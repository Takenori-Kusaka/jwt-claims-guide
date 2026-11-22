# -*- coding: utf-8 -*-
"""Tests of claim_lint render (#19): generated tables, marked regions (--write / --check), the JSON bundle for the
viewer (#36), the payload JSON Schemas (consumer / issuer conformance) and the issuance effects."""
import copy
import json
import os
import shutil
import subprocess
import sys

import jsonschema
import pytest

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from claim_lint import core, render  # noqa: E402

EXAMPLE = os.path.join(ROOT, 'templates', 'examples', 'scenario-a')
DOC = os.path.join(EXAMPLE, 'design.md')
GOLDEN_TOKEN = os.path.join(TOOLS, 'tests', 'fixtures', 'claim_lint', 'golden', 'token.json')
NS = 'https://claims.example.com/'


@pytest.fixture(scope='module')
def lint():
    """The claim_lint result of the worked example, reused for copies (their path would change the CI section)."""
    return render.lint_result(EXAMPLE, DOC)


def copy_example(tmp_path):
    dst = tmp_path / 'design'
    shutil.copytree(EXAMPLE, dst)
    return str(dst)


def edit_line(path, old, new):
    """Change exactly one line of a file (keeping its newline style)."""
    with open(path, encoding='utf-8', newline='') as f:
        lines = f.read().split('\n')
    hits = [k for k, l in enumerate(lines) if old in l]
    assert len(hits) == 1, (old, hits)
    lines[hits[0]] = lines[hits[0]].replace(old, new)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write('\n'.join(lines))


def md_without_ci(design_dir):
    d = render.load_design(design_dir)
    return render.render_md(render.build_sections(d, None, only=set(render.SECTION_IDS) - {'ci-result'})).splitlines()


def golden_payload():
    return render.read_payload(GOLDEN_TOKEN)


# ------------------------------------------------------------------ the worked example is in sync
def test_example_regions_and_schemas_match_the_registry(lint):
    assert render.check(EXAMPLE, DOC, lint) == []


def test_example_has_every_generated_section():
    text, _ = render._read_text(DOC)
    assert set(render.regions(text)) == set(render.SECTION_IDS)


