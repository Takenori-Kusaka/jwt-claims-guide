# -*- coding: utf-8 -*-
"""claim_lint semantic rules (#6): L1a, L1b, L2-L9, L15-L18, L21-L23, L25, L27, L31, L37, L43, L62-L73, and L74 (#58).

Each rule reads the declarations of the design (claims.yaml, token_types.yaml, hops.yaml, catalog_answers.yaml and the
claim_request_*.md files) and reports what contradicts them. The rules see declarations only: whether a consumer really
checks what its enforced_at says is a runtime question (#8). The severities, the evidence of each rule and the false
positives measured on scenario A are in tools/claim_lint/RULES.md.

`run()` returns (findings, checked): checked[rule] is the number of rows (claims, token types, hops, ...) the rule examined,
so that RULES.md can tell "0 findings in 12 rows" from "never ran" (0 opportunities).
"""
import datetime
import glob
import os
import re

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ERROR, WARN, INFO = 'error', 'warn', 'info'
ADOPTED = ('採用', '既定どおり')

# Severity of each rule (or rule part) after measuring false positives on scenario A (RULES.md, 「重大度の決め方」).
# A rule enters as warn and becomes error only when it examined at least one row of scenario A and had no false positive.
SEV = {
    'L1a': ERROR, 'L1b': ERROR, 'L2': WARN, 'L3': ERROR, 'L4': ERROR, 'L5': ERROR, 'L6': ERROR, 'L7': ERROR,
    'L8': WARN, 'L9': ERROR, 'L15': WARN, 'L16': ERROR, 'L17': ERROR, 'L18': WARN, 'L21': ERROR, 'L22': ERROR,
    'L23': ERROR, 'L25': ERROR, 'L27': ERROR, 'L31': ERROR, 'L37': ERROR, 'L43': WARN,
    'L62': WARN, 'L63': WARN, 'L64': WARN, 'L65': ERROR, 'L66': WARN, 'L67': WARN,
    'L68': WARN, 'L69': WARN, 'L70': WARN, 'L71': WARN, 'L72': ERROR,  # #4: the slide-142 gate, required in Lite too; 0 false positives on scenario A (4 claims)
    'L73': WARN,
    'L74': WARN,  # #58: new rule, starts as warn (RULES.md)
}
LITE_WARN = {'L22'}  # issue #6: L22 is warn in Lite


class _F(dict):
    def __init__(self, rule, severity, target, message):
        super().__init__(rule=rule, severity=severity, target=target, message=message)


def _empty(v):
    if isinstance(v, str):
        return v.strip() == ''
    if isinstance(v, (list, tuple)):
        return all(_empty(x) for x in v)
    return v is None or v == {}


def _load(path):
    from .core import load_yaml  # same loader as the rest of claim_lint (dates stay strings, no duplicate keys)
    return load_yaml(path) or {}


def full_names(c):
    """The spellings a consumer may use for a claim in required_claims: name, and namespace + name in the usual forms."""
    n, ns = c.get('name'), c.get('namespace')
    if not ns:
        return {n}
    return {n, ns + n, ns + '.' + n, ns.rstrip('/') + '/' + n}


class Ctx:
    def __init__(self, docs, profile, design_dir, root, catalog_dir, today, caps_path=None):
        self.claims_doc = docs.get('claims') or {}
        self.claims = self.claims_doc.get('claims') or []
        self.tt_doc = docs.get('token_types') or {}
        self.tts = self.tt_doc.get('token_types') or []
        self.profile_doc = self.tt_doc.get('issuance_profile') or {}
        self.hops = (docs.get('hops') or {}).get('hops') or []
        self.answers = docs.get('catalog_answers') or {}
        self.profile, self.design_dir, self.root, self.catalog_dir = profile, design_dir, root, catalog_dir
        self.today = today or datetime.date.today()
        self.tt = {t.get('id'): t for t in self.tts}
        self.cid = {c.get('id'): c for c in self.claims}
        self.hop = {h.get('id'): h for h in self.hops}
        self.iana = {x['name']: x for x in (_load(os.path.join(HERE, 'iana_jwt_claims.yaml')).get('claims') or [])}
        self.drafts = _load(os.path.join(HERE, 'draft_claims.yaml')).get('drafts') or {}
        self.reserved = _load(os.path.join(HERE, 'idp_reserved.yaml')).get('idps') or {}
        self.idp_claims = _load(os.path.join(HERE, 'idp_claims.yaml')).get('idps') or {}  # #58: names an IdP product defines
        from . import coverage  # the IdPs of the design: one mapping or a list (#58)
        self.idps = coverage.idp_entries(self.answers)[0]
        self.caps = _load(caps_path or os.path.join(HERE, 'lifetime_caps.yaml')).get('caps') or {}
        self.effects = _load(os.path.join(root, 'templates', 'registry', 'issuance_effects.yaml')).get('effects') or []
        self.kinds = [k['id'] for k in (_load(os.path.join(catalog_dir, 'token_kinds.yaml')).get('kinds') or [])]
        self.findings, self.checked = [], {}

    # -- helpers
    def add(self, rule, target, message, severity=None):
        sev = severity or SEV[rule]
        if self.profile == 'lite' and rule in LITE_WARN and sev == ERROR:
            sev = WARN
        self.findings.append(_F(rule, sev, target, message))

    def count(self, rule, n=1):
        self.checked[rule] = self.checked.get(rule, 0) + n

    def adopted_claims(self):
        return [c for c in self.claims if c.get('decision') in ADOPTED]

    def adopted_tts(self):
        return [t for t in self.tts if t.get('decision') in ADOPTED]

    def carried(self, c):
        """Adopted token types that carry the claim."""
        return [self.tt[t] for t in c.get('carried_in') or [] if t in self.tt and self.tt[t].get('decision') in ADOPTED]

    def claims_in(self, tid):
        return [c for c in self.adopted_claims() if tid in (c.get('carried_in') or [])]

    def issuers_of(self, tid):
        """The IdP entries that issue the token type: the entries whose token_types name it; a single IdP without
        token_types issues every access token and ID token of the design."""
        named = [e for e in self.idps if e['token_types'] is not None and tid in e['token_types']]
        if named or len(self.idps) != 1 or self.idps[0]['token_types'] is not None:
            return named
        return list(self.idps) if (self.tt.get(tid) or {}).get('kind') in IDP_ISSUED else []

    def db_services(self):
        return {str(h.get('to', '')).lower() for h in self.hops if h.get('kind') in ('db_connection', 'broker_connection')}

    def writers(self, c):
        return list(c.get('authoritative_writer') or []) + list(c.get('modifiers') or [])


IDP_ISSUED = ('access_token', 'id_token')  # token kinds an IdP product issues to the organization's clients


def upstreams(hop):
    """The upstream hop IDs of a hop: `upstream` is one ID or, from #58, a list of IDs (several IdPs, one reissue)."""
    u = (hop or {}).get('upstream')
    if u is None:
        return []
    return list(u) if isinstance(u, list) else [u]


def _against(e):
    return set(e.get('against') or [])


# ------------------------------------------------------------------ L1a / L1b: names
ROLE_SYNONYM = re.compile(r'^(role|group|entitlement|user_?roles?|user_?groups?|app_?roles?|roles?_list|group_?list|permissions_?groups?)$', re.I)


def rule_l1a(x):
    for c in x.adopted_claims():
        if c.get('decision') == '採用' and ROLE_SYNONYM.match(c.get('name') or ''):
            x.add('L1a', c.get('id'), f"役割・グループ・資格に {c['name']} という名前を作っている。登録名 roles・groups・entitlements"
                                      '（RFC 9068 §7.2.1.1、RFC 7643 §4.1.2）を使う')
    for c in x.adopted_claims():
        x.count('L1a')  # every adopted row: the synonym check above and the registered-name check below
        if c.get('namespace') is not None or c.get('name') not in x.iana:
            continue
        reg, cid = x.iana[c['name']], c.get('id')
        if _empty(c.get('registered_ref')):
            x.add('L1a', cid, f"IANA の登録名 {c['name']}（{reg['ref']}）を使うのに registered_ref がない。登録どおりの意味なら参照を書く。"
                              '別の意味なら、組織の名前空間の下に別の名前で置く')
        rt, rs = reg.get('type'), reg.get('shape')
        if rt and c.get('type'):
            ok = c['type'] == rt or (rt == 'integer' and c['type'] in ('integer', 'number'))
            if not ok:
                x.add('L1a', cid, f"型 {c['type']} が登録（{rt}、{reg['ref']}）と違う。登録名を別の型で使わない")
        if rs and c.get('shape') and c['shape'] not in rs:
            x.add('L1a', cid, f"形 {c['shape']} が登録（{'・'.join(rs)}、{reg['ref']}）と違う")


def _iss_match(pattern, iss):
    rx = '^' + re.sub(r'\\\{[^}]*\\\}', '[^/]+', re.escape(pattern)) + '$'
    return re.match(rx, iss) is not None


def _draft_defined(c, drafts):
    """The name is pinned in draft_claims.yaml for the exact draft (name and version) that registered_ref cites and
    spec_version lists, and the claim is not used for authorization or identification (PR #44 review B06)."""
    ref = c.get('registered_ref') or {}
    m = re.match(r'^(draft-[a-z0-9-]+-\d{2}) §[0-9.]+$', str(ref.get('id') or ''))
    if not m or ref.get('kind') != 'spec' or m.group(1) not in (c.get('spec_version') or []):
        return None
    d = drafts.get(m.group(1)) or {}
    if c.get('name') not in (d.get('claims') or {}) or c.get('usage') in ('authz', 'identifier'):
        return None
    sec = re.search(r' (§[0-9.]+)$', str(ref.get('id') or ''))
    if not sec or sec.group(1) != d['claims'][c.get('name')]:
        return None  # the section that defines the name must be cited (PR #44 re-check)
    return m.group(1)


