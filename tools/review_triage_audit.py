# -*- coding: utf-8 -*-
"""Audit of the triage (#56): does the cited lint rule really decide the question?

For every question that templates/review/triage.yaml gives to the machine alone (class A, `lint` and no `proposed`),
a copy of a worked example is changed so that the answer to the question becomes No, and claim_lint must then report
one of the cited rules (an error or a warning that the unchanged copy does not have). A question whose mutation is not
reported is not decided by the rule and must leave "decided by an existing rule" (the independent check of PR #71 found
five such questions by this test).

  python tools/review_triage_audit.py            # run, print the table, exit 1 when a question is not decided
  python tools/review_triage_audit.py --write    # also write research/template-design/triage-audit.md

What this does not show:
  - the other direction. Only "No gives a finding" is tested, not "Yes gives none": a rule that warns whenever the
    row exists (L18 on a deprecated claim that is still read) passes this test although it only points at the place to
    look and does not tell Yes from No (the re-check of PR #71 found q-deprecated-deadline this way)
  - that the rule sees every way the answer can be No (one mutation per question, chosen by the author of the triage;
    the re-check found, with other mutations, a part of ap-2-9 and q-internal-delegation-token that no rule sees)
  - that the receiver does what is declared (RULES.md: the rules compare declarations)
"""
import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile

import yaml

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import review_triage  # noqa: E402

RECORD = os.path.join('research', 'template-design', 'triage-audit.md')
BASES = {'B': 'templates/examples/scenario-b', 'A': 'templates/examples/scenario-a', 'pilot-B': 'research/pilot/scenario-b'}
FILES = ('claims', 'token_types', 'hops', 'catalog_answers')


def row(d, name, key, rid):
    return next(r for r in d[name][key] if r.get('id') == rid)


def c(d, rid):
    return row(d, 'claims', 'claims', rid)


def t(d, rid):
    return row(d, 'token_types', 'token_types', rid)


def h(d, rid):
    return row(d, 'hops', 'hops', rid)


def _volatile(d):
    r = c(d, 'C-department')
    r['volatility'] = 10
    r.pop('on_revoke', None)
    r.pop('recompute_trigger', None)


def _unstable(d):
    c(d, 'C-user-id')['identifier_properties']['stable'] = False


def _email_key(d):
    c(d, 'C-email')['usage'] = 'identifier'


def _self_asserted(d):
    c(d, 'C-roles')['provenance'] = '本人が編集できる値'


def _writer_end_user(d):
    c(d, 'C-roles')['authoritative_writer'][0]['configurable_by'] = ['end_user']


def _no_max_items(d):
    r = c(d, 'C-roles')
    r.pop('max_items', None)
    r.pop('overflow_strategy', None)


def _not_rejected(d):
    c(d, 'C-roles')['on_missing'] = '無視'


def _two_writers(d):
    w = c(d, 'C-roles')['authoritative_writer']
    w.append(dict(w[0], writer='別の書き手（同じ段階）'))


def _blank_required(d):
    c(d, 'C-roles').pop('description', None)


def _strip_off(d):
    hop = next(x for x in d['hops']['hops'] if x.get('forwarded_headers'))
    hop['forwarded_headers'][0]['strip_inbound'] = False


def _no_namespace(d):
    c(d, 'C-task-id')['namespace'] = None


def _confidential(d):
    c(d, 'C-roles')['confidential_from'] = ['gateway']


def _oversize(d):
    c(d, 'C-roles')['max_bytes'] = 200000


def _wider_scope(d):
    h(d, 'H4')['scope'].append('admin.write')


def _longer_life(d):
    h(d, 'H4')['max_lifetime'] = 3600


def _not_upstream(d):
    h(d, 'H4')['custom_claims'].append('C-task-id')


def _roles_unenforced(d):
    c(d, 'C-roles').pop('enforced_at', None)


def _alg_none(d):
    t(d, 'KC_AT')['alg_allowlist'] = ['RS256', 'none']


def _aud_optional(d):
    t(d, 'KC_AT')['required_claims'].remove('aud')


def _no_tenant_binding(d):
    t(d, 'AT').pop('tenant_binding', None)


def _no_key_source(d):
    t(d, 'KC_AT').pop('key_source', None)


def _skew(d):
    t(d, 'KC_AT')['max_clock_skew'] = 900


def _jwe_no_inner(d):
    r = t(d, 'KC_AT')
    r['jwe'] = {'used': True, 'recipients': [{'recipient': 'gateway', 'key_ref': 'gateway の鍵'}]}


def _rt_no_idle(d):
    t(d, 'RT').pop('idle_timeout', None)


def _public_plain_rt(d):
    d['token_types']['issuance_profile']['client_type']['value'] = 'public'
    t(d, 'RT')['rt_rotation'] = {'rotation': False, 'reuse_detection': 'no'}


