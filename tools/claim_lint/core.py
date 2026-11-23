# -*- coding: utf-8 -*-
"""claim_lint (#16, #17, #3): load a design's registry, validate it against the schemas, and check rules R1, R2, R8, the
references between the files (REF), the slide references, and the coverage rules R3, R3b, R4, R6, R9, R10
(coverage.py). Rules are described in tools/claim_lint/RULES.md.

Input directory (e.g. templates/examples/scenario-a):
  claims.yaml            claim registry (templates/registry/claims.schema.json)
  token_types.yaml       token inventory, issuance profile and R8 inputs (templates/registry/token_types.schema.json)
  hops.yaml              per-hop declarations (templates/registry/hops.schema.json); optional, reported as info when absent
  catalog_answers.yaml   an answer for every event of the catalogue (templates/catalog/*.yaml)
The question IDs of claims.yaml (answers, does_not_answer) are those of templates/registry/questions.yaml.
"""
import json
import math
import os
import sys

import yaml

from . import coverage, purpose, r8, semantic

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
ROOT = os.path.dirname(TOOLS)
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
import check_slide_refs  # noqa: E402  (tools/check_slide_refs.py, #15)

ERROR, WARN, INFO = 'error', 'warn', 'info'
SEVERITIES = (ERROR, WARN, INFO)
MIN_REASON = 10  # characters for assumption / breaks_when of a 対象外 answer (author-proposal, tracking #16)

# R1: columns that must be filled. The slide-134 items (slide:p11-registry-fields) are the core of CARRIED.
COMMON = ['id', 'name', 'decision', 'rationale']
CARRIED = ['namespace', 'type', 'shape', 'description', 'not_meaning', 'usage', 'issuers', 'authoritative_writer',
           'issue_events', 'consumers', 'carried_in', 'on_missing', 'max_bytes', 'overflow_strategy', 'pii_category',
           'log_policy', 'owner', 'source_system', 'volatility', 'propagation_delay', 'status', 'data_category',
           'confidential_from']
# columns whose honest answer can be "none": the key must be written, the value may be null / []
MAY_BE_NONE = {'namespace': '最上位のクレームは null と書く', 'consumers': '読む受け手がいないなら [] と書く',
               'confidential_from': '改ざん防止だけで足りるなら [] と書く'}
TWO_OF =['refs', 'assumption', 'revisit_trigger']  # 採用 (deviation from the default) and 却下 need two of these (#3)
TT_COMMON = ['id', 'kind', 'decision', 'rationale', 'format']
TT_ADOPTED = ['purpose', 'issuer', 'holder', 'max_lifetime', 'stored_at', 'transport', 'revocation', 'visible_to']
TT_JWT = ['typ', 'alg_allowlist', 'issuers', 'key_rotation', 'jwe']
HEADER_TRANSPORTS = {'authorization_bearer', 'authorization_dpop', 'cookie'}
IDLE_KINDS = {'refresh_token', 'session'}  # idle and absolute lifetimes are separate columns (gate1.md 5., A14)
# R8 info: claims of the ID token (OpenID Connect Core 1.0 §2) or of the JWT access token (RFC 9068 §2.2, §2.2.1)
IDT_AT_REGISTERED = {'iss', 'sub', 'aud', 'exp', 'iat', 'auth_time', 'nonce', 'acr', 'amr', 'azp', 'client_id', 'jti'}


class Finding(dict):
    def __init__(self, rule, severity, target, message, **extra):
        super().__init__(rule=rule, severity=severity, target=target, message=message, **extra)


def _empty(v):
    """None, an empty or whitespace-only string, an empty list or mapping (a list of blank strings is empty too)."""
    if isinstance(v, str):
        return v.strip() == ''
    if isinstance(v, list):
        return all(_empty(x) for x in v)
    return v is None or v == {}


class _Loader(yaml.SafeLoader):
    """SafeLoader that keeps dates as strings (the schemas say string) and rejects duplicate keys."""