def _idp_defined_problem(x, c):
    """None when the row may keep a name that an IdP product defines (#58): the IdP is declared, the name is pinned for it
    in idp_claims.yaml, the row is carried in that IdP's access / ID token types only, no hop passes it on in another token
    or in a header, and every consumer receives one of those token types."""
    idp, name = str((c.get('idp_defined') or {}).get('idp') or ''), c.get('name')
    ent = next((e for e in x.idps if e['name'] == idp), None)
    if ent is None:
        return f'idp_defined.idp の {idp} が catalog_answers.yaml の idp にない'
    if name not in ((x.idp_claims.get(idp) or {}).get('claims') or []):
        return (f'{name} は tools/claim_lint/idp_claims.yaml の {idp} の一覧にない。IdP の文書で名前を確かめ、出どころと確かめた日を付けて'
                '一覧に足す（一覧にない名前は組織の名前空間の下に置く）')
    carried = c.get('carried_in') or []
    for t in carried:
        tt = x.tt.get(t) or {}
        if tt.get('kind') not in IDP_ISSUED or (ent['token_types'] is not None and t not in ent['token_types']):
            return (f'{t} は IdP {idp} が出す AT・ID トークンの種別でない。IdP が決めた名前のまま、入口より下流のトークンに載せない'
                    '（組織の名前空間のクレームに写す）')
    for h in x.hops:
        if c.get('id') in (h.get('custom_claims') or []) and h.get('token_type') not in carried:
            return f"ホップ {h.get('id')} が、IdP {idp} のトークンでない {h.get('token_type')} で運んでいる（下流へ名前のまま渡さない）"
        if any(fh.get('claim') == c.get('id') for fh in h.get('forwarded_headers') or []):
            return f"ホップ {h.get('id')} がヘッダーに転記している（下流へ名前のまま渡さない）"
    # (5) only the entry reads it: every consumer receives the IdP's token on an entry hop and mints the organization's
    # token itself (the exchanger of a reissue / exchange hop). A service that reads the IdP's name directly from the
    # IdP's token keeps the error (PR #70 check: scenario A's API reading realm_access must not pass)
    entries = {_service_name(h.get('to')) for h in x.hops if h.get('token_type') in carried and h.get('kind') == 'entry'}
    minters = {str(h.get('exchanger')) for h in x.hops if _minted(h)}
    # for an ID token the entry is the client it was issued to (the relying party, a BFF): a name of the token's aud, or
    # the service that presents this IdP's access tokens (the `from` of a hop that carries one). A row carried in an access
    # token too is held to the access token's condition for the API side
    clients = set()
    idts = [t for t in carried if (x.tt.get(t) or {}).get('kind') == 'id_token']
    if idts:
        mine = {t.get('id') for t in x.adopted_tts() if t.get('kind') == 'access_token'
                and (ent['token_types'] is None or t.get('id') in ent['token_types'])}
        clients = {_service_name(h.get('from')) for h in x.hops if h.get('token_type') in mine}
        clients |= {str(a) for t in idts for a in (x.tt.get(t) or {}).get('aud') or []}
    strangers = [s for s in c.get('consumers') or [] if not (s in entries and s in minters) and s not in clients]
    if strangers:
        return (f"受け手 {'・'.join(strangers)} は、このクレームが載る種別（{'・'.join(carried)}）を入口のホップ（kind: entry）で受け取り、"
                '組織のトークンに作り直す入口（reissue・exchange のホップの exchanger）ではない。IdP が決めた名前を読めるのは入口だけ'
                '（ID トークンでは、その IdP のトークンを持つクライアント）')
    return None


def rule_l1b(x):
    declared = {n.get('namespace') for n in x.claims_doc.get('namespaces') or []}
    for c in x.adopted_claims():
        cid, ns = c.get('id'), c.get('namespace')
        x.count('L1b')
        if ns is None and c.get('name') not in x.iana:
            if c.get('idp_defined'):
                # a name the IdP product defines (Entra tid / oid, Okta uid / cid, Cognito token_use ...; #58): the entry
                # reads it from the IdP's token. Pinned names only (idp_claims.yaml), and only inside the IdP's tokens
                problem = _idp_defined_problem(x, c)
                if problem is None:
                    idp = c['idp_defined']['idp']
                    src = ((x.idp_claims.get(idp) or {}).get('source') or {}).get('url', '')
                    x.add('L1b', cid, f"IdP {idp} が決めた名前 {c.get('name')}（名前空間なし・未登録。tools/claim_lint/idp_claims.yaml、{src}）。"
                                      f"{'・'.join(c.get('carried_in') or [])} にだけ載り、下流のトークンとヘッダーへは名前のまま渡さない。"
                                      '一覧にある名前に組織の意味を載せていないかは、レビューで確かめる', INFO)
                else:
                    x.add('L1b', cid, f"未登録の名前 {c.get('name')} を idp_defined（IdP が決めた名前）として書いているが、条件を満たさない：{problem}")
            elif c.get('decision') == '既定どおり' and not c.get('consumers'):
                x.add('L1b', cid, f"IdP が既定で出す私的名 {c.get('name')}（名前空間なし・未登録）。名前を決めたのは IdP で、受け手は読まない"
                                  '（consumers が空）ので error にしない。読む受け手を足すなら組織の名前空間に写す', INFO)
            elif _draft_defined(c, x.drafts):
                # a name that a versioned draft itself defines (Txn-Token req_wl, tctx; #4 scenario B): the name belongs to
                # the draft, so it cannot move into the organization's namespace. Still unregistered: warn (L14 asks for
                # spec_version and revisit_trigger)
                x.add('L1b', cid, f"未登録の名前 {c.get('name')} は草案（{c['registered_ref'].get('id')}）が定める名前"
                                  '（tools/claim_lint/draft_claims.yaml）。登録の前なので、草案の版（spec_version）と、'
                                  '登録・改名されたときの見直しの条件を確かめる', WARN)
            else:
                x.add('L1b', cid, f"未登録の名前 {c.get('name')} を名前空間なしで使っている。IANA の登録名を使うか、組織の名前空間"
                                  '（namespaces）の下に置く（衝突に強い名前、RFC 7519 §4.2・§4.3）')
        elif ns is not None:
            if ns not in declared:
                x.add('L1b', cid, f'名前空間 {ns} が namespaces に宣言されていない（持ち主のいない名前空間は衝突に強いと言えない）')
            elif not re.match(r'^(https?://[^/\s]+\.[^/\s]+|urn:)', ns):
                x.add('L1b', cid, f'名前空間 {ns} が URI（組織が管理するドメイン）でない')
        # a consumer trusts the claim only from issuers that may put it (slide:p01-attack-patterns)
        pats = c.get('issuers') or []
        for t in x.carried(c):
            for i in t.get('issuers') or []:
                iss = i.get('iss')
                if pats and iss and not any(_iss_match(p, iss) for p in pats):
                    x.add('L1b', cid, f"{t['id']} は iss {iss} を受け入れるが、このクレームの issuers にない。別の発行者が書いた同名のクレームを信じない")
    groups = {}
    for c in x.adopted_claims():
        # #58: a name that IdP products define (Entra scp is a space-delimited string, Okta scp an array) cannot be renamed
        # by the design, so the rows of such a name are compared within one IdP only
        own = c['idp_defined'].get('idp') if c.get('idp_defined') and c.get('namespace') is None \
            and c.get('name') not in x.iana and _idp_defined_problem(x, c) is None else None
        groups.setdefault((c.get('namespace'), c.get('name'), own), []).append(c)
    for (ns, name, _own), cs in groups.items():
        if len(cs) > 1 and len({(c.get('type'), (c.get('description') or '').strip()) for c in cs}) > 1:
            x.add('L1b', '・'.join(c.get('id') for c in cs),
                  f"同じ名前 {(ns or '') + name} の行が {len(cs)} 行あり、型か意味（description）が違う。発行者ごとに意味が違うなら別の名前にする")


# ------------------------------------------------------------------ L2: IdP-reserved claims
def rule_l2(x):
    for ent in x.idps:  # #58: every IdP of the design; with token_types, only the claims carried in that IdP's token types
        if ent['kind'] == 'self_built':
            continue  # the organization's own issuer: no product restriction to compare with
        _l2_one(x, ent)


def _l2_one(x, ent):
    idp, scope = ent['name'], ent['token_types']
    block = x.reserved.get(idp)
    if not block:
        x.add('L2', ent['target'], f'IdP {idp} の、書き換えを許さないクレームの一覧が tools/claim_lint/idp_reserved.yaml にない。'
                                   'L2 は確かめていない（IdP モジュール #4 で手で確かめる）', INFO)
        return
    imm = set(block.get('immutable') or [])
    pre = tuple(block.get('prefixes') or [])
    exc = set(block.get('prefix_exceptions') or [])
    sup = tuple(block.get('suppress_only_prefixes') or [])
    src = (block.get('source') or {}).get('url', '')
    for c in x.adopted_claims():
        if scope is not None and not scope & set(c.get('carried_in') or []):
            continue
        n = c.get('name') or ''
        locked = n in imm or (n.startswith(pre) and n not in exc) if pre else n in imm
        suppress_only = bool(sup) and n.startswith(sup)
        if not (locked or suppress_only):
            continue
        x.count('L2')
        hooks = [w for w in c.get('authoritative_writer') or [] if re.search(r'フック|hook|lambda', w.get('writer', ''), re.I)]
        for m in c.get('modifiers') or []:
            if locked or m.get('action') != '抑止':
                x.add('L2', c.get('id'), f"{idp} はクレーム {n} の{'追加・変更・抑止' if locked else '追加・変更'}を許さないのに、"
                                         f"modifiers で {m.get('writer')} が「{m.get('action')}」する（{src}）")
        if locked and hooks:
            x.add('L2', c.get('id'), f"{idp} はクレーム {n} をフックで書かせないのに、authoritative_writer がフック（{hooks[0].get('writer')}）（{src}）")


# ------------------------------------------------------------------ L3: mutable values as identifier / authz
MUTABLE_NAMES = {'email', 'preferred_username', 'upn', 'name', 'nickname', 'given_name', 'family_name', 'phone_number',
                 'username', 'cognito:username', 'unique_name'}


def rule_l3(x):
    for c in x.adopted_claims():
        if c.get('usage') not in ('identifier', 'authz'):
            continue
        x.count('L3')
        ip = c.get('identifier_properties') or {}
        why = []
        if c.get('name') in MUTABLE_NAMES:
            why.append(f"{c.get('name')} は利用者・管理者が変えられる名前")
        if ip.get('stable') is False:
            why.append('identifier_properties.stable が false')
        if ip.get('reassignable') is True:
            why.append('identifier_properties.reassignable が true（再利用で別の主体を指す）')
        if ip.get('id_scheme') in ('email', 'phone', 'username'):
            why.append(f"id_scheme が {ip['id_scheme']}")
        cats = [str(d) for d in c.get('data_category') or []]
        contact = [d for d in cats if d.startswith('user.contact')]
        if contact:
            why.append(f"data_category が {'・'.join(contact)}（連絡先は変わりうる）")
            if ip.get('id_scheme') not in (None, 'email', 'phone'):
                why.append(f"id_scheme {ip['id_scheme']} が data_category と食い違う")
        if why:
            x.add('L3', c.get('id'), f"変わりうる値（{'、'.join(why)}）を usage {c['usage']} に使っている。表示（display）に限るか、変わらない ID を使う")


