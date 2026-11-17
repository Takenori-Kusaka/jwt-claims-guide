# 07. データ層: トークンのクレームはデータアクセス認可・DB 認証にどう届くか

- 調査日: 2026-11-17
- 方針: 各製品の公式ドキュメント、PostgreSQL 公式ドキュメント、ベンダーのセキュリティガイダンス・公式ブログを取得・読了して記載。取得したページで確認できなかった点は **[未検証]** と明記。「→」で始まる行は、出典の事実から筆者が導いた **推論** であり、出典の記述ではない。
- 主な参照版: PostgreSQL 18 (`docs/current`), PostgREST 16 (`stable`), Hasura v2.x, Microsoft Learn（Azure SQL Entra 概要 2026-10-07 版、SQL RLS 2026-07-20 更新、DDM 2026-11-04 更新）, Apache Kafka 4.3 ドキュメント, Snowflake / BigQuery / Databricks / MongoDB Atlas は 2026-11 時点の公開版。
- 凡例: AT = access token, RLS = row-level security, DLS = document-level security, CLS = column-level security, DDM = dynamic data masking, OBO = On-Behalf-Of, TVM = token vending machine

---

## 0. 結論（スライド用サマリ）

1. **クレームがデータ層に届く経路は 3 つ**ある。(A) **ゲートウェイ／ミドルウェアが検証済みクレームを DB セッションに注入する**（PostgREST・Supabase・Hasura・Data API builder・アプリ自身による `SET`/`sp_set_session_context`）。(B) **DB／データ基盤がトークンを直接検証し、クレームを自前のプリンシパル・ロールに対応付ける**（Azure SQL/PostgreSQL の Entra 認証、Snowflake External OAuth、MongoDB OIDC、Kafka OAUTHBEARER、Elasticsearch JWT realm）。(C) **クラウド STS がクレームを一時クレデンシャルの属性に変換する**（AWS session tags、GCP Workload Identity Federation の attribute mapping）。
2. **信頼境界は「誰が DB コンテキストを設定するか」で決まる。**(A) の場合、DB は注入者を信頼するしかない。そのため、注入者以外が同じ接続上で任意 SQL を実行できると境界が崩れる（AWS は「クエリを実行できる者は誰でもセッション変数を変更できるので分離は弱い」と明記）。
3. **最大の実装リスクはコネクションプール**である。セッションスコープの変数や `SET ROLE` は、プール越しに次のリクエストへ漏れる。PostgreSQL では `SET LOCAL`／`set_config(..., true)`（トランザクションスコープ）を使う。SQL Server では `@read_only=1` を使う。PgBouncer の transaction pooling では `SET/RESET` は「Never」（使えない）。
4. **トークン寿命と接続寿命は別物**である。RDS IAM トークン（15 分）は「認証時にだけ使われ、確立後のセッションには影響しない」。Cloud SQL では、期限切れ後に失敗するのは「新しい接続」だけと書かれている。Kafka だけは `connections.max.reauth.ms` で既存接続の再認証を強制できる。
5. **認可に使うクレームは「本人が書き換えられない属性」に限る**（Supabase: `user_metadata` は不可、`app_metadata` は可）。
6. **マスキング（DDM・Snowflake masking・BigQuery data masking）は「ロール」で選ばれる。**したがって、ロールを決めるクレーム（Snowflake の `scp` に入る `session:role:*`、Entra グループなど）こそが最重要の機密クレームになる。DDM は推論攻撃を防がない（Microsoft 明記）。

---

## 1. トークンのクレームで行・属性単位のデータ認可を行う

### 1.1 PostgreSQL RLS（素の PostgreSQL）— 前提知識

- RLS を有効にしたテーブルにポリシーが無いと **default-deny** になる。一方で **スーパーユーザーと `BYPASSRLS` 属性付きロールは常に RLS をバイパスする**。テーブル所有者も通常はバイパスするため、適用させるには `ALTER TABLE ... FORCE ROW LEVEL SECURITY` が要る。`TRUNCATE`／`REFERENCES` は RLS の対象外。
  - https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- `set_config(name, value, is_local)` は、`is_local=true` なら現在のトランザクションの間だけ有効、`false` ならセッションの残り全体で有効。
  - https://www.postgresql.org/docs/current/functions-admin.html
- `SET ROLE` は current user を切り替える。その後の権限チェックは「そのロールで最初からログインしたかのように」行われる。`RESET ROLE` と `SET ROLE NONE` は **任意のユーザーが実行できる**。また **`SET ROLE` は `SECURITY DEFINER` 関数の中では使えない**。
  - https://www.postgresql.org/docs/current/sql-set-role.html
  - → 推論: 任意 SQL を実行できるクライアントがセッションスコープの `SET ROLE` を使うと、`RESET ROLE` で元の（通常は高権限の）ログインロールに戻れてしまう。ロール切り替えはサーバー側（ゲートウェイ）が、トランザクションスコープ（`SET LOCAL ROLE`）で行うべきである。
- `SECURITY DEFINER` 関数は所有者の権限で実行される。安全に書くには `search_path` に信頼できるスキーマだけを並べ、**`pg_temp` を最後**に置く（一時スキーマはデフォルトで最初に検索され、誰でも書き込めるため）。
  - https://www.postgresql.org/docs/current/sql-createfunction.html

### 1.2 PostgREST（`request.jwt.claims` と `role` クレーム）

- **クレームから DB コンテキストへ**: PostgREST は JWT を検証し、ヘッダー・クッキー・JWT クレームを **トランザクションスコープの設定**として JSON 形式で格納する。SQL からは `current_setting('request.jwt.claims', true)::json ->> 'email'` のように読める。
  - https://docs.postgrest.org/en/stable/references/transactions.html
- `request.jwt.claims` の中の `role` は、未指定なら `db-anon-role` の値になる。設定値はコミット後に NULL ではなく空文字 `''` になるため、`nullif(current_setting($1, true), '')` のようなラッパー関数を作ることが推奨されている。（同上）
- **ロール切り替え**: 有効な JWT に `role` クレームがあれば、PostgREST は HTTP リクエストの間 `SET LOCAL ROLE user123;` を実行してそのロールに切り替える。そのためには、事前に authenticator ロールへ対象ロールを GRANT しておく必要がある。
  - https://docs.postgrest.org/en/stable/references/auth.html
  - https://docs.postgrest.org/en/stable/explanations/db_authz.html （`GRANT user000 TO authenticator;`、切り替え先ロールは nologin）
- **外部 IdP 対応**: `jwt-role-claim-key` に JSON Path（RFC 9535）を書くと、ロールの格納位置を変えられる。Auth0・Okta・Entra・Keycloak のトークンを想定している。旧 JSPath DSL は非推奨。
  - https://docs.postgrest.org/en/stable/references/auth.html
- **信頼境界**: コンテキストを設定するのは PostgREST（authenticator 接続）である。DB は「PostgREST が検証したクレーム」を信じる。
- **注意点（公式）**: SUPERUSER が作ったビューは **すべての RLS ポリシーをバイパスする**。ロール名はデータベース単位ではなくクラスタ単位の名前空間なので衝突しうる。
  - https://docs.postgrest.org/en/stable/explanations/db_authz.html
