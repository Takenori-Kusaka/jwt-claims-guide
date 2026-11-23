<!-- template_version: 0.3.0 -->
# IdP モジュール：Keycloak（modules/M_idp_keycloak）

> テンプレートです。候補と検討の問いだけを載せ、採否の理由の見本は載せません（理由の写し書きを防ぐため。#4 の方針）。判断は台帳（claims.yaml など）に 1 回だけ書き、ここからは ID で参照します。

- 使う場面：Keycloak を発行者にする境界。Keycloak 以外の IdP のモジュールは #21（後回し）です
- 版：Keycloak 26.8。文書は 2026-11-23 に `https://www.keycloak.org/docs/latest/` を見て確かめました。その日の「latest」は **26.8.2** の文書でした（ページの版の選択に 26.8.2・26.7.5・26.6.4 が並ぶ）。ケーススタディの実測は 26.8.0 です（jwt-claims-casestudy@080b8da の `results/summary.md`）。版を上げたら、この文書の「確かめた」の行を確かめ直します（slide:p03-recent-changes）
- 既定値の書き分け：「文書」＝Keycloak の文書で確かめた値。「ソースの要約」＝文書に書かれておらず、26.8.2 のソースの要約で補った値（`research/template-design/unverified.md` の V31。行は直接確かめていない）。「実測」＝ケーススタディで 26.8.0 を動かした結果。ソースの要約の値は、Lite の既定の回答の引き継ぎの根拠にしません（V31 の扱い）
- 組み合わせ：`template:00_core#catalog-answers`（カタログへの回答）、`template:00_core#issuance-profile`、`template:modules/M_token_validation`
- Lite での扱い：5.（カタログの既定の回答）の「引き継げる」の行だけ、Lite で「設定を確かめた」の 1 欄で回答できます（`tools/claim_lint/RULES.md` の「Lite の既定の回答の引き継ぎ」）。ほかの項目は〔Full：記入／Lite：参照〕
- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施。

<a id="triggers"></a>
## 1. 契機：いつクレームが計算されるか〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_idp_keycloak#triggers`
<!-- req:p03-keycloak-aud-lightweight.R7 req:p03-recent-changes.R2 req:p06-issuance-hook.R5 req:p08-refresh-reevaluation.R3 -->

決めること：Keycloak でクレームが作られる契機と、そのときの挙動を、設計の前提として記録します。Keycloak の「フック」はプロトコルマッパーで、マッパーを置いて初めて属性がクレームになります（slide:p03-keycloak-mappers）。

| 契機 | Keycloak の挙動 | 区分 | 設計で決めること | 根拠 |
| --- | --- | --- | --- | --- |
| ログイン（認可コード） | マッパーがトークンの生成時に動く | 文書 | 載せるクレームのマッパーとスコープ（2.） | slide:p03-keycloak-mappers |
| リフレッシュ | 変えた利用者属性と足したロールが、新しい AT に反映された | 実測（26.8.0） | 反映までの遅れ（AT の寿命）を鮮度の表に書く | slide:p08-refresh-reevaluation、jwt-claims-casestudy@080b8da:B11 |
| リフレッシュでの RT の入れ替わり | Revoke Refresh Token を有効にしたレルムで、RT も新しい値に替わった | 実測（26.8.0） | 9. の Revoke Refresh Token を有効にするか | slide:p08-refresh-reevaluation |
| 標準のトークン交換（Standard token exchange、V2） | サーバーの機能 `token-exchange-standard:v2` は既定で有効。交換を要求するクライアントごとにスイッチ「Standard token exchange」を有効にし、そのクライアントは機密クライアントであること | 文書 | 交換を許すクライアント（7.） | Keycloak Securing Applications（26.8.2）「Standard token exchange」 |
| 委任（act・may_act）の交換 | プレビュー（機能 `token-exchange-delegation`）。既定は無効 | 文書 | 委任を Keycloak の交換で表すか、別の発行サービスで表すか | Keycloak Securing Applications（26.8.2）「Token exchange delegation」、slide:p03-recent-changes |
| なりすまし（subject impersonation）の交換 | V2 では未実装 | 文書 | 使わない前提か | Keycloak Securing Applications（26.8.2）「Comparison of standard token exchange and legacy token exchange」 |
| 旧来のトークン交換（V1） | プレビューかつ非推奨。既定は無効 | 文書 | 使わない前提か | Keycloak Securing Applications（26.8.2）「Legacy token exchange」 |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| クレームを作る契機（発行イベント） |  |  | `claims[].issue_events`、`claims[].recompute_trigger` |
| リフレッシュで計算し直されることの前提 |  |  | `claims[].propagation_delay` |
| 使うトークン交換の版と機能 |  |  | `claims[].spec_version`、`claims[].revisit_trigger` |

