<!-- template_version: 0.3.0 -->
# 追加前の 25 問：`https://minato-denki.example/claims/` の `approval_id`

> **測定の対照に使う教材。設計に使わない**

- 対象：台帳の `C-approval-id`（claims.yaml）
- 判定：共有クレームにする（25 問すべてに答えた）

| # | 問い（スライド 142・143） | 回答 | 出どころ |
| --- | --- | --- | --- |
| 1 | 受け手はこのクレームで何を決めるか | refund-tool が、3 万円を超える返金の承認の記録を approval-svc で引く鍵にする（usage は identifier、answers は q-authorized） | 台帳：`usage`・`answers`・`rationale` |
| 2 | 寿命中に値が変わっても困らないか | ID は変わらない。承認の状態（取り下げ・使用済み）は変わるので、トークンに状態を載せず、返金のたびに approval-svc で引く | 台帳：`volatility`・`on_revoke` |
| 3 | 既存の標準クレームで表せないか | 表せない。authorization_details の identifier は対象のリソースを指し、承認の記録を指さない（prior_art_search） | 台帳：`registered_ref`・`prior_art_search` |
| 4 | 自組織の名前空間か。予約名と衝突しないか | 自組織の名前空間 https://minato-denki.example/claims/ の下 | 手書き |
| 5 | 「.」「/」入りの名前を全ての受け手のツールで参照できるか | 受け手は refund-tool だけで、組織の共通の検証部品で完全一致のキーとして読む | 手書き |
| 6 | トップレベルか、組織のオブジェクトの下か | トップレベルに、名前空間の接頭辞つきの名前で置く（flat_prefix） | 台帳：`namespace`・`shape` |
| 7 | 型は 1 つか。区切り文字列を避けたか | 文字列 1 つ（shape は single） | 台帳：`type`・`shape` |
| 8 | ID・金額は文字列で運ぶか | ID は文字列で運ぶ。金額は authorization_details の中の 10 進の文字列 | 手書き |
| 9 | 無い・null・false・空配列の意味は | 無ければ承認の要らない返金（3 万円以下）。3 万円を超える返金の要求で無ければ拒否する | 台帳：`absent_semantics`・`on_missing` |
| 10 | 大文字小文字・空白・比較方法は | 小文字の 16 進で、完全一致で比べる | 手書き |
| 11 | 誰が値を書けるか。自己申告と分けたか | agent-sts だけが、approval-svc の承認の記録を引いて書く。エージェントの申告の ID は、記録の担当者・案件・注文と合わなければ載せない | 台帳：`authoritative_writer`・`provenance` |
| 12 | 名前と不変の ID を出し、ID で照合させるか | 承認者の名前は載せない。ID だけを出し、承認者は approval-svc の記録で引く | 手書き |
| 13 | 上限は。超えたら失敗か、欠落か | 35 バイトで固定（上限で固定） | 台帳：`max_bytes`・`max_items`・`overflow_strategy` |
| 14 | 全リクエストに載せる価値があるか。宛先ごとに絞れるか | refund-tool 宛ての TOOL_AT にだけ載せる。order-tool・customer-tool 宛てには載せない | 手書き |
| 15 | 付与するのは単一の発行者だけか | agent-sts だけ（issuers） | 台帳：`issuers`・`enforced_at` |
| 16 | 検証を共通ライブラリで提供するか | 形式の検査は共通の検証部品。状態の照合は refund-tool が approval-svc を呼ぶ | 手書き |
| 17 | ヘッダーに移すとき、同名ヘッダーの偽装（大文字小文字・アンダースコアの変種・重複）を除去するか | ヘッダーに移さない | 手書き |
| 18 | 未検証の値を流すモードは無いか | 無い。approval-svc が応答しないときは返金を拒否する（読み取りは続ける） | 手書き |
| 19 | 知らない受け手が無視しても安全か | refund-tool のほかの受け手は返金をしないので安全。返金をする受け手を足すときは、状態の照合を必須にしてから足す | 手書き |
| 20 | ログに残すか。値かハッシュか。個人情報か | 値のまま記録する。個人情報ではない（承認の記録の番号） | 台帳：`log_policy`・`pii_category` |
| 21 | 委任なら act・承認 ID との関係は | 承認は責任者が担当者の返金について出すもので、act（エージェント）と別。refund-tool は承認の記録の担当者と sub、注文と authorization_details の一致を確かめる | 手書き |
| 22 | 台帳に登録し、受け手を把握したか | 登録した。受け手は refund-tool だけ | 台帳：`consumers` |
| 23 | 形式を変えるときの移行計画はあるか | approval-svc の ID の形式を変えるときは、refund-tool が新旧の両方の形式を受けるようになってから切り替える | 手書き |
| 24 | 改名・廃止の互換期間と並行発行は | TOOL_AT の受け入れの上限（330 秒）より長く、少なくとも 2 週間は並行して出す | 手書き |
| 25 | 発行前の確認手段と、受け手の条件のテストは | refund-tool の結合試験で、取り下げた承認・使用済みの承認・金額の違う要求が拒否され、approval-svc が止まると返金が拒否されることを確かめる | 手書き |
