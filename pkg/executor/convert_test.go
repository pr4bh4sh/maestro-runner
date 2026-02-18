package executor

import (
	"fmt"
	"testing"

	"github.com/devicelab-dev/maestro-runner/pkg/core"
)

func TestClassifyError(t *testing.T) {
	tests := []struct {
		msg  string
		want string
	}{
		{"Element not found: text='Login'", "element_not_found"},
		{"Element not found within 5000ms", "element_not_found"},
		{"Element found but keyboard is covering it (keyboard top: 1111, element center Y: 1178)", "element_not_found"},
		{"keyboard is open — add a `- hideKeyboard` step", "element_not_found"},
		{"Element not visible after 5000ms", "assertion"},
		{"Text is not displayed", "assertion"},
		{"Operation timed out after 30s", "timeout"},
		{"Connection timed out", "timeout"},
		{"App crashed during launch", "app_crash"},
		{"Application not responding", "app_crash"},
		{"App not installed: com.example", "app_crash"},
		{"Connection refused", "network"},
		{"Host unreachable", "network"},
		{"some other error", "unknown"},
	}

	for _, tt := range tests {
		t.Run(tt.msg, func(t *testing.T) {
			got := classifyError(tt.msg)
			if got != tt.want {
				t.Errorf("classifyError(%q) = %q, want %q", tt.msg, got, tt.want)
			}
		})
	}
}

func TestCommandResultToErrorClassification(t *testing.T) {
	t.Run("nil result", func(t *testing.T) {
		if got := commandResultToError(nil); got != nil {
			t.Errorf("expected nil, got %+v", got)
		}
	})

	t.Run("nil error", func(t *testing.T) {
		r := &core.CommandResult{Success: true}
		if got := commandResultToError(r); got != nil {
			t.Errorf("expected nil, got %+v", got)
		}
	})

	t.Run("element not found", func(t *testing.T) {
		r := &core.CommandResult{
			Error:   fmt.Errorf("element not found"),
			Message: "Element not found: text='Login'",
		}
		got := commandResultToError(r)
		if got == nil {
			t.Fatal("expected non-nil error")
		}
		if got.Type != "element_not_found" {
			t.Errorf("Type = %q, want %q", got.Type, "element_not_found")
		}
	})

	t.Run("keyboard covering", func(t *testing.T) {
		r := &core.CommandResult{
			Error:   fmt.Errorf("keyboard is open"),
			Message: "Element found but keyboard is covering it (keyboard top: 1111, element center Y: 1178)",
		}
		got := commandResultToError(r)
		if got == nil {
			t.Fatal("expected non-nil error")
		}
		if got.Type != "element_not_found" {
			t.Errorf("Type = %q, want %q", got.Type, "element_not_found")
		}
	})

	t.Run("uses message over error", func(t *testing.T) {
		r := &core.CommandResult{
			Error:   fmt.Errorf("raw error"),
			Message: "Connection refused to device",
		}
		got := commandResultToError(r)
		if got == nil {
			t.Fatal("expected non-nil error")
		}
		if got.Type != "network" {
			t.Errorf("Type = %q, want %q", got.Type, "network")
		}
		if got.Message != "Connection refused to device" {
			t.Errorf("Message = %q, want message from result", got.Message)
		}
	})
}
