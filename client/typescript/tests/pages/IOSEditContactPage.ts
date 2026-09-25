/** Page Object — iOS Contacts app: create / edit contact form. */

import { MaestroClient, ExecutionResult } from "../../src";
import { BasePage } from "./BasePage";

export class IOSEditContactPage extends BasePage {
  constructor(client: MaestroClient) {
    super(client);
  }

  async setFirstName(name: string): Promise<void> {
    await this.client.tap({ text: "First name" });
    await this.client.inputText(name);
  }

  async setLastName(name: string): Promise<void> {
    await this.client.tap({ text: "Last name" });
    await this.client.inputText(name);
  }

  async setPhone(number: string): Promise<void> {
    await this.waitForAnimation();
    await this.client.executeStep({
      type: "swipe",
      start: "50%, 42%",
      end: "50%, 12%",
      duration: 700,
    });
    await this.client.tap({ text: "add phone" });
    await this.client.tap({ text: "phone" });
    await this.client.inputText(number);
  }

  async save(): Promise<ExecutionResult> {
    const result = await this.client.tap({ text: "Done" });
    await this.waitForAnimation();
    return result;
  }
}