# -*- coding: utf-8 -*-
"""tools/review_record.py (#50): review.yaml against its schema, stale approvals, merge, sampling, the report, and the
form check of review reports (tools/review_check.py check_report).

  python -m pytest -q tools/tests/test_review_record.py

The browser side (docs/claims/review.js) writes the same text and the same report: tools/tests/test_claims_review_ui.py.
"""
import copy
import json
import os
import shutil
import sys

import jsonschema
import pytest

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import review_check  # noqa: E402
import review_record as rr  # noqa: E402
import row_hash  # noqa: E402

B = os.path.join(ROOT, 'templates', 'examples', 'scenario-b')
EXAMPLE = os.path.join(B, 'review.yaml')
REPORT = os.path.join(B, 'review-report-2026-11-23.md')


def example():
    return rr.load(EXAMPLE)


def test_schema_is_valid_2020_12():
    with open(rr.SCHEMA, encoding='utf-8') as f:
        jsonschema.Draft202012Validator.check_schema(json.load(f))


def test_the_example_passes_and_is_current():
    errs, notes = rr.check(example(), B)
    assert errs == [] and notes == []
    assert rr.main(['check', EXAMPLE, '--design', B, '--fail-on-stale']) == 0


def test_the_example_is_a_real_review_of_all_questions_labelled_llm():
    rv = example()['reviews'][0]
    qs = rr._questions()
    assert set(rv['answers']) == {q['id'] for q in qs} and len(qs) == 168
    assert rv['reviewer']['kind'] == 'llm' and rv['self_declared'] is True
    assert '人による点検は未実施' in rv['context']['human_check']
    assert all(f['verdict'] == '保留' for f in rv['findings'])  # a person has not decided yet
    assert len(rv['rows']) > 30


def test_canonical_text_round_trips():
    text = open(EXAMPLE, encoding='utf-8').read()
    assert rr.dump(rr.load_text(text)) == text
    odd = {'format': 'claims-review/1', 'design': 'x', 'independent': False, 'reviews': [{
        'reviewer': {'name': 'yes', 'kind': 'human'}, 'self_declared': True, 'started': '2026-01-01', 'submitted': None,
        'answers': {'q-a': {'answer': 'no', 'memo': 'a "q" \\ \n\t\x7f ﻿: # x'}}, 'rows': {}, 'findings': []}]}
    assert rr.load_text(rr.dump(odd)) == odd
    assert rr.dump(rr.load_text(rr.dump(odd))) == rr.dump(odd)


def test_schema_and_vocabulary_errors():
    d = example()
    d['reviews'][0]['findings'][0]['severity'] = 'Critical'
    assert any('severity' in e for e in rr.check(d)[0])
    d = example()
    f = d['reviews'][0]['findings'][0]
    f['kind'] = '目的と仕組みの不一致'
    f.pop('confused_question', None)
    assert any('confused_question' in e for e in rr.check(d)[0])
    d = example()
    d['reviews'][0]['answers']['q-no-such-question'] = {'answer': 'yes'}
    assert any('q-no-such-question' in e for e in rr.check(d)[0])
    d = example()
    d['reviews'][0]['self_declared'] = False  # the name is always self-declared
    assert rr.check(d)[0]
    d = example()
    d['reviews'].append(copy.deepcopy(d['reviews'][0]))
    assert any('two reviews' in e for e in rr.check(d)[0])
    d = example()
    d['reviews'][0]['sampling']['picked'] = ['claims:C-upn', 'claims:C-rctx', 'claims:C-rfc-roles']
    assert any('draws' in e for e in rr.check(d, B)[0])
    d = example()
    d['reviews'][0]['escalations']['not_applicable'].append('no-such-criterion')
    assert any('no-such-criterion' in e for e in rr.check(d)[0])


def test_an_edited_row_makes_its_approval_stale(tmp_path):
    design = tmp_path / 'scenario-b'
    shutil.copytree(B, design)
    rv = example()['reviews'][0]
    a = next(a for a, r in rv['rows'].items() if r['decision'] == 'approve' and a.startswith('hops:'))
    hop = a.split(':', 1)[1]
    p = design / 'hops.yaml'
    text = p.read_text(encoding='utf-8')
    assert f'  - id: {hop}\n' in text
    p.write_text(text.replace(f'  - id: {hop}\n', f'  - id: {hop}\n    x_changed: 1\n', 1), encoding='utf-8')
    errs, notes = rr.check(example(), str(design))
    assert errs == []
    assert any(a in n and '再確認が要る' in n for n in notes) and len(notes) == 1
    assert rr.main(['check', EXAMPLE, '--design', str(design)]) == 0
    assert rr.main(['check', EXAMPLE, '--design', str(design), '--fail-on-stale']) == 1
    # a comment changes nothing
    p.write_text(text.replace(f'  - id: {hop}\n', f'  - id: {hop}  # a comment\n', 1), encoding='utf-8')
    assert rr.check(example(), str(design))[1] == []
    # a removed row: the record is reported, not dropped
    p.write_text(text.replace(f'  - id: {hop}\n', f'  - id: {hop}-renamed\n', 1), encoding='utf-8')
    notes = rr.check(example(), str(design))[1]
    assert any(a in n and '台帳に無い' in n for n in notes)


