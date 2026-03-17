"""POM-based test — Add a new contact on iOS.

Equivalent of: e2e/workspaces/contacts/add_contact_ios.yaml

Prerequisites:
  1. iOS simulator running
  2. Python deps installed (from client/python):
       python3 -m venv .venv && source .venv/bin/activate
       pip install -e ".[dev]"
  3. (Optional) Start maestro-runner server manually:
       ./maestro-runner --platform ios --device <UDID> server --port 9999
     If not running, the server is auto-started by the test fixture.

Override with env vars:
  MAESTRO_SERVER_URL   (default: http://localhost:9999)
  MAESTRO_PLATFORM     (set to: ios)
  MAESTRO_DEVICE_ID    (recommended for explicit simulator targeting)
  MAESTRO_RUNNER_BIN   (path to binary, auto-detected by default)

Run:
  MAESTRO_PLATFORM=ios pytest tests/test_add_contact_ios.py -v
"""

from __future__ import annotations

import pytest
from maestro_runner import MaestroClient

from tests.pages.ios_contact_list_page import IOSContactListPage


@pytest.fixture()
def contact_list(client: MaestroClient) -> IOSContactListPage:
    return IOSContactListPage(client)


class TestAddContactIOS:
    """Mirrors add_contact_ios.yaml: launch → create → fill → save → verify."""

    def test_add_and_verify_contact(self, contact_list: IOSContactListPage):
        contact_list.launch()

        edit_page = contact_list.open_create_contact()
        edit_page.set_first_name("Alice")
        edit_page.set_last_name("Tester")
        edit_page.set_phone("5550100")
        edit_page.save()

        contact_list.assert_contact_visible("Alice Tester")
