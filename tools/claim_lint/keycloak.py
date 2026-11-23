# -*- coding: utf-8 -*-
"""claim_lint import keycloak (#30): normalize a Keycloak realm export into the observed configuration that
`claim_lint drift` compares with a design's registry. See tools/claim_lint/DRIFT.md.

  python tools/claim_lint import keycloak REALM_EXPORT.json [-o OBSERVED.yaml]

The input is a realm representation: the admin API partial export (POST /admin/realms/{realm}/partial-export with
exportClients and exportGroupsAndRoles), `kc.sh export`, or a keycloak-config-cli file (JSON or YAML). Normalization:
internal IDs, timestamps and secrets are dropped, lists are sorted by name, clients and client scopes become maps
keyed by their name, and each client's statically readable token contents (claims per token, from its own mappers,
its default and optional client scopes, and the claims Keycloak writes without a mapper, keycloak_implicit.yaml) are
computed. The same export always gives the same file, whatever the order of the arrays in the export.
"""
import json
import os
import re

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
FORMAT = 'claim-lint-keycloak-observed/1'
IMPLICIT_FILE = os.path.join(HERE, 'keycloak_implicit.yaml')
# clients that Keycloak creates in every realm (26.8)
BUILTIN_CLIENTS = {'account', 'account-console', 'admin-cli', 'broker', 'realm-management', 'security-admin-console'}
TOKENS = ('access', 'id', 'userinfo', 'introspection', 'lightweight')
# client attributes that are dropped (secrets, key material, timestamps) or kept as booleans / values
DROP_ATTR = re.compile(r'secret|certificate|jwks|private|key\.|creation\.time|realm_client|saml\.signing|saml\.encryption')
BOOL_ATTRS = {  # attribute -> (normalized name, value when the attribute is absent)
    'standard.token.exchange.enabled': ('standard_token_exchange', False),   # absent = off (#4 K2, measured 2026-11-23)
    'oauth2.device.authorization.grant.enabled': ('device_authorization_grant', False),
    'oidc.ciba.grant.enabled': ('ciba_grant', False),
    'oauth2.jwt.authorization.grant.enabled': ('jwt_authorization_grant', False),
    'client.use.lightweight.access.token.enabled': ('lightweight_access_token', False),
    'access.token.header.type.rfc9068': ('access_token_header_type_rfc9068', False),
    'dpop.bound.access.tokens': ('dpop_bound_access_tokens', False),
    'tls.client.certificate.bound.access.tokens': ('tls_client_certificate_bound_access_tokens', False),
    'use.refresh.tokens': ('use_refresh_tokens', True),
    'backchannel.logout.session.required': ('backchannel_logout_session_required', True),
    'backchannel.logout.revoke.offline.tokens': ('backchannel_logout_revoke_offline_tokens', False),
}
VALUE_ATTRS = {
    'pkce.code.challenge.method': 'pkce_method',
    'access.token.lifespan': 'access_token_lifespan',
    'client.session.idle.timeout': 'client_session_idle_timeout',
    'client.session.max.lifespan': 'client_session_max_lifespan',
    'client.offline.session.idle.timeout': 'client_offline_session_idle_timeout',
    'client.offline.session.max.lifespan': 'client_offline_session_max_lifespan',
    'access.token.signed.response.alg': 'access_token_signed_response_alg',
    'id.token.signed.response.alg': 'id_token_signed_response_alg',
    'backchannel.logout.url': 'backchannel_logout_url',
    'request.object.required': 'request_object_required',
}
INT_VALUES = {'access_token_lifespan', 'client_session_idle_timeout', 'client_session_max_lifespan',
              'client_offline_session_idle_timeout', 'client_offline_session_max_lifespan'}
