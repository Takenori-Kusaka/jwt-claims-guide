# 点検の依頼：ガイド本体の空白を埋めたスライドの事実（#10）

`templates/CONTRIBUTING.md` の 2.（完了の定義）と 3.（点検者の取り決め）による、独立点検のための一覧です。

> **点検済み（2026-11-22、全 88 件）。** 一覧は作成した側（Claude Opus 5.5 のセッション、ブランチ `issue-10-guide-gaps`）が書き、作成とは別の LLM のセッション 2 つ（前半 F01〜F44、後半 F45〜F88 と体裁）が一次資料に当たって点検した。点検の原文：https://github.com/Takenori-Kusaka/jwt-claims-guide/pull/34#issuecomment-7077107557 。結果は末尾の「4. 点検の結果」。人による点検と、作成者が 1 日以上空けた見直しは未実施。

## 対象

- 足したスライド 7 枚：`slide:p01-key-rotation-jwks`、`slide:p01-client-made-jwts`、`slide:p06-grant-types`、`slide:p08-four-lifetimes`、`slide:p08-reissue-triggers`、`slide:p08-logout`、`slide:p08-copies-outlive-token`
- 中身を変えたスライド 2 枚：`slide:p05-one-request-carries`（問いの表を分けた）、`slide:p06-issuance-hook`（client credentials のフック）
- Part 1・Part 8 の扉はノートの目次を直しただけで、新しい事実はない
- 本文・ノート・根拠の行のすべての事実を、下の表に 1 行ずつ挙げた。「筆者の推奨」「筆者の提案」と書いたものは事実ではないので、表には「推奨」として別に挙げた（事実と取り違えていないかを見てほしい）
- 作成者が取得して確かめた日：2026-11-22（各 URL を WebFetch で取得）。製品の文書は 2026-11-22 時点
- カタログ（#2、PR #32 で点検済み）の行から写した事実は、出どころの列に行の ID を書いた。PR #32 の点検は抜き取りなので、写した事実も点検の対象にしてほしい

## 1. 事実の一覧

### slide:p05-one-request-carries（問いの表を分けた）

| # | 述べたこと | 出どころ（版つき） | 結果 |
| --- | --- | --- | --- |
| F01 | 最も外側の act が今の代理者で、入れ子の内側の act は過去の代理者 | RFC 8693 §4.1 | OK |
| F02 | アクセス制御に使ってよいのは、トップレベルのクレームと今の代理者だけ。過去の代理者は参考の情報 | RFC 8693 §4.1（MUST only consider） | OK |
| F03 | req_wl は Txn-Token を求めた（発行させた）ワークロードを表す | draft-ietf-oauth-transaction-tokens-11 §9.2 | OK |
| F04 | 直接の通信相手は mTLS の相手の証明書（SPIFFE の X.509-SVID）で確かめる。トークンのクレームではない | SPIFFE X.509-SVID 仕様（一般的な記述。規範の文としての引用ではない） | OK |

### slide:p06-issuance-hook（client credentials のフック）

| # | 述べたこと | 出どころ | 結果 |
| --- | --- | --- | --- |
| F05 | Auth0 では client credentials の発行で credentials-exchange のトリガーが動き、アクセストークンにクレームを足せる | Auth0 Docs「Machine to Machine Trigger」（カタログ I05、a0_m2m） | OK |
| F06 | post-login で足すクレームは M2M の AT に載らない（と考える） | 推論（Login Flow の実行条件に client credentials がない。カタログ I05 の V34）。スライドのノートは「と考えてください」と書いた | 曖昧→直した |
| F07 | Cognito は、トリガーのイベントの版が V3_0 のときだけ、client credentials（と GetClientToken）の発行で発行前トリガーを呼ぶ（triggerSource は TokenGeneration_ClientCredentials） | AWS Cognito Developer Guide「Pre token generation Lambda trigger」 https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-pre-token-generation.html | OK |
| F08 | V3_0 は Essentials と Plus のプランで使え、M2M の分は MAU とは別の料金 | 同上「Event versions」 | OK |

### slide:p01-key-rotation-jwks

