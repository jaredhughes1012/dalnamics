package server

import (
	"context"

	openapi_types "github.com/oapi-codegen/runtime/types"

	"dalnamics/services/api/internal/apigen"
	"dalnamics/services/api/internal/auth"
)

func (s *Server) Signup(ctx context.Context, req apigen.SignupRequestObject) (apigen.SignupResponseObject, error) {
	sess, err := s.auth.Signup(ctx, req.Body.Email, req.Body.Name, req.Body.Password, auth.ClientStudio)
	if err != nil {
		return nil, err
	}
	return apigen.Signup201JSONResponse{SessionJSONResponse: toSession(sess)}, nil
}

func (s *Server) Login(ctx context.Context, req apigen.LoginRequestObject) (apigen.LoginResponseObject, error) {
	sess, err := s.auth.Login(ctx, req.Body.Email, req.Body.Password, auth.ClientStudio)
	if err != nil {
		return nil, err
	}
	return apigen.Login200JSONResponse{SessionJSONResponse: toSession(sess)}, nil
}

func (s *Server) Refresh(ctx context.Context, req apigen.RefreshRequestObject) (apigen.RefreshResponseObject, error) {
	tokens, err := s.auth.Refresh(ctx, req.Body.RefreshToken)
	if err != nil {
		return nil, err
	}
	return apigen.Refresh200JSONResponse(toTokens(tokens)), nil
}

func (s *Server) Logout(ctx context.Context, _ apigen.LogoutRequestObject) (apigen.LogoutResponseObject, error) {
	p, err := principal(ctx)
	if err != nil {
		return nil, err
	}
	if err := s.auth.Logout(ctx, p); err != nil {
		return nil, err
	}
	return apigen.Logout204Response{}, nil
}

func (s *Server) ListDevUsers(_ context.Context, _ apigen.ListDevUsersRequestObject) (apigen.ListDevUsersResponseObject, error) {
	if !s.auth.DevLoginEnabled() {
		return nil, auth.ErrDevLoginDisabled
	}
	return apigen.ListDevUsers200JSONResponse{Emails: s.auth.DevEmails()}, nil
}

func (s *Server) DevLogin(ctx context.Context, req apigen.DevLoginRequestObject) (apigen.DevLoginResponseObject, error) {
	client := auth.ClientStudio
	if req.Body.Client != nil {
		client = auth.Client(*req.Body.Client)
	}
	sess, err := s.auth.DevLogin(ctx, req.Body.Email, client)
	if err != nil {
		return nil, err
	}
	return apigen.DevLogin200JSONResponse{SessionJSONResponse: toSession(sess)}, nil
}

func (s *Server) AuthorizeCli(ctx context.Context, req apigen.AuthorizeCliRequestObject) (apigen.AuthorizeCliResponseObject, error) {
	p, err := principal(ctx)
	if err != nil {
		return nil, err
	}
	code, err := s.auth.AuthorizeCLI(ctx, p, req.Body.CodeChallenge, req.Body.RedirectUri)
	if err != nil {
		return nil, err
	}
	return apigen.AuthorizeCli200JSONResponse{Code: code}, nil
}

func (s *Server) ExchangeCliCode(ctx context.Context, req apigen.ExchangeCliCodeRequestObject) (apigen.ExchangeCliCodeResponseObject, error) {
	sess, err := s.auth.ExchangeCLICode(ctx, req.Body.Code, req.Body.CodeVerifier, req.Body.RedirectUri)
	if err != nil {
		return nil, err
	}
	return apigen.ExchangeCliCode200JSONResponse{SessionJSONResponse: toSession(sess)}, nil
}

func toSession(s auth.Session) apigen.SessionJSONResponse {
	return apigen.SessionJSONResponse{User: toUser(s.User), Tokens: toTokens(s.Tokens)}
}

func toTokens(t auth.Tokens) apigen.Tokens {
	return apigen.Tokens{
		AccessToken:  t.AccessToken,
		RefreshToken: t.RefreshToken,
		TokenType:    apigen.Bearer,
		ExpiresIn:    int(t.ExpiresIn.Seconds()),
	}
}

func toUser(u auth.User) apigen.User {
	return apigen.User{Id: u.ID, Email: openapi_types.Email(u.Email), Name: u.Name, CreatedAt: u.CreatedAt}
}
