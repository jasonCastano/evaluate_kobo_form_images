# Tasks: Kobo Account Login

**Input**: Design documents from `/specs/001-kobo-account-login/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: INCLUDED. Constitution Principle V ("new behavior ships with pytest tests …
synthetic fixtures only") makes tests mandatory. HTTP is stubbed (research R7): never call
real Kobo servers and never use real credentials in tests.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested
independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on incomplete tasks)
- **[Story]**: US1 = username/password sign-in (P1), US2 = sign out / switch account (P2),
  US3 = API key option (P3)

## Path Conventions

Single src-layout package: `src/evaluate_kobo_form_images/`, tests in `tests/`. Run all
commands through the Makefile (it forces `UV_PROJECT_ENVIRONMENT=.venv`).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare branch and empty modules; no new dependencies are needed (plan: requests,
Pillow, Streamlit already installed).

- [X] T001 Create and switch to git branch `001-kobo-account-login` from an up-to-date `main` (repository root); do not commit anything yet
- [X] T002 [P] Create `src/evaluate_kobo_form_images/kobo_auth.py` with the module docstring "Sign in to KoboToolbox and hold the in-memory session used to download private attachments." and `from __future__ import annotations`
- [X] T003 [P] Create `tests/test_kobo_auth.py` with a module docstring and a reusable fake HTTP helper: a `FakeHttp` class exposing `get(url, *, headers=None, auth=None, timeout=None)` that records each call (url, headers, auth) and returns queued fake responses (objects with `status_code`, `ok`, `content`, `json()`); support raising `requests.ConnectionError` / `requests.Timeout` from the queue

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Server/session value objects, error types, host-scoped image client and the
session plumbing in the UI. Every user story depends on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Tests (write first, must fail before implementation)

- [X] T004 [P] Add tests in `tests/test_kobo_auth.py` for `KoboServer.from_url`: normalizes to `scheme://host[:port]` with lower-case host, no trailing slash and no path (e.g. `"https://KF.kobotoolbox.org/api/v2/assets/x/"` → `"https://kf.kobotoolbox.org"`); rejects missing host and non-http(s) schemes and rejects `http://` except `http://localhost*` with `AuthError(kind=INVALID_SERVER)` and message "Enter a valid Kobo server address, e.g. https://kf.kobotoolbox.org"; known servers get labels "Global (kf.kobotoolbox.org)" and "EU (eu.kobotoolbox.org)", other hosts use the host as label; `owns(url)` is true only for the same scheme://host[:port]
- [X] T005 [P] Add tests in `tests/test_kobo_auth.py` for `detect_server(urls)`: returns the most frequent scheme://host among URLs (ties → first seen), ignores blank/invalid URLs, returns `GLOBAL_SERVER` for an empty list
- [X] T006 [P] Add tests in `tests/test_kobo_auth.py` that `repr(KoboSession(...))` and `str(...)` never contain the full token (only `****` + last 4 chars) and that `KoboSession` is frozen
- [X] T007 [P] Add tests in `tests/test_kobo_client.py` (update existing ones to the new constructor `KoboImageClient(session, cache_dir)`): (a) the `Authorization: Token <key>` header is sent only when `session.server.owns(url)`; a URL on another host is fetched without it; (b) failure mapping per contracts/kobo-http.md §3: 401/403/404 without credentials → `FetchFailure.NOT_SIGNED_IN`, 401 with credentials → `ACCESS_EXPIRED`, 403/404 with credentials → `NO_ACCESS`, 5xx / `ConnectionError` / `Timeout` → `UNREACHABLE`, undecodable 200 body → `NOT_AN_IMAGE`; (c) a cached URL is returned with `session=None` and without any HTTP call; use an injected fake HTTP object, never the network

### Implementation

