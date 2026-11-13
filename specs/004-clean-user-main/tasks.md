# Tasks: User-only Main Branch and Developer Branch

**Input**: Design documents from `/specs/004-clean-user-main/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: INCLUDED for the new release script (Constitution Principle V). Tests use a temporary
git repository; they never touch the real repository or the network.

**Organization**: Branch creation and the release script are foundational (both later phases need
them). US1 = user-only `main` (P1), US2 = complete `develop` + developer docs (P2), US3 = repeatable
release flow (P3). Publishing (PRs, release run) is grouped in the final Delivery phase because it
needs the content of all three stories merged into `develop` first.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: US1, US2, US3 as above

## Path Conventions

Repository root `D:\croppix\evaluate_form_images`. Python: `.venv/Scripts/python.exe`. GitHub
operations with the maintainer's `gh`. Never force-push; never push directly to `main` or
`develop` (only create branches and merge through PRs).

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Verify preconditions (repository root): `git fetch origin --prune`; local branch `003-readme-user-guide` has no unpushed commits (`git status -sb`); the only uncommitted change is the untracked `specs/004-clean-user-main/`; PR #3 is OPEN with base `main` and green checks (`gh pr checks 3`); `origin/main` is at `19f99e6` or later. Stop and report on any mismatch.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create `develop` with everything (FR-006) and the release tool every later phase uses.

**⚠️ CRITICAL**: All story work happens on a feature branch from `develop`.

- [X] T002 Create the remote branch `develop` from `origin/main` without touching `main`: `git push origin origin/main:refs/heads/develop`; confirm with `git ls-remote --heads origin develop`
- [X] T003 Retarget PR #3 to `develop` (`gh pr edit 3 --base develop`), wait for its checks (`gh pr checks 3 --watch`), mark it ready if draft, and merge with a merge commit keeping its branch until done: `gh pr merge 3 --merge --subject "docs: add detailed README user guide and how-it-works (#3)" --body ""`; then delete the remote branch `003-readme-user-guide` with `git push origin --delete 003-readme-user-guide` (it is the head, not a base, of any PR)
- [X] T004 Sync locally and create the feature branch: `git fetch origin --prune`; `git switch -c develop --track origin/develop` (or `git switch develop && git pull --ff-only`); `git branch -d 003-readme-user-guide`; `git switch -c 004-clean-user-main`; the untracked `specs/004-clean-user-main/` carries over
- [X] T005 [P] Write tests first in `tests/test_release_to_main.py` (load the script with `importlib.util.spec_from_file_location` from `scripts/release_to_main.py`; mark the module `pytest.mark.skipif(not SCRIPT.exists(), reason="developer-only script")`): (a) `is_published` returns True for `src/evaluate_kobo_form_images/app.py`, `tests/test_report.py`, `.github/workflows/ci.yml`, `.streamlit/config.toml`, `pyproject.toml`, `uv.lock`, `.python-version`, `.env.example`, `.gitignore`, `.gitattributes`, `.editorconfig`, `.pre-commit-config.yaml`, `Makefile`, `LICENSE`, `README.md`; (b) False for `tests/test_release_to_main.py`, `src/x/__pycache__/a.pyc`, `CONSTITUTION.md`, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `DEVELOPMENT.md`, `docs/README.md`, `specs/001-x/spec.md`, `.specify/memory/constitution.md`, `.claude/settings.json`, `.opencode/rules/tgrep.md`, `scripts/release_to_main.py`, `.github/workflows/labels.yml`, `.github/labels.yml`, `.github/pull_request_template.md`, `.github/ISSUE_TEMPLATE/bug_report.yml`, `newfile.txt`; (c) integration in a temp repo (`git init`, set local `user.name`/`user.email`, create `main` with `README.md`+`CONSTITUTION.md`+`src/a.py`, create `develop` adding `specs/s.md`, changing `src/a.py`, adding `src/b.py`, deleting nothing; run `main(["--source","develop","--target","main","--branch","release/test","--no-fetch"])` with `cwd` = temp repo): returns 0, `release/test` tree == {`README.md`,`src/a.py`,`src/b.py`} (so `CONSTITUTION.md` removed, `specs/` absent), last commit message starts with `release: sync user files from`, commit body has no `Co-authored-by`; (d) running again from that branch state with nothing to publish prints "already up to date" and creates no commit; (e) `--check` on a `main` containing `CONSTITUTION.md` returns 1 and lists it; (f) refuses with exit 2 when a tracked file is modified; (g) untracked file `data/x.xlsx` in the temp repo is untouched after a release
- [X] T006 Implement `scripts/release_to_main.py` per `contracts/release-script.md` (stdlib only: `argparse`, `fnmatch`/`PurePosixPath` matching with `**`, `subprocess.run([...], check=True, text=True, capture_output=True)` with `cwd` = current directory): constants `ALLOWLIST` and `DENYLIST` exactly as in `data-model.md`; `is_published(path)`; `published_paths(paths)`; `main(argv)` implementing: clean-tree guard (exit 2, "Commit or stash your changes first."), optional `git fetch origin` (`--no-fetch` skips), `--check` mode (print "Not allowed on <target>:" list and "Pending release diff:" list from comparing `git ls-tree -r <target>` with published paths of `<source>` and their blob ids; exit 1 if any not allowed), normal mode (`git switch -c <branch> <target>`, `git rm -r -q --ignore-unmatch .` on tracked files only, `git checkout <source> -- <published paths>` in chunks, `git add -A -- <published paths>`, if `git diff --cached --quiet` → print "main is already up to date with <source>." switch back and delete the branch, exit 0; else `git commit -m "release: sync user files from <source> @ <short sha>"`, print `git diff --name-status <target> HEAD` and next-step commands `git push -u origin <branch>` and `gh pr create --base main --head <branch> --title "release: <date>"`); docstring explains it is developer-only and never pushes
- [X] T007 Run `.venv/Scripts/python.exe -m pytest tests/test_release_to_main.py -q` and `-m ruff check scripts tests` / `-m ty check`; fix until green

**Checkpoint**: `develop` holds everything; the release tool works in isolation.

---

## Phase 3: User Story 1 - A new user sees only what they need on the main branch (Priority: P1) 🎯 MVP

**Goal**: The content that will be published to `main` is user-only and installable.

**Independent Test**: `scripts/release_to_main.py --check --source HEAD --target HEAD --no-fetch` on the feature branch lists the published set; the README has no references to non-published paths.

- [X] T008 [US1] Make `README.md` user-only per `contracts/user-readme.md`: remove the Overview call-out to `CONSTITUTION.md`; remove the "Contributing" section and its TOC entry; rename "Quality and automation" to "Quality checks" (keep only the command table, no hooks/workflow wording); in "Repository structure" list only published paths (`src/…` modules, `tests/`, `.github/workflows/ci.yml`, `.streamlit/`, `pyproject.toml`, `uv.lock`, `Makefile`, `LICENSE`, `README.md`, and the local-only folders note) — remove `specs/`, `docs/`, `.claude/ .specify/`, `CONSTITUTION.md`; remove any mention of Spec Kit, `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`; add before the footer: "> 👩‍💻 **Developers:** the full project (specifications, governance and tooling docs) lives on the [`develop`](https://github.com/jasonCastano/evaluate_kobo_form_images/tree/develop) branch."; update the TOC anchors
- [X] T009 [P] [US1] Reword the comment above `extend-exclude = [".specify"]` in `pyproject.toml` to "# Vendored tooling scripts are not linted here." (keep both `.specify` exclusions)
- [X] T010 [P] [US1] In `.github/workflows/ci.yml` change `push.branches` to `[main, develop]`
- [X] T011 [US1] Run the README verification script from feature 003 (scratchpad `check_readme.py`) against `README.md` and additionally assert that no link or quoted path in `README.md` points to a path for which `is_published` is False (except the `develop` branch URL); fix until clean

**Checkpoint**: Published content is user-only.

---

## Phase 4: User Story 2 - The developer keeps all project knowledge on a developer branch (Priority: P2)

**Goal**: `develop` documents itself as the development base; developer content has a home.

**Independent Test**: On `develop`, `DEVELOPMENT.md` explains the branch model and the release; CONSTITUTION/AGENTS/CLAUDE/CONTRIBUTING say feature branches start from `develop`.

- [X] T012 [P] [US2] Create `DEVELOPMENT.md` per `contracts/user-readme.md` §DEVELOPMENT.md: (1) branch model table (`main` user releases / `develop` full project / feature branches from `develop`, PRs `--base develop` / `release/*` → `main`); (2) release procedure (link to US3 section); (3) Spec Kit workflow (`/speckit-specify` → `/speckit-clarify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`, `specs/NNN-name/`); (4) quality tooling (`make dev`, `make check`, pre-commit, note "if the `uv-lock` hook stalls on network access, verify with `uv lock --check --offline` and commit with `SKIP=uv-lock`"); (5) rules (human authorship only — no AI/bot trailers; English only; never commit field data; `uv` only); (6) links to `CONSTITUTION.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `AGENTS.md`, `CLAUDE.md`, `docs/`
- [X] T013 [P] [US2] Update `CONSTITUTION.md`: §6 structure (add `DEVELOPMENT.md`, `scripts/`; mark which paths are published to `main`), §9 Repository and Git (branch model: `main` = user releases via `release/*` PRs only, `develop` = full project and default target for feature PRs; no direct pushes; no force-push), §10 workflow (start branches from `develop`), decision log rows "2026-11-13 | Split `main` (user-only) and `develop` (full project); publish with an allowlist snapshot script | Users need a clean main; developers keep specs/governance (feature 004)" and "2026-11-13 | Keep tests, CI, pre-commit and Makefile on `main` | Releases stay verified (feature 004, Q1=C)"; roadmap item for feature 004
- [X] T014 [P] [US2] Update `AGENTS.md` and `CLAUDE.md`: add "Branch model" rules — work on branches from `develop`, open PRs with `--base develop`, never push or open feature PRs against `main`, publish only with `scripts/release_to_main.py`; mention `DEVELOPMENT.md`
- [X] T015 [P] [US2] Update `CONTRIBUTING.md` §2 Branches and §5 Pull Requests: branch from `develop`, PRs target `develop`; releases to `main` are done by the maintainer with the release script
- [X] T016 [P] [US2] Add a short "Branch model" note to `.specify/memory/constitution.md` under "Development Workflow" (feature branches from `develop`; `main` receives allowlisted releases only) and bump its version to 1.1.0 with "Last Amended: 2026-11-13" and an updated Sync Impact Report comment

**Checkpoint**: Developer docs complete on the feature branch.

---

## Phase 5: User Story 3 - New versions reach the user branch without reintroducing developer files (Priority: P3)

**Goal**: The release step is documented and verified.

**Independent Test**: A dry run on a temporary repository (T005 tests) and the documented procedure produce a release containing only published paths.

- [X] T017 [US3] Write the "Releasing to `main`" section of `DEVELOPMENT.md`: prerequisites (clean tree, on `develop` up to date), `.\.venv\Scripts\python.exe scripts\release_to_main.py` (what it does, output), review the printed diff, `git push -u origin release/<stamp>`, `gh pr create --base main --head release/<stamp> --title "release: <date>" --body "<summary of changes>"`, wait for CI, squash merge, delete the release branch, `--check` afterwards; how to add a new user-facing file (edit `ALLOWLIST` in the script and its test); never merge `develop` into `main`

---

## Phase 6: Delivery & Verification (cross-cutting)

- [X] T018 Run `make check` and `SKIP=uv-lock .venv/Scripts/python.exe -m pre_commit run --all-files` (after `uv lock --check --offline`) on `004-clean-user-main`; all green
- [ ] T019 Commit on `004-clean-user-main` (`feat: split user-only main from develop and add release script`) including `specs/004-clean-user-main/`; human author only, no AI trailers; push; `gh pr create --base develop --head 004-clean-user-main`; wait for CI green; merge with `gh pr merge --merge --delete-branch` (head branch only); sync local `develop` (`git switch develop && git pull --ff-only`, `git branch -d 004-clean-user-main`)
- [ ] T020 [US1] Run the first release from local `develop`: `.venv/Scripts/python.exe scripts/release_to_main.py`; check the printed diff deletes exactly the developer-only files (`.claude/`, `.specify/`, `.opencode/`, `specs/`, `docs/`, `CONSTITUTION.md`, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `.github/ISSUE_TEMPLATE/`, `.github/pull_request_template.md`, `.github/labels.yml`, `.github/workflows/labels.yml`) and adds/modifies only published paths (README, ci.yml, pyproject); push the release branch and open the PR to `main` (`--base main`), wait for CI green, squash merge with subject "release: user-only main (feature 004)", delete the release branch
- [ ] T021 Verify (quickstart §1–2): `git diff --name-only --diff-filter=D 19f99e6 origin/develop` empty; PR #3 MERGED into `develop`; `release_to_main.py --check` → no non-allowed files and empty pending diff; `git ls-tree -r --name-only origin/main` contains only published paths; authors on `main` and `develop` = only the maintainer
- [ ] T022 Fresh-clone install test (quickstart §3) in a scratch folder: `git clone --branch main …`, follow the README "Getting started" (Windows path), confirm `.\.venv\Scripts\evaluate-kobo-images.exe` starts (run the app headless with AppTest or start and stop it) and `make check`/pytest pass on the clone; delete the scratch clone afterwards
- [ ] T023 Hand over: report the branch model, how to release, and that the GitHub repository page (default `main`) now shows only user files

---

## Dependencies & Execution Order

```text
Setup (T001) → Foundational (T002–T007) → US1 content (T008–T011) ┐
                                         → US2 docs (T012–T016)    ├→ US3 doc (T017) → Delivery (T018–T023)
```

- T002 → T003 → T004 strictly sequential (remote branch, PR #3, local sync).
- T005 (tests) before T006 (script) — TDD; T007 after both.
- US1, US2 content tasks can proceed in parallel after T004 (different files), except T011 needs T008 and T006.
- T017 after T012 (same file `DEVELOPMENT.md`).
- Delivery: T018 → T019 → T020 → T021 → T022 → T023 strictly sequential.

### Parallel opportunities

- T009 ∥ T010 ∥ T012 ∥ T013 ∥ T014 ∥ T015 ∥ T016 (all different files) once T004 is done.
- T005 can be written while T002–T004 run remotely.

## Parallel Example: User Story 2

```text
Task: "T012 Create DEVELOPMENT.md"
Task: "T013 Update CONSTITUTION.md"
Task: "T014 Update AGENTS.md and CLAUDE.md"
Task: "T015 Update CONTRIBUTING.md"
Task: "T016 Update .specify/memory/constitution.md"
```

## Implementation Strategy

### MVP first

Foundational + US1 content + the first release (T001–T011, T018–T020): `main` becomes user-only
while `develop` keeps everything — the user's core request.

### Incremental delivery

1. `develop` created with PR #3 merged (nothing lost).
2. Release tool tested.
3. User-only README + CI trigger.
4. Developer docs (DEVELOPMENT, CONSTITUTION, AGENTS, CLAUDE, CONTRIBUTING).
5. Release procedure documented → first release → verification.
