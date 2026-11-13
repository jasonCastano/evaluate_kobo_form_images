# Phase 1 Data Model: Save Report Locally and Resume from a Previous Report

**Feature**: [spec.md](./spec.md) · **Research**: [research.md](./research.md)

## ReportOutput (export result)

| Field | Type | Rules |
|-------|------|-------|
| `path` | Path | Absolute path of the written file. Name: `image_evaluation__<form stem>__<YYYYMMDD-HHMMSS>[-N].xlsx`; never overwrites an existing file. |
| `rows` | int | Rows written to the `Evaluations` sheet. |

Errors raise `ReportSaveError(path: Path, reason: str)` with a plain-English `reason`
(research R3).

## Evaluation report (input file, existing format)

Sheets used: `Evaluations` (required), `Metadata` (optional, for the form/data warning).

| Column | Required | Use |
|--------|----------|-----|
| `Image key` | yes | Primary match to `ImageRecord.key` |
| `Image URL` | yes | Fallback match (with `Question name`) |
| `Question name` | yes | Fallback match |
| `Evaluation status` | yes | `Valid` \| `Invalid` \| `Pending` (or empty) |
| `Invalid reasons` and/or `Reason: <reason>` | at least one | Reasons; values must be in `InvalidReason` |
| `Comments` | yes | Free text (may be empty) |
| `Evaluator` | yes | Kept as-is |
| `Evaluated at (UTC)` | yes | ISO-8601; must parse for Valid/Invalid rows |
| `Form file`, `Data file` | no | Shown in the mismatch warning |

`Metadata` sheet: two columns `Field`/`Value`; uses `Form file` and `Data file`.

## ImportedRow (internal)

| Field | Type | Notes |
|-------|------|-------|
| `row_number` | int | Excel row (for messages) |
| `record_key` | str | Key of the matched current `ImageRecord` |
| `evaluation` | Evaluation | Built from the row; `evaluated_at` = original report value |

## RejectedRow

| Field | Type | Values |
|-------|------|--------|
| `row_number` | int | Excel row |
| `reason` | str | "Unknown status 'X'", "Invalid without reasons", "Unknown reason 'X'", "Invalid evaluation date 'X'" |

## ImportResult (Import summary)

| Field | Type | Meaning |
|-------|------|---------|
| `report_name` | str | Uploaded file name |
| `report_form_file`, `report_data_file` | str | From `Metadata` (or first row) |
| `form_mismatch` | bool | Report form/data file ≠ loaded ones |
| `added` | int | New evaluations stored |
| `updated` | int | Local evaluations replaced by newer report ones |
| `unchanged` | int | Identical or local newer/equal (kept local) |
| `not_matched` | int | Evaluated rows with no image in the current export |
| `rejected` | list[RejectedRow] | Invalid rows |
| `resume_key` | str \| None | Record to open next (R8); `None` = all evaluated |
| `complete` | bool | No pending images remain |

Invariant: `added + updated + unchanged + not_matched + len(rejected)` = number of non-pending
rows in the report.

## MergeResult (EvaluationStore)

| Field | Type |
|-------|------|
| `added`, `updated`, `unchanged` | int |

Rule (R7): add if absent; replace only if the incoming `evaluated_at` is strictly newer;
equal or older → keep local. Never deletes. One autosave write per merge.

## UI session state (memory only)

| Key | Meaning |
|-----|---------|
| `report_dir` | Output folder text (default `REPORTS_DIR` or `exports`) |
| `last_report_path` / `last_report_error` | Last export outcome to display |
| `imported_fingerprint` | `name + sha1(content)` of the last processed upload |
| `import_result` | Last `ImportResult` for the summary |
| `target_key` | Existing navigation target (set to `resume_key`) |
