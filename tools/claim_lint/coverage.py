# -*- coding: utf-8 -*-
"""Coverage rules of claim_lint (#17): R2 (substance and the Lite inheritance), R3, R3b, R4, R6, R9, R10.

The inputs are the design's catalog_answers.yaml (the sections below) and the catalogue of #2 (templates/catalog/).
Rules and severities are described in tools/claim_lint/RULES.md.

catalog_answers.yaml, sections read here (all top-level keys; `answers` is read by R2 in core.py too):
  idp                     {name, version, enumerable?, enumerable_source?, trigger_list?, trigger_list_source?}  R3, R3b, R2
                          or, for a design with several IdPs (#58), a list of such entries, each with token_types (the
                          token types of the inventory that this IdP issues) and optionally kind: self_built
  answers[].inherit       `idp-default` with `setting_checked` (Lite only)                         R2
  answers[].hook_checked  how the author confirmed the hook runs for this issuance                  R3b
  subject_states          {unused_layers: {layer: reason}, states: {state: {layer: {result, basis}}}}  R4
  pairwise                {subject_kinds: {kind: {answer, reason?}}, combinations: [...]}           R6
  outside_enumeration     {answer, respondent, date, searched: [...], found?: [...]}                R9, R3
"""
import datetime
import os
import re
import sys

ERROR, WARN, INFO = 'error', 'warn', 'info'
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

# R3: IdPs and whether they have an enumerable list of the occasions on which tokens are issued. The classification
# follows templates/catalog/sources.md (「契機の一覧を持つ IdP と、持たない IdP」):
#   list        a list exists. For an IdP of the catalogue (auth0, keycloak) the seed lists of seeds.yaml with
#               `idp: <name>` are checked against the catalogue (closure). Keycloak has no list of hook occasions, but its
#               token endpoint grants are enumerable (keycloak-grant-types: the OAuth2GrantType implementations).
#               For cognito (not in the catalogue, #21) the design maps the list itself (idp.trigger_list).
#   unverified  whether a list exists was not checked in the documentation (Entra V08, Okta V07)
#   none        the design declares that the IdP has no list (idp.enumerable: false, with idp.enumerable_source)
ENUMERABLE = {'auth0': 'list', 'keycloak': 'list', 'cognito': 'list', 'entra': 'unverified', 'okta': 'unverified'}
CATALOGUE_IDPS = ('keycloak', 'auth0')  # the idp.<name> blocks of the catalogue rows (catalog_check.IDPS)

# R4: the layers of templates/catalog/subject_state_matrix.md and the token_types kind that each layer stands for.
# Both session layers are `session`; they are told apart by stored_at (idp: the IdP's session, otherwise RP / BFF).
LAYER_KIND = {'AT': 'access_token', 'RT': 'refresh_token', 'ID': 'id_token', '内部トークン': 'internal_token',
              'Logout Token': 'logout_token', 'IdP のセッション': 'session', 'RP・BFF のセッション': 'session'}
SESSION_LAYER = {'IdP のセッション': lambda st: st == 'idp', 'RP・BFF のセッション': lambda st: st not in (None, 'idp')}

# R6: the subject kinds of slide:p05-three-principals (agents are workloads there; operators and batch jobs are
# システム・基盤). Pairwise over subject kind x issue event x stage is an author-proposal (tracking #17).
SUBJECT_KINDS = ('利用者', 'ワークロード', 'システム')

# R9: answers that say nothing but "none" (compared after removing brackets, punctuation and spaces, lower case;
# any concatenation of these words is still "none", e.g. 「なし。なし。」「特に見つからなかった」「None found.」)
NONE_WORDS = ('ありませんでした', '見つかりませんでした', '見つからなかった', '見当たりませんでした', '見当たらなかった', '見当たらない',
              '見つからない', 'ありません', '該当なし', '特に', 'なし', 'ない', '無し', '無い', 'なかった', 'nothingfound', 'nonefound',
              'notfound', 'nothing', 'none', 'nil', 'na', 'no', '-', '—', 'ー')
_NONE_RE = re.compile('(?:' + '|'.join(re.escape(w) for w in sorted(NONE_WORDS, key=len, reverse=True)) + ')+')
# placeholders that are not an answer (R2, R4, R6, R9: weak())
PLACEHOLDER_RE = re.compile(r'(?i)(?<![a-z])(?:todo|tbd|tbc|fixme|xxx+|wip)(?![a-z])|未定|未記入|要記入|あとで書|後で書|後ほど記入')
# R9 / R3: a concrete source among `searched`: a URL, a file path, or a document title of this length or more
CONCRETE_TITLE = 15

INHERIT = 'idp-default'


def F(rule, severity, target, message):
    from .core import Finding
    return Finding(rule, severity, target, message)


def _empty(v):
    return v is None or v == '' or v == [] or v == {}


