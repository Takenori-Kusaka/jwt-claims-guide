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


def test_packet_refuses_a_directory_inside_the_repository():
    with pytest.raises(SystemExit, match='inside the repository'):
        cc.packet('seeded-a', os.path.join(cc.ROOT, 'designs', 'packet-x'), '12')
    assert not os.path.exists(os.path.join(cc.ROOT, 'designs', 'packet-x'))


def test_packet_refuses_a_non_empty_directory(tmp_path):
    (tmp_path / 'left.txt').write_text('x', encoding='utf-8')
    with pytest.raises(SystemExit, match='not empty'):
        cc.packet('seeded-a', str(tmp_path), '12')


def _hint_errors(**fields):
    e = {'id': 'X01', 'design': 'seeded-c', 'signpost': 'P1', 'span': '2+', 'difficulty': 'medium', 'form': 'absent',
         'channel': 'short_list', 'channel_priority': 1, 'channel_question': ['q-revocation-delivery'], 'locations': [],
         'hint_derived': [], 'copies': 0, 'masked_by': [], 'salience': 'low'}
    e.update(fields)
    errors = []
    cc.check_salience({'errors': [e]}, {}, os.path.join('no', 'such', 'protocol.md'), errors)
    return [x for x in errors if 'hint' in x]


def test_c8_requires_hint_derived_when_the_channel_question_got_a_new_hint():
    """set2/protocol.md 3.2 (S10): a channel question whose hint #80 changed needs hint_derived, and hint_derived a hint_note."""
    assert any('hint_derived is required' in x for x in _hint_errors())
    assert any('hint_derived is required' in x for x in _hint_errors(channel='lint', channel_question=[]))
    assert any('needs a hint_note' in x for x in _hint_errors(hint_derived=['A17']))
    assert _hint_errors(hint_derived=['A17'], hint_note='初回とは場所を変えた') == []
    assert _hint_errors(channel_question=['q-object-level-authz']) == []
    assert any('is not one of' in x for x in _hint_errors(hint_derived=['Z99'], hint_note='x'))


def _pinned_root(tmp_path, monkeypatch):
    root = tmp_path / 'repo'
    (root / 'rev' / 'contrasts').mkdir(parents=True)
    (root / 'rev' / 'a.md').write_text('a\n', encoding='utf-8')
    (root / 'rev' / 'contrasts' / 'one.md').write_text('one\n', encoding='utf-8')
    monkeypatch.setattr(cc, 'ROOT', str(root))
    monkeypatch.setattr(cc, 'MATERIALS', ('rev/a.md',))
    monkeypatch.setattr(cc, 'MATERIAL_DIRS', ('rev/contrasts',))
    pins = tmp_path / 'commitments.sha256'
    pins.write_text(''.join(f'{cc.sha256_lf(str(root / r))} *@{r}\n' for r in ('rev/a.md', 'rev/contrasts/one.md')),
                    encoding='utf-8')
    return root, str(pins)


def test_pinned_materials_refuse_changed_added_and_removed_files(tmp_path, monkeypatch):
    """set2/protocol.md S12: the pinned list is the whole packet material, not only the hashes of known files."""
    root, pins = _pinned_root(tmp_path, monkeypatch)
    assert cc.pinned_materials('seeded-c', pins) == []
    (root / 'rev' / 'a.md').write_text('a changed\n', encoding='utf-8')
    assert any('rev/a.md differs' in p for p in cc.pinned_materials('seeded-c', pins))
    (root / 'rev' / 'a.md').write_text('a\n', encoding='utf-8')
    (root / 'rev' / 'contrasts' / 'zz-new.md').write_text('new\n', encoding='utf-8')
    assert any('zz-new.md is a packet material that is not pinned' in p for p in cc.pinned_materials('seeded-c', pins))
    (root / 'rev' / 'contrasts' / 'zz-new.md').unlink()
    (root / 'rev' / 'contrasts' / 'one.md').unlink()
    assert any('one.md is pinned but missing' in p for p in cc.pinned_materials('seeded-c', pins))


def test_packet_refuses_changed_materials_before_writing_anything(tmp_path, monkeypatch):
    monkeypatch.setattr(cc, 'pinned_materials', lambda design, cpath=None: ['rev/a.md differs from the pinned sha256'])
    out = tmp_path / 'packet'
    with pytest.raises(SystemExit, match='differs from the pinned sha256'):
        cc.packet('seeded-c', str(out), '12')
    assert not out.exists()


def test_packet_without_leaves_out_only_an_extra_file_of_the_set(tmp_path):
    """#88's kind_tell ablation: --without drops one of the set's own packet files; the pinned materials always go in."""
    assert [n for _, n in cc.extra_materials('seeded-c')] == ['kind_tell.md']
    assert cc.extra_materials('seeded-c', ('kind_tell.md',)) == []
    with pytest.raises(SystemExit, match='short_list.md is not an extra file'):
        cc.packet('seeded-c', str(tmp_path / 'packet'), '12', ('short_list.md',))
    with pytest.raises(SystemExit, match='kind_tell.md is not an extra file of set1'):
        cc.packet('seeded-a', str(tmp_path / 'packet'), '12', ('kind_tell.md',))
    assert not (tmp_path / 'packet').exists()


def test_packet_without_still_refuses_changed_pinned_materials(tmp_path, monkeypatch):
    """--without leaves S12 in force: changed pinned materials stop the packet before anything is written."""
    monkeypatch.setattr(cc, 'pinned_materials', lambda design, cpath=None: ['rev/a.md differs from the pinned sha256'])
    out = tmp_path / 'packet'
    with pytest.raises(SystemExit, match='differs from the pinned sha256'):
        cc.packet('seeded-c', str(out), '12', ('kind_tell.md',))
    assert not out.exists()


def test_packet_without_builds_a_packet_that_passes_p1_to_p3(tmp_path, monkeypatch):
    # the materials changed after set 2 was fixed (#88), so the real pin refuses (the next test); this one checks --without
    monkeypatch.setattr(cc, 'pinned_materials', lambda design, cpath=None: [])
    out = tmp_path / 'packet'
    cc.packet('seeded-c', str(out), '12', ('kind_tell.md',))  # raises SystemExit on any P1-P3 error
    assert not (out / 'kind_tell.md').exists()
    assert (out / 'short_list.md').exists() and (out / 'designs' / 'target' / 'design.md').exists()
    assert cc.packet_errors(str(out), 'seeded-c', ('kind_tell.md',)) == []


def test_set2_packets_are_refused_after_the_materials_changed(tmp_path):
    """#88 changed templates/review after set 2 was fixed: a set-2 packet built now would not be the measured packet, so
    the S12 pin refuses it before writing (build it from the commit recorded in set2/README.md instead)."""
    out = tmp_path / 'packet'
    with pytest.raises(SystemExit, match='differs from the pinned sha256'):
        cc.packet('seeded-c', str(out), '12')
    assert not out.exists()


def test_a_released_set_skips_its_material_pins_in_check_only(tmp_path, monkeypatch):
    """#88: set 2 is measured and released; check no longer compares its `@` pins (C6) and builds its packets without
    the pin (C7), while packet still refuses (the test above)."""
    assert cc.SETS['set2']['released']['commit'] == '5be7cea'
    errors = []
    cc.check_commitments('set2', errors)
    assert errors == []
    monkeypatch.setitem(cc.SETS, 'set2', {k: v for k, v in cc.SETS['set2'].items() if k != 'released'})
    errors = []
    cc.check_commitments('set2', errors)
    assert errors and all(e.startswith('C6 set2 @templates/review/') for e in errors)

