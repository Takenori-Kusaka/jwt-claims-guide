# 台帳のスキーマ v0：足りなかった列と不要だった列（#16 → #3）

シナリオ A（Keycloak 26.8）の記入例（`templates/examples/scenario-a/`）を、スキーマ v0（`templates/registry/claims.schema.json`・`token_types.schema.json`）で書いて分かった過不足です。#3（台帳 v1）に渡します。

- 基準日：2026-11-22
- 作成方法：生成 AI（Claude）を使って作り、筆者が確認した。人による点検は未実施。別の LLM のセッションでの点検も未実施（`gate1.md` の 5.）
- 根拠：記入例の行の ID（`C-…`）と、claim_lint の出力

## 1. 足りなかった列・値（v0 で足したもの、または文で逃げたもの）

| # | 列・値 | 何が書けなかったか | v0 での扱い | #3 への提案 |
| --- | --- | --- | --- | --- |
| 1 | `catalog_refs`（配列） | ケーススタディの一覧表は「定義した出典ごとに 1 行」なので、AT の `iss`（RFC 9068、CLM-0092）と ID トークンの `iss`（OIDC Core、CLM-0093）が別の行になる。台帳の 1 行（クレーム名ごと）から 1 つの ID では指せない | 配列にした（`catalog_refs`）。casestudy-mapping.md の 3. の `catalog_ref`（単数）の案を変えた | 配列で持つ。照合の CI は参照ごとに、その行の `token` と `carried_in` を突き合わせる |
| 2 | `usage` の値 `protocol` | `exp`・`iat`・`jti`・`typ`・`sid`・`scope`・`nonce` は identifier／authz／display のどれでもない | 値 `protocol` を足した | `protocol` を足すか、`usage` を任意にする。R8 の info（重複の候補）は `protocol` を除いて出している |
| 3 | `on_missing` の値 `既定値`・`無視` と、欠落の意味（`absent_semantics`） | `roles` が無いのは「ロールなし＝何も許さない」で、拒否ではない（slide:p04-absent-null-false-empty）。読まないクレーム（`auth_time` など）は「無視」 | 値を足した。意味は `note` に文で書いた | `absent_semantics`（無い・null・false・空配列の意味）を列にする。#3 の本文の `on_missing`（拒否）だけでは足りない |
| 4 | `integrity_until` | `tenant_id` は API で Postgres のセッション変数 `app.tenant` に写した時点で、JWS の保護の外に出る。その先の守り（SET LOCAL・NOBYPASSRLS）を書く場所がない | 任意の列として足した（文）。`C-tenant-id` だけに書いた | #3 の `integrity_until` で受ける。シナリオ A では「DB のセッションの文脈」が実際に要った。値の語彙（header・db_session・queue・logs）を決める |
| 5 | `confidential_from`（読ませない相手） | ID トークンの `name`・`email` をブラウザに渡さない、は `assumption` の文でしか書けなかった | 書いていない（`assumption`） | シナリオ A でも要る（browser）。BFF の構成では、ブラウザは BFF のセッションの Cookie だけを持つので、IDT の個人情報のクレームに `confidential_from: [browser]` を書ける |
| 6 | トークン種別の `visible_to` | 「AT はブラウザに出ない」は `holder`・`stored_at` の文で書いた | 書いていない | 要る。nginx（経路の途中）に AT が見えることも書ける。ログに残すかは `log_policy` と分けて書く |
| 7 | トークン種別の `jwe` | — | なし | シナリオ A では不要だった（JWE を使わない）。列を作るなら「使わない」と書けるようにする |
| 8 | IdP が外せないクレームの印 | `typ`・`sid`・`azp`・`scope` を「既定どおり」にする理由は、公式文書（26.8.2「Using lightweight access token」）の一覧による。行ごとに同じ根拠を書いた | `refs` に同じ根拠を 4 回書いた | IdP モジュール（#4 の M_idp_keycloak）に「外せないクレーム」の一覧を持たせ、台帳はそれを参照する。#6 の L2 の予約名の一覧と同じ形にできる |
| 9 | テナントの束縛（`tenant_binding`） | iss のレルム名と `tenant_id` の照合は、`enforced_at` の文でしか書けない | `enforced_at` の文 | #6 の L9 の入力として列にする（`tenant_binding: iss+claim`） |
| 10 | R8 のヘッダーの空白（`size.header.serializer_extra_bytes`） | Keycloak 26.8.0 の JOSE ヘッダーは `"typ" : "at+jwt"` のように空白を入れる。コンパクトな JSON として計算すると 4 バイト（base64url で 5 文字）足りなかった | 足した（実測の値と根拠の文） | IdP モジュールに版ごとの値を持たせる。版を上げたら見本トークンで測り直す |
| 11 | 経路の上限の種類（`applies_to`）と `other_headers_bytes` | Tomcat・Node.js・HTTP.sys の MaxRequestBytes は「要求行と全ヘッダーの合計」、nginx・Apache httpd・HTTP.sys の MaxFieldLength は「ヘッダー 1 つ」。同じ予算として比べられない | 両方を足した | hops（#3）の宣言に入れる。`other_headers_bytes` は見積もり（筆者の提案） |
| 12 | 発行の契機ごとの値の長さ | `jti` の接頭辞（見本は `onrtac`）が、リフレッシュなどで同じ長さかが分からない | `assumption` に書いた | 列にはしない。IdP モジュールの「確かめていない点」に置く |
| 13 | ライフサイクルの「DB の接続」の層 | `token_types` の `kind` に DB の接続がない（slide:p07-lifetime-mismatch） | 設計書の表にだけ書いた | #4 の追加（ライフサイクル表の DB・ブローカーの接続の層）で受ける。`token_types` に入れるか、hops に入れるかを決める |
| 14 | 却下の理由の種類 | `client_id` の却下は「IdP が出さない」で、ケーススタディの「不要・代替あり・禁止」のどれでもない | `rationale` の文 | casestudy-mapping.md の 4. の「`decision` を細かくするか」で、「IdP が出さない」を区別するか決める |

