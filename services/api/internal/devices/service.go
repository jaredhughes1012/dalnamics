// Package devices issues device registration codes and lists and gets a
// user's devices. devicemgr redeems the codes and owns the devices themselves.
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

// SeedDevRegistrationCode registers code to the user with email, for
// development. The code never expires, and seeding it again lets it be redeemed
// once more, so a dev device can register after every api start. It needn't
// follow the code format; one outside the alphabet can never collide with an
// issued code.
func (s *Service) SeedDevRegistrationCode(ctx context.Context, email, code string) error {
	n, err := s.q.SeedDeviceRegistrationCode(ctx, storedevices.SeedDeviceRegistrationCodeParams{
		CodeHash: hashCode(code),
		Email:    email,
	})
	if err != nil {
		return fmt.Errorf("seed dev registration code: %w", err)
	}
	if n == 0 {
		return fmt.Errorf("seed dev registration code: no user %s", email)
	}
	return nil
}

// List returns userID's devices, newest first.
func (s *Service) List(ctx context.Context, userID uuid.UUID) ([]Device, error) {
	devices, err := s.q.ListDevicesByUser(ctx, userID)
	if err != nil {
		return nil, fmt.Errorf("list devices: %w", err)
	}
	return devices, nil
}

// Get returns userID's device with id, or ErrNotFound if userID has no such
// device.
func (s *Service) Get(ctx context.Context, userID, id uuid.UUID) (Device, error) {
	d, err := s.q.GetDeviceForUser(ctx, storedevices.GetDeviceForUserParams{ID: id, UserID: userID})
	if errors.Is(err, store.ErrNoRows) {
		return Device{}, ErrNotFound
	}
	if err != nil {
		return Device{}, fmt.Errorf("get device: %w", err)
	}
	return Device(d), nil
}
