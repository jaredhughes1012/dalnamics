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

var token = strings.Repeat("t", minTokenLen)

func TestLoadDefaults(t *testing.T) {
	cfg, err := Load(env(map[string]string{"DATABASE_URL": "postgres://db", "DEVICEMGR_TOKEN": token}))
	require.NoError(t, err)

	assert.Equal(t, ":8081", cfg.Addr)
	assert.Equal(t, "postgres://db", cfg.DatabaseURL)
	assert.Equal(t, []byte(token), cfg.Token)
}

func TestLoadAddr(t *testing.T) {
	cfg, err := Load(env(map[string]string{"DEVICEMGR_ADDR": ":9000", "DATABASE_URL": "postgres://db", "DEVICEMGR_TOKEN": token}))
	require.NoError(t, err)
	assert.Equal(t, ":9000", cfg.Addr)
}

func TestLoadRequiresDatabaseURL(t *testing.T) {
	_, err := Load(env(map[string]string{"DEVICEMGR_TOKEN": token}))
	assert.ErrorContains(t, err, "DATABASE_URL")
}

func TestLoadRequiresToken(t *testing.T) {
	for name, tok := range map[string]string{"missing": "", "short": token[1:]} {
		t.Run(name, func(t *testing.T) {
			_, err := Load(env(map[string]string{"DATABASE_URL": "postgres://db", "DEVICEMGR_TOKEN": tok}))
			assert.ErrorContains(t, err, "DEVICEMGR_TOKEN")
		})
	}
}

func TestLoadReportsAllErrors(t *testing.T) {
	_, err := Load(env(map[string]string{}))

	require.Error(t, err)
	assert.Contains(t, err.Error(), "DATABASE_URL")
	assert.Contains(t, err.Error(), "DEVICEMGR_TOKEN")
}
