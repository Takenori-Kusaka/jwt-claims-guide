# 02. IdP別 JWT クレーム調査ノート（Entra ID / Keycloak / Auth0・Okta / Amazon Cognito）

- 調査日: 2026-11-17
- 方針: 各ベンダー公式ドキュメントを取得して確認した内容のみ記載。取得ページで確認できなかった点は **[未検証]** と明記。
- 参照バージョン/日付:
  - Microsoft Learn: 2026-11 時点の公開版（Entra Agent ID 系ページは "Last updated 2026-04-08" 表示）
  - Keycloak: `docs/latest` = 26.8.0（2026-10 リリース告知 https://www.keycloak.org/2026/10/keycloak-2680-released ）
  - Auth0 / Okta: 2026-11 時点の公開版（Auth0 docs はバージョン表記なし）
  - Amazon Cognito: Developer Guide 2026-11 時点（What's new に 2026-11-12 付の更新あり）
- 凡例: AT = access token, IDT = ID token, RT = refresh token, AS = authorization server

---

## 0. 最近の主な変更（要フラグ）

| 日付 | IdP | 変更 | 出典 |
|---|---|---|---|
| 2026-11-12 | Cognito | **OAuth 2.0 Token Exchange (RFC 8693) 追加**（Essentials/Plus）。下流サービス向けにスコープを絞った単一 audience のトークンを発行。actor token 付きで `act` クレーム | https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-whats-new.html , https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-token-exchange.html |
| 2025-10-27 | Cognito | **Resource indicators (RFC 8707)**。`resource` パラメータで要求すると AT に `aud` が入る | 同 What's new |
| 2025-10-13 | Cognito | jwks.json 取得に 50,000 req/s/アカウント/リージョンのクォータ（非調整）。JWKS をキャッシュせよ | 同 What's new |
| 2025-03-03 | Cognito | Pre token generation V3 で M2M の AT をカスタマイズ可能 | 同 What's new |
| 時期[未検証] | Cognito | `acr`/`amr` クレーム（4段階の固定 ACR レベル）。"rolling out gradually" と明記 | https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-step-up-authentication.html |
| 時期[未検証] | Cognito | issuer に ORIGINAL / UPDATED（マルチリージョン JWKS）の2種 | https://docs.aws.amazon.com/cognito/latest/developerguide/federation-endpoints.html |
| 2026-10 (26.8) | Keycloak | Token exchange **delegation** が experimental → **preview**。`delegation:client` / `delegation:user` スコープ、`may_act` 制限ポリシー | https://www.keycloak.org/2026/10/keycloak-2680-released |
| 26.7 | Keycloak | Identity Assertion JWT Grant（クロスドメイン, experimental）、AuthZen（experimental）、MCP 向け文書 | https://www.keycloak.org/docs/latest/release_notes/index.html |
| 26.5 | Keycloak | JWT Authorization Grant (RFC 7523, preview)、MCP AS 文書 | 同上, https://www.keycloak.org/2026/01/jwt-authorization-grant |
| 時期[未検証] | Auth0 | **On-Behalf-Of Token Exchange**（RFC 8693, `act` ネスト）。Custom Token Exchange とは別機能 | https://auth0.com/docs/secure/call-apis-on-users-behalf/on-behalf-of-token-exchange |
| Early Access | Auth0 | **Agent as Principal**（AT に `sub_profile`/`client_profile`/`act`、client credentials では `sub` がエージェント ID に） | https://auth0.com/docs/ai-agents-mcp/agent-as-principal/agent-identity-in-tokens |
| 時期[未検証] | Okta | **Cross App Access (XAA) / ID-JAG** | https://developer.okta.com/docs/concepts/xaa |
| 2026-04-08 更新 | Entra | **Agent ID** 用トークンクレーム（`xms_act_fct`, `xms_sub_fct` 等） | https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/agent-token-claims |

---

## 1. Microsoft Entra ID

### 1.1 トークン種別 / どれを検証するか
- AT には v1.0 / v2.0 の2形式。リソース（API）側の `requestedAccessTokenVersion`（旧 manifest では `accessTokenAcceptedVersion`）で決まり、値は `1` / `2` / `null`。**null は 1 扱い**。endpoint（v1/v2）はクライアントが選び、**ID token のバージョンにのみ影響**。個人MSAを含む signInAudience では 2 必須。
  - https://learn.microsoft.com/en-us/entra/identity-platform/reference-microsoft-graph-app-manifest
  - https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens （"when the value of requestedAccessTokenVersion is 2, a client calling the v1.0 endpoint ... receives a v2.0 access token"）
- クライアントは AT を **opaque として扱い検証しない**。検証はリソースサーバーの責務。「Microsoft API が受け取るトークンは常にデコード可能な JWT とは限らない」。
  - https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens
- **Microsoft Graph 等 Microsoft 所有 API 向けトークンは自前で検証しない**: "you can't validate tokens for Microsoft Graph according to these rules due to their proprietary format"。ページ全体が「登録済み API 向けトークンのみ」に適用と明記。他リソース向けトークンを受理するのは confused deputy。
  - https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens
- API は `aud` が自アプリに一致するトークンのみ受理。v1.0 の aud は App ID URI（例 `api://{ApplicationID}`）。
  - https://learn.microsoft.com/en-us/entra/identity-platform/claims-validation
- AT 既定寿命は 60–90 分のランダム（平均75分）。
  - https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens

### 1.2 識別子クレーム
- `sub`: 不変・再利用されないが **pairwise（アプリ ID ごとに異なる）**。同一ユーザーでも client ID が違えば別値。
- `oid`: 不変の GUID。**同一テナント内でアプリ間共通**。テナントが違えば別値。ユーザー向けには `profile` scope が必要。
- `tid`: テナント GUID。
- ガイダンス: 「ユーザー単位保存は `sub` か `oid` 単独、`tid` はルーティング/シャーディング」「サービス間共有には `oid`+`tid`」「`tid` と `oid` を複合キーに」。`idp` でテナント横断の名寄せをしない（oid/sub はテナントごとに変わる設計）。
  - https://learn.microsoft.com/en-us/entra/identity-platform/id-token-claims-reference
  - https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference
  - https://learn.microsoft.com/en-us/entra/identity-platform/claims-validation
- 可変クレームの公式警告: "**Never use claims like email, preferred_username or unique_name** to store or determine whether the user ... should have access"、"Also don't use the **upn** claim for authorization ... it often changes"。`preferred_username` と `name` は mutable、表示用のみ。
  - https://learn.microsoft.com/en-us/entra/identity-platform/claims-validation
  - https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference
- `sub` は issuer（テナント）の文脈で解釈: 同じ sub でも iss が違えば別ユーザー。
  - https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens

### 1.3 aud / iss / マルチテナント
- マルチテナント用 tenant-independent メタデータ（common / organizations）の issuer は **`{tenantid}` を含むテンプレート**。トークンの iss と完全一致比較ではなく、`{tenantid}` を当該リクエストの対象テナント ID（トークンの `tid`）に置換してから完全一致を確認。`tid` が GUID であること、iss が `.../{tid}/...` 形式であることを検証。
- 署名キーの issuer 検証: メタデータ内のキーに付く `issuer` プロパティも確認（kid→キー→issuer の信頼チェーン）。
- `tid` をユーザーデータアクセスのキーの一部に含めよ。
  - https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens
- 「tid が保存データのテナントと一致するか必ず確認。テナント間アクセスを許すな」。
  - https://learn.microsoft.com/en-us/entra/identity-platform/claims-validation
- v1 iss = `https://sts.windows.net/{tid}/`、v2 iss = `https://login.microsoftonline.com/{tid}/v2.0` **[未検証: 今回取得チャンクでは URL 部分が欠落]**

### 1.4 認可クレーム
- `scp`: アプリが公開し、クライアントが同意を得たスコープ（空白区切り）。**ユーザートークンのみ**。事前承認スコープを含み得る。
- `roles`, `groups`, `wids`: 認可に使えるが「網羅的な認可手段ではない」。
  - https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference
- `roles` = アプリケーション許可/アプリロール、`wids` = テナント全体ディレクトリロール、という一般的説明は **[未検証: 今回取得チャンクで定義文を確認できず]**。Agent ID 自律フローでは `roles` が付与権限、委任では `scp`（1.9参照）。
- `groups`: manifest `groupMembershipClaims`（null / SecurityGroup / All）。
- **Groups overage**: JWT **200**、SAML **150**（ネスト含む）を超えると `groups` を出さず `_claim_names` / `_claim_sources` を出す。返る URL は Azure AD Graph（graph.windows.net）なので頼らず、`idtyp` で app/app+user を判定して Microsoft Graph URL を組み立てよ。`hasgroups`（常に true）もある。
  - https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference
  - https://learn.microsoft.com/en-us/entra/identity-platform/optional-claims
- 大規模組織には "Groups assigned to the application" を推奨（上限対策）。
  - https://learn.microsoft.com/en-us/entra/identity-platform/optional-claims
- implicit flow の上限 6: **[未検証]**（learn.microsoft.com の Q&A 回答にのみ記載を確認。公式ドキュメント本文では未確認） https://learn.microsoft.com/en-ca/answers/questions/5835705/limits-on-ms-graph-groups

### 1.5 認証コンテキスト
- `acr`: "0 or 1, **only present in v1.0 tokens**"。
- `amr`: 認証方法の配列。v1.0 basic claims 表に掲載（v2.0 では既定で出ず optional claim で要求）。
- `acrs`: Auth Context ID の配列。step-up の契機に使用、`xms_cc` と併用。
- `xms_cc`: クライアントが claims challenge を扱えるか。**`cp1` が唯一の既知値**で、AT 内の `cp1` が権威ある判定。**リソース側（API）が optional claim として要求**しないと出ない。
  - https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference
  - https://learn.microsoft.com/en-us/entra/identity-platform/claims-challenge
- `azpacr`（v2）/`appidacr`（v1）: クライアント認証方式 0=public, 1=secret, 2=証明書。
- Claims challenge: HTTP 401 + `WWW-Authenticate: Bearer ... error="insufficient_claims", claims="<base64>"`。
  - https://learn.microsoft.com/en-us/entra/identity-platform/claims-challenge
- CAE: CAE セッションの AT は最大 **28 時間**、トークン寿命ポリシーは無視される。期限前でもリソースが拒否し得る。
  - https://learn.microsoft.com/en-us/entra/identity/conditional-access/concept-continuous-access-evaluation
- `auth_time` の Entra AT での扱い: **[未検証]**

### 1.6 サイズ
- groups 上限は「HTTP ヘッダーサイズ上限内に収めるため」。
  - https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference

### 1.7 署名キー
- `jwks_uri` から取得、ヘッダー `kid` で選択。v1 は `x5t` と `kid`、v2 は `kid` のみ → **`kid` を使え**。
- claims-mapping でカスタム署名キーがある場合、メタデータ URL に **`appid` クエリパラメータ**を付けアプリ固有 jwks_uri を使う。
  - https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens
- キャッシュ: kid 単位で個別キャッシュ、TTL 24h、1時間ごと更新、未知 kid 受信時に動的更新（最短5分間隔）。10–1000 キーを保持できること。
  - https://learn.microsoft.com/en-us/entra/identity-platform/signing-key-rollover

### 1.8 OBO
- `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer`, `requested_token_use=on_behalf_of`, `assertion`=中間層 API が受けた AT。**assertion の aud は OBO を行うアプリ自身**でなければならず、Graph 向けトークンを中間層が OBO で引き換えることは不可（拒否せよ）。
- 下流で claims challenge が出たら中間層は 401 + WWW-Authenticate でクライアントへ返す。
  - https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-on-behalf-of-flow
- OBO 後のトークンでどのクレームが変わるか（aud/azp/scp が下流向けになる等）の明文: **[未検証]**

### 1.9 AI エージェント: Microsoft Entra Agent ID
- 識別クレーム: `xms_act_fct`（actor facets, `azp`/`appid` について）、`xms_sub_fct`（subject facets）、`xms_tnt_fct`、`xms_par_app_azp`（authorized party の親アプリ）、`idtyp`、`xms_idrel`。
- シナリオ別:
  - OBO（対話型エージェント）: `idtyp=user`、`oid`=人間ユーザー、`azp/appid`=エージェント identity、`scp`、`xms_act_fct=11`
  - 自律（app-only）: `idtyp=app`、`xms_idrel=7`、`roles`、`oid`=エージェント identity、`xms_act_fct=11`、`xms_sub_fct=11`
  - エージェントのユーザーアカウント: `idtyp=user`、`xms_idrel=1`、`oid`=エージェントのユーザーアカウント、`xms_act_fct=11`、`xms_sub_fct=13`
- エージェント OBO では incoming token の aud が **agent identity blueprint**（通常 OBO の「aud=client ID」規則と異なる）。
- エージェントを作る「プラットフォーム」側には特別なクレームは付かない。
  - https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/agent-token-claims
  - https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/agent-tokens （Last updated 2026-04-08）
- プレビュー/GA ステータス: **[未検証]**

---

## 2. Keycloak（26.8.0 / docs latest）

### 2.1 トークン種別
- AT / IDT / RT を発行。**Lightweight access token** があり、フルクレームが必要なら token exchange で通常 AT に変換（その際 audience mapper の "Add to lightweight access token" を ON、対象 client が aud に必要）。
  - https://www.keycloak.org/docs/latest/server_admin/index.html
- AT が既定で JWT であること: **[未検証: 今回の取得範囲で明文未確認。一般には JWT]**

### 2.2 識別子
- `sub` はユーザー ID（例示値は UUID 形式 `0fa1e5d4-...`）。https://www.keycloak.org/securing-apps/token-exchange
- `sub` の不変性・`preferred_username`/`email` の可変性に関する公式警告: **[未検証]**

### 2.3 aud / iss
- **aud は自動では API を含まない**。方法:
  - Audience protocol mapper（Included Client Audience / Included Custom Audience）を client scope に設定（例: `service2-scope` に Audience mapper）。
  - 既定 client scope `roles` の **Audience Resolve** mapper: トークン内に client role がある client の client ID を aud に追加。
  - 無効化/削除された client は aud に追加されず、その client role も `resource_access` に出ない。
  - https://www.keycloak.org/docs/latest/server_admin/index.html
- iss 形式 `https://<host>/realms/<realm>`: **[未検証]**

### 2.4 認可クレーム
- realm role → `realm_access`（`.roles`）、client role → `resource_access`（`.<client>.roles`）が既定。入るロールは「ユーザーに割当」∩「client の role scope mapping」。
  - https://www.keycloak.org/docs/latest/server_admin/index.html
- `scope` クレーム、Group Membership mapper による `groups`（full path 設定等）: **[未検証: 今回取得できず]**

### 2.5 認証コンテキスト
- `acr`: 既定 realm client scope `acr` の "acr loa level" mapper が付与。`claims` パラメータで acr を essential 要求した場合、満たせなければエラー。
  - https://www.keycloak.org/docs/latest/server_admin/index.html
- `amr` mapper、`auth_time`: **[未検証]**

### 2.6 サイズ
- 公式の token サイズ上限記述: **[未検証]**。lightweight AT がサイズ削減手段。

### 2.7 署名キー
- realm ごとに active キーペアは1つ、passive キーは検証用に複数可。ローテーション: 高優先度の新キーを作成 → 旧キーを passive → 後に disable。
  - https://www.keycloak.org/docs/latest/server_admin/index.html
- JWKS: `/realms/{realm}/protocol/openid-connect/certs` **[未検証]**

### 2.8 Token exchange
- **Standard token exchange V2**: 完全サポート、**既定で有効**。対応は internal-to-internal（use-case 1）のみ。リクエスタ client は subject token の aud に含まれる必要。
- **Legacy V1**: preview かつ deprecated、既定無効、将来削除。
- External-to-internal は V2 + JWT Authorization Grant で、impersonation は未実装。
- **Delegation**（26.8 で preview、`--features=preview` または `--features=token-exchange-delegation`）: 結果トークンは transient session（AT のみ、RT なし）。aud とスコープは **actor client の設定から**解決（元 subject token からではない）。`act`: `{"sub": "...", "client_id": "actor-app"}`。`delegation:client` は actor client を subject token の aud に自動追加、`delegation:user` は追加しない。
  - https://www.keycloak.org/securing-apps/token-exchange
  - https://www.keycloak.org/2026/10/keycloak-2680-released （delegation:client 委任トークンは service account があっても Admin API 権限を与えない、standard token exchange は委任クレーム付き subject token を拒否、`may_act` 制限 executor）

