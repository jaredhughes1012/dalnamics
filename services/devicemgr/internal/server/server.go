// Package server wires devicemgr's private HTTP routes to the generated
// OpenAPI interface in apigen.
package server

import (
	"crypto/subtle"
	"log/slog"
	"net/http"
	"strings"

	"dalnamics/internal/health"
	"dalnamics/services/devicemgr/internal/apigen"
)

// ServiceName identifies devicemgr in health checks and logs.
const ServiceName = "devicemgr"

// Server implements apigen.StrictServerInterface.
type Server struct {
	logger *slog.Logger
}

var _ apigen.StrictServerInterface = (*Server)(nil)

// NewHandler returns the root handler for devicemgr. Every route except the
// health check requires the shared service token.
func NewHandler(token []byte, logger *slog.Logger) http.Handler {
	s := &Server{logger: logger}
	strict := apigen.NewStrictHandlerWithOptions(s, nil, apigen.StrictHTTPServerOptions{
		RequestErrorHandlerFunc:  s.handleRequestError,
		ResponseErrorHandlerFunc: s.handleError,
	})

	mux := http.NewServeMux()
	mux.Handle("GET "+health.Path, health.Handler(ServiceName))
	mux.HandleFunc("/", s.handleNotFound)
	return requireServiceToken(token, apigen.HandlerWithOptions(strict, apigen.StdHTTPServerOptions{
		BaseRouter:       mux,
		ErrorHandlerFunc: s.handleRequestError,
	}))
}

// requireServiceToken rejects requests, other than the health check, that do
// not carry token as a bearer token.
func requireServiceToken(token []byte, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != health.Path && !validToken(r, token) {
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
