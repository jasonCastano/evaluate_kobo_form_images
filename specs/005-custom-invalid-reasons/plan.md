# Implementation Plan: Custom Invalid Reasons

**Branch**: `005-custom-invalid-reasons` | **Date**: 2026-11-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-custom-invalid-reasons/spec.md`

## Summary

Let evaluators add their own invalid reasons next to the four defaults, keep them permanently
on the installation, and carry them through the Excel report and report import. Technically:
`Evaluation.reasons` becomes a list of names (`InvalidReason` remains the defaults); a new
`reasons.py` module owns a `ReasonCatalogue` persisted as `evaluations/custom_reasons.json`
(atomic writes, re-read before each change); the report builds its reason columns from the
catalogue plus the reasons actually used; report import accepts and registers unknown reasons;
the evaluation form gains an "➕ Add reason" submit button whose callback preserves everything
typed; a sidebar expander renames / hides custom reasons. Principle III is amended (MAJOR).

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: Streamlit 1.67, openpyxl (existing); no new dependencies

**Storage**: local JSON files — new `evaluations/custom_reasons.json`; existing per-form
autosave `evaluations/<form>__<data>.json` (format unchanged)

**Testing**: pytest (+ `streamlit.testing.v1.AppTest` for UI), synthetic fixtures only;
`make check` (Ruff, ty, pytest)

**Target Platform**: local Streamlit app on Windows / macOS / Linux

**Project Type**: single-package desktop-style web app (src-layout)

**Performance Goals**: adding a reason re-renders in < 1 s; catalogue holds ≤ ~100 reasons;
rename rewrites all autosave files in < 2 s for typical folders (≤ 50 files)

**Constraints**: no data loss (atomic writes, never delete reasons or unreadable files);
reports without custom reasons byte-for-byte equivalent in structure to today's; English UI

**Scale/Scope**: one evaluator per installation; 4 user stories (2×P1, P2, P3); ~5 modules
touched

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Human judgment, full traceability | ✅ | Reasons are chosen by humans; traceability columns unchanged. |
| II. No image silently dropped | ✅ | Matching untouched. |
| III. Closed evaluation vocabulary | ⚠️ **Amend (MAJOR)** | The feature makes the reason list extensible. Justified below; principle redefined as "Controlled evaluation vocabulary" (verdicts closed, defaults fixed and first, custom reasons local, validated, never deleted). Constitution → 2.0.0, `/CONSTITUTION.md` §3 + decision log in the same commit. |
| IV. Logic outside the UI | ✅ | All rules in `reasons.py` / `report*.py`; `app.py` only wires widgets and callbacks. |
| V. Test-backed quality gates | ✅ | New `tests/test_reasons.py`, `tests/test_app_reasons.py`; updated report/import/evaluation tests; `make check`. |
| VI. Data protection | ✅ | Catalogue lives in git-ignored `evaluations/`; not in the release allowlist; tests use `tmp_path`. |
| VII. English only | ✅ | UI text and docs in English; reason names are user data. |
| VIII. Human authorship only | ✅ | No attribution; commits by the maintainer. |

**Post-design re-check (after Phase 1)**: unchanged — the only deviation is the planned,
justified Principle III amendment.

## Project Structure

### Documentation (this feature)

```text
specs/005-custom-invalid-reasons/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── custom-reasons-file.md
│   ├── report-format.md
│   ├── python-api.md
│   └── ui.md
├── checklists/requirements.md
└── tasks.md              # /speckit-tasks
```

### Source Code (repository root)

```text
src/evaluate_kobo_form_images/
├── reasons.py            # NEW: name rules, ReasonCatalogue, rename across stores, report_reasons
├── evaluation.py         # Evaluation.reasons -> list[str]; InvalidReason = defaults
├── report.py             # dynamic reason columns; separate verdict/reason counters in summary
├── report_import.py      # accept/canonicalize/register reasons; ImportResult.new_reasons
└── app.py                # Add-reason button in the form; Manage reasons expander; wiring

tests/
├── test_reasons.py       # NEW
├── test_app_reasons.py   # NEW (AppTest)
├── test_evaluation.py    # updated
├── test_report.py        # updated
└── test_report_import.py # updated

README.md                         # user guide: adding / managing reasons, report columns
CONSTITUTION.md                   # §3 domain rules + decision log
.specify/memory/constitution.md   # Principle III → 2.0.0
```

**Structure Decision**: keep the existing single src-layout package; add one domain module
(`reasons.py`) so the catalogue logic stays testable without Streamlit (Principle IV).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle III (closed reason list) redefined | Owner requires evaluators to add permanent categories | Keeping the closed list and using comments makes problems uncountable in the report (spec US1 rationale); a developer-edited list would need a release for each new category |
