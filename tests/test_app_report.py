"""UI tests for the "4. Report" sidebar section: local export and import (AppTest, no network)."""

from __future__ import annotations

import io
import shutil
from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from streamlit.testing.v1 import AppTest

from evaluate_kobo_form_images.kobo_client import KoboImageClient

APP = Path(__file__).resolve().parents[1] / "src" / "evaluate_kobo_form_images" / "app.py"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


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
    monkeypatch.setenv("IMAGE_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("REPORTS_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("KOBO_API_TOKEN", "")
    monkeypatch.setattr(KoboImageClient, "fetch", lambda self, url: _jpeg())
    monkeypatch.setattr(KoboImageClient, "is_cached", lambda self, url: True)
    return tmp_path


def _open_app() -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    at.selectbox(key="form_choice").select("test_form.xlsx").run()
    at.selectbox(key="data_choice").select("test_export.xlsx").run()
    return at


def _evaluate_valid(at: AppTest, times: int) -> None:
    """Mark the current image Valid and go to the next one, ``times`` times."""
    for _ in range(times):
        at.radio[0].set_value("Valid")
        next(b for b in at.button if "Save & next" in str(b.label)).click().run()


def _texts(elements: Any) -> list[str]:
    return [str(e.value) for e in elements]


def test_export_writes_report_to_chosen_folder(app_env: Path) -> None:
    # Arrange
    at = _open_app()
    _evaluate_valid(at, 2)

    # Act
    at.button(key="export_report").click().run()

    # Assert
    reports = list((app_env / "reports").glob("*.xlsx"))
    assert len(reports) == 1
    assert at.text_input(key="report_dir").value == str((app_env / "reports").resolve())
    assert any("Report saved to" in t and reports[0].name in t for t in _texts(at.sidebar.success))
    assert not at.get("download_button")


def test_export_to_invalid_folder_shows_error(app_env: Path) -> None:
    blocker = app_env / "a_file"
    blocker.write_text("not a folder")
    at = _open_app()

    at.text_input(key="report_dir").input(str(blocker / "sub")).run()
    at.button(key="export_report").click().run()

    assert any(t.startswith("Could not save the report to") for t in _texts(at.sidebar.error))


def test_import_restores_and_resumes(app_env: Path) -> None:
    # Arrange: evaluate 2 images, export, then wipe the autosave
    at = _open_app()
    _evaluate_valid(at, 2)
    at.button(key="export_report").click().run()
    report = next((app_env / "reports").glob("*.xlsx"))
    for autosave in (app_env / "evaluations").glob("*.json"):
        autosave.unlink()
    at = _open_app()
    at.selectbox(key="filter_status").select("Pending").run()

    # Act
    at.file_uploader(key="import_report_file").set_value(
        (report.name, report.read_bytes(), XLSX_MIME)
    ).run()
    at.button(key="import_report").click().run()

    # Assert
    assert any(t.startswith("Restored 2 evaluations from") for t in _texts(at.sidebar.success))
    assert at.session_state["filter_status"] == "All"
    assert any("Image 3 of 4" in t for t in _texts(at.caption))
    assert {m.label: m.value for m in at.metric}["Valid"] == "2"

    at.button(key="import_report").click().run()
    assert any("This report was already imported." in t for t in _texts(at.sidebar.info))
