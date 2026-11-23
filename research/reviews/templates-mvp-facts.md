# 点検の材料：設計書テンプレートの MVP（#4）

独立の点検（`templates/CONTRIBUTING.md` の 2.・3.）に渡すための、成果物に含まれる事実の一覧と、抜き取りの対象です。**作成者の結論（正しいかどうか）は書いていません。** 点検者は、ここの一覧と一次資料を突き合わせ、結果を `research/reviews/templates-mvp-<日付>.md` に、既存と同じ区分（誤り・過大・不一致・曖昧）で記録してください。

- 作成：2026-11-23、LLM（Claude、Opus 5.5）。テンプレートの一部（profiles・modules）は同じセッションから分けた作業者（同じモデル）が書いた
- 対象：PR 1（ブランチ `issue-4-templates`）の `templates/README.md`・`GETTING_STARTED.md`・`glossary.md`・`00_core.md`・`claim_request.md`・`profiles/*.md`・`modules/*.md`、`tools/template_check.py`、`tools/claim_lint` の `--profile lite` の R1、`tools/count_lite_fields.py --current`、対応表の変更。PR 2（ブランチ `issue-4-scenario-b`）の記入例は 5. に足す
- 「確かめ方」の列：**web** は作成のときに一次資料を開いて確かめた（URL と日付つき）、**slide** はガイドのスライドの記述を写した（一次資料では確かめていない）、**repo** は本リポジトリの既存の資料（カタログ・ケーススタディの結果など）から写した、**記憶** は作成者の知識で書き、作成のときに一次資料を開いていない。**記憶** の行を優先して点検してください

## 1. 機械の検査の結果（作成のとき）

| 検査 | 結果 |
| --- | --- |
| `python tools/template_check.py` | files 15、items 142、error 0 |
| `python tools/check_slide_refs.py templates` | 0 problems |
| `python tools/trace_check.py`・`--tier core` | OK |
| `python tools/claim_lint templates/examples/scenario-a`・`--profile lite` | error 0（lite の R1 の変更の後も） |
| `python -m pytest tools/tests` | PR の CI の結果を見る |

`template_check.py` が確かめるのは、根拠の**形**（スライドの実在、RFC の節、草案の版、筆者の提案の追跡 issue）までです。その根拠が項目の主張を支えるかは、3. の抜き取りで点検します。

## 2. 事実の一覧

### 2.1 Keycloak 26.8（`modules/M_idp_keycloak.md`。#4 の改訂「Keycloak 26.8 の既定は文書で確かめる」）

文書の「latest」は 26.8.2 でした（版の選択に 26.8.2・26.7.5・26.6.4）。確かめた日はすべて 2026-11-23。

