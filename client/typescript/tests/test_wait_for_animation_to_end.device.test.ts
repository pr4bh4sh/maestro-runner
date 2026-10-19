/**
 * Tests for waitForAnimationToEnd on Android.
 *
 * The test launches Android Settings, navigates into a sub-screen (which
 * produces a visible transition animation) and then calls waitForAnimationToEnd
 * to confirm the screen has settled.
 *
 * Equivalent of: client/python/tests/test_wait_for_animation_to_end.py
 *
 * Prerequisites:
 *   1. Android emulator running (adb devices shows a device)
 *   2. Node deps installed (from client/typescript): npm install
 *   3. (Optional) Start maestro-runner server manually:
 *        ./maestro-runner --platform android server --port 9999
 *      If not running, the server is auto-started by the test setup.
 *
 * Run:
 *   cd client/typescript && npx jest tests/test_wait_for_animation_to_end.device.test.ts --runInBand
 */

import { afterAll, describe, expect, it } from "@jest/globals";

import { getClient, teardown } from "./setup";

// API 35 titles the screen row "Display, interaction, audio"; the sub-screen it
// opens is still called Display.
const DISPLAY_ROW = "Display, interaction, audio";

afterAll(async () => {
  await teardown();
});

describe("WaitForAnimationToEnd (settles)", () => {
  it("should settle after app launch", async () => {
    const client = await getClient();

    await client.launchApp("com.android.settings", { clearState: false });

    // Should not throw; returns success=true once screen becomes static
    const result = await client.waitForAnimationToEnd();
    expect(result.success).toBe(true);
    expect(result.message).not.toContain("WARNING");
    console.log(`  waitForAnimationToEnd message: ${result.message}`);
  });

  it("should settle after navigation", async () => {
    const client = await getClient();

    // API 35 titles the Settings row "Display, interaction, audio" (there is no
    // bare "Display" row) and it sits below the fold of the home list, so scroll
    // to it first. `text` is a whole-value match, so the full title is required.
    await client.scrollUntilVisible({ element: DISPLAY_ROW, direction: "down" });
    await client.tap({ text: DISPLAY_ROW });

    const result = await client.waitForAnimationToEnd();
    expect(result.success).toBe(true);
    expect(result.message).not.toContain("WARNING");
    console.log(`  waitForAnimationToEnd message: ${result.message}`);
  });

  it("should settle immediately on already-static screen", async () => {
    const client = await getClient();

    const result = await client.waitForAnimationToEnd();
    expect(result.success).toBe(true);
    console.log(`  waitForAnimationToEnd (static) message: ${result.message}`);
  });
});
