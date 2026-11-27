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
    dst = tmp_path / 'scenario-a'  # the directory name is part of the schemas' $id
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
    assert cat['total'] == 64 and cat['out_of_scope'] == 51 and cat['out_of_scope_pct'] == 80 and cat['missing'] == []  # U29・U30 (#63)
    json.dumps(b1)  # serialisable without default=


def test_markdown_cells_escape_pipes_and_newlines():
    assert render.cell('a|b\nc', 'text') == 'a\\|b<br>c'
    assert render.cell(None, 'text') == '—' and render.cell([], 'codes') == '—'
    assert render.cell([{'kind': 'guide-slide', 'id': 'p06-narrow-downstream'}], 'refs') == '`slide:p06-narrow-downstream`'


# ------------------------------------------------------------------ independent check of PR #39
def test_orphan_schema_of_a_rejected_token_type_fails_check_and_write_removes_it(tmp_path, lint):
    dst = copy_example(tmp_path)
    doc = os.path.join(dst, 'design.md')
    edit_line(os.path.join(dst, 'token_types.yaml'), 'rationale: BFF がログインを確かめ、画面の表示名を得る',
              'rationale: BFF がログインを確かめ、画面の表示名を得る（却下にした）')
    path = os.path.join(dst, 'token_types.yaml')
    with open(path, encoding='utf-8', newline='') as f:
        text = f.read()
    nl = '\r\n' if '\r\n' in text else '\n'
    old = nl.join(['  - id: IDT', '    kind: id_token', '    decision: 採用'])
    assert text.count(old) == 1
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text.replace(old, old.replace('採用', '却下')))
    render.write(dst, doc, lint)
    orphan = os.path.join(dst, 'schemas', 'IDT.issuer.schema.json')
    assert not os.path.exists(orphan)
    with open(orphan, 'w', encoding='utf-8') as f:
        f.write('{}\n')
    problems = render.check(dst, doc, lint)
    assert any('IDT.issuer.schema.json: not generated from the registry any more' in p for p in problems)
    render.write(dst, doc, lint)
    assert not os.path.exists(orphan)


def test_tokenless_hop_shows_the_sender_as_writer_not_the_token_issuer():
    sec = render.sec_arrow_table(render.load_design(EXAMPLE))
    h3 = [r for r in sec['tables'][0]['rows'] if r['hop'] == 'H3']
    assert len(h3) == 1 and h3[0]['claim_id'] == 'C-tenant-id'
    assert h3[0]['writers'][0].startswith('saas-api（トークンなし。書き先：Postgres のセッション変数 app.tenant')
    assert 'iss から引いたテナント' in h3[0]['writers'][0] and 'Keycloak' not in h3[0]['writers'][0].split('。')[0]
    h2 = [r for r in sec['tables'][0]['rows'] if r['hop'] == 'H2' and r['claim_id'] == 'C-tenant-id']
    assert h2[0]['writers'][0].startswith('② Keycloak')


def _claim_rows(d):
    return {r['id']: r for r in next(t for t in render.sec_lifecycle(d)['tables'] if t['id'] == 'lifecycle-claim')['rows']}


def test_volatility_zero_means_immediate_and_is_flagged():
    d = render.load_design(EXAMPLE)
    for c in d['claims']['claims']:
        if c['id'] in ('C-sub', 'C-tenant-id', 'C-nonce'):
            c['volatility'] = 0
    rows = _claim_rows(d)
    assert rows['C-sub']['exceeds'] and rows['C-sub']['exceeds_text'] == '超える（AT 330 秒・IDT 330 秒 > 許容 0 秒）'  # IDT max_clock_skew 30 (#6, L27)
    assert rows['C-tenant-id']['measures'] == ['AT：DB の確認（0 秒）']  # a candidate; whether it applies is on_revoke
    assert rows['C-nonce']['exceeds'] and rows['C-nonce']['measures'] == []
    assert not rows['C-roles']['exceeds'] and not rows['C-name']['exceeds']  # 330 <= 330, 330 <= 86400


def test_volatility_never_is_not_compared():
    rows = _claim_rows(render.load_design(EXAMPLE))
    assert not any(r['exceeds'] for r in rows.values())
    assert rows['C-sub']['volatility'] == 'never' and rows['C-sub']['exceeds_text'] == '寿命の間に変わらない（never）'
    assert render.cell('never', 'seconds') == '`never`' and render.cell(330, 'seconds') == '330 秒'


@pytest.mark.parametrize('value, ok', [(0, True), (330, True), ('never', True), (-1, False), ('immutable', False), (None, False)])
def test_claims_schema_volatility_is_seconds_or_never(value, ok):
    with open(os.path.join(ROOT, 'templates', 'registry', 'claims.schema.json'), encoding='utf-8') as f:
        prop = json.load(f)['$defs']['claim']['properties']['volatility']
    assert jsonschema.Draft202012Validator(prop).is_valid(value) is ok


def _dpop_design():
    d = render.load_design(EXAMPLE)
    d['token_types']['issuance_profile']['sender_constraint']['value'] = 'dpop'
    return d


