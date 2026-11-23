# -*- coding: utf-8 -*-
"""Tests of tools/build_claims_viewer.py and of the static files of the design editor (#49; the viewer of #36).

  python -m pytest -q tools/tests/test_build_claims_viewer.py

No browser is needed (CI). The browser tests (entry points, diagnostics, claim_lint in Pyodide vs the CLI, export,
network log) are in tools/tests/test_claims_editor_ui.py and need Playwright. Here, claim_lint is run from
data/claim_lint.zip with the driver of lint-worker.js under CPython, and compared with the CLI: the zip holds every file
claim_lint reads, and the driver gives the CLI result.
"""
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import build_claims_viewer as bcv  # noqa: E402

VIEWER = os.path.join(ROOT, 'docs', 'claims')
# the release asset of Pyodide 314.0.8 the vendored files come from (gh api repos/pyodide/pyodide/releases/tags/314.0.8)
PYODIDE_CORE_SHA256 = 'ff3e5f9d9bc8e98ff30b99515535fc24d375994f47a978c61975d653e162ca37'
_EXPECTED = {}


def expected():
    if not _EXPECTED:
        _EXPECTED.update(bcv.expected())
    return _EXPECTED


def data_of(text):
    """The JSON assigned in a generated data file."""
    if isinstance(text, bytes):
        text = text.decode('utf-8')
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
            old_viewer = bcv.VIEWER_DIR
            bcv.OUT_DIR = os.path.join(d, 'data')
            bcv.VIEWER_DIR = d
            os.makedirs(os.path.join(d, 'data'))
            os.makedirs(os.path.join(d, 'vendor'))
            for n, t in want.items():
                with open(os.path.join(d, *n.split('/')), 'wb') as f:
                    f.write(t if isinstance(t, bytes) else t.encode('utf-8'))
            self.assertEqual(bcv.check(want), [])
            # CRLF (a Windows checkout) is not a difference in a text file
            with open(os.path.join(d, 'data', 'trace.js'), 'w', encoding='utf-8', newline='\r\n') as f:
                f.write(want['data/trace.js'])
            self.assertEqual(bcv.check(want), [])
            # one value changed in the YAML-derived data (a sample file)
            p = os.path.join(d, 'data', 'sample-a.js')
            t = want['data/sample-a.js']
            self.assertIn('C-iss', t)
            with open(p, 'w', encoding='utf-8', newline='\n') as f:
                f.write(t.replace('C-iss', 'C-isx', 1))
            probs = bcv.check(want)
            self.assertEqual(len(probs), 1)
            self.assertIn('sample-a.js: differs from the YAML', probs[0])
            # one byte of the zip changed
            z = os.path.join(d, 'data', 'claim_lint.zip')
            with open(z, 'r+b') as f:
                f.seek(100)
                b = f.read(1)
                f.seek(100)
                f.write(bytes([b[0] ^ 1]))
            self.assertTrue(any('claim_lint.zip: differs' in x for x in bcv.check(want)))
            os.remove(p)
            with open(os.path.join(d, 'data', 'old.js'), 'w', encoding='utf-8') as f:
                f.write('x')
            probs = bcv.check(want)
            self.assertTrue(any('sample-a.js: missing' in x for x in probs), probs)
            self.assertTrue(any('old.js: not generated' in x for x in probs), probs)
        finally:
            bcv.OUT_DIR = old
            bcv.VIEWER_DIR = old_viewer
            shutil.rmtree(d)

    def test_samples_are_the_files_of_the_worked_examples(self):
        for i, rel, _, prof in bcv.DATASETS:
            s = data_of(expected()[f'data/sample-{i[-1]}.js'])
            self.assertEqual((s['design'], s['profile']), (rel, prof))
            d = os.path.join(ROOT, rel)
            want = sorted(n for n in os.listdir(d) if n in bcv.DESIGN_FILES or re.match(r'^claim_request_.+\.md$', n) or n == 'design.md')
            self.assertEqual(sorted(s['files']), want)
            for n, t in s['files'].items():
                with open(os.path.join(d, n), encoding='utf-8') as f:
                    self.assertEqual(t, f.read().replace('\r\n', '\n'), n)

    def test_skeleton_is_new_design(self):
        import new_design
        s = data_of(expected()['data/skeleton.js'])
        self.assertEqual(s['files'], new_design.build(os.path.join(ROOT, bcv.SKELETON_DIR)))
        self.assertIn('# yaml-language-server: $schema=../templates/registry/claims.schema.json', s['files']['claims.yaml'])

    def test_schemas_are_the_registry_schemas(self):
        s = data_of(expected()['data/schemas.js'])
        for k in ('claims', 'token_types', 'hops'):
            with open(os.path.join(ROOT, 'templates', 'registry', k + '.schema.json'), encoding='utf-8') as f:
                self.assertEqual(s[k], json.load(f))

    def test_meta_lists_the_samples(self):
        meta = data_of(expected()['data/meta.js'])
        self.assertEqual([d['id'] for d in meta['datasets']], ['scenario-a', 'scenario-b'])


