# Tasks: Save Report Locally and Resume from a Previous Report

**Input**: Design documents from `/specs/002-report-export-resume/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: INCLUDED — mandatory by Constitution Principle V. Use synthetic fixtures from
`tests/conftest.py` only; never real field data; file writes only under pytest `tmp_path`.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested
independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: US1 = save report locally (P1), US2 = resume from a report (P2),
  US3 = merge with evaluations in progress (P3)

## Path Conventions

Package `src/evaluate_kobo_form_images/`, tests in `tests/`. Run checks with `make check`
(forces `UV_PROJECT_ENVIRONMENT=.venv`). If `uv run` stalls on network access, run the tools
with `.venv/Scripts/python.exe -m <tool>` instead.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Branch and configuration; no new dependencies.

- [X] T001 (PR #1 still open → stacked on `001-kobo-account-login`) Create branch `002-report-export-resume` (repository root): from `main` if PR #1 (`001-kobo-account-login`) is merged, otherwise from `001-kobo-account-login`; do not commit yet
- [X] T002 [P] Add `REPORTS_DIR` to `.env.example` as a commented optional line `# REPORTS_DIR=exports` with the comment "Folder where Excel reports are saved (default: exports, relative to the project folder)."
- [X] T003 [P] Confirm `.gitignore` already ignores `/exports/` and `*.xlsx` (add `/exports/` if missing) so saved reports never enter Git

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Filter widget keys needed to reset the view after an import, and the report sheet
helpers shared by export and import.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Give the three filter widgets in `filtered_records` of `src/evaluate_kobo_form_images/app.py` stable keys `filter_questions` (multiselect), `filter_status` (selectbox over `STATUS_FILTERS`) and `filter_submitters` (multiselect) without changing labels or behavior, so later tasks can reset them through `st.session_state` before they render
- [X] T005 In `src/evaluate_kobo_form_images/report.py` export module-level constants `EVALUATIONS_SHEET = "Evaluations"`, `METADATA_SHEET = "Metadata"` and `REASON_COLUMN_PREFIX = "Reason: "`, and use them inside `build_report` instead of the literals (output must stay byte-for-byte equivalent in content: same sheet names and headers)
- [X] T006 Run `make check` (repository root); all existing 64 tests must still pass

**Checkpoint**: Foundation ready.

---

## Phase 3: User Story 1 - Save the Excel report directly to a local folder (Priority: P1) 🎯 MVP

**Goal**: "Export report" writes the `.xlsx` into a chosen local folder and shows the full path; no browser download.

**Independent Test**: Evaluate a few images, set the folder, press "Export report", open the file at the displayed path (quickstart scenarios 1–4).

### Tests for User Story 1

- [X] T007 [P] [US1] Create `tests/test_report_save.py` with tests for `report_file_name(form_file, now)`: `("CIAT_CIV_2_Yield_FORM.xlsx", datetime(2026, 11, 12, 16, 30, 0))` → `"image_evaluation__CIAT_CIV_2_Yield_FORM__20261112-163000.xlsx"`; characters other than letters, digits, `.`, `_`, `-` in the stem are replaced by `_`
- [X] T008 [P] [US1] Add tests in `tests/test_report_save.py` for `save_report(content, folder, form_file, now=...)`: (a) creates a missing nested folder under `tmp_path` and returns the absolute path of a file whose bytes equal `content`; (b) calling it twice with the same `now` returns two different paths, the second ending in `-2.xlsx`, and the first file is unchanged; (c) no `.tmp` file remains after success; (d) a `PermissionError` raised while writing (monkeypatch `Path.write_bytes` or `os.replace`) becomes `ReportSaveError` whose `reason` is "Permission denied (is the file or folder open in another program?)" and leaves no `.tmp` file; (e) an `OSError` from `mkdir` becomes `ReportSaveError` with reason starting "The folder path is not valid or the drive is not available"; (f) a write slower than `timeout` (monkeypatch the internal writer to `time.sleep(1)` with `timeout=0.1`) raises `ReportSaveError` with reason "Saving took too long — the folder may be on a slow or offline drive."; (g) `~` in `folder` is expanded
- [X] T009 [P] [US1] Create `tests/test_app_report.py` (reuse the `app_env` fixture pattern from `tests/test_app_login.py`: synthetic form/export copied to tmp `forms/`/`data/`, env vars `KOBO_FORMS_DIR`, `KOBO_DATA_DIR`, `EVALUATIONS_DIR`, `IMAGE_CACHE_DIR`, `REPORTS_DIR` pointing into `tmp_path`, `KOBO_API_TOKEN=""`, `KoboImageClient.fetch` stubbed to return a small JPEG); test: the sidebar has a text input with key `report_dir` whose default is the absolute `REPORTS_DIR`, there is no `st.download_button`, clicking button key `export_report` writes exactly one `.xlsx` into that folder and a `st.success` containing "Report saved to" and the file path is shown; a second test sets `report_dir` to a path under a file (invalid folder) and asserts an `st.error` starting "Could not save the report to"

