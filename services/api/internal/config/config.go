// Package config loads the api's configuration from the environment.
package config

import (
	"errors"
	"fmt"
	"strconv"
	"strings"
)

// Config is the api's runtime configuration.
type Config struct {
	// Addr is the HTTP listen address (API_ADDR).
	Addr string
	// DatabaseURL is the Postgres connection string (DATABASE_URL).
	DatabaseURL string
	// JWTSecret signs access tokens (JWT_SECRET, at least 32 bytes).
	JWTSecret []byte
	// Debug enables development-only features such as dev login (DEBUG).
	Debug bool
	// DevEmails are users seeded at startup and allowed to use dev login
	// (DEV_EMAILS, comma separated). Always empty unless Debug is set.
	DevEmails []string
}

const minJWTSecretLen = 32

// Load reads the configuration using getenv (typically os.Getenv).
func Load(getenv func(string) string) (Config, error) {
	cfg := Config{
		Addr:        getenv("API_ADDR"),
		DatabaseURL: getenv("DATABASE_URL"),
		JWTSecret:   []byte(getenv("JWT_SECRET")),
	}
	if cfg.Addr == "" {
		cfg.Addr = ":8080"
	}

	var errs []error
	if cfg.DatabaseURL == "" {
		errs = append(errs, errors.New("DATABASE_URL is required"))
	}
	if len(cfg.JWTSecret) < minJWTSecretLen {
		errs = append(errs, fmt.Errorf("JWT_SECRET must be at least %d bytes", minJWTSecretLen))
	}
	if v := getenv("DEBUG"); v != "" {
		debug, err := strconv.ParseBool(v)
		if err != nil {
			errs = append(errs, fmt.Errorf("DEBUG: %w", err))
		}
		cfg.Debug = debug
	}
	if cfg.Debug {
		cfg.DevEmails = parseEmails(getenv("DEV_EMAILS"))
	}

	return cfg, errors.Join(errs...)
}

func parseEmails(list string) []string {
	var emails []string
	seen := map[string]bool{}
	for _, e := range strings.Split(list, ",") {
		e = strings.ToLower(strings.TrimSpace(e))
		if e != "" && !seen[e] {
			seen[e] = true
			emails = append(emails, e)
		}
	}
	return emails
}
