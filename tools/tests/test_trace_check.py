# -*- coding: utf-8 -*-
"""Tests for tools/trace_check.py.  Run: python -m pytest tools/tests"""
import copy, json, os, sys

import pytest
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import trace_check as tc  # noqa: E402

SLIDES = [
    {'n': 1, 'id': 'p00-title', 'part': 'p00', 'title': 't'},
    {'n': 2, 'id': 'p01-validate', 'part': 'p01', 'title': 'v'},
    {'n': 3, 'id': 'p01-background', 'part': 'p01', 'title': 'b'},
]
ITEMS = {'items': [
    {'ref': 'template:00_core#hop-table', 'issue': '#4', 'origin': 'issue', 'title': 'hop table'},
    {'ref': 'lint:L16', 'issue': '#6', 'origin': 'issue', 'title': 'narrow downstream'},
    {'ref': 'render:payload-schema', 'issue': '#19', 'origin': 'issue', 'title': 'schema'},
    {'ref': 'review:contrasts/four-lifetimes', 'issue': '#5', 'origin': 'proposed', 'title': 'contrast'},
    {'ref': 'deferred:idp-entra', 'issue': '#21', 'origin': 'issue', 'title': 'entra'},
    {'ref': 'none:out-of-scope', 'issue': '#22', 'origin': 'issue', 'title': 'none'},
]}
REQS = {
    'classification': [
        {'slide': 'slide:p00-title', 'kind': 'structural'},
        {'slide': 'slide:p01-validate', 'kind': 'design-decision'},
        {'slide': 'slide:p01-background', 'kind': 'knowledge'},
    ],
    'requirements': [
        {'id': 'p01-validate.R1', 'slide': 'slide:p01-validate', 'text': '下流ほど絞る', 'owner_issue': '#4',
         'planned_items': ['template:00_core#hop-table', 'lint:L16'], 'status': '未着手'},
        {'id': 'p01-validate.R2', 'slide': 'slide:p01-validate', 'text': 'Entra の上限', 'owner_issue': '#21',
         'planned_items': ['deferred:idp-entra'], 'status': '後回し'},
        {'id': 'p01-validate.R3', 'slide': 'slide:p01-validate', 'text': '組織の判断', 'owner_issue': '#22',
         'planned_items': ['none:out-of-scope'], 'status': '扱わない',
         'assumption': '起きない', 'breaks_when': '起きたとき'},
    ],
    'teaching': [{'slide': 'slide:p01-background', 'use': ['review:contrasts/four-lifetimes'], 'note': 'x'}],
}


def summary_for(reqs):
    kinds = [c['kind'] for c in reqs['classification']]
    st = [r.get('status') for r in reqs['requirements']]
    s = {'design_decision_slides': kinds.count('design-decision'), 'knowledge_slides': kinds.count('knowledge'),
         'structural_slides': kinds.count('structural'), 'requirements': len(st)}
    s.update({k: st.count(k) for k in tc.STATUSES})
    return s


def build(root, slides=None, items=None, reqs=None, fix_summary=True, write_new_items=True, files=None):
    slides = copy.deepcopy(SLIDES if slides is None else slides)
    items = copy.deepcopy(ITEMS if items is None else items)
    reqs = copy.deepcopy(REQS if reqs is None else reqs)
    if fix_summary:
        reqs['summary'] = summary_for(reqs)
    os.makedirs(os.path.join(root, 'deck'), exist_ok=True)
    os.makedirs(os.path.join(root, 'templates', 'trace'), exist_ok=True)
    with open(os.path.join(root, 'deck', 'slide_ids.json'), 'w', encoding='utf-8') as f:
        json.dump(slides, f)
    with open(os.path.join(root, tc.ITEMS_FILE), 'w', encoding='utf-8') as f:
        yaml.safe_dump(items, f, allow_unicode=True, sort_keys=False)
    with open(os.path.join(root, tc.REQ_FILE), 'w', encoding='utf-8') as f:
        yaml.safe_dump(reqs, f, allow_unicode=True, sort_keys=False)
    for rel, text in (files or {}).items():
        os.makedirs(os.path.dirname(os.path.join(root, rel)), exist_ok=True)
        with open(os.path.join(root, rel), 'w', encoding='utf-8') as f:
            f.write(text)
    if write_new_items:
        tc.main(['--root', str(root), '--write-new-items'])
    return str(root)


def run(root, capsys):
    capsys.readouterr()
    code = tc.main(['--root', root])
    return code, capsys.readouterr().out


def with_req(change, index=0):
    reqs = copy.deepcopy(REQS)
    change(reqs['requirements'][index])
    return reqs


