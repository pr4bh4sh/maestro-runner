"""Shared pytest fixtures — auto-start maestro-runner server when needed.

Supports pytest-xdist parallel execution: each worker gets its own server
instance on a unique port, targeting a specific device (via ANDROID_SERIAL).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from collections.abc import Generator

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
    # Single-worker mode (no xdist or xdist with -n0)
    if worker_id == "master":
        if _server_is_ready(SERVER_URL):
            yield SERVER_URL, None
            return

        binary = shutil.which("maestro-runner") or MAESTRO_RUNNER_BIN
        if not os.path.isfile(binary):
            pytest.fail(
                f"maestro-runner binary not found at {binary}. "
                "Set MAESTRO_RUNNER_BIN or add it to PATH."
            )

        proc = subprocess.Popen(
            [binary, "--platform", PLATFORM, "server", "--port", SERVER_PORT],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                out = proc.stdout.read().decode() if proc.stdout else ""
                pytest.fail(f"maestro-runner exited early (code {proc.returncode}):\n{out}")
            if _server_is_ready(SERVER_URL):
                break
            time.sleep(0.5)
        else:
            proc.terminate()
            pytest.fail("maestro-runner server did not become ready within 30 s")

        yield SERVER_URL, None
        proc.terminate()
        proc.wait(timeout=10)
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

    proc = subprocess.Popen(
        [binary, "--platform", PLATFORM, "server", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            out = proc.stdout.read().decode() if proc.stdout else ""
            pytest.fail(f"maestro-runner exited early (code {proc.returncode}):\n{out}")
        if _server_is_ready(url):
            break
        time.sleep(0.5)
    else:
        proc.terminate()
        pytest.fail(f"maestro-runner server on port {port} did not become ready within 30 s")

    yield url, device_serial

    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="session")
def client(maestro_server: tuple[str, str | None]) -> Generator[MaestroClient, None, None]:
    """Create a MaestroClient session for the entire test session."""
    url, device_serial = maestro_server
    caps: dict[str, str] = {"platformName": PLATFORM}
    if device_serial:
        caps["deviceId"] = device_serial
    with MaestroClient(url, capabilities=caps) as c:
        yield c
