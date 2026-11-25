# -*- coding: utf-8 -*-
"""The triage of the review questions (#56): templates/review/triage.yaml sorts each question of perspectives.md into
A machine / B author self-check / C human judgement / D expert, and is the source of the short list given to reviewers.

  python tools/review_triage.py --check            # triage.yaml is complete and the generated files match it (CI)
  python tools/review_triage.py --write            # rewrite the generated files
  python tools/review_triage.py --counts           # questions per class, priority and condition
  python tools/review_triage.py --design DIR       # the short list for one design (its traits, the questions shown)

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
      decide has none
  T4  class C: priority 1-3, unit and show_when (known conditions), `ask` not empty; `show_on_lint` names rules of RULES.md
  T5  class D: `escalation` is a criterion of escalation.md
  T6  `when` (classes A and B: when the author's check applies) names known conditions
  T7  5-8 open prompts with unique `op-` IDs, known conditions, `ask` and `from`
  T8  every condition is used; every N<n> rule is used by a question or carries a pilot finding
  T9  the generated files equal what triage.yaml gives (--check; fix with --write)
"""
import argparse
import os
import re
import sys

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


def traits(reg):
    """The conditions of triage.yaml that hold for a design. reg: {claims, token_types, hops, catalog_answers} as the
    parsed YAML files (a missing file is None). docs/claims/review.js designTraits() is the same function."""
    claims = _adopted(((reg.get('claims') or {}).get('claims')))
    types = _adopted(((reg.get('token_types') or {}).get('token_types')))
    hops = [h for h in ((reg.get('hops') or {}).get('hops') or []) if isinstance(h, dict)]
    lite = ((reg.get('catalog_answers') or {}).get('lite_criteria') or {})
    names = {str(c.get('name')) for c in claims}
    out = {'always'}
    if any(c.get('namespace') or (not c.get('registered_ref') and c.get('usage') in ('authz', 'identifier')) for c in claims):
        out.add('org_claims')
    if any(c.get('pii_category') and c.get('pii_category') != '該当なし' for c in claims):
        out.add('pii')
    iss = {str(i.get('iss')) for t in types for i in (t.get('issuers') or []) if isinstance(i, dict) and i.get('iss')}
    if len(iss) > 1 or any(c.get('upstream_issuer') for c in claims):
        out.add('multi_idp')
    kinds = {h.get('kind') for h in hops}
    if kinds & {'exchange', 'reissue'}:
        out.add('exchange')
    if names & {'act', 'may_act'} or any(t.get('max_delegation_depth') is not None for t in types):
        out.add('delegation')
    if 'authorization_details' in names or any(h.get('authorization_details') for h in hops):
        out.add('approval')
    # the author's answer decides; tenant_binding is read only when there is no answer (a single-organisation design
    # may still bind its tokens to the issuer: the dry run of #56 on the pilot scenario C)
    mt = lite.get('multitenant')
    answered = isinstance(mt, dict) and isinstance(mt.get('answer'), bool)
    if mt.get('answer') is True if answered else any(t.get('tenant_binding') for t in types):
        out.add('multitenant')
    if 'db_connection' in kinds:
        out.add('data_layer')
    if names & {'acr', 'amr', 'auth_time'}:
        out.add('auth_context')
    if any(t.get('sender_constraint') in ('dpop', 'mtls') for t in types):
        out.add('sender_constrained')
    if any(t.get('kind') in ('access_token', 'internal_token') and t.get('sender_constraint') in (None, 'none') for t in types):
        out.add('sender_declined')
    if any(t.get('long_running') for t in types) or 'broker_connection' in kinds:
        out.add('long_running')
    return out


def load_design(design_dir):
    reg = {}
    for name in ('claims', 'token_types', 'hops', 'catalog_answers'):
        p = os.path.join(design_dir, name + '.yaml')
        reg[name] = yaml.safe_load(_read(p)) if os.path.isfile(p) else None
    return reg


def selected(tri, have, warn_rules=()):
    """The class C questions shown by default for a design with the traits `have`: priority within the default
    priorities and a condition that holds, or a lint rule of show_on_lint that gave a warning. In the order of
    priority, then of perspectives.md."""
    prios = set((tri.get('budget') or {}).get('default_priorities') or [1, 2])
    out = []
    for q in tri['questions']:
        if q.get('class') != 'C':
            continue
        by_cond = q.get('priority') in prios and bool(set(q.get('show_when') or []) & set(have))
        by_lint = bool(set(q.get('show_on_lint') or []) & set(warn_rules))
        if by_cond or by_lint:
            out.append(q)
    return sorted(out, key=lambda q: q.get('priority', 9))


