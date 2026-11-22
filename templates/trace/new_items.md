<!-- template_version: 0.1.0 -->
<!-- 生成物。手で書き換えない。python tools/trace_check.py --write-new-items で作り直す -->
# 対応表で足した成果物の提案（#22）

対応表（`requirements.yaml`）を作るときに、どの issue の本文にもない成果物が必要になったものの一覧です。各 issue の本文に書き足すかどうかは、担当の issue で決めます。書き足さない場合は、`planned_items.yaml` の項目を別の成果物に付け替えるか、要件を「扱わない」にします。

提案の件数：259 件

## #3（32 件）

| 成果物 | 内容 | 使う要件 |
| --- | --- | --- |
| `registry:claims#absent_semantics` | 無い・null・false・空配列・空文字の意味の区別（上限による欠落を「所属なし」と読まない。無いときの挙動は on_missing） | `p00-claims-are-contracts.R3`, `p00-why-hard.R1`, `p00-why-hard.R5`, `p03-entra-scp-roles-groups.R1`, `p04-absent-null-false-empty.R1`, `p04-absent-null-false-empty.R5`, `p04-design-checklist.R7`, `p11-why-govern.R2`, `p11-pre-add-questions-1.R9`, `p12-review-viewpoints.R2` |
| `registry:claims#value_vocabulary` | 値の語彙（許可値の列挙・語彙の名前空間・語彙の持ち主・acr の値と水準の対応・authorization_details の type） | `p02-roles-groups-entitlements.R2`, `p02-scope.R4`, `p02-auth-strength-session.R1`, `p05-coarse-fine-layers.R4` |
| `registry:claims#prior_art_search` | 作る前に探した記録（IANA・仕様の構造・IdP の文書・組織の台帳）、近い既存クレームとの違い、使わなかった理由 | `p02-check-before-creating.R1`, `p02-check-before-creating.R3`, `p02-check-before-creating.R4`, `p04-claim-names.R1`, `p04-design-checklist.R2` |
| `registry:token_types#key_source` | 検証の鍵の取得元（事前に設定した JWKS だけか、許可リストつきの jku か）。ヘッダーの jwk・x5c を信頼しないことの宣言 | `p01-dangerous-header-params.R4`, `p01-dangerous-header-params.R5`, `p01-key-rotation-jwks.R1` |
| `registry:token_types#jti_policy` | jti の一意性の範囲（発行者をまたいで衝突しない）と、リプレイ検知に使うかどうか | `p01-client-made-jwts.R2`, `p02-registered-claims.R5` |
| `registry:token_types#subject_type` | sub の種類（public／pairwise）。ペアワイズなら突き合わせに使うキーを別に書く | `p02-user-identifier.R3`, `p09-pairwise-identifiers.R1`, `p09-pairwise-identifiers.R3`, `p09-checklist.R3` |
| `registry:claims#provenance` | 値の出どころと書ける者（発行者・管理側が確かめた値／呼び出し側の申告／本人が編集できる値） | `p03-cognito-pre-token-hook.R4`, `p04-split-by-writer.R1`, `p04-design-checklist.R10`, `p07-three-db-paths.R4`, `p07-row-level-security.R2`, `p07-cloud-attributes.R1`, `p11-registry-fields.R5`, `p11-pre-add-questions-1.R11`, `p12-antipatterns-1.R7`, `p12-review-viewpoints.R15` |
| `registry:claims#effect` | クレームの効き方（許可を与える／制限をかける）。無いときの既定の扱いを決める入力 | `p04-absent-null-false-empty.R2`, `p04-absent-null-false-empty.R3` |
| `registry:claims#value_normalization` | 値の文字集合・大文字小文字・正規化をする書き手と、受け手の比較の規則（完全一致） | `p04-case-and-characters.R1`, `p04-case-and-characters.R2`, `p04-design-checklist.R8`, `p11-pre-add-questions-1.R10` |
| `registry:claims#consumer_access_path` | 受け手のツール（ゲートウェイ・メッシュ・CEL・JSONPath）ごとの参照式と、読めることを確かめた記録 | `p04-namespace.R2`, `p04-namespace.R3`, `p04-design-checklist.R4` |
| `registry:claims#flat_alias` | ネストできない IdP 向けのフラットな別名 | `p04-namespace.R4`, `p04-namespace-object-example.R2` |
| `registry:claims#namespace_version` | 名前空間のオブジェクトの構造の版（v） | `p04-namespace-object-example.R1` |
| `registry:claims#paired_id` | 名前のクレームと対になる変わらない ID のクレーム | `p00-incident-signature-valid.R4`, `p04-immutable-identifiers.R2`, `p04-design-checklist.R9` |
| `registry:claims#composite_format` | 合成の識別子（sub など）の区切り文字と退避の規則、その公開先 | `p00-incident-signature-valid.R4`, `p04-immutable-identifiers.R3` |
| `registry:token_types#subject_kind` | sub が表す主体の種類（利用者／クライアント・ワークロード）と、受け手が区別する手段 | `p05-three-principals.R2`, `p05-system-privileges.R2` |
| `registry:token_types#signing_key_scope` | 署名鍵のスコープ（テナント単位か、共有か） | `p05-multitenancy.R5` |
| `registry:hops#authorization_details` | ホップごとの authorization_details（宛先に合わせて絞る。L16 の比較対象に加える） | `p05-coarse-fine-layers.R2`, `p10-four-questions.R3`, `p10-human-approval-evidence.R2` |
| `registry:questions#q-via` | 問い「どこを経由したか」（経由を示す別の属性） | `p05-one-request-carries.R2`, `p05-confused-deputy.R5` |
| `registry:README#slide-61-map` | スライド 61 の設計のチェックリスト 12 項目と台帳の列の対応表 | `p04-design-checklist.R1`, `p04-design-checklist.R2`, `p04-design-checklist.R3`, `p04-design-checklist.R4`, `p04-design-checklist.R5`, `p04-design-checklist.R6`, `p04-design-checklist.R7`, `p04-design-checklist.R8`, `p04-design-checklist.R9`, `p04-design-checklist.R10`, `p04-design-checklist.R11`, `p04-design-checklist.R12`, `p04-design-checklist.R13` |
| `registry:token_types#log_policy` | トークン全体のログの方針（記録しない／ハッシュ・jti だけ）と、ログ・トレースに記録してよい要素・ヘッダーの許可リスト | `p06-transaction-tokens.R7`, `p06-audit-trail.R6`, `p08-copies-outlive-token.R3`, `p09-logs-traces.R1`, `p09-logs-traces.R2`, `p09-checklist.R8` |
| `registry:hops#validates` | ホップの受け手が確かめること（署名・iss・exp・aud・相手の ID）と方式（手元で検証／問い合わせ） | `p06-validation-split.R1`, `p06-header-forwarding.R4`, `p08-revocation-propagation.R4` |
| `registry:claims#privilege_level` | クレームが選ぶ権限の強さ（DB のロール・マスキングの解除など最高権限の印） | `p07-trust-boundary.R4`, `p07-masking.R1` |
| `registry:hops#connection_max_lifetime` | DB・ブローカーへのホップの接続の最大寿命と再認証の設定 | `p07-lifetime-mismatch.R1`, `p08-copies-outlive-token.R1` |
| `registry:token_types#client_type` | クライアントの種類（公開／機密／FAPI 対象） | `p06-grant-types.R1`, `p08-rotation.R2` |
| `registry:token_types#idle_timeout` | 長く使われない RT・セッションを失効させる期間（idle。絶対的な上限の max_lifetime とは別の列。#3 で rt_idle_timeout から改名） | `p08-rotation.R4` |
| `registry:token_types#introspection_cache_ttl` | イントロスペクション応答のキャッシュの TTL（応答の exp を超えない） | `p08-revocation-propagation.R3`, `p08-copies-outlive-token.R2` |
| `registry:token_types#selective_disclosure` | SD-JWT の選択的開示の対象クレームと鍵束縛の有無 | `p09-jwe-sd-jwt.R3` |
| `registry:token_types#max_delegation_depth` | 委任の連鎖（act の入れ子）の深さの上限（組織の規則） | `p10-delegation-chain-depth.R1`, `p12-priorities-deferrals.R6` |
| `registry:claims#allowed_values` | 形式（正規表現）と許容値 | `p11-registry-fields.R2`, `p11-contract-test-gaps.R1` |
| `registry:claims#restrictive` | 制限のクレーム（知らない受け手が無視すると危険）の印 | `p11-contract-test-gaps.R4`, `p11-pre-add-questions-2.R7` |
| `registry:claims#consumers_migration` | 受け手ごとの新形式への移行状況 | `p11-change-procedure.R6` |
| `registry:README#namespace-owner` | 組織の名前空間の持ち主と、下位の名前の割り当て規則（台帳への登録） | `p11-reserved-names.R2`, `p11-reserved-names.R3`, `p11-ownership.R1` |

