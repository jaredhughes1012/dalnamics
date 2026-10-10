# Authentication

Accounts are identified by email. Clients authenticate to the api with short-lived bearer **access tokens** and renew them with single-use **refresh tokens**. The api is the only component that reads or writes auth data.

## Accounts

- Users sign up with email, name, and password (`POST /auth/signup`) and log in with email and password (`POST /auth/login`).
- Emails are trimmed, lowercased, and unique (`citext`).
- Passwords are 8–128 characters and stored as argon2id hashes (PHC string format).
- Unknown emails and wrong passwords produce the same `invalid_credentials` error and take the same time to reject.
- `users.password_hash` is NULL for accounts that have no password (dev users, and future external identity providers). Those accounts cannot use password login.

## Sessions and tokens

Every sign-in creates a row in `sessions`, tagged with the client (`studio` or `cli`).

| Token | Format | Lifetime | Stored server-side as |
|---|---|---|---|
| Access | HS256 JWT; `sub` = user id, `sid` = session id | 15 min | not stored |
| Refresh | 32 random bytes, base64url | until the session expires, 7 days after sign-in | SHA-256 in `sessions.refresh_token_hash` |

- **Authenticated requests** send `Authorization: Bearer <access>`. The api verifies the JWT and confirms the session is still active, so logout takes effect immediately.
- **Refresh** (`POST /auth/refresh`) atomically swaps the session's refresh hash for a new one. Each refresh token therefore works once. Refreshing does not extend the session, so users sign in again after 7 days.
- **Reuse detection**: a trigger records every rotated-away hash in `rotated_refresh_tokens`. Presenting one again means the token was copied, so the api revokes its session. The legitimate client and whoever copied the token both have to sign in again.
- **Logout** (`POST /auth/logout`) revokes the session, which invalidates both of its tokens.
- **Clients** refresh once when they get a 401 and retry the request. Because reuse revokes the session, a client must never present a refresh token that a concurrent refresh already rotated:
  - Studio shares one in-flight refresh across concurrent requests. Tabs take turns through a Web Lock, and each tab adopts tokens another tab already rotated. Tabs follow each other's refreshes and sign-outs through `storage` events.
  - The cli serializes refreshes across processes with a lock file in its config directory, then persists the rotated pair. The credentials file is also locked while being rewritten.

## Dev users

When the api runs with `DEBUG=true`, each address in `DEV_EMAILS` (comma separated) is created at startup if it doesn't exist. Dev users have no password.

- `GET /auth/dev-users` lists the addresses, and studio renders them as one-click login buttons.
- `POST /auth/dev-login` signs one in.
- Without `DEBUG=true`, both endpoints return 404 and `DEV_EMAILS` is ignored.
- E2E tests and `cli auth login --dev <email>` use the same endpoint.

## CLI login

`cli auth login` follows the OAuth native-app pattern ([RFC 8252](https://datatracker.ietf.org/doc/html/rfc8252)): a loopback redirect with PKCE (S256). The browser does the login, and the cli gets its own session.

```mermaid
sequenceDiagram
    participant CLI as cli
    participant B as Browser (studio)
    participant API as api
    CLI->>CLI: verifier, challenge = S256(verifier), state; listen on 127.0.0.1:<port>
    CLI->>B: open /cli-login?redirect_uri&code_challenge&state
    B->>B: log in if needed, user clicks Authorize
    B->>API: POST /auth/cli/authorize {code_challenge, redirect_uri} (bearer)
    API-->>B: one-time code (60s, stored as SHA-256)
    B->>CLI: GET http://127.0.0.1:<port>/callback?code&state
    CLI->>API: POST /auth/cli/token {code, code_verifier, redirect_uri}
    API-->>CLI: user + tokens for a new cli session
```

- The api accepts only `http` loopback redirect URIs with an explicit port. Studio checks the URI before redirecting, including on Cancel.
- The code is single use and bound to the challenge and redirect URI. A code intercepted without the verifier is useless. A redemption with the wrong verifier or redirect URI is rejected without using up the code.
- The cli ignores callbacks whose `state` doesn't match.

## CLI credential storage

Credentials are keyed by api URL, so one machine can be logged in to several environments.

- **Default:** the OS keychain (macOS Keychain, Linux Secret Service, Windows Credential Manager), under service `dalnamics-cli`.
- **No keychain** (e.g. headless containers): an owner-only (0600) file at `<user config dir>/dalnamics/credentials.json`.
- `DALNAMICS_CREDENTIAL_STORE=keyring|file` forces a backend, and `DALNAMICS_CONFIG_DIR` relocates the file and the cli's lock files.

## Studio session storage

Studio keeps the user and token pair in localStorage (`dalnamics-auth`) through a persisted zustand store, and attaches the access token to every request made with the `api` client.

## Configuration

| Variable | Used by | Purpose |
|---|---|---|
| `JWT_SECRET` | api | Signs access tokens; at least 32 bytes |
| `DATABASE_URL` | api | Postgres connection string |
| `DEBUG` | api | Enables dev users |
| `DEV_EMAILS` | api | Dev user addresses (only read when `DEBUG=true`) |
| `DALNAMICS_API_URL` / `--api-url` | cli | api base URL |
| `DALNAMICS_STUDIO_URL` / `--studio-url` | cli | studio base URL for browser login |
