from __future__ import annotations

from typing import Iterable, Mapping, Sequence

NavEntry = tuple[str, str, str, Sequence[str] | bool]
ModuleSpec = tuple[str, str]

APP_NAV: tuple[NavEntry, ...] = (
    ("\U0001F4C8", "Dashboard", "dashboard", ("owner", "manager", "receptionist")),
    ("\U0001F9FE", "Billing", "billing", ("owner", "manager", "receptionist", "staff")),
    ("\U0001F465", "Customers", "customers", ("owner", "manager", "receptionist", "staff")),
    ("\U0001F4C5", "Appointments", "appointments", ("owner", "manager", "receptionist", "staff")),
    ("\U0001F381", "Memberships", "membership", ("owner", "manager", "receptionist")),
    ("\U0001F3F7\ufe0f", "Offers", "offers", ("owner", "manager")),
    ("\U0001F39F\ufe0f", "Redeem", "redeem_codes", ("owner", "manager", "receptionist")),
    ("\u2601\ufe0f", "Cloud Sync", "cloud_sync", ("owner",)),
    ("\U0001F469\u200D\U0001F4BC", "Staff", "staff", ("owner", "manager")),
    ("\U0001F4E6", "Inventory", "inventory", ("owner", "manager")),
    ("\U0001F4B0", "Expenses", "expenses", ("owner", "manager")),
    ("\U0001F48C", "Bulk WhatsApp", "whatsapp_bulk", ("owner", "manager", "receptionist")),
    ("\U0001F4CA", "Reports", "reports", ("owner", "manager")),
    ("\U0001F4C5", "Closing Report", "closing_report", ("owner", "manager")),
    ("\U0001F916", "AI Assistant", "ai_assistant", ("owner", "manager", "receptionist", "staff")),
    ("\u2699", "Settings", "settings", ("owner",)),
)

ACTION_ROLES: dict[str, tuple[str, ...]] = {
    "admin_panel": ("owner",),
    "manage_users": ("owner",),
    "manage_staff": ("owner", "manager"),
    "manage_inventory": ("owner", "manager"),
    "manage_expenses": ("owner", "manager"),
    "manage_offers": ("owner", "manager"),
    "manage_cloud_sync": ("owner",),
    "delete_bill": ("owner", "manager"),
}

MODULE_SPECS: dict[str, ModuleSpec] = {
    "dashboard": ("dashboard", "DashboardFrame"),
    "billing": ("billing", "BillingFrame"),
    "customers": ("customers", "CustomersFrame"),
    "appointments": ("booking_calendar", "BookingCalendarFrame"),
    "membership": ("membership", "MembershipFrame"),
    "offers": ("offers", "OffersFrame"),
    "redeem_codes": ("redeem_codes", "RedeemCodesFrame"),
    "cloud_sync": ("cloud_sync", "CloudSyncFrame"),
    "staff": ("staff", "StaffFrame"),
    "inventory": ("inventory", "InventoryFrame"),
    "expenses": ("expenses", "ExpensesFrame"),
    "whatsapp_bulk": ("whatsapp_bulk", "WhatsAppBulkFrame"),
    "reports": ("reports", "ReportsFrame"),
    "accounting": ("accounting", "AccountingFrame"),
    "closing_report": ("closing_report", "ClosingReportFrame"),
    "settings": ("salon_settings", "SettingsFrame"),
}


def normalize_role(role: object) -> str:
    return str(role or "staff").strip().lower() or "staff"


def normalize_roles(roles: Iterable[object]) -> list[str]:
    return [normalize_role(role) for role in roles]


def build_nav_entries() -> list[NavEntry]:
    return [
        (icon, label, key, allowed if isinstance(allowed, bool) else list(allowed))
        for icon, label, key, allowed in APP_NAV
    ]


def build_action_roles() -> dict[str, list[str]]:
    return {permission: list(roles) for permission, roles in ACTION_ROLES.items()}


def build_module_specs() -> dict[str, ModuleSpec]:
    return dict(MODULE_SPECS)


def nav_entry_allows_role(nav_entry: NavEntry | None, role: object) -> bool:
    if not nav_entry:
        return False
    normalized_role = normalize_role(role)
    allowed = nav_entry[3]
    if isinstance(allowed, bool):
        return (not allowed) or normalized_role == "owner"
    return normalized_role in normalize_roles(allowed)


def action_allows_role(
    action_roles: Mapping[str, Sequence[str]],
    permission: str,
    role: object,
) -> bool:
    allowed = action_roles.get(permission, ())
    if not allowed:
        return False
    return normalize_role(role) in normalize_roles(allowed)


def first_allowed_nav_key(nav_entries: Iterable[NavEntry], role: object) -> str | None:
    for entry in nav_entries:
        if nav_entry_allows_role(entry, role):
            return entry[2]
    return None
