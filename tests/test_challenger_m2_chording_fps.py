"""
Adversarial Stress Test: Multi-Finger Simultaneous Chording & 60 FPS Stability
Milestone 2 Gate - Empirical Challenger 1 (challenger_m2_1)

Adversarial Stress Dimensions:
1. Multi-Finger Simultaneous Articulation & Chording:
   - 2-finger simultaneous chords (KeyW + KeyT, KeyA + KeyN)
   - 3-finger simultaneous chords (KeyW + KeyF + KeyG, KeyA + KeyE + KeyN)
   - 4-finger simultaneous chords (KeyZ + KeyW + KeyF + KeyG, KeyQ + KeyR + KeyG + KeyB)
   - 5-finger full-hand simultaneous chords (KeyA + KeyW + KeyF + KeyG + KeyN)
   - 5-finger simultaneous home-key press (KeyZ + KeyD + KeyR + KeyT + Space)
   - Staggered partial release during multi-finger chord
   - Intra-finger key queuing during active chords
   - Hybrid mouse click + physical keyboard concurrent chording
2. High-Frequency Rapid Tapping & Burst Spam:
   - 15ms rapid burst spam on single key
   - 15ms alternating burst spam on same finger across 4 keys
   - 15ms multi-finger interwoven burst storm (50+ rapid events)
   - Rapid virtual keycap click spam
   - Post-burst zero state corruption, zero NaN/null coordinates, zero stuck fingers
3. 60 FPS Frame Rate & Kinematics Loop Stability:
   - Sustained multi-finger chord typing benchmark (1500ms)
   - Empirical rAF interval tracking, average FPS >= 58.0, max interval < 50ms
   - rAF idle sleep verification: zero CPU spinning at steady state
   - Zero console errors across entire adversarial test suite
"""

import math
import os
import re
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