- → 設計上の含意: `role` クレームは **DB の権限ロールそのもの**を選ぶ。IdP 側でこのクレームを誰が設定できるかが、権限昇格の境界になる。組織共通クレームに `role` という汎用名を使うと、PostgREST がそれを DB ロールと解釈して衝突する恐れがある（→ 名前空間付きクレームと `jwt-role-claim-key` を使う）。

### 1.3 Supabase（`auth.jwt()` / `auth.uid()`）

- `auth.uid()` は「リクエストしているユーザーの ID を返す」。`auth.jwt()` はリクエストユーザーの JWT を返し、`raw_app_meta_data` と `raw_user_meta_data` の両方の内容が読める。
  - https://supabase.com/docs/guides/database/postgres/row-level-security
- **公式警告**: 「JWT にある情報のすべてを RLS ポリシーに使うべきではない」。`user_metadata` クレームに依存する RLS は、**認証済みエンドユーザーが値を変更できる**ためセキュリティ上の問題を生む。`raw_user_meta_data` は `supabase.auth.update()` でユーザー自身が更新できるので認可データの置き場所に向かない。`raw_app_meta_data` はユーザーが更新できないので認可データに適する。（同上）
- 「JWT は常に最新とは限らない」（同上）→ ロールを剥奪しても、トークンが失効するまで RLS は古いクレームで評価される。
- テストでは `set local role` と `set local request.jwt.claim.sub` でロールと ID を切り替えることが推奨されている。（同上）
- **SECURITY DEFINER の扱い**: RLS の性能対策として security definer 関数（例: `private.has_good_role()`）を使う方法が紹介されている。ただし「**公開（exposed）スキーマにある security definer 関数は、作成者の権限で Data API から呼び出せる**」ため、非公開スキーマに置く。（同上）
- **ビュー**: 「ビューは通常 postgres ユーザーで作られるため、デフォルトで RLS をバイパスする」。（同上）
- **管理用キー**: RLS をバイパスする管理タスクには secret key を使う。（同上）→ secret key をサービス間で共有すると、エンドユーザーのクレームに基づく分離は完全に無効になる。

### 1.4 Hasura（セッション変数）

- Hasura は JWT を検証・デコードし、**`x-hasura-` で始まるセッション変数のクレーム**を取り出す。`x-hasura-default-role` と `x-hasura-allowed-roles` は必須。
  - https://hasura.io/docs/2.0/auth/authentication/jwt/
- `x-hasura-allowed-roles` はユーザーが取りうるロールの一覧である。リクエストヘッダー `x-hasura-role` で **クライアントがその中から使うロールを選べる**（無ければ default-role）。（同上）
- 行権限はセッション変数で組み立てる。例: `{"id":{"_eq":"X-Hasura-User-Id"}}`。配列のセッション変数（`X-Hasura-Allowed-Ids: {1,2,3}`）は `_in` などで使える。
  - https://hasura.io/docs/2.0/auth/authorization/permissions/row-level-permissions/
- **信頼境界**: 認可を評価するのは Hasura エンジン（DB の RLS ではない）。DB は Hasura の接続ロールしか知らない。
- → 推論: ヘッダーで選べるのは allowed-roles の範囲内に限られる。それでも allowed-roles に高権限ロールを入れると、クライアント判断で昇格できてしまう。

### 1.5 SQL Server / Azure SQL RLS と `SESSION_CONTEXT`

- **パターン（公式例 C）**: 中間層アプリケーションのユーザー（またはテナント）が同じ SQL ユーザーを共有する。アプリは接続後に `SESSION_CONTEXT` にアプリユーザー ID を設定し、セキュリティポリシーがフィルター述語・ブロック述語で行を絞る。「実際には、接続を開いた後に `SESSION_CONTEXT()` に現在のユーザー ID を設定するのはアプリケーションの責任」。**`@read_only = 1` を指定すると、接続が閉じられる（＝プールに返される）まで値を変更できない**。
  - https://learn.microsoft.com/en-us/sql/relational-databases/security/row-level-security
- 公式例の述語では `DATABASE_PRINCIPAL_ID() = DATABASE_PRINCIPAL_ID('AppUser')` も同時に確認している。さらに `DENY UPDATE ON Sales(AppUserId)` でテナント列の書き換えを禁止している。（同上）
- `sp_set_session_context`: 「**任意のユーザーが自分のセッションのセッションコンテキストを設定できる**」。キーは最大 128 バイト、値は最大 8,000 バイト、合計 1 MB まで。
  - https://learn.microsoft.com/en-us/sql/relational-databases/system-stored-procedures/sp-set-session-context-transact-sql
  - → 推論: 任意 SQL を実行できる者が同じ接続を使える場合、`read_only` でロックされていなければ偽のテナント ID を設定できる。
- **Data API builder（DAB）**: `set-session-context: true` にすると、DAB は毎リクエスト、クエリ実行前に `sp_set_session_context` で**認証済みユーザーの全クレーム**（`roles`、`sub`/`oid`、カスタムクレーム）をキーと値の組で送る。例: `EXEC sp_set_session_context 'roles', 'Oscar', @read_only = 0;`。有効にするとそのデータソースのレスポンスキャッシュは無効になる。
  - https://learn.microsoft.com/en-us/azure/data-api-builder/concept/security/row-level-security
  - https://learn.microsoft.com/en-us/azure/data-api-builder/reference-database-specific-features
  - → 注: DAB の例は `@read_only = 0`。DAB 以外のクライアントが同じ DB ユーザーで任意 SQL を実行できると上書きされうる。DB ユーザーを DAB 専用にするべきである（推論）。
- **公式のセキュリティ注意**: 悪意のあるセキュリティポリシー管理者によるサイドチャネル攻撃がある。また巧妙なクエリ（例: `SELECT 1/(SALARY-100000) ...` のゼロ除算エラー）で、フィルターされた値を推測できる。`DBCC SHOW_STATISTICS`、CDC、Change Tracking も漏えい経路になる。RLS 用オブジェクトは専用スキーマに分け、`ALTER ANY SECURITY POLICY` は高権限者に限定する。
  - https://learn.microsoft.com/en-us/sql/relational-databases/security/row-level-security
- `dbo`・`db_owner`・テーブル所有者にもセキュリティポリシーは適用される（PostgreSQL の所有者バイパスとは異なる）。（同上）

### 1.6 Elasticsearch / OpenSearch（DLS とテンプレート）

- **Elasticsearch JWT realm**: `claims.principal`（既定は `username`）、`claims.groups`、`claims.mail` などで、クレームをユーザー属性に対応付ける。`allowed_issuer` は大文字小文字を区別した完全一致、`allowed_audiences` も完全一致。扱うトークン種別は `id_token`（既定）か `access_token` で、**1 つの realm で扱えるのは 1 種別だけ**。`access_token` には `allowed_subjects` または `allowed_subject_patterns` が必須。クライアント認証（shared secret）はデフォルトで有効。クレームは role mapping で `metadata.jwt_claim_<key>` として参照できる。`role_mapping.yml` は JWT realm では使えない。
  - https://www.elastic.co/docs/deploy-manage/users-roles/cluster-or-deployment-auth/jwt
