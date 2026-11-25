# -*- coding: utf-8 -*-
"""tools/review_record.py (#50, #67): review.yaml (claims-review/2) against its schema, viewed marks that no longer hold
after an edit, comment states, submissions, the migration from claims-review/1 (still read; the pilot originals are
kept byte for byte), merge, sampling, the report, and the form check of review reports (tools/review_check.py).

  python -m pytest -q tools/tests/test_review_record.py

The browser side (docs/claims/review-format.js) writes the same text and the same report:
tools/tests/test_claims_review_ui.py.
"""
import copy
import hashlib
import json
import os
import re
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


def test_schemas_are_valid_2020_12():
    for path, fmt in ((rr.SCHEMA, 'claims-review/2'), (rr.SCHEMA_V1, 'claims-review/1')):
        with open(path, encoding='utf-8') as f:
            schema = json.load(f)
        jsonschema.Draft202012Validator.check_schema(schema)
        assert schema['properties']['format'] == {'const': fmt}


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
    assert all(f['verdict'] == '保留' for f in rv['comments'])  # a person has not decided yet
    assert len(rv['viewed']) > 30


def test_canonical_text_round_trips():
    text = open(EXAMPLE, encoding='utf-8').read()
    assert rr.dump(rr.load_text(text)) == text
    odd = {'format': 'claims-review/2', 'design': 'x', 'independent': False, 'reviews': [{
        'reviewer': {'name': 'yes', 'kind': 'human'}, 'self_declared': True, 'started': '2026-01-01', 'submitted': None,
        'answers': {'q-a': {'answer': 'no', 'memo': 'a "q" \\ \n\t\x7f ﻿: # x'}}, 'viewed': {}, 'comments': [], 'submissions': []}]}
    assert rr.check(odd)[0] == []
    assert rr.load_text(rr.dump(odd)) == odd
    assert rr.dump(rr.load_text(rr.dump(odd))) == rr.dump(odd)


def test_schema_and_vocabulary_errors():
    d = example()
    d['reviews'][0]['comments'][0]['severity'] = 'Critical'
    assert any('severity' in e for e in rr.check(d)[0])
    d = example()
    f = d['reviews'][0]['comments'][0]
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


def test_an_edited_row_takes_its_viewed_mark_away(tmp_path):
    design = tmp_path / 'scenario-b'
    shutil.copytree(B, design)
    rv = example()['reviews'][0]
    a = next(a for a in rv['viewed'] if a.startswith('hops:'))
    hop = a.split(':', 1)[1]
    p = design / 'hops.yaml'
    text = p.read_text(encoding='utf-8')
    assert f'  - id: {hop}\n' in text
    p.write_text(text.replace(f'  - id: {hop}\n', f'  - id: {hop}\n    x_changed: 1\n', 1), encoding='utf-8')
    errs, notes = rr.check(example(), str(design))
    assert errs == []
    assert any(a in n and '前回の確認から変更あり' in n for n in notes) and len(notes) == 1
    assert rr.main(['check', EXAMPLE, '--design', str(design)]) == 0
    assert rr.main(['check', EXAMPLE, '--design', str(design), '--fail-on-stale']) == 1
    # a comment changes nothing
    p.write_text(text.replace(f'  - id: {hop}\n', f'  - id: {hop}  # a comment\n', 1), encoding='utf-8')
    assert rr.check(example(), str(design))[1] == []
    # a removed row: the record is reported, not dropped
    p.write_text(text.replace(f'  - id: {hop}\n', f'  - id: {hop}-renamed\n', 1), encoding='utf-8')
    notes = rr.check(example(), str(design))[1]
    assert any(a in n and '一覧に無い行' in n for n in notes)


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
    f = rv['comments'][0]
    f['location'], f['content'] = EVIL[0], ' '.join(EVIL)
    f['response']['owner'] = '<script>'
    sc = rv['sampling']['scores']
    sc[next(iter(sc))]['note'] = '<!-- note'
    rv['viewed'][next(iter(rv['viewed']))]['migrated_from']['comment'] = '</td></tr><!--'
    rv['submissions'][0]['summary'] = '<!-- 総評 | x'
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
    for r in rv['viewed'].values():
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



# ------------------------------------------------------------------ #67: claims-review/2 and the migration from claims-review/1
PILOT = os.path.join(ROOT, 'research', 'pilot')
PILOT_REVIEWS = [(d, r) for d in ('scenario-b', 'scenario-c') for r in ('R1', 'R2')]


def _pilot(d, r, name='review.yaml'):
    return os.path.join(PILOT, d, 'reviews', r, name)