| # | 事実 | 出どころ | 確かめ方 |
| --- | --- | --- | --- |
| K1 | サーバーの機能 `token-exchange-standard:v2` は既定で有効。使うには要求元のクライアントでスイッチ「Standard token exchange」を有効にし、そのクライアントは機密クライアント | Securing Applications（26.8.2）「Standard token exchange」 https://www.keycloak.org/securing-apps/token-exchange | web |
| K2 | クライアントのスイッチ「Standard token exchange」の既定値は、文書に書かれていない（カタログの V31 はソースの要約で OFF） | 同上、`templates/catalog/` の V31 | web・repo |
| K3 | 委任（`may_act`・`act`）は Preview で既定は無効。`--features=preview` か `--features=token-exchange-delegation` で有効 | 同上「Token exchange delegation」 | web |
| K4 | V2 では subject impersonation は「Not implemented yet」 | 同上「Comparison of standard token exchange and legacy token exchange」 | web |
| K5 | V1（legacy）は preview で非推奨、既定は無効 | 同上「Legacy token exchange」 | web |
| K6 | 交換で RT を出すのは、クライアントの「Allow refresh token in Standard Token Exchange」が No（既定）以外のときだけ。RT は subject token の期限で上限がかからず、元の期限を越えうる | 同上 | web |
| K7 | 交換の scope は要求元のクライアントの Optional のスコープを足せる。audience は aud とクライアントロールを絞るだけ | 同上 | web |
| K8 | executor `downscope-assertion-grant-enforcer` は subject_token に無いスコープを拒否する。例外は include in token scope が false の既定のスコープ（basic・acr など） | Server Administration Guide（26.8.2）「Downscoping」 https://www.keycloak.org/docs/latest/server_admin/ | web |
| K9 | offline_access のクライアントスコープは、Optional として既定でクライアントに付く。オフラインのトークンには、利用者にレルムの offline_access ロールが要る | 同上「Offline access」 | web |
| K10 | offline_access ロールが既定のロール（default-roles）に含まれるかは、文書の本文では確かめられなかった | 同上 | web（確かめられず） |
| K11 | Revoke Refresh Token を有効にすると、リフレッシュで RT を失効させ新しい RT を出す。既定値はこの節に書かれていない（「既定で無効」は slide:p08-rotation と V31） | 同上（Tokens タブの表と「Offline access」） | web・slide |
| K12 | 軽量アクセストークンは client policy の executor `use-lightweight-access-token` で有効にする。マッパーの「Add to lightweight access token」は既定でオフ | 同上「Using lightweight access token」 | web |
| K13 | 軽量アクセストークンで外せないクレームは exp・iat・jti・iss・typ・azp・sid・scope・cnf | 同上 | web |
| K14 | 軽量アクセストークンで落ちるクレームは「Add to token introspection」でイントロスペクションから得られる。UserInfo は軽量 AT を既定で拒否 | 同上 | web |
| K15 | Full Scope Allowed のスイッチは非推奨で将来消える。全クライアントで無効にするよう文書が求め、強制する executor「Full Scope Disabled」がある | 同上「Role scope mappings」 | web |
| K16 | イントロスペクションは、問い合わせたクライアントが aud に含まれるときだけ active を返す。互換の設定「Allow token introspection without audience check」で外せる。RT・オフラインのトークンは azp のクライアントだけ | 同上「Token introspection audience validation」 | web |
| K17 | Client Scopes の Evaluate タブで AT・ID トークン・UserInfo の例を作れる。audience パラメータはトークン交換でだけ使える | 同上「Evaluating Client Scopes」 | web |
| K18 | カタログの各行の `stop_setting.default`（I03・I04・I05・I07 の引き継ぎの印 `lite_inherit: true`） | `templates/catalog/issue_events.yaml` | repo |
| K19 | ケーススタディの実測（26.8.0）：軽量 AT で 12 個のクレームが落ちる、グループ 200 個で AT が 8609 B、交換で元に無い宛先が出る、交換のトークンに act なし、リフレッシュで再評価、ログアウト後のイントロスペクション、Full Scope Allowed の漏れ | jwt-claims-casestudy@080b8da の results/summary.md | repo |

### 2.2 MCP の認可（`profiles/P4_ai_agent_delegation.md` の `mcp-checklist`）

確かめた日はすべて 2026-11-23。現行版は 2026-07-28（https://modelcontextprotocol.io/specification/latest/basic/authorization）。

| # | 事実 | 出どころ | 確かめ方 |
| --- | --- | --- | --- |
| M1 | 認可要求とトークン要求の両方に resource を入れる（MUST）。AS が対応していなくても送る | MCP Authorization（2026-07-28）「Resource Parameter Implementation」 | web |
| M2 | MCP サーバーは自分宛てのトークンだけを受け入れ、ほかのトークンを受け入れも中継もしない | 同「Token Handling」 | web |
| M3 | AT はすべての要求の Authorization ヘッダーで送り、クエリに入れない | 同「Token Requirements」 | web |
| M4 | MCP サーバーは RFC 9728 を実装する（MUST） | 同「Overview」 | web |
| M5 | 認可応答の iss を RFC 9207 §2.4 で照合する（MUST）。AS が対応を宣言しているのに iss が無ければ拒否 | 同「Authorization Response Validation」 | web |
| M6 | insufficient_scope は 403 と WWW-Authenticate の scope で返す（SHOULD）。取り直しは前の scope との和 | 同「Scope Challenge Handling」「Step-Up Authorization Flow」 | web |
| M7 | STDIO の運び方では、この仕様に従わず環境から資格情報を得る | 同「Protocol Requirements」 | web |
| M8 | PKCE は MUST、S256 は技術的に可能なら MUST。`code_challenge_methods_supported` が無ければ進まない | MCP Authorization Security Considerations（2026-07-28）「Authorization Code Protection」 | web |
| M9 | 公開クライアントの RT を AS がローテーションする（MUST） | 同「Token Theft」 | web |
| M10 | 固定のクライアント ID のプロキシは、動的に登録されたクライアントごとに同意を取る（MUST） | 同「Confused Deputy Problem」 | web |
| M11 | 受け取ったトークンを上流に渡さない（MUST NOT） | 同「Access Token Privilege Restriction」 | web |

