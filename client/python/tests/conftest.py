"""Shared pytest fixtures — auto-start maestro-runner server when needed.

Supports pytest-xdist parallel execution: each worker gets its own server
instance on a unique port, targeting a specific device (via ANDROID_SERIAL).
"""

from __future__ import annotations

import base64
import fcntl
import html
import json
import logging
import os
import re
import shutil
import subprocess
import time
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import requests
from maestro_runner import MaestroClient

SERVER_URL = os.environ.get("MAESTRO_SERVER_URL", "http://localhost:9999")
PLATFORM = os.environ.get("MAESTRO_PLATFORM", "android")
EXPLICIT_DEVICE_ID = os.environ.get("MAESTRO_DEVICE_ID")
SERVER_PORT = SERVER_URL.rsplit(":", 1)[-1].rstrip("/")

# Where to find the binary — override with MAESTRO_RUNNER_BIN env var
_DEFAULT_BIN = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "maestro-runner",
)
MAESTRO_RUNNER_BIN = os.environ.get("MAESTRO_RUNNER_BIN", _DEFAULT_BIN)
REPORTS_DIR = (Path(__file__).resolve().parent.parent / "reports")
HTML_OVERRIDE_CSS = Path(__file__).resolve().parent / "report-overrides.css"
_CURRENT_NODE_ID = "-"
_SESSION_RUN_ID = ""
_SESSION_WORKER_ID = "master"


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _active_worker_id(explicit_worker_id: str | None = None) -> str:
    if explicit_worker_id:
        return explicit_worker_id
    return os.environ.get("PYTEST_XDIST_WORKER", "master")


def _active_node_id() -> str:
    if _CURRENT_NODE_ID and _CURRENT_NODE_ID != "-":
        return _CURRENT_NODE_ID
    current_test = os.environ.get("PYTEST_CURRENT_TEST", "")
    if "::" in current_test:
        return current_test.split(" ", 1)[0]
    return "-"


def _make_run_id(worker_id: str) -> str:
    return f"{_utc_timestamp()}-{worker_id}-{os.getpid()}"


def _ensure_session_context(explicit_worker_id: str | None = None) -> tuple[str, str]:
    global _SESSION_RUN_ID, _SESSION_WORKER_ID

    worker_id = _active_worker_id(explicit_worker_id)
    if not _SESSION_RUN_ID:
        _SESSION_RUN_ID = _make_run_id(worker_id)
        _SESSION_WORKER_ID = worker_id
    elif not _SESSION_WORKER_ID:
        _SESSION_WORKER_ID = worker_id

    return _SESSION_RUN_ID, _SESSION_WORKER_ID


def _session_run_dir(run_id: str | None = None) -> Path:
    active_run_id = run_id or _SESSION_RUN_ID
    return REPORTS_DIR / active_run_id if active_run_id else REPORTS_DIR


def _move_shared_pytest_reports(run_dir: Path) -> None:
    for artifact_name in ("report.html", "junit-report.xml"):
        shared_path = REPORTS_DIR / artifact_name
        run_path = run_dir / artifact_name
        if shared_path.exists() and shared_path != run_path:
            run_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(shared_path, run_path)


def _relative_run_artifact_path(path: Path) -> str:
    return str(path.relative_to(_session_run_dir()))


_ORIGINAL_RECORD_FACTORY = logging.getLogRecordFactory()


def _record_factory(*args: object, **kwargs: object) -> logging.LogRecord:
    record = _ORIGINAL_RECORD_FACTORY(*args, **kwargs)
    if not hasattr(record, "worker_id"):
        record.worker_id = _active_worker_id()
    if not hasattr(record, "node_id"):
        record.node_id = _active_node_id()
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
    run_dir = _session_run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    handler_name = f"pytest-run-{run_id}"

    for handler in root_logger.handlers:
        if getattr(handler, "name", "") == handler_name:
            return

    log_path = run_dir / "pytest-run.log"
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.name = handler_name
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s] "
            "[worker=%(worker_id)s] [node=%(node_id)s] %(message)s"
        )
    )
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)


