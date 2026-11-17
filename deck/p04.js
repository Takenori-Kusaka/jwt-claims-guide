// Part 4: design principles for organisation-wide custom claims (what to carry, names, types, identifiers, writers, size, compatibility)
module.exports = (L) => {
  const { C, SH, HEX } = L;
  L.section('Part 4 設計原則');
  L.divider('PART 4', '独自クレームの設計原則', '何を載せ、どう名付け、どの型で、誰が書くか。受け手が読み違えない契約にする',
    ['何をトークンに載せ、何を都度問い合わせるか', '名前・名前空間・型を、どう決めるか', '識別子と、値を書ける主体を、どう分けるか', '上限・欠落・未知のクレームに、どう備えるか'],
    'Part 4 は、この資料の中心です。組織で共用する独自クレームを、どう設計するかを扱います。最初に、そもそも何をトークンに載せ、何を載せずに都度問い合わせるかを決めます。次に、名前と名前空間、型、空の値の意味、大文字小文字の扱いを決めます。さらに、識別子を名前ではなく変わらない ID にすること、値を書ける主体ごとにクレームを分けること、サイズの上限と黙って消えるクレーム、前方互換、そして誰が付与するかを扱います。最後に、設計例とチェックリストでまとめます。');

  {
    const s = L.content('トークンは写し：発行後の変更は届かない', {
      lead: '載せたクレームは発行時点の値のまま、期限まで使われる。権限を外しても、すぐには効かない',
      stages: [0, 1, 4],
      notes: '独自クレームの設計で最初に押さえるべきことは、トークンは発行時点の写しだということです。上の図は例です。10 時に editor のロールを載せたトークンを発行し、10 時 5 分に管理画面で権限を外しても、トークンの期限が切れるまでは editor のまま通ります。これは実装の不具合ではなく、自己完結型のトークンの性質です。Firebase、Supabase、OpenFGA、Amazon Verified Permissions は、いずれも公式の文書でこの性質を明記しています。Google の Zanzibar の論文は、アクセス制御の設定と内容の更新の順序の問題を「new enemy」問題として説明しています。ある人を文書の共有から外した後に新しい内容を追加したのに、古い共有の設定で評価すると、外したはずの人に新しい内容が見えてしまう、という問題です。論文はトークンを扱っていませんが、同じ構造の問題がトークンでも起きます。発行時点の権限を固めたトークンは、外した後も古い権限のまま評価されるからです。したがって、変わりやすい権限や、主体と対象の関係は、トークンではなく、都度問い合わせる側に置きます。',
      refs: { spec: 'Firebase・Supabase・OpenFGA・AVP 公式文書／Zanzibar（USENIX ATC 2019）', inst: 'NIST SP 800-162 §3.3.1（キャッシュと鮮度）／ASVS 8.3.2', book: '『デジタルアイデンティティのすべて』12.6 節 pp.199–200（考え方）' },
    });
    L.flow(s, [{ t: '10:00 発行', d: 'roles に editor を載せる', fill: C.accent1 }, { t: '10:05 権限を外す', d: 'DB では editor ではない', fill: C.accent5 },
      { t: '10:05〜 まだ通る', d: 'トークンは editor のまま', fill: C.accent3 }, { t: '10:15 期限切れ', d: '次の発行で、やっと反映', fill: C.accent4 }],
    { x: 0.6, y: 1.95, w: 12.1, h: 1.05, tSize: 15, dSize: 12 });
    L.table(s, [['製品・研究', '公式に書かれていること'],
      ['Firebase', 'クレームの変更は、再ログインかトークンの更新まで反映されない'],
      ['Supabase', 'app_metadata を更新しても、JWT の更新まで反映されない'],
      ['OpenFGA', '関係が変わっても、トークンの期限までアクセスが続く'],
      ['Verified Permissions', '失効やリソースの削除は、トークンの有効性に影響しない']],
    { x: 0.6, y: 3.2, w: 7.7, colW: [2.4, 5.3], fontSize: 12, rowH: 0.48 });
    L.card(s, { x: 8.55, y: 3.2, w: 4.15, h: 2.4, color: C.accent3, icon: 'MdHistory', title: '同じ構造：new enemy 問題', titleSize: 15, body: ['共有から外した人に、新しい内容が見える', '古い設定で新しい内容を評価すると起きる', '権限を固めたトークンでも同じ形で起きる'], bodySize: 12.5 });
    L.note(s, 'leader', '変わりやすい権限・関係は、トークンではなく、都度問い合わせる側（PDP・DB）に置く', { x: 0.6, y: 5.8, w: 12.1, h: 0.7, size: 13.5 });
  }

  {
    const s = L.content('載せるか、問い合わせるか：4 つの問いで決める', {
      lead: '認可に使い、寿命より変化が遅く、小さく、全受け手が要るものだけを載せる',
      stages: [0, 1],
      notes: '独自クレームを載せるかどうかを、4 つの問いで決めます。1 つ目は、受け手がそのクレームで認可やルーティングを決めるかです。表示用のプロフィールなら、トークンに載せる必要はなく、UserInfo やデータベースから取ります。Firebase は、カスタムクレームをアクセス制御専用とし、プロフィールなどの保存を強く勧めていません。2 つ目は、トークンの寿命の間に値が変わらないかです。変わるなら、都度 PDP やデータベースに問い合わせます。3 つ目は、小さく上限に収まるかです。長い一覧は、ID だけを載せて中身は API で引きます。4 つ目は、受け手の全員が必要とするかです。一部のサービスだけが使うなら、宛先ごとに絞るか、トークン交換のときに付けます。4 つとも「はい」のときだけ載せ、台帳に登録します。『セキュアAPI』は、細かい権限一覧をトークンに詰める欠点として、更新漏れ、内部構成の露出、肥大化を挙げています。『OpenID Connect入門』は、権限をトークンに入れると IdP にロックインされうると注意しています。',
      refs: { spec: 'Curity クレームのベストプラクティス／Firebase カスタムクレーム', inst: 'NIST SP 800-63C-4 §3.10（必要最小限のデータ）／ASVS 8.3.2', book: '『セキュアAPI』7.7 節 pp.220–221／『OpenID Connect入門』4.3 節 p.68' },
    });
    const qs = [['認可・ルーティングに使うか', '載せない', 'UserInfo・DB で取る'], ['寿命の間、変わらないか', '都度問い合わせる', 'PDP・DB で判定'],
      ['小さく、上限に収まるか', '参照だけ載せる', 'ID を載せ、中身は API'], ['受け手の全員が要るか', '宛先ごとに絞る', '宛先別・交換時に付ける']];
    qs.forEach((q, i) => {
      const x = 0.6 + i * 2.5;
      L.box(s, (i + 1) + '. ' + q[0], { x, y: 2.0, w: 2.1, h: 1.0, fill: C.accent5, fontSize: 13.5 });
      L.arrow(s, x + 2.13, 2.5, 0.33, 'r', L.MUTED, 1.5);
      L.T(s, 'はい', { x: x + 2.08, y: 2.12, w: 0.45, h: 0.28, fontSize: 10, color: L.MUTED, margin: 0, align: 'center' });
      L.arrow(s, x + 1.05, 3.03, 0.42, 'd', L.MUTED, 1.5);
      L.T(s, 'いいえ', { x: x + 1.15, y: 3.08, w: 0.8, h: 0.3, fontSize: 10, color: L.MUTED, margin: 0 });
      L.box(s, [{ text: q[1], options: { bold: true, fontSize: 14, breakLine: true } }, { text: q[2], options: { fontSize: 11.5, bold: false } }], { x, y: 3.5, w: 2.1, h: 0.95, fill: C.background2, color: C.text1 });
    });
    L.box(s, [{ text: '載せる', options: { bold: true, fontSize: 18, breakLine: true } }, { text: '名前・型・上限を台帳に登録（Part 11）', options: { fontSize: 12, bold: false } }], { x: 10.6, y: 2.0, w: 2.1, h: 2.45, fill: C.accent4 });
    L.card(s, { x: 0.6, y: 4.7, w: 7.6, h: 1.8, color: C.accent3, icon: 'MdWarning', title: '詰め込みの代償', titleSize: 15, body: ['更新漏れが、そのまま権限の漏れになる', '内部の構成が、トークンを読む人に見える', 'ヘッダーの上限を超え、性能も落ちる'], bodySize: 12.5 });
    L.note(s, 'leader', '揮発的な業務権限は API 側で管理し、トークンのクレームを鍵に引く（Curity）', { x: 8.45, y: 4.7, w: 4.25, h: 1.8, size: 13 });
  }

  {
    const s = L.content('クレーム名：まず登録名、無ければ自社の名前空間', {
      lead: '意味が足りる登録名は使う。独自の名前は自社が管理する URI を接頭辞にし、予約名を避ける',
      stages: [0],
      notes: '名前の決め方です。まず、IANA に登録された名前や、RFC 9068 の roles、groups、entitlements、委任の act、細かい認可の authorization_details など、既にある名前で意味が足りるかを確かめます。RFC 9068 は、登録済みのクレームで意味が十分なら、その名前を使うよう求めています。足りないときだけ独自の名前を作ります。RFC 7519 は、新しい名前には衝突しにくい名前を使うよう勧め、合意だけで使うプライベートな名前は衝突しうるので慎重に、としています。組織の独自クレームは、自社が管理する URI、たとえば https://claims.example.com/ を接頭辞にします。そのうえで、IdP や基盤の予約名と照合します。表のとおり、Auth0、Firebase、Cognito、Kubernetes は、それぞれ予約名を持っています。とくに Auth0 は、予約名と衝突してもトランザクションは失敗せず、クレームが黙って追加されません。テストで気づきにくいので、名前は発行の前に機械的に照合します。『実践 Keycloak』も、スコープ名は組織内で一意にし、サービス名や URL を接頭辞にするよう勧めています。',
      refs: { spec: 'RFC 7519 §4.2・4.3／RFC 9068 §2.2.2（登録名を優先）', inst: 'NIST SP 800-162 §2.4.2（名前と値を中央で正規化）', book: '『実践 Keycloak』5.5.3 節 pp.81–82（名前に接頭辞）' },
    });
    L.flow(s, [{ t: '1. 登録名で足りるか', d: 'roles・groups・act・authorization_details' }, { t: '2. 自社の名前空間', d: 'https://claims.example.com/…', fill: C.accent5 }, { t: '3. 予約名と照合', d: 'IdP・基盤の予約を避ける', fill: C.accent2 }],
      { x: 0.6, y: 1.95, w: 12.1, h: 1.1, tSize: 15, dSize: 12 });
    L.table(s, [['基盤', '予約・使えない名前', '衝突したとき'],
      ['Auth0', 'urn:auth0、auth0.com、roles・groups・permissions など', { text: '失敗せず、黙って追加されない', options: { color: HEX.accent3, bold: true } }],
      ['Firebase', 'OIDC の登録名、firebase、user_id', '使えない'],
      ['Cognito（AVP 連携）', '接頭辞 cognito・dev・custom', '追加しない（予約）'],
      ['Kubernetes', 'extra の k8s.io・kubernetes.io、接頭辞 system:', '予約。検証ルールで拒否する例']],
    { x: 0.6, y: 3.25, w: 12.1, colW: [2.4, 5.4, 4.3], fontSize: 12.5, rowH: 0.5 });
    L.note(s, 'tip', 'Auth0 では衝突しても失敗しない。名前は、発行の前に予約名の一覧と機械的に照合する', { x: 0.6, y: 5.85, w: 12.1, h: 0.65, size: 13, label: '' });
  }

  {
    const s = L.content('名前空間：1 つにまとめ、受け手のツールで試す', {
      lead: 'まとめると衝突と散らばりを防げる。ただし「.」を含む名前は、ドット区切りのツールで読めない',
      stages: [0, 2, 3],
      notes: '独自クレームを名前空間のもとに置く形は 2 つあります。左は、名前空間を 1 つのキーにして、その下にオブジェクトでまとめる形です。Kubernetes のサービスアカウントのトークンは kubernetes.io の下に、AWS が発行する JWT は https://sts.amazonaws.com/ の下に、自社のクレームをまとめています。散らばらず、衝突もしにくい形です。右は、名前空間を名前ごとの接頭辞にするフラットな形です。AWS のセッションタグは、Entra ID のようにネストを扱えない IdP のために、フラットな形も公式に認めています。注意点は、受け手のツールです。Envoy の jwt_authn の claim_name は、名前を「.」で分割してネストをたどります。そのため、http://example.org/parent_token のような URL 形式の名前は参照できず、キーを完全一致で並べる claim_path を使うよう、Envoy 自身が書いています。kubernetes.io のような名前も「.」を含みます。名前空間の形は、受け手の全ツール、つまりゲートウェイ、メッシュ、CEL、JSONPath で読めることを確かめてから決めます。',
      refs: { spec: 'Envoy jwt_authn（claim_name・claim_path）／AWS セッションタグ／K8s SA トークン', inst: 'OWASP WIF CS（独自クレームを条件に使えるか確認）', book: '『デジタルアイデンティティのすべて』10.2.1 節 p.136（識別子の名前空間の考え方）' },
    });
    L.T(s, 'まとめる（Kubernetes・AWS の形）', { x: 0.6, y: 1.95, w: 5.9, h: 0.35, fontSize: 13.5, bold: true, margin: 0 });
    L.code(s, '{\n  "sub": "u-7f3a…",\n  "https://claims.example.com/": {\n    "tenant_id": "t-042",\n    "org_unit_ids": ["ou-12"]\n  }\n}', { x: 0.6, y: 2.35, w: 5.9, h: 1.85, fontSize: 11 });
    L.T(s, 'フラット（ネストできない IdP 向け）', { x: 6.8, y: 1.95, w: 5.9, h: 0.35, fontSize: 13.5, bold: true, margin: 0 });
    L.code(s, '{\n  "sub": "u-7f3a…",\n  "https://claims.example.com/tenant_id": "t-042",\n  "https://claims.example.com/org_unit_ids": ["ou-12"]\n}', { x: 6.8, y: 2.35, w: 5.9, h: 1.85, fontSize: 11 });
    L.flow(s, [{ t: 'Envoy の claim_name', d: 'https://claims.example.com/tenant_id', fill: C.accent5 }, { t: '「.」で分割', d: '"https://claims" / "example" / "com/tenant_id"', fill: C.accent5 },
      { t: '見つからない', d: 'claim_path（キーの完全一致）を使う', fill: C.accent3 }], { x: 0.6, y: 4.4, w: 12.1, h: 0.95, tSize: 14, dSize: 11.5 });
    L.note(s, 'leader', '名前空間の形（ネストかフラットか）は、受け手の全ツール（ゲートウェイ、メッシュ、CEL、JSONPath）で読めると確かめてから決める', { x: 0.6, y: 5.55, w: 12.1, h: 0.95, size: 13 });
  }

  {
    const s = L.content('型：1 つに固定する。ID と金額は文字列で', {
      lead: '同じ種類の値で型が揺れると、受け手ごとに比較が変わる。型は台帳で 1 つに決める',
      stages: [0, 3],
      notes: '型の決め方です。左は GitLab の CI の ID トークンの公式例からの抜粋です。project_id は文字列の "20" なのに、runner_id は数値の 1 です。ref_protected は、真偽値ではなく文字列の "false" です。ci_config_ref_uri は null になることがあり、environment のように、そもそもキーが無いこともあります。受け手は、これに合わせて比較の書き方を変えなければなりません。組織の独自クレームでは、値の種類ごとに型を 1 つに決めます。ID は文字列にします。Bishop Fox の 49 種類の JSON パーサの調査では、大きな数値が最大値や 0 に化けることが報告されています。金額や数量も、RFC 9396 の例や Transaction Tokens の例と同じく文字列にします。時刻は RFC 7519 の NumericDate、つまり数値です。真偽値は JSON の true と false にします。複数の値を取りうるものは、1 件でも常に配列にします。Hasura は、独自クレームの値をすべて文字列にそろえる規則を採っています。デジタル庁の DS-212 も、属性名、データ型、設定できる値を事前に標準化する必要があるとしています。',
      refs: { spec: 'RFC 7519 §2（NumericDate）／RFC 9396 §9.1 の例／GitLab・Hasura 公式文書', inst: 'デジタル庁 DS-212 §3.2.3（属性名・データ型・値を標準化）' },
    });
    L.T(s, 'GitLab の公式例（抜粋）：型が揺れる', { x: 0.6, y: 1.95, w: 4.8, h: 0.35, fontSize: 13.5, bold: true, margin: 0 });
    L.code(s, '{\n  "project_id": "20",\n  "runner_id": 1,\n  "ref_protected": "false",\n  "groups_direct": ["mygroup/mysubgroup"],\n  "ci_config_ref_uri": null\n}', { x: 0.6, y: 2.35, w: 4.8, h: 2.9, fontSize: 11 });
    L.table(s, [['値の種類', '決める型', '根拠・実例'],
      ['ID', '文字列', '大きな数値はパーサによって化ける'],
      ['金額・数量', '文字列', 'RFC 9396・Txn-Token の例'],
      ['時刻', '数値（NumericDate）', 'RFC 7519 §2'],
      ['真偽', 'JSON の true / false', '文字列 "false" と混ぜない'],
      ['複数値', '常に配列（1 件でも）', 'Cognito の groups は 1 件でも配列']],
    { x: 5.6, y: 1.95, w: 7.1, colW: [1.5, 2.3, 3.3], fontSize: 12.5, rowH: 0.55 });
    L.note(s, 'warn', '大きな数値の ID は、パーサによって最大値や 0 に化ける（Bishop Fox の 49 パーサ調査）。ID は最初から文字列で運ぶ', { x: 0.6, y: 5.5, w: 12.1, h: 0.95, size: 13, label: '' });
  }

  {
    const s = L.content('形：配列は配列で、JSON は JSON のまま', {
      lead: '区切り文字の連結や JSON の文字列化は、受け手に分割と解析の規則を押しつける',
      stages: [0, 3],
      notes: '値の形の落とし穴です。GitHub Actions の OIDC トークンでは、リポジトリの複数選択のカスタムプロパティが、"us-east-1,eu-west-1" のようなカンマ連結の文字列で入ります。GitHub は、受け手の側で文字列の一致や contains で評価するよう案内しています。Kubernetes の設定例には、カンマ連結のロールを split で配列に戻す式があります。受け手は区切り文字を知っていなければなりません。空白区切りは、OAuth の scope の決まりです。Istio は scope と permission だけを自動で分割し、それ以外のクレームは設定しない限り、"admin editor" を 1 つの文字列として比べます。Hasura は、Cognito のように文字列しか載せられない IdP のために、JSON を文字列にして埋め込む形式を用意しています。これは IdP の制約への妥協で、受け手はもう一度 JSON として解析する必要があります。真偽値を文字列にすると、真偽値として比べたときに誤ります。Kubernetes は、email_verified を明示的に true と比較し、真偽値でない値を実行時に捕える書き方を勧めています。ただし、この例の orValue(true) は、クレームが無いときに通します。必須にするなら claims.email_verified == true と書きます。組織の独自クレームでは、複数値は配列、構造はオブジェクト、真偽は true と false にします。',
      refs: { spec: 'RFC 8693 §4.2（scope）／GitHub・Istio・Hasura・Kubernetes 公式文書', inst: 'デジタル庁 DS-212 §3.2.3／NIST SP 800-162 §3.2.1.3（定義を文書化）' },
    });
    L.table(s, [['形', '実例', '受け手に起きること', '代わりに'],
      ['カンマ連結', 'GitHub の複数選択 "us-east-1,eu-west-1"', '文字列の一致・contains で評価する', '文字列の配列'],
      ['空白区切り', 'scope。Istio は他のクレームを分割しない', '"admin editor" が 1 つの値になる', 'scope 以外は配列'],
      ['JSON の文字列化', 'Hasura の stringified_json（Cognito 向け）', 'もう一度 JSON として解析する', 'オブジェクトのまま'],
      ['文字列の真偽', 'GitLab の "ref_protected": "false"', '真偽値として比べると誤る', 'true / false']],
    { x: 0.6, y: 1.95, w: 12.1, colW: [1.9, 4.0, 3.4, 2.8], fontSize: 12.5, rowH: 0.62 });
    L.code(s, '# Kubernetes の設定例（公式、抜粋）\ngroups: claims.roles.split(",")\nclaims.?email_verified.orValue(true) == true', { x: 0.6, y: 5.25, w: 6.4, h: 1.25, fontSize: 11 });
    L.note(s, 'tip', '真偽値は true と明示的に比べる（Kubernetes の推奨）。この例はクレームが無ければ通す。必須なら claims.email_verified == true', { x: 7.2, y: 5.25, w: 5.5, h: 1.25, size: 12 });
  }

  {
    const s = L.content('無い・null・false・空配列：意味を決めておく', {
      lead: '「無い」は偽か、不明か、上限超えか。決めずにいると、受け手ごとに解釈が分かれる',
      stages: [0, 3, 4],
      notes: 'クレームが「無い」ことの意味です。実際の IdP や基盤では、4 つの状態が混在しています。AWS が発行する JWT の mfa_present は、MFA を使ったときだけ文字列の "true" が入り、"false" は決して入りません。無いことが偽を意味する、と明示した規約です。GitLab の ci_config_ref_uri は、パイプラインの定義が別のプロジェクトにあると null になり、environment は指定が無いとキーごと無くなります。groups_direct は、直接所属するグループが 200 を超えると丸ごと省略されるので、0 件と区別できません。Firebase では、null を指定すると独自クレームがすべて消えます。Istio は、クレームが無いと、対応するヘッダーを付けません。組織では、クレームの種類ごとに、無いときの扱いを決めて台帳に書きます。許可を与えるクレームなら、無いときは何も許しません。制限をかけるクレームなら、無いときは拒否します。上限で欠落しうるクレームは、無いことが 0 件を意味しないので、認可に使いません。',
      refs: { spec: 'AWS 送信側 JWT（mfa_present）／GitLab id_tokens／Firebase・Istio 公式文書', inst: 'NIST IR 8587 §5.2.1.1（必須要素を文書化）' },
    });
    const st = [['無い', 'キーそのものが無い', ['AWS の mfa_present は無い＝偽', 'GitLab の groups_direct は 200 超で無い'], C.accent3],
      ['null', '値が null', ['GitLab の ci_config_ref_uri', 'Firebase は null で全削除'], C.accent2],
      ['false', '明示的な偽', ['真偽値のクレームだけで使う', '文字列の "false" と混ぜない'], C.accent5],
      ['空配列 [ ]', '0 件と明示', ['複数値のクレームで使う', '「無い」と区別できる'], C.accent1]];
    st.forEach((c, i) => {
      L.card(s, { x: 0.6 + i * 3.075, y: 1.95, w: 2.875, h: 2.3, color: c[3], title: c[0], titleSize: 18, titleColor: c[3], body: [{ text: c[1], options: { bold: true, breakLine: true } }].concat(L.runs(c[2], { space: 4 })), bodySize: 12.5 });
    });
    L.table(s, [['クレームの種類', '無いときの扱い（台帳に書く）'],
      ['許可を与える（roles など）', '何も許さない'],
      ['制限をかける（区分・地域など）', { text: '拒否する（fail closed）', options: { color: HEX.accent3, bold: true } }],
      ['上限で欠落しうる（一覧など）', '0 件とみなさない。認可に使わない']],
    { x: 0.6, y: 4.45, w: 12.1, colW: [4.6, 7.5], fontSize: 13, rowH: 0.5 });
  }

  {
    const s = L.content('大文字小文字と文字：比べ方を決める', {
      lead: 'クレームは変換せずに比べるのが原則。基盤ごとの大小の扱いの差で、値が黙って消える',
      stages: [0, 3],
      notes: '大文字小文字と文字の扱いです。RFC 7519 は、StringOrURI の値を、大文字小文字を区別し、正規化もせずに比べると定めています。ところが、基盤ごとに扱いが違います。Entra ID のディレクトリ拡張属性は、設定するときは大文字小文字を区別しませんが、トークンを作るときには区別して読みます。そのため、LegacyId と legacyid で設定されたユーザーが混在すると、LegacyId で写像したクレームは後者のユーザーのトークンに出ません。エラーにはならず、黙って欠落します。AWS のセッションタグは、キーの大文字小文字を区別せずに、同じキーの既存のタグを上書きします。Hasura は x-hasura- で始まる名前の大文字小文字を区別しません。Entra の連携 ID 資格情報は、発行者、主体、宛先を大文字小文字を区別して完全一致で比べます。文字の見た目については、RFC 9396 が、同じ見た目で別の文字があるため、type の値を ASCII に限るなどの工夫を勧めています。組織では、値を小文字の ASCII の識別子に限り、発行時に一度だけ正規化し、受け手は変換せずに完全一致で比べます。NIST SP 800-162 も、属性の名前と値を正規化するよう求めています。',
      refs: { spec: 'RFC 7519 §2・§7.3／RFC 9396 §2.1（ASCII に限る）／Entra・AWS 公式文書', inst: 'NIST SP 800-162 §2.4.2（属性の名前と値を正規化）' },
    });
    L.table(s, [['どこで', '大文字小文字の扱い', '起きること'],
      ['RFC 7519（StringOrURI）', '区別する。正規化しない', '"T-042" と "t-042" は別の値'],
      ['Entra の拡張属性', '設定時は区別せず、読むときは区別', { text: '大小が混在すると、クレームが黙って欠落', options: { color: HEX.accent3, bold: true } }],
      ['AWS のセッションタグ', 'キーの大小を区別しない', '同じキーの既存のタグを上書き'],
      ['Hasura', 'x-hasura-* の名前は区別しない', '受け手によって区別の有無が違う'],
      ['Entra 連携 ID 資格情報', '区別して完全一致', '大小が違えば信頼が成り立たない']],
    { x: 0.6, y: 1.95, w: 12.1, colW: [3.0, 4.0, 5.1], fontSize: 12.5, rowH: 0.52 });
    L.note(s, 'leader', '値は小文字の ASCII の識別子に限る（RFC 9396 は type の値を ASCII に限るよう勧める）。発行時に一度だけ正規化し、受け手は変換せず完全一致で比べる', { x: 0.6, y: 5.3, w: 12.1, h: 1.1, size: 13.5 });
  }

  {
    const s = L.content('識別子：名前ではなく、変わらない ID で一致させる', {
      lead: '名前は改名や再利用で別の主体を指す。認可の条件は ID で書き、名前は表示と補助に使う',
      stages: [0, 1, 4],
      notes: '識別子の原則です。名前は変わり、再利用されます。GitHub Actions の OIDC トークンの sub は、従来は組織名とリポジトリ名だけで作られていました。名前が再利用されると、別の持ち主が同じ sub を作れました。GitHub は 2026 年 7 月 15 日以降に作成、改名、移譲されたリポジトリについて、sub に組織とリポジトリの数値の ID を埋め込む形に移りました。区切りに @ を使うのは、GitHub の名前に @ が現れないからです。値の中のコロンは %3A に置き換えます。区切り文字を明示的に設計した例です。GitLab は、別のプロジェクトが過去に使ったパスを含む sub の発行そのものを止めます。Kubernetes は、名前と uid を対で出します。名前は作り直しで再利用されますが、uid は変わりません。Entra ID は、サービス間で共有するキーとして oid と tid の組を勧め、email や upn を認可に使わないよう明記しています。組織の独自クレームでも、名前と ID を対で出し、受け手には ID での一致を求めます。『デジタルアイデンティティのすべて』も、識別子は変えず、名前と分ける考え方を示しています。',
      refs: { spec: 'OIDC Core §5.7／GitHub 不変の sub（2026-04 告知）／K8s SA トークン', inst: 'OWASP WIF CS（変わらない ID を使う）／ASVS 10.3.3', book: '『デジタルアイデンティティのすべて』（考え方）10.2 節 pp.135–136・p.139' },
    });
    L.T(s, 'GitHub Actions の sub', { x: 0.6, y: 1.95, w: 6.3, h: 0.35, fontSize: 13.5, bold: true, margin: 0 });
    L.code(s, '# 従来：名前だけ（再利用されると別の持ち主と一致）\nrepo:octo-org/octo-repo:ref:refs/heads/main\n\n# 2026-07-15 以降の作成・改名・移譲：名前@ID\nrepo:octo-org@123456/octo-repo@456789:ref:refs/heads/main', { x: 0.6, y: 2.35, w: 6.3, h: 1.75, fontSize: 11 });
    L.table(s, [['実例', '設計'],
      ['GitHub', '名前に現れない @ で ID を連結。値の「:」は %3A'],
      ['GitLab', '過去に使われたパスを含む sub は発行しない'],
      ['Kubernetes', 'name と uid を対で出す'],
      ['Entra ID', 'oid＋tid で共有。email・upn で認可しない']],
    { x: 7.1, y: 1.95, w: 5.6, colW: [1.5, 4.1], fontSize: 12.5, rowH: 0.62 });
    L.code(s, '"https://claims.example.com/": {\n  "org_unit_id": "ou-12",  "org_unit_name": "経理部" }', { x: 0.6, y: 4.3, w: 6.3, h: 0.8, fontSize: 11 });
    L.note(s, 'leader', '名前と ID を対で出し、受け手には ID での一致を求める。合成の sub を作るなら、区切り文字と退避の規則を発行者が決めて公開する', { x: 0.6, y: 5.3, w: 12.1, h: 1.1, size: 13.5 });
  }

  {
    const s = L.content('書き手で分ける：確認済みの値と申告の値', {
      lead: '発行者が確かめた値、呼び出しの申告、本人が編集できる値を、同じ場所に混ぜない',
      stages: [0, 1, 4],
      notes: '同じトークンの中でも、値を書ける主体はさまざまです。そこで、書き手ごとにクレームを分けます。AWS が発行する JWT では、IAM の主体に付いたタグは principal_tags に、呼び出し側が API の引数で任意に指定するタグは request_tags に、別のオブジェクトとして入ります。後者は呼び出し側の申告なので、信頼の度合いが違います。Supabase では、本人が自分で更新できる user_metadata と、本人が更新できない app_metadata が分かれています。Supabase は、user_metadata に依存する行単位の制御は、本人が書き換えられるので危険だと明記しています。Transaction Tokens の草案では、トークンの発行サービスである TTS が、決めた認可の詳細を tctx に、要求の環境の文脈を rctx に分けて書きます。rctx は呼び出し側の申告ではありませんが、要求時点の環境の値として扱います。NIST SP 800-162 も、権限を持つ機関だけが付与・主張できる属性があり、本人が変更できないようにすべきだとしています。組織の独自クレームでも、発行者が確かめた値と申告の値は別の名前にし、認可には前者だけを使います。',
      refs: { spec: 'AWS 送信側 JWT（principal_tags・request_tags）／Supabase RLS／Txn-Token 草案 11', inst: 'NIST SP 800-162 §3.1.3.3（権限ある機関だけが付与）', book: '『デジタルアイデンティティのすべて』（考え方）7.2 節 pp.63–64（出自）' },
    });
    const cols = [['MdVerifiedUser', C.accent1, '発行者が確かめた値', ['AWS の principal_tags', 'Supabase の app_metadata', 'Txn-Token の tctx'], '認可に使える'],
      ['MdSwapHoriz', C.accent2, '呼び出し側の申告', ['AWS の request_tags', 'API の引数で任意に指定', '呼び出し側が指定した値'], '記録と参考。認可は慎重に'],
      ['MdPerson', C.accent3, '本人が編集できる値', ['Supabase の user_metadata', 'プロフィールの項目', '本人が更新できる属性'], '認可に使わない']];
    cols.forEach((c, i) => {
      const x = 0.6 + i * 4.1;
      L.card(s, { x, y: 1.95, w: 3.9, h: 2.35, icon: c[0], color: c[1], title: c[2], titleSize: 15, body: c[3], bodySize: 12.5 });
      L.box(s, c[4], { x, y: 4.4, w: 3.9, h: 0.5, fill: c[1], fontSize: 13 });
    });
    L.code(s, '"https://claims.example.com/": {\n  "verified":  { "tenant_id": "t-042" },\n  "requested": { "job_id": "job-9" } }', { x: 0.6, y: 5.1, w: 7.4, h: 1.35, fontSize: 11 });
    L.note(s, 'warn', 'Supabase：user_metadata に依存する行の制御は危険。Txn-Token の rctx は TTS が書く環境の値で、要求時点の値として扱う', { x: 8.2, y: 5.1, w: 4.5, h: 1.35, size: 12, label: '' });
  }

  {
    const s = L.content('サイズの予算：上限を超えると黙って消える', {
      lead: '上限を超えたときの挙動は、エラー・失敗・置き換え・黙った欠落と、基盤ごとに違う',
      stages: [0, 1, 5],
      notes: 'トークンのサイズと、上限を超えたときの挙動です。表のとおり、基盤ごとに上限も挙動も違います。Firebase は独自クレームを 1000 バイトまでとし、超えるとエラーにします。Okta は groups が 100 件を超えるとリクエスト自体を失敗させます。Entra ID は、JWT で groups が 200 件を超えると groups を出さず、超過を示すクレームに置き換えます。危ないのは、黙って欠落するものです。GitLab の groups_direct は、200 件を超えると丸ごと省略され、0 件と区別できません。Cloudflare Access は、IdP 由来の属性を入れる custom クレームを、約 1KB を超えると末尾から切り捨て、大きくなりうる custom クレームを認可の判断に使わないよう明記しています。AWS のセッションタグも件数と容量の上限があり、超えると失敗します。組織では、クレームごとに最大の長さと件数を決め、超えたら発行を失敗させます。欠落しうる値では認可しません。長い一覧は、ID のような参照だけを載せます。『セキュアAPI』も、トークンの肥大化が HTTP ヘッダーの上限を超える原因になると指摘しています。',
      refs: { spec: 'Firebase・Okta・Entra・GitLab・Cloudflare Access・AWS 公式文書', book: '『セキュアAPI』7.7 節 pp.220–221（肥大とヘッダーの上限）' },
    });
    const red = (t) => ({ text: t, options: { color: HEX.accent3, bold: true } });
    L.table(s, [['基盤', '上限', '超えたとき'],
      ['Firebase', '独自クレーム 1000 バイト', 'エラー'],
      ['Okta', 'groups 100 件', 'リクエストが失敗'],
      ['Entra ID', 'groups 200 件（JWT）', '超過の印に置き換え'],
      ['GitLab', 'groups_direct 200 件', red('丸ごと省略（0 件と区別不能）')],
      ['Cloudflare Access', 'custom 約 1KB', red('末尾から切り捨て')],
      ['AWS', 'セッションタグ 50 件', '容量を超えると失敗'],
      ['Auth0', '独自クレーム 100KB', '重いペイロードを避けるよう注意']],
    { x: 0.6, y: 1.95, w: 8.0, colW: [2.1, 2.6, 3.3], fontSize: 12, rowH: 0.45 });
    L.card(s, { x: 8.85, y: 1.95, w: 3.85, h: 3.6, color: C.accent1, icon: 'MdStorage', title: 'サイズの予算', titleSize: 16, body: ['クレームごとに最大の長さ・件数', '超えたら発行を失敗させる', '欠落しうる値で認可しない', '長い一覧は ID だけ載せる'], bodySize: 13 });
    L.note(s, 'warn', 'Cloudflare は、大きくなりうる custom クレームを認可の判断に使わないよう明記している', { x: 0.6, y: 5.8, w: 12.1, h: 0.65, size: 13, label: '' });
  }

  {
    const s = L.content('前方互換：知らないものは無視、必須の欠落は拒否', {
      lead: '未知のクレームは、アプリが求めない限り無視する（MUST）。制限は受け手側の「必須」で効かせる',
      stages: [0, 3, 5],
      notes: '前方互換の規則です。RFC 7519 は、アプリケーションが別に求めない限り、受け手は理解できないクレームを無視しなければならないと定めています。Transaction Tokens の草案も同じです。このおかげで、新しいクレームを足しても、古い受け手は壊れません。しかし裏返すと、新しいクレームで制限をかけたつもりでも、古い受け手はそれを無視します。制限は、受け手が実装するまで効きません。RFC 8417 も、この性質が混乱のもとになりうると指摘しています。そこで、この「アプリが求めない限り」という条件を使い、受け手が判断に使うクレームは、受け手の側で必須と宣言し、無ければ拒否します。発行時フックの失敗などで欠けたまま発行されたトークンも、これで通さずに済みます。NIST IR 8587 は、トークンの種類ごとに必須の要素を文書化するよう求めています。なお、RFC 9396 は、発行者が、知らない type や知らないフィールドを含む authorization_details を拒否すると定めています。変更の順序も大切です。GitHub は、受け手の条件を先に作ってから発行側を変えるよう明記しています。変更の手順の詳細は Part 11 で扱います。',
      refs: { spec: 'RFC 7519 §4（求めない限り未知は無視）／RFC 8417 §4／RFC 9396 §5／Txn-Token 草案 11', inst: 'NIST IR 8587 §5.2.1.1（必須要素の文書化）', book: '『実践 Keycloak』5.6 節 p.86（必要なクレームを確認）' },
    });
    const cs = [['MdHelpOutline', C.accent1, '未知のクレーム', '無視する', ['RFC 7519 §4：別の要件が無ければ', '足しても古い受け手は壊れない']],
      ['MdNewReleases', C.accent2, '新しい制限のクレーム', '古い受け手は無視する', ['受け手の実装が先', '対応するまで制限は効かない']],
      ['MdBlock', C.accent3, '必須のクレームが無い', '拒否する（fail closed）', ['フックの失敗で欠けても通さない', '必須の一覧を台帳に書く']]];
    cs.forEach((c, i) => {
      L.card(s, { x: 0.6 + i * 4.1, y: 1.95, w: 3.9, h: 2.55, icon: c[0], color: c[1], title: c[2], titleSize: 15, body: [{ text: c[3], options: { bold: true, color: c[1], fontSize: 15, breakLine: true } }].concat(L.runs(c[4], { space: 4 })), bodySize: 12.5 });
    });
    L.flow(s, [{ t: '1. 受け手が先に対応' }, { t: '2. 発行を選択制に' }, { t: '3. 期日で既定に' }, { t: '4. 旧形式を廃止' }], { x: 0.6, y: 4.75, w: 12.1, h: 0.75, tSize: 14, fill: C.accent5 });
    L.note(s, 'tip', 'GitHub：受け手の条件を先に作ってから、発行側を変える。逆だとトークンが受け入れられない（手順は Part 11）', { x: 0.6, y: 5.7, w: 12.1, h: 0.75, size: 13, label: '' });
  }

  {
    const s = L.content('付与するのは単一の発行者：各サービスは足さない', {
      lead: '属性の源は多くても、クレームを書くのは 1 か所。受け手は、許可した発行者のクレームだけを信じる',
      stages: [1, 2, 3],
      notes: '誰がクレームを付与するかです。属性の源は、人事のディレクトリ、テナントや契約の管理、認証の結果など、複数あります。しかし、それをクレームとしてトークンに書くのは、組織の発行者 1 か所に限ります。具体的には、IdP か、入口でのトークン交換のサービスです。Curity は、API は中央のサーバーが主張したクレームだけを使い、自分で情報を足したりトークンを発行したりすべきでない、としています。OWASP の Identity Propagation Cheat Sheet も、アプリケーションのサービスを ID の発行者にしないこと、発行と検証の権限を分けることを求めています。NIST SP 800-162 は、属性の名前と値の正規化は中央の権限主体が管理すべきだとし、属性の源の数を減らす利点も挙げています。各サービスが独自にクレームを足すと、同じ名前で別の意味の値が生まれ、受け手はどれを信じればよいか分からなくなります。OWASP の JWT Cheat Sheet も、roles や groups などを、別の発行者が詐称することに注意するよう求めています。サービスの中で追加の文脈が必要なら、トークン交換や Transaction Tokens の発行サービスに書かせます。これは Part 6 で扱います。',
      refs: { spec: 'Curity API セキュリティのベストプラクティス', inst: 'OWASP Identity Propagation CS／NIST SP 800-162 §2.4.2・§3.3.2', book: '『デジタルアイデンティティのすべて』15.1.2 節 pp.260–261（考え方）' },
    });
    ['人事・ディレクトリ', 'テナント・契約の管理', '認証の結果（acr・amr）'].forEach((t, i) => {
      L.box(s, t, { x: 0.6, y: 2.0 + i * 0.8, w: 2.7, h: 0.6, fill: C.accent5, fontSize: 13 });
      L.arrow(s, 3.35, 2.3 + i * 0.8, 0.65, 'r', L.MUTED, 1.5);
      L.box(s, '受け手：サービス ' + 'ABC'[i], { x: 8.6, y: 2.0 + i * 0.8, w: 4.1, h: 0.6, fill: C.background2, color: C.text1, fontSize: 13 });
      L.arrow(s, 7.8, 2.3 + i * 0.8, 0.75, 'r', L.MUTED, 1.5);
    });
    L.box(s, [{ text: '組織の発行者', options: { bold: true, fontSize: 18, breakLine: true } }, { text: 'IdP、または入口のトークン交換', options: { fontSize: 12.5, bold: false, breakLine: true } }, { text: '名前・型・上限を台帳どおりに', options: { fontSize: 12.5, bold: false } }],
      { x: 4.05, y: 2.0, w: 3.7, h: 2.2, fill: C.accent1 });
    L.box(s, '× 各サービスが独自に追記・再発行', { x: 4.05, y: 4.35, w: 3.7, h: 0.55, fill: C.accent3, fontSize: 13 });
    L.T(s, '受け手は、許可した発行者のクレームだけを信じる', { x: 8.6, y: 4.35, w: 4.1, h: 0.55, fontSize: 13, bold: true, color: C.accent1, valign: 'middle', margin: 0 });
    L.note(s, 'leader', 'サービスの中で追加の文脈が要るなら、トークン交換や Transaction Tokens の発行サービスに書かせる（Part 6）', { x: 0.6, y: 5.15, w: 12.1, h: 1.0, size: 13.5 });
  }

  {
    const s = L.content('設計例：組織の名前空間オブジェクト', {
      lead: '登録名・名前空間・版・型・識別子・書き手の原則を、1 つのペイロードにまとめた例',
      stages: [0, 1],
      notes: 'ここまでの原則をまとめた設計例です。架空の組織のアクセストークンのペイロードを示します。ロールは、RFC 9068 の登録名である roles をトップレベルに置きます。登録名で意味が足りるものは、独自の名前を作りません。独自クレームは、自社が管理する https://claims.example.com/ を名前空間のキーとして、1 つのオブジェクトにまとめます。v は、このオブジェクトの構造の版です。Netflix の内部の ID 構造も、構造自体に版の番号を持たせています。テナントと部署は、名前ではなく ID で、すべて文字列です。部署は 1 つでも常に配列にします。このオブジェクトには、発行者が確かめた値だけを入れ、呼び出し側の申告は入れません。文書ごとの権限、氏名やメールのような個人情報は載せません。機微な情報の扱いは Part 9 で扱います。ネストを扱えない IdP のために、同じ内容をフラットな名前でも出せるよう、台帳には両方の形を定義しておきます。NIST IR 8112 が示す属性のメタデータ、つまり説明、許容値、形式、鮮度などは、台帳の項目の雛形として使えます。',
      refs: { spec: 'RFC 7519 §4.2／RFC 9068 §2.2.3.1（roles）', inst: 'NIST IR 8112 §3.1（属性スキーマのメタデータ）／DS-212 §3.2.3', book: '『セキュアAPI』7.2.2 節 p.195（ロール・組織を独自クレームで）' },
    });
    L.code(s, '{\n  "iss": "https://idp.example.com",  "sub": "u-7f3a…",\n  "aud": "https://api.example.com",  "roles": ["approver"],\n  "https://claims.example.com/": {\n    "v": "1",\n    "tenant_id": "t-042",\n    "org_unit_ids": ["ou-12", "ou-31"],\n    "employment": "regular"\n  }\n}', { x: 0.6, y: 1.95, w: 6.6, h: 2.75, fontSize: 11 });
    L.table(s, [['原則', 'この例での決め方'],
      ['登録名を優先', 'roles は RFC 9068 の名前でトップに'],
      ['名前空間', '自社の URI を 1 つのオブジェクトに'],
      ['版', 'v で構造の版を示す'],
      ['型', 'ID は文字列、複数値は常に配列'],
      ['識別子', 'テナント・部署は ID。名前は載せない'],
      ['書き手', '発行者が確かめた値だけ'],
      ['載せないもの', '文書ごとの権限、氏名・メール']],
    { x: 7.45, y: 1.95, w: 5.25, colW: [1.65, 3.6], fontSize: 12, rowH: 0.5 });
    L.note(s, 'tip', 'ネストできない IdP 向けに、同じ内容のフラットな名前（https://claims.example.com/tenant_id）も台帳に定義しておく', { x: 0.6, y: 4.9, w: 6.6, h: 1.15, size: 12.5, label: '' });
  }

  {
    const s = L.content('設計のチェックリスト：12 の確認', {
      lead: '新しい独自クレームを足す前に、設計の観点で確かめること。審査の質問は Part 11 で扱う',
      stages: [0, 5],
      notes: 'Part 4 のまとめとして、設計の観点のチェックリストを 12 項目にしました。左の 6 項目は、載せるかどうかと、名前と形の確認です。認可に使い、寿命の間に変わらない値か。登録名や IdP の既存のクレームで足りないか。自社の名前空間に入れて予約名と照合したか。受け手の全ツールで参照できるか。型は 1 つに決まり、ID は文字列か。複数値は配列で、区切り文字の連結や JSON の文字列化をしていないか。右の 6 項目は、意味と運用の確認です。無い、null、false、空配列の意味を決めたか。大文字小文字の扱いを決め、完全一致で比べるか。名前ではなく変わらない ID か。誰が値を書けるかを決め、申告の値と分けたか。上限と、超えたときの挙動を決めたか。必須のクレームが欠けたら拒否し、付与は単一の発行者に限っているか。新しい共有クレームの提案を審査するための 25 の質問は、Part 11 で扱います。',
      refs: { spec: 'RFC 7519 §4／RFC 9068 §2.2.2', inst: 'NIST SP 800-162 §2.4.2／IR 8587 §5.2.1.1／デジタル庁 DS-212 §3.2.3', book: '『実践 Keycloak』8.2 節 p.146（最小限のロールだけ）' },
    });
    const left = [['観点', '確認すること'], ['載せるか', '認可に使い、寿命の間に変わらないか'], ['既存', '登録名・IdP の既存クレームで足りないか'], ['名前', '自社の名前空間か。予約名と照合したか'],
      ['ツール', '受け手の全ツールで参照できるか'], ['型', '型は 1 つか。ID は文字列か'], ['形', '複数値は配列か。連結・文字列化していないか']];
    const right = [['観点', '確認すること'], ['欠落', '無い・null・false・空配列の意味を決めたか'], ['比較', '大小の扱いを決め、完全一致で比べるか'], ['識別子', '名前ではなく、変わらない ID か'],
      ['書き手', '誰が書けるか。申告の値と分けたか'], ['サイズ', '上限と、超えたときの挙動を決めたか'], ['必須', '欠けたら拒否するか。発行者は 1 つか']];
    L.table(s, left, { x: 0.6, y: 1.95, w: 5.95, colW: [1.3, 4.65], fontSize: 12.5, rowH: 0.5, headFill: C.accent1 });
    L.table(s, right, { x: 6.75, y: 1.95, w: 5.95, colW: [1.3, 4.65], fontSize: 12.5, rowH: 0.5, headFill: C.accent1 });
    L.note(s, 'leader', '1 つでも答えられない項目があれば、まだトークンに載せない。答えは台帳に残し、受け手と共有する', { x: 0.6, y: 5.75, w: 12.1, h: 0.75, size: 13.5 });
  }
};
