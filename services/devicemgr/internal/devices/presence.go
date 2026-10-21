package devices

import (
	"context"
	"fmt"
	"log/slog"
	"time"

	"github.com/google/uuid"

	storedevices "dalnamics/services/devicemgr/internal/store/devices"
)

// throttleWindow is how often MarkSeen writes at most per device. It is shorter
// than offlineAfter, so a device the sweep marked offline is always older than
// the window and its next message always writes.
func (s *Service) throttleWindow() time.Duration {
	return s.offlineAfter / 3
}

// MarkSeen records that a device sent MQTT traffic: it marks the device online
// and updates its last_seen_at. It writes at most once per throttle window per
// device on this instance, and the query skips rows another instance wrote
// within the window. An unknown device is a no-op.
func (s *Service) MarkSeen(ctx context.Context, id uuid.UUID) error {
	window := s.throttleWindow()
	s.mu.Lock()
	last, ok := s.seen[id]
	s.mu.Unlock()
	if ok && s.now().Sub(last) < window {
		return nil
	}

	_, err := s.q.MarkDeviceSeen(ctx, storedevices.MarkDeviceSeenParams{
		DeviceID:           id,
		MinIntervalSeconds: window.Seconds(),
	})
	if err != nil {
		return fmt.Errorf("mark device seen: %w", err)
	}
	// Cached only after a successful write, so a failed one retries on the
	// device's next message.
	s.mu.Lock()
	s.seen[id] = s.now()
	s.mu.Unlock()
	return nil
}

// Sweep marks devices offline that have been silent longer than offlineAfter,
// and returns how many it marked. It compares database timestamps only, so it
// also corrects state that went stale while devicemgr was down. It also drops
// cache entries old enough that they can no longer suppress a write.
func (s *Service) Sweep(ctx context.Context) (int64, error) {
	n, err := s.q.MarkStaleDevicesOffline(ctx, s.offlineAfter.Seconds())
	if err != nil {
		return 0, fmt.Errorf("mark stale devices offline: %w", err)
	}

	cutoff := s.now().Add(-s.offlineAfter)
	s.mu.Lock()
	for id, at := range s.seen {
		if at.Before(cutoff) {
			delete(s.seen, id)
		}
	}
	s.mu.Unlock()
	return n, nil
}

// RunSweeper calls Sweep every interval until ctx is cancelled. The first sweep
// waits out grace, so devices whose traffic was missed while devicemgr was down
// get a chance to report before they are marked offline.
func (s *Service) RunSweeper(ctx context.Context, interval, grace time.Duration, logger *slog.Logger) {
	select {
	case <-ctx.Done():
		return
	case <-time.After(grace):
	}

	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		switch n, err := s.Sweep(ctx); {
		case err != nil && ctx.Err() == nil:
			logger.ErrorContext(ctx, "device presence sweep", "err", err)
		case n > 0:
			logger.InfoContext(ctx, "devices marked offline", "count", n)
		}

		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
		}
	}
}
