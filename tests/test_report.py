"""Tests for the Excel evaluation report."""

from __future__ import annotations

import io
from pathlib import Path

from openpyxl import load_workbook

from evaluate_kobo_form_images.evaluation import Evaluation, InvalidReason, Verdict
from evaluate_kobo_form_images.kobo_export import scan_export
from evaluate_kobo_form_images.reasons import DEFAULT_REASONS
from evaluate_kobo_form_images.report import EVALUATION_COLUMNS, build_report
from evaluate_kobo_form_images.xlsform import parse_xlsform


def _rows(content: bytes, sheet: str) -> list[dict[str, object]]:
    workbook = load_workbook(io.BytesIO(content))
    values = list(workbook[sheet].iter_rows(values_only=True))
    return [dict(zip(values[0], row, strict=True)) for row in values[1:]]


def test_report_links_evaluation_to_form_question_and_image(
    form_path: Path, export_path: Path
) -> None:
    # Arrange
    records = scan_export(export_path, parse_xlsform(form_path)).records
    target = records[1]
    evaluations = {
        target.key: Evaluation(
            record_key=target.key,
            verdict=Verdict.INVALID,
            reasons=[InvalidReason.TOO_BRIGHT],
            comments="sun glare",
            evaluator="Tester",
        )
    }

    # Act
    rows = _rows(build_report(records, evaluations, evaluator="Tester"), "Evaluations")

    # Assert
    assert list(rows[0]) == EVALUATION_COLUMNS
    assert len(rows) == len(records)
    row = next(r for r in rows if r["Image key"] == target.key)
    assert row["Form file"] == "test_form.xlsx"
    assert row["Data file"] == "test_export.xlsx"
    assert row["Question name"] == target.question_name
    assert row["Image URL"] == target.image_url
    assert row["Evaluation status"] == "Invalid"
    assert row[f"Reason: {InvalidReason.TOO_BRIGHT.value}"] == "Yes"
    assert row["Comments"] == "sun glare"
    assert sum(r["Evaluation status"] == "Pending" for r in rows) == len(records) - 1


def test_report_can_exclude_pending_and_summarizes_by_question(
    form_path: Path, export_path: Path
) -> None:
    # Arrange
    records = scan_export(export_path, parse_xlsform(form_path)).records
    evaluations = {records[0].key: Evaluation(record_key=records[0].key, verdict=Verdict.VALID)}

    # Act
    content = build_report(records, evaluations, include_pending=False)

    # Assert
    assert len(_rows(content, "Evaluations")) == 1
    summary = {r["Question name"]: r for r in _rows(content, "Summary by question")}
    assert summary[records[0].question_name]["Valid"] == 1
    assert sum(int(str(r["Total images"])) for r in summary.values()) == len(records)


def test_report_has_columns_and_counts_for_custom_reasons(
    form_path: Path, export_path: Path
) -> None:
    # Arrange
    records = scan_export(export_path, parse_xlsform(form_path)).records
    target = records[1]
    evaluations = {
        target.key: Evaluation(
            record_key=target.key,
            verdict=Verdict.INVALID,
            reasons=["Finger over the lens", InvalidReason.BLURRY],
        ),
        records[0].key: Evaluation(record_key=records[0].key, verdict=Verdict.VALID),
    }
    reasons = [*DEFAULT_REASONS, "Finger over the lens", "Valid"]

    # Act
    content = build_report(records, evaluations, reasons=reasons)

    # Assert
    rows = _rows(content, "Evaluations")
    header = list(rows[0])
    custom_column = header.index("Reason: Finger over the lens")
    assert header[custom_column - 1] == f"Reason: {DEFAULT_REASONS[-1]}"
    assert header[custom_column + 2] == "Invalid reasons"
    row = next(r for r in rows if r["Image key"] == target.key)
    assert row["Reason: Finger over the lens"] == "Yes"
    assert row["Invalid reasons"] == "Finger over the lens; Out of focus / blurry"
    assert all(not r["Reason: Finger over the lens"] for r in rows if r is not row)
    summary = {r["Question name"]: r for r in _rows(content, "Summary by question")}
    assert summary[target.question_name]["Finger over the lens"] == 1
    assert summary[records[0].question_name]["Valid"] == 1  # verdict count, not the reason
    assert summary[records[0].question_name]["Reason: Valid"] == 0  # no clash with verdicts
    assert sum(int(str(r["Valid"])) for r in summary.values()) == 1
