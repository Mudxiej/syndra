"""
SYNDRA Milestone 2 Gate Challenger Suite 2:
Empirical Stress Testing for Zero Layout Thrashing & rAF Lifecycle.

Challenger: teamwork_preview_challenger (Milestone 2 Gate Challenger 2)
Focus Areas:
1. Zero Layout Thrashing: Element.prototype.getBoundingClientRect monkey-patching
   asserting 0 calls during active animation frames (while window._handRafActive is true).
2. rAF Idle Sleep: Assert window._handRafActive transitions to false within 250ms
   after key release, and zero rAF callbacks fire until the next key event.
3. Mid-Flight Direction Reversal: Press key, release mid-flight at ~50ms,
   assert smooth trajectory back to home posture without snapping or NaN coordinates.

Execution:
    & 'C:\\Users\\mudxiej\\AppData\\Local\\Programs\\Python\\Python314\\python.exe' -m unittest tests.test_challenger_m2_raf_thrash -v
"""

import math
import time
import unittest
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright

from tests.helpers import HTML_URL, reset_page_state


class BaseChallengerM2TestCase(unittest.TestCase):
    """Playwright fixture initialized at 1400x900 desktop viewport."""

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
        cls.page.on("console", lambda msg: cls.console_errors.append(msg.text) if msg.type == "error" else None)
        cls.page.on("pageerror", lambda err: cls.console_errors.append(str(err)))
        cls.page.goto(HTML_URL)
        cls.page.locator("#ch5").scroll_into_view_if_needed()
        cls.page.wait_for_timeout(300)

        # Inject robust in-page monitoring harnesses
        cls.page.evaluate("""() => {
            // Layout Thrash Monitor
            window.__challengerGbrcCalls = [];
            window.__challengerLayoutReads = [];
            const originalGbrc = Element.prototype.getBoundingClientRect;
            window.__originalGbrc = originalGbrc;

            Element.prototype.getBoundingClientRect = function() {
                if (window._handRafActive) {
                    const stack = (new Error()).stack || '';
                    window.__challengerGbrcCalls.push({
                        time: performance.now(),
                        tagName: this.tagName,
                        id: this.id,
                        className: String(this.className),
                        stack: stack
                    });
                }
                return originalGbrc.apply(this, arguments);
            };

            // Layout Property Monitor
            const layoutProps = ['offsetWidth', 'offsetHeight', 'clientWidth', 'clientHeight', 'scrollWidth', 'scrollHeight'];
            layoutProps.forEach(prop => {
                const descriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, prop);
                if (descriptor && descriptor.get) {
                    const origGet = descriptor.get;
                    Object.defineProperty(HTMLElement.prototype, prop, {
                        get: function() {
                            if (window._handRafActive) {
                                const stack = (new Error()).stack || '';
                                window.__challengerLayoutReads.push({
                                    time: performance.now(),
                                    property: prop,
                                    tagName: this.tagName,
                                    id: this.id,
                                    stack: stack
                                });
                            }
                            return origGet.apply(this);
                        },
                        configurable: true
                    });
                }
            });

            // rAF Callback Counter & Monitor
            window.__challengerRafCount = 0;
            window.__challengerRafLog = [];
            const origRaf = window.requestAnimationFrame;
            window.__originalRaf = origRaf;
            window.requestAnimationFrame = function(cb) {
                window.__challengerRafCount++;
                return origRaf.call(window, function(timestamp) {
                    window.__challengerRafLog.push({
                        time: timestamp,
                        rafActive: !!window._handRafActive
                    });
                    return cb(timestamp);
                });
            };

            // High-Frequency Trajectory Flight Recorder
            window.__trajectory = [];
            window.__trajectoryActive = false;
            window.__recordFinger = null;

            window.__startTrajectoryRecording = function(fingerName) {
                window.__trajectory = [];
                window.__trajectoryActive = true;
                window.__recordFinger = fingerName;

                function sampleStep(now) {
                    if (!window.__trajectoryActive) return;
                    const st = window.fingerState ? window.fingerState[window.__recordFinger] : null;
                    if (st) {
                        window.__trajectory.push({
                            time: now,
                            x: st.current.x,
                            y: st.current.y,
                            tx: st.target.x,
                            ty: st.target.y,
                            isAnimating: st.isAnimating,
                            rafActive: !!window._handRafActive
                        });
                    }
                    origRaf.call(window, sampleStep);
                }
                origRaf.call(window, sampleStep);
            };

            window.__stopTrajectoryRecording = function() {
                window.__trajectoryActive = false;
                return window.__trajectory || [];
            };
        }""")

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
        # Reset telemetry logs
        self.page.evaluate("""() => {
            window.__challengerGbrcCalls = [];
            window.__challengerLayoutReads = [];
            window.__challengerRafLog = [];
            window.__trajectory = [];
            window.__trajectoryActive = false;
        }""")

    def tearDown(self):
        reset_page_state(self.page)


