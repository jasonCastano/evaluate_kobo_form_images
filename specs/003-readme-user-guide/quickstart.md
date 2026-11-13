# Quickstart: validate the repository update and the README guide

**Feature**: [spec.md](./spec.md) · Contracts: [readme-content](./contracts/readme-content.md),
[merge-procedure](./contracts/merge-procedure.md)

## 1. Repository state (User Story 3)

| Check | Command / action | Expected |
|-------|------------------|----------|
| PRs merged | `gh pr list --state merged` | #1 and #2 merged into `main` |
| Default branch has the features | `git log --oneline main` / browse `src/` on GitHub | `kobo_auth.py`, `report_import.py` present |
| Authors | `git log --format='%an' main \| sort -u` | only the maintainer |
| CI | Actions tab on `main` | green |

## 2. README accuracy (automated)

```bash
make check
uv run pre-commit run --all-files
```

Plus the scripted checks from tasks.md: every `code`-quoted UI string of the README exists in
`src/`; every relative link and `#anchor` resolves.

## 3. README rendering (manual, on GitHub)

- Mermaid diagram renders; tables and `<details>` blocks render; TOC links jump correctly.

## 4. Reader tests (manual)

- **Six-question test** (User Story 2): answer the six questions of
  [readme-content](./contracts/readme-content.md#six-question-test-sc-002) using only the README.
- **First-time evaluator** (User Story 1, SC-001): someone who never used the app follows the
  README from install to "resume from a report" with real data in < 30 minutes, noting every
  step that was unclear.
