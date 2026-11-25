# -*- coding: utf-8 -*-
"""claim_lint render (#19): generate the design-document tables, a JSON bundle for the viewer (#36) and the payload
JSON Schemas from a design's registry. See tools/claim_lint/RENDER.md.

  python tools/claim_lint render DESIGN_DIR [--format md|json] [--section ID ...] [--out FILE]
  python tools/claim_lint render DESIGN_DIR --write     # rewrite the marked regions of design.md and schemas/*.json
  python tools/claim_lint render DESIGN_DIR --check     # exit 1 when they differ from what the registry generates
  python tools/claim_lint render DESIGN_DIR --validate TOKEN --token-type AT [--schema-kind issuer|consumer]

Every table is built once as structured rows (section -> tables -> columns + rows); the Markdown and the JSON bundle
are two views of the same rows, so the viewer (#36) and design.md cannot disagree.
"""
import argparse
import base64
import difflib
import hashlib
import json
import os
import re
import sys

from . import core

ROOT = core.ROOT
REGISTRY = os.path.join(ROOT, 'templates', 'registry')
CATALOG = os.path.join(ROOT, 'templates', 'catalog')
BUNDLE_FORMAT = 'claim-lint-render/1'
DOC_NAME = 'design.md'
SCHEMA_DIR = 'schemas'
CARRIED_DECISIONS = ('採用', '既定どおり')
NONE = '—'
REPO_URL = 'https://github.com/Takenori-Kusaka/jwt-claims-guide'  # the $id base of templates/registry/*.schema.json
TEMPLATE_VERSION_RE = re.compile(r'^#\s*template_version:\s*(\d+\.\d+\.\d+)')

# ------------------------------------------------------------------ labels (display only; the values stay as written)
STORED_AT = {'browser': 'ブラウザ', 'bff_server': 'BFF のサーバー', 'idp': 'IdP', 'rp_server': 'RP のサーバー',
             'service_memory': 'サービスのメモリ', 'none': 'なし'}
TRANSPORT = {'authorization_bearer': 'Authorization: Bearer', 'authorization_dpop': 'Authorization: DPoP',
             'cookie': 'Cookie', 'form_post_body': 'フォームの本文', 'token_response_body': 'トークンの応答',
             'back_channel_post': 'バックチャネルの POST', 'redirect_query': 'リダイレクトの query',
             'txn_token_header': 'Txn-Token のヘッダー', 'introspection_response': 'イントロスペクションの応答'}
PROFILE_FIELDS = [('client_type', 'クライアントの種類'), ('client_auth', 'クライアント認証'), ('grants', 'grant'),
                  ('sender_constraint', '送信者制約'), ('tls_termination', 'TLS の終端'),
                  ('forwarded_cert_header', '証明書を下流へ渡すヘッダー'), ('at_format', 'AT の形式'),
                  ('rt_strategy', 'RT の方式'), ('request_protection', '要求の保護'),
                  ('conformance_profile', '適合のプロファイル')]
PROFILE_VALUES = {'public': '公開', 'confidential': '機密', 'fapi': 'FAPI の対象', 'none': 'なし',
                  'authorization_code_pkce': '認可コード＋PKCE', 'refresh_token': 'リフレッシュ',
                  'client_credentials': 'client credentials', 'token_exchange': 'トークン交換', 'dpop': 'DPoP',
                  'mtls': 'mTLS', 'jwt': 'JWT', 'opaque_introspection': '不透明＋イントロスペクション',
                  'phantom': 'phantom token', 'rotation': 'ローテーション',
                  'rotation_reuse_detection': 'ローテーション＋再利用の検知', 'sender_constrained': '送信者制約'}
REVOCATION = {'exp_only': 'exp まで残る', 'introspection': 'イントロスペクション', 'status_list': '状態リスト',
              'ssf_caep': 'SSF・CAEP', 'back_channel_logout': 'Back-Channel Logout',
              'front_channel_logout': 'Front-Channel Logout', 'rp_initiated_logout': 'RP-Initiated Logout',
              'revocation_endpoint': '失効の端点', 'session_delete': 'セッションの削除',
              'refresh_failure': 'リフレッシュの失敗', 'db_lookup': 'DB の確認', 'one_time_use': '1 回の使用',
              'rotation': 'ローテーション'}
STATUS = {'satisfied': '満たす', 'unsatisfied': '満たさない', 'unknown': '判定できない'}


# ------------------------------------------------------------------ loading
def _load(path, default=None):
    return core.load_yaml(path) if os.path.isfile(path) else default


def load_design(design_dir):
    d = {k: _load(os.path.join(design_dir, k + '.yaml'), {}) or {}
         for k in ('claims', 'token_types', 'hops', 'catalog_answers')}
    d['questions'] = _load(os.path.join(REGISTRY, 'questions.yaml'), {}) or {}
    d['effects'] = (_load(os.path.join(REGISTRY, 'issuance_effects.yaml'), {}) or {}).get('effects') or []
    d['kinds'] = {k['id']: k for k in (_load(os.path.join(CATALOG, 'token_kinds.yaml'), {}) or {}).get('kinds') or []}
    events = []
    for name in ('issue_events', 'use_events'):
        events += [dict(e, _file=name) for e in (_load(os.path.join(CATALOG, name + '.yaml'), {}) or {}).get('events') or []]
    d['events'] = events
    # the $id of a payload schema names the design by its directory name, so that a copy of the directory generates
    # the same schema files (the files are compared by --check)
    d['_design'] = os.path.basename(os.path.abspath(design_dir).rstrip('/\\'))
    d['_template_version'] = None
    p = os.path.join(design_dir, 'claims.yaml')
    if os.path.isfile(p):
        with open(p, encoding='utf-8') as f:
            m = TEMPLATE_VERSION_RE.match(f.readline())
        d['_template_version'] = m.group(1) if m else None
    return d


def _claims(d):
    return d['claims'].get('claims') or []


def _tts(d):
    return d['token_types'].get('token_types') or []


def _carried(c):
    return c.get('decision') in CARRIED_DECISIONS


def _full_name(c):
    ns = c.get('namespace')
    return f"{ns}.{c.get('name')}" if ns else c.get('name')


def _secs(v):
    return None if v is None else f'{v} 秒'


# ------------------------------------------------------------------ sections (structured rows)
def _table(tid, columns, rows, title=None):
    return {'id': tid, 'title': title, 'columns': [{'key': k, 'label': l, 'fmt': f} for k, l, f in columns], 'rows': rows}


