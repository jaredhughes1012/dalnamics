package commands

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"dalnamics/services/cli/internal/client/apigen"
)

// fakeDevicesAPI serves dev login and the device endpoints, with devices as the
// logged-in user's list.
func fakeDevicesAPI(t *testing.T, code apigen.DeviceRegistrationCode, devices []apigen.Device) *httptest.Server {
	t.Helper()
	srv, _ := fakeDevicesAPIWithCount(t, code, devices)
	return srv
}

// fakeDevicesAPIWithCount is fakeDevicesAPI, and also counts the requests made
// to device endpoints.
func fakeDevicesAPIWithCount(t *testing.T, code apigen.DeviceRegistrationCode, devices []apigen.Device) (*httptest.Server, *atomic.Int32) {
	t.Helper()
	var deviceRequests atomic.Int32
	authorized := func(w http.ResponseWriter, r *http.Request) bool {
		if r.Header.Get("Authorization") != "Bearer access" {
			w.WriteHeader(http.StatusUnauthorized)
			_ = json.NewEncoder(w).Encode(apigen.Error{Code: "unauthenticated", Message: "authentication required"})
			return false
		}
		return true
	}

	mux := http.NewServeMux()
	mux.HandleFunc("POST /auth/dev-login", func(w http.ResponseWriter, _ *http.Request) {
		_ = json.NewEncoder(w).Encode(apigen.Session{
			User:   apigen.User{Name: "dev", Email: "dev@dalnamics.local"},
			Tokens: apigen.Tokens{AccessToken: "access", RefreshToken: "refresh", TokenType: apigen.Bearer},
		})
	})
	mux.HandleFunc("POST /devices/registration-codes", func(w http.ResponseWriter, r *http.Request) {
		if authorized(w, r) {
			w.WriteHeader(http.StatusCreated)
			_ = json.NewEncoder(w).Encode(code)
		}
	})
	mux.HandleFunc("GET /devices", func(w http.ResponseWriter, r *http.Request) {
		if authorized(w, r) {
			_ = json.NewEncoder(w).Encode(devices)
		}
	})
	mux.HandleFunc("GET /devices/{id}", func(w http.ResponseWriter, r *http.Request) {
		if !authorized(w, r) {
			return
		}
		for _, d := range devices {
			if d.Id.String() == r.PathValue("id") {
				_ = json.NewEncoder(w).Encode(d)
				return
			}
		}
		w.WriteHeader(http.StatusNotFound)
		_ = json.NewEncoder(w).Encode(apigen.Error{Code: "not_found", Message: "device not found"})
	})

	// Renames like the api: the name is trimmed, and a blank one is rejected.
	mux.HandleFunc("PATCH /devices/{id}", func(w http.ResponseWriter, r *http.Request) {
		if !authorized(w, r) {
			return
		}
		var body apigen.DeviceUpdate
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil || strings.TrimSpace(body.Name) == "" {
			w.WriteHeader(http.StatusBadRequest)
			_ = json.NewEncoder(w).Encode(apigen.Error{Code: "invalid_request", Message: "name: is required"})
			return
		}
		for _, d := range devices {
			if d.Id.String() == r.PathValue("id") {
				d.Name = strings.TrimSpace(body.Name)
				_ = json.NewEncoder(w).Encode(d)
				return
			}
		}
		w.WriteHeader(http.StatusNotFound)
		_ = json.NewEncoder(w).Encode(apigen.Error{Code: "not_found", Message: "device not found"})
	})

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if strings.HasPrefix(r.URL.Path, "/devices") {
			deviceRequests.Add(1)
		}
		w.Header().Set("Content-Type", "application/json")
		mux.ServeHTTP(w, r)
	}))
	t.Cleanup(srv.Close)
	return srv, &deviceRequests
}

func devLogin(t *testing.T, apiURL string) {
	t.Helper()
	_, err := runRoot(t, "auth", "login", "--dev", "dev@dalnamics.local", "--api-url", apiURL)
	require.NoError(t, err)
}

