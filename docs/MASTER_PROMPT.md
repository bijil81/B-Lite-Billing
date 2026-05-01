# V6 Master Prompt

You are working on `B-Lite management_Billing_V6.0`, a safe next-version migration of the stable V5.6 billing app.

Primary mission:
- Keep the current app behavior stable.
- Find and fix bugs without breaking working workflows.
- Split oversized files into maintainable modules.
- Preserve encoding quality and prevent mojibake.
- Use tests, comparisons, and migration notes for every risky step.

Operating discipline:
- Treat `Bobys Billing V5.6 Development` as read-only source of truth.
- Work only inside `B-Lite management_Billing_V6.0`.
- Before splitting any file, read the relevant source carefully.
- Prefer small, reversible changes with focused verification.
- Do not introduce new features unless they are needed for stability, testing, or safe migration.
- Every financial calculation change needs explicit tests.
- New update work should create focused new modules/files for new logic whenever practical.
- Do not grow existing large wrapper files with new responsibilities; use them mainly for thin wiring to the new modules.
- For large files, prefer a dedicated module under `src/blite_v6/` and leave only small imports, callbacks, and compatibility wrappers in the legacy file.
- When touching a large wrapper, check whether line count is increasing materially; split first if it is.

Definition of done for each migration step:
- Original file copied or referenced.
- Extracted module has clear responsibility.
- Tests prove the extracted behavior.
- Legacy comparison is documented.
- Known risks are written down before moving to the next file.
