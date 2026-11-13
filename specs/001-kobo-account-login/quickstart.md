# Quickstart: validate Kobo Account Login

**Feature**: [spec.md](./spec.md) · Contracts: [kobo-http](./contracts/kobo-http.md),
[python-api](./contracts/python-api.md), [ui-login-panel](./contracts/ui-login-panel.md)

## Prerequisites

- Project set up (`make dev`), a Kobo form in `forms/` and its export in `data/`.
- A Kobo account **with access to that project** (username + password), and its API key
  (Kobo > Account settings > Security).
- Remove `KOBO_API_TOKEN` from `.env` (or comment it out) for scenarios 1–4.

## Automated checks

```bash
make check     # lint + format + ty + pytest (auth and fetch paths use stubbed HTTP)
```

Expected: all tests pass, including the new `tests/test_kobo_auth.py` cases for each row of
the contract tables.

## Manual scenarios

Run `make run`, select the form and its export.

| # | Steps | Expected |
|---|-------|----------|
| 1 | Do not sign in | Image area: "Sign in to your Kobo account in the sidebar to see this image." Server pre-selected = image host. |
| 2 | Sign in with a wrong password | "Invalid Kobo username or password…"; password field empty; still signed out. |
| 3 | Sign in with valid username + password | "Signed in as <user> on <server>"; image shown within seconds; evaluator name pre-filled if it was empty. |
| 4 | Press **Next** 20 times | All images show; no credential prompt (SC-003). |
| 5 | **Sign out**, open an image not seen before | Sign-in invitation; previously seen images still show (cache). |
| 6 | API key tab: paste an invalid key | "This API key is not valid for <server>." |
| 7 | API key tab: paste the valid key | Signed in as the key owner; images show. |
| 8 | Put the key in `.env` as `KOBO_API_TOKEN`, restart | Signed in automatically ("via environment"). |
| 9 | Choose EU server, sign in with a global-server account | "Invalid Kobo username or password…" (or mismatch warning if the account also exists there). |
| 10 | Disconnect network, open an uncached image | "Kobo (<server>) cannot be reached…" + Retry; evaluations still save. |

## Secret-leak check (SC-005)

After the session:

```bash
git status --short                                   # no new tracked files with secrets
grep -rIl "<your API key>" evaluations/ .cache/ . 2>/dev/null | grep -v "^./.env$"   # expect no output
grep -rIl "<your password>" evaluations/ .cache/ . 2>/dev/null                      # expect no output
```

Also open the exported Excel: no token or password in any sheet.
