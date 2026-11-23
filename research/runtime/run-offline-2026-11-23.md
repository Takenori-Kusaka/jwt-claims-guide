# 実行テストの記録（#8、env=offline）

- 開始（UTC）：2026-11-23T07:57:50+00:00
- 環境：{"python": "3.14.6", "os": "Windows-11-10.0.26300-SP0", "cryptography": "50.0.0", "pyyaml": "6.0.3"}
- 生のトークン・鍵・パスワードは記録しない。試験用の利用者の復号したクレームだけを記録する

| テスト | 結果 | 確かめた数 | 要件 | lint | 期待する結果 |
| --- | --- | --- | --- | --- | --- |
| `test:golden_tokens#scenario-a-at` | PASS | 4/4 | — | — | 見本の AT を参照の saas-api が受理する |
| `test:golden_tokens#scenario-b-tokens` | PASS | 3/3 | — | — | 見本の TXN・TASK_AT を参照の ledger・invoices が受理する |
| `test:negative_tests#alg-none` | PASS | 4/4 | p01-attack-patterns.R1・p01-dangerous-header-params.R1・p01-validation-order.R2・p12-antipatterns-1.R1 | L17 | alg-not-allowed で拒否 |
| `test:negative_tests#alg-confusion` | PASS | 3/3 | p01-attack-patterns.R1・p01-dangerous-header-params.R2・p12-antipatterns-1.R1 | — | alg-not-allowed で拒否（HS256 は許可リストに無い） |
| `test:negative_tests#jku-x5u` | PASS | 6/6 | p01-dangerous-header-params.R4 | L25 | header-key-param で拒否し、URL を 1 回も取得しない |
| `test:negative_tests#embedded-jwk` | PASS | 2/2 | p01-dangerous-header-params.R5 | L25 | header-key-param で拒否 |
| `test:negative_tests#untrusted-key` | PASS | 6/6 | p00-incident-signature-valid.R1・p01-key-rotation-jwks.R1・p01-validation-order.R3・p12-antipatterns-1.R5 | — | unknown-kid・bad-signature で拒否。未知の kid での JWKS の取り直しは 300 秒に 1 回まで |
| `test:negative_tests#iss-mismatch` | PASS | 10/10 | p01-validation-order.R4・p02-registered-claims.R1 | — | iss-not-allowed で拒否（完全一致だけを受ける） |
| `test:negative_tests#aud-wrong` | PASS | 14/14 | p01-attack-patterns.R2・p01-id-token-vs-access-token.R2・p01-library-defaults.R1・p01-validation-order.R5・p02-registered-claims.R3・p03-entra-oid-tid.R5・p03-keycloak-aud-lightweight.R1・p04-reject-missing-required.R4・p05-confused-deputy.R4・p05-cross-tenant.R6・p06-transaction-tokens.R6・p06-validation-split.R2・p10-mcp-authorization.R2・p12-antipatterns-1.R3 | L41 | aud-mismatch で拒否。文字列と配列の aud はどちらも受ける |
| `test:negative_tests#typ-wrong` | PASS | 9/9 | p01-attack-patterns.R4・p01-client-made-jwts.R3・p01-dangerous-header-params.R6・p01-id-token-vs-access-token.R1・p01-validation-order.R7・p03-cognito-token-use.R1・p06-flow-browser-to-db.R2・p06-return-results.R2・p08-logout.R1 | L17 | typ-mismatch で拒否。application/at+jwt は受ける |
| `test:negative_tests#expired` | PASS | 6/6 | p01-validation-order.R6・p12-antipatterns-1.R8 | L27 | expired・lifetime-too-long で拒否。ずれ 30 秒の境界までは受ける |
| `test:negative_tests#nbf-future` | PASS | 4/4 | p01-validation-order.R6 | — | not-yet-valid・iat-in-future で拒否。ずれ 30 秒までは受ける |
| `test:negative_tests#missing-required` | PASS | 9/9 | p01-library-defaults.R2・p01-validation-order.R8・p03-cognito-token-use.R3・p03-confusing-differences.R4 | L7 | missing-claim（iss は iss-not-allowed）で拒否。aud は文字列と配列の両方を受ける |
| `test:negative_tests#missing-required-claim` | PASS | 9/9 | p03-absorb-idp-differences.R5・p03-custom-claim-injection.R1・p04-absent-null-false-empty.R3・p04-forward-compatibility.R2・p04-reject-missing-required.R4・p06-grant-types.R4 | L37・L7 | missing-claim で拒否（fail closed）。roles の欠落は「ロールなし」で受ける |
| `test:negative_tests#duplicate-claim` | PASS | 4/4 | p01-attack-patterns.R6 | — | duplicate-member で拒否 |
| `test:negative_tests#case-variant` | PASS | 6/6 | p04-case-and-characters.R3 | — | 大文字小文字だけが違う値は別の値として扱い、照合に通らない |
| `test:negative_tests#tenant-mismatch` | PASS | 7/7 | p00-incident-signature-valid.R2・p01-attack-patterns.R3・p02-tenant-org.R3・p05-multitenancy.R3・p05-multitenancy.R6・p06-flow-multitenant-saas.R2・p08-reissue-triggers.R1・p12-antipatterns-1.R4 | L9 | tenant-iss-mismatch・tenant-path-mismatch・claim-type で拒否 |
| `test:negative_tests#bola-other-owner` | PASS | 4/4 | p05-bola.R5・p06-validation-split.R5・p12-review-viewpoints.R13 | — | 他人の請求書は not-found（他テナントと同じ答え） |
| `test:negative_tests#revocation-latency` | PASS | 4/4 | p04-token-is-snapshot.R3・p08-revocation-propagation.R2・p08-stale-claims.R3 | — | テナントの停止は次の要求で拒否（0 秒）。ロールの剥奪は受け入れの上限（330 秒）の後に効く |
| `test:negative_tests#txn-token-as-at` | PASS | 2/2 | p06-transaction-tokens.R2 | L43 | Authorization ヘッダーの Txn-Token は txn-token-in-authorization、AT の受け手では typ-mismatch |
| `test:negative_tests#txn-remint-immutable` | PASS | 6/6 | p06-transaction-tokens.R5 | L16・L44 | txn・sub・aud・req_wl を変えた、または scope を広げた Txn-Token は txn-changed で拒否 |
| `test:negative_tests#nested-act` | PASS | 8/8 | p02-delegation-client.R1・p05-confused-deputy.R2・p06-audit-trail.R2・p10-delegation-chain-depth.R4・p10-four-questions.R6 | L12 | 認可は最も外側の act だけで決まる。入れ子の act に特権の主体を入れても権限は増えず、入れ子の act があること自体では拒否しない |
| `test:negative_tests#req-wl-changed` | PASS | 3/3 | p06-validation-split.R3 | — | req_wl だけを変えたトークンを拒否 |
| `test:negative_tests#tctx-mismatch` | PASS | 3/3 | p06-transaction-tokens.R9 | L11 | 本文の操作が tctx と食い違う要求を拒否 |
| `test:negative_tests#approval-mismatch` | PASS | 5/5 | p10-agent-checklist.R7・p10-human-approval-evidence.R3 | L11 | 承認と食い違う金額・相手先・対象、取り消した承認を拒否 |
| `test:negative_tests#passthrough-rejected` | PASS | 2/2 | p10-mcp-authorization.R3 | L41 | MCP サーバー宛ての AGENT_AT を上流の invoices に送ると aud-mismatch |
| `test:negative_tests#rar-unknown-type` | PASS | 4/4 | p05-coarse-fine-layers.R3 | — | 知らない type・フィールド・actions の authorization_details を sts が invalid_authorization_details で拒否 |
| `test:negative_tests#spoofed-identity-header` | PASS | 10/10 | p06-header-forwarding.R1・p06-header-forwarding.R2・p06-header-forwarding.R3・p11-pre-add-questions-2.R5・p12-antipatterns-2.R5 | L72・L8 | x-user-* はどの綴りでも除去、重複は duplicate-header で拒否。素朴な除去は変種を通す |
| `test:negative_tests#exchange-narrowing` | PASS | 10/10 | p03-keycloak-aud-lightweight.R4・p06-narrow-downstream.R3・p10-delegation-chain-depth.R2・p10-token-exchange-not-narrowing.R1・p10-token-exchange-not-narrowing.R4 | L16 | 交換で出たトークンが上流を超えたら指摘する。正規の交換は指摘 0 |
| `test:consumer_contract#declared-reads` | PASS | 6/6 | p00-claims-are-contracts.R7・p11-schema-contract-tests.R4 | — | 受け手が読むクレームはすべて台帳の consumers に受け手がある。consumers から外すと失敗する |
| `test:consumer_contract#unknown-claim-ignored` | PASS | 2/2 | p04-forward-compatibility.R1 | — | 未知のクレームを足しても受理する |
| `test:consumer_contract#issued-claims-present` | PASS | 2/2 | p03-auth0-namespace.R2・p03-entra-scp-roles-groups.R4 | — | 発行されたトークンに、台帳で AT に載ると宣言した採用の独自クレームが全部ある |
| `test:consumer_contract#type-shape-match` | PASS | 5/5 | p04-type.R1 | — | 発行されたトークンが台帳から生成した issuer 適合のスキーマ（型・形）に合う |
| `test:consumer_contract#format-change-cases` | PASS | 9/9 | p11-contract-test-gaps.R1・p11-contract-test-gaps.R2 | L24 | 形式の変化ごとに、どの検査が見つけるかを示す（型だけの契約の死角を含む） |

