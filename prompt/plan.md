# Implementation Plan: Maestro-Runner Remote Bindings

## Goal

Decouple the maestro-runner execution engine from YAML files by implementing a **REST Server (Go)** and a **Client binding (Python)**.

---

## Current Codebase Reality

> **Read this before writing a single line** — audit these facts so nothing is reinvented.

| Area | Fact |
|---|---|
| **CLI framework** | `github.com/urfave/cli/v2` (NOT Cobra). All commands live in `pkg/cli/`. There is no `cmd/` directory. New commands go in `pkg/cli/` following the patterns in `pkg/cli/android.go` and `pkg/cli/ios.go`. |
| **HTTP framework** | stdlib `net/http` only — no gin or gorilla/mux in `go.mod`. Do not add a new HTTP router framework unless there is a compelling reason; stdlib is sufficient. |
| **Step types** | All structs in `pkg/flow/step.go` have **only** `yaml:` struct tags. There are no `json:` tags anywhere. The `Selector` struct (`pkg/flow/selector.go`) also has only `yaml:` tags with a custom `UnmarshalYAML`. |
| **Driver interface** | `pkg/core/driver.go` defines the `core.Driver` interface and `core.CommandResult`. Every driver (`uiautomator2`, `wda`, `appium`, `devicelab`) implements this interface. The server must use it, never call driver internals directly. |
| **Driver initialization** | The full device discovery, ADB port-forwarding, emulator/simulator boot, and driver startup logic already lives in `pkg/cli/android.go` (Android) and `pkg/cli/ios.go` (iOS). The server command **MUST** reuse these helpers; do not duplicate them. |
| **Existing JSON-RPC** | `pkg/maestro/protocol.go` already defines a well-designed JSON protocol (used by the DeviceLab WebSocket driver). The pattern `Request{ID, Method, Params}` and `Response{ID, Result, Error}` is already proven. |
| **Python binding** | `client/python/` does not exist yet. Create it fresh. |
| **Server package** | `pkg/server/` does not exist yet. Create it fresh. |

---

## Phase 1: JSON Support for Step Types

**Target:** Allow step structs to be serialized/deserialized from JSON without breaking YAML parsing.

### Task 1.1 — Add `json:` tags to Step structs

- **Files:** `pkg/flow/step.go` and `pkg/flow/selector.go`
- **Action:** Add `json:` tags alongside the existing `yaml:` tags on every exported field. The `yaml:` tags must remain untouched — this is **purely additive**.

> **Key rule:** The type discriminator field must be exposed. `BaseStep.StepType` is currently `yaml:"-"`. Add `json:"type"` to it so the type round-trips through JSON.

**Before → After examples:**

```go
// BaseStep
StepType StepType `yaml:"-"`
// becomes:
StepType StepType `yaml:"-" json:"type"`

// TapOnStep field
LongPress bool `yaml:"longPress"`
// becomes:
LongPress bool `yaml:"longPress" json:"longPress,omitempty"`
```

The `Selector` struct also needs `json:` tags, plus a custom `MarshalJSON` / `UnmarshalJSON` that mirrors its existing scalar-or-mapping YAML behavior (plain string → `Text` field).

### Task 1.2 — Implement `UnmarshalStep(data []byte) (Step, error)`

- **File:** `pkg/flow/parser.go` or a new `pkg/flow/json.go`
- **Action:** Read the `"type"` field from the raw JSON, then switch on it — mirroring the existing `decodeStep` switch in `parser.go` — and unmarshal into the correct concrete struct (`TapOnStep`, `InputTextStep`, etc.).

> **Do NOT rewrite `decodeStep`.** It handles YAML. The new function handles JSON. They share the same `StepType` constants.

---

## Phase 2: The Server Package

**Target:** A self-contained HTTP server that bridges REST calls to the existing `core.Driver`.

### Task 2.1 — Create `pkg/server/server.go`

- Use stdlib `net/http` with a `ServeMux`. No external router needed.
- The server holds a `map[string]*sessionState` (protected by `sync.RWMutex`) where `sessionState` wraps a `core.Driver` and its initialization options.
- The `sessionId` is a UUID generated with `crypto/rand` (no external package needed).

**Session lifecycle** (mirrors how the existing CLI works):

| Method | Endpoint | Action |
|---|---|---|
| `POST` | `/session` | Run driver-init logic from `pkg/cli/android.go` or `pkg/cli/ios.go`; return `{"sessionId": "..."}` |
| `POST` | `/session/{id}/execute` | Call `UnmarshalStep` on body, then `driver.Execute(step)`, return `CommandResult` JSON |
| `GET` | `/session/{id}/screenshot` | Call `driver.Screenshot()`, return PNG bytes (`Content-Type: image/png`) |
| `GET` | `/session/{id}/source` | Call `driver.Hierarchy()`, return XML string |
| `GET` | `/session/{id}/device-info` | Call `driver.GetPlatformInfo()`, return `PlatformInfo` JSON |
| `DELETE` | `/session/{id}` | Call driver cleanup (same `defer` pattern used in the CLI test command) |

