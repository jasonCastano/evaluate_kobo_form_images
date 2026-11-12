# Implementation Plan: Kobo Account Login

**Branch**: `001-kobo-account-login` | **Date**: 2026-11-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-kobo-account-login/spec.md`

## Summary

Let evaluators sign in to their Kobo account from the app sidebar so private image
attachments display without manually copying an API key. The username and password are
exchanged once for the account's API key through Kobo's `/token/` endpoint (verified on the
live servers), the key is verified with `/me/` to obtain the canonical username, and the
resulting in-memory `KoboSession` authorizes image downloads for the rest of the browser
session. The API-key path (pasted or from `.env`) is kept for SSO/MFA accounts. The image
client is reworked to attach the key only to the signed-in server's host and to report typed
failure reasons, so the UI can show plain-language messages and invite sign-in.

## Technical Context

**Language/Version**: Python 3.13

**Primary Dependencies**: Streamlit 1.67 (UI), requests (HTTP), Pillow (images) — no new
dependencies

**Storage**: None for this feature (session state in memory only); existing JSON autosave and
image cache unchanged and credential-free

**Testing**: pytest with stubbed HTTP (`requests.Session` fakes), synthetic data only

**Target Platform**: Local Streamlit app (Windows/macOS/Linux) reaching public or private Kobo
servers over HTTPS

**Project Type**: Single Python package (src-layout) with a Streamlit UI

**Performance Goals**: Sign-in completes in < 5 s on a normal connection; first image visible
< 1 min after opening the app (SC-001); no extra requests per image beyond today's single GET

**Constraints**: Password never retained after the sign-in call; token never logged, persisted
or sent to another host; English-only UI; must keep working with `KOBO_API_TOKEN` in `.env`

**Scale/Scope**: One evaluator per browser session; exports up to ~10k images; 2 public
servers + custom

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| I. Human judgment, traceability | Evaluation model, record keys and report untouched; evaluator name only pre-filled | ✅ |
| II. No image silently dropped | Export scanning untouched; fetch failures are shown, never hide records | ✅ |
| III. Closed evaluation vocabulary | Unchanged | ✅ |
| IV. Logic outside the UI | Auth flow in new `kobo_auth.py`; failure typing in `kobo_client.py`; `app.py` only renders | ✅ |
| V. Test-backed quality gates | Unit tests for every contract row with stubbed HTTP; `make check` gate | ✅ |
| VI. Data protection | Password used once; token in memory only, masked repr, host-scoped; nothing written to disk/report | ✅ |
| VII. English only | All UI strings defined in contracts in English | ✅ |
| VIII. Human authorship | No change to commit process | ✅ |

**Post-design re-check (after Phase 1)**: ✅ all gates still pass. The breaking change to
`KoboImageClient.__init__` is internal (only `app.py` uses it) and covered by tests.

## Project Structure

### Documentation (this feature)

```text
specs/001-kobo-account-login/
├── plan.md              # This file
├── research.md          # Phase 0: endpoint verification and decisions
├── data-model.md        # Phase 1: KoboServer, KoboSession, AuthState, errors
├── quickstart.md        # Phase 1: validation guide
├── contracts/
│   ├── kobo-http.md     # Kobo endpoints and response mapping
│   ├── python-api.md    # kobo_auth / kobo_client interfaces
│   └── ui-login-panel.md# Sidebar panel and image-area states
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
src/evaluate_kobo_form_images/
├── kobo_auth.py         # NEW: KoboServer, KoboSession, detect_server, sign_in_* , AuthError
├── kobo_client.py       # CHANGED: session-based client, host-scoped token, FetchFailure
├── app.py               # CHANGED: "Kobo account" panel, session state, image-area messages
└── (xlsform.py, kobo_export.py, evaluation.py, report.py unchanged)

tests/
├── test_kobo_auth.py    # NEW: server normalization/detection, password & token sign-in paths
└── test_kobo_client.py  # CHANGED: host scoping, failure reasons, cache without session
```

**Structure Decision**: Keep the single src-layout package; add one domain module
(`kobo_auth.py`) next to `kobo_client.py`. Docs to update in the implementation commit:
`README.md` (Getting started / Using the app), `CONSTITUTION.md` (architecture table, decision
log), `.env.example` comment.

## Complexity Tracking

No constitution violations; nothing to justify.
