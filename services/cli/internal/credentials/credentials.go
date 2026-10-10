// Package credentials persists the cli's api tokens, keyed by api URL so one
// machine can be logged in to several environments.
package credentials

import (
	"errors"
	"fmt"
	"os"
)

// ErrNotFound is returned by Load when no credentials are stored for an api.
var ErrNotFound = errors.New("not logged in")

// Credentials are the tokens for one api.
type Credentials struct {
	AccessToken  string `json:"access_token"`
	RefreshToken string `json:"refresh_token"`
}

// Store loads and saves Credentials.
type Store interface {
	Load(apiURL string) (Credentials, error)
	Save(apiURL string, c Credentials) error
	Delete(apiURL string) error
}

// StoreEnv selects the backend: "keyring", "file", or empty to use the OS
// keyring when one is available and fall back to a file otherwise.
const StoreEnv = "DALNAMICS_CREDENTIAL_STORE"

// New returns the Store selected by StoreEnv.
func New() (Store, error) {
	switch v := os.Getenv(StoreEnv); v {
	case "keyring":
		return keyringStore{}, nil
	case "file":
		return NewFileStore()
	case "":
		if keyringAvailable() {
			return keyringStore{}, nil
		}
		return NewFileStore()
	default:
		return nil, fmt.Errorf("%s: unknown store %q (want keyring or file)", StoreEnv, v)
	}
}