- **Elasticsearch DLS テンプレート**: ロールのクエリに Mustache テンプレートを書き、`_user.username`、`_user.roles`、`_user.metadata` などを差し込める。例: `{{#toJson}}_user.metadata.statuses{{/toJson}}`。ingest の set security user processor を使えば、ドキュメント側にユーザー情報を付与できる。
  - https://www.elastic.co/docs/deploy-manage/users-roles/cluster-or-deployment-auth/controlling-access-at-document-field-level
  - JWT クレーム由来の `jwt_claim_*` メタデータを DLS テンプレートの `_user.metadata` から直接参照できるかは、両ページの組み合わせからの推論であり **[未検証]**。
- **OpenSearch**: DLS のパラメータ置換で `${user.name}`、`${user.roles}`（backend roles）、`${user.securityRoles}`、`${attr.<type>.<name>}`（type は `internal`、**`jwt`**、`proxy`、`ldap`）が使える。**変数が存在しないとエラーになる**。3.7.0 からはフォールバック値（`${attr.proxy.notexists:-bar}`）を指定できる。`terms_set` と組み合わせた属性ベースのセキュリティ例がある（index の `security_attributes` は keyword 型にする）。
  - https://docs.opensearch.org/latest/security/access-control/document-level-security/
  - → 推論: フォールバック値を「全件許可」側に設定すると、クレームが欠けたときにフェイルオープンになる。

### 1.7 Snowflake（row access policy）と External OAuth

- row access policy は、セッションの **アクティブなプライマリ／セカンダリロール**を直接評価するか、マッピングテーブルを参照するか、その両方で行を絞る。マッピングテーブルは保護対象テーブルと同じ DB に置くことが推奨されている（`IS_DATABASE_ROLE_IN_SESSION` を使う場合は特に）。インシデント調査では Time Travel でポリシーとマッピングを再構成する。
  - https://docs.snowflake.com/en/user-guide/security-row-intro
- External OAuth では、トークンの scope に入った `session:role:<role>` がセッションロールになる（詳細は §2.4）。→ 推論: External OAuth 経由のクエリでは、**IdP が発行した `scp` クレームが `CURRENT_ROLE()` を決め、それが row access policy／masking policy の分岐を決める**。

### 1.8 BigQuery row-level security

- row access policy の grantee には `user:`、`group:`、`domain:` の他に **Workforce Identity Federation のプリンシパル識別子**を指定できる。grantee list に含まれないユーザーは行を一切見られない。`SESSION_USER()` を使うと、クエリ実行者のメールアドレスに基づいて行を絞れる。
  - https://cloud.google.com/bigquery/docs/row-level-security-intro
- **制約・注意（公式）**: クエリ時間などのサイドチャネルで、ストレージシャード境界付近の行の情報が漏れうる。JSON 列、一時テーブル、ワイルドカードテーブルには適用できない。BI Engine と materialized views は高速化されない。（同上）
- → 推論: BigQuery の RLS は「自分で定義したセッション変数」ではなく、**IAM プリンシパル（Google ID または WIF で対応付けた外部 ID）**で評価される。カスタムクレームを効かせるには、WIF の attribute mapping でプリンシパルやグループに落とし込む必要がある。

---

## 2. パスワードの代わりにトークンで DB に認証する

### 2.1 Azure SQL Database / Managed Instance（Microsoft Entra）

- **対応付けの鍵は Entra のオブジェクト ID**。Entra ログインまたは包含ユーザーの `SID` は「Entra ID のオブジェクト ID のバイナリ表現」（ログインベースユーザーは末尾に 'AADE' が付く）。`CAST(sid AS UNIQUEIDENTIFIER)` で GUID に戻せる。type は E（外部ユーザー／アプリ）か X（外部グループ）。
  - https://learn.microsoft.com/en-us/azure/azure-sql/database/authentication-aad-overview
- 表示名が重複する場合は `CREATE LOGIN/USER ... FROM EXTERNAL PROVIDER WITH OBJECT_ID = '...'` を使う。サービスプリンシパルでは「Application ID ではなく Object ID が必要」。
  - https://learn.microsoft.com/en-us/azure/azure-sql/database/authentication-microsoft-entra-create-users-with-nonunique-names
- **制約**: 2048 を超える Entra セキュリティグループに所属するユーザー／SP はログインできない。`SUSER_NAME()` などの関数は Entra プリンシパルに対して NULL を返す。グループ経由でサインインしたユーザーには暗黙のユーザーが作られない。**Entra 認証は Azure RBAC と統合されない**（DB 内にプリンシパルを作る必要がある）。受け付けるのは Entra ID が発行したアクセストークンだけで、サードパーティのトークンは使えない。（authentication-aad-overview）
- → 推論: SID の照合は oid、グループ照合はトークンまたはディレクトリのグループに基づく。トークン内のどのクレーム（`oid`/`groups`/`appid`）をどう使うかは、このページでは明示されていない **[未検証]**。
- **トークン期限と既存接続**: 公式の記述は見つからなかった **[未検証]**。

### 2.2 Azure Database for PostgreSQL Flexible Server（Entra）

- アクセストークンを DB ロールに対応付けるとき、**ユーザー名ではなく Entra の一意なユーザー ID** を使う。同名ユーザーを削除して作り直すと別人として扱われ、既存ロールでは接続できない。
- **削除された Entra ユーザーでも、トークンが失効するまで（発行から最大 60 分）サインインできる**。DB 側でもユーザーを削除すれば即時に失効する。
- ユーザートークンは最大 1 時間、システム割り当てマネージド ID のトークンは最大 24 時間有効。グループメンバーとしてサインインする場合は、ユーザー名にグループ名を指定し、パスワードには個人のトークンを使う。
  - https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/security-entra-concepts

### 2.3 AWS RDS / Aurora IAM データベース認証

- 認証トークンは AWS Signature Version 4 で生成され、**有効期限は 15 分**。「トークンは認証にのみ使われ、**確立後のセッションには影響しない**」。
- 制限: CloudWatch と CloudTrail は IAM 認証を記録しない（`generate-db-auth-token` を追跡しない）。PostgreSQL では `rds_iam` を付けたユーザーはパスワード認証より IAM 認証が優先される。`aws:SourceIp` などの一部のグローバル条件キーは使えない。インスタンスに 300〜1000 MiB の追加メモリが必要。トークンは約 1 KB 以上あり、ドライバーが切り詰めると失敗する。一時クレデンシャルからトークンを生成した場合、接続時にもその一時クレデンシャルが有効でなければならない。
  - https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAMDBAuth.html
- → 推論: エンドユーザーのクレームは IAM 認証に乗らない（DB ユーザーと IAM ポリシーの `rds-db:connect` の対応付けのみ）。エンドユーザー単位の分離には §1 の RLS 注入を併用する。

### 2.4 Google Cloud SQL IAM データベース認証

- OAuth 2.0 アクセストークンを使い、**有効期限は 1 時間**。Cloud SQL コネクタがトークンを取得・更新するので、コネクションプールを使う長期プロセスでも安定する。自動 IAM 認証が強く推奨されている。手動方式ではユーザー名にメールアドレス、パスワードにトークンを使う。SSL 接続が必須。
  - https://docs.cloud.google.com/sql/docs/postgres/iam-authentication
