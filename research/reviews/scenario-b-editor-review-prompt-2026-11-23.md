# シナリオ B のレビュー（#50 の記入例）に渡した指示文

`templates/examples/scenario-b/review.yaml` のレビューは、LLM のセッション 1 つが行いました（Claude Opus 5.5、claude-opus-5-5、2026-11-23）。そのセッションに渡した指示の全文を、ここに残します（`templates/CONTRIBUTING.md` の 3. の「記録に残すもの」）。

- 渡した資料：リポジトリの作業ツリー（main の `bd1747b`）。読むよう指示したのは `templates/examples/scenario-b/` と `templates/review/` の教材
- 読まないよう指示したもの：`templates/examples/scenario-b/review-report.md`（前のレビュー）、perspectives.md の 9.（較正）、`research/reviews/`、PR のコメント
- 出力：問いへの回答・指摘・行の判定・抜き取りの採点などの YAML。レビューモードの作者が、ID と行のハッシュを付けて `review.yaml` の形にした（中身の文は変えていない。PR #52 の点検の後に、`hops:H15`・`claims:C-cnf` のコメントにだけ追記した）

## 読むときの注意（独立性）

- 「前のレビューを読んでいない」は、レビューしたセッションの自己申告です。確かめる手段はありません
- このセッションを起動した側（レビューモードの作者のセッション）は、前のレビューを読める状態にありました。ただし、指示文には前のレビューの中身を入れていません（下の全文）
- PR #52 の独立点検によると、24 件の指摘のうち約 11 件は、主題が前のレビュー（`review-report.md` の F01〜F29）と重なります。直していない問題が残っているなら、重なるのは自然です。それでも、この約 11 件を、独立に見つかった証拠には数えないでください

## 指示の全文

```text
You are an LLM reviewer doing a real design review of a worked example, following the review materials of this repository. Work read-only in the repository at E:\Github\jwt-claims-guide\.claude\worktrees\agent-a51f592d806d2b1e8 (do not edit any file there; do not run git commands that change anything). Write your only output file to: <scratchpad>\review-b-input.yaml

Target: the design in templates/examples/scenario-b/ (design.md, claims.yaml, token_types.yaml, hops.yaml, catalog_answers.yaml, claim_request_*.md, schemas/, variants/). Current working-tree version.

Materials to use: templates/review/procedure.md (follow 「1 名で行う場合」 and 「LLM で一次スクリーニングする」), templates/review/perspectives.md sections 1.-7. (168 questions; `python tools/review_check.py --list` prints the IDs with their stage), templates/review/decision_tree.md, templates/review/contrasts/*.md, templates/review/escalation.md, templates/review/rationale_rubric.md, templates/review/report_template.md (vocabulary for findings). You may run `python tools/claim_lint templates/examples/scenario-b --also-scan templates/examples/scenario-b/design.md` to get the CI result.
DO NOT read: templates/examples/scenario-b/review-report.md, section 9 (較正) of perspectives.md, research/reviews/*, or any PR comments — they hold an earlier review and reading them would anchor you. Form your own judgment from the design files.

What to produce (in Japanese for all free text, concise, one line per memo):
1. answers: for EVERY one of the 168 questions (IDs from perspectives.md 1.-6.): answer yes | no | na and a one-line memo saying what you saw in the 見る欄 (for na: why it does not apply). Yes means "meets". If the field is empty or you cannot decide, answer no (procedure step 3).
2. findings: for each problem found (every No should lead to a finding, possibly one finding covering several questions). Fields: id (F01, F02, ...), location (string, as report_template.md says: item IDs like `template:00_core#hop-table`, row id and column like `C-roles.volatility`, `claim_request_roles.md の問 13`, question IDs), anchors (list of row anchors this finding is about, form `claims:C-xxx`, `token_types:AT_ID`, `hops:H01`, `catalog_answers:I25`, `issuance_profile:key`; may be empty), questions (list of question IDs that found it), content, severity (Blocker|Major|Minor), origin (テンプレート項目|観点|カタログ外の質問|テンプレート外|LLM — you are the LLM primary screening, but classify by where it was found as the template says; use 観点 for perspectives questions etc.), kind (理由の不備|前提の誤り|実装とのずれ|候補の漏れ|目的と仕組みの不一致), confused_question (ONLY when kind is 目的と仕組みの不一致: which question was confused, e.g. "`q-peer` を `req_wl` で答えた"), verdict (always 保留 — a human reviewer has to decide; write that), response_state: 未着手.
   Verify every claim you make in a finding against the files (quote the column / line). Do not invent facts about specs; if unsure, say so and make it a question for the escalation list.
3. rows: a decision for each row you actually examined, at least every row of claims.yaml with decision 採用 (and others you looked at): anchor, decision (approve | request_changes | hold), comment (one line; for request_changes name the finding ID). Use hold when you could not decide.
4. sampling: rejection rationales of these three rows were drawn by the tool (seed "20261123-b", sha256 ranking): claims:C-rfc-roles, claims:C-rctx, claims:C-upn. Score each row's `rationale` (column rationale) with RR1..RR7 of rationale_rubric.md: each 満 | 否 | 対象外, pass true/false, note (one line, which aspect failed and why).
5. escalations: go through every criterion of escalation.md's first table; list the ones that apply (criterion id, location, to whom, conclusion "未了") and the ids that do not apply.
6. feedback: items to return to catalog / perspectives / trace / lint (to, content, finding ids).
7. ci: the claim_lint counts you got (error, warn, info, profile) and whether they match design.md section 1.
8. steps: which procedure steps (0-8) you did, and the role switching order you used.

Output format (YAML, exactly these top-level keys): reviewer_note, steps, ci, lite_full, answers (all 168), findings, rows, sampling, escalations (applies, not_applicable), feedback.
Make sure the YAML parses with PyYAML (double quotes for free text), 168 answers, and every ID is one from `python tools/review_check.py --list`.
When done, reply with a short summary: counts of yes/no/na per stage, number of findings by severity, number of rows per decision.
```

上の全文は、YAML の形の例（`answers:` などの記入例）を 1 行の説明に縮めたほかは、渡したとおりです。scratchpad のパスは `<scratchpad>` と書きました。
