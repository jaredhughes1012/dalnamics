// Package devices issues device registration codes and lists a user's
// devices. devicemgr redeems the codes and owns the devices themselves.
package devices

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"

	"dalnamics/services/api/internal/store"
	storedevices "dalnamics/services/api/internal/store/devices"
)

const (
	codeTTL = 10 * time.Minute
	// codeAttempts bounds retries when a new code collides with a live one.
	codeAttempts = 3
)

// Config configures a Service.
type Config struct {
	// Now defaults to time.Now.
	Now func() time.Time
}

// Service implements device operations for users.
type Service struct {
	q   store.Querier
	now func() time.Time
}

// NewService returns a Service backed by q.
func NewService(q store.Querier, cfg Config) *Service {
	s := &Service{q: q, now: cfg.Now}
	if s.now == nil {
		s.now = time.Now
	}
	return s
}

// Device is a device registered to a user.
type Device = storedevices.ListDevicesByUserRow

// RegistrationCode is a one-time code that registers a device to the user who
// requested it.
type RegistrationCode struct {
	Code      string
	ExpiresAt time.Time
}

// IssueRegistrationCode issues a registration code for userID. It doesn't
// revoke the user's other unexpired codes.
func (s *Service) IssueRegistrationCode(ctx context.Context, userID uuid.UUID) (RegistrationCode, error) {
	for range codeAttempts {
		rc := RegistrationCode{Code: generateCode(), ExpiresAt: s.now().Add(codeTTL)}
		err := s.q.InTx(ctx, func(q store.Querier) error {
			if err := q.DeleteExpiredDeviceRegistrationCodes(ctx); err != nil {
				return fmt.Errorf("delete expired registration codes: %w", err)
			}
			return q.CreateDeviceRegistrationCode(ctx, storedevices.CreateDeviceRegistrationCodeParams{
				CodeHash:  hashCode(rc.Code),
				UserID:    userID,
				ExpiresAt: rc.ExpiresAt,
			})
		})
		if store.IsUniqueViolation(err) {
			continue
		}
		if err != nil {
			return RegistrationCode{}, fmt.Errorf("create registration code: %w", err)
		}
		return rc, nil
	}
	return RegistrationCode{}, errors.New("create registration code: every attempt collided with an existing code")
}

// List returns userID's devices, newest first.
func (s *Service) List(ctx context.Context, userID uuid.UUID) ([]Device, error) {
	devices, err := s.q.ListDevicesByUser(ctx, userID)
	if err != nil {
		return nil, fmt.Errorf("list devices: %w", err)
	}
	return devices, nil
}
