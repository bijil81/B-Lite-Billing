"""Membership context menu definitions."""

from __future__ import annotations

from shared.context_menu.dto import ContextMenuActionDTO, ContextMenuItemDTO, ContextMenuSectionDTO


class MembershipContextAction:
    RENEW = "membership.row.renew"
    CANCEL = "membership.row.cancel"
    ADD_WALLET = "membership.row.add_wallet"
    COPY_CUSTOMER = "membership.row.copy_customer"
    COPY_PHONE = "membership.row.copy_phone"
    COPY_PACKAGE = "membership.row.copy_package"
    COPY_WALLET = "membership.row.copy_wallet"
    REFRESH = "membership.refresh"
    DELETE = "membership.row.delete"


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


def get_sections() -> tuple[ContextMenuSectionDTO, ...]:
    return (
        ContextMenuSectionDTO(
            id="membership_primary",
            title="Membership",
            items=(
                _action(MembershipContextAction.RENEW, "Renew membership"),
                _action(MembershipContextAction.CANCEL, "Cancel membership"),
                _action(MembershipContextAction.ADD_WALLET, "Add wallet balance"),
            ),
        ),
        ContextMenuSectionDTO(
            id="membership_copy",
            title="Copy",
            items=(
                _action(MembershipContextAction.COPY_CUSTOMER, "Copy customer name"),
                _action(MembershipContextAction.COPY_PHONE, "Copy phone number"),
                _action(MembershipContextAction.COPY_PACKAGE, "Copy package name"),
                _action(MembershipContextAction.COPY_WALLET, "Copy wallet balance"),
            ),
        ),
        ContextMenuSectionDTO(
            id="membership_maintenance",
            title="Maintenance",
            items=(
                _action(MembershipContextAction.REFRESH, "Refresh memberships", "F5"),
                _action(MembershipContextAction.DELETE, "Delete membership", danger=True),
            ),
        ),
    )
