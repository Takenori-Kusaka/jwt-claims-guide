# 08. マイクロサービス全体でのクレームの流れ（付与・拡張・縮小・伝播・更新・返却）

- 調査日: 2026-11-17
- 方針: 一次情報（IETF RFC/Internet-Draft、OpenID 仕様、NIST、OWASP、各ベンダー公式ドキュメント、システムを作った企業のエンジニアリングブログ）を取得して確認した内容のみを書く。取得したページで確認できなかった点は **[未検証]** とする。
- 他ノートとの分担: 標準クレームの定義、IdP ごとのクレーム一覧（→ 02_idp-claims.md）、インシデントと攻撃、MCP の基礎、カスタムクレーム製品のカタログ、データ層は扱わない。このノートは **フロー**（どこでクレームが生まれ、どう変わり、どう返るか）に絞る。
- 略語: AT = access token、RT = refresh token、IDT = ID token、AS = authorization server、RS = resource server、TTS = Transaction Token Service、PEP/PDP = policy enforcement/decision point

---

## 0. 2026-11 時点の仕様ステータス（フロー設計に効くもの）

| 仕様 | 状態 (2026-11) | 出典 |
|---|---|---|
| Transaction Tokens | **draft-ietf-oauth-transaction-tokens-11**（最新リビジョン 2026-07-30）。WG 状態は "WG Consensus: Waiting for Write-Up"。IESG への提出予定（マイルストーン）は 2026-12 | https://datatracker.ietf.org/doc/draft-ietf-oauth-transaction-tokens/ |
| Transaction Tokens のクレーム名 | **-11 で改名済み**。目的は `purp` → **`scope`**、不変の文脈は `azd` → **`tctx`**、リクエスト文脈は **`rctx`**。`req_wl` は REQUIRED。古い資料の `purp`/`azd` は使わない | https://www.ietf.org/archive/id/draft-ietf-oauth-transaction-tokens-11.html §9.2 |
| OAuth 2.1 | draft-ietf-oauth-v2-1-17（2026-10-31 付、WG Document、IESG 提出予定は 2026-12） | https://datatracker.ietf.org/doc/draft-ietf-oauth-v2-1/ |
| Identity Assertion JWT Authorization Grant (ID-JAG) | draft-ietf-oauth-identity-assertion-authz-grant-06（2026-10-30、WG Document） | https://datatracker.ietf.org/doc/draft-ietf-oauth-identity-assertion-authz-grant/ |
| Identity and Authorization Chaining Across Domains | draft-17。IESG 状態は "RFC Ed Queue"（RFC 番号はまだ付いていない） | https://datatracker.ietf.org/doc/draft-ietf-oauth-identity-chaining/ |
| OAuth 2.0 for Browser-Based Apps | **RFC 10017**（BCP 212, 2026-08） | https://datatracker.ietf.org/doc/draft-ietf-oauth-browser-based-apps/ |
| SD-JWT | **RFC 9901**（2025-11） | https://datatracker.ietf.org/doc/rfc9901 |
| MCP | 現行のプロトコル版は `2026-07-28`。この版で Dynamic Client Registration は deprecated | https://modelcontextprotocol.io/specification/latest/basic/security_best_practices |
| CAEP / SSF | OpenID CAEP 1.0 と Shared Signals Framework 1.0 はいずれも final | https://openid.net/specs/openid-caep-1_0-final.html , https://openid.net/specs/openid-sharedsignals-framework-1_0-final.html |

---

## 1. 三種類のプリンシパルと、1 リクエストでの同時表現

### 1.1 三種類のプリンシパル

| 種類 | 例 | 代表的な表現 |
|---|---|---|
| エンドユーザー | 社員、顧客、パートナーの担当者 | IdP が発行する AT/IDT の `sub`。Entra なら `oid`+`tid` |
| サービス/ワークロード | マイクロサービス、ジョブ、エージェント | SPIFFE ID（`spiffe://trust-domain/path`）を X.509-SVID または JWT-SVID で表す。OAuth の client credentials。クラウドのサービスアカウント／マネージド ID |
| システム/プラットフォーム自身 | クラウド事業者のサービス、運用者、バッチ、break-glass | AWS の service-linked role、FAS。CloudEvents の `authtype=system` |

- SPIFFE ID は URI 形式 `spiffe://trust domain/workload identifier` で、SVID は SPIFFE ID を 1 つだけ持つ。https://spiffe.io/docs/latest/spiffe-about/spiffe-concepts/
- JWT-SVID では `sub` = SPIFFE ID、`aud` は MUST。aud は 1 個が強く推奨される（複数あると受信者が別の受信者へ再送して「なりすまし」できるため）。`exp` は短めにすることが推奨される。https://github.com/spiffe/spiffe/blob/main/standards/JWT-SVID.md §3.1, §3.2, §7.1, §7.2
- AWS の service-linked role は「サービスが事前に定義し、原則としてそのサービスだけが引き受けられる」ロールで、管理者は閲覧はできても権限を編集できない。https://docs.aws.amazon.com/IAM/latest/UserGuide/using-service-linked-roles.html
- CloudEvents の Auth Context 拡張では、`authtype` が `app_user` / `user` / `service_account` / `api_key` / `system` の 5 種類を区別する。`system` は「TTL による削除などでプラットフォームがイベントを起こした場合の、伏せられた ID」。https://github.com/cloudevents/spec/blob/main/cloudevents/extensions/authcontext.md
- 運用者と break-glass を表す標準クレームは見つからなかった **[未検証]**。代わりに RFC 8693 の `may_act` が使える。これは「`sub` の代理として行動してよい者」を表し、仕様の例は「admin@example.com が user@example.com の代理として行動してよい」。https://www.rfc-editor.org/rfc/rfc8693.html §4.4

### 1.2 「ユーザー＋ワークロード（＋経由したサービス）」を同時に運ぶ実例

| 方式 | ユーザー | ワークロード | 経路（チェーン） | 出典 |
|---|---|---|---|---|
| Google BeyondProd | **end-user context ticket**。エンドユーザー認証サービスが中央発行し、完全性保護された、転送可能なクレデンシャル | ALTS のサービス ID（RPC ライブラリに組み込み） | サービスアクセス管理のポリシーと監査 | https://cloud.google.com/docs/security/beyondprod |
| Netflix Passport | Edge（Zuul）でリクエストごとに作る「短命の ID 構造体」。ユーザーと端末の ID を持つ。protobuf 形式、HMAC(SHA-256) で完全性保護。`PassportAuthenticationLevel`（LOW/HIGH/HIGHEST）と `Source`（COOKIE、MSL、PARTNER_TOKEN など）も持つ | 社内 mTLS **[未検証]**（ブログに記述なし） | — | https://netflixtechblog.com/edge-authentication-and-token-agnostic-identity-propagation-514e47e0b602 |
| Transaction Tokens | `sub`（トランザクションの主体） | `req_wl`（Txn-Token を要求したワークロード） | 置換時も「元のトークンを要求したワークロードのコールチェーン」を保持しなければならない (MUST) | draft-11 §9.2, §13.15 |
| RFC 8693 `act` | 最上位の `sub` | `act`（現在のアクター） | `act` のネストで委任チェーンを表す。ただし **アクセス制御に使ってよいのは最上位クレームと現在のアクターだけ**で、ネストした過去のアクターは「informational only」 | RFC 8693 §4.1 |
| AWS FAS | 呼び出し元プリンシパルの権限をそのまま使う | サービス（CloudFormation など） | `aws:CalledVia`、`aws:CalledViaFirst`、`aws:CalledViaLast` にサービスプリンシパルが入り、`aws:ViaAWSService=true` になる | https://docs.aws.amazon.com/IAM/latest/UserGuide/access_forward_access_sessions.html |
| Entra OBO | 中間 API が受け取った AT（`aud` は中間 API でなければならない） | 中間 API の client_id | 1 ホップずつ交換する。app-only トークンは OBO にかけられない（OBO はユーザープリンシパル専用） | https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-on-behalf-of-flow |
| Google Agent Identity | 3 層に分かれる。ユーザー ID、エージェント ID（SPIFFE と X.509）、**委任 ID**（エージェントがユーザーの代理として行動するときの複合的な権限文脈） | `spiffe://…/resources/aiplatform/…/reasoningEngines/<agent>` | Agent Identity auth manager が 3LO のクレデンシャルを仲介する | https://docs.cloud.google.com/iam/docs/agent-identity-overview |