# ------------------------------------------------------------------ pass
def test_fixture_passes(tmp_path, capsys):
    code, out = run(build(tmp_path), capsys)
    assert code == 0, out
    assert 'by status: 未着手 1, 実装済み 0, 後回し 1, 扱わない 1' in out
    assert 'by owner issue: #4 1, #21 1, #22 1' in out
    assert '扱わない: 1 / 3 (33.3%)' in out


def test_repository_trace_passes(capsys):
    code, out = run(tc.DEFAULT_ROOT, capsys)
    assert code == 0, out


# ------------------------------------------------------------------ (a) slide set
def test_new_slide_without_trace_fails(tmp_path, capsys):
    slides = SLIDES + [{'n': 4, 'id': 'p02-new', 'part': 'p02', 'title': 'n'}]
    code, out = run(build(tmp_path, slides=slides), capsys)
    assert code == 1 and 'slide:p02-new (slide 4) is not classified' in out


def test_removed_slide_fails(tmp_path, capsys):
    code, out = run(build(tmp_path, slides=SLIDES[:2]), capsys)
    assert code == 1 and 'unknown slide:p01-background' in out


def test_duplicate_classification_fails(tmp_path, capsys):
    reqs = copy.deepcopy(REQS)
    reqs['classification'].append({'slide': 'slide:p00-title', 'kind': 'knowledge'})
    code, out = run(build(tmp_path, reqs=reqs), capsys)
    assert code == 1 and 'classified more than once' in out


def test_bad_kind_fails(tmp_path, capsys):
    reqs = copy.deepcopy(REQS)
    reqs['classification'][0]['kind'] = 'divider'
    code, out = run(build(tmp_path, reqs=reqs, fix_summary=False), capsys)
    assert code == 1 and 'kind must be one of' in out


# ------------------------------------------------------------------ (b) every design slide decomposed
def test_design_slide_without_requirement_fails(tmp_path, capsys):
    reqs = copy.deepcopy(REQS)
    reqs['requirements'] = []
    reqs['teaching'] = []
    items = {'items': [i for i in ITEMS['items'] if i['origin'] == 'issue']}
    code, out = run(build(tmp_path, reqs=reqs, items=items), capsys)
    assert code == 1 and 'design-decision slide:p01-validate has no requirement' in out


def test_requirement_on_knowledge_slide_fails(tmp_path, capsys):
    reqs = copy.deepcopy(REQS)
    r = copy.deepcopy(reqs['requirements'][0])
    r.update(id='p01-background.R1', slide='slide:p01-background')
    reqs['requirements'].append(r)
    code, out = run(build(tmp_path, reqs=reqs), capsys)
    assert code == 1 and 'classified knowledge, not design-decision' in out


# ------------------------------------------------------------------ (c) fields
@pytest.mark.parametrize('change, message', [
    (lambda r: r.pop('owner_issue'), 'owner_issue must look like'),
    (lambda r: r.update(planned_items=[]), 'needs at least one planned item'),
    (lambda r: r.update(planned_items=['template:00_core#hop table']), 'malformed planned item'),
    (lambda r: r.update(planned_items=['lint:L99']), 'lint:L99 is not in'),
    (lambda r: r.update(planned_items=['widget:x']), "unknown kind 'widget'"),
    (lambda r: r.update(status='done'), 'status must be one of'),
    (lambda r: r.update(text=''), 'text is empty'),
    (lambda r: r.update(id='p01-validate-R1'), 'id must be <slide-id>.R<n>'),
    (lambda r: r.update(slide='slide:p00-title'), 'slide must be slide:p01-validate'),
    (lambda r: r.update(owner_issue='#8'), 'owner_issue #8 is not the issue of any planned item'),
    (lambda r: r.update(break_condition='x'), "unknown field 'break_condition'"),
    (lambda r: r.update(status='後回し'), '後回し needs owner_issue in'),
])
def test_bad_requirement_fails(tmp_path, capsys, change, message):
    code, out = run(build(tmp_path, reqs=with_req(change)), capsys)
    assert code == 1 and message in out, out


def test_out_of_scope_needs_assumption_and_breaks_when(tmp_path, capsys):
    code, out = run(build(tmp_path, reqs=with_req(lambda r: r.pop('breaks_when'), 2)), capsys)
    assert code == 1 and '扱わない needs breaks_when' in out


def test_none_item_only_for_out_of_scope(tmp_path, capsys):
    def change(r):
        r.update(status='未着手'); r.pop('assumption'); r.pop('breaks_when')
    code, out = run(build(tmp_path, reqs=with_req(change, 2)), capsys)
    assert code == 1 and 'none:out-of-scope is only for status 扱わない' in out


