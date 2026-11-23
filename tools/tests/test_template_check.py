# -*- coding: utf-8 -*-
"""tools/template_check.py (#4): item IDs, evidence and blank fill-in columns of the design-doc templates."""
import os
import shutil
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import template_check as tc  # noqa: E402

SLIDES = {'p06-narrow-downstream', 'p08-rotation'}

GOOD = '''<!-- template_version: 0.3.0 -->
# 見本（modules/M_x）

<a id="item-one"></a>
## 1. 項目

項目 ID：`template:modules/M_x#item-one`

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） |
| --- | --- | --- |
| 寿命 |  |  |

根拠：slide:p06-narrow-downstream、RFC 9449 §4.3、draft-ietf-oauth-transaction-tokens-11 §6、筆者の提案：寿命と範囲を、同じ表で比べる（追跡 #4）
'''


def run(tmp_path, text):
    d = tmp_path / 'templates' / 'modules'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'M_x.md').write_text(text, encoding='utf-8')
    return tc.check_file(str(d / 'M_x.md'), str(tmp_path), SLIDES)


def rules(findings):
    return sorted({f[0] for f in findings})


def test_repository_templates_pass():
    assert tc.main(['--root', ROOT]) == 0


def test_good_item_passes(tmp_path):
    findings, items = run(tmp_path, GOOD)
    assert findings == [] and items == ['template:modules/M_x#item-one']


def test_t1_version_line(tmp_path):
    assert rules(run(tmp_path, GOOD.replace('<!-- template_version: 0.3.0 -->', '# no version'))[0]) == ['T1']


def test_t2_item_id_must_name_file_and_anchor(tmp_path):
    assert rules(run(tmp_path, GOOD.replace('M_x#item-one`', 'M_y#item-one`'))[0]) == ['T2']
    assert rules(run(tmp_path, GOOD.replace('項目 ID：`template:modules/M_x#item-one`\n', ''))[0]) == ['T2']


def test_t3_evidence_line_and_forms(tmp_path):
    assert rules(run(tmp_path, GOOD.replace('根拠：', '参考：'))[0]) == ['T3']
    bad = run(tmp_path / 'a', GOOD.replace('slide:p06-narrow-downstream', 'slide:p99-nothing'))[0]
    assert rules(bad) == ['T3'] and '実在しない' in bad[0][2]
    # a draft needs its version, an RFC its section, a proposal its tracking issue
    assert rules(run(tmp_path / 'b', GOOD.replace('transaction-tokens-11', 'transaction-tokens'))[0]) == ['T3']
    assert rules(run(tmp_path / 'c', GOOD.replace('RFC 9449 §4.3', 'RFC 9449'))[0]) == ['T3']
    assert rules(run(tmp_path / 'd', GOOD.replace('（追跡 #4）', ''))[0]) == ['T3']


def test_t3_author_proposal_may_contain_a_comma(tmp_path):
    findings, _ = run(tmp_path, GOOD)
    assert findings == []  # 「寿命と範囲を、同じ表で比べる」 is one element


def test_t4_fill_in_columns_stay_blank(tmp_path):
    text = GOOD.replace('| 寿命 |  |  |', '| 寿命 | 300 秒 | 剥奪を早く届けるため |')
    f = run(tmp_path, text)[0]
    assert rules(f) == ['T4'] and len(f) == 2


def test_t5_planned_template_items_resolve(tmp_path):
    shutil.copytree(os.path.join(ROOT, 'templates', 'trace'), tmp_path / 'templates' / 'trace')
    out = tc.check_planned(str(tmp_path), [])
    assert out and all(r == 'T5' for r, _, _ in out)
