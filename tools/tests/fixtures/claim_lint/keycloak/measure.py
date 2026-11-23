# -*- coding: utf-8 -*-
"""How the Keycloak fixtures of claim_lint import/drift (#30) were made. Not run by CI (CI reads the stored files).

Needs a throw-away Keycloak 26.8 started in dev mode, for example (WSL Docker, a port of its own):

  docker run -d --name jcg30-kc -p 28080:8080 -e KC_BOOTSTRAP_ADMIN_USERNAME=admin \
      -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak:26.8.0 start-dev
  python tools/tests/fixtures/claim_lint/keycloak/measure.py --base http://localhost:28080 --out <dir>
  docker rm -f jcg30-kc

Steps (standard library only):
 1. scenario A: create realm t1 from scenario-a-t1.import.json (random client secret and user password set here),
    log alice in with authorization code + PKCE S256 (I01), refresh once (I02), and write the decoded AT, ID token
    and refreshed AT (header and payload only, no compact token, no signature) and the partial export of the realm
    (admin API, secrets masked by Keycloak as "**********")
 2. the same realm shifted on the server (mapper "plan" added, accessTokenLifespan 3600, Full Scope Allowed on):
    write its partial export and an AT issued after the shift
 3. defaults (#4 K2, K10): create realm "fresh" with only its name, and a client with only its clientId; write the
    partial export and the client as the admin API returns it; check that a token exchange from a client without the
    switch is refused and accepted after the switch is turned on; and whether a new user's token carries offline_access
 The output files are copied into this directory by hand after review, and scenario-a-t1.observed.yaml is made with
 `python -m tools.claim_lint import keycloak scenario-a-t1.export.json -o scenario-a-t1.observed.yaml`.
 Last run: 2026-11-23, quay.io/keycloak/keycloak:26.8.0 on WSL Docker, port 28080 (tools/claim_lint/DRIFT.md 5.).
"""
import argparse
import base64
import hashlib
import html
import http.cookiejar
import json
import os
import re
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REDIRECT = 'http://localhost:28081/callback'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def call(method, url, token=None, data=None, form=None, auth=None, opener=None):
    headers = {}
    body = None
    if token:
        headers['Authorization'] = 'Bearer ' + token
    if auth:
        headers['Authorization'] = 'Basic ' + base64.b64encode(f'{auth[0]}:{auth[1]}'.encode()).decode()
    if data is not None:
        body = json.dumps(data).encode()
        headers['Content-Type'] = 'application/json'
    if form is not None:
        body = urllib.parse.urlencode(form).encode()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        r = (opener or urllib.request.build_opener()).open(req)
        return r.status, r.headers, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read().decode('utf-8', 'replace')


def admin_token(base):
    s, _, b = call('POST', f'{base}/realms/master/protocol/openid-connect/token',
                   form={'grant_type': 'password', 'client_id': 'admin-cli', 'username': 'admin', 'password': 'admin'})
    assert s == 200, b
    return json.loads(b)['access_token']


def decode(tok):
    h, p, s = tok.split('.')
    pad = lambda x: x + '=' * (-len(x) % 4)  # noqa: E731
    return (base64.urlsafe_b64decode(pad(h)).decode(), base64.urlsafe_b64decode(pad(p)).decode(),
            len(base64.urlsafe_b64decode(pad(s))))


def fixture(tok, note, issued_on):
    h, p, sig = decode(tok)
    return {'_note': note, 'issued_on': issued_on, 'header_json': h, 'payload_json': p, 'token_length': len(tok),
            'sig_bytes': sig}


def recreate_realm(base, at, rep):
    call('DELETE', f'{base}/admin/realms/{rep["realm"]}', token=at)
    s, _, b = call('POST', f'{base}/admin/realms', token=at, data=rep)
    assert s == 201, (s, b)


class LocalHttpPolicy(http.cookiejar.DefaultCookiePolicy):
    """Keycloak marks its login cookies Secure even in start-dev on http://localhost; send them back anyway."""
    def return_ok_secure(self, cookie, request):
        return True


