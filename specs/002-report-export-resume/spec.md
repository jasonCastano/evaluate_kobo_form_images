# Feature Specification: Save Report Locally and Resume from a Previous Report

**Feature Branch**: `002-report-export-resume`

**Created**: 2026-11-12

**Status**: Draft

**Input**: User description (originally in Spanish, from the manual test of feature 001): "Sign-in,
image display, evaluation and navigation work correctly. Exporting the Excel report did not
work: the report was built but could not be downloaded to the chosen folder. When the user
chooses to export the report, it must be written locally to the given path, not downloaded
through the browser. Additionally, the evaluator must be able to upload a previously exported
report and continue evaluating from the last image evaluated in that report; the loaded
information must not be lost when a new report is generated."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Save the Excel report directly to a local folder (Priority: P1)

The evaluator finishes (or pauses) a review session and presses "Export report". The app
writes the Excel report straight into a folder on the computer — a default reports folder or
a folder the evaluator types — and confirms the full path of the saved file. Nothing goes
through the browser's download dialog.

**Why this priority**: Exporting is the deliverable of the whole review. Today the report is
built but never reaches the intended folder, so the evaluation work cannot be handed over.

**Independent Test**: Evaluate a few images, set the output folder, press "Export report",
and open the file at the path shown by the app; it contains the evaluations.

**Acceptance Scenarios**:

1. **Given** the evaluator has evaluated some images and the output folder exists, **When**
   they press "Export report", **Then** an Excel file is written to that folder and the app
   shows "Report saved to <full path>".
2. **Given** the evaluator types an output folder that does not exist yet, **When** they press
   "Export report", **Then** the folder is created and the report is saved there.
3. **Given** the output path cannot be written (no permission, invalid path, file open in
   another program), **When** they press "Export report", **Then** the app shows a clear
   error naming the path and the reason, and no evaluation is lost.
4. **Given** a report was already exported earlier in the day, **When** the evaluator exports
   again, **Then** a new file with a different name is created and the earlier file is not
   overwritten.

---

### User Story 2 - Resume evaluation from a previously exported report (Priority: P2)

An evaluator (the same person on another day or computer, or a colleague) loads the form and
its data export, then uploads a report exported earlier. The app restores every evaluation
from the report (verdict, reasons, comments, evaluator, date), shows how many were restored,
and moves straight to the image right after the last evaluated one so work continues where it
stopped.

**Why this priority**: Large exports (thousands of images) are reviewed over several sessions
and sometimes by different people or computers; without resuming from a report, work must be
redone.

**Independent Test**: Export a report with N evaluations, start from a clean session (no
local autosave), load the same form and data export, upload the report, and check that the
counters show N evaluated and the current image is the one after the last evaluated image.

**Acceptance Scenarios**:

1. **Given** a form and its data export are loaded, **When** the evaluator uploads a report
   generated for that form and export, **Then** all evaluations in the report are restored and
   the app shows "Restored N evaluations from <report file>".
2. **Given** the report has been restored, **When** the import finishes, **Then** the viewer
   opens on the first not-yet-evaluated image that comes after the last evaluated image of the
   report (wrapping to the first pending image if none follows).
3. **Given** evaluations were restored, **When** the evaluator evaluates more images and
   exports a new report, **Then** the new report contains both the restored and the new
   evaluations — nothing restored is lost.
4. **Given** the uploaded report belongs to a different form or data export, **When** it is
   uploaded, **Then** the app warns which form/data file the report belongs to, restores only
   the evaluations that match images in the current export, and reports how many rows could
   not be matched.
5. **Given** the uploaded file is not a report produced by this app (missing required
   columns), **When** it is uploaded, **Then** the app rejects it with a clear message and the
   current evaluations stay unchanged.

---

### User Story 3 - Merge a report with evaluations already in progress (Priority: P3)

The evaluator already has evaluations saved for this form and export (autosave) and uploads a
report that overlaps with them. The app combines both without losing anything, keeping the
most recent decision when the same image appears in both.

**Why this priority**: Prevents accidental loss when a colleague's report is loaded on top of
local work, but the common case (fresh session) is covered by User Story 2.

**Independent Test**: Evaluate images A and B locally; upload a report containing B (older
decision) and C; check that A, the newer B and C are all kept.

**Acceptance Scenarios**:

1. **Given** local evaluations exist, **When** a report with overlapping images is uploaded,
   **Then** images only in one source are kept, and for images in both the evaluation with
   the most recent evaluation date is kept.
2. **Given** a merge happened, **When** it finishes, **Then** the app shows how many
   evaluations were added, updated, and kept unchanged.

---

### Edge Cases

- A report row whose image no longer exists in the current export (e.g. submission deleted
  in Kobo): it cannot be shown, is counted as "not matched" and listed in the import summary.
