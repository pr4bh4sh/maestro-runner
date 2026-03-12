# maestro-runner — TypeScript Client

TypeScript/JavaScript client for the [maestro-runner](../../README.md) REST API.

## Installation

```bash
cd client/typescript
npm install
```

## Quick Start

```ts
import { MaestroClient } from "maestro-runner";

const client = new MaestroClient("http://localhost:9999");
await client.createSession({ platformName: "android" });

try {
  await client.tap({ text: "Login" });
  await client.inputText("user@example.com");
  await client.assertVisible({ text: "Welcome" });
} finally {
  await client.close();
}
```

## Page Object Model

Tests use the Page Object Model pattern for maintainable E2E tests:

```ts
import { getClient, teardown } from "./setup";
import { ContactListPage } from "./pages/ContactListPage";

afterAll(() => teardown());

it("adds a contact", async () => {
  const client = await getClient();
  const contactList = new ContactListPage(client);

  await contactList.launch(true);
  const editPage = await contactList.openCreateContact();
  await editPage.setFirstName("Alice");
  await editPage.setLastName("Tester");
  await editPage.setPhone("5550100");
  await editPage.save();
  await contactList.assertContactVisible("Alice Tester");
});
```

## Running Tests

```bash
# Prerequisites for device tests: emulator/simulator running, maestro-runner server started
./maestro-runner --platform android server --port 9999

# Run unit tests only
npm run test:unit

# Run device tests
npm run test:device:android
npm run test:device:ios
```

## Environment Variables

| Variable              | Default                    | Description                     |
| --------------------- | -------------------------- | ------------------------------- |
| `MAESTRO_SERVER_URL`  | `http://localhost:9999`    | Server URL                      |
| `MAESTRO_PLATFORM`    | `android`                  | Target platform                 |
| `MAESTRO_RUNNER_BIN`  | `../../maestro-runner`     | Path to maestro-runner binary   |

## API Reference

### MaestroClient

| Method                | Description                            |
| --------------------- | -------------------------------------- |
| `createSession()`     | Initialize a session                   |
| `close()`             | Delete the session                     |
| `launchApp()`         | Launch an app                          |
| `stopApp()`           | Stop an app                            |
| `clearState()`        | Clear app state                        |
| `tap()`               | Tap on an element                      |
| `longPress()`         | Long-press on an element               |
| `tapOnPoint()`        | Tap on a coordinate                    |
| `inputText()`         | Type text                              |
| `eraseText()`         | Erase text                             |
| `pressKey()`          | Press a key                            |
| `back()`              | Press back button                      |
| `hideKeyboard()`      | Hide the keyboard                      |
| `scroll()`            | Scroll                                 |
| `swipe()`             | Swipe in a direction                   |
| `assertVisible()`     | Assert element is visible              |
| `assertNotVisible()`  | Assert element is not visible          |
| `elementExists()`     | Check if element exists (no throw)     |
| `tapFirstMatch()`     | Tap first matching selector            |
| `deviceInfo()`        | Get device information                 |
| `screenshot()`        | Get screenshot as ArrayBuffer          |
| `viewHierarchy()`     | Get view hierarchy XML                 |
