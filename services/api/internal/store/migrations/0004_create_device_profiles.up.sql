CREATE TABLE device_profiles (
    -- devicemgr.devices(id). No foreign key, so neither service's migrations
    -- depend on the other's.
    device_id  uuid PRIMARY KEY,
    name       text CHECK (name IS NULL OR char_length(name) BETWEEN 1 AND 100),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER device_profiles_set_updated_at
    BEFORE UPDATE ON device_profiles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE device_profiles IS
    'User-facing display data for devicemgr''s devices, owned by the api and overlaid on devicemgr.devices when read. A null field falls back to devicemgr''s value; devicemgr.devices.name keeps the name the device registered with. Rows are created on the first change, so a device may have none.';
