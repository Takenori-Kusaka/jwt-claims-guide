# -*- coding: utf-8 -*-
"""tools/review_triage.py (#56): templates/review/triage.yaml classifies every question of perspectives.md, the lint
rules it cites exist and decide the questions given to them, the generated files match, the short list of a design
follows its traits (and does not get shorter silently), and the record of what the short list would have prompted among
the Major findings of the pilot (#9) adds up. No browser is needed: the default (short list) path of the editor is
checked here on the data the editor loads (docs/claims/data/review.js)."""
import copy
import json
import os
import re
import shutil
import sys

import pytest
import yaml

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import build_claims_viewer as bcv  # noqa: E402
import review_check as rc  # noqa: E402
import review_triage as rt  # noqa: E402
import review_triage_audit as audit  # noqa: E402

COPY = ['templates', 'deck/slide_ids.json', 'tools/template_sources.yaml', 'tools/claim_lint/RULES.md',
        '.github/PULL_REQUEST_TEMPLATE/design_doc.md', 'research/template-design/triage-evidence.md',
        'research/template-design/triage-audit.md']
TRIAGE = os.path.join('templates', 'review', 'triage.yaml')
DESIGNS = {'A': 'templates/examples/scenario-a', 'B': 'templates/examples/scenario-b',
           'pilot-B': 'research/pilot/scenario-b', 'pilot-C': 'research/pilot/scenario-c'}


@pytest.fixture
def root(tmp_path):
    for rel in COPY:
        src, dst = os.path.join(ROOT, rel), tmp_path / rel
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)
    return tmp_path


def edit(root, rel, old, new):
    p = root / rel
    text = p.read_text(encoding='utf-8')
    assert old in text, old
    p.write_text(text.replace(old, new, 1), encoding='utf-8', newline='\n')


def rules(root):
    return sorted({e[0] for e in rt.check(str(root))})


def design(key):
    return rt.load_design(os.path.join(ROOT, DESIGNS[key]))


def traits_of(key):
    return rt.traits(design(key))


def ids(qs):
    return {q['id'] for q in qs}


# ---------------------------------------------------------------- the classification
def test_repository_triage_passes():
    assert rt.check(ROOT) == []
    assert rt.main(['--root', ROOT, '--check']) == 0


def test_copy_passes_and_review_check_runs_it_as_v14(root):
    assert rules(root) == []
    edit(root, TRIAGE, '- {id: dc-01, class: A, lint: [L5],', '- {id: dc-01, class: A, lint: [L99],')
    errors, _, _ = rc.check(str(root))
    assert {e[0] for e in errors} == {'V14'}
    assert any('T3' in e[2] and 'L99' in e[2] for e in errors)


def test_every_question_has_one_class_and_a_reason():
    tri = rt.load(ROOT)
    _, questions, _ = rc.check(ROOT)
    got = [q['id'] for q in tri['questions']]
    assert sorted(got) == sorted(q['id'] for q in questions) and len(got) == len(set(got)) == 168
    assert all(q['class'] in 'ABCD' and q['why'].strip() for q in tri['questions'])
    c = rt.counts(tri)
    assert (c['A'], c['B'], c['C'], c['D']) == (81, 36, 47, 4)
    assert (c['A_with_rule'], c['A_partial_rule'], c['A_without_rule']) == (39, 23, 19)
    assert (c['C_priority_1'], c['C_priority_2'], c['C_priority_3'], c['C_until_rule']) == (19, 10, 18, 4)
    assert c['open_prompts'] == 6


def test_no_part_of_a_question_is_left_to_nobody():
    # every question is answered by a rule alone (audited below), by the author (class B or interim: B), by a reviewer
    # (class C: on the default list, merged into a question on it, or done in a step of the procedure), or by an expert
    tri = rt.load(ROOT)
    by = rt.by_id(tri)
    author = {i for x in rt.author_lines(tri) for i in x['ids']}
    for q in tri['questions']:
        if q['class'] == 'A':
            assert (q.get('lint') and not q.get('proposed')) or q['id'] in author, q['id']
            if q.get('rest'):
                assert by[q['rest']]['class'] == 'C' and by[q['rest']]['priority'] in (1, 2)
        if q['class'] == 'B':
            assert q['id'] in author, q['id']
        if q['class'] == 'C' and q['priority'] == 3 and q.get('merged_into'):
            assert by[q['merged_into']]['priority'] in (1, 2) and not by[q['merged_into']].get('merged_into')
    assert not author & {q['id'] for q in tri['questions'] if q['class'] in 'CD'}


def test_t1_a_question_without_a_class_and_an_unknown_question(root):
    edit(root, TRIAGE, '  - {id: dc-01, class: A, lint: [L5], why: "usage と volatility と寿命の比較は、台帳と目録の値の計算で決まる"}\n', '')
    assert rules(root) == ['T1']
    edit(root, TRIAGE, '  - {id: dc-02,', '  - {id: dc-99,')
    assert rules(root) == ['T1']


