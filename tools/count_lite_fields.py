# -*- coding: utf-8 -*-
"""Count the hand-written fields of a worked example, before and after the reduced Lite proposed at gate 1 (#16).

  python tools/count_lite_fields.py [EXAMPLE_DIR]      (default: templates/examples/scenario-a)

Prints a Markdown table (research/template-design/gate1.md section 10 is generated from it).

Counting rule: in each YAML row, every key except `id` whose value is not null counts as one field (an explicit
empty list such as `consumers: []` is a written answer and counts; `namespace: null` does not). Nested values
(`refs`, `enforced_at`, `authoritative_writer`) count as one field. The reduced Lite rules are the constants below;
they are a proposal (author-proposal, tracking #16), not yet the Lite definition of #4.
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
# catalogue events the IdP module would mark 「起きない（構造上）」 for this issuance profile: their 対象外 answer is
# inherited. Every other 対象外 (the event can occur in the chosen profile) is hand-written with assumption and
# breaks_when -- this is where review findings A03 (I09, U07), A15 (U05) and the lint finding U10 came from.
STRUCTURAL = {
    'I03': 'the use-lightweight-access-token client policy executor is not applied to the client',
    'I04': 'Direct Access Grants is OFF on the client',
    'I05': 'Service accounts is OFF on the client',
    'I07': 'the device authorization grant is not enabled on the client',
    'I08': 'the offline_access scope is not assigned to the client',
}
# design.md sections: example numbering -> handling in the reduced Lite; LITE_4 = the Lite sections of #4 (00_core
# 2, 3, 4, 6, 7, 12), mapped to the example's numbering (2, 3, 6, 8, 9, 12)
DESIGN = {1: 'generated', 2: 'hand', 3: 'hand', 4: 'generated', 5: 'generated', 6: 'hand', 7: 'full-only',
          8: 'generated', 9: 'hand', 10: 'generated', 11: 'generated', 12: 'hand'}
LITE_4 = {2, 3, 6, 8, 9, 12}


def fields(row, skip=('id',)):
    return [k for k, v in row.items() if k not in skip and v is not None]


def count(example):
    claims = core.load_yaml(os.path.join(example, 'claims.yaml'))['claims']
    tts = core.load_yaml(os.path.join(example, 'token_types.yaml'))
    answers = core.load_yaml(os.path.join(example, 'catalog_answers.yaml'))['answers']
    rows = []
    groups = {'read': [0, 0, 0], 'unread': [0, 0, 0], 'rejected': [0, 0, 0]}
    for c in claims:
        f = fields(c)
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
    ip = sum(len(fields(v, ())) for v in tts['issuance_profile'].values())
    rows.append(('発行方式の選択（既定の組み合わせのまま）', ip, 0))
    ttb = sum(len(fields(t)) for t in tts['token_types'])
    tta = sum(len(fields(t)) if t['decision'] != '却下' else len([k for k in fields(t) if k in REJECTED_TT_KEEP]) for t in tts['token_types'])
    rows.append(('トークン目録', ttb, tta))
    ab = sum(len(fields(a, ())) for a in answers)
    aa = sum(len(fields(a, ())) for a in answers if not (a['answer'] == '対象外' and a['event'] in STRUCTURAL))
    inherited = sorted(a['event'] for a in answers if a['answer'] == '対象外' and a['event'] in STRUCTURAL)
    hand_oos = sorted(a['event'] for a in answers if a['answer'] == '対象外' and a['event'] not in STRUCTURAL)
    rows.append((f"カタログへの回答（対象外のうち引き継ぐ {len(inherited)} 件：{'・'.join(inherited)}）", ab, aa))
    cr = open(os.path.join(example, 'claim_request_tenant_id.md'), encoding='utf-8').read()
    hand_q = len(re.findall(r'^\| \d+ \|.*\| 手書き \|$', cr, flags=re.M))
    shared = [c['id'] for c in claims if c.get('namespace') and c['decision'] == '採用']
    rows.append((f'追加前の 25 問（共有クレーム {len(shared)} つ × 手で書く {hand_q} 問）', 0, len(shared) * hand_q))
    tb = sum(r[1] for r in rows); ta = sum(r[2] for r in rows)
    hand = sorted(k for k, v in DESIGN.items() if v == 'hand')
    return rows, (tb, ta), hand, hand_oos


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    example = os.path.abspath(argv[0]) if argv else os.path.join(ROOT, 'templates', 'examples', 'scenario-a')
    rows, (tb, ta), hand, hand_oos = count(example)
    out = ['| 対象 | 今の記入例 | 縮小 Lite | 差 |', '| --- | --- | --- | --- |']
    out += [f'| {n} | {b} | {a} | {a - b:+d} |' for n, b, a in rows]
    out.append(f'| **YAML の欄の計** | **{tb}** | **{ta}** | **{ta - tb:+d}（{100 * (tb - ta) / tb:.0f}% 減）** |')
    out.append(f'| 設計書の手で書く節（記入例が書いた 12 節に対して） | 12 | {len(hand)} | {len(hand) - 12:+d} |')
    out.append(f'| 設計書の手で書く節（#4 の Lite の定義の 6 節に対して） | {len(LITE_4)} | {len(LITE_4 & set(hand))} | {len(LITE_4 & set(hand)) - len(LITE_4):+d} |')
    out.append('')
    out.append(f"手で書く対象外の回答：{'・'.join(hand_oos)}（その構成で起こりうるイベント）")
    text = '\n'.join(out)
    sys.stdout.buffer.write((text + '\n').encode('utf-8'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