def _v1():
    return rr.load(_pilot('scenario-c', 'R1'))


def test_the_pilot_originals_are_not_rewritten():
    """research/pilot/commitments.txt holds the sha256 of the files as they were handed in: they stay claims-review/1."""
    n = 0
    with open(os.path.join(PILOT, 'commitments.txt'), encoding='utf-8') as f:
        for line in f:
            m = re.match(r'([0-9a-f]{64}) \*review-([BC])-(R[12])/(\S+)$', line.strip())
            if not m:
                continue
            want, case, rev, name = m.groups()
            with open(_pilot(f'scenario-{case.lower()}', rev, name), 'rb') as g:
                # the committed bytes have LF; a checkout with core.autocrlf has CRLF in the working tree
                assert hashlib.sha256(g.read().replace(b'\r\n', b'\n')).hexdigest() == want, (case, rev, name)
            n += 1
    assert n == 12
    for d, r in PILOT_REVIEWS:
        assert rr.load(_pilot(d, r))['format'] == 'claims-review/1'


@pytest.mark.parametrize('d,r', PILOT_REVIEWS)
def test_a_v1_file_is_read_as_it_is_and_its_copy_is_its_migration(d, r, capsys):
    design = os.path.join(PILOT, d)
    path = _pilot(d, r)
    with open(path, encoding='utf-8') as f:
        raw = f.read().replace('\r\n', '\n')
    data = rr.load_text(raw)
    assert rr.dump(data, rr.version_of(raw)) == raw  # the v1 dumper still writes the same bytes
    assert rr.check(data, design)[0] == []
    assert rr.main(['check', path, '--design', design]) == 0
    out = capsys.readouterr().out
    assert 'info ' in out and 'claims-review/1' in out and 'migrate' in out
    copy_ = _pilot(d, r, 'review.v2.yaml')
    assert rr.main(['migrate', path, '--check', copy_]) == 0
    assert rr.load(copy_)['format'] == 'claims-review/2'
    assert rr.main(['check', copy_, '--design', design]) == 0
    assert 'info ' not in capsys.readouterr().out.split('migrate --check')[1]  # the copy is not v1


def test_migration_keeps_everything_and_is_deterministic():
    v1 = _v1()
    before = copy.deepcopy(v1)
    v2 = rr.migrate(v1)
    assert v1 == before  # the input is left alone
    assert rr.dump(v2, '0.4.0') == rr.dump(rr.migrate(copy.deepcopy(before)), '0.4.0')
    assert rr.migrate(v2) is v2 and rr.dump(rr.migrate(v2), '0.4.0') == rr.dump(v2, '0.4.0')  # a v2 record is not migrated again
    assert rr.schema_errors(v2) == []
    a, b = before['reviews'][0], v2['reviews'][0]
    assert 'rows' not in b and 'findings' not in b
    assert set(b['viewed']) == set(a['rows'])
    for k, r in a['rows'].items():
        m = b['viewed'][k]
        assert m['hash'] == r['hash'] and m['at'] == r['at'] and m['migrated_from']['decision'] == r['decision']
        assert m['migrated_from'].get('comment') == r.get('comment') and m.get('reviewer_kind') == r.get('reviewer_kind')
    assert [dict(c) for c in b['comments']] == [dict(f, state='unresolved') for f in a['findings']]
    assert b['submitted'] == a['submitted'] and len(b['submissions']) == 1
    sb = b['submissions'][0]
    assert sb['at'] == a['submitted'] and sb['verdict'] == 'comment' and sb['migrated'] is True
    assert sb['viewed'] == {k: r['hash'] for k, r in a['rows'].items()} and sb['comments'] == [f['id'] for f in a['findings']]
    for k in ('reviewer', 'answers', 'context', 'materials', 'sampling', 'escalations', 'target'):
        assert b.get(k) == a.get(k)
    assert [x.get('comments') for x in b.get('feedback') or []] == [x.get('findings') for x in a.get('feedback') or []]
    # a review that was not submitted: no submission, its findings are pending comments
    v1 = copy.deepcopy(before)
    v1['reviews'][0]['submitted'] = None
    v2 = rr.migrate(v1)
    assert v2['reviews'][0]['submissions'] == [] and {c['state'] for c in v2['reviews'][0]['comments']} == {'pending'}
    assert rr.check(v2)[0] == []


