# -*- coding: utf-8 -*-
"""Tests of the claim_lint semantic rules (#6): a pass case and a fail case for every rule, the pass cases named in the
issue (L1a: roles used as registered, L4: a Cognito hook that adds and suppresses scope, L9: tenants separated by iss),
the L16 fail case measured in the casestudy (Keycloak 26.8 exchange that produced an orders audience,
slide:p10-token-exchange-not-narrowing), and the true positives of the review of scenario A (#16, gate1.md 5.) as fail
fixtures: A01 (L23, L31), A07 (L27), A08 (L7), A09 (L17), A14 (L23), A17 (L73)."""
import copy
import datetime
import os
import shutil
import sys

import pytest
import yaml

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from claim_lint import core, semantic  # noqa: E402

EXAMPLE = os.path.join(ROOT, 'templates', 'examples', 'scenario-a')
FILES = ('claims', 'token_types', 'catalog_answers', 'hops')
TODAY = datetime.date(2026, 11, 23)
_BASE = {k: core.load_yaml(os.path.join(EXAMPLE, k + '.yaml')) for k in FILES}


def base():
    return copy.deepcopy(_BASE)


def lint(tmp_path, docs, profile='full', md=True):
    d = tmp_path / 'design'
    d.mkdir(parents=True, exist_ok=True)
    for k, v in docs.items():
        with open(d / (k + '.yaml'), 'w', encoding='utf-8') as f:
            yaml.safe_dump(v, f, allow_unicode=True, sort_keys=False)
    if md:
        for n in os.listdir(EXAMPLE):
            if n.startswith('claim_request_'):
                shutil.copy(os.path.join(EXAMPLE, n), d / n)
    return core.run(str(d), profile=profile, today=TODAY)


def by(res, rule, severity=None):
    return [f for f in res['findings'] if f['rule'] == rule and (severity is None or f['severity'] == severity)]


def bad(res, rule):
    return [f for f in by(res, rule) if f['severity'] in ('error', 'warn')]


def claim(docs, cid):
    return next(c for c in docs['claims']['claims'] if c['id'] == cid)


def tt(docs, tid):
    return next(t for t in docs['token_types']['token_types'] if t['id'] == tid)


def hop(docs, hid):
    return next(h for h in docs['hops']['hops'] if h['id'] == hid)


def new_claim(**kw):
    c = copy.deepcopy(claim(_BASE, 'C-v'))
    c.pop('answers', None)
    c.update(kw)
    return c


@pytest.fixture(scope='module')
def example():
    return core.run(EXAMPLE, today=TODAY)


# ------------------------------------------------------------------ the worked example
def test_example_has_no_semantic_error(example):
    errs = [f for f in example['findings'] if f['rule'] in semantic.SEV and f['severity'] == 'error']
    assert not errs, core.format_table(example)


def test_example_known_semantic_warnings(example):
    # the 3 shared claims without the 25 answers (L72, true positives left for #4: claim_request.md)
    got = sorted((f['rule'], f['target']) for f in example['findings'] if f['rule'] in semantic.SEV and f['severity'] == 'warn')
    assert got == [('L72', 'C-roles'), ('L72', 'C-user-id'), ('L72', 'C-v')]


def test_example_checked_counts(example):
    """The rules that are error ran on at least one row of scenario A (RULES.md: no promotion without an opportunity)."""
    ch = example['checked']
    for rule, sev in semantic.SEV.items():
        if sev == 'error':
            assert ch.get(rule, 0) > 0, rule


# ------------------------------------------------------------------ L1a
def test_l1a_registered_roles_pass(tmp_path):
    d = base()
    d['claims']['claims'].append(new_claim(id='C-roles-top', name='roles', namespace=None, shape='array', max_items=2,
                                           registered_ref={'kind': 'spec', 'id': 'RFC 7643 §4.1.2'}))
    assert not bad(lint(tmp_path, d), 'L1a')


def test_l1a_registered_name_without_ref_or_wrong_type_fails(tmp_path):
    d = base()
    claim(d, 'C-sid').pop('registered_ref')
    claim(d, 'C-exp')['type'] = 'string'
    msgs = [f['target'] for f in bad(lint(tmp_path, d), 'L1a')]
    assert 'C-sid' in msgs and 'C-exp' in msgs


