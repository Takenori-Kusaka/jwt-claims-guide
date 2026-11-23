# 点検の材料：実行での照合の確認（#8）

独立の点検（`templates/CONTRIBUTING.md` の 2.・3.）に渡すための、成果物に含まれる事実の一覧と、抜き取りの対象です。**作成者の結論（正しいかどうか）は書いていません。** 点検者は、ここの一覧と一次資料（仕様、ケーススタディ、実行の記録）を突き合わせ、結果を `research/reviews/runtime-<日付>.md` に、既存と同じ区分（誤り・過大・不一致・曖昧）で記録してください。

- 作成：2026-11-23、LLM（Claude、Opus 5.5）
- 対象：ブランチ `issue-8-runtime` の `templates/runtime/`（README・negative_tests・consumer_contract・golden_tokens・lifetime_revocation）、`tools/runtime_tests/`、`tools/tests/test_runtime.py`、`research/runtime/`（実行の記録）、対応表の変更（`templates/trace/`）、`req:` の印を足したファイル（`templates/registry/*.schema.json`・`questions.yaml`、`templates/modules/M_token_validation.md`、`tools/claim_lint/RULES.md`）、観点書（`templates/review/perspectives.md`）の「つながり」、`tools/review_check.py` の V6
- 「確かめ方」の列：**実測** は本リポジトリの実行の記録（`research/runtime/run-*-2026-11-23.md`）で観測した、**cs** はケーススタディ（jwt-claims-casestudy@080b8da）のファイルを開いて写した、**repo** は本リポジトリの既存の資料を写した、**記憶** は作成者の知識で書き、一次資料を開いていない。**記憶** の行を優先して点検してください

## 1. 機械の検査の結果（作成のとき）

| 検査 | 結果 |
| --- | --- |
| `python tools/runtime_tests/run.py --env offline` | 34/34 件、186 の確認（`research/runtime/run-offline-2026-11-23.md`） |
| `python tools/runtime_tests/run.py --env live` | 15/15 件、57 の確認（`research/runtime/run-live-2026-11-23.md`）。Keycloak 26.8.0（image id sha256:27b3230f…eb05741）・postgres:16-alpine、compose のプロジェクト `jcg-issue8-runtime`、ポート 38080・35432。実行の後、コンテナが残っていないことを `docker ps -a` で確かめた |
| `python tools/trace_check.py`・`--tier core` | OK（未着手 362・実装済み 345・後回し 42・扱わない 1。#8 は 50 件中 40 件が実装済み。PR #48 の点検で 2 件を未着手に戻した） |
| `python tools/review_check.py` | error 0 |
| `python -m pytest tools/tests/test_runtime.py` | 44 passed |

`test_runtime.py` が確かめるのは、テストのコードと文書の節の対応（アンカー・`req:` の印・lint の規則の名前）、計画の項目が作られたか一覧にあるか、記録に生の JWT・PEM が無いことまでです。テストが要件を満たしているか、参照の受け手が設計どおりかは、下の抜き取りで点検します。

## 2. 事実の一覧

### 2.1 仕様

