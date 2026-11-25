# -*- coding: utf-8 -*-
"""tools/new_design.py (#4, #60, #61): an empty design starts from blank values, not from a worked example; lint fails
on it with the to-do list (TODO, R1, ...) and never with SCHEMA; the coverage sections carry their key names; the
fill-in tables of the chosen profiles and modules go to appendix D of design.md."""
import os
import shutil
import sys

import pytest
import yaml

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import catalog_check  # noqa: E402
import new_design  # noqa: E402
from claim_lint import core, coverage, render, semantic  # noqa: E402

EXAMPLE_A = os.path.join(ROOT, 'templates', 'examples', 'scenario-a')


def _yaml(path):
    return yaml.safe_load(path.read_text(encoding='utf-8'))


def _by(res, rule):
    return [f for f in res['findings'] if f['rule'] == rule]


def test_new_design_is_blank_and_fails_lint(tmp_path):
    d = tmp_path / 'my-service'
    assert new_design.main([str(d)]) == 0
    tts = _yaml(d / 'token_types.yaml')['token_types']
    kinds = yaml.safe_load(open(os.path.join(ROOT, 'templates', 'catalog', 'token_kinds.yaml'), encoding='utf-8'))['kinds']
    assert len(tts) == len(kinds) and all(t['decision'] == '却下' and t['rationale'] == '' for t in tts)
    ans = _yaml(d / 'catalog_answers.yaml')['answers']
    assert ans and all(a['answer'] is None for a in ans)
    assert _yaml(d / 'claims.yaml')['claims'] == []
    assert _yaml(d / 'claims.yaml')['data_category_vocabulary']['name'] == 'fideslang'
    # no sample rationale of a worked example reaches the new design
    example = open(os.path.join(EXAMPLE_A, 'claims.yaml'), encoding='utf-8').read()
    assert 'saas-api' in example and 'saas-api' not in (d / 'claims.yaml').read_text(encoding='utf-8')
    res = core.run(str(d), profile='lite')
    assert res['counts']['error'] > 0
    assert new_design.main([str(d)]) == 1  # does not overwrite without --force


# ------------------------------------------------------------------ #60: the skeleton is not against the schemas
@pytest.mark.parametrize('profile', ['lite', 'full'])
def test_skeleton_has_no_schema_finding_only_the_to_do_list(tmp_path, profile):
    d = tmp_path / 'design'
    assert new_design.main([str(d), '--profile', profile]) == 0
    res = core.run(str(d), profile=profile)
    assert _by(res, 'SCHEMA') == [], _by(res, 'SCHEMA')[:3]
    assert not [f for f in _by(res, 'LOAD') if f['severity'] == 'error']
    todo = _by(res, 'TODO')
    # blank fields stay errors (no severity is lowered), one finding per field
    assert todo and all(f['severity'] == 'error' for f in todo)
    assert len({f['target'] for f in todo}) == len(todo)
    assert 'claims:scenario' in {f['target'] for f in todo}
    assert res['counts']['error'] > 0
    # the optional `namespaces` is not written as an empty list (pilot defect D1)
    assert 'namespaces' not in _yaml(d / 'claims.yaml')
    assert 'claims:namespaces' not in {f['target'] for f in res['findings']}


def test_lite_skeleton_has_no_hops_file_and_full_says_what_to_do_about_an_empty_one(tmp_path):
    lite, full = tmp_path / 'lite', tmp_path / 'full'
    assert new_design.main([str(lite), '--profile', 'lite']) == 0
    assert new_design.main([str(full), '--profile', 'full']) == 0
    assert not (lite / 'hops.yaml').exists()
    load = [f for f in core.run(str(lite), profile='lite')['findings'] if f['rule'] == 'LOAD']
    assert [(f['severity'], f['target']) for f in load] == [('info', 'hops')]
    assert _yaml(full / 'hops.yaml') == {'hops': []}
    hops = [f for f in core.run(str(full))['findings'] if f['target'] == 'hops:hops']
    assert [(f['rule'], f['severity']) for f in hops] == [('TODO', 'error')]
    assert 'hops.yaml を置かない' in hops[0]['message']


def test_a_design_without_hops_reaches_zero_errors_by_having_no_hops_file(tmp_path):
    """The way written in GETTING_STARTED (手順 1): no hops.yaml. Scenario A without its hops passes Lite with error 0."""
    dst = tmp_path / 'scenario-a'
    shutil.copytree(EXAMPLE_A, dst)
    os.remove(dst / 'hops.yaml')
    res = core.run(str(dst), profile='lite')
    assert res['counts']['error'] == 0
    assert render.sec_hop_table(render.load_design(str(dst)))['tables'][0]['rows'] == []
    # and `hops: []` is not that way: it stays an error
    (dst / 'hops.yaml').write_text('# template_version: 0.2.0\nhops: []\n', encoding='utf-8')
    res = core.run(str(dst), profile='lite')
    assert [f['rule'] for f in res['findings'] if f['severity'] == 'error'] == ['TODO']


