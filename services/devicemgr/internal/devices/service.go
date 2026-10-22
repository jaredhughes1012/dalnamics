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
	// OfflineAfter is how long a device stays online after a heartbeat.
	// Defaults to DefaultOfflineAfter.
	OfflineAfter time.Duration
	// Now defaults to time.Now.
	Now func() time.Time
}

// DefaultOfflineAfter is how long a device stays online after a heartbeat
// unless Config.OfflineAfter says otherwise.
const DefaultOfflineAfter = 90 * time.Second

// Service implements device registration, broker authorization, and presence.
type Service struct {
	q            store.Querier
	mqttPassword []byte
	offlineAfter time.Duration
	now          func() time.Time

	mu sync.Mutex
	// seen is when this instance last wrote, or started writing, each device's
	// presence.
	seen map[uuid.UUID]time.Time
	// pruned is when seen was last pruned.
	pruned time.Time
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
	if s.offlineAfter <= 0 {
		s.offlineAfter = DefaultOfflineAfter
	}
	return s
}
