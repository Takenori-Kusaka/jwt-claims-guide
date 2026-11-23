# 変更の記録

`templates/` の変更を記録します。版は semver で、タグは `templates-vX.Y.Z` です。版の上げ方は [CONTRIBUTING.md](CONTRIBUTING.md) の「版の管理」にあります。

## 未リリース（Unreleased）

### 追加

- `CONTRIBUTING.md`：根拠の種類と書式、完了の定義、点検者の取り決め、公開物の取り扱い、題材（#13）
- `casestudy-mapping.md`：ケーススタディ（コミット `080b8da`）との対応表と、正とする側の決定（#13）
- `README.md`：準備中の入口
- `LICENSE`：CC0 1.0 Universal
- `catalog/issue_events.yaml`・`catalog/use_events.yaml`：発行・利用イベントのカタログの v0 の一部（Keycloak、シナリオ A に関係するものだけ。#16）
- `registry/claims.schema.json`・`registry/token_types.schema.json`・`registry/README.md`：台帳のスキーマ v0（シナリオ A に要る列だけ）と、スライド 134 の 12 項目との対応表（#16）
- `examples/scenario-a/`：シナリオ A（Keycloak）の記入例。台帳・トークン目録と発行方式・カタログへの回答・設計書（Lite）（#16）
- `casestudy-deviations.yaml`：記入例とケーススタディの判定の、意図した食い違いの一覧（#16）
- `examples/scenario-a/catalog_answers.yaml`：claim_lint の網羅の規則（#17）が求める節を足した。`idp`（R3・R3b）、`subject_states`（R4：7 状態 × 5 層の 35 セルと使わない層 2 つ）、`pairwise`（R6：主体の種類 3 つと組み合わせ 7 つ）、`outside_enumeration`（R9）。既存の `answers` は変えていない。設計書の `catalog_answers.yaml` にこの節が無いと、Full では R3・R4・R9 が error になる（未リリースのため版は 0.1.0 のまま）
- `catalog/`：カタログを全体に広げた（#2）。発行イベント 33 件・利用イベント 28 件、トークンの種類 `token_kinds.yaml`（17 件）、主体の状態の行列 `subject_state_matrix.md`（7 状態 × 7 層）、種になる一覧 `seeds.yaml`（17 一覧・345 項目）と出どころ `sources.md`。検査 `tools/catalog_check.py`

- `registry/`（#3、台帳 v1。版は 0.2.0）：`hops.schema.json`（ホップごとの宣言）、`questions.yaml`（問いの一覧。文言はスライドと一致。スライドに文言のない 4 問は `pending`）、`issuance_effects.yaml`・`issuance_effects.schema.json`（発行方式の選択ごとに台帳で必要になるもの）
- `examples/scenario-a/hops.yaml`：H1〜H3 のホップの宣言（#3）
- `tools/casestudy_check.py`・`tools/casestudy_pin.json`：ORG 行の名前と型、採否とケーススタディの判定の照合（`casestudy-mapping.md` の 8.。#3）
- `python tools/claim_lint render`（#19。`tools/claim_lint/render.py`・`RENDER.md`）：台帳から設計書の表（CI の結果・発行方式の選択と導かれる要件・トークン目録・問い × 仕組み・ホップ・矢印ごと・寿命の 4 層・判断の行・データ源・カタログへの回答の集計）と、ビューアー（#36）向けの JSON の束を生成する。設計書の `<!-- render:<節>:begin/end -->` の区間を `--write` で書き直し、`--check` で食い違いを検出する
- `examples/scenario-a/schemas/`：トークン種別（AT・IDT）ごとのペイロードの JSON Schema を、受け手向け（`additionalProperties: true`）と発行側の適合の検査用（`additionalProperties: false`）の 2 つずつ生成した（#19）。Keycloak で発行した見本の AT を発行側の Schema で CI で検証する
- `examples/scenario-a/design.md`（0.2.1）：縮小 Lite の〔生成〕の節を生成の区間に置き換えた（#19）。`claims.yaml`・`token_types.yaml` の 3 か所で、値の中の「 #」から後ろが YAML のコメントとして落ちていたのを、引用符で囲んで直した
- 同じ落ち方の残り 2 か所（`catalog/issue_events.yaml` の I24 の Auth0 の `hook_note`、`tools/claim_lint/path_limits.yaml` の Node.js の `note`）を直し、`templates/`・`tools/` の YAML で、引用符のない値が「 #」に続く語で切れていないかを確かめるテスト（`tools/tests/test_yaml_comment_truncation.py`）を足した（PR #39 の独立点検）
- `registry/claims.schema.json` の `volatility`：0 以上の整数か `never`。`0` は「変わったら即時に反映が要る」、`never` は「トークンの寿命の間に値が変わらない」（それまでの description は 0 を「変わらない」としていたので、意味を分けた）。`examples/scenario-a/claims.yaml` の 0 の 15 行（iss・sub・aud・exp・iat・jti・auth_time・typ・azp・sid・scope・nonce・tenant_id・user_id・v）を `never` にした（#19、PR #39。L5 は #6 で合わせる）
- `.gitleaks.toml`：トレースの要件 ID（`p08-revocation-propagation.R6` など）を generic-api-key の誤検出から外した。secret-scan は HEAD から辿れる履歴だけを見る（`--log-opts="HEAD"`）