- [X] T008 Implement in `src/evaluate_kobo_form_images/kobo_auth.py`: `AuthErrorKind(StrEnum)` with `INVALID_CREDENTIALS`, `INVALID_TOKEN`, `UNREACHABLE`, `INVALID_SERVER`, `UNEXPECTED`; `AuthError(Exception)` with `kind` and plain-English `message` attributes; frozen dataclass `KoboServer(base_url, label)` with `from_url` and `owns` per T004; constants `GLOBAL_SERVER`, `EU_SERVER`, `KNOWN_SERVERS`; `detect_server(urls)` per T005
- [X] T009 Implement in `src/evaluate_kobo_form_images/kobo_auth.py`: `SignInMethod(StrEnum)` with `PASSWORD="username & password"`, `API_KEY="API key"`, `ENVIRONMENT="environment"`; frozen dataclass `KoboSession(server, username, token, method, signed_in_at)` with `token` excluded from the generated repr and a custom `__repr__` showing `token=****<last4>`; `signed_in_at` = ISO-8601 UTC seconds
- [X] T010 Implement private helper `_fetch_username(server, token, http) -> str` in `src/evaluate_kobo_form_images/kobo_auth.py`: `GET {server}/me/?format=json` with headers `Authorization: Token <token>` and `Accept: application/json`, timeout 30 s; 200 with `username` → username; 401 → `AuthError(INVALID_TOKEN, "This API key is not valid for <server label>.")`; 200 without `username` or non-JSON → `AuthError(INVALID_SERVER, "<server> does not look like a Kobo server.")`; 5xx/`ConnectionError`/`Timeout` → `AuthError(UNREACHABLE, "Kobo (<server label>) cannot be reached. Check your connection and retry.")`; other statuses → `AuthError(UNEXPECTED, "Kobo answered HTTP <code>.")`; never log the token (depends on T008, T009)
- [X] T011 Refactor `src/evaluate_kobo_form_images/kobo_client.py` per contracts/python-api.md: add `FetchFailure(StrEnum)` (`NOT_SIGNED_IN`, `ACCESS_EXPIRED`, `NO_ACCESS`, `UNREACHABLE`, `NOT_AN_IMAGE`); give `ImageFetchError` a `reason: FetchFailure` attribute; change `KoboImageClient.__init__(self, session: KoboSession | None, cache_dir: Path, timeout: int = 30, http: requests.Session | None = None)`; stop setting a session-wide Authorization header — add it per request only when `session is not None and session.server.owns(url)`; map responses to reasons and the exact UI messages of contracts/ui-login-panel.md; keep cache-first behavior so cached images work with `session=None` (depends on T008, T009)
- [X] T012 (implemented directly in its final form; the transitional token input was not needed because US1 and US3 shipped together) Update `src/evaluate_kobo_form_images/app.py` session plumbing: remove the `get_client(token)` `st.cache_resource` (it kept tokens process-wide) and add helpers `current_session() -> KoboSession | None` and `image_client() -> KoboImageClient` that store/rebuild the client in `st.session_state["kobo_client"]` whenever `st.session_state["kobo_session"]` changes (compare by identity); keep the prefetch executor but pass it the session-scoped client. Transitional behavior (removed in T020): keep the existing "Kobo API token" input; when it holds a value, build an unverified `KoboSession(server=detect_server(record urls), username="(unverified)", token=<value>, method=SignInMethod.API_KEY, signed_in_at=<now>)` so current users keep working until US1/US3 land; when empty, use a client with `session=None` (depends on T011)
- [X] T013 Update `render_image` in `src/evaluate_kobo_form_images/app.py` to switch on `ImageFetchError.reason`: `NOT_SIGNED_IN` → `st.info("Sign in to your Kobo account in the sidebar to see this image.")`; `ACCESS_EXPIRED` → remove `kobo_session` and `kobo_client` from `st.session_state`, `st.warning("Your Kobo access expired or was revoked. Please sign in again.")`; `NO_ACCESS` → `st.error("Your account does not have access to this image (or it no longer exists in Kobo).")`; `UNREACHABLE` → `st.error(message)` plus a "Retry" button that reruns; `NOT_AN_IMAGE` → `st.error("The downloaded file is not a readable image.")`; the evaluation form must stay usable in every case (depends on T011, T012)
- [X] T014 Run `make check` (repository root) and fix failures until T004–T007 pass

