# -*- coding: utf-8 -*-
"""claim_lint drift (#30): compare the observed Keycloak configuration (claim_lint import keycloak) with a design's
registry (claims.yaml, token_types.yaml with issuance_profile, catalog_answers.yaml). See tools/claim_lint/DRIFT.md.

  python tools/claim_lint drift DESIGN_DIR OBSERVED.yaml|REALM_EXPORT.json [--client ID ...] [--token TYPE=FILE ...]
                                [--format table|json] [--json-out FILE]

Exit status: 1 when there is at least one error, 0 otherwise. No finding can be suppressed; a difference that is
accepted is justified in the design (or the configuration is changed), not silenced here (templates/CONTRIBUTING.md 2.).
"""
import argparse
import copy
import json
import os
import re
import sys

import yaml

from . import core, keycloak, render

ERROR, WARN, INFO = core.ERROR, core.WARN, core.INFO
CARRIED = render.CARRIED_DECISIONS
FORMAT = 'claim-lint-drift/1'
# Keycloak token kind of the static view for each registry kind
KC_TOKEN = {'access_token': 'access', 'id_token': 'id'}
# client switches that issue tokens by a grant (D9): switch -> (registry grant that allows it, catalogue event, label)
SWITCHES = [
    (('flows', 'standard'), 'authorization_code_pkce', 'I01', 'Standard Flow（認可コード）'),
    (('flows', 'direct_access_grants'), None, 'I04', 'Direct Access Grants（ROPC）'),
    (('flows', 'service_accounts'), 'client_credentials', 'I05', 'Service accounts（client credentials）'),
    (('standard_token_exchange',), 'token_exchange', 'I06', 'Standard token exchange'),
    (('device_authorization_grant',), 'device_code', 'I07', 'OAuth 2.0 Device Authorization Grant'),
    (('flows', 'implicit'), None, 'I10', 'Implicit Flow'),
    (('ciba_grant',), 'ciba', 'I13', 'OIDC CIBA Grant'),
    (('jwt_authorization_grant',), 'jwt_bearer', 'I15', 'JWT Authorization Grant'),
]
CLIENT_AUTH = {'client-secret': {'client_secret_basic', 'client_secret_post'}, 'client-jwt': {'private_key_jwt'},
               'client-secret-jwt': {'client_secret_jwt'}, 'client-x509': {'tls_client_auth', 'self_signed_tls_client_auth'}}
JSON_TYPES = {'string': 'string', 'long': 'integer', 'int': 'integer', 'integer': 'integer', 'boolean': 'boolean',
              'json': None}


class Finding(dict):
    def __init__(self, rule, severity, target, message, **extra):
        super().__init__(rule=rule, severity=severity, target=target, message=message, **extra)


# ------------------------------------------------------------------ inputs
def load_observed(path):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    if text.lstrip().startswith('{'):
        return keycloak.normalize(json.loads(text), source=os.path.basename(path))
    obs = yaml.safe_load(text)
    if isinstance(obs, dict) and obs.get('format') == keycloak.FORMAT:
        return obs
    if isinstance(obs, dict) and 'realm' in obs and 'clients' in obs and not isinstance(obs.get('realm'), dict):
        return keycloak.normalize(obs, source=os.path.basename(path))  # keycloak-config-cli YAML
    raise ValueError(f'{path}: neither {keycloak.FORMAT} nor a Keycloak realm representation')


def registry_key(path, styles):
    """Registry name of a claim path: '<namespace>.<name>' inside an object-style namespace, else the top-level name."""
    if len(path) >= 2 and styles.get(path[0]) == 'object':
        return f'{path[0]}.{path[1]}'
    return path[0]


def _full(c):
    ns = c.get('namespace')
    return f"{ns}.{c['name']}" if ns else c['name']


def _ns_styles(d):
    return {n.get('namespace'): n.get('style', 'object') for n in d['claims'].get('namespaces') or []}


def _registry_claims(d, styles):
    """registry key -> claim row (flat_prefix namespaces are written as one top-level name)."""
    out = {}
    for c in render._claims(d):
        ns = c.get('namespace')
        key = (ns + c['name']) if ns and styles.get(ns) == 'flat_prefix' else _full(c)
        out.setdefault(key, []).append(c)
    return out


def aud_values(obs, c, tok):
    """Audiences a client's token gets from Audience mappers (the client's own and those of its default and optional
    client scopes): {value: optional}. An ID token also names the client itself; the audience-resolve mapper adds the
    clients whose roles are in the role scope."""
    out = {}
    if tok == 'id':
        out[c['client_id_']] = False
    for src, opt, m in _sourced_mappers(obs, c):
        if tok not in m['tokens']:
            continue
        if m['type'] == 'oidc-audience-mapper':
            for k in ('audience', 'custom_audience'):
                if m.get(k):
                    out[m[k]] = out.get(m[k], True) and opt
        elif m['type'] == 'oidc-audience-resolve-mapper':
            for k, roles in c['effective_role_scope']['client'].items():
                if roles:
                    out[k] = out.get(k, True) and opt
    return out


