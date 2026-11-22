# -*- coding: utf-8 -*-
"""Check the issuance / use event catalogue (#2): row columns, seed-list closure, the subject-state matrix and the
counts written in sources.md.

  python tools/catalog_check.py [--catalog DIR] [--format table|json]

Input (default templates/catalog):
  issue_events.yaml          issuance events I01..  (rows under `events`)
  use_events.yaml            use events U01..       (rows under `events`)
  token_kinds.yaml           token kinds            (rows under `kinds`)
  seeds.yaml                 the seed lists          (lists under `seed_lists`, items under `items`)
  subject_state_matrix.md    subject state x token kind / session layer
  sources.md                 the seed lists for people, with the 対象外 count and ratio at the top

Checks (each failure is an error; `hook_invoked: unknown` and guide gaps are reported, not failed):
  COLUMNS   every event row has the columns of the catalogue (see REQUIRED_* below), valid enums, dates with
            review_by after verified_on, an owner `#NN`, versioned standard refs (a draft name ends in -NN), and an
            `idp` block for every catalogue IdP (keycloak, auth0) with occurs / hook_invoked; issuance rows also
            carry lifetime_impact with issued / recomputed / revoked lists of token kinds or session layers
  KINDS     tokens_issued / tokens_used / lifetime_impact name token kinds of token_kinds.yaml; every `kind` of the
            registry schema (templates/registry/token_types.schema.json) is a token kind
  GUIDE     guide.status is covered / partial / gap; covered and partial name existing slide IDs; gap carries the
            marker 「ガイドの空白」 and how the slides were checked
  CLOSURE   every seed item is referenced by a row (seeds, or claims_produced for the IANA JWT claims) or is
            対象外 with assumption and breaks_when (>= MIN_REASON characters, different from each other); no item is
            both; every reference names an existing item; every row references at least one seed item
  MATRIX    every subject state of the seed list has a section in subject_state_matrix.md with one row per layer,
            a result in RESULTS and a non-empty basis
  SOURCES   sources.md names every seed list and states the 対象外 count / total / ratio computed here

The closure function (closure()) is importable so that claim_lint's R3 (#17) can reuse it.
Exit status: 1 when there is at least one error, 0 otherwise.
"""
import argparse
import datetime
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
from claim_lint import core  # noqa: E402  (YAML loader that rejects duplicate keys and keeps dates as strings)

CATALOG = os.path.join(ROOT, 'templates', 'catalog')
IDPS = ('keycloak', 'auth0')
HOOK = ('yes', 'no', 'conditional', 'unknown')
OCCURS = ('yes', 'no', 'conditional', 'unknown')
ISSUERS = ('idp', 'gateway', 'tts', 'client', 'workload-platform', 'rp', 'resource-server', 'external-as')
PHASES = ('伝搬', '検証', '認可', '運用')
GUIDE_STATUS = ('covered', 'partial', 'gap')
GAP_MARK = 'ガイドの空白'
STOP_SCOPES = ('client', 'realm', 'tenant', 'api', 'server')
RESULTS = ('発行', '再計算', '失効', '影響なし')
LAYERS = ('AT', 'RT', 'ID', '内部トークン', 'Logout Token', 'IdP のセッション', 'RP・BFF のセッション')
SESSION_LAYERS = ('session_idp', 'session_rp')
MIN_REASON = 10  # same as claim_lint R2 (author-proposal, tracking #16)
STAGE_RE = re.compile(r'^[①②③④⑤⑥]+$')
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
REQUIRED_EVENT = ('id', 'name', 'standard_refs', 'seeds', 'guide', 'idp', 'verified_on', 'review_by', 'owner')
REQUIRED_ISSUE = ('issuer', 'stage', 'claims_produced', 'tokens_issued', 'lifetime_impact')
REQUIRED_USE = ('actor', 'phase', 'tokens_used', 'claims_read', 'lifetime_impact')
REQUIRED_KIND = ('id', 'name', 'format', 'typ', 'lifetime_hint', 'refs', 'seeds', 'guide', 'verified_on', 'review_by', 'owner')
FILES = {'issue_events': 'issue_events.yaml', 'use_events': 'use_events.yaml', 'token_kinds': 'token_kinds.yaml',
         'seeds': 'seeds.yaml'}
