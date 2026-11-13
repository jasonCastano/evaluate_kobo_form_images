<!--
Sync Impact Report
- Version: 1.0.0 → 1.1.0 (2026-11-13)
- Modified section: Development Workflow (branch model: develop / user-only main, feature 004)
- Principles defined: I–VIII (unchanged)
- Added sections: Technology & Data Constraints, Development Workflow, Governance
- Templates requiring updates: none (plan/spec/tasks templates read this file as-is)
- Follow-up TODOs: none
-->

# Evaluate Kobo Form Images Constitution

> This is the Spec Kit view of the project's governing rules. The **authoritative, detailed
> source of truth is [`/CONSTITUTION.md`](../../CONSTITUTION.md)** (stack, architecture,
> structure, decision log). Both files MUST stay consistent; any amendment updates both in
> the same commit.

## Core Principles

### I. Human Judgment, Full Traceability

The app supports human evaluators; it never auto-classifies images. Every evaluation MUST be
traceable to its source: form file and title, data file, data sheet, Excel row, submission
ID/UUID, repeat index, question name/label/group, image file name and image URL. Records are
identified by a stable key so work can be resumed.

### II. No Image Silently Dropped

Every `<header>_URL` column of a Kobo export MUST produce image records. Columns are matched
to form questions by XML name, then by any label (all languages, markup/case/spacing/group
prefix insensitive, duplicates resolved in form order). Unmatched columns are still listed and
flagged as unmapped.

### III. Closed Evaluation Vocabulary

An evaluation is **Valid** or **Invalid**. Invalid requires at least one reason from the closed
list `Low lighting`, `Too bright / overexposed`, `Out of focus / blurry`,
`Invalid image content`; comments are optional free text. Changing the list is a
constitutional (MAJOR) change because report columns depend on it.

### IV. Logic Outside the UI

Business logic lives in tested modules (`xlsform`, `kobo_export`, `kobo_client`,
`evaluation`, `report`). `app.py` (Streamlit) only orchestrates widgets and calls them.

### V. Test-Backed Quality Gates (NON-NEGOTIABLE)

`make check` (Ruff lint + format, `ty` type check, pytest) MUST pass before every commit and
in CI. New behavior ships with pytest tests following Arrange-Act-Assert, using **synthetic**
fixtures only. Pre-commit hooks are never skipped.

### VI. Data Protection

Field data never enters Git: Kobo forms, exports, evaluation files, Excel reports, downloaded
images and Kobo API tokens are git-ignored. Specs, plans, tasks and tests MUST NOT embed real
farmer/enumerator data or tokens.

### VII. English Only

UI, code, identifiers, comments, docs, specs, plans, tasks, reports and commit messages are
written in English.

### VIII. Human Authorship Only

Only human maintainers appear as contributors. Commits and PRs MUST NOT include
`Co-Authored-By:` trailers for AI assistants or bots, "Generated with ..." footers, or bot
identities. Dependabot and any bot that commits or opens PRs stay disabled; CI never commits.

## Technology & Data Constraints

- Python 3.13+, src-layout package `evaluate_kobo_form_images`, build backend `uv_build`.
- Dependencies and environments only through `uv` (`uv add`); `pip` and `requirements.txt`
  are forbidden; `uv.lock` is committed. The project always uses its own `.venv`.
- UI: Streamlit. Excel I/O: openpyxl. HTTP/images: requests + Pillow. Config: `.env`.
- Kobo attachments are private: downloads use `Authorization: Token <KOBO_API_TOKEN>`.
- Inputs are Kobo XLSForm `.xlsx` files and Kobo `.xlsx` data exports (any header mode).

## Development Workflow

1. Spec-driven flow for new features: `/speckit-specify` → (`/speckit-clarify`) →
   `/speckit-plan` → `/speckit-tasks` → (`/speckit-analyze`) → `/speckit-implement`.
   Feature artifacts live in `specs/NNN-feature-name/`.
2. Work on a branch created from `develop` (`feat/…`, `fix/…`, `docs/…`, or Spec Kit
   `NNN-feature-name`), Conventional Commits in imperative mood, PR into `develop` with green
   CI, Squash & Merge. `main` is user-only and receives allowlisted releases only
   (`scripts/release_to_main.py`, see `/DEVELOPMENT.md`).
3. Any architectural, technology or process change updates `/CONSTITUTION.md` (and this
   file when principles are affected) in the same commit.

## Governance

This constitution and `/CONSTITUTION.md` supersede other practices. Plans MUST pass a
Constitution Check against Principles I–VIII; violations require explicit justification in the
plan's Complexity Tracking. Amendments: document the change and rationale in the
`/CONSTITUTION.md` decision log, bump this version (MAJOR: principle removed/redefined;
MINOR: principle/section added; PATCH: clarification), and update both files together.

**Version**: 1.1.0 | **Ratified**: 2026-11-12 | **Last Amended**: 2026-11-13
