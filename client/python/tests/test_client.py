"""Unit tests for maestro_runner.client using requests-mock."""

import pytest
import requests_mock as rm
from maestro_runner.client import MaestroClient
from maestro_runner.exceptions import MaestroError, SessionError, StepError
from maestro_runner.models import ElementSelector

BASE = "http://localhost:9999"
SID = "test-session-123"


@pytest.fixture
def mock():
    """Provide a requests_mock adapter for the test."""
    with rm.Mocker() as m:
        yield m


@pytest.fixture
def mock_with_session(mock):
    """Register session create/delete and return the mock adapter."""
    mock.post(f"{BASE}/session", json={"sessionId": SID})
    mock.delete(f"{BASE}/session/{SID}", status_code=200)
    return mock


def _make_client(mock_adapter) -> MaestroClient:
    """Create a MaestroClient with a mocked session."""
    mock_adapter.post(f"{BASE}/session", json={"sessionId": SID})
    mock_adapter.delete(f"{BASE}/session/{SID}", status_code=200)
    return MaestroClient(BASE, capabilities={"platformName": "android"})


# ── Session management ───────────────────────────────────────────────────


class TestSessionManagement:
    def test_create_session(self, mock):
        mock.post(f"{BASE}/session", json={"sessionId": SID})
        client = MaestroClient(BASE, capabilities={"platformName": "android"})
        assert client.session_id == SID

    def test_create_session_failure(self, mock):
        mock.post(f"{BASE}/session", status_code=500, text="Internal error")
        with pytest.raises(SessionError, match="Failed to create session"):
            MaestroClient(BASE, capabilities={"platformName": "android"})

    def test_no_capabilities_no_session(self):
        client = MaestroClient(BASE)
        assert client.session_id is None

    def test_close_deletes_session(self, mock):
        mock.post(f"{BASE}/session", json={"sessionId": SID})
        mock.delete(f"{BASE}/session/{SID}", status_code=200)
        client = MaestroClient(BASE, capabilities={"platformName": "android"})
        client.close()
        assert client.session_id is None
        assert mock.last_request.method == "DELETE"

    def test_close_without_session_is_noop(self):
        client = MaestroClient(BASE)
        client.close()  # should not raise

    def test_context_manager(self, mock):
        mock.post(f"{BASE}/session", json={"sessionId": SID})
        mock.delete(f"{BASE}/session/{SID}", status_code=200)
        with MaestroClient(BASE, capabilities={"platformName": "android"}) as c:
            assert c.session_id == SID
        # after exiting, session should be cleaned up
        assert c.session_id is None

    def test_require_session_raises_without_session(self):
        client = MaestroClient(BASE)
        with pytest.raises(SessionError, match="No active session"):
            client.execute_step({"type": "back"})


# ── execute_step / _exec ─────────────────────────────────────────────────


class TestExecuteStep:
    def test_success(self, mock):
        client = _make_client(mock)
        mock.post(
            f"{BASE}/session/{SID}/execute",
            json={"success": True, "message": "ok"},
        )
        result = client.execute_step({"type": "back"})
        assert result.success is True
        assert result.message == "ok"

    def test_http_error(self, mock):
        client = _make_client(mock)
        mock.post(
            f"{BASE}/session/{SID}/execute",
            status_code=500,
            text="server error",
        )
        with pytest.raises(MaestroError, match="Execute failed"):
            client.execute_step({"type": "back"})

    def test_step_failure_raises_step_error(self, mock):
        client = _make_client(mock)
        mock.post(
            f"{BASE}/session/{SID}/execute",
            json={"success": False, "message": "element not found"},
        )
        with pytest.raises(StepError, match="element not found"):
            client.tap(text="Missing")

    def test_step_failure_no_raise_if_optional(self, mock):
        client = _make_client(mock)
        mock.post(
            f"{BASE}/session/{SID}/execute",
            json={"success": False, "message": "not found"},
        )
        result = client.tap(text="Maybe", optional=True)
        assert result.success is False


# ── App lifecycle commands ───────────────────────────────────────────────


