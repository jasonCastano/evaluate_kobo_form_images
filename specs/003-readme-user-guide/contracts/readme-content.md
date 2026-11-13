# Contract: README content that must be present and accurate

Strings in `code` are verbatim UI texts and must exist in `src/` (grep check).

## Invalid reasons (FR-003)

`Low lighting` · `Too bright / overexposed` · `Out of focus / blurry` · `Invalid image content`
— an *Invalid* image needs at least one; *Valid* stores none.

## Sidebar sections (FR-002)

`1. Kobo form` · `2. Collected data` · `3. Kobo account` · `4. Report`, plus `Evaluator name`.

## Troubleshooting table (FR-007) — minimum rows

| Message (as shown) | Cause | What to do |
|--------------------|-------|------------|
| `Sign in to your Kobo account in the sidebar to see this image.` | Not signed in; Kobo attachments are private | Sign in under 3. Kobo account |
| `Invalid Kobo username or password. …` | Wrong credentials, SSO-only or two-factor account | Retry, or use the API key tab |
| `This API key is not valid for <server>.` | Wrong / regenerated key, wrong server | Copy the key again from Kobo, check the server |
| `Your Kobo access expired or was revoked. Please sign in again.` | Key regenerated or account changed | Sign in again |
| `Your account does not have access to this image (or it no longer exists in Kobo).` | Account lacks project permission, or submission deleted | Ask the project owner for access; mark the image if appropriate |
| `Kobo (<server>) cannot be reached. Check your connection and retry.` | No internet / Kobo down | Check connection, press Retry |
| `The images in this export are hosted on <host>.` | Signed in to a different server | Sign out and choose the server of the images |
| `Some image columns of the export did not match any image question of the form …` | Wrong form for this export, or form changed | Load the matching form version |
| `Could not save the report to <path>: <reason>` | Invalid folder, permission, file open, slow drive | Choose another folder / close the file |
| `The report is missing required columns: …` / `This file is not an evaluation report exported by this app.` | Edited or wrong file | Use an unmodified report exported by the app |
| `<n> rows were rejected` (Row N: reason) | Invalid rows in an edited report | Fix the rows or ignore them |
| `<n> evaluated rows did not match any image in this export.` | Report from another export / deleted submissions | Load the matching data export |

## Configuration (FR-008)

| Variable | Default |
|----------|---------|
| `KOBO_API_TOKEN` | empty (sign in from the sidebar) |
| `KOBO_FORMS_DIR` | `forms` |
| `KOBO_DATA_DIR` | `data` |
| `EVALUATIONS_DIR` | `evaluations` |
| `IMAGE_CACHE_DIR` | `.cache/images` |
| `REPORTS_DIR` | `exports` |

## Six-question test (SC-002)

1. Which files do I need? → XLSForm `.xlsx` + Kobo data export `.xlsx` of the same form.
2. Why are images not shown before signing in? → Kobo attachments are private.
3. Where are evaluations saved? → `evaluations/<form>__<export>.json`, after every save.
4. What happens if I import a report twice? → Nothing changes; "This report was already imported."
5. What does "not matched" mean? → Report rows with no image in the loaded export.
6. Which reasons can mark an image invalid? → The four reasons above.
