"""POM-based test — Add a new contact.

Equivalent of: e2e/workspaces/contacts/add_contact_android.yaml

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
  pytest tests/test_add_contact.py -v
"""

from __future__ import annotations

import pytest
from maestro_runner import MaestroClient

from tests.pages.contact_list_page import ContactListPage


@pytest.fixture()
def contact_list(client: MaestroClient) -> ContactListPage:
    return ContactListPage(client)


class TestAddContact:
    """Mirrors add_contact_android.yaml: launch → create → fill → save → verify."""

    def test_add_and_verify_contact(self, contact_list: ContactListPage):
        # Launch with a clean slate
        contact_list.launch(clear_state=True)

        # Open the create-contact form
        edit_page = contact_list.open_create_contact()

        # Fill in name fields
        edit_page.set_first_name("Alice")
        edit_page.set_last_name("Tester")

        # Fill in phone number
        edit_page.set_phone("5550100")

        # Save
        edit_page.save()

        # Verify the contact now appears in the list
        contact_list.assert_contact_visible("Alice Tester")
