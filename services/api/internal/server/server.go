// Package server wires the api's HTTP routes to the generated OpenAPI
// interface in apigen.
package server

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"strings"

	"dalnamics/internal/health"
	"dalnamics/services/api/internal/apigen"
	"dalnamics/services/api/internal/auth"
)

// ServiceName identifies the api in health checks and logs.
const ServiceName = "api"

// Server implements apigen.StrictServerInterface.
type Server struct {
	auth   *auth.Service
	logger *slog.Logger
}

var _ apigen.StrictServerInterface = (*Server)(nil)

// NewHandler returns the root handler for the api.
func NewHandler(authSvc *auth.Service, logger *slog.Logger) (http.Handler, error) {
	protected, err := bearerOperations()
	if err != nil {
		return nil, err
	}

	s := &Server{auth: authSvc, logger: logger}
	strict := apigen.NewStrictHandlerWithOptions(s,
		[]apigen.StrictMiddlewareFunc{s.requireBearer(protected)},
		apigen.StrictHTTPServerOptions{
			RequestErrorHandlerFunc:  s.handleRequestError,
			ResponseErrorHandlerFunc: s.handleError,
		},
	)

	mux := http.NewServeMux()
	mux.Handle("GET "+health.Path, health.Handler(ServiceName))
	return apigen.HandlerWithOptions(strict, apigen.StdHTTPServerOptions{
		BaseRouter:       mux,
		ErrorHandlerFunc: s.handleRequestError,
	}), nil
}

// bearerOperations returns the lowercased operation IDs that the OpenAPI spec
// marks as requiring bearerAuth, so the spec stays the source of truth.
func bearerOperations() (map[string]bool, error) {
	spec, err := apigen.GetSwagger()
	if err != nil {
		return nil, fmt.Errorf("load openapi spec: %w", err)
	}

	ops := map[string]bool{}
	for _, item := range spec.Paths.Map() {
		for _, op := range item.Operations() {
			reqs := spec.Security
			if op.Security != nil {
				reqs = *op.Security
			}
			for _, req := range reqs {
				if _, ok := req["bearerAuth"]; ok {
					ops[strings.ToLower(op.OperationID)] = true
				}
			}
		}
	}
	return ops, nil
}

// requireBearer authenticates operations in protected and stores the caller's
// auth.Principal in the request context.
func (s *Server) requireBearer(protected map[string]bool) apigen.StrictMiddlewareFunc {
	return func(next apigen.StrictHandlerFunc, operationID string) apigen.StrictHandlerFunc {
		if !protected[strings.ToLower(operationID)] {
			return next
		}
		return func(ctx context.Context, w http.ResponseWriter, r *http.Request, req any) (any, error) {
			token, ok := auth.BearerToken(r)
			if !ok {
				return nil, auth.ErrUnauthenticated
			}
			p, err := s.auth.Authenticate(ctx, token)
			if err != nil {
				return nil, err
			}
			return next(auth.WithPrincipal(ctx, p), w, r, req)
		}
	}
}

// principal returns the caller authenticated by requireBearer.
func principal(ctx context.Context) (auth.Principal, error) {
	p, ok := auth.PrincipalFrom(ctx)
	if !ok {
		return auth.Principal{}, auth.ErrUnauthenticated
	}
	return p, nil
}