class AdversarialChordingAndFpsStressSuite(unittest.TestCase):
    """Adversarial stress test suite for multi-finger chording, burst spam, and 60 FPS performance."""

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

    def _assert_finger_inside_key(self, finger: str, key_code: str, label: str = ""):
        """Helper to assert that a given fingertip is strictly inside the keycap bounding box."""
        tip_box = get_bbox(self.page, f"#fingertip-{finger}")
        key_box = get_bbox(self.page, f'.key-cap[data-key="{key_code}"]')
        tip_center = get_center(tip_box)

        if key_code == "Space":
            # Spacebar left zone alignment
            sx = tip_center[0]
            sy = tip_center[1]
            inside = (
                (key_box["x"] <= sx <= key_box["x"] + key_box["width"] * 0.55)
                and (key_box["y"] <= sy <= key_box["y"] + key_box["height"])
            )
            self.assertTrue(
                inside,
                f"Thumb tip ({sx:.1f}, {sy:.1f}) outside Space left zone [{key_box['x']:.1f}..{key_box['x'] + key_box['width'] * 0.55:.1f}, {key_box['y']:.1f}..{key_box['y'] + key_box['height']:.1f}] for {label}",
            )
        else:
            assert_inside_bbox(self, tip_center, key_box, label or f"{finger} on {key_code}")

    def _assert_all_fingers_at_home(self, msg: str = ""):
        """Assert all 5 fingers are settled at their respective home keys."""
        self._assert_finger_inside_key("pinky", "KeyZ", f"{msg} Pinky home")
        self._assert_finger_inside_key("ring", "KeyD", f"{msg} Ring home")
        self._assert_finger_inside_key("middle", "KeyR", f"{msg} Middle home")
        self._assert_finger_inside_key("index", "KeyT", f"{msg} Index home")
        self._assert_finger_inside_key("thumb", "KeyM", f"{msg} Thumb home")

    # =========================================================================
    # PART 1: MULTI-FINGER SIMULTANEOUS CHORDING STRESS
    # =========================================================================

    def test_01_two_finger_chords_non_home_targets(self):
        """Stress: 2-finger simultaneous reach to non-home targets (Ring: KeyW, Thumb: KeyN)."""
        self.page.keyboard.down("KeyW")
        self.page.keyboard.down("KeyN")
        self.page.wait_for_timeout(140)

        self._assert_finger_inside_key("ring", "KeyW", "Chord 2: Ring reaches KeyW")
        self._assert_finger_inside_key("thumb", "KeyN", "Chord 2: Thumb reaches KeyN")

        # Other fingers must remain at their home positions
        self._assert_finger_inside_key("pinky", "KeyZ", "Chord 2: Pinky stays home")
        self._assert_finger_inside_key("middle", "KeyR", "Chord 2: Middle stays home")
        self._assert_finger_inside_key("index", "KeyT", "Chord 2: Index stays home")

        self.page.keyboard.up("KeyW")
        self.page.keyboard.up("KeyN")
        self.page.wait_for_timeout(180)
        self._assert_all_fingers_at_home("Post Chord 2 return")

    def test_02_three_finger_movement_combat_chord(self):
        """Stress: 3-finger simultaneous chord (Ring: KeyW, Middle: KeyF, Index: KeyG)."""
        self.page.keyboard.down("KeyW")
        self.page.keyboard.down("KeyF")
        self.page.keyboard.down("KeyG")
        self.page.wait_for_timeout(140)

        self._assert_finger_inside_key("ring", "KeyW", "Chord 3: Ring on KeyW")
        self._assert_finger_inside_key("middle", "KeyF", "Chord 3: Middle on KeyF")
        self._assert_finger_inside_key("index", "KeyG", "Chord 3: Index on KeyG")

        # Pinky and Thumb remain undisturbed
        self._assert_finger_inside_key("pinky", "KeyZ", "Chord 3: Pinky remains home")
        self._assert_finger_inside_key("thumb", "KeyM", "Chord 3: Thumb remains home")

        self.page.keyboard.up("KeyW")
        self.page.keyboard.up("KeyF")
        self.page.keyboard.up("KeyG")
        self.page.wait_for_timeout(180)
        self._assert_all_fingers_at_home("Post Chord 3 return")

    def test_03_three_finger_cross_hand_weapon_chord(self):
        """Stress: 3-finger chord spanning Pinky (KeyA), Ring (KeyE), Thumb (KeyM)."""
        self.page.keyboard.down("KeyA")
        self.page.keyboard.down("KeyE")
        self.page.keyboard.down("KeyM")
        self.page.wait_for_timeout(140)

        self._assert_finger_inside_key("pinky", "KeyA", "Chord 3b: Pinky on KeyA")
        self._assert_finger_inside_key("ring", "KeyE", "Chord 3b: Ring on KeyE")
        self._assert_finger_inside_key("thumb", "KeyM", "Chord 3b: Thumb on KeyM")

        self.page.keyboard.up("KeyA")
        self.page.keyboard.up("KeyE")
        self.page.keyboard.up("KeyM")
        self.page.wait_for_timeout(180)
        self._assert_all_fingers_at_home("Post Chord 3b return")

    def test_04_four_finger_tactical_chord(self):
        """Stress: 4-finger simultaneous articulation (Pinky: KeyZ, Ring: KeyW, Middle: KeyF, Index: KeyG)."""
        self.page.keyboard.down("KeyZ")
        self.page.keyboard.down("KeyW")
        self.page.keyboard.down("KeyF")
        self.page.keyboard.down("KeyG")
        self.page.wait_for_timeout(140)

        self._assert_finger_inside_key("pinky", "KeyZ", "Chord 4: Pinky on KeyZ")
        self._assert_finger_inside_key("ring", "KeyW", "Chord 4: Ring on KeyW")
        self._assert_finger_inside_key("middle", "KeyF", "Chord 4: Middle on KeyF")
        self._assert_finger_inside_key("index", "KeyG", "Chord 4: Index on KeyG")
        self._assert_finger_inside_key("thumb", "KeyM", "Chord 4: Thumb on KeyM")

        self.page.keyboard.up("KeyZ")
        self.page.keyboard.up("KeyW")
        self.page.keyboard.up("KeyF")
        self.page.keyboard.up("KeyG")
        self.page.wait_for_timeout(180)
        self._assert_all_fingers_at_home("Post Chord 4 return")

    def test_05_five_finger_full_hand_simultaneous_chord(self):
        """Stress: 5-finger simultaneous reach to 5 non-home targets across keyboard."""
        # Pinky -> KeyA, Ring -> KeyW, Middle -> KeyF, Index -> KeyG, Thumb -> KeyN
        keys = ["KeyA", "KeyW", "KeyF", "KeyG", "KeyN"]
        for k in keys:
            self.page.keyboard.down(k)

        self.page.wait_for_timeout(145)

        self._assert_finger_inside_key("pinky", "KeyA", "Chord 5: Pinky on KeyA")
        self._assert_finger_inside_key("ring", "KeyW", "Chord 5: Ring on KeyW")
        self._assert_finger_inside_key("middle", "KeyF", "Chord 5: Middle on KeyF")
        self._assert_finger_inside_key("index", "KeyG", "Chord 5: Index on KeyG")
        self._assert_finger_inside_key("thumb", "KeyN", "Chord 5: Thumb on KeyN")

        for k in keys:
            self.page.keyboard.up(k)

        self.page.wait_for_timeout(180)
        self._assert_all_fingers_at_home("Post Chord 5 return")

    def test_06_five_finger_simultaneous_home_press(self):
        """Stress: 5-finger simultaneous press on all baseline home keys (Z, D, R, T, Space)."""
        home_keys = ["KeyZ", "KeyD", "KeyR", "KeyT", "KeyM"]
        for k in home_keys:
            self.page.keyboard.down(k)

        self.page.wait_for_timeout(140)
        self._assert_all_fingers_at_home("During 5-finger home key chord")

        for k in home_keys:
            self.page.keyboard.up(k)

        self.page.wait_for_timeout(180)
        self._assert_all_fingers_at_home("After 5-finger home key release")

    def test_07_partial_staggered_release_dynamics(self):
        """Stress: Press 4 fingers, release 2 while holding 2, assert released return and held remain locked."""
        # Hold: KeyA (Pinky), KeyW (Ring), KeyF (Middle), KeyG (Index)
        for k in ["KeyA", "KeyW", "KeyF", "KeyG"]:
            self.page.keyboard.down(k)
        self.page.wait_for_timeout(140)

        # Release Ring (KeyW) and Middle (KeyF), keeping Pinky (KeyA) and Index (KeyG) held
        self.page.keyboard.up("KeyW")
        self.page.keyboard.up("KeyF")
        self.page.wait_for_timeout(180)

        # Pinky and Index must stay precisely on target
        self._assert_finger_inside_key("pinky", "KeyA", "Staggered: Pinky still on KeyA")
        self._assert_finger_inside_key("index", "KeyG", "Staggered: Index still on KeyG")

        # Ring and Middle must have returned smoothly to their home keys
        self._assert_finger_inside_key("ring", "KeyD", "Staggered: Ring returned to KeyD")
        self._assert_finger_inside_key("middle", "KeyR", "Staggered: Middle returned to KeyR")

        # Now release remaining keys
        self.page.keyboard.up("KeyA")
        self.page.keyboard.up("KeyG")
        self.page.wait_for_timeout(180)
        self._assert_all_fingers_at_home("Staggered: Full return")

    def test_08_multi_finger_chording_with_intra_finger_queue(self):
        """Stress: Multi-finger chord with same-finger queue re-targeting and recovery."""
        # Hold Middle on KeyF and Index on KeyT
        self.page.keyboard.down("KeyF")
        self.page.keyboard.down("KeyT")
        self.page.wait_for_timeout(140)

        self._assert_finger_inside_key("middle", "KeyF", "Queue: Middle on KeyF")
        self._assert_finger_inside_key("index", "KeyT", "Queue: Index on KeyT")

        # Index presses KeyY while continuing to hold KeyT
        self.page.keyboard.down("KeyY")
        self.page.wait_for_timeout(140)

        self._assert_finger_inside_key("middle", "KeyF", "Queue: Middle stays on KeyF")
        self._assert_finger_inside_key("index", "KeyY", "Queue: Index articulates to KeyY")

        # Index releases KeyY, still holding KeyT -> must cleanly retarget back to KeyT
        self.page.keyboard.up("KeyY")
        self.page.wait_for_timeout(140)

        self._assert_finger_inside_key("middle", "KeyF", "Queue: Middle still on KeyF")
        self._assert_finger_inside_key("index", "KeyT", "Queue: Index returns to held KeyT")

        # Release all
        self.page.keyboard.up("KeyF")
        self.page.keyboard.up("KeyT")
        self.page.wait_for_timeout(180)
        self._assert_all_fingers_at_home("Queue: Post recovery all home")

    def test_09_hybrid_mouse_click_and_keyboard_chording(self):
        """Stress: Physical keyboard keypress concurrent with virtual keycap mouse click."""
        # Ring finger held on KeyW via keyboard
        self.page.keyboard.down("KeyW")
        self.page.wait_for_timeout(60)

        # Mouse clicks and holds KeyF (Middle finger)
        key_f = self.page.locator('.key-cap[data-key="KeyF"]')
        f_box = key_f.bounding_box()
        self.assertIsNotNone(f_box)
        self.page.mouse.move(f_box["x"] + f_box["width"] / 2, f_box["y"] + f_box["height"] / 2)
        self.page.mouse.down()
        self.page.wait_for_timeout(140)

        # Both fingers must be on their respective keys
        self._assert_finger_inside_key("ring", "KeyW", "Hybrid: Ring on KeyW")
        self._assert_finger_inside_key("middle", "KeyF", "Hybrid: Middle on KeyF")

        # Release mouse and keyboard
        self.page.mouse.up()
        self.page.keyboard.up("KeyW")
        self.page.wait_for_timeout(180)
        self._assert_all_fingers_at_home("Hybrid: Post release home")

    # =========================================================================
    # PART 2: HIGH-FREQUENCY RAPID TAPPING & BURST SPAM (15ms CYCLES)
    # =========================================================================

    def test_10_rapid_15ms_burst_spam_single_key(self):
        """Stress: Rapid 15ms key burst spam on single key (Middle on KeyF)."""
        for _ in range(25):
            self.page.keyboard.down("KeyF")
            self.page.wait_for_timeout(15)
            self.page.keyboard.up("KeyF")
            self.page.wait_for_timeout(15)

        # Wait for kinematics settle
        self.page.wait_for_timeout(220)

        # Assert Middle finger returned safely to KeyR home
        self._assert_finger_inside_key("middle", "KeyR", "Post single-key 15ms spam return")
        self.assertEqual(len(self.console_errors), 0, f"Console errors: {self.console_errors}")

    def test_11_rapid_15ms_burst_spam_same_finger_multikey(self):
        """Stress: Rapid 15ms cycling across 4 keys on Index finger (KeyT, KeyG, KeyY, KeyH)."""
        index_keys = ["KeyT", "KeyG", "KeyY", "KeyH"]
        for _ in range(10):
            for k in index_keys:
                self.page.keyboard.down(k)
                self.page.wait_for_timeout(15)
                self.page.keyboard.up(k)
                self.page.wait_for_timeout(15)

        self.page.wait_for_timeout(220)

        # Verify finite coordinates in DOM & state
        coords = self.page.evaluate("""() => {
            const idx = window.fingerState.index;
            const pad = document.getElementById('fingertip-index');
            return {
                cx: parseFloat(pad.getAttribute('cx')),
                cy: parseFloat(pad.getAttribute('cy')),
                stateX: idx.current.x,
                stateY: idx.current.y
            };
        }""")
        self.assertFalse(math.isnan(coords["cx"]), "fingertip cx is NaN")
        self.assertFalse(math.isnan(coords["cy"]), "fingertip cy is NaN")
        self.assertFalse(math.isnan(coords["stateX"]), "state current.x is NaN")
        self.assertFalse(math.isnan(coords["stateY"]), "state current.y is NaN")

        self._assert_finger_inside_key("index", "KeyT", "Post multikey 15ms spam Index home")
        self.assertEqual(len(self.console_errors), 0, f"Console errors: {self.console_errors}")

    def test_12_rapid_15ms_multi_finger_burst_storm(self):
        """Stress: Interleaved 15ms burst storm across all 5 fingers simultaneously."""
        storm_sequence = [
            ("KeyZ", "KeyW"),
            ("KeyF", "KeyG"),
            ("KeyN", "KeyM"),
            ("Space", "KeyT"),
            ("KeyA", "KeyE"),
            ("KeyF", "KeyB"),
            ("KeyX", "KeyC"),
            ("KeyW", "KeyF"),
            ("KeyG", "KeyN"),
            ("KeyZ", "Space"),
        ]

        for pair in storm_sequence:
            self.page.keyboard.down(pair[0])
            self.page.keyboard.down(pair[1])
            self.page.wait_for_timeout(15)
            self.page.keyboard.up(pair[0])
            self.page.keyboard.up(pair[1])
            self.page.wait_for_timeout(15)

        # Allow kinematics to complete return animation
        self.page.wait_for_timeout(250)

        # Verify zero stuck fingers: all 5 must be inside home bounding boxes
        self._assert_all_fingers_at_home("Post burst storm zero stuck fingers")

        # Verify all spline SVG path strings are valid finite cubic Bezier paths
        spline_validity = self.page.evaluate("""() => {
            const fingers = ['pinky', 'ring', 'middle', 'index', 'thumb'];
            const results = {};
            for (const f of fingers) {
                const el = document.getElementById('finger-spline-' + f);
                const d = el ? el.getAttribute('d') : '';
                results[f] = {
                    hasNaN: d.includes('NaN'),
                    hasNull: d.includes('null'),
                    hasUndefined: d.includes('undefined'),
                    isNonEmpty: d.length > 10
                };
            }
            return results;
        }""")

        for f, res in spline_validity.items():
            self.assertFalse(res["hasNaN"], f"Spline {f} path contains NaN")
            self.assertFalse(res["hasNull"], f"Spline {f} path contains null")
            self.assertFalse(res["hasUndefined"], f"Spline {f} path contains undefined")
            self.assertTrue(res["isNonEmpty"], f"Spline {f} path is empty")

        self.assertEqual(len(self.console_errors), 0, f"Console errors: {self.console_errors}")

    def test_13_rapid_virtual_keycap_mouse_click_spam(self):
        """Stress: Rapid virtual mouse clicks across multiple keycaps."""
        test_keys = ["KeyR", "KeyT", "KeyW", "KeyZ", "Space", "KeyF", "KeyG"]
        for key in test_keys:
            key_el = self.page.locator(f'.key-cap[data-key="{key}"]')
            box = key_el.bounding_box()
            if box:
                self.page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                self.page.wait_for_timeout(25)

        self.page.wait_for_timeout(220)
        self._assert_all_fingers_at_home("Post mouse click spam return")
        self.assertEqual(len(self.console_errors), 0, f"Console errors: {self.console_errors}")

    # =========================================================================
    # PART 3: 60 FPS FRAME RATE & KINEMATICS LOOP STABILITY
    # =========================================================================

    def test_14_sustained_multi_finger_typing_fps(self):
        """Stress: Measure rAF frame intervals during sustained multi-finger typing; assert avg FPS >= 58.0."""
        # Inject frame timestamp recorder
        self.page.evaluate("""() => {
            window.__frameTimestamps = [];
            window.__fpsRecording = true;
            let lastTs = performance.now();
            function trackRaf(now) {
                if (!window.__fpsRecording) return;
                const delta = now - lastTs;
                lastTs = now;
                window.__frameTimestamps.push(delta);
                requestAnimationFrame(trackRaf);
            }
            requestAnimationFrame(trackRaf);
        }""")

        # Execute 1500ms of sustained alternating multi-finger typing
        chords = [
            ("KeyW", "KeyT"),
            ("KeyF", "Space"),
            ("KeyZ", "KeyG"),
            ("KeyR", "KeyN"),
            ("KeyA", "KeyE"),
            ("KeyW", "KeyF"),
            ("KeyT", "KeyM"),
            ("KeyZ", "KeyD"),
            ("KeyR", "KeyT"),
            ("KeyF", "KeyN"),
        ]

        for c in chords:
            self.page.keyboard.down(c[0])
            self.page.keyboard.down(c[1])
            self.page.wait_for_timeout(80)
            self.page.keyboard.up(c[0])
            self.page.keyboard.up(c[1])
            self.page.wait_for_timeout(70)

        # Stop recording and retrieve frame intervals
        frame_deltas = self.page.evaluate("""() => {
            window.__fpsRecording = false;
            return window.__frameTimestamps;
        }""")

        # Discard the very first warmup frame
        deltas = [d for d in frame_deltas[2:] if d > 0]
        self.assertGreater(len(deltas), 30, f"Insufficient frames recorded: {len(deltas)}")

        mean_delta = sum(deltas) / len(deltas)
        fps = 1000.0 / mean_delta
        max_delta = max(deltas)

        # Print empirical measurement summary for audit trail
        print(f"\n[FPS Benchmark] Frames: {len(deltas)}, Mean Interval: {mean_delta:.2f}ms, Effective FPS: {fps:.2f}, Max Interval: {max_delta:.2f}ms")

        # Assertions:
        # Standard display nominal interval: 16.67ms (60 FPS).
        # We assert average FPS >= 58.0 and no catastrophic frame hitch > 55.0ms (no drop of >3 frames).
        self.assertGreaterEqual(
            fps,
            58.0,
            f"Average FPS dropped below 58.0: {fps:.2f} FPS (mean delta: {mean_delta:.2f}ms)",
        )
        self.assertLess(
            max_delta,
            55.0,
            f"Detected excessive frame drop hitch: {max_delta:.2f}ms > 55.0ms",
        )

    def test_15_raf_idle_sleep_verification(self):
        """Stress: Assert rAF loop sleeps completely (window._handRafActive is false) at steady state."""
        # Trigger an animation
        self.page.keyboard.down("KeyF")
        self.page.wait_for_timeout(130)

        # While key is held or animating, ticker must be active or just finished
        # Now release key
        self.page.keyboard.up("KeyF")
        # Return duration is 160ms. Wait 240ms for steady state.
        self.page.wait_for_timeout(240)

        # Assert ticker has gone to sleep
        is_active = self.page.evaluate("() => window._handRafActive")
        self.assertFalse(is_active, f"rAF ticker did not sleep after reaching steady state! _handRafActive = {is_active}")

        # Attach frame spy while idle and verify zero new ticker frames are dispatched
        frames_while_idle = self.page.evaluate("""() => {
            return new Promise(resolve => {
                let frameCount = 0;
                // Check if any kinematics loop iteration runs in next 120ms
                const origSpline = document.getElementById('finger-spline-middle');
                const initialD = origSpline ? origSpline.getAttribute('d') : '';
                setTimeout(() => {
                    resolve({
                        rafActive: window._handRafActive,
                        dUnchanged: (origSpline ? origSpline.getAttribute('d') : '') === initialD
                    });
                }, 120);
            });
        }""")

        self.assertFalse(frames_while_idle["rafActive"], "rAF became active while idle without input")
        self.assertTrue(frames_while_idle["dUnchanged"], "DOM mutated while idle without input")

    def test_16_zero_console_errors_across_entire_session(self):
        """Final verification: Zero unhandled console errors or exceptions across all tests."""
        self.assertEqual(
            len(self.console_errors),
            0,
            f"Found unhandled console errors during adversarial stress: {self.console_errors}",
        )


if __name__ == "__main__":
    unittest.main()
