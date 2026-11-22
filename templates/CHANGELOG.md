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

### 変更

- `catalog/`（#17、PR #33 の独立点検）：種の一覧 `keycloak-grant-types` を足した。Keycloak 26.8.2 の `OAuth2GrantType` の実装 10 個で、`PermissionGrantType`（UMA）は対象外にした。あわせて、カタログに無かった OID4VCI の Pre-Authorized Code の発行を I34 として足した（Keycloak の機能 `oid4vc-vci` は Preview で既定は無効。`hook_invoked` は unknown、V37）。種は 355 項目、対象外は 138 件になった。Keycloak の I03・I04・I05・I07 の `idp.keycloak` には `lite_inherit: true` を付けた（Lite の引き継ぎの印。#4 の改訂）。`sources.md` では、Keycloak を「あり（grant の一覧）」に、Entra・Okta を「文書で未確認」に書き分けた
- `registry/token_types.schema.json`：その場で宣言する上限（`size.path` のオブジェクト）に、任意の `verified_on`・`review_by` を足した（#17 の R10。任意の列の追加なのでマイナー）
- `examples/scenario-a/catalog_answers.yaml`：I34 に対象外で答えた。停止の RT の根拠を「拒否による実質の失効」と書き直した。R9 の探した範囲から Full だけの節（シーケンス図）を外し、Keycloak の grant の一覧を足した（PR #33 の独立点検）
- `catalog/issue_events.yaml`・`use_events.yaml`（#2）：v0 の I01〜I09・U01〜U10 の ID はそのまま。IdP ごとの列（`hook_invoked`・`hook_note`・`source_refs`・`evidence`）を `idp.keycloak`・`idp.auth0` の下に移し、`occurs`・`hook_name`・`stop_setting`・`lifetime_note` を足した。行の `idp`（文字列）を外し、`issuer`（利用イベントは `actor`）・`claims_produced`（利用イベントは `claims_read`）・`seeds`・`guide` を足した。`tokens_issued` を `token_kinds.yaml` の id とセッションの層（`session_idp`・`session_rp`）で書き、`lifetime_impact` を `issued`・`recomputed`・`revoked`・`note` の形にした。v0 の `unknown` の `hook_invoked` は、公式文書で確かめて I05・I06・I07・I08 を `yes` にした。列の削除・改名なので semver ではメジャーに当たるが、未リリースのため版は 0.1.0 のまま
- `examples/scenario-a/catalog_answers.yaml`：足したイベント 42 件に回答した（#2）。`tools/count_lite_fields.py` は、関門 1 の記録を再現できるよう v0 の 19 件だけを数える
- #16 の YAML（`catalog/`・`examples/scenario-a/`・`casestudy-deviations.yaml`）の `template_version` を、上の規約に合わせて 1 行目のコメントにした。`registry/*.schema.json` からキー `template_version` を外した（#16、関門 1 の PR）。スキーマは `additionalProperties: false` なので、キーを持つ既存のファイルは検証で落ちる。semver では列の削除はメジャーに当たるが、未リリースのため版は 0.1.0 のままにした
- `examples/scenario-a/`：関門 1（判定は「絞る」）の Lite の縮小案での扱いを印で付けた（中身は消していない）。追加前の 25 問の記入例 `claim_request_tenant_id.md` を足した（#16）
- `trace/`：tier を確定した（`tier_confirmed`）。core に上げた要件 32 件。チェックリスト・アンチパターン・レビューの観点・追加前の問いのスライドに `review_required` を付けた（#16）
- `CONTRIBUTING.md`：YAML の `template_version` を 1 行目のキーから 1 行目のコメント（`# template_version: 0.1.0`）に改め、yaml-language-server の modeline の置き場所（最初のキーより前の先頭のコメント）を決めた。既存の `templates/trace/*.yaml` はもとからこの形（`research/claims-as-code/report.md` の点検の指摘）
- 独立点検（PR #23 のコメント）の 24 件を反映：根拠に `research` を追加、完了の定義に抜き取りの点検と根拠の ID の実在の確認を追加、正とする側の向きを 1 つに、`template_version` と意図的に誤りを含む教材の表示の書き方を JSON などにも拡張、後続の issue に渡す項目の一覧を追加
