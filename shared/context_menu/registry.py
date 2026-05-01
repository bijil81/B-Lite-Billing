"""Registry for module-specific context menu definitions."""

from __future__ import annotations

from collections.abc import Iterable

from .dto import ContextMenuContextDTO, ContextMenuSectionDTO


RegistryKey = tuple[str, str, str]


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower()


class ContextMenuRegistryService:
    def __init__(self) -> None:
        self._sections: dict[RegistryKey, tuple[ContextMenuSectionDTO, ...]] = {}

    def register(
        self,
        module_name: str,
        sections: Iterable[ContextMenuSectionDTO],
        *,
        entity_type: str = "",
        widget_type: str = "",
    ) -> None:
        key = (_normalize(module_name), _normalize(entity_type), _normalize(widget_type))
        if not key[0]:
            raise ValueError("module_name is required")
        self._sections[key] = tuple(sections)

    def unregister(self, module_name: str, *, entity_type: str = "", widget_type: str = "") -> None:
        key = (_normalize(module_name), _normalize(entity_type), _normalize(widget_type))
        self._sections.pop(key, None)

    def clear(self) -> None:
        self._sections.clear()

    def resolve(self, context: ContextMenuContextDTO) -> tuple[ContextMenuSectionDTO, ...]:
        module = _normalize(context.module_name)
        entity = _normalize(context.entity_type)
        widget = _normalize(context.widget_type)
        candidates = (
            (module, entity, widget),
            (module, entity, ""),
            (module, "", widget),
            (module, "", ""),
            ("global", entity, widget),
            ("global", entity, ""),
            ("global", "", widget),
            ("global", "", ""),
        )
        for key in candidates:
            sections = self._sections.get(key)
            if sections is not None:
                return sections
        return ()


registry_service = ContextMenuRegistryService()
