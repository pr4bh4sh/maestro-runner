"""Page Object — iOS Contacts app: contact list screen."""

from __future__ import annotations

from maestro_runner.models import ExecutionResult

from tests.pages import BasePage
from tests.pages.ios_edit_contact_page import IOSContactEditPage


class IOSContactListPage(BasePage):
    """The iOS Contacts list screen."""

    APP_ID = "com.apple.MobileAddressBook"

    def launch(self) -> ExecutionResult:
        result = self.client.launch_app(self.APP_ID, stop_app=True)
        self.wait_for_animation()
        return result

    def open_create_contact(self) -> IOSContactEditPage:
        self.client.tap(text="Add")
        self.wait_for_animation()
        return IOSContactEditPage(self.client)

    def assert_contact_visible(self, name: str) -> ExecutionResult:
        return self.client.assert_visible(text=name)
