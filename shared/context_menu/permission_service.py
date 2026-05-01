"""Role-aware permission checks for context menu actions."""

from __future__ import annotations

from .constants import PermissionKey
from .dto import ContextMenuActionDTO, ContextMenuContextDTO


ROLE_ALIASES = {
    "owner": "owner",
    "admin": "owner",
    "administrator": "owner",
    "manager": "manager",
    "cashier": "cashier",
    "receptionist": "receptionist",
    "staff": "staff",
    "viewer": "viewer",
    "view": "viewer",
}


ROLE_DENY: dict[str, set[str]] = {
    "owner": set(),
    "manager": {PermissionKey.ADMIN_USER_DISABLE},
    "cashier": {
        PermissionKey.INVOICE_DELETE,
        PermissionKey.INVENTORY_STOCK_REMOVE,
        PermissionKey.STAFF_SALARY_VIEW,
        PermissionKey.ADMIN_USER_DISABLE,
    },
    "receptionist": {
        PermissionKey.INVOICE_DELETE,
        PermissionKey.INVENTORY_STOCK_REMOVE,
        PermissionKey.STAFF_SALARY_VIEW,
        PermissionKey.ADMIN_USER_DISABLE,
    },
    "staff": {
        PermissionKey.INVOICE_DELETE,
        PermissionKey.CUSTOMER_DELETE,
        PermissionKey.INVENTORY_STOCK_REMOVE,
        PermissionKey.STAFF_SALARY_VIEW,
        PermissionKey.ADMIN_USER_DISABLE,
    },
    "viewer": {
        PermissionKey.INVOICE_DELETE,
        PermissionKey.INVOICE_PAYMENT_ADD,
        PermissionKey.CUSTOMER_DELETE,
        PermissionKey.INVENTORY_STOCK_REMOVE,
        PermissionKey.STAFF_SALARY_VIEW,
        PermissionKey.ADMIN_USER_DISABLE,
    },
}


class ContextMenuPermissionService:
    def normalize_role(self, role: str) -> str:
        return ROLE_ALIASES.get((role or "").strip().lower(), "viewer")

    def can_access(self, permission_key: str, user_role: str) -> bool:
        key = (permission_key or "").strip()
        if not key:
            return True
        role = self.normalize_role(user_role)
        return key not in ROLE_DENY.get(role, ROLE_DENY["viewer"])

    def is_visible(self, action: ContextMenuActionDTO, context: ContextMenuContextDTO) -> bool:
        return self.can_access(action.permission_key, context.user_role)

    def is_enabled(self, action: ContextMenuActionDTO, context: ContextMenuContextDTO) -> bool:
        if not self.can_access(action.permission_key, context.user_role):
            return False
        if action.enabled_when:
            return bool(context.extra.get(action.enabled_when))
        return True


permission_service = ContextMenuPermissionService()