def _cc():
    """tools/catalog_check.py (imported late: it imports claim_lint.core itself)."""
    tools = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import catalog_check
    return catalog_check


def weak(v, label=()):
    """A reason that is too short, one repeated character, the label itself (catalog_check._weak_reason), or a
    placeholder (TODO, TBD, xxx, 未定 ...). Whether the reason is sound is left to the sampled review (#13)."""
    return _empty(v) or _cc()._weak_reason(v, label) or bool(PLACEHOLDER_RE.search(str(v)))


def none_only(v):
    """The answer says only "none" (in any of NONE_WORDS), with nothing about what was searched or found."""
    t = re.sub(r'（[^）]*）|\([^)]*\)|「[^」]*」', '', str(v or '')).lower()
    t = re.sub(r'[\s。、．.,，!！?？:：;；/・]', '', t)
    return t == '' or bool(_NONE_RE.fullmatch(t))


def concrete(v):
    """A searched item that names a concrete source: a URL, a file path, or a document title (>= CONCRETE_TITLE)."""
    t = str(v or '').strip()
    if weak(t):
        return False
    return bool(re.search(r'https?://', t) or re.search(r'[\w.-]+/[\w./-]+', t)
                or re.search(r'\.(?:md|ya?ml|json|html?|pdf)\b', t) or len(t) >= CONCRETE_TITLE)


def parse_date(v):
    if isinstance(v, datetime.date):
        return v
    try:
        return datetime.date.fromisoformat(str(v or '').strip())
    except ValueError:
        return None


SELF_BUILT = 'self_built'  # idp[].kind: an issuer the organization builds itself (not a product; #58)


def idp_entries(answers_doc):
    """The IdPs of the design (#58): `idp` is one mapping (or, in old designs, a name) or a list of mappings.
    Returns (entries, problems, is_list). An entry is {name, block, token_types (set, or None = every token type), kind,
    target}; target is `idp` for the single form (as before #58) and `idp[<name>]` for the list form."""
    raw = (answers_doc or {}).get('idp')
    is_list = isinstance(raw, list)
    items = raw if is_list else ([raw] if raw is not None else [])
    entries, problems, seen = [], [], set()
    for i, it in enumerate(items):
        block = it if isinstance(it, dict) else {}
        name = str((block.get('name') if isinstance(it, dict) else it) or '').strip().lower() or None
        if not name:
            if is_list:
                problems.append((f'idp[{i}]', 'idp の要素に name がない'))
            continue
        if name in seen:
            problems.append((f'idp[{name}]', f'idp に {name} が 2 回ある（IdP ごとに 1 つの要素にまとめる）'))
            continue
        seen.add(name)
        tts = block.get('token_types')
        if tts is not None and (not isinstance(tts, list) or not all(isinstance(t, str) for t in tts)):
            problems.append((f'idp[{name}]', 'token_types はトークン目録の ID の配列で書く'))
            tts = None
        entries.append({'name': name, 'block': block, 'token_types': set(tts) if tts else None,
                        'kind': block.get('kind'), 'target': f'idp[{name}]' if is_list else 'idp'})
    return entries, problems, is_list


def idp_token_types(answers_doc, name):
    """Token types that the IdP `name` issues, or None when the design does not say (one IdP for every token type, or the
    IdP is not declared)."""
    for e in idp_entries(answers_doc)[0]:
        if e['name'] == name:
            return e['token_types']
    return None


def idp_name(answers_doc):
    """The design's IdP; with several IdPs (#58), the first one."""
    entries = idp_entries(answers_doc)[0]
    return entries[0]['name'] if entries else None


def _events(catalog):
    return {e['id']: e for e in catalog}


def _answers(answers_doc):
    return {a.get('event'): a for a in (answers_doc or {}).get('answers', []) or [] if isinstance(a, dict)}


# ------------------------------------------------------------------ R2: the Lite inheritance of 対象外
def _setting_words(setting):
    """Words of a stop_setting.setting that setting_checked must name (ASCII words of 6+ letters, e.g. Direct, Grants)."""
    return {w.lower() for w in re.findall(r'[A-Za-z][A-Za-z0-9-]{5,}', str(setting or ''))}


