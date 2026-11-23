<!-- template_version: 0.3.0 -->
# P1 人がブラウザで使う Web（profiles/P1_human_web）

> テンプレートです。候補と検討の問いだけを載せ、採否の理由の見本は載せません（理由の写し書きを防ぐため。#4 の方針）。判断は台帳（claims.yaml など）に 1 回だけ書き、ここからは ID で参照します。

- 使う場面：利用者（人）がブラウザでログインし、Web アプリ（SPA・サーバー側の画面）を通して API を呼ぶ境界。`00_core.md` の「範囲と信頼の境界」で、ブラウザとアプリの間の境界に P1 を書く
- 組み合わせ：入口で内部のトークンに作り替えるなら P5（`template:profiles/P5_internal_propagation#edge-conversion`）。エージェントが利用者の代理で動くなら P4。検証の設定は `template:modules/M_token_validation`、送信者制約は `template:modules/M_sender_constraint`
- Lite での扱い：各項目は〔Full：記入／Lite：参照〕。Lite では問いを読み、決めたことは `00_core.md` の「既定から外れた点」と台帳（`token_types.yaml` の `stored_at`・`transport` など）に書く。既定の組み合わせ（BFF＋認可コード＋PKCE）から外れないなら、Lite で書くことは増えない（`templates/registry/README.md` の 3.3）
- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施。

<a id="bff-vs-spa"></a>
## 1. BFF とトークンを持つ SPA の判断表〔Full：記入／Lite：参照〕

項目 ID：`template:profiles/P1_human_web#bff-vs-spa`
<!-- req:p06-flow-browser-to-db.R1 req:p09-url-browser.R4 -->

決めること：ブラウザに何を置くか（セッションの Cookie だけか、AT・RT も置くか）と、トークンを持つ部品（BFF のサーバー、トークンを仲介するバックエンド、ブラウザの中の OAuth クライアント）。RFC 10017 は 3 つの構成を並べ、悪意のある JavaScript に対する脅威を構成ごとに分析しています。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 構成 | どの部品が OAuth のクライアントになり、トークンを受け取るか | BFF（RFC 10017 §6.1）／トークンを仲介するバックエンド（§6.2）／ブラウザの中の OAuth クライアント（§6.3） | RFC 10017 §6 |
| AT の置き場所 | ブラウザの JavaScript から AT が読めるか。読めるなら、XSS で何が持ち出されるか | BFF のサーバー（ブラウザには Cookie だけ）／ブラウザのメモリ／Web Worker／Service Worker／永続の保存領域 | RFC 10017 §5・§8、slide:p06-flow-browser-to-db |
| RT の置き場所 | RT をブラウザに渡すか。渡すなら、ローテーションか送信者制約のどちらで守るか | ブラウザに渡さない（BFF が持つ）／渡してローテーション＋再利用の検知／渡して送信者制約（DPoP） | RFC 10017 §6.1.2.2・§6.3.2.3、RFC 9700 §4.14.2 |
| クライアントの種類 | クライアント認証のできる機密クライアントか、公開クライアントか | 機密（BFF・仲介のバックエンド）／公開（ブラウザの中のクライアント） | RFC 9700 §2.2.2、`issuance_profile.client_type` |
| Cookie の守り | セッションの Cookie を、CSRF と盗み出しからどう守るか | `HttpOnly`・`Secure`・`SameSite`・`__Host-` 接頭辞（RFC は `__Host-Http-` を推奨）、CSRF の対策（同一オリジンの確認など） | RFC 10017 §6.1.3.2・§6.1.3.3 |
| ID トークン | ID トークンを API に送らないことを、どこで保証するか | BFF のサーバーに留める／ブラウザに渡す | slide:p06-flow-browser-to-db、slide:p01-id-token-vs-access-token |
| 運び方 | AT を API へどう運ぶか | `Authorization: Bearer`／`Authorization: DPoP`／BFF が付け直す（ブラウザは Cookie） | RFC 6750 §2.1、RFC 9449 §7.1 |

記入欄（書き手が埋める。台帳に書いた行の ID で参照する）：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 構成 |  |  | `issuance_profile.client_type` |
| AT の置き場所 |  |  | `token_types[].stored_at`（AT の行） |
| RT の置き場所 |  |  | `token_types[].stored_at`・`rt_rotation`（RT の行）、`issuance_profile.rt_strategy` |
| Cookie の守り |  |  | `token_types[].note`（BFFSESSION の行） |
| ID トークンの置き場所 |  |  | `token_types[].stored_at`・`visible_to`（IDT の行） |
| 運び方 |  |  | `token_types[].transport` |

