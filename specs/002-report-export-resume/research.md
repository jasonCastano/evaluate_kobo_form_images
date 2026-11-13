# Phase 0 Research: Save Report Locally and Resume from a Previous Report

**Feature**: [spec.md](./spec.md) · **Date**: 2026-11-12

## R1. Why the export "did not reach the folder"

- **Finding**: The current export uses Streamlit's `st.download_button`, which hands the bytes to
  the **browser**; the browser saves them to its own download location (usually `Downloads`)
  or asks the user. The app never knew or controlled the target folder, so the report could not
  land in the folder the evaluator expected.
- **Decision**: Replace the download button with a server-side write: the app (which runs on
  the evaluator's computer, spec assumption) writes the `.xlsx` with Python file I/O into a
  folder chosen in the UI and reports the absolute path.
- **Alternatives considered**: browser "File System Access API" / save dialog (needs custom JS
  component, browser-specific) → rejected; keeping download + adding a local save (two paths to
  maintain, the spec removes the button) → rejected.

## R2. Output folder and file naming

- **Decision**:
  - Default folder: `REPORTS_DIR` env var or `exports/` (already git-ignored), resolved against
    the working directory; `~` expanded; the absolute path is shown back to the user.
  - The folder text is kept in `st.session_state` (per session, FR-001).
  - File name: `image_evaluation__<form stem>__<YYYYMMDD-HHMMSS>.xlsx`; if it exists (two
    exports in the same second), append `-2`, `-3`, … (FR-004: never overwrite).
  - Folder created with `mkdir(parents=True, exist_ok=True)` (FR-003).
  - Atomic write: write to `<name>.tmp` in the same folder, then `replace()`; on failure delete
    the temp file.
- **Rationale**: Deterministic, collision-free names; atomic replace avoids half-written files on
  network/synced drives.

## R3. Error reporting and slow/offline folders

- **Decision**: Map exceptions to plain-English reasons (FR-005):
  `PermissionError` → "Permission denied (is the file or folder open in another program?)";
  `FileNotFoundError` / invalid drive → "The folder path is not valid or the drive is not
  available"; `OSError` (other) → "The file system reported: <strerror>". Run the write in a
  worker thread with a 30 s timeout; on timeout show "Saving took too long — the folder may be
  on a slow or offline drive." The UI never blocks indefinitely (edge case).
- **Alternatives considered**: synchronous write only (can freeze on offline network shares)
  → rejected.

## R4. Report format as an import contract

- **Decision**: The import reads the `Evaluations` sheet produced by `report.build_report`
  (v0.1.0 format) and the `Metadata` sheet. Required columns: `Image key`, `Image URL`,
  `Question name`, `Evaluation status`, `Comments`, `Evaluator`, `Evaluated at (UTC)` and the
  reasons — either the `Invalid reasons` text (`"; "`-separated) or the per-reason
  `Reason: <reason>` = `Yes` columns (union of both). Header matching is exact after trimming.
  Missing required columns → reject the file (FR-013).
- **Rationale**: The export already carries everything needed (verdict, reasons, comments,
  evaluator, ISO-8601 UTC date, stable key), so no format change or version bump is required.
- **Alternatives considered**: separate JSON sidecar for resume (users only keep the Excel)
  → rejected.

## R5. Matching report rows to current images

- **Decision**: (1) match `Image key` against `ImageRecord.key` (stable hash of submission
  UUID, sheet, `_index`, question, URL); (2) fallback on `(Image URL, Question name)`; rows
  matching nothing are "not matched" (FR-008, FR-012). Matching uses dictionaries built once
  (O(n)), so 10,000 rows import in well under a second (SC-003).
- **Rationale**: Keys are stable for the same export; the fallback covers re-exports from Kobo
  where row indexes shifted but URLs (attachment IDs) did not.

## R6. Row validation on import

- **Decision**: Skip `Pending` (or empty status) rows silently (not counted as rejected).
  Reject — and list with a reason — rows with: unknown status; `Invalid` without reasons;
  unknown reason text; unparsable `Evaluated at`. Accepted rows become `Evaluation` objects with
  the report's evaluator and original `evaluated_at` (not "now"), preserving history.
- **Rationale**: Principle III (closed vocabulary) — never coerce bad data silently.

## R7. Merge rule (local autosave vs report)

- **Decision**: For each accepted row: absent locally → **added**; present and identical
  (verdict, reasons, comments, evaluator, date) → **unchanged**; present and report date
  strictly newer → **updated**; otherwise keep local (**unchanged**, counted as "kept local").
  Dates compared as timezone-aware datetimes. One single autosave write after the merge
  (FR-009) through a new `EvaluationStore.merge()`; nothing is ever deleted (FR-011).
- **Idempotency**: re-importing the same report yields only "unchanged" (SC-004).

## R8. Resume position

- **Decision**: "Last evaluated image" = the last accepted+matched row in the report's row order.
  Find its index in `scan.records` (export order); target = first record after it with no
  evaluation (after the merge); else the first pending record anywhere; else none → show
  "All images in this export are evaluated." and keep the current image. The UI resets the
  filters (questions = all, status = All, submitters = all) so the target is visible, and sets
  `target_key` (existing navigation mechanism).

## R9. Avoid re-importing on every rerun

- **Decision**: `st.file_uploader` keeps its value across reruns; the app imports only when the
  upload's fingerprint (name + SHA-1 of content) differs from the last processed one stored in
  session state, and only when the evaluator presses **Import report** (explicit action).
- **Rationale**: Prevents repeated merges and position jumps on every interaction.

## R10. Testing

- **Decision**: Unit tests build reports with `build_report` from the synthetic fixtures
  (round-trip: export → import), plus hand-edited workbooks for rejection cases; export tests use
  `tmp_path` and monkeypatched failures (`PermissionError`, timeout). AppTest covers the sidebar
  flow. No new dependencies.
