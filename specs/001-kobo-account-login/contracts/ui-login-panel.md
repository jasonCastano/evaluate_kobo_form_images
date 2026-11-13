# Contract: "Kobo account" sidebar panel (UI)

Replaces the current "Kobo API token" text input in sidebar section **3. Session**.
All texts are normative English strings (FR-012).

## Signed out

```text
3. Kobo account
  Server: [ Global (kf.kobotoolbox.org) ▾ ]        ← pre-selected from image links
          (Custom URL field appears when "Custom…" is chosen)
  ┌ Username & password ┬ API key ┐
  │ Username  [________]          │
  │ Password  [••••••••]          │
  │ [ Sign in ]                   │
  └───────────────────────────────┘
  ⓘ Use an API key if you sign in to Kobo with your organization (SSO) or with
    two-factor authentication. Find it in Kobo > Account settings > Security.
  Evaluator name [________]
```

- API key tab: `API key [••••]` (password-masked) + **Sign in**.
- Both forms clear their inputs on submit.
- Error messages (research R5) render as `st.error` under the form and persist until the next
  attempt.

## Signed in

```text
3. Kobo account
  ✅ Signed in as **jdoe** on Global (kf.kobotoolbox.org)
     via username & password · 14:02 UTC
  [ Sign out ]
  ⚠ The images in this export are hosted on eu.kobotoolbox.org.   ← only on mismatch
  Evaluator name [jdoe____]                                        ← pre-filled if empty
```

## Image area (main view)

| Fetch result | Display |
|--------------|---------|
| Image | image + "Open original attachment in Kobo" link |
| `NOT_SIGNED_IN` | `st.info("Sign in to your Kobo account in the sidebar to see this image.")` |
| `ACCESS_EXPIRED` | session cleared, `st.warning("Your Kobo access expired or was revoked. Please sign in again.")` |
| `NO_ACCESS` | `st.error("Your account does not have access to this image (or it no longer exists in Kobo).")` |
| `UNREACHABLE` | `st.error(...)` + **Retry** button |
| `NOT_AN_IMAGE` | `st.error("The downloaded file is not a readable image.")` |

The evaluation form stays usable in every case (evaluators may mark an unreachable image).
