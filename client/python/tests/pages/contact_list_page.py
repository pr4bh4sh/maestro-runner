"""Page Object — Contacts app: contact list screen."""

from __future__ import annotations

from maestro_runner.models import ExecutionResult

from tests.pages import BasePage
from tests.pages.edit_contact_page import EditContactPage


class ContactListPage(BasePage):
    """The main Contacts list screen."""

    APP_ID = "com.google.android.contacts"

    def launch(self, clear_state: bool = True) -> ExecutionResult:
        result = self.client.launch_app(self.APP_ID, clear_state=clear_state)
        self.wait_for_animation()
        return result

    def open_create_contact(self) -> EditContactPage:

        self.client.tap(text="Create contact|Add contact|New contact")
        self.wait_for_animation()
        return EditContactPage(self.client)

    def assert_contact_visible(self, name: str) -> ExecutionResult:
        return self.client.assert_visible(text=name)
