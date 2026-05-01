CREATE VIEW IF NOT EXISTS v5_daily_sales AS
SELECT invoice_date,
       COUNT(*) AS invoice_count,
       SUM(net_total) AS net_total,
       SUM(discount_total) AS discount_total,
       SUM(tax_total) AS tax_total
FROM v5_invoices
GROUP BY invoice_date;

CREATE VIEW IF NOT EXISTS v5_payment_summary AS
SELECT i.invoice_date,
       p.payment_method,
       SUM(p.amount) AS amount_total,
       COUNT(*) AS payment_rows
FROM v5_payments p
JOIN v5_invoices i ON i.id = p.invoice_id
GROUP BY i.invoice_date, p.payment_method;

CREATE VIEW IF NOT EXISTS v5_inventory_balance AS
SELECT legacy_name,
       category,
       current_qty,
       min_qty,
       cost_price,
       sale_price,
       CASE WHEN current_qty <= min_qty THEN 1 ELSE 0 END AS is_low_stock
FROM v5_inventory_items;
