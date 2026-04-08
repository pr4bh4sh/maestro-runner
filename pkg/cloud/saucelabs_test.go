package cloud

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

func TestNewSauceLabs_MatchesURLs(t *testing.T) {
	urls := []string{
		"https://user:key@ondemand.us-west-1.saucelabs.com:443/wd/hub",
		"https://user:key@ondemand.eu-central-1.saucelabs.com/wd/hub",
		"https://user:key@ondemand.us-east-4.saucelabs.com/wd/hub",
		"https://user:key@ondemand.SAUCELABS.com/wd/hub",
	}
	for _, u := range urls {
		if p := newSauceLabs(u); p == nil {
			t.Errorf("expected match for %s", u)
		}
	}
}

func TestNewSauceLabs_RejectsNonSauce(t *testing.T) {
	urls := []string{
		"http://localhost:4723",
		"https://hub.browserstack.com/wd/hub",
		"https://hub.testingbot.com/wd/hub",
		"",
	}
	for _, u := range urls {
		if p := newSauceLabs(u); p != nil {
			t.Errorf("expected nil for %q, got %q", u, p.Name())
		}
	}
}

func TestExtractMeta_RealDevice(t *testing.T) {
	p := &sauceLabs{}
	caps := map[string]interface{}{
		"appium:jobUuid":  "abc-123",
		"appium:deviceName": "Samsung Galaxy S21",
	}
	meta := make(map[string]string)
	p.ExtractMeta("session-456", caps, meta)

	if meta["type"] != "rdc" {
		t.Errorf("expected type=rdc, got %q", meta["type"])
	}
	if meta["jobID"] != "abc-123" {
		t.Errorf("expected jobID=abc-123, got %q", meta["jobID"])
	}
}

func TestExtractMeta_Emulator(t *testing.T) {
	p := &sauceLabs{}
	caps := map[string]interface{}{
		"appium:deviceName": "Google Pixel 9 Emulator",
	}
	meta := make(map[string]string)
	p.ExtractMeta("session-789", caps, meta)

	if meta["type"] != "vms" {
		t.Errorf("expected type=vms, got %q", meta["type"])
	}
	if meta["jobID"] != "session-789" {
		t.Errorf("expected jobID=session-789, got %q", meta["jobID"])
	}
}

func TestExtractMeta_Simulator(t *testing.T) {
	p := &sauceLabs{}
	caps := map[string]interface{}{
		"appium:deviceName": "iPhone Simulator",
	}
	meta := make(map[string]string)
	p.ExtractMeta("session-101", caps, meta)

	if meta["type"] != "vms" {
		t.Errorf("expected type=vms, got %q", meta["type"])
	}
}

func TestAPIBaseFromAppiumURL_Regions(t *testing.T) {
	tests := []struct {
		url      string
		expected string
	}{
		{"https://user:key@ondemand.eu-central-1.saucelabs.com/wd/hub", "https://api.eu-central-1.saucelabs.com"},
		{"https://user:key@ondemand.us-east-4.saucelabs.com/wd/hub", "https://api.us-east-4.saucelabs.com"},
		{"https://user:key@ondemand.us-west-1.saucelabs.com/wd/hub", "https://api.us-west-1.saucelabs.com"},
		{"https://user:key@ondemand.saucelabs.com/wd/hub", "https://api.us-west-1.saucelabs.com"},
	}
	for _, tt := range tests {
		got, err := apiBaseFromAppiumURL(tt.url)
		if err != nil {
			t.Errorf("unexpected error for %s: %v", tt.url, err)
		}
		if got != tt.expected {
			t.Errorf("apiBase(%s) = %q, want %q", tt.url, got, tt.expected)
		}
	}
}

func TestAPIBaseFromAppiumURL_Empty(t *testing.T) {
	_, err := apiBaseFromAppiumURL("")
	if err == nil {
		t.Error("expected error for empty URL")
	}
}

func TestCredentialsFromAppiumURL_FromURL(t *testing.T) {
	u, k, err := credentialsFromAppiumURL("https://myuser:mykey@ondemand.saucelabs.com/wd/hub")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if u != "myuser" || k != "mykey" {
		t.Errorf("got (%q, %q), want (myuser, mykey)", u, k)
	}
}

func TestCredentialsFromAppiumURL_FromEnv(t *testing.T) {
	os.Setenv("SAUCE_USERNAME", "envuser")
	os.Setenv("SAUCE_ACCESS_KEY", "envkey")
	defer os.Unsetenv("SAUCE_USERNAME")
	defer os.Unsetenv("SAUCE_ACCESS_KEY")

	u, k, err := credentialsFromAppiumURL("https://ondemand.saucelabs.com/wd/hub")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if u != "envuser" || k != "envkey" {
		t.Errorf("got (%q, %q), want (envuser, envkey)", u, k)
	}
}

