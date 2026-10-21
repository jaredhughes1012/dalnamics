package config

import (
	"strings"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func env(vars map[string]string) func(string) string {
	return func(k string) string { return vars[k] }
}

var (
	token        = strings.Repeat("t", minTokenLen)
	mqttPassword = strings.Repeat("m", minMQTTPasswordLen)
)

// valid returns a complete environment with overrides applied.
func valid(overrides map[string]string) map[string]string {
	vars := map[string]string{
		"DATABASE_URL":            "postgres://db",
		"DEVICEMGR_TOKEN":         token,
		"DEVICEMGR_MQTT_URL":      "mqtt://mosquitto:1883",
		"DEVICEMGR_MQTT_PASSWORD": mqttPassword,
	}
	for k, v := range overrides {
		vars[k] = v
	}
	return vars
}

func TestLoadDefaults(t *testing.T) {
	cfg, err := Load(env(valid(nil)))
	require.NoError(t, err)

	assert.Equal(t, ":8081", cfg.Addr)
	assert.Equal(t, "postgres://db", cfg.DatabaseURL)
	assert.Equal(t, []byte(token), cfg.Token)
	assert.Equal(t, "mqtt://mosquitto:1883", cfg.MQTTURL.String())
	assert.Equal(t, []byte(mqttPassword), cfg.MQTTPassword)
	assert.Equal(t, 90*time.Second, cfg.OfflineAfter)
	assert.Equal(t, 15*time.Second, cfg.SweepInterval)
}

func TestLoadAddr(t *testing.T) {
	cfg, err := Load(env(valid(map[string]string{"DEVICEMGR_ADDR": ":9000"})))
	require.NoError(t, err)
	assert.Equal(t, ":9000", cfg.Addr)
}

func TestLoadRequiresDatabaseURL(t *testing.T) {
	_, err := Load(env(valid(map[string]string{"DATABASE_URL": ""})))
	assert.ErrorContains(t, err, "DATABASE_URL")
}

func TestLoadRequiresToken(t *testing.T) {
	for name, tok := range map[string]string{"missing": "", "short": token[1:]} {
		t.Run(name, func(t *testing.T) {
			_, err := Load(env(valid(map[string]string{"DEVICEMGR_TOKEN": tok})))
			assert.ErrorContains(t, err, "DEVICEMGR_TOKEN")
		})
	}
}

func TestLoadReportsAllErrors(t *testing.T) {
	_, err := Load(env(map[string]string{}))

	require.Error(t, err)
	assert.Contains(t, err.Error(), "DATABASE_URL")
	assert.Contains(t, err.Error(), "DEVICEMGR_TOKEN")
	assert.Contains(t, err.Error(), "DEVICEMGR_MQTT_URL")
	assert.Contains(t, err.Error(), "DEVICEMGR_MQTT_PASSWORD")
}

func TestLoadRequiresMQTTURL(t *testing.T) {
	for name, u := range map[string]string{"missing": "", "no host": "mqtt://", "http scheme": "http://mosquitto:1883", "garbage": "::"} {
		t.Run(name, func(t *testing.T) {
			_, err := Load(env(valid(map[string]string{"DEVICEMGR_MQTT_URL": u})))
			assert.ErrorContains(t, err, "DEVICEMGR_MQTT_URL")
		})
	}
}

func TestLoadRequiresMQTTPassword(t *testing.T) {
	for name, pw := range map[string]string{"missing": "", "short": mqttPassword[1:]} {
		t.Run(name, func(t *testing.T) {
			_, err := Load(env(valid(map[string]string{"DEVICEMGR_MQTT_PASSWORD": pw})))
			assert.ErrorContains(t, err, "DEVICEMGR_MQTT_PASSWORD")
		})
	}
}

func TestLoadConnectivityDurations(t *testing.T) {
	cfg, err := Load(env(valid(map[string]string{"DEVICEMGR_OFFLINE_AFTER": "2m", "DEVICEMGR_SWEEP_INTERVAL": "2m"})))
	require.NoError(t, err)
	assert.Equal(t, 2*time.Minute, cfg.OfflineAfter)
	assert.Equal(t, 2*time.Minute, cfg.SweepInterval, "the sweep may run as rarely as the threshold")
}

func TestLoadRejectsBadDurations(t *testing.T) {
	for _, key := range []string{"DEVICEMGR_OFFLINE_AFTER", "DEVICEMGR_SWEEP_INTERVAL"} {
		for name, v := range map[string]string{"garbage": "soon", "no unit": "90", "zero": "0s", "negative": "-5s"} {
			t.Run(key+"/"+name, func(t *testing.T) {
				_, err := Load(env(valid(map[string]string{key: v})))
				assert.ErrorContains(t, err, key)
			})
		}
	}
}

func TestLoadRejectsSweepLongerThanOfflineAfter(t *testing.T) {
	_, err := Load(env(valid(map[string]string{"DEVICEMGR_OFFLINE_AFTER": "30s", "DEVICEMGR_SWEEP_INTERVAL": "31s"})))
	assert.ErrorContains(t, err, "DEVICEMGR_SWEEP_INTERVAL must not exceed DEVICEMGR_OFFLINE_AFTER")
}
