# AGENTS — Evaluate Kobo Form Images

> Project context for sessions with LLM assistants. Tracked in the repository.

## Project

Streamlit app to review and grade the quality of images collected with KoboToolbox forms
and export the evaluation to Excel.

> 📘 The technical source of truth — purpose, stack, architecture, domain rules, decisions
> and workflow — is [`CONSTITUTION.md`](./CONSTITUTION.md). **Read it before acting.** Any
> architectural, technology or process change must update it in the same commit.

## Hard rules for agents

- **English only** in code, UI, docs, reports and commit messages.
- **No AI/bot attribution:** never add `Co-Authored-By:` trailers, "Generated with" footers
  or bot identities to commits or PRs. Commits use the human maintainer's Git identity.
- **Never commit field data or secrets:** `forms/`, `data/`, `evaluations/`, `.cache/`,
  `*.xlsx`, `.env` are git-ignored on purpose.
- **`uv` only** for dependencies (`uv add`); `pip` and `requirements.txt` are forbidden.
- Use the `Makefile` (it forces `UV_PROJECT_ENVIRONMENT=.venv`); if calling `uv` directly,
  set `UV_PROJECT_ENVIRONMENT=.venv` because this workstation defines a global one.
- Keep business logic out of `app.py`; it belongs in `xlsform.py`, `kobo_export.py`,
  `kobo_client.py`, `evaluation.py` or `report.py`, with tests.

## Commands

```bash
make help      # list targets
make dev       # environment + pre-commit hooks
make run       # start the Streamlit app
make check     # lint + format + types + tests
```

## Commit convention

[Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`,
`refactor:`, `style:`, `test:`, `chore:`.

## Code search: `tgrep`

If [`tgrep`](https://github.com/microsoft/tgrep) is installed, prefer it over `grep`/`find`
(see [`.opencode/rules/tgrep.md`](./.opencode/rules/tgrep.md)). Otherwise use `rg`/`grep`.
