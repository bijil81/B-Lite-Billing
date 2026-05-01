"""Constants shared by the context menu foundation.

This module intentionally contains no Tkinter imports. The foundation layer
must stay safe to import from tests, build validation, and future non-UI code.
"""


class MenuKind:
    ACTION = "action"
    SEPARATOR = "separator"
    SUBMENU = "submenu"


class WidgetType:
    UNKNOWN = "unknown"
    ENTRY = "entry"
    TEXT = "text"
    TREEVIEW = "treeview"
    LISTBOX = "listbox"
    TABLE = "table"
    PREVIEW = "preview"
    CARD = "card"
    EMPTY_AREA = "empty_area"


class CommonActionId:
    COPY = "global.copy"
    PASTE = "global.paste"
    CUT = "global.cut"
    SELECT_ALL = "global.select_all"
    COPY_ALL = "global.copy_all"
    REFRESH = "global.refresh"
    OPEN = "global.open"
    DELETE = "global.delete"
    PRINT = "global.print"
    EXPORT = "global.export"


class PermissionKey:
    INVOICE_DELETE = "invoice.delete"
    INVOICE_EXPORT = "invoice.export"
    INVOICE_PAYMENT_ADD = "invoice.payment.add"
    CUSTOMER_DELETE = "customer.delete"
    INVENTORY_STOCK_REMOVE = "inventory.stock.remove"
    STAFF_SALARY_VIEW = "staff.salary.view"
    REPORT_SHARE = "report.share"
    ADMIN_USER_DISABLE = "admin.user.disable"


class FeatureFlag:
    ENABLE_CONTEXT_MENU = "ENABLE_CONTEXT_MENU"
    ENABLE_KEYBOARD_SHORTCUTS = "ENABLE_KEYBOARD_SHORTCUTS"
    ENABLE_ADVANCED_CLIPBOARD = "ENABLE_ADVANCED_CLIPBOARD"
    ENABLE_BULK_ACTIONS = "ENABLE_BULK_ACTIONS"
    ENABLE_RECENT_ACTIONS = "ENABLE_RECENT_ACTIONS"
    ENABLE_FAVORITE_ACTIONS = "ENABLE_FAVORITE_ACTIONS"
    ENABLE_EMPTY_AREA_MENUS = "ENABLE_EMPTY_AREA_MENUS"
    ENABLE_DASHBOARD_QUICK_MENUS = "ENABLE_DASHBOARD_QUICK_MENUS"
    ENABLE_ADMIN_CONTEXT_MENUS = "ENABLE_ADMIN_CONTEXT_MENUS"


ALL_FEATURE_FLAGS = (
    FeatureFlag.ENABLE_CONTEXT_MENU,
    FeatureFlag.ENABLE_KEYBOARD_SHORTCUTS,
    FeatureFlag.ENABLE_ADVANCED_CLIPBOARD,
    FeatureFlag.ENABLE_BULK_ACTIONS,
    FeatureFlag.ENABLE_RECENT_ACTIONS,
    FeatureFlag.ENABLE_FAVORITE_ACTIONS,
    FeatureFlag.ENABLE_EMPTY_AREA_MENUS,
    FeatureFlag.ENABLE_DASHBOARD_QUICK_MENUS,
    FeatureFlag.ENABLE_ADMIN_CONTEXT_MENUS,
)
