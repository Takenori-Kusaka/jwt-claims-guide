# -*- coding: utf-8 -*-
"""tools/new_design.py (#4): an empty design starts from blank values, not from a worked example, and lint fails on it."""
import os
import sys

import yaml

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import new_design  # noqa: E402
from claim_lint import core  # noqa: E402


def test_new_design_is_blank_and_fails_lint(tmp_path):
    d = tmp_path / 'my-service'
    assert new_design.main([str(d)]) == 0
    tts = yaml.safe_load((d / 'token_types.yaml').read_text(encoding='utf-8'))['token_types']
    kinds = yaml.safe_load(open(os.path.join(ROOT, 'templates', 'catalog', 'token_kinds.yaml'), encoding='utf-8'))['kinds']
    assert len(tts) == len(kinds) and all(t['decision'] == '却下' and t['rationale'] == '' for t in tts)
    ans = yaml.safe_load((d / 'catalog_answers.yaml').read_text(encoding='utf-8'))['answers']
    assert ans and all(a['answer'] is None for a in ans)
    assert yaml.safe_load((d / 'claims.yaml').read_text(encoding='utf-8'))['claims'] == []
    assert yaml.safe_load((d / 'claims.yaml').read_text(encoding='utf-8'))['data_category_vocabulary']['name'] == 'fideslang'
    # no sample rationale of a worked example reaches the new design
    example = open(os.path.join(ROOT, 'templates', 'examples', 'scenario-a', 'claims.yaml'), encoding='utf-8').read()
    assert 'saas-api' in example and 'saas-api' not in (d / 'claims.yaml').read_text(encoding='utf-8')
    res = core.run(str(d), profile='lite')
    assert res['counts']['error'] > 0
    assert new_design.main([str(d)]) == 1  # does not overwrite without --force
