# Backlog

Potential future work, not yet scheduled.

## CDP test suite: split & improve (then re-enable in CI) — ✅ Completed (PR #5)

### Context
The `pkg/driver/browser/cdp` package's tests were by far the slowest in the
repo. Measured on CI at the time:

- **~354s** with no `-race` (from the sharding `prepare` timing run)
- **~446s (~7.5 min)** with `-race` — the dominant shard in the time-based
  sharded `Test Go` job.

Because `go test` shards at **package** granularity, a single package cannot be
split across the matrix shards, so this one package floored total CI time to
~7.5 min while the other three shards idled at ~1 min each. Time-based sharding
is correct; `cdp` is simply too big to benefit from it.

### Decision (completed — PR #5)
CDP browser tests are **re-enabled in CI** via a dedicated `cdp` shard
(`.github/workflows/ci.yml:81`, `CDP_PARALLEL=4`, `RACE_FLAG` dropped for
`cdp`). The suite uses in-package `t.Parallel()` and `-parallel 4` in CI. The
`EXCLUDE_PKGS` exclusion was removed. The sharded `Test Go` job now finishes
with `cdp` ~3 min and the other shards ~1 min, removing the prior ~7.5 min
floor and keeping the build in the ~1-3 min budget.

### Plan to re-enable & parallelize (historical — completed)
1. **Profile the slowness** — determine *why* `cdp` takes 354s even without
   `-race`. Likely causes: real headless-Chrome automation, a single heavy
   shared setup, or many serial subtests. Confirm whether the tests actually
   require a live browser in CI or could run against a mock CDP WebSocket
   server.
2. **Mock the transport** — most CDP client logic (command encoding, event
   parsing, session/target management) can be exercised against an in-process
   mock WebSocket server, removing the browser dependency and the bulk of the
   runtime.
3. **Split into sub-packages** — once mocked/heavier tests are isolated, factor
   `cdp` test files into multiple packages (e.g. `cdp`, `cdp/page`,
   `cdp/input`, `cdp/network`) so the existing package-level time-based
   sharding parallelizes them automatically.
4. **Parallelize subtests** — annotate independent subtests with `t.Parallel()`
   and share/reset a single browser session instead of per-test setup.
5. **Re-enable in CI** once the package fits a reasonable budget (target
   < ~2 min, or split such that no single shard exceeds the others by >2x).
   Remove `EXCLUDE_PKGS` from `.github/workflows/ci.yml` at that point.
6. **Interim (pure-CI) option** — if code changes are deferred, partition
   `cdp`'s test functions across extra shards via `go test -run 'TestX|TestY'`
   in the sharding matrix (no code refactor) to at least parallelize execution.

### Acceptance — met
- `cdp` tests run in CI again without blowing the overall time budget. Latest
  `main` run `33304524139` shows `Test Go (shard cdp)` `success`.
- No single `Test Go` shard is an outlier by >2x vs the others (cdp ~3 min vs
  others ~1 min).

## Android animation testing: stoppable-animation feature & tests — ✅ Completed (PR #11)

### Context
The Android animation test app lives at `e2e/android-animation-app` (package
`dev.maestro.animationtest`). Its `MainActivity.java` renders a **canvas
spinner** via `setInterval(draw, 16)` (`MainActivity.java:28`). Until PR #11 it
had **no stop control** — no Stop button, `clearInterval`, or pause. As a
result the only animation coverage was:

- **Continuous / never-ends**: `client/python/tests/test_wait_for_animation_never_ends.py`,
  `client/typescript/tests/test_wait_for_animation_never_ends.device.test.ts`,
  and the YAML flow `e2e/workspaces/animation/wait_for_animation_android.yaml`
  (added in PR #10, `waitForAnimationToEnd` with `optional: true`).
- **"Animation settles" (positive)**: exercised against **Android Settings**
  (`client/python/tests/test_wait_for_animation_to_end.py`), not the spinner
  app.

### Plan (completed — PR #11)
1. **Continuous animation test** — covered (never-ends) and the YAML coverage
   is `optional` / best-effort.
2. **Stop control in the animation app** — added `Stop`/`Start` buttons to
   `activity_main.xml:7` (`fitsSystemWindows` + side-by-side) wired to
   `clearInterval`/`setInterval` in `MainActivity.java:28` (white static
   background, only the bar animates). Rebuilt `drivers/android/animation-test-app-debug.apk` (12K).
3. **Animation stops on click** — added e2e tests (YAML `e2e/workspaces/animation/wait_for_animation_stops_on_click_android.yaml:13` + Python `client/python/tests/test_wait_for_animation_stops_on_click.py:26` + TS `client/typescript/tests/test_wait_for_animation_stops_on_click.device.test.ts:26`) that launch the app, verify the spinner is animating (`waitForAnimationToEnd` times out in `pytest.raises(StepError)` / `rejects.toThrow`), `tapOn`/`tap` Stop, then `waitForAnimationToEnd` succeeds. Wired into `e2e-android.yml:196`.
4. **Acceptance** — CI verifies BOTH an infinite spinner is "never ending" AND a
   spinner halted via Stop is "ended" (both `uiautomator2` and `devicelab` legs
   in PR #11).

### Acceptance — met
- An infinite spinner is detected as "never ending" (continuous coverage
  preserved, incl. the `optional` YAML flow).
- A spinner halted via the Stop button is detected as "ended" (new
  stop-on-click tests passed locally `11.29s` and in CI on `android/animation-stop-button`).
