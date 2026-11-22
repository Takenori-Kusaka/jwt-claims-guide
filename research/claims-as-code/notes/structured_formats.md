# クレーム定義の機械可読フォーマット（「クレーム版 OpenAPI」）の先行事例

調査日: 2026-11-22。比較の基準は本リポジトリの `claims.yaml` の列。列は name, namespace, type, shape, meaning/not-meaning, writer/issuer, data source, lifetime/volatility, carried_in, consumers, size, pii_category, confidential_from, decision+rationale, evidence。
凡例: 「確認済」は本調査で一次資料を取得して確かめた事項。「未取得」は既知の仕様だが本調査では取得していない事項で、Gaps に回した。

## Q1. クレジットクレームのメタデータ標準（SD-JWT VC Type Metadata / OpenID4VCI / W3C VC JSON Schema / mdoc / EUDI ARF）は、クレーム単位のメタデータをどこまで定義しているか

### Takeaway
クレーム単位のメタデータを JSON で正式に定義した仕様として最も近いのは、SD-JWT VC Type Metadata と OpenID4VCI の claims description の二つである。ただし対象は path、mandatory、sd（選択的開示）、display（表示ラベル）に限られる。意味、発行者側のデータソース、寿命、サイズ、PII 分類、消費者、設計判断の根拠は、どちらも扱わない。

### Cited Findings
- SD-JWT VC の最新版は draft-ietf-oauth-sd-jwt-vc-27（2026-11-16）。WG 状態は「Submitted to IESG for Publication」、IESG 状態は「IESG Evaluation::AD Followup」で、目標は Proposed Standard、失効は 2027-05-20 — [IETF Datatracker](https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/)
- Type Metadata のトップレベルは `vct`（REQUIRED）、`name`、`description`、`extends`、`display`、`claims`、`extends#integrity` の 7 つ。仕様は「Consumers MUST ignore properties that are not understood」と定めるため、独自プロパティを足しても互換性は壊れない — [同上 §5.2](https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/)
- Claim metadata（§5.6）のフィールド:
  - `path`（REQUIRED。文字列・null・非負整数の配列）
  - `display`（`locale`, `label`, `description`, `dir`）
  - `mandatory`（boolean、既定 false）
  - `sd`（`always` / `allowed` / `never`、既定 `allowed`。曖昧さを避けるため `always` か `never` の使用を推奨）
  - `svg_id`

  — [同上](https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/)
- 改訂履歴では JSON Schema を -04 で「Include schema Type Metadata」として追加し、-12 で「Remove JSON schema from Type Metadata」として削除した。つまり現行の Type Metadata は型や形状（type/shape）を持たない — [同上 changelog](https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/)
- 改訂履歴に見える検証ルール:
  - -12: `extends` で型を継承するときの sd/mandatory の規則を導入
  - -17: 不正な claim metadata の拒否を要求。選択的開示クレームが提示されていないことを mandatory 違反とみなしてはならない
  - -21: 処理失敗ルールの範囲を claims 配列と path/mandatory/sd に限定

  これらは機械検査できる整合性ルールの先例になる — [同上](https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/)
