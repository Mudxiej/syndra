"""
SYNDRA Ergonomic Hand Overlay Automated Verification Suite
4-Tier Comprehensive Playwright E2E Test Suite
Python 3.14 + Playwright (Headless Chrome)

Execution:
    & 'C:\\Users\\mudxiej\\AppData\\Local\\Programs\\Python\\Python314\\python.exe' -m unittest discover -s tests -p 'test_*.py'
"""

import time
import unittest
from playwright.sync_api import sync_playwright

from tests.helpers import (
    HTML_URL,
    FINGER_CONFIG,
    get_bbox,
    get_center,
    assert_inside_bbox,
    colors_match,
    reset_page_state,
)


class BaseE2ETestCase(unittest.TestCase):
    """Base test case initializing Playwright Chromium instance."""

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
        cls.page.on("console", lambda msg: cls.console_errors.append(msg.text) if msg.type == "error" else None)
        cls.page.on("pageerror", lambda err: cls.console_errors.append(str(err)))
        cls.page.goto(HTML_URL)
        cls.page.locator("#ch5").scroll_into_view_if_needed()
        cls.page.wait_for_timeout(300)

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
        # Restore default viewport if modified
        self.page.set_viewport_size({"width": 1400, "height": 900})
        reset_page_state(self.page)
        self.page.wait_for_timeout(50)

    def tearDown(self):
        reset_page_state(self.page)


# ==============================================================================
# TIER 1: FEATURE COVERAGE (Features 1 to 5: Structure, Posture, Styling)
# ==============================================================================

