<div align="center">

# Evaluate Kobo Form Images

**Review the quality of images collected with KoboToolbox forms, flag the bad ones and export the evaluation to Excel.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/jasonCastano/evaluate_kobo_form_images/actions/workflows/ci.yml/badge.svg)](https://github.com/jasonCastano/evaluate_kobo_form_images/actions/workflows/ci.yml)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Managed with uv](https://img.shields.io/badge/managed%20with-uv-de5fe9.svg)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=precommit&logoColor=white)](./.pre-commit-config.yaml)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-fe5196.svg)](https://conventionalcommits.org)

</div>

---

## 📖 Overview

Field teams collect thousands of photos with [KoboToolbox](https://www.kobotoolbox.org/)
forms. Before those images are used, someone has to check that each one was captured
properly. **Evaluate Kobo Form Images** is a local web app that:

1. Loads a **Kobo form** (XLSForm `.xlsx`) and finds all of its `image` questions — including
   those inside groups and repeat groups, in any label language.
2. Loads the **data exported from Kobo** for that form (`.xlsx`, every sheet, either
   *XML values and headers* or *Labels* headers) and lists every collected image link.
3. Shows each image with its context (question, submission, enumerator, row) so the
   evaluator can mark it **Valid** or **Invalid**. Invalid images need one or more reasons:
   - Low lighting
   - Too bright / overexposed
   - Out of focus / blurry
   - Invalid image content

   plus optional **free-text comments**.
4. **Exports an Excel report** that links every evaluation to its form, data file, sheet,
   row, submission, question and image.

> 📘 The technical source of truth (stack, rules, architecture and decisions) is
> [`CONSTITUTION.md`](./CONSTITUTION.md). Read it before contributing.

## 📑 Table of contents

- [Overview](#-overview)
- [Features](#-features)
- [Tech stack](#️-tech-stack)
- [Getting started](#-getting-started)
- [Using the app](#️-using-the-app)
- [Excel report](#-excel-report)
- [Quality and automation](#-quality-and-automation)
- [Repository structure](#-repository-structure)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Features

| Feature | Details |
|---------|---------|
| Any XLSForm | Parses `survey`/`settings`; groups, repeats and multilingual labels. |
| Any Kobo export | All sheets; XML-name or label headers; group prefixes; duplicate labels resolved in form order. |
| No image lost | Image columns that do not match the form are still listed and flagged. |
| Authenticated download | Uses your Kobo API token; EXIF rotation, resizing, disk cache and prefetch of the next images. |
| Fast review | Filters by question, status and enumerator; *Save & next*; *Next pending*. |
| Autosave & resume | Every decision is saved immediately to `evaluations/<form>__<export>.json`. |
| Traceable report | Excel with `Evaluations`, `Summary by question` and `Metadata` sheets. |

## 🛠️ Tech stack

| Category | Technology |
|----------|------------|
| **Language** | Python 3.13+ |
| **Package manager** | [`uv`](https://docs.astral.sh/uv/) |
| **UI** | [Streamlit](https://streamlit.io/) |
| **Excel** | [openpyxl](https://openpyxl.readthedocs.io/) |
| **HTTP / images** | requests, Pillow |
| **Typing / lint / tests** | [`ty`](https://github.com/astral-sh/ty), [Ruff](https://docs.astral.sh/ruff/), [pytest](https://docs.pytest.org/) |
| **CI** | [GitHub Actions](.github/workflows/ci.yml) |

## 🚀 Getting started

### Prerequisites

- [Python 3.13+](https://www.python.org/downloads/)
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
- [Git](https://git-scm.com/) and (optionally) GNU `make`
- A **KoboToolbox API token** with access to the project (Kobo → *Account settings* →
  *Security* → *API key*). Kobo attachment links are private and return *404* without it.

### Installation

```bash
git clone https://github.com/jasonCastano/evaluate_kobo_form_images.git
cd evaluate_kobo_form_images

make dev                   # = uv sync + pre-commit install
cp .env.example .env       # then set KOBO_API_TOKEN in .env
```

> 💡 The `Makefile` forces a project-local `.venv`. If you run `uv` directly and your
> machine defines `UV_PROJECT_ENVIRONMENT`, prefix the commands with
> `UV_PROJECT_ENVIRONMENT=.venv`.

### Run

```bash
make run                   # or: uv run evaluate-kobo-images
```

The app opens at <http://localhost:8501>.

## 🖥️ Using the app

1. **Put your files in place** (optional): forms in `forms/`, Kobo exports in `data/`
   (subfolders allowed). Both folders are git-ignored. You can also upload files directly
   from the sidebar.
2. In the sidebar select the **form**, then the matching **data export**, type your
   **evaluator name** and (if not in `.env`) the **Kobo API token**.
3. Use the filters (question, status, submitted by) and the navigation buttons to move
   through the images.
4. For each image choose **Valid** or **Invalid**; for *Invalid* tick at least one reason;
   add comments if needed; press **Save & next**.
5. In the sidebar, **Build Excel report** → **Download Excel**.

Evaluations are autosaved; reopening the same form and export resumes where you left off.

## 📊 Excel report

| Sheet | Content |
|-------|---------|
| `Evaluations` | One row per image: form file and title, data file, data sheet, Excel row, submission ID/UUID/time, submitted by, Kobo validation status, repeat and parent index, question name/label/group, export column, image file name, image URL (hyperlink), image key, **evaluation status** (`Valid`/`Invalid`/`Pending`), one *Yes* column per reason, reasons text, comments, evaluator and timestamp. |
| `Summary by question` | Totals per question: valid, invalid, pending and count per reason. |
| `Metadata` | Form, data file, number of images, evaluator, generation time and app version. |

## ✅ Quality and automation

| Command | Description |
|---------|-------------|
| `make help` | List all targets. |
| `make dev` | `uv sync` + install pre-commit hooks. |
| `make run` | Start the Streamlit app. |
| `make check` | Lint + format check + type check + tests. |
| `make lint` / `make format` | Ruff. |
| `make test` | pytest. |
| `make clean-cache` | Delete downloaded images cache. |

## 📁 Repository structure

```text
evaluate_kobo_form_images/
├── src/evaluate_kobo_form_images/
│   ├── app.py            # Streamlit UI
│   ├── cli.py            # `evaluate-kobo-images` launcher
│   ├── xlsform.py        # XLSForm parser (image questions)
│   ├── kobo_export.py    # Kobo export scanner (one record per image)
│   ├── kobo_client.py    # authenticated image download + cache
│   ├── evaluation.py     # evaluation model + autosave store
│   └── report.py         # Excel report
├── tests/                # pytest suite (synthetic fixtures)
├── docs/                 # documentation
├── .github/              # CI, PR and issue templates, labels
├── CONSTITUTION.md       # single source of truth
├── Makefile
├── pyproject.toml
└── uv.lock
```

Local, git-ignored folders: `forms/`, `data/`, `evaluations/`, `.cache/`, `.env`.

## 🤝 Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md). In short: branch from `main`, run `make check`,
use [Conventional Commits](https://www.conventionalcommits.org/), open a PR and keep
[`CONSTITUTION.md`](./CONSTITUTION.md) up to date. Commits must be authored by humans only
— no AI/bot co-author trailers.

## 📄 License

Distributed under the [MIT License](./LICENSE).

---

<div align="center">
<sub>Maintained by Jason Alejandro Castaño</sub>
</div>
