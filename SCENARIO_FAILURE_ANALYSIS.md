# Real Shop Scenario Failure Analysis

**Date:** May 1, 2026  
**Method:** Mental simulation of real-world usage patterns  
**Focus:** Edge cases, race conditions, data corruption scenarios

---

## Scenario 1: Multiple Purchases with Different Costs

### Setup
```
Product: "L'Oréal Shampoo 500ml"
- Purchase 1: Jan 15 - 10 units @ ₹100/unit
- Purchase 2: Feb 20 - 10 units @ ₹120/unit  
- Purchase 3: Mar 10 - 10 units @ ₹110/unit
- Current stock: 30 units
- Sale price: ₹150/unit
```

### Expected Behavior (FIFO Accounting)
1. First sale should deduct from Purchase 1 (₹100 cost)
2. After 10 units sold, cost basis switches to Purchase 2 (₹120)
3. Profit calculation should reflect actual cost of goods sold

### ⚠️ **ACTUAL BEHAVIOR - BREAKS HERE**

#### Problem 1: No Batch Tracking
**File:** `services_v5/billing_service.py:_record_inventory_movement()`
```python
def _record_inventory_movement(self, conn, invoice_no: str, item: dict) -> None:
    variant_id = int(item.get("variant_id", 0) or 0)
    qty = float(item.get("qty", 1.0) or 1.0)
    if variant_id:
        conn.execute(
            "UPDATE v5_product_variants SET stock_qty = COALESCE(stock_qty, 0) - ? WHERE id = ?",
            (qty, variant_id),
        )
        # ❌ No batch identification
        # ❌ No cost basis tracking
        # ❌ Just reduces total quantity
```

**Impact:**
- System has **no idea** which purchase batch was sold
- Cannot calculate **actual profit margin**
- Financial reports show **averaged costs** (wrong for tax purposes)
- **FIFO/LIFO impossible** with current schema

#### Problem 2: Average Cost Drift
**File:** `inventory.py:deduct_inventory_for_sale()`
```python
# Legacy path - still active!
if name in inv:
    inv[name]["qty"] = max(0.0, safe_float(inv[name].get("qty", 0), 0.0) - qty)
    # ❌ Cost remains at whatever value was last set
    # ❌ No weighted average calculation
```

**Real-World Failure:**
```
Shop owner asks: "What's my profit on shampoo this month?"
System calculates: ₹150 - ₹110 (last purchase cost) = ₹40 profit/unit
Reality: Sold first 10 units from ₹100 batch → ₹50 profit/unit
         Next 5 units from ₹120 batch → ₹30 profit/unit
         Average profit: ₹43.33/unit, not ₹40

Result: Wrong business decisions based on inaccurate data
```

#### Problem 3: Stock Valuation Impossible
**File:** `reports.py` - No inventory valuation report exists

**Impact:**
- Cannot answer: "What's my inventory worth?"
- Tax filing requires manual calculation
- Insurance claims lack documentation

### 🚨 **WHERE IT BREAKS**

1. **During Sale:** No batch ID captured in invoice items
2. **During Reporting:** Cost of goods sold calculated from last purchase price
3. **During Tax Season:** Cannot produce FIFO-compliant reports

### Fix Required
```sql
-- Schema needs:
CREATE TABLE v5_purchase_batches (
    id INTEGER PRIMARY KEY,
    variant_id INTEGER,
    purchase_invoice_id INTEGER,
    qty_received REAL,
    qty_sold REAL,  -- Track remaining
    unit_cost REAL,
    purchase_date TEXT,
    batch_no TEXT,
    expiry_date TEXT
);

-- Sale should specify batch:
UPDATE v5_purchase_batches 
SET qty_sold = qty_sold + ? 
WHERE variant_id = ? 
  AND (qty_received - qty_sold) > 0
ORDER BY purchase_date  -- FIFO
LIMIT 1;
```

---

## Scenario 2: Selling Below Cost with Discounts

### Setup
```
Product: "Hair Treatment Serum"
- Cost: ₹500/unit
- Sale Price: ₹600/unit
- Margin: ₹100 (16.67%)

Customer: VIP member
- Membership discount: 10% on services
- Bill discount: ₹200 (manual)
- Points redemption: 500 points = ₹50
- Offer: "Festival Special" - 15% off
- Redeem code: "SAVE100" - ₹100 off
```