根拠：slide:p03-keycloak-mappers、slide:p03-keycloak-aud-lightweight、slide:p03-recent-changes、slide:p08-refresh-reevaluation、Keycloak Securing Applications（26.8.2）「Standard token exchange」、jwt-claims-casestudy@080b8da:B11（裏付け）

<a id="mappers-scopes"></a>
## 2. プロトコルマッパーとクライアントスコープ〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_idp_keycloak#mappers-scopes`
<!-- req:p03-keycloak-mappers.R1 req:p03-keycloak-mappers.R2 req:p03-keycloak-mappers.R4 req:p03-keycloak-mappers.R5 -->

決めること：クレームごとに、どのマッパーで作り、どのクライアントスコープ（Default は常に付く、Optional は要求したときだけ付く）に入れ、どのトークンに載せるか。

| 観点 | 検討の問い | 根拠 |
| --- | --- | --- |
| マッパーの種類 | User Attribute・Hardcoded claim・Group Membership・Audience などのどれで作るか | slide:p03-keycloak-mappers |
| JSON の型 | マッパーの「Claim JSON Type」を台帳の `type` と揃えたか | slide:p03-keycloak-mappers |
| 載せるトークン | AT・ID トークン・UserInfo・イントロスペクション・軽量 AT（4.）のどれに載せるか | slide:p03-keycloak-mappers、Keycloak Server Administration Guide（26.8.2）「Using lightweight access token」 |
| スコープ | Default と Optional のどちらに入れるか。`basic` が `sub`・`auth_time` を、`profile` が `preferred_username` を連れてくるように、スコープが既定で付けるクレームを把握したか | slide:p03-keycloak-mappers、jwt-claims-casestudy@080b8da:A1（裏付け） |
| ロールの積 | 入るロールが「利用者のロール」∩「クライアントが使えるロール」であることを前提にしたか（3.） | slide:p03-keycloak-mappers |
| グループ | グループを載せるなら Group Membership マッパーを置き、フルパスで出る形を台帳の `shape`・`allowed_values` に書いたか | slide:p03-keycloak-mappers |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| クレームごとのマッパー・型・載せるトークン |  |  | `claims[].authoritative_writer`、`claims[].type`、`claims[].carried_in` |
| クライアントに付けるスコープ（Default・Optional） |  |  | `claims[].assumption` |
| グループの形 |  |  | `claims[].shape`、`claims[].allowed_values` |

根拠：slide:p03-keycloak-mappers、Keycloak Server Administration Guide（26.8.2）「Client scopes」、『実践 Keycloak』（オライリー・ジャパン 2022）4.5.2 節 pp.56–58

<a id="client-scope"></a>
## 3. ロールの絞り込み（Full Scope Allowed）〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_idp_keycloak#client-scope`
<!-- req:p03-keycloak-mappers.R3 req:p05-scope-vs-role.R2 req:p05-scope-vs-role.R3 req:p05-role-explosion.R3 -->

