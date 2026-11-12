"""Read KoboToolbox Excel data exports and extract one record per collected image.

Kobo exports store each repeat group in its own sheet. Every image question produces a
``<header>`` column with the file name and a ``<header>_URL`` column with the attachment
link, where ``<header>`` is either the question XML name (``"XML values and headers"``
export) or its label (``"Labels"`` export), optionally prefixed by its group path.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO

from openpyxl import load_workbook

from evaluate_kobo_form_images.xlsform import ImageQuestion, KoboForm, normalize_text

URL_SUFFIX = "_URL"

_SUBMISSION_ID_COLUMNS = ("_id", "_submission__id")
_SUBMISSION_UUID_COLUMNS = ("_uuid", "_submission__uuid")
_SUBMISSION_TIME_COLUMNS = ("_submission_time", "_submission__submission_time")
_SUBMITTED_BY_COLUMNS = ("_submitted_by", "_submission__submitted_by")
_VALIDATION_COLUMNS = ("_validation_status", "_submission__validation_status")


@dataclass(frozen=True)
class ImageRecord:
    """One image attachment found in a Kobo data export."""

    key: str
    form_file: str
    form_title: str
    data_file: str
    sheet: str
    excel_row: int
    submission_id: str
    submission_uuid: str
    submission_time: str
    submitted_by: str
    validation_status: str
    row_index: str
    parent_table: str
    parent_index: str
    question_name: str
    question_label: str
    question_group: str
    column_header: str
    image_file_name: str
    image_url: str
    mapped_to_form: bool
    context: dict[str, str] = field(default_factory=dict, compare=False, hash=False)


@dataclass
class ExportScan:
    """Result of scanning a Kobo data export against its form."""

    records: list[ImageRecord]
    unmapped_columns: list[str]
    missing_uploads: int
    sheets: list[str]

    def questions(self) -> list[str]:
        """Return the distinct question names in the order they first appear."""
        return list(dict.fromkeys(record.question_name for record in self.records))


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _first(row: dict[str, Any], columns: tuple[str, ...]) -> str:
    for column in columns:
        text = _to_text(row.get(column))
        if text:
            return text
    return ""


def record_key(submission_uuid: str, sheet: str, row_index: str, question: str, url: str) -> str:
    """Build a stable identifier for an image record (used to persist evaluations)."""
    raw = "|".join((submission_uuid, sheet, row_index, question, url))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


class _QuestionMatcher:
    """Resolve export column headers to form image questions.

    Duplicate labels are resolved in form order: Kobo writes the columns in the same order
    as the questions in the form, so the n-th column with a given label maps to the n-th
    question with that label.
    """

    def __init__(self, questions: list[ImageQuestion]) -> None:
        self._candidates: dict[str, list[ImageQuestion]] = defaultdict(list)
        for question in questions:
            keys = {normalize_text(question.name)}
            keys.update(normalize_text(label) for label in question.labels.values())
            for key in keys:
                if key:
                    self._candidates[key].append(question)

    def match(self, header_base: str, used: set[str]) -> ImageQuestion | None:
        """Return the first unused question whose name or label matches the header."""
        attempts = [header_base]
        if "/" in header_base:
            attempts.append(header_base.rsplit("/", 1)[-1])
        for attempt in attempts:
            candidates = self._candidates.get(normalize_text(attempt), [])
            for question in candidates:
                if question.name not in used:
                    return question
            if candidates:
                return candidates[0]
        return None


def scan_export(
    source: str | Path | BinaryIO,
    form: KoboForm,
    file_name: str | None = None,
) -> ExportScan:
    """Extract every image attachment of a Kobo data export.

    Args:
        source: Path or binary file-like object of the exported ``.xlsx``.
        form: The parsed XLSForm the data was collected with.
        file_name: Display name of the data file (defaults to the path name).
    """
    if file_name is None:
        file_name = Path(source).name if isinstance(source, str | Path) else "data.xlsx"
    matcher = _QuestionMatcher(form.image_questions)
    records: list[ImageRecord] = []
    unmapped: list[str] = []
    missing_uploads = 0

    workbook = load_workbook(source, read_only=True, data_only=True)
    try:
        sheets = list(workbook.sheetnames)
        for sheet in sheets:
            rows = workbook[sheet].iter_rows(values_only=True)
            header_row = next(rows, None)
            if not header_row:
                continue
            header = [_to_text(value) for value in header_row]
            url_columns: list[tuple[int, str, int | None, ImageQuestion | None]] = []
            used: set[str] = set()
            for idx, column in enumerate(header):
                if not column.endswith(URL_SUFFIX):
                    continue
                base = column[: -len(URL_SUFFIX)]
                if idx > 0 and header[idx - 1] == base:
                    file_idx: int | None = idx - 1
                else:
                    file_idx = header.index(base) if base in header else None
                question = matcher.match(base, used)
                if question is not None:
                    used.add(question.name)
                else:
                    unmapped.append(f"{sheet}: {column}")
                url_columns.append((idx, base, file_idx, question))
            if not url_columns:
                continue

            for excel_row, values in enumerate(rows, start=2):
                row = {name: value for name, value in zip(header, values, strict=False) if name}
                context = {
                    name: _to_text(value)
                    for name, value in row.items()
                    if _to_text(value) and not name.endswith(URL_SUFFIX)
                }
                submission_uuid = _first(row, _SUBMISSION_UUID_COLUMNS)
                row_index = _to_text(row.get("_index"))
                for url_idx, base, file_idx, question in url_columns:
                    url = _to_text(values[url_idx]) if url_idx < len(values) else ""
                    image_name = (
                        _to_text(values[file_idx])
                        if file_idx is not None and file_idx < len(values)
                        else ""
                    )
                    if not url:
                        if image_name:
                            missing_uploads += 1
                        continue
                    question_name = question.name if question else base
                    records.append(
                        ImageRecord(
                            key=record_key(submission_uuid, sheet, row_index, question_name, url),
                            form_file=form.file_name,
                            form_title=form.title,
                            data_file=file_name,
                            sheet=sheet,
                            excel_row=excel_row,
                            submission_id=_first(row, _SUBMISSION_ID_COLUMNS),
                            submission_uuid=submission_uuid,
                            submission_time=_first(row, _SUBMISSION_TIME_COLUMNS),
                            submitted_by=_first(row, _SUBMITTED_BY_COLUMNS),
                            validation_status=_first(row, _VALIDATION_COLUMNS),
                            row_index=row_index,
                            parent_table=_to_text(row.get("_parent_table_name")),
                            parent_index=_to_text(row.get("_parent_index")),
                            question_name=question_name,
                            question_label=question.label if question else base,
                            question_group=question.group if question else "",
                            column_header=base,
                            image_file_name=image_name,
                            image_url=url,
                            mapped_to_form=question is not None,
                            context=context,
                        )
                    )
    finally:
        workbook.close()

    return ExportScan(
        records=records,
        unmapped_columns=unmapped,
        missing_uploads=missing_uploads,
        sheets=sheets,
    )
