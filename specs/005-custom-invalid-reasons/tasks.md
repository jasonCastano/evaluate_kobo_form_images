---

description: "Task list for feature 005 — custom invalid reasons"
---

# Tasks: Custom Invalid Reasons

**Input**: Design documents from `/specs/005-custom-invalid-reasons/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Included — Constitution Principle V requires pytest tests (Arrange-Act-Assert,
synthetic fixtures only, `tmp_path` for every file) for all new behavior.

**Organization**: Tasks are grouped by user story. Paths are relative to the repository root
(single src-layout package `src/evaluate_kobo_form_images/`).

**Commands**: run tests with `.venv/Scripts/python.exe -m pytest <file> -q`; full gate is
`make check` (Ruff lint + format, `ty`, pytest). Never use field data from `forms/`, `data/`
or `evaluations/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1–US4 from spec.md

---

## Phase 1: Setup

**Purpose**: Baseline and governance before touching code

- [X] T001 Verify the baseline: on branch `005-custom-invalid-reasons` (created from `develop`), run `make check` and record that all existing tests pass before any change
- [X] T002 [P] Amend Principle III in `.specify/memory/constitution.md` from "Closed Evaluation Vocabulary" to "Controlled Evaluation Vocabulary" (verdicts Valid/Invalid stay closed; the four default reasons are fixed, always listed first and cannot be renamed or hidden; evaluators may add local custom reasons that follow the name rules — 1–60 characters, no `;`, no control characters, unique ignoring case and spacing — stored in git-ignored local data, never deleted, only hidden), update the Sync Impact Report and bump Version to 2.0.0 / Last Amended 2026-11-19
- [X] T003 [P] Update `CONSTITUTION.md` §3 Domain rules with the same controlled-vocabulary rule and the catalogue location `evaluations/custom_reasons.json` (overridable with `CUSTOM_REASONS_FILE`), and add decision-log rows dated 2026-11-19: "Allow local custom invalid reasons (Principle III amended, MAJOR)" and "Store custom reasons in `evaluations/custom_reasons.json`, shared by all forms of the installation" (feature 005)

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: Reasons as plain names + the persistent catalogue, needed by every story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational

- [X] T004 [P] Create `tests/test_reasons.py` with tests for the name rules and catalogue core (see [contracts/python-api.md](./contracts/python-api.md), [contracts/custom-reasons-file.md](./contracts/custom-reasons-file.md)): `normalize_reason(" low  LIGHTING ") == "low lighting"`; `clean_reason_name` trims and collapses whitespace and raises `ReasonError` with messages `Enter a reason name.` (empty/whitespace), `Reason names can have at most 60 characters.` (61 chars; exactly 60 accepted), `Reason names cannot contain ';'.`, and for control characters; `ReasonCatalogue(tmp_path / "custom_reasons.json")` with a missing file returns `all_names() == list(DEFAULT_REASONS)` and `load_error is None`; `add("Finger over the lens")` returns the name, writes the file (version 1, `reasons[0]` has `name`, `hidden: false`, `created_at`), and a **new** `ReasonCatalogue` on the same path lists it after the defaults; `add(" low LIGHTING ")` raises `ReasonError("'Low lighting' already exists.")`; adding a duplicate of a custom reason raises; creation order is preserved for three additions; two catalogue instances on the same file each adding one reason keep both (re-read before write); defaults are never written to the file; `reason_widget_id` is stable and differs for different keys
- [X] T005 [P] Update `tests/test_evaluation.py`: an `Evaluation` accepts custom reason names (`["Finger over the lens"]`) and `InvalidReason` members (stored as their string values); duplicate names by key are removed keeping the first; a reason name that breaks the format rules raises `ValueError`; Invalid with no reasons still raises; Valid still clears reasons; `to_dict()["reasons"]` is a list of strings; an existing autosave JSON written with default reasons loads unchanged through `EvaluationStore`

### Implementation for Foundational

