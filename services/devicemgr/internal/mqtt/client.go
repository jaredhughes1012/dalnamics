// Package mqtt is devicemgr's MQTT client. It connects to the broker as the
// superuser and answers device registration handshakes.
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

// registerSubscription is shared, so each request is handled by exactly one
// devicemgr instance.
const registerSubscription = "$share/devicemgr/devices/register/+"

// Config configures the broker connection.
type Config struct {
	URL      *url.URL
	Password []byte
}

// Connect starts a connection to the broker that reconnects until ctx is
// cancelled, and handles registration requests with h. It returns without
// waiting for the broker, so devicemgr starts even while the broker is down.
func Connect(ctx context.Context, cfg Config, h *Handshake, logger *slog.Logger) (*autopaho.ConnectionManager, error) {
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
					Subscriptions: []paho.SubscribeOptions{{Topic: registerSubscription, QoS: 1}},
				})
				if err != nil && ctx.Err() == nil {
					logger.Error("mqtt subscribe", "topic", registerSubscription, "err", err)
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
					go h.Handle(ctx, pr.Client, pr.Packet.Topic, pr.Packet.Payload)
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

func randomHex(n int) string {
	b := make([]byte, n)
	_, _ = rand.Read(b) // never returns an error
	return hex.EncodeToString(b)
}
