# -*- coding: utf-8 -*-
"""The triage of the review questions (#56): templates/review/triage.yaml sorts each question of perspectives.md into
A machine / B author self-check / C human judgement / D expert, and is the source of the short list given to reviewers.

  python tools/review_triage.py --check            # triage.yaml is complete and the generated files match it (CI)
  python tools/review_triage.py --write            # rewrite the generated files
  python tools/review_triage.py --counts           # questions per class, priority and condition
  python tools/review_triage.py --design DIR [--seed S]   # the sheet for one design: its 12 traits (holds / does not /
                                                   # cannot be read, with the field read), the priority 1 questions,
                                                   # three open prompts, then the questions "if time remains"
  python tools/review_triage.py --load DIR [DIR..] # the size of the short list of each design (items, sentences, characters)

Generated from triage.yaml (never edited by hand):
  templates/review/perspectives.md      the line `- 区分：…` of every question
  templates/review/short_list.md        the short list for reviewers (class C, by priority and condition; open prompts)
  .github/PULL_REQUEST_TEMPLATE/design_doc.md   the self-check of the author before a review (class B, and class A
                                        questions that no lint rule decides yet)
  templates/review/README.md            the table of the classes between the triage-counts markers
docs/claims/data/review.js takes the same data through tools/build_claims_viewer.py.

Checks (errors; tools/review_check.py runs them as V14 with the other checks of the review materials):
  T1  every question of perspectives.md is classified exactly once; no entry names an unknown question
  T2  class is A, B, C or D and `why` is not empty
  T3  class A: every rule of `lint` is a rule of tools/claim_lint/RULES.md; every `proposed` is a planned rule
      (templates/trace/planned_items.yaml) that RULES.md does not have yet, or an N<n> of `proposed_rules`; one of the
      two is not empty; a question with a proposed rule (no rule decides it yet, or the rules decide a part of it) has
      `interim: B`, which also puts it on the author's list until the rule exists; a question that the existing rules
      decide has none; `rest` (the part of the question the rule does not see) names a class C question of a default
      priority, so that no part of a question is left to nobody
  T4  class C: priority 1-3, unit and show_when (known conditions); `ask` is ONE sentence (no 。 inside, at most 70
      characters), the explanation goes to the optional `hint`; `show_on_lint` names rules of RULES.md; `until_rule`
      (a machine-decidable question a reviewer answers until its rule exists) names proposals; `merged_into` names a
      class C question of a default priority and the question itself has priority 3
  T5  class D: `escalation` is a criterion of escalation.md
  T6  `when` (classes A and B: when the author's check applies) names known conditions; `group` names an author group
  T7  5-8 open prompts with unique `op-` IDs, known conditions, a one-sentence `ask` and `from`
  T8  every condition is used; every N<n> rule is used by a question or carries a pilot finding
  T9  the generated files equal what triage.yaml gives (--check; fix with --write)
"""
import argparse
import os
import re
import sys
from urllib.parse import urlparse

import yaml

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

TRIAGE = os.path.join('templates', 'review', 'triage.yaml')
PERSP = os.path.join('templates', 'review', 'perspectives.md')
SHORT = os.path.join('templates', 'review', 'short_list.md')
PR_TEMPLATE = os.path.join('.github', 'PULL_REQUEST_TEMPLATE', 'design_doc.md')
README = os.path.join('templates', 'review', 'README.md')
CLASS_LINE = re.compile(r'^- 区分：.*$')
UNITS = ('row', 'hop', 'design')
ASK_MAX = 70
STATE_WORD = {'on': '当たる', 'off': '当たらない', 'unknown': '読めない'}


def _read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def load(root=ROOT):
    return yaml.safe_load(_read(os.path.join(root, TRIAGE)))


def by_id(tri):
    return {q['id']: q for q in tri.get('questions') or []}


# ---------------------------------------------------------------- traits of a design (the conditions of show_when)
def _adopted(rows):
    return [r for r in rows or [] if isinstance(r, dict) and r.get('decision') != '却下']


