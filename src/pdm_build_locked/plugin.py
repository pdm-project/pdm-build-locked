"""
    pdm-build-locked

    A PDM plugin that adds locked dependencies to optional-dependencies on build
"""
from pdm.core import Core

from .command import BuildCommand


def main(core: Core) -> None:
    """register pdm plugin

    Args:
        core: pdm core
    """
    core.register_command(BuildCommand)
