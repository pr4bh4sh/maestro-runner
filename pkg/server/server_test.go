package server

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/devicelab-dev/maestro-runner/pkg/core"
	"github.com/devicelab-dev/maestro-runner/pkg/driver/mock"
)

func newTestServer() (*Server, *mock.Driver) {
	drv := mock.New(mock.Config{Platform: "android", DeviceID: "test-device"})
	srv := New(func(req SessionRequest) (core.Driver, func(), error) {
		return drv, func() {}, nil
	})
	return srv, drv
}

func createSession(t *testing.T, handler http.Handler) string {
	t.Helper()
	body := `{"platformName":"android","deviceId":"test-device"}`
	req := httptest.NewRequest("POST", "/session", bytes.NewBufferString(body))
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("create session: expected 200, got %d: %s", w.Code, w.Body.String())
	}
	var resp SessionResponse
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("decode session response: %v", err)
	}
	if resp.SessionID == "" {
		t.Fatal("session id is empty")
	}
	return resp.SessionID
}

func TestStatus(t *testing.T) {
	srv, _ := newTestServer()
	handler := srv.Handler()
	req := httptest.NewRequest("GET", "/status", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	var body map[string]interface{}
	if err := json.NewDecoder(w.Body).Decode(&body); err != nil {
		t.Fatalf("decode error: %v", err)
	}
	if body["status"] != "ok" {
		t.Errorf("expected status ok, got %v", body["status"])
	}
}

func TestCreateSession(t *testing.T) {
	srv, _ := newTestServer()
	handler := srv.Handler()
	sid := createSession(t, handler)
	req := httptest.NewRequest("GET", "/status", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	var body map[string]interface{}
	json.NewDecoder(w.Body).Decode(&body)
	if body["sessions"].(float64) != 1 {
		t.Errorf("expected 1 session, got %v", body["sessions"])
	}
	_ = sid
}

func TestCreateSession_MissingPlatform(t *testing.T) {
	srv, _ := newTestServer()
	handler := srv.Handler()
	req := httptest.NewRequest("POST", "/session", bytes.NewBufferString(`{"deviceId":"x"}`))
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", w.Code)
	}
}

func TestExecuteStep(t *testing.T) {
	srv, _ := newTestServer()
	handler := srv.Handler()
	sid := createSession(t, handler)
	step := `{"type":"tapOn","selector":"Login"}`
	req := httptest.NewRequest("POST", "/session/"+sid+"/execute", bytes.NewBufferString(step))
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", w.Code, w.Body.String())
	}
	var result core.CommandResult
	if err := json.NewDecoder(w.Body).Decode(&result); err != nil {
		t.Fatalf("decode error: %v", err)
	}
	if !result.Success {
		t.Errorf("expected success, got: %s", result.Message)
	}
}

func TestExecuteStep_InvalidJSON(t *testing.T) {
	srv, _ := newTestServer()
	handler := srv.Handler()
	sid := createSession(t, handler)
	req := httptest.NewRequest("POST", "/session/"+sid+"/execute", bytes.NewBufferString(`not json`))
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", w.Code)
	}
}

func TestExecuteStep_SessionNotFound(t *testing.T) {
	srv, _ := newTestServer()
	handler := srv.Handler()
	req := httptest.NewRequest("POST", "/session/nonexistent/execute", bytes.NewBufferString(`{"type":"back"}`))
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", w.Code)
	}
}

func TestScreenshot(t *testing.T) {
	srv, _ := newTestServer()
	handler := srv.Handler()
	sid := createSession(t, handler)
	req := httptest.NewRequest("GET", "/session/"+sid+"/screenshot", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	if ct := w.Header().Get("Content-Type"); ct != "image/png" {
		t.Errorf("expected image/png, got %s", ct)
	}
	if w.Body.Len() == 0 {
		t.Error("expected non-empty body")
	}
}

func TestSource(t *testing.T) {
	srv, _ := newTestServer()
	handler := srv.Handler()
	sid := createSession(t, handler)
	req := httptest.NewRequest("GET", "/session/"+sid+"/source", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	body, _ := io.ReadAll(w.Body)
	if len(body) == 0 {
		t.Error("expected non-empty hierarchy")
	}
}

func TestDeviceInfo(t *testing.T) {
	srv, _ := newTestServer()
	handler := srv.Handler()
	sid := createSession(t, handler)
	req := httptest.NewRequest("GET", "/session/"+sid+"/device-info", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	var info core.PlatformInfo
	if err := json.NewDecoder(w.Body).Decode(&info); err != nil {
		t.Fatalf("decode error: %v", err)
	}
	if info.Platform != "android" {
		t.Errorf("expected platform android, got %q", info.Platform)
	}
	if info.DeviceID != "test-device" {
		t.Errorf("expected deviceId test-device, got %q", info.DeviceID)
	}
}

func TestDeleteSession(t *testing.T) {
	srv, _ := newTestServer()
	handler := srv.Handler()
	sid := createSession(t, handler)
	req := httptest.NewRequest("DELETE", "/session/"+sid, nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusNoContent {
		t.Fatalf("expected 204, got %d", w.Code)
	}
	req = httptest.NewRequest("GET", "/session/"+sid+"/device-info", nil)
	w = httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusNotFound {
		t.Errorf("expected 404 after delete, got %d", w.Code)
	}
}

func TestDeleteSession_NotFound(t *testing.T) {
	srv, _ := newTestServer()
	handler := srv.Handler()
	req := httptest.NewRequest("DELETE", "/session/nonexistent", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", w.Code)
	}
}

func TestShutdownAll(t *testing.T) {
	srv, _ := newTestServer()
	handler := srv.Handler()
	createSession(t, handler)
	createSession(t, handler)
	srv.ShutdownAll()
	req := httptest.NewRequest("GET", "/status", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	var body map[string]interface{}
	json.NewDecoder(w.Body).Decode(&body)
	if body["sessions"].(float64) != 0 {
		t.Errorf("expected 0 sessions after shutdown, got %v", body["sessions"])
	}
}
