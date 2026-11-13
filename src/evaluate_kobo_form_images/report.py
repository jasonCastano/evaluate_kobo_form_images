"""Build the Excel evaluation report."""

from __future__ import annotations

import io
import os
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from datetime import UTC, datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from evaluate_kobo_form_images import __version__
from evaluate_kobo_form_images.evaluation import Evaluation, InvalidReason, Verdict
from evaluate_kobo_form_images.kobo_export import ImageRecord

PENDING = "Pending"
EVALUATIONS_SHEET = "Evaluations"
METADATA_SHEET = "Metadata"
REASON_COLUMN_PREFIX = "Reason: "

EVALUATION_COLUMNS: list[str] = [
    "Form file",
    "Form title",
    "Data file",
    "Data sheet",
    "Data row (Excel)",
    "Submission ID",
    "Submission UUID",
    "Submission time",
    "Submitted by",
    "Kobo validation status",
    "Repeat index",
    "Parent table",
    "Parent index",
    "Question name",
    "Question label",
    "Question group",
    "Export column",
    "Image file name",
    "Image URL",
    "Image key",
    "Evaluation status",
    *(f"{REASON_COLUMN_PREFIX}{reason.value}" for reason in InvalidReason),
    "Invalid reasons",
    "Comments",
    "Evaluator",
    "Evaluated at (UTC)",
]

_HEADER_FONT = Font(bold=True, color="FFFFFF")
_HEADER_FILL = PatternFill("solid", fgColor="305496")
_STATUS_FILL = {
    Verdict.VALID.value: PatternFill("solid", fgColor="C6EFCE"),
    Verdict.INVALID.value: PatternFill("solid", fgColor="FFC7CE"),
    PENDING: PatternFill("solid", fgColor="FFEB9C"),
}


def evaluation_row(record: ImageRecord, evaluation: Evaluation | None) -> list[object]:
    """Return the report row for one image and its (optional) evaluation."""
    reasons = set(evaluation.reasons) if evaluation else set()
    return [
        record.form_file,
        record.form_title,
        record.data_file,
        record.sheet,
        record.excel_row,
        record.submission_id,
        record.submission_uuid,
        record.submission_time,
        record.submitted_by,
        record.validation_status,
        record.row_index,
        record.parent_table,
        record.parent_index,
        record.question_name,
        record.question_label,
        record.question_group,
        record.column_header,
        record.image_file_name,
        record.image_url,
        record.key,
        evaluation.verdict.value if evaluation else PENDING,
        *(("Yes" if reason in reasons else "") for reason in InvalidReason),
        "; ".join(reason.value for reason in evaluation.reasons) if evaluation else "",
        evaluation.comments if evaluation else "",
        evaluation.evaluator if evaluation else "",
        evaluation.evaluated_at if evaluation else "",
    ]


def _style_header(sheet: Worksheet, widths: Mapping[int, int] | None = None) -> None:
    for cell in sheet[1]:
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
    sheet.freeze_panes = "A2"
    for idx, width in (widths or {}).items():
        sheet.column_dimensions[get_column_letter(idx)].width = width


