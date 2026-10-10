package server

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"dalnamics/internal/health"
)

func TestHealthRoute(t *testing.T) {
	srv := httptest.NewServer(NewHandler())
	defer srv.Close()

	res, err := http.Get(srv.URL + health.Path)
	if err != nil {
		t.Fatalf("get: %v", err)
	}
	defer res.Body.Close()

	if res.StatusCode != http.StatusOK {
		t.Fatalf("status = %d, want %d", res.StatusCode, http.StatusOK)
	}
	var body health.Response
	if err := json.NewDecoder(res.Body).Decode(&body); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if body.Service != ServiceName || body.Status != health.StatusOK {
		t.Errorf("body = %+v", body)
	}
}

func TestHealthRouteRejectsPost(t *testing.T) {
	rec := httptest.NewRecorder()
	NewHandler().ServeHTTP(rec, httptest.NewRequest(http.MethodPost, health.Path, nil))

	if rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusMethodNotAllowed)
	}
}