_Loader.yaml_implicit_resolvers = {k: [r for r in v if r[0] != 'tag:yaml.org,2002:timestamp']
                                   for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()}


def _mapping(loader, node, deep=False):
    keys = set()
    for k, _ in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in keys:
            raise yaml.constructor.ConstructorError(None, None, f'duplicate key {key!r}', k.start_mark)
        keys.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


_Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def load_yaml(path):
    with open(path, encoding='utf-8') as f:
        return yaml.load(f, Loader=_Loader)


def schema_check(doc, schema_path, where):
    import jsonschema
    with open(schema_path, encoding='utf-8') as f:
        schema = json.load(f)
    v = jsonschema.Draft202012Validator(schema)
    out = []
    for e in sorted(v.iter_errors(doc), key=lambda e: list(e.absolute_path)):
        loc = '/'.join(str(p) for p in e.absolute_path) or '(root)'
        out.append(Finding('SCHEMA', ERROR, f'{where}:{loc}', e.message))
    return out


# ------------------------------------------------------------------ R1
def rule_r1(claims, token_types):
    out = []
    for c in claims:
        cid = c.get('id', '?')
        need = list(COMMON)
        if c.get('decision') in ('採用', '既定どおり'):
            need += CARRIED
            if c.get('shape') == 'array':
                need.append('max_items')
        for k in need:
            if k in MAY_BE_NONE:
                if k not in c:
                    out.append(Finding('R1', ERROR, cid, f'{k} がない（{MAY_BE_NONE[k]}）'))
                continue
            if _empty(c.get(k)):
                out.append(Finding('R1', ERROR, cid, f'必須の列 {k} が空'))
        if c.get('decision') in ('採用', '却下'):
            have = [k for k in TWO_OF if not _empty(c.get(k))]
            if len(have) < 2:
                out.append(Finding('R1', ERROR, cid, f"{c.get('decision')} には refs・assumption・revisit_trigger のうち 2 つ以上が要る（あるのは {have or 'なし'}）"))
    for t in token_types:
        tid = t.get('id', '?')
        need = list(TT_COMMON)
        if t.get('decision') in ('採用', '既定どおり'):
            need += TT_ADOPTED
            if t.get('kind') in IDLE_KINDS:
                need.append('idle_timeout')
            if t.get('format') == 'jwt':
                need += TT_JWT
                if t.get('transport') in HEADER_TRANSPORTS:
                    need.append('size')
        for k in need:
            if _empty(t.get(k)):
                out.append(Finding('R1', ERROR, f'token_type {tid}', f'必須の列 {k} が空'))
    return out


# ------------------------------------------------------------------ R2
def rule_r2(answers_doc, catalog, profile, tt_ids=None):
    """Every catalogue event has 該当 or 対象外. 対象外 needs assumption and breaks_when with substance (the same test
    as catalog_check's seed items: >= MIN_REASON characters, not one repeated character, not the event ID or name, not
    equal to each other). Lite may inherit the IdP default for an event that one client setting stops (coverage.py)."""
    out = []
    sev = WARN if profile == 'lite' else ERROR
    idp = coverage.idp_name(answers_doc)
    answers = {}
    for a in (answers_doc or {}).get('answers', []) or []:
        eid = a.get('event')
        if eid in answers:
            out.append(Finding('R2', ERROR, eid, '同じイベントに回答が 2 つある'))
        answers[eid] = a
    known = {e['id']: e for e in catalog}
    for eid in known:
        a = answers.get(eid)
        if a is None:
            out.append(Finding('R2', sev, eid, f"カタログのイベント {eid}（{known[eid].get('name')}）に回答がない"))
            continue
        ans = a.get('answer')
        label = (eid, known[eid].get('name'))
        if a.get('inherit') is not None:
            if a.get('inherit') != coverage.INHERIT:
                out.append(Finding('R2', sev, eid, f"inherit に書けるのは {coverage.INHERIT} だけ（あるのは {a.get('inherit')!r}）"))
            else:
                out += coverage.r2_inherit(a, known[eid], idp, profile, sev)
            continue
        if tt_ids is not None:
            for t in a.get('token_types') or []:
                if t not in tt_ids:
                    out.append(Finding('R2', ERROR, eid, f'token_types の {t} がトークン目録（token_types.yaml）にない'))
        if ans == '該当':
            if _empty(a.get('token_types')) and _empty(a.get('note')):
                out.append(Finding('R2', sev, eid, '該当の回答に、関係するトークン種別（token_types）か説明（note）がない'))
        elif ans == '対象外':
            for k in ('assumption', 'breaks_when'):
                if coverage.weak(a.get(k), label):
                    out.append(Finding('R2', sev, eid, f'対象外の回答に {k} がない、{MIN_REASON} 字未満、同じ文字の繰り返し、'
                                                       'またはイベントの ID・名前そのもの'))
            if not _empty(a.get('assumption')) and a.get('assumption') == a.get('breaks_when'):
                out.append(Finding('R2', sev, eid, 'assumption と breaks_when が同じ文'))
        else:
            out.append(Finding('R2', sev, eid, f'回答は「該当」か「対象外」（あるのは {ans!r}）'))
    for eid in answers:
        if eid not in known:
            out.append(Finding('R2', ERROR, eid, 'カタログにないイベント ID への回答'))
    return out


