package devices

import (
	"context"
	"crypto/subtle"
	"errors"
	"fmt"
	"strings"

	"github.com/google/uuid"

	"dalnamics/services/devicemgr/internal/store"
)

// Broker usernames other than device IDs.
const (
	// SuperuserName is devicemgr's own MQTT client.
	SuperuserName = "devicemgr"
	// RegisterUsername is used by unregistered devices for the registration
	// handshake, with any password. mosquitto-go-auth rejects an empty password
	// before asking devicemgr, so devices send "register".
	RegisterUsername = "register"
)

// Access is the access an MQTT client asks for on a topic, as mosquitto-go-auth
// reports it.
type Access int

const (
	AccessRead      Access = 1
	AccessWrite     Access = 2
	AccessSubscribe Access = 4
)

// RegisterTopic is where a device with MQTT client ID clientID publishes its
// registration request.
func RegisterTopic(clientID string) string {
	return "devices/register/" + clientID
}

// ReplyTopic is where devicemgr replies to a request published on topic.
func ReplyTopic(topic string) string {
	return topic + "/reply"
}

// DeviceIDFromTopic returns the device ID in a device's own topic,
// devices/{device id}/..., and reports whether topic is one.
func DeviceIDFromTopic(topic string) (uuid.UUID, bool) {
	rest, ok := strings.CutPrefix(topic, "devices/")
	if !ok {
		return uuid.Nil, false
	}
	idPart, sub, ok := strings.Cut(rest, "/")
	if !ok || sub == "" {
		return uuid.Nil, false
	}
	id, err := uuid.Parse(idPart)
	if err != nil {
		return uuid.Nil, false
	}
	return id, true
}

// CheckUser reports whether the broker should accept a connection with these
// credentials.
func (s *Service) CheckUser(ctx context.Context, username, password string) (bool, error) {
	switch username {
	case SuperuserName:
		return subtle.ConstantTimeCompare([]byte(password), s.mqttPassword) == 1, nil
	case RegisterUsername:
		return true, nil
	}

	id, err := uuid.Parse(username)
	if err != nil {
		return false, nil
	}
	want, err := s.q.GetDeviceSecretHash(ctx, id)
	if errors.Is(err, store.ErrNoRows) {
		return false, nil
	}
	if err != nil {
		return false, fmt.Errorf("get device secret: %w", err)
	}
	return subtle.ConstantTimeCompare(hashSecret(password), want) == 1, nil
}

// IsSuperuser reports whether username bypasses topic ACLs.
func (s *Service) IsSuperuser(username string) bool {
	return username == SuperuserName
}

// CheckACL reports whether a connected client may access topic (a topic name,
// or a topic filter for subscriptions). Anything not allowed is denied:
//   - register may publish only to RegisterTopic(clientID), and read or
//     subscribe only to its reply topic.
//   - a device may use only devices/{its id} and below.
func (s *Service) CheckACL(username, clientID, topic string, acc Access) bool {
	switch username {
	case SuperuserName:
		return true
	case RegisterUsername:
		if !validClientID(clientID) {
			return false
		}
		request := RegisterTopic(clientID)
		switch acc {
		case AccessWrite:
			return topic == request
		case AccessRead, AccessSubscribe:
			return topic == ReplyTopic(request)
		}
		return false
	}

	if _, err := uuid.Parse(username); err != nil {
		return false
	}
	prefix := "devices/" + username
	return topic == prefix || strings.HasPrefix(topic, prefix+"/")
}

// validClientID reports whether clientID can name a single topic level.
func validClientID(clientID string) bool {
	return clientID != "" && !strings.ContainsAny(clientID, "/+#")
}
