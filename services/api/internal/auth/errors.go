package auth

import "errors"

// Sentinel errors returned by Service. The server maps them to HTTP responses.
var (
	ErrEmailTaken         = errors.New("an account with that email already exists")
	ErrInvalidCredentials = errors.New("invalid email or password")
	ErrInvalidToken       = errors.New("invalid or expired token")
	ErrInvalidCode        = errors.New("invalid or expired authorization code")
	ErrDevLoginDisabled   = errors.New("dev login is disabled")
	ErrNotDevUser         = errors.New("email is not a dev user")
	ErrUnauthenticated    = errors.New("authentication required")
)

// ValidationError reports a request that failed input validation.
type ValidationError struct {
	Field   string
	Message string
}

func (e *ValidationError) Error() string {
	return e.Field + ": " + e.Message
}
