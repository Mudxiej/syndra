# Project: SYNDRA Ergonomic Left-Hand Overlay

## Architecture
- **Host Application**: Single-page static application in `index.html`.
- **Chapter 5 Virtual Keyboard**: `#keyboardContainer` within `#ch5` (`.visualizer-inner`), styled via container query units (`cqw`).
- **Overlay Layer**: Absolute SVG stage `#handOverlay` positioned directly over the keyboard with `pointer-events: none`.
- **Palm Anchor Bar**: Ergonomic desk wrist rest positioned below Spacebar row providing visual anchor for carpal root.
- **Skeletal Kinematic Model**: Procedural cubic Bezier splines connecting palm MCP joints to PIP, DIP, and fingertip circle pads.
- **Dynamic Coordinate Cache**: Screen-space keycap centers cached relative to `#keyboardContainer` on load and window/container resize (`ResizeObserver`), eliminating DOM reads during animation loops.
- **Input Pipeline**: Refactored `activateKey` and `deactivateKey` with per-finger active key sets and `e.repeat` guards, supporting physical keyboard events and virtual key mouse clicks.
- **Render Engine**: Lightweight `requestAnimationFrame` loop active only during transitions (100-150ms reach, 150-180ms return) and sleeping at steady state for 60 FPS performance.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Hand Silhouette & Layering | Stylized semi-transparent left hand silhouette overlaid on keyboard stage | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Palm Desk Anchor | Natural carpal/wrist anchor bar positioned at bottom desk edge below Spacebar | M1 | ORIGINAL_REQUEST §R1 |
| 3 | Baseline Home Rest Posture | Fingertips resting on baseline home keys: Pinky (Z), Ring (D), Middle (R), Index (T), Thumb (Space) | M1 | ORIGINAL_REQUEST §R1 |
| 4 | Visual Clarity & Legibility | Keycap labels, action names, and colors sharp and readable through the hand layer | M1 | ORIGINAL_REQUEST §R3 |
| 5 | Fingertip Glow Accents | Soft signature color glowing pads: Amber (Pinky), Blue (Ring), Green (Middle), Red (Index), Violet (Thumb) | M1 | ORIGINAL_REQUEST §R3 |
| 6 | Dynamic Reach Kinematics | Smooth 100-150ms animated reach from home posture to center of target keycap on keydown/click | M2 | ORIGINAL_REQUEST §R2 |
| 7 | Dynamic Return Kinematics | Smooth 150-180ms animated return from target keycap back to home posture on key release | M2 | ORIGINAL_REQUEST §R2 |
| 8 | Multi-Finger Articulation | Independent concurrent articulation for simultaneous keypresses (e.g., R + T, Z + Space) without state reset | M2 | ORIGINAL_REQUEST §R2 |
| 9 | Zero Layout Thrashing Cache | Coordinate lookup cache refreshed via ResizeObserver avoiding getBoundingClientRect in rAF | M2 | ORIGINAL_REQUEST §R4 |
| 10 | 60 FPS & Multi-Viewport Stability | 60+ FPS animation with idle sleep, 0 console errors, stable across 1400px and 1024px displays | M2 | ORIGINAL_REQUEST §R4 |
| 11 | Comprehensive E2E Verification | 100% pass on 4-tier Playwright automated test suite + Tier 5 adversarial hardening | M3 | ORIGINAL_REQUEST §Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Overlay Structure & Rest Geometry | SVG overlay stage, palm bar anchor, skeletal spline paths, baseline rest posture over Z/D/R/T/Space, fingertip glow pads, legibility styling | none | DONE |
| 2 | Kinematics Engine & Event Integration | Coordinate caching, ResizeObserver, per-finger state tracking, e.repeat guards, 100-150ms cubic Bezier reach/return, multi-key articulation, 60 FPS rAF loop | M1 | DONE |
| 3 | Final Milestone: 100% E2E Pass & Hardening | Phase 1: Pass 100% of E2E test suite (Tiers 1-4). Phase 2: Tier 5 white-box adversarial coverage hardening. | M2, TEST_READY | DONE |

## Interface Contracts

### DOM Selectors & Markup Contract
- Root Overlay: `<svg class="hand-overlay-svg" id="handOverlay" ...>` with CSS `pointer-events: none; position: absolute; inset: 0; width: 100%; height: 100%; z-index: 10;`.
- Desk Palm Bar: `<div class="palm-rest-bar" id="palmRestBar">` mounted below row 5.
- Fingertip Element IDs:
  - Pinky: `#fingertip-pinky` (data-finger="pinky")
  - Ring: `#fingertip-ring` (data-finger="ring")
  - Middle: `#fingertip-middle` (data-finger="middle")
  - Index: `#fingertip-index` (data-finger="index")
  - Thumb: `#fingertip-thumb` (data-finger="thumb")
- Finger Spline Paths:
  - `#finger-spline-pinky`
  - `#finger-spline-ring`
  - `#finger-spline-middle`
  - `#finger-spline-index`
  - `#finger-spline-thumb`

### Kinematics API & State Contract
- Key Center Lookup: `getKeyCenter(keyCode)` returns `{ x: number, y: number, width: number, height: number }` relative to `#keyboardContainer`.
- Finger State Object:
  ```javascript
  const fingerState = {
    pinky:  { current: {x, y}, target: {x, y}, home: {x, y}, activeKeys: Set, color: "#f59e0b" },
    ring:   { current: {x, y}, target: {x, y}, home: {x, y}, activeKeys: Set, color: "#3b82f6" },
    middle: { current: {x, y}, target: {x, y}, home: {x, y}, activeKeys: Set, color: "#10b981" },
    index:  { current: {x, y}, target: {x, y}, home: {x, y}, activeKeys: Set, color: "#ff4655" },
    thumb:  { current: {x, y}, target: {x, y}, home: {x, y}, activeKeys: Set, color: "#8b5cf6" }
  };
  ```
- Reach Timing: 100ms - 150ms cubic Bezier transition.
- Return Timing: 150ms - 180ms cubic Bezier transition.

### E2E Test Contract
- Runner command: `& 'C:\Users\mudxiej\AppData\Local\Programs\Python\Python314\python.exe' -m unittest discover -s tests -p 'test_*.py'`
- Pass condition: All tests exit code 0.

## Code Layout
- Target application file: `index.html` (all HTML, CSS, and JS components).
- Test directory: `tests/`
  - `tests/test_e2e_hand_overlay.py`: Main Playwright test suite.
  - `tests/helpers.py`: Common test setup, coordinate extraction, and assertions.
- Agent artifacts and handoffs: `.agents/teamwork/`
