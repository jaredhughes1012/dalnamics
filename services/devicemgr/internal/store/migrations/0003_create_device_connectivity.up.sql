-- Kept apart from devicemgr.devices because it is written on every heartbeat:
-- updates here don't touch devices.updated_at, and the registration record
-- stays cold. A device with no row has never connected and is offline.
CREATE TABLE devicemgr.device_connectivity (
    device_id    uuid PRIMARY KEY REFERENCES devicemgr.devices (id) ON DELETE CASCADE,
    last_seen_at timestamptz NOT NULL,
    -- The device is online while online_until is in the future. Each heartbeat
    -- pushes it out by DEVICEMGR_OFFLINE_AFTER, so a device goes offline on its
    -- own once heartbeats stop, even while devicemgr is down.
    online_until timestamptz NOT NULL
);

COMMENT ON TABLE devicemgr.device_connectivity IS
    'Whether each device is connected. Each heartbeat records last_seen_at and extends online_until by DEVICEMGR_OFFLINE_AFTER (throttled); a device is online while online_until is in the future.';
