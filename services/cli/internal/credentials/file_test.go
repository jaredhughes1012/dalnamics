package credentials

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newTestFileStore(t *testing.T) (*FileStore, string) {
	t.Helper()
	dir := t.TempDir()
	t.Setenv(ConfigDirEnv, dir)
	f, err := NewFileStore()
	require.NoError(t, err)
	return f, dir
}

func TestFileStoreRoundTrip(t *testing.T) {
	f, dir := newTestFileStore(t)
	local := Credentials{AccessToken: "a1", RefreshToken: "r1"}
	prod := Credentials{AccessToken: "a2", RefreshToken: "r2"}

	_, err := f.Load("http://localhost:8080")
	assert.ErrorIs(t, err, ErrNotFound)

	require.NoError(t, f.Save("http://localhost:8080", local))
	require.NoError(t, f.Save("https://api.example.com", prod))

	got, err := f.Load("http://localhost:8080")
	require.NoError(t, err)
	assert.Equal(t, local, got)

	require.NoError(t, f.Delete("http://localhost:8080"))
	_, err = f.Load("http://localhost:8080")
	assert.ErrorIs(t, err, ErrNotFound)
	got, err = f.Load("https://api.example.com")
	require.NoError(t, err)
	assert.Equal(t, prod, got)

	info, err := os.Stat(filepath.Join(dir, "credentials.json"))
	require.NoError(t, err)
	assert.Equal(t, os.FileMode(0o600), info.Mode().Perm())
}

func TestNewHonorsStoreEnv(t *testing.T) {
	t.Setenv(ConfigDirEnv, t.TempDir())

	t.Setenv(StoreEnv, "file")
	s, err := New()
	require.NoError(t, err)
	assert.IsType(t, &FileStore{}, s)

	t.Setenv(StoreEnv, "carrier-pigeon")
	_, err = New()
	assert.Error(t, err)
}
