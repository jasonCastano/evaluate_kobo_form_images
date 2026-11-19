# Contract: Custom reasons file

**Path**: `$CUSTOM_REASONS_FILE`, default `<EVALUATIONS_DIR>/custom_reasons.json`
(`evaluations/custom_reasons.json`). Git-ignored with the rest of `evaluations/`; never in
the release allowlist.

```json
{
  "version": 1,
  "updated_at": "2026-11-19T15:04:05+00:00",
  "reasons": [
    {"name": "Finger over the lens", "hidden": false, "created_at": "2026-11-19T15:00:00+00:00"},
    {"name": "Wrong plant part", "hidden": true, "created_at": "2026-11-19T15:02:00+00:00"}
  ]
}
```

Rules:

- UTF-8, written atomically (`custom_reasons.json.tmp` → `os.replace`), `ensure_ascii=False`.
- `reasons` order is creation order and is the display order after the defaults.
- Default reasons are **never** written to the file.
- Reading: a missing file = no custom reasons (not an error). Invalid JSON, wrong `version`,
  or a non-list `reasons` = unreadable (`load_error`); individual entries with an invalid or
  duplicate name are skipped and reported in `load_error` without making the file unreadable.
- An unknown `version` greater than 1 is treated as unreadable and never overwritten without
  first being renamed (`.unreadable-<YYYYMMDD-HHMMSS>`).
- Autosave stores are `*__*.json` files; this file name has no `__`, so store scans
  (rename, R8) skip it.
