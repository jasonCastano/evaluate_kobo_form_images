"""Download Kobo image attachments (authenticated) with a local disk cache."""

from __future__ import annotations

import hashlib
import io
import uuid
from pathlib import Path

import requests
from PIL import Image, ImageOps

DEFAULT_TIMEOUT = 30
DISPLAY_MAX_SIDE = 1600


class ImageFetchError(RuntimeError):
    """Raised when an attachment cannot be downloaded or decoded."""


class KoboImageClient:
    """Fetch Kobo attachment URLs using an API token and cache display-ready JPEGs.

    Kobo attachment URLs (``/api/v2/assets/<uid>/data/<id>/attachments/<uid>/``) require
    authentication. The token is sent as ``Authorization: Token <token>``.
    """

    def __init__(self, token: str, cache_dir: Path, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.session = requests.Session()
        if token:
            self.session.headers["Authorization"] = f"Token {token.strip()}"

    def _cache_path(self, url: str) -> Path:
        return self.cache_dir / f"{hashlib.sha1(url.encode('utf-8')).hexdigest()}.jpg"

    def is_cached(self, url: str) -> bool:
        """Return whether a display copy of the URL is already cached."""
        return self._cache_path(url).exists()

    def fetch(self, url: str) -> bytes:
        """Return a JPEG (EXIF-rotated, downscaled) for display, using the cache when possible."""
        path = self._cache_path(url)
        if path.exists():
            return path.read_bytes()
        try:
            response = self.session.get(url, timeout=self.timeout)
        except requests.RequestException as exc:
            raise ImageFetchError(f"Network error while downloading the image: {exc}") from exc
        if response.status_code in (401, 403, 404) and "Authorization" not in self.session.headers:
            raise ImageFetchError(
                f"Kobo answered HTTP {response.status_code}. Provide a Kobo API token."
            )
        if response.status_code in (401, 403):
            raise ImageFetchError(
                f"Kobo answered HTTP {response.status_code}: check the API token permissions."
            )
        if response.status_code == 404:
            raise ImageFetchError("Kobo answered HTTP 404: the attachment was not found.")
        if not response.ok:
            raise ImageFetchError(f"Kobo answered HTTP {response.status_code}.")
        data = to_display_jpeg(response.content)
        tmp = path.with_name(f"{path.stem}.{uuid.uuid4().hex}.tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
        return data


def to_display_jpeg(raw: bytes, max_side: int = DISPLAY_MAX_SIDE) -> bytes:
    """Decode an image, apply its EXIF orientation, downscale it and re-encode as JPEG."""
    try:
        with Image.open(io.BytesIO(raw)) as image:
            image = ImageOps.exif_transpose(image) or image
            image = image.convert("RGB")
            image.thumbnail((max_side, max_side))
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=88)
    except OSError as exc:
        raise ImageFetchError(f"The downloaded file is not a readable image: {exc}") from exc
    return buffer.getvalue()