def _no_unknown_kid(d):
    t(d, 'KC_AT').pop('unknown_kid', None)


def _many_items(d):
    c(d, 'C-roles')['max_items'] = 500


# mutation: (base design, function, what was changed)
MUTATIONS = {
    'volatile': ('B', _volatile, 'C-department の volatility を 10 秒にし、対策（on_revoke・recompute_trigger）を消す'),
    'unstable-id': ('B', _unstable, 'C-user-id の identifier_properties.stable を false にする'),
    'email-key': ('B', _email_key, 'C-email の usage を identifier にする'),
    'self-asserted': ('B', _self_asserted, 'C-roles の provenance を「本人が編集できる値」にする'),
    'writer-end-user': ('B', _writer_end_user, 'C-roles の書き手の configurable_by を end_user にする'),
    'no-max-items': ('B', _no_max_items, 'C-roles の max_items・overflow_strategy を消す'),
    'not-rejected': ('B', _not_rejected, '必須の C-roles の on_missing を「無視」にする'),
    'two-writers': ('B', _two_writers, 'C-roles の同じ段階に書き手をもう 1 つ足す'),
    'blank-required': ('B', _blank_required, 'C-roles の description を消す'),
    'strip-off': ('pilot-B', _strip_off, 'ヘッダーに写すホップの strip_inbound を false にする'),
    'no-namespace': ('B', _no_namespace, '登録名でない C-task-id の namespace を null にする'),
    'confidential': ('B', _confidential, 'C-roles の confidential_from に gateway を足す（KC_AT は gateway に見える）'),
    'oversize': ('B', _oversize, 'C-roles の max_bytes を 200000 にする'),
    'wider-scope': ('B', _wider_scope, 'H4 の scope に、上流に無い admin.write を足す'),
    'longer-life': ('B', _longer_life, 'H4 の max_lifetime を、上流より長い 3600 秒にする'),
    'not-upstream': ('B', _not_upstream, 'H4 の custom_claims に、上流に無い C-task-id を足す'),
    'roles-unenforced': ('B', _roles_unenforced, 'C-roles の enforced_at を消す'),
    'alg-none': ('B', _alg_none, 'KC_AT の alg_allowlist に none を足す'),
    'aud-optional': ('B', _aud_optional, 'KC_AT の required_claims から aud を外す'),
    'no-tenant-binding': ('A', _no_tenant_binding, 'AT の tenant_binding を消す'),
    'no-key-source': ('B', _no_key_source, 'KC_AT の key_source を消す'),
    'skew': ('B', _skew, 'KC_AT の max_clock_skew を 900 秒にする'),
    'jwe-no-inner': ('B', _jwe_no_inner, 'KC_AT を JWE にし、ネストの宣言（sign_then_encrypt）を書かない'),
    'rt-no-idle': ('B', _rt_no_idle, 'RT の idle_timeout を消す'),
    'public-plain-rt': ('B', _public_plain_rt, 'クライアントを public にし、RT のローテーションと再利用の検知を外す'),
    'no-unknown-kid': ('B', _no_unknown_kid, 'KC_AT の unknown_kid を消す'),
    'many-items': ('B', _many_items, 'C-roles の max_items を 500 にする'),
}

# question -> the mutation that makes its answer No (the rules that must report are the question's `lint` in triage.yaml)
AUDIT = {
    'dc-01': 'volatile', 'pa-02': 'volatile', 'ap-2-2': 'volatile', 'cf-01': 'two-writers',
    'dc-09': 'unstable-id', 'pa-12': 'unstable-id', 'ap-1-6': 'email-key',
    'dc-10': 'self-asserted', 'q-writer-distinguished': 'self-asserted', 'cd-04': 'self-asserted', 'pa-11': 'writer-end-user',
    'dc-11': 'no-max-items', 'pa-13': 'no-max-items', 'ap-2-1': 'many-items',
    'dc-12': 'not-rejected', 'cf-02': 'not-rejected', 'q-hook-failure': 'not-rejected', 'q-consumer-expression': 'roles-unenforced',
    'dc-gate': 'blank-required', 'pa-15': 'two-writers', 'q-single-issuer': 'two-writers',
    'pa-17': 'strip-off', 'cf-08': 'strip-off', 'ap-2-5': 'strip-off',
    'ap-2-4': 'no-namespace', 'q-payload-readable': 'confidential', 'q-confidential-reaches-reader': 'confidential',
    'q-size-limit': 'oversize',
    'cf-05': 'wider-scope', 'q-hop-narrowing': 'wider-scope', 'q-hop-lifetime': 'longer-life', 'q-claim-earliest-hop': 'not-upstream',
    'ap-1-1': 'alg-none', 'ap-1-3': 'aud-optional', 'ap-1-4': 'no-tenant-binding', 'ap-1-5': 'no-key-source', 'ap-1-8': 'skew',
    'q-nested-jwt-both-layers': 'jwe-no-inner', 'q-session-rt-bounds': 'rt-no-idle', 'q-rt-policy-by-client': 'public-plain-rt',
    'q-key-rotation': 'no-unknown-kid',
}


