/** Page Object Model — base page with common helpers. */

import { MaestroClient, ExecutionResult } from "../../src";

export abstract class BasePage {
  constructor(protected readonly client: MaestroClient) {}

  async waitForAnimation(sleepMs?: number, threshold?: number): Promise<ExecutionResult> {
    return this.client.waitForAnimationToEnd(sleepMs, threshold);
  }

  async hideKeyboard(strategy?: string): Promise<ExecutionResult> {
    return this.client.hideKeyboard(strategy);
  }
}