def r2_inherit(a, event, idp, profile, sev, idp_count=1):
    """An answer `inherit: idp-default`. Lite only, and only for an event that the catalogue marks with
    `idp.<IdP>.lite_inherit: true` (#4 revised Lite, gate1.md section 10: Keycloak I03 I04 I05 I07), with a
    「設定を確かめた」 field (setting_checked) that names the stop_setting."""
    eid = a.get('event')
    out = []
    if profile != 'lite':
        return [F('R2', sev, eid, '既定の回答の引き継ぎ（inherit）は Lite だけ。Full では assumption と breaks_when を書く')]
    if a.get('answer') != '対象外':
        return [F('R2', sev, eid, '引き継げるのは「対象外」の回答だけ')]
    if idp_count > 1:
        return [F('R2', sev, eid, f'IdP が {idp_count} つある設計では、既定の回答を引き継げない（止める設定が IdP ごとに違う。#58）。'
                                  'assumption と breaks_when を書く')]
    block = ((event or {}).get('idp') or {}).get(idp or '') if idp in CATALOGUE_IDPS else None
    ss = (block or {}).get('stop_setting') or {}
    if not idp:
        out.append(F('R2', sev, eid, '引き継ぐには idp（設計書の IdP）を宣言する'))
    elif block is None:
        out.append(F('R2', sev, eid, f'IdP {idp} はカタログの IdP でない（{"・".join(CATALOGUE_IDPS)}）ので、既定の回答を引き継げない'))
    elif block.get('lite_inherit') is not True:
        out.append(F('R2', sev, eid, f'このイベントは {idp} の既定の回答を引き継げない（カタログに lite_inherit の印がない。#4 の改訂：'
                                     '指摘が出た行・レルムやクライアントの既定に依存する行・利用イベントは手で書く）。assumption と breaks_when を書く'))
    sc = a.get('setting_checked')
    words = _setting_words(ss.get('setting'))
    if weak(sc, (eid,)):
        out.append(F('R2', sev, eid, '引き継ぐ回答に「設定を確かめた」（setting_checked：どの設定を、どこで、いつ確かめたか）がない、または短い'))
    elif words and not any(w in str(sc).lower() for w in words):
        out.append(F('R2', sev, eid, f"setting_checked に、止める設定（{ss.get('setting')}）の名前がない"))
    return out


# ------------------------------------------------------------------ R3
def _idp_searched(doc, idp):
    """The R9 searched items that name the IdP and a concrete source."""
    r9 = doc.get('outside_enumeration') or {}
    return [x for x in (r9.get('searched') or []) if idp in str(x).lower() and concrete(x)]


KNOWN_KINDS = (None, 'product', SELF_BUILT)


def rule_r3(answers_doc, catalog_dir, token_types=None):
    """R3 for every IdP of the design (#58: `idp` may be a list). token_types (the inventory) is given by core.run so that
    the token types an IdP entry names can be checked."""
    doc = answers_doc or {}
    entries, problems, is_list = idp_entries(doc)
    out = [F('R3', ERROR, t, m) for t, m in problems]
    if not entries:
        return out + [F('R3', ERROR, 'idp', 'catalog_answers.yaml に idp（設計書の IdP の name と version）がない')]
    known = {t.get('id') for t in token_types or []}
    if is_list and token_types is not None:
        out += _r3_token_type_owners(entries, token_types)
    for e in entries:
        if token_types is not None:
            for t in sorted((e['token_types'] or set()) - known):
                out.append(F('R3', ERROR, e['target'], f"IdP {e['name']} の token_types の {t} がトークン目録（token_types.yaml）にない"))
        if e['kind'] not in KNOWN_KINDS:
            out.append(F('R3', ERROR, e['target'], f"IdP {e['name']} の kind は product（製品。既定）か {SELF_BUILT}（組織が自分で作る発行者）"))
            continue
        out += (_r3_self_built if e['kind'] == SELF_BUILT else _r3_one)(doc, e, catalog_dir)
    return out


IDP_KINDS = ('access_token', 'id_token')
PRODUCT_WORDS = tuple(ENUMERABLE) + ('azure', 'aad', 'pingfederate', 'pingone', 'onelogin')


def _r3_token_type_owners(entries, token_types):
    """The list form ties token types to IdPs, and R3b, L2, L27, L74 and drift look at a token type through the IdP that
    names it (PR #70 check B5, B1). So every adopted access token and ID token type belongs to an entry, every entry of a
    list names its token types, and an access token type belongs to one entry."""
    out = []
    multi = len(entries) > 1
    unscoped = [e['name'] for e in entries if e['token_types'] is None]
    if multi and unscoped:
        out.append(F('R3', ERROR, 'idp', f"IdP が複数あるのに、{'・'.join(unscoped)} に token_types がない。IdP ごとに、出すトークン種別を書く"
                                         '（書かない IdP は全種別を出すものとして読まれ、ほかの IdP の検査と重なる）'))
    adopted = [t for t in token_types if t.get('decision') in ('採用', '既定どおり') and t.get('kind') in IDP_KINDS]
    for t in adopted:
        owners = [e['name'] for e in entries if e['token_types'] is not None and t.get('id') in e['token_types']]
        if not owners and not unscoped:
            out.append(F('R3', ERROR, 'idp', f"採用した種別 {t.get('id')}（{t.get('kind')}）が、どの IdP の token_types にもない。出す IdP の要素に書く"
                                             '（組織が自分で作る発行者なら kind: self_built の要素。書かないと R3b・L2・L27・L74・drift がこの種別を見ない）'))
        elif len(owners) > 1 and t.get('kind') == 'access_token':
            out.append(F('R3', WARN, 'idp', f"AT の種別 {t.get('id')} を {'・'.join(owners)} の token_types に書いている。AT は発行者ごとに検証の規則が違うので、"
                                            'IdP ごとに種別を分ける'))
    return out