def test_migrate_cli(tmp_path, capsys):
    src = _pilot('scenario-c', 'R1')
    out = tmp_path / 'review.v2.yaml'
    assert rr.main(['migrate', src, '-o', str(out)]) == 0
    assert out.read_text(encoding='utf-8') == open(_pilot('scenario-c', 'R1', 'review.v2.yaml'), encoding='utf-8').read().replace('\r\n', '\n')
    assert rr.main(['migrate', src, '--check', str(out)]) == 0
    out.write_text(out.read_text(encoding='utf-8').replace('verdict: "comment"', 'verdict: "approve"', 1), encoding='utf-8')
    assert rr.main(['migrate', src, '--check', str(out)]) == 1
    assert 'FAIL' in capsys.readouterr().out
    # the migration of a v2 file is the file
    again = tmp_path / 'again.yaml'
    assert rr.main(['migrate', EXAMPLE, '-o', str(again)]) == 0
    assert again.read_text(encoding='utf-8') == open(EXAMPLE, encoding='utf-8').read().replace('\r\n', '\n')


def test_a_v1_record_with_a_schema_error_is_not_migrated_silently():
    v1 = _v1()
    v1['reviews'][0]['rows'][next(iter(v1['reviews'][0]['rows']))]['decision'] = 'ok'
    assert any('decision' in e for e in rr.check(v1)[0])
    mixed = _v1()
    mixed['reviews'][0]['viewed'] = {}  # a v2 key in a v1 file
    assert rr.check(mixed)[0]
    v2 = example()
    v2['reviews'][0]['rows'] = {}  # a v1 key in a v2 file
    assert rr.check(v2)[0]


def test_submitted_is_the_latest_submission():
    d = example()
    rv = d['reviews'][0]
    rv['submitted'] = None
    assert any('submitted is null' in e for e in rr.check(d)[0])
    d = example()
    d['reviews'][0]['submissions'] = []
    assert any('no submission' in e for e in rr.check(d)[0])
    d = example()
    d['reviews'][0]['submitted'] = '2026-11-24'
    assert any('latest submission' in e for e in rr.check(d)[0])
    d = example()
    rv = d['reviews'][0]
    rv['submissions'].append({'at': '2026-11-25T10:00:00Z', 'verdict': 'request_changes', 'summary': '2 回目', 'viewed': {}, 'unresolved': 3})
    rv['submitted'] = '2026-11-25T10:00:00Z'
    assert rr.check(d, B) == ([], [])
    rv['submissions'][-1]['verdict'] = 'reject'
    assert any('verdict' in e for e in rr.check(d)[0])


def test_comment_states():
    d = example()
    rv = d['reviews'][0]
    rv['comments'][0]['state'] = 'resolved'
    rv['comments'][0]['resolved_at'] = '2026-11-25'
    assert rr.check(d)[0] == []
    rv['comments'][1]['state'] = 'pending'  # it was submitted
    assert any('in a submission but its state is pending' in e for e in rr.check(d)[0])
    d = example()
    rv = d['reviews'][0]
    new = dict(rv['comments'][0], id='N01', state='pending', column='usage', suggestion='x', hash='0' * 64)
    rv['comments'].append(new)  # written after the submission: pending
    assert rr.check(d)[0] == []
    new['state'] = 'unresolved'
    assert any('N01 is unresolved but in no submission' in e for e in rr.check(d)[0])
    new['state'] = 'open'
    assert any('state' in e for e in rr.check(d)[0])
    d = example()
    d['reviews'][0]['submissions'][0]['comments'].append('F-none')
    assert any('names comment F-none' in e for e in rr.check(d)[0])
    d = example()
    d['reviews'][0]['comments'].append(copy.deepcopy(d['reviews'][0]['comments'][0]))
    assert any('written twice' in e for e in rr.check(d)[0])
    d = example()
    d['reviews'][0]['feedback'] = [{'to': 'カタログ', 'content': 'x', 'comments': ['F-none']}]
    assert any('feedback names comment F-none' in e for e in rr.check(d)[0])


def test_the_snapshot_of_a_viewed_mark_must_hash_to_it():
    docs = row_hash.load(B)
    hashes = row_hash.row_hashes(B)['hashes']
    row = next(c for c in docs['claims']['claims'] if c['id'] == 'C-iss')
    text = row_hash.jcs(row)
    assert hashlib.sha256(text.encode('utf-8')).hexdigest() == hashes['claims:C-iss']
    d = example()
    m = d['reviews'][0]['viewed']['claims:C-iss']
    m['snapshot'] = text
    assert rr.check(d, B) == ([], [])
    assert rr.load_text(rr.dump(d)) == d  # a JSON text inside the YAML survives the round trip
    m['snapshot'] = text.replace('C-iss', 'C-isx')
    assert any('claims:C-iss' in e and 'snapshot' in e for e in rr.check(d)[0])