| # | 述べたこと | 出どころ | 結果 |
| --- | --- | --- | --- |
| F09 | 署名する側は鍵を jwks_uri の JWK Set に公開し、ヘッダーの kid で署名した鍵を示す。新しい鍵は定期的に足し、いつ使い始めるかは署名する側が決める | OpenID Connect Core 1.0（errata set 2）§10.1.1 | OK |
| F10 | 受け手は知らない kid を見たら jwks_uri から取り直す | 同上 §10.1.1 | OK |
| F11 | 使わなくなった鍵も、しばらく JWK Set に残すべき（SHOULD） | 同上 §10.1.1 | OK |
| F12 | 使った鍵がその発行者のものであることを確かめる | RFC 8725 §3.8 | OK |
| F13 | jwks_uri は AS のメタデータの項目 | RFC 8414 §2 | OK |
| F14 | Microsoft は、鍵を kid ごとにキャッシュし、寿命 24 時間、1 時間ごとの更新を示している | Microsoft Learn「Signing Key Rollover in Microsoft identity platform」（ms.date 2024-10-28、更新 2026-06-15）「Keys metadata caching algorithm」 https://learn.microsoft.com/en-us/entra/identity-platform/signing-key-rollover | OK |
| F15 | 知らない鍵のトークンが来たら取り直すが、5 分より頻繁にしない | 同上（KeyRefresh の 7.、疑似コードの 5 分） | OK |
| F16 | 取り直しに失敗したら、最後に取れた設定で動き続ける | 同上（KeyRefresh の 5. Error Handling） | OK |
| F17 | Okta は組織の認可サーバーの鍵を、今は年 4 回ローテーションし、頻度は予告なく変わりうる | Okta Developer「Key rotation」 https://developer.okta.com/docs/concepts/key-rotation/ | 曖昧→直した |
| F18 | Okta は新しい鍵をローテーションの数週間前に作る（公開する） | 同上 | OK |
| F19 | 古い鍵を JWK Set から外すと、その鍵で署名したトークンは exp の前でも検証できない | 論理的な帰結（カタログ U09 の lifetime_impact） | OK |
| F20 | NIST SP 800-63C-4 は、鍵のローテーションの手順をトラストアグリーメントで取り決めることを求める | NIST SP 800-63C-4 §3.6（研究ノート 05 の要約。節番号を確かめてほしい） | OK |
| F21 | CSRB の報告書は、自動化した頻繁な鍵のローテーションを参考の慣行に挙げている（勧告 6） | CSRB「Review of the Summer 2023 Microsoft Exchange Online Intrusion」（2024-03-20）勧告 6 | OK |
| F22 | 書籍：署名鍵のローテーション | 『実践 Keycloak』14.1.3 節 pp.283–286 | OK |

### slide:p01-client-made-jwts

| # | 述べたこと | 出どころ | 結果 |
| --- | --- | --- | --- |
| F23 | private_key_jwt の assertion は iss・sub がクライアント ID、aud が認可サーバー | RFC 7523 §3（OIDC Core §9 も） | 曖昧→直した |
| F24 | RFC 10070（2026 年 11 月）は、クライアント認証の JWT の aud を AS の issuer の値だけにし、トークンエンドポイントの URL を aud にしてはならず、AS は自分の issuer だけを aud に持たない JWT を拒否しなければならない | RFC 10070 §4 https://www.rfc-editor.org/rfc/rfc10070 | OK |
| F25 | typ は client-authentication+jwt を推奨（SHOULD）。typ の無いものを拒否することは推奨しない（NOT RECOMMENDED） | 同上 §4 | OK |
| F26 | JAR の Request Object は、認可要求のパラメータをクレームに入れた JWT | RFC 9101 §2.1・§4 | OK |
| F27 | Request Object は署名が必須（署名、または署名と暗号化） | RFC 9101 §5・§10.1 | OK |
| F28 | 署名した Request Object は iss と aud を入れるべき（SHOULD）。aud は AS の issuer | RFC 9101 §4 | OK |
| F29 | AS は Request Object の中のパラメータだけを使う | RFC 9101 §5・§6.3 | OK |
| F30 | DPoP の proof のヘッダーは typ が dpop+jwt、jwk に公開鍵 | RFC 9449 §4.2 | OK |
| F31 | proof のクレームは jti・htm・htu・iat。AT と一緒なら ath、サーバーが nonce を求めたら nonce | RFC 9449 §4.2 | OK |
| F32 | サーバーは proof を作成から限られた時間だけ受け入れ、その間の jti を覚えて再送を拒むことができる | RFC 9449 §11.1 | OK |
| F33 | RFC 8725 は明示的な型付けと、互いに受け入れない検証の規則を求める | RFC 8725 §3.11・§3.12 | OK |
| F34 | OWASP ASVS 5.0 10.3.5 は送信者制約のトークンを求める（L3） | OWASP ASVS 5.0.0 10.3.5（研究ノート 05 の要約） | OK |
| F35 | 書籍：DPoP の証明は 1 回限り | 『セキュアAPI』7.5.2 節 p.216 | OK |