## #4（69 件）

| 成果物 | 内容 | 使う要件 |
| --- | --- | --- |
| `template:modules/M_token_validation#shared-validator` | 組織共通の検証・解析部品の採否と版、そこで固定する alg・発行者・宛先・必須クレーム（各サービスに生で解析させない） | `p00-why-hard.R2`, `p00-incident-signature-valid.R5`, `p01-library-defaults.R4`, `p11-contract-test-gaps.R3`, `p11-translation-layer.R3`, `p11-pre-add-questions-2.R4`, `p12-review-viewpoints.R10` |
| `template:modules/M_token_validation#validation-order` | 検証の順序（形式・alg・署名・iss・aud・exp/nbf・typ・クレーム）と、受け入れ前に独自クレームを読まないこと | `p01-validation-order.R1`, `p01-validation-order.R9`, `p01-attack-patterns.R7` |
| `template:modules/M_token_validation#audience` | aud の検証（文字列と配列の両方を受け付け、自分が含まれなければ拒否） | `p01-validation-order.R5`, `p02-registered-claims.R3` |
| `template:modules/M_token_validation#header-params` | ヘッダーの危険なパラメータ（kid・jku・x5u・jwk・x5c）の扱い | `p01-jwt-structure.R1`, `p01-dangerous-header-params.R3` |
| `template:modules/M_token_validation#library-config` | 使う検証ライブラリと版、明示した設定（audience・issuer・algorithms・必須クレーム・時刻のずれ・鍵の確認・重複クレームの拒否） | `p00-incident-signature-valid.R5`, `p01-library-defaults.R1`, `p01-library-defaults.R3`, `p01-library-defaults.R5`, `p01-attack-patterns.R6` |
| `template:00_core#step-up` | 操作ごとに求める acr・max_age と、足りないときの応答（insufficient_user_authentication） | `p02-auth-strength-session.R6`, `p06-step-up-approval.R1` |
| `template:profiles/P4_ai_agent_delegation#delegation-policy` | may_act を誰がどう評価するか、委任の理由・承認者をどこに置くか（act の外） | `p02-delegation-client.R3`, `p02-delegation-client.R4` |
| `template:modules/M_idp_keycloak#broker-mapping` | Keycloak のブローカーでの写し方（IdP マッパーで取り込み、プロトコルマッパーで社内の名前のクレームに） | `p02-saml-attributes.R5` |
| `template:modules/M_idp_keycloak#mappers-scopes` | プロトコルマッパー（名前・JSON の型・載せるトークン）とクライアントスコープ（Default／Optional）、ロールの積集合、グループのフルパス | `p03-keycloak-mappers.R1`, `p03-keycloak-mappers.R2`, `p03-keycloak-mappers.R4`, `p03-keycloak-mappers.R5` |
| `template:modules/M_idp_keycloak#client-scope` | Keycloak のクライアントスコープとロールの絞り込み（Full Scope Allowed は本番でオフ、レルムとクライアントのロール） | `p03-keycloak-mappers.R3`, `p05-scope-vs-role.R2`, `p05-scope-vs-role.R3`, `p05-role-explosion.R3` |
| `template:modules/M_idp_keycloak#audience-mapper` | API を aud に入れる Audience マッパーの設定（既定の account に頼らない） | `p03-keycloak-aud-lightweight.R1` |
| `template:modules/M_idp_keycloak#lightweight-at` | 軽量アクセストークンの採否と、落ちるクレームを受け手がどう得るか | `p03-keycloak-aud-lightweight.R2` |
| `template:00_core#principals` | 主体の種類（利用者・ワークロード・システム）と表し方の表 | `p05-three-principals.R1` |
| `template:00_core#system-privileges` | システムの権限の表（夜間バッチ・運用者の操作・break-glass・基盤の操作ごとの主体・トークン・記録・承認と期限） | `p05-system-privileges.R1`, `p05-system-privileges.R3`, `p05-system-privileges.R5`, `p05-system-privileges.R7`, `p05-cross-tenant.R3` |
| `template:modules/M_authz_pdp#object-level` | オブジェクト単位の認可（3 段の認可、所有者・テナントのデータ側での照合、404／403 の方針） | `p05-authz-models.R2`, `p05-bola.R1`, `p05-bola.R2`, `p05-bola.R3`, `p06-validation-split.R5` |
| `template:modules/M_authz_pdp#layers` | 粗い権限・取引単位・オブジェクト単位の 3 層の置き場所の表 | `p05-coarse-fine-layers.R1`, `p05-role-explosion.R2` |
| `template:modules/M_authz_pdp#pep-pdp-inputs` | PEP・PDP・PIP の分担と、判断の入力ごとの出どころ | `p05-pep-pdp.R1`, `p05-pep-pdp.R2` |
| `template:modules/M_multitenancy#cross-tenant` | テナントをまたぐ場面（複数テナントの利用者・運用者・取引先）ごとの識別子と権限の出し方 | `p05-cross-tenant.R1`, `p05-cross-tenant.R2` |
| `template:profiles/P4_ai_agent_delegation#human-approval` | 人の承認（CIBA の binding_message・結果の受け取り方・承認の記録） | `p06-step-up-approval.R4`, `p10-human-approval-evidence.R1`, `p10-human-approval-evidence.R5` |
| `template:modules/M_idp_keycloak#token-exchange-downscope` | Keycloak のトークン交換を許すクライアント・宛先・スコープの最小化（絞り込みだけを許す設定、scope で宛先が足される点） | `p06-narrow-downstream.R4`, `p10-token-exchange-not-narrowing.R2`, `p10-token-exchange-not-narrowing.R3`, `p10-token-exchange-not-narrowing.R5`, `p10-vendor-features（教材）` |
| `template:00_core#result-integrity` | 結果・応答・Webhook の完全性の方式（JWT／RFC 9421／参照型）と署名する部分 | `p06-return-results.R1`, `p06-return-results.R4`, `p06-flow-partner-events.R3` |
| `template:modules/M_multitenancy#operator-access` | 運用者のテナント横断作業（委任トークン・緊急時の承認と期限・両者の監査） | `p06-flow-multitenant-saas.R5` |
| `template:profiles/P5_internal_propagation#async-messaging` | イベント・キュー（発行者の ID・メタデータの間接参照と txn・配送の認証・コンシューマーの作り直し） | `p06-flow-partner-events.R4`, `p06-flow-partner-events.R5`, `p06-flow-partner-events.R6`, `p08-async-processing.R2`, `p08-async-processing.R3` |
| `template:modules/M_data_layer#cloud-credentials` | クラウドの一時認証情報（テナントに限る部品への集約、クレームがポリシーで効くか） | `p07-connect-as-whom.R4`, `p07-cloud-attributes.R2` |
| `template:00_core#lifetime-policy` | 組織の種類ごとの寿命の上限と、例外を認める手順、剥奪の許容時間から導いた理由 | `p08-token-types-lifetimes.R4`, `p08-choosing-lifetime.R1`, `p08-choosing-lifetime.R2`, `p08-choosing-lifetime.R4`, `p08-decision-table.R1` |
| `template:modules/M_idp_keycloak#refresh-token-settings` | Keycloak の RT の設定（Revoke Refresh Token、リフレッシュ時の再評価、交換で出した RT の期限） | `p08-refresh-reevaluation.R3`, `p08-rotation.R5`, `p08-rotation.R8` |
| `template:modules/M_idp_keycloak#introspection` | Keycloak のイントロスペクション（aud のクライアントだけ active、問い合わせの資格情報） | `p08-revocation-propagation.R5` |
| `template:modules/M_privacy_minimization#derived-values` | 値ではなく判定（派生値）で足りるかの判断と、判定の責任を持つ発行者 | `p09-minimize-derived.R1`, `p09-minimize-derived.R2`, `p09-checklist.R2` |
| `template:modules/M_privacy_minimization#sensitive-via-api` | 機微な属性をトークンに入れず、送信者制約つきの identity API で期間を限って渡す判断 | `p09-minimize-derived.R3` |
| `template:modules/M_privacy_minimization#identifier-sectors` | 社内で突き合わせる ID と外部に出す ID（public／pairwise・セクター）の設計 | `p09-pairwise-identifiers.R2` |
| `template:modules/M_privacy_minimization#protection-order` | 機微な値の保護の優先順（載せない→派生値→JWE・SD-JWT）の選択と理由 | `p09-jwe-sd-jwt.R1` |
| `template:modules/M_privacy_minimization#audit-log-protection` | 監査ログ自体を機微な情報として守る方針（アクセス・保存期間） | `p09-logs-traces.R5`, `p09-checklist.R9` |
| `template:modules/M_token_validation#nested-jwt` | ネストした JWT（署名＋暗号化）で外側と内側の両方を検証する設定 | `p09-jwe-sd-jwt.R2` |
| `template:profiles/P1_human_web#url-exposure` | トークン・認可パラメータを URL から外す（PAR・form_post・Authorization ヘッダー）判断表 | `p09-url-browser.R2` |
| `template:profiles/P4_ai_agent_delegation#agent-identity` | エージェントを独立した ID として登録する欄（共有アカウント・利用者のトークンを使わない） | `p10-agent-identity.R1`, `p10-agent-checklist.R1` |
| `template:profiles/P4_ai_agent_delegation#delegation-mode` | 自律・委任・なりすましの型の選択と、エージェント自身の権限と代理の権限の分離 | `p10-agent-identity.R2`, `p10-agent-identity.R4` |
| `template:profiles/P4_ai_agent_delegation#audit-correlation` | sub・全アクター・txn・承認 ID・昇格の相関 ID を監査ログで相関させる欄 | `p10-agent-identity.R5`, `p10-per-tool-scopes.R3`, `p10-human-approval-evidence.R4`, `p10-agent-checklist.R9`, `p11-pre-add-questions-2.R9` |
| `template:profiles/P4_ai_agent_delegation#tool-scopes` | ツールごとの最小スコープ、WWW-Authenticate による段階的な引き上げ | `p10-per-tool-scopes.R1`, `p10-per-tool-scopes.R2` |
| `template:profiles/P4_ai_agent_delegation#chain-revocation` | 委任の根元の承認からの一括失効の手段 | `p10-delegation-chain-depth.R3` |
| `template:modules/M_idp_keycloak#token-preview` | 発行前に実トークンを確かめる手段（プレビュー・評価機能） | `p11-schema-contract-tests.R3`, `p11-change-procedure.R4`, `p11-pre-add-questions-2.R13` |
| `template:00_core#operational-metrics` | 運用で測る指標（台帳とのずれ・検証失敗など）、周期、持ち主 | `p11-audit-metrics.R3`, `p11-audit-metrics.R6`, `p11-audit-metrics.R7` |
| `template:00_core#baseline` | どの組織でも却下できない共通の基準（受け入れの検証・欠落の拒否・型の固定・不変の ID・名前空間・ログ）の確認欄 | `p12-priorities-deferrals.R1`, `p12-priorities-deferrals.R2`, `p12-summary（教材）` |
| `template:00_core#priorities-deferrals` | 組織の種類ごとの重点と見送り、その効果・費用・見直しの条件 | `p12-priorities-deferrals.R3`, `p12-priorities-deferrals.R4`, `p12-priorities-deferrals.R5` |
| `template:claim_request#q01` | 追加前の 25 問の第 1 問の回答欄 | `p11-pre-add-questions-1.R1` |
| `template:claim_request#q02` | 追加前の 25 問の第 2 問の回答欄 | `p11-pre-add-questions-1.R2` |
| `template:claim_request#q03` | 追加前の 25 問の第 3 問の回答欄 | `p10-four-questions.R7`, `p11-pre-add-questions-1.R3`, `p12-review-viewpoints.R1` |
| `template:claim_request#q04` | 追加前の 25 問の第 4 問の回答欄 | `p11-pre-add-questions-1.R4` |
| `template:claim_request#q05` | 追加前の 25 問の第 5 問の回答欄 | `p11-pre-add-questions-1.R5` |
| `template:claim_request#q06` | 追加前の 25 問の第 6 問の回答欄 | `p11-pre-add-questions-1.R6` |
| `template:claim_request#q07` | 追加前の 25 問の第 7 問の回答欄 | `p11-pre-add-questions-1.R7` |
| `template:claim_request#q08` | 追加前の 25 問の第 8 問の回答欄 | `p11-pre-add-questions-1.R8` |
| `template:claim_request#q09` | 追加前の 25 問の第 9 問の回答欄 | `p11-pre-add-questions-1.R9` |
| `template:claim_request#q10` | 追加前の 25 問の第 10 問の回答欄 | `p11-pre-add-questions-1.R10` |
| `template:claim_request#q11` | 追加前の 25 問の第 11 問の回答欄 | `p11-pre-add-questions-1.R11` |
| `template:claim_request#q12` | 追加前の 25 問の第 12 問の回答欄 | `p11-pre-add-questions-1.R12` |
| `template:claim_request#q13` | 追加前の 25 問の第 13 問の回答欄 | `p11-pre-add-questions-2.R1` |
| `template:claim_request#q14` | 追加前の 25 問の第 14 問の回答欄 | `p11-pre-add-questions-2.R2` |
| `template:claim_request#q15` | 追加前の 25 問の第 15 問の回答欄 | `p11-pre-add-questions-2.R3` |
| `template:claim_request#q16` | 追加前の 25 問の第 16 問の回答欄 | `p11-pre-add-questions-2.R4` |
| `template:claim_request#q17` | 追加前の 25 問の第 17 問の回答欄 | `p11-pre-add-questions-2.R5` |
| `template:claim_request#q18` | 追加前の 25 問の第 18 問の回答欄 | `p11-pre-add-questions-2.R6` |
| `template:claim_request#q19` | 追加前の 25 問の第 19 問の回答欄 | `p11-pre-add-questions-2.R7` |
| `template:claim_request#q20` | 追加前の 25 問の第 20 問の回答欄 | `p11-pre-add-questions-2.R8` |
| `template:claim_request#q21` | 追加前の 25 問の第 21 問の回答欄 | `p11-pre-add-questions-2.R9` |
| `template:claim_request#q22` | 追加前の 25 問の第 22 問の回答欄 | `p11-pre-add-questions-2.R10` |
| `template:claim_request#q23` | 追加前の 25 問の第 23 問の回答欄 | `p11-pre-add-questions-2.R11` |
| `template:claim_request#q24` | 追加前の 25 問の第 24 問の回答欄 | `p11-pre-add-questions-2.R12` |
| `template:claim_request#q25` | 追加前の 25 問の第 25 問の回答欄 | `p11-pre-add-questions-2.R13` |
| `template:claim_request#gate` | 答えられない問いが残るなら共有クレームにせずローカルな属性にとどめる判定 | `p11-pre-add-questions-1.R13` |

