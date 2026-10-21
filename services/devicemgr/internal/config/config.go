// Package config loads devicemgr's configuration from the environment.
package config

import (
	"errors"
	"fmt"
	"net/url"
	"time"
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
	// MQTTURL is the MQTT broker URL devicemgr connects to as a client
	// (DEVICEMGR_MQTT_URL, e.g. mqtt://mosquitto:1883).
	MQTTURL *url.URL
	// MQTTPassword is devicemgr's broker password as the superuser
	// "devicemgr" (DEVICEMGR_MQTT_PASSWORD, at least 32 bytes).
	MQTTPassword []byte
	// OfflineAfter is how long a device may stay silent before the sweep marks
	// it offline (DEVICEMGR_OFFLINE_AFTER, a Go duration, default 90s).
	OfflineAfter time.Duration
	// SweepInterval is how often the sweep runs (DEVICEMGR_SWEEP_INTERVAL, a
	// Go duration, default 15s, at most OfflineAfter).
	SweepInterval time.Duration
}

const (
	minTokenLen        = 32
	minMQTTPasswordLen = 32

	defaultOfflineAfter  = 90 * time.Second
	defaultSweepInterval = 15 * time.Second
)

// Load reads the configuration using getenv (typically os.Getenv).
func Load(getenv func(string) string) (Config, error) {
	cfg := Config{
		Addr:         getenv("DEVICEMGR_ADDR"),
		DatabaseURL:  getenv("DATABASE_URL"),
		Token:        []byte(getenv("DEVICEMGR_TOKEN")),
		MQTTPassword: []byte(getenv("DEVICEMGR_MQTT_PASSWORD")),
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

	switch rawURL := getenv("DEVICEMGR_MQTT_URL"); {
	case rawURL == "":
		errs = append(errs, errors.New("DEVICEMGR_MQTT_URL is required"))
	default:
		u, err := url.Parse(rawURL)
		if err != nil || u.Host == "" || (u.Scheme != "mqtt" && u.Scheme != "tcp") {
			errs = append(errs, errors.New("DEVICEMGR_MQTT_URL must be an mqtt://host:port URL"))
		} else {
			cfg.MQTTURL = u
		}
	}
	if len(cfg.MQTTPassword) < minMQTTPasswordLen {
		errs = append(errs, fmt.Errorf("DEVICEMGR_MQTT_PASSWORD must be at least %d bytes", minMQTTPasswordLen))
	}

	offlineAfter, err := duration(getenv, "DEVICEMGR_OFFLINE_AFTER", defaultOfflineAfter)
	if err != nil {
		errs = append(errs, err)
	}
	sweepInterval, err := duration(getenv, "DEVICEMGR_SWEEP_INTERVAL", defaultSweepInterval)
	if err != nil {
		errs = append(errs, err)
	}
	if offlineAfter > 0 && sweepInterval > offlineAfter {
		errs = append(errs, errors.New("DEVICEMGR_SWEEP_INTERVAL must not exceed DEVICEMGR_OFFLINE_AFTER"))
	}
	cfg.OfflineAfter, cfg.SweepInterval = offlineAfter, sweepInterval

	return cfg, errors.Join(errs...)
}

// duration reads a positive Go duration from key, or def when key is unset.
func duration(getenv func(string) string, key string, def time.Duration) (time.Duration, error) {
	raw := getenv(key)
	if raw == "" {
		return def, nil
	}
	d, err := time.ParseDuration(raw)
	if err != nil || d <= 0 {
		return 0, fmt.Errorf("%s must be a positive duration such as 90s", key)
	}
	return d, nil
}