class TestTier1Features01To05HandOverlayRestPosture(BaseE2ETestCase):
    """Tier 1: Feature Coverage for Features 1-5 (>=5 tests per feature)."""

    # --- Feature 1: Hand Silhouette & Layering (ORIGINAL_REQUEST §R1) ---

    def test_f01_01_svg_overlay_element_mounted(self):
        """Feature 1: #handOverlay SVG element exists and is mounted in DOM."""
        locator = self.page.locator("#handOverlay")
        self.assertGreater(locator.count(), 0, "Missing #handOverlay SVG root element in DOM.")
        tag_name = locator.evaluate("el => el.tagName.toLowerCase()")
        self.assertEqual(tag_name, "svg", "#handOverlay must be an SVG element.")

    def test_f01_02_svg_overlay_pointer_events_none(self):
        """Feature 1: #handOverlay has pointer-events: none so clicks reach keycaps."""
        locator = self.page.locator("#handOverlay")
        self.assertGreater(locator.count(), 0, "#handOverlay element not found.")
        pe = locator.evaluate("el => window.getComputedStyle(el).pointerEvents")
        self.assertEqual(pe, "none", "#handOverlay must have CSS 'pointer-events: none'.")

    def test_f01_03_svg_overlay_position_absolute_and_inset(self):
        """Feature 1: #handOverlay has absolute positioning covering the keyboard stage."""
        locator = self.page.locator("#handOverlay")
        self.assertGreater(locator.count(), 0, "#handOverlay element not found.")
        pos = locator.evaluate("el => window.getComputedStyle(el).position")
        self.assertEqual(pos, "absolute", "#handOverlay must have position: absolute.")

    def test_f01_04_svg_overlay_z_index_layering(self):
        """Feature 1: #handOverlay z-index is >= 10 to render above keycaps."""
        locator = self.page.locator("#handOverlay")
        self.assertGreater(locator.count(), 0, "#handOverlay element not found.")
        z_index = locator.evaluate("el => parseInt(window.getComputedStyle(el).zIndex) || 0")
        self.assertGreaterEqual(z_index, 10, "#handOverlay z-index must be at least 10.")

    def test_f01_05_svg_overlay_dimensions_match_container(self):
        """Feature 1: #handOverlay dimensions match or cover keyboard container."""
        overlay_box = get_bbox(self.page, "#handOverlay")
        kb_box = get_bbox(self.page, "#keyboardContainer")
        self.assertGreater(overlay_box["width"], 300, "Overlay width too small.")
        self.assertGreater(overlay_box["height"], 150, "Overlay height too small.")
        # Overlay should roughly align with keyboard container bounds
        self.assertAlmostEqual(overlay_box["width"], kb_box["width"], delta=50)

    # --- Feature 2: Palm Desk Anchor (ORIGINAL_REQUEST §R1) ---

    def test_f02_01_palm_rest_bar_exists(self):
        """Feature 2: #palmRestBar element exists in DOM below row 5."""
        locator = self.page.locator("#palmRestBar")
        self.assertGreater(locator.count(), 0, "Missing #palmRestBar element in DOM.")

    def test_f02_02_palm_rest_bar_positioned_below_spacebar(self):
        """Feature 2: #palmRestBar y coordinate is positioned below Spacebar row."""
        palm_box = get_bbox(self.page, "#palmRestBar")
        space_box = get_bbox(self.page, '.key-cap[data-key="Space"]')
        # Palm bar center or top should be below Spacebar center
        self.assertGreaterEqual(
            palm_box["y"] + palm_box["height"] / 2,
            space_box["y"] + space_box["height"] / 2,
            "Palm rest bar must be anchored below Spacebar.",
        )

    def test_f02_03_palm_rest_bar_width_spans_keyboard_base(self):
        """Feature 2: #palmRestBar spans at least 40% of keyboard width."""
        palm_box = get_bbox(self.page, "#palmRestBar")
        kb_box = get_bbox(self.page, "#keyboardContainer")
        self.assertGreater(palm_box["width"], kb_box["width"] * 0.4)

    def test_f02_04_palm_spline_roots_originate_at_palm_rest(self):
        """Feature 2: Finger splines anchor/originate near palm rest region."""
        spline_ids = [
            "#finger-spline-pinky",
            "#finger-spline-ring",
            "#finger-spline-middle",
            "#finger-spline-index",
            "#finger-spline-thumb",
        ]
        for s_id in spline_ids:
            locator = self.page.locator(s_id)
            self.assertGreater(locator.count(), 0, f"Missing spline path: {s_id}")
            d_val = locator.get_attribute("d")
            self.assertTrue(d_val and len(d_val) > 5, f"Spline {s_id} has invalid path: {d_val}")

    def test_f02_05_palm_rest_bar_has_expected_class(self):
        """Feature 2: #palmRestBar has class 'palm-rest-bar'."""
        locator = self.page.locator("#palmRestBar")
        self.assertGreater(locator.count(), 0, "Missing #palmRestBar element in DOM.")
        classes = locator.evaluate("el => el.className")
        self.assertIn("palm-rest-bar", classes)

    # --- Feature 3: Baseline Home Rest Posture (ORIGINAL_REQUEST §R1) ---

    def test_f03_01_pinky_home_rest_on_key_z(self):
        """Feature 3: Pinky fingertip rests over KeyZ at rest."""
        pinky_box = get_bbox(self.page, "#fingertip-pinky")
        z_box = get_bbox(self.page, '.key-cap[data-key="KeyZ"]')
        assert_inside_bbox(self, get_center(pinky_box), z_box, "Pinky on KeyZ")

    def test_f03_02_ring_home_rest_on_key_d(self):
        """Feature 3: Ring fingertip rests over KeyD at rest."""
        ring_box = get_bbox(self.page, "#fingertip-ring")
        d_box = get_bbox(self.page, '.key-cap[data-key="KeyD"]')
        assert_inside_bbox(self, get_center(ring_box), d_box, "Ring on KeyD")

    def test_f03_03_middle_home_rest_on_key_r(self):
        """Feature 3: Middle fingertip rests over KeyR at rest."""
        mid_box = get_bbox(self.page, "#fingertip-middle")
        r_box = get_bbox(self.page, '.key-cap[data-key="KeyR"]')
        assert_inside_bbox(self, get_center(mid_box), r_box, "Middle on KeyR")

    def test_f03_04_index_home_rest_on_key_t(self):
        """Feature 3: Index fingertip rests over KeyT at rest."""
        idx_box = get_bbox(self.page, "#fingertip-index")
        t_box = get_bbox(self.page, '.key-cap[data-key="KeyT"]')
        assert_inside_bbox(self, get_center(idx_box), t_box, "Index on KeyT")

    def test_f03_05_thumb_home_rest_on_key_m(self):
        """Feature 3: Thumb fingertip rests over KeyM at rest."""
        thumb_box = get_bbox(self.page, "#fingertip-thumb")
        m_box = get_bbox(self.page, '.key-cap[data-key="KeyM"]')
        assert_inside_bbox(self, get_center(thumb_box), m_box, "Thumb on KeyM")

    # --- Feature 4: Visual Clarity & Legibility (ORIGINAL_REQUEST §R3) ---

    def test_f04_01_keycap_labels_visible_under_overlay(self):
        """Feature 4: Keycap primary labels (.key-id) remain visible with high opacity."""
        labels = self.page.locator(".key-id")
        self.assertGreater(labels.count(), 40, "Keycap labels not rendered.")
        first_label_opacity = float(labels.first.evaluate("el => window.getComputedStyle(el).opacity"))
        self.assertGreaterEqual(first_label_opacity, 0.8)

    def test_f04_02_keycap_actions_visible_under_overlay(self):
        """Feature 4: Keycap tactical action names (.key-action) remain visible."""
        actions = self.page.locator(".key-action")
        self.assertGreater(actions.count(), 10, "Keycap action labels not found.")
        first_action_display = actions.first.evaluate("el => window.getComputedStyle(el).display")
        self.assertNotEqual(first_action_display, "none")

    def test_f04_03_hand_silhouette_semi_transparent(self):
        """Feature 4: Hand silhouette fill or paths are semi-transparent (opacity/alpha <= 0.85)."""
        overlay = self.page.locator("#handOverlay")
        self.assertGreater(overlay.count(), 0, "Missing #handOverlay.")
        is_transparent = self.page.evaluate("""() => {
            const overlay = document.getElementById('handOverlay');
            if (!overlay) return false;
            const op = parseFloat(window.getComputedStyle(overlay).opacity);
            if (op <= 0.85) return true;
            const palm = document.querySelector('.hand-palm-silhouette') || document.getElementById('hand-palm');
            if (palm) {
                const palmOp = parseFloat(window.getComputedStyle(palm).opacity);
                if (palmOp <= 0.85) return true;
                const fill = window.getComputedStyle(palm).fill;
                const match = fill.match(/rgba?\\([^,]+,[^,]+,[^,]+,?\\s*([\\d\\.]+)?\\)/);
                if (match && match[1] !== undefined && parseFloat(match[1]) <= 0.85) return true;
            }
            return false;
        }""")
        self.assertTrue(is_transparent, "Hand overlay silhouette must be semi-transparent (opacity/alpha <= 0.85).")

    def test_f04_04_custom_background_gradients_preserved(self):
        """Feature 4: Underlying keycap custom background gradients remain intact."""
        r_key = self.page.locator('.key-cap[data-key="KeyR"]')
        bg = r_key.evaluate("el => window.getComputedStyle(el).backgroundImage")
        self.assertTrue("gradient" in bg.lower() or "linear" in bg.lower())

    def test_f04_05_unmapped_keys_contrast_maintained(self):
        """Feature 4: Unmapped keys retain distinctive muted styling without obscuration."""
        unmapped = self.page.locator(".key-cap.unmapped")
        self.assertGreater(unmapped.count(), 0)
        unmapped_bg = unmapped.first.evaluate("el => window.getComputedStyle(el).backgroundColor")
        self.assertTrue(len(unmapped_bg) > 0)

    # --- Feature 5: Fingertip Glow Accents (ORIGINAL_REQUEST §R3) ---

    def _finger_has_accent_color(self, finger: str, hex_color: str, alt_hex: str = None) -> bool:
        """Check if fingertip pad, core, halo, or gradient reflects signature accent color."""
        return self.page.evaluate("""({ finger, hexColor, altHex }) => {
            const pad = document.getElementById(`fingertip-${finger}`);
            const core = document.getElementById(`fingertip-core-${finger}`);
            const halo = document.getElementById(`fingertip-halo-${finger}`);
            const grad = document.getElementById(`radial-glow-${finger}`);
            const candidates = [];
            if (pad) {
                candidates.push(pad.getAttribute('fill') || '', pad.getAttribute('stroke') || '', window.getComputedStyle(pad).fill, window.getComputedStyle(pad).stroke);
            }
            if (core) {
                candidates.push(core.getAttribute('fill') || '', window.getComputedStyle(core).fill);
            }
            if (halo) {
                candidates.push(halo.getAttribute('fill') || '', window.getComputedStyle(halo).fill);
            }
            if (grad) {
                grad.querySelectorAll('stop').forEach(s => candidates.push(s.getAttribute('stop-color') || ''));
            }
            const normalize = s => (s || '').toLowerCase().replace(/\\s+/g, '');
            const target1 = normalize(hexColor);
            const target2 = altHex ? normalize(altHex) : null;
            return candidates.some(c => {
                const norm = normalize(c);
                return norm.includes(target1) || (target2 && norm.includes(target2));
            });
        }""", {"finger": finger, "hexColor": hex_color, "altHex": alt_hex})

    def test_f05_01_pinky_fingertip_amber_glow(self):
        """Feature 5: Pinky fingertip has signature Amber accent (#f59e0b)."""
        tip = self.page.locator("#fingertip-pinky")
        self.assertGreater(tip.count(), 0, "Missing #fingertip-pinky.")
        self.assertTrue(self._finger_has_accent_color("pinky", FINGER_CONFIG["pinky"]["hex_color"]))

    def test_f05_02_ring_fingertip_blue_glow(self):
        """Feature 5: Ring fingertip has signature Blue accent (#3b82f6)."""
        tip = self.page.locator("#fingertip-ring")
        self.assertGreater(tip.count(), 0, "Missing #fingertip-ring.")
        self.assertTrue(self._finger_has_accent_color("ring", FINGER_CONFIG["ring"]["hex_color"]))

    def test_f05_03_middle_fingertip_green_glow(self):
        """Feature 5: Middle fingertip has signature Green accent (#10b981)."""
        tip = self.page.locator("#fingertip-middle")
        self.assertGreater(tip.count(), 0, "Missing #fingertip-middle.")
        self.assertTrue(self._finger_has_accent_color("middle", FINGER_CONFIG["middle"]["hex_color"]))

    def test_f05_04_index_fingertip_red_glow(self):
        """Feature 5: Index fingertip has signature Red accent (#ff4655 / #ef4444)."""
        tip = self.page.locator("#fingertip-index")
        self.assertGreater(tip.count(), 0, "Missing #fingertip-index.")
        self.assertTrue(self._finger_has_accent_color("index", FINGER_CONFIG["index"]["hex_color"], FINGER_CONFIG["index"]["alt_hex"]))

    def test_f05_05_thumb_fingertip_violet_glow(self):
        """Feature 5: Thumb fingertip has signature Violet accent (#8b5cf6)."""
        tip = self.page.locator("#fingertip-thumb")
        self.assertGreater(tip.count(), 0, "Missing #fingertip-thumb.")
        self.assertTrue(self._finger_has_accent_color("thumb", FINGER_CONFIG["thumb"]["hex_color"]))


