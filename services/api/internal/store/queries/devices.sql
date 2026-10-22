-- name: DeleteExpiredDeviceRegistrationCodes :exec
DELETE FROM device_registration_codes WHERE expires_at <= now();

-- name: CreateDeviceRegistrationCode :exec
INSERT INTO device_registration_codes (code_hash, user_id, expires_at)
VALUES (@code_hash, @user_id, @expires_at);

-- name: SeedDeviceRegistrationCode :execrows
-- Gives the code a new id on every call, so a code already redeemed (whose old
-- id devicemgr.devices holds) can be redeemed once more.
INSERT INTO device_registration_codes (code_hash, user_id, expires_at)
SELECT @code_hash::bytea, id, 'infinity' FROM users WHERE email = @email
ON CONFLICT (code_hash) DO UPDATE
SET id = gen_random_uuid(), user_id = EXCLUDED.user_id, expires_at = EXCLUDED.expires_at;

-- name: ListDevicesByUser :many
-- Reads devicemgr's schema, which the api may read but never writes. A device
-- with no connectivity row has never connected, so it is offline.
SELECT d.id, d.type, d.name, d.created_at,
       coalesce(c.online_until > now(), false)::boolean AS online, c.last_seen_at
FROM devicemgr.devices d
LEFT JOIN devicemgr.device_connectivity c ON c.device_id = d.id
WHERE d.user_id = @user_id
ORDER BY d.created_at DESC, d.id;

-- name: GetDeviceForUser :one
-- Matches only the user's own devices, so another user's device looks unknown.
SELECT d.id, d.type, d.name, d.created_at,
       coalesce(c.online_until > now(), false)::boolean AS online, c.last_seen_at
FROM devicemgr.devices d
LEFT JOIN devicemgr.device_connectivity c ON c.device_id = d.id
WHERE d.id = @id AND d.user_id = @user_id;
