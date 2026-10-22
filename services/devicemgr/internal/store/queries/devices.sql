-- name: GetActiveRegistrationCode :one
-- Reads the api's schema, which devicemgr may read but never writes. A code
-- already redeemed is still returned; CreateDevice rejects its reuse.
SELECT id, user_id FROM public.device_registration_codes
WHERE code_hash = @code_hash AND expires_at > now();

-- name: CreateDevice :one
INSERT INTO devicemgr.devices (user_id, type, name, secret_hash, registration_code_id)
VALUES (@user_id, @type, @name, @secret_hash, @registration_code_id)
RETURNING id;

-- name: GetDeviceSecretHash :one
SELECT secret_hash FROM devicemgr.devices WHERE id = @id;

-- name: MarkDeviceSeen :execrows
-- Records a heartbeat: the device is online for offline_after_seconds from now.
-- Inserts only for a known device, so an unknown ID is a no-op. Skips a row
-- seen within min_interval_seconds, which bounds writes across devicemgr
-- instances.
INSERT INTO devicemgr.device_connectivity (device_id, last_seen_at, online_until)
SELECT id, now(), now() + make_interval(secs => @offline_after_seconds::float8)
FROM devicemgr.devices WHERE id = @device_id
ON CONFLICT (device_id) DO UPDATE
SET last_seen_at = EXCLUDED.last_seen_at, online_until = EXCLUDED.online_until
WHERE device_connectivity.last_seen_at < now() - make_interval(secs => @min_interval_seconds::float8);
