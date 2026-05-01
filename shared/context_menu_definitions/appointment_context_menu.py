"""Appointment context menu definitions."""

from __future__ import annotations

from shared.context_menu.dto import ContextMenuActionDTO, ContextMenuItemDTO, ContextMenuSectionDTO


class AppointmentContextAction:
    MARK_COMPLETED = "appointments.row.mark_completed"
    MARK_CANCELLED = "appointments.row.mark_cancelled"
    MARK_NO_SHOW = "appointments.row.mark_no_show"
    SEND_REMINDER = "appointments.row.send_reminder"
    COPY_CUSTOMER = "appointments.row.copy_customer"
    COPY_PHONE = "appointments.row.copy_phone"
    COPY_SERVICE = "appointments.row.copy_service"
    REFRESH = "appointments.refresh"
    DELETE = "appointments.row.delete"


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
            id="appointment_primary",
            title="Appointment",
            items=(
                _action(AppointmentContextAction.MARK_COMPLETED, "Mark completed"),
                _action(AppointmentContextAction.MARK_CANCELLED, "Mark cancelled"),
                _action(AppointmentContextAction.MARK_NO_SHOW, "Mark no show"),
                _action(AppointmentContextAction.SEND_REMINDER, "WhatsApp reminder"),
            ),
        ),
        ContextMenuSectionDTO(
            id="appointment_copy",
            title="Copy",
            items=(
                _action(AppointmentContextAction.COPY_CUSTOMER, "Copy customer name"),
                _action(AppointmentContextAction.COPY_PHONE, "Copy phone number"),
                _action(AppointmentContextAction.COPY_SERVICE, "Copy service"),
            ),
        ),
        ContextMenuSectionDTO(
            id="appointment_maintenance",
            title="Maintenance",
            items=(
                _action(AppointmentContextAction.REFRESH, "Refresh appointments", "F5"),
                _action(AppointmentContextAction.DELETE, "Delete appointment", danger=True),
            ),
        ),
    )
