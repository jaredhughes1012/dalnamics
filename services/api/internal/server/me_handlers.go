package server

import (
	"context"

	"dalnamics/services/api/internal/apigen"
)

func (s *Server) GetMe(ctx context.Context, _ apigen.GetMeRequestObject) (apigen.GetMeResponseObject, error) {
	p, err := principal(ctx)
	if err != nil {
		return nil, err
	}
	user, err := s.auth.Me(ctx, p)
	if err != nil {
		return nil, err
	}
	return apigen.GetMe200JSONResponse(toUser(user)), nil
}