### 2.3 Transaction Token（`profiles/P5_internal_propagation.md`・`00_core.md`・`glossary.md`）

| # | 事実 | 出どころ | 確かめ方 |
| --- | --- | --- | --- |
| X1 | 最新は draft-ietf-oauth-transaction-tokens-11（2026-07-30）で、まだ Internet-Draft | https://datatracker.ietf.org/doc/draft-ietf-oauth-transaction-tokens/（2026-11-23） | web |
| X2 | 節：§6 寿命（分以下。元のトークンより長くてもよい）、§8.1・§8.2 発行の流れ、§9.1 ヘッダー（typ）、§9.2 クレーム（txn・req_wl など）、§9.2.2 rctx、§9.2.3 tctx、§10 TTS、§12.1 Txn-Token ヘッダー、§12.2 受け取ったまま渡す、§13.13 AT ではない、§13.15 作り直し、§15.2 ログ | https://www.ietf.org/archive/id/draft-ietf-oauth-transaction-tokens-11.html（2026-11-23） | web |
| X3 | 作り直しで scope の拡大と txn・sub・aud の変更は不可 | slide:p06-transaction-tokens | slide |
| X4 | 用語「Transaction Token Service（TTS）」と、用語の節 §2（`glossary.md` の `notation` が引く） | draft-ietf-oauth-transaction-tokens-11 §2 | 記憶 |

### 2.4 データ層（`modules/M_data_layer.md`・`00_core.md` の 9.1）

| # | 事実 | 出どころ | 確かめ方 |
| --- | --- | --- | --- |
| D1 | スーパーユーザーと BYPASSRLS のロールは常に RLS をすり抜ける。テーブルの所有者は通常すり抜け、`FORCE ROW LEVEL SECURITY` で対象になる。ポリシーが無ければ既定で拒否 | PostgreSQL 16 §5.8「Row Security Policies」 https://www.postgresql.org/docs/16/ddl-rowsecurity.html（2026-11-23） | web |
| D2 | `set_config` の is_local=true は現在の取引だけ、false はセッションの終わりまで。`current_setting(…, true)` は未設定なら NULL | PostgreSQL 16 §9.27.1 https://www.postgresql.org/docs/16/functions-admin.html（2026-11-23） | web |
| D3 | `sp_set_session_context` の `@read_only` は bit で既定 0。1 にすると、その論理接続ではキーを変えられない。SQL Server 2016 以降 | https://learn.microsoft.com/en-us/sql/relational-databases/system-stored-procedures/sp-set-session-context-transact-sql（ms.date 2025-06-23、2026-11-23） | web |
| D4 | Kafka の `connections.max.reauth.ms` は既定 0。正の値にすると、再認証しない接続をブローカーが切る | Kafka 4.4 Broker Configs https://kafka.apache.org/44/configuration/broker-configs/（2026-11-23） | web |
| D5 | RDS・Aurora の IAM 認証と Cloud SQL の IAM 認証は開いた接続に影響しない。Azure Database for PostgreSQL は削除した利用者も最大 60 分は入れる | slide:p07-lifetime-mismatch | slide |
| D6 | PostgREST はコミット後の値が空文字になる | slide:p07-connection-pool | slide |

### 2.5 個人情報保護法（`modules/M_privacy_minimization.md` の `appi-table`）

