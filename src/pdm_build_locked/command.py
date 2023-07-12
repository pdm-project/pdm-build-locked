"""pdm build --locked command"""
import argparse
import subprocess
from contextlib import suppress
from typing import Dict, List, Set, Tuple, Union

from pdm.cli import actions
from pdm.cli.commands.build import Command as BaseCommand
from pdm.exceptions import PdmException
from pdm.models.candidates import Candidate
from pdm.models.requirements import Requirement, parse_requirement
from pdm.project.core import Project

DependencyList = Dict[str, Union[List[str], Dict[str, List[str]]]]

# copied from pdm.models.repository due to TYPECHECKING guard
CandidateKey = Tuple[str, Union[str, None], Union[str, None], bool]


class BuildCommand(BaseCommand):
    """subclasses pdm's build command and calls it via super()"""

    description = BaseCommand.__doc__
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

        groups = set(group for group in project.all_dependencies.keys() if group not in pdm_dev_dependencies)

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
        optional_dependencies: Dict[str, Set[str]] = {}

        ###############################
        # determine locked dependencies
        ###############################
        # performance optimization: we prepare the data structure here instead of searching inside the loop
        locked_package_version: Dict[str, Tuple[CandidateKey, Candidate]] = {}
        for package_key, package in project.locked_repository.packages.items():
            locked_package_version[str(package.name)] = (package_key, package)

        for group in groups:
            group_name = self._get_locked_group_name(group)
            optional_dependencies[group_name] = set()

            for dependency in project.all_dependencies[group].values():
                locked_packages = self._get_locked_packages(project, locked_package_version, str(dependency.name))
                optional_dependencies[group_name].update(locked_packages)

        ####################
        # write to pyproject
        ####################
        # transform sets to list for target project.pyproject.metadata
        optional_dependencies_pyproject = dict((key, list(value)) for key, value in optional_dependencies.items())
        optional_dependencies_pyproject.update(project.pyproject.metadata.get("optional-dependencies", {}))

        # get reference to optional-dependencies in project.pyproject, or create it if it doesn't exist
        optional = project.pyproject.metadata.get(
            "optional-dependencies", None
        ) or project.pyproject.metadata.setdefault("optional-dependencies", {})

        # update target
        optional.update(optional_dependencies_pyproject)
        project.pyproject.write()

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
            project.pyproject.write()
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
    def _get_locked_packages(
        project: Project, locked_package_version: Dict[str, Tuple[CandidateKey, Candidate]], pkg: str
    ) -> Set[str]:
        """
        Recursively determine locked dependency strings
        For

        Target: the locked optional-dependency groups in pyproject.toml

        Args:
            project: the pdm Project
            locked_package_version: data structure based on current lockfile mapping package name to lockfile Candidate
            pkg: package name

        Returns:
            Set of locked packages
        """
        locked_packages: Set[str] = set()
        pkg = pkg.lower()

        package_key, package = locked_package_version[pkg]

        # lock self
        locked_packages.add(str(package.req))  # pdm Requirement classes implement __repr__

        # lock self requirements, if any
        reqs, _, _ = project.locked_repository.candidate_info[package_key]
        sub_dependencies: List[Requirement] = list(map(parse_requirement, reqs))
        for sub_dependency in sub_dependencies:
            # recursing into self for each sub-package
            locked_packages.update(
                BuildCommand._get_locked_packages(project, locked_package_version, str(sub_dependency.name))
            )

        return locked_packages

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
