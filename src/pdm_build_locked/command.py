"""pdm build --locked command"""

from __future__ import annotations

import argparse
import inspect
import os
import subprocess
from contextlib import suppress
from importlib import import_module
from typing import Dict, List, Optional, Tuple, Union

from pdm.cli import actions
from pdm.cli.commands.build import Command as BaseCommand
from pdm.exceptions import PdmException
from pdm.project.core import Project

from ._utils import get_locked_group_name

DependencyList = Dict[str, Union[List[str], Dict[str, List[str]]]]

# copied from pdm.models.repository due to TYPECHECKING guard
CandidateKey = Tuple[str, Optional[str], Optional[str], bool]


class BuildCommand(BaseCommand):
    """subclasses pdm's build command and calls it via super()"""

    name = "build"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-l", "--locked", help="Add locked dependencies to distribution metadata.", action="store_true"
        )
        super().add_arguments(parser)

    def handle(self, project: Project, options: argparse.Namespace) -> None:
        # pylint: disable=too-many-locals; we want this in a single function
        if (
            not options.locked
            and not project.pyproject.settings.get("build", {}).get("locked", False)
            and os.getenv("PDM_BUILD_LOCKED", "false") == "false"
        ):
            super().handle(project, options)
            return

        # we are not interested in the pdm dev-dependencies group
        pdm_dev_dependencies = set()
        if dev_dependencies := project.pyproject.settings.get("dev-dependencies"):
            pdm_dev_dependencies = dev_dependencies.keys()

        if dev_dependencies := getattr(project.pyproject, "dev_dependencies", None):
            pdm_dev_dependencies |= dev_dependencies.keys()

        groups = project.pyproject.settings.get("build", {}).get("locked-groups", None)
        if groups is None:
            groups = {group for group in project.all_dependencies if group not in pdm_dev_dependencies}
        else:
            groups = set(groups)

        locked_groups = [get_locked_group_name(group) for group in groups]
        if duplicate_groups := groups.intersection(locked_groups):
            raise PdmException(
                f"You already have groups in your lockfile that would be overwritten by this command:"
                f" {duplicate_groups}. Please remove them."
            )

        # update lockfile
        self._update_lockfile(project)

        # retrieve locked dependencies and write to pyproject
        optional_dependencies: dict[str, list[str]] = {}

        # determine locked dependencies
        project.core.ui.echo("pdm-build-locked - Resolving locked packages from lockfile...")

        for group in groups:
            locked_group_name = get_locked_group_name(group)

            locked_packages = self._get_locked_packages(project, group)
            if locked_packages:
                optional_dependencies[locked_group_name] = locked_packages

        # write to pyproject
        # get reference to optional-dependencies in project.pyproject, or create it if it doesn't exist
        optional_key = "optional-dependencies"
        optional = project.pyproject.metadata.get(optional_key, None) or project.pyproject.metadata.setdefault(
            optional_key, {}
        )

        # update target
        optional.update(optional_dependencies)
        project.pyproject.metadata[optional_key] = optional
        project.pyproject.write(show_message=False)

        # to prevent unclean scm status, we need to ignore pyproject.toml during build
        self._git_ignore_pyproject(project, True)

        # build project
        try:
            super().handle(project, options)
        finally:
            # undo our changes to pyproject.toml even if pdm build crashes
            for group in locked_groups:
                with suppress(KeyError):
                    project.pyproject.metadata.get("optional-dependencies", {}).pop(group)
            if not project.pyproject.settings:
                del project.pyproject._data["tool"]["pdm"]  # type: ignore[union-attr]
                if not project.pyproject._data["tool"]:
                    del project.pyproject._data["tool"]

            project.pyproject.write(show_message=False)
            self._git_ignore_pyproject(project, False)

    @staticmethod
    def _update_lockfile(project: Project) -> None:
        """
        Update the lockfile if needed
        Reimplementation of pdm install lockfile check and update

        Args:
            project: the pdm project
        """
        strategy = actions.check_lockfile(project, raise_not_exist=False)
        groups = list(project.iter_groups())
        with suppress(ValueError):
            groups.remove("dev")
        if strategy:
            actions.do_lock(project, strategy=strategy, groups=groups)

    @staticmethod
    def _get_locked_packages(project: Project, group: str) -> list[str]:
        """
        Determine locked dependency strings for direct and transitive dependencies

        Args:
            project: the pdm Project
            group: the group to get pinned dependencies for

        Returns:
            Set of locked packages
        """
        from pdm.cli.actions import resolve_candidates_from_lockfile

        supported_params = inspect.signature(resolve_candidates_from_lockfile).parameters
        if "env_spec" in supported_params:
            # pdm 2.17.0+
            requirements = list(project.get_dependencies(group))
            markers = import_module("pdm.models.markers")
            # use lowest supported specifier to include all deps - we don't know the target Python at build time
            env_spec = markers.EnvSpec.from_spec(str(project.python_requires))
            candidates = resolve_candidates_from_lockfile(project, requirements, groups=[group], env_spec=env_spec)
        elif "cross_platform" in supported_params:
            # pdm 2.11.0+
            requirements = list(project.get_dependencies(group).values())  # type: ignore[attr-defined]
            candidates = resolve_candidates_from_lockfile(project, requirements, cross_platform=True, groups=[group])
        else:
            raise PdmException("Unsupported pdm version. pdm>=2.11 is required")

        return [str(c.req.as_pinned_version(c.version)) for c in candidates.values()]

    @staticmethod
    def _git_ignore_pyproject(project: Project, ignore: bool = True) -> None:
        """
        set the git index status of pyproject.toml if the project uses scm-based versioning
        Note: currently only git is supported - will crash if git repo is not present

        Args:
            project: the pdm project
            ignore: If True, ignore the file, else stop ignoring the file if it was ignored
        """
        skip_worktree = "--skip-worktree" if ignore else "--no-skip-worktree"
        if project.pyproject.settings.get("version", {}).get("source", "") == "scm":
            with suppress(FileNotFoundError):
                subprocess.run(
                    ["git", "update-index", skip_worktree, project.root.joinpath("pyproject.toml")], check=False
                )
