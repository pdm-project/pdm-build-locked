"""
    pdm-build-locked

    A PDM plugin that adds locked dependencies to optional-dependencies on build
"""
from pdm.core import Core
from pdm.project.config import ConfigItem

from .command import BuildCommand


def plugin(core: Core) -> None:
    """register pdm plugin

    Args:
        core: pdm core
    """
    core.register_command(BuildCommand)
    core.add_config(
        "build-locked.lock",
        ConfigItem("Build this project with locked dependencies", False, env_var="PDM_BUILD_LOCKED"),
    )