- 期限切れの扱いについては「この時刻以降に作られる**新しい接続やログインは失敗する**」とだけ書かれている。既存セッションへの影響は明記されていない **[未検証]**。（同上）
- **IAM グループ認証**: 共有のグループアカウントではなく、各ユーザーが個人の IAM アカウントでログインする。初回ログイン時にユーザーごとの DB アカウントが作られ、「**個々のログインと DB 操作が監査ログに現れる**」。Workforce Identity Federation による DB 認証もある（別ページ）。（同上）
- サービスアカウントの DB ユーザー名は、メールアドレスから `.gserviceaccount.com` を除いたもの。
  - https://docs.cloud.google.com/sql/docs/postgres/iam-logins

### 2.5 Snowflake External OAuth

- **スコープ→ロール**: カスタムロールは `session:role:<role>`（例: ANALYST → `session:role:analyst`）、PUBLIC は `session:role:public`、ANY ロールは `session:role-any`。**scope が定義されていないと接続は失敗する**。
- **既定でブロックされるロール**: ACCOUNTADMIN、GLOBALORGADMIN、ORGADMIN、SECURITYADMIN。解除するには `EXTERNAL_OAUTH_ADD_PRIVILEGED_ROLES_TO_BLOCKED_LIST = FALSE` を設定する。
- **ユーザー対応付け**: `EXTERNAL_OAUTH_TOKEN_USER_MAPPING_CLAIM` に、Okta なら `sub`、Entra なら `upn` を指定する例がある。どちらも Snowflake の `login_name` に対応付ける。セカンダリロールにも対応している。
  - https://docs.snowflake.com/en/user-guide/oauth-ext-overview
- **カスタム認可サーバーの要件**: ペイロードに `aud`、`exp`、`iss`、`iat`、`scp`（scope の一覧）が必要。scope 属性は既定で `scp`。`scope` を使う場合は `external_oauth_scope_mapping_attribute` で指定する。Snowflake 側の属性は `external_oauth_snowflake_user_mapping_attribute`（例: `login_name`）で指定する。`external_oauth_any_role_mode` は `DISABLE`（既定）、`ENABLE`、`ENABLE_FOR_PRIVILEGE`（`USE_ANY_ROLE` 権限を持つ場合のみ）のいずれか。
  - https://docs.snowflake.com/en/user-guide/oauth-ext-custom
- トークン期限切れのエラー（390318）は記載されている。セッション継続中に期限が切れたときの挙動とリフレッシュの扱いは記載されていない **[未検証]**。（同上）

### 2.6 Databricks OAuth token federation

- IdP のトークンで Databricks API にアクセスでき、PAT や Databricks OAuth シークレットを不要にする。種類は「アカウント全体のフェデレーション」と「ワークロード ID フェデレーション（サービスプリンシパル単位）」。
  - https://docs.databricks.com/aws/en/dev-tools/auth/oauth-federation
- フェデレーションポリシー: `iss`（issuer）、`aud`（audiences）、subject claim（既定は `sub`）。サービスプリンシパル用ポリシーでは「**`sub` クレームとポリシーの subject を完全一致で照合**」する。アカウント全体ポリシーの subject claim は「Databricks ユーザー名を含むクレーム」。交換後の Databricks トークンの寿命は記載されていない **[未検証]**。
  - https://docs.databricks.com/aws/en/dev-tools/auth/oauth-federation-policy

### 2.7 MongoDB Atlas（Workforce / Workload Identity Federation）

- 人間向けの Workforce は OIDC、アプリ向けの Workload は OAuth 2.0。LDAP 認可と OIDC 認証は併用できない。
  - https://www.mongodb.com/docs/atlas/security-oidc/
- **User Claim**（既定 `sub`。Entra でユーザー ID 認可を使う場合は `upn` か `oid`）、**Groups Claim**（既定 `groups`。Group Membership 認可を選んだ場合に必須）、Audience（通常は Client ID）。認可方式は「Group Membership」と「User ID」から選ぶ。
- 寿命: 「（任意）アクセストークンの寿命（`exp` クレーム）を DB 接続セッションの時間に合わせる」、「（任意）リフレッシュトークンを許可する」と書かれている（`offline_access` が必要）。期限切れ時に既存接続がどうなるかは記載されていない **[未検証]**。
  - https://www.mongodb.com/docs/atlas/workforce-oidc/

### 2.8 Kafka SASL/OAUTHBEARER

- デフォルト実装（unsecured JWT）は「本番以外での使用にのみ適する」。本番では callback handler をオーバーライドするか、組み込みの JWT 検証を使う必要がある。ブローカーの設定項目は `sasl.oauthbearer.jwks.endpoint.url`、`sasl.oauthbearer.expected.audience`、`sasl.oauthbearer.expected.issuer`、`sasl.oauthbearer.sub.claim.name`、`sasl.oauthbearer.scope.claim.name`。「Kafka はトークンが失効する前に定期的にリフレッシュする」（`sasl.login.refresh.*`）。
  - https://kafka.apache.org/43/security/authentication-using-sasl
- `sasl.oauthbearer.sub.claim.name` は既定 `sub`、`sasl.oauthbearer.scope.claim.name` は既定 `scope`。いずれも IdP が別名を使う場合に指定する（Red Hat の Kafka 設定リファレンス。Apache Kafka のプロパティ説明と同一とみられる）。
  - https://docs.redhat.com/en/documentation/red_hat_streams_for_apache_kafka/2.5/html/kafka_configuration_properties/admin-client-configuration-properties-str
  - → 推論: プリンシパル（ACL の対象）は sub クレームで決まる。標準の ACL authorizer が scope クレームを認可に使うかどうかは **[未検証]**（ACL はプリンシパル単位と理解している）。
- **再認証**: `connections.max.reauth.ms` を正の値にすると、セッション寿命（この値を超えない）が v2.2.0 以降のクライアントに伝えられる。**寿命内に再認証せずに使われた接続はブローカーが切断する**。既定値は 0（無効）。メトリクス `ExpiredConnectionsKilledCount` で監視できる。
  - https://kafka.apache.org/41/configuration/broker-configs
  - https://kafka.apache.org/30/operations/monitoring

### 2.9 「トークン寿命 vs 接続寿命」問題のまとめ

| 製品 | トークン寿命（公式） | 確立済み接続への影響 | 出典 |
|---|---|---|---|
| RDS/Aurora IAM | 15 分 | **影響しない**（認証時のみ使用） | RDS IAMDBAuth |
| Cloud SQL IAM | 1 時間 | 新規接続のみ失敗と記載。既存は **[未検証]** | Cloud SQL iam-authentication |
| Azure PostgreSQL Entra | ユーザー最大 1 時間、システム MI 最大 24 時間 | 削除ユーザーも失効まで（最大 60 分）サインイン可。既存接続は **[未検証]** | security-entra-concepts |
| Azure SQL Entra | 記載なし | **[未検証]** | — |
| Snowflake External OAuth | IdP の `exp` に依存 | **[未検証]** | oauth-ext-custom |
| MongoDB Atlas OIDC | IdP の `exp`（接続時間に合わせることを推奨） | **[未検証]** | workforce-oidc |
| Kafka OAUTHBEARER | IdP の `exp` | `connections.max.reauth.ms` で**再認証を強制でき、しなければ切断** | broker-configs |