e-Gov 法令 API の現行の本文（https://laws.e-gov.go.jp/api/1/lawdata/415AC0000000057、2026-11-23）。

| # | 事実 | 確かめ方 |
| --- | --- | --- |
| P1 | 第 2 条：第 1 項 個人情報、第 3 項 要配慮個人情報、第 5 項 仮名加工情報、第 6 項 匿名加工情報、第 7 項 個人関連情報 | web |
| P2 | 見出し：第 17 条 利用目的の特定、第 23 条 安全管理措置、第 27 条 第三者提供の制限、第 28 条 外国にある第三者への提供の制限、第 31 条 個人関連情報の第三者提供の制限等 | web |
| P3 | どのクレームがどの区分に当たるかの解釈（`sub` を個人情報とするなど）は筆者の判断で、法の本文が直接定めるものではない | （判断。点検者は「過大」がないかを見る） |

### 2.6 作成のときに一次資料を開いていない節（記憶。優先して点検）

テンプレートの根拠に書いた次の節は、作成のときに本文を開いていません。項目の主張を支えるかを確かめてください。

- RFC 9449：§1、§4.3（proof の照合）、§5（RT を DPoP で束縛）、§6.1（`cnf.jkt`）、§7.1（DPoP の方式）、§8（AS の nonce）、§9（RS の nonce）、§11.1（proof の再送）
- RFC 8705：§1、§2、§2.1、§3、§3.1（`x5t#S256`）、§6.5（入口での TLS の終端）
- RFC 9700：§2.1.1、§2.2.1、§2.2.2、§2.3、§2.4、§4.2、§4.3.2、§4.14.2、§4.15.1
- RFC 8725：§3.1、§3.8、§3.9、§3.10、§3.11
- RFC 7519：§2、§4.1.3〜§4.1.5、§7.2、§11.2。RFC 7515：§4.1.4、§5.2。RFC 7516：§4.1.1・§4.1.2
- RFC 9068：§2.1、§2.2、§2.2.3、§2.2.3.1、§4
- RFC 8707 §2、RFC 8414 §2、RFC 9126 §1・§2、RFC 9207 §2.4、RFC 9470 §3・§4、RFC 6750 §2.1・§2.3・§3.1、RFC 7009 §2、RFC 7523 §2.2、RFC 7662 §2・§4、RFC 7800 §3.1、RFC 8693 §1.1・§2.1・§4.1・§4.4・§5、RFC 9396 §2・§2.2・§9.1、RFC 9421 §2、RFC 9728 §3
- RFC 9110 §15.5.4（存在を隠すなら 403 の代わりに 404 を返してよい）
- RFC 10017（BCP 212）の節：§5、§6、§6.1、§6.2、§6.3、§6.1.2.2、§6.1.3.2、§6.3.2.3、§8（作業者は https://www.rfc-editor.org/rfc/rfc10017.html を 2026-11-23 に開いたと報告している。番号と BCP の番号を確かめる）
- OpenID Connect Core 1.0 §3.1.2.1・§3.1.3.7・§5.1・§5.3・§9・§10.1.1、Back-Channel Logout 1.0 §2.4・§2.6、Front-Channel Logout 1.0 §3、RP-Initiated Logout 1.0 §2、CIBA Core 1.0 §5・§7.1、OAuth 2.0 Form Post Response Mode
- FAPI 2.0 Security Profile（Final）§5.3.2.1・§5.3.2.2
- NIST SP 800-162 §2・§2.4.2・§3・§3.3.3、NIST SP 800-63B-4 §2.2.3、NIST SP 800-63C-4 §3.6・§3.10・§4.11.1、NIST IR 8587 §4.1.4・§5.2.1.2・§5.3.1.1・§5.3.1.4・§5.3.1.5・§5.3.1.6・§5.3.1.7、NIST SP 800-228 REC-API-12
- OWASP API Security Top 10 2023 の API1・API5、ASVS v5.0.0-8.2.2・8.3.2・8.3.3、CoSAI Agentic IAM v1.0 §1.2・§3.4
- Zanzibar（USENIX ATC 2019）§2
- ライブラリの既定値（jsonwebtoken・golang-jwt の `WithExpirationRequired`・Microsoft.IdentityModel の署名鍵の確認が既定で無効など）は slide:p01-library-defaults の記述による