| # | 事実（成果物での書き方の要約） | 書いた場所 | 出どころ | 確かめ方 |
| --- | --- | --- | --- | --- |
| S1 | JOSE ヘッダーの jku・x5u をたどらない（取得が SSRF になる） | validator.py、negative_tests の jku-x5u | RFC 8725 §3.10 | 記憶（PR #48 の点検で「§3.10 は kid・jku・x5u だけ」と指摘。jwk・x5c を S1a に分けた） |
| S1a | ヘッダーの jwk・x5c の鍵・証明書は、設定した鍵に結びつけない限り信頼しない | validator.py、embedded-jwk の注 | RFC 7515 §4.1.3・§4.1.6 | 記憶 |
| S1b | 受け手の知らない crit のヘッダーは拒否する | validator.py、jku-x5u の期待する結果 | RFC 7515 §4.1.11 | 記憶 |
| S2 | alg は許可リストで固定し、none と HS256 の混同を防ぐ | validator.py、alg-none・alg-confusion | RFC 8725 §3.1・§3.2 | 記憶 |
| S3 | 明示的な型（typ）で種類を分ける | validator.py | RFC 8725 §3.11 | 記憶 |
| S4 | typ のメディア型の名前は大文字小文字を区別せず、`application/` を省ける | validator.py、typ-wrong の注 | RFC 7515 §4.1.9 | 記憶 |
| S5 | 受け手は typ の `at+jwt` と `application/at+jwt` を受ける | typ-wrong | RFC 9068 §4（受け手の検証の手順。§2.1 は発行者の規則） | 記憶（PR #48 の点検で §4 と指摘） |
| S6 | 重複したクレーム名は、拒否するか、後勝ちで読むかのどちらか | duplicate-claim の注、M_token_validation の「同名のメンバー」 | RFC 7519 §4 | 記憶 |
| S7 | 今の代理者は最も外側の act だけ | nested-act、scenario_b.py | RFC 8693 §4.1 | repo |
| S8 | Txn-Token は Txn-Token ヘッダーで送り、Authorization では送らない | txn-token-as-at | draft-ietf-oauth-transaction-tokens-11 §12・§12.1 | repo（RULES.md の L43） |
| S9 | Txn-Token の置き換えでは txn・sub・aud を変えない。元より長い寿命の置き換えは MAY | txn-remint-immutable の注、scenario_b.remint_violations | draft-ietf-oauth-transaction-tokens-11 §13.15 | PR #48 の点検（作成時の「§13.6」は誤り） |
| S9a | TTS が出す scope は元の subject_token と同じか狭い | 同上 | draft-ietf-oauth-transaction-tokens-11 §13.6 | PR #48 の点検 |
| S9b | req_wl を変えない・exp を延ばさないのは記入例の組織の規則（草案の規則ではない） | 同上 | 筆者の提案（追跡 #8）、claims.yaml C-req-wl、hops.yaml H9 の note | repo |
| S12 | 入れ子の act は情報で、アクセス制御には最も外側の act だけを使う。深さの上限は組織の規則 | nested-act、scenario_b.Invoices | RFC 8693 §4.1、ケーススタディの depth_rule | repo・PR #48 の点検 |
| S10 | 発行者は知らない type・フィールドの authorization_details を拒否する | rar-unknown-type | RFC 9396 §5 | repo（対応表の要件の文） |
| S11 | PostgreSQL の `SET LOCAL app.tenant = $1` はパラメータにできずエラーになる | pool-context-leak | 実測（`syntax error at or near "$1"`） | 実測 |

### 2.2 Keycloak 26.8.0 の観測（live の記録）

| # | 事実 | 書いた場所 | 確かめ方 |
| --- | --- | --- | --- |
| K1 | mcp-tools が scope=aud-orders で交換すると、元のトークン（aud mcp-tools・account）に無い orders 宛ての AT が 200 で出る（ケーススタディと同じ） | negative_tests の exchange-narrowing、lifetime_revocation 7. | 実測・cs（`results/measurements.json` の C.keycloak_exchange.probes.scope_not_granted） |
| K2 | 交換で出た AT の exp は交換の時刻から寿命 1 本分で、元の exp で抑えられない（3 秒後の交換で +3、点検の再現で寿命 20 秒・15 秒後の交換で +16、元が期限切れなら 400）。M_idp_keycloak の 9. が要約した文書の記述（AT は subject token の exp を超えない）と食い違う | lifetime_revocation 7.、research/runtime/keycloak-observations-2026-11-23.md の 1.、M_idp_keycloak の 8. | 実測・PR #48 の点検の再現 |
| K3 | 標準の交換（V2）の結果に act が無い | exchange-narrowing | 実測・cs（has_act false） |
| K4 | 無効にした利用者の AT を交換すると 400（invalid_request: Invalid token） | disabled-subject-exchange | 実測 |
| K5 | ローテーション済みの RT1 の再提示は `invalid_grant: Maximum allowed refresh token reuse exceeded`、その後の RT2 も `invalid_grant: Session doesn't have required client`。順番を逆にしても同じ。消えるのはクライアントのセッションで、SSO のセッションは残る。refreshTokenMaxReuse 0 での並行のリフレッシュでのログアウトは推論（試していない） | rt-reuse、lifetime_revocation 6.、keycloak-observations の 2.、M_idp_keycloak の 9.、P1 の 4. | 実測・PR #48 の点検の再現 |
| K6 | 管理者がセッションを消すと次のリフレッシュが `Session not active`、利用者を無効にすると `User disabled` | lifetime_revocation 5. | 実測 |
| K7 | ロールを外すと、次のリフレッシュの AT からそのロールが消える（縮めた設定で 18.1 秒） | lifetime_revocation 3. | 実測・cs（keycloak.refresh_reevaluation） |
| K8 | 軽量アクセストークンには名前空間・aud・sub が無い | missing-required-claim、issued-claims-present | 実測・cs（keycloak.lightweight） |
| K9 | ID トークンのヘッダーの typ は JWT | typ-wrong（live） | 実測 |
| K10 | t1 と t2 の JWKS に共通の kid は無い | untrusted-key（live） | 実測 |

