# Contract: Kobo HTTP endpoints used by the app

External interface consumed by `kobo_auth.py` and `kobo_client.py`. `{server}` is a
normalized `KoboServer.base_url`. All requests use a 30 s timeout and HTTPS.

## 1. Exchange username + password for an API key

```http
GET {server}/token/?format=json
Authorization: Basic base64(username:password)
Accept: application/json
```

| Response | Meaning | App result |
|----------|---------|------------|
| `200 {"token": "<key>"}` | Valid credentials | Continue with §2 using `<key>` |
| `401 {"detail": "Invalid username/password."}` | Wrong pair, SSO-only or MFA account | `AuthError(INVALID_CREDENTIALS)` |
| `401/403` other | Credentials not accepted | `AuthError(INVALID_CREDENTIALS)` |
| `5xx`, timeout, connection error | Server unavailable | `AuthError(UNREACHABLE)` |
| `200` without `token` / non-JSON | Not a Kobo server | `AuthError(INVALID_SERVER)` |

The password is used only for this request and is never retained.

## 2. Verify an API key and read the username

```http
GET {server}/me/?format=json
Authorization: Token <key>
Accept: application/json
```

| Response | Meaning | App result |
|----------|---------|------------|
| `200 {"username": "<user>", ...}` | Valid key | `KoboSession(server, user, key, method)` |
| `401 {"detail": "Invalid token."}` | Invalid / regenerated key | `AuthError(INVALID_TOKEN)` |
| `200` without `username` / non-JSON | Not a Kobo server | `AuthError(INVALID_SERVER)` |
| `5xx`, timeout, connection error | Server unavailable | `AuthError(UNREACHABLE)` |

## 3. Download an attachment (existing, behavior refined)

```http
GET {image_url}
Authorization: Token <key>      # ONLY if scheme://host(image_url) == server
```

| Response | Credentials sent | `ImageFetchError.reason` |
|----------|------------------|--------------------------|
| `200` image bytes | any | — (decoded, cached) |
| `401/403/404` | no | `NOT_SIGNED_IN` |
| `401` | yes | `ACCESS_EXPIRED` |
| `403/404` | yes | `NO_ACCESS` |
| `5xx`, timeout, connection error | any | `UNREACHABLE` |
| `200` not decodable | any | `NOT_AN_IMAGE` |

Verified on 2026-11-12 against `kf.kobotoolbox.org` and `eu.kobotoolbox.org` for the
unauthenticated / invalid cases of §1 and §2.