def sec_decision_rows(d):
    claims = _claims(d)
    n = {k: sum(1 for c in claims if c.get('decision') == k) for k in ('採用', '既定どおり', '却下')}
    rows = []
    for c in claims:
        decision = c.get('decision')
        if c.get('rejection_kind'):
            decision += f"（{c['rejection_kind']}）"
        rows.append({'id': c.get('id'), 'candidate': _full_name(c), 'decision': decision, 'rationale': c.get('rationale'),
                     'assumption': c.get('assumption'), 'refs': c.get('refs') or [], 'evidence': c.get('evidence') or [],
                     'alt': c.get('alt') or [], 'revisit_trigger': c.get('revisit_trigger')})
    cols = [('id', 'ID', 'code'), ('candidate', '候補', 'code'), ('decision', '採否', 'text'), ('alt', '代わりの行', 'codes'),
            ('rationale', '理由', 'text'),
            ('assumption', '前提', 'text'), ('refs', '根拠 ID', 'refs'), ('evidence', '裏付け', 'list'),
            ('revisit_trigger', '見直しの条件', 'text')]
    return {'id': 'decision-rows', 'title': '判断の行',
            'notes': [f"`claims.yaml` の {len(claims)} 行（採用 {n['採用']}・既定どおり {n['既定どおり']}・却下 {n['却下']}）。"
                      '根拠 ID は `refs`、裏付けは `evidence`（ケーススタディの実測など）。'],
            'tables': [_table('decision-rows', cols, rows)]}


def sec_data_sources(d):
    rows = []
    for c in _claims(d):
        if not _carried(c):
            continue
        writers = [f"{w.get('stage')} {w.get('writer')}" + (f"（設定できる主体：{'・'.join(w['configurable_by'])}）"
                                                          if w.get('configurable_by') else '')
                   for w in c.get('authoritative_writer') or []]
        rows.append({'id': c.get('id'), 'claim': _full_name(c), 'source_system': c.get('source_system'), 'writers': writers,
                     'issue_events': c.get('issue_events') or [], 'recompute_trigger': c.get('recompute_trigger') or [],
                     'volatility': c.get('volatility'), 'propagation_delay': c.get('propagation_delay')})
    cols = [('id', 'ID', 'code'), ('claim', 'クレーム', 'code'), ('source_system', 'データ源', 'text'),
            ('writers', '書き手（段階）', 'list'), ('issue_events', '発行の契機', 'codes'),
            ('recompute_trigger', '再計算', 'codes'), ('volatility', '反映までに許す秒数', 'seconds'),
            ('propagation_delay', '反映の遅れ', 'seconds')]
    return {'id': 'data-sources', 'title': 'データ源', 'notes': ['載せる行（採用・既定どおり）の `source_system`・`authoritative_writer`・発行の契機。'],
            'tables': [_table('data-sources', cols, rows)]}


def _kind_name(d, kind):
    k = d['kinds'].get(kind) or {}
    return k.get('name') or kind


def _lifetime(t):
    if t.get('max_lifetime') is None:
        return None
    if t.get('idle_timeout') is not None:
        return f"idle {t['idle_timeout']} 秒、最大 {t['max_lifetime']} 秒"
    return f"{t['max_lifetime']} 秒" + (f"（時計のずれ {t['max_clock_skew']} 秒）" if t.get('max_clock_skew') is not None else '')


def _format(t):
    if t.get('format') != 'jwt':
        return t.get('format')
    extra = [x for x in (t.get('typ'), '・'.join(t.get('alg_allowlist') or [])) if x]
    return 'jwt' + (f"（{'、'.join(extra)}）" if extra else '')


def sec_token_inventory(d):
    rows = []
    for t in _tts(d):
        adopted = t.get('decision') != '却下'
        jwe = t.get('jwe')
        rows.append({'id': t.get('id'), 'kind': t.get('kind'), 'kind_name': _kind_name(d, t.get('kind')),
                     'decision': t.get('decision'),
                     'issuer_to': f"{t.get('issuer')} → {'・'.join(map(str, t.get('aud') or [])) or NONE}"
                     if adopted and t.get('issuer') else None,
                     'holder': t.get('holder') if adopted else None,
                     'format': _format(t), 'lifetime': _lifetime(t) if adopted else None,
                     'stored_at': STORED_AT.get(t.get('stored_at'), t.get('stored_at')) if adopted else None,
                     'transport': TRANSPORT.get(t.get('transport'), t.get('transport')) if adopted else None,
                     'visible_to': t.get('visible_to') or [],
                     'jwe': None if not isinstance(jwe, dict) else ('あり' if jwe.get('used') else 'なし'),
                     'rationale': t.get('rationale')})
    cols = [('id', 'ID', 'code'), ('kind_name', '種類', 'text'), ('decision', '採否', 'text'),
            ('issuer_to', '発行 → 宛先（aud）', 'text'), ('holder', '持ち手', 'text'), ('format', '形式', 'text'), ('lifetime', '寿命', 'text'),
            ('stored_at', '保存場所', 'text'), ('transport', '運び方', 'text'), ('visible_to', '読める相手', 'codes'),
            ('jwe', 'JWE', 'text'), ('rationale', '理由', 'text')]
    n = sum(1 for t in _tts(d) if t.get('decision') == '却下')
    return {'id': 'token-inventory', 'title': 'トークン目録',
            'notes': [f"`token_types.yaml` の {len(_tts(d))} 行（却下 {n}）。種類の名前は `templates/catalog/token_kinds.yaml`。"],
            'tables': [_table('token-inventory', cols, rows)]}


# ---- issuance effects (display-only evaluation; the rule is #6's L62)
def _profile_value(profile, field):
    v = profile.get(field)
    return v.get('value') if isinstance(v, dict) and 'value' in v else v


def _profile_values(profile, field):
    """The value of the field and the values of its per-IdP exceptions (#58; the same reading as L62's _when)."""
    v = profile.get(field)
    exc = v.get('exceptions') or [] if isinstance(v, dict) else []
    return [_profile_value(profile, field)] + [e.get('value') for e in exc if isinstance(e, dict)]


def _when_holds(profile, conds):
    for c in conds:
        vs = _profile_values(profile, c['field'])
        if 'equals' in c and not any(v == c['equals'] for v in vs):
            return False
        if 'includes' in c and not any(isinstance(v, list) and c['includes'] in v for v in vs):
            return False
    return True


SEL_RE = re.compile(r'^(?P<coll>claims|token_types|hops)\[(?P<key>\*|[a-z_]+)(?:(?P<op>!?=)(?P<val>[^\]]+))?\]$')


def _select(d, coll, key, op, val):
    rows = {'claims': [c for c in _claims(d) if _carried(c) or coll != 'claims'],
            'token_types': [t for t in _tts(d) if t.get('decision') != '却下'],
            'hops': d['hops'].get('hops') or []}[coll]
    if key == '*':
        return rows
    want = None if val == 'null' else val
    return [r for r in rows if (r.get(key) == want) == (op == '=')]


def _get(node, parts):
    for p in parts:
        if not isinstance(node, dict) or p not in node:
            return None, False
        node = node[p]
    return node, True


def _includes_token(d, carried, value):
    """carried_in (token type ids) includes a token type matching value ('kind:X', 'transport:Y', alternatives with |)."""
    tts = {t.get('id'): t for t in _tts(d)}
    known = False
    for alt in str(value).split('|'):
        k, _, v = alt.partition(':')
        if k not in ('kind', 'transport'):
            continue
        known = True
        if any((tts.get(tid) or {}).get(k) == v for tid in carried or []):
            return True
    return False if known else None


