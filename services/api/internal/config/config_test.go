package config

import (
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func env(vars map[string]string) func(string) string {
	return func(k string) string { return vars[k] }
}

var secret = strings.Repeat("s", minJWTSecretLen)

func TestLoadDefaults(t *testing.T) {
	cfg, err := Load(env(map[string]string{"DATABASE_URL": "postgres://db", "JWT_SECRET": secret}))
	require.NoError(t, err)

	assert.Equal(t, ":8080", cfg.Addr)
	assert.False(t, cfg.Debug)
	assert.Empty(t, cfg.DevEmails)
}

func TestLoadRequiresDatabaseAndSecret(t *testing.T) {
	_, err := Load(env(map[string]string{"JWT_SECRET": "short"}))

	require.Error(t, err)
	assert.Contains(t, err.Error(), "DATABASE_URL")
	assert.Contains(t, err.Error(), "JWT_SECRET")
}

func TestLoadDevEmailsRequireDebug(t *testing.T) {
	vars := map[string]string{
		"DATABASE_URL": "postgres://db",
		"JWT_SECRET":   secret,
		"DEV_EMAILS":   " Dev@Example.com,ops@example.com,,dev@example.com ",
	}

	cfg, err := Load(env(vars))
	require.NoError(t, err)
	assert.Empty(t, cfg.DevEmails, "DEV_EMAILS is ignored without DEBUG")

	vars["DEBUG"] = "true"
	cfg, err = Load(env(vars))
	require.NoError(t, err)
	assert.True(t, cfg.Debug)
	assert.Equal(t, []string{"dev@example.com", "ops@example.com"}, cfg.DevEmails)
}

func TestLoadRejectsInvalidDebug(t *testing.T) {
	_, err := Load(env(map[string]string{"DATABASE_URL": "postgres://db", "JWT_SECRET": secret, "DEBUG": "yes please"}))
	assert.ErrorContains(t, err, "DEBUG")
}
