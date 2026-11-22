// Part 7: the data layer - how claims reach databases (RLS, DB authentication, pooling, masking)
module.exports = (L) => {
  const { C, SH, HEX } = L;
  L.section('Part 7 データ層');
  L.divider('PART 7', 'データ層：データアクセスとデータベース認証', 'クレームは DB の手前で消えない。行の絞り込み・DB へのログイン・マスキングで、誰がどの値を信じるかを決める',
    ['クレームは、どの経路で DB に届くか', '誰が DB の文脈を設定してよいか', '接続プールで、なぜ他人の文脈が漏れるのか', 'DB の監査ログに、利用者を残すべきか'],
    'Part 7 はデータ層です。トークンのクレームは、API で読まれて終わりではありません。テナントや利用者の ID で DB の行を絞ったり、パスワードの代わりにトークンで DB にログインしたり、ロールでマスキングを切り替えたりと、データ層まで届きます。そのとき問題になるのは、誰がクレームを解釈し、誰が DB の文脈を設定するか、という信頼境界です。この Part では、クレームが DB に届く 3 つの経路、行単位の制御の製品ごとの違い、接続プールで文脈が漏れる事故、トークンでの DB 認証と寿命のずれ、利用者の ID を DB まで伝えるかどうか、マスキング、クラウドの属性を順に扱い、最後にレビューの規則をまとめます。', { id: 'p07-part' });

  const ruleGrid = (s, items) => {
    items.forEach((t, i) => {
      const col = Math.floor(i / 5), row = i % 5;
      const x = 0.6 + col * 6.15, y = 1.95 + row * 0.9;
      s.addShape(SH.ROUNDED_RECTANGLE, { x, y, w: 5.95, h: 0.78, rectRadius: 0.08, fill: { color: C.background2 }, line: { color: C.background2 } });
      s.addText(String(i + 1), { shape: SH.OVAL, x: x + 0.15, y: y + 0.14, w: 0.5, h: 0.5, fill: { color: C.accent4 }, line: { color: C.accent4 }, fontSize: 14, bold: true, color: C.background1, align: 'center', valign: 'middle', margin: 0 });
      L.T(s, t, { x: x + 0.8, y: y + 0.06, w: 5.0, h: 0.66, fontSize: 13, valign: 'middle', margin: 0 });
    });
  };

  {
    const s = L.content('DB への 3 つの経路：誰がクレームを解釈するか', { id: 'p07-three-db-paths',
      lead: '注入する／DB が検証する／STS が一時認証情報に替える。経路ごとに信頼境界が違う',
      stages: [2, 4],
      notes: 'トークンのクレームがデータ層に届く経路は 3 つあります。A は注入です。ゲートウェイやミドルウェア、アプリ自身がトークンを検証し、そのクレームを DB のセッションの設定に書き込みます。PostgREST、Supabase、Hasura、Microsoft の Data API builder、アプリが自分で set_config や SESSION_CONTEXT を設定する方式がこれに当たります。DB は注入した者を信じるしかないので、注入した者以外が同じ接続で任意の SQL を流せると、境界が崩れます。B は、DB やデータ基盤がトークンを直接検証し、自分の主体やロールに対応付ける方式です。Azure SQL や Azure の PostgreSQL の Entra 認証、Snowflake の External OAuth、Kafka の OAUTHBEARER などです。ここでの問題は、トークンの寿命と接続の寿命のずれです。C は、クラウドの STS がクレームを一時的な認証情報の属性に変える方式で、AWS のセッションタグや、Google Cloud の Workload Identity Federation の属性の対応付けです。タグの元になる属性を誰が書けるかが境界になります。経路を選ぶ前に、DB の文脈を設定するのは誰かを図にしておきます。',
      refs: { spec: 'PostgREST Transactions／Azure SQL Entra 認証／AWS STS セッションタグ', inst: 'NIST SP 800-162 §3.1.3.3（権威ある者だけが属性を付与）', book: '『デジタルアイデンティティのすべて』（考え方）12.3 節 pp.194–195' },
    });
    const paths = [
      ['A　注入する', 'ゲートウェイ・アプリが DB の文脈を設定', C.accent1, [['例：', 'PostgREST・Supabase・Hasura・Data API builder・アプリの set_config'], ['DB が信じる：', '注入した者'], ['危険：', '任意の SQL での上書き、接続プールでの漏れ']]],
      ['B　DB が検証する', 'DB がトークンを受け、自分の主体に対応付け', C.accent5, [['例：', 'Azure SQL・PostgreSQL の Entra 認証、Snowflake External OAuth、Kafka'], ['DB が信じる：', '発行者と対応付けの規則'], ['危険：', 'トークンの寿命と接続の寿命のずれ']]],
      ['C　STS が変換する', 'クレームを一時認証情報の属性に', C.accent2, [['例：', 'AWS のセッションタグ、GCP Workload Identity Federation'], ['DB が信じる：', '信頼ポリシーと属性の対応'], ['危険：', '利用者が編集できる属性からタグを作る']]]];
    paths.forEach((p, i) => {
      const x = 0.6 + i * 4.125;
      L.box(s, [{ text: p[0], options: { bold: true, fontSize: 16, breakLine: true } }, { text: p[1], options: { fontSize: 11.5 } }], { x, y: 1.95, w: 3.85, h: 0.95, fill: p[2] });
      s.addShape(SH.ROUNDED_RECTANGLE, { x, y: 3.05, w: 3.85, h: 2.5, rectRadius: 0.08, fill: { color: C.background2 }, line: { color: C.background2 } });
      L.T(s, L.runs(p[3], { space: 8 }), { x: x + 0.18, y: 3.17, w: 3.5, h: 2.3, fontSize: 12, margin: 0 });
    });
    L.note(s, 'leader', '経路を選ぶ前に「DB の文脈を設定するのは誰か」を図に書く。その主体以外が書ける経路を残さない', { x: 0.6, y: 5.75, w: 12.1, h: 0.75, size: 13, label: '' });
  }

  {
    const s = L.content('行単位の制御：クレームで行を絞る製品の違い', { id: 'p07-row-level-security',
      lead: '同じ「クレームで行を絞る」でも、どのクレームを誰が評価するかが製品ごとに違う',
      stages: [4],
      notes: 'クレームで行を絞る代表的な製品を比べます。PostgREST は JWT を検証し、クレームを request.jwt.claims という取引単位の設定に入れます。JWT に role クレームがあれば、その要求の間だけ SET LOCAL ROLE でそのロールに切り替えます。つまり role は DB のロールそのものなので、組織の共通クレームに role という汎用の名前を使うと衝突します。Supabase は auth.uid() と auth.jwt() で利用者の ID とクレームを読みますが、公式に、user_metadata は利用者自身が書き換えられるので認可に使ってはならず、app_metadata を使うよう警告しています。Hasura は x-hasura- で始まるクレームをセッション変数にし、エンジンの中で行の権限を評価します。クライアントは x-hasura-role ヘッダーで、許されたロールの中から使うロールを選べます。SQL Server と Azure SQL では、アプリや Data API builder が SESSION_CONTEXT に値を入れ、セキュリティポリシーで行を絞ります。Snowflake は、External OAuth の scp に入った session:role がセッションのロールになり、行のポリシーを決めます。BigQuery は、セッション変数ではなく IAM の主体で評価します。どの製品でも、スーパーユーザーのように RLS をすり抜ける主体を、通常の経路から外す必要があります。',
      refs: { spec: 'PostgreSQL RLS／PostgREST Auth／Supabase RLS／Hasura JWT', inst: 'OWASP ASVS 8.2.2（データ単位の認可）・8.4.1', book: '『セキュアAPI』4.3 節 pp.101–103（取得時に所有者を照合）' },
    });
    L.table(s, [['製品', 'クレームの届き方', '評価する者', '注意'],
      ['PostgreSQL RLS＋PostgREST', 'request.jwt.claims（取引単位）。role で SET LOCAL ROLE', 'DB のポリシー', 'role は DB ロールそのもの。汎用名は衝突する'],
      ['Supabase', 'auth.uid()・auth.jwt()', 'DB のポリシー', { text: 'user_metadata は本人が書ける。app_metadata を使う', options: { color: HEX.accent3 } }],
      ['Hasura', 'x-hasura-* のセッション変数', 'Hasura エンジン', 'x-hasura-role で許されたロールから選べる'],
      ['SQL Server・Azure SQL', 'SESSION_CONTEXT（アプリ・DAB が設定）', 'DB のセキュリティポリシー', 'DAB は全クレームを送る。@read_only を確認'],
      ['Snowflake', 'scp の session:role:* → CURRENT_ROLE()', 'row access policy', 'IdP の scope が見える行を決める'],
      ['BigQuery', 'IAM の主体（WIF で対応付け）', 'row access policy', 'セッション変数ではなく主体で評価']],
    { x: 0.6, y: 1.95, w: 12.1, colW: [2.6, 3.7, 2.1, 3.7], fontSize: 11.5, rowH: 0.55 });
    L.note(s, 'warn', 'RLS をすり抜ける主体を通常の経路から外す：superuser・BYPASSRLS・テーブル所有者・SUPERUSER が作ったビュー・Supabase の secret key', { x: 0.6, y: 5.95, w: 12.1, h: 0.6, size: 12, label: '' });
  }

  {
    const s = L.content('信頼境界：DB の文脈を設定してよいのは誰か', { id: 'p07-trust-boundary',
      lead: '注入型の分離は、注入者以外が同じ接続で SQL を流せた時点で崩れる。AWS と Microsoft が明記',
      stages: [4],
      notes: '注入型の方式では、DB は「注入した者が正しく検証した」ことを前提にしています。AWS は SaaS のテナント分離の解説で、テーブルにクエリできる者は誰でもセッション変数を変えられるので、この分離は弱いと書き、すべての SQL に明示的な WHERE の条件を付ける規約とレビューを併用するよう勧めています。Microsoft も、sp_set_session_context について、どのユーザーも自分のセッションの文脈を設定できると明記しています。そのため、値を設定するときに @read_only を 1 にして、接続が閉じられるまで変えられないようにし、述語では接続している DB の主体も確かめます。もう 1 つの論点は、DB のロールを選ぶクレームです。PostgREST の role、Hasura の x-hasura-allowed-roles、Snowflake の session:role は、どれも DB の権限そのものを選びます。こうしたクレームは最も権限の高いクレームとして、書ける発行元を限定します。また、PostgreSQL の RESET ROLE は誰でも実行できます。取引単位の SET LOCAL ROLE でも、クライアントが同じ取引の中で任意の SQL を流せれば、RESET ROLE で戻せます。分離が成り立つのは、クライアントに任意の SQL を流させないときだけです。',
      refs: { spec: 'sp_set_session_context／PostgreSQL SET ROLE／Snowflake External OAuth', inst: 'NIST SP 800-162 §3.1.3.3（本人が変えられない属性）' },
    });
    L.card(s, { x: 0.6, y: 1.95, w: 5.9, h: 1.8, icon: 'MdWarning', color: C.accent3, title: 'AWS の注意', titleSize: 14, body: ['クエリできる者は誰でもセッション変数を変えられる。分離は弱い', '→ 全 SQL に WHERE を付ける規約とレビューを併用'], bodySize: 12 });
    L.card(s, { x: 0.6, y: 3.9, w: 5.9, h: 1.8, icon: 'MdWarning', color: C.accent3, title: 'Microsoft の注意', titleSize: 14, body: ['どのユーザーも自分のセッションの SESSION_CONTEXT を設定できる', '→ @read_only = 1 と、接続主体の確認'], bodySize: 12 });
    L.table(s, [['DB の権限を選ぶクレーム', '何を選ぶか'],
      ['PostgREST の role', 'DB のロール（SET LOCAL ROLE）'],
      ['Hasura の x-hasura-allowed-roles', '選べるロールの範囲'],
      ['Snowflake の session:role:*', 'セッションのロール'],
      ['Supabase の app_metadata', '認可データ（user_metadata は不可）']],
    { x: 6.8, y: 1.95, w: 5.9, colW: [3.1, 2.8], fontSize: 11.5, rowH: 0.6 });
    L.note(s, 'tip', 'SET LOCAL ROLE も、同じ取引で任意の SQL を流せれば RESET ROLE で戻せる。クライアントに任意の SQL を流させない', { x: 6.8, y: 5.1, w: 5.9, h: 0.6, size: 11.5, label: '' });
    L.note(s, 'leader', 'DB の権限を選ぶクレームは最高権限のクレーム。発行元を限定し、名前空間を付けて製品の設定（jwt-role-claim-key など）で対応付ける', { x: 0.6, y: 5.85, w: 12.1, h: 0.7, size: 12.5, label: '' });
  }

  {
    const s = L.content('接続プール：前の利用者の文脈が残る', { id: 'p07-connection-pool',
      lead: 'セッション単位の設定は、プールで次の要求に引き継がれる。文脈は取引ごとに設定する',
      stages: [2, 4],
      notes: '注入型の方式で最も起きやすい事故が、接続プールでの文脈の漏れです。PostgreSQL の SET や、set_config の 3 番目の引数を false にした設定は、セッションが終わるまで残ります。接続プールは接続を使い回すので、前の要求で設定したテナントが、次の利用者の要求に残ってしまいます。対策は、取引単位で設定することです。SET LOCAL か、set_config の 3 番目の引数を true にすると、その取引が終わった時点で設定が消えます。PostgREST はこの方式で、コミットの後は値が NULL ではなく空文字になるので、空文字を NULL として扱うラッパーを作るよう勧めています。PgBouncer の transaction pooling では、SET と RESET はそもそも使えません。AWS も、セッション変数はサーバー側のプールと互換性がない場合があるので、プールが状態を共有するかを試験するよう注意しています。SQL Server では、sp_set_session_context の @read_only を 1 にすると、接続がプールに返されるまで値を変えられません。値は文字列の連結ではなく、パラメータで渡します。',
      refs: { spec: 'PostgreSQL set_config／PgBouncer features／SQL Server RLS（@read_only）／PostgREST', inst: 'OWASP ASVS 8.4.1（テナント横断の制御）' },
    });
    L.T(s, '危ない：セッション単位の設定', { x: 0.6, y: 1.95, w: 6, h: 0.32, fontSize: 12.5, bold: true, color: C.accent3, margin: 0, valign: 'middle' });
    L.code(s, "-- 接続を取り出すたびに\nSET app.current_tenant = 't-042';\nSELECT * FROM orders;\n-- 戻さずに返却 → 次の要求に残る", { x: 0.6, y: 2.3, w: 6.0, h: 1.2, fontSize: 11 });
    L.T(s, '安全：取引単位の設定', { x: 0.6, y: 3.62, w: 6, h: 0.32, fontSize: 12.5, bold: true, color: C.accent4, margin: 0, valign: 'middle' });
    L.code(s, "BEGIN;\nSELECT set_config('app.current_tenant', $1, true);\nSELECT * FROM orders;  -- RLS が行を絞る\nCOMMIT;                -- ここで設定が消える", { x: 0.6, y: 3.97, w: 6.0, h: 1.2, fontSize: 11 });
    L.table(s, [['環境', '規則'],
      ['PostgreSQL', 'SET LOCAL か set_config(…, true)'],
      ['PgBouncer（transaction pooling）', { text: 'SET・RESET は使えない', options: { color: HEX.accent3, bold: true } }],
      ['PostgREST', '取引単位。コミット後は空文字になる'],
      ['SQL Server', '@read_only = 1。述語で接続主体も確認'],
      ['ロールの切り替え', 'サーバー側で SET LOCAL ROLE']],
    { x: 6.9, y: 1.95, w: 5.8, colW: [2.6, 3.2], fontSize: 11.5, rowH: 0.54 });
    L.note(s, 'warn', 'AWS も「サーバー側のプールとは互換性がない場合がある。状態を共有するか試験せよ」と注意している。値は文字列の連結でなくパラメータで渡す', { x: 0.6, y: 5.4, w: 12.1, h: 1.1, size: 12.5, label: '' });
  }

  {
    const s = L.content('DB 認証：パスワードの代わりにトークンで入る', { id: 'p07-db-token-auth',
      lead: 'DB がトークンを検証し、自分の主体に対応付ける。照合のキーは名前ではなく不変の ID',
      stages: [1, 3],
      notes: 'パスワードの代わりに、トークンで DB に認証する方式です。Azure SQL の Entra 認証では、DB のユーザーの SID が Entra のオブジェクト ID から作られます。受け付けるのは Entra が発行したトークンだけで、2048 を超えるセキュリティグループに属する主体はログインできません。また、Azure の権限管理とは統合されないので、DB の中に主体を作る必要があります。Azure の PostgreSQL では、トークンを DB のロールに対応付けるときに、名前ではなく Entra の一意な ID を使います。同じ名前のユーザーを作り直すと、別人として扱われます。トークンの寿命は、利用者のもので最大 1 時間、システム割り当てのマネージド ID で最大 24 時間です。AWS の RDS と Aurora の IAM 認証のトークンは 15 分で、CloudTrail には IAM 認証が記録されません。Cloud SQL の IAM 認証は 1 時間のトークンで、コネクタが取得と更新をします。グループ認証では、個人のログインと操作が監査ログに残ります。Snowflake の External OAuth では、scp に入った session:role がロールになり、ACCOUNTADMIN などの強いロールは既定でブロックされます。Kafka の OAUTHBEARER は、既定の実装が署名を確かめないので、本番では使えません。',
      refs: { spec: 'Azure SQL・PostgreSQL Entra 認証／RDS IAM／Cloud SQL IAM／Snowflake External OAuth', inst: 'NIST IR 8587 §5.3.1.6（ワークロードは短命のトークン）' },
    });
    L.table(s, [['製品', '対応付けのキー', '要点・注意'],
      ['Azure SQL（Entra）', 'オブジェクト ID（SID）', 'Entra のトークンだけ。グループ 2048 超はログイン不可。DB 内に主体を作る'],
      ['Azure PostgreSQL（Entra）', '一意なユーザー ID', '利用者は最大 1 時間、システム MI は最大 24 時間。同名で作り直すと別人'],
      ['RDS・Aurora（IAM）', 'IAM ポリシーの rds-db:connect', 'トークンは 15 分。CloudTrail に IAM 認証は残らない'],
      ['Cloud SQL（IAM）', 'IAM の主体（メールアドレス）', 'トークンは 1 時間。コネクタが更新。グループ認証で個人の操作が監査に残る'],
      ['Snowflake External OAuth', 'sub・upn を login_name に', 'scp の session:role:* がロール。ACCOUNTADMIN などは既定でブロック'],
      ['Kafka OAUTHBEARER', 'sub（名前は設定で変更可）', { text: '既定の unsecured 実装は本番不可。issuer・audience・JWKS を設定', options: { color: HEX.accent3 } }]],
    { x: 0.6, y: 1.95, w: 12.1, colW: [2.7, 2.9, 6.5], fontSize: 11.5, rowH: 0.55 });
    L.note(s, 'leader', '組織の独自クレームを使うなら、製品ごとの「クレームの位置」の設定で対応付ける（Kafka の sub.claim.name、Snowflake の scope 属性など）', { x: 0.6, y: 5.95, w: 12.1, h: 0.6, size: 12, label: '' });
  }

  {
    const s = L.content('寿命のずれ：トークンが切れても、接続は生きている', { id: 'p07-lifetime-mismatch',
      lead: '多くの DB でトークンは「接続を開く鍵」。失効やロールの剥奪は、開いた接続に届かない',
      stages: [5],
      notes: 'トークンで DB に認証するとき、トークンの寿命と接続の寿命は別物です。RDS の IAM 認証のトークンは 15 分ですが、AWS は、トークンは認証のときだけ使われ、確立した後のセッションには影響しないと明記しています。Cloud SQL も、期限の後に失敗するのは新しい接続とログインだと書いています。Azure の PostgreSQL では、Entra から削除したユーザーでも、トークンが切れるまでの最大 60 分はサインインでき、DB 側でもユーザーを削除すればすぐに止まります。既存の接続に期限を効かせられるのは Kafka で、connections.max.reauth.ms を正の値にすると、期限内に再認証しなかった接続をブローカーが切断します。既定値は 0 で無効です。図のように、接続プールで長く使われる接続は、ロールを剥奪した後も、同じ権限で読み続けられます。対策は 3 つです。プールの接続の最大寿命をトークンの寿命以下にすること、利用者のクレームは接続ではなく取引ごとに注入すること、すぐに止めたいときは DB 側の主体を削除することです。',
      refs: { spec: 'RDS IAM DB 認証／Cloud SQL IAM／Azure PG Entra／Kafka broker configs', inst: 'NIST IR 8587 §4.1.4（有効性を権限付与と揃える）／OWASP ASVS 8.3.2' },
    });
    // timeline
    L.T(s, '時間 →', { x: 6.6, y: 3.45, w: 0.9, h: 0.3, fontSize: 11, color: L.MUTED, margin: 0 });
    s.addShape(SH.LINE, { x: 0.6, y: 3.42, w: 6.9, h: 0, line: { color: L.MUTED, width: 1.25, endArrowType: 'triangle' } });
    L.box(s, 'トークン（例：RDS は 15 分）', { x: 0.6, y: 1.95, w: 2.3, h: 0.5, fill: C.accent2, fontSize: 11.5 });
    L.box(s, '接続（プールで使い回される）', { x: 0.6, y: 2.6, w: 6.9, h: 0.5, fill: C.accent5, fontSize: 12 });
    s.addShape(SH.LINE, { x: 4.2, y: 1.95, w: 0, h: 1.45, line: { color: C.accent3, width: 2, dashType: 'dash' } });
    L.T(s, 'ロールを剥奪', { x: 4.3, y: 1.95, w: 2.0, h: 0.32, fontSize: 11.5, bold: true, color: C.accent3, margin: 0 });
    L.T(s, 'この後も同じ接続で読める', { x: 4.3, y: 2.25, w: 3.2, h: 0.32, fontSize: 11.5, color: C.accent3, margin: 0 });
    const fx = [['接続の最大寿命を', 'トークン寿命以下に'], ['利用者のクレームは', '取引ごとに注入'], ['すぐ止めるなら', 'DB 側の主体を削除']];
    fx.forEach((f, i) => {
      L.box(s, [{ text: f[0], options: { fontSize: 12, breakLine: true } }, { text: f[1], options: { fontSize: 13, bold: true } }], { x: 0.6 + i * 2.37, y: 3.95, w: 2.2, h: 1.05, fill: C.accent1 });
    });
    L.table(s, [['製品', '開いた接続への影響'],
      ['RDS・Aurora IAM', '影響しない（認証時だけ使う）'],
      ['Cloud SQL IAM', '影響しない（期限後に失敗するのは新しい接続だけ）'],
      ['Azure PostgreSQL', '削除した利用者も最大 60 分は入れる。DB 側で削除すれば即時'],
      [{ text: 'Kafka', options: { bold: true, color: HEX.accent4 } }, { text: 'connections.max.reauth.ms で再認証を強制。しなければ切断', options: { color: HEX.accent4, bold: true } }]],
    { x: 7.9, y: 1.95, w: 4.8, colW: [1.7, 3.1], fontSize: 11.5, rowH: 0.62 });
    L.note(s, 'warn', '1 時間のトークンで開いた接続を、ロールの剥奪後もプールで使い続けない。Kafka の再認証の既定値は 0（無効）', { x: 0.6, y: 5.35, w: 12.1, h: 0.8, size: 12.5, label: '' });
  }

  {
    const s = L.content('誰として接続するか：利用者の ID か、サービスの ID か', { id: 'p07-connect-as-whom',
      lead: '利用者単位の監査が要るなら ID を DB まで伝える。代わりに接続数とプールの効率を払う',
      stages: [2, 4, 5],
      notes: 'DB に誰として接続するかには、3 つの型があります。1 つ目は利用者の ID を DB まで伝える型で、Entra の On-Behalf-Of で SQL 用のトークンに交換したり、DB のトークン認証で利用者ごとに接続したりします。DB の監査ログに利用者が残り、利用者の ID に依存する行の制御もできます。Data API builder 2.0 の OBO は、利用者ごとに別の接続プールを持ち、あるユーザーのトークンが別のユーザーに使われないようにしています。そのぶん接続数が増え、キャッシュは無効にする必要があります。OBO が使えるのは利用者の主体だけで、アプリだけのトークンは交換できません。2 つ目は、サービスの ID で接続し、文脈を注入する型です。AWS の SaaS の分離の例がこれで、プールの効率は高いですが、取引単位の注入が前提になり、監査ログにはサービスしか残りません。3 つ目は、サービスの ID で接続し、アプリだけで認可する型で、アプリの不具合がそのままテナントの越境になります。クラウドの資格情報なら、AWS の Token Vending Machine のように、JWT からテナント ID を取り出し、テナントに限った一時的な認証情報を返す部品に経路を集めます。',
      refs: { spec: 'Entra OBO／Data API builder OBO／AWS SaaS RLS・TVM の解説', inst: 'OWASP ASVS 8.3.3（元の主体の権限で判断）／NIST IR 8587 §5.3.1.4', book: '『セキュアAPI』4.6.2 節 pp.117–120（所属を DB で照合）' },
    });
    L.table(s, [['観点', 'ID を伝える（OBO・DB のトークン認証）', 'サービス ID＋文脈の注入', 'サービス ID＋アプリで認可'],
      ['DB が知る主体', '利用者（oid・sub）', 'サービス＋注入した属性', 'サービスだけ'],
      ['DB の監査ログ', { text: '利用者', options: { bold: true, color: HEX.accent4 } }, 'サービス（注入値を別に記録しない限り）', 'サービスだけ'],
      ['プールの効率', '低い（利用者ごとのプール）', '高い（取引単位の注入が前提）', '高い'],
      ['主な危険', '寿命のずれ、接続数の増加', '文脈の漏れ・偽装', 'アプリの不具合がそのまま越境']],
    { x: 0.6, y: 1.95, w: 12.1, colW: [2.0, 3.6, 3.4, 3.1], fontSize: 12, rowH: 0.6 });
    const ex = [['MdAccountTree', 'Entra OBO → Azure SQL', '利用者の主体だけ。DAB は利用者ごとのプールでキャッシュ無効'], ['MdApartment', 'AWS の SaaS 分離', 'RLS と app.current_tenant。全 SQL に WHERE も'], ['MdKey', 'Token Vending Machine', 'JWT からテナント ID → ポリシーかタグ → AssumeRole']];
    ex.forEach((e, i) => {
      L.card(s, { x: 0.6 + i * 4.125, y: 5.1, w: 3.85, h: 1.45, icon: e[0], color: C.accent5, title: e[1], titleSize: 13, titleH: 0.45, body: [{ text: e[2], options: {} }], bodySize: 11.5, pad: 0.12 });
    });
  }

  {
    const s = L.content('マスキング：ロールを決めるクレームが最も機微', { id: 'p07-masking',
      lead: 'マスキングはロールで選ばれる。ロールを決めるクレームの発行が、事実上の平文の閲覧権になる',
      stages: [4],
      notes: '列のマスキングも、ロールで選ばれます。Snowflake の例で連鎖を追うと、IdP が scope を発行し、External OAuth のトークンの scp に session:role:analyst が入ります。これが Snowflake の CURRENT_ROLE() になり、マスキングのポリシーが「このロールなら平文を返す」と分岐します。つまり、IdP の scope の発行ポリシーが、事実上、マスキングを解除する権限になります。Azure SQL と SQL Server の動的データマスキングでは、UNMASK 権限を持つ者だけが平文を見られ、SQL Server 2022 以降は Entra のグループにも付与できます。ただし Microsoft は、アドホックなクエリを実行できる利用者が、範囲を絞った条件の繰り返しで実データを推測するのは防げないと明記しています。Snowflake は、ロールの階層が必要なら IS_ROLE_IN_SESSION を使うよう勧めています。BigQuery は、Masked Reader と Fine-Grained Reader の 2 つのロールで決まり、ポリシータグの階層で最初に見つかったロールが使われます。マスキングと行の制御だけで機微なデータを守らず、最小権限と監査を組み合わせます。機微情報の扱いは Part 9 でも扱います。',
      refs: { spec: 'SQL Server DDM／Snowflake masking policies／BigQuery data masking', inst: 'NIST SP 800-162 §3.2.1.6（許可・拒否から属性が推測される）' },
    });
    L.flow(s, [
      { t: 'IdP', d: 'scope を発行', fill: C.accent5 },
      { t: 'トークン', d: 'scp に session:role:analyst', fill: C.accent2 },
      { t: 'Snowflake', d: 'CURRENT_ROLE() = ANALYST', fill: C.accent1 },
      { t: 'マスキング', d: 'このロールなら平文を返す', fill: C.accent3 }],
    { x: 0.6, y: 1.95, w: 12.1, h: 1.05, tSize: 14, dSize: 12 });
    L.table(s, [['製品', '何で選ぶか', '注意'],
      ['Azure SQL・SQL Server DDM', 'UNMASK 権限（Entra のグループにも付与可）', { text: '推論・総当たりは防がない。CONTROL を持つ管理者は常に平文', options: { color: HEX.accent3 } }],
      ['Snowflake', 'CURRENT_ROLE()・IS_ROLE_IN_SESSION', 'ロールの階層が要るなら IS_ROLE_IN_SESSION'],
      ['BigQuery', 'Masked Reader・Fine-Grained Reader', 'ポリシータグの階層で最初に見つかったロールが使われる']],
    { x: 0.6, y: 3.25, w: 12.1, colW: [2.8, 4.1, 5.2], fontSize: 12, rowH: 0.58 });
    L.note(s, 'warn', 'DDM と RLS だけで機微データを守らない。エラー・統計・クエリ時間からも推測される。最小権限と監査を併用する（Part 9）', { x: 0.6, y: 5.75, w: 12.1, h: 0.75, size: 12.5, label: '' });
  }

  {
    const s = L.content('クラウドの属性：クレームがそのまま効くとは限らない', { id: 'p07-cloud-attributes',
      lead: 'STS はクレームを一時認証情報の属性に替える。Azure Storage はクレームでなく属性を見る',
      stages: [1, 4],
      notes: 'クラウドのストレージやデータ基盤では、クレームは一時的な認証情報の属性に変換されてから使われます。AWS では、OIDC のトークンの https://aws.amazon.com/tags というクレームにセッションタグを入れると、STS が一時認証情報にタグを付け、ポリシーの条件で aws:PrincipalTag として参照できます。タグは 50 個まで、多値は使えず、IdP につないだすべてのロールの信頼ポリシーに sts:TagSession が必要です。渡せるキーと値は aws:RequestTag で制限できます。Google Cloud の Workload Identity Federation では、属性の対応付けを CEL の式で書き、attribute condition で受け入れるトークンを絞り、principalSet で属性ごとに権限を付けます。プール全体に付与するのは危険です。Azure Storage の ABAC で使う主体の属性は、Entra のカスタムセキュリティ属性で、アプリが発行する独自の JWT クレームではありません。同じ値を効かせたいなら、ディレクトリの属性として持つ必要があります。どの場合も、タグや属性の元を、利用者が自分で編集できる属性にしてはいけません。',
      refs: { spec: 'AWS STS セッションタグ／GCP Workload Identity Federation／Azure ABAC 条件の形式', inst: 'OWASP Workload Identity Federation CS（ポリシーで使えるか確認）' },
    });
    L.card(s, { x: 0.6, y: 1.95, w: 3.85, h: 2.6, icon: 'MdLabel', color: C.accent2, title: 'AWS STS セッションタグ', titleSize: 14, body: ['タグは 50 個まで。多値は不可', '全ロールの信頼ポリシーに sts:TagSession', 'aws:RequestTag で渡せる値を制限'], bodySize: 12 });
    L.card(s, { x: 4.725, y: 1.95, w: 3.85, h: 2.6, icon: 'MdHub', color: C.accent2, title: 'GCP Workload Identity Federation', titleSize: 14, body: ['属性の対応付けを CEL で書く', 'attribute condition で受け入れを絞る', 'principalSet で属性ごとに付与'], bodySize: 12 });
    L.card(s, { x: 8.85, y: 1.95, w: 3.85, h: 2.6, icon: 'MdStorage', color: C.accent3, title: 'Azure Storage ABAC', titleSize: 14, body: ['主体の属性は Entra のカスタムセキュリティ属性', 'アプリの独自 JWT クレームでは効かない', '同じ値を属性として二重に持つ'], bodySize: 12 });
    L.code(s, '"https://aws.amazon.com/tags": {\n  "principal_tags": { "TenantID": ["t-042"] },\n  "transitive_tag_keys": ["TenantID"]\n}', { x: 0.6, y: 4.75, w: 6.4, h: 1.25, fontSize: 11 });
    L.note(s, 'leader', 'タグや属性の元を、利用者が編集できる属性にしない。トークンにあっても、ポリシーで使えるとは限らない', { x: 7.25, y: 4.75, w: 5.45, h: 1.75, size: 12.5 });
  }

  {
    const s = L.content('データ層の規則：レビューで確かめる 10 項目', { id: 'p07-data-layer-checklist',
      lead: '誰が文脈を設定するか、どの単位で設定するか、接続がいつまで生きるかを確かめる',
      stages: [4, 5],
      notes: 'Part 7 のまとめとして、データ層をレビューするときの 10 項目です。1 から 3 は文脈の設定です。DB の文脈は、検証済みのトークンを受けた注入者だけが設定し、PostgreSQL では取引単位の SET LOCAL か set_config の true で、SQL Server では @read_only を 1 にして接続主体も確かめます。4 から 7 はクレームの選び方です。認可には本人が書き換えられない属性だけを使い、DB のロールを選ぶクレームは高権限として発行元を限定し、RLS をすり抜ける主体を通常の経路から外し、DB のユーザーは表示名やメールではなく不変の ID で対応付けます。8 と 9 は接続です。トークンの寿命と接続の寿命を分けて、プールの接続の寿命を決め、利用者単位の監査が要るなら ID を DB まで伝えます。10 は守りの考え方で、クレームが欠けたときは全件を許すのではなく拒否し、マスキングと行の制御だけに頼りません。どの項目も、製品の既定値に任せず、設計書に書いて試験で確かめます。',
      refs: { spec: 'PostgreSQL・PostgREST・SQL Server・Supabase の公式文書', inst: 'OWASP ASVS 8.2.2・8.4.1／NIST SP 800-162 §3.1.3.3', book: '『セキュアAPI』4.3 節 pp.101–103' },
    });
    ruleGrid(s, [
      'DB の文脈は、検証済みトークンを受けた注入者だけが設定する',
      'PostgreSQL は SET LOCAL か set_config(…, true)',
      'SQL Server は @read_only = 1 と接続主体の確認',
      '認可には、本人が書き換えられない属性だけを使う',
      'DB ロールを選ぶクレームは高権限。発行元を限定する',
      'RLS をすり抜ける主体を、通常の経路から外す',
      'DB ユーザーの対応付けは、名前でなく不変の ID で',
      'トークンと接続の寿命を分け、プール接続の寿命を決める',
      '利用者単位の監査が要るなら、ID を DB まで伝える',
      'クレームが欠けたら拒否。DDM・RLS だけに頼らない']);
  }
};
