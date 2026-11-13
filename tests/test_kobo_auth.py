"""Tests for Kobo sign-in (servers, sessions, password and API-key flows) with stubbed HTTP."""

from __future__ import annotations

import dataclasses

import pytest
import requests

from evaluate_kobo_form_images.kobo_auth import (
    EU_SERVER,
    GLOBAL_SERVER,
    AuthError,
    AuthErrorKind,
    KoboServer,
    KoboSession,
    SignInMethod,
    detect_server,
    sign_in_with_password,
    sign_in_with_token,
)
from tests.fake_http import FakeHttp, FakeResponse

TOKEN = "0123456789abcdef0123456789abcdef01234567"
INVALID_PASSWORD_MESSAGE = (
    "Invalid Kobo username or password. If you sign in to Kobo with your organization (SSO) "
    "or use two-factor authentication, use an API key instead."
)


# --------------------------------------------------------------------------- KoboServer
def test_server_from_url_normalizes_to_scheme_and_host() -> None:
    server = KoboServer.from_url("https://KF.kobotoolbox.org/api/v2/assets/x/")
    assert server == GLOBAL_SERVER
    assert server.base_url == "https://kf.kobotoolbox.org"
    assert server.label == "Global (kf.kobotoolbox.org)"


def test_server_labels_known_and_custom_hosts() -> None:
    assert KoboServer.from_url("https://eu.kobotoolbox.org/").label == "EU (eu.kobotoolbox.org)"
    custom = KoboServer.from_url("https://kobo.example.org:8443/path")
    assert custom.base_url == "https://kobo.example.org:8443"
    assert custom.label == "kobo.example.org:8443"


@pytest.mark.parametrize(
    "url",
    ["", "kf.kobotoolbox.org", "ftp://kf.kobotoolbox.org", "http://kf.kobotoolbox.org", "https://"],
)
def test_server_from_url_rejects_invalid_addresses(url: str) -> None:
    with pytest.raises(AuthError) as info:
        KoboServer.from_url(url)
    assert info.value.kind is AuthErrorKind.INVALID_SERVER
    assert info.value.message == (
        "Enter a valid Kobo server address, e.g. https://kf.kobotoolbox.org"
    )


def test_server_allows_plain_http_on_localhost() -> None:
    assert KoboServer.from_url("http://localhost:8000/x").base_url == "http://localhost:8000"


def test_server_owns_only_same_scheme_and_host() -> None:
    assert GLOBAL_SERVER.owns("https://kf.kobotoolbox.org/api/v2/assets/a/data/1/attachments/b/")
    assert not GLOBAL_SERVER.owns("https://eu.kobotoolbox.org/api/v2/assets/a/")
    assert not GLOBAL_SERVER.owns("http://kf.kobotoolbox.org/api/")
    assert not GLOBAL_SERVER.owns("https://kf.kobotoolbox.org.evil.com/api/")
    assert not GLOBAL_SERVER.owns("not a url")


# --------------------------------------------------------------------------- detect_server
def test_detect_server_returns_most_common_host() -> None:
    urls = [
        "https://eu.kobotoolbox.org/a",
        "https://kf.kobotoolbox.org/b",
        "https://eu.kobotoolbox.org/c",
        "",
        "garbage",
    ]
    assert detect_server(urls) == EU_SERVER


def test_detect_server_breaks_ties_by_first_seen_and_defaults_to_global() -> None:
    assert detect_server(["https://eu.kobotoolbox.org/a", "https://kf.kobotoolbox.org/b"]) == (
        EU_SERVER
    )
    assert detect_server([]) == GLOBAL_SERVER


# --------------------------------------------------------------------------- KoboSession
def _session() -> KoboSession:
    return KoboSession(
        server=GLOBAL_SERVER,
        username="jdoe",
        token=TOKEN,
        method=SignInMethod.API_KEY,
        signed_in_at="2026-11-12T14:00:00+00:00",
    )


def test_session_repr_masks_token() -> None:
    session = _session()
    for text in (repr(session), str(session)):
        assert TOKEN not in text
        assert "****4567" in text


def test_session_is_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        _session().username = "other"  # ty: ignore[invalid-assignment]