### 2.9 AI エージェント
- 26.5: MCP サーバー向け AS としての文書、JWT Authorization Grant (preview)。26.7: "Authorize AI tools and MCP servers"、Identity Assertion JWT Grant (experimental)。26.8: AI エージェント向け delegation（consent・FGAP・監査）。
  - https://www.keycloak.org/docs/latest/release_notes/index.html , https://www.keycloak.org/2026/10/keycloak-2680-released
- JWT Authorization Grant の次ステップとして「次リリースで full support へ」「Token Exchange V1 を deprecate」（2026-01 ブログ時点の計画）。
  - https://www.keycloak.org/2026/01/jwt-authorization-grant

---

## 3. Auth0

### 3.1 トークン種別 / audience
- `audience` パラメータなし（/userinfo 用）→ **opaque AT**。自前 API には **API Identifier を audience に指定**すると JWT AT。
- audience=自前 API + `openid` scope → aud は配列（自前 API と /userinfo）。複数 aud はこの組合せのみ。
  - https://auth0.com/docs/secure/tokens/access-tokens/get-access-tokens
- AT プロファイル: Auth0 profile（`typ: JWT`、`azp`、`gty`）と RFC 9068 profile（`typ: at+jwt`、`client_id`、`jti`）。
  - https://auth0.com/docs/secure/tokens/access-tokens/access-token-profiles

### 3.2 識別子
- `user_id`（= `sub`）は **テナント内で一意**、形式 `{identity provider id}|{unique id in the provider}`（例 `facebook|1234567890`）。テナント間で同一とは限らない。DB 接続間の衝突に注意（接続プレフィックス推奨）。
  - https://auth0.com/docs/manage-users/user-accounts/identify-users
- email を自然キーにする場合の注意: ページ説明に "or by a natural key like email" とあるが、詳細警告は **[未検証]**。

### 3.3 認可クレーム / カスタムクレーム規則（現行）
- RBAC 有効 + **"Add Permissions in the Access Token"** で `permissions` クレーム。dialect は `access_token`→`access_token_authz`（RFC 9068 は `rfc9068_profile_authz`）。サイズ増に注意。
  - https://auth0.com/docs/get-started/apis/enable-role-based-access-control-for-apis
- カスタムクレーム（現行ルール）:
  - **namespaced / non-namespaced とも許可**（namespaced を推奨）。衝突時はトランザクションは失敗せず**クレームが黙って追加されない**。
  - payload 上限 **100KB**。
  - OIDC 標準クレームと Auth0 内部クレームは変更不可。
  - **Auth0 API audience を持つ AT（/userinfo 除く）は private な non-namespaced クレーム不可**。
  - AT に追加できる OIDC プロフィールクレームは指定されたもののみ。
  - 制限対象名の例: `acr, act, amr, aud, auth_time, azp, client_id, cnf, exp, groups, gty, iat, iss, jti, may_act, nbf, nonce, org_id, org_name, permissions, roles, sid, sub ...`（**`roles`/`groups`/`permissions` は素の名前で追加不可**）。
  - namespace に使えない: `auth0.com`, `webtask.io`, `webtask.run`、URN `urn:auth0`。
  - https://auth0.com/docs/secure/tokens/json-web-tokens/create-custom-claims
- Actions（post-login）でクレーム追加: 同ページが前提とする **[未検証: API 名 `api.accessToken.setCustomClaim` は今回未取得]**

### 3.4 認証コンテキスト
- Step-up: API には高価値 scope を要求し MFA を Action で強制、web app は ID token を確認。
  - https://auth0.com/docs/secure/multi-factor-authentication/step-up-authentication
- `amr`（`mfa` 値）/`acr` の具体値: **[未検証]**（`acr`/`amr` はカスタム不可の制限名には含まれる）

### 3.5 サイズ
- カスタムクレーム 100KB 上限、permissions 追加でトークン肥大。

### 3.6 署名キー
- テナント JWKS: `https://{yourDomain}/.well-known/jwks.json`（URL 部はチャンクで欠落、パス表記 **[未検証]**）。署名は1キーずつだが JWKS は複数キーを想定せよ。
- JWKS を 5–10 分キャッシュ、**未知 kid で無効化・再取得**。Currently used / Previously used / Next in queue。
  - https://auth0.com/docs/secure/tokens/json-web-tokens/json-web-key-sets
  - https://auth0.com/docs/get-started/tenant-settings/signing-keys

### 3.7 Token exchange
- **On-Behalf-Of Token Exchange**（RFC 8693, `grant_type=urn:ietf:params:oauth:grant-type:token-exchange`, subject/requested token type = access_token）: `sub` 維持、`aud` 下流 API、`azp`/`client_id` = 交換した client、`act` に委任チェーン（外側が現在の actor）。`org_id` 維持。深さ超過エラー例 "exceeds the maximum allowed limit of 4"。
  - https://auth0.com/docs/secure/call-apis-on-users-behalf/on-behalf-of-token-exchange
  - https://auth0.com/docs/api/authentication/on-behalf-of-token-exchange/get-token