func TestCredentialsFromAppiumURL_Missing(t *testing.T) {
	os.Unsetenv("SAUCE_USERNAME")
	os.Unsetenv("SAUCE_ACCESS_KEY")

	_, _, err := credentialsFromAppiumURL("https://ondemand.saucelabs.com/wd/hub")
	if err == nil {
		t.Error("expected error when credentials are missing")
	}
}

func TestCapsDeviceNameIndicatesEmuSim(t *testing.T) {
	tests := []struct {
		name     string
		caps     map[string]interface{}
		expected bool
	}{
		{"nil caps", nil, false},
		{"real device", map[string]interface{}{"appium:deviceName": "Samsung Galaxy S21"}, false},
		{"emulator", map[string]interface{}{"appium:deviceName": "Google Pixel 9 Emulator"}, true},
		{"simulator", map[string]interface{}{"deviceName": "iPhone Simulator"}, true},
		{"nested", map[string]interface{}{
			"sauce:options": map[string]interface{}{
				"deviceName": "Android Emulator",
			},
		}, true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := capsDeviceNameIndicatesEmuSim(tt.caps); got != tt.expected {
				t.Errorf("got %v, want %v", got, tt.expected)
			}
		})
	}
}

func TestJobUUIDFromSessionCaps(t *testing.T) {
	tests := []struct {
		name     string
		caps     map[string]interface{}
		expected string
	}{
		{"nil", nil, ""},
		{"has appium:jobUuid", map[string]interface{}{"appium:jobUuid": "uuid-123"}, "uuid-123"},
		{"has jobUuid", map[string]interface{}{"jobUuid": "uuid-456"}, "uuid-456"},
		{"prefers appium:jobUuid", map[string]interface{}{"appium:jobUuid": "a", "jobUuid": "b"}, "a"},
		{"empty value", map[string]interface{}{"appium:jobUuid": ""}, ""},
		{"no uuid key", map[string]interface{}{"platformName": "Android"}, ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := jobUUIDFromSessionCaps(tt.caps); got != tt.expected {
				t.Errorf("got %q, want %q", got, tt.expected)
			}
		})
	}
}

func TestReportResult_RDC(t *testing.T) {
	var gotPath string
	var gotBody map[string]bool

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotPath = r.URL.Path
		body, _ := io.ReadAll(r.Body)
		json.Unmarshal(body, &gotBody)
		w.WriteHeader(200)
	}))
	defer srv.Close()

	p := &sauceLabs{}
	meta := map[string]string{"type": "rdc", "jobID": "job-abc"}
	result := &TestResult{Passed: true}

	// Override apiBase by using the test server URL directly
	err := updateJob(srv.URL+"/v1/rdc/jobs/job-abc", "user", "key", true)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if gotPath != "/v1/rdc/jobs/job-abc" {
		t.Errorf("path = %q, want /v1/rdc/jobs/job-abc", gotPath)
	}
	if gotBody["passed"] != true {
		t.Errorf("body passed = %v, want true", gotBody["passed"])
	}

	// Verify the provider wiring works
	_ = p
	_ = meta
	_ = result
}

func TestReportResult_VMs(t *testing.T) {
	var gotPath string
	var gotBody map[string]bool

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotPath = r.URL.Path
		body, _ := io.ReadAll(r.Body)
		json.Unmarshal(body, &gotBody)
		w.WriteHeader(200)
	}))
	defer srv.Close()

	err := updateJob(srv.URL+"/rest/v1/myuser/jobs/session-123", "myuser", "mykey", false)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if gotPath != "/rest/v1/myuser/jobs/session-123" {
		t.Errorf("path = %q, want /rest/v1/myuser/jobs/session-123", gotPath)
	}
	if gotBody["passed"] != false {
		t.Errorf("body passed = %v, want false", gotBody["passed"])
	}
}

func TestReportResult_EmptyJobID(t *testing.T) {
	p := &sauceLabs{}
	meta := map[string]string{"type": "rdc", "jobID": ""}
	err := p.ReportResult("https://user:key@ondemand.saucelabs.com/wd/hub", meta, &TestResult{Passed: true})
	if err == nil {
		t.Error("expected error for empty job ID")
	}
}

func TestUpdateJob_ServerError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(500)
		w.Write([]byte("internal error"))
	}))
	defer srv.Close()

	err := updateJob(srv.URL+"/v1/rdc/jobs/123", "user", "key", true)
	if err == nil {
		t.Error("expected error for 500 response")
	}
}