### 1.3 confused deputy と、クレームでチェーンを見せること

- AWS の整理は 2 つ。サービス間の confused deputy には、リソースポリシーで `aws:SourceArn` / `aws:SourceAccount` / `aws:SourceOrgID` / `aws:SourceOrgPaths` を使って「自分のために動いているサービスか」を確かめる。https://docs.aws.amazon.com/IAM/latest/UserGuide/confused-deputy.html
- FAS には注意点がある。最初のリクエストが VPC エンドポイント経由だった場合、`aws:SourceVpce` / `aws:SourceVpc` / `aws:VpcSourceIp` は FAS リクエストに引き継がれない。これらで制限するポリシーには `aws:ViaAWSService` または `aws:CalledVia` で例外を設ける必要がある。公開エンドポイント経由なら `aws:SourceIP` は引き継がれる。（同 FAS ページ）
  → スライド向けの教訓: **アクセス元の文脈（IP/VPC）はホップをまたぐと消えたり変わったりする。経由情報（CalledVia）は別の属性として明示する。**
- MCP は token passthrough を明示的に禁止している。理由として、aud 検証が抜けること、下流が「MCP サーバーが検証済み」と誤信して confused deputy になること、監査証跡が壊れることを挙げる。対策は「MCP サーバーは自分宛てに発行されたトークン以外を受け入れてはならない (MUST NOT)」。https://modelcontextprotocol.io/specification/latest/basic/security_best_practices

**設計上の含意**: 「誰の権限で（`sub`）」「誰が実行しているか（`act` / `req_wl` / mTLS のピア ID）」「どこを経由したか（CalledVia 相当）」を **別々のクレームや別々のチャネル**で運ぶ。そうすれば下流が「ユーザー権限」と「サービス権限」を混同しない。

---

## 2. クレームはどこで生まれ、どこで足されるか（ステージ別）

| ステージ | 代表的な仕組み | ここに入れてよいもの | ここに入れてはいけないもの |
|---|---|---|---|
| ① IdP での認証時 | `acr`/`amr`/`auth_time`、Entra の `amr` 値表 | 認証の事実（方式、時刻、保証レベル） | 業務上の権限の詳細（認証の事実とは寿命も変更頻度も違う） |
| ② 発行時フック | Entra custom claims provider、Auth0 Actions、Okta token inline hook、Cognito pre token generation、Keycloak mappers | テナント ID、課金プラン、粗いロールなど、比較的安定した属性 | 秒単位で変わる状態（残高、在庫、リスクスコア）。生年月日などの生 PII（§7） |
| ③ エッジ／ゲートウェイ | phantom token、split token、Netflix Passport、Envoy ext_authz、Istio `outputClaimToHeaders` | 内部用の「値渡し」トークン、正規化した主体 ID、認証レベル | クライアントが送ってきた同名ヘッダーの値（必ず上書きするか除去する） |
| ④ メッシュ内（サービス間） | Transaction Tokens（`txn`/`scope`/`tctx`/`rctx`/`req_wl`）、mTLS/SPIFFE | 呼び出しチェーン全体で不変の文脈、トランザクション ID | 外部から受け取った AT そのもの（draft-11 §13.4 で MUST NOT） |
| ⑤ step-up | RFC 9470 `insufficient_user_authentication` + `acr_values`/`max_age` | より強い・より新しい認証の事実 | — |
| ⑥ 同意／承認 | RAR `authorization_details`、CIBA `binding_message` | 承認された具体的な取引内容（金額、相手先など） | 承認していない操作 |

### 2.1 発行時フック（外部 API 呼び出しとレイテンシ・障害時の扱い）

| IdP | いつ呼ばれるか | 外部呼び出しの制約 | 失敗時の挙動 | 出典 |
|---|---|---|---|---|
| Entra（custom claims provider） | `OnTokenIssuanceStart`（トークンを発行する直前） | REST API は公開されている必要がある。返したクレームは **claims mapping policy で明示的にマップしたものだけ**がトークンに入る。返せる型は String と String 配列のみ（Boolean と JSON は非対応）。合計 **3KB まで** | **[未検証]**（タイムアウト値とリトライ回数は取得したページで確認できなかった） | https://learn.microsoft.com/en-us/entra/identity-platform/custom-claims-provider-reference , https://learn.microsoft.com/en-us/entra/identity-platform/custom-extension-overview |
| Entra（API 側の保護） | — | Entra は bearer トークン付きで REST API を呼ぶ。API は `azp`/`appid` = `99045fe1-7639-4a75-9d4a-577b6ca3810f`、`aud`、`iss` を検証する | — | 同 custom-extension-overview |
| Okta（token inline hook） | カスタム AS が OAuth/OIDC トークンを発行するとき（org AS では使えない） | デフォルトのタイムアウトは **3 秒**。token inline hook は **リトライしない**。外部サービスが遅いと同時実行のレート制限を圧迫する | **フローは続行し、元のトークンがそのまま返る**（クレームは付かない） | https://developer.okta.com/docs/concepts/inline-hooks/ , https://developer.okta.com/docs/api/openapi/okta-management/management/tags/inlinehook/webhooks/createtokeninlinehook |
| Auth0（post-login Action） | ログイン後に加え、**RT を交換するときにも実行される** | 同期実行（Action が終わるまで後続のパイプラインはブロックされる） | **[未検証]**（タイムアウト値） | https://auth0.com/docs/customize/actions/explore-triggers/signup-and-login-triggers/login-trigger |
| Auth0（M2M） | `credentials-exchange`（client credentials で AT を返す前） | — | — | https://auth0.com/docs/customize/actions/explore-triggers/signup-and-login-triggers/login-trigger/post-login-event-object |
| Cognito（pre token generation） | triggerSource で区別される。**`TokenGeneration_RefreshTokens`（リフレッシュ時）**、`TokenGeneration_ClientCredentials`（V3_0 のみ）など | AT のスコープやクレームの追加・抑止は V2_0 以上 | **[未検証]** | https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-pre-token-generation.html |
| Keycloak（protocol mappers） | トークンを生成するとき | — | — | https://www.keycloak.org/admin-api/protocol-mappers |

**設計の要点**:
- Okta は「フックが失敗してもクレームなしでトークンが出る」。したがって **RS は、カスタムクレームがないときに拒否（fail-closed）するよう実装する**。クレームがないことを「権限なし」と解釈し、「デフォルト権限あり」と解釈しない。
- Entra の custom claims provider のサンプルは `DateOfBirth` を返している。しかしこれは §7 の最小化原則（NIST 800-63C-4 の派生属性）と衝突する。スライドでは反面教師として使える。

### 2.2 エッジ／ゲートウェイでの変換

- **Phantom token**（Curity）: クライアントには参照型（opaque）のトークンを渡す。リバースプロキシがイントロスペクションで値型の JWT を取得し、それに差し替えてマイクロサービスへ渡す。結果として、クライアントにはクレームが見えず、API は JWT の利点を得られる。https://curity.io/resources/learn/phantom-token-pattern/
- **Split token**（Curity）: AS が JWT を「署名部分」と「ヘッダー＋本文」に分ける。署名部分を opaque トークンとしてクライアントに渡す。ゲートウェイには「署名のハッシュ」と「ヘッダー＋本文」を送り、署名のハッシュをキーに exp までキャッシュさせる。リクエストが来たら連結して API に転送する。イントロスペクションの往復が要らない。https://curity.io/resources/learn/split-token-pattern/
- **Netflix Passport**: 外部トークンの種類（Cookie、MSL、パートナートークン）を Edge で吸収する。内部には「トークンに依存しない」Passport だけを流す。下流は Passport Introspector で完全性を確認してから値を使う。（§1.2 の出典）
- **Envoy ext_authz**: 外部の認可サービスに問い合わせ、拒否なら 403 を返す。認可サービスが返したメタデータを上流（または下流）へ伝播できる。ext_authz の後にルートキャッシュがクリアされると、別ルートに再ルーティングされて認可を迂回できる、という注意書きがある。https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/ext_authz_filter
- **Istio RequestAuthentication**: `outputClaimToHeaders` は検証済み JWT のクレームをヘッダーに出力する。**同名ヘッダーが既にあれば上書きする**。対応する型は string/int/bool のみで、experimental。`outputPayloadToHeader` はペイロード全体を base64 で出力する。`forwardOriginalToken` のデフォルトは false。資格情報なしのリクエストは「ID なし」として通るので、AuthorizationPolicy と組み合わせる必要がある。https://istio.io/latest/docs/reference/config/security/request_authentication/
- Kong と Apigee の具体的な設定は今回取得していない **[未検証]**。