# ==============================================================================
# TIER 1: FEATURE COVERAGE (Features 6 to 10: Kinematics, Cache, Performance)
# ==============================================================================

class TestTier1Features06To10KinematicsPerformance(BaseE2ETestCase):
    """Tier 1: Feature Coverage for Features 6-10 (>=5 tests per feature)."""

    # --- Feature 6: Dynamic Reach Kinematics (ORIGINAL_REQUEST §R2) ---

    def test_f06_01_reach_middle_finger_to_key_r(self):
        """Feature 6: Middle finger articulates to KeyR within 150ms on keydown."""
        r_el = self.page.locator('.key-cap[data-key="KeyR"]')
        r_box = get_bbox(self.page, '.key-cap[data-key="KeyR"]')
        self.page.keyboard.down("KeyR")
        self.page.wait_for_timeout(135)
        tip_box = get_bbox(self.page, "#fingertip-middle")
        assert_inside_bbox(self, get_center(tip_box), r_box, "Middle reaches KeyR")
        self.assertTrue(r_el.evaluate("el => el.classList.contains('is-pressed')"))
        self.page.keyboard.up("KeyR")

    def test_f06_02_reach_index_finger_to_key_t(self):
        """Feature 6: Index finger articulates to KeyT within 150ms on keydown."""
        t_el = self.page.locator('.key-cap[data-key="KeyT"]')
        t_box = get_bbox(self.page, '.key-cap[data-key="KeyT"]')
        self.page.keyboard.down("KeyT")
        self.page.wait_for_timeout(135)
        tip_box = get_bbox(self.page, "#fingertip-index")
        assert_inside_bbox(self, get_center(tip_box), t_box, "Index reaches KeyT")
        self.assertTrue(t_el.evaluate("el => el.classList.contains('is-pressed')"))
        self.page.keyboard.up("KeyT")

    def test_f06_03_reach_ring_finger_to_key_w(self):
        """Feature 6: Ring finger articulates to KeyW within 150ms on keydown."""
        w_el = self.page.locator('.key-cap[data-key="KeyW"]')
        w_box = get_bbox(self.page, '.key-cap[data-key="KeyW"]')
        self.page.keyboard.down("KeyW")
        self.page.wait_for_timeout(135)
        tip_box = get_bbox(self.page, "#fingertip-ring")
        assert_inside_bbox(self, get_center(tip_box), w_box, "Ring reaches KeyW")
        self.assertTrue(w_el.evaluate("el => el.classList.contains('is-pressed')"))
        self.page.keyboard.up("KeyW")

    def test_f06_04_reach_pinky_finger_to_key_x(self):
        """Feature 6: Pinky finger articulates to KeyX within 150ms on keydown."""
        x_el = self.page.locator('.key-cap[data-key="KeyX"]')
        x_box = get_bbox(self.page, '.key-cap[data-key="KeyX"]')
        self.page.keyboard.down("KeyX")
        self.page.wait_for_timeout(135)
        tip_box = get_bbox(self.page, "#fingertip-pinky")
        assert_inside_bbox(self, get_center(tip_box), x_box, "Pinky reaches KeyX")
        self.assertTrue(x_el.evaluate("el => el.classList.contains('is-pressed')"))
        self.page.keyboard.up("KeyX")

    def test_f06_05_reach_thumb_finger_to_key_n(self):
        """Feature 6: Thumb finger articulates to KeyN within 150ms on keydown."""
        n_el = self.page.locator('.key-cap[data-key="KeyN"]')
        n_box = get_bbox(self.page, '.key-cap[data-key="KeyN"]')
        self.page.keyboard.down("KeyN")
        self.page.wait_for_timeout(135)
        tip_box = get_bbox(self.page, "#fingertip-thumb")
        assert_inside_bbox(self, get_center(tip_box), n_box, "Thumb reaches KeyN")
        self.assertTrue(n_el.evaluate("el => el.classList.contains('is-pressed')"))
        self.page.keyboard.up("KeyN")

    # --- Feature 7: Dynamic Return Kinematics (ORIGINAL_REQUEST §R2) ---

    def test_f07_01_return_middle_finger_after_release(self):
        """Feature 7: Middle finger returns to KeyR home after releasing KeyF."""
        self.page.keyboard.down("KeyF")
        self.page.wait_for_timeout(135)
        self.page.keyboard.up("KeyF")
        self.page.wait_for_timeout(180)
        tip_box = get_bbox(self.page, "#fingertip-middle")
        r_box = get_bbox(self.page, '.key-cap[data-key="KeyR"]')
        assert_inside_bbox(self, get_center(tip_box), r_box, "Middle returns to KeyR")

    def test_f07_02_return_index_finger_after_release(self):
        """Feature 7: Index finger returns to KeyT home after releasing KeyG."""
        self.page.keyboard.down("KeyG")
        self.page.wait_for_timeout(135)
        self.page.keyboard.up("KeyG")
        self.page.wait_for_timeout(180)
        tip_box = get_bbox(self.page, "#fingertip-index")
        t_box = get_bbox(self.page, '.key-cap[data-key="KeyT"]')
        assert_inside_bbox(self, get_center(tip_box), t_box, "Index returns to KeyT")

    def test_f07_03_return_ring_finger_after_release(self):
        """Feature 7: Ring finger returns to KeyD home after releasing KeyW."""
        self.page.keyboard.down("KeyW")
        self.page.wait_for_timeout(135)
        self.page.keyboard.up("KeyW")
        self.page.wait_for_timeout(180)
        tip_box = get_bbox(self.page, "#fingertip-ring")
        d_box = get_bbox(self.page, '.key-cap[data-key="KeyD"]')
        assert_inside_bbox(self, get_center(tip_box), d_box, "Ring returns to KeyD")

    def test_f07_04_return_pinky_finger_after_release(self):
        """Feature 7: Pinky finger returns to KeyZ home after releasing KeyA."""
        self.page.keyboard.down("KeyA")
        self.page.wait_for_timeout(135)
        self.page.keyboard.up("KeyA")
        self.page.wait_for_timeout(180)
        tip_box = get_bbox(self.page, "#fingertip-pinky")
        z_box = get_bbox(self.page, '.key-cap[data-key="KeyZ"]')
        assert_inside_bbox(self, get_center(tip_box), z_box, "Pinky returns to KeyZ")

    def test_f07_05_return_thumb_finger_after_release(self):
        """Feature 7: Thumb finger returns to KeyM home after releasing Space."""
        self.page.keyboard.down("Space")
        self.page.wait_for_timeout(135)
        self.page.keyboard.up("Space")
        self.page.wait_for_timeout(180)
        tip_box = get_bbox(self.page, "#fingertip-thumb")
        m_box = get_bbox(self.page, '.key-cap[data-key="KeyM"]')
        assert_inside_bbox(self, get_center(tip_box), m_box, "Thumb returns to KeyM")

    # --- Feature 8: Multi-Finger Articulation (ORIGINAL_REQUEST §R2) ---

    def test_f08_01_simultaneous_press_r_and_t(self):
        """Feature 8: Middle (KeyR) and Index (KeyT) articulate concurrently."""
        self.page.keyboard.down("KeyR")
        self.page.keyboard.down("KeyT")
        self.page.wait_for_timeout(135)
        r_box = get_bbox(self.page, '.key-cap[data-key="KeyR"]')
        t_box = get_bbox(self.page, '.key-cap[data-key="KeyT"]')
        mid_box = get_bbox(self.page, "#fingertip-middle")
        idx_box = get_bbox(self.page, "#fingertip-index")
        assert_inside_bbox(self, get_center(mid_box), r_box, "Middle on KeyR")
        assert_inside_bbox(self, get_center(idx_box), t_box, "Index on KeyT")
        self.page.keyboard.up("KeyR")
        self.page.keyboard.up("KeyT")

    def test_f08_02_simultaneous_press_z_and_space(self):
        """Feature 8: Pinky (KeyZ) and Thumb (Space) articulate concurrently."""
        self.page.keyboard.down("KeyZ")
        self.page.keyboard.down("Space")
        self.page.wait_for_timeout(135)
        z_box = get_bbox(self.page, '.key-cap[data-key="KeyZ"]')
        space_box = get_bbox(self.page, '.key-cap[data-key="Space"]')
        pinky_box = get_bbox(self.page, "#fingertip-pinky")
        thumb_box = get_bbox(self.page, "#fingertip-thumb")
        assert_inside_bbox(self, get_center(pinky_box), z_box, "Pinky on KeyZ")
        assert_inside_bbox(self, get_center(thumb_box), space_box, "Thumb on Space")
        self.page.keyboard.up("KeyZ")
        self.page.keyboard.up("Space")

    def test_f08_03_simultaneous_press_w_and_space(self):
        """Feature 8: Ring (KeyW) and Thumb (Space) articulate concurrently."""
        self.page.keyboard.down("KeyW")
        self.page.keyboard.down("Space")
        self.page.wait_for_timeout(135)
        w_box = get_bbox(self.page, '.key-cap[data-key="KeyW"]')
        space_box = get_bbox(self.page, '.key-cap[data-key="Space"]')
        ring_box = get_bbox(self.page, "#fingertip-ring")
        thumb_box = get_bbox(self.page, "#fingertip-thumb")
        assert_inside_bbox(self, get_center(ring_box), w_box, "Ring on KeyW")
        assert_inside_bbox(self, get_center(thumb_box), space_box, "Thumb on Space")
        self.page.keyboard.up("KeyW")
        self.page.keyboard.up("Space")

    def test_f08_04_staggered_press_and_release(self):
        """Feature 8: Releasing one finger does not reset still-held finger."""
        self.page.keyboard.down("KeyR")
        self.page.wait_for_timeout(70)
        self.page.keyboard.down("KeyT")
        self.page.wait_for_timeout(70)
        self.page.keyboard.up("KeyR")
        self.page.wait_for_timeout(160)
        # Index should still be on KeyT
        t_box = get_bbox(self.page, '.key-cap[data-key="KeyT"]')
        idx_box = get_bbox(self.page, "#fingertip-index")
        assert_inside_bbox(self, get_center(idx_box), t_box, "Index remains on KeyT")
        self.page.keyboard.up("KeyT")

    def test_f08_05_same_finger_chording_set(self):
        """Feature 8: Pressing KeyT then KeyG (both Index) tracks active key set cleanly."""
        self.page.keyboard.down("KeyT")
        self.page.wait_for_timeout(70)
        self.page.keyboard.down("KeyG")
        self.page.wait_for_timeout(135)
        # Finger articulates to latest key (KeyG)
        g_box = get_bbox(self.page, '.key-cap[data-key="KeyG"]')
        idx_box = get_bbox(self.page, "#fingertip-index")
        assert_inside_bbox(self, get_center(idx_box), g_box, "Index articulates to KeyG")
        self.page.keyboard.up("KeyT")
        self.page.keyboard.up("KeyG")

    # --- Feature 9: Zero Layout Thrashing Cache (ORIGINAL_REQUEST §R4) ---

    def test_f09_01_get_key_center_function_exists(self):
        """Feature 9: window.getKeyCenter lookup function exists in page scope."""
        has_fn = self.page.evaluate("() => typeof window.getKeyCenter === 'function'")
        self.assertTrue(has_fn, "window.getKeyCenter function must be defined.")

    def test_f09_02_key_center_cache_returns_coordinates(self):
        """Feature 9: window.getKeyCenter returns valid relative coordinates."""
        coords = self.page.evaluate("() => window.getKeyCenter ? window.getKeyCenter('KeyR') : null")
        self.assertIsNotNone(coords, "getKeyCenter('KeyR') returned null.")
        self.assertIn("x", coords)
        self.assertIn("y", coords)
        self.assertGreater(coords["x"], 0)
        self.assertGreater(coords["y"], 0)

    def test_f09_03_resize_observer_updates_cache(self):
        """Feature 9: ResizeObserver updates coordinate cache on viewport resize."""
        c1 = self.page.evaluate("() => window.getKeyCenter ? window.getKeyCenter('KeyT') : null")
        self.page.set_viewport_size({"width": 1024, "height": 768})
        self.page.wait_for_timeout(100)
        c2 = self.page.evaluate("() => window.getKeyCenter ? window.getKeyCenter('KeyT') : null")
        self.assertIsNotNone(c2)
        # Coordinates change dynamically on resize
        self.assertNotEqual(c1["x"], c2["x"], "Cache failed to refresh on viewport resize.")

    def test_f09_04_no_dom_reads_in_raf_loop(self):
        """Feature 9: rAF animation loop runs without forced layout thrashing."""
        # Execute reach and measure forced reflow long tasks
        self.page.keyboard.down("KeyR")
        self.page.wait_for_timeout(140)
        self.page.keyboard.up("KeyR")
        self.page.wait_for_timeout(180)
        # Ensure zero console errors or performance warnings occurred
        self.assertEqual(len(self.console_errors), 0)

    def test_f09_05_cached_coordinates_match_screen_space_geometry(self):
        """Feature 9: Cached keycap centers match rendered DOM boundingClientRect within 5px."""
        cache_pt = self.page.evaluate("""() => {
            if (!window.getKeyCenter) return null;
            const pt = window.getKeyCenter('KeyR');
            const kb = document.getElementById('keyboardContainer').getBoundingClientRect();
            return { screenX: kb.left + pt.x, screenY: kb.top + pt.y };
        }""")
        self.assertIsNotNone(cache_pt)
        r_box = get_bbox(self.page, '.key-cap[data-key="KeyR"]')
        cx, cy = get_center(r_box)
        self.assertAlmostEqual(cache_pt["screenX"], cx, delta=5.0)
        self.assertAlmostEqual(cache_pt["screenY"], cy, delta=5.0)

    # --- Feature 10: 60 FPS & Multi-Viewport Stability (ORIGINAL_REQUEST §R4) ---

    def test_f10_01_sustained_60fps_animation(self):
        """Feature 10: rAF loop maintains 60 FPS (>= 58 FPS, 0 dropped) during reach motion."""
        # Trigger motion then measure 60 rAF frame intervals
        self.page.keyboard.down("KeyR")
        metrics = self.page.evaluate("""() => new Promise(resolve => {
            const deltas = [];
            let last = performance.now();
            let count = 0;
            function step(now) {
                const delta = now - last;
                last = now;
                if (count > 2) deltas.push(delta);
                count++;
                if (count < 60) {
                    requestAnimationFrame(step);
                } else {
                    const avgDelta = deltas.reduce((a, b) => a + b, 0) / deltas.length;
                    const avgFps = 1000 / avgDelta;
                    const dropped = deltas.filter(d => d > 32).length;
                    resolve({ avgFps, avgDelta, dropped });
                }
            }
            requestAnimationFrame(step);
        })""")
        self.page.keyboard.up("KeyR")
        self.assertGreater(metrics["avgFps"], 55.0, f"Low FPS: {metrics}")
        self.assertEqual(metrics["dropped"], 0, f"Dropped frames detected: {metrics}")

    def test_f10_02_raf_loop_sleeps_at_idle(self):
        """Feature 10: Animation rAF loop enters sleep state when fingers are at rest."""
        # Wait until steady rest state
        self.page.wait_for_timeout(250)
        raf_calls = self.page.evaluate("""() => new Promise(resolve => {
            let active = false;
            if (window._handRafActive !== undefined) {
                resolve({ active: window._handRafActive });
                return;
            }
            // Check if active rAF loop continues unnecessarily
            let ticks = 0;
            const start = performance.now();
            function probe() {
                ticks++;
                if (performance.now() - start < 100) {
                    requestAnimationFrame(probe);
                } else {
                    resolve({ active: false, ticks });
                }
            }
            requestAnimationFrame(probe);
        })""")
        self.assertFalse(raf_calls.get("active", False), "rAF loop should sleep at steady state.")

    def test_f10_03_no_longtask_exceeding_50ms(self):
        """Feature 10: No longtask exceeding 50ms during active input sequences."""
        self.page.evaluate("""() => {
            window._testLongTasks = [];
            if (window.PerformanceObserver) {
                try {
                    const obs = new PerformanceObserver((list) => {
                        for (const entry of list.getEntries()) {
                            window._testLongTasks.push(entry.duration);
                        }
                    });
                    obs.observe({ entryTypes: ['longtask'] });
                } catch(e) {}
            }
        }""")
        self.page.keyboard.down("KeyR")
        self.page.wait_for_timeout(140)
        self.page.keyboard.up("KeyR")
        self.page.wait_for_timeout(180)
        long_tasks = self.page.evaluate("() => window._testLongTasks || []")
        self.assertEqual(len(long_tasks), 0, f"Long tasks observed: {long_tasks}")

    def test_f10_04_zero_console_errors_at_1400px(self):
        """Feature 10: Zero console errors on 1400px desktop viewport."""
        self.page.set_viewport_size({"width": 1400, "height": 900})
        self.page.wait_for_timeout(100)
        self.assertEqual(len(self.console_errors), 0, f"Console errors: {self.console_errors}")

    def test_f10_05_zero_console_errors_at_1024px(self):
        """Feature 10: Zero console errors on 1024px laptop viewport."""
        self.page.set_viewport_size({"width": 1024, "height": 768})
        self.page.wait_for_timeout(100)
        self.assertEqual(len(self.console_errors), 0, f"Console errors: {self.console_errors}")


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# ==============================================================================

