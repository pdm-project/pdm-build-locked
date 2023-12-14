from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ._utils import update_metadata_with_locked

if TYPE_CHECKING:
    from pdm.backend.hooks import BuildHookInterface
    from pdm.backend.hooks.base import Context
else:
    BuildHookInterface = object


class BuildLockedHook(BuildHookInterface):
    def pdm_build_hook_enabled(self, context: Context) -> bool:
        if os.getenv("PDM_BUILD_LOCKED", "false") != "false":
            return True
        return context.config.build_config.get("locked", False)

    def pdm_build_initialize(self, context: Context) -> None:
        static_fields = list(context.config.metadata)
        update_metadata_with_locked(context.config.metadata, context.root)
        new_fields = set(context.config.metadata) - set(static_fields)
        for field in new_fields:
            if field in context.config.metadata.get("dynamic", []):
                context.config.metadata["dynamic"].remove(field)
