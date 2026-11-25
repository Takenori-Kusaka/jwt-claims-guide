# -*- coding: utf-8 -*-
"""tools/review_triage.py (#56): templates/review/triage.yaml classifies every question of perspectives.md, the lint
rules it cites exist, the generated files match, the short list of a design follows its traits, and the record of what
the short list would have prompted among the Major findings of the pilot (#9) adds up."""
import os
import shutil
import sys

import pytest
import yaml

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import review_check as rc  # noqa: E402
import review_triage as rt  # noqa: E402

COPY = ['templates', 'deck/slide_ids.json', 'tools/template_sources.yaml', 'tools/claim_lint/RULES.md',
        '.github/PULL_REQUEST_TEMPLATE/design_doc.md', 'research/template-design/triage-evidence.md']
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


def traits_of(key):
    return rt.traits(rt.load_design(os.path.join(ROOT, DESIGNS[key])))


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
    ids = [q['id'] for q in tri['questions']]
    assert sorted(ids) == sorted(q['id'] for q in questions) and len(ids) == len(set(ids)) == 168
    assert all(q['class'] in 'ABCD' and q['why'].strip() for q in tri['questions'])
    c = rt.counts(tri)
    assert (c['A'], c['B'], c['C'], c['D']) == (86, 35, 43, 4)
    assert c['A_with_rule'] + c['A_partial_rule'] + c['A_without_rule'] == c['A']
    assert c['C_priority_1'] + c['C_priority_2'] + c['C_priority_3'] == c['C']
    assert 5 <= c['open_prompts'] <= 8


def test_t1_a_question_without_a_class_and_an_unknown_question(root):
    edit(root, TRIAGE, '  - {id: dc-01, class: A, lint: [L5], why: "usage と volatility と寿命の比較は、台帳と目録の値の計算で決まる"}\n', '')
    assert rules(root) == ['T1']
    edit(root, TRIAGE, '  - {id: dc-02,', '  - {id: dc-99,')
    assert rules(root) == ['T1']


def test_t3_lint_rules_must_exist_and_proposals_must_be_known(root):
    edit(root, TRIAGE, '- {id: dc-09, class: A, lint: [L3],', '- {id: dc-09, class: A, lint: [L24],')   # planned, not implemented
    assert rules(root) == ['T3']


def test_t3_an_implemented_rule_is_not_a_proposal(root):
    edit(root, TRIAGE, 'lint: [], proposed: [L36], interim: B, why: "shape の値', 'lint: [], proposed: [L5], interim: B, why: "shape の値')
    assert rules(root) == ['T3']


def test_t3_a_question_no_rule_decides_goes_to_the_author_meanwhile(root):
    edit(root, TRIAGE, 'proposed: [L56], interim: B,', 'proposed: [L56],')
    assert rules(root) == ['T3']


def test_t4_t5_human_and_expert_questions(root):
    edit(root, TRIAGE, '{id: q-outside-catalog, class: C, priority: 1, unit: design, show_when: [always],',
         '{id: q-outside-catalog, class: C, priority: 1, unit: design, show_when: [no_such_condition],')
    assert rules(root) == ['T4']
    edit(root, TRIAGE, 'show_when: [no_such_condition],', 'show_when: [always],')
    edit(root, TRIAGE, 'escalation: custom-crypto', 'escalation: no-such-criterion')
    assert rules(root) == ['T5']


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
    # a question that an existing rule decides says so, and tells the reviewer not to answer
    a = next(q for q in qs if q['id'] == 'dc-01')
    assert 'lint の `lint:L5` が確かめる（レビュアーは答えない）' in a['fields']['区分']


def test_author_self_check_holds_class_b_and_the_questions_waiting_for_a_rule():
    tri = rt.load(ROOT)
    text = open(os.path.join(ROOT, rt.PR_TEMPLATE), encoding='utf-8').read()
    want = {q['id'] for q in tri['questions'] if q['class'] == 'B' or q.get('interim') == 'B'}
    import re
    got = set(re.findall(r'^- \[ \] `([a-z0-9-]+)`', text, re.M))
    assert got == want and len(got) == 70
    assert not any(q['id'] in got for q in tri['questions'] if q['class'] in 'CD')


