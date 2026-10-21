package server

import (
	"context"

	"dalnamics/services/api/internal/apigen"
	"dalnamics/services/api/internal/devices"
)

func (s *Server) CreateDeviceRegistrationCode(ctx context.Context, _ apigen.CreateDeviceRegistrationCodeRequestObject) (apigen.CreateDeviceRegistrationCodeResponseObject, error) {
	p, err := principal(ctx)
	if err != nil {
		return nil, err
	}
	rc, err := s.devices.IssueRegistrationCode(ctx, p.UserID)
	if err != nil {
		return nil, err
	}
	return apigen.CreateDeviceRegistrationCode201JSONResponse{Code: rc.Code, ExpiresAt: rc.ExpiresAt}, nil
}

func (s *Server) ListDevices(ctx context.Context, _ apigen.ListDevicesRequestObject) (apigen.ListDevicesResponseObject, error) {
	p, err := principal(ctx)
	if err != nil {
		return nil, err
	}
	list, err := s.devices.List(ctx, p.UserID)
	if err != nil {
		return nil, err
	}
	res := make(apigen.ListDevices200JSONResponse, len(list))
	for i, d := range list {
		res[i] = toDevice(d)
	}
	return res, nil
}

func toDevice(d devices.Device) apigen.Device {
	return apigen.Device{Id: d.ID, Type: d.Type, Name: d.Name, CreatedAt: d.CreatedAt}
}
