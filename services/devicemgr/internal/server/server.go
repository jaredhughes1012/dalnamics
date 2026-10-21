// Package server wires devicemgr's private HTTP routes to the generated
// OpenAPI interface in apigen.
package server

import (
	"crypto/subtle"
	"fmt"
	"log/slog"
	"net/http"
	"strings"

	"dalnamics/internal/health"
	"dalnamics/services/devicemgr/internal/apigen"
	"dalnamics/services/devicemgr/internal/devices"
)

// ServiceName identifies devicemgr in health checks and logs.
const ServiceName = "devicemgr"

// Server implements apigen.StrictServerInterface.
type Server struct {
	devices *devices.Service
	logger  *slog.Logger
}

var _ apigen.StrictServerInterface = (*Server)(nil)

// NewHandler returns the root handler for devicemgr. Every route requires the
// shared service token unless the spec gives its operation empty security.
func NewHandler(token []byte, devicesSvc *devices.Service, logger *slog.Logger) (http.Handler, error) {
	open, err := openRoutes()
	if err != nil {
		return nil, err
	}

	s := &Server{devices: devicesSvc, logger: logger}
	strict := apigen.NewStrictHandlerWithOptions(s, nil, apigen.StrictHTTPServerOptions{
		RequestErrorHandlerFunc:  s.handleRequestError,
		ResponseErrorHandlerFunc: s.handleError,
	})

	mux := http.NewServeMux()
	mux.Handle("GET "+health.Path, health.Handler(ServiceName))
	mux.HandleFunc("/", s.handleNotFound)
	return requireServiceToken(token, open, apigen.HandlerWithOptions(strict, apigen.StdHTTPServerOptions{
		BaseRouter:       mux,
		ErrorHandlerFunc: s.handleRequestError,
	})), nil
}

// openRoutes returns the "METHOD /path" of every operation the OpenAPI spec
// declares with empty security, so the spec stays the source of truth. The
// health check is served by the shared handler and is left out of the embedded
// spec, so it is added here.
func openRoutes() (map[string]bool, error) {
	spec, err := apigen.GetSwagger()
	if err != nil {
		return nil, fmt.Errorf("load openapi spec: %w", err)
	}

	routes := map[string]bool{"GET " + health.Path: true}
	for path, item := range spec.Paths.Map() {
		for method, op := range item.Operations() {
			reqs := spec.Security
			if op.Security != nil {
				reqs = *op.Security
			}
			if len(reqs) == 0 {
				routes[method+" "+path] = true
			}
		}
	}
	return routes, nil
}

// requireServiceToken rejects requests to routes outside open that do not
// carry token as a bearer token.
func requireServiceToken(token []byte, open map[string]bool, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !open[r.Method+" "+r.URL.Path] && !validToken(r, token) {
			writeJSON(w, http.StatusUnauthorized, apigen.Error{Code: codeUnauthenticated, Message: "missing or invalid service token"})
			return
		}
		next.ServeHTTP(w, r)
	})
}

func validToken(r *http.Request, token []byte) bool {
	scheme, got, ok := strings.Cut(r.Header.Get("Authorization"), " ")
	if !ok || !strings.EqualFold(scheme, "Bearer") {
		return false
	}
	return subtle.ConstantTimeCompare([]byte(got), token) == 1
}