# mapper types whose claim is fixed by the type (no claim.name). None: the mapper writes no claim of its own
FIXED_CLAIM = {
    'oidc-audience-mapper': 'aud', 'oidc-audience-resolve-mapper': 'aud', 'oidc-full-name-mapper': 'name',
    'oidc-sub-mapper': 'sub', 'oidc-sha256-pairwise-sub-mapper': 'sub', 'oidc-address-mapper': 'address',
    'oidc-allowed-origins-mapper': 'allowed-origins', 'oidc-acr-mapper': 'acr', 'oidc-amr-mapper': 'amr',
    'oidc-role-name-mapper': None, 'oidc-hardcoded-role-mapper': None,
}
# mapper types that read claim.name (the default claim name when claim.name is absent)
NAMED_CLAIM = {
    'oidc-hardcoded-claim-mapper': None, 'oidc-usermodel-attribute-mapper': None, 'oidc-usermodel-property-mapper': None,
    'oidc-usersessionmodel-note-mapper': None, 'oidc-group-membership-mapper': None,
    'oidc-organization-membership-mapper': 'organization', 'oidc-usermodel-realm-role-mapper': 'realm_access.roles',
    'oidc-usermodel-client-role-mapper': 'resource_access.${client_id}.roles', 'oidc-claims-param-token-mapper': None,
    'oidc-claims-param-value-idtoken-mapper': None,
}
ROLE_MAPPERS = {'oidc-usermodel-realm-role-mapper', 'oidc-usermodel-client-role-mapper'}


class ImportError_(ValueError):
    pass


# ------------------------------------------------------------------ reading
def load_export(path):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    data = json.loads(text) if text.lstrip().startswith('{') else yaml.safe_load(text)
    if not isinstance(data, dict) or 'realm' not in data:
        raise ImportError_(f'{path}: not a Keycloak realm representation (no "realm" key)')
    return data


def split_claim_name(name):
    """Keycloak nests a claim at each unescaped dot: 'https://claims\\.example\\.com/.tenant_id' ->
    ['https://claims.example.com/', 'tenant_id'] (OIDCAttributeMapperHelper.splitClaimPath)."""
    parts, cur, i = [], '', 0
    while i < len(name):
        ch = name[i]
        if ch == '\\' and i + 1 < len(name) and name[i + 1] == '.':
            cur += '.'
            i += 2
            continue
        if ch == '.':
            parts.append(cur)
            cur = ''
        else:
            cur += ch
        i += 1
    parts.append(cur)
    return parts


def _true(v):
    return str(v).strip().lower() == 'true'


def mapper_tokens(cfg):
    """Tokens a mapper writes into. Keycloak 26.8 treats an absent access.token.claim / introspection.token.claim as
    true (backwards compatibility in OIDCAttributeMapperHelper) and the others as false."""
    out = []
    for tok, key, absent in (('access', 'access.token.claim', True), ('id', 'id.token.claim', False),
                             ('userinfo', 'userinfo.token.claim', False),
                             ('introspection', 'introspection.token.claim', True),
                             ('lightweight', 'lightweight.claim', False)):
        v = cfg.get(key)
        if (absent if v is None else _true(v)):
            out.append(tok)
    return out


def normalize_mapper(m):
    cfg = {k: (v[0] if isinstance(v, list) and len(v) == 1 else v) for k, v in (m.get('config') or {}).items()}
    typ = m.get('protocolMapper')
    out = {'name': m.get('name'), 'type': typ}
    if typ in FIXED_CLAIM:
        claim = FIXED_CLAIM[typ]
        out['claim'] = [claim] if claim else None
    elif typ in NAMED_CLAIM:
        cn = cfg.get('claim.name') or NAMED_CLAIM[typ]
        out['claim'] = split_claim_name(cn) if cn else None
        if not cn:
            out['readable'] = False
    else:
        cn = cfg.get('claim.name')
        out['claim'] = split_claim_name(cn) if cn else None
        out['readable'] = False  # a type this importer does not know (script mapper, extension): not read statically
    out['tokens'] = mapper_tokens(cfg) if out.get('claim') else []
    if cfg.get('jsonType.label'):
        out['json_type'] = cfg['jsonType.label']
    if typ in ROLE_MAPPERS or cfg.get('multivalued') is not None:
        out['multivalued'] = _true(cfg.get('multivalued'))
    for k, nk in (('claim.value', 'value'), ('user.attribute', 'user_attribute'),
                  ('included.client.audience', 'audience'), ('included.custom.audience', 'custom_audience'),
                  ('usermodel.clientRoleMapping.clientId', 'role_client'), ('usermodel.realmRoleMapping.rolePrefix', 'role_prefix')):
        if cfg.get(k) not in (None, ''):
            out[nk] = cfg[k]
    return out


