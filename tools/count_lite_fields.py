# -*- coding: utf-8 -*-
"""Count the hand-written fields of a worked example, before and after the reduced Lite proposed at gate 1 (#16).

  python tools/count_lite_fields.py [EXAMPLE_DIR]      (default: templates/examples/scenario-a)

Prints a Markdown table (research/template-design/gate1.md section 10 is generated from it).

Counting rule: in each YAML row, every key except `id` whose value is not null counts as one field (an explicit
empty list such as `consumers: []` is a written answer and counts; `namespace: null` does not). Nested values
(`refs`, `enforced_at`, `authoritative_writer`) count as one field. The reduced Lite rules are the constants below;
they are a proposal (author-proposal, tracking #16), not yet the Lite definition of #4.

  python tools/count_lite_fields.py --current EXAMPLE_DIR --profile lite|full

counts the fields the writer of a worked example writes by hand today (all columns of registry v1, not the v0 subset;
templates/README.md 「記入の目安」, #4). Same counting rule. lite applies the reduced Lite of templates/README.md (the
generated columns and sections are not counted; issuance_profile counts only the items that leave the default combination;
hops count only exchange / reissue hops; an inherited 対象外 answer counts one field). full counts every written field.
Both add the hand-written questions of every claim_request_*.md (rows whose last column is 手書き) and the hand-written
sections of design.md (00_core: lite 2, 3, 6, 9, 12; full also 7).
"""
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from claim_lint import core  # noqa: E402

# carried claim rows that someone reads: generated from the IdP module, the catalogue and token_types
GENERATED_CARRIED = {'issue_events', 'recompute_trigger', 'propagation_delay', 'change_controller', 'status', 'issuers'}
# 既定どおり rows that nobody reads (consumers: []): only what R8 and the decision need
UNREAD_KEEP = {'name', 'namespace', 'type', 'shape', 'decision', 'rationale', 'refs', 'max_bytes', 'pii_category',
               'carried_in'}
# rejected token types: kind, decision, rationale
REJECTED_TT_KEEP = {'kind', 'decision', 'rationale'}
# Split of the 対象外 answers (re-check of PR #31, N3). Inherited from the IdP module: only events that one named
# client switch turns off, with no review or lint finding on the row. The author still writes one field per inherited
# row ("the setting was checked"), so INHERITED_FIELD counts it. Hand-written with assumption and breaks_when: rows
# where a finding occurred (A03: I09, U07; A15: U05; the lint finding U10 and its pair I06), rows that depend on a
# realm or client default the issuance profile cannot show (I08: Keycloak's default offline_access), and use events
# (U05, U08), which no client switch removes.
STRUCTURAL = {
    'I03': 'client policy: the use-lightweight-access-token executor is not applied to the client',
    'I04': 'client setting: Direct access grants OFF',
    'I05': 'client setting: Service accounts roles OFF',
    'I07': 'client setting: OAuth 2.0 Device Authorization Grant OFF',
}
INHERITED_FIELD = 1
# The gate-1 count (research/template-design/gate1.md section 10) was taken on the v0 subset of the catalogue (#16).
# #2 extended the catalogue to I01..I33 / U01..U28; the record stays reproducible by counting only the v0 events.
GATE1_EVENTS = {f'I{n:02d}' for n in range(1, 10)} | {f'U{n:02d}' for n in range(1, 11)}
# design.md sections: example numbering -> handling in the reduced Lite; LITE_4 = the Lite sections of #4 (00_core
# 2, 3, 4, 6, 7, 12), mapped to the example's numbering (2, 3, 6, 8, 9, 12)
DESIGN = {1: 'generated', 2: 'hand', 3: 'hand', 4: 'generated', 5: 'generated', 6: 'hand', 7: 'full-only',
          8: 'generated', 9: 'hand', 10: 'generated', 11: 'generated', 12: 'hand'}