def read_traits(reg):
    """The conditions of triage.yaml for a design: {condition: {'state': 'on' | 'off' | 'unknown', 'evidence': text}}.

    reg: {claims, token_types, hops, catalog_answers} as the parsed YAML files (a missing file is None). A trait is on
    when the registry shows it OR the author declared it (catalog_answers: lite_criteria, questions). A trait whose file
    is missing is `unknown` (not off): its questions are shown with a note, so that a design that leaves something out
    does not get a shorter list silently. docs/claims/review.js readTraits() is the same function."""
    claims = _adopted(((reg.get('claims') or {}).get('claims')))
    types = _adopted(((reg.get('token_types') or {}).get('token_types')))
    no_hops = not isinstance(reg.get('hops'), dict)
    no_cat = not isinstance(reg.get('catalog_answers'), dict)
    hops = [h for h in ((reg.get('hops') or {}).get('hops') or []) if isinstance(h, dict)]
    cat = reg.get('catalog_answers') or {}
    lite = cat.get('lite_criteria') or {}
    asked = cat.get('questions') or {}

    def declared(section, key, field):
        v = section.get(key) if isinstance(section, dict) else None
        return v.get(field) if isinstance(v, dict) and isinstance(v.get(field), bool) else None
    names = {str(c.get('name')): str(c.get('id')) for c in claims}
    kinds = {}
    for h in hops:
        kinds.setdefault(h.get('kind'), str(h.get('id')))
    out = {}

    def put(cond, on, evidence, unknown=None):
        out[cond] = {'state': 'on' if on else 'unknown' if unknown else 'off', 'evidence': on or unknown or evidence}

    def first(rows, test):
        return next((str(r.get('id')) for r in rows if test(r)), None)
    out['always'] = {'state': 'on', 'evidence': '条件なし'}
    c = first(claims, lambda c: c.get('namespace') or (not c.get('registered_ref') and c.get('usage') in ('authz', 'identifier')))
    put('org_claims', c and f'claims.yaml の {c}（名前空間つき、または登録名でない認可・識別子の行）', 'claims.yaml に、名前空間つきの行も、登録名でない認可・識別子の行も無い')
    c = first(claims, lambda c: c.get('pii_category') and c.get('pii_category') != '該当なし')
    put('pii', c and f'claims.yaml の {c} の pii_category', 'claims.yaml の pii_category は、どの行も「該当なし」か未記入')
    hosts = sorted({urlparse(str(i.get('iss'))).netloc for t in types for i in (t.get('issuers') or [])
                    if isinstance(i, dict) and urlparse(str(i.get('iss'))).netloc})
    c = first(claims, lambda c: c.get('upstream_issuer'))
    put('multi_idp', (len(hosts) > 1 and f'token_types.yaml の issuers のホストが {len(hosts)} 種類（{"・".join(hosts[:3])}{" ほか" if len(hosts) > 3 else ""}）')
        or (c and f'claims.yaml の {c} の upstream_issuer'), 'token_types.yaml の issuers のホストは 1 種類以下で、upstream_issuer のある行も無い')
    k = kinds.get('exchange') or kinds.get('reissue')
    d = declared(lite, 'delegation_or_exchange', 'answer')
    put('exchange', (k and f'hops.yaml の {k}（kind が exchange・reissue）') or (d and 'catalog_answers.yaml の lite_criteria.delegation_or_exchange が Yes（書き手の宣言）'),
        'hops.yaml に kind が exchange・reissue の行が無く、書き手も宣言していない', no_hops and 'hops.yaml が無い')
    t = first(types, lambda t: t.get('max_delegation_depth') is not None)
    a = names.get('act') or names.get('may_act')
    d = declared(asked, 'q-actor', 'needed')
    put('delegation', (a and f'claims.yaml の {a}（act・may_act）') or (t and f'token_types.yaml の {t} の max_delegation_depth')
        or (d and 'catalog_answers.yaml の questions.q-actor が「要る」（書き手の宣言。台帳に act の行は無い）'),
        'claims.yaml に act・may_act の行が無く、max_delegation_depth も無く、書き手も q-actor を「要らない」とした',
        (d is None and 'catalog_answers.yaml の questions.q-actor の回答が無い')
        or (declared(lite, 'delegation_or_exchange', 'answer') and '要確認：lite_criteria.delegation_or_exchange は Yes だが、act の行が無く、q-actor は「要らない」（委任か交換かを、図と要求で確かめる）'))
    h = first(hops, lambda h: h.get('authorization_details'))
    put('approval', (names.get('authorization_details') and f'claims.yaml の {names["authorization_details"]}（authorization_details）')
        or (h and f'hops.yaml の {h} の authorization_details'), 'authorization_details が、claims.yaml の行にも hops.yaml にも無い', no_hops and 'hops.yaml が無い')
    # the author's answer decides multitenant; tenant_binding is read only when there is no answer (a
    # single-organisation design may still bind its tokens to the issuer: the dry run of #56 on the pilot scenario C)
    d = declared(lite, 'multitenant', 'answer')
    t = first(types, lambda t: t.get('tenant_binding'))
    if d is not None:
        put('multitenant', d and 'catalog_answers.yaml の lite_criteria.multitenant が Yes（書き手の宣言）', 'catalog_answers.yaml の lite_criteria.multitenant が No（書き手の宣言）')
    else:
        put('multitenant', t and f'token_types.yaml の {t} の tenant_binding（lite_criteria.multitenant の回答は無い）', 'tenant_binding のある種別が無い（lite_criteria.multitenant の回答も無い）')
    put('data_layer', kinds.get('db_connection') and f'hops.yaml の {kinds["db_connection"]}（kind が db_connection）', 'hops.yaml に kind が db_connection の行が無い', no_hops and 'hops.yaml が無い')
    a = names.get('acr') or names.get('amr') or names.get('auth_time')
    put('auth_context', a and f'claims.yaml の {a}（acr・amr・auth_time）', 'claims.yaml に acr・amr・auth_time の行が無い')
    t = first(types, lambda t: t.get('sender_constraint') in ('dpop', 'mtls'))
    d = declared(asked, 'q-holder', 'needed')
    put('sender_constrained', (t and f'token_types.yaml の {t} の sender_constraint') or (d and 'catalog_answers.yaml の questions.q-holder が「要る」（書き手の宣言）'),
        'sender_constraint が dpop・mtls の種別が無い')
    t = first(types, lambda t: t.get('kind') in ('access_token', 'internal_token') and t.get('sender_constraint') in (None, 'none'))
    put('sender_declined', t and f'token_types.yaml の {t} の sender_constraint が none か未記入', 'アクセストークン・内部トークンは、どれも送信者制約つき')
    t = first(types, lambda t: t.get('long_running'))
    put('long_running', (t and f'token_types.yaml の {t} の long_running') or (kinds.get('broker_connection') and f'hops.yaml の {kinds["broker_connection"]}（kind が broker_connection）'),
        'long_running のある種別も、kind が broker_connection のホップも無い', no_hops and 'hops.yaml が無い')
    return out


def traits(reg):
    """The conditions that hold or cannot be read (both show their questions)."""
    return {c for c, v in read_traits(reg).items() if v['state'] != 'off'}


class DesignError(Exception):
    pass


def load_design(design_dir):
    """The four registry files of a design. A missing directory, claims.yaml or token_types.yaml is an error (nothing
    can be read); a missing hops.yaml or catalog_answers.yaml is None (its traits are `unknown`)."""
    if not os.path.isdir(design_dir):
        raise DesignError(f'{design_dir}: 設計書のディレクトリが無い')
    reg = {}
    for name in ('claims', 'token_types', 'hops', 'catalog_answers'):
        p = os.path.join(design_dir, name + '.yaml')
        if not os.path.isfile(p):
            if name in ('claims', 'token_types'):
                raise DesignError(f'{p}: 無い（台帳と目録が無いと、設計の性質を読めない）')
            reg[name] = None
            continue
        try:
            reg[name] = yaml.safe_load(_read(p))
        except yaml.YAMLError as e:
            raise DesignError(f'{p}: YAML として読めない（{str(e).splitlines()[0]}）')
        if not isinstance(reg[name], dict):
            raise DesignError(f'{p}: 中身が無いか、マップでない')
    return reg


def selected(tri, have, warn_rules=(), priorities=None):
    """The class C questions shown by default for a design with the traits `have`: a default priority (1) and a
    condition that holds, or a lint rule of show_on_lint that gave a warning. In the order of priority, then of
    perspectives.md. priorities: other priorities to select (optional(): the questions "if time remains")."""
    prios = set(priorities or (tri.get('budget') or {}).get('default_priorities') or [1])
    out = []
    for q in tri['questions']:
        if q.get('class') != 'C':
            continue
        by_cond = q.get('priority') in prios and bool(set(q.get('show_when') or []) & set(have))
        by_lint = priorities is None and bool(set(q.get('show_on_lint') or []) & set(warn_rules))
        if by_cond or by_lint:
            out.append(q)
    return sorted(out, key=lambda q: q.get('priority', 9))


def optional(tri, have):
    """The questions "if time remains" (priority 2) of a design: shown apart and counted apart."""
    return selected(tri, have, priorities=(tri.get('budget') or {}).get('optional_priorities') or [2])


def prompts(tri, have):
    """The open prompts of a design, the ones that fit it first: a condition other than `always` holds, then a trait of
    prefer_when holds, then the rest; within each, the order of triage.yaml. The first budget.default_prompts are shown
    by default (default_prompts()), the others under "more"."""
    have = set(have)
    ps = [p for p in tri.get('open_prompts') or [] if set(p.get('show_when') or []) & have]

    def rank(p):
        if set(p['show_when']) - {'always'} & have:
            return 0
        return 1 if set(p.get('prefer_when') or []) & have else 2
    return sorted(ps, key=rank)


def default_prompts(tri, have):
    return prompts(tri, have)[:(tri.get('budget') or {}).get('default_prompts') or 3]


