<!-- template_version: 0.1.0 -->
# JWT クレームの設計書テンプレート一式（準備中）

**準備中です。まだ使える版はありません。** 最初の公開版は `templates-v1.0.0` のタグで出します。

## ここに入るもの

全体の計画は #11 にあります（https://github.com/Takenori-Kusaka/jwt-claims-guide/issues/11）。

- 設計書のテンプレート（Lite と Full）と記入例（#4）
- クレームの台帳のスキーマと問いの一覧（#3）
- 発行・利用イベントのカタログ（#2）
- レビュー観点書、判断の木、対比表、レビューレポートの様式（#5）
- ガイドのスライドとの対応表（#22）

いま入っているのは、共通の規約（[CONTRIBUTING.md](CONTRIBUTING.md)）と、ケーススタディとの対応表（[casestudy-mapping.md](casestudy-mapping.md)）と、#16（縦の一本）で作った仮の版です。仮の版は列や形が変わります。

- 発行・利用イベントのカタログ（[catalog/](catalog/)。Keycloak 26.8 と Auth0。#2）と、台帳のスキーマ v0（[registry/](registry/)）
  - カタログの出どころと、種になる一覧との差集合（[catalog/sources.md](catalog/sources.md)）。検査は `python tools/catalog_check.py`
- シナリオ A（Keycloak）の記入例（[examples/scenario-a/](examples/scenario-a/)）。推奨ではなく、ケーススタディの前提での一例
- 検査：`python tools/claim_lint templates/examples/scenario-a`（規則は [tools/claim_lint/RULES.md](../tools/claim_lint/RULES.md)）

## ライセンス

`templates/` のファイルは [CC0 1.0](LICENSE) です。表示の義務なしに、社内の設計書へそのままコピーできます。ガイド本体は CC BY 4.0、コードは MIT です（[LICENSE-CONTENT.md](../LICENSE-CONTENT.md)）。

## 作成方法

本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。

## 点検状況

> 人による点検は未実施。作成とは別の LLM のセッションで点検した。作成者の 1 日以上空けた見直しは未実施（記録：`research/reviews/templates-conventions-2026-11-22.md`）。

点検の手順と表示の決まりは [CONTRIBUTING.md](CONTRIBUTING.md) の「3. 点検者についての取り決め」にあります。人による点検は、協力者が見つかったときに #20 で行います。

## 規約

根拠の書き方、完了の定義、版の管理、公開の決まり、題材は [CONTRIBUTING.md](CONTRIBUTING.md) にあります。変更の記録は [CHANGELOG.md](CHANGELOG.md) です。