MD = {'matrix': 'subject_state_matrix.md', 'sources': 'sources.md'}
JWT_CLAIMS = 'iana-jwt-claims'
STATES = 'subject-states'


def err(check, target, message):
    return {'check': check, 'severity': 'error', 'target': target, 'message': message}


def note(check, target, message):
    return {'check': check, 'severity': 'info', 'target': target, 'message': message}


def _empty(v):
    return v is None or v == '' or v == [] or v == {}


def load(catalog_dir=CATALOG):
    docs, out = {}, []
    for k, name in FILES.items():
        p = os.path.join(catalog_dir, name)
        try:
            docs[k] = core.load_yaml(p) or {}
        except (OSError, Exception) as e:  # yaml errors and missing files
            out.append(err('LOAD', name, str(e).splitlines()[0]))
            docs[k] = {}
    for k, name in MD.items():
        p = os.path.join(catalog_dir, name)
        try:
            with open(p, encoding='utf-8') as f:
                docs[k] = f.read()
        except OSError as e:
            out.append(err('LOAD', name, str(e)))
            docs[k] = ''
    return docs, out


def known_slides(root=ROOT):
    with open(os.path.join(root, 'deck', 'slide_ids.json'), encoding='utf-8') as f:
        return {x['id'] for x in json.load(f)}


def registry_kinds(root=ROOT):
    with open(os.path.join(root, 'templates', 'registry', 'token_types.schema.json'), encoding='utf-8') as f:
        s = json.load(f)
    return set(s['$defs']['token_type']['properties']['kind']['enum']) if 'token_type' in s.get('$defs', {}) else \
        set(_find_kind_enum(s))


def _find_kind_enum(node):
    if isinstance(node, dict):
        k = node.get('kind')
        if isinstance(k, dict) and 'enum' in k and 'access_token' in k['enum']:
            return k['enum']
        for v in node.values():
            r = _find_kind_enum(v)
            if r:
                return r
    elif isinstance(node, list):
        for v in node:
            r = _find_kind_enum(v)
            if r:
                return r
    return []


# ------------------------------------------------------------------ seeds and closure
def seed_items(seeds_doc, dups=None):
    """{'<list>/<item>': item} and the list rows. Duplicate keys are appended to `dups` when given."""
    items, lists = {}, []
    for sl in (seeds_doc or {}).get('seed_lists', []) or []:
        lists.append(sl)
        for it in sl.get('items', []) or []:
            key = f"{sl['id']}/{it['id']}"
            if key in items and dups is not None:
                dups.append(key)
            items[key] = it
    return items, lists


def _weak_reason(v, label):
    """A 対象外 reason that is too short, one repeated character, or just the item label.
    Whether the reason is sound is not judged here (left to the sampled review of #13)."""
    t = str(v or '').strip()
    core_chars = set(t) - set(' \u3000、。・（）()')
    return len(t) < MIN_REASON or len(core_chars) <= 2 or t in {str(x) for x in label if x}


def row_refs(row, items):
    """Seed references of a row: explicit `seeds`, plus claims_produced / claims_read names of the IANA JWT claims."""
    refs = list(row.get('seeds') or [])
    for c in (row.get('claims_produced') or []) + (row.get('claims_read') or []):
        key = f'{JWT_CLAIMS}/{c}'
        if key in items:
            refs.append(key)
    return refs


def matrix_refs(matrix_md):
    return re.findall(r'種：`(' + re.escape(STATES) + r'/[a-z0-9-]+)`', matrix_md or '')


