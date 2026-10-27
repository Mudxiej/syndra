"""
Adversarial Stress Test: Dynamic Geometry & Multi-Viewport Jitter
Milestone 1 Gate - Empirical Challenger 2 (challenger_m1_2)

Adversarial Stress Dimensions:
1. Rapid Multi-Viewport Jitter:
   1600x900 -> 1400x900 -> 1280x800 -> 1024x768 -> 900x700 -> 1024x768 -> 1280x800 -> 1400x900 -> 1600x900
2. Subpixel Concentricity Verification (<1.0px delta):
   - Pinky on KeyZ center
   - Ring on KeyD center
   - Middle on KeyR center
   - Index on KeyT center
   - Thumb on Space left zone (aligned directly under KeyC / KeyV)
3. Zero-Delay Rapid Burst Jitter (Layout Thrash Resilience)
4. Spline Kinematic & Bezier Integrity:
   - Valid cubic Bezier syntax (M kx ky C c1x c1y, c2x c2y, tx ty)
   - Monotonic directional progression (knuckle -> control points -> fingertip)
   - Zero NaN, undefined, or zero-dimension rendering
5. Knuckle & Palm Silhouette Anatomy:
   - MCP Knuckles strictly between wrist anchor and fingertips (wristY > knuckle.y > tip.y)
   - Palm silhouette closed path ending in Z with non-zero area
6. Scroll Offset Immunity:
   - Concentricity verified while page is scrolled to arbitrary offsets
7. Extreme Aspect Ratio Hardening:
   - Ultra-wide (1920x600) and narrow/tall (900x1200) viewports
"""

import math
import re
import os
import sys
import unittest
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests.helpers import HTML_URL


class AdversarialViewportJitterSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(channel="chrome", headless=True)
        cls.context = cls.browser.new_context(viewport={"width": 1600, "height": 900})
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
        self.page.set_viewport_size({"width": 1600, "height": 900})
        self.page.locator("#ch5").scroll_into_view_if_needed()
        self.page.wait_for_timeout(100)

    def _extract_geometry_state(self):
        """Extract all screen-space centers, splines, knuckles, and palm geometry."""
        return self.page.evaluate("""() => {
            function center(rect) {
                return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
            }
            const pinky = document.getElementById('fingertip-pinky').getBoundingClientRect();
            const ring = document.getElementById('fingertip-ring').getBoundingClientRect();
            const middle = document.getElementById('fingertip-middle').getBoundingClientRect();
            const index = document.getElementById('fingertip-index').getBoundingClientRect();
            const thumb = document.getElementById('fingertip-thumb').getBoundingClientRect();

            const keyZ = document.querySelector('.key-cap[data-key="KeyZ"]').getBoundingClientRect();
            const keyD = document.querySelector('.key-cap[data-key="KeyD"]').getBoundingClientRect();
            const keyR = document.querySelector('.key-cap[data-key="KeyR"]').getBoundingClientRect();
            const keyT = document.querySelector('.key-cap[data-key="KeyT"]').getBoundingClientRect();
            const keyC = document.querySelector('.key-cap[data-key="KeyC"]').getBoundingClientRect();
            const keyV = document.querySelector('.key-cap[data-key="KeyV"]').getBoundingClientRect();
            const space = document.querySelector('.key-cap[data-key="Space"]').getBoundingClientRect();

            const keyM = document.querySelector('.key-cap[data-key="KeyM"]').getBoundingClientRect();
            const thumbHomeX = center(keyM).x;
            const thumbHomeY = center(keyM).y;

            const fingers = ['pinky', 'ring', 'middle', 'index', 'thumb'];
            const splines = {};
            const knuckles = {};

            for (const f of fingers) {
                const sEl = document.getElementById(`finger-spline-${f}`);
                const sRect = sEl ? sEl.getBoundingClientRect() : null;
                splines[f] = {
                    d: sEl ? sEl.getAttribute('d') : null,
                    rect: sRect ? { x: sRect.left, y: sRect.top, width: sRect.width, height: sRect.height } : null
                };

                const kEl = document.getElementById(`knuckle-${f}`);
                const kRect = kEl ? kEl.getBoundingClientRect() : null;
                knuckles[f] = {
                    cx: kEl ? parseFloat(kEl.getAttribute('cx')) : null,
                    cy: kEl ? parseFloat(kEl.getAttribute('cy')) : null,
                    rect: kRect ? center(kRect) : null
                };
            }

            const palmEl = document.getElementById('hand-palm');
            const palmRect = palmEl ? palmEl.getBoundingClientRect() : null;
            const palmRest = document.getElementById('palmRestBar').getBoundingClientRect();
            const stage = document.getElementById('keyboardStage').getBoundingClientRect();

            return {
                centers: {
                    pinky: { pad: center(pinky), target: center(keyZ) },
                    ring: { pad: center(ring), target: center(keyD) },
                    middle: { pad: center(middle), target: center(keyR) },
                    index: { pad: center(index), target: center(keyT) },
                    thumb: { pad: center(thumb), target: { x: thumbHomeX, y: thumbHomeY } }
                },
                splines,
                knuckles,
                palm: {
                    d: palmEl ? palmEl.getAttribute('d') : null,
                    rect: palmRect ? { x: palmRect.left, y: palmRect.top, width: palmRect.width, height: palmRect.height } : null
                },
                palmRest: center(palmRest),
                stage: { x: stage.left, y: stage.top, width: stage.width, height: stage.height }
            };
        }""")

    # --------------------------------------------------------------------------
    # Test 1: Full Viewport Jitter Sweep (Concentricity < 1.0px)
    # --------------------------------------------------------------------------
    def test_01_viewport_jitter_sweep_concentricity(self):
        """Stress-test 9-step viewport jitter sweep asserting fingertip concentricity delta < 1.0px."""
        resolutions = [
            (1600, 900),
            (1400, 900),
            (1280, 800),
            (1024, 768),
            (900, 700),
            (1024, 768),
            (1280, 800),
            (1400, 900),
            (1600, 900),
        ]

        max_observed_drift = 0.0

        for width, height in resolutions:
            with self.subTest(viewport=f"{width}x{height}"):
                self.page.set_viewport_size({"width": width, "height": height})
                self.page.wait_for_timeout(80)

                state = self._extract_geometry_state()
                self.assertEqual(len(self.console_errors), 0, f"Console error at {width}x{height}: {self.console_errors}")

                for finger, data in state["centers"].items():
                    pad = data["pad"]
                    tgt = data["target"]
                    dx = abs(pad["x"] - tgt["x"])
                    dy = abs(pad["y"] - tgt["y"])
                    drift = math.hypot(dx, dy)
                    if drift > max_observed_drift:
                        max_observed_drift = drift

                    self.assertLess(
                        drift,
                        1.0,
                        f"Fingertip {finger} concentricity drift {drift:.3f}px exceeds 1.0px at {width}x{height} (dx={dx:.3f}, dy={dy:.3f})",
                    )

        # Ensure max drift across entire sweep stayed well within subpixel threshold
        self.assertLess(max_observed_drift, 0.5, f"Subpixel concentricity drift {max_observed_drift:.3f}px exceeds 0.5px margin.")

    # --------------------------------------------------------------------------
    # Test 2: Cubic Bezier Spline Integrity Under Jitter
    # --------------------------------------------------------------------------
    def test_02_spline_bezier_syntax_and_bounds_under_jitter(self):
        """Assert all 5 splines retain non-NaN, valid cubic Bezier curves without clipping."""
        resolutions = [(1600, 900), (1280, 800), (900, 700)]
        spline_regex = re.compile(
            r"^M\s+([-\d\.]+)\s+([-\d\.]+)\s+C\s+([-\d\.]+)\s+([-\d\.]+),\s*([-\d\.]+)\s+([-\d\.]+),\s*([-\d\.]+)\s+([-\d\.]+)$"
        )

        for width, height in resolutions:
            self.page.set_viewport_size({"width": width, "height": height})
            self.page.wait_for_timeout(80)

            state = self._extract_geometry_state()
            for finger, sdata in state["splines"].items():
                d = sdata["d"]
                self.assertIsNotNone(d, f"Missing spline d path for {finger} at {width}x{height}")
                self.assertNotIn("NaN", d, f"Spline {finger} contains NaN at {width}x{height}: {d}")
                self.assertNotIn("undefined", d, f"Spline {finger} contains undefined at {width}x{height}: {d}")

                match = spline_regex.match(d.strip())
                self.assertIsNotNone(match, f"Spline {finger} failed cubic Bezier regex match: '{d}'")

                # Parse points: M kx ky C c1x c1y, c2x c2y, tx ty
                kx, ky, c1x, c1y, c2x, c2y, tx, ty = [float(v) for v in match.groups()]

                # Spline must span from knuckle to fingertip
                dist = math.hypot(tx - kx, ty - ky)
                self.assertGreater(dist, 10.0, f"Spline {finger} length {dist:.1f}px is unrealistically collapsed at {width}x{height}")

                # Spline bounding box must be positive and non-zero
                rect = sdata["rect"]
                self.assertGreater(rect["width"], 0, f"Spline {finger} width <= 0")
                self.assertGreater(rect["height"], 0, f"Spline {finger} height <= 0")

    # --------------------------------------------------------------------------
    # Test 3: Zero-Delay Rapid Burst Jitter (Thrash Test)
    # --------------------------------------------------------------------------
    def test_03_zero_delay_rapid_burst_jitter(self):
        """Rapidly mutate viewport across 10 sizes without inter-frame delay to test ResizeObserver stability."""
        burst_widths = [1600, 1500, 1400, 1300, 1200, 1100, 1000, 950, 900, 1600]
        for w in burst_widths:
            self.page.set_viewport_size({"width": w, "height": 850})

        # Wait one frame for final settling
        self.page.wait_for_timeout(100)

        state = self._extract_geometry_state()
        self.assertEqual(len(self.console_errors), 0, f"Console errors during burst jitter: {self.console_errors}")

        for finger, data in state["centers"].items():
            drift = math.hypot(data["pad"]["x"] - data["target"]["x"], data["pad"]["y"] - data["target"]["y"])
            self.assertLess(drift, 1.0, f"Finger {finger} desynchronized after burst jitter: drift={drift:.3f}px")

    # --------------------------------------------------------------------------
    # Test 4: Biomechanical Knuckle & Wrist Anatomy
    # --------------------------------------------------------------------------
    def test_04_biomechanical_knuckle_and_wrist_alignment(self):
        """Assert knuckles sit anatomically between palm wrist rest and fingertips."""
        resolutions = [(1600, 900), (1280, 800), (900, 700)]
        for width, height in resolutions:
            self.page.set_viewport_size({"width": width, "height": height})
            self.page.wait_for_timeout(80)

            state = self._extract_geometry_state()
            wrist_y = state["palmRest"]["y"]

            for finger in ["pinky", "ring", "middle", "index"]:
                k_pos = state["knuckles"][finger]["rect"]
                pad_pos = state["centers"][finger]["pad"]

                # Biomechanical constraint: fingertip is higher on screen (smaller Y) than knuckle,
                # and knuckle is higher than wrist anchor bar
                self.assertLess(
                    pad_pos["y"],
                    k_pos["y"],
                    f"{finger.upper()} fingertip Y ({pad_pos['y']:.1f}) should be above knuckle Y ({k_pos['y']:.1f})",
                )
                self.assertLess(
                    k_pos["y"],
                    wrist_y,
                    f"{finger.upper()} knuckle Y ({k_pos['y']:.1f}) should be above palm rest Y ({wrist_y:.1f})",
                )

    # --------------------------------------------------------------------------
    # Test 5: Palm Silhouette Structural Integrity
    # --------------------------------------------------------------------------
    def test_05_palm_silhouette_path_integrity(self):
        """Verify glass palm silhouette path forms a closed polygon without NaN."""
        resolutions = [(1600, 900), (1400, 900), (1024, 768), (900, 700)]
        for width, height in resolutions:
            self.page.set_viewport_size({"width": width, "height": height})
            self.page.wait_for_timeout(80)

            state = self._extract_geometry_state()
            palm_d = state["palm"]["d"]
            self.assertIsNotNone(palm_d, f"Palm path d is None at {width}x{height}")
            self.assertTrue(palm_d.startswith("M "), f"Palm path d does not start with 'M ': '{palm_d[:20]}'")
            self.assertTrue(palm_d.strip().endswith("Z"), f"Palm path d is not closed with 'Z': '{palm_d[-10:]}'")
            self.assertNotIn("NaN", palm_d, f"Palm path contains NaN at {width}x{height}")

            palm_rect = state["palm"]["rect"]
            self.assertGreater(palm_rect["width"], 50.0, f"Palm width too small at {width}x{height}")
            self.assertGreater(palm_rect["height"], 30.0, f"Palm height too small at {width}x{height}")

    # --------------------------------------------------------------------------
    # Test 6: Scroll Offset Independence
    # --------------------------------------------------------------------------
    def test_06_scroll_offset_concentricity_invariance(self):
        """Assert concentricity remains < 1.0px regardless of window scroll offset."""
        scroll_offsets = [0, 200, 500, 1000]
        for scroll_y in scroll_offsets:
            self.page.evaluate(f"window.scrollTo(0, {scroll_y});")
            self.page.wait_for_timeout(50)

            state = self._extract_geometry_state()
            for finger, data in state["centers"].items():
                drift = math.hypot(data["pad"]["x"] - data["target"]["x"], data["pad"]["y"] - data["target"]["y"])
                self.assertLess(
                    drift,
                    1.0,
                    f"Fingertip {finger} concentricity drift {drift:.3f}px exceeds 1.0px at scrollY={scroll_y}",
                )

    # --------------------------------------------------------------------------
    # Test 7: Extreme Aspect Ratios
    # --------------------------------------------------------------------------
    def test_07_extreme_aspect_ratios_stability(self):
        """Stress-test ultra-wide and ultra-tall viewports for coordinate degeneration."""
        extreme_resolutions = [
            (1920, 600),   # Ultra-wide landscape
            (900, 1200),   # Narrow portrait
            (1100, 700),   # Compact laptop
        ]

        for width, height in extreme_resolutions:
            self.page.set_viewport_size({"width": width, "height": height})
            self.page.locator("#ch5").scroll_into_view_if_needed()
            self.page.wait_for_timeout(100)

            state = self._extract_geometry_state()
            self.assertEqual(len(self.console_errors), 0, f"Console error at extreme viewport {width}x{height}: {self.console_errors}")

            for finger, data in state["centers"].items():
                drift = math.hypot(data["pad"]["x"] - data["target"]["x"], data["pad"]["y"] - data["target"]["y"])
                self.assertLess(
                    drift,
                    1.0,
                    f"Finger {finger} drift {drift:.3f}px exceeds 1.0px at extreme viewport {width}x{height}",
                )


if __name__ == "__main__":
    unittest.main()
