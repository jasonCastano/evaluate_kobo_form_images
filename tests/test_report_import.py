"""Tests for importing a previously exported report (resume + merge)."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from evaluate_kobo_form_images.evaluation import (
    Evaluation,
    EvaluationStore,
    InvalidReason,
    Verdict,
)
from evaluate_kobo_form_images.kobo_export import ImageRecord, scan_export
from evaluate_kobo_form_images.report import build_report
from evaluate_kobo_form_images.report_import import (
    ReportImportError,
    import_report,
    resume_target,
)
from evaluate_kobo_form_images.xlsform import parse_xlsform


@pytest.fixture
def records(form_path: Path, export_path: Path) -> list[ImageRecord]:
    return scan_export(export_path, parse_xlsform(form_path)).records


def _store(tmp_path: Path, name: str) -> EvaluationStore:
    return EvaluationStore(tmp_path / name, "test_form.xlsx", "test_export.xlsx")


def _evaluation(
    key: str,
    verdict: Verdict,
    when: str,
    reasons: list[InvalidReason] | None = None,
    comments: str = "",
    evaluator: str = "",
) -> Evaluation:
    return Evaluation(
        record_key=key,
        verdict=verdict,
        reasons=reasons or [],
        comments=comments,
        evaluator=evaluator,
        evaluated_at=when,
    )


def _report(records: list[ImageRecord], evaluations: dict[str, Evaluation]) -> bytes:
    return build_report(records, evaluations, evaluator="Tester", include_pending=True)


def _edit(content: bytes, edits: dict[tuple[int, str], object], drop: str | None = None) -> bytes:
    """Return a copy of a report with cells changed (row, header) or a column removed."""
    workbook = load_workbook(io.BytesIO(content))
    sheet = workbook["Evaluations"]
    header = [cell.value for cell in sheet[1]]
    for (row, column), value in edits.items():
        sheet.cell(row=row, column=header.index(column) + 1).value = value
    if drop:
        sheet.delete_cols(header.index(drop) + 1)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _two_evaluated(records: list[ImageRecord]) -> dict[str, Evaluation]:
    return {
        records[0].key: _evaluation(records[0].key, Verdict.VALID, "2026-11-12T10:00:00+00:00"),
        records[2].key: _evaluation(
            records[2].key,
            Verdict.INVALID,
            "2026-11-12T10:05:00+00:00",
            reasons=[InvalidReason.BLURRY, InvalidReason.LOW_LIGHT],
            comments="shaky",
            evaluator="Ana",
        ),
    }


# --------------------------------------------------------------------------- round trip
def test_round_trip_restores_and_persists(tmp_path: Path, records: list[ImageRecord]) -> None:
    # Arrange
    original = _two_evaluated(records)
    content = _report(records, original)
    store = _store(tmp_path, "b")

    # Act
    result = import_report(io.BytesIO(content), "report.xlsx", records, store)

    # Assert
    assert (result.added, result.updated, result.unchanged, result.not_matched) == (2, 0, 0, 0)
    assert result.rejected == []
    reloaded = _store(tmp_path, "b")
    for key, evaluation in original.items():
        restored = reloaded.get(key)
        assert restored is not None
        assert restored.to_dict() == evaluation.to_dict()


def test_reimporting_same_report_changes_nothing(
    tmp_path: Path, records: list[ImageRecord]
) -> None:
    content = _report(records, _two_evaluated(records))
    store = _store(tmp_path, "b")
    import_report(io.BytesIO(content), "report.xlsx", records, store)

    again = import_report(io.BytesIO(content), "report.xlsx", records, store)

    assert (again.added, again.updated, again.unchanged) == (0, 0, 2)


# --------------------------------------------------------------------------- matching / rejection
def test_fallback_match_and_not_matched_rows(tmp_path: Path, records: list[ImageRecord]) -> None:
    content = _report(records, _two_evaluated(records))
    # Row 2 = records[0]: wrong key but same URL+question -> fallback match.
    # Row 4 = records[2]: wrong key and URL -> not matched.
    content = _edit(
        content,
        {
            (2, "Image key"): "nope",
            (4, "Image key"): "nope2",
            (4, "Image URL"): "https://kf.kobotoolbox.org/elsewhere/",
        },
    )
    result = import_report(io.BytesIO(content), "r.xlsx", records, _store(tmp_path, "b"))
    assert result.added == 1
    assert result.not_matched == 1


@pytest.mark.parametrize(
    ("edits", "reason"),
    [
        ({(2, "Evaluation status"): "Maybe"}, "Unknown status 'Maybe'"),
        (
            {
                (4, "Invalid reasons"): "",
                **{(4, f"Reason: {r.value}"): None for r in InvalidReason},
            },
            "Invalid without reasons",
        ),
        ({(4, "Invalid reasons"): "Too dark"}, "Unknown reason 'Too dark'"),
        ({(2, "Evaluated at (UTC)"): "yesterday"}, "Invalid evaluation date 'yesterday'"),
    ],
)
def test_invalid_rows_are_rejected_with_reason(
    tmp_path: Path, records: list[ImageRecord], edits: dict[tuple[int, str], object], reason: str
) -> None:
    content = _edit(_report(records, _two_evaluated(records)), edits)
    result = import_report(io.BytesIO(content), "r.xlsx", records, _store(tmp_path, "b"))
    assert len(result.rejected) == 1
    assert result.rejected[0].reason == reason
    assert result.rejected[0].row_number in (2, 4)
    assert result.added == 1


def test_pending_rows_are_ignored(tmp_path: Path, records: list[ImageRecord]) -> None:
    content = _report(records, {})
    result = import_report(io.BytesIO(content), "r.xlsx", records, _store(tmp_path, "b"))
    assert (result.added, result.not_matched, result.rejected) == (0, 0, [])


# --------------------------------------------------------------------------- file rejection
def test_rejects_workbook_without_evaluations_sheet(
    tmp_path: Path, records: list[ImageRecord]
) -> None:
    buffer = io.BytesIO()
    Workbook().save(buffer)
    store = _store(tmp_path, "b")
    with pytest.raises(ReportImportError) as info:
        import_report(io.BytesIO(buffer.getvalue()), "x.xlsx", records, store)
    assert info.value.message == "This file is not an evaluation report exported by this app."
    assert store.evaluations == {}


def test_rejects_missing_columns(tmp_path: Path, records: list[ImageRecord]) -> None:
    content = _edit(_report(records, _two_evaluated(records)), {}, drop="Comments")
    with pytest.raises(ReportImportError) as info:
        import_report(io.BytesIO(content), "x.xlsx", records, _store(tmp_path, "b"))
    assert info.value.message == "The report is missing required columns: Comments."


def test_rejects_non_excel_bytes(tmp_path: Path, records: list[ImageRecord]) -> None:
    with pytest.raises(ReportImportError) as info:
        import_report(io.BytesIO(b"hello"), "x.xlsx", records, _store(tmp_path, "b"))
    assert info.value.message == "This file is not an evaluation report exported by this app."


# --------------------------------------------------------------------------- resume
def test_resume_target_rules(tmp_path: Path, records: list[ImageRecord]) -> None:
    store = _store(tmp_path, "a")
    keys = [r.key for r in records]
    store.put(_evaluation(keys[1], Verdict.VALID, "2026-11-12T10:00:00+00:00"))

    assert resume_target(records, store, keys[1]) == keys[2]
    store.put(_evaluation(keys[2], Verdict.VALID, "2026-11-12T10:00:00+00:00"))
    store.put(_evaluation(keys[3], Verdict.VALID, "2026-11-12T10:00:00+00:00"))
    assert resume_target(records, store, keys[3]) == keys[0]  # wraps
    store.put(_evaluation(keys[0], Verdict.VALID, "2026-11-12T10:00:00+00:00"))
    assert resume_target(records, store, keys[3]) is None


def test_import_sets_resume_key_and_form_mismatch(
    tmp_path: Path, records: list[ImageRecord]
) -> None:
    content = _report(records, _two_evaluated(records))
    result = import_report(io.BytesIO(content), "r.xlsx", records, _store(tmp_path, "b"))
    assert result.resume_key == records[3].key  # first pending after records[2]
    assert not result.complete
    assert not result.form_mismatch

    other = _edit(content, {(2, "Form file"): "other.xlsx"})
    workbook = load_workbook(io.BytesIO(other))
    workbook["Metadata"]["B2"] = "other.xlsx"
    buffer = io.BytesIO()
    workbook.save(buffer)
    mismatch = import_report(
        io.BytesIO(buffer.getvalue()), "r.xlsx", records, _store(tmp_path, "c")
    )
    assert mismatch.form_mismatch
    assert mismatch.report_form_file == "other.xlsx"


# --------------------------------------------------------------------------- merge (US3)
def test_merge_with_local_work_keeps_newest(tmp_path: Path, records: list[ImageRecord]) -> None:
    # Arrange: local A (old) and B (newer than report's B)
    a, b, c = records[0].key, records[1].key, records[2].key
    store = _store(tmp_path, "local")
    store.put(_evaluation(a, Verdict.VALID, "2026-11-10T08:00:00+00:00"))
    store.put(_evaluation(b, Verdict.VALID, "2026-11-12T08:00:00+00:00"))
    report_evals = {
        b: _evaluation(
            b, Verdict.INVALID, "2026-11-11T08:00:00+00:00", reasons=[InvalidReason.TOO_BRIGHT]
        ),
        c: _evaluation(c, Verdict.VALID, "2026-11-11T09:00:00+00:00"),
    }

    # Act
    result = import_report(io.BytesIO(_report(records, report_evals)), "r.xlsx", records, store)

    # Assert
    assert (result.added, result.updated, result.unchanged) == (1, 0, 1)
    assert store.get(a) is not None
    local_b = store.get(b)
    assert local_b is not None and local_b.verdict is Verdict.VALID
    assert store.get(c) is not None

    newer = {
        b: _evaluation(
            b, Verdict.INVALID, "2026-11-13T08:00:00+00:00", reasons=[InvalidReason.TOO_BRIGHT]
        )
    }
    result = import_report(io.BytesIO(_report(records, newer)), "r2.xlsx", records, store)
    assert result.updated == 1
    updated_b = store.get(b)
    assert updated_b is not None and updated_b.verdict is Verdict.INVALID