def closure(docs):
    """Seed-list closure. Returns (findings, stats). Usable by claim_lint R3 (#17)."""
    out = []
    dups = []
    items, lists = seed_items(docs.get('seeds'), dups)
    for key in dups:
        out.append(err('CLOSURE', key, '同じ一覧の中で項目の id が重複している'))
    for sl in lists:
        exp = (sl.get('expected') or {})
        n = len(sl.get('items') or [])
        if not isinstance(exp.get('count'), int) or _empty(exp.get('source')) or _empty(exp.get('verified_on')):
            out.append(err('CLOSURE', f"seeds.yaml:{sl.get('id')}", 'expected（count・source・verified_on）がない'))
        elif exp['count'] != n:
            out.append(err('CLOSURE', f"seeds.yaml:{sl.get('id')}", f"項目の数 {n} が出どころの件数 {exp['count']}（{exp['source']}）と合わない"))
    referenced = {}
    rows = [('issue_events', r) for r in (docs.get('issue_events') or {}).get('events', []) or []] + \
           [('use_events', r) for r in (docs.get('use_events') or {}).get('events', []) or []] + \
           [('token_kinds', r) for r in (docs.get('token_kinds') or {}).get('kinds', []) or []]
    for where, r in rows:
        rid = r.get('id', '?')
        refs = row_refs(r, items)
        if not refs:
            out.append(err('CLOSURE', f'{where}:{rid}', '種になる一覧のどの項目にもひもづいていない（seeds が空）'))
        for ref in refs:
            if ref not in items:
                out.append(err('CLOSURE', f'{where}:{rid}', f'種の項目 {ref} が seeds.yaml にない'))
            else:
                referenced.setdefault(ref, []).append(rid)
    for ref in matrix_refs(docs.get('matrix')):
        if ref not in items:
            out.append(err('CLOSURE', 'subject_state_matrix.md', f'種の項目 {ref} が seeds.yaml にない'))
        else:
            referenced.setdefault(ref, []).append('matrix')
    oos = 0
    for key, it in items.items():
        o = it.get('out_of_scope')
        if o:
            oos += 1
            for k in ('assumption', 'breaks_when'):
                v = (o or {}).get(k)
                if _empty(v) or _weak_reason(v, (it.get('id'), it.get('value'), it.get('note'))):
                    out.append(err('CLOSURE', key, f'対象外の {k} がない、{MIN_REASON} 字未満、同じ文字の繰り返し、または項目の名前そのもの'))
            if not _empty(o.get('assumption')) and o.get('assumption') == o.get('breaks_when'):
                out.append(err('CLOSURE', key, '対象外の assumption と breaks_when が同じ文'))
            if key in referenced:
                out.append(err('CLOSURE', key, f"対象外なのに行から参照されている（{', '.join(referenced[key])}）"))
        elif key not in referenced:
            out.append(err('CLOSURE', key, 'カタログのどの行にもひもづかず、対象外でもない（差集合に残る）'))
    total = len(items)
    reasons = {(o.get('assumption'), o.get('breaks_when')) for o in (it.get('out_of_scope') for it in items.values()) if o}
    stats = {'seed_lists': len(lists), 'seed_items': total, 'out_of_scope': oos, 'out_of_scope_reason_texts': len(reasons),
             'out_of_scope_ratio': round(oos / total, 4) if total else 0.0,
             'unmapped': sum(1 for f in out if f['message'].startswith('カタログのどの行にもひもづかず'))}
    return out, stats


# ------------------------------------------------------------------ rows
def _check_dates(where, r, out):
    v, b = r.get('verified_on'), r.get('review_by')
    if not (isinstance(v, str) and DATE_RE.match(v)) or not (isinstance(b, str) and DATE_RE.match(b)):
        out.append(err('COLUMNS', where, 'verified_on と review_by は YYYY-MM-DD'))
        return
    if datetime.date.fromisoformat(b) <= datetime.date.fromisoformat(v):
        out.append(err('COLUMNS', where, 'review_by が verified_on より後でない'))