- **Custom Token Exchange**: Action で任意形式の subject token を自前検証しユーザーを設定。B2C/B2B Professional・Enterprise。**検証を自分で厳密に行わないとなりすまし**。自社サービス間の委任伝播だけなら OBO を使えと明記。
  - https://auth0.com/docs/authenticate/custom-token-exchange

### 3.8 AI エージェント（Auth0 for AI Agents）
- **Token Vault**: 外部プロバイダ（Google, GitHub, Microsoft 等）のトークンを保管。refresh token exchange / access token exchange / privileged worker token exchange で取り出す。
  - https://auth0.com/ai/docs/intro/token-vault
- **Asynchronous Authorization**: CIBA + RAR。既定・推奨は Guardian push、email は明示有効化（有料アドオン）。
  - https://auth0.com/ai/docs/intro/asynchronous-authorization
- **Agent as Principal（Early Access）**: AT のみに `sub_profile`、`client_profile`（例 `service ai_agent`）、`act`。token exchange/通常ログインではエージェントは `act`、client credentials ではエージェントが `sub`。最大深さ 5 hops / ネスト `act` 4 レベル。エージェント ID は `external_agent_id` があればそれ、なければ `agent_id`。
  - https://auth0.com/docs/ai-agents-mcp/agent-as-principal/agent-identity-in-tokens
  - https://auth0.com/docs/ai-agents-mcp/agent-as-principal/associate-agent-client
  - https://auth0.com/docs/secure/tokens/access-tokens/access-token-profiles

---

## 4. Okta

### 4.1 トークン種別 / Org AS vs Custom AS
- **Org AS の AT は Okta のみが消費・検証する前提。自前 API で検証してはならない**（内容は予告なく変わる、opaque 扱い）。Org AS の audience/claims/scopes はカスタマイズ不可。Okta API scope を持つ AT は Org AS のみ発行。
- 自前 API 保護・トークン自前検証には **Custom AS**（API Access Management）。
  - https://developer.okta.com/docs/concepts/auth-servers/
  - https://developer.okta.com/docs/guides/validate-access-tokens/dotnet/main/
- リソースサーバーは **AT のみ受理、IDT で認可しない**。IDT の aud は client_id。
  - https://developer.okta.com/docs/guides/validate-access-tokens/dotnet/main/

### 4.2 識別子
- AT: `uid` = ユーザーの一意 ID（ユーザー非紐付けなら無し）、`cid` = client ID。**AT の `sub` はログイン名（例 `user@example.com`）**、IDT の `sub` は Okta ユーザー ID（`00u...`）。
  - https://developer.okta.com/docs/reference/api/oidc/
  - https://developer.okta.com/docs/guides/set-up-token-exchange/main/ （AT 例: `"uid":"00u930...","sub":"user@example.com"`）
  - https://developer.okta.com/docs/guides/customize-tokens-static/main （IDT 例 `sub: 00uixa...`）
- ログイン名変更時の扱いに関する公式警告: **[未検証]**（実装上は `uid` / IDT `sub` をキーにすべき、は推論）

### 4.3 aud / iss
- Custom AS の aud は AS に設定した audience（例 `api://default`、`com.api.atko`）。
  - https://developer.okta.com/docs/guides/set-up-token-exchange/main/ , https://developer.okta.com/docs/guides/oie-embedded-common-refresh-tokens/main

### 4.4 認可クレーム
- `scp`: 付与スコープの**配列**（Entra は空白区切り文字列）。
- `groups`: アプリの group filter に一致するグループ。**上限 100、超過時はリクエストが失敗**（Entra の overage と挙動が違う）。
- Org AS ではカスタム groups クレームのみ、Custom AS は任意クレーム/スコープ可。
  - https://developer.okta.com/docs/reference/api/oidc/
  - https://developer.okta.com/docs/guides/customize-tokens-groups-claim/main/

### 4.5 認証コンテキスト
- IDT base claims に `amr`（例 `pwd, mfa, otp, kba, sms, swk, hwk`）、`auth_time`。AT にも `auth_time`、`acr`（保証レベル）。
  - https://developer.okta.com/docs/reference/api/oidc/
- acr の具体値（`urn:okta:loa:...` 等）: **[未検証]**

### 4.6 サイズ
- groups 100 上限で失敗。その他サイズ上限: **[未検証]**

### 4.7 署名キー
- 自動ローテーション（現行**年4回**、予告なく変更あり）。新キーは数週間前に公開。**公開鍵をハードコードするな**、jwks_uri の Cache-Control に従いキャッシュ。Custom AS は AS 単位、Org AS は client 単位でロールオーバー設定。Manual に切替可。
  - https://developer.okta.com/docs/concepts/key-rotation/

### 4.8 Token exchange
- **OAuth 2.0 On-Behalf-Of Token Exchange**（RFC 8693 grant）: `subject_token_type=...access_token`、`audience`、`scope`。結果 AT の aud は Custom AS の audience。同一テナント内の別 AS 間は "trusted server" 設定。
  - https://developer.okta.com/docs/guides/set-up-token-exchange/main/
- **Cross App Access (XAA)**: ID-JAG（Identity Assertion JWT Authorization Grant）による。ユーザーの ID token（または RT）→ Org AS で ID-JAG → リソース側 AS（Custom AS）で JWT Authorization Grant として scoped AT。要求側アプリは Okta 上で **AI agent として登録**。Identity Engine。
  - https://developer.okta.com/docs/concepts/xaa
  - https://developer.okta.com/docs/guides/xaa-request-token-ex/main
  - https://developer.okta.com/docs/guides/ai-agent-secure-third-party/main
  - https://developer.okta.com/docs/guides/ai-agent-third-party-token-exchange/main

