# -*- coding: utf-8 -*-
"""The review mode of the design editor (#50) in headless Chromium.

  pip install playwright && python -m playwright install chromium
  python -m pytest -q tools/tests/test_claims_review_ui.py
  CLAIMS_EDITOR_EVIDENCE=research/claims-editor python -m pytest -q tools/tests/test_claims_review_ui.py   # also save
      screenshots and the network log of the review mode

Skipped when Playwright or its browser is not installed (the CI jobs have no browser; run them locally, as the tests of
#49 in test_claims_editor_ui.py). One test per criterion of #50:
  the checklist shows all 168 questions of perspectives.md, filtered by the 6 stages x the roles, and every 見る欄 moves
  to its field; a row decision is bound to the row hash and an edit of the row invalidates it (再確認が要る), a removed
  row keeps its record; review.yaml is written and read back byte for byte and two reviewers' files are shown together
  (a conflict is asked about); the analysis (coverage, lint x review, the diff against a base version, the seeded draw)
  works; the report of the recorded review of scenario B is the committed one and follows report_template.md; in
  independent mode the other reviewers' records are hidden until one submits; nothing is sent (the network log), the
  review records are never dropped without a question, and another tab saving the same design is told; the leftovers
  of the PR #51 check (`=` and `[:1]` are YAML11 errors, `.inf` / `.nan` keys hash alike in both readers).
"""
import functools
import http.server
import json
import os
import pathlib
import socketserver
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
B = os.path.join(ROOT, 'templates', 'examples', 'scenario-b')
A = os.path.join(ROOT, 'templates', 'examples', 'scenario-a')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import review_check  # noqa: E402
import review_record  # noqa: E402
import row_hash  # noqa: E402
import trace_check  # noqa: E402
try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read().replace('\r\n', '\n')


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@unittest.skipIf(sync_playwright is None, 'playwright not installed')
class ReviewMode(unittest.TestCase):
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
        persp = trace_check._read(os.path.join(ROOT, 'templates', 'review', 'perspectives.md'))
        cls.questions = review_check.parse_questions(persp)
        cls.roles, cls.stages = review_check.roles_and_stages(persp, cls.questions)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.srv.shutdown()

    def context(self):
        ctx = self.browser.new_context(viewport={'width': 1500, 'height': 950}, accept_downloads=True)
        ctx.requests = []
        ctx.on('request', lambda r: ctx.requests.append({'method': r.method, 'url': r.url, 'type': r.resource_type}))
        self.addCleanup(ctx.close)
        return ctx

    def page(self, ctx=None):
        ctx = ctx or self.context()
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

    def sample(self, pg, letter):
        pg.click(f'#btn-sample-{letter}')
        self.poll(pg, '() => ClaimsEditor.state().open && document.querySelectorAll("#tabs [role=tab]").length > 0 && ClaimsReview.ready()')
        pg.wait_for_timeout(300)

    def shot(self, pg, name):
        if EVIDENCE:
            pg.screenshot(path=os.path.join(ROOT, EVIDENCE, name + '.jpg'), type='jpeg', quality=70, full_page=False)

    def become(self, pg, name, kind='human'):
        self.go(pg, '#/review', 'レビュー')
        pg.fill('#rv-name', name)
        pg.select_option('#rv-kind', kind)
        pg.click('#rv-new-go')
        self.poll(pg, 'n => ClaimsReview.me() === n', arg=name)

    def second_reviewer(self, tmp, name='レビュアー B（人）'):
        """A review.yaml of another reviewer of scenario B, written by tools/review_record.py (Python)."""
        h = row_hash.row_hashes(B)['hashes']
        data = {'format': 'claims-review/1', 'design': 'templates/examples/scenario-b', 'independent': False, 'reviews': [{
            'reviewer': {'name': name, 'kind': 'human'}, 'self_declared': True, 'started': '2026-11-24', 'submitted': None,
            'answers': {'dc-01': {'answer': 'yes', 'memo': '人の確認'}, 'ap-1-1': {'answer': 'na', 'memo': 'テスト'}},
            'rows': {'claims:C-iss': {'decision': 'approve', 'hash': h['claims:C-iss'], 'at': '2026-11-24T10:00:00Z', 'comment': '確認した'}},
            'findings': [{'id': 'F01', 'location': 'C-iss.enforced_at', 'anchors': ['claims:C-iss'], 'content': '人の指摘（テスト）', 'severity': 'Minor',
                          'origin': 'テンプレート外', 'kind': '目的と仕組みの不一致', 'confused_question': '`q-peer` を `req_wl` で答えた', 'verdict': '保留',
                          'response': {'state': '未着手'}}]}]}
        p = os.path.join(tmp, 'review-b2.yaml')
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(review_record.dump(data))
        return p, data

    # ------------------------------------------------------------------ 1. the checklist: 168 questions, stage x role, 見る欄
    def test_checklist_shows_all_questions_by_stage_and_role_and_moves_to_each_field(self):
        pg = self.page()
        self.sample(pg, 'b')
        self.go(pg, '#/review/checklist?triage=all', '観点のチェックリスト')
        ids = pg.evaluate('() => Array.from(document.querySelectorAll(".rv-q")).map(e => e.dataset.q)')
        self.assertEqual(ids, [q['id'] for q in self.questions])
        self.assertEqual(len(ids), 168)
        role_of = {r['id']: set(r['questions']) for r in self.roles}
        visible = '() => Array.from(document.querySelectorAll(".rv-q")).filter(e => !e.hidden).map(e => e.dataset.q)'
        combos = 0
        for s in [None] + [x['id'] for x in self.stages]:
            for r in [None] + list(role_of) + ['none']:
                pg.select_option('#rv-f-stage', s or '')
                pg.select_option('#rv-f-role', r or '')
                want = [q['id'] for q in self.questions if (not s or q['stage'] == s) and
                        (not r or (q['id'] not in set().union(*role_of.values()) if r == 'none' else q['id'] in role_of[r]))]
                self.assertEqual(pg.evaluate(visible), want, (s, r))
                combos += 1
        self.assertEqual(combos, 7 * 8)
        self.assertIn('stage=stage-operations', pg.evaluate('() => location.hash'))
        pg.select_option('#rv-f-stage', '')
        pg.select_option('#rv-f-role', '')
        # every ref of every 見る欄 is a link or a button to its field
        n_refs = sum(len([m for m in review_check.REF_IN_TICKS.finditer(q['fields']['見る欄']) if m.group(1).split(':')[0] in ('template', 'registry', 'catalog', 'review')])
                     for q in self.questions)
        self.assertEqual(pg.evaluate('() => document.querySelectorAll(".rv-q [data-see]").length'), n_refs)
        # a registry column: the column of every row
        pg.click('#q-dc-01 [data-see="registry:claims#usage"]')
        self.poll(pg, '() => document.querySelector("main h1[data-column=\'claims.usage\']")')
        self.assertGreater(pg.evaluate('() => document.querySelectorAll("table[data-table=column] tbody tr").length'), 40)
        # a section of the design: design.md at the heading of the same number (8. ホップごとの表)
        self.go(pg, '#/review/checklist?triage=all', '観点のチェックリスト')
        btn = pg.locator('[data-see="template:00_core#hop-table"]').first
        line = int(btn.get_attribute('data-see-line'))
        btn.click()
        self.assertEqual(pg.evaluate('() => ClaimsEditor.state().active'), 'design.md')
        self.assertTrue(read(os.path.join(B, 'design.md')).split('\n')[line - 1].startswith('## 8. '))
        # an answer of the 25 questions: every claim_request_*.md at question 13
        self.go(pg, '#/review/checklist?triage=all', '観点のチェックリスト')
        pg.locator('[data-see="template:claim_request#q13"]').first.click()
        self.poll(pg, '() => document.querySelector("main h1[data-pa=\'13\']")')
        n_req = len([x for x in os.listdir(B) if x.startswith('claim_request_')])
        self.assertEqual(pg.evaluate('() => document.querySelectorAll("table[data-table=pa] tbody tr").length'), n_req)
        # keyboard and not by colour only: each answer is a radio group with a legend, the state is written as text
        self.go(pg, '#/review/checklist?triage=all', '観点のチェックリスト')
        self.assertEqual(pg.evaluate('() => document.querySelectorAll(".rv-ans legend").length'), 168)
        self.become(pg, 'キーボードの人')
        self.go(pg, '#/review/checklist?triage=all', '観点のチェックリスト')
        pg.focus('#q-dc-02 input[value="no"]')
        pg.keyboard.press('Space')
        self.poll(pg, '() => ClaimsReview.data().reviews.find(r => r.reviewer.name === "キーボードの人").answers["dc-02"].answer === "no"')
        self.assertTrue(pg.is_visible('#q-dc-02 .rv-findbtn'))
        self.shot(pg, '50_review_checklist')
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ 2. a decision is bound to the row hash
    def test_a_row_decision_is_invalidated_when_the_row_changes(self):
        pg = self.page()
        self.sample(pg, 'a')
        self.become(pg, '確認する人')
        self.go(pg, '#/claim/C-iss', '(C-iss)')
        pg.check('[data-review-panel="claims:C-iss"] input[value="approve"]')
        pg.fill('[data-review-panel="claims:C-iss"] textarea', '読んだ')
        pg.click('[data-record="claims:C-iss"]')
        self.poll(pg, '() => document.querySelector("[data-review-panel=\'claims:C-iss\'] [data-review-state=approve]")')
        h0 = pg.evaluate('() => ClaimsEditor.rowHash("claims:C-iss")')
        rec = pg.evaluate('() => ClaimsReview.data().reviews[0].rows["claims:C-iss"]')
        self.assertEqual(rec['hash'], h0)
        self.assertEqual(rec['hash'], row_hash.row_hashes(A)['hashes']['claims:C-iss'])  # the same hash as tools/row_hash.py
        self.go(pg, '#/claims', 'クレームの一覧')
        self.assertIn('承認', pg.inner_text('tr[data-anchor="claims:C-iss"] [data-review-for="claims:C-iss"]'))
        # a comment in the YAML changes nothing
        pg.evaluate('() => ClaimsEditor.replaceText("claims.yaml", "  - id: C-iss\\n", "  - id: C-iss  # note\\n")')
        pg.wait_for_timeout(700)
        self.assertEqual(pg.get_attribute('tr[data-anchor="claims:C-iss"] [data-review-for="claims:C-iss"]', 'data-review-state'), 'approve')
        # a value of the row: 再確認が要る, everywhere
        pg.evaluate('() => ClaimsEditor.replaceText("claims.yaml", "  - id: C-iss  # note\\n", "  - id: C-iss\\n    x_changed_after_approval: 1\\n")')
        self.poll(pg, '() => (document.querySelector("tr[data-anchor=\'claims:C-iss\'] [data-review-for=\'claims:C-iss\']") || {}).dataset?.reviewState === "stale"')
        self.assertIn('再確認が要る', pg.inner_text('tr[data-anchor="claims:C-iss"]'))
        self.go(pg, '#/review', 'レビュー')
        self.assertIn('claims:C-iss', pg.inner_text('#rv-attention'))
        self.go(pg, '#/review/rows?state=stale', '行ごとの判定')
        self.poll(pg, '() => document.querySelectorAll("table[data-table=review-rows] tbody tr").length === 1')
        self.shot(pg, '51_review_stale')
        pg.click('[data-rerecord="claims:C-iss"]')
        self.poll(pg, 'h => ClaimsReview.data().reviews[0].rows["claims:C-iss"].hash !== h', arg=h0)
        self.assertEqual(pg.evaluate('() => ClaimsReview.data().reviews[0].rows["claims:C-iss"].hash'), pg.evaluate('() => ClaimsEditor.rowHash("claims:C-iss")'))
        # a removed row (its id changed): the record is kept and listed, not dropped
        pg.evaluate('() => ClaimsEditor.replaceText("claims.yaml", "  - id: C-iss\\n", "  - id: C-iss-renamed\\n")')
        self.poll(pg, '() => !ClaimsEditor.anchors().some(a => a.anchor === "claims:C-iss")')
        self.go(pg, '#/review', 'レビュー')
        self.assertTrue(pg.is_visible('[data-missing="claims:C-iss"]'))
        self.assertIn('claims:C-iss', pg.evaluate('() => Object.keys(ClaimsReview.data().reviews[0].rows)'))
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ 3. review.yaml round trip, two reviewers
    def test_review_yaml_round_trip_and_two_reviewers_shown_together(self):
        pg = self.page()
        self.sample(pg, 'b')
        committed = read(os.path.join(B, 'review.yaml'))
        self.assertEqual(pg.evaluate('() => ClaimsReview.text()'), committed)
        self.assertFalse(pg.evaluate('() => ClaimsReview.unsaved()'))
        self.go(pg, '#/review', 'レビュー')
        with pg.expect_download() as dl:
            pg.click('#rv-export')
        self.assertEqual(dl.value.suggested_filename, 'review.yaml')
        self.assertEqual(pathlib.Path(dl.value.path()).read_bytes().decode('utf-8'), committed)
        with tempfile.TemporaryDirectory() as tmp:
            p, other = self.second_reviewer(tmp)
            pg.set_input_files('#rv-import', [p])
            self.poll(pg, '() => ClaimsReview.visibleNames().length === 2')
            self.go(pg, '#/review', 'レビュー')
            self.assertEqual(pg.evaluate('() => document.querySelectorAll("table[data-table=reviewers] tbody tr").length'), 2)
            self.go(pg, '#/claims', 'クレームの一覧')
            badges = pg.evaluate('() => Array.from(document.querySelectorAll("tr[data-anchor=\'claims:C-iss\'] [data-review-for]")).map(e => [e.dataset.reviewBy, e.dataset.reviewState])')
            self.assertEqual(sorted(badges), sorted([['Claude Opus 5.5（LLM の一次スクリーニング）', 'request_changes'], ['レビュアー B（人）', 'approve']]))
            self.go(pg, '#/review/findings', '指摘')
            self.assertEqual(pg.evaluate('() => document.querySelectorAll("tr[data-finding-by=\'レビュアー B（人）\']").length'), 1)
            # the merged file is what tools/review_record.py merge writes
            want = review_record.dump(review_record.merge([review_record.load(os.path.join(B, 'review.yaml')), other]))
            self.go(pg, '#/review', 'レビュー')
            with pg.expect_download() as dl:
                pg.click('#rv-export')
            got = pathlib.Path(dl.value.path()).read_bytes().decode('utf-8')
            self.assertEqual(got, want)
            # read back: the same text again (a round trip of a file with two reviewers)
            p2 = os.path.join(tmp, 'review.yaml')
            pathlib.Path(p2).write_text(got, encoding='utf-8')
            pg.click('#btn-close')
            self.poll(pg, '() => !ClaimsEditor.state().open && !document.querySelector("dialog#confirm")')
            self.sample(pg, 'b')
            self.go(pg, '#/review', 'レビュー')
            pg.set_input_files('#rv-import', [p2])  # the LLM review is the same: merged without a question
            self.poll(pg, '() => ClaimsReview.visibleNames().length === 2')
            self.assertEqual(pg.evaluate('() => ClaimsReview.text()'), got)
            # the same reviewer with other records: asked, and kept under another name when asked to keep both
            other['reviews'][0]['answers']['dc-02'] = {'answer': 'no', 'memo': '別の版'}
            p3 = os.path.join(tmp, 'review-b3.yaml')
            pathlib.Path(p3).write_text(review_record.dump(other), encoding='utf-8')
            self.go(pg, '#/review', 'レビュー')
            pg.set_input_files('#rv-import', [p3])
            pg.wait_for_selector('dialog#confirm[open]')
            self.assertIn('同じレビュアーの記録が 2 つ', pg.inner_text('dialog#confirm'))
            pg.click('dialog#confirm [data-choice="both"]')
            self.poll(pg, '() => ClaimsReview.visibleNames().includes("レビュアー B（人） (2)")')
            self.assertEqual(len(pg.evaluate('() => ClaimsReview.visibleNames()')), 3)
            self.assertTrue(pg.evaluate('() => ClaimsReview.unsaved()'))
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ 4. the analysis
    def test_analysis_coverage_overlay_diff_and_sampling(self):
        pg = self.page()
        self.sample(pg, 'b')
        self.go(pg, '#/review/analysis', '分析')
        self.assertEqual(pg.inner_text('[data-cov="all|all"]').split('（')[0].strip(), '168 / 168')
        rv = review_record.load(os.path.join(B, 'review.yaml'))['reviews'][0]
        for s in self.stages:
            n = sum(1 for q in self.questions if q['stage'] == s['id'])
            a = sum(1 for q in self.questions if q['stage'] == s['id'] and q['id'] in rv['answers'])
            self.assertEqual(pg.inner_text(f'[data-cov="{s["id"]}|all"]').split('（')[0].strip(), f'{a} / {n}')
        # lint x review: the rows with a decision or a finding, those that need attention first
        rows = pg.evaluate('() => Array.from(document.querySelectorAll("table[data-table=overlay] tbody tr[data-anchor]")).map(e => [e.dataset.anchor, +e.dataset.flags])')
        self.assertGreater(len(rows), 40)
        self.assertEqual([f for _, f in rows], sorted([f for _, f in rows], reverse=True))
        # the diff against a base version: one row changed in the base files
        with tempfile.TemporaryDirectory() as tmp:
            for n in ('claims.yaml', 'token_types.yaml', 'hops.yaml', 'catalog_answers.yaml'):
                t = read(os.path.join(B, n))
                if n == 'hops.yaml':
                    t = t.replace('  - id: H1\n', '  - id: H1\n    x_base_version: 1\n', 1)
                pathlib.Path(tmp, n).write_text(t, encoding='utf-8')
            self.assertEqual(review_record.main(['diff', tmp, B]), 0)
            pg.set_input_files('#rv-base-files', [os.path.join(tmp, n) for n in ('claims.yaml', 'token_types.yaml', 'hops.yaml', 'catalog_answers.yaml')])
            self.poll(pg, '() => document.querySelector("#rv-diff")')
            self.assertEqual(pg.get_attribute('#rv-diff', 'data-changed'), '1')
            self.assertIn('hops:H1', pg.inner_text('#rv-diff'))
            self.go(pg, '#/review/rows?changed=1', '行ごとの判定')
            self.poll(pg, '() => document.querySelectorAll("table[data-table=review-rows] tbody tr").length === 1')
            self.assertEqual(pg.get_attribute('table[data-table=review-rows] tbody tr', 'data-anchor'), 'hops:H1')
        # 25 answers, contrasts and the decision tree
        self.go(pg, '#/review/analysis', '分析')
        self.assertGreater(pg.evaluate('() => document.querySelectorAll("#rv-a-links ~ ul a[href*=\'decision_tree\']").length'), 5)
        # the seeded draw of rejection rationales: the same rows as tools/review_record.py sample, the seed recorded
        self.become(pg, '抜き取る人')
        self.go(pg, '#/review/analysis', '分析')
        pg.fill('#rv-seed', 'seed-42')
        pg.select_option('#rv-seed-count', '2')
        pg.click('#rv-draw')
        self.poll(pg, '() => document.querySelector("#rv-picked")')
        want = review_record.sample('seed-42', 2, row_hash.load(B))
        self.assertEqual(pg.get_attribute('#rv-picked', 'data-picked').split(' '), want)
        me = pg.evaluate('() => ClaimsReview.data().reviews.find(r => r.reviewer.name === "抜き取る人").sampling')
        self.assertEqual((me['seed'], me['count'], me['picked']), ('seed-42', 2, want))
        for i in range(1, 8):
            pg.select_option(f'[data-rr="{want[0]}.RR{i}"]', '満' if i != 3 else '否')
        self.poll(pg, 'a => ClaimsReview.data().reviews.find(r => r.reviewer.name === "抜き取る人").sampling.scores[a].pass === false', arg=want[0])
        self.shot(pg, '52_review_analysis')
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ 5. the report of scenario B
    def test_the_report_of_scenario_b_is_the_committed_one_and_follows_the_form(self):
        pg = self.page()
        self.sample(pg, 'b')
        self.go(pg, '#/review/report', 'レビューレポート')
        text = pg.inner_text('#rv-report')
        committed = read(os.path.join(B, 'review-report-2026-11-23.md'))
        self.assertEqual(pg.evaluate('() => ClaimsReview.reportText()'), committed)
        self.assertEqual(review_check.check_report(ROOT, committed), [])
        self.assertTrue(text.startswith('# レビューレポート：'))
        with pg.expect_download() as dl:
            pg.click('#rv-report-download')
        self.assertEqual(dl.value.suggested_filename, 'review-report-2026-11-23.md')
        self.assertEqual(pathlib.Path(dl.value.path()).read_bytes().decode('utf-8'), committed)
        self.assertIn('人による点検は未実施', committed)
        self.assertIn('自己申告', committed)
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ 6. independent review
    def test_independent_mode_hides_the_others_until_submitted(self):
        pg = self.page()
        self.sample(pg, 'b')
        self.become(pg, '独立のレビュアー')
        pg.check('#rv-independent')
        self.poll(pg, '() => ClaimsReview.data().independent === true')
        self.assertEqual(pg.evaluate('() => ClaimsReview.visibleNames()'), ['独立のレビュアー'])
        self.go(pg, '#/review/findings', '指摘')
        self.assertEqual(pg.evaluate('() => document.querySelectorAll("tr[data-finding]").length'), 0)
        self.assertIn('隠しています', pg.inner_text('main'))
        self.go(pg, '#/claim/C-iss', '(C-iss)')
        self.assertEqual(pg.evaluate('() => document.querySelectorAll("[data-review-panel] [data-review-by]").length'), 0)
        self.assertNotIn('payment-worker の enforced_at', pg.inner_text('main'))
        self.go(pg, '#/review/checklist?triage=all', '観点のチェックリスト')
        self.assertEqual(pg.evaluate('() => document.querySelectorAll(".rv-others").length'), 0)
        self.go(pg, '#/review/analysis', '分析')
        self.assertEqual(pg.inner_text('[data-cov="all|all"]').split('（')[0].strip(), '0 / 168')
        self.shot(pg, '53_review_independent')
        # submitting shows them
        self.go(pg, '#/review', 'レビュー')
        pg.click('#rv-submit')
        pg.click('dialog#confirm [data-choice="submit"]')
        self.poll(pg, '() => ClaimsReview.visibleNames().length === 2')
        self.go(pg, '#/review/findings', '指摘')
        self.assertEqual(pg.evaluate('() => document.querySelectorAll("tr[data-finding]").length'), 24)
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ 7. nothing is sent, nothing is lost
    def test_review_records_are_not_sent_and_not_lost(self):
        ctx = self.context()
        pg = self.page(ctx)
        initial = list(ctx.requests)
        self.sample(pg, 'a')
        self.become(pg, '送らない人')
        self.go(pg, '#/review/checklist?triage=all', '観点のチェックリスト')
        pg.check('#q-dc-01 input[value="yes"]')
        self.poll(pg, '() => ClaimsReview.unsaved()')
        self.go(pg, '#/claim/C-iss', '(C-iss)')
        pg.check('[data-review-panel="claims:C-iss"] input[value="hold"]')
        pg.click('[data-record="claims:C-iss"]')
        for sub in ('rows', 'findings', 'analysis', 'pa', 'report'):
            self.go(pg, '#/review/' + sub)
        # closing with records not written out asks; the zip has review.yaml
        pg.click('#btn-close')
        pg.wait_for_selector('dialog#confirm[open]')
        self.assertIn('レビューの記録', pg.inner_text('dialog#confirm'))
        pg.click('dialog#confirm [data-choice="cancel"]')
        self.poll(pg, '() => !document.querySelector("dialog#confirm")')
        self.assertTrue(pg.evaluate('() => ClaimsEditor.state().open'))
        with pg.expect_download() as dl:
            pg.click('#btn-close')
            pg.click('dialog#confirm [data-choice="export"]')
        with zipfile.ZipFile(dl.value.path()) as z:
            data = review_record.load_text(z.read('scenario-a/review.yaml').decode('utf-8'))
        self.assertEqual(data['reviews'][0]['answers']['dc-01']['answer'], 'yes')
        self.assertEqual(review_record.check(data, A)[0], [])
        self.poll(pg, '() => !ClaimsEditor.state().open')
        bad = [r for r in ctx.requests if r['method'] != 'GET' or not (r['url'].startswith(self.origin + '/') or r['url'].startswith('blob:' + self.origin))
               or r['type'] in ('ping', 'beacon', 'websocket', 'eventsource')]
        self.assertEqual(bad, [])
        if EVIDENCE:
            o = lambda u: u.replace(self.origin, '<origin>')  # noqa: E731
            with open(os.path.join(ROOT, EVIDENCE, 'review-network-log.json'), 'w', encoding='utf-8', newline='\n') as f:
                json.dump({'what': 'Playwright (Chromium) network log of the review mode (#50): every request of the page while '
                                   'a reviewer is created, a question answered, a row decided, every review screen opened and '
                                   'the zip with review.yaml written (tools/tests/test_claims_review_ui.py::test_review_records_are_not_sent_and_not_lost)',
                           'browser': f'chromium {self.browser.version}',
                           'summary': {'requests': len(ctx.requests), 'methods': sorted({r['method'] for r in ctx.requests}),
                                       'non_get_or_cross_origin_or_beacon': len(bad)},
                           'initial_load_requests': [dict(r, url=o(r['url'])) for r in initial],
                           'session_requests': [dict(r, url=o(r['url'])) for r in ctx.requests[len(initial):]]},
                          f, ensure_ascii=False, indent=1)
                f.write('\n')
        self.assertEqual(pg.problems, [])

    def test_another_tab_saving_the_same_design_is_told(self):
        ctx = self.context()
        p1 = self.page(ctx)
        p2 = self.page(ctx)
        for pg in (p1, p2):
            self.sample(pg, 'a')
        p1.check('#chk-autosave')
        p1.evaluate('() => ClaimsEditor.replaceText("hops.yaml", "hops:", "hops:  # tab 1")')
        self.poll(p2, '() => document.querySelector("#tab-warn [data-foreign=\'claims-editor:autosave:v2:templates/examples/scenario-a\']")')
        self.assertIn('別のタブ', p2.inner_text('#tab-warn'))
        # the review records too
        self.become(p1, 'タブ 1 の人')
        self.go(p1, '#/review/checklist?triage=all', '観点のチェックリスト')
        p1.check('#q-dc-01 input[value="no"]')
        self.poll(p2, '() => document.querySelector("#tab-warn [data-foreign=\'claims-editor:review:v1:templates/examples/scenario-a\']")')
        p2.click('[data-foreign-load="claims-editor:review:v1:templates/examples/scenario-a"]')
        self.poll(p2, '() => ClaimsReview.data().reviews.some(r => r.reviewer.name === "タブ 1 の人")')
        p2.click('[data-foreign-keep="claims-editor:autosave:v2:templates/examples/scenario-a"]')
        self.assertTrue(p2.is_hidden('#tab-warn'))
        self.assertEqual(p1.problems + p2.problems, [])

    # ------------------------------------------------------------------ the leftovers of the PR #51 check
    def test_pyyaml_errors_and_non_finite_keys(self):
        from claim_lint.core import _Loader
        pg = self.page()
        text = 'claims:\n  - id: C-a\n    eq: =\n    flow: [:1]\n    map: {:2}\n    ok: [a:1]\n'
        pg.click('#btn-paste')
        pg.fill('#paste-text', text)
        pg.select_option('#paste-kind', 'claims.yaml')
        pg.click('#paste-open')
        self.poll(pg, '() => ClaimsEditor.state().open')
        d = self.poll(pg, '() => { const d = ClaimsEditor.diagnostics().filter(x => x.rule === "YAML11"); return d.length >= 3 ? d : null; }')
        self.assertEqual(sorted((x['line'], x['severity']) for x in d), [(3, 'error'), (4, 'error'), (5, 'error')])
        for t in ('a: =\n', 'a: [:1]\n', 'a: {:1}\n'):  # PyYAML refuses each
            with self.assertRaises(yaml.YAMLError):
                yaml.load(t, Loader=_Loader)
        keys = '.inf: 1\n-.inf: 2\n.nan: 3\nx: {.Inf: a}\n'
        self.assertEqual(pg.evaluate('t => ClaimsEditor.canonicalYaml(t)', keys), row_hash.jcs(yaml.load(keys, Loader=_Loader)))
        pg.click('#btn-close')
        pg.click('dialog#confirm [data-choice="discard"]') if pg.is_visible('dialog#confirm') else None
        self.poll(pg, '() => !ClaimsEditor.state().open')
        pg.click('#btn-paste')
        pg.fill('#paste-text', 'claims:\n  - id: C-a\n    x: {.inf: 1}\n')
        pg.select_option('#paste-kind', 'claims.yaml')
        pg.click('#paste-open')
        d = self.poll(pg, '() => { const d = ClaimsEditor.diagnostics().filter(x => x.rule === "YAML11"); return d.length ? d : null; }')
        self.assertEqual([(x['line'], x['severity']) for x in d], [(3, 'warn')])
        self.assertEqual(pg.problems, [])

    # ------------------------------------------------------------------ the PR #52 check
    def test_leaving_independent_mode_is_asked_and_recorded(self):
        pg = self.page()
        self.sample(pg, 'b')
        llm = pg.evaluate('() => ClaimsReview.visibleNames()[0]')
        self.become(pg, '独立の X')
        pg.check('#rv-independent')
        self.poll(pg, '() => ClaimsReview.data().reviews.find(r => r.reviewer.name === "独立の X").independence.mode === "kept"')
        self.assertTrue(pg.is_visible('#rv-independence-limits'))
        # switching to the submitted LLM reviewer: asked; "やめる" keeps everything hidden
        pg.select_option('#rv-pick', llm)
        pg.click('#rv-pick-go')
        pg.wait_for_selector('dialog#confirm[open]')
        self.assertIn('独立レビューを外れる', pg.inner_text('dialog#confirm'))
        pg.keyboard.press('Escape')
        self.poll(pg, '() => !document.querySelector("dialog#confirm")')
        self.assertEqual(pg.evaluate('() => [ClaimsReview.me(), ClaimsReview.visibleNames()]'), ['独立の X', ['独立の X']])
        # typing the existing name: asked too
        pg.fill('#rv-name', llm)
        pg.click('#rv-new-go')
        pg.wait_for_selector('dialog#confirm[open]')
        pg.click('dialog#confirm [data-choice="cancel"]')
        self.assertEqual(pg.evaluate('() => ClaimsReview.me()'), '独立の X')
        # unchecking: asked
        pg.click('#rv-independent')
        pg.wait_for_selector('dialog#confirm[open]')
        pg.click('dialog#confirm [data-choice="cancel"]')
        self.poll(pg, '() => ClaimsReview.data().independent === true')
        # writing out every record: asked; "自分の記録だけ" writes only mine
        self.go(pg, '#/review', 'レビュー')
        pg.click('#rv-export')
        pg.wait_for_selector('dialog#confirm[open]')
        with pg.expect_download() as dl:
            pg.click('dialog#confirm [data-choice="mine"]')
        mine = review_record.load_text(pathlib.Path(dl.value.path()).read_bytes().decode('utf-8'))
        self.assertEqual([r['reviewer']['name'] for r in mine['reviews']], ['独立の X'])
        self.assertEqual(pg.evaluate('() => ClaimsReview.visibleNames()'), ['独立の X'])
        # leaving on purpose: recorded with when and why; the others' records then seen; later edits are marked
        pg.click('#rv-independent')
        pg.wait_for_selector('dialog#confirm[open]')
        pg.click('dialog#confirm [data-choice="break"]')
        self.poll(pg, '() => ClaimsReview.visibleNames().length === 2')
        self.go(pg, '#/review/findings', '指摘')
        ind = self.poll(pg, '() => { const r = ClaimsReview.data().reviews.find(r => r.reviewer.name === "独立の X"); return r.independence.viewed_others_at ? r.independence : null; }')
        self.assertEqual((ind['mode'], ind['reason']), ('broken', '独立レビューの設定を外した'))
        self.go(pg, '#/review/checklist?triage=all', '観点のチェックリスト')
        pg.check('#q-dc-03 input[value="yes"]')
        self.poll(pg, '() => ClaimsReview.data().reviews.find(r => r.reviewer.name === "独立の X").answers["dc-03"].edited_after_viewing_others === true')
        rep = pg.evaluate('() => ClaimsReview.reportText("独立の X")')
        self.assertIn('独立レビュー：提出の前に外れた', rep)
        self.assertIn('その後に直した記録 1 件', rep)
        self.assertEqual(review_check.check_report(ROOT, rep), [])
        self.assertEqual(pg.problems, [])

    def test_zip_export_in_independent_mode_puts_only_own_records_unless_asked(self):
        # PR #52 re-check: "zip で書き出す" and "zip で書き出してから閉じる" wrote every reviewer's records silently
        pg = self.page()
        self.sample(pg, 'b')
        llm = pg.evaluate('() => ClaimsReview.visibleNames()[0]')
        self.become(pg, 'zip の X')
        pg.check('#rv-independent')
        self.go(pg, '#/review/checklist?triage=all', '観点のチェックリスト')
        pg.check('#q-dc-01 input[value="yes"]')
        self.poll(pg, '() => ClaimsReview.unsaved()')

        def names_in(dl):
            with zipfile.ZipFile(dl.value.path()) as z:
                return [r['reviewer']['name'] for r in review_record.load_text(z.read('scenario-b/review.yaml').decode('utf-8'))['reviews']]
        # 1. the button: asked; the first choice puts my records only, nothing is recorded, the rest stays unsaved
        pg.click('#btn-export-zip')
        pg.wait_for_selector('dialog#confirm[open]')
        self.assertIn('zip に入れる review.yaml', pg.inner_text('dialog#confirm'))
        with pg.expect_download() as dl:
            pg.click('dialog#confirm [data-choice="mine"]')
        self.assertEqual(names_in(dl), ['zip の X'])
        me = 'r => r.reviewer.name === "zip の X"'
        self.assertEqual(pg.evaluate(f'() => ClaimsReview.data().reviews.find({me}).independence.mode'), 'kept')
        self.assertTrue(pg.evaluate('() => ClaimsReview.unsaved()'))
        self.assertEqual(pg.evaluate('() => ClaimsReview.visibleNames()'), ['zip の X'])
        # Esc on that question: nothing is written
        pg.click('#btn-export-zip')
        pg.wait_for_selector('dialog#confirm[open]')
        pg.keyboard.press('Escape')
        self.poll(pg, '() => !document.querySelector("dialog#confirm")')
        # 2. closing with "zip で書き出してから閉じる": the same question; with my records only, the rest is asked about again
        pg.click('#btn-close')
        pg.wait_for_selector('dialog#confirm[open]')
        pg.click('dialog#confirm [data-choice="export"]')
        pg.wait_for_selector('dialog#confirm[open]')
        self.assertIn('zip に入れる review.yaml', pg.inner_text('dialog#confirm'))
        with pg.expect_download() as dl:
            pg.click('dialog#confirm [data-choice="mine"]')
        self.assertEqual(names_in(dl), ['zip の X'])
        pg.wait_for_selector('dialog#confirm[open]')
        self.assertIn('まだ書き出していない記録があります', pg.inner_text('dialog#confirm'))
        pg.click('dialog#confirm [data-choice="cancel"]')
        self.poll(pg, '() => !document.querySelector("dialog#confirm")')
        self.assertTrue(pg.evaluate('() => ClaimsEditor.state().open'))
        # every record: only when chosen, and recorded as leaving the independent review
        with pg.expect_download() as dl:
            pg.click('#btn-close')
            pg.click('dialog#confirm [data-choice="export"]')
            pg.wait_for_selector('dialog#confirm[open] [data-choice="all"]')
            pg.click('dialog#confirm [data-choice="all"]')
        self.assertEqual(sorted(names_in(dl)), sorted([llm, 'zip の X']))
        with zipfile.ZipFile(dl.value.path()) as z:
            data = review_record.load_text(z.read('scenario-b/review.yaml').decode('utf-8'))
        ind = next(r for r in data['reviews'] if r['reviewer']['name'] == 'zip の X')['independence']
        self.assertEqual((ind['mode'], ind['reason']), ('broken', '提出の前に全員の記録を zip で書き出した'))
        self.poll(pg, '() => !ClaimsEditor.state().open')
        self.assertEqual(pg.problems, [])

    def test_review_autosave_failure_is_shown_and_guarded(self):
        pg = self.page()
        self.sample(pg, 'a')
        pg.check('#chk-autosave')
        self.become(pg, '保存できない人')
        pg.evaluate('''() => { const orig = Storage.prototype.setItem;
            Storage.prototype.setItem = function (k, v) { if (String(k).startsWith('claims-editor:review:')) throw new DOMException('full', 'QuotaExceededError'); return orig.call(this, k, v); }; }''')
        self.go(pg, '#/review/checklist?triage=all', '観点のチェックリスト')
        pg.check('#q-dc-01 input[value="no"]')
        self.poll(pg, '() => (document.querySelector("#save-warn") || {}).textContent.includes("レビューの記録の自動保存に失敗")')
        self.assertTrue(pg.is_visible('#save-warn'))
        pg.click('#btn-close')
        pg.wait_for_selector('dialog#confirm[open]')
        self.assertIn('レビューの記録', pg.inner_text('dialog#confirm'))
        pg.click('dialog#confirm [data-choice="cancel"]')
        self.assertTrue(pg.evaluate('() => ClaimsEditor.state().open'))
        self.assertEqual(pg.problems, [])

    def test_escape_on_the_autosave_question_never_overwrites_it(self):
        pg = self.page()
        self.sample(pg, 'a')
        pg.check('#chk-autosave')
        self.become(pg, '保存した人')
        self.go(pg, '#/review/checklist?triage=all', '観点のチェックリスト')
        pg.check('#q-dc-01 input[value="yes"]')
        key = 'claims-editor:review:v1:templates/examples/scenario-a'
        saved = self.poll(pg, 'k => { const v = localStorage.getItem(k); return v && v.includes("保存した人") && v.includes("dc-01") ? v : null; }', arg=key, timeout=10)
        pg.click('#btn-close')
        self.poll(pg, '() => !ClaimsEditor.state().open')
        pg.click('#btn-sample-a')
        pg.wait_for_selector('dialog#confirm[open]')
        self.assertIn('自動保存したレビューの記録', pg.inner_text('dialog#confirm'))
        pg.keyboard.press('Escape')
        self.poll(pg, '() => ClaimsReview.ready() && !document.querySelector("dialog#confirm")')
        self.assertIn('自動保存を止めています', pg.inner_text('#save-warn'))
        # recording now does not write over the autosaved records
        self.become(pg, '別の人')
        self.go(pg, '#/review/checklist?triage=all', '観点のチェックリスト')
        pg.check('#q-dc-02 input[value="no"]')
        pg.wait_for_timeout(1500)
        self.assertEqual(pg.evaluate('k => localStorage.getItem(k)', key), saved)
        self.go(pg, '#/review', 'レビュー')
        self.assertTrue(pg.is_visible('#rv-slot-hold'))
        pg.click('#rv-slot-ask')
        pg.wait_for_selector('dialog#confirm[open]')
        pg.click('dialog#confirm [data-choice="merge"]')
        self.poll(pg, '() => ClaimsReview.data().reviews.map(r => r.reviewer.name).sort().join() === ["保存した人", "別の人"].sort().join()')
        self.assertEqual(pg.problems, [])

    def test_report_escaping_and_llm_labels_match_python(self):
        pg = self.page()
        self.sample(pg, 'b')
        d = review_record.load(os.path.join(B, 'review.yaml'))
        rv = d['reviews'][0]
        rv['reviewer']['name'] = '<b>悪い名前</b> | `x`'
        rv['context']['human_check'] = '# <!-- 7. を隠す'
        rv['answers']['dc-01']['memo'] = '<!-- hide / <script>x</script> / </details> / a | b / `c` / > q'
        rv['findings'][0]['content'] = '<img src=https://example.com/x.png> [l](https://example.com) *e* _e_ & ~~s~~'
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'evil.yaml')
            pathlib.Path(p).write_text(review_record.dump(d), encoding='utf-8')
            self.go(pg, '#/review', 'レビュー')
            pg.set_input_files('#rv-import', [p])
            self.poll(pg, 'n => ClaimsReview.visibleNames().includes(n)', arg=rv['reviewer']['name'])
        js = pg.evaluate('n => ClaimsReview.reportText(n)', rv['reviewer']['name'])
        py = review_record.report(d, B, review_record.review_data(), reviewer=rv['reviewer']['name'], version='0.4.0')
        self.assertEqual(js, py)
        self.assertNotIn('<!--', js)
        self.assertIn('人による点検は未実施', js.split('## 7. ')[1].split('## 8. ')[0])
        # the badges name the reviewer and say an LLM's decision is not checked by a person
        self.go(pg, '#/claims', 'クレームの一覧')
        b = pg.inner_text('tr[data-anchor="claims:C-iss"] [data-review-kind="llm"]')
        self.assertIn('人による点検は未実施', b)
        self.assertIn('Claude', b)
        # the checklist names each question in its answer group; a role filter says what it leaves out
        self.go(pg, '#/review/checklist?triage=all', '観点のチェックリスト')
        self.assertIn('dc-01', pg.inner_text('#q-dc-01 legend'))
        pg.select_option('#rv-f-role', 'role-attacker')
        self.assertTrue(pg.is_visible('#rv-role-note'))
        self.assertIn('役割の索引が未整備の問い', pg.inner_text('#rv-role-note'))
        self.assertIn('役割の索引が未整備の問い（121 問）', pg.inner_text('#rv-f-role'))
        # the rows a decision does not cover
        self.go(pg, '#/claim/C-roles', '(C-roles)')
        self.assertTrue(pg.is_visible('[data-dependents="claims:C-roles"]'))
        self.assertIn('claim_request_roles.md', pg.text_content('[data-dependents="claims:C-roles"]'))
        self.assertEqual(pg.problems, [])


if __name__ == '__main__':
    unittest.main()
