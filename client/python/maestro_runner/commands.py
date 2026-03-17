"""Command builders — produce Go step JSON for the REST API."""

from __future__ import annotations

from typing import Any

from maestro_runner.models import ElementSelector


def _selector_value(
    *,
    text: str | None = None,
    id: str | None = None,
    index: int | None = None,
    selector: ElementSelector | None = None,
    enabled: bool | None = None,
    checked: bool | None = None,
    focused: bool | None = None,
    selected: bool | None = None,
) -> str | dict[str, Any]:
    """Build a selector value (string for text-only, object otherwise)."""
    d: dict[str, Any] = {}
    if selector is not None:
        d.update(selector.to_dict())
    if text is not None:
        d["text"] = text
    if id is not None:
        d["id"] = id
    if index is not None:
        d["index"] = str(index)
    if enabled is not None:
        d["enabled"] = enabled
    if checked is not None:
        d["checked"] = checked
    if focused is not None:
        d["focused"] = focused
    if selected is not None:
        d["selected"] = selected
    # Compact form: text-only selector → plain string
    if list(d.keys()) == ["text"]:
        return str(d["text"])
    return d


def tap_on(
    *,
    text: str | None = None,
    id: str | None = None,
    index: int | None = None,
    selector: ElementSelector | None = None,
    long_press: bool = False,
    wait_until_visible: bool | None = None,
    retry_if_no_change: bool | None = None,
    enabled: bool | None = None,
    checked: bool | None = None,
    focused: bool | None = None,
    selected: bool | None = None,
    optional: bool = False,
    timeout: int | None = None,
    label: str | None = None,
) -> dict[str, Any]:
    step: dict[str, Any] = {"type": "tapOn"}
    step["selector"] = _selector_value(
        text=text, id=id, index=index, selector=selector,
        enabled=enabled, checked=checked, focused=focused, selected=selected,
    )
    if long_press:
        step["longPress"] = True
    if wait_until_visible is not None:
        step["waitUntilVisible"] = wait_until_visible
    if retry_if_no_change is not None:
        step["retryTapIfNoChange"] = retry_if_no_change
    if optional:
        step["optional"] = True
    if timeout is not None:
        step["timeout"] = timeout
    if label is not None:
        step["label"] = label
    return step


def input_text(text: str, *, label: str | None = None) -> dict[str, Any]:
    step: dict[str, Any] = {"type": "inputText", "text": text}
    if label is not None:
        step["label"] = label
    return step


def erase_text(characters: int | None = None, *, label: str | None = None) -> dict[str, Any]:
    step: dict[str, Any] = {"type": "eraseText"}
    if characters is not None:
        step["charactersToErase"] = characters
    if label is not None:
        step["label"] = label
    return step


def press_key(code: str, *, label: str | None = None) -> dict[str, Any]:
    step: dict[str, Any] = {"type": "pressKey", "key": code}
    if label is not None:
        step["label"] = label
    return step


def back(*, label: str | None = None) -> dict[str, Any]:
    step: dict[str, Any] = {"type": "back"}
    if label is not None:
        step["label"] = label
    return step


def scroll(*, label: str | None = None) -> dict[str, Any]:
    step: dict[str, Any] = {"type": "scroll"}
    if label is not None:
        step["label"] = label
    return step


def swipe(direction: str, *, duration_ms: int = 400, label: str | None = None) -> dict[str, Any]:
    step: dict[str, Any] = {
        "type": "swipe",
        "direction": direction.upper(),
        "duration": duration_ms,
    }
    if label is not None:
        step["label"] = label
    return step


def assert_visible(
    *,
    text: str | None = None,
    id: str | None = None,
    selector: ElementSelector | None = None,
    timeout_ms: int | None = None,
    optional: bool = False,
    label: str | None = None,
) -> dict[str, Any]:
    step: dict[str, Any] = {"type": "assertVisible"}
    step["selector"] = _selector_value(text=text, id=id, selector=selector)
    if timeout_ms is not None:
        step["timeout"] = timeout_ms
    if optional:
        step["optional"] = True
    if label is not None:
        step["label"] = label
    return step


def assert_not_visible(
    *,
    text: str | None = None,
    id: str | None = None,
    selector: ElementSelector | None = None,
    timeout_ms: int | None = None,
    label: str | None = None,
) -> dict[str, Any]:
    step: dict[str, Any] = {"type": "assertNotVisible"}
    step["selector"] = _selector_value(text=text, id=id, selector=selector)
    if timeout_ms is not None:
        step["timeout"] = timeout_ms
    if label is not None:
        step["label"] = label
    return step


def launch_app(
    app_id: str,
    *,
    clear_state: bool | None = None,
    stop_app: bool | None = None,
    label: str | None = None,
) -> dict[str, Any]:
    step: dict[str, Any] = {"type": "launchApp", "appId": app_id}
    if clear_state is not None:
        step["clearState"] = clear_state
    if stop_app is not None:
        step["stopApp"] = stop_app
    if label is not None:
        step["label"] = label
    return step


def stop_app(app_id: str, *, label: str | None = None) -> dict[str, Any]:
    step: dict[str, Any] = {"type": "stopApp", "appId": app_id}
    if label is not None:
        step["label"] = label
    return step


def clear_state(app_id: str, *, label: str | None = None) -> dict[str, Any]:
    step: dict[str, Any] = {"type": "clearState", "appId": app_id}
    if label is not None:
        step["label"] = label
    return step


def open_link(link: str, *, label: str | None = None) -> dict[str, Any]:
    step: dict[str, Any] = {"type": "openLink", "link": link}
    if label is not None:
        step["label"] = label
    return step


def hide_keyboard(*, strategy: str | None = None, label: str | None = None) -> dict[str, Any]:
    step: dict[str, Any] = {"type": "hideKeyboard"}
    if strategy is not None:
        step["strategy"] = strategy
    if label is not None:
        step["label"] = label
    return step


def wait_for_animation_to_end(
    *,
    sleep_ms: int | None = None,
    threshold: float | None = None,
    label: str | None = None,
) -> dict[str, Any]:
    """Build a waitForAnimationToEnd step.

    Args:
        sleep_ms:  Milliseconds to pause between the two comparison screenshots.
                   Longer values catch slow-moving animations.  Defaults to 200 ms
                   on the server side.
        threshold: Maximum pixel-diff percentage (0.0-1.0) still considered static.
                   Lower is stricter.  Defaults to 0.005 (0.5 %) on the server side.
        label:     Optional step label shown in reports.
    """
    step: dict[str, Any] = {"type": "waitForAnimationToEnd"}
    if sleep_ms is not None:
        step["sleepMs"] = sleep_ms
    if threshold is not None:
        step["threshold"] = threshold
    if label is not None:
        step["label"] = label
    return step
