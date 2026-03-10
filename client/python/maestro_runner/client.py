"""MaestroClient — main client class for maestro-runner REST API."""

from __future__ import annotations

import logging
from typing import Any

import requests

from maestro_runner import commands
from maestro_runner.exceptions import MaestroError, SessionError, StepError
from maestro_runner.models import DeviceInfo, ElementSelector, ExecutionResult

logger = logging.getLogger("maestro_runner")


class MaestroClient:
    """Client for the maestro-runner REST server.

    Usage::

        with MaestroClient("http://localhost:9999",
                           capabilities={"platformName": "android"}) as c:
            c.tap(text="Login")
            c.input_text("user@example.com")
    """

    def __init__(
        self,
        base_url: str = "http://localhost:9999",
        capabilities: dict[str, Any] | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session_id: str | None = None

        if capabilities:
            self._create_session(capabilities)

    # --- Context manager ---

    def __enter__(self) -> MaestroClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def close(self) -> None:
        """Delete the server session and release resources."""
        if self._session_id:
            try:
                self._session.delete(
                    f"{self.base_url}/session/{self._session_id}",
                    timeout=self.timeout,
                )
            except requests.RequestException:
                pass
            self._session_id = None

    # --- Session management ---

    def _create_session(self, capabilities: dict[str, Any]) -> None:
        resp = self._session.post(
            f"{self.base_url}/session",
            json=capabilities,
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            raise SessionError(
                f"Failed to create session: {resp.text}",
                status_code=resp.status_code,
            )
        data = resp.json()
        self._session_id = data["sessionId"]
        logger.info("Session created: %s", self._session_id)

    @property
    def session_id(self) -> str | None:
        return self._session_id

    def _require_session(self) -> str:
        if not self._session_id:
            raise SessionError(
                "No active session. Pass capabilities to __init__ or call close() first."
            )
        return self._session_id

    # --- Low-level ---

    def execute_step(self, step: dict[str, Any]) -> ExecutionResult:
        """Execute a raw step dict via POST /session/{id}/execute."""
        sid = self._require_session()
        resp = self._session.post(
            f"{self.base_url}/session/{sid}/execute",
            json=step,
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            raise MaestroError(f"Execute failed: {resp.text}", status_code=resp.status_code)
        return ExecutionResult.from_dict(resp.json())

    def _exec(self, step: dict[str, Any]) -> ExecutionResult:
        """Execute a step, raising StepError on failure unless optional."""
        result = self.execute_step(step)
        if not result.success and not step.get("optional", False):
            raise StepError(result.message or "step failed")
        return result

    # --- App lifecycle ---

    def launch_app(
        self,
        app_id: str,
        *,
        clear_state: bool | None = None,
        stop_app: bool | None = None,
        label: str | None = None,
    ) -> ExecutionResult:
        return self._exec(
            commands.launch_app(app_id, clear_state=clear_state, stop_app=stop_app, label=label)
        )

    def stop_app(self, app_id: str, *, label: str | None = None) -> ExecutionResult:
        return self._exec(commands.stop_app(app_id, label=label))

    def clear_state(self, app_id: str, *, label: str | None = None) -> ExecutionResult:
        return self._exec(commands.clear_state(app_id, label=label))

    def open_link(self, link: str, *, label: str | None = None) -> ExecutionResult:
        return self._exec(commands.open_link(link, label=label))

    # --- Tap ---

    def tap(
        self,
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
        label: str | None = None,
    ) -> ExecutionResult:
        return self._exec(commands.tap_on(
            text=text, id=id, index=index, selector=selector,
            long_press=long_press, wait_until_visible=wait_until_visible,
            retry_if_no_change=retry_if_no_change,
            enabled=enabled, checked=checked, focused=focused, selected=selected,
            optional=optional, label=label,
        ))

    def long_press(
        self,
        *,
        text: str | None = None,
        id: str | None = None,
        selector: ElementSelector | None = None,
        label: str | None = None,
    ) -> ExecutionResult:
        return self._exec(
            commands.tap_on(text=text, id=id, selector=selector, long_press=True, label=label)
        )

    def tap_on_point(
        self, point: str, *, long_press: bool = False, label: str | None = None
    ) -> ExecutionResult:
        step: dict[str, Any] = {"type": "tapOnPoint", "point": point}
        if long_press:
            step["longPress"] = True
        if label:
            step["label"] = label
        return self._exec(step)

    # --- Input ---

    def input_text(self, text: str, *, label: str | None = None) -> ExecutionResult:
        return self._exec(commands.input_text(text, label=label))

    def erase_text(
        self, characters: int | None = None, *, label: str | None = None
    ) -> ExecutionResult:
        return self._exec(commands.erase_text(characters, label=label))

    def press_key(self, code: str, *, label: str | None = None) -> ExecutionResult:
        return self._exec(commands.press_key(code, label=label))

    def back(self, *, label: str | None = None) -> ExecutionResult:
        return self._exec(commands.back(label=label))

    def hide_keyboard(
        self, *, strategy: str | None = None, label: str | None = None
    ) -> ExecutionResult:
        return self._exec(commands.hide_keyboard(strategy=strategy, label=label))

    def wait_for_animation_to_end(self, *, label: str | None = None) -> ExecutionResult:
        return self._exec(commands.wait_for_animation_to_end(label=label))

    # --- Scroll / Swipe ---

    def scroll(self, *, label: str | None = None) -> ExecutionResult:
        return self._exec(commands.scroll(label=label))

    def swipe(
        self, direction: str, *, duration_ms: int = 400, label: str | None = None
    ) -> ExecutionResult:
        return self._exec(commands.swipe(direction, duration_ms=duration_ms, label=label))

    def swipe_on(
        self,
        *,
        text: str | None = None,
        id: str | None = None,
        direction: str = "UP",
        duration_ms: int = 400,
        label: str | None = None,
    ) -> ExecutionResult:
        step: dict[str, Any] = {
            "type": "swipe",
            "direction": direction.upper(),
            "duration": duration_ms,
        }
        if text is not None:
            step["selector"] = {"text": text}
        elif id is not None:
            step["selector"] = {"id": id}
        if label:
            step["label"] = label
        return self._exec(step)

    # --- Assertions ---

    def assert_visible(
        self,
        *,
        text: str | None = None,
        id: str | None = None,
        selector: ElementSelector | None = None,
        timeout_ms: int | None = None,
        label: str | None = None,
    ) -> ExecutionResult:
        return self._exec(commands.assert_visible(
            text=text, id=id, selector=selector, timeout_ms=timeout_ms, label=label,
        ))

    def assert_not_visible(
        self,
        *,
        text: str | None = None,
        id: str | None = None,
        selector: ElementSelector | None = None,
        timeout_ms: int | None = None,
        label: str | None = None,
    ) -> ExecutionResult:
        return self._exec(commands.assert_not_visible(
            text=text, id=id, selector=selector, timeout_ms=timeout_ms, label=label,
        ))

    def element_exists(self, *, text: str | None = None, id: str | None = None) -> bool:
        """Check if an element exists without raising. Returns bool."""
        step = commands.assert_visible(text=text, id=id, optional=True)
        result = self.execute_step(step)
        return result.success

    # --- Self-healing multi-selector tap ---

    def tap_first_match(
        self, selectors: list[dict[str, Any]], *, step: str = ""
    ) -> ExecutionResult:
        """Try each selector in order; return on the first successful tap."""
        last_result = None
        for sel in selectors:
            tap_step = {"type": "tapOn", "optional": True}
            tap_step.update(sel)
            result = self.execute_step(tap_step)
            if result.success:
                logger.info("tap_first_match: matched selector %s (step=%s)", sel, step)
                return result
            last_result = result
        if last_result is None:
            raise StepError("tap_first_match: no selectors provided")
        raise StepError(
            f"tap_first_match: none of {len(selectors)} selectors matched (step={step})"
        )

    # --- Device queries ---

    def device_info(self) -> DeviceInfo:
        sid = self._require_session()
        resp = self._session.get(
            f"{self.base_url}/session/{sid}/device-info",
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            raise MaestroError(f"device-info failed: {resp.text}", status_code=resp.status_code)
        return DeviceInfo.from_dict(resp.json())

    def screenshot(self) -> bytes:
        sid = self._require_session()
        resp = self._session.get(
            f"{self.base_url}/session/{sid}/screenshot",
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            raise MaestroError(f"screenshot failed: {resp.text}", status_code=resp.status_code)
        return resp.content

    def view_hierarchy(self) -> str:
        sid = self._require_session()
        resp = self._session.get(
            f"{self.base_url}/session/{sid}/source",
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            raise MaestroError(f"source failed: {resp.text}", status_code=resp.status_code)
        return resp.text