### slide:p06-grant-types

| # | 述べたこと | 出どころ | 結果 |
| --- | --- | --- | --- |
| F36 | 公開クライアントは PKCE を使わなければならず、AS は PKCE に対応しなければならない | RFC 9700 §2.1.1 | OK |
| F37 | device flow では端末が device_code・user_code を受け取り、利用者は別の端末で verification_uri を開いて承認し、端末はトークンエンドポイントにポーリングする | RFC 8628 §3.2・§3.4・§3.5 | 曖昧→直した |
| F38 | user_code は短いので、試行の回数を制限するよう勧める | RFC 8628 §5.1 | OK |
| F39 | 攻撃者が自分の端末でフローを始め、被害者にコードを入れさせる遠隔のフィッシングに注意する（端末の情報を見せる） | RFC 8628 §5.4 | OK |
| F40 | client credentials は利用者のいない発行で、sub はクライアントになる | RFC 6749 §4.4、RFC 9068 §2.2（カタログ I05） | OK |
| F41 | ワークロードの ID（SPIFFE の JWT-SVID、Kubernetes のサービスアカウントのトークン）は基盤が発行し、IdP のフックは動かない | カタログ I20 | OK |
| F42 | ROPC は使ってはならない（MUST NOT） | RFC 9700 §2.4 | OK |
| F43 | implicit など、AT を認可応答で返す型は使うべきでない（SHOULD NOT）。代わりに code | RFC 9700 §2.1.2 | OK |
| F44 | Keycloak と Auth0 は、device flow で発行時フックが動くかを文書に明記していない | カタログ I07（hook_invoked: unknown、V32・V34） | OK |
| F45 | 指針：ワークロードは短命・狭いスコープ | NIST IR 8587 §5.3.1.6（既存のスライド p05-three-principals と同じ根拠） | OK |
| F46 | 書籍：インプリシット・ROPC・ハイブリッド | 『OpenID Connect入門』3.4・3.7・3.8 節 pp.50–57 | 曖昧→直した |

### slide:p08-four-lifetimes

| # | 述べたこと | 出どころ | 結果 |
| --- | --- | --- | --- |
| F47 | exp を過ぎたトークンは受け入れてはならない | RFC 7519 §4.1.4 | OK |
| F48 | CAEP の token-claims-change でクレームの変更を伝えられる | CAEP 1.0（Final、2025-08-29）§3.2 | OK |
| F49 | RFC 7009 で RT などを失効させられる | RFC 7009 §2.1 | OK |
| F50 | Back-Channel Logout は、offline_access なしで出した RT をログアウトで失効させるべきとする（SHOULD） | OpenID Connect Back-Channel Logout 1.0（errata set 1）§2.7 | OK |
| F51 | 書籍：署名した運び手に載せる属性は、変わりにくいものに限るべき（考え方） | 『デジタルアイデンティティのすべて』12.6 節 pp.199–200 | OK |
| F52 | 「AT が 5 分でもセッションが 10 時間なら 10 時間トークンを得られる」（Keycloak の既定 AT 5 分・SSO 最大 10 時間を例にした説明） | 既存のスライド p08-token-types-lifetimes の数値 | OK |

### slide:p08-reissue-triggers