決めること：トークンに入るロールを、クライアントが使えるロールにどう絞るか。Full Scope Allowed がオンだと、利用者の全ロールが入ります。Keycloak 26.8.2 の文書は、このスイッチを非推奨とし、すべてのクライアントで無効にして、必要なロールのスコープの対応付けを明示するよう書いています（新規・更新のクライアントに強制するクライアントポリシーの executor「Full Scope Disabled」がある）。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| Full Scope Allowed | 全クライアントでオフにしたか。強制するか | オフ＋executor で強制／オフ（手で）／オン | Keycloak Server Administration Guide（26.8.2）「Role scope mappings」、jwt-claims-casestudy@080b8da:A8（裏付け） |
| ロールの置き場所 | 組織全体で同じ意味のロール（realm_access）と、クライアント固有の意味のロール（resource_access）を分け、台帳に区別を書いたか | レルムのロール／クライアントのロール | slide:p05-scope-vs-role |
| ロールの数 | 複数のロールを渡すならグループにまとめるか。複合ロールの性能と管理を確かめたか | グループ／複合ロール | slide:p05-role-explosion |

ケーススタディの実測（26.8.0）：Full Scope Allowed がオンのクライアントでは tenant-admin のロールが AT に漏れ、オフでは realm_access が空でした。

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| Full Scope Allowed と強制の方法 |  |  | `claims[].assumption`（roles の行） |
| ロールの名前空間（レルム・クライアント） |  |  | `claims[].namespace`、`claims[].value_vocabulary` |

根拠：Keycloak Server Administration Guide（26.8.2）「Role scope mappings」、slide:p05-scope-vs-role、slide:p05-role-explosion、slide:p03-keycloak-mappers

<a id="lightweight-at"></a>
## 4. 軽量アクセストークン〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_idp_keycloak#lightweight-at`
<!-- req:p03-keycloak-aud-lightweight.R2 -->

決めること：軽量アクセストークンを使うか。使うなら、落ちるクレームを受け手がイントロスペクションで得るか。

| 観点 | Keycloak の挙動 | 区分 | 検討の問い | 根拠 |
| --- | --- | --- | --- | --- |
| 有効にする方法 | クライアントポリシーの executor `use-lightweight-access-token` をクライアントに適用する | 文書 | 適用するクライアントはどれか | Keycloak Server Administration Guide（26.8.2）「Using lightweight access token」 |
| 載るクレーム | マッパーの「Add to lightweight access token」（既定はオフ）がオンのものだけ | 文書 | 受け手が要るクレームをオンにしたか | Keycloak Server Administration Guide（26.8.2）「Using lightweight access token」 |
| 落ちたクレーム | sub・aud・組織の名前空間・realm_access など 12 個が落ちた | 実測（26.8.0） | 必須のクレームが落ちても、受け手は拒否するか（ケーススタディの A11） | slide:p03-keycloak-aud-lightweight |
| 受け手の取得 | マッパーの「Add to token introspection」がオンなら、受け手はイントロスペクションで得る | 文書 | 受け手がイントロスペクションを呼ぶか（10.） | Keycloak Server Administration Guide（26.8.2）「Using lightweight access token」 |
| UserInfo | 軽量 AT は既定で UserInfo に拒否される | 文書 | UserInfo を使う受け手がいるか | Keycloak Server Administration Guide（26.8.2）「Using lightweight access token」 |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 軽量 AT を使うか |  |  | `catalog:issue_events#I03` への回答 |
| 落ちるクレームの受け手の取得方法 |  |  | `token_types[].required_claims`、`token_types[].revocation` |

根拠：Keycloak Server Administration Guide（26.8.2）「Using lightweight access token」、slide:p03-keycloak-aud-lightweight、jwt-claims-casestudy@080b8da:A11（裏付け）

<a id="immutable-claims"></a>
## 5. 外せないクレーム〔Lite・Full：記入（台帳の既定どおりの行）〕

項目 ID：`template:modules/M_idp_keycloak#immutable-claims`

決めること：Keycloak が外せないクレームを、台帳の「既定どおり」の行として載せるか（載せない選択はできないので、受け手が読まないなら `consumers: []`）。

