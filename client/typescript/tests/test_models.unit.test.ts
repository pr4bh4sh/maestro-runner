import { describe, expect, it } from "@jest/globals";

import { DeviceInfo, ElementInfo, ElementSelector, ExecutionResult } from "../src/models";

describe("ElementSelector.toDict", () => {
  it("serializes text only", () => {
    const sel = new ElementSelector({ text: "Hello" });
    expect(sel.toDict()).toEqual({ text: "Hello" });
  });

  it("serializes id only", () => {
    const sel = new ElementSelector({ id: "btn_login" });
    expect(sel.toDict()).toEqual({ id: "btn_login" });
  });

  it("serializes index as string", () => {
    const sel = new ElementSelector({ index: 3 });
    expect(sel.toDict()).toEqual({ index: "3" });
  });

  it("serializes boolean flags", () => {
    const sel = new ElementSelector({
      enabled: true,
      checked: false,
      focused: true,
      selected: false,
    });
    expect(sel.toDict()).toEqual({
      enabled: true,
      checked: false,
      focused: true,
      selected: false,
    });
  });

  it("serializes nested relative selectors", () => {
    const ref = new ElementSelector({ text: "Ref" });
    const sel = new ElementSelector({
      text: "Target",
      childOf: { id: "parent" },
      below: ref,
      above: ref,
      leftOf: ref,
      rightOf: ref,
      containsChild: ref,
      insideOf: ref,
    });

    expect(sel.toDict()).toEqual({
      text: "Target",
      childOf: { id: "parent" },
      below: { text: "Ref" },
      above: { text: "Ref" },
      leftOf: { text: "Ref" },
      rightOf: { text: "Ref" },
      containsChild: { text: "Ref" },
      insideOf: { text: "Ref" },
    });
  });

  it("returns empty object for empty selector", () => {
    expect(new ElementSelector().toDict()).toEqual({});
  });
});

describe("ElementInfo.fromDict", () => {
  it("returns undefined for null/undefined", () => {
    expect(ElementInfo.fromDict(undefined)).toBeUndefined();
    expect(ElementInfo.fromDict(null)).toBeUndefined();
  });

  it("parses full payload", () => {
    const info = ElementInfo.fromDict({
      id: "btn1",
      text: "OK",
      bounds: { x: 10, y: 20, width: 100, height: 50 },
      visible: true,
      enabled: true,
      focused: false,
      checked: true,
      selected: false,
    });

    expect(info).toEqual(
      expect.objectContaining({
        id: "btn1",
        text: "OK",
        visible: true,
        enabled: true,
        focused: false,
        checked: true,
        selected: false,
      }),
    );
  });

  it("applies defaults for partial payload", () => {
    const info = ElementInfo.fromDict({ text: "hello", visible: true });
    expect(info).toEqual(
      expect.objectContaining({
        id: "",
        text: "hello",
        visible: true,
      }),
    );
  });
});

describe("ExecutionResult.fromDict", () => {
  it("parses success payload", () => {
    const result = ExecutionResult.fromDict({ success: true, message: "ok", duration: 1234 });
    expect(result.success).toBe(true);
    expect(result.message).toBe("ok");
    expect(result.durationNs).toBe(1234);
  });

  it("parses element and data fields", () => {
    const result = ExecutionResult.fromDict({
      success: true,
      element: { id: "e1", text: "Hello", visible: true },
      data: { key: "value" },
    });

    expect(result.element).toEqual(expect.objectContaining({ id: "e1", text: "Hello" }));
    expect(result.data).toEqual({ key: "value" });
  });

  it("uses defaults for empty payload", () => {
    const result = ExecutionResult.fromDict({});
    expect(result.success).toBe(false);
    expect(result.message).toBeUndefined();
    expect(result.element).toBeUndefined();
    expect(result.data).toBeUndefined();
  });
});

describe("DeviceInfo.fromDict", () => {
  it("parses full payload", () => {
    const info = DeviceInfo.fromDict({
      platform: "android",
      osVersion: "14",
      deviceName: "Pixel 6",
      deviceId: "emulator-5554",
      isSimulator: true,
      screenWidth: 1080,
      screenHeight: 2400,
      appId: "com.example.app",
    });

    expect(info).toEqual(
      expect.objectContaining({
        platform: "android",
        osVersion: "14",
        deviceName: "Pixel 6",
        deviceId: "emulator-5554",
        isSimulator: true,
        screenWidth: 1080,
        screenHeight: 2400,
        appId: "com.example.app",
      }),
    );
  });

  it("applies defaults for empty payload", () => {
    const info = DeviceInfo.fromDict({});
    expect(info.platform).toBe("");
    expect(info.osVersion).toBe("");
    expect(info.screenWidth).toBe(0);
    expect(info.isSimulator).toBe(false);
  });
});
