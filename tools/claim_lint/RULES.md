# claim_lint の規則

設計書の台帳（`claims.yaml`）・トークン目録（`token_types.yaml`）・カタログへの回答（`catalog_answers.yaml`）を検査する規則です。#16（縦の一本）で R1・R2・R8 とスライドの参照の解決を作り、#17 で網羅の規則（R2 の強化・R3・R3b・R4・R6・R9・R10。`tools/claim_lint/coverage.py`）を足しました。#6 で意味の規則（L1a〜L73 の一部と L10。`tools/claim_lint/semantic.py`・`diff.py`）を足しました。下の「意味の規則」の節にあります。#18 で目的と仕組みの宣言の整合の規則（L11〜L14。`tools/claim_lint/purpose.py`）を足しました。下の「目的と仕組みの規則」の節にあります。

```
python tools/claim_lint templates/examples/scenario-a                 # 人向けの表
python tools/claim_lint templates/examples/scenario-a --format json   # 機械向けの JSON
python tools/claim_lint <設計書のディレクトリ> --profile lite         # Lite：R2・R4 を warn に下げる（R6 はもとから warn）
python tools/claim_lint diff --base origin/main <設計書のディレクトリ>  # L10：前の版と比べて互換性を壊す変更
```

IdP の実際の設定と台帳のずれ（`claim_lint import keycloak`・`claim_lint drift`、規則 D0〜D14。#30）は、台帳の中の宣言どうしではなく設定の書き出しとの比較なので、`DRIFT.md` に分けて書きました。

error が 1 件でもあれば終了コード 1 です。error の規則は抑止できません（`templates/CONTRIBUTING.md` の 2.）。

| ID | 内容 | 重大度（Full／Lite） | 根拠 |
| --- | --- | --- | --- |
| SCHEMA | `templates/registry/claims.schema.json`・`token_types.schema.json`・`hops.schema.json`（台帳 v1、template_version 0.2.0）の検証（JSON Schema 2020-12）。YAML の日付は文字列として読む。同じキーを 2 回書くと失敗する（LOAD） | error | #3 |
| LOAD | ファイルが読めるか。`claims.yaml`・`token_types.yaml`・`catalog_answers.yaml` が無い、YAML として読めない、同じキーが 2 回ある、は error。`hops.yaml` が無い・中身が空（コメントだけ、`{}`）のときは、Lite では info（ホップを書かない Lite の設計は置かない）、Full では warn（Full では経路のホップを書く。無いと、ホップを読む規則 L8・L15・L16・L21・L23・L43・L67 が何も見ない。PR #69 の点検で足した。新しい指摘なので warn から） | error／error（`hops.yaml` が無い・空：warn／info） | #3、#60 |
| TODO | スキーマが求める欄が、まだ書かれていない（値が null・空白だけの文字列・空の配列・空のオブジェクト）。`tools/new_design.py` が作る空の設計書の空欄がこれに当たる。1 欄に 1 件だけ出し、同じ欄の SCHEMA は出さない（#60）。書いた値の形が違うときは SCHEMA。重大度は SCHEMA と同じ error で、引き下げていない。`hops: []` は「ホップを書くか、`hops.yaml` を置かない」、`namespaces: []` は「キーを書かない」と直し方を添える | error | #60、research/template-design/pilot.md の 7. |
| R1 | 必須の列が空でない。下の「R1 の必須の列」。スライド 134 の 12 項目を載せる行の必須の列にし、欠ければ検出する（req:p11-registry-fields.R13）。対応表の要件：req:p00-claims-are-contracts.R4 req:p00-why-hard.R3 req:p02-check-before-creating.R2 | error／error | slide:p11-registry-fields、#3 |
| R2 | カタログ（`templates/catalog/`）の全イベントに「該当」か「対象外」の回答がある。「対象外」には `assumption`（起きない前提）と `breaks_when`（崩れる条件）があり、どちらも `tools/catalog_check.py` の種の項目と同じ中身の検査（10 字以上、同じ文字の繰り返しでない、イベントの ID・名前そのものでない）と、仮の値（TODO・TBD・xxx・未定など）でないことの検査を通り、互いに同じでない。「該当」には関係するトークン種別か説明がある。回答の `token_types` は、トークン目録（`token_types.yaml`）の ID でなければならない（目録にない ID は、どちらのプロファイルでも error）。Lite だけ、下の「Lite の既定の回答の引き継ぎ」を使える。カタログにない ID への回答と、同じイベントへの 2 つの回答は、どちらのプロファイルでも error。**理由が妥当かは機械では判定しない**（「対象外です対象外です。」のような文は通る）。妥当性は抜き取りの点検（#13）で見る | error／warn | `templates/CONTRIBUTING.md` の 2.「対象外の書き方」、report Q9 の R2、#4 の改訂（縮小 Lite）。10 字は筆者の提案（tracking #16） |
| R3 | 設計書の `idp` で、IdP の契機の一覧を確かめる。分類は `sources.md` の「契機の一覧を持つ IdP と、持たない IdP」による。**一覧あり・カタログの IdP**（Auth0：`auth0-protocol`・`auth0-trigger`・`auth0-grant`。Keycloak：トークン端点の grant の一覧 `keycloak-grant-types`（`OAuth2GrantType` の実装 10 個）と `keycloak-settings`）は、`seeds.yaml` で `idp: <IdP>` の一覧について、`catalog_check.closure()` の差集合（どの行にもひもづかず、対象外でもない項目）と件数の食い違いを error にする。Keycloak にはフックが呼ばれる契機の一覧はないが、grant の一覧は列挙できる（PR #33 の独立点検）。**一覧あり・カタログにない IdP**（Cognito。#21）は、設計書の `idp.trigger_list` に一覧の全項目と、ひもづくイベントか対象外（前提と崩れる条件）を書き、`idp.trigger_list_source`（url・verified_on）を付ける。**文書で未確認**（Entra・Okta：一覧があるかを文書で確かめていない。`unverified.md` の V07・V08）と、**一覧が存在しない**（設計書が `idp.enumerable: false` と宣言し、`idp.enumerable_source` に確かめた出どころを書いた IdP）は、R9 の `searched` に、その IdP の名前を含む具体的な出どころ（URL、ファイルのパス、15 字以上の文書の名前）を書く。2 つは別のメッセージを出す。一覧の有無が分からない IdP は `idp.enumerable` を宣言する。`idp` が無ければ error | error／error | #17、`templates/catalog/sources.md` |
| R3b | 設計書の IdP の列（カタログの `idp.<IdP>`）で `hook_invoked: no` の発行イベントに「該当」と答え、その発行で独自クレームを運ぶ（クレームの `issue_events` にそのイベントがあるか、回答の `token_types` とクレームの `carried_in` が重なる）なら error。`unknown`・`conditional` は warn で、書き手が回答の `hook_checked` に確かめた方法を書けば info に下げる（`hook_checked` の中身が本当かは機械では確かめない）。発行イベントの「該当」に `token_types` が無ければ error（照合を外せないように。照合にはカタログの `tokens_issued` の種類に当たる目録の行を使う）。独自クレームは、名前空間の付いたクレームと、IANA の JWT Claims にない名前で `usage` が protocol でないもの（IdP 自身が書く Keycloak のペイロードの `typ` は数えない）。発行者が IdP でない行（`issuer` が gateway・tts など）と、IdP が起こさない行（`occurs: no`）は見ない。カタログの IdP でない IdP は照合できないので warn。この規則に結びつく要件 p03-cognito-pre-token-hook.R2（Cognito の V2_0 の M2M の検出がない）と p06-issuance-hook.R2（「失敗する発行」の欄がカタログにない）は、足りない部分があるので未着手のまま（PR #33 の独立点検） | error（no・token_types が無い）・warn（unknown・conditional）／同じ | slide:p03-cognito-pre-token-hook、slide:p06-issuance-hook、#2 の `hook_invoked` <!-- req:p12-review-viewpoints.R5 --> |
| R4 | 設計書の `subject_states` に、カタログの行列（`subject_state_matrix.md`）の 7 状態 × 7 層の全セルがあり、結果が「発行・再計算・失効・影響なし」のどれかで、根拠（`basis`）が R2 と同じ中身の検査を通る（「影響なし」も根拠が要る）。使わない層は `unused_layers` に理由を書けば、その層のセルを省ける。ただし、その層の採用の行が `token_types` にあれば error。セッションの 2 つの層（どちらも `kind: session`）は `stored_at` で見分ける（`idp` なら IdP のセッション、それ以外は RP・BFF のセッション）。`stored_at` が無くて見分けられないときは warn。同じ根拠の文が多くのセルに並ぶことは検査しない（抜き取りの点検で見る） | error／warn | #17、#2 の行列、slide:p08-stale-claims |
| R6 | 主体の種類（利用者・ワークロード・システム。slide:p05-three-principals）× 発行イベント（「該当」と答えたもの）× 段階（カタログのそのイベントの `stage`）について、2 因子ずつの組（主体×イベント、主体×段階、イベント×段階）が、`pairwise.combinations` のどれかの組み合わせ（`note` つき）に一度は出る。主体の種類には「該当」か「対象外＋理由」を答える。**pairwise を網羅の目標にするのは筆者の提案（author-proposal、tracking #17）** で、下の「R6 の証拠の状況」のとおり、拾える割合には幅がある（req:p05-three-principals.R3） | warn／warn | report の R6（NIST ACTS）、`research/template-design/notes/coverage_lifecycle.md` |
| R8 | トークン種別ごとの最悪のサイズと、経路の上限。下の「R8 の計算」。配列の max_items と overflow_strategy（切り詰めは書けない）を求め、超えたら「載せるか、問い合わせるか」へ誘導する（req:p02-roles-groups-entitlements.R4 req:p04-carry-or-query.R3 req:p04-size-budget.R1 req:p04-size-budget.R2 req:p06-edge-exchange.R3 req:p11-registry-fields.R7） | error／warn／info（Lite も同じ） | report Q9。しきい値は筆者の提案（tracking #16） <!-- req:p06-issuance-hook.R3 req:p09-do-not-carry.R5 req:p12-antipatterns-2.R1 req:p12-review-viewpoints.R6 --> |
| R9 | 設計書の `outside_enumeration`（「この列挙の外に契機はないか」）に、回答（`answer`）・回答者（`respondent`）・日付（`date`）・探した範囲（`searched`：見た資料・図）がある。回答が「なし」だけなら error。同じ意味の「ありませんでした」「見つかりませんでした」「特に見つからなかった」「None found」「N/A」と、その繰り返し・括弧の中の補足だけを足したもの（「なし（特になし）」）も「なし」とみなす（`coverage.py` の `NONE_WORDS`。列挙した語だけを落とす）。仮の値（TODO・TBD・xxx・未定など、同じ文字の繰り返し）は、回答・回答者・探した範囲のどれでも error。日付は実在の日で、実行した日の翌日より後でない。探した範囲の各項目は短すぎず、少なくとも 1 つは具体的な出どころ（URL、ファイルのパス、15 字以上の文書の名前）。見つかった契機（`found`）には扱い（`handled_as`）を書く | error／error | report の R9（Threat Modeling Manifesto の 4 つ目の問い）、#11 の約束の範囲 |
| R10 | 出どころ・上限の `review_by` が過ぎている：`seeds.yaml` の一覧、カタログの行（`issue_events`・`use_events`・`token_kinds`）、`path_limits.yaml`（`--limits` で渡したファイル）の上限、`token_types` の `size.path` にその場で宣言した上限（スキーマに `verified_on`・`review_by` を足した）。上限のファイルとその場の宣言で `review_by` が無い・日付でないときも warn（カタログの行と一覧は `catalog_check` の COLUMNS・SOURCES が守る）。ファイルごとに 1 件にまとめ、ID を並べる。範囲はカタログと上限だけで、設計書が自分で書く IdP の挙動（design.md の「Keycloak 26.3 からの既定」など）の確認日は見ない（req:p03-recent-changes.R1） | warn／warn | slide:p03-recent-changes、`sources.md`（見直しの期限は確かめた日の 90 日後。筆者の提案、tracking #17） |
| REF | ファイルの間の参照が実在する（#3 の台帳 v1 で追加）：台帳の `answers`・`does_not_answer` は `templates/registry/questions.yaml` の `questions` の ID（`pending` の問いはスライドに同じ文言がないので参照できない）、`paired_id`・`alt`（`C-` の行）・`namespaces[].namespace_version`・トークン目録の `tenant_binding.claim`・ホップの `custom_claims`・`forwarded_headers[].claim` は台帳の行、ホップの `token_type` はトークン目録、`upstream` はホップ。ホップの `id` は重複せず、`upstream` をたどって循環しない（自分自身を含む）。`data_category_extensions` の `key` は `parent` の子（`parent` + `.` で始まる）。`hops.yaml` が無いときは info（交換・作り直しのホップがない設計では書かなくてよい） | error（`hops.yaml` が無いのは info） | #3。シナリオ A で誤検知 0 件（足した直後の指摘 0 件） |
| SLIDE | `refs` の `guide-slide` の ID と、入力のファイルの中の `slide:<id>` が、実在のスライドを指す（`tools/check_slide_refs.py` の解決を使う） | error | #15 |

