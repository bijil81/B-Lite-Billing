# Architecture Analysis: Current vs Recommended

## Current Architecture (As-Is)

```
┌─────────────────────────────────────────────────────────────────┐
│                         UI LAYER (Tkinter)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  billing.py  │  │ inventory.py │  │ customers.py │          │
│  │  (2000+ LOC) │  │  (800+ LOC)  │  │  (600+ LOC)  │          │
│  │              │  │              │  │              │          │
│  │ • UI widgets │  │ • UI widgets │  │ • UI widgets │          │
│  │ • Business   │  │ • Business   │  │ • Business   │          │
│  │   logic      │  │   logic      │  │   logic      │          │
│  │ • Data access│  │ • Data access│  │ • Data access│          │
│  │ • Validation │  │ • Validation │  │ • Validation │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
         ┌────────────────────┴────────────────────┐
         │                                         │
         ▼                                         ▼
┌─────────────────────┐                 ┌─────────────────────┐
│   LEGACY PATH       │                 │   MODERN PATH (v5)  │
│   ┌──────────────┐  │                 │  ┌──────────────┐   │
│   │  utils.py    │  │                 │  │ services_v5/ │   │
│   │  load_json() │  │                 │  │ BillingSvc   │   │
│   │  save_json() │  │                 │  │ InventorySvc │   │
│   └──────────────┘  │                 │  │ CustomerSvc  │   │
│         │           │                 │  └──────────────┘   │
│         ▼           │                 │         │            │
│  ┌──────────────┐   │                 │         ▼            │
│  │ JSON Files   │   │                 │  ┌──────────────┐   │
│  │ customers.json│  │                 │  │ repositories/│   │
│  │ inventory.json│  │                 │  │ BillingRepo  │   │
│  │ sales_report.csv│ │                 │  │ InventoryRepo│   │
│  └──────────────┘   │                 │  └──────────────┘   │
│                     │                 │         │            │
└─────────────────────┘                 │         ▼            │
          │                             │  ┌──────────────┐   │
          └─────────────────────────────┼──│ db_core/     │   │
                                        │  │ SQLite       │   │
                                        │  └──────────────┘   │
                                        └─────────────────────┘
                                                      │
                                                      ▼
                                            ┌─────────────────────┐
                                            │  SQLite Database    │
                                            │  - v5_invoices      │
                                            │  - v5_customers     │
                                            │  - v5_inventory     │
                                            │  - v5_payments      │
                                            └─────────────────────┘
```

### Problems with Current Architecture

1. **Split Brain:** Two parallel data paths create inconsistency
2. **God Classes:** UI files contain business logic and data access
3. **Circular Dependencies:** `billing.py` ↔ `billing_logic.py`
4. **No Clear Boundaries:** Where does UI end and business logic begin?
5. **Testing Difficulty:** Cannot test business logic without UI

---

## Recommended Architecture (To-Be)

```
┌─────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │BillingFrame  │  │InventoryFrame│  │CustomerFrame │          │
│  │              │  │              │  │              │          │
│  │ • UI widgets │  │ • UI widgets │  │ • UI widgets │          │
│  │ • User input │  │ • User input │  │ • User input │          │
│  │ • Display    │  │ • Display    │  │ • Display    │          │
│  │ • Navigation │  │ • Navigation │  │ • Navigation │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│           │                 │                 │                 │
│           └─────────────────┴─────────────────┘                 │
│                             │                                   │
│           ┌─────────────────┴─────────────────┐                │
│           │         DI Container              │                │
│           │  (injects services into frames)   │                │
│           └─────────────────┬─────────────────┘                │
└─────────────────────────────┼───────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────┐
│                      SERVICE LAYER (Pure Business Logic)         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │BillingService│  │InventorySvc  │  │CustomerSvc   │          │
│  │              │  │              │  │              │          │
│  │ • Validate   │  │ • Stock calc │  │ • VIP status │          │
│  │ • Calculate  │  │ • Reorder    │  │ • Points     │          │
│  │   totals     │  │   alerts     │  │   balance    │          │
│  │ • Apply      │  │ • Batch/     │  │ • Visit      │          │
│  │   discounts  │  │   expiry     │  │   history    │          │
│  │ • Coordinate │  │ • Valuation  │  │ • Segmentation│         │
│  │   transactions│ │              │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│           │                 │                 │                 │
│           └─────────────────┴─────────────────┘                 │
│                             │                                   │
│           ┌─────────────────┴─────────────────┐                │
│           │      Unit of Work Pattern         │                │
│           │   (transaction boundaries)        │                │
│           └─────────────────┬─────────────────┘                │
└─────────────────────────────┼───────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────┐
│                    REPOSITORY LAYER (Data Access)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │BillingRepo   │  │InventoryRepo │  │CustomerRepo  │          │
│  │              │  │              │  │              │          │
│  │ • CRUD ops   │  │ • CRUD ops   │  │ • CRUD ops   │          │
│  │ • Queries    │  │ • Stock      │  │ • Search     │          │
│  │   (parameterized)│ movements │  │ • History    │          │
│  │ • No business│  │ • No business│  │ • No business│          │
│  │   logic      │  │   logic      │  │   logic      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│           │                 │                 │                 │
│           └─────────────────┴─────────────────┘                 │
│                             │                                   │
│           ┌─────────────────┴─────────────────┐                │
│           │        Data Mapper                │                │
│           │   (rows → domain objects)         │                │
│           └─────────────────┬─────────────────┘                │
└─────────────────────────────┼───────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────┐
│                    DATABASE LAYER (SQLite Only)                  │
│           ┌─────────────────┴─────────────────┐                │
│           │   Single Source of Truth          │                │
│           │   - WAL mode for concurrency      │                │
│           │   - CHECK constraints             │                │
│           │   - Foreign keys enforced         │                │
│           │   - Indexed for performance       │                │
│           └───────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    CROSS-CUTTING CONCERNS                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Logging     │  │  Validation  │  │   Security   │          │
│  │  (centralized)│ │  (validators)│  │   (RBAC)     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Backup     │  │   Audit      │  │  Exception   │          │
│  │   (atomic)   │  │   Trail      │  │   Handler    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### Benefits of Recommended Architecture

1. **Single Data Source:** SQLite only, no JSON fallback
2. **Clear Separation:** UI ≠ Business Logic ≠ Data Access
3. **Testable:** Services can be unit tested without UI
4. **Maintainable:** Each layer has single responsibility
5. **Scalable:** Can add caching, queuing, microservices later

---

## Migration Path

### Phase 1: Stabilize (2-3 weeks)
```
Week 1:
  - Remove JSON fallback from billing path
  - Add transaction boundaries to save operations
  - Fix race condition in inventory deduction