class LintZip(unittest.TestCase):
    """data/claim_lint.zip and the driver of lint-worker.js, run with CPython (what Pyodide runs in the browser)."""

    def entries(self):
        with zipfile.ZipFile(io.BytesIO(expected()['data/claim_lint.zip'])) as z:
            return {i.filename: i for i in z.infolist()}, z

    def test_zip_is_stored_and_deterministic(self):
        a = bcv.lint_zip()
        self.assertEqual(a, bcv.lint_zip())
        infos, _ = self.entries()
        self.assertIn('tools/claim_lint/core.py', infos)
        self.assertIn('tools/check_slide_refs.py', infos)
        self.assertIn('tools/catalog_check.py', infos)
        self.assertIn('deck/slide_ids.json', infos)
        self.assertIn('templates/catalog/seeds.yaml', infos)
        self.assertIn('templates/registry/claims.schema.json', infos)
        self.assertFalse([n for n in infos if 'examples/' in n or '__pycache__' in n or n.endswith('.pyc')])
        for i in infos.values():
            self.assertEqual((i.compress_type, i.date_time), (zipfile.ZIP_STORED, (1980, 1, 1, 0, 0, 0)), i.filename)

    def driver(self):
        with open(os.path.join(VIEWER, 'lint-worker.js'), encoding='utf-8') as f:
            js = f.read()
        src = re.search(r'const DRIVER = `(.*?)`;', js, re.S).group(1)
        return src.replace('\\\\', '\\')  # the JS template literal escapes a backslash as two

    def test_driver_on_the_zip_gives_the_cli_result(self):
        import new_design  # noqa: F401  (tools/ is on sys.path)
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, 'repo')
            with zipfile.ZipFile(io.BytesIO(expected()['data/claim_lint.zip'])) as z:
                z.extractall(repo)
            for i, rel, _, prof in bcv.DATASETS:
                s = data_of(expected()[f'data/sample-{i[-1]}.js'])
                for profile in ('full', 'lite'):
                    code = (self.driver().replace("'/repo/", repr(repo.replace(os.sep, '/') + '/')[:-1])
                            + f'\nsys.stdout.buffer.write(lint_design({json.dumps(json.dumps(s["files"]))}, {rel!r}, {profile!r}).encode("utf-8"))\n')
                    script = os.path.join(tmp, 'drive.py')
                    with open(script, 'w', encoding='utf-8') as f:
                        f.write(code)
                    out = subprocess.run([sys.executable, script], capture_output=True, cwd=tmp)
                    self.assertEqual(out.returncode, 0, out.stderr.decode('utf-8', 'replace'))
                    got = json.loads(out.stdout.decode('utf-8'))
                    self.assertEqual(got['errors'], [])
                    cli = subprocess.run([sys.executable, os.path.join('tools', 'claim_lint'), rel, '--profile', profile, '--format', 'json',
                                          '--also-scan', rel + '/design.md'], cwd=ROOT, capture_output=True)
                    self.assertEqual(got['lint'], json.loads(cli.stdout.decode('utf-8')), f'{i} {profile}')
                    self.assertIn('ci-result', got['bundle']['section_ids'])