def _r3_trigger_list(tl, catalog_dir):
    """Every item of a trigger list maps to catalogue events or is out of scope with a premise and a breaking condition."""
    out = []
    known = set(_load_event_ids(catalog_dir))
    for t in tl:
        tid = (t or {}).get('trigger', '?')
        evs, oos = t.get('events') or [], t.get('out_of_scope')
        if evs and oos:
            out.append(F('R3', ERROR, tid, 'events と out_of_scope の両方がある'))
        elif evs:
            for e in evs:
                if e not in known:
                    out.append(F('R3', ERROR, tid, f'イベント {e} がカタログにない'))
        elif isinstance(oos, dict):
            for k in ('assumption', 'breaks_when'):
                if weak(oos.get(k), (tid,)):
                    out.append(F('R3', ERROR, tid, f'対象外の {k} がない、または短い'))
        else:
            out.append(F('R3', ERROR, tid, 'カタログのイベントにひもづかず、対象外でもない（差集合に残る）'))
    return out


def _r3_self_built(doc, entry, catalog_dir):
    """An issuer the organization builds itself (an STS, a gateway that mints internal tokens; #58, pilot C): there is no
    product documentation to cite. The design enumerates the occasions on which its issuer mints tokens (trigger_list) and
    names the document that defines them (trigger_list_source.document: a path or a title; a url only if one exists)."""
    idp, block, target = entry['name'], entry['block'], entry['target']
    if idp in ENUMERABLE:
        return [F('R3', ERROR, target, f'{idp} は製品の IdP の名前。kind: {SELF_BUILT} は組織が自分で作る発行者にだけ書く')]
    tl = block.get('trigger_list')
    if _empty(tl):
        return [F('R3', ERROR, target, f'発行者 {idp} は組織が自分で作る（kind: {SELF_BUILT}）。発行の契機の一覧を決めるのは設計書なので、'
                                       'idp の trigger_list に、発行者が受ける grant・要求の全項目と、ひもづくイベント（events）か対象外'
                                       '（assumption・breaks_when）を書く')]
    out = []
    src = block.get('trigger_list_source')
    src = src if isinstance(src, dict) else {}
    ok_doc = not weak(src.get('document')) and concrete(src.get('document'))
    ok_url = not _empty(src.get('url'))
    if not (ok_doc or ok_url) or not DATE_RE.match(str(src.get('verified_on') or '')):
        out.append(F('R3', ERROR, target, f'発行者 {idp}（kind: {SELF_BUILT}）の trigger_list_source に、一覧を定める文書（document：設計書の'
                                          '節・仕様書のパスか名前。公開の URL があれば url）と、一覧を決めた・確かめた日（verified_on）がない'))
    out += _r3_trigger_list(tl, catalog_dir)
    like = [w for w in PRODUCT_WORDS if w in idp]
    if like:
        out.append(F('R3', WARN, target, f"発行者 {idp}（kind: {SELF_BUILT}）の名前が、製品の IdP（{'・'.join(like)}）を含む。製品を別の名前で {SELF_BUILT} と書くと、"
                                         'R3b（フックが呼ばれるか）と L2（書き換えを許さないクレーム）がその IdP を見なくなる。製品なら製品の名前で書く'))
    if not [f for f in out if f['severity'] == ERROR]:
        planned = '。まだ存在しない発行者（planned: true）なので、作った後に一覧を実装と突き合わせる' if src.get('planned') is True else ''
        out.append(F('R3', INFO, target, f'発行者 {idp} は組織が自分で作る（kind: {SELF_BUILT}）。契機の一覧 {len(tl)} 項目は設計書が決め、'
                                         f'すべてカタログのイベントか対象外にひもづく{planned}。R3b と L2 は、この発行者を照合しない'))
    return out


