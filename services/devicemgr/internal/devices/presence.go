package devices

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"

	storedevices "dalnamics/services/devicemgr/internal/store/devices"
)

// HeartbeatTopic is where a device publishes heartbeats.
func HeartbeatTopic(id uuid.UUID) string {
	return "devices/" + id.String() + "/heartbeat"
}

// DeviceIDFromHeartbeatTopic returns the device ID in a heartbeat topic,
// devices/{device id}/heartbeat, and reports whether topic is one.
func DeviceIDFromHeartbeatTopic(topic string) (uuid.UUID, bool) {
	rest, ok := strings.CutPrefix(topic, "devices/")
	if !ok {
		return uuid.Nil, false
	}
	idPart, ok := strings.CutSuffix(rest, "/heartbeat")
	if !ok {
		return uuid.Nil, false
	}
	id, err := uuid.Parse(idPart)
	if err != nil {
		return uuid.Nil, false
	}
	return id, true
}

// throttleWindow is how often MarkSeen writes at most per device. It is well
// under offlineAfter, so a skipped heartbeat always leaves the device's stored
// online_until at least offlineAfter - window away, and short enough that
// heartbeats sent every offlineAfter/3 (the documented maximum) are never
// skipped.
func (s *Service) throttleWindow() time.Duration {
	return s.offlineAfter / 6
}

// MarkSeen records a heartbeat from a device: it updates last_seen_at and keeps
// the device online for offlineAfter. It writes at most once per throttle
// window per device on this instance, and the query skips rows another
// instance wrote within the window. An unknown device is a no-op.
func (s *Service) MarkSeen(ctx context.Context, id uuid.UUID) error {
	window := s.throttleWindow()
	// Reserve the write before making it, so concurrent heartbeats from one
	// device write once, and the window starts no later than the write does.
	s.mu.Lock()
	now := s.now()
	if last, ok := s.seen[id]; ok && now.Sub(last) < window {
		s.mu.Unlock()
		return nil
	}
	s.seen[id] = now
	s.pruneLocked(now)
	s.mu.Unlock()

	n, err := s.q.MarkDeviceSeen(ctx, storedevices.MarkDeviceSeenParams{
		DeviceID:            id,
		OfflineAfterSeconds: s.offlineAfter.Seconds(),
		MinIntervalSeconds:  window.Seconds(),
	})
	if err != nil || n == 0 {
		// Nothing was written (a failure, an unknown device, or a row another
		// instance wrote within the window), so don't let the reservation
		// suppress the device's next heartbeat.
		s.mu.Lock()
		if s.seen[id].Equal(now) {
			delete(s.seen, id)
		}
		s.mu.Unlock()
	}
	if err != nil {
		return fmt.Errorf("mark device seen: %w", err)
	}
	return nil
}

// pruneLocked drops entries old enough that they can no longer suppress a
// write, at most once per offlineAfter, which bounds the cache. s.mu must be
// held.
func (s *Service) pruneLocked(now time.Time) {
	if now.Sub(s.pruned) < s.offlineAfter {
		return
	}
	s.pruned = now
	cutoff := now.Add(-s.throttleWindow())
	for id, at := range s.seen {
		if at.Before(cutoff) {
			delete(s.seen, id)
		}
	}
}
