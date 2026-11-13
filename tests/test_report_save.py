"""Tests for saving the Excel report to a local folder."""

from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path

import pytest

from evaluate_kobo_form_images import report
from evaluate_kobo_form_images.report import ReportSaveError, report_file_name, save_report

NOW = datetime(2026, 11, 12, 16, 30, 0)
CONTENT = b"PK fake xlsx bytes"


def test_report_file_name_uses_form_stem_and_timestamp() -> None:
    assert report_file_name("CIAT_CIV_2_Yield_FORM.xlsx", NOW) == (
        "image_evaluation__CIAT_CIV_2_Yield_FORM__20261112-163000.xlsx"
    )


def test_report_file_name_sanitizes_unsafe_characters() -> None:
    assert report_file_name("Form: P&D (v2).xlsx", NOW) == (
        "image_evaluation__Form__P_D__v2___20261112-163000.xlsx"
    )


def test_save_report_creates_folder_and_writes_file(tmp_path: Path) -> None:
    # Arrange
    folder = tmp_path / "nested" / "reports"

    # Act
    path = save_report(CONTENT, folder, "form.xlsx", now=NOW)

    # Assert
    assert path.is_absolute()
    assert path.parent == folder.resolve()
    assert path.read_bytes() == CONTENT
    assert not list(folder.glob("*.tmp"))


def test_save_report_never_overwrites(tmp_path: Path) -> None:
    first = save_report(CONTENT, tmp_path, "form.xlsx", now=NOW)
    second = save_report(b"second", tmp_path, "form.xlsx", now=NOW)
    third = save_report(b"third", tmp_path, "form.xlsx", now=NOW)

    assert first != second != third
    assert second.name.endswith("-2.xlsx")
    assert third.name.endswith("-3.xlsx")
    assert first.read_bytes() == CONTENT


def test_save_report_expands_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    path = save_report(CONTENT, "~/reports", "form.xlsx", now=NOW)
    assert path.parent == (tmp_path / "reports").resolve()


def test_permission_error_is_explained_and_cleaned_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def deny(src: object, dst: object) -> None:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(report.os, "replace", deny)
    with pytest.raises(ReportSaveError) as info:
        save_report(CONTENT, tmp_path, "form.xlsx", now=NOW)
    assert info.value.reason == "Permission denied (is the file or folder open in another program?)"
    assert str(info.value).startswith("Could not save the report to ")
    assert not list(tmp_path.glob("*.tmp"))
    assert not list(tmp_path.glob("*.xlsx"))


def test_invalid_folder_is_explained(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_mkdir(self: Path, *args: object, **kwargs: object) -> None:
        raise OSError(2, "The system cannot find the drive specified")

    monkeypatch.setattr(Path, "mkdir", broken_mkdir)
    with pytest.raises(ReportSaveError) as info:
        save_report(CONTENT, tmp_path / "x", "form.xlsx", now=NOW)
    assert info.value.reason.startswith(
        "The folder path is not valid or the drive is not available"
    )


def test_slow_folder_times_out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def slow(tmp: Path, final: Path, content: bytes) -> None:
        time.sleep(1)

    monkeypatch.setattr(report, "_write_atomic", slow)
    with pytest.raises(ReportSaveError) as info:
        save_report(CONTENT, tmp_path, "form.xlsx", now=NOW, timeout=0.1)
    assert info.value.reason == (
        "Saving took too long — the folder may be on a slow or offline drive."
    )


def test_os_replace_is_used_for_atomic_write(tmp_path: Path) -> None:
    # The real writer leaves only the final file.
    path = save_report(CONTENT, tmp_path, "form.xlsx", now=NOW)
    assert os.listdir(tmp_path) == [path.name]
