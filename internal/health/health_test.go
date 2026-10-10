package health

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHandler(t *testing.T) {
	rec := httptest.NewRecorder()
	Handler("api")(rec, httptest.NewRequest(http.MethodGet, Path, nil))

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", rec.Code, http.StatusOK)
	}
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}

	var got Response
	if err := json.NewDecoder(rec.Body).Decode(&got); err != nil {
		t.Fatalf("decode: %v", err)
	}
	want := Response{Status: StatusOK, Service: "api"}
	if got != want {
		t.Errorf("body = %+v, want %+v", got, want)
	}
}
