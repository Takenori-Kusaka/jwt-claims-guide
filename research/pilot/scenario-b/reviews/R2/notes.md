# R2 のメモ（シナリオ B のブラインドのレビュー、パイロット #9）

**LLM によるレビュー。人による検証ではない。**

- レビュアー：R2（Claude Opus 5.5、Claude Code のサブエージェントのセッション 1 つ）
- 対象：`E:\Github\jwt-claims-guide\.claude\worktrees\agent-acb20059fb1493488\research\pilot\scenario-b`（コミット 857320c、読み取りだけ）
- 要求：`scratchpad\pilot\brief-B.md`
- 壁時計の開始：2026-11-24T07:08:15+09:00（`date -Iseconds`）
- 壁時計の終了：末尾に記録

## 読んだ順（攻撃者・運用を先に）

1. brief-B（2. の IdP の癖、5. の脅威、7. のあいまいな点）
2. procedure.md・report_template.md・review_record.py の help と review.schema.json
3. design.md の全体（1.〜13.、付録 A〜E）
4. perspectives.md の 1.〜6. の 168 問の問いの行と「見る欄」の行（9. の較正は読んでいない）
5. claims.yaml・hops.yaml・token_types.yaml の全体、catalog_answers.yaml の冒頭と outside_enumeration、claim_request の 3 件、受け手のスキーマ 4 件の required
6. rationale_rubric.md・escalation.md・decision_tree.md（contrasts/ は開いていない）
7. claim_lint を同じコミットで実行（error 0・warn 2・info 16。設計書の 1. と一致）

## 攻撃者・運用の視点で立てた仮説と結果

| 仮説 | 結果 |
| --- | --- |
| Entra の AT を別のクライアントが取っても入口が受けるか | 受ける。H3 に azp の照合が無い（R2-01） |
| 入口は BFF だけを受けるか | 確かめていない（R2-02）。B23 の見送りの比較にも無い |
| B13・B10 の守りに使うクレームは台帳にあるか | oid・tid・uid・cid・scp が行に無い（R2-03） |
| 5 つの IdP の管理者のだれでも admins を作れるか | 作れる。社員が IdP を選び分ける経路もある（R2-04） |
| Okta の groups は不変の値か | 名前（R2-05） |
| 異動でロールが外れるまで何秒か | 人事 → IdP の経路が無く上限が無い（R2-06） |
| 移行の間の B4〜B7 | 開いたまま。今の入口での除去・ネットワークを先に閉じる手順が無い（R2-07） |
| ログアウトの時刻は誰がどこへ書くか | BFF が人事の台帳に書くが、経路が図・ホップに無い（R2-08） |
| Entra の設定の前提が崩れたら | exp − iat ≤ 600 と v2.0 の iss で全員を拒む（R2-09、保留） |
| 経理台帳の jti の 1 回だけは複数台・再送で動くか | 書いてない（R2-10） |
| ヘッダーは許可リストか | 否定のリスト（R2-11） |
| B22・B15・B18・B19・B20・B2・B17 | 守れる |

## 確かめていないこと（レビュアーの側）

- R2-13 の Okta の groups の件数の上限（100 件、超えると失敗）はレビュアーの記憶で、公式文書を開いていない → 保留
- R2-09 の Entra の既定の AT の寿命（60〜90 分）・v1 の iss（sts.windows.net）・寿命のポリシーの最短 10 分はレビュアーの記憶 → 保留
- R2-22 の RFC 9700 §4.14.2 が公開クライアントを対象にすることはレビュアーの記憶（原典は開いていない）
- 理由の採点の RR4 は、引用元のスライド・仕様を開かずに名前と主張の対応だけを見た
- 対比表（contrasts/）は開いていない。判断の木は 6. の q-resource・q-peer・q-agent・q-authorized の行と比べた（R2-17 を出した）
- 段 3 の No の指摘を別の新しいセッションに読み直させる手順（procedure.md の「1 名で行う場合」の 3.）は行っていない

## 件数

- 指摘：24 件（Blocker 0・Major 8・Minor 16）。判定：採用 22・保留 2（R2-09・R2-13）
- 出どころ：観点 15・テンプレート外 6・カタログ外の質問 2・テンプレート項目 1
- 問い：168 問に回答（Yes 106・No 22・該当なし 40）
- 行の判定：60 行（claims 24・token_types 23・hops 13）。承認 35・修正を求める 22・保留 3（C-aud・C-cnf・DPOP_PROOF）。catalog_answers の 62 行は行ごとの判定をしていない
- 理由の採点：却下 5 件（合格 5）、採用 5 件（合格 4・不合格 1：C-sub の RR7）
- 専門家に回す：unverified-idp-behavior（基準）、B23 の見送り（基準の外、書き手の希望）

## 一覧の外にかけた時間

- 読みと並行：07:08〜07:13（要求の脅威と本番の障害を当てながら読んだ。一覧の外の分だけを分けて測っていない）
- 単独：07:17〜07:18 ごろ（約 1 分。試験の経路 R2-24 を足した）
- 推定の合計：4〜5 分。範囲は review-report.md の 10.3

壁時計の終了：2026-11-24T07:22:11+09:00（最後の確認の時刻）
