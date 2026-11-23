<!-- template_version: 0.4.0 -->
# 対比表：ID トークンとアクセストークン

どちらも JWT で、`iss`・`sub`・`aud`・`exp` を持つので取り違えやすいトークンです。違いは宛先です。ID トークンはクライアント（RP）がログインを確かめるためのもので、API に送るものではありません（slide:p01-id-token-vs-access-token）。

- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施

<a id="question"></a>

## 1. 解く問い

| トークン | 解く問い | 解かない問い |
| --- | --- | --- |
| ID トークン | この利用者は、いつ、どの強さで、この RP にログインしたか | この API を呼んでよいか |
| アクセストークン（AT） | このクライアントは、このリソースに、どの範囲でアクセスしてよいか | 利用者が今ログインしているか（AT は利用者がいる証拠ではない） |

根拠：OpenID Connect Core 1.0 §2、RFC 9068 §2.2、NIST SP 800-63B-4 §5.1.2

<a id="unit"></a>

## 2. 仕様上の単位

| 観点 | ID トークン | AT（JWT の場合） |
| --- | --- | --- |
| 宛先（`aud`） | クライアントの `client_id` | リソースサーバー（RFC 8707 の `resource` で絞る） |
| 種類の印（`typ`） | 仕様上の決まった値はない（`JWT` か省略が多い） | `at+jwt`（RFC 9068 §2.1） |
| 受け手が確かめること | `iss`・`aud`・`exp`・`nonce`・`azp` など（OIDC Core §3.1.3.7） | `typ`・`iss`・`aud`・`exp`、`scope` など（RFC 9068 §4） |
| 持つ者 | クライアント | クライアント（送信者制約なら鍵を持つ者） |
| 寿命 | 短命。セッションの長さではない | 短命（1 時間以内とすべき） |

根拠：OpenID Connect Core 1.0 §3.1.3.7、RFC 9068 §2.1、RFC 9068 §4、RFC 8707 §2、NIST IR 8587 §5.3.1.1

<a id="table"></a>

## 3. 対比

| 観点 | ID トークン | AT |
| --- | --- | --- |
| API に送るか | 送らない・受け入れない | 送る |
| 寿命の意味 | ログインの確認の期限。RP のセッションの長さと混同しない | API で受け入れる期限 |
| 載せてよいもの | 利用者の識別子と、ログインの事実（`auth_time`・`acr`・`amr`） | 認可に使う最小限のクレーム |
| ほかのトークンとの区別 | Logout Token（`typ: logout+jwt`、`nonce` なし）とも取り違えない | 内部の AT・Txn-Token とも `typ`・`aud` で区別する |

根拠：slide:p01-id-token-vs-access-token、slide:p08-token-types-lifetimes、slide:p08-logout、RFC 8725 §3.11

<a id="not-covered"></a>

## 4. 扱わないこと

- JWT でない AT（参照型・opaque）の検証は扱わない。参照型の判断は [carry-vs-query.md](carry-vs-query.md)
- 外部の IdP の AT を内部に持ち込むかは、この表ではなく入口の交換（template:profiles/P5_internal_propagation#edge-conversion）で決める
- `typ` を見ない古いライブラリでの区別の方法（`aud` の値の分け方など）は扱わない。共通の検証部品で `typ` を確かめる

根拠：slide:p01-self-contained-vs-reference、slide:p06-edge-exchange

<a id="misuse"></a>

## 5. 典型的な誤用

| # | 誤用 | 起きること | 見つける問い |
| --- | --- | --- | --- |
| m-1 | ID トークンを API に送り、API が受け入れる | `aud` がクライアントの ID なので、宛先の確認ができない。別のクライアントの ID トークンでも通りうる | `q-typ-distinguishes`・`ap-1-3` |
| m-2 | ID トークンの `exp` をログインセッションの寿命にする | セッションが数分で切れる、または ID トークンを延命する | `q-auth-context-semantics`・`q-session-rt-bounds` |
| m-3 | `typ: at+jwt` を名乗るのに、RFC 9068 の必須（`client_id` など）がない | 受け手の検証部品が拒否するか、検証を緩める | `q-typ-distinguishes` |
| m-4 | 外部の AT を内部のサービスにそのまま流す | 内部の `aud`・寿命・クレームの規則が当たらない | `cf-03`・`ap-2-6` |
| m-5 | AT を「利用者が今いる」証拠として、追加認証や承認を省く | 利用者のいない処理（ジョブ・エージェント）で高リスクの操作が通る | `q-step-up-by-rs` |

根拠：slide:p01-id-token-vs-access-token、slide:p06-flow-browser-to-db、slide:p08-token-types-lifetimes、RFC 9068 §2.2
<!-- req:p01-id-token-vs-access-token.R1 req:p06-flow-browser-to-db.R2 req:p08-token-types-lifetimes.R2 -->

<a id="evidence"></a>

## 6. 根拠

- OpenID Connect Core 1.0 §2（ID トークン）・§3.1.3.7（検証）
- RFC 9068 §2.1（`at+jwt`）・§2.2（必須のクレーム）・§4（検証）
- RFC 8725 §3.11（明示的な型）、RFC 8707 §2（宛先）
- ガイド：slide:p01-id-token-vs-access-token、slide:p06-flow-browser-to-db

根拠：OpenID Connect Core 1.0 §2、RFC 9068 §2.1、RFC 8725 §3.11、slide:p01-id-token-vs-access-token
