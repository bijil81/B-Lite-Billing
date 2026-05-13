# Critical Issues Summary - B-Lite Billing v6.0

**Priority:** P0 = Block Production | P1 = Fix Within 1 Week | P2 = Fix Within 1 Month

---

## 🔴 P0: BLOCK PRODUCTION DEPLOYMENT

### 1. Dual Storage Model Creates Data Inconsistency
- **Files:** `db.py`, `utils.py`, `billing.py`, `inventory.py`
- **Issue:** System writes to SQLite but reads from JSON on error
- **Risk:** Customers see wrong balances, inventory mismatches
- **Fix:** Remove JSON fallback, migrate all data to SQLite
- **Effort:** 3-5 days

### 2. No Transaction Boundaries on Financial Operations
- **Files:** `billing.py`, `services_v5/billing_service.py`
- **Issue:** Invoice save, inventory deduct, payment record not atomic
- **Risk:** Partial writes → financial data corruption
- **Fix:** Wrap all billing operations in database transactions
- **Effort:** 2-3 days

### 3. Race Condition in Inventory Deduction
- **Files:** `inventory.py`, `services_v5/billing_service.py`
- **Issue:** Concurrent bills can oversell same product
- **Risk:** Negative stock, fulfillment failures
- **Fix:** Use SQL `UPDATE ... WHERE qty >= ?` with row locking
- **Effort:** 1-2 days

### 4. Silent Error Swallowing
- **Files:** 20+ files with `except Exception:` (70+ occurrences)
- **Issue:** Errors logged but ignored, operations continue
- **Risk:** Data corruption undetected, debugging impossible
- **Fix:** Replace with specific exceptions, fail fast, alert users
- **Effort:** 5-7 days

### 5. Missing Stock Validation
- **Files:** `billing.py`, `cart_operations.py`
- **Issue:** Can sell products with zero/negative stock
- **Risk:** Overselling, customer dissatisfaction
- **Fix:** Block sale if `current_qty < sale_qty` (respecting decimal flag)
- **Effort:** 1 day

---

## 🟠 P1: FIX WITHIN 1 WEEK

### 6. Circular Dependencies
- **Files:** `billing.py` ↔ `billing_logic.py`
- **Issue:** Mutual imports create fragile code
- **Risk:** Import errors, testing impossible
- **Fix:** Extract shared logic to neutral module
- **Effort:** 2 days

### 7. God File: billing.py (2000+ lines)
- **Files:** `billing.py`
- **Issue:** Unmaintainable, untestable
- **Risk:** Bug fixes introduce new bugs
- **Fix:** Decompose into focused components
- **Effort:** 5-7 days

### 8. CHECK Constraints Not Applied to Existing DBs
- **Files:** `sql/v5_schema.sql`, `db_core/constraint_migration.py`
- **Issue:** Negative values possible in production data
- **Risk:** Financial data integrity
- **Fix:** Run migration on all existing customer databases
- **Effort:** 2 days (including testing)

### 9. Backup Restore Not Atomic
- **Files:** `backup_system.py`
- **Issue:** File-by-file restore can leave mixed state
- **Risk:** Data corruption after restore
- **Fix:** Use directory swap or transactional restore
- **Effort:** 3 days

### 10. No Discount Stacking Limits
- **Files:** `billing.py`, `discounts.py`, `totals.py`
- **Issue:** Can stack discounts beyond 100%
- **Risk:** Negative bill amounts possible
- **Fix:** Enforce maximum discount cap (e.g., 90%)
- **Effort:** 1 day

### 11. License Lockout Risk
- **Files:** `licensing/license_manager.py`
- **Issue:** Hardware changes trigger lockout
- **Risk:** Business operations halted
- **Fix:** Implement license transfer process, add grace period
- **Effort:** 2 days

