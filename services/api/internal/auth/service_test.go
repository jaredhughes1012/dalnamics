package auth

import (
	"context"
	"errors"
	"sync"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"go.uber.org/mock/gomock"

	"dalnamics/services/api/internal/store"
	storeauth "dalnamics/services/api/internal/store/auth"
	"dalnamics/services/api/internal/store/mockstore"
)

var testSecret = []byte("test-secret-that-is-at-least-32-bytes")

type fakeClock struct {
	mu  sync.Mutex
	now time.Time
}

func (c *fakeClock) Now() time.Time {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.now
}

func (c *fakeClock) Advance(d time.Duration) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.now = c.now.Add(d)
}

func newTestService(t *testing.T, devEmails ...string) (*Service, *fakeClock) {
	t.Helper()
	s, _, clock := newMockedService(t, devEmails...)
	return s, clock
}

func newMockedService(t *testing.T, devEmails ...string) (*Service, *mockstore.MockQuerier, *fakeClock) {
	t.Helper()
	q := mockstore.NewMockQuerier(gomock.NewController(t))
	clock := &fakeClock{now: time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)}
	s := NewService(q, Config{JWTSecret: testSecret, DevEmails: devEmails, Now: clock.Now})
	return s, q, clock
}

func testUser(passwordHash *string) storeauth.User {
	return storeauth.User{ID: uuid.New(), Email: "jane@example.com", Name: "Jane", PasswordHash: passwordHash}
}

// expectSession expects a new session for user and returns its id.
func expectSession(q *mockstore.MockQuerier, user storeauth.User, client Client, clock *fakeClock) uuid.UUID {
	id := uuid.New()
	q.EXPECT().CreateSession(gomock.Any(), gomock.Cond(func(p storeauth.CreateSessionParams) bool {
		return p.UserID == user.ID && p.Client == string(client) && len(p.RefreshTokenHash) == 32 &&
			p.ExpiresAt.Equal(clock.Now().Add(defaultRefreshTTL))
	})).DoAndReturn(func(_ context.Context, p storeauth.CreateSessionParams) (storeauth.Session, error) {
		return storeauth.Session{ID: id, UserID: p.UserID, Client: p.Client, RefreshTokenHash: p.RefreshTokenHash}, nil
	})
	return id
}

func assertSessionTokens(t *testing.T, s *Service, sess Session, sessionID uuid.UUID) {
	t.Helper()
	p, err := s.parseAccessToken(sess.Tokens.AccessToken)
	require.NoError(t, err)
	assert.Equal(t, Principal{UserID: sess.User.ID, SessionID: sessionID}, p)
	assert.NotEmpty(t, sess.Tokens.RefreshToken)
	assert.Equal(t, defaultAccessTTL, sess.Tokens.ExpiresIn)
}

func TestSignup(t *testing.T) {
	s, q, clock := newMockedService(t)
	user := testUser(nil)
	q.EXPECT().CreateUser(gomock.Any(), gomock.Any()).DoAndReturn(
		func(_ context.Context, p storeauth.CreateUserParams) (storeauth.User, error) {
			assert.Equal(t, "jane@example.com", p.Email)
			assert.Equal(t, "Jane", p.Name)
			require.NotNil(t, p.PasswordHash)
			ok, err := verifyPassword("hunter22", *p.PasswordHash)
			require.NoError(t, err)
			assert.True(t, ok, "stored hash must verify the password")
			user.PasswordHash = p.PasswordHash
			return user, nil
		})
	sid := expectSession(q, user, ClientStudio, clock)

	sess, err := s.Signup(context.Background(), "  Jane@Example.com ", " Jane ", "hunter22", ClientStudio)

	require.NoError(t, err)
	assert.Equal(t, user.ID, sess.User.ID)
	assertSessionTokens(t, s, sess, sid)
}

