<!-- template_version: 0.3.0 -->
# データ層（modules/M_data_layer）

> テンプレートです。候補と検討の問いだけを載せ、採否の理由の見本は載せません（理由の写し書きを防ぐため。#4 の方針）。判断は台帳（claims.yaml など）に 1 回だけ書き、ここからは ID で参照します。

- 使う場面：トークンのクレームが DB・データ基盤・メッセージブローカーに届く境界（ガイドの Part 7）。DB の文脈の注入、DB のトークン認証、クラウドの一時認証情報
- 組み合わせ：`template:modules/M_multitenancy#data-layer-filter`（テナントの絞り込み）、`template:00_core#lifecycle-db-connection`（ライフサイクル表の「DB・ブローカーの接続」の層）、`template:modules/M_token_validation#issuer`（DB・ブローカーがトークンを検証するとき）
- 台帳の列：ホップの `kind: db_connection`・`broker_connection` と `connection_max_lifetime`、台帳の `integrity_until`（place：db_session）・`enforced_at`（DB の行）（`templates/registry/README.md` の 3.）
- Lite での扱い：〔Full：記入／Lite：参照〕。Lite では、DB の文脈を誰が設定するかを `template:00_core#scope-boundary` の図に書き、接続の寿命を `template:00_core#lifecycle` に書きます
- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施。
- 製品の挙動の確かめ：PostgreSQL 16 の文書、SQL Server の文書、Kafka 4.4 の文書を 2026-11-23 に確かめました。それ以外の製品の挙動はガイドのスライドによります

<a id="db-context-setter"></a>
## 1. DB の文脈を設定する主体と、経路の選択〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_data_layer#db-context-setter`
<!-- req:p07-three-db-paths.R1 req:p07-three-db-paths.R2 req:p07-row-level-security.R4 req:p07-data-layer-checklist.R1 -->

決めること：トークンのクレームがデータ層に届く経路と、「DB の文脈を設定するのは誰か」。経路を選ぶ前に、設定する主体を図に書き、その主体以外が書ける経路を残さないようにします（slide:p07-three-db-paths）。

| 経路 | DB が信じるもの | 検討の問い | 崩れる条件 | 根拠 |
| --- | --- | --- | --- | --- |
| A 注入する（入口・アプリが検証し、DB のセッションの設定に書く。PostgREST・アプリの set_config・SESSION_CONTEXT） | 注入した者 | 注入者以外が同じ接続で任意の SQL を流せないか | 任意の SQL での上書き、接続プールでの漏れ（3.） | slide:p07-three-db-paths、slide:p07-trust-boundary |
| B DB が検証する（DB がトークンを受け、自分の主体に対応付ける） | 発行者と対応付けの規則 | 発行者・aud・JWKS を DB 側で設定できるか（4.） | トークンの寿命と接続の寿命のずれ | slide:p07-three-db-paths、slide:p07-db-token-auth |
| C STS が変換する（クラウドの STS がクレームを一時認証情報の属性に替える） | 信頼ポリシーと属性の対応 | 属性の元を利用者が編集できないか（6.） | 利用者が編集できる属性からタグを作る | slide:p07-three-db-paths、slide:p07-cloud-attributes |

製品ごとに、クレームの届き方と、行の権限を評価する者を書きます。

| 製品の例 | クレームの届き方 | 評価する者 | 根拠 |
| --- | --- | --- | --- |
| PostgreSQL の RLS＋PostgREST | `request.jwt.claims`（取引単位）。role で SET LOCAL ROLE | DB のポリシー | slide:p07-row-level-security |
| Supabase | `auth.uid()`・`auth.jwt()`（user_metadata は本人が書ける） | DB のポリシー | slide:p07-row-level-security |
| Hasura | `x-hasura-*` のセッション変数 | Hasura のエンジン | slide:p07-row-level-security |
| SQL Server・Azure SQL | SESSION_CONTEXT（アプリ・Data API builder が設定） | DB のセキュリティポリシー | slide:p07-row-level-security |
| Snowflake・BigQuery | セッションのロール・IAM の主体 | row access policy | slide:p07-row-level-security |

