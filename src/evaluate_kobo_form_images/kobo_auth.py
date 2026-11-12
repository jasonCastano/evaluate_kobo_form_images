"""Sign in to KoboToolbox and hold the in-memory session used to download private attachments.

Kobo attachments are private. A username and password are exchanged **once** for the
account's API key (``GET /token/`` with HTTP Basic auth); the key is verified with
``GET /me/``, which also returns the canonical username. The resulting :class:`KoboSession`
lives only in memory and is never logged or written to disk.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol
from urllib.parse import urlsplit

import requests

TIMEOUT_SECONDS = 30
_KNOWN_LABELS = {
    "kf.kobotoolbox.org": "Global (kf.kobotoolbox.org)",
    "eu.kobotoolbox.org": "EU (eu.kobotoolbox.org)",
}
_LOCAL_HOSTS = ("localhost", "127.0.0.1")


class HttpGetter(Protocol):
    """The subset of ``requests.Session`` used here (lets tests inject a fake)."""

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = ...,
        auth: tuple[str, str] | None = ...,
        timeout: float | None = ...,
    ) -> Any: ...


class AuthErrorKind(StrEnum):
    """Why a sign-in attempt failed."""

    INVALID_CREDENTIALS = "invalid_credentials"
    INVALID_TOKEN = "invalid_token"
    UNREACHABLE = "unreachable"
    INVALID_SERVER = "invalid_server"
    UNEXPECTED = "unexpected"


class AuthError(Exception):
    """A sign-in failure with a plain-language English message for the evaluator."""

    def __init__(self, kind: AuthErrorKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


_INVALID_SERVER_MESSAGE = "Enter a valid Kobo server address, e.g. https://kf.kobotoolbox.org"
_INVALID_PASSWORD_MESSAGE = (
    "Invalid Kobo username or password. If you sign in to Kobo with your organization (SSO) "
    "or use two-factor authentication, use an API key instead."
)


@dataclass(frozen=True)
class KoboServer:
    """A Kobo instance identified by its normalized ``scheme://host[:port]``."""

    base_url: str
    label: str

    @classmethod
    def from_url(cls, url: str) -> KoboServer:
        """Build a server from any URL on it (e.g. an attachment link).

        Raises:
            AuthError: ``INVALID_SERVER`` when the address has no host or an unsupported
                scheme (plain ``http`` is only allowed for localhost).
        """
        try:
            parts = urlsplit(url.strip())
            host = (parts.hostname or "").lower()
            port = parts.port
        except ValueError:
            raise AuthError(AuthErrorKind.INVALID_SERVER, _INVALID_SERVER_MESSAGE) from None
        scheme = parts.scheme.lower()
        allowed = scheme == "https" or (scheme == "http" and host in _LOCAL_HOSTS)
        if not host or not allowed:
            raise AuthError(AuthErrorKind.INVALID_SERVER, _INVALID_SERVER_MESSAGE)
        netloc = f"{host}:{port}" if port else host
        return cls(base_url=f"{scheme}://{netloc}", label=_KNOWN_LABELS.get(netloc, netloc))

    def owns(self, url: str) -> bool:
        """Return whether ``url`` is served by this exact server (same scheme, host, port)."""
        try:
            return KoboServer.from_url(url).base_url == self.base_url
        except AuthError:
            return False


GLOBAL_SERVER = KoboServer.from_url("https://kf.kobotoolbox.org")
EU_SERVER = KoboServer.from_url("https://eu.kobotoolbox.org")
KNOWN_SERVERS: tuple[KoboServer, ...] = (GLOBAL_SERVER, EU_SERVER)


class SignInMethod(StrEnum):
    """How a session was obtained (shown to the evaluator)."""

    PASSWORD = "username & password"
    API_KEY = "API key"
    ENVIRONMENT = "environment"


@dataclass(frozen=True)
class KoboSession:
    """In-memory proof of identity for one Kobo server and user. Never persist it."""

    server: KoboServer
    username: str
    token: str = field(repr=False)
    method: SignInMethod
    signed_in_at: str

    def __repr__(self) -> str:
        return (
            f"KoboSession(server={self.server.base_url!r}, username={self.username!r}, "
            f"token='****{self.token[-4:]}', method={self.method.value!r}, "
            f"signed_in_at={self.signed_in_at!r})"
        )

    __str__ = __repr__