def lint(design_dir):
    """{rule: number of errors and warnings} of claim_lint on a design directory."""
    p = subprocess.run([sys.executable, os.path.join(TOOLS, 'claim_lint'), design_dir, '--format', 'json'], capture_output=True)
    data = json.loads(p.stdout.decode('utf-8'))
    out = {}
    for f in data['findings']:
        if f['severity'] in ('error', 'warn'):
            out[f['rule']] = out.get(f['rule'], 0) + 1
    return out


def _copy(base, tmp, name, fn=None):
    dst = os.path.join(tmp, name)
    shutil.copytree(os.path.join(ROOT, BASES[base]), dst, ignore=shutil.ignore_patterns('reviews', 'schemas'))
    d = {}
    for f in FILES:
        with open(os.path.join(dst, f + '.yaml'), encoding='utf-8') as fh:
            d[f] = yaml.safe_load(fh)
    if fn:
        fn(d)
    for f in FILES:   # written back also when unchanged, so that the base and the mutation differ only by the change
        with open(os.path.join(dst, f + '.yaml'), 'w', encoding='utf-8', newline='\n') as fh:
            yaml.safe_dump(d[f], fh, allow_unicode=True, sort_keys=False)
    return dst


def run(only=None):
    """[{question, rules, mutation, change, base, reported: {rule: +n}, ok}] for the questions decided by a rule alone."""
    tri = review_triage.load(ROOT)
    decided = [q for q in tri['questions'] if q['class'] == 'A' and q.get('lint') and not q.get('proposed')]
    missing = [q['id'] for q in decided if q['id'] not in AUDIT]
    extra = [i for i in AUDIT if i not in {q['id'] for q in decided}]
    if missing or extra:
        raise SystemExit(f'review_triage_audit: AUDIT does not match triage.yaml (no mutation: {missing}; not decided by a rule alone: {extra})')
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        base, result = {}, {}
        for q in decided:
            if only and q['id'] not in only:
                continue
            name = AUDIT[q['id']]
            b, fn, change = MUTATIONS[name]
            if b not in base:
                base[b] = lint(_copy(b, tmp, 'base-' + b))
            if name not in result:
                result[name] = lint(_copy(b, tmp, 'm-' + name, fn))
            # SCHEMA: a value the schema forbids is also reported by the machine (before the rule runs)
            reported = {r: result[name].get(r, 0) - base[b].get(r, 0) for r in list(q['lint']) + ['SCHEMA']}
            reported = {r: n for r, n in reported.items() if n > 0}
            rows.append({'question': q['id'], 'rules': q['lint'], 'mutation': name, 'change': change, 'base': BASES[b],
                         'reported': reported, 'ok': bool(reported)})
    return rows


