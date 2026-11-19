# Research: Custom Invalid Reasons

Feature: [spec.md](./spec.md) · Plan: [plan.md](./plan.md)

No `NEEDS CLARIFICATION` remained in the Technical Context; the items below record the
design decisions taken while reading the current code (`evaluation.py`, `report.py`,
`report_import.py`, `app.py`).

## R1. How reasons are represented in an evaluation

- **Decision**: `Evaluation.reasons` becomes `list[str]` (reason display names). The existing
  `InvalidReason` `StrEnum` stays as the list of **default** reasons (`DEFAULT_REASONS`).
  `Evaluation` only checks name *format* (FR-002 format rules), not catalogue membership.
- **Rationale**: `InvalidReason` is a `StrEnum`, so its members already equal their string
  values; stored JSON already contains plain names. Switching to `str` keeps every existing
  autosave file and report readable without migration (FR-009). Membership is not checked in
  `Evaluation` because hidden reasons, renamed reasons and reasons arriving from a report must
  still load.
- **Alternatives considered**: a dynamic `Enum` built at runtime (fragile, breaks typing);
  a `Reason` dataclass inside each evaluation (changes the autosave format for no gain).

## R2. Where the custom reasons are stored

- **Decision**: one JSON file, `custom_reasons.json`, inside `EVALUATIONS_DIR`
  (default `evaluations/`, already git-ignored). Overridable with the `CUSTOM_REASONS_FILE`
  environment variable for tests and unusual setups. Format in
  [contracts/custom-reasons-file.md](./contracts/custom-reasons-file.md).
- **Rationale**: "per installation" (spec Assumptions) and "local data like evaluations"
  (FR-014). `evaluations/` already survives restarts and is excluded from Git and from the
  release allowlist, so no change to `.gitignore` or `scripts/release_to_main.py` is needed.
- **Alternatives considered**: user profile directory (`~/.config`, `%APPDATA%`) — survives
  re-cloning but is invisible to users who back up the project folder and differs per OS;
  inside each per-form autosave file — contradicts "available for every form" (FR-005);
  a tracked config file — violates FR-014 / Principle VI.

## R3. Writing safely and concurrently

- **Decision**: atomic write (temp file + `os.replace`), and **re-read the file before every
  mutation** (add, rename, hide/restore, import-ensure). The catalogue never caches across
  mutations.
- **Rationale**: covers the two-browser-tabs edge case without locks (single evaluator per
  installation, spec Assumptions); same pattern as `EvaluationStore.save`.
- **Unreadable file (FR-013)**: loading returns defaults plus a `load_error` message shown
  once as a warning. The file is left untouched. If the evaluator then adds a reason, the
  unreadable file is first renamed to `custom_reasons.json.unreadable-<YYYYMMDD-HHMMSS>` and a
  new file is written, and the warning says where the old content went.
- **Alternatives considered**: file locking (`msvcrt`/`fcntl`) — platform-specific and
  unnecessary for one evaluator; SQLite — heavier than a short list needs.

## R4. Name rules and equality

- **Decision**: `normalize(name) = " ".join(name.split()).casefold()`. A valid name, after
  trimming and collapsing inner whitespace: 1–60 characters, no `;`, no control characters.
  Uniqueness is checked on `normalize()` across defaults and all custom reasons, hidden ones
  included. The stored display name is the trimmed, whitespace-collapsed text as typed.
- **Rationale**: matches FR-002 and the "` low LIGHTING `" acceptance scenario. `;` is the
  separator of the report's `Invalid reasons` column. Control characters break Excel cells.
- **Report import canonicalization**: a reason name from a report that normalizes to a known
  reason is mapped to the known display name (e.g. `low lighting` → `Low lighting`).

## R5. Adding a reason from inside the evaluation `st.form`

- **Decision**: put the "New reason" text input **inside** the existing evaluation form,
  together with a third submit button "➕ Add reason". Its `on_click` callback validates and
  stores the name, sets the new reason's checkbox key to `True` in `st.session_state`, and
  clears the text input; the verdict / checkboxes / comments widgets keep their keyed state, so
  nothing typed is lost (FR-003). The evaluation is **not** saved by this button.
- **Rationale**: a widget outside an `st.form` triggers a rerun that discards unsubmitted form
  values; a form submit button sends them all, and callbacks are the only place where
  widget state can be modified before the widgets are recreated (same technique already used
  for the Kobo sign-in in feature 001).
- **Checkbox keys**: change from `reason_{enum name}_{record}` to
  `reason_{sha1(normalize(name))[:10]}_{record}` so any custom name yields a safe, stable key.
  When a key already exists in `session_state`, the checkbox is created without `value=` to
  avoid Streamlit's "default value and Session State" warning.
- **Alternatives considered**: `st.dialog` / popover outside the form (loses unsubmitted
  values); a separate page (breaks flow, SC-001).

## R6. Which reasons appear as report columns

- **Decision**: `report_reasons(catalogue, evaluations)` = defaults (fixed order) + visible
  custom reasons (creation order) + any other reason used by an evaluation in the report
  (hidden custom reasons first in catalogue order, then names unknown to the catalogue in
  first-use order). Used for the `Reason: <name>` columns of `Evaluations` and the reason
  columns of `Summary by question`.
- **Rationale**: FR-007 / FR-011 (hidden but used reasons still exported). With no custom
  reasons the column list is exactly today's (FR-009, SC-005).
- **Summary-sheet collision**: the summary currently counts verdicts and reasons in one
  `Counter`, so a custom reason named "Valid" or "Pending" would merge with a verdict count.
  Verdicts and reasons get separate counters.

## R7. Importing reports with unknown reasons

- **Decision**: `read_report` accepts any reason name that passes the format rules (R4) and
  canonicalizes known ones; names that fail the rules reject the row
  (`Invalid reason name '<name>'`). `import_report` takes the catalogue, calls
  `catalogue.ensure(names)` for reasons used by **matched** rows only, and returns
  `new_reasons` in `ImportResult`, shown in the import summary.
- **Rationale**: FR-008, SC-004. Reasons from unmatched rows are not added so an unrelated
  report does not clutter the list.
- **Order**: ensure → merge. If writing the catalogue fails, the import still merges
  (evaluations are the priority) and the summary warns that the reasons were not saved.

## R8. Rename and hide (P3)

- **Decision**: `rename_reason(catalogue, directory, old, new)` renames in the catalogue and
  rewrites every autosave file (`*__*.json` in `EVALUATIONS_DIR`) that uses the old name,
  each with the existing atomic write; the in-memory `EvaluationStore` is reloaded afterwards.
  Hide/restore only flip a `hidden` flag. UI: a "Manage invalid reasons" expander in the
  sidebar listing custom reasons with rename and hide/restore controls. Defaults are listed
  read-only.
- **Rationale**: FR-010–FR-012. Rewriting stores keeps old evaluations consistent with the
  new name and with later reports. Already exported Excel files are not touched.
- **Alternatives considered**: keeping an alias map instead of rewriting (more moving parts,
  reports would show old names unless resolved everywhere).

## R9. Constitution impact

- **Decision**: amend Principle III from "Closed Evaluation Vocabulary" to
  "Controlled Evaluation Vocabulary": verdicts stay closed; the four default reasons are fixed
  and always first; evaluators may add local custom reasons that follow the name rules and are
  never deleted (only hidden). This is a MAJOR amendment (principle redefined) → Spec Kit
  constitution 2.0.0; `/CONSTITUTION.md` §3 and decision log updated in the same commit.
- **Rationale**: the owner explicitly requested extensible categories; Principle III itself
  says changing the list is a MAJOR change.