def _sourced_mappers(obs, c):
    out = [('client', False, m) for m in c['mappers']]
    for opt, names in ((False, c['default_client_scopes']), (True, c['optional_client_scopes'])):
        for sc in names:
            out += [(f'scope:{sc}', opt, m) for m in (obs['client_scopes'].get(sc) or {}).get('mappers') or []]
    return out


def _ids(obs):
    for cid, c in obs['clients'].items():
        c['client_id_'] = cid


def _kc_tts(d):
    """Token types of the registry that the observed Keycloak issues. In a design with several IdPs (#58) the keycloak
    entry of catalog_answers.yaml `idp` names them (token_types); the token types of the other IdPs are not compared."""
    from . import coverage
    mine = coverage.idp_token_types(d.get('catalog_answers') or {}, 'keycloak')
    return [t for t in render._tts(d) if t.get('decision') in CARRIED and t.get('kind') in KC_TOKEN
            and (mine is None or t.get('id') in mine)]


def scoped_clients(d, obs, explicit=None):
    """Clients whose tokens a registry token type describes (disabled clients are left out, D13):
    an ID token type: the clients its aud names; an access token type: the clients whose Audience mappers (own or
    of their client scopes) write one of its aud values, and the clients of the ID token types (the relying party
    that gets the ID token also gets the access token, so a moved or changed Audience mapper does not drop it).
    Returns {client: {token type id: kc token}}."""
    tts = _kc_tts(d)
    out = {}
    enabled = {cid: c for cid, c in obs['clients'].items() if c['enabled'] and not c['bearer_only']
               and not (explicit and cid not in explicit)}
    for cid, c in enabled.items():
        for t in tts:
            if t['kind'] == 'id_token' and (cid in set(t.get('aud') or []) or explicit):
                out.setdefault(cid, {})[t['id']] = 'id'
    for cid, c in enabled.items():
        for t in tts:
            if t['kind'] == 'access_token' and (set(t.get('aud') or []) & set(aud_values(obs, c, 'access'))
                                                or cid in out or explicit):
                out.setdefault(cid, {})[t['id']] = 'access'
    return out


def resource_clients(d, obs, scope):
    """Clients that a scoped access token is addressed to (the API's own client, e.g. saas-api): they can exchange
    that token, so the switches the catalogue answers 対象外 are checked on them too (PR #47 check, 2)."""
    tts = {t['id']: t for t in render._tts(d)}
    names = {a for kinds in scope.values() for tid, tok in kinds.items() if tok == 'access' for a in tts[tid].get('aud') or []}
    return sorted(n for n in names if n in obs['clients'] and n not in scope and obs['clients'][n]['enabled'])


# ------------------------------------------------------------------ rules
def rule_claims(d, obs, scope, styles, reg):
    """D1 a claim the configuration emits is not in the registry for that token type (or is rejected there);
    D2 a registry claim of the token type is not emitted; D3 a mapper's type or shape differs from the registry."""
    f = []
    tts = {t['id']: t for t in render._tts(d)}
    for cid, kinds in sorted(scope.items()):
        c = obs['clients'][cid]
        for tid, tok in sorted(kinds.items()):
            t = tts[tid]
            want = {k for k, rows in reg.items() for r in rows if r.get('decision') in CARRIED and tid in (r.get('carried_in') or [])}
            rejected = {k for k, rows in reg.items() for r in rows if r.get('decision') == '却下'}
            emitted = {}
            for e in c['emits'][tok]:
                emitted.setdefault(registry_key(e['claim'], styles), []).append(e)
            for key in sorted(emitted):
                if key in want:
                    continue
                es = emitted[key]
                optional = all(e['optional'] for e in es)
                by = '、'.join(sorted({(e['mapper'] and f"マッパー {e['mapper']}（{e['source']}）") or 'Keycloak（マッパーなし）' for e in es}))
                why = '台帳で却下したクレーム' if key in rejected else f'台帳で {tid} に載せると宣言していないクレーム'
                f.append(Finding('D1', WARN if optional else ERROR, f'{cid}:{tid}:{key}',
                                 f"{why} {key} を、{by} が {tid} に出す" +
                                 ('（任意のクライアントスコープ。要求されたときだけ）' if optional else ''),
                                 client=cid, token_type=tid, claim=key))
            required = set(t.get('required_claims') or [])
            for key in sorted(want - set(emitted)):
                f.append(Finding('D2', ERROR if key in required else WARN, f'{cid}:{tid}:{key}',
                                 f"台帳で {tid} に載せる {key} を、設定のどのマッパーも出さない" +
                                 ('（required_claims にある）' if key in required else ''),
                                 client=cid, token_type=tid, claim=key))
            for key, es in sorted(emitted.items()):
                rows = [r for r in reg.get(key, []) if r.get('decision') in CARRIED]
                if not rows:
                    continue
                r = rows[0]
                for e in es:
                    m = next((m for m in _all_mappers(obs, c) if m['name'] == e['mapper'] and m['claim'] == e['claim']), None)
                    if not m or len(e['claim']) > (2 if styles.get(e['claim'][0]) == 'object' else 1):
                        continue
                    jt = JSON_TYPES.get(str(m.get('json_type', '')).lower())
                    if jt and jt != r.get('type') and not (jt == 'integer' and r.get('type') == 'number'):
                        f.append(Finding('D3', ERROR, f'{cid}:{tid}:{key}',
                                         f"マッパー {m['name']} の JSON の型 {m['json_type']} が、台帳の型 {r.get('type')} と違う",
                                         client=cid, token_type=tid, claim=key))
                    if 'multivalued' in m and m['multivalued'] != (r.get('shape') == 'array'):
                        f.append(Finding('D3', ERROR, f'{cid}:{tid}:{key}',
                                         f"マッパー {m['name']} の Multivalued が {'ON' if m['multivalued'] else 'OFF'} で、台帳の形 {r.get('shape')} と違う",
                                         client=cid, token_type=tid, claim=key))
    return f


