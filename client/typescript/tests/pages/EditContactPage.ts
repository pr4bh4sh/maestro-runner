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
    // On API 35 the phone row is an EditText labelled "Phone"; the old
    // "Phone (Mobile)|Add phone" label belonged to the pre-API-33 editor.
    await this.client.tap({ text: "Phone" });
    await this.client.inputText(number);
    await this.hideKeyboard("back");
  }

  async save(): Promise<ExecutionResult> {
    const result = await this.client.tap({ text: "Save" });
    await this.waitForAnimation();
    return result;
  }
}
