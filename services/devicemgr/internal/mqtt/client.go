// Package mqtt is devicemgr's MQTT client. It connects to the broker as the
// superuser, answers device registration handshakes, and records device
// heartbeats for presence.
package mqtt

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"log/slog"
	"net/url"
	"time"

	"github.com/eclipse/paho.golang/autopaho"
	"github.com/eclipse/paho.golang/paho"

	"dalnamics/services/devicemgr/internal/devices"
)

// devicemgr's subscriptions are shared, so each message is handled by exactly
// one devicemgr instance. They cover only what devicemgr handles: registration
// requests (not devicemgr's own replies) and heartbeats, not other device
// traffic.
//
// A register client could pick the client ID "heartbeat", whose request topic
// matches both filters and so arrives twice. Each subscription therefore
// carries its own identifier, and route picks the handler by it rather than by
// topic.
var subscriptions = []struct {
	filter string
	id     int
}{
	{"$share/devicemgr/" + devices.RegisterTopic("+"), registerSubID},
	{"$share/devicemgr/devices/+/heartbeat", heartbeatSubID},
}

const (
	registerSubID = 1 + iota
	heartbeatSubID
)

// Config configures the broker connection.
type Config struct {
	URL      *url.URL
	Password []byte
}

// Connect starts a connection to the broker that reconnects until ctx is
// cancelled. It handles registration requests with h and heartbeats with p. It returns without waiting for the broker, so devicemgr starts even while
// the broker is down.
func Connect(ctx context.Context, cfg Config, h *Handshake, p *Presence, logger *slog.Logger) (*autopaho.ConnectionManager, error) {
	r := router{handshake: h, presence: p}
	cm, err := autopaho.NewConnection(ctx, autopaho.ClientConfig{
		ServerUrls:                    []*url.URL{cfg.URL},
		KeepAlive:                     30,
		ConnectRetryDelay:             2 * time.Second,
		CleanStartOnInitialConnection: true,
		ConnectUsername:               devices.SuperuserName,
		ConnectPassword:               cfg.Password,
		OnConnectionUp: func(cm *autopaho.ConnectionManager, _ *paho.Connack) {
			logger.Info("mqtt connected", "broker", cfg.URL.Host)
			go func() {
				for _, sub := range subscriptions {
					_, err := cm.Subscribe(ctx, &paho.Subscribe{
						Properties:    &paho.SubscribeProperties{SubscriptionIdentifier: &sub.id},
						Subscriptions: []paho.SubscribeOptions{{Topic: sub.filter, QoS: 1}},
					})
					if err != nil && ctx.Err() == nil {
						logger.Error("mqtt subscribe", "topic", sub.filter, "err", err)
					}
				}
			}()
		},
		OnConnectError: func(err error) {
			logger.Warn("mqtt connect failed; retrying", "broker", cfg.URL.Host, "err", err)
		},
		ClientConfig: paho.ClientConfig{
			ClientID: "devicemgr-" + randomHex(8),
			OnPublishReceived: []func(paho.PublishReceived) (bool, error){
				func(pr paho.PublishReceived) (bool, error) {
					// Handle off the client's goroutine, which must not block.
					var subID int
					if p := pr.Packet.Properties; p != nil && p.SubscriptionIdentifier != nil {
						subID = *p.SubscriptionIdentifier
					}
					go r.route(ctx, pr.Client, subID, pr.Packet.Topic, pr.Packet.Payload)
					return true, nil
				},
			},
		},
	})
	if err != nil {
		return nil, fmt.Errorf("start mqtt connection: %w", err)
	}
	return cm, nil
}

// router sends each received message to one handler by the subscription it
// arrived on.
type router struct {
	handshake *Handshake
	presence  *Presence
}

// route handles messages from the register subscription with the handshake and
// from the heartbeat subscription with presence, and drops anything else.
func (r router) route(ctx context.Context, pub Publisher, subID int, topic string, payload []byte) {
	switch subID {
	case registerSubID:
		r.handshake.Handle(ctx, pub, topic, payload)
	case heartbeatSubID:
		r.presence.Handle(ctx, topic)
	}
}

func randomHex(n int) string {
	b := make([]byte, n)
	_, _ = rand.Read(b) // never returns an error
	return hex.EncodeToString(b)
}