def code_flow(base, realm, client, secret, user, password):
    jar = http.cookiejar.CookieJar(LocalHttpPolicy())
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), NoRedirect)
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    nonce = secrets.token_urlsafe(16)
    q = urllib.parse.urlencode({'client_id': client, 'redirect_uri': REDIRECT, 'response_type': 'code', 'scope': 'openid',
                                'state': secrets.token_urlsafe(8), 'nonce': nonce, 'code_challenge': challenge,
                                'code_challenge_method': 'S256'})
    s, _, page = call('GET', f'{base}/realms/{realm}/protocol/openid-connect/auth?{q}', opener=op)
    assert s == 200, (s, page[:500])
    action = html.unescape(re.search(r'<form[^>]*id="kc-form-login"[^>]*action="([^"]+)"', page).group(1))
    s, h, b = call('POST', action, form={'username': user, 'password': password, 'credentialId': ''}, opener=op)
    assert s == 302, (s, b[:500])
    loc = h['Location']
    code = urllib.parse.parse_qs(urllib.parse.urlparse(loc).query)['code'][0]
    s, _, b = call('POST', f'{base}/realms/{realm}/protocol/openid-connect/token', auth=(client, secret),
                   form={'grant_type': 'authorization_code', 'code': code, 'redirect_uri': REDIRECT, 'code_verifier': verifier})
    assert s == 200, b
    tokens = json.loads(b)
    assert json.loads(decode(tokens['id_token'])[1]).get('nonce') == nonce
    return tokens


def scenario_a(base, at, out, today):
    with open(os.path.join(HERE, 'scenario-a-t1.import.json'), encoding='utf-8') as f:
        rep = json.load(f)
    rep.pop('_note', None)
    secret = secrets.token_urlsafe(24)
    password = secrets.token_urlsafe(16) + 'Aa1!'
    for c in rep['clients']:
        c['secret'] = secrets.token_urlsafe(24) if c['clientId'] != 'saas-web' else secret
    rep['users'][0]['credentials'] = [{'type': 'password', 'value': password, 'temporary': False}]
    recreate_realm(base, at, rep)
    tokens = code_flow(base, 't1', 'saas-web', secret, 'alice', password)
    s, _, b = call('POST', f'{base}/realms/t1/protocol/openid-connect/token', auth=('saas-web', secret),
                   form={'grant_type': 'refresh_token', 'refresh_token': tokens['refresh_token']})
    assert s == 200, b
    refreshed = json.loads(b)
    note = (f'Issued on {today} by a throw-away Keycloak 26.8.0 container (start-dev) with realm t1 created from '
            'tools/tests/fixtures/claim_lint/keycloak/scenario-a-t1.import.json, user alice, client saas-web, '
            'authorization code + PKCE S256 (measure.py). Only the decoded header and payload are kept (no compact '
            'token, no signature); the signing key existed only in that container, which was removed.')
    files = {
        'scenario-a-t1.at.json': fixture(tokens['access_token'], note + ' Access token of I01.', today),
        'scenario-a-t1.idt.json': fixture(tokens['id_token'], note + ' ID token of I01.', today),
        'scenario-a-t1.at-refresh.json': fixture(refreshed['access_token'], note + ' Access token of the refresh (I02).', today),
    }
    s, _, b = call('POST', f'{base}/admin/realms/t1/partial-export?exportClients=true&exportGroupsAndRoles=true', token=at)
    assert s == 200, b
    files['scenario-a-t1.export.json'] = json.loads(b)
    s, _, b = call('GET', f'{base}/admin/serverinfo', token=at)
    files['_serverinfo-version.json'] = {'version': json.loads(b)['systemInfo']['version']}
    # 2. the same realm deliberately shifted on the server (one mapper added, AT lifetime extended, Full Scope Allowed
    #    on), exported and logged in again: drift must report each shift, and the issuer schema must reject the AT
    s, _, b = call('GET', f'{base}/admin/realms/t1/clients?clientId=saas-web', token=at)
    web = json.loads(b)[0]
    s, _, b = call('POST', f'{base}/admin/realms/t1/clients/{web["id"]}/protocol-mappers/models', token=at,
                   data={'name': 'plan', 'protocol': 'openid-connect', 'protocolMapper': 'oidc-hardcoded-claim-mapper',
                         'config': {'claim.name': 'plan', 'claim.value': 'gold', 'jsonType.label': 'String',
                                    'access.token.claim': 'true', 'id.token.claim': 'false',
                                    'userinfo.token.claim': 'false', 'introspection.token.claim': 'true'}})
    assert s == 201, b
    web['fullScopeAllowed'] = True
    s, _, b = call('PUT', f'{base}/admin/realms/t1/clients/{web["id"]}', token=at, data=dict(web, protocolMappers=None))
    assert s == 204, b
    s, _, b = call('GET', f'{base}/admin/realms/t1', token=at)
    realm = json.loads(b)
    realm['accessTokenLifespan'] = 3600
    s, _, b = call('PUT', f'{base}/admin/realms/t1', token=at, data=realm)
    assert s == 204, b
    shifted = code_flow(base, 't1', 'saas-web', secret, 'alice', password)
    files['scenario-a-t1-shifted.at.json'] = fixture(
        shifted['access_token'], note.replace('measure.py)', 'measure.py), then shifted on the server: mapper plan '
                                              'added, accessTokenLifespan 3600, Full Scope Allowed on.') + ' Access token of I01.', today)
    s, _, b = call('POST', f'{base}/admin/realms/t1/partial-export?exportClients=true&exportGroupsAndRoles=true', token=at)
    assert s == 200, b
    files['scenario-a-t1-shifted.export.json'] = json.loads(b)
    for k, v in files.items():
        with open(os.path.join(out, k), 'w', encoding='utf-8', newline='\n') as f:
            json.dump(v, f, ensure_ascii=False, indent=1)
            f.write('\n')
    print('scenario A: wrote', ', '.join(files))


