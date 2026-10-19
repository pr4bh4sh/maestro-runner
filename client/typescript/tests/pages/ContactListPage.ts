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
    // The list can come back with a one-time "Some menu items have moved"
    // nag over it. Dismiss it when it shows; not every run gets it.
    await this.client.tap({ id: "android:id/closeButton", optional: true });
    return this.client.assertVisible({ text: name });
  }
}
