# -*- coding: utf-8 -*-
"""The way through the design editor (docs/claims/, #53) in headless Chromium: open -> see -> fix -> review.

  pip install playwright && python -m playwright install chromium
  python -m pytest -q tools/tests/test_claims_editor_ux.py
  CLAIMS_EDITOR_UX_SHOTS=research/claims-editor/ux-2026-11-24 python -m pytest -q tools/tests/test_claims_editor_ux.py
      # also save the screenshots at 900px and 1280px

Skipped when Playwright or its browser is not installed (as test_claims_editor_ui.py). One test per criterion of #53:
  two builds served one after the other to a browser that keeps its HTTP cache (Cache-Control: max-age=600, as GitHub
  Pages): no exception, a banner when the files of two builds are read together, the review works after the reload;
  each kind of file opened alone shows its screen first, several show the dashboard; the screens of a file that is not
  open are dimmed and offer to add it; the dashboard lists what needs doing and links to it; a review is started in
  three actions from the first screen, through a stepper; no issue number, file path or internal jargon in the words
  of the screens; the editor and the menu fold on a narrow window.
"""
import functools
import http.server
import os
import re
import shutil
import socketserver
import sys
import tempfile
import threading
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS = os.path.join(ROOT, 'docs')
VIEWER = os.path.join(DOCS, 'claims')
EXAMPLES = os.path.join(ROOT, 'templates', 'examples')
SHOTS = os.environ.get('CLAIMS_EDITOR_UX_SHOTS')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import build_claims_viewer as bcv  # noqa: E402
try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

# words of the implementation that a reader new to the guide does not know: not in headings, buttons or the menu
JARGON = ['CSP', 'connect-src', 'worker', 'Worker', 'Pyodide', 'rowHash', 'hash', 'ハッシュ', 'stale', 'tier', 'profile', 'claim_lint',
          'render', 'bundle', 'registry', 'anchor', 'lint', 'PR', 'JSON Schema', 'YAML のまま', 'レビューモード',
          # the words that #67 replaces on the screens (templates/glossary.md has the table): 台帳 -> クレーム一覧, ホップ -> 経路,
          # 観点 -> 確認事項, 検査の結果 -> 問題, 出どころ -> 元データ; 縮小 Lite and 正本 are not shown
          '台帳', 'ホップ', '観点', '検査の結果', '出どころ', '縮小 Lite', '正本']
# （「概要」 was in this list while it named the dashboard; #67 asks for a tab 「概要」 on the claim detail screen）
# words of the body text that templates/glossary.md 5.1 replaces (the re-check of PR #72): 指摘 is a reviewer's word (the
# checks give 問題), the levels are エラー・警告・情報, and the screens do not say which tool is the authority
BODY_DENY = [re.compile(r'指摘はありません'), re.compile(r'検査の正'), re.compile(r'(?<![A-Za-z_])(?:error|warn|info) \d')]
FILE_IN_HEADING = re.compile(r'[A-Za-z0-9_*.-]+\.(?:ya?ml|md|json|js)\b|templates/|tools/')
# the rendered text of the page (visible text nodes), leaving out the labelled links to GitHub and a file shown as it is
RENDERED = '''() => {
  const out = [];
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = w.nextNode())) {
    const el = n.parentElement;
    if (!el || !n.textContent.trim()) continue;
    if (el.closest('script,style,[hidden],dialog:not([open])')) continue;
    if (el.closest('a[href^="https://github.com/"]') || el.closest('[data-file-preview]')) continue;
    if (el.checkVisibility && !el.checkVisibility()) continue;
    out.push(n.textContent);
  }
  return out.join(' ');
}'''
# the same, without the text that comes from the design document (sectionBlock of preview.js: data-design-text)
RENDERED_UI = RENDERED.replace("el.closest('[data-file-preview]')", "el.closest('[data-file-preview]') || el.closest('[data-design-text]')")
LABELS = '''() => {
  const pick = (sel) => Array.from(document.querySelectorAll(sel)).filter((e) => !e.closest('[hidden]') && (!e.checkVisibility || e.checkVisibility()))
    .filter((e) => !e.closest('.rv-q h3, [data-see], [data-anchor], table'))
    .map((e) => { const c = e.cloneNode(true); c.querySelectorAll('code,.small,.muted,.vh').forEach((x) => x.remove()); return [e.tagName, c.textContent.trim()]; });
  return pick('main h1, main h2, main h3, #start h1, #start h2, .top button, .top summary, main button, #start button, #nav a, #nav li.sep, main summary, main legend, '
    + '#review-bar button, #problems button, #problems th, .menu-items button, .menu-items label, dialog[open] h2, dialog[open] button, dialog[open] legend, dialog[open] label');
}'''


class _Server(http.server.SimpleHTTPRequestHandler):
    root = DOCS
    fail = set()
    cache = None

    def __init__(self, *a, **k):
        super().__init__(*a, directory=type(self).root, **k)

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.split('?')[0] in type(self).fail:
            self.send_error(503)
            return
        super().do_GET()

    def send_response(self, code, message=None):
        self._code = code
        super().send_response(code, message)

    def end_headers(self):
        if type(self).cache and getattr(self, '_code', 0) == 200:  # GitHub Pages caches what it serves; an error is not kept
            self.send_header('Cache-Control', type(self).cache)
        super().end_headers()


