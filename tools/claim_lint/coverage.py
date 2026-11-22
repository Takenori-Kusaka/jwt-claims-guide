# -*- coding: utf-8 -*-
"""Coverage rules of claim_lint (#17): R2 (substance and the Lite inheritance), R3, R3b, R4, R6, R9, R10.

The inputs are the design's catalog_answers.yaml (the sections below) and the catalogue of #2 (templates/catalog/).
Rules and severities are described in tools/claim_lint/RULES.md.

catalog_answers.yaml, sections read here (all top-level keys; `answers` is read by R2 in core.py too):
  idp                     {name, version, enumerable?, trigger_list?, trigger_list_source?}         R3, R3b, R2 (Lite)
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

# R3: IdPs and whether they have an enumerable list of the occasions on which tokens are issued / hooks run.
# The classification follows templates/catalog/sources.md (「契機の一覧を持つ IdP と、持たない IdP」). For an IdP of the
# catalogue with a list (auth0), the seed lists of seeds.yaml that carry `idp: <name>` are its lists. keycloak-settings
# (idp: keycloak) is a list of settings picked by the author, not the IdP's own list of occasions, so Keycloak is 一覧なし.
ENUMERABLE = {'auth0': True, 'cognito': True, 'keycloak': False, 'entra': False, 'okta': False}
CATALOGUE_IDPS = ('keycloak', 'auth0')  # the idp.<name> blocks of the catalogue rows (catalog_check.IDPS)

# R4: the layers of templates/catalog/subject_state_matrix.md and the token_types kind that each layer stands for.
# The two session layers both map to `session`, so they are not cross-checked against token_types.
LAYER_KIND = {'AT': 'access_token', 'RT': 'refresh_token', 'ID': 'id_token', '内部トークン': 'internal_token',
              'Logout Token': 'logout_token', 'IdP のセッション': None, 'RP・BFF のセッション': None}

# R6: the subject kinds of slide:p05-three-principals (agents are workloads there; operators and batch jobs are
# システム・基盤). Pairwise over subject kind x issue event x stage is an author-proposal (tracking #17).
SUBJECT_KINDS = ('利用者', 'ワークロード', 'システム')

# R9: answers that say nothing but "none"
NONE_WORDS = {'なし', 'ない', '無し', '無い', '特になし', '特にない', 'ありません', 'none', 'no', 'n/a', 'na', '-', '—'}

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
    """A reason that is too short, one repeated character, or the label itself (catalog_check._weak_reason)."""
    return _empty(v) or _cc()._weak_reason(v, label)


def idp_name(answers_doc):
    idp = (answers_doc or {}).get('idp')
    if isinstance(idp, dict):
        return str(idp.get('name') or '').strip().lower() or None
    if isinstance(idp, str):
        return idp.strip().lower() or None
    return None


def _events(catalog):
    return {e['id']: e for e in catalog}


def _answers(answers_doc):
    return {a.get('event'): a for a in (answers_doc or {}).get('answers', []) or [] if isinstance(a, dict)}


# ------------------------------------------------------------------ R2: the Lite inheritance of 対象外
def r2_inherit(a, event, idp, profile, sev):
    """An answer `inherit: idp-default`. Lite only, and only for an event that one client setting stops (the
    stop_setting of the catalogue row for the design's IdP has scope client), with a 「設定を確かめた」 field."""
    eid = a.get('event')
    out = []
    if profile != 'lite':
        return [F('R2', sev, eid, '既定の回答の引き継ぎ（inherit）は Lite だけ。Full では assumption と breaks_when を書く')]
    if a.get('answer') != '対象外':
        return [F('R2', sev, eid, '引き継げるのは「対象外」の回答だけ')]
    block = ((event or {}).get('idp') or {}).get(idp or '') if idp in CATALOGUE_IDPS else None
    ss = (block or {}).get('stop_setting')
    if not idp:
        out.append(F('R2', sev, eid, '引き継ぐには idp（設計書の IdP）を宣言する'))
    elif block is None:
        out.append(F('R2', sev, eid, f'IdP {idp} はカタログの IdP でない（{"・".join(CATALOGUE_IDPS)}）ので、既定の回答を引き継げない'))
    elif not isinstance(ss, dict) or ss.get('scope') != 'client':
        out.append(F('R2', sev, eid, f"このイベントは {idp} のクライアントの設定 1 つでは止まらない"
                                     f"（stop_setting の scope が {(ss or {}).get('scope')!r}）。assumption と breaks_when を手で書く"))
    if weak(a.get('setting_checked'), (eid,)):
        out.append(F('R2', sev, eid, '引き継ぐ回答に「設定を確かめた」（setting_checked：どの設定を、どこで、いつ確かめたか）がない、または短い'))
    return out


# ------------------------------------------------------------------ R3
def rule_r3(answers_doc, catalog_dir):
    out = []
    doc = answers_doc or {}
    idp = idp_name(doc)
    block = doc.get('idp') if isinstance(doc.get('idp'), dict) else {}
    if not idp:
        return [F('R3', ERROR, 'idp', 'catalog_answers.yaml に idp（設計書の IdP の name と version）がない')]
    enumerable = ENUMERABLE.get(idp, block.get('enumerable'))
    if enumerable is None:
        return [F('R3', ERROR, 'idp', f'IdP {idp} の契機の一覧の有無が分からない。idp.enumerable（true／false）を宣言する')]
    if not enumerable:
        # 一覧なし: R9 is required (R9 checks it); here: the search must have covered the IdP's own documentation
        r9 = doc.get('outside_enumeration') or {}
        searched = ' '.join(str(s) for s in (r9.get('searched') or []) if s).lower()
        if idp not in searched:
            out.append(F('R3', ERROR, 'idp', f'IdP {idp} は契機の一覧を持たない（一覧なし）。outside_enumeration（R9）の searched に、'
                                             f'{idp} の文書（フック・発行の契機）を探したことを書く'))
        else:
            out.append(F('R3', INFO, 'idp', f'IdP {idp} は一覧なし。列挙の外の契機は R9 の回答で探した'))
        return out
    if idp in CATALOGUE_IDPS:
        cc = _cc()
        docs, load_err = cc.load(catalog_dir)
        lists = [sl['id'] for sl in (docs.get('seeds') or {}).get('seed_lists', []) or [] if sl.get('idp') == idp]
        if not lists:
            return [F('R3', ERROR, 'idp', f'カタログの seeds.yaml に IdP {idp} の一覧（idp: {idp}）がない')]
        findings, _ = cc.closure(docs)
        mine = [f for f in findings if any(str(f['target']).startswith(f'{lid}/') or str(f['target']) == f'seeds.yaml:{lid}'
                                           for lid in lists)]
        for f in mine:
            out.append(F('R3', ERROR, f['target'], f"IdP {idp} の一覧とカタログの差集合：{f['message']}"))
        if not mine:
            out.append(F('R3', INFO, 'idp', f"IdP {idp} の一覧（{'・'.join(lists)}）とカタログの差集合は 0 件"))
        return out
    # an IdP with a list that the catalogue does not carry (e.g. Cognito, #21): the design maps the list itself
    tl = block.get('trigger_list')
    if _empty(tl):
        return [F('R3', ERROR, 'idp', f'IdP {idp} は契機の一覧を持つが、カタログにない（#21）。idp.trigger_list に一覧の全項目と、'
                                      'ひもづくイベント（events）か対象外（assumption・breaks_when）を書く')]
    src = block.get('trigger_list_source') or {}
    if not isinstance(src, dict) or _empty(src.get('url')) or not DATE_RE.match(str(src.get('verified_on') or '')):
        out.append(F('R3', ERROR, 'idp', 'idp.trigger_list_source に一覧の出どころ（url）と確かめた日（verified_on）がない'))
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
    return [c for c in claims if c.get('decision') in ('採用', '既定どおり')
            and (c.get('namespace') or (c.get('name') not in iana and c.get('usage') != 'protocol'))]


def rule_r3b(claims, answers_doc, catalog, catalog_dir):
    out = []
    idp = idp_name(answers_doc)
    events = _events(catalog)
    answers = _answers(answers_doc)
    customs = custom_claims(claims, catalog_dir)
    if not customs:
        return out
    if idp not in CATALOGUE_IDPS:
        return [F('R3b', WARN, 'idp', f"IdP {idp or '(未宣言)'} はカタログの IdP でないので、hook_invoked を照合できない。"
                                      '独自クレームを載せる発行ごとに、フックが呼ばれることを確かめて hook_checked に書く')]
    for eid, a in answers.items():
        e = events.get(eid)
        if not e or not str(eid).startswith('I') or a.get('answer') != '該当' or e.get('issuer') != 'idp':
            continue
        b = (e.get('idp') or {}).get(idp) or {}
        if b.get('occurs') == 'no':
            continue
        issued = set(a.get('token_types') or [])
        hit = [c['id'] for c in customs if eid in (c.get('issue_events') or []) or issued & set(c.get('carried_in') or [])]
        if not hit:
            continue
        hk = b.get('hook_invoked')
        names = '・'.join(hit)
        if hk == 'no':
            out.append(F('R3b', ERROR, eid, f"{idp} ではこの発行で {b.get('hook_name')} が呼ばれない（hook_invoked: no）のに、"
                                            f"独自クレーム {names} を運ぶトークンが出る。クレームが欠けたまま出る"))
        elif hk in ('unknown', 'conditional'):
            if weak(a.get('hook_checked'), (eid,)):
                out.append(F('R3b', WARN, eid, f"{idp} のこの発行で {b.get('hook_name')} が呼ばれるかは {hk}（カタログ）。"
                                               f"独自クレーム {names} が載ることを確かめて hook_checked に書く"))
            else:
                out.append(F('R3b', INFO, eid, f"hook_invoked {hk}：書き手が確かめた（{a.get('hook_checked')}）"))
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
    adopted = {t.get('kind') for t in token_types if t.get('decision') in ('採用', '既定どおり')}
    for layer, reason in unused.items():
        if layer not in cc.LAYERS:
            out.append(F('R4', sev, f'unused_layers:{layer}', f"層は {'・'.join(cc.LAYERS)} のどれか"))
            continue
        if weak(reason, (layer,)):
            out.append(F('R4', sev, f'unused_layers:{layer}', '使わない層に理由がない、または短い'))
        if LAYER_KIND.get(layer) in adopted:
            out.append(F('R4', sev, f'unused_layers:{layer}', f'使わないとしたが、token_types に {LAYER_KIND[layer]} の採用の行がある'))
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
def rule_r9(answers_doc):
    r = (answers_doc or {}).get('outside_enumeration')
    t = 'outside_enumeration'
    if not isinstance(r, dict):
        return [F('R9', ERROR, t, '「この列挙の外に契機はないか」の回答（outside_enumeration）がない')]
    out = []
    ans = str(r.get('answer') or '').strip()
    bare = re.sub(r'[\s。、．.!！]', '', ans).lower()
    if not ans:
        out.append(F('R9', ERROR, t, 'answer がない'))
    elif bare in NONE_WORDS or weak(ans):
        out.append(F('R9', ERROR, t, '回答が「なし」だけ、または短い。何を探して、何が無かったか（見つかったか）を書く'))
    if len(str(r.get('respondent') or '').strip()) < 2:
        out.append(F('R9', ERROR, t, '回答者（respondent）がない'))
    d = str(r.get('date') or '')
    if not DATE_RE.match(d):
        out.append(F('R9', ERROR, t, '日付（date、YYYY-MM-DD）がない'))
    sr = r.get('searched')
    if not isinstance(sr, list) or not [s for s in sr if not _empty(s) and len(str(s).strip()) >= 4]:
        out.append(F('R9', ERROR, t, '探した範囲（searched：見た資料・図の一覧）がない'))
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

    def check(where, rid, row):
        rb = str((row or {}).get('review_by') or '')
        if DATE_RE.match(rb) and datetime.date.fromisoformat(rb) < today:
            groups.setdefault(where, []).append(f'{rid}（{rb}）')

    seeds = load_yaml(os.path.join(catalog_dir, 'seeds.yaml')) or {}
    for sl in seeds.get('seed_lists', []) or []:
        check('seeds.yaml', sl.get('id'), sl)
    for name, key in (('issue_events', 'events'), ('use_events', 'events'), ('token_kinds', 'kinds')):
        for r in (load_yaml(os.path.join(catalog_dir, name + '.yaml')) or {}).get(key, []) or []:
            check(f'{name}.yaml', r.get('id'), r)
    for lim in (load_yaml(limits_path) or {}).get('limits', []) or []:
        check(os.path.basename(limits_path), lim.get('id'), lim)
    for t in token_types:
        for p in ((t.get('size') or {}).get('path') or []):
            if isinstance(p, dict):
                check(f"token_types {t.get('id')}", p.get('id'), p)
    return [F('R10', WARN, where, f"見直しの期限（review_by）が過ぎている {len(ids)} 件：{'、'.join(ids)}。出どころを確かめ直し、"
                                  'verified_on と review_by を更新する') for where, ids in groups.items()]