def _check_refs(where, refs, out, slides):
    for ref in refs or []:
        if not isinstance(ref, dict) or _empty(ref.get('kind')) or _empty(ref.get('id')):
            out.append(err('COLUMNS', where, f'根拠の書式（kind と id）が不正：{ref!r}'))
            continue
        rid = str(ref['id'])
        if ref['kind'] == 'spec' and re.search(r'\bdraft-', rid) and not re.search(r'draft-[a-z0-9-]+-\d{2}\b', rid):
            out.append(err('COLUMNS', where, f'草案の根拠に版がない：{rid}'))
        if ref['kind'] == 'guide-slide' and rid not in slides:
            out.append(err('GUIDE', where, f'guide-slide の ID {rid} がスライドにない'))
        if ref['kind'] == 'author-proposal' and _empty(ref.get('tracking')):
            out.append(err('COLUMNS', where, 'author-proposal に tracking がない'))
        if ref['kind'] in ('spec', 'research') and re.search(r'Keycloak|Auth0|Okta|Entra|Cognito', rid) \
                and _empty(ref.get('verified_on')):
            out.append(err('COLUMNS', where, f'製品の文書の根拠に verified_on がない：{rid}'))


def _check_guide(where, g, out, slides):
    if not isinstance(g, dict) or g.get('status') not in GUIDE_STATUS:
        out.append(err('GUIDE', where, f'guide.status は {"/".join(GUIDE_STATUS)}'))
        return
    for s in g.get('slides') or []:
        if s not in slides:
            out.append(err('GUIDE', where, f'スライド ID {s} がない'))
    if g['status'] in ('covered', 'partial') and _empty(g.get('slides')):
        out.append(err('GUIDE', where, f"guide.status {g['status']} にスライド ID がない"))
    if g['status'] in ('partial', 'gap') and _empty(g.get('note')):
        out.append(err('GUIDE', where, f"guide.status {g['status']} に note（扱っていない点）がない"))
    if g['status'] == 'gap':
        if g.get('marker') != GAP_MARK:
            out.append(err('GUIDE', where, f'ガイドにない行に marker「{GAP_MARK}」がない'))
        if _empty(g.get('checked')):
            out.append(err('GUIDE', where, 'ガイドにない行に、どう確かめたか（checked）がない'))


def _kind_list(v):
    return v if isinstance(v, list) else []