def detect_server(urls: Iterable[str]) -> KoboServer:
    """Return the server hosting most of ``urls`` (ties: first seen; none: global server)."""
    counts: Counter[str] = Counter()
    servers: dict[str, KoboServer] = {}
    for url in urls:
        if not url:
            continue
        try:
            server = KoboServer.from_url(url)
        except AuthError:
            continue
        servers.setdefault(server.base_url, server)
        counts[server.base_url] += 1
    if not counts:
        return GLOBAL_SERVER
    best = max(counts.values())
    first = next(base for base in servers if counts[base] == best)
    return servers[first]


def _unreachable(server: KoboServer) -> AuthError:
    return AuthError(
        AuthErrorKind.UNREACHABLE,
        f"Kobo ({server.label}) cannot be reached. Check your connection and retry.",
    )


def _json(response: Any) -> dict[str, Any] | None:
    try:
        data = response.json()
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _get(
    http: HttpGetter,
    server: KoboServer,
    path: str,
    *,
    headers: dict[str, str],
    auth: tuple[str, str] | None = None,
) -> Any:
    try:
        response = http.get(
            f"{server.base_url}{path}", headers=headers, auth=auth, timeout=TIMEOUT_SECONDS
        )
    except requests.RequestException:
        raise _unreachable(server) from None
    if response.status_code >= 500:
        raise _unreachable(server)
    return response


def _fetch_username(server: KoboServer, token: str, http: HttpGetter) -> str:
    """Verify ``token`` against ``/me/`` and return the account's username."""
    response = _get(
        http,
        server,
        "/me/?format=json",
        headers={"Authorization": f"Token {token}", "Accept": "application/json"},
    )
    if response.status_code in (401, 403):
        raise AuthError(
            AuthErrorKind.INVALID_TOKEN, f"This API key is not valid for {server.label}."
        )
    if response.status_code != 200:
        raise AuthError(AuthErrorKind.UNEXPECTED, f"Kobo answered HTTP {response.status_code}.")
    data = _json(response)
    username = str(data.get("username", "")).strip() if data else ""
    if not username:
        raise AuthError(
            AuthErrorKind.INVALID_SERVER, f"{server.base_url} does not look like a Kobo server."
        )
    return username


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def sign_in_with_token(
    server: KoboServer,
    token: str,
    method: SignInMethod = SignInMethod.API_KEY,
    *,
    http: HttpGetter | None = None,
) -> KoboSession:
    """Verify an API key and return a session for its owner.

    Raises:
        AuthError: ``INVALID_TOKEN``, ``UNREACHABLE``, ``INVALID_SERVER`` or ``UNEXPECTED``.
    """
    token = (token or "").strip()
    if not token:
        raise AuthError(AuthErrorKind.INVALID_TOKEN, "Enter your Kobo API key.")
    username = _fetch_username(server, token, http or requests.Session())
    return KoboSession(
        server=server, username=username, token=token, method=method, signed_in_at=_now()
    )


def sign_in_with_password(
    server: KoboServer,
    username: str,
    password: str,
    *,
    http: HttpGetter | None = None,
) -> KoboSession:
    """Exchange a username and password for the account's API key and return a session.

    The password is sent once, as HTTP Basic auth of the ``/token/`` request, and is not
    kept anywhere afterwards.

    Raises:
        AuthError: ``INVALID_CREDENTIALS``, ``UNREACHABLE``, ``INVALID_SERVER`` or
            ``UNEXPECTED``.
    """
    username = (username or "").strip()
    if not username or not password:
        raise AuthError(AuthErrorKind.INVALID_CREDENTIALS, "Enter your Kobo username and password.")
    http = http or requests.Session()
    response = _get(
        http,
        server,
        "/token/?format=json",
        auth=(username, password),
        headers={"Accept": "application/json"},
    )
    del password
    if response.status_code in (401, 403):
        raise AuthError(AuthErrorKind.INVALID_CREDENTIALS, _INVALID_PASSWORD_MESSAGE)
    if response.status_code != 200:
        raise AuthError(AuthErrorKind.UNEXPECTED, f"Kobo answered HTTP {response.status_code}.")
    data = _json(response)
    token = str(data.get("token", "")).strip() if data else ""
    if not token:
        raise AuthError(
            AuthErrorKind.INVALID_SERVER, f"{server.base_url} does not look like a Kobo server."
        )
    canonical = _fetch_username(server, token, http)
    return KoboSession(
        server=server,
        username=canonical,
        token=token,
        method=SignInMethod.PASSWORD,
        signed_in_at=_now(),
    )