func TestDevicesRegister(t *testing.T) {
	useTempCredentials(t)
	expires := time.Now().Add(10 * time.Minute).Truncate(time.Second)
	api := fakeDevicesAPI(t, apigen.DeviceRegistrationCode{Code: "AB3D7K", ExpiresAt: expires}, nil)
	devLogin(t, api.URL)

	out, err := runRoot(t, "devices", "register", "--api-url", api.URL)

	require.NoError(t, err)
	assert.Equal(t, "Enter code AB3D7K on the device. It expires at "+expires.Local().Format("15:04")+" (10 min).\n", out)
}

func TestDevicesRegisterJSON(t *testing.T) {
	useTempCredentials(t)
	expires := time.Date(2026, 1, 2, 3, 14, 5, 0, time.UTC)
	api := fakeDevicesAPI(t, apigen.DeviceRegistrationCode{Code: "AB3D7K", ExpiresAt: expires}, nil)
	devLogin(t, api.URL)

	out, err := runRoot(t, "devices", "register", "--json", "--api-url", api.URL)

	require.NoError(t, err)
	assert.JSONEq(t, `{"code":"AB3D7K","expires_at":"2026-01-02T03:14:05Z"}`, out)
}

func TestDevicesList(t *testing.T) {
	useTempCredentials(t)
	created := time.Date(2026, 1, 2, 3, 4, 5, 0, time.Local)
	seen := created.Add(time.Hour)
	api := fakeDevicesAPI(t, apigen.DeviceRegistrationCode{}, []apigen.Device{
		{Id: uuid.MustParse("6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11"), Name: "bench-rover", Type: "harwood0", CreatedAt: created, Online: true, LastSeenAt: &seen},
		{Id: uuid.MustParse("7a2d2f9f-3b9f-4a1d-8e66-3b9e1d2c8f22"), Name: "garage-rover", Type: "harwood0", CreatedAt: created},
	})
	devLogin(t, api.URL)

	out, err := runRoot(t, "devices", "list", "--api-url", api.URL)

	require.NoError(t, err)
	assert.Equal(t, ""+
		"ID                                    NAME          TYPE      STATUS   REGISTERED\n"+
		"6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11  bench-rover   harwood0  online   2026-01-02 03:04:05\n"+
		"7a2d2f9f-3b9f-4a1d-8e66-3b9e1d2c8f22  garage-rover  harwood0  offline  2026-01-02 03:04:05\n", out)
}

func TestDevicesListJSON(t *testing.T) {
	useTempCredentials(t)
	id := uuid.MustParse("6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11")
	seen := time.Date(2026, 1, 2, 4, 5, 6, 0, time.UTC)
	api := fakeDevicesAPI(t, apigen.DeviceRegistrationCode{}, []apigen.Device{
		{Id: id, Name: "bench-rover", Type: "harwood0", CreatedAt: time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC), Online: true, LastSeenAt: &seen},
		{Id: id, Name: "garage-rover", Type: "harwood0", CreatedAt: time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)},
	})
	devLogin(t, api.URL)

	out, err := runRoot(t, "devices", "list", "--json", "--api-url", api.URL)

	require.NoError(t, err)
	assert.JSONEq(t, `[`+
		`{"id":"6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11","name":"bench-rover","type":"harwood0","created_at":"2026-01-02T03:04:05Z","online":true,"last_seen_at":"2026-01-02T04:05:06Z"},`+
		`{"id":"6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11","name":"garage-rover","type":"harwood0","created_at":"2026-01-02T03:04:05Z","online":false,"last_seen_at":null}]`, out)
}

func TestDevicesListEmpty(t *testing.T) {
	useTempCredentials(t)
	api := fakeDevicesAPI(t, apigen.DeviceRegistrationCode{}, []apigen.Device{})
	devLogin(t, api.URL)

	out, err := runRoot(t, "devices", "list", "--api-url", api.URL)

	require.NoError(t, err)
	assert.Equal(t, "No devices registered. Run `cli devices register` to add one.\n", out)
}