- 設計書テンプレートの MVP（#4）：`00_core.md`（設計書の本体。13 の節と付録、生成の区間）、`claim_request.md`（追加前の 25 問。Lite でも必須）、`GETTING_STARTED.md`（30 分の入門）、`glossary.md`（ガイドと同じ訳語。「Transaction Token（Txn-Token）」「誰の権限で」）、`profiles/`（P1_human_web・P4_ai_agent_delegation・P5_internal_propagation）、`modules/`（M_authz_pdp・M_token_validation・M_multitenancy・M_privacy_minimization・M_data_layer・M_sender_constraint・M_idp_keycloak）。各項目に固定の項目 ID（`template:<パス>#<アンカー>`）と根拠の行を付け、採否の理由の見本は載せていない。版は 0.3.0
- `README.md`：準備中の入口を、一式の入口に書き直した。Lite と Full の判定（5 問）、縮小 Lite の定義（関門 1 の 10.）、プロファイルとモジュールの組み合わせ方、記入の順序、記入の目安（欄の数）（#4）
- `tools/template_check.py`：テンプレートの項目 ID・根拠の形（スライドの実在、RFC の節、草案の版、筆者の提案の追跡 issue）・記入欄が空かを確かめる（#4。CI は `.github/workflows/trace.yml`）
- `python tools/claim_lint --profile lite`：R1 の必須の列を縮小 Lite に合わせた。載せて誰かが読む行は、生成する列（`issue_events`・`propagation_delay`・`status`・`issuers`）と単一値の `overflow_strategy` を求めない。既定どおりで誰も読まない行は、R8 と判断に要る列だけを求める（#4、`tools/claim_lint/RULES.md` の「R1 の必須の列」）
- `tools/count_lite_fields.py --current <記入例> --profile lite|full`：今の記入例の、手で書く欄の数（#4。README の「記入の目安」）
- 対応表（#22）：#4 の要件 122 件を実装済みにした（core 92・full 30。うち 11 件は #6・#18 の規則（L3・L5・L6・L9・L14・L18・L23・L43・R8）の行に印を足して実装済みにした）。`template:00_core#issuance-profile`・`template:modules/M_sender_constraint#…`（5 件）・`template:claim_request#form` を planned_items に足し、送信者制約・クライアントの種類・PAR に関係する要件（7 件）に結び直した。`template:claim_request`（アンカーなし）を指していた 5 件は、`#form`・`#gate` に付け替えた。台帳のスキーマと問いの一覧には、#4 の要件の `req:` の印だけを足した（列は変えていない）

