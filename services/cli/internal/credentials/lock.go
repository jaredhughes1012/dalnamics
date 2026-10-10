package credentials

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/gofrs/flock"
)

const lockRetryDelay = 20 * time.Millisecond

// Lock takes an exclusive lock named name that is shared by every cli process
// on the machine, waiting until it is free or ctx is done. Call the returned
// function to release it.
func Lock(ctx context.Context, name string) (unlock func(), err error) {
	dir, err := configDir()
	if err != nil {
		return nil, err
	}
	return lockFile(ctx, filepath.Join(dir, name+".lock"))
}

// lockFile takes an exclusive lock on the file at path, creating it if needed.
func lockFile(ctx context.Context, path string) (unlock func(), err error) {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return nil, err
	}
	l := flock.New(path, flock.SetPermissions(0o600))
	locked, err := l.TryLockContext(ctx, lockRetryDelay)
	if err == nil && !locked {
		err = ctx.Err()
	}
	if err != nil {
		return nil, fmt.Errorf("lock %s: %w", path, err)
	}
	return func() { _ = l.Unlock() }, nil
}

// configDir is $DALNAMICS_CONFIG_DIR, or <user config dir>/dalnamics.
func configDir() (string, error) {
	if dir := os.Getenv(ConfigDirEnv); dir != "" {
		return dir, nil
	}
	base, err := os.UserConfigDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(base, "dalnamics"), nil
}
