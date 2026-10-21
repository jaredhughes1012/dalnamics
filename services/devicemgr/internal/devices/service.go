// Package devices registers devices to users, decides what each broker
// identity may do on the MQTT broker, and tracks whether devices are online.
package devices

import (
	"sync"
	"time"

	"github.com/google/uuid"

	"dalnamics/services/devicemgr/internal/store"
)

// Config configures a Service.
type Config struct {
	// MQTTPassword is the broker password of devicemgr's own MQTT client,
	// the broker superuser.
	MQTTPassword []byte
	// OfflineAfter is how long a device may stay silent before Sweep marks it
	// offline.
	OfflineAfter time.Duration
	// Now defaults to time.Now.
	Now func() time.Time
}

// Service implements device registration, broker authorization, and presence.
type Service struct {
	q            store.Querier
	mqttPassword []byte
	offlineAfter time.Duration
	now          func() time.Time

	mu sync.Mutex
	// seen is when this instance last wrote each device's presence.
	seen map[uuid.UUID]time.Time
}

// NewService returns a Service backed by q.
func NewService(q store.Querier, cfg Config) *Service {
	s := &Service{
		q:            q,
		mqttPassword: cfg.MQTTPassword,
		offlineAfter: cfg.OfflineAfter,
		now:          cfg.Now,
		seen:         make(map[uuid.UUID]time.Time),
	}
	if s.now == nil {
		s.now = time.Now
	}
	return s
}
