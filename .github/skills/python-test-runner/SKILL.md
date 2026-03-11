---
name: python-test-runner
description: >
  Runs tests, lint, and type checks for the maestro-runner Python client at
  client/python/. Use this skill whenever the user mentions pytest, ruff,
  mypy, the Python venv, or running/debugging tests for client/python/ — even
  if they just say "run the tests" and the context is clearly Python. Make
  sure to use this skill for any pytest or make lint-py command, and any time
  the user asks why a Python test is failing or the venv isn't working. 
  Automatically handles test sequencing and device lock conflicts for "run all tests" 
  requests. DO NOT use for TypeScript tests, Go tests, or server-side code — use the
  typescript-test-runner skill or run Go tests directly.
allowed-tools: "Bash(python:*) Bash(python3:*) Bash(pip:*) Bash(pip3:*) Bash(pytest:*) Bash(ruff:*) Bash(mypy:*) Bash(make:*) Bash(adb:*) Bash(curl:*) Bash(source:*)"
metadata:
  author: maestro-runner
  version: 1.1.0
  category: testing
  tags: [python, pytest, e2e, android, lint, mypy, ruff, test-sequencing, device-lock]
---

# Python Test Runner

Runs tests, lint, and type checks for the Python client at `client/python/`.

## Do NOT use this skill for

- TypeScript tests → use the `typescript-test-runner` skill
- Go / server tests → run `go test ./...` directly
- General Python questions unrelated to running tests

## Prerequisites

- Python venv at `client/python/.venv/` — activate it before every command or
  pytest will use the system Python and not find the project's dependencies
- Prefer the project-local venv (`client/python/.venv`) over repo-root venvs.
  If `python -m pytest` says `No module named pytest`, you're likely using the
  wrong interpreter.
- For e2e/Android tests: Android emulator running + `maestro-runner` binary built

```sh
# Activate the venv first — all commands below assume it is active
cd client/python && source .venv/bin/activate

# Or run directly without activating
cd client/python && ./.venv/bin/python -m pytest -v
```

## Step 1: Unit Tests (no device needed)

```sh
# All unit tests
cd client/python && source .venv/bin/activate && python -m pytest tests/test_client.py tests/test_models.py -v

# Single file
python -m pytest tests/test_client.py -v

# Specific test
python -m pytest tests/test_client.py::TestSessionManagement::test_create_session -v

# Parallel execution
python -m pytest tests/test_client.py tests/test_models.py -n auto -v
```

## Step 2: E2E Android Tests

Requires the server to be running first.

### 1. Check emulator is attached
```sh
adb devices
```

### 2. Start the server (if not already running)
```sh
# From repo root — runs in background
./maestro-runner --platform android server --port 9999 &>/tmp/maestro-server.log &

# Verify it's up
curl -s http://localhost:9999/status

# Optional: ensure no stale server process is holding the device
pgrep -af "maestro-runner.*server" || true
```

### 3. Run the tests
```sh
cd client/python && source .venv/bin/activate && python -m pytest tests/test_e2e_android.py -v
```

To target a different server URL:
```sh
MAESTRO_SERVER_URL=http://localhost:8888 python -m pytest tests/test_e2e_android.py -v
```

## Step 3: Page-Object / Integration Tests (need device + server)

```sh
cd client/python && source .venv/bin/activate && \
  python -m pytest tests/test_add_contact.py tests/test_contact_persists.py -n auto -v
```

## Step 4: Lint

```sh
# From repo root via Makefile
make lint-py

# Or directly
cd client/python && source .venv/bin/activate
ruff check maestro_runner tests
mypy maestro_runner

# Auto-fix
make lint-py-fix
```

## Step 5: All Tests (unit only, no device)

```sh
cd client/python && source .venv/bin/activate && python -m pytest tests/test_client.py tests/test_models.py -v
```

## Run All Tests (Complete Suite)

**Use this when asked to "run all tests"** — handles proper sequencing and device lock mitigation:

```sh
# 1) Run unit tests first (no device needed)
cd client/python && source .venv/bin/activate && \
  python -m pytest tests/test_client.py tests/test_models.py -v

# 2) Run page-object/integration tests (need device + server)
cd client/python && python -m pytest tests/test_add_contact.py tests/test_contact_persists.py -v

# 3) Clean up any stale server processes holding device
pkill -f "maestro-runner.*server" || true
sleep 2

# 4) Start fresh server instance for e2e tests
cd /path/to/repo && ./maestro-runner --platform android server --port 9999 &>/tmp/maestro-server.log &
sleep 2
curl -s http://localhost:9999/status

# 5) Run e2e tests (with exclusive device access)
cd client/python && python -m pytest tests/test_e2e_android.py -v
```

**Why this order:**
- Unit tests run first (fastest, no device needed)
- Integration tests can share server session
- Device lock is cleaned up before e2e tests to prevent "device already in use" errors
- E2E tests run last with fresh server connection

## Reliable Full-Client Run Order

When both unit and Android e2e tests are needed, run in this order to reduce
device-lock flakes:

```sh
# 1) Unit/model/integration tests (no device lock risk)
cd client/python && ./.venv/bin/python -m pytest tests/test_client.py tests/test_models.py -v

# 2) Start server and confirm status
cd /path/to/repo && ./maestro-runner --platform android server --port 9999 &>/tmp/maestro-server.log &
curl -s http://localhost:9999/status

# 3) E2E tests separately
cd client/python && ./.venv/bin/python -m pytest tests/test_e2e_android.py -v

# 4) Page-Object / Integration Tests (after e2e, reusing server)
cd client/python && ./.venv/bin/python -m pytest tests/test_add_contact.py tests/test_contact_persists.py -v
```

## Reports

HTML and JUnit XML reports are written to `client/python/reports/` after every pytest run:
- `reports/report.html`
- `reports/junit-report.xml`

## Common Issues

| Problem | Fix |
|---------|-----|
| `Connection refused` on e2e tests | Server not running — start it with step 2 above |
| `No module named pytest` | You're using the wrong Python interpreter. Use `client/python/.venv/bin/python` |
| `device ... is already in use` | Another server/session is holding the emulator. Stop stale server process and rerun e2e tests separately |
| `adb: command not found` | Android SDK not on PATH; set `ANDROID_HOME` |
| Lint `E501` line-too-long | Line length limit is 100; wrap long lines |