class TestAppLifecycle:
    def test_launch_app(self, mock):
        client = _make_client(mock)
        mock.post(
            f"{BASE}/session/{SID}/execute",
            json={"success": True},
        )
        result = client.launch_app("com.example.app", clear_state=True)
        assert result.success is True
        body = mock.last_request.json()
        assert body["type"] == "launchApp"
        assert body["appId"] == "com.example.app"
        assert body["clearState"] is True

    def test_stop_app(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.stop_app("com.example.app")
        body = mock.last_request.json()
        assert body["type"] == "stopApp"
        assert body["appId"] == "com.example.app"

    def test_clear_state(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.clear_state("com.example.app")
        body = mock.last_request.json()
        assert body["type"] == "clearState"

    def test_open_link(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.open_link("https://example.com")
        body = mock.last_request.json()
        assert body["type"] == "openLink"
        assert body["link"] == "https://example.com"


# ── Tap commands ─────────────────────────────────────────────────────────


class TestTap:
    def test_tap_by_text(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.tap(text="Login")
        body = mock.last_request.json()
        assert body["type"] == "tapOn"
        assert body["selector"] == "Login"

    def test_tap_by_id(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.tap(id="btn_login")
        body = mock.last_request.json()
        assert body["selector"] == {"id": "btn_login"}

    def test_long_press(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.long_press(text="Hold")
        body = mock.last_request.json()
        assert body["longPress"] is True

    def test_tap_on_point(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.tap_on_point("50%,50%")
        body = mock.last_request.json()
        assert body["type"] == "tapOnPoint"
        assert body["point"] == "50%,50%"

    def test_tap_on_point_long_press(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.tap_on_point("100,200", long_press=True)
        body = mock.last_request.json()
        assert body["longPress"] is True

    def test_tap_with_selector_object(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        sel = ElementSelector(text="Item", child_of=ElementSelector(id="list"))
        client.tap(selector=sel)
        body = mock.last_request.json()
        assert body["selector"]["childOf"] == {"id": "list"}

    def test_tap_with_index_coerced_to_string(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.tap(text="Item", index=2)
        body = mock.last_request.json()
        assert body["selector"] == {"text": "Item", "index": "2"}

    def test_tap_with_boolean_selector_flags(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.tap(text="CB", enabled=True, checked=False)
        sel = mock.last_request.json()["selector"]
        assert sel["enabled"] is True
        assert sel["checked"] is False

    def test_tap_wait_until_visible(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.tap(text="Load", wait_until_visible=True)
        assert mock.last_request.json()["waitUntilVisible"] is True

    def test_tap_retry_if_no_change(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.tap(text="Retry", retry_if_no_change=False)
        assert mock.last_request.json()["retryTapIfNoChange"] is False


# ── Input commands ───────────────────────────────────────────────────────


class TestInput:
    def test_input_text(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.input_text("hello@example.com")
        body = mock.last_request.json()
        assert body["type"] == "inputText"
        assert body["text"] == "hello@example.com"

    def test_erase_text(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.erase_text(10)
        body = mock.last_request.json()
        assert body["type"] == "eraseText"
        assert body["charactersToErase"] == 10

    def test_erase_text_no_count(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.erase_text()
        body = mock.last_request.json()
        assert body == {"type": "eraseText"}


    def test_press_key(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.press_key("ENTER")
        body = mock.last_request.json()
        assert body["type"] == "pressKey"
        assert body["key"] == "ENTER"

    def test_back(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.back()
        body = mock.last_request.json()
        assert body["type"] == "back"


# ── Scroll / Swipe ───────────────────────────────────────────────────────


class TestScrollSwipe:
    def test_scroll(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.scroll()
        body = mock.last_request.json()
        assert body["type"] == "scroll"

    def test_swipe(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.swipe("left", duration_ms=600)
        body = mock.last_request.json()
        assert body["type"] == "swipe"
        assert body["direction"] == "LEFT"  # lowercase input uppercased
        assert body["duration"] == 600

    def test_swipe_default_duration(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.swipe("up")
        assert mock.last_request.json()["duration"] == 400

    def test_swipe_on_text(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.swipe_on(text="List", direction="DOWN")
        body = mock.last_request.json()
        assert body["type"] == "swipe"
        assert body["selector"] == {"text": "List"}
        assert body["direction"] == "DOWN"

    def test_swipe_on_id(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.swipe_on(id="scroll_view", direction="UP")
        body = mock.last_request.json()
        assert body["selector"] == {"id": "scroll_view"}


# ── Assertions ───────────────────────────────────────────────────────────


class TestAssertions:
    def test_assert_visible(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.assert_visible(text="Welcome")
        body = mock.last_request.json()
        assert body["type"] == "assertVisible"
        assert body["selector"] == "Welcome"

    def test_assert_visible_with_timeout(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.assert_visible(text="Loading", timeout_ms=5000)
        assert mock.last_request.json()["timeout"] == 5000

    def test_assert_not_visible(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.assert_not_visible(text="Error")
        body = mock.last_request.json()
        assert body["type"] == "assertNotVisible"
        assert body["selector"] == "Error"

    def test_element_exists_true(self, mock):
        client = _make_client(mock)
        mock.post(
            f"{BASE}/session/{SID}/execute",
            json={"success": True},
        )
        assert client.element_exists(text="Title") is True

    def test_element_exists_false(self, mock):
        client = _make_client(mock)
        mock.post(
            f"{BASE}/session/{SID}/execute",
            json={"success": False, "message": "not found"},
        )
        assert client.element_exists(text="Ghost") is False


# ── tap_first_match ──────────────────────────────────────────────────────


class TestTapFirstMatch:
    def test_first_selector_matches(self, mock):
        client = _make_client(mock)
        mock.post(
            f"{BASE}/session/{SID}/execute",
            json={"success": True},
        )
        result = client.tap_first_match(
            [{"selector": "Create contact"}, {"selector": "Add contact"}],
            step="create",
        )
        assert result.success is True

    def test_second_selector_matches(self, mock):
        client = _make_client(mock)
        responses = [
            {"json": {"success": False, "message": "miss"}},
            {"json": {"success": True, "message": "hit"}},
        ]
        mock.post(f"{BASE}/session/{SID}/execute", responses)
        result = client.tap_first_match(
            [{"selector": "Nope"}, {"selector": "Found"}],
        )
        assert result.success is True
        assert result.message == "hit"

    def test_no_match_raises(self, mock):
        client = _make_client(mock)
        mock.post(
            f"{BASE}/session/{SID}/execute",
            json={"success": False, "message": "miss"},
        )
        with pytest.raises(StepError, match="none of 2 selectors matched"):
            client.tap_first_match(
                [{"selector": "A"}, {"selector": "B"}],
                step="test",
            )

    def test_empty_selectors_raises(self, mock):
        client = _make_client(mock)
        with pytest.raises(StepError, match="no selectors provided"):
            client.tap_first_match([])


# ── Device queries ───────────────────────────────────────────────────────


class TestDeviceQueries:
    def test_device_info(self, mock):
        client = _make_client(mock)
        mock.get(
            f"{BASE}/session/{SID}/device-info",
            json={
                "platform": "android",
                "osVersion": "14",
                "deviceName": "Pixel 6",
                "deviceId": "emulator-5554",
                "isSimulator": True,
                "screenWidth": 1080,
                "screenHeight": 2400,
                "appId": "",
            },
        )
        info = client.device_info()
        assert info.platform == "android"
        assert info.screen_width == 1080

    def test_device_info_error(self, mock):
        client = _make_client(mock)
        mock.get(
            f"{BASE}/session/{SID}/device-info",
            status_code=500,
            text="fail",
        )
        with pytest.raises(MaestroError, match="device-info failed"):
            client.device_info()

    def test_screenshot(self, mock):
        client = _make_client(mock)
        mock.get(
            f"{BASE}/session/{SID}/screenshot",
            content=b"\x89PNG fake image data",
        )
        data = client.screenshot()
        assert data == b"\x89PNG fake image data"

    def test_screenshot_error(self, mock):
        client = _make_client(mock)
        mock.get(
            f"{BASE}/session/{SID}/screenshot",
            status_code=500,
            text="fail",
        )
        with pytest.raises(MaestroError, match="screenshot failed"):
            client.screenshot()

    def test_view_hierarchy(self, mock):
        client = _make_client(mock)
        xml = "<hierarchy><node text='Hello'/></hierarchy>"
        mock.get(
            f"{BASE}/session/{SID}/source",
            text=xml,
        )
        assert client.view_hierarchy() == xml

    def test_view_hierarchy_error(self, mock):
        client = _make_client(mock)
        mock.get(
            f"{BASE}/session/{SID}/source",
            status_code=500,
            text="fail",
        )
        with pytest.raises(MaestroError, match="source failed"):
            client.view_hierarchy()


# ── waitForAnimationToEnd ────────────────────────────────────────────────


class TestWaitForAnimationToEnd:
    def test_default_params(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.wait_for_animation_to_end()
        body = mock.last_request.json()
        assert body["type"] == "waitForAnimationToEnd"
        assert "sleepMs" not in body
        assert "threshold" not in body

    def test_with_sleep_ms_and_threshold(self, mock):
        client = _make_client(mock)
        mock.post(f"{BASE}/session/{SID}/execute", json={"success": True})
        client.wait_for_animation_to_end(sleep_ms=500, threshold=0.001)
        body = mock.last_request.json()
        assert body["type"] == "waitForAnimationToEnd"
        assert body["sleepMs"] == 500
        assert body["threshold"] == 0.001