## 2. 不要だった列（シナリオ A では書くことがなかった）

#3 の本文の列のうち、シナリオ A では書く内容がなく、v0 に入れなかったものです。シナリオ B・C では要る見込みなので、削るのではなく「任意」にすることを提案します。

| 列 | 不要だった理由（シナリオ A） | 見込み |
| --- | --- | --- |
| `upstream_issuer`・正規化の規則 | 入口での中継・交換がない | B（入口で内部トークンに交換）で要る |
| `modifiers` | 書き手が各段階で 1 つ（Keycloak のマッパー）で、追加・抑止・上書きがない | B（フックで groups が消える Cognito など）で要る |
| `recipients_external`・`cross_border` | 社外の受け手がない | 連携先（I05）を入れるときに要る |
| `sunset_on` | すべて active | 定義の寿命（Full の欄）で要る |
| `asvs_ids`・`spec_version` | 草案のクレームを使わず、ASVS の ID を引かなかった | Full で要る |
| `verification_method`・`last_verified` | データ源（Keycloak のユーザー・設定）を、記入例では確かめる手順がなかった | 実運用の台帳では要る。記入例で書くと作り話になる |
| `typical_items` | 配列は `roles` だけで、最大 2 件の固定の語彙 | 件数が多い配列（groups）で要る |

v0 で入れたが、ほぼ使わなかった列：

| 列 | 様子 | 提案 |
| --- | --- | --- |
| `propagation_delay` | 載せる 19 行のうち 15 行が 0（値が変わらないクレーム）。値が変わる行（`roles`・`name`・`email`・`email_verified`）でも、AT の寿命と同じ値を書いただけ | `volatility` が 0 の行では省けるようにする |
| `change_controller` | 標準のクレームでは仕様の発行元、組織のクレームでは `owner` と同じ | 組織のクレームでは `owner` と同じなら省けるようにする |
| 載せるが誰も読まない行の 21 列 | `auth_time`・`typ`・`sid`・`scope` は IdP が出すだけで、`consumers: []`。上限・個人情報・持ち主などを書いたが、判断の情報はほとんどない | 「既定どおり」かつ `consumers: []` の行は、R1 の必須を名前・型・上限・個人情報の区分に減らす（R8 の計算に要るもの） |

