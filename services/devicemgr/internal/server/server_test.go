package server

import (
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"go.uber.org/mock/gomock"

	"dalnamics/internal/health"
	"dalnamics/services/devicemgr/internal/apigen"
	"dalnamics/services/devicemgr/internal/devices"
	"dalnamics/services/devicemgr/internal/store/mockstore"
)

const (
	testToken        = "test-token-that-is-at-least-32-bytes"
	testMQTTPassword = "test-mqtt-password-that-is-at-least-32-bytes"
)

func newHandler(t *testing.T) (http.Handler, *mockstore.MockQuerier) {
	t.Helper()
	q := mockstore.NewMockQuerier(gomock.NewController(t))
	svc := devices.NewService(q, devices.Config{MQTTPassword: []byte(testMQTTPassword)})
	h, err := NewHandler([]byte(testToken), svc, slog.New(slog.NewTextHandler(io.Discard, nil)))
	require.NoError(t, err)
	return h, q
}

func serve(t *testing.T, path, authorization string) *httptest.ResponseRecorder {
	t.Helper()
	h, _ := newHandler(t)
	req := httptest.NewRequest(http.MethodGet, path, nil)
	if authorization != "" {
		req.Header.Set("Authorization", authorization)
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func decode[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	var v T
	require.NoError(t, json.NewDecoder(rec.Body).Decode(&v))
	return v
}

func TestHealthNeedsNoToken(t *testing.T) {
	rec := serve(t, health.Path, "")

	require.Equal(t, http.StatusOK, rec.Code)
	assert.Equal(t, health.Response{Status: health.StatusOK, Service: "devicemgr"}, decode[health.Response](t, rec))
}

func TestServiceTokenRejected(t *testing.T) {
	tests := map[string]string{
		"missing":      "",
		"wrong token":  "Bearer not-the-right-token-but-still-32-bytes",
		"basic scheme": "Basic " + testToken,
		"no token":     "Bearer",
	}
	for name, authorization := range tests {
		t.Run(name, func(t *testing.T) {
			rec := serve(t, "/devices", authorization)

			require.Equal(t, http.StatusUnauthorized, rec.Code)
			assert.Equal(t, "unauthenticated", decode[apigen.Error](t, rec).Code)
		})
	}
}

func TestUnknownPathWithTokenIsNotFound(t *testing.T) {
	rec := serve(t, "/devices", "Bearer "+testToken)

	require.Equal(t, http.StatusNotFound, rec.Code)
	assert.Equal(t, "not_found", decode[apigen.Error](t, rec).Code)
}

func TestOpenRoutesComeFromSpec(t *testing.T) {
	routes, err := openRoutes()

	require.NoError(t, err)
	assert.Equal(t, map[string]bool{
		"GET /healthz":         true,
		"POST /mqtt/user":      true,
		"POST /mqtt/superuser": true,
		"POST /mqtt/acl":       true,
	}, routes)
}