### 2.7 その他の事実（`00_core.md`・`README.md`・`claim_request.md`）

| # | 事実 | 書いた場所 | 確かめ方 |
| --- | --- | --- | --- |
| C1 | 寿命の指針：AT・ID トークンは 1 時間以内とすべき（IR 8587 §5.3.1.1）、AAL2 の再認証は 24 時間・無操作 1 時間（SP 800-63B-4）、アサーションの参照は 5 分以内（SP 800-63C-4 §4.11.1）、FAPI 2.0 の認可コードは 60 秒 | `00_core.md` の 5.1 | slide（slide:p08-choosing-lifetime・slide:p08-token-types-lifetimes） |
| C2 | 社内業務・マルチテナント SaaS・AI エージェントの委任の重点と見送りの候補 | `00_core.md` の 3.1 | slide（slide:p12-priorities-deferrals） |
| C3 | Kafka の再認証の既定は 0（無効）、ほか 3 製品の開いた接続への影響 | `00_core.md` の 9.1 | slide・web（D4） |
| C4 | 25 問の文言 | `claim_request.md` | slide（slide:p11-pre-add-questions-1・2。要件の文と同じ。問 5・14・17 は要件の文の言い回し） |
| C5 | 25 問のうち台帳から写せる 11 問と手書きの 14 問の分け方 | `claim_request.md` の 2. | repo（`examples/scenario-a/claim_request_tenant_id.md`、gate1.md の 10.） |
| C6 | 縮小 Lite の手で書く 5 節・生成する節・Full だけの節 | `README.md` | repo（gate1.md の 10.） |
| C7 | `RFC 9470 §3` が `insufficient_user_authentication` と `acr_values`・`max_age` を定める | `00_core.md` の付録 B | 記憶 |
| C8 | `RFC 9421 §2` が署名する部分（`@method`・`@path` など）を定める | `00_core.md` の付録 C | 記憶 |

## 3. 根拠の中身の抜き取り（10%、最低 10 件）

母数：テンプレートの項目 142、根拠の要素 468。乱数の種 20261123 で 47 件を選んだ（`research/reviews/` に置かない作業用のスクリプトで、`tools/template_check.py` の `template_files`・`split_evidence` を使って数えた）。各行について、その根拠が項目の主張を支えるか（支える・一部・支えない）を記録してください。

