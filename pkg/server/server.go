// Package server provides a REST API server that bridges HTTP calls to core.Driver.
package server

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
	"sync"

	"github.com/devicelab-dev/maestro-runner/pkg/core"
	"github.com/devicelab-dev/maestro-runner/pkg/flow"
	"github.com/devicelab-dev/maestro-runner/pkg/logger"
)

// SessionState holds a driver session.
type SessionState struct {
	Driver  core.Driver
	Cleanup func()
}

// Server is the REST API server.
type Server struct {
	mu       sync.RWMutex
	sessions map[string]*SessionState

	// CreateDriver is called when POST /session is invoked.
	// It receives the session request and must return a driver + cleanup func.
	CreateDriver func(req SessionRequest) (core.Driver, func(), error)
}

// SessionRequest is the JSON body for POST /session.
type SessionRequest struct {
	PlatformName string `json:"platformName"`
	DeviceID     string `json:"deviceId,omitempty"`
	AppID        string `json:"appId,omitempty"`
	Driver       string `json:"driver,omitempty"`
}

// SessionResponse is the JSON response for POST /session.
type SessionResponse struct {
	SessionID string `json:"sessionId"`
}

// ErrorResponse is a JSON error response.
type ErrorResponse struct {
	Error string `json:"error"`
}

// New creates a new Server.
func New(createDriver func(req SessionRequest) (core.Driver, func(), error)) *Server {
	return &Server{
		sessions:     make(map[string]*SessionState),
		CreateDriver: createDriver,
	}
}

// Handler returns an http.Handler with all routes registered.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /status", s.handleStatus)
	mux.HandleFunc("POST /session", s.handleCreateSession)
	mux.HandleFunc("POST /session/{id}/execute", s.handleExecute)
	mux.HandleFunc("GET /session/{id}/screenshot", s.handleScreenshot)
	mux.HandleFunc("GET /session/{id}/source", s.handleSource)
	mux.HandleFunc("GET /session/{id}/device-info", s.handleDeviceInfo)
	mux.HandleFunc("DELETE /session/{id}", s.handleDeleteSession)

	return mux
}

// ShutdownAll cleans up all active sessions.
func (s *Server) ShutdownAll() {
	s.mu.Lock()
	defer s.mu.Unlock()
	for id, sess := range s.sessions {
		logger.Info("Cleaning up session %s", id)
		if sess.Cleanup != nil {
			sess.Cleanup()
		}
		delete(s.sessions, id)
	}
}

func (s *Server) handleStatus(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	s.mu.RLock()
	count := len(s.sessions)
	s.mu.RUnlock()
	writeJSON(w, http.StatusOK, map[string]interface{}{
		"status":   "ok",
		"sessions": count,
	})
}

func (s *Server) handleCreateSession(w http.ResponseWriter, r *http.Request) {
	var req SessionRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "invalid request body: " + err.Error()})
		return
	}

	if req.PlatformName == "" {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "platformName is required"})
		return
	}

	driver, cleanup, err := s.CreateDriver(req)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, ErrorResponse{Error: "failed to create driver: " + err.Error()})
		return
	}

	sessionID := generateSessionID()
	s.mu.Lock()
	s.sessions[sessionID] = &SessionState{
		Driver:  driver,
		Cleanup: cleanup,
	}
	s.mu.Unlock()

	logger.Info("Created session %s for platform=%s", sessionID, req.PlatformName)
	writeJSON(w, http.StatusOK, SessionResponse{SessionID: sessionID})
}

func (s *Server) handleExecute(w http.ResponseWriter, r *http.Request) {
	sess, ok := s.getSession(w, r)
	if !ok {
		return
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "failed to read body: " + err.Error()})
		return
	}

	step, err := flow.UnmarshalStep(body)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "invalid step: " + err.Error()})
		return
	}

	result := sess.Driver.Execute(step)
	writeJSON(w, http.StatusOK, result)
}

func (s *Server) handleScreenshot(w http.ResponseWriter, r *http.Request) {
	sess, ok := s.getSession(w, r)
	if !ok {
		return
	}

	png, err := sess.Driver.Screenshot()
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, ErrorResponse{Error: "screenshot failed: " + err.Error()})
		return
	}

	w.Header().Set("Content-Type", "image/png")
	w.WriteHeader(http.StatusOK)
	if _, err := w.Write(png); err != nil {
		log.Printf("failed to write screenshot: %v", err)
	}
}

func (s *Server) handleSource(w http.ResponseWriter, r *http.Request) {
	sess, ok := s.getSession(w, r)
	if !ok {
		return
	}

	hierarchy, err := sess.Driver.Hierarchy()
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, ErrorResponse{Error: "hierarchy failed: " + err.Error()})
		return
	}

	// Detect content type from the hierarchy bytes
	contentType := "application/xml"
	if len(hierarchy) > 0 && hierarchy[0] == '{' {
		contentType = "application/json"
	}
	w.Header().Set("Content-Type", contentType)
	w.WriteHeader(http.StatusOK)
	if _, err := w.Write(hierarchy); err != nil {
		log.Printf("failed to write hierarchy: %v", err)
	}
}

func (s *Server) handleDeviceInfo(w http.ResponseWriter, r *http.Request) {
	sess, ok := s.getSession(w, r)
	if !ok {
		return
	}

	info := sess.Driver.GetPlatformInfo()
	writeJSON(w, http.StatusOK, info)
}

func (s *Server) handleDeleteSession(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")

	s.mu.Lock()
	sess, exists := s.sessions[id]
	if exists {
		delete(s.sessions, id)
	}
	s.mu.Unlock()

	if !exists {
		writeJSON(w, http.StatusNotFound, ErrorResponse{Error: fmt.Sprintf("session %s not found", id)})
		return
	}

	if sess.Cleanup != nil {
		sess.Cleanup()
	}
	logger.Info("Deleted session %s", id)
	w.WriteHeader(http.StatusNoContent)
}

// getSession retrieves a session by the {id} path parameter. Returns false if not found.
func (s *Server) getSession(w http.ResponseWriter, r *http.Request) (*SessionState, bool) {
	id := r.PathValue("id")

	s.mu.RLock()
	sess, exists := s.sessions[id]
	s.mu.RUnlock()

	if !exists {
		writeJSON(w, http.StatusNotFound, ErrorResponse{Error: fmt.Sprintf("session %s not found", id)})
		return nil, false
	}
	return sess, true
}

func generateSessionID() string {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		// Fallback — should never happen
		return fmt.Sprintf("session-%d", len(b))
	}
	return hex.EncodeToString(b)
}

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("failed to encode JSON response: %v", err)
	}
}

// SanitizePlatform normalizes the platform name.
func SanitizePlatform(p string) string {
	return strings.ToLower(strings.TrimSpace(p))
}