WORD_RE = re.compile(r'[A-Za-z0-9_#+-]+')


def _matches(v, want):
    """equals: a mapping matches when every key of `want` has that value (other keys of the row are ignored)."""
    if isinstance(want, dict):
        return isinstance(v, dict) and all(_matches(v.get(k), x) for k, x in want.items())
    return v == want


def evaluate_check(d, check):
    """Return (status, matched row ids). status: satisfied / unsatisfied / unknown. A simple reading for display only;
    the rule is #6's L62. `[*]` with includes means every row; all_consumers matches whole words of the checks."""
    path, op, value = check.get('path', ''), check.get('op'), check.get('value')
    if op == 'not_required':
        return 'satisfied', []
    profile = d['token_types'].get('issuance_profile') or {}
    head, _, rest = path.partition('.')
    if head == 'issuance_profile':
        parts = rest.split('.')
        v = _profile_value(profile, parts[0]) if parts[0] in profile else None
        found = parts[0] in profile
        if found and len(parts) > 1:
            v, found = _get(v, parts[1:])
        # every effective value must pass: value and each per-IdP exception (#58, the same reading as L62's _check)
        vs = _profile_values(profile, parts[0]) if found and len(parts) == 1 else [v]
        if op == 'present':
            return ('satisfied' if found and all(not core._empty(v) for v in vs) else 'unsatisfied'), []
        if op == 'absent':
            return ('satisfied' if not found or all(core._empty(v) for v in vs) else 'unsatisfied'), []
        if op == 'equals':
            ok = all((v in value if isinstance(value, list) and not isinstance(v, list) else v == value) for v in vs)
            return ('satisfied' if ok else 'unsatisfied'), []
        if op == 'includes':
            return ('satisfied' if all(isinstance(v, list) and value in v for v in vs) else 'unsatisfied'), []
        return 'unknown', []
    m = SEL_RE.match(head)
    if not m:
        return 'unknown', []
    rows = _select(d, m['coll'], m['key'], m['op'], m['val'])
    fields = rest.split('.') if rest else []
    ids = [r.get('id') for r in rows]
    if not fields:
        if op == 'present':
            return ('satisfied' if rows else 'unsatisfied'), ids
        if op == 'equals' and isinstance(value, dict):
            hit = [r.get('id') for r in rows if _matches(r, value)]
            return ('satisfied' if hit else 'unsatisfied'), hit
        return 'unknown', ids
    vals = [(r.get('id'), *_get(r, fields)) for r in rows]
    if op == 'present':
        hit = [i for i, v, f in vals if f and not core._empty(v)]
        return ('satisfied' if hit else 'unsatisfied'), hit
    if op == 'absent' and value is None:
        hit = [i for i, v, f in vals if f and not core._empty(v)]
        return ('unsatisfied' if hit else 'satisfied'), hit
    if op in ('includes', 'absent') and fields == ['carried_in']:
        res = [(i, _includes_token(d, v, value)) for i, v, f in vals]
        if any(r is None for _, r in res):
            return 'unknown', ids
        hit = [i for i, r in res if r]
        if op == 'includes':
            ok = (rows and len(hit) == len(rows)) if m['key'] == '*' else bool(hit)  # [*]: every row
            return ('satisfied' if ok else 'unsatisfied'), hit
        return ('unsatisfied' if hit else 'satisfied'), hit
    if op == 'equals':
        hit = [i for i, v, f in vals if f and _matches(v, value)]
        return ('satisfied' if hit else 'unsatisfied'), hit
    if op == 'all_consumers' and fields == ['enforced_at']:
        hit = []
        for r in rows:
            checks = {}
            for e in r.get('enforced_at') or []:
                checks.setdefault(e.get('service'), []).append(str(e.get('check')))
            words = {s: set(WORD_RE.findall(' '.join(checks.get(s, [])))) for s in r.get('consumers') or []}
            if r.get('consumers') and all(all(str(x) in words[s] for x in value or []) for s in r['consumers']):
                hit.append(r.get('id'))
        return ('satisfied' if rows and len(hit) == len(rows) else 'unsatisfied'), hit
    return 'unknown', ids


def issuance_effects(d):
    profile = d['token_types'].get('issuance_profile') or {}
    out = []
    for e in d['effects']:
        holds = _when_holds(profile, e.get('when') or [])
        reqs = []
        if holds:
            for r in e.get('requires') or []:
                status, rows = evaluate_check(d, r.get('check') or {})
                reqs.append({'id': r.get('id'), 'target': r.get('target'), 'text': r.get('text'), 'check': r.get('check'),
                             'status': status, 'rows': rows})
        out.append({'id': e.get('id'), 'when': e.get('when'), 'holds': holds, 'requires': reqs, 'refs': e.get('refs') or [],
                    'lint': e.get('lint') or []})
    return out


def _show_profile_value(v):
    if isinstance(v, list):
        return '、'.join(_show_profile_value(x) for x in v) if v else 'なし'
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    label = PROFILE_VALUES.get(v)
    return f'{label}（`{v}`）' if label and label != v else f'`{v}`'


def sec_issuance_profile(d):
    profile = d['token_types'].get('issuance_profile') or {}
    rows = []
    for field, label in PROFILE_FIELDS:
        if field not in profile:
            continue
        p = profile[field] if isinstance(profile[field], dict) else {'value': profile[field]}
        row = {'field': field, 'label': label, 'value': p.get('value'), 'value_text': _show_profile_value(p.get('value')),
               'rationale': p.get('rationale'), 'refs': p.get('refs') or []}
        if p.get('exceptions'):  # #58: per-IdP exceptions, shown with the value and the reason (only when declared)
            row['exceptions'] = p['exceptions']
            row['value_text'] += '。例外：' + '、'.join(f"{e.get('idp')} は {_show_profile_value(e.get('value'))}" for e in p['exceptions'])
            row['rationale'] = (row['rationale'] or '') + ''.join(f"【{e.get('idp')} の例外】{e.get('rationale')}" for e in p['exceptions'])
            row['refs'] = row['refs'] + [r for e in p['exceptions'] for r in e.get('refs') or []]
        rows.append(row)
    effects = issuance_effects(d)
    held = [e for e in effects if e['holds']]
    erows = [{'effect': e['id'], 'id': r['id'], 'text': r['text'], 'status': r['status'],
              'status_text': STATUS[r['status']], 'rows': r['rows'], 'lint': e['lint']}
             for e in held for r in e['requires']]
    notes = ['`token_types.yaml` の `issuance_profile`。既定の組み合わせから外れた点の理由は、手で書く節（既定から外れた点）に書く。']
    tables = [_table('issuance-profile', [('label', '項目', 'text'), ('value_text', '選択', 'raw'), ('rationale', '理由', 'text'),
                                          ('refs', '根拠', 'refs')], rows)]
    after = [f"選択から導かれる要件（`templates/registry/issuance_effects.yaml`）：条件が成り立つ行は {len(held)} 件／全 {len(effects)} 件"
             + ('。' if held else f"（成り立たない行：{'・'.join(e['id'] for e in effects)}）。")]
    if held:
        t = _table('issuance-effects', [('effect', '行', 'code'), ('id', '要件', 'code'), ('text', '台帳で必要になるもの', 'text'),
                                        ('status_text', '簡易な読み取り（正は L62）', 'text'),
                                        ('rows', '満たしている行', 'codes'), ('lint', '規則', 'codes')], erows)
        t['note'] = (after.pop() + '**次の表は検査ではない。** render が `check` を簡易に読み取った表示で、検査の正は'
                     ' `tools/claim_lint/RULES.md` の L62〜L64（#6）。「満たしている行」は、要件の場所にある台帳の行。')
        tables.append(t)
    return {'id': 'issuance-profile', 'title': '発行方式の選択', 'notes': notes, 'tables': tables, 'after': after,
            'effects': effects}