| クレーム | Keycloak の挙動 | 区分 | 台帳での扱いの問い | 根拠 |
| --- | --- | --- | --- | --- |
| exp・iat・jti・iss・typ・azp・sid・scope・cnf | 軽量 AT からも外せない（プロトコルマッパーで消せない） | 文書 | 受け手が読むか（`consumers`）。読まないなら既定どおり・`consumers: []` | Keycloak Server Administration Guide（26.8.2）「Using lightweight access token」 |
| sub・auth_time | `basic` のスコープが一緒に出す。外すには sub だけの独自のスコープが要る | 実測（26.8.0、シナリオ A） | ケーススタディの判定と違うなら `casestudy-deviations.yaml` に書く | templates/casestudy-deviations.yaml の CLM-0228 |
| client_id | 認可コードで発行した AT に出なかった（azp で読む） | 実測（26.8.0、シナリオ A） | 呼び出し元のクライアントを何で確かめるか | templates/casestudy-deviations.yaml の CLM-0405 |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 外せないクレームの台帳の行と受け手 |  |  | `claims[].decision: 既定どおり`、`claims[].consumers` |

根拠：Keycloak Server Administration Guide（26.8.2）「Using lightweight access token」、templates/casestudy-deviations.yaml の CLM-0198、templates/examples/scenario-a/claims.yaml の C-typ-claim

<a id="catalog-defaults"></a>
## 6. カタログの既定の回答（設定のスイッチと引き継ぎの印）〔Lite・Full：記入〕

項目 ID：`template:modules/M_idp_keycloak#catalog-defaults`

決めること：カタログ（`templates/catalog/issue_events.yaml`・`use_events.yaml`）の Keycloak の行ごとに、そのイベントを止めるクライアント・レルムの設定と、既定の回答の候補。**正はカタログの YAML**（`idp.keycloak` の `stop_setting`・`lite_inherit`・`hook_invoked`）で、この表はその読み物です。食い違えばカタログを正とし、この表を直します。

Lite での扱い（`research/template-design/gate1.md` の 10.、`tools/claim_lint/RULES.md` の「Lite の既定の回答の引き継ぎ」）：

- **引き継げる**：カタログで `lite_inherit: true` の行（I03・I04・I05・I07）。クライアント（I03 はクライアントポリシー）のスイッチ 1 つで止めていて、指摘が出ていないイベント。回答は「対象外」＋`inherit: idp-default`＋`setting_checked`（どの設定を、どこで、いつ確かめたか。1 欄）
- **手で書く**：指摘が出た行（I06・I09・U07・U10 など）、レルム・クライアントの既定に依存する行（I08）、利用イベント（U01〜）、`stop_setting` の無い行。回答に `assumption`（起きない前提）と `breaks_when`（崩れる条件）を書く

スイッチで止められる発行イベント：

| イベント | 止める設定 | 範囲 | 既定（区分） | Lite | 手で書く理由 |
| --- | --- | --- | --- | --- | --- |
| I01 認可コード＋PKCE | Capability config > Standard Flow | client | 文書に記載なし（ソースの要約：管理画面の新規作成で ON） | 手で書く | 使う前提のイベント（「該当」で答える） |
| I03 軽量アクセストークン | クライアントポリシーの executor `use-lightweight-access-token` を適用しない | realm | 適用しなければ起きない（文書：executor を適用したクライアントだけ軽量 AT を受ける） | 引き継げる | — |
| I04 ROPC など | Capability config > Direct Access Grants | client | 文書に記載なし（ソースの要約：管理画面の新規作成で OFF、REST で省くと ON） | 引き継げる | — |
| I05 Client Credentials | Capability config > Service account roles | client | 文書に記載なし（ソースの要約：OFF） | 引き継げる | — |
| I06 トークン交換 | Capability config > Standard Token Exchange（要求元のクライアント） | client | クライアントのスイッチの既定は文書に記載なし（ソースの要約：OFF）。サーバーの機能 `token-exchange-standard:v2` は既定で有効（文書） | 手で書く | 指摘が出た行（U10 と対） |
| I07 Device Authorization Grant | Capability config > OAuth 2.0 Device Authorization Grant | client | 文書に記載なし（ソースの要約：OFF） | 引き継げる | — |
| I08 オフラインアクセス | クライアントの Client scopes から offline_access を外す | client | 新しいクライアントに Optional として付く（文書）。offline_access のロールが既定のロールに含まれる（ソースの要約） | 手で書く | レルム・クライアントの既定に依存する |
| I09 Back-Channel Logout | Logout settings > Backchannel logout URL を空にする | client | 空（推論） | 手で書く | 指摘が出た行 |
| I10 implicit・hybrid | Capability config > Implicit Flow | client | 文書に記載なし（ソースの要約：OFF） | 手で書く | `lite_inherit` の印がない |
| I13 CIBA | Capability config > OIDC CIBA Grant | client | 文書に記載なし（ソースの要約：OFF） | 手で書く | `lite_inherit` の印がない |
| I15 JWT のアサーショングラント | Capability config > JWT Authorization Grant | client | 文書に記載なし（ソースの要約：OFF） | 手で書く | `lite_inherit` の印がない |
| I16 ID-JAG | 機能 identity-assertion-jwt を有効にしない | server | experimental（既定は確かめていない） | 手で書く | サーバーの機能で、クライアントのスイッチでない |
| I19 管理者の代理操作 | realm-management の impersonation ロールを誰にも与えない | realm | 確かめていない | 手で書く | レルムの設定 |
| I24 テナント・組織の切り替え | クライアントの Client scopes から organization を外す | client | 組み込みの Optional（文書） | 手で書く | `lite_inherit` の印がない |
| I34 OID4VCI | 機能 oid4vc-vci を有効にしない | server | Preview で既定は無効（文書） | 手で書く | サーバーの機能 |