DB の権限（ロール）を選ぶクレーム（PostgREST の role、Hasura の x-hasura-allowed-roles、Snowflake の session:role:*）は、最も権限の高いクレームとして扱い、書ける発行元を限ります（slide:p07-trust-boundary）。

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 経路（A・B・C） |  |  | `hops[].kind: db_connection` |
| DB の文脈を設定する主体（図に書く） |  |  | `claims[].integrity_until`（place：db_session、trust_boundary） |
| 使う製品と、行の権限を評価する者 |  |  | `claims[].enforced_at` |
| DB の権限を選ぶクレームの発行元 |  |  | `claims[].authoritative_writer` |

根拠：slide:p07-three-db-paths、slide:p07-row-level-security、slide:p07-trust-boundary、slide:p07-data-layer-checklist、NIST SP 800-162 §3.1.3.3

<a id="pool-context"></a>
## 2. 接続プールでの文脈の設定単位〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_data_layer#pool-context`
<!-- req:p07-trust-boundary.R3 req:p07-connection-pool.R1 req:p07-connection-pool.R3 req:p07-lifetime-mismatch.R2 req:p07-data-layer-checklist.R3 -->

決めること：利用者のクレームから作る DB の文脈を、どの単位で設定するか。セッション単位の設定は、接続プールで次の要求に引き継がれます（slide:p07-connection-pool）。利用者のクレームは接続ではなく取引ごとに注入します。

| 環境 | 設定の単位の候補 | 検討の問い | 根拠 |
| --- | --- | --- | --- |
| PostgreSQL | `SET LOCAL`、または `set_config(名前, 値, true)`（第 3 引数 true で、その取引の間だけ有効。false ならセッションの終わりまで残る） | 取引（BEGIN〜COMMIT）の中で設定しているか | PostgreSQL 16 文書 §9.27.1「Configuration Settings Functions」、slide:p07-connection-pool |
| PostgreSQL の読み取り | `current_setting(名前, true)`（第 2 引数 true で、未設定なら誤りではなく NULL） | 未設定を「全件」と読まない述語か | PostgreSQL 16 文書 §9.27.1「Configuration Settings Functions」 |
| PostgREST | 取引単位。コミットの後は値が空文字になる | 空文字を「文脈なし」として扱い、全件を許さないか | slide:p07-connection-pool |
| PgBouncer（transaction pooling） | SET・RESET は使えない | 取引単位の設定だけで済むか | slide:p07-connection-pool |
| SQL Server | `sp_set_session_context` の `@read_only = 1`（同じ論理接続ではそのキーを変えられなくなる。既定は 0） | 述語で接続している DB の主体も確かめるか | SQL Server 文書「sp_set_session_context (Transact-SQL)」（2025-06-23 更新）、slide:p07-trust-boundary |
| ロールの切り替え | サーバー側の `SET LOCAL ROLE` | クライアントに任意の SQL を流させないか（同じ取引で RESET ROLE で戻せる） | slide:p07-trust-boundary |

値は文字列の連結でなくパラメータで渡します（slide:p07-connection-pool）。

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 文脈の設定の単位と方法 |  |  | `claims[].integrity_until`、`hops[].validates` |
| 文脈が無い・空のときの挙動 |  |  | `claims[].on_missing`、`claims[].enforced_at` |
| 文脈が残らないことの試験 |  |  | `catalog:use_events#U02` への回答 |

根拠：PostgreSQL 16 文書 §9.27.1「Configuration Settings Functions」、SQL Server 文書「sp_set_session_context (Transact-SQL)」（2025-06-23 更新）、slide:p07-connection-pool、slide:p07-trust-boundary、slide:p07-lifetime-mismatch、jwt-claims-casestudy@080b8da:A7（裏付け）

<a id="db-identity"></a>
## 3. 誰として DB に接続するか〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_data_layer#db-identity`
<!-- req:p06-flow-browser-to-db.R4 req:p07-db-token-auth.R1 req:p07-db-token-auth.R2 req:p07-db-token-auth.R3 req:p07-connect-as-whom.R1 req:p07-connect-as-whom.R2 req:p07-data-layer-checklist.R7 req:p07-data-layer-checklist.R9 -->