def _resolve_worker_metadata(worker_id: str) -> dict[str, Any]:
    latest_path = REPORTS_DIR / "server-latest.json"
    if not latest_path.exists():
        return {}
    try:
        data = json.loads(latest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    workers = data.get("workers", {})
    if not isinstance(workers, dict):
        return {}

    metadata = workers.get(worker_id)
    if not isinstance(metadata, dict):
        return {}
    return metadata


def _write_artifact_summary(exit_status: int) -> None:
    if not _SESSION_RUN_ID:
        return

    worker_id = _SESSION_WORKER_ID
    run_id = _SESSION_RUN_ID
    run_dir = _session_run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    _move_shared_pytest_reports(run_dir)
    metadata = _resolve_worker_metadata(worker_id)

    artifacts: list[dict[str, Any]] = []
    for path in [
        run_dir / "report.html",
        run_dir / "junit-report.xml",
    ]:
        if path.exists():
            artifacts.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "sizeBytes": path.stat().st_size,
                }
            )

    pytest_log_path = run_dir / "pytest-run.log"
    if pytest_log_path.exists():
        artifacts.append(
            {
                "name": pytest_log_path.name,
                "path": str(pytest_log_path),
                "sizeBytes": pytest_log_path.stat().st_size,
            }
        )

    server_log_path = Path(str(metadata.get("serverLogPath", "")))
    if server_log_path.exists():
        artifacts.append(
            {
                "name": server_log_path.name,
                "path": str(server_log_path),
                "sizeBytes": server_log_path.stat().st_size,
            }
        )

    summary: dict[str, Any] = {
        "runId": run_id,
        "workerId": worker_id,
        "platform": PLATFORM,
        "serverUrl": str(metadata.get("serverUrl", SERVER_URL)),
        "serverPort": str(metadata.get("serverPort", SERVER_PORT)),
        "sessionStatus": "failed" if exit_status != 0 else "passed",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "artifacts": artifacts,
    }

    if exit_status != 0:
        summary["failureTails"] = {
            "server": _tail_file(server_log_path) if server_log_path.exists() else "",
            "pytest": _tail_file(pytest_log_path) if pytest_log_path.exists() else "",
        }

    summary_path = run_dir / "artifact-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def _server_command(port: str, *, device_id: str | None = None) -> list[str]:
    command = ["--platform", PLATFORM]
    if device_id:
        command.extend(["--device", device_id])
    command.extend(["server", "--port", port])
    return command


