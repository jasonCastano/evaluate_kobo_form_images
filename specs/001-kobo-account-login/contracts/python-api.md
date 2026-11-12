# Contract: Python module interface

Public interface the Streamlit UI relies on. Business logic stays out of `app.py`
(Principle IV). Signatures are normative; bodies are implementation.

## `evaluate_kobo_form_images.kobo_auth` (new)

```python
GLOBAL_SERVER: KoboServer          # https://kf.kobotoolbox.org
EU_SERVER: KoboServer              # https://eu.kobotoolbox.org
KNOWN_SERVERS: tuple[KoboServer, ...]

class AuthErrorKind(StrEnum):
    INVALID_CREDENTIALS, INVALID_TOKEN, UNREACHABLE, INVALID_SERVER, UNEXPECTED

class AuthError(Exception):
    kind: AuthErrorKind
    message: str                   # plain-language English (research R5)

@dataclass(frozen=True)
class KoboServer:
    base_url: str
    label: str
    @classmethod
    def from_url(cls, url: str) -> KoboServer          # raises AuthError(INVALID_SERVER)
    def owns(self, url: str) -> bool                   # same scheme://host[:port]

class SignInMethod(StrEnum):
    PASSWORD, API_KEY, ENVIRONMENT

@dataclass(frozen=True)
class KoboSession:
    server: KoboServer
    username: str
    token: str                     # repr masked
    method: SignInMethod
    signed_in_at: str

def detect_server(urls: Iterable[str]) -> KoboServer  # most common host; default GLOBAL

def sign_in_with_password(
    server: KoboServer, username: str, password: str, *, http: requests.Session | None = None
) -> KoboSession                   # raises AuthError

def sign_in_with_token(
    server: KoboServer, token: str, method: SignInMethod = SignInMethod.API_KEY,
    *, http: requests.Session | None = None
) -> KoboSession                   # raises AuthError
```

Rules: empty username/password/token → `AuthError(INVALID_CREDENTIALS | INVALID_TOKEN)`
without any network call; no function logs or stores the password or token.

## `evaluate_kobo_form_images.kobo_client` (changed)

```python
class FetchFailure(StrEnum):
    NOT_SIGNED_IN, ACCESS_EXPIRED, NO_ACCESS, UNREACHABLE, NOT_AN_IMAGE

class ImageFetchError(RuntimeError):
    reason: FetchFailure

class KoboImageClient:
    def __init__(self, session: KoboSession | None, cache_dir: Path, timeout: int = 30) -> None
    def is_cached(self, url: str) -> bool
    def fetch(self, url: str) -> bytes   # cache first; token only if session.server.owns(url)
```

Breaking change: the constructor takes a `KoboSession | None` instead of a raw token string.
Cached images are returned even when `session` is `None` (FR-011).