| # | 述べたこと | 出どころ | 結果 |
| --- | --- | --- | --- |
| F53 | Auth0 は /authorize の organization のパラメータで組織を指定し、org_id を ID トークンとアクセストークンに入れる | Auth0 Docs「Work with Tokens and Organizations」（カタログ I24） | OK |
| F54 | Keycloak は organization の client scope を scope で求め、複数の組織に属すると認証のときに選ばせる | Keycloak Server Administration Guide 26.8.2「Mapping organization claims」（カタログ I24） | OK |
| F55 | Keycloak・Auth0 とも、ログイン中の組織を切り替える手順は文書にない | カタログ I24 | 不一致→直した |
| F56 | Keycloak は外部の IdP で初めてログインした利用者を first broker login のフローで作る | Keycloak Server Administration Guide 26.8.2「First login flow」（カタログ I17） | OK |
| F57 | Auth0 の post-login はサインアップの直後の認証でも動く | Auth0 Docs「Login Trigger」（カタログ I17・I25） | OK |
| F58 | Keycloak の IdP マッパーの Sync mode は、import なら初回のログインだけ、force なら毎回のログインで更新する | Keycloak Server Administration Guide 26.8.2「General configuration」（カタログ I17） | 曖昧→直した |
| F59 | Keycloak は既存のアカウントがあると、確認の後、メールか再認証で外部の ID を結びつける | Keycloak Server Administration Guide 26.8.2「First login flow」（カタログ I18） | OK |
| F60 | Keycloak のパスワード変更の「Sign out from other devices」は 26.3.0 から既定で未チェック | Keycloak Upgrading Guide 26.8.2「Migrating to 26.3.0」（カタログ I26） | OK |
| F61 | CAEP は credential-change のイベントを定める | CAEP 1.0 §3.3 | OK |
| F62 | prompt=none では、AS は認証・同意の画面を出してはならず、ログインが要るならエラー（login_required など）を返す | OpenID Connect Core 1.0 §3.1.2.1・§3.1.2.6 | OK |
| F63 | auth_time は利用者が認証した時刻（サイレント再認証では変わらない） | OpenID Connect Core 1.0 §2（auth_time の定義からの帰結。カタログ I11） | OK |
| F64 | Auth0 の post-login はサイレント認証（prompt=none）でも動く（リダイレクトはできない） | Auth0 Docs「Action Coding Guidelines」（カタログ I11） | OK |
| F65 | 書籍：外部 IdP のトークンから利用者を作る・更新する | 『実践 Keycloak』10.3 節 pp.198–199 | OK |

### slide:p08-logout

| # | 述べたこと | 出どころ | 結果 |
| --- | --- | --- | --- |
| F66 | RP-Initiated Logout の id_token_hint は推奨（RECOMMENDED） | OpenID Connect RP-Initiated Logout 1.0（Final、2022-09-12）§2 | OK |
| F67 | post_logout_redirect_uri は事前に登録したものでなければならず、OP は完全に一致しないときは戻さない | 同上 §2・§3 | OK |
| F68 | Front-Channel Logout は、OP のページが RP ごとの iframe でログアウトの URI を開く | OpenID Connect Front-Channel Logout 1.0（Final、2022-09-12）§2・§3 | OK |
| F69 | iss と sid は任意で、片方を付けるなら両方を付ける | 同上 §2 | OK |
| F70 | サードパーティのコンテンツへのアクセスを既定で遮るブラウザが増え、この方式が働かないことがある | 同上 §4.1 | OK |
| F71 | Logout Token は iss・aud・iat・exp・jti・events が必須。sub か sid の少なくとも一方。nonce は禁止 | Back-Channel Logout 1.0 §2.4 | OK |
| F72 | typ を logout+jwt にすることを推奨 | 同上 §2.4 | OK |
| F73 | exp は 2 分以内程度を勧める | 同上 §4 | OK |
| F74 | RP は ID トークンと同じ手順で署名・iss・aud・iat・exp を確かめ、events、sub か sid、nonce の不在を確かめる。jti の再送の確認は任意 | 同上 §2.6 | OK |
| F75 | 成功は 200、失敗は 400 を返す | 同上 §2.8（§2.6 の失敗も 400） | OK |
| F76 | RFC 7009：RT を失効させたとき、AS が AT の失効に対応していれば、同じグラントの AT も無効にすべき（SHOULD） | RFC 7009 §2.1 | OK |
| F77 | Auth0 の /oauth/revoke が失効させるのは RT だけ | Auth0 Authentication API「Revoke Refresh Token」（カタログ U15） | OK |
| F78 | Keycloak の Not before は指定の時刻より前に出たセッションとトークンを無効にし、その通知（押し出し）は Keycloak の OIDC アダプターにだけ届く | Keycloak Server Administration Guide 26.8.2「Revoking active sessions」（カタログ U15） | OK |
| F79 | ASVS 5.0 10.5.5 はログアウトトークンの typ（logout+jwt）を確かめることを求める | OWASP ASVS 5.0.0 10.5.5（研究ノート 05 の要約） | OK |
| F80 | 書籍：ログアウト（RP-Initiated・Front-Channel・Back-Channel） | 『OpenID Connect入門』7 章 pp.95–103 | 曖昧→直した |
| F81 | 書籍：Front-Channel Logout と Session Management はブラウザのサードパーティ Cookie の制限で当てにならない。すぐログアウトさせるなら Back-Channel | 『実践 Keycloak』4.7 節 pp.60–63 | OK |

