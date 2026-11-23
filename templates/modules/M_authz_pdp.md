<!-- template_version: 0.3.0 -->
# 認可の方式と PDP（modules/M_authz_pdp）

> テンプレートです。候補と検討の問いだけを載せ、採否の理由の見本は載せません（理由の写し書きを防ぐため。#4 の方針）。判断は台帳（claims.yaml など）に 1 回だけ書き、ここからは ID で参照します。

- 使う場面：認可に使うクレーム（`usage: authz`）があるとき。どのモデルで判定するか、何をトークンに載せ、何を都度問い合わせるか、オブジェクト単位の判定をどこで行うかを決める
- 組み合わせ：どのプロファイルとも組み合わせる。テナントの絞り込みは `template:modules/M_multitenancy`、DB の行の絞り込みは `template:modules/M_data_layer`
- Lite での扱い：〔Full：記入／Lite：参照〕。Lite では、載せるクレームの判断を台帳（`usage`・`volatility`・`max_items`・`enforced_at`）に書き、問い合わせに切り替えた理由を `rationale` に書く
- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施。

<a id="model-choice"></a>
## 1. RBAC・ABAC・関係ベース（併用）の判断表〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_authz_pdp#model-choice`
<!-- req:p05-authz-models.R1 req:p05-authz-models.R4 -->

決めること：操作ごとに、役割・属性・関係のどれで判定するか（併用を含む）。どのモデルでも、トークンが運ぶのは判定の入力の一部です。

| モデル | 検討の問い | トークンに載せる候補 | 判定を置く場所の候補 | 根拠 |
| --- | --- | --- | --- | --- |
| RBAC（役割） | 機能の粗い区別（使えるか）だけで足りるか。役割の数が増え続けないか | `roles`・`groups`（RFC 9068 §2.2.3.1） | サービス（PEP）／PDP | slide:p05-authz-models、RFC 9068 §2.2.3.1 |
| ABAC（属性） | 部署・地域・認証の強さなど、主体・対象・環境の属性で決めるか | 主体の安定した属性（寿命の間に変わらないもの） | PDP（対象と環境の属性は PIP・PEP から） | NIST SP 800-162 §2、slide:p05-authz-models |
| 関係ベース（ReBAC） | 所有者・共有先など、主体と対象の関係で決めるか | `sub` だけ（関係は PDP に持たせる） | PDP（関係の保存先） | Pang et al.「Zanzibar: Google's Consistent, Global Authorization System」（USENIX ATC 2019）§2、slide:p05-authz-models |
| 併用 | 粗い区別は RBAC、細かい区別は ABAC・ReBAC のように分けるか | 層ごとに分ける（4.） | 層ごとに分ける | slide:p05-coarse-fine-layers |

記入欄（操作ごとに 1 行）：

| 操作 | 選んだモデル（書き手が書く） | 理由（書き手が書く） | 入力のクレーム（台帳の ID） |
| --- | --- | --- | --- |
|  |  |  |  |

根拠：slide:p05-authz-models、NIST SP 800-162 §2、RFC 9068 §2.2.3.1

<a id="carry-or-query"></a>
## 2. 載せるか、問い合わせるか〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_authz_pdp#carry-or-query`
<!-- req:p01-self-contained-vs-reference.R1 req:p04-token-is-snapshot.R2 req:p04-carry-or-query.R1 req:p04-size-budget.R4 req:p05-authz-models.R2 req:p06-issuance-hook.R3 req:p08-decision-table.R4 req:p09-do-not-carry.R5 req:p04-carry-or-query.R5 req:p12-antipatterns-2.R1 -->

決めること：判定の入力をトークンに載せるか、都度 PDP・DB・UserInfo に問い合わせるか。トークンは発行時点の写しで、発行後の変更は届きません。