# ------------------------------------------------------------------ L1b
def test_l1b_private_name_fails(tmp_path):
    d = base()
    d['claims']['claims'].append(new_claim(id='C-plan', name='plan', namespace=None))
    assert [f['target'] for f in bad(lint(tmp_path, d), 'L1b')] == ['C-plan']


def test_l1b_undeclared_namespace_and_foreign_issuer_fail(tmp_path):
    d = base()
    claim(d, 'C-v')['namespace'] = 'https://other.example.org/'
    claim(d, 'C-roles')['issuers'] = ['https://idp.example.com/realms/t1']  # AT also accepts realm t2
    msgs = ' '.join(f['message'] for f in bad(lint(tmp_path, d), 'L1b'))
    assert 'namespaces に宣言されていない' in msgs and 'realms/t2' in msgs


def test_l1b_same_name_different_meaning_fails(tmp_path):
    d = base()
    d['claims']['claims'].append(new_claim(id='C-v2', name='v', type='integer', description='別の発行者の版'))
    assert any('同じ名前' in f['message'] for f in bad(lint(tmp_path, d), 'L1b'))


def test_l1b_idp_default_private_name_is_info(example):
    assert [f['target'] for f in by(example, 'L1b')] == ['C-typ-claim'] and by(example, 'L1b')[0]['severity'] == 'info'


# ------------------------------------------------------------------ L2
def test_l2_cognito_hook_overwrites_sub_fails(tmp_path):
    d = base()
    d['catalog_answers']['idp'] = {'name': 'cognito'}
    claim(d, 'C-sub')['modifiers'] = [{'stage': '②', 'writer': 'pre token generation Lambda', 'action': '上書き'}]
    assert [f['target'] for f in bad(lint(tmp_path, d), 'L2')] == ['C-sub']


def test_l2_cognito_hook_on_custom_claim_pass(tmp_path):
    d = base()
    d['catalog_answers']['idp'] = {'name': 'cognito'}
    claim(d, 'C-roles')['modifiers'] = [{'stage': '②', 'writer': 'pre token generation Lambda', 'action': '追加'}]
    assert not bad(lint(tmp_path, d), 'L2')


def test_l2_without_list_is_info(example):
    assert [f['severity'] for f in by(example, 'L2')] == ['info']


# ------------------------------------------------------------------ L3
def test_l3_email_as_identifier_fails(tmp_path):
    d = base()
    c = claim(d, 'C-email')
    c['usage'] = 'identifier'
    c['identifier_properties'] = {'stable': False, 'reassignable': True, 'pairwise': False, 'id_scheme': 'email'}
    assert [f['target'] for f in bad(lint(tmp_path, d), 'L3')] == ['C-email']


def test_l3_display_email_pass(example):
    assert not bad(example, 'L3')


# ------------------------------------------------------------------ L4
def test_l4_cognito_hook_adds_and_suppresses_scope_pass(tmp_path):
    d = base()
    claim(d, 'C-scope')['modifiers'] = [{'stage': '②', 'writer': 'pre token generation Lambda', 'action': '追加'},
                                        {'stage': '②', 'writer': 'pre token generation Lambda', 'action': '抑止'}]
    assert not bad(lint(tmp_path, d), 'L4')


def test_l4_two_writers_in_one_stage_fails(tmp_path):
    d = base()
    claim(d, 'C-roles')['authoritative_writer'].append({'stage': '②', 'writer': '発行時のフック'})
    assert [f['target'] for f in bad(lint(tmp_path, d), 'L4')] == ['C-roles']


# ------------------------------------------------------------------ L5
def test_l5_volatile_claim_without_mitigation_fails(tmp_path):
    d = base()
    claim(d, 'C-roles')['volatility'] = 60
    claim(d, 'C-roles')['propagation_delay'] = 60
    assert [f['target'] for f in bad(lint(tmp_path, d), 'L5')] == ['C-roles']


def test_l5_short_lifetime_or_revocation_pass(tmp_path):
    d = base()
    claim(d, 'C-roles')['volatility'] = 60
    claim(d, 'C-roles')['propagation_delay'] = 60
    tt(d, 'AT')['revocation'].append({'method': 'ssf_caep', 'delay_seconds': 30})
    assert not bad(lint(tmp_path, d), 'L5')