# ------------------------------------------------------------------ L4: one writer per stage
def rule_l4(x):
    for c in x.adopted_claims():
        x.count('L4')
        stages = [w.get('stage') for w in c.get('authoritative_writer') or []]
        for s in sorted({s for s in stages if stages.count(s) > 1}):
            x.add('L4', c.get('id'), f'段階 {s} の authoritative_writer が {stages.count(s)} つある。段階ごとに書き手を 1 つにし、'
                                     'ほかは modifiers（追加・抑止・上書き）に書く')
        aw = {(w.get('stage'), w.get('writer')) for w in c.get('authoritative_writer') or []}
        for m in c.get('modifiers') or []:
            if (m.get('stage'), m.get('writer')) in aw:
                x.add('L4', c.get('id'), f"{m.get('writer')} が段階 {m.get('stage')} の書き手と modifiers の両方にいる")


# ------------------------------------------------------------------ L5: freshness against the token lifetime
# revocation means that end an issued token before exp for every claim it carries. db_lookup (the consumer asks the data
# store on each request) counts only for the claims its note names (e.g. "C-tenant-id"); session_delete and
# refresh_failure end the session, not the access token already issued
TOKEN_WIDE = {'introspection', 'status_list', 'ssf_caep', 'back_channel_logout', 'revocation_endpoint'}


def _never_in_schema(x):
    """volatility: never (the value does not change during the token's life) exists from #39 (#19). Before it, 0 was
    written for such values, so 0 is read the old way until the registry schema has `never`."""
    import json
    p = os.path.join(x.root, 'templates', 'registry', 'claims.schema.json')
    try:
        prop = json.load(open(p, encoding='utf-8'))['$defs']['claim']['properties']['volatility']
    except (OSError, KeyError, ValueError):
        return False
    prop = {k: v for k, v in prop.items() if k not in ('description', '$comment')}
    return '"never"' in json.dumps(prop)


def rule_l5(x):
    strict_zero = _never_in_schema(x)
    for c in x.adopted_claims():
        v = c.get('volatility')
        if v == 'never' or not isinstance(v, int) or isinstance(v, bool):
            continue  # never: no freshness to keep during the token's life
        pd = c.get('propagation_delay')
        if v > 0 and isinstance(pd, int):
            x.count('L5')
            if pd > v:
                x.add('L5', c.get('id'), f'propagation_delay（{pd} 秒）が volatility（{v} 秒）を超える。反映までの最悪の遅れが、許す時間より長い')
        if v == 0 and not strict_zero:
            continue  # before #39: 0 meant "never changes"
        for t in x.carried(c):
            ml = t.get('max_lifetime')
            if not isinstance(ml, int):
                continue
            x.count('L5')
            worst = ml + (t.get('max_clock_skew') or 0)
            if v >= worst:
                continue
            ok = [r for r in t.get('revocation') or [] if isinstance(r.get('delay_seconds'), int) and r['delay_seconds'] <= v
                  and (r.get('method') in TOKEN_WIDE or (r.get('method') == 'db_lookup' and c.get('id') in re.findall(r'C-[a-z0-9-]+', r.get('note') or '')))]
            ttl = t.get('introspection_cache_ttl')
            if not ok and not (isinstance(ttl, int) and ttl <= v):
                x.add('L5', c.get('id'), f"volatility（{v} 秒）が {t['id']} の受け入れの上限（max_lifetime {ml} 秒＋時計のずれ）より短いのに、"
                                         f"{v} 秒以内に反映する失効の手段（{t['id']} の revocation）がない。寿命を縮めるか、問い合わせに切り替えるか、失効を伝える")


# ------------------------------------------------------------------ L6: personal data in the browser, logging
PII = ('個人情報', '要配慮個人情報')


def rule_l6(x):
    for c in x.adopted_claims():
        cid = c.get('id')
        for t in x.carried(c):
            x.count('L6')
            in_browser = t.get('stored_at') == 'browser' or 'browser' in (t.get('visible_to') or [])
            if c.get('pii_category') in PII and in_browser:
                x.add('L6', cid, f"pii_category が {c['pii_category']} のクレームが、ブラウザに置かれる・読まれる {t['id']} に載る")
            if c.get('log_policy') == '記録しない' and t.get('log_policy') == '記録する':
                x.add('L6', cid, f"log_policy が「記録しない」なのに、{t['id']} はトークン全体を記録する（log_policy: 記録する）")
        if c.get('log_policy') == '記録しない' and any(i.get('place') == 'log' for i in c.get('integrity_until') or []):
            x.add('L6', cid, 'log_policy が「記録しない」なのに、integrity_until でログに写している')
        if c.get('usage') == 'identifier' and c.get('pii_category') in PII and c.get('log_policy') == '記録する':
            x.add('L6', cid, '利用者の識別子（個人情報）を値のまま記録する。ハッシュなどで仮名化して記録する（log_policy: ハッシュ化して記録）')


# ------------------------------------------------------------------ L7: on_missing against required_claims, both ways
def rule_l7(x):
    for t in x.adopted_tts():
        req = t.get('required_claims') or []
        if not req:
            continue
        here = x.claims_in(t['id'])
        for n in req:
            x.count('L7')
            rows = [c for c in here if n in full_names(c)]
            if not rows:
                x.add('L7', f"token_type {t['id']}", f'required_claims の {n} が、台帳の行（carried_in に {t["id"]}）にない')
            for c in rows:
                if c.get('on_missing') != '拒否':
                    x.add('L7', c.get('id'), f"{t['id']} の required_claims にあるのに on_missing が {c.get('on_missing')!r}（拒否にする。fail-closed）")
    for c in x.adopted_claims():
        if c.get('on_missing') != '拒否':
            continue
        for t in x.carried(c):
            if t.get('format') != 'jwt':
                continue
            aud = set(t.get('aud') or [])
            sev = None
            if aud and not aud & set(c.get('consumers') or []):
                # none of the claim's consumers is an audience of this token type. #58: a claim that the IdP defines is read
                # by the entry, which a hop delivers the token to although aud names the API behind it (new part: warn)
                if not (c.get('idp_defined') and any(h.get('token_type') == t['id'] and _service_name(h.get('to')) in (c.get('consumers') or [])
                                                     for h in x.hops)):
                    continue
                sev = WARN
            x.count('L7')
            if not full_names(c) & set(t.get('required_claims') or []):
                x.add('L7', c.get('id'), f"on_missing が拒否なのに、{t['id']} の required_claims にない（受け手の検証の設定で拒否できない）", sev)


# ------------------------------------------------------------------ L8: headers copied from claims
def rule_l8(x):
    fwd = {}
    for h in x.hops:
        for fh in h.get('forwarded_headers') or []:
            x.count('L8')
            fwd.setdefault(fh.get('claim'), []).append(fh)
            if fh.get('strip_inbound') is not True:
                x.add('L8', f"hop {h.get('id')}", f"ヘッダー {fh.get('name')} に転記するのに、入口でクライアントから来た同名のヘッダーを捨てない（strip_inbound）")
    for c in x.adopted_claims():
        for i in c.get('integrity_until') or []:
            if i.get('place') != 'http_header':
                continue
            x.count('L8')
            if not any(f.get('strip_inbound') is True for f in fwd.get(c.get('id'), [])):
                x.add('L8', c.get('id'), f"ヘッダー（{i.get('target')}）に写すのに、hops の forwarded_headers に同名のヘッダーを捨てる宣言がない")


# ------------------------------------------------------------------ L9: tenant binding
def _multitenant(x):
    lc = (x.answers.get('lite_criteria') or {}).get('multitenant')
    return any(t.get('tenant_binding') for t in x.tts) or (isinstance(lc, dict) and lc.get('answer') is True) \
        or any(str(d).startswith('system.operations.tenant') for c in x.claims for d in c.get('data_category') or [])


def rule_l9(x):
    """by: claim / tid / org_id name a tenant claim (tenant_binding.claim, or for tid / org_id the claim of that name,
    `organization` too, carried in the token type). It must be checked at every consumer, against iss (or aud), and in the
    data layer. by: iss / aud: the iss / aud claim must be checked at every consumer; the data layer must filter."""
    if not _multitenant(x):
        return
    dbs = x.db_services()
    for t in x.adopted_tts():
        if t.get('kind') not in ('access_token', 'internal_token', 'txn_token') or t.get('format') != 'jwt':
            continue
        x.count('L9')
        tid = f"token_type {t['id']}"
        tb = t.get('tenant_binding')
        if not tb:
            x.add('L9', tid, 'マルチテナントの設計なのに tenant_binding（iss・aud・tid・org_id・claim）がない')
            continue
        by = set(tb.get('by') or [])
        here = x.claims_in(t['id'])
        tenant_claims = []
        for kind in sorted(by & {'claim', 'tid', 'org_id'}):
            c = x.cid.get(tb.get('claim')) if tb.get('claim') else None
            if c is None and kind != 'claim':
                names = {'tid'} if kind == 'tid' else {'org_id', 'organization'}
                c = next((r for r in here if r.get('name') in names), None)
            if c is None:
                x.add('L9', tid, f'tenant_binding.by の {kind} に当たる台帳の行がない（tenant_binding.claim に ID を書くか、{t["id"]} に載せる）')
            elif c not in tenant_claims:
                tenant_claims.append(c)
        protocol = [c for c in here if c.get('namespace') is None and c.get('name') in by & {'iss', 'aud'}]
        for c in tenant_claims + protocol:
            services = {str(e.get('service', '')).lower() for e in c.get('enforced_at') or []}
            for s in set(c.get('consumers') or []) & set(t.get('aud') or c.get('consumers') or []):
                if s.lower() not in services:
                    x.add('L9', c.get('id'), f"テナントの束縛（{t['id']}）に使うのに、受け手 {s} の enforced_at に照合がない")
        for c in tenant_claims:
            ea = c.get('enforced_at') or []
            if not any(_against(e) & {'iss', 'aud'} for e in ea):
                x.add('L9', c.get('id'), 'テナントのクレームを iss（か aud）と突き合わせる照合がない（enforced_at の against に iss を書く）')
            if dbs and not any(str(e.get('service', '')).lower() in dbs or 'data_layer' in _against(e) for e in ea):
                x.add('L9', c.get('id'), f"データ層（{'・'.join(sorted(dbs))}）での絞り込みの照合が enforced_at にない")
        if not tenant_claims and dbs and not any('data_layer' in _against(e) or str(e.get('service', '')).lower() in dbs
                                                 for c in here for e in c.get('enforced_at') or []):
            x.add('L9', tid, f"データ層（{'・'.join(sorted(dbs))}）でテナントを絞る照合が、どのクレームの enforced_at にもない")


