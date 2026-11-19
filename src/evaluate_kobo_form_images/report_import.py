"""Import a previously exported evaluation report to resume (and merge) evaluation work.

The input is the Excel file written by :func:`evaluate_kobo_form_images.report.build_report`
(see ``specs/002-report-export-resume/contracts/report-format.md``). Rows are matched to the
images of the current export by ``Image key``, falling back to ``(Image URL, Question name)``,
validated against the evaluation vocabulary and merged into the autosave store. Reasons that
are not known yet (custom reasons of another installation) are accepted when their names are
valid and registered in the custom reason catalogue.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO

from openpyxl import load_workbook

from evaluate_kobo_form_images.evaluation import (
    Evaluation,
    EvaluationStore,
    Verdict,
    parse_timestamp,
)
from evaluate_kobo_form_images.kobo_export import ImageRecord
from evaluate_kobo_form_images.reasons import (
    DEFAULT_REASONS,
    ReasonCatalogue,
    ReasonError,
    clean_reason_name,
    normalize_reason,
)
from evaluate_kobo_form_images.report import (
    EVALUATIONS_SHEET,
    METADATA_SHEET,
    PENDING,
    REASON_COLUMN_PREFIX,
)

REQUIRED_COLUMNS: tuple[str, ...] = (
    "Image key",
    "Image URL",
    "Question name",
    "Evaluation status",
    "Comments",
    "Evaluator",
    "Evaluated at (UTC)",
)
REASONS_TEXT_COLUMN = "Invalid reasons"
NOT_A_REPORT = "This file is not an evaluation report exported by this app."


class ReportImportError(Exception):
    """The whole file was rejected; nothing was imported."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class RejectedRow:
    """A report row that could not be imported, with the reason."""

    row_number: int
    reason: str


@dataclass(frozen=True)
class _ParsedRow:
    row_number: int
    image_key: str
    image_url: str
    question_name: str
    evaluation: Evaluation


@dataclass
class ParsedReport:
    """Validated content of a report file."""

    form_file: str
    data_file: str
    rows: list[_ParsedRow] = field(default_factory=list)
    rejected: list[RejectedRow] = field(default_factory=list)


@dataclass
class ImportResult:
    """Summary of an import (see data-model.md)."""

    report_name: str
    report_form_file: str
    report_data_file: str
    form_mismatch: bool
    added: int
    updated: int
    unchanged: int
    not_matched: int
    rejected: list[RejectedRow]
    resume_key: str | None
    complete: bool
    new_reasons: list[str] = field(default_factory=list)
    reasons_error: str | None = None

    @property
    def restored(self) -> int:
        """Evaluations that changed the store (added + updated)."""
        return self.added + self.updated


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value).strip()


def _metadata(workbook: Any) -> dict[str, str]:
    if METADATA_SHEET not in workbook.sheetnames:
        return {}
    values: dict[str, str] = {}
    for row in workbook[METADATA_SHEET].iter_rows(min_row=2, values_only=True):
        if row and row[0] is not None:
            values[_text(row[0])] = _text(row[1] if len(row) > 1 else None)
    return values


def _parse_row(
    row_number: int, row: dict[str, str], reason_columns: list[str], known: dict[str, str]
) -> _ParsedRow | RejectedRow | None:
    status = row.get("Evaluation status", "")
    if status in ("", PENDING):
        return None
    if status not in (Verdict.VALID.value, Verdict.INVALID.value):
        return RejectedRow(row_number, f"Unknown status '{status}'")
    names = [part.strip() for part in row.get(REASONS_TEXT_COLUMN, "").split(";")]
    names += [
        column[len(REASON_COLUMN_PREFIX) :]
        for column in reason_columns
        if row.get(column, "").casefold() == "yes"
    ]
    reasons: list[str] = []
    seen: set[str] = set()
    for name in names:
        if not name:
            continue
        key = normalize_reason(name)
        if key in known:
            canonical = known[key]
        else:
            try:
                canonical = clean_reason_name(name)
            except ReasonError:
                return RejectedRow(row_number, f"Invalid reason name '{name}'")
        if key not in seen:
            seen.add(key)
            reasons.append(canonical)
    if status == Verdict.INVALID.value and not reasons:
        return RejectedRow(row_number, "Invalid without reasons")
    evaluated_at = row.get("Evaluated at (UTC)", "")
    try:
        parse_timestamp(evaluated_at)
    except ValueError:
        return RejectedRow(row_number, f"Invalid evaluation date '{evaluated_at}'")
    evaluation = Evaluation(
        record_key=row.get("Image key", ""),
        verdict=Verdict(status),
        reasons=reasons if status == Verdict.INVALID.value else [],
        comments=row.get("Comments", ""),
        evaluator=row.get("Evaluator", ""),
        evaluated_at=evaluated_at,
    )
    return _ParsedRow(
        row_number=row_number,
        image_key=row.get("Image key", ""),
        image_url=row.get("Image URL", ""),
        question_name=row.get("Question name", ""),
        evaluation=evaluation,
    )


