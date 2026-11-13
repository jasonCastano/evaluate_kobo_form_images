# Contract: README (user-only, identical on `main` and `develop`) and DEVELOPMENT.md (develop only)

## README.md sections (in order)

Overview · Table of contents · Features · How it works · Getting started · Using the interface ·
Kobo account · Reports: export and resume · Excel report reference · Configuration ·
Troubleshooting · Quality checks · License · (footer line) "Developers: the full project
(specifications, governance and tooling docs) lives on the `develop` branch."

Removed versus the PR #3 README: the "Contributing" section, the Spec Kit / `CLAUDE.md` /
`CONSTITUTION.md` / `CONTRIBUTING.md` links, `specs/`, `.claude/`, `.specify/`, `docs/` from the
structure tree, and the `CONSTITUTION.md` call-out in the Overview. "Quality and automation" is
renamed "Quality checks" and keeps only commands (`make check`, `make test`, … and non-make
equivalents). The repository-structure tree lists only published paths.

Validation: no link to a non-published path; every quoted UI string exists in `src/`
(feature 003 script).

## DEVELOPMENT.md (develop only)

1. Branch model (`main` = user releases, `develop` = full project; feature branches from
   `develop`; PRs `--base develop`).
2. Release procedure (`scripts/release_to_main.py`, review diff, PR to `main`, squash, `--check`).
3. Spec Kit workflow (`/speckit-specify` … `/speckit-implement`), `specs/` layout.
4. Quality tooling (`make dev`, `make check`, pre-commit, `SKIP=uv-lock` note).
5. Rules: human authorship only, English only, no field data, `uv` only.
6. Links: `CONSTITUTION.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `AGENTS.md`, `CLAUDE.md`.