## 意味の規則（#6。`tools/claim_lint/semantic.py`・`diff.py`）

台帳・目録・ホップ・カタログへの回答の**宣言**どうしを突き合わせる規則です。受け手が宣言どおりに照合しているかは静的には分かりません。実際の照合は #8 の実行テストで確かめます。error にした規則も「宣言が矛盾していない」ことしか保証しません。

列の「シナリオ A」は、2026-11-23 に `templates/examples/scenario-a` で測った値です。**機会**は規則が調べた行の数（`--format json` の `checked`）、**足した直後**は規則を足した直後、記入例に手を入れる前の指摘の数、**誤検知**はそのうちの誤り、**後**は記入例に欄を足した後の指摘の数です。決め方は下の「意味の規則の重大度の決め方」。

| ID | 内容 | 重大度 | 根拠（版付き） | シナリオ A（機会／足した直後／誤検知／後） |
| --- | --- | --- | --- | --- |
| L1a | 名前空間なしの IANA 登録名（`tools/claim_lint/iana_jwt_claims.yaml`。IANA の claims.csv を 2026-11-23 に取得、163 件）に `registered_ref` がない、型か形が登録と違う（NumericDate は integer・number のどちらも可）。役割・グループ・資格に roles・groups・entitlements 以外の名前（`user_roles` など）を作る。登録どおりの使用（`roles` を string の配列で、`registered_ref` つき）は通る（req:p02-roles-groups-entitlements.R1） | error | RFC 7519 §4.1、IANA JSON Web Token Claims、RFC 9068 §7.2.1.1、RFC 7643 §4.1.2 | 19（採用・既定どおりの全行。登録名の検査はそのうち 14 行）／1（C-sid に registered_ref がない）／0／0 <!-- req:p12-review-viewpoints.R1 --> |
| L1b | 名前空間なしの未登録名（IdP が既定で出し、誰も読まない名前は info）。`namespaces` に宣言していない名前空間、URI でない名前空間。同じ名前の行が型か意味の違うまま複数ある。クレームが載る種別の `issuers` の `iss` が、クレームの `issuers`（`{tenant}` は 1 区画のワイルドカード）にない（req:p01-attack-patterns.R8 req:p02-name-categories.R1 req:p02-name-categories.R2 req:p03-auth0-namespace.R1 req:p04-claim-names.R2 req:p04-single-issuer.R5）。「閉じた範囲で使うなら理由を書く」私的名の逃げ道は設けていない（厳しい側）。草案が定める名前は、`tools/claim_lint/draft_claims.yaml` に（草案の名前と版 → 名前と節）で固定したものだけを warn にする（組織の名前空間に移せないため。#4 のシナリオ B、Txn-Token の `req_wl`・`tctx`・`rctx`）。`registered_ref` がその版の草案の、その名前を定める節（`draft_claims.yaml` に記録した節と一致）を指し、`spec_version` に同じ版があり、`usage` が authz・identifier でないことが条件。架空の草案・草案に無い名前・認可に使う名前は error のまま（PR #44 の点検 B06 の 2 つの悪用の例をテストにした） | error | RFC 7519 §4.2・§4.3、slide:p02-name-categories | 19／0（info 1：Keycloak の `typ`）／0／0 <!-- req:p12-antipatterns-2.R4 --> |
| L2 | IdP が書き換えを許さないクレームを、`modifiers` かフック（`authoritative_writer` の writer に「フック」「hook」「Lambda」）で書く。一覧は `tools/claim_lint/idp_reserved.yaml`（出典 URL と確認日つき）。今は Cognito だけ（Pre token generation の「Claims and scopes reference」、2026-11-23 に確認）。一覧のない IdP は info（req:p03-cognito-pre-token-hook.R3） | warn | Amazon Cognito Developer Guide（Pre token generation Lambda trigger） | 0（Keycloak の一覧がない。info 1）／0／—／0 |
| L3 | `usage` が identifier・authz のクレームが、変わりうる名前（email・preferred_username・upn・name・username・cognito:username など）か、`identifier_properties` が stable: false・reassignable: true・id_scheme が email／phone／username か、`data_category` が user.contact.*（`id_scheme` と食い違えばそれも出す）。display は対象外（req:p02-user-identifier.R2 req:p03-entra-oid-tid.R2 req:p03-cognito-token-use.R4 req:p09-do-not-carry.R4） | error | OpenID Connect Core 1.0 §5.7、slide:p04-immutable-identifiers | 7／0／0／0 <!-- req:p07-db-token-auth.R1 req:p12-antipatterns-1.R6 --> |
| L4 | `authoritative_writer` の同じ段階に書き手が 2 つ以上。同じ書き手が書き手と `modifiers` の両方にいる。`modifiers` の追加・抑止・上書きの区別はスキーマが必須にしている（Cognito のフックが scope を追加・抑止する例は通る）（req:p06-stage-map.R2） | error | slide:p06-stage-map、#3 | 19／0／0／0 <!-- req:p12-review-viewpoints.R4 --> |
| L5 | `volatility`（`never` はトークンの寿命の間に変わらない値として見ない。`0` は即時の反映が要る値で、寿命が 0 より長い種別では遅れ 0 の失効の手段が要る。`never` は #39 でスキーマに入った。スキーマに `never` が無い古い設計書では、0 を前の意味（変わらない）で読む）が、載る種別の受け入れの上限（`max_lifetime`＋`max_clock_skew`）より短いのに、その秒数以内に効く失効の手段がない。数えるのはトークン全体を終わらせる手段（introspection・status_list・ssf_caep・back_channel_logout・revocation_endpoint）と、`note` にそのクレームの ID（`C-…` を語として完全一致）を書いた db_lookup。`propagation_delay` が `volatility` を超える。手段とクレームの結びつきは `note` の ID でしか表せない（限界） | error | slide:p08-stale-claims、slide:p04-carry-or-query | 8／0／0／0 <!-- req:p04-token-is-snapshot.R2 req:p06-issuance-hook.R3 req:p06-access-context.R1 req:p12-antipatterns-2.R2 --> |
| L6 | 個人情報・要配慮個人情報のクレームが、`stored_at: browser` か `visible_to` に browser のある種別に載る。`log_policy: 記録しない` のクレームが、トークン全体を記録する種別（`log_policy: 記録する`）に載るか、`integrity_until` でログに写る。識別子（個人情報）を値のまま記録する（req:p09-logs-traces.R4）。「ログの出力設定に現れる」は、出力設定の入力がないので見ていない | error | slide:p09-logs-traces、slide:p06-flow-browser-to-db | 28／0／0／0 <!-- req:p06-flow-browser-to-db.R1 --> |
| L7 | 種別の `required_claims` にあるクレームの `on_missing` が拒否でない。required_claims の名前（名前空間は `namespace + name` の書き方も可）が台帳の行にない。**逆向き**（#16 の A08）：`on_missing: 拒否` のクレームが、その受け手が受ける JWT の種別（`aud` が受け手を含む）の `required_claims` にない | error | RFC 7519 §4、RFC 9068 §4、slide:p04-reject-missing-required | 31／0／0／0 <!-- req:p12-review-viewpoints.R5 req:p12-review-viewpoints.R12 req:p01-validation-order.R8 --> |
| L8 | ホップの `forwarded_headers` で `strip_inbound` が true でない。`integrity_until` で http_header に写すクレームに、同名のヘッダーを捨てる宣言がない（req:p00-why-hard.R6 req:p06-stage-map.R5） | warn | slide:p06-header-forwarding、OWASP Identity Propagation Cheat Sheet | 0（ヘッダーに写さない）／0／—／0 <!-- req:p12-review-viewpoints.R9 --> |
| L9 | マルチテナント（`tenant_binding` がある、`lite_criteria.multitenant` が Yes、`data_category` に system.operations.tenant）なのに、JWT の AT・内部・Txn-Token に `tenant_binding` がない。`by` の 5 つ（iss・aud・tid・org_id・claim）すべてを見る：claim・tid・org_id は束縛のクレーム（`tenant_binding.claim`、無ければ tid／org_id・organization の名前の行）を特定し、見つからなければ error。束縛に使うクレーム（と iss・aud）に、全受け手の `enforced_at` がない。束縛のクレームを iss（か aud）と照合する宣言（`against`）がない。データ層（`hops` の db_connection の宛先か `against: data_layer`）の照合がない。iss だけでテナントを分ける設計（`by: [iss]`）は通る（req:p02-tenant-org.R4） | error | slide:p05-multitenancy、slide:p02-tenant-org | 1／1（C-tenant-id の iss との照合に `against` がない）／0／0 <!-- req:p05-multitenancy.R1 req:p05-multitenancy.R4 req:p10-delegation-chain-depth.R5 req:p12-review-viewpoints.R14 req:p01-attack-patterns.R3 req:p06-flow-multitenant-saas.R2 --> |
| L15 | 公開クライアント（`issuance_profile.client_type: public`）の RT に、ローテーション＋再利用の検知（`reuse_detection: yes`）も送信者制約もない。送信者制約のある種別に cnf の行がない。cnf の受け手の `enforced_at` がない（req:p02-keys-events-identity-assurance.R2） | warn | RFC 9700 §2.2.2・§4.14.2、RFC 9449 §4.3、RFC 8705 §3.1 | 0（機密クライアント・送信者制約なし）／0／—／0 |
| L16 | **下流ほど絞る**：`upstream` のあるホップで、独自クレーム（`custom_claims`）が上流にない（error。例外なし。上流のトークンに移す）。交換・作り直しのホップ（と、種別の変わるサービスのホップ）で、`aud`・`scope`・`authorization_details` の集合が上流の部分集合でない、または寿命が上流より長い（warn）。Txn-Token を改変せずに渡すホップ（同じ Txn-Token の種別のサービスのホップ）でも、`scope` が上流の部分集合かを見る（Txn-Token の scope は同じか狭い：draft-ietf-oauth-transaction-tokens-11 §13.6）。上流がセッション（トークンでない）のときは見ない。**例外は 2 つだけ**：(1) `kind: exchange` のホップで `aud_replacement: true` を宣言し、aud が 1 つで、ホップの行き先（`to` のサービス）と一致し、ワイルドカード・入口全体の宛先でなく、上流の aud に交換を求めるサービス（`from`）があり、`narrowing_exception.aud` に理由がある（10 字以上）とき、aud の置き換えを info にする（slide:p06-narrow-downstream の例：入口 → orders → inventory）。条件を 1 つでも欠くと error。作り直しのホップでは使えない。(2) Txn-Token のホップの寿命が上流より長いとき、`narrowing_exception`（文字列か `max_lifetime`。10 字以上）に理由があれば info（§6・§13.15。2026-11-23 に本文で確認）。scope・authorization_details と、Txn-Token でない交換の寿命には例外を設けない（`narrowing_exception` にそのキーを書くとスキーマの誤り）。落ちる例はケーススタディの実測（Keycloak 26.8 の交換で、元のトークンに無かった orders 宛てが出た。slide:p10-token-exchange-not-narrowing）と、PR #44 の再点検の 11 通り（`tools/tests/test_claim_lint_semantic.py` の L16 のシナリオ B の回帰テスト） | error（独自クレームの部分）／warn（交換・作り直しのホップで aud・scope・authorization_details・寿命が上流を超える部分。シナリオ A に該当のホップがなく、機会 0） | author-proposal（slide:p06-narrow-downstream の組織規則、tracking #6）。scope は draft-ietf-oauth-transaction-tokens-11 §13.6（発行の scope は元のトークンと同じか狭い）・§13.15（置き換え）・RFC 8693 §5 | 独自クレームの部分 1（H3。H2 は上流がセッションなので見ない）、広げる部分 0（`checked` の `L16.widen`）／0／0／0。発行されたトークンで同じことを確かめる実行版は `test:negative_tests#exchange-narrowing`（#8、`tools/runtime_tests/narrowing.py`） <!-- req:p12-review-viewpoints.R7 req:p10-token-exchange-not-narrowing.R1 --> |
| L17 | 採用した JWT の種別に `unknown_kid`・`jwks_cache_ttl` がない（#16 の A09。見るのは宣言の有無で、値が十分かは見ない）。`alg_allowlist` に none、または HS* と `jwks_uri` の発行者が並ぶ。種類の違う種別が同じ `typ`。`typ`・`alg_allowlist`・`issuers`・`max_lifetime`・`key_rotation` の有無は R1 が見る | error | RFC 8725 §3.1・§3.11、slide:p01-key-rotation-jwks | 2／0／0／0 <!-- req:p10-delegation-chain-depth.R5 req:p12-antipatterns-2.R9 req:p12-review-viewpoints.R11 --> |
| L18 | status が deprecated・sunset のクレームを読む受け手（`consumers`）がいる。`sunset_on` を過ぎたか sunset なら、その旨を出す（req:p11-schema-contract-tests.R6） | warn | slide:p11-change-procedure | 0（deprecated の行がない）／0／—／0 <!-- req:p04-forward-compatibility.R4 --> |
| L21 | 却下した種別を参照している（採用のクレームの `carried_in`、ホップ、該当のカタログへの回答）。目録で採用・既定どおりの種別が、どこからも参照されていない（warn）。目録にない ID の参照は R8・REF・R2 が error にする。シーケンス図の参照は、図の ID の書き方が #4 で決まるまで見ない | error（参照）／warn（未参照） | slide:p08-token-types-lifetimes | 8／0／0／0 |
| L22 | カタログの種類（`templates/catalog/token_kinds.yaml`、17 件）のうち、目録に行（採用か、却下＋理由）がないもの | error（Lite は warn） | #2、slide:p08-token-types-lifetimes | 17／0／0／0 |
| L23 | 採用した種別の `max_lifetime` が組織の上限（`tools/claim_lint/lifetime_caps.yaml`。`--lifetime-caps` で自組織のファイルに替える）を超えるのに `lifetime_exception` がない。RT とセッションに `idle_timeout` がない・絶対的な上限を超える・上限を超える（#16 の A14）。寿命を platform 以外（tenant_admin など。`lifetime_set_by`）が設定できるのに、受け手が exp − iat ≤ max_lifetime を強制する宣言（exp の `enforced_at` かホップの `validates.checks`）がない（#16 の A01）。3 種類以上がすべて同じ寿命なら warn（スライドの「1 つの数字で語らない」） | error／warn（同じ寿命） | NIST IR 8587 §5.3.1.1、NIST SP 800-63B-4 §2.2.3、RFC 6749 §4.1.2（上限ごとの根拠はファイルに書いた）、slide:p08-choosing-lifetime | 6／0／0／0 <!-- req:p08-choosing-lifetime.R2 --> |
| L25 | 採用した JWT の種別に `key_source` がない（ヘッダーの jku・x5u をたどらず、jwk・x5c を信頼しない。`header_key_params: reject` はスキーマが固定する） | error | RFC 8725 §3.10、slide:p01-dangerous-header-params | 2／0／0／0 |
| L27 | `required_claims` を宣言した JWT の種別で、exp・aud・iss が無い。`max_clock_skew` が無いか 300 秒を超える（上限は筆者の提案、tracking #6）。`typ: at+jwt` なら RFC 9068 §2.2 の REQUIRED（iss・exp・aud・sub・client_id・iat・jti）が `required_claims` にあるか、台帳の却下の行で逸脱を記録している（記録があれば info。#16 の A07）（req:p01-attack-patterns.R5） | error | RFC 9068 §2.2、RFC 7519 §4.1.4 | 2／1（IDT に max_clock_skew がない）／0／0（info 1：AT の client_id の逸脱） |
| L31 | `usage` が authz・identifier のクレームの `provenance` が「本人が編集できる値」「呼び出し側の申告」。書き手（`authoritative_writer`・`modifiers`）の `configurable_by` に platform 以外（tenant_admin・end_user・client・caller）がいるのに、`enforced_at` に iss・API 側の設定・データ層との照合（`against` の iss・api_config・data_layer）がない。他のクレームとの照合（`against: [other_claim]` と `with`）は、その相手が同じ条件を満たせば通る（#16 の A01）（req:p03-cognito-pre-token-hook.R4 req:p04-split-by-writer.R2 req:p07-three-db-paths.R4 req:p07-row-level-security.R2 req:p07-cloud-attributes.R1） | error | slide:p04-split-by-writer、slide:p07-row-level-security | 7／7（`against` の列がなかった）／0／0 <!-- req:p12-antipatterns-1.R7 req:p12-review-viewpoints.R15 --> |
| L37 | 認可のクレーム（`usage: authz`）が無いときに拒否しない（`on_missing` が既定値・無視）のに、`absent_semantics.absent` がない。台帳に `effect`（許可・制限）の列がまだないので、「許可のクレームで無いときに許す」の向きは見ていない（一部の実装） | error | slide:p04-absent-null-false-empty | 1／0／0／0 |
| L43 | 採用した Txn-Token の運搬（`transport`）が `txn_token_header` でない。外部の AT を含める宣言は見ていない | warn | draft-ietf-oauth-transaction-tokens-11 §12.1（Txn-Token ヘッダーを使う、MUST）・§12（Authorization ヘッダーを使わない、MUST NOT）。独立点検で本文を確かめた、slide:p06-transaction-tokens | 0（Txn-Token を却下）／0／—／0 <!-- req:p06-transaction-tokens.R1 --> |
| L62 | `issuance_profile` の選択から `templates/registry/issuance_effects.yaml` で導かれる要件（`check` の `op`：present・absent・equals・includes・all_consumers・not_required）を台帳が満たしていない。宣言から決められない検査（`grant:` の値）は info | warn | 表の行ごとの `refs` | 0（どの行の when も成り立たない）／0／—／0 |
| L63 | FAPI 2.0（`conformance_profile: fapi2_security`）なのに、AT に送信者制約がない、PAR・PKCE を使わない（`E-fapi2`） | warn | FAPI 2.0 Security Profile（Final）§5.3.2.1・§5.3.2.2 | 0／0／—／0 |
| L64 | mTLS を入口で終端するのに、証明書を渡すヘッダーに、同名を捨てる規則と入口だけが書けるという信頼境界がない（`E-mtls-entry`） | warn | RFC 8705 §6.5、author-proposal（tracking #3） | 0／0／—／0 |
| L65 | クレームの `confidential_from` の相手が、載る種別の `visible_to`（トークン全体を記録する種別では logs も）にいる。JWE を使い、その相手が復号できない（`jwe.decryptors` にいない）なら通る。相手の書き方：役割（browser・gateway など）か `hop:<名前>`（経路の特定の中継）。`hop:<名前>` は gateway でもあるので、`confidential_from: [gateway]` はすべての `hop:<名前>` に当たり、`confidential_from: [hop:nginx]` は `visible_to: [gateway]` にも当たる | error | RFC 7515 §1（JWS は読める）、RFC 7516、slide:p09-jws-is-readable | 3／0／0／0 |
| L66 | JWE を使う種別で、ネストが「署名してから暗号化」でない。内側の JWS を検証する設定（`alg_allowlist`・`issuers`）がない。復号できる相手が `visible_to` にない | warn | RFC 7519 §11.2、slide:p09-jwe-sd-jwt | 0（JWE を使わない）／0／—／0 |
| L67 | 認可・識別子のクレームを HTTP ヘッダーに写す（`integrity_until` の http_header、または target がヘッダーを指す other）のに、そのヘッダーを入口だけが書ける（`forwarded_headers` の `strip_inbound`・`written_only_by`）と宣言していない。写し先の `trust_boundary` が「なし」などの中身のない値。ほかの写し先（DB のセッション変数など）に何を求めるかは見ていない（一部の実装） | warn | slide:p06-header-forwarding、slide:p08-copies-outlive-token | 0（ヘッダーへの写しがない。信頼境界の中身の検査は 1 行：C-tenant-id の db_session）／0／—／0 |
| L68 | 接続元の詳細（IP・端末の識別子。名前か `data_category` の user.device）をトークンに載せる | warn のみ | slide:p09-do-not-carry | 19／0／—／0 |
| L69 | 認可の配列のクレームで、名前・説明がエンドポイント・操作ごとの許可を思わせるか、`max_items` が 50 を超える | warn のみ | slide:p09-do-not-carry、slide:p05-role-explosion | 1／0／—／0 |
| L70 | 名前から推測した分類（password・secret・api_key → user.authorization.credentials、email、phone、birth）と `data_category` が食い違う、または無い。推測は名前だけによる | warn のみ（error にしない） | research/claims-as-code/report.md、fideslang 3.1.4 | 2／0／—／0 |
| L71 | 台帳・目録・ホップの YAML に、メールアドレス（example.com などの予約の名前を除く）・電話番号・JWT・秘密らしい文字列（秘密鍵・AWS のアクセスキー・`sk_live_` など）がある | warn のみ | slide:p09-do-not-carry、`.gitleaks.toml` | 3 ファイル／0／—／0 |
| L72 | 組織の名前空間で採用・status が proposed 以上の共有クレームに、追加前の 25 問の回答（設計書のディレクトリの `claim_request_*.md`。「- 対象：」の行に台帳の ID を `` ` `` で書き、`\| 番号 \| 問い \| 回答 \|` の表に 1〜25 が並ぶ）が揃っていない（空欄・未定・TBD など）。#4 で error に上げた：追加前の 25 問は Lite でも必須の関所（slide:p11-pre-add-questions-1 の「答えられない問いが残るなら共有クレームにしない」）で、シナリオ A の共有クレーム 4 つに 25 問を揃えた後の指摘は 0 件（誤検知 0）。シナリオ B でも 9 つで 0 件 | error（Lite も同じ） | slide:p11-pre-add-questions-1・slide:p11-pre-add-questions-2 | 4／3（C-user-id・C-roles・C-v に 25 問がない）／0／0（#4 で 3 ファイルを足した後） |
| L73 | `--profile lite` なのに、#4 の Lite の判定の 5 問（`catalog_answers.yaml` の `lite_criteria`：crosses_boundary・multitenant・delegation_or_exchange・new_issuer・regulated）に答えていない、または 1 つでも Yes（#16 の A17）。Full では見ない。Yes があるのに Lite の欄で書いた設計書の扱いは 1 つ：この warn で知らせ、レビューの受け付け（`templates/review/procedure.md` の段 0）で Full に書き直すよう返す（`templates/README.md` の「Lite と Full の判定」、#61）。error にしないのは、測定の記録（シナリオ A、パイロットのシナリオ C）を CI で検査し続けるためと、error の規則の追加が版のメジャーに当たるため | warn | #4 の Lite の定義、research/template-design/gate1.md の 5. | Lite で 1／1（multitenant が Yes）／0／1 |
| L10 | `python tools/claim_lint diff --base <git ref> <設計書>`：前の版と比べて、採用のクレームの削除（前の版で sunset なら info）・改名・型・形・用途の変更、必須化（on_missing が拒否に、`required_claims` に名前を足す）、語彙（`value_vocabulary.values`）から値を消す・変える、受け手のいるクレームを種別から外す、採用の種別の削除・typ の変更を error、語彙に値を足すのを info、description・not_meaning の変更を warn にする（req:p11-why-govern.R4） | error（description は warn） | slide:p11-why-govern、slide:p11-change-procedure | main との比較で 0。履歴との比較：befd117（#16 の最初）から 2 件（C-scope の形を single から space_delimited に直した、AT の required_claims に azp を足した＝A08）、b684571 から 1 件。どちらも正しい検出（scope は宣言の訂正で、実物のトークンは変わっていない）／誤検知 0 |

`against` と `with` は、この PR で `enforced_at` の要素に足した任意の列です（`templates/registry/README.md` の `enforced_at`）。

### 意味の規則の重大度の決め方

新しい規則は warn で入れ、**シナリオ A で 1 行以上を調べ（機会が 1 以上）、誤検知が 0 件のものだけ** を error にしました（`semantic.py` の `SEV`。`tools/tests/test_claim_lint_semantic.py` が「error の規則はシナリオ A で機会が 1 以上」を確かめる）。#17 の R3b の `no` の分岐は機会 0 のまま error にしましたが、#6 では機会 0 の規則（L2・L8・L15・L43・L62〜L64・L66・L67）と、規則の中で機会 0 の部分（L16 の aud・scope・寿命）を warn に留めました。誤検知を測れていないからです。シナリオ B（#4）で機会ができたら測り直し、誤検知 0 なら error に上げる PR を出します。

ほかに warn に留めたもの：
- L18：#6 の本文が warn
- L68〜L71：#6 の本文が「warn から始める」（L70 は error にしない）
- L72：3 件とも正しい指摘だが、25 問の様式（`templates/claim_request.md`）は #4 で決まる。#4 で C-user-id・C-roles・C-v の 25 問を書いてから error に上げる
- L73：Lite の判定の 5 問は #4 で決まる。シナリオ A は Full に当たるのに Lite で書いた例（意図して残した正しい指摘）

**シナリオ A の誤検知は全規則で 0 件でした。** 足した直後の指摘は 15 件（L1a 1・L9 1・L27 1・L31 7・L72 3・L73 は Lite で 1・L1b／L2／L27 の info を除く）で、すべて正しい指摘（宣言の欄が無いか、値が足りない）でした。L72・L73 の 4 件を除いて、記入例に欄を足しました（`design.md` の 13.）。シナリオ A は 1 件だけなので、誤検知 0 件は弱い証拠です。

### R8 の info の見直し（#16 からの引き渡し）

R8 の info「同じクレームが 2 つ以上の種別に載る」から、名前空間なしで `registered_ref` があり、ID トークン（OpenID Connect Core 1.0 §2）か JWT の AT（RFC 9068 §2.2・§2.2.1）が定める名前（iss・sub・aud・exp・iat・auth_time・nonce・acr・amr・azp・client_id・jti）を除きました。シナリオ A の誤検出の候補 4 件（iss・sub・aud・azp）が消え、独自クレームが 2 つの種別に載れば今までどおり出ます。L26（ID トークンだけが読むクレームの置き場所、#18 の full）との分担は、L26 を作るときに決めます。

### 未実装の規則

- **未実装（full）**：対応表で提案した lint のうち、**#6・#18 が担当する要件では** tier が full の要件にしか結びつかないもの。v1.0.0 の後に需要を見て進める（#11）
  - full の要件にしか結びつかない：L26・L28・L29・L30・L32・L33・L35・L38・L39・L40・L42・L44・L46・L47・L48・L49・L50・L51・L52・L53・L54・L56・L57・L58・L59
  - ほかの issue の core の要件にも結びつくが、その要件はほかの成果物（観点書・25 問の様式・台帳の README）でも解決する：L24（p04-design-checklist.R5・p11-pre-add-questions-1.R8）、L34（p04-design-checklist.R3・p11-pre-add-questions-1.R4）、L36（p04-design-checklist.R6）、L41（p12-antipatterns-2.R6・p12-review-viewpoints.R8）、L45（p12-antipatterns-2.R8・p12-review-viewpoints.R17）、L55（p12-antipatterns-2.R7）、L60（p11-pre-add-questions-2.R7）、L61（p12-review-viewpoints.R3）。担当は #3・#4・#5。担当の issue が lint を要ると決めたら、その tier の要件として #6 で実装する
- **一部だけ実装**：L21（シーケンス図）、L37（`effect` の列が #3 にない）、L43（外部の AT を含める宣言）、L6（ログの出力設定）、L67（ヘッダー以外の写し先に何を求めるか）、L17（typ・alg_allowlist などの有無は R1 に任せる）、L5（失効の手段とクレームの結びつきは note の ID だけ）、L16（最初の発行で受け手ごとに絞ったかは見ない）。対応表のこれらの要件は未着手のまま
- **対応表で core だが、実装済みにしていない要件**：テンプレート（#4）・観点書（#5）・実行テスト（#8）・`render`・`calib` の成果物が要るもの、要件の文が規則より広いもの（例：p04-single-issuer.R1「書くのは組織の発行者 1 か所」は L4 の「段階ごとに 1 つ」より広い）。`python tools/trace_check.py` の #6 の行が数を示す

## 目的と仕組みの規則（#18。`tools/claim_lint/purpose.py`）

**L11〜L14 は宣言の整合の検査です。** 設計者が書いた宣言（答える問い・答えない問い・照合する場所・草案への依存）が互いに矛盾していないかだけを見ます。受け手が実際に照合しているか、入れ子の act を本当に拒否しているかは、静的には判定できません。実際の照合は #8 の実行テスト（拒否されるべきトークン。`templates/runtime/negative_tests.md`、`python tools/runtime_tests/run.py`）で確かめます。**error にしたからといって「機械で保証した」とは言えません。**

| ID | 内容（宣言の整合の検査） | 重大度 | 根拠（版付き） | 対応する #8 の実行テスト | シナリオ A（機会／足した直後／誤検知／後） |
| --- | --- | --- | --- | --- | --- |
| L11 | `usage` が authz・identifier のクレームを読む受け手（`consumers`）のそれぞれに `enforced_at` がない。`tctx` に照合の規則がない、`tctx` の項目（`value_vocabulary.values`）を照合する規則がない。AT に sub・scope・authorization_details を載せるのに `enforced_at` がない（warn。載せるなら判断に使う）（req:p05-coarse-fine-layers.R5 req:p06-validation-split.R4 req:p10-human-approval-evidence.R3） | error（ASVS の部分は warn） | author-proposal（tracking #18）：本文と `tctx` の照合は仕様では MAY（draft-ietf-oauth-transaction-tokens-11 §12.2）。OWASP ASVS 5.0.0 10.3.2 | `test:negative_tests#tctx-mismatch`、`test:negative_tests#approval-mismatch` | 9（authz・identifier の受け手 7、ASVS の部分 2。tctx の部分は 0）／3（C-iss・C-sub の saas-web の照合が無い 2 件、C-scope の warn 1 件）／0／1（C-scope の warn。正しい指摘で、設計が逸脱を選んだ：Keycloak が外せない scope=openid を判断に使わない。design.md の 6.） |
| L12 | 同じ問いが `answers` と `does_not_answer` の両方にある。questions.yaml の `not_this` で取り違えやすいとした 2 つの問いに、同じクレームで答えている（`act` と Txn-Token、`sub` と `act` の取り違え）。入れ子の act の下の行（`path` に act が 2 つ以上。名前は問わない：`act.act`・`act.act.sub`）を「誰が代理して実行しているか」（q-actor）の答えにしている。`not_this` は片方向だけに書かれていても対として見る | error | RFC 8693 §4.1（最も外側の act だけが今の代理者）、slide:p05-one-request-carries | `test:negative_tests#nested-act` | 5（同じ問いの両方・not_this の部分。入れ子の act の部分は該当の行がなく 0）／0／0／0 |
| L13 | `catalog_answers.yaml` の `questions` に、問いの一覧（`templates/registry/questions.yaml` の questions、11 問）のそれぞれが要るか（`needed`）の回答がない。不要とした問いに理由がない。要るとした問いに、答える仕組み（その問いを `answers` に持つ採用のクレームか、クレームでない仕組みの `channel`）が 1 つもない | error | slide:p05-one-request-carries、#11 の「問い × 仕組み」 | —（設計の網羅。実行テストはない） | 11／1（`questions` の節が無い）／0／0 |
| L14 | 草案に依存する行（`refs` が draft-…-NN・preview を指す、草案が定めるクレーム txn・tctx・req_wl・purp・azd・status など、草案のトークン Txn-Token・ID-JAG・状態リストに載る）に `spec_version` か `revisit_trigger` がない。草案の purp・azd に依存している。草案の種別を採用したのに、版付きの草案の参照か `revisit_trigger` がない（req:p06-transaction-tokens.R8 req:p08-revocation-propagation.R6 req:p10-vendor-features.R2） | warn | slide:p10-guidance-standards（草案を必須と書かない）、slide:p03-keycloak-aud-lightweight（preview の機能） | — | 0（草案に依存する行がない）／0／—／0 <!-- req:p03-recent-changes.R2 --> |

