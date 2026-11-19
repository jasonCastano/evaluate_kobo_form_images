# Contract: Report format changes (delta)

Base contract: [`specs/002-report-export-resume/contracts/report-format.md`](../../002-report-export-resume/contracts/report-format.md).
Only the differences are listed.

## Export

- **Reason columns** (`Evaluations` sheet, between `Evaluation status` and `Invalid reasons`):
  one `Reason: <name>` column per name of `report_reasons(...)` (research R6): defaults,
  then visible custom reasons, then hidden or unknown reasons used by an exported evaluation.
  Cell = `Yes` when the evaluation has the reason, else blank.
- **`Invalid reasons`**: unchanged format, `"; "`-joined names in the evaluation's order;
  custom names included.
- **`Summary by question`**: reason columns use the same `report_reasons(...)` list;
  verdict and reason counts are kept separately (a reason named like a verdict does not mix).
- With no custom reasons the workbook is identical to the previous version (FR-009).

## Import

- A reason name (from `Invalid reasons` or from a `Reason: <name>` header marked `Yes`) is:
  1. canonicalized to a known reason when its key matches (case/spacing-insensitive);
  2. otherwise accepted if it passes the name rules, and added to the catalogue when the row
     matches an image of the current export;
  3. otherwise the row is rejected with `Invalid reason name '<name>'`.
- `Unknown reason '<name>'` is no longer produced.
- The import summary lists `new_reasons` ("Added invalid reasons: …").