- [X] T006 Create `src/evaluate_kobo_form_images/reasons.py` (no Streamlit imports) with `MAX_REASON_LENGTH = 60`, `DEFAULT_REASONS = tuple(r.value for r in InvalidReason)`, `ReasonError(ValueError)` exposing `.message`, `normalize_reason(name) = " ".join(name.split()).casefold()`, `clean_reason_name(name)` (trimmed, inner whitespace collapsed; "1–60 characters, no `;`, no control characters"), `reason_widget_id(name) = sha1(normalize_reason(name).encode()).hexdigest()[:10]`, frozen dataclass `CustomReason(name: str, hidden: bool, created_at: str)`, and `catalogue_path(evaluations_dir)` returning `Path(os.environ["CUSTOM_REASONS_FILE"])` when set, else `evaluations_dir / "custom_reasons.json"`
- [X] T007 Implement `ReasonCatalogue` core in `src/evaluate_kobo_form_images/reasons.py`: `__init__(path)`, private `_read()` that re-reads the file on every call (missing file → no custom reasons; invalid JSON, `version` ≠ 1 or non-list `reasons` → `load_error` set and no custom reasons; individual invalid/duplicate entries skipped and mentioned in `load_error`), private `_write(reasons)` that writes `{"version": 1, "updated_at", "reasons": [...]}` atomically via `<name>.tmp` + `os.replace` with `ensure_ascii=False` and, if the last read was unreadable, first renames the existing file to `custom_reasons.json.unreadable-<YYYYMMDD-HHMMSS>`; public `custom()`, `all_names()` (defaults + all custom incl. hidden), `offered_names(selected=())` (defaults + visible custom + hidden names present in `selected`, in catalogue order), `canonical(name)`, `is_default(name)`, and `add(name)` (clean, check uniqueness by `normalize_reason` across defaults and all custom incl. hidden → `ReasonError("'<existing>' already exists.")`, append with `created_at` = UTC ISO seconds, write)
- [X] T008 Change `Evaluation` in `src/evaluate_kobo_form_images/evaluation.py`: `reasons: list[str]`; in `__post_init__` convert each item with `str()`, validate with `clean_reason_name` (raise `ValueError` with the `ReasonError` message), drop duplicates by `normalize_reason` keeping the first, keep the Invalid-needs-a-reason and Valid-clears rules; `to_dict()` returns the list of names; keep `InvalidReason` as the enum of default reasons with an updated docstring ("default reasons; custom ones live in reasons.py"). Avoid an import cycle: `reasons.py` imports `InvalidReason` from `evaluation.py`, so `evaluation.py` imports the helpers lazily or the name rules move to a tiny shared section at the top of `reasons.py` that does not import `evaluation` (choose one and keep `ty` clean)
- [X] T009 Make `tests/test_reasons.py` and `tests/test_evaluation.py` pass and fix any existing test or module that relied on `Evaluation.reasons` being `InvalidReason` members (`src/evaluate_kobo_form_images/report.py`, `src/evaluate_kobo_form_images/report_import.py`, `tests/test_report.py`, `tests/test_report_import.py`) without changing their behavior yet

**Checkpoint**: Catalogue persists to disk and evaluations accept any well-formed reason name; full suite green

---

## Phase 3: User Story 1 — Add a new invalid reason while evaluating (Priority: P1) 🎯 MVP

**Goal**: From the evaluation form, type a new reason and add it; it appears ticked for the current image without losing the verdict, other reasons or comments.

**Independent Test**: Load the synthetic form/export, mark Invalid, type a comment, add "Finger over the lens" → it is listed and ticked, comment kept; Save → stored evaluation has that reason.

### Tests for User Story 1

