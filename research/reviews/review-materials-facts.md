# 点検の材料：レビュー教材の MVP（#5）

独立の点検（`templates/CONTRIBUTING.md` の 2.・3.）に渡すための、成果物に含まれる事実の一覧と、抜き取りの対象です。**作成者の結論（正しいかどうか）は書いていません。** 点検者は、ここの一覧と一次資料を突き合わせ、結果を `research/reviews/review-materials-<日付>.md` に、既存と同じ区分（誤り・過大・不一致・曖昧）で記録してください。

- 作成：2026-11-23、LLM（Claude、Opus 5.5）。シナリオ B のレビュー（`templates/examples/scenario-b/review-report.md` の 1.〜8.）は、同じセッションから分けた作業者（同じモデル。教材の作成の履歴を引き継がない）が書いた
- 対象：ブランチ `issue-5-review-materials` の `templates/review/`（README・perspectives・decision_tree・contrasts 8 本・escalation・procedure・rationale_rubric・report_template・escaped_defects・metrics）、`templates/examples/scenario-b/review-report.md`、`tools/review_check.py`、`research/reviews/rubric-agreement-2026-11-23.md`、対応表の変更
- 「確かめ方」の列：**slide** はガイドのスライド（`docs/slides.json`）の記述を写した（一次資料では確かめていない）、**repo** は本リポジトリの既存の資料（テンプレート・台帳・RULES.md・調査メモ）の引用を写した、**記憶** は作成者の知識で書き、作成のときに一次資料を開いていない。**この PR では、web で一次資料を開いて確かめた事実はありません。** **記憶** の行を優先して点検してください

## 1. 機械の検査の結果（作成のとき）

| 検査 | 結果 |
| --- | --- |
| `python tools/review_check.py` | questions 167、files 17、error 0 |
| `python tools/trace_check.py`・`--tier core` | OK（未着手 402・実装済み 305・後回し 42・扱わない 1） |
| `python tools/template_check.py` | files 15、items 142、error 0 |
| `python tools/check_slide_refs.py templates` | 0 problems |
| `python tools/check_mermaid.py templates/review/decision_tree.md` | 1 block、failed 0 |
| `python -m pytest tools/tests` | 519 passed・5 skipped（test_review_check.py を足す前）。test_review_check.py は 17 passed |

`review_check.py` が確かめるのは、問いの形（ID・見る欄・根拠の形・リンクの解決・対応表の印）までです。問いが正しい問いか、見る欄が本当に答えを持つか、根拠が主張を支えるかは、3. の抜き取りで点検します。

## 2. 事実の一覧

### 2.1 仕様の節

