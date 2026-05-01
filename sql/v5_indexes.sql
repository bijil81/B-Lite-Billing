CREATE INDEX IF NOT EXISTS idx_v5_customers_name
ON v5_customers(name);

CREATE INDEX IF NOT EXISTS idx_v5_customers_phone
ON v5_customers(legacy_phone);

CREATE INDEX IF NOT EXISTS idx_v5_customer_visits_customer
ON v5_customer_visits(customer_id, visit_date);

CREATE INDEX IF NOT EXISTS idx_v5_loyalty_customer
ON v5_loyalty_ledger(customer_id, created_at);

CREATE INDEX IF NOT EXISTS idx_v5_users_role
ON v5_app_users(role, active);

CREATE INDEX IF NOT EXISTS idx_v5_staff_active
ON v5_staff(active, display_name);

CREATE INDEX IF NOT EXISTS idx_v5_appointments_date
ON v5_appointments(appointment_date, appointment_time, status);

CREATE INDEX IF NOT EXISTS idx_v5_inventory_active
ON v5_inventory_items(active, legacy_name);

CREATE INDEX IF NOT EXISTS idx_v5_inventory_movements_item
ON v5_inventory_movements(item_id, created_at);

CREATE INDEX IF NOT EXISTS idx_v5_invoices_date
ON v5_invoices(invoice_date, invoice_no);

CREATE INDEX IF NOT EXISTS idx_v5_invoices_customer_date
ON v5_invoices(customer_phone, invoice_date);

CREATE INDEX IF NOT EXISTS idx_v5_invoices_name_date
ON v5_invoices(customer_name, invoice_date);

CREATE INDEX IF NOT EXISTS idx_v5_invoice_items_invoice
ON v5_invoice_items(invoice_id);

CREATE INDEX IF NOT EXISTS idx_v5_invoice_items_name
ON v5_invoice_items(item_name);

CREATE INDEX IF NOT EXISTS idx_v5_payments_invoice
ON v5_payments(invoice_id, payment_method);

CREATE INDEX IF NOT EXISTS idx_v5_payments_method_invoice
ON v5_payments(payment_method, invoice_id);

CREATE INDEX IF NOT EXISTS idx_v5_attendance_staff_date
ON v5_attendance_sessions(staff_name, attendance_date);

CREATE INDEX IF NOT EXISTS idx_v5_commissions_staff
ON v5_staff_commissions(staff_name, commission_date);

CREATE INDEX IF NOT EXISTS idx_v5_memberships_phone
ON v5_customer_memberships(customer_phone, status);

CREATE INDEX IF NOT EXISTS idx_v5_redeem_code_active
ON v5_redeem_codes(active, used);

CREATE INDEX IF NOT EXISTS idx_v5_expenses_date
ON v5_expenses(expense_date, category);