| # | 検討の問い | 「いいえ」のときの候補 | 根拠 |
| --- | --- | --- | --- |
| 1 | 認可・ルーティングに使うか | 載せない（UserInfo・DB で取る） | slide:p04-carry-or-query、NIST SP 800-63C-4 §3.10 |
| 2 | 寿命の間、値が変わらないか（変わってから反映までに許す時間が、載るトークンの受け入れの上限より長いか） | 都度問い合わせる（PDP・DB）／寿命を縮める／失効を伝える | slide:p04-token-is-snapshot、slide:p08-stale-claims |
| 3 | 小さく、サイズの上限に収まるか（細かい権限の一覧・長い一覧でないか） | 参照（ID）だけを載せ、中身は API で引く／PDP に問い合わせる | slide:p04-size-budget、slide:p09-do-not-carry、jwt-claims-casestudy@080b8da:A6 |
| 4 | 受け手の全員が要るか | 宛先ごとに絞る（交換のときに付ける） | slide:p04-carry-or-query、slide:p06-narrow-downstream |
| 5 | 発行時フックで足すなら、安定した属性だけか（大きな権限表を足していないか） | フックでは安定した属性だけを足し、権限表は PDP | slide:p06-issuance-hook |
| 6 | 剥奪をすぐ効かせたい操作か | 短命に加えて、イントロスペクション・PDP で都度判定する | slide:p08-decision-table、RFC 7662 §2 |
| 7 | 自己完結型（JWT）か参照型（イントロスペクション）か。寿命と取り消しの要件から決めたか | 自己完結型＋短命／参照型（不透明＋イントロスペクション）／入口で作り直す | slide:p01-self-contained-vs-reference、`issuance_profile.at_format` |

記入欄（クレームの候補ごとに 1 行）：

| 候補 | 載せる・問い合わせる（書き手が書く） | 理由（書き手が書く） | 台帳の ID |
| --- | --- | --- | --- |
|  |  |  | `claims[].decision`・`usage`・`volatility`・`max_items`・`overflow_strategy` |

根拠：slide:p04-carry-or-query、slide:p04-token-is-snapshot、slide:p08-decision-table、slide:p01-self-contained-vs-reference

<a id="object-level"></a>
## 3. オブジェクト単位の認可（BFLA・BOLA）〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_authz_pdp#object-level`
<!-- req:p05-authz-models.R2 req:p05-bola.R1 req:p05-bola.R2 req:p05-bola.R3 req:p06-validation-split.R5 -->

決めること：認可を 3 段（トークンの検証・機能を使えるか・このオブジェクトか）で行い、オブジェクトとの関係を毎回データの側で確かめる方法。`roles` に承認者があっても、この請求書を承認できるかは分かりません。

| 段 | 検討の問い | 確かめ方の候補 | 根拠 |
| --- | --- | --- | --- |
| 1. トークンの検証 | 署名・`iss`・`aud`・`exp`・`typ` を確かめたか | `template:modules/M_token_validation#validation-order` | slide:p05-bola |
| 2. 機能を使えるか（BFLA） | その操作を `roles`・`scope` が許すか | サービスで照合する／PDP | OWASP API Security Top 10 2023 API5、slide:p05-bola |
| 3. このオブジェクトか（BOLA） | 利用者が指定した ID で取り出すすべての処理で、オブジェクトの所有者・テナントを、トークンの `sub`・テナントとデータの側で照合するか | 取り出す SQL の条件に所有者・テナントを入れる／RLS／PDP の関係 | OWASP API Security Top 10 2023 API1、ASVS v5.0.0-8.2.2、slide:p05-bola |
| 照合する時点 | データを取るときに照合するか（入口・WAF では防げない） | データを取るとき | slide:p06-validation-split、slide:p05-bola |
| 失敗の応答 | 照合に失敗したとき、存在を隠すなら 404、示してよいなら 403 のどちらにするか | 404／403 | RFC 9110 §15.5.4、slide:p05-bola |
| 回帰の試験 | 利用者 A・B の自動試験で、他人のオブジェクトを読めないことを確かめるか | 試験を置く | slide:p05-bola、jwt-claims-casestudy@080b8da:A6 |

記入欄（オブジェクトの種類ごとに 1 行）：

| オブジェクト | 照合の仕方（書き手が書く） | 失敗の応答（書き手が書く） | 理由（書き手が書く） | 台帳の ID |
| --- | --- | --- | --- | --- |
|  |  |  |  | `claims[].enforced_at`（sub・テナントの行） |