def check_rows(docs, slides, reg_kinds):
    out, info = [], []
    kinds = {k.get('id') for k in (docs.get('token_kinds') or {}).get('kinds', []) or []}
    layer_ids = kinds | set(SESSION_LAYERS)
    for k in sorted(reg_kinds - kinds):
        out.append(err('KINDS', 'token_kinds.yaml', f'台帳のスキーマの kind {k} が token_kinds にない'))
    seen = set()
    for kind_name, req, pat in (('issue_events', REQUIRED_ISSUE, r'^I\d{2}$'), ('use_events', REQUIRED_USE, r'^U\d{2}$')):
        for r in (docs.get(kind_name) or {}).get('events', []) or []:
            rid = r.get('id', '?')
            where = f'{kind_name}:{rid}'
            if not re.match(pat, str(rid)):
                out.append(err('COLUMNS', where, f'id の形が {pat} でない'))
            if rid in seen:
                out.append(err('COLUMNS', where, 'id が重複している'))
            seen.add(rid)
            for k in REQUIRED_EVENT + req:
                if k not in r or (k not in ('standard_refs', 'claims_produced', 'claims_read', 'tokens_used') and _empty(r.get(k))):
                    out.append(err('COLUMNS', where, f'必須の列 {k} がない'))
            if kind_name == 'issue_events' and r.get('issuer') not in ISSUERS:
                out.append(err('COLUMNS', where, f"issuer は {'/'.join(ISSUERS)}（あるのは {r.get('issuer')!r}）"))
            if kind_name == 'issue_events' and not STAGE_RE.match(str(r.get('stage', ''))):
                out.append(err('COLUMNS', where, 'stage は ①〜⑥ の組み合わせ'))
            if kind_name == 'use_events' and r.get('phase') not in PHASES:
                out.append(err('COLUMNS', where, f"phase は {'/'.join(PHASES)}"))
            if _empty(r.get('standard_refs')) and _empty(r.get('standard_refs_none')):
                out.append(err('COLUMNS', where, '標準の根拠がない。無いときは standard_refs_none に理由を書く'))
            if not re.match(r'^#\d+$', str(r.get('owner', ''))):
                out.append(err('COLUMNS', where, 'owner は #NN'))
            _check_dates(where, r, out)
            _check_refs(where, r.get('standard_refs'), out, slides)
            _check_guide(where, r.get('guide'), out, slides)
            if (r.get('guide') or {}).get('status') == 'gap':
                info.append(note('GUIDE', where, f"{GAP_MARK}：{r.get('name')}"))
            for t in _kind_list(r.get('tokens_issued')) + _kind_list(r.get('tokens_used')):
                if t not in layer_ids:
                    out.append(err('KINDS', where, f'トークン種別 {t} が token_kinds にない'))
            li = r.get('lifetime_impact')
            if not isinstance(li, dict) or not all(k in li for k in ('issued', 'recomputed', 'revoked')) or _empty(li.get('note')):
                out.append(err('COLUMNS', where, 'lifetime_impact に issued・recomputed・revoked（空なら []）と note が要る'))
            else:
                for k in ('issued', 'recomputed', 'revoked'):
                    for t in _kind_list(li.get(k)):
                        if t not in layer_ids:
                            out.append(err('KINDS', where, f'lifetime_impact.{k} の {t} が token_kinds にもセッション層にもない'))
            idp = r.get('idp') or {}
            for name in IDPS:
                b = idp.get(name)
                w = f'{where}:{name}'
                if not isinstance(b, dict):
                    out.append(err('COLUMNS', w, f'idp.{name} がない'))
                    continue
                if b.get('occurs') not in OCCURS:
                    out.append(err('COLUMNS', w, f"occurs は {'/'.join(OCCURS)}"))
                if b.get('occurs') == 'unknown' and b.get('hook_invoked') != 'unknown':
                    out.append(err('COLUMNS', w, 'occurs が unknown なら hook_invoked も unknown'))
                if b.get('hook_invoked') not in HOOK:
                    out.append(err('COLUMNS', w, f"hook_invoked は {'/'.join(HOOK[:3])}（確かめていなければ unknown）"))
                elif b['hook_invoked'] in ('conditional', 'unknown') and _empty(b.get('hook_note')):
                    out.append(err('COLUMNS', w, f"hook_invoked {b['hook_invoked']} に hook_note がない"))
                elif b['hook_invoked'] == 'yes' and '推論' in str(b.get('hook_note') or ''):
                    out.append(err('COLUMNS', w, 'hook_note が推論なのに hook_invoked が yes（確かめていなければ unknown）'))
                elif b['hook_invoked'] == 'unknown':
                    info.append(note('COLUMNS', w, 'hook_invoked unknown（確かめていない）'))
                _check_refs(w, b.get('source_refs'), out, slides)
                ss = b.get('stop_setting')
                if ss is not None:
                    if not isinstance(ss, dict) or _empty(ss.get('setting')) or ss.get('scope') not in STOP_SCOPES \
                            or _empty(ss.get('default')):
                        out.append(err('COLUMNS', w, f"stop_setting は setting・scope（{'/'.join(STOP_SCOPES)}）・default を持つ"))
                if b.get('occurs') in ('yes', 'conditional') and r.get('issuer') == 'idp' and _empty(b.get('source_refs')) and _empty(b.get('evidence')):
                    out.append(err('COLUMNS', w, 'IdP が起こすイベントに、IdP 側の出どころ（source_refs か evidence）がない'))
    issuing = {}
    for r in (docs.get('issue_events') or {}).get('events', []) or []:
        for t in _kind_list(r.get('tokens_issued')):
            issuing.setdefault('session' if t in SESSION_LAYERS else t, set()).add(r.get('id'))
    for k in (docs.get('token_kinds') or {}).get('kinds', []) or []:
        where = f"token_kinds:{k.get('id', '?')}"
        want, have = issuing.get(k.get('id'), set()), set(k.get('issued_by') or [])
        if want != have:
            out.append(err('KINDS', where, f"issued_by が発行イベントの tokens_issued と合わない（足りない {sorted(want - have)}、余分 {sorted(have - want)}）"))
        for c in REQUIRED_KIND:
            if c not in k or (c != 'typ' and _empty(k.get(c))):
                out.append(err('COLUMNS', where, f'必須の列 {c} がない'))
        if k.get('format') not in ('jwt', 'opaque', 'jwt-or-opaque', 'not-a-token'):
            out.append(err('COLUMNS', where, 'format は jwt / opaque / jwt-or-opaque / not-a-token'))
        typ = k.get('typ')
        if not isinstance(typ, dict) or 'value' not in typ or _empty(typ.get('basis')):
            out.append(err('COLUMNS', where, 'typ は value（無ければ null）と basis を持つ'))
        _check_dates(where, k, out)
        _check_refs(where, k.get('refs'), out, slides)
        _check_guide(where, k.get('guide'), out, slides)
    return out, info


