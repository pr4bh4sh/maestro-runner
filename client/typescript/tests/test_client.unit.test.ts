import { afterAll, beforeEach, describe, expect, it, jest } from "@jest/globals";

import { MaestroClient } from "../src/client";
import { MaestroError, SessionError, StepError } from "../src/exceptions";
import { ElementSelector } from "../src/models";

const BASE = "http://localhost:9999";
const SID = "test-session-123";

function jsonResponse(status: number, payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function textResponse(status: number, text: string): Response {
  return new Response(text, { status });
}

describe("MaestroClient (unit)", () => {
  const originalFetch = global.fetch;
  let fetchMock: jest.MockedFunction<typeof fetch>;

  beforeEach(() => {
    fetchMock = jest.fn() as jest.MockedFunction<typeof fetch>;
    global.fetch = fetchMock;
  });

  afterAll(() => {
    global.fetch = originalFetch;
  });

  it("creates a session", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { sessionId: SID }));

    const client = new MaestroClient(BASE);
    await client.createSession({ platformName: "android" });

    expect(client.getSessionId()).toBe(SID);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe(`${BASE}/session`);
    expect(init?.method).toBe("POST");
    expect(JSON.parse(init?.body as string)).toEqual({ platformName: "android" });
  });

  it("raises SessionError when createSession fails", async () => {
    fetchMock.mockResolvedValueOnce(textResponse(500, "Internal error"));

    const client = new MaestroClient(BASE);
    await expect(client.createSession({ platformName: "android" })).rejects.toBeInstanceOf(
      SessionError,
    );
  });

  it("close is no-op without session", async () => {
    const client = new MaestroClient(BASE);
    await client.close();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("close deletes active session", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(200, { sessionId: SID }))
      .mockResolvedValueOnce(textResponse(200, ""));

    const client = new MaestroClient(BASE);
    await client.createSession({ platformName: "android" });
    await client.close();

    expect(client.getSessionId()).toBeUndefined();
    expect(String(fetchMock.mock.calls[1][0])).toBe(`${BASE}/session/${SID}`);
    expect(fetchMock.mock.calls[1][1]?.method).toBe("DELETE");
  });

  it("requires an active session for executeStep", async () => {
    const client = new MaestroClient(BASE);
    await expect(client.executeStep({ type: "back" })).rejects.toBeInstanceOf(SessionError);
  });

  it("raises MaestroError on executeStep http error", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(200, { sessionId: SID }))
      .mockResolvedValueOnce(textResponse(500, "server error"));

    const client = new MaestroClient(BASE);
    await client.createSession({ platformName: "android" });

    await expect(client.executeStep({ type: "back" })).rejects.toBeInstanceOf(MaestroError);
  });

  it("tap by text uses compact selector", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(200, { sessionId: SID }))
      .mockResolvedValueOnce(jsonResponse(200, { success: true }));

    const client = new MaestroClient(BASE);
    await client.createSession({ platformName: "android" });
    await client.tap({ text: "Login" });

    const body = JSON.parse(fetchMock.mock.calls[1][1]?.body as string);
    expect(body.type).toBe("tapOn");
    expect(body.selector).toBe("Login");
  });

  it("tap with selector object serializes selector fields", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(200, { sessionId: SID }))
      .mockResolvedValueOnce(jsonResponse(200, { success: true }));

    const client = new MaestroClient(BASE);
    await client.createSession({ platformName: "android" });
    await client.tap({ selector: new ElementSelector({ text: "Item", childOf: { id: "list" } }) });

    const body = JSON.parse(fetchMock.mock.calls[1][1]?.body as string);
    expect(body.selector).toEqual({ text: "Item", childOf: { id: "list" } });
  });

  it("raises StepError on non-optional step failure", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(200, { sessionId: SID }))
      .mockResolvedValueOnce(jsonResponse(200, { success: false, message: "not found" }));

    const client = new MaestroClient(BASE);
    await client.createSession({ platformName: "android" });

    await expect(client.tap({ text: "Missing" })).rejects.toBeInstanceOf(StepError);
  });

  it("does not raise StepError for optional failure", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(200, { sessionId: SID }))
      .mockResolvedValueOnce(jsonResponse(200, { success: false, message: "not found" }));

    const client = new MaestroClient(BASE);
    await client.createSession({ platformName: "android" });
    const result = await client.tap({ text: "Maybe", optional: true });

    expect(result.success).toBe(false);
  });

  it("elementExists returns true or false based on optional assert", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(200, { sessionId: SID }))
      .mockResolvedValueOnce(jsonResponse(200, { success: true }))
      .mockResolvedValueOnce(jsonResponse(200, { success: false }));

    const client = new MaestroClient(BASE);
    await client.createSession({ platformName: "android" });

    await expect(client.elementExists({ text: "Visible" })).resolves.toBe(true);
    await expect(client.elementExists({ text: "Missing" })).resolves.toBe(false);
  });

  it("tapFirstMatch returns on first successful selector", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(200, { sessionId: SID }))
      .mockResolvedValueOnce(jsonResponse(200, { success: false }))
      .mockResolvedValueOnce(jsonResponse(200, { success: true, message: "ok" }));

    const client = new MaestroClient(BASE);
    await client.createSession({ platformName: "android" });

    const result = await client.tapFirstMatch([
      { selector: { text: "missing" } },
      { selector: { text: "present" } },
    ]);

    expect(result.success).toBe(true);
  });

  it("tapFirstMatch fails when selectors are empty", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { sessionId: SID }));

    const client = new MaestroClient(BASE);
    await client.createSession({ platformName: "android" });

    await expect(client.tapFirstMatch([])).rejects.toBeInstanceOf(StepError);
  });

  it("fetches device info", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(200, { sessionId: SID }))
      .mockResolvedValueOnce(
        jsonResponse(200, {
          platform: "android",
          osVersion: "14",
          deviceName: "Pixel 6",
        }),
      );

    const client = new MaestroClient(BASE);
    await client.createSession({ platformName: "android" });
    const info = await client.deviceInfo();

    expect(info.platform).toBe("android");
    expect(info.osVersion).toBe("14");
    expect(info.deviceName).toBe("Pixel 6");
  });

  it("fetches screenshot bytes", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(200, { sessionId: SID }))
      .mockResolvedValueOnce(new Response(new Uint8Array([1, 2, 3]), { status: 200 }));

    const client = new MaestroClient(BASE);
    await client.createSession({ platformName: "android" });
    const bytes = await client.screenshot();

    expect(bytes.byteLength).toBe(3);
  });

  it("fetches view hierarchy", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(200, { sessionId: SID }))
      .mockResolvedValueOnce(textResponse(200, "<hierarchy />"));

    const client = new MaestroClient(BASE);
    await client.createSession({ platformName: "android" });
    const source = await client.viewHierarchy();

    expect(source).toContain("hierarchy");
  });

  it("waitForAnimationToEnd sends correct step type", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(200, { sessionId: SID }))
      .mockResolvedValueOnce(jsonResponse(200, { success: true }));

    const client = new MaestroClient(BASE);
    await client.createSession({ platformName: "android" });
    await client.waitForAnimationToEnd();

    const body = JSON.parse(fetchMock.mock.calls[1][1]?.body as string);
    expect(body.type).toBe("waitForAnimationToEnd");
    expect(body.sleepMs).toBeUndefined();
    expect(body.threshold).toBeUndefined();
  });

  it("waitForAnimationToEnd forwards sleepMs and threshold", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(200, { sessionId: SID }))
      .mockResolvedValueOnce(jsonResponse(200, { success: true }));

    const client = new MaestroClient(BASE);
    await client.createSession({ platformName: "android" });
    await client.waitForAnimationToEnd(500, 0.001);

    const body = JSON.parse(fetchMock.mock.calls[1][1]?.body as string);
    expect(body.type).toBe("waitForAnimationToEnd");
    expect(body.sleepMs).toBe(500);
    expect(body.threshold).toBe(0.001);
  });
});