def _r3_one(doc, entry, catalog_dir):
    out = []
    idp, block, target = entry['name'], entry['block'], entry['target']
    kind = ENUMERABLE.get(idp)
    if kind is None:
        e = block.get('enumerable')
        if e is True:
            kind = 'list'
        elif e is False:
            kind = 'none'
            src = block.get('enumerable_source')
            if weak(src) or not concrete(src):
                out.append(F('R3', ERROR, target, f'IdP {idp} を「一覧が存在しない」とするなら、確かめた出どころ（idp.enumerable_source：'
                                                  '文書の URL か名前）を書く'))
        else:
            return [F('R3', ERROR, target, f'IdP {idp} の契機の一覧の有無が分からない。idp.enumerable（true／false）を宣言する')]
    if kind in ('unverified', 'none'):
        # R9 is required in any case (R9 checks it); here the search must have covered the IdP's own documentation
        if not _idp_searched(doc, idp):
            why = ('契機の一覧があるかを文書で確かめていない（文書で未確認。sources.md）' if kind == 'unverified'
                   else '契機の一覧を持たない（一覧が存在しない）')
            out.append(F('R3', ERROR, target, f'IdP {idp} は{why}。outside_enumeration（R9）の searched に、{idp} の文書（フック・発行の契機）'
                                              'を探したことを、文書の URL か名前で書く'))
        else:
            out.append(F('R3', INFO, target, f"IdP {idp} は{'文書で未確認' if kind == 'unverified' else '一覧が存在しない'}。"
                                             '列挙の外の契機は R9 の回答で探した'))
        return out
    if kind == 'list' and idp not in CATALOGUE_IDPS and idp not in ENUMERABLE and _empty(block.get('trigger_list')):
        return out + [F('R3', ERROR, target, f'IdP {idp} は一覧を持つと宣言したが、idp.trigger_list がない')]
    if idp in CATALOGUE_IDPS:
        cc = _cc()
        docs, load_err = cc.load(catalog_dir)
        lists = [sl['id'] for sl in (docs.get('seeds') or {}).get('seed_lists', []) or [] if sl.get('idp') == idp]
        if not lists:
            return [F('R3', ERROR, target, f'カタログの seeds.yaml に IdP {idp} の一覧（idp: {idp}）がない')]
        findings, _ = cc.closure(docs)
        mine = [f for f in findings if any(str(f['target']).startswith(f'{lid}/') or str(f['target']) == f'seeds.yaml:{lid}'
                                           for lid in lists)]
        for f in mine:
            out.append(F('R3', ERROR, f['target'], f"IdP {idp} の一覧とカタログの差集合：{f['message']}"))
        if not mine:
            out.append(F('R3', INFO, target, f"IdP {idp} の一覧（{'・'.join(lists)}）とカタログの差集合は 0 件"))
        return out
    # an IdP with a list that the catalogue does not carry (e.g. Cognito, #21): the design maps the list itself
    tl = block.get('trigger_list')
    if _empty(tl):
        return [F('R3', ERROR, target, f'IdP {idp} は契機の一覧を持つが、カタログにない（#21）。idp.trigger_list に一覧の全項目と、'
                                       'ひもづくイベント（events）か対象外（assumption・breaks_when）を書く')]
    src = block.get('trigger_list_source') or {}
    if not isinstance(src, dict) or _empty(src.get('url')) or not DATE_RE.match(str(src.get('verified_on') or '')):
        out.append(F('R3', ERROR, target, 'idp.trigger_list_source に一覧の出どころ（url）と確かめた日（verified_on）がない'))
    return out + _r3_trigger_list(tl, catalog_dir)


def _load_event_ids(catalog_dir):
    from .core import load_yaml
    ids = []
    for name in ('issue_events', 'use_events'):
        ids += [e['id'] for e in (load_yaml(os.path.join(catalog_dir, name + '.yaml')) or {}).get('events', [])]
    return ids


# ------------------------------------------------------------------ R3b
def custom_claims(claims, catalog_dir):
    """Adopted claims that the hook adds: a namespaced claim, or a name outside IANA JWT Claims whose usage is not
    protocol. A non-registered protocol claim without a namespace (Keycloak's payload `typ`) is written by the IdP
    itself, not by the hook, so it is left out (measured on scenario A: counting it was a false positive)."""
    from .core import load_yaml
    seeds = load_yaml(os.path.join(catalog_dir, 'seeds.yaml')) or {}
    iana = {it['id'] for sl in seeds.get('seed_lists', []) if sl.get('id') == 'iana-jwt-claims' for it in sl.get('items', [])}
    # #58: a top-level name that the IdP product defines (idp_defined; L1b checks the conditions) is written by the IdP
    # itself. A namespaced claim is the organization's whatever the row says, so idp_defined does not take it out of R3b
    return [c for c in claims if c.get('decision') in ('採用', '既定どおり')
            and (c.get('namespace') or (c.get('name') not in iana and c.get('usage') != 'protocol' and not c.get('idp_defined')))]


def _issued(a, event, token_types):
    """Token type IDs that the answer says the event issues; without token_types, those of the design whose kind is
    in the catalogue row's tokens_issued (session_idp / session_rp are `session`)."""
    if not _empty(a.get('token_types')):
        return set(a['token_types'])
    kinds = {'session' if k in ('session_idp', 'session_rp') else k for k in (event.get('tokens_issued') or [])}
    return {t.get('id') for t in token_types if t.get('kind') in kinds}


