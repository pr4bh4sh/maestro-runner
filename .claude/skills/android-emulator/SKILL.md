---
name: android-emulator
description: >
  Starts the Android emulator that maestro-runner's Android E2E suite expects, on the
  plain google_apis image CI uses, with the emulator window open. Use this skill whenever an
  Android e2e test must be reproduced, debugged or re-run locally, when a flow fails only on CI's
  E2E Android jobs, when choosing between emulator images, when an e2e run needs a booted
  emulator with animations disabled, or when setting up a device before running the Python or
  TypeScript device tests.
---

# Skill: android-emulator

Boots the emulator the Android E2E suite is written against, and hands back its serial.

## Image: plain `google_apis`, never `playstore`

The suite pins `system-images;android-35;google_apis;arm64-v8a` — the same image
`.github/workflows/e2e-android.yml` uses (`target: google_apis`, `api-level: 35`).

The `google_apis_playstore*` images look equivalent and are not. They carry a working Play
Store that **updates the apps under test mid-session**: a `google_apis_playstore_ps16k` AVD
pulled Contacts from the image's build up to **4.89.27** partway through a run, and the
create-contact form's labels changed with it. A flow that passes against CI fails against that
AVD, and the reverse — the selector is right for one Contacts build and wrong for the other.

Choose the image to match what CI runs, not to match whatever AVD already exists.

**Completion criterion:** Contacts reports the build the image ships, not a Play Store update:

```sh
adb -s "$SERIAL" shell dumpsys package com.google.android.contacts | grep -m1 versionName
```

`system-images;android-35;google_apis` ships **4.32.50**. Anything in the 4.8x/4.89 range means
the AVD drifted off CI and its Contacts UI is not the one the flows were written against.

Play Store (`com.android.vending`) is installed and enabled on the `google_apis` image too, so
its presence proves nothing — compare the Contacts version instead.

## Steps

### 1. Ensure the image is installed

```sh
SDK="$HOME/Library/Android/sdk"
ls "$SDK/system-images/android-35/google_apis/arm64-v8a/package.xml" >/dev/null 2>&1 \
  || yes | "$SDK/cmdline-tools/latest/bin/sdkmanager" --install 'system-images;android-35;google_apis;arm64-v8a'
```

Already installed? Nothing happens. A partial download leaves no `package.xml`; delete the
partial directory and retry.

**Done when:** `package.xml` exists under the image path.

### 2. Create the AVD only if it does not exist

```sh
cd ~/.android/avd
[ -d ci35.avd ] || {
  cp -r Pixel_9a_1.avd ci35.avd && cp Pixel_9a_1.ini ci35.ini
  sed -i '' 's|image.sysdir.1=.*|image.sysdir.1=system-images/android-35/google_apis/arm64-v8a/|' ci35.avd/config.ini
  sed -i '' 's|^avd.ini.displayname=.*|avd.ini.displayname=ci35|' ci35.ini
  # The copy carries the source AVD's userdata disk: its installed apps come along too.
  # find, not a glob: zsh aborts the whole command on an unmatched pattern.
  find ci35.avd -maxdepth 1 \( -name '*.img' -o -name '*.qcow2' \) -delete
}
```

`ci35` is reused across runs — if it exists, leave it alone. Re-copying it every time throws away
the installed drivers and settings. To rebuild, `adb emu kill` first, then `rm -rf ci35.avd ci35.ini`.

`avdmanager create` is not used: it answers a hardware-profile prompt and exits 1 when stdin isn't
an interactive TTY, leaving no AVD. Any API 35 AVD works as the source; only `image.sysdir.1`
matters. Deleting the image files on a *new* copy is what makes it a clean factory image —
otherwise the source AVD's packages make the next `adb install` fail with
`INSTALL_FAILED_UPDATE_INCOMPATIBLE`.

**Done when:** `emulator -list-avds` lists `ci35` and its `config.ini` names the `google_apis` image.

### 3. Start it fresh, with the window open

```sh
export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/emulator:$ANDROID_HOME/platform-tools:$PATH"
adb devices | grep -q '^emulator-[0-9]*' \
  || nohup emulator -avd ci35 -no-boot-anim -no-snapshot-load \
       -netdelay none -netspeed full -gpu swiftshader_indirect \
       > /tmp/emulator-ci35.log 2>&1 &
```

`-no-snapshot-load` is what makes the reused AVD boot fresh — previous session state is not
restored, so runs stay comparable. Keep the window visible: it is opened on purpose, so a run can
be watched and a stuck screen read directly instead of inferred from a timeout.

**Done when:** the emulator window is on screen and the log reports `Boot completed`.

### 4. Wait for boot and disable animations

```sh
adb start-server >/dev/null 2>&1
SERIAL=$(adb devices | awk '/emulator-[0-9]+[[:space:]]+device/{print $1; exit}')
until [ "$(adb -s "$SERIAL" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; do sleep 5; done
for s in window_animation_scale transition_animation_scale animator_duration_scale; do
  adb -s "$SERIAL" shell settings put global "$s" 0
done
echo "$SERIAL"
```

