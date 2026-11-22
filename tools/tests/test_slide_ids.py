# -*- coding: utf-8 -*-
"""Tests for the stable slide IDs (issue #15).

  python -m unittest discover -s tools/tests -v

The build tests copy deck/*.js to a temporary directory and run `node build.js --ids-only` there,
so the real deck is never modified. They are skipped when node or deck/node_modules is missing
(cd deck && npm install).
"""
import copy, json, os, re, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import check_slide_refs as C  # noqa: E402
from check_slide_refs import _read  # noqa: E402


def _write(path, text):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def _writeb(path, data):
    with open(path, 'wb') as f:
        f.write(data)

DECK = os.path.join(ROOT, 'deck')
IDS = json.loads(_read(os.path.join(DECK, 'slide_ids.json')))
REG = json.loads(_read(os.path.join(DECK, 'slide_ids_registry.json')))
KNOWN = {x['id'] for x in IDS}
HAVE_NODE = shutil.which('node') is not None and os.path.isdir(os.path.join(DECK, 'node_modules'))
# the block of slide 47 (p04-carry-or-query) in deck/p04.js, up to the closing brace of its block
BLOCK_RE = re.compile(r"\n  \{\n    const s = L\.content\('[^']*', \{ id: 'p04-carry-or-query',.*?\n  \}\n", re.S)


def errs(text):
    return C.scan_text(text, KNOWN, 'f')[1]


class ReferenceGrammar(unittest.TestCase):
    def test_valid_forms(self):
        for t in ['slide:p04-carry-or-query', 'see slide:p04-carry-or-query.', '(slide:p12-summary)',
                  'slide:p06-narrow-downstream.R1', 'slide:p06-narrow-downstream.R12.', '[slide:p00-title, slide:p12-summary]',
                  'slide:p04-carry-or-queryを参照', 'placeholder slide:<id>', 'Slide: overview of the part',
                  'https://takenori-kusaka.github.io/jwt-claims-guide/#p04-carry-or-query',
                  'https://takenori-kusaka.github.io/jwt-claims-guide/#p04-carry-or-query.',
                  'https://takenori-kusaka.github.io/jwt-claims-guide/#…', 'https://takenori-kusaka.github.io/jwt-claims-guide/']:
            self.assertEqual(errs(t), [], t)

    def test_unknown_and_malformed(self):
        cases = {
            'slide:p04-no-such-slide': 'unknown slide id',
            'slide:47': 'malformed',
            'slide:P04-carry-or-query': 'malformed',
            'slide:p04-carry-or-query_x': 'malformed',
            'slide:p04-carry-or-query-': 'malformed',
            'slide:p06-narrow-downstream.R1a': 'requirement suffix',
            'Slide:p04-carry-or-query': 'looks like a slide reference',
            'slide: p04-carry-or-query': 'looks like a slide reference',
            'SLIDE :47': 'looks like a slide reference',
            'https://takenori-kusaka.github.io/jwt-claims-guide/#s47': 'slide number',
            'https://takenori-kusaka.github.io/jwt-claims-guide/#p99-nope': 'unknown slide id',
        }
        for t, want in cases.items():
            e = errs(t)
            self.assertEqual(len(e), 1, (t, e))
            self.assertIn(want, e[0], t)

    def test_files(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, 'a.md'), 'slide:p04-carry-or-query\n')
            _write(os.path.join(d, 'b.adoc'), 'slide:p99-nope\n')
            _writeb(os.path.join(d, 'c.md'), 'slide:p99-nope 日本語'.encode('cp932'))
            files, n, e = C.check_refs([d], KNOWN, C.TEXT_EXT)
            self.assertEqual(files, 3)
            self.assertTrue(any('not UTF-8' in x for x in e), e)
            self.assertTrue(any('b.adoc:1: unknown slide id' in x for x in e), e)
            self.assertTrue(any('no such file' in x for x in C.check_refs([os.path.join(d, 'nope')], KNOWN, C.TEXT_EXT)[2]))