### slide:p08-copies-outlive-token

| # | 述べたこと | 出どころ | 結果 |
| --- | --- | --- | --- |
| F82 | ブラウザの WebSocket の API は URL とサブプロトコルしか受け取らず、Authorization ヘッダーを付けられない | WHATWG WebSockets Standard（Living Standard、2026-11-22 に取得）の WebSocket の constructor（`WebSocket(url, protocols)`） | OK |
| F83 | MCP の認可仕様は、同じ論理的なセッションでも HTTP の要求ごとに Authorization を付け、AT を URL のクエリに入れてはならないとする | MCP Specification 2026-07-28「Authorization」の「Access Token Usage」 https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization | 不一致→直した |
| F84 | イントロスペクションの応答をキャッシュするなら、応答の exp を超えてはならない | RFC 7662 §4（既存のスライド p08-revocation-propagation と同じ） | OK |
| F85 | NIST IR 8587 は、トークンとトークンに含まれる個人情報をログに保存しないよう求める | NIST IR 8587 §5.3.1.5・§5.3.1.7（既存のスライド p09-logs-traces と同じ根拠。どちらの節かを確かめてほしい） | 曖昧→直した |
| F86 | 相関しやすい識別子があると、別々に共有したデータセットでも名寄せされる（考え方） | 『デジタルアイデンティティのすべて』8.2 節 p.75 | OK |
| F87 | 書籍：Bearer トークンは gRPC・WebSocket でも使える | 『実践 Keycloak』6 章 p.107 | OK |
| F88 | 多くの実装は、長い接続を開くときにだけトークンを確かめる | 一般的な観察（規範の出どころなし）。「多くの実装」という言い方が過大でないかを見てほしい | 曖昧→直した |

## 2. 筆者の推奨・提案として表示したもの（事実ではない）

| # | スライド | 内容 | 表示 |
| --- | --- | --- | --- |
| P01 | p01-key-rotation-jwks | 4 つの手順の並び（公開・待つ・切り替え・廃止）。最長の寿命のトークンが切れてから鍵を外す | リーダーの視点に「4 つの手順の並びは筆者の推奨」 |
| P02 | p01-client-made-jwts | クライアントが作る JWT に組織の独自クレームを載せない | ポイントに「筆者の推奨」 |
| P03 | p08-four-lifetimes | 寿命を 4 つの層に分けること、独自クレームごとに 4 つの層を別々に書くこと | リーダーの視点に「層の分け方と書き方は筆者の提案」 |
| P04 | p08-reissue-triggers | 契機ごとにフックが動くかを確かめ、剥奪をすぐ効かせたいクレームは載せない | リーダーの視点に「筆者の推奨」 |
| P05 | p08-copies-outlive-token | 長い接続は exp で切るか再認証、判断のキャッシュの寿命とキー、分析基盤への複製のしかた | カードの各項目に「筆者の推奨：」 |
| P06 | p06-grant-types | グラントを足したらフックの実行を確かめる | リーダーの視点（規範の出どころなし。F44 の事実からの助言） |

## 3. 確かめて閉じた項目：ID-JAG の版（スライド 110 だったもの、今は `slide:p08-downstream-after-expiry`）

