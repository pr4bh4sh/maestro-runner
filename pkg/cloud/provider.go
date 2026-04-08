// Package cloud provides an abstraction for cloud device providers
// (Sauce Labs, BrowserStack, LambdaTest, TestingBot, etc.).
//
// Each provider registers itself via init(). The Detect function
// selects the matching provider from the Appium URL.
package cloud

import "sync"

// Provider abstracts cloud device provider operations.
type Provider interface {
	// Name returns the human-readable provider name (e.g., "Sauce Labs").
	Name() string

	// ExtractMeta extracts provider-specific metadata from the Appium session.
	// Called once after the session is created.
	// sessionID is the WebDriver session ID; caps are the merged capabilities
	// from the session response; meta is the output map to populate.
	ExtractMeta(sessionID string, caps map[string]interface{}, meta map[string]string)

	// ReportResult reports the test result to the cloud provider.
	// Called once after all flows and reports have completed.
	ReportResult(appiumURL string, meta map[string]string, result *TestResult) error
}

// TestResult contains the test run outcome passed to cloud providers.
type TestResult struct {
	Passed      bool
	Total       int
	PassedCount int
	FailedCount int
	Duration    int64  // total milliseconds
	OutputDir   string // path to log, reports, screenshots
	Flows       []FlowResult
}

// FlowResult contains the outcome of a single flow.
type FlowResult struct {
	Name     string
	File     string // source YAML file path
	Passed   bool
	Duration int64 // milliseconds
	Error    string
}

// ProviderFactory returns a Provider if the Appium URL matches, or nil.
type ProviderFactory func(appiumURL string) Provider

var (
	mu        sync.RWMutex
	factories []ProviderFactory
)

// Register adds a provider factory to the registry.
// Called from init() in each provider implementation file.
func Register(f ProviderFactory) {
	mu.Lock()
	defer mu.Unlock()
	factories = append(factories, f)
}

// Detect returns the first Provider matching the Appium URL, or nil.
func Detect(appiumURL string) Provider {
	mu.RLock()
	defer mu.RUnlock()
	for _, f := range factories {
		if p := f(appiumURL); p != nil {
			return p
		}
	}
	return nil
}