決めること：DB に利用者の ID で接続するか、サービスの ID で接続して文脈を注入するか、サービスの ID で接続してアプリだけで認可するか。DB に利用者の AT をそのまま渡すかも、ここで決めます（slide:p06-flow-browser-to-db は渡さない形を示す）。

| 型 | DB が知る主体 | DB の監査ログ | プールの効率 | 主な危険 | 根拠 |
| --- | --- | --- | --- | --- | --- |
| 利用者の ID を伝える（OBO・DB のトークン認証） | 利用者 | 利用者 | 低い（利用者ごとのプール） | 寿命のずれ、接続数の増加 | slide:p07-connect-as-whom |
| サービスの ID＋文脈の注入 | サービスと注入した属性 | サービス（注入値を別に記録しない限り） | 高い（取引単位の注入が前提） | 文脈の漏れ・偽装 | slide:p07-connect-as-whom |
| サービスの ID＋アプリで認可 | サービスだけ | サービスだけ | 高い | アプリの不具合がそのまま越境 | slide:p07-connect-as-whom |

DB・ブローカーがトークンを検証する（経路 B）ときに確かめること：

| 観点 | 検討の問い | 根拠 |
| --- | --- | --- |
| 対応付けのキー | DB の主体との対応付けを、名前やメールではなく不変の ID で行うか（同じ名前で作り直すと別人になる製品がある） | slide:p07-db-token-auth、slide:p07-data-layer-checklist |
| 組織の独自クレーム | 製品の「クレームの位置」の設定（Kafka の sub.claim.name など）で対応付けるか | slide:p07-db-token-auth |
| 検証の設定 | 発行者・aud・JWKS を設定したか。署名を確かめない既定の実装（Kafka の OAUTHBEARER の unsecured の実装）を本番で使っていないか | slide:p07-db-token-auth、template:modules/M_token_validation#issuer |
| 利用者単位の監査 | 利用者単位の DB の監査が要るか。要るなら ID を DB まで伝え、接続数とプールの効率への影響を書く | slide:p07-connect-as-whom |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 接続の型 |  |  | `hops[]`（db_connection のホップ） |
| DB の主体との対応付けのキー |  |  | `claims[].identifier_properties` |
| DB・ブローカーでの検証の設定 |  |  | `token_types[].issuers`・`alg_allowlist` |
| 利用者単位の監査の要否と影響 |  |  | `template:modules/M_privacy_minimization#audit-log` |

根拠：slide:p07-connect-as-whom、slide:p07-db-token-auth、slide:p06-flow-browser-to-db、slide:p07-data-layer-checklist、NIST IR 8587 §5.3.1.6

<a id="masking-rls-bypass"></a>
## 4. マスキングと RLS をすり抜ける主体〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_data_layer#masking-rls-bypass`
<!-- req:p07-row-level-security.R3 req:p07-masking.R3 req:p07-data-layer-checklist.R6 -->

決めること：行単位の制御とマスキングの外にいる主体の一覧と、それを通常の経路から外す方法。

| 主体 | 何をすり抜けるか | 検討の問い | 根拠 |
| --- | --- | --- | --- |
| PostgreSQL のスーパーユーザー・BYPASSRLS の属性を持つロール | 行のセキュリティを常にすり抜ける | アプリの接続にこの属性を持つロールを使っていないか | PostgreSQL 16 文書 §5.8「Row Security Policies」 |
| PostgreSQL のテーブルの所有者 | 既定ではすり抜ける。`ALTER TABLE … FORCE ROW LEVEL SECURITY` で対象になる | アプリの接続がテーブルの所有者か。FORCE を付けたか | PostgreSQL 16 文書 §5.8「Row Security Policies」 |
| ポリシーが無いテーブル | RLS を有効にしてポリシーが無ければ既定で拒否（行が見えない） | 拒否を全件許可の設定で回避していないか | PostgreSQL 16 文書 §5.8「Row Security Policies」 |
| スーパーユーザーが作ったビュー・Supabase の secret key | 行の制御をすり抜ける | 通常の経路から使えないか | slide:p07-row-level-security |
| SQL Server の CONTROL を持つ管理者（動的データマスキング） | 常に平文を見られる。UNMASK の権限も平文を見せる | 平文を見られる主体を一覧にしたか | slide:p07-masking |
| マスキングを解くロールを選ぶクレーム（Snowflake の session:role:* など） | IdP の scope の発行が、事実上の平文の閲覧権になる | そのクレームを発行できる主体を限ったか | slide:p07-masking |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| すり抜ける主体の一覧 |  |  |  |
| 通常の経路から外す方法 |  |  | `claims[].enforced_at` |
| 平文を見られる主体の一覧 |  |  |  |