def _all_mappers(obs, c):
    return [m for _, _, m in _sourced_mappers(obs, c)]


def rule_aud(d, obs, scope):
    """D4 (aud) the audiences the configuration writes differ from the token type's aud in the registry: a value is
    missing, or an extra value is added (an extra value from an optional client scope only when requested: warn)."""
    f = []
    tts = {t['id']: t for t in render._tts(d)}
    for cid, kinds in sorted(scope.items()):
        c = obs['clients'][cid]
        for tid, tok in sorted(kinds.items()):
            want = set(tts[tid].get('aud') or [])
            got = aud_values(obs, c, tok)
            for v in sorted(want - set(got)):
                f.append(Finding('D4', ERROR, f'{cid}:{tid}:aud', f'台帳の {tid} の aud {v} を、設定が出さない（Audience マッパーの値か場所が変わった）',
                                 client=cid, token_type=tid, claim='aud'))
            for v in sorted(set(got) - want):
                f.append(Finding('D4', WARN if got[v] else ERROR, f'{cid}:{tid}:aud',
                                 f'設定が {tid} の aud に、台帳に無い {v} を足す' + ('（任意のクライアントスコープ。要求されたときだけ）' if got[v] else ''),
                                 client=cid, token_type=tid, claim='aud'))
    return f


WORD = re.compile(r'[A-Za-z0-9_]+')
ATTR_MAPPERS = {'oidc-usermodel-attribute-mapper', 'oidc-usermodel-property-mapper'}


def rule_source(d, obs, scope, styles, reg):
    """D3 (source) a user attribute / property mapper reads an attribute that the registry row does not name as the
    claim's source (source_system or the authoritative_writer text), e.g. user_id read from username instead of id."""
    f = []
    for cid, kinds in sorted(scope.items()):
        c = obs['clients'][cid]
        for tid, tok in sorted(kinds.items()):
            for m in _all_mappers(obs, c):
                if m['type'] in keycloak.ROLE_MAPPERS and m.get('claim') and tok in m['tokens']:
                    key = registry_key(m['claim'], styles)
                    rows = [r for r in reg.get(key, []) if r.get('decision') in CARRIED and tid in (r.get('carried_in') or [])]
                    writer = ' '.join(str(w.get('writer') or '') for r in rows for w in r.get('authoritative_writer') or [])
                    want = 'Realm Role' if m['type'] == 'oidc-usermodel-realm-role-mapper' else 'Client Role'
                    if 'Role' in writer and want not in writer:
                        f.append(Finding('D3', ERROR, f'{cid}:{tid}:{key}',
                                         f"マッパー {m['name']} の種類は {m['type']}（{want}）だが、台帳の書き手は「{writer}」",
                                         client=cid, token_type=tid, claim=key))
                    continue
                if m['type'] not in ATTR_MAPPERS or not m.get('claim') or tok not in m['tokens'] or not m.get('user_attribute'):
                    continue
                key = registry_key(m['claim'], styles)
                rows = [r for r in reg.get(key, []) if r.get('decision') in CARRIED and tid in (r.get('carried_in') or [])]
                if not rows:
                    continue
                r = rows[0]
                text = ' '.join([str(r.get('source_system') or '')] + [str(w.get('writer') or '') for w in r.get('authoritative_writer') or []])
                if m['user_attribute'] not in set(WORD.findall(text)):
                    f.append(Finding('D3', ERROR, f'{cid}:{tid}:{key}',
                                     f"マッパー {m['name']} は利用者の属性 {m['user_attribute']} を読むが、台帳の {r['id']} の source_system・書き手にその属性の名前が無い（{text}）",
                                     client=cid, token_type=tid, claim=key))
    return f


