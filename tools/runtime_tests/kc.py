# -*- coding: utf-8 -*-
"""Live environment for #8: Keycloak 26.8.0 (realms t1, t2 of scenario A and corp for the exchange measurement) and
Postgres 16, in the Ubuntu-24.04 WSL distro, under the compose project jcg-issue8-runtime (ports 38080 / 35432).

Realms are generated per run from the scenario A design (design.md 3.「既定から外れた点」): client saas-web with the
basic scope only, Full Scope Allowed OFF with the scope roles approver / tenant-admin, header typ at+jwt, the namespace
mappers (tenant_id, user_id, roles, v) and the Audience mapper saas-api. Test-environment deviations (written in
templates/runtime/lifetime_revocation.md): Direct Access Grants is ON for saas-web so that the harness can log in
without a browser (the design uses authorization code + PKCE), and the extra clients saas-light (lightweight AT),
saas-multi (tenant as an array) and rogue-web in t2 (a tenant admin's mapper claiming t1) reproduce casestudy A8, A11, A12.
Client secrets and passwords are random per run and live only in memory and in the temporary import directory.
"""
import json
import os
import secrets
import shutil
import subprocess
import tempfile
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = 'jcg-issue8-runtime'
KC = 'http://localhost:38080'
PG = {'host': 'localhost', 'port': 35432, 'dbname': 'saas'}
NS_KC = 'https://claims\\.example\\.com/'   # Keycloak nests on '.', so the dots of the namespace URI are escaped
KC_IMAGE = 'quay.io/keycloak/keycloak:26.8.0'


def wsl(cmd, check=True, env=None):
    e = dict(os.environ, MSYS_NO_PATHCONV='1')
    exports = ' '.join(f"{k}='{v}'" for k, v in (env or {}).items())
    r = subprocess.run(['wsl', '-d', 'Ubuntu-24.04', '--', 'bash', '-lc', f'{exports} {cmd}'], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=e)
    if check and r.returncode != 0:
        raise RuntimeError(f'wsl failed: {cmd}\n{r.stdout}\n{r.stderr}')
    return r.stdout


def wsl_path(p):
    p = os.path.abspath(p)
    return f'/mnt/{p[0].lower()}{p[2:].replace(os.sep, "/")}'


def _mapper(name, kind, cfg):
    base = {'access.token.claim': 'true', 'id.token.claim': 'false', 'userinfo.token.claim': 'false', 'introspection.token.claim': 'true'}
    base.update(cfg)
    return {'name': name, 'protocol': 'openid-connect', 'protocolMapper': kind, 'consentRequired': False, 'config': base}


def hard(name, claim, value, jtype='String'):
    return _mapper(name, 'oidc-hardcoded-claim-mapper', {'claim.name': claim, 'claim.value': value, 'jsonType.label': jtype})


def aud(name, client):
    return _mapper(name, 'oidc-audience-mapper', {'included.client.audience': client})


def design_mappers(tenant, tenant_value=None, tenant_type='String'):
    return [hard('tenant_id', NS_KC + '.tenant_id', tenant_value or tenant, tenant_type),
            _mapper('user_id', 'oidc-usermodel-property-mapper', {'user.attribute': 'id', 'claim.name': NS_KC + '.user_id', 'jsonType.label': 'String'}),
            _mapper('roles', 'oidc-usermodel-realm-role-mapper', {'claim.name': NS_KC + '.roles', 'multivalued': 'true', 'jsonType.label': 'String'}),
            hard('v', NS_KC + '.v', '1'), aud('aud-saas-api', 'saas-api')]


