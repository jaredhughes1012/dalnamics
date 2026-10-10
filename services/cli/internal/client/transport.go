package client

import (
	"context"
	"errors"
	"net/http"
	"sync"

	"dalnamics/services/cli/internal/client/apigen"
	"dalnamics/services/cli/internal/credentials"
)

// authDoer attaches the stored access token to requests and, on a 401,
// refreshes the tokens once and retries.
type authDoer struct {
	base      apigen.HttpRequestDoer
	apiURL    string
	creds     credentials.Store
	refresher *apigen.ClientWithResponses

	mu sync.Mutex
}

func (d *authDoer) Do(req *http.Request) (*http.Response, error) {
	creds, err := d.creds.Load(d.apiURL)
	if errors.Is(err, credentials.ErrNotFound) {
		return d.base.Do(req) // unauthenticated request (login, health)
	}
	if err != nil {
		return nil, err
	}

	res, err := d.base.Do(withBearer(req, creds.AccessToken))
	if err != nil || res.StatusCode != http.StatusUnauthorized || creds.RefreshToken == "" || req.GetBody == nil && req.Body != nil {
		return res, err
	}

	refreshed, ok := d.refresh(req.Context(), creds)
	if !ok {
		return res, nil
	}
	res.Body.Close()

	retry := req.Clone(req.Context())
	if req.GetBody != nil {
		if retry.Body, err = req.GetBody(); err != nil {
			return nil, err
		}
	}
	return d.base.Do(withBearer(retry, refreshed.AccessToken))
}

// refreshLock serializes refreshes across cli processes, since the api revokes
// a session when one of its rotated refresh tokens is presented again.
const refreshLock = "refresh"

// refresh exchanges the refresh token for a new pair and saves it. If another
// request or cli process already rotated the tokens, it uses the newer stored
// pair instead.
func (d *authDoer) refresh(ctx context.Context, stale credentials.Credentials) (credentials.Credentials, bool) {
	d.mu.Lock()
	defer d.mu.Unlock()
	unlock, err := credentials.Lock(ctx, refreshLock)
	if err != nil {
		return credentials.Credentials{}, false
	}
	defer unlock()

	if current, err := d.creds.Load(d.apiURL); err == nil && current.RefreshToken != stale.RefreshToken {
		return current, true
	}

	res, err := d.refresher.RefreshWithResponse(ctx, apigen.RefreshRequest{RefreshToken: stale.RefreshToken})
	if err != nil || res.JSON200 == nil {
		return credentials.Credentials{}, false
	}
	fresh := credentials.Credentials{AccessToken: res.JSON200.AccessToken, RefreshToken: res.JSON200.RefreshToken}
	if err := d.creds.Save(d.apiURL, fresh); err != nil {
		return credentials.Credentials{}, false
	}
	return fresh, true
}

func withBearer(req *http.Request, token string) *http.Request {
	r := req.Clone(req.Context())
	r.Header.Set("Authorization", "Bearer "+token)
	return r
}
