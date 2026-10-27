"""
SYNDRA Milestone 1 Challenger Test Suite:
Adversarial Click Transparency, Keycap Penetration, Text Legibility, and Console Error Immunity.

Author: teamwork_preview_challenger (Milestone 1 Gate Challenger 1)
Role: critic, specialist
"""

import time
import unittest
from playwright.sync_api import sync_playwright

from tests.helpers import (
    HTML_URL,
    FINGER_CONFIG,
    get_bbox,
    get_center,
    reset_page_state,
)


def get_relative_luminance(rgb_tuple):
    """Compute WCAG 2.1 relative luminance from (r, g, b) tuple in 0-255."""
    def channel_lum(c):
        v = c / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb_tuple
    return 0.2126 * channel_lum(r) + 0.7152 * channel_lum(g) + 0.0722 * channel_lum(b)


def calculate_contrast_ratio(rgb1, rgb2):
    """Calculate contrast ratio between two (r, g, b) tuples."""
    l1 = get_relative_luminance(rgb1)
    l2 = get_relative_luminance(rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def parse_rgb(rgb_str):
    """Parse 'rgb(r, g, b)' or 'rgba(r, g, b, a)' into (r, g, b)."""
    import re
    m = re.search(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", rgb_str)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return (255, 255, 255)


class BaseChallengerTestCase(unittest.TestCase):
    """Base setup for Challenger Playwright test cases."""

    playwright = None
    browser = None
    context = None
    page = None
    console_errors = []

    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(channel="chrome", headless=True)
        cls.context = cls.browser.new_context(viewport={"width": 1400, "height": 900})
        cls.page = cls.context.new_page()
        cls.console_errors = []
        cls.page.on("console", lambda msg: cls.console_errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
        cls.page.on("pageerror", lambda err: cls.console_errors.append(f"[pageerror] {err}"))
        cls.page.goto(HTML_URL)
        cls.page.locator("#ch5").scroll_into_view_if_needed()
        cls.page.wait_for_timeout(400)

    @classmethod
    def tearDownClass(cls):
        if cls.page:
            cls.page.close()
        if cls.context:
            cls.context.close()
        if cls.browser:
            cls.browser.close()
        if cls.playwright:
            cls.playwright.stop()

    def setUp(self):
        self.console_errors.clear()
        self.page.set_viewport_size({"width": 1400, "height": 900})
        self.page.locator("#ch5").scroll_into_view_if_needed()
        reset_page_state(self.page)
        self.page.wait_for_timeout(50)

    def tearDown(self):
        reset_page_state(self.page)


class TestKeycapClickPenetration(BaseChallengerTestCase):
    """Adversarial testing of pointer transparency and click penetration."""

    def test_click_penetration_all_53_keycaps_center(self):
        """Stress-test: Mouse clicks on all 53 keycaps center must register without SVG interception."""
        keycaps = self.page.locator("#keyboardContainer .key-cap").all()
        self.assertEqual(len(keycaps), 53, "Expected 53 keycaps in Chapter 5 keyboard.")

        blocked_keys = []
        unpressed_keys = []

        for keycap in keycaps:
            code = keycap.get_attribute("data-key")
            box = keycap.bounding_box()
            self.assertIsNotNone(box, f"Keycap {code} has no bounding box.")
            cx = box["x"] + box["width"] / 2.0
            cy = box["y"] + box["height"] / 2.0

            # 1. elementFromPoint check: Must NEVER be inside #handOverlay
            hit_info = self.page.evaluate("""([x, y]) => {
                const el = document.elementFromPoint(x, y);
                if (!el) return { hit: null, insideOverlay: false };
                const overlay = document.getElementById('handOverlay');
                const insideOverlay = overlay ? overlay.contains(el) : false;
                const closestKey = el.closest('.key-cap');
                return {
                    tag: el.tagName,
                    id: el.id,
                    className: el.className ? el.className.toString() : '',
                    insideOverlay: insideOverlay,
                    keyData: closestKey ? closestKey.getAttribute('data-key') : null
                };
            }""", [cx, cy])

            if hit_info["insideOverlay"]:
                blocked_keys.append((code, hit_info))

            # 2. Simulate physical mouse down
            self.page.mouse.move(cx, cy)
            self.page.mouse.down()
            time.sleep(0.01)

            is_pressed = self.page.evaluate("""([code]) => {
                const el = document.querySelector(`.key-cap[data-key="${code}"]`);
                return el ? el.classList.contains('is-pressed') : false;
            }""", [code])

            if not is_pressed:
                unpressed_keys.append(code)

            self.page.mouse.up()
            time.sleep(0.005)

        self.assertEqual(
            len(blocked_keys),
            0,
            f"Clicks intercepted by #handOverlay on {len(blocked_keys)} keys: {blocked_keys}",
        )
        self.assertEqual(
            len(unpressed_keys),
            0,
            f"Keys failed to activate 'is-pressed' on click: {unpressed_keys}",
        )

    def test_click_penetration_all_53_keycaps_four_corners(self):
        """Stress-test: Clicks at 4 corner offsets on every keycap must penetrate to keycap."""
        keycaps = self.page.locator("#keyboardContainer .key-cap").all()
        corner_blocked = []

        for keycap in keycaps:
            code = keycap.get_attribute("data-key")
            box = keycap.bounding_box()
            if not box:
                continue

            corners = [
                (box["x"] + 4, box["y"] + 4, "top-left"),
                (box["x"] + box["width"] - 4, box["y"] + 4, "top-right"),
                (box["x"] + 4, box["y"] + box["height"] - 4, "bottom-left"),
                (box["x"] + box["width"] - 4, box["y"] + box["height"] - 4, "bottom-right"),
            ]

            for px, py, corner_name in corners:
                is_svg = self.page.evaluate("""([x, y]) => {
                    const el = document.elementFromPoint(x, y);
                    if (!el) return false;
                    const overlay = document.getElementById('handOverlay');
                    return overlay ? (overlay === el || overlay.contains(el)) : false;
                }""", [px, py])

                if is_svg:
                    corner_blocked.append((code, corner_name, px, py))

        self.assertEqual(
            len(corner_blocked),
            0,
            f"Corner clicks blocked by SVG overlay on: {corner_blocked}",
        )

    def test_click_penetration_directly_on_all_5_resting_fingertip_pads(self):
        """Adversarial: Clicking directly on the resting fingertip centers must penetrate to underlying home keys."""
        target_map = {
            "pinky": "KeyZ",
            "ring": "KeyD",
            "middle": "KeyR",
            "index": "KeyT",
            "thumb": "KeyM",
        }

        for finger, expected_key in target_map.items():
            pad_selector = f"#fingertip-{finger}"
            pad_box = get_bbox(self.page, pad_selector)
            cx, cy = get_center(pad_box)

            # Check elementFromPoint right on the pad center
            hit_info = self.page.evaluate("""([x, y]) => {
                const el = document.elementFromPoint(x, y);
                const overlay = document.getElementById('handOverlay');
                const closest = el ? el.closest('.key-cap') : null;
                return {
                    tag: el ? el.tagName : null,
                    insideOverlay: overlay ? overlay.contains(el) : false,
                    hitKey: closest ? closest.getAttribute('data-key') : null
                };
            }""", [cx, cy])

            self.assertFalse(
                hit_info["insideOverlay"],
                f"Fingertip pad #{finger} intercepted click at ({cx:.1f}, {cy:.1f}): {hit_info}",
            )
            self.assertEqual(
                hit_info["hitKey"],
                expected_key,
                f"Click on #{finger} center hit key '{hit_info['hitKey']}' instead of expected '{expected_key}'.",
            )

            # Click down and verify key activates
            self.page.mouse.move(cx, cy)
            self.page.mouse.down()
            time.sleep(0.02)

            key_pressed = self.page.evaluate("""([k]) => {
                const el = document.querySelector(`.key-cap[data-key="${k}"]`);
                return el ? el.classList.contains('is-pressed') : false;
            }""", [expected_key])

            self.assertTrue(
                key_pressed,
                f"Expected underlying key '{expected_key}' to activate on fingertip '{finger}' click.",
            )
            self.page.mouse.up()
            time.sleep(0.01)

    def test_click_penetration_directly_on_palm_silhouette(self):
        """Adversarial: Clicking points along palm silhouette must penetrate to underlying keycaps/stage."""
        palm_box = get_bbox(self.page, "#hand-palm")
        self.assertGreater(palm_box["width"], 20)
        self.assertGreater(palm_box["height"], 20)

        # Sample a 5x5 grid across the palm silhouette bounding box
        x_step = palm_box["width"] / 6.0
        y_step = palm_box["height"] / 6.0

        svg_intercepts = []
        for i in range(1, 6):
            for j in range(1, 6):
                sx = palm_box["x"] + i * x_step
                sy = palm_box["y"] + j * y_step

                inside_svg = self.page.evaluate("""([x, y]) => {
                    const el = document.elementFromPoint(x, y);
                    const overlay = document.getElementById('handOverlay');
                    return overlay ? (overlay === el || overlay.contains(el)) : false;
                }""", [sx, sy])

                if inside_svg:
                    svg_intercepts.append((sx, sy))

        self.assertEqual(
            len(svg_intercepts),
            0,
            f"Palm silhouette intercepted pointer events at {len(svg_intercepts)} sample points: {svg_intercepts}",
        )

    def test_click_penetration_directly_on_skeletal_splines(self):
        """Adversarial: Pointer events must not be caught by skeletal spline stroke paths."""
        spline_ids = [
            "#finger-spline-pinky",
            "#finger-spline-ring",
            "#finger-spline-middle",
            "#finger-spline-index",
            "#finger-spline-thumb",
        ]

        for s_id in spline_ids:
            box = get_bbox(self.page, s_id)
            cx, cy = get_center(box)

            inside_svg = self.page.evaluate("""([x, y]) => {
                const el = document.elementFromPoint(x, y);
                const overlay = document.getElementById('handOverlay');
                return overlay ? (overlay === el || overlay.contains(el)) : false;
            }""", [cx, cy])

            self.assertFalse(
                inside_svg,
                f"Spline {s_id} intercepted pointer events at center ({cx:.1f}, {cy:.1f}).",
            )

    def test_click_penetration_on_mcp_knuckles(self):
        """Adversarial: Pointer events must not be caught by knuckle circles."""
        knuckle_ids = [
            "#knuckle-pinky",
            "#knuckle-ring",
            "#knuckle-middle",
            "#knuckle-index",
            "#knuckle-thumb",
        ]

        for k_id in knuckle_ids:
            box = get_bbox(self.page, k_id)
            cx, cy = get_center(box)

            inside_svg = self.page.evaluate("""([x, y]) => {
                const el = document.elementFromPoint(x, y);
                const overlay = document.getElementById('handOverlay');
                return overlay ? (overlay === el || overlay.contains(el)) : false;
            }""", [cx, cy])

            self.assertFalse(
                inside_svg,
                f"Knuckle {k_id} intercepted pointer events at center ({cx:.1f}, {cy:.1f}).",
            )

    def test_click_penetration_while_keys_are_active(self):
        """Adversarial: When a key is active/held, clicking other keys penetrates normally."""
        # Hold Spacebar
        space_box = get_bbox(self.page, '.key-cap[data-key="Space"]')
        self.page.mouse.move(space_box["x"] + space_box["width"] / 2.0, space_box["y"] + space_box["height"] / 2.0)
        self.page.mouse.down()
        time.sleep(0.02)

        # While holding Space, verify element under KeyR, KeyT, KeyD penetrates
        for test_key in ["KeyR", "KeyT", "KeyD", "KeyZ", "KeyC"]:
            kbox = get_bbox(self.page, f'.key-cap[data-key="{test_key}"]')
            kcx, kcy = get_center(kbox)
            hit_key = self.page.evaluate("""([x, y]) => {
                const el = document.elementFromPoint(x, y);
                return el ? el.closest('.key-cap')?.getAttribute('data-key') : null;
            }""", [kcx, kcy])
            self.assertEqual(hit_key, test_key, f"Holding Space blocked click on {test_key}")

        self.page.mouse.up()
        time.sleep(0.01)


class TestLegibilityAndContrast(BaseChallengerTestCase):
    """Stress-test keycap text legibility, bounding boxes, and color contrast."""

    def test_all_keycap_primary_labels_bounding_boxes_and_visibility(self):
        """Verify all keycap primary labels (.key-id) have accessible bounding boxes and high opacity."""
        labels = self.page.locator("#keyboardContainer .key-cap .key-id").all()
        self.assertGreater(len(labels), 45, "Expected at least 45 .key-id elements in keyboard.")

        illegible_labels = []

        for label in labels:
            text = label.inner_text().strip()
            box = label.bounding_box()
            if not box or box["width"] <= 0 or box["height"] <= 0:
                illegible_labels.append(f"Label '{text}' has invalid bbox: {box}")
                continue

            styles = label.evaluate("""el => {
                const cs = window.getComputedStyle(el);
                return {
                    opacity: parseFloat(cs.opacity),
                    display: cs.display,
                    visibility: cs.visibility,
                    fontSize: parseFloat(cs.fontSize),
                    color: cs.color
                };
            }""")

            if styles["opacity"] < 0.8:
                illegible_labels.append(f"Label '{text}' low opacity: {styles['opacity']}")
            if styles["display"] == "none" or styles["visibility"] == "hidden":
                illegible_labels.append(f"Label '{text}' hidden: display={styles['display']}, visibility={styles['visibility']}")
            if styles["fontSize"] < 8.0:
                illegible_labels.append(f"Label '{text}' font size too small: {styles['fontSize']}px")

        self.assertEqual(
            len(illegible_labels),
            0,
            f"Found illegible primary labels: {illegible_labels}",
        )

    def test_all_mapped_keycap_tactical_action_labels_bounding_boxes(self):
        """Verify all tactical action labels (.key-action) are rendered with readable dimensions."""
        actions = self.page.locator("#keyboardContainer .key-cap .key-action").all()
        self.assertGreater(len(actions), 10, "Expected at least 10 .key-action elements.")

        action_issues = []

        for action in actions:
            text = action.inner_text().strip()
            box = action.bounding_box()
            if not box or box["width"] <= 0 or box["height"] <= 0:
                action_issues.append(f"Action '{text}' has invalid bbox: {box}")
                continue

            styles = action.evaluate("""el => {
                const cs = window.getComputedStyle(el);
                return {
                    opacity: parseFloat(cs.opacity),
                    display: cs.display,
                    visibility: cs.visibility,
                    fontSize: parseFloat(cs.fontSize)
                };
            }""")

            if styles["opacity"] < 0.7:
                action_issues.append(f"Action '{text}' low opacity: {styles['opacity']}")
            if styles["display"] == "none" or styles["visibility"] == "hidden":
                action_issues.append(f"Action '{text}' hidden")

        self.assertEqual(len(action_issues), 0, f"Found action label issues: {action_issues}")

    def test_text_color_contrast_ratios(self):
        """Verify text color contrast against keycap background exceeds minimum WCAG threshold."""
        labels = self.page.locator("#keyboardContainer .key-cap .key-id").all()
        low_contrast_keys = []

        for label in labels:
            text = label.inner_text().strip()
            data = label.evaluate("""el => {
                const keyCap = el.closest('.key-cap');
                const labelStyle = window.getComputedStyle(el);
                const keyStyle = window.getComputedStyle(keyCap);
                return {
                    textColor: labelStyle.color,
                    bgColor: keyStyle.backgroundColor,
                    keyData: keyCap.getAttribute('data-key')
                };
            }""")

            text_rgb = parse_rgb(data["textColor"])
            # Fallback bg color if transparent is #171717 (var(--key-base))
            bg_rgb = parse_rgb(data["bgColor"]) if "rgba(0, 0, 0, 0)" not in data["bgColor"] else (23, 23, 23)

            ratio = calculate_contrast_ratio(text_rgb, bg_rgb)
            # Minimum contrast ratio for large/bold UI keycap text: 3.0:1
            if ratio < 3.0:
                low_contrast_keys.append((data["keyData"], text, ratio, data["textColor"], data["bgColor"]))

        self.assertEqual(
            len(low_contrast_keys),
            0,
            f"Keys with insufficient contrast ratio (< 3.0): {low_contrast_keys}",
        )

    def test_hand_overlay_semi_transparency_alpha(self):
        """Verify hand palm silhouette and overlay elements maintain semi-transparent glass styling."""
        palm_fill = self.page.locator("#hand-palm").evaluate("el => window.getComputedStyle(el).fill")
        import re
        match = re.search(r"rgba\([^,]+,[^,]+,[^,]+,\s*([\d\.]+)\)", palm_fill)
        self.assertIsNotNone(match, f"Expected rgba fill on #hand-palm, got: {palm_fill}")
        alpha = float(match.group(1))
        # Silhouette must be semi-transparent (alpha <= 0.40) to guarantee under-hand text readability
        self.assertLessEqual(alpha, 0.40, f"Hand palm silhouette alpha too opaque: {alpha}")


class TestStressHoverClickAndConsoleErrors(BaseChallengerTestCase):
    """Stress test: rapid interactions, viewport resize, zero console error invariant."""

    def test_rapid_mouse_hover_across_all_keys_zero_errors(self):
        """Stress: Fast mouse sweeping over all 53 keys sequentially generates zero console errors."""
        keycaps = self.page.locator("#keyboardContainer .key-cap").all()
        for keycap in keycaps:
            box = keycap.bounding_box()
            if box:
                self.page.mouse.move(box["x"] + box["width"] / 2.0, box["y"] + box["height"] / 2.0)
                time.sleep(0.005)

        self.assertEqual(
            len(self.console_errors),
            0,
            f"Console errors during hover sweep: {self.console_errors}",
        )

    def test_rapid_burst_clicking_across_keys_zero_errors(self):
        """Stress: Rapid burst clicking on 25 keys in sequence produces zero console errors."""
        test_keys = [
            "Escape", "Tab", "KeyQ", "KeyW", "KeyE", "KeyR", "KeyT", "KeyY",
            "CapsLock", "KeyA", "KeyS", "KeyD", "KeyF", "KeyG",
            "ShiftLeft", "KeyZ", "KeyX", "KeyC", "KeyV", "KeyB",
            "ControlLeft", "AltLeft", "Space", "KeyN", "KeyM"
        ]

        for code in test_keys:
            keycap = self.page.locator(f'#keyboardContainer .key-cap[data-key="{code}"]')
            box = keycap.bounding_box()
            if box:
                cx = box["x"] + box["width"] / 2.0
                cy = box["y"] + box["height"] / 2.0
                self.page.mouse.click(cx, cy)
                time.sleep(0.005)

        self.assertEqual(
            len(self.console_errors),
            0,
            f"Console errors during rapid clicking: {self.console_errors}",
        )

    def test_rapid_viewport_resizing_during_interactions_zero_errors(self):
        """Stress: Viewport changes (1400 -> 1024 -> 1280 -> 1400) during clicks maintain zero errors."""
        viewports = [
            {"width": 1400, "height": 900},
            {"width": 1024, "height": 768},
            {"width": 1280, "height": 800},
            {"width": 1400, "height": 900},
        ]

        for vp in viewports:
            self.page.set_viewport_size(vp)
            self.page.locator("#ch5").scroll_into_view_if_needed()
            self.page.wait_for_timeout(50)

            # Trigger a click on KeyR and Space in this viewport
            r_box = self.page.locator('.key-cap[data-key="KeyR"]').bounding_box()
            if r_box:
                self.page.mouse.click(r_box["x"] + r_box["width"] / 2.0, r_box["y"] + r_box["height"] / 2.0)

            space_box = self.page.locator('.key-cap[data-key="Space"]').bounding_box()
            if space_box:
                self.page.mouse.click(space_box["x"] + space_box["width"] / 2.0, space_box["y"] + space_box["height"] / 2.0)

        self.assertEqual(
            len(self.console_errors),
            0,
            f"Console errors during viewport resizing: {self.console_errors}",
        )


class TestLaptopViewportClickTransparency(BaseChallengerTestCase):
    """Verify click transparency and legibility specifically at 1024px laptop viewport."""

    def setUp(self):
        super().setUp()
        self.page.set_viewport_size({"width": 1024, "height": 768})
        self.page.locator("#ch5").scroll_into_view_if_needed()
        self.page.wait_for_timeout(100)

    def test_laptop_1024px_click_penetration_all_keys(self):
        """At 1024px laptop resolution, all 53 keys pass clicks through without overlay interference."""
        keycaps = self.page.locator("#keyboardContainer .key-cap").all()
        blocked = []

        for keycap in keycaps:
            code = keycap.get_attribute("data-key")
            box = keycap.bounding_box()
            if not box:
                continue
            cx = box["x"] + box["width"] / 2.0
            cy = box["y"] + box["height"] / 2.0

            inside_overlay = self.page.evaluate("""([x, y]) => {
                const el = document.elementFromPoint(x, y);
                const overlay = document.getElementById('handOverlay');
                return overlay ? (overlay === el || overlay.contains(el)) : false;
            }""", [cx, cy])

            if inside_overlay:
                blocked.append(code)

        self.assertEqual(len(blocked), 0, f"At 1024px, clicks blocked by SVG on: {blocked}")

    def test_laptop_1024px_fingertip_pad_alignment_and_click(self):
        """At 1024px laptop resolution, fingertip pads align over resting keys and clicks pass through."""
        target_keys = {
            "pinky": "KeyZ",
            "ring": "KeyD",
            "middle": "KeyR",
            "index": "KeyT",
            "thumb": "KeyM",
        }

        for finger, expected_key in target_keys.items():
            pad_box = get_bbox(self.page, f"#fingertip-{finger}")
            cx, cy = get_center(pad_box)

            hit_key = self.page.evaluate("""([x, y]) => {
                const el = document.elementFromPoint(x, y);
                const closest = el ? el.closest('.key-cap') : null;
                return closest ? closest.getAttribute('data-key') : null;
            }""", [cx, cy])

            self.assertEqual(
                hit_key,
                expected_key,
                f"At 1024px, click on #{finger} hit key '{hit_key}' instead of '{expected_key}'.",
            )


if __name__ == "__main__":
    unittest.main()