- The same report is uploaded twice: the second import changes nothing and says so.
- A report row marked "Invalid" without reasons, or with an unknown reason text: the row is
  skipped and reported as invalid (not silently changed).
- A report exported without pending images vs. with pending images: both can be imported;
  "Pending" rows are ignored.
- All images are already evaluated after import: the app says the review is complete and
  shows the last image.
- The output folder is on a network or synced drive that is slow or offline: the error message
  appears instead of the app freezing indefinitely.
- Very large reports (≈10,000 rows) import without the evaluator having to wait more than a
  short moment.

## Requirements *(mandatory)*

### Functional Requirements

**Local export**

- **FR-001**: The app MUST let the evaluator choose the output folder for reports, pre-filled
  with a default reports folder inside the project, and remember the last folder used during
  the session.
- **FR-002**: Pressing "Export report" MUST write the Excel report directly to the chosen
  folder on the computer where the app runs, without using the browser download dialog.
- **FR-003**: The app MUST create the output folder if it does not exist.
- **FR-004**: Each export MUST create a new file whose name includes the form name and the date
  and time of export, so previous reports are never overwritten.
- **FR-005**: After a successful export, the app MUST show the full path of the saved file;
  after a failure, it MUST show the path and a plain-language reason.
- **FR-006**: The exported report MUST keep the current content and traceability (form, data
  file, sheet, row, submission, question, image, evaluation) and the option to include or
  exclude images not evaluated yet.

**Resume from a report**

- **FR-007**: The app MUST let the evaluator upload a previously exported report once a form
  and its data export are loaded.
- **FR-008**: The app MUST restore each evaluated row of the report (verdict, invalid reasons,
  comments, evaluator, evaluation date) and link it to the matching image of the current
  export using the report's image identifier, falling back to the image link together with the
  question when the identifier does not match.
- **FR-009**: Restored evaluations MUST be saved immediately in the same way as evaluations made
  in the app, so they survive closing the app and are included in every later report.
- **FR-010**: After restoring, the viewer MUST move to the first not-yet-evaluated image that
  follows the last evaluated image of the report (by report order); if there is none, to the
  first pending image; if none is pending, it MUST say the review is complete.
- **FR-011**: When both the local evaluations and the report contain the same image, the
  evaluation with the most recent evaluation date MUST be kept; nothing else may be deleted.
- **FR-012**: The app MUST show an import summary: rows restored (added / updated / unchanged),
  rows not matched to the current export, and rows rejected as invalid, with the reason.
- **FR-013**: The app MUST warn when the report's form or data file differs from the loaded
  ones, and MUST reject files that are not reports produced by this app, leaving current
  evaluations unchanged.
- **FR-014**: All new texts and messages MUST be in English.

### Key Entities

- **Evaluation report**: the Excel file exported by the app; identifies its form file, data
  file and generation date, and holds one row per image with the image identifier, image link,
  question, evaluation status, reasons, comments, evaluator and evaluation date.
- **Report output folder**: the local folder where reports are written; default inside the
  project, editable by the evaluator.
- **Import summary**: the result of uploading a report — counts of added, updated, unchanged,
  not matched and rejected rows, plus the resume position.
- **Evaluation** (existing): verdict, reasons, comments, evaluator and date for one image.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of export attempts to a writable folder produce a file at the path shown to
  the evaluator, with no extra step outside the app.
- **SC-002**: After uploading a report, 100% of its evaluated rows that match images of the
  current export are restored, and a report exported right after contains all of them.
- **SC-003**: An evaluator resumes work from a report in under 1 minute (upload + continue on
  the right image), for reports of up to 10,000 rows.
- **SC-004**: Re-uploading the same report twice produces zero changes the second time.
- **SC-005**: No evaluation, local or imported, is lost in any of the merge scenarios of User
  Story 3.

## Assumptions

- The app runs on the evaluator's own computer, so "local path" means a folder on that
  computer. Running the app on a shared server where the browser user's computer differs from
  the app's computer is out of scope.
- Default output folder: `exports/` inside the project folder (already excluded from version
  control). The evaluator can type any other folder, including network or synced folders.
- The browser download button is removed; local saving fully replaces it.
- Reports generated by version 0.1.0 of the app (current format, including the "Image key"
  column) are importable; reports edited by hand are importable as long as the required
  columns remain.
- "Last evaluated image" means the evaluated row that appears last in the report's row order
  (which follows the export order), not the most recent evaluation date.
- Conflict rule between local and imported evaluations: most recent evaluation date wins; when
  dates are equal, the local evaluation is kept.
- Kobo sign-in (feature 001) is unchanged and not needed to import a report; it is only needed
  to view images.