def row_sample(tri, reg, seed):
    """The rows a "per row" question is answered for: budget.row_sample adopted claims used for authorization or as an
    identifier, ranked by sha256(seed + ':' + id) (the same kind of draw as tools/review_record.py sample)."""
    import hashlib
    rows = [str(c.get('id')) for c in _adopted(((reg.get('claims') or {}).get('claims'))) if c.get('usage') in ('authz', 'identifier')]
    ranked = sorted(rows, key=lambda i: hashlib.sha256(f'{seed}:{i}'.encode('utf-8')).hexdigest())
    return ranked[:(tri.get('budget') or {}).get('row_sample') or 3], len(rows)


def sentences(text):
    """Number of sentences of a Japanese text (ends with 。 or ？, or the end of the text)."""
    return len([x for x in re.split(r'[。？]', text or '') if x.strip()])


def load_of(tri, have):
    """The size of the default list of a design (priority 1 questions and the default open prompts): items, and the
    sentences and characters to read (the questions only, and with the hints); and the number "if time remains"."""
    qs, ps = selected(tri, have), default_prompts(tri, have)
    items = qs + ps
    ask = [x['ask'] for x in items]
    hint = [x.get('hint') or '' for x in items]
    return {'questions': len(qs), 'prompts': len(ps), 'items': len(items),
            'ask_sentences': sum(sentences(a) for a in ask), 'ask_chars': sum(len(a) for a in ask),
            'all_sentences': sum(sentences(a) + sentences(h) for a, h in zip(ask, hint)),
            'all_chars': sum(len(a) + len(h) for a, h in zip(ask, hint)),
            'optional_questions': len(optional(tri, have)), 'more_prompts': len(prompts(tri, have)) - len(ps)}


# ---------------------------------------------------------------- generated text
def _lint_ref(rule):
    return f'`lint:{rule}`'


def _proposed_ref(rule):
    return rule if rule.startswith('N') else f'`lint:{rule}`（未実装）'


def class_line(tri, q):
    """The line `- 区分：…` of one question of perspectives.md."""
    c = q['class']
    name = tri['classes'][c]['name']
    if c == 'A':
        lint = '・'.join(_lint_ref(r) for r in q.get('lint') or [])
        prop = '・'.join(_proposed_ref(r) for r in q.get('proposed') or [])
        rest = f'。規則が見ない残りは、`{q["rest"]}` でレビュアーが見る' if q.get('rest') else ''
        if lint:
            return (f'- 区分：A {name}。lint の {lint} が確かめる（レビュアーは答えない）'
                    + (f'。規則が見ない残り（規則の案：{prop}）は、規則ができるまで書き手の自己点検で確かめる' if prop else '') + rest)
        return f'- 区分：A {name}。答えを決める規則はまだ無い（案：{prop}）。規則ができるまでは、書き手の自己点検で確かめる'
    if c == 'B':
        return f'- 区分：B {name}（提出前のチェックリストで、書き手が確かめる。レビュアーは答えない）'
    if c == 'C':
        cond = '・'.join(tri['conditions'][x]['label'] for x in q['show_when'])
        warn = ''.join(f'。{_lint_ref(r)} の warn が出たときも出す' for r in q.get('show_on_lint') or [])
        if q.get('merged_into'):
            return f'- 区分：C {name}（`{q["merged_into"]}` にまとめた。レビュアーはそちらで答える。この問いは既定では出さない）'
        if q.get('step'):
            return f'- 区分：C {name}（レビュアーが、手順の段 {q["step"]} で確かめる。短い一覧には出さない）'
        until = ('。機械で決まるが規則がまだ無いので（案：' + '・'.join(_proposed_ref(r) for r in q['until_rule']) + '）、規則ができるまでレビュアーが答える') if q.get('until_rule') else ''
        prio = '既定で出す' if q['priority'] in tri['budget']['default_priorities'] else '時間があれば' if q['priority'] in tri['budget']['optional_priorities'] else '既定では出さない'
        return f'- 区分：C {name}（レビュアーが答える。優先 {q["priority"]}＝{prio}。出す条件：{cond}{warn}{until}）'
    return f'- 区分：D {name}（レビュアーは答えず、`review:escalation#{q["escalation"]}` の基準で回す）'


def perspectives_text(tri, text):
    """perspectives.md with the 区分 line of every question set from triage.yaml (after the last field line of the block)."""
    import review_check
    qs = by_id(tri)
    lines = text.split('\n')
    out, k = [], 0
    while k < len(lines):
        m = review_check.Q_START.match(lines[k])
        out.append(lines[k])
        k += 1
        if not m or m.group(1) not in qs:
            continue
        block = []
        while k < len(lines) and lines[k].strip():
            if not CLASS_LINE.match(lines[k]):
                block.append(lines[k])
            k += 1
        out += block + [class_line(tri, qs[m.group(1)])]
    return '\n'.join(out)


def _version(root):
    return re.match(r'<!-- template_version: ([0-9.]+) -->', _read(os.path.join(root, PERSP))).group(1)


def _cond_labels(tri, ids):
    return '・'.join(tri['conditions'][x]['label'] for x in ids)


def _parsed(root):
    import review_check
    return review_check.parse_questions(_read(os.path.join(root, PERSP)))


def _cell(q, see_of):
    """The question cell of a table: the one-sentence question, then the hint and the fields to open."""
    hint = f'<br>*{q["hint"]}*' if q.get('hint') else ''
    see = f'<br>見る欄：{see_of[q["id"]]}' if q['id'] in see_of else ''
    return f'**{q["ask"]}**{hint}{see}'


