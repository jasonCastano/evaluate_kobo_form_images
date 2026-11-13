# Tasks: Up-to-date Repository and Detailed README User Guide

**Input**: Design documents from `/specs/003-readme-user-guide/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: No code changes, so no new pytest tests. Verification is a scripted check of README
strings and links (Phase 6) plus the existing `make check`, which must stay green.

**Organization**: Tasks are grouped by user story. The repository merge (prerequisite for writing
the README on top of the final code) is in the Foundational phase; User Story 3 delivers and
verifies the README pull request on `main`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files / sections, no dependency on incomplete tasks)
- **[Story]**: US1 = interface guide (P1), US2 = how it works + reference + troubleshooting (P2),
  US3 = repository up to date (P3)

## Path Conventions

Repository root `D:\croppix\evaluate_form_images`. Use `gh` (authenticated as the maintainer)
for PR operations. If `uv run` stalls on network access, run tools with
`.venv/Scripts/python.exe -m <tool>`.

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Verify preconditions in the repository root: `git status` shows only the untracked `specs/003-readme-user-guide/`; current branch `002-report-export-resume` is pushed (`git status -sb` shows no "ahead"); `gh pr checks 1` and `gh pr checks 2` are all successful. Stop and report if any check fails.

---

## Phase 2: Foundational (Blocking Prerequisites) — merge PR #1 and #2 into `main`

**Purpose**: Bring `main` to the code the README will document (spec FR-013, FR-014; procedure in `contracts/merge-procedure.md`).

**⚠️ CRITICAL**: The README branch must be created from `main` after these merges.

- [X] T002 Mark PR #1 ready and merge it with a merge commit: `gh pr ready 1` then `gh pr merge 1 --merge --delete-branch --subject "feat: sign in to Kobo from the sidebar (#1)" --body ""`; never use `--admin`, never add `Co-authored-by` text
- [X] T003 (deleting the base branch with --delete-branch closed #2; recovered by re-pushing `001-kobo-account-login` at d838b57, `gh pr reopen 2`, `gh pr edit 2 --base main`, then deleting the branch again) Confirm PR #2 was retargeted to `main` (`gh pr view 2 --json baseRefName --jq .baseRefName` = `main`); if not, run `gh pr edit 2 --base main`
- [X] T004 Wait for PR #2 checks on the new base until all are successful (`gh pr checks 2 --watch`); stop and report if any fails
- [X] T005 Mark PR #2 ready and merge it: `gh pr ready 2` then `gh pr merge 2 --merge --delete-branch --subject "feat: save reports locally and resume from a previous report (#2)" --body ""`
- [X] T006 Sync locally: `git fetch origin --prune`, `git checkout main`, `git pull --ff-only`; delete the merged local branches `001-kobo-account-login` and `002-report-export-resume` with `git branch -d` (not `-D`); confirm `src/evaluate_kobo_form_images/kobo_auth.py` and `report_import.py` exist on `main`
- [X] T007 Run `make check` on `main` (all tests green) and confirm authors with `git log --format='%an' origin/main | sort -u` → only "Jason Alejandro Castaño"
- [X] T008 Create branch `003-readme-user-guide` from the updated `main` (`git checkout -b 003-readme-user-guide`); the untracked `specs/003-readme-user-guide/` folder carries over

**Checkpoint**: `main` contains features 001 + 002; README work can start.

---

## Phase 3: User Story 1 - A new evaluator learns to use the interface from the README alone (Priority: P1) 🎯 MVP

**Goal**: A first-time evaluator can install, start, sign in, load files, evaluate, export and resume using only the README.

**Independent Test**: A person who never used the app follows the README end to end in < 30 minutes (quickstart §4).

- [X] T009 [US1] Restructure `README.md` skeleton per `data-model.md` (sections 1–14 in this order: Overview, Table of contents, Features, How it works, Getting started, Using the interface, Kobo account, Reports: export and resume, Excel report reference, Configuration, Troubleshooting, Quality and automation, Repository structure, Contributing, License), keeping the existing badges header; update the Table of contents anchors to the new headings
- [X] T010 [US1] Rewrite "Getting started" in `README.md`: prerequisites (Python 3.13+, uv, Git, a Kobo account with access to the project; `make` optional); install with `make dev` or `$env:UV_PROJECT_ENVIRONMENT=".venv"; uv sync; uv run pre-commit install`; optional `Copy-Item .env.example .env`; start with `.\.venv\Scripts\evaluate-kobo-images.exe` (Windows) or `make run` / `uv run evaluate-kobo-images`; app URL `http://localhost:8501`; stop with Ctrl+C; a note "If this computer defines a global `UV_PROJECT_ENVIRONMENT`, uv may install into another environment — use `make` or set `$env:UV_PROJECT_ENVIRONMENT=\".venv\"` first"
- [X] T011 [US1] Write "Using the interface" in `README.md`: a text map of the screen (sidebar: `1. Kobo form`, `2. Collected data`, `3. Kobo account`, `Evaluator name`, `4. Report`; main area: title, form/data caption, counters `Image questions in form`/`Images collected`/`Valid`/`Invalid`/`Pending`, progress bar, filters `Questions`/`Status`/`Submitted by`, navigation `⏮ First`/`◀ Previous`/`Image #`/`Next ▶`/`Next pending ⏭`, image + "Open original attachment in Kobo", details with "All data of this row", evaluation form) followed by a numbered walkthrough: (1) choose the form from `forms/` or "Upload a file..."; (2) choose the matching data export; (3) sign in (link to Kobo account section); (4) type the evaluator name (pre-filled with the Kobo username); (5) read counters/progress; (6) filter; (7) navigate; (8) evaluate: choose `Valid` or `Invalid`, for Invalid tick at least one of `Low lighting`, `Too bright / overexposed`, `Out of focus / blurry`, `Invalid image content`, optional `Additional comments`, then `💾 Save` or `💾 Save & next`, and `🗑️ Clear this evaluation` to undo; validation messages `Select whether the image is valid or invalid.` and `Select at least one reason for an invalid image.`; (9) export and resume (link to Reports section). Copy every label verbatim from `src/evaluate_kobo_form_images/app.py`
- [X] T012 [US1] Write "Kobo account" in `README.md`: `Server` choices `Global (kf.kobotoolbox.org)`, `EU (eu.kobotoolbox.org)`, `Custom…` (pre-selected from the image links; `Server URL` for custom); tab `Username & password` and tab `API key` with the caption text `Use an API key if you sign in to Kobo with your organization (SSO) or with two-factor authentication. Find it in Kobo > Account settings > Security.`; automatic sign-in from `KOBO_API_TOKEN` in `.env`; signed-in panel (`Signed in as …`, method, `Sign out`); mismatch warning; privacy: password sent once to Kobo to obtain the API key and never stored, key kept only in memory for the browser session and sent only to the signed-in Kobo server, nothing written to evaluations or reports
- [X] T013 [US1] Write "Reports: export and resume" in `README.md`: `Save to folder` (default `exports/` or `REPORTS_DIR`), `Include images not evaluated yet`, `💾 Export report`, success text `Report saved to <path>`, naming `image_evaluation__<form>__<YYYYMMDD-HHMMSS>.xlsx` with `-2`, `-3`… (never overwritten); resume: `Previous report (.xlsx)` + `⤴ Import report`, what is restored (verdict, reasons, comments, evaluator, date), persisted immediately to the autosave, merge rule (newer evaluation wins, equal dates keep local, nothing deleted), summary items (`Restored N evaluations from … (A added, U updated, K unchanged).`, form/data mismatch warning, `… evaluated rows did not match any image in this export.`, `… rows were rejected`, `All images in this export are evaluated.`), filters reset and viewer jumps to the first pending image after the last evaluated row, `This report was already imported.`; a tip to keep a backup copy of `evaluations/*.json`

