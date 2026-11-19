"""Invalid reasons: the fixed defaults plus the evaluator's custom reasons.

Custom reasons are local data kept in one JSON file per installation (by default
``<EVALUATIONS_DIR>/custom_reasons.json``, see
``specs/005-custom-invalid-reasons/contracts/custom-reasons-file.md``). They are shared by all
forms, never deleted (only hidden) and re-read from disk before every change, so two browser
tabs never overwrite each other's additions.
"""

from __future__ import annotations

import hashlib
import json
import os
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from evaluate_kobo_form_images.evaluation import Evaluation

MAX_REASON_LENGTH = 60
FILE_VERSION = 1
DEFAULT_FILE_NAME = "custom_reasons.json"
CUSTOM_REASONS_ENV = "CUSTOM_REASONS_FILE"


class InvalidReason(StrEnum):
    """Default reasons an image can be rejected for (fixed; custom ones live in the catalogue)."""

    LOW_LIGHT = "Low lighting"
    TOO_BRIGHT = "Too bright / overexposed"
    BLURRY = "Out of focus / blurry"
    INVALID_CONTENT = "Invalid image content"


DEFAULT_REASONS: tuple[str, ...] = tuple(reason.value for reason in InvalidReason)


class ReasonError(ValueError):
    """A reason name or change was refused; ``message`` is plain English for the evaluator."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


# --------------------------------------------------------------------------- name rules
def normalize_reason(name: str) -> str:
    """Comparison key: whitespace collapsed and case folded."""
    return " ".join(str(name).split()).casefold()


def clean_reason_name(name: str) -> str:
    """Return the display form of ``name`` (trimmed, inner whitespace collapsed).

    Raises:
        ReasonError: empty, longer than 60 characters, containing ``;`` or control characters.
    """
    text = str(name)
    if any(unicodedata.category(char) == "Cc" and char not in " \t\n\r" for char in text):
        raise ReasonError("Reason names cannot contain control characters.")
    cleaned = " ".join(text.split())
    if not cleaned:
        raise ReasonError("Enter a reason name.")
    if len(cleaned) > MAX_REASON_LENGTH:
        raise ReasonError(f"Reason names can have at most {MAX_REASON_LENGTH} characters.")
    if ";" in cleaned:
        raise ReasonError("Reason names cannot contain ';'.")
    return cleaned


def reason_widget_id(name: str) -> str:
    """Short, stable identifier of a reason (same for names equal by key), for widget keys."""
    return hashlib.sha1(normalize_reason(name).encode("utf-8")).hexdigest()[:10]


def catalogue_path(evaluations_dir: Path) -> Path:
    """Location of the custom reasons file (``CUSTOM_REASONS_FILE`` overrides it)."""
    override = os.getenv(CUSTOM_REASONS_ENV)
    return Path(override) if override else evaluations_dir / DEFAULT_FILE_NAME


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


# --------------------------------------------------------------------------- catalogue
@dataclass(frozen=True)
class CustomReason:
    """A reason added by an evaluator."""

    name: str
    hidden: bool = False
    created_at: str = ""


class ReasonCatalogue:
    """The installation's permanent list of custom invalid reasons."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.load_error: str | None = None
        self.backup_path: Path | None = None
        self._preserve_on_write = False

    # ----------------------------------------------------------------- reading
    def _unreadable(self, detail: str) -> list[CustomReason]:
        self.load_error = (
            f"Could not read the custom reasons file ({self.path}): {detail}. "
            "Only the default reasons are shown; the file was not changed."
        )
        self._preserve_on_write = True
        return []

    def _read(self) -> list[CustomReason]:
        self.load_error = None
        self._preserve_on_write = False
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            return self._unreadable(str(exc))
        if not isinstance(payload, dict):
            return self._unreadable("the content is not a JSON object")
        if payload.get("version") != FILE_VERSION:
            return self._unreadable(f"unsupported version {payload.get('version')!r}")
        items = payload.get("reasons")
        if not isinstance(items, list):
            return self._unreadable("'reasons' is not a list")
        reasons: list[CustomReason] = []
        keys = {normalize_reason(name) for name in DEFAULT_REASONS}
        skipped: list[str] = []
        for item in items:
            raw = item.get("name") if isinstance(item, dict) else None
            try:
                name = clean_reason_name(raw) if isinstance(raw, str) else None
            except ReasonError:
                name = None
            if name is None or normalize_reason(name) in keys:
                skipped.append(repr(raw))
                continue
            keys.add(normalize_reason(name))
            assert isinstance(item, dict)
            reasons.append(
                CustomReason(
                    name=name,
                    hidden=bool(item.get("hidden", False)),
                    created_at=str(item.get("created_at", "")),
                )
            )
        if skipped:
            self.load_error = (
                f"Some entries of the custom reasons file ({self.path}) were skipped because "
                f"they are invalid or duplicated: {', '.join(skipped)}. The file was not changed."
            )
            self._preserve_on_write = True
        return reasons

    def _write(self, reasons: list[CustomReason]) -> None:
        if self._preserve_on_write and self.path.exists():
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = self.path.with_name(f"{self.path.name}.unreadable-{stamp}")
            counter = 2
            while backup.exists():
                backup = self.path.with_name(f"{self.path.name}.unreadable-{stamp}-{counter}")
                counter += 1
            os.replace(self.path, backup)
            self.backup_path = backup
        _write_json_atomic(
            self.path,
            {
                "version": FILE_VERSION,
                "updated_at": _now(),
                "reasons": [
                    {"name": r.name, "hidden": r.hidden, "created_at": r.created_at}
                    for r in reasons
                ],
            },
        )
        self._preserve_on_write = False
        self.load_error = None

    # ----------------------------------------------------------------- queries
    def custom(self) -> list[CustomReason]:
        """Custom reasons in creation order (hidden included)."""
        return self._read()

    def all_names(self) -> list[str]:
        """Defaults, then every custom reason (hidden included)."""
        return [*DEFAULT_REASONS, *(reason.name for reason in self._read())]

    def offered_names(self, selected: Iterable[str] = ()) -> list[str]:
        """Reasons to show as checkboxes.

        Defaults, then visible custom reasons, plus hidden or unknown names that are already
        in ``selected`` (so a saved evaluation keeps showing its reasons ticked).
        """
        selected = list(selected)
        selected_keys = {normalize_reason(name) for name in selected}
        names = list(DEFAULT_REASONS)
        names += [
            reason.name
            for reason in self._read()
            if not reason.hidden or normalize_reason(reason.name) in selected_keys
        ]
        known = {normalize_reason(name) for name in names}
        for name in selected:
            if normalize_reason(name) not in known:
                names.append(name)
                known.add(normalize_reason(name))
        return names

    def canonical(self, name: str) -> str | None:
        """The known display name equal to ``name`` ignoring case and spacing, if any."""
        key = normalize_reason(name)
        return next((known for known in self.all_names() if normalize_reason(known) == key), None)

    def is_default(self, name: str) -> bool:
        """Whether ``name`` is one of the fixed default reasons."""
        return normalize_reason(name) in {normalize_reason(d) for d in DEFAULT_REASONS}

    # ----------------------------------------------------------------- changes
    def _existing(self, reasons: list[CustomReason], key: str) -> str | None:
        for name in (*DEFAULT_REASONS, *(r.name for r in reasons)):
            if normalize_reason(name) == key:
                return name
        return None

    def add(self, name: str) -> str:
        """Add a custom reason and return its display name.

        Raises:
            ReasonError: invalid name or already existing (hidden reasons included).
        """
        cleaned = clean_reason_name(name)
        reasons = self._read()
        existing = self._existing(reasons, normalize_reason(cleaned))
        if existing is not None:
            raise ReasonError(f"'{existing}' already exists.")
        reasons.append(CustomReason(name=cleaned, hidden=False, created_at=_now()))
        self._write(reasons)
        return cleaned

    def ensure(self, names: Iterable[str]) -> list[str]:
        """Add every valid, unknown name (one write); return the names that were added."""
        reasons = self._read()
        added: list[str] = []
        for name in names:
            try:
                cleaned = clean_reason_name(name)
            except ReasonError:
                continue
            if self._existing(reasons, normalize_reason(cleaned)) is None:
                reasons.append(CustomReason(name=cleaned, hidden=False, created_at=_now()))
                added.append(cleaned)
        if added:
            self._write(reasons)
        return added

    def _custom_index(self, reasons: list[CustomReason], name: str) -> int:
        if self.is_default(name):
            raise ReasonError("Default reasons cannot be changed.")
        key = normalize_reason(name)
        for index, reason in enumerate(reasons):
            if normalize_reason(reason.name) == key:
                return index
        raise ReasonError(f"'{name}' is not a custom reason.")

    def rename(self, old: str, new: str) -> str:
        """Rename a custom reason (position, date and visibility kept); return the new name.

        Raises:
            ReasonError: ``old`` is a default or unknown, or ``new`` is invalid / taken.
        """
        reasons = self._read()
        index = self._custom_index(reasons, old)
        cleaned = clean_reason_name(new)
        key = normalize_reason(cleaned)
        if key != normalize_reason(reasons[index].name):
            existing = self._existing(reasons, key)
            if existing is not None:
                raise ReasonError(f"'{existing}' already exists.")
        reasons[index] = replace(reasons[index], name=cleaned)
        self._write(reasons)
        return cleaned

    def set_hidden(self, name: str, hidden: bool) -> None:
        """Hide (stop offering) or restore a custom reason.

        Raises:
            ReasonError: ``name`` is a default or unknown.
        """
        reasons = self._read()
        index = self._custom_index(reasons, name)
        if reasons[index].hidden != hidden:
            reasons[index] = replace(reasons[index], hidden=hidden)
            self._write(reasons)


