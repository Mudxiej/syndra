"""
SYNDRA Test Helpers & Utilities
Shared fixtures, geometry math, and assertion helpers for Playwright E2E tests.
"""

import re
from typing import Dict, Tuple, Optional, Any

HTML_URL = "file:///C:/Users/mudxiej/Documents/GitHub/syndra/index.html"

# Biomechanical finger configuration & signature colors
FINGER_CONFIG = {
    "pinky": {
        "name": "Pinky",
        "home_key": "KeyZ",
        "hex_color": "#f59e0b",
        "rgb": (245, 158, 11),
    },
    "ring": {
        "name": "Ring",
        "home_key": "KeyD",
        "hex_color": "#3b82f6",
        "rgb": (59, 130, 246),
    },
    "middle": {
        "name": "Middle",
        "home_key": "KeyR",
        "hex_color": "#10b981",
        "rgb": (16, 185, 129),
    },
    "index": {
        "name": "Index",
        "home_key": "KeyT",
        "hex_color": "#ff4655",
        "rgb": (255, 70, 85),
        "alt_hex": "#ef4444",
        "alt_rgb": (239, 68, 68),
    },
    "thumb": {
        "name": "Thumb",
        "home_key": "KeyM",
        "hex_color": "#8b5cf6",
        "rgb": (139, 92, 246),
    },
}


def parse_color_to_rgb(color_str: str) -> Optional[Tuple[int, int, int]]:
    """Parse hex or rgb/rgba string into (r, g, b) tuple."""
    if not color_str:
        return None
    s = color_str.strip().lower()
    hex_match = re.match(r"^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})", s)
    if hex_match:
        return (
            int(hex_match.group(1), 16),
            int(hex_match.group(2), 16),
            int(hex_match.group(3), 16),
        )
    rgb_match = re.match(r"^rgba?\((\d+),\s*(\d+),\s*(\d+)", s)
    if rgb_match:
        return (
            int(rgb_match.group(1)),
            int(rgb_match.group(2)),
            int(rgb_match.group(3)),
        )
    return None


def colors_match(actual: str, expected_hex: str, tolerance: int = 15) -> bool:
    """Check if actual color string matches expected hex within tolerance."""
    act_rgb = parse_color_to_rgb(actual)
    exp_rgb = parse_color_to_rgb(expected_hex)
    if not act_rgb or not exp_rgb:
        # Fallback to substring matching if format is complex
        return expected_hex.lower() in actual.lower()
    return all(abs(a - e) <= tolerance for a, e in zip(act_rgb, exp_rgb))


def get_bbox(page: Any, selector: str, timeout: int = 500) -> Dict[str, float]:
    """
    Safely get bounding box for selector with short fail-fast timeout.
    Raises AssertionError if element does not exist or has no bounding box.
    """
    locator = page.locator(selector)
    try:
        count = locator.count()
        if count == 0:
            raise AssertionError(f"Required element '{selector}' not found in DOM.")
        box = locator.bounding_box(timeout=timeout)
        if not box:
            raise AssertionError(f"Element '{selector}' is not visible or has zero size.")
        return box
    except Exception as e:
        if isinstance(e, AssertionError):
            raise
        raise AssertionError(f"Failed to obtain bounding box for '{selector}': {e}")


def get_center(bbox: Dict[str, float]) -> Tuple[float, float]:
    """Calculate (cx, cy) from bounding box dict."""
    return (bbox["x"] + bbox["width"] / 2.0, bbox["y"] + bbox["height"] / 2.0)


def assert_inside_bbox(test_case: Any, point: Tuple[float, float], bbox: Dict[str, float], label: str = ""):
    """Assert point (px, py) is strictly inside bbox."""
    px, py = point
    x_min = bbox["x"]
    x_max = bbox["x"] + bbox["width"]
    y_min = bbox["y"]
    y_max = bbox["y"] + bbox["height"]
    inside = (x_min <= px <= x_max) and (y_min <= py <= y_max)
    test_case.assertTrue(
        inside,
        f"Point ({px:.1f}, {py:.1f}) is outside bbox [x: {x_min:.1f}..{x_max:.1f}, y: {y_min:.1f}..{y_max:.1f}] for {label}",
    )


def reset_page_state(page: Any):
    """Release all pressed keys and reset DOM state for test isolation."""
    page.evaluate("""() => {
        document.querySelectorAll('.key-cap.is-pressed').forEach(el => {
            el.classList.remove('is-pressed');
        });
        if (typeof deactivateKey === 'function') {
            const testKeys = ['KeyR', 'KeyT', 'KeyW', 'KeyZ', 'Space', 'KeyF', 'KeyG', 'KeyD', 'KeyX', 'KeyC', 'KeyV', 'KeyB', 'KeyN', 'KeyM', 'Digit4', 'Digit5', 'Digit6', 'Comma', 'Escape', 'ControlLeft', 'MetaLeft', 'AltLeft', 'ShiftLeft', 'Period'];
            testKeys.forEach(k => {
                try { deactivateKey(k); } catch(e){}
            });
        }
        if (window.fingerState) {
            for (const f of ['pinky', 'ring', 'middle', 'index', 'thumb']) {
                const s = window.fingerState[f];
                if (s) {
                    s.activeKeys.clear();
                    s.current = { ...s.home };
                    s.target = { ...s.home };
                    s.isAnimating = false;
                }
            }
        }
    }""")
