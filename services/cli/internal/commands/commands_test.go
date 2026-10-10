package commands

import (
	"bytes"
	"context"
	"testing"

	"dalnamics/services/cli/internal/credentials"
)

// useTempCredentials points the cli at a throwaway file credential store.
func useTempCredentials(t *testing.T) {
	t.Helper()
	t.Setenv(credentials.StoreEnv, "file")
	t.Setenv(credentials.ConfigDirEnv, t.TempDir())
}

// runRoot executes the cli. Call useTempCredentials first.
func runRoot(t *testing.T, args ...string) (string, error) {
	t.Helper()
	var out bytes.Buffer
	root := NewRootCmd()
	root.SetOut(&out)
	root.SetErr(&out)
	root.SetArgs(args)
	err := root.ExecuteContext(context.Background())
	return out.String(), err
}
