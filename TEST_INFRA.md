# TEST_INFRA: SYNDRA Ergonomic Hand Overlay Automated Verification

## 1. Overview & Architecture

This document defines the automated end-to-end (E2E) testing infrastructure for the SYNDRA ergonomic left-hand overlay superimposed over the Chapter 5 virtual keyboard in `index.html`.

The test suite exercises opaque-box browser interactions using the official Playwright sync API and Python standard library `unittest`.

### 1.1 Technical Stack
- **Language & Runtime**: Python 3.14.0 (`C:\Users\mudxiej\AppData\Local\Programs\Python\Python314\python.exe`)
- **E2E Automation Framework**: Playwright 1.63.0 (`playwright.sync_api`)
- **Browser Channel**: System Google Chrome 156.0.8078.48 (`channel="chrome"`, `headless=True`)
- **Host Application**: Direct file protocol (`file:///C:/Users/mudxiej/Documents/GitHub/syndra/index.html`)
- **Dependencies**: Zero external server, bundler, or Node dependencies required.

---

## 2. 4-Tier Test Suite Structure

The verification suite in `tests/test_e2e_hand_overlay.py` implements 72 automated test cases structured across 4 distinct tiers:

```
tests/
├── __init__.py
├── helpers.py                  # Geometry math, RGB parsers, bounding box assertions
└── test_e2e_hand_overlay.py    # 4-Tier Playwright verification suite
```

### 2.1 Tier 1: Feature Coverage (50 Tests, >= 5 per Feature)
Covers all 10 core features defined in `PROJECT.md`:

| Feature # | Feature Name | Test Methods | Scope & Contract |
|---|---|---|---|
| Feature 1 | Hand Silhouette & Layering | `test_f01_01` to `test_f01_05` | SVG `#handOverlay`, `pointer-events: none`, absolute inset, z-index >= 10, dimensions |
| Feature 2 | Palm Desk Anchor | `test_f02_01` to `test_f02_05` | `#palmRestBar` below Spacebar, width span >= 40%, spline root anchoring, class naming |
| Feature 3 | Baseline Home Rest Posture | `test_f03_01` to `test_f03_05` | Pinky on Z, Ring on D, Middle on R, Index on T, Thumb on Space (left cluster <= 55%) |
| Feature 4 | Visual Clarity & Legibility | `test_f04_01` to `test_f04_05` | Keycap text `.key-id`, `.key-action` visible, hand opacity <= 0.85, gradient preservation |
| Feature 5 | Fingertip Glow Accents | `test_f05_01` to `test_f05_05` | Amber (Pinky #f59e0b), Blue (Ring #3b82f6), Green (Middle #10b981), Red (Index #ff4655/#ef4444), Violet (Thumb #8b5cf6) |
| Feature 6 | Dynamic Reach Kinematics | `test_f06_01` to `test_f06_05` | Keydown reaches target center within 100-150ms window, adds `.is-pressed` |
| Feature 7 | Dynamic Return Kinematics | `test_f07_01` to `test_f07_05` | Keyup returns fingertip to home key within 150-180ms window, clears `.is-pressed` |
| Feature 8 | Multi-Finger Articulation | `test_f08_01` to `test_f08_05` | Simultaneous keypresses (R+T, Z+Space, W+Space), staggered releases, per-finger state sets |
| Feature 9 | Zero Layout Thrashing Cache | `test_f09_01` to `test_f09_05` | `window.getKeyCenter`, ResizeObserver cache updates, no forced reflows during rAF |
| Feature 10 | 60 FPS & Viewport Stability | `test_f10_01` to `test_f10_05` | rAF >= 58 FPS, 0 dropped frames, idle rAF sleep, 0 long tasks > 50ms, 0 console errors |

### 2.2 Tier 2: Boundary & Corner Cases (9 Tests)
- Rapid 20ms key tap and immediate release prior to reach completion.
- Simultaneous release of 3 keys returning all articulated fingers cleanly.
- `e.repeat == true` events safely discarded without animation stutter or restart.
- Extreme viewports (1024px laptop vs 1400px desktop) alignment verification.
- Multi-row cross-keyboard reach: Pinky to Escape (row 1) and Index to Digit6 (row 2).
- Virtual mouse click activation equivalence on `.key-cap`.
- Unmapped keypress event (`Digit9`) handling without DOM faults or JS exceptions.

### 2.3 Tier 3: Cross-Feature Combinations (7 Tests)
- Pairwise simultaneous keys: R + T (movement + strafe), Z + Space (walk + crouch), W + Space (interact + crouch), D + T (voice PTT + strafe).
- Tri-finger chord: R + T + Space articulated simultaneously across middle, index, and thumb.
- Interrupted reach: Key released at 50ms (mid-flight) smoothly reverses kinematic spline without coordinate discontinuity.
- Dynamic viewport resize during active keypress hold adapts fingertip target immediately.

### 2.4 Tier 4: Real-World Workloads (6 Tests)
- Gaming Counter-Strafing Workload: Tactical shooter movement (R forward -> T strafe left -> G strafe right -> Space crouch).
- Weapon Swap Burst Macro: Rapid sequential switches (W -> N Vandal -> M Pistol -> B Knife).
- Tactical Spike Plant Sequence: Coordinated multi-key hold (Walk Z -> Crouch Space -> Plant Period).
- Sustained Rapid Typing Burst: 10-key rapid input sequence across multiple rows.
- Rapid Alternate Finger Trill: 20 alternating high-speed taps between Middle (R) and Index (T).
- Full-Round Gameplay Lifecycle Stress: 3-second continuous randomized combination input stream testing memory and frame stability.

---

## 3. Interface Contracts & DOM Selectors

The test suite verifies against the following interface contract:

### 3.1 Overlay & DOM Selectors
- `#handOverlay`: Root `<svg class="hand-overlay-svg" id="handOverlay">`
- `#palmRestBar`: Wrist anchor bar mounted below Spacebar `<div class="palm-rest-bar" id="palmRestBar">`
- `#fingertip-pinky`: SVG fingertip pad circle (data-finger="pinky")
- `#fingertip-ring`: SVG fingertip pad circle (data-finger="ring")
- `#fingertip-middle`: SVG fingertip pad circle (data-finger="middle")
- `#fingertip-index`: SVG fingertip pad circle (data-finger="index")
- `#fingertip-thumb`: SVG fingertip pad circle (data-finger="thumb")
- Splines: `#finger-spline-pinky`, `#finger-spline-ring`, `#finger-spline-middle`, `#finger-spline-index`, `#finger-spline-thumb`
- Target Keycaps: `.key-cap[data-key="<KeyCode>"]`

### 3.2 Coordinate Cache API
- `window.getKeyCenter(keyCode)`: Returns `{ x: number, y: number, width: number, height: number }` relative to `#keyboardContainer`.
- `window._handRafActive`: Boolean flag exposing rAF sleep status at steady state.

---

## 4. Test Execution & Verification

### 4.1 Invocation Command
```powershell
& 'C:\Users\mudxiej\AppData\Local\Programs\Python\Python314\python.exe' -m unittest discover -s tests -p 'test_*.py' -v
```

### 4.2 Empirical Baseline Results (72 Tests)
- **Total Test Count**: 72 test cases across 5 test classes.
- **Execution Time**: 25.16 seconds on host (Python 3.14 + Chromium system Chrome).
- **Milestone 1 Features (T1A Features 1-5)**: 25 / 25 Passing (100% PASS).
- **Milestone 2 Features (T1B Features 6-10)**: 20 / 25 Passing (5 failures on pending non-home reach kinematics).
- **Tier 2 Boundary Cases**: 7 / 9 Passing (2 failures on pending multi-row reach to Escape and Digit6).
- **Tier 3 Cross-Feature**: 6 / 7 Passing (1 failure on pending Ring reach to KeyW).
- **Tier 4 Real-World Workloads**: 6 / 6 Passing (100% PASS).
- **Current Summary**: 64 PASS / 8 FAIL / 0 ERRORS.
- **Target for Milestone 3**: 72 / 72 PASS (100% exit code 0).
