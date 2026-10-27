"""
Adversarial Stress Test Suite: Tier 5 Event & State Edge Cases (Part 1)
Milestone 3 Phase 2 — Empirical Challenger 1 (challenger_tier5_1)

Adversarial Stress Dimensions:
1. Unmapped & Modifier Key Edge Cases:
   - Completely unmapped keys (F11, F12, Backslash, ScrollLock, NumLock, PrintScreen, Pause, ContextMenu)
   - Mapped modifier keys (ShiftLeft, ShiftRight, AltLeft, ControlLeft, MetaLeft)
   - Unmapped modifier variants (AltRight, ControlRight, MetaRight)
   - Repeated/burst hammering of unmapped and modifier keys
   - Malformed/falsy inputs to activateKey and deactivateKey ("", null, undefined, unknown keys)
   - Assert zero console errors, zero stuck states, fingers remain at rest for unmapped keys.

2. Window Blur & Focus Switching Lifecycle:
   - Window blur while single key held
   - Window blur while multi-finger chord held (KeyW + KeyR + KeyT + Space)
   - Window blur dispatched mid-flight during reach animation (~40ms)
   - Focus recovery and subsequent release of held keys
   - Assert rAF loop settles to idle sleep (window._handRafActive is false), no infinite spinning, zero errors.

3. Intra-Finger Queue Scramble & Out-of-Order Release:
   - 3 keys held on Index (Digit4, KeyT, KeyG) released in permutations:
     * Middle key first, then last, then first
     * Last key first, then first, then middle
     * First key first, then middle, then last
   - Intra-finger scramble on Pinky (KeyZ, KeyA, ShiftLeft)
   - Intra-finger scramble on Ring (KeyW, KeyD, KeyC)
   - Intra-finger scramble on Thumb (KeyV, KeyB, Space)
   - High-speed 4-key intra-finger churning
   - Assert proper retargeting to remaining held keys and eventual clean return to home posture.

4. Rapid Simultaneous Space & Virtual Mouse-Drag Interactions:
   - Rapid Spacebar spam while dragging mouse over virtual keycaps
   - Interleaved mouse clicks and Space keydowns
   - Rapid mouseup with multiple keys active
   - Assert event stability, zero stuck classes, fingers settle to rest, rAF loop sleeps.
"""

import math
import os
import sys
import time
import unittest
from typing import Dict, List, Tuple
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests.helpers import (
    HTML_URL,
    FINGER_CONFIG,
    get_bbox,
    get_center,
    assert_inside_bbox,
    reset_page_state,
)


