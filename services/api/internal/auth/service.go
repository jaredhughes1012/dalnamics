// Package auth implements accounts, sessions, and token issuance.
package auth

import (
	"context"
	"errors"
	"fmt"
	"net/mail"
	"strings"
	"time"
	"unicode/utf8"

	"dalnamics/services/api/internal/store"
	storeauth "dalnamics/services/api/internal/store/auth"
)

// Client identifies what kind of client a session belongs to.
type Client string

const (
	ClientStudio Client = "studio"
	ClientCLI    Client = "cli"
)

const (
	defaultAccessTTL  = 15 * time.Minute
	defaultSessionTTL = 7 * 24 * time.Hour
	cliCodeTTL        = time.Minute

	minPasswordLen = 8
	maxPasswordLen = 128
	maxNameLen     = 100
)

// Config configures a Service.
type Config struct {
	// JWTSecret signs access tokens.
	JWTSecret []byte
	// DevEmails may use DevLogin. Empty disables dev login.
	DevEmails []string
	// AccessTTL defaults to 15 minutes. SessionTTL, the fixed lifetime of a
	// session and so of its refresh tokens, defaults to 7 days.
	AccessTTL  time.Duration
	SessionTTL time.Duration
	// Now defaults to time.Now.
	Now func() time.Time
}

// Service implements account and session operations.
type Service struct {
	q          store.Querier
	jwtSecret  []byte
	devEmails  []string
	accessTTL  time.Duration
	sessionTTL time.Duration
	now        func() time.Time
}

// NewService returns a Service backed by q.
func NewService(q store.Querier, cfg Config) *Service {
	s := &Service{
		q:          q,
		jwtSecret:  cfg.JWTSecret,
		devEmails:  cfg.DevEmails,
		accessTTL:  cfg.AccessTTL,
		sessionTTL: cfg.SessionTTL,
		now:        cfg.Now,
	}
	if s.accessTTL == 0 {
		s.accessTTL = defaultAccessTTL
	}
	if s.sessionTTL == 0 {
		s.sessionTTL = defaultSessionTTL
	}
	if s.now == nil {
		s.now = time.Now
	}
	return s
}

// User is an account.
type User = storeauth.User

// Session is the result of a successful sign-in.
type Session struct {
	User   User
	Tokens Tokens
}

// Signup creates a password account and signs it in.
func (s *Service) Signup(ctx context.Context, email, name, password string, client Client) (Session, error) {
	email, err := normalizeEmail(email)
	if err != nil {
		return Session{}, err
	}
	name = strings.TrimSpace(name)
	if name == "" || utf8.RuneCountInString(name) > maxNameLen {
		return Session{}, &ValidationError{Field: "name", Message: fmt.Sprintf("must be 1-%d characters", maxNameLen)}
	}
	if n := utf8.RuneCountInString(password); n < minPasswordLen || n > maxPasswordLen {
		return Session{}, &ValidationError{Field: "password", Message: fmt.Sprintf("must be %d-%d characters", minPasswordLen, maxPasswordLen)}
	}

	hash, err := hashPassword(password)
	if err != nil {
		return Session{}, err
	}
	user, err := s.q.CreateUser(ctx, storeauth.CreateUserParams{Email: email, Name: name, PasswordHash: &hash})
	if store.IsUniqueViolation(err) {
		return Session{}, ErrEmailTaken
	}
	if err != nil {
		return Session{}, fmt.Errorf("create user: %w", err)
	}
	return s.startSession(ctx, user, client)
}

// Login signs in with an email and password.
func (s *Service) Login(ctx context.Context, email, password string, client Client) (Session, error) {
	email = strings.ToLower(strings.TrimSpace(email))
	user, err := s.q.GetUserByEmail(ctx, email)
	if errors.Is(err, store.ErrNoRows) {
		_, _ = verifyPassword(password, dummyHash)
		return Session{}, ErrInvalidCredentials
	}
	if err != nil {
		return Session{}, fmt.Errorf("get user: %w", err)
	}
	if user.PasswordHash == nil {
		_, _ = verifyPassword(password, dummyHash)
		return Session{}, ErrInvalidCredentials
	}

	ok, err := verifyPassword(password, *user.PasswordHash)
	if err != nil {
		return Session{}, fmt.Errorf("verify password: %w", err)
	}
	if !ok {
		return Session{}, ErrInvalidCredentials
	}
	return s.startSession(ctx, user, client)
}

// DevLogin signs in a configured dev user without a password.
func (s *Service) DevLogin(ctx context.Context, email string, client Client) (Session, error) {
	if !s.DevLoginEnabled() {
		return Session{}, ErrDevLoginDisabled
	}
	if client != ClientStudio && client != ClientCLI {
		return Session{}, &ValidationError{Field: "client", Message: "must be studio or cli"}
	}
	email = strings.ToLower(strings.TrimSpace(email))
	if !s.isDevEmail(email) {
		return Session{}, ErrNotDevUser
	}

	user, err := s.q.GetUserByEmail(ctx, email)
	if errors.Is(err, store.ErrNoRows) {
		return Session{}, ErrNotDevUser
	}
	if err != nil {
		return Session{}, fmt.Errorf("get dev user: %w", err)
	}
	return s.startSession(ctx, user, client)
}

