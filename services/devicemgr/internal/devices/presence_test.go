package devices

import (
	"context"
	"errors"
	"io"
	"log/slog"
	"sync/atomic"
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
	// The throttle window is a third of the offline threshold.
	return q.EXPECT().MarkDeviceSeen(gomock.Any(), storedevices.MarkDeviceSeenParams{DeviceID: id, MinIntervalSeconds: 30}).Return(int64(1), nil)
}

func TestMarkSeenWritesOncePerWindow(t *testing.T) {
	s, q, c := newPresenceService(t)
	id := uuid.New()
	expectSeen(q, id).Times(1)

	require.NoError(t, s.MarkSeen(context.Background(), id))
	c.advance(29 * time.Second)
	require.NoError(t, s.MarkSeen(context.Background(), id), "within the window: no write")

	expectSeen(q, id).Times(1)
	c.advance(time.Second)
	require.NoError(t, s.MarkSeen(context.Background(), id), "the window has passed: writes again")
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

func TestMarkSeenRetriesAfterFailedWrite(t *testing.T) {
	s, q, _ := newPresenceService(t)
	id := uuid.New()
	boom := errors.New("db down")
	q.EXPECT().MarkDeviceSeen(gomock.Any(), gomock.Any()).Return(int64(0), boom)

	assert.ErrorIs(t, s.MarkSeen(context.Background(), id), boom)

	expectSeen(q, id).Times(1)
	require.NoError(t, s.MarkSeen(context.Background(), id), "a failed write isn't cached")
}

func TestSweep(t *testing.T) {
	s, q, _ := newPresenceService(t)
	q.EXPECT().MarkStaleDevicesOffline(gomock.Any(), float64(90)).Return(int64(3), nil)

	n, err := s.Sweep(context.Background())

	require.NoError(t, err)
	assert.Equal(t, int64(3), n)
}

func TestSweepError(t *testing.T) {
	s, q, _ := newPresenceService(t)
	boom := errors.New("db down")
	q.EXPECT().MarkStaleDevicesOffline(gomock.Any(), gomock.Any()).Return(int64(0), boom)

	_, err := s.Sweep(context.Background())
	assert.ErrorIs(t, err, boom)
}

func TestSweepPrunesOldCacheEntries(t *testing.T) {
	s, q, c := newPresenceService(t)
	old, recent := uuid.New(), uuid.New()
	expectSeen(q, old).Times(1)
	expectSeen(q, recent).Times(1)
	q.EXPECT().MarkStaleDevicesOffline(gomock.Any(), gomock.Any()).Return(int64(0), nil)

	require.NoError(t, s.MarkSeen(context.Background(), old))
	c.advance(testOfflineAfter)
	require.NoError(t, s.MarkSeen(context.Background(), recent))
	c.advance(time.Second)
	_, err := s.Sweep(context.Background())
	require.NoError(t, err)

	s.mu.Lock()
	defer s.mu.Unlock()
	assert.NotContains(t, s.seen, old, "older than the offline threshold")
	assert.Contains(t, s.seen, recent)
}

func TestRunSweeper(t *testing.T) {
	q := mockstore.NewMockQuerier(gomock.NewController(t))
	s := NewService(q, Config{OfflineAfter: testOfflineAfter})
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))

	var sweeps atomic.Int32
	swept := make(chan struct{}, 10)
	q.EXPECT().MarkStaleDevicesOffline(gomock.Any(), gomock.Any()).DoAndReturn(func(context.Context, float64) (int64, error) {
		sweeps.Add(1)
		swept <- struct{}{}
		return 1, nil
	}).AnyTimes()

	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	start := time.Now()
	go func() {
		s.RunSweeper(ctx, 20*time.Millisecond, 100*time.Millisecond, logger)
		close(done)
	}()

	<-swept
	assert.GreaterOrEqual(t, time.Since(start), 100*time.Millisecond, "the first sweep waits out the grace period")
	<-swept
	<-swept
	cancel()
	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("RunSweeper didn't stop when ctx was cancelled")
	}
	n := sweeps.Load()
	time.Sleep(50 * time.Millisecond)
	assert.Equal(t, n, sweeps.Load(), "no sweeps after it stops")
}

func TestRunSweeperStopsDuringGrace(t *testing.T) {
	q := mockstore.NewMockQuerier(gomock.NewController(t))
	s := NewService(q, Config{OfflineAfter: testOfflineAfter})
	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	// No sweep is expected: the mock fails the test if one runs.
	s.RunSweeper(ctx, time.Millisecond, time.Hour, slog.New(slog.NewTextHandler(io.Discard, nil)))
}

func TestDeviceIDFromTopic(t *testing.T) {
	id := uuid.New()
	for topic, want := range map[string]bool{
		"devices/" + id.String() + "/heartbeat": true,
		"devices/" + id.String() + "/a/b":       true,
		"devices/register/x":                    false,
		"devices/not-a-uuid/x":                  false,
		"devices/" + id.String():                false,
		"devices/" + id.String() + "/":          false,
		"other/" + id.String() + "/x":           false,
	} {
		got, ok := DeviceIDFromTopic(topic)
		assert.Equal(t, want, ok, topic)
		if want {
			assert.Equal(t, id, got, topic)
		}
	}
}
