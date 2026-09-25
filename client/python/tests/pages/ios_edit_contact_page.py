"""Page Object — iOS Contacts app: create / edit contact form."""

from __future__ import annotations

from maestro_runner.models import ExecutionResult

from tests.pages import BasePage


class IOSContactEditPage(BasePage):
    """The iOS new-contact form."""

    def set_first_name(self, name: str) -> None:
        self.client.tap(text="First name")
        self.client.input_text(name)

    def set_last_name(self, name: str) -> None:
        self.client.tap(text="Last name")
        self.client.input_text(name)

    def set_phone(self, number: str) -> None:
        self.wait_for_animation()
        self.client.execute_step(
            {"type": "swipe", "start": "50%, 42%", "end": "50%, 12%", "duration": 400}
        )
        self.client.tap(text="add phone")
        self.client.tap(text="phone")
        self.client.input_text(number)

    def save(self) -> ExecutionResult:
        result = self.client.tap(text="Done")
        self.wait_for_animation()
        return result