def prompts(tri, have):
    return [p for p in tri.get('open_prompts') or [] if set(p.get('show_when') or []) & set(have)]


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
        if lint:
            return f'- 区分：A {name}。lint の {lint} が確かめる（レビュアーは答えない）' + (f'。規則が見ない残り（規則の案：{prop}）は、規則ができるまで書き手の自己点検で確かめる' if prop else '')
        return f'- 区分：A {name}。答えを決める規則はまだ無い（案：{prop}）。規則ができるまでは、書き手の自己点検で確かめる'
    if c == 'B':
        return f'- 区分：B {name}（提出前のチェックリストで、書き手が確かめる。レビュアーは答えない）'
    if c == 'C':
        cond = '・'.join(tri['conditions'][x]['label'] for x in q['show_when'])
        warn = ''.join(f'。{_lint_ref(r)} の warn が出たときも出す' for r in q.get('show_on_lint') or [])
        return f'- 区分：C {name}（レビュアーが答える。優先 {q["priority"]}。出す条件：{cond}{warn}）'
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


def short_list_text(tri, root=ROOT):
    import review_check
    parsed = review_check.parse_questions(_read(os.path.join(root, PERSP)))
    text_of = {q['id']: q['text'] for q in parsed}
    see_of = {q['id']: q['fields'].get('見る欄', '') for q in parsed}
    qs = tri['questions']
    n = {c: sum(1 for q in qs if q['class'] == c) for c in 'ABCD'}
    cq = [q for q in qs if q['class'] == 'C']
    default = [q for q in cq if q['priority'] in tri['budget']['default_priorities']]
    b = tri['budget']
    L = [f'<!-- template_version: {_version(root)} -->',
         '# 人に渡す短い一覧（レビュアーが答える問い）',
         '',
         '<!-- このファイルは python tools/review_triage.py --write が templates/review/triage.yaml から作る。手で直さない -->',
         '',
         f'設計書の PR をレビューする人が答える問いは、ここにあるものだけです。観点書（[perspectives.md](perspectives.md)）の {len(qs)} 問を 1 問ずつ振り分け'
         f'（[triage.yaml](triage.yaml)）、人でなければ判断できない {n["C"]} 問だけを残しました。そこから、設計の性質に当たるものを、優先の順に出します。',
         '',
         '- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施',
         f'- **1 回の量の目安**：{b["questions"][0]}〜{b["questions"][1]} 問、{b["minutes"][0]}〜{b["minutes"][1]} 分。筆者の提案です（追跡 #56）。'
         '人のレビュアーで確かめるのは #20 で、それまでは目安にとどめてください。' + b['note'],
         '- 区分・優先・出す条件は、どれも筆者の提案です（追跡 #56）。根拠にしたパイロット（#9）の数は [research/template-design/triage-evidence.md](../../research/template-design/triage-evidence.md) にあります',
         '- 「漏れゼロ」は約束しません。パイロットでは、人の判断が要る Major の指摘の半分が、問いの一覧の外から出ました。そのため、問いのほかに「開いた問い」（4.）を置いています',
         '',
         '<a id="not-here"></a>',
         '',
         '## 0. ここに無い問いの行き先',
         '',
         '| 区分 | 数 | 誰が確かめるか |',
         '| --- | --- | --- |',
         f'| A 機械 | {n["A"]} | claim_lint（[RULES.md](../../tools/claim_lint/RULES.md)）。レビュアーは、設計書の 1. に貼られた結果で error が 0 であることだけを見る（手順の段 0）。'
         f'うち {sum(1 for q in qs if q["class"] == "A" and not q.get("lint"))} 問は規則がまだ無く、{sum(1 for q in qs if q["class"] == "A" and q.get("lint") and q.get("proposed"))} 問は規則が一部しか見ない。'
         'この分は、規則ができるまで書き手の自己点検にも置く（6.） |',
         f'| B 書き手の自己点検 | {n["B"]} | 書き手が、提出前のチェックリスト（PR のテンプレート `.github/PULL_REQUEST_TEMPLATE/design_doc.md`）で確かめる。レビュアーは、チェックリストで印の無い行（書き手が「満たさない」「当てはまらない」とした行）だけを読む |',
         f'| C 人の判断 | {n["C"]} | レビュアー。この文書（既定で出すのは優先 1・2 の {len(default)} 問のうち、設計の性質に当たるもの） |',
         f'| D 専門家 | {n["D"]} | レビュアーは答えず、[escalation.md](escalation.md) の基準に当たる行を回す（5.） |',
         '',
         '<a id="traits"></a>',
         '',
         '## 1. 先に、設計の性質を読む',
         '',
         '問いは、設計の性質に当たるものだけを出します。性質は、台帳・目録・ホップ・カタログへの回答から機械で読めます。',
         '',
         '```',
         'python tools/review_triage.py --design <設計書のディレクトリ>   # 性質と、出す問いの一覧',
         '```',
         '',
         'エディターのレビューモード（`docs/claims/`）の「観点のチェックリスト」は、開いている設計書から同じ性質を読み、既定でこの一覧を出します。',
         '',
         '| 性質 | 読み方 | 出る問い（優先 1・2） | 出る開いた問い |',
         '| --- | --- | --- | --- |']
    for cid, c in tri['conditions'].items():
        nq = sum(1 for q in default if cid in q['show_when'])
        npr = sum(1 for p in tri['open_prompts'] if cid in p['show_when'])
        L.append(f'| {c["label"]} | {c["read"]} | {nq} | {npr} |')
    L += ['',
          '条件を 2 つ以上持つ問いは、どれか 1 つに当たれば出ます（上の表では、それぞれの行で数えています）。',
          '',
          '<a id="questions"></a>',
          '',
          '## 2. 問い（読む単位ごと）',
          '',
          'どの問いも、Yes／No では足りません。**自分の言葉で答えを 1 行書けるか**を確かめ、書けない・設計書から読み取れないなら指摘にします。'
          '問い ID は観点書の ID で、No のときの重大度の目安・根拠は観点書にあります。「見る欄」は、答えを探すために開く設計書の節（`template:…`）と台帳の列（`registry:…`）です。']
    for unit in UNITS:
        rows = sorted((q for q in default if q['unit'] == unit), key=lambda q: q['priority'])
        L += ['', f'<a id="unit-{unit}"></a>', '', f'### {tri["units"][unit]}', '', '| 優先 | 問い ID | 問い | 見る欄 | 出す条件 |', '| --- | --- | --- | --- | --- |']
        for q in rows:
            L.append(f'| {q["priority"]} | `{q["id"]}` | {q["ask"]} | {see_of[q["id"]]} | {_cond_labels(tri, q["show_when"])} |')
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
            L.append(f'| {_lint_ref(r)} | `{q["id"]}` | {q["ask"]} |')
    L += ['',
          '<a id="open-prompts"></a>',
          '',
          '## 4. 開いた問い（要求と運用から辿る）',
          '',
          '問いの一覧の内側だけを見ていると、見つからないものがあります。次の問いは Yes／No で答えず、要求の文と運用の場面から自分で辿って、気づいたことを指摘にします（出どころは「テンプレート外」か「カタログ外の質問」）。',
          f'1 つにつき 2〜3 分、合わせて 15 分ほどを、2. の問いとは別に取ります（筆者の提案。追跡 #56）。',
          '',
          '| ID | 辿ること | 出す条件 |',
          '| --- | --- | --- |']
    for p in tri['open_prompts']:
        L.append(f'| {p["id"]} | {p["ask"]} | {_cond_labels(tri, p["show_when"])} |')
    L += ['',
          'これらは、パイロット（#9）で問いの一覧の外から出た Major の指摘を元に作りました。同じ設計で作って同じ設計で確かめた問いなので、別の設計でも効くかは分かっていません（triage-evidence.md の 3.）。',
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
    rest = [q for q in cq if q['priority'] not in tri['budget']['default_priorities']]
    L += ['',
          '<a id="more"></a>',
          '',
          f'## 7. 詳しく見る（優先 3。既定では出さない {len(rest)} 問）',
          '',
          '時間が残ったとき、または 2. の問いに答える中で気になったときに見ます。',
          '',
          '| 問い ID | 問い | 当たる設計 |',
          '| --- | --- | --- |']
    for q in rest:
        L.append(f'| `{q["id"]}` | {q["ask"]} | {_cond_labels(tri, q["show_when"])} |')
    L += ['',
          '根拠：筆者の提案：問いの区分・優先・出す条件・1 回の量の目安（追跡 #56）、templates/CONTRIBUTING.md の 2.・3.、research/template-design/pilot.md の 9.',
          '']
    return '\n'.join(L)


def pr_template_text(tri, root=ROOT):
    import review_check
    text_of = {q['id']: q['text'] for q in review_check.parse_questions(_read(os.path.join(root, PERSP)))}
    qs = tri['questions']
    b_always = [q for q in qs if q['class'] == 'B' and not q.get('when')]
    interim = [q for q in qs if q['class'] == 'A' and q.get('interim') == 'B']
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
         f'観点書（`templates/review/perspectives.md`）の問いのうち、書き手が自分の設計書を開けば確かめられるもの（区分 B の {sum(1 for q in qs if q["class"] == "B")} 問と、'
         f'機械で確かめる規則がまだ無い・足りない {len(interim)} 問）です。レビュアーは、ここの問いには答えません。',
         '満たすものに印を付け、満たさない・当てはまらない問いは、印を付けずに行の末尾に理由を書いてください。レビュアーは、印の無い行だけを読みます。',
         '区分と理由は `templates/review/triage.yaml`、問いの見る欄は観点書にあります。量と分け方は筆者の提案です（追跡 #56）。',
         '',
         '### どの設計でも',
         '']
    L += [f'- [ ] `{q["id"]}` {text_of[q["id"]]}' for q in b_always]
    conds = []
    for q in qs:
        for c in q.get('when') or []:
            if q['class'] == 'B' and c not in conds:
                conds.append(c)
    for c in conds:
        L += ['', f'### 当てはまるときだけ：{tri["conditions"][c]["label"]}', '']
        L += [f'- [ ] `{q["id"]}` {text_of[q["id"]]}' for q in qs if q['class'] == 'B' and c in (q.get('when') or [])]
    L += ['', '### lint の規則ができるまで（規則ができたら、ここから外す）', '']
    for q in interim:
        cond = f'（当てはまるときだけ：{_cond_labels(tri, q["when"])}）' if q.get('when') else ''
        part = '（lint が一部を見る。残り：' + '；'.join(tri['proposed_rules'][r]['rule'] if r.startswith('N') else f'未実装の {r}' for r in q['proposed']) + '）' if q.get('lint') else ''
        L.append(f'- [ ] `{q["id"]}` {text_of[q["id"]]}{cond}{part}')
    L += ['',
          '## レビュアーへ',
          '',
          '人が答える問いは `templates/review/short_list.md` にあります（`python tools/review_triage.py --design <ディレクトリ>` で、この設計に当たる問いが出ます）。',
          '']
    return '\n'.join(L)


