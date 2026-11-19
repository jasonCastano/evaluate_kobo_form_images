# Feature Specification: Custom Invalid Reasons

**Feature Branch**: `005-custom-invalid-reasons`

**Created**: 2026-11-19

**Status**: Draft

**Input**: User description: "junto a las categorías de evaluación de las imágenes que existen por defecto, necesito añadir una opción de añadir nueva categoría para las evaluaciones de las imágenes. Si el usuario nota que existe una categoría que debe añadir para la evaluación de la imagen, debe tener esta opción y su opción registrada debe quedar permanente en su uso, el usuario debe poder visualizar esta opción cuando despliegue la herramienta después de cerrarla"

(English summary: next to the default image evaluation categories, add an option to create a
new category. When evaluators notice a problem not covered by the defaults, they can add it,
and the new category stays permanently available, including after the tool is closed and
started again.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add a new invalid reason while evaluating (Priority: P1)

While reviewing an image, the evaluator finds a problem that none of the default reasons
(Low lighting, Too bright / overexposed, Out of focus / blurry, Invalid image content)
describes, for example "Wrong plant part" or "Finger over the lens". Next to the list of
reasons, they type the name of a new reason and add it. The new reason appears immediately
in the list, below the defaults, and they can tick it for the current image and save.

**Why this priority**: This is the core of the request. Without it, evaluators have to hide
specific problems inside "Invalid image content" plus a free-text comment, which makes the
report hard to filter and count.

**Independent Test**: Start the app with a form loaded, add a reason "Finger over the lens"
from the evaluation panel, tick it on an image marked Invalid, save, and confirm the saved
evaluation and the exported report show that reason.

**Acceptance Scenarios**:

1. **Given** an image is open for evaluation, **When** the evaluator enters "Finger over the
   lens" and confirms, **Then** the reason appears in the list of selectable reasons without
   losing anything already entered for the current image (verdict, ticked reasons, comments).
2. **Given** the new reason is in the list, **When** the evaluator marks the image Invalid,
   ticks only the new reason and saves, **Then** the evaluation is accepted and stored with
   that reason.
3. **Given** the evaluator enters a name that matches an existing reason ignoring case and
   extra spaces (e.g. " low LIGHTING "), **When** they confirm, **Then** no duplicate is
   created and they are told the reason already exists.
4. **Given** the evaluator enters an empty or whitespace-only name, **When** they confirm,
   **Then** nothing is added and they see a clear message.

---

### User Story 2 - Custom reasons survive closing and reopening the tool (Priority: P1)

The evaluator added one or more reasons in a previous session. They close the tool (or the
computer restarts), start it again and load any form. The reasons they added are still in
the list, in the order they were added, after the defaults.

**Why this priority**: The user explicitly requires the new category to be permanent and
visible after redeploying the tool. A reason that disappears on restart would make earlier
evaluations inconsistent with new ones.

**Independent Test**: Add a reason, stop the app completely, start it again, load a form and
confirm the reason is listed and selectable.

**Acceptance Scenarios**:

1. **Given** the evaluator added "Finger over the lens" and closed the tool, **When** they
   start the tool again and open any image, **Then** "Finger over the lens" is listed after
   the default reasons.
2. **Given** custom reasons exist, **When** the evaluator loads a different form and data
   export on the same installation, **Then** the same custom reasons are available there too.
3. **Given** previously saved evaluations use a custom reason, **When** the tool is
   restarted and those images are reopened, **Then** the reason is shown as ticked.

---

### User Story 3 - Custom reasons in the Excel report and when resuming from it (Priority: P2)

Custom reasons are first-class in the exported Excel report: they appear in the
"Invalid reasons" text column and each one gets its own Yes/blank column, like the defaults,
and they are listed in the report's reference of reasons. When a report that contains custom
reasons is uploaded to resume work (on this or another installation), the evaluations are
restored with their custom reasons, and any reason not yet known on that installation is
added to the list so the evaluator can keep using it.

**Why this priority**: The report is the deliverable of the tool. Custom reasons that are
not countable in the report, or that break resuming from a report, would undo the value of
Story 1. It is P2 because Stories 1–2 already deliver value in the interface and the saved
evaluations.

**Independent Test**: Evaluate an image with a custom reason, export the report, open it and
check the columns; then on a clean installation (no custom reasons) upload the report and
confirm the evaluation is restored and the reason now appears in the list.

**Acceptance Scenarios**:

1. **Given** an evaluation uses the custom reason "Finger over the lens", **When** the report
   is exported, **Then** the "Invalid reasons" column contains it and a dedicated column for
   that reason shows "Yes" on that row and is blank on the others.
2. **Given** a report containing a reason unknown to the installation, **When** it is
   uploaded to resume, **Then** the rows are restored (not rejected as "Unknown reason"), the
   reason is added permanently to the list, and the import summary says which reasons were
   added.
3. **Given** a report made before this feature (default reasons only), **When** it is
   uploaded, **Then** it is imported exactly as before.

---

### User Story 4 - Rename or retire a custom reason (Priority: P3)

The evaluator made a typo or no longer needs a reason. They can rename a custom reason or
hide it from the list of selectable reasons. Default reasons cannot be renamed or hidden.

**Why this priority**: Useful housekeeping but not required for the core request; typos can
be worked around until this exists.

**Independent Test**: Add "Fingr over lens", rename it to "Finger over the lens", hide another
custom reason, restart the tool and confirm both changes persisted.

**Acceptance Scenarios**:

1. **Given** a custom reason "Fingr over lens" is used by saved evaluations, **When** the
   evaluator renames it to "Finger over the lens", **Then** the list and every saved
   evaluation that used it show the new name, and the next exported report uses it.
2. **Given** a custom reason is hidden, **When** the evaluator opens a new image, **Then**
   the reason is not offered; **and** images already evaluated with it still show it ticked
   and it still appears in exported reports.
3. **Given** a hidden custom reason, **When** the evaluator restores it, **Then** it is
   offered again.
4. **Given** a default reason, **Then** no rename or hide option is offered for it.

---

### Edge Cases

- The name of a new reason is very long → names are limited to 60 characters; longer input
  is refused with a message.
- The name contains the separator used in the report's "Invalid reasons" text column (";")
  → refused with a message, because it would split into two reasons on re-import.
- The name matches a report column that already exists (e.g. "Comments") → still allowed;
  reason columns carry a fixed prefix so they cannot collide with other columns.
- The stored list of custom reasons is missing, empty or unreadable at start-up → the tool
  starts with the default reasons only, warns the evaluator once if the file was unreadable,
  and does not overwrite the unreadable file until a reason is added.
- Two browser tabs of the same tool add reasons at the same time → both additions are kept
  (the list is re-read before saving a new reason).
- Renaming a custom reason to the name of another existing reason → refused, same as a
  duplicate.
- A report uploaded for resuming contains a reason name that is invalid under the rules
  above (too long, contains ";") → those rows are rejected with a clear reason, as today.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The evaluation panel MUST offer, next to the list of invalid reasons, a way to
  add a new reason by typing its name and confirming.
- **FR-002**: The system MUST validate a new reason name: trimmed of surrounding spaces,
  not empty, at most 60 characters, no ";" character, and not equal (ignoring case and
  repeated spaces) to any existing default or custom reason, hidden ones included.
- **FR-003**: A newly added reason MUST become selectable immediately for the current image,
  without losing the verdict, reasons or comments already entered for that image.
- **FR-004**: Custom reasons MUST behave exactly like default reasons when evaluating: they
  count toward the "at least one reason for Invalid" rule and are stored with the evaluation.
- **FR-005**: Custom reasons MUST be stored permanently on the installation and MUST be
  available in every later session and for every form, until the evaluator hides them.
- **FR-006**: The list MUST show default reasons first, in their current order, followed by
  custom reasons in the order they were added.
- **FR-007**: The exported Excel report MUST include custom reasons in the "Invalid reasons"
  text column, one Yes/blank column per reason (defaults first, then custom), and in the
  report's list of reasons.
- **FR-008**: Uploading a report to resume MUST accept reasons that are not yet known on the
  installation if their names satisfy FR-002's format rules, MUST add them permanently to the
  custom reasons, and MUST report which reasons were added.
- **FR-009**: Reports created before this feature MUST continue to export and import
  unchanged.
- **FR-010**: Evaluators MUST be able to rename a custom reason; the new name follows FR-002,
  and every saved evaluation using the old name MUST be updated.
- **FR-011**: Evaluators MUST be able to hide and restore a custom reason. Hidden reasons are
  not offered for new selections but remain on evaluations that already use them, in the
  interface and in exported reports.
- **FR-012**: Default reasons MUST NOT be renamable, hideable or removable.
- **FR-013**: If the stored custom reasons cannot be read, the tool MUST still start with the
  default reasons, show a warning, and MUST NOT discard the unreadable stored data silently.
- **FR-014**: Custom reasons MUST NOT be stored in any tracked project file; they are local
  data like evaluations and reports.

### Key Entities

- **Invalid reason**: A named cause for rejecting an image. Attributes: display name
  (unique ignoring case and spacing), origin (default or custom), visibility (offered or
  hidden; defaults are always offered), order of creation.
- **Custom reason catalogue**: The installation's permanent list of custom invalid reasons,
  shared by all forms and sessions on that installation.
- **Evaluation** (existing): now references any invalid reason, default or custom, by name.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An evaluator can add a new reason and apply it to the current image in under
  30 seconds, without re-entering anything already entered for that image.
- **SC-002**: 100% of custom reasons added in a session are present after the tool is
  stopped and started again (verified across at least 3 restarts).
- **SC-003**: Every custom reason used in at least one evaluation can be counted in the
  exported report by filtering a single column.
- **SC-004**: A report containing custom reasons, uploaded on an installation that does not
  know them, restores 100% of its valid rows with no "Unknown reason" rejections.
- **SC-005**: Reports created before this feature import with the same results as before
  (same restored and rejected row counts).

## Assumptions

- "Evaluation categories" means the **invalid reasons** ticked when an image is marked
  Invalid; the Valid / Invalid verdict itself stays fixed.
- Custom reasons are kept per installation (the folder where the tool runs, alongside the
  local evaluations) and shared by all forms and evaluators using that installation; there
  is no central server, so other installations learn custom reasons through report uploads
  (FR-008).
- The tool is used by one evaluator at a time per installation; no permissions model is
  needed to add, rename or hide reasons.
- Reasons are never fully deleted, only hidden, so saved evaluations and reports never point
  to a reason that no longer exists.
- Reason names are free text in whatever language the evaluator types; the interface text
  around them stays in English.
