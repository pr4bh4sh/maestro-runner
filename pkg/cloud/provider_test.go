package cloud

import "testing"

func TestDetect_NoMatch_ReturnsNil(t *testing.T) {
	// Reset registry for isolated test
	mu.Lock()
	saved := factories
	factories = nil
	mu.Unlock()
	defer func() {
		mu.Lock()
		factories = saved
		mu.Unlock()
	}()

	if p := Detect("http://localhost:4723"); p != nil {
		t.Errorf("expected nil, got %q", p.Name())
	}
}

func TestDetect_MatchesProvider(t *testing.T) {
	mu.Lock()
	saved := factories
	factories = nil
	mu.Unlock()
	defer func() {
		mu.Lock()
		factories = saved
		mu.Unlock()
	}()

	Register(func(url string) Provider {
		if url == "https://example.com" {
			return &testProvider{name: "Example"}
		}
		return nil
	})

	p := Detect("https://example.com")
	if p == nil {
		t.Fatal("expected provider, got nil")
	}
	if p.Name() != "Example" {
		t.Errorf("expected Example, got %q", p.Name())
	}
}

func TestDetect_FirstMatchWins(t *testing.T) {
	mu.Lock()
	saved := factories
	factories = nil
	mu.Unlock()
	defer func() {
		mu.Lock()
		factories = saved
		mu.Unlock()
	}()

	Register(func(url string) Provider { return &testProvider{name: "First"} })
	Register(func(url string) Provider { return &testProvider{name: "Second"} })

	p := Detect("anything")
	if p == nil || p.Name() != "First" {
		t.Errorf("expected First, got %v", p)
	}
}

func TestDetect_SkipsNilFactory(t *testing.T) {
	mu.Lock()
	saved := factories
	factories = nil
	mu.Unlock()
	defer func() {
		mu.Lock()
		factories = saved
		mu.Unlock()
	}()

	Register(func(url string) Provider { return nil })
	Register(func(url string) Provider { return &testProvider{name: "Fallback"} })

	p := Detect("anything")
	if p == nil || p.Name() != "Fallback" {
		t.Errorf("expected Fallback, got %v", p)
	}
}

// testProvider is a minimal Provider for registry tests.
type testProvider struct {
	name string
}

func (t *testProvider) Name() string { return t.name }
func (t *testProvider) ExtractMeta(sessionID string, caps map[string]interface{}, meta map[string]string) {
}
func (t *testProvider) ReportResult(appiumURL string, meta map[string]string, result *TestResult) error {
	return nil
}