## `test:golden_tokens#scenario-a-at`（見本のトークン（シナリオ A の AT））

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| t1 の見本の AT で t1 の請求書を一覧する | accept | accepted | OK |
| t1 の行だけが返る | tenant_id がすべて t1 | ["t1", "t1"] | OK |
| t2 の見本の AT で t2 を一覧する | accept | accepted | OK |
| iss に example を含む | example を含む | https://idp.example.com/realms/t1 | OK |

## `test:golden_tokens#scenario-b-tokens`（見本のトークン（シナリオ B））

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| TXN を Txn-Token ヘッダーで ledger に送る | accept | accepted | OK |
| TASK_AT で承認どおりの支払い | accept | accepted | OK |
| 見本の iss に example を含む | すべて example を含む | ["https://tts.corp.example.com", "https://sts.corp.example.com", "https://sts.corp.example.com"] | OK |

## `test:negative_tests#alg-none`（alg=none）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| alg=none（署名なし） | reject alg-not-allowed | alg-not-allowed | OK |
| alg=None（署名なし） | reject alg-not-allowed | alg-not-allowed | OK |
| alg=NONE（署名なし） | reject alg-not-allowed | alg-not-allowed | OK |
| alg の欠落 | reject alg-not-allowed | alg-not-allowed | OK |