def _claim_by_id(d):
    return {c.get('id'): c for c in _claims(d)}


def sec_hop_table(d):
    cl = _claim_by_id(d)
    rows = []
    for h in d['hops'].get('hops') or []:
        v = h.get('validates') or {}
        # #58: claims the exchanger adds when it mints the token (added_claims) are marked with where the value comes from
        added = {a.get('claim'): ('上流のクレームから導く' if a.get('source') == 'upstream_claims' else a.get('system'))
                 for a in h.get('added_claims') or []}
        rows.append({'id': h.get('id'), 'hop': f"{h.get('id')} {h.get('from')} → {h.get('to')}", 'kind': h.get('kind'),
                     'token_type': h.get('token_type'), 'upstream': h.get('upstream'), 'aud': h.get('aud') or [],
                     'scope': h.get('scope') or [], 'lifetime': _secs(h.get('max_lifetime')),
                     'custom_claims': [(cl.get(x) or {}).get('name', x) + (f'（足す：{added[x]}）' if x in added else '')
                                       for x in h.get('custom_claims') or []],
                     'exchanger': h.get('exchanger'), 'validates_mode': v.get('mode'), 'validates': v.get('checks') or []})
    cols = [('hop', 'ホップ', 'text'), ('kind', '種類', 'code'), ('token_type', '運ぶトークン', 'code'), ('aud', 'aud', 'codes'),
            ('scope', 'scope', 'codes'), ('lifetime', '寿命', 'text'), ('custom_claims', '運ぶ独自クレーム', 'codes'),
            ('exchanger', '交換するサービス', 'text'), ('validates_mode', '検証', 'code'), ('validates', '検証・照合すること', 'list')]
    return {'id': 'hop-table', 'title': 'ホップごとの表', 'notes': ['`hops.yaml` の宣言。トークンのないホップの「運ぶトークン」は —。'],
            'tables': [_table('hop-table', cols, rows)]}


def _service_in(service, text):
    return bool(service) and str(service).lower() in str(text or '').lower()


def sec_arrow_table(d):
    """Per arrow (hop): carried token x the claims the receiving side checks x writer x aud x lifetime."""
    tts = {t.get('id'): t for t in _tts(d)}
    cl = _claim_by_id(d)
    rows = []
    for h in d['hops'].get('hops') or []:
        tid = h.get('token_type')
        if tid:
            cands = [c for c in _claims(d) if _carried(c) and tid in (c.get('carried_in') or [])]
        else:
            cands = [cl[x] for x in h.get('custom_claims') or [] if x in cl]
        hit = False
        for c in cands:
            checks = [e.get('check') for e in c.get('enforced_at') or [] if _service_in(e.get('service'), h.get('to'))]
            if not checks:
                continue
            hit = True
            if tid:
                writers = [f"{w.get('stage')} {w.get('writer')}" for w in c.get('authoritative_writer') or []]
            else:
                # no token on this hop: the sender (`from`) writes the value; the registry says what it copies and where
                # the token's protection ends (integrity_until), so the token's writer is not shown as the writer here
                writers = [f"{h.get('from')}（トークンなし。書き先：{u.get('target')}）" + (f"。{u['trust_boundary']}" if u.get('trust_boundary') else '')
                           for u in c.get('integrity_until') or []] or [f"{h.get('from')}（トークンなし）"]
            rows.append({'hop': h.get('id'), 'token_type': tid, 'claim_id': c.get('id'), 'claim': _full_name(c),
                         'writers': writers,
                         'checks': checks, 'aud': h.get('aud') or (tts.get(tid) or {}).get('aud') or [],
                         'lifetime': _secs(h.get('max_lifetime'))})
        if not hit:
            rows.append({'hop': h.get('id'), 'token_type': tid, 'claim_id': None, 'claim': None, 'writers': [],
                         'checks': [], 'aud': h.get('aud') or [], 'lifetime': _secs(h.get('max_lifetime'))})
    cols = [('hop', 'ホップ', 'code'), ('token_type', 'トークン', 'code'), ('claim', '確かめるクレーム', 'code'),
            ('writers', '書き手', 'list'), ('checks', '確かめること', 'list'), ('aud', 'aud', 'codes'), ('lifetime', '寿命', 'text')]
    return {'id': 'arrow-table', 'title': '矢印ごとの表',
            'notes': ['ホップの受け手（`to`）が `enforced_at` で確かめるクレームを、ホップのトークン（トークンのないホップでは `custom_claims`）から引いた。'
                      'トークンのあるホップの書き手は `authoritative_writer`。トークンのないホップでは、値を書くのは送り手（`from`）なので、'
                      '書き手の列には送り手と、台帳の `integrity_until`（書き先と、署名の保護が外れる境界）を出す。'],
            'tables': [_table('arrow-table', cols, rows)]}


def sec_question_mechanism(d):
    q = d['questions']
    rows = []
    claims = [c for c in _claims(d) if _carried(c)]
    for item, pending in [(x, False) for x in q.get('questions') or []] + [(x, True) for x in q.get('pending') or []]:
        qid = item.get('id')
        ans = [c for c in claims if qid in (c.get('answers') or [])]
        no = [c for c in _claims(d) if qid in (c.get('does_not_answer') or [])]
        mech = [m.get('name') for m in item.get('mechanisms') or []] if not pending else [item.get('mechanisms_hint')]
        services = []
        for c in ans:
            for e in c.get('enforced_at') or []:
                if e.get('service') not in services:
                    services.append(e.get('service'))
        rows.append({'id': qid, 'question': (item.get('text') if not pending else f"{item.get('proposed_text')}（pending）"),
                     'mechanisms': [m for m in mech if m], 'claims': [c.get('name') for c in ans],
                     'claim_ids': [c.get('id') for c in ans], 'not_claims': [c.get('name') for c in no],
                     'services': services, 'pending': pending})
    cols = [('id', 'ID', 'code'), ('question', '問い', 'text'), ('mechanisms', '問いの一覧の仕組み', 'codes'),
            ('claims', '答える台帳の行（answers）', 'codes'), ('not_claims', '答えに使わない行（does_not_answer）', 'codes'),
            ('services', '照合する場所', 'codes')]
    return {'id': 'question-mechanism', 'title': '問い × 仕組み（台帳から引いた分）',
            'notes': ['`templates/registry/questions.yaml` の問いごとに、台帳の `answers`・`does_not_answer` を引いた。'
                      '「不要」の理由は台帳に列がないので、手で書く表に書く。'],
            'tables': [_table('question-mechanism', cols, rows)]}