def test_merge_two_reviewers_and_refuse_a_conflict():
    a = example()
    b = copy.deepcopy(a)
    b['reviews'][0]['reviewer'] = {'name': '人のレビュアー', 'kind': 'human'}
    m = rr.merge([a, b])
    assert [r['reviewer']['name'] for r in m['reviews']] == [a['reviews'][0]['reviewer']['name'], '人のレビュアー']
    assert rr.check(m, B)[0] == []
    assert rr.merge([a, copy.deepcopy(a)]) == a  # the same records twice: one
    c = copy.deepcopy(a)
    c['reviews'][0]['answers']['dc-01'] = {'answer': 'yes'}
    with pytest.raises(ValueError):
        rr.merge([a, c])
    d = copy.deepcopy(b)
    d['design'] = 'templates/examples/scenario-a'
    with pytest.raises(ValueError):
        rr.merge([a, d])


def test_sampling_is_reproducible():
    docs = row_hash.load(B)
    one = rr.sample('20261123-b', 3, docs)
    assert one == rr.sample('20261123-b', 3, docs) == example()['reviews'][0]['sampling']['picked']
    assert rr.sample('20261123-b', 2, docs) == one[:2]
    rejected = {f'claims:{c["id"]}' for c in docs['claims']['claims'] if c.get('decision') == '却下'}
    assert set(one) <= rejected and len(set(one)) == 3


def test_the_committed_report_is_generated_and_follows_the_form():
    assert rr.main(['report', EXAMPLE, '--design', B, '--check', REPORT]) == 0
    with open(REPORT, encoding='utf-8') as f:
        text = f.read()
    assert review_check.check_report(ROOT, text) == []
    assert '人による点検は未実施' in text and '自己申告' in text


def _report():
    with open(REPORT, encoding='utf-8') as f:
        return f.read()


@pytest.mark.parametrize('old,new,rule', [
    ('# レビューレポート：', '# レポート：', 'RP1'),
    ('## 3. 対応の一覧', '## 3. 対応', 'RP2'),
    ('| 実施日 |', '| 日付 |', 'RP3'),
    ('| ID | 場所 | 内容 | 重大度 |', '| ID | 場所 | 中身 | 重大度 |', 'RP4'),
    ('| Major | 観点 |', '| Critical | 観点 |', 'RP5'),
    ('| Major | 観点 | 候補の漏れ | — |', '| Major | 観点 | 候補の漏れ | `q-peer` |', 'RP5'),
    ('| 未着手 |', '| 終わった |', 'RP6'),
    ('当てはまらなかった基準：', '当てはまらない：', 'RP7'),
    ('| 合格 |', '| 可 |', 'RP8'),
    ('| `dc-01` | No |', '| `dc-01` | いいえ |', 'RP10'),
    ('| `dc-01` |', '| `dc-99` |', 'RP10'),
])
def test_report_form_errors(old, new, rule):
    text = _report()
    assert old in text, old
    rules = {r for r, _, _ in review_check.check_report(ROOT, text.replace(old, new, 1))}
    assert rule in rules, rules


def test_report_mismatch_needs_the_confused_question():
    text = _report()
    row = next(x for x in text.split('\n') if '| 目的と仕組みの不一致 |' in x)
    cells = row.split(' | ')
    cells[6] = '—'
    assert 'RP5' in {r for r, _, _ in review_check.check_report(ROOT, text.replace(row, ' | '.join(cells)))}


def test_review_check_cli_takes_reports():
    assert review_check.main(['--root', ROOT, '--report', REPORT]) == 0


def test_roles_and_stages_of_perspectives():
    import trace_check
    text = trace_check._read(os.path.join(ROOT, 'templates', 'review', 'perspectives.md'))
    qs = review_check.parse_questions(text)
    roles, stages = review_check.roles_and_stages(text, qs)
    assert [r['id'] for r in roles] == [x for x, _ in review_check.ROLE_IDS]
    assert all(r['questions'] for r in roles)
    assert 'q-token-not-in-url' in next(r for r in roles if r['id'] == 'role-client')['questions']
    assert 'dc-01' not in next(r for r in roles if r['id'] == 'role-client')['questions']  # 8. is not part of 7.6
    assert [s['id'] for s in stages] == [x for x, _ in review_check.STAGES] and all(s['who'] for s in stages)


def test_diff_lists_changed_rows(tmp_path, capsys):
    design = tmp_path / 'b'
    shutil.copytree(B, design)
    p = design / 'claims.yaml'
    p.write_text(p.read_text(encoding='utf-8').replace('  - id: C-iss\n', '  - id: C-iss\n    x_changed: 1\n', 1), encoding='utf-8')
    assert rr.main(['diff', B, str(design)]) == 0
    assert capsys.readouterr().out.split('\n')[0] == 'changed  claims:C-iss'