def test_a_blank_value_is_todo_and_a_wrong_value_is_schema(tmp_path):
    dst = tmp_path / 'scenario-a'
    shutil.copytree(EXAMPLE_A, dst)
    p = dst / 'token_types.yaml'
    doc = core.load_yaml(str(p))
    doc['issuance_profile']['at_format']['value'] = None      # not written yet
    doc['issuance_profile']['client_type']['value'] = 'nope'  # written and wrong
    p.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding='utf-8')
    res = core.run(str(dst), profile='lite')
    assert [f['target'] for f in _by(res, 'TODO')] == ['token_types:issuance_profile/at_format/value']
    assert [f['target'] for f in _by(res, 'SCHEMA')] == ['token_types:issuance_profile/client_type/value']
    assert all(f['severity'] == 'error' for f in _by(res, 'TODO') + _by(res, 'SCHEMA'))


def test_skeleton_has_the_coverage_sections_with_their_key_names(tmp_path):
    """Pilot defect B10: the keys of questions / subject_states / pairwise were only in RULES.md and catalog_check.py."""
    d = tmp_path / 'design'
    assert new_design.main([str(d)]) == 0
    doc = _yaml(d / 'catalog_answers.yaml')
    questions = yaml.safe_load(open(os.path.join(ROOT, 'templates', 'registry', 'questions.yaml'), encoding='utf-8'))
    assert list(doc['questions']) == [q['id'] for q in questions['questions']]
    assert all(v == {'needed': None, 'reason': ''} for v in doc['questions'].values())
    seeds = yaml.safe_load(open(os.path.join(ROOT, 'templates', 'catalog', 'seeds.yaml'), encoding='utf-8'))
    states = sorted(k for k in catalog_check.seed_items(seeds)[0] if k.startswith(catalog_check.STATES + '/'))
    assert len(states) == 7 and sorted(doc['subject_states']['states']) == states
    for cells in doc['subject_states']['states'].values():
        assert list(cells) == list(catalog_check.LAYERS)
        assert all(c == {'result': None, 'basis': ''} for c in cells.values())
    assert doc['subject_states']['unused_layers'] == {}
    assert list(doc['pairwise']['subject_kinds']) == list(coverage.SUBJECT_KINDS) == list(new_design.SUBJECT_KINDS)
    assert doc['pairwise']['combinations'] == []
    assert list(doc['lite_criteria']) == list(semantic.LITE_CRITERIA) == list(new_design.LITE_CRITERIA)
    # the rules read the sections as present: they ask for the cells, not for the missing section
    res = core.run(str(d))
    assert not [f for f in _by(res, 'R4') if f['target'] == 'subject_states']
    assert not [f for f in _by(res, 'R6') if f['target'] == 'pairwise' and f['severity'] != 'info']
    assert not [f for f in _by(res, 'L13') if f['target'] == 'questions']
    # the allowed values are in the header comment
    head = (d / 'catalog_answers.yaml').read_text(encoding='utf-8')
    for word in ('unused_layers', '発行・再計算・失効・影響なし', 'needed: true か false', 'combinations'):
        assert word in head


# ------------------------------------------------------------------ #61: where the fill-in tables go
def _appendix(path):
    text = path.read_text(encoding='utf-8')
    return text.split(new_design.FILL_BEGIN, 1)[1].split(new_design.FILL_END, 1)[0]


def test_template_has_the_fill_in_region_in_appendix_d():
    core_md = open(os.path.join(ROOT, 'templates', '00_core.md'), encoding='utf-8').read()
    head = core_md.split(new_design.FILL_BEGIN, 1)[0]
    assert '<a id="profile-fill-ins"></a>' in head and '項目 ID：`template:00_core#profile-fill-ins`' in head
    assert core_md.count(new_design.FILL_BEGIN) == 1 and core_md.count(new_design.FILL_END) == 1
    for doc in ('GETTING_STARTED.md', 'README.md'):
        text = open(os.path.join(ROOT, 'templates', doc), encoding='utf-8').read()
        assert '付録 D' in text and '--use' in text, doc


def test_use_copies_the_fill_in_tables_of_the_chosen_profiles(tmp_path):
    d = tmp_path / 'design'
    assert new_design.main([str(d), '--profile', 'full', '--use', 'P4,M_token_validation']) == 0
    body = _appendix(d / 'design.md')
    p4 = new_design.fill_in_sections('P4_ai_agent_delegation')
    tv = new_design.fill_in_sections('M_token_validation')
    assert len(p4) == 9 and len(tv) == 12
    for item, title, block in p4 + tv:
        assert f'`{item}`' in body and title in body and '\n'.join(block) in body
        assert '〔' not in title
    assert 'template:profiles/P1_human_web#' not in body
    # (the copied tables are the template's own, which template_check T4 keeps blank)
    # the document outside the region is the template
    core_md = open(os.path.join(ROOT, 'templates', '00_core.md'), encoding='utf-8').read()
    text = (d / 'design.md').read_text(encoding='utf-8')
    assert text.split(new_design.FILL_BEGIN)[0] == core_md.split(new_design.FILL_BEGIN)[0]
    assert text.split(new_design.FILL_END)[1] == core_md.split(new_design.FILL_END)[1]