## 3. ケーススタディの「一部」の列の移し替え（casestudy-mapping.md の 3. と 4.）

#13 の 8. の #16 への引き継ぎ（1 つ目）。シナリオ A の記入例で実際に移した結果です。文章は写さず、書き直しました。

| ケーススタディの列 | 台帳の列 | 移せたか | メモ |
| --- | --- | --- | --- |
| `name` | `name`・`namespace` | 移せた | ORG-01〜03・07 は `https://claims.example.com/` と名前に分けた |
| `purpose` | `description`・`not_meaning` | 書き直した | 「表さないこと」は 1 行ずつ考え直す必要があった |
| `source_kind`・`source`・`url` | `registered_ref`・`refs` | 移せた | 標準の行は `registered_ref` |
| `multiplicity` | `shape` | 判断が要った | `aud` は「単一または配列」。宛先が 1 つの前提で `single` にし、`assumption` に書いた |
| `token` | `carried_in` | 判断が要った | 一覧表は種類だけで、台帳はトークン種別の ID。出典ごとの行を `catalog_refs` にまとめた（1. の #1） |
| `is_custom` | `registered_ref` の有無 | 移せた | |
| `checked_on` | `refs` の `verified_on` | 意味が違う | 一覧表の日付は写さず、記入例で確かめた日（2026-11-22）を書いた |
| `writer` | `authoritative_writer` | 書き直した | 区分ではなく、具体的なマッパー（Hardcoded claim・User Realm Role など）を書いた |
| `mutability` | `volatility` | 判断が要った | 区分から秒数へ。値は筆者の判断（0・300・86400） |
| `freshness` | `recompute_trigger` | 移せた | Keycloak はリフレッシュで再計算する（I02） |
| `authz_use` | `usage` | 判断が要った | `protocol` の値が要った（1. の #2） |
| `pii` | `pii_category` | 判断が要った | `sub`・`user_id` を個人情報、`sid` を個人関連情報とした。機械的には写せない |
| `log_policy` | `log_policy` | 判断が要った | 一覧表はほとんど「記載なし」 |
| `limit` | `max_bytes`・`max_items`・`overflow_strategy` | 判断が要った | 一覧表の上限の文は使えず、すべて記入例で決めた |
| `judgement` | `decision` | 移せた（4. の表） | 「既定どおり」に当たる判定がケーススタディにない。5 行がこれに当たった |
| `condition` | `assumption`・`carried_in` | 判断が要った | 「ID トークンのみ」は `carried_in: [IDT]`、「入口の正規化でのみ読む」は入口が無いので当てはまらなかった |
| `use_or_loss` | `rationale` | 書き直した | |
| `revisit` | `revisit_trigger` | 書き直した | |
| `checks` | `evidence` | 移せた | `jwt-claims-casestudy@080b8da:A8` の形 |

## 4. 照合の結果（#13 の 8. の #16 への引き継ぎ、2 つ目）

記入例の採否とケーススタディのシナリオ A の判定の食い違いを、手で数えました（照合の CI は #3）。

- 比べた参照：32 件（記入例の 25 行の `catalog_refs`）
- 載せる／載せないの食い違い：7 件（すべて意図したもの。`templates/casestudy-deviations.yaml`）
- 載せる側で一致したが、条件付き採用の条件と使い方が違う：1 件（`azp`）
- 名前の不一致：0 件
- 主な原因：記入例は入口での交換を置かない（`scenario_premises`）。7 件のうち 4 件（`auth_time` 2・`typ`・`sid`）は、Keycloak が既定で出す、または外せないクレームが API に届くことから生じた

数え方と実行の記録は `gate1.md` の 6.