func TestSignupValidation(t *testing.T) {
	s, _ := newTestService(t)
	cases := []struct {
		name, email, userName, password, field string
	}{
		{"bad email", "nope", "Jane", "hunter22", "email"},
		{"display email", "Jane <jane@example.com>", "Jane", "hunter22", "email"},
		{"empty name", "jane@example.com", "  ", "hunter22", "name"},
		{"short password", "jane@example.com", "Jane", "short", "password"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, err := s.Signup(context.Background(), tc.email, tc.userName, tc.password, ClientStudio)

			var verr *ValidationError
			require.ErrorAs(t, err, &verr)
			assert.Equal(t, tc.field, verr.Field)
		})
	}
}

func TestSignupEmailTaken(t *testing.T) {
	s, q, _ := newMockedService(t)
	q.EXPECT().CreateUser(gomock.Any(), gomock.Any()).Return(storeauth.User{}, &pgconn.PgError{Code: "23505"})

	_, err := s.Signup(context.Background(), "jane@example.com", "Jane", "hunter22", ClientStudio)

	assert.ErrorIs(t, err, ErrEmailTaken)
}

func TestLogin(t *testing.T) {
	s, q, clock := newMockedService(t)
	hash, err := hashPassword("hunter22")
	require.NoError(t, err)
	user := testUser(&hash)
	q.EXPECT().GetUserByEmail(gomock.Any(), "jane@example.com").Return(user, nil)
	sid := expectSession(q, user, ClientStudio, clock)

	sess, err := s.Login(context.Background(), "JANE@example.com", "hunter22", ClientStudio)

	require.NoError(t, err)
	assert.Equal(t, user, sess.User)
	assertSessionTokens(t, s, sess, sid)
}

func TestLoginRejects(t *testing.T) {
	hash, err := hashPassword("hunter22")
	require.NoError(t, err)

	cases := []struct {
		name  string
		user  storeauth.User
		err   error
		input string
	}{
		{"unknown email", storeauth.User{}, store.ErrNoRows, "hunter22"},
		{"wrong password", testUser(&hash), nil, "wrong-password"},
		{"passwordless user", testUser(nil), nil, "hunter22"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			s, q, _ := newMockedService(t)
			q.EXPECT().GetUserByEmail(gomock.Any(), "jane@example.com").Return(tc.user, tc.err)

			_, err := s.Login(context.Background(), "jane@example.com", tc.input, ClientStudio)

			assert.ErrorIs(t, err, ErrInvalidCredentials)
		})
	}
}

func TestLoginStoreError(t *testing.T) {
	s, q, _ := newMockedService(t)
	boom := errors.New("boom")
	q.EXPECT().GetUserByEmail(gomock.Any(), gomock.Any()).Return(storeauth.User{}, boom)

	_, err := s.Login(context.Background(), "jane@example.com", "hunter22", ClientStudio)

	assert.ErrorIs(t, err, boom)
}

func TestRefresh(t *testing.T) {
	s, q, clock := newMockedService(t)
	session := storeauth.Session{ID: uuid.New(), UserID: uuid.New()}
	q.EXPECT().RotateSessionRefreshToken(gomock.Any(), gomock.Cond(func(p storeauth.RotateSessionRefreshTokenParams) bool {
		return string(p.RefreshTokenHash) == string(hashToken("old-token")) &&
			len(p.NewRefreshTokenHash) == 32 &&
			p.ExpiresAt.Equal(clock.Now().Add(defaultRefreshTTL))
	})).Return(session, nil)

	tokens, err := s.Refresh(context.Background(), "old-token")

	require.NoError(t, err)
	assert.NotEqual(t, "old-token", tokens.RefreshToken)
	p, err := s.parseAccessToken(tokens.AccessToken)
	require.NoError(t, err)
	assert.Equal(t, Principal{UserID: session.UserID, SessionID: session.ID}, p)
}

func TestRefreshRejectsUnknownToken(t *testing.T) {
	s, q, _ := newMockedService(t)
	q.EXPECT().RotateSessionRefreshToken(gomock.Any(), gomock.Any()).Return(storeauth.Session{}, store.ErrNoRows)

	_, err := s.Refresh(context.Background(), "used-or-revoked")

	assert.ErrorIs(t, err, ErrInvalidToken)
}

