-- name: DeleteExpiredDeviceRegistrationCodes :exec
DELETE FROM device_registration_codes WHERE expires_at <= now();

-- name: CreateDeviceRegistrationCode :exec
INSERT INTO device_registration_codes (code_hash, user_id, expires_at)
VALUES (@code_hash, @user_id, @expires_at);

-- name: ListDevicesByUser :many
-- Reads devicemgr's schema, which the api may read but never writes.
SELECT id, type, name, created_at FROM devicemgr.devices
WHERE user_id = @user_id
ORDER BY created_at DESC, id;