func TestDevicesNotLoggedIn(t *testing.T) {
	for _, args := range [][]string{{"devices", "register"}, {"devices", "list"}, {"devices", "get", "6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11"}} {
		t.Run(args[1], func(t *testing.T) {
			useTempCredentials(t)
			api := fakeDevicesAPI(t, apigen.DeviceRegistrationCode{}, nil)

			_, err := runRoot(t, append(args, "--api-url", api.URL)...)

			assert.ErrorContains(t, err, "not logged in; run `cli auth login`")
		})
	}
}

func TestDevicesGet(t *testing.T) {
	useTempCredentials(t)
	created := time.Date(2026, 1, 2, 3, 4, 5, 0, time.Local)
	seen := created.Add(time.Hour)
	api := fakeDevicesAPI(t, apigen.DeviceRegistrationCode{}, []apigen.Device{
		{Id: uuid.MustParse("6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11"), Name: "bench-rover", Type: "harwood0", CreatedAt: created, Online: true, LastSeenAt: &seen},
	})
	devLogin(t, api.URL)

	out, err := runRoot(t, "devices", "get", "6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11", "--api-url", api.URL)

	require.NoError(t, err)
	assert.Equal(t, ""+
		"ID          6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11\n"+
		"NAME        bench-rover\n"+
		"TYPE        harwood0\n"+
		"STATUS      online\n"+
		"LAST SEEN   2026-01-02 04:04:05\n"+
		"REGISTERED  2026-01-02 03:04:05\n", out)
}

func TestDevicesGetNeverConnected(t *testing.T) {
	useTempCredentials(t)
	api := fakeDevicesAPI(t, apigen.DeviceRegistrationCode{}, []apigen.Device{
		{Id: uuid.MustParse("7a2d2f9f-3b9f-4a1d-8e66-3b9e1d2c8f22"), Name: "garage-rover", Type: "harwood0", CreatedAt: time.Date(2026, 1, 2, 3, 4, 5, 0, time.Local)},
	})
	devLogin(t, api.URL)

	out, err := runRoot(t, "devices", "get", "7a2d2f9f-3b9f-4a1d-8e66-3b9e1d2c8f22", "--api-url", api.URL)

	require.NoError(t, err)
	assert.Contains(t, out, "STATUS      offline\n")
	assert.Contains(t, out, "LAST SEEN   never\n")
}

func TestDevicesGetJSON(t *testing.T) {
	useTempCredentials(t)
	api := fakeDevicesAPI(t, apigen.DeviceRegistrationCode{}, []apigen.Device{
		{Id: uuid.MustParse("6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11"), Name: "bench-rover", Type: "harwood0", CreatedAt: time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)},
	})
	devLogin(t, api.URL)

	out, err := runRoot(t, "devices", "get", "6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11", "--json", "--api-url", api.URL)

	require.NoError(t, err)
	assert.JSONEq(t, `{"id":"6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11","name":"bench-rover","type":"harwood0",`+
		`"created_at":"2026-01-02T03:04:05Z","online":false,"last_seen_at":null}`, out)
}

func TestDevicesGetNotFound(t *testing.T) {
	useTempCredentials(t)
	api := fakeDevicesAPI(t, apigen.DeviceRegistrationCode{}, nil)
	devLogin(t, api.URL)

	_, err := runRoot(t, "devices", "get", "6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11", "--api-url", api.URL)

	assert.EqualError(t, err, "device 6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11 not found")
}

func TestDevicesGetInvalidID(t *testing.T) {
	useTempCredentials(t)
	api, requests := fakeDevicesAPIWithCount(t, apigen.DeviceRegistrationCode{}, nil)
	devLogin(t, api.URL)

	_, err := runRoot(t, "devices", "get", "not-a-uuid", "--api-url", api.URL)

	assert.EqualError(t, err, `invalid device id "not-a-uuid": must be a UUID`)
	assert.Zero(t, requests.Load(), "a bad id is rejected before any request")
}

