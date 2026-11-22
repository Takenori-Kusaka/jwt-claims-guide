# 変更の記録

`templates/` の変更を記録します。版は semver で、タグは `templates-vX.Y.Z` です。版の上げ方は [CONTRIBUTING.md](CONTRIBUTING.md) の「版の管理」にあります。

## 未リリース（Unreleased）

### 追加

- `CONTRIBUTING.md`：根拠の種類と書式、完了の定義、点検者の取り決め、公開物の取り扱い、題材（#13）
- `casestudy-mapping.md`：ケーススタディ（コミット `080b8da`）との対応表と、正とする側の決定（#13）
- `README.md`：準備中の入口
- `LICENSE`：CC0 1.0 Universal

### 変更

- `CONTRIBUTING.md`：YAML の `template_version` を 1 行目のキーから 1 行目のコメント（`# template_version: 0.1.0`）に改め、yaml-language-server の modeline の置き場所（最初のキーより前の先頭のコメント）を決めた。既存の `templates/trace/*.yaml` はもとからこの形（`research/claims-as-code/report.md` の点検の指摘）
- 独立点検（PR #23 のコメント）の 24 件を反映：根拠に `research` を追加、完了の定義に抜き取りの点検と根拠の ID の実在の確認を追加、正とする側の向きを 1 つに、`template_version` と意図的に誤りを含む教材の表示の書き方を JSON などにも拡張、後続の issue に渡す項目の一覧を追加