def rule_r3b(claims, answers_doc, catalog, catalog_dir, token_types=()):
    out = []
    events0 = _events(catalog)
    for eid, a in _answers(answers_doc).items():
        e = events0.get(eid)
        if e and str(eid).startswith('I') and a.get('answer') == '該当' and e.get('tokens_issued') and _empty(a.get('token_types')):
            out.append(F('R3b', ERROR, eid, '発行イベントの「該当」に token_types（出るトークン種別の ID）がない。R3b の照合に使う'))
    events = _events(catalog)
    answers = _answers(answers_doc)
    customs = custom_claims(claims, catalog_dir)
    if not customs:
        return out
    entries = idp_entries(answers_doc)[0] or [{'name': None, 'block': {}, 'token_types': None, 'kind': None, 'target': 'idp'}]
    for ent in entries:
        out += _r3b_one(ent, customs, events, answers, token_types)
    return out


def _r3b_one(ent, customs, events, answers, token_types):
    """R3b for one IdP. With several IdPs (#58) the entry names its token types: only the claims carried in them and the
    issuances that issue them are compared with this IdP's hook_invoked."""
    out = []
    idp, scope = ent['name'], ent['token_types']
    if ent['kind'] == SELF_BUILT:
        return out  # the organization's own issuer writes the claims itself: there is no hook whose invocation could be skipped
    if scope is not None:
        customs = [c for c in customs if scope & set(c.get('carried_in') or [])]
        if not customs:
            return out
    if idp not in CATALOGUE_IDPS:
        return [F('R3b', WARN, ent['target'], f"IdP {idp or '(未宣言)'} はカタログの IdP でないので、hook_invoked を照合できない。"
                                      '独自クレームを載せる発行ごとに、フックが呼ばれることを確かめて hook_checked に書く')]
    for eid, a in answers.items():
        e = events.get(eid)
        if not e or not str(eid).startswith('I') or a.get('answer') != '該当' or e.get('issuer') != 'idp':
            continue
        b = (e.get('idp') or {}).get(idp) or {}
        if b.get('occurs') == 'no':
            continue
        issued = _issued(a, e, token_types)
        if scope is not None:
            issued &= scope
            if not issued:
                continue  # this issuance does not produce a token of this IdP
        hit = [c['id'] for c in customs if (scope is None and eid in (c.get('issue_events') or []))
               or issued & set(c.get('carried_in') or [])]
        if not hit:
            continue
        hk = b.get('hook_invoked')
        names = '・'.join(hit)
        # #58: with several IdPs, what the author confirmed must be about this IdP: a mapping {IdP: text}, or a text that
        # names the IdP (a statement about Keycloak says nothing about Auth0)
        hc, multi = a.get('hook_checked'), ent['target'] != 'idp'
        if isinstance(hc, dict):
            hc = hc.get(idp)
        elif multi and idp not in str(hc or '').lower():
            hc = None
        if hk == 'no':
            out.append(F('R3b', ERROR, eid, f"{idp} ではこの発行で {b.get('hook_name')} が呼ばれない（hook_invoked: no）のに、"
                                            f"独自クレーム {names} を運ぶトークンが出る。クレームが欠けたまま出る"))
        elif hk in ('unknown', 'conditional'):
            if weak(hc, (eid,)):
                out.append(F('R3b', WARN, eid, f"{idp} のこの発行で {b.get('hook_name')} が呼ばれるかは {hk}（カタログ）。"
                                               f"独自クレーム {names} が載ることを確かめて hook_checked に書く"
                                               + (f'（IdP が複数なので、{idp} の名前を含む文か、IdP ごとの対応 {{{idp}: …}} で書く）' if multi else '')))
            else:
                out.append(F('R3b', INFO, eid, f"hook_invoked {hk}：書き手が確かめた（{hc}）"))
    return out