根拠：RFC 10017 §6、slide:p06-flow-browser-to-db、slide:p09-url-browser、RFC 9700 §4.14.2、筆者の提案：3 つの構成を同じ観点の表で比べる（追跡 #4）

<a id="url-exposure"></a>
## 2. トークンと認可のパラメータを URL から外す〔Full：記入／Lite：参照〕

項目 ID：`template:profiles/P1_human_web#url-exposure`
<!-- req:p09-url-browser.R2 -->

決めること：認可要求・認可応答・API の呼び出しのそれぞれで、トークンや認可のパラメータが URL（履歴・アクセスログ・Referer・HAR ファイル）に残らない運び方。

| 場面 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 認可要求 | 認可要求のパラメータ（scope・authorization_details など）がブラウザの URL に出るか | PAR（RFC 9126）で URL から外す／JAR（RFC 9101）で署名する／そのまま URL に出す | RFC 9126 §2、FAPI 2.0 Security Profile（Final）§5.3.2.2、slide:p09-url-browser |
| 認可応答 | 認可コードが URL のクエリに出るか | `response_mode=form_post`／クエリ（認可コードだけ。1 回限り） | OAuth 2.0 Form Post Response Mode（2015）、RFC 9700 §4.2 |
| API の呼び出し | AT をクエリパラメータで送る経路が残っていないか | Authorization ヘッダーだけ／クエリを受け付ける経路がある（ダウンロードの URL など） | RFC 9700 §4.3.2、RFC 6750 §2.3 |
| ログと共有物 | URL・ヘッダーを記録するログや HAR ファイルに、トークンが残るか | 記録の前に伏せる／記録しない | NIST IR 8587 §5.3.1.5、slide:p09-logs-traces |
| 認可応答の発行者 | 認可応答の `iss` を確かめるか（複数の AS を使う場合の mix-up） | RFC 9207 の `iss` を照合する／照合しない | RFC 9207 §2.4 |

記入欄：

| 場面 | 選んだ運び方（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 認可要求 |  |  | `issuance_profile.request_protection` |
| 認可応答 |  |  | `token_types[].transport`（CODE の行） |
| API の呼び出し |  |  | `token_types[].transport`（AT の行） |
| ログ |  |  | `token_types[].log_policy` |

根拠：slide:p09-url-browser、RFC 9700 §4.2・§4.3.2、RFC 9126 §1、OAuth 2.0 Form Post Response Mode（2015）、RFC 9207 §2.4

<a id="login-id-token"></a>
## 3. ログインと ID トークンの扱い〔Full：記入／Lite：参照〕

項目 ID：`template:profiles/P1_human_web#login-id-token`

決めること：ログインの確かめ方（ID トークンの検証）と、ID トークンの中身を誰が読むか。ID トークンはクライアント宛てで、API の認可には使いません。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 検証 | ID トークンの `iss`・`aud`（自分の client_id）・`exp`・`nonce`・`azp`（aud が複数のとき）を確かめるか | OpenID Connect Core 1.0 §3.1.3.7 の手順どおり／ライブラリの既定に任せる | OpenID Connect Core 1.0 §3.1.3.7 |
| 載せる属性 | 表示に使う属性（`name`・`email` など）を ID トークンで受けるか、UserInfo で取るか | ID トークン／UserInfo／どちらも使わない | OpenID Connect Core 1.0 §5.1・§5.3、slide:p04-carry-or-query |
| 認証の強さ | 画面の先へ進む前に `acr`・`auth_time` を確かめるか（`max_age` を付けて要求するか） | 確かめる（要求時に `max_age`・`acr_values`）／確かめない | OpenID Connect Core 1.0 §3.1.2.1、slide:p02-auth-strength-session |
| ブラウザへの露出 | ID トークンの個人情報が、ブラウザに届くか | BFF のサーバーだけ／ブラウザにも渡す | slide:p09-jws-is-readable |

記入欄：

| 観点 | 決めたこと（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 検証 |  |  | `token_types[].required_claims`（IDT の行） |
| 載せる属性 |  |  | `claims[].carried_in`・`confidential_from` |
| 認証の強さ |  |  | `claims[]`（acr・auth_time の行） |

根拠：OpenID Connect Core 1.0 §3.1.3.7、slide:p01-id-token-vs-access-token、slide:p09-jws-is-readable

