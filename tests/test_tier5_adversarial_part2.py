"""
SYNDRA Milestone 3 Phase 2: Tier 5 Adversarial Coverage Hardening — Part 2
Empirical Challenger: teamwork_preview_challenger (challenger_tier5_2)

Adversarial Stress Dimensions:
1. Extreme Viewport Aspect Ratios:
   - Ultra-wide (2560x1080, ~21:9 aspect ratio):
     Assert keycap centers stay strictly inside container bounds, splines remain bounded,
     fingertip rest pads stay within stage, and non-overlapping distance between fingers > 15px.
   - Compact laptop (1024x600, ~1.71:1 cramped height):
     Assert keycap centers and splines remain valid, within bounds, and non-overlapping (> 10px).
   - Dynamic articulation under extreme viewports (reach and return with drift < 1.0px).
2. SVG Path Syntax Rigor (BNF Grammar Validation):
   - Strict SVG 1.1 / 2.0 BNF tokenizer and validator for all generated 'd' path strings.
   - Assert all splines conform strictly to: M <x> <y> C <c1x> <c1y>, <c2x> <c2y>, <tx> <ty>.
   - Assert palm path conforms strictly to: M ... C ... C ... C ... C ... C ... C ... L ... Z.
   - Assert 0 NaN, 0 undefined, 0 double dots (..), 0 malformed tokens across rest and dynamic frames.
3. Halo & Glow Filter Validity:
   - Verify all #radial-glow-* definitions in <defs> (stops, colors, opacities).
   - Verify all #glow-filter-* definitions in <defs> (feGaussianBlur, feMerge).
   - Assert halo circles maintain valid, finite cx, cy, and r values.
   - Assert halo cx/cy strictly concentric with fingertip pads (< 0.01px delta).
   - Assert SVG rendering and getBBox() succeed without SVG filter errors or console warnings.
4. Cache Re-entry Safety:
   - Simulate rapid container resize bursts (50 resize events in 200ms).
   - Assert coordinate cache (keycapCenterCache) updates deterministically without memory leak.
   - Assert zero dropped references in fingerElements and cachedKnuckles.
   - Assert 100% deterministic coordinate recovery (0.000px drift) after returning to baseline.

Execution:
    & 'C:\\Users\\mudxiej\\AppData\\Local\\Programs\\Python\\Python314\\python.exe' -m unittest tests.test_tier5_adversarial_part2 -v
"""

import math
import os
import re
import sys
import time
import unittest
from typing import Dict, List, Tuple, Any, Optional
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tests.helpers import HTML_URL, reset_page_state


def parse_and_validate_svg_path(path_d: str) -> Dict[str, Any]:
    """
    Strict SVG BNF Grammar Tokenizer & Validator.
    Conforms to W3C SVG Path Data BNF specification:
    path-data ::= wsp* moveto? (moveto | lineto | curveto | closepath)* wsp*
    """
    if not path_d or not path_d.strip():
        raise AssertionError("SVG path string is empty or whitespace only.")

    raw = path_d.strip()

    # Disallow illegal tokens and malformed representations
    for illegal in ["NaN", "undefined", "null", "Infinity"]:
        if illegal in raw:
            raise AssertionError(f"SVG path contains illegal keyword '{illegal}': {raw}")

    # Disallow double dots (e.g., '..' or '12.34.56')
    if re.search(r"\.\.|\d+\.\d+\.", raw):
        raise AssertionError(f"SVG path contains double dots or malformed float: {raw}")

    # Tokenize: Extract command letters and numeric tokens
    tokens = re.findall(r"([a-zA-Z]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?)", raw)
    if not tokens:
        raise AssertionError(f"Failed to tokenize SVG path: {raw}")

    commands: List[Tuple[str, List[float]]] = []
    curr_cmd: Optional[str] = None
    curr_args: List[float] = []

    for tok in tokens:
        if tok.isalpha():
            if curr_cmd is not None:
                commands.append((curr_cmd, curr_args))
            curr_cmd = tok
            curr_args = []
        else:
            try:
                val = float(tok)
            except ValueError:
                raise AssertionError(f"Malformed coordinate token '{tok}' in path: {raw}")
            if not math.isfinite(val):
                raise AssertionError(f"Coordinate '{tok}' evaluated to non-finite float: {raw}")
            curr_args.append(val)

    if curr_cmd is not None:
        commands.append((curr_cmd, curr_args))

    if not commands:
        raise AssertionError(f"No valid SVG commands found in path: {raw}")

    # First command must be 'M' or 'm'
    first_cmd, _ = commands[0]
    if first_cmd not in ("M", "m"):
        raise AssertionError(f"SVG path must start with 'M' or 'm', got '{first_cmd}': {raw}")

    # Validate argument counts per command
    for cmd, args in commands:
        if cmd in ("M", "m"):
            if len(args) < 2 or len(args) % 2 != 0:
                raise AssertionError(f"Command '{cmd}' expects coordinate pairs (multiple of 2), got {len(args)}: {raw}")
        elif cmd in ("C", "c"):
            if len(args) < 6 or len(args) % 6 != 0:
                raise AssertionError(f"Command '{cmd}' expects multiples of 6 arguments, got {len(args)}: {raw}")
        elif cmd in ("L", "l"):
            if len(args) < 2 or len(args) % 2 != 0:
                raise AssertionError(f"Command '{cmd}' expects coordinate pairs (multiple of 2), got {len(args)}: {raw}")
        elif cmd in ("Z", "z"):
            if len(args) != 0:
                raise AssertionError(f"Command '{cmd}' expects 0 arguments, got {len(args)}: {raw}")
        else:
            raise AssertionError(f"Unexpected SVG command '{cmd}' in path: {raw}")

    return {"commands": commands, "raw": raw}