### 2.3 メッシュ内: Transaction Tokens（draft-11）

| クレーム | 必須性 | 中身 |
|---|---|---|
| `iat`, `exp` | REQUIRED | — |
| `aud` | REQUIRED | Trust Domain。aud で示された Trust Domain の外では受け入れてはならない (MUST NOT) |
| `txn` | REQUIRED | 一意のトランザクション ID（RFC 8417 §2.2 の定義） |
| `sub` | REQUIRED | トランザクションの主体。aud の Trust Domain 内で一意 |
| `scope` | REQUIRED | TTS が決める。要求された scope と一致する必要はなく、「最も狭い目的」を表す |
| `tctx` | RECOMMENDED | コールチェーン全体で不変の値 |
| `rctx` | RECOMMENDED | 環境的な文脈（要求元 IP など） |
| `req_wl` | REQUIRED | Txn-Token を要求したワークロード |
| `iss` | OPTIONAL | — |

- 取得方法: RFC 8693 のトークン交換で、`requested_token_type=urn:ietf:params:oauth:token-type:txn_token` を指定する。`subject_token` に refresh token は使えない。self_signed / unsigned_json 形式の subject も可。`request_context` が `rctx` に、`request_details` が `tctx` に反映される。レスポンスに refresh token を含めてはならない。
- 伝送: `Txn-Token` ヘッダーで送る。**`Authorization` ヘッダーは使ってはならない (MUST NOT)**。ワークロードは受け取った Txn-Token を改変せずに転送する。
- 置換（replacement）: 許可される操作を減らすことと、表明値を追加することはできる (MAY)。**scope の拡大と、`txn`/`sub`/`aud` の変更は MUST NOT**。期限切れの入力からは発行しない。
- 寿命: 「分以下のオーダー」。長時間のバッチも短命の Txn-Token で扱う。
- 禁止事項: Txn-Token を OAuth の AT や認証クレデンシャルとして使わない。Txn-Token を丸ごとログに出さない（§15.2）。
- 出典: https://www.ietf.org/archive/id/draft-ietf-oauth-transaction-tokens-11.html §6, §9.2, §11, §12, §13, §15.2

### 2.4 step-up（RFC 9470）

- RS が `WWW-Authenticate: Bearer error="insufficient_user_authentication", acr_values="…"` または `max_age="5"` を返す。クライアントはこの値で認可リクエストを組み立て直し、新しい AT を取得する。AS 側の挙動は OIDC のままでよい。https://www.rfc-editor.org/rfc/rfc9470.html
- Entra の場合: `acrs`（Auth Context ID）と `xms_cc=cp1`（クライアントが claims challenge を扱える）の組で同じことを実現する。https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference
- **含意**: 認証強度のクレームは「AT 発行時点の事実」にすぎない。高リスク操作は RS が `auth_time`/`acr` を見て、その都度 step-up を要求する。

### 2.5 同意／承認（RAR, CIBA）

- RAR: AS は `authorization_details` を JWT AT かイントロスペクション応答に入れてよい (MAY)。JWT に入れるときは **audience ごとにフィルタして**トップレベルクレームにすることが推奨される。https://www.rfc-editor.org/rfc/rfc9396.html §9.1, §9.2
- CIBA: 結果の受け取り方は poll / ping / push の 3 モード。認証要求には `binding_message` と `login_hint_token` を入れられる。https://openid.net/specs/openid-client-initiated-backchannel-authentication-core-1_0.html §5
- Auth0 Asynchronous Authorization: CIBA と RAR（任意）を組み合わせ、エージェントのバックエンドが `/bc-authorize` に要求を出す。ユーザーは Guardian アプリへのプッシュで承認し、エージェントは `/token` をポーリングする。https://auth0.com/ai/docs/intro/asynchronous-authorization , https://auth0.com/docs/get-started/auth0-for-ai-agents

---

## 3. 縮小と拡張（ホップごとのダウンスコープ、リフレッシュ）

### 3.1 原則

- RFC 9700 §2.3: AT は特定の RS に audience を限定すべきで (SHOULD)、リソースと操作も限定すべき (SHOULD)。手段は `scope`、`authorization_details`、`resource`（RFC 8707）。https://www.rfc-editor.org/rfc/rfc9700.html
- RFC 8693 はスコープ縮小を **要求していない**。§5 は「scope と短い寿命の併用を推奨」しているだけで、§2.1.1 も「要求する範囲には分別を」と述べる程度である。→ **「下流トークンは上流より強くしない」は組織のポリシーとして明文化する必要がある**。https://www.rfc-editor.org/rfc/rfc8693.html
- 規範として「縮小のみ」を定めているもの:
  - Transaction Tokens: 要求する scope は subject token の scope と「同じかそれ以下」。subject token の scope を判別できなければ拒否しなければならない (MUST)。置換で scope を拡大してはならない。（draft-11 §13.6, §13.14, §13.15）
  - OAuth 2.1: RT は「リソースオーナーが同意した scope と RS に束縛されなければならない (MUST)」。（draft-17 §3.2.3）
- 寿命についての注意: Transaction Tokens は「Txn-Token の寿命が提示されたトークンの期限を超えてもよい（TTS のポリシー次第）」としている（§6）。つまり **「上流より長生きしない」を仕様は強制していない**。組織のルールで上限を決める。
- 委任チェーンの縮小（attenuation）: RFC 8693 のネストした `act` は情報提供にすぎず、縮小を構造的に保証しない。2026 年にはこの点を扱う個人ドラフトが多数出ている（例: draft-sweeney-wimse-credential-delegation-00、draft-niyikiza-oauth-attenuating-agent-tokens-02、draft-mishra-oauth-agent-grants-02）。いずれも個人ドラフトで、**標準化されていない**。
  - https://www.ietf.org/archive/id/draft-sweeney-wimse-credential-delegation-00.html
  - https://datatracker.ietf.org/doc/draft-niyikiza-oauth-attenuating-agent-tokens
  - https://www.ietf.org/archive/id/draft-mishra-oauth-agent-grants-02.html

### 3.2 リフレッシュ時にクレームはどう変わるか

| IdP | リフレッシュ時の再評価 | 出典 |
|---|---|---|
| Auth0 | post-login Action が RT 交換時にも実行される → **カスタムクレームは再計算される** | https://auth0.com/docs/customize/actions/explore-triggers/signup-and-login-triggers/login-trigger |
| Cognito | pre token generation が `TokenGeneration_RefreshTokens` で呼ばれる → **Lambda の中で再計算できる** | https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-pre-token-generation.html |
| Okta | token inline hook は「トークン発行時」に呼ばれると説明されている。refresh_token グラントで呼ばれるかどうかは取得したページで確認できず **[未検証]** | https://developer.okta.com/docs/api/openapi/okta-management/management/tags/inlinehook/webhooks/createtokeninlinehook |
| Entra | RT は「ユーザー＋クライアント」に束縛され、リソースやテナントには束縛されない（同じ RT で別リソースの AT も取れる）。RT は使うたびに新しい RT に置き換わるが、**古い RT は失効しない**（再利用検知はない）。グループや custom claims が RT 利用時に再評価されるかどうかは **[未検証]** | https://learn.microsoft.com/en-us/entra/identity-platform/refresh-tokens |
| Keycloak | トークン交換で RT を発行すると「subject token の期限を大きく超えて、ユーザーセッションが続く限り新しいトークンを得られる」と公式に警告し、新しい subject token での再交換を推奨している。protocol mapper がリフレッシュ時に再実行されるかについては、カスタム mapper でクレームが消えたというフォーラム報告がある程度で、公式の記述は確認できなかった **[未検証]** | https://www.keycloak.org/securing-apps/token-exchange , https://forum.keycloak.org/t/custom-claims-are-missing-in-access-token-when-generated-using-refresh-token/24629 |

