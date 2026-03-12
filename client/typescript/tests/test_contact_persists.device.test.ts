/**
 * POM-based test — Contact persists after relaunch.
 *
 * Equivalent of: e2e/workspaces/contacts/contact_persists.yaml
 * Also equivalent of: client/python/tests/test_contact_persists.py
 *
 * This test creates a contact using the add_contact flow as setup,
 * then cold-relaunches the app and verifies the contact is still visible.
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
 *   npx jest tests/test_contact_persists.device.test.ts
 */

import { afterAll, describe, it } from "@jest/globals";

import { getClient, teardown } from "./setup";
import { ContactListPage } from "./pages/ContactListPage";

afterAll(async () => {
  await teardown();
});

describe("ContactPersists", () => {
  /** Mirrors contact_persists.yaml: add contact → relaunch → verify. */
  it("should persist contact after relaunch", async () => {
    const client = await getClient();
    const contactList = new ContactListPage(client);

    // First create the contact (reuses the add_contact flow as setup)
    await contactList.launch(true);
    const editPage = await contactList.openCreateContact();
    await editPage.setFirstName("Alice");
    await editPage.setLastName("Tester");
    await editPage.setPhone("5550100");
    await editPage.save();
    await contactList.assertContactVisible("Alice Tester");

    // Cold-relaunch the app
    await client.stopApp(ContactListPage.APP_ID);
    await contactList.launch(false);

    // The contact must still be visible
    await contactList.assertContactVisible("Alice Tester");
  });
});
