// Package client is the cli's client for the api. It wraps the generated
// apigen client with credential handling: requests carry the stored access
// token, and a 401 triggers one refresh-and-retry that persists the rotated
// tokens.
package client

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/google/uuid"

	"dalnamics/services/cli/internal/client/apigen"
	"dalnamics/services/cli/internal/credentials"
)

// Client calls api endpoints.
type Client struct {
	BaseURL string

	api   *apigen.ClientWithResponses
	creds credentials.Store
}

// New returns a Client for the api at baseURL that authenticates with creds.
func New(baseURL string, creds credentials.Store) (*Client, error) {
	baseURL = strings.TrimRight(baseURL, "/")
	httpClient := &http.Client{Timeout: 30 * time.Second}

	// The refresher uses an unauthenticated client so a failing refresh
	// cannot recurse back into the auth transport.
	refresher, err := apigen.NewClientWithResponses(baseURL, apigen.WithHTTPClient(httpClient))
	if err != nil {
		return nil, err
	}
	doer := &authDoer{base: httpClient, apiURL: baseURL, creds: creds, refresher: refresher}
	api, err := apigen.NewClientWithResponses(baseURL, apigen.WithHTTPClient(doer))
	if err != nil {
		return nil, err
	}
	return &Client{BaseURL: baseURL, api: api, creds: creds}, nil
}

// APIError is an error response from the api.
type APIError struct {
	Status  int
	Code    string
	Message string
}

func (e *APIError) Error() string {
	if e.Message == "" {
		return fmt.Sprintf("api returned %d", e.Status)
	}
	return fmt.Sprintf("%s (%d %s)", e.Message, e.Status, e.Code)
}

// IsUnauthorized reports whether err is a 401 from the api.
func IsUnauthorized(err error) bool {
	var apiErr *APIError
	return errors.As(err, &apiErr) && apiErr.Status == http.StatusUnauthorized
}

// IsNotFound reports whether err is a 404 from the api.
func IsNotFound(err error) bool {
	var apiErr *APIError
	return errors.As(err, &apiErr) && apiErr.Status == http.StatusNotFound
}

// decoded returns v, or an error if a 2xx response had no JSON body.
func decoded[T any](res *http.Response, v *T) (T, error) {
	if v == nil {
		var zero T
		return zero, fmt.Errorf("unexpected %s response from %s %s", res.Status, res.Request.Method, res.Request.URL.Path)
	}
	return *v, nil
}

// checkStatus converts a non-2xx response into an *APIError.
func checkStatus(res *http.Response, body []byte) error {
	if res.StatusCode < 300 {
		return nil
	}
	apiErr := &APIError{Status: res.StatusCode}
	var e apigen.Error
	if json.Unmarshal(body, &e) == nil {
		apiErr.Code, apiErr.Message = e.Code, e.Message
	}
	return apiErr
}

// Health calls the api's health check.
func (c *Client) Health(ctx context.Context) (apigen.Health, error) {
	res, err := c.api.GetHealthWithResponse(ctx)
	if err != nil {
		return apigen.Health{}, err
	}
	if err := checkStatus(res.HTTPResponse, res.Body); err != nil {
		return apigen.Health{}, err
	}
	return decoded(res.HTTPResponse, res.JSON200)
}

// Me returns the logged-in user.
func (c *Client) Me(ctx context.Context) (apigen.User, error) {
	res, err := c.api.GetMeWithResponse(ctx)
	if err != nil {
		return apigen.User{}, err
	}
	if err := checkStatus(res.HTTPResponse, res.Body); err != nil {
		return apigen.User{}, err
	}
	return decoded(res.HTTPResponse, res.JSON200)
}

// CreateDeviceRegistrationCode issues a one-time code that registers a device
// to the logged-in user.
func (c *Client) CreateDeviceRegistrationCode(ctx context.Context) (apigen.DeviceRegistrationCode, error) {
	res, err := c.api.CreateDeviceRegistrationCodeWithResponse(ctx)
	if err != nil {
		return apigen.DeviceRegistrationCode{}, err
	}
	if err := checkStatus(res.HTTPResponse, res.Body); err != nil {
		return apigen.DeviceRegistrationCode{}, err
	}
	return decoded(res.HTTPResponse, res.JSON201)
}

// ListDevices returns the logged-in user's devices, newest first.
func (c *Client) ListDevices(ctx context.Context) ([]apigen.Device, error) {
	res, err := c.api.ListDevicesWithResponse(ctx)
	if err != nil {
		return nil, err
	}
	if err := checkStatus(res.HTTPResponse, res.Body); err != nil {
		return nil, err
	}
	return decoded(res.HTTPResponse, res.JSON200)
}

// GetDevice returns the logged-in user's device with id.
func (c *Client) GetDevice(ctx context.Context, id uuid.UUID) (apigen.Device, error) {
	res, err := c.api.GetDeviceWithResponse(ctx, id)
	if err != nil {
		return apigen.Device{}, err
	}
	if err := checkStatus(res.HTTPResponse, res.Body); err != nil {
		return apigen.Device{}, err
	}
	return decoded(res.HTTPResponse, res.JSON200)
}

// DevLogin starts a cli session for a dev user and stores its tokens.
func (c *Client) DevLogin(ctx context.Context, email string) (apigen.User, error) {
	client := apigen.Cli
	res, err := c.api.DevLoginWithResponse(ctx, apigen.DevLoginRequest{Email: email, Client: &client})
	if err != nil {
		return apigen.User{}, err
	}
	if err := checkStatus(res.HTTPResponse, res.Body); err != nil {
		return apigen.User{}, err
	}
	sess, err := decoded(res.HTTPResponse, res.JSON200)
	if err != nil {
		return apigen.User{}, err
	}
	return c.saveSession(sess)
}

// ExchangeCLICode redeems a code from the browser login flow and stores the
// resulting tokens.
func (c *Client) ExchangeCLICode(ctx context.Context, code, verifier, redirectURI string) (apigen.User, error) {
	res, err := c.api.ExchangeCliCodeWithResponse(ctx, apigen.CliTokenRequest{
		Code: code, CodeVerifier: verifier, RedirectUri: redirectURI,
	})
	if err != nil {
		return apigen.User{}, err
	}
	if err := checkStatus(res.HTTPResponse, res.Body); err != nil {
		return apigen.User{}, err
	}
	sess, err := decoded(res.HTTPResponse, res.JSON200)
	if err != nil {
		return apigen.User{}, err
	}
	return c.saveSession(sess)
}

// Logout revokes the session on the api and deletes the stored tokens. The
// local tokens are deleted even if the api call fails.
func (c *Client) Logout(ctx context.Context) error {
	var apiErr error
	res, err := c.api.LogoutWithResponse(ctx)
	if err != nil {
		apiErr = err
	} else if err := checkStatus(res.HTTPResponse, res.Body); err != nil && !IsUnauthorized(err) {
		apiErr = err // a 401 means the session is already gone
	}
	return errors.Join(apiErr, c.creds.Delete(c.BaseURL))
}

func (c *Client) saveSession(s apigen.Session) (apigen.User, error) {
	err := c.creds.Save(c.BaseURL, credentials.Credentials{
		AccessToken:  s.Tokens.AccessToken,
		RefreshToken: s.Tokens.RefreshToken,
	})
	if err != nil {
		return apigen.User{}, fmt.Errorf("save credentials: %w", err)
	}
	return s.User, nil
}
