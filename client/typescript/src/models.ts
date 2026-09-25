/** Data models mapping Go server JSON responses to TypeScript types. */

// ---------- Element Selector ----------

export interface ElementSelectorInit {
  text?: string;
  id?: string;
  index?: number;
  enabled?: boolean;
  checked?: boolean;
  focused?: boolean;
  selected?: boolean;
  css?: string;
  traits?: string;
  childOf?: ElementSelectorInit;
  below?: ElementSelectorInit;
  above?: ElementSelectorInit;
  leftOf?: ElementSelectorInit;
  rightOf?: ElementSelectorInit;
  containsChild?: ElementSelectorInit;
  insideOf?: ElementSelectorInit;
}

export class ElementSelector {
  text?: string;
  id?: string;
  index?: number;
  enabled?: boolean;
  checked?: boolean;
  focused?: boolean;
  selected?: boolean;
  css?: string;
  traits?: string;
  childOf?: ElementSelector;
  below?: ElementSelector;
  above?: ElementSelector;
  leftOf?: ElementSelector;
  rightOf?: ElementSelector;
  containsChild?: ElementSelector;
  insideOf?: ElementSelector;

  constructor(init: ElementSelectorInit = {}) {
    Object.assign(this, init);
    if (init.childOf) this.childOf = new ElementSelector(init.childOf);
    if (init.below) this.below = new ElementSelector(init.below);
    if (init.above) this.above = new ElementSelector(init.above);
    if (init.leftOf) this.leftOf = new ElementSelector(init.leftOf);
    if (init.rightOf) this.rightOf = new ElementSelector(init.rightOf);
    if (init.containsChild)
      {this.containsChild = new ElementSelector(init.containsChild);}
    if (init.insideOf) this.insideOf = new ElementSelector(init.insideOf);
  }

  toDict(): Record<string, unknown> {
    const d: Record<string, unknown> = {};
    if (this.text != null) d.text = this.text;
    if (this.id != null) d.id = this.id;
    if (this.index != null) d.index = String(this.index);
    if (this.enabled != null) d.enabled = this.enabled;
    if (this.checked != null) d.checked = this.checked;
    if (this.focused != null) d.focused = this.focused;
    if (this.selected != null) d.selected = this.selected;
    if (this.css != null) d.css = this.css;
    if (this.traits != null) d.traits = this.traits;
    if (this.childOf) d.childOf = this.childOf.toDict();
    if (this.below) d.below = this.below.toDict();
    if (this.above) d.above = this.above.toDict();
    if (this.leftOf) d.leftOf = this.leftOf.toDict();
    if (this.rightOf) d.rightOf = this.rightOf.toDict();
    if (this.containsChild) d.containsChild = this.containsChild.toDict();
    if (this.insideOf) d.insideOf = this.insideOf.toDict();
    return d;
  }
}

// ---------- Element Info ----------

export interface ElementInfoData {
  id?: string;
  text?: string;
  bounds?: Record<string, number>;
  visible?: boolean;
  enabled?: boolean;
  focused?: boolean;
  checked?: boolean;
  selected?: boolean;
}

export class ElementInfo {
  id: string;
  text: string;
  bounds: Record<string, number>;
  visible: boolean;
  enabled: boolean;
  focused: boolean;
  checked: boolean;
  selected: boolean;

  constructor(data: ElementInfoData = {}) {
    this.id = data.id ?? "";
    this.text = data.text ?? "";
    this.bounds = data.bounds ?? {};
    this.visible = data.visible ?? false;
    this.enabled = data.enabled ?? false;
    this.focused = data.focused ?? false;
    this.checked = data.checked ?? false;
    this.selected = data.selected ?? false;
  }

  static fromDict(data?: Record<string, unknown> | null): ElementInfo | undefined {
    if (!data) return undefined;
    return new ElementInfo(data as ElementInfoData);
  }
}

// ---------- Execution Result ----------

export class ExecutionResult {
  success: boolean;
  message?: string;
  durationNs: number;
  element?: ElementInfo;
  data?: unknown;

  constructor(
    success: boolean,
    message?: string,
    durationNs: number = 0,
    element?: ElementInfo,
    data?: unknown,
  ) {
    this.success = success;
    this.message = message;
    this.durationNs = durationNs;
    this.element = element;
    this.data = data;
  }

  static fromDict(data: Record<string, unknown>): ExecutionResult {
    return new ExecutionResult(
      (data.success as boolean) ?? false,
      data.message as string | undefined,
      (data.duration as number) ?? 0,
      ElementInfo.fromDict(data.element as Record<string, unknown> | undefined),
      data.data,
    );
  }
}

// ---------- Device Info ----------

export class DeviceInfo {
  platform: string;
  osVersion: string;
  deviceName: string;
  deviceId: string;
  isSimulator: boolean;
  screenWidth: number;
  screenHeight: number;
  appId: string;

  constructor(data: Record<string, unknown> = {}) {
    this.platform = (data.platform as string) ?? "";
    this.osVersion = (data.osVersion as string) ?? "";
    this.deviceName = (data.deviceName as string) ?? "";
    this.deviceId = (data.deviceId as string) ?? "";
    this.isSimulator = (data.isSimulator as boolean) ?? false;
    this.screenWidth = (data.screenWidth as number) ?? 0;
    this.screenHeight = (data.screenHeight as number) ?? 0;
    this.appId = (data.appId as string) ?? "";
  }

  static fromDict(data: Record<string, unknown>): DeviceInfo {
    return new DeviceInfo(data);
  }
}
