# -*- coding: utf-8 -*-
"""The review flow of the design editor (#50, redesigned in #67) in headless Chromium.

  pip install playwright && python -m playwright install chromium
  python -m pytest -q tools/tests/test_claims_review_ui.py
  CLAIMS_EDITOR_REDESIGN=research/claims-editor/ux-redesign python -m pytest -q tools/tests/test_claims_review_ui.py
      # also save the screenshots (900 and 1280 wide) and the network log

Skipped when Playwright or its browser is not installed (the CI jobs have no browser; run them locally). One test per
criterion of #67:
  the whole flow from the first screen: 「レビューを開始」 -> a row marked 「確認済み」 -> a comment (未提出) -> 「レビューを
  提出」 with a verdict, and the review.yaml written passes tools/review_record.py check; a row that changes loses its
  mark and says 「前回の確認から変更あり」, with old and new side by side; a review after a submission lists only the rows
  that changed, the unresolved comments first; a claims-review/1 file is read (the pilot originals) and is the migration
  of tools/review_record.py; the problems panel goes to the line and to the field; 確認事項 are filtered by the properties
  of the design (scenario A and B show different numbers); the top bar and the file tabs stay on one row at 900px.
Kept from #50: the independent review (hidden until submitted, leaving it is asked and recorded), review.yaml byte for
byte with the Python writer, the report equal to the committed one, nothing sent, nothing dropped without a question.
"""
import functools
import http.server
import json
import os
import socketserver
import sys
import tempfile
import threading
import time
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS = os.path.join(ROOT, 'docs')
SHOTS = os.environ.get('CLAIMS_EDITOR_REDESIGN')
B = os.path.join(ROOT, 'templates', 'examples', 'scenario-b')
PILOT_B = os.path.join(ROOT, 'research', 'pilot', 'scenario-b')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import review_check  # noqa: E402
import review_record  # noqa: E402
import row_hash  # noqa: E402
try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

