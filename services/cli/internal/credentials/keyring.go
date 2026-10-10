package credentials

import (
	"encoding/json"
	"errors"

	"github.com/zalando/go-keyring"
)

const keyringService = "dalnamics-cli"

// keyringStore keeps credentials in the OS keychain (macOS Keychain, Linux
// Secret Service, Windows Credential Manager).
type keyringStore struct{}

func (keyringStore) Load(apiURL string) (Credentials, error) {
	secret, err := keyring.Get(keyringService, apiURL)
	if errors.Is(err, keyring.ErrNotFound) {
		return Credentials{}, ErrNotFound
	}
	if err != nil {
		return Credentials{}, err
	}
	var c Credentials
	err = json.Unmarshal([]byte(secret), &c)
	return c, err
}

func (keyringStore) Save(apiURL string, c Credentials) error {
	b, err := json.Marshal(c)
	if err != nil {
		return err
	}
	return keyring.Set(keyringService, apiURL, string(b))
}

func (keyringStore) Delete(apiURL string) error {
	err := keyring.Delete(keyringService, apiURL)
	if errors.Is(err, keyring.ErrNotFound) {
		return nil
	}
	return err
}

// keyringAvailable reports whether the OS keyring can be used; a missing item
// is the expected answer, anything else means there is no usable keyring
// (e.g. a headless Linux container without Secret Service).
func keyringAvailable() bool {
	_, err := keyring.Get(keyringService, "availability-probe")
	return err == nil || errors.Is(err, keyring.ErrNotFound)
}