def short_list_text(tri, root=ROOT):
    parsed = _parsed(root)
    text_of = {q['id']: q['text'] for q in parsed}
    see_of = {q['id']: q['fields'].get('見る欄', '') for q in parsed}
    qs = tri['questions']
    n = {c: sum(1 for q in qs if q['class'] == c) for c in 'ABCD'}
    cq = [q for q in qs if q['class'] == 'C']
    b = tri['budget']
    default = [q for q in cq if q['priority'] in b['default_priorities']]
    opt = [q for q in cq if q['priority'] in b['optional_priorities']]
    whole = b['whole_procedure_minutes']

    def table(rows):
        out = ['| 問い ID | 問い | 出す条件 |', '| --- | --- | --- |']
        for q in rows:
            until = '<br>（機械で決まる問い。lint の規則ができるまで）' if q.get('until_rule') else ''
            out.append(f'| `{q["id"]}` | {_cell(q, see_of)}{until} | {_cond_labels(tri, q["show_when"])} |')
        return out
    L = [f'<!-- template_version: {_version(root)} -->',
         '# 人に渡す短い一覧（レビュアーが答える問い）',
         '',
         '<!-- このファイルは python tools/review_triage.py --write が templates/review/triage.yaml から作る。手で直さない -->',
         '',
         f'レビュアーが答える問いの全部です。1 つの設計で答えるのは、このうち設計の性質に当たる分だけで、**その 1 枚は `python tools/review_triage.py --design <設計書のディレクトリ>` が作ります**。'
         f'既定で出すのは優先 1 の問い（設計ごとに {b["questions"][0]}〜{b["questions"][1]} 問）と、開いた問い {b["default_prompts"]} つです。'
         f'時間の目安は、問いに答えるのに {b["minutes"][0]}〜{b["minutes"][1]} 分、レビューの全体（手順の段 0〜6）で {whole[0]}〜{whole[1]} 分です（LLM の見積もり。**人では測っていません**。#20）。'
         'この文書の作り方・ここに無い問いの行き先は、末尾の 8. にあります。',
         '',
         '<a id="traits"></a>',
         '',
         '## 1. 先に、設計の性質を読む',
         '',
         '問いは、設計の性質に当たるものだけを出します。`--design` の 1 枚の先頭に、12 の性質が「当たる／当たらない／読めない」と、読んだ欄つきで出ます。',
         '**レビュアーは、手順の段 1 で、この表を図と要求に照らして確かめます**（1〜2 分）。「当たらない」とされた性質が実際にはあるなら、それ自体を指摘にし、その性質の問いも足して答えます。',
         '',
         '| 性質 | 読み方 | 出る問い（優先 1） | 時間があれば（優先 2） | 出る開いた問い |',
         '| --- | --- | --- | --- | --- |']
    for cid, c in tri['conditions'].items():
        nq = sum(1 for q in default if cid in q['show_when'])
        no = sum(1 for q in opt if cid in q['show_when'])
        npr = sum(1 for p in tri['open_prompts'] if cid in p['show_when'])
        L.append(f'| {c["label"]} | {c["read"]} | {nq} | {no} | {npr} |')
    L += ['',
          '- 性質は、**台帳が示すか、書き手が宣言していれば**当たります。読むためのファイルが無い・宣言どうしが食い違う性質は「読めない」として、問いを出します。黙って一覧を短くしません',
          '- 条件を 2 つ以上持つ問いは、どれか 1 つに当たれば出ます（上の表では、それぞれの行で数えています）',
          '',
          '<a id="questions"></a>',
          '',
          f'## 2. 問い（優先 1。既定で出す {len(default)} 問のうち、設計の性質に当たるもの）',
          '',
          '問いは 1 文です。**自分の言葉で答えを 1 行書けるか**を確かめ、書けない・設計書から読み取れないなら指摘にします。'
          '斜体は手がかり（見る場所と、あわせて確かめること）で、問いだけで答えられるなら読まなくてかまいません。「見る欄」は、開く設計書の節（`template:…`）と台帳の列（`registry:…`）です。'
          'No のときの重大度の目安と根拠は、観点書の同じ ID の問いにあります。']
    for unit in UNITS:
        rows = [q for q in default if q['unit'] == unit]
        L += ['', f'<a id="unit-{unit}"></a>', '', f'### {tri["units"][unit]}', '']
        if unit == 'row':
            L += [f'**全部の行には答えません。** 認可・識別子に使う行（`usage` が authz・identifier）から {b["row_sample"]} 行を抜き取り、その行について答えます。'
                  '抜き取る行は `--design <ディレクトリ> --seed <種>` が決めます（同じ種なら同じ行。種をレポートに書く）。問いが名指す行（ロール・グループの行など）が抜き取りに無ければ、その行を足します。抜き取った行で答えが No なら、残りの行も見ます。', '']
        L += table(rows)
    L += ['',
          '<a id="optional"></a>',
          '',
          f'### 時間があれば（優先 2。{len(opt)} 問のうち、設計の性質に当たるもの）',
          '',
          '優先 1 と開いた問いを終えて、時間が残ったときに答えます。答えなかった問いは、レポートに書きます。量の目安には数えていません。',
          '']
    L += table(opt)
    L += ['',
          '<a id="on-lint"></a>',
          '',
          '## 3. lint の結果から出す問い',
          '',
          'lint の warn は、機械が「人が見てほしい」と言っている箇所です。次の規則の warn が出ていたら、その行について右の問いに答えます。',
          'warn に行ごとの理由が書いてあるか（[../CONTRIBUTING.md](../CONTRIBUTING.md) の 2.）も、あわせて見ます。',
          '',
          '| lint の規則 | 問い ID | 問い |',
          '| --- | --- | --- |']
    for q in cq:
        for r in q.get('show_on_lint') or []:
            L.append(f'| {_lint_ref(r)} | `{q["id"]}` | {_cell(q, see_of)} |')
    L += ['',
          '<a id="open-prompts"></a>',
          '',
          '## 4. 開いた問い（要求と運用から辿る）',
          '',
          '設計書の決まった欄を開くだけでは答えられない問いです。要求の文と運用の場面から自分で辿り、辿った範囲と気づいたことを書きます（指摘の出どころは「テンプレート外」）。',
          f'**設計ごとに {b["default_prompts"]} つまで**を出します。性質に合うもの（「先に出す設計」に当たるもの）を先に選び、残りは下の表の順です。選ばれなかったものは「さらに」として、時間があれば辿ります。1 つにつき 2〜4 分が目安です（未計測）。',
          '',
          '| ID | 辿ること | 出す条件 | 先に出す設計 |',
          '| --- | --- | --- | --- |']
    for p in tri['open_prompts']:
        pref = _cond_labels(tri, p.get('prefer_when') or []) or ('（条件に当たれば先に出す）' if set(p['show_when']) - {'always'} else '—')
        L.append(f'| {p["id"]} | {_cell(p, {})} | {_cond_labels(tri, p["show_when"])} | {pref} |')
    L += ['',
          'これらは、パイロット（#9）で問いの一覧の外から出た Major の指摘を元に作りました。同じ設計で作って同じ設計で確かめた問いなので、別の設計でも効くかは分かっていません（triage-evidence.md の 3.）。',
          '旧経路・テストの経路は `q-outside-catalog` に、同意と宛先の束縛は `q-approval-from-as` にまとめてあります。',
          '',
          '<a id="experts"></a>',
          '',
          '## 5. 専門家に回す（レビュアーは答えない）',
          '',
          '次の問いは、レビュアーに答えを求めません。[escalation.md](escalation.md) の基準の表を上から見て、当たる行を回します。',
          '',
          '| 問い ID | 問い | 回す基準 |',
          '| --- | --- | --- |']
    for q in qs:
        if q['class'] == 'D':
            L.append(f'| `{q["id"]}` | {text_of[q["id"]]} | `review:escalation#{q["escalation"]}` |')
    L += ['',
          '<a id="machine"></a>',
          '',
          '## 6. 機械が確かめること（レビュアーは答えない）',
          '',
          '次の問いは、lint の規則が答えを決めます。レビュアーは、設計書の 1. の結果で error が 0 であることと、warn に理由が付いていることだけを見ます。',
          '規則が決めるのは「宣言が矛盾していない」ことまでです（RULES.md）。既存の規則だけが答えを決めるとした問いは、記入例の答えを No に書き換えて、lint が指摘を出すことを 1 問ずつ確かめました（[research/template-design/triage-audit.md](../../research/template-design/triage-audit.md)）。',
          '',
          '| lint の規則 | 確かめる問い |',
          '| --- | --- |']
    rules = {}
    for q in qs:
        for r in q.get('lint') or []:
            rules.setdefault(r, []).append(q['id'])
    for r in sorted(rules, key=lambda x: (x[0], int(re.sub(r'\D', '', x) or 0), x)):
        L.append(f'| {_lint_ref(r)} | ' + '・'.join(f'`{i}`' for i in rules[r]) + ' |')
    pend = [q for q in qs if q['class'] == 'A' and q.get('proposed')]
    L += ['',
          f'規則がまだ無い問い・規則が一部しか見ない問い（{len(pend)} 問）は、規則ができるまで、書き手の提出前のチェックリストに置いています。規則の案は triage.yaml の `proposed_rules` と、その一覧の issue（{tri["proposed_rules_issue"]}）にあります。',
          '',
          '| 問い ID | いまの規則 | 規則の案 |',
          '| --- | --- | --- |']
    for q in pend:
        L.append(f'| `{q["id"]}` | ' + ('・'.join(_lint_ref(r) for r in q.get('lint') or []) or '無い') + ' | ' + '・'.join(_proposed_ref(r) for r in q['proposed']) + ' |')
    rest = [q for q in cq if q['priority'] not in b['default_priorities'] + b['optional_priorities']]
    L += ['',
          '<a id="more"></a>',
          '',
          f'## 7. 詳しく見る（優先 3。出さない {len(rest)} 問）',
          '',
          '問いに答える中で気になったときに見ます。ほかの問いにまとめた問いと、手順の別の段で確かめる問いも、ここにあります。',
          '',
          '| 問い ID | 問い | 当たる設計 |',
          '| --- | --- | --- |']
    for q in rest:
        note = f'（`{q["merged_into"]}` にまとめた）' if q.get('merged_into') else f'（手順の段 {q["step"]} で確かめる）' if q.get('step') else ''
        L.append(f'| `{q["id"]}` | {q["ask"]}{note} | {_cond_labels(tri, q["show_when"])} |')
    L += ['',
          '<a id="not-here"></a>',
          '',
          '## 8. ここに無い問いの行き先と、この文書について',
          '',
          f'観点書（[perspectives.md](perspectives.md)）の {len(qs)} 問を 1 問ずつ振り分け（[triage.yaml](triage.yaml)）、人が判断する {n["C"]} 問を残しました。',
          '',
          '| 区分 | 数 | 誰が確かめるか |',
          '| --- | --- | --- |',
          f'| A 機械 | {n["A"]} | claim_lint（[RULES.md](../../tools/claim_lint/RULES.md)）。レビュアーは、設計書の 1. に貼られた結果で error が 0 であることだけを見る（手順の段 0）。'
          f'うち {sum(1 for q in qs if q["class"] == "A" and not q.get("lint"))} 問は規則がまだ無く、{sum(1 for q in qs if q["class"] == "A" and q.get("lint") and q.get("proposed"))} 問は規則が一部しか見ない。'
          'この分は、規則ができるまで書き手の自己点検にも置く（6.） |',
          f'| B 書き手の自己点検 | {n["B"]} | 書き手が、提出前のチェックリスト（PR のテンプレート `.github/PULL_REQUEST_TEMPLATE/design_doc.md`）で確かめる。'
          'レビュアーは、印の無い行を読み、25 問の回答の行と、No なら Blocker の行から 2 件を抜き取って欄を開く（手順の段 0） |',
          f'| C 人の判断 | {n["C"]} | レビュアー。優先 1 の {len(default)} 問（既定）、優先 2 の {len(opt)} 問（時間があれば）、優先 3 の {len(rest)} 問（出さない）。'
          f'優先 1 のうち {sum(1 for q in cq if q.get("until_rule"))} 問は、機械で決まるが規則がまだ無いので、規則ができるまでレビュアーが答える |',
          f'| D 専門家 | {n["D"]} | レビュアーは答えず、[escalation.md](escalation.md) の基準に当たる行を回す（5.） |',
          '',
          '- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施',
          '- 区分・優先・出す条件・量と時間の目安は、どれも筆者の提案と LLM の見積もりです（追跡 #56）。人が測るのは #20 です。根拠にしたパイロット（#9）の数は [research/template-design/triage-evidence.md](../../research/template-design/triage-evidence.md) にあります',
          '- 「漏れゼロ」は約束しません。パイロットでは、人の判断が要る Major の指摘の半分が、問いの一覧の外から出ました。そのため、問いのほかに開いた問い（4.）を置いています',
          '- エディターのレビューモード（`docs/claims/`）の「観点のチェックリスト」は、開いている設計書から同じ性質を読み、既定でこの一覧を出します',
          '',
          '```',
          'python tools/review_triage.py --design <設計書のディレクトリ> [--seed <種>]   # その設計の 1 枚（性質の表、問い、開いた問い）',
          'python tools/review_triage.py --load <設計書のディレクトリ>…                  # 一覧の大きさ（問い・文・字数）',
          '```',
          '',
          '根拠：筆者の提案：問いの区分・優先・出す条件・1 回の量の目安（追跡 #56）、templates/CONTRIBUTING.md の 2.・3.、research/template-design/pilot.md の 9.',
          '']
    return '\n'.join(L)


