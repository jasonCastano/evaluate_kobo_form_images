# Quickstart: validate local report export and resume

**Feature**: [spec.md](./spec.md) · Contracts: [report-format](./contracts/report-format.md),
[python-api](./contracts/python-api.md), [ui-export-import](./contracts/ui-export-import.md)

## Prerequisites

- `make dev`; a form in `forms/` and its export in `data/`; Kobo sign-in working (feature 001).
- Start the app: `.\.venv\Scripts\evaluate-kobo-images.exe` (or `make run`).

## Automated checks

```bash
make check   # includes export round-trip, merge, rejection and resume tests
```

## Manual scenarios

| # | Steps | Expected |
|---|-------|----------|
| 1 | Evaluate 3 images, keep default folder, **Export report** | "Report saved to …\exports\image_evaluation__<form>__<timestamp>.xlsx"; file opens in Excel with the 3 evaluations |
| 2 | Type a new folder (e.g. `D:\temp\reports_test`) and export | Folder created, file saved there |
| 3 | Export twice quickly | Two different files; first not overwritten |
| 4 | Open the last report in Excel (keep it open) and export to the same folder | New file still saved (different name); if you force an invalid path like `Z:\nope`, a clear error appears |
| 5 | Close the app, rename `evaluations\<form>__<data>.json` to back it up, restart, load the same form/data | Counters at 0 evaluated |
| 6 | Upload the report from scenario 1 → **Import report** | "Restored 3 evaluations…"; viewer opens on the first pending image after the 3rd evaluated one |
| 7 | Evaluate 2 more images and export | New report has 5 evaluations |
| 8 | Import the same report again | "This report was already imported." / no changes |
| 9 | Load a different form/data and import the scenario-1 report | Mismatch warning; "3 evaluated rows did not match…" |
| 10 | Edit a copy of the report: set one row to `Invalid` with empty reasons, delete column `Comments` in another copy; import each | Row rejected with "Invalid without reasons"; file rejected with "missing required columns: Comments" |
| 11 | Restore the backed-up JSON from scenario 5 and re-check counters | Your original evaluations are intact |

> ⚠️ Scenario 5 touches your autosave file: **back it up** (rename/copy) — do not delete it.
