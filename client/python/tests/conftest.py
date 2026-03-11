"""Shared pytest fixtures — auto-start maestro-runner server when needed.

Supports pytest-xdist parallel execution: each worker gets its own server
instance on a unique port, targeting a specific device (via ANDROID_SERIAL).
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Generator

import fcntl

import pytest
import requests
from maestro_runner import MaestroClient

SERVER_URL = os.environ.get("MAESTRO_SERVER_URL", "http://localhost:9999")
PLATFORM = os.environ.get("MAESTRO_PLATFORM", "android")
SERVER_PORT = SERVER_URL.rsplit(":", 1)[-1].rstrip("/")

# Where to find the binary — override with MAESTRO_RUNNER_BIN env var
_DEFAULT_BIN = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "maestro-runner",
)
MAESTRO_RUNNER_BIN = os.environ.get("MAESTRO_RUNNER_BIN", _DEFAULT_BIN)
REPORTS_DIR = (Path(__file__).resolve().parent.parent / "reports")


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _active_worker_id(explicit_worker_id: str | None = None) -> str:
    if explicit_worker_id:
        return explicit_worker_id
    return os.environ.get("PYTEST_XDIST_WORKER", "master")


def _make_run_id(worker_id: str) -> str:
    return f"{_utc_timestamp()}-{worker_id}-{os.getpid()}"


_ORIGINAL_RECORD_FACTORY = logging.getLogRecordFactory()


def _record_factory(*args: object, **kwargs: object) -> logging.LogRecord:
    record = _ORIGINAL_RECORD_FACTORY(*args, **kwargs)
    if not hasattr(record, "worker_id"):
        record.worker_id = _active_worker_id()
    return record


logging.setLogRecordFactory(_record_factory)


def _tail_file(path: Path, max_lines: int = 120) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-max_lines:])


def _persist_latest_server_metadata(entry: dict[str, str]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    latest_path = REPORTS_DIR / "server-latest.json"
    lock_path = REPORTS_DIR / "server-latest.lock"

    with lock_path.open("w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        payload: dict[str, object] = {
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "workers": {},
        }

        if latest_path.exists():
            try:
                payload = json.loads(latest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {
                    "updatedAt": datetime.now(timezone.utc).isoformat(),
                    "workers": {},
                }

        workers = payload.get("workers", {})
        if not isinstance(workers, dict):
            workers = {}
        workers[entry["workerId"]] = entry
        payload["workers"] = workers
        payload["updatedAt"] = datetime.now(timezone.utc).isoformat()

        tmp_path = REPORTS_DIR / "server-latest.json.tmp"
        tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp_path, latest_path)


def _setup_persisted_python_logs(worker_id: str, run_id: str) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    handler_name = f"pytest-run-{worker_id}"

    for handler in root_logger.handlers:
        if getattr(handler, "name", "") == handler_name:
            return

    log_path = REPORTS_DIR / f"pytest-run-{run_id}.log"
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.name = handler_name
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s] [worker=%(worker_id)s] %(message)s"
        )
    )
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)


def _server_is_ready(url: str, timeout: float = 2.0) -> bool:
    """Return True if the server responds to /status."""
    try:
        resp = requests.get(f"{url}/status", timeout=timeout)
        return resp.status_code == 200
    except requests.ConnectionError:
        return False


def _discover_devices() -> list[str]:
    """Return a list of connected Android device serials via adb."""
    try:
        out = subprocess.check_output(["adb", "devices"], text=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []
    devices = []
    for line in out.strip().splitlines()[1:]:
        m = re.match(r"^(\S+)\s+device$", line)
        if m:
            devices.append(m.group(1))
    return devices


def _worker_index(worker_id: str) -> int:
    """Extract 0-based index from xdist worker id like 'gw0', 'gw1'."""
    m = re.search(r"(\d+)$", worker_id)
    return int(m.group(1)) if m else 0


@pytest.fixture(scope="session")
def maestro_server(worker_id: str) -> Generator[tuple[str, str | None], None, None]:
    """Ensure a maestro-runner server is available.

    In xdist parallel mode, each worker starts its own server on a unique port
    targeting a specific device. In single-worker mode, reuses any running
    server or starts one.

    Yields (server_url, device_serial_or_None).
    """
    run_id = _make_run_id(worker_id)
    _setup_persisted_python_logs(worker_id, run_id)

    # Single-worker mode (no xdist or xdist with -n0)
    if worker_id == "master":
        if _server_is_ready(SERVER_URL):
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            server_log_path = REPORTS_DIR / f"server-run-{_utc_timestamp()}-{worker_id}.log"
            server_log_path.write_text(
                "Reused existing maestro-runner server; process stdout/stderr "
                "owned by external process.\n",
                encoding="utf-8",
            )
            _persist_latest_server_metadata(
                {
                    "workerId": worker_id,
                    "runId": run_id,
                    "serverUrl": SERVER_URL,
                    "serverPort": SERVER_PORT,
                    "serverLogPath": str(server_log_path),
                    "mode": "reused-existing-server",
                    "startedAt": datetime.now(timezone.utc).isoformat(),
                }
            )
            yield SERVER_URL, None
            return

        binary = shutil.which("maestro-runner") or MAESTRO_RUNNER_BIN
        if not os.path.isfile(binary):
            pytest.fail(
                f"maestro-runner binary not found at {binary}. "
                "Set MAESTRO_RUNNER_BIN or add it to PATH."
            )

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        server_log_path = REPORTS_DIR / f"server-run-{_utc_timestamp()}-{worker_id}.log"
        server_log = server_log_path.open("a", encoding="utf-8", buffering=1)
        server_log.write(f"runId={run_id} workerId={worker_id} platform={PLATFORM}\n")

        proc = subprocess.Popen(
            [binary, "--platform", PLATFORM, "server", "--port", SERVER_PORT],
            stdout=server_log,
            stderr=subprocess.STDOUT,
        )
        _persist_latest_server_metadata(
            {
                "workerId": worker_id,
                "runId": run_id,
                "serverUrl": SERVER_URL,
                "serverPort": SERVER_PORT,
                "serverLogPath": str(server_log_path),
                "mode": "spawned",
                "startedAt": datetime.now(timezone.utc).isoformat(),
            }
        )

        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                out = _tail_file(server_log_path)
                server_log.close()
                pytest.fail(f"maestro-runner exited early (code {proc.returncode}):\n{out}")
            if _server_is_ready(SERVER_URL):
                break
            time.sleep(0.5)
        else:
            proc.terminate()
            server_log.close()
            pytest.fail("maestro-runner server did not become ready within 30 s")

        yield SERVER_URL, None
        proc.terminate()
        proc.wait(timeout=10)
        server_log.write(f"terminated runId={run_id} workerId={worker_id}\n")
        server_log.close()
        return

    # Parallel mode — each worker gets its own port and device
    idx = _worker_index(worker_id)
    port = int(SERVER_PORT) + idx
    url = f"http://localhost:{port}"

    devices = _discover_devices()
    if idx >= len(devices):
        pytest.fail(
            f"Worker {worker_id} needs device index {idx} but only "
            f"{len(devices)} device(s) found: {devices}"
        )
    device_serial = devices[idx]

    binary = shutil.which("maestro-runner") or MAESTRO_RUNNER_BIN
    if not os.path.isfile(binary):
        pytest.fail(
            f"maestro-runner binary not found at {binary}. "
            "Set MAESTRO_RUNNER_BIN or add it to PATH."
        )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    server_log_path = REPORTS_DIR / f"server-run-{_utc_timestamp()}-{worker_id}.log"
    server_log = server_log_path.open("a", encoding="utf-8", buffering=1)
    server_log.write(
        f"runId={run_id} workerId={worker_id} platform={PLATFORM} "
        f"deviceId={device_serial}\n"
    )

    proc = subprocess.Popen(
        [binary, "--platform", PLATFORM, "server", "--port", str(port)],
        stdout=server_log,
        stderr=subprocess.STDOUT,
        env={**os.environ, "ANDROID_SERIAL": device_serial},
    )
    _persist_latest_server_metadata(
        {
            "workerId": worker_id,
            "runId": run_id,
            "serverUrl": url,
            "serverPort": str(port),
            "deviceId": device_serial,
            "serverLogPath": str(server_log_path),
            "mode": "spawned",
            "startedAt": datetime.now(timezone.utc).isoformat(),
        }
    )

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            out = _tail_file(server_log_path)
            server_log.close()
            pytest.fail(f"maestro-runner exited early (code {proc.returncode}):\n{out}")
        if _server_is_ready(url):
            break
        time.sleep(0.5)
    else:
        proc.terminate()
        server_log.close()
        pytest.fail(f"maestro-runner server on port {port} did not become ready within 30 s")

    yield url, device_serial

    proc.terminate()
    proc.wait(timeout=10)
    server_log.write(f"terminated runId={run_id} workerId={worker_id}\n")
    server_log.close()


@pytest.fixture(scope="session")
def client(maestro_server: tuple[str, str | None]) -> Generator[MaestroClient, None, None]:
    """Create a MaestroClient session for the entire test session."""
    url, device_serial = maestro_server
    caps: dict[str, str] = {"platformName": PLATFORM}
    if device_serial:
        caps["deviceId"] = device_serial
    with MaestroClient(url, capabilities=caps) as c:
        yield c
