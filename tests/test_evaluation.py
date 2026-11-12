"""Tests for the evaluation model and its persistence."""

from __future__ import annotations

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


def test_store_remove_deletes_evaluation(tmp_path: Path) -> None:
    store = EvaluationStore(tmp_path, "form.xlsx", "data.xlsx")
    store.put(Evaluation(record_key="abc", verdict=Verdict.VALID))
    store.remove("abc")
    assert EvaluationStore(tmp_path, "form.xlsx", "data.xlsx").get("abc") is None
