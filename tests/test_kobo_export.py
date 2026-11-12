"""Tests for scanning Kobo data exports."""

from __future__ import annotations

from pathlib import Path

from evaluate_kobo_form_images.kobo_export import scan_export
from evaluate_kobo_form_images.xlsform import parse_xlsform


def test_scan_export_extracts_one_record_per_image_url(form_path: Path, export_path: Path) -> None:
    # Arrange
    form = parse_xlsform(form_path)

    # Act
    scan = scan_export(export_path, form)

    # Assert
    assert len(scan.records) == 4
    assert scan.missing_uploads == 1  # b2.jpg has a file name but no URL
    assert scan.unmapped_columns == []
    assert len({record.key for record in scan.records}) == 4


def test_scan_export_links_image_to_form_submission_and_row(
    form_path: Path, export_path: Path
) -> None:
    # Act
    records = scan_export(export_path, parse_xlsform(form_path)).records
    tree_a = next(r for r in records if r.image_file_name == "a2.jpg")

    # Assert
    assert tree_a.form_file == "test_form.xlsx"
    assert tree_a.data_file == "test_export.xlsx"
    assert tree_a.sheet == "tree"
    assert tree_a.excel_row == 3
    assert tree_a.submission_id == "1"
    assert tree_a.submission_uuid == "uuid-1"
    assert tree_a.row_index == "2"
    assert tree_a.question_name == "tree_photo_side_A"
    assert tree_a.question_group == "tree/photos"
    assert tree_a.mapped_to_form


def test_scan_export_matches_label_headers_and_reports_unknown_columns(
    form_path: Path, labels_export_path: Path
) -> None:
    # Act
    scan = scan_export(labels_export_path, parse_xlsform(form_path))

    # Assert
    names = [record.question_name for record in scan.records]
    assert names == ["tree_photo_side_A", "Unknown photo"]
    assert scan.records[0].image_file_name == "a.jpg"
    assert not scan.records[1].mapped_to_form
    assert scan.unmapped_columns == ["tree: Unknown photo_URL"]


def test_record_keys_are_stable_between_scans(form_path: Path, export_path: Path) -> None:
    form = parse_xlsform(form_path)
    first = [r.key for r in scan_export(export_path, form).records]
    second = [r.key for r in scan_export(export_path, form).records]
    assert first == second