def _mappers(lst):
    ms = [normalize_mapper(m) for m in lst or [] if (m.get('protocol') or 'openid-connect') == 'openid-connect']
    return sorted(ms, key=lambda m: (m.get('name') or '', m.get('type') or ''))


def _composites(role):
    comp = role.get('composites') or {}
    return {'realm': sorted(comp.get('realm') or []),
            'client': {k: sorted(v) for k, v in sorted((comp.get('client') or {}).items())}}


def normalize(export, source=None):
    realm = export
    roles = (export.get('roles') or {})
    realm_roles = {r['name']: r for r in roles.get('realm') or []}
    client_roles = {cid: {r['name']: r for r in lst or []} for cid, lst in (roles.get('client') or {}).items()}
    default_role = (export.get('defaultRole') or {}).get('name') or f"default-roles-{export.get('realm')}"
    scope_maps = export.get('scopeMappings') or []
    client_scope_maps = export.get('clientScopeMappings') or {}

    def role_scope(kind, name):
        """Roles mapped to a client ('client') or a client scope ('clientScope'), realm roles and client roles."""
        realm_r = sorted({r for sm in scope_maps if sm.get(kind) == name for r in sm.get('roles') or []})
        cl = {}
        for owner, lst in client_scope_maps.items():
            for sm in lst or []:
                if sm.get(kind) == name:
                    cl.setdefault(owner, set()).update(sm.get('roles') or [])
        return {'realm': realm_r, 'client': {k: sorted(v) for k, v in sorted(cl.items())}}

    scopes = {}
    for s in export.get('clientScopes') or []:
        if (s.get('protocol') or 'openid-connect') != 'openid-connect':
            continue
        attrs = s.get('attributes') or {}
        scopes[s['name']] = {
            'include_in_token_scope': _true(attrs.get('include.in.token.scope', 'true')),
            'role_scope': role_scope('clientScope', s['name']),
            'mappers': _mappers(s.get('protocolMappers')),
        }
    clients = {}
    for c in export.get('clients') or []:
        if (c.get('protocol') or 'openid-connect') != 'openid-connect':
            continue
        attrs = {k: v for k, v in (c.get('attributes') or {}).items()}
        n = {
            'builtin': c['clientId'] in BUILTIN_CLIENTS,
            'enabled': bool(c.get('enabled', True)),
            'public_client': bool(c.get('publicClient', False)),
            'bearer_only': bool(c.get('bearerOnly', False)),
            'client_authenticator': c.get('clientAuthenticatorType', 'client-secret'),
            'flows': {
                'standard': bool(c.get('standardFlowEnabled', True)),
                'implicit': bool(c.get('implicitFlowEnabled', False)),
                'direct_access_grants': bool(c.get('directAccessGrantsEnabled', False)),
                'service_accounts': bool(c.get('serviceAccountsEnabled', False)),
            },
            'full_scope_allowed': bool(c.get('fullScopeAllowed', True)),
            'default_client_scopes': sorted(c.get('defaultClientScopes') or []),
            'optional_client_scopes': sorted(c.get('optionalClientScopes') or []),
            'role_scope': role_scope('client', c['clientId']),
            'redirect_uris': sorted(c.get('redirectUris') or []),
            'mappers': _mappers(c.get('protocolMappers')),
        }
        for k, (nk, absent) in BOOL_ATTRS.items():
            n[nk] = _true(attrs[k]) if k in attrs else absent
        for k, nk in VALUE_ATTRS.items():
            v = attrs.get(k)
            if v in (None, ''):
                n[nk] = None
            elif nk in INT_VALUES:
                try:
                    n[nk] = int(v) if int(v) > 0 else None  # 0 / -1 mean "use the realm value"
                except ValueError:
                    n[nk] = v
            else:
                n[nk] = v
        n['other_attributes'] = sorted(k for k in attrs if k not in BOOL_ATTRS and k not in VALUE_ATTRS and not DROP_ATTR.search(k))
        clients[c['clientId']] = n
    policies = []
    for p in ((export.get('clientPolicies') or {}).get('policies') or []):
        policies.append({'name': p.get('name'), 'enabled': p.get('enabled', True),
                         'conditions': sorted(x.get('condition') for x in p.get('conditions') or []),
                         'profiles': sorted(p.get('profiles') or [])})
    profiles = []
    for p in ((export.get('clientProfiles') or {}).get('profiles') or []):
        profiles.append({'name': p.get('name'), 'executors': sorted(x.get('executor') for x in p.get('executors') or [])})
    out = {
        'format': FORMAT,
        'source': dict({'kind': 'keycloak-realm-export', 'keycloak_version': export.get('keycloakVersion')},
                       **({'file': source} if source else {})),
        'realm': {
            'name': export.get('realm'),
            'enabled': bool(export.get('enabled', True)),
            'access_token_lifespan': realm.get('accessTokenLifespan'),
            'access_token_lifespan_implicit': realm.get('accessTokenLifespanForImplicitFlow'),
            'access_code_lifespan': realm.get('accessCodeLifespan'),
            'sso_session_idle_timeout': realm.get('ssoSessionIdleTimeout'),
            'sso_session_max_lifespan': realm.get('ssoSessionMaxLifespan'),
            'remember_me': bool(realm.get('rememberMe', False)),
            'sso_session_idle_timeout_remember_me': realm.get('ssoSessionIdleTimeoutRememberMe'),
            'sso_session_max_lifespan_remember_me': realm.get('ssoSessionMaxLifespanRememberMe'),
            'client_session_idle_timeout': realm.get('clientSessionIdleTimeout'),
            'client_session_max_lifespan': realm.get('clientSessionMaxLifespan'),
            'offline_session_idle_timeout': realm.get('offlineSessionIdleTimeout'),
            'offline_session_max_lifespan_enabled': realm.get('offlineSessionMaxLifespanEnabled'),
            'offline_session_max_lifespan': realm.get('offlineSessionMaxLifespan'),
            'revoke_refresh_token': realm.get('revokeRefreshToken'),
            'refresh_token_max_reuse': realm.get('refreshTokenMaxReuse'),
            'default_signature_algorithm': realm.get('defaultSignatureAlgorithm'),
            'organizations_enabled': realm.get('organizationsEnabled'),
            'default_role': default_role,
            'default_roles': _composites(realm_roles.get(default_role, {})),
            'realm_roles': sorted(realm_roles),
            'composite_roles': {k: _composites(r) for k, r in sorted(realm_roles.items()) if r.get('composite')},
            'client_roles': {k: sorted(v) for k, v in sorted(client_roles.items()) if v},
            'default_default_client_scopes': sorted(export.get('defaultDefaultClientScopes') or []),
            'default_optional_client_scopes': sorted(export.get('defaultOptionalClientScopes') or []),
            'client_policies': sorted(policies, key=lambda p: p['name'] or ''),
            'client_profiles': sorted(profiles, key=lambda p: p['name'] or ''),
        },
        'client_scopes': dict(sorted(scopes.items())),
        'clients': {},
    }
    implicit = load_implicit()
    for cid in sorted(clients):
        clients[cid]['effective_role_scope'] = effective_role_scope(out, clients[cid])
        clients[cid]['emits'] = emits(out, clients[cid], implicit)
        out['clients'][cid] = clients[cid]
    return out


