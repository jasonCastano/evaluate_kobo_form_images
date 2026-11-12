"""Tests for image decoding and caching (no network)."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from evaluate_kobo_form_images.kobo_client import (
    ImageFetchError,
    KoboImageClient,
    to_display_jpeg,
)


def _png(width: int, height: int) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", (width, height), (10, 120, 30, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_to_display_jpeg_downscales_and_converts() -> None:
    data = to_display_jpeg(_png(4000, 2000), max_side=1000)
    with Image.open(io.BytesIO(data)) as image:
        assert image.format == "JPEG"
        assert image.size == (1000, 500)


def test_to_display_jpeg_rejects_non_images() -> None:
    with pytest.raises(ImageFetchError):
        to_display_jpeg(b"<html>login</html>")


def test_client_sends_token_and_serves_from_cache(tmp_path: Path) -> None:
    # Arrange
    client = KoboImageClient(token="secret", cache_dir=tmp_path)
    url = "https://kf.kobotoolbox.org/api/v2/assets/a/data/1/attachments/att/"
    client._cache_path(url).write_bytes(b"cached")

    # Act / Assert
    assert client.session.headers["Authorization"] == "Token secret"
    assert client.is_cached(url)
    assert client.fetch(url) == b"cached"