def record(rows):
    ok = sum(1 for r in rows if r['ok'])
    L = ['# 振り分けの点検：引いた lint の規則は、問いの答えを本当に決めるか（#56）',
         '',
         '> **道具による確かめ。人による点検ではない。** `python tools/review_triage_audit.py --write` が書く。手で直さない。',
         '',
         '`templates/review/triage.yaml` で「既存の規則が答えを決める（レビュアーも書き手も答えない）」とした問いを、1 問ずつ確かめた記録です。',
         '記入例の写しを、その問いの答えが No になるように 1 か所書き換え、claim_lint が、引いた規則の error か warn を新しく出すかを見ます'
         '（PR #71 の独立点検が使った確かめ方。そこで 5 問が外れた）。出さなければ、その規則は問いを決めていないので、この区分から外します。',
         '',
         f'- 結果：{len(rows)} 問のうち {ok} 問で、規則が指摘を出した' + ('' if ok == len(rows) else f'。**出さなかった {len(rows) - ok} 問は、区分を直す必要がある**'),
         '- 分かること：その書き換えを、規則が拾うこと',
         '- 分からないこと：答えが No になる書き方の全部を規則が拾うか（1 問につき書き換えは 1 つで、振り分けを書いた側が選んだ）。受け手が宣言どおりに動くか（規則は宣言どうしを比べるだけ。`tools/claim_lint/RULES.md`）',
         '- **確かめているのは「No にしたら指摘が出る」の向きだけ**。「Yes なら指摘が出ない」は確かめていない。行があるだけで出る warn（見る場所を知らせるだけの規則）は、この確かめを通ってしまう。再点検（PR #71）が、別の書き換えで 3 問をこの区分から外した（下の表）',
         '- 「SCHEMA」は、スキーマがその値を許さず、規則の手前で機械が止めたもの',
         '- `tools/tests/test_review_triage.py` が同じ確かめを走らせる（区分を変えて、書き換えの無い問いができると落ちる）',
         '',
         '| 問い | 引いた規則 | 書き換え（答えを No にする） | 元の記入例 | 新しく出た指摘 | 判定 |',
         '| --- | --- | --- | --- | --- | --- |']
    for r in rows:
        rep = '・'.join(f'{k} +{n}' for k, n in r['reported'].items()) or '無し'
        L.append(f'| `{r["question"]}` | {"・".join(r["rules"])} | {r["change"]} | `{r["base"]}` | {rep} | {"決める" if r["ok"] else "**決めない**"} |')
    L += ['',
          '## この確かめで区分を直した問い',
          '',
          '独立点検（PR #71）と、この確かめで、「既存の規則が決める」から外した問いです。',
          '',
          '| 問い | 前 | 後 | 理由 |',
          '| --- | --- | --- | --- |',
          '| `q-hook-adds-raw-pii` | A（L70） | A・規則なし（案 N14）。書き手の自己点検 | L70 は名前からの推測との食い違いだけを見る。フックが書く行の pii_category を書き換えても指摘が増えない |',
          '| `pa-trace` | A（L72） | B | L72 は回答の有無と「対象：」だけ。台帳の rationale と同じことを言うかは見ない |',
          '| `pa-20` | A（L70・L6） | B | 25 問の回答の文と台帳の一致は、規則が見ない（`pa-06` と同じ扱いにそろえた） |',
          '| `q-unwrapped-value-authz` | A（L67） | A・一部（案 N15）。書き手の自己点検 | L67 はヘッダーへの写しだけを見る |',
          '| `dc-09`・`pa-12` | A（L3） | A（L3）＋残りは `q-value-vocabulary`（どの設計でも出す） | L3 は名前と識別子の性質を見て、値が名前かは見ない |',
          '| `q-hop-narrowing` | A（L16） | A（L16）＋残りは `q-no-passthrough` | 交換を担うサービスが規則を強制する設定は、L16 が見ない |',
          '| `q-auth-context-semantics` | C | A・規則なし（案 N16）。書き手の自己点検 | 行の usage・enforced_at の値でほぼ決まる |',
          '| `q-relies-on-at-expiry` | B | C（`q-revocation-delivery` にまとめた） | 自分の前提を自分で疑う問いで、書き手の自己点検に向かない |',
          '| `q-deprecated-deadline` | A（L18） | A・一部（案 N17）。書き手の自己点検 | 再点検：L18 は、廃止予定の行を読む受け手がいれば必ず出る。期日・代わりの行があっても出るので、答えを決めていない。この道具の確かめ（No の向きだけ）は通っていた |',
          '| `ap-2-9`・`q-internal-delegation-token` | A（L17・L9・R1） | A・一部（案 N18）。書き手の自己点検 | 再点検：`log_policy` を消しても指摘が増えない。「ログに残るか」は、どの規則も見ない |',
          '| `ap-1-3`・`q-txn-scope-fixed` | A（L27）／A（L11） | 引く規則に L11／L16 を足した | 再点検：問いの後半を No にすると出るのは、引いていなかった規則だった |',
          '| `q-agent-delegation-claims` | A（L12） | A・一部（案 N24）。書き手の自己点検 | 初回の測定（#12）の A01：入れ子の act で行為者を照合すると、照合の文（`enforced_at`・`validates`）にだけ書くと、L12 は見ない（#80）。書き換えの確かめは外した。規則ができたら、書き換えを足して戻す |',
          '| `cf-06`・`q-txn-scope-fixed` | A（L43）／A（L11・L16） | A・一部（案 N25）。書き手の自己点検 | 初回の測定の B03・B05：ホップの文に書いた Authorization での送り方と、ホップで受けるのに `consumers` に無い受け手は、L43・L11 が見ない（#80）。書き換えの確かめは外した。規則ができたら、書き換えを足して戻す |',
          '']
    return '\n'.join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args(argv)
    rows = run()
    text = record(rows)
    if a.write:
        with open(os.path.join(ROOT, RECORD), 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
    bad = [r for r in rows if not r['ok']]
    out = [f'{r["question"]}\t{"・".join(r["rules"])}\t{r["mutation"]}\t{r["reported"] or "NOT REPORTED"}' for r in rows]
    out.append(f'questions {len(rows)}  decided {len(rows) - len(bad)}  not decided {len(bad)}')
    sys.stdout.buffer.write(('\n'.join(out) + '\n').encode('utf-8'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
