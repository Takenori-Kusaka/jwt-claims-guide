<!-- template_version: 0.3.0 -->
# 追加前の 25 問：`https://aoba-sumai.example/claims/` の `approval_ref`

> **意図的に誤りを含む教材。設計に使わない**

- 対象：台帳の `C-approval-ref`（claims.yaml）
- 判定：共有クレームにする（25 問すべてに答えた）

| # | 問い（スライド 142・143） | 回答 | 出どころ |
| --- | --- | --- | --- |
| 1 | 受け手はこのクレームで何を決めるか | order-tool・lock-tool は、approval-svc の承認を条件つきの更新で使用済みにする鍵に、approval-svc は APPROVAL_AT で操作してよい 1 つの承認の記録を決めるのに使う（usage は identifier、answers は q-authorized） | 台帳：`usage`・`answers`・`enforced_at` |
| 2 | 寿命中に値が変わっても困らないか | ID は変わらない。承認の状態（取り下げ・使用済み・期限切れ）は変わるので、トークンに状態を載せず、受け手が approval-svc で条件つきの更新をして確かめる | 台帳：`volatility`・`on_revoke` |
| 3 | 既存の標準クレームで表せないか | 表せない。authorization_details の identifier は対象のリソースを指し、承認の記録を指さない。参照だけの APPROVAL_AT には authorization_details が無い（prior_art_search） | 台帳：`prior_art_search` |
| 4 | 自組織の名前空間か。予約名と衝突しないか | 自組織の名前空間 https://aoba-sumai.example/claims/ の下 | 台帳：`namespace` |
| 5 | 「.」「/」入りの名前を全ての受け手のツールで参照できるか | 受け手は order-tool・lock-tool・approval-svc で、order-tool・lock-tool は組織の共通の検証部品で、approval-svc は承認の画面の Web の枠組みの検証で、完全一致のキーとして読む | 手書き |
| 6 | トップレベルか、組織のオブジェクトの下か | トップレベルに、名前空間の接頭辞つきの名前で置く（flat_prefix） | 台帳：`namespaces`・`shape` |
| 7 | 型は 1 つか。区切り文字列を避けたか | 文字列 1 つ（shape は single）。^apv_[0-9a-f]{32}$ | 台帳：`type`・`shape`・`allowed_values` |
| 8 | ID・金額は文字列で運ぶか | ID は文字列で運ぶ。金額は authorization_details の中の 10 進の文字列 | 手書き |
| 9 | 無い・null・false・空配列の意味は | ORDER_TOOL_AT では承認の要らない操作（下書きと累計 10 万円以下の確定）、LOCK_TOOL_AT では承認の依頼の登録だけ、APPROVAL_AT では一覧の参照だけを許す。承認の要る操作で無ければ拒否する | 台帳：`absent_semantics`・`on_missing` |
| 10 | 大文字小文字・空白・比較方法は | approval-svc が採番のときに小文字の 16 進にする。受け手は完全一致で比べる | 台帳：`value_normalization` |
| 11 | 誰が値を書けるか。自己申告と分けたか | agent-sts だけが、approval-svc の記録を引いて書く。エージェント・repair-console が申告した ID は、記録の修繕依頼・担当者・宛先（locations）が合わなければ載せない | 台帳：`authoritative_writer` |
| 12 | 名前と不変の ID を出し、ID で照合させるか | 承認者の名前は載せない。ID だけを出し、承認者は approval-svc の記録で引く | 手書き |
| 13 | 上限は。超えたら失敗か、欠落か | 36 バイトで固定（上限で固定） | 台帳：`max_bytes`・`overflow_strategy` |
| 14 | 全リクエストに載せる価値があるか。宛先ごとに絞れるか | 承認の要る操作の宛先（order-tool・lock-tool）と approval-svc 宛てにだけ載せる。contact-tool・payment-tool 宛てには載せない | 台帳：`carried_in` |
| 15 | 付与するのは単一の発行者だけか | agent-sts だけ（issuers） | 台帳：`issuers` |
| 16 | 検証を共通ライブラリで提供するか | 形式の検査は共通の検証部品（approval-svc は承認の画面の Web の枠組み）。状態の照合と使用済みにする更新は、各受け手が approval-svc を呼ぶ | 手書き |
| 17 | ヘッダーに移すとき、同名ヘッダーの偽装（大文字小文字・アンダースコアの変種・重複）を除去するか | ヘッダーに移さない | 手書き |
| 18 | 未検証の値を流すモードは無いか | 無い。approval-svc が応答しないときは、承認の要る確定・発行を拒否する（下書き・連絡は続ける） | 手書き |
| 19 | 知らない受け手が無視しても安全か | order-tool・lock-tool のほかの受け手は承認の要る操作をしないので安全。承認の要る操作をする受け手を足すときは、条件つきの更新を必須にしてから足す | 手書き |
| 20 | ログに残すか。値かハッシュか。個人情報か | 個人情報として扱う（approval-svc の記録と突き合わせると、修繕依頼・部屋・時間帯が分かる。repair_id と同じ基準）。監査ログには監査の共通部品の鍵つきのハッシュで残す（C-sub と同じ鍵） | 台帳：`log_policy`・`pii_category` |
| 21 | 委任なら act・承認 ID との関係は | 承認は人（上長か担当者本人）が 1 つの操作について出すもので、act（エージェント）と別。受け手は承認の記録の担当者が sub、修繕依頼が repair_id と一致することを確かめ、エージェントは承認の操作をできない（APPROVAL_AT は act の無い repair-console にだけ出す）。発注の承認者は、承認の記録の担当者と別人で、修繕依頼の担当の履歴にも無い人に限る（担当の付け替えを挟んだ自己承認を止める） | 手書き |
| 22 | 台帳に登録し、受け手を把握したか | 登録した。受け手は order-tool・lock-tool・approval-svc | 台帳：`consumers` |
| 23 | 形式を変えるときの移行計画はあるか | approval-svc の ID の形式を変えるときは、受け手が新旧の両方の形式を受けるようになってから切り替える | 手書き |
| 24 | 改名・廃止の互換期間と並行発行は | ツールのトークンの受け入れの上限（330 秒）と配備の周期（2 週間）の長いほうより長く並行して出す | 手書き |
| 25 | 発行前の確認手段と、受け手の条件のテストは | order-tool・lock-tool の結合試験で、取り下げた承認・使用済みの承認・別の発注 ID の承認・金額の違う下書きが拒否され、同じ発注 ID の再試行では 1 回だけ確定し、approval-svc が止まると確定・発行が拒否されることを確かめる | 手書き |