def test_all_consumers_matches_whole_words_not_substrings():
    d = _dpop_design()
    d['claims']['claims'].append({'id': 'C-cnf', 'name': 'cnf', 'namespace': None, 'decision': '採用', 'carried_in': ['AT'],
                                  'consumers': ['saas-api'], 'enforced_at': [
                                      {'service': 'saas-api', 'check': 'htm・htu は path まで・iat・jti を照合'}]})
    e = {x['id']: x for x in render.issuance_effects(d)}
    st = {r['id']: r['status'] for r in e['E-dpop']['requires']}
    assert st['E-dpop.2'] == 'unsatisfied'  # "ath" is not in the checks; "path" must not count as "ath"


def test_star_includes_needs_every_row():
    d = render.load_design(EXAMPLE)
    d['token_types']['issuance_profile']['at_format']['value'] = 'opaque_introspection'
    d['token_types']['token_types'].append({'id': 'INTRO', 'kind': 'introspection_response_jwt', 'decision': '採用',
                                            'format': 'jwt', 'transport': 'introspection_response'})
    next(c for c in d['claims']['claims'] if c['id'] == 'C-sub')['carried_in'] = ['INTRO']
    e = {x['id']: x for x in render.issuance_effects(d)}
    r = next(r for r in e['E-opaque']['requires'] if r['id'] == 'E-opaque.1')
    assert r['status'] == 'unsatisfied' and r['rows'] == ['C-sub']  # one row moved, the others are still in the AT


def test_equals_on_a_mapping_is_a_subset_match():
    d = render.load_design(EXAMPLE)
    d['token_types']['issuance_profile']['client_type']['value'] = 'public'
    rt = next(t for t in d['token_types']['token_types'] if t['id'] == 'RT')
    rt['rt_rotation'] = {'rotation': True, 'reuse_detection': 'yes', 'note': '別のキーがあってもよい'}
    e = {x['id']: x for x in render.issuance_effects(d)}
    r = e['E-public-no-sender-constraint']['requires'][0]
    assert e['E-public-no-sender-constraint']['holds'] and r['status'] == 'satisfied' and r['rows'] == ['RT']


def test_issuance_effects_table_is_labelled_as_not_a_check():
    md = render.section_md(render.sec_issuance_profile(_dpop_design()))
    note, table = md.index('**次の表は検査ではない。**'), md.index('| 行 | 要件 |')
    assert note < table and 'L62' in md[note:table] and '簡易な読み取り（正は L62）' in md


def test_decision_rows_show_alt():
    rows = {r['id']: r for r in render.sec_decision_rows(render.load_design(EXAMPLE))['tables'][0]['rows']}
    assert rows['C-preferred-username']['alt'] == ['C-name', 'C-sub']
    text, _ = render._read_text(DOC)
    assert '| `C-realm-access` | `realm_access` | 却下（代替あり） | `C-roles` |' in text


def test_bundle_sources_include_the_catalog():
    src = render.bundle(EXAMPLE, render.load_design(EXAMPLE), [])['sources']
    assert {'templates/catalog/token_kinds.yaml', 'templates/catalog/issue_events.yaml',
            'templates/catalog/use_events.yaml'} <= set(src)


def test_schema_id_and_template_version():
    s = render.payload_schemas(render.load_design(EXAMPLE))['AT']['issuer']
    assert s['$id'] == 'https://github.com/Takenori-Kusaka/jwt-claims-guide/payload-schemas/scenario-a/AT.issuer.schema.json/v0.2.0'
    assert s['$comment'].startswith('template_version: 0.2.0.')


def test_consumer_aud_accepts_string_or_array_issuer_follows_the_registry():
    d = render.load_design(EXAMPLE)
    p = golden_payload()
    p['aud'] = ['saas-api', 'other-api']
    assert render.validate_payload(d, p, 'AT', 'consumer') == []
    assert render.validate_payload(d, p, 'AT', 'issuer')  # the registry says shape single


# ------------------------------------------------------------------ #60: names, silent dashes
PILOT_B = os.path.join(ROOT, 'research', 'pilot', 'scenario-b')  # namespaces[].style: flat_prefix
PILOT_C = os.path.join(ROOT, 'research', 'pilot', 'scenario-c')  # written with the Lite fields: no status column


def _shown_names(d):
    """claim id -> the names that the generated tables show for it (every table that has a claim name column)."""
    out = {}
    secs = [render.sec_decision_rows(d), render.sec_data_sources(d), render.sec_arrow_table(d), render.sec_lifecycle(d)]
    for sec in secs:
        for t in sec['tables']:
            for r in t['rows']:
                cid = r.get('claim_id') or r.get('id')
                name = r.get('claim') or r.get('candidate')
                if cid and name:
                    out.setdefault(cid, set()).add(name)
    return out


