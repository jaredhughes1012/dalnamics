package devices

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"errors"
	"fmt"
	"regexp"
	"strings"
	"unicode/utf8"

	"github.com/google/uuid"

	"dalnamics/services/devicemgr/internal/store"
	storedevices "dalnamics/services/devicemgr/internal/store/devices"
)

const (
	maxNameLen = 100
	secretLen  = 32
)

var typePattern = regexp.MustCompile(`^[a-z0-9-]{1,64}$`)

// Request is a device's registration handshake.
type Request struct {
	// Code is the registration code the user gave the device.
	Code string `json:"code"`
	// Type is the kind of device, e.g. harwood0.
	Type string `json:"type"`
	// Name is optional and defaults to Type.
	Name string `json:"name"`
}

// Credentials are what a device connects to the broker with: its ID as the
// username and its secret as the password.
type Credentials struct {
	DeviceID uuid.UUID
	Secret   string
}

// Redeem registers a device to the user who requested req.Code and returns
// the device's new credentials. A code works once.
func (s *Service) Redeem(ctx context.Context, req Request) (Credentials, error) {
	name, err := validate(req)
	if err != nil {
		return Credentials{}, err
	}

	code, err := s.q.GetActiveRegistrationCode(ctx, hashCode(req.Code))
	if errors.Is(err, store.ErrNoRows) {
		return Credentials{}, ErrInvalidCode
	}
	if err != nil {
		return Credentials{}, fmt.Errorf("get registration code: %w", err)
	}

	secret, secretHash := newSecret()
	id, err := s.q.CreateDevice(ctx, storedevices.CreateDeviceParams{
		UserID:             code.UserID,
		Type:               req.Type,
		Name:               name,
		SecretHash:         secretHash,
		RegistrationCodeID: code.ID,
	})
	// registration_code_id is unique, so a used code fails here.
	if store.IsUniqueViolation(err) {
		return Credentials{}, ErrInvalidCode
	}
	if err != nil {
		return Credentials{}, fmt.Errorf("create device: %w", err)
	}
	return Credentials{DeviceID: id, Secret: secret}, nil
}

// validate checks req and returns the device name to store.
func validate(req Request) (string, error) {
	if strings.TrimSpace(req.Code) == "" {
		return "", &ValidationError{Field: "code", Message: "is required"}
	}
	if !typePattern.MatchString(req.Type) {
		return "", &ValidationError{Field: "type", Message: "must be 1-64 lowercase letters, digits, or hyphens"}
	}
	name := strings.TrimSpace(req.Name)
	if name == "" {
		return req.Type, nil
	}
	if utf8.RuneCountInString(name) > maxNameLen {
		return "", &ValidationError{Field: "name", Message: fmt.Sprintf("must be at most %d characters", maxNameLen)}
	}
	return name, nil
}

// hashCode returns the stored form of a registration code: SHA-256 of the code
// trimmed and uppercased. The api hashes codes the same way when it issues them.
func hashCode(code string) []byte {
	sum := sha256.Sum256([]byte(strings.ToUpper(strings.TrimSpace(code))))
	return sum[:]
}

// newSecret returns a random device secret and the hash to store for it.
func newSecret() (string, []byte) {
	b := make([]byte, secretLen)
	_, _ = rand.Read(b) // never returns an error
	secret := base64.RawURLEncoding.EncodeToString(b)
	return secret, hashSecret(secret)
}

func hashSecret(secret string) []byte {
	sum := sha256.Sum256([]byte(secret))
	return sum[:]
}
