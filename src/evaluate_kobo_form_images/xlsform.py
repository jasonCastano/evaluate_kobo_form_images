"""Parse KoboToolbox XLSForm definitions and extract their image questions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO

from openpyxl import load_workbook

IMAGE_TYPES = frozenset({"image", "photo"})
_BEGIN_GROUP = frozenset({"begin_group", "begin group"})
_END_GROUP = frozenset({"end_group", "end group"})
_BEGIN_REPEAT = frozenset({"begin_repeat", "begin repeat"})
_END_REPEAT = frozenset({"end_repeat", "end repeat"})
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


def normalize_text(value: object) -> str:
    """Normalize a label or header for tolerant comparisons.

    HTML tags and markdown emphasis are removed, whitespace is collapsed and the text is
    case-folded, so ``"Take the  <b>photo</b>"`` matches ``"take the photo"``.
    """
    text = _TAG_RE.sub("", str(value or ""))
    text = text.replace("*", "")
    return _SPACE_RE.sub(" ", text).strip().casefold()


@dataclass(frozen=True)
class ImageQuestion:
    """An ``image`` question declared in the ``survey`` sheet of an XLSForm."""

    name: str
    labels: dict[str, str]
    group_path: tuple[str, ...] = ()
    repeat_path: tuple[str, ...] = ()
    row_number: int = 0

    @property
    def label(self) -> str:
        """Return the best human-readable label (English first, then any label, then name)."""
        for key, value in self.labels.items():
            if "english" in key.casefold() or key.casefold().endswith("(en)"):
                return value
        if "label" in self.labels:
            return self.labels["label"]
        return next(iter(self.labels.values()), self.name)

    @property
    def group(self) -> str:
        """Return the slash-separated group path (``"group_a/group_b"``)."""
        return "/".join(self.group_path)


@dataclass
class KoboForm:
    """An XLSForm with its metadata and the list of image questions it declares."""

    file_name: str
    title: str
    form_id: str
    version: str
    image_questions: list[ImageQuestion] = field(default_factory=list)

    def by_name(self) -> dict[str, ImageQuestion]:
        """Index image questions by their XML ``name``."""
        return {question.name: question for question in self.image_questions}


def _cell(row: tuple[Any, ...], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    value = row[index]
    return "" if value is None else str(value).strip()


def _read_settings(workbook: Any) -> dict[str, str]:
    if "settings" not in workbook.sheetnames:
        return {}
    rows = list(workbook["settings"].iter_rows(values_only=True))
    if len(rows) < 2:
        return {}
    header, values = rows[0], rows[1]
    return {
        str(key).strip(): "" if value is None else str(value).strip()
        for key, value in zip(header, values, strict=False)
        if key
    }


def parse_xlsform(source: str | Path | BinaryIO, file_name: str | None = None) -> KoboForm:
    """Parse an XLSForm workbook and return its image questions in form order.

    Args:
        source: Path or binary file-like object of the ``.xlsx`` XLSForm.
        file_name: Display name of the form file (defaults to the path name).

    Raises:
        ValueError: If the workbook has no ``survey`` sheet or no ``type``/``name`` columns.
    """
    if file_name is None:
        file_name = Path(source).name if isinstance(source, str | Path) else "form.xlsx"
    workbook = load_workbook(source, read_only=True, data_only=True)
    try:
        if "survey" not in workbook.sheetnames:
            raise ValueError(f"'{file_name}' is not an XLSForm: missing 'survey' sheet.")
        rows = list(workbook["survey"].iter_rows(values_only=True))
        settings = _read_settings(workbook)
    finally:
        workbook.close()

    if not rows:
        raise ValueError(f"'{file_name}' has an empty 'survey' sheet.")
    header = [str(value).strip() if value is not None else "" for value in rows[0]]
    if "type" not in header or "name" not in header:
        raise ValueError(f"'{file_name}' survey sheet needs 'type' and 'name' columns.")
    type_idx, name_idx = header.index("type"), header.index("name")
    label_idx = {
        col: idx for idx, col in enumerate(header) if col == "label" or col.startswith("label::")
    }

    groups: list[tuple[str, bool]] = []  # (name, is_repeat)
    questions: list[ImageQuestion] = []
    for offset, row in enumerate(rows[1:], start=2):
        qtype = _cell(row, type_idx).casefold()
        base_type = qtype.split(" ")[0]
        name = _cell(row, name_idx)
        if qtype in _BEGIN_GROUP or qtype in _BEGIN_REPEAT:
            groups.append((name, qtype in _BEGIN_REPEAT))
        elif qtype in _END_GROUP or qtype in _END_REPEAT:
            if groups:
                groups.pop()
        elif base_type in IMAGE_TYPES and name:
            labels = {col: _cell(row, idx) for col, idx in label_idx.items() if _cell(row, idx)}
            questions.append(
                ImageQuestion(
                    name=name,
                    labels=labels,
                    group_path=tuple(group for group, _ in groups),
                    repeat_path=tuple(group for group, is_repeat in groups if is_repeat),
                    row_number=offset,
                )
            )

    stem = Path(file_name).stem
    return KoboForm(
        file_name=file_name,
        title=settings.get("form_title") or settings.get("title") or stem,
        form_id=settings.get("form_id") or settings.get("id_string") or stem,
        version=settings.get("version", ""),
        image_questions=questions,
    )