**Checkpoint**: MVP — the README alone guides a new evaluator through the full workflow.

---

## Phase 4: User Story 2 - A reviewer understands how the app works and what to expect (Priority: P2)

**Goal**: Readers understand the end-to-end mechanics, report contents and error messages.

**Independent Test**: The six questions of `contracts/readme-content.md` are answered from the README only (quickstart §4).

- [X] T014 [P] [US2] Write "How it works" in `README.md`: a Mermaid `flowchart LR` (XLSForm + Kobo export → image records → Kobo sign-in → download & cache → evaluate → autosave JSON → Excel report → import/resume back into autosave) and short paragraphs: inputs (XLSForm `.xlsx` + Kobo data export `.xlsx` of the same form, all sheets, XML-name or label headers), image discovery (`<header>_URL` columns matched to image questions by name or label, group prefixes ignored, unmatched columns still listed with a warning — no image dropped), why sign-in is needed (Kobo attachments are private), image cache (`.cache/images`), autosave per form+export in `evaluations/<form>__<export>.json` after every save, stable image key used to resume
- [X] T015 [P] [US2] Write "Excel report reference" in `README.md` inside a `<details>` block: sheets `Evaluations` (one row per image; list the traceability columns and evaluation columns exactly as in `EVALUATION_COLUMNS` of `src/evaluate_kobo_form_images/report.py`), `Summary by question`, `Metadata`; columns required for re-import (`Image key`, `Image URL`, `Question name`, `Evaluation status`, `Invalid reasons` or `Reason: …`, `Comments`, `Evaluator`, `Evaluated at (UTC)`)
- [X] T016 [P] [US2] Write "Configuration" in `README.md`: table `KOBO_API_TOKEN` (empty → sign in from the sidebar), `KOBO_FORMS_DIR` (`forms`), `KOBO_DATA_DIR` (`data`), `EVALUATIONS_DIR` (`evaluations`), `IMAGE_CACHE_DIR` (`.cache/images`), `REPORTS_DIR` (`exports`), set in `.env` (copy of `.env.example`, git-ignored); note that `forms/`, `data/`, `evaluations/`, `exports/`, `.cache/` and `*.xlsx` are never committed
- [X] T017 [P] [US2] Write "Troubleshooting" in `README.md`: a table Message → Cause → What to do with at least the 12 rows of `contracts/readme-content.md` (copy each message verbatim from `src/`), plus "`uv run` hangs / installs elsewhere" (global `UV_PROJECT_ENVIRONMENT` or no PyPI access → use the `.venv` executable or `make`)