- 完全性: `vct#integrity`、`extends#integrity`、`uri#integrity` を W3C SRI 形式で付ける — [同上 §6](https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/)
- OpenID4VCI 1.0 は Final（2025-09-16 公開）。Issuer metadata の `claims` は claims description object の配列で、Appendix B.2 によるフィールドは次の 3 つ — [OpenID4VCI 1.0](https://openid.net/specs/openid-4-verifiable-credential-issuance-1_0.html)
  - `path`（REQUIRED、claims path pointer）
  - `mandatory`（既定 false。true なら Issuer は常にそのクレームを含める）
  - `display`（`name`, `locale`）
- OpenID4VCI の形式別必須パラメータ: `dc+sd-jwt` は `vct`、`mso_mdoc` は `doctype`、`jwt_vc_json` は `credential_definition.type`、`ldp_vc` は `@context` と `type`。仕様は「Authorization Server MUST be able to determine from the Issuer metadata what claims are disclosed」と定めるため、メタデータが開示クレームの正本になる — [同上 Appendix A/B](https://openid.net/specs/openid-4-verifiable-credential-issuance-1_0.html)
- EUDI ARF の namespace と rulebook:
  - namespace は「属性の識別子・構文・意味」をエコシステム全体で一意に定める単位 — [ARF Annex 1（v3.0.0）](https://eudi.dev/3.0.0/annexes/annex-1/annex-1-definitions/)（取り込んだ版は 1.3.0 の URL を引いていたが、いまは 404。定義の文は現行の v3.0.0 でも同じ）
  - PID の attestation type と namespace は `eu.europa.ec.eudi.pid.1`。国別属性は domestic namespace に置く（独の例は `eu.europa.ec.eudi.pid.de.1`） — [ARF PID Rulebook 1.4.0](https://eu-digital-identity-wallet.github.io/eudi-doc-architecture-and-reference-framework/1.4.0/annexes/annex-3/annex-3.01-pid-rulebook)、German PID rulebook（OpenCoDE の個別ページの URL は 404。2026-11-22 のリンクの点検。設計文書の入口は [eIDAS 2.0 Architekturkonzept](https://bmi.usercontent.opencode.de/eudi-wallet/eidas-2.0-architekturkonzept/)）
- Rulebook は人が読む文書（Markdown/PDF）で、属性定義と形式別エンコーディングの章を分ける。APTITUDE のテンプレートは ISO 18013-5、SD-JWT VC、W3C VCDM 2.0 のエンコーディングを別章に置く。同じ属性でも形式によって名前が異なり、生年月日は mdoc で `birth_date`、SD-JWT VC で `birthdate` — APTITUDE attestation rulebook template（`aptitude-consortium.github.io` の URL は 404。2026-11-22 のリンクの点検。代わりの URL は見つけていない）, [ETSI TS 119 472-2](https://etsi.org/deliver/etsi_ts/119400_119499/11947202/01.02.01_60/ts_11947202v010201p.pdf)
- mDL は ISO 18013-5 だけで実装し、SD-JWT VC にしてはならない — [ARF mDL Rulebook](https://eu-digital-identity-wallet.github.io/eudi-doc-architecture-and-reference-framework/latest/annexes/annex-3/annex-3.02-mDL-rulebook)

### Inferences
- `claims.yaml` の列との対応:
  - `name`/`namespace` は `path` と `vct`（または mdoc namespace）に当たる
  - `carried_in` は OpenID4VCI の credential configuration（形式ごと）に当たる
  - 「必須か」は `mandatory`、選択的開示方針は `sd` に当たる
  - type/shape、意味/非意味、データソース、寿命、サイズ、PII、confidential_from、decision/evidence には対応する標準フィールドがない
- Type Metadata は未知プロパティの無視を MUST としている。そのため `claims.yaml` の 1 エントリを Type Metadata の claim object の上位集合として設計し、`path`、`mandatory`、`sd`、`display` を同じ名前と意味で持つと、将来 VC 化するときにそのまま射影できる。
- JSON Schema が -12 で外された経緯から、形状の検証は Type Metadata と分けて別の JSON Schema で持つのが IETF での整理だと読める。claims.yaml の type/shape も JSON Schema（2020-12）として書き出せる形にしておくと整合する。
- ARF の「namespace = 識別子・構文・意味」は、claims.yaml の namespace 列と meaning 列の組み合わせに概念上近い。ただし機械可読のスキーマとしては公開されておらず、文書ベースである。

### Gaps
- W3C「Verifiable Credentials JSON Schema」仕様の現在の成熟度：取り込みの際（2026-11-22）に確認先のページを取得し、W3C Candidate Recommendation Draft（2025-02-04）であることを確かめた。Recommendation ではない — https://www.w3.org/TR/vc-json-schema/
- ISO 18013-5 と 23220 の namespace/data element 定義は有償規格のため本文を確認していない。
- ARF の rulebook に機械可読版（JSON/YAML）や CI 検査があるかは確認できなかった。見つかったのは文書形式だけ。

## Q2. クレームについて機械可読な OAuth/OIDC メタデータ（Discovery claims_supported、OpenID Federation、RFC 9068、IANA JWT Claims registry、RFC 9728）

### Takeaway
OAuth/OIDC 系のメタデータがクレームについて表せるのは、名前の列挙（`claims_supported`）とレジストリ登録（名前・説明・変更管理者・参照）までである。型、必須性、寿命、消費者は表せない。その中で、IANA レジストリが XML と CSV で取得できる点は、linter での衝突検査に直接使える。

### Cited Findings
- IANA「JSON Web Token Claims」レジストリの列は Claim Name、Claim Description、Change Controller、Reference の 4 つで、約 160 件が登録されている（最終更新 2026-10-28）。形式は XML（`/assignments/jwt/jwt.xml`）、TXT、HTML があり、claims 表だけの CSV（`/assignments/jwt/claims.csv`）も取得できる — [IANA JWT registry](https://www.iana.org/assignments/jwt/jwt.xhtml)
- OpenID Federation 1.0 は Final:
  - パブリックレビュー 2025-12-04〜2026-02-02、投票 2026-02-03〜02-17 — [OIDF](https://openid.net/public-review-period-for-proposed-openid-federation-1-final-specification/)
  - 投票数 105（定足数 24.7%）、2026 年 2 月に公開 — [OIDF 承認告知](https://openid.net/openid-federation-1-0-final-specification-approved/), [self-issued.info](https://self-issued.info/?p=2813)（非公式）
  - 1.1 は protocol 非依存部と依存部に分割され、1.0 と相互に使えるとされる — [self-issued.info](https://self-issued.info/?m=202602)（非公式）

### Inferences
- linter に「IANA 登録済みのクレーム名を独自の意味で再定義していないか」「private claim が登録名と衝突しないか」という検査を入れるなら、`claims.csv` を CI で取り込むのが最も確実な方法である。
- Discovery、RFC 9068、RFC 9728 はいずれもクレームを「名前」か「固定の必須集合」としてしか扱わない。このため、claims.yaml を正本にしてそこから `claims_supported` を生成する方向は成り立つ。逆方向（メタデータから claims.yaml を作る）は情報が足りず成り立たない。

### Gaps（未取得。既知の仕様として要確認）
- OIDC Discovery 1.0 の `claims_supported` は「OP が値を提供しうる Claim 名の JSON 配列」で、型などは持たない（記憶ベース）。確認先: https://openid.net/specs/openid-connect-discovery-1_0.html
- RFC 9068（JWT Profile for OAuth 2.0 Access Tokens）は必須クレーム `iss`/`exp`/`aud`/`sub`/`client_id`/`iat`/`jti` を本文で定めるだけで、機械可読なスキーマは持たない（記憶ベース）。確認先: https://www.rfc-editor.org/rfc/rfc9068
- RFC 9728（Protected Resource Metadata）は `resource`、`authorization_servers`、`scopes_supported`、`bearer_methods_supported` などを定めるが、RS が要求するクレームを宣言するフィールドはない（記憶ベース）。確認先: https://www.rfc-editor.org/rfc/rfc9728
- OpenID Federation の metadata_policy（`value`/`one_of`/`subset_of`/`essential` などの演算子）はメタデータ値の制約言語である。クレーム設計書への応用例があるかは未確認。

## Q3. API 記述（OpenAPI / AsyncAPI / Arazzo）とゲートウェイ設定における必須クレームの宣言（config-as-spec）

### Takeaway
OpenAPI 本体に JWT クレームを記述する標準の仕組みはなく、`x-jwt-claims` のような共通拡張も見つからなかった。必須クレームを機械可読に宣言する手段は、ゲートウェイ製品ごとの拡張や設定（Azure APIM の `required-claims`、Tetrate の `x-tsb-authorization.claims`、Yandex の `x-yc-apigateway-authorizer:jwt`、Envoy の `claim_to_headers` など）に分かれている。

### Cited Findings
- `x-jwt-claims` という標準や共通の OpenAPI 拡張は検索で見つからなかった。近いものはベンダー拡張だけだった — [検索結果: Yandex](https://yandex.cloud/en/docs/api-gateway/concepts/extensions/jwt-authorizer), [Tetrate](https://docs.tetrate.io/service-bridge/refs/tsb/application/v2/openapi_extensions), [Google API Gateway](https://docs.cloud.google.com/api-gateway/docs/oasv3-extensions)
- Tetrate Service Bridge の OpenAPI 拡張 `x-tsb-authorization` は、要求するクレームを `claims` リスト（型 `tetrateio.api.tsb.gateway.v2.Subject.JWTClaims`）で書ける — [Tetrate](https://docs.tetrate.io/service-bridge/refs/tsb/application/v2/openapi_extensions)（2026-11-22 に確認。取り込んだ版の 1.5.x の URL は 404 なので、版のない URL に替えた）
- Yandex Cloud の `x-yc-apigateway-authorizer:jwt` は securityScheme の中に置き、署名・iss・aud を検証し、失敗時は 403 を返す — [Yandex Cloud](https://yandex.cloud/en/docs/api-gateway/concepts/extensions/jwt-authorizer)
- Azure APIM の `validate-jwt` は必須クレームを XML で宣言する。`<required-claims><claim name="..." match="all|any" separator=","><value>...</value></claim></required-claims>` の形で書き、`match` の既定は `all`。スコープは global / workspace / product / API / operation、`exp` は既定で必須（ドキュメント更新 2026-08-18） — [Microsoft Learn](https://learn.microsoft.com/en-us/azure/api-management/validate-jwt-policy)
- Envoy `jwt_authn` が自前で検査するのは `issuer`（iss）、`audiences`、`subjects`（sub に対する StringMatcher）、`require_expiration`、`max_lifetime`、`allowed_algorithms` まで。任意のクレーム値の条件は持たない。検証済みの payload は `payload_in_metadata` で DynamicMetadata に、`claim_to_headers` でヘッダに渡し、RBAC や ext_authz が消費する — [Envoy jwt_authn proto](https://www.envoyproxy.io/docs/envoy/latest/api-v3/extensions/filters/http/jwt_authn/v3/config.proto)

### Inferences
- ゲートウェイ設定は「RS 側が要求するクレームと値」の正本になりうる。しかし製品ごとに形式が違い、意味や寿命などの設計情報は持たない。
- 実用的な連携は、claims.yaml の `consumers` 列（どの RS／ゲートウェイが読むか）を起点に、各ゲートウェイ設定を生成するか、設定と claims.yaml の差分を CI で検査することである。
- OpenAPI に寄せる場合は、securityScheme か operation に独自拡張（例: `x-required-claims: [ref → claims.yaml]`）を置くのが現実的である。ただし先例は各ベンダー独自のものに限られる。

### Gaps（未取得）
- OpenAPI 3.1/3.2 の securitySchemes は oauth2 の scopes（3.2 では `oauth2MetadataUrl` なども）までで、クレームは記述できない（記憶ベース）。確認先: https://spec.openapis.org/oas/v3.2.0.html
- AsyncAPI と Arazzo のクレーム記述も同様に未確認。
- Kong jwt プラグインの `claims_to_verify`（exp/nbf のみ）、Apigee VerifyJWT の `AdditionalClaims`、AWS API Gateway HTTP API JWT authorizer（issuer/audience/scopes のみ）は記憶ベースで未確認。

## Q4. トークン属性をモデル化する認可スキーマ（Cedar + Verified Permissions、OpenFGA、OPA、AuthZEN）

### Takeaway
認可スキーマのうち、トークンのクレームを型付きスキーマに対応づける仕組みを公式に持つのは、Amazon Verified Permissions の identity source と Cedar schema である。ID トークンのクレームは principal の属性に、アクセストークンのクレームは context に入る。Cedar schema は型付きなので、クレームの type と必須性を機械検査できる。

### Cited Findings
- Verified Permissions での対応づけ:
  - ID トークンのクレームは principal（ユーザエンティティ）の属性になり、groups クレームは親グループエンティティになる
  - アクセストークンのクレームは `context.token.<attr>` として参照する
  - groups 以外のクレームは、JSON モードで schema（commonTypes）に手で追加する必要がある

  — [AWS: Mapping OIDC tokens to schema](https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/oidc-map-token-to-schema.html)（`context.token.<属性>` の記述はこのページにある。取り込んだ版が併記した `identity-sources_map-token-to-schema.html` は、いま概要のページに転送されるので外した）
- policy store に schema がある場合は、principal 型と、ポリシーで使う属性を schema に追加しなければならない。`cognito:username` のように `:` や `.` を含むクレーム名には特殊な記法が必要になる — [同上](https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/oidc-map-token-to-schema.html), [Cognito 版](https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/cognito-map-token-to-schema.html)
- OpenID AuthZEN Authorization API 1.0 は 2026-01-12 に Final として承認された。Subject は必須の識別子と任意の properties オブジェクトを持つ — [OIDF 承認告知](https://openid.net/authorization-api-1-0-final-specification-approved/), [仕様](https://openid.net/specs/authorization-api-1_0.html)
- AuthZEN の draft-03 には「Many authorization systems are stateless, and expect the client (PEP) to pass in any properties」とある（Final でも同じ文言かは未確認） — [draft-03](https://openid.net/specs/authorization-api-1_0-03.html)

### Inferences
- Cedar の型システム（必須/任意の属性、Long/String/Set/Record）は、claims.yaml の type、shape、consumers をそのまま写せる受け皿になる。claims.yaml から Cedar schema の `commonTypes` を生成し、`cedar validate` でポリシーとの整合を CI 検査する流れが組める。
- AuthZEN の subject properties は、PEP がトークンのクレームを PDP に渡すときの線形式（wire format）にすぎず、スキーマではない。

### Gaps（未取得）
- OpenFGA のモデル（type/relation と conditions の CEL パラメータ）と、OPA の input schema（`--schema` による型検査）については、本調査では一次資料を取得していない。確認先: https://openfga.dev/docs/modeling/conditions, https://www.openpolicyagent.org/docs/policy-language#schema-annotations

## Q5. フィールド単位メタデータを持つデータ契約・分類体系（ODCS、datacontract、Fideslang、JSON Schema annotations）

### Takeaway
「列ごとの意味・分類・品質・所有者を YAML で宣言し、JSON Schema と CLI で CI 検査する」という運用は、データ契約の分野で確立している。中でも ODCS（Apache 2.0、LF AI & Data）は claims.yaml の構造面のお手本になる。PII 分類の語彙には、Fideslang（CC BY 4.0）の階層ラベルをそのまま使える。

### Cited Findings
- ODCS（Open Data Contract Standard）の現行版は v3.2.0、ライセンスは Apache 2.0、組織は LF AI & Data Foundation / Bitol。JSON Schema は `schema/odcs-json-schema-latest.json` にあり、IDE で YAML を検証できる。JSON Schema と標準本文が矛盾した場合は標準が優先する — [GitHub bitol-io/open-data-contract-standard](https://github.com/bitol-io/open-data-contract-standard), [ODCS docs](https://bitol-io.github.io/open-data-contract-standard/latest/)
- Fideslang のデータカテゴリは階層ラベルで、`user.contact` → `user.contact.email` のように細分化する。YAML でフィールドに `data_categories` を付ける例がある。ライセンスは CC BY 4.0、管理は IAB Tech Lab（Ethyca から寄贈）— [Ethyca data mapping annotations](https://ethyca.com/docs/data-mapping/guides/data-mapping-annotations), [IAB Tech Lab fideslang](https://iabtechlab.github.io/fideslang), [IAB Tech Lab の寄贈の告知（2024-01-09）](https://iabtechlab.com/iab-tech-lab-accelerates-privacy-taxonomy-project-with-fides-language-product-donation)（取り込んだ版が引いた Ethyca のブログは 404）
- 古い資料には `user.provided.identifiable.contact.email` という旧体系のパスも見られ、版によってラベルが変わっている — [Ethyca blog](https://ethyca.com/blog/fideslang-a-taxonomy-for-privacy-engineering)

### Inferences
- claims.yaml の `pii_category` 列を自由記述ではなく Fideslang のラベル（版を固定する）に限定すると、外部の語彙に揃えられ、linter で列挙値として検査できる。
- ODCS の「標準本文 + 付属 JSON Schema（本文が優先）」という構成は、ガイド本文と claims.yaml スキーマの関係づけにそのまま使える。

### Gaps
- ODCS v3.2.0 のリリース日と、property レベルのフィールド名（classification、criticalDataElement など）は今回取得したページから確認できなかった。
- datacontract-cli（datacontract.com）の CI 機能（lint、breaking change 検出）は未取得。確認先: https://github.com/datacontract/datacontract-cli

## Q6. クレームマッパーを含む IdP の config-as-code（Keycloak、Terraform）は CI 付きで正本として使われているか

### Takeaway
Keycloak では keycloak-config-cli（adorsys）による YAML/JSON の宣言的管理と GitOps 運用が一般的で、protocolMappers（クレームマッパー）もクライアント設定として管理できる。ただし、そこに書けるのは「どの属性をどのクレームに入れるか」という実装の配線だけで、意味、寿命、消費者といった設計情報は持たない。

### Cited Findings
- keycloak-config-cli は realm、client、user、role を JSON か YAML で宣言的に管理するツールで、GitOps 対応を掲げ、Keycloak を再起動せずに適用できる — [keycloak-config-cli docs](https://adorsys.github.io/keycloak-config-cli/), [GitHub](https://github.com/adorsys/keycloak-config-cli)
- client 設定（protocolMappers を含む）の作成と更新に対応している。YAML anchors や、1 ファイルに複数の realm を書く形式もサポートする — [GitHub](https://github.com/adorsys/keycloak-config-cli), [CHANGELOG v5.1.0](https://github.com/adorsys/keycloak-config-cli/blob/v5.1.0/CHANGELOG.md)
- 実運用の例として、ID を除いた partial export から YAML を作り、protocolMappers を jq で名前順に並べて diff を安定させる、という報告がある — [Keycloak forum](https://forum.keycloak.org/t/how-do-you-manage-your-realm-configuration/18099)（非公式）
- Go 製の keycloak-provisioner は `--dry-run` を持ち、realm export 形式をそのまま使う。Kubernetes 用の keycloak-controller は keycloak-config-cli をラップしている — [keycloak-provisioner](https://github.com/datarocks-ag/keycloak-provisioner), [keycloak-controller](https://www.github.com/DoodleScheduling/keycloak-controller)

### Inferences
- IdP の設定は「発行側の実装」の正本、claims.yaml は「設計」の正本という二層に分けるのが自然である。CI で claims.yaml の `writer/issuer`・`data source`・`carried_in` と IdP 設定の mapper 一覧を突き合わせれば、設計にないクレームの発行や、設計にあるのに発行されていないクレームを検出できる。

### Gaps（未取得）
- Terraform provider（auth0、okta、azuread、aws_cognito）でのクレーム、mapper、optional claims の記述と CI 運用事例は取得していない。

## 総括: claims.yaml の列ごとの対応状況

| claims.yaml 列 | 標準・先例での対応 |
|---|---|
| name / namespace | SD-JWT VC `path`・`vct`、mdoc namespace、IANA registry（名前の衝突検査） |
| type / shape | 現行 Type Metadata では削除済み（-12）。JSON Schema か Cedar schema で別途持つ |
| 必須性・選択的開示 | SD-JWT VC `mandatory`/`sd`、OpenID4VCI `mandatory` |
| 表示ラベル | `display`（locale/label） |
| meaning / not-meaning | IANA の Claim Description と ARF namespace の意味定義（どちらも自然文）。否定的な定義（not-meaning）の先例はなし |
| writer / data source | IdP の mapper 設定だけ（設計としての先例はなし） |
| lifetime / volatility | 先例なし |
| carried_in | OpenID4VCI の credential configuration（形式単位） |
| consumers | ゲートウェイの required-claims、Cedar schema（間接的） |
| size max_bytes / max_items | 先例なし |
| pii_category | Fideslang data categories、ODCS の分類 |
| confidential_from | 先例なし（SD-JWT VC の `sd` が部分的に近い） |
| decision / rationale / evidence | 先例なし |

結論: 「設計判断、根拠、寿命、サイズ、秘匿先までを持つクレーム設計書のフォーマット」で、かつ CI で検査されるものは見つからなかった（本調査の範囲内）。現実的な方針は、claims.yaml を SD-JWT VC claim metadata の上位集合にし（`path`/`mandatory`/`sd`/`display` を同名・同義で持つ）、PII は Fideslang、名前の衝突は IANA CSV、形状は JSON Schema に揃えることである。そのうえで Cedar schema、ゲートウェイ設定、`claims_supported` を生成するか、差分を検査する。
