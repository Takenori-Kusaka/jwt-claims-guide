# -*- coding: utf-8 -*-
"""The claim detail screen of the design editor (docs/claims/, #67): six fields on top, the other columns in tabs.

  python -m pytest -q tools/tests/test_claims_detail_ui.py
  CLAIMS_EDITOR_REDESIGN=research/claims-editor/ux-redesign python -m pytest -q tools/tests/test_claims_detail_ui.py
      # also save the screenshots (1280 and 900 wide)

The first class needs no browser: every column of templates/registry/claims.schema.json ($defs.claim) is in exactly one
tab of meta.claim_tabs (tools/build_claims_viewer.py CLAIM_TABS). The second opens the editor in headless Chromium
(skipped when Playwright or its browser is not installed): a row that fills every column of the schema shows every
column in a tab that can be selected; the columns not filled in are folded; the tabs work with the keyboard and the
selected one is kept in the URL; ClaimsPreview.focusColumn lands on the column.
"""
import functools
import http.server
import json
import os
import socketserver
import sys
import threading
import time
import unittest

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS = os.path.join(ROOT, 'docs')
SHOTS = os.environ.get('CLAIMS_EDITOR_REDESIGN')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import build_claims_viewer  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

TAB_LABELS = ['概要', '値と型', '発行と元データ', '有効期間と更新', '保護', '使う側', '経緯', 'そのほか']
HEAD_LABELS = ['名前', '意味', '型', '発行元', '入るトークン', '状態']


def claim_schema():
    with open(os.path.join(ROOT, 'templates', 'registry', 'claims.schema.json'), encoding='utf-8') as f:
        return json.load(f)


def sample_value(schema, node, depth=0):
    """A value for a schema node that the editor can show (not necessarily valid: the screen must show anything)."""
    if '$ref' in node:
        target = schema
        for part in node['$ref'].lstrip('#/').split('/'):
            target = target[part]
        return sample_value(schema, target, depth + 1)
    if 'const' in node:
        return node['const']
    if 'enum' in node:
        return next((x for x in node['enum'] if x is not None), node['enum'][0])
    for k in ('anyOf', 'oneOf'):
        if k in node:
            return sample_value(schema, next((x for x in node[k] if x.get('type') != 'null'), node[k][0]), depth + 1)
    t = node.get('type')
    if isinstance(t, list):
        t = next((x for x in t if x != 'null'), t[0])
    if t == 'array':
        return [sample_value(schema, node.get('items', {'type': 'string'}), depth + 1)]
    if t == 'object' or 'properties' in node:
        if depth > 4:
            return {}
        return {k: sample_value(schema, v, depth + 1) for k, v in node.get('properties', {}).items()} or {'key': 'value'}
    if t == 'integer' or t == 'number':
        return max(1, node.get('minimum', 1))
    if t == 'boolean':
        return True
    return 'text'


def full_row():
    schema = claim_schema()
    props = schema['$defs']['claim']['properties']
    row = {k: sample_value(schema, v) for k, v in props.items()}
    row.update({'id': 'C-all', 'name': 'all_columns', 'decision': '採用'})
    return row, list(props)


