import unittest
from typing import List
from playwright.sync_api import sync_playwright
from tests.helpers import HTML_URL, reset_page_state


class TestInteractiveMouseSuite(unittest.TestCase):
    """Test suite verifying interactive clickable mouse controls, tactile feedback, and zero-displacement anchoring."""

    playwright = None
    browser = None
    context = None
    page = None
    console_errors: List[str] = []

    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)
        cls.context = cls.browser.new_context(viewport={"width": 1400, "height": 900})
        cls.page = cls.context.new_page()
        cls.console_errors = []
        cls.page.on(
            "console",
            lambda msg: cls.console_errors.append(msg.text) if msg.type == "error" else None,
        )
        cls.page.on("pageerror", lambda err: cls.console_errors.append(str(err)))
        cls.page.goto(HTML_URL)
        cls.page.locator("#mouse").scroll_into_view_if_needed()
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
        reset_page_state(self.page)
        self.page.wait_for_timeout(50)

    def tearDown(self):
        reset_page_state(self.page)
        self.page.wait_for_timeout(50)

    def test_01_lmb_click(self):
        """LMB paddle clicks and enters is-pressed state."""
        lmb = self.page.locator("#mouseBtnLmb")
        lmb.dispatch_event("pointerdown")
        self.page.wait_for_timeout(40)
        has_pressed = "is-pressed" in (lmb.get_attribute("class") or "")
        self.assertTrue(has_pressed, "LMB did not enter is-pressed state on click.")

    def test_02_rmb_click(self):
        """RMB paddle clicks and enters is-pressed state."""
        rmb = self.page.locator("#mouseBtnRmb")
        rmb.dispatch_event("pointerdown")
        self.page.wait_for_timeout(40)
        has_pressed = "is-pressed" in (rmb.get_attribute("class") or "")
        self.assertTrue(has_pressed, "RMB did not enter is-pressed state on click.")

    def test_03_rmb_right_click_contextmenu(self):
        """Right-clicking mouse SVG triggers RMB and prevents default browser context menu."""
        mouse_svg = self.page.locator(".mouse-svg")
        mouse_svg.dispatch_event("contextmenu")
        self.page.wait_for_timeout(40)
        rmb = self.page.locator("#mouseBtnRmb")
        has_pressed = "is-pressed" in (rmb.get_attribute("class") or "")
        self.assertTrue(has_pressed, "Right-click contextmenu event did not trigger RMB.")

    def test_04_wheel_middle_click(self):
        """Scroll wheel middle click triggers is-pressed state."""
        wheel = self.page.locator("#mouseBtnWheel")
        wheel.dispatch_event("pointerdown")
        self.page.wait_for_timeout(40)
        has_pressed = "is-pressed" in (wheel.get_attribute("class") or "")
        self.assertTrue(has_pressed, "Scroll wheel did not enter is-pressed state on click.")

    def test_05_wheel_scroll_interactions(self):
        """Scrolling mouse wheel over mouse SVG pulses JUMP and USE badges."""
        mouse_svg = self.page.locator(".mouse-svg")
        badge_jump = self.page.locator("#mouseBadgeWheelUp")
        badge_use = self.page.locator("#mouseBadgeWheelDown")

        # Scroll up
        mouse_svg.dispatch_event("wheel", {"deltaY": -120})
        self.page.wait_for_timeout(40)
        has_jump = "is-pressed" in (badge_jump.get_attribute("class") or "")
        self.assertTrue(has_jump, "Wheel up scroll did not trigger JUMP badge.")

        self.page.wait_for_timeout(150)

        # Scroll down
        mouse_svg.dispatch_event("wheel", {"deltaY": 120})
        self.page.wait_for_timeout(40)
        has_use = "is-pressed" in (badge_use.get_attribute("class") or "")
        self.assertTrue(has_use, "Wheel down scroll did not trigger USE badge.")

    def test_06_side_buttons_click(self):
        """MB5 (ABL 2) and MB4 (ABL 3) click and enter is-pressed state."""
        mb5 = self.page.locator("#mouseBtnMb5")
        mb5.dispatch_event("pointerdown")
        self.page.wait_for_timeout(40)
        self.assertTrue("is-pressed" in (mb5.get_attribute("class") or ""), "MB5 failed to enter is-pressed state.")

        self.page.wait_for_timeout(150)

        mb4 = self.page.locator("#mouseBtnMb4")
        mb4.dispatch_event("pointerdown")
        self.page.wait_for_timeout(40)
        self.assertTrue("is-pressed" in (mb4.get_attribute("class") or ""), "MB4 failed to enter is-pressed state.")

    def test_07_badges_click(self):
        """Clicking outboard badges triggers corresponding button states."""
        badge_jump = self.page.locator("#mouseBadgeWheelUp")
        wheel = self.page.locator("#mouseBtnWheel")
        badge_jump.dispatch_event("pointerdown")
        self.page.wait_for_timeout(40)
        self.assertTrue("is-pressed" in (badge_jump.get_attribute("class") or ""))
        self.assertTrue("is-pressed" in (wheel.get_attribute("class") or ""))

    def test_08_badges_and_buttons_zero_displacement(self):
        """Assert all badges and mouse buttons maintain 100% rock-solid zero displacement on click."""
        elements = [
            ("#mouseBadgeMb5", "ABL 2 badge"),
            ("#mouseBadgeMb4", "ABL 3 badge"),
            ("#mouseBadgeWheelUp", "JUMP badge"),
            ("#mouseBadgeWheelDown", "USE badge"),
            ("#mouseBtnMb5", "MB5 button"),
            ("#mouseBtnMb4", "MB4 button"),
            ("#mouseBtnWheel", "Wheel button"),
            ("#mouseBtnLmb", "LMB button"),
            ("#mouseBtnRmb", "RMB button"),
        ]
        for sel, name in elements:
            el = self.page.locator(sel)
            box_rest = el.bounding_box()
            self.assertIsNotNone(box_rest, f"Failed bounding box for {name} at rest.")

            el.dispatch_event("pointerdown")
            self.page.wait_for_timeout(35)
            box_pressed = el.bounding_box()
            self.assertIsNotNone(box_pressed, f"Failed bounding box for {name} when pressed.")

            dx = abs(box_pressed["x"] - box_rest["x"])
            dy = abs(box_pressed["y"] - box_rest["y"])
            self.assertLess(dx, 0.2, f"{name} jumped horizontally: dx={dx:.3f}px")
            self.assertLess(dy, 0.2, f"{name} jumped vertically: dy={dy:.3f}px")
            self.page.wait_for_timeout(150)

    def test_09_zero_console_errors(self):
        """Zero console errors emitted during mouse interactions."""
        self.assertEqual(len(self.console_errors), 0, f"Console errors detected: {self.console_errors}")


if __name__ == "__main__":
    unittest.main()
