# Contract: repository update procedure (FR-012 – FR-014)

All commands run from the repository root with the maintainer's authenticated `gh`.

1. Pre-checks
   - `gh pr checks 1` and `gh pr checks 2` → all successful.
   - `git status` clean except the untracked `specs/003-readme-user-guide/`.
2. Merge #1 → `main`
   - `gh pr ready 1` (leave draft state)
   - `gh pr merge 1 --merge --delete-branch --subject "feat: sign in to Kobo from the sidebar (#1)"`
   - Expect GitHub to retarget #2 to `main` (`gh pr view 2 --json baseRefName` = `main`).
3. Merge #2 → `main`
   - Wait for #2 CI on the new base: `gh pr checks 2 --watch` → green.
   - `gh pr ready 2`
   - `gh pr merge 2 --merge --delete-branch --subject "feat: save reports locally and resume from a previous report (#2)"`
4. Local sync
   - `git checkout main && git pull --ff-only`
   - `git branch -d 001-kobo-account-login 002-report-export-resume` (only if fully merged)
5. Verify
   - `git log --format='%an | %s' -5` → only the maintainer as author.
   - `make check` on `main` → green.

Forbidden: force-push, direct push to `main`, `--admin` override of failing checks, any
`Co-authored-by` / "Generated with" text in merge subjects or bodies.