class Tier5AdversarialPart1Suite(unittest.TestCase):
    """Tier 5 white-box adversarial stress test suite for event and state edge cases."""

    playwright = None
    browser = None
    context = None
    page = None
    console_errors: List[str] = []

    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(channel="chrome", headless=True)
        cls.context = cls.browser.new_context(viewport={"width": 1400, "height": 900})
        cls.page = cls.context.new_page()
        cls.console_errors = []
        cls.page.on(
            "console",
            lambda msg: cls.console_errors.append(msg.text) if msg.type == "error" else None,
        )
        cls.page.on("pageerror", lambda err: cls.console_errors.append(str(err)))
        cls.page.goto(HTML_URL)
        cls.page.locator("#ch5").scroll_into_view_if_needed()
        cls.page.wait_for_timeout(350)

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
        reset_page_state(self.page)
        self.page.wait_for_timeout(60)

    def tearDown(self):
        reset_page_state(self.page)
        self.page.wait_for_timeout(60)

    # --------------------------------------------------------------------------
    # Helper Assertions
    # --------------------------------------------------------------------------

    def _assert_zero_console_errors(self):
        self.assertEqual(
            len(self.console_errors),
            0,
            f"Console errors detected: {self.console_errors}",
        )

    def _assert_finger_at_home(self, finger: str, tolerance: float = 6.0):
        """Assert finger is at its resting home position within tolerance."""
        res = self.page.evaluate(f"""() => {{
            const s = window.fingerState['{finger}'];
            if (!s) return null;
            const dist = Math.hypot(s.current.x - s.home.x, s.current.y - s.home.y);
            return {{
                dist: dist,
                current: s.current,
                home: s.home,
                activeCount: s.activeKeys.size,
                isAnimating: s.isAnimating
            }};
        }}""")
        self.assertIsNotNone(res, f"Finger state for '{finger}' not found.")
        self.assertLessEqual(
            res["dist"],
            tolerance,
            f"Finger '{finger}' not at home: dist={res['dist']:.2f}px (curr={res['current']}, home={res['home']})",
        )
        self.assertEqual(
            res["activeCount"],
            0,
            f"Finger '{finger}' still has {res['activeCount']} active keys.",
        )

    def _assert_all_fingers_at_home(self, tolerance: float = 6.0):
        """Assert all 5 fingers are resting at their respective home keys."""
        for f in ["pinky", "ring", "middle", "index", "thumb"]:
            self._assert_finger_at_home(f, tolerance)

    def _assert_finger_inside_key(self, finger: str, key_code: str, label: str = ""):
        """Assert fingertip is strictly inside keycap bounding box."""
        tip_box = get_bbox(self.page, f"#fingertip-{finger}")
        key_box = get_bbox(self.page, f'.key-cap[data-key="{key_code}"]')
        tip_center = get_center(tip_box)

        if key_code == "Space":
            # Spacebar left zone alignment
            x_min = key_box["x"]
            x_max = key_box["x"] + key_box["width"] * 0.70
            y_min = key_box["y"]
            y_max = key_box["y"] + key_box["height"]
            inside = (x_min <= tip_center[0] <= x_max) and (y_min <= tip_center[1] <= y_max)
            self.assertTrue(
                inside,
                f"Thumb tip ({tip_center[0]:.1f}, {tip_center[1]:.1f}) outside Space left zone [{x_min:.1f}..{x_max:.1f}, {y_min:.1f}..{y_max:.1f}] for {label}",
            )
        else:
            assert_inside_bbox(self, tip_center, key_box, f"{finger} on {key_code} ({label})")

    def _assert_raf_sleeping(self, timeout_ms: int = 300):
        """Poll until window._handRafActive is false, failing if timeout is reached."""
        start = time.time()
        while time.time() - start < (timeout_ms / 1000.0):
            active = self.page.evaluate("() => window._handRafActive")
            if not active:
                return
            self.page.wait_for_timeout(20)
        active = self.page.evaluate("() => window._handRafActive")
        self.assertFalse(active, f"rAF animation loop still active after {timeout_ms}ms idle wait.")

    # ==========================================================================
    # Dimension 1: Unmapped & Modifier Key Edge Cases
    # ==========================================================================

    def test_unmapped_keys_ignored_without_errors(self):
        """Press and release keys completely absent from fingerMap and keyboard layout."""
        unmapped_keys = [
            "F11",
            "F12",
            "Backslash",
            "ScrollLock",
            "NumLock",
            "PrintScreen",
            "Pause",
            "ContextMenu",
            "Insert",
            "Delete",
            "Home",
            "End",
            "PageUp",
            "PageDown",
        ]
        for key in unmapped_keys:
            self.page.keyboard.down(key)
            self.page.wait_for_timeout(25)
            self.page.keyboard.up(key)
            self.page.wait_for_timeout(25)

        self._assert_zero_console_errors()
        self._assert_all_fingers_at_home()
        self._assert_raf_sleeping()

    def test_mapped_modifier_keys_articulate_and_return(self):
        """Test mapped modifiers: ShiftLeft, ShiftRight, AltLeft (colored amber)."""
        modifiers = ["ShiftLeft", "ShiftRight", "AltLeft"]
        for mod in modifiers:
            self.page.keyboard.down(mod)
            self.page.wait_for_timeout(160)

            # Pinky is assigned to mapped tactical modifiers
            # Note: ShiftRight targets ShiftLeft keycap in compact layout
            expected_key = "ShiftLeft" if mod == "ShiftRight" else mod
            self._assert_finger_inside_key("pinky", expected_key, f"Holding {mod}")

            self.page.keyboard.up(mod)
            self.page.wait_for_timeout(200)

            self._assert_finger_at_home("pinky")
            self._assert_raf_sleeping()

        self._assert_zero_console_errors()

    def test_unmapped_modifier_variants_safe(self):
        """Press unmapped modifier variants (AltRight, ControlRight, MetaRight, ControlLeft, MetaLeft)."""
        unmapped_mods = ["AltRight", "ControlRight", "MetaRight", "ControlLeft", "MetaLeft"]
        for mod in unmapped_mods:
            self.page.keyboard.down(mod)
            self.page.wait_for_timeout(60)

            # Confirm no fingers moved away from home posture
            self._assert_all_fingers_at_home(tolerance=6.0)

            self.page.keyboard.up(mod)
            self.page.wait_for_timeout(60)

        self._assert_zero_console_errors()
        self._assert_raf_sleeping()

    def test_falsy_and_boundary_key_invocations(self):
        """Invoke activateKey and deactivateKey directly with boundary and falsy inputs."""
        boundary_inputs = [
            "",
            "   ",
            "UnknownKey999",
            "KeyWith[Bracket]",
            "Quote'Single",
            "Numpad99",
        ]
        for inp in boundary_inputs:
            self.page.evaluate("""(k) => {
                activateKey(k);
                deactivateKey(k);
            }""", inp)

        # Also test null and undefined
        self.page.evaluate("""() => {
            activateKey(null);
            deactivateKey(null);
            activateKey(undefined);
            deactivateKey(undefined);
        }""")

        self.page.wait_for_timeout(100)
        self._assert_zero_console_errors()
        self._assert_all_fingers_at_home()
        self._assert_raf_sleeping()

    def test_unescaped_selector_injection_finding(self):
        """
        White-box vulnerability audit: verify activateKey behavior on unescaped double-quote strings.
        Empirically documents that raw template interpolation without CSS.escape throws DOMException SyntaxError.
        Verifies that page recovers immediately and subsequent valid key presses work normally.
        """
        syntax_error_thrown = self.page.evaluate("""() => {
            let threw = false;
            try {
                activateKey('Malicious"Quote');
            } catch (e) {
                threw = (e instanceof DOMException || e.name === 'SyntaxError');
            }
            try {
                deactivateKey('Malicious"Quote');
            } catch (e) {
                threw = threw && (e instanceof DOMException || e.name === 'SyntaxError');
            }
            return threw;
        }""")
        self.assertTrue(
            syntax_error_thrown,
            "Expected activateKey('Malicious\"Quote') to throw SyntaxError due to unescaped querySelector.",
        )

        # Assert system remains fully functional after the injection attempt
        self.page.keyboard.down("KeyR")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("middle", "KeyR", "Recovery after injection attempt")
        self.page.keyboard.up("KeyR")
        self.page.wait_for_timeout(220)
        self._assert_finger_at_home("middle")
        self._assert_raf_sleeping()
        self._assert_zero_console_errors()

    def test_burst_hammering_unmapped_and_mapped_keys(self):
        """Rapid interwoven hammering of unmapped and mapped keys in 10ms intervals."""
        keys = ["F11", "KeyR", "ScrollLock", "KeyT", "Backslash", "Space", "NumLock"]
        for _ in range(4):
            for k in keys:
                self.page.keyboard.down(k)
                self.page.wait_for_timeout(12)
                self.page.keyboard.up(k)
                self.page.wait_for_timeout(12)

        self.page.wait_for_timeout(250)
        self._assert_zero_console_errors()
        self._assert_all_fingers_at_home()
        self._assert_raf_sleeping()

    # ==========================================================================
    # Dimension 2: Window Blur & Focus Switching Lifecycle
    # ==========================================================================

    def test_window_blur_with_single_key_held(self):
        """Simulate window blur event while a single key is held down."""
        self.page.keyboard.down("KeyR")
        self.page.wait_for_timeout(160)

        # Verify Middle finger reached KeyR
        self._assert_finger_inside_key("middle", "KeyR", "Holding KeyR before blur")

        # Simulate browser window blur
        self.page.evaluate("() => window.dispatchEvent(new Event('blur'))")
        self.page.wait_for_timeout(80)

        # Verify rAF loop does not hang in an infinite loop while held
        self._assert_raf_sleeping(timeout_ms=250)
        self._assert_zero_console_errors()

        # Simulate refocus and key release
        self.page.evaluate("() => window.dispatchEvent(new Event('focus'))")
        self.page.keyboard.up("KeyR")
        self.page.wait_for_timeout(220)

        self._assert_finger_at_home("middle")
        self._assert_raf_sleeping()
        self._assert_zero_console_errors()

    def test_window_blur_with_multi_finger_chord_held(self):
        """Simulate window blur event while a 4-finger chord is actively held."""
        chord = [("ring", "KeyW"), ("middle", "KeyR"), ("index", "KeyT"), ("thumb", "Space")]
        for _, k in chord:
            self.page.keyboard.down(k)
        self.page.wait_for_timeout(160)

        for f, k in chord:
            self._assert_finger_inside_key(f, k, f"Holding {k} in 4-finger chord")

        # Window blur during sustained chord
        self.page.evaluate("() => window.dispatchEvent(new Event('blur'))")
        self.page.wait_for_timeout(80)

        self._assert_raf_sleeping(timeout_ms=250)
        self._assert_zero_console_errors()

        # Refocus and release chord
        self.page.evaluate("() => window.dispatchEvent(new Event('focus'))")
        for _, k in chord:
            self.page.keyboard.up(k)
        self.page.wait_for_timeout(240)

        self._assert_all_fingers_at_home()
        self._assert_raf_sleeping()
        self._assert_zero_console_errors()

    def test_window_blur_mid_flight_during_reach(self):
        """Dispatch window blur event 40ms into reach animation while finger is in flight."""
        self.page.keyboard.down("KeyG")  # Index finger reaches to KeyG
        self.page.wait_for_timeout(40)  # Mid-flight (~33% progress)

        # Dispatch blur event
        self.page.evaluate("() => window.dispatchEvent(new Event('blur'))")
        self.page.wait_for_timeout(150)

        # Animation should complete safely to target without crashing
        self._assert_finger_inside_key("index", "KeyG", "Mid-flight reach completed after blur")
        self._assert_raf_sleeping()
        self._assert_zero_console_errors()

        # Release and return
        self.page.keyboard.up("KeyG")
        self.page.wait_for_timeout(220)

        self._assert_finger_at_home("index")
        self._assert_raf_sleeping()
        self._assert_zero_console_errors()

    # ==========================================================================
    # Dimension 3: Intra-Finger Queue Scramble & Out-of-Order Release
    # ==========================================================================

    def test_index_intra_finger_out_of_order_permutation_1(self):
        """
        Index intra-finger queue: Hold Digit5, KeyT, KeyG.
        Release sequence: KeyT (middle), KeyG (last), Digit5 (first).
        """
        # Step 1: Hold Digit5 -> reaches Digit5
        self.page.keyboard.down("Digit5")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("index", "Digit5", "Holding Digit5")

        # Step 2: Hold KeyT -> retargets to KeyT
        self.page.keyboard.down("KeyT")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("index", "KeyT", "Holding Digit5 + KeyT")

        # Step 3: Hold KeyG -> retargets to KeyG
        self.page.keyboard.down("KeyG")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("index", "KeyG", "Holding Digit5 + KeyT + KeyG")

        # Step 4: Release KeyT (middle key). Active keys remain: {Digit5, KeyG}.
        # Most recent active key in set is KeyG -> finger stays on KeyG.
        self.page.keyboard.up("KeyT")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("index", "KeyG", "Released KeyT, still on KeyG")

        # Step 5: Release KeyG (last key). Active keys remain: {Digit5}.
        # Finger retargets to Digit5.
        self.page.keyboard.up("KeyG")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("index", "Digit5", "Released KeyG, retargeted to Digit5")

        # Step 6: Release Digit5. Active keys empty. Finger returns to home (KeyT).
        self.page.keyboard.up("Digit5")
        self.page.wait_for_timeout(220)
        self._assert_finger_at_home("index")
        self._assert_raf_sleeping()
        self._assert_zero_console_errors()

    def test_index_intra_finger_out_of_order_permutation_2(self):
        """
        Index intra-finger queue: Hold Digit5, KeyT, KeyG.
        Release sequence: KeyG (last), Digit5 (first), KeyT (middle/home).
        """
        self.page.keyboard.down("Digit5")
        self.page.keyboard.down("KeyT")
        self.page.keyboard.down("KeyG")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("index", "KeyG", "Holding Digit5 + KeyT + KeyG")

        # Release KeyG. Remaining: {Digit5, KeyT}. Most recent is KeyT.
        self.page.keyboard.up("KeyG")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("index", "KeyT", "Released KeyG, retargeted to KeyT")

        # Release Digit5. Remaining: {KeyT}. Most recent is KeyT.
        self.page.keyboard.up("Digit5")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("index", "KeyT", "Released Digit5, still on KeyT")

        # Release KeyT. Remaining: empty. Returns to home.
        self.page.keyboard.up("KeyT")
        self.page.wait_for_timeout(220)
        self._assert_finger_at_home("index")
        self._assert_raf_sleeping()
        self._assert_zero_console_errors()

    def test_index_intra_finger_out_of_order_permutation_3(self):
        """
        Index intra-finger queue: Hold Digit5, KeyT, KeyG.
        Release sequence: Digit5 (first), KeyT (middle), KeyG (last).
        """
        self.page.keyboard.down("Digit5")
        self.page.keyboard.down("KeyT")
        self.page.keyboard.down("KeyG")
        self.page.wait_for_timeout(160)

        # Release Digit5. Remaining: {KeyT, KeyG}. Most recent is KeyG.
        self.page.keyboard.up("Digit5")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("index", "KeyG", "Released Digit5, still on KeyG")

        # Release KeyT. Remaining: {KeyG}. Most recent is KeyG.
        self.page.keyboard.up("KeyT")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("index", "KeyG", "Released KeyT, still on KeyG")

        # Release KeyG. Remaining: empty. Returns to home.
        self.page.keyboard.up("KeyG")
        self.page.wait_for_timeout(220)
        self._assert_finger_at_home("index")
        self._assert_raf_sleeping()
        self._assert_zero_console_errors()

    def test_middle_intra_finger_queue_with_digit4(self):
        """Middle finger intra-finger queue: Hold Digit4 (defuse), KeyR (forward), KeyF (backward)."""
        # Step 1: Hold Digit4 -> Middle finger reaches Digit4 in green
        self.page.keyboard.down("Digit4")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("middle", "Digit4", "Middle holding Digit4")

        # Step 2: Hold KeyF -> Middle finger retargets to KeyF
        self.page.keyboard.down("KeyF")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("middle", "KeyF", "Middle holding Digit4 + KeyF")

        # Step 3: Release KeyF -> Middle retargets back to Digit4
        self.page.keyboard.up("KeyF")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("middle", "Digit4", "Middle back to Digit4")

        # Step 4: Release Digit4 -> Middle returns to home KeyR
        self.page.keyboard.up("Digit4")
        self.page.wait_for_timeout(220)
        self._assert_finger_at_home("middle")
        self._assert_raf_sleeping()
        self._assert_zero_console_errors()

    def test_pinky_intra_finger_out_of_order(self):
        """Pinky intra-finger queue: Hold KeyZ, KeyA, ShiftLeft. Release out of order."""
        self.page.keyboard.down("KeyZ")
        self.page.keyboard.down("KeyA")
        self.page.keyboard.down("ShiftLeft")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("pinky", "ShiftLeft", "Holding Z + A + ShiftLeft")

        # Release middle key KeyA
        self.page.keyboard.up("KeyA")
        self.page.wait_for_timeout(140)
        self._assert_finger_inside_key("pinky", "ShiftLeft", "Released KeyA, still ShiftLeft")

        # Release ShiftLeft -> retargets to KeyZ
        self.page.keyboard.up("ShiftLeft")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("pinky", "KeyZ", "Released ShiftLeft, retargeted to KeyZ")

        # Release KeyZ -> returns to home (KeyZ)
        self.page.keyboard.up("KeyZ")
        self.page.wait_for_timeout(220)
        self._assert_finger_at_home("pinky")
        self._assert_raf_sleeping()
        self._assert_zero_console_errors()

    def test_ring_intra_finger_out_of_order(self):
        """Ring intra-finger queue: Hold KeyW, KeyD, KeyC. Release out of order."""
        self.page.keyboard.down("KeyW")
        self.page.keyboard.down("KeyD")
        self.page.keyboard.down("KeyC")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("ring", "KeyC", "Holding W + D + C")

        # Release KeyC -> retargets to KeyD
        self.page.keyboard.up("KeyC")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("ring", "KeyD", "Released KeyC, retargeted to KeyD")

        # Release KeyD -> retargets to KeyW
        self.page.keyboard.up("KeyD")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("ring", "KeyW", "Released KeyD, retargeted to KeyW")

        # Release KeyW -> returns to home (KeyD)
        self.page.keyboard.up("KeyW")
        self.page.wait_for_timeout(220)
        self._assert_finger_at_home("ring")
        self._assert_raf_sleeping()
        self._assert_zero_console_errors()

    def test_thumb_intra_finger_out_of_order(self):
        """Thumb intra-finger queue: Hold KeyV, KeyB, Space. Release out of order."""
        self.page.keyboard.down("KeyV")
        self.page.keyboard.down("KeyB")
        self.page.keyboard.down("Space")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("thumb", "Space", "Holding V + B + Space")

        # Release Space -> retargets to KeyB
        self.page.keyboard.up("Space")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("thumb", "KeyB", "Released Space, retargeted to KeyB")

        # Release KeyB -> retargets to KeyV
        self.page.keyboard.up("KeyB")
        self.page.wait_for_timeout(160)
        self._assert_finger_inside_key("thumb", "KeyV", "Released KeyB, retargeted to KeyV")

        # Release KeyV -> returns to home (Space left zone)
        self.page.keyboard.up("KeyV")
        self.page.wait_for_timeout(220)
        self._assert_finger_at_home("thumb")
        self._assert_raf_sleeping()
        self._assert_zero_console_errors()

    def test_high_speed_intra_finger_churning(self):
        """Rapidly add and remove 4 keys on Index finger in quick succession."""
        keys = ["Digit5", "Digit6", "KeyT", "KeyG"]
        for _ in range(3):
            for k in keys:
                self.page.keyboard.down(k)
                self.page.wait_for_timeout(15)
            for k in reversed(keys):
                self.page.keyboard.up(k)
                self.page.wait_for_timeout(15)

        self.page.wait_for_timeout(240)
        self._assert_finger_at_home("index")
        self._assert_raf_sleeping()
        self._assert_zero_console_errors()

    # ==========================================================================
    # Dimension 4: Rapid Simultaneous Space & Virtual Mouse-Drag Interactions
    # ==========================================================================

    def test_rapid_space_spam_during_mouse_drag_across_keys(self):
        """Spam Spacebar rapidly while dragging the mouse across multiple virtual keycaps."""
        # Get bounding boxes for multiple keys to drag across
        key_r = get_bbox(self.page, '.key-cap[data-key="KeyR"]')
        key_f = get_bbox(self.page, '.key-cap[data-key="KeyF"]')
        key_d = get_bbox(self.page, '.key-cap[data-key="KeyD"]')
        key_t = get_bbox(self.page, '.key-cap[data-key="KeyT"]')

        c_r = get_center(key_r)
        c_f = get_center(key_f)
        c_d = get_center(key_d)
        c_t = get_center(key_t)

        # Start mouse drag at KeyR
        self.page.mouse.move(c_r[0], c_r[1])
        self.page.mouse.down()
        self.page.wait_for_timeout(30)

        # Drag through points while spamming Spacebar
        drag_points = [c_f, c_d, c_t, c_r]
        for pt in drag_points:
            self.page.mouse.move(pt[0], pt[1], steps=3)
            self.page.keyboard.down("Space")
            self.page.wait_for_timeout(20)
            self.page.keyboard.up("Space")
            self.page.wait_for_timeout(20)

        # Release mouse button
        self.page.mouse.up()
        self.page.wait_for_timeout(250)

        # Verify no stuck pressed classes remain
        stuck_pressed = self.page.locator(".key-cap.is-pressed").count()
        self.assertEqual(stuck_pressed, 0, f"Found {stuck_pressed} stuck pressed keycaps after mouse drag.")

        self._assert_all_fingers_at_home()
        self._assert_raf_sleeping()
        self._assert_zero_console_errors()

    def test_interleaved_virtual_clicks_and_space_chords(self):
        """Interleave virtual keycap mouse clicks with Space physical keydowns/keyups."""
        virtual_keys = ["KeyW", "KeyE", "KeyR", "KeyT", "KeyG", "KeyC"]
        for k in virtual_keys:
            key_box = get_bbox(self.page, f'.key-cap[data-key="{k}"]')
            cx, cy = get_center(key_box)

            # Mouse down on virtual key
            self.page.mouse.move(cx, cy)
            self.page.mouse.down()
            self.page.wait_for_timeout(20)

            # Concurrently press Spacebar
            self.page.keyboard.down("Space")
            self.page.wait_for_timeout(25)

            # Release Spacebar
            self.page.keyboard.up("Space")
            self.page.wait_for_timeout(20)

            # Release virtual key
            self.page.mouse.up()
            self.page.wait_for_timeout(30)

        self.page.wait_for_timeout(250)
        self._assert_all_fingers_at_home()
        self._assert_raf_sleeping()
        self._assert_zero_console_errors()

    def test_rapid_drag_release_with_sustained_space_hold(self):
        """
        Hold Spacebar continuously, drag mouse across virtual keys and release mouse
        before releasing Spacebar.
        """
        self.page.keyboard.down("Space")
        self.page.wait_for_timeout(100)

        key_t = get_bbox(self.page, '.key-cap[data-key="KeyT"]')
        key_g = get_bbox(self.page, '.key-cap[data-key="KeyG"]')
        c_t = get_center(key_t)
        c_g = get_center(key_g)

        self.page.mouse.move(c_t[0], c_t[1])
        self.page.mouse.down()
        self.page.wait_for_timeout(40)
        self.page.mouse.move(c_g[0], c_g[1], steps=5)
        self.page.wait_for_timeout(40)
        self.page.mouse.up()
        self.page.wait_for_timeout(60)

        # Release Spacebar
        self.page.keyboard.up("Space")
        self.page.wait_for_timeout(250)

        self._assert_all_fingers_at_home()
        self._assert_raf_sleeping()
        self._assert_zero_console_errors()


if __name__ == "__main__":
    unittest.main()
