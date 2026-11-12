# Feature Specification: Kobo Account Login

**Feature Branch**: `001-kobo-account-login`

**Created**: 2026-11-12

**Status**: Draft

**Input**: User description: "Add an option inside the interface so users can log in to their Kobo account and correctly view the image linked to each URL. Is this possible?" (originally written in Spanish)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Log in with Kobo username and password (Priority: P1)

An evaluator opens the app, selects a form and its data export, and sees that the images
cannot be shown because Kobo attachments are private. Instead of finding and copying an API
key, the evaluator types the Kobo server, username and password into a login panel in the
sidebar. The app confirms the login ("Signed in as <username>") and the images start showing
right away.

**Why this priority**: Today images only show if the evaluator already knows how to get an
API key from Kobo account settings. Most field reviewers know their username and password,
not their API key. Without a simple login, the core review work cannot start.

**Independent Test**: Start the app with no token configured, load a form and its export,
log in with valid Kobo credentials, and check that the current image is shown without any
other setup.

**Acceptance Scenarios**:

1. **Given** the evaluator is not signed in and an export is loaded, **When** they enter a
   valid username and password for the Kobo server that hosts the images and press
   "Sign in", **Then** the app shows "Signed in as <username>" and the current image is shown.
2. **Given** the evaluator enters a wrong username or password, **When** they press
   "Sign in", **Then** the app shows a clear "Invalid Kobo username or password" message,
   stays signed out, and does not display the password back.
3. **Given** the evaluator is signed in, **When** they move to the next image, **Then** the
   image is shown without asking for credentials again.

---

### User Story 2 - Sign out and switch account (Priority: P2)

An evaluator who shares a computer, or who used the wrong account, signs out from the
sidebar. Their access is removed from the session and they can sign in with another account.

**Why this priority**: Protects access to private field data on shared computers and lets
reviewers fix a wrong-account login without restarting the app.

**Independent Test**: Sign in, press "Sign out", and check that images no longer download
and the login panel is shown again; then sign in with a different account.

**Acceptance Scenarios**:

1. **Given** the evaluator is signed in, **When** they press "Sign out", **Then** the app
   forgets the session access, shows the login panel again, and new images are no longer
   downloaded.
2. **Given** the evaluator signed out, **When** they sign in with another account, **Then**
   the app shows the new username and uses its access from then on.

---

### User Story 3 - Keep the API key option and guide the evaluator (Priority: P3)

Evaluators whose Kobo account has no password (e.g. they sign in to Kobo through their
organization's single sign-on) or who prefer API keys can still paste an API key. The login
panel explains both options and links to where the API key is found in Kobo.

**Why this priority**: Single sign-on accounts cannot use username/password login, and the
existing API-key method must keep working for current users.

**Independent Test**: With the login panel open, choose "Use an API key instead", paste a
valid key, and check that images are shown and the panel shows "Signed in as <username>".

**Acceptance Scenarios**:

1. **Given** the evaluator chooses the API key option, **When** they paste a valid key,
   **Then** the app checks it, shows the account username and images are shown.
2. **Given** an API key is already configured on the machine (environment file), **When** the
   app starts, **Then** the evaluator is signed in automatically and the panel says so.
3. **Given** the evaluator pastes an invalid key, **When** the app checks it, **Then** it
   shows "This API key is not valid for <server>" and stays signed out.

---

### Edge Cases

- **Wrong server**: the account belongs to a different Kobo server than the one hosting the
  images (e.g. global server vs. EU server). The app pre-selects the server found in the
  image links and warns if the signed-in server differs from it.
- **No access to the project**: the login succeeds but the account cannot see this project's
  attachments; the app shows "Your account does not have access to these images" instead of a
  generic error.
- **Session expires or key is revoked** during review: the next image fails with an
  "access expired, please sign in again" message and the login panel reopens; evaluations
  already saved are not affected.
- **Kobo unreachable / no internet**: the app reports that Kobo cannot be reached and lets the
  evaluator retry; already cached images remain visible.
- **Account with single sign-on only**: a username/password attempt fails; the message points
  the evaluator to the API key option.
- **Several exports from different servers** in one session: access is tied to the server it
  was obtained for; the app asks to sign in for the other server when needed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The app MUST provide a login panel where the evaluator chooses the Kobo server
  and enters a Kobo username and password.
- **FR-002**: The app MUST pre-select the Kobo server detected from the image links of the
  loaded data export, and offer the public Kobo servers (global and EU) plus a custom server
  address.
- **FR-003**: On sign-in, the app MUST verify the credentials with Kobo and, if valid, use the
  resulting access for every image download in the session without asking again.
- **FR-004**: The app MUST show the signed-in username and server while signed in.
- **FR-005**: The app MUST show distinct, plain-language messages for: invalid credentials,
  account without access to the images, unreachable server, and expired or revoked access.
- **FR-006**: The app MUST provide a "Sign out" action that removes the session access and
  stops further authenticated downloads.
- **FR-007**: The app MUST keep the API key alternative: pasting a key, or a key configured on
  the machine, signs the evaluator in after the key is verified.
- **FR-008**: The app MUST NOT store the password anywhere (disk, logs, evaluation files,
  Excel report) and MUST discard it right after the sign-in attempt.
- **FR-009**: The session access MUST be kept only in memory for the current browser session
  and MUST NOT be written to the evaluation files, the Excel report or the repository.
- **FR-010**: When an image cannot be downloaded because the evaluator is not signed in, the
  image area MUST invite them to sign in instead of showing a raw error.
- **FR-011**: Images already downloaded in the session MUST remain viewable after a failed
  re-authentication, and saved evaluations MUST never be lost because of login problems.
- **FR-012**: All login texts and messages MUST be in English.

### Key Entities

- **Kobo server**: the Kobo instance hosting the forms and attachments; identified by its
  address (detected from image links or chosen by the evaluator).
- **Kobo session access**: the proof of identity obtained after a successful sign-in (from
  username/password or an API key); belongs to one server and one Kobo username; lives only
  for the browser session.
- **Evaluator identity**: the Kobo username shown in the app; may pre-fill the evaluator name
  recorded in evaluations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An evaluator with valid Kobo credentials sees the first image within 1 minute of
  opening the app, without visiting the Kobo website.
- **SC-002**: 100% of images that the signed-in account can access in Kobo are shown in the
  app; none show an authentication error while the session is valid.
- **SC-003**: After signing in once, an evaluator reviews at least 100 consecutive images
  without being asked for credentials again.
- **SC-004**: Each failed sign-in shows one of the specific messages of FR-005; no failure
  shows a raw technical error.
- **SC-005**: A search of the evaluation files, Excel reports, logs and repository after a
  review session finds no password or session access.

## Assumptions

- **It is possible**: Kobo lets an account exchange its username and password for its API
  key, and that key gives access to the private image links. The feature is therefore
  feasible without changes on the Kobo side. Logging in through Kobo's own web page
  (browser redirect / OAuth) is not offered by public Kobo servers to third-party apps, so it
  is out of scope.
- Accounts that only use single sign-on have no Kobo password; they use the API key option
  (User Story 3).
- The app keeps running locally for a single evaluator per browser session; multi-user
  accounts, roles or permissions inside the app are out of scope.
- The evaluator name recorded in evaluations defaults to the Kobo username but stays editable.
- No "remember me" across app restarts in this version; the evaluator signs in again after
  restarting the app (unless an API key is configured on the machine).
- The existing image cache, autosave and Excel report keep working unchanged.
