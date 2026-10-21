package server

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"go.uber.org/mock/gomock"

	"dalnamics/services/devicemgr/internal/store"
)

// post calls a /mqtt endpoint the way mosquitto-go-auth does: JSON params and
// no Authorization header.
func post(h http.Handler, path, body string) int {
	req := httptest.NewRequest(http.MethodPost, path, strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec.Code
}

func TestCheckMqttUser(t *testing.T) {
	h, q := newHandler(t)
	unknown := uuid.New()
	q.EXPECT().GetDeviceSecretHash(gomock.Any(), unknown).Return(nil, store.ErrNoRows)

	assert.Equal(t, http.StatusOK, post(h, "/mqtt/user", `{"username":"devicemgr","password":"`+testMQTTPassword+`","clientid":"dm"}`))
	assert.Equal(t, http.StatusForbidden, post(h, "/mqtt/user", `{"username":"devicemgr","password":"wrong","clientid":"dm"}`))
	assert.Equal(t, http.StatusOK, post(h, "/mqtt/user", `{"username":"register","password":"","clientid":"c1"}`))
	assert.Equal(t, http.StatusForbidden, post(h, "/mqtt/user", `{"username":"`+unknown.String()+`","password":"s","clientid":"d"}`))
}

func TestCheckMqttUserStoreErrorDenies(t *testing.T) {
	h, q := newHandler(t)
	q.EXPECT().GetDeviceSecretHash(gomock.Any(), gomock.Any()).Return(nil, assert.AnError)

	assert.Equal(t, http.StatusInternalServerError, post(h, "/mqtt/user", `{"username":"`+uuid.NewString()+`","password":"s","clientid":"d"}`))
}

func TestCheckMqttSuperuser(t *testing.T) {
	h, _ := newHandler(t)

	assert.Equal(t, http.StatusOK, post(h, "/mqtt/superuser", `{"username":"devicemgr"}`))
	assert.Equal(t, http.StatusForbidden, post(h, "/mqtt/superuser", `{"username":"register"}`))
}

func TestCheckMqttAcl(t *testing.T) {
	h, _ := newHandler(t)

	assert.Equal(t, http.StatusOK, post(h, "/mqtt/acl", `{"username":"register","clientid":"c1","topic":"devices/register/c1","acc":2}`))
	assert.Equal(t, http.StatusForbidden, post(h, "/mqtt/acl", `{"username":"register","clientid":"c1","topic":"devices/register/c2","acc":2}`))
}

func TestMqttEndpointsRejectMalformedBodies(t *testing.T) {
	h, _ := newHandler(t)

	assert.Equal(t, http.StatusBadRequest, post(h, "/mqtt/user", `not json`))
}

func TestMqttEndpointsStillNeedTokenForOtherMethods(t *testing.T) {
	h, _ := newHandler(t)
	req := httptest.NewRequest(http.MethodGet, "/mqtt/user", nil)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	assert.Equal(t, http.StatusUnauthorized, rec.Code)
}
