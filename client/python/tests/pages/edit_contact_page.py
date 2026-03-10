"""Page Object — Contacts app: create / edit contact form."""

from __future__ import annotations

from maestro_runner.models import ExecutionResult

from tests.pages import BasePage


class EditContactPage(BasePage):
    """The new-contact / edit-contact form."""

    def set_first_name(self, name: str) -> None:
        self.client.tap(text="First name")
        self.client.input_text(name)
        self.hide_keyboard()

    def set_last_name(self, name: str) -> None:
        self.client.tap(text="Last name")
        self.client.input_text(name)
        self.hide_keyboard(strategy="escape")

    def set_phone(self, number: str) -> None:
        self.wait_for_animation()
        self.client.tap(text="Phone (Mobile)|Add phone")
        self.client.input_text(number)
        self.hide_keyboard(strategy="back")

    def save(self) -> ExecutionResult:
        result = self.client.tap(text="Save")
        self.wait_for_animation()
        return result