def test_l5_propagation_beyond_volatility_fails(tmp_path):
    d = base()
    claim(d, 'C-name')['propagation_delay'] = 90000
    assert [f['target'] for f in bad(lint(tmp_path, d), 'L5')] == ['C-name']


# ------------------------------------------------------------------ L6
def test_l6_personal_data_in_browser_token_fails(tmp_path):
    d = base()
    tt(d, 'IDT')['visible_to'] = ['bff', 'browser']
    tt(d, 'IDT')['stored_at'] = 'browser'
    claim(d, 'C-name')['confidential_from'] = []
    claim(d, 'C-name').pop('confidentiality_measure')
    assert 'C-name' in [f['target'] for f in bad(lint(tmp_path, d), 'L6')]


def test_l6_identifier_logged_in_clear_fails(tmp_path):
    d = base()
    claim(d, 'C-sub')['log_policy'] = '記録する'
    assert [f['target'] for f in bad(lint(tmp_path, d), 'L6')] == ['C-sub']


def test_l6_pass(example):
    assert not bad(example, 'L6')


# ------------------------------------------------------------------ L7 (A08: azp)
def test_l7_required_but_not_reject_fails(tmp_path):
    d = base()
    claim(d, 'C-v')['on_missing'] = '既定値'
    assert [f['target'] for f in bad(lint(tmp_path, d), 'L7')] == ['C-v']


def test_l7_reverse_a08_azp_not_in_required_claims_fails(tmp_path):
    d = base()
    tt(d, 'AT')['required_claims'].remove('azp')  # the state before the review of PR #28 (A08)
    assert [f['target'] for f in bad(lint(tmp_path, d), 'L7')] == ['C-azp']


def test_l7_pass(example):
    assert not bad(example, 'L7')


# ------------------------------------------------------------------ L8
def test_l8_header_without_strip_fails(tmp_path):
    d = base()
    hop(d, 'H2')['forwarded_headers'] = [{'name': 'X-Tenant', 'claim': 'C-tenant-id', 'strip_inbound': False, 'written_only_by': 'nginx'}]
    assert [f['target'] for f in bad(lint(tmp_path, d), 'L8')] == ['hop H2']


def test_l8_header_with_strip_pass(tmp_path):
    d = base()
    hop(d, 'H2')['forwarded_headers'] = [{'name': 'X-Tenant', 'claim': 'C-tenant-id', 'strip_inbound': True, 'written_only_by': 'nginx'}]
    claim(d, 'C-tenant-id')['integrity_until'].append({'place': 'http_header', 'target': 'X-Tenant', 'trust_boundary': 'nginx だけが書く'})
    assert not bad(lint(tmp_path, d), 'L8')


# ------------------------------------------------------------------ L9
def test_l9_tenants_by_iss_pass(tmp_path):
    d = base()
    tt(d, 'AT')['tenant_binding'] = {'by': ['iss']}
    assert not bad(lint(tmp_path, d), 'L9')


def test_l9_no_binding_fails(tmp_path):
    d = base()
    tt(d, 'AT').pop('tenant_binding')
    assert [f['target'] for f in bad(lint(tmp_path, d), 'L9')] == ['token_type AT']


def test_l9_claim_not_checked_against_iss_nor_data_layer_fails(tmp_path):
    d = base()
    c = claim(d, 'C-tenant-id')
    c['enforced_at'] = [e for e in c['enforced_at'] if e['service'] == 'saas-api' and 'iss' not in e.get('against', [])
                        and 'data_layer' not in e.get('against', [])]
    msgs = ' '.join(f['message'] for f in bad(lint(tmp_path, d), 'L9'))
    assert 'iss' in msgs and 'データ層' in msgs


# ------------------------------------------------------------------ L15
def test_l15_public_client_rt_without_rotation_fails(tmp_path):
    d = base()
    d['token_types']['issuance_profile']['client_type']['value'] = 'public'
    assert 'token_type RT' in [f['target'] for f in bad(lint(tmp_path, d), 'L15')]


def test_l15_public_client_with_reuse_detection_pass(tmp_path):
    d = base()
    d['token_types']['issuance_profile']['client_type']['value'] = 'public'
    tt(d, 'RT')['rt_rotation'] = {'rotation': True, 'reuse_detection': 'yes'}
    assert not [f for f in bad(lint(tmp_path, d), 'L15') if f['target'] == 'token_type RT']