## `test:negative_tests#alg-confusion`（RS256 と HS256 の混同）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| t1 の公開鍵（PEM）を HMAC の鍵にした HS256 | reject alg-not-allowed | alg-not-allowed | OK |
| t1 の公開鍵（JWK の JSON）を HMAC の鍵にした HS256 | reject alg-not-allowed | alg-not-allowed | OK |
| 許可リストに無い ES256（kid は t1 の鍵） | reject alg-not-allowed | alg-not-allowed | OK |

## `test:negative_tests#jku-x5u`（jku・x5u）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| jku で攻撃者の鍵の場所を指し、攻撃者の鍵で署名 | reject header-key-param | header-key-param | OK |
| 正しい t1 の署名に jku を足したもの | reject header-key-param | header-key-param | OK |
| x5u で攻撃者の鍵の場所を指し、攻撃者の鍵で署名 | reject header-key-param | header-key-param | OK |
| 正しい t1 の署名に x5u を足したもの | reject header-key-param | header-key-param | OK |
| 検証の間に URL を取得した回数 | 0 | 0 | OK |
| 正しい t1 の署名に、受け手の知らない crit（exp-policy）を足したもの（RFC 7515 §4.1.11） | reject crit-unknown | crit-unknown | OK |

## `test:negative_tests#embedded-jwk`（ヘッダーの jwk・x5c）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| ヘッダーの jwk に自前の公開鍵を入れ、その鍵で署名 | reject header-key-param | header-key-param | OK |
| ヘッダーの x5c に自前の証明書を入れたもの | reject header-key-param | header-key-param | OK |

## `test:negative_tests#untrusted-key`（設定外の鍵・別の発行者の鍵）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| t1 の kid を名乗り、攻撃者の鍵で署名 | reject bad-signature | bad-signature | OK |
| iss=t1 を t2 の鍵（t2 の kid）で署名（Storm-0558 の型、ケーススタディ A9） | reject unknown-kid | unknown-kid | OK |
| 未知の kid rotated-1（0 秒後） | reject unknown-kid | unknown-kid | OK |
| 未知の kid rotated-2（10 秒後） | reject unknown-kid | unknown-kid | OK |
| 未知の kid rotated-3（20 秒後） | reject unknown-kid | unknown-kid | OK |
| 300 秒の間の JWKS の取り直し | 1 回 | 1 回 | OK |

