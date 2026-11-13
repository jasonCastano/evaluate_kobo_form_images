# Feature Specification: User-only Main Branch and Developer Branch

**Feature Branch**: `004-clean-user-main`

**Created**: 2026-11-13

**Status**: Draft

**Input**: User description (originally in Spanish): "ONLY the files needed for a new user to
install and run the interface must remain in the repository. Files such as agents, Claude
information, Spec Kit and the CONSTITUTION are information for the developer, not the user. We
can keep all of that in a developer branch, but the main branch must be completely clean,
transparent and clear for users."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A new user sees only what they need on the main branch (Priority: P1)

A field-data reviewer opens the repository page. The default branch shows only the application,
the files needed to install and run it, the license and a README written for users. There are no
AI-assistant folders, specification documents, governance files or contributor templates to
confuse them. Following the README they install and start the interface successfully.

**Why this priority**: This is the explicit goal: the default branch must be clean, transparent
and clear for users.

**Independent Test**: List the files of the default branch and compare them with the approved
user file list (Key Entities); then, on a clean computer, clone the default branch and follow the
README until the interface opens.

**Acceptance Scenarios**:

1. **Given** the default branch, **When** a visitor lists its files, **Then** only files from the
   approved user file list are present.
2. **Given** a clean computer with the documented prerequisites, **When** a user clones the
   default branch and follows its README, **Then** the interface installs and opens without errors
   and without needing any removed file.
3. **Given** the README of the default branch, **When** a user reads it, **Then** it contains no
   references to removed developer material (governance document, AI assistants, specifications,
   contributor workflow) and no broken links.

---

### User Story 2 - The developer keeps all project knowledge on a developer branch (Priority: P2)

The maintainer (and future developers or AI assistants) work on a developer branch that keeps
everything: specifications, governance document, assistant configuration, contribution guides,
tests and automation. Nothing that exists today is lost.

**Why this priority**: The developer material is valuable and required by the project's own
working method; removing it from the default branch must not destroy it.

**Independent Test**: Compare the developer branch with the current default branch (before
cleaning) plus the pending README work: every file is still present on the developer branch.

**Acceptance Scenarios**:

1. **Given** the cleanup is done, **When** the maintainer switches to the developer branch,
   **Then** every file that existed before (including the pending README guide) is there with
   its history.
2. **Given** the developer branch, **When** the automated quality checks run, **Then** they pass.
3. **Given** a developer opens the repository, **When** they read the default branch README,
   **Then** a short note tells them where the developer branch is.

---

### User Story 3 - New versions reach the user branch without reintroducing developer files (Priority: P3)

When the maintainer finishes new work on the developer branch, they publish it to the default
branch through a repeatable, documented release step that brings the updated application and user
documentation but never the developer-only files.

**Why this priority**: Without a defined release step, the next update would either reintroduce
developer files on the default branch or require manual cleanup every time.

**Independent Test**: Make a small change on the developer branch (e.g. in the application and a
specification), run the release step, and check that the default branch receives the application
change but not the specification.

**Acceptance Scenarios**:

1. **Given** a change on the developer branch touching both user and developer files, **When**
   the release step runs, **Then** only the user files change on the default branch.
2. **Given** the release step, **When** it is documented, **Then** the documentation lives on the
   developer branch (not on the default branch).

---

### Edge Cases

- Files needed to install but that look "technical" (dependency manifest, lock file, Python
  version pin, app runtime settings, environment template, line-ending rules) must stay: removing
  them would break installation.
