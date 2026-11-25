# -*- coding: utf-8 -*-
"""Tests of #58: several IdPs (R3, R3b, L2 per IdP), claims an IdP defines (L1b idp_defined, L7, L74), a reissue hop with
several upstream hops that adds values from a directory (L16 added_claims, aud_mapping), an access token without aud
(L27 audience_claim), token kinds with the same header typ (L17 kind_discriminator), per-IdP exceptions of the issuance
profile (L62), and an issuer the organization builds itself (R3 kind: self_built).

The base is tools/tests/fixtures/claim_lint/pilot-b-migrated: the pilot design of scenario B (research/pilot/scenario-b,
#9, which is evidence and stays as it was written) with the workarounds of its author replaced by the new columns. Every
rule has a mutation test: the fixture passes, and the fixture with one declaration broken fails."""
import copy
import datetime
import json
import os
import shutil
import subprocess
import sys

import jsonschema
import pytest
import yaml

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from claim_lint import core, coverage, drift, render, semantic  # noqa: E402

FIXTURE = os.path.join(TOOLS, 'tests', 'fixtures', 'claim_lint', 'pilot-b-migrated')
PILOT = os.path.join(ROOT, 'research', 'pilot', 'scenario-b')
PILOT_C = os.path.join(ROOT, 'research', 'pilot', 'scenario-c')
FILES = ('claims', 'token_types', 'catalog_answers', 'hops')
TODAY = datetime.date(2026, 11, 25)
_BASE = {k: core.load_yaml(os.path.join(FIXTURE, k + '.yaml')) for k in FILES}
_PILOT = {k: core.load_yaml(os.path.join(PILOT, k + '.yaml')) for k in FILES}


def base():
    return copy.deepcopy(_BASE)


def pilot():
    return copy.deepcopy(_PILOT)


def lint(tmp_path, docs, profile='full'):
    d = tmp_path / 'design'
    d.mkdir(parents=True, exist_ok=True)
    for k, v in docs.items():
        with open(d / (k + '.yaml'), 'w', encoding='utf-8') as f:
            yaml.safe_dump(v, f, allow_unicode=True, sort_keys=False)
    for n in os.listdir(FIXTURE):
        if n.startswith('claim_request_'):
            shutil.copy(os.path.join(FIXTURE, n), d / n)
    return core.run(str(d), profile=profile, today=TODAY)


def by(res, rule, severity=None):
    return [f for f in res['findings'] if f['rule'] == rule and (severity is None or f['severity'] == severity)]


def errors(res):
    return [(f['rule'], f['target'], f['message']) for f in res['findings'] if f['severity'] == 'error']


def claim(docs, cid):
    return next(c for c in docs['claims']['claims'] if c['id'] == cid)


def tt(docs, tid):
    return next(t for t in docs['token_types']['token_types'] if t['id'] == tid)


def hop(docs, hid):
    return next(h for h in docs['hops']['hops'] if h['id'] == hid)


def idp(docs, name):
    return next(e for e in docs['catalog_answers']['idp'] if e['name'] == name)


@pytest.fixture(scope='module')
def migrated():
    return core.run(FIXTURE, today=TODAY)


# ------------------------------------------------------------------ the fixture, and the designs that must not change
def test_fixture_is_what_the_migration_of_the_pilot_makes():
    out = subprocess.run([sys.executable, os.path.join(FIXTURE, 'migrate.py'), '--check'], capture_output=True)
    assert out.returncode == 0, out.stdout.decode('utf-8', 'replace') + out.stderr.decode('utf-8', 'replace')


def test_migrated_pilot_b_has_no_error_without_the_workarounds(migrated):
    assert errors(migrated) == []
    warns = sorted((f['rule'], f['target']) for f in migrated['findings'] if f['severity'] == 'warn')
    # L11 and L69 are the two warnings the pilot's author left. R3b I26 is new: the pilot named Keycloak only, so nothing
    # compared Auth0's Actions with the claim that Auth0 adds (C-auth0-roles); what its author confirmed is about Keycloak
    assert warns == [('L11', 'C-sub-unread'), ('L69', 'C-groups'), ('R3b', 'I26')]


def test_the_workarounds_are_gone_from_the_fixture():
    d = base()
    assert [e['name'] for e in d['catalog_answers']['idp']] == ['keycloak', 'entra', 'okta', 'cognito', 'auth0']    # 1
    names = {c['name'] for c in d['claims']['claims'] if c.get('idp_defined')}                                       # 2
    assert names == {'oid', 'tid', 'scp', 'uid', 'cid', 'token_use', 'cognito:groups', 'realm_access', 'typ'}
    for h in ('H7', 'H8'):                                                                                           # 3
        assert hop(d, h)['upstream'] == ['H2', 'H3', 'H4', 'H5', 'H6'] and 'note' not in hop(d, h)
    assert 'aud' not in tt(d, 'COGNITO_AT')['required_claims'] and tt(d, 'COGNITO_AT')['audience_claim'] == 'client_id'  # 4
    for t in d['token_types']['token_types']:                                                                        # 5
        assert '（' not in str(t.get('typ', '')), t['id']
    assert d['token_types']['issuance_profile']['client_auth']['exceptions'][0]['idp'] == 'cognito'                  # 6
    # and the pilot itself still has them (it is not rewritten)
    p = pilot()
    assert p['catalog_answers']['idp'] == {'name': 'keycloak', 'version': '26.8'}
    assert 'upstream' not in hop(p, 'H7') and 'required_claims' not in tt(p, 'COGNITO_AT')


@pytest.mark.parametrize('design,profile,counts', [
    (PILOT, 'full', {'error': 0, 'warn': 2, 'info': 16}),
    (PILOT_C, 'lite', {'error': 0, 'warn': 3, 'info': 9}),
])
def test_committed_pilot_designs_give_the_same_result_as_before(design, profile, counts):
    """The pilot designs were written against 0.2.0 and are not edited; their design.md embeds the lint result."""
    assert core.run(design, profile=profile, today=TODAY)['counts'] == counts


@pytest.mark.parametrize('name', ('claims', 'token_types', 'hops'))
def test_designs_written_for_0_2_0_still_validate(name):
    with open(os.path.join(ROOT, 'templates', 'registry', name + '.schema.json'), encoding='utf-8') as f:
        v = jsonschema.Draft202012Validator(json.load(f))
    for d in ('templates/examples/scenario-a', 'templates/examples/scenario-b', 'research/pilot/scenario-b', 'research/pilot/scenario-c'):
        assert list(v.iter_errors(core.load_yaml(os.path.join(ROOT, d, name + '.yaml')))) == [], d


# ------------------------------------------------------------------ 1: several IdPs (R3, R3b, L2, R2)
def test_r3_reports_every_idp(migrated):
    assert sorted(f['target'] for f in by(migrated, 'R3', 'info')) == ['idp[auth0]', 'idp[entra]', 'idp[keycloak]', 'idp[okta]']


def test_r3_fails_for_an_idp_whose_documentation_was_not_searched(tmp_path):
    d = base()
    oe = d['catalog_answers']['outside_enumeration']
    oe['searched'] = [s for s in oe['searched'] if 'okta' not in s.lower()]
    got = by(lint(tmp_path, d), 'R3', 'error')
    assert [f['target'] for f in got] == ['idp[okta]']


