package server

import (
	"encoding/json"
	"net/http"

	"dalnamics/services/devicemgr/internal/apigen"
)

// Error codes returned in apigen.Error.Code, shared with the api (see
// docs/arch.md#error-codes).
const (
	codeInvalidRequest  = "invalid_request"
	codeUnauthenticated = "unauthenticated"
	codeNotFound        = "not_found"
	codeInternal        = "internal"
)

// handleError maps an error returned by a handler to an HTTP response.
func (s *Server) handleError(w http.ResponseWriter, r *http.Request, err error) {
	s.logger.ErrorContext(r.Context(), "request failed", "method", r.Method, "path", r.URL.Path, "err", err)
	writeJSON(w, http.StatusInternalServerError, apigen.Error{Code: codeInternal, Message: "internal server error"})
}

// handleRequestError responds to requests the generated code could not decode.
func (s *Server) handleRequestError(w http.ResponseWriter, _ *http.Request, err error) {
	writeJSON(w, http.StatusBadRequest, apigen.Error{Code: codeInvalidRequest, Message: err.Error()})
}

// handleNotFound responds to requests that match no route.
func (s *Server) handleNotFound(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusNotFound, apigen.Error{Code: codeNotFound, Message: "not found"})
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}
