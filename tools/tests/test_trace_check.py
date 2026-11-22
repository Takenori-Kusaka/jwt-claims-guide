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
WEB = [
    {'n': 1, 'id': 'p00-title', 'title': 't', 'text': 'title', 'notes': ''},
    {'n': 2, 'id': 'p01-validate', 'title': 'v', 'text': '下流ほど絞る', 'notes': 'ノート'},
    {'n': 3, 'id': 'p01-background', 'title': 'b', 'text': '背景', 'notes': ''},
]
ITEMS = {'items': [
    {'ref': 'template:00_core#hop-table', 'issue': '#4', 'origin': 'issue', 'title': 'hop table'},
    {'ref': 'lint:L16', 'issue': '#6', 'origin': 'issue', 'title': 'narrow downstream'},
    {'ref': 'review:contrasts/signed-vs-enforced', 'issue': '#5', 'origin': 'issue', 'title': 'no anchor'},
    {'ref': 'registry:claims#volatility', 'issue': '#3', 'origin': 'issue', 'title': 'volatility'},
    {'ref': 'render:payload-schema', 'issue': '#19', 'origin': 'issue', 'title': 'schema'},
    {'ref': 'review:contrasts/four-lifetimes', 'issue': '#5', 'origin': 'proposed', 'title': 'contrast'},
    {'ref': 'deferred:idp-entra', 'issue': '#21', 'origin': 'issue', 'title': 'entra'},
    {'ref': 'none:out-of-scope', 'issue': '#22', 'origin': 'issue', 'title': 'none'},
]}
ASSUMPTION = '組織の運営で決まり、設計書の欄にしなくても抜けない'
BREAKS = 'レビュー後の欠陥の記録に、この判断の抜けが原因の事例が出たとき'
REQS = {
    'classification': [
        {'slide': 'slide:p00-title', 'kind': 'structural'},
        {'slide': 'slide:p01-validate', 'kind': 'design-decision'},
        {'slide': 'slide:p01-background', 'kind': 'knowledge'},
    ],
    'requirements': [
        {'id': 'p01-validate.R1', 'slide': 'slide:p01-validate', 'text': '下流ほど絞る', 'owner_issue': '#4',
         'planned_items': ['template:00_core#hop-table', 'lint:L16'], 'status': '未着手', 'tier': 'core'},
        {'id': 'p01-validate.R2', 'slide': 'slide:p01-validate', 'text': 'Entra の上限', 'owner_issue': '#21',
         'planned_items': ['deferred:idp-entra'], 'status': '後回し', 'tier': 'full'},
        {'id': 'p01-validate.R3', 'slide': 'slide:p01-validate', 'text': '組織の判断', 'owner_issue': '#22',
         'planned_items': ['none:out-of-scope'], 'status': '扱わない', 'tier': 'full',
         'assumption': ASSUMPTION, 'breaks_when': BREAKS},
    ],
    'teaching': [{'slide': 'slide:p01-background', 'use': ['review:contrasts/four-lifetimes'], 'note': 'x'}],
}
DONE_FILES = {
    'templates/00_core.md': '## ホップごとの表 <a id="hop-table"></a>\n<!-- req:p01-validate.R1 -->\n## 次 <a id="lifecycle"></a>\n',
    'tools/claim_lint/RULES.md': '| ID | 内容 |\n|---|---|\n| L16 | 下流ほど絞る（req:p01-validate.R1） |\n| L17 | x |\n',
}


def finish(reqs):
    reqs = copy.deepcopy(reqs)
    sha = {s['id']: tc.slide_sha(s) for s in WEB}
    for c in reqs['classification']:
        c.setdefault('sha', sha.get(c['slide'][6:], '000000000000'))
        c.setdefault('reviewed_on', '2026-11-22')
    reqs['summary'] = dict(tc.summary_of([c['kind'] for c in reqs['classification']], reqs['requirements']))
    return reqs


