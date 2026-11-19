"""Streamlit user interface to evaluate images collected with KoboToolbox forms.

Run with ``make run`` or ``uv run evaluate-kobo-images``.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from evaluate_kobo_form_images import __version__, kobo_auth
from evaluate_kobo_form_images.evaluation import (
    Evaluation,
    EvaluationStore,
    Verdict,
)
from evaluate_kobo_form_images.kobo_auth import (
    EU_SERVER,
    GLOBAL_SERVER,
    AuthError,
    KoboServer,
    KoboSession,
    SignInMethod,
)
from evaluate_kobo_form_images.kobo_client import (
    EXPIRED_MESSAGE,
    FetchFailure,
    ImageFetchError,
    KoboImageClient,
)
from evaluate_kobo_form_images.kobo_export import ExportScan, ImageRecord, scan_export
from evaluate_kobo_form_images.reasons import (
    ReasonCatalogue,
    ReasonError,
    catalogue_path,
    reason_widget_id,
    rename_reason_in_stores,
    report_reasons,
)
from evaluate_kobo_form_images.report import (
    PENDING,
    ReportSaveError,
    build_report,
    save_report,
)
from evaluate_kobo_form_images.report_import import (
    ImportResult,
    ReportImportError,
    import_report,
)
from evaluate_kobo_form_images.xlsform import KoboForm, parse_xlsform

load_dotenv()

FORMS_DIR = Path(os.getenv("KOBO_FORMS_DIR", "forms"))
DATA_DIR = Path(os.getenv("KOBO_DATA_DIR", "data"))
EVALUATIONS_DIR = Path(os.getenv("EVALUATIONS_DIR", "evaluations"))
CACHE_DIR = Path(os.getenv("IMAGE_CACHE_DIR", ".cache/images"))
PREFETCH_AHEAD = 3
STATUS_FILTERS = ("All", PENDING, Verdict.VALID.value, Verdict.INVALID.value)
CUSTOM_SERVER = "Custom…"
SERVER_OPTIONS = {GLOBAL_SERVER.label: GLOBAL_SERVER, EU_SERVER.label: EU_SERVER}
API_KEY_HELP = (
    "Use an API key if you sign in to Kobo with your organization (SSO) or with two-factor "
    "authentication. Find it in Kobo > Account settings > Security."
)
# Session-state keys (memory only, per browser tab; never persisted).
SESSION_KEY = "kobo_session"
CLIENT_KEY = "kobo_client"
ERROR_KEY = "kobo_auth_error"
ENV_ATTEMPT_KEY = "kobo_env_attempted"
REASON_ERROR_KEY = "reason_error"
REASON_NOTICE_KEY = "reason_notice"
REASON_WARNED_KEY = "reason_file_warned"
MANAGE_MESSAGE_KEY = "manage_reasons_message"
MANAGE_ERROR_KEY = "manage_reasons_error"


# --------------------------------------------------------------------------- loaders
@st.cache_data(show_spinner="Reading the Kobo form...")
def load_form(content: bytes, file_name: str) -> KoboForm:
    """Parse an XLSForm (cached by content)."""
    return parse_xlsform(io.BytesIO(content), file_name=file_name)


@st.cache_data(show_spinner="Scanning the data export for images...")
def load_export(content: bytes, file_name: str, _form: KoboForm, form_key: str) -> ExportScan:
    """Scan a Kobo data export (cached by content and form)."""
    del form_key  # only part of the cache key
    return scan_export(io.BytesIO(content), _form, file_name=file_name)


@st.cache_resource
def get_executor() -> ThreadPoolExecutor:
    """Shared thread pool used to prefetch the next images."""
    return ThreadPoolExecutor(max_workers=PREFETCH_AHEAD)


def _prefetch(client: KoboImageClient, url: str) -> None:
    with contextlib.suppress(ImageFetchError):
        client.fetch(url)


def _xlsx_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.rglob("*.xlsx") if not p.name.startswith("~$"))


def _pick_file(label: str, directory: Path, key: str) -> tuple[bytes, str] | None:
    """Let the user pick a file from a project folder or upload one."""
    files = _xlsx_files(directory)
    options = ["Upload a file...", *(p.relative_to(directory).as_posix() for p in files)]
    choice = st.selectbox(label, options, key=f"{key}_choice")
    if choice == options[0]:
        uploaded = st.file_uploader(f"Upload {label.lower()}", type=["xlsx"], key=f"{key}_upload")
        return (uploaded.getvalue(), uploaded.name) if uploaded else None
    path = directory / choice
    return path.read_bytes(), path.name


# --------------------------------------------------------------------------- Kobo account
def current_session() -> KoboSession | None:
    """Return the signed-in Kobo session of this browser tab, if any."""
    return st.session_state.get(SESSION_KEY)


def image_client() -> KoboImageClient:
    """Return the image client bound to the current session (rebuilt when it changes)."""
    session = current_session()
    client: KoboImageClient | None = st.session_state.get(CLIENT_KEY)
    if client is None or client.kobo_session is not session:
        client = KoboImageClient(session, CACHE_DIR)
        st.session_state[CLIENT_KEY] = client
    return client


def sign_out(message: str | None = None) -> None:
    """Forget the Kobo session and its client (evaluations and cache are kept)."""
    for key in (SESSION_KEY, CLIENT_KEY, ERROR_KEY):
        st.session_state.pop(key, None)
    if message:
        st.session_state[ERROR_KEY] = message


def _store_session(session: KoboSession) -> None:
    st.session_state[SESSION_KEY] = session
    st.session_state.pop(ERROR_KEY, None)
    if not st.session_state.get("evaluator"):
        st.session_state["evaluator"] = session.username


def _choose_server(detected: KoboServer) -> KoboServer | None:
    """Server selector pre-selected from the image links; ``None`` if the custom URL is bad."""
    options = [*SERVER_OPTIONS, CUSTOM_SERVER]
    default = options.index(detected.label) if detected.label in SERVER_OPTIONS else 2
    choice = st.selectbox("Server", options, index=default, key="kobo_server_choice")
    if choice != CUSTOM_SERVER:
        return SERVER_OPTIONS[choice]
    url = st.text_input(
        "Server URL",
        value="" if detected.label in SERVER_OPTIONS else detected.base_url,
        placeholder="https://kobo.example.org",
        key="kobo_server_url",
    )
    try:
        return KoboServer.from_url(url)
    except AuthError as exc:
        st.error(exc.message)
        return None


def _attempt(sign_in: Callable[[], KoboSession]) -> None:
    """Run a sign-in inside a widget callback (the script reruns right after)."""
    try:
        session = sign_in()
    except AuthError as exc:
        st.session_state[ERROR_KEY] = exc.message
        return
    _store_session(session)


def _submit_password(server: KoboServer | None) -> None:
    """Form callback: read and immediately wipe the password, then sign in."""
    username = st.session_state.get("kobo_username", "")
    password = st.session_state.get("kobo_password", "")
    st.session_state["kobo_password"] = ""
    if server is not None:
        _attempt(lambda: kobo_auth.sign_in_with_password(server, username, password))


def _submit_api_key(server: KoboServer | None) -> None:
    """Form callback: read and immediately wipe the API key, then sign in."""
    api_key = st.session_state.get("kobo_api_key", "")
    st.session_state["kobo_api_key"] = ""
    if server is not None:
        _attempt(lambda: kobo_auth.sign_in_with_token(server, api_key, SignInMethod.API_KEY))


def _auto_sign_in(server: KoboServer) -> None:
    """Sign in once with ``KOBO_API_TOKEN`` from the environment, if configured."""
    token = os.getenv("KOBO_API_TOKEN", "").strip()
    if not token or current_session() is not None or st.session_state.get(ENV_ATTEMPT_KEY):
        return
    st.session_state[ENV_ATTEMPT_KEY] = True
    try:
        session = kobo_auth.sign_in_with_token(server, token, SignInMethod.ENVIRONMENT)
    except AuthError as exc:
        st.session_state[ERROR_KEY] = exc.message
        return
    _store_session(session)


def render_account(image_urls: list[str]) -> None:
    """Sidebar panel to sign in to Kobo (username/password or API key) or sign out."""
    st.header("3. Kobo account")
    detected = kobo_auth.detect_server(image_urls)
    _auto_sign_in(detected)
    session = current_session()
    if session is not None:
        st.success(f"Signed in as **{session.username}** on {session.server.label}")
        st.caption(f"via {session.method.value} · {session.signed_in_at[11:16]} UTC")
        if st.button("Sign out", key="kobo_sign_out", width="stretch"):
            sign_out()
            st.rerun()
        if image_urls and detected != session.server:
            host = detected.base_url.split("://", 1)[-1]
            st.warning(f"The images in this export are hosted on {host}.")
        return

    server = _choose_server(detected)
    password_tab, key_tab = st.tabs(["Username & password", "API key"])
    with password_tab, st.form("kobo_password_form"):
        st.text_input("Username", key="kobo_username")
        st.text_input("Password", type="password", key="kobo_password")
        st.form_submit_button(
            "Sign in",
            width="stretch",
            key="kobo_password_submit",
            on_click=_submit_password,
            args=(server,),
        )
    with key_tab, st.form("kobo_key_form"):
        st.text_input("API key", type="password", key="kobo_api_key")
        st.form_submit_button(
            "Sign in",
            width="stretch",
            key="kobo_key_submit",
            on_click=_submit_api_key,
            args=(server,),
        )
    st.caption(API_KEY_HELP)
    if st.session_state.get(ERROR_KEY):
        st.error(st.session_state[ERROR_KEY])


# --------------------------------------------------------------------------- sidebar
def sidebar() -> tuple[KoboForm | None, ExportScan | None, str]:
    """Render the sidebar inputs and return the loaded form, export and evaluator name."""
    form = scan = None
    with st.sidebar:
        st.header("1. Kobo form")
        form_file = _pick_file("Form (XLSForm)", FORMS_DIR, "form")
        st.header("2. Collected data")
        data_file = _pick_file("Data export", DATA_DIR, "data")
        if form_file:
            try:
                form = load_form(*form_file)
            except Exception as exc:
                st.error(f"Could not read the form: {exc}")
        if form_file and form and data_file:
            try:
                form_key = hashlib.sha1(form_file[0]).hexdigest()
                scan = load_export(data_file[0], data_file[1], form, form_key)
            except Exception as exc:
                st.error(f"Could not read the data export: {exc}")
        render_account([r.image_url for r in scan.records] if scan else [])
        evaluator = st.text_input("Evaluator name", key="evaluator")
    return form, scan, evaluator


# --------------------------------------------------------------------------- main view
def status_of(record: ImageRecord, store: EvaluationStore) -> str:
    """Return ``Valid``, ``Invalid`` or ``Pending`` for a record."""
    evaluation = store.get(record.key)
    return evaluation.verdict.value if evaluation else PENDING


def render_summary(form: KoboForm, scan: ExportScan, store: EvaluationStore) -> None:
    """Render the progress metrics and data warnings."""
    total = len(scan.records)
    valid = sum(1 for r in scan.records if status_of(r, store) == Verdict.VALID.value)
    invalid = sum(1 for r in scan.records if status_of(r, store) == Verdict.INVALID.value)
    done = valid + invalid
    cols = st.columns(5)
    cols[0].metric("Image questions in form", len(form.image_questions))
    cols[1].metric("Images collected", total)
    cols[2].metric("Valid", valid)
    cols[3].metric("Invalid", invalid)
    cols[4].metric("Pending", total - done)
    st.progress(done / total if total else 0.0, text=f"{done} of {total} images evaluated")
    if scan.unmapped_columns:
        st.warning(
            "Some image columns of the export did not match any image question of the form "
            "(is this the right form?). They are still listed using the column header: "
            + ", ".join(scan.unmapped_columns[:10])
        )
    if scan.missing_uploads:
        st.warning(f"{scan.missing_uploads} image(s) have a file name but no URL in the export.")


def filtered_records(scan: ExportScan, store: EvaluationStore) -> list[ImageRecord]:
    """Render the filters and return the records that pass them."""
    labels = {r.question_name: r.question_label for r in scan.records}
    cols = st.columns([3, 1, 2])
    questions = cols[0].multiselect(
        "Questions",
        options=list(labels),
        format_func=lambda name: f"{labels[name]}  ({name})",
        placeholder="All image questions",
        key="filter_questions",
    )
    status = cols[1].selectbox("Status", STATUS_FILTERS, key="filter_status")
    people = sorted({r.submitted_by for r in scan.records if r.submitted_by})
    submitters = cols[2].multiselect(
        "Submitted by", people, placeholder="Everyone", key="filter_submitters"
    )
    return [
        r
        for r in scan.records
        if (not questions or r.question_name in questions)
        and (status == "All" or status_of(r, store) == status)
        and (not submitters or r.submitted_by in submitters)
    ]


def navigation(records: list[ImageRecord], store: EvaluationStore) -> int:
    """Render navigation controls and return the current position in ``records``."""
    state = st.session_state
    target = state.pop("target_key", None)
    keys = [r.key for r in records]
    if target in keys:
        state.pos = keys.index(target)
    state.pos = min(max(state.get("pos", 0), 0), len(records) - 1)

    cols = st.columns([1, 1, 2, 1, 1])
    if cols[0].button("⏮ First", width="stretch"):
        state.pos = 0
    if cols[1].button("◀ Previous", width="stretch"):
        state.pos = max(state.pos - 1, 0)
    if cols[3].button("Next ▶", width="stretch"):
        state.pos = min(state.pos + 1, len(records) - 1)
    if cols[4].button("Next pending ⏭", width="stretch"):
        pending = [i for i, r in enumerate(records) if store.get(r.key) is None and i != state.pos]
        after = [i for i in pending if i > state.pos] or pending
        if after:
            state.pos = after[0]
        else:
            st.toast("No pending images left in this selection.")
    state.pos = (
        cols[2].number_input(
            "Image #",
            min_value=1,
            max_value=len(records),
            value=state.pos + 1,
            label_visibility="collapsed",
        )
        - 1
    )
    return state.pos


def render_image(record: ImageRecord, client: KoboImageClient, upcoming: list[str]) -> None:
    """Download and display the image, then prefetch the next ones."""
    try:
        with st.spinner("Downloading image from Kobo..."):
            data = client.fetch(record.image_url)
        st.image(data, width="stretch")
    except ImageFetchError as exc:
        if exc.reason is FetchFailure.ACCESS_EXPIRED:
            sign_out(EXPIRED_MESSAGE)
            st.rerun()
        elif exc.reason is FetchFailure.NOT_SIGNED_IN:
            st.info(str(exc))
        else:
            st.error(str(exc))
            if exc.reason is FetchFailure.UNREACHABLE and st.button(
                "Retry", key=f"retry_{record.key}"
            ):
                st.rerun()
    st.markdown(f"[Open original attachment in Kobo]({record.image_url})")
    executor = get_executor()
    for url in upcoming:
        if not client.is_cached(url):
            executor.submit(_prefetch, client, url)


def render_details(record: ImageRecord) -> None:
    """Show where the image comes from (form, data file, submission, question)."""
    st.subheader(record.question_label)
    rows = {
        "Question name": record.question_name,
        "Question group": record.question_group or "-",
        "Data sheet / row": f"{record.sheet} / row {record.excel_row}",
        "Repeat index": record.row_index or "-",
        "Submission ID": record.submission_id,
        "Submitted by": record.submitted_by or "-",
        "Submission time": record.submission_time or "-",
        "Image file": record.image_file_name or "-",
    }
    st.markdown("\n".join(f"- **{k}:** {v}" for k, v in rows.items()))
    if not record.mapped_to_form:
        st.caption("⚠️ This column was not found in the form; the export header is shown.")
    with st.expander("All data of this row"):
        st.json(record.context, expanded=False)


def reason_key(name: str, record_key: str) -> str:
    """Session-state key of the checkbox of reason ``name`` for one image."""
    return f"reason_{reason_widget_id(name)}_{record_key}"


def _add_reason_callback(catalogue: ReasonCatalogue, record_key: str) -> None:
    """Add the typed reason and tick it, keeping everything else entered in the form."""
    input_key = f"new_reason_{record_key}"
    try:
        name = catalogue.add(st.session_state.get(input_key, ""))
    except ReasonError as exc:
        st.session_state[REASON_ERROR_KEY] = exc.message
        return
    except OSError as exc:
        st.session_state[REASON_ERROR_KEY] = f"Could not save the new reason: {exc}"
        return
    st.session_state[reason_key(name, record_key)] = True
    st.session_state[input_key] = ""
    notice = f"Added reason '{name}'."
    if catalogue.backup_path is not None:
        notice += f" The unreadable file was kept as {catalogue.backup_path.name}."
    st.session_state[REASON_NOTICE_KEY] = notice


def _reason_checkbox(name: str, record_key: str, ticked: bool) -> bool:
    key = reason_key(name, record_key)
    if key in st.session_state:
        return st.checkbox(name, key=key)
    return st.checkbox(name, value=ticked, key=key)


def render_evaluation_form(
    record: ImageRecord,
    store: EvaluationStore,
    evaluator: str,
    next_key: str | None,
    catalogue: ReasonCatalogue,
) -> None:
    """Render the valid / invalid form for the current image and persist the answer."""
    current = store.get(record.key)
    saved = {reason_widget_id(name) for name in current.reasons} if current else set()
    if notice := st.session_state.pop(REASON_NOTICE_KEY, None):
        st.toast(notice)
    with st.form(key=f"eval_{record.key}", border=True):
        st.markdown("**Evaluation**")
        verdict = st.radio(
            "Is the image valid?",
            [v.value for v in Verdict],
            index=list(Verdict).index(current.verdict) if current else None,
            horizontal=True,
            key=f"verdict_{record.key}",
        )
        st.caption("If invalid, select at least one reason:")
        selected = [
            name
            for name in catalogue.offered_names(current.reasons if current else ())
            if _reason_checkbox(name, record.key, reason_widget_id(name) in saved)
        ]
        st.text_input(
            "New reason",
            max_chars=60,
            key=f"new_reason_{record.key}",
            placeholder="e.g. Finger over the lens",
            help="Add a reason that is not in the list; it stays available for every form.",
        )
        comments = st.text_area(
            "Additional comments",
            value=current.comments if current else "",
            height=100,
            key=f"comments_{record.key}",
        )
        cols = st.columns(3)
        cols[0].form_submit_button(
            "➕ Add reason",  # noqa: RUF001 - emoji icon, like the other buttons
            width="stretch",
            on_click=_add_reason_callback,
            args=(catalogue, record.key),
        )
        save = cols[1].form_submit_button("💾 Save", width="stretch")
        save_next = cols[2].form_submit_button("💾 Save & next", type="primary", width="stretch")
    if error := st.session_state.pop(REASON_ERROR_KEY, None):
        st.error(error)

    if save or save_next:
        if verdict is None:
            st.error("Select whether the image is valid or invalid.")
            return
        if verdict == Verdict.INVALID.value and not selected:
            st.error("Select at least one reason for an invalid image.")
            return
        if not evaluator.strip():
            st.warning("Tip: type your name in the sidebar so it is recorded in the report.")
        store.put(
            Evaluation(
                record_key=record.key,
                verdict=Verdict(verdict),
                reasons=selected if verdict == Verdict.INVALID.value else [],
                comments=comments,
                evaluator=evaluator.strip(),
            )
        )
        st.session_state.target_key = next_key if save_next and next_key else record.key
        st.rerun()

    if current:
        st.caption(
            f"Saved as **{current.verdict.value}** by {current.evaluator or 'unknown'} "
            f"at {current.evaluated_at} UTC."
        )
        if st.button("🗑️ Clear this evaluation", key=f"clear_{record.key}"):
            store.remove(record.key)
            st.session_state.target_key = record.key
            st.rerun()


def _forget_reason_widgets(name: str) -> None:
    """Drop the per-image checkbox states of a reason (after it was renamed)."""
    prefix = f"reason_{reason_widget_id(name)}_"
    for key in [k for k in st.session_state if str(k).startswith(prefix)]:
        del st.session_state[key]


def _rename_reason_callback(catalogue: ReasonCatalogue, old: str) -> None:
    old_id = reason_widget_id(old)
    try:
        new = catalogue.rename(old, st.session_state.get(f"rename_input_{old_id}", ""))
        files = rename_reason_in_stores(EVALUATIONS_DIR, old, new)
    except ReasonError as exc:
        st.session_state[MANAGE_ERROR_KEY] = exc.message
        return
    except OSError as exc:
        st.session_state[MANAGE_ERROR_KEY] = f"Could not rename the reason: {exc}"
        return
    if reason_widget_id(new) != old_id:
        _forget_reason_widgets(old)
        st.session_state.pop(f"rename_input_{old_id}", None)
    st.session_state[MANAGE_MESSAGE_KEY] = (
        f"Renamed '{old}' to '{new}' in {files} saved evaluation file(s)."
    )


def _hide_reason_callback(catalogue: ReasonCatalogue, name: str, hidden: bool) -> None:
    try:
        catalogue.set_hidden(name, hidden)
    except (ReasonError, OSError) as exc:
        st.session_state[MANAGE_ERROR_KEY] = getattr(exc, "message", str(exc))
        return
    state = "hidden" if hidden else "restored"
    st.session_state[MANAGE_MESSAGE_KEY] = f"Reason '{name}' {state}."


def render_manage_reasons(catalogue: ReasonCatalogue) -> None:
    """Sidebar expander to rename, hide and restore custom reasons (defaults are fixed)."""
    with st.sidebar.expander("Manage invalid reasons"):
        if message := st.session_state.pop(MANAGE_MESSAGE_KEY, None):
            st.success(message)
        if error := st.session_state.pop(MANAGE_ERROR_KEY, None):
            st.error(error)
        for name in catalogue.all_names():
            if catalogue.is_default(name):
                st.caption(f"{name} · default")
        custom = catalogue.custom()
        if not custom:
            st.caption("No custom reasons yet: add one from the evaluation form.")
        for reason in custom:
            reason_id = reason_widget_id(reason.name)
            label = f"{reason.name} (hidden)" if reason.hidden else reason.name
            st.markdown(f"**{label}**")
            input_key = f"rename_input_{reason_id}"
            if input_key not in st.session_state:
                st.session_state[input_key] = reason.name
            st.text_input("New name", key=input_key, max_chars=60, label_visibility="collapsed")
            cols = st.columns(2)
            cols[0].button(
                "Rename",
                key=f"rename_{reason_id}",
                on_click=_rename_reason_callback,
                args=(catalogue, reason.name),
                width="stretch",
            )
            cols[1].button(
                "Restore" if reason.hidden else "Hide",
                key=f"hide_{reason_id}",
                on_click=_hide_reason_callback,
                args=(catalogue, reason.name, not reason.hidden),
                width="stretch",
            )


def _report_dir_default() -> str:
    return str(Path(os.path.expanduser(os.getenv("REPORTS_DIR", "exports"))).resolve())


def _export_block(
    form: KoboForm,
    scan: ExportScan,
    store: EvaluationStore,
    evaluator: str,
    catalogue: ReasonCatalogue,
) -> None:
    """Save the Excel report directly into a local folder (no browser download)."""
    if "report_dir" not in st.session_state:
        st.session_state["report_dir"] = _report_dir_default()
    st.text_input("Save to folder", key="report_dir")
    include_pending = st.checkbox("Include images not evaluated yet", value=True)
    if st.button("💾 Export report", key="export_report", width="stretch"):
        st.session_state.pop("last_report_path", None)
        st.session_state.pop("last_report_error", None)
        with st.spinner("Saving the report…"):
            content = build_report(
                scan.records,
                store.evaluations,
                evaluator=evaluator,
                include_pending=include_pending,
                reasons=report_reasons(catalogue, store.evaluations.values()),
            )
            try:
                path = save_report(content, st.session_state["report_dir"], form.file_name)
            except ReportSaveError as exc:
                st.session_state["last_report_error"] = str(exc)
            else:
                st.session_state["last_report_path"] = str(path)
    if st.session_state.get("last_report_path"):
        st.success(f"Report saved to {st.session_state['last_report_path']}")
    if st.session_state.get("last_report_error"):
        st.error(st.session_state["last_report_error"])


def _render_import_summary(result: ImportResult) -> None:
    st.success(
        f"Restored {result.restored} evaluations from {result.report_name} "
        f"({result.added} added, {result.updated} updated, {result.unchanged} unchanged)."
    )
    if result.form_mismatch:
        st.warning(
            f"This report was created for form '{result.report_form_file}' and data "
            f"'{result.report_data_file}'. Only matching images were restored."
        )
    if result.not_matched:
        st.warning(f"{result.not_matched} evaluated rows did not match any image in this export.")
    if result.new_reasons:
        st.info(f"Added invalid reasons: {', '.join(result.new_reasons)}.")
    if result.reasons_error:
        st.warning(result.reasons_error)
    if result.rejected:
        with st.expander(f"{len(result.rejected)} rows were rejected"):
            st.markdown("\n".join(f"- Row {r.row_number}: {r.reason}" for r in result.rejected))
    if result.complete:
        st.success("All images in this export are evaluated.")


def _import_block(scan: ExportScan, store: EvaluationStore, catalogue: ReasonCatalogue) -> None:
    """Restore evaluations from a previously exported report and jump to the next image."""
    st.markdown("**Resume from a previous report**")
    uploaded = st.file_uploader("Previous report (.xlsx)", type=["xlsx"], key="import_report_file")
    if (
        st.button(
            "⤴ Import report", key="import_report", width="stretch", disabled=uploaded is None
        )
        and uploaded is not None
    ):
        content = uploaded.getvalue()
        fingerprint = f"{uploaded.name}:{hashlib.sha1(content).hexdigest()}"
        if st.session_state.get("imported_fingerprint") == fingerprint:
            st.info("This report was already imported.")
        else:
            try:
                result = import_report(
                    io.BytesIO(content), uploaded.name, scan.records, store, catalogue
                )
            except ReportImportError as exc:
                st.session_state.pop("import_result", None)
                st.error(exc.message)
            else:
                st.session_state["import_result"] = result
                st.session_state["imported_fingerprint"] = fingerprint
                st.session_state["filter_questions"] = []
                st.session_state["filter_status"] = "All"
                st.session_state["filter_submitters"] = []
                if result.resume_key is not None:
                    st.session_state.target_key = result.resume_key
                st.rerun()  # redraw counters and filters with the restored evaluations
    result = st.session_state.get("import_result")
    if result is not None:
        _render_import_summary(result)


def render_report_section(
    form: KoboForm,
    scan: ExportScan,
    store: EvaluationStore,
    evaluator: str,
    catalogue: ReasonCatalogue,
) -> None:
    """Sidebar section "4. Report": local export and resume from a previous report."""
    with st.sidebar:
        st.header("4. Report")
        _export_block(form, scan, store, evaluator, catalogue)
        st.divider()
        _import_block(scan, store, catalogue)
        st.caption(f"Evaluations autosave to `{store.path}`.")


def main() -> None:
    """Application entry point."""
    st.set_page_config(page_title="Kobo Image Evaluator", page_icon="🖼️", layout="wide")
    st.title("🖼️ Kobo Image Evaluator")
    form, scan, evaluator = sidebar()
    st.sidebar.caption(f"v{__version__}")

    if form is None or scan is None:
        st.info(
            "Select (or upload) a Kobo **form** (XLSForm `.xlsx`) and the **data export** "
            "downloaded from Kobo (`.xlsx`) in the sidebar to start."
        )
        return
    if not form.image_questions:
        st.warning(f"The form '{form.file_name}' has no image questions.")
    if not scan.records:
        st.warning("No image links were found in this data export.")
        return

    store = EvaluationStore(EVALUATIONS_DIR, form.file_name, scan.records[0].data_file)
    catalogue = ReasonCatalogue(catalogue_path(EVALUATIONS_DIR))
    catalogue.custom()  # read once so an unreadable file is reported
    if catalogue.load_error and not st.session_state.get(REASON_WARNED_KEY):
        st.session_state[REASON_WARNED_KEY] = True
        st.warning(catalogue.load_error)
    st.caption(
        f"**Form:** {form.title} (`{form.file_name}`) · **Data:** `{scan.records[0].data_file}`"
    )
    render_summary(form, scan, store)
    render_report_section(form, scan, store, evaluator, catalogue)
    render_manage_reasons(catalogue)
    st.divider()

    records = filtered_records(scan, store)
    if not records:
        st.info("No images match the current filters.")
        return
    pos = navigation(records, store)
    record = records[pos]
    st.caption(f"Image {pos + 1} of {len(records)} in the current selection")

    client = image_client()
    upcoming = [r.image_url for r in records[pos + 1 : pos + 1 + PREFETCH_AHEAD]]
    left, right = st.columns([3, 2])
    with left:
        render_image(record, client, upcoming)
    with right:
        render_details(record)
        next_key = records[pos + 1].key if pos + 1 < len(records) else None
        render_evaluation_form(record, store, evaluator, next_key, catalogue)


if __name__ == "__main__":
    main()