# ------------------------------------------------------------------ R4
def rule_r4(answers_doc, token_types, catalog_dir, profile):
    sev = WARN if profile == 'lite' else ERROR
    cc = _cc()
    from .core import load_yaml
    seeds = load_yaml(os.path.join(catalog_dir, 'seeds.yaml')) or {}
    items, _ = cc.seed_items(seeds)
    states = sorted(k for k in items if k.startswith(cc.STATES + '/'))
    sm = (answers_doc or {}).get('subject_states')
    if not isinstance(sm, dict):
        return [F('R4', sev, 'subject_states', f'主体の状態 × トークン・セッションの行列（subject_states）がない（{len(states)} 状態 × '
                                               f'{len(cc.LAYERS)} 層）')]
    out = []
    unused = sm.get('unused_layers') or {}
    adopted = [t for t in token_types if t.get('decision') in ('採用', '既定どおり')]
    for layer, reason in unused.items():
        if layer not in cc.LAYERS:
            out.append(F('R4', sev, f'unused_layers:{layer}', f"層は {'・'.join(cc.LAYERS)} のどれか"))
            continue
        if weak(reason, (layer,)):
            out.append(F('R4', sev, f'unused_layers:{layer}', '使わない層に理由がない、または短い'))
        kind = LAYER_KIND.get(layer)
        rows = [t for t in adopted if t.get('kind') == kind]
        if kind == 'session':
            unknown = [t['id'] for t in rows if not t.get('stored_at')]
            rows = [t for t in rows if t.get('stored_at') and SESSION_LAYER[layer](t.get('stored_at'))]
            if unknown and not rows:
                out.append(F('R4', WARN, f'unused_layers:{layer}', f"使わないとしたが、token_types に session の採用の行"
                                                                   f"（{'・'.join(unknown)}。stored_at が無く層を見分けられない）がある"))
        if rows:
            out.append(F('R4', sev, f'unused_layers:{layer}', f"使わないとしたが、token_types にこの層の採用の行"
                                                              f"（{'・'.join(t['id'] for t in rows)}）がある"))
    given = sm.get('states') or {}
    for s in given:
        if s not in states:
            out.append(F('R4', sev, str(s), f'カタログにない主体の状態（{"・".join(states)}）'))
    for s in states:
        cells = given.get(s)
        if not isinstance(cells, dict):
            out.append(F('R4', sev, s, '主体の状態の回答がない'))
            continue
        for layer in cc.LAYERS:
            if layer in unused:
                if layer in cells:
                    out.append(F('R4', sev, f'{s}:{layer}', '使わない層（unused_layers）にセルがある'))
                continue
            c = cells.get(layer)
            if not isinstance(c, dict):
                out.append(F('R4', sev, f'{s}:{layer}', 'セルがない（使わない層なら unused_layers に理由を書く）'))
                continue
            res = str(c.get('result') or '')
            if res not in cc.RESULTS:
                out.append(F('R4', sev, f'{s}:{layer}', f"結果は {'・'.join(cc.RESULTS)} のどれか（あるのは {res!r}）"))
            if weak(c.get('basis'), (layer, res)):
                what = '「影響なし」に根拠がない' if res == '影響なし' else '根拠がない'
                out.append(F('R4', sev, f'{s}:{layer}', f'{what}、または短い（basis）'))
        for layer in cells:
            if layer not in cc.LAYERS:
                out.append(F('R4', sev, f'{s}:{layer}', f"層は {'・'.join(cc.LAYERS)} のどれか"))
    return out


# ------------------------------------------------------------------ R6
def rule_r6(answers_doc, catalog):
    """Pairwise: every 2-factor pair of (subject kind present in the design) x (issue event answered 該当) x
    (stage of that event in the catalogue) appears in at least one considered combination. warn only."""
    doc = answers_doc or {}
    pw = doc.get('pairwise')
    if not isinstance(pw, dict):
        return [F('R6', WARN, 'pairwise', '主体の種類 × 発行イベント × 段階の組み合わせの検討（pairwise）がない')]
    out = []
    sk = pw.get('subject_kinds') or {}
    present = []
    for k in SUBJECT_KINDS:
        v = sk.get(k)
        if not isinstance(v, dict) or v.get('answer') not in ('該当', '対象外'):
            out.append(F('R6', WARN, f'subject_kinds:{k}', '主体の種類に「該当」か「対象外」の回答がない'))
        elif v['answer'] == '対象外' and weak(v.get('reason'), (k,)):
            out.append(F('R6', WARN, f'subject_kinds:{k}', '対象外の主体の種類に理由（reason）がない、または短い'))
        elif v['answer'] == '該当':
            present.append(k)
    for k in sk:
        if k not in SUBJECT_KINDS:
            out.append(F('R6', WARN, f'subject_kinds:{k}', f"主体の種類は {'・'.join(SUBJECT_KINDS)}（slide:p05-three-principals）"))
    events = _events(catalog)
    issue = [eid for eid, a in _answers(doc).items() if str(eid).startswith('I') and a.get('answer') == '該当' and eid in events]
    stages = {e: list(str(events[e].get('stage') or '')) for e in issue}
    need = set()
    for s in present:
        for e in issue:
            need.add(('S×E', s, e))
            for t in stages[e]:
                need.add(('S×T', s, t))
    for e in issue:
        for t in stages[e]:
            need.add(('E×T', e, t))
    have = set()
    for i, c in enumerate(pw.get('combinations') or []):
        s, e, t = (c or {}).get('subject'), (c or {}).get('event'), str((c or {}).get('stage') or '')
        where = f'combinations[{i}]'
        if s not in SUBJECT_KINDS or e not in events or t not in stages.get(e, list(str(events.get(e, {}).get('stage') or ''))):
            out.append(F('R6', WARN, where, f'組み合わせ ({s}, {e}, {t}) の主体・イベント・段階が不正（段階はカタログのそのイベントの stage）'))
            continue
        if weak(c.get('note'), (s, e, t)):
            out.append(F('R6', WARN, where, f'組み合わせ ({s}, {e}, {t}) に検討の記録（note）がない、または短い'))
            continue
        have |= {('S×E', s, e), ('S×T', s, t), ('E×T', e, t)}
    missing = sorted(need - have)
    for kind, x, y in missing:
        out.append(F('R6', WARN, f'{kind}:{x}×{y}', f'2 因子の組 ({x}, {y}) を含む組み合わせを検討していない'))
    if not missing:
        out.append(F('R6', INFO, 'pairwise', f'2 因子の組 {len(need)} 個をすべて検討した（主体 {len(present)}・発行イベント {len(issue)}）'))
    return out


