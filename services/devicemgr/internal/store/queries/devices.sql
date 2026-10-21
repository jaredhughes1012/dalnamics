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
-- Marks a device online. Inserts only for a known device, so an unknown ID is a
-- no-op. Skips the write while the row is already online and was seen within
-- min_interval_seconds, which bounds writes across devicemgr instances.
INSERT INTO devicemgr.device_connectivity (device_id, online, last_seen_at)
SELECT id, true, now() FROM devicemgr.devices WHERE id = @device_id
ON CONFLICT (device_id) DO UPDATE SET online = true, last_seen_at = now()
WHERE NOT device_connectivity.online
   OR device_connectivity.last_seen_at < now() - make_interval(secs => @min_interval_seconds::float8);

-- name: MarkStaleDevicesOffline :execrows
UPDATE devicemgr.device_connectivity SET online = false
WHERE online AND last_seen_at < now() - make_interval(secs => @offline_after_seconds::float8);
