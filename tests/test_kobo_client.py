"""Tests for authenticated, host-scoped image download and caching (no network)."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
import requests
from PIL import Image

from evaluate_kobo_form_images.kobo_auth import GLOBAL_SERVER, KoboSession, SignInMethod
from evaluate_kobo_form_images.kobo_client import (
    FetchFailure,
    ImageFetchError,
    KoboImageClient,
    to_display_jpeg,
)
from tests.fake_http import FakeHttp, FakeResponse

TOKEN = "0123456789abcdef0123456789abcdef01234567"
KF_URL = "https://kf.kobotoolbox.org/api/v2/assets/a/data/1/attachments/att/"
EU_URL = "https://eu.kobotoolbox.org/api/v2/assets/a/data/1/attachments/att/"


def _png(width: int = 40, height: int = 20) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", (width, height), (10, 120, 30, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def _session() -> KoboSession:
    return KoboSession(
        server=GLOBAL_SERVER,
        username="jdoe",
        token=TOKEN,
        method=SignInMethod.PASSWORD,
        signed_in_at="2026-11-12T14:00:00+00:00",
    )


def _client(tmp_path: Path, http: FakeHttp, signed_in: bool = True) -> KoboImageClient:
    return KoboImageClient(_session() if signed_in else None, tmp_path, http=http)


def test_to_display_jpeg_downscales_and_converts() -> None:
    data = to_display_jpeg(_png(4000, 2000), max_side=1000)
    with Image.open(io.BytesIO(data)) as image:
        assert image.format == "JPEG"
        assert image.size == (1000, 500)


def test_to_display_jpeg_rejects_non_images() -> None:
    with pytest.raises(ImageFetchError) as info:
        to_display_jpeg(b"<html>login</html>")
    assert info.value.reason is FetchFailure.NOT_AN_IMAGE


def test_token_is_sent_only_to_the_signed_in_server(tmp_path: Path) -> None:
    # Arrange
    http = FakeHttp([FakeResponse(200, content=_png()), FakeResponse(200, content=_png())])
    client = _client(tmp_path, http)

    # Act
    client.fetch(KF_URL)
    client.fetch(EU_URL)

    # Assert
    assert http.calls[0].headers["Authorization"] == f"Token {TOKEN}"
    assert "Authorization" not in http.calls[1].headers


@pytest.mark.parametrize(
    ("signed_in", "response", "reason"),
    [
        (False, FakeResponse(401), FetchFailure.NOT_SIGNED_IN),
        (False, FakeResponse(403), FetchFailure.NOT_SIGNED_IN),
        (False, FakeResponse(404), FetchFailure.NOT_SIGNED_IN),
        (True, FakeResponse(401), FetchFailure.ACCESS_EXPIRED),
        (True, FakeResponse(403), FetchFailure.NO_ACCESS),
        (True, FakeResponse(404), FetchFailure.NO_ACCESS),
        (True, FakeResponse(502), FetchFailure.UNREACHABLE),
        (True, requests.ConnectionError("down"), FetchFailure.UNREACHABLE),
        (True, requests.Timeout("slow"), FetchFailure.UNREACHABLE),
        (True, FakeResponse(200, content=b"<html/>"), FetchFailure.NOT_AN_IMAGE),
    ],
)
def test_fetch_failures_are_typed(
    tmp_path: Path,
    signed_in: bool,
    response: FakeResponse | Exception,
    reason: FetchFailure,
) -> None:
    client = _client(tmp_path, FakeHttp([response]), signed_in=signed_in)
    with pytest.raises(ImageFetchError) as info:
        client.fetch(KF_URL)
    assert info.value.reason is reason
    assert TOKEN not in str(info.value)


def test_other_host_failure_asks_to_sign_in_there(tmp_path: Path) -> None:
    client = _client(tmp_path, FakeHttp([FakeResponse(404)]))
    with pytest.raises(ImageFetchError) as info:
        client.fetch(EU_URL)
    assert info.value.reason is FetchFailure.NOT_SIGNED_IN
    assert "eu.kobotoolbox.org" in str(info.value)


def test_cached_image_is_served_without_session_or_http(tmp_path: Path) -> None:
    # Arrange
    http = FakeHttp([FakeResponse(200, content=_png())])
    first = _client(tmp_path, http).fetch(KF_URL)

    # Act
    anonymous = KoboImageClient(None, tmp_path, http=FakeHttp())

    # Assert
    assert anonymous.is_cached(KF_URL)
    assert anonymous.fetch(KF_URL) == first
