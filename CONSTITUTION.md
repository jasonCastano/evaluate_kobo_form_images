# CONSTITUTION — Evaluate Kobo Form Images

> **Single source of truth.** This document defines the purpose, stack, structure,
> conventions and workflow of `Evaluate Kobo Form Images`. If anything here contradicts the
> code, the code wins **and this file is updated**.

> ⚠️ **Maintenance directive:** every significant change (new features, architectural
> changes, new modules/classes or technology changes) **must update this file in the same
> commit**.

---

## 0. Project identity

| Field | Value |
|-------|-------|
| **Name** | Evaluate Kobo Form Images |
| **Description** | Streamlit app to review and grade the quality of images collected with KoboToolbox forms and export the evaluation to Excel. |
| **Repository** | https://github.com/jasonCastano/evaluate_kobo_form_images (private) |
| **Owner / author** | Jason Alejandro Castaño (`jasonCastano`) |
| **License** | MIT |
| **Main branch** | `main` |
| **Status** | Alpha 🚧 (v0.1.0) |

## 1. Purpose and non-purpose

### Purpose

Give field-data reviewers a single interface to **load a KoboToolbox form (XLSForm) and the
data exported from Kobo for that form, look at every image collected, decide whether each
image is valid, record why it is not, and export the evaluation to Excel** with an
unambiguous link between each evaluation and its source form, data file, submission,
question and image.

### Non-purpose

- It is **not** an automatic image-quality classifier (all decisions are human).
- It does **not** edit Kobo data, change validation statuses or upload anything to Kobo.
- It is **not** a general Kobo data-cleaning or analysis tool.

## 2. Scope

### In scope

- Parsing any XLSForm (`survey` + optional `settings`) and listing its `image` questions,
  with groups, repeat groups and multilingual labels.
- Reading Kobo `.xlsx` data exports — every sheet (main table and one sheet per repeat), in
  both **"XML values and headers"** and **"Labels"** header modes, with or without group
  prefixes — and producing one record per image attachment (`<header>_URL` column).
- Signing in to Kobo from the UI (username & password exchanged once for the API key, or
  an API key) and downloading attachments with it (attachments are not public), with a local
  display cache and prefetching of the next images.
- Evaluation per image: **Valid / Invalid**; when invalid, one or more reasons from a closed
  list plus free-text comments.
- Autosave and resume of evaluations per *(form, data export)* pair.
- Excel report (`Evaluations`, `Summary by question`, `Metadata` sheets) saved directly to a
  local folder chosen in the UI (default `exports/`), never overwriting earlier reports.
- Resuming work by importing a previously exported report (merge: newer evaluation wins,
  nothing deleted; viewer continues on the next pending image).

### Out of scope (for now)

- Pulling forms/data directly from the Kobo API (the user supplies the exported files).
- Multi-user concurrent evaluation on a shared server / central database.
- Automatic quality metrics (brightness, blur scores) — candidate for a future spike.

## 3. Domain rules (invariants)

1. **Invalid reasons are a closed list** defined in `evaluation.InvalidReason`:
   `Low lighting`, `Too bright / overexposed`, `Out of focus / blurry`,
   `Invalid image content`. Changing it is a constitutional change (report columns depend on it).
2. An **Invalid** evaluation requires **at least one reason**; a **Valid** one stores none.
   Comments are always optional.
3. Every image record carries a **stable key** = hash of *(submission UUID, sheet, `_index`,
   question, URL)*. Evaluations are stored by this key, so re-loading the same export resumes
   the work.
4. Export columns are matched to questions by XML name first, then by any label (all
   languages), ignoring markup, case, spacing and group prefixes. Duplicate labels are
   resolved in form order. Columns that match no question are **still listed** (flagged as
   unmapped) — **no image may be silently dropped**.
5. The Excel report must always let the reader trace an evaluation back to: **form file,
   form title, data file, data sheet, Excel row, submission ID/UUID, repeat index, question
   name/label/group, image file name and image URL**.
