// Package mqtt is devicemgr's MQTT client. It connects to the broker as the
// superuser, answers device registration handshakes, and records device
// traffic for presence.
package mqtt

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"log/slog"
	"net/url"
	"strings"
	"time"

	"github.com/eclipse/paho.golang/autopaho"
	"github.com/eclipse/paho.golang/paho"

	"dalnamics/services/devicemgr/internal/devices"
)

// deviceSubscription covers registration requests and all device traffic. It is
// shared, so each message is handled by exactly one devicemgr instance, and it
// is a single subscription, so each message arrives once; route picks the
// handler by topic.
const deviceSubscription = "$share/devicemgr/devices/#"

// Config configures the broker connection.
type Config struct {
	URL      *url.URL
	Password []byte
}

// Connect starts a connection to the broker that reconnects until ctx is
// cancelled. It handles registration requests with h and device traffic with
// p. It returns without waiting for the broker, so devicemgr starts even while
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
				_, err := cm.Subscribe(ctx, &paho.Subscribe{
					Subscriptions: []paho.SubscribeOptions{{Topic: deviceSubscription, QoS: 1}},
				})
				if err != nil && ctx.Err() == nil {
					logger.Error("mqtt subscribe", "topic", deviceSubscription, "err", err)
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
					go r.route(ctx, pr.Client, pr.Packet.Topic, pr.Packet.Payload)
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

// router sends each received message to one handler by its topic.
type router struct {
	handshake *Handshake
	presence  *Presence
}

// route handles registration traffic (devices/register/...) with the handshake
// and everything else with presence. devicemgr's own replies come back too, and
// the handshake ignores them.
func (r router) route(ctx context.Context, pub Publisher, topic string, payload []byte) {
	if strings.HasPrefix(topic, devices.RegisterTopic("")) {
		r.handshake.Handle(ctx, pub, topic, payload)
		return
	}
	r.presence.Handle(ctx, topic)
}

func randomHex(n int) string {
	b := make([]byte, n)
	_, _ = rand.Read(b) // never returns an error
	return hex.EncodeToString(b)
}