def test_l15_cnf_without_consumer_check_fails(tmp_path):
    d = base()
    tt(d, 'AT')['sender_constraint'] = 'dpop'
    assert 'token_type AT' in [f['target'] for f in bad(lint(tmp_path, d), 'L15')]


# ------------------------------------------------------------------ L16 (the Keycloak 26.8 exchange, slide:p10-token-exchange-not-narrowing)
def _exchange(d, aud, scope, lifetime=300, claims=('C-tenant-id',)):
    d['hops']['hops'].append({'id': 'H4', 'from': 'saas-api', 'to': 'orders', 'kind': 'exchange', 'upstream': 'H2', 'token_type': 'AT',
                              'aud': aud, 'scope': scope, 'max_lifetime': lifetime, 'custom_claims': list(claims),
                              'exchanger': 'Keycloak', 'validates': {'mode': 'local', 'checks': ['署名']}})


def test_l16_keycloak_exchange_widens_to_orders_fails(tmp_path):
    d = base()
    hop(d, 'H2').update(aud=['mcp-tools', 'account'], scope=['openid'])
    _exchange(d, ['orders', 'account'], ['aud-orders', 'email', 'profile'])
    msgs = ' '.join(f['message'] for f in bad(lint(tmp_path, d), 'L16'))
    assert 'orders' in msgs and 'aud-orders' in msgs


def test_l16_narrowing_exchange_pass(tmp_path):
    d = base()
    _exchange(d, ['saas-api'], ['openid'], 120)
    assert not bad(lint(tmp_path, d), 'L16')


def test_l16_longer_lifetime_and_extra_claim_fail(tmp_path):
    d = base()
    _exchange(d, ['saas-api'], ['openid'], 600, ('C-tenant-id', 'C-email'))
    msgs = ' '.join(f['message'] for f in bad(lint(tmp_path, d), 'L16'))
    assert '寿命 600' in msgs and 'C-email' in msgs


# ------------------------------------------------------------------ L17 (A09), L25, L27 (A07)
def test_l17_a09_no_refetch_rule_fails(tmp_path):
    d = base()
    tt(d, 'AT').pop('unknown_kid')
    tt(d, 'AT').pop('jwks_cache_ttl')
    assert len(bad(lint(tmp_path, d), 'L17')) == 2


def test_l17_same_typ_for_two_kinds_and_alg_none_fail(tmp_path):
    d = base()
    tt(d, 'IDT')['typ'] = 'at+jwt'
    tt(d, 'IDT')['alg_allowlist'] = ['RS256', 'none']
    msgs = ' '.join(f['message'] for f in bad(lint(tmp_path, d), 'L17'))
    assert 'none' in msgs and '同じ typ' in msgs


def test_l17_l25_l27_pass(example):
    assert not bad(example, 'L17') and not bad(example, 'L25') and not bad(example, 'L27')


def test_l25_no_key_source_fails(tmp_path):
    d = base()
    tt(d, 'IDT').pop('key_source')
    assert [f['target'] for f in bad(lint(tmp_path, d), 'L25')] == ['token_type IDT']


def test_l27_a07_client_id_neither_required_nor_recorded_fails(tmp_path):
    d = base()
    d['claims']['claims'] = [c for c in d['claims']['claims'] if c['id'] != 'C-client-id']
    msgs = [f['message'] for f in bad(lint(tmp_path, d), 'L27')]
    assert len(msgs) == 1 and 'client_id' in msgs[0]


def test_l27_a07_recorded_deviation_is_info(example):
    assert [f['severity'] for f in by(example, 'L27')] == ['info']


def test_l27_skew_and_exp_fail(tmp_path):
    d = base()
    tt(d, 'IDT')['max_clock_skew'] = 900
    tt(d, 'IDT')['required_claims'].remove('exp')
    assert len(bad(lint(tmp_path, d), 'L27')) == 2


# ------------------------------------------------------------------ L18
def test_l18_deprecated_claim_still_read_warns(tmp_path):
    d = base()
    claim(d, 'C-v').update(status='deprecated', sunset_on='2026-01-01')
    f = bad(lint(tmp_path, d), 'L18')
    assert [x['severity'] for x in f] == ['warn'] and '過ぎても' in f[0]['message']


def test_l18_pass(example):
    assert not bad(example, 'L18')


