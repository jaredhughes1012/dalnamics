package server

import (
	"context"
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"go.uber.org/mock/gomock"

	"dalnamics/internal/health"
	"dalnamics/services/api/internal/apigen"
	"dalnamics/services/api/internal/auth"
	"dalnamics/services/api/internal/devices"
	storeauth "dalnamics/services/api/internal/store/auth"
	"dalnamics/services/api/internal/store/mockstore"
)

var testSecret = []byte("test-secret-that-is-at-least-32-bytes")

type testServer struct {
	*httptest.Server
	q    *mockstore.MockQuerier
	auth *auth.Service
}

func newTestServer(t *testing.T, devEmails ...string) *testServer {
	t.Helper()
	q := mockstore.NewMockQuerier(gomock.NewController(t))
	svc := auth.NewService(q, auth.Config{JWTSecret: testSecret, DevEmails: devEmails})
	h, err := NewHandler(svc, devices.NewService(q, devices.Config{}), slog.New(slog.NewTextHandler(io.Discard, nil)))
	require.NoError(t, err)

	srv := httptest.NewServer(h)
	t.Cleanup(srv.Close)
	return &testServer{Server: srv, q: q, auth: svc}
}

func (ts *testServer) do(t *testing.T, method, path, body, token string) *http.Response {
	t.Helper()
	req, err := http.NewRequest(method, ts.URL+path, strings.NewReader(body))
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	res, err := http.DefaultClient.Do(req)
	require.NoError(t, err)
	t.Cleanup(func() { res.Body.Close() })
	return res
}

func decode[T any](t *testing.T, res *http.Response) T {
	t.Helper()
	var v T
	require.NoError(t, json.NewDecoder(res.Body).Decode(&v))
	return v
}

// login signs a user in through a mocked session and returns its access token.
func (ts *testServer) login(t *testing.T, user storeauth.User) string {
	t.Helper()
	sessionID := uuid.New()
	ts.q.EXPECT().CreateSession(gomock.Any(), gomock.Any()).Return(storeauth.Session{ID: sessionID, UserID: user.ID}, nil)
	ts.q.EXPECT().GetUserByEmail(gomock.Any(), user.Email).Return(user, nil)
	sess, err := ts.auth.DevLogin(context.Background(), user.Email, auth.ClientStudio)
	require.NoError(t, err)

	ts.q.EXPECT().GetActiveSession(gomock.Any(), sessionID).
		Return(storeauth.Session{ID: sessionID, UserID: user.ID}, nil).AnyTimes()
	return sess.Tokens.AccessToken
}

func TestHealth(t *testing.T) {
	ts := newTestServer(t)

	res := ts.do(t, http.MethodGet, health.Path, "", "")

	assert.Equal(t, http.StatusOK, res.StatusCode)
	assert.Equal(t, health.Response{Status: health.StatusOK, Service: ServiceName}, decode[health.Response](t, res))
}

func TestBearerOperationsComeFromSpec(t *testing.T) {
	ops, err := bearerOperations()

	require.NoError(t, err)
	assert.Equal(t, map[string]bool{
		"logout": true, "authorizecli": true, "getme": true,
		"listdevices": true, "getdevice": true, "createdeviceregistrationcode": true,
	}, ops)
}

func TestSignup(t *testing.T) {
	ts := newTestServer(t)
	user := storeauth.User{ID: uuid.New(), Email: "jane@example.com", Name: "Jane"}
	ts.q.EXPECT().CreateUser(gomock.Any(), gomock.Any()).Return(user, nil)
	ts.q.EXPECT().CreateSession(gomock.Any(), gomock.Any()).Return(storeauth.Session{ID: uuid.New()}, nil)

	res := ts.do(t, http.MethodPost, "/auth/signup", `{"email":"jane@example.com","name":"Jane","password":"hunter22"}`, "")

	require.Equal(t, http.StatusCreated, res.StatusCode)
	body := decode[apigen.Session](t, res)
	assert.Equal(t, "Jane", body.User.Name)
	assert.Equal(t, user.ID, body.User.Id)
	assert.Equal(t, apigen.Bearer, body.Tokens.TokenType)
	assert.Equal(t, 900, body.Tokens.ExpiresIn)
	assert.NotEmpty(t, body.Tokens.AccessToken)
	assert.NotEmpty(t, body.Tokens.RefreshToken)
}

