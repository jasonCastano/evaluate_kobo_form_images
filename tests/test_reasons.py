"""Tests for invalid-reason name rules and the persistent custom-reason catalogue."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluate_kobo_form_images.evaluation import Evaluation, Verdict
from evaluate_kobo_form_images.reasons import (
    DEFAULT_REASONS,
    MAX_REASON_LENGTH,
    ReasonCatalogue,
    ReasonError,
    catalogue_path,
    clean_reason_name,
    normalize_reason,
    reason_widget_id,
    rename_reason_in_stores,
    report_reasons,
)


@pytest.fixture
def path(tmp_path: Path) -> Path:
    return tmp_path / "custom_reasons.json"


# --------------------------------------------------------------------------- name rules
def test_normalize_reason_ignores_case_and_spacing() -> None:
    assert normalize_reason(" low  LIGHTING ") == "low lighting"


def test_clean_reason_name_trims_and_collapses_whitespace() -> None:
    assert clean_reason_name("  Finger   over the\tlens ") == "Finger over the lens"


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("", "Enter a reason name."),
        ("   ", "Enter a reason name."),
        ("x" * (MAX_REASON_LENGTH + 1), "Reason names can have at most 60 characters."),
        ("Blurry; dark", "Reason names cannot contain ';'."),
        ("Bad\x07name", "Reason names cannot contain control characters."),
    ],
)
def test_clean_reason_name_rejects_invalid_names(name: str, message: str) -> None:
    with pytest.raises(ReasonError) as error:
        clean_reason_name(name)
    assert error.value.message == message


def test_clean_reason_name_accepts_exactly_the_maximum_length() -> None:
    name = "x" * MAX_REASON_LENGTH
    assert clean_reason_name(name) == name


def test_reason_widget_id_is_stable_and_key_based() -> None:
    assert reason_widget_id("Low lighting") == reason_widget_id(" low  LIGHTING ")
    assert reason_widget_id("Low lighting") != reason_widget_id("Too bright / overexposed")
    assert len(reason_widget_id("Finger over the lens")) == 10


def test_catalogue_path_defaults_to_evaluations_dir_and_honours_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CUSTOM_REASONS_FILE", raising=False)
    assert catalogue_path(tmp_path) == tmp_path / "custom_reasons.json"
    monkeypatch.setenv("CUSTOM_REASONS_FILE", str(tmp_path / "other.json"))
    assert catalogue_path(tmp_path) == tmp_path / "other.json"


# --------------------------------------------------------------------------- catalogue core
def test_missing_file_means_only_default_reasons(path: Path) -> None:
    catalogue = ReasonCatalogue(path)

    assert catalogue.all_names() == list(DEFAULT_REASONS)
    assert catalogue.offered_names() == list(DEFAULT_REASONS)
    assert catalogue.load_error is None
    assert not path.exists()


def test_add_persists_reason_after_defaults(path: Path) -> None:
    # Act
    added = ReasonCatalogue(path).add("  Finger over the lens ")

    # Assert
    assert added == "Finger over the lens"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert payload["reasons"][0]["name"] == "Finger over the lens"
    assert payload["reasons"][0]["hidden"] is False
    assert payload["reasons"][0]["created_at"]
    assert ReasonCatalogue(path).all_names() == [*DEFAULT_REASONS, "Finger over the lens"]


def test_add_rejects_duplicate_of_default_ignoring_case_and_spacing(path: Path) -> None:
    with pytest.raises(ReasonError) as error:
        ReasonCatalogue(path).add(" low LIGHTING ")
    assert error.value.message == "'Low lighting' already exists."
    assert not path.exists()


def test_add_rejects_duplicate_of_custom_reason(path: Path) -> None:
    catalogue = ReasonCatalogue(path)
    catalogue.add("Finger over the lens")

    with pytest.raises(ReasonError, match="already exists"):
        catalogue.add("FINGER over the  lens")


def test_add_keeps_creation_order(path: Path) -> None:
    catalogue = ReasonCatalogue(path)
    for name in ("C reason", "A reason", "B reason"):
        catalogue.add(name)

    assert ReasonCatalogue(path).all_names()[len(DEFAULT_REASONS) :] == [
        "C reason",
        "A reason",
        "B reason",
    ]


def test_two_catalogues_on_the_same_file_keep_both_additions(path: Path) -> None:
    # Arrange: two browser tabs, each with its own catalogue object
    first, second = ReasonCatalogue(path), ReasonCatalogue(path)
    first.all_names()
    second.all_names()

    # Act
    first.add("Finger over the lens")
    second.add("Wrong plant part")

    # Assert
    assert ReasonCatalogue(path).all_names()[len(DEFAULT_REASONS) :] == [
        "Finger over the lens",
        "Wrong plant part",
    ]


def test_default_reasons_are_never_written_to_the_file(path: Path) -> None:
    ReasonCatalogue(path).add("Finger over the lens")

    names = [item["name"] for item in json.loads(path.read_text(encoding="utf-8"))["reasons"]]
    assert names == ["Finger over the lens"]


def test_canonical_and_is_default(path: Path) -> None:
    catalogue = ReasonCatalogue(path)
    catalogue.add("Finger over the lens")

    assert catalogue.canonical("low lighting") == "Low lighting"
    assert catalogue.canonical(" finger OVER the lens") == "Finger over the lens"
    assert catalogue.canonical("Unknown") is None
    assert catalogue.is_default("LOW lighting")
    assert not catalogue.is_default("Finger over the lens")


# --------------------------------------------------------------------------- unreadable file
def test_unreadable_file_is_reported_and_preserved_on_read(path: Path) -> None:
    path.write_text("{not json", encoding="utf-8")

    catalogue = ReasonCatalogue(path)

    assert catalogue.all_names() == list(DEFAULT_REASONS)
    assert catalogue.load_error is not None
    assert "custom reasons file" in catalogue.load_error
    assert path.read_text(encoding="utf-8") == "{not json"


def test_add_after_unreadable_file_keeps_a_backup(path: Path) -> None:
    # Arrange
    path.write_text("{not json", encoding="utf-8")
    catalogue = ReasonCatalogue(path)

    # Act
    catalogue.add("Finger over the lens")

    # Assert
    backups = list(path.parent.glob("custom_reasons.json.unreadable-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{not json"
    assert catalogue.backup_path == backups[0]
    assert ReasonCatalogue(path).all_names() == [*DEFAULT_REASONS, "Finger over the lens"]


def test_unknown_version_is_unreadable(path: Path) -> None:
    path.write_text(json.dumps({"version": 2, "reasons": []}), encoding="utf-8")

    catalogue = ReasonCatalogue(path)

    assert catalogue.all_names() == list(DEFAULT_REASONS)
    assert catalogue.load_error is not None and "version" in catalogue.load_error


def test_invalid_entries_are_skipped_and_reported(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "reasons": [
                    {"name": "Good one", "hidden": False, "created_at": ""},
                    {"name": "bad;name", "hidden": False, "created_at": ""},
                    {"name": "Low lighting", "hidden": False, "created_at": ""},
                ],
            }
        ),
        encoding="utf-8",
    )

    catalogue = ReasonCatalogue(path)

    assert catalogue.all_names() == [*DEFAULT_REASONS, "Good one"]
    assert catalogue.load_error is not None
    assert "bad;name" in catalogue.load_error


# --------------------------------------------------------------------------- report columns
def _invalid(*reasons: str) -> Evaluation:
    return Evaluation(record_key="k", verdict=Verdict.INVALID, reasons=list(reasons))


def test_report_reasons_without_catalogue_are_the_defaults() -> None:
    assert report_reasons(None, [_invalid("Low lighting")]) == list(DEFAULT_REASONS)


def test_report_reasons_order_visible_hidden_used_and_unknown(path: Path) -> None:
    # Arrange
    catalogue = ReasonCatalogue(path)
    for name in ("Visible one", "Hidden used", "Hidden unused", "Visible two"):
        catalogue.add(name)
    catalogue.set_hidden("Hidden used", True)
    catalogue.set_hidden("Hidden unused", True)
    evaluations = [_invalid("Unknown B", "Hidden used"), _invalid("unknown a", "Unknown B")]

    # Act
    names = report_reasons(catalogue, evaluations)

    # Assert
    assert names == [
        *DEFAULT_REASONS,
        "Visible one",
        "Visible two",
        "Hidden used",
        "Unknown B",
        "unknown a",
    ]


def test_ensure_adds_only_unknown_valid_names_once(path: Path) -> None:
    catalogue = ReasonCatalogue(path)
    catalogue.add("Existing")

    added = catalogue.ensure(["low lighting", "EXISTING", "New one", "new  ONE", "bad;name"])

    assert added == ["New one"]
    assert ReasonCatalogue(path).all_names() == [*DEFAULT_REASONS, "Existing", "New one"]


def test_ensure_without_new_names_does_not_write(path: Path) -> None:
    ReasonCatalogue(path).ensure(["Low lighting"])

    assert not path.exists()


# --------------------------------------------------------------------------- rename / hide
def test_rename_keeps_position_date_and_visibility(path: Path) -> None:
    # Arrange
    catalogue = ReasonCatalogue(path)
    catalogue.add("Fingr over lens")
    catalogue.add("Wrong plant part")
    catalogue.set_hidden("Fingr over lens", True)
    before = catalogue.custom()[0]

    # Act
    renamed = catalogue.rename("fingr over LENS", "Finger over the lens")

    # Assert
    after = ReasonCatalogue(path).custom()
    assert renamed == "Finger over the lens"
    assert [r.name for r in after] == ["Finger over the lens", "Wrong plant part"]
    assert after[0].created_at == before.created_at
    assert after[0].hidden is True


def test_rename_to_an_existing_name_is_refused(path: Path) -> None:
    catalogue = ReasonCatalogue(path)
    catalogue.add("A reason")
    catalogue.add("B reason")

    with pytest.raises(ReasonError, match="'B reason' already exists"):
        catalogue.rename("A reason", "b REASON")
    with pytest.raises(ReasonError, match="'Low lighting' already exists"):
        catalogue.rename("A reason", "Low lighting")


def test_case_only_rename_of_the_same_reason_is_allowed(path: Path) -> None:
    catalogue = ReasonCatalogue(path)
    catalogue.add("finger over the lens")

    assert catalogue.rename("finger over the lens", "Finger over the lens") == (
        "Finger over the lens"
    )


@pytest.mark.parametrize("action", ["rename", "hide"])
def test_default_reasons_cannot_be_changed(path: Path, action: str) -> None:
    catalogue = ReasonCatalogue(path)

    with pytest.raises(ReasonError) as error:
        if action == "rename":
            catalogue.rename("Low lighting", "Dark")
        else:
            catalogue.set_hidden("Low lighting", True)
    assert error.value.message == "Default reasons cannot be changed."


def test_hidden_reason_is_only_offered_when_already_selected(path: Path) -> None:
    # Arrange
    catalogue = ReasonCatalogue(path)
    catalogue.add("Finger over the lens")

    # Act / Assert
    catalogue.set_hidden("Finger over the lens", True)
    assert catalogue.offered_names() == list(DEFAULT_REASONS)
    assert catalogue.offered_names(["finger over the lens"]) == [
        *DEFAULT_REASONS,
        "Finger over the lens",
    ]
    assert "Finger over the lens" in catalogue.all_names()

    catalogue.set_hidden("Finger over the lens", False)
    assert catalogue.offered_names() == [*DEFAULT_REASONS, "Finger over the lens"]


def _store_file(directory: Path, name: str, reasons_per_item: list[list[str]]) -> Path:
    path = directory / name
    path.write_text(
        json.dumps(
            {
                "form_file": "f.xlsx",
                "data_file": "d.xlsx",
                "evaluations": [
                    {"record_key": str(i), "verdict": "Invalid", "reasons": reasons}
                    for i, reasons in enumerate(reasons_per_item)
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_rename_reason_in_stores_rewrites_only_files_that_use_it(tmp_path: Path) -> None:
    # Arrange
    using = _store_file(tmp_path, "a__b.json", [["fingr over lens", "Low lighting"], ["Other"]])
    unrelated = _store_file(tmp_path, "c__d.json", [["Low lighting"]])
    dedupe = _store_file(tmp_path, "e__f.json", [["Fingr over lens", "Finger over the lens"]])
    catalogue_file = tmp_path / "custom_reasons.json"
    catalogue_file.write_text('{"version": 1, "reasons": [{"name": "Fingr over lens"}]}')
    untouched = {p: p.read_bytes() for p in (unrelated, catalogue_file)}

    # Act
    count = rename_reason_in_stores(tmp_path, "Fingr over lens", "Finger over the lens")

    # Assert
    assert count == 2
    items = json.loads(using.read_text(encoding="utf-8"))["evaluations"]
    assert items[0]["reasons"] == ["Finger over the lens", "Low lighting"]
    assert items[1]["reasons"] == ["Other"]
    deduped = json.loads(dedupe.read_text(encoding="utf-8"))["evaluations"][0]["reasons"]
    assert deduped == ["Finger over the lens"]
    assert {p: p.read_bytes() for p in untouched} == untouched
