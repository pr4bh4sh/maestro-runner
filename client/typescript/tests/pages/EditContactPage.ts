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
    await this.client.tap({ text: "Phone (Mobile)|Add phone" });
    await this.client.inputText(number);
    await this.hideKeyboard("back");
  }

  async save(): Promise<ExecutionResult> {
    const result = await this.client.tap({ text: "Save" });
    await this.waitForAnimation();
    return result;
  }
}
