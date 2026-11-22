# -*- coding: utf-8 -*-
"""Open docs/index.html in headless Chromium and check the slide anchors (issue #15).

  pip install playwright && python -m playwright install chromium
  python -m unittest tools/tests/test_viewer.py -v

Skipped when Playwright or its browser is not installed.
"""
import os, pathlib, unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAGE = (ROOT / 'docs' / 'index.html').as_uri()
try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None


@unittest.skipIf(sync_playwright is None, 'playwright not installed')
class Viewer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        try:
            cls.browser = cls.pw.chromium.launch()
        except Exception as e:  # browser not installed
            cls.pw.stop()
            raise unittest.SkipTest(f'chromium not available: {e}')

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop()

    def open(self, hash_):
        pg = self.browser.new_page()
        errors = []
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(PAGE + hash_)
        return pg, errors

    def pos(self, hash_):
        pg, errors = self.open(hash_)
        try:
            self.assertEqual(errors, [], hash_)
            return pg.inner_text('#pos')
        finally:
            pg.close()

    def test_anchors(self):
        self.assertEqual(self.pos('#p04-carry-or-query'), '49 / 159')
        self.assertEqual(self.pos('#s49'), '49 / 159')  # old number links keep working
        self.assertEqual(self.pos('#p12-summary'), '159 / 159')
        self.assertEqual(self.pos(''), '1 / 159')

    def test_bad_hashes_fall_back_with_a_note(self):
        for h in ['#%E0', '#p99-nope', '#s999']:
            p = self.pos(h)
            self.assertTrue(p.startswith('1 / 159'), (h, p))
            self.assertIn('見つかりません', p, h)

    def test_navigation_updates_hash(self):
        pg, errors = self.open('#p00-title')
        pg.click('#mode'); pg.click('#next')
        self.assertEqual(pg.evaluate('location.hash'), '#p00-goals-and-how-to-read')
        pg.evaluate("location.hash='#p06-narrow-downstream'"); pg.wait_for_timeout(200)
        self.assertEqual(pg.inner_text('#pos'), '84 / 159')
        self.assertEqual(errors, [])
        pg.close()


if __name__ == '__main__':
    unittest.main()
