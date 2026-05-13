# Membership Wallet Workflow Notes

Date: 2026-05-04

## Current Implemented Behaviour

1. Membership package templates can include two benefits:
   - `discount_pct`: percentage discount for eligible bills.
   - `wallet`: starting wallet balance given with that package.

2. When a membership is assigned:
   - The selected package is saved against the customer phone number.
   - `wallet_balance` is set from the selected package wallet value.
   - `price_paid`, `payment`, `start`, `expiry`, and `status` are saved.

3. When a membership is renewed:
   - Expiry date is extended based on package duration.
   - Status is set to `Active`.
   - Package wallet value is added again to the existing wallet balance.

4. Wallet can be increased from Memberships:
   - Active Members tab: select member, then `Add Wallet`.
   - Wallet Top-up tab: enter phone and amount, then top up.

5. Wallet storage:
   - SQLite table: `v5_customer_memberships.wallet_balance`.
   - Basic wallet adjustment log: `v5_membership_transactions`.

6. Billing currently uses membership discount:
   - Active membership discount is shown in Billing.
   - Discount is applied to service subtotal.
   - Invoice preview shows membership discount.

7. Billing wallet redemption is implemented as an optional payment:
   - `Use Wallet` is default OFF.
   - If enabled, wallet is applied up to the bill payable amount.
   - If `Wallet Rs` is blank, the maximum possible wallet amount is used.
   - If `Wallet Rs` has a value, press `Apply`; only that fixed amount is used, limited by wallet balance and bill payable amount.
   - Wallet reduces the cash/card/UPI amount to collect.
   - Wallet is deducted only after invoice save succeeds.
   - Invoice output shows wallet used and remaining wallet balance.

## Production Gap

Remaining hardening areas:

1. Add a dedicated wallet top-up receipt/sale entry if the business wants wallet top-ups to appear in payment reports immediately.
2. Add refund/reversal workflow for cancelled bills.
3. Add automated tests for duplicate save, insufficient wallet, inactive membership, and split payment.

## Recommended Production Workflow

1. Customer selected in Billing.
2. App detects active membership by phone number.
3. App shows:
   - Package name
   - Discount percentage
   - Wallet available
4. Membership discount applies automatically according to package rules.
5. User can optionally apply wallet:
   - Use full available wallet up to bill payable amount.
   - Or enter a partial wallet amount.
6. Wallet deduction should happen only when bill is saved/finalized.
7. Invoice should show:
   - Subtotal
   - Membership discount
   - Wallet used
   - Final amount paid
   - Wallet balance before/after
8. Wallet transaction should be logged with:
   - Invoice number
   - Customer phone
   - Amount deducted
   - Balance after deduction
   - User/staff who performed the transaction
9. If bill is cancelled/refunded, wallet should be reversed through a transaction log.

## International POS Practice

Wallet should be treated as stored value or prepaid balance, not as a normal discount.
Discount reduces sale price. Wallet reduces payable amount after discount/tax calculation,
depending on local accounting policy.

Common safeguards:

1. Never deduct wallet during preview.
2. Deduct only once on successful bill save.
3. Keep immutable wallet ledger entries.
4. Allow reversal/refund entries instead of editing old ledger rows.
5. Show wallet usage clearly on invoice.
6. Restrict manual wallet adjustment to owner/admin.
7. Support split payment: wallet plus cash/card/UPI.
8. Block wallet redemption for expired/cancelled memberships unless owner overrides.

## Implemented Files

1. `src/blite_v6/billing/wallet_payment.py`
   - Wallet preview calculation.
   - Payable-after-wallet calculation.
   - Payment split builder.

2. `billing.py`
   - Minimal UI wiring only.
   - `Use Wallet` checkbox.
   - Optional `Wallet Rs` partial wallet amount field.
   - Wallet preview label.
   - Paid amount defaults to payable amount after wallet.

3. `src/blite_v6/billing/report_persistence.py`
   - Builds split payments including Wallet.
   - Sends wallet amount and balance information into invoice payload.

4. `services_v5/billing_service.py`
   - Deducts wallet inside invoice DB transaction.
   - Logs `wallet_redeem` transaction with invoice reference.
   - Blocks inactive/expired membership and insufficient balance.
   - Prevents duplicate wallet deduction for the same invoice reference.

5. `print_engine.py`, `print_utils.py`, `src/blite_v6/billing/bill_document.py`
   - Shows wallet used and wallet balance after deduction in invoice output.
