# -*- mode: python ; coding: utf-8 -*-
# WhiteLabelApp.spec - PyInstaller spec for the white-label desktop app
# Build command: python -m PyInstaller WhiteLabelApp.spec
import sys
from pathlib import Path

if "__file__" in globals():
    ROOT = Path(__file__).resolve().parent
else:
    ROOT = Path.cwd()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from branding import get_build_branding

block_cipher = None
brand = get_build_branding()

hidden = [
    'accounting', 'admin', 'appointments', 'auth', 'auth_security',
    'branding',
    'backup_system', 'billing', 'booking_calendar', 'closing_report', 'cloud_sync',
    'customers', 'dashboard', 'db', 'expenses', 'help_content',
    'help_system', 'icon_system', 'inventory', 'membership', 'migration_state',
    'notifications', 'offers', 'print_engine', 'print_templates',
    'print_utils', 'redeem_codes', 'reports', 'salon_settings',
    'staff', 'ui_components', 'ui_responsive', 'ui_text',
    'ui_theme', 'ui_utils', 'utils', 'date_helpers',
    'whatsapp_bulk', 'whatsapp_helper',
    'ai_assistant', 'ai_assistant.controllers',
    'ai_assistant.controllers.ai_controller',
    'ai_assistant.services', 'ai_assistant.services.ai_agent',
    'ai_assistant.services.ai_service', 'ai_assistant.services.ai_tools',
    'ai_assistant.ui', 'ai_assistant.ui.ai_chat_window',
    'secure_store', 'keyring', 'keyring.backends',
    'flask', 'jinja2', 'werkzeug',
    'openai', 'anthropic',
    'tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.filedialog',
    'tkinter.simpledialog', 'tkinter.colorchooser',
    'PIL', 'PIL.Image', 'PIL.ImageTk',
    'reportlab', 'reportlab.pdfgen', 'reportlab.pdfgen.canvas',
    'reportlab.lib', 'reportlab.lib.pagesizes', 'reportlab.lib.units',
    'reportlab.lib.colors', 'reportlab.platypus',
    'selenium', 'selenium.webdriver',
    'selenium.webdriver.edge.options', 'selenium.webdriver.edge.service',
    'selenium.webdriver.chrome.options', 'selenium.webdriver.chrome.service',
    'selenium.webdriver.firefox.options', 'selenium.webdriver.firefox.service',
    'selenium.webdriver.common.keys', 'selenium.webdriver.support.ui',
    'selenium.webdriver.support.expected_conditions',
    'webdriver_manager', 'webdriver_manager.microsoft',
    'webdriver_manager.chrome', 'webdriver_manager.firefox',
    'openpyxl', 'openpyxl.styles', 'openpyxl.utils',
    'bcrypt',
    'sqlite3', 'csv', 'json', 'shutil', 'threading', 'hashlib',
    'logging', 'logging.handlers', 're', 'difflib', 'atexit',
    'collections', 'win32api', 'win32print', 'pywhatkit',
    'update_checker',
    'db_core', 'db_core.connection', 'db_core.constraint_migration', 'db_core.query_utils',
    'db_core.schema_manager', 'db_core.transaction',
    'repositories', 'repositories.appointments_repo', 'repositories.attendance_repo',
    'repositories.billing_repo', 'repositories.brands_repo',
    'repositories.customers_repo', 'repositories.inventory_repo',
    'repositories.memberships_repo', 'repositories.offers_repo',
    'repositories.products_repo', 'repositories.product_categories_repo',
    'repositories.product_variants_repo', 'repositories.reports_repo',
    'repositories.settings_repo', 'repositories.staff_repo',
    'repositories.users_repo',
    'services_v5', 'services_v5.appointment_service', 'services_v5.attendance_service',
    'services_v5.auth_service', 'services_v5.billing_service',
    'services_v5.customer_service', 'services_v5.inventory_service',
    'services_v5.membership_service', 'services_v5.offers_service',
    'services_v5.product_catalog_service', 'services_v5.report_service',
    'services_v5.staff_service',
    'migrations', 'migrations.migration_runner',
    'migrations.migrate_appointments', 'migrations.migrate_customers',
    'migrations.migrate_expenses', 'migrations.migrate_inventory',
    'migrations.migrate_memberships', 'migrations.migrate_offers',
    'migrations.migrate_product_variants', 'migrations.migrate_sales_csv',
    'migrations.migrate_staff', 'migrations.migrate_users',
    'migrations.migration_validate',
    'validators', 'validators.billing_validator',
    'validators.appointment_validator', 'validators.customer_validator',
    'validators.product_validator', 'validators.common_validators',
    # Licensing system -- client-side verification only
    'licensing', 'licensing.crypto', 'licensing.device',
    'licensing.integrity', 'licensing.install', 'licensing.license_manager',
    'licensing.public_key', 'licensing.storage', 'licensing.trial', 'licensing.ui_gate',
    # Packages with submodules imported transitively by top-level modules
    'adapters', 'adapters.billing_adapter', 'adapters.customer_adapter',
    'adapters.product_catalog_adapter', 'adapters.report_adapter',
    'adapters.staff_adapter',
    'multibranch', 'multibranch.sync_config', 'multibranch.sync_manager',
    'whatsapp_api', 'whatsapp_api.api_settings', 'whatsapp_api.provider_factory',
    # Support modules imported at runtime (not via module_specs)
    'reports_data', 'reports_export',
    'advanced_tab', 'billing_logic',
]

datas = [
    ('assets',               'assets'),
    ('sql',                  'sql'),
    ('services_db.json',     '.'),
    ('print_settings.json',  '.'),
    ('pkg_templates.json', '.'),
    ('membership_templates.json', '.'),
    ('offers_templates.json', '.'),
    ('redeem_codes_templates.json', '.'),
]

for optional_name in ("icon.ico", "logo.png", "loading_logo.gif"):
    optional_path = ROOT / optional_name
    if optional_path.exists():
        datas.append((str(optional_path), '.'))

a = Analysis(
    ['main.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'scipy',
        'IPython', 'jupyter', 'test', 'tests', 'pytest', '_pytest',
        'unittest', 'openpyxl.tests',
        # SECURITY: Admin-only tools must NOT ship in production.
        # These contain key generation and integrity-reset functions.
        'licensing_admin', 'licensing_admin.keygen',
        'licensing_admin.refresh_integrity',
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=brand['exe_name'],
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=brand['app_icon'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=brand['dist_name'],
)