**含意（stale attributes）**: リフレッシュでクレームが再評価されない IdP では、AT の属性は「RT の寿命の間」古いまま残りうる。Entra の RT は既定で 90 日（SPA は 24 時間）である。権限の剥奪を即時に効かせたいなら、AT を短命にし、RS 側で参照（PDP）を引き、CAE/SSF のイベントを受ける。この 3 つを組み合わせる。

---

## 4. 寿命（AT / RT / IDT / セッション）と非同期処理

### 4.1 推奨値と規範

| 対象 | 推奨・規範 | 出典 |
|---|---|---|
| AT | OAuth 2.1 は「漏えいの影響を抑えるため短命」とする。クライアントは提示された寿命まで AT が有効だと期待してはならない（AS は早期に失効させうる） | draft-ietf-oauth-v2-1-17 §1.4, §3.2.3 |
| AT（FAPI 2.0） | 長期の grant（数日〜数週間）なら、短命の AT（数分〜数時間）と RT の組み合わせを検討する。短すぎると AS への負荷と依存が増す | https://openid.net/specs/fapi-security-profile-2_0-final.html §6.1 |
| AT（Entra） | 既定は 1 時間。CAE 対応クライアントでは最長 28 時間（重大イベントで失効させる前提） | https://learn.microsoft.com/en-us/entra/identity/conditional-access/concept-continuous-access-evaluation |
| 認可コード（FAPI 2.0） | 最大 60 秒 | FAPI 2.0 §5.3.2.1 |
| JARM の応答 JWT | 最大 10 分を推奨 | https://openid.net/specs/oauth-v2-jarm-final.html |
| Txn-Token | 分以下 | draft-11 §6 |
| ID-JAG | 固定値は定めていない。例示は 300 秒 | draft-06 §4.3.4 |
| RT（公開クライアント） | sender-constrained にするか、ローテーションしなければならない (MUST) | RFC 9700 §2.2.2 |
| RT（ローテーションと再利用検知） | 更新のたびに新しい RT を発行し、古い RT を無効化する。無効化済みの RT が提示されたら、アクティブな RT も失効させる。一定期間クライアントが非アクティブなら RT は失効させるべき (SHOULD)。パスワード変更やログアウトで自動失効させてよい (MAY) | RFC 9700 §4.14.2 |
| RT（FAPI 2.0） | **AS はローテーションを使ってはならない（例外的な状況を除く）**。機密クライアントと sender-constrained な AT の組み合わせではローテーションの利点がなく、UX と運用を悪化させるため。一方でクライアントは、RT とそのローテーションをサポートしなければならない (shall) | FAPI 2.0 §5.3.2.1 item 9 と NOTE 1, §5.3.3.1 item 6 |
| AT の sender constraint（FAPI 2.0） | sender-constrained な AT だけを発行する（MTLS または DPoP） | FAPI 2.0 §5.3.2.1 |
| 再認証（NIST SP 800-63B-4） | **AAL1**: 全体のタイムアウトは 30 日以下を推奨、非アクティブタイムアウトは任意。**AAL2**: 全体 24 時間以下、非アクティブ 1 時間以下。**AAL3**: 全体 12 時間以下（SHALL）、非アクティブ 15 分以下 | https://pages.nist.gov/800-63-4/sp800-63b.html §2.1.3, §2.2.3, §2.3.3 |
| Auth0 の再利用検知 | 再利用を検知すると RT ファミリー全体を無効化し、ログに `ferrt` を記録する | https://auth0.com/docs/secure/tokens/refresh-tokens/refresh-token-rotation |

- **RFC 9700 と FAPI 2.0 の違いは重要**: 一般の公開クライアントではローテーションが必須級だが、FAPI（機密クライアント＋sender constraint）ではローテーションが禁止される。どちらに従うかはクライアント種別ごとにポリシーを分ける。
- 時刻ずれ:
  - RFC 7519 §4.1.4 / §4.1.5 は、exp/nbf に「通常は数分以内の小さな leeway」を許している (MAY)。https://www.rfc-editor.org/rfc/rfc7519.html
  - FAPI 2.0 は、`iat`/`nbf` が未来に 0〜10 秒ずれている JWT は受け入れ、60 秒を超えて未来のものは拒否する。（FAPI 2.0 §5.3.2.1 item 13）

### 4.2 失効の伝播（CAE / Shared Signals）

- CAEP 1.0 は、session-revoked、token-claims-change、assurance-level-change、device-compliance-change などのイベントを SET で送る。`sub_id` には「ユーザー＋端末＋テナント」の複合 subject を書ける。https://openid.net/specs/openid-caep-1_0-final.html
- SSF 1.0 は SET の `txn` クレームを SHOULD とする。同じ原因から生じた複数の SET には同じ `txn` を使える。https://openid.net/specs/openid-sharedsignals-framework-1_0-final.html §4.1.9
- Entra CAE では、egress IP が RP 側と Entra 側で異なると IP ベースの強制が誤作動しうる。そのため、共有 IP や列挙できない IP を信頼済みの場所に入れないよう注意喚起している。（同 CAE ページの表）

### 4.3 長時間ジョブと非同期メッセージング（ユーザーが去った後の「アクター」）

- `offline_access`（OIDC Core §11）は、ユーザーが不在でも UserInfo などにアクセスするための RT を要求するスコープ。https://openid.net/specs/openid-connect-core-1_0.html#OfflineAccess
- 長時間のバッチやオフライン処理も、短命の Txn-Token に頼るべきだとされる。（draft-11 §6）
- CloudEvents Auth Context の `authclaims` は、**なりすましに足る実クレデンシャルを含めてはならない (MUST NOT)**。一方で、Consumer が ID サービスで「元のプリンシパルになりすますクレデンシャル」を作り直せるだけの情報なら含めてよい (MAY)。`authid` に PII を入れることは不適切とされ、ハッシュなどの間接参照を推奨している。この拡張は「情報提供用」で、イベントの安全性を保証するものではない。https://github.com/cloudevents/spec/blob/main/cloudevents/extensions/authcontext.md
- Google Pub/Sub の push サブスクリプション: 配信のたびに **サービスアカウントの OIDC トークン**が付く。受信側は `aud` に加えて `email`（期待するサービスアカウント）と `email_verified=true` も検証する。→ 非同期の配送は「ワークロード ID」で認証し、ユーザー文脈はメッセージ本体のメタデータとして運ぶ、という分業の実例。https://cloud.google.com/pubsub/docs/authenticate-push-subscriptions
- Keycloak は、トークン交換で RT を出すとセッションが続く限り subject token の期限を越えられると警告している。（§3.2）
- **ユーザーのトークンが切れた後に下流呼び出しが発生した場合の設計オプション**:
  1. キューにはユーザーの AT を入れず、`sub`/`tenant`/`txn`/承認 ID だけを入れる。
  2. コンシューマーは自身のワークロード ID でトークン交換し、`sub`（ユーザー）と `act`（ジョブ）を持つ短命トークンを作り直す。
  3. 作り直しの可否は「元の同意・承認記録が有効か」で AS が判断する。
  
  2 と 3 の組み合わせは複数ベンダーの部品から導いた推奨で、単一の仕様に書かれた手順ではない **[未検証]**。

---

## 5. アクセス元／文脈クレーム（IP、端末、場所、チャネル）