| # | 事実（教材での書き方の要約） | 書いた場所 | 出どころ | 確かめ方 |
| --- | --- | --- | --- | --- |
| S1 | `act` の最も外側が今の行為者で、入れ子の `act` は情報だけで、アクセス制御に使わない | contrasts/act-txn-workload の 2.・5.、perspectives `q-agent-delegation-claims` | RFC 8693 §4.1 | repo・記憶 |
| S2 | `may_act` は RFC 8693 §4.4 | contrasts/act-txn-workload の 6.、perspectives `q-break-glass` | RFC 8693 §4.4 | repo |
| S3 | RFC 8693 は交換で範囲を狭めることを求めない（§5 は scope と短い寿命の併用を推奨するだけ） | contrasts/act-txn-workload の 4. | RFC 8693 §5、slide:p06-narrow-downstream | slide |
| S4 | Txn-Token の寿命は短く（分以下）、元のトークンより長くてよい | contrasts/act-txn-workload の 3.、four-lifetimes の 3.、perspectives `q-hop-lifetime` | draft-ietf-oauth-transaction-tokens-11 §6、slide:p06-narrow-downstream（スライドは §13.6・§13.14 を引く） | slide・repo |
| S5 | Txn-Token の `scope` は元と同じかそれ以下で、判別できなければ拒否 | contrasts/act-txn-workload の 3. | slide:p06-narrow-downstream | slide |
| S6 | Txn-Token のクレーム `txn`・`sub`・`scope`・`tctx`・`rctx`（`req_wl` を含む） | contrasts/act-txn-workload の 2. | draft-ietf-oauth-transaction-tokens-11 §9.2 | repo |
| S7 | Txn-Token は `Txn-Token` ヘッダーで送り、Authorization ヘッダーで送らない | perspectives `cf-06`、contrasts/act-txn-workload | draft-ietf-oauth-transaction-tokens-11 §12.1 | repo（RULES.md の L43） |
| S8 | `req_wl` は伝搬の途中で書き換えない | contrasts/act-txn-workload の 3.、decision_tree の 4. | draft-ietf-oauth-transaction-tokens-11 §12.2 | repo（#5 の本文、P5） |
| S9 | 作り直し（Txn-Token を subject token にした再発行）の扱いは §13.15 で、P5 の表を見る | contrasts/act-txn-workload の 3. | draft-ietf-oauth-transaction-tokens-11 §13.15 | repo。#5 の本文は「作り直しの扱いは仕様が定めていない（§13.15）」、P5 の表は「権限を減らす・値を足すのは可／scope の拡大と txn・sub・aud の変更は不可」と書いており、**両者の食い違いを教材では解消していない**（点検で確かめてほしい） |
| S10 | mTLS のクライアント認証は RFC 8705 §2 | contrasts/act-txn-workload、decision_tree の 5. | RFC 8705 §2 | 記憶 |
| S11 | ID トークンの `aud` はクライアントの `client_id`。検証の手順は OIDC Core §3.1.3.7 | contrasts/id-vs-access-token の 2. | OpenID Connect Core 1.0 §2・§3.1.3.7 | 記憶 |
| S12 | ID トークンには仕様上の決まった `typ` がない（`JWT` か省略が多い） | contrasts/id-vs-access-token の 2. | 記憶（出典なし） | 記憶 |
| S13 | AT の `typ` は `at+jwt`、必須のクレームは iss・exp・aud・sub・client_id・iat・jti、検証は §4 | contrasts/id-vs-access-token | RFC 9068 §2.1・§2.2・§4 | repo（RULES.md の L27）・記憶（§4） |
| S14 | RFC 8725 の節：§3.1 アルゴリズムの検証、§3.2 適切なアルゴリズム、§3.3 すべての暗号の操作の検証、§3.8 発行者と主体の検証、§3.9 宛先、§3.10 受け取ったクレームを信じない、§3.11 明示的な型 | contrasts の各所、perspectives `ap-1-1`・`ap-1-3`・`q-nested-jwt-both-layers` | RFC 8725 | 記憶 |
| S15 | JWS は完全性、JWE は秘匿。JWE の形（ヘッダー・暗号化した鍵・IV・暗号文・認証タグ） | contrasts/jws-vs-jwe | RFC 7515 §1、RFC 7516 §1 | 記憶 |
| S16 | JWE の JSON の直列化は複数の宛先に暗号化できる | contrasts/jws-vs-jwe の 3. | RFC 7516 §7.2 | 記憶 |
| S17 | ネストした JWT は署名してから暗号化する順 | contrasts/jws-vs-jwe | RFC 7519 §11.2 | 記憶 |
| S18 | `scope` の形は空白区切り、`roles`・`groups`・`entitlements` は SCIM の語彙を使う | contrasts/scope-vs-role の 2. | RFC 9068 §2.2.3・§2.2.3.1 | slide・記憶 |
| S19 | `authorization_details` の `type` は自分が管理する URI を既定にする（推奨） | contrasts/scope-vs-role、decision_tree の 6. | RFC 9396 §2、slide:p02-scope | repo（要件 p02-scope.R4） |
| S20 | JWT の AT の `authorization_details` は宛先ごとに絞る | perspectives `q-rar-per-audience` | RFC 9396 §9.1 | repo（00_core の 8.） |
| S21 | イントロスペクションの応答のキャッシュは応答の `exp` を超えない | contrasts/carry-vs-query・four-lifetimes | RFC 7662 §4 | slide |
| S22 | `iss` と `sub` の組だけが安定した利用者のキー | contrasts/name-vs-identifier、perspectives `ap-1-6` | OpenID Connect Core 1.0 §5.7 | slide・記憶 |
| S23 | ペアワイズの `sub` は OIDC Core §8 | perspectives `q-pairwise-external`、contrasts/name-vs-identifier | OpenID Connect Core 1.0 §8 | slide |
| S24 | 公開クライアントの RT はローテーション（＋再利用検知）か送信者制約 | decision_tree の 7.、rationale_rubric の RR5 の例 | RFC 9700 §4.14.2 | slide |
| S25 | FAPI 2.0 の機密クライアントでは AS は RT のローテーションを使わない | rationale_rubric の RR4 の例 | FAPI 2.0 Security Profile（Final）§5.3.2.1 | slide |
| S26 | 追加認証が足りないときの `insufficient_user_authentication` | perspectives `q-step-up-by-rs` | RFC 9470 §3 | repo |
| S27 | トークンを URL・クエリに載せない | perspectives `q-token-not-in-url` | RFC 9700 §4.3.2 | slide |
| S28 | Logout Token は `typ: logout+jwt`、`nonce` を入れない | contrasts/id-vs-access-token の 3. | slide:p08-logout（Back-Channel Logout 1.0 §2.4〜§2.8・§4） | slide |
| S29 | AT は利用者がいる証拠ではない | contrasts/id-vs-access-token の 1. | NIST SP 800-63B-4 §5.1.2 | slide |
| S30 | AT・ID トークンは 1 時間以内とすべき | contrasts/four-lifetimes、decision_tree の 7. | NIST IR 8587 §5.3.1.1 | slide |
| S31 | 再認証の上限：AAL2 は 24 時間・無操作 1 時間 | contrasts/four-lifetimes、perspectives `q-session-rt-bounds` | NIST SP 800-63B-4 §2.2.3 | slide |
| S32 | アサーションの参照は 5 分以内（FAPI 2.0 は 60 秒） | contrasts/four-lifetimes の 4. | NIST SP 800-63C-4 §4.11.1 | slide |
| S33 | アサーションの有効期間を RP のセッションの長さと混同しない | contrasts/four-lifetimes の 5. | NIST SP 800-63C-4 §4.7 | slide |
| S34 | 受け手ごとに必要なクレームだけを出す／派生値 | perspectives `q-minimal-per-recipient`・`q-derived-value` | NIST SP 800-63C-4 §3.10・§3.12.2 | slide |
| S35 | トークンと個人情報をログに残さない | perspectives `ap-2-8`・`pa-20` | NIST IR 8587 §5.3.1.7 | slide |
| S36 | 非人間の ID は狭く短命なトークン | perspectives `q-agent-short-lived-no-rt` | NIST IR 8587 §5.3.1.6 | slide |
| S37 | 元の利用者の権限で判断する | perspectives `q-original-principal` | ASVS v5.0.0-8.3.3 | slide（スライドは「ASVS 8.3.3」） |
| S38 | 監査ログ自体を守る | perspectives `q-audit-log-protected` | ASVS v5.0.0-16.4.2 | slide（スライドは「ASVS 16.4.2」） |
| S39 | BOLA は OWASP API Security Top 10 2023 の API1 | perspectives `q-object-level-authz` | OWASP API Security Top 10 2023 API1 | 記憶 |
| S40 | 属性の名前・定義・許容値は中央が管理する／変更は全依拠当事者に事前通知 | perspectives `stage-definition`・`q-change-order` | NIST SP 800-162 §2.4.2・§3.3.3 | slide |
| S42 | 同じ API では `scope` か `authorization_details` の一方を使う（シナリオ B のレビュアーは、RFC 9396 が併用を想定した記述を持つと指摘した。F27） | perspectives `q-scope-semantics`、decision_tree の 6. | slide:p02-scope（要件 p02-scope.R6）、RFC 9396 §2 | slide。**一次資料で確かめていない** |
| S43 | Txn-Token の必須のクレームは iat・aud・exp・txn・sub・scope・req_wl | perspectives `q-txn-required-claims` | draft-ietf-oauth-transaction-tokens-11 §9.2 | PR #44 のレビュー（B02）の写し |
| S41 | CAEP 1.0 は 2025-09 に Final | contrasts/four-lifetimes の 2. | slide:p08-revocation-propagation | slide |

