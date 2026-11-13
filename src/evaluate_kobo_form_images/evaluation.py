"""Image evaluation model and its on-disk persistence (autosave / resume)."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path


class Verdict(StrEnum):
    """Outcome of an image evaluation."""

    VALID = "Valid"
    INVALID = "Invalid"


class InvalidReason(StrEnum):
    """Reasons an image can be rejected."""

    LOW_LIGHT = "Low lighting"
    TOO_BRIGHT = "Too bright / overexposed"
    BLURRY = "Out of focus / blurry"
    INVALID_CONTENT = "Invalid image content"


@dataclass
class Evaluation:
    """The evaluator's decision about one image record."""

    record_key: str
    verdict: Verdict
    reasons: list[InvalidReason] = field(default_factory=list)
    comments: str = ""
    evaluator: str = ""
    evaluated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds")
    )

    def __post_init__(self) -> None:
        self.verdict = Verdict(self.verdict)
        self.reasons = [InvalidReason(reason) for reason in self.reasons]
        self.comments = self.comments.strip()
        if self.verdict is Verdict.INVALID and not self.reasons:
            raise ValueError("An invalid image needs at least one reason.")
        if self.verdict is Verdict.VALID:
            self.reasons = []

    def to_dict(self) -> dict[str, object]:
        """Serialize to plain JSON-compatible values."""
        data = asdict(self)
        data["verdict"] = self.verdict.value
        data["reasons"] = [reason.value for reason in self.reasons]
        return data


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO-8601 timestamp; naive values are taken as UTC.

    Raises:
        ValueError: if ``value`` is not ISO-8601.
    """
    moment = datetime.fromisoformat(value.strip())
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


@dataclass(frozen=True)
class MergeResult:
    """Outcome of :meth:`EvaluationStore.merge`."""

    added: int
    updated: int
    unchanged: int


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_") or "session"


class EvaluationStore:
    """JSON file that autosaves the evaluations of one form + data export pair."""

    def __init__(self, directory: Path, form_file: str, data_file: str) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        name = f"{_slug(Path(form_file).stem)}__{_slug(Path(data_file).stem)}.json"
        self.path = directory / name
        self.evaluations: dict[str, Evaluation] = {}
        self.form_file = form_file
        self.data_file = data_file
        if self.path.exists():
            self._load()

    def _load(self) -> None:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        for item in payload.get("evaluations", []):
            evaluation = Evaluation(**item)
            self.evaluations[evaluation.record_key] = evaluation

    def save(self) -> None:
        """Write all evaluations to disk atomically."""
        payload = {
            "form_file": self.form_file,
            "data_file": self.data_file,
            "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "evaluations": [evaluation.to_dict() for evaluation in self.evaluations.values()],
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def put(self, evaluation: Evaluation) -> None:
        """Add or replace an evaluation and autosave."""
        self.evaluations[evaluation.record_key] = evaluation
        self.save()

    def remove(self, record_key: str) -> None:
        """Delete an evaluation (if present) and autosave."""
        if self.evaluations.pop(record_key, None) is not None:
            self.save()

    def get(self, record_key: str) -> Evaluation | None:
        """Return the evaluation of a record, if any."""
        return self.evaluations.get(record_key)

    def merge(self, evaluations: Iterable[Evaluation]) -> MergeResult:
        """Merge evaluations without ever deleting: add absent ones, replace strictly newer.

        Identical evaluations, and incoming ones that are older or as old as the stored one,
        leave the store unchanged (local wins ties). Saves once, only if something changed.
        """
        added = updated = unchanged = 0
        for incoming in evaluations:
            current = self.evaluations.get(incoming.record_key)
            if current is None:
                self.evaluations[incoming.record_key] = incoming
                added += 1
            elif current.to_dict() != incoming.to_dict() and parse_timestamp(
                incoming.evaluated_at
            ) > parse_timestamp(current.evaluated_at):
                self.evaluations[incoming.record_key] = incoming
                updated += 1
            else:
                unchanged += 1
        if added or updated:
            self.save()
        return MergeResult(added=added, updated=updated, unchanged=unchanged)
