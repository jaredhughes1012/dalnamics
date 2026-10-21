package devices

import "errors"

// ErrInvalidCode is returned when a registration code is unknown, expired, or
// already used. The cases are deliberately indistinguishable.
var ErrInvalidCode = errors.New("invalid or expired registration code")

// ValidationError reports a registration request that failed input validation.
type ValidationError struct {
	Field   string
	Message string
}

func (e *ValidationError) Error() string {
	return e.Field + ": " + e.Message
}
