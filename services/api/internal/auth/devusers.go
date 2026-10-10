package auth

import (
	"context"
	"fmt"
	"slices"
	"strings"

	storeauth "dalnamics/services/api/internal/store/auth"
)

// DevLoginEnabled reports whether dev users are configured.
func (s *Service) DevLoginEnabled() bool {
	return len(s.devEmails) > 0
}

// DevEmails returns the configured dev user emails.
func (s *Service) DevEmails() []string {
	return slices.Clone(s.devEmails)
}

// SeedDevUsers creates a passwordless user for every dev email that does not
// already have an account. It fails if any dev email is not a valid address.
func (s *Service) SeedDevUsers(ctx context.Context) error {
	for _, email := range s.devEmails {
		if _, err := normalizeEmail(email); err != nil {
			return fmt.Errorf("dev email %q: %w", email, err)
		}
	}
	for _, email := range s.devEmails {
		err := s.q.CreateUserIfNotExists(ctx, storeauth.CreateUserIfNotExistsParams{
			Email: email,
			Name:  nameFromEmail(email),
		})
		if err != nil {
			return fmt.Errorf("seed dev user %s: %w", email, err)
		}
	}
	return nil
}

func (s *Service) isDevEmail(email string) bool {
	return slices.Contains(s.devEmails, email)
}

// nameFromEmail derives a display name from an email's local part.
func nameFromEmail(email string) string {
	local, _, _ := strings.Cut(email, "@")
	return local
}
