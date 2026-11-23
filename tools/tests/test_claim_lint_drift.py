# -*- coding: utf-8 -*-
"""Tests of claim_lint import keycloak / drift (#30). Offline: they read the stored Keycloak 26.8.0 export and tokens
of scenario A (tools/tests/fixtures/claim_lint/keycloak/, made by measure.py there)."""
import copy
import json
import os
import random
import subprocess
import sys

import pytest

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from claim_lint import drift, keycloak, render  # noqa: E402

EXAMPLE = os.path.join(ROOT, 'templates', 'examples', 'scenario-a')
FIX = os.path.join(TOOLS, 'tests', 'fixtures', 'claim_lint', 'keycloak')
EXPORT = os.path.join(FIX, 'scenario-a-t1.export.json')
OBSERVED = os.path.join(FIX, 'scenario-a-t1.observed.yaml')
SHIFTED = os.path.join(FIX, 'scenario-a-t1-shifted.export.json')
NS = 'https://claims.example.com/'
TOKENS = [('AT', os.path.join(FIX, 'scenario-a-t1.at.json')), ('IDT', os.path.join(FIX, 'scenario-a-t1.idt.json')),
          ('AT', os.path.join(FIX, 'scenario-a-t1.at-refresh.json'))]


def export():
    with open(EXPORT, encoding='utf-8') as f:
        return json.load(f)


def web(exp):
    return next(c for c in exp['clients'] if c['clientId'] == 'saas-web')


def run(exp, tokens=()):
    return drift.run(EXAMPLE, keycloak.normalize(exp), tokens=list(tokens))


def rules(res, severity='error'):
    return sorted({(f['rule'], f['target']) for f in res['findings'] if f['severity'] == severity})


def keys(payload):
    """Top-level claims, and the members of the organization's namespace object as '<namespace>.<name>'."""
    out = set()
    for k, v in payload.items():
        if k == NS and isinstance(v, dict):
            out |= {f'{NS}.{m}' for m in v}
        else:
            out.add(k)
    return out


# ------------------------------------------------------------------ import keycloak: normalization
def test_normalized_fixture_is_up_to_date():
    """The stored observed file is what `import keycloak` makes of the stored export (CI regenerates and compares)."""
    with open(OBSERVED, encoding='utf-8') as f:
        stored = f.read()
    want = keycloak.dump(keycloak.normalize(export(), source=os.path.basename(EXPORT)))
    assert stored.split('\n', 1)[1] == want


def test_normalization_ignores_array_order_and_internal_ids():
    base = keycloak.dump(keycloak.normalize(export()))
    exp = export()
    rnd = random.Random(30)

    def shuffle(node):
        if isinstance(node, list):
            rnd.shuffle(node)
            for x in node:
                shuffle(x)
        elif isinstance(node, dict):
            if 'id' in node and isinstance(node['id'], str):
                node['id'] = 'x' + node['id'][::-1]
            if 'containerId' in node:
                node['containerId'] = 'other'
            for v in node.values():
                shuffle(v)
    shuffle(exp)
    assert keycloak.dump(keycloak.normalize(exp)) == base


