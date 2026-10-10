-- name: CreateUser :one
INSERT INTO users (email, name, password_hash)
VALUES (@email, @name, @password_hash)
RETURNING *;

-- name: CreateUserIfNotExists :exec
INSERT INTO users (email, name)
VALUES (@email, @name)
ON CONFLICT (email) DO NOTHING;

-- name: GetUserByEmail :one
SELECT * FROM users WHERE email = @email;

-- name: GetUserByID :one
SELECT * FROM users WHERE id = @id;

-- name: CreateSession :one
INSERT INTO sessions (user_id, client, refresh_token_hash, expires_at)
VALUES (@user_id, @client, @refresh_token_hash, @expires_at)
RETURNING *;

-- name: GetActiveSession :one
SELECT * FROM sessions
WHERE id = @id AND revoked_at IS NULL AND expires_at > now();

-- name: RotateSessionRefreshToken :one
-- Atomically swaps the refresh token, so a token can only be redeemed once.
UPDATE sessions
SET refresh_token_hash = @new_refresh_token_hash, expires_at = @expires_at
WHERE refresh_token_hash = @refresh_token_hash
  AND revoked_at IS NULL
  AND expires_at > now()
RETURNING *;

-- name: RevokeSession :exec
UPDATE sessions SET revoked_at = now()
WHERE id = @id AND revoked_at IS NULL;

-- name: CreateCLIAuthCode :exec
INSERT INTO cli_auth_codes (code_hash, user_id, code_challenge, redirect_uri, expires_at)
VALUES (@code_hash, @user_id, @code_challenge, @redirect_uri, @expires_at);

-- name: UseCLIAuthCode :one
-- Marks a code used and returns it; returns no rows if it is unknown, used, or expired.
UPDATE cli_auth_codes SET used_at = now()
WHERE code_hash = @code_hash AND used_at IS NULL AND expires_at > now()
RETURNING *;
