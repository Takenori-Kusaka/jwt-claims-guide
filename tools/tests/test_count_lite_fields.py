# -*- coding: utf-8 -*-
"""The counts of research/template-design/gate1.md section 10 are reproducible (#16, PR #31)."""
import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
import count_lite_fields as clf  # noqa: E402


def test_scenario_a_counts_match_gate1():
    rows, (before, after), hand, hand_oos = clf.count(os.path.join(os.path.dirname(TOOLS), 'templates', 'examples', 'scenario-a'))
    assert (before, after) == (875, 700)
    assert hand == [2, 3, 6, 9, 12]
    assert hand_oos == ['I06', 'I08', 'I09', 'U05', 'U07', 'U08', 'U10']
    gate1 = open(os.path.join(os.path.dirname(TOOLS), 'research', 'template-design', 'gate1.md'), encoding='utf-8').read()
    assert '| **YAML の欄の計** | **875** | **700** |' in gate1


def test_out_of_scope_answers_that_can_occur_are_hand_written():
    # A03 (I09, U07), A15 (U05) and the lint finding U10 were in 対象外 rows: they must not be inherited
    assert not {'I06', 'I08', 'I09', 'U07', 'U05', 'U08', 'U10'} & set(clf.STRUCTURAL)


def test_current_counts_lite_below_full_and_skip_generated_columns(tmp_path):
    """--current (#4, templates/README.md 「記入の目安」): Lite does not count the generated columns, sections and hops."""
    ex = os.path.join(os.path.dirname(TOOLS), 'templates', 'examples', 'scenario-a')
    lite_rows, lite = clf.count_current(ex, 'lite')
    full_rows, full = clf.count_current(ex, 'full')
    assert 0 < lite < full
    lite_d, full_d = dict(lite_rows), dict(full_rows)
    assert lite_d['発行方式の選択（既定から外れた 0 項目）'] == 0 and full_d['発行方式の選択'] > 0
    assert lite_d['ホップ（0 行。交換・作り直しのホップだけ）'] == 0
    # an inherited 対象外 answer counts one field
    import shutil
    import yaml
    d = tmp_path / 'ex'
    shutil.copytree(ex, d)
    p = d / 'catalog_answers.yaml'
    doc = yaml.safe_load(p.read_text(encoding='utf-8'))
    a = next(x for x in doc['answers'] if x['event'] == 'I04')
    for k in ('assumption', 'breaks_when'):
        a.pop(k, None)
    a.update(inherit='idp-default', setting_checked='Direct access grants を確かめた')
    p.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding='utf-8')
    rows, _ = clf.count_current(str(d), 'lite')
    assert any('引き継ぎ 1 件' in n for n, _ in rows)