def build(root, slides=None, web=None, items=None, reqs=None, fix=True, write_new_items=True, files=None, raw=None):
    items = copy.deepcopy(ITEMS if items is None else items)
    reqs = copy.deepcopy(REQS if reqs is None else reqs)
    if fix:
        reqs = finish(reqs)
    for d in ('deck', 'docs', os.path.join('templates', 'trace')):
        os.makedirs(os.path.join(root, d), exist_ok=True)
    with open(os.path.join(root, 'deck', 'slide_ids.json'), 'w', encoding='utf-8') as f:
        json.dump(SLIDES if slides is None else slides, f)
    with open(os.path.join(root, 'docs', 'slides.json'), 'w', encoding='utf-8') as f:
        json.dump(WEB if web is None else web, f, ensure_ascii=False)
    with open(os.path.join(root, tc.ITEMS_FILE), 'w', encoding='utf-8') as f:
        yaml.safe_dump(items, f, allow_unicode=True, sort_keys=False)
    with open(os.path.join(root, tc.REQ_FILE), 'w', encoding='utf-8') as f:
        f.write(raw if raw is not None else yaml.safe_dump(reqs, allow_unicode=True, sort_keys=False))
    for rel, text in (files or {}).items():
        os.makedirs(os.path.dirname(os.path.join(root, rel)), exist_ok=True)
        with open(os.path.join(root, rel), 'w', encoding='utf-8') as f:
            f.write(text)
    if write_new_items:
        tc.main(['--root', str(root), '--write-new-items'])
    return str(root)


def run(root, capsys, *extra):
    capsys.readouterr()
    code = tc.main(['--root', root, *extra])
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
    assert 'tier core: 未着手 1, 実装済み 0, 後回し 0, 扱わない 0 (total 1)' in out
    assert 'by owner issue: #4 1, #21 1, #22 1' in out
    assert '扱わない: 1 / 3 (33.3%)' in out


def test_repository_trace_passes(capsys):
    code, out = run(tc.DEFAULT_ROOT, capsys)
    assert code == 0, out


# ------------------------------------------------------------------ (a) slide set and content
def test_new_slide_without_trace_fails(tmp_path, capsys):
    slides = SLIDES + [{'n': 4, 'id': 'p02-new', 'part': 'p02', 'title': 'n'}]
    web = WEB + [{'n': 4, 'id': 'p02-new', 'title': 'n', 'text': 'x', 'notes': ''}]
    code, out = run(build(tmp_path, slides=slides, web=web), capsys)
    assert code == 1 and 'slide:p02-new (slide 4) is not classified' in out


def test_removed_slide_fails(tmp_path, capsys):
    code, out = run(build(tmp_path, slides=SLIDES[:2], web=WEB[:2]), capsys)
    assert code == 1 and 'unknown slide:p01-background' in out


def test_changed_slide_content_fails_until_rehashed(tmp_path, capsys):
    root = build(tmp_path)
    web = copy.deepcopy(WEB)
    web[1]['notes'] = 'ノートを書き換えた'
    with open(os.path.join(root, 'docs', 'slides.json'), 'w', encoding='utf-8') as f:
        json.dump(web, f, ensure_ascii=False)
    code, out = run(root, capsys)
    assert code == 1 and 'slide:p01-validate: slide content changed since it was reviewed on 2026-11-22' in out
    assert tc.main(['--root', root, '--update-hash', 'p01-validate', '--reviewed-on', '2026-12-01']) == 0
    code, out = run(root, capsys)
    assert code == 0, out
    assert '"2026-12-01"' in open(os.path.join(root, tc.REQ_FILE), encoding='utf-8').read()


def test_update_hash_needs_date(tmp_path):
    with pytest.raises(SystemExit):
        tc.main(['--root', build(tmp_path), '--update-hash', 'p01-validate'])


def test_missing_sha_fails(tmp_path, capsys):
    reqs = finish(REQS)
    reqs['classification'][1].pop('sha')
    code, out = run(build(tmp_path, reqs=reqs, fix=False), capsys)
    assert code == 1 and 'sha must be 12 lowercase hex digits' in out