- The open README pull request (#3) is based on the default branch and contains developer
  material (its specification folder and governance edits); it must not land on the cleaned
  default branch as-is.
- Links on external pages or badges pointing to removed files (e.g. a CI badge) must not appear
  broken on the default branch.
- AI-assistant settings that enforce "no AI attribution" in commits only matter where development
  happens (developer branch).
- Old commits of the default branch still contain the removed files in its history unless the
  history is rewritten (see FR-010).

## Requirements *(mandatory)*

### Functional Requirements

**Default branch content**

- **FR-001**: The default branch MUST contain only the approved user file list: the application
  source, the files required to install and run it (dependency manifest and lock file, Python
  version pin, app runtime settings, environment template, ignore/attribute files, launcher
  configuration), the license and the user README.
- **FR-002**: The default branch MUST NOT contain: AI-assistant configuration and skills, Spec Kit
  configuration, the `specs/` folder, the governance document and its Spec Kit copy, agent
  instructions, the contribution guide, the code of conduct, the internal docs folder, issue/PR
  templates and repository-label automation, and editor rules for other agents.
- **FR-003**: The default-branch README MUST be a user README: overview, features, how it works,
  getting started, using the interface, Kobo account, reports, Excel report reference,
  configuration, troubleshooting, quality checks (commands only), license, plus one line pointing
  developers to the developer branch. Developer sections (contributing workflow, specifications,
  governance, AI assistants) MUST be removed, and no link may point to a removed file.
- **FR-004**: Installing and starting the interface from a fresh clone of the default branch MUST
  work exactly as documented in its README.
- **FR-005**: Decision (maintainer, 2026-11-13, option C): the default branch KEEPS the automated
  tests, the continuous-integration check (with its badge), the quality hooks it runs, the task
  runner (short commands such as `make run`) and the development dependencies; only AI-assistant,
  Spec Kit and internal documentation/governance material is removed. The README may keep a short
  "Quality checks" section describing these commands, without contributor-workflow content.

**Developer branch**

- **FR-006**: A developer branch MUST be created from the current default branch plus the pending
  README work (PR #3) and MUST keep every existing file and its history.
- **FR-007**: The developer branch MUST become the base for all future development (new feature
  branches start from it and merge back into it), and the project's governance document and
  assistant instructions MUST be updated to say so.

**Release flow**

- **FR-008**: A documented, repeatable release step MUST publish the user files from the developer
  branch to the default branch without bringing developer-only files, and MUST be checkable (it
  reports which files it changed).
- **FR-009**: Changes to the default branch MUST still go through a pull request authored by the
  human maintainer, with no bot or AI attribution.

**History**

- **FR-010**: Decision (maintainer, 2026-11-13, option A): the default-branch history is NOT
  rewritten; it is enough that the current default branch no longer contains the developer files.
  No force-push is allowed.

### Key Entities

- **Approved user file list** (default branch): `src/` (application), `pyproject.toml`,
  `uv.lock`, `.python-version`, `.streamlit/config.toml`, `.env.example`, `.gitignore`,
  `.gitattributes`, `.editorconfig`, `LICENSE`, `README.md`, and (FR-005) `tests/`,
  `.github/workflows/ci.yml`, `.pre-commit-config.yaml`, `Makefile`.
- **Developer-only files** (developer branch only): `.claude/`, `.specify/`, `.opencode/`,
  `specs/`, `CONSTITUTION.md`, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
  `docs/`, `.github/ISSUE_TEMPLATE/`, `.github/pull_request_template.md`, `.github/labels.yml`,
  `.github/workflows/labels.yml`.
- **Default branch** (`main`): user-facing, released versions.
- **Developer branch**: complete project, base for development.
- **Release step**: the procedure that copies user files from the developer branch to the default
  branch.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the files on the default branch belong to the approved user file list.
- **SC-002**: A new user installs and opens the interface from the default branch in under 15
  minutes following only its README.
- **SC-003**: 0 broken links and 0 references to removed developer material in the default-branch
  README.
- **SC-004**: 100% of the files that existed before the cleanup are present on the developer
  branch.
- **SC-005**: A release from the developer branch changes 0 developer-only files on the default
  branch.

## Assumptions

- Developer branch name: `develop` (conventional; can be renamed).
- The default branch stays `main` and remains the branch shown to visitors and cloned by default.
- The repository stays private; this feature changes what is visible to users with access, not
  who has access.
- The pending README guide (PR #3) is preserved on the developer branch; its user content becomes
  the base of the default-branch README, with developer sections removed.
- The maintainer's earlier project standard (governance document, Spec Kit, assistant files) keeps
  applying on the developer branch; the user's explicit request overrides it for the default
  branch.
