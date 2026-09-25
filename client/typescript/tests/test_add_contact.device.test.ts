/**
 * POM-based test — Add a new contact.
 *
 * Equivalent of: client/python/tests/test_add_contact.py
 * Also equivalent of: e2e/workspaces/contacts/add_contact_android.yaml
 *
 * Prerequisites:
 *   1. Android emulator running (adb devices shows device)
 *   2. Node deps installed (from client/typescript):
 *        npm install
 *   3. (Optional) Start maestro-runner server manually:
 *        ./maestro-runner --platform android server --port 9999
 *      If not running, the server is auto-started by the test setup.
 *
 * Override with env vars:
 *   MAESTRO_SERVER_URL   (default: http://localhost:9999)
 *   MAESTRO_PLATFORM     (default: android)
 *   MAESTRO_RUNNER_BIN   (path to binary, auto-detected by default)
 *
 * Run:
 *   npx jest tests/test_add_contact.device.test.ts
 */

import { afterAll, describe, it } from "@jest/globals";

import { getClient, teardown } from "./setup";
import { ContactListPage } from "./pages/ContactListPage";

afterAll(async () => {
  await teardown();
});

describe("AddContact", () => {
  /** Mirrors add_contact_android.yaml: launch → create → fill → save → verify. */
  it("should add and verify a contact", async () => {
    const client = await getClient();
    const contactList = new ContactListPage(client);

    // Launch with a clean slate
    await contactList.launch(true);

    // Open the create-contact form
    const editPage = await contactList.openCreateContact();

    // Fill in name fields
    await editPage.setFirstName("Alice");
    await editPage.setLastName("Tester");

    // Fill in phone number
    await editPage.setPhone("5550100");

    // Save
    await editPage.save();

    // Verify the contact now appears in the list
    await contactList.assertContactVisible("Alice Tester");
  });
});
