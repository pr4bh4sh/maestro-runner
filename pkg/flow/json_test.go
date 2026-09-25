package flow

import (
	"encoding/json"
	"testing"
)

func TestUnmarshalStep_TapOn(t *testing.T) {
	input := `{"type":"tapOn","selector":"Login","longPress":true,"timeout":5000}`
	step, err := UnmarshalStep([]byte(input))
	if err != nil {
		t.Fatalf("UnmarshalStep error: %v", err)
	}
	if step.Type() != StepTapOn {
		t.Fatalf("expected type %s, got %s", StepTapOn, step.Type())
	}
	tap := step.(*TapOnStep)
	if tap.Selector.Text != "Login" {
		t.Errorf("expected text 'Login', got %q", tap.Selector.Text)
	}
	if !tap.LongPress {
		t.Error("expected longPress=true")
	}
	if tap.TimeoutMs != 5000 {
		t.Errorf("expected timeout 5000, got %d", tap.TimeoutMs)
	}
}

func TestUnmarshalStep_TapOnByID(t *testing.T) {
	input := `{"type":"tapOn","selector":{"id":"btn_login"},"longPress":true}`
	step, err := UnmarshalStep([]byte(input))
	if err != nil {
		t.Fatalf("UnmarshalStep error: %v", err)
	}
	tap := step.(*TapOnStep)
	if tap.Selector.ID != "btn_login" {
		t.Errorf("expected id 'btn_login', got %q", tap.Selector.ID)
	}
	if !tap.LongPress {
		t.Error("expected longPress=true")
	}
}

func TestUnmarshalStep_InputText(t *testing.T) {
	input := `{"type":"inputText","text":"user@example.com"}`
	step, err := UnmarshalStep([]byte(input))
	if err != nil {
		t.Fatalf("UnmarshalStep error: %v", err)
	}
	if step.Type() != StepInputText {
		t.Fatalf("expected type %s, got %s", StepInputText, step.Type())
	}
	is := step.(*InputTextStep)
	if is.Text != "user@example.com" {
		t.Errorf("expected text 'user@example.com', got %q", is.Text)
	}
}

func TestUnmarshalStep_AssertVisible(t *testing.T) {
	input := `{"type":"assertVisible","selector":"Dashboard","timeout":10000}`
	step, err := UnmarshalStep([]byte(input))
	if err != nil {
		t.Fatalf("UnmarshalStep error: %v", err)
	}
	if step.Type() != StepAssertVisible {
		t.Fatalf("expected type %s, got %s", StepAssertVisible, step.Type())
	}
	av := step.(*AssertVisibleStep)
	if av.Selector.Text != "Dashboard" {
		t.Errorf("expected text 'Dashboard', got %q", av.Selector.Text)
	}
	if av.TimeoutMs != 10000 {
		t.Errorf("expected timeout 10000, got %d", av.TimeoutMs)
	}
}

func TestUnmarshalStep_LaunchApp(t *testing.T) {
	input := `{"type":"launchApp","appId":"com.example.app","clearState":true}`
	step, err := UnmarshalStep([]byte(input))
	if err != nil {
		t.Fatalf("UnmarshalStep error: %v", err)
	}
	la := step.(*LaunchAppStep)
	if la.AppID != "com.example.app" {
		t.Errorf("expected appId 'com.example.app', got %q", la.AppID)
	}
	if !la.ClearState {
		t.Error("expected clearState=true")
	}
}

func TestUnmarshalStep_Swipe(t *testing.T) {
	input := `{"type":"swipe","direction":"UP","duration":400}`
	step, err := UnmarshalStep([]byte(input))
	if err != nil {
		t.Fatalf("UnmarshalStep error: %v", err)
	}
	sw := step.(*SwipeStep)
	if sw.Direction != "UP" {
		t.Errorf("expected direction UP, got %q", sw.Direction)
	}
	if sw.Duration != 400 {
		t.Errorf("expected duration 400, got %d", sw.Duration)
	}
}

func TestUnmarshalStep_Back(t *testing.T) {
	input := `{"type":"back"}`
	step, err := UnmarshalStep([]byte(input))
	if err != nil {
		t.Fatalf("UnmarshalStep error: %v", err)
	}
	if step.Type() != StepBack {
		t.Fatalf("expected type %s, got %s", StepBack, step.Type())
	}
}