def test_deferred_owner_must_be_deferred_status(tmp_path, capsys):
    code, out = run(build(tmp_path, reqs=with_req(lambda r: r.update(status='未着手'), 1)), capsys)
    assert code == 1 and 'is a deferred issue' in out


# ------------------------------------------------------------------ (d) 実装済み resolves
def test_implemented_without_artifact_fails(tmp_path, capsys):
    code, out = run(build(tmp_path, reqs=with_req(lambda r: r.update(status='実装済み'))), capsys)
    assert code == 1
    assert 'templates' in out and '00_core.md does not exist' in out
    assert 'tools' in out and 'RULES.md does not exist' in out


def test_implemented_with_artifacts_passes(tmp_path, capsys):
    files = {'templates/00_core.md': '## ホップごとの表 <a id="hop-table"></a>\n',
             'tools/claim-lint/RULES.md': '| ID | 内容 |\n|---|---|\n| L16 | 下流ほど絞る |\n'}
    root = build(tmp_path, reqs=with_req(lambda r: r.update(status='実装済み')), files=files)
    code, out = run(root, capsys)
    assert code == 0, out


def test_implemented_wrong_anchor_fails(tmp_path, capsys):
    files = {'templates/00_core.md': '<a id="lifecycle"></a>\n',
             'tools/claim-lint/RULES.md': '| L16 | x |\n'}
    code, out = run(build(tmp_path, reqs=with_req(lambda r: r.update(status='実装済み')), files=files), capsys)
    assert code == 1 and 'has no anchor <a id="hop-table"></a>' in out


def test_implemented_unbuilt_kind_fails(tmp_path, capsys):
    def change(r):
        r.update(status='実装済み', owner_issue='#19', planned_items=['render:payload-schema'])
    code, out = run(build(tmp_path, reqs=with_req(change)), capsys)
    assert code == 1 and 'kind render has no artifact to resolve yet' in out


def test_registry_resolver(tmp_path):
    rel = 'templates/registry/claims.schema.json'
    os.makedirs(os.path.join(tmp_path, 'templates', 'registry'))
    with open(os.path.join(tmp_path, rel), 'w') as f:
        json.dump({'$defs': {'claim': {'properties': {'volatility': {}, 'on_revoke': {}}}}}, f)
    assert tc.resolve_registry(str(tmp_path), 'claims', 'volatility') is None
    assert 'no property' in tc.resolve_registry(str(tmp_path), 'claims', 'provenance')
    assert 'does not exist' in tc.resolve_registry(str(tmp_path), 'hops', 'aud')


# ------------------------------------------------------------------ (e) summary, generated list, teaching
def test_stale_summary_fails(tmp_path, capsys):
    reqs = copy.deepcopy(REQS)
    reqs['summary'] = dict(summary_for(reqs), requirements=99)
    code, out = run(build(tmp_path, reqs=reqs, fix_summary=False), capsys)
    assert code == 1 and 'summary block is stale' in out


def test_stale_new_items_fails(tmp_path, capsys):
    code, out = run(build(tmp_path, write_new_items=False), capsys)
    assert code == 1 and 'new_items.md: stale' in out


def test_unused_proposed_item_fails(tmp_path, capsys):
    items = copy.deepcopy(ITEMS)
    items['items'].append({'ref': 'lint:L19', 'issue': '#6', 'origin': 'proposed', 'title': 'x'})
    code, out = run(build(tmp_path, items=items), capsys)
    assert code == 1 and 'proposed item lint:L19 is used by no requirement' in out


def test_teaching_on_design_slide_fails(tmp_path, capsys):
    reqs = copy.deepcopy(REQS)
    reqs['teaching'][0]['slide'] = 'slide:p01-validate'
    code, out = run(build(tmp_path, reqs=reqs), capsys)
    assert code == 1 and 'is not classified knowledge' in out


@pytest.mark.parametrize('ref, ok', [
    ('registry:claims#volatility', True), ('registry:claims', False), ('registry:widgets#x', False),
    ('lint:L1a', True), ('lint:R3b', True), ('lint:L5#x', False), ('lint:NEW-foo', False),
    ('template:modules/M_token_validation#jwks-cache', True), ('template:../x', False),
    ('test:negative_tests#alg-none', True), ('test:other#x', False),
    ('deferred:idp-entra', True), ('deferred:Idp', False), ('none:out-of-scope', True), ('none:other', False),
])
def test_parse_ref(ref, ok):
    if ok:
        tc.parse_ref(ref)
    else:
        with pytest.raises(ValueError):
            tc.parse_ref(ref)