- PR #43 の独立点検の反映（#4。記録：`research/reviews/templates-mvp-2026-11-23.md`）：事実の誤り・過大・不一致の 13 件を直した。`tools/new_design.py`（空の設計書。GETTING_STARTED は記入例を写させない）、`tools/template_sources.yaml`（RFC と追跡 issue の固定の一覧）と `template_check` の T3（RFC・issue・パスの実在、形の絞り込み）・T4（記入欄の全列）・T6（見出しのアンカー）、シナリオ A の追加前の 25 問 3 ファイル（`claim_request_user_id.md`・`claim_request_roles.md`・`claim_request_v.md`）、L72 を error に（Lite も同じ）、`count_lite_fields --current` の Lite で Full のみの列を数えない
- `examples/scenario-b/`：シナリオ B（社内業務システム）＋C（AI エージェントの委任）の Full の記入例（P1＋P4＋P5。#4）。台帳 46 行（廃止予定の行 `C-employee-id` を含む）、トークン目録 24 行、ホップ 15 行、カタログへの回答 62 件、共有クレームごとの追加前の 25 問 9 ファイル、設計書（Full）、送信者制約を none にした変種（`variants/sender-none.yaml`）と、その比較（設計書の 3.3）
- `tools/variant_compare.py`：記入例に差分だけの上書きを当て、台帳・目録・ホップ・カタログへの回答・lint の結果の違いを表にする（`--write`・`--check`。#4）
- `casestudy-deviations.yaml`：シナリオ B の前提（B＋C の組み合わせ）と、carry 21 件・not_in_example 30 件
- claim_lint の L1b：草案が定める名前のうち、`tools/claim_lint/draft_claims.yaml` に固定したもの（Txn-Token の草案 -11 の `req_wl`・`tctx`・`rctx`）だけを warn にした。架空の草案・草案に無い名前・認可に使う名前は error のまま（#4、PR #44 の点検 B06）
- claim_lint の L16：トークン交換のホップで、aud を行き先の 1 つの宛先に替えるもの（`aud_replacement: true`、上流の aud に交換を求めるサービス、`narrowing_exception.aud` の理由）は info。条件を欠けば error。寿命の例外は Txn-Token だけ。scope・authorization_details・独自クレームには例外を設けない。Txn-Token を渡すホップの scope も上流と比べる（PR #44 の再点検）（#4、PR #44 の点検 B05。`hops.schema.json` に `aud_replacement` を足し、`narrowing_exception` を文字列かオブジェクトにした。任意の列の追加なのでマイナー）
- `review/`（#5、レビュー教材の MVP。版は 0.4.0）：`perspectives.md`（観点書。スライド 148 の 6 段を骨格に 168 問（うち 7 問はシナリオ B の較正で、1 問は PR #45 の点検で追加）。追加前の 25 問・アンチパターンの専用の問い 17・各 Part のチェックリストを段の下に置き、各問いに見る欄・No のとき・対比表・lint・実行テスト・根拠を付けた。役割ごとの索引、スライドの行との対応、シナリオ A・B の指摘との較正の表）、`decision_tree.md`、`contrasts/`（`act` と Txn-Token とワークロード認証、ID トークンとアクセストークン、署名と照合、寿命の 4 つの層、JWS と JWE、scope と role と RAR、載せるか問い合わせるか、名前と識別子の 8 本）、`escalation.md`、`procedure.md`（1 名で行う場合、LLM の一次スクリーニング）、`rationale_rubric.md`、`report_template.md`、`escaped_defects.md`、`metrics.md`、`README.md`
- `examples/scenario-b/review-report.md`：観点書でシナリオ B（コミット `a6aad45`）を改めてレビューしたレポートと、PR #44 の指摘 B01〜B15 との較正（#5）
- `tools/review_check.py`：レビュー教材の問い ID・見る欄・根拠・リンクの解決と、`review:` の成果物を持つ要件の印を確かめる（#5。CI は `.github/workflows/trace.yml`）
- 対応表（#22）：#5 の要件 94 件を実装済みにした。台帳のスキーマ・問いの一覧・テンプレート・`RULES.md` の、その要件が指す箇所に `req:` の印だけを足した（中身は変えていない）。`review:contrasts/<名前>`（アンカーなし）を `#misuse` に付け替えた。`template:claim_request`（アンカーなし）を指していた #5 の 2 件を `#q03` に付け替えた。`CONTRIBUTING.md` に `evidence-types` のアンカーを足した
- `tools/template_sources.yaml`：RFC 7516（JWE）を足した（#5）
- `modules/M_token_validation.md` の `library-config`：検討の行「未検証の値を流すモード」を足した（#5、PR #45 の再点検。観点書の `q-no-unverified-passthrough-mode` が見る欄）。`review/rationale_rubric.md` は採点の決まりと RR7 を足したので 0.5.0

