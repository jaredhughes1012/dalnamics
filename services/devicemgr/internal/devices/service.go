// Package devices registers devices to users and decides what each broker
// identity may do on the MQTT broker.
package devices

import "dalnamics/services/devicemgr/internal/store"

// Config configures a Service.
type Config struct {
	// MQTTPassword is the broker password of devicemgr's own MQTT client,
	// the broker superuser.
	MQTTPassword []byte
}

// Service implements device registration and broker authorization.
type Service struct {
	q            store.Querier
	mqttPassword []byte
}

// NewService returns a Service backed by q.
func NewService(q store.Querier, cfg Config) *Service {
	return &Service{q: q, mqttPassword: cfg.MQTTPassword}
}
