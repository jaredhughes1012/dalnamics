package mqtt

import (
	"context"
	"log/slog"

	"github.com/google/uuid"

	"dalnamics/services/devicemgr/internal/devices"
)

// Seer records that a device sent traffic.
type Seer interface {
	MarkSeen(ctx context.Context, id uuid.UUID) error
}

// Presence marks devices online when they send traffic.
type Presence struct {
	devices Seer
	logger  *slog.Logger
}

// NewPresence returns a Presence that records traffic with s.
func NewPresence(s Seer, logger *slog.Logger) *Presence {
	return &Presence{devices: s, logger: logger}
}

// Handle records a message a device published on topic. Any message on a
// device's own topics counts; topics outside devices/{device id}/ are ignored.
func (p *Presence) Handle(ctx context.Context, topic string) {
	id, ok := devices.DeviceIDFromTopic(topic)
	if !ok {
		return
	}
	if err := p.devices.MarkSeen(ctx, id); err != nil {
		p.logger.ErrorContext(ctx, "mark device seen", "device_id", id, "err", err)
	}
}