def test_an_approval_of_rows_that_changed_is_old(tmp_path, capsys):
    design = tmp_path / 'b'
    shutil.copytree(B, design)
    d = example()
    rv = d['reviews'][0]
    rv['submissions'].append({'at': '2026-11-25T10:00:00Z', 'verdict': 'approve', 'viewed': {a: m['hash'] for a, m in rv['viewed'].items()}})
    rv['submitted'] = '2026-11-25T10:00:00Z'
    assert rr.check(d, str(design)) == ([], [])
    assert '古い承認：' not in rr.report(d, str(design), rr.review_data())
    p = design / 'hops.yaml'
    p.write_text(p.read_text(encoding='utf-8').replace('  - id: H15\n', '  - id: H15\n    x_changed: 1\n', 1), encoding='utf-8')
    errs, notes = rr.check(d, str(design))
    assert errs == [] and len(notes) == 2
    assert any('hops:H15' in n and '前回の確認から変更あり' in n for n in notes)
    assert any('古い承認（内容が変更されました）' in n and 'hops:H15' in n for n in notes)
    y = tmp_path / 'review.yaml'
    y.write_text(rr.dump(d, '0.4.0'), encoding='utf-8', newline='\n')
    assert rr.main(['check', str(y), '--design', str(design)]) == 0
    assert rr.main(['check', str(y), '--design', str(design), '--fail-on-stale']) == 1
    text = rr.report(d, str(design), rr.review_data())
    assert '承認（古い承認：内容が変更されました。1 行）' in text and '前回の確認から変更あり 1' in text
    # a later submission that is not an approval: nothing is called an old approval
    rv['submissions'].append({'at': '2026-11-26', 'verdict': 'comment', 'viewed': {}})
    rv['submitted'] = '2026-11-26'
    assert not any('古い承認' in n for n in rr.check(d, str(design))[1])


def test_report_section_9_lists_submissions_states_and_viewed_rows():
    d = example()
    rv = d['reviews'][0]
    text = rr.report(d, B, rr.review_data())
    sec9 = text.split('## 9. 確認済みの行と提出の記録')[1]
    intro = sec9.split('| 日時 |')[0]  # the fixed text (the cells below are values of review.yaml)
    assert '台帳' not in intro and 'ホップ' not in intro and '承認ではありません' in intro
    assert '| コメントのみ（移行） |' in sec9 and f'| {len(rv["viewed"])} | {len(rv["comments"])} |' in sec9
    assert f'コメントの状態：未提出 0・未解決 {len(rv["comments"])}・解決済み 0' in sec9
    assert f'計 {len(rv["viewed"])} 行：一致 {len(rv["viewed"])}・前回の確認から変更あり 0・一覧に無い 0' in sec9
    a = sorted(rv['viewed'])[0]
    m = rv['viewed'][a]
    assert f'| {rr.md(a)} | {m["at"]}（LLM） | 一致（確認したときのまま）（{m["hash"][:12]}） | {rr.DECISION_JA[m["migrated_from"]["decision"]]}' in sec9
    # not submitted: said, and the form still holds
    rv['submitted'], rv['submissions'] = None, []
    for c in rv['comments']:
        c['state'] = 'pending'
    assert rr.check(d, B)[0] == []
    text = rr.report(d, B, rr.review_data())
    assert '未提出（判定はまだ無い）。' in text and f'未提出 {len(rv["comments"])}・未解決 0' in text
    assert review_check.check_report(ROOT, text) == []


def test_merge_takes_v1_and_v2_files_together():
    a = rr.load(_pilot('scenario-b', 'R1'))
    b = rr.load(_pilot('scenario-b', 'R2', 'review.v2.yaml'))
    assert a['format'] == 'claims-review/1' and b['format'] == 'claims-review/2'
    m = rr.merge([a, b])
    assert m['format'] == 'claims-review/2' and len(m['reviews']) == 2
    assert rr.check(m, os.path.join(PILOT, 'scenario-b'))[0] == []
    assert rr.merge([a, rr.load(_pilot('scenario-b', 'R1', 'review.v2.yaml'))])['reviews'] == rr.migrate(a)['reviews']  # the same review twice


def test_traits_are_booleans_by_id():
    d = example()
    d['reviews'][0]['traits'] = {'external_party': True, 'audited': False}
    assert rr.check(d)[0] == [] and rr.load_text(rr.dump(d)) == d
    d['reviews'][0]['traits'] = {'External Party': True}
    assert rr.check(d)[0]
    d['reviews'][0]['traits'] = {'audited': 'yes'}
    assert rr.check(d)[0]