# ------------------------------------------------------------------ L21, L22, L23 (A01, A14)
def test_l21_rejected_type_referenced_and_unused_adopted(tmp_path):
    d = base()
    claim(d, 'C-v')['carried_in'] = ['AT', 'TXN']
    d['token_types']['token_types'].append(dict(tt(d, 'CODE'), id='CODE2'))
    res = lint(tmp_path, d)
    assert ('C-v', 'error') in [(f['target'], f['severity']) for f in by(res, 'L21')]
    assert ('token_type CODE2', 'warn') in [(f['target'], f['severity']) for f in by(res, 'L21')]


def test_l21_l22_pass(example):
    assert not bad(example, 'L21') and not bad(example, 'L22')


def test_l22_missing_kind_fails_and_is_warn_in_lite(tmp_path):
    d = base()
    d['token_types']['token_types'] = [t for t in d['token_types']['token_types'] if t['kind'] != 'status_list_token']
    assert [f['severity'] for f in bad(lint(tmp_path, d), 'L22')] == ['error']
    assert [f['severity'] for f in bad(lint(tmp_path / 'lite', d, profile='lite'), 'L22')] == ['warn']


def test_l23_over_cap_without_exception_fails_and_with_exception_pass(tmp_path):
    d = base()
    tt(d, 'AT')['max_lifetime'] = 7200
    hop(d, 'H2')['max_lifetime'] = 7200
    assert any('組織の上限' in f['message'] for f in bad(lint(tmp_path, d), 'L23'))
    tt(d, 'AT')['lifetime_exception'] = {'approved_by': 'セキュリティ委員会', 'reason': '移行期間', 'approved_on': '2026-11-23'}
    assert not any('組織の上限' in f['message'] for f in bad(lint(tmp_path / 'b', d), 'L23'))


def test_l23_a01_tenant_admin_sets_lifetime_without_exp_iat_fails(tmp_path):
    d = base()
    c = claim(d, 'C-exp')
    c['enforced_at'] = [e for e in c['enforced_at'] if 'iat' not in e['check']]
    hop(d, 'H2')['validates']['checks'] = [x for x in hop(d, 'H2')['validates']['checks'] if 'iat' not in x]
    assert any('exp − iat' in f['message'] for f in bad(lint(tmp_path, d), 'L23'))


def test_l23_a14_session_without_idle_fails(tmp_path):
    d = base()
    tt(d, 'BFFSESSION').pop('idle_timeout')
    assert 'token_type BFFSESSION' in [f['target'] for f in bad(lint(tmp_path, d), 'L23')]


def test_l23_same_lifetime_everywhere_warns(tmp_path):
    d = base()
    for t in d['token_types']['token_types']:
        if t['decision'] in ('採用', '既定どおり'):
            t['max_lifetime'] = 300
            if 'idle_timeout' in t:
                t['idle_timeout'] = 300
    assert any(f['severity'] == 'warn' and '1 つの数字' in f['message'] for f in by(lint(tmp_path, d), 'L23'))


def test_l23_pass(example):
    assert not bad(example, 'L23')


# ------------------------------------------------------------------ L31 (A01)
def test_l31_a01_tenant_admin_writable_without_iss_or_api_check_fails(tmp_path):
    d = base()
    for e in claim(d, 'C-roles')['enforced_at']:
        e.pop('against', None)
    assert [f['target'] for f in bad(lint(tmp_path, d), 'L31')] == ['C-roles']


def test_l31_editable_provenance_fails(tmp_path):
    d = base()
    claim(d, 'C-roles')['provenance'] = '本人が編集できる値'
    assert [f['target'] for f in bad(lint(tmp_path, d), 'L31')] == ['C-roles']


def test_l31_other_claim_chain_pass_and_break(tmp_path, example):
    assert not bad(example, 'L31')  # C-user-id is pinned through C-sub (with), C-sub through the data layer and iss
    d = base()
    for e in claim(d, 'C-sub')['enforced_at']:
        e.pop('against', None)
    assert sorted(f['target'] for f in bad(lint(tmp_path, d), 'L31')) == ['C-sub', 'C-user-id']


# ------------------------------------------------------------------ L37, L43
def test_l37_authz_claim_without_absent_meaning_fails(tmp_path, example):
    assert not bad(example, 'L37')
    d = base()
    claim(d, 'C-roles').pop('absent_semantics')
    assert [f['target'] for f in bad(lint(tmp_path, d), 'L37')] == ['C-roles']


