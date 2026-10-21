CREATE TABLE device_registration_codes (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code_hash  bytea NOT NULL UNIQUE,
    user_id    uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX device_registration_codes_user_id_idx ON device_registration_codes (user_id);

COMMENT ON TABLE device_registration_codes IS
    'Short-lived, single-use codes that register a device to the user who requested them. devicemgr reads a code when a device redeems it and records the redemption in devicemgr.devices.registration_code_id, which is unique, so the api never marks codes used. Only the SHA-256 of the normalized code is stored.';