def test_duplicate_classification_fails(tmp_path, capsys):
    reqs = copy.deepcopy(REQS)
    reqs['classification'].append({'slide': 'slide:p00-title', 'kind': 'knowledge'})
    code, out = run(build(tmp_path, reqs=reqs), capsys)
    assert code == 1 and 'classified more than once' in out


def test_bad_kind_fails(tmp_path, capsys):
    reqs = copy.deepcopy(REQS)
    reqs['classification'][0]['kind'] = 'divider'
    code, out = run(build(tmp_path, reqs=reqs), capsys)
    assert code == 1 and 'kind must be one of' in out


# ------------------------------------------------------------------ duplicate YAML keys
@pytest.mark.parametrize('inject', [
    lambda t: t.replace("  text: 下流ほど絞る\n", "  text: 下流ほど絞る\n  text: 別の文\n", 1),
    lambda t: t + 'summary: {}\n',
])
def test_duplicate_yaml_key_fails(tmp_path, capsys, inject):
    raw = inject(yaml.safe_dump(finish(REQS), allow_unicode=True, sort_keys=False))
    code, out = run(build(tmp_path, raw=raw, write_new_items=False), capsys)
    assert code == 1 and 'duplicate key' in out


# ------------------------------------------------------------------ (b) every design slide decomposed, teaching
def test_design_slide_without_requirement_fails(tmp_path, capsys):
    reqs = copy.deepcopy(REQS)
    reqs['requirements'] = []
    reqs['teaching'] = [{'slide': 'slide:p01-background', 'use': ['lint:L16']}]
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


def test_knowledge_slide_without_teaching_fails(tmp_path, capsys):
    reqs = copy.deepcopy(REQS)
    reqs['teaching'] = [{'slide': 'slide:p01-validate', 'use': ['review:contrasts/four-lifetimes']}]
    code, out = run(build(tmp_path, reqs=reqs), capsys)
    assert code == 1 and 'knowledge slide:p01-background has no teaching row' in out


def test_duplicate_teaching_row_fails(tmp_path, capsys):
    reqs = copy.deepcopy(REQS)
    reqs['teaching'].append(copy.deepcopy(reqs['teaching'][0]))
    code, out = run(build(tmp_path, reqs=reqs), capsys)
    assert code == 1 and 'has more than one teaching row' in out


def test_teaching_on_structural_slide_fails(tmp_path, capsys):
    reqs = copy.deepcopy(REQS)
    reqs['teaching'].append({'slide': 'slide:p00-title', 'use': ['lint:L16']})
    code, out = run(build(tmp_path, reqs=reqs), capsys)
    assert code == 1 and 'teaching rows are for knowledge or design-decision slides' in out


# ------------------------------------------------------------------ (c) fields
@pytest.mark.parametrize('change, message', [
    (lambda r: r.pop('owner_issue'), 'owner_issue must look like'),
    (lambda r: r.update(planned_items=[]), 'needs at least one planned item'),
    (lambda r: r.update(planned_items=['template:00_core#hop table']), 'malformed planned item'),
    (lambda r: r.update(planned_items=['lint:L99']), 'lint:L99 is not in'),
    (lambda r: r.update(planned_items=['widget:x']), "unknown kind 'widget'"),
    (lambda r: r.update(status='done'), 'status must be one of'),
    (lambda r: r.pop('tier'), 'tier must be one of'),
    (lambda r: r.update(tier='mvp'), 'tier must be one of'),
    (lambda r: r.update(text=''), 'text is empty'),
    (lambda r: r.update(id='p01-validate-R1'), 'id must be <slide-id>.R<n>'),
    (lambda r: r.update(slide='slide:p00-title'), 'slide must be slide:p01-validate'),
    (lambda r: r.update(owner_issue='#8'), 'owner_issue #8 is not the issue of any planned item'),
    (lambda r: r.update(break_condition='x'), "unknown field 'break_condition'"),
    (lambda r: r.update(assumption=ASSUMPTION), 'assumption is only for status 扱わない'),
    (lambda r: r.update(status='後回し'), '後回し needs owner_issue in'),
])
def test_bad_requirement_fails(tmp_path, capsys, change, message):
    code, out = run(build(tmp_path, reqs=with_req(change)), capsys)
    assert code == 1 and message in out, out


