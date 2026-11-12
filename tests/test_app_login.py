"""UI tests for the "Kobo account" sidebar panel (Streamlit AppTest, no network)."""

from __future__ import annotations

import io
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
from PIL import Image
from streamlit.testing.v1 import AppTest

from evaluate_kobo_form_images import kobo_auth
from evaluate_kobo_form_images.kobo_auth import (
    GLOBAL_SERVER,
    AuthError,
    AuthErrorKind,
    KoboServer,
    KoboSession,
    SignInMethod,
)
from evaluate_kobo_form_images.kobo_client import (
    EXPIRED_MESSAGE,
    FetchFailure,
    ImageFetchError,
    KoboImageClient,
)

APP = Path(__file__).resolve().parents[1] / "src" / "evaluate_kobo_form_images" / "app.py"
INVALID = "Invalid Kobo username or password."
FETCH_MODE = {"signed_in": "image"}


def _jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), (0, 128, 0)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _session(username: str = "jdoe", method: SignInMethod = SignInMethod.PASSWORD) -> KoboSession:
    return KoboSession(
        server=GLOBAL_SERVER,
        username=username,
        token="0123456789abcdef0123456789abcdef01234567",
        method=method,
        signed_in_at="2026-11-12T14:02:00+00:00",
    )


@pytest.fixture
def app_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, form_path: Path, export_path: Path
) -> Path:
    """Isolated folders with the synthetic form/export; images never hit the network."""
    for name, source in (("forms", form_path), ("data", export_path)):
        folder = tmp_path / name
        folder.mkdir()
        shutil.copy(source, folder / source.name)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KOBO_FORMS_DIR", str(tmp_path / "forms"))
    monkeypatch.setenv("KOBO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("EVALUATIONS_DIR", str(tmp_path / "evaluations"))
    monkeypatch.setenv("IMAGE_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("KOBO_API_TOKEN", "")

    def fake_fetch(self: KoboImageClient, url: str) -> bytes:
        del url
        if self.kobo_session is None:
            raise ImageFetchError(FetchFailure.NOT_SIGNED_IN, "Sign in to your Kobo account.")
        if FETCH_MODE["signed_in"] == "expired":
            raise ImageFetchError(FetchFailure.ACCESS_EXPIRED, EXPIRED_MESSAGE)
        return _jpeg()

    FETCH_MODE["signed_in"] = "image"

    monkeypatch.setattr(KoboImageClient, "fetch", fake_fetch)
    monkeypatch.setattr(KoboImageClient, "is_cached", lambda self, url: True)
    return tmp_path


def _open_app() -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    at.selectbox(key="form_choice").select("test_form.xlsx").run()
    at.selectbox(key="data_choice").select("test_export.xlsx").run()
    return at


def _sidebar_text(at: AppTest) -> str:
    parts = [e.value for e in at.sidebar.success]
    parts += [e.value for e in at.sidebar.error]
    parts += [e.value for e in at.sidebar.warning]
    return "\n".join(str(p) for p in parts)


def _sign_in(at: AppTest, username: str = "jdoe", password: str = "pw") -> None:
    at.text_input(key="kobo_username").input(username)
    at.text_input(key="kobo_password").input(password)
    at.button(key="kobo_password_submit").click().run()


def _patch_password(
    monkeypatch: pytest.MonkeyPatch, impl: Callable[[KoboServer, str, str], KoboSession]
) -> None:
    monkeypatch.setattr(kobo_auth, "sign_in_with_password", impl)


# --------------------------------------------------------------------------- US1
@pytest.mark.usefixtures("app_env")
def test_password_sign_in_shows_user_and_prefills_evaluator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    _patch_password(monkeypatch, lambda server, username, password: _session(username))
    at = _open_app()

    # Act
    _sign_in(at)

    # Assert
    assert not at.exception
    assert "Signed in as **jdoe** on Global (kf.kobotoolbox.org)" in _sidebar_text(at)
    assert at.text_input(key="evaluator").value == "jdoe"


@pytest.mark.usefixtures("app_env")
def test_password_sign_in_failure_shows_message_and_stores_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(server: KoboServer, username: str, password: str) -> KoboSession:
        raise AuthError(AuthErrorKind.INVALID_CREDENTIALS, INVALID)

    _patch_password(monkeypatch, fail)
    at = _open_app()

    _sign_in(at, password="wrong-pass")

    assert INVALID in _sidebar_text(at)
    assert "kobo_session" not in at.session_state
    assert at.text_input(key="kobo_password").value == ""


@pytest.mark.usefixtures("app_env")
def test_unsigned_user_is_invited_to_sign_in() -> None:
    at = _open_app()
    assert any("Sign in to your Kobo account" in str(i.value) for i in at.info)


# --------------------------------------------------------------------------- US2
@pytest.mark.usefixtures("app_env")
def test_sign_out_and_switch_account(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    _patch_password(monkeypatch, lambda server, username, password: _session(username))
    at = _open_app()
    _sign_in(at, username="first")

    # Act
    at.button(key="kobo_sign_out").click().run()

    # Assert
    assert "kobo_session" not in at.session_state
    assert "kobo_client" not in at.session_state or (
        at.session_state["kobo_client"].kobo_session is None
    )
    _sign_in(at, username="second")
    assert "Signed in as **second**" in _sidebar_text(at)


@pytest.mark.usefixtures("app_env")
def test_expired_access_signs_out_with_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_password(monkeypatch, lambda server, username, password: _session(username))
    FETCH_MODE["signed_in"] = "expired"
    at = _open_app()

    _sign_in(at)  # the stubbed download then answers "access expired"

    assert "kobo_session" not in at.session_state
    assert EXPIRED_MESSAGE in _sidebar_text(at)


# --------------------------------------------------------------------------- US3
@pytest.mark.usefixtures("app_env")
def test_api_key_tab_success_and_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def sign_in(server: KoboServer, token: str, method: SignInMethod, **_: object) -> KoboSession:
        if token != "good":
            raise AuthError(AuthErrorKind.INVALID_TOKEN, "This API key is not valid for X.")
        return _session("keyuser", method)

    monkeypatch.setattr(kobo_auth, "sign_in_with_token", sign_in)
    at = _open_app()

    at.text_input(key="kobo_api_key").input("bad")
    at.button(key="kobo_key_submit").click().run()
    assert "This API key is not valid for X." in _sidebar_text(at)

    at.text_input(key="kobo_api_key").input("good")
    at.button(key="kobo_key_submit").click().run()
    assert "Signed in as **keyuser**" in _sidebar_text(at)


@pytest.mark.usefixtures("app_env")
def test_environment_key_signs_in_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[SignInMethod] = []

    def sign_in(server: KoboServer, token: str, method: SignInMethod, **_: object) -> KoboSession:
        calls.append(method)
        raise AuthError(AuthErrorKind.INVALID_TOKEN, "This API key is not valid for X.")

    monkeypatch.setenv("KOBO_API_TOKEN", "from-env")
    monkeypatch.setattr(kobo_auth, "sign_in_with_token", sign_in)

    at = _open_app()
    at.run()

    assert calls == [SignInMethod.ENVIRONMENT]
    assert "This API key is not valid for X." in _sidebar_text(at)
