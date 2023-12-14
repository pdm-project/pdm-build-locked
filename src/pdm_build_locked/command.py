"""pdm build --locked command"""
from __future__ import annotations

import argparse
import subprocess
from contextlib import suppress
from typing import Dict, List, Optional, Tuple, Union

from pdm.cli import actions
from pdm.cli.commands.build import Command as BaseCommand
from pdm.exceptions import PdmException
from pdm.models.requirements import Requirement
from pdm.project.core import Project
from pdm.resolver import resolve
from pdm.resolver.providers import ReusePinProvider
from pdm.utils import normalize_name
from resolvelib import BaseReporter

DependencyList = Dict[str, Union[List[str], Dict[str, List[str]]]]

# copied from pdm.models.repository due to TYPECHECKING guard
CandidateKey = Tuple[str, Optional[str], Optional[str], bool]


class BuildCommand(BaseCommand):  # type: ignore[misc]
    """subclasses pdm's build command and calls it via super()"""

    name = "build"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "-l", "--locked", help="Add locked dependencies to distribution metadata.", action="store_true"
        )
        super().add_arguments(parser)

    def handle(self, project: Project, options: argparse.Namespace) -> None:
        # pylint: disable=too-many-locals; we want this in a single function
        if not options.locked and not project.pyproject.settings.get("build", {}).get("locked", False):
            super().handle(project, options)
            return

        # we are not interested in the pdm dev-dependencies group
        pdm_dev_dependencies = []
        if dev_dependencies := project.pyproject.settings.get("dev-dependencies"):
            pdm_dev_dependencies = dev_dependencies.keys()

        groups = {group for group in project.all_dependencies if group not in pdm_dev_dependencies}

        locked_groups = [self._get_locked_group_name(group) for group in groups]
        if duplicate_groups := groups.intersection(locked_groups):
            raise PdmException(
                f"You already have groups in your lockfile that would be overwritten by this command:"
                f" {duplicate_groups}. Please remove them."
            )

        ###################
        # update lockfile
        ###################
        self._update_lockfile(project)

        # retrieve locked dependencies and write to pyproject
        optional_dependencies: dict[str, list[str]] = {}

        ###############################
        # determine locked dependencies
        ###############################
        project.core.ui.echo("pdm-build-locked - Resolving locked packages from lockfile...")

        for group in groups:
            locked_group_name = self._get_locked_group_name(group)

            locked_packages = self._get_locked_packages(project, group)
            optional_dependencies[locked_group_name] = locked_packages

        ####################
        # write to pyproject
        ####################

        # get reference to optional-dependencies in project.pyproject, or create it if it doesn't exist
        optional = project.pyproject.metadata.get(
            "optional-dependencies", None
        ) or project.pyproject.metadata.setdefault("optional-dependencies", {})

        # update target
        optional.update(optional_dependencies)
        project.pyproject.write(show_message=False)

        # to prevent unclean scm status, we need to ignore pyproject.toml during build
        self._git_ignore_pyproject(project, True)

        ################
        # build project
        ################
        try:
            super().handle(project, options)
        finally:
            # undo our changes to pyproject.toml even if pdm build crashes
            for group in locked_groups:
                with suppress(KeyError):
                    project.pyproject.metadata.get("optional-dependencies", {}).pop(group)
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
        groups = list(project.all_dependencies.keys())
        with suppress(ValueError):
            groups.remove("dev")
        if strategy:
            actions.do_lock(project, strategy=strategy, groups=groups)

    @staticmethod
    def _get_locked_group_name(group: str) -> str:
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
        requirements: dict[str, Requirement] = project.get_dependencies(group)

        # get a ReusePinProvider - we don't want any calls to the remote repository,
        # we just want to read from the lockfile
        locked_repository = project.locked_repository
        locked_repository.ignore_compatibility = True
        project.get_provider()
        # taken from pdm.actions.resolve_candidates_from_lockfile and adjusted
        provider = ReusePinProvider(
            locked_repository.all_candidates,
            (),
            locked_repository,
            project.allow_prereleases,
            {normalize_name(k): v for k, v in project.pyproject.resolution_overrides.items()},
        )
        resolver = project.core.resolver_class(provider, BaseReporter())
        reqs = list(requirements.values())
        candidates, *_ = resolve(resolver, reqs, project.environment.python_requires)

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
            subprocess.run(["git", "update-index", skip_worktree, project.root.joinpath("pyproject.toml")], check=False)