def _subschema(d, tt, path, styles):
    sch = render.payload_schema(d, tt, 'issuer')
    node = sch
    for i, p in enumerate(path[:2]):
        props = node.get('properties') or {}
        if p not in props:
            return None
        node = props[p]
        if not (styles.get(p) == 'object' and i == 0):
            break
    return node


def rule_values(d, obs, scope, styles, reg):
    """D4 a value the configuration fixes (a hardcoded claim, the roles a role mapper can emit) is outside what the
    registry allows (the issuer-conformance schema of the token type: enum, pattern, maxLength, maxItems)."""
    import jsonschema
    f = []
    tts = {t['id']: t for t in render._tts(d)}
    for cid, kinds in sorted(scope.items()):
        c = obs['clients'][cid]
        for tid, tok in sorted(kinds.items()):
            for m in _all_mappers(obs, c):
                if not m.get('claim') or tok not in m['tokens']:
                    continue
                key = registry_key(m['claim'], styles)
                if not any(r.get('decision') in CARRIED and tid in (r.get('carried_in') or []) for r in reg.get(key, [])):
                    continue
                sub = _subschema(d, tts[tid], m['claim'], styles)
                if sub is None:
                    continue
                if m['type'] == 'oidc-hardcoded-claim-mapper' and 'value' in m:
                    v = m['value']
                    jt = str(m.get('json_type', 'String')).lower()
                    try:
                        v = json.loads(v) if jt == 'json' else int(v) if jt in ('long', 'int') else (str(v).lower() == 'true') if jt == 'boolean' else v
                    except ValueError:
                        pass
                    errs = list(jsonschema.Draft202012Validator(sub).iter_errors(v))
                    if errs:
                        f.append(Finding('D4', ERROR, f'{cid}:{tid}:{key}',
                                         f"Hardcoded claim マッパー {m['name']} の値 {json.dumps(v, ensure_ascii=False)} が、台帳の値の制約を満たさない（{errs[0].message}）",
                                         client=cid, token_type=tid, claim=key))
                if m['type'] in keycloak.ROLE_MAPPERS:
                    ers = c['effective_role_scope']
                    if m['type'] == 'oidc-usermodel-realm-role-mapper':
                        roles = list(ers['realm'])
                    elif m.get('role_client'):
                        roles = list(ers['client'].get(m['role_client']) or [])
                    else:
                        roles = sorted({r for v in ers['client'].values() for r in v})
                    if m.get('role_prefix'):
                        roles = [m['role_prefix'] + r for r in roles]
                    value = roles if sub.get('type') == 'array' else (roles[0] if roles else '')
                    errs = list(jsonschema.Draft202012Validator(sub).iter_errors(value))
                    if errs:
                        msgs = list(dict.fromkeys(e.message for e in errs))
                        f.append(Finding('D4', ERROR, f'{cid}:{tid}:{key}',
                                         f"ロールのマッパー {m['name']} が出しうるロール（クライアントのロールのスコープ：{', '.join(roles) or 'なし'}）が、台帳の値の制約を満たさない（{'; '.join(msgs[:4])}{' ほか' if len(msgs) > 4 else ''}）",
                                         client=cid, token_type=tid, claim=key, roles=roles))
    return f


def _cmp_lifetime(f, rule, target, label, configured, declared):
    if configured is None or declared is None:
        return
    if configured > declared:
        f.append(Finding(rule, ERROR, target, f'{label}が、設定では {configured} 秒で、台帳の {declared} 秒より長い'))
    elif configured < declared:
        f.append(Finding(rule, WARN, target, f'{label}が、設定では {configured} 秒で、台帳の {declared} 秒より短い（台帳を実態に合わせるか、設定を戻す）'))