`stop_setting` の無い発行イベント（I02・I11・I12・I14・I17・I18・I20〜I23・I25〜I33）と、すべての利用イベント（U01〜U28）は、手で書きます。「既定」の列の出どころは各行の `idp.keycloak.stop_setting.default` で、「ソースの要約」は `research/template-design/unverified.md` の V31 です。

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 引き継ぐ行と、確かめた設定（setting_checked） |  |  | `catalog_answers.yaml` の `answers[].setting_checked` |
| 既定から変えた行と理由 |  |  | `catalog_answers.yaml` の `answers[]` |

根拠：templates/catalog/issue_events.yaml の I03、templates/catalog/issue_events.yaml の I08、tools/claim_lint/RULES.md の「Lite の既定の回答の引き継ぎ」、research/template-design/gate1.md の 10.、research/template-design/unverified.md の V31、Keycloak Server Administration Guide（26.8.2）「Offline access」、Keycloak Securing Applications（26.8.2）「Standard token exchange」

<a id="audience-mapper"></a>
## 7. aud の設定（Audience マッパー）〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_idp_keycloak#audience-mapper`
<!-- req:p03-keycloak-aud-lightweight.R1 -->

決めること：API を aud に入れる方法。Keycloak は自動では API を aud に入れず、既定で入る `account` は API 固有の値ではありません（slide:p03-keycloak-aud-lightweight）。

| 候補 | 検討の問い | 根拠 |
| --- | --- | --- |
| Audience マッパーをクライアントスコープに置く | どのスコープを要求したときに、どの API を aud に入れるか | Keycloak Server Administration Guide（26.8.2）「Audience support」 |
| Audience Resolve（クライアントロールを持つクライアントを aud に足す） | クライアントロールの割り当てが aud を決めてよいか | slide:p03-keycloak-aud-lightweight |
| 受け手の確かめ | API が aud に自分が含まれるかを確かめ、`account` だけのトークンを拒否するか | slide:p03-keycloak-aud-lightweight、template:modules/M_token_validation#audience |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| aud を入れる方法とスコープ |  |  | `token_types[].aud`、`claims[]`（aud の行の `authoritative_writer`） |

根拠：Keycloak Server Administration Guide（26.8.2）「Audience support」、slide:p03-keycloak-aud-lightweight

<a id="token-exchange-downscope"></a>
## 8. トークン交換の絞り込み〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_idp_keycloak#token-exchange-downscope`
<!-- req:p06-narrow-downstream.R4 req:p10-token-exchange-not-narrowing.R2 req:p10-token-exchange-not-narrowing.R3 req:p10-token-exchange-not-narrowing.R5 -->