def _adopt_txn(d, transport):
    t = tt(d, 'TXN')
    t.update(decision='採用', purpose='p', issuer='TTS', holder='saas-api', max_lifetime=60, stored_at='service_memory',
             transport=transport, revocation=[{'method': 'exp_only', 'delay_seconds': 60}], visible_to=['api'],
             typ='txntoken+jwt', alg_allowlist=['ES256'], issuers=[{'iss': 'https://tts.example.com', 'jwks_uri': 'https://tts.example.com/jwks'}],
             key_rotation={'publish_before_use_seconds': 0, 'retire_after_seconds': 60}, jwe={'used': False},
             unknown_kid={'refetch_min_interval_seconds': 300, 'negative_cache_seconds': 300, 'on_fetch_failure': 'reject'},
             jwks_cache_ttl=3600, key_source={'from': 'configured_jwks_uri', 'header_key_params': 'reject'},
             required_claims=['iss', 'exp', 'aud'], max_clock_skew=30, tenant_binding={'by': ['iss']},
             size={'signing': {'alg': 'ES256'}, 'header': {'params': [{'name': 'alg', 'type': 'string', 'max_bytes': 5}]}, 'path': ['nginx-large-client-header-buffers']})


def test_l43_txn_token_as_bearer_warns_and_header_pass(tmp_path):
    d = base()
    _adopt_txn(d, 'authorization_bearer')
    assert [f['target'] for f in bad(lint(tmp_path, d), 'L43')] == ['token_type TXN']
    d = base()
    _adopt_txn(d, 'txn_token_header')
    assert not bad(lint(tmp_path / 'b', d), 'L43')


# ------------------------------------------------------------------ L62, L63, L64 (issuance_effects.yaml)
def test_l62_dpop_without_cnf_fails(tmp_path):
    d = base()
    d['token_types']['issuance_profile']['sender_constraint']['value'] = 'dpop'
    ids = {f['target'] for f in bad(lint(tmp_path, d), 'L62')}
    assert {'E-dpop.1', 'E-dpop.3', 'E-dpop.5'} <= ids


def test_l62_example_has_no_effect(example):
    assert not by(example, 'L62') and not by(example, 'L63') and not by(example, 'L64')


def test_l63_fapi_without_sender_constraint_or_par_fails(tmp_path):
    d = base()
    d['token_types']['issuance_profile']['conformance_profile']['value'] = 'fapi2_security'
    assert {f['target'] for f in bad(lint(tmp_path, d), 'L63')} == {'E-fapi2.1', 'E-fapi2.2'}


def test_l64_mtls_at_entry_pass_with_forwarded_cert_header(tmp_path):
    d = base()
    ip = d['token_types']['issuance_profile']
    ip['sender_constraint']['value'] = 'mtls'
    ip['tls_termination'] = {'value': 'at_entry', 'rationale': 'nginx で終端する'}
    ip['forwarded_cert_header'] = {'name': 'X-Client-Cert', 'strip_inbound': True, 'written_only_by': 'nginx'}
    assert not bad(lint(tmp_path, d), 'L64')


# ------------------------------------------------------------------ L65, L66, L67
def test_l65_confidential_claim_visible_fails_and_jwe_pass(tmp_path, example):
    assert not bad(example, 'L65')
    d = base()
    claim(d, 'C-email')['carried_in'] = ['IDT', 'AT']
    assert [f['target'] for f in bad(lint(tmp_path, d), 'L65')] == []  # AT is not visible to the browser
    claim(d, 'C-email')['confidential_from'] = ['browser', 'hop:nginx']
    assert [f['target'] for f in bad(lint(tmp_path / 'b', d), 'L65')] == ['C-email']
    tt(d, 'AT')['jwe'] = {'used': True, 'nesting': 'sign_then_encrypt', 'recipients': [{'recipient': 'saas-api', 'key_ref': 'k1'}], 'decryptors': ['api']}
    assert not bad(lint(tmp_path / 'c', d), 'L65')


def test_l66_jwe_decryptor_not_visible_fails(tmp_path):
    d = base()
    tt(d, 'AT')['jwe'] = {'used': True, 'nesting': 'sign_then_encrypt', 'recipients': [{'recipient': 'db', 'key_ref': 'k1'}], 'decryptors': ['db']}
    assert [f['target'] for f in bad(lint(tmp_path, d), 'L66')] == ['token_type AT']


