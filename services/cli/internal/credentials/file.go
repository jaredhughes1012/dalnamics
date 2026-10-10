package credentials

import (
	"encoding/json"
	"errors"
	"io/fs"
	"os"
	"path/filepath"
)

// ConfigDirEnv overrides the directory the file store writes to.
const ConfigDirEnv = "DALNAMICS_CONFIG_DIR"

// FileStore keeps credentials in an owner-only JSON file. It is the fallback
// when no OS keyring is available.
type FileStore struct {
	path string
}

// NewFileStore returns a FileStore in $DALNAMICS_CONFIG_DIR, or in
// <user config dir>/dalnamics.
func NewFileStore() (*FileStore, error) {
	dir := os.Getenv(ConfigDirEnv)
	if dir == "" {
		base, err := os.UserConfigDir()
		if err != nil {
			return nil, err
		}
		dir = filepath.Join(base, "dalnamics")
	}
	return &FileStore{path: filepath.Join(dir, "credentials.json")}, nil
}

func (f *FileStore) Load(apiURL string) (Credentials, error) {
	all, err := f.read()
	if err != nil {
		return Credentials{}, err
	}
	c, ok := all[apiURL]
	if !ok {
		return Credentials{}, ErrNotFound
	}
	return c, nil
}

func (f *FileStore) Save(apiURL string, c Credentials) error {
	all, err := f.read()
	if err != nil {
		return err
	}
	all[apiURL] = c
	return f.write(all)
}

func (f *FileStore) Delete(apiURL string) error {
	all, err := f.read()
	if err != nil {
		return err
	}
	delete(all, apiURL)
	return f.write(all)
}

func (f *FileStore) read() (map[string]Credentials, error) {
	all := map[string]Credentials{}
	b, err := os.ReadFile(f.path)
	if errors.Is(err, fs.ErrNotExist) {
		return all, nil
	}
	if err != nil {
		return nil, err
	}
	err = json.Unmarshal(b, &all)
	return all, err
}

// write replaces the file atomically so a crash never leaves partial JSON.
func (f *FileStore) write(all map[string]Credentials) error {
	if err := os.MkdirAll(filepath.Dir(f.path), 0o700); err != nil {
		return err
	}
	b, err := json.MarshalIndent(all, "", "  ")
	if err != nil {
		return err
	}
	tmp, err := os.CreateTemp(filepath.Dir(f.path), ".credentials-*")
	if err != nil {
		return err
	}
	defer os.Remove(tmp.Name())
	if err := tmp.Chmod(0o600); err != nil {
		tmp.Close()
		return err
	}
	if _, err := tmp.Write(b); err != nil {
		tmp.Close()
		return err
	}
	if err := tmp.Close(); err != nil {
		return err
	}
	return os.Rename(tmp.Name(), f.path)
}