class Registry(unittest.TestCase):
    def ids(self, **retitle):
        ids = copy.deepcopy(IDS)
        for x in ids:
            x['title'] = retitle.get(x['id'], x['title'])
        return ids

    def test_current_deck_is_consistent(self):
        self.assertEqual(C.check_registry(IDS, REG), [])
        self.assertEqual(C.main(['--root', ROOT]), 0)

    def test_rename_is_detected(self):
        ids = self.ids()
        ids[46]['id'] = 'p04-carry-or-ask'
        e = C.check_registry(ids, REG)
        self.assertTrue(any('p04-carry-or-ask is not in' in x for x in e), e)
        self.assertTrue(any('id p04-carry-or-query' in x and 'on no slide' in x for x in e), e)

    def test_repointing_is_detected(self):
        ids = self.ids()
        ids[46]['id'], ids[47]['id'] = 'p04-claim-names', 'p04-carry-or-query'  # swap the ids of slides 47 and 48
        e = C.check_registry(ids, REG)
        self.assertTrue(any('slide 47' in x and 'p04-claim-names' in x for x in e), e)
        self.assertTrue(any('slide 48' in x and 'p04-carry-or-query' in x for x in e), e)

    def test_repointing_between_similar_titles_is_detected(self):
        ids = self.ids()
        a = next(i for i, x in enumerate(ids) if x['id'] == 'p11-pre-add-questions-1')
        ids[a]['title'] = ids[a + 1]['title']  # 1/2 now carries the 2/2 slide
        e = C.check_registry(ids, REG)
        self.assertTrue(any('better' in x for x in e), e)

    def test_title_tolerance_and_retitled(self):
        old = REG['p04-carry-or-query']['title']
        self.assertEqual(C.check_registry(self.ids(**{'p04-carry-or-query': old.replace('4 つ', '5 つ')}), REG), [])
        new = 'クレームの載せ方を決める手順'
        self.assertTrue(C.check_registry(self.ids(**{'p04-carry-or-query': new}), REG))
        reg = copy.deepcopy(REG)
        reg['p04-carry-or-query']['retitled'] = [{'date': '2026-12-01', 'title': new}]
        self.assertEqual(C.check_registry(self.ids(**{'p04-carry-or-query': new}), reg), [])

    def test_retired(self):
        reg = copy.deepcopy(REG)
        reg['p04-carry-or-query']['retired'] = '2026-12-01'
        e = C.check_registry(IDS, reg)
        self.assertTrue(any('retired' in x and 'cannot be reused' in x for x in e), e)
        ids = [x for x in IDS if x['id'] != 'p04-carry-or-query']
        self.assertEqual(C.check_registry(ids, reg), [])  # a retired id may be absent

    def test_append_only(self):
        reg = copy.deepcopy(REG)
        del reg['p00-title']
        reg['p04-carry-or-query']['title'] = 'x'
        e = C.check_append_only(REG, reg)
        self.assertTrue(any('p00-title was removed' in x for x in e), e)
        self.assertTrue(any('p04-carry-or-query.title was changed' in x for x in e), e)
        reg = copy.deepcopy(REG)
        reg['p04-carry-or-query']['retitled'] = [{'date': '2026-12-01', 'title': 'y'}]
        reg['p04-carry-or-query']['retired'] = '2026-12-02'
        reg['p99-new'] = {'issued': '2026-12-01', 'title': 'z'}
        self.assertEqual(C.check_append_only(REG, reg), [])
        self.assertEqual(C.main(['--root', ROOT, '--base', 'no-such-revision-xyz']), 1)


class Freshness(unittest.TestCase):
    def test_stale_sidecar_and_missing_id(self):
        with tempfile.TemporaryDirectory() as d:
            shutil.copytree(DECK, os.path.join(d, 'deck'), ignore=shutil.ignore_patterns('node_modules', '*.pptx'))
            self.assertEqual(C.main(['--root', d]), 0)
            self.assertEqual(C.main(['--root', d, '--expect', '153']), 1)
            p = os.path.join(d, 'deck', 'p04.js')
            s = _read(p)
            _write(p, s.replace("id: 'p04-carry-or-query'", "id: 'p04-carry-or-ask'"))
            self.assertEqual(C.main(['--root', d]), 1)  # source changed, sidecar not rebuilt
            _write(p, s.replace("{ id: 'p04-carry-or-query',", "{"))
            self.assertEqual(C.main(['--root', d]), 1)  # a slide call without an id