# ==============================================================================
# CHALLENGE SUITE 1: ZERO LAYOUT THRASHING DURING ANIMATIONS
# ==============================================================================

class TestChallengerM2ZeroLayoutThrashing(BaseChallengerM2TestCase):
    """Stress tests verifying ZERO getBoundingClientRect calls during active rAF animation frames."""

    def test_c1_01_zero_gbrc_during_single_reach_and_return_animation(self):
        """Zero Layout Thrashing: Ring finger reach to KeyW and return generates 0 getBoundingClientRect calls."""
        # Pre-check initial state
        initial_gbrc = self.page.evaluate("() => window.__challengerGbrcCalls.length")
        self.assertEqual(initial_gbrc, 0, "Pre-condition failed: GBRC calls must start at 0.")

        # Trigger KeyW reach
        self.page.keyboard.down("KeyW")
        self.page.wait_for_timeout(60)  # Mid-flight reach

        # Verify rAF is active
        is_active = self.page.evaluate("() => window._handRafActive")
        self.assertTrue(is_active, "Kinematics rAF loop must be active during KeyW reach.")

        # Check GBRC calls during reach
        reach_gbrc = self.page.evaluate("() => window.__challengerGbrcCalls.slice()")
        # Filter calls that originate from kinematics loop or application code
        app_reach_calls = [c for c in reach_gbrc if "kinematicsTick" in c.get("stack", "") or "renderFingers" in c.get("stack", "")]
        self.assertEqual(
            len(app_reach_calls), 0,
            f"Layout thrashing detected during reach: {len(app_reach_calls)} GBRC calls in rAF loop: {app_reach_calls}"
        )
        self.assertEqual(len(reach_gbrc), 0, f"Zero GBRC calls permitted while _handRafActive is true. Got: {reach_gbrc}")

        # Let reach complete
        self.page.wait_for_timeout(80)

        # Release KeyW to trigger return
        self.page.keyboard.up("KeyW")
        self.page.wait_for_timeout(80)  # Mid-flight return

        return_gbrc = self.page.evaluate("() => window.__challengerGbrcCalls.slice()")
        self.assertEqual(
            len(return_gbrc), 0,
            f"Layout thrashing detected during return: {len(return_gbrc)} GBRC calls while rAF active: {return_gbrc}"
        )

        # Settle to idle
        self.page.wait_for_timeout(150)
        final_gbrc = self.page.evaluate("() => window.__challengerGbrcCalls.slice()")
        self.assertEqual(len(final_gbrc), 0, "Zero GBRC calls must occur across entire reach/return cycle.")

    def test_c1_02_zero_gbrc_during_5_finger_concurrent_articulation(self):
        """Zero Layout Thrashing: Concurrent 5-finger articulation generates 0 getBoundingClientRect calls."""
        # Simultaneously activate all 5 fingers
        self.page.keyboard.down("KeyZ")  # Pinky
        self.page.keyboard.down("KeyW")  # Ring
        self.page.keyboard.down("KeyF")  # Middle
        self.page.keyboard.down("KeyG")  # Index
        self.page.keyboard.down("KeyV")  # Thumb

        self.page.wait_for_timeout(60)

        is_active = self.page.evaluate("() => window._handRafActive")
        self.assertTrue(is_active, "rAF loop must be active during 5-finger concurrent motion.")

        gbrc_calls = self.page.evaluate("() => window.__challengerGbrcCalls.slice()")
        self.assertEqual(
            len(gbrc_calls), 0,
            f"Concurrent 5-finger motion triggered {len(gbrc_calls)} GBRC calls: {gbrc_calls}"
        )

        # Release all 5 keys simultaneously
        self.page.keyboard.up("KeyZ")
        self.page.keyboard.up("KeyW")
        self.page.keyboard.up("KeyF")
        self.page.keyboard.up("KeyG")
        self.page.keyboard.up("KeyV")

        self.page.wait_for_timeout(80)
        return_gbrc = self.page.evaluate("() => window.__challengerGbrcCalls.slice()")
        self.assertEqual(len(return_gbrc), 0, f"Concurrent return triggered GBRC calls: {return_gbrc}")

        self.page.wait_for_timeout(150)

    def test_c1_03_zero_gbrc_during_rapid_successive_key_burst(self):
        """Zero Layout Thrashing: Rapid fire succession of 8 distinct keys causes 0 GBRC calls."""
        keys = ["KeyR", "KeyT", "KeyG", "KeyF", "KeyW", "Space", "KeyX", "KeyE"]
        for k in keys:
            self.page.keyboard.down(k)
            self.page.wait_for_timeout(15)
            self.page.keyboard.up(k)
            self.page.wait_for_timeout(15)

        gbrc_calls = self.page.evaluate("() => window.__challengerGbrcCalls.slice()")
        self.assertEqual(
            len(gbrc_calls), 0,
            f"Rapid key burst triggered {len(gbrc_calls)} GBRC calls: {gbrc_calls}"
        )

    def test_c1_04_zero_gbrc_during_virtual_mouse_clicks(self):
        """Zero Layout Thrashing: Virtual keycap mouse clicks trigger 0 GBRC calls during animation."""
        key_cap = self.page.locator('.key-cap[data-key="KeyW"]')
        self.assertGreater(key_cap.count(), 0, "KeyW cap element must exist.")

        # Dispatch mousedown and mouseup
        key_cap.dispatch_event("mousedown")
        self.page.wait_for_timeout(50)

        is_active = self.page.evaluate("() => window._handRafActive")
        self.assertTrue(is_active, "rAF loop must activate upon virtual mouse click.")

        key_cap.dispatch_event("mouseup")
        self.page.wait_for_timeout(50)

        gbrc_calls = self.page.evaluate("() => window.__challengerGbrcCalls.slice()")
        self.assertEqual(
            len(gbrc_calls), 0,
            f"Virtual mouse click triggered {len(gbrc_calls)} GBRC calls: {gbrc_calls}"
        )
        self.page.wait_for_timeout(150)

    def test_c1_05_zero_dom_layout_property_reads_during_raf(self):
        """Zero Layout Thrashing: No offsetWidth, clientWidth, or scrollWidth reads during rAF frames."""
        self.page.keyboard.down("KeyT")
        self.page.keyboard.down("KeyR")
        self.page.wait_for_timeout(60)
        self.page.keyboard.up("KeyT")
        self.page.keyboard.up("KeyR")
        self.page.wait_for_timeout(100)

        layout_reads = self.page.evaluate("() => window.__challengerLayoutReads.slice()")
        app_reads = [r for r in layout_reads if "kinematicsTick" in r.get("stack", "") or "renderFingers" in r.get("stack", "")]
        self.assertEqual(
            len(app_reads), 0,
            f"Forbidden layout property reads detected in rAF loop: {app_reads}"
        )


