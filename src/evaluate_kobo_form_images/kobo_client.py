"""Download Kobo image attachments with a local disk cache.

The API key of the signed-in :class:`~evaluate_kobo_form_images.kobo_auth.KoboSession` is
attached **only** to URLs served by that session's server, so it can never leak to another
host. Failures carry a :class:`FetchFailure` reason so the UI can react appropriately.
"""

from __future__ import annotations

import hashlib
import io
import uuid
from enum import StrEnum
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageOps

from evaluate_kobo_form_images.kobo_auth import HttpGetter, KoboServer, KoboSession

DEFAULT_TIMEOUT = 30
DISPLAY_MAX_SIDE = 1600


class FetchFailure(StrEnum):
    """Why an image could not be shown."""

    NOT_SIGNED_IN = "not_signed_in"
    ACCESS_EXPIRED = "access_expired"
    NO_ACCESS = "no_access"
    UNREACHABLE = "unreachable"
    NOT_AN_IMAGE = "not_an_image"


class ImageFetchError(RuntimeError):
    """Raised when an attachment cannot be downloaded or decoded."""

    def __init__(self, reason: FetchFailure, message: str) -> None:
        super().__init__(message)
        self.reason = reason


SIGN_IN_MESSAGE = "Sign in to your Kobo account in the sidebar to see this image."
EXPIRED_MESSAGE = "Your Kobo access expired or was revoked. Please sign in again."
NO_ACCESS_MESSAGE = (
    "Your account does not have access to this image (or it no longer exists in Kobo)."
)
NOT_AN_IMAGE_MESSAGE = "The downloaded file is not a readable image."


def _host_label(url: str) -> str:
    try:
        return KoboServer.from_url(url).label
    except Exception:
        return "the server hosting this image"


class KoboImageClient:
    """Fetch Kobo attachment URLs and cache display-ready JPEGs.

    Kobo attachment URLs (``/api/v2/assets/<uid>/data/<id>/attachments/<uid>/``) require
    authentication; the session's key is sent as ``Authorization: Token <key>``.
    """

    def __init__(
        self,
        session: KoboSession | None,
        cache_dir: Path,
        timeout: int = DEFAULT_TIMEOUT,
        http: HttpGetter | None = None,
    ) -> None:
        self.kobo_session = session
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.http: HttpGetter = http or requests.Session()

    def _cache_path(self, url: str) -> Path:
        return self.cache_dir / f"{hashlib.sha1(url.encode('utf-8')).hexdigest()}.jpg"

    def is_cached(self, url: str) -> bool:
        """Return whether a display copy of the URL is already cached."""
        return self._cache_path(url).exists()

    def _headers_for(self, url: str) -> dict[str, str]:
        session = self.kobo_session
        if session is not None and session.server.owns(url):
            return {"Authorization": f"Token {session.token}"}
        return {}

    def _failure(self, status: int, authenticated: bool, url: str) -> ImageFetchError:
        if status >= 500:
            return ImageFetchError(
                FetchFailure.UNREACHABLE,
                f"Kobo ({_host_label(url)}) cannot be reached. Check your connection and retry.",
            )
        if status in (401, 403, 404) and not authenticated:
            if self.kobo_session is not None:
                return ImageFetchError(
                    FetchFailure.NOT_SIGNED_IN,
                    f"This image is hosted on {_host_label(url)}. "
                    "Sign in to that server to see it.",
                )
            return ImageFetchError(FetchFailure.NOT_SIGNED_IN, SIGN_IN_MESSAGE)
        if status == 401:
            return ImageFetchError(FetchFailure.ACCESS_EXPIRED, EXPIRED_MESSAGE)
        if status in (403, 404):
            return ImageFetchError(FetchFailure.NO_ACCESS, NO_ACCESS_MESSAGE)
        return ImageFetchError(FetchFailure.UNREACHABLE, f"Kobo answered HTTP {status}.")

    def fetch(self, url: str) -> bytes:
        """Return a JPEG (EXIF-rotated, downscaled) for display, using the cache when possible.

        Raises:
            ImageFetchError: with a :class:`FetchFailure` reason and a plain-English message.
        """
        path = self._cache_path(url)
        if path.exists():
            return path.read_bytes()
        headers = self._headers_for(url)
        try:
            response: Any = self.http.get(url, headers=headers, timeout=self.timeout)
        except requests.RequestException:
            raise ImageFetchError(
                FetchFailure.UNREACHABLE,
                f"Kobo ({_host_label(url)}) cannot be reached. Check your connection and retry.",
            ) from None
        if not response.ok:
            raise self._failure(response.status_code, bool(headers), url)
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
    except OSError:
        raise ImageFetchError(FetchFailure.NOT_AN_IMAGE, NOT_AN_IMAGE_MESSAGE) from None
    return buffer.getvalue()
