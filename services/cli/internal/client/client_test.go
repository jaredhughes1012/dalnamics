package client

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"sync/atomic"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"dalnamics/services/cli/internal/client/apigen"
	"dalnamics/services/cli/internal/credentials"
)

// fakeAPI accepts one valid access token and rotates it on refresh.
type fakeAPI struct {
	mu              sync.Mutex
	access, refresh string
	refreshes       atomic.Int32
}

func (f *fakeAPI) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	f.mu.Lock()
	defer f.mu.Unlock()
	w.Header().Set("Content-Type", "application/json")
	switch r.URL.Path {
	case "/auth/refresh":
		var req apigen.RefreshRequest
		_ = json.NewDecoder(r.Body).Decode(&req)
		if req.RefreshToken != f.refresh {
			w.WriteHeader(http.StatusUnauthorized)
			_ = json.NewEncoder(w).Encode(apigen.Error{Code: "invalid_token", Message: "invalid or expired token"})
			return
		}
		f.refreshes.Add(1)
		f.access, f.refresh = "access-2", "refresh-2"
		_ = json.NewEncoder(w).Encode(apigen.Tokens{AccessToken: f.access, RefreshToken: f.refresh, TokenType: apigen.Bearer})
	case "/me":
		if r.Header.Get("Authorization") != "Bearer "+f.access {
			w.WriteHeader(http.StatusUnauthorized)
			_ = json.NewEncoder(w).Encode(apigen.Error{Code: "invalid_token", Message: "invalid or expired token"})
			return
		}
		_ = json.NewEncoder(w).Encode(apigen.User{Name: "Jane", Email: "jane@example.com"})
	default:
		http.NotFound(w, r)
	}
}

func newTestClient(t *testing.T, api http.Handler) (*Client, *credentials.FileStore) {
	t.Helper()
	srv := httptest.NewServer(api)
	t.Cleanup(srv.Close)
	t.Setenv(credentials.ConfigDirEnv, t.TempDir())
	store, err := credentials.NewFileStore()
	require.NoError(t, err)
	c, err := New(srv.URL+"/", store)
	require.NoError(t, err)
	return c, store
}

func TestMeWithValidToken(t *testing.T) {
	api := &fakeAPI{access: "access-1", refresh: "refresh-1"}
	c, store := newTestClient(t, api)
	require.NoError(t, store.Save(c.BaseURL, credentials.Credentials{AccessToken: "access-1", RefreshToken: "refresh-1"}))

	user, err := c.Me(context.Background())

	require.NoError(t, err)
	assert.Equal(t, "Jane", user.Name)
	assert.Zero(t, api.refreshes.Load())
}

func TestRefreshesExpiredAccessToken(t *testing.T) {
	api := &fakeAPI{access: "access-1", refresh: "refresh-1"}
	c, store := newTestClient(t, api)
	require.NoError(t, store.Save(c.BaseURL, credentials.Credentials{AccessToken: "expired", RefreshToken: "refresh-1"}))

	user, err := c.Me(context.Background())

	require.NoError(t, err)
	assert.Equal(t, "Jane", user.Name)
	assert.EqualValues(t, 1, api.refreshes.Load())
	saved, err := store.Load(c.BaseURL)
	require.NoError(t, err)
	assert.Equal(t, credentials.Credentials{AccessToken: "access-2", RefreshToken: "refresh-2"}, saved, "rotated tokens are persisted")
}

func TestConcurrentClientsRefreshOnce(t *testing.T) {
	// Separate clients and stores stand in for separate cli processes, which
	// share only the credentials directory.
	api := &fakeAPI{access: "access-1", refresh: "refresh-1"}
	c, store := newTestClient(t, api)
	require.NoError(t, store.Save(c.BaseURL, credentials.Credentials{AccessToken: "expired", RefreshToken: "refresh-1"}))
	other, err := credentials.NewFileStore()
	require.NoError(t, err)
	c2, err := New(c.BaseURL, other)
	require.NoError(t, err)

	var wg sync.WaitGroup
	errs := make([]error, 2)
	for i, client := range []*Client{c, c2} {
		wg.Go(func() { _, errs[i] = client.Me(context.Background()) })
	}
	wg.Wait()

	require.NoError(t, errs[0])
	require.NoError(t, errs[1])
	assert.EqualValues(t, 1, api.refreshes.Load(), "the second client reuses the first client's rotated tokens")
}

func TestFailedRefreshReturnsUnauthorized(t *testing.T) {
	api := &fakeAPI{access: "access-1", refresh: "refresh-1"}
	c, store := newTestClient(t, api)
	require.NoError(t, store.Save(c.BaseURL, credentials.Credentials{AccessToken: "expired", RefreshToken: "revoked"}))

	_, err := c.Me(context.Background())

	assert.True(t, IsUnauthorized(err))
	var apiErr *APIError
	require.ErrorAs(t, err, &apiErr)
	assert.Equal(t, "invalid_token", apiErr.Code)
}

func TestUnauthenticatedWithoutCredentials(t *testing.T) {
	c, _ := newTestClient(t, &fakeAPI{access: "access-1"})

	_, err := c.Me(context.Background())

	assert.True(t, IsUnauthorized(err))
}

func TestBaseURLIsNormalized(t *testing.T) {
	c, _ := newTestClient(t, &fakeAPI{})

	assert.False(t, strings.HasSuffix(c.BaseURL, "/"))
}
