# -*- coding: utf-8 -*-
"""Tests of the registry v1 (#3): the schemas, questions.yaml, issuance_effects.yaml, the README column table, the
REF rule and the new R1 columns of claim_lint, and tools/casestudy_check.py (pure check, no network)."""
import copy
import json
import os
import re
import sys

import jsonschema
import pytest
import yaml

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from claim_lint import core  # noqa: E402
import casestudy_check as cc  # noqa: E402

REG = os.path.join(ROOT, 'templates', 'registry')
EXAMPLE = os.path.join(ROOT, 'templates', 'examples', 'scenario-a')
SCHEMAS = ('claims', 'token_types', 'hops', 'issuance_effects')
FILES = ('claims', 'token_types', 'catalog_answers', 'hops')


def schema(name):
    with open(os.path.join(REG, name + '.schema.json'), encoding='utf-8') as f:
        return json.load(f)


def errors(name, doc):
    return list(jsonschema.Draft202012Validator(schema(name)).iter_errors(doc))


def example():
    return {k: core.load_yaml(os.path.join(EXAMPLE, k + '.yaml')) for k in FILES}


def claim(docs, cid):
    return next(c for c in docs['claims']['claims'] if c['id'] == cid)


def tt(docs, tid):
    return next(t for t in docs['token_types']['token_types'] if t['id'] == tid)


def lint(tmp_path, docs):
    for k, v in docs.items():
        with open(tmp_path / (k + '.yaml'), 'w', encoding='utf-8') as f:
            yaml.safe_dump(v, f, allow_unicode=True, sort_keys=False)
    return core.run(str(tmp_path))


def by(res, rule, severity='error'):
    return [f for f in res['findings'] if f['rule'] == rule and f['severity'] == severity]


# ------------------------------------------------------------------ schemas
@pytest.mark.parametrize('name', SCHEMAS)
def test_schema_is_valid_2020_12_with_version(name):
    s = schema(name)
    jsonschema.Draft202012Validator.check_schema(s)
    assert s['$schema'] == 'https://json-schema.org/draft/2020-12/schema'
    assert s['$id'].endswith('/v0.2.0') and s['$comment'].startswith('template_version: 0.2.0')


