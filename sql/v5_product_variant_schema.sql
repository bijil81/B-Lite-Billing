-- additive foundation for product/variant catalog

CREATE TABLE IF NOT EXISTS v5_brands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    code TEXT DEFAULT '',
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS v5_product_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS v5_catalog_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id INTEGER,
    category_id INTEGER,
    name TEXT NOT NULL,
    base_name TEXT DEFAULT '',
    description TEXT DEFAULT '',
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(brand_id, category_id, name),
    FOREIGN KEY(brand_id) REFERENCES v5_brands(id) ON DELETE SET NULL,
    FOREIGN KEY(category_id) REFERENCES v5_product_categories(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS v5_product_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    variant_name TEXT DEFAULT '',
    unit_value REAL DEFAULT 0.0,
    unit_type TEXT DEFAULT 'pcs',
    pack_label TEXT DEFAULT '',
    bill_label TEXT DEFAULT '',
    sku TEXT DEFAULT '',
    barcode TEXT DEFAULT '',
    sale_price REAL DEFAULT 0.0 CHECK(sale_price >= 0),
    cost_price REAL DEFAULT 0.0 CHECK(cost_price >= 0),
    stock_qty REAL DEFAULT 0.0 CHECK(stock_qty >= 0),
    reorder_level REAL DEFAULT 0.0 CHECK(reorder_level >= 0),
    sale_unit TEXT DEFAULT 'pcs',
    base_unit TEXT DEFAULT 'pcs',
    unit_multiplier REAL DEFAULT 1.0,
    allow_decimal_qty INTEGER DEFAULT 0,
    mrp REAL DEFAULT 0.0,
    gst_rate REAL DEFAULT 0.0,
    cess_rate REAL DEFAULT 0.0,
    hsn_sac TEXT DEFAULT '',
    price_includes_tax INTEGER DEFAULT 1,
    is_weighed INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(product_id, pack_label),
    FOREIGN KEY(product_id) REFERENCES v5_catalog_products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS v5_product_variant_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id INTEGER NOT NULL,
    movement_type TEXT NOT NULL,
    qty_delta REAL NOT NULL,
    qty_unit TEXT DEFAULT '',
    unit_cost REAL DEFAULT 0.0,
    supplier_name TEXT DEFAULT '',
    purchase_ref TEXT DEFAULT '',
    batch_no TEXT DEFAULT '',
    expiry_date TEXT DEFAULT '',
    reference_type TEXT DEFAULT '',
    reference_id TEXT DEFAULT '',
    note TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(variant_id) REFERENCES v5_product_variants(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_v5_product_variants_product_id
    ON v5_product_variants(product_id);

CREATE INDEX IF NOT EXISTS idx_v5_product_variants_pack_label
    ON v5_product_variants(pack_label);

CREATE INDEX IF NOT EXISTS idx_v5_product_variants_sku
    ON v5_product_variants(sku);

CREATE INDEX IF NOT EXISTS idx_v5_product_variants_barcode
    ON v5_product_variants(barcode);

CREATE TABLE IF NOT EXISTS v5_vendors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    phone TEXT DEFAULT '',
    gstin TEXT DEFAULT '',
    address TEXT DEFAULT '',
    opening_balance REAL DEFAULT 0.0 CHECK(opening_balance >= 0),
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS v5_purchase_invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id INTEGER,
    invoice_no TEXT DEFAULT '',
    invoice_date TEXT DEFAULT '',
    gross_total REAL DEFAULT 0.0 CHECK(gross_total >= 0),
    tax_total REAL DEFAULT 0.0 CHECK(tax_total >= 0),
    net_total REAL DEFAULT 0.0 CHECK(net_total >= 0),
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(vendor_id) REFERENCES v5_vendors(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS v5_purchase_invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_invoice_id INTEGER NOT NULL,
    variant_id INTEGER,
    item_name TEXT NOT NULL,
    qty REAL DEFAULT 0.0 CHECK(qty >= 0),
    unit TEXT DEFAULT 'pcs',
    cost_price REAL DEFAULT 0.0 CHECK(cost_price >= 0),
    sale_price REAL DEFAULT 0.0 CHECK(sale_price >= 0),
    mrp REAL DEFAULT 0.0 CHECK(mrp >= 0),
    gst_rate REAL DEFAULT 0.0 CHECK(gst_rate >= 0),
    hsn_sac TEXT DEFAULT '',
    batch_no TEXT DEFAULT '',
    expiry_date TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(purchase_invoice_id) REFERENCES v5_purchase_invoices(id) ON DELETE CASCADE,
    FOREIGN KEY(variant_id) REFERENCES v5_product_variants(id) ON DELETE SET NULL
);