## `test:negative_tests#iss-mismatch`（iss の不一致）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| iss='https://idp.example.com/realms/t1/'（t1 の鍵で正しく署名） | reject iss-not-allowed | iss-not-allowed | OK |
| iss='http://idp.example.com/realms/t1'（t1 の鍵で正しく署名） | reject iss-not-allowed | iss-not-allowed | OK |
| iss='https://IDP.example.com/realms/t1'（t1 の鍵で正しく署名） | reject iss-not-allowed | iss-not-allowed | OK |
| iss='https://idp.example.com/realms/T1'（t1 の鍵で正しく署名） | reject iss-not-allowed | iss-not-allowed | OK |
| iss='https://idp.example.com/realms/t1x'（t1 の鍵で正しく署名） | reject iss-not-allowed | iss-not-allowed | OK |
| iss='https://idp.example.com/realms/t1/../t2'（t1 の鍵で正しく署名） | reject iss-not-allowed | iss-not-allowed | OK |
| iss='https://idp.example.com/realms/t1 '（t1 の鍵で正しく署名） | reject iss-not-allowed | iss-not-allowed | OK |
| iss='https://idp.example.com.attacker.example.net/realms/t1'（t1 の鍵で正しく署名） | reject iss-not-allowed | iss-not-allowed | OK |
| iss='https://idp.example.com'（t1 の鍵で正しく署名） | reject iss-not-allowed | iss-not-allowed | OK |
| iss が配列 | reject iss-not-allowed | iss-not-allowed | OK |

## `test:negative_tests#aud-wrong`（aud の誤り）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| aud='saas-web' | reject aud-mismatch | aud-mismatch | OK |
| aud='account' | reject aud-mismatch | aud-mismatch | OK |
| aud='https://graph.microsoft.com' | reject aud-mismatch | aud-mismatch | OK |
| aud=['other-api'] | reject aud-mismatch | aud-mismatch | OK |
| aud=['saas-web', 'account'] | reject aud-mismatch | aud-mismatch | OK |
| aud='saas-api-admin' | reject aud-mismatch | aud-mismatch | OK |
| aud='SAAS-API' | reject aud-mismatch | aud-mismatch | OK |
| aud の型の誤り 7 | reject claim-type|missing-claim | claim-type | OK |
| aud の型の誤り [] | reject claim-type|missing-claim | claim-type | OK |
| aud の型の誤り ['saas-api', 7] | reject claim-type|missing-claim | claim-type | OK |
| aud の型の誤り None | reject claim-type|missing-claim | missing-claim | OK |
| aud が配列 ["saas-api","account"]（正規） | accept | accepted | OK |
| aud が文字列 "saas-api"（正規） | accept | accepted | OK |
| シナリオ B：Txn-Token の aud が信頼ドメイン（https://corp.example.com）の外 | reject aud-mismatch | aud-mismatch | OK |

## `test:negative_tests#typ-wrong`（typ の誤り）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| ヘッダーの typ='JWT' | reject typ-mismatch | typ-mismatch | OK |
| ヘッダーの typ='jwt' | reject typ-mismatch | typ-mismatch | OK |
| ヘッダーの typ='logout+jwt' | reject typ-mismatch | typ-mismatch | OK |
| ヘッダーの typ='txntoken+jwt' | reject typ-mismatch | typ-mismatch | OK |
| ヘッダーの typ='dpop+jwt' | reject typ-mismatch | typ-mismatch | OK |
| ヘッダーの typ='at+JWT+extra' | reject typ-mismatch | typ-mismatch | OK |
| ヘッダーの typ=None | reject typ-mismatch | typ-mismatch | OK |
| ID トークンの形（typ JWT、aud saas-web）を API に送る（ケーススタディ A13） | reject typ-mismatch | typ-mismatch | OK |
| typ=application/at+jwt（RFC 9068 §2.1 の別の書き方、正規） | accept | accepted | OK |

## `test:negative_tests#expired`（期限切れ）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| exp ちょうど＋30 秒（受け入れの上限 330 秒の境界） | accept | accepted | OK |
| exp＋31 秒（発行から 331 秒） | reject expired | expired | OK |
| 発行から 400 秒（ケーススタディ A14） | reject expired | expired | OK |
| exp − iat = 301 秒（テナントの管理者が寿命を延ばした） | reject lifetime-too-long | lifetime-too-long | OK |
| exp が文字列 | reject claim-type | claim-type | OK |
| exp が真偽値 | reject claim-type | claim-type | OK |

## `test:negative_tests#nbf-future`（nbf が未来・時刻のずれ）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| nbf が 31 秒先 | reject not-yet-valid | not-yet-valid | OK |
| nbf が 30 秒先（ずれの許容の内側） | accept | accepted | OK |
| iat が 31 秒先（発行者の時計が進んでいる） | reject iat-in-future | iat-in-future | OK |
| iat が 30 秒先 | accept | accepted | OK |