重大度は意味の規則と同じ決め方です（シナリオ A で機会が 1 以上、error の部分で誤検知 0 のものだけ error）。L14 は #18 の本文が warn です。L11 の ASVS の部分（warn）は、シナリオ A の 1 件が正しい指摘で、設計が逸脱を選んだものです。逸脱を記録する欄（L27 の却下の行に当たるもの）がまだないので、error に上げず warn に留めます（欄は別の PR で作る）。L11 の tctx の部分と L12 の入れ子の act の部分は、シナリオ A に該当の行がなく機会 0 です（落ちる例のテストだけ）。

カタログそのものの検査（列、種になる一覧との差集合、主体の状態の行列、`sources.md` の件数）は、設計書ではなくカタログの検査なので `tools/catalog_check.py` に分けました（#2）。R3 はその `closure()` を、R2・R4 は `_weak_reason()` を、R4 は `seed_items()`・`STATES`・`LAYERS`・`RESULTS` を使います。

## 網羅の規則の入力（`catalog_answers.yaml` の節）

```yaml
idp: {name: keycloak, version: "26.8"}       # R3・R3b・R2（Lite の引き継ぎ）。カタログにない IdP は enumerable・trigger_list
answers:
  - {event: I04, answer: 対象外, inherit: idp-default, setting_checked: "…"}   # Lite だけ（下）
  - {event: I25, answer: 該当, token_types: [AT], note: "…", hook_checked: "…"} # hook_checked は R3b の unknown を info にする
subject_states:                               # R4
  unused_layers: {Logout Token: "使わない理由"}
  states:
    subject-states/suspended:
      AT: {result: 影響なし, basis: "許す遅れか対策"}
pairwise:                                     # R6
  subject_kinds: {利用者: {answer: 該当}, ワークロード: {answer: 対象外, reason: "…"}, システム: {answer: 対象外, reason: "…"}}
  combinations:
    - {subject: 利用者, event: I01, stage: ①, note: "検討したこと"}
outside_enumeration:                          # R9
  answer: "何を探して、何が無かったか（見つかったか）"
  respondent: "…"
  date: "2026-11-22"
  searched: ["見た資料・図", "…"]
  found: [{name: "…", handled_as: "…"}]
```