def test_t3_lint_rules_must_exist_and_proposals_must_be_known(root):
    edit(root, TRIAGE, '- {id: ap-1-6, class: A, lint: [L3],', '- {id: ap-1-6, class: A, lint: [L24],')   # planned, not implemented
    assert rules(root) == ['T3']


def test_t3_an_implemented_rule_is_not_a_proposal(root):
    edit(root, TRIAGE, 'lint: [], proposed: [L36], interim: B, why: "shape の値', 'lint: [], proposed: [L5], interim: B, why: "shape の値')
    assert rules(root) == ['T3']


def test_t3_a_question_no_rule_decides_goes_to_the_author_meanwhile(root):
    edit(root, TRIAGE, 'proposed: [L54], interim: B,', 'proposed: [L54],')
    assert rules(root) == ['T3']


def test_t3_the_rest_of_a_partly_decided_question_goes_to_a_question_reviewers_get(root):
    edit(root, TRIAGE, 'lint: [L3], rest: q-value-vocabulary, why: "変わりうる名前', 'lint: [L3], rest: q-break-glass, why: "変わりうる名前')   # priority 3
    assert rules(root) == ['T3']


def test_t4_t5_human_and_expert_questions(root):
    edit(root, TRIAGE, '{id: q-operator-act, class: C, priority: 1, unit: design, show_when: [always],',
         '{id: q-operator-act, class: C, priority: 1, unit: design, show_when: [no_such_condition],')
    assert rules(root) == ['T4']
    edit(root, TRIAGE, 'show_when: [no_such_condition],', 'show_when: [always],')
    edit(root, TRIAGE, 'escalation: custom-crypto', 'escalation: no-such-criterion')
    assert rules(root) == ['T5']


def test_t4_a_question_for_a_reviewer_is_one_sentence(root):
    edit(root, TRIAGE, 'ask: "運用者・管理者の操作を、後から利用者の操作と見分けられるか"', 'ask: "運用者はどのトークンで動くか。後から見分けられるか"')
    assert rules(root) == ['T4']


def test_every_ask_is_one_sentence_and_names_where_to_look():
    tri = rt.load(ROOT)
    see = {q['id']: q['fields']['見る欄'] for q in rc.parse_questions(open(os.path.join(ROOT, rt.PERSP), encoding='utf-8').read())}
    for q in [q for q in tri['questions'] if q['class'] == 'C'] + tri['open_prompts']:
        assert rt.sentences(q['ask']) == 1 and '。' not in q['ask'] and len(q['ask']) <= rt.ASK_MAX, q['id']
        assert q.get('hint'), q['id']
        if not q['id'].startswith('op-'):
            assert see[q['id']]   # the fields to open come with the question (short_list.md and the design sheet print them)


def test_t9_generated_files_follow_triage(root):
    edit(root, TRIAGE, '同じ意味の値が、別の名前で 2 行に分かれていないか', '同じ意味の値が、別の名前で 2 つの行に分かれていないか')
    assert rules(root) == ['T9']
    assert rt.main(['--root', str(root), '--write']) == 0
    assert rules(root) == []
    assert '2 つの行に分かれていないか' in (root / 'templates' / 'review' / 'short_list.md').read_text(encoding='utf-8')


def test_every_question_of_perspectives_shows_its_class():
    tri = rt.load(ROOT)
    text = open(os.path.join(ROOT, rt.PERSP), encoding='utf-8').read()
    qs = rc.parse_questions(text)
    by = rt.by_id(tri)
    for q in qs:
        assert q['fields']['区分'].startswith(by[q['id']]['class'] + ' '), q['id']
    f = {q['id']: q['fields']['区分'] for q in qs}
    # a question that an existing rule decides says so, and tells the reviewer not to answer
    assert 'lint の `lint:L5` が確かめる（レビュアーは答えない）' in f['dc-01']
    assert '規則が見ない残りは、`q-value-vocabulary` でレビュアーが見る' in f['dc-09']
    assert '規則ができるまでレビュアーが答える' in f['q-single-aud-resource']
    assert '`q-revocation-delivery` にまとめた' in f['q-relies-on-at-expiry']