# ------------------------------------------------------------------ L15: refresh tokens of public clients, cnf
def rule_l15(x):
    cts = _profile_values(x, 'client_type')  # value and the per-IdP exceptions (#58)
    for t in x.adopted_tts():
        if t.get('kind') == 'refresh_token' and 'public' in cts:
            x.count('L15')
            rot = t.get('rt_rotation') or {}
            if not (rot.get('rotation') is True and rot.get('reuse_detection') == 'yes') and t.get('sender_constraint') not in ('dpop', 'mtls'):
                x.add('L15', f"token_type {t['id']}", '公開クライアントの RT に、ローテーションと再利用の検知（reuse_detection: yes）も送信者制約もない（RFC 9700 §2.2.2・§4.14.2）')
        if t.get('sender_constraint') in ('dpop', 'mtls'):
            x.count('L15')
            cnf = [c for c in x.claims_in(t['id']) if c.get('name') == 'cnf']
            if not cnf:
                x.add('L15', f"token_type {t['id']}", f"送信者制約（{t['sender_constraint']}）なのに、台帳に {t['id']} に載る cnf の行がない")
    for c in x.adopted_claims():
        if c.get('name') != 'cnf':
            continue
        x.count('L15')
        have = {str(e.get('service')) for e in c.get('enforced_at') or []}
        for s in c.get('consumers') or []:
            if s not in have:
                x.add('L15', c.get('id'), f'cnf を持つトークンの受け手 {s} の enforced_at に、DPoP・mTLS の鍵の照合がない')


# ------------------------------------------------------------------ L16: narrower downstream
# The aud / scope / lifetime part of L16 (exchange and reissue hops) has not run on scenario A (no such hop): warn until
# a worked example exercises it (RULES.md). The custom-claims part ran on H3 of scenario A.
SEV_WIDEN = WARN


def _narrowing_exceptions(h):
    """narrowing_exception: a string is the reason for a longer max_lifetime (Txn-Token only); an object may give aud (with
    aud_replacement) and max_lifetime (Txn-Token only). scope and authorization_details never widen (draft-ietf-oauth-
    transaction-tokens-11 §13.6: same or narrower), and extra custom_claims have no exception."""
    e = h.get('narrowing_exception')
    if isinstance(e, str):
        return {'max_lifetime': e}
    return e if isinstance(e, dict) else {}


def _service_name(text):
    """The service of a hop's from / to: the text before the first space or full-width bracket."""
    return re.split(r'[\s（(]', str(text or '').strip(), maxsplit=1)[0]


def _aud_replacement_problem(h, up):
    """None when the hop may replace aud (PR #44 re-check): a token-exchange hop, one concrete aud equal to the hop's
    destination service, and the upstream token addressed the requesting service."""
    aud = h.get('aud') or []
    if h.get('kind') != 'exchange':
        return 'aud_replacement は交換（kind: exchange）のホップだけ。作り直しのホップは上流の aud の部分集合にする'
    if len(aud) != 1:
        return f'aud_replacement の aud は 1 つ（いまは {len(aud)} 個）'
    a = str(aud[0])
    if '*' in a or '{' in a or a.endswith('/'):
        return f'aud_replacement の aud {a} は 1 つの具体的な宛先でない（ワイルドカード・入口全体の宛先は不可）'
    if a != _service_name(h.get('to')):
        return f"aud_replacement の aud {a} がホップの行き先（{_service_name(h.get('to'))}）と一致しない"
    if _service_name(h.get('from')) not in [str(x) for x in (up.get('aud') or [])]:
        return f"上流（{up.get('id')}）の aud に、交換を求めるサービス（{_service_name(h.get('from'))}）が無い"
    if _empty(_narrowing_exceptions(h).get('aud')):
        return 'aud_replacement には narrowing_exception.aud の理由が要る'
    return None


AUTHORITY_NAMES = {'roles', 'groups', 'entitlements', 'scope', 'scp', 'permissions'}


def _minted(h):
    """The hop mints a new token (a reissue or an exchange with an exchanger); only such a hop can add or rename anything."""
    return h.get('kind') in ('reissue', 'exchange') and not _empty(h.get('exchanger'))


def _added_claims(x, h, ups, hid):
    """added_claims (#58): organization claims that the upstream tokens do not carry and the exchanger adds when it mints
    the new token, from a system that is not a token (external_source) or derived from upstream claims (upstream_claims).
    Returns the claim IDs accepted; every entry that does not meet the conditions is an error and is not accepted."""
    entries = h.get('added_claims') or []
    if not entries:
        return set()
    if not _minted(h):
        x.add('L16', hid, 'added_claims は、新しいトークンを作るホップ（kind が reissue・exchange で、exchanger がある）だけに書ける。'
                          'そのまま渡すホップは値を足せない', ERROR)
        return set()
    ok, notes = set(), []
    up_claims = set().union(*[set(u.get('custom_claims') or []) for u in ups]) if ups else set()
    for a in entries:
        cid = a.get('claim')
        row = x.cid.get(cid) or {}
        if cid not in (h.get('custom_claims') or []):
            x.add('L16', hid, f'added_claims の {cid} が、このホップの custom_claims にない', ERROR)
            continue
        if row.get('decision') not in ADOPTED or h.get('token_type') not in (row.get('carried_in') or []):
            x.add('L16', hid, f"added_claims の {cid} が、台帳でこのホップの種別（{h.get('token_type')}）に載る行でない", ERROR)
            continue
        if a.get('source') == 'upstream_claims':
            src = a.get('from') or []
            nowhere = [f for f in src if f not in up_claims]
            if nowhere:
                x.add('L16', hid, f"added_claims の {cid} の from の {'・'.join(nowhere)} が、どの上流のホップの custom_claims にもない", ERROR)
                continue
            for u in ups:
                if (x.tt.get(u.get('token_type')) or {}).get('kind') != 'session' and not set(src) & set(u.get('custom_claims') or []):
                    x.add('L16', hid, f"added_claims の {cid}（上流のクレームから導く）の from のどれも、上流（{u.get('id')}）が運ばない。"
                                      'その経路では値の出どころが無い', SEV_WIDEN)
            notes.append(f"{cid}（上流の {'・'.join(src)} から導く）")
        else:
            if _empty(row.get('source_system')):
                x.add('L16', hid, f'added_claims の {cid} の台帳の行に source_system（値の出どころ）がない', ERROR)
                continue
            # a claim that decides access, added from outside the tokens, widens what the upstream token allowed: the
            # source must be the one the registry row names, and roles / groups / scope / permissions are always reported
            sysname, src_sys = str(a.get('system') or '').strip(), str(row.get('source_system') or '')
            if row.get('name') in AUTHORITY_NAMES:
                x.add('L16', hid, f"added_claims の {cid}（{row.get('name')}）は権限のクレーム。上流のトークンに無い権限を、トークン以外（{sysname}）から足す。"
                                  '上流のクレームから導く（source: upstream_claims）か、足す理由と出どころをレビューで確かめる', SEV_WIDEN)
            elif row.get('usage') == 'authz' and (len(sysname) < 4 or (sysname not in src_sys and src_sys not in sysname)):
                x.add('L16', hid, f"added_claims の {cid} は認可に使うクレーム（usage: authz）なのに、system（{sysname}）が台帳の行の source_system"
                                  f"（{src_sys}）と合わない。出どころを台帳と同じ名前で書く", SEV_WIDEN)
            notes.append(f"{cid}（{a.get('system')}）")
        ok.add(cid)
    if notes:
        x.add('L16', hid, f"上流のトークンに無い独自クレームを、作り直しで足す（added_claims）：{'、'.join(notes)}", INFO)
    return ok


def rule_l16(x):
    for h in x.hops:
        ups = [x.hop[u] for u in upstreams(h) if u in x.hop]
        hid = f"hop {h.get('id')}"
        if not ups:
            if h.get('added_claims') or h.get('aud_mapping'):
                x.add('L16', hid, 'added_claims・aud_mapping を書いたのに upstream が無い。比べる上流が無いので、絞り込み（L16）を確かめていない', SEV_WIDEN)
            continue
        added = _added_claims(x, h, ups, hid)
        for m in h.get('aud_mapping') or []:
            if h.get('kind') != 'reissue':
                x.add('L16', hid, 'aud_mapping は作り直し（kind: reissue）のホップだけに書ける（交換のホップは aud_replacement）', SEV_WIDEN)
                break
            if m.get('upstream') not in upstreams(h):
                x.add('L16', hid, f"aud_mapping の upstream {m.get('upstream')} が、このホップの upstream にない", SEV_WIDEN)
        for up in ups:
            _l16_against(x, h, up, hid, added)


def _aud_mapped(h, up):
    """aud values of a reissue hop that an aud_mapping entry ties to a value of this upstream hop's aud or scope (#58)."""
    if h.get('kind') != 'reissue':
        return set()
    # the mapped aud must be the hop's destination (as for aud_replacement): one upstream value cannot authorize any
    # number of audiences (PR #70 check)
    return {m.get('aud') for m in h.get('aud_mapping') or []
            if m.get('upstream') == up.get('id') and m.get('via') in ('aud', 'scope') and m.get('value') in (up.get(m['via']) or [])
            and str(m.get('aud')) == _service_name(h.get('to'))}


