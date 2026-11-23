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

### 変更

- claim_lint の意味の規則（#6）：L1a・L1b・L2〜L9・L15〜L18・L21〜L23・L25・L27・L31・L37・L43・L62〜L73 と `claim_lint diff`（L10）を足した。新しい規則は warn から入れ、シナリオ A で機会が 1 以上・誤検知 0 のものだけを error にした（`tools/claim_lint/RULES.md`）。R8 の info から、ID トークンと AT の両方の仕様が定める登録名を外した
- `registry/claims.schema.json`（#6）：`enforced_at` の要素に任意の `against`・`with` を足した（任意の列の追加なのでマイナー）
- `examples/scenario-a/`（#6）：意味の規則が求める宣言を足した。C-sid の `registered_ref`、`enforced_at` の `against`（14 件）と `with`（C-user-id）、IDT の `max_clock_skew`、`catalog_answers.yaml` の `lite_criteria`。値の途中の「 #」で消えていた 3 か所を引用符で囲んだ（#39 と同じ直し。検査は #39 で足す）。判断（採否・値）は変えていない（`design.md` の 13.）
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
