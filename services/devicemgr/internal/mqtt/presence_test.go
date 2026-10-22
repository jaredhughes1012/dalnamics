package mqtt

import (
	"context"
	"errors"
	"io"
	"log/slog"
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"dalnamics/services/devicemgr/internal/devices"
)

type fakeSeer struct {
	seen []uuid.UUID
	err  error
}

func (f *fakeSeer) MarkSeen(_ context.Context, id uuid.UUID) error {
	f.seen = append(f.seen, id)
	return f.err
}

func discard() *slog.Logger { return slog.New(slog.NewTextHandler(io.Discard, nil)) }

func TestPresenceMarksDeviceSeen(t *testing.T) {
	id := uuid.New()
	s := &fakeSeer{}

	NewPresence(s, discard()).Handle(context.Background(), "devices/"+id.String()+"/heartbeat")

	assert.Equal(t, []uuid.UUID{id}, s.seen)
}

func TestPresenceIgnoresOtherTopics(t *testing.T) {
	id := uuid.NewString()
	for _, topic := range []string{"devices/register/heartbeat", "devices/not-a-uuid/heartbeat", "devices/" + id, "devices/" + id + "/x", "other/" + id + "/heartbeat"} {
		s := &fakeSeer{}
		NewPresence(s, discard()).Handle(context.Background(), topic)
		assert.Empty(t, s.seen, topic)
	}
}

func TestPresenceSurvivesStoreErrors(t *testing.T) {
	s := &fakeSeer{err: errors.New("db down")}

	NewPresence(s, discard()).Handle(context.Background(), "devices/"+uuid.NewString()+"/heartbeat")

	assert.Len(t, s.seen, 1)
}

func newRouter() (router, *fakeRedeemer, *fakeSeer) {
	r := &fakeRedeemer{creds: devices.Credentials{DeviceID: uuid.New(), Secret: "s3cret"}}
	s := &fakeSeer{}
	return router{handshake: NewHandshake(r, discard()), presence: NewPresence(s, discard())}, r, s
}

func TestRouteRegistrationToHandshake(t *testing.T) {
	rt, r, s := newRouter()
	pub := &fakePublisher{}

	rt.route(context.Background(), pub, registerSubID, "devices/register/c1", []byte(`{"code":"AB3D7K","type":"harwood0"}`))

	assert.Equal(t, "AB3D7K", r.got.Code)
	require.Len(t, pub.published, 1)
	assert.Empty(t, s.seen)
}

func TestRouteHeartbeatToPresence(t *testing.T) {
	rt, r, s := newRouter()
	pub := &fakePublisher{}
	id := uuid.New()

	rt.route(context.Background(), pub, heartbeatSubID, devices.HeartbeatTopic(id), nil)

	assert.Equal(t, []uuid.UUID{id}, s.seen)
	assert.Empty(t, r.got.Code)
	assert.Empty(t, pub.published)
}

func TestRouteRedeemsOverlappingTopicOnce(t *testing.T) {
	rt, r, s := newRouter()
	pub := &fakePublisher{}
	// A register client named "heartbeat" matches both subscriptions, so its
	// request arrives on each.
	req := []byte(`{"code":"AB3D7K","type":"harwood0"}`)

	rt.route(context.Background(), pub, registerSubID, "devices/register/heartbeat", req)
	rt.route(context.Background(), pub, heartbeatSubID, "devices/register/heartbeat", req)

	assert.Equal(t, "AB3D7K", r.got.Code)
	assert.Len(t, pub.published, 1, "the request is redeemed exactly once")
	assert.Empty(t, s.seen)
}

func TestRouteDropsUnknownSubscriptions(t *testing.T) {
	rt, r, s := newRouter()
	pub := &fakePublisher{}

	rt.route(context.Background(), pub, 0, "devices/register/c1", []byte(`{"code":"AB3D7K","type":"harwood0"}`))

	assert.Empty(t, r.got.Code)
	assert.Empty(t, pub.published)
	assert.Empty(t, s.seen)
}
