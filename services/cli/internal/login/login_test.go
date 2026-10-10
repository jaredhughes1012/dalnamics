package login

import (
	"bytes"
	"context"
	"errors"
	"net/http"
	"net/url"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"dalnamics/services/cli/internal/client/apigen"
)

type fakeExchanger struct {
	code, verifier, redirectURI string
}

func (f *fakeExchanger) ExchangeCLICode(_ context.Context, code, verifier, redirectURI string) (apigen.User, error) {
	f.code, f.verifier, f.redirectURI = code, verifier, redirectURI
	return apigen.User{Name: "Jane"}, nil
}

// fakeStudio plays the browser + studio: it reads the login URL the cli opens
// and calls the loopback redirect the way studio would.
func fakeStudio(t *testing.T, respond func(redirect *url.URL, q url.Values)) func(string) error {
	return func(loginURL string) error {
		u, err := url.Parse(loginURL)
		require.NoError(t, err)
		assert.Equal(t, "/cli-login", u.Path)
		q := u.Query()
		redirect, err := url.Parse(q.Get("redirect_uri"))
		require.NoError(t, err)
		go respond(redirect, q)
		return nil
	}
}

func get(t *testing.T, u *url.URL, params url.Values) *http.Response {
	t.Helper()
	u.RawQuery = params.Encode()
	res, err := http.Get(u.String())
	require.NoError(t, err)
	res.Body.Close()
	return res
}

func TestBrowser(t *testing.T) {
	ex := &fakeExchanger{}
	var challengeSent string
	var out bytes.Buffer

	user, err := Browser(context.Background(), ex, Options{
		StudioURL: "http://studio.test/",
		Out:       &out,
		OpenBrowser: fakeStudio(t, func(redirect *url.URL, q url.Values) {
			challengeSent = q.Get("code_challenge")
			// A forged callback with the wrong state is rejected and ignored.
			assert.Equal(t, http.StatusBadRequest, get(t, redirect, url.Values{"state": {"forged"}, "code": {"evil"}}).StatusCode)
			assert.Equal(t, http.StatusOK, get(t, redirect, url.Values{"state": {q.Get("state")}, "code": {"the-code"}}).StatusCode)
		}),
	})

	require.NoError(t, err)
	assert.Equal(t, "Jane", user.Name)
	assert.Equal(t, "the-code", ex.code)
	assert.Equal(t, challenge(ex.verifier), challengeSent, "verifier must match the challenge sent to studio")
	assert.Regexp(t, `^http://127\.0\.0\.1:\d+/callback$`, ex.redirectURI)
	assert.Contains(t, out.String(), "Open this URL to log in: http://studio.test/cli-login?")
}

func TestBrowserCancelled(t *testing.T) {
	_, err := Browser(context.Background(), &fakeExchanger{}, Options{
		StudioURL: "http://studio.test",
		Out:       &bytes.Buffer{},
		OpenBrowser: fakeStudio(t, func(redirect *url.URL, q url.Values) {
			get(t, redirect, url.Values{"state": {q.Get("state")}, "error": {"access_denied"}})
		}),
	})

	assert.ErrorContains(t, err, "access_denied")
}

func TestBrowserTimeout(t *testing.T) {
	var out bytes.Buffer
	_, err := Browser(context.Background(), &fakeExchanger{}, Options{
		StudioURL:   "http://studio.test",
		Out:         &out,
		OpenBrowser: func(string) error { return errors.New("no browser") },
		Timeout:     50 * time.Millisecond,
	})

	assert.ErrorIs(t, err, context.DeadlineExceeded)
	assert.Contains(t, out.String(), "open the URL above manually")
}
