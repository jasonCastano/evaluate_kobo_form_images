# 🤝 Contributing guide

Thanks for contributing to **Evaluate Kobo Form Images**. The project's source of truth is
[`CONSTITUTION.md`](./CONSTITUTION.md) — read it first.

## 1. Environment

```bash
git clone https://github.com/jasonCastano/evaluate_kobo_form_images.git
cd evaluate_kobo_form_images
make dev                 # uv sync + pre-commit install
cp .env.example .env     # set KOBO_API_TOKEN
make run                 # start the app
```

- Dependencies are managed **only** with `uv` (`uv add <pkg>`, `uv add --dev <pkg>`).
  `pip` and `requirements.txt` are forbidden.
- Never commit field data (Kobo forms, exports, evaluations, images) or tokens.

## 2. Branches

Create a branch from **`develop`** (`git switch develop; git pull --ff-only`) with a type
prefix (or the Spec Kit `NNN-feature-name`). `main` is the user-facing branch and only receives
releases (see [`DEVELOPMENT.md`](./DEVELOPMENT.md)).

| Prefix | Use |
|--------|-----|
| `feat/` | New feature |
| `fix/` | Bug fix |
| `docs/` | Documentation |
| `refactor/` | Refactor without behavior change |
| `test/` | Tests |
| `chore/` | Maintenance / tooling |

## 3. Code standards

- Ruff (lint + format), `ty` type checking and pytest must pass: `make check`.
- Type hints and docstrings on public functions and classes.
- Tests follow the AAA pattern and use **synthetic** fixtures (`tests/conftest.py`).
- Everything in English: UI, code, comments, docs, reports and commit messages.

## 4. Commits

Use [Conventional Commits](https://www.conventionalcommits.org/) in the imperative mood:

```text
feat: add next-pending navigation
fix: map label headers with group prefixes
docs: explain Kobo token setup
```

**Authorship rule:** commits are authored by humans with their own Git identity. Do **not**
add `Co-Authored-By:` trailers for AI assistants or bots, and do not use bot identities.

## 5. Pull Requests

1. Run `make check` locally.
2. Push the branch and open a PR **to `develop`** using the template
   (`gh pr create --base develop`).
3. Update `CONSTITUTION.md` in the same PR if you change architecture, technology or process.
4. CI must be green; merge with **Squash & Merge** and delete the branch.
5. Releases to `main` are done by the maintainer with `scripts/release_to_main.py`.