class ClaimTabsData(unittest.TestCase):
    def test_every_schema_column_is_in_exactly_one_tab(self):
        props = list(claim_schema()['$defs']['claim']['properties'])
        tabs = build_claims_viewer.claim_tabs()
        self.assertEqual([t['label'] for t in tabs], TAB_LABELS)
        where = {}
        for t in tabs:
            for c in t['columns']:
                where.setdefault(c, []).append(t['id'])
        self.assertEqual([p for p in props if p not in where], [])
        self.assertEqual({c: w for c, w in where.items() if len(w) != 1}, {})
        self.assertEqual([c for c in where if c not in props], [])
        self.assertEqual([label for label, _ in build_claims_viewer.CLAIM_HEAD], HEAD_LABELS)

    def test_a_new_schema_column_goes_to_the_last_tab_and_an_unknown_name_stops_the_build(self):
        props = list(claim_schema()['$defs']['claim']['properties']) + ['brand_new_column']
        self.assertIn('brand_new_column', build_claims_viewer.claim_tabs(props)[-1]['columns'])
        with self.assertRaises(SystemExit):
            build_claims_viewer.claim_tabs(props, [('overview', '概要', ['no_such_column']), ('other', 'そのほか', [])])
        with self.assertRaises(SystemExit):
            build_claims_viewer.claim_tabs(props, [('overview', '概要', ['id']), ('value', '値と型', ['id']), ('other', 'そのほか', [])])

    def test_the_built_meta_has_the_tabs(self):
        with open(os.path.join(DOCS, 'claims', 'data', 'meta.js'), encoding='utf-8') as f:
            text = f.read()
        meta = json.loads(text[text.index('window.CLAIMS_VIEWER_DATA["meta"] = ') + len('window.CLAIMS_VIEWER_DATA["meta"] = '):].rstrip().rstrip(';'))
        self.assertEqual(meta['claim_tabs'], build_claims_viewer.claim_tabs())


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@unittest.skipIf(sync_playwright is None, 'playwright not installed')
class ClaimDetail(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(_Quiet, directory=DOCS))
        cls.srv.daemon_threads = True
        cls.base = f'http://127.0.0.1:{cls.srv.server_address[1]}/claims/'
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        try:
            cls.browser = cls.pw.chromium.launch()
        except Exception as e:  # browser not installed
            cls.pw.stop()
            cls.srv.shutdown()
            raise unittest.SkipTest(f'chromium not available: {e}')
        if SHOTS:
            os.makedirs(os.path.join(ROOT, SHOTS), exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.srv.shutdown()

    def open(self, width=1280, height=900):
        ctx = self.browser.new_context(viewport={'width': width, 'height': height})
        pg = ctx.new_page()
        pg.problems, pg.requests = [], []
        pg.on('pageerror', lambda e: pg.problems.append('pageerror: ' + str(e)))
        pg.on('console', lambda m: pg.problems.append(f'console {m.type}: {m.text}') if m.type in ('error', 'warning') else None)
        ctx.on('request', lambda r: pg.requests.append({'method': r.method, 'url': r.url}))
        pg.goto(self.base)
        pg.wait_for_selector('#btn-sample-a')
        self.addCleanup(ctx.close)
        return pg

    def poll(self, pg, js, timeout=30, arg=None):
        end = time.time() + timeout
        while time.time() < end:
            v = pg.evaluate(js, arg) if arg is not None else pg.evaluate(js)
            if v:
                return v
            time.sleep(0.1)
        self.fail(f'timed out waiting for {js}')

    def go(self, pg, hash_, h1):
        pg.evaluate('h => { location.hash = h; }', hash_)
        self.poll(pg, 't => ((document.querySelector("main h1") || {}).textContent || "").includes(t)', arg=h1, timeout=10)

    def sample(self, pg, letter):
        pg.click(f'#btn-sample-{letter}')
        self.poll(pg, '() => ClaimsEditor.state().open && document.querySelectorAll("#tabs [role=tab]").length > 0')

    def paste(self, pg, rows):
        pg.click('#btn-paste')
        pg.fill('#paste-text', yaml.safe_dump({'claims': rows}, allow_unicode=True, sort_keys=False))
        pg.select_option('#paste-kind', 'claims.yaml')
        pg.click('#paste-open')
        self.poll(pg, '() => ClaimsEditor.state().open')

    def selected(self, pg):
        return pg.evaluate('() => Array.from(document.querySelectorAll("#claim-tabs [role=tab]")).filter(b => b.getAttribute("aria-selected") === "true").map(b => b.dataset.tab)')

    # ------------------------------------------------------------------ every column of the schema is in a tab
    def test_every_schema_column_is_shown_in_a_tab_that_can_be_selected(self):
        row, props = full_row()
        pg = self.open()
        self.paste(pg, [row])
        self.go(pg, '#/claim/C-all', '(C-all)')
        self.assertEqual(pg.eval_on_selector_all('#claim-tabs [role=tab]', 'els => els.map(e => e.firstChild.textContent.trim())'), TAB_LABELS)
        self.assertEqual(pg.eval_on_selector_all('.chead dt', 'els => els.map(e => e.textContent)'), HEAD_LABELS)
        where = pg.evaluate('''() => { const o = {}; document.querySelectorAll('[role=tabpanel] [data-col]').forEach(e => {
            (o[e.dataset.col] = o[e.dataset.col] || []).push(e.closest('[role=tabpanel]').dataset.tabpanel); }); return o; }''')
        self.assertEqual([p for p in props if p not in where], [])
        self.assertEqual({k: v for k, v in where.items() if len(v) != 1}, {})
        # nothing is folded away: every column is filled in
        self.assertEqual(pg.locator('main details.fold.unfilled').count(), 0)
        self.assertEqual(pg.locator('main .col.empty').count(), 0)
        # each column is on screen once its tab is selected (with the mouse), and only one panel is shown at a time
        for tab in pg.evaluate('() => window.CLAIMS_VIEWER_DATA.meta.claim_tabs'):
            pg.click(f'#ctab-{tab["id"]}')
            self.assertEqual(self.selected(pg), [tab['id']])
            self.assertEqual(pg.eval_on_selector_all('[role=tabpanel][data-tabpanel]:not([hidden])', 'els => els.map(e => e.dataset.tabpanel)'), [tab['id']])
            for c in tab['columns']:
                self.assertTrue(pg.is_visible(f'#cpanel-{tab["id"]} [data-col="{c}"]'), c)
                self.assertNotIn('（未記入）', pg.inner_text(f'#cpanel-{tab["id"]} [data-col="{c}"] .cv'), c)
        self.assertEqual([p for p in pg.problems if 'pageerror' in p], [])

    # ------------------------------------------------------------------ the columns not filled in are folded
    def test_unfilled_columns_are_folded_and_counted(self):
        claims = yaml.safe_load(open(os.path.join(ROOT, 'templates', 'examples', 'scenario-a', 'claims.yaml'), encoding='utf-8'))['claims']
        row = next(c for c in claims if c['id'] == 'C-tenant-id')
        pg = self.open()
        self.sample(pg, 'a')
        self.go(pg, '#/claim/C-tenant-id', '(C-tenant-id)')
        # the six fields on top
        self.assertEqual(pg.eval_on_selector_all('.chead dt', 'els => els.map(e => e.textContent)'), HEAD_LABELS)
        self.assertIn(row['name'], pg.inner_text('[data-head="name"]'))
        self.assertIn('C-tenant-id', pg.inner_text('[data-head="name"]'))
        self.assertIn(row['decision'], pg.inner_text('[data-head="status"]'))
        for t in row['carried_in']:
            self.assertIn(t, pg.inner_text('[data-head="carried_in"]'))
        for tab in pg.evaluate('() => window.CLAIMS_VIEWER_DATA.meta.claim_tabs'):
            tid = tab['id']
            filled = [c for c in tab['columns'] if c in row]
            empty = [c for c in tab['columns'] if c not in row]
            pg.click(f'#ctab-{tid}')
            self.assertEqual(pg.inner_text(f'#ctab-{tid} .cnt'), f'{len(filled)}/{len(tab["columns"])}')
            fold = pg.locator(f'#cpanel-{tid} details.fold.unfilled')
            self.assertEqual(fold.count(), 1 if empty else 0, tid)
            for c in filled:
                self.assertTrue(pg.is_visible(f'#cpanel-{tid} [data-col="{c}"]'), c)
            if not empty:
                continue
            self.assertFalse(fold.evaluate('e => e.open'), tid)  # folded by default
            self.assertEqual(fold.locator(':scope > summary').inner_text().strip(), f'未記入 {len(empty)} 件を表示')
            self.assertEqual(fold.locator('.col.empty').evaluate_all('els => els.map(e => e.dataset.col)'), empty)
            self.assertFalse(pg.is_visible(f'#cpanel-{tid} [data-col="{empty[0]}"]'))
            fold.locator(':scope > summary').click()
            self.assertTrue(pg.is_visible(f'#cpanel-{tid} [data-col="{empty[0]}"]'))
            self.assertIn('（未記入）', pg.inner_text(f'#cpanel-{tid} [data-col="{empty[0]}"] .cv'))
        # no words of the makers on this screen (#67)
        chrome = pg.evaluate("""() => Array.from(document.querySelectorAll('#main h1, #main .cbadges, #main .chead dt, #claim-tabs, ' +
            '#main details.unfilled > summary, #main [data-related], #main [data-lint-for] > strong, #main .col summary')).map(e => e.textContent).join(' ')""")
        for word in ('台帳', 'ホップ', '出どころ', '観点', '縮小 Lite', '正本', 'lint', '検査'):
            self.assertNotIn(word, chrome)
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ keyboard, and the tab in the URL
    def test_tabs_with_the_keyboard_and_the_tab_is_kept_in_the_url(self):
        pg = self.open()
        self.sample(pg, 'a')
        self.go(pg, '#/claim/C-tenant-id', '(C-tenant-id)')
        ids = [t['id'] for t in pg.evaluate('() => window.CLAIMS_VIEWER_DATA.meta.claim_tabs')]
        self.assertEqual(self.selected(pg), ['overview'])
        self.assertEqual(pg.get_attribute('#claim-tabs', 'role'), 'tablist')
        # roving tabindex: only the selected tab is in the tab order
        self.assertEqual(pg.eval_on_selector_all('#claim-tabs [role=tab]', 'els => els.filter(e => e.tabIndex === 0).map(e => e.dataset.tab)'), ['overview'])
        pg.focus('#ctab-overview')
        pg.keyboard.press('ArrowRight')
        self.assertEqual(self.selected(pg), [ids[1]])
        self.assertEqual(pg.evaluate('() => document.activeElement.id'), 'ctab-' + ids[1])
        self.assertIn('tab=' + ids[1], pg.evaluate('() => location.hash'))
        self.assertEqual(pg.get_attribute(f'#ctab-{ids[1]}', 'aria-controls'), 'cpanel-' + ids[1])
        self.assertEqual(pg.get_attribute(f'#cpanel-{ids[1]}', 'aria-labelledby'), 'ctab-' + ids[1])
        pg.keyboard.press('End')
        self.assertEqual(self.selected(pg), [ids[-1]])
        pg.keyboard.press('ArrowRight')  # wraps
        self.assertEqual(self.selected(pg), [ids[0]])
        self.assertNotIn('tab=', pg.evaluate('() => location.hash'))
        pg.keyboard.press('ArrowLeft')
        self.assertEqual(self.selected(pg), [ids[-1]])
        pg.keyboard.press('Home')
        self.assertEqual(self.selected(pg), [ids[0]])
        # the URL opens the tab again (a reload of the screen, another claim and back)
        pg.keyboard.press('ArrowRight')
        pg.keyboard.press('ArrowRight')
        h = pg.evaluate('() => location.hash')
        self.assertIn('tab=' + ids[2], h)
        self.go(pg, '#/claims', 'クレーム一覧')
        self.go(pg, h, '(C-tenant-id)')
        self.assertEqual(self.selected(pg), [ids[2]])
        self.assertTrue(pg.is_visible('#cpanel-' + ids[2]))
        pg.go_back()
        self.poll(pg, '() => (document.querySelector("main h1") || {}).textContent.includes("クレーム一覧")', timeout=10)
        pg.go_forward()
        self.poll(pg, '() => !!document.querySelector("#claim-tabs")', timeout=10)
        self.assertEqual(self.selected(pg), [ids[2]])
        # a tab name that does not exist falls back to the first tab
        self.go(pg, '#/claims', 'クレーム一覧')
        self.go(pg, '#/claim/C-tenant-id?tab=nope', '(C-tenant-id)')
        self.assertEqual(self.selected(pg), ['overview'])
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ a problem lands on its field
    def test_focus_column_lands_on_the_tab_and_the_row_of_the_column(self):
        claims = yaml.safe_load(open(os.path.join(ROOT, 'templates', 'examples', 'scenario-a', 'claims.yaml'), encoding='utf-8'))['claims']
        row = next(c for c in claims if c['id'] == 'C-tenant-id')
        tabs = build_claims_viewer.claim_tabs()
        tab_of = {c: t['id'] for t in tabs for c in t['columns']}
        filled = next(c for c in tab_of if c in row and tab_of[c] == 'protect')
        unfilled = next(c for c in tab_of if c not in row and tab_of[c] not in ('overview', 'protect'))
        pg = self.open()
        self.sample(pg, 'a')
        self.go(pg, '#/claims', 'クレーム一覧')
        self.assertTrue(pg.evaluate('c => ClaimsPreview.focusColumn("claims", "C-tenant-id", c)', filled))
        self.poll(pg, 'c => document.activeElement && document.activeElement.dataset.col === c', arg=filled, timeout=10)
        self.assertEqual(self.selected(pg), ['protect'])
        self.assertIn('tab=protect', pg.evaluate('() => location.hash'))
        self.assertTrue(pg.is_visible(f'[data-col="{filled}"]'))
        self.assertTrue(pg.evaluate('c => document.querySelector(`[data-col="${c}"]`).classList.contains("flash")', filled))
        # a column that is not filled in: its fold is opened; a path into the column (a.b[0]) lands on the column
        self.assertTrue(pg.evaluate('c => ClaimsPreview.focusColumn("claims", "C-tenant-id", c + "[0].x")', unfilled))
        self.poll(pg, 'c => document.activeElement && document.activeElement.dataset.col === c', arg=unfilled, timeout=10)
        self.assertEqual(self.selected(pg), [tab_of[unfilled]])
        self.assertTrue(pg.is_visible(f'[data-col="{unfilled}"]'))
        self.assertTrue(pg.evaluate('c => document.querySelector(`[data-col="${c}"]`).closest("details").open', unfilled))
        # from the same screen and the same tab (the hash does not change)
        self.assertTrue(pg.evaluate('c => ClaimsPreview.focusColumn("claims", "C-tenant-id", c)', unfilled))
        self.poll(pg, 'c => document.activeElement && document.activeElement.dataset.col === c', arg=unfilled, timeout=10)
        # no column: the screen of the row; a row that does not exist: false, and nothing moves
        self.assertTrue(pg.evaluate('() => ClaimsPreview.focusColumn("claims", "C-iss", null)'))
        self.poll(pg, '() => (document.querySelector("main h1") || {}).textContent.includes("(C-iss)")', timeout=10)
        h = pg.evaluate('() => location.hash')
        self.assertFalse(pg.evaluate('() => ClaimsPreview.focusColumn("claims", "C-no-such-row", "type")'))
        self.assertFalse(pg.evaluate('() => ClaimsPreview.focusColumn("nothing", "x", "type")'))
        self.assertEqual(pg.evaluate('() => location.hash'), h)
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ 900 and 1280 wide
    def test_screenshots_and_no_horizontal_overflow(self):
        for width in (1280, 900):
            pg = self.open(width=width)
            self.sample(pg, 'b')
            self.go(pg, '#/claim/C-roles', '(C-roles)')
            # the six fields and the row of tabs stay inside the pane (the row of tabs scrolls sideways inside itself)
            over = pg.evaluate("""() => { const m = document.querySelector('#main').getBoundingClientRect();
                return Array.from(document.querySelectorAll('#main .chead, #main .chead .chi, #claim-tabs, #main [role=tabpanel]:not([hidden]) .cols'))
                    .filter(e => e.getBoundingClientRect().right > m.right + 1).map(e => e.className || e.id); }""")
            self.assertEqual(over, [])
            # the row of tabs is one line (it scrolls sideways when it does not fit)
            tops = pg.eval_on_selector_all('#claim-tabs [role=tab]', 'els => els.map(e => Math.round(e.getBoundingClientRect().top))')
            self.assertEqual(len(set(tops)), 1, tops)
            if SHOTS:
                pg.screenshot(path=os.path.join(ROOT, SHOTS, f'{width}_claim_detail.png'), full_page=False)
            self.assertEqual(pg.problems, [])
        # every request is a GET to this site
        self.assertEqual([r for r in pg.requests if r['method'] != 'GET' or not r['url'].startswith(self.base.rsplit('/claims/', 1)[0])], [])


if __name__ == '__main__':
    unittest.main()
