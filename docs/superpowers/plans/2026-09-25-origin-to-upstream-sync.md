# Origin-to-Upstream Feature Sync Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the product features and validation improvements that exist in `origin/main` into the canonical `upstream/main` repository, one way only.

**Architecture:** Treat `origin/main` as the source-of-truth feature branch and `upstream/main` as the target integration branch. Port behavior and tests as small reviewable changes, reconciling each port against the current upstream implementation rather than copying whole directories or replaying unrelated merge history.

**Tech Stack:** Go 1.26 module, standard `net/http`, YAML/JSON flow models, Python 3.11, TypeScript/Node 24, Jest, pytest/pytest-xdist, GitHub Actions, Android Gradle fixtures, UIAutomator2/DeviceLab/Appium drivers.

**Spec:** This document is the audit and implementation spec for the origin-to-upstream sync. Audit refs: `origin/main` = `4171fc3`, `upstream/main` = `09a05b5`.

## Global Constraints

- Port only from `origin/main` to `upstream/main`; do not plan or perform an upstream-to-origin merge.
- Start every implementation branch from the current `upstream/main`, not from `origin/main`.
- Preserve current upstream behavior where it is already equal or newer; port only the documented delta.
- Do not copy generated files: `.gradle/`, `build/`, APKs, reports, local logs, `.playwright-mcp/`, or test output.
- Do not copy the legacy `drivers/ios/DeviceLabDriver` project over upstream's `drivers/ios/DevicelabIOSRunner`; reconcile the two protocols and build layouts first.
- Keep the REST API route and JSON field names compatible with the origin implementation unless a deliberate compatibility decision is documented.
- Add tests in the same change as behavior; each feature must be independently testable.
- No migration is required for existing YAML flows. New JSON/client APIs are additive.

## Audit Summary

The origin-only history contains a coherent programmatic-automation layer, two reliability improvements, a reusable animation test fixture, a multi-driver Android E2E workflow, and CI/test-orchestration improvements. The highest-value work is the REST/client stack because upstream has no `pkg/server` package and no `client/python` or `client/typescript` tree. Reliability and CI work should follow so the new APIs are exercised against the real driver surface.

The following are explicitly not in the propagation list because they are already present in upstream or are not product features: upstream-only/current-upstream capabilities such as CommonJS `require` in `runScript`, the plain `wait` step, remote `--app-file`, current WDA/device fixes, and current npm packaging; generated artifacts; repository-local skills; historical CI run IDs; and the duplicate legacy iOS driver project.

## Feature Priority Table

| Priority | Title | Short description | Why it matters | Effort | Dependencies |
|---|---|---|---|---|---|
| P0 | Session-based REST API and JSON step protocol | Add a long-lived HTTP server with session creation, step execution, screenshots, hierarchy, device info, deletion, and graceful shutdown. Decode typed JSON steps through the flow model. | Enables programmatic and language-client automation without generating YAML or embedding the runner in a host process. | M | None |
| P0 | Python REST client | Ship a typed Python package wrapping sessions, steps, results, device queries, and common gestures/device controls. | Gives pytest users a maintainable, typed interface and enables page-object-style suites. | M | REST API/JSON protocol |
| P0 | TypeScript REST client | Ship the equivalent typed Node/TypeScript client, command builders, models, and raw-step escape hatch. | Enables Jest/Vitest/Playwright users to reuse the runner with IDE completion and type checking. | M | REST API/JSON protocol |
| P1 | Android keyboard-state and `hideKeyboard` strategy support | Make keyboard detection robust across Android/vendor formats; add `isKeyboardVisible` and configurable `hideKeyboard` strategies with verification. | Prevents coordinate taps from landing on a keyboard and avoids silently reporting dismissal that did not happen. | M | Flow model/parser; UIAutomator2 driver |
| P1 | Cross-driver configurable `waitForAnimationToEnd` | Centralize screenshot settling, honor `sleepMs`/`threshold`/`timeout`, and fail when the screen never stabilizes. | Makes animation waits deterministic and consistent across UIAutomator2, DeviceLab, WDA, and Appium instead of allowing false positives. | M | Core image comparison; four drivers |
| P1 | Stoppable Android animation fixture and coverage | Add a source-buildable animation app with Start/Stop controls plus strict Python, TypeScript, and YAML tests for never-ending and halted animation states. | Provides deterministic E2E coverage for timeout and success paths instead of relying on an uncontrollable spinner. | M | Animation settling; Android E2E harness |
| P1 | Multi-driver Android E2E workflow | Add an Android API 36/Pixel 6 workflow covering UIAutomator2, DeviceLab, and Appium, with YAML and client suites, artifacts, and path filters. | Validates the supported driver matrix and prevents driver-specific regressions from reaching upstream. | M | Stoppable fixture; client test harness |
| P1 | Go test sharding and CDP parallelization | Replace the monolithic Go CI job with static shards, isolate the browser/CDP package, and run independent CDP tests in parallel. | Reduces CI wall-clock time while retaining race detection and coverage for the fast shards. | M | Upstream CI workflow |
| P1 | Client test isolation, worker support, and documentation | Separate unit/device tests, add per-worker server/device assignment, artifact summaries, and document local/CI execution. | Prevents unit jobs from requiring devices and makes multi-device debugging and CI artifacts reliable. | M | Python/TypeScript clients; E2E workflow |