根拠：slide:p05-bola、OWASP API Security Top 10 2023 API1、RFC 9110 §15.5.4、ASVS v5.0.0-8.2.2

<a id="layers"></a>
## 4. 粗い権限・取引単位・オブジェクト単位の 3 層〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_authz_pdp#layers`
<!-- req:p05-coarse-fine-layers.R1 req:p05-role-explosion.R2 -->

決めること：権限を 3 つの層に分け、それぞれの置き場所を決める。ロールは役割の名前にし、テナントや対象ごとの許可をロールの名前に混ぜないこと（ロール爆発を避ける）。

| 層 | 表すこと | クレームの候補 | 置き場所の候補 | 根拠 |
| --- | --- | --- | --- | --- |
| 粗い | 機能の範囲・役割 | `scope`・`roles`・`groups` | トークン（長く安定） | RFC 9068 §2.2.3、slide:p05-coarse-fine-layers |
| 取引単位 | この支払い・この金額 | `authorization_details`（宛先ごとに絞る） | トークン | RFC 9396 §2・§9.1、slide:p05-coarse-fine-layers |
| オブジェクト単位 | この文書を読めるか | 載せない | PDP・DB で都度判定（3.） | slide:p05-coarse-fine-layers |
| ロールの名前 | テナント・対象をロールの名前に入れていないか | 役割の名前だけ（テナントは別のクレーム） | 台帳の `value_vocabulary` | slide:p05-role-explosion |

記入欄：

| 層 | 使うクレーム（書き手が書く） | 理由（書き手が書く） | 台帳の ID |
| --- | --- | --- | --- |
| 粗い |  |  |  |
| 取引単位 |  |  |  |
| オブジェクト単位 |  |  |  |

根拠：slide:p05-coarse-fine-layers、slide:p05-role-explosion、RFC 9396 §9.1

<a id="pep-pdp-inputs"></a>
## 5. PEP・PDP の分担と判断の入力の出どころ〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_authz_pdp#pep-pdp-inputs`
<!-- req:p05-pep-pdp.R1 req:p05-pep-pdp.R2 -->

決めること：トークンを検証する部品（PEP：入口・サービス）と、判断する部品（PDP）の分担と、判断の入力ごとの出どころ。トークンが有効かどうかだけで認可しません。

| 判断の入力 | 検討の問い | 出どころの候補 | 根拠 |
| --- | --- | --- | --- |
| 主体の安定した属性 | `sub`・テナント・ロールなど、寿命の間に変わらない属性か | トークンのクレーム | slide:p05-pep-pdp、NIST SP 800-162 §3 |
| 関係・オブジェクトの属性 | 所有者・共有先・文書の区分か | PIP（DB・関係の保存先） | slide:p05-pep-pdp |
| 環境・文脈 | IP アドレス・時刻・端末の状態か | PEP が要求の時点で取る（トークンに入れると古くなる） | slide:p05-pep-pdp、slide:p06-access-context |
| 分担 | PEP が検証し、判断は方針に従う PDP に任せるか。サービスの中で判断するか | 外部の PDP／サービスの中のライブラリ | NIST SP 800-162 §3、NIST IR 8587 §4.1.4 |

記入欄：

| 判断の入力 | 出どころ（書き手が書く） | 理由（書き手が書く） | 台帳の ID |
| --- | --- | --- | --- |
|  |  |  | `claims[].source_system` |

根拠：slide:p05-pep-pdp、NIST SP 800-162 §3、NIST IR 8587 §4.1.4

<a id="registry-map"></a>
## 6. 台帳・目録との対応

項目 ID：`template:modules/M_authz_pdp#registry-map`

| 決めること | 列 |
| --- | --- |
| 認可に使うか | `claims[].usage`（authz） |
| 載せるか・問い合わせるか | `claims[].decision`・`rationale`・`volatility`・`on_revoke` |
| サイズ | `claims[].max_bytes`・`max_items`・`overflow_strategy`（R8） |
| 照合する場所 | `claims[].enforced_at` |
| 値の出どころ | `claims[].source_system`・`provenance` |
| AT の形式 | `issuance_profile.at_format`、`token_types[].revocation` |

根拠：templates/registry/README.md の 3.1、slide:p04-carry-or-query