### 2.3 時間の縮め方（lifetime_revocation 2.）

| # | 事実 | 確かめ方 |
| --- | --- | --- |
| T1 | 受け入れの上限 330 秒 = 寿命 300 秒 + ずれ 30 秒（シナリオ A の token_types.yaml の AT の note・at_format の rationale） | repo |
| T2 | テストは寿命 20 秒・ずれ 2 秒（1/15）で、上限 22 秒と比べる | repo（cases_live.py の SHORT） |
| T3 | 縮めてよい理由：反映の遅れは AT の期限で決まり、比に乗らないのは応答時間と要求の間隔だけ | 作成者の推論（点検の対象） |
| T4 | 本番の値でのロールの剥奪の最悪は「寿命＋要求の間隔」で約 301 秒（330 秒の内）。縮めた 18.1 秒を比で直した値（前の版の約 272 秒）は意味がない（剥奪の時刻を縮めていない） | 作成者の推論・PR #48 の点検 |
| T5 | 時計のずれ（2 秒）は同じホストなので実際には使われていない | PR #48 の点検 |

## 3. 抜き取りの対象

### 3.1 参照の受け手が設計どおりか（全件）

`tools/runtime_tests/scenario_a.py` の `SaasApi.authorize` の各手順と、`templates/examples/scenario-a/design.md` の 2.「境界の要点」、`hops.yaml` の H2 の `validates.checks`、`claims.yaml` の `enforced_at` を突き合わせる。同じく `scenario_b.py` の `Ledger.accept`・`Invoices.pay` と、シナリオ B の `hops.yaml` の H10・H15 の `validates.checks`。

### 3.2 要件を実装済みにした判断（40 件から 10 件以上）

`templates/trace/requirements.yaml` で #8 が担当し、この PR で `実装済み` にした 40 件から無作為に 10 件を選び、要件の文と、テストの節・実行の記録が要件を満たすかを点検する。とくに次は、作成者が「近い題材で代えた」もの：
- `p03-entra-scp-roles-groups.R4`・`p03-auth0-namespace.R2`：Entra・Auth0 でなく Keycloak の軽量アクセストークンで「宣言したのに出ていない」を確かめた
- `p11-schema-contract-tests.R4`：「新しい Schema の版で」を、台帳から生成した今の版の consumer のスキーマで代えた
- `p05-coarse-fine-layers.R3`：「発行者」は参照の sts（Python）で、実物の AS ではない

### 3.3 実装済みにしなかった #8 の要件（10 件、全件）

`p04-namespace.R2`、`p04-reject-missing-required.R4`、`p06-narrow-downstream.R3`（`calib:` に解決の手段なし）、`p06-flow-partner-events.R5`、`p07-connection-pool.R2`（PgBouncer を試していない）、`p08-stale-claims.R3`（`calib:`）、`p08-logout.R1`、`p08-async-processing.R5`、`p06-validation-split.R3`（ledger だけ）・`p08-rotation.R3`（台帳の reuse_detection が unverified のまま）。後の 2 件は PR #48 の点検で戻した。理由が negative_tests.md の 9.・consumer_contract.md の 7.・各節の注と一致するか。

### 3.4 ほかの issue の成果物に足した `req:` の印（全件）

`git diff origin/main -- templates/registry templates/modules tools/claim_lint/RULES.md` の各印について、その列・節・規則が要件の宣言の側を本当に表しているか。

## 4. 実行の記録の秘密情報

`research/runtime/` に、生のトークン・鍵・パスワード・クライアントシークレットが無いか（`test_runtime.py` は JWT と PEM の形だけを機械で見る）。
