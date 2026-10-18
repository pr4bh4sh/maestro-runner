package cli

import "testing"

// The E2E matrix sets MAESTRO_DRIVER per job, which reaches the binary as the
// global --driver flag. runServer used to read only the per-request driver, so
// the flag was dropped and every Android session fell back to devicelab -- the
// `uiautomator2` job was silently testing the devicelab driver.
func TestResolveDriver(t *testing.T) {
	tests := []struct {
		name    string
		request string
		flag    string
		want    string
	}{
		{
			name: "flag is used when the request omits a driver",
			// The regression: --driver uiautomator2 with no request driver.
			request: "",
			flag:    "uiautomator2",
			want:    "uiautomator2",
		},
		{
			name:    "request driver wins over the flag",
			request: "appium",
			flag:    "uiautomator2",
			want:    "appium",
		},
		{
			name:    "neither set yields empty so the platform default applies",
			request: "",
			flag:    "",
			want:    "",
		},
		{
			name:    "appium driver from the flag is honoured",
			request: "",
			flag:    "appium",
			want:    "appium",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := resolveDriver(tt.request, tt.flag); got != tt.want {
				t.Errorf("resolveDriver(%q, %q) = %q, want %q",
					tt.request, tt.flag, got, tt.want)
			}
		})
	}
}
