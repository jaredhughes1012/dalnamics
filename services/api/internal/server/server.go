// Package server wires the api's HTTP routes.
package server

import (
	"net/http"

	"dalnamics/internal/health"
)

// ServiceName identifies the api in health checks and logs.
const ServiceName = "api"

// NewHandler returns the root handler for the api.
func NewHandler() http.Handler {
	mux := http.NewServeMux()
	mux.Handle("GET "+health.Path, health.Handler(ServiceName))
	return mux
}
