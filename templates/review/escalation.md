<!-- template_version: 0.4.0 -->
# 専門家に回す基準

設計書の次の欄に当てはまる行があれば、レビュアーは自分で可否を決めず、ID の分野の専門家（組織の認証基盤の担当、または外部の専門家）に回します。回した項目は、レビューレポートの「専門家に回した項目」に、基準の ID・行・回した先・期限を書きます（[report_template.md](report_template.md)）。

- 基準は「設計書のどの欄を見れば当てはまるか分かるか」で書きました。経験の浅いレビュアーが、内容の正しさを判断せずに回せるようにするためです
- 回すことは却下ではありません。専門家の結論が出るまで、その行は「保留」にします
- 基準の選び方は筆者の提案です（追跡 #5）。#5 の本文に挙げた 4 つの例（草案の仕様に依存する行・独自の暗号・委任の深さが 2 以上・テナントをまたぐ交換）に、シナリオ A・B のレビューで判断が分かれた点から 5 つを足しました
- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施

| ID | 当てはまる条件（見る欄） | 回す理由 |
| --- | --- | --- |
| `draft-spec` | 台帳・目録の `refs` が草案（`draft-…-NN`）・製品の preview を指す行、草案が定めるクレーム（`txn`・`tctx`・`req_wl` など）・草案のトークン（Txn-Token・ID-JAG・状態リスト）を採用した行 | 版で中身が変わる。見直しの条件と、確定版での差の評価が要る |
| `custom-crypto` | 独自の署名・暗号化の方式、鍵の導出、トークンの独自の形式、`alg_allowlist` に組織の独自の値がある | 暗号の正しさは、レビューの問いでは判定できない |
| `delegation-depth` | `max_delegation_depth` が 2 以上、または `act` が入れ子になる経路がある | 深さの上限と一括失効は標準になく、組織の規則の妥当性を判断する |
| `cross-tenant-exchange` | テナントをまたぐ交換・運用者のテナント横断の操作・テナントをまたぐ利用者のリンク | 別テナントのデータに届く誤りは Blocker になりやすい |
| `baseline-unmet` | 3.2 の共通の基準（`template:00_core#baseline`）に「満たさない」がある | 外す理由の妥当性を、組織の基準の持ち主が判断する |
| `jwe-key-management` | JWE を採用した種別（`jwe` がある） | 受け手ごとの鍵の配布・ローテーション・失効の設計 |
| `unverified-idp-behavior` | 12.（`template:00_core#uncertain`）に、IdP の挙動（リフレッシュでの再評価・RT の再利用の検知・交換で出た `act`）を確かめていないと書いた行で、その挙動に Major 以上の判断が依存する | 実測か公式の文書で確かめる手順が要る |
| `regulated-data` | `pii_category` が要配慮個人情報、または規制（金融・医療・FAPI）の対象のトークン | 法令と業界の要求の当てはめ |
| `new-token-type` | 目録に、カタログの 17 種類（`templates/catalog/token_kinds.yaml`）に無い種類のトークンがある | 検証の規則・寿命の前例がない |

<a id="draft-spec"></a>

## draft-spec：草案の仕様に依存する行

- 見る欄：`registry:claims#refs`、`registry:claims#spec_version`、`registry:claims#revisit_trigger`
- 回す前に確かめること：行に版（`spec_version`）と見直しの条件（`revisit_trigger`）があるか（無ければ、まず書き手に戻す。`lint:L14`）。白書や草案を「必須」と書いていないか
- 回す先：組織の認証基盤の担当。結論は台帳の `revisit_trigger` に書く

根拠：slide:p03-keycloak-aud-lightweight、slide:p10-guidance-standards、templates/CONTRIBUTING.md の 1.
<!-- req:p03-keycloak-aud-lightweight.R6 req:p10-guidance-standards.R1 -->

<a id="custom-crypto"></a>

## custom-crypto：独自の暗号

- 見る欄：`registry:token_types#alg_allowlist`、`registry:token_types#jwe`、`registry:token_types#signing`
- 回す前に確かめること：標準のアルゴリズム（RFC 8725 §3.2）と標準の形式（JWS・JWE）で代えられないか
- 回す先：組織の暗号の担当か外部の専門家

根拠：RFC 8725 §3.2、slide:p01-jwt-structure

<a id="delegation-depth"></a>

## delegation-depth：委任の深さが 2 以上

- 見る欄：`registry:token_types#max_delegation_depth`、`template:profiles/P4_ai_agent_delegation#delegation-depth`、`template:profiles/P4_ai_agent_delegation#chain-revocation`
- 回す前に確かめること：深さの上限と、根元の承認からの一括失効の手段が書いてあるか（`q-delegation-depth-and-revocation`）。認可に使うのが最も外側の `act` だけか
- 回す先：組織の認証基盤の担当

根拠：slide:p10-delegation-chain-depth、RFC 8693 §4.1
<!-- req:p10-delegation-chain-depth.R6 -->

<a id="cross-tenant-exchange"></a>

## cross-tenant-exchange：テナントをまたぐ交換

- 見る欄：`template:00_core#system-privileges`、`template:modules/M_multitenancy#operator-access`、`template:modules/M_multitenancy#cross-tenant`
- 回す前に確かめること：運用者は委任のトークン（`sub`＝顧客、`act`＝運用者）で操作し、承認と期限を確かめ、顧客と運用者の両方を記録するか
- 回す先：テナントの分離の責任者

根拠：slide:p05-cross-tenant、slide:p06-flow-multitenant-saas
<!-- req:p05-cross-tenant.R3 req:p06-flow-multitenant-saas.R5 -->

<a id="baseline-unmet"></a>

## baseline-unmet：共通の基準を満たさない

- 見る欄：`template:00_core#baseline`、`template:00_core#deviations`
- 回す前に確かめること：外す理由と、回した先（追跡 issue）が設計書に書いてあるか
- 回す先：組織の共通の基準の持ち主

根拠：slide:p12-priorities-deferrals

<a id="jwe-key-management"></a>

## jwe-key-management：JWE の鍵の管理

- 見る欄：`registry:token_types#jwe`、`registry:token_types#key_rotation`
- 回す前に確かめること：まず載せない・派生値にする案を比べたか（`review:contrasts/jws-vs-jwe#misuse`）
- 回す先：組織の鍵の管理の担当

根拠：slide:p09-jwe-sd-jwt、RFC 7516 §1

<a id="unverified-idp-behavior"></a>

## unverified-idp-behavior：確かめていない IdP の挙動に依存する

- 見る欄：`template:00_core#uncertain`、`template:00_core#lifecycle`
- 回す前に確かめること：確かめ方の案（実測・公式の文書）が書いてあるか
- 回す先：IdP の運用の担当

根拠：slide:p03-recent-changes、slide:p08-refresh-reevaluation

<a id="regulated-data"></a>

## regulated-data：規制の対象のデータ

- 見る欄：`registry:claims#pii_category`、`registry:token_types#issuance_profile`
- 回す前に確かめること：`pii_category` と `log_policy` が書いてあるか
- 回す先：個人情報の保護の担当・法務

根拠：slide:p09-do-not-carry、template:modules/M_privacy_minimization#appi-table

<a id="new-token-type"></a>

## new-token-type：カタログに無い種類のトークン

- 見る欄：`template:00_core#token-inventory`
- 回す前に確かめること：カタログの 17 種類のどれかで代えられないか
- 回す先：組織の認証基盤の担当。結論はカタログに戻す（[procedure.md](procedure.md) の 6.）

根拠：templates/catalog/token_kinds.yaml、slide:p01-client-made-jwts