def _l16_against(x, h, up, hid, added):
    if True:  # (indentation kept: the body below is the pre-#58 rule for one upstream hop)
        extra = sorted(set(h.get('custom_claims') or []) - set(up.get('custom_claims') or []) - added)
        up_tt = x.tt.get(up.get('token_type'))
        if up_tt is not None and up_tt.get('kind') != 'session':
            x.count('L16')
        if extra and up_tt is not None and up_tt.get('kind') != 'session':
            x.add('L16', hid, f"独自クレーム {'・'.join(extra)} が上流（{up.get('id')}）に無い")
        kind = (x.tt.get(h.get('token_type')) or {}).get('kind')
        exchange_like = h.get('kind') in ('exchange', 'reissue') or (h.get('kind') == 'service' and h.get('token_type') != up.get('token_type'))
        txn_pass = kind == 'txn_token' and up.get('token_type') == h.get('token_type')
        if not exchange_like and not txn_pass:
            return
        if up_tt is None or up_tt.get('kind') == 'session':
            return
        x.count('L16.widen')
        exc = _narrowing_exceptions(h)
        dims = (('scope', 'scope'),) if txn_pass else (('aud', 'aud'), ('scope', 'scope'), ('authorization_details', 'authorization_details'))
        for k, label in dims:
            wide = sorted(set(h.get(k) or []) - set(up.get(k) or []))
            if k == 'aud' and wide:
                mapped = _aud_mapped(h, up)
                used = [a for a in wide if a in mapped]
                wide = [a for a in wide if a not in mapped]
                if used:
                    how = '、'.join(f"{m.get('aud')} ← {m.get('via')} の {m.get('value')}" for m in h.get('aud_mapping') or []
                                   if m.get('upstream') == up.get('id') and m.get('aud') in used)
                    x.add('L16', hid, f"aud の {'・'.join(map(str, used))} は上流（{up.get('id')}）の aud に無いが、aud_mapping で上流の値に対応づけた（{how}）。"
                                      '入口が経路ごとにその値を確かめることは、レビューで確かめる', INFO)
            if not wide:
                continue
            if k == 'aud' and h.get('aud_replacement') is True:
                problem = _aud_replacement_problem(h, up)
                if problem is None:
                    x.add('L16', hid, f"aud を上流（{up.get('id')}）の {'・'.join(map(str, up.get('aud') or []))} から、行き先の 1 つの宛先 "
                                      f"{h['aud'][0]} に替える（aud_replacement。理由：{exc['aud']}）", INFO)
                else:
                    x.add('L16', hid, problem, ERROR)
                continue
            x.add('L16', hid, f"{label} の {'・'.join(map(str, wide))} が上流（{up.get('id')}）に無い（下流ほど絞る。広げない"
                              f"{'。Txn-Token の scope は同じか狭い：draft-ietf-oauth-transaction-tokens-11 §13.6' if kind == 'txn_token' else ''}）", SEV_WIDEN)
        ml, uml = h.get('max_lifetime'), up.get('max_lifetime')
        if isinstance(ml, int) and isinstance(uml, int) and ml > uml:
            reason = exc.get('max_lifetime')
            if kind == 'txn_token' and isinstance(reason, str) and len(reason.strip()) >= 10:
                x.add('L16', hid, f"Txn-Token の寿命 {ml} 秒が上流の {uml} 秒を超える。仕様は認めている（draft-ietf-oauth-transaction-tokens-11 §6・§13.15）"
                                  f"ので、narrowing_exception の理由を記録として扱う：{reason}", INFO)
            else:
                x.add('L16', hid, f"寿命 {ml} 秒が上流（{up.get('id')}）の {uml} 秒を超える（下流ほど絞る。組織の規則、author-proposal。"
                                  '寿命の例外は Txn-Token の作り直しだけで、理由は 10 字以上）', SEV_WIDEN)


# ------------------------------------------------------------------ L17 / L25 / L27: validation settings
RFC9068_REQUIRED = ['iss', 'exp', 'aud', 'sub', 'client_id', 'iat', 'jti']  # RFC 9068 §2.2
MAX_SKEW = 300


def rule_l17(x):
    typs = {}
    for t in x.adopted_tts():
        if t.get('format') != 'jwt':
            continue
        x.count('L17')
        tid = f"token_type {t['id']}"
        for k in ('unknown_kid', 'jwks_cache_ttl'):
            if t.get(k) is None:
                x.add('L17', tid, f'{k} がない（未知の kid での取り直しの最短間隔・負のキャッシュ、JWKS のキャッシュの TTL。見るのは宣言の有無で、値が十分かは見ない）')
        algs = [str(a) for a in t.get('alg_allowlist') or []]
        if any(a.lower() == 'none' for a in algs):
            x.add('L17', tid, 'alg_allowlist に none がある')
        if any(a.startswith('HS') for a in algs) and any(i.get('jwks_uri') for i in t.get('issuers') or []):
            x.add('L17', tid, 'alg_allowlist に HMAC（HS*）と公開鍵の発行者（jwks_uri）が並ぶ。alg の取り違えを許す')
        if t.get('typ'):
            typs.setdefault(t['typ'].lower(), []).append(t)
    for typ, ts in typs.items():
        if len({t.get('kind') for t in ts}) > 1:
            _l17_same_typ(x, typ, ts)


# claims whose value differs from token to token (times, random values, hashes): a required value of such a claim cannot
# tell two kinds of token apart (re-check of PR #70)
KD_VOLATILE = {'exp', 'iat', 'nbf', 'auth_time', 'updated_at', 'jti', 'nonce', 'at_hash', 'c_hash', 's_hash', 'sid'}


def _norm_value(v):
    return ('true' if v else 'false') if isinstance(v, bool) else str(v).strip()


def _declared_values(row):
    """The values a registry row says the claim can have (allowed_values.enum, value_vocabulary.values), normalized."""
    vals = list((row.get('allowed_values') or {}).get('enum') or []) + list((row.get('value_vocabulary') or {}).get('values') or [])
    return {_norm_value(v) for v in vals}


def _kd_forms(t):
    """kind_discriminator as {claim: ('value', v) | ('absent',) | ('aud', set of the row's aud)}; entries that say neither
    are left out (returned second)."""
    forms, vague = {}, []
    for e in t.get('kind_discriminator') or []:
        c = e.get('claim')
        if 'value' in e:
            forms[c] = ('value', _norm_value(e['value']))  # 1 and "1" are the same value
        elif e.get('absent') is True:
            forms[c] = ('absent',)
        elif c == 'aud':
            forms[c] = ('aud', frozenset(map(str, t.get('aud') or [])))
        else:
            vague.append(c)
    return forms, vague


def _forms_exclusive(fa, fb):
    """The validation rules of two token types cannot both accept one token (RFC 8725 §3.12): on some claim, they require
    different values, one requires a value (or its aud) and the other requires the claim to be absent, or both check aud
    against sets that do not overlap."""
    for c in fa.keys() & fb.keys():
        p, q = fa[c], fb[c]
        kinds = {p[0], q[0]}
        if kinds == {'value'} and p[1] != q[1]:
            return True
        if 'absent' in kinds and len(kinds) == 2 and ('aud' not in kinds or (p if p[0] == 'aud' else q)[1]):
            return True
        if kinds == {'aud'} and p[1] and q[1] and not p[1] & q[1]:
            return True
    return False


def _kd_exclusive(a, b):
    return _forms_exclusive(_kd_forms(a)[0], _kd_forms(b)[0])


def _kd_grounded(x, t):
    """The kind_discriminator entries that can carry the proof, and what is wrong with the others (PR #70 check): a
    required value needs a registry row carried in the token type whose on_missing is 拒否 (the issuer sets it and the
    consumer rejects without it); `absent` must not contradict the token type (required_claims, or a registry row carried
    in it); {claim: aud} needs the aud column. Returns (forms, problems, contradictions)."""
    forms, vague = _kd_forms(t)
    problems = [f'{c} に、求める値（value）も「無いこと」（absent: true）もない' for c in vague]
    contradictions, ok = [], {}
    req = set(t.get('required_claims') or [])
    for c, form in forms.items():
        rows = [r for r in x.claims_in(t['id']) if c in full_names(r)]
        if form[0] == 'absent':
            if c in req or rows:
                contradictions.append(f"{c} を「無いこと」（absent: true）としたが、この種別の"
                                      f"{' required_claims ' if c in req else '台帳の行（' + rows[0].get('id', '') + ' の carried_in）'}にある")
                continue
        elif form[0] == 'aud':
            if not form[1]:
                problems.append('aud を書いたが、この種別の aud（宛先）の列が空')
                continue
        elif c in KD_VOLATILE:
            problems.append(f'{c} はトークンごとに変わる値（時刻・乱数・ハッシュ）。決まった value で種類を区別できない')
            continue
        elif not rows:
            problems.append(f'{c} が、台帳の行（carried_in に {t["id"]}）にない（発行者がその値を載せると言えない）')
            continue
        elif any(r.get('on_missing') != '拒否' for r in rows):
            problems.append(f'{c} の on_missing が拒否でない（区別に使う値が無いトークンを、この種類として受けてしまう）')
            continue
        elif c == 'iss':
            # the issuers the token type accepts are in the inventory: an iss value that is not among them proves nothing
            if form[1] not in {_norm_value(i.get('iss')) for i in t.get('issuers') or []}:
                problems.append(f'iss の value {form[1]} が、この種別の issuers の iss にない')
                continue
        elif any(form[1] not in _declared_values(r) for r in rows):
            # the value must be one the registry row declares (re-check of PR #70: a made-up value on any claim that has
            # a row turned the error into info)
            problems.append(f'{c} の value {form[1]} が、台帳の行（{rows[0].get("id")}）の allowed_values.enum・value_vocabulary.values にない'
                            '（発行者がその値を載せると、台帳が宣言していない）')
            continue
        ok[c] = form
    return ok, problems, contradictions


def _l17_same_typ(x, typ, ts):
    ids = '・'.join(t['id'] for t in ts)
    base = f'種類の違うトークン種別が同じ typ（{typ}）を使う。typ で種類を分け、種類ごとに検証の規則を分ける'
    without = [t['id'] for t in ts if _empty(t.get('kind_discriminator'))]
    if without:
        hint = '' if len(without) == len(ts) else f"（kind_discriminator が無い種別：{'・'.join(without)}）"
        x.add('L17', ids, base + hint)
        return
    # #58: the IdP fixes typ (Keycloak and Entra: JWT for access and ID tokens; Cognito: no typ), so the kinds are told
    # apart by payload values. The error goes away only when the declarations prove every pair of different kinds apart;
    # a kind_discriminator that does not discriminate leaves the error as it was (no downgrade of an error)
    grounded = {t['id']: _kd_grounded(x, t) for t in ts}
    for t in ts:
        for msg in grounded[t['id']][2]:
            x.add('L17', f"token_type {t['id']}", f'kind_discriminator の {msg}（矛盾）', ERROR)
    unproven = [f"{a['id']}／{b['id']}" for i, a in enumerate(ts) for b in ts[i + 1:]
                if a.get('kind') != b.get('kind') and not _forms_exclusive(grounded[a['id']][0], grounded[b['id']][0])]
    notes = [f"{t['id']}：kind_discriminator の {p}" for t in ts for p in grounded[t['id']][1]]
    if unproven:
        x.add('L17', ids, base + f"（kind_discriminator の宣言からは、次の組を排他と言えない：{'、'.join(unproven)}。同じクレームに別の value、"
                                 f"片方が absent、重ならない aud のどれかを両方の行に書く。RFC 8725 §3.12"
                                 + (f"。使えない宣言：{'；'.join(notes)}" if notes else '') + '）')
        return
    for t in ts:
        for p in grounded[t['id']][1]:
            x.add('L17', f"token_type {t['id']}", f'kind_discriminator の {p}。この要素は区別に使えない', WARN)
    x.add('L17', ids, f'種類の違うトークン種別が同じ typ（{typ}）を使うが、ペイロードの値と aud で区別する（kind_discriminator。'
                      'RFC 8725 §3.12 の「必須クレームの値を変える」「aud を変える」）。typ は IdP が決め、設計では選べない。'
                      'aud の列は自由記述なので、文字列が違っても同じ宛先を指していないかは、レビューで確かめる', INFO)