def test_r3_fails_for_cognito_without_its_trigger_list(tmp_path):
    d = base()
    del idp(d, 'cognito')['trigger_list']
    assert [f['target'] for f in by(lint(tmp_path, d), 'R3', 'error')] == ['idp[cognito]']


def test_r3_pilot_with_one_idp_never_looked_at_the_others(tmp_path):
    """Before: idp held one IdP, so dropping the Okta documentation from the search changed nothing."""
    d = pilot()
    oe = d['catalog_answers']['outside_enumeration']
    oe['searched'] = [s for s in oe['searched'] if 'okta' not in s.lower()]
    assert by(lint(tmp_path, d), 'R3', 'error') == []


@pytest.mark.parametrize('mutate,word', [
    (lambda d: d['catalog_answers']['idp'].append({'name': 'okta'}), '2 回'),
    (lambda d: d['catalog_answers']['idp'].append({'version': '1'}), 'name'),
    (lambda d: idp(d, 'okta').update(token_types=['OKTA_AT', 'NO_SUCH']), 'NO_SUCH'),
    (lambda d: idp(d, 'okta').update(token_types='OKTA_AT'), '配列'),
    (lambda d: idp(d, 'okta').update(kind='saas'), 'kind'),
])
def test_r3_rejects_a_malformed_idp_list(tmp_path, mutate, word):
    d = base()
    mutate(d)
    assert any(word in f['message'] for f in by(lint(tmp_path, d), 'R3', 'error'))


def test_r3_every_idp_token_type_belongs_to_an_idp(tmp_path):
    """Check of PR #70, B5: a token type taken out of its IdP's token_types took the checks of that type with it."""
    d = base()
    idp(d, 'auth0')['token_types'] = ['ID_TOKEN', 'REFRESH_TOKEN']
    res = lint(tmp_path, d)
    got = by(res, 'R3', 'error')
    assert len(got) == 1 and 'AUTH0_AT' in got[0]['message']
    d = base()
    del idp(d, 'entra')['token_types']
    assert any('entra に token_types がない' in f['message'] for f in by(lint(tmp_path, d), 'R3', 'error'))


SB = dict(kind='self_built',
          trigger_list=[{'trigger': 'すべての発行', 'out_of_scope': {'assumption': 'この発行者は社内の入口だけが使い、契機は設計書に列挙した',
                                                                 'breaks_when': '入口の外から発行を求める経路ができたとき'}}],
          trigger_list_source={'document': '設計書 3.2 節（発行の契機）', 'verified_on': '2026-11-25'})


def _move_auth0_at_to_keycloak(d):
    idp(d, 'auth0')['token_types'].remove('AUTH0_AT')
    idp(d, 'keycloak')['token_types'].append('AUTH0_AT')


def _move_auth0_at_to_self_built(d):
    idp(d, 'auth0')['token_types'].remove('AUTH0_AT')
    d['catalog_answers']['idp'].append(dict(SB, name='org-sts', token_types=['AUTH0_AT']))


def _relabel_auth0_at_internal(d):
    tt(d, 'AUTH0_AT')['kind'] = 'internal_token'
    idp(d, 'auth0')['token_types'].remove('AUTH0_AT')


def _move_kc_at_to_cognito(d):
    idp(d, 'keycloak')['token_types'].remove('KC_AT')
    idp(d, 'cognito')['token_types'].append('KC_AT')


@pytest.mark.parametrize('mutate', [_move_auth0_at_to_keycloak, _move_auth0_at_to_self_built, _relabel_auth0_at_internal,
                                    _move_kc_at_to_cognito])
def test_r3_token_type_attached_to_an_idp_that_does_not_issue_it(tmp_path, mutate):
    """Re-check of PR #70: moving a token type to another entry (or relabelling its kind) silenced the per-IdP checks
    without a trace. The issuers of the inventory give it away."""
    d = base()
    mutate(d)
    got = [f for f in by(lint(tmp_path, d), 'R3', 'warn') if 'issuers' in f['message'] or '同じ iss' in f['message']]
    assert got, mutate.__name__


def test_r3_self_built_name_is_matched_by_whole_words(tmp_path):
    d = base()
    d['catalog_answers']['idp'].append(dict(SB, name='central-sts', token_types=['REFRESH_TOKEN']))  # contains "entra"
    assert not [f for f in by(lint(tmp_path, d), 'R3', 'warn')]


def test_r3_self_built_under_a_product_like_name_is_reported(tmp_path):
    """Check of PR #70: Auth0 renamed auth0-tenant and declared self_built silenced R3b and L2 without a trace."""
    d = base()
    e = idp(d, 'auth0')
    e.update(name='auth0-tenant', kind='self_built',
             trigger_list=[{'trigger': 'すべての発行', 'out_of_scope': {'assumption': 'この発行者は社内の入口だけが使い、契機は設計書に列挙した',
                                                                    'breaks_when': '入口の外から発行を求める経路ができたとき'}}],
             trigger_list_source={'document': '設計書 3.2 節（発行の契機）', 'verified_on': '2026-11-25'})
    res = lint(tmp_path, d)
    got = [f for f in by(res, 'R3') if f['target'] == 'idp[auth0-tenant]']
    assert sorted(f['severity'] for f in got) == ['info', 'warn']
    assert 'auth0' in next(f for f in got if f['severity'] == 'warn')['message']
    assert '照合しない' in next(f for f in got if f['severity'] == 'info')['message']


def test_r3b_compares_a_claim_with_the_idp_that_issues_it(tmp_path, migrated):
    # C-auth0-roles is carried in AUTH0_AT only: Auth0's hook table is used, and Keycloak's is not
    assert [(f['target'], f['severity']) for f in by(migrated, 'R3b')] == [('I26', 'warn')]
    assert 'auth0' in by(migrated, 'R3b')[0]['message']
    # before: the pilot named Keycloak only, and the same claim was compared with Keycloak's mappers (3 info)
    assert len(by(core.run(PILOT, today=TODAY), 'R3b', 'info')) == 3
    d = base()
    a = next(x for x in d['catalog_answers']['answers'] if x['event'] == 'I26')
    a['hook_checked'] = {'auth0': 'Auth0 の post-login の Action が、パスワード変更の後のログインでも roles を足すことをテナントで確かめた'}
    assert [f['severity'] for f in by(lint(tmp_path, d), 'R3b')] == ['info']


def test_r3b_idp_defined_does_not_hide_a_namespaced_claim(tmp_path):
    d = base()
    claim(d, 'C-auth0-roles')['idp_defined'] = {'idp': 'auth0'}
    assert [(f['target'], f['severity']) for f in by(lint(tmp_path, d), 'R3b')] == [('I26', 'warn')]


def test_l2_reads_the_reserved_list_of_every_idp(tmp_path, migrated):
    assert sorted(f['target'] for f in by(migrated, 'L2', 'info')) == ['idp[auth0]', 'idp[entra]', 'idp[keycloak]', 'idp[okta]']
    d = base()
    claim(d, 'C-cognito-token-use')['modifiers'] = [{'stage': '②', 'writer': 'pre token generation Lambda', 'action': '上書き'}]
    assert [f['target'] for f in by(lint(tmp_path, d), 'L2', 'warn')] == ['C-cognito-token-use']


def test_l2_only_looks_at_the_claims_in_the_idps_own_token_types(tmp_path):
    d = base()  # sub is immutable in Cognito, but C-sub-unread is carried in the Okta and Entra tokens only
    claim(d, 'C-sub-unread')['modifiers'] = [{'stage': '②', 'writer': 'token inline hook', 'action': '上書き'}]
    assert by(lint(tmp_path, d), 'L2', 'warn') == []


