// Package login implements browser-based cli login: the cli listens on a
// loopback port, sends the user to studio's /cli-login page, and redeems the
// authorization code studio redirects back with (OAuth native app flow with
// PKCE, RFC 8252).
package login

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"errors"
	"fmt"
	"html"
	"io"
	"net"
	"net/http"
	"net/url"
	"strings"
	"time"

	"dalnamics/services/cli/internal/client/apigen"
)

const callbackPath = "/callback"

// Exchanger redeems an authorization code. *client.Client implements it.
type Exchanger interface {
	ExchangeCLICode(ctx context.Context, code, verifier, redirectURI string) (apigen.User, error)
}

// Options configures Browser.
type Options struct {
	// StudioURL is where the user logs in and approves the cli.
	StudioURL string
	// OpenBrowser opens a URL. When nil or failing, the URL is only printed.
	OpenBrowser func(url string) error
	// Out receives instructions for the user.
	Out io.Writer
	// Timeout bounds how long to wait for the user. Defaults to 5 minutes.
	Timeout time.Duration
}

type callback struct {
	code string
	err  error
}

// Browser runs the browser login flow and returns the user the code was
// redeemed for.
func Browser(ctx context.Context, ex Exchanger, opts Options) (apigen.User, error) {
	var zero apigen.User
	if opts.Timeout == 0 {
		opts.Timeout = 5 * time.Minute
	}
	ctx, cancel := context.WithTimeout(ctx, opts.Timeout)
	defer cancel()

	verifier, err := randomString()
	if err != nil {
		return zero, err
	}
	state, err := randomString()
	if err != nil {
		return zero, err
	}

	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return zero, fmt.Errorf("listen for callback: %w", err)
	}
	redirectURI := fmt.Sprintf("http://%s%s", ln.Addr(), callbackPath)

	results := make(chan callback, 1)
	srv := &http.Server{
		Handler:           callbackHandler(state, results),
		ReadHeaderTimeout: 5 * time.Second,
	}
	go func() { _ = srv.Serve(ln) }()
	defer srv.Close()

	loginURL, err := authorizeURL(opts.StudioURL, redirectURI, challenge(verifier), state)
	if err != nil {
		return zero, err
	}
	fmt.Fprintf(opts.Out, "Open this URL to log in: %s\n", loginURL)
	if opts.OpenBrowser != nil {
		if err := opts.OpenBrowser(loginURL); err != nil {
			fmt.Fprintln(opts.Out, "Could not open a browser; open the URL above manually.")
		}
	}
	fmt.Fprintln(opts.Out, "Waiting for login...")

	select {
	case <-ctx.Done():
		return zero, fmt.Errorf("timed out waiting for browser login: %w", ctx.Err())
	case cb := <-results:
		if cb.err != nil {
			return zero, cb.err
		}
		return ex.ExchangeCLICode(ctx, cb.code, verifier, redirectURI)
	}
}

func authorizeURL(studioURL, redirectURI, codeChallenge, state string) (string, error) {
	u, err := url.Parse(strings.TrimRight(studioURL, "/") + "/cli-login")
	if err != nil {
		return "", fmt.Errorf("invalid studio URL: %w", err)
	}
	u.RawQuery = url.Values{
		"redirect_uri":   {redirectURI},
		"code_challenge": {codeChallenge},
		"state":          {state},
	}.Encode()
	return u.String(), nil
}

// callbackHandler accepts the first callback with a matching state.
func callbackHandler(state string, results chan<- callback) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET "+callbackPath, func(w http.ResponseWriter, r *http.Request) {
		q := r.URL.Query()
		if q.Get("state") != state {
			writePage(w, http.StatusBadRequest, "Login failed", "This login link is stale. Run the login command again.")
			return
		}

		var cb callback
		switch {
		case q.Get("error") != "":
			cb.err = fmt.Errorf("login was not completed: %s", q.Get("error"))
			writePage(w, http.StatusOK, "Login cancelled", "You can close this tab.")
		case q.Get("code") == "":
			cb.err = errors.New("login callback did not include a code")
			writePage(w, http.StatusBadRequest, "Login failed", "No authorization code was received.")
		default:
			cb.code = q.Get("code")
			writePage(w, http.StatusOK, "Logged in", "The cli is logged in. You can close this tab.")
		}

		select {
		case results <- cb:
		default: // a callback was already accepted
		}
	})
	return mux
}

func writePage(w http.ResponseWriter, status int, title, message string) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(status)
	fmt.Fprintf(w, `<!doctype html><html><head><title>%[1]s</title></head>
<body style="font-family:system-ui;display:grid;place-items:center;height:100vh;margin:0">
<div style="text-align:center"><h1>%[1]s</h1><p>%[2]s</p></div></body></html>`,
		html.EscapeString(title), html.EscapeString(message))
}

// randomString returns 32 random bytes, base64url encoded (a valid PKCE verifier).
func randomString() (string, error) {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return base64.RawURLEncoding.EncodeToString(b), nil
}

// challenge returns the PKCE S256 challenge for verifier.
func challenge(verifier string) string {
	sum := sha256.Sum256([]byte(verifier))
	return base64.RawURLEncoding.EncodeToString(sum[:])
}
