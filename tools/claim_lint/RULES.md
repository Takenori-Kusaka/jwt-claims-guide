# claim_lint の規則（v0）

設計書の台帳（`claims.yaml`）・トークン目録（`token_types.yaml`）・カタログへの回答（`catalog_answers.yaml`）を検査する規則です。v0 は #16（縦の一本）で作った土台で、R1・R2・R8 と、スライドの参照の解決だけを持ちます。意味の規則（L1〜）は #6、網羅の規則（R3〜）は #17 で足します。

```
python tools/claim_lint templates/examples/scenario-a                 # 人向けの表
python tools/claim_lint templates/examples/scenario-a --format json   # 機械向けの JSON
python tools/claim_lint <設計書のディレクトリ> --profile lite         # Lite：R2 を warn に下げる
```

error が 1 件でもあれば終了コード 1 です。error の規則は抑止できません（`templates/CONTRIBUTING.md` の 2.）。

| ID | 内容 | 重大度 | 根拠 |
| --- | --- | --- | --- |
| SCHEMA | `templates/registry/claims.schema.json`・`token_types.schema.json` の検証（JSON Schema 2020-12）。YAML の日付は文字列として読む。同じキーを 2 回書くと失敗する（LOAD） | error | #3 |
| R1 | 必須の列が空でない。下の「R1 の必須の列」。スライド 134 の 12 項目を載せる行の必須の列にし、欠ければ検出する（req:p11-registry-fields.R13） | error | slide:p11-registry-fields、#3 |
| R2 | カタログ（`templates/catalog/`）の全イベントに「該当」か「対象外」の回答がある。「対象外」には `assumption`（起きない前提）と `breaks_when`（崩れる条件）が、それぞれ 10 字以上あり、互いに同じでない。「該当」には関係するトークン種別か説明がある。カタログにない ID への回答と、同じイベントへの 2 つの回答は error | error（`--profile lite` では warn。未知の ID と重複は error のまま） | `templates/CONTRIBUTING.md` の 2.「対象外の書き方」、report Q9 の R2。10 字は筆者の提案（tracking #16） |
| R8 | トークン種別ごとの最悪のサイズと、経路の上限。下の「R8 の計算」 | error／warn／info | report Q9。しきい値は筆者の提案（tracking #16） |
| SLIDE | `refs` の `guide-slide` の ID と、入力のファイルの中の `slide:<id>` が、実在のスライドを指す（`tools/check_slide_refs.py` の解決を使う） | error | #15 |

## R1 の必須の列

| 行の種類 | 必須の列 |
| --- | --- |
| すべてのクレーム | `id`・`name`・`decision`・`rationale` |
| `採用`・`既定どおり`（トークンに載せる行） | 上に加えて `namespace`（最上位は `null`）・`type`・`shape`・`description`・`not_meaning`・`usage`・`issuers`・`authoritative_writer`・`issue_events`・`consumers`（読む受け手がいなければ `[]`）・`carried_in`・`on_missing`・`max_bytes`（配列は `max_items` も）・`overflow_strategy`・`pii_category`・`log_policy`・`owner`・`source_system`・`volatility`・`propagation_delay`・`status` |
| `採用`・`却下` | `refs`・`assumption`・`revisit_trigger` のうち 2 つ以上（#3 の「判断」の区分） |
| トークン種別 | `id`・`kind`・`decision`・`rationale`・`format`。`採用`・`既定どおり` は `purpose`・`issuer`・`holder`・`max_lifetime`・`stored_at`・`transport`・`revocation`。JWT はさらに `typ`・`alg_allowlist`・`issuers`・`key_rotation`。ヘッダー（Authorization・Cookie）で運ぶ JWT は `size`（R8 の入力） |

スライド 134（slide:p11-registry-fields）の 12 の項目は、載せる行の必須の列に入っています。項目と列の対応は `templates/registry/README.md` の「スライド 134 の 12 項目と台帳の列」にあります。12 番目の「変更履歴」は列ではなく Git の履歴で持ちます。