## Implementation Sequence

1. Land the REST API and JSON step protocol first, including contract tests.
2. Land Python and TypeScript clients against the same contract; add typed bindings and raw-step escape hatches.
3. Land keyboard and animation reliability changes with driver-level tests.
4. Land the source-buildable animation fixture, then the Android E2E matrix.
5. Land CI sharding/CDP parallelization and client test isolation/documentation after the new packages and workflows exist.
6. Run cross-cutting validation across Go, Python, TypeScript, and the selected E2E drivers before proposing upstream release integration.

## Issue Tracking

GitHub Issues are enabled for the `origin` repository `pr4bh4sh/maestro-runner`, and one tracking issue has been created per feature. Each issue links to this plan and remains scoped to one feature below. Do not create these issues in `upstream`; the target repository is `pr4bh4sh/maestro-runner`.

| Feature | Intended issue title | Status | Issue |
|---|---|---|---|
| 1 | `[upstream-sync] Session-Based REST API and JSON Step Protocol` | Open | [#2](https://github.com/pr4bh4sh/maestro-runner/issues/2) |
| 2 | `[upstream-sync] Python REST Client` | Open | [#3](https://github.com/pr4bh4sh/maestro-runner/issues/3) |
| 3 | `[upstream-sync] TypeScript REST Client` | Open | [#4](https://github.com/pr4bh4sh/maestro-runner/issues/4) |
| 4 | `[upstream-sync] Android Keyboard-State and \`hideKeyboard\` Strategy Support` | Open | [#5](https://github.com/pr4bh4sh/maestro-runner/issues/5) |
| 5 | `[upstream-sync] Cross-Driver Configurable \`waitForAnimationToEnd\`` | Open | [#6](https://github.com/pr4bh4sh/maestro-runner/issues/6) |
| 6 | `[upstream-sync] Stoppable Android Animation Fixture and Coverage` | Open | [#7](https://github.com/pr4bh4sh/maestro-runner/issues/7) |
| 7 | `[upstream-sync] Multi-driver Android E2E Workflow` | Open | [#8](https://github.com/pr4bh4sh/maestro-runner/issues/8) |
| 8 | `[upstream-sync] Go Test Sharding and CDP Parallelization` | Open | [#9](https://github.com/pr4bh4sh/maestro-runner/issues/9) |
| 9 | `[upstream-sync] Client Test Isolation, Worker Support, and Documentation` | Open | [#10](https://github.com/pr4bh4sh/maestro-runner/issues/10) |

Each issue body contains the corresponding Feature Spec section as the implementation source of truth.

## Feature Spec 1: Session-Based REST API and JSON Step Protocol

### Goal and scope

Provide `maestro-runner server`, a session-oriented HTTP API that accepts JSON-encoded flow steps and delegates them to the existing `core.Driver` abstraction. The server is the programmatic entry point for the clients; YAML execution remains unchanged.

### Current behaviour in upstream

`upstream/main` has no `pkg/server` package, no `pkg/flow/json.go`, and no `server` CLI command. Clients cannot create a driver session or execute a typed step over HTTP.

### Desired behaviour

Starting `maestro-runner server [--port 9999]` exposes:

- `GET /status` with `{"status":"ok","sessions":N}`.
- `POST /session` accepting `platformName`, optional `deviceId`, `appId`, and `driver`, returning `{"sessionId":"..."}`.
- `POST /session/{id}/execute` accepting a JSON step with a `type` discriminator and returning the driver's JSON result.
- `GET /session/{id}/screenshot` returning PNG bytes.
- `GET /session/{id}/source` returning XML or JSON according to the hierarchy content.
- `GET /session/{id}/device-info` returning platform information.
- `DELETE /session/{id}` cleaning up the driver and returning 204.

The server must be safe for concurrent session-map access, clean up all sessions on SIGINT/SIGTERM, and emit worker-aware trace lines without logging credentials or request bodies containing secrets.

JSON decoding must preserve the same concrete `flow.Step` types and selector semantics as YAML. Selectors must accept either a text-only string or an object. Unsupported/malformed step types must return a clear 400 response rather than panic.

### Required code changes

- Add `pkg/server/server.go` with `Server`, `SessionState`, `SessionRequest`, `SessionResponse`, `ErrorResponse`, `New`, `Handler`, `ShutdownAll`, and route handlers.
- Add `pkg/server/server_test.go` covering status, create, execute, screenshot, source content type, device info, delete, invalid JSON, missing platform, missing session, and cleanup.
- Add `pkg/flow/json.go` with `UnmarshalStep`, type dispatch, `Selector.MarshalJSON`, and `Selector.UnmarshalJSON`; add `pkg/flow/json_test.go` for every supported step type and selector shape.
- Add `pkg/cli/server.go`; register it in `pkg/cli/cli.go`; construct drivers through the existing Android/iOS factory functions and inherit relevant global flags.
- Add JSON tags to step/selector fields required by the protocol, without changing YAML decoding.
- Make the server trace helper worker-aware using `PYTEST_XDIST_WORKER` and `MAESTRO_WORKER_ID`, and redact or bound sensitive payloads before logging.

### Configuration / migration / data changes

- `MAESTRO_SERVER_PORT` maps to the default `--port`.
- No persistent data migration is required.
- Server sessions are in-memory and are lost on restart; document that clients must create a new session after reconnecting.

### Testing strategy

- Unit: `go test ./pkg/server ./pkg/flow` with an injected mock driver and table-driven JSON step cases.
- Integration: start the CLI server, create a session, execute one harmless command through a real Android/iOS-capable driver, then delete the session and assert cleanup.
- Manual: exercise `curl` examples for every endpoint and verify graceful shutdown closes active drivers.

### Rollout plan

Land as an additive CLI/API feature with no feature flag. Publish the API contract in the server and client documentation, then release the clients after the server endpoint set is stable. Do not advertise typed client parity for a step until the server accepts and executes that step.

### Acceptance criteria

- `maestro-runner server` starts and prints the expected endpoint list.
- All seven routes have automated success and failure coverage.
- A JSON step is decoded into the same `flow.Step` implementation used by YAML and reaches the injected driver unchanged.
- Text-only and structured selectors round-trip through JSON.
- Concurrent create/delete/status requests do not race or corrupt the session map.
- Shutdown invokes cleanup for every active session.
- No test or CI job requires upstream-to-origin synchronization.

## Feature Spec 2: Python REST Client

### Goal and scope

Publish a supported Python package under `client/python` that wraps the REST API for pytest and Python automation users. It must cover session lifecycle, typed results, common flow steps, device queries, and an escape hatch for future server steps.

### Current behaviour in upstream

`upstream/main` has no `client/python` package or Python client tests. Users must call the HTTP API manually or generate YAML.

### Desired behaviour

`MaestroClient` supports context-manager use, explicit session creation/close, raw `execute_step`, and typed helpers for the origin-supported step families: app lifecycle, selectors/actions, text input, scrolling/gestures, assertions, screenshots, permissions, scripting, device controls, and browser/WebView controls. `commands.py` is the single JSON command-builder layer, while `models.py` converts server responses into typed Python objects. Failed non-optional steps raise `StepError`; optional failures return an `ExecutionResult`.

Parallel pytest fixtures start one server per worker, assign a distinct device/port, create per-worker output directories, and attach failure log tails and artifact summaries.

### Required code changes

- Add `client/python/pyproject.toml`, package metadata, dependency declarations, and development tooling.
- Add `client/python/maestro_runner/models.py`, `exceptions.py`, `commands.py`, `client.py`, and `__init__.py`.
- Port the origin typed methods and the expanded gesture/media/device/browser/WebView bindings from commit `9448fa1`.
- Add `client/python/tests/conftest.py` with server startup, device discovery, xdist worker isolation, cleanup, and artifact reporting.
- Add unit tests for models and command serialization; add device tests separately from unit tests.
- Add `client/python/README.md` and `DEVELOPER.md` with installation, server prerequisite, worker variables, and test commands.

### Configuration / migration / data changes

- `MAESTRO_SERVER_URL`, `MAESTRO_PLATFORM`, `MAESTRO_RUNNER_BIN`, and `MAESTRO_DEVICE_ID` are supported.
- `pytest-xdist` is an optional development/test dependency, not a runtime requirement.
- No user data migration; sessions remain external to the Python process.

### Testing strategy

- Unit: mocked HTTP tests for all command builders, response parsing, error mapping, optional failures, and context-manager cleanup.
- Integration: one real server/driver session per Android or iOS device; run a contact flow and animation wait flow.
- Parallel: run two workers against two devices and assert distinct ports, device serials, and output directories.

### Rollout plan

Ship after Feature 1. Release the Python package as a development/client artifact first; no runner feature flag is needed. Publish examples and API reference before advertising it as stable.

### Acceptance criteria

- The package installs from a clean checkout and passes lint/type/unit checks.
- Every public client method emits a valid JSON step accepted by the server.
- A failed non-optional command raises `StepError`; optional commands do not.
- `close()` and context-manager exit are idempotent and do not mask test failures.
- Two xdist workers can run against separate devices without port or server-session collisions.

## Feature Spec 3: TypeScript REST Client

### Goal and scope

Publish an equivalent typed client under `client/typescript` for Node.js, Jest, Vitest, and Playwright projects. It must have the same session and command coverage as the Python client while following the repository's TypeScript conventions.

### Current behaviour in upstream

`upstream/main` has no TypeScript client package, command builders, models, or unit/device test split.

### Desired behaviour

`MaestroClient` supports `createSession`, `close`, `executeStep`, typed command helpers, device queries, and typed models. Text-only selectors serialize as strings; structured selectors serialize as objects. A raw `executeStep` method remains available for step types not yet wrapped by a typed method.

The test suite separates `*.unit.test.ts` from `*.device.test.ts`. Unit tests run in parallel without devices. Device tests derive an isolated server port and device assignment from `JEST_WORKER_ID`, and run serially by default for a single device.

### Required code changes

- Add `client/typescript/package.json`, lockfile, `tsconfig.json`, test TypeScript configuration, ESLint configuration, and Jest configuration.
- Add `client/typescript/src/models.ts`, `exceptions.ts`, `commands.ts`, `client.ts`, and `index.ts`.
- Port the expanded typed bindings from commit `9448fa1`; keep command construction separate from transport.
- Add `client/typescript/tests/setup.ts` for server/device lifecycle, worker identity, logs, and artifacts.
- Add unit tests for models, JSON command shapes, HTTP errors, and session cleanup.
- Add device tests under the `.device.test.ts` naming convention; retain `test:unit`, `test:device:android`, and `test:device:ios` scripts.
- Add `client/typescript/README.md` and `DEVELOPER.md` with server setup, worker variables, and test commands.

### Configuration / migration / data changes

- `MAESTRO_SERVER_URL`, `MAESTRO_PLATFORM`, `MAESTRO_RUNNER_BIN`, and `MAESTRO_DEVICE_ID` are supported.
- Node 24 and the lockfile become the reproducible client toolchain.
- No user data migration.

### Testing strategy

- Unit: `npm ci && npm run test:unit` and `npm run lint` with no device or server.
- Integration: use a real server for one Android and one iOS device suite.
- Manual: verify a public package import and a raw `executeStep` call against the documented server contract.

### Rollout plan

Ship after Features 1 and 2 so both clients reveal protocol omissions. Add the package to documentation and release notes after TypeScript unit/device suites pass in CI.

### Acceptance criteria

- TypeScript unit tests run without a running server or attached device.
- Device tests cannot be selected by the unit-test command.
- Public command helpers produce the same JSON payloads as the Python command builders.
- Workers receive isolated ports/devices and clean up sessions/log streams.
- TypeScript compilation, lint, unit, and selected device suites pass under Node 24.

## Feature Spec 4: Android Keyboard-State and `hideKeyboard` Strategy Support

### Goal and scope

Make Android keyboard detection and dismissal observable and configurable. The change is focused on UIAutomator2 and the flow model; other drivers retain their existing platform-specific behavior unless the same step model is shared.

### Current behaviour in upstream

Upstream has a basic `hideKeyboard` implementation without a strategy field, and its Android keyboard parsing is weaker across Android versions and vendor keyboards. It lacks the origin `isKeyboardVisible` step.

### Desired behaviour

- Parse `mInputShown`, `isOnScreen`, visibility, touchable-region, content-inset, and frame forms from Android `dumpsys` output.
- Return no visible bounds for dismissed/full-screen/non-keyboard frames.
- `hideKeyboard` accepts `strategy: appium|escape|esc|back`; an empty strategy tries Appium, ESCAPE, then BACK, verifying after each attempt.
- Never send BACK when the keyboard is not visible; reject unknown strategies with a clear error.
- Expose `isKeyboardVisible` as a flow step returning a command result that reflects the detected state.

### Required code changes

- Update `pkg/flow/step.go` and `pkg/flow/parser.go` for the `strategy` field and `StepIsKeyboardVisible`.
- Update `pkg/driver/uiautomator2/keyboard.go` with the origin parser strategy and canonical `isInputShown` check.
- Update `pkg/driver/uiautomator2/commands.go` with verified strategy handlers.
- Update the shared JSON decoder/selector tags as needed.
- Add parser tests for every dumpsys form and driver tests for each strategy, fallback order, dismissed keyboard, unknown strategy, and `isKeyboardVisible`.

### Configuration / migration / data changes

- No persistent configuration or migration.
- `strategy` is optional and preserves the origin default ordered fallback.
- Existing flows without `strategy` continue to work.

### Testing strategy

- Unit: table-driven parser tests using captured Android/vendor `dumpsys` strings and fake device-shell responses.
- Driver: verify each strategy and fallback order without actually dismissing a keyboard.
- Manual/device: test on at least one stock Android emulator and one vendor-like keyboard/focus scenario; assert a following coordinate tap does not hit the keyboard overlay.

### Rollout plan

Ship as a compatible enhancement with no feature flag. Document valid strategy values and the fact that verification is best-effort when the device shell cannot inspect the IME.

### Acceptance criteria

- Valid strategy values execute only the selected strategy.
- Empty strategy uses the documented fallback order.
- Unknown strategy fails with the list of accepted values.
- Dismissed keyboards do not trigger BACK/navigation.
- Keyboard visibility is false for dismissed, hidden, and full-screen false positives.
- Existing `hideKeyboard` flows pass.

## Feature Spec 5: Cross-Driver Configurable `waitForAnimationToEnd`

### Goal and scope

Provide one screenshot-settling implementation for UIAutomator2, DeviceLab Android, WDA, and Appium. The step must be testable without a device and must return a failed result when the screen does not settle.

### Current behaviour in upstream

Upstream implementations differ: Appium is not fully implemented, other drivers use hard-coded thresholds/timing, capture failures may fail immediately, and a timeout can return success. Origin adds a shared `WaitForScreenStatic` helper and configurable `sleepMs`/`threshold` handling.

### Desired behaviour

For each driver, `waitForAnimationToEnd` must:

- Default to a 15,000 ms timeout, 200 ms inter-screenshot delay, 0.5% threshold, and 100 ms retry interval.
- Take two screenshots separated by `sleepMs`, compare using the shared image difference, and retry until the threshold is met or the deadline expires.
- Treat screenshot capture errors as transient and retry within the timeout.
- Return success with elapsed/iteration diagnostics when stable.
- Return failure with timeout and diagnostic differences when never stable.
- Use flow-level `sleepMs`, `threshold`, and `timeout` values when supplied.

### Required code changes

- Add `WaitForScreenStatic` and `AnimationSettleResult` to `pkg/core/imagediff.go`.
- Add the `SleepMs` and `Threshold` fields to `WaitForAnimationToEndStep` in `pkg/flow/step.go` and YAML/JSON parsing.
- Update `pkg/driver/uiautomator2/commands.go`, `pkg/driver/devicelab/commands.go`, `pkg/driver/wda/commands.go`, and `pkg/driver/appium/commands.go` to call the helper.
- Add core tests for identical frames, changing frames, threshold boundaries, capture errors, and timeout.
- Add driver tests with scripted screenshot sequences proving success, failure, and per-driver defaults.

### Configuration / migration / data changes

- Defaults preserve the origin behavior; custom values are per-step and require no migration.
- `optional: true` must continue to allow the flow to proceed after a failed wait, matching the existing flow semantics.

### Testing strategy

- Unit: deterministic fake screenshot callbacks and short injected durations.
- Driver: mock clients that return stable, changing, and error-producing screenshot sequences.
- E2E: run the stoppable animation fixture through all three Android drivers in the E2E matrix.

### Rollout plan

Ship with a compatibility note: unlike the old soft-timeout behavior, a non-optional wait now fails when animation never ends. Treat this as a deliberate behavior correction and document it in the changelog.

### Acceptance criteria

- All four drivers use the same settling algorithm and defaults.
- A stable screen passes within the configured timeout.
- A permanently changing screen fails for a non-optional step.
- Screenshot errors do not produce false success and do not panic.
- Diagnostic output includes timeout, threshold, and comparison values.
- The stoppable animation E2E passes across the supported Android drivers.

## Feature Spec 6: Stoppable Android Animation Fixture and Coverage

### Goal and scope

Add a source-buildable Android test application and deterministic flow coverage for both a never-ending spinner and a spinner that is stopped by a user action. This is test infrastructure, not a shipped application.

### Current behaviour in upstream

`upstream/main` has no animation test app, no stop/start control, and no YAML/Python/TypeScript animation flows. Animation behavior cannot be tested without relying on an uncontrollable external app or a prebuilt binary.

### Desired behaviour

The fixture renders a canvas animation and exposes stable `Start` and `Stop` controls. Tests verify that the animation times out while running and becomes static after Stop. The fixture must build from a clean checkout.

### Required code changes

- Add `e2e/android-animation-app/` Gradle project, wrapper, manifest, Java activity, layout, strings, and `.gitignore`.
- Add the Stop/Start interval controls to `MainActivity.java` and `activity_main.xml`.
- Add `e2e/workspaces/animation/wait_for_animation_android.yaml` and `wait_for_animation_stops_on_click_android.yaml`.
- Add Python tests for never-ending, ended, and stop-on-click behavior.
- Add TypeScript device tests for the same three cases.
- Add a CI build step that uploads/copies the APK to the exact path consumed by the E2E job; do not depend on a tracked APK or an unrelated build job.

### Configuration / migration / data changes

- No runtime configuration or migration.
- CI needs JDK 17, Android SDK platform 36/build tools 36.0.0, and Gradle wrapper execution.
- The E2E job must build the fixture or consume an artifact with an explicit path contract.

### Testing strategy

- Build: run `./gradlew :app:assembleDebug` from a clean checkout.
- YAML: run the continuous flow with the expected optional/best-effort behavior and the stop flow with a success assertion.
- Python/TypeScript: strict positive/negative timeout tests; these provide the exact expected failure that YAML cannot express.
- Manual: launch the fixture, tap Stop, and confirm the frame stops changing.

### Rollout plan

Add the source and test jobs together. Do not publish the APK as a source artifact; if a binary is needed for release testing, generate it in CI and document the checksum/artifact name.

### Acceptance criteria

- A clean checkout builds the APK without tracked generated files.
- The continuous animation test times out for a non-optional wait.
- The stop-on-click test passes after tapping Stop.
- All three drivers in the Android E2E matrix run the coverage.
- CI fails if the APK build, install path, or artifact handoff is broken.

## Feature Spec 7: Multi-Driver Android E2E Workflow

### Goal and scope

Add a separate Android E2E GitHub Actions workflow for API 36/Pixel 6 and the supported driver matrix: UIAutomator2, DeviceLab, and Appium. The workflow runs YAML, Python, and TypeScript suites and publishes useful artifacts.

### Current behaviour in upstream

Upstream CI has no Android E2E job. Driver-specific regressions and Appium compatibility are not continuously exercised.

### Desired behaviour

- Path filters trigger the job for Go/client/E2E/Android/workflow changes.
- Emulator setup is repeated per matrix leg.
- Appium is installed and started only for the Appium leg.
- Driver APKs are installed only where required.
- YAML, Python, and TypeScript tests run against the same emulator and driver.
- JUnit/CTRF/artifact upload identifies the driver, device, worker, and failure artifacts.
- Job cancellation is enabled for superseded commits.

### Required code changes

- Add `.github/workflows/e2e-android.yml` based on the origin workflow, with the APK handoff corrected.
- Reuse the client setup/fixture rather than duplicating server startup logic in the workflow.
- Keep the driver matrix in one place and pass it through environment variables.
- Add a workflow-level check that fails if the matrix is accidentally reduced or if a driver is run without its required server/artifact.

### Configuration / migration / data changes

- GitHub Actions secrets/tokens remain unchanged unless artifact publication requires a new permission.
- Android SDK/JDK versions must be documented and pinned.
- No user data migration.

### Testing strategy

- Static: actionlint/workflow syntax and YAML validation.
- CI: run a manual dispatch on one branch for each matrix leg; first validate UIAutomator2, then DeviceLab, then Appium.
- Local: run the same script with `MAESTRO_DRIVER` and a local emulator.

### Rollout plan

Add the workflow disabled-by-default only if upstream CI cost is a concern; otherwise enable on pull requests and main. Start with API 36/Pixel 6, then expand to additional API/device profiles after two stable weeks.

### Acceptance criteria

- All three driver legs appear in GitHub Actions and are independently selectable.
- A YAML, Python, and TypeScript failure produces driver-specific JUnit/artifact output.
- Appium is not started for non-Appium legs.
- The animation fixture is built from source in the workflow and installed from a known path.
- Unrelated documentation-only changes do not start emulator jobs.

## Feature Spec 8: Go Test Sharding and CDP Parallelization

### Goal and scope

Reduce upstream Go CI wall-clock time without dropping race detection or coverage for the fast packages. Isolate the slow browser/CDP package and parallelize independent CDP tests.

### Current behaviour in upstream

Upstream runs a monolithic `go test -race ... ./...` job. The CDP browser package is not given a dedicated bounded-parallelism shard.

### Desired behaviour

- Use static matrix shards: `cdp`, `s1`, `s2`, and `s3`.
- Keep `-race` on s1–s3; run CDP with bounded `-parallel 4` and no race flag unless a later benchmark proves it safe.
- Include the new `pkg/server` package in the correct shard.
- Upload per-shard coverage.
- Make package assignment complete and reviewable so adding a package cannot silently omit tests.

### Required code changes

- Update `.github/workflows/ci.yml` with the matrix and conditional race expression from the origin workflow.
- Update `pkg/driver/browser/cdp/driver_test.go` so independent tests call `t.Parallel()` only where shared setup is safe.
- Add a CI validation step that compares the static package list with `go list ./...` and fails on missing/duplicate assignment.
- Keep the existing formatting, lint, build, and release jobs intact.

### Configuration / migration / data changes

- `CDP_PARALLEL=4` is the default CI bound.
- No user or runtime configuration changes.

### Testing strategy

- Unit: run each shard command locally and verify coverage files are produced.
- CI: compare total wall-clock time and per-shard maximum; reject a configuration where one fast shard is an outlier.
- Race: run s1–s3 with `-race`; run CDP with and without race in a benchmark job if the browser environment permits.

### Rollout plan

Land as CI-only infrastructure. If the new package-list check is too strict for current repository conventions, land the matrix first and add the check in the same feature branch before merging.

### Acceptance criteria

- Every Go package appears in exactly one test shard.
- Fast shards retain race detection and coverage.
- CDP runs with bounded parallelism and no new data races or shared-browser interference.
- The CI job no longer has a single unpartitioned Go test invocation.
- Existing lint/build/release behavior is unchanged.

## Feature Spec 9: Client Test Isolation, Worker Support, and Documentation

### Goal and scope

Make Python and TypeScript client testing safe to run in CI and locally with multiple devices, while documenting the exact commands and limitations. This is supporting work for the two client features and the E2E matrix.

### Current behaviour in upstream

There are no client trees, no unit/device test distinction, and no worker-aware device/server allocation. Documentation only describes the Go runner and existing drivers.

### Desired behaviour

- Unit tests never start a runner server or require a device.
- Device tests require a server/driver and are selected explicitly.
- Python xdist workers receive unique ports, devices, and output directories.
- TypeScript workers receive unique ports and can be limited to serial execution for one device.
- Logs and artifact summaries are attached to failures with worker/device identity.
- Documentation describes prerequisites, environment variables, unit/device commands, and the fact that parallel device tests require multiple devices.

### Required code changes

- Update Python `tests/conftest.py` and TypeScript `tests/setup.ts` with worker-aware lifecycle and artifact summaries.
- Rename/add TypeScript unit and device tests to match the configured Jest patterns.
- Add `client/python/DEVELOPER.md`, `client/typescript/DEVELOPER.md`, `docs/clients/README.md`, `docs/clients/python.md`, and `docs/clients/typescript.md`.
- Update `README.md` and the client package READMEs with installation and server-start commands.
- Add Makefile targets for client unit checks and a clear device-test command that is not part of the default unit target.

### Configuration / migration / data changes

- Existing `MAESTRO_*` variables remain supported.
- Add explicit worker/device variables only where the runtime cannot infer them.
- No user data migration.

### Testing strategy

- Unit: run the client unit commands in a clean environment with no server/device.
- Device: run one serial Android suite and one iOS suite on an explicitly named device.
- Parallel: run two Python workers and two TypeScript workers against two Android devices, verifying no port/device collision.
- Documentation: execute every documented command in a clean checkout.

### Rollout plan

Land with the clients and before enabling the full E2E matrix. Keep device suites opt-in in the normal unit CI job; trigger them from the Android E2E workflow and documented local commands.

### Acceptance criteria

- Unit CI has no hidden server/device requirement.
- Device tests cannot run accidentally from the unit command.
- Worker artifacts identify the worker and device.
- Two-worker runs are isolated and deterministic.
- Documentation commands are executable as written.

## Cross-Cutting Validation

Before marking the sync complete, run these checks against the target upstream branch:

```bash
gofmt -s -l $(git ls-files '*.go')
go test ./...
go test -race ./...
go vet ./...
npm --prefix client/typescript ci
npm --prefix client/typescript run test:unit
npm --prefix client/typescript run lint
cd client/python && python -m pytest tests/test_client.py tests/test_models.py -v --noconftest
cd client/python && ruff check maestro_runner tests
cd client/python && mypy maestro_runner
```

Then run the Android E2E workflow manually for `uiautomator2`, `devicelab`, and `appium`, followed by the iOS client device suite. Validate that no generated artifacts were introduced and that every change is present in the upstream target branch only.

## Definition of Done

- Every P0 feature has a stable API contract and automated unit coverage.
- Every P1 runtime feature has focused driver/parser tests and a real-device test where applicable.
- CI sharding includes all new Go packages and all client/E2E workflows.
- Generated binaries and local-only files are absent from the propagation commits.
- No upstream change was merged back into origin as part of this effort.
- A release note or changelog entry documents the additive server/client capabilities and the intentional animation-wait timeout behavior change.