| # | 項目 | 根拠 |
| --- | --- | --- |
| 15 | `template:GETTING_STARTED#step-2-gate` | templates/README.md の「Lite と Full の判定」 |
| 23 | `template:glossary#notation` | slide:p00-terminology |
| 25 | `template:glossary#terms-basic` | slide:p00-terminology |
| 27 | `template:glossary#terms-questions` | templates/registry/questions.yaml |
| 31 | `template:glossary#terms-design-doc` | research/template-design/report.md の Q3 |
| 37 | `template:00_core#scope-boundary` | slide:p06-stage-map |
| 45 | `template:00_core#system-privileges` | slide:p05-cross-tenant |
| 51 | `template:00_core#priorities-deferrals` | slide:p12-priorities-deferrals |
| 56 | `template:00_core#issuance-profile` | templates/registry/issuance_effects.yaml |
| 81 | `template:00_core#lifecycle` | slide:p08-async-processing |
| 88 | `template:00_core#lifecycle-db-connection` | slide:p08-revocation-propagation |
| 95 | `template:00_core#definition-lifecycle` | slide:p11-change-procedure |
| 100 | `template:00_core#decisions` | slide:p11-ownership |
| 120 | `template:claim_request#gate` | slide:p11-pre-add-questions-2 |
| 139 | `template:claim_request#q05` | slide:p11-pre-add-questions-1 |
| 144 | `template:claim_request#q07` | slide:p04-type |
| 167 | `template:claim_request#q16` | slide:p11-contract-test-gaps |
| 175 | `template:claim_request#q19` | slide:p04-forward-compatibility |
| 193 | `template:profiles/P1_human_web#bff-vs-spa` | slide:p09-url-browser |
| 198 | `template:profiles/P1_human_web#url-exposure` | RFC 9126 §2 |
| 217 | `template:profiles/P4_ai_agent_delegation#agent-identity` | RFC 8693 §1.1 |
| 238 | `template:profiles/P4_ai_agent_delegation#chain-revocation` | slide:p08-revocation-propagation |
| 241 | `template:profiles/P5_internal_propagation#edge-conversion` | slide:p06-edge-exchange |
| 244 | `template:profiles/P5_internal_propagation#edge-conversion` | slide:p10-vendor-features |
| 252 | `template:profiles/P5_internal_propagation#service-to-service` | RFC 9068 §4 |
| 276 | `template:modules/M_authz_pdp#registry-map` | slide:p04-carry-or-query |
| 286 | `template:modules/M_data_layer#pool-context` | slide:p07-lifetime-mismatch |
| 289 | `template:modules/M_data_layer#db-identity` | slide:p07-db-token-auth |
| 294 | `template:modules/M_data_layer#masking-rls-bypass` | slide:p07-row-level-security |
| 334 | `template:modules/M_idp_keycloak#token-exchange-downscope` | slide:p06-narrow-downstream |
| 335 | `template:modules/M_idp_keycloak#token-exchange-downscope` | RFC 8693 §5 |
| 338 | `template:modules/M_idp_keycloak#refresh-token-settings` | slide:p08-rotation |
| 345 | `template:modules/M_idp_keycloak#limits` | slide:p03-custom-claim-injection |
| 371 | `template:modules/M_multitenancy#data-layer-filter` | jwt-claims-casestudy@080b8da:A7（裏付け） |
| 372 | `template:modules/M_multitenancy#cross-tenant` | slide:p05-cross-tenant |
| 376 | `template:modules/M_multitenancy#operator-access` | slide:p05-cross-tenant |
| 386 | `template:modules/M_privacy_minimization#protection-table` | RFC 7519 §11.2 |
| 387 | `template:modules/M_privacy_minimization#protection-table` | templates/registry/README.md の 8. |
| 388 | `template:modules/M_privacy_minimization#protection-table` | 筆者の提案：保護の要件表を台帳から作って手で二重に書かない（追跡 #19） |
| 411 | `template:modules/M_privacy_minimization#audit-log-protection` | 個人情報の保護に関する法律（平成十五年法律第五十七号）第23条 |
| 416 | `template:modules/M_sender_constraint#dpop-vs-mtls` | FAPI 2.0 Security Profile（Final）§5.3.2.1 |
| 421 | `template:modules/M_sender_constraint#tls-termination` | 筆者の提案：証明書を渡すヘッダーは入口だけが書く（追跡 #3） |
| 424 | `template:modules/M_sender_constraint#rt-rotation` | RFC 9700 §4.14.2 |
| 436 | `template:modules/M_token_validation#issuer` | slide:p05-multitenancy |
| 442 | `template:modules/M_token_validation#header-params` | RFC 7515 §4.1.4 |
| 456 | `template:modules/M_token_validation#jwks-cache` | slide:p01-key-rotation-jwks |
| 459 | `template:modules/M_token_validation#library-config` | RFC 8725 §3.1 |

## 4. 模範の理由が含まれていないことの点検

#4 の方針：カタログとテンプレートには候補と検討の問いだけを載せ、「候補への採否と、その理由を示す文」（模範の理由）は載せない。

- **機械で確かめたこと**：見出しに「（書き手が書く）」のある記入欄の列が、テンプレートでは空であること（`tools/template_check.py` の T4。0 件）
- **機械で確かめていないこと**（点検者が全ファイルを読む）：
  - 地の文・候補の表に、「〜を選ぶ」「推奨」「この例では〜にした」「〜が適切」のような、特定の候補を採る文と理由が無いか
  - 仕様の MUST の紹介（例：MCP の必須チェック、RFC 9700 の公開クライアントの RT）が、仕様の事実の紹介にとどまり、設計の採否の見本になっていないか
  - 候補の並べ方（最初に置いた候補）や「候補」の列の注記が、採否を示唆していないか
