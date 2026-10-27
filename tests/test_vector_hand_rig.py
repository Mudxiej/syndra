"""Behavior checks for the rendered SVG hand, not just hidden fingertip markers."""
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

class VectorHandRigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw=sync_playwright().start()
        cls.browser=cls.pw.chromium.launch(channel='chrome',headless=True)
        cls.page=cls.browser.new_page(viewport={'width':1600,'height':1400})
    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.pw.stop()
    def setUp(self):
        self.page.goto((Path(__file__).resolve().parents[1]/'index.html').as_uri())
        self.page.wait_for_function("document.getElementById('hand-surface').getAttribute('d')?.length > 1000")
    def activate(self,key):
        self.page.evaluate('(k)=>activateKey(k)',key);self.page.wait_for_timeout(250)
    def release(self,key):
        self.page.evaluate('(k)=>deactivateKey(k)',key);self.page.wait_for_timeout(250)
    def test_visible_hand_is_vector_geometry_without_raster(self):
        self.assertEqual(self.page.locator('#handOverlay image').count(),0)
        self.assertEqual(self.page.locator('#hand-surface').evaluate('(e)=>e.tagName'),'path')
        self.assertGreaterEqual(self.page.locator('#hand-surface').get_attribute('d').count('M'),2)
    def test_thumb_changes_actual_outline_and_returns_exactly(self):
        baseline=self.page.locator('#hand-surface').get_attribute('d')
        self.activate('Space')
        self.assertNotEqual(baseline,self.page.locator('#hand-surface').get_attribute('d'))
        self.release('Space')
        self.assertEqual(baseline,self.page.locator('#hand-surface').get_attribute('d'))
    def test_joint_lengths_are_preserved_on_reach(self):
        for key in ['KeyW','KeyH','Digit4','Space']:
            self.activate(key)
            error=self.page.evaluate('''()=>Math.max(...Object.entries(vectorHandRig.poses).flatMap(([f,p])=>p.joints.slice(1).map((q,i)=>{const r=vectorHandRig.restChains[f];return Math.abs(Math.hypot(q[0]-p.joints[i][0],q[1]-p.joints[i][1])-Math.hypot(r[i+1][0]-r[i][0],r[i+1][1]-r[i][1]))})))''')
            self.assertLess(error,0.1,key)
            self.release(key)
    def test_chords_release_each_finger_independently(self):
        self.activate('Space');self.activate('KeyH');self.release('Space')
        movement=self.page.evaluate('Object.fromEntries(Object.entries(vectorHandRig.poses).map(([f,p])=>[f,p.movement]))')
        self.assertLess(movement['thumb'],0.01)
        self.assertGreater(movement['index'],50)
        self.release('KeyH')
    def test_resize_keeps_geometry_valid_and_clicks_pass_through(self):
        for width in [1024,1600,2560]:
            self.page.set_viewport_size({'width':width,'height':1400})
            self.page.locator('#keyboardStage').scroll_into_view_if_needed()
            self.page.wait_for_timeout(100)
            d=self.page.locator('#hand-surface').get_attribute('d')
            self.assertNotIn('NaN',d);self.assertNotIn('Infinity',d)
            key=self.page.evaluate('''()=>{const r=document.querySelector('[data-key="KeyR"]').getBoundingClientRect();return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest('[data-key]')?.dataset.key}''')
            self.assertEqual(key,'KeyR')
