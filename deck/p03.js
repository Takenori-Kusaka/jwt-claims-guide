// Part 3: what the four IdPs actually issue (Entra ID, Keycloak, Auth0/Okta, Cognito) as of 2026-11
module.exports = (L) => {
  const { C, SH, HEX } = L;
  L.section('Part 3 4 つの IdP の実際');
  L.divider('PART 3', '4 つの IdP の実際', '同じ名前のクレームでも、IdP ごとに位置・形・意味が違う。2026 年 11 月時点の挙動と、最近の変更',
    ['利用者の安定したキーは、IdP ごとにどれか', 'アクセストークンの aud は、どう決まるか', '独自クレームは、どこで入れ、何が禁じられているか', '古い理解のままだと、どこで誤るか'],
    'Part 3 では、Microsoft Entra ID、Keycloak、Auth0 と Okta、Amazon Cognito の 4 つの IdP が、実際にどんなクレームを出しているかを見ます。標準のクレームの名前を使っていても、IdP によって位置や形や意味が違います。たとえば sub は、Entra ID ではアプリごとに違う値になり、Okta のアクセストークンではログイン名になります。また、各社とも最近になって大きな変更を入れています。Cognito のトークン交換や、Keycloak のトークン交換の正式サポート、Auth0 の独自クレームの規則などです。古い記事や書籍の理解のままだと誤ります。内容は各社の公式文書を 2026 年 11 月 17 日時点で確認したものです。最後に、IdP ごとの違いを各サービスに持ち込まず、入口で吸収する考え方を示します。');

  {
    const s = L.content('4 つの IdP の比較：同じ用途、違うクレーム', {
      lead: '利用者のキー、aud、ロールの位置、独自クレームの入れ方は、IdP ごとにすべて違う',
      stages: [0, 1, 3],
      notes: '4 つの IdP を、7 つの観点で並べた表です。利用者の安定したキーは、Entra ID では oid と tid の組で、sub はアプリごとに違います。Okta はアクセストークンの sub がログイン名なので、uid を使います。テナントは、Entra ID の tid、Auth0 の org_id、Keycloak の organization と、それぞれ独自です。アクセストークンの aud も違います。Keycloak は自動では API を aud に入れず、Cognito は既定では aud 自体がありません。ロールやグループの位置もばらばらで、独自クレームの入れ方も、マッパー、Actions、発行前のフックと仕組みが違います。トークン交換は、どの IdP も RFC 8693 系の仕組みを持つようになりましたが、提供の段階が違います。この表から言えるのは、受け手のサービスが IdP ごとの読み方を持つと、IdP を足したり替えたりするたびに全サービスが変わる、ということです。この後、IdP ごとに詳しく見ていきます。',
      refs: { spec: 'Entra／Keycloak／Auth0／Okta／Cognito の公式文書（2026-11 時点）', inst: 'NIST SP 800-63C-4 §3.4（iss と sub の組）', book: '『セキュアAPI』7.7 節 p.219（IdP ごとのロールの運び方）' },
    });
    const H = (t) => ({ text: t, options: { bold: true } });
    L.table(s, [['観点', 'Entra ID', 'Keycloak', 'Auth0／Okta', 'Cognito'],
      ['利用者のキー', 'oid＋tid（sub はアプリごと）', 'sub', 'Auth0：sub／Okta：AT は uid', 'sub（username は一意でない）'],
      ['テナント', 'tid', 'organization（レルムは iss）', 'Auth0：org_id', 'なし（プールは iss）'],
      ['AT の aud', 'API の App ID URI か client ID', '自動では入らない', 'Auth0：audience 指定時／Okta：Custom AS', '既定は無し。resource 指定時のみ'],
      ['ロール・グループ', 'roles・scp・groups・wids', 'realm_access・resource_access', 'Auth0：permissions／Okta：groups・scp', 'cognito:groups・scope'],
      ['独自クレーム', '任意クレーム・クレームの対応づけ', 'プロトコルマッパー・クライアントスコープ', 'Auth0：Actions／Okta：Custom AS のみ', '発行前フック V1〜V3・custom: 属性'],
      ['acr・amr', 'acr は v1 のみ（0/1）・acrs', 'acr（LoA マッパー）', 'Okta：acr・amr・auth_time', '固定 4 段階（順次提供）'],
      ['トークン交換', 'OBO（jwt-bearer）', 'Standard V2（正式）・委任（preview）', 'OBO（RFC 8693）', 'RFC 8693（2026-11〜）']],
    { x: 0.6, y: 1.95, w: 12.1, colW: [1.7, 2.6, 2.6, 2.6, 2.6], fontSize: 10.5, rowH: 0.55 });
  }

  {
    const s = L.content('Entra ID：キーは oid と tid、sub はアプリごと', {
      lead: 'sub はアプリごとに値が違う。サービス間で共有するキーは oid＋tid。iss は tid で照合する',
      stages: [3, 4],
      notes: 'Microsoft Entra ID の識別子です。Entra ID の sub は不変で再利用されませんが、ペアワイズで、アプリごとに値が違います。同じ利用者でも、クライアントが違えば sub が違います。テナント内でアプリをまたいで同じになるのは oid で、テナントは tid です。Microsoft は、サービス間で共有するキーには oid と tid を使い、tid をデータのキーに含めるよう勧めています。email、preferred_username、unique_name で認可を判断してはならず、upn も変わることがあるので認可に使いません。マルチテナントのアプリでは、common などのメタデータの issuer が tenantid を含むテンプレートになっています。そのまま文字列で比べるのではなく、トークンの tid で置き換えてから完全一致で確かめます。もう 1 つ大事なのは、自分の API 宛てでないトークンを検証しないことです。Microsoft Graph 向けのトークンは独自の形式で、自分の API で検証も受け入れもしてはいけません。受け入れると、他人宛てのトークンで動く confused deputy になります。',
      refs: { spec: 'Entra：access-token-claims-reference／claims-validation／access-tokens', inst: 'NIST SP 800-63C-4 §3.4・§4.9（IdP をまたいで一意とみなさない）', book: '『デジタルアイデンティティのすべて』（考え方）4.2.4 節 pp.33–35（指向性のある識別子）' },
    });
    L.code(s, ['{', '  "aud": "<API の client ID>",', '  "tid": "9c1e…",            // テナント', '  "oid": "3f2b…",            // テナント内で共通', '  "sub": "Kx9…",             // アプリごとに違う', '  "scp": "Orders.Read",      // 空白区切り', '  "azp": "<クライアントのアプリ ID>",', '  "upn": "taro@example.com"  // 認可に使わない', '}'].join('\n'), { x: 0.6, y: 1.95, w: 5.9, h: 3.0, fontSize: 11 });
    L.card(s, { x: 6.8, y: 1.95, w: 5.9, h: 1.85, color: C.accent1, icon: 'MdPerson', title: '識別子', titleSize: 15, body: ['共有のキーは oid＋tid、tid をデータのキーに', 'email・preferred_username・upn で認可しない'], bodySize: 12.5 });
    L.card(s, { x: 6.8, y: 3.95, w: 5.9, h: 2.0, color: C.accent5, icon: 'MdApartment', title: 'マルチテナント', titleSize: 15, body: ['issuer のテンプレートを tid で置き換えて照合', 'tid が保存データのテナントと一致するか確かめる'], bodySize: 12.5 });
    L.note(s, 'warn', 'Microsoft Graph 向けなど、自分の API 宛てでないトークンは検証も受け入れもしない（独自形式。confused deputy になる）', { x: 0.6, y: 5.15, w: 5.9, h: 1.3, size: 12.5, label: '' });
    L.note(s, 'leader', '組織のキーは oid＋tid に揃える（Part 5）', { x: 6.8, y: 6.05, w: 5.9, h: 0.45, size: 12.5, label: '' });
  }

  {
    const s = L.content('Entra ID：scp と roles、グループの超過、拡張属性', {
      lead: 'groups は 200 件を超えると消えて別の形に置き換わる。「無い」は「所属なし」ではない',
      stages: [1, 3, 4],
      notes: 'Entra ID の認可に関わるクレームです。scp は、クライアントが同意を得たスコープを空白区切りで並べたもので、利用者のトークンだけに入ります。アプリ専用のトークンでは、許可された権限は roles に入ります。groups には注意が必要です。JWT では 200 件、SAML では 150 件を超えると groups が出なくなり、代わりに _claim_names と _claim_sources という超過の印が入ります。そこに書かれた URL は古い Azure AD Graph のものなので頼らず、idtyp でトークンの種類を見て Microsoft Graph に問い合わせます。groups が無いことを所属なしと読むと、判断を誤ります。大きな組織では、アプリに割り当てたグループだけを出す設定が勧められています。トークンの版は、呼んだエンドポイントではなく、API 側の requestedAccessTokenVersion で決まり、null は v1 扱いです。acr は v1 のトークンにしかありません。拡張属性は extn という接頭辞つきの名前で出ますが、名前の大文字小文字が揺れると黙って欠落します。AI エージェントは Agent ID 用のクレームで表されます。これは Part 10 で扱います。',
      refs: { spec: 'Entra：access-token-claims-reference／optional-claims／schema-extensions', inst: 'OWASP JWT Cheat Sheet（roles・groups の扱い）', book: '『セキュアAPI』7.7 節 p.219（Entra は roles・groups）' },
    });
    L.table(s, [['クレーム・設定', '挙動'],
      ['scp', 'クライアントが同意を得たスコープ（空白区切り）。利用者のトークンだけ'],
      ['roles', 'アプリ専用のトークンでは、許可された権限はここに入る'],
      ['groups', { text: 'JWT で 200 件、SAML で 150 件を超えると出ず、_claim_names・_claim_sources に置き換わる', options: { color: HEX.accent3, bold: true } }],
      ['トークンの版', 'API 側の requestedAccessTokenVersion で決まる（null は v1）。acr は v1 だけ'],
      ['拡張属性', 'extn.<属性名> で出る。名前の大文字小文字の揺れで黙って欠落する'],
      ['Agent ID', 'xms_act_fct・xms_sub_fct・idtyp などでエージェントを表す（Part 10）']],
    { x: 0.6, y: 1.9, w: 8.0, colW: [1.8, 6.2], fontSize: 11.5, rowH: 0.5 });
    L.card(s, { x: 8.9, y: 1.95, w: 3.8, h: 3.0, color: C.accent3, icon: 'MdGroups', title: 'グループの超過', titleSize: 15, body: ['印にある古い URL に頼らない', 'idtyp を見て Microsoft Graph に問い合わせる', 'アプリに割り当てたグループに絞る'], bodySize: 12.5 });
    L.note(s, 'leader', 'groups が無いトークンを「所属なし」と読まない。超過の経路を実装するか、件数を絞る', { x: 8.9, y: 5.1, w: 3.8, h: 1.4, size: 12.5 });
    L.note(s, 'tip', 'アクセストークンは常にリソース側の設定で作られる', { x: 0.6, y: 5.95, w: 8.0, h: 0.55, size: 12.5, label: '' });
  }

  {
    const s = L.content('Keycloak：マッパーがなければクレームは出ない', {
      lead: '属性はプロトコルマッパーで初めてクレームになる。束ねて再利用するのがクライアントスコープ',
      stages: [0, 1],
      notes: 'Keycloak では、利用者の属性を作っただけではトークンに出ません。プロトコルマッパーを設定して、初めてクレームになります。マッパーでは、クレームの名前、JSON の型、どのトークンに載せるかを指定します。マッパーを束ねて再利用する単位がクライアントスコープです。Default に入れたスコープは常に付き、Optional に入れたスコープはクライアントが要求したときだけ付きます。User Attribute のマッパーではクレームの JSON の型を選べるので、組織で型をそろえておきます。ロールは、レルムロールが realm_access、クライアントロールが resource_access の中に入ります。入るのは、利用者が持つロールと、クライアントが使ってよいロールの積集合です。既定では Full scope allowed がオンで全ロールが入るので、本番ではオフにして必要なロールだけにします。グループは Group Membership マッパーが必要で、フルパスで出ます。なお『実践 Keycloak』は Keycloak 18 が前提なので、画面の名前は今と違います。',
      refs: { spec: 'Keycloak Server Administration Guide（Mappers・Client scopes）', inst: 'NIST SP 800-63C-4 §3.10（必要最小限のデータ）', book: '『実践 Keycloak』4.5.2・5.5.2 節 pp.56–58, 77–81（UI は旧版）' },
    });
    L.flow(s, [{ t: 'ユーザー属性', d: '利用者ごとの値', fill: C.accent5 }, { t: 'プロトコルマッパー', d: '名前・JSON の型・載せるトークン' }, { t: 'クライアントスコープ', d: 'Default は常に、Optional は要求時' }, { t: 'トークン', d: 'クレームとして出る', fill: C.accent2 }],
      { x: 0.6, y: 1.95, w: 12.1, h: 1.15, tSize: 14, dSize: 11.5 });
    L.code(s, ['{', '  "iss": "https://kc.example.com/realms/corp",', '  "azp": "portal",', '  "aud": ["orders-api"],', '  "realm_access": { "roles": ["employee"] },', '  "resource_access": { "orders-api": { "roles": ["approver"] } },', '  "scope": "openid profile",', '  "https://claims.example.com/tenant": "t-042"', '}'].join('\n'), { x: 0.6, y: 3.3, w: 6.9, h: 3.15, fontSize: 11 });
    L.card(s, { x: 7.75, y: 3.3, w: 4.95, h: 3.15, color: C.accent3, icon: 'MdRule', title: '注意点', titleSize: 15, body: ['入るロールは「利用者」∩「クライアント」', 'Full scope allowed は本番でオフに', 'クレームの JSON の型をマッパーで固定', 'グループはマッパーが要り、フルパスで出る'], bodySize: 12.5 });
  }

  {
    const s = L.content('Keycloak：aud・軽量トークン・組織・トークン交換', {
      lead: 'API を aud に入れるには設定が要る。トークン交換は V2 が正式、委任はまだ preview',
      stages: [1, 2, 3],
      notes: 'Keycloak の 4 つの論点です。1 つ目は aud です。Keycloak は自動では API を aud に入れません。Audience マッパーをクライアントスコープに設定するか、クライアントロールを持つクライアントを aud に足す Audience Resolve の仕組みを使います。既定で aud に入る account は、API 固有の値ではありません。『OpenID Connect入門』のサンプルも、本来は API 固有の値にすべきと断ったうえで、既定のままにしています。2 つ目は軽量アクセストークンです。クレームを絞ったアクセストークンで、全クレームが必要な場面ではトークン交換で通常のトークンに変えます。3 つ目は組織の機能で、organization スコープを要求すると organization クレームが出ます。ただし 2025 年に、メールのドメインが一致するだけで組織の所属を付けてしまう脆弱性が報告されました。4 つ目はトークン交換です。内部のトークン同士を交換する Standard Token Exchange V2 は正式サポートで既定で有効、旧 V1 は非推奨です。act を入れる委任は 26.8 で preview になりました。',
      refs: { spec: 'Keycloak：Server Admin Guide／Token exchange／26.8.0 告知', inst: 'NVD CVE-2025-1391・CVE-2025-14559', book: '『OpenID Connect入門』9.4 節 p.130／『実践 Keycloak』5.5.1 節 pp.76–77' },
    });
    const cs = [
      ['MdDns', C.accent1, 'aud', ['自動では API を含まない', 'Audience マッパーをスコープに設定', '既定の account は API 固有の値ではない']],
      ['MdDataObject', C.accent5, '軽量アクセストークン', ['クレームを絞ったアクセストークン', '全クレームが要るならトークン交換で変換', 'マッパーごとに載せるかを選ぶ']],
      ['MdApartment', C.accent3, '組織（Organizations）', ['organization スコープで organization クレーム', 'CVE-2025-1391：ドメイン一致だけで所属を付与', '所属は確かな情報源から付ける']],
      ['MdSwapHoriz', C.accent4, 'トークン交換', ['Standard V2：正式・既定で有効（内部同士）', '旧 V1：非推奨', '委任（act）：26.8 で preview', 'CVE-2025-14559：無効な利用者にも発行']],
    ];
    cs.forEach((c, i) => {
      const col = i % 2, row = Math.floor(i / 2);
      L.card(s, { x: 0.6 + col * 6.15, y: 1.95 + row * 2.3, w: 5.95, h: 2.15, icon: c[0], color: c[1], title: c[2], titleSize: 15, body: c[3], bodySize: 12.5 });
    });
  }

  {
    const s = L.content('Auth0：名前空間の規則と、黙って消えるクレーム', {
      lead: '名前空間なしも許されるようになったが制約が多い。予約名と衝突すると、エラーなしで外れる',
      stages: [0, 1],
      notes: 'Auth0 の独自クレームの規則は変わっています。以前は名前空間つきの名前が必須とされていましたが、現在は名前空間なしの名前も許されています。ただし制約が多く、Auth0 自身も、どうしても必要でない限り名前空間つきを使うよう勧めています。まず、予約された名前があります。acr、act、aud、client_id、cnf、groups、org_id、permissions、roles、sid、sub などで、roles や groups や permissions を素の名前で足すことはできません。名前空間にも、auth0.com、webtask.io、webtask.run のドメインと、urn:auth0 は使えません。Auth0 の API を宛先とするアクセストークンには、名前空間なしの私的なクレームを入れられません。そして最も注意が要るのは、衝突したときの挙動です。トランザクションは失敗せず、クレームが黙って追加されないだけです。独自クレームの合計は 100KB までです。また、audience を指定せずにトークンを要求すると、自分の API では検証できない不透明なアクセストークンが返ります。',
      refs: { spec: 'Auth0：create-custom-claims／get-access-tokens／access-token-profiles', inst: 'NVD CVE-2025-68129（ID トークンを AT として受理）', book: '『セキュアAPI』7.7 節 p.219・付録 B pp.355–356' },
    });
    L.table(s, [['規則', '内容'],
      ['名前', '名前空間つき・なしの両方を許可。名前空間つきを推奨'],
      ['予約名', 'acr・act・aud・client_id・cnf・groups・org_id・permissions・roles・sid・sub ほか'],
      ['使えない名前空間', 'auth0.com・webtask.io・webtask.run・urn:auth0'],
      ['API 宛ての AT', 'Auth0 の API 宛てには、名前空間なしの私的クレームを入れられない'],
      ['衝突したとき', { text: 'トランザクションは失敗せず、クレームが黙って追加されない', options: { color: HEX.accent3, bold: true } }],
      ['上限', '独自クレームの合計 100KB']],
    { x: 0.6, y: 1.9, w: 7.2, colW: [1.9, 5.3], fontSize: 11.5, rowH: 0.5 });
    L.code(s, ['{', '  "sub": "auth0|64f…",', '  "aud": ["https://api.example.com",', '          "https://<テナント>/userinfo"],', '  "org_id": "org_9a…",', '  "permissions": ["orders:read"],', '  "https://claims.example.com/tenant": "t-042"', '}', '// "roles" を素の名前で足しても黙って外れる'].join('\n'), { x: 8.05, y: 1.95, w: 4.65, h: 3.25, fontSize: 10.5 });
    L.note(s, 'warn', 'audience を付け忘れると、自分の API では検証できない不透明な AT が返る', { x: 8.05, y: 5.35, w: 4.65, h: 1.1, size: 12.5, label: '' });
    L.note(s, 'leader', '独自クレームは必ず組織の名前空間つきで足し、発行後のトークンに入っているかをテストで確かめる', { x: 0.6, y: 5.85, w: 7.2, h: 0.6, size: 12.5, label: '' });
  }

  {
    const s = L.content('Okta：Custom AS を使い、AT では uid を見る', {
      lead: 'Org AS の AT は自分の API で検証しない。AT の sub はログイン名なので、キーは uid',
      stages: [1, 3, 4],
      notes: 'Okta には 2 種類の認可サーバーがあります。Org 認可サーバーは Okta 自身の API のためのもので、そのアクセストークンは Okta だけが検証する前提です。内容は予告なく変わるので、自分の API で検証してはいけません。aud やクレームも変えられません。自分の API を守るには、Custom 認可サーバーを使います。独自クレームを自由に足せるのも Custom 認可サーバーだけです。次に識別子です。Okta のアクセストークンの sub は、ログイン名、多くはメール形式の文字列です。一方、ID トークンの sub は 00u で始まる Okta のユーザー ID です。アクセストークンで利用者を識別するには uid を使います。scp は付与されたスコープの配列で、Entra ID の空白区切りの文字列とは形が違います。groups は 100 件を超えると、要求そのものが失敗します。Entra ID の超過の挙動とは逆です。独自クレームの値は式で書き、式は 1024 文字までです。トークンのプレビューの画面で、発行前に結果を確かめられます。',
      refs: { spec: 'Okta：auth-servers／reference/api/oidc／customize-tokens-groups-claim', inst: 'NIST SP 800-63C-4 §3.4／OWASP ASVS 10.5.2（変わらない識別子）' },
    });
    L.table(s, [['', 'Org 認可サーバー', 'Custom 認可サーバー'],
      ['用途', 'Okta 自身の API', '自分の API の保護'],
      ['AT を自分で検証', { text: 'しない（予告なく変わる）', options: { color: HEX.accent3, bold: true } }, 'する'],
      ['独自クレーム', 'groups クレームだけ', '任意のクレーム・スコープ'],
      ['aud', '変えられない', '設定した audience']],
    { x: 0.6, y: 1.95, w: 6.4, colW: [1.8, 2.3, 2.3], fontSize: 12, rowH: 0.6 });
    L.table(s, [['クレーム', 'アクセストークン', 'ID トークン'],
      ['sub', { text: 'ログイン名（メール形式）', options: { color: HEX.accent3, bold: true } }, 'ユーザー ID（00u…）'],
      ['uid', 'ユーザー ID', '—'],
      ['cid', 'client ID', '—（aud が client ID）'],
      ['scp', 'スコープの配列', '—']],
    { x: 7.25, y: 1.95, w: 5.45, colW: [1.1, 2.25, 2.1], fontSize: 12, rowH: 0.6 });
    L.card(s, { x: 0.6, y: 5.15, w: 6.4, h: 1.35, color: C.accent3, icon: 'MdGroups', title: 'groups は 100 件まで', titleSize: 14, body: ['超えると要求そのものが失敗（Entra と逆）'], bodySize: 12.5 });
    L.card(s, { x: 7.25, y: 5.15, w: 5.45, h: 1.35, color: C.accent1, icon: 'MdFactCheck', title: '値は式で書く（1024 文字まで）', titleSize: 14, body: ['プレビューの画面で発行前に確かめる'], bodySize: 12.5 });
  }

  {
    const s = L.content('Cognito：token_use を確かめ、aud の欠落に備える', {
      lead: 'ID トークンが API を通らないよう token_use を確かめる。AT の aud は resource 指定時だけ',
      stages: [3],
      notes: 'Amazon Cognito のトークンを受け取るときの確認点です。Cognito の ID トークンとアクセストークンは、どちらも JWT で、token_use というクレームで種類を区別します。API でアクセストークンだけを受け入れるなら、token_use が access であることを必ず確かめます。確かめないと、ID トークンが API を通ってしまいます。次に宛先です。ID トークンでは aud が、アクセストークンでは client_id が、アプリクライアントの ID と一致することを確かめます。Cognito のアクセストークンには、既定では aud がありません。2025 年 10 月から、RFC 8707 の resource を指定して要求したときだけ aud が入るようになりました。aud を必須とする検証の部品をそのまま使うと、失敗するか、設定次第では素通りします。利用者のキーは sub です。username はプール内で一意とは限りません。sub は Cognito 独自の形式なので、UUID として厳密に形式を検証してはいけません。また、署名と exp の確認だけでは、サインアウトや失効を検出できません。',
      refs: { spec: 'Cognito：verifying-a-jwt／using-the-access-token／What\'s new 2025-10', inst: 'OWASP ASVS 9.2.2（トークンの種類の確認）' },
    });
    L.code(s, ['{', '  "iss": "https://cognito-idp.<リージョン>.amazonaws.com/<プール ID>",', '  "token_use": "access",', '  "client_id": "6s1q…",', '  "sub": "c4f8…",', '  "username": "taro",', '  "cognito:groups": ["approvers"],', '  "scope": "orders/read"', '}'].join('\n'), { x: 0.6, y: 1.95, w: 6.0, h: 3.0, fontSize: 10.5 });
    L.table(s, [['確認', '内容'],
      ['token_use', 'access か id。API では access だけ'],
      ['aud・client_id', 'ID トークンは aud、AT は client_id をアプリクライアントの ID と照合'],
      ['aud（AT）', { text: '既定では無い。2025-10 以降、resource 指定時に入る', options: { color: HEX.accent3, bold: true } }],
      ['sub', '利用者のキー。UUID として厳密に検証しない'],
      ['username', 'プール内で一意とは限らない']],
    { x: 6.85, y: 1.9, w: 5.85, colW: [1.6, 4.25], fontSize: 11, rowH: 0.45 });
    L.note(s, 'warn', 'aud を必須とする検証の部品をそのまま使うと、失敗するか素通りする。署名と exp だけでは、サインアウトや失効は検出できない', { x: 0.6, y: 5.35, w: 12.1, h: 0.62, size: 12.5, label: '' });
    L.note(s, 'tip', 'acr・amr は固定の 4 段階。順次提供中で、発行前のフックでは変えられない', { x: 0.6, y: 6.05, w: 12.1, h: 0.45, size: 12.5, label: '' });
  }

  {
    const s = L.content('Cognito：発行前フックと custom: 属性の落とし穴', {
      lead: 'AT を変えるには V2 以上が要る。custom: 属性は利用者本人が書き換えられることがある',
      stages: [1, 4],
      notes: 'Cognito で独自クレームを入れるのは、トークン発行前の Lambda のフックです。版によってできることが違います。V1 は ID トークンだけを変えられ、V2 では利用者のアクセストークンも、V3 では M2M、つまりクライアントクレデンシャルのアクセストークンも変えられます。V2 と V3 は Essentials か Plus のプランが必要です。sub、username、client_id、aud、acr、amr などは、フックでは変えられません。次に custom: 属性です。Cognito の独自の属性は custom: という接頭辞がつき、最大 50 個、値は 2048 文字までで、追加した後は削除も改名も型の変更もできません。そして重要なのは、読み取り専用にしない限り、利用者本人が書き換えられる場合があることです。custom:role のような属性を権限に使って昇格される問題が、研究で指摘されています。最後に、2026 年 11 月 12 日にトークン交換が追加されました。単一の aud に絞ったトークンを出し、actor token を付ければ act が入ります。付けなければ本人と区別できず、may_act は扱いません。',
      refs: { spec: 'Cognito：pre-token-generation／user-pool-settings-attributes／token-exchange', inst: 'NIST SP 800-162 §3.1.3.3（権威ある主体だけが属性を付与）' },
    });
    L.table(s, [['版', '変えられるトークン', 'プラン'],
      ['V1_0', 'ID トークンだけ', '—'],
      ['V2_0', '＋利用者のアクセストークン', 'Essentials・Plus'],
      ['V3_0', '＋M2M のアクセストークン', 'Essentials・Plus（M2M は別料金）']],
    { x: 0.6, y: 1.95, w: 6.3, colW: [1.0, 2.8, 2.5], fontSize: 12, rowH: 0.5 });
    L.card(s, { x: 0.6, y: 4.2, w: 6.3, h: 2.25, color: C.accent5, icon: 'MdRule', title: 'フックで変えられないクレーム', titleSize: 14, body: ['sub・username・cognito:username', 'client_id・aud・acr・amr', 'その他の cognito: で始まるもの'], bodySize: 12.5 });
    L.card(s, { x: 7.15, y: 1.95, w: 5.55, h: 2.4, color: C.accent3, icon: 'MdWarning', title: 'custom: 属性', titleSize: 15, body: ['最大 50 個、値は 2048 文字まで', '追加後は削除・改名・型の変更ができない', '読み取り専用にしない限り本人が書き換えうる'], bodySize: 12.5 });
    L.card(s, { x: 7.15, y: 4.5, w: 5.55, h: 1.95, color: C.accent4, icon: 'MdSwapHoriz', title: 'トークン交換（2026-11-12〜）', titleSize: 14, body: ['単一の aud、リフレッシュトークンなし', 'actor token ありなら act。無しは本人と区別不能', 'may_act は発行も評価もしない'], bodySize: 12 });
  }

  {
    const s = L.content('最近の変更：古い理解のままだと誤る点', {
      lead: '2025〜2026 年に各社が大きく変えた。古い記事や書籍の手順は、現行の文書で確かめ直す',
      stages: [5],
      notes: '最近の変更のうち、古い理解のままだと誤る点をまとめます。Cognito は変更が多く、2025 年 3 月に M2M のアクセストークンを発行前フックの V3 で変えられるようになり、10 月には resource を指定するとアクセストークンに aud が入るようになりました。2026 年 11 月 12 日には RFC 8693 のトークン交換が加わりました。acr と amr も順次提供されています。Keycloak は、内部のトークン同士を交換する Standard Token Exchange V2 が正式サポートになり、旧 V1 は非推奨です。2026 年 10 月の 26.8 では、act を使う委任が preview になりました。『実践 Keycloak』は Keycloak 18 を前提にしているので、画面の名前やトークン交換、組織の機能、軽量アクセストークンの記述は現行と違います。Auth0 は、独自クレームに名前空間なしの名前も許すようになりましたが、制約と黙った欠落があります。Entra ID は、AI エージェントを表す Agent ID 用のクレームを文書化しています。いずれも、調査日時点の公式文書を正としてください。',
      refs: { spec: 'Cognito What\'s new／Keycloak 26.8.0 告知／Auth0・Entra 公式文書', book: '『実践 Keycloak』は Keycloak 18 前提（訳者まえがき p.vii）' },
    });
    L.table(s, [['時期', 'IdP', '古い理解', '現在'],
      ['2025-03-03', 'Cognito', 'M2M の AT は変えられない', '発行前フック V3 で変えられる'],
      ['2025-10-27', 'Cognito', 'AT に aud は入らない', 'resource を指定すると aud が入る'],
      ['2026-11-12', 'Cognito', 'トークン交換はない', 'RFC 8693 のトークン交換。act つき、RT なし'],
      ['順次提供中', 'Cognito', 'acr・amr は出ない', '固定 4 段階の acr・amr'],
      ['26.x', 'Keycloak', 'トークン交換は preview', 'Standard V2 は正式。旧 V1 は非推奨'],
      ['2026-10（26.8）', 'Keycloak', '委任は experimental', '委任（act）は preview'],
      ['現行', 'Auth0', '独自クレームは名前空間が必須', '名前空間なしも可。予約名と衝突すると黙って外れる'],
      ['2026-04 更新', 'Entra ID', 'エージェントも普通のアプリ', 'Agent ID 用のクレーム（xms_act_fct など）']],
    { x: 0.6, y: 1.9, w: 12.1, colW: [1.8, 1.4, 3.6, 5.3], fontSize: 11.5, rowH: 0.43 });
    L.note(s, 'leader', '社内の手順書や書籍の記述は、現行の公式文書で確かめ直してから使う（『実践 Keycloak』は 18 前提）', { x: 0.6, y: 6.08, w: 12.1, h: 0.45, size: 12.5, label: '' });
  }

  {
    const s = L.content('独自クレームの入れ方：失敗しても黙って出る', {
      lead: '仕組みも上限も IdP ごとに違う。フックが失敗しても、クレームなしでトークンが出ることがある',
      stages: [1, 3],
      notes: '各 IdP で独自クレームを入れる仕組みと、失敗したときの挙動、上限をまとめます。Entra ID の custom claims provider は、トークンを発行する直前に外部の REST API を呼びますが、返したクレームのうち、クレームの対応づけで明示したものだけが入ります。型は文字列と文字列の配列だけで、合計 3KB までです。Okta の token inline hook は、既定で 3 秒でタイムアウトし、リトライしません。失敗するとフローはそのまま続き、クレームの付かない元のトークンが返ります。Auth0 の post-login の Action は、リフレッシュトークンの交換のときにも実行され、予約名と衝突したクレームは黙って外れます。Cognito の発行前フックもリフレッシュのときに呼ばれ、既存と追加のクレームとスコープの合計に 5,000 の上限があります。Keycloak はマッパーで入れ、SPI で自作もできます。ここから言えるのは、独自クレームが無いトークンが実際に届く、ということです。受け手は、必要なクレームが無いときに拒否し、無いことを既定の権限ありと読んではいけません。',
      refs: { spec: 'Entra custom claims provider／Okta inline hooks／Auth0 login trigger／Cognito quotas', inst: 'OWASP ASVS 8.1.1〜8.1.3（認可ルールと属性の文書化）', book: '『実践 Keycloak』13.5 節 p.276・解答 pp.319–320（SPI による拡張）' },
    });
    L.table(s, [['IdP', '入れる仕組み', '失敗・衝突のとき', '上限'],
      ['Entra ID', 'custom claims provider（発行直前に REST）', '対応づけたものだけ入る。型は文字列と配列だけ', '合計 3KB'],
      ['Keycloak', 'プロトコルマッパー（SPI で自作も可）', 'マッパーが無ければ出ない', '軽量 AT で削る'],
      ['Auth0', 'post-login Action（RT 交換時も実行）', { text: '予約名と衝突すると黙って外れる', options: { color: HEX.accent3, bold: true } }, '合計 100KB'],
      ['Okta', '式・token inline hook', { text: '3 秒で打ち切り、リトライなし。クレームなしで出る', options: { color: HEX.accent3, bold: true } }, '式 1024 文字・groups 100 件'],
      ['Cognito', '発行前フック（リフレッシュ時も）', 'V1 では AT を変えられない', 'クレームとスコープで 5,000']],
    { x: 0.6, y: 1.95, w: 12.1, colW: [1.4, 3.8, 4.3, 2.6], fontSize: 12, rowH: 0.6 });
    L.note(s, 'leader', '受け手は fail-closed にする。必要な独自クレームが無いトークンは拒否し、「無い」を「既定の権限あり」と読まない', { x: 0.6, y: 5.75, w: 12.1, h: 0.75, size: 13 });
  }

  {
    const s = L.content('取り違えやすい点：同じ名前でも形と意味が違う', {
      lead: 'sub・scope・groups・aud・トークンの種類は、IdP ごとに形も意味も挙動も違う',
      stages: [3, 4],
      notes: '同じ名前のクレームが、IdP ごとに違う形や意味を持つ点をまとめます。sub は、Entra ID ではアプリごとに違い、Okta のアクセストークンではログイン名、Auth0 では IdP の種類と ID をつないだ文字列です。sub を共通のキーとして各サービスで使うと、IdP が変わったときに壊れます。scope は、Entra ID の scp と Cognito の scope は空白区切りの文字列ですが、Okta の scp は配列です。groups が上限を超えたときの挙動は、Entra ID は超過の印に置き換え、Okta は要求そのものを失敗させます。aud は、Cognito の既定のアクセストークンには無く、Keycloak は設定しないと API が入らず、Auth0 は userinfo を含む配列になることがあります。トークンの種類の見分け方も、Cognito は token_use、Entra ID は idtyp、RFC 9068 の形式なら typ の at+jwt と違います。受け手の各サービスが、これらをすべて正しく扱うのは現実的ではありません。次のスライドで、入口で吸収する考え方を示します。',
      refs: { spec: 'Entra／Okta／Auth0／Cognito／Keycloak の公式文書（Part 3 各スライド）', inst: 'OWASP JWT Cheat Sheet（トークンの種類の取り違え）' },
    });
    L.table(s, [['論点', 'IdP ごとの違い', '受け手の規則'],
      ['sub', 'Entra：アプリごと／Okta の AT：ログイン名／Auth0：IdP の種類|ID', '共通のキーは入口で決める'],
      ['scope の形', 'Entra の scp・Cognito の scope：空白区切り／Okta の scp：配列', '正規化した 1 つの形で渡す'],
      ['groups の超過', 'Entra：200 件超で超過の印に／Okta：100 件超で要求が失敗', '「無い」を「所属なし」と読まない'],
      ['aud', 'Cognito：既定で無い／Keycloak：設定が要る／Auth0：配列になる', '文字列と配列の両方を受け、無ければ拒否'],
      ['トークンの種類', 'Cognito：token_use／Entra：idtyp／RFC 9068：typ が at+jwt', '種類の確認を IdP ごとに実装する']],
    { x: 0.6, y: 1.95, w: 12.1, colW: [1.8, 6.0, 4.3], fontSize: 12, rowH: 0.62 });
    L.note(s, 'warn', '各サービスに IdP ごとの読み方を持たせると、IdP を足すたびに全サービスの修正が要る', { x: 0.6, y: 5.85, w: 12.1, h: 0.6, size: 13, label: '' });
  }

  {
    const s = L.content('IdP の差は入口で吸収する', {
      lead: 'IdP ごとの検証と対応づけは入口で 1 回だけ行い、内側のサービスには組織の形で渡す',
      stages: [2, 3, 5],
      notes: 'Part 3 のまとめです。4 つの IdP は、利用者のキー、テナント、aud、ロールの位置、独自クレームの入れ方がすべて違います。各サービスがこの違いを個別に扱うと、IdP を足したり、IdP の挙動が変わったりするたびに、全サービスを直すことになります。そこで、IdP ごとの検証と対応づけを入口で 1 回だけ行い、内側のサービスには組織が決めた形で渡します。入口では、IdP ごとに iss、aud、トークンの種類を検証し、Entra ID なら oid と tid、Okta なら uid というように、IdP ごとのキーを組織のキーに対応づけます。scope の形やロールの名前も、組織の語彙にそろえます。具体的な方法は、入口でのトークン交換や内部トークンの発行で、これは Part 6 で扱います。また、対応づけの表と、組織のクレームの台帳、共通の検証部品は、Part 11 のガバナンスで扱います。どちらの場合も、内側のサービスが読むのは組織の名前空間のクレームだけ、という状態を目指します。',
      refs: { spec: 'RFC 8693（トークン交換）／RFC 9068 §2.2.2', inst: 'CSRB 勧告 6（共通の認証ライブラリ）／NIST SP 800-162 §3.2.3.2', book: '『デジタルアイデンティティのすべて』（考え方）4.2.5・13.4.2 節 pp.35–36, 207–209' },
    });
    const idps = [['Entra ID', 'oid＋tid'], ['Keycloak', 'sub・organization'], ['Auth0／Okta', 'sub・org_id／uid'], ['Cognito', 'sub（token_use を確認）']];
    idps.forEach((d, i) => {
      L.box(s, [{ text: d[0], options: { bold: true, fontSize: 13, breakLine: true } }, { text: d[1], options: { fontSize: 11, bold: false } }], { x: 0.6, y: 1.95 + i * 0.95, w: 2.6, h: 0.8, fill: C.accent5 });
      L.arrow(s, 3.25, 2.35 + i * 0.95, 0.55, 'r', L.MUTED, 1.25);
    });
    L.card(s, { x: 3.9, y: 1.95, w: 3.7, h: 3.65, color: C.accent1, icon: 'MdHub', title: '入口（1 回だけ）', titleSize: 15, body: ['IdP ごとに iss・aud・種類を検証', 'IdP のキーを組織のキーへ', 'scope・ロールを組織の語彙へ', '無いクレームは拒否'], bodySize: 12.5, fill: C.background2 });
    L.arrow(s, 7.65, 3.75, 0.5, 'r', L.MUTED, 1.75);
    L.code(s, ['{', '  "iss": "https://sts.internal.example.com",', '  "sub": "u-7f3a…",', '  "aud": "https://orders.internal.example.com",', '  "https://claims.example.com/tenant": "t-042",', '  "https://claims.example.com/roles":', '    ["approver"]', '}'].join('\n'), { x: 8.25, y: 1.95, w: 4.45, h: 3.65, fontSize: 10 });
    L.note(s, 'leader', '内側のサービスが読むのは組織の名前空間のクレームだけにする。方法は Part 6（入口での交換）、対応表と台帳は Part 11', { x: 0.6, y: 5.8, w: 12.1, h: 0.7, size: 13 });
  }
};