def test_author_self_check_is_grouped_and_marks_what_the_reviewer_samples():
    tri = rt.load(ROOT)
    text = open(os.path.join(ROOT, rt.PR_TEMPLATE), encoding='utf-8').read()
    lines = [x for x in text.split('\n') if x.startswith('- [ ] ')]
    want = {q['id'] for q in tri['questions'] if q['class'] == 'B' or q.get('interim') == 'B'}
    got = [i for x in lines for i in re.findall(r'`([a-z0-9-]+)`', x.rsplit(' — ', 1)[1])]
    assert set(got) == want and len(got) == len(set(got)) == 78
    assert len(lines) == 55
    # the 25-question answers are one line; questions waiting for the same rule are one line
    assert sum('`pa-03`' in x and '`pa-25`' in x and '`pa-trace`' in x for x in lines) == 1
    # that line holds the most checks behind one tick: the reviewer always samples it at step 0
    assert [x for x in lines if '【レビュアーが必ず抜き取る】' in x] == [x for x in lines if '`pa-03`' in x]
    assert sum('`cf-07`' in x and '`ap-1-2`' in x and 'L46' in x for x in lines) == 1
    # the data-layer Blocker items are marked: the reviewer samples three of the marked lines at step 0
    marked = [x for x in lines if '【No なら Blocker】' in x]
    assert len(marked) == 13 and sum('`cd-0' in x or '`cd-10`' in x for x in marked) >= 5
    proc = open(os.path.join(ROOT, 'templates', 'review', 'procedure.md'), encoding='utf-8').read()
    assert '25 問の回答をまとめた行（【レビュアーが必ず抜き取る】）を必ず入れる' in proc and '残りの 2 件は、**【No なら Blocker】の行**から選ぶ' in proc


# ---------------------------------------------------------------- the rules really decide the questions given to them
def test_every_question_decided_by_a_rule_alone_is_reported_when_its_answer_becomes_no():
    rows = audit.run()
    assert len(rows) == 39
    assert [r['question'] for r in rows if not r['ok']] == []
    record = open(os.path.join(ROOT, audit.RECORD), encoding='utf-8').read()
    assert record == audit.record(rows)
    # the audit tests one direction only, and says so (the re-check of PR #71 found three questions it had passed)
    assert '「No にしたら指摘が出る」の向きだけ' in record and '`q-deprecated-deadline`' in record
    by = rt.by_id(rt.load(ROOT))
    for qid in ('q-deprecated-deadline', 'ap-2-9', 'q-internal-delegation-token'):
        assert by[qid]['proposed'] and by[qid]['interim'] == 'B'
    assert 'L11' in by['ap-1-3']['lint'] and 'L16' in by['q-txn-scope-fixed']['lint']


def test_the_audit_fails_for_a_rule_that_does_not_decide(monkeypatch):
    # the finding of the independent check: L70 does not look at pii_category of a row a hook writes
    tri = rt.load(ROOT)
    q = next(q for q in tri['questions'] if q['id'] == 'q-hook-adds-raw-pii')
    q.update(lint=['L70'], proposed=[])
    q.pop('interim')

    def hook_pii(d):
        r = audit.c(d, 'C-v')
        r['pii_category'] = '要配慮個人情報'
        r['description'] = '生年月日'
    monkeypatch.setitem(audit.MUTATIONS, 'hook-pii', ('A', hook_pii, 'C-v を要配慮個人情報にする'))
    monkeypatch.setitem(audit.AUDIT, 'q-hook-adds-raw-pii', 'hook-pii')
    monkeypatch.setattr(rt, 'load', lambda root=ROOT: tri)
    rows = audit.run(only={'q-hook-adds-raw-pii'})
    assert [(r['question'], r['ok']) for r in rows] == [('q-hook-adds-raw-pii', False)]


# ---------------------------------------------------------------- traits and the short list of a design
def test_traits_are_read_from_the_registry_and_from_what_the_author_declared():
    a, b, pb, pc = (traits_of(k) for k in ('A', 'B', 'pilot-B', 'pilot-C'))
    # scenario A: two realms of one IdP are not several issuers
    assert a == {'always', 'org_claims', 'pii', 'multitenant', 'data_layer', 'auth_context', 'sender_declined', 'long_running'}
    assert {'delegation', 'exchange', 'approval', 'sender_constrained', 'multi_idp'} <= b and 'multitenant' not in b
    assert {'multi_idp', 'exchange', 'data_layer', 'sender_declined'} <= pb
    assert pc == {'always', 'pii', 'exchange', 'delegation', 'approval', 'sender_constrained', 'long_running'}
    tr = rt.read_traits(design('pilot-C'))
    assert set(tr) == set(rt.load(ROOT)['conditions']) and all(v['state'] in ('on', 'off', 'unknown') and v['evidence'] for v in tr.values())
    assert tr['multitenant']['state'] == 'off' and '書き手の宣言' in tr['multitenant']['evidence']
    # the author's answer decides multitenant: scenario C binds its tokens to the issuer but is one organisation
    reg = design('pilot-C')
    assert any(t.get('tenant_binding') for t in reg['token_types']['token_types'])
    del reg['catalog_answers']['lite_criteria']['multitenant']
    assert 'multitenant' in rt.traits(reg)


