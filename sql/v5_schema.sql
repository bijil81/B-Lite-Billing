-- v5 relational foundation schema
-- additive only: safe to run alongside current legacy storage

CREATE TABLE IF NOT EXISTS v5_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS v5_app_users (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'staff',
    display_name TEXT DEFAULT '',
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS v5_app_settings (
    key TEXT PRIMARY KEY,
    value TEXT DEFAULT '',
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS v5_customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    legacy_phone TEXT UNIQUE,
    name TEXT NOT NULL DEFAULT '',
    birthday TEXT DEFAULT '',
    vip INTEGER DEFAULT 0,
    points_balance INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    is_deleted INTEGER DEFAULT 0,
    deleted_at TEXT DEFAULT '',
    deleted_by TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS v5_customer_visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    visit_date TEXT NOT NULL,
    note TEXT DEFAULT '',
    amount REAL DEFAULT 0.0,
    invoice_no TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(customer_id) REFERENCES v5_customers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS v5_loyalty_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    txn_type TEXT NOT NULL,
    points_delta INTEGER NOT NULL DEFAULT 0,
    reference_type TEXT DEFAULT '',
    reference_id TEXT DEFAULT '',
    note TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(customer_id) REFERENCES v5_customers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS v5_staff (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    legacy_name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    role_name TEXT DEFAULT 'staff',
    phone TEXT DEFAULT '',
    commission_pct REAL DEFAULT 0.0,
    salary REAL DEFAULT 0.0,
    active INTEGER DEFAULT 1,
    photo_path TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS v5_appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    legacy_key TEXT UNIQUE,
    customer_id INTEGER,
    customer_name TEXT NOT NULL DEFAULT '',
    phone TEXT DEFAULT '',
    service_name TEXT DEFAULT '',
    staff_name TEXT DEFAULT '',
    appointment_date TEXT NOT NULL,
    appointment_time TEXT NOT NULL,
    status TEXT DEFAULT 'Scheduled',
    dont_show INTEGER DEFAULT 0,
    last_reminded TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(customer_id) REFERENCES v5_customers(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS v5_services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    legacy_name TEXT NOT NULL UNIQUE,
    category TEXT DEFAULT '',
    price REAL DEFAULT 0.0,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS v5_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    legacy_name TEXT NOT NULL UNIQUE,
    sku TEXT DEFAULT '',
    unit TEXT DEFAULT 'pcs',
    sale_price REAL DEFAULT 0.0,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS v5_inventory_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    legacy_name TEXT NOT NULL UNIQUE,
    category TEXT DEFAULT '',
    brand TEXT DEFAULT '',
    unit TEXT DEFAULT 'pcs',
    current_qty REAL DEFAULT 0.0 CHECK(current_qty >= 0),
    min_qty REAL DEFAULT 0.0 CHECK(min_qty >= 0),
    cost_price REAL DEFAULT 0.0 CHECK(cost_price >= 0),
    sale_price REAL DEFAULT 0.0 CHECK(sale_price >= 0),
    active INTEGER DEFAULT 1,
    is_deleted INTEGER DEFAULT 0,
    deleted_at TEXT DEFAULT '',
    deleted_by TEXT DEFAULT '',
    updated_at TEXT DEFAULT (datetime('now')),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS v5_inventory_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    movement_type TEXT NOT NULL,
    qty_delta REAL NOT NULL,
    reference_type TEXT DEFAULT '',
    reference_id TEXT DEFAULT '',
    note TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(item_id) REFERENCES v5_inventory_items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS v5_offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    legacy_name TEXT NOT NULL UNIQUE,
    offer_type TEXT DEFAULT 'percentage',
    value REAL DEFAULT 0.0,
    service_name TEXT DEFAULT '',
    coupon_code TEXT DEFAULT '',
    min_bill REAL DEFAULT 0.0,
    valid_from TEXT DEFAULT '',
    valid_to TEXT DEFAULT '',
    active INTEGER DEFAULT 1,
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS v5_redeem_codes (
    code TEXT PRIMARY KEY,
    customer_phone TEXT DEFAULT '',
    customer_name TEXT DEFAULT '',
    discount_type TEXT DEFAULT 'flat',
    discount_value REAL DEFAULT 0.0,
    min_bill REAL DEFAULT 0.0,
    active INTEGER DEFAULT 1,
    used INTEGER DEFAULT 0,
    used_invoice TEXT DEFAULT '',
    valid_until TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS v5_redeem_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    invoice_no TEXT DEFAULT '',
    discount_amount REAL DEFAULT 0.0,
    customer_phone TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(code) REFERENCES v5_redeem_codes(code) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS v5_membership_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_name TEXT NOT NULL UNIQUE,
    duration_days INTEGER DEFAULT 0,
    discount_pct REAL DEFAULT 0.0,
    wallet_amount REAL DEFAULT 0.0,
    price REAL DEFAULT 0.0,
    description TEXT DEFAULT '',
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS v5_customer_memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_phone TEXT NOT NULL,
    customer_name TEXT DEFAULT '',
    plan_name TEXT NOT NULL,
    discount_pct REAL DEFAULT 0.0,
    wallet_balance REAL DEFAULT 0.0,
    start_date TEXT DEFAULT '',
    expiry_date TEXT DEFAULT '',
    status TEXT DEFAULT 'Active',
    price_paid REAL DEFAULT 0.0,
    payment_method TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS v5_membership_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_membership_id INTEGER,
    customer_phone TEXT NOT NULL,
    txn_type TEXT NOT NULL,
    amount REAL DEFAULT 0.0,
    note TEXT DEFAULT '',
    reference_id TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(customer_membership_id) REFERENCES v5_customer_memberships(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS v5_expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expense_date TEXT NOT NULL,
    category TEXT DEFAULT '',
    staff_name TEXT DEFAULT '',
    description TEXT DEFAULT '',
    amount REAL DEFAULT 0.0,
    payment_method TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS v5_invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no TEXT NOT NULL UNIQUE,
    invoice_date TEXT NOT NULL,
    customer_phone TEXT DEFAULT '',
    customer_name TEXT DEFAULT '',
    gross_total REAL DEFAULT 0.0 CHECK(gross_total >= 0),
    discount_total REAL DEFAULT 0.0 CHECK(discount_total >= 0),
    tax_total REAL DEFAULT 0.0 CHECK(tax_total >= 0),
    net_total REAL DEFAULT 0.0 CHECK(net_total >= 0),
    loyalty_earned INTEGER DEFAULT 0,
    loyalty_redeemed INTEGER DEFAULT 0,
    redeem_code TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_by TEXT DEFAULT '',
    is_deleted INTEGER DEFAULT 0,
    deleted_at TEXT DEFAULT '',
    deleted_by TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS v5_invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    item_type TEXT DEFAULT 'service',
    staff_name TEXT DEFAULT '',
    qty REAL DEFAULT 1.0 CHECK(qty >= 0),
    unit_price REAL DEFAULT 0.0 CHECK(unit_price >= 0),
    line_total REAL DEFAULT 0.0 CHECK(line_total >= 0),
    discount_amount REAL DEFAULT 0.0 CHECK(discount_amount >= 0),
    inventory_item_name TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(invoice_id) REFERENCES v5_invoices(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS v5_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    payment_method TEXT NOT NULL,
    amount REAL DEFAULT 0.0 CHECK(amount >= 0),
    reference_no TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(invoice_id) REFERENCES v5_invoices(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS v5_attendance_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_name TEXT NOT NULL,
    attendance_date TEXT NOT NULL,
    status TEXT NOT NULL,
    in_time TEXT DEFAULT '',
    out_time TEXT DEFAULT '',
    source TEXT DEFAULT 'migration',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS v5_staff_commissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_name TEXT NOT NULL,
    invoice_item_id INTEGER,
    amount REAL DEFAULT 0.0,
    rate_pct REAL DEFAULT 0.0,
    commission_date TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(invoice_item_id) REFERENCES v5_invoice_items(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS v5_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT DEFAULT '',
    action TEXT NOT NULL,
    entity_type TEXT DEFAULT '',
    entity_id TEXT DEFAULT '',
    payload TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS v5_app_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    logged_in_at TEXT DEFAULT (datetime('now')),
    logged_out_at TEXT DEFAULT '',
    status TEXT DEFAULT 'open'
);