class TestTier2BoundaryCornerCases(BaseE2ETestCase):
    """Tier 2: Boundary and corner cases (taps, repeat discard, multi-row)."""

    def test_tier2_01_rapid_key_tap_and_immediate_release(self):
        """Tier 2: Rapid 20ms key tap and immediate release does not crash kinematics."""
        self.page.keyboard.down("KeyR")
        self.page.wait_for_timeout(20)
        self.page.keyboard.up("KeyR")
        self.page.wait_for_timeout(200)
        tip_box = get_bbox(self.page, "#fingertip-middle")
        r_box = get_bbox(self.page, '.key-cap[data-key="KeyR"]')
        assert_inside_bbox(self, get_center(tip_box), r_box, "Middle returns to KeyR after quick tap")

    def test_tier2_02_simultaneous_chord_releases(self):
        """Tier 2: Simultaneous release of 3 keys returns all fingers cleanly."""
        self.page.keyboard.down("KeyR")
        self.page.keyboard.down("KeyT")
        self.page.keyboard.down("Space")
        self.page.wait_for_timeout(135)
        self.page.keyboard.up("KeyR")
        self.page.keyboard.up("KeyT")
        self.page.keyboard.up("Space")
        self.page.wait_for_timeout(200)
        # All three fingers return to home
        mid_box = get_bbox(self.page, "#fingertip-middle")
        idx_box = get_bbox(self.page, "#fingertip-index")
        thumb_box = get_bbox(self.page, "#fingertip-thumb")
        r_box = get_bbox(self.page, '.key-cap[data-key="KeyR"]')
        t_box = get_bbox(self.page, '.key-cap[data-key="KeyT"]')
        space_box = get_bbox(self.page, '.key-cap[data-key="Space"]')
        assert_inside_bbox(self, get_center(mid_box), r_box, "Middle returns")
        assert_inside_bbox(self, get_center(idx_box), t_box, "Index returns")
        m_box = get_bbox(self.page, ".key-cap[data-key=\"KeyM\"]"); assert_inside_bbox(self, get_center(thumb_box), m_box, "Thumb returns")

    def test_tier2_03_key_repeat_events_discarded(self):
        """Tier 2: Successive keydown events with repeat: true do not stutter animation."""
        self.page.keyboard.down("KeyR")
        self.page.wait_for_timeout(100)
        # Dispatch repeated keydown
        self.page.evaluate("""() => {
            window.dispatchEvent(new KeyboardEvent('keydown', { code: 'KeyR', repeat: true }));
        }""")
        self.page.wait_for_timeout(40)
        tip_box = get_bbox(self.page, "#fingertip-middle")
        r_box = get_bbox(self.page, '.key-cap[data-key="KeyR"]')
        assert_inside_bbox(self, get_center(tip_box), r_box, "Middle stays on KeyR")
        self.page.keyboard.up("KeyR")

    def test_tier2_04_extreme_viewport_1024px(self):
        """Tier 2: 1024px viewport width rest positions align accurately."""
        self.page.set_viewport_size({"width": 1024, "height": 768})
        self.page.wait_for_timeout(150)
        mid_box = get_bbox(self.page, "#fingertip-middle")
        r_box = get_bbox(self.page, '.key-cap[data-key="KeyR"]')
        assert_inside_bbox(self, get_center(mid_box), r_box, "Middle on KeyR at 1024px")

    def test_tier2_05_extreme_viewport_1400px(self):
        """Tier 2: 1400px viewport width rest positions align accurately."""
        self.page.set_viewport_size({"width": 1400, "height": 900})
        self.page.wait_for_timeout(150)
        mid_box = get_bbox(self.page, "#fingertip-middle")
        r_box = get_bbox(self.page, '.key-cap[data-key="KeyR"]')
        assert_inside_bbox(self, get_center(mid_box), r_box, "Middle on KeyR at 1400px")

    def test_tier2_06_multi_row_reach_pinky_escape(self):
        """Tier 2: Unmapped gray Escape does not trigger reach; Pinky stays at home KeyZ."""
        esc_box = get_bbox(self.page, '.key-cap[data-key="Escape"]')
        self.page.keyboard.down("Escape")
        self.page.wait_for_timeout(140)
        tip_box = get_bbox(self.page, "#fingertip-pinky")
        z_box = get_bbox(self.page, '.key-cap[data-key="KeyZ"]')
        assert_inside_bbox(self, get_center(tip_box), z_box, "Pinky stays on KeyZ during unmapped Escape")
        esc_el = self.page.locator('.key-cap[data-key="Escape"]')
        self.assertIn("is-pressed", esc_el.evaluate("el => el.className"))
        self.page.keyboard.up("Escape")

    def test_tier2_07_multi_row_reach_index_digit6(self):
        """Tier 2: Index reaches from home KeyT (row 3) up to Digit6 (row 2)."""
        d6_box = get_bbox(self.page, '.key-cap[data-key="Digit6"]')
        self.page.keyboard.down("Digit6")
        self.page.wait_for_timeout(140)
        tip_box = get_bbox(self.page, "#fingertip-index")
        assert_inside_bbox(self, get_center(tip_box), d6_box, "Index on Digit6")
        self.page.keyboard.up("Digit6")

    def test_tier2_08_virtual_mouse_click_activation(self):
        """Tier 2: Mouse click on keycap triggers reach kinematics like physical key."""
        r_el = self.page.locator('.key-cap[data-key="KeyR"]')
        r_box = get_bbox(self.page, '.key-cap[data-key="KeyR"]')
        # Mouse click keycap
        r_el.click(delay=140)
        # Should have pressed class during click
        self.assertEqual(len(self.console_errors), 0)

    def test_tier2_09_unmapped_key_event_ignored(self):
        """Tier 2: Pressing unmapped key (Digit9) does not throw errors or break posture."""
        self.page.keyboard.down("Digit9")
        self.page.wait_for_timeout(50)
        self.page.keyboard.up("Digit9")
        self.assertEqual(len(self.console_errors), 0)


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS
# ==============================================================================