→ 設計上の含意（推論）: 多くの DB では、トークンは「接続を開く鍵」にすぎず、**失効やクレーム変更（ロール剥奪・テナント移動）は既存の接続に反映されない**。対策は次のとおり。(1) プール接続の最大寿命をトークン寿命以下にする（Microsoft Q&A の SQL MI の事例では、プール接続の寿命を 5 分未満にする記述がある［二次情報］）。(2) エンドユーザーのクレームは接続単位ではなく**トランザクション単位で毎回注入する**。(3) 即時失効が必要なら DB 側のプリンシパルを削除する（Azure PostgreSQL では即時失効と明記）。

---

## 3. オブジェクトストレージ・クラウドデータへのフェデレーション

### 3.1 AWS STS `AssumeRoleWithWebIdentity` + session tags → S3 ABAC

- OIDC トークンにセッションタグを含める形式は 2 つある。
  - **ネスト形式**: `"https://aws.amazon.com/tags": {"principal_tags": {"Project": ["Automation"], ...}, "transitive_tag_keys": ["Project", ...]}`
  - **フラット形式**（Entra ID のようにネストしたオブジェクトを出せない IdP 向け）: `"https://aws.amazon.com/tags/principal_tags/Project": "Automation"`、`"https://aws.amazon.com/tags/transitive_tag_keys": [...]`
- 発行された一時クレデンシャルでのリクエストには、`aws:PrincipalTag` コンテキストキーが付く。ポリシーの `Condition` でこれを見て許可・拒否する（S3 などの ABAC）。
- **制約・注意**: IdP に接続された**すべてのロールの信頼ポリシーに `sts:TagSession` が必要**（無いと AssumeRole 自体が失敗する。タグを渡す IdP は別インスタンスにする手もある）。タグは 50 個まで、キーは 128 文字、値は 256 文字、**多値は不可**。新しいセッションタグは同じキーのロールタグを（大文字小文字を問わず）上書きする。transitive タグはロールチェーンで引き継がれる。`aws:RequestTag`、`aws:TagKeys`、`sts:TransitiveTagKeys` で、渡せるタグのキーと値を制限できる。プリンシパルタグは CloudTrail に記録される。
  - https://docs.aws.amazon.com/IAM/latest/UserGuide/id_session-tags.html
  - https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRoleWithWebIdentity.html
- → 設計上の含意（推論）: IdP がタグ用クレームを**ユーザー自身が編集できる属性**から作っていると、ユーザーが自分のタグを選べてしまう。信頼ポリシーで `aws:RequestTag/TenantID` の値を検証するか、IdP 側でマッピング元を管理者専用の属性に限定する。

### 3.2 Azure Storage（Entra トークン + ABAC 条件）

- Azure ABAC は Blob / ADLS Gen2 / Queue で GA。`request`、`resource`、`environment`、`principal` の各属性が使える。
  - https://learn.microsoft.com/en-us/azure/storage/blobs/storage-auth-abac-attributes
- **`@Principal` 属性は Microsoft Entra の「カスタムセキュリティ属性」**（ユーザーまたはエンタープライズアプリに割り当てる）であり、使うには Attribute Assignment Administrator などの権限が必要。条件では `@Resource[...tags:Project]` などと比較できる。
  - https://learn.microsoft.com/en-us/azure/role-based-access-control/conditions-format
  - → 推論: Azure Storage の ABAC は、**アプリが発行するカスタム JWT クレームではなくディレクトリの属性**を見る。したがって組織カスタムクレームを Storage ABAC に効かせるには、同じ値を Entra のカスタムセキュリティ属性として持つ必要がある（トークンに載るかどうかは **[未検証]**）。

### 3.3 Google Cloud Workload Identity Federation

- attribute mapping は `TARGET_ATTRIBUTE=SOURCE_EXPRESSION`（CEL）で書く（例: `google.subject=assertion.sub`）。OIDC と SAML では mapping の指定が必須。attribute condition では `assertion.*` とマッピング済み属性を使って受け入れるトークンを制限できる。
- `google.subject` は一意かつ 127 文字以内、カスタム属性は 50 個まで。`principal://.../subject/VALUE` で単一 ID、`principalSet://.../group/GROUP_ID` や `principalSet://.../attribute.NAME/VALUE` で集合に IAM ロールを付与する。「プール内の全 ID にアクセスを付与することもできるが、リスクを伴う」。`google.subject` は Cloud Logging のログに現れる。
  - https://docs.cloud.google.com/iam/docs/workload-identity-federation
  - マッピング済み属性を IAM Conditions（allow policy の条件式）で直接参照できるかは、このページでは確認できなかった **[未検証]**。属性で権限を分けるには `principalSet://.../attribute.tenant/acme` へのロール付与が確実な方法である。

---

## 4. パターン: 「ID をデータ層まで伝播する」か「サービス ID + アプリ側で認可する」か

### 4.1 Microsoft: OBO で SQL へ

- OBO の目的は「ユーザーの ID と権限をリクエストチェーンに沿って渡すこと」。委任スコープのみを使い、アプリロールは使わない。**OBO が使えるのはユーザープリンシパルだけ**（app-only トークンは不可）。受け取ったトークンの `aud` が OBO を要求するアプリ自身でなければ交換できない。中間層が受け取ったトークンを、本来の audience 以外に転送してはならない。
  - https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-on-behalf-of-flow
- App Service のチュートリアル: 組み込み認証と Azure SQL の `user_impersonation` 委任権限を使い、「サインインしたユーザーとして」SQL に接続する。
  - https://learn.microsoft.com/en-us/azure/app-service/tutorial-connect-app-access-sql-database-as-user-dotnet
- **Data API builder 2.0 の OBO**: 受け取ったユーザートークンを SQL 用トークンに交換し、「DB が実際の呼び出しユーザーとして認証する」。標準モード（DAB 自身の資格情報で接続）との対比で、OBO を使うべき場面は「**ユーザー ID に依存する RLS**」「**ユーザー単位の DB アクセスログが必要なコンプライアンス監査**」「MCP」。**ユーザーごとに別の SQL コネクションプールを持つ**ので、あるユーザーのトークンが別ユーザーに再利用されることはない。キャッシュは無効にする必要がある。対応は MSSQL + Entra のみ。
  - https://learn.microsoft.com/en-us/azure/data-api-builder/concept/security/authenticate-on-behalf-of
  - → 推論: 代償としてユーザー数に比例して接続数が増え、プール効率が落ちる。

### 4.2 AWS: SaaS テナント分離（PostgreSQL RLS）

- RLS ポリシー `tenant_id = current_setting('app.current_tenant')::UUID` を使う。`app.current_tenant` は、アプリが接続を作るときまたはプールから取り出すときに `SET`／`set_config` で設定する（Java の `getConnection()` オーバーライド例あり）。変数名には「接頭辞.変数」形式が必要。**「セッション変数は pgBouncer などのサーバー側コネクションプールと互換性がない場合がある。プール戦略がセッション状態を共有するかどうかをテストせよ」**。
  - https://aws.amazon.com/blogs/database/multi-tenant-data-isolation-with-postgresql-row-level-security （日本語版: https://aws.amazon.com/jp/blogs/news/multi-tenant-data-isolation-with-postgresql-row-level-security ）