def test_cli_check_and_section(tmp_path):
    r = subprocess.run([sys.executable, os.path.join(TOOLS, 'claim_lint'), 'render', EXAMPLE, '--check'],
                       capture_output=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout.decode('utf-8') + r.stderr.decode('utf-8')
    r = subprocess.run([sys.executable, '-m', 'tools.claim_lint', 'render', EXAMPLE, '--section', 'token-inventory'],
                       capture_output=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr.decode('utf-8')
    out = r.stdout.decode('utf-8')
    assert out.startswith('## トークン目録') and '| `AT` | アクセストークン |' in out and '## 判断の行' not in out


# ------------------------------------------------------------------ one registry line changes only the related rows
@pytest.mark.parametrize('file, old, new, row_key', [
    ('claims.yaml', 'rationale: API の入口で、承認と管理の操作を粗く絞る。', 'rationale: API の入口で、承認と管理の操作を粗く絞る（変更）。', '`C-roles`'),
    ('claims.yaml', 'source_system: Keycloak のユーザー（レルムの DB）', 'source_system: Keycloak のユーザー（変更）', '`C-sub`'),
    ('token_types.yaml', 'rationale: BFF がログインを確かめ、画面の表示名を得る', 'rationale: BFF がログインを確かめる（変更）', '`IDT`'),
    ('catalog_answers.yaml', 'breaks_when: テレビ・CLI など、入力の限られた端末のクライアントを足すとき',
     'breaks_when: CLI の端末のクライアントを足すとき（変更）', '`I07`'),
])
def test_one_line_change_changes_only_the_related_row(tmp_path, file, old, new, row_key):
    before = md_without_ci(EXAMPLE)
    dst = copy_example(tmp_path)
    edit_line(os.path.join(dst, file), old, new)
    after = md_without_ci(dst)
    assert len(before) == len(after)
    changed = [(a, b) for a, b in zip(before, after) if a != b]
    assert len(changed) == 1, changed
    assert row_key in changed[0][1] and '（変更）' in changed[0][1]


def test_one_line_change_in_the_payload_schema(tmp_path):
    dst = copy_example(tmp_path)
    edit_line(os.path.join(dst, 'claims.yaml'), 'max_bytes: 12', 'max_bytes: 16')  # C-roles
    s0 = render.payload_schemas(render.load_design(EXAMPLE))['AT']['issuer']
    s1 = render.payload_schemas(render.load_design(dst))['AT']['issuer']
    roles0 = s0['properties'][NS]['properties'].pop('roles')
    roles1 = s1['properties'][NS]['properties'].pop('roles')
    assert s0 == s1 and roles0['items']['maxLength'] == 12 and roles1['items']['maxLength'] == 16


# ------------------------------------------------------------------ --check detects drift, --write repairs it
def test_check_detects_registry_drift_and_write_repairs_it(tmp_path, lint):
    dst = copy_example(tmp_path)
    doc = os.path.join(dst, 'design.md')
    assert render.check(dst, doc, lint) == []
    edit_line(os.path.join(dst, 'claims.yaml'), 'revisit_trigger: 利用者を別のレルムへ移す運用を始めるとき',
              'revisit_trigger: 利用者をレルムの間で移すとき')
    problems = render.check(dst, doc, lint)
    assert len(problems) == 1 and 'design.md' in problems[0] and '利用者をレルムの間で移すとき' in problems[0]
    assert render.write(dst, doc, lint) == [core._rel(doc, ROOT)]
    assert render.check(dst, doc, lint) == []


def test_check_detects_a_hand_edit_inside_a_region_only(tmp_path, lint):
    dst = copy_example(tmp_path)
    doc = os.path.join(dst, 'design.md')
    edit_line(doc, '書き手が自信のない点　〔縮小 Lite：手で書く〕', '書き手が自信のない点（手で直した）　〔縮小 Lite：手で書く〕')
    assert render.check(dst, doc, lint) == []  # outside the regions: hand-written prose is kept
    edit_line(doc, '| `CODE` | 認可コード | 既定どおり |', '| `CODE` | 認可コード | 採用 |')
    problems = render.check(dst, doc, lint)
    assert len(problems) == 1 and '| `CODE` | 認可コード | 既定どおり |' in problems[0]
    render.write(dst, doc, lint)
    text, _ = render._read_text(doc)
    assert '（手で直した）' in text and '| `CODE` | 認可コード | 既定どおり |' in text


def test_check_detects_schema_drift(tmp_path, lint):
    dst = copy_example(tmp_path)
    path = os.path.join(dst, 'schemas', 'AT.issuer.schema.json')
    with open(path, encoding='utf-8') as f:
        s = json.load(f)
    s['additionalProperties'] = True
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(s, f)
    problems = render.check(dst, os.path.join(dst, 'design.md'), lint)
    assert len(problems) == 1 and 'AT.issuer.schema.json' in problems[0]


def test_check_keeps_crlf(tmp_path, lint):
    dst = copy_example(tmp_path)
    doc = os.path.join(dst, 'design.md')
    with open(doc, encoding='utf-8', newline='') as f:
        text = f.read().replace('\r\n', '\n')
    with open(doc, 'w', encoding='utf-8', newline='') as f:
        f.write(text.replace('\n', '\r\n'))
    edit_line(os.path.join(dst, 'claims.yaml'), 'revisit_trigger: AT の寿命を変えるとき', 'revisit_trigger: AT の寿命を変えたとき')
    render.write(dst, doc, lint)
    with open(doc, 'rb') as f:
        raw = f.read()
    assert b'\r\n' in raw and raw.count(b'\n') == raw.count(b'\r\n')


@pytest.mark.parametrize('text, needle', [
    ('<!-- render:nope:begin -->\nx\n<!-- render:nope:end -->\n', 'unknown region nope'),
    ('<!-- render:hop-table:begin -->\nx\n', 'unbalanced'),
    ('<!-- render:hop-table:begin -->\n<!-- render:hop-table:end -->\n<!-- render:hop-table:begin -->\n<!-- render:hop-table:end -->\n', 'twice'),
])
def test_bad_regions_are_errors(text, needle):
    with pytest.raises(ValueError, match=needle):
        render.regions(text)


# ------------------------------------------------------------------ payload JSON Schemas
def test_schema_kinds_and_required():
    d = render.load_design(EXAMPLE)
    schemas = render.payload_schemas(d)
    assert set(schemas) == {'AT', 'IDT'}  # adopted JWT token types only
    for kinds in schemas.values():
        jsonschema.Draft202012Validator.check_schema(kinds['consumer'])
        jsonschema.Draft202012Validator.check_schema(kinds['issuer'])
        assert kinds['consumer']['additionalProperties'] is True
        assert kinds['issuer']['additionalProperties'] is False
    at = schemas['AT']
    assert at['issuer']['properties'][NS]['additionalProperties'] is False
    assert at['consumer']['properties'][NS]['additionalProperties'] is True
    assert at['consumer']['required'] == ['iss', 'sub', 'aud', 'exp', 'iat', 'jti', 'azp', NS]
    assert at['consumer']['properties'][NS]['required'] == ['tenant_id', 'user_id', 'v']
    # rejected claims are not in the schema; claims carried only in IDT are not in the AT schema
    assert 'realm_access' not in at['issuer']['properties'] and 'nonce' not in at['issuer']['properties']
    assert at['issuer']['properties'][NS]['properties']['roles'] == {
        'description': at['issuer']['properties'][NS]['properties']['roles']['description'], '$comment': 'C-roles',
        'type': 'array', 'items': {'type': 'string', 'maxLength': 12, 'enum': ['approver', 'tenant-admin']}, 'maxItems': 2}


def test_golden_keycloak_token_conforms_to_the_issuer_schema():
    d = render.load_design(EXAMPLE)
    assert render.validate_payload(d, golden_payload(), 'AT', 'issuer') == []
    assert render.validate_payload(d, golden_payload(), 'AT', 'consumer') == []


@pytest.mark.parametrize('mutate, issuer_fails, consumer_fails', [
    (lambda p: p.update(realm_access={'roles': ['offline_access']}), True, False),   # a rejected claim slipped in
    (lambda p: p.update(unknown_claim='x'), True, False),                             # a claim not in the registry
    (lambda p: p[NS].update(department='sales'), True, False),                        # unknown claim in the namespace
    (lambda p: p[NS]['roles'].append('auditor'), True, False),                        # outside the vocabulary, 3 items
    (lambda p: p.pop('azp'), True, True),                                             # required claim missing
    (lambda p: p[NS].pop('tenant_id'), True, True),                                   # required namespaced claim missing
    (lambda p: p.update(exp=str(p['exp'])), True, True),                              # wrong type
])
def test_issuer_schema_rejects_what_the_registry_does_not_declare(mutate, issuer_fails, consumer_fails):
    d = render.load_design(EXAMPLE)
    p = copy.deepcopy(golden_payload())
    mutate(p)
    assert bool(render.validate_payload(d, p, 'AT', 'issuer')) is issuer_fails
    assert bool(render.validate_payload(d, p, 'AT', 'consumer')) is consumer_fails


def test_cli_validate_fails_on_an_unknown_claim(tmp_path):
    p = golden_payload()
    p['unknown_claim'] = 'x'
    bad = tmp_path / 'payload.json'
    bad.write_text(json.dumps(p), encoding='utf-8')
    cmd = [sys.executable, os.path.join(TOOLS, 'claim_lint'), 'render', EXAMPLE, '--token-type', 'AT', '--validate']
    assert subprocess.run(cmd + [GOLDEN_TOKEN], capture_output=True, cwd=ROOT).returncode == 0
    r = subprocess.run(cmd + [str(bad)], capture_output=True, cwd=ROOT)
    assert r.returncode == 1 and 'unknown_claim' in r.stdout.decode('utf-8')


def test_read_payload_accepts_a_compact_jws(tmp_path):
    with open(GOLDEN_TOKEN, encoding='utf-8') as f:
        token = json.load(f)['token']
    p = tmp_path / 'at.jwt'
    p.write_text(token, encoding='utf-8')
    assert render.read_payload(str(p)) == golden_payload()


# ------------------------------------------------------------------ issuance effects
def test_scenario_a_triggers_no_effect():
    effects = render.issuance_effects(render.load_design(EXAMPLE))
    assert effects and not any(e['holds'] for e in effects)


def test_dpop_effect_and_the_claims_that_satisfy_it():
    d = render.load_design(EXAMPLE)
    d['token_types']['issuance_profile']['sender_constraint']['value'] = 'dpop'
    e = {x['id']: x for x in render.issuance_effects(d)}
    assert e['E-dpop']['holds'] and not e['E-mtls']['holds']
    st = {r['id']: r['status'] for r in e['E-dpop']['requires']}
    assert st == {'E-dpop.1': 'unsatisfied', 'E-dpop.2': 'unsatisfied', 'E-dpop.3': 'unsatisfied',
                  'E-dpop.4': 'unsatisfied', 'E-dpop.5': 'unsatisfied'}
    d['claims']['claims'].append({'id': 'C-cnf', 'name': 'cnf', 'namespace': None, 'decision': '採用', 'type': 'object',
                                  'shape': 'single', 'carried_in': ['AT'], 'max_bytes': 60, 'consumers': ['saas-api'],
                                  'enforced_at': [{'service': 'saas-api', 'check': 'DPoP proof の htm・htu・iat・jti・ath'}]})
    tt = {t['id']: t for t in d['token_types']['token_types']}
    tt['DPOP'].update(decision='採用', typ='dpop+jwt')
    tt['AT']['transport'] = 'authorization_dpop'
    e = {x['id']: x for x in render.issuance_effects(d)}
    got = {r['id']: (r['status'], r['rows']) for r in e['E-dpop']['requires']}
    assert got == {'E-dpop.1': ('satisfied', ['C-cnf']), 'E-dpop.2': ('satisfied', ['C-cnf']),
                   'E-dpop.3': ('satisfied', ['DPOP']), 'E-dpop.4': ('satisfied', ['C-cnf']),
                   'E-dpop.5': ('satisfied', ['AT'])}
    sec = render.sec_issuance_profile(d)
    md = render.section_md(sec)
    assert '条件が成り立つ行は 1 件' in md and '| `E-dpop` | `E-dpop.1` |' in md


# ------------------------------------------------------------------ JSON bundle (viewer, #36)
def test_bundle_is_deterministic_and_shares_rows_with_markdown(lint):
    d = render.load_design(EXAMPLE)
    b1 = render.bundle(EXAMPLE, d, render.build_sections(d, lint))
    b2 = render.bundle(EXAMPLE, render.load_design(EXAMPLE), render.build_sections(render.load_design(EXAMPLE), lint))
    assert json.dumps(b1, ensure_ascii=False) == json.dumps(b2, ensure_ascii=False)
    assert b1['format'] == render.BUNDLE_FORMAT and b1['section_ids'] == render.SECTION_IDS
    assert set(b1['registry']) == {'claims', 'token_types', 'hops', 'catalog_answers'}
    assert set(b1['payload_schemas']) == {'AT', 'IDT'}
    inv = next(s for s in b1['sections'] if s['id'] == 'token-inventory')['tables'][0]
    assert [r['id'] for r in inv['rows']] == [t['id'] for t in d['token_types']['token_types']]
    assert all({'key', 'label', 'fmt'} <= set(c) for c in inv['columns'])
    cat = next(s for s in b1['sections'] if s['id'] == 'catalog-summary')['counts']
    assert cat['total'] == 62 and cat['out_of_scope'] == 50 and cat['out_of_scope_pct'] == 81 and cat['missing'] == []
    json.dumps(b1)  # serialisable without default=


def test_markdown_cells_escape_pipes_and_newlines():
    assert render.cell('a|b\nc', 'text') == 'a\\|b<br>c'
    assert render.cell(None, 'text') == '—' and render.cell([], 'codes') == '—'
    assert render.cell([{'kind': 'guide-slide', 'id': 'p06-narrow-downstream'}], 'refs') == '`slide:p06-narrow-downstream`'
