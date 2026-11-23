<!-- template_version: 0.3.0 -->
# トークンの検証（modules/M_token_validation）

> テンプレートです。候補と検討の問いだけを載せ、採否の理由の見本は載せません（理由の写し書きを防ぐため。#4 の方針）。判断は台帳（claims.yaml など）に 1 回だけ書き、ここからは ID で参照します。

- 使う場面：JWT を受け取るすべての受け手（API・入口・ツールサーバー・DB やブローカーのトークン認証）の検証の設定を決めるとき。受け手ごとに設定を散らさず、組織で 1 つに決める（6.）
- 組み合わせ：どのプロファイルとも組み合わせる。テナントごとの発行者は `template:modules/M_multitenancy`、送信者制約の照合は `template:modules/M_sender_constraint`
- Lite での扱い：〔Full：記入／Lite：参照〕。Lite では、答えをトークン目録の列（`typ`・`alg_allowlist`・`issuers`・`required_claims`・`max_clock_skew`・`key_rotation`・`unknown_kid`・`jwks_cache_ttl`・`key_source`）に書く。これらは採用した JWT の行では R1 の必須の列で、Lite でも書く
- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施。

<a id="validation-order"></a>
## 1. 検証の順序〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_token_validation#validation-order`
<!-- req:p01-validation-order.R1 req:p01-validation-order.R9 req:p01-attack-patterns.R7 -->

決めること：受け手が、どの独自クレームを読むより先に確かめる項目と順序。署名を確かめる前のクレームは、誰でも書ける文字列にすぎません。

| # | 確かめること | 検討の問い | 根拠 |
| --- | --- | --- | --- |
| 1 | 形式 | ピリオドで区切った 3 部分か。JWE（5 部分）と区別してから検証を始めるか | RFC 7519 §7.2、slide:p01-validation-order |
| 2 | `alg` | 許可リストに入っているか（3.） | RFC 8725 §3.1 |
| 3 | 署名 | 事前に設定した発行者の鍵で確かめるか（ヘッダーの鍵を信じない。4.） | RFC 8725 §3.10、RFC 7515 §5.2 |
| 4 | `iss` | 想定の発行者と完全一致か（2.） | RFC 8725 §3.8 |
| 5 | `aud` | 自分が含まれるか（5.） | RFC 7519 §4.1.3、RFC 8725 §3.9 |
| 6 | `exp`・`nbf`・`iat` | 期限内か。ずれは何秒まで許すか（8.） | RFC 7519 §4.1.4・§4.1.5 |
| 7 | `typ` | トークンの種類が想定どおりか（7.） | RFC 8725 §3.11、RFC 9068 §4 |
| 8 | 必須クレームと型 | 必須のクレームが揃い、型が正しいか | RFC 9068 §4、slide:p04-reject-missing-required |
| 9 | 独自クレーム | テナント・権限を表すクレームを、1〜8 を全部通った後にだけ読むか | slide:p01-attack-patterns、slide:p01-validation-order |

記入欄：

| 受け手 | 順序を守る仕組み（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
|  |  |  | `token_types[].required_claims`、`hops[].validates` |

根拠：slide:p01-validation-order、RFC 9068 §4、RFC 8725 §3.1・§3.8・§3.9・§3.11

<a id="issuer"></a>
## 2. 発行者（iss）〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_token_validation#issuer`
<!-- req:p05-multitenancy.R2 req:p07-db-token-auth.R3 -->

決めること：受け入れる発行者の許可リストと、発行者ごとの鍵の取得元。鍵がその発行者のものであることを確かめます（別の発行者の鍵で署名したトークンを、その発行者のものとして受けない）。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 許可リスト | 受け入れる `iss` を列挙し、完全一致で比べるか | 列挙して完全一致／前方一致・パターン（避ける） | RFC 8725 §3.8、slide:p05-multitenancy |
| テンプレート形式の iss | `{tenantid}` を含む iss（Entra のマルチテナント）を、どう比べるか | `tid` で置き換えてから完全一致で比べる／許可したテナントだけ | slide:p05-multitenancy、jwt-claims-casestudy@080b8da:B10 |
| 鍵と発行者の対応 | 鍵を、その `iss` のメタデータの `jwks_uri` から取るか | 発行者ごとの `jwks_uri`／鍵の集合を共有（避ける） | RFC 8414 §2、slide:p00-incident-signature-valid |
| DB・ブローカー | DB やブローカーがトークンで認証するとき、発行者・`aud`・JWKS を設定しているか。署名を確かめない既定の実装（開発用）を本番で使っていないか | 設定して確かめる／製品の既定のまま（避ける） | slide:p07-db-token-auth |