func TestErrorResponses(t *testing.T) {
	cases := []struct {
		name   string
		setup  func(q *mockstore.MockQuerier)
		path   string
		body   string
		status int
		code   string
	}{
		{
			name:   "malformed json",
			path:   "/auth/login",
			body:   `{`,
			status: http.StatusBadRequest,
			code:   codeInvalidRequest,
		},
		{
			name:   "validation",
			path:   "/auth/signup",
			body:   `{"email":"nope","name":"Jane","password":"hunter22"}`,
			status: http.StatusBadRequest,
			code:   codeInvalidRequest,
		},
		{
			name: "email taken",
			setup: func(q *mockstore.MockQuerier) {
				q.EXPECT().CreateUser(gomock.Any(), gomock.Any()).Return(storeauth.User{}, &pgconn.PgError{Code: "23505"})
			},
			path:   "/auth/signup",
			body:   `{"email":"jane@example.com","name":"Jane","password":"hunter22"}`,
			status: http.StatusConflict,
			code:   codeEmailTaken,
		},
		{
			name: "store failure is hidden",
			setup: func(q *mockstore.MockQuerier) {
				q.EXPECT().GetUserByEmail(gomock.Any(), gomock.Any()).Return(storeauth.User{}, assert.AnError)
			},
			path:   "/auth/login",
			body:   `{"email":"jane@example.com","password":"hunter22"}`,
			status: http.StatusInternalServerError,
			code:   codeInternal,
		},
		{
			name:   "dev login disabled",
			path:   "/auth/dev-login",
			body:   `{"email":"dev@dalnamics.local"}`,
			status: http.StatusNotFound,
			code:   codeNotFound,
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			ts := newTestServer(t)
			if tc.setup != nil {
				tc.setup(ts.q)
			}

			res := ts.do(t, http.MethodPost, tc.path, tc.body, "")

			assert.Equal(t, tc.status, res.StatusCode)
			assert.Equal(t, tc.code, decode[apigen.Error](t, res).Code)
		})
	}
}

func TestProtectedRoutesRequireBearer(t *testing.T) {
	ts := newTestServer(t)
	for _, tc := range []struct{ method, path, token string }{
		{http.MethodGet, "/me", ""},
		{http.MethodGet, "/me", "garbage"},
		{http.MethodPost, "/auth/logout", ""},
		{http.MethodPost, "/auth/cli/authorize", ""},
		{http.MethodGet, "/devices", ""},
		{http.MethodPost, "/devices/registration-codes", ""},
	} {
		res := ts.do(t, tc.method, tc.path, `{}`, tc.token)

		assert.Equal(t, http.StatusUnauthorized, res.StatusCode, tc.path)
	}
}

func TestGetMe(t *testing.T) {
	ts := newTestServer(t, "dev@dalnamics.local")
	user := storeauth.User{ID: uuid.New(), Email: "dev@dalnamics.local", Name: "dev"}
	token := ts.login(t, user)
	ts.q.EXPECT().GetUserByID(gomock.Any(), user.ID).Return(user, nil)

	res := ts.do(t, http.MethodGet, "/me", "", token)

	require.Equal(t, http.StatusOK, res.StatusCode)
	body := decode[apigen.User](t, res)
	assert.Equal(t, user.ID, body.Id)
	assert.Equal(t, "dev@dalnamics.local", string(body.Email))
}

func TestLogout(t *testing.T) {
	ts := newTestServer(t, "dev@dalnamics.local")
	token := ts.login(t, storeauth.User{ID: uuid.New(), Email: "dev@dalnamics.local"})
	ts.q.EXPECT().RevokeSession(gomock.Any(), gomock.Any()).Return(nil)

	res := ts.do(t, http.MethodPost, "/auth/logout", "", token)

	assert.Equal(t, http.StatusNoContent, res.StatusCode)
}

func TestListDevUsers(t *testing.T) {
	res := newTestServer(t).do(t, http.MethodGet, "/auth/dev-users", "", "")
	assert.Equal(t, http.StatusNotFound, res.StatusCode)

	res = newTestServer(t, "dev@dalnamics.local").do(t, http.MethodGet, "/auth/dev-users", "", "")
	require.Equal(t, http.StatusOK, res.StatusCode)
	assert.Equal(t, []string{"dev@dalnamics.local"}, decode[apigen.DevUsers](t, res).Emails)
}
