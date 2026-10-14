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

	"dalnamics/internal/health"
	"dalnamics/services/devicemgr/internal/apigen"
)

const testToken = "test-token-that-is-at-least-32-bytes"

func serve(t *testing.T, path, authorization string) *httptest.ResponseRecorder {
	t.Helper()
	h := NewHandler([]byte(testToken), slog.New(slog.NewTextHandler(io.Discard, nil)))
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
