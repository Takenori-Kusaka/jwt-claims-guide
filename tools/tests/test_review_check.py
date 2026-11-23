# -*- coding: utf-8 -*-
"""tools/review_check.py (#5): question IDs, fields, evidence and links of the review materials, and the trace markers."""
import os
import shutil
import sys

import pytest

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import review_check as rc  # noqa: E402

COPY = ['templates', 'deck/slide_ids.json', 'tools/template_sources.yaml', 'tools/claim_lint/RULES.md']
PERSP = os.path.join('templates', 'review', 'perspectives.md')


@pytest.fixture
def root(tmp_path):
    for rel in COPY:
        src, dst = os.path.join(ROOT, rel), tmp_path / rel
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)
    return tmp_path


def edit(root, rel, old, new):
    p = root / rel
    text = p.read_text(encoding='utf-8')
    assert old in text, old
    p.write_text(text.replace(old, new, 1), encoding='utf-8')


def rules(root):
    errors, _, _ = rc.check(str(root))
    return sorted({e[0] for e in errors}), errors


def test_repository_materials_pass():
    assert rc.main(['--root', ROOT]) == 0


def test_copy_passes(root):
    assert rules(root)[0] == []


def test_counts_cover_six_stages():
    _, questions, _ = rc.check(ROOT)
    stages = {q['stage'] for q in questions}
    assert stages == {s for s, _ in rc.STAGES}
    assert all(q['id'] for q in questions)


def test_v2_question_must_be_yes_no(root):
    edit(root, PERSP, '**q-hop-lifetime**　ホップごとに、下流のトークンの寿命（`max_lifetime`）が上流のトークン以下か（Txn-Token など、上流より長いホップには `narrowing_exception` に理由があるか）',
         '**q-hop-lifetime**　ホップごとの寿命')
    assert rules(root)[0] == ['V2']


def test_v2_missing_field_line(root):
    edit(root, PERSP, '- No なら：Blocker（`none`・HS256 の混同で偽造）\n', '')
    r, errors = rules(root)
    assert r == ['V2'] and any('No なら' in e[2] for e in errors)


def test_v3_field_must_name_a_design_doc_field_that_resolves(root):
    edit(root, PERSP, '- 見る欄：`registry:token_types#alg_allowlist`、`template:modules/M_token_validation#alg`',
         '- 見る欄：`registry:token_types#alg_list`')
    assert rules(root)[0] == ['V3', 'V6']
    edit(root, PERSP, '- 見る欄：`registry:token_types#alg_list`', '- 見る欄：設計書を読む')
    assert rules(root)[0] == ['V3']


def test_v4_evidence_form(root):
    edit(root, PERSP, '- 根拠：slide:p12-antipatterns-1、slide:p01-dangerous-header-params、RFC 8725 §3.1',
         '- 根拠：slide:p12-no-such-slide、RFC 1 §1')
    assert rules(root)[0] == ['V4']


def test_v5_contrast_link_and_incident(root):
    edit(root, PERSP, '- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L17`／実行 `test:negative_tests#alg-none`（未実装）・`test:negative_tests#alg-confusion`（未実装）／事例 CVE-2015-9235',
         '- つながり：lint `lint:L17`')
    r, errors = rules(root)
    assert r == ['V5'] and len([e for e in errors if e[0] == 'V5']) == 2


def test_v6_unimplemented_lint_and_test_must_be_marked(root):
    edit(root, PERSP, '`lint:L34`（未実装）', '`lint:L34`')
    assert rules(root)[0] == ['V6']


def test_v6_implemented_lint_must_not_be_marked(root):
    edit(root, PERSP, '／lint `lint:L17`／実行', '／lint `lint:L17`（未実装）／実行')
    assert rules(root)[0] == ['V6']


def test_v7_unknown_question_id(root):
    edit(root, os.path.join('templates', 'review', 'decision_tree.md'), '`q-original-principal`', '`q-no-such-question`')
    assert rules(root)[0] == ['V7']


def test_v8_and_v10_anti_pattern_question_removed(root):
    edit(root, PERSP, '**ap-2-9**　', '**q-ap-2-9-renamed**　')
    edit(root, PERSP, '<a id="ap-2-9"></a>', '<a id="q-ap-2-9-renamed"></a>')
    r, _ = rules(root)
    assert 'V8' in r and 'V10' in r


def test_v9_contrast_sections(root):
    edit(root, os.path.join('templates', 'review', 'contrasts', 'jws-vs-jwe.md'), '<a id="not-covered"></a>', '')
    assert rules(root)[0] == ['V9']


def test_v10_marker_must_be_in_the_section(root):
    edit(root, PERSP, '<!-- req:p06-narrow-downstream.R1 -->', '')
    r, errors = rules(root)
    assert r == ['V10'] and any('p06-narrow-downstream.R1' in e[1] for e in errors)


def test_v10_review_item_needs_an_anchor(root):
    edit(root, os.path.join('templates', 'trace', 'requirements.yaml'), 'review:contrasts/scope-vs-role#misuse',
         'review:contrasts/scope-vs-role')
    r, errors = rules(root)
    assert r == ['V10'] and any('アンカー' in e[2] for e in errors)


def test_v11_escalation_needs_sections(root):
    edit(root, os.path.join('templates', 'review', 'escalation.md'), '<a id="new-token-type"></a>', '')
    assert 'V11' in rules(root)[0]


def test_v12_readme_counts(root):
    edit(root, os.path.join('templates', 'review', 'README.md'), '| 計 | 160 |', '| 計 | 161 |')
    assert rules(root)[0] == ['V12']
