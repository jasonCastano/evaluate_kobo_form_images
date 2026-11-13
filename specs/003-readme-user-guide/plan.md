# Implementation Plan: Up-to-date Repository and Detailed README User Guide

**Branch**: `003-readme-user-guide` | **Date**: 2026-11-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-readme-user-guide/spec.md`

## Summary

Bring `main` up to date by merging the stacked PRs #1 (Kobo sign-in) and #2 (local report saving
and resume) with merge commits — no history rewrite, CI green before each merge, maintainer as
the only author — and then deliver, in a new PR from the updated `main`, a reorganized README:
a Mermaid "How it works" flow, a step-by-step "Using the interface" guide covering every sidebar
section and main-area control, Kobo account and privacy, report export/resume and the import
summary, the Excel report reference, all configuration options and a troubleshooting table of the
real UI messages. UI strings are copied verbatim from the code and verified by script.

## Technical Context

**Language/Version**: Markdown (GitHub-flavored) with Mermaid; repository operations with
`git` + `gh`

**Primary Dependencies**: none new (GitHub renders Mermaid natively)

**Storage**: N/A

**Testing**: pre-commit hygiene + `make check` (unchanged code must stay green); scripted
string/link verification; manual rendering and reader tests (quickstart)

**Target Platform**: GitHub repository page; readers on Windows primarily

**Project Type**: Documentation + repository maintenance for the existing single Python package

**Performance Goals**: N/A (reader goal: first-time workflow < 30 min, SC-001)

**Constraints**: English only; no field data/tokens/personal names; every quoted UI string exists
in `src/`; no force-push or direct push to `main`; no bot/AI attribution

**Scale/Scope**: One README (~14 sections), CONSTITUTION consistency edits, 2 PR merges, 1 new PR

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| I. Traceability | README documents report columns and how evaluations link to form/data/question/image | ✅ |
| II. No image silently dropped | README explains unmapped columns and "not matched" rows | ✅ |
| III. Closed vocabulary | README lists the four reasons verbatim | ✅ |
| IV. Logic outside UI | No code change | ✅ |
| V. Quality gates | CI green before each merge; `make check` on `main` after merging | ✅ |
| VI. Data protection | No screenshots with field data; no tokens in docs | ✅ |
| VII. English only | README in English | ✅ |
| VIII. Human authorship | Merge commits authored by the maintainer; no AI trailers | ✅ |
| Process (CONSTITUTION §9 PR flow) | Deviation: merge commits instead of Squash & Merge for the stacked PRs (research R1) — recorded in the decision log | ✅ justified |

**Post-design re-check**: ✅ all gates pass.

## Project Structure

### Documentation (this feature)

```text
specs/003-readme-user-guide/
├── plan.md
├── research.md                 # R1 merge strategy … R7 branch
├── data-model.md               # README sections + repository state transitions
├── quickstart.md               # validation guide
├── contracts/
│   ├── readme-content.md       # required content, troubleshooting rows, six-question test
│   └── merge-procedure.md      # exact merge commands and guards
├── checklists/requirements.md
└── tasks.md                    # /speckit-tasks
```

### Source Code (repository root)

```text
README.md            # REWRITTEN (sections per data-model.md)
CONSTITUTION.md      # CHANGED: decision log (merge strategy for stacked PRs), §12 roadmap
src/, tests/         # unchanged
```

**Structure Decision**: Documentation-only change on top of the merged code; the README stays a
single file with `<details>` blocks for long references.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Merge commits instead of Squash & Merge for PR #1 and #2 | #2 is stacked on #1; squashing #1 would force a rebase + force-push of a published branch | Force-push rewrites shared history and risks losing review state |