DESIGN = ('claims.yaml', 'token_types.yaml', 'hops.yaml', 'catalog_answers.yaml')


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read().replace('\r\n', '\n')


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@unittest.skipIf(sync_playwright is None, 'playwright not installed')
class ReviewFlow(unittest.TestCase):
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
        if SHOTS:
            os.makedirs(os.path.join(ROOT, SHOTS), exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.srv.shutdown()

    def context(self, width=1280, height=900):
        ctx = self.browser.new_context(viewport={'width': width, 'height': height}, accept_downloads=True)
        ctx.requests = []
        ctx.on('request', lambda r: ctx.requests.append({'method': r.method, 'url': r.url, 'type': r.resource_type}))
        self.addCleanup(ctx.close)
        return ctx

    def page(self, ctx=None, width=1280):
        ctx = ctx or self.context(width)
        pg = ctx.new_page()
        pg.problems = []
        pg.on('pageerror', lambda e: pg.problems.append('pageerror: ' + str(e)))
        pg.on('console', lambda m: pg.problems.append(f'console {m.type}: {m.text}') if m.type in ('error', 'warning') else None)
        pg.goto(self.base)
        pg.wait_for_selector('#btn-sample-a')
        pg.ctx = ctx
        return pg

    def poll(self, pg, js, timeout=20, arg=None):
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
            pg.wait_for_timeout(200)

    def ready(self, pg):
        self.poll(pg, '() => ClaimsEditor.state().open && document.querySelectorAll("#tabs [role=tab]").length > 0 && ClaimsReview.ready()')
        pg.wait_for_timeout(200)

    def sample(self, pg, letter):
        pg.click(f'#btn-sample-{letter}')
        self.ready(pg)

    def open_files(self, pg, paths):
        pg.set_input_files('#in-files', paths)
        self.ready(pg)

    def start(self, pg, name, kind='human', independent=False):
        """「レビューを開始」 through the dialog."""
        pg.click('#btn-start-review')
        pg.wait_for_selector('#rv-start[open]')
        pg.fill('#rv-name', name)
        pg.check('#rv-kind-' + kind)
        if independent != pg.is_checked('#rv-independent'):
            pg.click('#rv-independent')
        pg.click('#rv-start-go')

    def started(self, pg, name):
        self.poll(pg, 'n => ClaimsReview.me() === n && !document.querySelector("#review-bar").hidden', arg=name)

    def shot(self, pg, name):
        if SHOTS:
            w = pg.viewport_size['width']
            pg.screenshot(path=os.path.join(ROOT, SHOTS, f'{w}_{name}.png'), full_page=False)

    def data(self, pg):
        return pg.evaluate('() => ClaimsReview.data()')

    def check_text(self, text, design):
        """The review.yaml text written by the editor passes the Python checker, and is its canonical form."""
        data = review_record.load_text(text)
        errs, notes = review_record.check(data, design)
        self.assertEqual(errs, [])
        self.assertEqual(review_record.dump(data, review_record.version_of(text)), text)
        return data, notes

    # ------------------------------------------------------------------ criterion 1: the whole flow
    def test_the_flow_from_the_first_screen_to_the_submission(self):
        for width in (1280, 900):
            with self.subTest(width=width):
                pg = self.page(width=width)
                # the first screen: 「レビューを開始」 is there, and with nothing open it points at what to open
                self.assertTrue(pg.is_visible('#btn-start-review'))
                self.shot(pg, '00_start')
                pg.click('#btn-start-review')
                self.assertIn('先に開いてください', pg.inner_text('#start-msg'))
                self.assertEqual(pg.evaluate('() => document.activeElement.id'), 'btn-review')
                self.sample(pg, 'a')
                self.assertTrue(pg.is_hidden('#review-bar'))
                # the dialog: the name (self-declared), a person or an LLM, a review.yaml to read in, independent or not
                pg.click('#btn-start-review')
                pg.wait_for_selector('#rv-start[open]')
                self.assertEqual(pg.evaluate('() => document.activeElement.id'), 'rv-name')
                for sel in ('#rv-kind-human', '#rv-kind-llm', '#rv-independent', '#rv-import-btn'):
                    self.assertTrue(pg.is_visible(sel), sel)
                self.shot(pg, '01_start_dialog')
                pg.click('#rv-start-go')  # no name: said, not started
                self.assertIn('名前', pg.inner_text('#rv-start-msg'))
                pg.fill('#rv-name', '山田')
                pg.click('#rv-start-go')
                self.started(pg, '山田')
                # the bar: the progress and the one button that submits, always there while reviewing
                bar = pg.inner_text('#rv-progress')
                total = int(pg.get_attribute('#rv-progress', 'data-total'))
                self.assertGreater(total, 10)
                self.assertIn(f'確認済み 0 / {total} 行・コメント 0 件・未提出', bar)
                self.assertTrue(pg.is_visible('#rv-submit'))
                self.assertIn('レビューする行', pg.inner_text('main h1'))
                self.assertEqual(pg.get_attribute('#rv-filter', 'data-filter'), 'all')
                self.assertEqual(pg.locator('.rv-row').count(), total)
                # a row: opened with the keyboard, its values listed, marked 「確認済み」 -> it folds
                first = pg.locator('.rv-row').first
                anchor = first.get_attribute('data-anchor')
                title = first.locator('.rv-row-title')
                self.assertEqual(title.get_attribute('aria-expanded'), 'false')
                title.focus()
                pg.keyboard.press('Enter')
                self.poll(pg, 'a => document.querySelector(`.rv-row[data-anchor="${a}"]`).dataset.open === "1"', arg=anchor)
                self.assertEqual(pg.locator(f'.rv-row[data-anchor="{anchor}"] .rv-row-title').get_attribute('aria-expanded'), 'true')
                self.assertGreater(pg.locator('.rv-row.open .rv-values .col').count(), 3)
                # a comment: kept as 未提出 until the submission, with the severity and the kind the report needs
                pg.click(f'[data-add-comment="{anchor}"]')
                self.assertEqual(pg.evaluate('() => document.activeElement.id'), 'rvc-content')
                self.assertEqual(pg.locator('#rvc-severity option').count(), 3)
                self.assertEqual(pg.locator('#rvc-kind option').count(), 5)
                pg.fill('#rvc-content', 'この行の理由が、要求と合っていない')
                pg.select_option('#rvc-severity', 'Minor')
                pg.click('#rvc-save')
                c = pg.locator(f'.rv-row[data-anchor="{anchor}"] .rv-c')
                self.assertEqual(c.count(), 1)
                self.assertEqual(c.get_attribute('data-comment-state'), 'pending')
                self.assertIn('未提出', c.inner_text())
                self.shot(pg, '02_row_open_with_comment')
                pg.click(f'[data-viewed="{anchor}"]')
                self.poll(pg, 'a => document.querySelector(`.rv-row[data-anchor="${a}"]`).dataset.rowState === "viewed"', arg=anchor)
                self.assertEqual(pg.locator(f'.rv-row[data-anchor="{anchor}"]').get_attribute('data-open'), '0')  # folded
                self.assertEqual(pg.evaluate('() => document.activeElement.dataset.viewed'), anchor)  # the focus stays on the mark
                self.assertIn(f'確認済み 1 / {total} 行・コメント 1 件・未提出', pg.inner_text('#rv-progress'))
                # 「次の未確認へ」 opens the next row that is not marked
                pg.click('#rv-next')
                nxt = self.poll(pg, '() => (document.querySelector(".rv-row.open") || {dataset: {}}).dataset.anchor')
                self.assertNotEqual(nxt, anchor)
                self.assertEqual(pg.evaluate('() => document.activeElement.dataset.toggleRow'), nxt)
                self.shot(pg, '03_rows')
                # the submission: once, with a summary and one verdict; the default follows the comments
                pg.click('#rv-submit')
                pg.wait_for_selector('#rv-submit-dialog[open]')
                self.assertEqual(pg.get_attribute('#rv-submit-counts', 'data-default'), 'request_changes')
                self.assertTrue(pg.is_checked('#rv-verdict-request_changes'))
                self.assertEqual(pg.locator('input[name="rv-verdict"]').count(), 3)
                pg.fill('#rv-summary', '理由の書き方を 1 か所直してほしい')
                self.shot(pg, '04_submit_dialog')
                pg.click('#rv-submit-go')
                pg.wait_for_selector('#rv-next-steps')
                # after it: what to do next (commit review.yaml to the pull request)
                nxt_text = pg.inner_text('#rv-next-steps')
                self.assertIn('review.yaml を書き出す', nxt_text)
                self.assertIn('pull request にコミット', nxt_text)
                self.assertIn('提出済み', pg.inner_text('#rv-progress'))
                self.shot(pg, '05_submitted')
                with pg.expect_download() as dl:
                    pg.click('#rv-export-next')
                self.assertEqual(dl.value.suggested_filename, 'review.yaml')
                text = read(dl.value.path())
                data, _ = self.check_text(text, os.path.join(ROOT, 'templates', 'examples', 'scenario-a'))
                rv = data['reviews'][0]
                self.assertEqual(data['format'], 'claims-review/2')
                self.assertEqual(rv['reviewer'], {'name': '山田', 'kind': 'human'})
                sub = rv['submissions'][0]
                self.assertEqual((sub['verdict'], sub['summary'], sub['comments'], sub['unresolved']), ('request_changes', '理由の書き方を 1 か所直してほしい', ['C01'], 1))
                hashes = row_hash.row_hashes(os.path.join(ROOT, 'templates', 'examples', 'scenario-a'))['hashes']
                self.assertEqual(sub['viewed'], {anchor: hashes[anchor]})  # the hashes of the rows viewed go with the verdict
                self.assertEqual(rv['submitted'], sub['at'])
                self.assertEqual(rv['comments'][0]['state'], 'unresolved')
                self.assertEqual((rv['comments'][0]['severity'], rv['comments'][0]['anchors'], rv['comments'][0]['hash']), ('Minor', [anchor], hashes[anchor]))
                self.assertFalse(pg.evaluate('() => ClaimsReview.unsaved()'))
                self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ criterion 2: a changed row loses its mark
    def test_a_changed_row_loses_its_mark_and_shows_old_and_new(self):
        pg = self.page()
        self.sample(pg, 'a')
        self.start(pg, '山田')
        self.started(pg, '山田')
        anchor = 'claims:C-tenant-id'
        pg.click(f'.rv-row[data-anchor="{anchor}"] .rv-row-title')
        pg.click(f'[data-viewed="{anchor}"]')
        self.poll(pg, 'a => document.querySelector(`.rv-row[data-anchor="${a}"]`).dataset.rowState === "viewed"', arg=anchor)
        self.assertTrue(pg.is_checked(f'[data-viewed="{anchor}"]'))
        before = self.data(pg)['reviews'][0]['viewed'][anchor]
        self.assertEqual(before['hash'], row_hash.row_hashes(os.path.join(ROOT, 'templates', 'examples', 'scenario-a'))['hashes'][anchor])
        self.assertEqual(review_record.hashlib.sha256(before['snapshot'].encode('utf-8')).hexdigest(), before['hash'])
        # the row is edited in the editor (the same path as typing)
        old = pg.evaluate('() => ClaimsEditor.rowOf("claims:C-tenant-id").row.description')
        self.assertTrue(pg.evaluate('([a, b]) => ClaimsEditor.replaceText("claims.yaml", a, b)', [old, old + '（書き換えた）']))
        self.poll(pg, 'a => document.querySelector(`.rv-row[data-anchor="${a}"]`).dataset.rowState === "changed"', arg=anchor)
        self.assertFalse(pg.is_checked(f'[data-viewed="{anchor}"]'))  # the mark is off
        self.assertIn('前回の確認から変更あり', pg.inner_text(f'.rv-row[data-anchor="{anchor}"] [data-changed]'))
        self.assertEqual(pg.get_attribute('#rv-progress', 'data-viewed'), '0')
        self.assertEqual(pg.get_attribute('#rv-progress', 'data-changed'), '1')
        # the changed column, old and new side by side
        pg.click(f'.rv-row[data-anchor="{anchor}"] .rv-row-title')
        pg.wait_for_selector(f'[data-changed-row="{anchor}"] table')
        rows = pg.locator(f'[data-changed-row="{anchor}"] tbody tr')
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.get_attribute('data-diff-col'), 'description')
        self.assertNotIn('書き換えた', rows.locator('.rv-old').inner_text())
        self.assertIn('書き換えた', rows.locator('.rv-new').inner_text())
        self.shot(pg, '06_changed_row')
        # the detail screen says the same, and the Python checker too
        self.go(pg, '#/claim/C-tenant-id')
        pg.wait_for_selector('[data-review-panel] [data-changed]')
        d = tempfile.mkdtemp()
        for n in DESIGN:
            with open(os.path.join(d, n), 'w', encoding='utf-8', newline='\n') as f:
                f.write(pg.evaluate('n => ClaimsEditor.fileText(n)', n).replace('\r\n', '\n'))
        _, notes = self.check_text(pg.evaluate('() => ClaimsReview.text()'), d)
        self.assertTrue(any(anchor in n and '前回の確認から変更あり' in n for n in notes), notes)
        # marking it again binds the mark to the new content
        pg.click(f'[data-review-panel] [data-viewed="{anchor}"]')
        self.poll(pg, '() => document.querySelector("[data-review-panel] .rv-viewed").dataset.rowState === "viewed"')
        self.assertNotEqual(self.data(pg)['reviews'][0]['viewed'][anchor]['hash'], before['hash'])
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ criterion 3: the review after a submission
    def rereview_yaml(self, design, edit=None):
        """A review.yaml in which 再レビュー has viewed every row of the design and submitted (with one unresolved comment)."""
        hashes = row_hash.row_hashes(design)['hashes']
        docs = row_hash.load(design)
        rows, _ = row_hash.anchors(docs)
        snap = {a: row_hash.jcs(r) for a, _, _, r in rows if a in hashes}
        at = '2026-11-20T01:02:03Z'
        rv = {'reviewer': {'name': '再レビュー', 'kind': 'human'}, 'self_declared': True, 'started': at, 'submitted': at, 'answers': {},
              'viewed': {a: {'hash': h, 'at': at, 'snapshot': snap[a]} for a, h in hashes.items()},
              'comments': [{'id': 'C01', 'state': 'unresolved', 'location': 'C-roles', 'anchors': ['claims:C-roles'], 'content': '前回の指摘', 'severity': 'Major',
                            'origin': 'テンプレート項目', 'kind': '理由の不備', 'verdict': '保留', 'hash': hashes['claims:C-roles'], 'at': at}],
              'submissions': [{'at': at, 'verdict': 'approve', 'viewed': dict(hashes), 'comments': ['C01'], 'unresolved': 1}]}
        data = {'format': 'claims-review/2', 'design': 'work/rereview', 'independent': False, 'reviews': [rv]}
        errs, _ = review_record.check(data, design)
        self.assertEqual(errs, [])
        return review_record.dump(data), len(hashes)

    def test_a_review_after_a_submission_lists_only_the_changed_rows(self):
        a_dir = os.path.join(ROOT, 'templates', 'examples', 'scenario-a')
        text, total = self.rereview_yaml(a_dir)
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, 'rereview'))
        for n in DESIGN:
            body = read(os.path.join(a_dir, n))
            if n == 'claims.yaml':  # the author changed one row after the review
                row = next(c for c in row_hash.load(a_dir)['claims']['claims'] if c['id'] == 'C-tenant-id')
                self.assertEqual(body.count(row['description']), 1)
                body = body.replace(row['description'], row['description'] + '（直した）')
            with open(os.path.join(d, 'rereview', n), 'w', encoding='utf-8', newline='\n') as f:
                f.write(body)
        with open(os.path.join(d, 'rereview', 'review.yaml'), 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        pg = self.page()
        # 「設計書をレビューする」 on the first screen: the files and review.yaml, then the dialog of 「レビューを開始」
        pg.set_input_files('#in-review-files', [os.path.join(d, 'rereview', n) for n in DESIGN + ('review.yaml',)])
        pg.wait_for_selector('#rv-start[open]')
        self.assertEqual(pg.get_attribute('#rv-start-records', 'data-reviewers'), '1')
        self.assertIn('再レビュー', pg.inner_text('#rv-start-records'))
        pg.fill('#rv-name', '再レビュー')
        pg.click('#rv-start-go')
        pg.click('#confirm [data-choice="go"]')  # the same name as a recorded reviewer: asked (names are self-declared)
        self.started(pg, '再レビュー')
        # by default: only what changed since the last review
        self.assertEqual(pg.get_attribute('#rv-filter', 'data-rereview'), '1')
        self.assertEqual(pg.get_attribute('#rv-filter', 'data-filter'), 'todo')
        self.assertIn('前回のレビュー以降の変更（1）', pg.inner_text('#rv-flt-todo'))
        self.assertEqual([r.get_attribute('data-anchor') for r in pg.locator('.rv-row').all()], ['claims:C-tenant-id'])
        self.assertEqual(pg.locator('.rv-row').get_attribute('data-row-state'), 'changed')
        self.assertIn(f'確認済み {total - 1} / {total} 行', pg.inner_text('#rv-progress'))
        # the unresolved comments come first
        self.assertEqual(pg.locator('#rv-unresolved .rv-c').count(), 1)
        self.assertTrue(pg.evaluate('() => document.querySelector("#rv-unresolved").compareDocumentPosition(document.querySelector(".rv-row")) & Node.DOCUMENT_POSITION_FOLLOWING'))
        # the changed column, old and new
        pg.click('.rv-row .rv-row-title')
        self.assertEqual(pg.locator('[data-changed-row] tbody tr').get_attribute('data-diff-col'), 'description')
        self.assertIn('直した', pg.inner_text('[data-changed-row] .rv-new'))
        self.shot(pg, '07_rereview')
        # the approval of the last submission is old: the content changed
        self.go(pg, '#/review/record', '提出と記録')
        self.assertEqual(pg.locator('[data-stale-approval]').count(), 1)
        self.assertIn('古い承認（内容が変更されました）', pg.inner_text('[data-table="submissions"]'))
        # every row is still one press away; resolving the comment and marking the row leaves nothing to do
        self.go(pg, '#/review', 'レビューする行')
        pg.click('#rv-flt-all')
        self.assertEqual(pg.locator('.rv-row').count(), total)
        pg.click('#rv-flt-todo')
        pg.click('#rv-unresolved [data-resolve="C01"]')
        self.poll(pg, '() => !document.querySelector("#rv-unresolved")')
        pg.click('[data-viewed="claims:C-tenant-id"]')
        pg.click('#rv-submit')
        self.assertEqual(pg.get_attribute('#rv-submit-counts', 'data-default'), 'approve')  # all viewed, nothing unresolved
        pg.click('#rv-submit-go')
        pg.wait_for_selector('#rv-next-steps')
        data = self.data(pg)
        self.assertEqual([s['verdict'] for s in data['reviews'][0]['submissions']], ['approve', 'approve'])
        self.assertEqual(data['reviews'][0]['comments'][0]['state'], 'resolved')
        self.assertEqual(pg.locator('[data-stale-approval]').count(), 0)
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ criterion 7: the old form is read
    def test_a_claims_review_1_file_is_read_and_migrated(self):
        v1 = os.path.join(PILOT_B, 'reviews', 'R1', 'review.yaml')
        self.assertIn('format: "claims-review/1"', read(v1))
        want = review_record.migrate(review_record.load(v1))
        pg = self.page()
        self.open_files(pg, [os.path.join(PILOT_B, n) for n in DESIGN] + [v1])
        got = self.data(pg)
        want['design'] = got['design']  # files opened without their folder take the design of the review
        self.assertEqual(got, json.loads(json.dumps(want)))
        self.assertEqual(pg.evaluate('() => ClaimsReview.text()'), review_record.dump(want, review_record.version_of(read(v1))))
        self.assertFalse(pg.evaluate('() => ClaimsReview.unsaved()'))  # reading the old form is not an edit
        self.go(pg, '#/review/record', '提出と記録')
        self.assertIn('古い形', pg.inner_text('#rv-migrated-note'))
        # the pilot reviews were independent: nothing of them is shown until one is the reviewer and has submitted
        self.assertEqual(pg.get_attribute('#rv-hidden', 'data-hidden-others'), '1')
        self.assertEqual(pg.locator('[data-table="submissions"]').count(), 0)
        pg.click('#btn-start-review')
        pg.fill('#rv-name', want['reviews'][0]['reviewer']['name'])
        pg.click('#rv-start-go')
        pg.click('#confirm [data-choice="go"]')
        self.started(pg, want['reviews'][0]['reviewer']['name'])
        self.go(pg, '#/review/record', '提出と記録')
        self.assertEqual(pg.locator('[data-table="submissions"] tbody tr').count(), len(want['reviews'][0]['submissions']))
        # the marks of the old decisions are on the rows, as viewed marks
        self.go(pg, '#/claims', 'クレーム')
        self.assertGreater(pg.locator('.rvb[data-review-state]').count(), 5)
        # the four migrated copies next to the pilot originals are what the editor makes of the originals
        for s, r in (('scenario-b', 'R1'), ('scenario-b', 'R2'), ('scenario-c', 'R1'), ('scenario-c', 'R2')):
            d = os.path.join(ROOT, 'research', 'pilot', s, 'reviews', r)
            js = pg.evaluate('t => { const F = ClaimsReviewFormat; return F.dump(F.migrate(ClaimsEditor.parseYaml(t)), F.versionOf(t)); }', read(os.path.join(d, 'review.yaml')))
            self.assertEqual(js, read(os.path.join(d, 'review.v2.yaml')), (s, r))
        self.assertEqual(pg.problems, [])

    def test_the_report_of_scenario_b_is_the_committed_one(self):
        pg = self.page()
        self.sample(pg, 'b')
        text = read(os.path.join(B, 'review.yaml'))
        self.assertEqual(pg.evaluate('() => ClaimsReview.text()'), text)  # read and written back byte for byte
        name = review_record.load_text(text)['reviews'][0]['reviewer']['name']
        got = pg.evaluate('n => ClaimsReview.reportText(n)', name)
        self.assertEqual(got, read(os.path.join(B, 'review-report-2026-11-23.md')))
        self.assertEqual(review_check.check_report(ROOT, got), [])
        self.go(pg, '#/review/report', 'レビューレポート')
        self.assertEqual(pg.inner_text('#rv-report').replace('\r\n', '\n').strip(), got.strip())

    # ------------------------------------------------------------------ criterion 5: the problems panel
    def test_the_problems_panel_goes_to_the_line_and_to_the_field(self):
        pg = self.page()
        self.sample(pg, 'a')
        self.assertTrue(pg.is_visible('#problems-toggle'))
        self.assertEqual(pg.get_attribute('#problems-toggle', 'aria-expanded'), 'false')
        self.assertEqual(pg.get_attribute('#problems-count', 'data-counts'), '0/0/0')
        self.assertIn('問題はありません', pg.inner_text('#problems-toggle'))
        # an error in one column of one row
        self.assertTrue(pg.evaluate('''() => { const m = /pii_category: [^\\n]+/.exec(ClaimsEditor.fileText("claims.yaml"));
          return ClaimsEditor.replaceText("claims.yaml", m[0], "pii_category: 分からない"); }'''))
        self.poll(pg, '() => document.querySelector("#problems-count").dataset.counts.split("/")[0] !== "0"')
        self.assertIn('エラー 1', pg.inner_text('#problems-toggle'))  # the count is always on screen
        pg.click('#problems-toggle')
        pg.wait_for_selector('#problems-panel tr[data-problem]')
        row = pg.locator('#problems-panel tr[data-sev="error"]').first
        cells = row.locator('td').all_inner_texts()
        self.assertEqual(len(cells), 5)  # severity, message, place, file and line, rule
        self.assertIn('エラー', cells[0])
        self.assertIn('pii_category', cells[1])
        self.assertRegex(cells[2], r'^クレーム \S+ › ')
        self.assertRegex(cells[3], r'^claims\.yaml:\d+$')
        self.assertEqual(cells[4], 'SCHEMA')
        anchor = row.get_attribute('data-anchor')
        self.assertEqual(row.get_attribute('data-column'), 'pii_category')
        line = int(cells[3].split(':')[1])
        self.shot(pg, '08_problems')
        row.locator('.pb-msg').click()
        # the editor is on the line, the screen of the design on the field
        self.poll(pg, 'l => ClaimsEditor.state().active === "claims.yaml" && ClaimsEditor.cursorLine() === l', arg=line)
        self.poll(pg, 'a => location.hash.startsWith("#/claim/" + encodeURIComponent(a.split(":")[1]))', arg=anchor)
        self.poll(pg, '() => { const el = document.querySelector("main [data-col=pii_category]"); return el && !el.closest("[hidden]") && document.activeElement === el; }')
        self.assertEqual(pg.locator('#problems-panel tr[aria-current="true"]').count(), 1)
        # the reviewers' comments are not in the panel
        self.start(pg, '山田')
        self.started(pg, '山田')
        pg.click(f'.rv-row[data-anchor="{anchor}"] .rv-row-title')
        pg.click(f'[data-add-comment="{anchor}"]')
        pg.fill('#rvc-content', 'レビュアーが書いた意見')
        pg.click('#rvc-save')
        self.assertNotIn('レビュアーが書いた意見', pg.inner_text('#problems-panel'))
        # F8 steps through the problems; the severity toggles filter; Escape-free closing with the button
        pg.locator('main h1').focus()
        pg.keyboard.press('F8')
        self.assertEqual(pg.locator('#problems-panel tr[aria-current="true"]').count(), 1)
        pg.uncheck('[data-pb-sev="error"]')
        self.assertEqual(pg.locator('#problems-panel tr[data-sev="error"]').count(), 0)
        pg.click('#problems-close')
        self.assertTrue(pg.is_hidden('#problems-panel'))
        self.assertEqual(pg.evaluate('() => document.activeElement.id'), 'problems-toggle')
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ criterion 6: 確認事項 follow the design
    def shown(self, pg):
        self.go(pg, '#/review/checklist', '確認事項')
        el = pg.locator('#rv-q-count')
        return int(el.get_attribute('data-shown')), int(el.get_attribute('data-total'))

    def test_the_questions_are_filtered_by_the_properties_of_the_design(self):
        counts = {}
        for letter in ('a', 'b'):
            pg = self.page()
            self.sample(pg, letter)
            n, total = self.shown(pg)
            counts[letter] = n
            self.assertEqual(total, 168)
            self.assertLess(n, total)
            self.assertIn(f'全 {total} 件のうち {n} 件を表示', pg.inner_text('#rv-q-count'))
            self.assertEqual(pg.locator('.rv-q').count(), n)
            # why the others are not shown, with numbers that add up
            pg.click('#rv-q-why summary')
            hidden = [int(x) for x in pg.locator('[data-table="hidden-reasons"] td.num').all_inner_texts()]
            self.assertEqual(sum(hidden), total - n)
            # each question says why it is shown
            self.assertEqual(pg.locator('.rv-q [data-why]').count(), n)
            # the properties were read from the design
            traits = {el.get_attribute('data-trait'): el.get_attribute('data-trait-value') for el in pg.locator('#rv-traits [data-trait]').all()}
            self.assertEqual(traits['delegation'], 'true' if letter == 'b' else 'false')
            self.assertEqual(traits, {k: str(v).lower() for k, v in pg.evaluate('() => ClaimsReview.traitValues()').items() if k != 'always'})
            # all of them are one press away
            pg.click('#rv-q-all')
            self.assertEqual(pg.locator('.rv-q').count(), total)
            self.assertEqual(pg.locator('.rv-q[data-shown="0"]').count(), total - n)
            pg.click('#rv-q-all')
            self.assertEqual(pg.locator('.rv-q').count(), n)
            if letter == 'b':
                self.shot(pg, '09_checklist')
            self.assertEqual(pg.problems, [])
        self.assertNotEqual(counts['a'], counts['b'])
        self.assertLess(counts['a'], counts['b'])  # the smaller design has fewer questions

    def test_a_property_that_cannot_be_read_is_asked_and_kept(self):
        pg = self.page()
        self.sample(pg, 'a')
        # the data decide what is asked: a condition with `ask` (none of today's conditions needs one)
        pg.evaluate('''() => { const R = CLAIMS_VIEWER_DATA.review; R.checklist.conditions.push({ id: 'audited', label: '監査の対象である', ask: '監査の対象ですか' });
          R.questions[0].triage = 'C'; R.questions[0].priority = 1; R.questions[0].show_when = ['audited']; }''')
        qid = pg.evaluate('() => CLAIMS_VIEWER_DATA.review.questions[0].id')
        self.start(pg, '山田')
        self.started(pg, '山田')
        n0, _ = self.shown(pg)
        self.assertEqual(pg.get_attribute('#rv-asked', 'data-asked'), '1')
        self.assertEqual(pg.locator(f'.rv-q[data-q="{qid}"]').count(), 1)  # not known yet: shown
        self.assertIn('読めない', pg.inner_text(f'.rv-q[data-q="{qid}"] [data-why]'))
        pg.check('input[name="rv-trait-audited"][value="false"]')
        self.poll(pg, 'q => !document.querySelector(`.rv-q[data-q="${q}"]`)', arg=qid)
        self.assertEqual(self.shown(pg)[0], n0 - 1)
        self.assertEqual(self.data(pg)['reviews'][0]['traits'], {'audited': False})  # kept in review.yaml
        self.check_text(pg.evaluate('() => ClaimsReview.text()'), None)
        pg.check('input[name="rv-trait-audited"][value="true"]')
        self.poll(pg, 'q => !!document.querySelector(`.rv-q[data-q="${q}"]`)', arg=qid)
        self.assertIn('監査の対象である', pg.inner_text(f'.rv-q[data-q="{qid}"] [data-why]'))
        # an answer is kept, and a question answered 「直す必要あり」 becomes a comment
        pg.check(f'.rv-q[data-q="{qid}"] input[value="no"]')
        pg.fill(f'#rv-memo-{qid}', '欄が空')
        pg.wait_for_timeout(400)
        self.assertEqual(self.data(pg)['reviews'][0]['answers'][qid]['answer'], 'no')
        pg.click(f'.rv-q[data-q="{qid}"] .rv-findbtn')
        pg.wait_for_selector('#rvc-content')
        self.assertEqual(pg.input_value('#rvc-content'), '欄が空')
        pg.click('#rvc-save')
        c = self.data(pg)['reviews'][0]['comments'][0]
        self.assertEqual((c['questions'], c['origin'], c['state']), ([qid], '観点', 'pending'))
        # beside a row: the questions read with that kind of row
        self.go(pg, '#/review', 'レビューする行')
        pg.click('.rv-row[data-anchor="claims:C-tenant-id"] .rv-row-title')
        self.assertGreater(int(pg.get_attribute('.rv-row.open [data-related-questions]', 'data-related-questions')), 0)
        self.assertEqual(pg.problems, [])

    def test_a_property_whose_file_is_not_open_is_unreadable_and_a_hint_is_folded(self):
        pg = self.page()
        self.open_files(pg, [os.path.join(ROOT, 'templates', 'examples', 'scenario-a', 'claims.yaml')])
        # the data may give a question a one-sentence wording (ask) and an explanation (hint, #56): the hint is folded
        pg.evaluate('''() => { const q = CLAIMS_VIEWER_DATA.review.questions[0]; q.triage = 'C'; q.priority = 1; q.show_when = ['exchange'];
          q.ask = '一文の問い'; q.hint = '補足の説明'; }''')
        qid = pg.evaluate('() => CLAIMS_VIEWER_DATA.review.questions[0].id')
        self.go(pg, '#/review/checklist', '確認事項')
        traits = {el.get_attribute('data-trait'): el.get_attribute('data-trait-value') for el in pg.locator('#rv-traits [data-trait]').all()}
        self.assertEqual(traits['exchange'], 'null')  # read from hops.yaml, which is not open
        self.assertIn('読めない', pg.inner_text('#rv-traits [data-trait="exchange"]'))
        self.assertIn(traits['pii'], ('true', 'false'))  # read from claims.yaml, which is open
        item = pg.locator(f'.rv-q[data-q="{qid}"]')
        self.assertEqual(item.count(), 1)  # a question of a property that cannot be read stays, with a note
        self.assertIn('読めない', item.locator('[data-why]').inner_text())
        self.assertIn('一文の問い', item.locator('h3').inner_text())
        self.assertFalse(item.locator('.rv-hint p').is_visible())
        item.locator('.rv-hint summary').click()
        self.assertIn('補足の説明', item.locator('.rv-hint p').inner_text())
        self.assertEqual(pg.problems, [])

    def test_empty_required_fields_are_one_folded_group_of_the_problems(self):
        # the rule TODO of claim_lint (#60: required fields left empty): its findings follow the text like SCHEMA, and the
        # panel lists them last, folded. The rule is not in this build of claim_lint yet, so its findings are put in by hand
        pg = self.page()
        self.sample(pg, 'a')
        pg.evaluate('''() => { const orig = ClaimsEditor.problems.list; const fake = [1, 2, 3].map((i) => ({ source: 'claim_lint', severity: 'warn', rule: 'TODO',
          message: '必須の欄が空 ' + i, file: 'claims.yaml', line: 30 + i, anchorKind: 'claims', anchorId: 'C-iss', column: 'owner' }));
          ClaimsEditor.problems.inject(fake); }''')
        pg.click('#problems-toggle')
        pg.wait_for_selector('#problems-todo')
        self.assertIn('未記入 3 件', pg.inner_text('#problems-todo summary'))
        self.assertFalse(pg.locator('#problems-todo tr[data-problem]').first.is_visible())
        pg.click('#problems-todo summary')
        self.assertEqual(pg.locator('#problems-todo tr[data-rule="TODO"]').count(), 3)
        pg.locator('#problems-todo .pb-msg').first.click()
        self.poll(pg, '() => ClaimsEditor.cursorLine() === 31')
        self.assertTrue(pg.locator('#problems-todo tr[data-problem]').first.is_visible())  # stays open after the jump
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ the layout left over from #53
    def test_the_top_bar_and_the_file_tabs_stay_on_one_row(self):
        for width in (900, 1280):
            with self.subTest(width=width):
                pg = self.page(width=width)
                self.sample(pg, 'b')
                self.assertGreaterEqual(pg.locator('#tabs [role=tab]').count(), 14)
                self.start(pg, 'レイアウト')
                self.started(pg, 'レイアウト')
                # a review folds the YAML editor (it is reading); the toggle of the top bar opens it again
                self.assertEqual(pg.get_attribute('#btn-toggle-editor', 'aria-expanded'), 'false')
                self.assertTrue(pg.is_hidden('#pane-left'))
                pg.click('#btn-toggle-editor')
                self.assertTrue(pg.is_visible('#pane-left'))
                box = pg.evaluate('''() => { const r = (s) => document.querySelector(s).getBoundingClientRect();
                  const kids = Array.from(document.querySelectorAll('header.top > *, #ws-bar > *')).filter((e) => e.offsetParent !== null && e.id !== 'ws-bar');
                  const tabs = Array.from(document.querySelectorAll('#tabs [role=tab]'));
                  return { top: r('header.top').height, mids: kids.map((e) => { const b = e.getBoundingClientRect(); return Math.round(b.top + b.height / 2); }),
                    tabTops: Array.from(new Set(tabs.map((t) => Math.round(t.getBoundingClientRect().top)))), tabsH: r('#tabs').height, tabH: tabs[0].getBoundingClientRect().height,
                    scroll: document.querySelector('#tabs').scrollWidth > document.querySelector('#tabs').clientWidth, overflowX: document.documentElement.scrollWidth > innerWidth }; }''')
                self.assertLess(max(box['mids']) - min(box['mids']), 12, box)   # everything of the top bar is on one line
                self.assertLess(box['top'], 75, box)
                self.assertEqual(len(box['tabTops']), 1, box)                 # the 14 file tabs are one row
                self.assertLess(box['tabsH'], box['tabH'] * 1.9, box)
                self.assertTrue(box['scroll'], box)                           # which scrolls sideways
                self.assertFalse(box['overflowX'], box)
                # the last tab can be reached with the keyboard and is brought into view
                pg.locator('#tabs [role=tab]').first.focus()
                pg.keyboard.press('End')
                last = pg.evaluate('''() => { const t = document.querySelector('#tabs [aria-selected="true"]').getBoundingClientRect(); const b = document.querySelector('#tabs').getBoundingClientRect();
                  return t.left >= b.left - 1 && t.right <= b.right + 1; }''')
                self.assertTrue(last)
                # the menu 「ファイル」 holds what left the bar; Escape closes it
                pg.click('#ws-menu-btn')
                for sel in ('#btn-export-one', '#btn-export-zip', '#chk-autosave', '#btn-close', '#btn-add-file'):
                    self.assertTrue(pg.is_visible(sel), sel)
                pg.keyboard.press('Escape')
                self.assertTrue(pg.is_hidden('#btn-close'))
                self.assertEqual(pg.evaluate('() => document.activeElement.id'), 'ws-menu-btn')
                self.shot(pg, '10_layout')
                self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ kept from #50
    def test_independent_review_hides_the_others_until_submitted_and_leaving_is_recorded(self):
        pg = self.page()
        self.sample(pg, 'b')
        other = self.data(pg)['reviews'][0]['reviewer']['name']
        self.start(pg, '独立 A', independent=True)
        self.started(pg, '独立 A')
        d = self.data(pg)
        self.assertTrue(d['independent'])
        self.assertEqual(d['reviews'][1]['independence'], {'mode': 'kept'})
        self.assertEqual(pg.evaluate('() => ClaimsReview.visibleNames()'), ['独立 A'])
        self.assertEqual(pg.locator('.rv-row .rv-c').count(), 0)
        self.assertEqual(pg.locator('.rvb[data-review-by]').count(), 0)
        self.go(pg, '#/review/comments', 'コメント')
        self.assertEqual(pg.get_attribute('#rv-comment-list', 'data-comments'), '0')
        self.assertIn('隠しています', pg.inner_text('main'))
        self.go(pg, '#/review/record', '提出と記録')
        self.assertEqual(pg.get_attribute('#rv-hidden', 'data-hidden-others'), '1')
        self.assertEqual(pg.get_attribute('#rv-independent-state', 'data-independent'), '1')
        # writing out every record before submitting is leaving the independent review: asked first
        pg.click('#rv-export')
        pg.wait_for_selector('#confirm')
        self.assertIn('独立レビュー', pg.inner_text('#confirm'))
        pg.click('#confirm [data-choice="cancel"]')
        self.assertEqual(self.data(pg)['reviews'][1]['independence'], {'mode': 'kept'})
        # the zip holds only one's own records unless asked
        pg.click('#ws-menu-btn')
        with pg.expect_download() as dl:
            pg.click('#btn-export-zip')
            pg.click('#confirm [data-choice="mine"]')
        with zipfile.ZipFile(dl.value.path()) as z:
            name = next(n for n in z.namelist() if n.endswith('review.yaml'))
            mine = review_record.load_text(z.read(name).decode('utf-8'))
        self.assertEqual([r['reviewer']['name'] for r in mine['reviews']], ['独立 A'])
        # after the submission the others' records are shown, and when they were first seen is recorded
        pg.click('#rv-submit')
        pg.click('#rv-verdict-comment')
        pg.click('#rv-submit-go')
        pg.wait_for_selector('#rv-next-steps')
        self.assertEqual(pg.evaluate('() => ClaimsReview.visibleNames()'), [other, '独立 A'])
        self.go(pg, '#/review/comments', 'コメント')
        self.assertGreater(int(pg.get_attribute('#rv-comment-list', 'data-comments')), 0)
        ind = self.data(pg)['reviews'][1]['independence']
        self.assertEqual(ind['mode'], 'kept')
        self.assertIn('viewed_others_at', ind)
        # a record changed after that is flagged
        self.go(pg, '#/review', 'レビューする行')
        pg.click('#rv-flt-all')
        a = pg.locator('.rv-row').first.get_attribute('data-anchor')
        pg.click(f'[data-viewed="{a}"]')
        self.assertTrue(self.data(pg)['reviews'][1]['viewed'][a]['edited_after_viewing_others'])
        self.check_text(pg.evaluate('() => ClaimsReview.text()'), B)
        # leaving before submitting (another reviewer): asked, and recorded with the reason
        pg2 = self.page()
        self.sample(pg2, 'b')
        self.start(pg2, '独立 B', independent=True)
        self.started(pg2, '独立 B')
        pg2.click('#rv-leave')
        pg2.click('#btn-start-review')
        pg2.fill('#rv-name', '独立 C')
        pg2.click('#rv-start-go')
        pg2.wait_for_selector('#confirm')
        self.assertIn('独立レビューを外れ', pg2.inner_text('#confirm'))
        pg2.click('#confirm [data-choice="break"]')
        self.started(pg2, '独立 C')
        b = next(r for r in self.data(pg2)['reviews'] if r['reviewer']['name'] == '独立 B')
        self.assertEqual(b['independence']['mode'], 'broken')
        self.assertIn('独立 C', b['independence']['reason'])
        self.assertEqual(pg.problems + pg2.problems, [])

    def test_review_records_are_not_sent_and_not_lost(self):
        ctx = self.context()
        pg = self.page(ctx)
        self.sample(pg, 'a')
        self.start(pg, '山田', kind='llm')
        self.started(pg, '山田')
        a = pg.locator('.rv-row').first.get_attribute('data-anchor')
        pg.click(f'[data-viewed="{a}"]')
        self.assertTrue(pg.evaluate('() => ClaimsReview.unsaved() && ClaimsEditor.unsaved()'))
        self.assertEqual(self.data(pg)['reviews'][0]['viewed'][a]['reviewer_kind'], 'llm')
        self.assertIn('LLM', pg.inner_text('#review-bar'))
        # closing with records that were not written out: asked first, and the zip offered holds review.yaml
        pg.click('#ws-menu-btn')
        pg.click('#btn-close')
        pg.wait_for_selector('#confirm')
        self.assertIn('レビューの記録', pg.inner_text('#confirm'))
        with pg.expect_download() as dl:
            pg.click('#confirm [data-choice="export"]')
        with zipfile.ZipFile(dl.value.path()) as z:
            self.assertTrue(any(n.endswith('/review.yaml') for n in z.namelist()), z.namelist())
        self.poll(pg, '() => !ClaimsEditor.state().open')
        self.assertTrue(pg.is_hidden('#review-bar'))
        self.assertTrue(pg.is_visible('#btn-start-review'))
        # with autosave on, the records are kept in this browser and offered when the design is opened again
        self.sample(pg, 'a')
        pg.click('#ws-menu-btn')
        pg.check('#chk-autosave')
        pg.keyboard.press('Escape')
        self.start(pg, '保存')
        self.started(pg, '保存')
        pg.click(f'[data-viewed="{a}"]')
        self.poll(pg, '() => Object.keys(localStorage).some((k) => k.startsWith("claims-editor:review:"))')
        pg.reload()
        pg.wait_for_selector('#btn-sample-a')
        pg.click('#btn-sample-a')
        pg.wait_for_selector('#confirm')
        self.assertIn('自動保存したレビューの記録', pg.inner_text('#confirm'))
        pg.click('#confirm [data-choice="saved"]')
        self.ready(pg)
        self.started(pg, '保存')
        self.assertIn(a, self.data(pg)['reviews'][0]['viewed'])
        # Escape on that question never overwrites the autosaved records
        pg.reload()
        pg.wait_for_selector('#btn-sample-a')
        pg.click('#btn-sample-a')
        pg.wait_for_selector('#confirm')
        before = pg.evaluate('() => Object.keys(localStorage).filter((k) => k.startsWith("claims-editor:review:")).map((k) => localStorage.getItem(k))')
        pg.keyboard.press('Escape')
        self.ready(pg)
        self.start(pg, '別の人')
        self.started(pg, '別の人')
        pg.click(f'[data-viewed="{a}"]')
        pg.wait_for_timeout(1500)
        self.assertEqual(pg.evaluate('() => Object.keys(localStorage).filter((k) => k.startsWith("claims-editor:review:")).map((k) => localStorage.getItem(k))'), before)
        self.assertIn('自動保存', pg.inner_text('#save-warn'))
        # nothing left this site
        bad = [r for r in ctx.requests if not r['url'].startswith(self.origin) and not r['url'].startswith(('blob:', 'data:'))]
        self.assertEqual(bad, [])
        self.assertEqual({r['method'] for r in ctx.requests}, {'GET'})
        if SHOTS:
            with open(os.path.join(ROOT, SHOTS, 'review-network-log.json'), 'w', encoding='utf-8', newline='\n') as f:
                json.dump({'origin': 'http://127.0.0.1:<port>', 'requests': sorted({(r['method'], r['url'].replace(self.origin, '').split('?')[0], r['type']) for r in ctx.requests})},
                          f, ensure_ascii=False, indent=1)
        self.assertEqual(pg.problems, [])

    def test_two_reviewers_files_are_shown_together_and_a_conflict_is_asked(self):
        pg = self.page()
        self.sample(pg, 'b')
        first = self.data(pg)
        name = first['reviews'][0]['reviewer']['name']
        other = json.loads(json.dumps(first))
        other['reviews'][0]['reviewer']['name'] = 'レビュアー B'
        other['reviews'][0]['comments'] = other['reviews'][0]['comments'][:1]
        ids = [c['id'] for c in other['reviews'][0]['comments']]
        for s in other['reviews'][0]['submissions']:
            s['comments'] = [i for i in s.get('comments', []) if i in ids]
        for fb in other['reviews'][0].get('feedback', []):
            fb['comments'] = [i for i in fb.get('comments', []) if i in ids]
        self.assertEqual(review_record.check(other, B)[0], [])
        r = pg.evaluate('t => ClaimsReview.importTexts([{ name: "review-b.yaml", text: t }])', review_record.dump(other))
        self.assertEqual(r['loaded'], 1)
        self.assertEqual(pg.evaluate('() => ClaimsReview.visibleNames()'), [name, 'レビュアー B'])
        self.go(pg, '#/review/record', '提出と記録')
        self.assertEqual(pg.locator('[data-table="reviewers"] tbody tr').count(), 2)
        # the same reviewer with other records: asked, nothing replaced silently
        clash = json.loads(json.dumps(other))
        clash['reviews'][0]['answers'] = {}
        pg.evaluate('t => { ClaimsReview.importTexts([{ name: "review-b2.yaml", text: t }]); }', review_record.dump(clash))
        pg.wait_for_selector('#confirm')
        self.assertIn('同じレビュアーの記録が 2 つあります', pg.inner_text('#confirm'))
        pg.click('#confirm [data-choice="both"]')
        self.poll(pg, '() => ClaimsReview.visibleNames().length === 3')
        self.check_text(pg.evaluate('() => ClaimsReview.text()'), B)
        self.assertEqual(pg.problems, [])

    def test_keyboard_and_names_of_the_review_controls(self):
        pg = self.page()
        self.sample(pg, 'a')
        # the dialog can be left with Escape, and the focus is in it
        pg.click('#btn-start-review')
        pg.wait_for_selector('#rv-start[open]')
        self.assertEqual(pg.get_attribute('#rv-start', 'aria-labelledby'), 'rv-start-h')
        pg.keyboard.press('Escape')
        self.poll(pg, '() => !document.querySelector("#rv-start")')
        self.start(pg, '山田')
        self.started(pg, '山田')
        self.assertEqual(pg.get_attribute('#review-bar', 'role'), 'region')
        self.assertEqual(pg.get_attribute('#rv-progress', 'role'), 'status')
        # every control of a row has a name; the mark is a checkbox with a label
        unnamed = pg.evaluate('''() => Array.from(document.querySelectorAll('#review-bar button, .rv-row button, .rv-row input, #rv-filter button, #rv-filter select'))
          .filter((e) => !((e.textContent || '').trim() || e.getAttribute('aria-label') || (e.labels && e.labels.length))).map((e) => e.outerHTML.slice(0, 80))''')
        self.assertEqual(unnamed, [])
        a = pg.locator('.rv-row').first.get_attribute('data-anchor')
        pg.locator(f'[data-viewed="{a}"]').focus()
        pg.keyboard.press('Space')
        self.poll(pg, 'a => document.querySelector(`.rv-row[data-anchor="${a}"]`).dataset.rowState === "viewed"', arg=a)
        self.assertEqual(pg.evaluate('() => document.activeElement.dataset.viewed'), a)
        # a comment on a column is written right under that column (the value stays in sight); found in the dry run of #67
        b = pg.locator('.rv-row').nth(1).get_attribute('data-anchor')
        pg.click(f'.rv-row[data-anchor="{b}"] .rv-row-title')
        col = pg.locator('.rv-row.open .rv-values .col').first.get_attribute('data-col')
        pg.click(f'[data-add-comment-col="{b}#{col}"]')
        self.assertEqual(pg.locator(f'.rv-row.open .col[data-col="{col}"] #rv-comment-form').count(), 1)
        self.assertEqual(pg.evaluate('() => document.activeElement.id'), 'rvc-content')
        pg.fill('#rvc-content', '列へのコメント')
        pg.click('#rvc-save')
        self.assertEqual(self.data(pg)['reviews'][0]['comments'][0]['column'], col)
        pg.click(f'.rv-row[data-anchor="{b}"] .rv-row-title')
        # the filter buttons say which is on
        self.assertEqual(pg.get_attribute('#rv-flt-all', 'aria-pressed'), 'true')
        pg.click('#rv-flt-todo')
        self.assertEqual(pg.get_attribute('#rv-flt-todo', 'aria-pressed'), 'true')
        self.assertEqual(pg.evaluate('() => document.activeElement.id'), 'rv-flt-todo')
        self.assertEqual(pg.locator(f'.rv-row[data-anchor="{a}"]').count(), 0)
        # 中断: the bar goes, the records stay, 「レビューを続ける」 comes back
        pg.click('#rv-leave')
        self.assertTrue(pg.is_hidden('#review-bar'))
        self.assertIn('レビューを続ける', pg.inner_text('#btn-start-review'))
        self.assertIn(a, self.data(pg)['reviews'][0]['viewed'])
        self.assertEqual(pg.problems, [])


if __name__ == '__main__':
    unittest.main()
