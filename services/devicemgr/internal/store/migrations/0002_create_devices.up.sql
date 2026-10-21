-- devicemgr keeps its own copy of the api's set_updated_at(), because the two
-- services migrate independently and in no fixed order.
CREATE FUNCTION devicemgr.set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE devicemgr.devices (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    -- public.users(id). No foreign key, so neither service's migrations depend
    -- on the other's.
    user_id              uuid NOT NULL,
    type                 text NOT NULL,
    name                 text NOT NULL,
    secret_hash          bytea NOT NULL UNIQUE,
    -- public.device_registration_codes(id). Unique, so each code registers at
    -- most one device.
    registration_code_id uuid NOT NULL UNIQUE,
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX devices_user_id_idx ON devicemgr.devices (user_id);

CREATE TRIGGER devices_set_updated_at
    BEFORE UPDATE ON devicemgr.devices
    FOR EACH ROW EXECUTE FUNCTION devicemgr.set_updated_at();

COMMENT ON TABLE devicemgr.devices IS
    'Hardware devices registered to a user by redeeming a device registration code. A device authenticates to the MQTT broker with its id and a secret; only the SHA-256 of the secret is stored.';
