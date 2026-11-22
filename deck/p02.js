// Part 2: map of existing claims (what already exists, what it does NOT mean, where the legitimate gaps are)
module.exports = (L) => {
  const { C, SH, HEX } = L;
  L.section('Part 2 既存のクレームの地図');
  L.divider('PART 2', '既存のクレームの地図：独自クレームを作る前に', '同じ意味のクレームを作り直さない。既存の名前と衝突させない。既存のクレームが「意味しないこと」に隙間がある',
    ['どのクレームが既に標準で決まっているか', '既存のクレームは、何を意味し、何を意味しないか', '標準の登録簿にない用途はどれか', '独自クレームを作る前に、どこを探すか'],
    'Part 2 は、既に存在するクレームの地図です。独自クレームを設計する前に、同じ意味のクレームが標準や IdP に既にないかを知っておく必要があります。知らずに作ると、同じ意味のクレームが二重にできたり、標準の名前と衝突したりします。この Part では、RFC 7519 の登録クレームと名前の 3 区分から始め、利用者の識別、テナント、役割、権限、認証の強さ、委任など、用途ごとに既存のクレームを見ていきます。それぞれについて、何を意味し、何を意味しないか、そして独自クレームが正当化される隙間はどこかを整理します。最後に、標準の登録簿にない用途、SAML の属性との対応、独自クレームを作る前の確認手順を扱います。', { id: 'p02-part' });

  {
    const s = L.content('登録クレーム：7 つの意味と、意味しないこと', { id: 'p02-registered-claims',
      lead: 'RFC 7519 が定める基本の 7 つ。どれも意味は狭く、受け手の確認の仕方まで決まっている',
      stages: [0, 3],
      notes: 'RFC 7519 は、7 つのクレームを登録クレームとして定めています。iss は発行者、sub は主体、aud は受け手、exp・nbf・iat は時刻、jti はトークンの一意な ID です。大事なのは、それぞれの意味が狭いことです。たとえば sub は「発行者の中で」一意な主体であって、発行者をまたいで一意ではありません。だから sub は必ず iss と組で使います。aud は文字列の場合も配列の場合もあり、受け手は自分が含まれていなければ拒否しなければなりません。iat は発行時刻で、利用者が認証した時刻ではありません。認証した時刻は auth_time という別のクレームです。jti は複数の発行者の間でも衝突しないように割り当てる必要があります。RFC 9068 の JWT アクセストークンでは、この中の iss・exp・aud・sub・iat・jti に client_id を加えた 7 つが必須です。独自クレームで、これらと同じ意味のものを別名で作らないことが第一歩です。',
      refs: { spec: 'RFC 7519 §4.1／RFC 9068 §2.2（必須クレーム）', inst: 'OWASP JWT Cheat Sheet／NIST SP 800-63C-4 §3.4', book: '『セキュアAPI』7.2.2 節 pp.194–195' },
    });
    L.table(s, [['クレーム', '意味', '型', '意味しないこと・注意'],
      ['iss', 'トークンを発行した主体', '文字列（StringOrURI）', '完全一致で比べる。部分一致で受け入れない'],
      ['sub', '発行者の中で一意な主体', '文字列（StringOrURI）', '発行者をまたいで一意ではない。iss と組で使う'],
      ['aud', '受け手', '文字列か配列', '自分が含まれなければ拒否。両方の形を受け付ける'],
      ['exp', 'この時刻以降は受け入れない', '数値（秒）', 'ずれの許容は数分まで'],
      ['nbf', 'この時刻より前は受け入れない', '数値（秒）', '同上'],
      ['iat', '発行した時刻', '数値（秒）', '認証した時刻ではない（auth_time は別）'],
      ['jti', 'トークンの一意な ID', '文字列', '発行者をまたいでも衝突させない。リプレイ検知に使える']],
    { x: 0.6, y: 1.95, w: 12.1, colW: [1.3, 3.4, 1.9, 5.5], fontSize: 12.5, rowH: 0.48 });
    L.note(s, 'tip', 'RFC 9068 のアクセストークンでは iss・exp・aud・sub・client_id・iat・jti が必須。これらと同じ意味の独自クレームを別名で作らない', { x: 0.6, y: 5.95, w: 12.1, h: 0.6, size: 13, label: '' });
  }

  {
    const s = L.content('名前の 3 区分：登録名・公開名・私的名', { id: 'p02-name-categories',
      lead: '新しい名前は IANA に登録するか、自分が管理する名前空間を含む「公開名」にする',
      stages: [0],
      notes: 'RFC 7519 は、クレームの名前を 3 つに分けています。1 つ目は登録名で、IANA の JSON Web Token Claims の登録簿に載った名前です。登録には仕様が必要で、専門家が既存の機能との重複や汎用性を審査します。組織固有のクレームは、通常この対象になりません。2 つ目は公開名で、衝突しない名前です。自分が管理するドメインの URI のように、他者と重ならない名前空間を含めます。組織で共用する独自クレームは、基本的にこの形にします。3 つ目は私的名で、発行者と受け手が合意しただけの名前です。登録も衝突回避もしないので、衝突のおそれがあり、慎重に使うべきとされています。RFC 9068 は、アクセストークンについて、登録名で意味が十分に表せる属性はその登録名を使うべきだとしています。つまり、まず登録簿を探し、無ければ公開名を作る、という順序になります。',
      refs: { spec: 'RFC 7519 §4.1–4.3・§10.1／RFC 9068 §2.2.2', inst: 'NIST SP 800-162 §2.4.2（属性の名前を正規化し中央で管理）', book: '『デジタルアイデンティティのすべて』10.2.1 節 p.136（識別子の名前空間の考え方）' },
    });
    const cards = [
      ['MdFactCheck', C.accent1, '登録名（Registered）', ['IANA の登録簿に載った名前', '登録には仕様と専門家の審査が要る', '組織固有のクレームは通常対象外']],
      ['MdLabel', C.accent4, '公開名（Public）', ['衝突しない名前を含む', '自社ドメインの URI など', '組織で共用する独自クレームの基本形']],
      ['MdWarning', C.accent3, '私的名（Private）', ['発行者と受け手の合意だけ', '登録も衝突回避もしない', '閉じた範囲だけで、慎重に使う']],
    ];
    cards.forEach((c, i) => {
      L.card(s, { x: 0.6 + i * 4.1, y: 1.95, w: 3.9, h: 2.1, icon: c[0], color: c[1], title: c[2], titleSize: 15, body: c[3], bodySize: 12.5 });
    });
    L.code(s, ['{', '  "iss": "https://idp.example.com",', '  "sub": "u-7f3a…",', '  "roles": ["approver"],                          // 登録名', '  "https://claims.example.com/tenant": "t-042",  // 公開名', '  "dept": "sales"                                 // 私的名（避ける）', '}'].join('\n'), { x: 0.6, y: 4.25, w: 7.0, h: 2.2, fontSize: 11 });
    L.note(s, 'tip', 'RFC 9068：登録名で意味が十分に表せる属性は、その登録名を使う（SHOULD）。まず登録簿を探し、無ければ公開名を作る', { x: 7.8, y: 4.25, w: 4.9, h: 2.2, size: 13.5, label: '' });
  }

  {
    const s = L.content('用途別の地図：16 の用途と既存のクレーム', { id: 'p02-claims-by-purpose',
      lead: '多くの用途には既に登録クレームがある。登録簿にないのは、テナント・同意と目的・端末と場所',
      stages: [0],
      notes: '独自クレームが欲しくなる用途を 16 に分けて、既存のクレームを並べた地図です。緑の用途には、標準で登録されたクレームがあり、名前も意味も決まっています。青の用途は、名前は登録されているものの、値の語彙や構造の中身は使う側が決める必要があるものです。役割やグループの値、authorization_details の type などがこれにあたります。赤の用途には、汎用の登録クレームがありません。テナントと組織、同意と目的、端末や IP アドレスや場所です。これらは各社の IdP が独自のクレームを持っていて、名前も形もばらばらです。独自クレームが正当化されるのは、主にこの赤の領域と、青の領域の値の語彙です。緑の領域で独自クレームを作るのは、多くの場合、既存のクレームの作り直しになります。次のスライドから、用途ごとに中身を見ていきます。',
      refs: { spec: 'IANA JSON Web Token Claims（2026-10-28 版）／RFC 9068 §2.2', inst: 'NIST SP 800-162 §3.2.1.3（属性の定義と意味の文書化）', book: '『OpenID Connect入門』4.2.2・4.3 節 pp.62, 67' },
    });
    const G = C.accent1, B = C.accent5, R = C.accent3;
    const cells = [
      ['利用者の識別', 'iss＋sub、sub_id', G], ['テナント・組織', '登録なし（tid・org_id は各社）', R], ['役割・グループ・資格', 'roles・groups・entitlements', B], ['権限', 'scope', G],
      ['細かい認可', 'authorization_details', B], ['認証の強さ', 'acr・amr・auth_time', G], ['セッション', 'sid', G], ['委任', 'act・may_act', G],
      ['クライアント', 'client_id・azp', G], ['鍵の保持', 'cnf', G], ['イベント・相関', 'events・toe・txn', G], ['同意・目的', '登録なし', R],
      ['ロケール・プロフィール', 'locale・name ほか', G], ['端末・IP・場所', '登録なし（ipaddr は各社）', R], ['本人確認済みの属性', 'verified_claims', G], ['失効状態', 'status・status_list（草案）', G],
    ];
    const bw = (12.1 - 3 * 0.15) / 4;
    cells.forEach((c, i) => {
      const col = i % 4, row = Math.floor(i / 4);
      L.box(s, [{ text: (i + 1) + '  ' + c[0], options: { bold: true, fontSize: 13, breakLine: true } }, { text: c[1], options: { fontSize: 11, bold: false } }], { x: 0.6 + col * (bw + 0.15), y: 1.95 + row * 1.0, w: bw, h: 0.88, fill: c[2] });
    });
    const leg = [[G, '標準の登録クレームがある'], [B, '名前は登録済み。値の語彙・構造は組織で決める'], [R, '汎用の登録クレームがない（独自クレームの候補）']];
    let lx = 0.6;
    leg.forEach(([col, t], i) => {
      s.addShape(SH.ROUNDED_RECTANGLE, { x: lx, y: 6.07, w: 0.3, h: 0.3, rectRadius: 0.05, fill: { color: col }, line: { color: col } });
      const w = [2.3, 3.8, 3.8][i];
      L.T(s, t, { x: lx + 0.38, y: 6.02, w, h: 0.4, fontSize: 11.5, margin: 0, valign: 'middle' });
      lx += w + 0.68;
    });
  }

  {
    const s = L.content('利用者の識別：安定したキーは iss と sub の組だけ', { id: 'p02-user-identifier',
      lead: 'email・preferred_username・name は変わり、再利用されうる。一意のキーにしない（MUST NOT）',
      stages: [0, 4],
      notes: '利用者を識別するクレームです。OpenID Connect Core は、iss と sub の組だけが、受け手が安定した識別子として頼れる唯一のクレームだとしています。sub は発行者の中で一意で、別の人に再割り当てされません。一方、email、preferred_username、phone_number、name は、一意のキーとして使ってはならないと MUST NOT で定めています。発行者は、同じメールアドレスを時期を変えて別の利用者に使ってよいからです。もう 1 つの注意は、ペアワイズの sub です。クライアントごとに違う sub を出す方式で、Entra ID の sub もアプリごとに値が違います。Entra ではテナント内でアプリをまたいで同じ値になる oid を使います。構造を持つ識別子が必要なら、RFC 9493 の sub_id があります。sub と両方あるときは同じ主体を指し、両方を組み合わせて主体を決めてはいけません。独自クレームの隙間は、複数の IdP やペアワイズの sub をまたいで、社内で同じ人を指す安定したキー、たとえば社員番号のようなものです。',
      refs: { spec: 'OIDC Core §2・§5.7・§8／RFC 9493 §4.1', inst: 'NIST SP 800-63C-4 §3.4・§4.9／OWASP ASVS 10.5.2', book: '『実践 Keycloak』2.4 節 p.24／『デジタルアイデンティティのすべて』（考え方）10.2.2 節 p.139' },
    });
    L.table(s, [['クレーム', '意味', '意味しないこと'],
      ['sub', '発行者の中で一意。再割り当てしない', '発行者をまたいだ一意性。ペアワイズならアプリごとに違う'],
      ['email', '連絡先のメールアドレス', '一意のキー。別人に再利用されうる'],
      ['preferred_username・name', '表示用の名前', '一意のキー。変わらないこと'],
      ['sub_id（RFC 9493）', '形式つきの構造化された識別子', 'sub と別の主体。sub と組み合わせて主体を決めること'],
      ['oid（Entra、各社独自）', 'テナント内でアプリをまたいで同じ', '別のテナントでも同じ値']],
    { x: 0.6, y: 1.95, w: 8.0, colW: [2.5, 2.6, 2.9], fontSize: 12, rowH: 0.62 });
    L.card(s, { x: 8.9, y: 1.95, w: 3.8, h: 2.4, color: C.accent4, icon: 'MdPerson', title: '独自クレームの隙間', titleSize: 15, body: ['複数の IdP をまたぐ社内の安定キー', 'ペアワイズの sub をまたぐ突き合わせ', '例：社員番号（変わらない ID）'], bodySize: 12.5 });
    L.note(s, 'warn', 'メールアドレスをキーにすると、再利用や変更で別人と取り違える（冒頭の事故例、スライド 5 の nOAuth）', { x: 8.9, y: 4.5, w: 3.8, h: 1.25, size: 12.5, label: '' });
    L.note(s, 'leader', '名前と ID を分ける。キーは「iss＋sub」か、組織が決めた変わらない ID だけ', { x: 0.6, y: 5.85, w: 12.1, h: 0.62, size: 13, label: '' });
  }

  {
    const s = L.content('テナント・組織：登録クレームはなく、各社が独自', { id: 'p02-tenant-org',
      lead: 'テナントを表す標準のクレームはない。先に aud と iss をテナントごとに分けられないかを考える',
      stages: [0, 3, 4],
      notes: 'テナントや組織を表すクレームは、IANA の登録簿にありません。tenant、organization、tid に相当する登録クレームは、2026 年 10 月 28 日版の登録簿でも見当たりません。そのため、各社の IdP が独自のクレームを持っています。Entra ID の tid はテナントの GUID で、マルチテナントでは iss と突き合わせて検証します。Auth0 は Organizations の機能でログインしたときに org_id を入れ、org_id で検証することを勧めています。Keycloak は organization スコープを要求すると organization クレームを出します。名前も形もばらばらです。標準の代わりの手段もあります。RFC 8707 は、マルチテナントの API ではテナントを含む resource の URI を使って aud を分けるよう勧めています。また RFC 8725 は、発行者を分けて検証規則を互いに排他にする戦略を挙げています。テナントは独自クレームの正当な候補ですが、テナントのクレームだけで分離するのではなく、aud や iss の分離と組み合わせます。',
      refs: { spec: 'RFC 8707 §3／RFC 8725 §3.8（鍵は発行者のもの）／IANA JWT Claims（tenant 相当なし）', inst: 'NIST IR 8587 §5.2.1.2（テナント単位の鍵）／CSRB 勧告 6', book: '『実践 Keycloak』1.4.1.1・4.3 節 pp.11, 46（レルムと iss）' },
    });
    L.table(s, [['IdP', 'クレーム', '入る条件と注意'],
      ['Entra ID', 'tid', 'テナントの GUID。iss と突き合わせ、データのキーに含める'],
      ['Auth0', 'org_id（org_name）', 'Organizations 経由のログイン時。org_id で検証する'],
      ['Keycloak', 'organization', 'organization スコープを要求したとき。別名をキーにしたオブジェクト']],
    { x: 0.6, y: 1.95, w: 7.6, colW: [1.5, 2.1, 4.0], fontSize: 12.5, rowH: 0.62 });
    L.code(s, ['"tid": "9c1e…"                          // Entra', '"org_id": "org_9a…"                     // Auth0', '"organization": { "acme": { "id": "…" } } // Keycloak'].join('\n'), { x: 0.6, y: 4.6, w: 7.6, h: 1.1, fontSize: 11 });
    L.card(s, { x: 8.5, y: 1.95, w: 4.2, h: 3.75, color: C.accent1, icon: 'MdApartment', title: '標準の代わりの手段', titleSize: 15, body: [['aud を分ける：', 'テナントを含む resource の URI（RFC 8707）'], ['iss を分ける：', 'テナントごとの発行者と鍵。鍵と発行者を照合（RFC 8725 §3.8）'], ['独自クレーム：', '上の 2 つと組み合わせて使う']], bodySize: 12.5 });
    L.note(s, 'leader', 'テナントは独自クレームの正当な候補。ただしクレームだけで分離せず、aud・iss・鍵の分離と重ねる（Part 5）', { x: 0.6, y: 5.85, w: 12.1, h: 0.62, size: 13, label: '' });
  }

  {
    const s = L.content('役割・グループ・資格：名前は標準、語彙は組織で', { id: 'p02-roles-groups-entitlements',
      lead: 'RFC 9068 は roles・groups・entitlements の名前を勧める。値の語彙と認可モデルは定めない',
      stages: [0, 4],
      notes: '役割、グループ、資格については、RFC 9068 が、SCIM の RFC 7643 で定義された roles、groups、entitlements という名前を使うよう勧めています。名前は標準ですが、中身はほとんど決まっていません。groups は利用者が直接または入れ子で所属するグループで、認可のモデルは定義されていません。roles は利用者が何者かを表すラベル、entitlements は利用者が持つ権利で、どちらも語彙も構文も決まっていません。つまり、同じ admin という文字列でも、受け手によって意味が違いえます。ここが組織で決めるべき部分です。値の語彙を、URI の名前空間などで組織として定義します。SAML の世界では、eduPersonEntitlement が権利を URI で表す先例です。また、IdP によってクレームの位置も違います。Keycloak は realm_access や resource_access の中、Auth0 は permissions、Cognito は cognito:groups です。グループを全件載せるとトークンが大きくなる点にも注意が要ります。',
      refs: { spec: 'RFC 9068 §2.2.3.1／RFC 7643 §4.1.2／eduPerson 2020-01 §2.2.2', inst: 'OWASP JWT Cheat Sheet（roles・groups は別発行者の詐称に注意）', book: '『実践 Keycloak』8.2・8.3.1 節 pp.146–152' },
    });
    const cs = [['MdGroups', 'groups', ['所属するグループ', '直接・入れ子・動的', '認可モデルは定めない']], ['MdBadge', 'roles', ['利用者が何者か', '例：Student', '語彙も構文もない']], ['MdKey', 'entitlements', ['利用者が持つ権利', '語彙も構文もない', 'SAML は URI の先例あり']]];
    cs.forEach((c, i) => {
      L.card(s, { x: 0.6 + i * 2.75, y: 1.95, w: 2.55, h: 2.35, icon: c[0], color: C.accent5, title: c[1], titleSize: 15, body: c[2], bodySize: 12 });
    });
    L.code(s, ['"roles": [', '  "https://claims.example.com/roles/billing-admin"', '],', '"groups": ["g-1203", "g-2210"]'].join('\n'), { x: 0.6, y: 4.5, w: 7.95, h: 1.3, fontSize: 11 });
    L.card(s, { x: 8.9, y: 1.95, w: 3.8, h: 3.85, color: C.accent3, icon: 'MdCallSplit', title: '意味しないこと', titleSize: 15, body: ['同じ文字列が、どの受け手でも同じ意味', 'IdP の roles が同じ位置・意味', 'グループが全件入っていること（Part 3）'], bodySize: 12.5 });
    L.note(s, 'leader', '名前は roles・groups・entitlements を使い、値の語彙を組織の名前空間で定義する。これが独自に決める部分', { x: 0.6, y: 5.95, w: 12.1, h: 0.6, size: 13, label: '' });
  }

  {
    const s = L.content('権限：scope はクライアントに許した範囲', { id: 'p02-scope',
      lead: 'scope は利用者の全権限ではない。取引単位の細かい認可は authorization_details で表す',
      stages: [0, 4],
      notes: '権限を表すクレームです。scope は RFC 8693 で定義された、空白区切りの文字列です。RFC 9068 は、各スコープが aud の示すリソースにとって意味を持たなければならないとしています。ここでよくある誤解は、scope を利用者の権限の一覧だと思うことです。scope は、利用者がクライアントに委ねた範囲であって、利用者が持つ全権限ではありません。ある利用者が管理者であっても、クライアントに読み取りのスコープしか許していなければ、そのトークンでは読み取りしかできません。もっと細かい、取引単位の認可には、RFC 9396 の authorization_details があります。type が必須で、actions、locations などの共通の項目を持つオブジェクトの配列です。JWT のアクセストークンには、その受け手向けに絞った authorization_details を入れることが勧められています。独自の「権限オブジェクト」のクレームを作る前に、authorization_details の type として定義できないかを検討します。type には自分が管理する URI を使うことが勧められています。',
      refs: { spec: 'RFC 9068 §2.2.3／RFC 8693 §4.2／RFC 9396 §2・§3.1・§9.1', inst: 'NIST IR 8587 §5.2.1.1（scope と RAR）', book: '『OpenID Connect入門』5.2.1 節 pp.74–75' },
    });
    L.card(s, { x: 0.6, y: 1.95, w: 5.4, h: 3.55, color: C.accent1, icon: 'MdRule', title: 'scope', titleSize: 16, body: [['形：', '空白区切りの文字列（Okta は scp という配列）'], ['意味：', 'クライアントに委ねた範囲'], ['規則：', '各スコープは aud のリソースにとって意味を持つ'], ['意味しない：', '利用者が持つ全権限']], bodySize: 12.5 });
    L.T(s, 'authorization_details（RFC 9396）', { x: 6.3, y: 1.95, w: 6.4, h: 0.4, fontSize: 15, bold: true, margin: 0 });
    L.code(s, ['"authorization_details": [{', '  "type": "https://claims.example.com/rar/payment",', '  "actions": ["initiate"],', '  "locations": ["https://api.example.com/payments"],', '  "instructedAmount": { "currency": "JPY", "amount": "120000" }', '}]'].join('\n'), { x: 6.3, y: 2.4, w: 6.4, h: 1.9, fontSize: 11 });
    L.T(s, L.runs(['type は必須。自分が管理する URI を勧める', '受け手向けに絞って入れる', '同じ API では scope か authorization_details の一方（RECOMMENDED）']), { x: 6.3, y: 4.4, w: 6.4, h: 1.1, fontSize: 12.5, margin: 0 });
    L.note(s, 'leader', '独自の「権限オブジェクト」を作る前に、authorization_details の type として定義できないかを検討する（Part 5）', { x: 0.6, y: 5.7, w: 12.1, h: 0.75, size: 13 });
  }

  {
    const s = L.content('認証の強さとセッション：acr・amr・auth_time・sid', { id: 'p02-auth-strength-session',
      lead: 'amr は使った方式、acr は保証の水準。値は認証時に固まり、リフレッシュでは変わらない',
      stages: [0, 3, 4],
      notes: '認証の強さとセッションのクレームです。acr は認証の保証クラスで、値の意味は当事者の間で合意しておく必要があります。amr は実際に使った認証方式の配列で、RFC 8176 が pwd、otp、mfa などの値を定めています。amr に mfa が入っていても、それは方式の事実であって、保証の水準を意味しません。水準を伝えるのは acr です。auth_time は利用者が認証した時刻で、トークンの発行時刻 iat とは別物です。再認証なしにトークンが再発行されることがあるからです。RFC 9068 では、これらの値は認可応答の時点で固まり、リフレッシュやトークン交換でも変わりません。sid は IdP 側のセッションの ID で、アプリのセッション ID ではありません。また、ID トークンの exp はログインセッションの寿命とは関係ありません。認証が足りないとき、API は RFC 9470 の insufficient_user_authentication で追加の認証を求められます。独自に決める部分は、組織の acr の値の語彙です。',
      refs: { spec: 'OIDC Core §2／RFC 8176 §2／RFC 9068 §2.2.1／RFC 9470 §3', inst: 'NIST SP 800-63C-4 §2.5・§4.9（xAL と認証時刻）', book: '『OpenID Connect入門』4.3 節 p.67' },
    });
    L.table(s, [['クレーム', '意味', '意味しないこと'],
      ['acr', '認証の保証クラス。値の意味は合意で決める', '合意のない値どうしの比較'],
      ['amr', '使った認証方式の配列（pwd・otp・mfa…）', '保証の水準（mfa ≠ 高い保証）'],
      ['auth_time', '利用者が認証した時刻', '発行時刻（iat）。再認証なしの再発行がある'],
      ['sid', 'IdP 側のセッションの ID', 'アプリのセッションの ID'],
      ['ID トークンの exp', 'トークンの有効期限', 'ログインセッションの寿命']],
    { x: 0.6, y: 1.95, w: 7.6, colW: [1.8, 3.1, 2.7], fontSize: 12, rowH: 0.62 });
    L.T(s, '足りないときの応答（RFC 9470）', { x: 8.5, y: 1.95, w: 4.2, h: 0.4, fontSize: 14, bold: true, margin: 0 });
    L.code(s, ['HTTP/1.1 401 Unauthorized', 'WWW-Authenticate: Bearer', ' error="insufficient_user_', '  authentication",', ' acr_values="…/loa/2",', ' max_age=300'].join('\n'), { x: 8.5, y: 2.4, w: 4.2, h: 2.1, fontSize: 11 });
    L.note(s, 'tip', '値は認証時に固まり、リフレッシュでも変わらない（RFC 9068）', { x: 8.5, y: 4.65, w: 4.2, h: 1.05, size: 12.5, label: '' });
    L.note(s, 'leader', '独自に決めるのは acr の値の語彙。どの値がどの水準かを台帳で定め、amr の mfa を水準の代わりにしない', { x: 0.6, y: 5.85, w: 12.1, h: 0.62, size: 13, label: '' });
  }

  {
    const s = L.content('委任とクライアント：sub は代理される主体', { id: 'p02-delegation-client',
      lead: 'act は今の行為者、may_act は代理してよい者。client_id はトークンを要求したクライアント',
      stages: [0, 2, 4],
      notes: '委任とクライアントのクレームです。RFC 8693 のトークン交換で委任が起きると、トークンの最上位の sub は代理される主体、つまり利用者のままで、実際に行動している者は act の中に入ります。act は入れ子にでき、いちばん外側が今の行為者、内側ほど以前の行為者です。アクセス制御に使ってよいのは、最上位のクレームと、いちばん外側の act だけで、以前の行為者は参考情報です。act の中には識別のためのクレームだけを入れ、exp や aud のようなクレームは意味を持ちません。may_act は、ある者が代理の行為者になってよいという表明で、交換の際に認可サーバーが判断に使います。client_id はトークンを要求したクライアントで、RFC 9068 のアクセストークンでは必須です。azp は OpenID Connect の ID トークンのクレームで、Keycloak はアクセストークンにも azp を入れます。委任の理由や承認者は標準にないので独自の候補ですが、act の中に権限の情報を入れてはいけません。',
      refs: { spec: 'RFC 8693 §4.1–4.4／RFC 9068 §2.2／OIDC Core §2（azp）', inst: 'OIDF「Agentic AI のアイデンティティ管理」§2.11', book: '『OpenID Connect入門』4.2.2 節 p.62（Keycloak は azp）' },
    });
    L.code(s, ['{', '  "sub": "u-7f3a…",               // 代理される利用者', '  "client_id": "portal",', '  "act": {', '    "sub": "svc-orders",           // 今の行為者', '    "act": { "sub": "agent-17" }   // 以前の行為者', '  }', '}'].join('\n'), { x: 0.6, y: 1.95, w: 6.2, h: 2.6, fontSize: 11 });
    L.table(s, [['クレーム', '意味', '注意'],
      ['act', '今の行為者（入れ子で履歴）', '認可は最上位と最も外側の act だけ'],
      ['may_act', '代理してよい者の表明', '交換時に認可サーバーが使う'],
      ['client_id', '要求したクライアント', 'RFC 9068 で必須'],
      ['azp', 'ID トークンの発行先', 'Keycloak は AT にも入れる']],
    { x: 7.0, y: 1.95, w: 5.7, colW: [1.15, 2.05, 2.5], fontSize: 11.5, rowH: 0.52 });
    L.card(s, { x: 0.6, y: 4.85, w: 6.2, h: 1.65, color: C.accent4, icon: 'MdLightbulb', title: '独自クレームの隙間', titleSize: 14, body: ['委任の理由・承認者（act の外に置く）', '利用者のトークンかアプリのトークンかの明示'], bodySize: 12.5 });
    L.note(s, 'warn', 'sub だけを見ると、エージェントや別サービス経由の操作を本人の操作と区別できない。act の中に権限を入れない（Part 5・10）', { x: 7.0, y: 4.85, w: 5.7, h: 1.65, size: 12.5, label: '' });
  }

  {
    const s = L.content('鍵・イベント・本人確認：既存の構造を使う', { id: 'p02-keys-events-identity-assurance',
      lead: '端末への結び付けは cnf、相関の ID は txn、確認済みの属性は verified_claims が既にある',
      stages: [0, 3],
      notes: '独自クレームで作り直されやすい 3 つの領域です。1 つ目は鍵の保持です。RFC 7800 の cnf は、トークンを提示した者が特定の鍵を持っていることを確かめるためのクレームです。DPoP では鍵のサムプリントを jkt、mTLS では証明書のサムプリントを x5t#S256 として入れます。cnf には鍵を 1 つだけ入れます。独自の「端末への結び付け」のクレームを作る前に、cnf を使います。2 つ目はイベントと相関です。RFC 8417 のセキュリティイベントトークンは events、toe、txn を定めています。txn は関連する複数の JWT を相関させる ID で、イベントトークン以外の JWT でも使えます。3 つ目は本人確認済みの属性です。2024 年に Final になり、2026 年 7 月に最初の正誤表が承認された OpenID Identity Assurance の verified_claims は、確認の枠組みや方法を表す verification と、確認済みの claims を組で持ちます。目的は、確認済みの属性と未確認の属性を受け手が混同しないことです。email_verified は、確認した時点でそのメールを管理していたことしか意味しません。',
      refs: { spec: 'RFC 7800 §3.1／RFC 8417 §2.2／OpenID IDA Schema 1.0 §5', inst: 'NIST SP 800-63C-4 §3.14（bearer と鍵の保持）', book: '『セキュアAPI』7.5 節 pp.212–216（cnf）' },
    });
    const cs = [
      ['MdKey', C.accent1, 'cnf（鍵の保持）', ['提示者が特定の鍵を持つことの確認', 'DPoP は jkt、mTLS は x5t#S256', '入れる鍵は 1 つだけ', '独自の端末の結び付けを作らない']],
      ['MdHistory', C.accent5, 'events・toe・txn', ['セキュリティイベント（RFC 8417）', 'txn は他の JWT でも使える相関 ID', 'イベントトークンには exp を入れない（推奨）']],
      ['MdVerifiedUser', C.accent4, 'verified_claims', ['OpenID Identity Assurance（2024 Final、2026-07 正誤表）', 'verification と確認済みの claims の組', '未確認の given_name 等と混同させない']],
    ];
    cs.forEach((c, i) => {
      L.card(s, { x: 0.6 + i * 4.1, y: 1.95, w: 3.9, h: 3.2, icon: c[0], color: c[1], title: c[2], titleSize: 15, body: c[3], bodySize: 12.5 });
    });
    L.note(s, 'warn', 'email_verified が true でも、意味は「確認した時点でそのメールを管理していた」だけ。本人確認済みを意味しない', { x: 0.6, y: 5.35, w: 12.1, h: 0.62, size: 13, label: '' });
    L.T(s, '独自の名前で作り直す前に、既存の構造で表せないかを確かめる', { x: 0.6, y: 6.05, w: 12.1, h: 0.42, fontSize: 13.5, bold: true, color: C.accent1, margin: 0, valign: 'middle' });
  }

  {
    const s = L.content('標準の登録簿にないもの：テナント・同意・端末', { id: 'p02-not-in-registry',
      lead: '似た名前の登録クレームはあるが、意味が違う。ここが独自クレームの正当な隙間',
      stages: [0],
      notes: '汎用の登録クレームがない用途を、改めて整理します。テナントと組織は、前に見たとおり各社が tid、org_id、organization という独自のクレームを持っています。同意と目的にも汎用の登録クレームはありません。rdap_allowed_purposes という登録名はありますが、RDAP という特定の用途のためのものです。同意の内容は、scope や authorization_details で表すのが標準の方法です。端末、IP アドレス、場所については、location という登録名がありますが、これは機器の証明を出す機器の位置で、利用者のログインの場所ではありません。cdniip も CDN の署名つき URI が有効な IP で、汎用のクライアント IP ではありません。名前が似ているからといって流用すると、意味の違うクレームになります。注意したいのは、同じ名前でも意味が違う例があることです。Curity の製品では purpose というクレームがトークンの種類を表します。また英国のオープンバンキングの仕様では、同じ ID の名前がハイフンとアンダースコアで揺れていて、誤記が相互運用の不具合になりえます。',
      refs: { spec: 'IANA JWT Claims（2026-10-28 版）／RFC 9711 §4.2.10／RFC 9246 §2.1.10', inst: 'NIST SP 800-162 §2.4.2（属性の名前と定義を管理）', book: '『デジタルアイデンティティのすべて』（考え方）15.2 節 p.262（スキーマの統一）' },
    });
    L.table(s, [['用途', '似た登録クレーム（別物）', '各社の独自クレーム', '独自に作る前に'],
      ['テナント・組織', 'なし', 'tid・org_id・organization', 'aud・iss の分離で足りるか'],
      ['同意・目的', 'rdap_allowed_purposes（RDAP 専用）', 'オープンバンキングの同意 ID など', 'scope・authorization_details で表せるか'],
      ['端末・IP・場所', 'location（証明を出す機器の位置）、cdniip（CDN 用）', 'Entra の ipaddr など', '変わる状態は PEP で都度評価できないか（Part 6）']],
    { x: 0.6, y: 1.95, w: 12.1, colW: [1.8, 3.6, 3.0, 3.7], fontSize: 12, rowH: 0.75 });
    L.card(s, { x: 0.6, y: 5.05, w: 5.95, h: 1.45, color: C.accent3, icon: 'MdCallSplit', title: '同じ名前、違う意味', titleSize: 14, body: ['purpose がトークンの種類を表す製品もある'], bodySize: 12.5 });
    L.card(s, { x: 6.75, y: 5.05, w: 5.95, h: 1.45, color: C.accent3, icon: 'MdWarning', title: '名前の表記揺れ', titleSize: 14, body: ['仕様書の中で - と _ が揺れ、相互運用の不具合に'], bodySize: 12.5 });
  }

  {
    const s = L.content('SAML の属性と JWT：対応表は規範ではない', { id: 'p02-saml-attributes',
      lead: '概念の対応はあるが、規範として定めた対応表は見当たらない。ブローカーでの写し方を組織で決める',
      stages: [0, 1],
      notes: 'SAML から OpenID Connect に移行したり、外部の SAML の IdP をブローカーでつないだりすると、SAML の属性を JWT のクレームに写す必要が出てきます。概念の対応はおおむね明らかで、Issuer が iss、NameID が sub、AudienceRestriction が aud、NotOnOrAfter が exp にあたります。ただし、これを規範として定めた単一の標準は、本調査では見当たりませんでした。ずれの例があります。Entra ID は SAML の AuthnContextClassRef を amr に対応づけていますが、名前の上では OpenID Connect の acr に対応します。どちらに写すかは組織で決める必要があります。識別子にも注意が要ります。SAML の subject-id は大文字小文字を区別せずに比べますが、OpenID Connect の sub は区別します。また、メールアドレス形式の NameID をそのまま sub に写すと、メールを一意のキーにする状態を作ってしまいます。Keycloak では、IdP マッパーで外部の属性をいったん取り込み、プロトコルマッパーで社内の名前のクレームにする 2 段の写し方になります。',
      refs: { spec: 'SAML 2.0 Profiles §8／SAML Subject ID Attributes §3.3–3.4', inst: 'NIST SP 800-162 §3.2.3.2（組織間の属性の対応づけ）', book: '『実践 Keycloak』10.3 節 pp.198–199、解答 p.318' },
    });
    L.table(s, [['概念', 'SAML', 'JWT', '注意'],
      ['発行者・宛先', 'Issuer・AudienceRestriction', 'iss・aud', '一般的な対応'],
      ['主体', 'NameID', 'sub', 'メール形式の NameID を sub にしない'],
      ['識別子の属性', 'subject-id・pairwise-id', 'sub（public・pairwise）', 'subject-id は大文字小文字を無視して比べる'],
      ['認証の方式', 'AuthnContextClassRef', 'acr か amr', 'Entra は amr に対応づけ。名前は acr に近い'],
      ['テナント（Entra）', '…/identity/claims/tenantid', 'tid', '同じ属性が SAML では URI 名']],
    { x: 0.6, y: 1.95, w: 12.1, colW: [2.0, 3.3, 2.4, 4.4], fontSize: 12, rowH: 0.5 });
    L.flow(s, [{ t: '外部の IdP', d: 'SAML の属性', fill: C.accent5 }, { t: 'IdP マッパー', d: '属性・ロールに取り込む' }, { t: 'Keycloak のユーザー', d: '属性・ロール', fill: C.accent5 }, { t: 'プロトコルマッパー', d: '社内の名前のクレームに' }, { t: 'トークン', d: '組織の公開名', fill: C.accent2 }],
      { x: 0.6, y: 5.25, w: 12.1, h: 1.2, tSize: 13.5, dSize: 11 });
  }

  {
    const s = L.content('独自クレームを作る前の確認：4 つの場所を探す', { id: 'p02-check-before-creating',
      lead: '登録簿・仕様・IdP の文書・組織の台帳の順に探し、無いときだけ名前空間つきで作る',
      stages: [0, 5],
      notes: 'Part 2 のまとめとして、独自クレームを作る前に確認する手順を示します。まず IANA の JSON Web Token Claims の登録簿を探します。意味が合う登録名があれば、その名前を使います。次に、OpenID Connect、RFC 9068、RFC 9396 などの仕様に、拡張のための構造がないかを確かめます。authorization_details の type や、sub_id の format のように、名前ではなく値の中で拡張できる場合があります。3 つ目に、使っている IdP の文書を確かめます。IdP が既に出しているクレーム、予約された名前、衝突したときの挙動です。Auth0 のように、予約名と衝突した独自クレームが黙って外れる IdP もあります。4 つ目に、組織のクレームの台帳を確かめます。同じ意味のクレームが別の名前で既にないかです。ここまで探して無いときだけ、組織の名前空間の下に新しいクレームを作り、何を意味し、何を意味しないかを書き残します。名前や型の決め方は Part 4、台帳の運用は Part 11 で扱います。',
      refs: { spec: 'RFC 7519 §4.2・§10.1／RFC 9068 §2.2.2', inst: 'デジタル庁 DS-212 §3.2.3（属性名・型・値を事前に標準化）', book: '『デジタルアイデンティティのすべて』（考え方）21.2 節 pp.380–381' },
    });
    L.flow(s, [
      { t: '1. IANA の登録簿', d: '意味が合えば登録名を使う' },
      { t: '2. 仕様の構造', d: 'type や format など、値の中で拡張できないか' },
      { t: '3. IdP の文書', d: '既存のクレーム、予約名、衝突時の挙動' },
      { t: '4. 組織の台帳', d: '同じ意味のクレームが別名で無いか' },
      { t: '5. 作る', d: 'https://claims.example.com/ の下に', fill: C.accent2 },
    ], { x: 0.6, y: 1.95, w: 12.1, h: 1.75, tSize: 14.5, dSize: 12 });
    L.card(s, { x: 0.6, y: 3.95, w: 5.95, h: 2.5, color: C.accent1, icon: 'MdFactCheck', title: '作るときに書き残すこと', titleSize: 15, body: ['何を意味し、何を意味しないか', '近い既存クレームとの違い', '探した場所と、使わなかった理由'], bodySize: 13 });
    L.card(s, { x: 6.75, y: 3.95, w: 5.95, h: 2.5, color: C.accent2, icon: 'MdFlag', title: 'この先の Part', titleSize: 15, body: [['Part 3：', '各 IdP の予約名と衝突時の挙動'], ['Part 4：', '名前・型・識別子の決め方'], ['Part 11：', 'クレームの台帳と変更の手順']], bodySize: 13 });
  }
};
