# R1 のレビューの記録（パイロット #9、シナリオ B、Full、ブラインド）

> LLM によるレビュー。人による検証ではない。

## 時刻（壁時計、JST）

| 区切り | 時刻 |
| --- | --- |
| 開始（最初のコマンド） | 2026-11-24T07:08:06+09:00 |
| 段 0（lint の再実行・render --check・抜き取り） | 07:11 頃 |
| 段 1〜3（設計書・台帳・観点書 168 問を読み、答えた） | 07:08〜07:13 |
| 段 5（一覧の外を探した時間。観点書を閉じて） | 07:12〜07:18（約 6 分） |
| review.yaml の作成・検査・レポートの生成 | 07:15〜07:20 |
| 終了（提出の時刻、review.yaml の submitted） | 2026-11-24T07:20:06+09:00 |

合計 約 12 分。LLM のため、読みと判断の多くは同じ応答の中で並行している。段の時刻は目安。

## 渡したもの・読んだもの

- 設計書：`E:\Github\jwt-claims-guide\.claude\worktrees\agent-acb20059fb1493488\research\pilot\scenario-b\`（コミット 857320c）の design.md・claims.yaml・token_types.yaml・hops.yaml・catalog_answers.yaml・claim_request_*.md（schemas/ は一覧だけ）
- 要求の概要：brief-B.md
- 教材：templates/review の procedure.md・perspectives.md（全文）・decision_tree.md（節 2〜7）・escalation.md・rationale_rubric.md・report_template.md・review.schema.json・README.md。contrasts/ は開いていない（判断の木と観点書の本文で足りた）
- ツール：`python tools/claim_lint research/pilot/scenario-b --also-scan .../design.md`（error 0・warn 2・info 16、設計書の 1. と一致）、`claim_lint render --check`（OK）、`review_record.py sample --seed R1-pilot-B --count 3`、`review_record.py check`（OK）、`review_record.py report`、`review_check.py --report`（OK）
- 読んでいないもの：author-log.md、templates/examples/**、templates/casestudy-*、research/** の設計書の外、ケーススタディのリポジトリ・xlsx、PR #55 のコメント、ほかのレビュアーの出力（review-B-R2 など）。tools/claim_lint/drift.py は 1 行（flat_prefix の名前のつなぎ方）だけを grep で見た
- worktree は変更していない（git status は空のまま）。review.yaml の作成に使ったスクリプトは scratchpad の直下（build_review_B_R1.py）に置いた

## 結果の要約

- 168 問すべてに回答：Yes 114・No 17・該当なし 37
- 指摘 22 件：Blocker 0・Major 9・Minor 13。出どころ：観点 12・カタログ外の質問 1（T2）・テンプレート外 9（T1・T3〜T10）
- 行の判定 130 行：承認 96・修正を求める 28・保留 6
- 専門家に回す：unverified-idp-behavior の 1 件
- 理由の採点：却下 5（合格 4）、採用 5（合格 3）

## 一覧の外で見つけた主なもの

1. T1：ログアウトの判定が、5 つの IdP の iat と BFF が書く時刻を比べる（要求の概要の 6. は Keycloak 以外を仮想の時計とする）
2. T2：BFF・管理者が社員台帳にログアウトの時刻を書く経路が、ホップにも範囲の図にも無い（書けないときに B12 が通る）
3. T3：移行の期間の B4〜B7 に、すぐ取れる守り（現状の入口でのヘッダーの除去など）を検討していない
4. T4：B15 の守りが「契約社員は社員台帳で部署が無い」前提に依存する
5. T5：内部トークンの署名鍵の保管・漏えい時の手順が無い

## 限界・注意

- 1 名・1 セッションで、procedure.md の「日を分ける」「段 3 の No を別のセッションで読み直す」はしていない
- 引用元（RFC・スライド）は開いていない。RR4 と q-evidence-attribution は、引用の名前と主張の対応だけで判定した
- IdP の挙動（Entra の v1／v2、Graph の権限、Okta の uid、Logout Token の検証の手順）はモデルの知識で書いた。T8・T10 は確かめていない前提を含むので、T8 は保留にした
- 重大度は観点書の目安に従ったが、最終の判断はレビュアー（人）が行う
- procedure.md の段 4（採用・却下から各 5 件）と、review_record.py の sampling（却下の 2〜3 件）が合わないため、追加の採点はレポートの補遺に手で書いた（review.yaml には入っていない）