- 記録には、読んだファイルの一覧と、指摘が 0 件ならその旨を書いてください（一覧のない「指摘なし」は点検したことにならない。`templates/CONTRIBUTING.md` の 3.）

## 5. 記入例（シナリオ B。PR 2）

対象：`templates/examples/scenario-b/`（`claims.yaml` 46 行、`token_types.yaml` 24 行、`hops.yaml` 15 行、`catalog_answers.yaml` 62 件、`design.md`、`claim_request_*.md` 9 ファイル、`variants/sender-none.yaml`）、`templates/casestudy-deviations.yaml` のシナリオ B の行、`tools/variant_compare.py`、`tools/claim_lint/semantic.py` の L1b の変更。

### 5.1 題材の組み合わせ

- ケーススタディのシナリオ B（社内業務システム）に、シナリオ C（AI エージェントの委任）の委任の部分を足した。`scenario: B` で照合し、C から来た行は `casestudy-deviations.yaml` に `kind: carry`（21 件）で載せた。`not_in_example` は 30 件。点検者は、C の判定と記入例の採否が合っているか（carry の理由が正しいか）を見てください

### 5.2 事実（ケーススタディ・仕様から写したもの）

| # | 事実 | 書いた場所 | 確かめ方 |
| --- | --- | --- | --- |
| B1 | ケーススタディの事例 ID（B3〜B23、C2〜C15、G6・G7・G9・G10・G12・G13）とその中身 | 台帳の `evidence`・`rationale`、design.md の 3.1・6.・9. | repo（jwt-claims-casestudy@080b8da の results/summary.md） |
| B2 | 費用の数値：入口の交換 p50 682 µs、イントロスペクション p50 8.9 ms、ディレクトリ参照 p50 50.7 ms、DPoP の証明 498 バイト・作成と検証 p50 約 0.1 ms、JWS 670 バイト・JWE 1345 バイト | design.md の 3.1 | repo（同上） |
| B3 | Keycloak 26.8.0 のリフレッシュでマッパーが再実行され、部署・ロールが反映される。RT はローテーションされる | 目録の KC_AT・RT | repo（同上の「Keycloak 26.8 の実際の挙動」） |
| B4 | Keycloak corp の AT に `client_id` が無い | `C-kc-client-id`（却下） | シナリオ A の見本（2026-11-22）からの推定。corp では確かめていない（design.md の 12.） |
| B5 | RFC 9068 §2.2 の at+jwt の REQUIRED（iss・exp・aud・sub・client_id・iat・jti）、RFC 8693 §4.1（最も外側の act が今の行為者）・§4.4（may_act）、RFC 7800 §3.1（cnf）、RFC 9449 §4.2・§4.3・§6.1・§8・§11.1、RFC 9396 §2・§9.1、RFC 9470 §3、OpenID Connect Back-Channel Logout 1.0 §2.4（ログアウトトークンに nonce を入れない） | 台帳・目録 | 記憶 |
| B6 | draft-ietf-oauth-transaction-tokens-11 §9.2（txn・req_wl）・§9.2.3（tctx） | `C-txn`・`C-req-wl`・`C-tctx` | 記憶（2.3 の X2 は作業者が web で確かめた） |
| B7 | IANA の JWT Claims の登録の有無：req_wl・tctx・rctx・typ は未登録、htm・htu・ath・cnf・act・txn・groups は登録済み | 台帳の `registered_ref` | repo（`tools/claim_lint/iana_jwt_claims.yaml`、2026-11-23 取得） |
| B8 | ASVS 5.0.0 の 9.2.1・9.2.4・10.3.1・10.3.2 | 台帳の `asvs_ids` | 記憶（10.3.2 だけがリポジトリのほかの場所にもある） |
| B9 | fideslang 3.1.4 のキー（user.unique_id・user.name・user.contact.email・user.job_title・user.financial・user.authorization・system.operations・system.authentication）と、組織の子カテゴリ 2 つ（system.operations.transaction・user.authorization.delegation） | 台帳の `data_category` | 記憶（キーの実在は機械で確かめていない。registry README の 9.） |
| B10 | DPoP の proof の受け入れの窓 60 秒・nonce の寿命 300 秒、接続の寿命（ledger-db 1800 秒、ブローカー 3600 秒） | 目録の DPOP、hops の H11〜H13 | 設計の値（筆者の提案） |
| B11 | Kafka の `connections.max.reauth.ms` は SASL の接続にだけ効き、mTLS の接続では効かない | hops の H12 | 記憶（2.4 の D4 は既定値だけを確かめた） |

