<!-- template_version: 0.4.0 -->
# 対比表：名前（表示・語彙）と識別子（照合のキー）

利用者・テナント・部門・ロールには、人が読む名前と、照合に使う変わらない ID があります。名前は改名・再利用・大文字小文字の違いで別のものを指しうるので、照合に使いません（slide:p04-immutable-identifiers、slide:p02-user-identifier）。

- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施

<a id="question"></a>

## 1. 解く問い

| 種類 | 解く問い | 解かない問い |
| --- | --- | --- |
| 名前（`name`・`email`・`preferred_username`・部門名） | 人に何と見せるか | これは同じ主体か |
| 識別子（`iss`＋`sub`、組織の不変の ID、Entra の `tid`＋`oid`） | これは同じ主体か | 人に何と見せるか |
| 名前空間（組織の URI） | このクレームの意味を決めたのは誰か | 値が正しいか |

根拠：slide:p02-user-identifier、slide:p04-immutable-identifiers、slide:p04-namespace、OpenID Connect Core 1.0 §5.7

<a id="unit"></a>

## 2. 仕様上の単位

| 観点 | 名前 | 識別子 |
| --- | --- | --- |
| 安定性 | 変わる（改名・結婚・異動）、再利用される | 変わらない。`sub` は発行者の中で一意（`iss` と組でだけ意味を持つ） |
| 範囲 | 組織の中でも重なりうる | `iss` ごと。ペアワイズの `sub` は受け手ごとに違う |
| 型と比べ方 | 大文字小文字・正規化で揺れる | 文字列として完全一致 |
| 台帳の欄 | `registry:claims#display`・`registry:claims#value_normalization` | `registry:claims#identifier_properties`・`registry:claims#paired_id`・`registry:token_types#subject_type` |

根拠：OpenID Connect Core 1.0 §5.7、OpenID Connect Core 1.0 §8、slide:p04-case-and-characters

<a id="table"></a>

## 3. 対比

| 場面 | 名前で照合すると | 識別子で照合すると |
| --- | --- | --- |
| 利用者のキー | `email` を書き換えられる IdP で乗っ取り（nOAuth） | 乗っ取りにくい。IdP を替えるなら組織の不変の ID でつなぐ |
| テナント | 表示名の重なり・改名で別のテナントを指す | `iss` か不変のテナント ID の 1 つで決める |
| DB のユーザー | 名前の再利用で前の人の権限を引き継ぐ | 不変の ID で対応付ける |
| ロール・部門 | 語彙の違う IdP の同じ文字列を同じ意味とみなす | 組織の語彙（`value_vocabulary`）に対応付けてから使う |
| 型 | 数値の ID が丸められる・桁が落ちる | 文字列で運ぶ |

根拠：slide:p12-antipatterns-1、slide:p07-data-layer-checklist、slide:p02-roles-groups-entitlements、slide:p04-type

<a id="not-covered"></a>

## 4. 扱わないこと

- 組織の不変の ID を作る仕組み（人事の台帳・ID の払い出し）は扱わない
- 複数の IdP をまたぐアカウントのリンク（同一人物の判定）は扱わない。リンクのキーを組織が決めることだけを求める（`q-cross-tenant-identity`）

根拠：slide:p02-user-identifier、slide:p05-cross-tenant

<a id="misuse"></a>

## 5. 典型的な誤用

| # | 誤用 | 起きること | 見つける問い |
| --- | --- | --- | --- |
| m-1 | `email`・`upn` を利用者のキーにする | アカウントの乗っ取り | `ap-1-6`・`q-identifier-choice` |
| m-2 | ペアワイズの `sub` をアプリ・IdP をまたいで突き合わせる・`sub_id` と `sub` を組み合わせて主体を決める | 別人として扱う・別人を同じとみなす | `q-identifier-choice` |
| m-3 | テナントを決める値が 2 つある（`iss` と `tenant_id` のどちらが正か書いていない） | 片方だけを照合する受け手が出る | `q-identifier-choice`・`ap-1-4` |
| m-4 | 名前空間なしの独自クレーム・予約名と衝突する名前 | 黙って消える・上書きされる | `ap-2-4`・`dc-03` |
| m-5 | 型を決めない・配列を区切り文字列にする・ID を数値で運ぶ | 受け手ごとに解釈が分かれる | `ap-2-3`・`dc-05`・`dc-06` |
| m-6 | 大小だけ違う値を同じとみなす | 別のテナント・部門の値で通る | `dc-08`・`q-consumer-expression` |
| m-7 | テナントをまたいで暗黙に名寄せする | 別テナントの利用者を同一人物とみなす | `q-cross-tenant-identity` |
| m-8 | 製品の独自クレーム・製品ごとの位置を、組織の契約にする | IdP を替えると全受け手が壊れる | `q-idp-diff-absorbed` |

根拠：slide:p12-antipatterns-1、slide:p02-user-identifier、slide:p04-immutable-identifiers、slide:p04-namespace

<a id="evidence"></a>

## 6. 根拠

- OpenID Connect Core 1.0 §5.7（クレームの安定性。`iss` と `sub` の組だけが安定）・§8（ペアワイズ）
- ガイド：slide:p02-user-identifier、slide:p04-immutable-identifiers、slide:p04-namespace、slide:p12-antipatterns-1

根拠：OpenID Connect Core 1.0 §5.7、slide:p02-user-identifier、slide:p04-immutable-identifiers
