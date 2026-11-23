# -*- coding: utf-8 -*-
"""Tests of tools/build_claims_viewer.py and of the static files of the viewer (#36).

  python -m pytest -q tools/tests/test_build_claims_viewer.py

The browser tests (rendering, filters, every column on the detail screen, no network) are in
tools/tests/test_claims_viewer_ui.py and need Playwright.
"""
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import build_claims_viewer as bcv  # noqa: E402

VIEWER = os.path.join(ROOT, 'docs', 'claims')
JS_YAML = ('vendor/js-yaml-4.1.1.min.js', '0de3dec92d20eab9e0b46a5d928cd45ec025d73e348ddf458dbfb01da00cb473')
_EXPECTED = {}


def expected():
    if not _EXPECTED:
        _EXPECTED.update(bcv.expected())
    return _EXPECTED


def data_of(text):
    """The JSON assigned in a generated data file."""
    line = [x for x in text.split('\n') if x.startswith('window.CLAIMS_VIEWER_DATA[')][0]
    return json.loads(line.split(' = ', 1)[1].rstrip(';'))


class Build(unittest.TestCase):
    def test_committed_data_match_the_yaml(self):
        self.assertEqual(bcv.check(expected()), [], 'run: python tools/build_claims_viewer.py')

    def test_check_reports_a_changed_a_missing_and_a_stale_file(self):
        want = expected()
        d = tempfile.mkdtemp()
        old = bcv.OUT_DIR
        try:
            bcv.OUT_DIR = d
            for n, t in want.items():
                with open(os.path.join(d, n), 'w', encoding='utf-8', newline='\n') as f:
                    f.write(t)
            self.assertEqual(bcv.check(want), [])
            # CRLF (a Windows checkout) is not a difference
            with open(os.path.join(d, 'trace.js'), 'w', encoding='utf-8', newline='\r\n') as f:
                f.write(want['trace.js'])
            self.assertEqual(bcv.check(want), [])
            # one value changed in the YAML-derived data (C-iss max_bytes 63 -> 64)
            p = os.path.join(d, 'scenario-a.js')
            t = want['scenario-a.js']
            self.assertIn('"max_bytes":63', t)
            with open(p, 'w', encoding='utf-8', newline='\n') as f:
                f.write(t.replace('"max_bytes":63', '"max_bytes":64', 1))
            probs = bcv.check(want)
            self.assertEqual(len(probs), 1)
            self.assertIn('scenario-a.js: differs from the YAML', probs[0])
            os.remove(p)
            with open(os.path.join(d, 'old.js'), 'w', encoding='utf-8') as f:
                f.write('x')
            probs = bcv.check(want)
            self.assertTrue(any('scenario-a.js: missing' in x for x in probs), probs)
            self.assertTrue(any('old.js: not generated' in x for x in probs), probs)
        finally:
            bcv.OUT_DIR = old
            shutil.rmtree(d)

    def test_datasets_are_the_render_bundles(self):
        from claim_lint import render
        for i, rel, _ in bcv.DATASETS:
            b = data_of(expected()[f'{i}.js'])
            self.assertEqual(b['format'], render.BUNDLE_FORMAT)
            self.assertEqual(b['design'], rel)
            self.assertEqual(b['section_ids'], render.SECTION_IDS)
            self.assertEqual(set(b['registry']), {'claims', 'token_types', 'hops', 'catalog_answers'})