### Expected Behavior
1. System should warn if final price < cost
2. Manager approval required for below-cost sales
3. Discount stacking should have maximum cap

### ⚠️ **ACTUAL BEHAVIOR - MULTIPLE FAILURE POINTS**

#### Problem 1: Discount Order Not Canonical
**File:** `src/blite_v6/billing/totals.py:calculate_billing_totals()`

**Current calculation order:**
```python
total = 600
discount = 200          # Manual bill discount
membership_discount = 0 # Only applies to services
points_discount = 50    # After manual discount
offer_discount = ?      # Applied to what remainder?
redeem_discount = ?     # Applied to what remainder?
```

**Issue:** `NEXT_UPDATE_QA_BLUEPRINT.md` admits:
> "Discount order not fully canonical" - ISSUE-007 (marked closed)

**Reality:** Order is enforced but **no maximum cap**

#### Problem 2: Can Stack Beyond 100%
**File:** `src/blite_v6/billing/discounts.py`

**No validation exists for:**
```python
total_discount = manual + membership + points + offer + redeem
if total_discount > total:
    # ❌ No check! Negative bill possible
```

**Real-World Failure:**
```
Scenario:
- Product: ₹600
- Manual discount: ₹200 → ₹400 remaining
- Points: ₹50 → ₹350 remaining  
- Offer 15%: ₹52.50 → ₹297.50 remaining
- Redeem ₹100: → ₹197.50 final

Cost was ₹500, sold for ₹197.50
Loss: ₹302.50 per unit

System shows: "Sale completed successfully ✓"
```

#### Problem 3: Warning System Can Be Bypassed
**File:** `src/blite_v6/billing/profit_warning.py:build_below_cost_warning_state()`

**Warning logic:**
```python
effective_total = round(sale_total * (1.0 - discount_ratio), 2)
should_warn = effective_total + 0.005 < cost_total
```

**Bypass Method:**
1. Add item to cart
2. Apply discounts gradually
3. Warning only triggers on **final item added**
4. Previous items not re-validated

**Real-World Failure:**
```
Cashier workflow:
1. Add Serum (₹600, cost ₹500) → No warning
2. Add Shampoo (₹200, cost ₹150) → No warning
3. Apply ₹200 bill discount → Warning calculates on LAST item only
4. Customer sees total below cost but system doesn't catch it

Result: Entire bill below cost, no warning shown
```

#### Problem 4: Cost Price Not Always Available
**File:** `cart_operations.py:build_cart_item()`

```python
# Cost price copied from variant IF present
for key in ("cost_price", "gst_rate", ...):
    if key in selected_variant:
        item[key] = selected_variant[key]
# ❌ What if variant doesn't have cost_price set?
# ❌ Falls back to nothing → no below-cost warning possible
```

**Real-World Failure:**
```
Product created without cost_price (common in hurry)
- Sale price: ₹600
- Cost: Not set (None/0)
- Sold for: ₹100 after discounts
- Actual cost: ₹500

System: "No warning" (cost is 0, sale is 100, profit! ...wrong)
Reality: ₹400 loss per unit
```

### 🚨 **WHERE IT BREAKS**

1. **During Discount Application:** No running total validation
2. **During Manager Override:** No audit trail of who approved
3. **During Reporting:** Losses not flagged for review
4. **During Inventory Reorder:** System suggests reordering money-losing products

### Fix Required
```python
# Enforce maximum discount cap
MAX_DISCOUNT_RATIO = 0.90  # 90% max

def calculate_totals(items, discounts):
    total = sum(item.price * item.qty for item in items)
    total_discount = sum(discounts)
    
    if total_discount / total > MAX_DISCOUNT_RATIO:
        raise ValidationError(
            f"Total discount cannot exceed {MAX_DISCOUNT_RATIO*100}%"
        )
    
    # Re-validate ALL items after each discount change
    for item in items:
        if item.mode == "products":
            effective_price = item.price * (1 - discount_ratio)
            if effective_price < item.cost_price:
                require_manager_approval(item, effective_price, item.cost_price)
```

---

## Scenario 3: Editing Items After Purchase