### Implementation for User Story 1

- [X] T010 [US1] Implement in `src/evaluate_kobo_form_images/report.py`: `ReportSaveError(Exception)` with attributes `path: Path` and `reason: str` (message `f"Could not save the report to {path}: {reason}"`); `report_file_name(form_file: str, now: datetime) -> str` per T007; `save_report(content: bytes, folder: str | Path, form_file: str, *, now: datetime | None = None, timeout: float = 30.0) -> Path` that expands `~`, resolves to an absolute path, `mkdir(parents=True, exist_ok=True)`, picks the first non-existing name among `<name>.xlsx`, `<name>-2.xlsx`, `<name>-3.xlsx`…, writes to `<final>.tmp` then `os.replace` to the final path inside a single-worker `ThreadPoolExecutor` awaited with `timeout`, deletes the temp file on any failure, and maps errors to the exact reasons of research R3 / T008 (depends on T005)
- [X] T011 [US1] Replace `render_export` in `src/evaluate_kobo_form_images/app.py` with a "4. Report" sidebar section per `contracts/ui-export-import.md`: header "4. Report"; `st.text_input("Save to folder", key="report_dir")` initialized once to the absolute path of `REPORTS_DIR` env var or `exports`; checkbox "Include images not evaluated yet" (default True); button "💾 Export report" (key `export_report`) that, inside `st.spinner("Saving the report…")`, calls `build_report(...)` then `save_report(...)` and stores the outcome in `st.session_state["last_report_path"]` or `["last_report_error"]`; render `st.success(f"Report saved to {path}")` or `st.error(str(error))`; remove `st.download_button` and the `st.session_state.report` bytes cache (also drop the two `st.session_state.pop("report", None)` calls in `render_evaluation_form`); keep the caption "Evaluations autosave to `<path>`." (depends on T010, T004)
- [ ] T012 [US1] (`make check` ✅; manual part pending) Run `make check` and quickstart scenarios 1–4 manually (`specs/002-report-export-resume/quickstart.md`)

**Checkpoint**: MVP — reports land in the chosen folder.

---

## Phase 4: User Story 2 - Resume evaluation from a previously exported report (Priority: P2)

**Goal**: Upload a previous report, restore its evaluations, persist them, and continue on the next pending image after the last evaluated one.

**Independent Test**: Export a report with N evaluations, start with an empty autosave, load the same form/export, import the report → N evaluated and the viewer on the image after the last evaluated one (quickstart scenarios 5–10).

### Tests for User Story 2

- [X] T013 [P] [US2] Create `tests/test_report_import.py` with round-trip tests: build records with `scan_export(export_path, parse_xlsform(form_path))`, evaluate 2 of them in an `EvaluationStore(tmp_path / "a", ...)`, write the report with `build_report(..., include_pending=True)`, then `import_report(io.BytesIO(content), "report.xlsx", records, EvaluationStore(tmp_path / "b", ...))` → `added == 2`, `updated == unchanged == not_matched == 0`, `rejected == []`, the new store contains identical verdict/reasons/comments/evaluator/`evaluated_at`, and a fresh `EvaluationStore` on the same folder reloads them (persisted, FR-009); importing the same bytes again → `added == 0`, `unchanged == 2` (SC-004)
- [X] T014 [P] [US2] Add tests in `tests/test_report_import.py` for matching and rejection: a row whose `Image key` is changed but `Image URL` + `Question name` match is imported (fallback); a row with an unknown key and URL counts in `not_matched`; rows edited to status `Maybe` → rejected "Unknown status 'Maybe'"; `Invalid` with empty reasons → "Invalid without reasons"; reason `Too dark` → "Unknown reason 'Too dark'"; `Evaluated at (UTC)` = `yesterday` → "Invalid evaluation date 'yesterday'"; `Pending` rows are ignored (not rejected); `RejectedRow.row_number` equals the Excel row number
- [X] T015 [P] [US2] Add tests in `tests/test_report_import.py` for file rejection: a workbook without an `Evaluations` sheet raises `ReportImportError("This file is not an evaluation report exported by this app.")`; a report with the `Comments` column deleted raises `ReportImportError("The report is missing required columns: Comments.")`; a non-xlsx byte string raises the "not an evaluation report" error; in all cases the target store is unchanged
- [X] T016 [P] [US2] Add tests in `tests/test_report_import.py` for `resume_target(records, store, last_key)`: returns the first record after `last_key` (export order) without an evaluation; wraps to the first pending record when none follows; returns `None` when all are evaluated; and for `ImportResult.form_mismatch` being `True` when the report `Metadata` `Form file`/`Data file` differ from the records' `form_file`/`data_file`
- [X] T017 [P] [US2] Add AppTest cases in `tests/test_app_report.py`: with 2 evaluations saved and a report exported via the UI, delete the autosave JSON, rerun, upload the report through `st.file_uploader` key `import_report_file` and click button key `import_report`; assert a success message starting "Restored 2 evaluations from", counters show 2 evaluated, `st.session_state["filter_status"] == "All"`, and the current image caption is the record after the last evaluated one; clicking `import_report` again shows `st.info("This report was already imported.")`