class Columns(unittest.TestCase):
    def test_every_schema_property_has_a_japanese_heading(self):
        cols, problems = bcv.columns()
        self.assertEqual(problems, [])
        for _, key, rel, pointer in bcv.COLUMN_SECTIONS:
            props, _ = bcv.schema_properties(rel, pointer)
            self.assertEqual([c['key'] for c in cols[key]], props, key)
            for c in cols[key]:
                self.assertTrue(c['label'] and re.search(r'[ぁ-んァ-ン一-龥]', c['label']) or c['label'] in ('typ', 'aud', 'scope', 'grant', 'JWE'), c)
        meta = data_of(expected()['meta.js'])
        self.assertEqual(len(meta['columns']['claims']), 73)
        aw = [c for c in meta['columns']['claims'] if c['key'] == 'authoritative_writer'][0]
        self.assertEqual([p['key'] for p in aw['parts']], ['stage', 'configurable_by'])

    def test_a_missing_heading_fails_the_build(self):
        with open(os.path.join(ROOT, bcv.README), encoding='utf-8') as f:
            text = f.read()
        d = tempfile.mkdtemp()
        old = bcv.README
        try:
            p = os.path.join(d, 'README.md')
            bad = re.sub(r'^\| `on_missing` \|.*\n', '', text, count=1, flags=re.M)
            self.assertNotEqual(bad, text)
            with open(p, 'w', encoding='utf-8') as f:
                f.write(bad)
            bcv.README = p
            _, problems = bcv.columns()
            self.assertEqual(problems, [f'{p}: claims.on_missing (a property of templates/registry/claims.schema.json) has no row in the column table'])
            with self.assertRaises(SystemExit):
                bcv.expected()
        finally:
            bcv.README = old
            shutil.rmtree(d)

    def test_review_questions_are_linked_to_columns(self):
        meta = data_of(expected()['meta.js'])
        usage = meta['review']['claims.usage']
        self.assertIn('dc-01', [q['id'] for q in usage])
        self.assertTrue(all(q['url'].startswith('https://github.com/Takenori-Kusaka/jwt-claims-guide/blob/main/templates/review/') for q in usage))
        # a question may also name a planned column (`registry:claims#trust_boundary`（未実装）); the detail screen
        # shows the questions of the columns that exist
        cols = {c['key'] for c in meta['columns']['claims']}
        linked = {k.split('.')[1] for k in meta['review'] if k.startswith('claims.')} & cols
        self.assertGreater(len(linked), 30)


class StaticFiles(unittest.TestCase):
    def read(self, rel):
        with open(os.path.join(VIEWER, rel), encoding='utf-8') as f:
            return f.read()

    def test_csp_forbids_connections(self):
        html = self.read('index.html')
        m = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', html)
        self.assertTrue(m)
        csp = {d.split()[0]: d.split()[1:] for d in m.group(1).split(';') if d.strip()}
        self.assertEqual(csp['connect-src'], ["'none'"])
        self.assertEqual(csp['default-src'], ["'none'"])
        self.assertEqual(csp['script-src'], ["'self'"])
        self.assertNotIn("'unsafe-inline'", m.group(1))

    def test_no_external_resources_and_no_network_api(self):
        html = self.read('index.html')
        for src in re.findall(r'<(?:script|link)[^>]+(?:src|href)="([^"]+)"', html):
            self.assertFalse(re.match(r'(?i)(https?:)?//', src), src)
        js = self.read('app.js')
        for api in ('fetch(', 'XMLHttpRequest', 'WebSocket', 'EventSource', 'sendBeacon', 'importScripts', 'innerHTML', 'eval('):
            self.assertNotIn(api, js, api)
        self.assertNotRegex(self.read('app.css'), r'url\(|@import')

    def test_vendored_library_is_pinned_with_its_license(self):
        rel, sha = JS_YAML
        with open(os.path.join(VIEWER, rel), 'rb') as f:
            # LF, as published on npm (a Windows checkout may have CRLF)
            self.assertEqual(hashlib.sha256(f.read().replace(b'\r\n', b'\n')).hexdigest(), sha)
        self.assertIn('js-yaml 4.1.1', self.read(rel)[:80])
        lic = self.read('vendor/js-yaml-4.1.1.LICENSE.txt')
        self.assertIn('MIT', lic)
        self.assertIn(rel, self.read('index.html'))

    def test_readmes_link_to_the_viewer(self):
        url = 'https://takenori-kusaka.github.io/jwt-claims-guide/claims/'
        for rel in ('README.md', 'templates/README.md'):
            with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
                self.assertIn(url, f.read(), rel)


if __name__ == '__main__':
    unittest.main()