# ------------------------------------------------------------------ static view of the tokens
def load_implicit(path=IMPLICIT_FILE):
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)


def _expand(realm, role_names):
    """Realm roles with their composite realm roles (transitively), and the client roles they bring."""
    comp = realm['realm'].get('composite_roles') or {}
    seen, todo, cl = set(), list(role_names), {}
    while todo:
        r = todo.pop()
        if r in seen:
            continue
        seen.add(r)
        c = comp.get(r)
        if c:
            todo += c['realm']
            for k, v in c['client'].items():
                cl.setdefault(k, set()).update(v)
    return sorted(seen), cl


def effective_role_scope(obs, c):
    """Roles that may appear in a token of this client (the user's roles are intersected with this set).
    Full Scope Allowed: every realm role and client role. Otherwise the client's scope mappings and those of its
    default client scopes (optional scopes add theirs only when requested)."""
    realm = obs['realm']
    if c['full_scope_allowed']:
        return {'full_scope': True, 'realm': realm['realm_roles'], 'client': realm['client_roles']}
    realm_r = set(c['role_scope']['realm'])
    cl = {k: set(v) for k, v in c['role_scope']['client'].items()}
    for s in c['default_client_scopes']:
        rs = (obs['client_scopes'].get(s) or {}).get('role_scope') or {'realm': [], 'client': {}}
        realm_r |= set(rs['realm'])
        for k, v in rs['client'].items():
            cl.setdefault(k, set()).update(v)
    exp, more = _expand(obs, realm_r)
    for k, v in more.items():
        cl.setdefault(k, set()).update(v)
    return {'full_scope': False, 'realm': exp, 'client': {k: sorted(v) for k, v in sorted(cl.items())}}