def test_r2_lite_inheritance_needs_one_idp(tmp_path):
    d = base()
    a = next(x for x in d['catalog_answers']['answers'] if x['answer'] == '対象外')
    a.update(inherit='idp-default', setting_checked='Direct Access Grants が OFF であることを管理画面で確かめた')
    got = [f for f in by(lint(tmp_path, d, profile='lite'), 'R2') if f['target'] == a['event']]
    assert got and 'IdP が 5 つ' in got[0]['message']


# ------------------------------------------------------------------ 6 (issue): an issuer the organization builds itself
def _self_built(docs, **over):
    e = {'name': 'org-sts', 'kind': 'self_built', 'version': '設計中', 'token_types': ['INTERNAL_TOKEN'],
         'trigger_list_source': {'document': 'design.md の 4.（組織の STS が受ける grant の一覧）', 'verified_on': '2026-11-25', 'planned': True},
         'trigger_list': [{'trigger': '入口での作り直し（要求ごと）', 'events': ['I21']},
                          {'trigger': 'grant_type=client_credentials',
                           'out_of_scope': {'assumption': 'この STS はクライアントに直接トークンを出さない', 'breaks_when': 'STS にトークンエンドポイントを公開したとき'}}]}
    e.update(over)
    docs['catalog_answers']['idp'].append(e)
    return e


def test_r3_self_built_issuer_passes_without_a_url(tmp_path):
    d = base()
    _self_built(d)
    res = lint(tmp_path, d)
    assert by(res, 'R3', 'error') == []
    info = [f for f in by(res, 'R3', 'info') if f['target'] == 'idp[org-sts]']
    assert info and 'planned' in info[0]['message']
    assert not [f for f in by(res, 'R3b') + by(res, 'L2') if f['target'] == 'idp[org-sts]']


@pytest.mark.parametrize('over,word', [
    ({'trigger_list_source': {'verified_on': '2026-11-25'}}, 'document'),
    ({'trigger_list_source': {'document': 'TODO', 'verified_on': '2026-11-25'}}, 'document'),
    ({'trigger_list_source': {'document': 'design.md の 4.（組織の STS が受ける grant の一覧）'}}, 'verified_on'),
    ({'trigger_list': []}, 'trigger_list'),
    ({'trigger_list': [{'trigger': '作り直し'}]}, '差集合'),
    ({'name': 'okta'}, '製品'),
])
def test_r3_self_built_issuer_fails(tmp_path, over, word):
    d = base()
    if over.get('name') == 'okta':
        d['catalog_answers']['idp'] = [e for e in d['catalog_answers']['idp'] if e['name'] != 'okta']
    _self_built(d, **over)
    assert any(word in f['message'] for f in by(lint(tmp_path, d), 'R3', 'error'))


# ------------------------------------------------------------------ 2: claims an IdP defines (L1b, L7, L74, schemas)
def test_l1b_accepts_pinned_idp_names_read_at_the_entry(migrated):
    ok = [f['target'] for f in by(migrated, 'L1b', 'info')]
    assert sorted(ok) == sorted(c['id'] for c in _BASE['claims']['claims'] if c.get('idp_defined'))
    assert by(migrated, 'L1b', 'error') == []


def test_l1b_same_row_without_idp_defined_is_the_error_the_pilot_met(tmp_path):
    d = base()
    del claim(d, 'C-entra-oid')['idp_defined']
    assert [f['target'] for f in by(lint(tmp_path, d), 'L1b', 'error')] == ['C-entra-oid']


@pytest.mark.parametrize('mutate,word', [
    (lambda d: claim(d, 'C-entra-oid')['idp_defined'].update(idp='pingfederate'), 'catalog_answers.yaml の idp にない'),
    (lambda d: claim(d, 'C-entra-oid').update(name='employee_no'), 'idp_claims.yaml'),          # not a name Entra defines
    (lambda d: claim(d, 'C-entra-oid')['idp_defined'].update(idp='okta'), 'idp_claims.yaml'),  # oid is not Okta's
    (lambda d: claim(d, 'C-entra-oid')['carried_in'].append('INTERNAL_TOKEN'), 'INTERNAL_TOKEN'),
    (lambda d: claim(d, 'C-entra-oid')['carried_in'].append('OKTA_AT'), 'OKTA_AT'),
    (lambda d: hop(d, 'H7')['custom_claims'].append('C-entra-oid'), 'H7'),
    (lambda d: hop(d, 'H3')['forwarded_headers'].append({'name': 'X-Oid', 'claim': 'C-entra-oid', 'strip_inbound': True,
                                                         'written_only_by': '入口'}), 'ヘッダー'),
    (lambda d: claim(d, 'C-entra-oid')['consumers'].append('orders'), 'orders'),
])
def test_l1b_idp_defined_does_not_open_a_way_around_the_namespace(tmp_path, mutate, word):
    d = base()
    mutate(d)
    got = [f for f in by(lint(tmp_path, d), 'L1b', 'error') if f['target'] == 'C-entra-oid']
    assert got and word in got[0]['message'], got


def test_l1b_idp_claim_carried_only_in_another_idps_token(tmp_path):
    """Mutation gap of the check of PR #70: condition (3) alone (Entra's oid carried in the Okta token only)."""
    d = base()
    claim(d, 'C-entra-oid')['carried_in'] = ['OKTA_AT']
    hop(d, 'H3')['custom_claims'].remove('C-entra-oid')
    hop(d, 'H4')['custom_claims'].append('C-entra-oid')
    tt(d, 'ENTRA_AT')['required_claims'].remove('oid')
    tt(d, 'OKTA_AT')['required_claims'].append('oid')
    got = [f for f in by(lint(tmp_path, d), 'L1b', 'error') if f['target'] == 'C-entra-oid']
    assert got and 'OKTA_AT は IdP entra が出す AT・ID トークンの種別でない' in got[0]['message']


def test_l1b_only_the_entry_that_remints_may_read_an_idp_name():
    """Check of PR #70: in scenario A (one IdP, no gateway) the API reads the Keycloak token itself. realm_access read by
    the API was an L1b error before #58 and stays one with idp_defined."""
    a = os.path.join(ROOT, 'templates', 'examples', 'scenario-a')
    docs = {k: core.load_yaml(os.path.join(a, k + '.yaml')) for k in FILES}
    src = next(c for c in docs['claims']['claims'] if c['id'] == 'C-tenant-id')
    row = copy.deepcopy(src)
    row.update(id='C-x-realm-access', name='realm_access', namespace=None, idp_defined={'idp': 'keycloak'})
    docs['claims']['claims'].append(row)
    tt(docs, 'AT')['required_claims'].append('realm_access')
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        for k, v in docs.items():
            with open(os.path.join(tmp, k + '.yaml'), 'w', encoding='utf-8') as f:
                yaml.safe_dump(v, f, allow_unicode=True, sort_keys=False)
        for n in os.listdir(a):
            if n.startswith('claim_request_'):
                shutil.copy(os.path.join(a, n), tmp)
        res = core.run(tmp, today=TODAY)
    got = [f for f in by(res, 'L1b') if f['target'] == 'C-x-realm-access']
    assert [f['severity'] for f in got] == ['error'] and '入口' in got[0]['message']