def test_l67_header_copy_used_for_authz_fails_and_db_session_pass(tmp_path, example):
    assert not bad(example, 'L67')
    d = base()
    claim(d, 'C-tenant-id')['integrity_until'].append({'place': 'http_header', 'target': 'X-Tenant', 'trust_boundary': '内部'})
    assert [f['target'] for f in bad(lint(tmp_path, d), 'L67')] == ['C-tenant-id']


# ------------------------------------------------------------------ L68-L71 (warn only)
def test_l68_to_l71_warn(tmp_path):
    d = base()
    d['claims']['claims'].append(new_claim(id='C-ip', name='ip_address', data_category=['user.device.ip_address']))
    d['claims']['claims'].append(new_claim(id='C-perms', name='permissions', shape='array', max_items=200, usage='authz',
                                           absent_semantics={'absent': '何も許さない'}))
    d['claims']['claims'].append(new_claim(id='C-apikey', name='api_key', data_category=['system.operations']))
    claim(d, 'C-v')['note'] = 'example: alice@corp.co.jp'
    res = lint(tmp_path, d)
    assert [f['target'] for f in by(res, 'L68')] == ['C-ip']
    assert [f['target'] for f in by(res, 'L69')] == ['C-perms']
    assert [f['target'] for f in by(res, 'L70')] == ['C-apikey']
    assert len(by(res, 'L71')) == 1
    assert {f['severity'] for r in ('L68', 'L69', 'L70', 'L71') for f in by(res, r)} == {'warn'}


def test_l68_to_l71_pass(example):
    assert not any(bad(example, r) for r in ('L68', 'L69', 'L70', 'L71'))


# ------------------------------------------------------------------ L72
def test_l72_shared_claim_with_25_answers_pass_and_blank_fails(tmp_path, example):
    assert 'C-tenant-id' not in [f['target'] for f in by(example, 'L72')]
    d = base()
    res = lint(tmp_path, d, md=False)
    assert 'C-tenant-id' in [f['target'] for f in by(res, 'L72')]
    dd = tmp_path / 'blank'
    dd.mkdir()
    text = open(os.path.join(EXAMPLE, 'claim_request_tenant_id.md'), encoding='utf-8').read()
    text = text.replace('| 8 | ID・金額は文字列で運ぶか | 文字列（レルム名。数値にしない） |', '| 8 | ID・金額は文字列で運ぶか | 未定 |')
    (dd / 'claim_request_tenant_id.md').write_text(text, encoding='utf-8')
    reqs = semantic.claim_requests(str(dd))
    assert reqs['C-tenant-id']['rows'][8] == '未定' and len(reqs['C-tenant-id']['rows']) == 25


# ------------------------------------------------------------------ L73 (A17)
def test_l73_a17_lite_for_a_multitenant_design_warns(tmp_path):
    res = core.run(EXAMPLE, profile='lite', today=TODAY)
    assert [(f['severity'], 'multitenant' in f['message']) for f in by(res, 'L73')] == [('warn', True)]
    assert not by(core.run(EXAMPLE, today=TODAY), 'L73')  # Full: nothing to say


def test_l73_missing_criteria_in_lite(tmp_path):
    d = base()
    d['catalog_answers'].pop('lite_criteria')
    assert [f['severity'] for f in by(lint(tmp_path, d, profile='lite'), 'L73')] == ['warn']


# ------------------------------------------------------------------ R8 info (registered claims of both the ID token and the AT)
def test_r8_info_skips_registered_idt_at_claims(example):
    dup = [f['target'] for f in by(example, 'R8', 'info') if '重複' in f['message']]
    assert dup == []


def test_r8_info_still_reports_a_custom_claim_on_two_types(tmp_path):
    d = base()
    claim(d, 'C-tenant-id')['carried_in'] = ['AT', 'IDT']
    assert 'C-tenant-id' in [f['target'] for f in by(lint(tmp_path, d), 'R8', 'info')]


def test_l1a_role_synonym_fails(tmp_path):
    d = base()
    d['claims']['claims'].append(new_claim(id='C-user-roles', name='user_roles', shape='array', max_items=2))
    assert 'C-user-roles' in [f['target'] for f in bad(lint(tmp_path, d), 'L1a')]