def emits(obs, c, implicit):
    """Claims per token kind: [{claim (path), source, mapper, optional, when}]. The access token of a client with the
    lightweight switch keeps only the mapper claims marked "Add to lightweight access token" and the claims of
    keycloak_implicit.yaml lightweight_access."""
    out = {}
    sources = [('client', None, c['mappers'], False)]
    for opt, names in ((False, c['default_client_scopes']), (True, c['optional_client_scopes'])):
        for s in names:
            sc = obs['client_scopes'].get(s)
            if sc is not None:
                sources.append((f'scope:{s}', s, sc['mappers'], opt))
    for tok in ('access', 'id', 'userinfo'):
        light = tok == 'access' and c.get('lightweight_access_token')
        items = []
        imp_key = 'lightweight_access' if light else tok
        for e in implicit.get(imp_key) or []:
            if e.get('only_if') and not any(c.get(k) for k in e['only_if']):
                continue  # e.g. cnf of a lightweight token: only when the client binds its tokens (DPoP, mTLS)
            it = {'claim': [e['claim']], 'source': 'keycloak', 'mapper': None, 'optional': False}
            if e.get('when'):
                it['when'] = e['when']
            items.append(it)
        if tok == 'userinfo':
            items.append({'claim': ['sub'], 'source': 'keycloak', 'mapper': None, 'optional': False})
        for src, _, mappers, opt in sources:
            for m in mappers:
                if not m.get('claim') or tok not in m['tokens']:
                    continue
                if light and 'lightweight' not in m['tokens']:
                    continue
                it = {'claim': m['claim'], 'source': src, 'mapper': m['name'], 'optional': opt}
                if m['type'] == 'oidc-audience-resolve-mapper':
                    others = sorted(k for k in c['effective_role_scope']['client'] if c['effective_role_scope']['client'][k])
                    if not others:
                        continue
                    it['when'] = 'the token carries client roles of ' + ', '.join(others)
                items.append(it)
        seen, uniq = set(), []
        for it in sorted(items, key=lambda x: (x['claim'], x['source'], x['mapper'] or '')):
            key = (tuple(it['claim']), it['source'], it['mapper'])
            if key not in seen:
                seen.add(key)
                uniq.append(it)
        out[tok] = uniq
    return out


class _NoAliasDumper(yaml.SafeDumper):
    """Write shared lists in full instead of YAML anchors (&id001), so that the file diffs line by line."""
    def ignore_aliases(self, data):
        return True


def dump(obs):
    return yaml.dump(obs, Dumper=_NoAliasDumper, allow_unicode=True, sort_keys=False, default_flow_style=None, width=120)


def main(argv):
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog='claim_lint import', description='Normalize an IdP configuration export (#30).')
    ap.add_argument('idp', choices=('keycloak',))
    ap.add_argument('export')
    ap.add_argument('-o', '--out', help='write the normalized YAML here (default: stdout)')
    a = ap.parse_args(argv)
    try:
        obs = normalize(load_export(a.export), source=os.path.basename(a.export))
    except (ImportError_, json.JSONDecodeError, yaml.YAMLError) as e:
        sys.stderr.write(f'claim_lint import: {e}\n')
        return 2
    text = '# Generated by `python tools/claim_lint import keycloak` (#30). Do not edit; re-import the export.\n' + dump(obs)
    if a.out:
        with open(a.out, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
    else:
        sys.stdout.buffer.write(text.encode('utf-8'))
    return 0