def test_l1b_the_client_may_read_an_idp_name_from_the_id_token(tmp_path):
    """Re-check of PR #70: a BFF that reads Entra's oid from the ID token. For an ID token the entry is the client."""
    d = base()
    idt = copy.deepcopy(tt(d, 'ID_TOKEN'))
    idt.update(id='ENTRA_IDT', issuers=[i for i in idt['issuers'] if 'microsoftonline' in i['iss']])
    d['token_types']['token_types'].append(idt)
    idp(d, 'entra')['token_types'].append('ENTRA_IDT')
    row = copy.deepcopy(claim(d, 'C-entra-oid'))
    row.update(id='C-entra-oid-idt', carried_in=['ENTRA_IDT'], consumers=['portal-bff'],
               enforced_at=[dict(e, service='portal-bff') for e in row['enforced_at']])
    d['claims']['claims'].append(row)
    d['catalog_answers']['answers'][0].setdefault('token_types', [])
    res = lint(tmp_path, d)
    assert [f['severity'] for f in by(res, 'L1b') if f['target'] == 'C-entra-oid-idt'] == ['info']
    claim(d, 'C-entra-oid-idt')['consumers'].append('orders')  # a downstream service is still not the entry
    got = [f for f in by(lint(tmp_path, d), 'L1b', 'error') if f['target'] == 'C-entra-oid-idt']
    assert got and 'orders' in got[0]['message']


def test_l1b_same_name_of_two_idps_may_differ_but_not_inside_one_idp(tmp_path, migrated):
    # Entra scp is a space-delimited string and Okta scp an array: two rows named scp, no finding
    assert not [f for f in by(migrated, 'L1b') if '同じ名前' in f['message']]
    d = base()
    twin = copy.deepcopy(claim(d, 'C-okta-scp'))
    twin.update(id='C-okta-scp-2', description='別の意味の scp')
    d['claims']['claims'].append(twin)
    got = [f for f in by(lint(tmp_path, d), 'L1b', 'error') if '同じ名前' in f['message']]
    assert [f['target'] for f in got] == ['C-okta-scp・C-okta-scp-2']


def test_l7_idp_claim_the_entry_rejects_without_must_be_required(tmp_path, migrated):
    assert by(migrated, 'L7') == []
    d = base()
    tt(d, 'ENTRA_AT')['required_claims'].remove('oid')
    got = by(lint(tmp_path, d), 'L7')
    assert [(f['target'], f['severity']) for f in got] == [('C-entra-oid', 'warn')]  # new part of L7: warn


def test_l7_required_idp_claim_must_reject_when_missing(tmp_path):
    d = base()
    claim(d, 'C-okta-uid')['on_missing'] = '無視'
    assert [f['target'] for f in by(lint(tmp_path, d), 'L7', 'error')] == ['C-okta-uid']


def test_identifier_row_of_an_idp_claim_needs_identifier_properties(tmp_path):
    d = base()
    del claim(d, 'C-okta-uid')['identifier_properties']
    assert any('identifier_properties' in f['message'] for f in by(lint(tmp_path, d), 'SCHEMA', 'error'))


def test_consumer_schema_of_the_idp_token_requires_the_idp_claims():
    d = render.load_design(FIXTURE)
    tts = {t['id']: t for t in render._tts(d)}
    entra = render.payload_schema(d, tts['ENTRA_AT'], 'consumer')
    assert {'tid', 'oid', 'scp'} <= set(entra['required']) and {'tid', 'oid', 'scp'} <= set(entra['properties'])
    cognito = render.payload_schema(d, tts['COGNITO_AT'], 'consumer')
    assert 'aud' not in cognito['required'] and {'client_id', 'token_use'} <= set(cognito['required'])
    assert 'cognito:groups' in cognito['properties'] and 'cognito:groups' not in cognito['required']
    # before: the pilot's Cognito schema required nothing the entry relies on
    p = render.load_design(PILOT)
    assert render.payload_schema(p, {t['id']: t for t in render._tts(p)}['COGNITO_AT'], 'consumer')['required'] == []


def test_l74_finds_an_idp_claim_checked_at_a_hop_without_a_row(tmp_path, migrated):
    assert by(migrated, 'L74') == [] and migrated['checked']['L74'] == 6  # the six entry hops (Auth0 has a list too)
    d = base()
    d['claims']['claims'] = [c for c in d['claims']['claims'] if c['id'] != 'C-okta-uid']
    hop(d, 'H4')['custom_claims'].remove('C-okta-uid')
    tt(d, 'OKTA_AT')['required_claims'].remove('uid')
    got = by(lint(tmp_path, d), 'L74')
    assert [(f['target'], f['severity']) for f in got] == [('hop H4', 'warn')] and ' uid ' in got[0]['message']


def test_l74_on_the_pilot_once_its_idps_are_declared(tmp_path):
    """Findings B-R1 F01 and B-R2 R2-03 of the pilot (the IdP claims the entry matches on have no on_missing): the pilot's
    registry with nothing changed but the idp list. L74 names the claims; with one IdP it could not (0 findings)."""
    assert by(core.run(PILOT, today=TODAY), 'L74') == []
    d = pilot()
    d['catalog_answers']['idp'] = copy.deepcopy(_BASE['catalog_answers']['idp'])
    got = {(f['target'], f['message'].split('クレーム ')[1].split(' ')[0]) for f in by(lint(tmp_path, d), 'L74', 'warn')}
    assert got == {('hop H3', 'tid'), ('hop H3', 'oid'), ('hop H3', 'scp'), ('hop H4', 'uid'), ('hop H4', 'cid'), ('hop H4', 'scp'),
                   ('hop H5', 'token_use')}


def test_l74_does_not_match_everyday_words_but_reads_the_auth0_list(tmp_path):
    d = base()  # false positives found in the check of PR #70
    hop(d, 'H3')['validates']['checks'].append('idp ごとの JWKS で署名を検証する。ver が 2.0 であること')
    hop(d, 'H5')['validates']['checks'].append('username と version は使わない')
    assert by(lint(tmp_path, d), 'L74') == []
    d = base()  # Auth0's RBAC permissions (top-level, not namespaced) read at the entry without a row
    hop(d, 'H6')['validates']['checks'].append('permissions に read:orders があること')
    got = by(lint(tmp_path, d), 'L74', 'warn')
    assert [f['target'] for f in got] == ['hop H6'] and 'auth0' in got[0]['message']


def test_l74_is_a_new_rule_and_starts_as_warn():
    assert semantic.SEV['L74'] == 'warn'


def test_pinned_idp_names_have_a_source_and_are_not_registered_names():
    doc = core.load_yaml(os.path.join(TOOLS, 'claim_lint', 'idp_claims.yaml'))
    iana = {x['name'] for x in core.load_yaml(os.path.join(TOOLS, 'claim_lint', 'iana_jwt_claims.yaml'))['claims']}
    assert set(doc['idps']) == {'entra', 'okta', 'cognito', 'keycloak', 'auth0'}
    for name, block in doc['idps'].items():
        src = block['source']
        assert src['url'].startswith('https://') and src['verified_on'] and src['review_by'], name
        assert block['claims'] and not set(block['claims']) & iana, name