- [X] T010 [P] [US1] Create `tests/test_app_reasons.py` (AppTest, no network; reuse the `app_env` fixture pattern from `tests/test_app_report.py` and also `monkeypatch.setenv("CUSTOM_REASONS_FILE", str(tmp_path / "evaluations" / "custom_reasons.json"))`): (a) after loading form + export, the reason checkboxes are the four defaults; (b) select Invalid, type comment "keep me", enter "Finger over the lens" in the "New reason" input and click "➕ Add reason" → a checkbox "Finger over the lens" exists and is checked, the verdict is still Invalid and the comment is still "keep me", the text input is empty, and nothing was saved to the autosave store yet; (c) then click "💾 Save" → the autosave JSON for the record has `reasons == ["Finger over the lens"]`; (d) entering " low LIGHTING " shows the error `'Low lighting' already exists.` and adds no checkbox; (e) empty input shows `Enter a reason name.`

### Implementation for User Story 1

- [X] T011 [US1] In `src/evaluate_kobo_form_images/app.py` create the catalogue once per run with `ReasonCatalogue(catalogue_path(EVALUATIONS_DIR))` in `main()` and pass it to `render_evaluation_form`; show `st.warning(catalogue.load_error)` once per session (flag in `st.session_state`) when set
- [X] T012 [US1] In `render_evaluation_form` (`src/evaluate_kobo_form_images/app.py`) build the checkbox list from `catalogue.offered_names(current.reasons if current else ())` instead of iterating `InvalidReason`; use keys `f"reason_{reason_widget_id(name)}_{record.key}"`; pass `value=` only when that key is not yet in `st.session_state` (avoid the "default value and Session State" warning); `selected` is the list of ticked names
- [X] T013 [US1] Add to the same `st.form` in `src/evaluate_kobo_form_images/app.py` a `st.text_input("New reason", max_chars=60, key=f"new_reason_{record.key}", placeholder="e.g. Finger over the lens")` below the checkboxes, and change the buttons row to three columns: "➕ Add reason" (`form_submit_button`, `on_click=_add_reason_callback`, `args=(catalogue, record.key)`), "💾 Save", "💾 Save & next"; ensure clicking "➕ Add reason" does not run the save branch
- [X] T014 [US1] Implement `_add_reason_callback(catalogue, record_key)` in `src/evaluate_kobo_form_images/app.py`: read `st.session_state[f"new_reason_{record_key}"]`, call `catalogue.add(...)`; on success set `st.session_state[f"reason_{reason_widget_id(name)}_{record_key}"] = True`, clear the text input key, and queue `st.toast(f"Added reason '{name}'.")`; on `ReasonError` store the message in `st.session_state["reason_error"]` and render it with `st.error` under the form on the rerun (then clear it); the verdict, checkbox and comment keys are left untouched (FR-003)
- [X] T015 [US1] Run `tests/test_app_reasons.py` and the existing `tests/test_app_report.py` / `tests/test_app_login.py`; fix regressions caused by the new checkbox keys or button layout

**Checkpoint**: US1 works end-to-end in the UI; reasons are already written to disk (foundation)

---

## Phase 4: User Story 2 — Custom reasons survive closing and reopening the tool (Priority: P1)

**Goal**: Reasons added earlier are listed after the defaults on every later start and for every form; saved evaluations using them show them ticked.

**Independent Test**: Add a reason, start a **new** AppTest (simulated restart) on the same folders, load a form → reason listed; reopen the saved image → ticked.

### Tests for User Story 2

- [X] T016 [P] [US2] Add to `tests/test_app_reasons.py`: (a) restart persistence — after adding and saving with "Finger over the lens", a fresh `AppTest.from_file(APP)` run on the same env lists the reason after the four defaults and shows it checked on the saved record; (b) a second synthetic form/export pair (copy the fixture files under another name into the forms/data folders) also offers the reason; (c) an unreadable `custom_reasons.json` (write `"{not json"`) → app starts, shows the four defaults and a warning containing "custom reasons", and the file content is unchanged
- [X] T017 [P] [US2] Add to `tests/test_reasons.py`: unreadable file is preserved on read; after `add()` on a catalogue whose file was unreadable, a `custom_reasons.json.unreadable-*` file exists with the original bytes and the new file contains only the added reason; a file with `"version": 2` is treated as unreadable; an entry with an invalid name is skipped and `load_error` mentions it while valid entries still load