@unittest.skipUnless(HAVE_NODE, 'node or deck/node_modules not available')
class Build(unittest.TestCase):
    """Run the real deck build on a scratch copy of deck/."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.deck = os.path.join(self.tmp.name, 'deck')
        shutil.copytree(DECK, self.deck, ignore=shutil.ignore_patterns('node_modules', '*.pptx', 'qa'))

    def tearDown(self):
        self.tmp.cleanup()

    def edit(self, part, f):
        p = os.path.join(self.deck, part + '.js')
        s = _read(p).replace('\r\n', '\n')
        _write(p, f(s))

    def insert_dummy(self, part, opts, after_id=None):
        anchor = "\n  {\n    const s = L.content("
        def f(s):
            i = s.index(anchor) if after_id is None else s.index(anchor, s.index(f"id: '{after_id}'"))
            return s[:i] + f"\n  L.content('ダミーのスライド（挿入テスト）', {opts});\n" + s[i:]
        self.edit(part, f)

    def build(self, *extra):
        env = dict(os.environ, NODE_PATH=os.path.join(DECK, 'node_modules'), SLIDE_ID_DATE='2026-12-01')
        r = subprocess.run(['node', 'build.js', '--ids-only', *extra], cwd=self.deck, env=env,
                           capture_output=True, text=True, encoding='utf-8')
        ids = json.loads(_read(os.path.join(self.deck, 'slide_ids.json')))
        return r, ids

    def check(self):
        return C.main(['--root', self.tmp.name])

    def test_insert_keeps_existing_ids(self):
        self.insert_dummy('p04', "{ id: 'p04-dummy-inserted', lead: 'dummy' }", after_id='p04-carry-or-query')
        r, _ = self.build()
        self.assertEqual(r.returncode, 1)
        self.assertIn('p04-dummy-inserted is not in slide_ids_registry.json', r.stderr)
        r, ids = self.build('--register')
        self.assertEqual(r.returncode, 0, r.stderr)
        new = {x['id']: x for x in ids}
        self.assertEqual(len(ids), len(IDS) + 1)
        self.assertEqual(set(new) - KNOWN, {'p04-dummy-inserted'})
        self.assertEqual([x['id'] for x in ids if x['id'] in KNOWN], [x['id'] for x in IDS])
        for x in IDS:
            self.assertEqual(new[x['id']]['title'], x['title'])
        self.assertEqual([x['id'] for x in ids[45:49]], ['p04-token-is-snapshot', 'p04-carry-or-query', 'p04-dummy-inserted', 'p04-claim-names'])
        reg = json.loads(_read(os.path.join(self.deck, 'slide_ids_registry.json')))
        self.assertEqual(reg['p04-dummy-inserted'], {'issued': '2026-12-01', 'title': 'ダミーのスライド（挿入テスト）'})
        self.assertEqual(self.check(), 0)
        print(f'\n  inserted p04-dummy-inserted at 48: {len(IDS)} -> {len(ids)} slides, '
              f'{sum(1 for x in IDS if new[x["id"]]["n"] != x["n"])} numbers shifted, 0 existing ids changed', end=' ')

    def test_rejections(self):
        for opts, want in [("{ lead: 'x' }", 'slide without id'),
                           ("{ id: 'p04-carry-or-query' }", 'duplicate slide id'),
                           ("{ id: 'p05-dummy' }", 'must use the prefix of the part'),
                           ("{ id: 'p04-Bad_id' }", 'bad slide id')]:
            self.tearDown(); self.setUp()  # fresh copy of the deck for each case
            self.insert_dummy('p04', opts)
            r, _ = self.build('--register')
            self.assertEqual(r.returncode, 1, opts)
            self.assertIn(want, r.stderr, opts)

    def test_rename_fails(self):
        self.edit('p04', lambda s: s.replace("id: 'p04-carry-or-query'", "id: 'p04-carry-or-ask'"))
        r, _ = self.build('--register')  # even when registering the new id, the old one vanished
        self.assertEqual(r.returncode, 1)
        self.assertIn('p04-carry-or-query', r.stderr)
        self.assertIn('no slide has it', r.stderr)

    def test_retired_id_cannot_be_reused(self):
        p = os.path.join(self.deck, 'slide_ids_registry.json')
        reg = json.loads(_read(p))
        reg['p04-old-slide'] = {'issued': '2026-11-22', 'title': '古いスライド', 'retired': '2026-11-30', 'reason': 'test'}
        _write(p, json.dumps(reg, ensure_ascii=False))
        r, _ = self.build()
        self.assertEqual(r.returncode, 0, r.stderr)  # a retired id may be absent
        self.insert_dummy('p04', "{ id: 'p04-old-slide' }")
        r, _ = self.build('--register')
        self.assertEqual(r.returncode, 1)
        self.assertIn('retired', r.stderr)

    def test_move_to_another_part_keeps_id(self):
        """An issued id keeps its prefix when the slide moves to another part (README: prefix fixed at issuance)."""
        src = _read(os.path.join(self.deck, 'p04.js')).replace('\r\n', '\n')
        block = BLOCK_RE.search(src).group(0)
        self.edit('p04', lambda s: s.replace(block, '\n'))
        self.edit('p05', lambda s: s.replace("\n  {\n    const s = L.content(", block + "  {\n    const s = L.content(", 1))
        r, ids = self.build()
        self.assertEqual(r.returncode, 0, r.stderr)
        moved = next(x for x in ids if x['id'] == 'p04-carry-or-query')
        self.assertEqual(moved['part'], 'p05')
        self.assertEqual(self.check(), 0)


if __name__ == '__main__':
    unittest.main()
