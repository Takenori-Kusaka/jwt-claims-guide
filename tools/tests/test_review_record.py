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
    d['reviews'][0]['answers']['q-no-such-question'] = {'answer': 'yes'}  # the materials changed: a warning, not an error
    errs, notes = rr.check(d)
    assert errs == [] and any('q-no-such-question' in n and '教材' in n for n in notes)
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
    ('| dc-01 | No |', '| dc-01 | いいえ |', 'RP10'),
    ('| dc-01 |', '| dc-99 |', 'RP10'),
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


# ------------------------------------------------------------------ PR #52 check: escaping, versions, population, reseed
EVIL = ['<!-- hide the rest', '<script>alert(1)</script>', '</details>', 'a | b | c', '`code` and ``x``', '# heading',
        '> quote', '<img src=https://example.com/x.png>', '[link](https://example.com)', '*em* _em_ ~~s~~', 'a & b']


def _evil_review():
    d = example()
    rv = d['reviews'][0]
    rv['reviewer']['name'] = '<b>名前</b> | `x`'
    rv['context']['human_check'] = '# <!-- 7. を隠す'
    rv['answers']['dc-01']['memo'] = ' / '.join(EVIL)
    f = rv['findings'][0]
    f['location'], f['content'] = EVIL[0], ' '.join(EVIL)
    f['response']['owner'] = '<script>'
    sc = rv['sampling']['scores']
    sc[next(iter(sc))]['note'] = '<!-- note'
    rv['rows'][next(iter(rv['rows']))]['comment'] = '</td></tr><!--'
    return d


def test_report_escapes_every_value():
    text = rr.report(_evil_review(), B, rr.review_data(), label='<!-- label', version='0.4.0')
    for bad in ('<!--', '<script', '</details>', '<img', '<b>', '[link](', ' `code`'):
        assert bad not in text, bad
    assert '&lt;!-- hide the rest' in text and '&lt;script&gt;' in text and '\\`code\\`' in text and 'a &amp; b' in text
    assert '\\[link\\]' in text and '\\*em\\*' in text
    sec7 = text.split('## 7. ')[1].split('## 8. ')[0]
    assert '\\# &lt;!-- 7. を隠す' in sec7  # a value that starts a line with "#" stays text
    assert '人による点検は未実施' in sec7  # a fixed sentence: no value can hide it
    assert review_check.check_report(ROOT, text) == []  # the tables are still the form


def test_report_human_reviewer_is_not_called_unchecked_wrongly():
    d = example()
    rv = d['reviews'][0]
    rv['reviewer'] = {'name': '人', 'kind': 'human'}
    del rv['context']['human_check']
    for r in rv['rows'].values():
        r['reviewer_kind'] = 'human'
    text = rr.report(d, B, rr.review_data())
    assert 'レビュアーは人（名前は自己申告）' in text and '（LLM）' not in text


def test_report_versions_are_those_of_the_review():
    R = dict(rr.review_data(), template_version='9.9.9')
    d = example()
    text = rr.report_text(d, d['reviews'][0], R, row_hash.row_hashes(B)['hashes'], row_hash.load(B), version='0.4.0')
    assert 'レビューした時の版：perspectives.md 0.4.0' in text and '今の教材は perspectives.md 9.9.9' in text
    assert '今の教材' not in rr.report(d, B, rr.review_data(), version='0.4.0')


def test_a_changed_population_is_a_warning_and_reseed_records_the_old_draw(tmp_path):
    design = tmp_path / 'b'
    shutil.copytree(B, design)
    p = design / 'claims.yaml'
    p.write_text(p.read_text(encoding='utf-8').replace('  - id: C-kc-client-id\n', '  - id: C-kc-client-id0\n', 1), encoding='utf-8')
    errs, notes = rr.check(example(), str(design))
    assert errs == [] and any('抜き取りの母集団が変わった' in n for n in notes)
    y = tmp_path / 'review.yaml'
    shutil.copy(EXAMPLE, y)
    who = example()['reviews'][0]['reviewer']['name']
    assert rr.main(['sample', str(design), '--reseed', '--file', str(y), '--reviewer', who, '--reason', '却下の行の ID が変わった']) == 0
    d = rr.load(str(y))
    sm = d['reviews'][0]['sampling']
    assert sm['reason'] == '却下の行の ID が変わった' and sm['previous'][0]['picked'] == example()['reviews'][0]['sampling']['picked']
    assert sm['picked'] == rr.sample(sm['seed'], sm['count'], row_hash.load(str(design)))
    errs, notes = rr.check(d, str(design))
    assert errs == [] and not any('母集団' in n for n in notes)
    assert rr.main(['check', str(y), '--design', str(design)]) == 0


def test_tampered_draw_from_the_same_rows_is_an_error():
    d = example()
    d['reviews'][0]['sampling']['picked'] = list(reversed(d['reviews'][0]['sampling']['picked']))
    assert any('from the same rows' in e for e in rr.check(d, B)[0])


def test_annotations_for_stale_approvals(tmp_path, capsys):
    design = tmp_path / 'b'
    shutil.copytree(B, design)
    p = design / 'hops.yaml'
    p.write_text(p.read_text(encoding='utf-8').replace('  - id: H15\n', '  - id: H15\n    x_changed: 1\n', 1), encoding='utf-8')
    assert rr.main(['check', EXAMPLE, '--design', str(design), '--annotate']) == 0
    out = capsys.readouterr().out
    assert '::warning file=' in out and 'hops:H15' in out


def test_independence_is_reported():
    d = example()
    rv = d['reviews'][0]
    d['independent'] = True
    rv['independence'] = {'mode': 'broken', 'broken_at': '2026-11-24T10:00:00Z', 'reason': '独立レビューの設定を外した',
                          'viewed_others_at': '2026-11-24T10:00:00Z'}
    rv['answers']['dc-01']['edited_after_viewing_others'] = True
    rv['updated'] = '2026-11-25T00:00:00Z'
    assert rr.check(d, B)[0] == []
    text = rr.report(d, B, rr.review_data())
    assert '提出の前に外れた（2026-11-24T10:00:00Z。独立レビューの設定を外した）' in text
    assert 'その後に直した記録 1 件' in text and '提出（2026-11-23）の後に更新した' in text