func TestDevicesGetOtherNotFound(t *testing.T) {
	useTempCredentials(t)
	api := fakeDevicesAPI(t, apigen.DeviceRegistrationCode{}, nil)
	devLogin(t, api.URL)

	// Not an api: every path is a plain 404, as from a wrong --api-url.
	_, err := runRoot(t, "devices", "get", "6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11", "--api-url", api.URL+"/not-the-api")

	require.Error(t, err)
	assert.NotContains(t, err.Error(), "device 6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11 not found")
	assert.Contains(t, err.Error(), "404")
}

func TestDevicesRename(t *testing.T) {
	useTempCredentials(t)
	id := uuid.MustParse("6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11")
	api := fakeDevicesAPI(t, apigen.DeviceRegistrationCode{}, []apigen.Device{{Id: id, Type: "harwood0", Name: "harwood0"}})
	devLogin(t, api.URL)

	out, err := runRoot(t, "devices", "rename", id.String(), "Bench rover", "--api-url", api.URL)

	require.NoError(t, err)
	assert.Equal(t, "Renamed device 6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11 to \"Bench rover\".\n", out)
}

func TestDevicesRenameJSON(t *testing.T) {
	useTempCredentials(t)
	id := uuid.MustParse("6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11")
	api := fakeDevicesAPI(t, apigen.DeviceRegistrationCode{}, []apigen.Device{{Id: id, Type: "harwood0", Name: "harwood0"}})
	devLogin(t, api.URL)

	out, err := runRoot(t, "devices", "rename", id.String(), "Bench rover", "--json", "--api-url", api.URL)

	require.NoError(t, err)
	var d apigen.Device
	require.NoError(t, json.Unmarshal([]byte(out), &d))
	assert.Equal(t, apigen.Device{Id: id, Type: "harwood0", Name: "Bench rover"}, d)
}

func TestDevicesRenameNotFound(t *testing.T) {
	useTempCredentials(t)
	api := fakeDevicesAPI(t, apigen.DeviceRegistrationCode{}, nil)
	devLogin(t, api.URL)

	_, err := runRoot(t, "devices", "rename", "6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11", "Bench rover", "--api-url", api.URL)

	assert.EqualError(t, err, "device 6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11 not found")
}

func TestDevicesRenameInvalidName(t *testing.T) {
	useTempCredentials(t)
	id := uuid.MustParse("6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11")
	api := fakeDevicesAPI(t, apigen.DeviceRegistrationCode{}, []apigen.Device{{Id: id, Type: "harwood0", Name: "harwood0"}})
	devLogin(t, api.URL)

	_, err := runRoot(t, "devices", "rename", id.String(), "   ", "--api-url", api.URL)

	assert.EqualError(t, err, "name: is required", "prints the api's message")
}

func TestDevicesRenameUsageErrors(t *testing.T) {
	for _, tc := range []struct {
		desc string
		args []string
		err  string
	}{
		{"non-UUID ID", []string{"not-a-uuid", "Bench rover"}, `invalid device id "not-a-uuid": must be a UUID`},
		{"missing name", []string{"6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11"}, "accepts 2 arg(s), received 1"},
		{"unquoted name", []string{"6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11", "Bench", "rover"}, "accepts 2 arg(s), received 3"},
	} {
		t.Run(tc.desc, func(t *testing.T) {
			useTempCredentials(t)
			api, requests := fakeDevicesAPIWithCount(t, apigen.DeviceRegistrationCode{}, nil)
			devLogin(t, api.URL)

			_, err := runRoot(t, append([]string{"devices", "rename"}, append(tc.args, "--api-url", api.URL)...)...)

			assert.EqualError(t, err, tc.err)
			assert.Zero(t, requests.Load(), "a usage error sends no request")
		})
	}
}