### 変更

- claim_lint の目的と仕組みの規則（#18）：L11〜L14（宣言の整合の検査）を足した。`examples/scenario-a/catalog_answers.yaml` に `questions`（問いが要るか）を、`claims.yaml` の C-iss・C-sub に saas-web の `enforced_at` を足した（`design.md` の 13.）
- claim_lint の意味の規則（#6）：L1a・L1b・L2〜L9・L15〜L18・L21〜L23・L25・L27・L31・L37・L43・L62〜L73 と `claim_lint diff`（L10）を足した。新しい規則は warn から入れ、シナリオ A で機会が 1 以上・誤検知 0 のものだけを error にした（`tools/claim_lint/RULES.md`）。R8 の info から、ID トークンと AT の両方の仕様が定める登録名を外した
- `registry/claims.schema.json`（#6）：`enforced_at` の要素に任意の `against`・`with` を足した（任意の列の追加なのでマイナー）
- `examples/scenario-a/`（#6）：意味の規則が求める宣言を足した。C-sid の `registered_ref`、`enforced_at` の `against`（15 件）と `with`（C-user-id・C-iss）、IDT の `max_clock_skew`、`catalog_answers.yaml` の `lite_criteria`。値の途中の「 #」で消えていた 3 か所を引用符で囲んだ（#39 と同じ直し。検査は #39 で足す）。判断（採否・値）は変えていない（`design.md` の 13.）
- `registry/claims.schema.json`・`token_types.schema.json`（#3、台帳 v1。0.1.0 → 0.2.0）。列の意味と根拠と縮小 Lite の扱いは `registry/README.md` の 3.
  - 台帳：`authoritative_writer` を段階ごとの配列にし、`configurable_by` を足した（**形の変更**）。`integrity_until` を場所・写した先・信頼境界の構造にした（**形の変更**）。`shape` に `space_delimited` を足した。足した列：`allowed_values`・`value_vocabulary`・`absent_semantics`・`flat_alias`・`paired_id`・`composite_format`・`value_normalization`・`prior_art_search`・SD-JWT VC の `path`・`mandatory`・`sd`・`display`・`rejection_kind`（却下の行で必須）・`alt`・`answers`・`does_not_answer`・`upstream_issuer`・`modifiers`・`provenance`・`verification_method`・`last_verified`・`source_max_length`・`consumer_access_path`・`consumers_migration`・`confidential_from`・`confidentiality_measure`・`data_category`・`identifier_properties`（`usage: identifier` で必須）・`recipients_external`・`cross_border`・`sunset_on`・`asvs_ids`・`spec_version`。最上位に `namespaces`・`data_category_vocabulary`（必須。fideslang の版を固定して参照）・`data_category_extensions`。採用・却下の理由の 2 つ以上と、配列の `max_items` をスキーマでも強制した。`refs` に ASVS を書くとスキーマの誤り。すべての配列に `maxItems`
  - トークン目録：`kind` を `catalog/token_kinds.yaml` の 17 種類にした。`revocation` を手段と遅れの配列に、`key_rotation` を構造にした（**形の変更**）。足した列：`assumption`・`revisit_trigger`・`refs`・`subject_type`・`key_source`・`idle_timeout`・`lifetime_set_by`・`lifetime_exception`・`rt_rotation`・`sender_constraint`・`jti_policy`・`introspection_cache_ttl`・`long_running`・`max_delegation_depth`・`tenant_binding`・`unknown_kid`・`jwks_cache_ttl`・`signing_key_scope`・`visible_to`・`jwe`・`log_policy`・`asvs_ids`。AT は URL で運べない（スキーマ）。`issuance_profile` に `tls_termination`・`forwarded_cert_header` を足し、`request_protection`・`conformance_profile` を必須にした
  - claim_lint：R1 の必須に `data_category`・`confidential_from`（台帳）と `visible_to`・`jwe`（目録）を足した。規則 REF（ファイルの間の参照）を足した。`hops.yaml` をスキーマで検証する
  - 列の形の変更と必須化は semver ではメジャーに当たるが、未リリースのため 0.y のマイナーとして 0.2.0 にした