### 5.3 機械の検査の結果（作成のとき）

| 検査 | 結果 |
| --- | --- |
| `python tools/claim_lint templates/examples/scenario-b --also-scan .../design.md` | error 0、warn 7、info 28。warn：R3b 3 件（I12・I25・I26 で Keycloak のマッパーが呼ばれるかがカタログで unknown）、L1b 2 件（草案の名前 `req_wl`・`tctx`）、L18 1 件（廃止予定の `C-employee-id` を読む受け手。意図どおり）、L62 1 件（E-token-exchange.2：交換のホップ H15 に上流を置いていない。design.md の 8.） |
| `python tools/claim_lint render templates/examples/scenario-b --check` | OK |
| `python tools/variant_compare.py ... --check design.md` | OK |
| `python tools/casestudy_check.py templates/examples/scenario-b` | error 0（refs 105、ORG 9、deviations 51） |
| L16（下流ほど絞る） | 上流を置いた H2・H4〜H7・H10〜H13 で指摘 0 件。上流を置かない H3・H8・H9・H14・H15 の理由は design.md の 8. |
| L21（目録に無いトークン） | 指摘 0 件 |

### 5.4 規則の変更（#6 の L1b）

草案が定める名前（`registered_ref` が版つきの草案の節を指し、`spec_version` に同じ草案がある）を、error から warn にした。Txn-Token の `req_wl`・`tctx` は組織の名前空間に移せないため。error からの引き下げは「設計書での抑止」ではなく規則の変更なので、#6 の観点で妥当かを点検してください（テスト：`tools/tests/test_claim_lint_semantic.py` の `test_l1b_name_defined_by_a_versioned_draft_is_warn`）。

## 6. 対応表（#22）の変更の点検

- #4 の要件 199 件のうち 122 件（core 92・full 30）を実装済みにした（main に #40・#41 が入った後、`RULES.md` の L3・L5・L6・L9・L14・L18・L23・L43・R8 の行に印を足した 11 件を含む）。実装済みの検査（`trace_check.py`）が確かめるのは、成果物の節に `req:<ID>` の印があることまでで、中身が要件を満たすかは確かめない（`templates/trace/README.md`）。点検者は、実装済みにした要件から 10%（13 件）を選び、その節が要件の文を満たすかを見てください
- 未着手のまま残した 77 件の内訳：#5 の観点書（`review:`）・#8 の実行テスト（`test:`）が無く解決しないもの、提案のままで RULES.md に無い lint の規則（L24・L30・L32・L34・L51・L55・L60 など）、カタログの印が要るもの（p03-keycloak-aud-lightweight.R7、p05-three-principals.R1、p05-system-privileges.R1）、作業者が中身を満たせないとしたもの（p04-case-and-characters.R4：Keycloak の大小の扱いを確かめられなかった）
- planned_items に足したもの（`template:00_core#issuance-profile`、`template:modules/M_sender_constraint#dpop-vs-mtls`・`#tls-termination`・`#dpop-nonce-jti`・`#rt-rotation`・`#registry-effects`、`template:claim_request#form`）と、結び直した要件（p01-client-made-jwts.R2、p02-keys-events-identity-assurance.R2、p06-grant-types.R1、p08-rotation.R1・R2、p09-url-browser.R2、p10-four-questions.R5。`template:claim_request` から `#form`・`#gate` への付け替え 5 件）が妥当か