## R8 の計算

JWS（コンパクト形式）のエンコード後の長さを、宣言の値から計算します（`tools/claim_lint/r8.py`）。

```
最悪のサイズ = ceil(4/3 × ヘッダー) + ceil(4/3 × ペイロード) + ceil(4/3 × 署名) + 2（ドット 2 つ）
              Authorization の Bearer で運ぶなら + 7（"Bearer "）
```

- `ceil(4n/3)` は、n バイトを base64url（パディングなし）にした長さです（RFC 7515 §2、RFC 4648 §5）。
- ペイロードは、載る全クレームの JSON（空白なし）の UTF-8 のバイト数です。文字列は `max_bytes`＋引用符 2、数値は `max_bytes`（桁数）、配列は `2 ＋ max_items × 要素 ＋（max_items − 1）`、メンバーは `キー（引用符つき）＋ コロン ＋ 値`、オブジェクトは `2 ＋ メンバー ＋（メンバー − 1）`。`namespace` の付いたクレームは、名前空間の名前をキーにした 1 つのオブジェクトにまとめます。
- ヘッダーは、`size.header.params` から同じ規則で計算し、`serializer_extra_bytes`（発行者の JSON の書き出しが足す空白）を足します。Keycloak 26.8.0 では 4 バイトでした（見本トークンの実測。`research/template-design/gate1.md`）。
- 署名の長さは、HMAC は RFC 7518 §3.2、ECDSA は RFC 7518 §3.4、RSA（RS・PS）は鍵の長さ（RFC 8017 §8.1.1・§8.2.1）、Ed25519 は 64 バイト（RFC 8032 §5.1.6）です。
- 経路の上限は `tools/claim_lint/path_limits.yaml`（一次資料で確かめた値だけ）か、根拠つきでその場に宣言した値です。確かめていない値は既定に入れません（`research/template-design/unverified.md` の V01〜V04）。
  - `header_field` の上限（nginx・Apache httpd・HTTP.sys の MaxFieldLength）とは、`Authorization: Bearer <トークン>` の行（ヘッダー名を含む）を比べます。ヘッダー名を数えるのは保守側に倒した読み方で、各サーバーが数えるかは確かめていません（筆者の提案。tracking #16）。
  - `all_headers` の上限（Tomcat・Node.js・HTTP.sys の MaxRequestBytes）とは、上の行に `size.other_headers_bytes`（要求行とほかのヘッダーの見積もり）を足して比べます。宣言がなければ error です。
  - HTTP/2・HTTP/3 の圧縮による割り引きはしません（V03）。

| 判定 | 条件 |
| --- | --- |
| error | 最も厳しい上限を超える。配列に `max_items` がない（値域が無制限）。配列に `overflow_strategy` がない。載る行に `max_bytes` がない。`carried_in` のトークン種別が目録にない。経路の上限が既定の一覧にも宣言にもない。署名の長さが決まらない |
| warn | 最も厳しい上限の 75% を超える（report Q9 は 50〜75% としている。上の端を使った。筆者の提案、tracking #16） |
| info | 計算の結果。同じクレーム（`usage` が protocol でないもの）が 2 つ以上のトークン種別に載る（重複の候補） |

`overflow_strategy` に切り詰め（truncate）は書けません（スキーマの列挙にない）。error のメッセージは「載せるか、問い合わせるか」（slide:p04-carry-or-query）へ誘導します。軽量アクセストークン（Keycloak）は、解決策として誘導しません。

### 限界

R8 は宣言の値を信じます。宣言と実際の発行のずれは、見本トークンとの照合（`tools/tests/test_claim_lint.py` の golden）と、発行されたトークンの計測で補います。配列は `max_items × max_bytes` で数えるので、要素の長さがばらつく配列では実際より大きく出ます（安全側）。