記入例は `templates/examples/scenario-a/catalog_answers.yaml` です。

## Lite の既定の回答の引き継ぎ

#4 の改訂（縮小 Lite。`research/template-design/gate1.md` の 10.）に合わせました。`--profile lite` のときだけ、「対象外」の回答に `inherit: idp-default` と `setting_checked` を書けば、`assumption`・`breaks_when` を省けます。`setting_checked` には、どの設定を、どこで、いつ確かめたかを書きます。

- **引き継げるイベント**：カタログの行の `idp.<IdP>.lite_inherit: true` の印があるものだけです。Keycloak の I03・I04・I05・I07 に付けました。gate1.md の 10. の「引き継ぐ」4 件で、どれもクライアントの設定のスイッチ 1 つで止めていて、指摘が出ていません。I03 はクライアントポリシーの executor で、`stop_setting` の `scope` は realm です。それでも gate1.md の分類に合わせました。
- **手で書くイベント**：印のないイベントは手で書きます。
  - 指摘が出た行（I06・I09・U07・U10 など）
  - レルム・クライアントの既定に依存する行（I08）
  - 利用イベント（U05・U08 など）
  - Auth0 の行（gate1.md の分類がない）
  - カタログの IdP でない IdP
- **`setting_checked` の検査**：カタログの `stop_setting.setting` の英字の語（6 字以上）のどれかを含むことを求めます。例：I04 なら Direct か Grants。
- **Full では**：`inherit` を書くと R2 の error です。