記入欄：

| 受け手 | 受け入れる発行者と鍵の取得元（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
|  |  |  | `token_types[].issuers`（`iss`・`jwks_uri`）、`claims[].issuers` |

根拠：RFC 8725 §3.8、slide:p05-multitenancy、slide:p00-incident-signature-valid、slide:p07-db-token-auth

<a id="alg"></a>
## 3. アルゴリズム（alg）〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_token_validation#alg`

決めること：受け入れる署名のアルゴリズムの許可リスト。トークンのヘッダーの `alg` に従って検証の方式を変えないこと。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 許可リスト | どの `alg` を受け入れるか。鍵ごとに 1 つに決めるか | 発行者の鍵に合わせた 1 つ（RS256・ES256・PS256 など） | RFC 8725 §3.1、slide:p01-dangerous-header-params |
| `none` | `none` を拒むか | 拒む | RFC 8725 §3.1、jwt-claims-casestudy@080b8da:G1 |
| 対称と非対称の混同 | 公開鍵を HMAC の秘密として使わせる経路（RS256 → HS256）がないか | 鍵の種類とアルゴリズムを対にして固定する | RFC 8725 §3.1、jwt-claims-casestudy@080b8da:G2 |

記入欄：

| 種別 | 許可する alg（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
|  |  |  | `token_types[].alg_allowlist` |

根拠：RFC 8725 §3.1、slide:p01-dangerous-header-params

<a id="header-params"></a>
## 4. ヘッダーの危険なパラメータ〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_token_validation#header-params`
<!-- req:p01-dangerous-header-params.R3 -->

決めること：ヘッダーの `kid`・`jku`・`x5u`・`jwk`・`x5c` の扱い。鍵は設定した取得元からだけ取り、ヘッダーが指す鍵や場所をたどりません。

| パラメータ | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| `kid` | 事前に取得した鍵の一覧の中だけで探すか。ファイルのパスや検索式に使っていないか | 一覧の中だけで探す | RFC 8725 §3.10、RFC 7515 §4.1.4（kid はヒント）、slide:p01-dangerous-header-params、jwt-claims-casestudy@080b8da:G3 |
| `jku`・`x5u` | ヘッダーの URL をたどらないか | たどらない（取得元は `jwks_uri`） | RFC 8725 §3.10、jwt-claims-casestudy@080b8da:G4 |
| `jwk`・`x5c` | ヘッダーに埋め込まれた鍵を信じないか | 信じない | RFC 8725 §3.10、jwt-claims-casestudy@080b8da:G5 |

記入欄：

| 決めること | 決めたこと（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 鍵の取得元 |  |  | `token_types[].key_source`（`header_key_params: reject`） |

根拠：RFC 8725 §3.10、RFC 7515 §4.1.4、slide:p01-dangerous-header-params

<a id="audience"></a>
## 5. 宛先（aud）〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_token_validation#audience`
<!-- req:p02-registered-claims.R3 -->

決めること：受け手が自分を表す値と、`aud` の照合のしかた。`aud` は文字列のことも配列のこともあります。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 形 | 文字列と配列の両方を受け付け、自分が含まれなければ拒否するか | 両方を受け付ける | RFC 7519 §4.1.3、slide:p02-registered-claims |
| 自分の値 | 受け手を表す値（URI・クライアント ID）を何にするか | API の URI（resource indicator と同じ値）／クライアント ID | RFC 8707 §2、slide:p06-narrow-downstream |
| 既定の宛先 | IdP の既定の宛先（Keycloak の `account` など）を、API の宛先として扱っていないか | 扱わない（Audience マッパーで API を入れる） | slide:p03-keycloak-aud-lightweight |
| `aud` の無い IdP | `aud` の無いトークン（Cognito の AT）をどこで扱うか | 入口で `client_id` を照合して正規化する（P5） | slide:p03-cognito-token-use、`template:profiles/P5_internal_propagation#edge-conversion` |
| 複数の宛先 | 宛先が複数のトークンを受け入れるか | 1 つに絞る／複数を許す | slide:p10-four-questions |