LITE_4 = {2, 3, 6, 8, 9, 12}
# Registry v1 (#3) added columns and the rejected rows of the remaining token kinds to the example. The gate-1 count
# was taken with schema v0, so the record stays reproducible by counting only the v0 columns and the v0 token rows
# (as GATE1_EVENTS does for the catalogue). The v0 columns are those of templates/registry/*.schema.json v0.1.0.
V0_CLAIM_COLUMNS = {'name', 'namespace', 'catalog_refs', 'registered_ref', 'type', 'shape', 'description', 'not_meaning',
                    'decision', 'rationale', 'assumption', 'revisit_trigger', 'refs', 'usage', 'issuers',
                    'authoritative_writer', 'issue_events', 'source_system', 'volatility', 'propagation_delay',
                    'recompute_trigger', 'on_revoke', 'carried_in', 'consumers', 'on_missing', 'enforced_at', 'max_bytes',
                    'max_items', 'typical_items', 'overflow_strategy', 'pii_category', 'log_policy', 'status', 'owner',
                    'change_controller', 'integrity_until', 'evidence', 'note'}
V0_TT_COLUMNS = {'id', 'kind', 'decision', 'rationale', 'purpose', 'issuer', 'aud', 'holder', 'format', 'typ', 'alg_allowlist',
                 'issuers', 'required_claims', 'max_clock_skew', 'max_lifetime', 'lifetime_refs', 'refresh', 'revocation',
                 'stored_at', 'transport', 'key_rotation', 'size', 'note'}
# v0 columns that the v1 migration filled in on rows that had them empty at gate 1 (PR #37 independent check:
# C-scope became space_delimited with max_items; notes on C-scope and C-email-verified)
V1_FILLED = {('C-scope', 'max_items'), ('C-scope', 'note'), ('C-email-verified', 'note')}
# v0 columns that the semantic rules of #6 asked to fill on scenario A (L1a: registered_ref of C-sid; L27: max_clock_skew
# of IDT). Not counted, so that the gate-1 record stays reproducible (tools/claim_lint/RULES.md, design.md 13.)
L6_FILLED = {('C-sid', 'registered_ref')}
L6_TT_FILLED = {('IDT', 'max_clock_skew')}
V0_TT_IDS ={'AT', 'IDT', 'RT', 'CODE', 'BFFSESSION', 'SSO', 'LOGOUT', 'DPOP', 'TXN'}
V0_PROFILE = {'client_type', 'client_auth', 'grants', 'sender_constraint', 'at_format', 'rt_strategy', 'request_protection',
              'conformance_profile'}


def fields(row, skip=('id',)):
    return [k for k, v in row.items() if k not in skip and v is not None]


def count(example):
    claims = core.load_yaml(os.path.join(example, 'claims.yaml'))['claims']
    tts = core.load_yaml(os.path.join(example, 'token_types.yaml'))
    answers = [a for a in core.load_yaml(os.path.join(example, 'catalog_answers.yaml'))['answers'] if a['event'] in GATE1_EVENTS]
    rows = []
    groups = {'read': [0, 0, 0], 'unread': [0, 0, 0], 'rejected': [0, 0, 0]}
    for c in claims:
        f = [k for k in fields(c) if k in V0_CLAIM_COLUMNS and (c['id'], k) not in V1_FILLED | L6_FILLED]
        if c['decision'] == '却下':
            g, after = 'rejected', f
        elif c['decision'] == '既定どおり' and c.get('consumers') == []:
            g, after = 'unread', [x for x in f if x in UNREAD_KEEP]
        else:
            g = 'read'
            after = [x for x in f if x not in GENERATED_CARRIED and not (x == 'overflow_strategy' and c.get('shape') != 'array')]
        groups[g][0] += 1; groups[g][1] += len(f); groups[g][2] += len(after)
    rows.append((f"台帳：載せて誰かが読む行（{groups['read'][0]} 行）", groups['read'][1], groups['read'][2]))
    rows.append((f"台帳：既定どおりで誰も読まない行（{groups['unread'][0]} 行）", groups['unread'][1], groups['unread'][2]))
    rows.append((f"台帳：却下の行（{groups['rejected'][0]} 行）", groups['rejected'][1], groups['rejected'][2]))
    ip = sum(len(fields(v, ())) for k, v in tts['issuance_profile'].items() if k in V0_PROFILE)
    rows.append(('発行方式の選択（既定の組み合わせのまま）', ip, 0))
    tts['token_types'] = [{k: v for k, v in t.items() if k in V0_TT_COLUMNS and (t['id'], k) not in L6_TT_FILLED}
                          for t in tts['token_types'] if t['id'] in V0_TT_IDS]
    ttb = sum(len(fields(t)) for t in tts['token_types'])
    tta = sum(len(fields(t)) if t['decision'] != '却下' else len([k for k in fields(t) if k in REJECTED_TT_KEEP]) for t in tts['token_types'])
    rows.append(('トークン目録', ttb, tta))
    ab = sum(len(fields(a, ())) for a in answers)
    inherited = sorted(a['event'] for a in answers if a['answer'] == '対象外' and a['event'] in STRUCTURAL)
    aa = sum(len(fields(a, ())) for a in answers if not (a['answer'] == '対象外' and a['event'] in STRUCTURAL)) \
        + INHERITED_FIELD * len(inherited)
    hand_oos = sorted(a['event'] for a in answers if a['answer'] == '対象外' and a['event'] not in STRUCTURAL)
    rows.append((f"カタログへの回答（対象外のうち引き継ぐ {len(inherited)} 件：{'・'.join(inherited)}）", ab, aa))
    cr = open(os.path.join(example, 'claim_request_tenant_id.md'), encoding='utf-8').read()
    hand_q = len(re.findall(r'^\| \d+ \|.*\| 手書き \|$', cr, flags=re.M))
    shared = [c['id'] for c in claims if c.get('namespace') and c['decision'] == '採用']
    rows.append((f'追加前の 25 問（共有クレーム {len(shared)} つ × 手で書く {hand_q} 問）', 0, len(shared) * hand_q))
    tb = sum(r[1] for r in rows); ta = sum(r[2] for r in rows)
    hand = sorted(k for k, v in DESIGN.items() if v == 'hand')
    return rows, (tb, ta), hand, hand_oos