func TestLogout(t *testing.T) {
	s, q, _ := newMockedService(t)
	p := Principal{UserID: uuid.New(), SessionID: uuid.New()}
	q.EXPECT().RevokeSession(gomock.Any(), p.SessionID).Return(nil)

	require.NoError(t, s.Logout(context.Background(), p))
}

func TestAuthenticate(t *testing.T) {
	s, q, _ := newMockedService(t)
	p := Principal{UserID: uuid.New(), SessionID: uuid.New()}
	token, err := s.issueAccessToken(p.UserID, p.SessionID)
	require.NoError(t, err)
	q.EXPECT().GetActiveSession(gomock.Any(), p.SessionID).Return(storeauth.Session{ID: p.SessionID, UserID: p.UserID}, nil)

	got, err := s.Authenticate(context.Background(), token)

	require.NoError(t, err)
	assert.Equal(t, p, got)
}

func TestAuthenticateRejectsRevokedSession(t *testing.T) {
	s, q, _ := newMockedService(t)
	token, err := s.issueAccessToken(uuid.New(), uuid.New())
	require.NoError(t, err)
	q.EXPECT().GetActiveSession(gomock.Any(), gomock.Any()).Return(storeauth.Session{}, store.ErrNoRows)

	_, err = s.Authenticate(context.Background(), token)

	assert.ErrorIs(t, err, ErrInvalidToken)
}

func TestAuthenticateRejectsSessionOfAnotherUser(t *testing.T) {
	s, q, _ := newMockedService(t)
	sid := uuid.New()
	token, err := s.issueAccessToken(uuid.New(), sid)
	require.NoError(t, err)
	q.EXPECT().GetActiveSession(gomock.Any(), sid).Return(storeauth.Session{ID: sid, UserID: uuid.New()}, nil)

	_, err = s.Authenticate(context.Background(), token)

	assert.ErrorIs(t, err, ErrInvalidToken)
}

func TestAuthenticateRejectsGarbage(t *testing.T) {
	s, _ := newTestService(t)

	_, err := s.Authenticate(context.Background(), "not-a-jwt")

	assert.ErrorIs(t, err, ErrInvalidToken)
}

func TestDevLogin(t *testing.T) {
	s, q, clock := newMockedService(t, "dev@dalnamics.local")
	user := storeauth.User{ID: uuid.New(), Email: "dev@dalnamics.local", Name: "dev"}
	q.EXPECT().GetUserByEmail(gomock.Any(), "dev@dalnamics.local").Return(user, nil)
	sid := expectSession(q, user, ClientCLI, clock)

	sess, err := s.DevLogin(context.Background(), " Dev@Dalnamics.local", ClientCLI)

	require.NoError(t, err)
	assertSessionTokens(t, s, sess, sid)
}

func TestDevLoginRejects(t *testing.T) {
	disabled, _ := newTestService(t)
	_, err := disabled.DevLogin(context.Background(), "dev@dalnamics.local", ClientStudio)
	assert.ErrorIs(t, err, ErrDevLoginDisabled)

	enabled, _ := newTestService(t, "dev@dalnamics.local")
	_, err = enabled.DevLogin(context.Background(), "jane@example.com", ClientStudio)
	assert.ErrorIs(t, err, ErrNotDevUser)

	_, err = enabled.DevLogin(context.Background(), "dev@dalnamics.local", Client("bogus"))
	var verr *ValidationError
	assert.ErrorAs(t, err, &verr)
}

func TestSeedDevUsers(t *testing.T) {
	s, q, _ := newMockedService(t, "dev@dalnamics.local", "e2e@dalnamics.local")
	q.EXPECT().CreateUserIfNotExists(gomock.Any(), storeauth.CreateUserIfNotExistsParams{Email: "dev@dalnamics.local", Name: "dev"})
	q.EXPECT().CreateUserIfNotExists(gomock.Any(), storeauth.CreateUserIfNotExistsParams{Email: "e2e@dalnamics.local", Name: "e2e"})

	require.NoError(t, s.SeedDevUsers(context.Background()))
	assert.True(t, s.DevLoginEnabled())
	assert.Equal(t, []string{"dev@dalnamics.local", "e2e@dalnamics.local"}, s.DevEmails())
}

