/** Page Object — Contacts app: contact list screen. */

import { MaestroClient, ExecutionResult } from "../../src";
import { BasePage } from "./BasePage";
import { EditContactPage } from "./EditContactPage";

export class ContactListPage extends BasePage {
  static readonly APP_ID = "com.google.android.contacts";

  constructor(client: MaestroClient) {
    super(client);
  }

  async launch(clearState: boolean = true): Promise<ExecutionResult> {
    const result = await this.client.launchApp(ContactListPage.APP_ID, { clearState });
    await this.waitForAnimation();
    return result;
  }

  async openCreateContact(): Promise<EditContactPage> {
    await this.client.tap({ text: "Create contact|Add contact|New contact" });
    await this.waitForAnimation();
    return new EditContactPage(this.client);
  }

  async assertContactVisible(name: string): Promise<ExecutionResult> {
    return this.client.assertVisible({ text: name });
  }
}
