# Contract: sidebar "4. Report" section (UI)

Replaces the current "4. Export" section (browser download removed). English strings are
normative.

```text
4. Report
  Save to folder  [ D:\croppix\evaluate_form_images\exports ]   ← default REPORTS_DIR / exports
  ☑ Include images not evaluated yet
  [ 💾 Export report ]
  ✅ Report saved to D:\…\exports\image_evaluation__CIAT_CIV_2_Yield_FORM__20261112-163000.xlsx
     (or ❌ Could not save the report to <path>: <reason>)

  Resume from a previous report
  [ Browse… report.xlsx ]
  [ ⤴ Import report ]
  ✅ Restored 120 evaluations from report.xlsx (115 added, 5 updated, 0 unchanged).
  ⚠ This report was created for form 'X.xlsx' and data 'Y.xlsx'. Only matching images were restored.
  ⚠ 3 evaluated rows did not match any image in this export.
  ⚠ 2 rows were rejected:            ← expander with "Row 14: Invalid without reasons", …
  ℹ Continuing from image #121.      (or ✅ "All images in this export are evaluated.")

  Evaluations autosave to `evaluations\<form>__<data>.json`.
```

Behavior:

- The folder field accepts absolute or relative paths (relative to the project folder) and `~`.
- "Export report" shows a spinner "Saving the report…"; the result message persists until the
  next export.
- "Import report" is enabled only when a file is selected; the same file content is imported
  only once per session (re-pressing shows "This report was already imported.").
- After an import, filters reset to all questions / status All / everyone, and the viewer jumps
  to the resume image.
- Errors never clear existing evaluations.