def test_several_idps_declared_in_catalog_answers_turn_the_multi_idp_questions_on():
    # #58: registry 0.3.0 lets catalog_answers.yaml declare the IdPs as an array. Scenario A has one IdP with two
    # realms on one host and no upstream_issuer, so nothing but the declaration can turn the trait on
    tri = rt.load(ROOT)
    reg = design('A')
    assert rt.read_traits(reg)['multi_idp']['state'] == 'off' and 'idp' in rt.read_traits(reg)['multi_idp']['evidence']
    off = ids(rt.selected(tri, rt.traits(reg)))
    reg['catalog_answers']['idp'] = [{'name': 'keycloak', 'version': '26.8', 'token_types': ['AT']}, {'name': 'entra', 'token_types': ['IDT']}]
    t = rt.read_traits(reg)['multi_idp']
    assert t['state'] == 'on' and 'catalog_answers.yaml の idp が 2 つの IdP の配列（entra・keycloak' in t['evidence']
    assert 'multi_idp' in rt.traits(reg)
    on = ids(rt.selected(tri, rt.traits(reg)))
    assert off < on and 'q-identifier-choice' in on - off
    # one IdP written as an array, the same name twice, and elements without a name are not several IdPs
    for idp in ([{'name': 'keycloak'}], [{'name': 'keycloak'}, {'name': 'keycloak'}], [{'name': 'keycloak'}, {'name': ' '}, {'version': '1'}, 'entra', None],
                {'name': 'keycloak', 'version': '26.8'}, [], None, 'keycloak, entra'):
        reg['catalog_answers']['idp'] = idp
        assert rt.read_traits(reg)['multi_idp']['state'] == 'off', idp
    # the pilot design of scenario B rewritten with the 0.3.0 columns declares five IdPs
    t = rt.read_traits(rt.load_design(os.path.join(ROOT, 'tools/tests/fixtures/claim_lint/pilot-b-migrated')))['multi_idp']
    assert t['state'] == 'on' and '5 つの IdP の配列' in t['evidence']


def test_a_design_that_declares_delegation_but_writes_no_act_still_gets_the_delegation_questions():
    tri = rt.load(ROOT)
    reg = design('pilot-C')
    reg['claims']['claims'] = [c for c in reg['claims']['claims'] if c.get('name') not in ('act', 'may_act')]
    for t in reg['token_types']['token_types']:
        t.pop('max_delegation_depth', None)
    tr = rt.read_traits(reg)
    assert tr['delegation']['state'] == 'on' and 'q-actor' in tr['delegation']['evidence']
    assert 'ap-2-7' in ids(rt.selected(tri, rt.traits(reg)))
    assert ids(rt.selected(tri, rt.traits(reg))) == ids(rt.selected(tri, traits_of('pilot-C')))
    # the author also says "not needed", but still declares "delegation or exchange": the declarations disagree, so the
    # trait cannot be read and the questions stay, with a note (the pilot scenario B is such a design)
    reg['catalog_answers']['questions']['q-actor'] = {'needed': False, 'reason': '代理が無い'}
    tr = rt.read_traits(reg)
    assert tr['delegation']['state'] == 'unknown' and '要確認' in tr['delegation']['evidence'] and 'ap-2-7' in ids(rt.selected(tri, rt.traits(reg)))
    assert rt.read_traits(design('pilot-B'))['delegation']['state'] == 'unknown'
    # no declaration of delegation anywhere: off, and the sheet says which questions are not shown
    reg['catalog_answers']['lite_criteria']['delegation_or_exchange'] = {'answer': False, 'reason': '無い'}
    assert rt.read_traits(reg)['delegation']['state'] == 'off'
    reg['catalog_answers']['lite_criteria']['delegation_or_exchange'] = {'answer': True, 'reason': 'ある'}
    # no answer at all: cannot be read, the questions stay
    del reg['catalog_answers']['questions']['q-actor']
    assert rt.read_traits(reg)['delegation']['state'] == 'unknown' and 'ap-2-7' in ids(rt.selected(tri, rt.traits(reg)))


def test_misread_traits_of_the_first_measurement():
    # #80: three reviews of the first measurement of #12 read "per-operation approval: does not hold" as a misreading
    # (a break-glass approval ID in tctx), and a deferred batch (reservation refunds) was in neither the types nor the hops
    tri = rt.load(ROOT)
    cal = os.path.join(ROOT, 'research', 'template-design', 'calibration')
    b = rt.read_traits(rt.load_design(os.path.join(cal, 'control-b')))
    # a time-window approval is not a per-operation approval: the trait stays off (the list does not grow), but the
    # sheet names the row with the approval ID and the questions to add when it is per operation
    assert b['approval']['state'] == 'off'
    assert 'C-tctx に承認の ID がある' in b['approval']['evidence'] and 'dc-05・q-approval-from-as' in b['approval']['evidence']
    assert '承認の ID' not in rt.read_traits(design('A'))['approval']['evidence']
    reg = design('A')
    reg['claims']['claims'].append({'id': 'C-x', 'name': 'approval_id', 'usage': 'authz'})
    assert rt.read_traits(reg)['approval']['state'] == 'off' and 'C-x に承認の ID' in rt.read_traits(reg)['approval']['evidence']
    # the author's answer to U13 (asynchronous processing that carries the principal) turns long_running on
    a = rt.load_design(os.path.join(cal, 'control-a'))
    assert not any(t.get('long_running') for t in a['token_types']['token_types'])
    tr = rt.read_traits(a)
    assert tr['long_running']['state'] == 'on' and 'U13' in tr['long_running']['evidence']
    assert 'q-long-running' in ids(rt.optional(tri, rt.traits(a)))
    for x in a['catalog_answers']['answers']:
        if x.get('event') == 'U13':
            x['answer'] = '対象外'
    assert rt.read_traits(a)['long_running']['state'] == 'off'
    # neither change moves a priority 1 question: the default lists keep their size
    assert len(rt.selected(tri, rt.traits(rt.load_design(os.path.join(cal, 'control-b'))))) == 18
    by = rt.by_id(tri)
    # A12: set 2 (#82) missed it again (C17, by answering Yes), so #88 added the hint; the priority stays 2
    assert '業務の ID' in by['q-audit-correlation']['hint'] and by['q-audit-correlation']['priority'] == 2
    assert '止める単位' in by['q-revocation-delivery']['hint'] and '既知の限界' in by['q-db-context-writers']['hint']
    assert '作り直されずに内側の受け手に届く' in by['q-idp-diff-absorbed']['hint'] and by['q-idp-diff-absorbed']['priority'] == 2
    for qid, n in (('q-agent-delegation-claims', 'N24'), ('cf-06', 'N25'), ('q-txn-scope-fixed', 'N25')):
        assert n in by[qid]['proposed'] and by[qid]['interim'] == 'B'