# ------------------------------------------------------------------ R9
def rule_r9(answers_doc, today=None):
    today = today or datetime.date.today()
    r = (answers_doc or {}).get('outside_enumeration')
    t = 'outside_enumeration'
    if not isinstance(r, dict):
        return [F('R9', ERROR, t, '「この列挙の外に契機はないか」の回答（outside_enumeration）がない')]
    out = []
    ans = str(r.get('answer') or '').strip()
    if not ans:
        out.append(F('R9', ERROR, t, 'answer がない'))
    elif none_only(ans) or weak(ans):
        out.append(F('R9', ERROR, t, '回答が「なし」（見つかりませんでした・None found なども同じ）だけ、仮の値、または短い。'
                                     '何を探して、何が無かったか（見つかったか）を書く'))
    resp = str(r.get('respondent') or '').strip()
    if len(resp) < 2 or PLACEHOLDER_RE.search(resp) or len(set(resp)) <= 1:
        out.append(F('R9', ERROR, t, '回答者（respondent）がない、または仮の値'))
    d = parse_date(r.get('date'))
    if d is None:
        out.append(F('R9', ERROR, t, '日付（date、YYYY-MM-DD の実在の日）がない'))
    elif d > today + datetime.timedelta(days=1):
        out.append(F('R9', ERROR, t, f'日付（date）{d} が未来'))
    sr = r.get('searched')
    items = [x for x in sr if not _empty(x)] if isinstance(sr, list) else []
    if not items:
        out.append(F('R9', ERROR, t, '探した範囲（searched：見た資料・図の一覧）がない'))
    else:
        for i, x in enumerate(items):
            if weak(x):
                out.append(F('R9', ERROR, f'{t}.searched[{i}]', f'探した範囲の項目 {x!r} が短い、または仮の値'))
        if not any(concrete(x) for x in items):
            out.append(F('R9', ERROR, t, f'探した範囲に、具体的な出どころ（URL、ファイルのパス、{CONCRETE_TITLE} 字以上の文書の名前）がない'))
    for i, f in enumerate(r.get('found') or []):
        if not isinstance(f, dict) or _empty(f.get('name')) or weak(f.get('handled_as'), (f.get('name'),)):
            out.append(F('R9', ERROR, f'{t}.found[{i}]', '見つかった契機には name と扱い（handled_as：カタログに戻した・設計に足した など）を書く'))
    return out


# ------------------------------------------------------------------ R10
def rule_r10(catalog_dir, limits_path, token_types, today=None):
    """review_by of the sources (seed lists, catalogue rows, token kinds), the path limits, and limits declared
    inline in token_types (size.path) has passed. warn; one finding per file with the expired IDs."""
    from .core import load_yaml
    today = today or datetime.date.today()
    groups = {}

    missing = {}

    def check(where, rid, row, required=False):
        rb = (row or {}).get('review_by')
        d = parse_date(rb)
        if d is None:
            if required:
                missing.setdefault(where, []).append(str(rid))
        elif d < today:
            groups.setdefault(where, []).append(f'{rid}（{rb}）')

    seeds = load_yaml(os.path.join(catalog_dir, 'seeds.yaml')) or {}
    for sl in seeds.get('seed_lists', []) or []:
        check('seeds.yaml', sl.get('id'), sl)
    for name, key in (('issue_events', 'events'), ('use_events', 'events'), ('token_kinds', 'kinds')):
        for r in (load_yaml(os.path.join(catalog_dir, name + '.yaml')) or {}).get(key, []) or []:
            check(f'{name}.yaml', r.get('id'), r)
    for lim in (load_yaml(limits_path) or {}).get('limits', []) or []:
        check(os.path.basename(limits_path), lim.get('id'), lim, required=True)
    for t in token_types:
        for p in ((t.get('size') or {}).get('path') or []):
            if isinstance(p, dict):
                check(f"token_types {t.get('id')}", p.get('id'), p, required=True)
    out = [F('R10', WARN, where, f"見直しの期限（review_by、YYYY-MM-DD）が無い {len(ids)} 件：{'、'.join(ids)}。確かめた日"
                                 '（verified_on）と見直しの期限を書く') for where, ids in missing.items()]
    return out + [F('R10', WARN, where, f"見直しの期限（review_by）が過ぎている {len(ids)} 件：{'、'.join(ids)}。出どころを確かめ直し、"
                                  'verified_on と review_by を更新する') for where, ids in groups.items()]