## `test:negative_tests#missing-required`（必須クレームの欠落）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| iss を欠く | reject iss-not-allowed | iss-not-allowed | OK |
| sub を欠く | reject missing-claim | missing-claim | OK |
| aud を欠く | reject missing-claim | missing-claim | OK |
| exp を欠く | reject missing-claim | missing-claim | OK |
| iat を欠く | reject missing-claim | missing-claim | OK |
| jti を欠く | reject missing-claim | missing-claim | OK |
| azp を欠く | reject missing-claim | missing-claim | OK |
| exp が null | reject missing-claim | missing-claim | OK |
| aud が配列でも受ける | accept | accepted | OK |

## `test:negative_tests#missing-required-claim`（必須の独自クレームの欠落）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| 名前空間の tenant_id を欠く（マッパーやフックの打ち切りを模擬） | reject missing-claim | missing-claim | OK |
| 名前空間の tenant_id が null | reject missing-claim | missing-claim | OK |
| 名前空間の user_id を欠く（マッパーやフックの打ち切りを模擬） | reject missing-claim | missing-claim | OK |
| 名前空間の user_id が null | reject missing-claim | missing-claim | OK |
| 名前空間の v を欠く（マッパーやフックの打ち切りを模擬） | reject missing-claim | missing-claim | OK |
| 名前空間の v が null | reject missing-claim | missing-claim | OK |
| 名前空間のオブジェクトごと欠く（軽量アクセストークン、ケーススタディ A11） | reject missing-claim | missing-claim | OK |
| 同時に X-Tenant: t2 を付けても、ヘッダーで補わない | reject missing-claim | missing-claim | OK |
| roles を欠く（on_missing: 既定値） | ロールなしで受理 | [] | OK |

## `test:negative_tests#duplicate-claim`（同名のクレームの重複）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| sub が 2 回（後勝ちのパーサーなら carol になる） | reject duplicate-member | duplicate-member | OK |
| 名前空間の中の tenant_id が 2 回 | reject duplicate-member | duplicate-member | OK |
| 名前空間のオブジェクトが 2 回 | reject duplicate-member | duplicate-member | OK |
| ヘッダーの alg が 2 回 | reject duplicate-member | duplicate-member | OK |

## `test:negative_tests#case-variant`（大文字小文字の違い）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| tenant_id="T1"（iss は t1） | reject tenant-iss-mismatch | tenant-iss-mismatch | OK |
| パスのテナントが T1（トークンは t1） | reject tenant-path-mismatch | tenant-path-mismatch | OK |
| user_id が sub の大文字 | reject user-id-mismatch | user-id-mismatch | OK |
| roles=["Approver","TENANT-ADMIN"]（語彙と大文字小文字が違う） | ロールとして数えない（[]） | [] | OK |
| aud="Saas-Api" | reject aud-mismatch | aud-mismatch | OK |
| roles=["approver","tenant-admin","approver"]（台帳の C-roles の max_items 2 を超える） | reject claim-value | claim-value | OK |

## `test:negative_tests#tenant-mismatch`（別テナント・テナントの食い違い）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| t2 のトークンでパス /t1 を一覧 | reject tenant-path-mismatch | tenant-path-mismatch | OK |
| t2 のトークンでパス /t1、ヘッダー X-Tenant: t1（ケーススタディ A5） | reject tenant-path-mismatch | tenant-path-mismatch | OK |
| t2 の管理者が自分のレルムのマッパーで tenant_id=t1 を出させた（iss t2・t2 の鍵、ケーススタディ A8） | reject tenant-iss-mismatch | tenant-iss-mismatch | OK |
| tenant_id が配列 ["t1","t2"]（ケーススタディ A12） | reject claim-type | claim-type | OK |
| tenant_id=''…（0 バイト） | reject claim-value | claim-value | OK |
| tenant_id='xxxxxxxx'…（33 バイト） | reject claim-value | claim-value | OK |
| t2 のトークンで /t2（正規） | accept | accepted | OK |

## `test:negative_tests#bola-other-owner`（BOLA：他人のオブジェクト）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| alice が自分の請求書 2 を読む | accept | accepted | OK |
| alice が同じテナントの carol の請求書 3 を読む | reject not-found | not-found | OK |
| alice が t2 の請求書 1 を読む（ケーススタディ A6） | reject not-found | not-found | OK |
| user_id だけを carol にしたトークン（sub は alice） | reject user-id-mismatch | user-id-mismatch | OK |

## `test:negative_tests#revocation-latency`（剥奪の反映（オフライン））

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| 停止前の要求 | accept | accepted | OK |
| テナントを停止した直後の要求（AT の exp を待たない、ケーススタディの volatility 0） | reject tenant-suspended | tenant-suspended | OK |
| ロールを外した後も、手元の AT は発行から 330 秒まで approver のまま | approver が残る（上限 330 秒の内側） | ["approver"] | OK |
| 発行から 331 秒で、その AT は使えない | reject expired | expired | OK |