# ------------------------------------------------------------------ 3: a reissue hop with several upstream hops (L16, REF)
def test_l16_checks_the_reissue_hops_against_every_upstream_hop(migrated):
    info = by(migrated, 'L16')
    assert {f['severity'] for f in info} == {'info'}
    assert len([f for f in info if 'added_claims' in f['message']]) == 2
    # each aud that an aud_mapping ties to an upstream value is reported (H3-H6 for H7 and for H8)
    assert len([f for f in info if 'aud_mapping' in f['message']]) == 8
    assert migrated['checked']['L16'] == 10 and migrated['checked']['L16.widen'] == 10  # H7 and H8, five upstream hops each
    assert 'L16' not in core.run(PILOT, today=TODAY)['checked']  # before: no upstream, so nothing was compared


def test_l16_claims_missing_upstream_are_still_an_error_without_added_claims(tmp_path):
    d = base()
    del hop(d, 'H7')['added_claims']
    got = by(lint(tmp_path, d), 'L16', 'error')
    assert len(got) == 5 and all(f['target'] == 'hop H7' and 'C-department・C-roles' in f['message'] for f in got)


@pytest.mark.parametrize('mutate,word', [
    (lambda d: hop(d, 'H7').update(kind='service'), 'だけに書ける'),
    (lambda d: hop(d, 'H7').update(exchanger=None), 'だけに書ける'),
    (lambda d: hop(d, 'H7')['added_claims'].append({'claim': 'C-employee-id', 'source': 'external_source', 'system': '社員台帳',
                                                    'reason': '社員番号を社員台帳から引いて足す'}), 'custom_claims にない'),
    (lambda d: hop(d, 'H7')['added_claims'][0].update({'from': ['C-azp']}) or hop(d, 'H2')['custom_claims'].remove('C-azp'),
     'どの上流のホップの custom_claims にもない'),
    (lambda d: claim(d, 'C-department').update(carried_in=[]), '載る行でない'),
])
def test_l16_added_claims_conditions(tmp_path, mutate, word):
    d = base()
    mutate(d)
    assert any(word in f['message'] for f in by(lint(tmp_path, d), 'L16', 'error'))


def test_l16_derived_claim_needs_a_source_on_every_upstream_hop(tmp_path):
    d = base()
    hop(d, 'H4')['custom_claims'].remove('C-groups')  # the Okta hop then carries nothing roles could come from
    got = by(lint(tmp_path, d), 'L16', 'warn')
    assert sorted(f['target'] for f in got) == ['hop H7', 'hop H8'] and all('H4' in f['message'] for f in got)


def test_l16_lifetime_and_aud_of_the_reissue_are_compared_again(tmp_path):
    d = base()
    hop(d, 'H7')['max_lifetime'] = 400  # longer than the 300 s of four upstream tokens (Entra: 600)
    got = by(lint(tmp_path, d), 'L16', 'warn')
    assert len(got) == 4 and all('寿命 400 秒' in f['message'] for f in got)
    d = base()
    hop(d, 'H8')['aud'] = ['invoices', 'payroll']
    got = by(lint(tmp_path, d), 'L16', 'warn')
    assert len(got) == 5 and all('payroll' in f['message'] and 'invoices' not in f['message'].split('が上流')[0] for f in got)


def test_l16_aud_mapping_must_point_at_a_real_upstream_value(tmp_path):
    d = base()
    hop(d, 'H7')['aud_mapping'][0]['value'] = 'api://payroll'   # H3 has no such aud
    hop(d, 'H7')['aud_mapping'][1]['value'] = 'payroll'         # H4 has no such scope
    got = by(lint(tmp_path, d), 'L16', 'warn')
    assert sorted(f['message'].split('上流（')[1][:2] for f in got) == ['H3', 'H4']
    d = base()
    del hop(d, 'H7')['aud_mapping']
    assert len(by(lint(tmp_path, d), 'L16', 'warn')) == 4  # H3-H6 name the audience differently; H2 has orders itself
    d = base()
    hop(d, 'H7')['aud_mapping'].append({'upstream': 'H9', 'aud': 'orders', 'via': 'aud', 'value': 'https://graph.microsoft.com'})
    assert any('H9' in f['message'] for f in by(lint(tmp_path, d), 'L16', 'warn'))


def test_l16_aud_mapping_cannot_add_audiences_beyond_the_destination(tmp_path):
    """Check of PR #70: every new aud mapped to the one upstream scope. Only the hop's destination can be mapped."""
    d = base()
    h = hop(d, 'H7')
    h['aud'] = ['orders', 'admin-api']
    tt(d, 'INTERNAL_TOKEN')['aud'].append('admin-api')
    for u in ('H2', 'H3', 'H4', 'H5', 'H6'):
        h['aud_mapping'].append({'upstream': u, 'aud': 'admin-api', 'via': 'scope', 'value': 'orders'})
    got = [f for f in by(lint(tmp_path, d), 'L16', 'warn') if f['target'] == 'hop H7']
    assert len(got) == 5 and all('admin-api' in f['message'] for f in got)


def test_l16_authority_claims_added_from_outside_the_tokens_are_reported(tmp_path):
    d = base()  # roles from a system "x" with a reason: accepted as added (as declared), but never silently
    hop(d, 'H7')['added_claims'][0] = {'claim': 'C-roles', 'source': 'external_source', 'system': 'x', 'reason': 'ロールを足す。理由は書かない'}
    got = [f for f in by(lint(tmp_path, d), 'L16', 'warn') if f['target'] == 'hop H7']
    assert len(got) == 1 and '権限のクレーム' in got[0]['message']
    d = base()  # an authz claim whose system is not the source the registry row names
    hop(d, 'H7')['added_claims'][1]['system'] = '入口の設定ファイル'
    got = [f for f in by(lint(tmp_path, d), 'L16', 'warn') if f['target'] == 'hop H7']
    assert len(got) == 1 and 'source_system' in got[0]['message']


def test_l16_added_claims_without_upstream_is_not_silently_accepted(tmp_path):
    d = base()
    del hop(d, 'H7')['upstream']  # the pilot's workaround, with the new columns left in
    got = by(lint(tmp_path, d), 'L16')
    assert [(f['target'], f['severity']) for f in got if f['target'] == 'hop H7'] == [('hop H7', 'warn')]


def test_ref_upstream_list(tmp_path):
    d = base()
    hop(d, 'H7')['upstream'].append('H99')
    assert any('H99' in f['message'] for f in by(lint(tmp_path, d), 'REF', 'error'))
    d = base()
    hop(d, 'H2')['upstream'] = ['H7']
    assert any('循環' in f['message'] for f in by(lint(tmp_path, d), 'REF', 'error'))
    d = base()
    hop(d, 'H7')['added_claims'][0]['from'].append('C-no-such')
    assert any('C-no-such' in f['message'] for f in by(lint(tmp_path, d), 'REF', 'error'))


def test_hops_schema_upstream_is_one_id_or_a_list():
    with open(os.path.join(ROOT, 'templates', 'registry', 'hops.schema.json'), encoding='utf-8') as f:
        v = jsonschema.Draft202012Validator(json.load(f)['$defs']['hop']['properties']['upstream'])
    assert v.is_valid('H1') and v.is_valid(['H1', 'H2'])
    assert not v.is_valid([]) and not v.is_valid(['H1', 'H1']) and not v.is_valid('orders') and not v.is_valid(3)


# ------------------------------------------------------------------ 4: an access token without aud (L27)
def test_l27_cognito_access_token_passes_with_audience_claim(migrated):
    got = [f for f in by(migrated, 'L27') if f['target'] == 'token_type COGNITO_AT']
    assert [f['severity'] for f in got] == ['info'] and 'client_id' in got[0]['message']


