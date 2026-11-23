<!-- template_version: 0.3.0 -->
# マルチテナント（modules/M_multitenancy）

> テンプレートです。候補と検討の問いだけを載せ、採否の理由の見本は載せません（理由の写し書きを防ぐため。#4 の方針）。判断は台帳（claims.yaml など）に 1 回だけ書き、ここからは ID で参照します。

- 使う場面：1 つの発行者・API・DB を、複数のテナント（顧客企業・組織）で共有する境界。テナントをまたぐ利用者・運用者・取引先がいる境界
- 組み合わせ：`template:00_core#scope-boundary`（境界ごとにこのモジュールを使うと書く）、`template:modules/M_token_validation#issuer`（iss の許可リスト）、`template:modules/M_data_layer#db-context-setter`（DB の文脈）、`template:modules/M_authz_pdp#object-level`（オブジェクト単位の認可）
- Lite での扱い：マルチテナントは #4 の Lite の判定の 5 問の 1 つで、Yes なら Full です（`template:README#lite-criteria`）。そのため、このモジュールの記入欄は Full で書きます
- 台帳の列：トークン目録の `tenant_binding`（`by`：iss・aud・tid・org_id・claim と、`claim`：台帳の行の ID）・`signing_key_scope`（per_tenant・shared・per_client）、台帳の `enforced_at`・`integrity_until`・`usage`（`templates/registry/README.md` の 3.）。claim_lint の L9（#6）がこの宣言を突き合わせます
- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施。

<a id="tenant-determination"></a>
## 1. テナントの判定手段〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_multitenancy#tenant-determination`
<!-- req:p02-tenant-org.R1 req:p05-multitenancy.R1 req:p08-reissue-triggers.R1 -->

決めること：受け手が「このトークンはどのテナントのものか」を、何で決めるか。テナントを表す登録済みのクレームは IANA の JWT Claims にないので（slide:p02-tenant-org）、独自クレームを作る前に、発行者や宛先をテナントごとに分けられないかを先に検討します。

| 判定の手段 | 検討の問い | 受け手が確かめること | `tenant_binding.by` | 根拠 |
| --- | --- | --- | --- | --- |
| テナントごとの発行者（Keycloak のレルムなど） | テナントの数だけ発行者と鍵を運用できるか。受け手は発行者の許可リストを持てるか | iss を許可リストと完全一致で比べ、鍵はその発行者のものだけを使う | `iss` | slide:p05-multitenancy、RFC 8725 §3.8 |
| テナントごとの宛先（テナントを含む resource の URI） | クライアントが要求ごとに resource を指定できるか | aud に自分のテナントの URI が含まれるか | `aud` | slide:p02-tenant-org、RFC 8707 §2 |
| IdP のテナントのクレーム（Entra ID の tid、Auth0 の org_id） | 共有の発行者で、テンプレート形式の iss を使っていないか | iss の `{tenantid}` を tid で置き換えてから完全一致で比べる | `tid`・`org_id` | slide:p05-multitenancy |
| 組織の独自クレーム（名前空間の中の tenant_id など） | 上の手段と組み合わせるか。クレームだけで分けていないか | クレームの値と、iss（か aud）から決まるテナントが一致するか | `claim`（台帳の行の ID も書く） | slide:p02-tenant-org、slide:p05-multitenancy |
| テナントの切り替え | 利用者がテナントを切り替えるか。切り替えたら新しいトークンを取り直すか | BFF のテナントの文脈も置き換え、受け手は要求ごとにテナントを照合する | — | slide:p08-reissue-triggers |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| テナントを決める手段（複数可） |  |  | `token_types[].tenant_binding.by` |
| テナントのクレームの行 |  |  | `token_types[].tenant_binding.claim`、`claims[].enforced_at` |
| iss（か aud）とテナントのクレームを照合する受け手 |  |  | `claims[].enforced_at` |
| テナントの切り替えと再発行 |  |  | `catalog:issue_events#I24` への回答 |

根拠：slide:p02-tenant-org、slide:p05-multitenancy、slide:p08-reissue-triggers、RFC 8707 §2、RFC 8725 §3.8

<a id="signing-keys"></a>
## 2. テナント単位の署名鍵〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_multitenancy#signing-keys`

決めること：署名鍵をどの単位で持つか。共有の発行者・共有の鍵は、ほかのテナントのトークンも通しうる、という点を踏まえて決めます（ケーススタディのシナリオ A の A9・A10 は、テナント間で共有した鍵で他テナントを名乗る攻撃）。

| 単位 | 検討の問い | `signing_key_scope` | 根拠 |
| --- | --- | --- | --- |
| テナントごと | 鍵の数と、ローテーションの手間を運用できるか | `per_tenant` | NIST IR 8587 §5.2.1.2 |
| 共有 | テナントのクレームと iss の照合だけで、他テナントの名乗りを止められるか | `shared` | slide:p05-multitenancy |
| クライアントごと | 連携先ごとに鍵を分ける必要があるか | `per_client` | 筆者の提案：連携先に鍵を渡す構成を候補に含める（追跡 #4） |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 署名鍵の単位 |  |  | `token_types[].signing_key_scope` |
| 鍵と発行者の対応を受け手が確かめる方法 |  |  | `token_types[].issuers`・`key_source` |

根拠：NIST IR 8587 §5.2.1.2、slide:p05-multitenancy、jwt-claims-casestudy@080b8da:A9（裏付け）、筆者の提案：連携先に鍵を渡す構成を候補に含める（追跡 #4）