def rule_l25(x):
    for t in x.adopted_tts():
        if t.get('format') != 'jwt':
            continue
        x.count('L25')
        if not t.get('key_source'):
            x.add('L25', f"token_type {t['id']}", 'key_source がない（鍵をどこからだけ取るか。ヘッダーの jku・x5u をたどらず、jwk・x5c を信頼しない：header_key_params: reject）')


def _audience_claim_problem(x, t, ac, req):
    if str(t.get('typ', '')).lower() == 'at+jwt':
        return 'typ が at+jwt の種別は aud が REQUIRED（RFC 9068 §2.2）'
    ents = x.issuers_of(t.get('id'))
    if not ents:
        return ('この種別を出す IdP の宣言なし。catalog_answers.yaml の idp に、この種別を token_types に持つ IdP を書く'
                f'（tools/claim_lint/idp_claims.yaml の audience_claim に {ac} がある IdP だけ）')
    # every IdP that issues the token type must be one whose access token has no aud: a type that an IdP with aud also
    # issues keeps aud required (PR #70 check B1)
    bad = [e['name'] for e in ents
           if ((x.idp_claims.get(e['name']) or {}).get('audience_claim') or {}).get(t.get('kind')) != ac]
    if bad:
        return (f"この種別を出す IdP のうち {'・'.join(bad)} について、tools/claim_lint/idp_claims.yaml の audience_claim に {ac} がない"
                '（種別を出す IdP のすべての AT が aud を持たないときだけ使える）')
    if ac not in req:
        return f'required_claims に {ac} がない'
    # the token does have aud (Cognito: when the client asked for a resource binding)
    has_row = [c.get('id') for c in x.claims_in(t.get('id')) if c.get('namespace') is None and c.get('name') == 'aud']
    has_hop = [h.get('id') for h in x.hops if h.get('token_type') == t.get('id') and not _empty(h.get('aud'))]
    if has_row or has_hop:
        where = '・'.join(filter(None, [has_row and f"台帳の {'・'.join(has_row)}", has_hop and f"ホップ {'・'.join(has_hop)} の aud"]))
        return f'この種別は aud を持つと宣言している（{where}）。aud を持つ AT（Cognito ではリソースの束縛を求めた AT）は aud を必須にする'
    return None


def rule_l27(x):
    rejected = {c.get('name') for c in x.claims if c.get('decision') == '却下' and c.get('namespace') is None}
    for t in x.adopted_tts():
        if t.get('format') != 'jwt' or _empty(t.get('required_claims')):
            continue
        x.count('L27')
        tid = f"token_type {t['id']}"
        req = set(t.get('required_claims') or [])
        miss = [n for n in ('exp', 'aud', 'iss') if n not in req]
        ac = t.get('audience_claim')
        if ac and 'aud' in miss:
            # #58: an IdP whose access token has no aud (Amazon Cognito: client_id). Pinned per IdP in idp_claims.yaml
            problem = _audience_claim_problem(x, t, ac, req)
            if problem is None:
                miss.remove('aud')
                x.add('L27', tid, f'aud の代わりに {ac} で宛先を確かめる（audience_claim。この種別を出す IdP の AT は aud を持たない：'
                                  'tools/claim_lint/idp_claims.yaml の audience_claim）', INFO)
            else:
                x.add('L27', tid, f'audience_claim {ac} を aud の代わりにできない：{problem}')
        if miss:
            x.add('L27', tid, f"required_claims に {'・'.join(miss)} がない（exp を必須にする）")
        sk = t.get('max_clock_skew')
        if sk is None:
            x.add('L27', tid, 'max_clock_skew（時刻のずれの許容）がない')
        elif sk > MAX_SKEW:
            x.add('L27', tid, f'max_clock_skew {sk} 秒が上限 {MAX_SKEW} 秒を超える（数分まで。上限は筆者の提案）')
        if str(t.get('typ', '')).lower() == 'at+jwt':
            for n in RFC9068_REQUIRED:
                if n in req:
                    continue
                if n in rejected:
                    x.add('L27', tid, f'at+jwt の REQUIRED の {n}（RFC 9068 §2.2）が無いことを、台帳の却下の行で逸脱として記録している', INFO)
                else:
                    x.add('L27', tid, f'typ が at+jwt なのに、RFC 9068 §2.2 の REQUIRED の {n} が required_claims にも、逸脱の記録（台帳の却下の行）にもない')


# ------------------------------------------------------------------ L18: deprecated claims still read
def rule_l18(x):
    for c in x.claims:
        if c.get('status') not in ('deprecated', 'sunset'):
            continue
        x.count('L18')
        if not c.get('consumers'):
            continue
        so = c.get('sunset_on')
        past = bool(so) and so < x.today.isoformat()
        if c.get('status') == 'sunset' or past:
            x.add('L18', c.get('id'), f"廃止日（{so or 'sunset'}）を過ぎても読む受け手が残っている：{'・'.join(c['consumers'])}")
        else:
            x.add('L18', c.get('id'), f"廃止予定（deprecated、sunset_on {so or '未定'}）のクレームを読む受け手：{'・'.join(c['consumers'])}")


# ------------------------------------------------------------------ L21 / L22 / L23: the token inventory
def rule_l21(x):
    used = set()
    for c in x.claims:
        for t in c.get('carried_in') or []:
            used.add(t)
            if c.get('decision') in ADOPTED:
                x.count('L21')
            if t in x.tt and x.tt[t].get('decision') == '却下' and c.get('decision') in ADOPTED:
                x.add('L21', c.get('id'), f'却下したトークン種別 {t} に載せている（carried_in）')
    for h in x.hops:
        t = h.get('token_type')
        if t:
            used.add(t)
            x.count('L21')
            if t in x.tt and x.tt[t].get('decision') == '却下':
                x.add('L21', f"hop {h.get('id')}", f'却下したトークン種別 {t} がホップを通る')
    for a in x.answers.get('answers') or []:
        for t in a.get('token_types') or []:
            used.add(t)
            if a.get('answer') == '該当' and t in x.tt and x.tt[t].get('decision') == '却下':
                x.count('L21')
                x.add('L21', a.get('event'), f'該当と答えたイベントに、却下したトークン種別 {t} がある')
    for t in x.adopted_tts():
        x.count('L21')
        if t['id'] not in used:
            x.add('L21', f"token_type {t['id']}", f"目録で{t.get('decision')}の種別が、どこからも参照されていない（carried_in・hops・カタログへの回答）", WARN)


def rule_l22(x):
    have = {t.get('kind') for t in x.tts}
    for k in x.kinds:
        x.count('L22')
        if k not in have:
            x.add('L22', k, f'カタログのトークンの種類 {k}（templates/catalog/token_kinds.yaml）に、目録の行（採用か、却下＋理由）がない')


EXP_IAT = re.compile(r'exp\s*[−\-ー–]\s*iat')


def rule_l23(x):
    lts = []
    for t in x.adopted_tts():
        tid, ml = f"token_type {t['id']}", t.get('max_lifetime')
        if not isinstance(ml, int):
            continue
        x.count('L23')
        lts.append(ml)
        cap = x.caps.get(t.get('kind')) or {}
        exc = t.get('lifetime_exception')
        if cap.get('max_seconds') and ml > cap['max_seconds'] and not exc:
            x.add('L23', tid, f"max_lifetime {ml} 秒が組織の上限 {cap['max_seconds']} 秒（{cap.get('basis')}）を超えるのに、lifetime_exception（承認）がない")
        if t.get('kind') in ('refresh_token', 'session'):
            idle = t.get('idle_timeout')
            if not isinstance(idle, int):
                x.add('L23', tid, 'idle_timeout（無操作で終わる時間）がない。idle と絶対的な上限（max_lifetime）の両方を決める')
            elif idle > ml:
                x.add('L23', tid, f'idle_timeout {idle} 秒が絶対的な上限 max_lifetime {ml} 秒を超える')
            elif cap.get('idle_max_seconds') and idle > cap['idle_max_seconds'] and not exc:
                x.add('L23', tid, f"idle_timeout {idle} 秒が組織の上限 {cap['idle_max_seconds']} 秒を超えるのに、lifetime_exception がない")
        setters = set(t.get('lifetime_set_by') or []) - {'platform'}
        if setters and t.get('format') == 'jwt':
            ok = any(EXP_IAT.search(e.get('check', '')) for c in x.claims_in(t['id']) if c.get('name') == 'exp'
                     for e in c.get('enforced_at') or []) \
                or any(EXP_IAT.search(str(ch)) for h in x.hops if h.get('token_type') == t['id'] for ch in (h.get('validates') or {}).get('checks') or [])
            if not ok:
                x.add('L23', tid, f"寿命を {'・'.join(sorted(setters))} が設定できるのに、受け手が exp − iat ≤ max_lifetime を強制する宣言"
                                  '（exp の enforced_at か、ホップの validates.checks）がない')
    if len(lts) >= 3 and len(set(lts)) == 1:
        x.add('L23', 'token_types', f'採用した種別の max_lifetime がすべて {lts[0]} 秒。種類ごとに決める（1 つの数字で語らない）', WARN)


# ------------------------------------------------------------------ L31: who can write the value
EDITABLE = ('本人が編集できる値', '呼び出し側の申告')
NON_PLATFORM = {'tenant_admin', 'end_user', 'client', 'caller'}


def _pinned(x, c, seen):
    """The claim is compared with iss, the API's own configuration or the data layer (directly, or through another claim)."""
    if c.get('id') in seen:
        return False
    seen = seen | {c.get('id')}
    for e in c.get('enforced_at') or []:
        a = _against(e)
        if a & {'iss', 'api_config', 'data_layer'}:
            return True
        if 'other_claim' in a and e.get('with') in x.cid and _pinned(x, x.cid[e['with']], seen):
            return True
    return False


