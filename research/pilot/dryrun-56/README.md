# 試行：短い一覧だけでのレビュー（#56）

> **LLM による試行。人による検証ではない。**

経験の浅いレビュアーの役をさせた LLM のセッション 1 つが、短い一覧だけで `research/pilot/scenario-c` をレビューした記録です（2026-11-25）。
**使ったのは最初の版の一覧です**（問いが 2〜3 文）。その後、独立点検（PR #71）を受けて、問いを 1 文にし、重なる問いをまとめました。いまの版では試していません。分析は [`research/template-design/triage-evidence.md`](../../template-design/triage-evidence.md) の 4. にあります。

| ファイル | 中身 |
| --- | --- |
| [`short-list.md`](short-list.md) | セッションに渡した一覧（答え方の 6 行と、`python tools/review_triage.py --design research/pilot/scenario-c` の当時の出力）。渡したままの版で、性質の読み違い（マルチテナント）を直す前のもの。今の出力は、性質の表・1 文の問い 20・開いた問い 6 で、手がかりと「見る欄」が付く |
| [`result.md`](result.md) | セッションが書いた結果（時間・問いごとの答え・指摘 24 件・迷った点 11 件・感想）。書いたままで、直していない |

- 渡したもの：上の一覧、要求の概要（`research/pilot/brief-C.md` の写し）、設計書の 5 ファイル（`design.md`・`claims.yaml`・`token_types.yaml`・`hops.yaml`・`catalog_answers.yaml`）、lint の結果（`--profile lite`）。リポジトリの外の隔離したフォルダーに写して渡し、その外は読まないよう指示した
- 渡さなかったもの：観点書・手順書・対比表・判断の木・パイロットのレビューの記録・付け直し
- 時間（約 2 分）は LLM の壁時計で、人の時間ではない
- 指摘が正しいかは、人は確かめていない
- レビューの記録（`review.yaml`）は作っていない