PR #33 の独立点検より前は、`stop_setting.scope == client` で判定していました。そのため I08 が引き継げ、I03 が引き継げない、という #4 と逆の結果になっていました。印は `catalog_check` が確かめます（`true` だけ、`stop_setting` のある発行イベントだけ）。新しく「指摘が出た行」が見つかったら、印を外します。「指摘が出たか」は機械では判定できません。

## R6 の証拠の状況

R6 の目標（2 因子の組をすべて一度は検討する）は、組み合わせテストの知見を設計の検討に当てはめた筆者の提案です（tracking #17）。根拠は NIST の組み合わせテストの研究だけで、それもソフトウェアの障害についてのものです。NIST が示す 10 種類のアプリケーションのデータでは、2 因子までの組み合わせで起きた障害の割合はおおよそ 47%〜97% と幅があります（グラフからの読み取り。[NIST ACTS](https://csrc.nist.gov/projects/automated-combinatorial-testing-for-software/combinatorial-methods-in-testing/interactions-involved-in-software-failures)。`research/template-design/report.md` の訂正）。設計の想定漏れを pairwise でどれだけ拾えるかは、測っていません。そのため R6 は warn にとどめ、昇格もしません。対象は設計書が「該当」と答えた主体と発行イベントだけなので、答えなかった主体・イベントの漏れは R2 と R9 で拾います。