### Implementation for User Story 2

- [X] T018 [US2] Add to `src/evaluate_kobo_form_images/evaluation.py` a frozen dataclass `MergeResult(added: int, updated: int, unchanged: int)` and `EvaluationStore.merge(evaluations: Iterable[Evaluation]) -> MergeResult` implementing research R7 exactly: absent → add; present and identical (verdict, reasons, comments, evaluator, evaluated_at) → unchanged; incoming `evaluated_at` strictly newer (compare `datetime.fromisoformat` values, timezone-aware) → replace and count updated; otherwise keep local and count unchanged; never delete; call `self.save()` once at the end only if something changed
- [X] T019 [US2] Create `src/evaluate_kobo_form_images/report_import.py` per `contracts/python-api.md` and `contracts/report-format.md`: `REQUIRED_COLUMNS = ("Image key", "Image URL", "Question name", "Evaluation status", "Comments", "Evaluator", "Evaluated at (UTC)")`; `ReportImportError(Exception)` with `message`; dataclasses `RejectedRow(row_number: int, reason: str)` and `ImportResult` with fields `report_name, report_form_file, report_data_file, form_mismatch, added, updated, unchanged, not_matched, rejected, resume_key, complete`; `read_report(source, file_name)` that opens the workbook read-only (any `openpyxl`/zip error → "This file is not an evaluation report exported by this app."), requires sheet `EVALUATIONS_SHEET`, requires `REQUIRED_COLUMNS` plus at least one of `Invalid reasons` or any `Reason: …` column (message "The report is missing required columns: <comma-separated>."), reads `Metadata` `Form file`/`Data file` when present, and converts rows per the row-handling table of `contracts/report-format.md` (reasons = union of `Invalid reasons` split on `;` stripped and `Reason: <x>` columns equal to `Yes`; statuses compared case-sensitively to `Valid`/`Invalid`/`Pending`; empty status = Pending) (depends on T005)
- [X] T020 [US2] Implement in `src/evaluate_kobo_form_images/report_import.py`: `resume_target(records, store, last_key)` per T016 and `import_report(source, file_name, records, store) -> ImportResult` that reads the report, matches rows by `Image key` then `(Image URL, Question name)` using dicts built once, counts `not_matched`, calls `store.merge(...)` with the matched evaluations (keyed to the matched record's key), computes `form_mismatch`, `resume_key` from the last matched evaluated row in report order and `complete = resume_key is None` (depends on T018, T019)
- [X] T021 [US2] Add the "Resume from a previous report" block to the "4. Report" section of `src/evaluate_kobo_form_images/app.py`: `st.file_uploader("Previous report (.xlsx)", type=["xlsx"], key="import_report_file")` and button "⤴ Import report" (key `import_report`, disabled when no file); on click compute fingerprint `f"{name}:{sha1(content)}"`; if equal to `st.session_state["imported_fingerprint"]` show `st.info("This report was already imported.")`; else call `import_report`, store the result in `st.session_state["import_result"]` and the fingerprint, reset `filter_questions=[]`, `filter_status="All"`, `filter_submitters=[]` and set `st.session_state.target_key = result.resume_key` when not None; catch `ReportImportError` → `st.error(message)`; render the summary per `contracts/ui-export-import.md`: success "Restored {added+updated} evaluations from {name} ({added} added, {updated} updated, {unchanged} unchanged).", warning for `form_mismatch` "This report was created for form '{form}' and data '{data}'. Only matching images were restored.", warning "{n} evaluated rows did not match any image in this export." when `not_matched`, expander "{n} rows were rejected" listing "Row {row}: {reason}", and `st.success("All images in this export are evaluated.")` when `complete` (depends on T020, T011, T004). The import block must run before `filtered_records` renders the filters in the same script run (it lives in the sidebar section rendered from `main()` before the filters).
- [ ] T022 [US2] (`make check` ✅; manual part pending) Run `make check` and quickstart scenarios 5–10 (back up the autosave JSON first; never delete it)

**Checkpoint**: US1 and US2 work independently.

---

## Phase 5: User Story 3 - Merge a report with evaluations already in progress (Priority: P3)

**Goal**: Importing on top of local work keeps everything, with "newer evaluation wins".

**Independent Test**: Local A and B; report with older B and C → A, local B and C kept; summary shows added/updated/unchanged (quickstart scenario 11).

### Tests for User Story 3

- [X] T023 [P] [US3] Add tests in `tests/test_evaluation.py` for `EvaluationStore.merge`: absent → added; identical → unchanged; incoming strictly newer → updated (stored value replaced); incoming older → unchanged and local kept; equal timestamps but different content → unchanged and local kept; merge never removes keys absent from the input; `save()` is not called when nothing changed (assert the JSON file mtime is unchanged)
- [X] T024 [P] [US3] Add a scenario test in `tests/test_report_import.py`: local store has A (2026-11-10) and B (2026-11-12); report has B (2026-11-11, different verdict) and C → after import A, local B and C exist; result `added == 1` (C), `updated == 0`, `unchanged == 1` (B); with report B dated 2026-11-13 → `updated == 1` and stored B equals the report's B

### Implementation for User Story 3

- [X] T025 [US3] Verify `EvaluationStore.merge` (T018) and the import summary (T021) satisfy T023–T024; adjust only if a test fails, keeping research R7 as the rule (depends on T018, T021)

**Checkpoint**: All user stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T026 [P] Update `README.md`: "Using the app" step 5 → "Under **4. Report** choose the folder and press **Export report**; the file is saved there (no browser download). To continue earlier work, upload a previous report and press **Import report**."; "Excel report" section: mention file naming and that reports can be re-imported; Features table row for resume
- [X] T027 [P] Update `CONSTITUTION.md`: §2 scope (local report saving, resume from report), §5 module table (`report.py` save, new `report_import.py`, `EvaluationStore.merge`), §6 structure (`exports/` local-only), decision log rows "2026-11-13 | Save reports server-side to a chosen folder instead of browser download | Browser download ignored the intended folder (feature 002)" and "2026-11-13 | Resume by importing a previous report; newer evaluation wins, never delete | Multi-session / multi-evaluator review"; keep `.specify/memory/constitution.md` consistent (no principle change expected — confirm)
- [X] T028 Run `make check` and `uv run pre-commit run --all-files` (use `SKIP=uv-lock` only if the hook stalls on network, after `uv lock --check --offline` passes)
- [ ] T029 Run the full manual quickstart (`specs/002-report-export-resume/quickstart.md`, scenarios 1–11) with real data, backing up the autosave JSON before scenario 5
- [X] T030 Commit with Conventional Commits (e.g. `feat: save reports locally and resume from a previous report`), human author only, no AI trailers; push the branch and open a PR to `main` (draft until T029 passes)

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (1)** → none. **Foundational (2)** → after Setup; blocks all stories.
- **US1 (3)** → after Foundational.
- **US2 (4)** → after Foundational; its UI (T021) goes into the section created by T011, so implement after US1's T011.
- **US3 (5)** → depends on US2's merge (T018) and summary (T021).
- **Polish (6)** → after the desired stories.

```text
Setup → Foundational → US1 (MVP) → US2 → US3 → Polish
```

### Within each story

Tests first (must fail) → domain code (`report.py` / `evaluation.py` / `report_import.py`) → `app.py` → `make check`.

### Parallel opportunities

- T002 ∥ T003.
- US1 tests T007 ∥ T008 ∥ T009.
- US2 tests T013 ∥ T014 ∥ T015 ∥ T016 ∥ T017.
- US3 tests T023 ∥ T024.
- Docs T026 ∥ T027.
- Sequential (same file `app.py`): T004 → T011 → T021. Sequential (`report_import.py`): T019 → T020.

## Parallel Example: User Story 2

```text
Task: "T013 round-trip import tests in tests/test_report_import.py"
Task: "T017 AppTest import flow in tests/test_app_report.py"
# then: T018 (evaluation.py) → T019 → T020 (report_import.py) → T021 (app.py) → T022
```

## Implementation Strategy

### MVP first (User Story 1)

Phases 1–3: the export bug is fixed and reports land in the chosen folder — shippable alone.

### Incremental delivery

1. US1 → local export (fixes the reported bug).
2. US2 → resume from a report (core of the new request).
3. US3 → merge guarantees on top of local work (tests + verification; logic already in US2).
4. Polish → docs, full quickstart, PR.
