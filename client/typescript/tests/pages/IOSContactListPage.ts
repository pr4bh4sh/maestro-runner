/** Page Object — iOS Contacts app: contact list screen. */

import { MaestroClient, ExecutionResult } from "../../src";
import { BasePage } from "./BasePage";
import { IOSEditContactPage } from "./IOSEditContactPage";

export class IOSContactListPage extends BasePage {
  static readonly APP_ID = "com.apple.MobileAddressBook";

  constructor(client: MaestroClient) {
    super(client);
  }

  async launch(): Promise<ExecutionResult> {
    const result = await this.client.launchApp(IOSContactListPage.APP_ID, { stopApp: true });
    await this.waitForAnimation();
    return result;
  }

  async openCreateContact(): Promise<IOSEditContactPage> {
    await this.client.tap({ text: "Add" });
    await this.waitForAnimation();
    return new IOSEditContactPage(this.client);
  }

  async assertContactVisible(name: string): Promise<ExecutionResult> {
    return this.client.assertVisible({ text: name });
  }
}