COUNTS_RE = re.compile(r'(<!-- triage-counts:begin -->\n).*?(<!-- triage-counts:end -->)', re.S)


def readme_text(tri, text):
    """templates/review/README.md with the table of the classes between the triage-counts markers."""
    c = counts(tri)
    rows = ['| 区分 | 問いの数 | 行き先 |', '| --- | --- | --- |',
            f'| A 機械 | {c["A"]}（既存の規則が確かめる {c["A_with_rule"]}、規則が一部を確かめる {c["A_partial_rule"]}、規則がまだ無い {c["A_without_rule"]}） | claim_lint。規則が無い・足りない間は書き手の自己点検にも置く |',
            f'| B 書き手の自己点検 | {c["B"]} | 提出前のチェックリスト（PR のテンプレート） |',
            f'| C 人の判断 | {c["C"]}（優先 1：{c["C_priority_1"]}、優先 2：{c["C_priority_2"]}、優先 3：{c["C_priority_3"]}） | short_list.md（既定で出すのは優先 1・2 のうち、設計の性質に当たるもの） |',
            f'| D 専門家 | {c["D"]} | escalation.md |',
            f'| 計 | {c["total"]} | 開いた問いは、このほかに {c["open_prompts"]} 個 |']
    return COUNTS_RE.sub(lambda m: m.group(1) + '\n'.join(rows) + '\n' + m.group(2), text)