func TestUnmarshalStep_PressKey(t *testing.T) {
	input := `{"type":"pressKey","key":"ENTER"}`
	step, err := UnmarshalStep([]byte(input))
	if err != nil {
		t.Fatalf("UnmarshalStep error: %v", err)
	}
	pk := step.(*PressKeyStep)
	if pk.Key != "ENTER" {
		t.Errorf("expected key 'ENTER', got %q", pk.Key)
	}
}

func TestUnmarshalStep_EraseText(t *testing.T) {
	input := `{"type":"eraseText","charactersToErase":5}`
	step, err := UnmarshalStep([]byte(input))
	if err != nil {
		t.Fatalf("UnmarshalStep error: %v", err)
	}
	et := step.(*EraseTextStep)
	if et.Characters != 5 {
		t.Errorf("expected characters 5, got %d", et.Characters)
	}
}

func TestUnmarshalStep_MissingType(t *testing.T) {
	input := `{"text":"Login"}`
	_, err := UnmarshalStep([]byte(input))
	if err == nil {
		t.Fatal("expected error for missing type")
	}
}

func TestUnmarshalStep_Optional(t *testing.T) {
	input := `{"type":"tapOn","selector":"OK","optional":true}`
	step, err := UnmarshalStep([]byte(input))
	if err != nil {
		t.Fatalf("UnmarshalStep error: %v", err)
	}
	if !step.IsOptional() {
		t.Error("expected optional=true")
	}
}

func TestUnmarshalStep_StopApp(t *testing.T) {
	input := `{"type":"stopApp","appId":"com.example.app"}`
	step, err := UnmarshalStep([]byte(input))
	if err != nil {
		t.Fatalf("UnmarshalStep error: %v", err)
	}
	sa := step.(*StopAppStep)
	if sa.AppID != "com.example.app" {
		t.Errorf("expected appId 'com.example.app', got %q", sa.AppID)
	}
}

func TestUnmarshalStep_Scroll(t *testing.T) {
	input := `{"type":"scroll"}`
	step, err := UnmarshalStep([]byte(input))
	if err != nil {
		t.Fatalf("UnmarshalStep error: %v", err)
	}
	if step.Type() != StepScroll {
		t.Fatalf("expected type %s, got %s", StepScroll, step.Type())
	}
}

// --- Selector JSON ---

func TestSelector_MarshalJSON_TextOnly(t *testing.T) {
	s := Selector{Text: "Login"}
	data, err := json.Marshal(s)
	if err != nil {
		t.Fatalf("marshal error: %v", err)
	}
	// Text-only selector should marshal as plain string
	if string(data) != `"Login"` {
		t.Errorf("expected \"Login\", got %s", string(data))
	}
}

func TestSelector_MarshalJSON_WithID(t *testing.T) {
	s := Selector{Text: "Login", ID: "btn"}
	data, err := json.Marshal(s)
	if err != nil {
		t.Fatalf("marshal error: %v", err)
	}
	// Should be an object
	var m map[string]interface{}
	if err := json.Unmarshal(data, &m); err != nil {
		t.Fatalf("expected JSON object, got: %s", string(data))
	}
	if m["text"] != "Login" {
		t.Errorf("expected text 'Login', got %v", m["text"])
	}
	if m["id"] != "btn" {
		t.Errorf("expected id 'btn', got %v", m["id"])
	}
}

func TestSelector_UnmarshalJSON_String(t *testing.T) {
	var s Selector
	if err := json.Unmarshal([]byte(`"Login"`), &s); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if s.Text != "Login" {
		t.Errorf("expected text 'Login', got %q", s.Text)
	}
}

func TestSelector_UnmarshalJSON_Object(t *testing.T) {
	var s Selector
	if err := json.Unmarshal([]byte(`{"text":"Login","id":"btn","enabled":true}`), &s); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if s.Text != "Login" {
		t.Errorf("expected text 'Login', got %q", s.Text)
	}
	if s.ID != "btn" {
		t.Errorf("expected id 'btn', got %q", s.ID)
	}
	if s.Enabled == nil || !*s.Enabled {
		t.Error("expected enabled=true")
	}
}

// --- JSON round-trip: step type is preserved ---

func TestStepType_JSONRoundTrip(t *testing.T) {
	input := `{"type":"tapOn","selector":"Login"}`
	step, err := UnmarshalStep([]byte(input))
	if err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	data, err := json.Marshal(step)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	var m map[string]interface{}
	if err := json.Unmarshal(data, &m); err != nil {
		t.Fatalf("re-unmarshal: %v", err)
	}
	if m["type"] != "tapOn" {
		t.Errorf("expected type 'tapOn' in JSON, got %v", m["type"])
	}
}
