package devices

import (
	"context"
	"errors"
	"sync"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"go.uber.org/mock/gomock"

	storedevices "dalnamics/services/devicemgr/internal/store/devices"
	"dalnamics/services/devicemgr/internal/store/mockstore"
)

const testOfflineAfter = 90 * time.Second

// clock is a settable time source.
type clock struct{ t time.Time }

func (c *clock) now() time.Time          { return c.t }
func (c *clock) advance(d time.Duration) { c.t = c.t.Add(d) }

func newPresenceService(t *testing.T) (*Service, *mockstore.MockQuerier, *clock) {
	t.Helper()
	q := mockstore.NewMockQuerier(gomock.NewController(t))
	c := &clock{t: time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)}
	return NewService(q, Config{OfflineAfter: testOfflineAfter, Now: c.now}), q, c
}

func expectSeen(q *mockstore.MockQuerier, id uuid.UUID) *gomock.Call {
	// Online for the offline threshold; the throttle window is a sixth of it.
	return q.EXPECT().MarkDeviceSeen(gomock.Any(), storedevices.MarkDeviceSeenParams{
		DeviceID: id, OfflineAfterSeconds: 90, MinIntervalSeconds: 15,
	}).Return(int64(1), nil)
}

func TestMarkSeenWritesOncePerWindow(t *testing.T) {
	s, q, c := newPresenceService(t)
	id := uuid.New()
	expectSeen(q, id).Times(1)

	require.NoError(t, s.MarkSeen(context.Background(), id))
	c.advance(14 * time.Second)
	require.NoError(t, s.MarkSeen(context.Background(), id), "within the window: no write")

	expectSeen(q, id).Times(1)
	c.advance(time.Second)
	require.NoError(t, s.MarkSeen(context.Background(), id), "the window has passed: writes again")
}

func TestMarkSeenWritesEveryHeartbeat(t *testing.T) {
	s, q, c := newPresenceService(t)
	id := uuid.New()
	expectSeen(q, id).Times(4)

	// Heartbeats every offlineAfter/3, the most a device may wait, all write.
	for range 4 {
		require.NoError(t, s.MarkSeen(context.Background(), id))
		c.advance(testOfflineAfter / 3)
	}
}

func TestMarkSeenThrottlesPerDevice(t *testing.T) {
	s, q, _ := newPresenceService(t)
	a, b := uuid.New(), uuid.New()
	expectSeen(q, a).Times(1)
	expectSeen(q, b).Times(1)

	require.NoError(t, s.MarkSeen(context.Background(), a))
	require.NoError(t, s.MarkSeen(context.Background(), b))
	require.NoError(t, s.MarkSeen(context.Background(), a))
}

func TestMarkSeenWritesOnceForConcurrentHeartbeats(t *testing.T) {
	s, q, _ := newPresenceService(t)
	id := uuid.New()
	release := make(chan struct{})
	q.EXPECT().MarkDeviceSeen(gomock.Any(), gomock.Any()).DoAndReturn(
		func(context.Context, storedevices.MarkDeviceSeenParams) (int64, error) {
			<-release
			return 1, nil
		}).Times(1)

	var wg sync.WaitGroup
	first := make(chan error, 1)
	wg.Add(1)
	go func() {
		defer wg.Done()
		first <- s.MarkSeen(context.Background(), id)
	}()
	// Wait until the first write is in flight, then send more heartbeats.
	require.Eventually(t, func() bool {
		s.mu.Lock()
		defer s.mu.Unlock()
		_, ok := s.seen[id]
		return ok
	}, time.Second, time.Millisecond)
	for range 5 {
		require.NoError(t, s.MarkSeen(context.Background(), id), "skipped while the first write is in flight")
	}
	close(release)
	wg.Wait()
	require.NoError(t, <-first)
}

func TestMarkSeenRetriesAfterFailedWrite(t *testing.T) {
	s, q, _ := newPresenceService(t)
	id := uuid.New()
	boom := errors.New("db down")
	q.EXPECT().MarkDeviceSeen(gomock.Any(), gomock.Any()).Return(int64(0), boom)

	assert.ErrorIs(t, s.MarkSeen(context.Background(), id), boom)

	expectSeen(q, id).Times(1)
	require.NoError(t, s.MarkSeen(context.Background(), id), "a failed write isn't cached")
}

func TestMarkSeenRetriesAfterSkippedWrite(t *testing.T) {
	s, q, _ := newPresenceService(t)
	id := uuid.New()
	// Another instance wrote the row within the window, so nothing changed.
	q.EXPECT().MarkDeviceSeen(gomock.Any(), gomock.Any()).Return(int64(0), nil)

	require.NoError(t, s.MarkSeen(context.Background(), id))

	expectSeen(q, id).Times(1)
	require.NoError(t, s.MarkSeen(context.Background(), id), "a skipped write isn't cached")
}

func TestMarkSeenPrunesOldCacheEntries(t *testing.T) {
	s, q, c := newPresenceService(t)
	old, recent := uuid.New(), uuid.New()
	expectSeen(q, old).Times(1)
	expectSeen(q, recent).Times(1)

	require.NoError(t, s.MarkSeen(context.Background(), old))
	c.advance(testOfflineAfter)
	require.NoError(t, s.MarkSeen(context.Background(), recent))

	s.mu.Lock()
	defer s.mu.Unlock()
	assert.NotContains(t, s.seen, old, "older than the throttle window")
	assert.Contains(t, s.seen, recent)
}

func TestNewServiceDefaultsOfflineAfter(t *testing.T) {
	s := NewService(mockstore.NewMockQuerier(gomock.NewController(t)), Config{})
	assert.Equal(t, DefaultOfflineAfter, s.offlineAfter)
}

func TestDeviceIDFromHeartbeatTopic(t *testing.T) {
	id := uuid.New()
	for topic, want := range map[string]bool{
		HeartbeatTopic(id):                        true,
		"devices/" + id.String() + "/a/heartbeat": false,
		"devices/" + id.String() + "/telemetry":   false,
		"devices/register/heartbeat":              false,
		"devices/not-a-uuid/heartbeat":            false,
		"devices/" + id.String():                  false,
		"other/" + id.String() + "/heartbeat":     false,
	} {
		got, ok := DeviceIDFromHeartbeatTopic(topic)
		assert.Equal(t, want, ok, topic)
		if want {
			assert.Equal(t, id, got, topic)
		}
	}
}