def generated(tri, root=ROOT):
    """{relative path: text} of the files made from triage.yaml."""
    return {PERSP: perspectives_text(tri, _read(os.path.join(root, PERSP))),
            SHORT: short_list_text(tri, root),
            PR_TEMPLATE: pr_template_text(tri, root),
            README: readme_text(tri, _read(os.path.join(root, README)))}


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

    def implemented(rule):
        return review_check.resolve(root, 'lint:' + rule, planned) is None

    def conds_ok(where, key, vals, need=True):
        if need and not vals:
            errors.append(('T4', where, f'{key} が空'))
        for v in vals or []:
            if v not in conds:
                errors.append(('T6' if key == 'when' else 'T4', where, f'{key} の {v} は conditions に無い'))
            used_conds.add(v)

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
            for r in prop:
                if str(r).startswith('N'):
                    used_n.add(r)
                    if r not in props:
                        errors.append(('T3', where, f'proposed の {r} が proposed_rules に無い'))
                elif implemented(r):
                    errors.append(('T3', where, f'proposed の {r} は実装済み（lint に書く）'))
                elif 'lint:' + r not in planned:
                    errors.append(('T3', where, f'proposed の {r} は planned_items.yaml に無い（新しい案は N<番号> で proposed_rules に書く）'))
            if prop and q.get('interim') != 'B':
                errors.append(('T3', where, '規則の案がある A の問い（規則が無い・一部しか見ない）には interim: B（規則ができるまで書き手の自己点検）が要る'))
            if not prop and q.get('interim'):
                errors.append(('T3', where, '既存の規則が答えを決める問いに interim は書かない'))
        if c == 'C':
            if q.get('priority') not in (1, 2, 3):
                errors.append(('T4', where, 'priority は 1・2・3'))
            if q.get('unit') not in UNITS:
                errors.append(('T4', where, f'unit は {"・".join(UNITS)}'))
            conds_ok(where, 'show_when', q.get('show_when'))
            if not str(q.get('ask') or '').strip():
                errors.append(('T4', where, 'ask（人に渡す問いの文）が空'))
            for r in q.get('show_on_lint') or []:
                if not implemented(r):
                    errors.append(('T4', where, f'show_on_lint の {r} は RULES.md に無い'))
        elif q.get('show_when') or q.get('ask') or q.get('priority'):
            errors.append(('T4', where, 'show_when・ask・priority は C の問いだけに書く'))
        if c == 'D' and q.get('escalation') not in criteria:
            errors.append(('T5', where, f'escalation の {q.get("escalation")!r} は escalation.md の基準に無い'))
        if c in ('A', 'B'):
            conds_ok(where, 'when', q.get('when'), need=False)
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
        if not str(p.get('ask') or '').strip() or not p.get('from'):
            errors.append(('T7', where, 'ask と from（元にした指摘）が要る'))
        if not p.get('show_when'):
            errors.append(('T7', where, 'show_when が空'))
        for v in p.get('show_when') or []:
            if v not in conds:
                errors.append(('T7', where, f'show_when の {v} は conditions に無い'))
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