### 4.9 AI エージェント
- 上記 XAA / imported AI agents ガイド。"Auth for GenAI" という製品名の現行ドキュメント: **[未検証]**（Auth0 側は "Auth0 for AI Agents"）。

---

## 5. Amazon Cognito（User Pools）

### 5.1 トークン種別 / どれを受理するか
- IDT / AT / RT（JWT は IDT と AT）。**`token_use` を必ず確認**: API で AT のみ受理なら `access`、IDT のみなら `id`。
- **IDT の `aud` と AT の `client_id`** がアプリクライアント ID に一致すること。
- 署名と exp だけでは失効（サインアウト、RevokeToken）を検出できない。
  - https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-verifying-a-jwt.html
- M2M AT は `username`、`cognito:groups`、`device_key`、`origin_jti` を含まない（RT も発行されない）。
  - https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-the-access-token.html

### 5.2 識別子
- `sub` が**ユーザー識別の最良手段**。`username` はプール内で一意とは限らない。sub は Cognito 独自形式で RFC UUID 準拠ではない → **形式を厳密検証するな**。
  - https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-the-access-token.html
- IDT は `cognito:username`、AT は `username`。
  - https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-the-id-token.html
- 属性の mutable/immutable は設定次第（immutable は作成時のみ書込可）。
  - https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-attributes.html

### 5.3 aud / iss
- **AT には既定で `aud` が無く `client_id`**。ただし 2025-10 以降、`resource` パラメータ（RFC 8707）で要求すると AT に `aud`（Essentials/Plus, managed login）。
  - https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-whats-new.html
- iss は user pool を表す（`https://cognito-idp.<Region>.amazonaws.com/<userPoolId>` 形式。例 `us-east-1_EXAMPLE`）。ORIGINAL / UPDATED（推奨、マルチリージョンで同一 JWKS）の issuer 種別あり。UPDATED は ALB の `authenticate-cognito` と非互換。UPDATED の正確な URL 形式: **[未検証: チャンクで欠落]**
  - https://docs.aws.amazon.com/cognito/latest/developerguide/federation-endpoints.html
  - https://docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/API_IssuerConfigurationType.html

### 5.4 認可クレーム
- `cognito:groups`（配列、要素1つでも配列）、`cognito:roles`（IAM ロール ARN 配列）、`cognito:preferred_role`（文字列）。AT には `scope`（空白区切り）。
  - https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-the-id-token.html
  - https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-the-access-token.html
- カスタム属性: コード上 **`custom:` プレフィックス**必須。最大50、値最大2048文字。**追加後は削除・改名・型/可変性変更不可**。
  - https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-attributes.html
- **Pre token generation trigger**:
  - V1_0: IDT のみカスタマイズ（Basic）
  - V2_0: AT もカスタマイズ（ユーザー）— Essentials/Plus
  - V3_0: ユーザー + **M2M（client credentials と GetClientToken API）** の AT — Essentials/Plus、M2M は別料金
  - 既定は V1_0 イベント。2024-11-22 以前に高度セキュリティ有効だった Lite プールは V1/V2 可。
  - 変更不可: `sub`, `cognito:username`, `username`, `client_id`, `aud`, `identities`, `event_id`, 他の `cognito:` プレフィックス。変更可: `scope`（scopesToAdd/Suppress, V2/V3）, `cognito:groups`（groupsToOverride）, `cognito:roles`, `cognito:preferred_role`, 標準 OIDC 属性, `custom:` 属性, スキーマ外の任意クレーム。`dev:` は抑止のみ。
  - https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-pre-token-generation.html

### 5.5 認証コンテキスト
- `auth_time` は IDT/AT に含まれる（例示）。
- **`acr`/`amr`**: 固定4レベル（Level1–4）、名前のみ `AcrConfiguration` でカスタマイズ（Essentials/Plus）。IDT/AT に付与、refresh 後も維持。**Pre token generation で変更不可**。NIST/eIDAS への対応付けはアプリ責務。**段階的ロールアウト中で未提供のプールあり**。
  - https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-step-up-authentication.html
  - https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-the-id-token.html

### 5.6 サイズ
- Pre token generation の「既存+追加クレーム+スコープ」合計クォータ **5,000**（調整可、抑止分は除外）。
  - https://docs.aws.amazon.com/cognito/latest/developerguide/quotas.html
- トークンサイズは可変（クレーム追加、アルゴリズム変更、失効有効化で `origin_jti`/`jti` 追加）→ アプリは可変長を保存できること。
  - https://docs.aws.amazon.com/pdfs/cognito/latest/developerguide/cognito-dg.pdf （"Storing tokens"）
- ユーザーあたりグループ所属上限 100。同上 quotas
- バイト単位のトークン最大長: **[未検証]**

### 5.7 署名キー
- `https://cognito-idp.<Region>.amazonaws.com/<userPoolId>/.well-known/jwks.json`、RS256。キーはローテーションされ得る → kid をキーにキャッシュ、正しい iss で未知 kid なら再取得。jwks.json は 50,000 req/s クォータ（2025-10）。
  - https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-verifying-a-jwt.html
  - https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-whats-new.html

### 5.8 委任 / Token exchange
- M2M: client credentials（resource server のカスタム scope）。
  - https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-define-resource-servers.html