def sec_lifecycle(d):
    tts = _tts(d)
    by_id = {t.get('id'): t for t in tts}
    hops = d['hops'].get('hops') or []
    adopted = [t for t in tts if t.get('decision') != '却下']
    t1 = [{'id': t.get('id'), 'max_lifetime': t.get('max_lifetime'), 'skew': t.get('max_clock_skew'),
           'set_by': t.get('lifetime_set_by') or [],
           'hops': [f"{h.get('id')} {h.get('max_lifetime')} 秒" for h in hops
                    if h.get('token_type') == t.get('id') and h.get('max_lifetime') is not None]}
          for t in adopted if t.get('kind') not in ('session', 'refresh_token')]
    t2 = []
    for c in _claims(d):
        if not _carried(c) or not c.get('consumers'):
            continue
        vol = c.get('volatility')
        worst, over_tts, measures = 0, [], []
        for x in c.get('carried_in') or []:
            t = by_id.get(x) or {}
            acc = (t.get('max_lifetime') or 0) + (t.get('max_clock_skew') or 0)
            worst = max(worst, acc)
            if isinstance(vol, int) and acc > vol:  # never: the value does not change during the token's life
                over_tts.append(f'{x} {acc} 秒')
                measures += [f"{x}：{REVOCATION.get(r.get('method'), r.get('method'))}（{r.get('delay_seconds')} 秒）"
                             for r in t.get('revocation') or []
                             if r.get('method') != 'exp_only' and r.get('delay_seconds') is not None
                             and r['delay_seconds'] <= vol]
        over = bool(over_tts)
        t2.append({'id': c.get('id'), 'claim': _full_name(c), 'carried_in': c.get('carried_in') or [],
                   'acceptance': _secs(worst), 'volatility': vol, 'propagation_delay': c.get('propagation_delay'),
                   'recompute_trigger': c.get('recompute_trigger') or [], 'on_revoke': c.get('on_revoke'),
                   'exceeds': over, 'exceeds_text': (f"超える（{'・'.join(over_tts)} > 許容 {vol} 秒）" if over
                                                     else '寿命の間に変わらない（never）' if vol == 'never' else NONE),
                   'measures': measures})
    t3 = []
    for t in adopted:
        if t.get('kind') not in ('session', 'refresh_token'):
            continue
        rot = t.get('rt_rotation') or {}
        t3.append({'id': t.get('id'), 'idle': t.get('idle_timeout'), 'max_lifetime': t.get('max_lifetime'),
                   'rotation': None if not rot else ('あり' if rot.get('rotation') else 'なし'),
                   'reuse_detection': rot.get('reuse_detection'),
                   'revocation': [f"{REVOCATION.get(r.get('method'), r.get('method'))}（{r.get('delay_seconds')} 秒）"
                                  for r in t.get('revocation') or []]})
    for h in hops:
        if h.get('kind') in ('db_connection', 'broker_connection'):
            t3.append({'id': f"{h.get('id')}（{h.get('kind')}）", 'idle': None, 'max_lifetime': h.get('connection_max_lifetime'),
                       'rotation': None, 'reuse_detection': None, 'revocation': []})
    t4 = [{'id': c.get('id'), 'claim': _full_name(c), 'status': c.get('status'), 'sunset_on': c.get('sunset_on'),
           'owner': c.get('owner'), 'change_controller': c.get('change_controller')}
          for c in _claims(d) if _carried(c)]
    ns = ['名前空間 `{}` の構造の版：{}'.format(n.get('namespace'), n.get('namespace_version') or NONE)
          for n in d['claims'].get('namespaces') or []]
    return {'id': 'lifecycle', 'title': '寿命の 4 つの層（台帳から引いた分）',
            'notes': ['slide:p08-four-lifetimes の 4 層を、台帳の列から引いた（`templates/registry/README.md` の 6.）。'
                      '長時間の処理と剥奪の反映の書き方は、手で書くライフサイクル表に書く。',
                      '2. の `volatility` は「値が変わってから反映されるまでに許す秒数」（`templates/registry/README.md` の 3.）で、'
                      '0 は即時の反映が要ること、`never` はトークンの寿命の間に値が変わらないことを表す。載るトークンの受け入れの最大（寿命＋時計のずれ）がこれを超える行に「超える」と出し、'
                      '目録の `revocation` のうち遅れが許容以内の手段（`exp_only` を除く）を並べる。その手段がこのクレームの変化に効くかは'
                      '機械では読まないので、台帳の `on_revoke` で確かめる。検査の正は L5（#6）で、この表は検査ではない。'],
            'tables': [
                _table('lifecycle-token', [('id', 'トークン', 'code'), ('max_lifetime', '寿命', 'seconds'), ('skew', '時計のずれ', 'seconds'),
                                           ('set_by', '寿命を変えられる主体', 'codes'), ('hops', 'ホップでの寿命', 'list')], t1,
                       '1. トークンの寿命'),
                _table('lifecycle-claim', [('claim', 'クレーム', 'code'), ('carried_in', '載るトークン', 'codes'),
                                           ('acceptance', '受け入れの最大', 'text'), ('volatility', '反映までに許す秒数', 'seconds'),
                                           ('propagation_delay', '反映の遅れ', 'seconds'), ('recompute_trigger', '再計算', 'codes'),
                                           ('exceeds_text', '受け入れの最大と許容', 'text'),
                                           ('measures', '許容以内の失効の手段（目録）', 'list'),
                                           ('on_revoke', '剥奪・停止のとき（台帳）', 'text')], t2,
                       '2. クレームの値の鮮度（受け手のいる行）'),
                _table('lifecycle-session', [('id', 'セッション・RT・接続', 'code'), ('idle', 'idle', 'seconds'),
                                             ('max_lifetime', '最大', 'seconds'), ('rotation', 'ローテーション', 'text'),
                                             ('reuse_detection', '再利用の検知', 'code'), ('revocation', '失効の手段（遅れ）', 'list')], t3,
                       '3. セッションと RT の寿命'),
                _table('lifecycle-definition', [('claim', 'クレーム', 'code'), ('status', '状態', 'code'), ('sunset_on', '廃止の期限', 'text'),
                                                ('owner', '持ち主', 'text'), ('change_controller', '変更を決める者', 'text')], t4,
                       '4. クレームの定義の寿命')],
            'after': ns}


