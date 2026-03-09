/** Command builders — produce step JSON for the REST API. */

import type { ElementSelector } from "./models";

type Step = Record<string, unknown>;
type SelectorValue = string | Record<string, unknown>;

function selectorValue(opts: {
  text?: string;
  id?: string;
  index?: number;
  selector?: ElementSelector;
  enabled?: boolean;
  checked?: boolean;
  focused?: boolean;
  selected?: boolean;
}): SelectorValue {
  const d: Record<string, unknown> = {};
  if (opts.selector) Object.assign(d, opts.selector.toDict());
  if (opts.text != null) d.text = opts.text;
  if (opts.id != null) d.id = opts.id;
  if (opts.index != null) d.index = String(opts.index);
  if (opts.enabled != null) d.enabled = opts.enabled;
  if (opts.checked != null) d.checked = opts.checked;
  if (opts.focused != null) d.focused = opts.focused;
  if (opts.selected != null) d.selected = opts.selected;
  // Compact form: text-only selector → plain string
  const keys = Object.keys(d);
  if (keys.length === 1 && keys[0] === "text") return d.text as string;
  return d;
}

export function tapOn(opts: {
  text?: string;
  id?: string;
  index?: number;
  selector?: ElementSelector;
  longPress?: boolean;
  waitUntilVisible?: boolean;
  retryIfNoChange?: boolean;
  enabled?: boolean;
  checked?: boolean;
  focused?: boolean;
  selected?: boolean;
  optional?: boolean;
  timeout?: number;
  label?: string;
}): Step {
  const step: Step = { type: "tapOn" };
  step.selector = selectorValue(opts);
  if (opts.longPress) step.longPress = true;
  if (opts.waitUntilVisible != null) step.waitUntilVisible = opts.waitUntilVisible;
  if (opts.retryIfNoChange != null) step.retryTapIfNoChange = opts.retryIfNoChange;
  if (opts.optional) step.optional = true;
  if (opts.timeout != null) step.timeout = opts.timeout;
  if (opts.label != null) step.label = opts.label;
  return step;
}

export function inputText(text: string, label?: string): Step {
  const step: Step = { type: "inputText", text };
  if (label != null) step.label = label;
  return step;
}

export function eraseText(characters?: number, label?: string): Step {
  const step: Step = { type: "eraseText" };
  if (characters != null) step.charactersToErase = characters;
  if (label != null) step.label = label;
  return step;
}

export function pressKey(code: string, label?: string): Step {
  const step: Step = { type: "pressKey", key: code };
  if (label != null) step.label = label;
  return step;
}

export function back(label?: string): Step {
  const step: Step = { type: "back" };
  if (label != null) step.label = label;
  return step;
}

export function scroll(label?: string): Step {
  const step: Step = { type: "scroll" };
  if (label != null) step.label = label;
  return step;
}

export function swipe(direction: string, durationMs: number = 400, label?: string): Step {
  const step: Step = { type: "swipe", direction: direction.toUpperCase(), duration: durationMs };
  if (label != null) step.label = label;
  return step;
}

export function hideKeyboard(strategy?: string, label?: string): Step {
  const step: Step = { type: "hideKeyboard" };
  if (strategy != null) step.strategy = strategy;
  if (label != null) step.label = label;
  return step;
}

export function waitForAnimationToEnd(label?: string): Step {
  const step: Step = { type: "waitForAnimationToEnd" };
  if (label != null) step.label = label;
  return step;
}

export function assertVisible(opts: {
  text?: string;
  id?: string;
  selector?: ElementSelector;
  timeoutMs?: number;
  optional?: boolean;
  label?: string;
}): Step {
  const step: Step = { type: "assertVisible" };
  step.selector = selectorValue({ text: opts.text, id: opts.id, selector: opts.selector });
  if (opts.timeoutMs != null) step.timeout = opts.timeoutMs;
  if (opts.optional) step.optional = true;
  if (opts.label != null) step.label = opts.label;
  return step;
}

export function assertNotVisible(opts: {
  text?: string;
  id?: string;
  selector?: ElementSelector;
  timeoutMs?: number;
  label?: string;
}): Step {
  const step: Step = { type: "assertNotVisible" };
  step.selector = selectorValue({ text: opts.text, id: opts.id, selector: opts.selector });
  if (opts.timeoutMs != null) step.timeout = opts.timeoutMs;
  if (opts.label != null) step.label = opts.label;
  return step;
}

export function launchApp(
  appId: string,
  opts?: { clearState?: boolean; stopApp?: boolean; label?: string },
): Step {
  const step: Step = { type: "launchApp", appId };
  if (opts?.clearState != null) step.clearState = opts.clearState;
  if (opts?.stopApp != null) step.stopApp = opts.stopApp;
  if (opts?.label != null) step.label = opts.label;
  return step;
}

export function stopApp(appId: string, label?: string): Step {
  const step: Step = { type: "stopApp", appId };
  if (label != null) step.label = label;
  return step;
}

export function clearState(appId: string, label?: string): Step {
  const step: Step = { type: "clearState", appId };
  if (label != null) step.label = label;
  return step;
}

export function openLink(link: string, label?: string): Step {
  const step: Step = { type: "openLink", link };
  if (label != null) step.label = label;
  return step;
}
