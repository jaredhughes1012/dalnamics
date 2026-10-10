package auth

import (
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestAccessTokenRoundTrip(t *testing.T) {
	s, _ := newTestService(t)
	userID, sessionID := uuid.New(), uuid.New()

	token, err := s.issueAccessToken(userID, sessionID)
	require.NoError(t, err)

	p, err := s.parseAccessToken(token)
	require.NoError(t, err)
	assert.Equal(t, Principal{UserID: userID, SessionID: sessionID}, p)
}

func TestAccessTokenExpires(t *testing.T) {
	s, clock := newTestService(t)
	token, err := s.issueAccessToken(uuid.New(), uuid.New())
	require.NoError(t, err)

	clock.Advance(s.accessTTL + time.Second)

	_, err = s.parseAccessToken(token)
	assert.ErrorIs(t, err, ErrInvalidToken)
}

func TestAccessTokenRejectsOtherSecret(t *testing.T) {
	s, _ := newTestService(t)
	other := NewService(nil, Config{JWTSecret: []byte("a-completely-different-secret-value"), Now: s.now})
	token, err := other.issueAccessToken(uuid.New(), uuid.New())
	require.NoError(t, err)

	_, err = s.parseAccessToken(token)
	assert.ErrorIs(t, err, ErrInvalidToken)
}

func TestAccessTokenRejectsNoneAlg(t *testing.T) {
	s, _ := newTestService(t)
	token, err := jwt.NewWithClaims(jwt.SigningMethodNone, jwt.MapClaims{
		"sub": uuid.NewString(), "sid": uuid.NewString(), "iss": accessTokenIssuer,
		"exp": s.now().Add(time.Minute).Unix(),
	}).SignedString(jwt.UnsafeAllowNoneSignatureType)
	require.NoError(t, err)

	_, err = s.parseAccessToken(token)
	assert.ErrorIs(t, err, ErrInvalidToken)
}

func TestOpaqueToken(t *testing.T) {
	token, hash, err := newOpaqueToken()
	require.NoError(t, err)

	assert.Len(t, token, 43)
	assert.Equal(t, hashToken(token), hash)
}