// Refresh redeems a refresh token for a new token pair. The presented refresh
// token is rotated and cannot be used again; presenting it again means it was
// copied, so its session is revoked. Refreshing does not extend the session.
func (s *Service) Refresh(ctx context.Context, refreshToken string) (Tokens, error) {
	newToken, newHash, err := newOpaqueToken()
	if err != nil {
		return Tokens{}, err
	}
	hash := hashToken(refreshToken)
	session, err := s.q.RotateSessionRefreshToken(ctx, storeauth.RotateSessionRefreshTokenParams{
		RefreshTokenHash:    hash,
		NewRefreshTokenHash: newHash,
	})
	if errors.Is(err, store.ErrNoRows) {
		if _, err := s.q.RevokeSessionByRotatedRefreshToken(ctx, hash); err != nil {
			return Tokens{}, fmt.Errorf("revoke session of reused refresh token: %w", err)
		}
		return Tokens{}, ErrInvalidToken
	}
	if err != nil {
		return Tokens{}, fmt.Errorf("rotate refresh token: %w", err)
	}

	access, err := s.issueAccessToken(session.UserID, session.ID)
	if err != nil {
		return Tokens{}, err
	}
	return Tokens{AccessToken: access, RefreshToken: newToken, ExpiresIn: s.accessTTL}, nil
}

// Logout revokes a session, invalidating its access and refresh tokens.
func (s *Service) Logout(ctx context.Context, p Principal) error {
	if err := s.q.RevokeSession(ctx, p.SessionID); err != nil {
		return fmt.Errorf("revoke session: %w", err)
	}
	return nil
}

// Authenticate validates an access token and confirms its session is still active.
func (s *Service) Authenticate(ctx context.Context, accessToken string) (Principal, error) {
	p, err := s.parseAccessToken(accessToken)
	if err != nil {
		return Principal{}, err
	}
	session, err := s.q.GetActiveSession(ctx, p.SessionID)
	if errors.Is(err, store.ErrNoRows) || (err == nil && session.UserID != p.UserID) {
		return Principal{}, ErrInvalidToken
	}
	if err != nil {
		return Principal{}, fmt.Errorf("get session: %w", err)
	}
	return p, nil
}

// Me returns the authenticated user.
func (s *Service) Me(ctx context.Context, p Principal) (User, error) {
	user, err := s.q.GetUserByID(ctx, p.UserID)
	if errors.Is(err, store.ErrNoRows) {
		return User{}, ErrInvalidToken
	}
	if err != nil {
		return User{}, fmt.Errorf("get user: %w", err)
	}
	return user, nil
}

// AuthorizeCLI issues a single-use code that a cli listening on redirectURI
// redeems, with the PKCE verifier for codeChallenge, via ExchangeCLICode.
func (s *Service) AuthorizeCLI(ctx context.Context, p Principal, codeChallenge, redirectURI string) (string, error) {
	if !validChallenge(codeChallenge) {
		return "", &ValidationError{Field: "code_challenge", Message: "must be a base64url SHA-256 (S256)"}
	}
	if !isLoopbackRedirect(redirectURI) {
		return "", &ValidationError{Field: "redirect_uri", Message: "must be an http loopback URL with a port"}
	}

	code, hash, err := newOpaqueToken()
	if err != nil {
		return "", err
	}
	err = s.q.CreateCLIAuthCode(ctx, storeauth.CreateCLIAuthCodeParams{
		CodeHash:      hash,
		UserID:        p.UserID,
		CodeChallenge: codeChallenge,
		RedirectUri:   redirectURI,
		ExpiresAt:     s.now().Add(cliCodeTTL),
	})
	if err != nil {
		return "", fmt.Errorf("create cli auth code: %w", err)
	}
	return code, nil
}

// ExchangeCLICode redeems a code from AuthorizeCLI for a new cli session.
func (s *Service) ExchangeCLICode(ctx context.Context, code, codeVerifier, redirectURI string) (Session, error) {
	authCode, err := s.q.UseCLIAuthCode(ctx, storeauth.UseCLIAuthCodeParams{
		CodeHash:      hashToken(code),
		CodeChallenge: pkceChallenge(codeVerifier),
		RedirectUri:   redirectURI,
	})
	if errors.Is(err, store.ErrNoRows) {
		return Session{}, ErrInvalidCode
	}
	if err != nil {
		return Session{}, fmt.Errorf("use cli auth code: %w", err)
	}

	user, err := s.q.GetUserByID(ctx, authCode.UserID)
	if err != nil {
		return Session{}, fmt.Errorf("get user: %w", err)
	}
	return s.startSession(ctx, user, ClientCLI)
}

func (s *Service) startSession(ctx context.Context, user User, client Client) (Session, error) {
	refresh, refreshHash, err := newOpaqueToken()
	if err != nil {
		return Session{}, err
	}
	session, err := s.q.CreateSession(ctx, storeauth.CreateSessionParams{
		UserID:           user.ID,
		Client:           string(client),
		RefreshTokenHash: refreshHash,
		ExpiresAt:        s.now().Add(s.sessionTTL),
	})
	if err != nil {
		return Session{}, fmt.Errorf("create session: %w", err)
	}
	access, err := s.issueAccessToken(user.ID, session.ID)
	if err != nil {
		return Session{}, err
	}
	return Session{
		User:   user,
		Tokens: Tokens{AccessToken: access, RefreshToken: refresh, ExpiresIn: s.accessTTL},
	}, nil
}

func normalizeEmail(email string) (string, error) {
	email = strings.ToLower(strings.TrimSpace(email))
	addr, err := mail.ParseAddress(email)
	if err != nil || addr.Address != email {
		return "", &ValidationError{Field: "email", Message: "must be a valid email address"}
	}
	return email, nil
}
