package auth

import (
	"crypto/sha256"
	"encoding/base64"
	"testing"

	"github.com/stretchr/testify/assert"
)

func challengeFor(verifier string) string {
	sum := sha256.Sum256([]byte(verifier))
	return base64.RawURLEncoding.EncodeToString(sum[:])
}

func TestVerifyPKCE(t *testing.T) {
	c := challengeFor("verifier")

	assert.True(t, verifyPKCE("verifier", c))
	assert.False(t, verifyPKCE("other", c))
	assert.True(t, validChallenge(c))
	assert.False(t, validChallenge("short"))
}

func TestIsLoopbackRedirect(t *testing.T) {
	valid := []string{
		"http://127.0.0.1:5555/callback",
		"http://localhost:5555/callback",
		"http://[::1]:5555/callback",
	}
	invalid := []string{
		"http://127.0.0.1/callback",
		"https://127.0.0.1:5555/callback",
		"http://example.com:5555/callback",
		"http://user@127.0.0.1:5555/callback",
		"http://10.0.0.1:5555/callback",
		"not a url",
	}
	for _, u := range valid {
		assert.True(t, isLoopbackRedirect(u), u)
	}
	for _, u := range invalid {
		assert.False(t, isLoopbackRedirect(u), u)
	}
}