# --current (#4): the default issuance combination (templates/registry/README.md 3.3, gate1.md 10.)
DEFAULT_PROFILE = {'client_type': 'confidential', 'grants': ['authorization_code_pkce', 'refresh_token'],
                   'sender_constraint': 'none', 'at_format': 'jwt', 'rt_strategy': 'rotation', 'request_protection': [],
                   'conformance_profile': 'none'}
HAND_SECTIONS = {'lite': [2, 3, 6, 9, 12], 'full': [2, 3, 6, 7, 9, 12]}


def _load(example, name):
    path = os.path.join(example, name + '.yaml')
    return (core.load_yaml(path) or {}) if os.path.isfile(path) else {}


def _row(v):
    return len(fields(v, ())) if isinstance(v, dict) else (0 if v is None else 1)


def _count_section(v):
    """A section of catalog_answers.yaml or an issuance_profile item: every written leaf counts as one field, and a list of
    plain values (a list of IDs, `searched`) counts as one field, like a nested value of a YAML row."""
    if v is None:
        return 0
    if isinstance(v, dict):
        return sum(_count_section(x) for x in v.values())
    if isinstance(v, list):
        if all(not isinstance(x, (dict, list)) for x in v):
            return 1
        return sum(_count_section(x) for x in v)
    return 1