### Implementation for User Story 2

- [X] T018 [US2] Make the T016/T017 tests pass in `src/evaluate_kobo_form_images/reasons.py` and `src/evaluate_kobo_form_images/app.py` (warning text: `Could not read the custom reasons file (<path>): <detail>. Only the default reasons are shown; the file was not changed.`; after a recovery write: `The unreadable file was kept as <backup name>.`)
- [X] T019 [US2] Confirm `evaluations/custom_reasons.json` is git-ignored (`git check-ignore -v evaluations/custom_reasons.json`) and that `scripts/release_to_main.py` `is_published("evaluations/custom_reasons.json")` is `False`; add that assertion to `tests/test_release_to_main.py`

**Checkpoint**: US1 + US2 = the full owner request (MVP)

---

## Phase 5: User Story 3 — Custom reasons in the Excel report and when resuming (Priority: P2)

**Goal**: Custom reasons get `Reason: <name>` columns and summary counts; importing a report registers unknown reasons instead of rejecting rows.

**Independent Test**: Export with a custom reason → column `Reason: Finger over the lens` = `Yes`; on an empty catalogue import that report → row restored, reason added, summary lists it.

### Tests for User Story 3

- [X] T020 [P] [US3] Add to `tests/test_reasons.py` tests for `report_reasons(catalogue, evaluations)`: defaults first; visible custom next in creation order; a hidden custom reason appears only if some evaluation uses it; a name used by an evaluation but unknown to the catalogue is appended last in first-use order; with `catalogue=None` and default-only evaluations the result equals `list(DEFAULT_REASONS)`
- [X] T021 [P] [US3] Update `tests/test_report.py`: `build_report(..., reasons=[*DEFAULT_REASONS, "Finger over the lens"])` produces header `Reason: Finger over the lens` right after the default reason columns and before `Invalid reasons`; the row with that reason has `Yes`, other rows blank; `Invalid reasons` contains `Finger over the lens`; `Summary by question` has a `Finger over the lens` column with the right count; a custom reason named `Valid` does not change the Valid verdict count; with no custom reasons the `Evaluations` header equals `EVALUATION_COLUMNS` (FR-009)
- [X] T022 [P] [US3] Update `tests/test_report_import.py`: a report containing `Finger over the lens` (in `Invalid reasons` and/or a `Reason: Finger over the lens` column marked `Yes`) imported with an empty `ReasonCatalogue(tmp_path/...)` restores the row (no rejection), adds the reason to the catalogue and returns `new_reasons == ["Finger over the lens"]`; `low lighting` is canonicalized to `Low lighting` and not added; a name with 61 characters rejects the row with `Invalid reason name '<name>'`; reasons used only by rows that match no image are not added; a default-only report gives the same added/updated/unchanged/rejected counts as before; when the catalogue file cannot be written (patch `ReasonCatalogue.ensure` to raise `OSError`) evaluations are still merged and `reasons_error` is set

### Implementation for User Story 3

