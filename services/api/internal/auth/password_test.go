package auth

import (
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestPasswordRoundTrip(t *testing.T) {
	hash, err := hashPassword("correct horse")
	require.NoError(t, err)
	assert.True(t, strings.HasPrefix(hash, "$argon2id$v=19$"))

	ok, err := verifyPassword("correct horse", hash)
	require.NoError(t, err)
	assert.True(t, ok)

	ok, err = verifyPassword("wrong horse", hash)
	require.NoError(t, err)
	assert.False(t, ok)
}

func TestHashPasswordIsSalted(t *testing.T) {
	a, err := hashPassword("same")
	require.NoError(t, err)
	b, err := hashPassword("same")
	require.NoError(t, err)

	assert.NotEqual(t, a, b)
}

func TestVerifyPasswordRejectsMalformedHash(t *testing.T) {
	for _, hash := range []string{"", "plain", "$bcrypt$v=19$m=1,t=1,p=1$c2FsdA$aGFzaA", "$argon2id$v=19$m=1,t=1,p=1$!!$aGFzaA"} {
		_, err := verifyPassword("pw", hash)
		assert.ErrorIs(t, err, errMalformedHash, hash)
	}
}