class Columns(unittest.TestCase):
    def test_every_schema_property_has_a_japanese_heading(self):
        cols, problems = bcv.columns()
        self.assertEqual(problems, [])
        for _, key, rel, pointer in bcv.COLUMN_SECTIONS:
            props, _ = bcv.schema_properties(rel, pointer)
            self.assertEqual([c['key'] for c in cols[key]], props, key)
            for c in cols[key]:
                self.assertTrue(c['label'] and re.search(r'[ぁ-んァ-ン一-龥]', c['label']) or c['label'] in ('typ', 'aud', 'scope', 'grant', 'JWE'), c)
        meta = data_of(expected()['data/meta.js'])
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
        meta = data_of(expected()['data/meta.js'])
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

    def csp(self):
        m = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', self.read('index.html'))
        self.assertTrue(m)
        return m.group(1), {d.split()[0]: d.split()[1:] for d in m.group(1).split(';') if d.strip()}

    def test_csp_allows_only_this_site(self):
        raw, csp = self.csp()
        self.assertEqual(csp['default-src'], ["'none'"])
        self.assertEqual(csp['connect-src'], ["'self'"])  # Pyodide's GETs of vendor/pyodide/ and data/claim_lint.zip
        self.assertEqual(csp['script-src'], ["'self'", "'wasm-unsafe-eval'"])  # WebAssembly only, no eval of JS
        self.assertEqual(csp['style-src'], ["'self'"])
        self.assertEqual(csp['worker-src'], ['blob:'])  # the lint worker is a blob: that inherits this policy
        for d in ('object-src', 'frame-src', 'base-uri', 'form-action'):
            self.assertEqual(csp[d], ["'none'"], d)
        for bad in ("'unsafe-inline'", "'unsafe-eval'", 'http:', 'https:', '*', 'data: blob:'):
            self.assertNotIn(' ' + bad + ';', ' ' + raw.replace("'wasm-unsafe-eval'", '') + ';', bad)
        self.assertNotIn('unsafe-eval', raw.replace("'wasm-unsafe-eval'", ''))

    def test_no_external_resources_and_no_sending_api(self):
        html = self.read('index.html')
        for src in re.findall(r'<(?:script|link)[^>]+(?:src|href)="([^"]+)"', html):
            self.assertFalse(re.match(r'(?i)(https?:)?//', src), src)
        for name in ('editor.js', 'preview.js', 'lint-worker.js'):
            js = self.read(name)
            for api in ('XMLHttpRequest', 'WebSocket', 'EventSource', 'sendBeacon', 'innerHTML', 'outerHTML', 'insertAdjacentHTML',
                        'eval(', 'new Function', 'document.write', "method: 'POST'", 'method: "POST"'):
                self.assertNotIn(api, js, (name, api))
        # the only fetch is the worker's GET of data/claim_lint.zip from the page's own directory
        self.assertEqual(re.findall(r'fetch\(([^,)]+)', self.read('lint-worker.js')), ["base + 'data/claim_lint.zip'"])
        self.assertNotIn('fetch(', self.read('editor.js') + self.read('preview.js'))
        self.assertNotRegex(self.read('app.css'), r'url\(|@import')

    def test_editor_opens_empty(self):
        # no sample is loaded by the page itself: the samples are loaded only by openSample (the buttons)
        html = self.read('index.html')
        self.assertNotIn('sample-', html)
        self.assertNotIn('skeleton', html)
        js = self.read('editor.js')
        self.assertEqual(re.findall(r"loadScript\(`data/sample-\$\{letter\}\.js`", js), ['loadScript(`data/sample-${letter}.js`'])
        self.assertRegex(js, r'function init\(\) \{[\s\S]*renderStart\(\);\n  \}')

    def test_vendored_files_match_the_manifest(self):
        man = json.loads(expected()['vendor/MANIFEST.json'])
        files = bcv.vendor_files()
        self.assertEqual(sorted(man['files']), files)
        for rel, info in man['files'].items():
            with open(os.path.join(VIEWER, 'vendor', *rel.split('/')), 'rb') as f:
                self.assertEqual(hashlib.sha256(f.read()).hexdigest(), info['sha256'], rel)
        libs, pyo = man['components']
        self.assertTrue(all(p['license'] for p in libs['packages']), libs['packages'])
        self.assertTrue(all(re.match(r'^\d+\.\d+\.\d+$', p['version']) for p in libs['packages']))
        self.assertEqual((pyo['version'], pyo['license'], pyo['source_sha256']), ('314.0.8', 'MPL-2.0', PYODIDE_CORE_SHA256))
        names = {p['name'] for p in pyo['packages']}
        self.assertEqual(names, {'pyyaml', 'jsonschema', 'attrs', 'referencing', 'jsonschema-specifications', 'rpds-py', 'six',
                                 'typing-extensions', 'pyrsistent'})
        for p in pyo['packages']:
            self.assertEqual(p['sha256_in_lock'], man['files'][p['file']]['sha256'], p['name'])  # wheel = pyodide-lock.json
            self.assertTrue(p['license'], p['name'])
        chk = man['vulnerability_check']
        self.assertRegex(chk['date'], r'^\d{4}-\d{2}-\d{2}$')
        self.assertIn('no known vulnerability', chk['result'])
        # every wheel the lock file needs for pyyaml and jsonschema is vendored (no request for a missing file)
        with open(os.path.join(VIEWER, 'vendor', 'pyodide', 'pyodide-lock.json'), encoding='utf-8') as f:
            lock = json.load(f)['packages']
        norm = lambda n: re.sub(r'[-_.]+', '-', n).lower()  # noqa: E731
        by = {norm(k): k for k in lock}
        need, todo = set(), ['pyyaml', 'jsonschema']
        while todo:
            n = by[norm(todo.pop())]
            if n not in need:
                need.add(n)
                todo += lock[n]['depends']
        self.assertEqual({lock[n]['file_name'] for n in need}, {f.split('/')[-1] for f in files if f.endswith('.whl')})
        # licenses are published next to the files
        self.assertIn('Mozilla Public License Version 2.0', self.read('vendor/pyodide/LICENSE'))
        lic = self.read('vendor/editor-libs.LICENSES.txt')
        for p in libs['packages']:
            self.assertIn(f"==== {p['name']}@{p['version']} ({p['license']}) ====", lic)

    def test_vendor_sources_are_pinned(self):
        with open(os.path.join(ROOT, 'tools', 'claims_editor_vendor', 'package.json'), encoding='utf-8') as f:
            pkg = json.load(f)
        for k, v in list(pkg['dependencies'].items()) + list(pkg['devDependencies'].items()):
            self.assertRegex(v, r'^\d+\.\d+\.\d+$', k)  # exact versions; the lock file pins the rest with integrity hashes

    def test_readmes_link_to_the_editor(self):
        url = 'https://takenori-kusaka.github.io/jwt-claims-guide/claims/'
        for rel in ('README.md', 'templates/README.md'):
            with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
                self.assertIn(url, f.read(), rel)


if __name__ == '__main__':
    unittest.main()
