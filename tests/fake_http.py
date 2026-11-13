"""Minimal stand-in for ``requests.Session`` used to stub Kobo HTTP calls in tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeResponse:
    """A canned HTTP response."""

    status_code: int = 200
    json_data: Any = None
    content: bytes = b""

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    def json(self) -> Any:
        if self.json_data is None:
            raise ValueError("No JSON body")
        return self.json_data


@dataclass
class Call:
    """One recorded request."""

    url: str
    headers: dict[str, str]
    auth: tuple[str, str] | None


@dataclass
class FakeHttp:
    """Records ``get`` calls and replays queued responses or exceptions in order."""

    queue: list[FakeResponse | Exception] = field(default_factory=list)
    calls: list[Call] = field(default_factory=list)

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        auth: tuple[str, str] | None = None,
        timeout: float | None = None,
    ) -> FakeResponse:
        del timeout
        self.calls.append(Call(url=url, headers=dict(headers or {}), auth=auth))
        if not self.queue:
            raise AssertionError(f"Unexpected HTTP call to {url}")
        item = self.queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
