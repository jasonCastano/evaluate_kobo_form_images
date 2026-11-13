# Implementation Plan: Save Report Locally and Resume from a Previous Report

**Branch**: `002-report-export-resume` | **Date**: 2026-11-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-report-export-resume/spec.md`

## Summary

The Excel export currently goes through the browser download, which never lands in the
evaluator's chosen folder. Replace it with a server-side write: the app (running on the
evaluator's computer) saves the report into a folder typed in the sidebar (default `exports/`),
with timestamped, never-overwritten names, atomic writes, a 30 s guard for slow drives and
plain-English errors. Add "Resume from a previous report": the uploaded report's `Evaluations`
sheet is validated against the existing export format, rows are matched to current images by
`Image key` (fallback: URL + question), merged into the autosave store with a
"newer evaluation wins, never delete" rule, and the viewer jumps to the first pending image after
the last evaluated row of the report. Imported evaluations are persisted immediately, so every
later report includes them.

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: Streamlit 1.67, openpyxl — no new dependencies

**Storage**: Local files: Excel reports in the chosen folder; existing JSON autosave per
(form, data export) extended with a bulk `merge()`

**Testing**: pytest (export → import round-trip with synthetic fixtures, merge rules, rejection
cases, save failures via monkeypatch) + Streamlit AppTest for the sidebar

**Target Platform**: Local Streamlit app on the evaluator's computer (Windows primarily)

**Project Type**: Single Python package (src-layout) with a Streamlit UI

**Performance Goals**: Export of 10k rows saved in a few seconds; import of 10k rows + resume
< 1 min end-to-end (SC-003), matching O(n)

**Constraints**: Never overwrite reports; never delete evaluations; UI never blocks forever on
slow folders; English only; report column format unchanged (import contract)

**Scale/Scope**: Exports up to ~10k images; one evaluator per session

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| I. Human judgment, traceability | Report format and traceability columns unchanged; imported evaluations keep original evaluator and date | ✅ |
| II. No image silently dropped | Unmatched and rejected rows counted and listed in the import summary | ✅ |
| III. Closed evaluation vocabulary | Import rejects unknown statuses/reasons and Invalid-without-reasons | ✅ |
| IV. Logic outside the UI | Save in `report.py`, import/merge/resume in `report_import.py` + `evaluation.py`; `app.py` renders | ✅ |
| V. Test-backed quality gates | Round-trip, merge, rejection, save-failure and AppTest tests; `make check` | ✅ |
| VI. Data protection | Reports go to the git-ignored `exports/` by default; no credentials in reports | ✅ |
| VII. English only | All strings in contracts are English | ✅ |
| VIII. Human authorship | Unchanged | ✅ |

**Post-design re-check**: ✅ all gates pass; no complexity to justify.

## Project Structure

### Documentation (this feature)

```text
specs/002-report-export-resume/
├── plan.md
├── research.md          # R1–R10 decisions
├── data-model.md        # ReportOutput, ImportResult, MergeResult, session state
├── quickstart.md        # 11 manual scenarios
├── contracts/
│   ├── report-format.md     # Excel report as export⇄import contract
│   ├── python-api.md        # report / report_import / evaluation interfaces
│   └── ui-export-import.md  # sidebar "4. Report" section
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
src/evaluate_kobo_form_images/
├── report.py            # CHANGED: report_file_name, save_report, ReportSaveError
├── report_import.py     # NEW: read_report, import_report, resume_target, ImportResult
├── evaluation.py        # CHANGED: MergeResult, EvaluationStore.merge
└── app.py               # CHANGED: "4. Report" section (folder, export, import, summary)

tests/
├── test_report_save.py      # NEW
├── test_report_import.py    # NEW
├── test_evaluation.py       # CHANGED: merge rules
└── test_app_report.py       # NEW: AppTest export/import flow
```

**Structure Decision**: Same single package. Docs to update in the implementation commit:
`README.md` (Using the app, Excel report), `CONSTITUTION.md` (§2 scope, §5 modules, decision
log), `.env.example` (`REPORTS_DIR`).

**Branching note**: this feature builds on `001-kobo-account-login` (not yet merged). Create
`002-report-export-resume` from `main` after PR #1 is merged, or stack it on the 001 branch.

## Complexity Tracking

No constitution violations.
