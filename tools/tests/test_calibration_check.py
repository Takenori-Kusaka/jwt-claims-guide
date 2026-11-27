# -*- coding: utf-8 -*-
"""tools/calibration_check.py (#12): the markers of the calibration set come off byte for byte."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import calibration_check as cc  # noqa: E402

MD = '<!-- template_version: 0.1.0 -->\n# 設計書：架空\n\n本文\n'
YML = '# template_version: 0.1.0\n# yaml-language-server: $schema=./x.json\nclaims: []\n'
JSN = '{\n  "$id": "x",\n  "type": "object"\n}\n'


@pytest.mark.parametrize('name,text', [('design.md', MD), ('claims.yaml', YML), ('AT.issuer.schema.json', JSN)])
@pytest.mark.parametrize('marker', [cc.M_SEEDED, cc.M_CONTROL])
def test_marker_round_trip(tmp_path, name, text, marker):
    p = tmp_path / name
    p.write_bytes(text.encode('utf-8'))
    cc.add_marker(str(p), marker)
    marked = p.read_text(encoding='utf-8')
    assert marker in marked and marked != text
    ext = os.path.splitext(name)[1]
    back, had = cc.strip_marker(marked, ext, marker)
    assert had and back == text


def test_markdown_marker_follows_first_heading(tmp_path):
    p = tmp_path / 'design.md'
    p.write_text(MD, encoding='utf-8')
    cc.add_marker(str(p), cc.M_SEEDED)
    lines = p.read_text(encoding='utf-8').split('\n')
    assert lines[1].startswith('# ') and lines[2] == '' and lines[3] == f'> **{cc.M_SEEDED}**'


def test_wrong_marker_is_not_stripped():
    marked = MD.replace('# 設計書：架空\n', f'# 設計書：架空\n\n> **{cc.M_CONTROL}**\n')
    back, had = cc.strip_marker(marked, '.md', cc.M_SEEDED)
    assert not had and back == marked


def test_yaml_marker_must_be_line_two():
    text = YML + f'# {cc.M_SEEDED}\n'
    back, had = cc.strip_marker(text, '.yaml', cc.M_SEEDED)
    assert not had


def test_mark_seeded_renames_with_broken(tmp_path):
    d = tmp_path / 'seeded-x'
    (d / 'schemas').mkdir(parents=True)
    (d / 'design.md').write_text(MD, encoding='utf-8')
    (d / 'claims.yaml').write_text(YML, encoding='utf-8')
    (d / 'schemas' / 'AT.issuer.schema.json').write_text(JSN, encoding='utf-8')
    assert cc.main(['mark', str(d), '--seeded']) == 0
    names = sorted(os.path.relpath(p, d).replace('\\', '/') for p in cc.files_of(str(d)))
    assert names == ['claims.broken.yaml', 'design.broken.md', 'schemas/AT.issuer.broken.schema.json']
