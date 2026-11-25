# -*- coding: utf-8 -*-
"""Open the design editor (docs/claims/, #49; the viewer of #36) in headless Chromium.

  pip install playwright && python -m playwright install chromium
  python -m pytest -q tools/tests/test_claims_editor_ui.py
  CLAIMS_EDITOR_EVIDENCE=research/claims-editor python -m pytest -q tools/tests/test_claims_editor_ui.py   # also save
      screenshots, the network log and the load measurements

Skipped when Playwright or its browser is not installed (CI: the workflows have no browser; run them locally).
docs/ is served by a local HTTP server, as GitHub Pages serves it (the slide viewer at /, the editor at /claims/).
Checks: the page opens empty and loads no sample; the six entry points (files, folder, drag and drop, paste, skeleton,
samples A and B); an edit shows JSON Schema and claim_lint diagnostics in the editor (line markers) and on the preview
rows; claim_lint in Pyodide gives the same result as the CLI for scenarios A and B with --profile full and lite; the
exported files (one file and zip) are byte for byte the opened ones; folds are kept in the URL; the review hooks of #50
(anchors, row hashes, row panels); no request is a POST, goes to another origin or is a beacon, and the CSP stops a
connection from the page and from the worker.
"""
import functools
import http.server
import io
import json
import os
import pathlib
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import zipfile

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS = os.path.join(ROOT, 'docs')
EVIDENCE = os.environ.get('CLAIMS_EDITOR_EVIDENCE')
EXAMPLES = os.path.join(ROOT, 'templates', 'examples')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

def menu_open(pg):
    """Open the menu 「ファイル」 of the top bar (#67: export, autosave, close and add-file live there)."""
    if not pg.evaluate('() => document.querySelector("#ws-menu").open'):
        pg.click('#ws-menu-btn')


def menu_click(pg, sel):
    menu_open(pg)
    pg.click(sel)


def menu_check(pg, on):
    menu_open(pg)
    (pg.check if on else pg.uncheck)('#chk-autosave')
    if pg.evaluate('() => document.querySelector("#ws-menu").open && !document.querySelector("#confirm")'):
        pg.keyboard.press('Escape')