- [X] T023 [US3] Implement `report_reasons(catalogue, evaluations)` in `src/evaluate_kobo_form_images/reasons.py` per research R6 and `ReasonCatalogue.ensure(names)` (clean each name, skip known keys, append the rest in order with one write, return the added display names)
- [X] T024 [US3] Update `src/evaluate_kobo_form_images/report.py`: add `evaluation_columns(reasons=DEFAULT_REASONS)` and keep `EVALUATION_COLUMNS = evaluation_columns()`; `evaluation_row(record, evaluation, reasons=DEFAULT_REASONS)` writes `Yes` per name in `reasons` (compare by `normalize_reason`); `build_report(..., reasons=None)` uses `reasons or report_reasons(None, evaluations.values())` for the `Evaluations` header/rows and the summary reason columns; keep verdict counts and reason counts in separate `Counter`s; recompute `status_col`/`url_col` from the dynamic header
- [X] T025 [US3] Update `src/evaluate_kobo_form_images/report_import.py`: remove `_VALID_REASONS`; `read_report(source, file_name, catalogue=None)` canonicalizes names with `catalogue.canonical` (or `DEFAULT_REASONS` when `None`), accepts other names that pass `clean_reason_name`, rejects the row with `Invalid reason name '<name>'` otherwise; `import_report(..., catalogue=None)` collects reason names of matched rows, calls `catalogue.ensure(...)` before `store.merge` (catching `OSError`/`ReasonError` into `reasons_error`), and returns `ImportResult` with new fields `new_reasons: list[str]` and `reasons_error: str | None` (defaults `[]`/`None`); update the module docstring ("closed evaluation vocabulary" → "evaluation vocabulary")
- [X] T026 [US3] Wire `src/evaluate_kobo_form_images/app.py`: `_export_block` passes `reasons=report_reasons(catalogue, store.evaluations.values())` to `build_report`; `_import_block` passes `catalogue` to `import_report`; `_render_import_summary` adds `Added invalid reasons: <comma-separated>.` when `new_reasons` is non-empty and `st.warning(reasons_error)` when set
- [X] T027 [US3] Add an AppTest case to `tests/test_app_reasons.py`: with an empty catalogue, importing a synthetic report that uses "Finger over the lens" shows "Added invalid reasons: Finger over the lens" and the reason becomes a checkbox

**Checkpoint**: Reports carry custom reasons both ways; old reports unchanged

---

## Phase 6: User Story 4 — Rename or retire a custom reason (Priority: P3)

**Goal**: Rename custom reasons (updating saved evaluations) and hide/restore them; defaults are read-only.

**Independent Test**: Add "Fingr over lens", save an evaluation with it, rename to "Finger over the lens" → autosave updated; hide another → not offered on new images, still ticked on its saved image and still in the report.

### Tests for User Story 4

- [X] T028 [P] [US4] Add to `tests/test_reasons.py`: `rename("Fingr over lens", "Finger over the lens")` keeps position, `created_at` and `hidden`; renaming to an existing name raises `already exists`; a case/spacing-only rename of the same reason is allowed; renaming or hiding a default raises `ReasonError("Default reasons cannot be changed.")`; `set_hidden(name, True)` removes it from `offered_names()` but `offered_names(["<name>"])` still includes it; restore makes it offered again; `rename_reason_in_stores(tmp_path, old, new)` rewrites only `*__*.json` files that use the old name (by key), leaves `custom_reasons.json` and unrelated stores untouched, and returns the count of rewritten files
- [X] T029 [P] [US4] Add an AppTest case to `tests/test_app_reasons.py`: the sidebar expander "Manage invalid reasons" lists defaults without rename/hide controls; renaming a custom reason updates the checkbox label on a saved image and shows `Renamed 'A' to 'B' in N saved evaluation file(s).`; hiding removes it from a new image's checkboxes but keeps it checked on the saved image

### Implementation for User Story 4

- [X] T030 [US4] Implement `ReasonCatalogue.rename(old, new)` and `ReasonCatalogue.set_hidden(name, hidden)` in `src/evaluate_kobo_form_images/reasons.py` (re-read, validate with `clean_reason_name`, uniqueness excluding the reason itself, defaults → `ReasonError("Default reasons cannot be changed.")`, one atomic write)
- [X] T031 [US4] Implement `rename_reason_in_stores(directory, old, new)` in `src/evaluate_kobo_form_images/reasons.py`: for each `directory.glob("*__*.json")`, load JSON, replace reasons whose `normalize_reason` equals the old key with `new` (deduplicating), and if anything changed write atomically (`.tmp` + `os.replace`) keeping all other fields; return the number of files rewritten
- [X] T032 [US4] Add a "Manage invalid reasons" `st.sidebar.expander` in `src/evaluate_kobo_form_images/app.py` (only logic calls into `reasons.py`): defaults listed with a "default" caption; per custom reason a text input + "Rename" button (callback: `catalogue.rename`, then `rename_reason_in_stores(EVALUATIONS_DIR, old, new)`, then reload the `EvaluationStore`, clear the affected checkbox keys from `st.session_state`, toast the confirmation) and a "Hide"/"Restore" button; hidden reasons shown with "(hidden)"; errors shown with `st.error`
- [X] T033 [US4] Make T028/T029 pass; verify a hidden reason used by a saved evaluation still appears as a `Reason: <name>` column in an exported report (covered by `report_reasons`)