@unittest.skipIf(sync_playwright is None, 'playwright not installed')
class EditorUX(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.handler = type('H', (_Server,), {'root': DOCS, 'fail': set(), 'cache': None})
        cls.srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), cls.handler)
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
        if SHOTS:
            os.makedirs(os.path.join(ROOT, SHOTS), exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.srv.shutdown()

    def setUp(self):
        self.handler.root, self.handler.fail, self.handler.cache = DOCS, set(), None

    # ------------------------------------------------------------------ helpers
    def watch(self, pg):
        pg.problems = []
        pg.on('pageerror', lambda e: pg.problems.append('pageerror: ' + str(e)))
        pg.on('console', lambda m: pg.problems.append(f'console {m.type}: {m.text}') if m.type in ('error', 'warning') else None)
        return pg

    def open(self, width=1280, height=900):
        ctx = self.browser.new_context(viewport={'width': width, 'height': height})
        self.addCleanup(ctx.close)
        pg = self.watch(ctx.new_page())
        pg.goto(self.base)
        pg.wait_for_selector('#btn-sample-a')
        return pg

    def poll(self, pg, js, timeout=20, arg=None):
        end = time.time() + timeout
        while time.time() < end:
            v = pg.evaluate(js, arg) if arg is not None else pg.evaluate(js)
            if v:
                return v
            time.sleep(0.1)
        self.fail(f'timed out waiting for {js}')

    def h1(self, pg, text, timeout=10):
        self.poll(pg, 't => ((document.querySelector("main h1") || {}).textContent || "").includes(t)', arg=text, timeout=timeout)

    def go(self, pg, hash_, h1=None):
        pg.evaluate('h => { location.hash = h; }', hash_)
        if h1:
            self.h1(pg, h1)
        else:
            pg.wait_for_timeout(200)

    def shot(self, pg, name):
        if SHOTS:
            pg.screenshot(path=os.path.join(ROOT, SHOTS, name + '.png'), full_page=False)

    def files_of(self, letter, *names):
        return [os.path.join(EXAMPLES, 'scenario-' + letter, n) for n in names]

    def open_files(self, pg, paths):
        pg.set_input_files('#in-files', paths)
        self.poll(pg, '() => ClaimsEditor.state().open && document.querySelector("main h1")')

    # ------------------------------------------------------------------ 1. two builds and a browser cache
    def _two_builds(self, tmp):
        """v1: the editor of this tree with a changed editor.js, preview.js and review.js (a build before), re-stamped;
        v2: the editor as committed. Copied without their times, v2 after v1 (newer files, as a deploy)."""
        v1 = os.path.join(tmp, 'v1')
        shutil.copytree(VIEWER, os.path.join(v1, 'claims'), copy_function=shutil.copy)
        for n in ('editor.js', 'preview.js', 'review.js'):
            with open(os.path.join(v1, 'claims', n), 'a', encoding='utf-8', newline='\n') as f:
                f.write('\n// the build before (tools/tests/test_claims_editor_ux.py)\n')
        id1 = bcv.stamp_dir(os.path.join(v1, 'claims'))
        time.sleep(1.2)
        v2 = os.path.join(tmp, 'v2')
        shutil.copytree(VIEWER, os.path.join(v2, 'claims'), copy_function=shutil.copy)
        id2 = bcv.MARK_JS.search(open(os.path.join(VIEWER, 'data', 'build.js'), encoding='utf-8').read()).group(2)
        self.assertNotEqual(id1, id2)
        return v1, v2, id1, id2

    def _review_works(self, pg, name):
        pg.click('#btn-sample-a')
        self.poll(pg, '() => ClaimsEditor.state().open && window.ClaimsReview && ClaimsReview.ready()')
        pg.click('#btn-start-review')
        pg.fill('#rv-name', name)
        pg.click('#rv-start-go')
        self.poll(pg, 'n => ClaimsReview.me() === n', arg=name)
        self.h1(pg, '確認事項')  # a first review starts on the questions
        self.go(pg, '#/review/checklist', '確認事項')
        qid = pg.evaluate('() => document.querySelector(".rv-q").dataset.q')
        pg.check(f'.rv-q[data-q="{qid}"] input[value="yes"]')
        self.poll(pg, 'q => ClaimsReview.data().reviews.some(r => r.answers[q])', arg=qid)
        self.assertTrue(pg.locator('#nav a[data-view="review/checklist"]').count())

    def test_two_builds_in_a_row_with_the_browser_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            v1, v2, id1, id2 = self._two_builds(tmp)
            self.handler.cache = 'max-age=600'  # what GitHub Pages sends
            # (a) a reload after the deploy: the page is checked again, every URL is new, nothing old is mixed in
            self.handler.root = v1
            ctx = self.pw.chromium.launch_persistent_context(os.path.join(tmp, 'profile-a'), headless=True, viewport={'width': 1280, 'height': 900})
            try:
                pg = self.watch(ctx.new_page())
                pg.goto(self.base)
                pg.wait_for_selector('#btn-sample-a')
                self.assertEqual(pg.evaluate('() => window.CLAIMS_BUILD["editor.js"]'), id1)
                self._review_works(pg, '一つ目の版の人')
                self.handler.root = v2
                pg.reload()
                pg.wait_for_selector('#btn-sample-a')
                self.assertEqual(pg.evaluate('() => Object.values(window.CLAIMS_BUILD)'), [id2] * len(pg.evaluate('() => Object.values(window.CLAIMS_BUILD)')))
                self.assertFalse(pg.locator('#build-banner').count())
                self._review_works(pg, '二つ目の版の人')
                self.assertEqual(pg.problems, [])
            finally:
                ctx.close()
            # (b) the case of #53: index.html and editor.js of the build before still in the cache, review.js not
            # (it failed to load then), and the server has the new build: the files of two builds meet
            self.handler.root, self.handler.fail = v1, {'/claims/review.js'}
            ctx = self.pw.chromium.launch_persistent_context(os.path.join(tmp, 'profile-b'), headless=True, viewport={'width': 1280, 'height': 900})
            try:
                first = ctx.new_page()
                first.goto(self.base)
                first.wait_for_selector('#btn-sample-a')
                first.close()
                self.handler.root, self.handler.fail = v2, set()
                pg = self.watch(ctx.new_page())
                pg.goto(self.base)
                pg.wait_for_selector('#build-banner', timeout=10000)
                builds = pg.evaluate('() => window.CLAIMS_BUILD')
                self.assertEqual((builds['editor.js'], builds['review.js']), (id1, id2))  # really mixed
                self.assertIn('新しい版が公開されました。再読み込みしてください', pg.inner_text('#build-banner'))
                self.assertEqual(pg.get_attribute('#build-banner', 'role'), 'alert')
                self.shot(pg, '90_build_banner')
                self.assertEqual(pg.problems, [])  # no TypeError: review.js of the new build stops before using the old editor
                pg.click('#build-reload')
                pg.wait_for_selector('#btn-sample-a')
                self.poll(pg, 'id => Object.values(window.CLAIMS_BUILD).every(x => x === id)', arg=id2)
                self.assertFalse(pg.locator('#build-banner').count())
                self._review_works(pg, '再読み込みした人')
                self.assertEqual(pg.problems, [])
            finally:
                ctx.close()

    def test_a_data_file_of_another_build_is_not_used(self):
        # a sample from the server is of a newer build than the page: refused with the banner, not opened half way
        ctx = self.browser.new_context()
        self.addCleanup(ctx.close)
        pg = self.watch(ctx.new_page())
        stale = open(os.path.join(VIEWER, 'data', 'sample-a.js'), encoding='utf-8').read()
        stale = bcv.MARK_JS.sub(lambda m: m.group(1) + '0' * bcv.HASH_LEN + m.group(3), stale)
        ctx.route('**/data/sample-a.js*', lambda r: r.fulfill(status=200, content_type='text/javascript', body=stale))
        pg.goto(self.base)
        pg.wait_for_selector('#btn-sample-a')
        pg.click('#btn-sample-a')
        pg.wait_for_selector('#build-banner')
        self.poll(pg, '() => document.querySelector("#start-msg").textContent.includes("別の版")')
        self.assertFalse(pg.evaluate('() => ClaimsEditor.state().open'))
        self.assertEqual([x for x in pg.problems if 'pageerror' in x], [])

    def test_every_url_carries_its_content_hash(self):
        ctx = self.browser.new_context()
        self.addCleanup(ctx.close)
        urls = []
        ctx.on('request', lambda r: urls.append(r.url))
        pg = self.watch(ctx.new_page())
        pg.goto(self.base)
        pg.wait_for_selector('#btn-sample-a')
        pg.click('#btn-sample-b')
        self.poll(pg, '() => ClaimsEditor.state().open && ClaimsReview.ready()')
        self.go(pg, '#/lint')
        self.poll(pg, '() => ClaimsEditor.state().lint === "fresh"', timeout=120)
        mine = [u[len(self.base):] for u in urls if u.startswith(self.base) and u != self.base]
        ours = [u for u in mine if not u.startswith('vendor/pyodide/') or u.startswith('vendor/pyodide/pyodide.js')]
        self.assertTrue(ours)
        self.assertEqual([u for u in ours if '?v=' not in u], [])
        for u in ours:
            path, v = u.split('?v=')
            self.assertEqual(v, bcv.short_hash(open(os.path.join(VIEWER, *path.split('/')), 'rb').read().replace(b'\r\n', b'\n')
                                               if not path.startswith('vendor/') and not path.endswith('.zip') else open(os.path.join(VIEWER, *path.split('/')), 'rb').read()), u)
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ 2. the first screen follows the file
    def test_the_first_screen_follows_the_opened_file(self):
        cases = [('claims.yaml', 'クレーム一覧', 'claims'), ('token_types.yaml', 'トークン目録', 'tokens'), ('hops.yaml', '経路の一覧', 'hops'),
                 ('catalog_answers.yaml', 'カタログへの回答', 'catalog')]
        for name, title, route in cases:
            pg = self.open()
            self.open_files(pg, self.files_of('a', name))
            self.h1(pg, title)
            self.assertEqual(pg.evaluate('() => location.hash'), '#/' + route, name)
            self.assertEqual(pg.problems, [], name)
            if name in ('claims.yaml', 'token_types.yaml'):
                for w in (900, 1280):
                    pg.set_viewport_size({'width': w, 'height': 900})
                    pg.wait_for_timeout(200)
                    self.shot(pg, f'{w}_02_open_{name.split(".")[0]}')
        # review.yaml alone: the review
        pg = self.open()
        self.open_files(pg, self.files_of('b', 'review.yaml'))
        self.poll(pg, '() => location.hash === "#/review" && ClaimsReview.ready()')
        self.h1(pg, 'レビュー')
        self.assertEqual(pg.evaluate('() => ClaimsReview.visibleNames().length'), 1)
        self.assertEqual(pg.evaluate('() => ClaimsEditor.state().designRel'), 'templates/examples/scenario-b')
        self.assertTrue(pg.is_visible('#rv-begin'))  # the rows to review, with the button that starts
        self.assertEqual(pg.problems, [])
        # several files: the dashboard
        pg = self.open()
        self.open_files(pg, self.files_of('a', 'claims.yaml', 'hops.yaml'))
        self.h1(pg, 'ダッシュボード')
        self.assertEqual(pg.evaluate('() => location.hash'), '#/dashboard')
        self.assertEqual(pg.problems, [])

    def test_screens_of_a_file_not_open_are_dimmed_and_offer_to_add_it(self):
        pg = self.open()
        self.open_files(pg, self.files_of('a', 'claims.yaml'))
        dim = pg.eval_on_selector_all('#nav a.nofile', 'els => els.map(e => e.dataset.view)')
        self.assertEqual(sorted(dim), sorted(['tokens', 'profile', 'lifecycle', 'hops', 'catalog']))
        self.assertFalse(pg.locator('#nav a.nofile[data-view="claims"]').count())
        self.assertIn('まだ開いていない', pg.text_content('#nav a[data-view="tokens"]'))
        self.go(pg, '#/tokens', 'トークン目録')
        self.assertTrue(pg.is_visible('[data-nofile="token_types.yaml"]'))
        self.assertIn('まだ開いていません', pg.inner_text('main'))
        with pg.expect_file_chooser() as fc:
            pg.click('#btn-nofile-add')
        fc.value.set_files(self.files_of('a', 'token_types.yaml'))
        self.poll(pg, '() => ClaimsEditor.state().files.includes("token_types.yaml")')
        self.go(pg, '#/tokens', 'トークン目録')
        self.poll(pg, '() => !document.querySelector("main [data-nofile]") && document.querySelector("main table")')
        self.assertFalse(pg.locator('#nav a.nofile[data-view="tokens"]').count())
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ 3. the dashboard
    def test_the_dashboard_lists_what_needs_doing_and_links_to_it(self):
        pg = self.open()
        pg.click('#btn-sample-b')
        self.poll(pg, '() => ClaimsEditor.state().open && ClaimsReview.ready()')
        self.h1(pg, 'ダッシュボード')
        self.assertEqual(pg.evaluate('() => location.hash'), '#/dashboard')
        # an error and a row changed after its review
        pg.evaluate('() => ClaimsEditor.replaceText("claims.yaml", "  - id: C-iss\\n", "  - id: C-iss\\n    x_bogus: 1\\n")')
        self.poll(pg, '() => document.querySelector("#dash-todo [data-todo-kind=error]") && document.querySelector("#dash-todo [data-todo-kind=stale]")')
        self.assertIn('claims:C-iss', pg.inner_text('#dash-todo [data-todo-kind=stale]'))
        self.assertTrue(pg.locator('#dash-counts a[data-dash="claims"]').count())
        self.assertTrue(pg.is_visible('#dash-lint'))
        self.assertTrue(pg.is_visible('[data-dash-summary="review"]'))
        for w in (900, 1280):
            pg.set_viewport_size({'width': w, 'height': 900})
            pg.wait_for_timeout(200)
            self.shot(pg, f'{w}_03_dashboard')
        pg.click('#dash-todo [data-todo-kind=stale] a')
        self.h1(pg, '(C-iss)')
        self.go(pg, '#/dashboard', 'ダッシュボード')
        pg.click('#dash-todo [data-todo-kind=error] a')
        self.h1(pg, '(C-iss)')
        self.go(pg, '#/dashboard', 'ダッシュボード')
        pg.click('#dash-counts a[data-dash="claims"]')
        self.h1(pg, 'クレーム一覧')
        # the comments of a review that are not resolved, and the progress once a review is going on
        self.go(pg, '#/dashboard', 'ダッシュボード')
        pg.click('#dash-todo [data-todo-kind=question] a')
        self.h1(pg, 'コメント')
        pg.click('#btn-start-review')
        pg.fill('#rv-name', 'ダッシュボードの人')
        pg.click('#rv-start-go')
        self.poll(pg, '() => ClaimsReview.me()')
        self.go(pg, '#/dashboard', 'ダッシュボード')
        self.assertIn('ダッシュボードの人：確認済み 0 /', pg.inner_text('[data-dash-summary="review"]'))
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ 4. the review: three actions, a stepper
    def test_a_review_is_started_in_three_actions(self):
        pg = self.open()
        pg.click('#btn-sample-a')
        self.poll(pg, '() => ClaimsEditor.state().open && ClaimsReview.ready()')
        for w in (900, 1280):
            pg.set_viewport_size({'width': w, 'height': 900})
            pg.wait_for_timeout(150)
            self.shot(pg, f'{w}_04_after_sample')
        pg.set_viewport_size({'width': 1280, 'height': 900})
        # 1. 「レビューを開始」 in the top bar, 2. the name, 3. 「レビューを開始」 of the dialog
        pg.click('#btn-start-review')
        pg.wait_for_selector('#rv-start[open]')
        pg.fill('#rv-name', '三回で始める人')
        pg.click('#rv-start-go')
        self.poll(pg, '() => ClaimsReview.me() === "三回で始める人"')
        self.h1(pg, '確認事項')  # the questions first, then the required rows
        # recording works from here, on the screens of the design too
        self.go(pg, '#/claim/C-iss', '(C-iss)')
        pg.click('[data-review-panel="claims:C-iss"] [data-viewed="claims:C-iss"]')
        self.poll(pg, '() => ClaimsReview.data().reviews.find(r => r.reviewer.name === "三回で始める人").viewed["claims:C-iss"]')
        self.assertEqual(pg.problems, [])

    def test_the_checklist_follows_the_data(self):
        # which questions are shown is decided by data/review.js (the class of each question, its conditions and its
        # priority: templates/review/triage.yaml of #56), not by the screen
        pg = self.open()
        pg.click('#btn-sample-a')
        self.poll(pg, '() => ClaimsEditor.state().open && ClaimsReview.ready()')
        n = pg.evaluate('''() => { const R = window.CLAIMS_VIEWER_DATA.review;
          R.questions.forEach((q, i) => { q.triage = i < 5 ? 'C' : i < 9 ? 'A' : 'B'; q.show_when = ['always']; q.priority = i < 3 ? 1 : i < 5 ? 3 : 2; });
          R.checklist.short = { priorities: [1, 2] }; return R.questions.length; }''')
        self.go(pg, '#/review/checklist', '確認事項')
        self.poll(pg, '() => document.querySelectorAll(".rv-q").length === 3')  # class C of a default priority
        self.assertEqual(pg.get_attribute('#rv-q-count', 'data-shown'), '3')
        pg.click('#rv-q-why summary')
        why = pg.inner_text('[data-table="hidden-reasons"]')
        self.assertIn('自動の検査で確かめる', why)
        self.assertIn('書き手が、提出の前に自分で確かめる', why)
        self.assertIn('優先 3', why)
        pg.click('#rv-q-all')
        self.poll(pg, 'n => document.querySelectorAll(".rv-q").length === n', arg=n)
        self.assertEqual(pg.problems, [])

    def test_the_checklist_shows_the_short_list_of_the_open_design_by_default(self):
        # #56: by default only the questions a reviewer answers (class C of templates/review/triage.yaml, priority 1,
        # a condition that holds for the open design or cannot be read) and the open prompts. The traits and the list
        # are the ones python tools/review_triage.py --design gives: the two samples and the two pilot designs
        sys.path.insert(0, os.path.join(ROOT, 'tools'))
        import review_triage as rt
        tri = rt.load(ROOT)
        counts = {}
        names = ('claims.yaml', 'token_types.yaml', 'hops.yaml', 'catalog_answers.yaml')
        designs = (('a', 'templates/examples/scenario-a', None), ('b', 'templates/examples/scenario-b', None),
                   ('pilot-b', 'research/pilot/scenario-b', names), ('pilot-c', 'research/pilot/scenario-c', names),
                   ('pilot-b without hops.yaml', 'research/pilot/scenario-b', names[:2] + names[3:]))
        # #58: scenario A with two IdPs declared as an array in catalog_answers.yaml (registry 0.3.0). Nothing else in
        # scenario A says "several IdPs", so the page and review_triage.py must both read the declaration
        two = tempfile.mkdtemp(prefix='claims-two-idps-')
        self.addCleanup(shutil.rmtree, two, True)
        for f in names:
            shutil.copy(os.path.join(ROOT, 'templates/examples/scenario-a', f), two)
        with open(os.path.join(two, 'catalog_answers.yaml'), encoding='utf-8') as f:
            text = f.read()
        old = 'idp:\n  name: keycloak\n  version: "26.8"\n'
        self.assertIn(old, text)
        with open(os.path.join(two, 'catalog_answers.yaml'), 'w', encoding='utf-8', newline='\n') as f:
            f.write(text.replace(old, 'idp:\n  - {name: keycloak, version: "26.8", token_types: [AT]}\n  - {name: entra, version: "v2.0", token_types: [IDT]}\n'))
        designs += (('a with two IdPs', two, names),)
        for key, d, files in designs:
            reg = rt.load_design(os.path.join(ROOT, d))
            if files and 'hops.yaml' not in files:
                reg['hops'] = None
            states = {c: v['state'] for c, v in rt.read_traits(reg).items()}
            have = rt.traits(reg)
            on = {c for c, v in states.items() if v == 'on'}
            pg = self.open()
            if files:
                self.open_files(pg, [os.path.join(ROOT, d, f) for f in files])
            else:
                pg.click(f'#btn-sample-{key}')
            self.poll(pg, '() => ClaimsEditor.state().open && ClaimsReview.ready()')
            self.go(pg, '#/review/checklist', '確認事項')
            self.assertEqual(pg.evaluate('() => ClaimsReview.traits()'), states, key)
            want = {q['id'] for q in rt.selected(tri, have)}
            optional = {q['id'] for q in tri['questions'] if q.get('show_on_lint')}   # shown when their lint rule warned
            self.poll(pg, 'n => document.querySelectorAll(".rv-q").length >= n && document.querySelector("#rv-short-note")', arg=len(want))
            got = set(pg.evaluate('() => Array.from(document.querySelectorAll(".rv-q")).map(e => e.dataset.q)'))
            self.assertTrue(want <= got and got - want <= optional, (key, got ^ want))
            self.assertEqual(pg.evaluate('() => Array.from(document.querySelectorAll("#rv-prompts [data-prompt]")).map(e => e.dataset.prompt)'),
                             [p['id'] for p in rt.default_prompts(tri, have, on)])
            sl = pg.evaluate('() => ClaimsReview.shortList()')
            self.assertEqual(set(sl['optional']), {q['id'] for q in rt.optional(tri, have)}, key)
            self.assertEqual(sl['prompts'] + sl['morePrompts'], [p['id'] for p in rt.prompts(tri, have, on)], key)
            self.assertIn(f'全 168 件のうち {len(got)} 件を表示', pg.inner_text('#rv-q-count'))
            self.assertIn(f'あなたが答える問い {len(got)} 件', pg.inner_text('#rv-short-note'))
            pg.click('#rv-q-why summary')
            reasons = dict(tuple(r) for r in pg.evaluate('''() => Array.from(document.querySelectorAll('[data-table="hidden-reasons"] tbody tr'))
              .map(tr => [tr.cells[0].textContent, Number(tr.cells[1].textContent)])'''))
            self.assertEqual(reasons[next(k for k in reasons if k.startswith('自動の検査で確かめる'))], 81)
            # the traits table: 当たる / 当たらない / 読めない, the same states as review_triage.py
            shown = {el.get_attribute('data-trait'): el.get_attribute('data-trait-value') for el in pg.locator('#rv-traits [data-trait]').all()}
            self.assertEqual(shown, {c: {'on': 'true', 'off': 'false', 'unknown': 'null'}[v] for c, v in states.items() if c != 'always'}, key)
            if 'unknown' in states.values():
                self.assertIn('読めない', pg.inner_text('#rv-traits'))
            # the rows a per-row question is answered for: the same draw as review_triage.py --seed
            if pg.locator('#rv-row-seed').count():
                pg.fill('#rv-row-seed', 'PR-72')
                self.assertEqual(pg.get_attribute('#rv-row-sample', 'data-rows').split(), rt.row_sample(tri, reg, 'PR-72')[0], key)
            counts[key] = len(want)
            if key == 'b':
                # "if time remains": the priority 2 questions and the other open prompts are one press away
                pg.click('#rv-q-more')
                self.poll(pg, 'n => document.querySelectorAll(".rv-q").length >= n', arg=len(want) + len(rt.optional(tri, have)))
                self.assertEqual(set(pg.evaluate('() => Array.from(document.querySelectorAll("[data-stage=more] .rv-q")).map(e => e.dataset.q)')),
                                 {q['id'] for q in rt.optional(tri, have)})
                self.assertEqual(pg.evaluate('() => document.querySelectorAll("#rv-prompts [data-prompt]").length'), len(rt.prompts(tri, have)))
                self.assertIn('more=1', pg.evaluate('() => location.hash'))
            if key == 'a':
                # the questions a machine or the author answers are one press away, and say who answers them
                pg.click('#rv-q-all')
                self.poll(pg, '() => document.querySelectorAll(".rv-q").length === 168')
                self.assertIn('L5', pg.locator('#q-dc-01 .rv-triage').text_content())
                self.assertIn('all=1', pg.evaluate('() => location.hash'))
            self.assertEqual(pg.problems, [])
            pg.close()
        self.assertNotEqual(counts['a'], counts['b'])
        self.assertGreater(counts['a with two IdPs'], counts['a'])
        self.assertGreaterEqual(counts['pilot-b without hops.yaml'], counts['pilot-b'])

    def test_a_review_can_be_recorded_from_the_short_list(self):
        # #56: the default view is enough to work in: answer a question of the short list (one sentence, with its hint
        # folded and its fields), and turn what an open prompt made the reviewer notice into a comment
        pg = self.open()
        pg.click('#btn-sample-b')
        self.poll(pg, '() => ClaimsEditor.state().open && ClaimsReview.ready()')
        pg.click('#btn-start-review')
        pg.fill('#rv-name', '短い一覧の人')
        pg.click('#rv-start-go')
        self.poll(pg, '() => ClaimsReview.me()')
        self.go(pg, '#/review/checklist', '確認事項')
        self.poll(pg, '() => document.querySelector("#rv-short-note")')
        self.assertTrue(pg.locator('#q-q-revocation-delivery').is_visible())
        self.assertIn('最悪で何分か', pg.inner_text('#q-q-revocation-delivery h3'))
        hint = pg.locator('#q-q-revocation-delivery .rv-hint')
        self.assertFalse(hint.locator('p').is_visible())  # folded
        hint.locator('summary').click()
        self.assertTrue(hint.locator('p').is_visible())
        self.assertTrue(pg.locator('#q-q-revocation-delivery [data-see]').count())
        self.assertEqual(pg.locator('#q-dc-01').count(), 0)
        pg.check('#q-q-revocation-delivery input[value="no"]')
        self.poll(pg, '() => ClaimsReview.data().reviews.some(r => r.answers["q-revocation-delivery"] && r.answers["q-revocation-delivery"].answer === "no")')
        pg.click('#rv-prompts [data-prompt="op-one-time"] button')
        self.poll(pg, '() => location.hash.startsWith("#/review/comments")')
        self.assertEqual(pg.problems, [])

    def test_the_start_screen_card_opens_files_for_a_review(self):
        pg = self.open()
        with pg.expect_file_chooser() as fc:
            pg.click('#btn-review')
        fc.value.set_files(self.files_of('b', 'claims.yaml', 'token_types.yaml', 'hops.yaml', 'catalog_answers.yaml', 'review.yaml'))
        self.poll(pg, '() => ClaimsEditor.state().open && ClaimsReview.ready() && document.querySelector("#rv-start[open]")')
        self.assertEqual(pg.evaluate('() => location.hash'), '#/review')
        self.assertEqual(pg.get_attribute('#rv-start-records', 'data-reviewers'), '1')
        self.assertEqual(pg.evaluate('() => ClaimsReview.visibleNames().length'), 1)  # review.yaml came with the files
        self.assertEqual(pg.problems, [])

    def test_autosaved_designs_come_first_as_continue(self):
        pg = self.open()
        pg.evaluate('''() => {
          localStorage.setItem('claims-editor:autosave-enabled', '1');
          localStorage.setItem('claims-editor:autosave:v2:work/mine', JSON.stringify({ name: 'mine', label: '自分の設計書', designRel: 'work/mine', origin: 'files',
            profile: 'full', savedAt: '2026-11-24 10:00:00', files: { 'hops.yaml': 'hops: []\\n' } }));
        }''')
        pg.reload()
        pg.wait_for_selector('#autosave-box')
        order = pg.evaluate('() => Array.from(document.querySelectorAll("#start h2, #start .entries")).map(e => e.id || e.className)')
        self.assertEqual(order[0], 'recent-h')
        self.assertIn('続きから開く', pg.inner_text('#autosave-box'))
        for w in (900, 1280):
            pg.set_viewport_size({'width': w, 'height': 900})
            pg.wait_for_timeout(150)
            self.shot(pg, f'{w}_01_start_with_autosave')
        pg.click('[data-restore="work/mine"]')
        self.poll(pg, '() => ClaimsEditor.state().open && ClaimsEditor.state().files.join() === "hops.yaml"')
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ 5. the words of the screens
    def _words(self, pg, where):
        """The problems of the words on the screen: collected in self.bad (all of them reported at once)."""
        text = pg.evaluate(RENDERED)
        for x in re.findall(r'.{0,30}#\d+.{0,10}', text):
            self.bad.append(f'{where}: an issue number on the screen: {x!r}')
        ui_text = pg.evaluate(RENDERED_UI)
        for rx in BODY_DENY:
            for x in rx.findall(ui_text):
                self.bad.append(f'{where}: a word of the body text that the glossary replaces: {x!r}')
        for tag, label in pg.evaluate(LABELS):
            if tag in ('H1', 'H2', 'H3') and FILE_IN_HEADING.search(label):
                self.bad.append(f'{where}: a file name as a heading: {label!r}')
            for j in JARGON:
                if re.search(r'(?<![A-Za-z_])' + re.escape(j) + r'(?![A-Za-z_])', label):
                    self.bad.append(f'{where}: the word {j!r} in a {tag}: {label!r}')

    def test_no_issue_numbers_file_names_or_jargon_on_the_screens(self):
        self.bad = []
        pg = self.open()
        self._words(pg, 'the start screen')
        for w in (900, 1280):
            pg.set_viewport_size({'width': w, 'height': 900})
            pg.wait_for_timeout(150)
            self.shot(pg, f'{w}_00_start')
        pg.set_viewport_size({'width': 1280, 'height': 900})
        pg.click('#btn-skeleton')
        self.poll(pg, '() => ClaimsEditor.state().open && ClaimsReview.ready()')
        screens = ['#/dashboard', '#/claims', '#/ledger', '#/tokens', '#/profile', '#/hops', '#/lifecycle', '#/catalog', '#/lint', '#/tables', '#/trace']
        for h in screens:
            self.go(pg, h)
            self._words(pg, h)
        pg.click('#ws-menu-btn')
        self._words(pg, 'the menu of the top bar')
        pg.keyboard.press('Escape')
        pg.click('#problems-toggle')
        self._words(pg, 'the problems panel')
        pg.click('#problems-close')
        pg.click('#btn-start-review')
        pg.wait_for_selector('#rv-start[open]')
        self._words(pg, 'the dialog of the review start')
        pg.fill('#rv-name', '言葉を見る人')
        pg.click('#rv-start-go')
        self.poll(pg, '() => ClaimsReview.me()')
        for h in ('#/review', '#/review/checklist', '#/review/comments', '#/review/record', '#/review/pa', '#/review/report', '#/review/col/claims/usage'):
            self.go(pg, h)
            pg.wait_for_timeout(200)
            self._words(pg, h)
        self.go(pg, '#/review')
        pg.locator('.rv-row .rv-row-title').first.click()
        pg.locator('.rv-row.open [data-add-comment]').click()
        self._words(pg, 'a row with the comment form')
        pg.click('#rv-submit')
        pg.wait_for_selector('#rv-submit-dialog[open]')
        self._words(pg, 'the dialog of the submission')
        pg.click('#rv-submit-cancel')
        self.assertEqual(self.bad, [], '\n'.join(self.bad))
        self.assertEqual(pg.problems, [])

    def test_no_file_names_or_jargon_in_the_labels_with_a_full_design(self):
        # scenario B with claim_lint run (every generated table, the review records): the headings, buttons and menu.
        # Its own text (the values of the design) may name issues; only the labels of the screens are checked here
        self.bad = []
        pg = self.open()
        pg.click('#btn-sample-b')
        self.poll(pg, '() => ClaimsEditor.state().open && ClaimsReview.ready()')
        self.go(pg, '#/lint')
        self.poll(pg, '() => ClaimsEditor.state().lint === "fresh"', timeout=120)
        for h in ['#/dashboard', '#/claims', '#/ledger', '#/claim/C-iss', '#/tokens', '#/token/KC_AT', '#/profile', '#/hops', '#/lifecycle', '#/catalog',
                  '#/lint', '#/tables', '#/trace', '#/review', '#/review/checklist', '#/review/comments', '#/review/record', '#/review/report']:
            self.go(pg, h)
            pg.wait_for_timeout(200)
            text = pg.evaluate(RENDERED)
            self._words(pg, h)
            self.bad = [b for b in self.bad if 'an issue number' not in b]
            self.assertTrue(text)
        self.assertEqual(self.bad, [], '\n'.join(self.bad))
        self.assertEqual(pg.problems, [])

    def test_the_py_mark_is_explained(self):
        pg = self.open()
        pg.click('#btn-sample-a')
        self.poll(pg, '() => ClaimsEditor.state().open')
        self.assertIn('Python で計算', pg.get_attribute('#nav a[data-view="lint"] .py', 'title'))
        self.assertIn('Python で計算', pg.inner_text('#nav-legend'))
        self.assertIn('数秒', pg.inner_text('#nav-legend'))

    # ------------------------------------------------------------------ 6. a narrow window
    def test_the_editor_and_the_menu_fold_on_a_narrow_window(self):
        pg = self.open(width=900)
        pg.click('#btn-sample-a')
        self.poll(pg, '() => ClaimsEditor.state().open')
        self.assertEqual(pg.get_attribute('#btn-toggle-nav', 'aria-expanded'), 'false')  # folded where it is narrow
        self.assertFalse(pg.is_visible('#side-nav'))
        self.assertTrue(pg.is_visible('#pane-left'))
        self.assertLessEqual(pg.evaluate('document.documentElement.scrollWidth'), 901)
        main_w = pg.evaluate('() => document.querySelector("#main").getBoundingClientRect().width')
        pg.click('#btn-toggle-editor')
        self.assertEqual(pg.get_attribute('#btn-toggle-editor', 'aria-expanded'), 'false')
        self.assertFalse(pg.is_visible('#pane-left'))
        self.assertGreater(pg.evaluate('() => document.querySelector("#main").getBoundingClientRect().width'), main_w + 200)
        pg.focus('#btn-toggle-nav')
        pg.keyboard.press('Enter')
        self.assertTrue(pg.is_visible('#side-nav'))
        # a jump to a line opens the folded editor
        self.go(pg, '#/claim/C-iss', '(C-iss)')
        pg.click('[data-reveal="claims:C-iss"]')
        self.assertTrue(pg.is_visible('#pane-left'))
        self.assertEqual(pg.problems, [])


if __name__ == '__main__':
    unittest.main()
