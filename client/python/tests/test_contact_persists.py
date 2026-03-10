"""POM-based test — Contact persists after relaunch.

Equivalent of: e2e/workspaces/contacts/contact_persists.yaml

This test creates a contact using the add_contact flow as setup,
then cold-relaunches the app and verifies the contact is still visible.

Prerequisites:
  1. Android emulator running (adb devices shows device)
  2. Python deps installed (from client/python):
       python3 -m venv .venv && source .venv/bin/activate
       pip install -e ".[dev]"
  3. (Optional) Start maestro-runner server manually:
       ./maestro-runner --platform android server --port 9999
     If not running, the server is auto-started by the test fixture.

Override with env vars:
  MAESTRO_SERVER_URL   (default: http://localhost:9999)
  MAESTRO_PLATFORM     (default: android)
  MAESTRO_RUNNER_BIN   (path to binary, auto-detected by default)

Run:
  pytest tests/test_contact_persists.py -v
"""

from __future__ import annotations

import pytest
from maestro_runner import MaestroClient

from tests.pages.contact_list_page import ContactListPage


@pytest.fixture()
def contact_list(client: MaestroClient) -> ContactListPage:
    return ContactListPage(client)


class TestContactPersists:
    """Mirrors contact_persists.yaml: add contact → relaunch → verify."""

    def test_contact_persists_after_relaunch(self, contact_list: ContactListPage):
        # First create the contact (reuses the add_contact flow as setup)
        contact_list.launch(clear_state=True)
        edit_page = contact_list.open_create_contact()
        edit_page.set_first_name("Alice")
        edit_page.set_last_name("Tester")
        edit_page.set_phone("5550100")
        edit_page.save()
        contact_list.assert_contact_visible("Alice Tester")

        # Cold-relaunch the app
        contact_list.client.stop_app(ContactListPage.APP_ID)
        contact_list.launch(clear_state=False)

        # The contact must still be visible
        contact_list.assert_contact_visible("Alice Tester")