記入欄：

| 受け手 | 自分を表す値（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
|  |  |  | `token_types[].aud`、`hops[].aud`、`claims[].enforced_at`（aud の行） |

根拠：RFC 7519 §4.1.3、RFC 8725 §3.9、slide:p02-registered-claims

<a id="time"></a>
## 6. 時刻（exp・nbf・iat）〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_token_validation#time`

決めること：`exp` を必須にするか、時計のずれを何秒まで許すか、`exp − iat` を寿命の上限と比べるか。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| `exp` の必須 | `exp` の無いトークンを拒むか（ライブラリによっては無くても通る） | 拒む（必須クレームに入れる） | RFC 9068 §2.2、slide:p01-library-defaults、jwt-claims-casestudy@080b8da:G6 |
| ずれ | 時計のずれを何秒まで許すか | 秒数を決める（ライブラリの既定を確かめる） | RFC 7519 §4.1.4、slide:p01-library-defaults |
| `nbf` | `nbf` があれば確かめるか | 確かめる | RFC 7519 §4.1.5 |
| 寿命の上限 | `exp − iat` が、目録の寿命の上限を超えるトークンを拒むか | 拒む／確かめない | slide:p08-token-types-lifetimes、筆者の提案：受け手が発行者の寿命の設定の誤りを検出する（追跡 #6） |

記入欄：

| 種別 | 許すずれ・寿命の確かめ方（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
|  |  |  | `token_types[].max_clock_skew`・`max_lifetime` |

根拠：RFC 7519 §4.1.4・§4.1.5、slide:p01-library-defaults

<a id="typ"></a>
## 7. 種類（typ）〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_token_validation#typ`
<!-- req:p03-confusing-differences.R5 -->

決めること：トークンの種類（AT・ID トークン・Txn-Token・Logout Token・DPoP proof など）を、IdP ごとにどの値で確かめるか。同じ発行者の別の種類のトークンを、取り違えて受け入れないこと。

| IdP・種類 | 検討の問い | 確かめる値の候補 | 根拠 |
| --- | --- | --- | --- |
| JWT の AT（RFC 9068） | ヘッダーの `typ` が `at+jwt` か | `typ: at+jwt` | RFC 9068 §2.1・§4 |
| Cognito | `typ` の代わりに `token_use` で区別するか | `token_use: access` | slide:p03-cognito-token-use |
| Entra ID | アプリのトークンか利用者のトークンか（`idtyp`）を区別するか | `idtyp`（任意のクレーム） | slide:p03-confusing-differences |
| ID トークン | API で ID トークンを拒むか | `typ`・`aud` で拒む | slide:p01-id-token-vs-access-token、jwt-claims-casestudy@080b8da:G11 |
| 組織が作る種類 | 内部トークン・Txn-Token に、種類ごとに別の `typ` を付けるか | `txntoken+jwt` など、種類ごとに別の値 | RFC 8725 §3.11、draft-ietf-oauth-transaction-tokens-11 §9.1 |

記入欄：

| 種別 | 確かめる値（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
|  |  |  | `token_types[].typ` |

根拠：RFC 8725 §3.11、RFC 9068 §2.1、slide:p03-confusing-differences

<a id="key-rotation"></a>
## 8. 鍵のローテーション〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_token_validation#key-rotation`

決めること：発行者の鍵の入れ替えの手順（公開 → 待つ → 切り替え → 廃止）と、受け手が追従する条件。古い鍵は、その鍵で署名したトークンの受け入れの上限が過ぎてから外します。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 周期 | 定期の入れ替えの周期と、緊急の入れ替えの手順 | 周期を決める／発行者に任せる（予告なく変わりうる） | slide:p01-key-rotation-jwks、NIST SP 800-63C-4 §3.6 |
| 先に公開する時間 | 新しい鍵を署名に使う前に、JWKS に何秒公開しておくか | 受け手のキャッシュの TTL と取り直しの間隔の和より長く | OpenID Connect Core 1.0 §10.1.1、slide:p01-key-rotation-jwks |
| 古い鍵を外す時間 | 古い鍵を外すまで何秒待つか | その鍵で署名した最後のトークンの受け入れの上限（寿命＋ずれ）より長く | slide:p01-key-rotation-jwks |
| 埋め込み | 公開鍵をコードや設定に埋め込んでいないか | 埋め込まない（`jwks_uri` から取る） | slide:p01-key-rotation-jwks |