- **Token exchange（2026-11-12 新機能, Essentials/Plus）**: `grant_type=urn:ietf:params:oauth:grant-type:token-exchange`、subject token、resource server、down-scope。**RT は発行しない**。単一 audience・単一 resource にバインド（登録 resource server で検証）。subject token の署名・期限・失効を検証、ユーザーは enabled/confirmed 必須。actor token 無し = ユーザー本人扱い（`act` 無し、区別不能）、有り = `act`（identity claims のみ）。**`may_act` は発行も評価もしない**。外部 IdP トークン用に `subject_token_provider_name`/`actor_token_provider_name`（Cognito 独自拡張）。API は `GetDerivedToken`。
  - https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-token-exchange.html
  - https://docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/API_GetDerivedToken.html

### 5.9 AI エージェント: Amazon Bedrock AgentCore Identity
- エージェント identity は workload identity として実装、ディレクトリで集中管理。Token vault に OAuth トークン/クライアント資格情報/API キーを KMS 暗号化で保管、ワークロード identity の証明提示時のみ取得可。
  - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity.html
  - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/key-features-and-benefits.html
- Inbound JWT authorizer: allowed audiences / **allowed clients（`client_id` クレームと照合）** / allowed scopes / required custom claims（STRING は EQUALS、STRING_ARRAY は CONTAINS/CONTAINS_ANY）。最低1つ必須、複数なら全て検証。
  - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/inbound-jwt-authorizer.html
- Outbound: OAuth credential provider でユーザー委任/M2M トークンを取得し vault 保存、RT で自動更新。On-behalf-of token exchange は RFC 8693 または RFC 7523 §2.1 方式の IdP をサポート。
  - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity-authentication.html
  - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/on-behalf-of-token-exchange.html

---

## 6. 横断比較表

| 項目 | Entra ID | Keycloak | Auth0 / Okta | Cognito |
|---|---|---|---|---|
| 安定ユーザーキー | `oid`+`tid`（`sub` はアプリ毎 pairwise） | `sub`（ユーザー ID）[不変性の明文は未検証] | Auth0: `sub`=`user_id`（`provider\|id`, テナント内一意）/ Okta: AT は `uid`（AT の `sub` はログイン名）、IDT `sub` | `sub`（`username` は一意でない、sub 形式を厳密検証しない） |
| テナントクレーム | `tid`（iss と突合必須） | なし（realm は iss パス）[未検証] | Auth0: `org_id`（Organizations）/ Okta: なし（org = iss） | なし（user pool は iss） |
| AT の aud | API の App ID URI(v1) / client ID(v2)。Graph 向けは検証不可 | 既定では API 不在。Audience mapper / Audience Resolve で付与 | Auth0: `audience`=API Identifier（無指定は opaque）/ Okta: Custom AS の audience（Org AS AT は検証不可） | 既定 aud 無し・`client_id`。`resource` 指定時のみ `aud`（2025-10〜） |
| roles/groups の位置 | `roles`, `scp`, `groups`, `wids` | `realm_access.roles`, `resource_access.<client>.roles`, groups mapper[未検証] | Auth0: `permissions`（RBAC トグル）、roles は namespaced で自作 / Okta: `groups`, `scp`(配列) | `cognito:groups`, `cognito:roles`, `scope` |
| カスタムクレーム規則 | optional claims / claims-mapping（カスタム署名キー → `appid` 付き JWKS） | protocol mapper / client scope | Auth0: non-namespaced 可だが API AT は private 非 namespaced 不可、予約名・auth0.com 系 namespace 不可、100KB / Okta: Custom AS のみ自由 | Pre token gen（V1=IDT, V2=+AT, V3=+M2M）、`custom:` 属性、変更不可クレームあり |
| acr/amr | `acr`(v1のみ 0/1), `amr`, `acrs`(auth context), `xms_cc` | `acr`（LoA mapper）, amr[未検証] | Auth0: 制限名に含む、値[未検証] / Okta: `amr`, `acr`, `auth_time` | `acr`/`amr`（4固定レベル、段階展開中、変更不可）, `auth_time` |
| Token exchange | OBO（jwt-bearer, `requested_token_use=on_behalf_of`）、Agent ID | Standard TE V2（GA, internal）、Delegation（preview, `act`）、JWT Authz Grant（preview）、ID-JAG（experimental） | Auth0: OBO TE（`act`）、Custom TE / Okta: OBO TE、XAA(ID-JAG) | RFC 8693 TE（2026-11〜, `act`, RT 無し, `may_act` 非対応） |
| 主な落とし穴 | v1/v2 混在、common の `{tenantid}`、groups overage、Graph トークン検証 | aud が自動で入らない、lightweight AT | Auth0: audience 忘れで opaque、衝突クレームが黙って消える / Okta: Org AS AT 検証、AT `sub` がメール形式 | `token_use` 未確認で IDT 受理、AT に aud 無し、custom 属性は不可逆 |

---

## 7. 取り違えやすい点（出典付き）