決めること：標準のトークン交換で、得られる宛先とスコープをどう限るか。交換は絞るとは限りません：`scope` は要求元のクライアントの Optional のスコープを足せる（広げうる）一方、`audience` は aud とクライアントロールを絞るだけで足しません（文書）。ケーススタディの実測（26.8.0）では、Optional のスコープ `aud-orders` を求めると、元のトークンに無い orders 宛てのトークンが 200 で出ました。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 交換を許すクライアント | 「Standard token exchange」のスイッチを有効にするクライアントは最小か | クライアントの一覧 | Keycloak Securing Applications（26.8.2）「Standard token exchange」 |
| 割り当てるスコープ | 交換するクライアントに Optional で割り当てた宛先・スコープは最小か | クライアントごとの一覧 | slide:p10-token-exchange-not-narrowing |
| 絞り込みだけに限る | クライアントポリシーの executor `downscope-assertion-grant-enforcer` を適用するか（適用すると、subject_token に無いスコープは拒否される。include in token scope が false の既定のスコープは例外） | 適用する／適用しない | Keycloak Server Administration Guide（26.8.2）「Downscoping」 |
| act | 交換で出たトークンに act が付くか。委任を表すならプレビューの委任の機能を使うか | 付けない／プレビューの機能／別の発行サービス | slide:p10-token-exchange-not-narrowing、Keycloak Securing Applications（26.8.2）「Standard token exchange」 |
| 下流ほど絞る | 交換のホップで aud・scope・寿命が上流を超えないことを、交換のサービスか受け手で確かめるか | ホップの表と L16（#6） | slide:p06-narrow-downstream |

ケーススタディの実測（26.8.0）：標準の交換で出たトークンに act はありませんでした。

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 交換を許すクライアントと割り当てるスコープ |  |  | `hops[].exchanger`、`hops[].scope` |
| downscope の executor |  |  | `hops[].narrowing_exception` |
| act の扱い |  |  | `claims[]`（act の行）、`catalog:issue_events#I06` への回答 |

根拠：Keycloak Server Administration Guide（26.8.2）「Downscoping」、Keycloak Securing Applications（26.8.2）「Standard token exchange」、slide:p10-token-exchange-not-narrowing、slide:p06-narrow-downstream、RFC 8693 §5

<a id="refresh-token-settings"></a>
## 9. リフレッシュトークンの設定〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_idp_keycloak#refresh-token-settings`
<!-- req:p08-refresh-reevaluation.R3 req:p08-rotation.R5 -->

決めること：RT のローテーションと、交換で出した RT の期限。

| 観点 | Keycloak の挙動 | 区分 | 検討の問い | 根拠 |
| --- | --- | --- | --- | --- |
| Revoke Refresh Token（レルムの Tokens タブ） | 有効にすると、リフレッシュで RT を失効させ、新しい RT を出す。オフラインのトークンも 1 回限りになる | 文書 | 公開クライアントで有効にするか（RFC 9700 §4.14.2） | Keycloak Server Administration Guide（26.8.2）「Offline access」、RFC 9700 §4.14.2 |
| Revoke Refresh Token の既定 | 無効 | ガイドのスライド（文書のこの節に既定の記載は見つからなかった。ソースの要約も false） | 既定のまま使っていないか | slide:p08-rotation |
| 古い RT の再利用での系列の失効（再利用の検知） | 確かめていない | — | 再利用の検知を前提にしないか | slide:p08-rotation |
| 交換で出す RT | 要求元が refresh_token を求め、クライアントの「Allow refresh token in Standard Token Exchange」が No（既定）でないときだけ出る。AT・ID トークンは subject token の exp を超えない（既定。互換のスイッチ「Allow exchange token expiration after subject token expiration」を有効にすると上限が外れる）が、RT はセッションが続く限り元の期限を超えうる（文書の警告） | 文書 | 交換で RT を出すか | Keycloak Securing Applications（26.8.2）「Standard token exchange」 |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| Revoke Refresh Token |  |  | `token_types[].rt_rotation`、`issuance_profile.rt_strategy` |
| 交換で RT を出すか |  |  | `token_types[]`（RT の行の `max_lifetime`） |