| IdP | 文脈系クレーム | 出典 |
|---|---|---|
| Entra | `ipaddr`（ログイン元の IP。v1 では常に含まれ、v2 では optional）、`in_corp`（社内ネットワークからか。MFA の信頼済み IP 設定に基づく）、`fwd`（VNET 内での元のクライアントアドレス）、`vnet`、`ctry`/`tenant_ctry`、`xms_pdl`（優先データ所在地）、`xms_cc`、`acrs`、`ztdid`（Autopilot の端末 ID） | https://learn.microsoft.com/en-us/entra/identity-platform/optional-claims-reference , https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference |
| Entra custom claims provider への入力 | `authenticationContext.client.ip` と locale が REST API に渡される → IP をトークンに焼き込むこともできてしまう | https://learn.microsoft.com/en-us/entra/identity-platform/custom-claims-provider-reference |
| Netflix Passport | `Source`（Cookie、MSL、パートナー）と認証レベル | §1.2 の出典 |
| Entra の `deviceid` / Intune のコンプライアンス | 取得したページでは確認できなかった **[未検証]**（02 ノート参照） | — |
| Okta | アクセス元の文脈を AT に入れる標準クレームは確認できなかった **[未検証]** | — |

**なぜ古くなるのか、なぜ偽装されるのか**:
- `ipaddr` は「認証した時点」の IP である。AT の寿命（Entra の既定 1 時間、CAE では最長 28 時間）の間にネットワークが変わっても値は変わらない。
- egress IP は Entra 側と RP 側で異なりうる。（CAE ページの表）
- FAS でも VPC 系の文脈キーはホップで消える。（§1.3）
- ヘッダー由来の文脈（`X-Forwarded-For`、User-Agent）はクライアントが偽装できる。ゲートウェイで上書きしない限り信頼できない（Istio は同名ヘッダーを上書きする。§2.2）。

**代替案: PEP でリクエスト時に評価する**:
- NIST SP 800-207 は、PE（Policy Engine）が企業ポリシーと外部ソース（CDM、脅威インテリジェンス）を入力にして、アクセスを許可・拒否・取り消しすると定める。PA（Policy Administrator）がセッション固有の認証トークンを生成し、PEP に経路の開閉を指示する。https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-207.pdf §3
- ゼロトラストの基本原則（SP 800-207 §2.1）は 2 つある。「リソースへのアクセスはセッション単位で許可する」と「アクセスは、クライアント ID、アプリ、要求資産の観測可能な状態などを含む動的ポリシーで決める」。これは SP 800-207 の記述に基づく要約で、原文の逐語確認は今回していない **[未検証]**。
- 推奨: トークンには「認証時の文脈（`acr`、`amr`、認証時の IP など）」だけを、その旨が分かる名前で入れる。「今の文脈」は PEP（ゲートウェイやサイドカー）が実際の接続から取得し、Txn-Token の `rctx` のように **TTS が権威を持つ** フィールドに入れる（draft-11 は、TTS が `rctx`/`tctx` の値をそのまま写すことも、導出することも、独自に表明することもできるとしている）。

---

## 6. 処理結果を署名付きで返す・次段へ渡す

| 方式 | 何に使うか | 要点 | 出典 |
|---|---|---|---|
| JWT イントロスペクション応答（RFC 9701） | RS が AS の判断を否認できない形で受け取る | `Accept: application/token-introspection+jwt`。`typ` も同じ値。署名、または署名後に暗号化（ネスト JWT）。**この JWT は AT の代替表現ではなく、AT として使ってはならない** | https://www.rfc-editor.org/rfc/rfc9701.html |
| 署名付き UserInfo | ユーザー属性の否認防止 | OIDC Core §5.3.2（`userinfo_signed_response_alg`）。今回は本文を取得していない **[未検証]** | https://openid.net/specs/openid-connect-core-1_0.html#UserInfoResponse |
| JARM | 認可応答の完全性、送信者認証、audience 制限、mix-up 対策 | `iss`/`aud`/`exp` を必須とし、最大 10 分を推奨。`alg=none` は拒否 | https://openid.net/specs/oauth-v2-jarm-final.html |
| HTTP Message Signatures（RFC 9421） | Webhook やサービス間の応答の署名 | 対象コンポーネント（`@method`、`@authority`、`@path`、`Content-Digest` など）とパラメータ（`created`、`expires`、`keyid`、`tag`）をアプリ側で要求できる。最大署名年齢を強制でき、`alg` パラメータを禁止できる | https://www.rfc-editor.org/rfc/rfc9421.html |
| SET（RFC 8417）/ CAEP | 状態変化の通知 | §4.2 を参照 | — |
| SD-JWT（RFC 9901）/ SD-JWT VC | 「検証済み結果」を後で選択的に開示する | SD-JWT VC は IETF のドラフト（ライブラリの記載では draft-15）**[未検証: 最新版]** | https://datatracker.ietf.org/doc/rfc9901 , https://sdjwt.js.org |
| 承認の受領証 | 人による承認の証跡 | RAR の `authorization_details` を承認済みトークンに入れる（§2.5）。CIBA の結果は AT/IDT として返る | RFC 9396 §9, CIBA §5 |

**JWT が適しているとき**:
- 結果が **自己完結した主張** で、受け手が後で第三者に提示する（否認防止が必要）。
- 受け手が複数いる、またはオフラインで検証したい。
- 有効期限と audience が意味を持つ（例: 承認済みの取引内容、属性の判定結果、イントロスペクション結果）。

**JWT が適さないとき**:
- 大きなペイロードや、ストリームになる業務データ。→ HTTP Message Signatures（RFC 9421）と `Content-Digest` で本文を保護するほうが自然。
- 結果を即時に取り消す必要がある。→ JWT は発行後に撤回できないので、参照型にする。
- 中身に機密が含まれ、経路上のすべての中継者に見せたくない（§7）。
- RFC 9701 にあるように、結果の JWT を AT として流用するのは誤り。`typ` で用途を区別する（RFC 8725 §3.11 の明示的型付け、§3.12 の「種類ごとに相互排他的な検証規則」）。https://www.rfc-editor.org/rfc/rfc8725.html

---

## 7. 機微情報とマスキング

- **JWS は保持者全員に読める**: RFC 7519 §12 は 3 点を述べる。JWT が機微情報を含むなら漏えいを防ぐ措置が MUST であること。その方法は暗号化 JWT＋受信者の認証、または TLS 上でのみ送ること。そして「**機微情報を JWT に含めないのが最も簡単な対策**」であること。https://www.rfc-editor.org/rfc/rfc7519.html
- **JWE のネスト**: RFC 8725 §3.3 は、ネスト JWT では外側と内側の両方の暗号処理を検証しなければならない (MUST) とする。§2.3 は、内側の署名を検証しないライブラリがあると警告している。RFC 9701 も「署名＋暗号化ならネスト JWT」と定めている。https://www.rfc-editor.org/rfc/rfc8725.html
- **ペアワイズ識別子**: Entra の `sub` は「受信者、テナント、ユーザー」の組み合わせごとのペアワイズ値で、`oid` はアプリをまたいで共通。サービス間でデータを共有するなら `oid`+`tid`、アプリ単位の識別には `sub` を使う。https://learn.microsoft.com/en-us/entra/identity-platform/id-token-claims-reference
  ID-JAG の `sub` も「aud の Resource AS 向けに選んだ識別子」である。（draft-06 §3.1）