# ==============================================================================
# CHALLENGE SUITE 2: rAF IDLE SLEEP & LIFECYCLE DEACTIVATION
# ==============================================================================

class TestChallengerM2RafIdleSleep(BaseChallengerM2TestCase):
    """Stress tests verifying rAF idle sleep timing, deactivation, and quiescence."""

    def test_c2_01_initial_state_idle_quiescence(self):
        """rAF Idle Sleep: Hand animation engine starts in deactivated sleep state."""
        is_active = self.page.evaluate("() => window._handRafActive")
        self.assertFalse(is_active, "Initial steady state must have window._handRafActive === false.")

    def test_c2_02_sleep_deactivation_within_250ms_post_release(self):
        """rAF Idle Sleep: window._handRafActive transitions to false within 250ms of key release."""
        self.page.keyboard.down("KeyW")
        self.page.wait_for_timeout(130)  # Reach completes

        # Verify reached target and steady
        self.page.keyboard.up("KeyW")
        release_timestamp = time.time()

        # Poll until _handRafActive becomes false
        settled = False
        duration_to_sleep = 0.0
        for _ in range(35):  # Up to 350ms
            active = self.page.evaluate("() => window._handRafActive")
            if not active:
                settled = True
                duration_to_sleep = (time.time() - release_timestamp) * 1000
                break
            time.sleep(0.01)

        self.assertTrue(
            settled,
            "window._handRafActive failed to deactivate to false within 350ms after key release."
        )
        self.assertLessEqual(
            duration_to_sleep, 250.0,
            f"Sleep deactivation took {duration_to_sleep:.1f}ms, exceeding the 250ms threshold."
        )

        # Verify finger position settled precisely at home
        drift = self.page.evaluate("""() => {
            const r = window.fingerState.ring;
            return Math.hypot(r.current.x - r.home.x, r.current.y - r.home.y);
        }""")
        self.assertLess(drift, 0.2, f"Ring finger drift from home position is {drift:.2f}px (expected < 0.2px).")

    def test_c2_03_zero_raf_callbacks_in_steady_state(self):
        """rAF Idle Sleep: Strictly zero rAF callbacks fire for hand engine during idle sleep."""
        # Ensure system is idle
        self.page.wait_for_timeout(100)
        self.assertFalse(self.page.evaluate("() => window._handRafActive"))

        # Snapshot rAF count
        start_count = self.page.evaluate("() => window.__challengerRafLog.length")
        time.sleep(0.3)  # Wait 300ms in idle steady state
        end_log = self.page.evaluate(f"() => window.__challengerRafLog.slice({start_count})")

        # Any callbacks that did fire must have rafActive === false
        active_in_log = [entry for entry in end_log if entry.get("rafActive") is True]
        self.assertEqual(
            len(active_in_log), 0,
            f"Spurious active rAF callbacks detected during steady state idle sleep: {active_in_log}"
        )

    def test_c2_04_chord_partial_release_and_eventual_sleep(self):
        """rAF Idle Sleep: Multi-finger chord partial release keeps rAF active until all fingers settle."""
        # Activate Ring and Index
        self.page.keyboard.down("KeyW")
        self.page.keyboard.down("KeyG")
        self.page.wait_for_timeout(130)

        # Release Ring only, keep Index pressed
        self.page.keyboard.up("KeyW")
        self.page.wait_for_timeout(200)  # Ring returns to home and settles

        # Index is still pressed, but steady state reached -> rAF should sleep!
        is_active_with_held_key = self.page.evaluate("() => window._handRafActive")
        self.assertFalse(
            is_active_with_held_key,
            "rAF loop should sleep once held fingers reach their steady targets."
        )

        # Now release Index
        self.page.keyboard.up("KeyG")
        self.page.wait_for_timeout(40)
        self.assertTrue(
            self.page.evaluate("() => window._handRafActive"),
            "rAF loop must reactivate when held key is released."
        )

        # Must sleep again within 250ms
        self.page.wait_for_timeout(220)
        self.assertFalse(
            self.page.evaluate("() => window._handRafActive"),
            "rAF loop must return to sleep after Index settles at home."
        )

    def test_c2_05_keyboard_repeat_guard_sleep_resilience(self):
        """rAF Idle Sleep: e.repeat events do not cause rAF loop instability or prevent sleep."""
        # Press key and simulate 15 repeat keydowns
        self.page.keyboard.down("KeyW")
        for _ in range(15):
            self.page.evaluate("""() => {
                const ev = new KeyboardEvent('keydown', { code: 'KeyW', key: 'w', repeat: true, bubbles: true });
                window.dispatchEvent(ev);
            }""")
            time.sleep(0.01)

        # Release key
        self.page.keyboard.up("KeyW")
        self.page.wait_for_timeout(220)

        is_active = self.page.evaluate("() => window._handRafActive")
        self.assertFalse(
            is_active,
            "rAF failed to sleep after e.repeat bursts followed by keyup."
        )