def test_misses_of_the_second_measurement():
    """#88: the misses of set 2 (research/template-design/calibration/set2/results.md 4.) are fed back as hints, two
    answering rules and two rule proposals, without moving a priority 1 question."""
    tri = rt.load(ROOT)
    by = rt.by_id(tri)
    for qid, word in (('q-audit-correlation', 'ツール・サービスごと'), ('q-revocation-delivery', '承認者を含む'),
                      ('q-identifier-choice', '1 つずつ'), ('q-original-principal', '理由つきの見送り'),
                      ('q-copies-outlive', '期限を言えない'), ('q-long-running', '承認した人の在籍'),
                      ('q-lint-workaround', '区間の長さではない')):
        assert word in by[qid]['hint'], qid
    assert '同じ鍵で署名するすべての種別' in by_prompt(tri, 'op-key-custody')['hint']
    for qid, n in (('q-hop-lifetime', 'N27'), ('q-key-rotation', 'N26')):
        assert n in by[qid]['proposed'] and by[qid]['interim'] == 'B' and n in tri['proposed_rules']
    for qid in ('q-audit-correlation', 'q-original-principal', 'q-copies-outlive', 'q-long-running'):
        assert by[qid]['priority'] == 2
    cal = os.path.join(ROOT, 'research', 'template-design', 'calibration')
    assert len(rt.selected(tri, rt.traits(rt.load_design(os.path.join(cal, 'control-b'))))) == 18
    sheet, _ = rt.design_sheet(tri, os.path.join(ROOT, 'templates', 'examples', 'scenario-b'), seed='88')
    assert '1 つずつ確かめる。1 つでも満たさなければ No' in sheet and 'No の理由を 1 つ見つけても止めずに' in sheet


def by_prompt(tri, pid):
    return next(p for p in tri['open_prompts'] if p['id'] == pid)


def test_a_trait_that_cannot_be_read_shows_its_questions(tmp_path):
    tri = rt.load(ROOT)
    d = tmp_path / 'design'
    shutil.copytree(os.path.join(ROOT, DESIGNS['pilot-B']), d, ignore=shutil.ignore_patterns('reviews', 'schemas'))
    full = ids(rt.selected(tri, rt.traits(rt.load_design(str(d)))))
    os.remove(d / 'hops.yaml')
    tr = rt.read_traits(rt.load_design(str(d)))
    assert tr['data_layer']['state'] == 'unknown' and tr['approval']['state'] == 'unknown' and 'hops.yaml が無い' in tr['data_layer']['evidence']
    assert tr['exchange']['state'] == 'on' and '書き手の宣言' in tr['exchange']['evidence']
    got = ids(rt.selected(tri, rt.traits(rt.load_design(str(d)))))
    assert full <= got                      # nothing is dropped silently
    sheet, _ = rt.design_sheet(tri, str(d), ROOT)
    assert '[読めない] トークンの値を DB の層まで運ぶ' in sheet and '性質が読めないので出している' in sheet


