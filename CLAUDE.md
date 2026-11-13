# CLAUDE.md

Instructions for Claude Code in this repository.

@AGENTS.md

## Sources of truth

- [`CONSTITUTION.md`](./CONSTITUTION.md): project source of truth (stack, architecture,
  domain rules, decisions). Read it before changing anything.
- [`.specify/memory/constitution.md`](./.specify/memory/constitution.md): Spec Kit principles
  derived from it. Keep both consistent and update them in the same commit.

## Spec-driven development (Spec Kit)

Spec Kit skills are installed in `.claude/skills/`. Use them for new features:

| Step | Skill | Output |
|------|-------|--------|
| 1 | `/speckit-specify <feature description>` | `specs/NNN-name/spec.md` |
| 2 (optional) | `/speckit-clarify` | clarifications recorded in the spec |
| 3 | `/speckit-plan <technical notes>` | `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` |
| 4 | `/speckit-tasks` | `tasks.md` |
| 5 (optional) | `/speckit-analyze` / `/speckit-checklist` | consistency report / checklists |
| 6 | `/speckit-implement` | code + tests |

Spec Kit scripts are the Python variant (`.specify/scripts/python/`).

## Branch model

- `main` is **user-only** (published files); `develop` is the full project.
- Start every branch from `develop` and open PRs with `--base develop`. Never push to, merge
  `develop` into, or open feature PRs against `main`.
- Publish to `main` only with `scripts/release_to_main.py` (see `DEVELOPMENT.md`).
- Never delete the base branch of an open PR; never force-push.

## Non-negotiable rules

- Everything in English: code, UI, specs, plans, tasks, docs, reports, commit messages.
- **No AI attribution:** never add `Co-Authored-By:` trailers or "Generated with Claude Code"
  lines to commits or PRs (also disabled in `.claude/settings.json`). Commit only when the
  user asks.
- Run `make check` before declaring work done; use `uv` only (the project `.venv`).
- Never read field data into specs/tests or commit it (`forms/`, `data/`, `evaluations/`,
  `*.xlsx`, `.env`).