- **派生属性値**: NIST SP 800-63C-4 は、RP が完全な属性値ではなく派生属性値（例: 「13 歳以上か」に Y/N で答える）を要求することを推奨している。派生属性値は元の値を開示してはならない (SHALL NOT)。選択的開示の技術を使えば、完全な値と派生値を同じ応答に載せて必要な分だけ開示できる。https://pages.nist.gov/800-63-4/sp800-63c.html
- **SD-JWT**（RFC 9901）: 保持者が開示するクレームを選べる。上の NIST の選択的開示に対応する実装手段。
- **mutable な識別子で認可しない**: Entra は `email`/`upn` を認可や保存に使わないよう明記している。https://learn.microsoft.com/en-us/entra/identity-platform/optional-claims-reference
- **ログ**:
  - OWASP Logging Cheat Sheet は、AT、セッション ID（必要ならハッシュに置き換える）、パスワード、機微な PII などを「ログに直接記録せず、除去・マスク・ハッシュ・暗号化する」対象に挙げている。https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
  - OpenTelemetry の HTTP セマンティック規約は、`http.request.header.<key>` と `http.response.header.<key>` について、記録するヘッダーを明示的に設定させるべき (SHOULD) とする。全ヘッダーを記録するのはセキュリティリスクだからである。https://opentelemetry.io/docs/specs/semconv/http/http-spans/
  - Txn-Token を丸ごとログに出すことも禁止されている（draft-11 §15.2）。
  - RFC 9700 §4.9.3 は、RS は AT を他の秘密情報と同様に扱わなければならない (MUST) とする。
- **URL と Referer**: RFC 9700 §4.3.2 は、クライアントは AT を URI のクエリパラメータで渡してはならない (MUST NOT) とする。§4.2 は Referer 経由での漏えいを、§4.3.1 は form_post を推奨することを述べている。
- **ブラウザ保存**: OAuth 2.0 for Browser-Based Apps は RFC 10017（BCP 212）になった。BFF などのパターンの詳細は本文で確認していない **[未検証: 個別推奨の逐語]**。https://datatracker.ietf.org/doc/draft-ietf-oauth-browser-based-apps/
- **イベント**: CloudEvents の `authid` には PII を入れず、間接参照にする。（§4.3）

---

## 8. AI エージェントのアクセスポリシー（フローでの付与・縮小）

※ MCP の基礎と各 IdP のエージェント用クレーム名（Entra の `xms_act_fct`/`xms_sub_fct`、Auth0 の `sub_profile` など）は 02 ノートと MCP ノートが扱う。ここではホップごとの変化だけを見る。

### 8.1 エージェント ID とユーザー委任をどう分けるか

- **Entra Agent ID（OBO）**: 3 段階の流れになる。
  1. agent identity blueprint がマネージド ID で T1 を取得する。`scope=api://AzureADTokenExchange/.default`、`fmi_path` で子のエージェント ID を指定する。
  2. 子のエージェント ID が `client_assertion=T1` と、ユーザーの AT Tc（`aud` は blueprint でなければならない）を持って OBO 交換する。
  3. Graph 宛てなど blueprint 以外を `aud` とする Tc は `AADSTS50013` で拒否される。
  
  つまり「ユーザー → blueprint → エージェント」の束縛を AS が検証する。https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/agent-on-behalf-of-oauth-flow
- **Okta Cross App Access / ID-JAG**: 次の順で進む。
  1. ユーザーが要求元アプリに SSO する。
  2. 要求元アプリは IDT または RT を IdP でトークン交換し、ID-JAG を得る。IdP は管理者が設定したアプリ間の接続で許された範囲でしか発行しない。
  3. 要求元アプリは Resource AS に JWT グラントとして提示し、短命でスコープを絞った AT を得る。
  
  https://developer.okta.com/docs/concepts/xaa/
  ID-JAG 本体（draft-06）の規定: `typ=oauth-id-jag+jwt`。必須クレームは `iss`、`sub`、`aud`（Resource AS）、`client_id`、`jti`、`exp`、`iat`。任意クレームは `resource`、`scope`、`authorization_details`、`act`、`auth_time`、`amr`、`tenant`（マルチテナント発行者なら MUST）。Resource AS は `client_id` と認証済みクライアントが一致しなければ `invalid_grant` で拒否する。**ID-JAG と交換するときは RT を返すべきでない (SHOULD NOT)**。https://www.ietf.org/archive/id/draft-ietf-oauth-identity-assertion-authz-grant-06.html §3.1, §4.3, §4.4.1, §4.4.4
- **AWS Bedrock AgentCore Identity**: エージェント ID は「エージェント固有の属性を持つワークロード ID」で、ARN は `…:workload-identity/directory/default/workload-identity/<agent>`。token vault が OAuth トークン、クライアント資格情報、API キーを KMS で暗号化して保管する。取得できるのはワークロード ID を証明できた正当なエージェントだけで、同じ信頼ドメイン内からの要求も個別に検証する。2LO（client credentials）と 3LO（authorization code）の両方に対応する。https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/key-features-and-benefits.html , https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity.html
  - ワークロードアクセストークンの API 名（GetWorkloadAccessTokenForJWT/ForUserId）とその中身は、取得したページで確認できず **[未検証]**。
- **Google Agent Identity**: ユーザー、エージェント、委任の 3 層（§1.2）。Google Cloud 向けの AT はエージェントの X.509 証明書に暗号学的に束縛され、Agent Gateway を通るときは DPoP も使う（二重束縛）。既定の Context-Aware Access ポリシーが、信頼済みランタイムの外での再送を防ぐ。Principal Access Boundary は egress 呼び出しで評価される。提供段階（Preview/GA）はページに記載がなく **[未検証]**。https://docs.cloud.google.com/iam/docs/agent-identity-overview

### 8.2 ツール単位のスコープ、人による承認、委任の深さ、タスク単位トークン

- **ツール単位のスコープ**: MCP のセキュリティベストプラクティスは段階的なスコープ付与を推奨する。最初は `mcp:tools-basic` のような最小限で始め、特権操作のときに `WWW-Authenticate scope="…"` で引き上げる。ワイルドカードや包括的なスコープは典型的な失敗として挙げられ、昇格イベントは相関 ID 付きでログに残すよう求めている。https://modelcontextprotocol.io/specification/latest/basic/security_best_practices
- **audience の束縛**: MCP クライアントは、認可リクエストとトークンリクエストの両方で RFC 8707 の `resource`（MCP サーバーの正規 URI）を指定しなければならない (MUST)。https://modelcontextprotocol.io/specification/latest/basic/authorization
- **人による承認の証跡**: CIBA と RAR（§2.5）を使う。Auth0 は「承認があったかどうかをエージェント自身に判断させず、ID を認識する認可フローから得る」ことを強調している。https://auth0.com/intro-to-iam/human-in-the-loop-ai-approvals
  承認内容（`authorization_details`）を audience ごとにフィルタしてトークンに入れるのが RAR の推奨である。
- **委任の深さ**: 標準（RFC 8693）には深さを制限する仕組みがない（ネストした `act` は情報提供のみ）。個人ドラフトの提案例:
  - draft-wei-aic-jwt-02: `chain_depth` と `max_depth`（ベストプラクティスとして max_depth は 1 以下）
  - draft-mishra-oauth-agent-grants-02: 委任の深さに上限を設け、ルートの承認から派生した全トークンを一括失効できるようにすべき (SHOULD)
  - draft-liu-ai-agent-authorization-integration-00: AS が最大深度を強制し、ホップごとにスコープが部分集合であることを検証する
  
  いずれも **個人ドラフトで、標準ではない**。
  - https://datatracker.ietf.org/doc/draft-wei-aic-jwt
  - https://www.ietf.org/archive/id/draft-mishra-oauth-agent-grants-02.html
  - https://www.ietf.org/archive/id/draft-liu-ai-agent-authorization-integration-00.html
  
  参考: draft-sweeney は「OAuth WG が 2026-06 に再チャーターされ、ユーザーの代理として動くエージェントが明示的にスコープに入った」と書いているが、これは個人ドラフトの記述であり、一次確認していない **[未検証]**。
- **タスク単位の短命トークン**: ID-JAG の例は 300 秒で、RT は出さない。Txn-Token は分以下で、RT を返してはならない。エージェント → ツールの各ホップでは、毎回トークン交換して `aud` を 1 つに絞る。

---

## 9. エンドツーエンドのフロー（6 例）

凡例: **+** 追加、**−** 除去、**✓** 検証、**→** 次のホップへ送るトークン

### フロー A: ブラウザ → BFF → ゲートウェイ → サービス群 → DB（社内向け Web）

