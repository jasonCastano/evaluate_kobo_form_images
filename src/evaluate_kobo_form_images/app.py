"""Streamlit user interface to evaluate images collected with KoboToolbox forms.

Run with ``make run`` or ``uv run evaluate-kobo-images``.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from evaluate_kobo_form_images import __version__
from evaluate_kobo_form_images.evaluation import (
    Evaluation,
    EvaluationStore,
    InvalidReason,
    Verdict,
)
from evaluate_kobo_form_images.kobo_client import ImageFetchError, KoboImageClient
from evaluate_kobo_form_images.kobo_export import ExportScan, ImageRecord, scan_export
from evaluate_kobo_form_images.report import PENDING, build_report
from evaluate_kobo_form_images.xlsform import KoboForm, parse_xlsform

load_dotenv()

FORMS_DIR = Path(os.getenv("KOBO_FORMS_DIR", "forms"))
DATA_DIR = Path(os.getenv("KOBO_DATA_DIR", "data"))
EVALUATIONS_DIR = Path(os.getenv("EVALUATIONS_DIR", "evaluations"))
CACHE_DIR = Path(os.getenv("IMAGE_CACHE_DIR", ".cache/images"))
PREFETCH_AHEAD = 3
STATUS_FILTERS = ("All", PENDING, Verdict.VALID.value, Verdict.INVALID.value)


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
def get_client(token: str) -> KoboImageClient:
    """Return one image client per token."""
    return KoboImageClient(token=token, cache_dir=CACHE_DIR)


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


# --------------------------------------------------------------------------- sidebar
def sidebar() -> tuple[KoboForm | None, ExportScan | None, str, str]:
    """Render the sidebar inputs and return the loaded form, export, token and evaluator."""
    with st.sidebar:
        st.header("1. Kobo form")
        form_file = _pick_file("Form (XLSForm)", FORMS_DIR, "form")
        st.header("2. Collected data")
        data_file = _pick_file("Data export", DATA_DIR, "data")
        st.header("3. Session")
        evaluator = st.text_input("Evaluator name", key="evaluator")
        token = st.text_input(
            "Kobo API token",
            value=os.getenv("KOBO_API_TOKEN", ""),
            type="password",
            help="Needed to download images. Kobo > Account settings > Security > API key. "
            "It can also be set as KOBO_API_TOKEN in a local .env file.",
        )

    form = scan = None
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
    return form, scan, token, evaluator


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
    )
    status = cols[1].selectbox("Status", STATUS_FILTERS)
    people = sorted({r.submitted_by for r in scan.records if r.submitted_by})
    submitters = cols[2].multiselect("Submitted by", people, placeholder="Everyone")
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
        st.error(str(exc))
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


def render_evaluation_form(
    record: ImageRecord,
    store: EvaluationStore,
    evaluator: str,
    next_key: str | None,
) -> None:
    """Render the valid / invalid form for the current image and persist the answer."""
    current = store.get(record.key)
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
            reason
            for reason in InvalidReason
            if st.checkbox(
                reason.value,
                value=bool(current and reason in current.reasons),
                key=f"reason_{reason.name}_{record.key}",
            )
        ]
        comments = st.text_area(
            "Additional comments",
            value=current.comments if current else "",
            height=100,
            key=f"comments_{record.key}",
        )
        cols = st.columns(2)
        save = cols[0].form_submit_button("💾 Save", width="stretch")
        save_next = cols[1].form_submit_button("💾 Save & next", type="primary", width="stretch")

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
        st.session_state.pop("report", None)
        st.session_state.target_key = next_key if save_next and next_key else record.key
        st.rerun()

    if current:
        st.caption(
            f"Saved as **{current.verdict.value}** by {current.evaluator or 'unknown'} "
            f"at {current.evaluated_at} UTC."
        )
        if st.button("🗑️ Clear this evaluation", key=f"clear_{record.key}"):
            store.remove(record.key)
            st.session_state.pop("report", None)
            st.session_state.target_key = record.key
            st.rerun()


def render_export(form: KoboForm, scan: ExportScan, store: EvaluationStore, evaluator: str) -> None:
    """Sidebar section to build and download the Excel report."""
    with st.sidebar:
        st.header("4. Export")
        include_pending = st.checkbox("Include images not evaluated yet", value=True)
        if st.button("Build Excel report", width="stretch"):
            with st.spinner("Building the report..."):
                st.session_state.report = build_report(
                    scan.records,
                    store.evaluations,
                    evaluator=evaluator,
                    include_pending=include_pending,
                )
        if st.session_state.get("report"):
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            st.download_button(
                "⬇️ Download Excel",
                data=st.session_state.report,
                file_name=f"image_evaluation__{Path(form.file_name).stem}__{stamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )
        st.caption(f"Evaluations autosave to `{store.path}`.")


def main() -> None:
    """Application entry point."""
    st.set_page_config(page_title="Kobo Image Evaluator", page_icon="🖼️", layout="wide")
    st.title("🖼️ Kobo Image Evaluator")
    form, scan, token, evaluator = sidebar()
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
    st.caption(
        f"**Form:** {form.title} (`{form.file_name}`) · **Data:** `{scan.records[0].data_file}`"
    )
    render_summary(form, scan, store)
    render_export(form, scan, store, evaluator)
    st.divider()

    records = filtered_records(scan, store)
    if not records:
        st.info("No images match the current filters.")
        return
    pos = navigation(records, store)
    record = records[pos]
    st.caption(f"Image {pos + 1} of {len(records)} in the current selection")

    client = get_client(token)
    upcoming = [r.image_url for r in records[pos + 1 : pos + 1 + PREFETCH_AHEAD]]
    left, right = st.columns([3, 2])
    with left:
        render_image(record, client, upcoming)
    with right:
        render_details(record)
        next_key = records[pos + 1].key if pos + 1 < len(records) else None
        render_evaluation_form(record, store, evaluator, next_key)


if __name__ == "__main__":
    main()
