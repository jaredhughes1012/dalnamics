package server

import (
	"context"
	"net/http"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"go.uber.org/mock/gomock"

	"dalnamics/services/api/internal/apigen"
	"dalnamics/services/api/internal/store"
	storeauth "dalnamics/services/api/internal/store/auth"
	storedevices "dalnamics/services/api/internal/store/devices"
)

func TestCreateDeviceRegistrationCode(t *testing.T) {
	ts := newTestServer(t, "dev@dalnamics.local")
	user := storeauth.User{ID: uuid.New(), Email: "dev@dalnamics.local"}
	token := ts.login(t, user)
	ts.q.EXPECT().InTx(gomock.Any(), gomock.Any()).
		DoAndReturn(func(_ context.Context, fn func(store.Querier) error) error { return fn(ts.q) })
	ts.q.EXPECT().DeleteExpiredDeviceRegistrationCodes(gomock.Any()).Return(nil)
	ts.q.EXPECT().CreateDeviceRegistrationCode(gomock.Any(), gomock.Cond(func(p storedevices.CreateDeviceRegistrationCodeParams) bool {
		return p.UserID == user.ID
	})).Return(nil)

	before := time.Now()
	res := ts.do(t, http.MethodPost, "/devices/registration-codes", "", token)

	require.Equal(t, http.StatusCreated, res.StatusCode)
	body := decode[apigen.DeviceRegistrationCode](t, res)
	assert.Regexp(t, `^[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{6}$`, body.Code)
	assert.WithinDuration(t, before.Add(10*time.Minute), body.ExpiresAt, 5*time.Second)
}

func TestListDevices(t *testing.T) {
	ts := newTestServer(t, "dev@dalnamics.local")
	user := storeauth.User{ID: uuid.New(), Email: "dev@dalnamics.local"}
	token := ts.login(t, user)
	created := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	device := storedevices.ListDevicesByUserRow{ID: uuid.New(), Type: "harwood0", Name: "bench-rover", CreatedAt: created}
	ts.q.EXPECT().ListDevicesByUser(gomock.Any(), user.ID).Return([]storedevices.ListDevicesByUserRow{device}, nil)

	res := ts.do(t, http.MethodGet, "/devices", "", token)

	require.Equal(t, http.StatusOK, res.StatusCode)
	assert.Equal(t, []apigen.Device{{Id: device.ID, Type: "harwood0", Name: "bench-rover", CreatedAt: created}}, decode[[]apigen.Device](t, res))
}

func TestListDevicesEmpty(t *testing.T) {
	ts := newTestServer(t, "dev@dalnamics.local")
	user := storeauth.User{ID: uuid.New(), Email: "dev@dalnamics.local"}
	token := ts.login(t, user)
	ts.q.EXPECT().ListDevicesByUser(gomock.Any(), user.ID).Return(nil, nil)

	res := ts.do(t, http.MethodGet, "/devices", "", token)

	require.Equal(t, http.StatusOK, res.StatusCode)
	assert.Equal(t, []apigen.Device{}, decode[[]apigen.Device](t, res), "an empty list is [], not null")
}