@pytest.mark.parametrize('mutate,word', [
    (lambda d: tt(d, 'COGNITO_AT').pop('audience_claim'), 'aud がない'),
    (lambda d: tt(d, 'COGNITO_AT')['required_claims'].remove('client_id'), 'required_claims に client_id がない'),
    (lambda d: tt(d, 'COGNITO_AT').update(audience_claim='token_use'), 'audience_claim に token_use がない'),
    (lambda d: idp(d, 'cognito')['token_types'].remove('COGNITO_AT'), '宣言なし'),
])
def test_l27_audience_claim_conditions(tmp_path, mutate, word):
    d = base()
    mutate(d)
    got = [f for f in by(lint(tmp_path, d), 'L27', 'error') if f['target'] == 'token_type COGNITO_AT']
    assert got and any(word in f['message'] for f in got), got


def test_l27_audience_claim_is_refused_for_at_jwt_even_with_a_recorded_deviation(tmp_path):
    """Mutation gap of the check of PR #70: an at+jwt type that Cognito issues, with the missing aud recorded as a
    rejected row (which turns the RFC 9068 REQUIRED finding into info). audience_claim must still be refused."""
    d = base()
    tt(d, 'COGNITO_AT')['typ'] = 'at+jwt'
    rej = copy.deepcopy(claim(d, 'C-email'))
    rej.update(id='C-aud-not-in-cognito', name='aud')
    d['claims']['claims'].append(rej)
    got = [f for f in by(lint(tmp_path, d), 'L27', 'error') if f['target'] == 'token_type COGNITO_AT']
    assert any('audience_claim client_id を aud の代わりにできない' in f['message'] and 'at+jwt' in f['message'] for f in got), got


def test_l27_aud_stays_required_when_an_idp_with_aud_also_issues_the_type(tmp_path):
    """Check of PR #70, B1: KC_AT listed under cognito as well does not lose aud."""
    d = base()
    t = tt(d, 'KC_AT')
    t['audience_claim'] = 'client_id'
    t['required_claims'].remove('aud')
    t['required_claims'].append('client_id')
    idp(d, 'cognito')['token_types'].append('KC_AT')
    c = claim(d, 'C-client-id')
    c['carried_in'].append('KC_AT')
    c['issuers'].append('https://kc.corp.example.com/realms/corp')
    claim(d, 'C-aud')['carried_in'].remove('KC_AT')
    hop(d, 'H2')['custom_claims'].append('C-client-id')
    res = lint(tmp_path, d)
    got = [f['message'] for f in by(res, 'L27', 'error') if f['target'] == 'token_type KC_AT']
    assert len(got) == 2 and any('keycloak' in m for m in got) and any('aud がない' in m for m in got)
    assert not [f for f in by(res, 'L27', 'info') if f['target'] == 'token_type KC_AT']
    assert any('KC_AT' in f['message'] and f['severity'] == 'warn' for f in by(res, 'R3'))  # an AT type under two IdPs


def test_l27_cognito_token_with_aud_keeps_aud_required(tmp_path):
    """A Cognito access token bound to a resource has aud: the design says so through the hop's aud or an aud row."""
    d = base()
    hop(d, 'H5')['aud'] = ['https://api.example.com']
    got = [f for f in by(lint(tmp_path, d), 'L27', 'error') if f['target'] == 'token_type COGNITO_AT']
    assert got and any('aud を持つ' in f['message'] for f in got)
    d = base()
    claim(d, 'C-aud')['carried_in'].append('COGNITO_AT')
    got = [f for f in by(lint(tmp_path, d), 'L27', 'error') if f['target'] == 'token_type COGNITO_AT']
    assert got and any('C-aud' in f['message'] for f in got)


def test_l27_audience_claim_is_only_for_an_idp_whose_token_has_no_aud(tmp_path):
    d = base()
    t = tt(d, 'OKTA_AT')
    t['required_claims'].remove('aud')
    t['audience_claim'] = 'cid'
    got = [f for f in by(lint(tmp_path, d), 'L27', 'error') if f['target'] == 'token_type OKTA_AT']
    assert len(got) == 2  # the audience_claim is refused, and aud is still missing


# ------------------------------------------------------------------ 5: the same header typ (L17)
def test_l17_same_typ_told_apart_by_payload_values(migrated):
    got = by(migrated, 'L17')
    assert [(f['target'], f['severity']) for f in got] == [('KC_AT・ENTRA_AT・GRAPH_AT・ID_TOKEN・CLIENT_ASSERTION', 'info')]


def test_l17_without_kind_discriminator_is_the_error_the_pilot_met(tmp_path):
    d = base()
    del tt(d, 'ID_TOKEN')['kind_discriminator']
    got = by(lint(tmp_path, d), 'L17', 'error')
    assert len(got) == 1 and 'kind_discriminator が無い種別：ID_TOKEN' in got[0]['message']
    d = pilot()  # the pilot's rows with typ written as the plain header value
    for t in ('KC_AT', 'ENTRA_AT', 'ID_TOKEN'):
        tt(d, t)['typ'] = 'JWT'
    got = by(lint(tmp_path, d), 'L17', 'error')
    assert len(got) == 1 and 'kind_discriminator' not in got[0]['message']


def test_l17_stays_an_error_when_the_declarations_do_not_prove_the_kinds_apart(tmp_path):
    d = base()
    tt(d, 'ID_TOKEN')['aud'] = ['portal', 'orders']  # overlaps the aud of KC_AT
    res = lint(tmp_path, d)
    got = by(res, 'L17', 'error')  # not proven apart: the error stays an error (no downgrade)
    assert len(got) == 1 and 'KC_AT／ID_TOKEN' in got[0]['message'] and 'ENTRA_AT／ID_TOKEN' not in got[0]['message']
    assert by(res, 'L17', 'info') == [] and by(res, 'L17', 'warn') == []


@pytest.mark.parametrize('entry,word', [
    ({'claim': 'no_such_claim', 'value': 'x'}, '台帳の行'),
    ({'claim': 'azp'}, 'value'),
])
def test_l17_discriminator_entries_are_checked(tmp_path, entry, word):
    d = base()
    tt(d, 'KC_AT')['kind_discriminator'].append(entry)
    got = [f for f in by(lint(tmp_path, d), 'L17', 'warn') if f['target'] == 'token_type KC_AT']
    assert got and word in got[0]['message']


JWT_TYPES = ('KC_AT', 'ENTRA_AT', 'GRAPH_AT', 'ID_TOKEN', 'CLIENT_ASSERTION')


@pytest.mark.parametrize('entries', [
    [{'claim': 'foo'}],                    # says nothing
    [{'claim': 'iss', 'value': 'same'}],   # the same value on every row
    [{'claim': 'no_row', 'value': 'a'}],   # replaced per row below with different values, but no registry row
])
def test_l17_a_declaration_that_does_not_discriminate_keeps_the_error(tmp_path, entries):
    """Check of PR #70, B2: a kind_discriminator on every row used to turn the error into warnings."""
    d = base()
    for i, t in enumerate(JWT_TYPES):
        e = copy.deepcopy(entries)
        if e[0].get('claim') == 'no_row':
            e[0]['value'] = f'v{i}'
        tt(d, t)['kind_discriminator'] = e
    res = lint(tmp_path, d)
    got = by(res, 'L17', 'error')
    assert len(got) == 1 and '排他と言えない' in got[0]['message'] and by(res, 'L17', 'info') == []