def build_report(
    records: Iterable[ImageRecord],
    evaluations: Mapping[str, Evaluation],
    *,
    evaluator: str = "",
    include_pending: bool = True,
) -> bytes:
    """Create the evaluation workbook and return it as ``.xlsx`` bytes.

    Sheets:
        * ``Evaluations``: one row per image with its source form, data file, sheet, row,
          submission, question and evaluation.
        * ``Summary by question``: counts of valid / invalid / pending images and reasons.
        * ``Metadata``: report provenance.
    """
    records = list(records)
    workbook = Workbook()
    sheet = workbook.active
    assert isinstance(sheet, Worksheet)
    sheet.title = EVALUATIONS_SHEET
    sheet.append(EVALUATION_COLUMNS)
    status_col = EVALUATION_COLUMNS.index("Evaluation status") + 1
    url_col = EVALUATION_COLUMNS.index("Image URL") + 1

    summary: dict[tuple[str, str], Counter[str]] = {}
    for record in records:
        evaluation = evaluations.get(record.key)
        counter = summary.setdefault((record.question_name, record.question_label), Counter())
        counter[evaluation.verdict.value if evaluation else PENDING] += 1
        for reason in evaluation.reasons if evaluation else []:
            counter[reason.value] += 1
        if evaluation is None and not include_pending:
            continue
        sheet.append(evaluation_row(record, evaluation))
        row = sheet.max_row
        status_cell = sheet.cell(row=row, column=status_col)
        status_cell.fill = _STATUS_FILL[str(status_cell.value)]
        url_cell = sheet.cell(row=row, column=url_col)
        url_cell.hyperlink = record.image_url
        url_cell.style = "Hyperlink"
    _style_header(sheet, {1: 30, 3: 40, 14: 28, 15: 45, 19: 60, 21: 18})
    sheet.auto_filter.ref = sheet.dimensions

    summary_sheet = workbook.create_sheet("Summary by question")
    summary_header = [
        "Question name",
        "Question label",
        "Total images",
        Verdict.VALID.value,
        Verdict.INVALID.value,
        PENDING,
        *(reason.value for reason in InvalidReason),
    ]
    summary_sheet.append(summary_header)
    for (name, label), counter in summary.items():
        total = counter[Verdict.VALID.value] + counter[Verdict.INVALID.value] + counter[PENDING]
        summary_sheet.append(
            [name, label, total, *(counter[column] for column in summary_header[3:])]
        )
    _style_header(summary_sheet, {1: 30, 2: 45})

    first = records[0] if records else None
    meta = workbook.create_sheet(METADATA_SHEET)
    meta.append(["Field", "Value"])
    for field_name, value in (
        ("Form file", first.form_file if first else ""),
        ("Form title", first.form_title if first else ""),
        ("Data file", first.data_file if first else ""),
        ("Images in data file", len(records)),
        ("Images evaluated", sum(1 for r in records if r.key in evaluations)),
        ("Evaluator", evaluator),
        ("Generated at (UTC)", datetime.now(UTC).isoformat(timespec="seconds")),
        ("Generated by", f"evaluate_kobo_form_images v{__version__}"),
    ):
        meta.append([field_name, value])
    _style_header(meta, {1: 25, 2: 70})

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


# --------------------------------------------------------------------------- local save
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")
_REASON_PERMISSION = "Permission denied (is the file or folder open in another program?)"
_REASON_FOLDER = "The folder path is not valid or the drive is not available"
_REASON_TIMEOUT = "Saving took too long — the folder may be on a slow or offline drive."


class ReportSaveError(Exception):
    """The report could not be written; ``reason`` is plain English for the evaluator."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"Could not save the report to {path}: {reason}")
        self.path = path
        self.reason = reason


def report_file_name(form_file: str, now: datetime) -> str:
    """Return ``image_evaluation__<form stem>__YYYYMMDD-HHMMSS.xlsx`` (filesystem-safe)."""
    stem = _UNSAFE.sub("_", Path(form_file).stem)
    return f"image_evaluation__{stem}__{now:%Y%m%d-%H%M%S}.xlsx"


def _write_atomic(tmp: Path, final: Path, content: bytes) -> None:
    tmp.write_bytes(content)
    os.replace(tmp, final)


def _free_path(folder: Path, name: str) -> Path:
    candidate = folder / name
    stem, suffix = candidate.stem, candidate.suffix
    counter = 2
    while candidate.exists():
        candidate = folder / f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate


def save_report(
    content: bytes,
    folder: str | Path,
    form_file: str,
    *,
    now: datetime | None = None,
    timeout: float = 30.0,
) -> Path:
    """Write the report into ``folder`` (created if needed) and return its absolute path.

    A new file is always created (``-2``, ``-3`` … suffixes); existing reports are never
    overwritten. The write is atomic (temporary file + rename) and bounded by ``timeout``.

    Raises:
        ReportSaveError: with a plain-English ``reason``.
    """
    target = Path(os.path.expanduser(str(folder))).resolve()
    try:
        target.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        raise ReportSaveError(target, _REASON_PERMISSION) from None
    except OSError as exc:
        raise ReportSaveError(target, f"{_REASON_FOLDER} ({exc.strerror or exc}).") from None
    final = _free_path(target, report_file_name(form_file, now or datetime.now()))
    tmp = final.with_name(f"{final.name}.tmp")
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        executor.submit(_write_atomic, tmp, final, content).result(timeout=timeout)
    except FutureTimeout:
        raise ReportSaveError(final, _REASON_TIMEOUT) from None
    except PermissionError:
        tmp.unlink(missing_ok=True)
        raise ReportSaveError(final, _REASON_PERMISSION) from None
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise ReportSaveError(final, f"The file system reported: {exc.strerror or exc}.") from None
    finally:
        executor.shutdown(wait=False)
    return final