- スライドの根拠は「ID-JAG 草案 06 §4.4.4」。
- 2026-11-22 に IETF Datatracker（https://datatracker.ietf.org/doc/draft-ietf-oauth-identity-assertion-authz-grant/）を取得した。最新は -06、版の表紙の日付は 2026-10-31、Datatracker の Last updated は 2026-10-30。-07 は無い。
- スライドの「06」は正しい。スライドは直していない。研究ノート 08 の「-06（2026-10-30）」と研究ノート 03 の「-06（2026-10-31）」の食い違いは、Datatracker の日付と表紙の日付の違いによる。
- 点検者は、点検の時点でも -06 が最新かを確かめてほしい。

## 4. 点検の結果

- 点検：作成とは別の LLM のセッション 2 つ（2026-11-22）。原文は PR #34 のコメント（上のリンク）
- 件数：88／88 件。OK 77、曖昧 9（F06・F17・F23・F37・F46・F58・F80・F85・F88）、不一致 2（F55・F83）、誤り 0、過大 0
- 一覧の外の指摘：A1（過大）、A2（表示漏れ）、A3（曖昧）、p08-reissue-triggers の「amr・auth_time が変わる」（過大）、体裁 3 件
- ID-JAG の版（§3）：-06 が最新（Datatracker の API で rev 06、2026-10-31T00:32:39Z）。スライドは正しい

### 直し方（同じ PR で反映し、再生成は 1 回）

| 指摘 | スライド | 直したこと |
| --- | --- | --- |
| F06 | p06-issuance-hook | 表を「client credentials では credentials-exchange が動く（post-login は実行条件にない）」に。ノートで、動かないことは実行条件からの推論で明文はないと書いた |
| F17 | p01-key-rotation-jwks | ノートの「組織の認可サーバーの鍵を」を「鍵のローテーションを」に（Okta 全体の注記） |
| F23 | p01-client-made-jwts | ノートと根拠の行に OIDC Core §9 を足し、OIDC Core §9 の aud（トークンエンドポイント）と RFC 10070 の違いを 1 文で書いた |
| F37 | p06-grant-types | 根拠の行を RFC 8628 §3.2〜§3.5 に |
| F40 | p06-grant-types | 根拠の行に RFC 9068 §2.2 を足した |
| F46 | p06-grant-types | 書籍を「3.4〜3.8 節 pp.50–57」に |
| F55 | p08-reissue-triggers | 「切り替えの手順はどちらも文書にない」を「どちらもログイン中のまま切り替える機能はなく、取り直す」に。ノートに Auth0 の Support Center の記事（ログインし直す手順）を書いた。カタログ I24 の auth0 の hook_note も直した |
| F58 | p08-reissue-triggers | ノートに出どころの節（Identity provider mappers の Sync Mode Override）を書いた |
| F80 | p08-logout | 書籍を「7 章 pp.95–104」に |
| F83 | p08-copies-outlive-token | ノートから「同じ論理的なセッションの中でも」を削った（2026-07-28 版に無い） |
| F85 | p08-copies-outlive-token | 指針の行を「§5.3.1.7（トークンと個人情報）・§5.3.1.5（トークン）」に |
| F88 | p08-copies-outlive-token | ノートの「多くの実装では」を「接続を開くときにだけトークンを確かめる実装では」に |
| A1 | p01-key-rotation-jwks | 表を「jwks_uri から取る」「jku・x5u をそのままたどらない（許可リストで SSRF を防ぐ。RFC 8725 §3.10）」に。根拠の行に §3.10 を足した。要件 p01-key-rotation-jwks.R1 の文も合わせた |
| A2 | p06-grant-types | リーダーの視点に「（筆者の推奨）」 |
| A3 | p06-grant-types | ノートの「交換するのが普通です」を「交換することもあります」に |
| 過大（amr） | p08-reissue-triggers | 表を「再認証を伴えば amr・auth_time が変わる」に。ノートとリードも、変更の後の再認証で出ると読めるようにした |
| 体裁 | s080・s114・s013 | s080：1 列目を「Device Authorization Grant」だけにし、RFC 8628 を 3 列目へ。「（前のスライド）」を削った。s114：表の列幅を変え、post_logout_redirect_uri のセルの行間を広げた。s013：根拠の行を 2 行に縮めた |

F44 の補足（Auth0 の event.transaction.protocol に oauth2-device-code がある）は、動く根拠にはならないので、スライドは「文書に明記がない」のままにした。
