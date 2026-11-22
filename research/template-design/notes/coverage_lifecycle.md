# 発行・利用イベントの網羅性：マスターカタログ、ガイドとの突合、「漏れゼロ」の到達可能性

調査日: 2026-11-22。対象ガイド: `docs/slides.json`（152 枚）。各ガイドのスライド番号は slides.json の `n`。
ガイド側の突合は slides.json の本文とノートへのキーワード検索と、主要スライド（26, 36, 70, 72, 76–80, 85, 89, 103, 106, 108–110, 122, 128, 134, 148）の通読による。キーワードが 0 件でも、言い換えで扱っている可能性は残る（下の「未確認の点」を参照）。
凡例: （非公式）= フォーラム・メーリングリスト・個人ブログ・他プロジェクトの Wiki・第三者のまとめ記事など、第三者の非公式な情報源。

## Q1. テンプレートが列挙すべき発行イベント・利用イベントのマスターカタログと、ガイドの充足状況

### 要点
標準（IANA の grant type 登録、OIDC 系仕様）と IdP のフック起動条件（Auth0 の `event.transaction.protocol` 16 値、Cognito の `triggerSource` 6 値）を「列挙の種」にすると、約 30 の発行イベントと約 20 の利用イベントが挙がる。ガイドは委任・交換・step-up・CIBA・非同期・DB・エージェントを厚く扱う。一方で、次の発行イベントはスライドにない（キーワード 0 件）：device flow（RFC 8628）、サイレント再認証（`prompt=none`）、Back-Channel Logout トークン、テナント（組織）の切り替えに伴う再発行、サインアップ・招待・初回ログイン、パスワード変更・MFA 登録の後の発行。利用側では、長時間接続（WebSocket・ストリーム）と分析基盤へのクレームの複製がない。

