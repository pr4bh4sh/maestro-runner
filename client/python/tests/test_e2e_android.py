"""End-to-end test against a running Android emulator.

Prerequisites:
  1. Android emulator running (adb devices shows device)
  2. maestro-runner server started:
       ./maestro-runner --platform android server --port 9999
  3. Python deps installed:
       pip install requests pytest

Run:
  pytest tests/test_e2e_android.py -v
"""

import os

import pytest
import requests

SERVER_URL = os.environ.get("MAESTRO_SERVER_URL", "http://localhost:9999")


@pytest.fixture(scope="module")
def session_id():
    """Create a session at module scope; delete it when done."""
    resp = requests.post(f"{SERVER_URL}/session", json={
        "platformName": "android",
    }, timeout=30)
    assert resp.status_code == 200, f"Failed to create session: {resp.text}"
    sid = resp.json()["sessionId"]
    yield sid
    requests.delete(f"{SERVER_URL}/session/{sid}")


def _execute(session_id: str, step: dict) -> dict:
    """Helper: execute a step and return the JSON result."""
    resp = requests.post(
        f"{SERVER_URL}/session/{session_id}/execute",
        json=step,
    )
    assert resp.status_code == 200, f"Execute failed ({resp.status_code}): {resp.text}"
    return resp.json()


# ---- Tests (run in order via pytest-ordering or alphabetical naming) ----


def test_01_server_status():
    """Server is reachable and healthy."""
    resp = requests.get(f"{SERVER_URL}/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_02_device_info(session_id):
    """Device info returns Android platform details."""
    resp = requests.get(f"{SERVER_URL}/session/{session_id}/device-info")
    assert resp.status_code == 200
    info = resp.json()
    assert info["platform"] == "android"
    assert info["isSimulator"] is True
    assert info["screenWidth"] > 0
    assert info["screenHeight"] > 0
    print(f"  Device: {info['deviceName']} (Android {info['osVersion']})")


def test_03_launch_settings(session_id):
    """Launch the Android Settings app."""
    result = _execute(session_id, {
        "type": "launchApp",
        "appId": "com.android.settings",
        "clearState": False,
    })
    assert result["success"] is True, f"Launch failed: {result.get('message')}"


def test_04_assert_settings_visible(session_id):
    """After launching Settings, the title should be visible."""
    result = _execute(session_id, {
        "type": "assertVisible",
        "selector": "Settings",
        "timeout": 10000,
    })
    assert result["success"] is True, f"Assert failed: {result.get('message')}"


def test_05_tap_search(session_id):
    """Tap on the search icon/bar in Settings."""
    result = _execute(session_id, {
        "type": "tapOn",
        "selector": {"id": "com.android.settings:id/search_action_bar_title"},
        "timeout": 5000,
    })
    # Allow failure if the ID changed on this Android version
    if not result["success"]:
        # Try text-based search as fallback
        result = _execute(session_id, {
            "type": "tapOn",
            "selector": "Search settings",
            "timeout": 5000,
        })
    assert result["success"] is True, f"Tap search failed: {result.get('message')}"


def test_06_input_text(session_id):
    """Type text into the search field."""
    # Tap the search edit text to ensure it's focused
    _execute(session_id, {
        "type": "tapOn",
        "selector": {"id": "com.android.settings:id/search_src_text"},
        "timeout": 5000,
    })
    result = _execute(session_id, {
        "type": "inputText",
        "text": "Display",
    })
    assert result["success"] is True, f"Input failed: {result.get('message')}"


def test_07_assert_search_result_visible(session_id):
    """After searching, a Display result should appear."""
    result = _execute(session_id, {
        "type": "assertVisible",
        "selector": "Display",
        "timeout": 10000,
    })
    assert result["success"] is True, f"Assert failed: {result.get('message')}"


def test_08_screenshot(session_id):
    """Take a screenshot and verify it returns PNG data."""
    resp = requests.get(f"{SERVER_URL}/session/{session_id}/screenshot")
    assert resp.status_code == 200
    assert resp.headers.get("Content-Type") == "image/png"
    # PNG magic bytes
    assert resp.content[:4] == b"\x89PNG", "Not valid PNG data"
    print(f"  Screenshot size: {len(resp.content)} bytes")


def test_09_view_hierarchy(session_id):
    """Fetch the view hierarchy."""
    resp = requests.get(f"{SERVER_URL}/session/{session_id}/source")
    assert resp.status_code == 200
    assert len(resp.content) > 100, "Hierarchy seems too small"


def test_10_press_back(session_id):
    """Press back to leave search."""
    result = _execute(session_id, {"type": "back"})
    assert result["success"] is True