def sec_catalog_summary(d):
    events = {e.get('id'): e for e in d['events']}
    answers = d['catalog_answers'].get('answers') or []
    by_ev = {a.get('event'): a for a in answers}
    total = len(events)
    n_issue = sum(1 for e in events.values() if e['_file'] == 'issue_events')
    applies = [a for a in answers if a.get('answer') == '該当']
    out = [a for a in answers if a.get('answer') == '対象外']
    missing = [eid for eid in events if eid not in by_ev]
    pct = round(len(out) * 100 / total) if total else 0
    note = (f"`catalog_answers.yaml`：全 {total} 件（発行 {n_issue}・利用 {total - n_issue}）のうち {total - len(missing)} 件に回答。"
            f"該当 {len(applies)} 件、**対象外 {len(out)} 件／全 {total} 件（{pct}%）**。"
            + (f"回答のないイベント：{'・'.join(missing)}。" if missing else ''))

    def name(eid):
        return (events.get(eid) or {}).get('name')
    t_app = [{'event': a.get('event'), 'name': name(a.get('event')), 'token_types': a.get('token_types') or [],
              'note': a.get('note')} for a in applies]
    t_out = [{'event': a.get('event'), 'name': name(a.get('event')), 'assumption': a.get('assumption'),
              'breaks_when': a.get('breaks_when')} for a in out]
    return {'id': 'catalog-summary', 'title': 'カタログへの回答の集計', 'notes': [note],
            'counts': {'total': total, 'issue': n_issue, 'use': total - n_issue, 'answered': total - len(missing),
                       'applies': len(applies), 'out_of_scope': len(out), 'out_of_scope_pct': pct, 'missing': missing},
            'tables': [_table('catalog-applies', [('event', 'イベント', 'code'), ('name', '名前', 'text'),
                                                  ('token_types', 'トークン', 'codes'), ('note', 'メモ', 'text')], t_app, '該当'),
                       _table('catalog-out-of-scope', [('event', 'イベント', 'code'), ('name', '名前', 'text'),
                                                       ('assumption', '起きない前提', 'text'),
                                                       ('breaks_when', '前提が崩れる条件', 'text')], t_out, '対象外')]}


def lint_result(design_dir, doc_path=None):
    extra = [doc_path] if doc_path and os.path.isfile(doc_path) else []
    return core.run(design_dir, extra_files=extra)


def sec_ci_result(d, lint):
    if lint is None:
        return {'id': 'ci-result', 'title': 'CI の結果', 'notes': ['（lint の結果を渡していない）'], 'tables': []}
    c = lint['counts']
    design = lint.get('design')
    rows = [{'rule': f['rule'], 'severity': f['severity'], 'target': f['target'], 'message': f['message']}
            for f in lint['findings']]
    after = []
    for rep in lint.get('r8') or []:
        budgets = '、'.join(f"{b['limit']} {b['used']}／{b['bytes']} バイト" for b in rep.get('budgets') or [])
        after.append(f"R8 {rep['token_type']}：ヘッダー {rep['header_bytes']}・ペイロード {rep['payload_bytes']}・"
                     f"署名 {rep['sig_bytes']} バイト（{rep['formula']}）。{budgets}")
    return {'id': 'ci-result', 'title': 'CI の結果',
            'notes': [f"`python tools/claim_lint {design} --also-scan {design}/{DOC_NAME}`（profile {lint['profile']}）："
                      f"**error {c['error']}、warn {c['warn']}、info {c['info']}**（claims {lint['claims']}・"
                      f"token_types {lint['token_types']}・catalog_events {lint['catalog_events']}）。"
                      + ('OK' if not c['error'] else 'FAIL')],
            'counts': c, 'tables': [_table('ci-result', [('rule', '規則', 'code'), ('severity', '重大度', 'text'),
                                                         ('target', '対象', 'code'), ('message', '内容', 'text')], rows)],
            'after': after}


SECTIONS = [
    ('ci-result', None), ('issuance-profile', sec_issuance_profile), ('token-inventory', sec_token_inventory),
    ('question-mechanism', sec_question_mechanism), ('hop-table', sec_hop_table), ('arrow-table', sec_arrow_table),
    ('lifecycle', sec_lifecycle), ('decision-rows', sec_decision_rows), ('data-sources', sec_data_sources),
    ('catalog-summary', sec_catalog_summary),
]
SECTION_IDS = [s for s, _ in SECTIONS]


def build_sections(d, lint, only=None):
    out = []
    for sid, fn in SECTIONS:
        if only and sid not in only:
            continue
        out.append(sec_ci_result(d, lint) if sid == 'ci-result' else fn(d))
    return out


# ------------------------------------------------------------------ Markdown view
def _esc(s):
    return str(s).replace('\\', '\\\\').replace('|', '\\|').replace('\r\n', '\n').replace('\n', '<br>')


def _ref_md(r):
    if not isinstance(r, dict):
        return _esc(r)
    kind, rid = r.get('kind'), r.get('id')
    if kind == 'guide-slide':
        return f'`slide:{rid}`'
    if kind == 'author-proposal':
        return f"筆者の提案：{_esc(rid)}（{r.get('tracking')}）"
    text = _esc(rid)
    return f"[{text}]({r['url']})" if r.get('url') else text


def cell(v, fmt):
    if v is None or v == [] or v == '':
        return NONE
    if fmt == 'refs':
        return '<br>'.join(_ref_md(r) for r in v)
    if fmt == 'codes':
        return '・'.join(f'`{_esc(x)}`' for x in v) if isinstance(v, list) else f'`{_esc(v)}`'
    if fmt == 'list':
        return '<br>'.join(_esc(x) for x in v) if isinstance(v, list) else _esc(v)
    if fmt == 'seconds':
        return f'{v} 秒' if isinstance(v, (int, float)) and not isinstance(v, bool) else f'`{_esc(v)}`'
    if fmt == 'code':
        return f'`{_esc(v)}`'
    if fmt == 'raw':
        return str(v).replace('|', '\\|')
    if isinstance(v, bool):
        return 'はい' if v else 'いいえ'
    return _esc(v)


def table_md(t):
    cols = t['columns']
    lines = []
    if t.get('note'):
        lines += [t['note'], '']
    if t.get('title'):
        lines += [f"**{t['title']}**", '']
    lines.append('| ' + ' | '.join(c['label'] for c in cols) + ' |')
    lines.append('| ' + ' | '.join('---' for _ in cols) + ' |')
    for r in t['rows']:
        lines.append('| ' + ' | '.join(cell(r.get(c['key']), c['fmt']) for c in cols) + ' |')
    if not t['rows']:
        lines.append('| ' + ' | '.join(NONE for _ in cols) + ' |')
    return '\n'.join(lines)


def section_md(s):
    parts = list(s.get('notes') or [])
    parts += [table_md(t) for t in s.get('tables') or []]
    parts += list(s.get('after') or [])
    return '\n\n'.join(parts)


def render_md(sections, headings=True):
    out = []
    for s in sections:
        out.append((f"## {s['title']}\n\n" if headings else '') + section_md(s))
    return '\n\n'.join(out) + '\n'


