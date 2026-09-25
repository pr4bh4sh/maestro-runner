"""Data models mapping Go server JSON responses to Python dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ElementSelector:
    """Element selection criteria — maps to Go flow.Selector."""

    text: str | None = None
    id: str | None = None
    index: int | None = None
    enabled: bool | None = None
    checked: bool | None = None
    focused: bool | None = None
    selected: bool | None = None
    css: str | None = None
    traits: str | None = None
    child_of: ElementSelector | None = None
    below: ElementSelector | None = None
    above: ElementSelector | None = None
    left_of: ElementSelector | None = None
    right_of: ElementSelector | None = None
    contains_child: ElementSelector | None = None
    inside_of: ElementSelector | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-compatible dict for the Go server."""
        d: dict[str, Any] = {}
        if self.text is not None:
            d["text"] = self.text
        if self.id is not None:
            d["id"] = self.id
        if self.index is not None:
            d["index"] = str(self.index)
        if self.enabled is not None:
            d["enabled"] = self.enabled
        if self.checked is not None:
            d["checked"] = self.checked
        if self.focused is not None:
            d["focused"] = self.focused
        if self.selected is not None:
            d["selected"] = self.selected
        if self.css is not None:
            d["css"] = self.css
        if self.traits is not None:
            d["traits"] = self.traits
        if self.child_of is not None:
            d["childOf"] = self.child_of.to_dict()
        if self.below is not None:
            d["below"] = self.below.to_dict()
        if self.above is not None:
            d["above"] = self.above.to_dict()
        if self.left_of is not None:
            d["leftOf"] = self.left_of.to_dict()
        if self.right_of is not None:
            d["rightOf"] = self.right_of.to_dict()
        if self.contains_child is not None:
            d["containsChild"] = self.contains_child.to_dict()
        if self.inside_of is not None:
            d["insideOf"] = self.inside_of.to_dict()
        return d


@dataclass
class ElementInfo:
    """UI element information — maps to Go core.ElementInfo."""

    id: str = ""
    text: str = ""
    bounds: dict[str, int] = field(default_factory=dict)
    visible: bool = False
    enabled: bool = False
    focused: bool = False
    checked: bool = False
    selected: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ElementInfo | None:
        if data is None:
            return None
        return cls(
            id=data.get("id", ""),
            text=data.get("text", ""),
            bounds=data.get("bounds", {}),
            visible=data.get("visible", False),
            enabled=data.get("enabled", False),
            focused=data.get("focused", False),
            checked=data.get("checked", False),
            selected=data.get("selected", False),
        )


@dataclass
class ExecutionResult:
    """Step execution result — maps to Go core.CommandResult."""

    success: bool
    message: str | None = None
    duration_ns: int = 0
    element: ElementInfo | None = None
    data: Any = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionResult:
        return cls(
            success=data.get("success", False),
            message=data.get("message"),
            duration_ns=data.get("duration", 0),
            element=ElementInfo.from_dict(data.get("element")),
            data=data.get("data"),
        )


@dataclass
class DeviceInfo:
    """Device/platform information — maps to Go core.PlatformInfo."""

    platform: str = ""
    os_version: str = ""
    device_name: str = ""
    device_id: str = ""
    is_simulator: bool = False
    screen_width: int = 0
    screen_height: int = 0
    app_id: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceInfo:
        return cls(
            platform=data.get("platform", ""),
            os_version=data.get("osVersion", ""),
            device_name=data.get("deviceName", ""),
            device_id=data.get("deviceId", ""),
            is_simulator=data.get("isSimulator", False),
            screen_width=data.get("screenWidth", 0),
            screen_height=data.get("screenHeight", 0),
            app_id=data.get("appId", ""),
        )
