// Package client is the cli's HTTP client for the api.
package client

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"dalnamics/internal/health"
)

// Client calls api endpoints.
type Client struct {
	baseURL string
	http    *http.Client
}

// New returns a Client targeting the api at baseURL.
func New(baseURL string) *Client {
	return &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		http:    &http.Client{Timeout: 10 * time.Second},
	}
}

// Health calls the api's health check.
func (c *Client) Health(ctx context.Context) (health.Response, error) {
	var out health.Response

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.baseURL+health.Path, nil)
	if err != nil {
		return out, err
	}
	res, err := c.http.Do(req)
	if err != nil {
		return out, err
	}
	defer res.Body.Close()

	if res.StatusCode != http.StatusOK {
		return out, fmt.Errorf("health check returned %s", res.Status)
	}
	if err := json.NewDecoder(res.Body).Decode(&out); err != nil {
		return out, fmt.Errorf("decode health response: %w", err)
	}
	return out, nil
}
