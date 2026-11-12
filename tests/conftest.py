"""Shared fixtures: small synthetic XLSForm and Kobo export workbooks."""

from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

URL = "https://kf.kobotoolbox.org/api/v2/assets/aTEST/data/{sub}/attachments/att{n}/"

SURVEY = [
    ["type", "name", "label::English (en)", "label::French (fr)"],
    ["text", "farm", "Farm", "Ferme"],
    ["begin_repeat", "tree", "Tree", "Arbre"],
    ["begin_group", "photos", "Photos", "Photos"],
    ["image", "tree_photo_side_A", "Take the tree photo side A", "Photo de l'arbre face A"],
    ["image", "tree_photo_side_B", "Take the tree photo side B", "Photo de l'arbre face B"],
    ["end_group", "", "", ""],
    ["end_repeat", "", "", ""],
    ["image", "farm_photo", "Farm photo", "Photo de la ferme"],
]


def _save(workbook: Workbook, path: Path) -> Path:
    workbook.save(path)
    return path


@pytest.fixture
def form_path(tmp_path: Path) -> Path:
    """An XLSForm with one top-level image and two images inside a repeat group."""
    workbook = Workbook()
    survey = workbook.active
    assert survey is not None
    survey.title = "survey"
    for row in SURVEY:
        survey.append(row)
    settings = workbook.create_sheet("settings")
    settings.append(["form_title", "form_id", "version"])
    settings.append(["Test Yield Form", "test_yield", "v1"])
    workbook.create_sheet("choices").append(["list_name", "name", "label"])
    return _save(workbook, tmp_path / "test_form.xlsx")


@pytest.fixture
def export_path(tmp_path: Path) -> Path:
    """A Kobo 'XML values and headers' style export with a main sheet and a repeat sheet."""
    workbook = Workbook()
    main = workbook.active
    assert main is not None
    main.title = "Test Yield Form"
    main.append(["farm", "farm_photo", "farm_photo_URL", "_id", "_uuid", "_submitted_by", "_index"])
    main.append(["F01", "f.jpg", URL.format(sub=1, n=0), 1, "uuid-1", "alice", 1])
    main.append(["F02", "", "", 2, "uuid-2", "bob", 2])

    tree = workbook.create_sheet("tree")
    tree.append(
        [
            "tree_photo_side_A",
            "tree_photo_side_A_URL",
            "tree_photo_side_B",
            "tree_photo_side_B_URL",
            "_index",
            "_parent_table_name",
            "_parent_index",
            "_submission__id",
            "_submission__uuid",
        ]
    )
    tree.append(
        [
            "a1.jpg",
            URL.format(sub=1, n=1),
            "b1.jpg",
            URL.format(sub=1, n=2),
            1,
            "Test Yield Form",
            1,
            1,
            "uuid-1",
        ]
    )
    tree.append(
        ["a2.jpg", URL.format(sub=1, n=3), "b2.jpg", "", 2, "Test Yield Form", 1, 1, "uuid-1"]
    )
    return _save(workbook, tmp_path / "test_export.xlsx")


@pytest.fixture
def labels_export_path(tmp_path: Path) -> Path:
    """A Kobo 'Labels' style export where headers are question labels with group prefixes."""
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "tree"
    sheet.append(
        [
            "Photos/Take the tree photo side A",
            "Photos/Take the tree photo side A_URL",
            "Unknown photo_URL",
            "_index",
            "_submission__uuid",
        ]
    )
    sheet.append(["a.jpg", URL.format(sub=9, n=1), URL.format(sub=9, n=2), 1, "uuid-9"])
    return _save(workbook, tmp_path / "labels_export.xlsx")
