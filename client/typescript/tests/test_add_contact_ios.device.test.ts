/**
 * POM-based test — Add a new contact on iOS.
 *
 * Equivalent of: e2e/workspaces/contacts/add_contact_ios.yaml
 *
 * Prerequisites:
 *   1. iOS simulator running
 *   2. Node deps installed (from client/typescript):
 *        npm install
 *   3. (Optional) Start maestro-runner server manually:
 *        ./maestro-runner --platform ios --device <UDID> server --port 9999
 *      If not running, the server is auto-started by the test setup.
 *
 * Override with env vars:
 *   MAESTRO_SERVER_URL   (default: http://localhost:9999)
 *   MAESTRO_PLATFORM     (set to: ios)
 *   MAESTRO_DEVICE_ID    (recommended for explicit simulator targeting)
 *   MAESTRO_RUNNER_BIN   (path to binary, auto-detected by default)
 *
 * Run:
 *   MAESTRO_PLATFORM=ios npx jest tests/test_add_contact_ios.device.test.ts --runInBand
 */

import { afterAll, describe, it } from "@jest/globals";

import { getClient, teardown } from "./setup";
import { IOSContactListPage } from "./pages/IOSContactListPage";

afterAll(async () => {
  await teardown();
});

describe("AddContactIOS", () => {
  it("should add and verify a contact on iOS", async () => {
    const client = await getClient();
    const contactList = new IOSContactListPage(client);

    await contactList.launch();

    const editPage = await contactList.openCreateContact();
    await editPage.setFirstName("Alice");
    await editPage.setLastName("Tester");
    await editPage.setPhone("5550100");
    await editPage.save();

    await contactList.assertContactVisible("Alice Tester");
  });
});