const testRedirect = "http://127.0.0.1:5555/callback"

func TestAuthorizeCLI(t *testing.T) {
	s, q, clock := newMockedService(t)
	p := Principal{UserID: uuid.New(), SessionID: uuid.New()}
	challenge := challengeFor("verifier")
	var stored storeauth.CreateCLIAuthCodeParams
	q.EXPECT().CreateCLIAuthCode(gomock.Any(), gomock.Any()).DoAndReturn(
		func(_ context.Context, arg storeauth.CreateCLIAuthCodeParams) error {
			stored = arg
			return nil
		})

	code, err := s.AuthorizeCLI(context.Background(), p, challenge, testRedirect)

	require.NoError(t, err)
	assert.Equal(t, hashToken(code), stored.CodeHash)
	assert.Equal(t, p.UserID, stored.UserID)
	assert.Equal(t, challenge, stored.CodeChallenge)
	assert.Equal(t, testRedirect, stored.RedirectUri)
	assert.Equal(t, clock.Now().Add(cliCodeTTL), stored.ExpiresAt)
}

func TestAuthorizeCLIValidation(t *testing.T) {
	s, _ := newTestService(t)
	p := Principal{UserID: uuid.New(), SessionID: uuid.New()}
	var verr *ValidationError

	_, err := s.AuthorizeCLI(context.Background(), p, "plain-challenge", testRedirect)
	require.ErrorAs(t, err, &verr)
	assert.Equal(t, "code_challenge", verr.Field)

	_, err = s.AuthorizeCLI(context.Background(), p, challengeFor("v"), "https://evil.example.com/cb")
	require.ErrorAs(t, err, &verr)
	assert.Equal(t, "redirect_uri", verr.Field)
}

func TestExchangeCLICode(t *testing.T) {
	s, q, clock := newMockedService(t)
	user := testUser(nil)
	q.EXPECT().UseCLIAuthCode(gomock.Any(), hashToken("the-code")).Return(storeauth.CliAuthCode{
		UserID: user.ID, CodeChallenge: challengeFor("verifier"), RedirectUri: testRedirect,
	}, nil)
	q.EXPECT().GetUserByID(gomock.Any(), user.ID).Return(user, nil)
	sid := expectSession(q, user, ClientCLI, clock)

	sess, err := s.ExchangeCLICode(context.Background(), "the-code", "verifier", testRedirect)

	require.NoError(t, err)
	assertSessionTokens(t, s, sess, sid)
}

func TestExchangeCLICodeRejects(t *testing.T) {
	valid := storeauth.CliAuthCode{UserID: uuid.New(), CodeChallenge: challengeFor("verifier"), RedirectUri: testRedirect}
	cases := []struct {
		name               string
		code               storeauth.CliAuthCode
		err                error
		verifier, redirect string
	}{
		{"unknown, used, or expired code", storeauth.CliAuthCode{}, store.ErrNoRows, "verifier", testRedirect},
		{"wrong verifier", valid, nil, "attacker", testRedirect},
		{"different redirect", valid, nil, "verifier", "http://127.0.0.1:6666/callback"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			s, q, _ := newMockedService(t)
			q.EXPECT().UseCLIAuthCode(gomock.Any(), gomock.Any()).Return(tc.code, tc.err)

			_, err := s.ExchangeCLICode(context.Background(), "the-code", tc.verifier, tc.redirect)

			assert.ErrorIs(t, err, ErrInvalidCode)
		})
	}
}

func TestMe(t *testing.T) {
	s, q, _ := newMockedService(t)
	user := testUser(nil)
	q.EXPECT().GetUserByID(gomock.Any(), user.ID).Return(user, nil)

	got, err := s.Me(context.Background(), Principal{UserID: user.ID})

	require.NoError(t, err)
	assert.Equal(t, user, got)
}