### Setup
```
Invoice #INV-2026-0042 created:
- 2x Haircut @ ₹300 = ₹600
- 1x Color Treatment @ ₹800 = ₹800
- Total: ₹1400
- Payment: Cash ₹1400
- Inventory deducted: 1x Color Treatment kit
```

**Customer returns next day:** "I want to change the color treatment to a different one"

### Expected Behavior
1. Original invoice voided/cancelled
2. Inventory restored for returned item
3. New invoice created with corrected items
4. Payment adjusted (refund or additional charge)
5. Audit trail preserved

### ⚠️ **ACTUAL BEHAVIOR - BREAKS COMPLETELY**

#### Problem 1: No Invoice Edit Functionality
**File:** `reports.py`, `billing.py` - No edit function exists

**Current options:**
- Delete invoice (hard delete or soft delete)
- Create new invoice

**Missing:**
- Invoice amendment
- Line item modification
- Partial returns

#### Problem 2: Inventory Not Restored on Delete
**File:** `soft_delete.py:soft_delete_invoice()`

```python
def soft_delete_invoice(invoice_no: str, deleted_by: str = "") -> bool:
    ensure_v5_schema()
    with connection_scope() as conn:
        conn.execute(
            "UPDATE v5_invoices SET is_deleted = 1, deleted_at = ?, deleted_by = ? WHERE invoice_no = ?",
            (now_str(), deleted_by, invoice_no),
        )
        # ❌ No inventory restoration
        # ❌ No loyalty point reversal
        # ❌ No customer visit history update
```

**Real-World Failure:**
```
Day 1: Sell 1x Color Treatment kit
- Stock: 10 → 9

Day 2: Delete invoice (customer complaint)
- Stock: Still 9 ❌
- System thinks item sold
- Physical stock: 10
- System stock: 9

Day 30: Inventory count
- Discrepancy: 1 unit missing
- Staff accused of theft
- Reality: System never restored stock
```

#### Problem 3: Payment Not Reversed
**File:** `services_v5/billing_service.py` - No refund logic

```python
# When invoice deleted:
# ❌ Payment record not reversed
# ❌ Cash drawer not adjusted
# ❌ Loyalty points not deducted
```

**Real-World Failure:**
```
Original invoice:
- Customer earned: 14 loyalty points (₹1400 / 100)
- Payment recorded: Cash ₹1400

After delete:
- Customer still has 14 points ❌
- Cash report shows ₹1400 ❌
- Can redeem points for free products
- Cash count will be short
```

#### Problem 4: No Return Merchandise Authorization (RMA)
**File:** No RMA workflow exists

**Impact:**
- Cannot track returned items
- Cannot process exchanges
- Cannot issue store credit
- Cannot track defective products

### 🚨 **WHERE IT BREAKS**

1. **During Invoice Deletion:** Inventory permanently lost
2. **During Cash Reconciliation:** Cashier appears short
3. **During Customer Dispute:** No audit trail of changes
4. **During Tax Audit:** Deleted invoices missing from reports

### Fix Required
```python
@transaction
def void_invoice(invoice_no: str, reason: str, user: str):
    """Proper invoice voiding with full reversal"""
    
    # 1. Get original invoice
    invoice = billing_repo.get_by_invoice_no(invoice_no)
    
    # 2. Restore inventory
    for item in invoice.items:
        if item.mode == "products":
            inventory_service.restore_stock(
                variant_id=item.variant_id,
                qty=item.qty,
                reference_type="void",
                reference_id=invoice_no,
            )
    
    # 3. Reverse loyalty points
    if invoice.customer_phone:
        customer_service.deduct_points(
            phone=invoice.customer_phone,
            points=invoice.loyalty_earned,
            reason=f"Invoice {invoice_no} voided",
        )
    
    # 4. Mark invoice as voided (not deleted)
    invoice.status = "VOIDED"
    invoice.void_reason = reason
    invoice.voided_by = user
    invoice.voided_at = now()
    billing_repo.save(invoice)
    
    # 5. Create audit entry
    audit_log.log(
        action="INVOICE_VOIDED",
        invoice_no=invoice_no,
        user=user,
        reason=reason,
    )
    
    # 6. Generate void receipt for customer
    generate_void_receipt(invoice)
```

---

## Scenario 4: Deleting Stock and Restoring Items