<a id="session-logout"></a>
## 4. セッションとログアウト〔Full：記入／Lite：参照〕

項目 ID：`template:profiles/P1_human_web#session-logout`

決めること：アプリ（BFF）のセッション、IdP のセッション、RT の 3 つの寿命と、ログアウト・失効がそれぞれにどう届くか。ログアウトで消えるのはセッションと RT で、発行済みの AT は `exp` まで残ります。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 寿命 | アプリのセッションの無操作の期限と絶対的な上限を、IdP のセッション・RT とどう揃えるか | 揃える／アプリのほうを短くする | slide:p08-four-lifetimes、slide:p08-logout |
| IdP からの通知 | IdP のセッションが終わったことを、アプリはどう知るか | Back-Channel Logout（Logout Token）／Front-Channel Logout／次のリフレッシュの失敗で知る | OpenID Connect Back-Channel Logout 1.0 §2.4・§2.6、OpenID Connect Front-Channel Logout 1.0 §3 |
| Logout Token の検証 | `iss`・`aud`・`iat`・`exp`・`sub` か `sid`・`events` を確かめ、`nonce` があれば拒否するか。`jti` での再送の確認は任意（仕様は Optionally） | 仕様の手順どおり | OpenID Connect Back-Channel Logout 1.0 §2.6 |
| 利用者のログアウト | 利用者の操作でどこまで消すか | アプリのセッションだけ／IdP のセッションも（RP-Initiated Logout）／RT も失効（RFC 7009） | OpenID Connect RP-Initiated Logout 1.0 §2、RFC 7009 §2 |
| 発行済みの AT | ログアウトの後に残る AT の時間を許すか | `exp` まで許す（寿命で上限を決める）／API が問い合わせで止める | slide:p08-logout、slide:p08-revocation-propagation |

記入欄：

| 観点 | 決めたこと（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 寿命 |  |  | `token_types[].idle_timeout`・`max_lifetime`（BFFSESSION・SSO・RT の行） |
| IdP からの通知 |  |  | `token_types[]`（LOGOUT の行）、`catalog_answers.yaml` の該当のイベント |
| ログアウトの後の AT |  |  | `token_types[].revocation`（AT の行） |

根拠：slide:p08-logout、OpenID Connect Back-Channel Logout 1.0 §2.6、RFC 7009 §2

<a id="step-up-hook"></a>
## 5. 追加認証への入り口〔Full：記入／Lite：参照〕

項目 ID：`template:profiles/P1_human_web#step-up-hook`

決めること：API が「認証の強さが足りない」と返したときに、ブラウザ側のアプリがどう取り直すか。操作ごとの要求の強さは `00_core.md` の付録（`template:00_core#step-up`）で決めます。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 応答の受け方 | API の `WWW-Authenticate` の `error="insufficient_user_authentication"`・`acr_values`・`max_age` を、誰が読むか | BFF が読み、認可要求をやり直す／画面が読む | RFC 9470 §3・§4 |
| 取り直し | 追加認証の後、新しい AT を取るか、セッションの属性だけを更新するか | 新しい AT を取る／ID トークンの `acr` だけを見る | RFC 9470 §4、slide:p06-step-up-approval |

記入欄：

| 観点 | 決めたこと（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 応答の受け方 |  |  | `claims[]`（acr の行の `enforced_at`） |

根拠：RFC 9470 §3、slide:p06-step-up-approval

<a id="registry-map"></a>
## 6. 台帳・目録との対応

項目 ID：`template:profiles/P1_human_web#registry-map`

P1 の答えを書く台帳の列です。判断は台帳に 1 回だけ書き、この表は読む場所を示すだけです。

| 決めること | 列 |
| --- | --- |
| トークンの置き場所 | `token_types[].stored_at`（browser・bff_server など） |
| 読める相手 | `token_types[].visible_to`、`claims[].confidential_from` |
| 運び方 | `token_types[].transport`（URL で運べるのは認可コードと JARM の応答だけ。スキーマが拒む） |
| クライアントの種類・grant・要求の保護 | `issuance_profile.client_type`・`grants`・`request_protection` |
| RT の守り | `issuance_profile.rt_strategy`、`token_types[].rt_rotation` |
| セッションの寿命 | `token_types[].idle_timeout`・`max_lifetime`（kind: session） |

根拠：templates/registry/README.md の 3.2・3.3、slide:p06-flow-browser-to-db