def defaults(base, at, out, today):
    """#4 K2 (default of the client switch Standard token exchange) and K10 (offline_access in default-roles)."""
    recreate_realm(base, at, {'realm': 'fresh', 'enabled': True})
    rec = {'_note': f'Measured on {today} with Keycloak 26.8.0 (start-dev) through the admin REST API (measure.py).',
           'realm_rep_sent': {'realm': 'fresh', 'enabled': True}, 'client_rep_sent': {'clientId': 'probe'}}
    s, _, b = call('POST', f'{base}/admin/realms/fresh/clients', token=at, data={'clientId': 'probe'})
    assert s == 201, b
    s, _, b = call('GET', f'{base}/admin/realms/fresh/clients?clientId=probe', token=at)
    probe = json.loads(b)[0]
    rec['client_as_returned'] = {k: probe.get(k) for k in ('clientId', 'publicClient', 'standardFlowEnabled',
                                                           'directAccessGrantsEnabled', 'implicitFlowEnabled',
                                                           'serviceAccountsEnabled', 'fullScopeAllowed',
                                                           'defaultClientScopes', 'optionalClientScopes', 'attributes')}
    s, _, b = call('GET', f'{base}/admin/realms/fresh/roles/default-roles-fresh/composites', token=at)
    rec['default_roles_composites'] = sorted(r['name'] for r in json.loads(b))
    s, _, b = call('GET', f'{base}/admin/realms/fresh', token=at)
    r = json.loads(b)
    rec['realm_defaults'] = {k: r.get(k) for k in ('accessTokenLifespan', 'accessCodeLifespan', 'ssoSessionIdleTimeout',
                                                   'ssoSessionMaxLifespan', 'revokeRefreshToken', 'refreshTokenMaxReuse',
                                                   'offlineSessionIdleTimeout', 'defaultSignatureAlgorithm',
                                                   'defaultDefaultClientScopes', 'defaultOptionalClientScopes')}
    s, _, b = call('GET', f'{base}/admin/realms/fresh/default-default-client-scopes', token=at)
    rec['realm_defaults']['defaultDefaultClientScopes'] = sorted(x['name'] for x in json.loads(b))
    s, _, b = call('GET', f'{base}/admin/realms/fresh/default-optional-client-scopes', token=at)
    rec['realm_defaults']['defaultOptionalClientScopes'] = sorted(x['name'] for x in json.loads(b))
    # behaviour of the switch: a confidential client without the attribute asks for a token exchange
    sec = secrets.token_urlsafe(24)
    pw = secrets.token_urlsafe(16) + 'Aa1!'
    s, _, b = call('POST', f'{base}/admin/realms/fresh/clients', token=at,
                   data={'clientId': 'requester', 'publicClient': False, 'secret': sec, 'directAccessGrantsEnabled': True})
    assert s == 201, b
    s, _, b = call('POST', f'{base}/admin/realms/fresh/users', token=at,
                   data={'username': 'bob', 'enabled': True, 'email': 'bob@example.com', 'emailVerified': True,
                         'firstName': 'bob', 'lastName': 'Test',
                         'credentials': [{'type': 'password', 'value': pw, 'temporary': False}]})
    assert s == 201, b
    tok_url = f'{base}/realms/fresh/protocol/openid-connect/token'
    s, _, b = call('POST', tok_url, auth=('requester', sec), form={'grant_type': 'password', 'username': 'bob', 'password': pw, 'scope': 'openid'})
    assert s == 200, b
    t = json.loads(b)['access_token']
    payload = json.loads(decode(t)[1])
    rec['new_user_token_realm_access'] = payload.get('realm_access')
    rec['new_user_token_scope'] = payload.get('scope')
    xform = {'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange', 'subject_token': t,
             'subject_token_type': 'urn:ietf:params:oauth:token-type:access_token'}
    s, _, b = call('POST', tok_url, auth=('requester', sec), form=xform)
    rec['exchange_without_switch'] = {'status': s, 'body': json.loads(b) if b.startswith('{') else b[:300]}
    s, _, b = call('GET', f'{base}/admin/realms/fresh/clients?clientId=requester', token=at)
    req = json.loads(b)[0]
    rec['requester_attributes_before'] = req.get('attributes')
    req['attributes'] = dict(req.get('attributes') or {}, **{'standard.token.exchange.enabled': 'true'})
    s, _, b = call('PUT', f'{base}/admin/realms/fresh/clients/{req["id"]}', token=at, data=req)
    assert s == 204, b
    s, _, b = call('POST', tok_url, auth=('requester', sec), form=xform)
    body = json.loads(b) if b.startswith('{') else b[:300]
    rec['exchange_with_switch'] = {'status': s, 'issued_token_type': body.get('issued_token_type') if isinstance(body, dict) else None,
                                   'error': body.get('error') if isinstance(body, dict) else body}
    s, _, b = call('POST', f'{base}/admin/realms/fresh/partial-export?exportClients=true&exportGroupsAndRoles=true', token=at)
    assert s == 200, b
    with open(os.path.join(out, 'fresh-realm.export.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(json.loads(b), f, ensure_ascii=False, indent=1)
        f.write('\n')
    with open(os.path.join(out, 'fresh-realm.defaults.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print(json.dumps(rec, ensure_ascii=False, indent=1))


def resource_exchange(base, at, out, today):
    """PR #47 independent check, item 2: the resource server's client (saas-api, aud of the AT) turns on Standard token
    exchange. Realm t1 is created again from the import; the AT of saas-web is the subject token; saas-api asks for
    the exchange before and after the switch. Writes scenario-a-t1.exchange.json (statuses and claim names only)."""
    with open(os.path.join(HERE, 'scenario-a-t1.import.json'), encoding='utf-8') as f:
        rep = json.load(f)
    rep.pop('_note', None)
    sec = {c['clientId']: secrets.token_urlsafe(24) for c in rep['clients']}
    for c in rep['clients']:
        c['secret'] = sec[c['clientId']]
    password = secrets.token_urlsafe(16) + 'Aa1!'
    rep['users'][0]['credentials'] = [{'type': 'password', 'value': password, 'temporary': False}]
    recreate_realm(base, at, rep)
    tokens = code_flow(base, 't1', 'saas-web', sec['saas-web'], 'alice', password)
    tok_url = f'{base}/realms/t1/protocol/openid-connect/token'
    x = {'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange', 'subject_token': tokens['access_token'],
         'subject_token_type': 'urn:ietf:params:oauth:token-type:access_token'}
    rec = {'_note': f'Measured on {today} with Keycloak 26.8.0 (start-dev), realm t1 from scenario-a-t1.import.json '
                    '(measure.py --step exchange). saas-api exchanges the access token that saas-web obtained (aud saas-api).'}
    s, _, b = call('POST', tok_url, auth=('saas-api', sec['saas-api']), form=x)
    rec['without_switch'] = {'status': s, 'error_description': (json.loads(b) if b.startswith('{') else {}).get('error_description')}
    s, _, b = call('GET', f'{base}/admin/realms/t1/clients?clientId=saas-api', token=at)
    api = json.loads(b)[0]
    api['attributes'] = dict(api.get('attributes') or {}, **{'standard.token.exchange.enabled': 'true'})
    s, _, b = call('PUT', f'{base}/admin/realms/t1/clients/{api["id"]}', token=at, data=api)
    assert s == 204, b
    s, _, b = call('POST', tok_url, auth=('saas-api', sec['saas-api']), form=x)
    body = json.loads(b) if b.startswith('{') else {}
    rec['with_switch_on_saas_api'] = {'status': s, 'issued_token_type': body.get('issued_token_type')}
    if s == 200:
        p = json.loads(decode(body['access_token'])[1])
        rec['with_switch_on_saas_api'].update(claims=sorted(p), aud=p.get('aud'), azp=p.get('azp'))
    with open(os.path.join(out, 'scenario-a-t1.exchange.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print(json.dumps(rec, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://localhost:28080')
    ap.add_argument('--out', required=True)
    ap.add_argument('--today', required=True, help='YYYY-MM-DD written into the fixtures')
    ap.add_argument('--step', choices=('all', 'exchange'), default='all',
                    help='exchange: only the resource-server exchange of the PR #47 check (scenario-a-t1.exchange.json)')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    at = admin_token(a.base)
    if a.step == 'exchange':
        resource_exchange(a.base, at, a.out, a.today)
        return 0
    scenario_a(a.base, at, a.out, a.today)
    at = admin_token(a.base)
    defaults(a.base, at, a.out, a.today)
    return 0


if __name__ == '__main__':
    sys.exit(main())