**Checkpoint**: Foundation ready — app runs with no sign-in (images show the sign-in invitation) and tokens can no longer leak to other hosts.

---

## Phase 3: User Story 1 - Log in with Kobo username and password (Priority: P1) 🎯 MVP

**Goal**: Evaluator selects/confirms the server, enters username and password, and images show for the rest of the session.

**Independent Test**: With no `KOBO_API_TOKEN`, load a form + export, sign in with valid credentials → "Signed in as <user> on <server>" and the current image is shown; wrong password → "Invalid Kobo username or password…"; next images show without new prompts (quickstart scenarios 1–4).

### Tests for User Story 1

- [X] T015 [P] [US1] Add tests in `tests/test_kobo_auth.py` for `sign_in_with_password(server, username, password, http=fake)`: calls `GET {server}/token/?format=json` with HTTP Basic `(username, password)` then `/me/` with the returned token; returns `KoboSession(method=PASSWORD, username=<from /me/>, token=<from /token/>)`; 401 on `/token/` → `AuthError(INVALID_CREDENTIALS)` whose message is exactly "Invalid Kobo username or password. If you sign in to Kobo with your organization (SSO) or use two-factor authentication, use an API key instead."; 200 without `token` → `INVALID_SERVER`; `ConnectionError` → `UNREACHABLE`; empty username or password → `INVALID_CREDENTIALS` with no HTTP call; assert the password never appears in any exception message or repr
- [X] T016 [P] [US1] Add a Streamlit `AppTest` test in `tests/test_app_login.py` that builds the synthetic form/export from `tests/conftest.py` into `KOBO_FORMS_DIR`/`KOBO_DATA_DIR` temp folders (via `monkeypatch.setenv`), monkeypatches `evaluate_kobo_form_images.kobo_auth.sign_in_with_password` to return a fake `KoboSession`, fills the username/password form and asserts the sidebar shows "Signed in as" with the username and the evaluator name is pre-filled; a second case makes it raise `AuthError(INVALID_CREDENTIALS, ...)` and asserts the error text is shown and no session is stored

### Implementation for User Story 1

- [X] T017 [US1] Implement `sign_in_with_password(server, username, password, *, http=None) -> KoboSession` in `src/evaluate_kobo_form_images/kobo_auth.py` per contracts/kobo-http.md §1 and T015; use `requests.Session()` when `http` is None; pass the password only as the Basic `auth` tuple of that single request and do not keep any reference to it (depends on T010)
- [X] T018 [US1] Add the server selector to sidebar section "3. Kobo account" in `src/evaluate_kobo_form_images/app.py`: options `Global (kf.kobotoolbox.org)`, `EU (eu.kobotoolbox.org)`, `Custom…`; default = `detect_server` over the loaded records' `image_url` (Global when no export is loaded); `Custom…` shows a "Server URL" text input validated with `KoboServer.from_url` (show its error message on failure)
- [X] T019 [US1] Add the "Username & password" tab in `src/evaluate_kobo_form_images/app.py`: `st.form(..., clear_on_submit=True)` with "Username", "Password" (`type="password"`) and a "Sign in" submit; on submit call `sign_in_with_password` inside `st.spinner("Signing in…")`; on success store the session in `st.session_state["kobo_session"]`, drop any `kobo_auth_error`, and `st.rerun()`; on `AuthError` store `str(message)` in `st.session_state["kobo_auth_error"]` and render it with `st.error` under the form; never write the password to session state, logs or files (depends on T017, T018)
- [X] T020 [US1] Render the signed-in state in `src/evaluate_kobo_form_images/app.py`: `st.success("Signed in as **<username>** on <server label>")` plus caption "via <method> · <HH:MM> UTC"; show `st.warning("The images in this export are hosted on <host>.")` when `detect_server(records) != session.server`; pre-fill the "Evaluator name" input with the username only when it is empty (keep it editable); remove the old "Kobo API token" text input (depends on T019)
- [ ] T021 [US1] Run `make check` and quickstart scenarios 1–4 manually with a real account (`specs/001-kobo-account-login/quickstart.md`)