def _overlapping_aud(d):
    tt(d, 'ID_TOKEN')['aud'] = ['orders', 'invoices', 'api://orders', 'api://invoices']  # control: L17 error


@pytest.mark.parametrize('at_entry,idt_entry', [
    ({'claim': 'iat', 'value': 1}, {'claim': 'iat', 'value': '1'}),                    # a time claim, and 1 against "1"
    ({'claim': 'iss', 'value': 'https://nowhere-a.example'}, {'claim': 'iss', 'value': 'https://nowhere-b.example'}),
    ({'claim': 'sub', 'value': 'a'}, {'claim': 'sub', 'value': 'b'}),                  # a row exists, but declares no values
    ({'claim': 'typ', 'value': 'Bearer'}, {'claim': 'typ', 'value': 'JWT-ID'}),         # not a value the row declares
    (None, None),
])
def test_l17_a_made_up_value_does_not_prove_the_kinds_apart(tmp_path, at_entry, idt_entry):
    """Re-check of PR #70: with overlapping aud the kinds are not apart; a value on a claim that merely has a row brought
    the info back. A value counts only when the registry row declares it (iss: the issuers of the token type)."""
    d = base()
    _overlapping_aud(d)
    if at_entry:
        for t in ('KC_AT', 'ENTRA_AT'):
            tt(d, t)['kind_discriminator'] = [e for e in tt(d, t)['kind_discriminator'] if e['claim'] != at_entry['claim']] + [at_entry]
        tt(d, 'ID_TOKEN')['kind_discriminator'].append(idt_entry)
        if at_entry['claim'] == 'typ':  # give the ID token a typ row whose values do not include the made-up one
            row = copy.deepcopy(claim(d, 'C-kc-typ'))
            row.update(id='C-kc-typ-idt', carried_in=['ID_TOKEN'], consumers=[], allowed_values={'enum': ['ID']})
            row['issuers'] = [i['iss'] for i in tt(d, 'ID_TOKEN')['issuers']]
            d['claims']['claims'].append(row)
    res = lint(tmp_path, d)
    got = by(res, 'L17', 'error')
    assert len(got) == 1 and '排他と言えない' in got[0]['message'] and by(res, 'L17', 'info') == []


def test_l17_value_grounding_one_condition_at_a_time(tmp_path):
    """Only KC_AT and the ID token overlap, and both carry sub and iat with on_missing 拒否, so each condition decides alone."""
    def design(kc, idt, enum=None):
        d = base()
        tt(d, 'ID_TOKEN')['aud'] = ['orders', 'portal']
        tt(d, 'KC_AT')['kind_discriminator'] = [{'claim': 'aud'}, kc]
        tt(d, 'ID_TOKEN')['kind_discriminator'].append(idt)
        if enum:
            claim(d, 'C-iat')['allowed_values'] = {'enum': enum}
        return d
    # a value the row does not declare
    res = lint(tmp_path, design({'claim': 'sub', 'value': 'a'}, {'claim': 'sub', 'value': 'b'}))
    assert len(by(res, 'L17', 'error')) == 1 and 'C-sub' in by(res, 'L17', 'error')[0]['message']
    # a time claim, even when the row declares the values
    res = lint(tmp_path, design({'claim': 'iat', 'value': 1}, {'claim': 'iat', 'value': 2}, enum=[1, 2]))
    assert len(by(res, 'L17', 'error')) == 1 and 'トークンごとに変わる値' in by(res, 'L17', 'error')[0]['message']


def test_l17_a_value_the_registry_declares_proves_the_kinds_apart(tmp_path):
    d = base()  # the same overlap, told apart by Keycloak's payload typ: Bearer (C-kc-typ) against ID (a row for the ID token)
    tt(d, 'ID_TOKEN')['aud'] = ['orders', 'invoices', 'portal']
    row = copy.deepcopy(claim(d, 'C-kc-typ'))
    row.update(id='C-kc-typ-idt', carried_in=['ID_TOKEN'], consumers=[], allowed_values={'enum': ['ID']})
    row['issuers'] = [i['iss'] for i in tt(d, 'ID_TOKEN')['issuers']]
    d['claims']['claims'].append(row)
    tt(d, 'ID_TOKEN')['kind_discriminator'].append({'claim': 'typ', 'value': 'ID'})
    res = lint(tmp_path, d)
    assert by(res, 'L17', 'error') == [] and len(by(res, 'L17', 'info')) == 1


def test_l17_absent_that_contradicts_the_token_type_is_an_error(tmp_path):
    """Check of PR #70, B3: aud declared absent on types that require aud."""
    d = base()
    for t in ('KC_AT', 'ENTRA_AT', 'GRAPH_AT'):
        tt(d, t)['kind_discriminator'] = [{'claim': 'aud', 'absent': True}]
    res = lint(tmp_path, d)
    contra = [f['target'] for f in by(res, 'L17', 'error') if '矛盾' in f['message']]
    assert contra == ['token_type KC_AT', 'token_type ENTRA_AT']  # required_claims / a registry row; GRAPH_AT has neither
    assert any('排他と言えない' in f['message'] for f in by(res, 'L17', 'error')) and by(res, 'L17', 'info') == []
    d = base()  # a row carried in the type, not in required_claims
    tt(d, 'ID_TOKEN')['kind_discriminator'].append({'claim': 'nonce', 'absent': True})
    assert [f['target'] for f in by(lint(tmp_path, d), 'L17', 'error') if '矛盾' in f['message']] == ['token_type ID_TOKEN']


def test_l17_discriminator_claim_must_reject_when_missing(tmp_path):
    d = base()
    claim(d, 'C-kc-typ')['on_missing'] = '無視'
    tt(d, 'KC_AT')['required_claims'].remove('typ')
    got = [f for f in by(lint(tmp_path, d), 'L17', 'warn') if f['target'] == 'token_type KC_AT']
    assert got and 'on_missing' in got[0]['message']


@pytest.mark.parametrize('a,b,want', [
    ([{'claim': 'typ', 'value': 'Bearer'}], [{'claim': 'typ', 'value': 'ID'}], True),
    ([{'claim': 'typ', 'value': 'Bearer'}], [{'claim': 'typ', 'value': 'Bearer'}], False),
    ([{'claim': 'token_use', 'value': 'access'}], [{'claim': 'token_use', 'absent': True}], True),
    ([{'claim': 'aud', 'absent': True}], [{'claim': 'aud'}], True),            # the other row has an aud column
    ([{'claim': 'aud', 'absent': True}], [{'claim': 'aud', 'absent': True}], False),
    ([{'claim': 'aud'}], [{'claim': 'aud'}], True),                            # aud columns a / b do not overlap
    ([{'claim': 'typ', 'value': 'Bearer'}], [{'claim': 'aud'}], False),        # no claim in common
])
def test_l17_mutually_exclusive(a, b, want):
    ta = {'id': 'A', 'aud': ['api'], 'kind_discriminator': a}
    tb = {'id': 'B', 'aud': ['client'], 'kind_discriminator': b}
    assert semantic._kd_exclusive(ta, tb) is want and semantic._kd_exclusive(tb, ta) is want