## #5（86 件）

| 成果物 | 内容 | 使う要件 |
| --- | --- | --- |
| `review:perspectives#q-shared-validator` | 全受け手が組織共通の検証部品で検証し、独自の読み方をしていないか | `p00-why-hard.R2`, `p01-library-defaults.R4` |
| `review:perspectives#q-payload-readable` | 署名つき JWT のペイロードは持つ者・経由する全ホップが読めることを前提に、載せる値を選んでいるか | `p01-jwt-structure.R2` |
| `review:perspectives#q-validate-before-read` | 受け入れの確認（署名・iss・aud・exp・typ）を終える前に独自クレームを読む実装がないか | `p01-validation-order.R9`, `p01-attack-patterns.R7` |
| `review:perspectives#q-auth-context-semantics` | iat を認証時刻に、amr の mfa を保証の水準に、sid をアプリのセッション ID に使っていないか | `p02-registered-claims.R4`, `p02-auth-strength-session.R2`, `p02-auth-strength-session.R3`, `p08-reissue-triggers.R5` |
| `review:perspectives#q-registered-synonym` | 登録クレームや台帳の既存クレームと同じ意味の独自クレームを、別名で作っていないか | `p02-registered-claims.R7`, `p02-name-categories.R3`, `p02-check-before-creating.R5` |
| `review:perspectives#q-identifier-choice` | 識別のキーが iss＋sub か組織の不変 ID で、email・upn・ペアワイズの sub の突き合わせ・sub_id と sub の組み合わせを使っていないか | `p02-user-identifier.R1`, `p02-user-identifier.R3`, `p02-user-identifier.R4`, `p02-user-identifier.R5` |
| `review:perspectives#q-value-vocabulary` | roles・groups などの値が、受け手・IdP をまたいで同じ意味だと仮定していないか（語彙が台帳にあるか） | `p02-roles-groups-entitlements.R3` |
| `review:perspectives#q-scope-semantics` | scope を利用者の全権限と読んでいないか。各スコープが aud のリソースで意味を持ち、同じ API で scope と authorization_details を併用していないか | `p02-scope.R1`, `p02-scope.R2`, `p02-scope.R4`, `p02-scope.R6` |
| `review:perspectives#q-reuse-standard-structure` | cnf・txn・verified_claims など既存の構造で表せるものを、独自のクレームで作り直していないか | `p02-keys-events-identity-assurance.R1`, `p02-keys-events-identity-assurance.R3`, `p02-keys-events-identity-assurance.R4` |
| `review:decision_tree#rar-vs-custom` | 取引単位の権限 → authorization_details の type で表せるか（独自の権限オブジェクトより先に検討） | `p02-scope.R3` |
| `review:decision_tree#existing-claim-first` | 用途から既存のクレームを探す分岐（16 の用途の地図、登録簿にない用途の代わりの手段） | `p02-claims-by-purpose（教材）`, `p02-not-in-registry（教材）` |
| `review:decision_tree#carry-or-query` | 判断の木：載せるか問い合わせるか（4 つの問い） | `p04-carry-or-query.R5` |
| `review:perspectives#q-consumer-expression` | 受け手の式で、変換せず完全一致で比べ、真偽値を true と明示的に比べ、欠落時に通す既定値を使っていないか | `p04-shape.R4`, `p04-case-and-characters.R3` |
| `review:perspectives#q-original-principal` | 認可が元の利用者の権限で行われ、仲介するサービスの権限で行われていないか | `p05-one-request-carries.R3`, `p05-confused-deputy.R3` |
| `review:perspectives#q-validity-not-authz` | トークンが有効かどうかだけで認可していないか | `p05-pep-pdp.R3` |
| `review:perspectives#q-object-level-authz` | オブジェクトの持ち主・テナントとの照合を、データを取るときにデータの側で行っているか（ゲートウェイ・WAF に頼っていないか） | `p05-bola.R2`, `p05-bola.R4`, `p06-validation-split.R5` |
| `review:perspectives#q-scope-and-role` | 受け手が scope と role の両方を確かめているか | `p05-scope-vs-role.R1` |
| `review:perspectives#q-role-explosion` | ロールの名前にテナント・対象の組み合わせを焼き込んでいないか | `p05-role-explosion.R1` |
| `review:perspectives#q-operator-act` | 運用者の操作が委任のトークン（sub と act）で行われ、両方が記録されているか | `p05-system-privileges.R3` |
| `review:perspectives#q-break-glass` | break-glass に承認の ID と短い期限があるか | `p05-system-privileges.R5` |
| `review:perspectives#q-cross-tenant-identity` | テナントをまたいだ暗黙の名寄せをしていないか、複合キーを使っているか | `p05-cross-tenant.R2` |
| `review:contrasts/scope-vs-role` | 対比表：scope と role（守る相手、トークンに入る範囲、IdP ごとの表し方） | `p05-scope-vs-role.R1` |
| `review:perspectives#q-hook-adds-raw-pii` | 発行時フックが生の個人情報を足していないか | `p06-issuance-hook.R4` |
| `review:perspectives#q-step-up-by-rs` | 高リスクの操作で、受け手が acr・auth_time を見て追加認証を求めるか | `p06-step-up-approval.R2` |
| `review:perspectives#q-rar-per-audience` | authorization_details を宛先ごとに絞っているか | `p06-step-up-approval.R3` |
| `review:perspectives#q-authorize-service-and-user` | 呼び出し元のサービスと利用者を、それぞれ認可しているか | `p06-validation-split.R7` |
| `review:perspectives#q-gateway-bypass-path` | 入口を通らない経路があるか。その経路でも検証しているか | `p06-validation-split.R8`, `p06-header-forwarding.R5` |
| `review:perspectives#q-access-context-from-pep` | アクセス元の文脈を、トークンのクレームでなく PEP が要求ごとに評価しているか | `p06-access-context.R1`, `p06-access-context.R4`, `p06-flow-checklist.R9`, `p09-do-not-carry.R6` |
| `review:perspectives#q-unverified-claim-extraction` | 署名を検証せずに取り出したクレームを認可に使っていないか | `p06-header-forwarding.R4` |
| `review:perspectives#q-trace-id-trust` | 監査に署名つきの txn を、観測に traceparent を使い分けているか | `p06-audit-trail.R4` |
| `review:perspectives#checklist-p06-flow` | Part 6 の流れの規則 10 項目（スライド 90）との対応 | `p06-flow-checklist.R1`, `p06-flow-checklist.R2`, `p06-flow-checklist.R3`, `p06-flow-checklist.R4`, `p06-flow-checklist.R5`, `p06-flow-checklist.R6`, `p06-flow-checklist.R7`, `p06-flow-checklist.R8`, `p06-flow-checklist.R9`, `p06-flow-checklist.R10` |
| `review:perspectives#checklist-p07-data-layer` | Part 7 のデータ層の規則 10 項目（スライド 101）との対応 | `p07-data-layer-checklist.R1`, `p07-data-layer-checklist.R2`, `p07-data-layer-checklist.R3`, `p07-data-layer-checklist.R4`, `p07-data-layer-checklist.R5`, `p07-data-layer-checklist.R6`, `p07-data-layer-checklist.R7`, `p07-data-layer-checklist.R8`, `p07-data-layer-checklist.R9`, `p07-data-layer-checklist.R10`, `p07-data-layer-checklist.R11` |
| `review:perspectives#q-db-context-writers` | DB の文脈を設定する主体以外が、同じ接続・取引で SQL を流せないか | `p07-three-db-paths.R3`, `p07-trust-boundary.R1` |
| `review:perspectives#q-sql-tenant-predicate` | 全 SQL にテナントの条件があることを、規約とレビューで確かめているか | `p07-trust-boundary.R2`, `p07-connect-as-whom.R3` |
| `review:perspectives#q-db-context-parameterized` | DB の文脈の値をパラメータで渡しているか | `p07-connection-pool.R4` |
| `review:perspectives#q-ddm-rls-only` | DDM・RLS だけで機微データを守っていないか。最小権限と監査を併用しているか | `p07-masking.R2`, `p07-data-layer-checklist.R10` |
| `review:perspectives#q-relies-on-at-expiry` | AT の期限を当てにした実装（期限で剥奪が効く前提など）がないか | `p08-choosing-lifetime.R3` |
| `review:perspectives#q-system-actor-no-fake-sub` | システム起因の処理をサービスの ID で動かし、利用者の sub を捏造していないか | `p08-downstream-after-expiry.R2` |
| `review:decision_tree#lifetime-by-situation` | 状況（公開クライアント・FAPI 機密・即時の剥奪・ワークロード・長時間ジョブ）から寿命・リフレッシュ・失効を選ぶ枝 | `p08-decision-table.R1`, `p08-decision-table.R2`, `p08-decision-table.R3`, `p08-decision-table.R4`, `p08-decision-table.R5`, `p08-decision-table.R6` |
| `review:perspectives#q-derived-value` | 観点書：値ではなく判定（派生値）で足りないか | `p09-minimize-derived.R1`, `p09-checklist.R2` |
| `review:perspectives#q-minimal-per-recipient` | 観点書：受け手ごとに必要なクレームだけを出しているか | `p09-minimize-derived.R4`, `p09-checklist.R4` |
| `review:perspectives#q-pairwise-external` | 観点書：外部の受け手にペアワイズの sub を使うか | `p09-pairwise-identifiers.R1`, `p09-pairwise-identifiers.R3`, `p09-checklist.R3` |
| `review:perspectives#q-no-secret-or-raw-pii` | 観点書：認証の秘密・平文の個人情報を載せていないか | `p09-checklist.R1` |
| `review:perspectives#q-nested-jwt-both-layers` | 観点書：暗号化するなら、ネストの両方の層を検証するか | `p09-checklist.R5` |
| `review:perspectives#q-token-not-in-url` | 観点書：URL・クエリにトークンを載せていないか | `p09-checklist.R6` |
| `review:perspectives#q-token-logging` | 観点書：ログ・トレースにトークン全文を出さず、記録するヘッダーを許可リストにしているか | `p09-checklist.R7`, `p09-checklist.R8`, `p12-antipatterns-2.R8` |
| `review:perspectives#q-audit-log-protected` | 観点書：監査ログ自体を機微な情報として守るか | `p09-checklist.R9` |
| `review:perspectives#q-agent-own-identity` | 観点書：エージェントを独立した ID として登録し、利用者のトークンを借りていないか | `p10-agent-identity.R1`, `p10-agent-identity.R3`, `p10-agent-checklist.R1`, `p12-antipatterns-2.R7` |
| `review:perspectives#q-agent-delegation-claims` | 観点書：sub＝利用者、act・client_id＝エージェントで分けたか | `p10-agent-checklist.R2` |
| `review:perspectives#q-single-aud-resource` | 観点書：resource で要求し、aud を 1 つに絞ったか | `p10-agent-checklist.R3` |
| `review:perspectives#q-no-passthrough` | 観点書：受け取ったトークンを上流に渡していないか。交換の宛先・範囲を組織で決めたか | `p10-agent-checklist.R4`, `p12-antipatterns-2.R6` |
| `review:perspectives#q-scope-elevation-logged` | 観点書：ツールごとの最小スコープで、昇格を相関 ID つきで記録するか | `p10-per-tool-scopes.R3`, `p10-agent-checklist.R5` |
| `review:perspectives#q-agent-short-lived-no-rt` | 観点書：タスク単位の短命トークンで、RT を出さないか | `p10-agent-checklist.R6` |
| `review:perspectives#q-approval-from-as` | 観点書：機微な操作の承認を AS が本人に確かめ、受け手が照合するか | `p10-human-approval-evidence.R1`, `p10-agent-checklist.R7` |
| `review:perspectives#q-delegation-depth-and-revocation` | 観点書：委任の深さの上限と、根元からの一括失効を決めたか | `p10-agent-checklist.R8` |
| `review:perspectives#q-audit-correlation` | 観点書：sub・全アクター・txn・承認 ID を監査で相関できるか | `p10-agent-checklist.R9` |
| `review:perspectives#q-internal-delegation-token` | 観点書：内部の代理トークンが署名・テナントの検証・失効・ログを備えるか（CVE-2025-55241 の逆） | `p00-incident-signature-valid.R2`, `p10-delegation-chain-depth.R5`, `p12-antipatterns-2.R9` |
| `review:perspectives#q-change-order` | 観点書：形式の変更が「受け手が先、発行者が後」の順で、通知・プレビュー・並行発行があるか | `p11-why-govern.R1`, `p11-change-procedure.R1`, `p11-why-govern（教材）` |
| `review:perspectives#q-idp-diff-absorbed` | 観点書：IdP の差（利用者キー・ロールの位置・aud）を入口か共通部品で吸収し、製品の独自クレームを契約にしていないか | `p10-vendor-features.R1`, `p11-translation-layer.R1`, `p11-translation-layer.R5` |
| `review:perspectives#q-no-unverified-passthrough-mode` | 観点書：未検証の値を流すモード（検証の無効化・デバッグ）が無いか | `p11-pre-add-questions-2.R6` |
| `review:perspectives#q-baseline-kept` | 観点書：共通の基準を外していないか | `p12-priorities-deferrals.R1` |
| `review:perspectives#stage-definition` | 観点書：レビューの段：定義 | `p12-review-viewpoints.R1`, `p12-review-viewpoints.R2`, `p12-review-viewpoints.R3`, `p12-review-viewpoints.R19` |
| `review:perspectives#stage-issuance` | 観点書：レビューの段：発行 | `p12-review-viewpoints.R4`, `p12-review-viewpoints.R5`, `p12-review-viewpoints.R6` |
| `review:perspectives#stage-propagation` | 観点書：レビューの段：伝搬 | `p12-review-viewpoints.R7`, `p12-review-viewpoints.R8`, `p12-review-viewpoints.R9` |
| `review:perspectives#stage-validation` | 観点書：レビューの段：検証 | `p12-review-viewpoints.R10`, `p12-review-viewpoints.R11`, `p12-review-viewpoints.R12` |
| `review:perspectives#stage-authorization` | 観点書：レビューの段：認可 | `p12-review-viewpoints.R13`, `p12-review-viewpoints.R14`, `p12-review-viewpoints.R15` |
| `review:perspectives#stage-operations` | 観点書：レビューの段：運用 | `p12-review-viewpoints.R16`, `p12-review-viewpoints.R17`, `p12-review-viewpoints.R18` |
| `review:perspectives#pre-add-questions` | 観点書：追加・変更する共有クレームに追加前の 25 問の回答がそろい、回答が妥当か（スライド 142・143） | `p11-pre-add-questions-1.R1`, `p11-pre-add-questions-1.R2`, `p11-pre-add-questions-1.R3`, `p11-pre-add-questions-1.R4`, `p11-pre-add-questions-1.R5`, `p11-pre-add-questions-1.R6`, `p11-pre-add-questions-1.R7`, `p11-pre-add-questions-1.R8`, `p11-pre-add-questions-1.R9`, `p11-pre-add-questions-1.R10`, `p11-pre-add-questions-1.R11`, `p11-pre-add-questions-1.R12`, `p11-pre-add-questions-1.R13`, `p11-pre-add-questions-2.R1`, `p11-pre-add-questions-2.R2`, `p11-pre-add-questions-2.R3`, `p11-pre-add-questions-2.R4`, `p11-pre-add-questions-2.R5`, `p11-pre-add-questions-2.R6`, `p11-pre-add-questions-2.R7`, `p11-pre-add-questions-2.R8`, `p11-pre-add-questions-2.R9`, `p11-pre-add-questions-2.R10`, `p11-pre-add-questions-2.R11`, `p11-pre-add-questions-2.R12`, `p11-pre-add-questions-2.R13`, `p11-pre-add-questions-2.R14` |
| `review:perspectives#design-checklist` | 観点書：設計のチェックリスト 12 項目（スライド 61）に、載せる独自クレームごとに答えているか | `p04-design-checklist.R1`, `p04-design-checklist.R2`, `p04-design-checklist.R3`, `p04-design-checklist.R4`, `p04-design-checklist.R5`, `p04-design-checklist.R6`, `p04-design-checklist.R7`, `p04-design-checklist.R8`, `p04-design-checklist.R9`, `p04-design-checklist.R10`, `p04-design-checklist.R11`, `p04-design-checklist.R12`, `p04-design-checklist.R13` |
| `review:perspectives#ap-1-1` | 観点書：アンチパターン 1-1（トークンの alg に従って検証しない。許可リストで鍵ごとに 1 つに固定する） | `p12-antipatterns-1.R1` |
| `review:perspectives#ap-1-2` | 観点書：アンチパターン 1-2（署名を確かめずに中身で認可しない。必ず検証してから読む） | `p12-antipatterns-1.R2` |
| `review:perspectives#ap-1-3` | 観点書：アンチパターン 1-3（aud を確かめないことを避け、aud を必須にして自分宛てか確認する） | `p12-antipatterns-1.R3` |
| `review:perspectives#ap-1-4` | 観点書：アンチパターン 1-4（マルチテナントで iss・tid を見ないことを避け、発行者とテナントの許可リストで照合する） | `p12-antipatterns-1.R4` |
| `review:perspectives#ap-1-5` | 観点書：アンチパターン 1-5（署名が通れば発行者も正しいと仮定せず、鍵と発行者の対応を確かめる） | `p12-antipatterns-1.R5` |
| `review:perspectives#ap-1-6` | 観点書：アンチパターン 1-6（email・upn を利用者のキーにせず、iss＋sub（Entra は tid＋oid）を使う） | `p12-antipatterns-1.R6` |
| `review:perspectives#ap-1-7` | 観点書：アンチパターン 1-7（本人が書ける属性から権限のクレームを作らない） | `p12-antipatterns-1.R7` |
| `review:perspectives#ap-1-8` | 観点書：アンチパターン 1-8（exp を必須にせず、時刻のずれを大きく許すことを避ける（ずれは数分まで）） | `p12-antipatterns-1.R8` |
| `review:perspectives#ap-2-1` | 観点書：アンチパターン 2-1（グループ・ロールを全部トークンに詰めず、粗いロールだけにして細かい権限は PDP に置く） | `p12-antipatterns-2.R1` |
| `review:perspectives#ap-2-2` | 観点書：アンチパターン 2-2（変わりやすい権限を焼き込まず、短命化・都度判定・失効の伝播で対処する） | `p12-antipatterns-2.R2` |
| `review:perspectives#ap-2-3` | 観点書：アンチパターン 2-3（型を決めない・配列を区切り文字列にすることを避け、台帳で型を 1 つに固定する） | `p12-antipatterns-2.R3` |
| `review:perspectives#ap-2-4` | 観点書：アンチパターン 2-4（名前空間なしの独自クレームを作らない） | `p12-antipatterns-2.R4` |
| `review:perspectives#ap-2-5` | 観点書：アンチパターン 2-5（クレームをヘッダーに移すとき、同名ヘッダーを消さないことを避け、入口で除去してから書き込む） | `p12-antipatterns-2.R5` |
| `review:perspectives#ap-2-6` | 観点書：アンチパターン 2-6（受け取ったトークンを上流へそのまま渡さず、宛先ごとに交換する） | `p12-antipatterns-2.R6` |
| `review:perspectives#ap-2-7` | 観点書：アンチパターン 2-7（エージェントが利用者のトークンを借りず、act で委任を表す） | `p12-antipatterns-2.R7` |
| `review:perspectives#ap-2-8` | 観点書：アンチパターン 2-8（トークン全文をログに出さず、種別・発行者・ハッシュだけを残す） | `p12-antipatterns-2.R8` |
| `review:perspectives#ap-2-9` | 観点書：アンチパターン 2-9（署名がなく、取り消せず、ログも残らない内部の代理トークンを作らない） | `p12-antipatterns-2.R9` |