def load_yaml(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return yaml.safe_load(f)


def claim_columns():
    with open(os.path.join(ROOT, 'templates', 'registry', 'claims.schema.json'), encoding='utf-8') as f:
        return list(json.load(f)['$defs']['claim']['properties'])


def read_lf(path):
    with open(path, 'rb') as f:
        return f.read().replace(b'\r\n', b'\n')


def cli_lint(design_dir, profile):
    """python tools/claim_lint DIR --profile P --format json --also-scan DIR/design.md (the CI command)."""
    rel = os.path.relpath(design_dir, ROOT).replace(os.sep, '/')
    out = subprocess.run([sys.executable, os.path.join('tools', 'claim_lint'), rel, '--profile', profile, '--format', 'json',
                          '--also-scan', rel + '/design.md'], cwd=ROOT, capture_output=True)
    return json.loads(out.stdout.decode('utf-8'))


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@unittest.skipIf(sync_playwright is None, 'playwright not installed')
class ClaimsEditor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(_Quiet, directory=DOCS))
        cls.srv.daemon_threads = True
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

    def open(self, width=1500, accept_downloads=False):
        ctx = self.browser.new_context(viewport={'width': width, 'height': 950}, accept_downloads=accept_downloads)
        pg = ctx.new_page()
        pg.problems, pg.requests = [], []
        pg.on('pageerror', lambda e: pg.problems.append('pageerror: ' + str(e)))
        pg.on('console', lambda m: pg.problems.append(f'console {m.type}: {m.text}') if m.type in ('error', 'warning') else None)
        # every request of the page and of its workers (context-level, so the Pyodide worker's fetches are included)
        ctx.on('request', lambda r: pg.requests.append({'method': r.method, 'url': r.url, 'type': r.resource_type}))
        pg.goto(self.base)
        pg.wait_for_selector('#btn-sample-a')
        self.addCleanup(ctx.close)
        return pg

    def poll(self, pg, js, timeout=90, arg=None):
        """Wait until the JS expression is truthy. (wait_for_function evaluates a string, which the CSP forbids.)"""
        end = time.time() + timeout
        while time.time() < end:
            v = pg.evaluate(js, arg) if arg is not None else pg.evaluate(js)
            if v:
                return v
            time.sleep(0.1)
        self.fail(f'timed out waiting for {js}')

    def go(self, pg, hash_, h1=None):
        pg.evaluate('h => { location.hash = h; }', hash_)
        if h1:
            self.poll(pg, 't => ((document.querySelector("main h1") || {}).textContent || "").includes(t)', arg=h1, timeout=10)
        else:
            pg.wait_for_timeout(150)

    def shot(self, pg, name):
        if EVIDENCE:
            pg.screenshot(path=os.path.join(ROOT, EVIDENCE, name + '.jpg'), type='jpeg', quality=70, full_page=False)

    def sample(self, pg, letter):
        pg.click(f'#btn-sample-{letter}')
        self.poll(pg, '() => ClaimsEditor.state().open && document.querySelectorAll("#tabs [role=tab]").length > 0', timeout=15)

    def lint_fresh(self, pg, timeout=120):
        self.poll(pg, '() => ClaimsEditor.state().lint === "fresh"', timeout=timeout)
        return pg.evaluate('() => ClaimsEditor.lastLint')

    def sample_files(self, letter):
        d = os.path.join(EXAMPLES, 'scenario-' + letter)
        names = [n for n in ('claims.yaml', 'token_types.yaml', 'hops.yaml', 'catalog_answers.yaml') if os.path.isfile(os.path.join(d, n))]
        names += sorted(n for n in os.listdir(d) if n.startswith('claim_request_') and n.endswith('.md')) + ['design.md']
        return d, names

    # ------------------------------------------------------------------ empty start
    def test_opens_empty_and_loads_no_sample(self):
        pg = self.open()
        pg.wait_for_timeout(500)
        st = pg.evaluate('() => ClaimsEditor.state()')
        self.assertFalse(st['open'])
        self.assertFalse(pg.is_visible('#split'))
        self.assertTrue(pg.is_visible('#start'))
        self.assertEqual(pg.locator('#tabs [role=tab]').count(), 0)
        urls = [r['url'].replace(self.base, '') for r in pg.requests]
        self.assertFalse([u for u in urls if 'sample-' in u or 'skeleton' in u or 'pyodide' in u or 'claim_lint' in u], urls)
        for b in ('#btn-open-files', '#btn-open-folder', '#drop-hint', '#btn-paste', '#btn-skeleton', '#btn-sample-a', '#btn-sample-b'):
            self.assertEqual(pg.locator(b).count(), 1, b)
        self.shot(pg, '00_empty')
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ the six entry points
    def test_entry_files(self):
        pg = self.open()
        d, names = self.sample_files('a')
        pg.set_input_files('#in-files', [os.path.join(d, n) for n in names[:4]])
        self.poll(pg, '() => ClaimsEditor.state().open')
        self.assertEqual(pg.evaluate('() => ClaimsEditor.state().files'), names[:4])
        self.assertEqual(pg.evaluate('() => ClaimsEditor.state().origin'), 'files')
        self.go(pg, '#/claims', 'クレーム一覧')
        self.assertEqual(pg.locator('table[data-table="claims"] tbody tr').count(), len(load_yaml('templates/examples/scenario-a/claims.yaml')['claims']))
        self.assertEqual(pg.problems, [])

    def test_entry_folder(self):
        pg = self.open()
        # the folder has schemas/ below it; the files of the directory that holds claims.yaml are opened
        pg.set_input_files('#in-folder', os.path.join(EXAMPLES, 'scenario-b'))
        self.poll(pg, '() => ClaimsEditor.state().open')
        _, names = self.sample_files('b')
        st = pg.evaluate('() => ClaimsEditor.state()')
        self.assertEqual(st['origin'], 'folder')
        self.assertEqual(sorted(st['files']), sorted(names))
        self.assertEqual(st['designRel'], 'work/scenario-b')
        self.assertEqual(pg.problems, [])

    def test_entry_drag_and_drop(self):
        pg = self.open()
        d, _ = self.sample_files('a')
        files = {n: open(os.path.join(d, n), encoding='utf-8').read() for n in ('claims.yaml', 'hops.yaml')}
        files['notes.txt'] = 'not a design file'
        pg.evaluate('''files => {
            const dt = new DataTransfer();
            for (const [n, t] of Object.entries(files)) dt.items.add(new File([t], n, { type: 'text/plain' }));
            document.body.dispatchEvent(new DragEvent('dragenter', { dataTransfer: dt, bubbles: true }));
            document.body.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true }));
        }''', files)
        self.poll(pg, '() => ClaimsEditor.state().open')
        st = pg.evaluate('() => ClaimsEditor.state()')
        self.assertEqual(st['files'], ['claims.yaml', 'hops.yaml'])
        self.assertEqual(st['origin'], 'drop')
        self.assertIn('notes.txt', pg.inner_text('#status'))
        self.assertFalse(pg.is_visible('#drop-overlay'))
        self.assertEqual(pg.problems, [])

    def test_entry_paste(self):
        pg = self.open()
        text = open(os.path.join(EXAMPLES, 'scenario-a', 'hops.yaml'), encoding='utf-8').read()
        pg.click('#btn-paste')
        pg.fill('#paste-text', text)
        pg.click('#paste-open')
        self.poll(pg, '() => ClaimsEditor.state().open')
        self.assertEqual(pg.evaluate('() => ClaimsEditor.state().files'), ['hops.yaml'])  # recognised from the content
        self.assertEqual(pg.evaluate('() => ClaimsEditor.fileText("hops.yaml")'), text.replace('\r\n', '\n'))
        self.go(pg, '#/hops', '経路')
        self.assertGreater(pg.locator('table[data-table="hops"] tbody tr').count(), 0)
        self.assertEqual(pg.problems, [])

    def test_entry_skeleton_is_new_design(self):
        import new_design
        import build_claims_viewer as bcv
        want = new_design.build(os.path.join(ROOT, bcv.SKELETON_DIR))
        pg = self.open()
        pg.click('#btn-skeleton')
        self.poll(pg, '() => ClaimsEditor.state().open')
        self.assertEqual(sorted(pg.evaluate('() => ClaimsEditor.state().files')), sorted(want))
        for n, t in want.items():
            self.assertEqual(pg.evaluate('n => ClaimsEditor.fileText(n)', n), t, n)
        # an empty design: the schema check already reports the empty required values
        self.assertGreater(len(pg.evaluate('() => ClaimsEditor.diagnostics()')), 0)
        self.shot(pg, '01_skeleton')
        self.assertEqual(pg.problems, [])

    def test_entry_samples(self):
        pg = self.open()
        for letter in ('a', 'b'):
            d, names = self.sample_files(letter)
            if letter == 'b':
                menu_click(pg, '#btn-close')
                self.poll(pg, '() => !ClaimsEditor.state().open')
            self.sample(pg, letter)
            st = pg.evaluate('() => ClaimsEditor.state()')
            self.assertEqual(st['files'], names)
            self.assertEqual(st['designRel'], f'templates/examples/scenario-{letter}')
            for n in names:
                self.assertEqual(pg.evaluate('n => ClaimsEditor.fileText(n)', n).encode('utf-8'), read_lf(os.path.join(d, n)), n)
            self.shot(pg, f'02_sample_{letter}')
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ preview screens (#36) on the opened design
    def test_every_screen_renders_and_every_column_is_shown(self):
        pg = self.open()
        self.sample(pg, 'b')
        self.go(pg, '#/lint', '問題')
        self.lint_fresh(pg)
        screens = [('#/overview', 'シナリオ B'), ('#/claims', 'クレーム一覧'), ('#/ledger', 'クレームを 1 件ずつ開く'), ('#/claim/C-tenant-id', 'C-tenant-id'),
                   ('#/tokens', 'トークン目録'), ('#/token/KC_AT', 'KC_AT'), ('#/profile', '発行方式'), ('#/hops', '経路の一覧'),
                   ('#/lifecycle', '寿命の 4 つの層'), ('#/catalog', 'カタログへの回答'), ('#/lint', '問題'), ('#/tables', '判断の行・データ源・問いと仕組み'),
                   ('#/trace', '対応表の進み具合')]
        for i, (h, title) in enumerate(screens):
            self.go(pg, h, title)
            self.shot(pg, f'10_{i:02d}_' + h.strip('#/').replace('/', '_'))
        for t in ('lifecycle-token', 'lifecycle-claim', 'lifecycle-session', 'lifecycle-definition'):
            self.go(pg, '#/lifecycle', '寿命')
            self.assertEqual(pg.locator(f'table[data-table="{t}"]').count(), 1, t)
        self.go(pg, '#/profile', '発行方式')
        self.assertIn('C-cnf', pg.inner_text('[data-effect="E-dpop"]'))
        cols = claim_columns()
        for c in load_yaml('templates/examples/scenario-b/claims.yaml')['claims']:
            self.go(pg, f"#/claim/{c['id']}", f"({c['id']})")
            shown = pg.eval_on_selector_all('main [data-col]', 'els => els.map(e => e.dataset.col)')
            self.assertEqual([k for k in cols if k not in shown], [], c['id'])
            empty = pg.eval_on_selector_all('main .col.empty', 'els => els.map(e => e.dataset.col)')
            self.assertEqual([k for k in empty if k in c], [], c['id'])
        self.go(pg, '#/claim/C-employee-id', '(C-employee-id)')
        self.assertIn('照合する場所', pg.inner_text('[data-col="enforced_at"] .lbl'))
        self.assertIn('L18', pg.inner_text('[data-lint-for="C-employee-id"]'))  # lint overlay on the row
        self.go(pg, '#/claims', 'クレーム一覧')
        self.assertIn('warn', pg.inner_text('tr[data-row="C-employee-id"]'))
        # status is not shown by colour only
        for h in ('#/profile', '#/claims', '#/lint'):
            self.go(pg, h)
            for t in pg.eval_on_selector_all('main .badge', 'els => els.map(e => e.textContent.trim())'):
                self.assertRegex(t, r'[A-Za-z぀-ヿ一-鿿]', (h, t))
        self.assertEqual(pg.problems, [])

    def test_links_leave_in_a_new_tab_and_unsaved_edits_are_guarded(self):
        import csv
        pg = self.open()
        self.sample(pg, 'a')
        self.go(pg, '#/claim/C-iss', '(C-iss)')
        with open(os.path.join(DOCS, 'slide_ids.csv'), encoding='utf-8') as f:
            n = {r['id']: r['n'] for r in csv.DictReader(f)}
        link = pg.locator('a[data-slide="p05-multitenancy"]').first
        self.assertEqual(link.get_attribute('href'), '../#p05-multitenancy')
        self.assertEqual((link.get_attribute('target'), link.get_attribute('rel')), ('_blank', 'noopener noreferrer'))
        # every link of the page that leaves the editor (another site or the slide page) opens in a new tab
        leaving = pg.eval_on_selector_all('a[href]', """els => els.filter(a => /^(https?:|\\.\\.\\/)/.test(a.getAttribute('href')))
            .map(a => [a.getAttribute('href'), a.getAttribute('target'), a.getAttribute('rel')])""")
        self.assertTrue(leaving)
        self.assertEqual([x for x in leaving if x[1:] != ['_blank', 'noopener noreferrer']], [])
        # the link is in one of the tabs of the claim detail screen (#67): its tab is selected first
        pg.click('#ctab-' + link.evaluate('e => e.closest("[role=tabpanel]").dataset.tabpanel'))
        with pg.context.expect_page() as popup:
            link.click()
        slide = popup.value
        slide.wait_for_selector('#pos')
        self.assertEqual(slide.inner_text('#pos'), f"{n['p05-multitenancy']} / {len(n)}")
        self.assertEqual(pg.evaluate('() => location.pathname'), '/claims/')  # the editor stays
        # an edit that is not written out: leaving the page asks first (beforeunload)
        pg.evaluate('() => ClaimsEditor.replaceText("hops.yaml", "hops:", "hops:  # unsaved")')
        self.assertTrue(pg.evaluate('() => ClaimsEditor.unsaved()'))
        self.assertTrue(pg.evaluate('() => { const e = new Event("beforeunload", { cancelable: true }); dispatchEvent(e); return e.defaultPrevented; }'))
        pg.locator('main h1').click()  # a user activation, which Chromium needs to show the question
        with pg.expect_event('dialog') as dlg:
            pg.close(run_before_unload=True)
        self.assertEqual(dlg.value.type, 'beforeunload')
        dlg.value.dismiss()  # stay on the page
        # once written out, leaving asks nothing
        pg2 = self.open(accept_downloads=True)
        self.sample(pg2, 'a')
        pg2.evaluate('() => ClaimsEditor.replaceText("hops.yaml", "hops:", "hops:  # unsaved")')
        with pg2.expect_download():
            menu_click(pg2, '#btn-export-zip')
        self.assertFalse(pg2.evaluate('() => ClaimsEditor.unsaved()'))
        self.assertFalse(pg2.evaluate('() => { const e = new Event("beforeunload", { cancelable: true }); dispatchEvent(e); return e.defaultPrevented; }'))

    # ------------------------------------------------------------------ edit -> diagnostics (editor and preview)
    def test_edit_shows_schema_and_lint_diagnostics_in_the_editor_and_the_preview(self):
        pg = self.open()
        self.sample(pg, 'a')
        self.assertEqual(pg.evaluate('() => ClaimsEditor.diagnostics().length'), 0)  # scenario A is schema-valid
        # a column outside the schema, and a number where the schema wants a string
        self.assertTrue(pg.evaluate('() => ClaimsEditor.replaceText("claims.yaml", "  - id: C-iss\\n", "  - id: C-iss\\n    bogus_column: 1\\n")'))
        self.assertTrue(pg.evaluate('() => ClaimsEditor.replaceText("hops.yaml", "max_lifetime: 300", "max_lifetime: \\"long\\"")'))
        diags = self.poll(pg, '() => { const d = ClaimsEditor.diagnostics(); return d.length >= 2 ? d : null; }', timeout=10)
        schema = [d for d in diags if d['source'] == 'schema']
        bogus = [d for d in schema if 'bogus_column' in d['message']]
        self.assertEqual(len(bogus), 1, schema)
        lines = open(os.path.join(EXAMPLES, 'scenario-a', 'claims.yaml'), encoding='utf-8').read().split('\n')
        want_line = next(i for i, l in enumerate(lines, 1) if l.startswith('  - id: C-iss'))
        self.assertEqual((bogus[0]['file'], bogus[0]['line'], bogus[0]['anchorId']), ('claims.yaml', want_line, 'C-iss'))
        self.assertTrue(any(d['file'] == 'hops.yaml' and d['source'] == 'schema' for d in schema), schema)
        # the editor marks the line (lint gutter marker, in the editor's shadow root) and the tab shows the count
        self.poll(pg, '() => document.querySelector("#editor").shadowRoot.querySelectorAll(".cm-lint-marker-error").length > 0', timeout=5)
        self.assertIn('✖', pg.inner_text('#tab-claims\\.yaml'))
        # the preview shows them on the row
        self.go(pg, '#/claims', 'クレーム一覧')
        self.assertIn('error', pg.inner_text('tr[data-row="C-iss"]'))
        self.go(pg, '#/claim/C-iss', '(C-iss)')
        self.assertIn('bogus_column', pg.inner_text('[data-lint-for="C-iss"]'))
        self.assertIn('bogus_column', pg.inner_text('main [data-col="bogus_column"]'))  # shown as a column outside the schema
        self.shot(pg, '20_edit_schema')
        # claim_lint (Pyodide): the same findings as the CLI on the same edited files
        self.go(pg, '#/lint', '問題')
        res = self.lint_fresh(pg)['result']
        with tempfile.TemporaryDirectory(dir=os.path.join(ROOT, 'templates', 'examples')) as tmp:
            d = os.path.join(tmp, 'scenario-a')  # the same directory name: the payload schema $id and the targets
            os.makedirs(d)
            for n in pg.evaluate('() => ClaimsEditor.state().files'):
                with open(os.path.join(d, n), 'w', encoding='utf-8', newline='') as f:
                    f.write(pg.evaluate('n => ClaimsEditor.fileText(n)', n))
            cli = cli_lint(d, pg.evaluate('() => ClaimsEditor.state().profile'))
        self.assertEqual(res['findings'], cli['findings'])
        self.assertEqual(res['counts'], cli['counts'])
        self.assertGreater(res['counts']['error'], 0)
        diags = pg.evaluate('() => ClaimsEditor.diagnostics()')
        lint_schema = [d for d in diags if d['source'] == 'claim_lint' and d['rule'] == 'SCHEMA']
        self.assertTrue(any(d['file'] == 'claims.yaml' and d['line'] == want_line for d in lint_schema), lint_schema)
        self.assertEqual([d for d in diags if d['source'] == 'schema'], [])  # replaced by claim_lint's SCHEMA once fresh
        self.go(pg, '#/lint', '問題')
        self.assertIn('bogus_column', pg.inner_text('table[data-table="diagnostics"]'))
        # clicking the line of a finding moves the editor there
        pg.locator('table[data-table="diagnostics"] [data-goto^="hops.yaml:"]').first.click()
        self.assertEqual(pg.evaluate('() => ClaimsEditor.state().active'), 'hops.yaml')
        self.shot(pg, '21_edit_lint')
        # undo the edits: the errors go away after the next run
        pg.evaluate('() => ClaimsEditor.replaceText("claims.yaml", "    bogus_column: 1\\n", "")')
        pg.evaluate('() => ClaimsEditor.replaceText("hops.yaml", "max_lifetime: \\"long\\"", "max_lifetime: 300")')
        self.poll(pg, '() => ClaimsEditor.lastLint && ClaimsEditor.lastLint.fresh && ClaimsEditor.lastLint.result.counts.error === 0 && ClaimsEditor.state().lint === "fresh"')
        self.assertEqual(pg.problems, [])

    def test_yaml_syntax_error_is_shown_on_its_line(self):
        pg = self.open()
        pg.click('#btn-paste')
        pg.fill('#paste-text', 'claims:\n  - id: C-x\n    name: a\n    name: b\n')
        pg.select_option('#paste-kind', 'claims.yaml')
        pg.click('#paste-open')
        self.poll(pg, '() => ClaimsEditor.state().open')
        d = self.poll(pg, '() => ClaimsEditor.diagnostics().filter(x => x.source === "yaml")', timeout=5)
        self.assertEqual(d[0]['line'], 4)  # the duplicate key (claim_lint's loader rejects duplicates too)
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ parity with the CLI
    def test_lint_in_the_browser_equals_the_cli(self):
        pg = self.open()
        report = []
        for letter in ('a', 'b'):
            if letter == 'b':
                menu_click(pg, '#btn-close')
                self.poll(pg, '() => !ClaimsEditor.state().open')
            self.sample(pg, letter)
            self.go(pg, '#/lint', '問題')
            for profile in ('full', 'lite'):
                pg.select_option('#lint-profile', profile)
                self.poll(pg, 'p => ClaimsEditor.state().lint === "fresh" && ClaimsEditor.lastLint.profile === p', arg=profile)
                got = pg.evaluate('() => ClaimsEditor.lastLint')
                cli = cli_lint(os.path.join(EXAMPLES, 'scenario-' + letter), profile)
                self.assertEqual(got['result'], cli, f'scenario {letter} {profile}')  # the whole JSON result
                report.append({'scenario': letter.upper(), 'profile': profile, 'counts': cli['counts'], 'findings': len(cli['findings']),
                               'equal_to_cli': got['result'] == cli, 'browser_ms': got['ms']})
        if EVIDENCE:
            with open(os.path.join(ROOT, EVIDENCE, 'parity.json'), 'w', encoding='utf-8', newline='\n') as f:
                json.dump({'what': 'claim_lint in Pyodide (the editor) vs python tools/claim_lint DIR --profile P --format json --also-scan DIR/design.md',
                           'test': 'tools/tests/test_claims_editor_ui.py::test_lint_in_the_browser_equals_the_cli',
                           'compared': 'the whole JSON result (findings, counts, r8, checked, ...)', 'results': report,
                           'pyodide': pg.evaluate('() => ClaimsEditor.lintInfo')}, f, ensure_ascii=False, indent=1)
                f.write('\n')
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ export round trip
    def test_export_round_trip(self):
        pg = self.open(accept_downloads=True)
        self.sample(pg, 'b')
        d, names = self.sample_files('b')
        with pg.expect_download() as dl:
            menu_click(pg, '#btn-export-zip')
        data = pathlib.Path(dl.value.path()).read_bytes()
        self.assertEqual(dl.value.suggested_filename, 'scenario-b.zip')
        names = names + ['review.yaml']  # the review records of the example (#50) go into the zip with the design
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            self.assertEqual(sorted(z.namelist()), sorted('scenario-b/' + n for n in names))
            for n in names:
                self.assertEqual(z.read('scenario-b/' + n), read_lf(os.path.join(d, n)), n)
        pg.click('#tab-token_types\\.yaml')
        with pg.expect_download() as dl:
            menu_click(pg, '#btn-export-one')
        self.assertEqual(dl.value.suggested_filename, 'token_types.yaml')
        self.assertEqual(pathlib.Path(dl.value.path()).read_bytes(), read_lf(os.path.join(d, 'token_types.yaml')))
        # a file with a BOM and CRLF comes back as it was; an edit is in the exported file
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'hops.yaml')
            raw = b'\xef\xbb\xbf' + read_lf(os.path.join(d, 'hops.yaml')).replace(b'\n', b'\r\n')
            with open(p, 'wb') as f:
                f.write(raw)
            menu_click(pg, '#btn-close')
            pg.set_input_files('#in-files', [p])
            self.poll(pg, '() => ClaimsEditor.state().open')
            with pg.expect_download() as dl:
                menu_click(pg, '#btn-export-one')
            self.assertEqual(pathlib.Path(dl.value.path()).read_bytes(), raw)
            pg.evaluate('() => ClaimsEditor.replaceText("hops.yaml", "hops:", "hops:  # edited")')
            with pg.expect_download() as dl:
                menu_click(pg, '#btn-export-one')
            self.assertEqual(pathlib.Path(dl.value.path()).read_bytes(), raw.replace(b'hops:', b'hops:  # edited', 1))
        self.assertEqual(pg.problems, [])

    def test_autosave_is_opt_in(self):
        pg = self.open()
        self.sample(pg, 'a')
        pg.evaluate('() => ClaimsEditor.replaceText("hops.yaml", "hops:", "hops:  # mine")')
        pg.wait_for_timeout(1500)
        self.assertEqual(pg.evaluate('() => Object.keys(localStorage)'), [])  # nothing is stored unless enabled
        menu_check(pg, True)
        pg.evaluate('() => ClaimsEditor.replaceText("hops.yaml", "# mine", "# mine2")')
        key = 'claims-editor:autosave:v2:templates/examples/scenario-a'
        self.poll(pg, 'k => (localStorage.getItem(k) || "").includes("mine2")', arg=key, timeout=5)
        pg.reload()
        pg.wait_for_selector('[data-restore="templates/examples/scenario-a"]')
        self.assertFalse(pg.evaluate('() => ClaimsEditor.state().open'))  # still opens empty; restoring is a choice
        pg.click('[data-restore="templates/examples/scenario-a"]')
        self.poll(pg, '() => ClaimsEditor.state().open')
        self.assertIn('# mine2', pg.evaluate('() => ClaimsEditor.fileText("hops.yaml")'))
        # turning autosave off asks what to do with the saved copies (R3): cancel keeps it on, delete removes them
        menu_check(pg, False)
        pg.wait_for_selector('dialog#confirm[open]')
        self.assertIn('1 件', pg.inner_text('dialog#confirm'))
        pg.click('dialog#confirm [data-choice="cancel"]')
        self.poll(pg, '() => !document.querySelector("dialog#confirm")')
        self.assertTrue(pg.is_checked('#chk-autosave'))
        self.assertEqual(len(pg.evaluate('() => Object.keys(localStorage)')), 2)
        menu_check(pg, False)
        pg.click('dialog#confirm [data-choice="delete"]')
        self.poll(pg, '() => Object.keys(localStorage).length === 0', timeout=5)
        self.assertEqual(pg.problems, [])

    def test_opening_another_design_never_loses_work(self):
        # the loss of the PR #51 check (F1): paste MY-WORK, enable autosave, close, open sample A -> MY-WORK was overwritten
        pg = self.open(accept_downloads=True)
        pg.click('#btn-paste')
        pg.fill('#paste-text', 'hops:\n  - id: MY-WORK\n')
        pg.click('#paste-open')
        self.poll(pg, '() => ClaimsEditor.state().open')
        menu_check(pg, True)
        self.assertEqual(pg.evaluate('() => Object.keys(localStorage).filter(k => k.includes("autosave:v2"))'), [])  # opening saves nothing
        pg.evaluate('() => ClaimsEditor.replaceText("hops.yaml", "MY-WORK", "MY-WORK-2")')
        rel = pg.evaluate('() => ClaimsEditor.state().designRel')
        self.assertRegex(rel, r'^work/pasted-\d{8}-\d{6}-[0-9a-f]{6}$')  # a slot of its own (R4)
        mine = 'claims-editor:autosave:v2:' + rel
        self.poll(pg, 'k => (localStorage.getItem(k) || "").includes("MY-WORK-2")', arg=mine, timeout=5)
        menu_click(pg, '#btn-close')  # autosave holds the edit: no question
        self.poll(pg, '() => !ClaimsEditor.state().open')
        self.sample(pg, 'a')
        pg.wait_for_timeout(1500)
        self.assertIn('MY-WORK-2', pg.evaluate('k => localStorage.getItem(k)', mine))  # still there
        self.assertIsNone(pg.evaluate('() => localStorage.getItem("claims-editor:autosave:v2:templates/examples/scenario-a")'))
        # without autosave (turned off, the saved copies kept): an edit not written out is not replaced without asking
        menu_check(pg, False)
        pg.click('dialog#confirm [data-choice="keep"]')
        self.poll(pg, '() => !document.querySelector("dialog#confirm")')
        self.assertIn('MY-WORK-2', pg.evaluate('k => localStorage.getItem(k)', mine))
        pg.evaluate('() => ClaimsEditor.replaceText("hops.yaml", "hops:", "hops:  # unsaved")')
        menu_click(pg, '#btn-close')
        pg.wait_for_selector('dialog#confirm[open]')
        self.assertIn('書き出していない変更', pg.inner_text('dialog#confirm'))
        self.assertTrue(pg.evaluate('() => document.activeElement.closest("dialog") !== null'))  # focus is in the dialog
        pg.click('dialog#confirm [data-choice="cancel"]')
        self.poll(pg, '() => !document.querySelector("dialog#confirm")')
        self.assertTrue(pg.evaluate('() => ClaimsEditor.state().open'))
        self.assertIn('# unsaved', pg.evaluate('() => ClaimsEditor.fileText("hops.yaml")'))
        with pg.expect_download() as dl:
            menu_click(pg, '#btn-close')
            pg.click('dialog#confirm [data-choice="export"]')
        self.assertEqual(dl.value.suggested_filename, 'scenario-a.zip')
        with zipfile.ZipFile(dl.value.path()) as z:
            self.assertIn(b'# unsaved', z.read('scenario-a/hops.yaml'))
        self.poll(pg, '() => !ClaimsEditor.state().open')
        # an autosaved version of the design being opened is offered first
        self.sample(pg, 'a')
        menu_check(pg, True)
        pg.evaluate('() => ClaimsEditor.replaceText("hops.yaml", "hops:", "hops:  # saved-a")')
        self.poll(pg, '() => (localStorage.getItem("claims-editor:autosave:v2:templates/examples/scenario-a") || "").includes("saved-a")', timeout=5)
        menu_click(pg, '#btn-close')
        self.poll(pg, '() => !ClaimsEditor.state().open')
        pg.click('#btn-sample-a')
        pg.wait_for_selector('dialog#confirm[open]')
        self.assertIn('自動保存した版', pg.inner_text('dialog#confirm'))
        pg.click('dialog#confirm [data-choice="saved"]')
        self.poll(pg, '() => ClaimsEditor.state().open')
        self.assertIn('# saved-a', pg.evaluate('() => ClaimsEditor.fileText("hops.yaml")'))
        self.assertEqual(sorted(pg.evaluate('() => Object.keys(localStorage).filter(k => k.includes("autosave:v2"))')),
                         sorted([mine, 'claims-editor:autosave:v2:templates/examples/scenario-a']))
        self.shot(pg, '31_autosave_slots')
        self.assertEqual(pg.problems, [])

    def test_a_failed_autosave_still_guards_the_edits(self):
        # R1: localStorage refuses the save (quota): the edits stay unsaved, a warning stays, closing and leaving still ask
        pg = self.open()
        self.sample(pg, 'b')
        menu_check(pg, True)
        pg.evaluate('''() => { Storage.prototype.setItem = function () { throw new DOMException('The quota has been exceeded.', 'QuotaExceededError'); }; }''')
        pg.evaluate('() => ClaimsEditor.replaceText("hops.yaml", "hops:", "hops:  # not saved")')
        pg.wait_for_selector('#save-warn:not([hidden])', timeout=5000)
        self.assertIn('自動保存に失敗', pg.inner_text('#save-warn'))
        self.assertIn('QuotaExceededError', pg.inner_text('#save-warn'))
        self.assertEqual(pg.get_attribute('#save-warn', 'role'), 'alert')
        self.assertTrue(pg.evaluate('() => ClaimsEditor.unsaved()'))
        self.assertTrue(pg.evaluate('() => { const e = new Event("beforeunload", { cancelable: true }); dispatchEvent(e); return e.defaultPrevented; }'))
        menu_click(pg, '#btn-close')
        pg.wait_for_selector('dialog#confirm[open]')
        self.assertIn('保存できていません', pg.inner_text('dialog#confirm'))
        pg.click('dialog#confirm [data-choice="cancel"]')
        self.assertTrue(pg.evaluate('() => ClaimsEditor.state().open'))
        self.assertTrue(pg.is_visible('#save-warn'))  # the warning stays until a save succeeds
        self.shot(pg, '32_autosave_failed')

    def test_adding_a_file_with_an_open_name_asks(self):
        # R2: "add file" with the name of an open file: replace / keep both / cancel, never silently
        pg = self.open()
        self.sample(pg, 'a')
        pg.evaluate('() => ClaimsEditor.replaceText("hops.yaml", "hops:", "hops:  # edited here")')
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'hops.yaml')
            with open(p, 'w', encoding='utf-8', newline='\n') as f:
                f.write('hops:\n  - id: OTHER\n')
            for choice in ('cancel', 'both', 'replace'):
                pg.set_input_files('#in-add', [p])
                pg.wait_for_selector('dialog#confirm[open]')
                self.assertIn('書き出していない変更', pg.inner_text('dialog#confirm'))
                pg.click(f'dialog#confirm [data-choice="{choice}"]')
                self.poll(pg, '() => !document.querySelector("dialog#confirm")')
                pg.wait_for_timeout(200)
                if choice == 'cancel':
                    self.assertIn('# edited here', pg.evaluate('() => ClaimsEditor.fileText("hops.yaml")'))
                    self.assertNotIn('hops.2.yaml', pg.evaluate('() => ClaimsEditor.state().files'))
                elif choice == 'both':
                    self.assertIn('# edited here', pg.evaluate('() => ClaimsEditor.fileText("hops.yaml")'))
                    self.assertEqual(pg.evaluate('() => ClaimsEditor.fileText("hops.2.yaml")'), 'hops:\n  - id: OTHER\n')
                else:
                    self.assertEqual(pg.evaluate('() => ClaimsEditor.fileText("hops.yaml")'), 'hops:\n  - id: OTHER\n')
        self.assertEqual(pg.problems, [])

    def test_yaml11_values_are_reported_and_read_as_claim_lint_reads_them(self):
        # R5: plain scalars that YAML readers disagree on get a YAML11 warning on their line
        pg = self.open()
        text = ('claims:\n  - id: C-a\n    note: y\n    n: 1\n    flag: yes\n    exp: 1e3\n    exp2: 1.0e3\n    ok: 1.0e+3\n'
                '    oct: 012\n    time: 10:30\n    under: 1_000\n    quoted: "yes"\n    plain: true\n')
        pg.click('#btn-paste')
        pg.fill('#paste-text', text)
        pg.select_option('#paste-kind', 'claims.yaml')
        pg.click('#paste-open')
        self.poll(pg, '() => ClaimsEditor.state().open')
        d = self.poll(pg, '() => { const d = ClaimsEditor.diagnostics().filter(x => x.rule === "YAML11"); return d.length ? d : null; }', timeout=5)
        self.assertEqual(sorted(x['line'] for x in d), [3, 4, 5, 6, 7, 9, 10, 11])  # not 1.0e+3, "yes", true
        self.assertTrue(all(x['severity'] == 'warn' for x in d))
        # the values are those of claim_lint's loader (PyYAML)
        from claim_lint.core import _Loader
        import row_hash
        self.assertEqual(pg.evaluate('t => ClaimsEditor.canonicalYaml(t)', text), row_hash.jcs(yaml.load(text, Loader=_Loader)))
        self.assertEqual(pg.evaluate('() => ClaimsEditor.diagnostics().filter(x => x.rule === "YAML11" && x.file === "claims.yaml").length'), 8)
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ folds, keyboard, #50 hooks
    def test_folds_are_kept_in_the_url(self):
        pg = self.open()
        self.sample(pg, 'a')
        self.go(pg, '#/ledger', 'クレームを 1 件ずつ開く')
        row = pg.locator('details[data-fold="claim~C-iss"]')
        self.assertFalse(row.evaluate('e => e.open'))
        row.locator('summary').first.click()
        self.poll(pg, '() => decodeURIComponent(location.hash).includes("claim~C-iss")', timeout=5)  # the toggle event is asynchronous
        self.assertGreater(row.locator('[data-col]').count(), 50)  # built when opened
        pg.locator('details[data-fold="sec~却下"] > summary').click()
        self.poll(pg, '() => decodeURIComponent(decodeURIComponent(location.hash)).includes("sec~却下")', timeout=5)
        h = pg.evaluate('() => location.hash')
        # the same URL opens the same folds
        self.go(pg, '#/overview', 'シナリオ A')
        self.go(pg, h, 'クレームを 1 件ずつ開く')
        self.assertTrue(pg.locator('details[data-fold="claim~C-iss"]').evaluate('e => e.open'))
        self.assertFalse(pg.locator('details[data-fold="sec~却下"]').evaluate('e => e.open'))
        # the claim detail screen (#67): one fold per tab that has columns not filled in, keyed by the tab (unfilled~<tab>)
        row = next(c for c in load_yaml('templates/examples/scenario-a/claims.yaml')['claims'] if c['id'] == 'C-iss')
        tabs = pg.evaluate('() => window.CLAIMS_VIEWER_DATA.meta.claim_tabs')
        self.go(pg, '#/claim/C-iss', '(C-iss)')
        keys = pg.eval_on_selector_all('main details.fold', 'els => els.map(e => e.dataset.fold)')
        self.assertEqual(keys, ['unfilled~' + t['id'] for t in tabs if any(k not in row for k in t['columns'])])
        self.assertEqual(pg.locator('main details.fold[open]').count(), 0)  # folded by default
        second = keys[1]
        pg.click('#ctab-' + second.split('~')[1])
        pg.locator(f'details[data-fold="{second}"] > summary').click()
        self.poll(pg, 'k => decodeURIComponent(decodeURIComponent(location.hash)).includes(k)', arg=second, timeout=5)
        h = pg.evaluate('() => location.hash')
        self.go(pg, '#/overview', 'シナリオ A')
        self.go(pg, h, '(C-iss)')
        self.assertEqual(pg.eval_on_selector_all('main details.fold[open]', 'els => els.map(e => e.dataset.fold)'), [second])
        self.assertTrue(pg.is_visible(f'details[data-fold="{second}"] .col.empty'))
        self.shot(pg, '30_folds')
        self.assertEqual(pg.problems, [])

    def test_fold_keys_and_ids_do_not_collide(self):
        # C-a's column group and a row whose id is C-a-1 had the same key with positional keys (claim-C-a-1)
        pg = self.open()
        pg.click('#btn-paste')
        pg.fill('#paste-text', 'claims:\n  - id: C-a\n    name: a\n    decision: 採用\n  - id: C-a-1\n    name: b\n    decision: 採用\n')
        pg.select_option('#paste-kind', 'claims.yaml')
        pg.click('#paste-open')
        self.poll(pg, '() => ClaimsEditor.state().open')
        self.go(pg, '#/ledger', 'クレームを 1 件ずつ開く')
        pg.click('text=すべて開く')
        keys = pg.eval_on_selector_all('details.fold', 'els => els.map(e => e.dataset.fold)')
        self.assertEqual(len(keys), len(set(keys)), keys)
        self.assertIn('claim~C-a-1', keys)
        self.assertTrue(any(k.startswith('claim~C-a~grp~') for k in keys))
        ids = pg.eval_on_selector_all('[id]', 'els => els.map(e => e.id)')
        self.assertEqual(len(ids), len(set(ids)), [x for x in ids if ids.count(x) > 1])
        self.assertEqual(pg.problems, [])

    def test_keyboard(self):
        pg = self.open()
        pg.keyboard.press('Tab')
        self.assertEqual(pg.evaluate('document.activeElement.textContent'), '本文へ移動')
        visited = []
        for _ in range(30):
            visited.append(pg.evaluate('() => document.activeElement.id || document.activeElement.tagName'))
            if visited[-1] == 'btn-sample-a':
                break
            pg.keyboard.press('Tab')
        self.assertNotIn('in-files', visited)  # the hidden file inputs are not in the tab order (F3)
        self.assertNotIn('in-folder', visited)
        pg.keyboard.press('Enter')
        self.poll(pg, '() => ClaimsEditor.state().open', timeout=10)
        # tabs: the tablist holds only tabs; each tab controls the editor panel; arrows, Home and End move (F5)
        roles = pg.eval_on_selector_all('#tabs > *', 'els => els.map(e => e.getAttribute("role"))')
        self.assertEqual(set(roles), {'tab'})
        self.assertEqual(set(pg.eval_on_selector_all('#tabs [role=tab]', 'els => els.map(e => e.getAttribute("aria-controls"))')), {'editor'})
        self.assertEqual(pg.get_attribute('#editor', 'role'), 'tabpanel')
        self.assertEqual(pg.eval_on_selector_all('#tabs [role=tab][tabindex="0"]', 'els => els.map(e => e.id)'), ['tab-claims.yaml'])
        pg.focus('#tab-claims\\.yaml')
        pg.keyboard.press('ArrowRight')
        self.assertEqual(pg.evaluate('() => ClaimsEditor.state().active'), 'token_types.yaml')
        self.assertEqual(pg.evaluate('document.activeElement.id'), 'tab-token_types.yaml')
        self.assertEqual(pg.get_attribute('#editor', 'aria-labelledby'), 'tab-token_types.yaml')
        pg.keyboard.press('End')
        self.assertEqual(pg.evaluate('() => ClaimsEditor.state().active'), 'design.md')
        pg.keyboard.press('Home')
        self.assertEqual(pg.evaluate('() => ClaimsEditor.state().active'), 'claims.yaml')
        # the counts of a tab have words for a screen reader
        pg.evaluate('() => ClaimsEditor.replaceText("claims.yaml", "  - id: C-iss\\n", "  - id: C-iss\\n    bogus_column: 1\\n")')
        self.poll(pg, '() => document.querySelector("#tab-claims\\\\.yaml").textContent.includes("エラー 1 件")', timeout=5)
        self.assertEqual(pg.get_attribute('#tab-claims\\.yaml .tb', 'aria-hidden'), 'true')
        # Tab in the editor moves on (it does not indent), and Shift+Tab does not land on a hidden input
        pg.focus('#tab-claims\\.yaml')
        pg.keyboard.press('Tab')
        self.assertTrue(pg.evaluate('() => document.activeElement.id === "editor" || !!(document.activeElement.shadowRoot)'))
        before = pg.evaluate('() => ClaimsEditor.fileText("claims.yaml")')
        pg.keyboard.press('Tab')
        self.assertEqual(pg.evaluate('() => ClaimsEditor.fileText("claims.yaml")'), before)
        self.assertNotEqual(pg.evaluate('() => document.activeElement.id'), 'editor')
        pg.keyboard.press('Shift+Tab')
        pg.keyboard.press('Shift+Tab')
        self.assertNotIn(pg.evaluate('() => document.activeElement.id'), ('in-add', 'in-files', 'in-folder'))
        self.go(pg, '#/claims', 'クレーム一覧')
        pg.locator('main h1').click()
        pg.keyboard.press('/')
        self.assertEqual(pg.evaluate('document.activeElement.id'), 'f-q')
        self.assertEqual(pg.problems, [])

    def test_review_hooks_anchor_hash_and_row_panel(self):
        pg = self.open()
        self.sample(pg, 'a')
        anchors = pg.evaluate('() => ClaimsEditor.anchors().map(a => a.anchor)')
        self.assertIn('claims:C-iss', anchors)
        self.assertIn('token_types:AT', anchors)
        self.assertIn('catalog_answers:I25', anchors)
        self.assertIn('issuance_profile:client_type', anchors)
        self.assertEqual(len(anchors), len(set(anchors)))
        h1 = pg.evaluate('() => ClaimsEditor.rowHash("claims:C-iss")')
        self.assertEqual(h1, pg.evaluate('() => ClaimsEditor.sha256(ClaimsEditor.canonicalJson(ClaimsEditor.rowOf("claims:C-iss").row))'))
        self.assertEqual(pg.evaluate('() => ClaimsEditor.sha256("abc")'), 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
        other = pg.evaluate('() => ClaimsEditor.rowHash("claims:C-sub")')
        # a comment or another row changes nothing; a value of the row changes its hash
        pg.evaluate('() => ClaimsEditor.replaceText("claims.yaml", "  - id: C-iss\\n", "  - id: C-iss  # note\\n")')
        self.poll(pg, '() => ClaimsEditor.diagnostics && true')
        pg.wait_for_timeout(500)
        self.assertEqual(pg.evaluate('() => ClaimsEditor.rowHash("claims:C-iss")'), h1)
        pg.evaluate('() => ClaimsEditor.replaceText("claims.yaml", "  - id: C-iss  # note\\n", "  - id: C-iss\\n    x_changed: 1\\n")')
        self.poll(pg, 'h => ClaimsEditor.rowHash("claims:C-iss") !== h', arg=h1, timeout=5)
        self.assertEqual(pg.evaluate('() => ClaimsEditor.rowHash("claims:C-sub")'), other)
        # a row panel (what #50 attaches review records with) appears on the rows of every screen
        pg.evaluate('''() => ClaimsEditor.registerRowPanel((anchor, row, kind, where) => {
            const s = document.createElement('span'); s.className = 'test-panel'; s.textContent = 'panel ' + anchor + ' ' + where; return s; })''')
        self.go(pg, '#/claims', 'クレーム一覧')
        self.assertIn('panel claims:C-iss list', pg.inner_text('tr[data-anchor="claims:C-iss"]'))
        self.go(pg, '#/claim/C-iss', '(C-iss)')
        self.assertIn('panel claims:C-iss detail', pg.inner_text('[data-panel-for="claims:C-iss"]'))
        pg.click('[data-reveal="claims:C-iss"]')
        self.assertEqual(pg.evaluate('() => ClaimsEditor.state().active'), 'claims.yaml')
        # an id written twice has no anchor and is reported (rule ANCHOR)
        pg.evaluate('() => ClaimsEditor.replaceText("claims.yaml", "  - id: C-sub\\n", "  - id: C-iss\\n")')
        self.poll(pg, '() => ClaimsEditor.duplicateAnchors().includes("claims:C-iss")', timeout=5)
        self.assertIsNone(pg.evaluate('() => ClaimsEditor.rowHash("claims:C-iss")'))
        self.assertNotIn('claims:C-iss', pg.evaluate('() => ClaimsEditor.anchors().map(a => a.anchor)'))
        d = [x for x in pg.evaluate('() => ClaimsEditor.diagnostics()') if x['rule'] == 'ANCHOR']
        self.assertEqual(len(d), 2, d)
        self.assertEqual(pg.problems, [])

    def test_row_hashes_equal_tools_row_hash(self):
        import row_hash
        from claim_lint.core import _Loader
        pg = self.open()
        report = []
        for letter in ('a', 'b'):
            if letter == 'b':
                menu_click(pg, '#btn-close')
                self.poll(pg, '() => !ClaimsEditor.state().open')
            self.sample(pg, letter)
            got = dict(pg.evaluate('() => ClaimsEditor.anchors().map(a => [a.anchor, ClaimsEditor.rowHash(a.anchor)])'))
            want = row_hash.row_hashes(os.path.join(EXAMPLES, 'scenario-' + letter))
            self.assertEqual(got, want['hashes'], letter)
            report.append({'scenario': letter.upper(), 'anchors': len(got), 'equal': got == want['hashes']})
        # JCS of the same YAML text, in the browser (yaml, YAML 1.1) and in Python (claim_lint's PyYAML loader)
        texts = ['a: 1.0\nb: 1\nc: -0.0\nd: 1.5e+3\ne: 1.0e-7\nf: 0.000001\ng: 123456789012345678901234\nh: 1.0e+21\n',
                 'x: "\\u00e9\\u65e5\\u672c\\u0001\\t\\"\\\\ \\U0001F600"\n',
                 '{z: 1, "\\u00e9": 2, a: 3, "10": 4, "9": 5, "\\u20ac": 6, "\\U0001F600": 7, "\\uff61": 8, B: 9}\n',
                 'nest:\n  - {b: [1, {d: null, c: true}], a: false}\n  - []\n  - {}\n',
                 'k: yes\nl: on\nm: 012\nhex: 0x1f\no: 1:20\np: 1_000\nq: 2026-01-01\nr: ~\n',
                 'base: &b {u: 1}\nalias: *b\n',  # an alias; a merge key (<<) is an error in claim_lint's loader
                 # plain scalars read differently by YAML 1.1 readers: the editor follows PyYAML's resolver (R5)
                 'i: y\nj: 1e3\nn: 1\nY: N\nk2: 1.0e3\nk3: 1.0E+3\nk4: .5\nk5: 0.\nk6: -.5\nk7: +.5\nk8: 09\nk9: 0b101\nka: 10:30\n'
                 'kb: 1:70\nkc: -1:20.5\nkd: 1_000.5\nke: 0o7\nkf: Off\nkg: NO\nkh: 1.\nki: 0_1\nkj: 0x_1F\n']
        for t in texts:
            js = pg.evaluate('t => ClaimsEditor.canonicalYaml(t)', t)
            py = row_hash.jcs(yaml.load(t, Loader=_Loader))
            self.assertEqual(js, py, t)
        # a lone surrogate: not I-JSON, refused on both sides; a pair written as two escapes is one character on both
        lone = 'x: "\\ud800"\n'
        self.assertIn('lone surrogate', pg.evaluate('t => { try { return ClaimsEditor.canonicalYaml(t); } catch (e) { return String(e.message); } }', lone))
        with self.assertRaises(ValueError):
            row_hash.jcs(yaml.load(lone, Loader=_Loader))
        pair = 'x: "\\ud83d\\ude00"\n'
        self.assertEqual(pg.evaluate('t => ClaimsEditor.canonicalYaml(t)', pair), row_hash.jcs(yaml.load(pair, Loader=_Loader)))
        if EVIDENCE:
            with open(os.path.join(ROOT, EVIDENCE, 'row-hash-parity.json'), 'w', encoding='utf-8', newline='\n') as f:
                json.dump({'what': 'ClaimsEditor.rowHash (browser) vs python tools/row_hash.py, RFC 8785 JCS + SHA-256',
                           'results': report, 'jcs_vectors_equal': len(texts),
                           'yaml11': 'the editor reads plain scalars with the rules of PyYAML (claim_lint): y/n, 1e3, 1.0e3, 09 are strings, '
                                     'yes/no/on/off booleans, 012 octal, 10:30 sexagesimal; they also get a YAML11 warning',
                           'lone_surrogate': 'refused by both (RFC 8785 works on I-JSON)'},
                          f, ensure_ascii=False, indent=1)
                f.write('\n')
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ no data leaves the browser
    def test_network_only_same_origin_gets_and_csp_blocks_sends(self):
        pg = self.open(accept_downloads=True)
        initial = list(pg.requests)
        violations = []
        pg.expose_function('reportViolation', lambda v: violations.append(v))
        pg.evaluate('''() => document.addEventListener('securitypolicyviolation',
            e => window.reportViolation({directive: e.violatedDirective, blocked: e.blockedURI}))''')
        steps = []
        self.sample(pg, 'b'); steps.append('open sample B')
        self.go(pg, '#/lint', '問題'); steps.append('open the lint screen (loads Pyodide and claim_lint)')
        self.lint_fresh(pg); steps.append('claim_lint ran')
        pg.evaluate('() => ClaimsEditor.replaceText("claims.yaml", "claims:", "claims:  # edited")')
        self.poll(pg, '() => ClaimsEditor.state().lint !== "fresh"', timeout=5)
        self.lint_fresh(pg); steps.append('edit claims.yaml; claim_lint ran again')
        menu_check(pg, True); steps.append('enable autosave')
        with pg.expect_download():
            menu_click(pg, '#btn-export-zip')
        steps.append('export as zip')
        for h in ('#/claims', '#/ledger', '#/profile', '#/lifecycle', '#/catalog'):
            self.go(pg, h)
        steps.append('visit the preview screens')
        session = list(pg.requests)
        # a script that tries to send to another origin: a receiver on another port records every request it gets
        hits = []

        class Receiver(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _hit(self):
                hits.append({'method': self.command, 'path': self.path})
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
            do_GET = do_POST = do_PUT = do_OPTIONS = _hit
        rcv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), Receiver)
        rcv.daemon_threads = True
        threading.Thread(target=rcv.serve_forever, daemon=True).start()
        self.addCleanup(rcv.shutdown)
        other = f'127.0.0.1:{rcv.server_address[1]}'
        ws_events = []
        pg.on('websocket', lambda w: ws_events.append(w.url))
        before = len(pg.requests)
        attempts = pg.evaluate('''async (other) => {
            const out = {};
            try { await fetch(`http://${other}/fetch`, {method: 'POST', body: 'x'}); out.fetch = 'sent'; } catch (e) { out.fetch = 'refused'; }
            try { out.beacon_queued = navigator.sendBeacon(`http://${other}/beacon`, 'x'); } catch (e) { out.beacon_queued = 'refused'; }
            try { const w = new WebSocket(`ws://${other}/ws`); out.websocket = await new Promise((r) => { w.onopen = () => r('open'); w.onerror = () => r('error (no connection)'); setTimeout(() => r('no event'), 3000); }); } catch (e) { out.websocket = 'refused'; }
            const img = new Image(); img.src = `http://${other}/img`; document.body.append(img);
            const f = document.createElement('form'); f.method = 'post'; f.action = `http://${other}/form`; f.target = '_blank'; document.body.append(f);
            try { f.submit(); out.form = 'submitted'; } catch (e) { out.form = 'refused'; }
            // the worker is started like the claim_lint worker (blob:): it inherits this CSP
            const src = `fetch('http://${other}/worker', {method: 'POST', body: 'x'}).then(() => postMessage('sent'), () => postMessage('refused'));`;
            const w = new Worker(URL.createObjectURL(new Blob([src], { type: 'text/javascript' })));
            out.worker_fetch = await new Promise((r) => { w.onmessage = (e) => r(e.data); });
            return out; }''', other)
        pg.wait_for_timeout(1500)
        self.assertEqual(hits, [], 'the receiver on another origin got a request')
        self.assertEqual((attempts['fetch'], attempts['worker_fetch']), ('refused', 'refused'))
        self.assertNotEqual(attempts['websocket'], 'open')
        self.assertEqual(ws_events, [])
        # Playwright reports the <img> request as started; the CSP stops it before anything is sent (the receiver got none)
        attempt_requests = pg.requests[before:]
        blocked = {(v['directive'], v['blocked'].split('/')[2] if '//' in v['blocked'] else v['blocked']) for v in violations}
        for d in ('connect-src', 'img-src', 'form-action'):
            self.assertIn((d, other), blocked, violations)
        everything = initial + session
        bad = [r for r in everything if r['method'] != 'GET' or not (r['url'].startswith(self.origin + '/') or r['url'].startswith('blob:' + self.origin))
               or r['type'] in ('ping', 'beacon', 'websocket', 'eventsource')]
        self.assertEqual(bad, [])
        self.assertTrue(any('pyodide.asm.wasm' in r['url'] for r in session))
        self.assertTrue({v['directive'] for v in violations} <= {'connect-src', 'img-src', 'form-action'}, violations)
        if EVIDENCE:
            o = lambda u: u.replace(self.origin, '<origin>')  # noqa: E731
            with open(os.path.join(ROOT, EVIDENCE, 'network-log.json'), 'w', encoding='utf-8', newline='\n') as f:
                json.dump({
                    'what': 'Playwright (Chromium) network log of the design editor (#49), every request of the page and its '
                            'workers (BrowserContext request events), tools/tests/test_claims_editor_ui.py::'
                            'test_network_only_same_origin_gets_and_csp_blocks_sends',
                    'page': 'docs/claims/index.html served by a local HTTP server (as GitHub Pages serves docs/)',
                    'browser': f'chromium {self.browser.version}',
                    'csp': pg.get_attribute('meta[http-equiv="Content-Security-Policy"]', 'content'),
                    'steps': steps,
                    'summary': {'requests': len(everything), 'methods': sorted({r['method'] for r in everything}),
                                'origins': sorted({r['url'].split('/', 3)[2] if '://' in r['url'] else r['url'].split(':')[0] for r in everything}),
                                'non_get_or_cross_origin_or_beacon': len(bad)},
                    'initial_load_requests': [dict(r, url=o(r['url'])) for r in initial],
                    'session_requests': [dict(r, url=o(r['url'])) for r in session],
                    'send_attempts': {'receiver': 'an HTTP server on another port of 127.0.0.1 that records every request (another origin)',
                                      'tried': ['fetch POST', 'navigator.sendBeacon', 'WebSocket', '<img>', 'form.submit() POST',
                                                'fetch POST from a blob: worker (as the claim_lint worker)'],
                                      'results_in_the_page': attempts, 'requests_received_by_the_receiver': hits,
                                      'websocket_events_seen_by_playwright': ws_events},
                    'requests_playwright_saw_start_during_the_attempts': [dict(r, url=o(r['url'])) for r in attempt_requests],
                    'csp_violations': [dict(v, blocked=o(v['blocked'])) for v in violations],
                }, f, ensure_ascii=False, indent=1)
                f.write('\n')

    def test_without_wasm_unsafe_eval_pyodide_does_not_start(self):
        # why the CSP has 'wasm-unsafe-eval': the same page without it cannot compile Pyodide's WebAssembly
        ctx = self.browser.new_context()
        self.addCleanup(ctx.close)
        html = open(os.path.join(DOCS, 'claims', 'index.html'), encoding='utf-8').read().replace(" 'wasm-unsafe-eval'", '')
        ctx.route(self.base, lambda route: route.fulfill(status=200, content_type='text/html; charset=utf-8', body=html))
        pg = ctx.new_page()
        msgs = []
        pg.on('console', lambda m: msgs.append(m.text))
        pg.goto(self.base)
        pg.wait_for_selector('#btn-sample-a')
        self.sample(pg, 'a')
        try:
            self.go(pg, '#/lint', '問題')
            end = time.time() + 40  # with the policy, Pyodide is ready in about 3 s here
            st = None
            while time.time() < end:
                st = pg.evaluate('() => ClaimsEditor.state().lint')
                if st in ('error', 'fresh'):
                    break
                time.sleep(0.2)
            self.assertIn(st, ('error', 'loading'))  # never ready
        except Exception as e:  # Chromium may also end the renderer when the wasm compile is refused
            self.assertIn('crash', str(e).lower())

    # ------------------------------------------------------------------ first-load size and time (README)
    def test_measure_first_load(self):
        import gzip
        ctx = self.browser.new_context(viewport={'width': 1500, 'height': 950})
        self.addCleanup(ctx.close)
        pg = ctx.new_page()
        got = []
        ctx.on('requestfinished', lambda r: got.append(r.url))

        def phase(urls):
            files = []
            for u in urls:
                if not u.startswith(self.base):
                    continue
                rel = u[len(self.base):].split('?')[0].split('#')[0] or 'index.html'
                with open(os.path.join(DOCS, 'claims', *rel.split('/')), 'rb') as f:
                    data = f.read()
                files.append({'file': rel, 'bytes': len(data), 'gzip_bytes': len(gzip.compress(data, 6, mtime=0))})
            return {'requests': len(files), 'bytes': sum(f['bytes'] for f in files), 'gzip_bytes': sum(f['gzip_bytes'] for f in files), 'files': files}

        t0 = time.time()
        pg.goto(self.base)
        pg.wait_for_selector('#btn-sample-a')
        empty_ms = round((time.time() - t0) * 1000)
        nav = pg.evaluate('() => { const n = performance.getEntriesByType("navigation")[0]; return {dcl: Math.round(n.domContentLoadedEventEnd), load: Math.round(n.loadEventEnd)}; }')
        p_empty = phase(list(got)); got.clear()
        t0 = time.time()
        pg.click('#btn-sample-b')
        self.poll(pg, '() => ClaimsEditor.state().open && document.querySelector("main h1")')
        sample_ms = round((time.time() - t0) * 1000)
        p_sample = phase(list(got)); got.clear()
        t0 = time.time()
        pg.evaluate('h => { location.hash = h; }', '#/lint')
        last = self.lint_fresh(pg)
        lint_ms = round((time.time() - t0) * 1000)
        info = pg.evaluate('() => ClaimsEditor.lintInfo')
        p_lint = phase(list(got)); got.clear()
        pg.evaluate('() => ClaimsEditor.replaceText("hops.yaml", "hops:", "hops:  # edited")')
        self.poll(pg, '() => ClaimsEditor.state().lint !== "fresh"', timeout=5)
        again = self.lint_fresh(pg)
        m = {
            'what': 'first-load size and time of the design editor (#49), tools/tests/test_claims_editor_ui.py::test_measure_first_load',
            'setup': f'headless chromium {self.browser.version}, local HTTP server (python http.server, no compression, no network latency), '
                     'cold cache. bytes = file sizes; gzip_bytes = gzip -6 of each file (about what GitHub Pages sends when it compresses)',
            'empty_page': dict(p_empty, ms_to_start_screen=empty_ms, navigation=nav),
            'open_sample_b': dict(p_sample, ms_to_preview=sample_ms),
            'claim_lint_first_use': dict(p_lint, ms_to_first_result=lint_ms, pyodide_ready_ms=info['loadMs'], first_lint_ms=last['ms']),
            'claim_lint_after_an_edit_ms': again['ms'],
        }
        if EVIDENCE:
            with open(os.path.join(ROOT, EVIDENCE, 'load-measurements.json'), 'w', encoding='utf-8', newline='\n') as f:
                json.dump(m, f, ensure_ascii=False, indent=1)
                f.write('\n')
        self.assertLess(p_empty['bytes'], 1_200_000)  # the empty page does not load Pyodide or a sample
        self.assertFalse([f for f in p_empty['files'] if 'pyodide' in f['file'] or 'sample' in f['file']])
        self.assertTrue(any('pyodide.asm.wasm' in f['file'] for f in p_lint['files']))

    # ------------------------------------------------------------------ other
    def test_opens_from_a_file_url(self):
        # a reader who downloads the repository opens docs/claims/index.html directly (no server): editing and the
        # schema check work; claim_lint needs HTTP and says so
        ctx = self.browser.new_context()
        self.addCleanup(ctx.close)
        pg = ctx.new_page()
        problems = []
        pg.on('pageerror', lambda e: problems.append(str(e)))
        pg.on('console', lambda m: problems.append(m.text) if m.type == 'error' else None)
        pg.goto(pathlib.Path(DOCS, 'claims', 'index.html').as_uri())
        pg.click('#btn-sample-a')
        self.poll(pg, '() => ClaimsEditor.state().open', timeout=10)
        self.go(pg, '#/lint', '問題')
        self.poll(pg, '() => ClaimsEditor.state().lint === "unavailable"', timeout=5)
        self.assertEqual(problems, [])

    def test_narrow_screen(self):
        pg = self.open(width=380)
        self.assertLessEqual(pg.evaluate('document.documentElement.scrollWidth'), 380 + 1)
        self.sample(pg, 'a')
        self.go(pg, '#/claim/C-iss', '(C-iss)')
        self.assertLessEqual(pg.evaluate('document.documentElement.scrollWidth'), 380 + 1)
        self.shot(pg, '40_narrow')

    def test_trace_counts(self):
        reqs = load_yaml('templates/trace/requirements.yaml')['requirements']
        pg = self.open()
        self.sample(pg, 'a')
        self.go(pg, '#/trace', '対応表')
        row = pg.locator('table[data-table="trace-tier"] tbody tr').filter(has_text='core').first.inner_text()
        done = sum(r['tier'] == 'core' and r['status'] == '実装済み' for r in reqs)
        total = sum(r['tier'] == 'core' for r in reqs)
        self.assertIn(f'（{done} / {total}）', row)


if __name__ == '__main__':
    unittest.main()