## 重大度の決め方と、シナリオ A での誤検知の数

新しい規則は warn から始め、#17 の表が error としていて、シナリオ A（`templates/examples/scenario-a`）で誤検知が 0 件のものだけを error にしました（2026-11-22 に測定）。測り方：規則を足した直後に、記入例に手を入れずに実行し、出た指摘を 1 件ずつ「正しい指摘（記入例に欄が無い・値を確かめていない）」か「誤検知」かに分けました。その後、記入例に欄を足して再び実行しました。

| 規則 | 足した直後の指摘 | 誤検知 | 欄を足した後 | 重大度 | 理由 |
| --- | --- | --- | --- | --- | --- |
| R2（中身の検査を足した） | 0 | 0 | 0 | error（既存。下げない） | 対象外 49 件のすべてが新しい検査を通った（I34 を足した後は 50 件） |
| R3 | error 1（`idp` がない） | 0 | info 1 | error | 正しい指摘。シナリオ A で動いたのは Keycloak の分岐だけ。測ったときは一覧なしの分岐で、独立点検の後は一覧ありの分岐（`keycloak-grant-types`）。**Auth0・Cognito・文書で未確認・一覧が存在しないの分岐は、どの設計書でも測っていない**（テストの例だけ） |
| R3b | warn 1（`idp` がない） | 0 | warn 2（I25・I26 が unknown） | error（no）・warn（unknown） | unknown の 2 件は正しい指摘（カタログで確かめていない）。**`no` の分岐はシナリオ A で一度も動いていないので、誤検知は測っていない**（機会が 0 回）。また、最初の実装は Keycloak の `typ`（IdP 自身が書く protocol のクレーム）を独自クレームに数え、2 件の指摘に並ぶクレームの一覧を誤らせた。指摘そのものは正しかったので誤検知には数えず、「指摘の中身の誤り 1 件」として記録する。定義は直した |
| R4 | error 1（`subject_states` がない） | 0 | 0 | error | 正しい指摘。欄を足した後の 35 セル＋使わない層 2 つで誤検知 0 |
| R6 | warn 1（`pairwise` がない） | 0 | info 1 | warn | 上の「R6 の証拠の状況」により上げない |
| R9 | error 1（`outside_enumeration` がない） | 0 | 0 | error | 正しい指摘。独立点検の後に足した検査（日付、仮の値、具体的な出どころ）でも、シナリオ A の回答は通った |
| R10 | 0 | — | 0 | warn | **測っていない**。測った日は、どの期限（2027-02-20）より前だった。期限切れは出どころの見直しの合図で、設計書の誤りではない |