class Env:
    def __init__(self):
        self.secret = {}
        self.admin_password = secrets.token_urlsafe(18)
        self.pg_password = secrets.token_urlsafe(18)
        self.user_password = 'T-' + secrets.token_urlsafe(12)
        self.import_dir = tempfile.mkdtemp(prefix='jcg-issue8-realms-')

    # ------------------------------------------------------------ realms
    def client(self, cid, mappers=(), direct=True, exchange=False, light=False, full_scope=True, basic_only=False, service=False):
        self.secret.setdefault(cid, secrets.token_urlsafe(24))  # the same client ID in t1 and t2 shares one secret
        c = {'clientId': cid, 'enabled': True, 'publicClient': False, 'secret': self.secret[cid], 'standardFlowEnabled': False,
             'directAccessGrantsEnabled': direct, 'serviceAccountsEnabled': service, 'protocol': 'openid-connect', 'fullScopeAllowed': full_scope,
             'attributes': {'access.token.header.type.rfc9068': 'true', 'standard.token.exchange.enabled': 'true' if exchange else 'false',
                            'client.use.lightweight.access.token.enabled': 'true' if light else 'false'},
             'protocolMappers': list(mappers)}
        if basic_only:
            c['defaultClientScopes'] = ['basic']
            c['optionalClientScopes'] = []
        return c

    def user(self, name, roles):
        return {'username': name, 'enabled': True, 'email': f'{name}@example.com', 'emailVerified': True, 'firstName': name, 'lastName': 'Test',
                'credentials': [{'type': 'password', 'value': self.user_password, 'temporary': False}], 'realmRoles': list(roles)}

    def tenant_realm(self, t):
        clients = [self.client('saas-web', design_mappers(t), full_scope=False, basic_only=True),
                   self.client('saas-api', direct=False)]
        if t == 't1':
            clients += [self.client('saas-light', design_mappers(t), light=True, full_scope=False, basic_only=True),
                        self.client('saas-multi', design_mappers(t, '["t1","t2"]', 'JSON'), full_scope=False, basic_only=True)]
        else:
            clients.append(self.client('rogue-web', design_mappers(t, 't1'), full_scope=False, basic_only=True))
        users = [self.user('alice', ['approver']), self.user('carol', ['approver'])] if t == 't1' else [self.user('bob', ['approver'])]
        return {'realm': t, 'enabled': True, 'accessTokenLifespan': 300, 'ssoSessionIdleTimeout': 1800, 'ssoSessionMaxLifespan': 36000,
                'revokeRefreshToken': True, 'refreshTokenMaxReuse': 0,
                'roles': {'realm': [{'name': 'approver'}, {'name': 'tenant-admin'}]}, 'clients': clients, 'users': users,
                # Full Scope Allowed OFF: the scope roles of saas-web are approver and tenant-admin only (design.md 3.)
                'scopeMappings': [{'client': c, 'roles': ['approver', 'tenant-admin']} for c in ('saas-web', 'saas-light', 'saas-multi', 'rogue-web')
                                  if any(x['clientId'] == c for x in clients)]}

    def corp_realm(self):
        dept = _mapper('department', 'oidc-usermodel-attribute-mapper', {'user.attribute': 'department', 'claim.name': NS_KC + '.department', 'jsonType.label': 'String'})
        clients = [self.client('portal', [dept]), self.client('orders', direct=False), self.client('invoices', direct=False),
                   self.client('mcp-tools', [dept], exchange=True, service=True)]
        users = [self.user('carol', ['approver', 'default-roles-corp']), self.user('dave', ['default-roles-corp'])]  # as the casestudy's corp
        users[0]['attributes'] = {'department': ['sales']}
        return {'realm': 'corp', 'enabled': True, 'accessTokenLifespan': 300, 'revokeRefreshToken': True, 'roles': {'realm': [{'name': 'approver'}]},
                'clients': clients, 'users': users,
                'attributes': {'userProfileEnabled': 'true'},
                'components': {'org.keycloak.userprofile.UserProfileProvider': [{'providerId': 'declarative-user-profile', 'subComponents': {},
                               'config': {'kc.user.profile.config': [json.dumps({'unmanagedAttributePolicy': 'ENABLED', 'attributes': [
                                   {'name': n, 'displayName': n, 'permissions': {'view': ['admin', 'user'], 'edit': ['admin']}, 'multivalued': False}
                                   for n in ('username', 'email', 'firstName', 'lastName')]})]}}]}}

    def write_realms(self):
        for r in (self.tenant_realm('t1'), self.tenant_realm('t2'), self.corp_realm()):
            json.dump(r, open(os.path.join(self.import_dir, r['realm'] + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    # ------------------------------------------------------------ containers
    def compose(self, args, check=True):
        env = {'KC_ADMIN_PASSWORD': self.admin_password, 'PG_PASSWORD': self.pg_password, 'IMPORT_DIR': wsl_path(self.import_dir)}
        return wsl(f"docker compose -p {PROJECT} -f '{wsl_path(os.path.join(HERE, 'compose.yaml'))}' {args}", check=check, env=env)

    def up(self):
        self.write_realms()
        self.compose('down -v --remove-orphans', check=False)
        self.compose('up -d')
        t0 = time.time()
        while time.time() - t0 < 300:
            try:
                if requests.get(f'{KC}/realms/corp/.well-known/openid-configuration', timeout=3).ok:
                    break
            except requests.RequestException:
                pass
            time.sleep(3)
        else:
            raise RuntimeError('keycloak did not start:\n' + self.compose('logs --tail 40 keycloak', check=False))
        self.setup_corp_scopes()
        return round(time.time() - t0, 1)

    def down(self):
        out = self.compose('down -v --remove-orphans', check=False)
        shutil.rmtree(self.import_dir, ignore_errors=True)
        return out

    def versions(self):
        return {'keycloak_image': KC_IMAGE, 'keycloak_image_id': wsl(f"docker image inspect {KC_IMAGE} --format '{{{{.Id}}}}'", check=False).strip(),
                'compose_project': PROJECT, 'ports': {'keycloak': 38080, 'postgres': 35432}}

    # ------------------------------------------------------------ Keycloak helpers
    def admin_token(self):
        r = requests.post(f'{KC}/realms/master/protocol/openid-connect/token',
                          data={'grant_type': 'password', 'client_id': 'admin-cli', 'username': 'admin', 'password': self.admin_password}, timeout=10)
        r.raise_for_status()
        return r.json()['access_token']

    def admin(self, method, path, **kw):
        r = requests.request(method, f'{KC}/admin/realms/{path}', headers={'Authorization': 'Bearer ' + self.admin_token()}, timeout=10, **kw)
        r.raise_for_status()
        return r.json() if r.content else None

    def user_id(self, realm, username):
        return self.admin('GET', f'{realm}/users', params={'username': username, 'exact': 'true'})[0]['id']

    def token(self, realm, client_id, username, scope='openid'):
        r = requests.post(f'{KC}/realms/{realm}/protocol/openid-connect/token', data={
            'grant_type': 'password', 'client_id': client_id, 'client_secret': self.secret[client_id], 'username': username,
            'password': self.user_password, 'scope': scope}, timeout=10)
        r.raise_for_status()
        return r.json()

    def refresh(self, realm, client_id, rt):
        r = requests.post(f'{KC}/realms/{realm}/protocol/openid-connect/token', data={
            'grant_type': 'refresh_token', 'client_id': client_id, 'client_secret': self.secret[client_id], 'refresh_token': rt}, timeout=10)
        if r.status_code != 200:
            raise RuntimeError(f'{r.status_code} {r.json().get("error")}: {r.json().get("error_description")}')
        return r.json()

    def exchange(self, realm, client_id, subject_token, audience=None, scope=None):
        data = {'grant_type': 'urn:ietf:params:oauth:grant-type:token-exchange', 'client_id': client_id, 'client_secret': self.secret[client_id],
                'subject_token': subject_token, 'subject_token_type': 'urn:ietf:params:oauth:token-type:access_token',
                'requested_token_type': 'urn:ietf:params:oauth:token-type:access_token'}
        if audience:
            data['audience'] = audience
        if scope:
            data['scope'] = scope
        r = requests.post(f'{KC}/realms/{realm}/protocol/openid-connect/token', data=data, timeout=10)
        return r.status_code, r.json()

    def jwks(self, realm):
        return requests.get(f'{KC}/realms/{realm}/protocol/openid-connect/certs', timeout=10).json()

    def setup_corp_scopes(self):
        """Audience scopes of corp, created after import as in the casestudy (cs/infra.py setup_scopes)."""
        targets = {'aud-orders': 'orders', 'aud-invoices': 'invoices', 'aud-mcp': 'mcp-tools'}
        optional = {'portal': ['aud-orders', 'aud-invoices', 'aud-mcp'], 'mcp-tools': ['aud-invoices', 'aud-orders']}
        have = {c['name']: c['id'] for c in self.admin('GET', 'corp/client-scopes')}
        for name, target in targets.items():
            if name not in have:
                self.admin('POST', 'corp/client-scopes', json={'name': name, 'protocol': 'openid-connect',
                                                               'attributes': {'include.in.token.scope': 'true', 'display.on.consent.screen': 'false'},
                                                               'protocolMappers': [aud(name, target)]})
        have = {c['name']: c['id'] for c in self.admin('GET', 'corp/client-scopes')}
        clients = {c['clientId']: c['id'] for c in self.admin('GET', 'corp/clients')}
        for cid, names in optional.items():
            for n in names:
                self.admin('PUT', f'corp/clients/{clients[cid]}/optional-client-scopes/{have[n]}')

    def set_realm(self, realm, **attrs):
        r = self.admin('GET', realm)
        old = {k: r.get(k) for k in attrs}
        r.update(attrs)
        self.admin('PUT', realm, json=r)
        return old

    def set_user(self, realm, username, **attrs):
        uid = self.user_id(realm, username)
        u = self.admin('GET', f'{realm}/users/{uid}')
        u.update(attrs)
        self.admin('PUT', f'{realm}/users/{uid}', json=u)

    def realm_role(self, realm, username, role, add):
        uid = self.user_id(realm, username)
        rep = self.admin('GET', f'{realm}/roles/{role}')
        self.admin('POST' if add else 'DELETE', f'{realm}/users/{uid}/role-mappings/realm', json=[rep])