<a id="data-layer-filter"></a>
## 3. データ層での絞り込み〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_multitenancy#data-layer-filter`
<!-- req:p05-multitenancy.R4 req:p05-bola.R2 req:p12-review-viewpoints.R14 -->

決めること：トークンのテナントと、保存データのテナントが一致することを、データの側でどう確かめるか。トークンの検証だけでは、保存データのテナントは確かめられません（slide:p05-bola）。DB の文脈を誰が設定するかは `template:modules/M_data_layer#db-context-setter` で決めます。

| 手段 | 検討の問い | 崩れる条件 | 根拠 |
| --- | --- | --- | --- |
| すべての SQL に明示のテナントの条件（ID 指定・集計も） | 書き忘れを、規約とレビューと試験で見つけられるか | 条件を書き忘れた集計の SQL（ケーススタディの A7） | slide:p07-trust-boundary、ASVS v5.0.0-8.4.1 |
| 行単位の制御（PostgreSQL の RLS など）と、取引単位の文脈 | RLS をすり抜ける主体を通常の経路から外せるか（`template:modules/M_data_layer#masking-rls-bypass`） | 接続プールで前の要求の文脈が残る（`template:modules/M_data_layer#pool-context`） | slide:p07-row-level-security、slide:p07-connection-pool |
| 上の 2 つの併用 | 両方を保守できるか | — | slide:p07-trust-boundary |
| 利用者が指定した ID での取り出し | 取り出したオブジェクトの持ち主・テナントを、トークンの sub・テナントと照合するか | ID の直接指定（BOLA。ケーススタディの A6） | slide:p05-bola |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| データ側でテナントを確かめる手段 |  |  | `claims[].enforced_at`（DB の行）、`claims[].integrity_until` |
| ID 指定の取り出しでの持ち主の照合 |  |  | `claims[].enforced_at` |
| テナントの文脈が無いときの挙動 |  |  | `claims[].on_missing` |

根拠：slide:p05-multitenancy、slide:p05-bola、slide:p07-trust-boundary、slide:p07-row-level-security、ASVS v5.0.0-8.4.1、jwt-claims-casestudy@080b8da:A7（裏付け）

<a id="cross-tenant"></a>
## 4. テナントをまたぐ場面〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_multitenancy#cross-tenant`
<!-- req:p05-cross-tenant.R1 req:p05-cross-tenant.R2 -->

決めること：テナントをまたぐ主体ごとに、識別子と権限をどう出すか。テナントをまたいだ暗黙の名寄せはしない前提で、場面ごとに決めます（slide:p05-cross-tenant）。

| 場面 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 複数のテナントに属する利用者 | 利用者のキーはテナントごとに別の値か（Entra の oid はテナントごとに別） | テナント ID と主体 ID の複合キー／組織の不変の利用者 ID | slide:p05-cross-tenant |
| データアクセスのキー | データのキーにテナントを含めるか | テナント ID を含む複合キー／テナントを含まないキー | slide:p05-cross-tenant |
| テナント横断の運用者 | 運用者は顧客として振る舞うか、実行者として名を残すか | 下の 5.（委任のトークン） | slide:p05-cross-tenant |
| 取引先（B2B） | 相手の発行者に交換して渡すか。外部にはどの識別子を出すか | トークン交換で相手の発行者へ／ペアワイズの識別子 | slide:p05-cross-tenant、template:modules/M_privacy_minimization#identifier-sectors |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 複数テナントの利用者のキー |  |  | `claims[].usage: identifier`・`identifier_properties` |
| データアクセスのキーに含めるもの |  |  | `claims[].enforced_at` |
| 取引先に出す識別子 |  |  | `token_types[].subject_type`、`claims[].recipients_external` |

根拠：slide:p05-cross-tenant、ASVS v5.0.0-8.4.1

<a id="operator-access"></a>
## 5. 運用者のテナント横断作業〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_multitenancy#operator-access`
<!-- req:p06-flow-multitenant-saas.R5 -->

決めること：運用者が顧客のテナントで作業するときのトークン・承認・監査。運用者が顧客になりすますと、sub だけでは区別できません（slide:p05-system-privileges）。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| トークン | 運用者の操作を、交換で得た委任のトークン（sub は顧客、act.sub は運用者）で行うか | トークン交換の委任／運用者のテナント外の専用の権限／なりすまし（Impersonate） | slide:p06-flow-multitenant-saas、RFC 8693 §4.1 |
| 交換の可否 | 誰がどの顧客に対して交換してよいかを、何で決めるか | may_act／交換のサービスの方針 | RFC 8693 §4.4、template:profiles/P4_ai_agent_delegation#delegation-policy |
| 緊急時の承認と期限 | 承認の記録（RAR・CIBA）と短い期限を、交換の時点で確かめるか | 承認 ID を確かめる／確かめない | slide:p05-system-privileges、slide:p06-flow-multitenant-saas |
| 監査 | 顧客の sub と運用者の act の両方を残すか | 両方／片方 | slide:p06-flow-multitenant-saas、template:modules/M_privacy_minimization#audit-log |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 運用者のトークン |  |  | `token_types[]`（委任の種別）、`claims[]`（act） |
| 承認と期限の確かめ方 |  |  | `hops[].exchanger`、`claims[].enforced_at` |
| 監査に残す項目 |  |  | `claims[].log_policy` |

根拠：slide:p06-flow-multitenant-saas、slide:p05-system-privileges、slide:p05-cross-tenant、RFC 8693 §4.1、RFC 8693 §4.4