def test_traits_are_read_from_the_registry():
    a, b, pb, pc = (traits_of(k) for k in ('A', 'B', 'pilot-B', 'pilot-C'))
    assert 'multitenant' in a and 'delegation' not in a and 'exchange' not in a
    assert {'delegation', 'exchange', 'approval', 'sender_constrained', 'multi_idp'} <= b and 'multitenant' not in b
    assert {'multi_idp', 'exchange', 'data_layer', 'sender_declined'} <= pb and 'delegation' not in pb
    assert pc == {'always', 'pii', 'exchange', 'delegation', 'approval', 'sender_constrained'}
    # the author's answer decides multitenant: scenario C binds its tokens to the issuer but is one organisation
    reg = rt.load_design(os.path.join(ROOT, DESIGNS['pilot-C']))
    assert any(t.get('tenant_binding') for t in reg['token_types']['token_types'])
    del reg['catalog_answers']['lite_criteria']['multitenant']
    assert 'multitenant' in rt.traits(reg)


def test_short_list_differs_by_design_and_stays_short():
    tri = rt.load(ROOT)
    n = {k: len(rt.selected(tri, traits_of(k))) for k in DESIGNS}
    assert n == {'A': 25, 'B': 29, 'pilot-B': 23, 'pilot-C': 19}
    assert n['A'] != n['B']
    for k in DESIGNS:
        qs = rt.selected(tri, traits_of(k))
        assert all(q['class'] == 'C' and q['priority'] in (1, 2) for q in qs)
        assert [q['priority'] for q in qs] == sorted(q['priority'] for q in qs)
    # a lint warning brings the question of show_on_lint in, whatever its priority
    with_warn = rt.selected(tri, traits_of('pilot-C'), warn_rules={'L69'})
    assert 'q-role-explosion' in {q['id'] for q in with_warn} and len(with_warn) == n['pilot-C'] + 1
    assert len(rt.prompts(tri, traits_of('pilot-C'))) == 8 and len(rt.prompts(tri, traits_of('A'))) == 6


def test_pilot_majors_are_each_mapped_once_and_the_totals_add_up():
    tri = rt.load(ROOT)
    cov = yaml.safe_load(open(os.path.join(ROOT, 'research', 'pilot', 'triage-coverage.yaml'), encoding='utf-8'))
    re_ = yaml.safe_load(open(os.path.join(ROOT, 'research', 'pilot', 'reattribution.yaml'), encoding='utf-8'))
    design = {'B-R1': 'pilot-B', 'B-R2': 'pilot-B', 'C-R1': 'pilot-C', 'C-R2': 'pilot-C'}
    by = rt.by_id(tri)
    kinds = {}
    human = {'total': 0, 'direct': 0, 'fitted': 0}
    for review, findings in re_['reviews'].items():
        majors = {f['id']: f for f in findings if f['severity'] == 'Major'}
        assert set(cov['majors'][review]) == set(majors), review
        have = traits_of(design[review])
        shown = {q['id'] for q in rt.selected(tri, have)} | {p['id'] for p in rt.prompts(tri, have)}
        for fid, m in cov['majors'][review].items():
            assert m['class'] == majors[fid]['triage'][0], (review, fid)   # the class of the re-attribution
            kinds[m['kind']] = kinds.get(m['kind'], 0) + 1
            if m['kind'] in ('direct', 'fitted'):
                assert m['class'] == 'C' and m['by'] in shown, (review, fid, m['by'])
            if m['kind'] == 'direct':   # the question was cited by the re-attribution
                assert m['by'] in majors[fid]['cited_id'], (review, fid)
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
    assert kinds['direct'] + kinds['fitted'] == t['prompted_by_short_list_and_prompts'] == 24
    # the numbers the evidence states are these numbers
    doc = open(os.path.join(ROOT, 'research', 'template-design', 'triage-evidence.md'), encoding='utf-8').read()
    assert '24／37（65%）' in doc and '直接 12（32%）、作り込み 12（32%）' in doc and '直接 12（50%）、作り込み 12（50%）' in doc
    assert '| 計 | 37 | 12 | 12 | 3 | 6 | 1 | 3 |' in doc
    assert '過学習' in doc and 'LLM による試行。人による検証ではない' in doc


def test_open_prompts_come_from_findings_outside_the_questions():
    tri = rt.load(ROOT)
    re_ = yaml.safe_load(open(os.path.join(ROOT, 'research', 'pilot', 'reattribution.yaml'), encoding='utf-8'))
    known = {f'{r} {f["id"]}' for r, fs in re_['reviews'].items() for f in fs}
    for p in tri['open_prompts']:
        assert p['from'] and set(p['from']) <= known, p['id']