# ------------------------------------------------------------------ matrix
def parse_matrix(md):
    """{state_seed: {'section': title, 'rows': {layer: (result, basis)}}}."""
    states = {}
    cur = None
    for line in (md or '').splitlines():
        m = re.match(r'^##\s+(.+?)\s*$', line)
        if m:
            s = re.search(r'種：`(' + re.escape(STATES) + r'/[a-z0-9-]+)`', line)
            cur = s.group(1) if s else None
            if cur:
                states[cur] = {'section': m.group(1), 'rows': {}}
            continue
        if cur and line.startswith('|'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) >= 3 and cells[0] in LAYERS:
                states[cur]['rows'][cells[0]] = (cells[1], cells[2])
    return states


def check_matrix(docs):
    out = []
    items, _ = seed_items(docs.get('seeds'))
    want = sorted(k for k in items if k.startswith(STATES + '/'))
    states = parse_matrix(docs.get('matrix'))
    cells = 0
    for s in want:
        if s not in states:
            out.append(err('MATRIX', s, '行列に、この主体の状態の節がない'))
            continue
        rows = states[s]['rows']
        for layer in LAYERS:
            if layer not in rows:
                out.append(err('MATRIX', f'{s}:{layer}', 'セルがない'))
                continue
            res, basis = rows[layer]
            head = res.split('（')[0].split('・')
            if not head or any(h not in RESULTS for h in head):
                out.append(err('MATRIX', f'{s}:{layer}', f"結果は {'・'.join(RESULTS)} のどれか（あるのは {res!r}）"))
            if _empty(basis) or basis in ('—', '-'):
                out.append(err('MATRIX', f'{s}:{layer}', '根拠がない'))
            cells += 1
    return out, {'matrix_states': len(states), 'matrix_cells': cells}