# ------------------------------------------------------------------ REF (#3)
def load_questions(path):
    doc = load_yaml(path) or {}
    return {q['id'] for q in doc.get('questions') or []}, {q['id'] for q in doc.get('pending') or []}


def rule_ref(claims_doc, token_types, hops_doc, questions):
    """IDs that one file uses must exist in the file that defines them (claims, token_types, hops, questions.yaml),
    and an organization sub-category of data_category sits below its parent."""
    out = []
    active, pending = questions
    cids = {c.get('id') for c in claims_doc.get('claims') or []}
    tids = {t.get('id') for t in token_types}

    def need(target, what, ref, known, label):
        if ref is not None and ref not in known:
            out.append(Finding('REF', ERROR, target, f'{what} の {ref} が{label}にない'))

    for c in claims_doc.get('claims') or []:
        cid = c.get('id', '?')
        for k in ('answers', 'does_not_answer'):
            for q in c.get(k) or []:
                if q in pending:
                    out.append(Finding('REF', ERROR, cid, f'{k} の {q} は questions.yaml の pending（スライドに同じ文言の問いがない）。'
                                                          'スライドを直して questions に載せるまで参照しない'))
                else:
                    need(cid, k, q, active, ' questions.yaml の questions')
        need(cid, 'paired_id', c.get('paired_id'), cids, '台帳')
        for e in c.get('enforced_at') or []:
            need(cid, 'enforced_at.with', e.get('with'), cids, '台帳')
        for a in c.get('alt') or []:
            if str(a).startswith('C-'):
                need(cid, 'alt', a, cids, '台帳')
    for ns in claims_doc.get('namespaces') or []:
        need(f"namespace {ns.get('namespace')}", 'namespace_version', ns.get('namespace_version'), cids, '台帳')
    for e in claims_doc.get('data_category_extensions') or []:
        if not str(e.get('key', '')).startswith(str(e.get('parent', '')) + '.'):
            out.append(Finding('REF', ERROR, f"data_category_extensions {e.get('key')}",
                               f"key は parent（{e.get('parent')}）の子（parent + '.' で始まる）にする"))
    for t in token_types:
        need(f"token_type {t.get('id')}", 'tenant_binding.claim', (t.get('tenant_binding') or {}).get('claim'), cids, '台帳')
    hops = (hops_doc or {}).get('hops') or []
    hids = [h.get('id') for h in hops]
    for h in hops:
        hid = f"hop {h.get('id')}"
        if hids.count(h.get('id')) > 1:
            out.append(Finding('REF', ERROR, hid, 'ホップの id が重複している'))
        need(hid, 'token_type', h.get('token_type'), tids, 'トークン目録（token_types.yaml）')
        need(hid, 'upstream', h.get('upstream'), set(hids), ' hops.yaml')
        seen, cur = [h.get('id')], h.get('upstream')
        by_id = {x.get('id'): x for x in hops}
        while cur is not None and cur in by_id:
            if cur in seen:
                out.append(Finding('REF', ERROR, hid, f"upstream が循環している（{' → '.join(seen + [cur])}）"))
                break
            seen.append(cur)
            cur = by_id[cur].get('upstream')
        for x in h.get('custom_claims') or []:
            need(hid, 'custom_claims', x, cids, '台帳')
        for fh in h.get('forwarded_headers') or []:
            need(hid, 'forwarded_headers.claim', fh.get('claim'), cids, '台帳')
    return out


