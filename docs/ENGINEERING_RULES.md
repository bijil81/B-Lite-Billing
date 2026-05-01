# B-Lite Management Billing V6.0 Engineering Rules

## Source of Truth
- Stable source: `G:\chimmu\Bobys_Salon Billing\Bobys Billing V5.6 Development`
- V6 workspace: `G:\chimmu\Bobys_Salon Billing\B-Lite management_Billing_V6.0`
- Never edit V5.6 during V6 migration unless the owner explicitly asks.
- Copy only the files needed for the current migration step.

## International Standard Quality Bar
- Stability is the first goal. Do not add features unless they directly reduce risk.
- Preserve current business behavior before refactoring structure.
- Every split must have a before/after comparison path.
- Financial logic must be deterministic, covered by focused tests, and free of silent data loss.
- Text encoding must stay UTF-8 safe. No mojibake fixes by guessing.
- Avoid broad silent exception handling in new or edited V6 code.

## Split Workflow
1. Read the full target file and identify natural seams.
2. Copy the original file into V6 before editing.
3. Keep an untouched copy in `legacy_reference` for comparison.
4. Extract only one responsibility at a time.
5. Add focused tests around the extracted behavior.
6. Run tests and compare with the legacy behavior.
7. Record the result in `docs/MIGRATION_LEDGER.md`.

## File Safety
- Do not bulk-copy build outputs, virtual environments, installers, caches, exports, or zip archives.
- Do not rename public APIs until the caller migration is complete.
- Prefer pure functions for billing, totals, tax, discounts, validation, and persistence adapters.
- UI code should call domain logic; it should not own billing math.
- For future updates, put new logic in new focused modules/files whenever practical.
- Do not make already-large legacy wrapper files bigger with new responsibilities.
- Existing large files may receive only small wiring edits, imports, compatibility wrappers, or bug-fix patches needed to call the new module safely.
- If a change genuinely must edit an existing large file, document why in the phase notes before continuing.

## Large File Guard
- Before adding a feature to an existing large file such as `billing.py`, `inventory.py`, `main.py`, `reports.py`, or `salon_settings.py`, check whether the work can live in a focused module under `src/blite_v6/`.
- New UI workflows should prefer a dedicated dialog/view module plus a thin opener method in the legacy wrapper file.
- New validation, parsing, import/export, tax, purchase, stock, billing, or report logic must live in focused service/helper modules unless there is a clear compatibility reason.
- For any large wrapper touched by a phase, record the before/after line count when practical.
- If a large wrapper grows by more than thin wiring, stop and split the new responsibility before continuing.

## Current First Split Target
- `billing.py` is the highest-risk file by size and responsibility.
- First extraction target: billing totals calculation.
- Reason: billing totals affect money, tax, discounts, loyalty points, offers, and redeem codes.