# --------------------------------------------------------------------------- helpers
def rename_reason_in_stores(directory: Path, old: str, new: str) -> int:
    """Replace reason ``old`` by ``new`` in every autosave file (``*__*.json``) of ``directory``.

    Files are rewritten atomically and only when they use ``old``; unreadable files are left
    alone. Returns the number of files rewritten.
    """
    old_key, new_key = normalize_reason(old), normalize_reason(new)
    rewritten = 0
    for path in sorted(directory.glob("*__*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            evaluations = payload["evaluations"]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        changed = False
        for item in evaluations if isinstance(evaluations, list) else []:
            reasons = item.get("reasons") if isinstance(item, dict) else None
            if not isinstance(reasons, list):
                continue
            if not any(normalize_reason(str(r)) == old_key for r in reasons):
                continue
            updated: list[str] = []
            seen: set[str] = set()
            for reason in reasons:
                is_old = normalize_reason(str(reason)) == old_key
                name = new if is_old else str(reason)
                key = new_key if is_old else normalize_reason(name)
                if key not in seen:
                    seen.add(key)
                    updated.append(name)
            item["reasons"] = updated
            changed = True
        if changed:
            _write_json_atomic(path, payload)
            rewritten += 1
    return rewritten


def report_reasons(
    catalogue: ReasonCatalogue | None, evaluations: Iterable[Evaluation]
) -> list[str]:
    """Reason columns of a report.

    Defaults, then visible custom reasons, then hidden custom reasons used by an evaluation,
    then names used by an evaluation but unknown to the catalogue (first-use order).
    """
    used: dict[str, str] = {}
    for evaluation in evaluations:
        for reason in evaluation.reasons:
            used.setdefault(normalize_reason(reason), str(reason))
    names = list(DEFAULT_REASONS)
    custom = catalogue.custom() if catalogue is not None else []
    names += [reason.name for reason in custom if not reason.hidden]
    names += [
        reason.name for reason in custom if reason.hidden and normalize_reason(reason.name) in used
    ]
    keys = {normalize_reason(name) for name in names}
    names += [name for key, name in used.items() if key not in keys]
    return names