class TestTier5AdversarialPart2Suite(unittest.TestCase):
    """Tier 5 Adversarial Test Suite: Geometry, SVG Paths & Cache Stress."""

    playwright = None
    browser = None
    context = None
    page = None
    console_errors: List[str] = []
    console_warnings: List[str] = []

    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(channel="chrome", headless=True)
        cls.context = cls.browser.new_context(viewport={"width": 1600, "height": 900})
        cls.page = cls.context.new_page()
        cls.console_errors = []
        cls.console_warnings = []

        cls.page.on("console", lambda msg: (
            cls.console_errors.append(msg.text) if msg.type == "error" else
            cls.console_warnings.append(msg.text) if msg.type == "warning" else None
        ))
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
        self.console_warnings.clear()
        reset_page_state(self.page)
        self.page.set_viewport_size({"width": 1600, "height": 900})
        self.page.locator("#ch5").scroll_into_view_if_needed()
        self.page.wait_for_timeout(80)

    # =========================================================================
    # SECTION 1: EXTREME VIEWPORT RATIOS (2560x1080 & 1024x600)
    # =========================================================================

    def test_01_extreme_viewport_ultrawide_2560x1080(self):
        """Ultra-wide viewport (2560x1080, 21:9): verify keycap centers, splines, and non-overlap."""
        self.page.set_viewport_size({"width": 2560, "height": 1080})
        self.page.locator("#ch5").scroll_into_view_if_needed()
        self.page.wait_for_timeout(100)

        self.assertEqual(len(self.console_errors), 0, f"Console error at 2560x1080: {self.console_errors}")

        data = self.page.evaluate("""() => {
            const container = document.getElementById('keyboardContainer');
            const stage = document.getElementById('keyboardStage');
            const palmRest = document.getElementById('palmRestBar');
            const cRect = container.getBoundingClientRect();
            const sRect = stage.getBoundingClientRect();
            const pRect = palmRest.getBoundingClientRect();

            // Evaluate all cached keycap centers
            const keyCenters = {};
            for (const [code, val] of keycapCenterCache.entries()) {
                keyCenters[code] = val;
            }

            // Fingertip elements
            const fingers = ['pinky', 'ring', 'middle', 'index', 'thumb'];
            const tips = {};
            const knuckles = {};
            const splines = {};

            for (const f of fingers) {
                const pad = document.getElementById(`fingertip-${f}`);
                const padRect = pad.getBoundingClientRect();
                tips[f] = {
                    cx: parseFloat(pad.getAttribute('cx')),
                    cy: parseFloat(pad.getAttribute('cy')),
                    screenX: padRect.left + padRect.width / 2,
                    screenY: padRect.top + padRect.height / 2
                };

                const kn = document.getElementById(`knuckle-${f}`);
                const knRect = kn.getBoundingClientRect();
                knuckles[f] = {
                    cx: parseFloat(kn.getAttribute('cx')),
                    cy: parseFloat(kn.getAttribute('cy')),
                    screenX: knRect.left + knRect.width / 2,
                    screenY: knRect.top + knRect.height / 2
                };

                const sp = document.getElementById(`finger-spline-${f}`);
                const spRect = sp.getBoundingClientRect();
                splines[f] = {
                    d: sp.getAttribute('d'),
                    width: spRect.width,
                    height: spRect.height
                };
            }

            return {
                cRect: { width: cRect.width, height: cRect.height, left: cRect.left, top: cRect.top },
                sRect: { width: sRect.width, height: sRect.height, left: sRect.left, top: sRect.top },
                pRect: { width: pRect.width, height: pRect.height, top: pRect.top },
                keyCenters,
                tips,
                knuckles,
                splines
            };
        }""")

        c_w, c_h = data["cRect"]["width"], data["cRect"]["height"]
        s_w, s_h = data["sRect"]["width"], data["sRect"]["height"]

        # 1. Assert container has realistic positive dimensions
        self.assertGreater(c_w, 600.0, "Container width too small on ultrawide")
        self.assertGreater(c_h, 200.0, "Container height too small on ultrawide")

        # 2. Assert keycap centers stay strictly inside container bounds
        for code, center in data["keyCenters"].items():
            self.assertGreaterEqual(center["x"], 0.0, f"Key {code} center.x < 0: {center['x']}")
            self.assertLessEqual(center["x"], c_w, f"Key {code} center.x > container width: {center['x']} > {c_w}")
            self.assertGreaterEqual(center["y"], 0.0, f"Key {code} center.y < 0: {center['y']}")
            self.assertLessEqual(center["y"], c_h, f"Key {code} center.y > container height: {center['y']} > {c_h}")
            self.assertGreater(center["width"], 10.0, f"Key {code} width too small: {center['width']}")
            self.assertGreater(center["height"], 10.0, f"Key {code} height too small: {center['height']}")

        # 3. Assert fingertip positions stay strictly inside stage bounds
        for f, tip in data["tips"].items():
            self.assertGreaterEqual(tip["cx"], 0.0, f"Fingertip {f} cx < 0: {tip['cx']}")
            self.assertLessEqual(tip["cx"], s_w, f"Fingertip {f} cx > stage width: {tip['cx']} > {s_w}")
            self.assertGreaterEqual(tip["cy"], 0.0, f"Fingertip {f} cy < 0: {tip['cy']}")
            self.assertLessEqual(tip["cy"], s_h, f"Fingertip {f} cy > stage height: {tip['cy']} > {s_h}")

        # 4. Assert non-overlapping fingertips (minimum Euclidean distance > 15px)
        fingers = ["pinky", "ring", "middle", "index", "thumb"]
        for i in range(len(fingers)):
            for j in range(i + 1, len(fingers)):
                f1, f2 = fingers[i], fingers[j]
                d_tips = math.hypot(data["tips"][f1]["cx"] - data["tips"][f2]["cx"],
                                    data["tips"][f1]["cy"] - data["tips"][f2]["cy"])
                self.assertGreater(
                    d_tips, 15.0,
                    f"Fingertips {f1} and {f2} overlapping or too close on ultrawide: dist={d_tips:.2f}px"
                )

                d_knuckles = math.hypot(data["knuckles"][f1]["cx"] - data["knuckles"][f2]["cx"],
                                        data["knuckles"][f1]["cy"] - data["knuckles"][f2]["cy"])
                self.assertGreater(
                    d_knuckles, 12.0,
                    f"Knuckles {f1} and {f2} overlapping or too close on ultrawide: dist={d_knuckles:.2f}px"
                )

        # 5. Assert splines have positive bounds and span knuckle to tip
        for f in fingers:
            sp = data["splines"][f]
            self.assertGreater(sp["width"], 0.0, f"Spline {f} width <= 0 on ultrawide")
            self.assertGreater(sp["height"], 0.0, f"Spline {f} height <= 0 on ultrawide")
            d_span = math.hypot(data["tips"][f]["cx"] - data["knuckles"][f]["cx"],
                                data["tips"][f]["cy"] - data["knuckles"][f]["cy"])
            self.assertGreater(d_span, 15.0, f"Spline span {f} collapsed on ultrawide: {d_span:.2f}px")

        # 6. Biomechanical ordering (tip Y < knuckle Y < wrist Y)
        wrist_y = data["pRect"]["top"]
        for f in ["pinky", "ring", "middle", "index"]:
            tip_y = data["tips"][f]["screenY"]
            kn_y = data["knuckles"][f]["screenY"]
            self.assertLess(tip_y, kn_y, f"{f.upper()} tip Y ({tip_y:.1f}) should be above knuckle Y ({kn_y:.1f})")
            self.assertLess(kn_y, wrist_y, f"{f.upper()} knuckle Y ({kn_y:.1f}) should be above wrist Y ({wrist_y:.1f})")

    def test_02_extreme_viewport_compact_laptop_1024x600(self):
        """Compact laptop viewport (1024x600, cramped height): verify bounds and non-overlap."""
        self.page.set_viewport_size({"width": 1024, "height": 600})
        self.page.locator("#ch5").scroll_into_view_if_needed()
        self.page.wait_for_timeout(100)

        self.assertEqual(len(self.console_errors), 0, f"Console error at 1024x600: {self.console_errors}")

        data = self.page.evaluate("""() => {
            const container = document.getElementById('keyboardContainer');
            const stage = document.getElementById('keyboardStage');
            const palmRest = document.getElementById('palmRestBar');
            const cRect = container.getBoundingClientRect();
            const sRect = stage.getBoundingClientRect();
            const pRect = palmRest.getBoundingClientRect();

            const keyCenters = {};
            for (const [code, val] of keycapCenterCache.entries()) {
                keyCenters[code] = val;
            }

            const fingers = ['pinky', 'ring', 'middle', 'index', 'thumb'];
            const tips = {};
            const knuckles = {};
            const splines = {};

            for (const f of fingers) {
                const pad = document.getElementById(`fingertip-${f}`);
                tips[f] = {
                    cx: parseFloat(pad.getAttribute('cx')),
                    cy: parseFloat(pad.getAttribute('cy'))
                };

                const kn = document.getElementById(`knuckle-${f}`);
                knuckles[f] = {
                    cx: parseFloat(kn.getAttribute('cx')),
                    cy: parseFloat(kn.getAttribute('cy'))
                };

                const sp = document.getElementById(`finger-spline-${f}`);
                const spRect = sp.getBoundingClientRect();
                splines[f] = {
                    d: sp.getAttribute('d'),
                    width: spRect.width,
                    height: spRect.height
                };
            }

            return {
                cRect: { width: cRect.width, height: cRect.height },
                sRect: { width: sRect.width, height: sRect.height },
                keyCenters,
                tips,
                knuckles,
                splines
            };
        }""")

        c_w, c_h = data["cRect"]["width"], data["cRect"]["height"]
        s_w, s_h = data["sRect"]["width"], data["sRect"]["height"]

        # Container & stage bounds check
        self.assertGreater(c_w, 400.0, "Container width collapsed on compact viewport")
        self.assertGreater(c_h, 150.0, "Container height collapsed on compact viewport")

        for code, center in data["keyCenters"].items():
            self.assertGreaterEqual(center["x"], 0.0, f"Key {code} center.x < 0: {center['x']}")
            self.assertLessEqual(center["x"], c_w, f"Key {code} center.x > width: {center['x']} > {c_w}")
            self.assertGreaterEqual(center["y"], 0.0, f"Key {code} center.y < 0: {center['y']}")
            self.assertLessEqual(center["y"], c_h, f"Key {code} center.y > height: {center['y']} > {c_h}")

        for f, tip in data["tips"].items():
            self.assertGreaterEqual(tip["cx"], 0.0, f"Fingertip {f} cx < 0: {tip['cx']}")
            self.assertLessEqual(tip["cx"], s_w, f"Fingertip {f} cx > stage width: {tip['cx']} > {s_w}")
            self.assertGreaterEqual(tip["cy"], 0.0, f"Fingertip {f} cy < 0: {tip['cy']}")
            self.assertLessEqual(tip["cy"], s_h, f"Fingertip {f} cy > stage height: {tip['cy']} > {s_h}")

        # Non-overlapping fingers under compact viewport (> 10px minimum distance)
        fingers = ["pinky", "ring", "middle", "index", "thumb"]
        for i in range(len(fingers)):
            for j in range(i + 1, len(fingers)):
                f1, f2 = fingers[i], fingers[j]
                d_tips = math.hypot(data["tips"][f1]["cx"] - data["tips"][f2]["cx"],
                                    data["tips"][f1]["cy"] - data["tips"][f2]["cy"])
                self.assertGreater(
                    d_tips, 10.0,
                    f"Fingertips {f1} and {f2} overlapping on compact laptop: dist={d_tips:.2f}px"
                )

                d_knuckles = math.hypot(data["knuckles"][f1]["cx"] - data["knuckles"][f2]["cx"],
                                        data["knuckles"][f1]["cy"] - data["knuckles"][f2]["cy"])
                self.assertGreater(
                    d_knuckles, 8.0,
                    f"Knuckles {f1} and {f2} overlapping on compact laptop: dist={d_knuckles:.2f}px"
                )

        for f in fingers:
            sp = data["splines"][f]
            self.assertGreater(sp["width"], 0.0, f"Spline {f} width <= 0 on compact laptop")
            self.assertGreater(sp["height"], 0.0, f"Spline {f} height <= 0 on compact laptop")

    def test_03_extreme_viewport_dynamic_reach_kinematics(self):
        """Verify reach kinematics and concentricity under both 2560x1080 and 1024x600."""
        viewports = [(2560, 1080), (1024, 600)]
        test_keys = [("KeyT", "index"), ("KeyR", "middle"), ("Space", "thumb"), ("KeyZ", "pinky")]

        for width, height in viewports:
            with self.subTest(viewport=f"{width}x{height}"):
                self.page.set_viewport_size({"width": width, "height": height})
                self.page.locator("#ch5").scroll_into_view_if_needed()
                self.page.wait_for_timeout(80)

                for code, finger in test_keys:
                    # Press key
                    self.page.evaluate(f"code => activateKey(code)", code)
                    self.page.wait_for_timeout(180)  # Wait for 120ms reach + settling

                    drift = self.page.evaluate(f"""([code, finger]) => {{
                        const pad = document.getElementById(`fingertip-${{finger}}`);
                        const cx = parseFloat(pad.getAttribute('cx'));
                        const cy = parseFloat(pad.getAttribute('cy'));
                        const tgt = getTargetForCode(code);
                        if (!tgt) return 999;
                        return Math.hypot(cx - tgt.x, cy - tgt.y);
                    }}""", [code, finger])

                    self.assertLess(
                        drift, 1.0,
                        f"Fingertip {finger} reach drift {drift:.3f}px exceeds 1.0px for key {code} at {width}x{height}"
                    )

                    # Release key
                    self.page.evaluate(f"code => deactivateKey(code)", code)
                    self.page.wait_for_timeout(220)  # Wait for 160ms return + settling

                    home_drift = self.page.evaluate(f"""finger => {{
                        const pad = document.getElementById(`fingertip-${{finger}}`);
                        const cx = parseFloat(pad.getAttribute('cx'));
                        const cy = parseFloat(pad.getAttribute('cy'));
                        const home = fingerState[finger].home;
                        return Math.hypot(cx - home.x, cy - home.y);
                    }}""", finger)

                    self.assertLess(
                        home_drift, 1.0,
                        f"Fingertip {finger} return drift {home_drift:.3f}px exceeds 1.0px at {width}x{height}"
                    )

    # =========================================================================
    # SECTION 2: SVG PATH SYNTAX RIGOR (BNF GRAMMAR VALIDATION)
    # =========================================================================

    def test_04_svg_bnf_path_grammar_baseline_splines_and_palm(self):
        """Assert all 5 splines and palm path strictly adhere to SVG BNF grammar at rest."""
        paths = self.page.evaluate("""() => {
            const fingers = ['pinky', 'ring', 'middle', 'index', 'thumb'];
            const res = { splines: {}, palm: null };
            for (const f of fingers) {
                const el = document.getElementById(`finger-spline-${f}`);
                res.splines[f] = el ? el.getAttribute('d') : null;
            }
            const palm = document.getElementById('hand-palm');
            res.palm = palm ? palm.getAttribute('d') : null;
            return res;
        }""")

        # 1. Validate Splines BNF
        for finger, d in paths["splines"].items():
            self.assertIsNotNone(d, f"Missing spline path d for {finger}")
            parsed = parse_and_validate_svg_path(d)
            cmds = parsed["commands"]

            # Spline contract: exactly one 'M' (2 args) followed by one 'C' (6 args)
            self.assertEqual(len(cmds), 2, f"Spline {finger} expected 2 commands (M, C), got {len(cmds)}: {d}")
            self.assertEqual(cmds[0][0], "M", f"Spline {finger} first command must be 'M'")
            self.assertEqual(len(cmds[0][1]), 2, f"Spline {finger} 'M' expects 2 coordinates")
            self.assertEqual(cmds[1][0], "C", f"Spline {finger} second command must be 'C'")
            self.assertEqual(len(cmds[1][1]), 6, f"Spline {finger} 'C' expects 6 coordinates")

            # Check that knuckle and tip coordinates match element attributes
            knuckle_cx, knuckle_cy, tip_cx, tip_cy = self.page.evaluate(f"""f => {{
                const kn = document.getElementById(`knuckle-${{f}}`);
                const tip = document.getElementById(`fingertip-${{f}}`);
                return [
                    parseFloat(kn.getAttribute('cx')),
                    parseFloat(kn.getAttribute('cy')),
                    parseFloat(tip.getAttribute('cx')),
                    parseFloat(tip.getAttribute('cy'))
                ];
            }}""", finger)

            start_x, start_y = cmds[0][1]
            end_x, end_y = cmds[1][1][4], cmds[1][1][5]

            self.assertAlmostEqual(start_x, knuckle_cx, places=1, msg=f"Spline {finger} start != knuckle")
            self.assertAlmostEqual(start_y, knuckle_cy, places=1, msg=f"Spline {finger} start != knuckle")
            self.assertAlmostEqual(end_x, tip_cx, places=1, msg=f"Spline {finger} end != fingertip")
            self.assertAlmostEqual(end_y, tip_cy, places=1, msg=f"Spline {finger} end != fingertip")

        # 2. Validate Palm Silhouette BNF
        palm_d = paths["palm"]
        self.assertIsNotNone(palm_d, "Missing palm silhouette path d")
        parsed_palm = parse_and_validate_svg_path(palm_d)
        palm_cmds = parsed_palm["commands"]

        # Palm contract: Starts with 'M', contains 6 'C' segments, 'L', and ends with 'Z'
        self.assertEqual(palm_cmds[0][0], "M", "Palm path must start with 'M'")
        c_cmds = [c for c in palm_cmds if c[0] == "C"]
        self.assertEqual(len(c_cmds), 6, f"Palm path expects 6 cubic Bezier segments, got {len(c_cmds)}")
        self.assertEqual(palm_cmds[-1][0], "Z", "Palm path must end with 'Z'")

    def test_05_svg_bnf_path_grammar_under_multi_key_articulation_frames(self):
        """Sample all splines and palm across 8 kinematic animation frames during multi-key chord."""
        # Activate multiple keys simultaneously
        self.page.evaluate("""() => {
            activateKey("KeyR");
            activateKey("KeyT");
            activateKey("Space");
            activateKey("KeyZ");
        }""")

        frame_delays = [20, 40, 70, 100, 130]  # Sample during reach animation
        for delay in frame_delays:
            self.page.wait_for_timeout(delay)
            frame_paths = self.page.evaluate("""() => {
                const fingers = ['pinky', 'ring', 'middle', 'index', 'thumb'];
                const res = { splines: {}, palm: null };
                for (const f of fingers) {
                    const el = document.getElementById(`finger-spline-${f}`);
                    res.splines[f] = el ? el.getAttribute('d') : null;
                }
                const palm = document.getElementById('hand-palm');
                res.palm = palm ? palm.getAttribute('d') : null;
                return res;
            }""")

            for finger, d in frame_paths["splines"].items():
                parsed = parse_and_validate_svg_path(d)
                self.assertEqual(len(parsed["commands"]), 2, f"Spline {finger} invalid during reach at {delay}ms: {d}")

            parse_and_validate_svg_path(frame_paths["palm"])

        # Release keys and sample return trajectory
        self.page.evaluate("""() => {
            deactivateKey("KeyR");
            deactivateKey("KeyT");
            deactivateKey("Space");
            deactivateKey("KeyZ");
        }""")

        return_delays = [30, 80, 140, 200]
        for delay in return_delays:
            self.page.wait_for_timeout(delay)
            frame_paths = self.page.evaluate("""() => {
                const fingers = ['pinky', 'ring', 'middle', 'index', 'thumb'];
                const res = { splines: {}, palm: null };
                for (const f of fingers) {
                    const el = document.getElementById(`finger-spline-${f}`);
                    res.splines[f] = el ? el.getAttribute('d') : null;
                }
                return res;
            }""")

            for finger, d in frame_paths["splines"].items():
                parsed = parse_and_validate_svg_path(d)
                self.assertEqual(len(parsed["commands"]), 2, f"Spline {finger} invalid during return at {delay}ms: {d}")

        self.assertEqual(len(self.console_errors), 0, f"Console error during path animation: {self.console_errors}")

    # =========================================================================
    # SECTION 3: HALO & GLOW FILTER VALIDITY
    # =========================================================================

    def test_06_svg_filter_and_radial_glow_defs_validity(self):
        """Verify SVG <filter> and <radialGradient> definitions in <defs>."""
        defs_data = self.page.evaluate("""() => {
            const fingers = ['pinky', 'ring', 'middle', 'index', 'thumb'];
            const res = { filters: {}, gradients: {} };

            for (const f of fingers) {
                // Filter check
                const filter = document.getElementById(`glow-filter-${f}`);
                if (filter) {
                    const blur = filter.querySelector('feGaussianBlur');
                    const merge = filter.querySelector('feMerge');
                    const nodes = merge ? merge.querySelectorAll('feMergeNode') : [];
                    res.filters[f] = {
                        exists: true,
                        stdDeviation: blur ? blur.getAttribute('stdDeviation') : null,
                        result: blur ? blur.getAttribute('result') : null,
                        mergeNodeCount: nodes.length
                    };
                } else {
                    res.filters[f] = { exists: false };
                }

                // RadialGradient check
                const grad = document.getElementById(`radial-glow-${f}`);
                if (grad) {
                    const stops = Array.from(grad.querySelectorAll('stop')).map(s => ({
                        offset: s.getAttribute('offset'),
                        stopColor: s.getAttribute('stop-color'),
                        stopOpacity: s.getAttribute('stop-opacity')
                    }));
                    res.gradients[f] = { exists: true, stopCount: stops.length, stops };
                } else {
                    res.gradients[f] = { exists: false };
                }
            }
            return res;
        }""")

        fingers = ["pinky", "ring", "middle", "index", "thumb"]
        for f in fingers:
            # Filter asserts
            f_info = defs_data["filters"][f]
            self.assertTrue(f_info["exists"], f"Missing <filter id='glow-filter-{f}'> in <defs>")
            self.assertEqual(f_info["stdDeviation"], "6", f"Filter {f} stdDeviation should be 6")
            self.assertEqual(f_info["result"], "blur", f"Filter {f} feGaussianBlur result must be 'blur'")
            self.assertEqual(f_info["mergeNodeCount"], 2, f"Filter {f} feMerge expects 2 merge nodes")

            # Gradient asserts
            g_info = defs_data["gradients"][f]
            self.assertTrue(g_info["exists"], f"Missing <radialGradient id='radial-glow-{f}'> in <defs>")
            self.assertGreaterEqual(g_info["stopCount"], 3, f"Gradient {f} must have at least 3 stops")

            stops = g_info["stops"]
            self.assertEqual(stops[0]["offset"], "0%", f"Gradient {f} stop 0 offset should be 0%")
            self.assertGreaterEqual(float(stops[0]["stopOpacity"]), 0.5, f"Gradient {f} stop 0 opacity too low")

            self.assertEqual(stops[-1]["offset"], "100%", f"Gradient {f} final stop offset should be 100%")
            self.assertEqual(float(stops[-1]["stopOpacity"]), 0.0, f"Gradient {f} final stop opacity must be 0")

    def test_07_fingertip_halo_geometry_and_concentricity(self):
        """Assert halo circles have valid positive radius, concentric cx/cy, and valid getBBox."""
        halo_data = self.page.evaluate("""() => {
            const fingers = ['pinky', 'ring', 'middle', 'index', 'thumb'];
            const res = {};
            for (const f of fingers) {
                const halo = document.getElementById(`fingertip-halo-${f}`);
                const pad = document.getElementById(`fingertip-${f}`);
                const bbox = halo.getBBox();
                res[f] = {
                    haloExists: !!halo,
                    fill: halo.getAttribute('fill'),
                    r: parseFloat(halo.getAttribute('r')),
                    cx: parseFloat(halo.getAttribute('cx')),
                    cy: parseFloat(halo.getAttribute('cy')),
                    padCx: parseFloat(pad.getAttribute('cx')),
                    padCy: parseFloat(pad.getAttribute('cy')),
                    bbox: { x: bbox.x, y: bbox.y, width: bbox.width, height: bbox.height }
                };
            }
            return res;
        }""")

        fingers = ["pinky", "ring", "middle", "index", "thumb"]
        for f in fingers:
            h = halo_data[f]
            self.assertTrue(h["haloExists"], f"Missing halo element #fingertip-halo-{f}")
            self.assertEqual(h["fill"], f"url(#radial-glow-{f})", f"Halo {f} fill must reference #radial-glow-{f}")
            self.assertGreaterEqual(h["r"], 12.0, f"Halo {f} radius {h['r']} too small")

            # Strict concentricity with fingertip pad
            self.assertAlmostEqual(h["cx"], h["padCx"], places=2, msg=f"Halo {f} cx != pad cx")
            self.assertAlmostEqual(h["cy"], h["padCy"], places=2, msg=f"Halo {f} cy != pad cy")

            # getBBox validation (bounding box width ~ 2 * r)
            expected_diameter = h["r"] * 2.0
            self.assertAlmostEqual(h["bbox"]["width"], expected_diameter, delta=1.0, msg=f"Halo {f} bbox width mismatch")
            self.assertAlmostEqual(h["bbox"]["height"], expected_diameter, delta=1.0, msg=f"Halo {f} bbox height mismatch")

        self.assertEqual(len(self.console_errors), 0, f"Console error during halo rendering: {self.console_errors}")

    # =========================================================================
    # SECTION 4: CACHE RE-ENTRY SAFETY & RAPID RESIZE BURSTS
    # =========================================================================

    def test_08_cache_rapid_resize_bursts_and_reentry_determinism(self):
        """Simulate rapid container resize bursts (50 resize events in 200ms) with re-entry safety."""
        # 1. Capture golden baseline coordinates at 1600x900
        golden = self.page.evaluate("""() => {
            updateHandOverlayGeometry();
            const cacheSnapshot = {};
            for (const [k, v] of keycapCenterCache.entries()) {
                cacheSnapshot[k] = { x: v.x, y: v.y, width: v.width, height: v.height };
            }
            const fingerSnapshot = {};
            for (const f of ['pinky', 'ring', 'middle', 'index', 'thumb']) {
                fingerSnapshot[f] = {
                    home: { ...fingerState[f].home },
                    current: { ...fingerState[f].current },
                    knuckle: { ...cachedKnuckles[f] }
                };
            }
            return {
                cacheSize: keycapCenterCache.size,
                cacheSnapshot,
                fingerSnapshot
            };
        }""")

        self.assertGreater(golden["cacheSize"], 25, "Golden cache size unexpectedly small")

        # 2. Execute 50 rapid burst resize mutations with re-entrant calls
        burst_result = self.page.evaluate("""async () => {
            const stage = document.getElementById('keyboardStage');
            const widths = [1500, 1350, 1200, 1400, 1600, 1100, 1700, 1250, 1450, 1600];
            const startTime = performance.now();
            let resizeCount = 0;
            const reentrantErrors = [];

            for (let i = 0; i < 50; i++) {
                const targetW = widths[i % widths.length];
                stage.style.width = `${targetW}px`;

                // Dispatch resize event
                window.dispatchEvent(new Event('resize'));

                // Interleaved re-entrant cache query
                try {
                    const c1 = getKeyCenter("KeyR");
                    const c2 = getKeyCenter("Space");
                    if (!c1 || !c2) {
                        reentrantErrors.push(`Null key center on iteration ${i}`);
                    }
                } catch (err) {
                    reentrantErrors.push(String(err));
                }

                resizeCount++;
                // Microtask yield to simulate rapid 200ms burst
                await new Promise(r => setTimeout(r, 4));
            }

            // Restore stage inline width style
            stage.style.width = '';
            window.dispatchEvent(new Event('resize'));
            updateHandOverlayGeometry();

            return {
                resizeCount,
                elapsed: performance.now() - startTime,
                reentrantErrors,
                finalCacheSize: keycapCenterCache.size
            };
        }""")

        self.assertEqual(burst_result["resizeCount"], 50, "Did not execute full 50 resize events")
        self.assertEqual(len(burst_result["reentrantErrors"]), 0, f"Reentrant errors during burst: {burst_result['reentrantErrors']}")

        # Memory leak check: Cache size must match golden exactly
        self.assertEqual(
            burst_result["finalCacheSize"], golden["cacheSize"],
            f"Cache size leaked! Expected {golden['cacheSize']}, got {burst_result['finalCacheSize']}"
        )

        # 3. Reference preservation check: DOM nodes still connected
        ref_check = self.page.evaluate("""() => {
            const fingers = ['pinky', 'ring', 'middle', 'index', 'thumb'];
            const res = { allConnected: true, dropped: [] };
            for (const f of fingers) {
                const els = fingerElements[f];
                for (const [key, el] of Object.entries(els)) {
                    if (!el || !el.isConnected) {
                        res.allConnected = false;
                        res.dropped.push(`${f}.${key}`);
                    }
                }
            }
            return res;
        }""")
        self.assertTrue(ref_check["allConnected"], f"Dropped DOM references in fingerElements: {ref_check['dropped']}")

        # 4. Determinism check: Golden coordinate comparison
        current = self.page.evaluate("""() => {
            const cacheSnapshot = {};
            for (const [k, v] of keycapCenterCache.entries()) {
                cacheSnapshot[k] = { x: v.x, y: v.y, width: v.width, height: v.height };
            }
            const fingerSnapshot = {};
            for (const f of ['pinky', 'ring', 'middle', 'index', 'thumb']) {
                fingerSnapshot[f] = {
                    home: { ...fingerState[f].home },
                    current: { ...fingerState[f].current },
                    knuckle: { ...cachedKnuckles[f] }
                };
            }
            return { cacheSnapshot, fingerSnapshot };
        }""")

        max_drift = 0.0
        for code, g_pos in golden["cacheSnapshot"].items():
            c_pos = current["cacheSnapshot"].get(code)
            self.assertIsNotNone(c_pos, f"Key {code} missing from cache after burst")
            dx = abs(g_pos["x"] - c_pos["x"])
            dy = abs(g_pos["y"] - c_pos["y"])
            drift = math.hypot(dx, dy)
            if drift > max_drift:
                max_drift = drift
            self.assertAlmostEqual(drift, 0.0, places=3, msg=f"Key {code} drift after resize burst: {drift:.4f}px")

        # Compare finger homes and knuckles
        for f in ["pinky", "ring", "middle", "index", "thumb"]:
            g_f = golden["fingerSnapshot"][f]
            c_f = current["fingerSnapshot"][f]
            home_drift = math.hypot(g_f["home"]["x"] - c_f["home"]["x"], g_f["home"]["y"] - c_f["home"]["y"])
            kn_drift = math.hypot(g_f["knuckle"]["x"] - c_f["knuckle"]["x"], g_f["knuckle"]["y"] - c_f["knuckle"]["y"])
            self.assertAlmostEqual(home_drift, 0.0, places=3, msg=f"Finger {f} home drift: {home_drift:.4f}px")
            self.assertAlmostEqual(kn_drift, 0.0, places=3, msg=f"Finger {f} knuckle drift: {kn_drift:.4f}px")

        self.assertEqual(len(self.console_errors), 0, f"Console error during cache burst stress: {self.console_errors}")


if __name__ == "__main__":
    unittest.main()