### 12. Missing Audit Trail
- **Files:** Multiple (deletes, refunds, adjustments)
- **Issue:** Critical actions not logged with user ID
- **Risk:** Cannot trace fraud/errors
- **Fix:** Add audit logging for all sensitive operations
- **Effort:** 3-4 days

---

## 🟡 P2: FIX WITHIN 1 MONTH

### 13. No Customer Credit Control
- **Files:** `customers.py`, `billing.py`
- **Issue:** Unlimited credit sales possible
- **Risk:** Bad debt accumulation
- **Fix:** Add credit limit field, block sales exceeding limit
- **Effort:** 3 days

### 14. Inventory Valuation Missing
- **Files:** `reports.py`, `inventory.py`
- **Issue:** Cannot report inventory value
- **Risk:** Financial reporting incomplete
- **Fix:** Add cost-based valuation reports
- **Effort:** 4 days

### 15. No Batch/Expiry Tracking Enforcement
- **Files:** `inventory.py`, `purchase_service.py`
- **Issue:** Expired products can be sold
- **Risk:** Customer safety, regulatory compliance
- **Fix:** Block sale of expired batches
- **Effort:** 3 days

### 16. WhatsApp Failures Silent
- **Files:** `whatsapp_helper.py`
- **Issue:** 20+ bare exception handlers
- **Risk:** Customer communication fails unnoticed
- **Fix:** Proper error handling, retry logic, user notification
- **Effort:** 3 days

### 17. No Performance Testing
- **Files:** Test suite
- **Issue:** Unknown behavior under load
- **Risk:** Production slowdowns/crashes
- **Fix:** Load test with 10k invoices, 10 concurrent users
- **Effort:** 4 days

### 18. Cache Invalidation Gaps
- **Files:** `customer_service.py`, `product_catalog_service.py`
- **Issue:** Stale data shown after updates
- **Risk:** Wrong prices, balances shown
- **Fix:** Comprehensive cache invalidation strategy
- **Effort:** 2 days

### 19. CSV Report as Source of Truth
- **Files:** `accounting.py`, `reports.py`
- **Issue:** Revenue calculations read CSV not SQLite
- **Risk:** CSV corruption → wrong financials
- **Fix:** Query SQLite directly
- **Effort:** 2 days

### 20. Role-Based Access Not Enforced
- **Files:** `auth.py`, `main.py`, all UI files
- **Issue:** Staff can access admin functions
- **Risk:** Unauthorized actions
- **Fix:** Enforce role checks on all sensitive operations
- **Effort:** 4 days

---

## Quick Stats

| Priority | Count | Total Effort |
|----------|-------|--------------|
| P0 (Block Production) | 5 | 12-18 days |
| P1 (1 Week) | 7 | 19 days |
| P2 (1 Month) | 8 | 25 days |
| **Total** | **20** | **56-62 days** |

---

## Testing Checklist

Before production deployment, verify:

- [ ] All P0 issues resolved and tested
- [ ] 100+ concurrent bills without race conditions
- [ ] Power failure during save → data integrity maintained
- [ ] Backup restore completes successfully
- [ ] Negative stock blocked in all paths
- [ ] Discount stacking capped at safe level
- [ ] All errors logged with stack traces
- [ ] Audit trail captures sensitive actions
- [ ] License transfer process tested
- [ ] Performance test: 10k invoices loads in <5 seconds

---

## Risk Matrix

| Risk | Probability | Impact | Status |
|------|-------------|--------|--------|
| Data corruption | HIGH | HIGH | ⚠️ Unmitigated |
| Financial loss | MEDIUM | HIGH | ⚠️ Partial |
| Business stoppage | LOW | CRITICAL | ⚠️ Manual process |
| Security breach | MEDIUM | HIGH | ⚠️ Known gaps |
| Compliance violation | LOW | HIGH | ⚠️ Missing controls |

---

**Prepared by:** GitHub Copilot  
**Date:** May 1, 2026  
**Review Required:** Engineering Lead, Product Owner