# ------------------------------------------------------------------ R8
def load_limits(path):
    return {x['id']: x for x in (load_yaml(path) or {}).get('limits', [])}


def rule_r8(claims, token_types, limits):
    out, reports = [], []
    by_tt = {}
    for c in claims:
        if c.get('decision') in ('採用', '既定どおり'):
            for tt in c.get('carried_in') or []:
                by_tt.setdefault(tt, []).append(c)
    tt_ids = {t.get('id') for t in token_types}
    for tt, cs in by_tt.items():
        if tt not in tt_ids:
            out.append(Finding('R8', ERROR, tt, f"carried_in のトークン種別 {tt} が token_types にない（{', '.join(c['id'] for c in cs)}）"))
    for t in token_types:
        size = t.get('size')
        if not size or t.get('decision') == '却下':
            continue
        tid = t['id']
        members, bad = [], False
        for c in by_tt.get(tid, []):
            if c.get('shape') == 'array' and not c.get('max_items'):
                out.append(Finding('R8', ERROR, c['id'], '配列のクレームに max_items がない（値域が無制限）'))
                bad = True
                continue
            if c.get('shape') == 'array' and _empty(c.get('overflow_strategy')):
                out.append(Finding('R8', ERROR, c['id'], '配列のクレームに overflow_strategy（超えたときの方針）がない'))
            v = r8.worst_value_len(c)
            if v is None:
                out.append(Finding('R8', ERROR, c['id'], f'{tid} に載るのに max_bytes がない'))
                bad = True
                continue
            members.append({'name': c['name'], 'namespace': c.get('namespace'), 'value_len': v})
        sig = r8.sig_octets(size['signing'])
        if sig is None:
            out.append(Finding('R8', ERROR, tid, f"署名の長さが分からない（alg={size['signing'].get('alg')}、RSA なら key_bits が要る）"))
            bad = True
        if bad:
            continue
        hdr = r8.header_len(size['header'])
        pay = r8.object_len(r8.payload_members(members))
        enc = r8.encoded_size(hdr, pay, sig)
        bearer = t.get('transport') == 'authorization_bearer'
        value = enc['token'] + (r8.BEARER_PREFIX if bearer else 0)
        field = value + (r8.FIELD_NAME if t.get('transport', '').startswith('authorization') else 0)
        budgets = []
        for p in size['path']:
            lim = limits.get(p) if isinstance(p, str) else p
            if lim is None:
                out.append(Finding('R8', ERROR, tid, f'経路の上限 {p} が path_limits.yaml にない（確かめていない値は既定にしない。根拠を付けて宣言する）'))
                continue
            if lim['applies_to'] == 'all_headers':
                if size.get('other_headers_bytes') is None:
                    out.append(Finding('R8', ERROR, tid, f"{lim['id']} は要求行と全ヘッダーの合計の上限。size.other_headers_bytes を宣言する"))
                    continue
                used = field + size['other_headers_bytes']
            else:
                used = field
            budgets.append({'limit': lim['id'], 'applies_to': lim['applies_to'], 'bytes': lim['bytes'], 'used': used})
        rep = {'token_type': tid, 'header_bytes': hdr, 'payload_bytes': pay, 'sig_bytes': sig, **enc,
               'header_value_bytes': value, 'header_field_bytes': field, 'budgets': budgets,
               'formula': f"ceil(4/3*{hdr}) + ceil(4/3*{pay}) + ceil(4/3*{sig}) + 2 = {enc['header_b64']} + {enc['payload_b64']} + {enc['sig_b64']} + 2 = {enc['token']}"
                          + (f"; + 7 (Bearer) = {value}" if bearer else '')}
        reports.append(rep)
        if budgets:
            tight = min(budgets, key=lambda b: b['bytes'] - b['used'])
            ratio = tight['used'] / tight['bytes']
            rep['tightest'] = tight['limit']
            rep['ratio'] = round(ratio, 4)
            msg = f"最悪 {enc['token']} バイト（ヘッダーの行で {tight['used']}）／上限 {tight['bytes']}（{tight['limit']}）= {ratio:.0%}"
            if tight['used'] > tight['bytes']:
                out.append(Finding('R8', ERROR, tid, msg + '。上限を超える。載せるか問い合わせるか（slide:p04-carry-or-query）を見直す'))
            elif ratio > r8.WARN_RATIO:
                out.append(Finding('R8', WARN, tid, msg + f'。予算の {r8.WARN_RATIO:.0%} を超える（しきい値は筆者の提案）'))
            else:
                out.append(Finding('R8', INFO, tid, msg))
    # info: the same non-protocol claim on more than one carried token type. A registered top-level claim that both the
    # ID token (OpenID Connect Core 1.0 §2) and the JWT access token (RFC 9068 §2.2) define is not a duplicate (#6, from
    # gate1.md 5.: iss, sub, aud, azp were the 4 false candidates of scenario A)
    for c in claims:
        if c.get('namespace') is None and c.get('registered_ref') and c.get('name') in IDT_AT_REGISTERED:
            continue
        if c.get('decision') in ('採用', '既定どおり') and c.get('usage') != 'protocol' and len(c.get('carried_in') or []) > 1:
            out.append(Finding('R8', INFO, c['id'], f"{'・'.join(c['carried_in'])} の両方に載る（重複の候補）"))
    return out, reports


