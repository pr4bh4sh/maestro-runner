"""Tests for waitForAnimationToEnd on Android.

The test launches Android Settings, navigates into a sub-screen (which
produces a visible transition animation) and then calls waitForAnimationToEnd
to confirm the screen has settled.

Prerequisites:
  1. Android emulator running  (``adb devices`` shows a device)
  2. maestro-runner binary built and on PATH (or conftest will auto-start)
  3. Python deps installed:  pip install requests pytest

Run:
  pytest tests/test_wait_for_animation_to_end.py -v
"""

from maestro_runner import MaestroClient

# API 35 titles the screen row "Display, interaction, audio"; the sub-screen it
# opens is still called Display.
DISPLAY_ROW = "Display, interaction, audio"

# ---------------------------------------------------------------------------
# Tests  (all use the session-scoped `client` fixture from conftest.py)
# ---------------------------------------------------------------------------


def test_wait_for_animation_settles_after_app_launch(client: MaestroClient) -> None:
    """
    Launch Settings (which itself triggers an entry animation) then immediately
    call waitForAnimationToEnd — the driver must detect that the screen has
    become static and return success.
    """
    client.launch_app("com.android.settings", clear_state=False)

    # Should not raise; always returns success=True (timeout is non-fatal)
    result = client.wait_for_animation_to_end()
    assert result.success is True, f"waitForAnimationToEnd failed: {result.message}"
    assert "WARNING" not in (result.message or ""), (
        f"Got placeholder warning instead of real implementation: {result.message}"
    )
    print(f"  waitForAnimationToEnd message: {result.message}")


def test_wait_for_animation_settles_after_navigation(client: MaestroClient) -> None:
    """
    Tap into a sub-screen to trigger a slide-in animation, then call
    waitForAnimationToEnd and confirm it settles without error.
    """
    # On API 35 the Settings entry is titled "Display, interaction, audio"
    # (there is no bare "Display" row), and it sits below the fold of the home
    # list, so scroll to it first. `text` is a whole-value match, so the full
    # title is required.
    client.scroll_until_visible(element=DISPLAY_ROW, direction="down")
    client.tap(text=DISPLAY_ROW)

    result = client.wait_for_animation_to_end()
    assert result.success is True, f"waitForAnimationToEnd failed: {result.message}"
    assert "WARNING" not in (result.message or ""), (
        f"Got placeholder warning: {result.message}"
    )
    print(f"  waitForAnimationToEnd message: {result.message}")


def test_wait_for_animation_on_already_static_screen(client: MaestroClient) -> None:
    """
    Call waitForAnimationToEnd when the screen is already fully static.
    The driver should take two consecutive identical screenshots and return
    almost immediately with a 'screen is static' message.
    """
    result = client.wait_for_animation_to_end()
    assert result.success is True, f"waitForAnimationToEnd on static screen failed: {result.message}"
    print(f"  waitForAnimationToEnd (static) message: {result.message}")