@pytest.mark.parametrize('change, message', [
    (lambda r: r.pop('breaks_when'), '扱わない needs breaks_when'),
    (lambda r: r.update(breaks_when='短い'), 'breaks_when is shorter than 20 characters'),
    (lambda r: r.update(assumption='組織の判断', text='組織の判断'), 'shorter than'),
    (lambda r: r.update(text=ASSUMPTION), 'assumption repeats the text'),
    (lambda r: r.update(breaks_when=ASSUMPTION), 'assumption and breaks_when are identical'),
    (lambda r: r.update(planned_items=['none:out-of-scope', 'lint:L16']), 'needs planned_items exactly [none:out-of-scope]'),
    (lambda r: r.update(owner_issue='#6', planned_items=['lint:L16']), '扱わない needs owner_issue #22'),
    (lambda r: r.update(tier='core'), 'status 扱わない needs tier full'),
])
def test_bad_out_of_scope_fails(tmp_path, capsys, change, message):
    code, out = run(build(tmp_path, reqs=with_req(change, 2)), capsys)
    assert code == 1 and message in out, out


def test_none_item_only_for_out_of_scope(tmp_path, capsys):
    def change(r):
        r.update(status='未着手'); r.pop('assumption'); r.pop('breaks_when')
    code, out = run(build(tmp_path, reqs=with_req(change, 2)), capsys)
    assert code == 1 and 'none:out-of-scope is only for status 扱わない' in out


def test_deferred_owner_must_be_deferred_status(tmp_path, capsys):
    code, out = run(build(tmp_path, reqs=with_req(lambda r: r.update(status='未着手'), 1)), capsys)
    assert code == 1 and 'is a deferred issue' in out


def test_deferred_must_be_full_tier(tmp_path, capsys):
    code, out = run(build(tmp_path, reqs=with_req(lambda r: r.update(tier='core'), 1)), capsys)
    assert code == 1 and 'status 後回し needs tier full' in out


# ------------------------------------------------------------------ (d) 実装済み resolves, with reverse references
def done(r):
    r.update(status='実装済み')


def test_implemented_without_artifact_fails(tmp_path, capsys):
    code, out = run(build(tmp_path, reqs=with_req(done)), capsys)
    assert code == 1
    assert '00_core.md does not exist' in out and 'RULES.md does not exist' in out


def test_implemented_with_artifacts_and_markers_passes(tmp_path, capsys):
    code, out = run(build(tmp_path, reqs=with_req(done), files=DONE_FILES), capsys)
    assert code == 0, out
    assert 'tier core: 未着手 0, 実装済み 1' in out


def test_implemented_without_reverse_reference_fails(tmp_path, capsys):
    files = dict(DONE_FILES)
    files['templates/00_core.md'] = '<a id="hop-table"></a>\n本文\n<a id="lifecycle"></a>\n<!-- req:p01-validate.R1 -->\n'
    files['tools/claim_lint/RULES.md'] = '| L16 | x |\n| L17 | req:p01-validate.R1 |\n| L18 | req:p01-validate.R10 |\n'
    code, out = run(build(tmp_path, reqs=with_req(done), files=files), capsys)
    assert code == 1
    assert 'template:00_core#hop-table does not contain the reverse reference req:p01-validate.R1' in out
    assert 'lint:L16 does not contain the reverse reference' in out


def test_implemented_wrong_anchor_fails(tmp_path, capsys):
    files = dict(DONE_FILES, **{'templates/00_core.md': '<a id="lifecycle"></a> req:p01-validate.R1\n'})
    code, out = run(build(tmp_path, reqs=with_req(done), files=files), capsys)
    assert code == 1 and 'has no anchor <a id="hop-table"></a>' in out