# ------------------------------------------------------------------ sources.md
def check_sources(docs, stats):
    out = []
    md = re.sub(r'(?s)<!--.*?-->', '', docs.get('sources') or '')
    head = md.split('\n## ', 1)[0]
    _, lists = seed_items(docs.get('seeds'))
    table = {}
    for line in md.splitlines():
        m = re.match(r'^\|\s*`([a-z0-9-]+)`\s*\|.*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*$', line)
        if m:
            table[m.group(1)] = (int(m.group(2)), int(m.group(3)))
    for sl in lists:
        n = len(sl.get('items') or [])
        o = sum(1 for i in sl.get('items') or [] if i.get('out_of_scope'))
        if sl['id'] not in table:
            out.append(err('SOURCES', 'sources.md', f"種の一覧 {sl['id']} が sources.md の表にない"))
        elif table[sl['id']] != (n, o):
            out.append(err('SOURCES', 'sources.md', f"表の {sl['id']} の項目・対象外 {table[sl['id']]} が seeds.yaml の ({n}, {o}) と合わない"))
        for k in ('name', 'url', 'verified_on', 'review_by', 'owner'):
            if _empty(sl.get(k)):
                out.append(err('SOURCES', f"seeds.yaml:{sl['id']}", f'{k} がない'))
        if not _empty(sl.get('verified_on')):
            _check_dates(f"seeds.yaml:{sl['id']}", sl, out)
    pct = round(100 * stats['out_of_scope_ratio'])
    want = f"**対象外 {stats['out_of_scope']} 件／全 {stats['seed_items']} 件（{pct}%）**"
    if want not in head:
        out.append(err('SOURCES', 'sources.md', f'冒頭の件数が計算と合わない（計算：{want}）'))
    return out


# ------------------------------------------------------------------ driver
def run(catalog_dir=CATALOG, root=ROOT, docs=None):
    findings = []
    if docs is None:
        docs, findings = load(catalog_dir)
    slides = known_slides(root)
    f, info = check_rows(docs, slides, registry_kinds(root))
    findings += f
    c, stats = closure(docs)
    findings += c
    m, mstats = check_matrix(docs)
    findings += m
    stats.update(mstats)
    findings += check_sources(docs, stats)
    ie = (docs.get('issue_events') or {}).get('events', []) or []
    ue = (docs.get('use_events') or {}).get('events', []) or []
    stats.update({'issue_events': len(ie), 'use_events': len(ue),
                  'token_kinds': len((docs.get('token_kinds') or {}).get('kinds', []) or []),
                  'guide_gaps': sorted(r['id'] for r in ie + ue if (r.get('guide') or {}).get('status') == 'gap'),
                  'guide_partial': sorted(r['id'] for r in ie + ue if (r.get('guide') or {}).get('status') == 'partial'),
                  'hook_unknown': sorted(f"{r['id']}:{n}" for r in ie + ue for n in IDPS
                                         if ((r.get('idp') or {}).get(n) or {}).get('hook_invoked') == 'unknown')})
    errors = [x for x in findings if x['severity'] == 'error']
    return {'stats': stats, 'findings': findings + info, 'errors': len(errors)}


def format_table(res):
    s = res['stats']
    lines = [f"catalog_check  issue_events={s['issue_events']}  use_events={s['use_events']}  token_kinds={s['token_kinds']}  "
             f"matrix_cells={s['matrix_cells']}",
             f"seed lists={s['seed_lists']}  seed items={s['seed_items']}  対象外={s['out_of_scope']} "
             f"({100 * s['out_of_scope_ratio']:.1f}%)  unmapped={s['unmapped']}",
             f"guide gaps ({len(s['guide_gaps'])}): {' '.join(s['guide_gaps']) or '-'}",
             f"guide partial ({len(s['guide_partial'])}): {' '.join(s['guide_partial']) or '-'}",
             f"hook_invoked unknown ({len(s['hook_unknown'])}): {' '.join(s['hook_unknown']) or '-'}", '']
    for f in res['findings']:
        if f['severity'] == 'error':
            lines.append(f"{f['check']:<8} error  {f['target']}  {f['message']}")
    lines.append(f"errors {res['errors']}")
    lines.append('FAIL' if res['errors'] else 'OK')
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='catalog_check', description='Check the event catalogue and its seed-list closure (#2).')
    ap.add_argument('--catalog', default=CATALOG)
    ap.add_argument('--format', choices=('table', 'json'), default='table')
    a = ap.parse_args(argv)
    res = run(os.path.abspath(a.catalog))
    text = json.dumps(res, ensure_ascii=False, indent=1) if a.format == 'json' else format_table(res)
    sys.stdout.buffer.write((text + '\n').encode('utf-8'))
    return 1 if res['errors'] else 0


if __name__ == '__main__':
    sys.exit(main())
