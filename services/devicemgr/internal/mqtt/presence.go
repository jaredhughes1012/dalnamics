package mqtt

import (
	"context"
	"log/slog"

	"github.com/google/uuid"

	"dalnamics/services/devicemgr/internal/devices"
)

// Seer records a heartbeat from a device.
type Seer interface {
	MarkSeen(ctx context.Context, id uuid.UUID) error
}

// Presence marks devices online when they send heartbeats.
type Presence struct {
	devices Seer
	logger  *slog.Logger
}

// NewPresence returns a Presence that records heartbeats with s.
func NewPresence(s Seer, logger *slog.Logger) *Presence {
	return &Presence{devices: s, logger: logger}
}

// Handle records a heartbeat a device published on topic. Topics other than
// devices/{device id}/heartbeat are ignored.
func (p *Presence) Handle(ctx context.Context, topic string) {
	id, ok := devices.DeviceIDFromHeartbeatTopic(topic)
	if !ok {
		return
	}
	if err := p.devices.MarkSeen(ctx, id); err != nil {
		p.logger.ErrorContext(ctx, "mark device seen", "device_id", id, "err", err)
	}
}
