# Feature Specification: Up-to-date Repository and Detailed README User Guide

**Feature Branch**: `003-readme-user-guide`

**Created**: 2026-11-13

**Status**: Draft

**Input**: User description (originally in Spanish): "Update the repository, update the
repository README and add the latest changes. Add to the README a detailed explanation of how
the app works and how to use the interface."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A new evaluator learns to use the interface from the README alone (Priority: P1)

A field-data reviewer who has never seen the app opens the repository page and, following only
the README, installs it, starts it, signs in to Kobo, loads a form and its data export, evaluates
images, exports the Excel report to a folder, and later resumes the work from that report —
without asking the maintainer for help.

**Why this priority**: The README is the only onboarding material; the app has grown (Kobo
sign-in, local report saving, resume from a report) and the current README describes the
interface only in a few lines, so new evaluators cannot work independently.

**Independent Test**: Give the README to a person who has not used the app; they complete the
full workflow (install → start → sign in → load files → evaluate 5 images → export → resume
from the report) on their own computer.

**Acceptance Scenarios**:

1. **Given** a computer with the prerequisites, **When** the reader follows the README
   "Getting started" steps, **Then** the app opens in the browser without any step that is not
   written in the README.
2. **Given** the app is open, **When** the reader follows the "Using the interface" guide,
   **Then** every sidebar section (1. Kobo form, 2. Collected data, 3. Kobo account,
   4. Report) and every main-area control (counters, filters, navigation, image, details,
   evaluation form) is explained with its purpose and how to use it.
3. **Given** the reader needs to sign in, **When** they read the Kobo account section, **Then**
   it explains both options (username & password, API key), when to use each (SSO /
   two-factor accounts), where to find the API key, and that the password is never stored.
4. **Given** the reader wants to stop and continue another day or on another computer, **When**
   they read the report section, **Then** it explains where the report is saved, how files are
   named, how to import a previous report, what the import summary means and where the viewer
   continues.

---

### User Story 2 - A reviewer understands how the app works and what to expect (Priority: P2)

A project lead or data manager reads the README to understand how the app works end to end:
what the inputs are, how images are found in the Kobo export, how evaluations are stored and
merged, what each column of the Excel report means, and what messages mean when something
fails.

**Why this priority**: Trust in the evaluation results depends on understanding traceability
and how evaluations are kept and merged; it also reduces support questions.

**Independent Test**: A reader answers, from the README only, a fixed set of questions: Which
files do I need? Why are images not shown before signing in? Where are evaluations saved? What
happens if I import a report twice? What does "not matched" mean? Which reasons can mark an
image invalid?

**Acceptance Scenarios**:

1. **Given** the README, **When** the reader looks for "how it works", **Then** they find the
   end-to-end flow (form + export → images → sign-in → evaluation → autosave → report → resume)
   including a simple diagram.
2. **Given** the reader sees an error or warning in the app, **When** they look it up in the
   README troubleshooting section, **Then** the most common messages (sign-in errors, access
   expired, no access to an image, Kobo unreachable, report could not be saved, report import
   rejections, unmapped columns) are listed with their cause and what to do.
3. **Given** the reader opens an exported report, **When** they read the report section,
   **Then** every sheet and the meaning of the key columns are documented.

---

### User Story 3 - The repository's main version reflects the latest changes (Priority: P3)

Anyone who opens the repository (main page and default branch) sees the latest version of the
app — with Kobo sign-in, local report saving and resume from a report — and a README that
matches it.

**Why this priority**: Today the latest work (sign-in, local export, resume) is only on review
branches; the default branch and its README still describe the first version.

**Independent Test**: Open the repository's main page: the README describes the current
features, and the default branch contains them.

**Acceptance Scenarios**:

1. **Given** the latest features are approved, **When** the repository is updated, **Then** the
   default branch contains the sign-in, local report saving and resume features together with
   the updated README.
2. **Given** the repository is updated, **When** the automated quality checks run, **Then** they
   pass.

---

### Edge Cases

- Readers on Windows vs. macOS/Linux: commands are given for Windows (PowerShell) first, which is
  the team's platform, with the equivalent for other systems where they differ.
- Readers without `make`: an alternative command is given for every `make` target used in the
  guide.
- A machine with a global `UV_PROJECT_ENVIRONMENT` setting: the README explains the symptom and
  the workaround.
