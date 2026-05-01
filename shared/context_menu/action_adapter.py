"""Callback adapter for context menu actions.

Menu definitions use stable action IDs. Existing screens can register their
current handlers against those IDs without moving business logic into the menu
system.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .dto import ContextMenuActionDTO, ContextMenuContextDTO


ActionCallback = Callable[[ContextMenuContextDTO, ContextMenuActionDTO], Any]


class ContextMenuActionAdapter:
    def __init__(self) -> None:
        self._callbacks: dict[str, ActionCallback] = {}

    def register(self, callback_key: str, callback: ActionCallback) -> None:
        key = (callback_key or "").strip()
        if not key:
            raise ValueError("callback_key is required")
        if not callable(callback):
            raise TypeError("callback must be callable")
        self._callbacks[key] = callback

    def unregister(self, callback_key: str) -> None:
        self._callbacks.pop((callback_key or "").strip(), None)

    def clear(self) -> None:
        self._callbacks.clear()

    def has_callback(self, callback_key: str) -> bool:
        return (callback_key or "").strip() in self._callbacks

    def dispatch(self, context: ContextMenuContextDTO, action: ContextMenuActionDTO) -> Any:
        key = (action.callback_key or "").strip()
        callback = self._callbacks.get(key)
        if callback is None:
            raise KeyError(f"No context menu callback registered for {key!r}")
        return callback(context, action)


action_adapter = ContextMenuActionAdapter()
