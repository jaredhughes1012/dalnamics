package server

import (
	"encoding/json"
	"errors"
	"net/http"

	"dalnamics/services/api/internal/apigen"
	"dalnamics/services/api/internal/auth"
	"dalnamics/services/api/internal/devices"
)

// Error codes returned in apigen.Error.Code. Clients may switch on these.
const (
	codeInvalidRequest     = "invalid_request"
	codeEmailTaken         = "email_taken"
	codeInvalidCredentials = "invalid_credentials"
	codeInvalidToken       = "invalid_token"
	codeUnauthenticated    = "unauthenticated"
	codeInvalidCode        = "invalid_code"
	codeNotDevUser         = "not_dev_user"
	codeNotFound           = "not_found"
	codeInternal           = "internal"
)

// handleError maps an error returned by a handler to an HTTP response. Domain
// handlers return sentinel errors from the domain packages rather than building
// error responses themselves.
func (s *Server) handleError(w http.ResponseWriter, r *http.Request, err error) {
	status, body := errorResponse(err)
	if status == http.StatusInternalServerError {
		s.logger.ErrorContext(r.Context(), "request failed", "method", r.Method, "path", r.URL.Path, "err", err)
	}
	writeJSON(w, status, body)
}

// handleRequestError responds to requests the generated code could not decode.
func (s *Server) handleRequestError(w http.ResponseWriter, _ *http.Request, err error) {
	writeJSON(w, http.StatusBadRequest, apigen.Error{Code: codeInvalidRequest, Message: err.Error()})
}

func errorResponse(err error) (int, apigen.Error) {
	var verr *auth.ValidationError
	var dverr *devices.ValidationError
	switch {
	case errors.As(err, &verr):
		return http.StatusBadRequest, apigen.Error{Code: codeInvalidRequest, Message: verr.Error()}
	case errors.As(err, &dverr):
		return http.StatusBadRequest, apigen.Error{Code: codeInvalidRequest, Message: dverr.Error()}
	case errors.Is(err, auth.ErrEmailTaken):
		return http.StatusConflict, apigen.Error{Code: codeEmailTaken, Message: err.Error()}
	case errors.Is(err, auth.ErrInvalidCredentials):
		return http.StatusUnauthorized, apigen.Error{Code: codeInvalidCredentials, Message: err.Error()}
	case errors.Is(err, auth.ErrInvalidToken):
		return http.StatusUnauthorized, apigen.Error{Code: codeInvalidToken, Message: auth.ErrInvalidToken.Error()}
	case errors.Is(err, auth.ErrUnauthenticated):
		return http.StatusUnauthorized, apigen.Error{Code: codeUnauthenticated, Message: err.Error()}
	case errors.Is(err, auth.ErrInvalidCode):
		return http.StatusBadRequest, apigen.Error{Code: codeInvalidCode, Message: err.Error()}
	case errors.Is(err, auth.ErrNotDevUser):
		return http.StatusUnauthorized, apigen.Error{Code: codeNotDevUser, Message: err.Error()}
	case errors.Is(err, devices.ErrNotFound):
		return http.StatusNotFound, apigen.Error{Code: codeNotFound, Message: err.Error()}
	case errors.Is(err, auth.ErrDevLoginDisabled):
		return http.StatusNotFound, apigen.Error{Code: codeNotFound, Message: "not found"}
	default:
		return http.StatusInternalServerError, apigen.Error{Code: codeInternal, Message: "internal server error"}
	}
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}
