# Backlog

Potential future work, not yet scheduled.

## CDP test suite: split & improve (then re-enable in CI)

### Context
The `pkg/driver/browser/cdp` package's tests are by far the slowest in the
repo. Measured on CI:

- **~354s** with no `-race` (from the sharding `prepare` timing run)
- **~446s (~7.5 min)** with `-race` — the dominant shard in the time-based
  sharded `Test Go` job.

Because `go test` shards at **package** granularity, a single package cannot be
split across the matrix shards, so this one package floors total CI time to
~7.5 min while the other three shards idle at ~1 min each. Time-based sharding
is correct; `cdp` is simply too big to benefit from it.

### Decision (current)
CDP browser tests are **disabled in CI** (excluded in
`.github/workflows/ci.yml` via `EXCLUDE_PKGS`). The suite still builds and runs
locally; it is just not executed in the CI matrix. This removes the ~7.5 min
floor and makes the sharded `Test Go` job finish in ~1-2 min.

### Plan to re-enable & parallelize
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

### Acceptance
- `cdp` tests run in CI again without blowing the overall time budget.
- No single `Test Go` shard is an outlier by >2x vs the others.