## #6（36 件）

| 成果物 | 内容 | 使う要件 |
| --- | --- | --- |
| `lint:L24` | 値の種類ごとの型の規則に反する（ID・金額は文字列で 2^53 を超えうる number にしない、時刻は NumericDate、真偽は boolean、複数値は配列）（仮称 type-by-kind） | `p00-why-hard.R4`, `p04-type.R2`, `p04-type.R3`, `p04-type.R4`, `p04-type.R5`, `p04-type.R6`, `p04-absent-null-false-empty.R5`, `p04-design-checklist.R5`, `p11-contract-test-gaps.R2`, `p11-pre-add-questions-1.R8` |
| `lint:L25` | token_types の key_source が、許可リストなしの jku・x5u の追跡や、ヘッダーの jwk・x5c の信頼を含めば error（仮称 header-key-params） | `p01-dangerous-header-params.R4`, `p01-dangerous-header-params.R5` |
| `lint:L27` | required_claims に exp・aud・iss が無い、または max_clock_skew が無いか上限（例 300 秒）を超える（仮称 required-exp-and-skew） | `p01-attack-patterns.R5`, `p12-antipatterns-1.R8` |
| `lint:L28` | usage が identifier のキーに sub を単独で使い、iss と組にしていなければ error（仮称 identifier-pairs-iss） | `p00-incident-signature-valid.R3`, `p02-registered-claims.R2`, `p02-user-identifier.R1` |
| `lint:L29` | tenant_binding がテナントのクレームだけで、aud・iss・鍵の分離のどれとも重ねていなければ warn（仮称 tenant-binding-layered） | `p02-tenant-org.R2` |
| `lint:L30` | act の中に識別以外のクレーム（権限・exp・aud・独自クレーム）を入れる宣言があれば error（仮称 act-identity-only） | `p02-delegation-client.R2`, `p02-delegation-client.R4` |
| `lint:L31` | usage が authz のクレーム（または STS のタグ・DB の文脈）の provenance が、呼び出し側の申告か本人が編集できる値（仮称 provenance-authz） | `p03-cognito-pre-token-hook.R4`, `p04-split-by-writer.R2`, `p04-split-by-writer.R3`, `p04-namespace-object-example.R3`, `p07-three-db-paths.R4`, `p07-row-level-security.R2`, `p07-cloud-attributes.R1`, `p07-data-layer-checklist.R4`, `p12-antipatterns-1.R7`, `p12-review-viewpoints.R15` |
| `lint:L32` | 入口より内側の受け手が、外部 IdP 固有のクレーム（組織の名前空間・内部発行者以外）を読んでいる（仮称 internal-reads-org-claims） | `p03-confusing-differences.R1`, `p03-absorb-idp-differences.R4` |
| `lint:L33` | 上限で欠落・切り捨て・置き換えが起きうるクレームを usage authz に使っている（仮称 truncatable-not-authz） | `p03-confusing-differences.R3`, `p04-absent-null-false-empty.R4`, `p04-size-budget.R3`, `p11-why-govern.R2` |
| `lint:L34` | クレーム名が IdP・受け手の基盤の予約名・予約接頭辞の一覧（出典と確認日つき）と衝突している（仮称 reserved-name-collision） | `p04-claim-names.R3`, `p04-design-checklist.R3`, `p11-why-govern.R2`, `p11-reserved-names.R1`, `p11-reserved-names.R4`, `p11-pre-add-questions-1.R4` |
| `lint:L35` | 「.」を含む名前を、ドット区切りで解釈する受け手のツールの参照式で読んでいる（仮称 dotted-name-tool） | `p04-namespace.R3` |
| `lint:L36` | 区切り文字の連結、scope 以外の空白区切り、JSON の文字列化、文字列の真偽を使っている（理由の記載がない）（仮称 shape-no-concat） | `p04-shape.R1`, `p04-shape.R2`, `p04-shape.R3`, `p04-design-checklist.R6` |
| `lint:L37` | effect が許可のクレームで無いときに許す、制限のクレームで無いときに拒否しない（仮称 absent-semantics） | `p04-absent-null-false-empty.R2`, `p04-absent-null-false-empty.R3` |
| `lint:L38` | 識別子のクレームに value_normalization がない、または小文字 ASCII 以外を許している（仮称 value-normalization） | `p04-case-and-characters.R1` |
| `lint:L39` | 利用者とクライアントの sub が重なりうるトークン種別に、subject_kind の区別の手段がない（仮称 subject-kind） | `p05-three-principals.R2`, `p05-system-privileges.R2` |
| `lint:L40` | roles の値の語彙に、テナント ID・対象 ID を含む組み合わせの名前がある（仮称 role-name-combinatorial） | `p05-role-explosion.R1` |
| `lint:L41` | 入口より内側のホップの carried_in に外部のトークン種別がある、または受け取ったトークンを交換せずに aud の異なる次のホップへ渡す（仮称 token-passthrough） | `p05-confused-deputy.R4`, `p06-stage-map.R6`, `p06-edge-exchange.R1`, `p06-narrow-downstream.R5`, `p06-flow-checklist.R3`, `p06-flow-checklist.R4`, `p10-mcp-authorization.R3`, `p10-agent-checklist.R4`, `p12-antipatterns-2.R6`, `p12-review-viewpoints.R8` |
| `lint:L42` | 段階ごとに足してはいけない内容（認証時に業務の権限、フックに秒単位で変わる値・生の個人情報、承認していない操作）を書いている（仮称 stage-content） | `p06-stage-map.R3`, `p06-stage-map.R4`, `p06-stage-map.R7` |
| `lint:L43` | Txn-Token を Authorization ヘッダーで送る・AT として受け入れる・外部の AT を含めると宣言している（仮称 txn-token-transport） | `p06-transaction-tokens.R1`, `p06-transaction-tokens.R2`, `p06-flow-checklist.R6` |
| `lint:L44` | Txn-Token の作り直しのホップで txn・sub・aud・tctx が変わる、または書き手が TTS 以外（仮称 txn-immutable） | `p06-transaction-tokens.R5`, `p06-flow-multitenant-saas.R3` |
| `lint:L45` | トークン種別の log_policy が全文の記録を許す、ログの許可リストがない、またはログの出力設定に Authorization・トークン全文が現れる（仮称 full-token-logged） | `p06-transaction-tokens.R7`, `p06-audit-trail.R6`, `p06-flow-checklist.R10`, `p09-logs-traces.R1`, `p09-logs-traces.R2`, `p09-checklist.R7`, `p11-audit-metrics.R8`, `p12-antipatterns-2.R8`, `p12-review-viewpoints.R17` |
| `lint:L46` | 入口の背後のホップの受け手が、署名・iss・exp・aud の検証を宣言していない（入口任せ）（仮称 hop-validation-missing） | `p06-validation-split.R1`, `p06-flow-checklist.R7` |
| `lint:L47` | 利用者の AT・RT の stored_at にキュー・ジョブの DB・ワーカーがある（仮称 token-in-queue） | `p06-flow-partner-events.R4`, `p08-async-processing.R1`, `p08-downstream-after-expiry.R1`, `p08-decision-table.R6` |
| `lint:L48` | privilege_level が DB の権限・マスキングを選ぶクレームで、issuers が 1 つに限定されていない、または名前空間がない（仮称 db-role-claim） | `p07-trust-boundary.R4`, `p07-masking.R1`, `p07-data-layer-checklist.R5` |
| `lint:L49` | DB・ブローカーの接続の最大寿命が、接続を開いたトークンの max_lifetime を超えている（仮称 connection-outlives-token） | `p07-lifetime-mismatch.R1`, `p07-data-layer-checklist.R8`, `p08-copies-outlive-token.R1` |
| `lint:L50` | pii_category が個人情報以上のクレームが、JWE でないトークンに載り、運搬経路（ゲートウェイ・ログ・トレース）を経由する（ブラウザ以外も対象。L6 の拡張）（仮称 pii-in-jws） | `p09-jws-is-readable.R1`, `p09-jws-is-readable.R3`, `p09-do-not-carry.R2` |
| `lint:L51` | 認証の秘密（パスワード・API キー・資格情報）・要配慮個人情報・平文の個人情報の区分のクレームがトークンに載っている（仮称 secret-or-raw-pii-in-token） | `p08-copies-outlive-token.R3`, `p09-do-not-carry.R1`, `p09-minimize-derived.R3`, `p09-checklist.R1` |
| `lint:L52` | sub の値の源がメール・社員番号など平文の個人情報（仮称 sub-plaintext-pii） | `p09-do-not-carry.R3` |
| `lint:L53` | SD-JWT で iss・aud・exp・cnf を選択的開示にしている、または鍵束縛がない（仮称 sd-jwt-rules） | `p09-jwe-sd-jwt.R3`, `p09-jwe-sd-jwt.R4` |
| `lint:L54` | transport に URL のクエリ・フラグメントがある（仮称 token-in-url） | `p09-url-browser.R1`, `p09-checklist.R6` |
| `lint:L56` | 交換・エージェント・MCP のホップで aud が 1 つでない（仮称 single-aud） | `p10-four-questions.R4`, `p10-per-tool-scopes.R4`, `p10-agent-checklist.R3` |
| `lint:L57` | ワイルドカード・包括的なスコープを宣言している（仮称 wildcard-scope） | `p10-per-tool-scopes.R1`, `p10-agent-checklist.R5` |
| `lint:L58` | エージェント・交換のトークン種別で RT を出す、または寿命がタスク単位の上限を超える（仮称 agent-token-refresh） | `p10-per-tool-scopes.R5`, `p10-agent-checklist.R6` |
| `lint:L59` | 委任のあるトークン種別に max_delegation_depth がない、または経路の深さが上限を超える（仮称 delegation-depth） | `p10-delegation-chain-depth.R1`, `p10-agent-checklist.R8`, `p12-priorities-deferrals.R6` |
| `lint:L61` | 発行の設定（マッパー・フック）に台帳に無いクレーム名がある（仮称 issuer-config-unregistered） | `p11-reserved-names.R4`, `p12-review-viewpoints.R3` |
| `lint:L72` | claim_request の 25 問に未回答がある共有クレーム（仮称 claim-request-complete） | `p11-pre-add-questions-1.R1`, `p11-pre-add-questions-1.R2`, `p11-pre-add-questions-1.R3`, `p11-pre-add-questions-1.R4`, `p11-pre-add-questions-1.R5`, `p11-pre-add-questions-1.R6`, `p11-pre-add-questions-1.R7`, `p11-pre-add-questions-1.R8`, `p11-pre-add-questions-1.R9`, `p11-pre-add-questions-1.R10`, `p11-pre-add-questions-1.R11`, `p11-pre-add-questions-1.R12`, `p11-pre-add-questions-1.R13`, `p11-pre-add-questions-2.R1`, `p11-pre-add-questions-2.R2`, `p11-pre-add-questions-2.R3`, `p11-pre-add-questions-2.R4`, `p11-pre-add-questions-2.R5`, `p11-pre-add-questions-2.R6`, `p11-pre-add-questions-2.R7`, `p11-pre-add-questions-2.R8`, `p11-pre-add-questions-2.R9`, `p11-pre-add-questions-2.R10`, `p11-pre-add-questions-2.R11`, `p11-pre-add-questions-2.R12`, `p11-pre-add-questions-2.R13`, `p11-pre-add-questions-2.R14` |

