<!-- template_version: 0.1.0 -->
# クレームの台帳のスキーマ（v0）

**v0 は #16（縦の一本）で、シナリオ A（Keycloak）を書くのに要る列だけを入れた仮の版です。** 列の名前・型・必須は、#3（台帳 v1）で変わります。v0 で足りなかった列と不要だった列は [`research/template-design/v0-columns.md`](../../research/template-design/v0-columns.md) にあり、#3 に渡しています。

| ファイル | 中身 |
| --- | --- |
| `claims.schema.json` | 台帳（`claims.yaml`）の行の形。どの判断の行でどの列が必須かは、スキーマではなく claim_lint の R1 で確かめる（列が欠けたときに規則の ID つきで出すため） |
| `token_types.schema.json` | トークン目録、発行方式の選択（`issuance_profile`）、R8 の入力（`size`） |

記入例は [`templates/examples/scenario-a/`](../examples/scenario-a/) です。検査は `python tools/claim_lint templates/examples/scenario-a` で、規則は [`tools/claim_lint/RULES.md`](../../tools/claim_lint/RULES.md) にあります。

各列の意味と根拠を列ごとに書くのは #3 です。この README には、#16 で要件を満たすのに要る対応表だけを置きます。

<a id="slide-134-map"></a>
## スライド 134 の 12 項目と台帳の列

<!-- req:p11-registry-fields.R13 -->
slide:p11-registry-fields の「クレームごとに決める 12 の項目」と、v0 の列の対応です。1〜11 は、トークンに載せる行（`採用`・`既定どおり`）の必須の列で、欠けると claim_lint の R1 が error にします。12 は列ではなく、Git の履歴で持ちます。

| # | 項目 | v0 の列 | R1 で必須 |
| --- | --- | --- | --- |
| 1 | 名前 | `name`・`namespace`（最上位は `null`） | はい |
| 2 | 型 | `type`・`shape` | はい（許容値の列 `allowed_values` は v0 にない。#3） |
| 3 | 意味 | `description`・`not_meaning` | はい |
| 4 | 発行者 | `issuers` | はい |
| 5 | 書ける者 | `authoritative_writer`（段階と書き手） | はい |
| 6 | 許可された受け手 | `consumers`（読む受け手がいなければ `[]`） | はい（キーを書くこと） |
| 7 | 上限 | `max_bytes`・`max_items`（配列）・`overflow_strategy` | はい |
| 8 | 個人情報の区分 | `pii_category`・`log_policy` | はい |
| 9 | 持ち主 | `owner` | はい |
| 10 | 鮮度 | `source_system`・`volatility`・`propagation_delay` | はい |
| 11 | 状態 | `status`（proposed・active・deprecated・sunset） | はい |
| 12 | 変更履歴 | なし。台帳のファイルの Git の履歴（いつ・誰が・何を）で持つ | — |

却下の行（トークンに載せない行）では、1〜11 を必須にしていません。載せない行に上限や受け手を書かせても、答えようがないためです。

<a id="authoring"></a>
## 作成方法と点検状況

本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。

> 人による点検は未実施。作成とは別の LLM のセッションでの点検は未実施（#16 の関門 1 の資料 `research/template-design/gate1.md` に、点検の欄を空けてある）。
