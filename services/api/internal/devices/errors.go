package devices

import "errors"

// ErrNotFound means the user has no device with the requested ID. Another
// user's device is reported the same way, so callers can't learn which device
// IDs exist.
var ErrNotFound = errors.New("device not found")

// ValidationError reports a request that failed input validation.
type ValidationError struct {
	Field   string
	Message string
}

func (e *ValidationError) Error() string {
	return e.Field + ": " + e.Message
}
