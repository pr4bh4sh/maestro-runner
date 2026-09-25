/**
 * Test that waitForAnimationToEnd succeeds after tapping Stop on the spinner app.
 */

import { execSync } from "child_process";
import { afterAll, describe, expect, it } from "@jest/globals";

import { getClient, teardown } from "./setup";

const APP_PKG = "dev.maestro.animationtest";
const APP_ACTIVITY = "dev.maestro.animationtest/.MainActivity";
const FOCUS_TIMEOUT_MS = 10_000;

function launchApp(): void {
  execSync(`adb shell am start -n ${APP_ACTIVITY}`, { stdio: "ignore" });
}

function waitForAppFocused(): void {
  const deadline = Date.now() + FOCUS_TIMEOUT_MS;
  while (Date.now() < deadline) {
    const out = execSync("adb shell dumpsys window", { encoding: "utf-8" });
    if (out.includes(APP_PKG)) return;
    execSync("sleep 0.5", { stdio: "ignore" });
  }
  throw new Error(`${APP_PKG} not focused within ${FOCUS_TIMEOUT_MS}ms`);
}

afterAll(async () => {
  await teardown();
});

describe("WaitForAnimation Stops On Click", () => {
  it("should settle after tapping Stop", async () => {
    const client = await getClient();
    launchApp();
    waitForAppFocused();
    await new Promise((r) => setTimeout(r, 2000));

    // Verify spinner is animating before Stop (must time out in 5s).
    await expect(
      client.waitForAnimationToEnd(500, 0.0003, "pre_check_animating", 5000),
    ).rejects.toThrow("Timed out");

    await client.tap({ text: "Stop" });

    await new Promise((r) => setTimeout(r, 500));

    await client.waitForAnimationToEnd(500, 0.0003, "wait_after_stop", 5000);
  }, 90_000);
});