def author_lines(tri, root=ROOT):
    """The lines of the author's self-check: [{ids, text, when, blocker, kind}]. Questions answered by one check are
    one line: the class B questions of one `group`, and the class A questions waiting for the same proposed rules."""
    parsed = _parsed(root)
    text_of = {q['id']: q['text'] for q in parsed}
    blocker = {q['id'] for q in parsed if q['fields'].get('No なら', '').startswith('Blocker')}
    out, seen = [], {}
    for q in tri['questions']:
        if q['class'] == 'B':
            key = ('group', q.get('group')) if q.get('group') else ('q', q['id'])
            text = tri['author_groups'][q['group']] if q.get('group') else text_of[q['id']]
            kind = 'B'
        elif q['class'] == 'A' and q.get('interim') == 'B':
            key = ('rule', tuple(q['proposed']), tuple(q.get('when') or []))
            props = tri['proposed_rules']
            # a new proposal says what to check; a planned rule has no text here, so the first question speaks
            ns = [props[r]['rule'] for r in q['proposed'] if r.startswith('N')]
            text = '；'.join(ns) if ns else text_of[q['id']]
            kind = 'A'
        else:
            continue
        if key in seen:
            seen[key]['ids'].append(q['id'])
            seen[key]['blocker'] = seen[key]['blocker'] or q['id'] in blocker
            continue
        seen[key] = {'ids': [q['id']], 'text': text, 'when': q.get('when') or [], 'blocker': q['id'] in blocker, 'kind': kind, 'group': q.get('group'),
                     'rules': q.get('proposed') or [], 'lint': q.get('lint') or []}
        out.append(seen[key])
    return out


