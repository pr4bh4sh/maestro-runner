package executor

import (
	"strings"

	"github.com/devicelab-dev/maestro-runner/pkg/core"
	"github.com/devicelab-dev/maestro-runner/pkg/report"
)

// commandResultToElement converts core.CommandResult to report.Element.
func commandResultToElement(r *core.CommandResult) *report.Element {
	if r == nil || r.Element == nil {
		return nil
	}

	el := r.Element
	element := &report.Element{
		Found: true,
		ID:    el.ID,
		Text:  el.Text,
		Class: el.Class,
	}

	// Convert bounds
	element.Bounds = &report.Bounds{
		X:      el.Bounds.X,
		Y:      el.Bounds.Y,
		Width:  el.Bounds.Width,
		Height: el.Bounds.Height,
	}

	return element
}

// commandResultToError converts core.CommandResult error to report.Error.
func commandResultToError(r *core.CommandResult) *report.Error {
	if r == nil || r.Error == nil {
		return nil
	}

	message := r.Error.Error()

	// Use message from result if available
	if r.Message != "" {
		message = r.Message
	}

	errType := classifyError(message)

	return &report.Error{
		Type:    errType,
		Message: message,
	}
}

// classifyError determines the error type from the message.
// Types: assertion, timeout, element_not_found, app_crash, network, unknown
func classifyError(msg string) string {
	lower := strings.ToLower(msg)

	switch {
	case strings.Contains(lower, "not found"):
		return "element_not_found"
	case strings.Contains(lower, "keyboard is covering") || strings.Contains(lower, "keyboard is open"):
		return "element_not_found"
	case strings.Contains(lower, "not visible") || strings.Contains(lower, "not displayed"):
		return "assertion"
	case strings.Contains(lower, "timeout") || strings.Contains(lower, "timed out"):
		return "timeout"
	case strings.Contains(lower, "crash") || strings.Contains(lower, "not responding") || strings.Contains(lower, "not installed"):
		return "app_crash"
	case strings.Contains(lower, "connection") || strings.Contains(lower, "refused") || strings.Contains(lower, "unreachable"):
		return "network"
	default:
		return "unknown"
	}
}