# --------------------------------------------------------------------------- password sign-in
def test_sign_in_with_password_exchanges_credentials_for_token() -> None:
    # Arrange
    http = FakeHttp(
        [
            FakeResponse(200, {"token": TOKEN}),
            FakeResponse(200, {"username": "jdoe", "email": "x"}),
        ]
    )

    # Act
    session = sign_in_with_password(GLOBAL_SERVER, "JDoe", "s3cret!", http=http)

    # Assert
    assert session.username == "jdoe"
    assert session.token == TOKEN
    assert session.method is SignInMethod.PASSWORD
    assert session.server == GLOBAL_SERVER
    token_call, me_call = http.calls
    assert token_call.url == "https://kf.kobotoolbox.org/token/?format=json"
    assert token_call.auth == ("JDoe", "s3cret!")
    assert "Authorization" not in token_call.headers
    assert me_call.url == "https://kf.kobotoolbox.org/me/?format=json"
    assert me_call.headers["Authorization"] == f"Token {TOKEN}"
    assert me_call.auth is None


def test_sign_in_with_password_rejects_wrong_credentials_without_echoing_password() -> None:
    http = FakeHttp([FakeResponse(401, {"detail": "Invalid username/password."})])
    with pytest.raises(AuthError) as info:
        sign_in_with_password(GLOBAL_SERVER, "jdoe", "s3cret!", http=http)
    assert info.value.kind is AuthErrorKind.INVALID_CREDENTIALS
    assert info.value.message == INVALID_PASSWORD_MESSAGE
    assert "s3cret!" not in repr(info.value)
    assert "s3cret!" not in str(info.value)


@pytest.mark.parametrize(("username", "password"), [("", "x"), ("jdoe", ""), ("  ", "x")])
def test_sign_in_with_password_requires_both_fields_without_http(
    username: str, password: str
) -> None:
    http = FakeHttp()
    with pytest.raises(AuthError) as info:
        sign_in_with_password(GLOBAL_SERVER, username, password, http=http)
    assert info.value.kind is AuthErrorKind.INVALID_CREDENTIALS
    assert http.calls == []


def test_sign_in_with_password_detects_non_kobo_server() -> None:
    http = FakeHttp([FakeResponse(200, {"hello": "world"})])
    with pytest.raises(AuthError) as info:
        sign_in_with_password(GLOBAL_SERVER, "jdoe", "pw", http=http)
    assert info.value.kind is AuthErrorKind.INVALID_SERVER


@pytest.mark.parametrize(
    "failure", [requests.ConnectionError("down"), requests.Timeout("slow"), FakeResponse(503)]
)
def test_sign_in_with_password_reports_unreachable_server(
    failure: FakeResponse | Exception,
) -> None:
    http = FakeHttp([failure])
    with pytest.raises(AuthError) as info:
        sign_in_with_password(GLOBAL_SERVER, "jdoe", "pw", http=http)
    assert info.value.kind is AuthErrorKind.UNREACHABLE
    assert info.value.message == (
        "Kobo (Global (kf.kobotoolbox.org)) cannot be reached. Check your connection and retry."
    )


# --------------------------------------------------------------------------- token sign-in
def test_sign_in_with_token_reads_username_from_me() -> None:
    http = FakeHttp([FakeResponse(200, {"username": "jdoe"})])
    session = sign_in_with_token(EU_SERVER, f"  {TOKEN}\n", SignInMethod.ENVIRONMENT, http=http)
    assert session.username == "jdoe"
    assert session.token == TOKEN
    assert session.method is SignInMethod.ENVIRONMENT
    assert http.calls[0].url == "https://eu.kobotoolbox.org/me/?format=json"
    assert http.calls[0].headers["Authorization"] == f"Token {TOKEN}"


def test_sign_in_with_token_rejects_invalid_key() -> None:
    http = FakeHttp([FakeResponse(401, {"detail": "Invalid token."})])
    with pytest.raises(AuthError) as info:
        sign_in_with_token(GLOBAL_SERVER, "bad", http=http)
    assert info.value.kind is AuthErrorKind.INVALID_TOKEN
    assert info.value.message == "This API key is not valid for Global (kf.kobotoolbox.org)."
    assert "bad" not in info.value.message


@pytest.mark.parametrize("token", ["", "   ", "\n"])
def test_sign_in_with_token_requires_a_key_without_http(token: str) -> None:
    http = FakeHttp()
    with pytest.raises(AuthError) as info:
        sign_in_with_token(GLOBAL_SERVER, token, http=http)
    assert info.value.kind is AuthErrorKind.INVALID_TOKEN
    assert http.calls == []


def test_sign_in_with_token_reports_unexpected_status_and_non_json() -> None:
    with pytest.raises(AuthError) as info:
        sign_in_with_token(GLOBAL_SERVER, TOKEN, http=FakeHttp([FakeResponse(418)]))
    assert info.value.kind is AuthErrorKind.UNEXPECTED
    with pytest.raises(AuthError) as info:
        sign_in_with_token(GLOBAL_SERVER, TOKEN, http=FakeHttp([FakeResponse(200, None)]))
    assert info.value.kind is AuthErrorKind.INVALID_SERVER
