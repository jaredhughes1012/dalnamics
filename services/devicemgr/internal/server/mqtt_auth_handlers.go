package server

import (
	"context"

	"dalnamics/services/devicemgr/internal/apigen"
	"dalnamics/services/devicemgr/internal/devices"
)

// The /mqtt handlers answer mosquitto-go-auth's HTTP backend, which reads only
// the status: 200 allows and anything else denies.

func (s *Server) CheckMqttUser(ctx context.Context, req apigen.CheckMqttUserRequestObject) (apigen.CheckMqttUserResponseObject, error) {
	ok, err := s.devices.CheckUser(ctx, req.Body.Username, req.Body.Password)
	if err != nil {
		return nil, err
	}
	if !ok {
		return apigen.CheckMqttUser403Response{}, nil
	}
	return apigen.CheckMqttUser200Response{}, nil
}

func (s *Server) CheckMqttSuperuser(_ context.Context, req apigen.CheckMqttSuperuserRequestObject) (apigen.CheckMqttSuperuserResponseObject, error) {
	if !s.devices.IsSuperuser(req.Body.Username) {
		return apigen.CheckMqttSuperuser403Response{}, nil
	}
	return apigen.CheckMqttSuperuser200Response{}, nil
}

func (s *Server) CheckMqttAcl(_ context.Context, req apigen.CheckMqttAclRequestObject) (apigen.CheckMqttAclResponseObject, error) {
	b := req.Body
	if !s.devices.CheckACL(b.Username, b.Clientid, b.Topic, devices.Access(b.Acc)) {
		return apigen.CheckMqttAcl403Response{}, nil
	}
	return apigen.CheckMqttAcl200Response{}, nil
}