def read_report(
    source: str | Path | BinaryIO, file_name: str, catalogue: ReasonCatalogue | None = None
) -> ParsedReport:
    """Parse and validate a report.

    Reason names equal (ignoring case and spacing) to a known reason take its display name;
    other well-formed names are kept as they are.

    Raises:
        ReportImportError: when the file is not a report of this app or misses columns.
    """
    del file_name  # kept for API symmetry / messages
    try:
        workbook = load_workbook(source, read_only=True, data_only=True)
    except Exception:
        raise ReportImportError(NOT_A_REPORT) from None
    try:
        if EVALUATIONS_SHEET not in workbook.sheetnames:
            raise ReportImportError(NOT_A_REPORT)
        rows = workbook[EVALUATIONS_SHEET].iter_rows(values_only=True)
        header = [_text(value) for value in next(rows, ())]
        reason_columns = [h for h in header if h.startswith(REASON_COLUMN_PREFIX)]
        missing = [column for column in REQUIRED_COLUMNS if column not in header]
        if REASONS_TEXT_COLUMN not in header and not reason_columns:
            missing.append(REASONS_TEXT_COLUMN)
        if missing:
            raise ReportImportError(
                f"The report is missing required columns: {', '.join(missing)}."
            )
        known_names = catalogue.all_names() if catalogue is not None else DEFAULT_REASONS
        known = {normalize_reason(name): name for name in known_names}
        metadata = _metadata(workbook)
        parsed = ParsedReport(
            form_file=metadata.get("Form file", ""), data_file=metadata.get("Data file", "")
        )
        for row_number, values in enumerate(rows, start=2):
            row = {name: _text(value) for name, value in zip(header, values, strict=False) if name}
            if not parsed.form_file:
                parsed.form_file = row.get("Form file", "")
                parsed.data_file = row.get("Data file", "")
            outcome = _parse_row(row_number, row, reason_columns, known)
            if isinstance(outcome, RejectedRow):
                parsed.rejected.append(outcome)
            elif outcome is not None:
                parsed.rows.append(outcome)
    finally:
        workbook.close()
    return parsed


def resume_target(
    records: Sequence[ImageRecord], store: EvaluationStore, last_key: str | None
) -> str | None:
    """First pending record after ``last_key`` (export order), else first pending, else None."""
    start = 0
    if last_key is not None:
        for index, record in enumerate(records):
            if record.key == last_key:
                start = index + 1
                break
    ordered = list(records[start:]) + list(records[:start])
    return next((r.key for r in ordered if store.get(r.key) is None), None)


def import_report(
    source: str | Path | BinaryIO,
    file_name: str,
    records: Sequence[ImageRecord],
    store: EvaluationStore,
    catalogue: ReasonCatalogue | None = None,
) -> ImportResult:
    """Read a report, match its rows to ``records``, merge them into ``store`` and resume.

    Reasons used by matched rows and unknown to ``catalogue`` are added to it first; if that
    fails the evaluations are still merged and ``reasons_error`` explains why.

    Raises:
        ReportImportError: when the whole file is rejected (``store`` is left untouched).
    """
    parsed = read_report(source, file_name, catalogue)
    by_key = {record.key: record for record in records}
    by_url = {(record.image_url, record.question_name): record for record in records}
    matched: dict[str, Evaluation] = {}
    last_key: str | None = None
    not_matched = 0
    for row in parsed.rows:
        record = by_key.get(row.image_key) or by_url.get((row.image_url, row.question_name))
        if record is None:
            not_matched += 1
            continue
        evaluation = row.evaluation
        if evaluation.record_key != record.key:
            evaluation = Evaluation(
                record_key=record.key,
                verdict=evaluation.verdict,
                reasons=list(evaluation.reasons),
                comments=evaluation.comments,
                evaluator=evaluation.evaluator,
                evaluated_at=evaluation.evaluated_at,
            )
        matched[record.key] = evaluation
        last_key = record.key
    new_reasons: list[str] = []
    reasons_error: str | None = None
    if catalogue is not None:
        used = [reason for evaluation in matched.values() for reason in evaluation.reasons]
        try:
            new_reasons = catalogue.ensure(used)
        except (OSError, ReasonError) as exc:
            reasons_error = f"The new invalid reasons of this report could not be saved: {exc}"
    merge = store.merge(matched.values())
    first = records[0] if records else None
    mismatch = (
        bool(first)
        and bool(parsed.form_file or parsed.data_file)
        and (
            (parsed.form_file and parsed.form_file != first.form_file)
            or (parsed.data_file and parsed.data_file != first.data_file)
        )
    )
    resume_key = resume_target(records, store, last_key)
    return ImportResult(
        report_name=file_name,
        report_form_file=parsed.form_file,
        report_data_file=parsed.data_file,
        form_mismatch=bool(mismatch),
        added=merge.added,
        updated=merge.updated,
        unchanged=merge.unchanged,
        not_matched=not_matched,
        rejected=parsed.rejected,
        resume_key=resume_key,
        complete=resume_key is None,
        new_reasons=new_reasons,
        reasons_error=reasons_error,
    )