### Task 2.2 — Wire the server command into the CLI

- **File:** `pkg/cli/server.go` (new file, follow the style of `pkg/cli/test.go`)
- Register the command in `pkg/cli/cli.go` under `Commands` alongside `testCommand`.
- Reuse the same global flags that `test.go` uses (`--platform`, `--device`, `--driver`, `--appium-url`, `--caps`, `--no-ansi`, `--verbose`, etc.).
- Add only one new flag: `--port` (default `4723`).
- The command starts the HTTP server and blocks until `SIGINT`/`SIGTERM`, then gracefully shuts down all active sessions.

---

## Phase 3: Wire Protocol Specification

**Target:** A stable, documented contract for the REST API.

> **The Go server is the SINGLE SOURCE OF TRUTH for the API shape.**
> The Python client MUST adapt to match what the Go server exposes.
> Do NOT design the Python client first and then try to fit the Go server around it.

### Task 3.1 — OpenAPI spec

- **File:** `docs/openapi.yaml`
- All JSON shapes are derived directly from Go structs (`json:` tags defined in Phase 1, and the existing `core.CommandResult` / `core.PlatformInfo` / `core.StateSnapshot` in `pkg/core/driver.go` which already have `json:` tags). Nothing is invented.

---

#### `POST /session`

**Request body** — capabilities that mirror the existing CLI global flags:

```json
{
  "platformName": "android | ios",
  "deviceId":     "<udid or serial>",
  "appId":        "com.example.app",
  "driver":       "uiautomator2 | wda | appium | devicelab"
}
```

> `deviceId`, `appId`, and `driver` are optional — auto-detected if omitted.

**Response:**

```json
{ "sessionId": "<uuid>" }
```

---

#### `POST /session/{id}/execute`