def test_implemented_review_item_needs_anchor(tmp_path, capsys):
    def change(r):
        r.update(status='実装済み', owner_issue='#5', planned_items=['review:contrasts/signed-vs-enforced'])
    files = {'templates/review/contrasts/signed-vs-enforced.md': 'req:p01-validate.R1\n'}
    code, out = run(build(tmp_path, reqs=with_req(change), files=files), capsys)
    assert code == 1 and 'names no #anchor' in out


def test_implemented_registry_marker_in_property(tmp_path, capsys):
    def change(r):
        r.update(status='実装済み', owner_issue='#3', planned_items=['registry:claims#volatility'])
    schema = {'$defs': {'claim': {'properties': {
        'volatility': {'type': 'integer', '$comment': 'req:p01-validate.R1'}, 'on_revoke': {}}}}}
    files = {'templates/registry/claims.schema.json': json.dumps(schema)}
    code, out = run(build(tmp_path, reqs=with_req(change), files=files), capsys)
    assert code == 0, out
    schema['$defs']['claim']['properties']['volatility'].pop('$comment')
    schema['$defs']['claim']['properties']['on_revoke']['$comment'] = 'req:p01-validate.R1'
    files = {'templates/registry/claims.schema.json': json.dumps(schema)}
    code, out = run(build(tmp_path, reqs=with_req(change), files=files), capsys)
    assert code == 1 and 'does not contain the reverse reference' in out


def test_implemented_unbuilt_kind_fails(tmp_path, capsys):
    def change(r):
        r.update(status='実装済み', owner_issue='#19', planned_items=['render:payload-schema'])
    code, out = run(build(tmp_path, reqs=with_req(change)), capsys)
    assert code == 1 and 'kind render has no artifact to resolve yet' in out


# ------------------------------------------------------------------ (e) tier filter, summary, generated list
def test_require_done_for_core(tmp_path, capsys):
    root = build(tmp_path)
    code, out = run(root, capsys, '--tier', 'core', '--require-done')
    assert code == 1 and 'p01-validate.R1: still 未着手 (tier core)' in out
    code, out = run(root, capsys, '--tier', 'full', '--require-done')
    assert code == 0, out


def test_stale_summary_fails(tmp_path, capsys):
    reqs = finish(REQS)
    reqs['summary']['requirements'] = 99
    code, out = run(build(tmp_path, reqs=reqs, fix=False), capsys)
    assert code == 1 and 'summary block is stale' in out


def test_stale_new_items_fails(tmp_path, capsys):
    code, out = run(build(tmp_path, write_new_items=False), capsys)
    assert code == 1 and 'new_items.md: stale' in out


def test_unused_proposed_item_fails(tmp_path, capsys):
    items = copy.deepcopy(ITEMS)
    items['items'].append({'ref': 'lint:L99', 'issue': '#6', 'origin': 'proposed', 'title': 'x'})
    code, out = run(build(tmp_path, items=items), capsys)
    assert code == 1 and 'proposed item lint:L99 is used by no requirement' in out


def test_dump_round_trip(tmp_path):
    data = finish(REQS)
    text = tc.dump_requirements(data, [s['id'] for s in SLIDES])
    back = tc.yaml_load(text)
    assert back['requirements'] == data['requirements']
    assert back['classification'] == data['classification']
    assert back['teaching'] == data['teaching']
    assert back['summary'] == dict(data['summary'])


@pytest.mark.parametrize('ref, ok', [
    ('registry:claims#volatility', True), ('registry:claims', False), ('registry:widgets#x', False),
    ('lint:L1a', True), ('lint:R3b', True), ('lint:L5#x', False), ('lint:NEW-foo', False),
    ('template:modules/M_token_validation#jwks-cache', True), ('template:../x', False),
    ('test:negative_tests#alg-none', True), ('test:other#x', False), ('catalog:token_kinds', True),
    ('deferred:idp-entra', True), ('deferred:Idp', False), ('none:out-of-scope', True), ('none:other', False),
])
def test_parse_ref(ref, ok):
    if ok:
        tc.parse_ref(ref)
    else:
        with pytest.raises(ValueError):
            tc.parse_ref(ref)