| ホップ | 持つトークン | クレーム操作 |
|---|---|---|
| ブラウザ → BFF | セッション Cookie だけ（トークンはブラウザに置かない。RFC 10017 の BFF パターン **[未検証: 逐語]**） | — |
| BFF → IdP | 認可コードフロー → AT（opaque または JWT）、RT、IDT | IdP: **+** `acr`/`amr`/`auth_time`（認証時）。発行時フック: **+** `tenant`、`plan`（安定した属性のみ） |
| BFF → ゲートウェイ | AT（`aud`=ゲートウェイ／API。RFC 8707 の resource で指定） | BFF: IDT は API に送らない |
| ゲートウェイ | phantom token: opaque → イントロスペクション → 内部 JWT | ✓ `aud`/`exp`/`scope`。**−** クライアントが送ってきた `X-User-*` ヘッダー。**+** 正規化した `sub`。Istio なら `outputClaimToHeaders` で上書き |
| ゲートウェイ → TTS | 内部 JWT を subject_token にして Txn-Token を取得 | TTS: **+** `txn`、`scope`（最も狭い目的）、`tctx`（テナントなど不変の値）、`rctx`（接続から得た IP）、`req_wl`=ゲートウェイ。**−** 外部 AT 自体は入れない |
| サービス A → サービス B | mTLS（SPIFFE）＋ `Txn-Token` ヘッダー | ✓ ピアの SPIFFE ID と `req_wl`。✓ `scope` が操作に合うか。Txn-Token は改変せずに転送 |
| サービス B → DB | DB 用のワークロード資格情報 | ユーザーの AT を DB に渡さない。行レベルのフィルタには `tctx.tenant` を使う（データ層の詳細は別ノート） |
| 高リスク操作 | RS が `insufficient_user_authentication` を返す（RFC 9470） | ✓ `auth_time` が `max_age` 以内か。BFF が再認証して新しい AT を取得 |

### フロー B: 夜間バッチ／長時間ジョブ（ユーザーが去った後）

| ホップ | 持つトークン | クレーム操作 |
|---|---|---|
| ユーザーがジョブを予約 | ユーザーの AT（短命） | ジョブ登録 API: ✓ `scope=jobs:create`。ジョブレコードに `sub`、`tenant`、承認 ID、要求スコープを保存する。**AT と RT はキューにもジョブ DB にも保存しない** |
| スケジューラー → ワーカー | ワーカーのワークロード ID（JWT-SVID。`aud` は 1 つ、短い `exp`） | — |
| ワーカー → AS／TTS | トークン交換。subject はジョブレコードを根拠にした self_signed または unsigned_json（draft-11 §11）、actor はワーカーの SVID | TTS: **+** `sub`=ユーザー、`req_wl`=ワーカー、`scope`=ジョブに必要な最小限、`tctx.job_id`。寿命は分単位で、必要なたびに再取得する |
| ワーカー → 下流 | Txn-Token、または `act` 付きの短命 AT | ✓ `act.sub`=ワーカー。監査ログに「誰の権限で（sub）、誰が（act）」を記録 |
| ユーザーの権限が途中で剥奪された | CAEP の session-revoked / token-claims-change | 再取得の時点で AS が拒否する。これが、ジョブ側で長命トークンを持たない理由 |
| システム起因（TTL 削除など） | プラットフォームのサービス ID | CloudEvents なら `authtype=system`。ユーザー `sub` を捏造しない |

### フロー C: マルチテナント SaaS のリクエスト

| ホップ | 持つトークン | クレーム操作 |
|---|---|---|
| ログイン | AT。テナント固有の発行者、または `tid`/`tenant` 付き | 発行時フック: **+** `tenant`、テナント内ロール。ID-JAG ではマルチテナント発行者に `tenant` が MUST（draft-06 §6.1） |
| ゲートウェイ | ✓ `iss` とテナントの対応。✓ `aud` | **+** Txn-Token の `tctx.tenant`（以降は不変）。URL やヘッダーのテナント ID と一致するか確認し、不一致なら拒否 |
| サービス間 | Txn-Token | `tctx.tenant` は置換で変えられない（draft-11 は `sub`/`aud`/`txn` の変更を禁止し、`tctx` は TTS が権威を持つ） |
| テナント横断の運用者アクセス | 運用者自身の AT ＋ `may_act` または `act` | **+** `act.sub`=運用者。✓ break-glass の承認（RAR/CIBA）と期限。監査で `sub`（顧客）と `act`（運用者）を両方記録 |
| 識別子 | Entra なら `oid`+`tid`（アプリ横断）と `sub`（ペアワイズ）を使い分ける | 外部のパートナーにはペアワイズの値を出す |

### フロー D: AI エージェントがユーザーの代わりにツール → バックエンドを呼ぶ

| ホップ | 持つトークン | クレーム操作 |
|---|---|---|
| ユーザー → エージェントのアプリ | ユーザーの AT（`aud`=エージェント。Entra なら blueprint） | ✓ `aud`。MCP ではトークンをそのまま転送しない |
| エージェント → AS | トークン交換（Entra Agent ID の OBO、Auth0 の OBO、ID-JAG など） | AS: **+** `act`（エージェント ID）または製品固有のクレーム（02 ノート）。**−** ツールに不要な scope。`aud`=ツール（MCP サーバーの正規 URI）。寿命は分単位、RT なし |
| エージェント → MCP サーバー（ツール） | 上で得た AT | ✓ `aud`=自分（MUST NOT accept others）。✓ ツール単位の scope。不足なら `WWW-Authenticate scope=` で段階的に引き上げる |
| 機微な操作（送金、削除） | CIBA の bc-authorize ＋ RAR `authorization_details`（金額、相手先） | ユーザーが別端末で承認すると、**+** `authorization_details`（audience ごとにフィルタ）の入った AT が発行される。✓ RS は要求内容と承認内容が一致するか確認 |
| ツール → バックエンド API | ツール自身がトークン交換（もう 1 ホップ）。または token vault（AgentCore / Google auth manager）から 3LO のトークンを取得 | `act` のネストが深くなる。現在のアクターだけをアクセス制御に使う（RFC 8693 §4.1）。深さの上限は組織ポリシーで決める（標準はない） |
| 監査 | — | `sub`、全アクター、`txn`、承認 ID を相関させる。エージェント ID 経由の操作は、すべてエージェント ID に紐づけられる（Google auth manager の記述） |

### フロー E: パートナー／B2B API（ドメインをまたぐ）

| ホップ | 持つトークン | クレーム操作 |
|---|---|---|
| 自社サービス（ドメイン A） → 自社 AS | RFC 8693 トークン交換 → JWT 認可グラント | AS A: クレームの追加・削除・変更が可能（主体 ID の写像、最小化、ダウンスコープ）。`aud` は相手の AS 1 つにすることが推奨される（identity-chaining draft-17 §2.3, §2.5） |
| ドメイン A → パートナー AS（ドメイン B） | RFC 7523 の JWT bearer grant | AS B: ✓ `aud`=自分。**+** ドメイン B 向けにクレームを再変換。短命の AT を発行 |
| パートナー API | AT（mTLS または DPoP で sender-constrained。FAPI 2.0 なら必須） | ✓ cnf。署名付きのイントロスペクション応答（RFC 9701）を使うと、判断を否認できない形で残せる |
| 応答や Webhook の返却 | RFC 9421 で署名した HTTP メッセージ（`Content-Digest`、`created`、`keyid` を必須にする） | JWT にするのは「承認結果」のように自己完結した主張だけ |

### フロー F: イベント駆動の非同期チェーン（Pub/Sub、Kafka、ワークフロー）

