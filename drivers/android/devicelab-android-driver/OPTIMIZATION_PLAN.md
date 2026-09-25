# DeviceLab Android Driver: Optimization Plan

Current benchmark: **27.8s avg** (6 flows, 51 steps) — **4.1x faster** than Maestro CLI (1m55s), **26% faster** than native UIAutomator2 (37.8s).

Device: Pixel 4a (API 33), serial: 11171JEC200939

---

## P0 — High Impact, Easy to Implement

| # | Optimization | Expected Impact | Status |
|---|-------------|----------------|--------|
| 1 | **Disable system animations** via `adb shell settings put global` (window_animation_scale, transition_animation_scale, animator_duration_scale = 0) | Eliminates 200-300ms animation waits per screen transition | Done |
| 2 | **Screenshot downscaling** — capture at 50% resolution (half width/height) | 4x fewer pixels = ~4x faster compress + transfer | Done |
| 3 | **Event-driven window waits** — use `setOnAccessibilityEventListener` to detect `TYPE_WINDOW_STATE_CHANGED` instead of polling | Caused regression (race condition: events fire before listener setup). Reverted to fast polling (10ms). | Reverted |
| 4 | **`performAction(ACTION_CLICK)`** on elements instead of coordinate injection | Single IPC vs 3 IPCs (getbounds + DOWN + UP events) | Done |
| 5 | **TCP_NODELAY on WebSocket** — disable Nagle's algorithm | Reduces ~40ms latency per small RPC message | Done |

## P1 — High Impact, Moderate Effort

| # | Optimization | Expected Impact | Status |
|---|-------------|----------------|--------|
| 6 | **WebP compression** for screenshots (API 30+, lossy quality 80) | ~30% smaller than JPEG at same quality | Pending |
| 7 | **Binary screenshot transfer** — send raw bytes via WebSocket binary frame instead of base64 | Eliminates 33% base64 overhead | Done |
| 8 | **Combined RPCs** — FindAndClick, SendKeysToActive in single WebSocket round-trip | Eliminates per-step RPC latency | Done |
| 9 | **Parallel screenshot** — take screenshot in background thread while processing next command | Overlaps I/O with computation | Pending |
| 10 | **Element store cleanup** — expire cached elements after TTL to prevent memory leaks | Reliability improvement | Pending |

## P2 — Medium Impact

| # | Optimization | Expected Impact | Status |
|---|-------------|----------------|--------|
| 11 | **Page source XML: use `XmlSerializer`** instead of StringBuilder concatenation | Faster, correct XML escaping, -2% | Done |
| 12 | **Skip invisible nodes** in tree traversal | Risks: breaks assertNotVisible, breaks relative selectors, isVisibleToUser() is itself an IPC call | Skip |
| 13 | **Pre-compiled regex patterns** for element matching | Already compiled once per search call, not per-element. Compile cost (~1-2μs) is 1000x less than tree IPC (~1ms) | Skip |
| 14 | **Accessibility node recycling** (`recycle()` calls) | Reduces GC pressure | Pending |
| 15 | **Connection keepalive/heartbeat tuning** | Prevents reconnection overhead | Pending |

## P3 — Low-Medium Impact

| # | Optimization | Expected Impact | Status |
|---|-------------|----------------|--------|
| 16 | **CPU governor pinning** — set performance governor during test runs | Prevents CPU throttling | Pending |
| 17 | **Process priority boosting** — set agent process to high priority | More CPU time for agent | Pending |
| 18 | **Custom IME for fast text input** — install lightweight keyboard | Faster sendKeys without character-by-character injection | Pending |
| 19 | **Partial tree queries** — limit tree depth for element finding | Less traversal for shallow elements | Pending |
| 20 | **Parallel element finding** — search multiple strategies concurrently | Reduces worst-case find time | Pending |

## P4 — Low Impact / Experimental

| # | Optimization | Expected Impact | Status |
|---|-------------|----------------|--------|
| 21 | **Display buffer direct access** — use SurfaceControl/PixelCopy APIs | Faster screenshots bypassing UiAutomation | Pending |
| 22 | **Warm element cache** — pre-fetch likely elements after navigation | Reduces find latency for next step | Pending |
| 23 | **Compression on WebSocket** — enable permessage-deflate | Smaller payloads for XML source | Pending |
| 24 | **Instrumentation thread pool** — handle multiple requests concurrently | Single client sequential RPC, UiAutomation not thread-safe, bottleneck is IPC not CPU | Skip |
| 25 | **Lazy XML attributes** — only include requested attributes in source | Smaller XML, faster parse | Pending |

## P5 — Future / Research

| # | Optimization | Expected Impact | Status |
|---|-------------|----------------|--------|
| 26 | **gRPC instead of WebSocket JSON-RPC** — binary protocol, code-gen | Lower serialization overhead | Pending |
| 27 | **Shared memory screenshot** — mmap between agent and host | Zero-copy screenshot transfer | Pending |
| 28 | **ADB forward instead of reverse** — reduce port forwarding overhead | Already using adb forward. Nothing to change. | N/A |
| 29 | **Custom accessibility service** — bypass UiAutomation limitations | Same underlying API, worse setup (requires manual enable), loses instrumentation powers | Skip |
| 30 | **Native code (JNI) for hot paths** — C/C++ for tree traversal | Bypass JVM overhead | Pending |
| 31 | **Multi-device test sharding** — split flows across devices | Linear speedup with device count | Pending |
| 32 | **Predictive pre-execution** — analyze flow ahead and pre-warm | Overlap wait time with next step prep | Pending |
| 33 | **App-side hooks** — inject test helper code into target app | Direct access to app state | Pending |
| 34 | **Snapshot/restore** — use emulator snapshots for instant app state reset | Eliminates clearState + relaunch overhead | Pending |

---

## Already Implemented (All Rounds)

- Prefetch flags for tree traversal (API 33+) — `FLAG_PREFETCH_DESCENDANTS_HYBRID | FLAG_PREFETCH_SIBLINGS`
- `syncInputTransactions` for gestures (API 31+) — via reflection
- JPEG 60 compression + 50% downscale for screenshots
- Binary WebSocket frame for screenshot transfer (no base64)
- Combined RPCs: `findAndClick`, `sendKeysToActive`
- XmlSerializer for page source (replaces StringBuilder + manual escaping)
- `performAction(ACTION_CLICK)` instead of coordinate injection
- TCP_NODELAY on WebSocket
- `waitForWindowReady` after app launch
- Reduced findElement retry sleep (200ms → 50ms)
- Reduced DOWN→UP sleep (50ms → 20ms on API <31)
- Disable system animations during test run
