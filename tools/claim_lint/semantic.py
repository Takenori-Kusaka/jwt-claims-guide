# -*- coding: utf-8 -*-
"""claim_lint semantic rules (#6): L1a, L1b, L2-L9, L15-L18, L21-L23, L25, L27, L31, L37, L43, L62-L73.

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
        self.reserved = _load(os.path.join(HERE, 'idp_reserved.yaml')).get('idps') or {}
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

    def idp(self):
        idp = self.answers.get('idp')
        return str(idp.get('name') if isinstance(idp, dict) else idp or '').lower()

    def db_services(self):
        return {str(h.get('to', '')).lower() for h in self.hops if h.get('kind') in ('db_connection', 'broker_connection')}

    def writers(self, c):
        return list(c.get('authoritative_writer') or []) + list(c.get('modifiers') or [])


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


def _draft_defined(c):
    """registered_ref names a section of a versioned IETF draft that spec_version also lists (draft-...-NN)."""
    ref = c.get('registered_ref') or {}
    m = re.match(r'^(draft-[a-z0-9-]+-\d{2})\b', str(ref.get('id') or ''))
    return bool(m) and ref.get('kind') == 'spec' and m.group(1) in (c.get('spec_version') or [])


def rule_l1b(x):
    declared = {n.get('namespace') for n in x.claims_doc.get('namespaces') or []}
    for c in x.adopted_claims():
        cid, ns = c.get('id'), c.get('namespace')
        x.count('L1b')
        if ns is None and c.get('name') not in x.iana:
            if c.get('decision') == '既定どおり' and not c.get('consumers'):
                x.add('L1b', cid, f"IdP が既定で出す私的名 {c.get('name')}（名前空間なし・未登録）。名前を決めたのは IdP で、受け手は読まない"
                                  '（consumers が空）ので error にしない。読む受け手を足すなら組織の名前空間に写す', INFO)
            elif _draft_defined(c):
                # a name that a versioned draft itself defines (Txn-Token req_wl, tctx; #4 scenario B): the name belongs to
                # the draft, so it cannot move into the organization's namespace. Still unregistered: warn (L14 asks for
                # spec_version and revisit_trigger)
                x.add('L1b', cid, f"未登録の名前 {c.get('name')} は草案（{c['registered_ref'].get('id')}）が定める名前。登録の前なので、"
                                  '草案の版（spec_version）と、登録・改名されたときの見直しの条件を確かめる', WARN)
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
        groups.setdefault((c.get('namespace'), c.get('name')), []).append(c)
    for (ns, name), cs in groups.items():
        if len(cs) > 1 and len({(c.get('type'), (c.get('description') or '').strip()) for c in cs}) > 1:
            x.add('L1b', '・'.join(c.get('id') for c in cs),
                  f"同じ名前 {(ns or '') + name} の行が {len(cs)} 行あり、型か意味（description）が違う。発行者ごとに意味が違うなら別の名前にする")


# ------------------------------------------------------------------ L2: IdP-reserved claims
def rule_l2(x):
    idp = x.idp()
    block = x.reserved.get(idp)
    if not block:
        if idp:
            x.add('L2', 'idp', f'IdP {idp} の、書き換えを許さないクレームの一覧が tools/claim_lint/idp_reserved.yaml にない。'
                               'L2 は確かめていない（IdP モジュール #4 で手で確かめる）', INFO)
        return
    imm = set(block.get('immutable') or [])
    pre = tuple(block.get('prefixes') or [])
    exc = set(block.get('prefix_exceptions') or [])
    sup = tuple(block.get('suppress_only_prefixes') or [])
    src = (block.get('source') or {}).get('url', '')
    for c in x.adopted_claims():
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
            if aud and not aud & set(c.get('consumers') or []):
                continue  # none of the claim's consumers receives this token type
            x.count('L7')
            if not full_names(c) & set(t.get('required_claims') or []):
                x.add('L7', c.get('id'), f"on_missing が拒否なのに、{t['id']} の required_claims にない（受け手の検証の設定で拒否できない）")


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
    ct = (x.profile_doc.get('client_type') or {}).get('value')
    for t in x.adopted_tts():
        if t.get('kind') == 'refresh_token' and ct == 'public':
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


def rule_l16(x):
    for h in x.hops:
        up = x.hop.get(h.get('upstream'))
        if not up:
            continue
        hid = f"hop {h.get('id')}"
        extra = sorted(set(h.get('custom_claims') or []) - set(up.get('custom_claims') or []))
        up_tt = x.tt.get(up.get('token_type'))
        if up_tt is not None and up_tt.get('kind') != 'session':
            x.count('L16')
        if extra and up_tt is not None and up_tt.get('kind') != 'session':
            x.add('L16', hid, f"独自クレーム {'・'.join(extra)} が上流（{up.get('id')}）に無い")
        if h.get('kind') not in ('exchange', 'reissue') and not (h.get('kind') == 'service' and h.get('token_type') != up.get('token_type')):
            continue
        if up_tt is None or up_tt.get('kind') == 'session':
            continue
        x.count('L16.widen')
        for k, label in (('aud', 'aud'), ('scope', 'scope'), ('authorization_details', 'authorization_details')):
            wide = sorted(set(h.get(k) or []) - set(up.get(k) or []))
            if wide:
                x.add('L16', hid, f"{label} の {'・'.join(map(str, wide))} が上流（{up.get('id')}）に無い（下流ほど絞る。広げない）", SEV_WIDEN)
        ml, uml = h.get('max_lifetime'), up.get('max_lifetime')
        if isinstance(ml, int) and isinstance(uml, int) and ml > uml:
            kind = (x.tt.get(h.get('token_type')) or {}).get('kind')
            if kind == 'txn_token' and not _empty(h.get('narrowing_exception')):
                x.add('L16', hid, f"Txn-Token の寿命 {ml} 秒が上流の {uml} 秒を超える。仕様は認めている（draft-ietf-oauth-transaction-tokens-11 §6）"
                                  f"ので、narrowing_exception の理由を記録として扱う", INFO)
            else:
                x.add('L16', hid, f"寿命 {ml} 秒が上流（{up.get('id')}）の {uml} 秒を超える（下流ほど絞る。組織の規則、author-proposal）", SEV_WIDEN)


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
            x.add('L17', '・'.join(t['id'] for t in ts), f'種類の違うトークン種別が同じ typ（{typ}）を使う。typ で種類を分け、種類ごとに検証の規則を分ける')


def rule_l25(x):
    for t in x.adopted_tts():
        if t.get('format') != 'jwt':
            continue
        x.count('L25')
        if not t.get('key_source'):
            x.add('L25', f"token_type {t['id']}", 'key_source がない（鍵をどこからだけ取るか。ヘッダーの jku・x5u をたどらず、jwk・x5c を信頼しない：header_key_params: reject）')


def rule_l27(x):
    rejected = {c.get('name') for c in x.claims if c.get('decision') == '却下' and c.get('namespace') is None}
    for t in x.adopted_tts():
        if t.get('format') != 'jwt' or _empty(t.get('required_claims')):
            continue
        x.count('L27')
        tid = f"token_type {t['id']}"
        req = set(t.get('required_claims') or [])
        miss = [n for n in ('exp', 'aud', 'iss') if n not in req]
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


def _when(x, conds):
    for w in conds:
        v = _profile_value(x, w['field'])
        if 'equals' in w and v != w['equals']:
            return False
        if 'includes' in w and w['includes'] not in (v or []):
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
        v = v.get('value') if isinstance(v, dict) and 'value' in v and len(parts) == 1 else v
        for p in parts[1:]:
            v = v.get(p) if isinstance(v, dict) else None
        if op == 'present':
            return not _empty(v)
        if op == 'equals':
            return v in val if isinstance(val, list) else v == val
        if op == 'includes':
            return val in (v or [])
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


RULES = [rule_l1a, rule_l1b, rule_l2, rule_l3, rule_l4, rule_l5, rule_l6, rule_l7, rule_l8, rule_l9, rule_l15, rule_l16,
         rule_l17, rule_l18, rule_l21, rule_l22, rule_l23, rule_l25, rule_l27, rule_l31, rule_l37, rule_l43, rule_effects,
         rule_l65, rule_l66, rule_l67, rule_l68_71, rule_l72, rule_l73]


def run(docs, profile, design_dir, root, catalog_dir, today=None, caps_path=None):
    x = Ctx(docs, profile, design_dir, root, catalog_dir, today, caps_path)
    for r in RULES:
        r(x)
    return x.findings, x.checked