- Screenshots containing field data or personal information must not be published; any image in
  the README uses synthetic data or illustrative mock-ups only.
- Features still under manual validation are described as they behave in the current code; no
  feature is documented that does not exist.

## Requirements *(mandatory)*

### Functional Requirements

**README content**

- **FR-001**: The README MUST contain a "How it works" section describing the end-to-end flow
  (inputs, image discovery in the export, Kobo sign-in, evaluation, autosave, report, resume),
  with a simple diagram.
- **FR-002**: The README MUST contain a step-by-step "Using the interface" guide covering, in
  order of use: starting the app, the four sidebar sections, the counters and progress bar,
  filters, navigation (including *Save & next* and *Next pending*), the image area and its
  messages, the image details, the evaluation form (valid/invalid, reasons, comments, clear),
  exporting the report and resuming from a report.
- **FR-003**: The guide MUST document the four invalid reasons exactly as shown in the app and
  the rule that an invalid image needs at least one reason.
- **FR-004**: The README MUST explain Kobo sign-in options, when to use each, where to get an
  API key, the optional automatic sign-in from the configuration file, and the privacy
  guarantees (password used once and never stored; key kept only for the session and sent only
  to the Kobo server).
- **FR-005**: The README MUST explain where evaluations are autosaved, where reports are saved,
  the report naming rule (never overwritten), how import merges evaluations (newer wins, nothing
  deleted, importing twice changes nothing) and what each item of the import summary means.
- **FR-006**: The README MUST document the report sheets and key columns.
- **FR-007**: The README MUST include a troubleshooting section with the common messages listed
  in User Story 2, scenario 2, each with cause and action.
- **FR-008**: The README MUST list all configuration options (Kobo key, forms folder, data
  folder, evaluations folder, image cache folder, reports folder) with defaults.
- **FR-009**: The table of contents, features table, status table and repository structure MUST
  reflect the current code (including the sign-in and report-import modules).
- **FR-010**: All README text MUST be in English; it MUST NOT contain real field data, tokens or
  personal information.
- **FR-011**: The project's governing document MUST stay consistent with the README (same
  feature list and configuration names).

**Repository update**

- **FR-012**: The latest changes MUST be delivered to the repository through the normal review
  flow (branch, conventional commit by the human maintainer, pull request, green automated
  checks).
- **FR-013**: The default branch MUST end up containing the sign-in feature, the local report /
  resume feature and the updated README. Decision (maintainer, 2026-11-13): merge the two open
  pull requests (#1 Kobo sign-in, then #2 local report and resume) into the default branch now,
  without waiting for the remaining manual validation of #2, and deliver the README update as a
  new pull request created from the updated default branch.
- **FR-014**: Before merging, each pull request MUST have green automated checks; #2 MUST target
  the default branch (not the sign-in branch) when it is merged, and the merge history MUST keep
  the maintainer as the only author (no bot or AI attribution).

### Key Entities

- **README**: the repository's main documentation page; sections: overview, features, how it
  works, getting started, using the interface, Kobo account, report and resume, configuration,
  troubleshooting, quality, structure, contributing, license.
- **Open pull requests**: #1 (Kobo sign-in) and #2 (local report saving and resume, stacked on
  #1); both are merged into the default branch as part of this feature (FR-013).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time evaluator completes the full workflow (install → start → sign in →
  load → evaluate 5 images → export → resume) in under 30 minutes using only the README.
- **SC-002**: The README answers 100% of the six questions of User Story 2's independent test.
- **SC-003**: 100% of the visible sidebar sections and main-area controls of the current app are
  described in the guide.
- **SC-004**: Every error or warning message listed in FR-007 appears in the troubleshooting
  section with a cause and an action.
- **SC-005**: After the update, the default branch's README and code describe the same features
  (no undocumented feature and no documented-but-missing feature).

## Assumptions

- The README remains a single file (no separate documentation site); long parts may use
  collapsible sections to stay readable.
- Diagrams are text-based (rendered by the repository host) rather than images, so they stay
  editable and contain no field data. No real screenshots are added unless made from synthetic
  data.
- Windows/PowerShell is the primary platform for commands; macOS/Linux equivalents are noted
  only where they differ.
- The README describes the code as it is on the latest feature branch (sign-in + local report
  and resume).
- The maintainer accepted merging #2 before its full manual quickstart; any issue found later is
  handled as a follow-up fix on the default branch. Automated checks are still required.
