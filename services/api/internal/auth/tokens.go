package auth

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"errors"
	"fmt"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

const accessTokenIssuer = "dalnamics-api"

// accessClaims are the claims carried by an access token.
type accessClaims struct {
	SessionID string `json:"sid"`
	jwt.RegisteredClaims
}

// Principal identifies the caller of an authenticated request.
type Principal struct {
	UserID    uuid.UUID
	SessionID uuid.UUID
}

func (s *Service) issueAccessToken(userID, sessionID uuid.UUID) (string, error) {
	now := s.now()
	claims := accessClaims{
		SessionID: sessionID.String(),
		RegisteredClaims: jwt.RegisteredClaims{
			Issuer:    accessTokenIssuer,
			Subject:   userID.String(),
			IssuedAt:  jwt.NewNumericDate(now),
			ExpiresAt: jwt.NewNumericDate(now.Add(s.accessTTL)),
		},
	}
	return jwt.NewWithClaims(jwt.SigningMethodHS256, claims).SignedString(s.jwtSecret)
}

func (s *Service) parseAccessToken(token string) (Principal, error) {
	var claims accessClaims
	_, err := jwt.ParseWithClaims(token, &claims, func(*jwt.Token) (any, error) { return s.jwtSecret, nil },
		jwt.WithValidMethods([]string{jwt.SigningMethodHS256.Alg()}),
		jwt.WithIssuer(accessTokenIssuer),
		jwt.WithExpirationRequired(),
		jwt.WithTimeFunc(s.now),
	)
	if err != nil {
		return Principal{}, fmt.Errorf("%w: %w", ErrInvalidToken, err)
	}

	userID, uerr := uuid.Parse(claims.Subject)
	sessionID, serr := uuid.Parse(claims.SessionID)
	if err := errors.Join(uerr, serr); err != nil {
		return Principal{}, fmt.Errorf("%w: %w", ErrInvalidToken, err)
	}
	return Principal{UserID: userID, SessionID: sessionID}, nil
}

// newOpaqueToken returns a random URL-safe token and the hash to store for it.
func newOpaqueToken() (token string, hash []byte, err error) {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		return "", nil, err
	}
	token = base64.RawURLEncoding.EncodeToString(b)
	return token, hashToken(token), nil
}

// hashToken returns the SHA-256 of an opaque token. Tokens are high-entropy,
// so a fast unsalted hash is sufficient.
func hashToken(token string) []byte {
	sum := sha256.Sum256([]byte(token))
	return sum[:]
}

// Tokens is an access/refresh token pair.
type Tokens struct {
	AccessToken  string
	RefreshToken string
	ExpiresIn    time.Duration
}