def rule_lifetimes(d, obs, scope):
    """D5 token and session lifetimes: AT and ID token (access token lifespan, client override), RT and the IdP
    session (SSO Session Idle / Max, client session overrides), authorization code (Client login timeout)."""
    f = []
    r = dict(obs['realm'])
    rm = ''
    if r.get('remember_me'):
        # with Remember Me on, a session that ticked it lives by the RememberMe values when they are longer
        for k in ('sso_session_idle_timeout', 'sso_session_max_lifespan'):
            v = r.get(k + '_remember_me') or 0
            if v > (r.get(k) or 0):
                r[k] = v
                rm = '。Remember Me が ON なので、覚えたセッションの長いほうの値で比べた'
    tts = [t for t in render._tts(d) if t.get('decision') in CARRIED]
    for cid, kinds in sorted(scope.items()):
        c = obs['clients'][cid]
        at_life = c.get('access_token_lifespan') or r['access_token_lifespan']
        for tid in sorted(kinds):
            t = next(t for t in tts if t['id'] == tid)
            _cmp_lifetime(f, 'D5', f'{cid}:{tid}', f'{tid} の寿命（{"クライアントの Access Token Lifespan" if c.get("access_token_lifespan") else "レルムの accessTokenLifespan"}）',
                          at_life, t.get('max_lifetime'))
        idle = min(x for x in (r['sso_session_idle_timeout'], c.get('client_session_idle_timeout') or r.get('client_session_idle_timeout') or None) if x)
        mx = min(x for x in (r['sso_session_max_lifespan'], c.get('client_session_max_lifespan') or r.get('client_session_max_lifespan') or None) if x)
        for t in tts:
            if t.get('kind') == 'refresh_token':
                _cmp_lifetime(f, 'D5', f'{cid}:{t["id"]}', f'{t["id"]} の idle（SSO Session Idle とクライアントのセッションの idle の短いほう{rm}）', idle, t.get('idle_timeout'))
                _cmp_lifetime(f, 'D5', f'{cid}:{t["id"]}', f'{t["id"]} の最大（SSO Session Max とクライアントのセッションの最大の短いほう{rm}）', mx, t.get('max_lifetime'))
    for t in tts:
        if t.get('kind') == 'session' and t.get('stored_at') == 'idp':
            _cmp_lifetime(f, 'D5', f'realm:{t["id"]}', f'{t["id"]} の idle（ssoSessionIdleTimeout{rm}）', r['sso_session_idle_timeout'], t.get('idle_timeout'))
            _cmp_lifetime(f, 'D5', f'realm:{t["id"]}', f'{t["id"]} の最大（ssoSessionMaxLifespan{rm}）', r['sso_session_max_lifespan'], t.get('max_lifetime'))
        if t.get('kind') == 'authorization_code':
            _cmp_lifetime(f, 'D5', f'realm:{t["id"]}', f'{t["id"]} の寿命（Client login timeout、accessCodeLifespan）', r['access_code_lifespan'], t.get('max_lifetime'))
    return f


def rule_refresh(d, obs, scope):
    """D6 RT rotation: the registry's rotation (token_types rt_rotation, issuance_profile rt_strategy) against the
    realm's Revoke Refresh Token and Refresh Token Max Reuse; refresh tokens off on a client whose registry has RT."""
    f = []
    r = obs['realm']
    profile = d['token_types'].get('issuance_profile') or {}
    strategy = (profile.get('rt_strategy') or {}).get('value')
    rts = [t for t in render._tts(d) if t.get('decision') in CARRIED and t.get('kind') == 'refresh_token']
    for t in rts:
        rot = (t.get('rt_rotation') or {}).get('rotation')
        want = rot if rot is not None else (strategy in ('rotation', 'rotation_reuse_detection') if strategy else None)
        if want is not None and bool(r.get('revoke_refresh_token')) != bool(want):
            f.append(Finding('D6', ERROR, f'realm:{t["id"]}',
                             f"台帳の {t['id']} はローテーション{'する' if want else 'しない'}が、レルムの Revoke Refresh Token は {'ON' if r.get('revoke_refresh_token') else 'OFF'}"))
        if want and (r.get('refresh_token_max_reuse') or 0) > 0:
            f.append(Finding('D6', ERROR, f'realm:{t["id"]}',
                             f"Refresh Token Max Reuse が {r['refresh_token_max_reuse']} で、同じ RT を複数回使える（台帳はローテーション）"))
    for cid in sorted(scope):
        if rts and not obs['clients'][cid].get('use_refresh_tokens', True):
            f.append(Finding('D6', ERROR, f'{cid}', f"台帳に RT（{rts[0]['id']}）があるが、クライアントの Use refresh tokens が OFF"))
    return f


def rule_header(d, obs, scope):
    """D7 the header typ of the access token (RFC 9068 switch) and the signing algorithms against the registry."""
    f = []
    tts = {t['id']: t for t in render._tts(d)}
    for cid, kinds in sorted(scope.items()):
        c = obs['clients'][cid]
        for tid, tok in sorted(kinds.items()):
            t = tts[tid]
            if tok == 'access' and t.get('typ'):
                typ = 'at+jwt' if c.get('access_token_header_type_rfc9068') else 'JWT'
                if typ.lower() != str(t['typ']).lower():
                    f.append(Finding('D7', ERROR, f'{cid}:{tid}', f"{tid} のヘッダーの typ は設定では {typ}（クライアントの Use \"at+jwt\" as access token header type）で、台帳の {t['typ']} と違う"))
            alg = c.get('access_token_signed_response_alg' if tok == 'access' else 'id_token_signed_response_alg') or obs['realm'].get('default_signature_algorithm')
            if alg and t.get('alg_allowlist') and alg not in t['alg_allowlist']:
                f.append(Finding('D7', ERROR, f'{cid}:{tid}', f"{tid} の署名のアルゴリズムは設定では {alg} で、台帳の alg_allowlist {t['alg_allowlist']} にない"))
    return f


