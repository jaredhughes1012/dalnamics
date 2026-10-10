// Package health defines the health check contract shared by every service
// and the clients that probe them.
package health

import (
	"encoding/json"
	"net/http"
)

// Path is the route every service exposes its health check on.
const Path = "/healthz"

// StatusOK is reported when a service is ready to serve traffic.
const StatusOK = "ok"

// Response is the body returned from a health check.
type Response struct {
	Status  string `json:"status"`
	Service string `json:"service"`
}

// Handler returns an http.HandlerFunc that reports the named service as healthy.
func Handler(service string) http.HandlerFunc {
	return func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(Response{Status: StatusOK, Service: service})
	}
}