根拠：Keycloak Server Administration Guide（26.8.2）「Offline access」、Keycloak Securing Applications（26.8.2）「Standard token exchange」、slide:p08-rotation、slide:p08-refresh-reevaluation、RFC 9700 §4.14.2

<a id="introspection"></a>
## 10. イントロスペクション〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_idp_keycloak#introspection`
<!-- req:p08-revocation-propagation.R5 -->

決めること：受け手がイントロスペクションで有効性を問い合わせるとき、どの資格情報で問い合わせるか。Keycloak は、問い合わせたクライアントがトークンの aud に含まれるときだけ active を返します（AT。互換のための設定「Allow token introspection without audience check」で外せる）。RT・オフラインのトークンは、発行を受けたクライアント（azp）だけが問い合わせられます。

| 観点 | 検討の問い | 根拠 |
| --- | --- | --- |
| 問い合わせの資格情報 | 宛先のサービス自身のクライアントの資格情報で問い合わせるか | Keycloak Server Administration Guide（26.8.2）「Token introspection audience validation」、slide:p08-revocation-propagation |
| 互換の設定 | aud の確認を外す設定を使っていないか | Keycloak Server Administration Guide（26.8.2）「Token introspection audience validation」 |
| 反映の速さ | ログアウトの後、問い合わせる受け手はすぐ止まるが、手元で検証する JWT は期限まで通る（実測 26.8.0：初回の問い合わせで active=false、JWT は残り 299 秒以上） | slide:p08-revocation-propagation |
| キャッシュ | 応答のキャッシュは応答の exp を超えないか | RFC 7662 §4 |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 問い合わせる受け手と資格情報 |  |  | `hops[].validates`（mode） |
| キャッシュの秒数 |  |  | `token_types[].introspection_cache_ttl` |

根拠：Keycloak Server Administration Guide（26.8.2）「Token introspection audience validation」、slide:p08-revocation-propagation、RFC 7662 §4

<a id="limits"></a>
## 11. 上限と、黙った欠落〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_idp_keycloak#limits`
<!-- req:p03-custom-claim-injection.R2 req:p04-size-budget.R5 req:p06-issuance-hook.R5 -->

決めること：Keycloak でクレームが黙って欠ける場面と、サイズの上限・超えたときの挙動。

| 場面 | Keycloak の挙動 | 区分 | 受け手の側で決めること | 根拠 |
| --- | --- | --- | --- | --- |
| マッパーが無い・スコープが付かない | クレームが無いままトークンが出る（誤りにならない） | 文書・実測 | 必須のクレームが無ければ拒否する（`on_missing`） | slide:p03-keycloak-mappers、slide:p03-custom-claim-injection |
| 軽量 AT | マッパーで「Add to lightweight access token」をオンにしたもの以外は落ちる（4.） | 文書・実測（26.8.0） | 同上 | Keycloak Server Administration Guide（26.8.2）「Using lightweight access token」 |
| 定義していない利用者属性 | 既定（unmanaged attributes が無効）では保存されなかった。有効にすると保存された | 実測（26.8.0） | 属性の書き手（管理者か本人か）を台帳に書く | jwt-claims-casestudy@080b8da:B18（裏付け） |
| トークンの大きさ | Keycloak の側の上限は文書で見つけていない。グループ 200 個で全量の AT は 8609 バイトになった（実測 26.8.0）。超過は経路の上限（nginx の 8 KiB のヘッダーなど）で 400 などになる | 実測（26.8.0） | R8 の計算と経路の上限（`tools/claim_lint/path_limits.yaml`） | slide:p04-size-budget、slide:p03-keycloak-aud-lightweight |
| マッパーの失敗 | マッパーはトークンの生成の中で動く（外部の呼び出しのフックではない）。自作の SPI のマッパーの失敗時の挙動は確かめていない | 文書（マッパー）・未確認（SPI） | SPI を使うなら失敗の試験を書く | slide:p03-custom-claim-injection |