def rule_client(d, obs, scope):
    """D8 client type and client authentication against issuance_profile."""
    f = []
    p = d['token_types'].get('issuance_profile') or {}
    ctype = (p.get('client_type') or {}).get('value')
    cauth = (p.get('client_auth') or {}).get('value')
    for cid in sorted(scope):
        c = obs['clients'][cid]
        if ctype in ('confidential', 'fapi') and c['public_client']:
            f.append(Finding('D8', ERROR, cid, f'台帳のクライアントの種類は {ctype} だが、設定は公開クライアント（Client authentication が OFF）'))
        if ctype == 'public' and not c['public_client']:
            f.append(Finding('D8', ERROR, cid, '台帳のクライアントの種類は public だが、設定は機密クライアント'))
        if cauth and not c['public_client']:
            allowed = CLIENT_AUTH.get(c['client_authenticator'])
            if allowed is not None and cauth not in allowed:
                f.append(Finding('D8', ERROR, cid, f"台帳のクライアント認証は {cauth} だが、設定の Client Authenticator は {c['client_authenticator']}"))
    return f


def _answers(d):
    return {a.get('event'): a for a in (d['catalog_answers'].get('answers') or [])}


def _get(c, path):
    v = c
    for p in path:
        v = (v or {}).get(p)
    return v


def rule_resource_switches(d, obs, resources):
    """D9 on the clients an access token is addressed to: a switch whose catalogue event is answered 対象外 is on
    (Standard token exchange on saas-api makes I06 happen: 400 -> 200, scenario-a-t1.exchange.json)."""
    f = []
    ans = _answers(d)
    for cid in resources:
        c = obs['clients'][cid]
        for path, grant, event, label in SWITCHES:
            a = ans.get(event) or {}
            if _get(c, path) and a.get('answer') == '対象外':
                f.append(Finding('D9', ERROR, f'{cid}:{event}', f'受け手のクライアント {cid}（AT の aud）で {label} が ON（カタログの {event} は「対象外」。前提：{a.get("assumption")}）',
                                 client=cid, event=event))
    return f


def rule_switches(d, obs, scope):
    """D9 a grant switch is on that the registry does not use (not in issuance_profile.grants, or its catalogue event
    answered 対象外), or a grant the registry uses is off; PKCE is not forced to S256 when the registry uses it."""
    f = []
    grants = set(((d['token_types'].get('issuance_profile') or {}).get('grants') or {}).get('value') or [])
    ans = _answers(d)
    for cid in sorted(scope):
        c = obs['clients'][cid]
        for path, grant, event, label in SWITCHES:
            on = bool(_get(c, path))
            a = ans.get(event) or {}
            allowed = (grant in grants if grant else False) or a.get('answer') == '該当'
            if on and not allowed:
                why = []
                if grant:
                    why.append(f'issuance_profile.grants に {grant} がない')
                else:
                    why.append('台帳の grant の語彙にない方式')
                if a.get('answer') == '対象外':
                    why.append(f'カタログの {event} は「対象外」（前提：{a.get("assumption")}）')
                f.append(Finding('D9', ERROR, f'{cid}:{event}', f'{label} が ON（' + '。'.join(why) + '）', client=cid, event=event))
            if not on and grant and grant in grants and a.get('answer') != '対象外':
                f.append(Finding('D9', ERROR, f'{cid}:{event}', f'{label} が OFF だが、台帳の issuance_profile.grants に {grant} がある', client=cid, event=event))
        if 'authorization_code_pkce' in grants and c['flows']['standard'] and c.get('pkce_method') != 'S256':
            f.append(Finding('D9', ERROR, f'{cid}:I01', f"台帳は認可コード＋PKCE だが、クライアントの PKCE Method が {c.get('pkce_method') or '未設定（PKCE を強制しない）'}", client=cid, event='I01'))
    return f


def rule_full_scope(d, obs, scope):
    """D10 Full Scope Allowed is on: every role of the realm can reach the token (Keycloak recommends turning it off,
    #4 facts K15)."""
    return [Finding('D10', ERROR, cid, 'Full Scope Allowed が ON（レルムのすべてのロールがトークンに出うる。'
                    'クライアントの Client scopes > Dedicated scope > Scope で OFF にし、載せるロールを割り当てる）', client=cid)
            for cid in sorted(scope) if obs['clients'][cid]['full_scope_allowed']]


