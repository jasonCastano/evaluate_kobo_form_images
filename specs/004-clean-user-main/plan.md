# Implementation Plan: User-only Main Branch and Developer Branch

**Branch**: `004-clean-user-main` | **Date**: 2026-11-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-clean-user-main/spec.md`

## Summary

Split the repository into a user-facing `main` and a complete `develop`. `develop` is created
from the current `main` and receives the pending README PR #3, so nothing is lost. On a feature
branch from `develop` we add a developer-only release script (`scripts/release_to_main.py`) that
builds `main` as an **allowlist snapshot** of `develop` (src, tests, CI, install/run files,
LICENSE, README), make `README.md` user-only on both branches and move developer content to a new
`DEVELOPMENT.md`, and update CONSTITUTION/AGENTS/CLAUDE/CONTRIBUTING with the branch model. The
first release run produces a PR to `main` that removes all developer material; no history is
rewritten and nothing is force-pushed.

## Technical Context

**Language/Version**: Python 3.13 (stdlib-only release script), Markdown, git + gh

**Primary Dependencies**: none new

**Storage**: N/A (git trees)

**Testing**: pytest — classification unit tests + git operations in a temporary repository
(`tests/test_release_to_main.py`, denylisted from `main`); `make check`; scripted `--check`;
fresh-clone install test

**Target Platform**: GitHub repository (`main` default, `develop`), Windows developer machine

**Project Type**: Repository restructuring + small developer tool for the existing package

**Performance Goals**: N/A (release script runs in seconds)

**Constraints**: no history rewrite, no force-push, no direct push to `main`/`develop`; human
author only; untracked/ignored local data (forms, data, evaluations, exports, .env) never touched;
English only

**Scale/Scope**: ~70 developer files removed from `main`; 1 script + tests; 2 docs rewritten
(README, new DEVELOPMENT.md); 4 governance docs updated; 3 PRs (#3 → develop, 004 → develop,
release → main)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| I–III (domain) | Application code unchanged | ✅ |
| IV. Logic outside UI | Release logic in a script with testable pure functions | ✅ |
| V. Quality gates | New script tested; CI green on `develop` and release PRs | ✅ |
| VI. Data protection | Script touches tracked files only; field data stays ignored | ✅ |
| VII. English only | All docs/messages English | ✅ |
| VIII. Human authorship | Release commits by the local maintainer identity; no trailers | ✅ |
| CONSTITUTION §6/§9 (structure, Git flow) | Amended: `main` = user releases, `develop` = full project, release procedure — recorded in the decision log | ✅ amended in the same change |

**Post-design re-check**: ✅ all gates pass; the constitution itself is amended (on `develop`) to
describe the new branch model, as required by its maintenance directive.

## Project Structure

### Documentation (this feature)

```text
specs/004-clean-user-main/
├── plan.md
├── research.md            # R1–R7
├── data-model.md          # allowlist / denylist, branches, release state machine
├── quickstart.md          # validation guide
├── contracts/
│   ├── release-script.md  # CLI + behaviour of release_to_main.py
│   └── user-readme.md     # README (user-only) + DEVELOPMENT.md contents
├── checklists/requirements.md
└── tasks.md               # /speckit-tasks
```

### Source Code (repository root)

```text
scripts/release_to_main.py        # NEW (develop only)
tests/test_release_to_main.py     # NEW (develop only, denylisted)
README.md                         # CHANGED: user-only (both branches)
DEVELOPMENT.md                    # NEW (develop only)
CONSTITUTION.md, AGENTS.md, CLAUDE.md, CONTRIBUTING.md   # CHANGED (develop only)
.specify/memory/constitution.md   # CHANGED: branch-model note (develop only)
.github/workflows/ci.yml          # CHANGED: push trigger on main and develop
pyproject.toml                    # CHANGED: neutral comment for the .specify exclusion
```

**Structure Decision**: Keep the single package; developer tooling lives in a top-level
`scripts/` folder that is developer-only by default (not in the allowlist).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Two long-lived branches with a snapshot release instead of a single `main` | User explicitly requires a user-only `main` while keeping developer material | Single branch cannot satisfy both; merge-based sync would reintroduce developer files |
