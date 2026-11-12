"""Build the Excel evaluation report."""

from __future__ import annotations

import io
from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from evaluate_kobo_form_images import __version__
from evaluate_kobo_form_images.evaluation import Evaluation, InvalidReason, Verdict
from evaluate_kobo_form_images.kobo_export import ImageRecord

PENDING = "Pending"

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
    *(f"Reason: {reason.value}" for reason in InvalidReason),
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
    sheet.title = "Evaluations"
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
    meta = workbook.create_sheet("Metadata")
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
