"""Tests for XLSForm parsing."""

from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

from evaluate_kobo_form_images.xlsform import normalize_text, parse_xlsform


def test_parse_xlsform_finds_image_questions_in_form_order(form_path: Path) -> None:
    # Act
    form = parse_xlsform(form_path)

    # Assert
    assert [q.name for q in form.image_questions] == [
        "tree_photo_side_A",
        "tree_photo_side_B",
        "farm_photo",
    ]
    assert form.title == "Test Yield Form"
    assert form.form_id == "test_yield"


def test_parse_xlsform_tracks_groups_repeats_and_english_label(form_path: Path) -> None:
    # Act
    question = parse_xlsform(form_path).by_name()["tree_photo_side_A"]

    # Assert
    assert question.group == "tree/photos"
    assert question.repeat_path == ("tree",)
    assert question.label == "Take the tree photo side A"


def test_parse_xlsform_rejects_workbook_without_survey(tmp_path: Path) -> None:
    # Arrange
    path = tmp_path / "not_a_form.xlsx"
    Workbook().save(path)

    # Act / Assert
    with pytest.raises(ValueError, match="survey"):
        parse_xlsform(path)


def test_normalize_text_ignores_markup_case_and_spacing() -> None:
    assert normalize_text("  Take the <b>Tree</b>   photo ") == "take the tree photo"
