package commands

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"dalnamics/internal/health"
)

func TestHealth(t *testing.T) {
	useTempCredentials(t)
	srv := httptest.NewServer(health.Handler("api"))
	defer srv.Close()

	out, err := runRoot(t, "health", "--api-url", srv.URL)

	require.NoError(t, err)
	assert.Equal(t, "api: ok\n", out)
}

func TestHealthJSON(t *testing.T) {
	useTempCredentials(t)
	srv := httptest.NewServer(health.Handler("api"))
	defer srv.Close()

	out, err := runRoot(t, "health", "--json", "--api-url", srv.URL)

	require.NoError(t, err)
	assert.JSONEq(t, `{"status":"ok","service":"api"}`, out)
}

func TestHealthUnhealthy(t *testing.T) {
	useTempCredentials(t)
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	defer srv.Close()

	_, err := runRoot(t, "health", "--api-url", srv.URL)

	require.Error(t, err)
	assert.True(t, strings.Contains(err.Error(), "503"), err.Error())
}