根拠：PostgreSQL 16 文書 §5.8「Row Security Policies」、slide:p07-row-level-security、slide:p07-masking、slide:p07-data-layer-checklist

<a id="connection-lifetime"></a>
## 5. 接続の寿命とトークンの寿命〔Lite・Full：記入（00_core に書く）〕

項目 ID：`template:modules/M_data_layer#connection-lifetime`

決めること：DB・ブローカーの接続が、トークンよりどれだけ長く生きるか。多くの DB でトークンは「接続を開く鍵」で、失効やロールの剥奪は開いた接続に届きません。答えは `template:00_core#lifecycle-db-connection`（ライフサイクル表の「DB・ブローカーの接続」の層）とホップの `connection_max_lifetime` に書きます。

| 候補 | 検討の問い | 根拠 |
| --- | --- | --- |
| プールの接続の最大寿命をトークンの寿命以下にする | プールの設定で接続の最大寿命を決められるか | slide:p07-lifetime-mismatch |
| 利用者のクレームは取引ごとに注入する（2.） | 接続に利用者の権限を結びつけていないか | slide:p07-lifetime-mismatch |
| 既存の接続に再認証を強制する（Kafka の `connections.max.reauth.ms`。既定は 0 で無効。正の値にすると、その間に再認証しない接続をブローカーが切る） | ブローカーが再認証を強制できる製品か | Kafka 4.4 Broker Configs「connections.max.reauth.ms」、slide:p07-lifetime-mismatch |
| すぐに止めるときは DB 側の主体を削除する | 剥奪をすぐに効かせる操作があるか | slide:p07-lifetime-mismatch |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 接続の最大寿命 |  |  | `hops[].connection_max_lifetime` |
| 剥奪を既存の接続に届ける手段 |  |  | `template:00_core#lifecycle-db-connection` |

根拠：slide:p07-lifetime-mismatch、Kafka 4.4 Broker Configs「connections.max.reauth.ms」、NIST IR 8587 §4.1.4

<a id="cloud-credentials"></a>
## 6. クラウドの一時認証情報〔Full だけ〕

項目 ID：`template:modules/M_data_layer#cloud-credentials`
<!-- req:p07-connect-as-whom.R4 req:p07-cloud-attributes.R2 -->

決めること：クラウドのストレージ・データ基盤の資格情報を、トークンからどう作るか。クレームは一時認証情報の属性に変換されてから使われ、トークンにあってもポリシーで効くとは限りません（slide:p07-cloud-attributes）。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 経路の集約 | トークンからテナントに限った一時認証情報を返す部品（Token Vending Machine など）に経路を集めるか | 1 つの部品に集める／サービスごとに AssumeRole する | slide:p07-connect-as-whom |
| 属性の元 | セッションタグ・属性の元が、利用者の編集できる属性になっていないか | ディレクトリの管理者が設定する属性だけ | slide:p07-cloud-attributes |
| ポリシーで効くか | 使う先のポリシーが、クレームではなくディレクトリの属性を見るか（Azure Storage の ABAC など） | 同じ値をディレクトリの属性として持つ | slide:p07-cloud-attributes |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 一時認証情報を作る部品 |  |  | `catalog:use_events#U24` への回答 |
| 属性の元と書ける者 |  |  | `claims[].authoritative_writer` |
| ポリシーで効くことの確かめ方 |  |  |  |

根拠：slide:p07-connect-as-whom、slide:p07-cloud-attributes、OWASP Workload Identity Federation Cheat Sheet