**Checkpoint**: US1 and US2 content complete.

---

## Phase 5: User Story 3 - The repository's main version reflects the latest changes (Priority: P3)

**Goal**: `main` contains features 001 + 002 (done in Phase 2) and the README describing them.

**Independent Test**: The repository main page shows the new README and `main` contains `kobo_auth.py` and `report_import.py` (quickstart §1).

- [X] T018 [US3] Update "Features", "Repository structure" and "Quality and automation" in `README.md`: features table rows for any XLSForm, any Kobo export, no image lost, Kobo sign-in, fast review, autosave, local report, resume from a report; structure tree including `kobo_auth.py`, `kobo_client.py`, `report.py`, `report_import.py`, `specs/`, `.specify/`, `.claude/`, local-only `forms/ data/ evaluations/ exports/ .cache/`; make targets with non-make equivalents (`.venv/Scripts/python.exe -m pytest`, `-m ruff check .`, `-m ty check`)
- [X] T019 [US3] Update `CONSTITUTION.md`: add decision-log row "2026-11-13 | Merge stacked PRs #1 and #2 with merge commits (not squash) | Avoid rewriting a published branch; keeps human-authored commits (feature 003)"; add §12 roadmap item "- [x] Detailed README user guide (spec `specs/003-readme-user-guide`)"; ensure feature list and configuration names match the README (FR-011)

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T020 Verify README accuracy with a one-off script (not committed, in the scratchpad): extract every backtick-quoted string from `README.md` that looks like UI text (contains a space or an emoji, excluding commands/paths) and assert it occurs in `src/evaluate_kobo_form_images/*.py`; extract every `](#anchor)` and relative `](path)` link and assert the anchor heading / file exists; fix `README.md` until clean
- [X] T021 Check `README.md` contains no real field data, tokens, e-mails or personal names other than the maintainer credit (grep for `kf.kobotoolbox.org/api/v2/assets/`, 40-hex tokens, `@`), and is fully English
- [X] T022 Run `make check` and `SKIP=uv-lock .venv/Scripts/python.exe -m pre_commit run --all-files` (after `uv lock --check --offline`); all green
- [X] T023 Commit on `003-readme-user-guide` with Conventional Commits (`docs: add detailed README user guide and how-it-works`), including `specs/003-readme-user-guide/`, `README.md`, `CONSTITUTION.md`; human author only, no AI trailers; push and open a PR to `main` (not draft) with the quickstart checklist; wait for CI green
- [ ] T024 Hand over to the maintainer: render check on GitHub (Mermaid, tables, `<details>`, TOC links) and the reader tests of `quickstart.md` §3–4; merging the README PR is the maintainer's action after review

---

## Dependencies & Execution Order

```text
Setup (T001) → Foundational merges (T002–T008) → US1 (T009–T013) → US2 (T014–T017) → US3 (T018–T019) → Polish (T020–T024)
```

- Foundational blocks everything: the README must describe the code on `main`.
- T009 (skeleton) must precede all other README tasks.
- US2 tasks write separate sections and can run in parallel after T009; US1 tasks are sequential (same narrative flow, cross-links).
- T019 (CONSTITUTION) is independent of README sections once T009 is done.

### Parallel opportunities

- T014 ∥ T015 ∥ T016 ∥ T017 (different README sections).
- T019 ∥ any README section task.
- Merge tasks T002–T007 are strictly sequential.

## Parallel Example: User Story 2

```text
Task: "T014 How it works (Mermaid + mechanics)"
Task: "T015 Excel report reference"
Task: "T016 Configuration table"
Task: "T017 Troubleshooting table"
```

## Implementation Strategy

### MVP first

Phase 1–3: `main` updated with features 001 + 002, and the README has the full user guide
(Getting started, Using the interface, Kobo account, Reports) — the main user need.

### Incremental delivery

1. Merges (Foundational) → repository up to date immediately.
2. US1 guide → new evaluators are autonomous.
3. US2 reference + troubleshooting → fewer support questions.
4. US3 polish of features/structure + CONSTITUTION → single source of truth consistent.
5. Verification + PR.