@pytest.fixture(scope="session")
def maestro_server(worker_id: str) -> Generator[tuple[str, str | None], None, None]:
    """Ensure a maestro-runner server is available.

    In xdist parallel mode, each worker starts its own server on a unique port
    targeting a specific device. In single-worker mode, reuses any running
    server or starts one.

    Yields (server_url, device_serial_or_None).
    """
    run_id, worker_id = _ensure_session_context(worker_id)
    _setup_persisted_python_logs(worker_id, run_id)
    run_dir = _session_run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    # Single-worker mode (no xdist or xdist with -n0)
    if worker_id == "master":
        if _server_is_ready(SERVER_URL):
            server_log_path = run_dir / "server-run.log"
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
                    **({"deviceId": EXPLICIT_DEVICE_ID} if EXPLICIT_DEVICE_ID else {}),
                    "startedAt": datetime.now(timezone.utc).isoformat(),
                }
            )
            yield SERVER_URL, EXPLICIT_DEVICE_ID
            return

        binary = shutil.which("maestro-runner") or MAESTRO_RUNNER_BIN
        if not os.path.isfile(binary):
            pytest.fail(
                f"maestro-runner binary not found at {binary}. "
                "Set MAESTRO_RUNNER_BIN or add it to PATH."
            )

        server_log_path = run_dir / "server-run.log"
        server_log = server_log_path.open("a", encoding="utf-8", buffering=1)
        server_log.write(f"runId={run_id} workerId={worker_id} platform={PLATFORM}\n")

        proc = subprocess.Popen(
            [binary, *_server_command(SERVER_PORT, device_id=EXPLICIT_DEVICE_ID)],
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
                **({"deviceId": EXPLICIT_DEVICE_ID} if EXPLICIT_DEVICE_ID else {}),
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

        yield SERVER_URL, EXPLICIT_DEVICE_ID
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

    server_log_path = run_dir / "server-run.log"
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


def _capture_failure_diagnostics(test_name: str, client: MaestroClient | None) -> dict[str, str]:
    """Capture server logs, screenshot, and UI dump after a test failure.

    Stores diagnostics in a run-specific directory: reports/{run_id}/diagnostics/
    """
    if not _SESSION_RUN_ID:
        return {}

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    test_safe = re.sub(r"[^a-zA-Z0-9_-]", "_", test_name)
    artifacts: dict[str, str] = {}

    # Create run-specific diagnostics directory
    run_dir = _session_run_dir() / "diagnostics"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Get server log tail
    worker_metadata = _resolve_worker_metadata(_SESSION_WORKER_ID)
    server_log_path = Path(str(worker_metadata.get("serverLogPath", "")))
    if server_log_path.exists():
        log_content = _tail_file(server_log_path, max_lines=200)
        log_file = run_dir / f"{test_safe}-{timestamp}-server.log"
        log_file.write_text(log_content, encoding="utf-8")
        artifacts["server_log"] = str(log_file)
        artifacts["server_log_text"] = log_content
        logger = logging.getLogger(__name__)
        logger.info(f"✓ Server log captured: {log_file.relative_to(REPORTS_DIR)}")

    # Capture screenshot and UI dump if client is available
    if client:
        try:
            screenshot_file = run_dir / f"{test_safe}-{timestamp}-screenshot.png"
            screenshot_data = client.screenshot()
            screenshot_file.write_bytes(screenshot_data)
            artifacts["screenshot_file"] = str(screenshot_file)
            artifacts["screenshot_base64"] = base64.b64encode(screenshot_data).decode("utf-8")
            logging.getLogger(__name__).info(
                f"✓ Screenshot captured: {screenshot_file.relative_to(REPORTS_DIR)}"
            )
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to capture screenshot: {e}")

        try:
            ui_dump_file = run_dir / f"{test_safe}-{timestamp}-ui-dump.xml"
            ui_dump = client.view_hierarchy()
            ui_dump_file.write_text(ui_dump, encoding="utf-8")
            artifacts["ui_dump"] = str(ui_dump_file)
            logging.getLogger(__name__).info(
                f"✓ UI dump captured: {ui_dump_file.relative_to(REPORTS_DIR)}"
            )
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to capture UI dump: {e}")

    return artifacts



_CURRENT_CLIENT: MaestroClient | None = None


@pytest.fixture(autouse=True)
def _track_client(client: MaestroClient) -> Generator[None, None, None]:
    """Track the current client for diagnostic capture."""
    global _CURRENT_CLIENT
    _CURRENT_CLIENT = client
    yield
    _CURRENT_CLIENT = None


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    global _CURRENT_NODE_ID
    _CURRENT_NODE_ID = item.nodeid


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    run_id, _ = _ensure_session_context()
    run_dir = _session_run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    existing_css = list(getattr(config.option, "css", []) or [])
    override_css = str(HTML_OVERRIDE_CSS)
    if override_css not in existing_css:
        config.option.css = [*existing_css, override_css]

    if hasattr(config.option, "htmlpath"):
        config.option.htmlpath = str(run_dir / "report.html")
    if hasattr(config.option, "xmlpath"):
        config.option.xmlpath = str(run_dir / "junit-report.xml")


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_teardown(item: pytest.Item, nextitem: pytest.Item | None) -> None:
    del item, nextitem
    global _CURRENT_NODE_ID
    _CURRENT_NODE_ID = "-"


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[Any]
) -> Generator[None, None, None]:
    """Capture diagnostics after test call fails and attach key artifacts to pytest-html."""
    outcome: Any = yield
    report = outcome.get_result()

    if report.when != "call" or call.excinfo is None:
        return

    test_name = item.name
    logging.getLogger(__name__).error(f"Test {test_name} failed, capturing diagnostics...")
    captured_artifacts = _capture_failure_diagnostics(test_name, _CURRENT_CLIENT)

    html_plugin = item.config.pluginmanager.getplugin("html")
    if html_plugin is None:
        return

    from pytest_html import extras as html_extras

    report_extras = list(getattr(report, "extras", []))

    screenshot_base64 = captured_artifacts.get("screenshot_base64")
    server_log_text = captured_artifacts.get("server_log_text")

    if screenshot_base64 or server_log_text or getattr(report, "longreprtext", ""):
        control_buttons: list[str] = []

        if screenshot_base64:
            control_buttons.append(
                """
                <button
                  type=\"button\"
                  class=\"report-section-toggle\"
                  onclick="const container=this.closest('td.extra'); const section=container && container.querySelector('.report-screenshot-panel'); if(!section){return;} const hidden=section.classList.toggle('report-section-hidden'); this.textContent=hidden ? 'Show Screenshot' : 'Hide Screenshot';"  # noqa: E501
                >Hide Screenshot</button>
                """.strip()
            )

        if server_log_text:
            control_buttons.append(
                """
                <button
                  type=\"button\"
                  class=\"report-section-toggle\"
                  onclick="const container=this.closest('td.extra'); const section=container && container.querySelector('.report-server-log'); if(!section){return;} const hidden=section.classList.toggle('report-section-hidden'); this.textContent=hidden ? 'Show Server Log' : 'Hide Server Log';"  # noqa: E501
                >Hide Server Log</button>
                """.strip()
            )

        if getattr(report, "longreprtext", ""):
            control_buttons.append(
                """
                <button
                  type=\"button\"
                  class=\"report-section-toggle\"
                  onclick="const container=this.closest('td.extra'); const section=container && container.querySelector('.logwrapper'); if(!section){return;} const hidden=section.classList.toggle('report-section-hidden'); this.textContent=hidden ? 'Show Error Details' : 'Hide Error Details';"  # noqa: E501
                >Hide Error Details</button>
                """.strip()
            )

        report_extras.append(
            html_extras.html(

                    '<div class="report-section-controls">'
                    + "".join(control_buttons)
                    + "</div>"

            )
        )

    if screenshot_base64:
        report_extras.append(
            html_extras.html(

                    '<div class="report-screenshot-panel">'
                    '<div class="report-screenshot-panel__title">Screenshot</div>'
                    '<div class="report-screenshot-frame">'
                    '<img class="report-screenshot-image" alt="Failure Screenshot" src="data:image/png;base64,'
                    + screenshot_base64
                    + '" />'
                    '</div>'
                    '</div>'

            )
        )

    if server_log_text:
        report_extras.append(
            html_extras.html(

                    '<div class="report-server-log">'
                    '<div class="report-server-log__title">Server Log</div>'
                    '<pre class="report-server-log__content">'
                    + html.escape(server_log_text)
                    + '</pre>'
                    '</div>'

            )
        )

    screenshot_file = captured_artifacts.get("screenshot_file")
    if screenshot_file:
        report_extras.append(
            html_extras.url(
                _relative_run_artifact_path(Path(screenshot_file)),
                name="Screenshot File",
            )
        )

    ui_dump = captured_artifacts.get("ui_dump")
    if ui_dump:
        report_extras.append(
            html_extras.url(
                _relative_run_artifact_path(Path(ui_dump)),
                name="UI Dump",
            )
        )

    server_log = captured_artifacts.get("server_log")
    if server_log:
        report_extras.append(
            html_extras.url(
                _relative_run_artifact_path(Path(server_log)),
                name="Server Log",
            )
        )

    report.extras = report_extras


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    del session
    _write_artifact_summary(exitstatus)
