# -*- coding: utf-8 -*-
"""Tests of tools/row_hash.py (RFC 8785 JCS and the row anchors / hashes of #49, used by the review mode of #50).

  python -m pytest -q tools/tests/test_row_hash.py

The browser side (ClaimsEditor.rowHash, docs/claims/editor.js) is compared with this module in
tools/tests/test_claims_editor_ui.py::test_row_hashes_equal_tools_row_hash (Playwright).
"""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import row_hash  # noqa: E402


class Numbers(unittest.TestCase):
    def test_ecmascript_number_text(self):
        cases = [(0, '0'), (-0.0, '0'), (1.0, '1'), (1, '1'), (-1.5, '-1.5'), (0.1, '0.1'), (123.456, '123.456'),
                 (1e20, '100000000000000000000'), (1e21, '1e+21'), (1e23, '1e+23'), (1e-6, '0.000001'), (1e-7, '1e-7'),
                 (1.5e-7, '1.5e-7'), (0.002, '0.002'), (5e-324, '5e-324'), (1.7976931348623157e308, '1.7976931348623157e+308'),
                 (333333333.33333329, '333333333.3333333'), (9007199254740993, '9007199254740992'), (4.35, '4.35'),
                 (1e300, '1e+300'), (123456789012345678901234, '1.2345678901234569e+23')]  # as node prints it
        for v, want in cases:
            self.assertEqual(row_hash.es_number(v), want, v)

    def test_not_finite_is_refused(self):
        for v in (float('inf'), float('nan')):
            with self.assertRaises(ValueError):
                row_hash.jcs({'a': v})

    def test_not_finite_key_is_its_text(self):
        # .inf / .nan as a mapping key: the editor's yaml package gives String(Infinity); row_hash does the same (#50)
        self.assertEqual(row_hash.jcs({float('inf'): 1, float('-inf'): 2, float('nan'): 3}), '{"-Infinity":2,"Infinity":1,"NaN":3}')


class Jcs(unittest.TestCase):
    def test_rfc8785_key_order(self):
        # RFC 8785 3.2.3: keys sorted by UTF-16 code units (the emoji's high surrogate sorts before U+FB33)
        v = {'€': 'Euro Sign', '\r': 'Carriage Return', 'דּ': 'Hebrew Letter Dalet With Dagesh', '1': 'One',
             '\U0001F600': 'Emoji: Grinning Face', '\u0080': 'Control', 'ö': 'Latin Small Letter O With Diaeresis'}
        self.assertEqual(row_hash.jcs(v), '{"\\r":"Carriage Return","1":"One","\u0080":"Control","ö":"Latin Small Letter O With Diaeresis",'
                                          '"€":"Euro Sign","\U0001F600":"Emoji: Grinning Face","דּ":"Hebrew Letter Dalet With Dagesh"}')

    def test_values(self):
        self.assertEqual(row_hash.jcs({'b': [1.0, None, True, False, 'x"\\\n\u0001'], 'a': {}}),
                         '{"a":{},"b":[1,null,true,false,"x\\"\\\\\\n\\u0001"]}')
        # a key that is not a string is written as the editor gets it from the yaml package
        self.assertEqual(row_hash.jcs({1: 'a', 1.5: 'b', None: 'c'}), '{"":"c","1":"a","1.5":"b"}')

    def test_sha256_of_utf8(self):
        self.assertEqual(row_hash.sha256_hex('abc'), 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')


class Rows(unittest.TestCase):
    def test_samples_have_unique_anchors(self):
        for s in ('scenario-a', 'scenario-b'):
            res = row_hash.row_hashes(os.path.join(ROOT, 'templates', 'examples', s))
            self.assertEqual(res['duplicates'], [], s)
            self.assertIn('claims:C-iss', res['hashes'])
            self.assertIn('issuance_profile:client_type', res['hashes'])

    def test_layout_does_not_change_the_hash_and_a_value_does(self):
        with tempfile.TemporaryDirectory() as d:
            def h(text):
                with open(os.path.join(d, 'claims.yaml'), 'w', encoding='utf-8') as f:
                    f.write(text)
                return row_hash.row_hashes(d)
            a = h('claims:\n  - id: C-a\n    name: a\n    max_bytes: 10\n')
            b = h('# comment\nclaims:\n  - {max_bytes: 10.0, "name": a, id: C-a}  # same row\n')
            c = h('claims:\n  - id: C-a\n    name: a\n    max_bytes: 11\n')
            self.assertEqual(a, b)
            self.assertNotEqual(a['hashes']['claims:C-a'], c['hashes']['claims:C-a'])
            dup = h('claims:\n  - id: C-a\n    name: a\n  - id: C-a\n    name: b\n  - id: C-b\n')
            self.assertEqual(dup['duplicates'], ['claims:C-a'])
            self.assertEqual(list(dup['hashes']), ['claims:C-b'])

    def test_lone_surrogate_has_no_hash(self):
        with self.assertRaises(ValueError):
            row_hash.jcs({'a': '\ud800'})
        self.assertEqual(row_hash.jcs({'a': '\ud83d\ude00'}), row_hash.jcs({'a': '\U0001F600'}))  # a pair is one character
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, 'claims.yaml'), 'w', encoding='utf-8') as f:
                f.write('claims:\n  - id: C-a\n    name: "\\ud800"\n  - id: C-b\n')
            res = row_hash.row_hashes(d)
            self.assertEqual(list(res['hashes']), ['claims:C-b'])
            self.assertIn('lone surrogate', res['errors']['claims:C-a'])
            import subprocess
            out = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'row_hash.py'), d], capture_output=True)
            self.assertEqual(out.returncode, 1)

    def test_cli_json(self):
        import subprocess
        out = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'row_hash.py'), os.path.join(ROOT, 'templates', 'examples', 'scenario-a'),
                              '--format', 'json'], capture_output=True)
        self.assertEqual(out.returncode, 0)
        self.assertEqual(json.loads(out.stdout.decode('utf-8')), row_hash.row_hashes(os.path.join(ROOT, 'templates', 'examples', 'scenario-a')))


if __name__ == '__main__':
    unittest.main()