Week 2:
  - Replace bare exception handlers
  - Add stock validation
  - Implement discount stacking limits

Week 3:
  - Test all P0 fixes
  - Run on staging database
  - Performance testing
```

### Phase 2: Refactor (4-6 weeks)
```
Week 4-5:
  - Decompose billing.py into components
  - Extract business logic to service layer
  - Break circular dependencies

Week 6-7:
  - Implement Unit of Work pattern
  - Add repository interfaces
  - Dependency injection setup

Week 8:
  - Integration testing
  - Documentation
  - Training
```

### Phase 3: Enhance (8-12 weeks)
```
Week 9-10:
  - Implement audit trail
  - Add credit control
  - Build admin dashboard

Week 11-12:
  - Advanced reporting
  - Mobile app preparation
  - Cloud sync planning
```

---

## File Organization (Recommended)

```
src/
├── presentation/           # UI Layer (Tkinter)
│   ├── billing/
│   │   ├── billing_frame.py
│   │   ├── billing_widgets.py
│   │   └── billing_handlers.py
│   ├── inventory/
│   ├── customers/
│   └── reports/
│
├── services/               # Business Logic
│   ├── billing_service.py
│   ├── inventory_service.py
│   ├── customer_service.py
│   └── report_service.py
│
├── repositories/           # Data Access
│   ├── billing_repo.py
│   ├── inventory_repo.py
│   └── customer_repo.py
│
├── domain/                 # Business Entities
│   ├── invoice.py
│   ├── product.py
│   └── customer.py
│
├── infrastructure/         # Technical Concerns
│   ├── database/
│   │   ├── connection.py
│   │   ├── transaction.py
│   │   └── migrations/
│   ├── logging/
│   ├── security/
│   └── backup/
│
└── shared/                 # Cross-cutting
    ├── validators/
    ├── exceptions/
    └── utils/
```

---

## Key Design Patterns to Implement

### 1. Unit of Work
```python
with UnitOfWork() as uow:
    invoice_id = uow.billing.create_invoice(payload)
    uow.inventory.deduct_stock(payload.items)
    uow.payments.record(payload.payments)
    # Commits all or rolls back on error
```

### 2. Repository
```python
class BillingRepository:
    def get_by_id(self, invoice_id: int) -> Invoice
    def save(self, invoice: Invoice) -> int
    def find_by_date_range(self, from_date, to_date) -> List[Invoice]
```

### 3. Service Layer
```python
class BillingService:
    def __init__(self, billing_repo, inventory_repo, payment_repo):
        # Dependencies injected
    
    def create_invoice(self, payload: dict) -> Invoice:
        # Business logic here
        # No UI code, no SQL
```

### 4. Factory
```python
class InvoiceFactory:
    @staticmethod
    def create_from_bill_frame(frame) -> Invoice:
        # Convert UI data to domain object
```

### 5. Observer (for audit trail)
```python
class AuditObserver:
    def on_invoice_created(self, invoice: Invoice, user: User):
        # Log to audit trail
```

---

## Technology Recommendations

### Keep
- ✅ SQLite (perfect for single-user desktop)
- ✅ Python 3.x (team expertise)
- ✅ Tkinter (stable, no dependencies)

### Add
- 🆕 SQLAlchemy ORM (optional, for cleaner data access)
- 🆕 Dependency injection container (injector or dependency-injector)
- 🆕 Structured logging (structlog)
- 🆕 Schema migration tool (alembic)

### Remove
- ❌ JSON file storage (after migration)
- ❌ CSV for financial data (use SQLite views)
- ❌ Bare exception handlers

---

## Success Metrics

After refactoring, measure:

1. **Code Quality**
   - billing.py < 500 LOC (was 2000+)
   - Test coverage > 80%
   - Cyclomatic complexity < 10 per function

2. **Reliability**
   - Zero data corruption incidents
   - 100% transaction rollback on errors
   - < 1% silent failures

3. **Performance**
   - Bill save < 500ms
   - Report load < 2s (10k invoices)
   - Concurrent users: 10+ without race conditions

4. **Maintainability**
   - New feature development: < 1 week
   - Bug fix turnaround: < 2 days
   - Onboarding new developer: < 1 week

---

**Prepared by:** GitHub Copilot  
**Date:** May 1, 2026  
**Status:** Ready for Engineering Review
