"""Test that waitForAnimationToEnd times out when animation never stops.

The target URL hosts a page with a constantly spinning CSS/JS loading
spinner.  Because the animation never ceases, the driver cannot reach a
"two consecutive identical screenshots" steady state, so
waitForAnimationToEnd must time out and return success=False.

Configuration knobs used by this test
--------------------------------------
sleep_ms=500
    Half a second between the two comparison screenshots.  A CSS spinner
    running at ~60 fps will have rotated noticeably in that window, ensuring
    the pixel diff stays consistently above the threshold.

threshold=0.001
    Only 0.1 % of pixels may differ for the screen to be considered static.
    This is tighter than the default 0.5 % so even a small spinner reliably
    triggers a diff above the threshold.

timeout=5000 (5 s)
    Long enough to take several comparison pairs, short enough that the test
    completes quickly.

Prerequisites:
  1. Android emulator running  (``adb devices`` shows a device)
  2. maestro-runner binary built and on PATH (or conftest will auto-start)
  3. Python deps installed:  pip install requests pytest

Run:
  pytest tests/test_wait_for_animation_never_ends.py -v
"""

import time

from maestro_runner import MaestroClient, commands

# Page with a perpetually spinning loading indicator — animation never settles
_SPINNER_URL = "https://discuss.wxpython.org/t/loading-spinner-animation/35657"

# How long the server waits before giving up (ms)
_TIMEOUT_MS = 5_000
# Pause between the two consecutive screenshots (ms) — must be long enough for
# the spinner to advance at least one visible frame
_SLEEP_MS = 500
# Maximum pixel-diff % still considered "static".
# The Discourse spinner produces ~0.000413-0.000674 diff on iOS after 500 ms;
# we set the bar at 0.0003 (well below that) so any rotation is detected as
# animated. On Android the diff is ~0.000741-0.000867 so 0.0003 works there too.
_THRESHOLD = 0.0003


def test_wait_for_animation_times_out_on_infinite_spinner(
    client: MaestroClient,
) -> None:
    """
    Open a page containing a continuously running spinner in Chrome, then call
    waitForAnimationToEnd with a tight threshold and a generous inter-screenshot
    sleep.  Because the animation never stops the driver must time out and
    return success=False.
    """
    open_result = client.open_link(_SPINNER_URL)
    assert open_result.success is True, (
        f"Failed to open spinner URL: {open_result.message}"
    )

    # Give the browser time to load the page and start rendering the spinner
    time.sleep(5)

    # Swipe up a bit to ensure the spinner is in view; assert it worked
    swipe_result = client.swipe("up", duration_ms=400)
    assert swipe_result.success is True, (
        f"Swipe failed: {swipe_result.message}"
    )
    time.sleep(1)

    # Use execute_step directly so that success=False is returned instead of
    # raising StepError — this is what we want to assert on.
    result = client.execute_step(commands.wait_for_animation_to_end(
        sleep_ms=_SLEEP_MS,
        threshold=_THRESHOLD,
        label="wait_for_animation_on_infinite_spinner",
    ))

    assert result.success is False, (
        "Expected waitForAnimationToEnd to fail (timeout) because the spinner "
        f"never stops, but got success=True. Message: {result.message}"
    )
    assert "Timed out" in (result.message or ""), (
        f"Expected a timeout message, got: {result.message}"
    )
    print(f"  waitForAnimationToEnd timed out as expected: {result.message}")