# ==============================================================================
# CHALLENGE SUITE 3: MID-FLIGHT DIRECTION REVERSAL & TRAJECTORY SMOOTHNESS
# ==============================================================================

class TestChallengerM2MidFlightDirectionReversal(BaseChallengerM2TestCase):
    """Stress tests verifying mid-flight release smoothly reverses trajectory without snapping or NaN."""

    def _verify_trajectory_smoothness(
        self,
        samples: List[Dict[str, Any]],
        start_pt: Dict[str, float],
        target_pt: Dict[str, float],
        finger_name: str,
        max_step_px: float = 30.0
    ):
        """Validate sample sequence for continuity, absence of NaN, and monotonic turnaround."""
        self.assertGreater(len(samples), 5, f"Insufficient trajectory samples for {finger_name} ({len(samples)} samples).")

        # Check for NaN or null coordinates
        for idx, s in enumerate(samples):
            self.assertTrue(math.isfinite(s["x"]), f"Sample {idx} has non-finite x: {s['x']}")
            self.assertTrue(math.isfinite(s["y"]), f"Sample {idx} has non-finite y: {s['y']}")

        # Check inter-frame step distances (no instantaneous snapping/teleportation)
        for i in range(1, len(samples)):
            dx = samples[i]["x"] - samples[i - 1]["x"]
            dy = samples[i]["y"] - samples[i - 1]["y"]
            step = math.hypot(dx, dy)
            self.assertLessEqual(
                step, max_step_px,
                f"Discontinuity / snap detected between frame {i-1} and {i} for {finger_name}: delta={step:.2f}px (max allowed: {max_step_px}px)"
            )

        # Check final sample reached home position
        final_sample = samples[-1]
        final_dist_to_home = math.hypot(final_sample["x"] - start_pt["x"], final_sample["y"] - start_pt["y"])
        self.assertLess(
            final_dist_to_home, 1.0,
            f"Finger {finger_name} failed to return to home posture: final drift={final_dist_to_home:.2f}px (expected < 1.0px)."
        )

    def test_c3_01_ring_finger_mid_flight_reversal_w_to_home(self):
        """Mid-Flight Reversal: Ring finger released at 50ms smoothly reverses to KeyD without snap or NaN."""
        # Get baseline home position
        home_pos = self.page.evaluate("() => ({ x: window.fingerState.ring.home.x, y: window.fingerState.ring.home.y })")
        target_pos = self.page.evaluate("() => window.getKeyCenter('KeyW')")

        # Start flight recording
        self.page.evaluate("() => window.__startTrajectoryRecording('ring')")

        # Press KeyW
        self.page.keyboard.down("KeyW")
        # Travel for ~50ms (mid-flight of 120ms reach)
        self.page.wait_for_timeout(50)

        # Release mid-flight
        self.page.keyboard.up("KeyW")

        # Allow return to home to complete (~180ms)
        self.page.wait_for_timeout(230)

        # Stop recording and inspect samples
        samples = self.page.evaluate("() => window.__stopTrajectoryRecording()")

        self._verify_trajectory_smoothness(
            samples=samples,
            start_pt=home_pos,
            target_pt=target_pos,
            finger_name="ring",
            max_step_px=25.0
        )

        # Verify reversal point happened mid-way (neither at home nor fully at target)
        max_dist_from_home = max(math.hypot(s["x"] - home_pos["x"], s["y"] - home_pos["y"]) for s in samples)
        total_target_dist = math.hypot(target_pos["x"] - home_pos["x"], target_pos["y"] - home_pos["y"])

        self.assertGreater(
            max_dist_from_home, total_target_dist * 0.15,
            f"Finger did not articulate forward before reversal (max_dist={max_dist_from_home:.1f}px, total={total_target_dist:.1f}px)"
        )
        self.assertLess(
            max_dist_from_home, total_target_dist * 0.95,
            f"Finger reached target prematurely before 50ms reversal (max_dist={max_dist_from_home:.1f}px, total={total_target_dist:.1f}px)"
        )

    def test_c3_02_index_finger_mid_flight_reversal_g_to_home(self):
        """Mid-Flight Reversal: Index finger released at 45ms smoothly reverses to KeyT."""
        home_pos = self.page.evaluate("() => ({ x: window.fingerState.index.home.x, y: window.fingerState.index.home.y })")
        target_pos = self.page.evaluate("() => window.getKeyCenter('KeyG')")

        self.page.evaluate("() => window.__startTrajectoryRecording('index')")
        self.page.keyboard.down("KeyG")
        self.page.wait_for_timeout(45)
        self.page.keyboard.up("KeyG")
        self.page.wait_for_timeout(220)

        samples = self.page.evaluate("() => window.__stopTrajectoryRecording()")
        self._verify_trajectory_smoothness(samples, home_pos, target_pos, "index", max_step_px=25.0)

    def test_c3_03_middle_finger_mid_flight_reversal_f_to_home(self):
        """Mid-Flight Reversal: Middle finger released at 50ms smoothly reverses to KeyR."""
        home_pos = self.page.evaluate("() => ({ x: window.fingerState.middle.home.x, y: window.fingerState.middle.home.y })")
        target_pos = self.page.evaluate("() => window.getKeyCenter('KeyF')")

        self.page.evaluate("() => window.__startTrajectoryRecording('middle')")
        self.page.keyboard.down("KeyF")
        self.page.wait_for_timeout(50)
        self.page.keyboard.up("KeyF")
        self.page.wait_for_timeout(220)

        samples = self.page.evaluate("() => window.__stopTrajectoryRecording()")
        self._verify_trajectory_smoothness(samples, home_pos, target_pos, "middle", max_step_px=25.0)

    def test_c3_04_thumb_finger_mid_flight_reversal_v_to_home(self):
        """Mid-Flight Reversal: Thumb released at 45ms smoothly reverses to Space home posture."""
        home_pos = self.page.evaluate("() => ({ x: window.fingerState.thumb.home.x, y: window.fingerState.thumb.home.y })")
        target_pos = self.page.evaluate("() => window.getKeyCenter('KeyV')")

        self.page.evaluate("() => window.__startTrajectoryRecording('thumb')")
        self.page.keyboard.down("KeyV")
        self.page.wait_for_timeout(45)
        self.page.keyboard.up("KeyV")
        self.page.wait_for_timeout(220)

        samples = self.page.evaluate("() => window.__stopTrajectoryRecording()")
        self._verify_trajectory_smoothness(samples, home_pos, target_pos, "thumb", max_step_px=25.0)

    def test_c3_05_pinky_finger_mid_flight_reversal_x_to_home(self):
        """Mid-Flight Reversal: Pinky released at 45ms smoothly reverses to KeyZ home posture."""
        home_pos = self.page.evaluate("() => ({ x: window.fingerState.pinky.home.x, y: window.fingerState.pinky.home.y })")
        target_pos = self.page.evaluate("() => window.getKeyCenter('KeyX')")

        self.page.evaluate("() => window.__startTrajectoryRecording('pinky')")
        self.page.keyboard.down("KeyX")
        self.page.wait_for_timeout(45)
        self.page.keyboard.up("KeyX")
        self.page.wait_for_timeout(220)

        samples = self.page.evaluate("() => window.__stopTrajectoryRecording()")
        self._verify_trajectory_smoothness(samples, home_pos, target_pos, "pinky", max_step_px=25.0)

    def test_c3_06_rapid_double_reversal_ping_pong_smoothness(self):
        """Mid-Flight Reversal: Rapid ping-pong press-release-press-release exhibits 0 discontinuity or NaN."""
        home_pos = self.page.evaluate("() => ({ x: window.fingerState.ring.home.x, y: window.fingerState.ring.home.y })")
        target_pos = self.page.evaluate("() => window.getKeyCenter('KeyW')")

        self.page.evaluate("() => window.__startTrajectoryRecording('ring')")

        # Sequence: Press -> wait 40ms -> Release -> wait 35ms -> Press -> wait 35ms -> Release -> wait 200ms
        self.page.keyboard.down("KeyW")
        self.page.wait_for_timeout(40)
        self.page.keyboard.up("KeyW")
        self.page.wait_for_timeout(35)
        self.page.keyboard.down("KeyW")
        self.page.wait_for_timeout(35)
        self.page.keyboard.up("KeyW")
        self.page.wait_for_timeout(220)

        samples = self.page.evaluate("() => window.__stopTrajectoryRecording()")
        self._verify_trajectory_smoothness(samples, home_pos, target_pos, "ring", max_step_px=25.0)

    def test_c3_07_chording_mid_flight_handoff_and_reversal(self):
        """Mid-Flight Reversal: Releasing one key of a 2-key chord mid-flight smoothly retargets without snap."""
        home_pos = self.page.evaluate("() => ({ x: window.fingerState.ring.home.x, y: window.fingerState.ring.home.y })")
        target_w = self.page.evaluate("() => window.getKeyCenter('KeyW')")
        target_e = self.page.evaluate("() => window.getKeyCenter('KeyE')")

        self.page.evaluate("() => window.__startTrajectoryRecording('ring')")

        # Press KeyW
        self.page.keyboard.down("KeyW")
        self.page.wait_for_timeout(30)
        # Press KeyE (same finger chords to E)
        self.page.keyboard.down("KeyE")
        self.page.wait_for_timeout(40)
        # Release KeyE mid-flight (finger must reverse back toward KeyW)
        self.page.keyboard.up("KeyE")
        self.page.wait_for_timeout(60)
        # Release KeyW (finger returns to home KeyD)
        self.page.keyboard.up("KeyW")
        self.page.wait_for_timeout(220)

        samples = self.page.evaluate("() => window.__stopTrajectoryRecording()")
        self._verify_trajectory_smoothness(samples, home_pos, target_w, "ring", max_step_px=30.0)


if __name__ == "__main__":
    unittest.main()