def pr_template_text(tri, root=ROOT):
    lines = author_lines(tri, root)
    nq = sum(len(x['ids']) for x in lines)

    def item(x):
        ids = '・'.join(f'`{i}`' for i in x['ids'])
        mark = '**【No なら Blocker】** ' if x['blocker'] else ''
        mark = '**【レビュアーが必ず抜き取る】** ' + mark if x.get('group') else mark
        rule = ''
        if x['kind'] == 'A':
            rule = '（規則の案：' + '・'.join(x['rules']) + ('。いまの lint が一部を見る' if x['lint'] else '') + '）'
        return f'- [ ] {mark}{x["text"]}{rule} — {ids}'
    L = ['<!-- このファイルは python tools/review_triage.py --write が templates/review/triage.yaml から作る。手で直さない -->',
         '<!-- 設計書（台帳の YAML と design.md）の PR 用。PR を作る URL に ?template=design_doc.md を付けると、この様式になる -->',
         '',
         '## 設計書',
         '',
         '- 設計書のディレクトリ：',
         '- Lite／Full：',
         '- claim_lint の結果（error・warn・info の件数。error は 0 にする）：',
         '- レビュアーに特に見てほしい点（設計書の 12. の自信のない点）：',
         '',
         '## 提出前の自己点検（書き手が確かめる）',
         '',
         f'書き手が自分の設計書を開けば確かめられることを、{len(lines)} 行にまとめました（観点書 `templates/review/perspectives.md` の {nq} 問に当たる。行の末尾が問いの ID で、見る欄は観点書の同じ ID の問いにある）。'
         'レビュアーは、ここの問いには答えません。',
         '満たす行に印を付け、満たさない・当てはまらない行は、印を付けずに行の末尾に理由を書いてください。レビュアーは、印の無い行を読み、**25 問の回答の行（必ず）と、【No なら Blocker】の行から 2 件を抜き取って、欄を開きます**（手順の段 0）。',
         '区分と理由は `templates/review/triage.yaml` にあります。量と分け方は筆者の提案です（追跡 #56）。',
         '',
         '### どの設計でも',
         '']
    L += [item(x) for x in lines if x['kind'] == 'B' and not x['when']]
    conds = []
    for x in lines:
        for c in x['when']:
            if c not in conds:
                conds.append(c)
    for c in conds:
        L += ['', f'### 当てはまるときだけ：{tri["conditions"][c]["label"]}', '']
        L += [item(x) for x in lines if x['kind'] == 'B' and c in x['when']]
    L += ['', '### lint の規則ができるまで（機械で決まる。規則ができたら、ここから外す）', '']
    for x in lines:
        if x['kind'] == 'A':
            cond = f'（当てはまるときだけ：{_cond_labels(tri, x["when"])}）' if x['when'] else ''
            L.append(item(x) + cond)
    L += ['',
          '## レビュアーへ',
          '',
          '人が答える問いは `templates/review/short_list.md` にあります（`python tools/review_triage.py --design <ディレクトリ>` で、この設計に当たる問いの 1 枚が出ます）。',
          '']
    return '\n'.join(L)


COUNTS_RE = re.compile(r'(<!-- triage-counts:begin -->\n).*?(<!-- triage-counts:end -->)', re.S)


def readme_text(tri, text):
    """templates/review/README.md with the table of the classes between the triage-counts markers."""
    c = counts(tri)
    rows = ['| 区分 | 問いの数 | 行き先 |', '| --- | --- | --- |',
            f'| A 機械 | {c["A"]}（既存の規則が確かめる {c["A_with_rule"]}、規則が一部を確かめる {c["A_partial_rule"]}、規則がまだ無い {c["A_without_rule"]}） | claim_lint。規則が無い・足りない間は書き手の自己点検にも置く |',
            f'| B 書き手の自己点検 | {c["B"]} | 提出前のチェックリスト（PR のテンプレート。規則待ちの A と合わせて {c["author_lines"]} 行） |',
            f'| C 人の判断 | {c["C"]}（優先 1：{c["C_priority_1"]}、優先 2：{c["C_priority_2"]}、優先 3：{c["C_priority_3"]}。うち規則ができるまで人が答える機械の問い {c["C_until_rule"]}） | short_list.md（既定で出すのは優先 1 のうち、設計の性質に当たるもの。優先 2 は時間があれば） |',
            f'| D 専門家 | {c["D"]} | escalation.md |',
            f'| 計 | {c["total"]} | 開いた問いは、このほかに {c["open_prompts"]} 個 |']
    return COUNTS_RE.sub(lambda m: m.group(1) + '\n'.join(rows) + '\n' + m.group(2), text)


def generated(tri, root=ROOT):
    """{relative path: text} of the files made from triage.yaml."""
    return {PERSP: perspectives_text(tri, _read(os.path.join(root, PERSP))),
            SHORT: short_list_text(tri, root),
            PR_TEMPLATE: pr_template_text(tri, root),
            README: readme_text(tri, _read(os.path.join(root, README)))}


