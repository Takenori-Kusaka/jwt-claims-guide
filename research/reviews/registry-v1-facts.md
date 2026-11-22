# 台帳 v1（#3）：独立点検のための事実の一覧

この文書は、#3（台帳 v1）の成果物に含まれる事実を、別のセッション（会話の履歴を引き継がないもの）が点検するための一覧です。**作成者は自分で正しいとは判定していません**（`templates/CONTRIBUTING.md` の 3.）。点検の結果は、この一覧の各行に区分（誤り・過大・不一致・曖昧）を付けた記録として、別のファイル（`research/reviews/registry-v1-<日付>.md`）に書きます。

- 作成：2026-11-22、生成AI（Claude）。人による点検は未実施。別の LLM のセッションでの点検も未実施
- 対象のブランチ：`issue-3-registry-v1`（PR「クレーム台帳 v1 (#3)」）
- 点検者に渡すもの：この一覧、#3 の本文とコメント、下の各行の「確かめ先」。渡さないもの：作成者の結論（「正しいことを確かめて」の形の指示）

## 1. 一次資料の節と中身（成果物が根拠として引いているもの）

| # | 主張 | 使っている場所 | 確かめ先 |
| --- | --- | --- | --- |
| F01 | RFC 9449 §4.2 は DPoP proof の構文、§4.3 は proof の確認の手順（htm・htu・iat・jti・ath を含む） | `issuance_effects.yaml` E-dpop | https://www.rfc-editor.org/rfc/rfc9449 |
| F02 | RFC 9449 §6.1 は `cnf` の `jkt`（JWK Thumbprint）、§7.1 は `DPoP` の認証方式、§11.1 は proof の再送 | E-dpop、README 3.2 `jti_policy`、questions.yaml q-holder | 同上 |
| F03 | RFC 8705 §3.1 は `cnf` の `x5t#S256`、§6.5 は TLS の終端、§2 はクライアント認証 | E-mtls・E-mtls-entry、README 3.3 | https://www.rfc-editor.org/rfc/rfc8705 |
| F04 | RFC 9396 §2 は `authorization_details` と `type`、§9.1 は「JWT の AT には、宛先で絞った authorization details を入れることを RECOMMENDED」 | E-rar、hops.schema.json `authorization_details`、questions.yaml q-authorized | https://www.rfc-editor.org/rfc/rfc9396 |
| F05 | RFC 9700 §2.2.2 は「公開クライアントの RT は送信者制約かローテーション（MUST）」、§4.14.2 は送信者制約の RT とローテーションを、公開クライアントの再送の検知の手段として挙げる。機密クライアントにはローテーションを課していない | E-public-no-sender-constraint、E-rt-sender-constrained、README 3.2・7. | https://www.rfc-editor.org/rfc/rfc9700 |
| F06 | RFC 9700 §2.1.1 は公開クライアントに PKCE を求める | E-public-pkce | 同上 |
| F07 | RFC 7662 §4 は、応答をキャッシュする場合の注意（キャッシュの期間と失効の反映のトレードオフ）を述べる。「応答の exp を超えてキャッシュしない」は §4 の記述か、ガイドのスライド（slide:p08-revocation-propagation）の記述か | token_types.schema.json `introspection_cache_ttl`、E-opaque | https://www.rfc-editor.org/rfc/rfc7662#section-4 |
| F08 | RFC 8693 §4.1 は `act`（最も外側が今の代理者、入れ子は過去の代理者でアクセス制御に使わない）、§4.4 は `may_act` | E-token-exchange、questions.yaml q-actor、README 3.1 `does_not_answer` | https://www.rfc-editor.org/rfc/rfc8693 |
| F09 | RFC 9068 §2.2 は client credentials の AT の `sub` はクライアントを表すべき（SHOULD）とする。§5 は client credentials での sub の扱いの注意。§2.2.3 は scope の形 | E-client-credentials、README 3.1 `shape` | https://www.rfc-editor.org/rfc/rfc9068 |
| F10 | RFC 8707 §2 は `resource` パラメータ | questions.yaml q-resource、README 3.3・3.4 | https://www.rfc-editor.org/rfc/rfc8707 |
| F11 | RFC 7519 §11.2 は署名と暗号化の順序（署名してから暗号化） | README 3.1 `confidential_from`、3.2 `jwe` | https://www.rfc-editor.org/rfc/rfc7519#section-11.2 |
| F12 | RFC 8725 §3.1 はアルゴリズムの検証（許可リスト） | README 3.2 `alg_allowlist` | https://www.rfc-editor.org/rfc/rfc8725 |
| F13 | OpenID Connect Core 1.0 §8 は Subject Identifier Types（public・pairwise） | README 3.2 `subject_type` | https://openid.net/specs/openid-connect-core-1_0.html#SubjectIDTypes |
| F14 | FAPI 2.0 Security Profile（Final）§5.3.2.1 に「RT のローテーションを例外的な事情を除き使わない」「送信者制約の AT だけを出す」、§5.3.2.2 に PAR と PKCE（S256）の要求がある（PR #37 の独立点検が本文で確かめた） | E-fapi-no-rotation、E-fapi2 | https://openid.net/specs/fapi-security-profile-2_0-final.html |
| F15 | draft-ietf-oauth-sd-jwt-vc-27（2026-11-16）が最新版で、§5.6 がクレームのメタデータ（path・display・mandatory・sd・svg_id）。sd は always・allowed・never で既定 allowed、mandatory の既定 false。§5.2 が「知らないプロパティを無視する（MUST）」 | claims.schema.json `path`・`mandatory`・`sd`・`display`、README 10. | https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/ （§5.2 の記述は `research/claims-as-code/report.md` からの引き写しで、作成者は本文で確かめていない） |
| F16 | draft-ietf-oauth-transaction-tokens-11 §9.2 は `req_wl`・`txn` を定め、§13.6 は Txn-Token の寿命が元のトークンより長くてもよいとする | questions.yaml q-req-wl・q-txn、hops.schema.json `max_lifetime`、README 3.4 | https://www.ietf.org/archive/id/draft-ietf-oauth-transaction-tokens-11.txt （#6 の本文の記述に合わせた。作成者は本文で確かめていない） |
| F17 | fideslang の最新のリリースは 3.1.4（2026-08-18）、ライセンスは CC BY 4.0。3.1.4 の `data_files/data_categories.csv` に、記入例で使ったキー（`system.operations`・`system.authentication`・`user.unique_id`・`user.name`・`user.contact.email`・`user.authorization`）がある。`system.operations` の下にテナントの専用のキーはない | claims.yaml `data_category_vocabulary`・`data_category`・`data_category_extensions`、README 9. | https://github.com/ethyca/fideslang/tree/3.1.4 |
| F18 | 記入例の `data_category` の割り当て（例：`sid`・`nonce`・`auth_time` を `system.authentication`、`scope`・`roles` を `user.authorization`、`email_verified` を `user.contact.email`）が、fideslang 3.1.4 のカテゴリの説明に合う | claims.yaml | 同上（説明文の当てはまりの判断。作成者の判断で、根拠の一次資料はない） |

## 2. スライドとの一致

| # | 主張 | 確かめ方 |
| --- | --- | --- |
| S01 | questions.yaml の `questions` の 11 問の `text` は、挙げたスライドの本文（`docs/slides.json` の text）にその文字列のまま現れる | `python -m pytest tools/tests/test_registry_v1.py -k question`。機械で確かめているのは部分文字列の一致だけで、その文字列が表の「問い」の列のものかは見ていない |
| S02 | slide:p05-one-request-carries の表は、act・req_wl・mTLS の相手を別の行に分けている（#10 の後） | `docs/slides.json` の p05-one-request-carries |
| S03 | #3 の本文の問いのうち、スライドに問いの形の文言がないのは「誰が発行したか、信頼する発行者か」「どの種類・目的のトークンか」「どの強さで、いつ認証されたか」「今も有効か」の 4 つ（pending）。「どの取引で、何をどの条件で」はスライドでは「どの取引か」だけ | `docs/slides.json` を全文検索する |
| S04 | #3 の本文の「スライド 134」はいまの slide:p11-registry-fields（141 枚目）、「スライド 61」は slide:p04-design-checklist（63 枚目）、「スライド 81」は slide:p06-narrow-downstream、「スライド 117」は slide:p09-jwe-sd-jwt にあたる | `docs/slides.json`、`deck/slide_ids_registry.json` |
| S05 | README 4. の 12 項目の「決めること」の文言は slide:p11-registry-fields の表と同じ | 同上 |
| S06 | README 6. の 4 つの層は slide:p08-four-lifetimes の表の 4 行と同じ | 同上 |

## 3. ケーススタディとの照合

| # | 主張 | 確かめ方 |
| --- | --- | --- |
| C01 | ケーススタディのコミット `080b8da` の完全な SHA は `080b8da317ac13386f60232f1840cdb7eadbc262` | `gh api repos/Takenori-Kusaka/jwt-claims-casestudy/commits/080b8da` |
| C02 | `tools/casestudy_pin.json` の sha256 は、そのコミットの各ファイルのもの（catalog.json と decisions の 5 ファイル） | `python tools/casestudy_check.py`（取り直して照合する） |
| C03 | catalog.json の ORG-01・02・03・06・07 の `name` と `value_type` は、記入例の名前空間＋名前と型・形に一致する（ORG-03 は `array of string`） | 同上 |
| C04 | 記入例の `catalog_refs` は 32 件で、載せる／載せないの食い違いは 7 件（すべて `casestudy-deviations.yaml` に載っている）、条件の違いは 1 件（CLM-0410）。#16 の手作業の数と同じ | 同上、`research/template-design/gate1.md` の 6. |
| C05 | decisions の 5 ファイルの行の合計は 795（CLM 784＋ORG 11） | 各ファイルの配列の長さ（215・223・167・189・1） |

## 4. 成果物の中の数と事実

| # | 主張 | 確かめ方 |
| --- | --- | --- |
| N01 | 台帳の行の列は 72（v0 は 39）、最上位の項目は 6。トークン目録の列は 45（v0 は 23）、発行方式の選択は 10 項目（v0 は 8）、ホップの列は 17 | スキーマの `properties` を数える |
| N02 | すべての配列に `maxItems` がある | `test_every_array_has_max_items` |
| N03 | `overflow_strategy` に truncate・切り詰め・切り捨ては書けない | `test_overflow_strategy_cannot_be_truncate` |
| N04 | トークン目録の記入例は 18 行で、`token_kinds.yaml` の 17 種類すべてを含む（session が 2 行） | `test_inventory_has_every_token_kind` |
| N05 | claim_lint の結果は移し替えの前と同じ（error 0・warn 2・info 7）。Full・Lite とも | `python tools/claim_lint templates/examples/scenario-a [--profile lite]` |
| N06 | 関門 1 の記録の数（875 → 700）は、v0 の列と v0 の 9 行に絞って数えると再現する | `test_count_lite_fields.py` |
| N07 | README の列の一覧（3.）に、4 つのスキーマのすべての列が、根拠と縮小 Lite の印つきで載っている | `test_readme_documents_every_column_with_evidence`（根拠の欄が空でないことしか見ていない。中身が主張を支えるかは見ていない） |
| N08 | README 3.1 の「ケーススタディの列（区分）」は `templates/casestudy-mapping.md` の 3. の表と食い違わない | 目で比べる |
| N09 | 記入例の値（寿命 300 秒、ずれ 30 秒、受け入れの上限 330 秒、idle 1800 秒、最大 36000 秒、JWKS の TTL 3600 秒、取り直しの最短 300 秒、公開から使用まで 3900 秒）は v0 の記入例から変えていない | `git diff main -- templates/examples/scenario-a/` |

## 5. 対応表（#22）の変更：要件を「実装済み」にした 67 件

**追記（2026-11-23）**：PR #37 の独立点検を受けて 67 件すべてを見直し、13 件を未着手に戻した（実装済みは 54 件）。記録は `research/reviews/registry-v1-trace-review.md`。下は点検の時点の記述のまま残す。

`templates/trace/requirements.yaml` で、#3 が担当の要件 152 件のうち 67 件（core 48・full 19）を `実装済み` にしました。`trace_check.py` が確かめるのは「成果物があり、その中に `req:<要件 ID>` がある」までで、**成果物が要件の中身を満たすかは確かめません**。点検では、下の各行について「列（や問い）があること」が要件の文を満たすと言えるかを見てください。満たさないものは `未着手` に戻します。

判断に迷った（作成者が弱いと見ている）もの：
- `p02-delegation-client.R6`（AT に client_id を入れる）：`required_claims` の列はあるが、記入例（Keycloak）は client_id を欠き、却下している
- `p06-access-context.R2`（アクセス元の値に、認証時の値と分かる名前と意味しないことを書く）：`name`・`not_meaning` の列があるだけ
- `p08-logout.R2`、`p06-flow-partner-events.R7`：`revocation` の手段の列挙があるだけで、選び方の規則は #6
- `p01-client-made-jwts.R2`：`jti_policy.max_age_seconds` と `replay_check` で表せるとしたが、記入例では DPoP を却下していて値はない
- `p06-grant-types.R1`：`client_type` の列と issuance_effects の E-public-pkce で表せるとした

一覧（`git diff main -- templates/trace/requirements.yaml` で `status: 実装済み` に変わった行）：p00-claims-are-contracts.R3・R4・R6、p00-why-hard.R1・R3・R5、p00-incident-signature-valid.R4、p01-jwt-structure.R3、p01-client-made-jwts.R2、p02-registered-claims.R5、p02-roles-groups-entitlements.R2・R4、p02-scope.R7、p02-auth-strength-session.R4、p02-delegation-client.R6、p02-saml-attributes.R1、p02-check-before-creating.R2・R3、p03-entra-scp-roles-groups.R1、p03-keycloak-aud-lightweight.R3、p03-absorb-idp-differences.R2、p04-carry-or-query.R3、p04-namespace.R1・R4、p04-absent-null-false-empty.R1、p04-case-and-characters.R2、p04-immutable-identifiers.R2・R3、p04-split-by-writer.R1、p04-size-budget.R1・R2、p04-namespace-object-example.R1・R2、p05-one-request-carries.R2、p05-confused-deputy.R5、p06-stage-map.R1、p06-grant-types.R1、p06-edge-exchange.R2・R3、p06-narrow-downstream.R2、p06-access-context.R2、p06-flow-browser-to-db.R3、p06-flow-partner-events.R7、p08-stale-claims.R4、p08-rotation.R2・R4、p08-revocation-propagation.R3・R4、p08-logout.R2、p08-copies-outlive-token.R4、p09-jws-is-readable.R2、p11-registry-fields.R2〜R12、p11-change-procedure.R6、p11-reserved-names.R2、p11-translation-layer.R4、p11-ownership.R1・R2

あわせて、`p08-rotation.R4` の成果物を `registry:token_types#rt_idle_timeout` から `#idle_timeout` に改名した（RT とセッションの両方の無操作の期限にしたため。`planned_items.yaml`）。

## 6. この PR で行っていないこと（点検の範囲外だが、完了基準に関わるもの）

- シナリオ B の記入例（#3 の完了基準「シナリオ A・B の記入例がスキーマの検証を通る」）。B の記入例は作っていない
- 定義の寿命の層の deprecated の行の記入例（README 6. の末尾）
- pending の 4 問をスライドに載せること（スライドは凍結中）。追跡は #3 にしてあるが、凍結が解けた後に担当の issue を立てる必要がある
- `claim_lint --profile lite` の R1 の必須の列を縮小 Lite に合わせること（#4 の担当）
- issuance_effects.yaml を読む規則（L62〜L64）と、`confidential_from`・`visible_to` を突き合わせる規則（L65〜L67）は #6