- 注：Keycloak を使う版（lifetime_revocation.md）で、剥奪からリフレッシュで新しい AT に替わるまでの時間を測る

## `test:negative_tests#txn-token-as-at`（Txn-Token を AT として送る）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| ledger に Authorization: Bearer <Txn-Token> | reject txn-token-in-authorization | txn-token-in-authorization | OK |
| orders（INT_AT の受け手）に Txn-Token を AT として送る | reject typ-mismatch | typ-mismatch | OK |

## `test:negative_tests#txn-remint-immutable`（Txn-Token の作り直しで不変であるべきもの）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| TTS が作り直して txn を変えた（署名は正しい） | reject txn-changed|unknown-txn|aud-mismatch | unknown-txn | OK |
| TTS が作り直して sub を変えた（署名は正しい） | reject txn-changed|unknown-txn|aud-mismatch | txn-changed | OK |
| TTS が作り直して aud を変えた（署名は正しい） | reject txn-changed|unknown-txn|aud-mismatch | aud-mismatch | OK |
| TTS が作り直して scope を広げた（ledger.post）（署名は正しい） | reject txn-changed|unknown-txn|aud-mismatch | txn-changed | OK |
| 作り直しで exp を延ばした（検査の関数） | 指摘あり | ["exp extended (org rule: H9 note)"] | OK |
| 改変せずに渡した（正規） | 指摘なし | [] | OK |

## `test:negative_tests#nested-act`（入れ子の act）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| 入れ子の act.act.sub を admin-console にし、scope に invoices.refund を足したトークンで返金（今の代理者 invoice-mcp に返金は許されていない） | reject actor-not-allowed | actor-not-allowed | OK |
| 同じトークンで支払い（入れ子の act は判断に使わないので、拒否もしない） | accept | accepted | OK |
| その支払いの今の代理者 | 最も外側の act.sub（invoice-mcp） | invoice-mcp | OK |
| 最も外側を admin-console にし、invoice-mcp を内側に入れた（内側を読む受け手なら通る） | reject actor-mismatch | actor-mismatch | OK |
| 委任の連鎖の深さ 4（組織の規則 max_delegation_depth 3。名前は読まない） | reject delegation-too-deep | delegation-too-deep | OK |
| 最も外側の act.sub と mTLS の相手が違う | reject actor-mismatch | actor-mismatch | OK |
| act が無い（利用者のトークンを借りた形、ケーススタディ C12） | reject missing-claim | missing-claim | OK |
| 正規の連鎖（invoice-mcp ← agent:expense） | accept | accepted | OK |

## `test:negative_tests#req-wl-changed`（req_wl だけを変えた）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| req_wl だけを書き換えた（署名はそのまま） | reject bad-signature | bad-signature | OK |
| TTS が req_wl=orders で発行した（入口以外が Txn-Token を求めた） | reject req-wl-not-allowed | req-wl-not-allowed | OK |
| mTLS の相手が orders でない | reject peer-mismatch | peer-mismatch | OK |

## `test:negative_tests#tctx-mismatch`（本文と tctx の食い違い）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| 本文の operation=ledger.post、tctx は ledger.read | reject tctx-body-mismatch | tctx-body-mismatch | OK |
| tctx.operation=ledger.post（scope は ledger.read） | reject tctx-scope-mismatch | tctx-scope-mismatch | OK |
| tctx に語彙に無い項目（amount） | reject tctx-shape | tctx-shape | OK |

- 注：シナリオ B の tctx の項目は operation だけ（claims.yaml C-tctx の value_vocabulary）。#8 の本文の「本文の数量」は、この記入例では承認の金額（approval-mismatch）で確かめる

## `test:negative_tests#approval-mismatch`（承認の内容と要求の食い違い）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| 金額を 1,200,000 に変えた（ケーススタディ C5） | reject approval-mismatch | approval-mismatch | OK |
| 相手先の口座を変えた（C6） | reject approval-mismatch | approval-mismatch | OK |
| authorization_details が空 | reject approval-missing | approval-missing | OK |
| 承認どおりでも scope に invoices.pay が無い | reject scope-missing | scope-missing | OK |
| 承認を取り消した後（C7。トークンの exp を待たない） | reject approval-not-active | approval-not-active | OK |

## `test:negative_tests#passthrough-rejected`（トークンのパススルー）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| invoice-mcp が受けた AGENT_AT をそのまま invoices に送る（ケーススタディ C2） | reject aud-mismatch | aud-mismatch | OK |
| 宛先を複数にした広いトークン（C13。H15 は aud が invoices だけ） | reject aud-mismatch | aud-mismatch | OK |