def design_sheet(tri, design_dir, root=ROOT, seed='review'):
    """The sheet handed to the reviewer of one design. It starts with the 12 traits (what was read) and the questions
    of this design (priority 1; one sentence each, the hint and the fields under it), then three open prompts, then the
    questions "if time remains"; how to answer and what is not asked come last."""
    reg = load_design(design_dir)
    tr = read_traits(reg)
    have = {c for c, v in tr.items() if v['state'] != 'off'}
    unknown = {c for c, v in tr.items() if v['state'] == 'unknown'}
    see_of = {q['id']: q['fields'].get('見る欄', '') for q in _parsed(root)}
    qs, opt, ps = selected(tri, have), optional(tri, have), prompts(tri, have)
    b = tri['budget']
    nd = b['default_prompts']
    listed = [q for q in tri['questions'] if q['class'] == 'C' and q['priority'] in b['default_priorities'] + b['optional_priorities']]
    rows, n_rows = row_sample(tri, reg, seed)
    out = [f'# このレビューで答える問い：{design_dir}',
           '',
           f'問い {len(qs)}・開いた問い {min(nd, len(ps))}（時間があれば：問い {len(opt)}・開いた問い {max(0, len(ps) - nd)}）。答え方と目安は末尾。',
           '',
           '## 1. 設計の性質（先に、図と要求に照らして確かめる）',
           '']
    for c, v in tr.items():
        if c == 'always':
            continue
        hidden = [q['id'] for q in listed if c in q['show_when'] and not set(q['show_when']) & have]
        hidden += [p['id'] for p in tri['open_prompts'] if c in p['show_when'] and not set(p['show_when']) & have]
        tail = f'。出さない問い {len(hidden)}：{"・".join(hidden)}' if v['state'] == 'off' and hidden else ''
        tail = '。読めないので、この性質の問いも出す' if v['state'] == 'unknown' else tail
        out.append(f'- [{STATE_WORD[v["state"]]}] {tri["conditions"][c]["label"]} ― {v["evidence"]}{tail}')

    def item(q):
        only_unknown = not (set(q['show_when']) & (have - unknown))
        lines = [f'- {q["id"]}　{q["ask"]}' + ('（性質が読めないので出している）' if only_unknown else '')]
        if q.get('hint'):
            lines.append(f'    手がかり：{q["hint"]}')
        if q['id'] in see_of:
            lines.append(f'    見る欄：{see_of[q["id"]]}')
        return lines
    n = 2
    for unit in UNITS:
        part = [q for q in qs if q['unit'] == unit]
        if not part:
            continue
        out += ['', f'## {n}. {tri["units"][unit]}', '']
        n += 1
        if unit == 'row':
            out += [f'答える行（認可・識別子に使う {n_rows} 行から {len(rows)} 行。種 {seed}）：{"・".join(rows)}。問いが名指す行（ロール・グループなど）が無ければ足す。答えが No なら、残りの行も見る。', '']
        for q in part:
            out += item(q)
    out += ['', f'## {n}. 開いた問い（決まった欄では答えられない。要求と運用から辿り、辿った範囲と気づきを書く）', '']
    for p in ps[:nd]:
        out += item(p)
    out += ['', f'## {n + 1}. 時間があれば', '']
    for q in opt:
        out += item(q)
    for p in ps[nd:]:
        out += [f'- （開いた問い・さらに）{p["id"]}　{p["ask"]}', f'    手がかり：{p["hint"]}']
    out += ['', f'## {n + 2}. 答え方と、答えないこと', '',
            '- 問いごとに、自分の言葉で答えを 1 行書く。書けない・設計書から読み取れないなら指摘にする。手がかりは、問いだけで答えられるなら読まなくてよい',
            '- 性質の表で「当たらない」とされた性質が実際にはあるなら、それ自体を指摘にし、その性質の問いも足して答える（全部の問いは templates/review/short_list.md）',
            f'- 目安は、問いに答える時間が {b["minutes"][0]}〜{b["minutes"][1]} 分、レビューの全体（手順の段 0〜6）が {b["whole_procedure_minutes"][0]}〜{b["whole_procedure_minutes"][1]} 分（LLM の見積もり。人では測っていない）',
            f'- この 1 枚の問いは、全 {len(tri["questions"])} 問のうち、人が判断する {counts(tri, root)["C"]} 問から選んだもの',
            '- 機械（lint）が確かめること：設計書の 1. の結果で、error が 0 かと、warn に理由があるかだけを見る',
            '- 書き手の自己点検（PR の本文）：印の無い行を読み、25 問の回答の行と、【No なら Blocker】の行から 2 件を抜き取って欄を開く',
            '- 暗号の方式・IdP や製品の実際の挙動・委任が 2 段以上になる場合：答えずに、専門家に回す（templates/review/escalation.md）']
    return '\n'.join(out), tr


# ---------------------------------------------------------------- checks
def check(root=ROOT, questions=None, generated_files=True):
    import review_check
    import trace_check
    errors = []
    path = os.path.join(root, TRIAGE)
    if not os.path.isfile(path):
        return [('T1', TRIAGE.replace(os.sep, '/'), 'ない')]
    tri = load(root)
    if questions is None:
        questions = review_check.parse_questions(_read(os.path.join(root, PERSP)))
    known = [q['id'] for q in questions]
    seen = {}
    planned = {}
    data = trace_check.yaml_load(trace_check._read(os.path.join(root, trace_check.ITEMS_FILE)))
    for it in (data or {}).get('items') or []:
        planned[str(it.get('ref'))] = it
    conds = tri.get('conditions') or {}
    used_conds, used_n = set(), set()
    esc_path = os.path.join(root, 'templates', 'review', 'escalation.md')
    criteria = set(re.findall(r'^\| `([a-z0-9-]+)` \|', _read(esc_path), re.M)) if os.path.isfile(esc_path) else set()
    props = tri.get('proposed_rules') or {}
    groups = tri.get('author_groups') or {}
    prios = set((tri.get('budget') or {}).get('default_priorities') or [1])
    entries = {str(q.get('id')): q for q in tri.get('questions') or []}

    def implemented(rule):
        return review_check.resolve(root, 'lint:' + rule, planned) is None

    def conds_ok(where, key, vals, need=True):
        if need and not vals:
            errors.append(('T4', where, f'{key} が空'))
        for v in vals or []:
            if v not in conds:
                errors.append(('T6' if key == 'when' else 'T4', where, f'{key} の {v} は conditions に無い'))
            used_conds.add(v)

    def proposals_ok(where, rule, vals):
        for r in vals:
            if str(r).startswith('N'):
                used_n.add(r)
                if r not in props:
                    errors.append((rule, where, f'規則の案 {r} が proposed_rules に無い'))
            elif implemented(r):
                errors.append((rule, where, f'規則の案 {r} は実装済み（lint に書く）'))
            elif 'lint:' + r not in planned:
                errors.append((rule, where, f'規則の案 {r} は planned_items.yaml に無い（新しい案は N<番号> で proposed_rules に書く）'))

    def human_default(where, rule, key, target):
        t = entries.get(target)
        if not t or t.get('class') != 'C' or t.get('priority') not in prios or t.get('merged_into'):
            errors.append((rule, where, f'{key} の {target} は、既定で出す（優先 1 の）区分 C の問いでない'))

    def one_sentence(where, rule, text):
        text = str(text or '').strip()
        if not text:
            errors.append((rule, where, 'ask（人に渡す問いの文）が空'))
        elif '。' in text or len(text) > ASK_MAX:
            errors.append((rule, where, f'ask は 1 文で、{ASK_MAX} 字まで（いま {len(text)} 字。説明は hint に書く）'))

    for q in tri.get('questions') or []:
        qid = str(q.get('id'))
        where = f'triage.yaml {qid}'
        if qid in seen:
            errors.append(('T1', where, '同じ問いが 2 回ある'))
        seen[qid] = q
        if qid not in known:
            errors.append(('T1', where, 'perspectives.md に無い問い'))
        c = q.get('class')
        if c not in ('A', 'B', 'C', 'D'):
            errors.append(('T2', where, f'class は A・B・C・D のどれか（{c!r}）'))
            continue
        if not str(q.get('why') or '').strip():
            errors.append(('T2', where, 'why（区分の根拠）が空'))
        if c == 'A':
            lint, prop = q.get('lint') or [], q.get('proposed') or []
            if not lint and not prop:
                errors.append(('T3', where, 'A には lint（既存の規則）か proposed（規則の案）が要る'))
            for r in lint:
                if not implemented(r):
                    errors.append(('T3', where, f'lint の {r} は tools/claim_lint/RULES.md に無い（未実装なら proposed に書く）'))
            proposals_ok(where, 'T3', prop)
            if prop and q.get('interim') != 'B':
                errors.append(('T3', where, '規則の案がある A の問い（規則が無い・一部しか見ない）には interim: B（規則ができるまで書き手の自己点検）が要る'))
            if not prop and q.get('interim'):
                errors.append(('T3', where, '既存の規則が答えを決める問いに interim は書かない'))
            if q.get('rest'):
                human_default(where, 'T3', 'rest', q['rest'])
        elif q.get('rest'):
            errors.append(('T3', where, 'rest は A の問いだけに書く'))
        if c == 'C':
            if q.get('priority') not in (1, 2, 3):
                errors.append(('T4', where, 'priority は 1・2・3'))
            if q.get('unit') not in UNITS:
                errors.append(('T4', where, f'unit は {"・".join(UNITS)}'))
            conds_ok(where, 'show_when', q.get('show_when'))
            one_sentence(where, 'T4', q.get('ask'))
            for r in q.get('show_on_lint') or []:
                if not implemented(r):
                    errors.append(('T4', where, f'show_on_lint の {r} は RULES.md に無い'))
            proposals_ok(where, 'T4', q.get('until_rule') or [])
            if q.get('merged_into'):
                human_default(where, 'T4', 'merged_into', q['merged_into'])
                if q.get('priority') != 3:
                    errors.append(('T4', where, 'ほかの問いにまとめた問い（merged_into）は priority 3 にする'))
            if q.get('step') and q.get('priority') != 3:
                errors.append(('T4', where, '手順の別の段で確かめる問い（step）は priority 3 にする'))
        elif q.get('show_when') or q.get('ask') or q.get('priority'):
            errors.append(('T4', where, 'show_when・ask・priority は C の問いだけに書く'))
        if c == 'D' and q.get('escalation') not in criteria:
            errors.append(('T5', where, f'escalation の {q.get("escalation")!r} は escalation.md の基準に無い'))
        if c in ('A', 'B'):
            conds_ok(where, 'when', q.get('when'), need=False)
        if q.get('group') and (c != 'B' or q['group'] not in groups):
            errors.append(('T6', where, f'group の {q["group"]} は author_groups に無い（group は B の問いだけに書く）'))
    for qid in known:
        if qid not in seen:
            errors.append(('T1', f'perspectives.md {qid}', 'triage.yaml に区分が無い'))
    ops = tri.get('open_prompts') or []
    if not 5 <= len(ops) <= 8:
        errors.append(('T7', 'triage.yaml open_prompts', f'開いた問いは 5〜8 個（{len(ops)} 個）'))
    ids = [str(p.get('id')) for p in ops]
    for p in ops:
        where = f'triage.yaml {p.get("id")}'
        if not re.match(r'^op-[a-z0-9-]+$', str(p.get('id'))) or ids.count(str(p.get('id'))) > 1:
            errors.append(('T7', where, 'ID は op- で始まり、重複しない'))
        one_sentence(where, 'T7', p.get('ask'))
        if not p.get('from'):
            errors.append(('T7', where, 'from（元にした指摘）が要る'))
        if not p.get('show_when'):
            errors.append(('T7', where, 'show_when が空'))
        for v in (p.get('show_when') or []) + (p.get('prefer_when') or []):
            if v not in conds:
                errors.append(('T7', where, f'show_when・prefer_when の {v} は conditions に無い'))
            used_conds.add(v)
    for cnd in conds:
        if cnd not in used_conds:
            errors.append(('T8', f'triage.yaml conditions.{cnd}', 'どの問いも使っていない条件'))
    for n, p in props.items():
        if n not in used_n and not (p or {}).get('pilot'):
            errors.append(('T8', f'triage.yaml proposed_rules.{n}', 'どの問いも引かず、パイロットの指摘も無い案'))
    if generated_files and not errors:
        for rel, want in generated(tri, root).items():
            p = os.path.join(root, rel)
            got = _read(p) if os.path.isfile(p) else None
            if got != want:
                errors.append(('T9', rel.replace(os.sep, '/'), 'triage.yaml から作る内容と違う（python tools/review_triage.py --write で直す）'))
    return errors