# ------------------------------------------------------------------ payload JSON Schemas (slide:p11-schema-contract-tests)
def _value_schema(c, strict):
    t = c.get('type') or 'string'
    base = {'type': t}
    av = c.get('allowed_values') or {}
    vv = c.get('value_vocabulary') or {}
    if strict:
        if t == 'string' and c.get('max_bytes') is not None:
            base['maxLength'] = c['max_bytes']  # characters <= bytes, so this is a necessary condition of max_bytes
        for k, sk in (('pattern', 'pattern'), ('enum', 'enum'), ('format', 'format'), ('min', 'minimum'), ('max', 'maximum')):
            if k in av:
                base[sk] = av[k]
        if vv.get('values') and vv.get('extensible') is False:
            base['enum'] = list(vv['values'])
    if c.get('shape') == 'array':
        s = {'type': 'array', 'items': base}
        if strict and c.get('max_items') is not None:
            s['maxItems'] = c['max_items']
        return s
    if c.get('shape') == 'space_delimited':
        s = {'type': 'string'}
        if strict and c.get('max_bytes') is not None:
            s['maxLength'] = c['max_bytes']
        return s
    return base


def payload_schema(d, tt, kind):
    """kind consumer: unknown claims allowed (additionalProperties true), required claims enforced.
    kind issuer: the issuer may emit only the registry's claims for this token type (additionalProperties false)."""
    strict = kind == 'issuer'
    styles = {n.get('namespace'): n.get('style', 'object') for n in d['claims'].get('namespaces') or []}
    props, nested, nested_req = {}, {}, {}
    for c in _claims(d):
        if not _carried(c) or tt.get('id') not in (c.get('carried_in') or []):
            continue
        s = _value_schema(c, strict)
        s = dict({'description': c.get('description'), '$comment': c.get('id')} if c.get('description') else {'$comment': c.get('id')}, **s)
        ns = c.get('namespace')
        if ns and styles.get(ns, 'object') == 'object':
            nested.setdefault(ns, {})[c['name']] = s
        else:
            props[(ns or '') + c['name']] = s
    required = []
    for r in tt.get('required_claims') or []:
        ns = next((n for n in nested if r.startswith(n + '.')), None)
        if ns:
            nested_req.setdefault(ns, []).append(r[len(ns) + 1:])
            if ns not in required:
                required.append(ns)
        else:
            required.append(r)
    for ns, p in nested.items():
        o = {'type': 'object', 'properties': p, 'additionalProperties': not strict}
        if nested_req.get(ns):
            o['required'] = nested_req[ns]
        props[ns] = o
    # an aud of the consumer schema may be a string or an array (RFC 7519 §4.1.3), so a receiver is not broken by
    # an issuer that starts sending several audiences; the issuer schema keeps the registry's shape
    # the issuer schema allows only the token type's audiences (PR #47 check, 3: maxLength alone let a short foreign
    # audience such as "account" through)
    if strict and isinstance(props.get('aud'), dict) and tt.get('aud'):
        a = props['aud']
        target = a['items'] if a.get('type') == 'array' and isinstance(a.get('items'), dict) else a
        target['enum'] = list(tt['aud'])
    if not strict and isinstance(props.get('aud'), dict):
        a = props['aud']
        props['aud'] = {k: v for k, v in a.items() if k not in ('type', 'items')}
        props['aud']['anyOf'] = [{'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}]
    ver = d.get('_template_version') or '0.0.0'
    return {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$id': f"{REPO_URL}/payload-schemas/{d.get('_design', 'design')}/{tt.get('id')}.{kind}.schema.json/v{ver}",
        '$comment': f"template_version: {ver}. Generated by `python tools/claim_lint render` (#19) from the registry of "
                    f"this design; do not edit. Token type {tt.get('id')} ({tt.get('kind')}), {kind} schema.",
        'title': f"{tt.get('id')} payload ({'consumer: unknown claims allowed' if not strict else 'issuer conformance: registry claims only'})",
        'type': 'object', 'properties': props, 'required': required, 'additionalProperties': not strict}


def schema_token_types(d):
    return [t for t in _tts(d) if t.get('decision') != '却下' and t.get('format') == 'jwt']


def payload_schemas(d):
    return {t['id']: {k: payload_schema(d, t, k) for k in ('consumer', 'issuer')} for t in schema_token_types(d)}


def schema_files(d):
    out = {}
    for tid, kinds in payload_schemas(d).items():
        for k, s in kinds.items():
            out[f'{SCHEMA_DIR}/{tid}.{k}.schema.json'] = json.dumps(s, ensure_ascii=False, indent=1) + '\n'
    return out


def read_payload(path):
    """A payload JSON object, a fixture with payload_json / token (tools/tests/fixtures/claim_lint/golden/token.json),
    or a file holding a compact JWS. The signature is not verified: this checks the shape only."""
    with open(path, encoding='utf-8') as f:
        text = f.read().strip()
    if text.startswith('{'):
        obj = json.loads(text)
        if 'payload_json' in obj:
            return json.loads(obj['payload_json'])
        if 'token' in obj and isinstance(obj['token'], str):
            text = obj['token']
        else:
            return obj
    part = text.split('.')[1]
    return json.loads(base64.urlsafe_b64decode(part + '=' * (-len(part) % 4)))


def validate_payload(d, payload, token_type, kind='issuer'):
    import jsonschema
    tt = next((t for t in schema_token_types(d) if t.get('id') == token_type), None)
    if tt is None:
        raise SystemExit(f'render: no adopted JWT token type {token_type!r} in token_types.yaml')
    v = jsonschema.Draft202012Validator(payload_schema(d, tt, kind))
    return [f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}"
            for e in sorted(v.iter_errors(payload), key=lambda e: list(map(str, e.absolute_path)))]


# ------------------------------------------------------------------ bundle (viewer, #36)
def _sha(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read().replace(b'\r\n', b'\n')).hexdigest()


def bundle(design_dir, d, sections):
    files = {}
    for k in ('claims', 'token_types', 'hops', 'catalog_answers'):
        p = os.path.join(design_dir, k + '.yaml')
        if os.path.isfile(p):
            files[k + '.yaml'] = _sha(p)
    for rel in ('questions.yaml', 'issuance_effects.yaml'):
        files['templates/registry/' + rel] = _sha(os.path.join(REGISTRY, rel))
    for rel in ('token_kinds.yaml', 'issue_events.yaml', 'use_events.yaml'):  # kind names, event names and counts
        files['templates/catalog/' + rel] = _sha(os.path.join(CATALOG, rel))
    return {'format': BUNDLE_FORMAT, 'design': core._rel(design_dir, ROOT), 'generator': 'python tools/claim_lint render',
            'sources': files, 'section_ids': [s['id'] for s in sections], 'sections': sections,
            'payload_schemas': payload_schemas(d),
            'registry': {k: d[k] for k in ('claims', 'token_types', 'hops', 'catalog_answers')}}


# ------------------------------------------------------------------ marked regions of design.md
REGION_RE = re.compile(r'<!-- render:(?P<id>[a-z0-9-]+):begin -->\n(?P<body>.*?)<!-- render:(?P=id):end -->', re.S)
MARK_RE = re.compile(r'<!-- render:([a-z0-9-]+):(begin|end) -->')


def regions(text):
    """{id: body}. Raises ValueError on unknown ids, duplicates or unbalanced markers."""
    found, problems = {}, []
    for m in REGION_RE.finditer(text):
        if m['id'] in found:
            problems.append(f"region {m['id']} appears twice")
        found[m['id']] = m['body']
    marks = MARK_RE.findall(text)
    if len(marks) != 2 * len(list(REGION_RE.finditer(text))):
        problems.append('unbalanced or nested render markers')
    for rid in found:
        if rid not in SECTION_IDS:
            problems.append(f'unknown region {rid} (known: {", ".join(SECTION_IDS)})')
    if problems:
        raise ValueError('; '.join(problems))
    return found


def fill_regions(text, by_id):
    return REGION_RE.sub(lambda m: f"<!-- render:{m['id']}:begin -->\n{by_id[m['id']]}<!-- render:{m['id']}:end -->", text)


def _read_text(path):
    with open(path, encoding='utf-8', newline='') as f:
        raw = f.read()
    return raw.replace('\r\n', '\n'), ('\r\n' if '\r\n' in raw else '\n')


def _write_text(path, text, nl='\n'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text.replace('\n', nl))


def expected_outputs(design_dir, doc_path, lint=None):
    """{path: expected text} for the regions of design.md and the schema files."""
    d = load_design(design_dir)
    out = {}
    if os.path.isfile(doc_path):
        text, _ = _read_text(doc_path)
        ids = regions(text)
        need_lint = 'ci-result' in ids
        if need_lint and lint is None:
            lint = lint_result(design_dir, doc_path)
        secs = {s['id']: s for s in build_sections(d, lint if need_lint else None, only=set(ids))}
        out[doc_path] = fill_regions(text, {k: section_md(secs[k]) + '\n' for k in ids})
    for rel, body in schema_files(d).items():
        out[os.path.join(design_dir, *rel.split('/'))] = body
    return out


def orphan_schemas(design_dir, expected):
    """schemas/*.schema.json that the registry no longer generates (a token type rejected, removed or not a JWT)."""
    base = os.path.join(design_dir, SCHEMA_DIR)
    if not os.path.isdir(base):
        return []
    want = {os.path.normcase(os.path.abspath(p)) for p in expected}
    return sorted(os.path.join(base, f) for f in os.listdir(base)
                  if f.endswith('.schema.json') and os.path.normcase(os.path.abspath(os.path.join(base, f))) not in want)


def check(design_dir, doc_path, lint=None):
    problems = []
    expected = expected_outputs(design_dir, doc_path, lint)
    for path in orphan_schemas(design_dir, expected):
        problems.append(f'{core._rel(path, ROOT)}: not generated from the registry any more (run render --write to remove it)')
    for path, want in expected.items():
        have = _read_text(path)[0] if os.path.isfile(path) else None
        if have != want:
            rel = core._rel(path, ROOT)
            if have is None:
                problems.append(f'{rel}: missing (run render --write)')
                continue
            diff = difflib.unified_diff(have.splitlines(), want.splitlines(), f'{rel} (file)', f'{rel} (generated)', lineterm='', n=0)
            problems.append(f'{rel}: differs from the registry (run render --write)\n' + '\n'.join(list(diff)[:80]))
    return problems


def write(design_dir, doc_path, lint=None):
    changed = []
    expected = expected_outputs(design_dir, doc_path, lint)
    for path in orphan_schemas(design_dir, expected):
        os.remove(path)
        changed.append('removed ' + core._rel(path, ROOT))
    for path, want in expected.items():
        have, nl = _read_text(path) if os.path.isfile(path) else (None, '\n')
        if have != want:
            _write_text(path, want, nl)
            changed.append(core._rel(path, ROOT))
    return changed


# ------------------------------------------------------------------ CLI
def main(argv=None):
    ap = argparse.ArgumentParser(prog='claim_lint render', description='Generate design-document tables, a JSON bundle and payload JSON Schemas from a registry (#19).')
    ap.add_argument('design_dir')
    ap.add_argument('--format', choices=('md', 'json'), default='md')
    ap.add_argument('--section', action='append', choices=SECTION_IDS, help='only these sections (repeatable)')
    ap.add_argument('--out', help='write the output to this file instead of stdout')
    ap.add_argument('--doc', help=f'design document with render regions (default DESIGN_DIR/{DOC_NAME})')
    ap.add_argument('--lint-json', help='use this claim_lint --format json result for the CI section instead of running claim_lint')
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--write', action='store_true', help='rewrite the regions of the design document and schemas/*.json')
    g.add_argument('--check', action='store_true', help='exit 1 when the regions or schemas differ from the registry')
    g.add_argument('--validate', metavar='TOKEN', help='validate a token payload (JSON, fixture or compact JWS) against a payload schema')
    ap.add_argument('--token-type', default='AT')
    ap.add_argument('--schema-kind', choices=('issuer', 'consumer'), default='issuer')
    a = ap.parse_args(argv)
    design_dir = os.path.abspath(a.design_dir)
    doc = os.path.abspath(a.doc) if a.doc else os.path.join(design_dir, DOC_NAME)
    lint = None
    if a.lint_json:
        with open(a.lint_json, encoding='utf-8') as f:
            lint = json.load(f)
    out = sys.stdout.buffer
    if a.validate:
        errs = validate_payload(load_design(design_dir), read_payload(a.validate), a.token_type, a.schema_kind)
        for e in errs:
            out.write((f'{a.token_type} {a.schema_kind}: {e}\n').encode('utf-8'))
        out.write((f"{a.validate}: {'FAIL' if errs else 'OK'} ({a.token_type}, {a.schema_kind} schema)\n").encode('utf-8'))
        return 1 if errs else 0
    if a.check or a.write:
        try:
            if a.check:
                problems = check(design_dir, doc, lint)
                for p in problems:
                    out.write((p + '\n').encode('utf-8'))
                out.write(('render --check: ' + ('FAIL' if problems else 'OK') + '\n').encode('utf-8'))
                return 1 if problems else 0
            for p in write(design_dir, doc, lint):
                out.write(((p if p.startswith('removed ') else 'updated ' + p) + '\n').encode('utf-8'))
            return 0
        except ValueError as e:
            out.write(f'render: {doc}: {e}\n'.encode('utf-8'))
            return 1
    d = load_design(design_dir)
    only = set(a.section) if a.section else None
    if lint is None and (only is None or 'ci-result' in only):
        lint = lint_result(design_dir, doc)
    sections = build_sections(d, lint, only)
    if a.format == 'json':
        text = json.dumps(bundle(design_dir, d, sections), ensure_ascii=False, indent=1) + '\n'
    else:
        text = render_md(sections)
    if a.out:
        _write_text(os.path.abspath(a.out), text)
    else:
        out.write(text.encode('utf-8'))
    return 0
