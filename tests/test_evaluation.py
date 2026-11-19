"""Tests for the evaluation model and its persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluate_kobo_form_images.evaluation import (
    Evaluation,
    EvaluationStore,
    InvalidReason,
    Verdict,
)


def test_invalid_evaluation_requires_a_reason() -> None:
    with pytest.raises(ValueError, match="reason"):
        Evaluation(record_key="k", verdict=Verdict.INVALID)


def test_valid_evaluation_drops_reasons() -> None:
    evaluation = Evaluation(record_key="k", verdict=Verdict.VALID, reasons=[InvalidReason.BLURRY])
    assert evaluation.reasons == []


def test_store_autosaves_and_resumes(tmp_path: Path) -> None:
    # Arrange
    store = EvaluationStore(tmp_path, "form.xlsx", "data export.xlsx")
    evaluation = Evaluation(
        record_key="abc",
        verdict=Verdict.INVALID,
        reasons=[InvalidReason.LOW_LIGHT, InvalidReason.BLURRY],
        comments="  shaded canopy  ",
        evaluator="Tester",
    )

    # Act
    store.put(evaluation)
    reloaded = EvaluationStore(tmp_path, "form.xlsx", "data export.xlsx").get("abc")

    # Assert
    assert reloaded is not None
    assert reloaded.verdict is Verdict.INVALID
    assert reloaded.reasons == [InvalidReason.LOW_LIGHT, InvalidReason.BLURRY]
    assert reloaded.comments == "shaded canopy"


def test_evaluation_accepts_custom_and_default_reasons_as_names() -> None:
    evaluation = Evaluation(
        record_key="k",
        verdict=Verdict.INVALID,
        reasons=[InvalidReason.BLURRY, "  Finger   over the lens "],
    )

    assert evaluation.reasons == ["Out of focus / blurry", "Finger over the lens"]
    stored = evaluation.to_dict()["reasons"]
    assert isinstance(stored, list)
    assert all(type(reason) is str for reason in stored)


def test_evaluation_drops_duplicate_reasons_by_key_keeping_the_first() -> None:
    evaluation = Evaluation(
        record_key="k",
        verdict=Verdict.INVALID,
        reasons=["Finger over the lens", "finger OVER the lens", "Low lighting"],
    )

    assert evaluation.reasons == ["Finger over the lens", "Low lighting"]


@pytest.mark.parametrize("name", ["", "a;b", "x" * 61])
def test_evaluation_rejects_malformed_reason_names(name: str) -> None:
    with pytest.raises(ValueError, match=r"[Rr]eason"):
        Evaluation(record_key="k", verdict=Verdict.INVALID, reasons=["Low lighting", name])


def test_store_loads_existing_autosave_with_default_reasons(tmp_path: Path) -> None:
    # Arrange: an autosave written before custom reasons existed
    (tmp_path / "form__data.json").write_text(
        json.dumps(
            {
                "form_file": "form.xlsx",
                "data_file": "data.xlsx",
                "evaluations": [
                    {
                        "record_key": "abc",
                        "verdict": "Invalid",
                        "reasons": ["Low lighting", "Invalid image content"],
                        "comments": "",
                        "evaluator": "",
                        "evaluated_at": "2026-11-12T10:00:00+00:00",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    # Act
    loaded = EvaluationStore(tmp_path, "form.xlsx", "data.xlsx").get("abc")

    # Assert
    assert loaded is not None
    assert loaded.reasons == [InvalidReason.LOW_LIGHT, InvalidReason.INVALID_CONTENT]


def test_store_remove_deletes_evaluation(tmp_path: Path) -> None:
    store = EvaluationStore(tmp_path, "form.xlsx", "data.xlsx")
    store.put(Evaluation(record_key="abc", verdict=Verdict.VALID))
    store.remove("abc")
    assert EvaluationStore(tmp_path, "form.xlsx", "data.xlsx").get("abc") is None


# --------------------------------------------------------------------------- merge
def _ev(key: str, when: str, verdict: Verdict = Verdict.VALID, comments: str = "") -> Evaluation:
    return Evaluation(record_key=key, verdict=verdict, comments=comments, evaluated_at=when)


def test_merge_adds_absent_and_keeps_identical(tmp_path: Path) -> None:
    store = EvaluationStore(tmp_path, "f.xlsx", "d.xlsx")
    store.put(_ev("a", "2026-11-12T10:00:00+00:00"))

    result = store.merge(
        [_ev("a", "2026-11-12T10:00:00+00:00"), _ev("b", "2026-11-12T11:00:00+00:00")]
    )

    assert (result.added, result.updated, result.unchanged) == (1, 0, 1)
    assert set(EvaluationStore(tmp_path, "f.xlsx", "d.xlsx").evaluations) == {"a", "b"}


def test_merge_replaces_only_when_strictly_newer(tmp_path: Path) -> None:
    store = EvaluationStore(tmp_path, "f.xlsx", "d.xlsx")
    store.put(_ev("a", "2026-11-12T10:00:00+00:00", comments="local"))

    older = store.merge([_ev("a", "2026-11-11T10:00:00+00:00", comments="old")])
    equal = store.merge([_ev("a", "2026-11-12T10:00:00+00:00", comments="same time")])
    newer = store.merge([_ev("a", "2026-11-13T10:00:00+00:00", comments="new")])

    assert (older.unchanged, equal.unchanged, newer.updated) == (1, 1, 1)
    current = store.get("a")
    assert current is not None and current.comments == "new"


def test_merge_never_deletes_and_skips_save_without_changes(tmp_path: Path) -> None:
    store = EvaluationStore(tmp_path, "f.xlsx", "d.xlsx")
    store.put(_ev("a", "2026-11-12T10:00:00+00:00"))
    store.put(_ev("b", "2026-11-12T10:00:00+00:00"))
    before = store.path.stat().st_mtime_ns

    result = store.merge([_ev("a", "2026-11-12T10:00:00+00:00")])

    assert result.unchanged == 1
    assert set(store.evaluations) == {"a", "b"}
    assert store.path.stat().st_mtime_ns == before