def counts(tri, root=ROOT):
    qs = tri['questions']
    out = {'total': len(qs)}
    for c in 'ABCD':
        out[c] = sum(1 for q in qs if q['class'] == c)
    out['A_with_rule'] = sum(1 for q in qs if q['class'] == 'A' and q.get('lint') and not q.get('proposed'))
    out['A_partial_rule'] = sum(1 for q in qs if q['class'] == 'A' and q.get('lint') and q.get('proposed'))
    out['A_without_rule'] = sum(1 for q in qs if q['class'] == 'A' and not q.get('lint'))
    for p in (1, 2, 3):
        out[f'C_priority_{p}'] = sum(1 for q in qs if q['class'] == 'C' and q['priority'] == p)
    out['C_until_rule'] = sum(1 for q in qs if q['class'] == 'C' and q.get('until_rule'))
    out['open_prompts'] = len(tri['open_prompts'])
    lines = author_lines(tri, root)
    out['author_lines'] = len(lines)
    out['author_questions'] = sum(len(x['ids']) for x in lines)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--root', default=ROOT)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--counts', action='store_true')
    ap.add_argument('--design', metavar='DIR', help='print the sheet for a design: its traits and the questions to answer')
    ap.add_argument('--seed', default='review', help='with --design: the seed of the rows the per-row questions are answered for')
    ap.add_argument('--load', metavar='DIR', nargs='+', help='print the size of the short list of each design')
    a = ap.parse_args(argv)
    tri = load(a.root)
    out, code = [], 0
    if a.write:
        errs = check(a.root, generated_files=False)
        if errs:
            out += [f'{r}  {w}  {m}' for r, w, m in errs] + ['FAIL（triage.yaml を直してから --write）']
            code = 1
        else:
            for rel, text in generated(tri, a.root).items():
                p = os.path.join(a.root, rel)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(text)
                out.append('wrote ' + rel.replace(os.sep, '/'))
    if a.counts:
        out += [f'{k}: {v}' for k, v in counts(tri, a.root).items()]
    try:
        if a.design:
            out.append(design_sheet(tri, a.design, a.root, a.seed)[0])
        if a.load:
            out.append('design\tquestions\tprompts\titems\task_sentences\task_chars\tall_sentences\tall_chars\toptional_questions\tmore_prompts')
            for d in a.load:
                v = load_of(tri, traits(load_design(d)))
                out.append('\t'.join([d] + [str(v[k]) for k in ('questions', 'prompts', 'items', 'ask_sentences', 'ask_chars', 'all_sentences', 'all_chars', 'optional_questions', 'more_prompts')]))
    except DesignError as e:
        sys.stderr.buffer.write(f'review_triage: {e}\n'.encode('utf-8'))
        return 2
    if a.check or not (a.write or a.counts or a.design or a.load):
        errs = check(a.root)
        out += [f'{r}  {w}  {m}' for r, w, m in errs] + [f'error {len(errs)}', 'FAIL' if errs else 'OK']
        code = 1 if errs else code
    sys.stdout.buffer.write(('\n'.join(out) + '\n').encode('utf-8'))
    return code


if __name__ == '__main__':
    sys.exit(main())
