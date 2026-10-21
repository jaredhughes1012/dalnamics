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
