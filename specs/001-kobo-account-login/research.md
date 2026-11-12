# Phase 0 Research: Kobo Account Login

**Feature**: [spec.md](./spec.md) · **Date**: 2026-11-12

All unknowns from the Technical Context are resolved below. Endpoint behavior was verified
against the live public servers with unauthenticated / deliberately invalid requests only
(no real credentials used).

## R1. How to turn a username + password into access to private attachments

- **Decision**: Call `GET {server}/token/?format=json` with HTTP Basic authentication
  (username, password). A `200` response returns `{"token": "<40-hex API key>"}`. That API key
  is then used as `Authorization: Token <key>` for attachment downloads, exactly like today.
- **Rationale**: This is Kobo's documented way to obtain the API key programmatically. Verified
  on 2026-11-12: `https://kf.kobotoolbox.org/token/` and `https://eu.kobotoolbox.org/token/`
  answer `401 {"detail":"Authentication credentials were not provided."}` without credentials
  and `401 {"detail":"Invalid username/password."}` for a wrong pair, proving Basic auth is
  accepted there. The password is used for one request and then discarded (FR-008).
- **Alternatives considered**:
  - *Browser redirect / OAuth2 "Sign in with Kobo"*: public Kobo servers do not offer OAuth
    client registration for third-party apps → not possible.
  - *Session-cookie login by posting the Kobo login form*: brittle (CSRF, HTML changes, MFA
    pages), and would keep a full web session → rejected.
  - *Sending username/password (Basic) on every attachment request*: keeps the password in
    memory for the whole session, contradicting FR-008 → rejected.

## R2. How to verify an API key and learn the username

- **Decision**: Call `GET {server}/me/?format=json` with `Authorization: Token <key>`. `200`
  returns the current user JSON including `username`; `401 {"detail":"Invalid token."}` means
  the key is invalid or was regenerated.
- **Rationale**: Verified on 2026-11-12 (`401 Invalid token.` for a dummy key). Used for the
  API-key path (User Story 3), the `.env` auto sign-in, and as a post-login sanity check that
  yields the canonical username shown in the UI (FR-004).
- **Alternatives considered**: `/api/v2/assets/?limit=1` (works but does not return the
  username); trusting the typed username (not verified) → rejected.

## R3. Which server to sign in to (global vs EU vs private)

- **Decision**: Detect the server as the most common `scheme://host` among the loaded image
  URLs (e.g. `https://kf.kobotoolbox.org`). Offer: *Global (kf.kobotoolbox.org)*,
  *EU (eu.kobotoolbox.org)*, *Custom URL*. Pre-select the detected server; warn when the
  signed-in server differs from the image host (edge case "wrong server").
- **Rationale**: All current exports point to `kf.kobotoolbox.org`; Kobo attachments are served
  from the same host as the KPI API, so the image host is the right login target.
- **Alternatives considered**: asking the user every time (error-prone); hard-coding the global
  server (breaks EU/private instances).

## R4. Never leak the API key to another host

- **Decision**: The image client sends the `Authorization` header only when the attachment
  URL's `scheme://host` equals the signed-in server. Other hosts are fetched without
  credentials and, if they fail with 401/403/404, report "sign in to <host>".
- **Rationale**: Prevents token leakage if an export contains links to another server
  (edge case "several servers") and enforces Principle VI (data protection).
- **Alternatives considered**: global `requests.Session` header (current behavior) → leaks the
  key to any host → replaced.

## R5. Mapping HTTP outcomes to the plain-language messages of FR-005

| Situation | Kobo response | Message |
|-----------|---------------|---------|
| Wrong username/password (or SSO / MFA account) | `401` on `/token/` | "Invalid Kobo username or password. If you sign in to Kobo with your organization (SSO) or use two-factor authentication, use an API key instead." |
| Invalid / regenerated API key | `401` on `/me/` or attachment | "This API key is not valid for <server>." / "Your Kobo access expired or was revoked. Please sign in again." (also signs the user out) |
| Not signed in | `401/403/404` on attachment without credentials | "Sign in to your Kobo account to see this image." |
| Signed in, no permission | `403` or `404` on attachment with valid key | "Your account does not have access to this image (or it no longer exists in Kobo)." |
| Network failure / timeout / 5xx | exception or `5xx` | "Kobo (<server>) cannot be reached. Check your connection and retry." |
| Response is not an image | decode failure | "The downloaded file is not a readable image." |

- **Note**: Kobo returns `404` (not `403`) for attachments the caller cannot see, as observed
  in the first session; therefore signed-in `404` is reported as "no access or deleted".

## R6. Keeping secrets in memory only (FR-008, FR-009, SC-005)

- **Decision**:
  - Password typed in a Streamlit `st.form` with `clear_on_submit=True`; the value is passed
    once to `login_with_password` and never assigned to session state or logs.
  - The resulting `KoboSession` (server, username, token) lives in `st.session_state`, which
    is per browser tab and in memory only. `KoboSession.__repr__` masks the token.
  - The image client is created per session (stored next to the `KoboSession`), replacing the
    process-wide `st.cache_resource` client keyed by token, so sign-out really drops the key.
  - The on-disk image cache stores only image bytes keyed by URL hash — no credentials.
- **Rationale**: Satisfies "no password or session access persisted" with no new dependency.
- **Alternatives considered**: OS keyring "remember me" — out of scope per spec assumptions.

## R7. Testing without real credentials

- **Decision**: Unit tests stub HTTP by monkeypatching `requests.Session.get` (or injecting a
  fake session) to return canned `401/200/403/404/5xx` responses; no new test dependency.
  End-to-end validation with real credentials is a manual quickstart step.
- **Alternatives considered**: `responses` / `requests-mock` libraries — unnecessary for ~10
  canned cases.

## R8. Evaluator name pre-fill

- **Decision**: After sign-in, if the evaluator name field is empty, pre-fill it with the Kobo
  username; it stays editable.
- **Rationale**: Matches spec assumption; improves report traceability at no cost.
