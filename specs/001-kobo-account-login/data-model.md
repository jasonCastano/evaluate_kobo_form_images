# Phase 1 Data Model: Kobo Account Login

**Feature**: [spec.md](./spec.md) · **Research**: [research.md](./research.md)

All entities are **in-memory only**; nothing in this feature is persisted to disk.

## KoboServer

The Kobo instance that hosts forms and attachments.

| Field | Type | Rules |
|-------|------|-------|
| `base_url` | str | Normalized `scheme://host[:port]`, lower-case host, no trailing slash, no path. `https` required except `http://localhost*` (testing). |
| `label` | str | Display name: "Global (kf.kobotoolbox.org)", "EU (eu.kobotoolbox.org)" or the custom host. |

- **Known servers**: `https://kf.kobotoolbox.org`, `https://eu.kobotoolbox.org`.
- **Detection**: most frequent `scheme://host` among `ImageRecord.image_url` of the loaded
  export (ties → first seen). No records → Global.
- **Validation**: an invalid custom URL (no host, unsupported scheme) is rejected with
  "Enter a valid Kobo server address, e.g. https://kf.kobotoolbox.org".

## KoboSession

Proof of identity for one server and one Kobo user, valid for the current browser session.

| Field | Type | Rules |
|-------|------|-------|
| `server` | KoboServer | Server the token was issued by. |
| `username` | str | Canonical username returned by `/me/`. |
| `token` | str | Kobo API key. **Never** printed, logged, persisted; masked in `repr` (`token=****abcd`). |
| `method` | enum `password` \| `api_key` \| `environment` | How the session was obtained (shown as a caption). |
| `signed_in_at` | str (ISO-8601 UTC) | For display only. |

- **Identity**: immutable value object (frozen).
- **Relationship**: one `KoboSession` → one `KoboImageClient` (per browser session).
- **Authorization rule**: the token is attached only to URLs whose `scheme://host` equals
  `server.base_url` (research R4).

## AuthState (UI state machine, per browser session)

```text
             ┌────────────── sign_out ───────────────┐
             ▼                                       │
  SIGNED_OUT ──submit credentials──► VERIFYING ──ok──► SIGNED_IN
      ▲   ▲                               │                │
      │   └──── error (message shown) ────┘                │
      └──────── access expired (401 on download) ──────────┘
```

| State | Stored in session | UI |
|-------|-------------------|----|
| `SIGNED_OUT` | no `KoboSession` | Login panel (password tab / API-key tab), last error message if any |
| `VERIFYING` | transient (inside one rerun, spinner) | "Signing in…" |
| `SIGNED_IN` | `KoboSession` + client | "Signed in as **user** on *server*" + **Sign out** |

- **Startup**: if `KOBO_API_TOKEN` is set and no session exists, attempt one `environment`
  sign-in for the detected server; on failure stay `SIGNED_OUT` and show the R5 message.
- **Expiry**: a `401` on an authenticated download clears the session (→ `SIGNED_OUT`) and
  shows "Your Kobo access expired or was revoked. Please sign in again." Evaluations are
  untouched (FR-011).

## AuthError

| Field | Type | Values |
|-------|------|--------|
| `kind` | enum | `INVALID_CREDENTIALS`, `INVALID_TOKEN`, `UNREACHABLE`, `INVALID_SERVER`, `UNEXPECTED` |
| `message` | str | Plain-language English text from research R5 |

## ImageFetchError (extended)

Existing exception gains a `reason` so the UI can react (FR-010):

| `reason` | Trigger | UI reaction |
|----------|---------|-------------|
| `NOT_SIGNED_IN` | 401/403/404 and no credentials sent | Show sign-in invitation |
| `ACCESS_EXPIRED` | 401 with credentials | Sign out + message |
| `NO_ACCESS` | 403/404 with credentials | Message, keep session |
| `UNREACHABLE` | network error, timeout, 5xx | Message + retry |
| `NOT_AN_IMAGE` | decode failure | Message |

## Unchanged entities

`ImageRecord`, `Evaluation`, `EvaluationStore` and the Excel report are not modified. The
evaluator name field may be pre-filled from `KoboSession.username` (still user-editable).