def test_normalized_output_has_no_ids_secrets_or_anchors():
    text = keycloak.dump(keycloak.normalize(export()))
    exp = export()
    ids = set()

    def collect(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in ('id', 'containerId') and isinstance(v, str):
                    ids.add(v)
                collect(v)
        elif isinstance(node, list):
            for x in node:
                collect(x)
    collect(exp)
    assert ids and not [i for i in ids if i in text]
    assert '**********' not in text and 'secret:' not in text and '&id' not in text


def test_claim_name_split_follows_keycloak_escaping():
    assert keycloak.split_claim_name('https://claims\\.example\\.com/.tenant_id') == ['https://claims.example.com/', 'tenant_id']
    assert keycloak.split_claim_name('realm_access.roles') == ['realm_access', 'roles']
    assert keycloak.split_claim_name('plain') == ['plain']


def test_static_view_equals_the_claims_of_the_issued_tokens():
    """The statically computed claims of saas-web (mappers + default scopes + keycloak_implicit.yaml) are exactly
    the claims of the tokens Keycloak issued from the same realm (I01 and the refresh I02)."""
    obs = keycloak.normalize(export())
    emits = obs['clients']['saas-web']['emits']
    styles = {NS: 'object'}
    static = {tok: {drift.registry_key(e['claim'], styles) for e in emits[tok] if not e['optional']} for tok in ('access', 'id')}
    for tid, path in TOKENS:
        payload = render.read_payload(path)
        assert keys(payload) == static['access' if tid == 'AT' else 'id'], path


def test_fresh_realm_defaults_k2_k10():
    """#4 K2 and K10, measured on a realm created with its name only (fresh-realm.*.json, 2026-11-23)."""
    with open(os.path.join(FIX, 'fresh-realm.export.json'), encoding='utf-8') as f:
        obs = keycloak.normalize(json.load(f))
    probe = obs['clients']['probe']  # created with {"clientId": "probe"} only
    assert probe['standard_token_exchange'] is False and probe['flows']['direct_access_grants'] is False
    assert 'offline_access' in probe['optional_client_scopes']
    assert 'offline_access' in obs['realm']['default_roles']['realm']
    with open(os.path.join(FIX, 'fresh-realm.defaults.json'), encoding='utf-8') as f:
        rec = json.load(f)
    assert 'standard.token.exchange.enabled' not in rec['client_as_returned']['attributes']
    assert rec['exchange_without_switch']['status'] == 400
    assert 'not enabled' in rec['exchange_without_switch']['body']['error_description']
    assert rec['exchange_with_switch']['status'] == 200
    assert 'offline_access' in rec['new_user_token_realm_access']['roles']


# ------------------------------------------------------------------ drift: scenario A
def test_scenario_a_has_no_drift():
    """Scenario A's realm and tokens against its registry: 0 errors and 0 warnings. The one info (D13) lists the
    built-in clients of every realm; the consumers reject their tokens by aud (C-aud) and azp (C-azp)."""
    res = drift.run(EXAMPLE, OBSERVED, tokens=TOKENS)
    assert res['counts'] == {'error': 0, 'warn': 0, 'info': 1}, res['findings']
    assert [f['rule'] for f in res['findings']] == ['D13']
    assert res['clients'] == {'saas-web': {'AT': 'access', 'IDT': 'id'}}


def test_raw_export_and_normalized_file_give_the_same_result():
    a = drift.run(EXAMPLE, EXPORT)
    b = drift.run(EXAMPLE, OBSERVED)
    assert a['findings'] == b['findings']


# ------------------------------------------------------------------ drift: deliberate shifts (the three of #30 first)
def test_added_mapper_is_detected():
    exp = export()
    web(exp)['protocolMappers'].append({'name': 'plan', 'protocol': 'openid-connect', 'protocolMapper': 'oidc-hardcoded-claim-mapper',
                                        'config': {'claim.name': 'plan', 'claim.value': 'gold', 'jsonType.label': 'String',
                                                   'access.token.claim': 'true', 'id.token.claim': 'false'}})
    assert rules(run(exp)) == [('D1', 'saas-web:AT:plan')]


def test_extended_lifetime_is_detected():
    exp = export()
    exp['accessTokenLifespan'] = 3600
    assert rules(run(exp)) == [('D5', 'saas-web:AT'), ('D5', 'saas-web:IDT')]
    exp = export()
    web(exp)['attributes']['access.token.lifespan'] = '900'  # the client override
    res = run(exp)
    assert rules(res) == [('D5', 'saas-web:AT'), ('D5', 'saas-web:IDT')]
    assert 'クライアントの Access Token Lifespan' in res['findings'][0]['message']
    exp = export()
    exp['ssoSessionMaxLifespan'] = 72000
    assert rules(run(exp)) == [('D5', 'realm:SSO'), ('D5', 'saas-web:RT')]


def test_shorter_lifetime_is_a_warning():
    exp = export()
    exp['accessTokenLifespan'] = 120
    res = run(exp)
    assert rules(res) == [] and rules(res, 'warn') == [('D5', 'saas-web:AT'), ('D5', 'saas-web:IDT')]


def test_full_scope_allowed_is_detected():
    exp = export()
    web(exp)['fullScopeAllowed'] = True
    res = run(exp)
    assert rules(res) == sorted([('D10', 'saas-web'), ('D4', f'saas-web:AT:{NS}.roles')])
    d4 = next(f for f in res['findings'] if f['rule'] == 'D4')
    assert 'offline_access' in d4['roles'] and 'default-roles-t1' in d4['roles']


def test_shift_made_on_the_server_is_detected_and_its_token_fails_the_issuer_schema():
    """The same three shifts made on a running Keycloak 26.8.0 (measure.py step 3): the export and the AT it issued."""
    res = drift.run(EXAMPLE, SHIFTED, tokens=[('AT', os.path.join(FIX, 'scenario-a-t1-shifted.at.json'))])
    got = {r for r, _ in rules(res)}
    assert {'D1', 'D4', 'D5', 'D10', 'D14'} <= got
    d14 = ' '.join(f['message'] for f in res['findings'] if f['rule'] == 'D14')
    assert "'plan' was unexpected" in d14 and 'offline_access' in d14


# ------------------------------------------------------------------ drift: other shifts
def test_rejected_claim_from_an_added_scope_is_detected():
    exp = export()
    web(exp)['defaultClientScopes'].append('profile')  # preferred_username is 却下 (C-preferred-username)
    res = run(exp)
    msgs = {f['target']: f['message'] for f in res['findings'] if f['rule'] == 'D1' and f['severity'] == 'error'}
    assert 'saas-web:AT:preferred_username' in msgs and '台帳で却下したクレーム' in msgs['saas-web:AT:preferred_username']
    exp = export()
    web(exp)['optionalClientScopes'].append('address')
    res = run(exp)
    assert rules(res) == [] and ('D1', 'saas-web:AT:address') in rules(res, 'warn')


def test_removed_mapper_is_detected():
    exp = export()
    web(exp)['protocolMappers'] = [m for m in web(exp)['protocolMappers'] if m['name'] != 'tenant_id']
    res = run(exp)
    assert rules(res) == [('D2', f'saas-web:AT:{NS}.tenant_id')]
    exp = export()
    web(exp)['protocolMappers'] = [m for m in web(exp)['protocolMappers'] if m['name'] != 'roles']
    assert rules(run(exp), 'warn') == [('D2', f'saas-web:AT:{NS}.roles')]  # roles is not in required_claims


def test_value_and_type_shifts_are_detected():
    exp = export()
    next(m for m in web(exp)['protocolMappers'] if m['name'] == 'v')['config']['claim.value'] = 'x' * 5
    assert rules(run(exp)) == [('D4', f'saas-web:AT:{NS}.v')]
    exp = export()
    next(m for m in web(exp)['protocolMappers'] if m['name'] == 'email_verified')['config']['jsonType.label'] = 'String'
    assert rules(run(exp)) == [('D3', 'saas-web:IDT:email_verified')]
    exp = export()
    next(m for m in web(exp)['protocolMappers'] if m['name'] == 'roles')['config']['multivalued'] = 'false'
    assert ('D3', f'saas-web:AT:{NS}.roles') in rules(run(exp))


@pytest.mark.parametrize('change,expected', [
    (lambda e: web(e).update(directAccessGrantsEnabled=True), ('D9', 'saas-web:I04')),
    (lambda e: web(e).update(serviceAccountsEnabled=True), ('D9', 'saas-web:I05')),
    (lambda e: web(e)['attributes'].update({'standard.token.exchange.enabled': 'true'}), ('D9', 'saas-web:I06')),
    (lambda e: web(e)['attributes'].update({'oauth2.device.authorization.grant.enabled': 'true'}), ('D9', 'saas-web:I07')),
    (lambda e: web(e).update(implicitFlowEnabled=True), ('D9', 'saas-web:I10')),
    (lambda e: web(e)['attributes'].update({'oidc.ciba.grant.enabled': 'true'}), ('D9', 'saas-web:I13')),
    (lambda e: web(e)['attributes'].update({'oauth2.jwt.authorization.grant.enabled': 'true'}), ('D9', 'saas-web:I15')),
    (lambda e: web(e)['attributes'].pop('pkce.code.challenge.method'), ('D9', 'saas-web:I01')),
    (lambda e: web(e).update(standardFlowEnabled=False), ('D9', 'saas-web:I01')),
    (lambda e: web(e)['attributes'].update({'backchannel.logout.url': 'https://bff.example.com/bcl'}), ('D11', 'saas-web:I09')),
    (lambda e: web(e)['attributes'].update({'dpop.bound.access.tokens': 'true'}), ('D11', 'saas-web:I29')),
    (lambda e: web(e)['optionalClientScopes'].append('offline_access'), ('D11', 'saas-web:I08')),
    (lambda e: e.update(revokeRefreshToken=False), ('D6', 'realm:RT')),
    (lambda e: e.update(refreshTokenMaxReuse=2), ('D6', 'realm:RT')),
    (lambda e: web(e)['attributes'].update({'access.token.header.type.rfc9068': 'false'}), ('D7', 'saas-web:AT')),
    (lambda e: web(e)['attributes'].update({'id.token.signed.response.alg': 'HS256'}), ('D7', 'saas-web:IDT')),
    (lambda e: web(e).update(publicClient=True), ('D8', 'saas-web')),
    (lambda e: web(e).update(clientAuthenticatorType='client-jwt'), ('D8', 'saas-web')),
])
def test_switch_shifts_are_detected(change, expected):
    exp = export()
    change(exp)
    assert expected in rules(run(exp))


def test_lightweight_access_token_drops_required_claims():
    exp = export()
    web(exp)['attributes']['client.use.lightweight.access.token.enabled'] = 'true'
    got = rules(run(exp))
    assert ('D11', 'saas-web:I03') in got
    assert ('D2', f'saas-web:AT:{NS}.tenant_id') in got and ('D2', 'saas-web:AT:sub') in got


def test_unreadable_mapper_is_a_warning():
    exp = export()
    web(exp)['protocolMappers'].append({'name': 'js', 'protocol': 'openid-connect', 'protocolMapper': 'script-claims.js', 'config': {}})
    res = run(exp)
    assert rules(res) == [] and ('D12', 'saas-web:js') in rules(res, 'warn')


def test_tokens_that_do_not_conform_fail(tmp_path):
    """D14: a token carrying a rejected claim (realm_access) or missing a required one fails the issuer schema."""
    bad = copy.deepcopy(render.read_payload(TOKENS[0][1]))
    bad['realm_access'] = {'roles': ['approver']}
    del bad[NS]['tenant_id']
    p = tmp_path / 'bad.json'
    p.write_text(json.dumps(bad), encoding='utf-8')
    res = drift.run(EXAMPLE, OBSERVED, tokens=[('AT', str(p))])
    msgs = [f['message'] for f in res['findings'] if f['rule'] == 'D14']
    assert any("'realm_access' was unexpected" in m for m in msgs)
    assert any("'tenant_id' is a required property" in m for m in msgs)


def test_no_client_in_scope_is_an_error():
    exp = export()
    web(exp)['protocolMappers'] = [m for m in web(exp)['protocolMappers'] if m['name'] != 'aud-saas-api']
    web(exp)['clientId'] = 'renamed'
    res = run(exp)
    assert ('D0', 'clients') in rules(res)


# ------------------------------------------------------------------ PR #47 independent check
def _mapper(exp, name):
    return next(m for m in web(exp)['protocolMappers'] if m['name'] == name)


def test_audience_mapper_moved_to_a_default_scope_still_compares_the_at():
    """1: the Audience mapper moved from the client to one of its default client scopes is still read."""
    exp = export()
    m = _mapper(exp, 'aud-saas-api')
    web(exp)['protocolMappers'].remove(m)
    exp['clientScopes'].append({'name': 'api-aud', 'protocol': 'openid-connect', 'attributes': {}, 'protocolMappers': [m]})
    web(exp)['defaultClientScopes'].append('api-aud')
    res = run(exp)
    assert res['clients'] == {'saas-web': {'AT': 'access', 'IDT': 'id'}}
    assert rules(res) == [] and rules(res, 'warn') == []


def test_audience_value_change_is_detected_and_the_at_stays_compared():
    """1, 3: a changed audience keeps saas-web in the AT comparison (it is the IDT client) and D4 reports both values;
    an extra Audience mapper and an Audience mapper into the ID token are reported too."""
    exp = export()
    _mapper(exp, 'aud-saas-api')['config']['included.client.audience'] = 'account'
    res = run(exp)
    assert res['clients']['saas-web'] == {'AT': 'access', 'IDT': 'id'}
    msgs = [f['message'] for f in res['findings'] if f['rule'] == 'D4' and f['target'] == 'saas-web:AT:aud']
    assert any('saas-api' in m and '出さない' in m for m in msgs) and any('account' in m for m in msgs)
    exp = export()
    web(exp)['protocolMappers'].append({'name': 'aud-evil', 'protocol': 'openid-connect', 'protocolMapper': 'oidc-audience-mapper',
                                        'config': {'included.custom.audience': 'https://evil.example', 'access.token.claim': 'true'}})
    assert ('D4', 'saas-web:AT:aud') in rules(run(exp))
    exp = export()
    _mapper(exp, 'aud-saas-api')['config']['id.token.claim'] = 'true'
    assert ('D4', 'saas-web:IDT:aud') in rules(run(exp))


def test_no_client_for_an_access_token_type_is_d0():
    exp = export()
    web(exp)['protocolMappers'].remove(_mapper(exp, 'aud-saas-api'))
    web(exp)['clientId'] = 'renamed'  # no IDT client either; the AT type has no client at all
    exp['clients'].append({'clientId': 'other-idt', 'enabled': True, 'protocolMappers': []})
    res = drift.run(EXAMPLE, keycloak.normalize(exp))
    assert ('D0', 'clients') in rules(res) or ('D0', 'AT') in rules(res)


def test_issuer_schema_rejects_a_foreign_audience():
    """3: the issuer schema's aud is the token type's audiences, not only a maxLength."""
    d = render.load_design(EXAMPLE)
    bad = copy.deepcopy(render.read_payload(TOKENS[0][1]))
    bad['aud'] = 'account'
    assert any('aud' in e for e in render.validate_payload(d, bad, 'AT', 'issuer'))


def test_token_exchange_on_the_resource_client_is_detected():
    """2: Standard token exchange on saas-api (the AT's aud) makes I06 happen (400 -> 200 on Keycloak 26.8.0)."""
    exp = export()
    api = next(c for c in exp['clients'] if c['clientId'] == 'saas-api')
    api['attributes']['standard.token.exchange.enabled'] = 'true'
    res = run(exp)
    assert rules(res) == [('D9', 'saas-api:I06')] and res['resource_clients'] == ['saas-api']
    with open(os.path.join(FIX, 'scenario-a-t1.exchange.json'), encoding='utf-8') as f:
        rec = json.load(f)
    assert rec['without_switch']['status'] == 400 and rec['with_switch_on_saas_api']['status'] == 200


def test_remember_me_extends_the_compared_lifetimes():
    """4: Remember Me with longer session values lengthens the RT and the IdP session."""
    exp = export()
    exp.update(rememberMe=True, ssoSessionMaxLifespanRememberMe=2592000, ssoSessionIdleTimeoutRememberMe=604800)
    got = rules(run(exp))
    assert ('D5', 'realm:SSO') in got and ('D5', 'saas-web:RT') in got
    exp = export()
    exp.update(rememberMe=False, ssoSessionMaxLifespanRememberMe=2592000)
    assert rules(run(exp)) == []


def test_client_role_mapper_values_are_checked():
    """5: the roles claim written by a client-role mapper is checked against the vocabulary."""
    exp = export()
    m = _mapper(exp, 'roles')
    m['protocolMapper'] = 'oidc-usermodel-client-role-mapper'
    m['config']['usermodel.clientRoleMapping.clientId'] = 'realm-management'
    exp['clientScopeMappings'] = {'realm-management': [{'client': 'saas-web', 'roles': ['realm-admin']}]}
    got = rules(run(exp))
    assert ('D4', f'saas-web:AT:{NS}.roles') in got
    assert ('D3', f'saas-web:AT:{NS}.roles') in got  # the registry's writer is a User Realm Role mapper


def test_source_attribute_change_is_detected():
    """5: user_id read from username instead of id."""
    exp = export()
    _mapper(exp, 'user_id')['config']['user.attribute'] = 'username'
    assert rules(run(exp)) == [('D3', f'saas-web:AT:{NS}.user_id')]


def test_disabled_clients_are_not_compared():
    """5: a disabled client with the same audience is reported as info only."""
    exp = export()
    other = copy.deepcopy(web(exp))
    other.update(clientId='old-web', enabled=False, fullScopeAllowed=True, directAccessGrantsEnabled=True)
    exp['clients'].append(other)
    res = run(exp)
    assert 'old-web' not in res['clients'] and rules(res) == []
    assert ('D13', 'realm:disabled-clients') in rules(res, 'info')


def test_lightweight_token_does_not_expect_cnf_without_sender_constraint():
    """5: cnf is a kept claim of a lightweight token only when the client binds its tokens."""
    exp = export()
    web(exp)['attributes']['client.use.lightweight.access.token.enabled'] = 'true'
    assert not [t for r, t in rules(run(exp)) + rules(run(exp), 'warn') if t.endswith(':cnf')]


# ------------------------------------------------------------------ CLI
def test_cli_import_and_drift(tmp_path):
    out = tmp_path / 'observed.yaml'
    r = subprocess.run([sys.executable, '-m', 'tools.claim_lint', 'import', 'keycloak', EXPORT, '-o', str(out)], cwd=ROOT,
                       capture_output=True)
    assert r.returncode == 0, r.stderr
    r = subprocess.run([sys.executable, '-m', 'tools.claim_lint', 'drift', EXAMPLE, str(out), '--format', 'json',
                        '--token', f'AT={TOKENS[0][1]}', '--token', f'IDT={TOKENS[1][1]}'], cwd=ROOT, capture_output=True)
    assert r.returncode == 0, r.stdout.decode('utf-8')
    res = json.loads(r.stdout.decode('utf-8'))
    assert res['format'] == 'claim-lint-drift/1' and res['counts']['error'] == 0
    r = subprocess.run([sys.executable, '-m', 'tools.claim_lint', 'drift', EXAMPLE, SHIFTED], cwd=ROOT, capture_output=True)
    assert r.returncode == 1
