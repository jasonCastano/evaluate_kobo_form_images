# Contract: Evaluation report file (export ⇄ import)

The Excel report written by `report.build_report` (format of app v0.1.0) is also the input of
the resume feature. Changing these columns is a breaking change for import.

## Sheet `Evaluations` (required)

Row 1 = headers (exact text, trimmed). Columns used by import:

| Header | Required for import | Content |
|--------|---------------------|---------|
| `Image key` | ✅ | Stable record key |
| `Image URL` | ✅ | Kobo attachment URL |
| `Question name` | ✅ | XLSForm question name |
| `Evaluation status` | ✅ | `Valid`, `Invalid` or `Pending` |
| `Invalid reasons` | one of the two | `"; "`-separated reason texts |
| `Reason: Low lighting`, `Reason: Too bright / overexposed`, `Reason: Out of focus / blurry`, `Reason: Invalid image content` | one of the two | `Yes` or empty |
| `Comments` | ✅ | Free text |
| `Evaluator` | ✅ | Name |
| `Evaluated at (UTC)` | ✅ | ISO-8601 (e.g. `2026-11-12T14:00:01+00:00`) |
| `Form file`, `Data file` | — | Provenance (warning only) |

All other columns (sheet, row, submission, label, group…) are ignored on import and
regenerated on export.

## Sheet `Metadata` (optional)

| Field | Value |
|-------|-------|
| `Form file` | Form file name |
| `Data file` | Data export file name |

## Row handling

| Row | Result |
|-----|--------|
| Status `Pending` or empty | ignored |
| Status not in {Valid, Invalid, Pending} | rejected: "Unknown status '<x>'" |
| `Invalid` with no reasons | rejected: "Invalid without reasons" |
| Reason text not in the closed list | rejected: "Unknown reason '<x>'" |
| Unparsable date | rejected: "Invalid evaluation date '<x>'" |
| Valid row, key or URL+question matches a current image | imported (merged) |
| Valid row, no match | counted as not matched |

## File rejection (nothing imported)

- Not an `.xlsx` workbook, or no `Evaluations` sheet → "This file is not an evaluation report
  exported by this app."
- Missing required columns → "The report is missing required columns: <list>."