- 別の AWS ブログ: テナント情報は認証コンテキスト（例: JWT）から取り出して `SET app.current_tenant` する。しかし「**テーブルにクエリできる者は誰でもセッション変数を変更できるので、この分離は弱い**」。そのため全 SQL に明示的な `WHERE` 述語を付けるコーディング規約とピアレビューを併用することが推奨されている。
  - https://aws.amazon.com/blogs/database/choose-the-right-postgresql-data-access-pattern-for-your-saas-application
- PgBouncer: transaction pooling では「SET/RESET: Never」（PREPARE、LISTEN、セッションレベルの advisory lock なども同様）。
  - https://www.pgbouncer.org/features.html
  - → 推論: `SET` ではなく、トランザクション内で `set_config('app.current_tenant', $1, true)`（＝ `SET LOCAL`）を使えば、プールで漏れることはない。PostgREST はこの方式。

### 4.3 AWS: テナント単位の IAM クレデンシャル（TVM / ABAC）

- **Token Vending Machine**: `JwtClaimsManager` が JWT からテナント ID を取り出し、`PolicyGenerator` が動的ポリシー（セッションポリシー）を生成し、STS `assumeRole` に渡してテナントに限定したクレデンシャルを返す。トークン取得の経路を 1 つに集約し、テナント分離をマイクロサービス開発者から隠す。
  - https://aws.amazon.com/blogs/apn/isolating-saas-tenants-with-dynamically-generated-iam-policies
  - https://aws.amazon.com/blogs/apn/applying-dynamically-generated-isolation-policies-in-saas-environments （TVM が JWT を検証し、テンプレートに値を埋めて STS に渡す）
- **ABAC 版**: `sts.assume_role(..., Tags=[{'Key':'TenantID','Value':tenant_id}])` でテナント ID をプリンシパルタグにし、ポリシーで `aws:PrincipalTag/TenantID` を参照する。動的ポリシー方式は、ロール定義が頻繁に変わる環境向けと位置づけられている。
  - https://aws.amazon.com/blogs/security/how-to-implement-saas-tenant-isolation-with-abac-and-aws-iam
- → 信頼境界（推論）: TVM（またはそれを呼ぶサービス）がクレームを検証してタグやポリシーに変換する。**TVM を経由せずに広い権限のロールを直接使える経路が残っていると、分離は成立しない**。

### 4.4 パターン比較と必要クレーム・監査

| 観点 | ID 伝播（OBO・DB ネイティブのトークン認証・ユーザーごとの接続） | サービス ID + コンテキスト注入（SESSION_CONTEXT / `set_config` / PostgREST） | サービス ID + アプリ側の認可のみ |
|---|---|---|---|
| DB が知る主体 | エンドユーザー（oid/upn/sub など） | サービス（＋注入された属性） | サービスのみ |
| DB 監査ログの主体 | エンドユーザー（Cloud SQL: 個人ごとに記録、DAB OBO: ユーザー単位ログ） | サービス。ユーザーは注入値を別途ログ化しない限り見えない（推論） | サービスのみ |
| 必要クレーム | 安定 ID（`oid`/`sub`）、グループ／ロール、（Snowflake は `scp` に `session:role:*`） | `tenant_id`、`sub`、`roles`、（目的: `purpose` 等） | アプリ認可に必要なもの |
| プール効率 | 低（ユーザーごとのプール） | 高（ただしトランザクションスコープでの注入が必須） | 高 |
| 主なリスク | トークン期限と接続寿命のずれ、接続数の爆発 | コンテキストの漏れ・偽装（任意 SQL・プール） | アプリのバグがそのまま越境になる |

- `purpose`（利用目的）クレームを DB 側の認可に使う製品機能は、今回の調査範囲の公式ドキュメントには無かった。SESSION_CONTEXT や `request.jwt.claims` に任意のクレームとして載せて述語で使うことは技術的に可能（DAB は全クレームを送る）。

---

## 5. 機微データとマスキング（ロール／クレームで選ばれる）

### 5.1 Azure SQL / SQL Server Dynamic Data Masking

- マスク関数は default、email、random、partial、datetime（2022 以降）。**`UNMASK` 権限を持つ者だけが平文を見られる**。SQL Server 2022 以降は、UNMASK を DB・スキーマ・テーブル・列の各レベルで、ユーザー、DB ロール、**Entra ID、Entra グループ**に付与できる。`CONTROL` を持つ管理者（sysadmin、db_owner）は常に平文を見られる。
- **公式のセキュリティ注意**: DDM は「アドホッククエリを実行できる非特権ユーザーが推論やブルートフォースで実データを得ること」を防がない（例: `WHERE Salary > 99999 and Salary < 100001`）。誤って露出するのを防ぐためのもので、悪意ある推論は防がない。最小権限と監査を併用する。マスク列への UPDATE は防がない。
  - https://learn.microsoft.com/en-us/sql/relational-databases/security/dynamic-data-masking
- → 推論: 共有のサービス ID で接続すると UNMASK は「サービス単位」でしか付与できない。ユーザーごとのマスキングには、ID 伝播（OBO）か、SESSION_CONTEXT を見る自前のビューや関数が必要になる。

### 5.2 Snowflake masking policies

- Dynamic Data Masking は Column-level Security の機能で、クエリ時にマスクする。ポリシーはスキーマレベルのオブジェクト。
  - https://docs.snowflake.com/en/user-guide/security-column-ddm-intro
- 例: `CASE WHEN CURRENT_ROLE() IN ('ANALYST') THEN val ELSE '*********' END`。
  - https://docs.snowflake.com/en/user-guide/security-column-ddm-use
- **関数の使い分け（公式）**: `CURRENT_ROLE` は SQL 文の実行コンテキストに影響されず、セッションを対象にする。**ロール階層が必要なら `IS_ROLE_IN_SESSION`** を使う。`INVOKER_ROLE` は実行コンテキストを対象にする（テーブルなら CURRENT_ROLE、ビューならビュー所有者のロール）。`IS_GRANTED_TO_INVOKER_ROLE` も同じ考え方。
  - https://docs.snowflake.com/en/user-guide/security-column-advanced
- → 推論: External OAuth では `scp` の `session:role:*` → `CURRENT_ROLE()` → マスキング分岐、と連鎖する。**IdP の scope 発行ポリシーが、事実上マスキング解除の権限になる**。`session:role-any` と `ENABLE` の組み合わせでは、ユーザーがセッション内でロールを切り替えられる。

### 5.3 BigQuery data masking（policy tags）

- data masking は列レベルのアクセス制御の上に成り立つ。**Masked Reader**（マスク済みデータを読める）と **Fine-Grained Reader**（平文を読める）の 2 つのロールで決まる。ポリシータグ階層を列のタグから上へ評価し、**最初に見つかったロール**が使われる（上位に Fine-Grained Reader、下位に Masked Reader があればマスクされる）。
  - https://cloud.google.com/bigquery/docs/column-data-masking-intro
- → 推論: 対象は IAM プリンシパルなので、外部クレームは WIF/Workforce の `principalSet://.../attribute.*` やグループ経由でロールに落とし込む。

