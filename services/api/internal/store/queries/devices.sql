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
-- Reads devicemgr's schema, which the api may read but never writes.
SELECT id, type, name, created_at FROM devicemgr.devices
WHERE user_id = @user_id
ORDER BY created_at DESC, id;