**Checkpoint**: MVP — username/password sign-in works end to end.

---

## Phase 4: User Story 2 - Sign out and switch account (Priority: P2)

**Goal**: Evaluator can drop their access and sign in with another account without restarting.

**Independent Test**: Sign in, press "Sign out" → login panel returns, uncached images show the sign-in invitation, cached ones still show; sign in with another account → new username shown (quickstart scenario 5).

### Tests for User Story 2

- [X] T022 [P] [US2] Add `AppTest` cases in `tests/test_app_login.py`: with a fake `KoboSession` pre-set in session state, clicking "Sign out" removes `kobo_session` and `kobo_client` from session state and shows the login form; signing in again with a different fake user shows the new username; when the fake client raises `ImageFetchError(reason=ACCESS_EXPIRED)` the session is cleared and the warning "Your Kobo access expired or was revoked. Please sign in again." is shown

### Implementation for User Story 2

- [X] T023 [US2] Add a "Sign out" button to the signed-in panel in `src/evaluate_kobo_form_images/app.py` that deletes `kobo_session`, `kobo_client` and `kobo_auth_error` from `st.session_state` and reruns; do not delete evaluations, the image cache or the evaluator name (depends on T020)
- [X] T024 [US2] Ensure `image_client()` in `src/evaluate_kobo_form_images/app.py` rebuilds the client after a different `KoboSession` is stored (switch account) and that prefetch jobs submitted before sign-out cannot attach the old token (they hold the old client object; verify the old client is not reused for new URLs) (depends on T023)

**Checkpoint**: US1 and US2 work independently.

---

## Phase 5: User Story 3 - Keep the API key option and guide the evaluator (Priority: P3)

**Goal**: SSO/MFA users and existing users can sign in with an API key (pasted or from `.env`).

**Independent Test**: "API key" tab → paste a valid key → "Signed in as <key owner>"; invalid key → "This API key is not valid for <server>."; `KOBO_API_TOKEN` in `.env` → signed in automatically "via environment" (quickstart scenarios 6–8).

### Tests for User Story 3

- [X] T025 [P] [US3] Add tests in `tests/test_kobo_auth.py` for `sign_in_with_token(server, token, method, http=fake)`: valid → `KoboSession` with username from `/me/` and the given method; 401 → `AuthError(INVALID_TOKEN, "This API key is not valid for <server label>.")`; empty/whitespace token → `INVALID_TOKEN` without HTTP call; token is stripped of surrounding whitespace before use
- [X] T026 [P] [US3] Add `AppTest` cases in `tests/test_app_login.py`: API key tab success/failure with `sign_in_with_token` monkeypatched; with `KOBO_API_TOKEN` set via `monkeypatch.setenv`, the first run signs in automatically with `method=ENVIRONMENT` exactly once (a failed attempt is not retried on every rerun and shows its message)

### Implementation for User Story 3

- [X] T027 [US3] Implement `sign_in_with_token(server, token, method=SignInMethod.API_KEY, *, http=None) -> KoboSession` in `src/evaluate_kobo_form_images/kobo_auth.py` reusing `_fetch_username` (depends on T010)
- [X] T028 [US3] Add the "API key" tab next to "Username & password" in `src/evaluate_kobo_form_images/app.py`: `st.form(clear_on_submit=True)` with "API key" (`type="password"`) and "Sign in"; same success/error handling as T019; add the caption "Use an API key if you sign in to Kobo with your organization (SSO) or with two-factor authentication. Find it in Kobo > Account settings > Security." below the tabs (depends on T027, T019)
- [X] T029 [US3] Implement environment auto sign-in in `src/evaluate_kobo_form_images/app.py`: when `KOBO_API_TOKEN` is set, no `kobo_session` exists and `st.session_state["kobo_env_attempted"]` is not set, call `sign_in_with_token(detected_server, token, SignInMethod.ENVIRONMENT)` once, mark the attempt, and store the session or the error message (depends on T027, T018)

