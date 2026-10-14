// Package config loads devicemgr's configuration from the environment.
package config

import (
	"errors"
	"fmt"
)

// Config is devicemgr's runtime configuration.
type Config struct {
	// Addr is the HTTP listen address (DEVICEMGR_ADDR).
	Addr string
	// DatabaseURL is the Postgres connection string (DATABASE_URL).
	DatabaseURL string
	// Token is the shared service token callers present as a bearer token
	// (DEVICEMGR_TOKEN, at least 32 bytes).
	Token []byte
}

const minTokenLen = 32

// Load reads the configuration using getenv (typically os.Getenv).
func Load(getenv func(string) string) (Config, error) {
	cfg := Config{
		Addr:        getenv("DEVICEMGR_ADDR"),
		DatabaseURL: getenv("DATABASE_URL"),
		Token:       []byte(getenv("DEVICEMGR_TOKEN")),
	}
	if cfg.Addr == "" {
		cfg.Addr = ":8081"
	}

	var errs []error
	if cfg.DatabaseURL == "" {
		errs = append(errs, errors.New("DATABASE_URL is required"))
	}
	if len(cfg.Token) < minTokenLen {
		errs = append(errs, fmt.Errorf("DEVICEMGR_TOKEN must be at least %d bytes", minTokenLen))
	}

	return cfg, errors.Join(errs...)
}