# ------------------------------------------------------------------ slide references
def _rel(path, root):
    try:
        return os.path.relpath(path, root).replace(os.sep, "/")
    except ValueError:  # another drive on Windows
        return path.replace(os.sep, "/")


def _known_slides(root):
    with open(os.path.join(root, 'deck', 'slide_ids.json'), encoding='utf-8') as f:
        return {x['id'] for x in json.load(f)}


def _walk_refs(node, out):
    if isinstance(node, dict):
        if node.get('kind') == 'guide-slide' and 'id' in node:
            out.append(node['id'])
        for v in node.values():
            _walk_refs(v, out)
    elif isinstance(node, list):
        for v in node:
            _walk_refs(v, out)
    return out


def rule_slides(docs, files, root):
    known = _known_slides(root)
    out = []
    for where, doc in docs.items():
        for sid in _walk_refs(doc, []):
            if sid not in known:
                out.append(Finding('SLIDE', ERROR, where, f'guide-slide の ID {sid} がスライドにない'))
    for f in files:
        with open(f, encoding='utf-8-sig') as fh:
            _, errs = check_slide_refs.scan_text(fh.read(), known, _rel(f, root))
        out += [Finding('SLIDE', ERROR, _rel(f, root), e) for e in errs]
    return out


# ------------------------------------------------------------------ driver
def run(design_dir, catalog_dir=None, limits_path=None, profile='full', root=ROOT, extra_files=(), today=None, caps_path=None):
    catalog_dir = catalog_dir or os.path.join(root, 'templates', 'catalog')
    limits_path = limits_path or os.path.join(HERE, 'path_limits.yaml')
    reg = os.path.join(root, 'templates', 'registry')
    findings = []
    paths = {k: os.path.join(design_dir, k + '.yaml') for k in ('claims', 'token_types', 'catalog_answers', 'hops')}
    docs = {}
    for k, p in paths.items():
        if k == 'hops' and not os.path.isfile(p):
            findings.append(Finding('LOAD', INFO, k, 'hops.yaml がない（ホップごとの宣言。交換・作り直しのホップがあれば書く）'))
            docs[k] = {}
            continue
        if not os.path.isfile(p):
            findings.append(Finding('LOAD', ERROR, k, f'{p} がない'))
            docs[k] = {}
            continue
        try:
            docs[k] = load_yaml(p) or {}
        except yaml.YAMLError as e:
            findings.append(Finding('LOAD', ERROR, k, f'YAML の誤り: {e}'))
            docs[k] = {}
    findings += schema_check(docs['claims'], os.path.join(reg, 'claims.schema.json'), 'claims')
    findings += schema_check(docs['token_types'], os.path.join(reg, 'token_types.schema.json'), 'token_types')
    if docs['hops']:
        findings += schema_check(docs['hops'], os.path.join(reg, 'hops.schema.json'), 'hops')
    claims = docs['claims'].get('claims') or []
    tts = docs['token_types'].get('token_types') or []
    catalog = []
    for name in ('issue_events', 'use_events'):
        catalog += (load_yaml(os.path.join(catalog_dir, name + '.yaml')) or {}).get('events', [])
    findings += rule_r1(claims, tts)
    findings += rule_ref(docs['claims'], tts, docs['hops'], load_questions(os.path.join(reg, 'questions.yaml')))
    findings += rule_r2(docs['catalog_answers'], catalog, profile, {t.get('id') for t in tts})
    findings += coverage.rule_r3(docs['catalog_answers'], catalog_dir)
    findings += coverage.rule_r3b(claims, docs['catalog_answers'], catalog, catalog_dir, tts)
    findings += coverage.rule_r4(docs['catalog_answers'], tts, catalog_dir, profile)
    findings += coverage.rule_r6(docs['catalog_answers'], catalog)
    findings += coverage.rule_r9(docs['catalog_answers'], today)
    r8_findings, reports = rule_r8(claims, tts, load_limits(limits_path))
    findings += r8_findings
    findings += coverage.rule_r10(catalog_dir, limits_path, tts, today)
    sem_findings, checked = semantic.run(docs, profile, design_dir, root, catalog_dir, today, caps_path)  # #6
    findings += sem_findings
    pur_findings, pur_checked = purpose.run(docs, root)  # #18: declaration consistency only
    findings += pur_findings
    checked.update(pur_checked)
    files = [p for p in paths.values() if os.path.isfile(p)] + list(extra_files)
    findings += rule_slides({k: docs[k] for k in docs}, files, root)
    counts = {s: sum(1 for f in findings if f['severity'] == s) for s in SEVERITIES}
    return {'design': _rel(design_dir, root), 'profile': profile,
            'counts': counts, 'findings': findings, 'r8': reports, 'checked': checked,
            'catalog_events': len(catalog), 'claims': len(claims), 'token_types': len(tts)}


def format_table(result):
    lines = [f"claim_lint  design={result['design']}  profile={result['profile']}  "
             f"claims={result['claims']}  token_types={result['token_types']}  catalog_events={result['catalog_events']}", '']
    rows = [('rule', 'severity', 'target', 'message')] + [(f['rule'], f['severity'], f['target'], f['message']) for f in result['findings']]
    w = [max(len(str(r[i])) for r in rows) for i in range(3)]
    for r in rows:
        lines.append(f'{r[0]:<{w[0]}}  {r[1]:<{w[1]}}  {r[2]:<{w[2]}}  {r[3]}')
    lines.append('')
    for rep in result['r8']:
        lines.append(f"R8 {rep['token_type']}: header {rep['header_bytes']} B, payload {rep['payload_bytes']} B, sig {rep['sig_bytes']} B -> {rep['formula']}")
        for b in rep['budgets']:
            lines.append(f"   {b['limit']} ({b['applies_to']}): used {b['used']} / {b['bytes']}")
    c = result['counts']
    lines.append(f"error {c['error']}, warn {c['warn']}, info {c['info']}")
    lines.append('FAIL' if c['error'] else 'OK')
    return '\n'.join(lines)