def test_lite_copies_only_the_sections_a_lite_design_fills_in(tmp_path):
    d = tmp_path / 'design'
    names = ','.join(new_design.template_parts())
    assert new_design.main([str(d), '--profile', 'lite', '--use', names]) == 0
    body = _appendix(d / 'design.md')
    items = [l.split('`')[1] for l in body.split('\n') if l.startswith('項目：`')]
    expected = []
    for name, rel in new_design.template_parts().items():
        lines = open(os.path.join(ROOT, 'templates', rel + '.md'), encoding='utf-8').read().split('\n')
        for i, line in enumerate(lines):
            if line.startswith('#') and new_design.LITE_MARK in line:
                item = next(l for l in lines[i:] if l.startswith('項目 ID：'))
                expected.append(item.split('`')[1])
    assert items == expected and items
    assert all('Full：記入／Lite：参照' not in l for l in body.split('\n'))


def test_use_on_an_existing_design_adds_only_what_is_missing(tmp_path):
    d = tmp_path / 'design'
    assert new_design.main([str(d), '--use', 'P1']) == 0
    design = d / 'design.md'
    text = design.read_text(encoding='utf-8')
    # the writer fills in a P1 table and a registry file
    row = next(l for l in _appendix(design).split('\n') if l.startswith('|') and '---' not in l and '（書き手が書く）' not in l)
    filled = row.replace('|  |', '| 書き手の答え |', 1)
    assert filled != row
    design.write_text(text.replace(row, filled, 1), encoding='utf-8')
    (d / 'claims.yaml').write_text('# mine\n', encoding='utf-8')
    before = _appendix(design)
    assert new_design.main([str(d), '--use', 'P1,P5']) == 0  # no --force: adds P5, keeps P1 and the other files
    after = _appendix(design)
    assert after.startswith(before.rstrip('\n')) and '書き手の答え' in after
    assert 'template:profiles/P5_internal_propagation#' in after and after.count('#### P1_human_web') == before.count('#### P1_human_web')
    assert (d / 'claims.yaml').read_text(encoding='utf-8') == '# mine\n'
    again = design.read_text(encoding='utf-8')
    assert new_design.main([str(d), '--use', 'P1,P5']) == 0
    assert design.read_text(encoding='utf-8') == again  # idempotent
    assert new_design.main([str(d), '--use', 'P9']) == 2  # unknown name
    assert new_design.main([str(d), '--use', 'M_']) == 2  # ambiguous prefix


def test_render_write_keeps_the_fill_in_tables(tmp_path):
    """The fill-in region is not a render region: render --write fills its own regions and leaves appendix D alone."""
    d = tmp_path / 'design'
    assert new_design.main([str(d), '--profile', 'lite', '--use', 'P4']) == 0
    design = d / 'design.md'
    before = _appendix(design)
    assert set(render.regions(design.read_text(encoding='utf-8'))) <= set(render.SECTION_IDS)
    render.write(str(d), str(design))
    assert _appendix(design) == before and 'mcp-checklist' in before
    assert render.check(str(d), str(design)) == []


# ------------------------------------------------------------------ #61: one sentence, two places
def test_the_column_reduction_rule_is_the_same_sentence_in_both_documents():
    sentence = ('**列を減らす規則は、縮小 Lite（`claim_lint --profile lite`）だけのものです。Full（`--profile` を付けない）では、'
                '既定どおりで `consumers: []` の行にも、トークンに載せる行の必須の列をすべて書きます。**')
    for rel in ('templates/registry/README.md', 'tools/claim_lint/RULES.md', 'templates/README.md'):
        assert sentence in open(os.path.join(ROOT, rel), encoding='utf-8').read(), rel


def test_each_lite_criterion_has_two_yes_and_two_no_examples():
    text = open(os.path.join(ROOT, 'templates', 'README.md'), encoding='utf-8').read()
    rows = [l for l in text.split('\n') if l.startswith('| ') and any(f'（`{k}`）' in l for k in semantic.LITE_CRITERIA)]
    assert len(rows) == 5
    for row in rows:
        cells = [c.strip() for c in row.strip().strip('|').split('|')]
        yes, no = cells[2], cells[3]
        assert '①' in yes and '②' in yes and '①' in no and '②' in no, row
    joined = '\n'.join(rows)
    assert '組織の中でも、信頼しない部品' in joined and '既存か新設かを確かめられない' in joined