### Setup
```
Inventory: 50 products in system
- 5 products discontinued (should be deleted)
- 3 products temporarily out of stock
- 2 products with data entry errors
```

**Manager action:** "Delete the discontinued products and fix the errors"

### Expected Behavior
1. Soft delete preserves history
2. Deleted items don't appear in billing
3. Restore function brings back with correct data
4. Sales history preserved

### ⚠️ **ACTUAL BEHAVIOR - DATA CORRUPTION RISK**

#### Problem 1: Soft Delete Not Enforced in Billing
**File:** `billing.py:smart_search()` and `catalog_search.py`

```python
def smart_search(query, mode, inventory_data):
    # Searches inventory
    for name, item in inventory_data.items():
        # ❌ No check for is_deleted flag
        if query.lower() in name.lower():
            results.append(item)
```

**Real-World Failure:**
```
Day 1: Delete "Old Shampoo v1" (discontinued)
- is_deleted = True

Day 2: New cashier bills "Old Shampoo v1"
- Search finds deleted product ✓
- Can add to cart ✓
- Can complete sale ✓

Result: Selling discontinued products that don't exist in inventory
```

#### Problem 2: Restore Doesn't Rebuild Links
**File:** `soft_delete.py:restore_product()`

```python
def restore_product(legacy_name: str) -> bool:
    ensure_v5_schema()
    with connection_scope() as conn:
        conn.execute(
            "UPDATE v5_inventory_items SET is_deleted = 0, deleted_at = '', deleted_by = '' WHERE legacy_name = ?",
            (legacy_name,),
        )
        # ❌ Doesn't restore product variants
        # ❌ Doesn't restore category/brand links
        # ❌ Doesn't restore barcode mappings
```

**Real-World Failure:**
```
Product: "Premium Hair Mask"
- Has 3 variants (100ml, 250ml, 500ml)
- Linked to category "Hair Care"
- Barcode: 8901234567890

Day 1: Delete product
- v5_inventory_items.is_deleted = 1

Day 2: Restore product
- v5_inventory_items.is_deleted = 0
- BUT variants still deleted ❌
- Category link broken ❌
- Barcode lookup fails ❌

Result: Product exists but cannot be billed
```

#### Problem 3: Historical Reports Break
**File:** `reports_data.py:read_report_rows()`

```python
def read_report_rows(from_date, to_date):
    # Reads sales_report.csv
    # ❌ References product names directly
    # ❌ No handling for deleted products
```

**Real-World Failure:**
```
January: Sell "Product A" (100 units)
February: Delete "Product A" (discontinued)
March: Generate Q1 report

Report shows:
- "Product A": 100 units sold
- BUT product doesn't exist in current inventory
- Cannot drill down to product details
- Cannot compare with current products

Result: Historical data orphaned
```

#### Problem 4: No Cascade Delete/Restore
**File:** `soft_delete.py` - Each entity handled separately

```python
# Must manually delete in order:
soft_delete_product(name)  # ❌ No variant deletion
soft_delete_customer(phone)  # ❌ No visit history handling
```

**Real-World Failure:**
```
Delete customer "John Doe":
- v5_customers.is_deleted = 1 ✓
- BUT v5_customer_visits still exist ❌
- BUT v5_loyalty_ledger still exists ❌
- BUT outstanding invoices still reference customer ❌

Result: Orphaned records, foreign key violations possible
```

### 🚨 **WHERE IT BREAKS**

1. **During Billing:** Deleted products still searchable
2. **During Restore:** Incomplete restoration breaks functionality
3. **During Reporting:** Historical data references ghosts
4. **During Migration:** Soft-delete flags not synced between JSON/SQLite