## `test:negative_tests#rar-unknown-type`（知らない authorization_details）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| 承認の形どおり | accept | accepted | OK |
| type が https://claims.example.com/rar/refund | reject invalid_authorization_details | invalid_authorization_details | OK |
| 知らないフィールド maxAmount | reject invalid_authorization_details | invalid_authorization_details | OK |
| actions に refund | reject invalid_authorization_details | invalid_authorization_details | OK |

## `test:negative_tests#spoofed-identity-header`（ID 系ヘッダーの偽装）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| 'X-User-Id' を入口で除去 | 除去される | ["Authorization"] | OK |
| 'x-user-id' を入口で除去 | 除去される | ["Authorization"] | OK |
| 'X_USER_ID' を入口で除去 | 除去される | ["Authorization"] | OK |
| 'x-User_Roles' を入口で除去 | 除去される | ["Authorization"] | OK |
| ' X-User-Department' を入口で除去 | 除去される | ["Authorization"] | OK |
| x-user-id が 2 回（大文字小文字違い） | reject duplicate-header | duplicate-header | OK |
| Authorization が 2 回 | reject duplicate-header | duplicate-header | OK |
| X_User_Id と X-User-Id（_ と - の変種の重複） | reject duplicate-header | duplicate-header | OK |
| 素朴な除去（X-User-Id の完全一致だけ）は変種を通す＝このテストが見つける誤り | 4 件以上が残る | ["x-user-id", "X_USER_ID", "x-User_Roles", " X-User-Department"] | OK |
| シナリオ A の API は X-Tenant を読まない | t2 の行だけ | ["t2"] | OK |

## `test:negative_tests#exchange-narrowing`（交換で絞られているか（オフライン））

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| H14→H15 の正規の交換 | 指摘 0 | [] | OK |
| 作った TASK_AT で scope に invoices.refund を足した | 指摘あり | ["scope widened by ['invoices.refund'] (upstream ['invoices.pay', 'invoices.read'])"] | OK |
| 作った TASK_AT で aud に orders を足した | 指摘あり | ["aud ['invoices', 'orders'] is not the declared single replacement ['invoices'] (added ['orders'])"] | OK |
| 作った TASK_AT で exp を上流より 600 秒延ばした | 指摘あり | ["exp extended by 600 s beyond the upstream exp"] | OK |
| 作った TASK_AT で 承認の金額を変えた | 指摘あり | ["authorization_details entry not upstream: {'type': 'https://claims.example.com/rar/payment', 'actions': ['pay'], 'identifier': 'inv-1', 'instructedAmount': 999999, 'creditorAccount': 'JP00-1234-5678'}"] | OK |
| 作った TASK_AT で 独自クレーム department を足した | 指摘あり | ["custom claim department added"] | OK |
| 作った TASK_AT で tenant_id を変えた | 指摘あり | ["custom claim tenant_id changed 'corp' -> 'other'"] | OK |
| ケーススタディの実測 narrow_to_invoices（aud=invoices） | 指摘 0 | [] | OK |
| ケーススタディの実測 scope_not_granted（aud=['orders', 'account']） | 指摘あり（orders が出た） | ["aud ['orders', 'account'] is not the declared single replacement ['invoices'] (added ['orders', 'account'])", "scope aud-orders carries audience orders, which is neither upstream nor the declared target"] | OK |
| aud は invoices だけのまま、scope に宛先を運ぶ aud-orders が付いた交換（Keycloak の audience スコープの規則だけが見つける） | 「aud-orders carries audience orders」の指摘だけ | ["scope aud-orders carries audience orders, which is neither upstream nor the declared target"] | OK |

## `test:consumer_contract#declared-reads`（読むクレームの宣言）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| 台帳のとおり（consumers に saas-api） | 違反 0 | [] | OK |
| 読むクレームの型：台帳から生成した今の版の consumer のスキーマ（AT.consumer.schema.json） | スキーマの誤り 0 | [] | OK |
| C-roles の consumers から saas-api を外す | 契約テストが失敗する（違反 1 件以上） | ["https://claims.example.com/roles (C-roles): saas-api is not in consumers []"] | OK |
| C-tenant-id の consumers から saas-api を外す | 契約テストが失敗する（違反 1 件以上） | ["https://claims.example.com/tenant_id (C-tenant-id): saas-api is not in consumers []"] | OK |
| C-azp の consumers から saas-api を外す | 契約テストが失敗する（違反 1 件以上） | ["azp (C-azp): saas-api is not in consumers []"] | OK |
| 受け手が email を読まないこと（AT に載せない宣言と一致） | email を読まない | false | OK |