def rule_l31(x):
    for c in x.adopted_claims():
        if c.get('usage') not in ('authz', 'identifier'):
            continue
        x.count('L31')
        cid = c.get('id')
        if c.get('provenance') in EDITABLE:
            x.add('L31', cid, f"provenance が「{c['provenance']}」の値を usage {c['usage']} に使っている。認可には発行者が確かめた値だけを使う")
        who = set()
        for w in x.writers(c):
            who |= set(w.get('configurable_by') or []) & NON_PLATFORM
        if who and not _pinned(x, c, set()):
            x.add('L31', cid, f"書き手の設定を {'・'.join(sorted(who))} が変えられるのに、iss か API 側の設定（またはデータ層）との照合が"
                              ' enforced_at にない（against に iss・api_config・data_layer を書く。他のクレームと照合するなら other_claim と with）')


# ------------------------------------------------------------------ L37: what a missing authz claim means
def rule_l37(x):
    for c in x.adopted_claims():
        if c.get('usage') != 'authz' or c.get('on_missing') == '拒否':
            continue
        x.count('L37')
        if _empty((c.get('absent_semantics') or {}).get('absent')):
            x.add('L37', c.get('id'), f"認可に使うクレームが無いときに拒否しない（on_missing: {c.get('on_missing')}）のに、無いときの意味"
                                      '（absent_semantics.absent）がない。許可のクレームなら「何も許さない」と書く')


# ------------------------------------------------------------------ L43: Txn-Token transport
def rule_l43(x):
    for t in x.adopted_tts():
        if t.get('kind') != 'txn_token':
            continue
        x.count('L43')
        if t.get('transport') != 'txn_token_header':
            x.add('L43', f"token_type {t['id']}", f"Txn-Token を {t.get('transport')} で運ぶ。専用のヘッダー（txn_token_header）で送り、AT として受けない")


# ------------------------------------------------------------------ L62 / L63 / L64: issuance effects
def _profile_value(x, field):
    v = x.profile_doc.get(field)
    return v.get('value') if isinstance(v, dict) and 'value' in v else v


def _profile_values(x, field):
    """The value of an issuance_profile field and the values of its per-IdP exceptions (#58)."""
    v = x.profile_doc.get(field)
    out = [_profile_value(x, field)]
    if isinstance(v, dict):
        out += [e.get('value') for e in v.get('exceptions') or [] if isinstance(e, dict)]
    return out


def _when(x, conds):
    """A condition holds when the value or the value of any per-IdP exception meets it: a requirement applies as soon as
    one IdP of the design makes the choice (#58)."""
    for w in conds:
        vs = _profile_values(x, w['field'])
        if 'equals' in w and not any(v == w['equals'] for v in vs):
            return False
        if 'includes' in w and not any(w['includes'] in (v or []) for v in vs):
            return False
    return True


def _select(x, path):
    """'claims[name=cnf].carried_in' -> (rows, field). Supports claims / token_types / hops with [k=v], [k!=null], [*]."""
    m = re.match(r'^(claims|token_types|hops)\[([^\]]+)\](?:\.(.+))?$', path)
    if not m:
        return None, None
    src = {'claims': x.adopted_claims(), 'token_types': x.tts, 'hops': x.hops}[m.group(1)]
    cond, field = m.group(2), m.group(3)
    if cond == '*':
        rows = list(src)
    elif '!=' in cond:
        k, v = cond.split('!=')
        rows = [r for r in src if (r.get(k) is not None if v == 'null' else str(r.get(k)) != v)]
    else:
        k, v = cond.split('=')
        rows = [r for r in src if str(r.get(k)) == v]
    return rows, field


def _get(row, field):
    cur = row
    for p in (field or '').split('.') if field else []:
        cur = cur.get(p) if isinstance(cur, dict) else None
    return cur


def _tt_matches(x, tid, spec):
    t = x.tt.get(tid) or {}
    for alt in str(spec).split('|'):
        k, _, v = alt.partition(':')
        if k in ('kind', 'transport') and t.get(k) == v:
            return True
    return False


def _check(x, chk):
    """True / False, or None when the check cannot be decided from the declarations."""
    path, op, val = chk.get('path', ''), chk.get('op'), chk.get('value')
    if op == 'not_required':
        return True
    if path.startswith('issuance_profile.'):
        parts = path.split('.')[1:]
        v = x.profile_doc.get(parts[0])
        if len(parts) == 1 and isinstance(v, dict) and 'value' in v:
            # the effective value of every IdP must pass: value and each per-IdP exception (PR #70 check B4)
            vs = _profile_values(x, parts[0])
        else:
            for p in parts[1:]:
                v = v.get(p) if isinstance(v, dict) else None
            vs = [v]
        if op == 'present':
            return all(not _empty(v) for v in vs)
        if op == 'equals':
            return all((v in val if isinstance(val, list) else v == val) for v in vs)
        if op == 'includes':
            return all(val in (v or []) for v in vs)
        return None
    rows, field = _select(x, path)
    if rows is None:
        return None
    if op == 'present':
        return any(not _empty(_get(r, field)) for r in rows) if field else bool(rows)
    if op == 'equals':
        if not rows:
            return False
        if field is None and isinstance(val, dict):
            return any(all(r.get(k) == v for k, v in val.items()) for r in rows)
        got = [_get(r, field) for r in rows]
        if isinstance(val, dict):
            return any(isinstance(g, dict) and all(g.get(k) == v for k, v in val.items()) for g in got)
        return any(g == val for g in got)
    if op in ('includes', 'absent'):
        if op == 'absent' and val is None:
            return all(_empty(_get(r, field)) for r in rows)
        if str(val).startswith('grant:'):
            return None  # which grant issued a token is not declared per claim
        hit = any(any(_tt_matches(x, t, val) for t in (_get(r, field) or [])) for r in rows)
        return hit if op == 'includes' else not hit
    if op == 'all_consumers':
        if not rows:
            return False
        for r in rows:
            for s in r.get('consumers') or []:
                txt = ' '.join(e.get('check', '') for e in r.get('enforced_at') or [] if e.get('service') == s)
                if not all(re.search(r'(?<![A-Za-z#])' + re.escape(w) + r'(?![A-Za-z])', txt) for w in val):
                    return False
        return True
    return None


def rule_effects(x):
    declared = {e['name'] for e in x.idps}
    for field, v in x.profile_doc.items():
        exs = (v.get('exceptions') or []) if isinstance(v, dict) else []
        named = [ex.get('idp') for ex in exs]
        if declared and declared <= set(named):
            x.add('L62', f'issuance_profile.{field}', f"exceptions が設計書の IdP のすべて（{'・'.join(sorted(declared))}）にある。value を使う IdP が無いので、"
                                                       '例外ではなく value を変える（value に書いた値で要件を満たしたことにしない）', ERROR)
        for dup in sorted({n for n in named if named.count(n) > 1}, key=str):
            x.add('L62', f'issuance_profile.{field}', f'exceptions に {dup} が 2 回ある', WARN)
        for ex in exs:
            x.count('L62')
            where = f'issuance_profile.{field}'
            if ex.get('idp') not in declared:
                x.add('L62', where, f"exceptions の idp {ex.get('idp')} が catalog_answers.yaml の idp にない", WARN)
            if ex.get('value') == v.get('value'):
                x.add('L62', where, f"exceptions の {ex.get('idp')} の値が value と同じ（例外でない）", WARN)
    for e in x.effects:
        if not _when(x, e.get('when') or []):
            continue
        rule = (e.get('lint') or ['L62'])[0]
        if rule not in ('L62', 'L63', 'L64'):
            rule = 'L62'  # the L15-only rows (RT rotation) are requirements derived from the profile too
        for r in e.get('requires') or []:
            x.count(rule)
            ok = _check(x, r.get('check') or {})
            if ok is False:
                x.add(rule, r.get('id'), f"発行方式の選択（{e['id']}）から要るもの：{r.get('text')}（templates/registry/issuance_effects.yaml）")
            elif ok is None:
                x.add(rule, r.get('id'), f"宣言から確かめられない（{r.get('check')}）。レビューで確かめる：{r.get('text')}", INFO)


# ------------------------------------------------------------------ L65 / L66 / L67: JWS and JWE
def _parties(names):
    """Party model of visible_to, confidential_from and jwe.decryptors: a role (browser, gateway, ...) or hop:<name>, one
    named intermediary on the path. A hop:<name> is also a gateway, so confidential_from: [gateway] covers every
    hop:<name>, and confidential_from: [hop:nginx] is met by visible_to: [gateway] (which may be that hop)."""
    out = set(names)
    if any(str(n).startswith('hop:') for n in names):
        out.add('gateway')
    return out


def rule_l65(x):
    for c in x.adopted_claims():
        cf = set(c.get('confidential_from') or [])
        if not cf:
            continue
        for t in x.carried(c):
            x.count('L65')
            vis = set(t.get('visible_to') or [])
            if t.get('log_policy') == '記録する':
                vis.add('logs')
            leak = _parties(cf) & _parties(vis)
            jwe = t.get('jwe') or {}
            if jwe.get('used') is True:
                leak &= _parties(set(jwe.get('decryptors') or []))
            leak = {p for p in leak if p in cf or (p == 'gateway' and any(str(q).startswith('hop:') for q in cf))}
            if leak:
                x.add('L65', c.get('id'), f"confidential_from の {'・'.join(sorted(leak))} が、{t['id']} を読める（visible_to"
                                          f"{'・JWE の decryptors' if jwe.get('used') else ''}）")


def rule_l66(x):
    for t in x.adopted_tts():
        jwe = t.get('jwe') or {}
        if jwe.get('used') is not True:
            continue
        x.count('L66')
        tid = f"token_type {t['id']}"
        if jwe.get('nesting') != 'sign_then_encrypt':
            x.add('L66', tid, 'JWE のネストが「署名してから暗号化」でない（RFC 7519 §11.2）')
        if _empty(t.get('alg_allowlist')) or _empty(t.get('issuers')):
            x.add('L66', tid, '内側の JWS を検証する設定（alg_allowlist・issuers）がない。復号しただけで受け入れない')
        extra = set(jwe.get('decryptors') or []) - set(t.get('visible_to') or [])
        if extra:
            x.add('L66', tid, f"復号できる相手 {'・'.join(sorted(extra))} が visible_to にない（読める相手の宣言と食い違う）")


WEAK_BOUNDARY = re.compile(r'^\s*(なし|無し|ない|none|n/?a|-|—|ー|不明|未定|tbd|todo)\s*[。.]?\s*$', re.I)
HEADERISH = re.compile(r'header|ヘッダー|ヘッダ', re.I)


