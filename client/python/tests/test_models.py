"""Unit tests for maestro_runner.models."""

from maestro_runner.models import DeviceInfo, ElementInfo, ElementSelector, ExecutionResult

# ── ElementSelector ──────────────────────────────────────────────────────


class TestElementSelector:
    def test_to_dict_text_only(self):
        sel = ElementSelector(text="Hello")
        assert sel.to_dict() == {"text": "Hello"}

    def test_to_dict_id_only(self):
        sel = ElementSelector(id="btn_login")
        assert sel.to_dict() == {"id": "btn_login"}

    def test_to_dict_index_as_string(self):
        sel = ElementSelector(index=3)
        assert sel.to_dict() == {"index": "3"}

    def test_to_dict_boolean_flags(self):
        sel = ElementSelector(enabled=True, checked=False, focused=True, selected=False)
        d = sel.to_dict()
        assert d == {"enabled": True, "checked": False, "focused": True, "selected": False}

    def test_to_dict_css_and_traits(self):
        sel = ElementSelector(css=".btn", traits="button")
        assert sel.to_dict() == {"css": ".btn", "traits": "button"}

    def test_to_dict_nested_child_of(self):
        parent = ElementSelector(id="list")
        child = ElementSelector(text="Item 1", child_of=parent)
        d = child.to_dict()
        assert d == {"text": "Item 1", "childOf": {"id": "list"}}

    def test_to_dict_all_relative_selectors(self):
        ref = ElementSelector(text="Ref")
        sel = ElementSelector(
            text="Target",
            below=ref,
            above=ref,
            left_of=ref,
            right_of=ref,
            contains_child=ref,
            inside_of=ref,
        )
        d = sel.to_dict()
        assert d["text"] == "Target"
        for key in ("below", "above", "leftOf", "rightOf", "containsChild", "insideOf"):
            assert d[key] == {"text": "Ref"}

    def test_to_dict_empty(self):
        sel = ElementSelector()
        assert sel.to_dict() == {}

    def test_to_dict_combined_text_and_id(self):
        sel = ElementSelector(text="Login", id="btn_login")
        d = sel.to_dict()
        assert d == {"text": "Login", "id": "btn_login"}


# ── ElementInfo ──────────────────────────────────────────────────────────


class TestElementInfo:
    def test_from_dict_full(self):
        data = {
            "id": "btn1",
            "text": "OK",
            "bounds": {"x": 10, "y": 20, "width": 100, "height": 50},
            "visible": True,
            "enabled": True,
            "focused": False,
            "checked": True,
            "selected": False,
        }
        elem = ElementInfo.from_dict(data)
        assert elem is not None
        assert elem.id == "btn1"
        assert elem.text == "OK"
        assert elem.bounds == {"x": 10, "y": 20, "width": 100, "height": 50}
        assert elem.visible is True
        assert elem.enabled is True
        assert elem.focused is False
        assert elem.checked is True
        assert elem.selected is False

    def test_from_dict_none_returns_none(self):
        assert ElementInfo.from_dict(None) is None

    def test_from_dict_empty(self):
        elem = ElementInfo.from_dict({})
        assert elem is not None
        assert elem.id == ""
        assert elem.text == ""
        assert elem.bounds == {}
        assert elem.visible is False

    def test_from_dict_partial(self):
        elem = ElementInfo.from_dict({"text": "hello", "visible": True})
        assert elem is not None
        assert elem.text == "hello"
        assert elem.visible is True
        assert elem.id == ""


# ── ExecutionResult ──────────────────────────────────────────────────────


class TestExecutionResult:
    def test_from_dict_success(self):
        data = {"success": True, "message": "done", "duration": 1234}
        r = ExecutionResult.from_dict(data)
        assert r.success is True
        assert r.message == "done"
        assert r.duration_ns == 1234

    def test_from_dict_failure(self):
        data = {"success": False, "message": "not found"}
        r = ExecutionResult.from_dict(data)
        assert r.success is False
        assert r.message == "not found"
        assert r.duration_ns == 0

    def test_from_dict_with_element(self):
        data = {
            "success": True,
            "element": {"id": "e1", "text": "Hello", "visible": True},
        }
        r = ExecutionResult.from_dict(data)
        assert r.element is not None
        assert r.element.id == "e1"
        assert r.element.text == "Hello"

    def test_from_dict_with_data(self):
        data = {"success": True, "data": {"key": "value"}}
        r = ExecutionResult.from_dict(data)
        assert r.data == {"key": "value"}

    def test_from_dict_minimal(self):
        r = ExecutionResult.from_dict({})
        assert r.success is False
        assert r.message is None
        assert r.element is None
        assert r.data is None


# ── DeviceInfo ───────────────────────────────────────────────────────────


class TestDeviceInfo:
    def test_from_dict_full(self):
        data = {
            "platform": "android",
            "osVersion": "14",
            "deviceName": "Pixel 6",
            "deviceId": "emulator-5554",
            "isSimulator": True,
            "screenWidth": 1080,
            "screenHeight": 2400,
            "appId": "com.example.app",
        }
        info = DeviceInfo.from_dict(data)
        assert info.platform == "android"
        assert info.os_version == "14"
        assert info.device_name == "Pixel 6"
        assert info.device_id == "emulator-5554"
        assert info.is_simulator is True
        assert info.screen_width == 1080
        assert info.screen_height == 2400
        assert info.app_id == "com.example.app"

    def test_from_dict_empty(self):
        info = DeviceInfo.from_dict({})
        assert info.platform == ""
        assert info.os_version == ""
        assert info.screen_width == 0
        assert info.is_simulator is False

    def test_from_dict_partial(self):
        info = DeviceInfo.from_dict({"platform": "ios", "screenWidth": 390})
        assert info.platform == "ios"
        assert info.screen_width == 390
        assert info.device_name == ""
