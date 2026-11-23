# -*- coding: utf-8 -*-
"""Tests of tools/variant_compare.py (#4): the overlay merge rules M1..M4, and the design-doc region check (drift fails)."""
import os
import sys

import pytest
import yaml

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import variant_compare as vc  # noqa: E402

EXAMPLE_A = os.path.join(ROOT, 'templates', 'examples', 'scenario-a')


# ------------------------------------------------------------------ merge rules
def test_m1_mapping_merged_key_by_key_and_null_removes():
    base = {'a': {'x': 1, 'y': 2}, 'b': 1, 'c': 3}
    out = vc.merge(base, {'a': {'y': 20}, 'b': None, 'd': 4})
    assert out == {'a': {'x': 1, 'y': 20}, 'c': 3, 'd': 4}
    assert base == {'a': {'x': 1, 'y': 2}, 'b': 1, 'c': 3}  # the example is not modified


def test_m2_rows_merged_by_id_replace_delete_unset_append():
    base = {'rows': [{'id': 'A', 'p': 1, 'q': 2, 'r': {'s': 1}}, {'id': 'B', 'p': 1}, {'id': 'C', 'p': 1}]}
    over = {'rows': [{'id': 'A', 'p': 10, 'r': {'t': 2}, '_unset': ['q']},
                     {'id': 'B', '_replace': True, 'z': 9},
                     {'id': 'C', '_delete': True},
                     {'id': 'D', 'p': 4}]}
    out = vc.merge(base, over)
    assert out['rows'] == [{'id': 'A', 'p': 10, 'r': {'t': 2}}, {'id': 'B', 'z': 9}, {'id': 'D', 'p': 4}]
    assert not any(k.startswith('_') for r in out['rows'] for k in r)


def test_m2_event_rows_of_catalogue_answers():
    base = {'answers': [{'event': 'I01', 'answer': '該当'}, {'event': 'I02', 'answer': '該当'}]}
    out = vc.merge(base, {'answers': [{'event': 'I02', 'answer': '対象外', 'assumption': 'x'}]})
    assert out['answers'][1] == {'event': 'I02', 'answer': '対象外', 'assumption': 'x'}


def test_m3_plain_list_replaced():
    assert vc.merge({'l': [1, 2, 3]}, {'l': [4]}) == {'l': [4]}


@pytest.mark.parametrize('over', [
    {'rows': [{'id': 'X', '_delete': True}]},
    {'rows': [{'id': 'A', '_unset': ['missing']}]},
    {'rows': [{'id': 'N', 'p': 1, '_unset': ['p']}]},
])
def test_m4_overlay_that_does_nothing_is_an_error(over):
    with pytest.raises(vc.OverlayError):
        vc.merge({'rows': [{'id': 'A', 'p': 1}]}, over)


# ------------------------------------------------------------------ end to end on scenario A (a copy; the example is not written)
def _overlay(tmp_path):
    ov = {'name': 'test-none', 'description': 'テスト用：RT のローテーションを外す',
          'files': {'token_types.yaml': {'token_types': [{'id': 'RT', 'rt_rotation': {'rotation': False, 'reuse_detection': 'no'}}]}}}
    p = tmp_path / 'ov.yaml'
    p.write_text(yaml.safe_dump(ov, allow_unicode=True), encoding='utf-8')
    return p


def test_variant_is_built_in_a_copy_and_compared(tmp_path):
    before = open(os.path.join(EXAMPLE_A, 'token_types.yaml'), encoding='utf-8').read()
    ov = vc.load_overlay(str(_overlay(tmp_path)))
    out = vc.build_variant(EXAMPLE_A, ov, str(tmp_path / 'scenario-a'))
    body = vc.compare(EXAMPLE_A, out, ov)
    assert '| RT | rt_rotation |' in body
    assert open(os.path.join(EXAMPLE_A, 'token_types.yaml'), encoding='utf-8').read() == before


def test_region_write_then_check_then_drift(tmp_path, capsys):
    ov = _overlay(tmp_path)
    doc = tmp_path / 'design.md'
    doc.write_text('# 題\n\n<!-- variant:test-none:begin -->\n古い\n<!-- variant:test-none:end -->\n\n手で書いた文\n', encoding='utf-8')
    assert vc.main([EXAMPLE_A, str(ov), '--write', str(doc)]) == 0
    assert vc.main([EXAMPLE_A, str(ov), '--check', str(doc)]) == 0
    text = doc.read_text(encoding='utf-8')
    assert '手で書いた文' in text and '古い' not in text
    doc.write_text(text.replace('rt_rotation', 'rt_rotatoin', 1), encoding='utf-8')
    assert vc.main([EXAMPLE_A, str(ov), '--check', str(doc)]) == 1


def test_missing_region_is_an_error(tmp_path):
    doc = tmp_path / 'design.md'
    doc.write_text('# 題\n', encoding='utf-8')
    assert vc.main([EXAMPLE_A, str(_overlay(tmp_path)), '--check', str(doc)]) == 2