Request body is a **single JSON step** using the type-discriminated format from Phase 1.
Selector fields are **flat** on the step object (matching `Selector`'s `json:` tags) — NOT wrapped in a `"selector"` key.

**Request examples:**

```jsonc
{ "type": "tapOn",           "text": "Login",              "timeout": 5000 }
{ "type": "tapOn",           "id": "btn_login",            "longPress": true }
{ "type": "tapOn",           "text": "OK",   "index": 1 }
{ "type": "inputText",       "text": "user@example.com" }           // focused element
{ "type": "assertVisible",   "text": "Dashboard",          "timeout": 10000 }
{ "type": "assertNotVisible","text": "Error" }
{ "type": "launchApp",       "appId": "com.example.app" }
{ "type": "stopApp",         "appId": "com.example.app" }
{ "type": "swipe",           "direction": "UP",            "duration": 400 }
{ "type": "scroll" }
{ "type": "pressKey",        "key": "ENTER" }
{ "type": "eraseText",       "charactersToErase": 5 }
// Add "optional": true to suppress failure on not-found
```

**Response** — `core.CommandResult` serialized directly (`json:` tags already present):

```jsonc
// Success
{
  "success":  true,
  "message":  "tapped element 'Login'",
  "duration": 312000000,        // nanoseconds (Go time.Duration)
  "element": {                  // core.ElementInfo, omitempty
    "id": "btn_login", "text": "Login",
    "bounds": { "x": 10, "y": 20, "width": 80, "height": 40 },
    "visible": true, "enabled": true
  }
}
// Failure
{ "success": false, "message": "element not found: text=Login" }
```

---

#### `GET /session/{id}/screenshot`

- **Response:** Raw PNG bytes
- **Content-Type:** `image/png`
- Calls `driver.Screenshot()` directly — no JSON wrapper.

---

#### `GET /session/{id}/source`

- **Response:** UI hierarchy bytes
- **Content-Type:** `application/xml` or `application/json` depending on driver
- Calls `driver.Hierarchy()` directly.

---

#### `GET /session/{id}/device-info`

**Response** — `core.PlatformInfo` serialized directly (`json:` tags already present):

```json
{
  "platform":    "android",
  "osVersion":   "14",
  "deviceName":  "Pixel 7",
  "deviceId":    "emulator-5554",
  "isSimulator": false,
  "screenWidth": 1080,
  "screenHeight":2400,
  "appId":       "com.example.app"
}
```

---

#### `DELETE /session/{id}`

- **Response:** `204 No Content`

---

## Phase 4: Python Client

**Target:** A thin client that adapts to the Go server endpoints defined in Phase 3.
The Go server is the source of truth.

### Task 4.1 — Create `client/python/maestro_runner/`

The existing `maestro_client/` was built for a different JVM-based Maestro bridge server.
Its public API (`MaestroClient`, `ElementSelector`, `ExecutionResult`, `CommandResult`, `DeviceInfo`, `tap_first_match`, `locator_logger`) is **good and should be kept**.
Only the **transport layer** needs to change to talk to the Go server.

#### Old JVM bridge vs. New Go server

| Old (`maestro_client/`) | New (`maestro_runner/`) |
|---|---|
| `POST /v1/execute` | `POST /session/{id}/execute` |
| `{"commands": [{"tapOnElement": {...}}]}` | Single step: `{"type": "tapOn", "text": "Login"}` |
| `GET /v1/device-info` | `GET /session/{id}/device-info` |
| `GET /v1/screenshot` | `GET /session/{id}/screenshot` |
| `GET /v1/view-hierarchy` | `GET /session/{id}/source` |
| No session concept | `POST /session` first, carry `sessionId` |
| `{"widthGrid": ..., "heightGrid": ...}` | `core.PlatformInfo` JSON (see Phase 3) |
| `ExecutionResult{success, results}` | `core.CommandResult` JSON (see Phase 3) |

#### File structure

```
client/python/
  maestro_runner/
    __init__.py        # exports MaestroClient (mirrors maestro_client's public API)
    client.py          # MaestroClient class
    commands.py        # command builder functions — produces Go step JSON
    models.py          # ElementSelector, ExecutionResult, DeviceInfo
    exceptions.py      # MaestroError
  tests/
    test_client.py
  pyproject.toml
  README.md
```

#### Command builder output shape

Builders MUST produce the Go step JSON. **Not** the old JVM envelope.

```python
# CORRECT — Go step JSON
tap_on_element(text="Login", long_press=True)
# → {"type": "tapOn", "text": "Login", "longPress": true, "optional": false}

# WRONG — old JVM envelope (do not use)
# → {"tapOnElement": {"selector": {"textRegex": "Login"}, "longPress": true}}
```

#### `DeviceInfo` field mapping — `core.PlatformInfo` (Go) → Python dataclass

| Go field | Python field |
|---|---|
| `platform` | `platform: str` |
| `osVersion` | `os_version: str` |
| `deviceName` | `device_name: str` |
| `screenWidth` | `screen_width: int` |
| `screenHeight` | `screen_height: int` |
| `isSimulator` | `is_simulator: bool` |
| `deviceId` | `device_id: str` |

#### `ExecutionResult` field mapping — `core.CommandResult` (Go) → Python dataclass

| Go field | Python field |
|---|---|
| `success` | `success: bool` |
| `message` | `message: str \| None` |
| `duration` | `duration_ns: int` (nanoseconds) |
| `element` | `element: ElementInfo \| None` |

#### `MaestroClient` class signature

```python
class MaestroClient:
    def __init__(
        self,
        base_url: str = "http://localhost:9999",
        capabilities: dict | None = None,
        timeout: float = 60.0,
    ) -> None:
        ...
    # capabilities passed to POST /session; session_id stored internally
```

#### Method signatures

**App lifecycle**

```python
launch_app(app_id: str, *, clear_state: bool | None = None,
           stop_app: bool | None = None, label: str | None = None) -> ExecutionResult
stop_app(app_id: str, *, label: str | None = None) -> ExecutionResult
clear_state(app_id: str, *, label: str | None = None) -> ExecutionResult
open_link(link: str, *, label: str | None = None) -> ExecutionResult
```

**Tap** — all selector fields are keyword-only

```python
tap(*, text: str | None = None, id: str | None = None, index: int | None = None,
    selector: ElementSelector | None = None, long_press: bool = False,
    wait_until_visible: bool | None = None, retry_if_no_change: bool | None = None,
    enabled: bool | None = None, checked: bool | None = None,
    focused: bool | None = None, selected: bool | None = None,
    optional: bool = False, label: str | None = None) -> ExecutionResult

long_press(*, text: str | None = None, id: str | None = None,
           selector: ElementSelector | None = None, label: str | None = None) -> ExecutionResult

tap_on_point(point: str, *, long_press: bool = False, label: str | None = None) -> ExecutionResult
```

**Input** — `input_text` with no selector targets the currently focused element

```python
input_text(text: str, *, label: str | None = None) -> ExecutionResult
erase_text(characters: int | None = None, *, label: str | None = None) -> ExecutionResult
press_key(code: str, *, label: str | None = None) -> ExecutionResult
back(*, label: str | None = None) -> ExecutionResult
```

**Scroll / swipe**

```python
scroll(*, label: str | None = None) -> ExecutionResult
swipe(direction: str, *, duration_ms: int = 400, label: str | None = None) -> ExecutionResult
swipe_on(*, text: str | None = None, id: str | None = None, direction: str = "UP",
         duration_ms: int = 400, label: str | None = None) -> ExecutionResult
```

**Assertions**

```python
assert_visible(*, text: str | None = None, id: str | None = None,
               selector: ElementSelector | None = None,
               timeout_ms: int | None = None, label: str | None = None) -> ExecutionResult

assert_not_visible(*, text: str | None = None, id: str | None = None,
                   selector: ElementSelector | None = None,
                   timeout_ms: int | None = None, label: str | None = None) -> ExecutionResult

element_exists(*, text: str | None = None, id: str | None = None) -> bool
# Posts {"type":"assertVisible","text":"...","optional":true}
# Returns True if success==true, False otherwise — never raises
```

**Self-healing multi-selector tap** (keep from `maestro_client`)

```python
tap_first_match(selectors: list[dict], *, step: str = "") -> ExecutionResult
```

**Device queries**

```python
device_info() -> DeviceInfo      # GET /session/{id}/device-info
screenshot() -> bytes            # GET /session/{id}/screenshot → raw PNG
view_hierarchy() -> str          # GET /session/{id}/source → XML/JSON string
```

**Low-level escape hatch**

```python
execute_step(step: dict) -> ExecutionResult
# POST /session/{id}/execute with a raw step dict
```

---

## Phase 5: Integration & Testing

**Target:** Prove the end-to-end flow works without YAML.

### Task 5.1 — End-to-end test script

- **File:** `client/python/tests/test_e2e.py`
- Use `pytest`. Start `maestro-runner server` in a subprocess fixture (`subprocess.Popen`), wait for `/status` to be healthy, run test flow, teardown server.

**Example test flow (login with conditional logic):**

```python
c = MaestroClient(
    "http://localhost:9999",
    capabilities={"platformName": "android", "appId": "com.example.app"},
)
c.launch_app("com.example.app")
if c.element_exists(text="Accept"):
    c.tap(text="Accept")
c.tap(text="Username")
c.input_text("testuser@example.com")
c.tap(text="Password")
c.input_text("s3cret")
c.tap(text="Login")
c.assert_visible(text="Dashboard", timeout_ms=10000)
info = c.device_info()   # DeviceInfo from core.PlatformInfo
shot = c.screenshot()    # raw PNG bytes from GET /session/{id}/screenshot
```

---

## Summary Checklist

### Go — source of truth, implement first

- [ ] Add `json:` tags (additive, do **not** remove `yaml:` tags) to all Step structs and `Selector` in `pkg/flow/`.
- [ ] Add `json:"type"` to `BaseStep.StepType` so the discriminator round-trips through JSON.
- [ ] Implement `UnmarshalStep(data []byte) (Step, error)` in `pkg/flow/` mirroring the existing `decodeStep` switch.
- [ ] Implement `Selector` `MarshalJSON`/`UnmarshalJSON` to mirror the existing scalar-or-mapping YAML behavior.
- [ ] Create `pkg/server/server.go` using stdlib `net/http` with these endpoints:
  - `POST   /session`
  - `POST   /session/{id}/execute`
  - `GET    /session/{id}/screenshot`
  - `GET    /session/{id}/source`
  - `GET    /session/{id}/device-info`
  - `DELETE /session/{id}`
- [ ] Reuse driver initialization helpers from `pkg/cli/android.go` and `pkg/cli/ios.go` in `POST /session`.
- [ ] Create `pkg/cli/server.go` using `urfave/cli/v2` (NOT Cobra) following the style of `pkg/cli/test.go`.
- [ ] Register the server command in `pkg/cli/cli.go` alongside `testCommand`.

### Docs — derived from Go implementation

- [ ] Create `docs/openapi.yaml` with the wire protocol spec — shapes taken from Go structs, not invented.

### Python — adapts to Go server, implement after Go endpoints are defined

- [ ] Create `client/python/maestro_runner/` package (new, alongside but separate from `maestro_client/`).
- [ ] Command builders in `commands.py` MUST produce Go step JSON (`{"type":"tapOn",...}`), **not** the old JVM envelope (`{"tapOnElement":{...}}`).
- [ ] `DeviceInfo` dataclass fields map to `core.PlatformInfo` JSON keys (`platform`, `osVersion`, `deviceName`, `screenWidth`, `screenHeight`, `isSimulator`, `deviceId`).
- [ ] `ExecutionResult` maps `core.CommandResult` JSON keys (`success`, `message`, `duration`, `element`).
- [ ] `MaestroClient.__init__` calls `POST /session` with capabilities dict; stores `session_id`.
- [ ] All session-scoped endpoints must include the `session_id` in the URL path.
- [ ] Implement context-manager support (`__enter__`/`__exit__`) for automatic `DELETE /session/{id}`.
- [ ] Keep `tap_first_match` + `locator_logger` from `maestro_client` (they are transport-agnostic).
- [ ] Write pytest-based tests in `client/python/tests/`.