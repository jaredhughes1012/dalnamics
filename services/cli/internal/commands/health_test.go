package commands

import (
	"bytes"
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"dalnamics/internal/health"
)

func runRoot(t *testing.T, args ...string) (string, error) {
	t.Helper()
	var out bytes.Buffer
	root := NewRootCmd()
	root.SetOut(&out)
	root.SetErr(&out)
	root.SetArgs(args)
	err := root.ExecuteContext(context.Background())
	return out.String(), err
}

func TestHealth(t *testing.T) {
	srv := httptest.NewServer(health.Handler("api"))
	defer srv.Close()

	out, err := runRoot(t, "health", "--api-url", srv.URL)
	if err != nil {
		t.Fatalf("health: %v", err)
	}
	if out != "api: ok\n" {
		t.Errorf("output = %q", out)
	}
}

func TestHealthJSON(t *testing.T) {
	srv := httptest.NewServer(health.Handler("api"))
	defer srv.Close()

	out, err := runRoot(t, "health", "--json", "--api-url", srv.URL)
	if err != nil {
		t.Fatalf("health: %v", err)
	}
	if strings.TrimSpace(out) != `{"status":"ok","service":"api"}` {
		t.Errorf("output = %q", out)
	}
}

func TestHealthUnhealthy(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	defer srv.Close()

	_, err := runRoot(t, "health", "--api-url", srv.URL)
	if err == nil || !strings.Contains(err.Error(), "503") {
		t.Errorf("err = %v, want 503 error", err)
	}
}