---

## 6. 設計ルール／アンチパターン（出典付き）

**(a) 設計ルール 22 項目**

1. **DB コンテキストは「検証済みトークン → 信頼できる注入者」だけが設定する。**アプリ利用者が任意 SQL を流せる接続では、セッション変数ベースの分離は弱い。— AWS「anyone with access to query the table can modify the session variable」 https://aws.amazon.com/blogs/database/choose-the-right-postgresql-data-access-pattern-for-your-saas-application ／ SQL Server「Any user can set a session context for their session」 https://learn.microsoft.com/en-us/sql/relational-databases/system-stored-procedures/sp-set-session-context-transact-sql
2. **PostgreSQL ではクレームをトランザクションスコープで注入する**（`SET LOCAL` / `set_config(..., true)`）。セッションスコープの `SET` はプールで漏れる。— https://www.postgresql.org/docs/current/functions-admin.html ／ PostgREST はトランザクションスコープの設定を使う https://docs.postgrest.org/en/stable/references/transactions.html
3. **PgBouncer の transaction pooling で `SET` に依存しない。**— 「SET/RESET … Never」 https://www.pgbouncer.org/features.html ／ AWS も pgBouncer との非互換に注意を促している https://aws.amazon.com/blogs/database/multi-tenant-data-isolation-with-postgresql-row-level-security
4. **SQL Server では `sp_set_session_context ... @read_only = 1` を使い、述語で接続主体（`DATABASE_PRINCIPAL_ID()`）も確認する。**— https://learn.microsoft.com/en-us/sql/relational-databases/security/row-level-security
5. **認可に使うクレームは、ユーザーが自分で書き換えられない属性から作る**（Supabase の `app_metadata` は可、`user_metadata` は不可）。— https://supabase.com/docs/guides/database/postgres/row-level-security
6. **DB ロールを選ぶクレーム（PostgREST の `role`、Hasura の `x-hasura-allowed-roles`、Snowflake の `session:role:*`）は高権限クレームとして扱い、発行元を限定する。**— https://docs.postgrest.org/en/stable/references/auth.html ／ https://hasura.io/docs/2.0/auth/authentication/jwt/ ／ https://docs.snowflake.com/en/user-guide/oauth-ext-overview
7. **組織共通クレームは名前空間付きにし、製品ごとのクレーム位置設定でマッピングする**（PostgREST の `jwt-role-claim-key`、Kafka の `sasl.oauthbearer.sub.claim.name`、Snowflake の `external_oauth_scope_mapping_attribute`、Elasticsearch の `claims.*`）。— 各製品ドキュメント（§1.2、§2.5、§2.8、§1.6）
8. **DB ユーザーの対応付けには、表示名やメールではなく不変 ID を使う**（Entra: object ID、Azure PostgreSQL: 一意なユーザー ID。同名で作り直したユーザーは別人）。— https://learn.microsoft.com/en-us/azure/azure-sql/database/authentication-aad-overview ／ https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/security-entra-concepts
9. **RLS をバイパスする主体（superuser、`BYPASSRLS`、テーブル所有者、SUPERUSER が作ったビュー、Supabase の secret key）をアプリの通常経路から排除する。**所有者にも適用するなら `FORCE ROW LEVEL SECURITY` を使う。— https://www.postgresql.org/docs/current/ddl-rowsecurity.html ／ https://docs.postgrest.org/en/stable/explanations/db_authz.html ／ https://supabase.com/docs/guides/database/postgres/row-level-security
10. **`SECURITY DEFINER` 関数は非公開スキーマに置き、`search_path` を固定して `pg_temp` を最後にする。**— https://www.postgresql.org/docs/current/sql-createfunction.html ／ https://supabase.com/docs/guides/database/postgres/row-level-security
11. **ロール切り替えはクライアントにさせない。**`RESET ROLE` は誰でも実行できるので、セッションスコープの `SET ROLE` は分離にならない。— https://www.postgresql.org/docs/current/sql-set-role.html
12. **トークン寿命と接続寿命を分けて設計する。**DB 認証トークンは「接続の鍵」にすぎない（RDS: 確立後のセッションに影響しない）。プール接続の最大寿命を決め、失効を即時反映したければ DB 側のプリンシパルを削除する。— https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAMDBAuth.html ／ https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/security-entra-concepts
13. **Kafka では `connections.max.reauth.ms` を設定し、既存接続にもトークン期限を効かせる。**unsecured のデフォルト実装は本番で使わない。— https://kafka.apache.org/41/configuration/broker-configs ／ https://kafka.apache.org/43/security/authentication-using-sasl
14. **ユーザー単位の監査が要件なら ID 伝播を選ぶ**（DAB OBO、Cloud SQL IAM グループ認証）。サービス ID 方式では DB 監査にサービスしか残らない。— https://learn.microsoft.com/en-us/azure/data-api-builder/concept/security/authenticate-on-behalf-of ／ https://docs.cloud.google.com/sql/docs/postgres/iam-authentication
15. **ID 伝播では、ユーザーごとの接続プールとキャッシュ無効化をセットで導入する。**— DAB はユーザーごとのプールを持ち、キャッシュ無効化を必須としている https://learn.microsoft.com/en-us/azure/data-api-builder/concept/security/authenticate-on-behalf-of
16. **OBO で渡せるのはユーザー ID だけ。**app-only のトークンは OBO できない。受け取ったトークンを別の audience に流用しない。— https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-on-behalf-of-flow
17. **STS session tags では、信頼ポリシーで `aws:RequestTag` / `aws:TagKeys` を使い、渡せるキーと値を限定する。**多値タグは使えないので、`roles` 配列はそのまま載らない。— https://docs.aws.amazon.com/IAM/latest/UserGuide/id_session-tags.html
18. **テナント単位のクラウドクレデンシャルは TVM に集約する**（JWT を検証 → テナント ID を抽出 → セッションポリシーかタグを付けて AssumeRole）。— https://aws.amazon.com/blogs/apn/isolating-saas-tenants-with-dynamically-generated-iam-policies ／ https://aws.amazon.com/blogs/security/how-to-implement-saas-tenant-isolation-with-abac-and-aws-iam
19. **GCP WIF では attribute condition で受け入れるトークンを絞り、権限は `principalSet://.../attribute.*` で限定的に付与する**（プール全体への付与はリスクがある）。— https://docs.cloud.google.com/iam/docs/workload-identity-federation
20. **マスキングを選ぶロールの階層を意識する**（Snowflake は階層が必要なら `IS_ROLE_IN_SESSION`、BigQuery はタグ階層で最初に見つかったロールが勝つ）。— https://docs.snowflake.com/en/user-guide/security-column-advanced ／ https://cloud.google.com/bigquery/docs/column-data-masking-intro
21. **DDM と RLS だけで機微データを守らない**（推論・エラー・統計・CDC・クエリ時間のサイドチャネル）。最小権限と監査を併用する。— https://learn.microsoft.com/en-us/sql/relational-databases/security/dynamic-data-masking ／ https://learn.microsoft.com/en-us/sql/relational-databases/security/row-level-security ／ https://cloud.google.com/bigquery/docs/row-level-security-intro
22. **クレームが欠けたらフェイルクローズにする**（OpenSearch は変数が無いとエラー。フォールバック値で全件許可にしない。PostgREST の設定値はコミット後に `''` になるので NULL と区別する）。— https://docs.opensearch.org/latest/security/access-control/document-level-security/ ／ https://docs.postgrest.org/en/stable/references/transactions.html