def rule_l67(x):
    """Copies out of the signed token: a copy to an HTTP header (place http_header, or place other whose target names a
    header) used for authz / identifier needs the header to be writable only by the entry; every copy needs a real trust
    boundary (not "なし")."""
    fwd = {fh.get('claim'): fh for h in x.hops for fh in h.get('forwarded_headers') or []}
    for c in x.adopted_claims():
        for i in c.get('integrity_until') or []:
            if WEAK_BOUNDARY.match(str(i.get('trust_boundary', ''))):
                x.add('L67', c.get('id'), f"写した先（{i.get('target')}）の信頼境界が「{i.get('trust_boundary')}」。誰が書けるかを書く")
            header = i.get('place') == 'http_header' or (i.get('place') == 'other' and HEADERISH.search(str(i.get('target', ''))))
            if not header or c.get('usage') not in ('authz', 'identifier'):
                continue
            x.count('L67')
            fh = fwd.get(c.get('id'))
            if not fh or fh.get('strip_inbound') is not True or _empty(fh.get('written_only_by')):
                x.add('L67', c.get('id'), f"署名の保護が外れるヘッダー（{i.get('target')}）の値を {c['usage']} に使うのに、そのヘッダーを入口だけが書ける"
                                          '（forwarded_headers の strip_inbound・written_only_by）と宣言していない')


# ------------------------------------------------------------------ L68-L71: what not to carry (warn only)
DEVICE_NAMES = re.compile(r'^(ip|ip_?addr(ess)?|client_ip|remote_addr|device_?id|user_agent|mac(_addr(ess)?)?|imei|idfa)$', re.I)
NAME_CATEGORY = [
    (re.compile(r'pass(word|wd)|secret|api_?key|private_?key|credential', re.I), 'user.authorization.credentials'),
    (re.compile(r'e_?mail', re.I), 'user.contact.email'),
    (re.compile(r'phone|msisdn', re.I), 'user.contact.phone_number'),
    (re.compile(r'birth|dob', re.I), 'user.demographic.date_of_birth'),
]
VALUE_PATTERNS = [
    ('メールアドレス', re.compile(r'[\w.+-]+@([\w-]+\.)+[A-Za-z]{2,}')),
    ('JWT', re.compile(r'eyJ[\w-]{5,}\.eyJ[\w-]{5,}\.[\w-]*')),
    ('電話番号', re.compile(r'(?<![\w.])\+\d{1,3}[ -]?\d{1,4}[ -]?\d{3,4}[ -]?\d{3,4}(?!\d)')),
    ('秘密らしい文字列', re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|(sk|rk)_(live|test)_[0-9A-Za-z]{10,}|gh[pousr]_[0-9A-Za-z]{30,}')),
]
SAFE_DOMAINS = re.compile(r'@([\w-]+\.)*(example\.(com|org|net)|[\w-]+\.(example|test|invalid|localhost))$', re.I)


def rule_l68_71(x):
    for c in x.adopted_claims():
        if not c.get('carried_in'):
            continue
        cid, name = c.get('id'), c.get('name') or ''
        cats = [str(d) for d in c.get('data_category') or []]
        x.count('L68')
        if DEVICE_NAMES.match(name) or any(d.startswith('user.device') for d in cats):
            x.add('L68', cid, '接続元の詳細（IP・端末の識別子）をトークンに載せている。受け手が要るなら要求そのものから得る（slide:p09-do-not-carry）')
        if c.get('shape') == 'array' and c.get('usage') == 'authz':
            x.count('L69')
            if re.search(r'perm|acl|endpoint', name, re.I) or re.search(r'エンドポイント|API ごと|操作ごと', c.get('description') or '') \
                    or (c.get('max_items') or 0) > 50:
                x.add('L69', cid, '細かい権限の一覧（エンドポイント・操作ごとの許可）を配列のクレームで載せている。粗いロールか scope に留め、細かい判断は PDP に問い合わせる')
        for rx, want in NAME_CATEGORY:
            if rx.search(name):
                x.count('L70')
                if not cats:
                    x.add('L70', cid, f'名前から {want} と推測したが、data_category がない')
                elif not any(d == want or d.startswith(want + '.') for d in cats):
                    x.add('L70', cid, f"名前から {want} と推測したが、data_category は {'・'.join(cats)}（食い違いの候補。推測は名前だけによる）")
    for fname in ('claims', 'token_types', 'hops'):
        p = os.path.join(x.design_dir, fname + '.yaml')
        if not os.path.isfile(p):
            continue
        x.count('L71')
        with open(p, encoding='utf-8') as f:
            for lineno, line in enumerate(f, 1):
                for label, rx in VALUE_PATTERNS:
                    for m in rx.finditer(line):
                        if label == 'メールアドレス' and SAFE_DOMAINS.search(m.group(0)):
                            continue
                        x.add('L71', f'{fname}.yaml:{lineno}', f'台帳の値に{label}らしい文字列がある（{m.group(0)[:24]}…）。例の値は example.com などの予約の名前で書く')


# ------------------------------------------------------------------ L72: the 25 questions before adding a shared claim
UNANSWERED = re.compile(r'^\s*(|-|—|ー|未定|未回答|tbd|todo|xxx|\?+|？+)\s*$', re.I)


def claim_requests(design_dir):
    """{claim id: {question number: answer}} from claim_request_*.md (the target line names the registry row in backquotes)."""
    out = {}
    for p in sorted(glob.glob(os.path.join(design_dir, 'claim_request_*.md'))):
        with open(p, encoding='utf-8') as f:
            text = f.read()
        ids = re.findall(r'^- 対象：.*?`(C-[a-z0-9-]+)`', text, re.M)
        rows = {}
        for m in re.finditer(r'^\|\s*(\d{1,2})\s*\|([^|]*)\|([^|]*)\|', text, re.M):
            rows[int(m.group(1))] = m.group(3).strip()
        for i in ids:
            out[i] = {'file': os.path.basename(p), 'rows': rows}
    return out


def rule_l72(x):
    reqs = claim_requests(x.design_dir)
    for c in x.claims:
        if c.get('namespace') is None or c.get('decision') != '採用' or c.get('status') not in ('proposed', 'active', 'deprecated'):
            continue
        x.count('L72')
        r = reqs.get(c.get('id'))
        if not r:
            x.add('L72', c.get('id'), '共有クレーム（組織の名前空間、status が proposed 以上）に、追加前の 25 問の回答（claim_request_*.md）がない'
                                      '（slide:p11-pre-add-questions-1 の「答えられない問いが残るなら共有クレームにしない」）')
            continue
        missing = [n for n in range(1, 26) if UNANSWERED.match(r['rows'].get(n, ''))]
        if missing:
            x.add('L72', c.get('id'), f"{r['file']} の 25 問のうち、問 {'・'.join(map(str, missing))} が空欄か未定")


# ------------------------------------------------------------------ L73: Lite criteria (A17 of gate1.md 5.)
LITE_CRITERIA = ('crosses_boundary', 'multitenant', 'delegation_or_exchange', 'new_issuer', 'regulated')


def rule_l73(x):
    if x.profile != 'lite':
        return
    lc = x.answers.get('lite_criteria')
    x.count('L73')
    if not isinstance(lc, dict):
        x.add('L73', 'lite_criteria', f"--profile lite なのに、Lite の判定の 5 問（{'・'.join(LITE_CRITERIA)}）の回答（catalog_answers.yaml の lite_criteria）がない")
        return
    for k in LITE_CRITERIA:
        a = lc.get(k)
        if not isinstance(a, dict) or not isinstance(a.get('answer'), bool):
            x.add('L73', 'lite_criteria', f'{k} に Yes／No（answer: true／false）の回答がない')
        elif a['answer']:
            x.add('L73', 'lite_criteria', f"{k} が Yes なので #4 の定義では Full。Lite で書いている（{a.get('reason', '')}）")


# ------------------------------------------------------------------ L74: IdP claims a hop checks without a registry row (#58)
HEADER_PARAMS = {'typ', 'alg', 'kid'}  # also header parameter names: a check that names them usually means the header
# pinned names that are also everyday words of a validation text ("idp ごとの JWKS", "ver が 2.0", "username は使わない"):
# matching them gave false positives in the check of PR #70, so L74 does not look for them (a limit, RULES.md)
L74_GENERIC = {'idp', 'ver', 'version', 'username'}


def rule_l74(x):
    """A hop's validates.checks names a claim that the IdP of the hop's token type defines (idp_claims.yaml), but the
    registry has no row for it in that token type: on_missing, identifier_properties and required_claims are then not
    declared for a value the entry relies on (pilot #9, findings B-R1 F01 and B-R2 R2-03). Free text is matched by name,
    so a check that does not spell the claim name is not seen."""
    for h in x.hops:
        t = h.get('token_type')
        checks = (h.get('validates') or {}).get('checks') or []
        if not t or not checks:
            continue
        text = ' '.join(map(str, checks))
        have = {c.get('name') for c in x.claims_in(t) if c.get('namespace') is None}
        for ent in x.issuers_of(t):
            names = set((x.idp_claims.get(ent['name']) or {}).get('claims') or []) - HEADER_PARAMS - L74_GENERIC
            if not names:
                continue
            x.count('L74')
            for n in sorted(names):
                if n not in have and re.search(r'(?<![A-Za-z0-9_:.])' + re.escape(n) + r'(?![A-Za-z0-9_:])', text):
                    x.add('L74', f"hop {h.get('id')}", f"受け手の検証（validates.checks）が IdP {ent['name']} のクレーム {n} を使うのに、台帳に {t} に載る "
                                                       f"{n} の行がない。行を足し（idp_defined: {{idp: {ent['name']}}}）、欠落時の扱い（on_missing）と、"
                                                       '識別子なら identifier_properties を書く')


RULES = [rule_l1a, rule_l1b, rule_l2, rule_l3, rule_l4, rule_l5, rule_l6, rule_l7, rule_l8, rule_l9, rule_l15, rule_l16,
         rule_l17, rule_l18, rule_l21, rule_l22, rule_l23, rule_l25, rule_l27, rule_l31, rule_l37, rule_l43, rule_effects,
         rule_l65, rule_l66, rule_l67, rule_l68_71, rule_l72, rule_l73, rule_l74]


def run(docs, profile, design_dir, root, catalog_dir, today=None, caps_path=None):
    x = Ctx(docs, profile, design_dir, root, catalog_dir, today, caps_path)
    for r in RULES:
        r(x)
    return x.findings, x.checked