1. **Entra の `sub` はアプリごとに違う**。複数サービスで共有するキーは `oid`+`tid`。 https://learn.microsoft.com/en-us/entra/identity-platform/id-token-claims-reference
2. **Entra の `email`/`preferred_username`/`unique_name`/`upn` で認可しない**（upn は一意だが変わる）。 https://learn.microsoft.com/en-us/entra/identity-platform/claims-validation
3. **common/organizations の issuer は `{tenantid}` テンプレート**。文字列一致ではなく `tid` で置換し、さらに `tid` をデータキーに含める。 https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens
4. **Graph 向けトークンを自分の API で検証・受理しない**（独自形式・confused deputy）。OBO の assertion にも使えない。 https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens , https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-on-behalf-of-flow
5. **AT のバージョンは呼んだ endpoint ではなく API 側の `requestedAccessTokenVersion` で決まる**（null=v1）。v1 と v2 で iss/aud 形式が違う。 https://learn.microsoft.com/en-us/entra/identity-platform/reference-microsoft-graph-app-manifest
6. **groups が無い ≠ 所属なし**。Entra は 200(JWT)/150(SAML) 超で `_claim_names`/`_claim_sources` に置換、URL は旧 graph.windows.net なので Microsoft Graph を組み立てる。 https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference
7. **Okta の groups は 100 超でリクエスト自体が失敗**（Entra の overage と挙動が逆）。 https://developer.okta.com/docs/reference/api/oidc/
8. **`xms_cc` は API 側が optional claim を設定しないと出ない**。`cp1` が唯一の既知値。CAE トークンは最大 28h。 https://learn.microsoft.com/en-us/entra/identity-platform/claims-challenge , https://learn.microsoft.com/en-us/entra/identity/conditional-access/concept-continuous-access-evaluation
9. **Entra の `acr` は v1.0 のみで 0/1**。step-up 判定には `acrs`（auth context）を使う。 https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference
10. **Okta Org AS の AT を自前 API で検証しない**（予告なく形式変更）。Custom AS を使う。 https://developer.okta.com/docs/concepts/auth-servers/
11. **Okta AT の `sub` はログイン名（メール形式）**で IDT の `sub`（`00u...`）と違う。AT では `uid` を使う。 https://developer.okta.com/docs/guides/set-up-token-exchange/main/
12. **Auth0 で `audience` を付け忘れると AT は opaque**（/userinfo 用）。 https://auth0.com/docs/secure/tokens/access-tokens/get-access-tokens
13. **Auth0 のカスタムクレームは衝突すると黙って消える**。`roles`/`groups`/`permissions` 等は素の名前で入らない、API AT は非 namespaced の private クレーム不可、`auth0.com`/`webtask.io`/`webtask.run`/`urn:auth0` は namespace 不可。 https://auth0.com/docs/secure/tokens/json-web-tokens/create-custom-claims
14. **Auth0 の `user_id` はテナント内一意**で、テナント間で一致する保証なし。 https://auth0.com/docs/manage-users/user-accounts/identify-users
15. **Cognito AT は既定で `aud` が無い**（`client_id` を見る）。`resource` 指定時のみ aud。aud 必須のミドルウェアをそのまま使うと失敗/素通りの危険。 https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-verifying-a-jwt.html , https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-whats-new.html
16. **Cognito は `token_use` を検証しないと IDT が API に通る**。 https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-verifying-a-jwt.html
17. **Cognito の `sub` 形式を UUID として厳密検証しない**、`username` をキーにしない。 https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-the-access-token.html
18. **Cognito Pre token generation V1 では AT を変えられない**（V2/V3 は Essentials/Plus）。`sub`/`client_id`/`aud`/`acr`/`amr` は変更不可。 https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-pre-token-generation.html
19. **Keycloak の aud は自動で API を含まない**。Audience mapper か Audience Resolve（client role 起点）が必要。token exchange V2 でもリクエスタが subject token の aud に要る。 https://www.keycloak.org/docs/latest/server_admin/index.html , https://www.keycloak.org/securing-apps/token-exchange
20. **委任トークンでは `sub`=ユーザー、actor は `act`（Keycloak/Auth0/Cognito）や `azp`+`xms_act_fct`（Entra Agent ID）**。`sub` だけ見るとエージェント経由の操作を区別できない。Cognito は actor token 無しだと本人と区別不能。 https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-token-exchange.html , https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/agent-token-claims , https://auth0.com/docs/secure/call-apis-on-users-behalf/on-behalf-of-token-exchange
21. **JWKS はキャッシュ + 未知 kid で再取得**。公開鍵ハードコード禁止（Okta 年4回ローテ、Cognito jwks クォータ、Entra 24h TTL/1h 更新、Auth0 5–10 分）。 https://developer.okta.com/docs/concepts/key-rotation/ , https://learn.microsoft.com/en-us/entra/identity-platform/signing-key-rollover , https://auth0.com/docs/secure/tokens/json-web-tokens/json-web-key-sets

---

## 8. 未検証事項まとめ
- Entra: v1/v2 の iss URL 実文字列、`roles`/`wids` の定義文、implicit flow の groups 上限 6（Q&A のみ）、OBO 後のクレーム変化の明文、Agent ID の GA/preview 状態、AT の `auth_time`
- Keycloak: AT が既定 JWT である明文、`sub` 不変性の明文、iss/JWKS パス、groups mapper・amr mapper 詳細、サイズ上限
- Auth0: JWKS パス表記、Actions の API 名、`amr`/`acr` の値、OBO TE の提供開始時期・プラン、"4" と "5 hops" の数え方（エラーは「上限4」、Agent as Principal ページは「5 hops / ネスト4」）
- Okta: acr 値の形式、"Auth for GenAI" 名称の現行性、XAA の GA 状態、ログイン名変更時の AT `sub` の扱い
- Cognito: UPDATED issuer の正確な URL、トークン最大バイト長、acr/amr 提供開始日
