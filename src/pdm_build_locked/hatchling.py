from __future__ import annotations

from pathlib import Path

from hatchling.metadata.plugin.interface import MetadataHookInterface
from hatchling.plugin import hookimpl

from ._utils import update_metadata_with_locked


class BuildLockedMetadataHook(MetadataHookInterface):
    PLUGIN_NAME = "build-locked"

    def update(self, metadata: dict) -> None:
        update_metadata_with_locked(metadata, Path(self.root))


@hookimpl
def hatch_register_metadata_hook() -> type[MetadataHookInterface]:
    return BuildLockedMetadataHook