- `examples/scenario-a/`（#3）：台帳 v1 に移し替えた。`claims.yaml` に上の列を足した（`name`・`email`・`email_verified` は `confidential_from: [browser]` で「載せない」）。`token_types.yaml` に、カタログの残りの 9 種類の却下の行と、`visible_to`・`jwe`・鍵の取り直しの規則などを足した（18 行）。claim_lint の結果は v0 と同じ（error 0・warn 2・info 7）。`tools/count_lite_fields.py` は、関門 1 の記録を再現できるよう v0 の列と v0 の 9 行だけを数える
- `casestudy-deviations.yaml`：照合を `tools/casestudy_check.py` で行うようにした。PR #37 の独立点検を受けて、`kind: not_in_example`（ケーススタディが載せるとしたが記入例が参照しない行、20 件）と、carry の CLM-0404 を足した
- PR #37 の独立点検を受けた修正（#3）：文字列の列は空白だけを拒む（スキーマの `\S`、R1 も空白を空とみなす）。`refs` の ASVS の検査を広げた（OWASP-ASVS・V8.3.2・v5.0.0-8.3.2・正式名・ASVS の URL）。`shape: space_delimited` にも `max_items` を必須にし、記入例の `C-scope` を `space_delimited` にした。`display.dir` に `auto` を足した（SD-JWT VC -27 §5.5・§5.6.2）。`confidential_from: []` の行には `confidentiality_measure` を書けない。名前空間が object なら `namespace_version` を必須。認可コードと JARM の応答のほかは URL で運べない。RT とセッションの採用の行は R1 で `idle_timeout` が必須。REF はホップの `upstream` の循環を拒む。`catalog_refs_reason` を足した。Txn-Token の寿命の根拠を §13.6 から §6 に直し、mTLS の証明書を渡すヘッダーの規則を筆者の提案にした（RFC 8705 §6.5 は範囲外としている）
- `catalog/`（#17、PR #33 の独立点検）：種の一覧 `keycloak-grant-types` を足した。Keycloak 26.8.2 の `OAuth2GrantType` の実装 10 個で、`PermissionGrantType`（UMA）は対象外にした。あわせて、カタログに無かった OID4VCI の Pre-Authorized Code の発行を I34 として足した（Keycloak の機能 `oid4vc-vci` は Preview で既定は無効。`hook_invoked` は unknown、V37）。I34 の `guide` は、新しい値 `out-of-scope`（「ガイドの範囲外」。VC の発行はガイドの対象の外。前提と崩れる条件つき）にした。スライドは関門の後まで凍結のため足さず、「ガイドの空白」は 0 件のまま。`catalog_check` はこの値を受け付け、`sources.md` の冒頭で別に数える。種は 355 項目、対象外は 138 件になった。Keycloak の I03・I04・I05・I07 の `idp.keycloak` には `lite_inherit: true` を付けた（Lite の引き継ぎの印。#4 の改訂）。`sources.md` では、Keycloak を「あり（grant の一覧）」に、Entra・Okta を「文書で未確認」に書き分けた
- `registry/token_types.schema.json`：その場で宣言する上限（`size.path` のオブジェクト）に、任意の `verified_on`・`review_by` を足した（#17 の R10。任意の列の追加なのでマイナー）
- `examples/scenario-a/catalog_answers.yaml`：I34 に対象外で答えた。停止の RT の根拠を「拒否による実質の失効」と書き直した。R9 の探した範囲から Full だけの節（シーケンス図）を外し、Keycloak の grant の一覧を足した（PR #33 の独立点検）
- `catalog/issue_events.yaml`・`use_events.yaml`（#2）：v0 の I01〜I09・U01〜U10 の ID はそのまま。IdP ごとの列（`hook_invoked`・`hook_note`・`source_refs`・`evidence`）を `idp.keycloak`・`idp.auth0` の下に移し、`occurs`・`hook_name`・`stop_setting`・`lifetime_note` を足した。行の `idp`（文字列）を外し、`issuer`（利用イベントは `actor`）・`claims_produced`（利用イベントは `claims_read`）・`seeds`・`guide` を足した。`tokens_issued` を `token_kinds.yaml` の id とセッションの層（`session_idp`・`session_rp`）で書き、`lifetime_impact` を `issued`・`recomputed`・`revoked`・`note` の形にした。v0 の `unknown` の `hook_invoked` は、公式文書で確かめて I05・I06・I07・I08 を `yes` にした。列の削除・改名なので semver ではメジャーに当たるが、未リリースのため版は 0.1.0 のまま
- `examples/scenario-a/catalog_answers.yaml`：足したイベント 42 件に回答した（#2）。`tools/count_lite_fields.py` は、関門 1 の記録を再現できるよう v0 の 19 件だけを数える
- #16 の YAML（`catalog/`・`examples/scenario-a/`・`casestudy-deviations.yaml`）の `template_version` を、上の規約に合わせて 1 行目のコメントにした。`registry/*.schema.json` からキー `template_version` を外した（#16、関門 1 の PR）。スキーマは `additionalProperties: false` なので、キーを持つ既存のファイルは検証で落ちる。semver では列の削除はメジャーに当たるが、未リリースのため版は 0.1.0 のままにした
- `examples/scenario-a/`：関門 1（判定は「絞る」）の Lite の縮小案での扱いを印で付けた（中身は消していない）。追加前の 25 問の記入例 `claim_request_tenant_id.md` を足した（#16）
- `trace/`：tier を確定した（`tier_confirmed`）。core に上げた要件 32 件。チェックリスト・アンチパターン・レビューの観点・追加前の問いのスライドに `review_required` を付けた（#16）
- `CONTRIBUTING.md`：YAML の `template_version` を 1 行目のキーから 1 行目のコメント（`# template_version: 0.1.0`）に改め、yaml-language-server の modeline の置き場所（最初のキーより前の先頭のコメント）を決めた。既存の `templates/trace/*.yaml` はもとからこの形（`research/claims-as-code/report.md` の点検の指摘）
- `catalog/`：「ガイドの空白」の 14 行（I04・I07・I09・I10・I11・I24・I25・I26・I28・I31・U07・U09・U18・U28）とトークンの種類 3 件（`logout_token`・`client_assertion`・`jar_request_object`）を、#10 で足したスライドの ID で `covered` にした。一部だけ扱う 9 行のうち 8 行と `dpop_proof` も `covered` にし、I20 は `partial` のまま、扱わない点の前提と崩れる条件を note に書いた（#10）
- `trace/`：#10 で足したスライド 7 枚を分類し（7 枚とも `design-decision`）、要件 31 件を足した。うち 6 件を core にし、`tier_changes` に記録した。スライド番号のずれで変わった 137 枚のハッシュを更新した（#10）
- 独立点検（PR #23 のコメント）の 24 件を反映：根拠に `research` を追加、完了の定義に抜き取りの点検と根拠の ID の実在の確認を追加、正とする側の向きを 1 つに、`template_version` と意図的に誤りを含む教材の表示の書き方を JSON などにも拡張、後続の issue に渡す項目の一覧を追加