**アンチパターン（上記の裏返し・要点）**
- A1: `getConnection()` で `SET app.current_tenant = '...'` を文字列連結で実行し、返却時にリセットしない（SQL インジェクションとプールでの漏れ）。※AWS ブログの例は説明用のコード。https://aws.amazon.com/blogs/database/multi-tenant-data-isolation-with-postgresql-row-level-security
- A2: `user_metadata`（ユーザーが編集できる）を RLS や AWS タグの元にする。https://supabase.com/docs/guides/database/postgres/row-level-security
- A3: 管理者キー（Supabase の secret key、DB 所有者ロール）をマイクロサービス間で共有し、エンドユーザーのクレームの分離を無効化する。（同上）
- A4: 1 時間有効のトークンで開いた接続を、ロール剥奪後も何時間もプールで使い続ける（§2.9）。

---

## 7. 表: パターン → 必要クレーム → DB コンテキストを設定する者 → 主なリスク

| パターン | 必要クレーム（例） | DB コンテキストを設定する者（信頼境界） | 主なリスク | 主な出典 |
|---|---|---|---|---|
| PostgREST / Supabase（JWT → `request.jwt.claims` + `SET LOCAL ROLE`） | `role`（DB ロール）、`sub`、`tenant_id`（app_metadata） | PostgREST / Supabase の API ゲートウェイ（authenticator 接続） | `role` クレームの過大付与、`user_metadata` の利用、RLS をバイパスするビューや secret key、公開スキーマの SECURITY DEFINER 関数 | docs.postgrest.org, supabase.com |
| Hasura（`x-hasura-*` セッション変数） | `x-hasura-allowed-roles`、`x-hasura-default-role`、`x-hasura-user-id`、テナント ID | Hasura エンジン（認可も Hasura 内で評価） | クライアントがヘッダーで allowed-roles 内の高権限ロールを選べる。DB 側に防御が無い | hasura.io |
| アプリが PostgreSQL に `set_config` / `SET`（AWS SaaS RLS） | `tenant_id`、（`sub`） | アプリ（共有 DB ユーザー） | プールでのセッション変数の漏れ（PgBouncer では使えない）、任意 SQL による偽装 | AWS DB Blog, pgbouncer.org |
| アプリ / DAB が SQL Server に `SESSION_CONTEXT` | `tenant_id` / `sub` / `oid` / `roles` | アプリ / DAB（共有 SQL ユーザー） | `read_only=0` での上書き、プールでの残留、エラーや統計によるサイドチャネル | learn.microsoft.com（RLS, DAB） |
| ID 伝播: OBO → Azure SQL | 委任スコープ（`user_impersonation`）、`oid`（SID の照合） | Entra + Azure SQL（DB がトークンを検証） | ユーザーごとのプールで接続数が増える、トークン期限と接続のずれ、ユーザープリンシパル限定 | learn.microsoft.com（OBO, DAB OBO） |
| DB ネイティブのトークン認証（RDS IAM / Cloud SQL IAM / Azure PG Entra） | IAM プリンシパル（ユーザー名）、グループ | クラウド IAM + DB | 確立後の接続にトークン失効が効かない、RDS では CloudTrail に IAM 認証が残らない | docs.aws.amazon.com, docs.cloud.google.com, learn.microsoft.com |
| Snowflake External OAuth（`scp` → セッションロール → RAP / masking） | `scp`/`scope` の `session:role:*`、ユーザー対応付けクレーム（`sub`/`upn`）、`aud`/`iss`/`exp`/`iat` | IdP（scope の発行）+ Snowflake（検証） | IdP の scope 発行ミスがそのままマスキング解除や行の可視化になる、`role-any` での切り替え | docs.snowflake.com |
| Databricks / MongoDB Atlas / Kafka のトークン認証 | `sub`（またはユーザー名クレーム）、`groups`、`scope` | 各サービス（フェデレーションポリシー / realm / ブローカー） | クレーム名の不一致、unsecured 実装（Kafka）、既存接続の期限切れ | docs.databricks.com, mongodb.com, kafka.apache.org |
| Elasticsearch / OpenSearch DLS テンプレート | `principal`/`groups`、属性（`attr.jwt.*` / `metadata.jwt_claim_*`） | ES/OpenSearch のセキュリティプラグイン（JWT を検証） | クレーム欠落時のフォールバックでフェイルオープンになる、realm のトークン種別の取り違え | elastic.co, docs.opensearch.org |
| AWS STS AssumeRoleWithWebIdentity + session tags → S3 ABAC | `https://aws.amazon.com/tags`（`principal_tags.TenantID` など） | IdP（タグ用クレーム）+ STS（信頼ポリシー） | ユーザーが編集できる属性からタグを作る、`sts:TagSession` の付け漏れ、多値不可 | docs.aws.amazon.com（session tags） |
| AWS TVM（JWT → 動的セッションポリシー / タグ → AssumeRole） | `tenant_id`、（ティアなど） | TVM（ライブラリまたはサービス） | TVM を通らない広い権限のロールが残る | AWS APN / Security Blog |
| GCP WIF → `principalSet` / BigQuery RLS / masking | `google.subject`（`sub`）、`attribute.tenant`、`google.groups` | Google STS（attribute mapping / condition） | attribute condition の不備（他テナントのトークンを受け入れる）、プール全体への付与 | docs.cloud.google.com |
| Azure Storage ABAC | （JWT クレームではなく）Entra のカスタムセキュリティ属性 + リソースタグ | Entra ディレクトリ + Azure RBAC | カスタム JWT クレームでは効かない（属性を二重管理する必要） | learn.microsoft.com（conditions-format） |

---

## 8. 未確認事項・不確実性

- Azure SQL: Entra トークンが失効したときに既存接続がどうなるか、および `groups`/`appid` のどのクレームを照合に使うか **[未検証]**。
- Cloud SQL / Azure PostgreSQL / Snowflake / MongoDB: 確立済みセッション中にトークンが失効したときの挙動 **[未検証]**（公式ページは新規接続についてのみ記載）。
- Kafka: 標準 ACL authorizer が `scope` クレームを認可に使うか **[未検証]**。`sub.claim.name`/`scope.claim.name` の既定値の説明は Red Hat の配布版リファレンスで確認した。
- Elasticsearch: JWT realm のクレーム（`jwt_claim_*`）を DLS テンプレートの `_user.metadata` で参照できるか **[未検証]**。
- GCP: WIF のマッピング済み属性を IAM Conditions で直接参照できるか **[未検証]**。BigQuery の grantee で `principalSet` がどこまで使えるかの詳細も **[未検証]**。
- Azure: カスタムセキュリティ属性がトークンに含まれるか **[未検証]**（ABAC はディレクトリから評価されるとみられる）。
- Databricks: 交換後のトークンの寿命 **[未検証]**。
- 「プール接続の寿命を 5 分未満に」の記述は Microsoft Q&A（コミュニティ回答）由来の二次情報。
