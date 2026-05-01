"""Redeem code context menu definitions."""

from __future__ import annotations

from shared.context_menu.dto import ContextMenuActionDTO, ContextMenuItemDTO, ContextMenuSectionDTO


class RedeemContextAction:
    SEND_WHATSAPP = "redeem.row.send_whatsapp"
    COPY_CODE = "redeem.row.copy_code"
    COPY_PHONE = "redeem.row.copy_phone"
    COPY_NAME = "redeem.row.copy_name"
    REFRESH = "redeem.refresh"
    DELETE = "redeem.row.delete"
    COPY_RESULT = "redeem.generate.copy_result"


def _action(action_id: str, label: str, shortcut: str = "", danger: bool = False) -> ContextMenuItemDTO:
    return ContextMenuItemDTO.action_item(
        ContextMenuActionDTO(
            id=action_id,
            label=label,
            callback_key=action_id,
            shortcut=shortcut,
            danger=danger,
        )
    )


def get_row_sections() -> tuple[ContextMenuSectionDTO, ...]:
    return (
        ContextMenuSectionDTO(
            id="redeem_primary",
            title="Redeem",
            items=(
                _action(RedeemContextAction.SEND_WHATSAPP, "Send WhatsApp"),
            ),
        ),
        ContextMenuSectionDTO(
            id="redeem_copy",
            title="Copy",
            items=(
                _action(RedeemContextAction.COPY_CODE, "Copy redeem code"),
                _action(RedeemContextAction.COPY_PHONE, "Copy phone number"),
                _action(RedeemContextAction.COPY_NAME, "Copy customer name"),
            ),
        ),
        ContextMenuSectionDTO(
            id="redeem_maintenance",
            title="Maintenance",
            items=(
                _action(RedeemContextAction.REFRESH, "Refresh codes", "F5"),
                _action(RedeemContextAction.DELETE, "Delete code", danger=True),
            ),
        ),
    )


def get_result_sections() -> tuple[ContextMenuSectionDTO, ...]:
    return (
        ContextMenuSectionDTO(
            id="redeem_generate_result",
            title="Generated Result",
            items=(
                _action(RedeemContextAction.COPY_RESULT, "Copy generated result"),
            ),
        ),
    )