def test_l17_aud_columns_that_overlap_or_are_empty_prove_nothing():
    a = {'id': 'A', 'aud': ['api'], 'kind_discriminator': [{'claim': 'aud'}]}
    assert not semantic._kd_exclusive(a, {'id': 'B', 'aud': ['api', 'x'], 'kind_discriminator': [{'claim': 'aud'}]})
    assert not semantic._kd_exclusive(a, {'id': 'B', 'aud': [], 'kind_discriminator': [{'claim': 'aud'}]})
    assert not semantic._kd_exclusive({'id': 'A', 'aud': [], 'kind_discriminator': [{'claim': 'aud'}]},
                                      {'id': 'B', 'aud': ['x'], 'kind_discriminator': [{'claim': 'aud', 'absent': True}]})


# ------------------------------------------------------------------ 6: per-IdP exceptions of the issuance profile (L62)
def test_profile_exception_is_schema_checked_and_needs_a_declared_idp(tmp_path, migrated):
    assert not [f for f in migrated['findings'] if f['target'].startswith('issuance_profile.')]
    d = base()
    d['token_types']['issuance_profile']['client_auth']['exceptions'][0]['value'] = 'password'
    assert any('exceptions' in f['target'] for f in by(lint(tmp_path, d), 'SCHEMA', 'error'))
    d = base()
    d['token_types']['issuance_profile']['client_auth']['exceptions'][0]['idp'] = 'ping'
    assert [f['target'] for f in by(lint(tmp_path, d), 'L62', 'warn')] == ['issuance_profile.client_auth']
    d = base()
    d['token_types']['issuance_profile']['client_auth']['exceptions'][0]['value'] = 'private_key_jwt'
    assert any('例外でない' in f['message'] for f in by(lint(tmp_path, d), 'L62', 'warn'))


ALL_IDPS = ('keycloak', 'entra', 'okta', 'cognito', 'auth0')


def test_profile_check_reads_the_effective_value_of_every_idp(tmp_path):
    """Check of PR #70, B4: value satisfies the requirement, the exceptions do not."""
    prof = lambda d: d['token_types']['issuance_profile']  # noqa: E731
    d = base()  # (a) FAPI 2.0 needs a sender constraint: value dpop, okta none
    prof(d)['conformance_profile']['value'] = 'fapi2_security'
    prof(d)['sender_constraint']['value'] = 'dpop'
    prof(d)['sender_constraint']['exceptions'] = [{'idp': 'okta', 'value': 'none', 'rationale': 'Okta では送信者制約を使わない'}]
    assert [f for f in by(lint(tmp_path, d), 'L63', 'warn') if f['target'] == 'E-fapi2.1']
    d = base()  # control: without the exception the requirement is met
    prof(d)['conformance_profile']['value'] = 'fapi2_security'
    prof(d)['sender_constraint']['value'] = 'dpop'
    assert not [f for f in by(lint(tmp_path, d), 'L63') if f['target'] == 'E-fapi2.1']
    d = base()  # (b) a public client needs PKCE: value has it, one IdP's exception drops it
    prof(d)['client_type']['value'] = 'public'
    prof(d)['grants']['exceptions'] = [{'idp': 'okta', 'value': ['refresh_token', 'device_code'], 'rationale': 'Okta では PKCE を使わない'}]
    assert [f for f in by(lint(tmp_path, d), 'L62', 'warn') if f['target'] == 'E-public-pkce.1']
    sec = render.sec_issuance_profile(render.load_design(str(tmp_path / 'design')))
    req = next(r for e in sec['effects'] if e['id'] == 'E-public-pkce' for r in e['requires'] if r['id'] == 'E-public-pkce.1')
    assert req['status'] == 'unsatisfied'


def test_profile_exceptions_for_every_idp_are_not_exceptions(tmp_path):
    d = base()
    p = d['token_types']['issuance_profile']['sender_constraint']
    p['value'] = 'dpop'
    p['exceptions'] = [{'idp': n, 'value': 'none', 'rationale': 'この IdP では送信者制約を使わない'} for n in ALL_IDPS]
    got = [f for f in by(lint(tmp_path, d), 'L62', 'error') if f['target'] == 'issuance_profile.sender_constraint']
    assert len(got) == 1 and 'value を変える' in got[0]['message']
    d = base()
    d['token_types']['issuance_profile']['client_auth']['exceptions'].append(
        {'idp': 'cognito', 'value': 'client_secret_post', 'rationale': '同じ IdP の例外を 2 回書く'})
    assert any('2 回' in f['message'] for f in by(lint(tmp_path, d), 'L62', 'warn'))


def test_profile_exception_makes_the_requirements_of_that_choice_apply(tmp_path, migrated):
    """E-dpop does not hold for the design (sender_constraint: none). With DPoP as the exception of one IdP it does."""
    assert not [f for f in by(migrated, 'L62') if str(f['target']).startswith('E-dpop')]
    d = base()
    d['token_types']['issuance_profile']['sender_constraint']['exceptions'] = [
        {'idp': 'okta', 'value': 'dpop', 'rationale': 'Okta のアプリだけ DPoP を必須にしている'}]
    res = lint(tmp_path, d)
    assert [f for f in by(res, 'L62', 'warn') if str(f['target']).startswith('E-dpop')]
    sec = render.sec_issuance_profile(render.load_design(str(tmp_path / 'design')))
    row = next(r for r in sec['tables'][0]['rows'] if r['field'] == 'sender_constraint')
    assert '例外：okta は' in row['value_text'] and '【okta の例外】' in row['rationale']
    assert next(e for e in sec['effects'] if e['id'] == 'E-dpop')['holds']


# ------------------------------------------------------------------ render and drift
def test_render_marks_the_claims_the_reissue_adds():
    rows = {r['id']: r for r in render.sec_hop_table(render.load_design(FIXTURE))['tables'][0]['rows']}
    assert any('（足す：社員台帳（人事システム））' in x for x in rows['H8']['custom_claims'])
    assert any('（足す：上流のクレームから導く）' in x for x in rows['H7']['custom_claims'])
    assert rows['H7']['upstream'] == ['H2', 'H3', 'H4', 'H5', 'H6'] and not any('足す' in x for x in rows['H2']['custom_claims'])


def test_drift_compares_only_the_token_types_of_the_keycloak_entry():
    d = render.load_design(FIXTURE)
    assert [t['id'] for t in drift._kc_tts(d)] == ['KC_AT', 'ID_TOKEN']
    p = render.load_design(PILOT)  # one IdP: every access token and ID token, as before
    assert [t['id'] for t in drift._kc_tts(p)] == ['KC_AT', 'ENTRA_AT', 'OKTA_AT', 'COGNITO_AT', 'AUTH0_AT', 'GRAPH_AT', 'ID_TOKEN']


def test_idp_entries_reads_both_forms():
    one, problems, is_list = coverage.idp_entries({'idp': {'name': 'Keycloak', 'version': '26.8'}})
    assert [(e['name'], e['target'], e['token_types']) for e in one] == [('keycloak', 'idp', None)] and not problems and not is_list
    assert coverage.idp_name({'idp': 'Auth0'}) == 'auth0' and coverage.idp_name({}) is None
    many, problems, is_list = coverage.idp_entries(_BASE['catalog_answers'])
    assert is_list and not problems and [e['target'] for e in many][:2] == ['idp[keycloak]', 'idp[entra]']
    assert coverage.idp_token_types(_BASE['catalog_answers'], 'okta') == {'OKTA_AT', 'ID_TOKEN', 'REFRESH_TOKEN'}
    assert coverage.idp_name(_BASE['catalog_answers']) == 'keycloak'