シナリオ A は 1 件だけなので、誤検知 0 件は弱い証拠です。ほかの設計書で誤検知が出たら、規則を直す PR を出します（error の抑止はしない）。

## R1 の必須の列

| 行の種類 | 必須の列 |
| --- | --- |
| すべてのクレーム | `id`・`name`・`decision`・`rationale`（R1 は、空白だけの文字列と、空白だけの要素しかない配列を空とみなす） |
| `採用`・`既定どおり`（トークンに載せる行） | 上に加えて `namespace`（最上位は `null`）・`type`・`shape`・`description`・`not_meaning`・`usage`・`issuers`・`authoritative_writer`・`issue_events`・`consumers`（読む受け手がいなければ `[]`）・`carried_in`・`on_missing`・`max_bytes`（配列は `max_items` も）・`overflow_strategy`・`pii_category`・`log_policy`・`owner`・`source_system`・`volatility`・`propagation_delay`・`status`・`data_category`・`confidential_from`（改ざん防止だけで足りるなら `[]`。v1 で足した） |
| `採用`・`却下` | `refs`・`assumption`・`revisit_trigger` のうち 2 つ以上（#3 の「判断」の区分） |
| トークン種別 | `id`・`kind`・`decision`・`rationale`・`format`。`採用`・`既定どおり` は `purpose`・`issuer`・`holder`・`max_lifetime`・`stored_at`・`transport`・`revocation`・`visible_to`（RT とセッションは `idle_timeout` も）。JWT はさらに `typ`・`alg_allowlist`・`issuers`・`key_rotation`・`jwe`（使わないなら `{used: false}`。v1 で `visible_to`・`jwe` を足した）。ヘッダー（Authorization・Cookie）で運ぶ JWT は `size`（R8 の入力） |

