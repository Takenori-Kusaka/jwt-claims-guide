<!-- template_version: 0.4.0 -->
# 対比表：JWS と JWE

JWS（署名）は改ざんを防ぎ、JWE（暗号化）は流出を防ぎます。署名だけの JWT のペイロードは、持つ者・経由する全ホップ・ログの誰でも読めます（slide:p09-jws-is-readable）。JWE は最後の手段で、使うと 4 つの影響が出ます（slide:p09-jwe-sd-jwt）。

- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施

<a id="question"></a>

## 1. 解く問い

| 仕組み | 解く問い | 解かない問い |
| --- | --- | --- |
| JWS | 途中で書き換えられていないか（完全性と、鍵の持ち主の確認） | 誰に読まれるか |
| JWE | 決めた相手（復号の鍵を持つ者）以外に読まれないか（秘匿） | 誰が作ったか（JWE だけでは発行者を確かめられない。署名してから暗号化する） |

根拠：RFC 7515 §1、RFC 7516 §1、RFC 7519 §11.2

<a id="unit"></a>

## 2. 仕様上の単位

| 観点 | JWS | JWE |
| --- | --- | --- |
| 形 | ヘッダー.ペイロード.署名（Base64url、読める） | ヘッダー.暗号化した鍵.IV.暗号文.認証タグ |
| 鍵 | 発行者の署名鍵。受け手は公開鍵（JWKS） | 受け手（復号する者）の鍵。発行者は受け手の公開鍵で暗号化する |
| 両方を使うとき | 内側を JWS、外側を JWE にする（ネストした JWT。署名してから暗号化） | 受け手は外側を復号し、内側の署名と発行者も検証する |

根拠：RFC 7515 §1、RFC 7516 §1、RFC 7519 §11.2、RFC 8725 §3.3

<a id="table"></a>

## 3. 対比（JWE にしたときの 4 つの影響）

| 影響 | JWS のとき | JWE にしたとき | 台帳・目録の欄 |
| --- | --- | --- | --- |
| サイズ | ペイロードの Base64url と署名 | 暗号化した鍵・IV・認証タグが加わり、ネストならさらに内側の JWS 全体が暗号文になる。ヘッダー・Cookie の上限に近づく | `registry:token_types#size`（`lint:R8`） |
| 入口でクレームを読めなくなる | 入口・ゲートウェイがクレームで経路を選べる・ヘッダーに写せる | 入口が復号の鍵を持たなければ、クレームでの経路の選択・転記・ログができない。入口に鍵を持たせれば、入口も読める相手になる | `registry:token_types#visible_to`・`registry:token_types#jwe` |
| 複数の宛先への暗号化 | 1 枚を何人が読んでもよい | 受け手ごとに暗号化する（JSON の直列化の複数の宛先か、宛先ごとに別のトークン）。宛先を絞る設計と組になる | `registry:token_types#jwe`（`decryptors`）、`registry:hops#aud` |
| 鍵の管理 | 発行者の署名鍵のローテーションだけ | 受け手ごとの暗号化の鍵の配布・ローテーション・失効が増える。受け手の鍵が漏れれば、過去のトークンも読める | `registry:token_types#key_rotation` |

根拠：slide:p09-jwe-sd-jwt、RFC 7516 §7.2、slide:p04-size-budget

<a id="not-covered"></a>

## 4. 扱わないこと

- 選んだ項目だけを開示する SD-JWT は扱わない（slide:p09-jwe-sd-jwt を見る）
- 暗号のアルゴリズムと鍵の長さの選び方は扱わない。独自の暗号は専門家に回す（`review:escalation#custom-crypto`）
- トークンに載せない（API で取りに行く）という選択は [carry-vs-query.md](carry-vs-query.md)。秘匿が要るなら、まず載せないことを検討する

根拠：slide:p09-do-not-carry、slide:p09-jwe-sd-jwt

<a id="misuse"></a>

## 5. 典型的な誤用

| # | 誤用 | 起きること | 見つける問い |
| --- | --- | --- | --- |
| m-1 | 署名しているから中身は見えないと考える | ブラウザ・中継・ログが個人情報を読む | `q-payload-readable`・`q-confidential-reaches-reader` |
| m-2 | JWE にしたが、入口に復号の鍵を持たせる・ログに復号後の値を出す | 読める相手が減っていない | `q-confidential-reaches-reader`・`q-token-logging` |
| m-3 | JWE だけで、内側を署名しない・内側の署名を検証しない | 受け手の公開鍵を知る誰でもトークンを作れる | `q-nested-jwt-both-layers` |
| m-4 | 署名の保護が外れた後の値（ヘッダー・DB の文脈）を、署名済みの値として認可に使う | 写し先を書ける者のなりすまし | `q-unwrapped-value-authz`・`ap-2-5` |
| m-5 | JWE のサイズの増加を計算しない | 上限を超えて黙って欠ける・要求が失敗する | `q-size-limit` |
| m-6 | 秘匿の代わりに、トークン全文をログ・URL に残す | ログ・履歴からの流出 | `ap-2-8`・`q-token-not-in-url` |
| m-7 | 認証の秘密・生の個人情報を、暗号化すれば載せてよいと考える | 受け手の鍵が漏れると全部読める。載せない・派生値にするのが先 | `q-no-secret-or-raw-pii`・`q-derived-value` |

根拠：slide:p09-jws-is-readable、slide:p09-jwe-sd-jwt、slide:p09-logs-traces、RFC 8725 §3.3

<a id="evidence"></a>

## 6. 根拠

- RFC 7515 §1（JWS）、RFC 7516 §1・§7.2（JWE と JSON の直列化）、RFC 7519 §11.2（署名と暗号化の順）、RFC 8725 §3.3（すべての暗号の操作を検証する）
- ガイド：slide:p01-jwt-structure、slide:p09-jws-is-readable、slide:p09-jwe-sd-jwt

根拠：RFC 7515 §1、RFC 7516 §1、RFC 7519 §11.2、slide:p09-jwe-sd-jwt