def rule_token_kinds(d, obs, scope):
    """D11 a token kind or variant that the registry rejects can be issued: logout tokens (Backchannel logout URL),
    DPoP-bound tokens, lightweight access tokens (I03), offline refresh tokens (I08), organization claims (I24)."""
    f = []
    tts = render._tts(d)
    rejected = {t.get('kind') for t in tts if t.get('decision') == '却下'}
    adopted = {t.get('kind') for t in tts if t.get('decision') in CARRIED}
    sender = ((d['token_types'].get('issuance_profile') or {}).get('sender_constraint') or {}).get('value')
    ans = _answers(d)
    r = obs['realm']
    for cid in sorted(scope):
        c = obs['clients'][cid]
        if c.get('backchannel_logout_url') and ('logout_token' in rejected or 'logout_token' not in adopted):
            f.append(Finding('D11', ERROR, f'{cid}:I09', f"Backchannel logout URL が設定されていて、ログアウトトークンを送る（台帳でログアウトトークンを{'却下' if 'logout_token' in rejected else '採用していない'}）", client=cid))
        if c.get('dpop_bound_access_tokens') and sender != 'dpop':
            f.append(Finding('D11', ERROR, f'{cid}:I29', f'Require DPoP bound tokens が ON だが、台帳の送信者制約は {sender}', client=cid))
        if c.get('lightweight_access_token') and (ans.get('I03') or {}).get('answer') != '該当':
            f.append(Finding('D11', ERROR, f'{cid}:I03', '軽量アクセストークン（Always use lightweight access token）が ON（カタログの I03 は該当でない）', client=cid))
        offline = 'offline_access' in c['default_client_scopes'] + c['optional_client_scopes']
        if offline and (ans.get('I08') or {}).get('answer') == '対象外':
            has_role = 'offline_access' in (r['default_roles']['realm'] or [])
            f.append(Finding('D11', ERROR, f'{cid}:I08',
                             'クライアントに offline_access のクライアントスコープが付いていて、オフラインの RT を出しうる（カタログの I08 は「対象外」）'
                             + ('。既定のロールにも offline_access がある' if has_role else ''), client=cid))
        org = 'organization' in c['default_client_scopes'] + c['optional_client_scopes']
        if org and r.get('organizations_enabled') and (ans.get('I24') or {}).get('answer') == '対象外':
            f.append(Finding('D11', ERROR, f'{cid}:I24', 'Organizations が有効なレルムで、クライアントに organization のクライアントスコープが付いている（カタログの I24 は「対象外」）', client=cid))
    for p in r.get('client_profiles') or []:
        if 'use-lightweight-access-token' in p['executors'] and (ans.get('I03') or {}).get('answer') != '該当':
            f.append(Finding('D11', WARN, f"realm:profile:{p['name']}", f"クライアントのプロファイル {p['name']} に executor use-lightweight-access-token がある。どのクライアントに効くかは条件しだいで、静的には読まない（発行したトークンを --token で検証する）"))
    return f


def rule_unreadable(d, obs, scope):
    """D12 parts that are not read statically: mappers of unknown types (script mappers, extensions), client policies.
    The remedy is to validate an issued token against the issuer-conformance schema (--token)."""
    f = []
    for cid in sorted(scope):
        c = obs['clients'][cid]
        for m in _all_mappers(obs, c):
            if m.get('readable') is False:
                f.append(Finding('D12', WARN, f"{cid}:{m['name']}", f"マッパー {m['name']}（{m['type']}）の出すクレームを静的に読めない。発行したトークンを --token で発行側の検査用スキーマと照合する", client=cid))
    pol = [p['name'] for p in obs['realm'].get('client_policies') or [] if p.get('enabled', True)]
    if pol:
        f.append(Finding('D12', WARN, 'realm:client-policies', f"クライアントのポリシー（{', '.join(pol)}）は静的に評価しない。発行したトークンを --token で照合する"))
    return f


def rule_out_of_scope(obs, scope, resources=()):
    """D13 clients that no registry token type describes but that can issue tokens (info: the consumers reject their
    tokens by aud and azp, which the registry's enforced_at must say)."""
    out, disabled = [], sorted(cid for cid, c in obs['clients'].items() if not c['enabled'])
    for cid, c in sorted(obs['clients'].items()):
        if cid in scope or cid in resources or not c['enabled'] or c['bearer_only']:
            continue
        flows = [k for k, v in c['flows'].items() if v] + [k for k in ('standard_token_exchange', 'device_authorization_grant', 'ciba_grant', 'jwt_authorization_grant') if c.get(k)]
        if flows:
            out.append(f"{cid}（{'・'.join(flows)}{'、既定のクライアント' if c['builtin'] else ''}）")
    f = []
    if out:
        f.append(Finding('D13', INFO, 'realm:clients', '台帳のどのトークン種別も宛先にしないが、トークンを出せるクライアント：' + '、'.join(out) +
                         '。受け手が aud と azp で拒否することを台帳の enforced_at で確かめる'))
    if disabled:
        f.append(Finding('D13', INFO, 'realm:disabled-clients', '無効なクライアント（トークンを出さないので比べない）：' + '、'.join(disabled)))
    return f


def rule_tokens(d, tokens):
    """D14 an issued token (decoded payload) does not conform to the issuer-conformance schema of its token type."""
    f = []
    for tid, path in tokens:
        payload = render.read_payload(path)
        for e in render.validate_payload(d, payload, tid, 'issuer'):
            f.append(Finding('D14', ERROR, f'token:{tid}', f'{os.path.basename(path)}: {e}', token_type=tid, file=os.path.basename(path)))
    return f