記入欄：

| 発行者 | 周期と待つ時間（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
|  |  |  | `token_types[].key_rotation`（`period_days`・`publish_before_use_seconds`・`retire_after_seconds`） |

根拠：OpenID Connect Core 1.0 §10.1.1、slide:p01-key-rotation-jwks、CSRB 報告書（Storm-0558）勧告 6

<a id="jwks-cache"></a>
## 9. JWKS のキャッシュと知らない kid〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_token_validation#jwks-cache`

決めること：JWKS をどれだけキャッシュするか、知らない `kid` を見たときに取り直す間隔の下限、取り直しに失敗したときの動き。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| キャッシュの TTL | JWKS を何秒キャッシュするか（消した鍵を信じ続けない長さか） | 秒数を決める | slide:p01-key-rotation-jwks |
| 知らない kid | 知らない `kid` で取り直すとき、最短の間隔を置くか（要求ごとに取り直さない） | 間隔の下限を置く | OpenID Connect Core 1.0 §10.1.1、slide:p01-key-rotation-jwks |
| 負のキャッシュ | 取り直しても無い `kid` を、しばらく取り直さずに拒むか | 負のキャッシュの秒数を決める／置かない | slide:p01-key-rotation-jwks |
| 取得の失敗 | JWKS が取れないとき、最後に取れた鍵で続けるか、全部を拒むか | 最後に取れた鍵で続ける／拒む | slide:p01-key-rotation-jwks |

記入欄：

| 受け手 | TTL・間隔・失敗時（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
|  |  |  | `token_types[].jwks_cache_ttl`・`unknown_kid` |

根拠：OpenID Connect Core 1.0 §10.1.1、slide:p01-key-rotation-jwks

<a id="library-config"></a>
## 10. 検証ライブラリと明示の設定〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_token_validation#library-config`
<!-- req:p00-incident-signature-valid.R5 req:p01-library-defaults.R1 req:p01-library-defaults.R3 req:p01-library-defaults.R5 -->

決めること：受け手ごとに使う検証ライブラリと版、既定に任せずに明示する設定。ライブラリの既定値は安全側とは限りません（aud を既定で確かめない、exp が無くても通す、など）。どのクレームを何と照合するかは、組織で決めて書きます。

| 設定 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| ライブラリと版 | どのライブラリの、どの版を使うか | 受け手ごとに書く | slide:p01-library-defaults |
| `audience`・`issuer` | 値を渡したときだけ検証するライブラリで、値を必ず渡しているか | 明示して渡す | slide:p01-library-defaults、RFC 8725 §3.8・§3.9 |
| `algorithms` | 許可するアルゴリズムを明示しているか | 明示する（3.） | RFC 8725 §3.1、slide:p01-library-defaults |
| 必須クレーム | `exp` などの必須を明示しているか（golang-jwt の `WithExpirationRequired` など） | 明示する | slide:p01-library-defaults |
| 時刻のずれ | ライブラリの既定のずれ（例：5 分）を確かめ、組織の値に設定したか | 組織の値に設定する | slide:p01-library-defaults |
| 署名鍵そのものの確認 | 署名鍵そのものを確かめる設定が既定で無効のライブラリ（Microsoft.IdentityModel など）で、有効にしたか | 有効にする／確かめない | slide:p01-library-defaults |
| 照合の一覧 | どのクレームを何と照合するか（`iss` と鍵、テナントと `iss`、`aud` と自分）を書いたか | 台帳の `enforced_at` に書く | slide:p00-incident-signature-valid |

記入欄：

| 受け手 | ライブラリと版（書き手が書く） | 明示した設定（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- | --- |
|  |  |  |  | `claims[].enforced_at`、`token_types[].alg_allowlist`・`max_clock_skew` |