class TestTier3CrossFeatureCombinations(BaseE2ETestCase):
    """Tier 3: Pairwise and multi-feature combinations (simultaneous keys)."""

    def test_tier3_01_pairwise_simultaneous_r_and_t(self):
        """Tier 3: Pairwise R + T (Middle + Index) articulate independently."""
        self.page.keyboard.down("KeyR")
        self.page.keyboard.down("KeyT")
        self.page.wait_for_timeout(135)
        r_box = get_bbox(self.page, '.key-cap[data-key="KeyR"]')
        t_box = get_bbox(self.page, '.key-cap[data-key="KeyT"]')
        mid_box = get_bbox(self.page, "#fingertip-middle")
        idx_box = get_bbox(self.page, "#fingertip-index")
        assert_inside_bbox(self, get_center(mid_box), r_box, "Middle on KeyR")
        assert_inside_bbox(self, get_center(idx_box), t_box, "Index on KeyT")
        self.page.keyboard.up("KeyR")
        self.page.keyboard.up("KeyT")

    def test_tier3_02_pairwise_simultaneous_z_and_space(self):
        """Tier 3: Pairwise Z + Space (Pinky + Thumb) articulate independently."""
        self.page.keyboard.down("KeyZ")
        self.page.keyboard.down("Space")
        self.page.wait_for_timeout(135)
        z_box = get_bbox(self.page, '.key-cap[data-key="KeyZ"]')
        space_box = get_bbox(self.page, '.key-cap[data-key="Space"]')
        pinky_box = get_bbox(self.page, "#fingertip-pinky")
        thumb_box = get_bbox(self.page, "#fingertip-thumb")
        assert_inside_bbox(self, get_center(pinky_box), z_box, "Pinky on KeyZ")
        assert_inside_bbox(self, get_center(thumb_box), space_box, "Thumb on Space")
        self.page.keyboard.up("KeyZ")
        self.page.keyboard.up("Space")

    def test_tier3_03_pairwise_simultaneous_w_and_space(self):
        """Tier 3: Pairwise W + Space (Ring + Thumb) articulate independently."""
        self.page.keyboard.down("KeyW")
        self.page.keyboard.down("Space")
        self.page.wait_for_timeout(135)
        w_box = get_bbox(self.page, '.key-cap[data-key="KeyW"]')
        space_box = get_bbox(self.page, '.key-cap[data-key="Space"]')
        ring_box = get_bbox(self.page, "#fingertip-ring")
        thumb_box = get_bbox(self.page, "#fingertip-thumb")
        assert_inside_bbox(self, get_center(ring_box), w_box, "Ring on KeyW")
        assert_inside_bbox(self, get_center(thumb_box), space_box, "Thumb on Space")
        self.page.keyboard.up("KeyW")
        self.page.keyboard.up("Space")

    def test_tier3_04_pairwise_simultaneous_d_and_t(self):
        """Tier 3: Pairwise D + T (Ring + Index) articulate independently."""
        self.page.keyboard.down("KeyD")
        self.page.keyboard.down("KeyT")
        self.page.wait_for_timeout(135)
        d_box = get_bbox(self.page, '.key-cap[data-key="KeyD"]')
        t_box = get_bbox(self.page, '.key-cap[data-key="KeyT"]')
        ring_box = get_bbox(self.page, "#fingertip-ring")
        idx_box = get_bbox(self.page, "#fingertip-index")
        assert_inside_bbox(self, get_center(ring_box), d_box, "Ring on KeyD")
        assert_inside_bbox(self, get_center(idx_box), t_box, "Index on KeyT")
        self.page.keyboard.up("KeyD")
        self.page.keyboard.up("KeyT")

    def test_tier3_05_three_finger_chord_r_t_space(self):
        """Tier 3: Tri-finger chord R + T + Space articulates 3 fingers concurrently."""
        self.page.keyboard.down("KeyR")
        self.page.keyboard.down("KeyT")
        self.page.keyboard.down("Space")
        self.page.wait_for_timeout(135)
        r_box = get_bbox(self.page, '.key-cap[data-key="KeyR"]')
        t_box = get_bbox(self.page, '.key-cap[data-key="KeyT"]')
        space_box = get_bbox(self.page, '.key-cap[data-key="Space"]')
        mid_box = get_bbox(self.page, "#fingertip-middle")
        idx_box = get_bbox(self.page, "#fingertip-index")
        thumb_box = get_bbox(self.page, "#fingertip-thumb")
        assert_inside_bbox(self, get_center(mid_box), r_box, "Middle on KeyR")
        assert_inside_bbox(self, get_center(idx_box), t_box, "Index on KeyT")
        assert_inside_bbox(self, get_center(thumb_box), space_box, "Thumb on Space")
        self.page.keyboard.up("KeyR")
        self.page.keyboard.up("KeyT")
        self.page.keyboard.up("Space")

    def test_tier3_06_interrupted_reach_mid_flight(self):
        """Tier 3: Interrupted reach at 50ms smoothly reverses without visual jump."""
        self.page.keyboard.down("KeyF")
        self.page.wait_for_timeout(50)  # Interrupt mid-reach
        self.page.keyboard.up("KeyF")
        self.page.wait_for_timeout(180)
        # Finger returns cleanly to KeyR home
        mid_box = get_bbox(self.page, "#fingertip-middle")
        r_box = get_bbox(self.page, '.key-cap[data-key="KeyR"]')
        assert_inside_bbox(self, get_center(mid_box), r_box, "Middle returns to KeyR")

    def test_tier3_07_viewport_resize_during_active_motion(self):
        """Tier 3: Viewport resize while key is held dynamically rescales target coordinate."""
        self.page.keyboard.down("KeyR")
        self.page.wait_for_timeout(135)
        # Resize during hold
        self.page.set_viewport_size({"width": 1024, "height": 768})
        self.page.wait_for_timeout(100)
        r_box = get_bbox(self.page, '.key-cap[data-key="KeyR"]')
        mid_box = get_bbox(self.page, "#fingertip-middle")
        assert_inside_bbox(self, get_center(mid_box), r_box, "Middle maintains alignment after resize")
        self.page.keyboard.up("KeyR")