`--profile lite`（縮小 Lite。`research/template-design/gate1.md` の 10.、#4）では、上の表から次を減らします（`core.py` の `LITE_GENERATED`・`LITE_UNREAD_KEEP`）。台帳の README の 2.「縮小 Lite の印」と同じ規則です。**列を減らす規則は、縮小 Lite（`claim_lint --profile lite`）だけのものです。Full（`--profile` を付けない）では、既定どおりで `consumers: []` の行にも、トークンに載せる行の必須の列をすべて書きます。**

| 行の種類 | Lite で必須にしない列 |
| --- | --- |
| `採用`・`既定どおり`で、`consumers` が空でない行 | 生成する列：`issue_events`・`propagation_delay`・`status`・`issuers`（IdP モジュール・カタログ・`token_types`・既定の状態から生成する）。単一値（`shape` が `array` でない）の `overflow_strategy`（既定は上限で固定） |
| `既定どおり`で `consumers: []` の行（IdP が出すが誰も読まない行） | `namespace`・`type`・`shape`・`max_bytes`（配列は `max_items` も）・`pii_category`・`carried_in`・`data_category`・`confidential_from` だけを必須にし、ほかの載せる行の列は求めない（R8 の計算と判断に要るものだけ） |
| トークン種別の `却下` の行 | 変えない（`kind`・`decision`・`rationale` に加えて、スキーマが `format` を求める） |

スライド 134（slide:p11-registry-fields）の 12 の項目は、載せる行の必須の列に入っています。項目と列の対応は `templates/registry/README.md` の「スライド 134 の 12 項目と台帳の列」にあります。12 番目の「変更履歴」は列ではなく Git の履歴で持ちます。

## R8 の計算

JWS（コンパクト形式）のエンコード後の長さを、宣言の値から計算します（`tools/claim_lint/r8.py`）。

```
最悪のサイズ = ceil(4/3 × ヘッダー) + ceil(4/3 × ペイロード) + ceil(4/3 × 署名) + 2（ドット 2 つ）
              Authorization の Bearer で運ぶなら + 7（"Bearer "）
```

- `ceil(4n/3)` は、n バイトを base64url（パディングなし）にした長さです（RFC 7515 §2、RFC 4648 §5）。
- ペイロードは、載る全クレームの JSON（空白なし）の UTF-8 のバイト数です。文字列は `max_bytes`＋引用符 2、数値は `max_bytes`（桁数）、配列は `2 ＋ max_items × 要素 ＋（max_items − 1）`、メンバーは `キー（引用符つき）＋ コロン ＋ 値`、オブジェクトは `2 ＋ メンバー ＋（メンバー − 1）`。`namespace` の付いたクレームは、名前空間の名前をキーにした 1 つのオブジェクトにまとめます。
- ヘッダーは、`size.header.params` から同じ規則で計算し、`serializer_extra_bytes`（発行者の JSON の書き出しが足す空白）を足します。Keycloak 26.8.0 では 4 バイトでした（見本トークンの実測。`research/template-design/gate1.md`）。
- 署名の長さは、HMAC は RFC 7518 §3.2、ECDSA は RFC 7518 §3.4、RSA（RS・PS）は鍵の長さ（RFC 8017 §8.1.1・§8.2.1）、Ed25519 は 64 バイト（RFC 8032 §5.1.6）です。
- 経路の上限は `tools/claim_lint/path_limits.yaml`（一次資料で確かめた値だけ）か、根拠つきでその場に宣言した値です。確かめていない値は既定に入れません（`research/template-design/unverified.md` の V01〜V04）。
  - `header_field` の上限（nginx・Apache httpd・HTTP.sys の MaxFieldLength）とは、`Authorization: Bearer <トークン>` の行（ヘッダー名を含む）を比べます。ヘッダー名を数えるのは保守側に倒した読み方で、各サーバーが数えるかは確かめていません（筆者の提案。tracking #16）。
  - `all_headers` の上限（Tomcat・Node.js・HTTP.sys の MaxRequestBytes）とは、上の行に `size.other_headers_bytes`（要求行とほかのヘッダーの見積もり）を足して比べます。宣言がなければ error です。
  - HTTP/2・HTTP/3 の圧縮による割り引きはしません（V03）。

| 判定 | 条件 |
| --- | --- |
| error | 最も厳しい上限を超える。配列に `max_items` がない（値域が無制限）。配列に `overflow_strategy` がない。載る行に `max_bytes` がない。`carried_in` のトークン種別が目録にない。経路の上限が既定の一覧にも宣言にもない。署名の長さが決まらない |
| warn | 最も厳しい上限の 75% を超える（report Q9 は 50〜75% としている。上の端を使った。筆者の提案、tracking #16） |
| info | 計算の結果。同じクレーム（`usage` が protocol でないもの）が 2 つ以上のトークン種別に載る（重複の候補）。ID トークンと AT の両方の仕様が定める登録名は数えない（#6。下の「R8 の info の見直し」） |

`overflow_strategy` に切り詰め（truncate）は書けません（スキーマの列挙にない）。error のメッセージは「載せるか、問い合わせるか」（slide:p04-carry-or-query）へ誘導します。軽量アクセストークン（Keycloak）は、解決策として誘導しません。

### 限界

R8 は宣言の値を信じます。宣言と実際の発行のずれは、見本トークンとの照合（`tools/tests/test_claim_lint.py` の golden）と、発行されたトークンの計測で補います。配列は `max_items × max_bytes` で数えるので、要素の長さがばらつく配列では実際より大きく出ます（安全側）。