## #8（32 件）

| 成果物 | 内容 | 使う要件 |
| --- | --- | --- |
| `test:negative_tests#revoked-token-rejected` | 失効（剥奪・ログアウト・SSF/CAEP のイベント）を受け取った受け手が、そのトークンを拒否し、セッションを終えることを確かめる | `p08-revocation-propagation.R2` |
| `test:negative_tests#untrusted-key` | 設定外の鍵、または別の発行者の鍵で正しく署名したトークンが拒否される | `p00-incident-signature-valid.R1`, `p01-validation-order.R3`, `p01-key-rotation-jwks.R1`, `p12-antipatterns-1.R5` |
| `test:negative_tests#iss-mismatch` | iss が想定と完全一致しない（部分一致・末尾のスラッシュ違いを含む）トークンが拒否される | `p01-validation-order.R4`, `p02-registered-claims.R1` |
| `test:negative_tests#nbf-future` | nbf が未来のトークン、許容を超えた時刻のずれのトークンが拒否される | `p01-validation-order.R6` |
| `test:negative_tests#missing-required` | exp・aud・iss など必須クレームを欠いたトークンが拒否され、文字列と配列の aud がどちらも正しく扱われる | `p01-validation-order.R8`, `p01-library-defaults.R2`, `p03-cognito-token-use.R3`, `p03-confusing-differences.R4` |
| `test:negative_tests#alg-confusion` | RS256 の公開鍵を HMAC の鍵にした HS256 の署名（アルゴリズムの混同）が拒否される | `p01-dangerous-header-params.R2`, `p01-attack-patterns.R1`, `p12-antipatterns-1.R1` |
| `test:negative_tests#jku-x5u` | jku・x5u で攻撃者の鍵の場所を指したトークンが拒否され、その URL が取得されない | `p01-dangerous-header-params.R4` |
| `test:negative_tests#embedded-jwk` | ヘッダーの jwk・x5c に埋め込んだ自前の鍵で署名したトークンが拒否される | `p01-dangerous-header-params.R5` |
| `test:negative_tests#tenant-mismatch` | 別テナントのトークン（発行者・鍵・テナントのクレーム）や、URL・ヘッダーのテナント ID とトークンのテナントが食い違う要求が拒否される | `p00-incident-signature-valid.R2`, `p01-attack-patterns.R3`, `p02-tenant-org.R3`, `p05-multitenancy.R3`, `p05-multitenancy.R6`, `p06-flow-multitenant-saas.R2`, `p08-reissue-triggers.R1`, `p12-antipatterns-1.R4` |
| `test:negative_tests#duplicate-claim` | 同名のクレームが重複したトークンが拒否される | `p01-attack-patterns.R6` |
| `test:negative_tests#disabled-subject-exchange` | 無効にした利用者のトークンを交換しても、新しいトークンが出ない（CVE-2025-14559 の型） | `p03-keycloak-aud-lightweight.R5` |
| `test:consumer_contract#issued-claims-present` | 実際に発行したトークンに、台帳で宣言した独自クレームが名前・型どおりに全部入っている（黙った欠落の検出） | `p03-entra-scp-roles-groups.R4`, `p03-auth0-namespace.R2` |
| `test:negative_tests#missing-required-claim` | 必須の独自クレームが欠けたトークン（フックの打ち切りを模擬）が拒否される | `p03-custom-claim-injection.R1`, `p03-absorb-idp-differences.R5`, `p04-absent-null-false-empty.R3`, `p04-forward-compatibility.R2`, `p04-reject-missing-required.R4`, `p06-grant-types.R4` |
| `test:negative_tests#legit-idp-variants-accepted` | IdP ごとの形の正規の要求（groups の超過、aud の代わりの client_id）が入口の正規化を経て受理される（誤拒否の確認） | `p04-reject-missing-required.R4` |
| `test:negative_tests#case-variant` | 大文字小文字だけが違う値のトークンが、別の値として扱われる（照合に通らない） | `p04-case-and-characters.R3` |
| `test:negative_tests#bola-other-owner` | 利用者 A のトークンで利用者 B のオブジェクト ID を指定した要求が拒否される（クレームでなく DB で持ち主を照合） | `p05-bola.R5`, `p06-validation-split.R5`, `p12-review-viewpoints.R13` |
| `test:negative_tests#rar-unknown-type` | 知らない type・フィールドを含む authorization_details の要求が発行者に拒否される | `p05-coarse-fine-layers.R3` |
| `test:consumer_contract#tool-access-path` | 受け手のツールの参照式で、名前空間のクレームを読めることを確かめる | `p04-namespace.R2` |
| `test:consumer_contract#type-shape-match` | 実際に発行したトークンのクレームの型と形が台帳と一致する | `p04-type.R1` |
| `test:consumer_contract#unknown-claim-ignored` | 未知のクレームを足したトークンを受け手が拒否せず、無視する | `p04-forward-compatibility.R1` |
| `test:negative_tests#txn-token-as-at` | Authorization ヘッダーで送った Txn-Token が拒否される | `p06-transaction-tokens.R2` |
| `test:negative_tests#txn-remint-immutable` | 作り直しで txn・sub・aud を変えた、または scope を広げた Txn-Token が拒否される | `p06-transaction-tokens.R5` |
| `test:negative_tests#insufficient-acr` | acr・auth_time が操作の要求を満たさないトークンに insufficient_user_authentication が返る | `p06-step-up-approval.R1` |
| `test:negative_tests#spoofed-identity-header` | クライアントが送った同名の ID 系ヘッダー（大文字小文字・_ と - の変種・重複を含む）が入口で除去・拒否される | `p06-header-forwarding.R1`, `p06-header-forwarding.R2`, `p06-header-forwarding.R3`, `p11-pre-add-questions-2.R5`, `p12-antipatterns-2.R5` |
| `test:negative_tests#db-context-override` | 同じ接続で DB の文脈（SESSION_CONTEXT・SET ROLE）を上書きしようとして失敗する | `p07-trust-boundary.R3`, `p07-data-layer-checklist.R11` |
| `test:negative_tests#pool-context-leak` | 接続プールで前の要求のテナントの文脈が次の要求に残らない | `p07-connection-pool.R2`, `p07-connection-pool.R3`, `p07-data-layer-checklist.R2`, `p07-data-layer-checklist.R11` |
| `test:negative_tests#rt-reuse` | 無効にした RT の再提示で、系列の有効な RT も失効する | `p08-rotation.R3` |
| `test:negative_tests#push-delivery-identity` | aud や送信元のアカウントが期待と違う push 配送が拒否される | `p06-flow-partner-events.R5`, `p08-async-processing.R5` |
| `test:negative_tests#nested-inner-unsigned` | 拒否されるべき：ネストした JWT で内側の署名が不正・欠けているトークン | `p09-jwe-sd-jwt.R2`, `p09-checklist.R5` |
| `test:negative_tests#approval-mismatch` | 拒否されるべき：承認された authorization_details と要求の内容（金額・相手先）が食い違うリクエスト | `p10-human-approval-evidence.R3`, `p10-agent-checklist.R7` |
| `test:negative_tests#passthrough-rejected` | 拒否されるべき：MCP サーバー宛てのトークンをそのまま上流 API に送ると拒否される | `p10-mcp-authorization.R3` |
| `test:consumer_contract#format-change-cases` | 契約テストが見逃しやすい変更（区切り文字・大文字化・2^53 超の数値・null／false・真偽値の文字列化・制限のクレームの追加）のケース | `p11-contract-test-gaps.R1`, `p11-contract-test-gaps.R2` |

## #18（3 件）

| 成果物 | 内容 | 使う要件 |
| --- | --- | --- |
| `lint:L26` | consumers に API がいるのに carried_in が ID トークンだけ、または ID トークンだけが読むクレームを AT に載せる宣言の不整合（仮称 carried-in-matches-consumers） | `p01-id-token-vs-access-token.R4` |
| `lint:L55` | 呼び出し元がエージェントのホップで、act・client_id でエージェントを表していない（なりすまし）（仮称 agent-delegation-without-act） | `p10-agent-identity.R2`, `p10-agent-identity.R3`, `p10-agent-checklist.R2`, `p12-antipatterns-2.R7` |
| `lint:L60` | 制限のクレームに、全受け手の enforced_at がない（仮称 restrictive-claim-unenforced） | `p11-contract-test-gaps.R4`, `p11-pre-add-questions-2.R7` |

## #21（1 件）

| 成果物 | 内容 | 使う要件 |
| --- | --- | --- |
| `deferred:data-platform-modules` | クラウドの DB・データ基盤ごとのモジュール（Azure SQL・RDS・Cloud SQL・Snowflake・Kafka・AWS STS・GCP WIF） | `p07-db-token-auth.R4`, `p07-cloud-attributes.R3` |
