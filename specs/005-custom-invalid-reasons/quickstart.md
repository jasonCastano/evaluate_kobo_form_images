# Quickstart: validate custom invalid reasons

Prerequisites: project set up (`make dev`), a Kobo form and export in `forms/` and `data/`
(or the synthetic fixtures used by the tests).

## Automated

```bash
make check     # lint + format + types + all tests
```

Key test files: `tests/test_reasons.py` (catalogue, rules, persistence, rename across stores),
`tests/test_evaluation.py`, `tests/test_report.py`, `tests/test_report_import.py`,
`tests/test_app_reasons.py` (AppTest: add reason inside the form, restart persistence).

## Manual

1. `make run`, load a form + export, open an image.
2. **Add (US1)**: mark Invalid, type a comment, enter `Finger over the lens`, click
   **➕ Add reason** → it appears ticked, the comment is still there; click **💾 Save**.
   Try ` low LIGHTING ` → "already exists"; try an empty name and a name with `;` → errors.
3. **Persistence (US2)**: stop the app (Ctrl+C), `make run` again, open any image (also with
   another form) → the reason is listed after the defaults; the saved image shows it ticked.
   Check `evaluations/custom_reasons.json` exists and `git status` does not list it.
4. **Report (US3)**: export the report → `Reason: Finger over the lens` column has `Yes` on that
   row; `Invalid reasons` contains it; `Summary by question` counts it. Rename
   `evaluations/custom_reasons.json` away, restart, import the report → evaluation restored,
   summary says "Added invalid reasons: Finger over the lens".
5. **Old report**: import a report exported before this feature → same restored/rejected counts
   as before.
6. **Manage (US4)**: sidebar → Manage invalid reasons → rename to `Finger on lens`; the saved
   image shows the new name; hide it → not offered on a new image, still ticked on the saved
   one and still in the exported report; restore it.
