<!--
Thank you for contributing to Evaluate Kobo Form Images.
Fill in every applicable section. Before opening this PR, make sure you have read CONSTITUTION.md.
-->

## 📝 PR title convention

Use a [Conventional Commits](https://www.conventionalcommits.org/) prefix in the title:

| Prefix | When | Example |
|--------|------|---------|
| `feat:` | New feature | `feat: add gallery view` |
| `fix:` | Bug fix | `fix: match label headers with group prefix` |
| `docs:` | Documentation | `docs: document Kobo token setup` |
| `refactor:` | Refactor without behavior change | `refactor: split export scanner` |
| `test:` | Add or fix tests | `test: cover duplicate labels` |
| `chore:` | Maintenance or configuration | `chore: update uv lock` |

> The title must be descriptive, imperative and a single line.

---

## 📚 Description

<!-- What does this change do and why? -->

**Resolves:** <!-- Closes #N -->

### In-scope changes

<!-- Short list of the main changes. -->

### Out of scope / other changes

<!-- Ideally empty. -->

---

## 🧪 How it was tested

```bash
# Commands run (e.g. make check)
```

| Case / scenario | Expected | Observed |
|-----------------|----------|----------|
|  |  |  |

---

## ✅ Pre-PR checklist

See **[`CONSTITUTION.md`](../CONSTITUTION.md)** for the detailed standards.

- [ ] **Type hints and docstrings** on new/changed code.
- [ ] **Tests** pass (`make check`).
- [ ] **Lint and format** clean (`make lint` / `make format`).
- [ ] **`uv.lock` updated** if any dependency changed.
- [ ] **No secrets** committed (`.env`, Kobo tokens, keys).
- [ ] **No field data** committed (Kobo forms, exports, evaluations, images).
- [ ] **No bot or AI co-author trailers** in commits (see CONSTITUTION §7).
- [ ] **`CONSTITUTION.md` updated** if there was an architectural, technology or process change.
- [ ] **README / docs** updated if applicable.

---

## 🚀 Merge

- [ ] Reviewed and approved.
- [ ] Branch up to date with `main`.
- [ ] **Squash & Merge**, then delete the branch.
