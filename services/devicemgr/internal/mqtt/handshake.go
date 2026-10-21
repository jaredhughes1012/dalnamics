package mqtt

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"strings"

	"github.com/eclipse/paho.golang/paho"
	"github.com/google/uuid"

	"dalnamics/services/devicemgr/internal/devices"
)

// Error codes in a handshake reply, shared with the HTTP error codes (see
// docs/arch.md#error-codes).
const (
	codeInvalidCode    = "invalid_code"
	codeInvalidRequest = "invalid_request"
	codeInternal       = "internal"
)

// Redeemer registers a device from a handshake request.
type Redeemer interface {
	Redeem(ctx context.Context, req devices.Request) (devices.Credentials, error)
}

// Publisher sends an MQTT message. *paho.Client implements it.
type Publisher interface {
	Publish(ctx context.Context, p *paho.Publish) (*paho.PublishResponse, error)
}

// Handshake answers device registration requests.
type Handshake struct {
	devices Redeemer
	logger  *slog.Logger
}

// NewHandshake returns a Handshake that redeems codes with r.
func NewHandshake(r Redeemer, logger *slog.Logger) *Handshake {
	return &Handshake{devices: r, logger: logger}
}

type reply struct {
	DeviceID *uuid.UUID `json:"device_id,omitempty"`
	Secret   string     `json:"secret,omitempty"`
	Error    string     `json:"error,omitempty"`
}

// Handle answers one registration request received on topic, publishing the
// reply to devices.ReplyTopic(topic). Requests on any other topic are ignored.
// Neither the code nor the secret is ever logged.
func (h *Handshake) Handle(ctx context.Context, pub Publisher, topic string, payload []byte) {
	clientID, ok := strings.CutPrefix(topic, devices.RegisterTopic(""))
	if !ok || clientID == "" || strings.Contains(clientID, "/") {
		return
	}

	res := h.redeem(ctx, payload)
	body, err := json.Marshal(res)
	if err != nil {
		h.logger.ErrorContext(ctx, "encode registration reply", "err", err)
		return
	}
	if _, err := pub.Publish(ctx, &paho.Publish{Topic: devices.ReplyTopic(topic), QoS: 1, Payload: body}); err != nil {
		h.logger.ErrorContext(ctx, "publish registration reply", "client_id", clientID, "err", err)
		return
	}
	if res.Error != "" {
		h.logger.InfoContext(ctx, "device registration rejected", "client_id", clientID, "error", res.Error)
	} else {
		h.logger.InfoContext(ctx, "device registered", "client_id", clientID, "device_id", res.DeviceID)
	}
}

func (h *Handshake) redeem(ctx context.Context, payload []byte) reply {
	var req devices.Request
	if err := json.Unmarshal(payload, &req); err != nil {
		return reply{Error: codeInvalidRequest}
	}

	creds, err := h.devices.Redeem(ctx, req)
	var verr *devices.ValidationError
	switch {
	case err == nil:
		return reply{DeviceID: &creds.DeviceID, Secret: creds.Secret}
	case errors.As(err, &verr):
		return reply{Error: codeInvalidRequest}
	case errors.Is(err, devices.ErrInvalidCode):
		return reply{Error: codeInvalidCode}
	default:
		h.logger.ErrorContext(ctx, "redeem registration code", "err", err)
		return reply{Error: codeInternal}
	}
}
