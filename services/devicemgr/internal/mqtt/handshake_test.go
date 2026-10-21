package mqtt

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"testing"

	"github.com/eclipse/paho.golang/paho"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"dalnamics/services/devicemgr/internal/devices"
)

type fakeRedeemer struct {
	got   devices.Request
	creds devices.Credentials
	err   error
}

func (f *fakeRedeemer) Redeem(_ context.Context, req devices.Request) (devices.Credentials, error) {
	f.got = req
	return f.creds, f.err
}

type fakePublisher struct {
	published []*paho.Publish
}

func (f *fakePublisher) Publish(_ context.Context, p *paho.Publish) (*paho.PublishResponse, error) {
	f.published = append(f.published, p)
	return &paho.PublishResponse{}, nil
}

func handle(t *testing.T, r *fakeRedeemer, topic, payload string) (*fakePublisher, map[string]any) {
	t.Helper()
	pub := &fakePublisher{}
	NewHandshake(r, slog.New(slog.NewTextHandler(io.Discard, nil))).Handle(context.Background(), pub, topic, []byte(payload))
	if len(pub.published) == 0 {
		return pub, nil
	}
	require.Len(t, pub.published, 1)
	var body map[string]any
	require.NoError(t, json.Unmarshal(pub.published[0].Payload, &body))
	return pub, body
}

func TestHandleSuccess(t *testing.T) {
	id := uuid.New()
	r := &fakeRedeemer{creds: devices.Credentials{DeviceID: id, Secret: "s3cret"}}

	pub, body := handle(t, r, "devices/register/c1", `{"code":"AB3D7K","type":"harwood0","name":"bench-rover","extra":"ignored"}`)

	assert.Equal(t, devices.Request{Code: "AB3D7K", Type: "harwood0", Name: "bench-rover"}, r.got)
	assert.Equal(t, "devices/register/c1/reply", pub.published[0].Topic)
	assert.Equal(t, byte(1), pub.published[0].QoS)
	assert.Equal(t, map[string]any{"device_id": id.String(), "secret": "s3cret"}, body)
}

func TestHandleErrors(t *testing.T) {
	for name, tc := range map[string]struct {
		payload string
		err     error
		want    string
	}{
		"invalid code":   {`{"code":"AB3D7K","type":"harwood0"}`, devices.ErrInvalidCode, "invalid_code"},
		"bad json":       {`{not json`, nil, "invalid_request"},
		"bad type":       {`{"code":"AB3D7K","type":"Bad Type"}`, &devices.ValidationError{Field: "type"}, "invalid_request"},
		"internal error": {`{"code":"AB3D7K","type":"harwood0"}`, errors.New("db down"), "internal"},
	} {
		t.Run(name, func(t *testing.T) {
			_, body := handle(t, &fakeRedeemer{err: tc.err}, "devices/register/c1", tc.payload)

			assert.Equal(t, map[string]any{"error": tc.want}, body)
		})
	}
}

func TestHandleIgnoresOtherTopics(t *testing.T) {
	for _, topic := range []string{"devices/register/", "devices/register/a/b", "devices/x/telemetry"} {
		pub, _ := handle(t, &fakeRedeemer{}, topic, `{}`)
		assert.Empty(t, pub.published, topic)
	}
}
