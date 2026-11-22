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