def test_the_design_sheet_lists_all_traits_with_what_was_read(capsys):
    tri = rt.load(ROOT)
    sheet, tr = rt.design_sheet(tri, os.path.join(ROOT, DESIGNS['pilot-B']), ROOT, seed='pr-74')
    for cid, c in tri['conditions'].items():
        if cid != 'always':
            assert f'] {c["label"]} ― ' in sheet
    assert '[読めない] 委任がある（代理で動く主体がいる） ― 要確認' in sheet and '出さない問い 1：dc-05' in sheet
    assert '手がかり：' in sheet and '見る欄：' in sheet and '70〜110 分' in sheet and '人では測っていない' in sheet
    # the sheet starts with the traits and the questions; how to answer comes last
    heads = [x for x in sheet.split('\n') if x.startswith('## ')]
    assert heads[0].startswith('## 1. 設計の性質') and heads[1].startswith('## 2. クレームの行') and heads[-1].endswith('答え方と、答えないこと')
    # (counted in lines, not characters: the title holds the path of the design, however long)
    assert sheet.split('\n').index(heads[0]) <= 4 and '時間があれば' in heads[-2]
    assert '受け付け（手順の段 0）で、あわせて確かめること：検査（lint）を通すために' in sheet
    # per-row questions: three rows used for authorization, drawn with a seed (the same seed, the same rows)
    line = next(x for x in sheet.split('\n') if x.startswith('答える行'))
    assert '10 行から 3 行。種 pr-74）' in line
    again, _ = rt.design_sheet(tri, os.path.join(ROOT, DESIGNS['pilot-B']), ROOT, seed='pr-74')
    other, _ = rt.design_sheet(tri, os.path.join(ROOT, DESIGNS['pilot-B']), ROOT, seed='another')
    assert again == sheet and next(x for x in other.split('\n') if x.startswith('答える行')) != line
    # without a seed: not a fixed string; made from the registry and the date, and printed
    auto, _ = rt.design_sheet(tri, os.path.join(ROOT, DESIGNS['pilot-B']), ROOT)
    seed = rt.default_seed(design('pilot-B'))
    assert re.match(r'^[0-9a-f]{8}-\d{4}-\d{2}-\d{2}$', seed) and f'種 {seed}：--seed が無いので' in auto
    assert rt.default_seed(design('pilot-C')) != seed
    # one row of the organisation's own authorization claims is always in the sample, whatever the seed
    for key in DESIGNS:
        reg = design(key)
        claims = {c['id']: c for c in reg['claims']['claims']}
        own_rows = {i for i, c in claims.items() if c.get('decision') != '却下' and c.get('namespace') and c.get('usage') == 'authz'}
        for sd in ('1', '2', '3', 'pr-74', 'x'):
            rows, total, own = rt.row_sample(tri, reg, sd)
            assert len(rows) == min(3, total) == len(set(rows)) and all(claims[r].get('usage') in ('authz', 'identifier') for r in rows)
            assert (own in own_rows and own == rows[0]) if own_rows else own is None, (key, sd)
    assert rt.row_sample(tri, design('pilot-B'), 'pr-74')[1] == 10
    # a directory that does not exist, or one without the registry, is an error, not a short list
    assert rt.main(['--root', ROOT, '--design', os.path.join(ROOT, 'no-such-design')]) == 2
    assert rt.main(['--root', ROOT, '--design', os.path.join(ROOT, 'templates', 'review')]) == 2
    err = capsys.readouterr().err
    assert '設計書のディレクトリが無い' in err and 'claims.yaml' in err
    with pytest.raises(rt.DesignError):
        rt.load_design(os.path.join(ROOT, 'no-such-design'))


def test_short_list_differs_by_design_and_stays_short():
    tri = rt.load(ROOT)
    n = {k: rt.load_of(tri, traits_of(k), rt.on_traits(design(k))) for k in DESIGNS}
    # by default: the priority 1 questions of the design (10-17) and three open prompts
    assert {k: (v['questions'], v['prompts']) for k, v in n.items()} == {'A': (11, 3), 'B': (18, 3), 'pilot-B': (16, 3), 'pilot-C': (15, 3)}
    assert {k: (v['optional_questions'], v['more_prompts']) for k, v in n.items()} == {'A': (7, 2), 'B': (9, 3), 'pilot-B': (8, 2), 'pilot-C': (5, 3)}
    lo, hi = tri['budget']['questions']
    for k, v in n.items():
        assert lo <= v['questions'] <= hi, k
        assert v['ask_sentences'] == v['items']          # one sentence per item
        assert v['ask_chars'] < 800
    for k in DESIGNS:
        qs = rt.selected(tri, traits_of(k))
        assert all(q['class'] == 'C' and q['priority'] == 1 and not q.get('merged_into') for q in qs)
        assert all(q['priority'] == 2 for q in rt.optional(tri, traits_of(k))) and not ids(qs) & ids(rt.optional(tri, traits_of(k)))
    # the open prompts that fit the design come first; the others are "more"
    dp = {k: [p['id'] for p in rt.default_prompts(tri, traits_of(k), rt.on_traits(design(k)))] for k in DESIGNS}
    assert dp['pilot-C'] == ['op-proof-holder', 'op-one-time', 'op-clock'] and dp['B'] == ['op-proof-holder', 'op-source-change', 'op-one-time']
    assert dp['A'] == ['op-source-change', 'op-one-time', 'op-requirement-words']
    # a trait that cannot be read does not rank a prompt up: the pilot scenario B has exchange (holds) and delegation
    # (cannot be read), so it gets the key custody prompt, not the one preferred for approval and delegation
    assert rt.read_traits(design('pilot-B'))['delegation']['state'] == 'unknown' and dp['pilot-B'] == ['op-source-change', 'op-clock', 'op-key-custody']
    assert [p['id'] for p in rt.default_prompts(tri, traits_of('pilot-B'))] == ['op-source-change', 'op-one-time', 'op-clock']   # if it counted
    # the question no other priority 1 question covers is on the default list; the lint work-around is step 0 work
    assert 'q-step-up-path-coverage' in ids(rt.selected(tri, traits_of('A'))) and rt.by_id(tri)['q-lint-workaround'].get('step') == 0
    assert 'q-lint-workaround' not in ids(rt.selected(tri, traits_of('A'))) | ids(rt.optional(tri, traits_of('A')))
    assert '`q-lint-workaround`' in open(os.path.join(ROOT, 'templates', 'review', 'procedure.md'), encoding='utf-8').read()
    assert len(rt.prompts(tri, traits_of('pilot-C'))) == 6
    # machine-decidable questions without a rule are back on the list of the designs they matter for
    assert {'q-single-aud-resource', 'q-agent-short-lived-no-rt', 'dc-05'} <= ids(rt.selected(tri, traits_of('pilot-C')))
    assert {'q-identifier-choice', 'q-single-aud-resource', 'q-agent-short-lived-no-rt'} <= ids(rt.selected(tri, traits_of('pilot-B')))
    assert not {'q-identifier-choice', 'q-single-aud-resource', 'q-agent-short-lived-no-rt', 'dc-05'} & ids(rt.selected(tri, traits_of('A')))
    # a lint warning brings the question of show_on_lint in, whatever its priority
    with_warn = rt.selected(tri, traits_of('pilot-C'), warn_rules={'L69'})
    assert 'q-role-explosion' in ids(with_warn) and len(with_warn) == n['pilot-C']['questions'] + 1