大小の扱い（属性名・値の大文字小文字）で値が黙って欠けるかは、Keycloak については確かめていません（slide:p04-case-and-characters の表に Keycloak の行はない）。使う前に、自組織の環境で確かめて 12.（書き手が自信のない点）に書きます。

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| クレームが欠けたときの受け手の挙動 |  |  | `claims[].on_missing`、`token_types[].required_claims` |
| サイズの最悪と経路の上限 |  |  | `token_types[].size`、`claims[].max_bytes` |
| 大小の扱いを確かめた結果 |  |  | `template:00_core#uncertain` |

根拠：slide:p03-keycloak-mappers、slide:p03-custom-claim-injection、slide:p04-size-budget、slide:p06-issuance-hook、Keycloak Server Administration Guide（26.8.2）「Using lightweight access token」、jwt-claims-casestudy@080b8da:B18（裏付け）

<a id="token-preview"></a>
## 12. 発行前の確かめ（Evaluate）〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_idp_keycloak#token-preview`
<!-- req:p11-schema-contract-tests.R3 req:p11-change-procedure.R4 -->

決めること：新しい形式や設定の変更を、発行の前に実際のトークンで確かめる手段。Keycloak では、クライアントの Client scopes タブの「Evaluate」で、選んだ利用者・スコープでの AT・ID トークン・UserInfo の例を作れます（audience パラメータはトークン交換でだけ使える）。

| 手段 | 検討の問い | 根拠 |
| --- | --- | --- |
| Evaluate | 変更のたびに、代表の利用者で AT を作り、台帳の Schema（`schemas/*.issuer.schema.json`）で確かめるか | Keycloak Server Administration Guide（26.8.2）「Evaluating Client Scopes」、slide:p11-schema-contract-tests |
| CI での発行 | 検証用のレルムで実際に発行し、発行側の Schema で検証するか | tools/claim_lint/RENDER.md の 4.、slide:p11-schema-contract-tests |
| 受け手の条件の試験 | 受け手の拒否の条件（欠落・型・宛先）を試験で確かめるか | slide:p11-change-procedure |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 発行前に確かめる手段 |  |  | `template:00_core#definition-lifecycle` |
| 確かめる利用者・スコープ |  |  |  |

根拠：Keycloak Server Administration Guide（26.8.2）「Evaluating Client Scopes」、slide:p11-schema-contract-tests、slide:p11-change-procedure

<a id="broker-mapping"></a>
## 13. 外部の IdP の取り込み（ブローカー）〔Full だけ〕

項目 ID：`template:modules/M_idp_keycloak#broker-mapping`
<!-- req:p02-saml-attributes.R5 -->

決めること：外部の IdP（SAML・OIDC）をブローカーでつなぐとき、外部の属性を社内の名前のクレームにする写し方。Keycloak では、IdP マッパーで外部の属性を利用者の属性・ロールに取り込み、プロトコルマッパーで社内の名前のクレームにする 2 段になります。

| 段 | 検討の問い | 根拠 |
| --- | --- | --- |
| IdP マッパー（取り込み） | どの属性を、利用者の属性・ロールのどれに取り込むか。取り込むのは初回だけか毎回か（Sync Mode。既定はソースの要約で import、V31） | slide:p02-saml-attributes、research/template-design/unverified.md の V31 |
| プロトコルマッパー（社内の名前） | 取り込んだ属性を、組織の名前空間のどのクレームにするか | slide:p02-saml-attributes |
| 識別子 | メール形式の NameID を sub にしていないか。SAML の subject-id の大小を無視する比べ方と、sub の比べ方の違いを扱ったか | slide:p02-saml-attributes |
| 鮮度 | 取り込みの方式（初回だけか毎回か）を、値の鮮度として書いたか | slide:p08-reissue-triggers |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 取り込む属性と写す先のクレーム |  |  | `claims[].upstream_issuer` |
| 取り込みの方式 |  |  | `claims[].recompute_trigger`、`claims[].volatility` |

根拠：slide:p02-saml-attributes、slide:p08-reissue-triggers、『実践 Keycloak』（オライリー・ジャパン 2022）10.3 節 pp.198–199、research/template-design/unverified.md の V31
