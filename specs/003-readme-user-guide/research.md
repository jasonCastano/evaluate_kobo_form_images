# Phase 0 Research: Up-to-date Repository and Detailed README User Guide

**Feature**: [spec.md](./spec.md) · **Date**: 2026-11-13

## R1. How to merge the stacked pull requests (#1 → #2) into `main`

- **Context**: #1 `001-kobo-account-login → main`; #2 `002-report-export-resume →
  001-kobo-account-login` (stacked). Repository convention (PR template): *Squash & Merge*.
- **Decision**: Merge both with **merge commits** (`gh pr merge --merge`), in order:
  1. #1 into `main` with `--delete-branch` → GitHub automatically retargets #2 to `main`.
  2. Wait for #2's CI on the new base, then merge #2 into `main` with `--merge --delete-branch`.
- **Rationale**: Squashing #1 would give `main` a new commit whose content duplicates #2's
  ancestor commit `d838b57`; #2 would then need a rebase and a **force-push** of a published
  branch, or GitHub would compute its squash against a diverged base. Merge commits keep the
  original, human-authored commits (`d838b57`, `00f7406`) and need no history rewrite. The
  deviation from "Squash & Merge" is limited to these stacked PRs and recorded in the
  CONSTITUTION decision log.
- **Authorship (FR-014)**: merge commits are authored by the maintainer's GitHub account
  (`jasonCastano`); GitHub's `web-flow` appears only as *committer* and is not listed as a
  contributor. No `Co-authored-by` lines are added (the merge body is the PR title only).
- **Alternatives considered**: squash #1 + rebase/force-push #2 (rewrites a published branch)
  → rejected; squash both and accept a conflicting/duplicated diff → rejected; local merge +
  direct push to `main` (bypasses PR checks, FR-012) → rejected.

## R2. README structure

- **Decision**: Single `README.md` (spec assumption) reorganized into: Overview · Features ·
  **How it works** · Getting started · **Using the interface** (step-by-step, the core) ·
  **Kobo account** · **Reports: export and resume** · Excel report reference ·
  **Configuration** · **Troubleshooting** · Quality and automation · Repository structure ·
  Contributing · License. Long reference tables go inside `<details>` blocks.
- **Rationale**: Ordered by the reader's journey (install → use → understand → fix problems);
  matches every requirement FR-001…FR-009.
- **Alternatives considered**: `docs/` user guide linked from a short README → rejected by spec
  assumption (README is the single entry point); GitHub Wiki → not versioned with the code.

## R3. Diagrams

- **Decision**: One **Mermaid** `flowchart` in "How it works" (GitHub renders Mermaid natively)
  plus a plain-text sidebar map in "Using the interface".
- **Rationale**: Text-based, editable, reviewable in diffs, no field data (FR-010, assumption).
- **Alternatives considered**: PNG screenshots → risk of field data / personal names; Archify
  HTML → heavier than needed for a user guide.

## R4. Source of truth for UI texts and messages

- **Decision**: Every label, button and message quoted in the README is copied verbatim from the
  code on the branch that contains features 001 + 002 (`app.py`, `kobo_auth.py`,
  `kobo_client.py`, `report.py`, `report_import.py`, `kobo_export.py`); the task list includes a
  verification step that greps each quoted string in `src/`.
- **Rationale**: SC-003/SC-004/SC-005 (no documented-but-missing behaviour).

## R5. Platform and commands

- **Decision**: Windows PowerShell commands first (`.\.venv\Scripts\evaluate-kobo-images.exe`,
  `Copy-Item .env.example .env`), `make` targets as the cross-platform alternative, and a note
  for machines with a global `UV_PROJECT_ENVIRONMENT` (symptom: packages installed into another
  environment / `uv run` uses the wrong venv; workaround: `$env:UV_PROJECT_ENVIRONMENT=".venv"`
  or `make`).
- **Rationale**: Team platform is Windows; edge cases in the spec.

## R6. Validation approach for documentation

- **Decision**: (1) automated: pre-commit hygiene + `make check` stay green; a scripted check that
  every quoted UI string exists in `src/` and every relative link/anchor resolves; (2) manual:
  render the README on GitHub (Mermaid, tables, `<details>`) and run the six-question test of
  User Story 2.
- **Rationale**: Documentation has no unit tests; these checks make FR/SC verifiable.

## R7. Branch for the README work

- **Decision**: After R1, create `003-readme-user-guide` from the updated `main`; commit the
  feature 003 spec artifacts and the README/CONSTITUTION changes there; open a PR to `main`.
- **Note**: The uncommitted `specs/003-readme-user-guide/` folder currently sits in the working
  tree of `002-report-export-resume`; it must be carried over (it is untracked, so a branch
  switch keeps it).