The serial is whatever port the emulator lands on — never assume `5554`; it is reused when a
previous emulator exits. Animations are disabled because CI sets `disable-animations: true`, and
a leftover transition makes `waitForAnimationToEnd` and tap timing behave differently.

**Done when:** `sys.boot_completed` is `1` and the three scales read `0`. The serial is now the
`MAESTRO_DEVICE_ID` for every device command that follows.

### 5. Dock the QWERTY keyboard

API 35's Gboard opens as a floating **"Write in text fields"** toolbar — backspace / tab / emoji /
menu down the left edge — instead of a keyboard. It occludes the left of the screen, so taps land
on the toolbar or miss entirely, and it never presents a keyboard window, so `hideKeyboard` cannot
confirm the IME went down.

```sh
adb -s "$SERIAL" shell settings put secure show_ime_with_hard_keyboard 1
adb -s "$SERIAL" shell settings put secure stylus_handwriting_enabled 0
adb -s "$SERIAL" shell ime set com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME
```

`stylus_handwriting_enabled 0` is the adb equivalent of Gboard → Settings → Write in text fields →
*Use stylus to write in text fields* off, which is what restores the docked layout.

Confirm visually rather than trusting the settings — this is the step that silently regresses:

```sh
adb -s "$SERIAL" exec-out screencap -p > /tmp/kb.png   # expect a QWERTY grid along the bottom
```

**Done when:** focusing a text field shows a QWERTY keyboard occupying the bottom ~45% of the
screen, with no floating toolbar at either edge.

### 6. Install the driver APKs

Uninstall each conflicting package first:

```sh
cd <repo root>
install_apk() {
  adb -s "$SERIAL" uninstall "$1" >/dev/null 2>&1 || true
  adb -s "$SERIAL" install -r -g "$2"
}
install_apk io.appium.uiautomator2.server drivers/android/appium-uiautomator2-server-v9.11.1.apk
adb -s "$SERIAL" install -r -g drivers/android/appium-uiautomator2-server-debug-androidTest.apk
install_apk io.appium.settings drivers/android/settings_apk-debug.apk
adb -s "$SERIAL" install -r -g drivers/android/animation-test-app-debug.apk
```

The `google_apis` image **pre-installs** `io.appium.uiautomator2.server` 9.9.0 and
`io.appium.settings` 7.0.6, both Google-signed. The pinned APKs are Appium-signed, so
`install -r` is refused with `INSTALL_FAILED_UPDATE_INCOMPATIBLE`. Uninstalling first lets the
pinned versions land; without it the run silently uses the image's older server.

The `devicelab` driver additionally needs `devicelab-android-driver.apk` and
`devicelab-android-driver-test.apk`; `appium` manages its own server and needs only the test app.

**Done when:** each `install` prints `Success`, and the installed versions are the pinned ones:

```sh
adb -s "$SERIAL" shell dumpsys package io.appium.uiautomator2.server | grep -m1 versionName   # 9.11.1
adb -s "$SERIAL" shell dumpsys package io.appium.settings | grep -m1 versionName             # 7.0.8
```

## Reference

### Running the suite once booted

```sh
go build -o maestro-runner .
export MAESTRO_DEVICE_ID="$SERIAL"
export MAESTRO_RUNNER_HOME="$(pwd)"   # the clients resolve drivers/ from here
./maestro-runner --driver uiautomator2 --platform android test \
  --output reports/yaml e2e/workspaces/contacts/add_contact_android.yaml
```

Pass the driver explicitly per run — `--driver` overrides the per-platform default, so omitting
it silently tests the devicelab path instead of the one you meant to check.

### Reading a CI-only failure

The same emulator with two drivers separates a stale selector from a driver bug. If devicelab
passes a flow and uiautomator2 fails it on one image, the selectors are right and the driver is
at fault — a flow fix will not help. If both fail, suspect the selector.

### Contacts editor labels differ between builds

The flow has to survive both, because real devices run either. `text` is a whole-value regex
(`\A(?:pattern)\z`), so alternation spans both shapes in one selector:

| Build | Phone row | Selector that matches both |
|---|---|---|
| CI image | `EditText text="Phone"` | `Phone.*\|Add phone` |
| Contacts 4.89+ | `"Phone (Mobile)"`, `"Add phone"`, `"+1"` prefix | |

Confirm against the live device rather than guessing:

```sh
adb -s "$SERIAL" shell uiautomator dump /sdcard/ui.xml
adb -s "$SERIAL" shell cat /sdcard/ui.xml | tr '>' '>\n' | grep -o 'text="[^"]*"' | grep -v 'text=""'
```

### Leaving the emulator as found

Record which AVDs were running before starting (`ps aux | grep "[e]mulator"`) and stop only the
one this skill started. Machines often keep other emulators up for unrelated work.

Guardrail: keep emulator-window startup on the visible path above — it is the documented
behaviour, and a headless launch is what makes an animation or focus bug invisible.