def _arrays(node, path='', out=None):
    out = [] if out is None else out
    if isinstance(node, dict):
        if node.get('type') == 'array':
            out.append((path, node))
        for k, v in node.items():
            _arrays(v, f'{path}/{k}', out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _arrays(v, f'{path}/{i}', out)
    return out


@pytest.mark.parametrize('name', ('claims', 'token_types', 'hops', 'issuance_effects'))
def test_every_array_has_max_items(name):
    """#3: arrays are bounded. grants and request_protection are inside choice values and are bounded too."""
    missing = [p for p, a in _arrays(schema(name)) if 'maxItems' not in a]
    assert not missing


def test_yaml_files_start_with_template_version_then_modeline():
    for rel in ('templates/registry/questions.yaml', 'templates/registry/issuance_effects.yaml',
                'templates/examples/scenario-a/claims.yaml', 'templates/examples/scenario-a/token_types.yaml',
                'templates/examples/scenario-a/hops.yaml'):
        lines = open(os.path.join(ROOT, rel), encoding='utf-8').read().splitlines()
        assert lines[0] == '# template_version: 0.2.0', rel
        if rel != 'templates/registry/questions.yaml':
            assert lines[1].startswith('# yaml-language-server: $schema='), rel


def test_example_validates():
    d = example()
    for name in ('claims', 'token_types', 'hops'):
        assert not errors(name, d[name]), name


def _base():
    return copy.deepcopy(example())


def test_overflow_strategy_cannot_be_truncate():
    d = _base()
    claim(d, 'C-roles')['overflow_strategy'] = 'truncate'
    assert errors('claims', d['claims'])


def test_rejection_needs_two_reasons_in_the_schema():
    d = _base()
    c = claim(d, 'C-acr')
    c.pop('revisit_trigger')
    assert errors('claims', d['claims'])


def test_rejection_kind_only_on_rejected_rows():
    d = _base()
    claim(d, 'C-sub')['rejection_kind'] = '不要'
    claim(d, 'C-idp').pop('rejection_kind')
    assert len(errors('claims', d['claims'])) == 2


def test_carried_array_needs_max_items():
    d = _base()
    claim(d, 'C-roles').pop('max_items')
    assert errors('claims', d['claims'])


def test_asvs_is_not_written_in_refs():
    d = _base()
    claim(d, 'C-sub')['refs'].append({'kind': 'guidance', 'id': 'ASVS v5.0.0-8.3.2'})
    assert errors('claims', d['claims'])
    claim(d, 'C-sub')['refs'].pop()
    claim(d, 'C-sub')['asvs_ids'] = ['v5.0.0-8.3.2']
    assert not errors('claims', d['claims'])


@pytest.mark.parametrize('ref', [
    {'kind': 'guidance', 'id': 'OWASP-ASVS 5.0 8.3.2'},
    {'kind': 'guidance', 'id': 'V8.3.2'},
    {'kind': 'guidance', 'id': 'v5.0.0-8.3.2'},
    {'kind': 'guidance', 'id': 'Application Security Verification Standard 5.0.0 8.3.2'},
    {'kind': 'guidance', 'id': 'OWASP の検証標準', 'url': 'https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x17-V8.md'},
    {'kind': 'guidance', 'id': 'OWASP の検証標準', 'url': 'https://owasp.org/www-project-application-security-verification-standard/'},
])
def test_asvs_in_any_spelling_is_not_written_in_refs(ref):
    # PR #37 independent check: the first pattern only caught a leading "ASVS"
    d = _base()
    claim(d, 'C-sub')['refs'].append(ref)
    assert errors('claims', d['claims'])


def test_whitespace_only_reasons_are_empty():
    # PR #37 independent check: minLength counted a space as text, and core._empty did not strip
    d = _base()
    c = claim(d, 'C-acr')
    c['assumption'] = ' '
    c['revisit_trigger'] = '　'
    assert errors('claims', d['claims'])
    assert core._empty('  ') and core._empty(['', ' ']) and not core._empty('x')


def test_whitespace_only_reasons_fail_r1(tmp_path):
    d = _base()
    c = claim(d, 'C-acr')
    c['assumption'] = ' '
    c['revisit_trigger'] = ' '
    res = lint(tmp_path, d)
    assert any(f['target'] == 'C-acr' for f in by(res, 'R1'))


def test_space_delimited_needs_max_items_and_scope_is_space_delimited():
    d = _base()
    assert claim(d, 'C-scope')['shape'] == 'space_delimited'
    claim(d, 'C-scope').pop('max_items')
    assert errors('claims', d['claims'])


def test_measure_only_when_confidential_from_is_not_empty():
    d = _base()
    claim(d, 'C-sub')['confidentiality_measure'] = {'outcome': '載せない', 'rationale': 'x'}
    assert errors('claims', d['claims'])


def test_object_namespace_needs_namespace_version():
    d = _base()
    d['claims']['namespaces'][0].pop('namespace_version')
    assert errors('claims', d['claims'])


def test_display_dir_values_of_sd_jwt_vc():
    d = _base()
    claim(d, 'C-name')['display'][0]['dir'] = 'auto'
    assert not errors('claims', d['claims'])
    claim(d, 'C-name')['display'][0]['dir'] = 'up'
    assert errors('claims', d['claims'])


def test_no_token_but_the_code_in_the_url():
    d = _base()
    tt(d, 'RT')['transport'] = 'redirect_query'
    assert errors('token_types', d['token_types'])
    tt(d, 'RT')['transport'] = 'token_response_body'
    assert tt(d, 'CODE')['transport'] == 'redirect_query' and not errors('token_types', d['token_types'])


def test_r1_idle_timeout_for_rt_and_sessions(tmp_path):
    d = _base()
    tt(d, 'RT').pop('idle_timeout')
    assert ('token_type RT', '必須の列 idle_timeout が空') in {(f['target'], f['message']) for f in by(lint(tmp_path, d), 'R1')}


def test_ref_hop_upstream_cycle(tmp_path):
    d = _base()
    d['hops']['hops'][0]['upstream'] = 'H1'
    assert any(f['target'] == 'hop H1' and '循環' in f['message'] for f in by(lint(tmp_path, d), 'REF'))


def test_data_category_format_only_and_pinned_vocabulary():
    d = _base()
    claim(d, 'C-sub')['data_category'] = ['user.unique_id.employee_number']   # an org sub-category: format is enough
    assert not errors('claims', d['claims'])
    claim(d, 'C-sub')['data_category'] = ['User Unique ID']
    assert errors('claims', d['claims'])
    d = _base()
    d['claims']['data_category_vocabulary']['license'] = 'CC0-1.0'
    assert errors('claims', d['claims'])


def test_confidential_from_needs_a_measure():
    d = _base()
    claim(d, 'C-name').pop('confidentiality_measure')
    assert errors('claims', d['claims'])
    d = _base()
    claim(d, 'C-sub')['confidential_from'] = ['hop:billing', 'logs']
    claim(d, 'C-sub')['confidentiality_measure'] = {'outcome': '派生値', 'rationale': 'ログにはハッシュだけを残す'}
    assert not errors('claims', d['claims'])


def test_identifier_claims_need_identifier_properties():
    d = _base()
    claim(d, 'C-sub').pop('identifier_properties')
    assert errors('claims', d['claims'])


def test_sd_jwt_vc_claim_metadata_names():
    props = schema('claims')['$defs']['claim']['properties']
    assert {'path', 'mandatory', 'sd', 'display'} <= set(props)
    assert props['sd']['enum'] == ['always', 'allowed', 'never']


def test_jwe_used_needs_nesting_recipients_decryptors():
    d = _base()
    tt(d, 'AT')['jwe'] = {'used': True}
    assert errors('token_types', d['token_types'])
    tt(d, 'AT')['jwe'] = {'used': True, 'nesting': 'sign_then_encrypt', 'recipients': [{'recipient': 'saas-api', 'key_ref': 'k1'}],
                          'decryptors': ['api']}
    assert not errors('token_types', d['token_types'])


def test_access_token_never_in_the_url():
    d = _base()
    tt(d, 'AT')['transport'] = 'redirect_query'
    assert errors('token_types', d['token_types'])


def test_rejected_token_type_needs_a_rationale_only():
    # #3: rejection needs a reason (rationale). The reduced Lite (gate1.md 10.) keeps kind, decision, rationale only
    d = _base()
    tt(d, 'SET').pop('assumption')
    tt(d, 'SET').pop('revisit_trigger')
    assert not errors('token_types', d['token_types'])
    tt(d, 'SET').pop('rationale')
    assert errors('token_types', d['token_types'])


def test_mtls_needs_tls_termination_and_entry_needs_header():
    d = _base()
    ip = d['token_types']['issuance_profile']
    ip['sender_constraint'] = {'value': 'mtls', 'rationale': 'x'}
    assert errors('token_types', d['token_types'])
    ip['tls_termination'] = {'value': 'at_entry', 'rationale': 'x'}
    assert errors('token_types', d['token_types'])
    ip['forwarded_cert_header'] = {'name': 'X-Client-Cert', 'strip_inbound': True, 'written_only_by': 'entry'}
    assert not errors('token_types', d['token_types'])


def test_inventory_has_every_token_kind():
    kinds = {k['id'] for k in core.load_yaml(os.path.join(ROOT, 'templates', 'catalog', 'token_kinds.yaml'))['kinds']}
    rows = example()['token_types']['token_types']
    assert kinds == {t['kind'] for t in rows}
    assert set(schema('token_types')['$defs']['token_type']['properties']['kind']['enum']) == kinds
    assert all(t['decision'] in ('採用', '既定どおり') or t.get('rationale') for t in rows)


# ------------------------------------------------------------------ questions
def test_question_text_is_the_slide_wording():
    slides = {s['id']: s for s in json.load(open(os.path.join(ROOT, 'docs', 'slides.json'), encoding='utf-8'))}
    q = core.load_yaml(os.path.join(REG, 'questions.yaml'))
    ids = [x['id'] for x in q['questions']] + [x['id'] for x in q['pending']]
    assert len(ids) == len(set(ids))
    for x in q['questions']:
        assert x['slides'], x['id']
        for sid in x['slides']:
            assert sid in slides, sid
            assert x['text'] in slides[sid]['text'], (x['id'], sid)
    for x in q['pending']:
        assert x['tracking'] and all(s in slides for s in x['nearest_slides'])
    # p05-one-request-carries has separate rows for act, req_wl and the mTLS peer (#10)
    assert {'q-actor', 'q-req-wl', 'q-peer'} <= {x['id'] for x in q['questions'] if 'p05-one-request-carries' in x['slides']}


# ------------------------------------------------------------------ issuance effects
def test_issuance_effects_conditions_name_allowed_values():
    eff = core.load_yaml(os.path.join(REG, 'issuance_effects.yaml'))
    assert not errors('issuance_effects', eff)
    prof = schema('token_types')['$defs']['issuance_profile']['properties']
    ids = set()
    for e in eff['effects']:
        assert e['id'] not in ids
        ids.add(e['id'])
        for r in e['requires']:
            assert r['id'].startswith(e['id'] + '.')
        for c in e['when']:
            p = prof[c['field']]
            value = p['allOf'][1]['properties']['value']
            allowed = value.get('enum') or value['items']['enum']
            v = c.get('equals', c.get('includes'))
            assert v in allowed, (e['id'], c)
    want = {'E-dpop', 'E-mtls', 'E-opaque', 'E-phantom', 'E-client-credentials', 'E-token-exchange', 'E-rar',
            'E-rt-sender-constrained', 'E-public-no-sender-constraint'}
    assert want <= ids


# ------------------------------------------------------------------ README
def test_readme_documents_every_column_with_evidence():
    readme = open(os.path.join(REG, 'README.md'), encoding='utf-8').read()
    rows = {}
    for line in readme.splitlines():
        m = re.match(r'^\| `([a-z_]+)` \|', line)
        if m:
            cells = [c.strip() for c in line.strip('|').split('|')]
            if len(cells) >= 5:   # the column tables of 3.; shorter tables (10.) are mappings, not column rows
                rows.setdefault(m.group(1), []).append(cells)
    props = set(schema('claims')['$defs']['claim']['properties']) | set(schema('token_types')['$defs']['token_type']['properties']) \
        | set(schema('token_types')['$defs']['issuance_profile']['properties']) | set(schema('hops')['$defs']['hop']['properties'])
    missing = sorted(p for p in props if p not in rows)
    assert not missing
    for name, rs in rows.items():
        for cells in rs:
            assert len(cells) >= 5, name
            assert cells[-2], f'{name}: 根拠 is empty'
            assert cells[-1].startswith(('手で書く', '生成', 'Full のみ')), f'{name}: {cells[-1]}'


# ------------------------------------------------------------------ claim_lint: REF and the new R1 columns
def test_ref_pass_on_example(tmp_path):
    assert not by(lint(tmp_path, _base()), 'REF')


def test_ref_pending_question_and_unknown_ids(tmp_path):
    d = _base()
    claim(d, 'C-exp')['answers'] = ['q-still-valid']
    claim(d, 'C-sub')['answers'] = ['q-nope']
    d['hops']['hops'][1]['token_type'] = 'NOPE'
    d['hops']['hops'][1]['custom_claims'].append('C-nope')
    d['claims']['data_category_extensions'][0]['key'] = 'user.tenant'
    targets = {(f['target'], f['message'].split(' ')[0]) for f in by(lint(tmp_path, d), 'REF')}
    assert ('C-exp', 'answers') in targets and ('C-sub', 'answers') in targets
    assert ('hop H2', 'token_type') in targets and ('hop H2', 'custom_claims') in targets
    assert any(t.startswith('data_category_extensions') for t, _ in targets)


def test_r1_new_columns(tmp_path):
    d = _base()
    claim(d, 'C-sub').pop('data_category')
    claim(d, 'C-aud').pop('confidential_from')
    tt(d, 'AT').pop('visible_to')
    tt(d, 'IDT').pop('jwe')
    msgs = {(f['target'], f['message']) for f in by(lint(tmp_path, d), 'R1')}
    assert ('C-sub', '必須の列 data_category が空') in msgs
    assert any(t == 'C-aud' and 'confidential_from' in m for t, m in msgs)
    assert ('token_type AT', '必須の列 visible_to が空') in msgs
    assert ('token_type IDT', '必須の列 jwe が空') in msgs


def test_hops_missing_is_info(tmp_path):
    d = _base()
    d.pop('hops')
    res = lint(tmp_path, d)
    assert [f for f in res['findings'] if f['rule'] == 'LOAD' and f['severity'] == 'info']
    assert res['counts']['error'] == 0


# ------------------------------------------------------------------ casestudy_check (pure)
PIN = {'commit': '080b8da317ac13386f60232f1840cdb7eadbc262'}
CATALOG = [{'id': 'ORG-01', 'name': 'https://claims.example.com/.tenant_id', 'value_type': 'string'},
           {'id': 'ORG-03', 'name': 'https://claims.example.com/.roles', 'value_type': 'array of string'},
           {'id': 'CLM-0206', 'name': 'acr', 'value_type': 'string'}]
DECISIONS = {'ORG-01': {'A': {'judgement': '必須（共通基準）'}}, 'ORG-03': {'A': {'judgement': '採用'}},
             'CLM-0206': {'A': {'judgement': '条件付き採用'}}}


def _cs_doc():
    ns = 'https://claims.example.com/'
    return {'scenario': 'A', 'casestudy_commit': '080b8da', 'claims': [
        {'id': 'C-tenant-id', 'name': 'tenant_id', 'namespace': ns, 'type': 'string', 'shape': 'single', 'decision': '採用',
         'catalog_refs': ['jwt-claims-casestudy@080b8da:ORG-01']},
        {'id': 'C-roles', 'name': 'roles', 'namespace': ns, 'type': 'string', 'shape': 'array', 'decision': '採用',
         'catalog_refs': ['jwt-claims-casestudy@080b8da:ORG-03']},
        {'id': 'C-acr', 'name': 'acr', 'type': 'string', 'decision': '却下', 'catalog_refs': ['jwt-claims-casestudy@080b8da:CLM-0206']}]}


DEV = {'deviations': [{'scenario': 'A', 'id': 'CLM-0206', 'example_row': 'C-acr', 'kind': 'carry'}]}


def test_casestudy_pass():
    assert cc.check(_cs_doc(), DEV, CATALOG, DECISIONS, PIN) == []


def test_casestudy_org_name_and_type_mismatch():
    d = _cs_doc()
    d['claims'][0]['name'] = 'tenant'
    d['claims'][1]['shape'] = 'single'
    kinds = [k for k, _, _ in cc.check(d, DEV, CATALOG, DECISIONS, PIN)]
    assert kinds.count('ORG') == 2


def test_casestudy_unlisted_and_stale_deviation():
    assert [k for k, _, _ in cc.check(_cs_doc(), {'deviations': []}, CATALOG, DECISIONS, PIN)] == ['CARRY']
    dev = {'deviations': DEV['deviations'] + [{'scenario': 'A', 'id': 'ORG-03', 'example_row': 'C-roles', 'kind': 'carry'}]}
    out = cc.check(_cs_doc(), dev, CATALOG, DECISIONS, PIN)
    assert len(out) == 1 and 'agree' in out[0][2]


def test_casestudy_wrong_commit():
    d = _cs_doc()
    d['casestudy_commit'] = 'deadbee'
    assert any(k == 'PIN' for k, _, _ in cc.check(d, DEV, CATALOG, DECISIONS, PIN))


def _cs_doc_ns():
    d = _cs_doc()
    d['namespaces'] = [{'namespace': 'https://claims.example.com/'}]
    return d


def test_casestudy_refs_must_be_declared_and_org_rows_must_refer():
    # PR #37 independent check: dropping catalog_refs hid an ORG rename and a carry divergence
    d = _cs_doc_ns()
    d['claims'][0].pop('catalog_refs')
    d['claims'][0]['name'] = 'tenant'
    kinds = {(k, t) for k, t, _ in cc.check(d, DEV, CATALOG, DECISIONS, PIN)}
    assert ('REFS', 'C-tenant-id') in kinds and ('ORG', 'C-tenant-id') in kinds
    d = _cs_doc_ns()
    d['claims'][2]['catalog_refs'] = []
    msgs = [m for _, _, m in cc.check(d, DEV, CATALOG, DECISIONS, PIN)]
    assert any('catalog_refs_reason' in m for m in msgs)


def test_casestudy_carried_row_missing_from_the_example():
    d = _cs_doc()
    d['claims'] = d['claims'][:2]           # drop the acr row and its deviation: the casestudy still carries CLM-0206
    out = cc.check(d, {'deviations': []}, CATALOG, DECISIONS, PIN)
    assert [k for k, _, _ in out] == ['COVER']
    dev = {'deviations': [{'scenario': 'A', 'id': 'CLM-0206', 'kind': 'not_in_example', 'reason': 'この例では使わない'}]}
    assert cc.check(d, dev, CATALOG, DECISIONS, PIN) == []


def test_casestudy_duplicate_ref_names_both_rows():
    d = _cs_doc()
    d['claims'].append({'id': 'C-acr2', 'name': 'acr', 'type': 'string', 'decision': '採用',
                        'catalog_refs': ['jwt-claims-casestudy@080b8da:CLM-0206']})
    out = cc.check(d, DEV, CATALOG, DECISIONS, PIN)
    assert any(k == 'REFS' and 'C-acr' in m and 'C-acr2' in m for k, _, m in out)


def test_casestudy_pin_file():
    pin = cc.load_pin()
    assert re.fullmatch('[0-9a-f]{40}', pin['commit'])
    assert pin['catalog_file'] in pin['files'] and all(f in pin['files'] for f in pin['decision_files'])
    assert all(re.fullmatch('[0-9a-f]{64}', h) for h in pin['files'].values())