### 出典のある所見
- IANA の OAuth の grant type URN は `jwt-bearer`（RFC 7523）、`saml2-bearer`（RFC 7522）、`device_code`（RFC 8628 §3.1）、`token-exchange`（RFC 8693 §2.1）の 4 つ。token type には `jwt`・`access_token`・`refresh_token`・`id_token`・`saml1`・`saml2` がある。認可エンドポイントの response type には `code`・`token`・`id_token`・`none`・hybrid の組み合わせ・`vp_token` がある — [IANA OAuth Parameters](https://www.iana.org/assignments/oauth-parameters/oauth-parameters.xhtml)
- Auth0 の post-login Action の `event.transaction.protocol` が取りうる値は次の 16 個：`oidc-basic-profile`、`oidc-ciba`、`oidc-ciba-web-link`、`oidc-implicit-profile`、`oauth2-device-code`、`oauth2-resource-owner`、`oauth2-resource-owner-jwt-bearer`、`oauth2-password`、`oauth2-webauthn`、`oauth2-access-token`、`oauth2-refresh-token`、`oauth2-token-exchange`、`oidc-hybrid-profile`、`samlp`、`wsfed`、`wstrust-usernamemixed`。つまり同じフックが 16 通りの契機で動く — [Auth0 post-login event object](https://auth0.com/docs/customize/actions/explore-triggers/signup-and-login-triggers/login-trigger/post-login-event-object)
- Auth0 では client credentials を別のトリガー `credentials-exchange` が扱う。説明は「Credentials Exchange Actions run when an Access Token is issued as part of the Machine to Machine Flow」。つまり M2M のトークンには post-login のクレームの付与が効かない — [Auth0 Machine to Machine trigger](https://auth0.com/docs/customize/actions/explore-triggers/machine-to-machine-trigger)
- Cognito の pre token generation の `triggerSource` は次の 6 つ：`TokenGeneration_HostedAuth`、`TokenGeneration_Authentication`、`TokenGeneration_NewPasswordChallenge`（管理者が作った利用者が一時パスワードを変えるとき）、`TokenGeneration_ClientCredentials`（V3_0 のときだけ送られる）、`TokenGeneration_AuthenticateDevice`、`TokenGeneration_RefreshTokens` — [AWS Cognito pre token generation](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-pre-token-generation.html)
- Cognito では M2M のアクセストークン（client credentials と `GetClientToken`）にフックが効くのは V3_0 のときだけで、V3_0 は Essentials と Plus のプランに限られる。`sub`・`acr`・`amr`・`auth_time`・`jti`・`sid` などはフックで変えられない — [AWS Cognito pre token generation](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-pre-token-generation.html)
- OIDC Back-Channel Logout 1.0 は Final（errata 1 を反映、2023-12-15）。Logout Token は ID トークンに似た署名付きの JWT で、`iss`・`aud`・`iat`・`exp`・`jti`・`events`（`http://schemas.openid.net/event/backchannel-logout`）が必須、`sub` か `sid` の少なくとも一方が必須。`nonce` は入れてはならない。`typ`=`logout+jwt` は推奨にとどまる。つまりこれもクレームを設計すべき「発行イベント」である — [OIDC Back-Channel Logout 1.0](https://openid.net/specs/openid-connect-backchannel-1_0.html)
- ID-JAG（draft-ietf-oauth-identity-assertion-authz-grant）は RFC 8693 と RFC 7523 を組み合わせ、Identity Chaining 草案のプロファイルとして作られている。最新版は -06（2026-10-31、2027-05-04 に失効）で、まだ RFC ではない。ガイドのスライド 110 の「ID-JAG 草案 06」は正しい（調査時は検索で見た -05 を最新としていたが、古い情報だった。取り込みの際に datatracker で確かめた） — [IETF datatracker ID-JAG](https://datatracker.ietf.org/doc/draft-ietf-oauth-identity-assertion-authz-grant/)、[-06 txt](https://www.ietf.org/archive/id/draft-ietf-oauth-identity-assertion-authz-grant-06.txt)、[-03](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-identity-assertion-authz-grant-03)、[-05 txt](https://www.ietf.org/archive/id/draft-ietf-oauth-identity-assertion-authz-grant-05.txt)
- ガイドのスライド 76 は 6 つの段階を示し、台帳に「どの段階で、誰が書くか」の列を持つよう求めている。スライド 77 は Okta・Entra・Auth0・Cognito・Keycloak のフックが起動する時点を表にしている（Auth0 は「ログイン後と、リフレッシュ時」、Cognito は「発行時。リフレッシュ時も」）。スライド 134 の台帳 12 項目には「鮮度：値の出どころと、反映までの遅れ」と「持ち主」がある（slides.json、n=76・77・134）。

#### マスターカタログ（発行イベント）とガイドの充足

凡例は ○＝専用の扱いあり、△＝言及のみ・別の文脈、×＝スライドにない（キーワード 0 件）。

| ID | 発行イベント | 主な標準・製品の根拠 | 主に生まれる・変わるクレーム | ガイド |
|---|---|---|---|---|
| I01 | 対話ログイン（認可コード＋PKCE） | RFC 6749 §4.1、RFC 7636、RFC 9700 | acr・amr・auth_time・sid、② のフック | ○ 76・87（PKCE は 126 のみ） |
| I02 | implicit・hybrid（レガシー） | IANA の response type、Auth0 `oidc-implicit-profile`／`oidc-hybrid-profile` | ID トークンがフロントに出る | ×（テンプレートでは「禁止のため対象外＋理由」の行にする） |
| I03 | ROPC・password grant | RFC 6749 §4.3、Auth0 `oauth2-password` | amr がパスワードだけ | ×（同上） |
| I04 | サイレント再認証・SSO セッションの再利用（`prompt=none`） | OIDC Core §3.1.2.1 | auth_time は古いまま、acr は前回の値 | ×（auth_time と max_age は 25・80 で扱うが、イベントとしては扱わない） |
| I05 | リフレッシュ（ローテーションを含む） | RFC 6749 §6、RFC 9700、Auth0 `oauth2-refresh-token`、Cognito `TokenGeneration_RefreshTokens` | フックが再び動くかで ② のクレームの鮮度が決まる | ○ 106・107 |
| I06 | トークン交換（委任・なりすまし） | RFC 8693 §4.1・4.4 | act・may_act・aud の絞り込み | ○ 26・36・70・72・110・127 |
| I07 | 追加認証（step-up） | RFC 9470 | acr・auth_time の更新 | ○ 80 |
| I08 | client credentials（M2M） | RFC 6749 §4.4、Auth0 `credentials-exchange`、Cognito V3_0 | sub がクライアント、利用者のフックは動かない | △ 63・70・122（フックが別であることはスライド 77 にない） |
| I09 | デバイス認可（device flow） | RFC 8628、Auth0 `oauth2-device-code` | 入力した端末と承認した端末が別 | × |
| I10 | CIBA | OIDC CIBA Core、Auth0 `oidc-ciba` | 承認の結果、binding_message | ○ 70・80・125 |
| I11 | JWT・SAML のアサーショングラント | RFC 7523、RFC 7522 | 上流の主張を AS が写し替える | △ 89（7522 は 0 件） |
| I12 | ID-JAG（ドメインをまたぐ SSO 済みの利用者のトークン） | ID-JAG 草案、Identity Chaining 草案 | sub の一致、client_id | ○ 110・123–131 |
| I13 | 外部 IdP 経由のログイン（ブローカー・JIT プロビジョニング） | OIDC・SAML の連携、SP 800-63C-4 | 上流の属性の写像。出どころが外部 | △ 29・44・72（JIT は 0 件） |
| I14 | アカウントの名寄せ・リンク | 製品機能（Auth0 の account linking など） | sub の継続性、identities | △ 72（「idp で名寄せしない」のみ） |
| I15 | 運用者の代理操作・break-glass | RFC 8693 | sub＝利用者、act＝運用者、承認 ID | ○ 70・72 |
| I16 | オフライン・夜間バッチ・長時間ジョブ | OIDC Core §11（offline_access）、RFC 8693 | ワーカーの ID による作り直し | ○ 70・109・110 |
| I17 | AI エージェントの委任・自律 | RFC 8693、MCP の認可、ID-JAG | act・client_id・ツールごとの scope | ○ 122–131 |
| I18 | ワークロード ID の連携（K8s の SA トークン、CI の OIDC、SPIFFE SVID） | SPIFFE、WIF | sub＝ワークロード | △ 63・96・100 |
| I19 | 入口での作り直し（phantom token、内部トークン） | Curity、Netflix Passport、ext_authz | 正規化した主体 ID、内部の aud | ○ 78 |
| I20 | Txn-Token の発行と作り直し | Transaction Tokens 草案 | txn・tctx・rctx・req_wl | ○ 79 |
| I21 | ログアウトトークン（Back-Channel Logout） | OIDC Back-Channel Logout 1.0 | events・sid・nonce 禁止 | ×（スライドは 0 件。research/notes/01 には記述あり） |
| I22 | 共有シグナル（SET）の発行（SSF・CAEP） | SSF 1.0、CAEP 1.0 | session-revoked、token-claims-change | ○ 105・108 |
| I23 | ID トークン、AT、UserInfo 応答の作り分け | OIDC Core §5.3、RFC 9068 | 宛先ごとに別のクレームの集合 | ○ 13・47 |
| I24 | テナント・組織の切り替えによる再発行 | Auth0 Organizations、Keycloak Organizations などの製品 | tid・org_id の差し替え | ×（切り替えの扱いは 0 件。組織のクレームは 22・36） |
| I25 | サインアップ・招待・初回ログイン | 製品のフック（Auth0 pre/post-user-registration など） | email_verified=false、所属の付与 | × |
| I26 | 資格情報の変更（パスワード変更・MFA 登録）の後の発行 | Cognito `TokenGeneration_NewPasswordChallenge` | amr、セッションの扱い | × |
| I27 | 端末の認証・端末の記憶 | Cognito `TokenGeneration_AuthenticateDevice` | device_key | ×（ベンダー固有） |
| I28 | レガシーの連携プロトコル（SAMLP・WS-Fed・WS-Trust） | Auth0 `samlp`／`wsfed`／`wstrust-usernamemixed` | 属性の写像 | △ 29 |
| I29 | 署名鍵のローテーション（kid の切り替え期間の発行） | RFC 7517、RFC 8725 | ヘッダーの kid | △ 12（ローテーションは 0 件） |
| I30 | ネイティブアプリ間の SSO（device_secret） | OpenID Native SSO（状態は未確認） | ds_hash など | ×（状態は「未確認の点」を参照） |

#### マスターカタログ（利用イベント）とガイドの充足

| ID | 利用イベント | 根拠 | ガイド |
|---|---|---|---|
| U01 | リソースサーバーでの検証と認可 | RFC 9068、RFC 8725 | ○ 11・82 |
| U02 | 入口での変換・ヘッダーへの転記 | NIST SP 800-228、OWASP | ○ 78・84 |
| U03 | サービス間の伝搬（Txn-Token・mTLS・SPIFFE） | Txn-Token 草案 | ○ 79・81・82 |
| U04 | 非同期（キュー・イベント・ワークフロー） | CloudEvents Auth Context、Pub/Sub push | ○ 89・109 |
| U05 | DB のセッション文脈（RLS）・接続プール | 各製品 | ○ 92–98 |
| U06 | ログ・監査・トレース | W3C Trace Context、OWASP Logging CS | ○ 85・118 |
| U07 | イントロスペクション | RFC 7662 | ○ 14・108 |
| U08 | 失効（失効エンドポイント・状態リスト・SET） | RFC 7009、Status List 草案、SSF | ○ 104・105・108 |
| U09 | ログアウト（RP-Initiated・Front-Channel・Back-Channel） | OIDC の各ログアウト仕様 | △ 108（ログアウト後の active=false の実測のみ。RP-Initiated・Front・Back は 0 件） |
| U10 | クライアントや UI が ID トークンを読む | OIDC Core | ○ 13 |
| U11 | UserInfo の呼び出し | OIDC Core §5.3 | ○ 37・47 |
| U12 | 応答・Webhook の署名 | RFC 9421 | ○ 86・89 |
| U13 | 取引先 API（ドメインをまたぐ） | Identity Chaining 草案 | ○ 89 |
| U14 | 判断や検証結果のキャッシュ | RFC 7662 §4 | △ 108 |
| U15 | ブラウザ・URL への保存 | RFC 9700 | ○ 119 |
| U16 | 長時間の接続（WebSocket・gRPC ストリーム・SSE）で途中に期限が切れる | — | ×（DB 接続の寿命のずれは 97 で扱う。類推は効く） |
| U17 | クラウドの STS での利用（AssumeRoleWithWebIdentity など） | 各クラウド | ○ 100 |
| U18 | エージェントのツール呼び出し（MCP） | MCP の認可 | ○ 126 |
| U19 | 送信者制約での利用（DPoP・mTLS の cnf） | RFC 9449、RFC 8705 | ○ 27・89 |
| U20 | 拒否と再挑戦（WWW-Authenticate、step-up の要求） | RFC 6750、RFC 9470 | ○ 80 |
| U21 | 分析基盤・データウェアハウスへのクレームの複製 | — | ×（ログは 118 で扱う。分析用の複製は扱わない） |

### 推論
- 列挙の種として最も機械的に使えるのは、IdP のフックが受け取る「契機の値の一覧」（Auth0 の 16 値、Cognito の 6 値）である。ここには「同じフックが動くか、動かないか」が直接現れる。テンプレートは「採用している IdP の契機の値をすべて行にし、各行に『使う・使わない（理由）』を書く」形にすると、少なくとも製品の範囲では閉じた列挙になる。
- 欠けている I04・I24・I25・I26 は、どれも「② のフックが動くか、動いたときにクレームが変わるか」で事故になりうる。代表例は、テナントを切り替えたのに古い tid が残ること、招待の直後に所属が未確定であることだ。ガイドの主題（独自クレームの鮮度と書き手）に直結するので、優先度が高い。
- I21（Logout Token）は、ガイドの研究ノート（research/notes/01）にはあるがスライドにない。U09 と合わせて 1 枚を足すと、失効のスライド 108 が閉じる。

### 未確認の点
- Okta の token inline hook がリフレッシュや client credentials でも動くかは、取得したガイドのページに記述がなかった（[Okta token inline hook guide](https://developer.okta.com/docs/guides/token-inline-hook/main/)）。リファレンスのページで確かめる必要がある。
- Entra の custom claims provider がリフレッシュ時に呼ばれるかは、今回確かめていない。
- OpenID Native SSO（I30）の現在の状態（Final か草案か）は確かめていない。
- キーワードで突合したため、言い換えで扱っているスライドを × と誤判定した可能性がある。特に I25 と I26 はノート本文まで目視で確かめていない。

## Q2. データの出どころの系統（クレーム → 元のシステム → 鮮度・持ち主）を体系的に写像する方法

### 要点
NIST には、属性の「出どころと確かさ」をメタデータとして運ぶ枠組みがある（NISTIR 8112 の属性メタデータ、SP 800-63C-4 の派生属性値）。これをクレームの台帳の列に写すと、系統の表は「クレーム × 段階（①〜⑥）× 元のシステム × 確認の方法 × 最終確認 × 持ち主」の行列になる。ガイドのスライド 134 は鮮度と持ち主の列を既に持つので、足りないのは「確認の方法」と「最終確認の時刻」の列と、段階の列との結合である。

### 出典のある所見
- NISTIR 8112『Attribute Metadata: A Proposed Schema for Evaluating Federated Attributes』（2018-01 最終版）は、属性値のメタデータに「確認の方法（document verification・record verification・proof of possession・probabilistic・not verified など）」と「最終確認（last verification）」を置く。目的は、RP が属性の決まり方（出どころと確かめ方）を理解できるようにすることにある — [NISTIR 8112 PDF](https://nvlpubs.nist.gov/nistpubs/ir/2018/nist.ir.8112.pdf)、[NISTIR 8112 HTML](https://pages.nist.gov/NISTIR-8112/NISTIR-8112.html)、[NIST の概要ページ](https://www.nist.gov/node/1802806)
- SP 800-63C-4 は、派生属性値を「元の属性値を含まずに限られた事実を表すもの」と定義する（例：生年月日ではなく「18 歳以上」）。CSP から IdP へは、属性値・派生属性値・属性の束のいずれかで渡す。どの属性を RP に出すかは、信頼の合意で範囲を決めたうえで、連携の取引のたびに確定する — [SP 800-63C-4 用語集](https://pages.nist.gov/800-63-4/sp800-63c/glossary)、[SP 800-63C-4 プライバシー](https://pages.nist.gov/800-63-4/sp800-63c/privacy)、[SP 800-63C-4 PDF](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-63C-4.pdf)
- Shostack の脅威モデリングの指針は、構成を変えたときの間接的な脅威を例に挙げる。設定データの出どころが管理画面の入力から AD・LDAP に変わると、データはネットワーク越しに複数のプロトコルで届くようになり、検証の方針を変える必要がある。つまり「出どころの変更」はそれ自体がレビューの契機になる — [Shostack, Security Briefs 2008](https://learn.microsoft.com/en-us/archive/msdn-magazine/2008/july/security-briefs-reinvigorate-your-threat-modeling-process)
- Cognito では、プラットフォームが書く `sub`・`acr`・`amr`・`auth_time`・`sid` などはフックで変えられない。フックで足せるのは任意のクレーム・scope・グループに限られる。つまり書き手が構造的に 2 つ（プラットフォームとフック）に分かれている — [AWS Cognito pre token generation](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-pre-token-generation.html)

### 推論
- 系統表の推奨列：クレーム名／発行イベント（I01〜）／段階（①〜⑥）／書き手（プラットフォーム・フック・入口・TTS）／元のシステム（ディレクトリ・人事・課金・ポリシーストア・上流の IdP・利用者の申告）／確認の方法（8112 の語彙）／反映の遅れ（イベント駆動か、次の発行までか）／再計算の契機（ログインのみか、リフレッシュでもか）／持ち主。このうち「再計算の契機」は、Q1 の契機の一覧（Auth0・Cognito）と結合して初めて埋まる。
- データの系統（data lineage）の考え方を当てはめると、クレームは「元のシステムからの派生物」である。系統表は上流（元のシステム）の変更から下流（受け手）への影響を逆にたどる用途に使える。これはスライド 137 の「9 つの受け手 × 10 の変更」の行列の上流版にあたる。
- 派生属性値（800-63C-4）は「何を載せるか」の最小化の根拠にもなり、系統表では「元の属性」と「載せる派生値」を別の行にする設計が自然である。

### 未確認の点
- データの系統の業界標準（OpenLineage など）をクレームの台帳に当てはめた先行事例は、今回探していない。
- 800-63C-4 §3.11.2 の規範の文言（SHOULD かどうか）は、原文の PDF で確かめていない。検索結果の要約では「where feasible で推奨」とされている。

## Q3. 網羅性の技法と、チェックリストで「漏れがない」ことを示すことの限界

### 要点
「漏れゼロ」は原理的に証明できない。テストは欠陥の存在を示せても不在は示せないし、脅威モデリングの第一人者も「要素ごとに STRIDE を当てたら『かなり良い』」と述べるにとどまる。到達できるのは「定義した列挙の軸に対する網羅（閉じた世界での完全性）」と、「軸の外の漏れを見つけやすくする仕組み」である。組み合わせテストの実証研究からは、2 因子までの組み合わせで多くの欠陥が見つかり（アプリによって幅がある）、4〜6 因子で既知の欠陥はすべて見つかったと報告されている。したがって「主体 × フロー × 段階」の 2 因子（pairwise）網羅は、費用対効果の良い目標になりうる。ただし全部を拾う保証ではない。

### 出典のある所見
- Dijkstra は 1969 年の NATO ソフトウェア工学会議（ローマ）で「Testing shows the presence, not the absence of bugs」と述べた。EWD288（1970 年 7 月）にも同じ趣旨の記述がある（【訂正 2026-11-22】調査時は「1968 年」と書いていた） — [EWD288 transcription](https://www.cs.utexas.edu/%7EEWD/transcriptions/EWD02xx/EWD288.html)、[Hillel Wayne による出典の整理](https://buttondown.com/hillelwayne/archive/testing-can-show-the-presence-of-bugs-but-not-the)（非公式）
- Shostack（「Knowing When You're Finished」）の要旨：図がシステムの関連する部分をすべて示し、図のすべての要素で STRIDE を一通り確かめたなら「かなり良い」。ただしそれは、すべてのドアと窓に鍵があるのを確かめて終わりにするようなもので、それで足りる場合もある、と添えている（【訂正 2026-11-22】調査時は「その程度の意味しかない」と強めに要約していた）。どこまで深くやるかは、リスク許容度・規制・予算と時間の兼ね合いで決まる。また、人に構造とフィードバックを与え、作業を小さな部分に分けて各部分に規則と自己点検を置くと、まずまずの結果が得られる。ただし規則が多すぎたり間違っていたりすると、作業が苦役になる — [Shostack, MSDN Security Briefs 2008-07](https://learn.microsoft.com/en-us/archive/msdn-magazine/2008/july/security-briefs-reinvigorate-your-threat-modeling-process)
- STRIDE-per-element は、DFD の要素の種類（外部エンティティ・プロセス・データストア・データフロー）ごとに当てはまる脅威の区分を決め、要素を順に確かめる方法である — [Larry Osterman, STRIDE per Element](https://learn.microsoft.com/de-de/archive/blogs/larryosterman/threat-modeling-again-stride-per-element)、[MSDN 2006 Uncover Security Design Flaws Using STRIDE](https://msdn.microsoft.com/en-us/magazine/cc163519.aspx)
- Shostack の旧版の書籍の抜粋には、DFD は脅威を探すうちに変わり、見つかる脅威の数は図の要素の数に比例する、という記述がある。目安は要素あたり約 5 件の STRIDE の脅威。この抜粋は後に削られた（検索結果の要約による。原文 PDF は未読） — [Shostack 第 1 版の章 PDF](https://shostack.org/files/tmbookchapters/threat-modeling-first-edition-Starting-the-Threat-Modeling-Project.pdf)
- Shostack は 2007 年のエッセイで、図を描かせるときに「どこで止めてよいか」「どの詳細は要らないか」を示していなかったことを問題として挙げている — [The Trouble with Threat Modeling (2007)](https://threatmodelingbook.com/files/essays/The%20Trouble%20With%20Threat%20Modeling.docx)
- Threat Modeling Manifesto は「チェックボックスの順守より、設計の問題を見つけて直す文化」と「スナップショットより理解の旅」を価値に掲げ、4 つ目の問いとして「十分にうまくやれたか？」を置く。網羅を一度きりの証明ではなく、繰り返し確かめるものとして扱っている — [Threat Modeling Manifesto](https://www.threatmodelingmanifesto.org/)
- NIST の組み合わせテストの研究（Kuhn ら）は「interaction rule」を示す。多くの障害は単一の因子か 2 因子の組み合わせで起きる。ある 2019 年の発表では、65% が単一因子、96% が単一因子か 2 因子によるものだった（1 種類のアプリケーションのデータという注記つき）。【訂正 2026-11-22】NIST ACTS のページ自体に 96% はない。ページの 10 種類のアプリのグラフでは、2 因子までの累積はおよそ 47%（Apache2）〜97%（FDA の医療機器）と幅がある。NIST は 6 因子を超える障害を観測しておらず、いくつかの研究では 4〜6 因子の網羅で、全数テストで見つかった欠陥をすべて検出できた。ただし因子数ごとの分布は、NIST 自身が研究課題として未解決にしている — [NIST ACTS: Interactions involved in software failures](https://csrc.nist.gov/projects/automated-combinatorial-testing-for-software/combinatorial-methods-in-testing/interactions-involved-in-software-failures)、[Kuhn 2019 slides](https://csrc.nist.gov/CSRC/media/Projects/cyber-supply-chain-risk-management/documents/SSCA/Fall_2019/WedAM2.2_kuhn.pdf)、[NIST ACTS Research Program](https://csrc.nist.gov/Projects/automated-combinatorial-testing-for-software/Our-Research-Program)
- 要求工学の大規模調査 NaPiRE では、「不完全な要求・隠れた要求」が最も多く挙がった問題だった（回答者の 48%。【訂正 2026-11-22】この値は arXiv 1611.10288 の Table 9 にある。1612.00163 にはない）。その原因として最も多く挙がったのは、要求工学の担当者の資格不足と経験不足（各約 9%）、時間の圧力などである（1611.10288 の Fig. 4）。ただしプロジェクトの失敗率との関連だけで見ると、最上位は「動く標的（要求の変化）」になる。回答は自己申告である — [arXiv 1612.00163](https://arxiv.org/pdf/1612.00163)、[arXiv 1611.10288](https://www.arxiv.org/pdf/1611.10288)、[arXiv 1707.00144](https://arxiv.org/pdf/1707.00144)

### 推論
- 「レビュー担当者がもう漏れを見つけられない」という主張は、上の根拠からは支持できない。言えるのは「テンプレートが定義する軸（発行イベントのカタログ × 段階 × 受け手）の内側では、未記入のセルが機械的に見つかる」までである。軸の外にある漏れ（新しい grant、製品の新しい契機、組織固有の業務イベント）は残る。NaPiRE では、その原因として担当者の資格や経験の不足などが挙がっており、テンプレートだけでは埋まらない。
- 網羅を高める仕組みの候補は次のとおり。
  1. **閉じた列挙の種**：IANA の grant type と token type、OIDC のログアウトの 3 仕様、採用している IdP のフックの契機の値の一覧を行の母集団にし、外部の一覧の改訂（新しい RFC・製品のリリースノート）をテンプレートの更新の契機にする。
  2. **DFD と要素ごとの点検**：シーケンス図の各メッセージをデータフローとみなし、各フローに「載るトークンの種類 × 確かめるクレーム」を書く。各フローに「書き手」「宛先（aud）」「寿命」の 3 つの問いを必ず当てる（STRIDE-per-element をクレームに当てはめたもの）。
  3. **状態遷移と CRUD の行列**：主体の状態（招待・有効・停止・削除・テナントの切り替え・権限の変更・資格情報の変更）を行、トークンの種類（AT・RT・ID・Txn・Logout）を列にし、各セルに「発行・再計算・失効・影響なし」のどれかを必ず書く。I24〜I26 はこの行列で初めて現れる種類の漏れである。
  4. **pairwise の網羅**：主体の種類（利用者・ワークロード・エージェント・運用者）× 発行イベント × 段階（①〜⑥）の 3 因子について、少なくとも 2 因子のすべての組を一度は検討する。NIST の実証研究に照らすと、費用対効果の良い目標になりうる（ただし拾える割合はアプリによって幅がある）。
  5. **双方向の追跡行列**：「クレーム → 発行イベント → 元のシステム」と「受け手 → 読むクレーム」を両方向に結ぶ。どの受け手も読まないクレーム（削除の候補）と、元のシステムのないクレーム（出どころが不明）を自動で検出する。
  6. **自己点検の規則**（テンプレートに埋め込む。台帳のスキーマで機械的に確かめられる）：
     - クレームの行は、少なくとも 1 つの発行イベント ID、段階（①〜⑥）、書き手、元のシステム、確認の方法、再計算の契機を必ず持つ。空欄は不可。
     - カタログの全発行イベントと全段階に、「該当」か「対象外＋理由」のどちらかを必ず書く（暗黙の対象外を禁止する）。I02・I03 のような禁止のフローも「対象外：ROPC は RFC 9700 §2.4 で使用禁止（MUST NOT）、implicit は §2.1.2 で SHOULD NOT」と明記する（【訂正 2026-11-22】調査時は「非推奨」と弱く書いていた）。
     - 受け手の行は、読むクレームと「欠けたときの挙動（拒否）」を必ず持つ（スライド 57・58・77 の規則を列にしたもの）。
     - 製品の契機の値の一覧と台帳の発行イベントの差集合を、CI で計算する（スライド 136 の契約テストの延長）。
     - 運用で出たトークンのクレームの実測と台帳との差を測る（スライド 144 の指標を、イベントの種類ごとに分ける）。
  7. **「十分か」の問いを残す**：Manifesto の 4 つ目の問い。チェックリストの末尾に「この列挙の外にある発行・利用の契機はないか」を自由記述で置き、領域の専門家が回答する。漏れの原因に担当者の資格や経験の不足が挙がっていることへの対策である。
- 打ち出し方の提案：「漏れゼロ」ではなく、「定義した軸の内側で未記入を機械的に検出し、軸そのものは外部の一覧と運用の実測で更新し続ける」と表現するのが根拠に沿う。

### 未確認の点
- 要求工学の「網羅性の基準」（たとえば、すべてのユースケースが少なくとも 1 つの要求に追跡されることを示す traceability の完全性の指標）について、定量的な効果を示した一次研究は今回取得していない。
- チェックリストの導入で、セキュリティレビューの見逃しが実際にどれだけ減ったかを示す定量研究は見つけていない。
- Shostack の第 2 版（*Threat Modeling: Designing for Security in an AI World*、2027-01 刊行予定と表示）で網羅の基準が改訂されるかは、確認できない。
- STPA（Leveson）などの安全分析の網羅性の議論は、探索の範囲外として扱っていない。