def _schema_keys(d):
    """claim id -> the name of the claim in the issuer payload schemas (top-level key, or <namespace>.<member>)."""
    out = {}
    for schemas in render.payload_schemas(d).values():
        for key, prop in schemas['issuer']['properties'].items():
            if prop.get('type') == 'object' and '$comment' not in prop:  # an object-style namespace
                for member, p in prop['properties'].items():
                    out.setdefault(p['$comment'], set()).add(f'{key}.{member}')
            else:
                out.setdefault(prop['$comment'], set()).add(key)
    return out


@pytest.mark.parametrize('design, style', [(PILOT_B, 'flat_prefix'), (EXAMPLE, 'object')])
def test_shown_names_are_the_names_of_the_payload_schema_and_required_claims(design, style):
    d = render.load_design(design)
    assert {n['style'] for n in d['claims']['namespaces']} == {style}
    shown, keys = _shown_names(d), _schema_keys(d)
    namespaced = {c['id'] for c in render._claims(d) if c.get('namespace') and c['id'] in keys}
    assert namespaced
    for cid in keys:
        assert shown[cid] == keys[cid], (cid, shown[cid], keys[cid])
    # every namespaced name of required_claims is a shown name, spelled the same way
    all_shown = set().union(*shown.values())
    required = {r for t in render._tts(d) for r in t.get('required_claims') or [] if r.startswith(NS)}
    assert required and required <= all_shown, required - all_shown


def test_flat_prefix_name_has_no_dot_between_namespace_and_name():
    d = render.load_design(PILOT_B)
    rows = {r['id']: r for r in render.sec_decision_rows(d)['tables'][0]['rows']}
    assert rows['C-employee-id']['candidate'] == NS + 'employee_id'
    text, _ = render._read_text(os.path.join(PILOT_B, 'design.md'))
    assert NS + '.' not in text and '`' + NS + 'employee_id`' in text
    # an object-style namespace keeps the path form that required_claims uses
    assert render._full_name({'namespace': NS, 'name': 'tenant_id'}, render.load_design(EXAMPLE)) == NS + '.tenant_id'


def test_arrow_table_says_why_a_hop_has_no_row():
    """Pilot C: hops[].to is a URL and enforced_at.service a service name, so every row was a silent dash."""
    sec = render.sec_arrow_table(render.load_design(PILOT_C))
    rows = sec['tables'][0]['rows']
    assert rows and all(r.get('unmatched') for r in rows)
    for r in rows:
        assert r['claim'] is None and len(r['checks']) == 1
        assert 'の名前を含む `enforced_at.service` が無い' in r['checks'][0] and 'invoices-api' in r['checks'][0]
    notice = [n for n in sec['notes'] if '受け手に結びつく行が無いホップ' in n]
    assert len(notice) == 1 and 'H1・H2・H3' in notice[0]
    md = render.render_md([sec])
    assert '| `H1` | `AGENT_AT` | — | — | 結びつく行なし：' in md


def test_arrow_table_has_no_notice_when_the_names_meet(tmp_path):
    d = render.load_design(EXAMPLE)
    sec = render.sec_arrow_table(d)
    assert not [n for n in sec['notes'] if '受け手に結びつく行が無いホップ' in n]
    # a hop whose token carries no registry row (an opaque session) says so, and is not counted as a mismatch
    h1 = [r for r in sec['tables'][0]['rows'] if r['hop'] == 'H1']
    assert len(h1) == 1 and h1[0]['checks'] == ['結びつく行なし：このホップのトークンに載る台帳の行が無い（`carried_in`）']
    # renaming the receiver of a hop breaks the link, and the table says so
    d2 = copy.deepcopy(d)
    h2 = next(h for h in d2['hops']['hops'] if h['id'] == 'H2')
    h2['to'] = 'https://api.example.com'
    sec2 = render.sec_arrow_table(d2)
    assert [n for n in sec2['notes'] if '受け手に結びつく行が無いホップ：H2' in n]
    assert [r for r in sec2['tables'][0]['rows'] if r['hop'] == 'H2'][0]['checks'][0].startswith('結びつく行なし：受け手 `https://api.example.com`')


def _definition_table(d):
    sec = render.sec_lifecycle(d)
    return sec, next(t for t in sec['tables'] if t['id'] == 'lifecycle-definition')


def test_lifecycle_has_no_column_of_dashes_for_status():
    """Pilot C (Lite fields): no row writes `status`, so the column is left out and a note says why."""
    sec, t = _definition_table(render.load_design(PILOT_C))
    assert t['rows'] and all(r['status'] is None for r in t['rows'])
    assert 'status' not in [c['key'] for c in t['columns']]
    assert [n for n in sec['notes'] if '「状態」の列は出していない' in n]
    # scenario A writes status: the column stays and there is no note
    sec, t = _definition_table(render.load_design(EXAMPLE))
    assert 'status' in [c['key'] for c in t['columns']] and {r['status'] for r in t['rows']} == {'active'}
    assert not [n for n in sec['notes'] if '「状態」の列は出していない' in n]


@pytest.mark.parametrize('design', [PILOT_B, PILOT_C, os.path.join(ROOT, 'templates', 'examples', 'scenario-b')])
def test_pilot_designs_and_scenario_b_are_in_sync(design):
    assert render.check(design, os.path.join(design, 'design.md')) == []
