from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # pragma: no cover


class UnsupportedRequirement(ValueError):
    """Requirement not complying with PEP 508"""


def requirement_dict_to_string(req_dict: dict[str, Any]) -> str:
    """Build a requirement string from a package item from pdm.lock

    Args:
        req_dict: The package item from pdm.lock

    Returns:
        A PEP 582 requirement string
    """
    extra_string = f"[{','.join(extras)}]" if (extras := req_dict.get("extras", [])) else ""
    version_string = f"=={version}" if (version := req_dict.get("version")) else ""
    if "name" not in req_dict:
        raise UnsupportedRequirement(f"Missing name in requirement: {req_dict}")
    if "editable" in req_dict:
        raise UnsupportedRequirement(f"Editable requirement is not allowed: {req_dict}")
    if "path" in req_dict:
        raise UnsupportedRequirement(f"Local path requirement is not allowed: {req_dict}")

    url_string = ""
    if "url" in req_dict:
        url_string = f" @ {req_dict['url']}"
    elif "ref" in req_dict:  # VCS requirement
        vcs, repo = next((k, v) for k, v in req_dict.items() if k in ("git", "svn", "bzr", "hg"))  # pragma: no cover
        url_string = f" @ {vcs}+{repo}@{req_dict.get('revision', req_dict['ref'])}"
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


def update_metadata_with_locked(metadata: dict[str, Any], root: Path) -> None:  # pragma: no cover
    """Inplace update the metadata(pyproject.toml) with the locked dependencies.

    Args:
        metadata (dict[str, Any]): The metadata dictionary
        root (Path): The path to the project root

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

    groups = ["default"]
    optional_groups = list(metadata.get("optional-dependencies", {}))
    locked_groups = lockfile_content.get("metadata", {}).get("groups", [])
    groups.extend(optional_groups)
    for group in groups:
        locked_group = get_locked_group_name(group)
        if locked_group in optional_groups:
            # already exists, don't override
            continue
        if group not in locked_groups:
            print(f"Group {group} is not stored in the lockfile, skip locking dependencies for it.")
            continue
        requirements: list[str] = []
        for package in lockfile_content.get("package", []):
            if group in package.get("groups", []):
                try:
                    requirements.append(requirement_dict_to_string(package))
                except UnsupportedRequirement as e:
                    print(f"Skipping unsupported requirement: {e}")

        metadata.setdefault("optional-dependencies", {})[locked_group] = requirements