**Checkpoint**: All three stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T030 [P] Update `README.md`: "Getting started" (API key now optional; sign in from the sidebar with username/password or API key), "Using the app" step 2, and the Features table row "Authenticated download"
- [X] T031 [P] Update `CONSTITUTION.md`: add `kobo_auth.py` to the §5 architecture table and diagram, add decision-log rows "2026-11-12 | Sign in with Kobo username/password via /token/ (password used once, key in memory only) | Reviewers know passwords, not API keys" and "2026-11-12 | Send the API key only to the signed-in server host | Prevent token leakage", and tick the roadmap item if applicable
- [X] T032 [P] Update `.env.example` comment for `KOBO_API_TOKEN`: optional; when set, the app signs in automatically; otherwise sign in from the sidebar
- [X] T033 Secret-safety review across `src/evaluate_kobo_form_images/`: confirm no `print`/logging of password or token, `KoboSession` repr masked, no token in exception messages, Excel report and evaluation JSON unchanged (grep for `token` and `password` usages)
- [X] T034 Run `make check` and `uv run pre-commit run --all-files` (with `UV_PROJECT_ENVIRONMENT=.venv`); all green
- [ ] T035 Run the full manual quickstart (`specs/001-kobo-account-login/quickstart.md` scenarios 1–10 and the secret-leak check) with a real Kobo account; record results in the PR description
- [X] T036 Commit with Conventional Commits (e.g. `feat: sign in to Kobo from the sidebar`), human author only, no AI trailers; push the branch and open a PR to `main` using the PR template

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)** → no dependencies.
- **Foundational (Phase 2)** → depends on Setup; **blocks all stories**.
- **US1 (Phase 3)** → depends on Foundational.
- **US2 (Phase 4)** → depends on US1's signed-in panel (T020) for the button placement; its logic (clearing session state) is otherwise independent.
- **US3 (Phase 5)** → depends on Foundational (T010) and reuses the panel/tabs from US1 (T019) — can start in parallel with US2.
- **Polish (Phase 6)** → after the desired stories are complete.

### Story completion order

```text
Setup → Foundational → US1 (MVP) ─┬─► US2
                                  └─► US3 → Polish
```

### Within each story

Tests first (must fail) → `kobo_auth.py` functions → `app.py` UI → `make check`.

### Parallel opportunities

- T002 ∥ T003 (different files).
- T004 ∥ T005 ∥ T006 ∥ T007 (test-only, independent).
- T015 ∥ T016 (US1 tests); T022 (US2) ∥ T025 ∥ T026 (US3) once US1 is done.
- T030 ∥ T031 ∥ T032 (docs).
- Not parallel: tasks editing `app.py` (T012, T013, T018–T020, T023, T024, T028, T029) must run sequentially.

## Parallel Example: User Story 1

```text
Task: "T015 [US1] tests for sign_in_with_password in tests/test_kobo_auth.py"
Task: "T016 [US1] AppTest login flow in tests/test_app_login.py"
# then sequentially: T017 → T018 → T019 → T020 → T021
```

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phase 1 + Phase 2 (foundation, host-scoped client, sign-in invitation).
2. Phase 3 (US1) → validate quickstart 1–4 → can be merged on its own.

### Incremental delivery

1. MVP (US1) → evaluators sign in with username/password.
2. + US2 → sign out / switch account.
3. + US3 → API key tab and `.env` auto sign-in (restores today's API-key convenience; until
   US3 lands, the `.env` key is not used — ship US1 and US3 together if current users rely on
   `.env`).
4. Polish → docs, secret review, full quickstart, PR.
