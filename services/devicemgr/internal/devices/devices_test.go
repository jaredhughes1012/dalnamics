package devices

import (
	"context"
	"crypto/sha256"
	"encoding/base64"
	"errors"
	"strings"
	"testing"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"go.uber.org/mock/gomock"

	"dalnamics/services/devicemgr/internal/store"
	storedevices "dalnamics/services/devicemgr/internal/store/devices"
	"dalnamics/services/devicemgr/internal/store/mockstore"
)

var testMQTTPassword = []byte("devicemgr-mqtt-password-at-least-32-bytes")

func newMockedService(t *testing.T) (*Service, *mockstore.MockQuerier) {
	t.Helper()
	q := mockstore.NewMockQuerier(gomock.NewController(t))
	return NewService(q, Config{MQTTPassword: testMQTTPassword}), q
}

func sha(s string) []byte {
	sum := sha256.Sum256([]byte(s))
	return sum[:]
}

func TestRedeem(t *testing.T) {
	for name, code := range map[string]string{
		"exact":            "AB3D7K",
		"lowercase padded": "  ab3d7k\n",
	} {
		t.Run(name, func(t *testing.T) {
			s, q := newMockedService(t)
			codeID, userID, deviceID := uuid.New(), uuid.New(), uuid.New()
			q.EXPECT().GetActiveRegistrationCode(gomock.Any(), sha("AB3D7K")).
				Return(storedevices.GetActiveRegistrationCodeRow{ID: codeID, UserID: userID}, nil)
			var created storedevices.CreateDeviceParams
			q.EXPECT().CreateDevice(gomock.Any(), gomock.Any()).
				DoAndReturn(func(_ context.Context, p storedevices.CreateDeviceParams) (uuid.UUID, error) {
					created = p
					return deviceID, nil
				})

			creds, err := s.Redeem(context.Background(), Request{Code: code, Type: "harwood0", Name: " bench-rover "})
			require.NoError(t, err)

			assert.Equal(t, deviceID, creds.DeviceID)
			secret, err := base64.RawURLEncoding.DecodeString(creds.Secret)
			require.NoError(t, err)
			assert.Len(t, secret, 32)
			assert.Equal(t, storedevices.CreateDeviceParams{
				UserID:             userID,
				Type:               "harwood0",
				Name:               "bench-rover",
				SecretHash:         sha(creds.Secret),
				RegistrationCodeID: codeID,
			}, created, "the device is linked to the code's user and only the secret's hash is stored")
		})
	}
}

func TestRedeemDefaultsNameToType(t *testing.T) {
	s, q := newMockedService(t)
	q.EXPECT().GetActiveRegistrationCode(gomock.Any(), gomock.Any()).Return(storedevices.GetActiveRegistrationCodeRow{}, nil)
	q.EXPECT().CreateDevice(gomock.Any(), gomock.Cond(func(p storedevices.CreateDeviceParams) bool {
		return p.Name == "harwood0"
	})).Return(uuid.New(), nil)

	_, err := s.Redeem(context.Background(), Request{Code: "AB3D7K", Type: "harwood0", Name: "   "})
	require.NoError(t, err)
}

func TestRedeemUnknownOrExpiredCode(t *testing.T) {
	s, q := newMockedService(t)
	q.EXPECT().GetActiveRegistrationCode(gomock.Any(), gomock.Any()).Return(storedevices.GetActiveRegistrationCodeRow{}, store.ErrNoRows)

	_, err := s.Redeem(context.Background(), Request{Code: "AB3D7K", Type: "harwood0"})
	assert.ErrorIs(t, err, ErrInvalidCode)
}

func TestRedeemUsedCode(t *testing.T) {
	s, q := newMockedService(t)
	q.EXPECT().GetActiveRegistrationCode(gomock.Any(), gomock.Any()).Return(storedevices.GetActiveRegistrationCodeRow{}, nil)
	q.EXPECT().CreateDevice(gomock.Any(), gomock.Any()).Return(uuid.Nil, &pgconn.PgError{Code: "23505"})

	_, err := s.Redeem(context.Background(), Request{Code: "AB3D7K", Type: "harwood0"})
	assert.ErrorIs(t, err, ErrInvalidCode)
}

func TestRedeemStoreError(t *testing.T) {
	s, q := newMockedService(t)
	boom := errors.New("boom")
	q.EXPECT().GetActiveRegistrationCode(gomock.Any(), gomock.Any()).Return(storedevices.GetActiveRegistrationCodeRow{}, boom)

	_, err := s.Redeem(context.Background(), Request{Code: "AB3D7K", Type: "harwood0"})
	assert.ErrorIs(t, err, boom)
	assert.NotErrorIs(t, err, ErrInvalidCode)
}

func TestRedeemValidation(t *testing.T) {
	for name, tc := range map[string]struct {
		req   Request
		field string
	}{
		"missing code":     {Request{Code: " ", Type: "harwood0"}, "code"},
		"missing type":     {Request{Code: "AB3D7K"}, "type"},
		"uppercase type":   {Request{Code: "AB3D7K", Type: "Harwood0"}, "type"},
		"type with spaces": {Request{Code: "AB3D7K", Type: "harwood 0"}, "type"},
		"long type":        {Request{Code: "AB3D7K", Type: strings.Repeat("a", 65)}, "type"},
		"long name":        {Request{Code: "AB3D7K", Type: "harwood0", Name: strings.Repeat("n", 101)}, "name"},
	} {
		t.Run(name, func(t *testing.T) {
			s, _ := newMockedService(t)

			_, err := s.Redeem(context.Background(), tc.req)

			var verr *ValidationError
			require.ErrorAs(t, err, &verr)
			assert.Equal(t, tc.field, verr.Field)
		})
	}
}