def count_current(example, profile):
    """(rows, total) of the hand-written fields of a worked example under the Lite or Full definition of #4."""
    lite = profile == 'lite'
    claims = _load(example, 'claims').get('claims') or []
    tdoc = _load(example, 'token_types')
    hops = _load(example, 'hops').get('hops') or []
    adoc = _load(example, 'catalog_answers')
    rows = []
    groups = {'read': [0, 0], 'unread': [0, 0], 'rejected': [0, 0]}
    for c in claims:
        f = fields(c)
        if c.get('decision') == '却下':
            g = 'rejected'
        elif c.get('decision') == '既定どおり' and c.get('consumers') == []:
            g = 'unread'
            if lite:
                f = [x for x in f if x in UNREAD_KEEP | {'data_category', 'confidential_from', 'max_items', 'catalog_refs'}]
        else:
            g = 'read'
            if lite:
                f = [x for x in f if x not in GENERATED_CARRIED and not (x == 'overflow_strategy' and c.get('shape') != 'array')]
        groups[g][0] += 1
        groups[g][1] += len(f)
    rows.append((f"台帳：載せて誰かが読む行（{groups['read'][0]} 行）", groups['read'][1]))
    rows.append((f"台帳：既定どおりで誰も読まない行（{groups['unread'][0]} 行）", groups['unread'][1]))
    rows.append((f"台帳：却下の行（{groups['rejected'][0]} 行）", groups['rejected'][1]))
    ip = tdoc.get('issuance_profile') or {}
    if lite:
        off = [k for k, v in ip.items() if k in DEFAULT_PROFILE and isinstance(v, dict) and v.get('value') != DEFAULT_PROFILE[k]]
        off += [k for k in ip if k not in DEFAULT_PROFILE and k != 'client_auth']
        rows.append((f"発行方式の選択（既定から外れた {len(off)} 項目）", sum(_row(ip[k]) for k in off)))
    else:
        rows.append(('発行方式の選択', sum(_row(v) for v in ip.values())))
    tts = tdoc.get('token_types') or []
    rows.append((f'トークン目録（{len(tts)} 行）', sum(
        len([k for k in fields(t) if k in REJECTED_TT_KEEP]) if lite and t.get('decision') == '却下' else len(fields(t))
        for t in tts)))
    hand_hops = [h for h in hops if not lite or h.get('kind') in ('exchange', 'reissue')]
    note = '。交換・作り直しのホップだけ' if lite else ''
    rows.append((f'ホップ（{len(hand_hops)} 行{note}）', sum(len(fields(h)) for h in hand_hops)))
    answers = adoc.get('answers') or []
    inherited = [a for a in answers if a.get('inherit') == 'idp-default']
    rows.append((f'カタログへの回答（{len(answers)} 件。引き継ぎ {len(inherited)} 件は各 1 欄）', sum(
        INHERITED_FIELD if a in inherited else len(fields(a, ())) for a in answers)))
    other = sum(_count_section(v) for k, v in adoc.items() if k != 'answers')
    keys = '・'.join(k for k in adoc if k != 'answers')
    rows.append((f'網羅の節（{keys}）', other))
    hand_q, files = 0, 0
    for n in sorted(os.listdir(example)):
        if n.startswith('claim_request_') and n.endswith('.md'):
            files += 1
            text = open(os.path.join(example, n), encoding='utf-8').read()
            hand_q += len(re.findall(r'^\| \d+ \|.*\| 手書き \|$', text, flags=re.M))
    rows.append((f'追加前の 25 問（{files} ファイルの手書きの問い）', hand_q))
    return rows, sum(r[1] for r in rows)


def main_current(example, profile):
    rows, total = count_current(example, profile)
    out = [f'| 対象（{os.path.basename(os.path.normpath(example))}、{profile}） | 手で書く欄 |', '| --- | --- |']
    out += [f'| {n} | {v} |' for n, v in rows]
    out.append(f'| **YAML と 25 問の欄の計** | **{total}** |')
    sec = '・'.join(map(str, HAND_SECTIONS[profile]))
    out.append(f'| 設計書の手で書く節（00_core の番号） | {len(HAND_SECTIONS[profile])}（{sec}） |')
    sys.stdout.buffer.write(('\n'.join(out) + '\n').encode('utf-8'))
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == '--current':
        profile = argv[argv.index('--profile') + 1] if '--profile' in argv else 'lite'
        if profile not in HAND_SECTIONS or len(argv) < 2:
            sys.stderr.write('usage: count_lite_fields.py --current EXAMPLE_DIR --profile lite|full\n')
            return 2
        return main_current(os.path.abspath(argv[1]), profile)
    example = os.path.abspath(argv[0]) if argv else os.path.join(ROOT, 'templates', 'examples', 'scenario-a')
    rows, (tb, ta), hand, hand_oos = count(example)
    out = ['| 対象 | 今の記入例 | 縮小 Lite | 差 |', '| --- | --- | --- | --- |']
    out += [f'| {n} | {b} | {a} | {a - b:+d} |' for n, b, a in rows]
    out.append(f'| **YAML の欄の計** | **{tb}** | **{ta}** | **{ta - tb:+d}（{100 * (tb - ta) / tb:.0f}% 減）** |')
    out.append(f'| 設計書の手で書く節（記入例が書いた 12 節に対して） | 12 | {len(hand)} | {len(hand) - 12:+d} |')
    out.append(f'| 設計書の手で書く節（#4 の Lite の定義の 6 節に対して） | {len(LITE_4)} | {len(LITE_4 & set(hand))} | {len(LITE_4 & set(hand)) - len(LITE_4):+d} |')
    out.append('')
    out.append(f"手で書く対象外の回答：{'・'.join(hand_oos)}（指摘が出た行、レルム・クライアントの既定に依存する行、利用イベント）")
    text = '\n'.join(out)
    sys.stdout.buffer.write((text + '\n').encode('utf-8'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