### 2.2 事例・製品の値

| # | 事実 | 書いた場所 | 出どころ | 確かめ方 |
| --- | --- | --- | --- | --- |
| E1 | CVE-2015-9235：`alg` の混同 | perspectives `ap-1-1` | slide:p12-antipatterns-1 | slide |
| E2 | CVE-2020-26160：`aud` の確認の抜け | perspectives `ap-1-3` | slide:p12-antipatterns-1 | slide |
| E3 | CVE-2025-55241：マルチテナントで iss・tid を見ない／署名・失効・ログの無い内部の代理トークン（Entra の Actor token） | perspectives `ap-1-4`・`ap-2-9`・`q-internal-delegation-token` | slide:p12-antipatterns-1、slide:p12-antipatterns-2 のノート | slide（「Actor token」の名前は記憶） |
| E4 | Storm-0558：別系統の鍵の署名を受理。CSRB 報告書（2024-03） | perspectives `ap-1-5` | slide:p12-antipatterns-1 | slide |
| E5 | 根拠として「CSRB 報告書（Storm-0558）勧告 6」を引いた | perspectives `ap-1-5` の根拠 | repo（既存の調査メモの引用の形） | repo。**勧告 6 の中身が鍵と発行者の対応を述べるかは確かめていない** |
| E6 | nOAuth（2023）：変更できる email を信じた RP の乗っ取り | perspectives `ap-1-6`、contrasts/name-vs-identifier | slide:p12-antipatterns-1 | slide（中身の要約は記憶） |
| E7 | Cognito の `custom:` 属性は、読み取り専用にしない限り本人が書き換えられる場合がある | perspectives `ap-1-7` | slide:p03-cognito-pre-token-hook | slide |
| E8 | golang-jwt v5 の既定では exp が無くても通る | perspectives `ap-1-8` | slide:p12-antipatterns-1（「golang-jwt v5 の既定」） | slide（「exp が無くても通る」の言い換えは記憶） |
| E9 | Entra の groups は JWT で 200 件を超えると出ず、`_claim_names`・`_claim_sources` に替わる | perspectives `ap-2-1` | slide:p03-entra-scp-roles-groups | slide |
| E10 | Auth0 の予約名と衝突した独自クレームは、エラーにならず黙って追加されない | perspectives `ap-2-4` | slide:p03-auth0-namespace | slide |
| E11 | Entra CAE のグループ変更の反映に最大 1 日 | perspectives `ap-2-2` | slide:p08-stale-claims | slide |
| E12 | Keycloak 26.8 の交換で、元に無い orders 宛てのトークンが出た | perspectives `q-hop-narrowing`、contrasts/act-txn-workload | slide:p06-narrow-downstream、slide:p10-token-exchange-not-narrowing | slide |
| E13 | ケーススタディ B15：Okta のフックの打ち切りで部署が消えた | perspectives `q-hook-failure` | jwt-claims-casestudy@080b8da:B15（記入例の claim_request_department.md の問 18 の引用） | repo |
| E14 | `SET LOCAL` はバインド変数を受けないので `set_config($1, $2, true)` を使う | perspectives `q-db-context-parameterized` | research/template-design/gate1.md の 5. の A12 | repo（`set_config($1, $2, true)` の書き方は記憶） |
| E15 | MCP の認可仕様（2026-07-28）はトークンのパススルーを禁じる | perspectives `ap-2-6` | slide:p10-mcp-authorization | slide |

