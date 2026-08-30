"""Test that waitForAnimationToEnd succeeds after tapping Stop on the spinner app.

A tiny offline Android app (dev.maestro.animationtest) shows a full-screen
WebView rendering a perpetually rotating canvas spinner. Tapping the Stop
button clears the setInterval, halting the animation. The driver should
detect that the screen becomes static and return success=True.

The WebView's canvas animation is independent of the system animator/window/
transition scales, so it keeps rotating even when the emulator runs with
`disable-animations: true`. No network or local HTTP server is involved --
the HTML is embedded in the app.

Prerequisites:
  1. Android emulator running  (``adb devices`` shows a device)
  2. maestro-runner binary built and on PATH (or conftest will auto-start)
  3. Python deps installed:  pip install requests pytest
  4. drivers/android/animation-test-app-debug.apk installed on the emulator

Run:
  pytest tests/test_wait_for_animation_stops_on_click.py -v
"""

import subprocess
import time

from maestro_runner import MaestroClient

# Package/activity of the offline WebView spinner test app.
_APP_PKG = "dev.maestro.animationtest"
_APP_ACTIVITY = "dev.maestro.animationtest/.MainActivity"

# Pause between the two consecutive screenshots (ms) -- must be long enough for
# the spinner to advance at least one visible frame
_SLEEP_MS = 500
# Maximum pixel-diff fraction still considered "static". Far below what a
# rotating spinner produces, so any rotation is detected as animated.
_THRESHOLD = 0.0003

# How long to wait for the app to come to the foreground before giving up (s)
_FOCUS_TIMEOUT_S = 10


def _launch_app() -> None:
    # Bring the WebView spinner app to the foreground.
    subprocess.run(  # noqa: S603
        ["adb", "shell", "am", "start", "-n", _APP_ACTIVITY],  # noqa: S607
        capture_output=True, text=True, check=True,
    )


def _wait_for_app_focused() -> None:
    # Ensure the app actually reached the foreground before we screenshot it;
    # otherwise waitForAnimationToEnd could sample a stale/previous screen.
    deadline = time.time() + _FOCUS_TIMEOUT_S
    while time.time() < deadline:
        out = subprocess.run(
            ["adb", "shell", "dumpsys", "window"],  # noqa: S607
            capture_output=True, text=True, check=True,
        ).stdout
        if _APP_PKG in out:
            return
        time.sleep(0.5)
    raise RuntimeError(
        f"{_APP_PKG} did not become the focused app within "
        f"{_FOCUS_TIMEOUT_S}s; cannot run the animation test"
    )


def test_wait_for_animation_stops_after_tapping_stop(client: MaestroClient) -> None:
    """
    Launch the spinner app (animation never settles), verify it is animating
    (wait times out), tap Stop, then verify the screen settles.
    """
    _launch_app()
    _wait_for_app_focused()
    time.sleep(2)

    # Verify the spinner is continuously animating before Stop (wait must
    # time out). wait_for_animation_to_end goes via _exec and throws
    # StepError on timeout, so we assert via try/catch.
    import pytest
    from maestro_runner.exceptions import StepError

    with pytest.raises(StepError, match="Timed out"):
        client.wait_for_animation_to_end(
            sleep_ms=_SLEEP_MS,
            threshold=_THRESHOLD,
            timeout_ms=5000,
            label="pre_check_animating",
        )

    client.tap(text="Stop")
    time.sleep(0.5)

    result = client.wait_for_animation_to_end(timeout_ms=5000)
    assert "WARNING" not in (result.message or "")
    print(f"  stopped animation message: {result.message}")
