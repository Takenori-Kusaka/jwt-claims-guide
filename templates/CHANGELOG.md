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

### 変更

- #16 の YAML（`catalog/`・`examples/scenario-a/`・`casestudy-deviations.yaml`）の `template_version` を、上の規約に合わせて 1 行目のコメントにした。`registry/*.schema.json` からキー `template_version` を外した（#16、関門 1 の PR）。スキーマは `additionalProperties: false` なので、キーを持つ既存のファイルは検証で落ちる。semver では列の削除はメジャーに当たるが、未リリースのため版は 0.1.0 のままにした
- `examples/scenario-a/`：関門 1（判定は「絞る」）の Lite の縮小案での扱いを印で付けた（中身は消していない）。追加前の 25 問の記入例 `claim_request_tenant_id.md` を足した（#16）
- `trace/`：tier を確定した（`tier_confirmed`）。core に上げた要件 32 件。チェックリスト・アンチパターン・レビューの観点・追加前の問いのスライドに `review_required` を付けた（#16）
- `CONTRIBUTING.md`：YAML の `template_version` を 1 行目のキーから 1 行目のコメント（`# template_version: 0.1.0`）に改め、yaml-language-server の modeline の置き場所（最初のキーより前の先頭のコメント）を決めた。既存の `templates/trace/*.yaml` はもとからこの形（`research/claims-as-code/report.md` の点検の指摘）
- 独立点検（PR #23 のコメント）の 24 件を反映：根拠に `research` を追加、完了の定義に抜き取りの点検と根拠の ID の実在の確認を追加、正とする側の向きを 1 つに、`template_version` と意図的に誤りを含む教材の表示の書き方を JSON などにも拡張、後続の issue に渡す項目の一覧を追加