根拠：slide:p01-library-defaults、slide:p00-incident-signature-valid、RFC 8725 §3.1

<a id="shared-validator"></a>
## 11. 組織共通の検証部品〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_token_validation#shared-validator`
<!-- req:p00-why-hard.R2 req:p00-incident-signature-valid.R5 req:p01-library-defaults.R4 req:p11-contract-test-gaps.R3 req:p11-translation-layer.R3 req:p11-pre-add-questions-2.R4 -->

決めること：検証と解析を各サービスに任せず、アルゴリズム・発行者・宛先・必須クレームを固定した組織共通の部品を配るか。配るなら、その部品だけを通してクレームを読ませる方法。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 配るか | 受け手が複数のとき、共通の検証部品を配るか | 配る／サービスごとに実装する | slide:p00-why-hard、slide:p01-library-defaults、CSRB 報告書（Storm-0558）勧告 6 |
| 固定する項目 | 部品で固定するのは何か | alg・発行者と鍵・宛先・必須クレーム・型・名前空間 | slide:p01-library-defaults、jwt-claims-casestudy@080b8da:B13 |
| 読ませ方 | 各サービスが生の JSON を自分で解析していないか | 部品の公式のパーサーだけで読む | slide:p11-translation-layer、slide:p11-contract-test-gaps |
| 版の管理 | 部品の採用率と版をどう測るか | 依存関係の走査（`template:00_core#operational-metrics`） | slide:p11-audit-metrics |
| 新しい共有クレーム | 共有クレームを足すとき、検証を部品に入れるか（追加前の問い 16） | 入れる／入れない | slide:p11-pre-add-questions-2、`template:claim_request#q16` |

記入欄：

| 決めること | 決めたこと（書き手が書く） | 理由（書き手が書く） | 台帳の ID |
| --- | --- | --- | --- |
| 配るか・部品の名前と版 |  |  | `claims[].consumer_access_path` |
| 固定する項目 |  |  |  |

根拠：slide:p01-library-defaults、slide:p11-translation-layer、slide:p11-contract-test-gaps、CSRB 報告書（Storm-0558）勧告 6

<a id="nested-jwt"></a>
## 12. ネストした JWT（署名＋暗号化）〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_token_validation#nested-jwt`
<!-- req:p09-jwe-sd-jwt.R2 -->

決めること：JWE を使う種別で、外側（暗号）と内側（署名）の両方を検証する設定。復号できたことは、発行者が署名したことを意味しません。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| ネストの順序 | 署名してから暗号化しているか | 署名してから暗号化（内側は JWS） | RFC 7519 §11.2、slide:p09-jwe-sd-jwt |
| 内側の検証 | 復号した後、内側の JWS を 1.〜9. の手順で検証するか | 検証する（`alg_allowlist`・`issuers` を内側にも当てる） | RFC 7519 §7.2、slide:p09-jwe-sd-jwt |
| 外側の許可 | 鍵の管理のアルゴリズム（`alg`）と暗号のアルゴリズム（`enc`）の許可リストを持つか | 持つ | RFC 7516 §4.1.1・§4.1.2、RFC 8725 §3.1 |

記入欄：

| 種別 | 外側と内側の検証の設定（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
|  |  |  | `token_types[].jwe`（`nesting`・`decryptors`） |

根拠：RFC 7519 §11.2・§7.2、slide:p09-jwe-sd-jwt

<a id="registry-map"></a>
## 13. 台帳・目録との対応

項目 ID：`template:modules/M_token_validation#registry-map`

| 決めること | 列 |
| --- | --- |
| 種類・アルゴリズム・発行者 | `token_types[].typ`・`alg_allowlist`・`issuers` |
| 必須クレーム・時刻 | `token_types[].required_claims`・`max_clock_skew`・`max_lifetime` |
| 鍵 | `token_types[].key_source`・`key_rotation`・`unknown_kid`・`jwks_cache_ttl`・`signing_key_scope` |
| 暗号 | `token_types[].jwe` |
| 何を何と照合するか | `claims[].enforced_at`、`hops[].validates` |

根拠：templates/registry/README.md の 3.2、slide:p01-validation-order
