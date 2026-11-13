# Development guide

> This file exists only on the **`develop`** branch. The user-facing **`main`** branch contains
> only what is needed to install and run the app (see [Branch model](#1-branch-model)).

The project's single source of truth is [`CONSTITUTION.md`](./CONSTITUTION.md). Assistant
instructions live in [`CLAUDE.md`](./CLAUDE.md) and [`AGENTS.md`](./AGENTS.md); contribution
rules in [`CONTRIBUTING.md`](./CONTRIBUTING.md) and [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md);
extra documentation in [`docs/`](./docs/).

## 1. Branch model

| Branch | Contains | Receives changes from | Rules |
|--------|----------|-----------------------|-------|
| `main` (default) | User files only: `src/`, `tests/`, CI, install/run files, `LICENSE`, `README.md` | `release/*` pull requests created by `scripts/release_to_main.py` | Never merge `develop` into `main`; no direct push; no force-push |
| `develop` | The full project (specs, governance, assistant config, scripts, docs) | Feature pull requests | No direct push; no force-push |
| `NNN-feature-name`, `fix/…`, `docs/…` | Work in progress | — | Branch from `develop`; open PRs with `--base develop` |
| `release/<YYYYMMDD-HHMM>` | Snapshot for `main` | — | Created by the script; deleted after merge |

```powershell
git switch develop; git pull --ff-only
git switch -c 005-my-feature
# ... work, commit ...
gh pr create --base develop --head 005-my-feature
```

> ⚠️ Never delete the base branch of an open pull request (GitHub closes the PR). Retarget it
> first.

## 2. Releasing to `main`

`scripts/release_to_main.py` makes `main` an exact copy of the **published** files of `develop`.
The published set is `ALLOWLIST` minus `DENYLIST` in the script; any other file stays on
`develop` (new files are developer-only by default).

1. Prerequisites: `develop` up to date (`git switch develop; git pull --ff-only`) and no tracked
   changes.
2. Check what would be published (read-only):

   ```powershell
   .\.venv\Scripts\python.exe scripts\release_to_main.py --check
   ```

3. Create the release branch (commits with your Git identity, never pushes):

   ```powershell
   .\.venv\Scripts\python.exe scripts\release_to_main.py
   ```

   Review the printed `A`/`M`/`D` list: only user files may appear.
4. Publish through a pull request:

   ```powershell
   git push -u origin release/<stamp>
   gh pr create --base main --head release/<stamp> --title "release: <date>" --body "<summary>"
   ```

5. Wait for CI, **squash merge**, delete the release branch, then
   `git switch develop` and run `--check` again: "Not allowed on origin/main" must be empty and
   the pending diff empty.

**Adding a user-facing file:** add its path or glob to `ALLOWLIST` in the script and to the
published list in `tests/test_release_to_main.py`, in the same pull request.

## 3. Spec-driven development (Spec Kit)

New features follow the Spec Kit flow in Claude Code: `/speckit-specify` → (`/speckit-clarify`)
→ `/speckit-plan` → `/speckit-tasks` → (`/speckit-analyze`) → `/speckit-implement`.
Artifacts live in `specs/NNN-feature-name/` and are committed on the feature branch.

## 4. Quality tooling

| Command | Purpose |
|---------|---------|
| `make dev` | `uv sync` + install pre-commit hooks |
| `make check` | Ruff + format check + `ty` + pytest |
| `uv run pre-commit run --all-files` | All hooks |

If the `uv-lock` hook stalls on network access to PyPI, verify the lockfile with
`uv lock --check --offline` and commit with `SKIP=uv-lock` (CI runs the hook anyway). The
`Makefile` and CI force a project-local `.venv`; when calling `uv` directly on a machine with a
global `UV_PROJECT_ENVIRONMENT`, set `UV_PROJECT_ENVIRONMENT=.venv` first.

## 5. Rules

- **Human authorship only:** no `Co-Authored-By:` trailers, "Generated with" footers or bot
  identities in commits or PRs (also enforced in `.claude/settings.json`).
- **English only** in code, UI, docs, reports and commit messages.
- **Never commit field data or secrets** (`forms/`, `data/`, `evaluations/`, `exports/`,
  `.cache/`, `*.xlsx`, `.env`).
- **`uv` only** for dependencies.
- Keep `CONSTITUTION.md` (and `.specify/memory/constitution.md`) up to date in the same PR as any
  architectural, technology or process change.