func TestCheckUser(t *testing.T) {
	deviceID := uuid.New()
	secret := "device-secret"

	for name, tc := range map[string]struct {
		username, password string
		expect             func(q *mockstore.MockQuerier)
		want               bool
	}{
		"devicemgr with its password":   {username: "devicemgr", password: string(testMQTTPassword), want: true},
		"devicemgr with wrong password": {username: "devicemgr", password: "nope"},
		"register with any password":    {username: "register", password: "anything", want: true},
		"register with no password":     {username: "register", want: true},
		"device with its secret": {
			username: deviceID.String(), password: secret, want: true,
			expect: func(q *mockstore.MockQuerier) {
				q.EXPECT().GetDeviceSecretHash(gomock.Any(), deviceID).Return(sha(secret), nil)
			},
		},
		"device with wrong secret": {
			username: deviceID.String(), password: "wrong",
			expect: func(q *mockstore.MockQuerier) {
				q.EXPECT().GetDeviceSecretHash(gomock.Any(), deviceID).Return(sha(secret), nil)
			},
		},
		"unknown device": {
			username: deviceID.String(), password: secret,
			expect: func(q *mockstore.MockQuerier) {
				q.EXPECT().GetDeviceSecretHash(gomock.Any(), deviceID).Return(nil, store.ErrNoRows)
			},
		},
		"non-uuid username": {username: "someone", password: secret},
	} {
		t.Run(name, func(t *testing.T) {
			s, q := newMockedService(t)
			if tc.expect != nil {
				tc.expect(q)
			}

			ok, err := s.CheckUser(context.Background(), tc.username, tc.password)
			require.NoError(t, err)
			assert.Equal(t, tc.want, ok)
		})
	}
}

func TestCheckUserStoreError(t *testing.T) {
	s, q := newMockedService(t)
	q.EXPECT().GetDeviceSecretHash(gomock.Any(), gomock.Any()).Return(nil, errors.New("boom"))

	_, err := s.CheckUser(context.Background(), uuid.NewString(), "secret")
	assert.Error(t, err)
}

func TestIsSuperuser(t *testing.T) {
	s, _ := newMockedService(t)

	assert.True(t, s.IsSuperuser("devicemgr"))
	assert.False(t, s.IsSuperuser("register"))
	assert.False(t, s.IsSuperuser(uuid.NewString()))
}

func TestCheckACL(t *testing.T) {
	device := uuid.NewString()
	other := uuid.NewString()

	tests := []struct {
		name                      string
		username, clientID, topic string
		acc                       Access
		want                      bool
	}{
		{"register publishes its request", "register", "c1", "devices/register/c1", AccessWrite, true},
		{"register subscribes to its reply", "register", "c1", "devices/register/c1/reply", AccessSubscribe, true},
		{"register reads its reply", "register", "c1", "devices/register/c1/reply", AccessRead, true},
		{"register publishes as another client", "register", "c1", "devices/register/c2", AccessWrite, false},
		{"register publishes to its reply", "register", "c1", "devices/register/c1/reply", AccessWrite, false},
		{"register reads another reply", "register", "c1", "devices/register/c2/reply", AccessRead, false},
		{"register subscribes to its request", "register", "c1", "devices/register/c1", AccessSubscribe, false},
		{"register subscribes with a wildcard", "register", "c1", "devices/register/+/reply", AccessSubscribe, false},
		{"register with a wildcard client id", "register", "+", "devices/register/+", AccessWrite, false},
		{"register with a multi-level client id", "register", "a/b", "devices/register/a/b", AccessWrite, false},
		{"register with read-write access", "register", "c1", "devices/register/c1", AccessRead | AccessWrite, false},
		{"register touches a device topic", "register", "c1", "devices/" + device + "/x", AccessWrite, false},
		{"device publishes under its prefix", device, "d", "devices/" + device + "/telemetry", AccessWrite, true},
		{"device reads under its prefix", device, "d", "devices/" + device + "/commands", AccessRead, true},
		{"device subscribes to all its topics", device, "d", "devices/" + device + "/#", AccessSubscribe, true},
		{"device uses its own root topic", device, "d", "devices/" + device, AccessWrite, true},
		{"device publishes to another device", device, "d", "devices/" + other + "/telemetry", AccessWrite, false},
		{"device subscribes to every device", device, "d", "devices/#", AccessSubscribe, false},
		{"device subscribes across devices", device, "d", "devices/+/telemetry", AccessSubscribe, false},
		{"device subscribes to everything", device, "d", "#", AccessSubscribe, false},
		{"device with a longer id prefix", device, "d", "devices/" + device + "x/telemetry", AccessWrite, false},
		{"device reaches registration", device, "d", "devices/register/d", AccessWrite, false},
		{"unknown username", "someone", "c1", "devices/someone/x", AccessWrite, false},
		{"devicemgr", "devicemgr", "dm", "anything", AccessWrite, true},
	}
	s, _ := newMockedService(t)
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.Equal(t, tt.want, s.CheckACL(tt.username, tt.clientID, tt.topic, tt.acc))
		})
	}
}