def run(design_dir, observed, clients=None, tokens=()):
    d = render.load_design(design_dir)
    obs = copy.deepcopy(observed) if isinstance(observed, dict) else load_observed(observed)
    styles = _ns_styles(d)
    reg = _registry_claims(d, styles)
    _ids(obs)
    scope = scoped_clients(d, obs, clients)
    resources = resource_clients(d, obs, scope)
    f = []
    if not scope:
        f.append(Finding('D0', ERROR, 'clients', '台帳のトークン種別（AT の aud・ID トークンの aud）に当たるクライアントが設定にない。--client で指定する'))
    else:
        covered = {tid for kinds in scope.values() for tid in kinds}
        for t in _kc_tts(d):
            if t['id'] not in covered:
                f.append(Finding('D0', ERROR, t['id'], f"台帳の {t['id']}（{t['kind']}、aud {t.get('aud')}）を出すクライアントが設定にない"))
    for missing in sorted(set(clients or []) - set(obs['clients'])):
        f.append(Finding('D0', ERROR, missing, f'クライアント {missing} が設定にない'))
    f += rule_claims(d, obs, scope, styles, reg)
    f += rule_values(d, obs, scope, styles, reg)
    f += rule_aud(d, obs, scope)
    f += rule_source(d, obs, scope, styles, reg)
    f += rule_lifetimes(d, obs, scope)
    f += rule_refresh(d, obs, scope)
    f += rule_header(d, obs, scope)
    f += rule_client(d, obs, scope)
    f += rule_switches(d, obs, scope)
    f += rule_resource_switches(d, obs, resources)
    f += rule_full_scope(d, obs, scope)
    f += rule_token_kinds(d, obs, scope)
    f += rule_unreadable(d, obs, scope)
    f += rule_out_of_scope(obs, scope, resources)
    f += rule_tokens(d, tokens)
    counts = {s: sum(1 for x in f if x['severity'] == s) for s in core.SEVERITIES}
    return {'format': FORMAT, 'design': core._rel(os.path.abspath(design_dir), core.ROOT),
            'observed': {'realm': obs['realm']['name'], 'keycloak_version': obs['source'].get('keycloak_version'),
                         'file': obs['source'].get('file')},
            'clients': {cid: dict(sorted(k.items())) for cid, k in sorted(scope.items())},
            'resource_clients': resources,
            'tokens': [{'token_type': t, 'file': os.path.basename(p)} for t, p in tokens],
            'counts': counts, 'findings': f}


def format_table(res):
    o = res['observed']
    lines = [f"claim_lint drift  design={res['design']}  realm={o['realm']}  keycloak={o['keycloak_version']}",
             'clients: ' + ('; '.join(f"{c} -> {', '.join(f'{t} ({k})' for t, k in ks.items())}" for c, ks in res['clients'].items()) or '(none)')]
    if res['tokens']:
        lines.append('tokens: ' + ', '.join(f"{t['token_type']}={t['file']}" for t in res['tokens']))
    lines.append('')
    rows = [('rule', 'severity', 'target', 'message')] + [(x['rule'], x['severity'], x['target'], x['message']) for x in res['findings']]
    w = [max(len(str(r[i])) for r in rows) for i in range(3)]
    for r in rows:
        lines.append(f'{r[0]:<{w[0]}}  {r[1]:<{w[1]}}  {r[2]:<{w[2]}}  {r[3]}')
    c = res['counts']
    lines += ['', f"error {c['error']}, warn {c['warn']}, info {c['info']}", 'FAIL' if c['error'] else 'OK']
    return '\n'.join(lines)


def main(argv):
    ap = argparse.ArgumentParser(prog='claim_lint drift', description='Compare an IdP configuration with the registry (#30).')
    ap.add_argument('design_dir')
    ap.add_argument('observed', help='output of claim_lint import keycloak, or a realm export (normalized on the fly)')
    ap.add_argument('--client', action='append', help='only these clients (default: the clients the registry token types address)')
    ap.add_argument('--token', action='append', default=[], metavar='TYPE=FILE',
                    help='an issued token (payload JSON, fixture or compact JWS) to validate against the issuer schema of TYPE')
    ap.add_argument('--format', choices=('table', 'json'), default='table')
    ap.add_argument('--json-out')
    a = ap.parse_args(argv)
    tokens = []
    for t in a.token:
        if '=' not in t:
            ap.error(f'--token {t}: expected TYPE=FILE')
        tid, path = t.split('=', 1)
        tokens.append((tid, path))
    try:
        res = run(a.design_dir, a.observed, a.client, tokens)
    except (ValueError, OSError) as e:
        sys.stderr.write(f'claim_lint drift: {e}\n')
        return 2
    if a.json_out:
        with open(a.json_out, 'w', encoding='utf-8') as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)
    text = json.dumps(res, ensure_ascii=False, indent=1) if a.format == 'json' else format_table(res)
    sys.stdout.buffer.write((text + '\n').encode('utf-8'))
    return 1 if res['counts']['error'] else 0
