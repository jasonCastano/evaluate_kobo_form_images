# Quickstart: validate the user-only `main` and the `develop` branch

**Feature**: [spec.md](./spec.md) · Contracts: [release-script](./contracts/release-script.md),
[user-readme](./contracts/user-readme.md)

## 1. Developer branch is complete (US2, SC-004)

```powershell
git fetch origin
# every file of the old main (19f99e6) and of PR #3 exists on develop
git diff --name-only --diff-filter=D 19f99e6 origin/develop     # expect: no output
git diff --name-only --diff-filter=D origin/003-readme-user-guide origin/develop  # expect: no output (if the branch still exists)
gh pr view 3 --json state,baseRefName   # MERGED into develop
```

## 2. `main` is user-only (US1, SC-001, SC-003)

```powershell
git checkout develop
.\.venv\Scripts\python.exe scripts\release_to_main.py --check
# expect: "Not allowed on origin/main:" empty, "Pending release diff:" empty, exit code 0
git ls-tree -r --name-only origin/main     # only allowlisted paths
```

## 3. Fresh install from `main` (US1, SC-002)

```powershell
cd $env:TEMP
git clone --branch main https://github.com/jasonCastano/evaluate_kobo_form_images.git kobo-test
cd kobo-test
# follow README "Getting started" exactly; the app opens at http://localhost:8501
```

## 4. Release flow (US3, SC-005)

1. On a feature branch from `develop`, change one line in `src/…` and one in `specs/…`; merge to
   `develop`.
2. `python scripts/release_to_main.py` → the printed diff lists only the `src/` file.
3. Push, open the PR to `main`, CI green, squash merge; `--check` passes again.
   (For validation without publishing, run step 2 and then delete the local release branch.)

## 5. Automated

```powershell
make check     # on develop (includes tests/test_release_to_main.py)
```

CI green on the `develop` PR and on the release PR to `main`.