### 2.3 筆者の提案（追跡 #5）

`templates/CONTRIBUTING.md` の 1. により、追跡 issue（#5）の本文に提案ごとに 1 項目を置く必要があります。**この PR では #5 の本文に項目を足していません**（調整役に渡す）。

| # | 提案 | 書いた場所 |
| --- | --- | --- |
| P1 | 段ごとの担当の割り当て（定義：台帳の持ち主＋受け手の代表、発行：発行者、伝搬：入口、検証：受け手、認可：受け手（PEP・PDP・データ層）、運用：運用） | perspectives の各段、procedure の 3. |
| P2 | 専門家に回す基準のうち、#5 の本文の 4 つ以外の 5 つ（baseline-unmet・jwe-key-management・unverified-idp-behavior・regulated-data・new-token-type） | escalation |
| P3 | 手順の段（0〜8）の順序と、理由の抜き取りの数（採用・却下から各 5 件） | procedure |
| P4 | 1 名で行う場合の役割の切り替えの順（攻撃者 → 受け手 → 発行者 → 運用 → 個人情報 → クライアント）と、段 0〜3 と 4〜6 を別の日に行うこと | procedure |
| P5 | 理由の採点の 6 観点（RR1〜RR6）と 2 値の採点 | rationale_rubric |
| P6 | レビューの指標の選び方 | metrics |
| P7 | 判断の木の分け方（7 つの節） | decision_tree |
| P8 | 採点の一致の目安（観点ごとに 7／10 未満なら直す） | research/reviews/rubric-agreement-2026-11-23.md |
| P9 | 重大度の 3 段（Blocker・Major・Minor）の定義と、問いごとの重大度の目安 | perspectives、report_template |

## 3. 抜き取りの対象

- 問いの抜き取り：perspectives の 167 問から 10%（17 問）。選び方の案：`python tools/review_check.py --list` の行を `random.seed(5)` で 17 行選ぶ。各問いについて、(a) 見る欄で本当に Yes／No を決められるか、(b) 根拠が問いを支えるか、(c) 対比表のリンク先が問いに関係するか
- 対比表：8 本の「典型的な誤用」の行の全件（67 行）で、「見つける問い」が誤用に当たるか
- 対応表の印：#5 の要件で実装済みにした 94 件から 10 件。印を足した他の成果物（台帳のスキーマ・テンプレート・RULES.md）の箇所が、その要件を実装しているか（`req:` の印は、中身が要件を満たすことまでは保証しない。templates/trace/README.md の「実装済みの確かめ方」）

## 4. 渡さないもの

作成者の結論（「正しいことを確かめた」など）はありません。シナリオ B のレビューの較正の結果（review-report.md の 9.）は、点検の対象ですが、PR #44 の指摘との照合の正しさは、点検者が PR #44 のコメントを読んで確かめてください。