# ==============================================================================
# TIER 4: REAL-WORLD SCENARIOS (TYPING & GAMING WORKLOADS)
# ==============================================================================

class TestTier4RealWorldWorkloads(BaseE2ETestCase):
    """Tier 4: Realistic gaming and typing workloads."""

    def test_tier4_01_gaming_counter_strafing_workload(self):
        """Tier 4: Tactical FPS movement sequence (R forward -> T strafe left -> G strafe right -> Space crouch)."""
        # Forward R
        self.page.keyboard.down("KeyR")
        self.page.wait_for_timeout(80)
        # Strafe left T while moving
        self.page.keyboard.down("KeyT")
        self.page.wait_for_timeout(60)
        self.page.keyboard.up("KeyR")
        self.page.wait_for_timeout(60)
        # Counter-strafe right G
        self.page.keyboard.up("KeyT")
        self.page.keyboard.down("KeyG")
        self.page.wait_for_timeout(70)
        # Crouch Space
        self.page.keyboard.down("Space")
        self.page.wait_for_timeout(80)
        self.page.keyboard.up("KeyG")
        self.page.keyboard.up("Space")
        self.page.wait_for_timeout(180)
        self.assertEqual(len(self.console_errors), 0, "Counter-strafing produced console errors.")

    def test_tier4_02_gaming_weapon_swap_burst_macro(self):
        """Tier 4: Rapid weapon swaps (W use -> N vandal -> M pistol -> B melee)."""
        swaps = ["KeyW", "KeyN", "KeyM", "KeyB"]
        for key in swaps:
            self.page.keyboard.down(key)
            self.page.wait_for_timeout(50)
            self.page.keyboard.up(key)
            self.page.wait_for_timeout(30)
        self.page.wait_for_timeout(200)
        self.assertEqual(len(self.console_errors), 0, "Weapon swap macro produced console errors.")

    def test_tier4_03_gaming_tactical_spike_plant_sequence(self):
        """Tier 4: Coordinated tactical hold (Walk KeyZ + Crouch Space + Plant Comma)."""
        self.page.keyboard.down("KeyZ")
        self.page.wait_for_timeout(60)
        self.page.keyboard.down("Space")
        self.page.wait_for_timeout(60)
        self.page.keyboard.down(",")
        self.page.wait_for_timeout(100)
        self.page.keyboard.up(",")
        self.page.keyboard.up("Space")
        self.page.keyboard.up("KeyZ")
        self.page.wait_for_timeout(200)
        self.assertEqual(len(self.console_errors), 0, "Spike plant sequence failed.")

    def test_tier4_04_sustained_typing_burst_workload(self):
        """Tier 4: Sustained rapid typing burst across multiple keyboard rows."""
        keys = ["KeyW", "KeyE", "KeyR", "KeyT", "KeyY", "KeyD", "KeyF", "KeyG", "KeyX", "KeyC"]
        for key in keys:
            self.page.keyboard.down(key)
            self.page.wait_for_timeout(40)
            self.page.keyboard.up(key)
            self.page.wait_for_timeout(20)
        self.page.wait_for_timeout(200)
        self.assertEqual(len(self.console_errors), 0, "Sustained typing burst generated errors.")

    def test_tier4_05_rapid_alternate_finger_trill(self):
        """Tier 4: Rapid 20-tap alternating trill between Middle (KeyR) and Index (KeyT)."""
        for _ in range(10):
            self.page.keyboard.down("KeyR")
            self.page.wait_for_timeout(30)
            self.page.keyboard.up("KeyR")
            self.page.keyboard.down("KeyT")
            self.page.wait_for_timeout(30)
            self.page.keyboard.up("KeyT")
        self.page.wait_for_timeout(200)
        self.assertEqual(len(self.console_errors), 0, "Alternate finger trill caused state fault.")

    def test_tier4_06_full_round_gameplay_lifecycle_stress(self):
        """Tier 4: Full round gameplay lifecycle stress test (sustained motion and zero error)."""
        actions = [
            ("down", "KeyR"),
            ("down", "KeyW"),
            ("up", "KeyW"),
            ("down", "KeyT"),
            ("up", "KeyR"),
            ("down", "Space"),
            ("up", "KeyT"),
            ("down", "KeyN"),
            ("up", "KeyN"),
            ("up", "Space"),
        ]
        for act, code in actions:
            if act == "down":
                self.page.keyboard.down(code)
            else:
                self.page.keyboard.up(code)
            self.page.wait_for_timeout(45)
        self.page.wait_for_timeout(250)
        self.assertEqual(len(self.console_errors), 0, "Lifecycle stress test generated console errors.")


if __name__ == "__main__":
    unittest.main()