6. **Field data never enters Git:** forms, exports, evaluation JSON files, Excel reports,
   images and Kobo tokens are git-ignored.
7. **English only:** UI, code, comments, docs, reports and commit messages are in English.

## 4. Technical stack

| Category | Technology |
|----------|------------|
| **Language** | Python 3.13+ |
| **Package / environment manager** | [`uv`](https://docs.astral.sh/uv/) |
| **Build backend** | `uv_build` (src-layout) |
| **Python package** | `evaluate_kobo_form_images` |
| **User interface** | [Streamlit](https://streamlit.io/) |
| **Excel read/write** | [openpyxl](https://openpyxl.readthedocs.io/) |
| **HTTP / images** | `requests`, Pillow |
| **Configuration** | `python-dotenv` (`.env`) |
| **Static typing** | [`ty`](https://github.com/astral-sh/ty) |
| **Testing** | [`pytest`](https://docs.pytest.org/) (synthetic fixtures only) |
| **Lint / format** | [Ruff](https://docs.astral.sh/ruff/) |
| **Pre-commit** | [pre-commit](https://pre-commit.com) |
| **CI** | [GitHub Actions](.github/workflows/ci.yml) |
| **Spec-driven development** | [GitHub Spec Kit](https://github.com/github/spec-kit) 1.2.3 (Claude Code skills) |

> ⚠️ **Hard rule:** all dependency and environment management goes through `uv`. `pip` and
> `requirements.txt` are **forbidden**.

## 5. Architecture

```text
 XLSForm (.xlsx) ──► xlsform.parse_xlsform ──► KoboForm (image questions)
                                                   │
 Kobo export (.xlsx) ─────────────► kobo_export.scan_export ──► ImageRecord[] (one per image)
                                                   │
 Kobo /token/, /me/ ◄── kobo_auth.sign_in_* ──► KoboSession (memory only)
 Kobo API (token) ◄── kobo_client.KoboImageClient ◄┤  (host-scoped key + EXIF fix + resize + cache)
                                                   │
                       app.py (Streamlit UI) ──────┤──► evaluation.EvaluationStore (JSON autosave)
                                                   │
                                     report.build_report ──► Excel report (.xlsx)
```

| Module | Responsibility |
|--------|----------------|
| `xlsform.py` | Parse the `survey`/`settings` sheets; image questions with group/repeat paths and labels. |
| `kobo_export.py` | Scan every sheet of a Kobo export, map `_URL` columns to questions, build `ImageRecord`s. |
| `kobo_auth.py` | Kobo servers, sign-in (password → API key via `/token/`, key check via `/me/`), in-memory `KoboSession`. |
| `kobo_client.py` | Host-scoped authenticated attachment download with typed failures, display JPEG conversion, disk cache. |
| `evaluation.py` | `Verdict`, `InvalidReason`, `Evaluation` validation and `EvaluationStore` persistence. |
| `report.py` | Excel report generation and local saving (`save_report`: timestamped name, atomic write, timeout). |
| `report_import.py` | Import of a previous report: validation, matching (key, then URL + question), merge, resume position. |
| `app.py` | Streamlit UI (no business logic beyond orchestration). |
| `cli.py` | `evaluate-kobo-images` console entry point (launches Streamlit). |

**Configuration** (environment or `.env`, see `.env.example`): `KOBO_API_TOKEN`,
`KOBO_FORMS_DIR` (default `forms`), `KOBO_DATA_DIR` (`data`), `EVALUATIONS_DIR`
(`evaluations`), `IMAGE_CACHE_DIR` (`.cache/images`), `REPORTS_DIR` (`exports`).

## 6. Repository structure

```text
evaluate_kobo_form_images/
├── src/evaluate_kobo_form_images/   # package (src-layout) — see §5
├── tests/                           # pytest suite with synthetic XLSForm/export fixtures
├── docs/                            # documentation, ADRs and research
├── .github/                         # PR/issue templates, CI, labels
├── .streamlit/config.toml           # Streamlit settings (upload size, telemetry off)
├── .opencode/rules/                 # agent rules (tgrep)
├── .claude/                         # Claude Code: settings (no AI attribution) + Spec Kit skills
├── .specify/                        # Spec Kit: memory/constitution.md, templates, scripts
├── specs/                           # Spec Kit feature artifacts (specs/NNN-name/)
├── CLAUDE.md                        # instructions for Claude Code
├── forms/  data/                    # LOCAL ONLY (git-ignored): Kobo forms and exports
├── evaluations/  .cache/            # LOCAL ONLY (git-ignored): autosave and image cache
├── exports/                         # LOCAL ONLY (git-ignored): saved Excel reports
├── .env.example                     # configuration template (copy to .env)
├── AGENTS.md                        # context for LLM agents
├── CONSTITUTION.md                  # this file — single source of truth
├── README.md                        # public entry point
├── CONTRIBUTING.md                  # contribution guide
├── CODE_OF_CONDUCT.md               # code of conduct
├── Makefile                         # task automation
├── pyproject.toml                   # metadata and dependencies (uv)
├── uv.lock                          # deterministic lockfile (committed)
├── .python-version                  # pinned Python version
└── .pre-commit-config.yaml          # quality hooks
```

## 7. Code and contribution conventions

- **Style:** PEP 8 / PEP 257 enforced by **Ruff** (`line-length = 100`, double quotes).
- **Typing:** annotations on all functions and public signatures; `ty check` must pass.
- **Naming:** `snake_case` (functions/variables), `PascalCase` (classes), `UPPER_CASE` (constants).
- **Docstrings:** on modules, classes and public functions.
- **Tests:** `pytest`, **AAA** pattern (*Arrange · Act · Assert*), synthetic fixtures built
  in `tests/conftest.py` — never real field data.
- **Language:** English everywhere (UI, code, comments, docs, reports, commits).
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) —
  `feat:`, `fix:`, `docs:`, `refactor:`, `style:`, `test:`, `chore:`.
- **Authorship — no bots or AI as contributors (hard rule):**
  - Every commit is authored and committed by a human maintainer with their own identity.
  - **Forbidden:** `Co-Authored-By:` trailers for Claude or any other AI/bot, bot commit
    identities, and "Generated with ..." footers in commits or PRs.
  - **Dependabot and other bots that open PRs or push commits are not enabled.** Dependency
    updates are done manually with `uv lock --upgrade` (see §8).
  - GitHub Actions workflows must not commit to the repository.

## 8. Quality and automation

| Tool | Role | Command |
|------|------|---------|
| `uv` | Environments and dependencies | `make install` |
| Streamlit | Run the app | `make run` |
| Ruff | Lint + format | `make lint` / `make format` |
| `ty` | Type checking | `make typecheck` |
| `pytest` | Tests | `make test` |
| `pre-commit` | Hooks before every commit | `make pre-commit` |
| GitHub Actions | CI (pre-commit + types + tests) | `.github/workflows/ci.yml` |

- No commit skips the hooks (`--no-verify` is forbidden unless justified and documented).
- **CI must be green** before merging a Pull Request.
- New dependencies go in with `uv add` / `uv add --dev` (never editing `uv.lock` by hand).
- Dependency refresh (manual, monthly or when needed): `uv lock --upgrade && make check`.
- The `Makefile` and CI force `UV_PROJECT_ENVIRONMENT=.venv`, so the project never reuses a
  machine-wide virtual environment.

## 9. Repository and Git

- **Remote:** `https://github.com/jasonCastano/evaluate_kobo_form_images.git` (private)
- **Main branch:** `main`, integrated through Pull Requests.
- **Branches:** `feat/...`, `fix/...`, `docs/...`, `refactor/...`, `test/...`, `chore/...`.

## 10. Spec-driven development (Spec Kit + Claude Code)

New features follow the Spec Kit flow inside Claude Code:
`/speckit-specify` → (`/speckit-clarify`) → `/speckit-plan` → `/speckit-tasks` →
(`/speckit-analyze`) → `/speckit-implement`. Artifacts live in `specs/NNN-feature-name/` and are
committed. Spec Kit's principles file `.specify/memory/constitution.md` is derived from this
document; **both are updated together**. `.claude/settings.json` disables Claude commit/PR
attribution for everyone using the repository.

## 10.1 Daily workflow (commit + push)

```bash
git status                       # 1. review changes
make check                       # 2. lint + format + types + tests
git add -A                       # 3. stage
git commit -m "type: message"    # 4. commit (hooks run automatically)
git push                         # 5. push
```

## 11. Technical decision log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-11-12 | Adopt `uv` as the only environment/dependency manager | Reproducibility; `pip`/`requirements.txt` forbidden |
| 2026-11-12 | Adopt Ruff, `ty`, pre-commit and pytest | Automated quality before every commit |
| 2026-11-12 | Adopt Conventional Commits, MIT license and this constitution | Readable history; legal and operational clarity |
| 2026-11-12 | Streamlit as UI | Pure-Python, local, fast to build image-review forms |
| 2026-11-12 | Read exports with openpyxl (no pandas) | Kobo exports have hundreds of columns and many sheets; row-wise streaming is enough and lighter |
| 2026-11-12 | Match `_URL` columns by name **or** label | Kobo exports may use XML names or labels as headers |
| 2026-11-12 | Download images through the app with a Kobo API token | Kobo attachment URLs return 404 without authentication |
| 2026-11-12 | Autosave evaluations as JSON per (form, export) pair | Never lose work; resume across sessions |
| 2026-11-13 | Save reports server-side to a chosen folder instead of browser download | Browser download ignored the intended folder (feature 002) |
| 2026-11-13 | Resume by importing a previous report; newer evaluation wins, never delete | Multi-session / multi-evaluator review (feature 002) |
| 2026-11-12 | Field data and tokens are git-ignored | Data protection |
| 2026-11-12 | Sign in with Kobo username/password via `/token/` (password used once, key in memory only) | Reviewers know passwords, not API keys (spec 001) |
| 2026-11-12 | Send the API key only to the signed-in server host | Prevent token leakage |
| 2026-11-12 | No AI/bot contributors; Dependabot disabled | Owner requirement: only humans appear as contributors |
| 2026-11-12 | Adopt GitHub Spec Kit (Claude integration, Python scripts) | Spec-driven development with Claude Code; principles mirrored in `.specify/memory/constitution.md` |
| 2026-11-12 | Disable Claude attribution in `.claude/settings.json` | Enforce the human-authorship rule at tool level |
| 2026-11-12 | Force a project-local `.venv` | The workstation sets a global `UV_PROJECT_ENVIRONMENT` shared with another project |

## 12. Notes and roadmap

- [x] Scaffold the project and publish the private repository.
- [x] XLSForm parser, export scanner, evaluation store, Excel report and Streamlit UI.
- [x] Sign in to Kobo from the UI (spec `specs/001-kobo-account-login`).
- [ ] Verify sign-in and image download end-to-end with a real Kobo account (all exports).
- [ ] Protect `main` (require PR + green CI).
- [x] Import a previous Excel report to resume or merge evaluations (spec `specs/002-report-export-resume`).
- [ ] Optional gallery/grid view and keyboard shortcuts for faster review.
- [ ] Spike: automatic brightness / blur scores to pre-sort images.

## 13. Local configuration (not tracked)

- Optional: copy `.env.example` to `.env` and set `KOBO_API_TOKEN` (Kobo → Account settings →
  Security → API key) to sign in automatically; otherwise sign in from the sidebar.
  `.env` is git-ignored.
- Git identity for this repository is the owner's GitHub identity
  (`Jason Alejandro Castaño`, email linked to `jasonCastano`).