def test_the_editor_data_start_with_the_short_list():
    # the default path of the editor's checklist, without a browser: docs/claims/data/review.js is what the build makes
    # from triage.yaml, its default filter is the short list, and the selection rule of review.js (class C, a default
    # priority, a condition that holds or cannot be read; or a warned rule of show_on_lint) gives, on these data, the
    # list of tools/review_triage.py for the four designs
    tri = rt.load(ROOT)
    text = open(os.path.join(ROOT, 'docs', 'claims', 'data', 'review.js'), encoding='utf-8').read()
    line = next(x for x in text.splitlines() if x.startswith('window.CLAIMS_VIEWER_DATA["review"] = '))
    data = json.loads(line.split(' = ', 1)[1].rstrip(';'))
    assert data == json.loads(json.dumps(bcv.review_bundle()))
    ck = data['checklist']
    assert ck['default'] == {'triage': ['short']} and ck['short']['priorities'] == [1] and ck['short']['optional_priorities'] == [2] and ck['short']['max_prompts'] == 3
    assert [c['id'] for c in ck['conditions']] == list(tri['conditions'])
    assert [p['id'] for p in ck['open_prompts']] == [p['id'] for p in tri['open_prompts']] and all(p['hint'] for p in ck['open_prompts'])
    by = rt.by_id(tri)
    for q in data['questions']:
        assert q['triage'] == by[q['id']]['class'] and q['triage_note']
        if q['triage'] == 'C':
            assert {'priority', 'unit', 'show_when', 'show_on_lint', 'ask', 'hint'} <= set(q) and '。' not in q['ask']
        else:
            assert not {'priority', 'ask', 'show_when'} & set(q)
    for k in DESIGNS:
        have = traits_of(k)
        shown = [q['id'] for q in data['questions'] if q['triage'] == 'C' and q['priority'] in ck['short']['priorities'] and set(q['show_when']) & have]
        assert set(shown) == ids(rt.selected(tri, have)), k
        more = [q['id'] for q in data['questions'] if q['triage'] == 'C' and q['priority'] in ck['short']['optional_priorities'] and set(q['show_when']) & have]
        assert set(more) == ids(rt.optional(tri, have)), k
        fit = [p for p in ck['open_prompts'] if set(p['show_when']) & have]
        on = rt.on_traits(design(k))
        ranked = sorted(fit, key=lambda p: 0 if set(p['show_when']) - {'always'} & have else 1 if set(p['prefer_when']) & on else 2)
        assert [p['id'] for p in ranked[:ck['short']['max_prompts']]] == [p['id'] for p in rt.default_prompts(tri, have, on)], k
    # review.js reads the traits with the same rules (the browser test compares the results; here: the function is the
    # one the checklist uses, and it keeps unknown traits)
    js = open(os.path.join(ROOT, 'docs', 'claims', 'review.js'), encoding='utf-8').read()
    assert "read[c.id] === 'on' ? true : read[c.id] === 'off' ? false : null" in js and "declared(asked, 'q-actor', 'needed')" in js and 'noHops' in js
    assert 'short.optional_priorities' in js and '.max_prompts' in js and "(p.prefer_when || []).some((c) => tr[c] === true)" in js


