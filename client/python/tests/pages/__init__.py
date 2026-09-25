"""Page Object Model — base page with common helpers."""

from __future__ import annotations

from maestro_runner.client import MaestroClient
from maestro_runner.models import ExecutionResult


class BasePage:
    """Shared helpers available to every page object."""

    def __init__(self, client: MaestroClient) -> None:
        self.client = client

    def wait_for_animation(self) -> ExecutionResult:
        return self.client.wait_for_animation_to_end()

    def hide_keyboard(self, strategy: str | None = None) -> ExecutionResult:
        return self.client.hide_keyboard(strategy=strategy)