### Fix Required
```python
@transaction
def delete_product_full(legacy_name: str, user: str):
    """Cascading soft delete with validation"""
    
    # 1. Check for outstanding stock
    stock = inventory_repo.get_stock(legacy_name)
    if stock > 0:
        raise ValidationError(
            f"Cannot delete: {legacy_name} has {stock} units in stock. "
            "Dispose of stock first."
        )
    
    # 2. Check for active variants
    variants = variant_repo.list_by_product(legacy_name)
    for variant in variants:
        variant_repo.soft_delete(variant.id, user)
    
    # 3. Soft delete product
    inventory_repo.soft_delete(legacy_name, user)
    
    # 4. Remove from search index
    search_index.remove(legacy_name)
    
    # 5. Mark in product catalog
    product_catalog.mark_discontinued(legacy_name)
    
    # 6. Audit log
    audit_log.log(
        action="PRODUCT_DELETED",
        product_name=legacy_name,
        user=user,
        stock_at_deletion=stock,
    )


@transaction  
def restore_product_full(legacy_name: str, user: str):
    """Cascading restore with validation"""
    
    # 1. Restore product
    inventory_repo.restore(legacy_name, user)
    
    # 2. Restore all variants
    variants = variant_repo.list_deleted_by_product(legacy_name)
    for variant in variants:
        variant_repo.restore(variant.id, user)
    
    # 3. Rebuild search index
    search_index.add(legacy_name)
    
    # 4. Validate links
    if not product_repo.has_category(legacy_name):
        logger.warning(f"Restored {legacy_name} has no category")
    
    # 5. Audit log
    audit_log.log(
        action="PRODUCT_RESTORED",
        product_name=legacy_name,
        user=user,
    )
```

---

## Additional Failure Scenarios

### Scenario 5: Concurrent Users Editing Same Customer

```
Cashier A: Opens customer "Alice" profile
Cashier B: Opens customer "Alice" profile

Cashier A: Updates phone to +91-9876543210, saves ✓
Cashier B: Updates birthday to 1990-05-15, saves ✓
           (overwrites phone change - lost update!)

Result: Customer phone reverted to old value
```

**Fix:** Optimistic locking with version numbers

### Scenario 6: Power Failure During Multi-Step Operation

```
11:59:59 PM - Month-end closing starts
11:59:59 PM - Backup initiated
11:59:59 PM - Report generation starts
12:00:00 AM - POWER FAILURE

All three operations incomplete:
- Backup: 50% done
- Report: CSV half-written
- Closing: Some entries posted, some not

Result: Data corruption, cannot determine state
```

**Fix:** Transactional operations, checkpoint system

### Scenario 7: Date Manipulation for Discounts

```
Smart cashier:
1. Sets system date to 2025-12-31
2. Applies "Year-End Sale" offer (expired in reality)
3. Bills customer at 40% discount
4. Resets date to 2026-05-01

System: "Offer applied successfully ✓"
Reality: Expired offer abused
```

**Fix:** Server-side date validation, offer expiry enforcement

### Scenario 8: Barcode Collision

```
Product A: Barcode 8901234567890 (manually entered)
Product B: Barcode 8901234567890 (auto-generated duplicate)

Cashier scans barcode:
- System finds Product A
- Inventory deducts from Product B
- Sales history shows Product A
- Stock discrepancy: Product B shows sold but physically present

Result: Inventory drift, cannot reconcile
```

**Fix:** Unique constraint on barcode, validation before save

---

## Summary: Critical Breaking Points

| Scenario | Break Point | Impact | Probability |
|----------|-------------|--------|-------------|
| Multiple purchases | No batch tracking | HIGH | CERTAIN |
| Below-cost sales | No discount cap | HIGH | LIKELY |
| Edit after purchase | No reversal logic | CRITICAL | LIKELY |
| Delete/restore stock | Incomplete cascade | MEDIUM | LIKELY |
| Concurrent edits | No locking | MEDIUM | POSSIBLE |
| Power failure | No transactions | CRITICAL | POSSIBLE |
| Date manipulation | Client-side dates | MEDIUM | POSSIBLE |
| Barcode collision | No unique constraint | LOW | RARE |

---

## Recommendations by Priority

### 🔴 IMMEDIATE (This Week)
1. Add maximum discount cap (90%)
2. Validate ALL items when discount changes
3. Enforce soft-delete in search/filter functions
4. Add transaction boundaries to delete operations

### 🟠 SHORT TERM (This Month)
1. Implement batch tracking for inventory
2. Build proper invoice void/return workflow
3. Add cascade delete/restore
4. Implement optimistic locking for concurrent edits

### 🟡 LONG TERM (Next Quarter)
1. FIFO/LIFO cost basis tracking
2. Server-side date validation
3. Barcode uniqueness enforcement
4. Checkpoint system for long operations

---

**Prepared by:** GitHub Copilot  
**Date:** May 1, 2026  
**Status:** Ready for Development Team Review
