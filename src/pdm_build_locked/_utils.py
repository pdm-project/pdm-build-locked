from __future__ import annotations

import os
import sys
import warnings
from collections.abc import Iterable, MutableMapping
from pathlib import Path
from typing import Any

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # pragma: no cover


class UnsupportedRequirement(ValueError):
    """Requirement not complying with PEP 508"""


class IncompatibleLockedRequirement(ValueError):
    """Locked requirement's pinned version is incompatible with a declared requirement"""


def check_locked_requirement_compatible(requirement_string: str, base_requirements: Iterable[str], group: str) -> None:
    """Ensure a locked requirement's pinned version satisfies the version specifier of any
    same-named requirement in ``base_requirements`` (requirements always installed alongside
    the locked group, e.g. via ``project.dependencies``).

    This catches ``tool.pdm.resolution.overrides`` pinning a version outside of the declared
    range, which would otherwise make e.g. ``pip install mypkg[locked]`` unsatisfiable.

    Args:
        requirement_string: the locked requirement, as produced for the locked group
        base_requirements: requirement strings always installed alongside the locked group
        group: the group name, used in the error message

    Raises:
        IncompatibleLockedRequirement: if the pinned version doesn't satisfy a declared specifier
    """
    req = Requirement(requirement_string)
    specifiers = list(req.specifier)
    if len(specifiers) != 1 or specifiers[0].operator != "==":
        return
    pinned_version = Version(specifiers[0].version)
    name = canonicalize_name(req.name)

    for base_requirement_string in base_requirements:
        base_req = Requirement(base_requirement_string)
        if canonicalize_name(base_req.name) != name or not base_req.specifier:
            continue
        if not base_req.specifier.contains(pinned_version, prereleases=True):
            raise IncompatibleLockedRequirement(
                f"Locked dependency '{requirement_string}' for group '{group}' is incompatible with "
                f"declared requirement '{base_requirement_string}'. This usually happens when "
                "tool.pdm.resolution.overrides pins a version outside of the declared range."
            )


def requirement_dict_to_string(req_dict: dict[str, Any]) -> str:
    """Build a requirement string from a package item from pdm.lock

    Args:
        req_dict: The package item from pdm.lock

    Returns:
        A PEP 582 requirement string
    """
    extra_string = f"[{','.join(extras)}]" if (extras := req_dict.get("extras", [])) else ""
    version_string = (
        f"=={version}"
        if ((version := req_dict.get("version")) and all(x not in req_dict for x in ("url", "ref", "revision")))
        else ""
    )
    if "name" not in req_dict:
        raise UnsupportedRequirement(f"Missing name in requirement: {req_dict}")
    if "editable" in req_dict:
        raise UnsupportedRequirement(f"Editable requirement is not allowed: {req_dict}")
    if "path" in req_dict:
        raise UnsupportedRequirement(f"Local path requirement is not allowed: {req_dict}")

    url_string = ""
    if "url" in req_dict:
        url_string = f" @ {req_dict['url']}"
    elif "revision" in req_dict or "ref" in req_dict:  # VCS requirement
        vcs, repo = next((k, v) for k, v in req_dict.items() if k in ("git", "svn", "bzr", "hg"))  # pragma: no cover
        url_string = f" @ {vcs}+{repo}@{req_dict.get('revision', req_dict.get('ref'))}"
    if "subdirectory" in req_dict:
        url_string = f"{url_string}#subdirectory={req_dict['subdirectory']}"

    marker_string = f" ; {marker}" if (marker := req_dict.get("marker")) else ""
    return f"{req_dict['name']}{extra_string}{version_string}{url_string}{marker_string}"


def get_locked_group_name(group: str) -> str:
    """
    Get the name of the locked group corresponding to the original group
    default dependencies: locked
    optional dependency groups: {group}-locked

    Args:
        group: original group name

    Returns:
        locked group name
    """
    group_name = "locked"
    if group != "default":
        group_name = f"{group}-{group_name}"

    return group_name


def update_metadata_with_locked(
    metadata: MutableMapping[str, Any], root: Path, groups: list[str] | None = None
) -> None:  # pragma: no cover
    """Inplace update the metadata(pyproject.toml) with the locked dependencies.

    Args:
        metadata (dict[str, Any]): The metadata dictionary
        root (Path): The path to the project root
        groups (list[str], optional): The groups to lock. Defaults to default + all optional groups.

    Raises:
        UnsupportedRequirement
    """
    lockfile = root / "pdm.lock"
    if "PDM_LOCKFILE" in os.environ:
        lockfile = Path(os.environ["PDM_LOCKFILE"])
    if not lockfile.exists():
        warnings.warn("The lockfile doesn't exist, skip locking dependencies", UserWarning, stacklevel=1)
        return
    with lockfile.open("rb") as f:
        lockfile_content = tomllib.load(f)

    if "inherit_metadata" not in lockfile_content.get("metadata", {}).get("strategy", []):
        warnings.warn(
            "The lockfile doesn't support 'inherit_metadata' strategy, skip locking dependencies",
            UserWarning,
            stacklevel=1,
        )
        return

    optional_groups = list(metadata.get("optional-dependencies", {}))
    locked_groups = lockfile_content.get("metadata", {}).get("groups", [])
    if groups is None:
        groups = ["default", *optional_groups]
    for group in groups:
        locked_group = get_locked_group_name(group)
        if locked_group in optional_groups:
            # already exists, don't override
            continue
        if group not in locked_groups:
            print(f"Group {group} is not stored in the lockfile, skip locking dependencies for it.")
            continue
        base_requirements = list(metadata.get("dependencies", []))
        if group != "default":
            base_requirements += list(metadata.get("optional-dependencies", {}).get(group, []))

        requirements: list[str] = []
        for package in lockfile_content.get("package", []):
            if group in package.get("groups", []):
                try:
                    requirement_string = requirement_dict_to_string(package)
                except UnsupportedRequirement as e:
                    print(f"Skipping unsupported requirement: {e}")
                    continue
                check_locked_requirement_compatible(requirement_string, base_requirements, group)
                requirements.append(requirement_string)

        metadata.setdefault("optional-dependencies", {})[locked_group] = requirements
