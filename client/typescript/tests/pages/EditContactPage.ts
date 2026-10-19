/** Page Object — Contacts app: create / edit contact form. */

import { ExecutionResult } from "../../src";
import { BasePage } from "./BasePage";

export class EditContactPage extends BasePage {
  async setFirstName(name: string): Promise<void> {
    await this.client.tap({ text: "First name" });
    await this.client.inputText(name);
    await this.hideKeyboard();
  }

  async setLastName(name: string): Promise<void> {
    await this.client.tap({ text: "Last name" });
    await this.client.inputText(name);
    await this.hideKeyboard("escape");
  }

  async setPhone(number: string): Promise<void> {
    await this.waitForAnimation();
    // Contacts ships two editors: the older one labels the row "Phone", the
    // newer one "Phone (Mobile)" next to an "Add phone" row. `text` is a
    // whole-value regex, so this alternation matches either build.
    await this.client.tap({ text: "Phone.*|Add phone" });
    await this.client.inputText(number);
    await this.hideKeyboard("back");
  }

  async save(): Promise<ExecutionResult> {
    const result = await this.client.tap({ text: "Save" });
    await this.waitForAnimation();
    return result;
  }
}