| ホップ | 持つトークン | クレーム操作 |
|---|---|---|
| API → トピックへ発行 | 発行者のワークロード ID | イベントのメタデータに **+** `authtype=app_user`、`authid`=ハッシュ化または間接参照の ID、`txn`。**AT は入れない**（CloudEvents の authclaims はクレデンシャルを MUST NOT） |
| ブローカー → コンシューマー（push） | ブローカーが付けるサービスアカウントの OIDC トークン（Pub/Sub） | ✓ `aud`、`email`=期待するサービスアカウント、`email_verified` |
| コンシューマー → 下流 | コンシューマーの ID で Txn-Token を取得（subject はイベントの `authid` に基づく） | TTS: ユーザーがまだ有効か、承認がまだ有効かを判断してから、`sub`=ユーザー、`req_wl`=コンシューマーで発行する。古いイベントを再処理するときもこの判断が必ず通る |
| 失効 | SSF/CAEP の SET（`txn` で同じ原因のイベントを相関） | コンシューマーはユーザーが失効していれば処理を止める |

---

## 10. 設計ルール（出典付き、27 項目）

1. **ユーザー、ワークロード、経由サービスを別々のクレームやチャネルで運ぶ**（`sub` / `act` または `req_wl` / mTLS のピア ID / CalledVia 相当）。— RFC 8693 §4.1、draft-11 §9.2、AWS FAS
2. **アクセス制御に使うのは最上位クレームと現在のアクターだけ。ネストした `act` は監査にだけ使う。** — RFC 8693 §4.1
3. **下流トークンは scope でも audience でも上流を超えない。これは仕様が強制しないので組織ポリシーで明文化する。** — RFC 8693 §5（推奨のみ）、draft-11 §13.6/§13.15（縮小のみ）
4. **AT の `aud` は 1 つの RS に限定し、RFC 8707 の `resource` で要求する。** — RFC 9700 §2.3、JWT-SVID §7.2、MCP authorization
5. **受け取ったトークンを別の宛先へそのまま転送しない（token passthrough の禁止）。ホップごとにトークン交換する。** — MCP security best practices、Entra OBO（aud 不一致は拒否）
6. **外部 AT を内部トークンに埋め込まない。内部には Txn-Token や Passport のような内部専用の構造を流す。** — draft-11 §13.4、Netflix Passport
7. **Txn-Token は `Txn-Token` ヘッダーで送り、`Authorization` は使わない。AT や認証クレデンシャルとして流用しない。** — draft-11 §12, §13.12–13.13
8. **ゲートウェイは、クライアントが送った ID 系ヘッダーを必ず除去するか上書きしてから、検証済みのクレームを出力する。** — Istio `outputClaimToHeaders`（上書き）、Envoy ext_authz の注意書き
9. **発行時フックには安定した属性だけを入れる。フックが失敗したらクレームが付かないことを前提に、RS は fail-closed にする。** — Okta inline hooks（3 秒、リトライなし、元のトークンで続行）
10. **発行時フックのペイロードには上限がある前提で設計する（Entra は合計 3KB、String と String 配列のみ）。大きな権限表はトークンに入れず PDP に問い合わせる。** — Entra custom claims provider reference
11. **リフレッシュでクレームが再計算されるかを IdP ごとに確認し、再計算されない場合は AT を短命にする。** — Auth0 post-login（RT 交換時に実行）、Cognito `TokenGeneration_RefreshTokens`、Entra RT のドキュメント
12. **公開クライアントの RT は sender-constrained にするか、ローテーション＋再利用検知を入れる。** — RFC 9700 §2.2.2, §4.14.2、Auth0 のローテーション
13. **FAPI 対象の機密クライアントでは RT のローテーションを使わない。クライアント種別ごとにポリシーを分ける。** — FAPI 2.0 §5.3.2.1 NOTE 1
14. **AT は短命（分〜時間）にし、長期の grant は RT で扱う。AT の有効期限を当てにした実装をしない。** — FAPI 2.0 §6.1、OAuth 2.1 draft-17 §1.4/§3.2.3
15. **セッションと再認証のタイムアウトは AAL に合わせる（AAL2 は 24h/1h、AAL3 は 12h/15m）。** — NIST SP 800-63B-4 §2.2.3, §2.3.3
16. **時刻ずれの許容は数分以内に固定する。未来の `iat`/`nbf` は 10 秒まで許容し、60 秒を超えたら拒否する（FAPI）。** — RFC 7519 §4.1.4、FAPI 2.0 §5.3.2.1
17. **長時間ジョブや非同期処理には長命のユーザートークンを持たせない。ワークロード ID で短命トークンを作り直し、その都度 AS に可否を判断させる。** — draft-11 §6、Keycloak token exchange の RT 警告、ID-JAG §4.4.4（RT を出さない）
18. **キューやイベントにはクレデンシャルを入れず、主体の間接参照と `txn` だけを入れる。** — CloudEvents Auth Context（authclaims MUST NOT、authid に PII を入れない）
19. **非同期配送はワークロード ID で認証し、受信側は `aud` に加えて期待するサービスアカウントも検証する。** — Google Pub/Sub push authentication
20. **失効は CAEP/SSF で伝播し、`txn` で原因を相関させる。** — CAEP 1.0、SSF 1.0 §4.1.9
21. **アクセス元の文脈（IP、ネットワーク）は「認証時の値」と分かる名前で入れる。認可には PEP がリクエスト時に取得した値を使う。** — Entra `ipaddr` の定義、AWS FAS（VPC 系のキーは引き継がれない）、NIST SP 800-207 §3
22. **step-up はトークンのクレームではなく RS 側の判断で起動する（`acr`/`max_age`/`auth_time` を見る）。** — RFC 9470、Entra `acrs`/`xms_cc`
23. **人による承認は CIBA と RAR で取得し、承認内容を audience ごとにフィルタして `authorization_details` に入れる。エージェント自身に承認の有無を判断させない。** — RFC 9396 §9.1、CIBA §5、Auth0 Async Authorization
24. **エージェントにはツールごとに最小限のスコープを付け、段階的に引き上げる。ワイルドカードスコープは禁止し、昇格は相関 ID 付きでログに残す。** — MCP security best practices（Scope Minimization）
25. **委任の深さとルートからの一括失効は自前のポリシーで実装する（標準はまだない）。** — RFC 8693 §4.1、draft-mishra-oauth-agent-grants-02（個人ドラフト）
26. **JWS に機微情報を入れない。どうしても必要なら派生属性値、SD-JWT、ネスト JWE（内外とも検証する）を使う。** — RFC 7519 §12、NIST SP 800-63C-4（派生属性値）、RFC 9901、RFC 8725 §3.3
27. **トークンをログ、URL、トレースに出さない。OTel では記録するヘッダーを許可リストで指定する。** — OWASP Logging Cheat Sheet、OpenTelemetry HTTP semconv、RFC 9700 §4.3.2, §4.9.3、draft-11 §15.2

補足（ルールに入れなかった観点）:
- 結果を返すときに JWT を使うのは「自己完結した、否認防止が必要な主張」だけにする。`typ` で種類を区別し、AT と混同させない（RFC 9701、RFC 8725 §3.11–3.12）。本文の保護には RFC 9421 を使う。
- 識別子は用途で使い分ける。認可には不変の ID（`oid`+`tid`）、外部にはペアワイズの `sub`、`email`/`upn` は認可に使わない（Entra のドキュメント）。

---

## 11. 未検証事項のまとめ

- Entra custom claims provider のタイムアウト値、リトライ回数、失敗時の挙動
- Auth0 Actions のタイムアウト値
- Okta token inline hook が refresh_token グラントで呼ばれるか
- Entra でリフレッシュ時に custom claims やグループが再評価されるか
- Keycloak の protocol mapper がリフレッシュ時に再実行されるかについての公式記述
- AgentCore のワークロードアクセストークンの API 名と中身
- Google Agent Identity の提供段階（Preview/GA）
- NIST SP 800-207 §2.1 の原則の逐語（PE/PA/PEP の §3 部分は取得済み）
- RFC 10017 の BFF やブラウザ保存に関する個別推奨の逐語
- OIDC Core の署名付き UserInfo（§5.3.2）と offline_access（§11）の本文（今回は取得していない）
- SD-JWT VC ドラフトの最新番号
- Entra の `deviceid` クレーム、Okta の文脈クレーム
- Kong と Apigee のヘッダー付与の設定
- Netflix の社内 mTLS
- OAuth WG の 2026-06 再チャーター（個人ドラフトの記述からの孫引き）