# ---------------------------------------------------------------- the pilot findings
def test_pilot_majors_are_each_mapped_once_and_the_totals_add_up():
    tri = rt.load(ROOT)
    cov = yaml.safe_load(open(os.path.join(ROOT, 'research', 'pilot', 'triage-coverage.yaml'), encoding='utf-8'))
    re_ = yaml.safe_load(open(os.path.join(ROOT, 'research', 'pilot', 'reattribution.yaml'), encoding='utf-8'))
    of = {'B-R1': 'pilot-B', 'B-R2': 'pilot-B', 'C-R1': 'pilot-C', 'C-R2': 'pilot-C'}
    by = rt.by_id(tri)
    kinds = {}
    later = []
    human = {'total': 0, 'direct': 0, 'fitted': 0}
    for review, findings in re_['reviews'].items():
        majors = {f['id']: f for f in findings if f['severity'] == 'Major'}
        assert set(cov['majors'][review]) == set(majors), review
        have = traits_of(of[review])
        shown = ids(rt.selected(tri, have)) | {p['id'] for p in rt.prompts(tri, have)}
        default = ids(rt.selected(tri, have)) | {p['id'] for p in rt.default_prompts(tri, have, rt.on_traits(design(of[review])))}
        for fid, m in cov['majors'][review].items():
            assert m['class'] == majors[fid]['triage'][0], (review, fid)   # the class of the re-attribution
            kinds[m['kind']] = kinds.get(m['kind'], 0) + 1
            if m['kind'] in ('direct', 'fitted', 'returned'):
                assert m['by'] in shown, (review, fid, m['by'])
                if m['by'] not in default:   # an open prompt that is not among the three shown by default for this design
                    later.append(f'{review} {fid}')
            if m['kind'] in ('direct', 'fitted'):
                assert m['class'] == 'C'
            if m['kind'] in ('direct', 'returned'):   # the question was cited by the re-attribution
                assert m['by'] in majors[fid]['cited_id'], (review, fid)
            if m['kind'] == 'returned':
                assert m['class'] == 'A' and by[m['by']].get('until_rule')
            if m['kind'] == 'machine':
                assert rc.resolve(ROOT, 'lint:' + m['by'], {}) is None
            if m['kind'] == 'pending':
                assert m['class'] == 'A' and any(m['by'] in (q.get('proposed') or []) for q in tri['questions'])
            if m['kind'] == 'author':
                assert by[m['by']]['class'] == 'B'
            if m['kind'] == 'expert':
                assert any(q['class'] == 'D' and q['escalation'] == m['by'] for q in tri['questions'])
            if m['class'] == 'C':
                human['total'] += 1
                human[m['kind']] += 1
    t = cov['totals']
    assert sum(kinds.values()) == t['major'] == 37
    assert kinds == t['by_kind'] and human == t['human_judgement']
    assert kinds['direct'] + kinds['returned'] + kinds['fitted'] == t['prompted_by_short_list_and_prompts'] == 29
    assert later == t['only_if_time_remains'] == ['B-R1 T4'] and 29 - len(later) == t['prompted_by_default_list'] == 28
    # the numbers the evidence states are these numbers, with what they do not show
    doc = open(os.path.join(ROOT, 'research', 'template-design', 'triage-evidence.md'), encoding='utf-8').read()
    assert '29／37（78%）' in doc and '28／37（76%）' in doc and '| 計 | 37 | 12 | 5 | 12 | 3 | 1 | 1 | 3 |' in doc
    assert '前からあったのは問いの ID だけ' in doc and '厳しく数えるなら 11 件' in doc
    assert 'Major として指摘にしたのは 7' in doc and '人では測っていません' in doc
    assert '過学習' in doc and 'LLM による試行。人による検証ではない' in doc


def test_open_prompts_come_from_findings_outside_the_questions():
    tri = rt.load(ROOT)
    re_ = yaml.safe_load(open(os.path.join(ROOT, 'research', 'pilot', 'reattribution.yaml'), encoding='utf-8'))
    known = {f'{r} {f["id"]}' for r, fs in re_['reviews'].items() for f in fs}
    for p in tri['open_prompts']:
        assert p['from'] and set(p['from']) <= known, p['id']


def test_times_are_stated_as_unmeasured_estimates_of_the_whole_procedure():
    tri = rt.load(ROOT)
    assert tri['budget']['whole_procedure_minutes'] == [70, 110]
    # the total is the sum of the per-step estimates of procedure.md (steps 0-6)
    assert (10 + 10 + 5 + 20 + 10 + 10 + 5, 10 + 10 + 10 + 40 + 15 + 20 + 5) == (70, 110)
    short = open(os.path.join(ROOT, rt.SHORT), encoding='utf-8').read()
    proc = open(os.path.join(ROOT, 'templates', 'review', 'procedure.md'), encoding='utf-8').read()
    for text in (short, proc):
        assert '70〜110 分' in text and '60〜100' not in text and '人では測っていません' in text
    assert '別に取ります' not in short