**Checkpoint**: All four stories functional

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T034 [P] Update `README.md` (user guide): in "Using the interface" document the "New reason" box and "➕ Add reason", the "Manage invalid reasons" expander and that custom reasons are stored in `evaluations/custom_reasons.json` (local, per installation, shared by all forms, back it up with your evaluations); in "Excel report reference" document the `Reason: <name>` columns for custom reasons; in "Reports: export and resume" document that importing registers unknown reasons; add a Troubleshooting entry for the unreadable-file warning; keep the "Repository structure" section limited to published paths
- [X] T035 [P] Update `specs/002-report-export-resume/contracts/report-format.md` with a short note linking to `specs/005-custom-invalid-reasons/contracts/report-format.md` for dynamic reason columns
- [X] T036 Run `make check` (Ruff lint + format, `ty`, full pytest) and fix everything until green
- [X] T037 Run the manual validation in [quickstart.md](./quickstart.md) steps 1–6 with the synthetic fixtures (or ask the user to run it with real data) and record the outcome in the PR description
- [X] T038 Commit with Conventional Commits (no AI attribution), push `005-custom-invalid-reasons`, open the PR with `--base develop`, wait for CI; after merge, publishing to `main` is a separate release via `scripts/release_to_main.py` (only `src/`, `tests/`, `README.md` changes will be published)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none; T002/T003 can be done any time before the commit
- **Foundational (Phase 2)**: after T001; blocks all stories
- **US1 (Phase 3)**: after Phase 2
- **US2 (Phase 4)**: after Phase 2; its AppTest cases reuse the US1 UI, so run after US1
- **US3 (Phase 5)**: after Phase 2; independent of US1/US2 in the domain modules (T020–T025); UI wiring T026–T027 after T011
- **US4 (Phase 6)**: after Phase 2; UI T032 after T011
- **Polish (Phase 7)**: after the stories you deliver

### Within Each Story

- Tests first (expect failures), then implementation, then make tests pass
- `reasons.py` before `report.py` / `report_import.py` before `app.py`

### Parallel Opportunities

- T002, T003 (governance docs) in parallel with T004, T005 (tests)
- US3 tests T020, T021, T022 in parallel (three different test files)
- US4 tests T028, T029 in parallel
- T034, T035 in parallel
- After Phase 2, the domain parts of US3 (T020–T025) and US4 (T028, T030, T031) can proceed in parallel with US1 UI work (T010–T015) because they touch different files

## Parallel Example: User Story 3

```text
Task: "T020 report_reasons tests in tests/test_reasons.py"
Task: "T021 dynamic reason columns tests in tests/test_report.py"
Task: "T022 import with unknown reasons tests in tests/test_report_import.py"
```

## Implementation Strategy

### MVP First (US1 + US2)

1. Phase 1 + Phase 2 (catalogue persisted, evaluations accept names)
2. Phase 3 (add from the form) and Phase 4 (persistence checks) → this is the owner's full
   request; stop and validate with quickstart steps 1–3
3. Note: without US3, exported reports already include custom names in the `Invalid reasons`
   text column (after T009), but they get no `Reason: <name>` column and importing such
   reports still rejects those rows; both need US3

### Incremental Delivery

1. MVP (US1 + US2) → demo
2. + US3 → reports and resume fully support custom reasons
3. + US4 → housekeeping (rename / hide)
4. Polish → README, `make check`, PR to `develop`, later release to `main`
