package commands

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"dalnamics/services/cli/internal/client/apigen"
)

// fakeAuthAPI implements just enough of the api for dev login, status and logout.
func fakeAuthAPI(t *testing.T) *httptest.Server {
	t.Helper()
	loggedIn := false
	user := apigen.User{Name: "dev", Email: "dev@dalnamics.local"}

	mux := http.NewServeMux()
	mux.HandleFunc("POST /auth/dev-login", func(w http.ResponseWriter, r *http.Request) {
		var req apigen.DevLoginRequest
		require.NoError(t, json.NewDecoder(r.Body).Decode(&req))
		assert.Equal(t, apigen.Cli, *req.Client, "cli logins create cli sessions")
		loggedIn = true
		_ = json.NewEncoder(w).Encode(apigen.Session{
			User:   user,
			Tokens: apigen.Tokens{AccessToken: "access", RefreshToken: "refresh", TokenType: apigen.Bearer},
		})
	})
	mux.HandleFunc("GET /me", func(w http.ResponseWriter, r *http.Request) {
		if !loggedIn || r.Header.Get("Authorization") != "Bearer access" {
			w.WriteHeader(http.StatusUnauthorized)
			_ = json.NewEncoder(w).Encode(apigen.Error{Code: "unauthenticated", Message: "authentication required"})
			return
		}
		_ = json.NewEncoder(w).Encode(user)
	})
	mux.HandleFunc("POST /auth/logout", func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "Bearer access", r.Header.Get("Authorization"))
		loggedIn = false
		w.WriteHeader(http.StatusNoContent)
	})

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		mux.ServeHTTP(w, r)
	}))
	t.Cleanup(srv.Close)
	return srv
}

func TestDevLoginStatusLogout(t *testing.T) {
	useTempCredentials(t)
	api := fakeAuthAPI(t)

	_, err := runRoot(t, "auth", "status", "--api-url", api.URL)
	assert.ErrorContains(t, err, "not logged in")

	out, err := runRoot(t, "auth", "login", "--dev", "dev@dalnamics.local", "--api-url", api.URL)
	require.NoError(t, err)
	assert.Equal(t, "Logged in to "+api.URL+" as dev <dev@dalnamics.local>\n", out)

	out, err = runRoot(t, "auth", "status", "--api-url", api.URL)
	require.NoError(t, err)
	assert.Contains(t, out, "as dev <dev@dalnamics.local>")

	out, err = runRoot(t, "auth", "logout", "--api-url", api.URL)
	require.NoError(t, err)
	assert.Equal(t, "Logged out of "+api.URL+"\n", out)

	_, err = runRoot(t, "auth", "status", "--api-url", api.URL)
	assert.ErrorContains(t, err, "not logged in")
}