- 注：参照の saas-api が読んだメンバー：aud、azp、exp、https://claims.example.com/、https://claims.example.com/roles、https://claims.example.com/tenant_id、https://claims.example.com/user_id、https://claims.example.com/v、iat、iss、jti、sub

## `test:consumer_contract#unknown-claim-ignored`（未知のクレームを無視する）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| 最上位に未知のクレーム 2 つ | accept | accepted | OK |
| 名前空間に未知の department | accept | accepted | OK |

## `test:consumer_contract#issued-claims-present`（発行されたトークンの黙った欠落）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| Keycloak 26.8 が発行した見本（tools/tests/fixtures/claim_lint/golden/token.json） | 欠落 0 | [] | OK |
| 軽量アクセストークンの形（ケーススタディ keycloak.lightweight の light_claims） | 欠落を検出 | ["C-sub (sub)", "C-aud (aud)", "C-tenant-id (https://claims.example.com/tenant_id)", "C-user-id (https://claims.example.com/user_id)", "C-v (https://claims.example.com/v)"] | OK |

## `test:consumer_contract#type-shape-match`（型と形の一致）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| Keycloak 26.8 の見本 | スキーマの誤り 0 | [] | OK |
| 見本を変えて roles が文字列 | スキーマの誤りあり | ["https://claims.example.com//roles: 'approver' is not of type 'array'"] | OK |
| 見本を変えて tenant_id が配列 | スキーマの誤りあり | ["https://claims.example.com//tenant_id: ['t1'] is not of type 'string'"] | OK |
| 見本を変えて v が数値 | スキーマの誤りあり | ["https://claims.example.com//v: 1 is not of type 'string'"] | OK |
| 見本を変えて 知らないクレームを足した | スキーマの誤りあり | ["(root): Additional properties are not allowed ('x_new' was unexpected)"] | OK |

## `test:consumer_contract#format-change-cases`（契約テストが見逃しやすい変更）

| 確かめたこと | 期待 | 観測 | 判定 |
| --- | --- | --- | --- |
| 区切り文字：roles を配列から空白区切りの文字列に | 型だけの契約は見つける。issuer 適合のスキーマか参照の受け手のどちらかが見つける | {"consumer_schema": "detect", "issuer_schema": "detect", "reference_api": "claim-type"} | OK |
| 区切り文字：roles の要素をカンマで連結した 1 要素に | 型だけの契約は見逃す。issuer 適合のスキーマか参照の受け手のどちらかが見つける | {"consumer_schema": "miss", "issuer_schema": "detect", "reference_api": "accepted"} | OK |
| 大文字化：tenant_id を T1 に | 型だけの契約は見逃す。issuer 適合のスキーマか参照の受け手のどちらかが見つける | {"consumer_schema": "miss", "issuer_schema": "miss", "reference_api": "tenant-iss-mismatch"} | OK |
| 2^53 を超える数値：user_id を数値 9007199254740993 に | 型だけの契約は見つける。issuer 適合のスキーマか参照の受け手のどちらかが見つける | {"consumer_schema": "detect", "issuer_schema": "detect", "reference_api": "user-id-mismatch"} | OK |
| null：roles を null に | 型だけの契約は見つける。issuer 適合のスキーマか参照の受け手のどちらかが見つける | {"consumer_schema": "detect", "issuer_schema": "detect", "reference_api": "claim-type"} | OK |
| false：tenant_id を false に | 型だけの契約は見つける。issuer 適合のスキーマか参照の受け手のどちらかが見つける | {"consumer_schema": "detect", "issuer_schema": "detect", "reference_api": "claim-type"} | OK |
| 真偽値の文字列化：v を "true" に（版の値の取り違え） | 型だけの契約は見逃す。issuer 適合のスキーマか参照の受け手のどちらかが見つける | {"consumer_schema": "miss", "issuer_schema": "miss", "reference_api": "unknown-version"} | OK |
| 制限のクレームの追加：名前空間に read_only: true | 型だけの契約は見逃す。issuer 適合のスキーマか参照の受け手のどちらかが見つける | {"consumer_schema": "miss", "issuer_schema": "detect", "reference_api": "accepted"} | OK |
| 2^53 を超える整数を倍精度で読む受け手（JavaScript の Number と同じ） | 値が変わる | 9007199254740992 | OK |

- 注：シナリオ A の AT に真偽値のクレームはない。真偽値の文字列化は、版の値 v（文字列の語彙）で代えた
