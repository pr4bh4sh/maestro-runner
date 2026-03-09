package devicelab

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"

	"github.com/devicelab-dev/maestro-runner/pkg/core"
	"github.com/devicelab-dev/maestro-runner/pkg/flow"
)

// Patterns for extracting keyboard bounds from "dumpsys window InputMethod".
var (
	// Android <=12: "mFrame=[left,top][right,bottom]"
	mFrameRegex = regexp.MustCompile(`mFrame=\[(\d+),(\d+)\]\[(\d+),(\d+)\]`)

	// Android 13+: "touchable region=SkRegion((left,top,right,bottom))"
	touchableRegionRegex = regexp.MustCompile(`touchable region=SkRegion\(\((\d+),(\d+),(\d+),(\d+)\)\)`)
)

// parseKeyboardFrame extracts keyboard bounds from "dumpsys window InputMethod" output.
// Returns nil if keyboard is not visible.
func parseKeyboardFrame(dumpsysOutput string) *core.Bounds {
	// Bail early if the window is explicitly not on screen.
	if strings.Contains(dumpsysOutput, "isOnScreen=false") ||
		strings.Contains(dumpsysOutput, "mViewVisibility=0x8") {
		return nil
	}

	// Prefer touchable region — gives the actual keyboard area, not the full
	// InputMethod window. Available on Android 11+ (SDK 30+). Safe to use here
	// because the caller already checks mInputShown before calling this function.
	if matches := touchableRegionRegex.FindStringSubmatch(dumpsysOutput); matches != nil {
		return boundsFromMatches(matches)
	}

	// Fallback for older Android (<=10) that lacks touchable region.
	if matches := mFrameRegex.FindStringSubmatch(dumpsysOutput); matches != nil {
		return boundsFromMatches(matches)
	}

	return nil
}

// boundsFromMatches converts regex matches [_, left, top, right, bottom] to Bounds.
// Atoi errors are safe to ignore — the regex guarantees \d+ captures.
// Returns nil if the resulting area has zero or negative dimensions.
func boundsFromMatches(matches []string) *core.Bounds {
	left, _ := strconv.Atoi(matches[1])
	top, _ := strconv.Atoi(matches[2])
	right, _ := strconv.Atoi(matches[3])
	bottom, _ := strconv.Atoi(matches[4])

	width := right - left
	height := bottom - top

	if width <= 0 || height <= 0 {
		return nil
	}

	return &core.Bounds{
		X:      left,
		Y:      top,
		Width:  width,
		Height: height,
	}
}

// getKeyboardBounds returns the keyboard frame if visible, nil otherwise.
// Requires device (ShellExecutor) to be available.
func (d *Driver) getKeyboardBounds() *core.Bounds {
	if d.device == nil {
		return nil
	}

	output, err := d.device.Shell("dumpsys window InputMethod")
	if err != nil {
		return nil
	}

	if strings.Contains(output, "mInputShown=false") {
		return nil
	}

	return parseKeyboardFrame(output)
}

// isKeyboardVisible checks if the soft keyboard is currently shown using dumpsys.
func (d *Driver) isKeyboardVisible() bool {
	return d.getKeyboardBounds() != nil
}

// tapWouldHitKeyboard returns true if a tap on the element's center would land
// on the keyboard area instead of the element. Uses a margin to account for the
// keyboard's touchable region including the suggestion strip above the actual keys.
func tapWouldHitKeyboard(element, keyboard core.Bounds) bool {
	_, cy := element.Center()
	// The keyboard's touchable region often includes the suggestion/toolbar strip,
	// so the reported top is higher than where keys actually start. Allow a 50px
	// margin so elements barely overlapping the strip are still considered tappable.
	const margin = 50
	return cy >= keyboard.Y+margin
}

// consumeInputFlag checks and resets the lastStepWasInput flag.
// Returns true if the previous step was an input step.
func (d *Driver) consumeInputFlag() bool {
	was := d.lastStepWasInput
	d.lastStepWasInput = false
	return was
}

var errKeyboardOpen = fmt.Errorf("keyboard is open — add a `- hideKeyboard` step before this step")

// checkKeyboardBlocking checks if the keyboard overlaps the target element after an input step.
// UIA2 finds elements via the accessibility tree even when the keyboard covers them,
// but coordinate taps land on the keyboard overlay instead. This detects that case and
// fails fast with a helpful hint instead of silently tapping the keyboard.
// Returns nil if this check doesn't apply or element is not blocked — caller should proceed normally.
func (d *Driver) checkKeyboardBlocking(wasInput bool, sel flow.Selector) *core.CommandResult {
	if !wasInput {
		return nil
	}

	// Find element (UIA2 will find it even behind keyboard)
	_, info, err := d.findElementOnce(sel)
	if err != nil || info == nil {
		// Element genuinely not found — let caller do the full-timeout find
		return nil
	}

	// Element found — check if keyboard overlaps its bounds
	kbBounds := d.getKeyboardBounds()
	if kbBounds == nil {
		return nil
	}

	if tapWouldHitKeyboard(info.Bounds, *kbBounds) {
		_, cy := info.Bounds.Center()
		return errorResult(errKeyboardOpen,
			fmt.Sprintf("Element found but keyboard is covering it (keyboard top: %d, element center Y: %d) — add a `- hideKeyboard` step before this step",
				kbBounds.Y, cy))
	}

	return nil
}
