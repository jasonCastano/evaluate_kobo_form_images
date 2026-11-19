"""UI tests for custom invalid reasons (AppTest, no network, synthetic fixtures)."""

from __future__ import annotations

import io
import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from streamlit.testing.v1 import AppTest

from evaluate_kobo_form_images.kobo_client import KoboImageClient
from evaluate_kobo_form_images.reasons import DEFAULT_REASONS

APP = Path(__file__).resolve().parents[1] / "src" / "evaluate_kobo_form_images" / "app.py"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CUSTOM = "Finger over the lens"


def _jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), (0, 128, 0)).save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def app_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, form_path: Path, export_path: Path
) -> Path:
    """Isolated folders with the synthetic form/export; images are stubbed."""
    for name, source in (("forms", form_path), ("data", export_path)):
        folder = tmp_path / name
        folder.mkdir()
        shutil.copy(source, folder / source.name)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KOBO_FORMS_DIR", str(tmp_path / "forms"))
    monkeypatch.setenv("KOBO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("EVALUATIONS_DIR", str(tmp_path / "evaluations"))
    monkeypatch.setenv("CUSTOM_REASONS_FILE", str(tmp_path / "evaluations" / "custom_reasons.json"))
    monkeypatch.setenv("IMAGE_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("REPORTS_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("KOBO_API_TOKEN", "")
    monkeypatch.setattr(KoboImageClient, "fetch", lambda self, url: _jpeg())
    monkeypatch.setattr(KoboImageClient, "is_cached", lambda self, url: True)
    return tmp_path


def _open_app(form: str = "test_form.xlsx", data: str = "test_export.xlsx") -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    at.selectbox(key="form_choice").select(form).run()
    at.selectbox(key="data_choice").select(data).run()
    return at


def _main_checkboxes(at: AppTest) -> dict[str, bool]:
    return {str(c.label): bool(c.value) for c in at.main.checkbox}


def _texts(elements: Any) -> list[str]:
    return [str(e.value) for e in elements]


def _button(at: AppTest, label: str) -> Any:
    return next(b for b in at.button if label in str(b.label))


def _add_reason(at: AppTest, name: str) -> None:
    next(t for t in at.text_input if t.label == "New reason").input(name)
    _button(at, "Add reason").click().run()


def _autosave_reasons(app_env: Path) -> list[list[str]]:
    stores = list((app_env / "evaluations").glob("*__*.json"))
    if not stores:
        return []
    payload = json.loads(stores[0].read_text(encoding="utf-8"))
    return [item["reasons"] for item in payload["evaluations"]]


# --------------------------------------------------------------------------- US1
def test_default_reasons_are_listed(app_env: Path) -> None:
    at = _open_app()

    assert list(_main_checkboxes(at)) == list(DEFAULT_REASONS)


def test_add_reason_keeps_entered_values_and_ticks_it(app_env: Path) -> None:
    # Arrange
    at = _open_app()
    at.radio[0].set_value("Invalid")
    at.text_area[0].input("keep me")

    # Act
    _add_reason(at, CUSTOM)

    # Assert
    boxes = _main_checkboxes(at)
    assert list(boxes) == [*DEFAULT_REASONS, CUSTOM]
    assert boxes[CUSTOM] is True
    assert at.radio[0].value == "Invalid"
    assert at.text_area[0].value == "keep me"
    assert next(t for t in at.text_input if t.label == "New reason").value == ""
    assert _autosave_reasons(app_env) == []  # adding a reason does not save the evaluation
    assert not at.exception


def test_added_reason_is_saved_with_the_evaluation(app_env: Path) -> None:
    at = _open_app()
    at.radio[0].set_value("Invalid")
    _add_reason(at, CUSTOM)

    _button(at, "💾 Save").click().run()

    assert _autosave_reasons(app_env) == [[CUSTOM]]


@pytest.mark.parametrize(
    ("name", "message"),
    [(" low LIGHTING ", "'Low lighting' already exists."), ("", "Enter a reason name.")],
)
def test_add_reason_errors_add_nothing(app_env: Path, name: str, message: str) -> None:
    at = _open_app()

    _add_reason(at, name)

    assert message in _texts(at.main.error)
    assert list(_main_checkboxes(at)) == list(DEFAULT_REASONS)


# --------------------------------------------------------------------------- US2
def test_custom_reason_survives_a_restart(app_env: Path) -> None:
    # Arrange: add and save a custom reason in a first session
    at = _open_app()
    at.radio[0].set_value("Invalid")
    _add_reason(at, CUSTOM)
    _button(at, "💾 Save").click().run()

    # Act: a brand-new app run on the same folders (simulated restart)
    restarted = _open_app()

    # Assert
    boxes = _main_checkboxes(restarted)
    assert list(boxes) == [*DEFAULT_REASONS, CUSTOM]
    assert boxes[CUSTOM] is True  # the saved image shows it ticked


def test_custom_reason_is_offered_for_another_form(app_env: Path) -> None:
    # Arrange
    _add_reason(_open_app(), CUSTOM)
    shutil.copy(app_env / "forms" / "test_form.xlsx", app_env / "forms" / "other_form.xlsx")
    shutil.copy(app_env / "data" / "test_export.xlsx", app_env / "data" / "other_export.xlsx")

    # Act
    at = _open_app("other_form.xlsx", "other_export.xlsx")

    # Assert
    assert list(_main_checkboxes(at)) == [*DEFAULT_REASONS, CUSTOM]


def test_unreadable_reasons_file_warns_and_is_left_untouched(app_env: Path) -> None:
    # Arrange
    reasons_file = app_env / "evaluations" / "custom_reasons.json"
    reasons_file.parent.mkdir(parents=True, exist_ok=True)
    reasons_file.write_text("{not json", encoding="utf-8")

    # Act
    at = _open_app()

    # Assert
    assert list(_main_checkboxes(at)) == list(DEFAULT_REASONS)
    assert any("custom reasons" in t for t in _texts(at.warning))
    assert reasons_file.read_text(encoding="utf-8") == "{not json"


# --------------------------------------------------------------------------- US3
def test_import_registers_custom_reason_and_offers_it(app_env: Path) -> None:
    # Arrange: export a report that uses a custom reason, then forget the reason
    at = _open_app()
    at.radio[0].set_value("Invalid")
    _add_reason(at, CUSTOM)
    _button(at, "💾 Save").click().run()
    at.button(key="export_report").click().run()
    report = next((app_env / "reports").glob("*.xlsx"))
    (app_env / "evaluations" / "custom_reasons.json").unlink()
    for autosave in (app_env / "evaluations").glob("*__*.json"):
        autosave.unlink()
    at = _open_app()
    assert list(_main_checkboxes(at)) == list(DEFAULT_REASONS)

    # Act
    at.file_uploader(key="import_report_file").set_value(
        (report.name, report.read_bytes(), XLSX_MIME)
    ).run()
    at.button(key="import_report").click().run()

    # Assert
    assert f"Added invalid reasons: {CUSTOM}." in _texts(at.sidebar.info)
    assert CUSTOM in _main_checkboxes(at)


# --------------------------------------------------------------------------- US4
def test_manage_reasons_lists_defaults_without_controls(app_env: Path) -> None:
    at = _open_app()

    captions = _texts(at.sidebar.caption)
    assert all(f"{name} · default" in captions for name in DEFAULT_REASONS)
    assert not [b for b in at.sidebar.button if str(b.label) in ("Rename", "Hide")]


def test_rename_updates_saved_evaluation_and_checkbox(app_env: Path) -> None:
    # Arrange: save the first image with a misspelt custom reason
    at = _open_app()
    at.radio[0].set_value("Invalid")
    _add_reason(at, "Fingr over lens")
    _button(at, "💾 Save").click().run()
    reason_id = next(b.key for b in at.sidebar.button if str(b.label) == "Rename")
    old_id = str(reason_id).removeprefix("rename_")

    # Act
    at.text_input(key=f"rename_input_{old_id}").input(CUSTOM)
    at.button(key=f"rename_{old_id}").click().run()

    # Assert
    assert f"Renamed 'Fingr over lens' to '{CUSTOM}' in 1 saved evaluation file(s)." in _texts(
        at.sidebar.success
    )
    assert _autosave_reasons(app_env) == [[CUSTOM]]
    boxes = _main_checkboxes(at)
    assert boxes.get(CUSTOM) is True
    assert "Fingr over lens" not in boxes


def test_hidden_reason_stays_on_saved_image_only(app_env: Path) -> None:
    # Arrange: save the first image with a custom reason, then hide it
    at = _open_app()
    at.radio[0].set_value("Invalid")
    _add_reason(at, CUSTOM)
    _button(at, "💾 Save & next").click().run()
    hide = next(b for b in at.sidebar.button if str(b.label) == "Hide")

    # Act
    hide.click().run()

    # Assert: not offered on the second (new) image
    assert CUSTOM not in _main_checkboxes(at)
    assert any(f"{CUSTOM} (hidden)" in str(m.value) for m in at.sidebar.markdown)
    # ...but still ticked on the saved first image
    _button(at, "First").click().run()
    assert _main_checkboxes(at).get(CUSTOM) is True
    # ...and offered again once restored
    next(b for b in at.sidebar.button if str(b.label) == "Restore").click().run()
    _button(at, "Next ▶").click().run()
    assert CUSTOM in _main_checkboxes(at)
