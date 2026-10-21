-- Kept apart from devicemgr.devices because it is written on device traffic:
-- updates here don't touch devices.updated_at, and the registration record
-- stays cold. A device with no row has never connected and is offline.
CREATE TABLE devicemgr.device_connectivity (
    device_id    uuid PRIMARY KEY REFERENCES devicemgr.devices (id) ON DELETE CASCADE,
    online       boolean NOT NULL,
    last_seen_at timestamptz NOT NULL
);

-- The sweep scans only online devices, by how long they've been silent.
CREATE INDEX device_connectivity_online_last_seen_at_idx
    ON devicemgr.device_connectivity (last_seen_at) WHERE online;

COMMENT ON TABLE devicemgr.device_connectivity IS
    'Whether each device is connected. Any MQTT message from a device marks it online and records last_seen_at (throttled); a periodic sweep marks devices offline once they have been silent past DEVICEMGR_OFFLINE_AFTER.';
