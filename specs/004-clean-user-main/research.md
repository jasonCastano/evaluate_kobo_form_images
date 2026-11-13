# Phase 0 Research: User-only Main Branch and Developer Branch

**Feature**: [spec.md](./spec.md) · **Date**: 2026-11-13

## R1. Creating the developer branch with nothing lost (FR-006)

- **Decision**: Create `develop` on GitHub from the current `main` (`19f99e6`), then retarget the
  open README PR #3 (`003-readme-user-guide`) from `main` to `develop` and merge it there (merge
  commit). `develop` = full project + README guide, with complete history.
- **Rationale**: Keeps PR #3's review record; no history rewrite; `develop` contains every file of
  `main` plus the pending work (SC-004).
- **Alternatives considered**: branch `develop` directly from `003-readme-user-guide` and close #3
  (loses the merged-PR record) → rejected; merge #3 into `main` first (would put developer
  material on `main` again) → rejected.

## R2. How releases reach `main` without developer files (FR-008, SC-005)

- **Decision**: **Allowlist snapshot release.** A dev-only script `scripts/release_to_main.py`:
  1. creates `release/<YYYYMMDD-HHMM>` from `origin/main`;
  2. removes all tracked files from the index (`git rm -r -q --cached .` + clean tree of tracked
     files only — untracked/ignored local data is never touched);
  3. checks out from `origin/develop` exactly the paths matching the **allowlist** minus the
     **denylist** (data-model.md);
  4. commits as the human maintainer (`release: sync user files from develop @ <sha>`), prints the
     added/modified/deleted file list (`git diff --name-status origin/main`), and stops (push and PR
     are separate, explicit steps);
  5. `--check` mode: only reports files on a ref (default `origin/main`) that are not allowed, and
     the diff the next release would produce; exit code 1 if `main` contains a non-allowed file.
  `main` never merges `develop`; it only receives snapshots of allowed paths through a PR.
- **Rationale**: Deterministic (main tree = allowed subset of develop tree), cannot reintroduce
  developer files, handles deletions, needs no special merge drivers, and the first run performs
  the initial cleanup itself.
- **Alternatives considered**: merging `develop` into `main` with `.gitattributes merge=ours` for
  developer paths (does not prevent new dev files, brittle) → rejected; `git subtree`/filter-repo
  per release (history rewrite) → rejected (FR-010); manual cleanup per release → rejected (not
  repeatable).

## R3. One README for both branches

- **Decision**: `README.md` becomes **user-only on both branches** (sections per
  contracts/user-readme.md, plus the line "Developers: the full project (specifications, governance
  and tooling docs) lives on the `develop` branch."). Developer content moves to a new
  **`DEVELOPMENT.md`** (dev-only): branch model, release procedure, Spec Kit workflow, quality
  tooling, contributing rules and links to `CONSTITUTION.md`, `CLAUDE.md`, `AGENTS.md`,
  `CONTRIBUTING.md`.
- **Rationale**: `README.md` can then be in the allowlist unchanged — no per-branch README
  variants to reconcile at each release; developers find their guide on `develop`.
- **Alternatives considered**: different README per branch maintained by hand (diverges, release
  would overwrite it) → rejected; template-generated user README (extra tooling) → rejected.

## R4. Tests for a dev-only script while `tests/` ships to `main`

- **Decision**: Put the script's pure logic (path classification) in the script and test it in
  `tests/test_release_to_main.py`; add that test file to the **denylist** so it never reaches
  `main`. Git operations are exercised in a temporary repository created inside the test (no
  network, no access to the real repo).
- **Rationale**: Principle V (new behaviour has tests) on `develop`; `main` keeps a passing,
  user-relevant test suite (Q1 = C).

## R5. Default branch, PR targets and protection

- **Decision**: `main` stays the default branch (visitors and clones see the user version).
  Development PRs target `develop` explicitly (`gh pr create --base develop`); release PRs target
  `main` and are opened only from `release/*` branches. CI runs on PRs to both branches (the
  existing workflow triggers on all `pull_request` events; add `develop` to the `push` trigger).
- **Note**: The workflow change lives in `.github/workflows/ci.yml`, which is on the allowlist, so
  `main` receives the same CI file (harmless: the `develop` push trigger simply never fires there).

## R6. Developer references that remain in user files

- **Finding**: `pyproject.toml` excludes `.specify` from Ruff and `ty` (comment mentions Spec Kit).
  On `main` this is inert (folder absent) but is developer wording.
- **Decision**: Keep the exclusions (needed on `develop`); reword the comment to "Vendored tooling
  scripts are not linted here." No other user file references developer material (checked:
  `Makefile`, `.pre-commit-config.yaml`, `ci.yml`, `.gitignore`, `.gitattributes`,
  `.editorconfig`, `.env.example`).

## R7. Order of operations

1. `develop` from `main`; PR #3 → `develop`, merge.
2. Feature branch `004-clean-user-main` from `develop`: script + tests, `DEVELOPMENT.md`,
   user-only README, CONSTITUTION/AGENTS/CLAUDE/CONTRIBUTING updates, CI trigger, pyproject comment,
   specs/004 → PR to `develop`, merge.
3. Run the release script → `release/<stamp>` → PR to `main` (squash) → `main` clean.
4. Verify with `--check` and a fresh clone of `main`.
