# Phase 1 Data Model: file classification and branch model

**Feature**: [spec.md](./spec.md) · **Research**: [research.md](./research.md)

## Allowlist (paths published to `main`)

Glob-style, matched against repository-relative POSIX paths:

```text
src/**
tests/**
.github/workflows/ci.yml
.streamlit/config.toml
pyproject.toml
uv.lock
.python-version
.env.example
.gitignore
.gitattributes
.editorconfig
.pre-commit-config.yaml
Makefile
LICENSE
README.md
```

## Denylist (never published, even if matched above)

```text
tests/test_release_to_main.py
**/__pycache__/**
```

## Developer-only (everything else on `develop`), for reference

`.claude/`, `.specify/`, `.opencode/`, `specs/`, `scripts/`, `docs/`, `CONSTITUTION.md`,
`AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `DEVELOPMENT.md`,
`.github/ISSUE_TEMPLATE/`, `.github/pull_request_template.md`, `.github/labels.yml`,
`.github/workflows/labels.yml`.

Rule: a path is **published** ⇔ it matches the allowlist **and** does not match the denylist.
Any new file is developer-only by default until added to the allowlist (safe default).

## Branches

| Branch | Content | Receives changes from | Protected rule |
|--------|---------|-----------------------|----------------|
| `main` (default) | Published paths only | `release/*` PRs only | No direct push, no force-push |
| `develop` | Everything | feature PRs (`NNN-name`, `fix/…`, `docs/…`) | No direct push, no force-push |
| `release/<YYYYMMDD-HHMM>` | Snapshot built by the script from `origin/main` | — | Deleted after merge |
| feature branches | Work in progress | — | Start from `develop` |

## Release state machine

```text
develop @ X ──release_to_main.py──► release/<stamp> (main + allowed paths of X)
     │                                   │ review diff (--name-status)
     │                                   ▼
     │                         PR release/<stamp> → main ──CI green──► squash merge
     ▼                                                               │
 next feature work                                       main == allowed(X)  (check passes)
```

Invariant after every release: `release_to_main.py --check` reports 0 non-allowed files on
`main` and an empty pending diff.