def counts(tri):
    qs = tri['questions']
    out = {'total': len(qs)}
    for c in 'ABCD':
        out[c] = sum(1 for q in qs if q['class'] == c)
    out['A_with_rule'] = sum(1 for q in qs if q['class'] == 'A' and q.get('lint') and not q.get('proposed'))
    out['A_partial_rule'] = sum(1 for q in qs if q['class'] == 'A' and q.get('lint') and q.get('proposed'))
    out['A_without_rule'] = sum(1 for q in qs if q['class'] == 'A' and not q.get('lint'))
    for p in (1, 2, 3):
        out[f'C_priority_{p}'] = sum(1 for q in qs if q['class'] == 'C' and q['priority'] == p)
    out['open_prompts'] = len(tri['open_prompts'])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--root', default=ROOT)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--counts', action='store_true')
    ap.add_argument('--design', metavar='DIR', help='print the traits of a design and the short list for it')
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
        out += [f'{k}: {v}' for k, v in counts(tri).items()]
    if a.design:
        have = traits(load_design(a.design))
        qs, ps = selected(tri, have), prompts(tri, have)
        import review_check
        see_of = {q['id']: q['fields'].get('見る欄', '') for q in review_check.parse_questions(_read(os.path.join(a.root, PERSP)))}
        out.append('性質：' + '・'.join(tri['conditions'][c]['label'] for c in tri['conditions'] if c in have and c != 'always'))
        out.append(f'問い：{len(qs)}（全 {len(tri["questions"])} 問のうち、人の判断が要る {counts(tri)["C"]} 問から）  開いた問い：{len(ps)}')
        for unit in UNITS:
            out.append(f'■ {tri["units"][unit]}')
            out += [f'  [{q["priority"]}] {q["id"]}  {q["ask"]}\n        見る欄：{see_of[q["id"]]}' for q in qs if q['unit'] == unit]
        out.append('■ 開いた問い')
        out += [f'  {p["id"]}  {p["ask"]}' for p in ps]
    if a.check or not (a.write or a.counts or a.design):
        errs = check(a.root)
        out += [f'{r}  {w}  {m}' for r, w, m in errs] + [f'error {len(errs)}', 'FAIL' if errs else 'OK']
        code = 1 if errs else code
    sys.stdout.buffer.write(('\n'.join(out) + '\n').encode('utf-8'))
    return code


if __name__ == '__main__':
    sys.exit(main())
