// Part 5: representing permissions for users, services and the system (principals, models, tenants, object-level checks)
module.exports = (L) => {
  const { C, SH, HEX } = L;
  L.section('Part 5 権限の表現');
  L.divider('PART 5', '権限の表現：利用者・サービス・システム', '誰の権限で、誰が実行し、どのテナントの、どのオブジェクトに対してか。クレームで運ぶ範囲と、都度判定する範囲を分ける',
    ['1 つのリクエストで、利用者とサービスをどう表すか', '粗い権限と細かい権限を、どこで分担するか', 'テナントをどう表し、どう検証するか', 'クレームだけで認可してはいけないのはどこか'],
    'Part 5 は、権限の表し方です。主体は利用者だけではありません。マイクロサービスやジョブなどのワークロード、そして運用者やバッチ、基盤そのものの操作もあります。この Part では、3 種類の主体と、それを 1 つのリクエストで同時に表す方法から始めます。次に、RBAC、ABAC、関係ベースという権限のモデルと、PEP と PDP の分担、粗い権限と細かい権限の分け方を扱います。さらに、ロール爆発、システムの権限、マルチテナント、オブジェクト単位の認可、代理の混乱を扱います。', { id: 'p05-part' });

  {
    const s = L.content('3 種類の主体：利用者・ワークロード・システム', { id: 'p05-three-principals',
      lead: '人だけが主体ではない。サービスと、基盤自身の操作も、別の種類の主体として表す',
      stages: [0, 4],
      notes: 'トークンが述べる主体には、3 つの種類があります。1 つ目は利用者で、社員、顧客、取引先の担当者です。IdP が発行するトークンの sub で表し、Entra ID なら oid と tid の組が安定したキーになります。2 つ目はワークロードで、マイクロサービス、ジョブ、エージェントなどです。SPIFFE ID、OAuth の client credentials、クラウドのサービスアカウントやマネージド ID で表します。3 つ目はシステムや基盤そのもので、クラウドのサービス、運用者、バッチなどです。AWS では、サービスにリンクされたロールがこれに当たり、サービスが事前に定義し、管理者も権限を編集できません。CloudEvents の Auth Context という拡張は、イベントを起こした主体を、app_user、user、service_account、api_key、system の 5 種類で区別しています。注意すべきは、RFC 9068 のアクセストークンでは、sub が利用者にもクライアントにもなることです。RFC 9700 §4.15.1 は、利用者とクライアントの識別子が同じ名前空間で重なりうる場合、認可サーバーが、受け手に両者を区別する手段を用意しなければならないと定めています。',
      refs: { spec: 'RFC 9068 §2.2・§5／RFC 9700 §4.15.1／SPIFFE JWT-SVID／CloudEvents', inst: 'NIST IR 8587 §5.3.1.6（ワークロードは短命・狭いスコープ）', book: '『デジタルアイデンティティのすべて』13.7.4.2 節 pp.226–227（考え方）' },
    });
    L.table(s, [['主体', '例', '代表的な表し方'],
      ['利用者', '社員、顧客、取引先の担当者', 'IdP のトークンの sub。Entra は oid＋tid'],
      ['ワークロード', 'マイクロサービス、ジョブ、エージェント', 'SPIFFE ID、client credentials、マネージド ID'],
      ['システム・基盤', 'クラウドのサービス、運用者、バッチ', 'AWS のサービスにリンクされたロール、FAS']],
    { x: 0.6, y: 1.95, w: 12.1, colW: [2.1, 4.4, 5.6], fontSize: 13, rowH: 0.6 });
    L.card(s, { x: 0.6, y: 4.55, w: 5.9, h: 1.95, color: C.accent5, icon: 'MdDataObject', title: 'CloudEvents の authtype', titleSize: 15, body: ['app_user・user：利用者', 'service_account・api_key：ワークロード', 'system：基盤が起こしたイベント'], bodySize: 12.5 });
    L.note(s, 'leader', 'RFC 9068 の sub は、利用者にもクライアントにもなる。名前空間が重なるなら、AS は受け手が区別できる手段を用意する（RFC 9700 §4.15.1 の MUST）', { x: 6.8, y: 4.55, w: 5.9, h: 1.95, size: 13.5 });
  }

  {
    const s = L.content('1 リクエストで運ぶ：誰の権限・誰が実行・どこ経由', { id: 'p05-one-request-carries',
      lead: '利用者の権限、実行しているワークロード、経由したサービスを、別々のクレームやチャネルで運ぶ',
      stages: [2, 3, 4],
      notes: '1 つのリクエストには、通常、複数の主体が関わります。利用者がブラウザで操作し、ゲートウェイが受け、サービス A がサービス B を呼びます。このとき、受け手が知りたいことは 1 つではありません。誰の権限で動いているか。誰が代理して実行しているか。どのワークロードが Txn-Token を求めたか。直接の通信相手は誰か。どこを経由してきたか。それぞれ答える仕組みが違うので、表では別の行にしました。誰の権限かは、トップレベルの sub で表します。誰が代理して実行しているかは、RFC 8693 の act で表します。RFC 8693 §4.1 では、最も外側の act が今の代理者で、入れ子の内側の act は過去の代理者です。アクセス制御に使ってよいのは、トップレベルのクレームと、今の代理者だけで、過去の代理者は参考の情報にとどまります。どのワークロードが Txn-Token を求めたかは、Transaction Tokens の草案 11 §9.2 の req_wl で表します。これは Txn-Token を発行させたワークロードで、今このリクエストを送ってきた相手とは限りません。直接の通信相手は、mTLS で相手が示した証明書、例えば SPIFFE の X.509-SVID の ID で確かめます。これはトークンのクレームではなく、接続の性質です。act、req_wl、mTLS の相手は、同じ「誰が実行しているか」に見えて、別の問いに答えます。1 つで他を代用すると、取り違えに気づけません。どこを経由したかは、AWS の FAS の aws:CalledVia のように、経由したサービスを別の属性として示します。Google の BeyondProd は、利用者の文脈を、完全性を保護した転送可能な切符として中央で発行し、サービスの ID とは別に運びます。Netflix の Passport も、入口で作る短命の内部の ID 構造です。大切なのは、これらを 1 つのクレームに混ぜないことです。NIST SP 800-228 は、呼び出し元のサービスとエンドユーザーの、それぞれの ID を認可するよう求めています。ASVS は、認可を元の主体の権限で判断し、仲介するサービスの権限で判断しないよう求めています。',
      refs: { spec: 'RFC 8693 §4.1／Txn-Token 草案 11 §9.2（req_wl）／SPIFFE X.509-SVID／AWS FAS（aws:CalledVia）', inst: 'NIST SP 800-228 REC-API-12（各 ID を認可）／ASVS 8.3.3' },
    });
    L.flow(s, [{ t: '利用者', d: 'ブラウザ', fill: C.accent5 }, { t: 'ゲートウェイ', d: '検証し、内部トークンへ' }, { t: 'サービス A', d: 'mTLS で自分を示す' }, { t: 'サービス B', d: 'sub・act・req_wl を確認', fill: C.accent4 }],
      { x: 0.6, y: 1.9, w: 12.1, h: 0.8, tSize: 14, dSize: 11.5 });
    L.table(s, [['問い', 'クレーム・チャネル', '実例'],
      ['誰の権限で', 'sub（トップレベル）', 'RFC 8693、Txn-Token の sub'],
      ['誰が代理して実行しているか', '最も外側の act（内側の act は過去の代理者）', 'RFC 8693 §4.1'],
      ['どのワークロードが Txn-Token を求めたか', 'req_wl（今の送り手とは限らない）', 'Txn-Token 草案 11 §9.2'],
      ['直接の通信相手は誰か', 'mTLS の相手の ID（クレームではない）', 'SPIFFE の X.509-SVID'],
      ['どこを経由したか', '経由を示す別の属性', 'AWS FAS の aws:CalledVia'],
      ['利用者の文脈ごと運ぶ', '完全性を保護した内部の切符', 'Google BeyondProd、Netflix Passport']],
    { x: 0.6, y: 2.85, w: 12.1, colW: [3.9, 4.6, 3.6], fontSize: 12, rowH: 0.4 });
    L.note(s, 'leader', 'act・req_wl・mTLS の相手は別の問いに答える。1 つで他を代用しない。認可は元の利用者の権限で判断する（ASVS 8.3.3）', { x: 0.6, y: 5.85, w: 12.1, h: 0.65, size: 13 });
  }

  {
    const s = L.content('権限のモデル：RBAC・ABAC・関係ベース', { id: 'p05-authz-models',
      lead: 'RBAC は役割だけを属性にした ABAC の特別な形。関係ベースは、主体と対象の関係で判定する',
      stages: [4],
      notes: '権限のモデルを 3 つに整理します。RBAC は、役割、つまりロールで許可を決める方式です。クレームとしては roles や groups が対応し、機能の粗い区別に向きます。弱点は、細かくしようとするとロールの数が増えることです。ABAC は、主体、対象、環境の属性で判定する方式です。トークンが運べるのは主体の安定した属性で、部署、地域、認証の強さなどに向きますが、設計とテストは難しくなります。『デジタルアイデンティティのすべて』は、RBAC を、ロールだけを属性とする ABAC の特別な形と位置づけています。関係ベースは、文書の所有者や共有先のような、主体と対象の関係で判定する方式で、Google の Zanzibar や OpenFGA がこの考え方です。関係は対象ごとに変わり、数も多いので、トークンには sub だけを載せ、関係は PDP が持ちます。『実践 Keycloak』は 8 章で、RBAC、グループ、スコープ、ABAC、中央集権型の認可を比べ、どれか 1 つに決める必要はなく併用してよいとしています。NIST IR 8587 も、権限をより細かく動的に定義できる形、例として ABAC で実装するよう求めています。',
      refs: { spec: 'RFC 9068 §2.2.3.1（roles・groups・entitlements）', inst: 'NIST SP 800-162（ABAC）／IR 8587 §4.1.4', book: '『デジタルアイデンティティのすべて』（考え方）12.2.5 節 p.194／『実践 Keycloak』8 章 pp.143–156' },
    });
    const ms = [['MdBadge', C.accent1, 'RBAC（役割）', [['判定：', '役割で許可を決める'], ['クレーム：', 'roles・groups'], ['向く：', '機能の粗い区別'], ['弱点：', '細かくするとロールが増える']]],
      ['MdRule', C.accent2, 'ABAC（属性）', [['判定：', '主体・対象・環境の属性'], ['クレーム：', '主体の安定した属性'], ['向く：', '部署・地域・認証の強さ'], ['弱点：', '設計とテストが難しい']]],
      ['MdAccountTree', C.accent6, '関係ベース', [['判定：', '所有者・共有先などの関係'], ['クレーム：', 'sub だけ。関係は PDP'], ['向く：', '文書・フォルダの共有'], ['例：', 'Zanzibar、OpenFGA']]]];
    ms.forEach((m, i) => L.card(s, { x: 0.6 + i * 4.1, y: 1.95, w: 3.9, h: 2.9, icon: m[0], color: m[1], title: m[2], titleSize: 16, body: m[3], bodySize: 12.5 }));
    L.note(s, 'leader', 'どのモデルでも、トークンが運ぶのは判定の入力の一部。関係とオブジェクト単位の判定は、PDP とデータの側に置く', { x: 0.6, y: 5.1, w: 12.1, h: 1.0, size: 13.5 });
  }

  {
    const s = L.content('PEP と PDP：クレームは判断の入力の 1 つ', { id: 'p05-pep-pdp',
      lead: 'サービス（PEP）がトークンを検証し、判断は方針（PDP）に任せる。足りない属性は PIP から補う',
      stages: [3, 4],
      notes: '認可の役割分担です。PEP は、要求を止めたり通したりする場所で、ゲートウェイや各サービスがこれに当たります。PDP は、方針に従って許可するかを判断する場所です。PIP は、判断に必要な属性を提供する源で、データベースやディレクトリです。PAP は、方針を管理する場所です。『デジタルアイデンティティのすべて』は、認可をこの 4 つに分け、ポリシーをコードから切り離して管理する考え方を示しています。トークンのクレームは、PDP が使う入力の一部にすぎません。主体の安定した属性はトークンから、関係やオブジェクトの属性は PIP から、IP アドレスや時刻のような環境の文脈は PEP が要求の時点で取ります。NIST IR 8587 は、認可の判断をトークンが有効かどうかだけで下すべきでなく、提示された文脈も考えるべきだとしています。NIST SP 800-207 も、アクセスは主体の ID、資産の状態、環境の属性を含む動的な方針で決めるとしています。『実践 Keycloak』は、hasRole のように判定をコードに書くと要件が変わるたびに再デプロイが要るので、canAccess のように判断を外に出す形を勧めています。',
      refs: { inst: 'NIST SP 800-162 §3（PEP・PDP）／IR 8587 §4.1.4／SP 800-207 §2.1 原則 4', book: '『デジタルアイデンティティのすべて』（考え方）12.3 節 pp.194–195／『実践 Keycloak』8.6 節 pp.154–155' },
    });
    L.box(s, '要求', { x: 0.6, y: 2.35, w: 1.6, h: 0.9, fill: C.accent5, fontSize: 15 });
    L.arrow(s, 2.25, 2.8, 0.5, 'r', L.MUTED, 1.75);
    L.box(s, [{ text: 'PEP', options: { bold: true, fontSize: 18, breakLine: true } }, { text: 'ゲートウェイ・サービス。トークンを検証', options: { fontSize: 12, bold: false } }], { x: 2.85, y: 2.0, w: 2.7, h: 1.6, fill: C.accent1 });
    L.arrow(s, 5.6, 2.8, 0.55, 'r', L.MUTED, 1.75);
    L.box(s, [{ text: 'PDP', options: { bold: true, fontSize: 18, breakLine: true } }, { text: '方針に従って判断', options: { fontSize: 12, bold: false } }], { x: 6.25, y: 2.0, w: 2.6, h: 1.6, fill: C.accent2 });
    L.box(s, [{ text: 'PIP  ', options: { bold: true, fontSize: 14 } }, { text: '属性の源（DB・ディレクトリ）', options: { fontSize: 12, bold: false } }], { x: 9.5, y: 2.0, w: 3.2, h: 0.7, fill: C.accent4 });
    L.box(s, [{ text: 'PAP  ', options: { bold: true, fontSize: 14 } }, { text: '方針の管理・レビュー', options: { fontSize: 12, bold: false } }], { x: 9.5, y: 2.9, w: 3.2, h: 0.7, fill: C.accent6 });
    L.arrow(s, 9.45, 2.35, 0.55, 'l', L.MUTED, 1.5);
    L.arrow(s, 9.45, 3.25, 0.55, 'l', L.MUTED, 1.5);
    L.table(s, [['判断の入力', '出どころ', '例'],
      ['主体の安定した属性', 'トークンのクレーム', 'sub、tenant_id、roles'],
      ['関係・オブジェクトの属性', 'PIP（DB・関係の保存先）', '所有者、共有先、文書の区分'],
      ['環境・文脈', 'PEP が要求の時点で取得', 'IP アドレス、時刻、端末の状態']],
    { x: 0.6, y: 3.9, w: 12.1, colW: [3.4, 4.0, 4.7], fontSize: 13, rowH: 0.48 });
    L.note(s, 'tip', 'トークンが有効かどうかだけで認可しない。提示された文脈も考える（IR 8587 §4.1.4）', { x: 0.6, y: 6.0, w: 12.1, h: 0.5, size: 12.5, label: '' });
  }

  {
    const s = L.content('粗い権限と細かい権限：3 層で分担する', { id: 'p05-coarse-fine-layers',
      lead: 'scope と roles は粗く、取引の中身は authorization_details、オブジェクトは都度判定',
      stages: [1, 4],
      notes: '権限の粒度に応じて、置き場所を 3 層に分けます。1 層目は粗い権限で、scope、roles、groups です。機能の範囲や役割のように、長く安定した値なので、トークンに載せます。RFC 9068 は、ロールやグループを載せるなら roles、groups、entitlements という名前を使うよう求めていますが、値の語彙は定めていないので、組織で決めます。2 層目は取引単位の権限で、RFC 9396 の authorization_details です。この支払い、この金額、この相手先、といった取引の中身を、型の付いたオブジェクトで表します。RFC 9396 は、JWT のアクセストークンに入れるときは、宛先に合わせて絞ったものを入れるよう勧めています。また、発行者は、知らない type や知らないフィールドを含む要求を拒否します。3 層目はオブジェクト単位の権限で、この文書を読めるか、この請求書を承認できるか、です。対象ごとに変わり数も多いので、トークンには載せず、PDP やデータベースで都度判定します。NIST IR 8587 も、アクセストークンに scope を含め、細かい権限には RAR、つまり authorization_details を使えるとしています。ASVS は、sub、scope、authorization_details があれば必ず判断に使うよう求めています。',
      refs: { spec: 'RFC 9396 §5・§9.1／RFC 9068 §2.2.3・2.2.3.1', inst: 'NIST IR 8587 §5.2.1.1（scope と RAR）／ASVS 10.3.2', book: '『セキュアAPI』7.7 節 pp.219–223' },
    });
    L.table(s, [['層', 'クレーム', '表すこと', '置き場所'],
      ['粗い', 'scope・roles・groups', '機能の範囲、役割', 'トークン（長く安定）'],
      ['取引単位', 'authorization_details', 'この支払い・この金額', 'トークン（宛先ごとに絞る）'],
      ['オブジェクト単位', { text: '載せない', options: { color: HEX.accent3, bold: true } }, 'この文書を読めるか', 'PDP・DB で都度判定']],
    { x: 0.6, y: 1.95, w: 12.1, colW: [2.2, 3.3, 3.2, 3.4], fontSize: 13, rowH: 0.58 });
    L.code(s, '// RFC 9396 §9.1 の例（抜粋）\n"authorization_details": [{\n  "type": "https://scheme.example.com/payment_initiation",\n  "actions": ["initiate", "status", "cancel"],\n  "instructedAmount": { "currency": "EUR", "amount": "123.50" },\n  "creditorName": "Merchant A" }]', { x: 0.6, y: 4.5, w: 6.7, h: 1.95, fontSize: 11 });
    L.note(s, 'tip', 'authorization_details は宛先に合わせて絞って入れる（§9.1）。知らない type やフィールドは、発行者が拒否する（§5）', { x: 7.5, y: 4.5, w: 5.2, h: 1.95, size: 13, label: '' });
  }

  {
    const s = L.content('scope と role：守る相手が違う', { id: 'p05-scope-vs-role',
      lead: 'scope はクライアントに委ねた範囲、role は利用者が持つ役割。トークンに入るのは両者の重なり',
      stages: [1, 4],
      notes: 'scope と role は、どちらも権限を表しますが、守る相手が違います。『実践 Keycloak』は、OAuth のスコープはクライアントからシステムを守り、RBAC は利用者からシステムを守る、と整理しています。scope は、利用者がクライアントに委ねた範囲で、利用者が持つ全権限ではありません。Keycloak では、トークンに入るロールは、利用者に割り当てたロールと、クライアントが使ってよいロールの積集合です。既定の Full Scope Allowed のままだと、利用者の全ロールが入るので、本番では切って、必要なロールだけに絞ります。IdP ごとの表し方は表のとおりです。Entra ID の scp は、クライアントが同意を得たスコープで、利用者のトークンにだけ入ります。Keycloak は、レルムのロールを realm_access に、クライアントのロールを resource_access に入れます。レルムのロールは組織全体で同じ意味、クライアントのロールはそのクライアント固有の意味として使い分けます。各 IdP の詳細は Part 3 で扱いました。',
      refs: { spec: 'Entra アクセストークンのクレーム／Keycloak サーバー管理ガイド', inst: 'ASVS 10.4.11（必要な scope だけを割り当てる）', book: '『実践 Keycloak』5.5.2 節 pp.77–81・8.4 節 pp.152–153' },
    });
    L.box(s, '利用者が持つロール', { x: 0.6, y: 2.0, w: 3.3, h: 0.95, fill: C.accent5, fontSize: 15 });
    L.T(s, '∩', { x: 3.95, y: 2.0, w: 0.5, h: 0.95, fontSize: 28, bold: true, align: 'center', valign: 'middle', margin: 0, color: C.text2 });
    L.box(s, 'クライアントが使えるロール', { x: 4.5, y: 2.0, w: 3.3, h: 0.95, fill: C.accent2, fontSize: 15 });
    L.arrow(s, 7.9, 2.475, 0.6, 'r', L.MUTED, 1.75);
    L.box(s, [{ text: 'トークンに入るロール', options: { bold: true, fontSize: 15, breakLine: true } }, { text: '本番は Full Scope Allowed を切る', options: { fontSize: 12, bold: false } }], { x: 8.6, y: 2.0, w: 4.1, h: 0.95, fill: C.accent4 });
    L.table(s, [['IdP', 'クライアントへの委任', '利用者・アプリの役割'],
      ['Entra ID', 'scp（利用者のトークンだけ。空白区切り）', 'roles・groups・wids'],
      ['Keycloak', 'scope', 'realm_access（全体）・resource_access（クライアント固有）'],
      ['Auth0', 'scope', 'permissions（RBAC を有効にしたとき）'],
      ['Cognito', 'scope（空白区切り）', 'cognito:groups（1 件でも配列）']],
    { x: 0.6, y: 3.2, w: 12.1, colW: [1.8, 4.4, 5.9], fontSize: 12.5, rowH: 0.5 });
    L.note(s, 'leader', 'scope は「クライアントに何を許したか」で、利用者の全権限ではない。両方を確かめる（各 IdP の詳細は Part 3）', { x: 0.6, y: 5.8, w: 12.1, h: 0.7, size: 13 });
  }

  {
    const s = L.content('ロール爆発：細かい権限をロールで表さない', { id: 'p05-role-explosion',
      lead: '役割 × テナント × 対象でロールを作ると、数が掛け算で増え、トークンも膨らむ',
      stages: [0, 4],
      notes: 'ロール爆発の例です。左は悪い例で、テナント、部署、対象、操作の組み合わせを、ロールの名前に焼き込んでいます。テナントが増えるたび、部署が増えるたびに、ロールの数が掛け算で増え、トークンも膨らみます。Entra ID では、groups が 200 件を超えると、groups の代わりに超過を示すクレームが入ります。右は分けた例です。役割は approver のような短い名前にし、テナントは独自クレームの tenant_id で別に運び、どの請求書を承認できるかは PDP やデータベースで判定します。『実践 Keycloak』は、ロールの数が爆発しないよう注意し、細かい権限をロールで表現しないよう求めています。複数のロールを渡したいときは、グループにロールを割り当てるほうが自然で、複合ロールは性能と管理の面で注意が要るとしています。『セキュアAPI』も、長いスコープや権限の一覧は、ロールにまとめよという兆候だと述べています。',
      refs: { spec: 'Entra グループの超過（groups overage）', inst: 'ASVS 8.1.1（認可ルールを文書化）', book: '『実践 Keycloak』8.2 節 pp.145–146／『セキュアAPI』7.7 節 pp.220–221' },
    });
    L.T(s, '悪い例：組み合わせをロール名に焼く', { x: 0.6, y: 1.95, w: 5.9, h: 0.35, fontSize: 13.5, bold: true, color: C.accent3, margin: 0 });
    L.code(s, '"roles": [\n  "t-042-invoice-approver",\n  "t-042-invoice-viewer",\n  "t-043-invoice-approver",\n  "t-042-ou-12-expense-approver",\n  … ]', { x: 0.6, y: 2.35, w: 5.9, h: 1.95, fontSize: 11 });
    L.T(s, '分ける：役割・テナント・対象', { x: 6.8, y: 1.95, w: 5.9, h: 0.35, fontSize: 13.5, bold: true, color: C.accent4, margin: 0 });
    L.code(s, '"roles": ["approver"],\n"https://claims.example.com/": {\n  "tenant_id": "t-042" }\n\n// どの請求書を承認できるかは PDP・DB で判定', { x: 6.8, y: 2.35, w: 5.9, h: 1.95, fontSize: 11 });
    const cs = [['細かい権限はロールにしない', ['ロールは役割の名前', '対象ごとの許可は PDP']], ['まとめるならグループ', ['複数のロールはグループに', '複合ロールは性能と管理に注意']], ['膨らむと上限に当たる', ['Entra は groups 200 件で置換', '長い一覧は集約の兆候']]];
    cs.forEach((c, i) => L.card(s, { x: 0.6 + i * 4.1, y: 4.55, w: 3.9, h: 1.95, color: C.accent1, title: c[0], titleSize: 15, titleColor: C.accent1, body: c[1], bodySize: 12.5 }));
  }

  {
    const s = L.content('システムの権限：バッチ・運用者・緊急時を分ける', { id: 'p05-system-privileges',
      lead: '利用者の権限を借りず、主体の種類が分かる形で発行する。運用者は実行者として名を残す',
      stages: [1, 4, 5],
      notes: '利用者ではない主体の権限です。夜間バッチは、ワークロード自身の権限で、client credentials でトークンを取ります。sub はクライアントになるので、受け手は利用者のトークンと区別できなければなりません。RFC 9700 §4.15.1 は、両者の識別子が同じ名前空間で重なりうるなら、認可サーバーが区別する手段を用意するよう求めています。長時間のジョブで利用者のトークンを持ち続けない話は Part 8 で扱います。運用者が顧客のデータを操作するときは、トークン交換で得た委任のトークンを使います。sub に対象の利用者、act に運用者が入り、監査で両方を記録します。緊急時の特権、いわゆる break-glass では、RFC 8693 の may_act、つまり「この主体の代理として行動してよい者」を示すクレームや act を使い、承認の記録と短い期限を確かめます。承認は、RAR や CIBA で取得できます。クラウドの基盤自身の操作には、AWS のサービスにリンクされたロールのような、サービス専用の ID があり、管理者もその権限を編集できません。NIST IR 8587 は、非人間の ID には狭いスコープの短命なトークンを使うよう求めています。',
      refs: { spec: 'RFC 8693 §4.1・§4.4（may_act）／RFC 9068 §2.2・§5／RFC 9700 §4.15.1', inst: 'NIST IR 8587 §5.3.1.6（非人間は短命・狭いスコープ）', book: '『OpenID Connect入門』12.5 節 pp.208–209（client credentials）' },
    });
    L.table(s, [['場面', '主体とトークン', 'クレームで示すこと', '確かめること'],
      ['夜間バッチ', 'ワークロード自身（client credentials）', 'sub はクライアント', '利用者のトークンと区別できるか'],
      ['運用者の操作', '交換で得た委任のトークン', 'sub に利用者、act に運用者', '監査で両方を記録'],
      ['緊急時の特権（break-glass）', '運用者のトークン＋承認', 'may_act・act、承認の ID', '承認（RAR・CIBA）と短い期限'],
      ['基盤の操作', 'サービスにリンクされたロール', 'サービス自身の ID', '管理者も権限を編集できない']],
    { x: 0.6, y: 1.95, w: 12.1, colW: [2.4, 3.3, 3.1, 3.3], fontSize: 12.5, rowH: 0.7 });
    L.note(s, 'warn', '運用者が利用者として振る舞うと、sub だけでは区別できない。act で実行者を残し、承認と期限を確かめる', { x: 0.6, y: 5.65, w: 12.1, h: 0.8, size: 13.5, label: '' });
  }

  {
    const s = L.content('マルチテナント：iss と tid の両方で確かめる', { id: 'p05-multitenancy',
      lead: 'テナントの表し方は 3 通り。どれでも、発行者・テナント・保存データのテナントを照合する',
      stages: [1, 3, 4],
      notes: 'マルチテナントでのテナントの表し方は、3 通りあります。1 つ目は、テナントごとに発行者を分ける方法です。Keycloak のレルムがそうで、発行者の URL にレルムの名前が入るので、iss がレルムごとに違います。2 つ目は、テナントのクレームを入れる方法です。Entra ID の tid、Auth0 の org_id がこれに当たり、ID-JAG の草案は、マルチテナントの発行者に tenant クレームを必須としています。テナントを表す登録済みのクレームはないので、独自クレームを作る正当な余地があります。3 つ目は、テナントを含む resource の URI で宛先を分ける方法です。どの方法でも、受け手は下の 4 点を確かめます。署名の鍵がそのテナントのものか、iss が許可したテナントの発行者か、tid が iss の中のテナントと一致するか、保存データのテナントが tid と一致するか、です。Entra ID のマルチテナント用のメタデータでは、iss は {tenantid} を含むテンプレートなので、トークンの tid で置き換えてから完全一致で比べます。NIST IR 8587 は、署名鍵を単一のテナントのような最小の単位にスコープするよう求めています。',
      refs: { spec: 'Entra アクセストークンの検証／RFC 8707 §3／RFC 8725 §3.8・§3.9', inst: 'NIST IR 8587 §5.2.1.2（テナント単位の鍵）／ASVS 8.4.1', book: '『実践 Keycloak』1.4.1.1 節 p.11・4.3 節 p.46（レルム）' },
    });
    L.table(s, [['表し方', '例', '受け手の確認'],
      ['テナントごとの発行者', 'Keycloak のレルム（iss がレルムごと）', 'iss を許可リストと完全一致'],
      ['テナントのクレーム', 'Entra の tid、Auth0 の org_id、ID-JAG の tenant', 'iss の {tenantid} を tid で置換して一致'],
      ['テナントごとの宛先', 'テナントを含む resource の URI', 'aud に自分のテナントが含まれるか']],
    { x: 0.6, y: 1.95, w: 12.1, colW: [2.6, 4.8, 4.7], fontSize: 12.5, rowH: 0.58 });
    L.flow(s, [{ t: '署名の鍵', d: 'テナント単位の鍵か', fill: C.accent5 }, { t: 'iss', d: '許可したテナントの発行者か' }, { t: 'tid', d: 'iss の中のテナントと一致' }, { t: '保存データ', d: '行のテナント＝tid', fill: C.accent4 }],
      { x: 0.6, y: 4.5, w: 12.1, h: 1.0, tSize: 15, dSize: 12 });
    L.note(s, 'leader', '署名鍵はテナント単位にスコープする（IR 8587 §5.2.1.2）。共有の発行者は、他のテナントのトークンも通しうる', { x: 0.6, y: 5.7, w: 12.1, h: 0.75, size: 13 });
  }

  {
    const s = L.content('テナントをまたぐ：利用者・運用者・取引先', { id: 'p05-cross-tenant',
      lead: 'またぐ場面ごとに、識別子と権限の出し方を変える。テナントをまたいだ暗黙の名寄せはしない',
      stages: [1, 2, 4],
      notes: 'テナントをまたぐ場面は 3 つあります。1 つ目は、複数のテナントに属する利用者です。Entra ID の oid は、テナントが違えば別の値になります。Microsoft は、tid と oid を複合キーにし、データアクセスのキーに tid を含め、idp クレームでテナントをまたいだ名寄せをしないよう求めています。2 つ目は、テナントをまたいで作業する運用者です。運用者は顧客になりすますのではなく、トークン交換で得た委任のトークン（sub は顧客、act は運用者）で実行者として名を残し、承認と期限を確かめ、監査で顧客の sub と運用者の act を両方記録します。3 つ目は、取引先、つまり B2B です。自社の発行者でトークン交換をして、相手のドメインの発行者に渡し、相手の発行者が自分たちの語彙にクレームを変換し直して、短命のトークンを発行します。外部の取引先には、ペアワイズ、つまり相手ごとに異なる識別子を出します。OWASP の Workload Identity Federation Cheat Sheet は、共有の発行者を信頼すると、他のテナントのトークンも受け入れてしまう危険を指摘しています。ドメインをまたぐ流れの例は、Part 6 で扱います。',
      refs: { spec: 'Entra ID トークンのクレーム／RFC 8693 §4.1／identity-chaining 草案', inst: 'ASVS 8.4.1（テナント横断の制御）／OWASP WIF CS', book: '『デジタルアイデンティティのすべて』4.2.4 節 pp.33–35（考え方）' },
    });
    const cs = [['MdPerson', C.accent1, '複数テナントの利用者', ['Entra の oid はテナントごとに別', 'tid＋oid を複合キーに', 'idp で名寄せしない']],
      ['MdSupportAgent', C.accent2, 'テナント横断の運用者', ['交換で得た委任のトークン', '承認と期限を確かめる', 'sub と act を両方記録']],
      ['MdBusiness', C.accent5, '取引先（B2B）', ['トークン交換で相手の発行者へ', '相手が自分の語彙に変換', '外にはペアワイズの識別子']]];
    cs.forEach((c, i) => L.card(s, { x: 0.6 + i * 4.1, y: 1.95, w: 3.9, h: 2.65, icon: c[0], color: c[1], title: c[2], titleSize: 15, body: c[3], bodySize: 12.5 }));
    L.code(s, '// 運用者がテナント t-042 の利用者のために操作する\n{ "sub": "u-7f3a…",\n  "act": { "sub": "op-118" },\n  "https://claims.example.com/": { "tenant_id": "t-042" } }', { x: 0.6, y: 4.85, w: 7.2, h: 1.6, fontSize: 11 });
    L.note(s, 'tip', '取引先の API は自分宛ての aud だけを受け入れ、クレームを自分の語彙に変換し直す（流れの例は Part 6）', { x: 8.0, y: 4.85, w: 4.7, h: 1.6, size: 13, label: '' });
  }

  {
    const s = L.content('BOLA：クレームはオブジェクトの確認を代わらない', { id: 'p05-bola',
      lead: 'roles に approver があっても、この請求書を承認できるかは分からない。データ側の照合が要る',
      stages: [4],
      notes: 'OWASP の API Security Top 10 の 1 位は、BOLA、つまりオブジェクト単位の認可の不備です。利用者が指定した ID でデータを取り出すすべての処理で、そのオブジェクトにアクセスしてよいかを確かめる必要があります。トークンのクレームは、誰か、どのテナントか、どんな役割かを運ぶだけで、この請求書を読めるかは教えてくれません。認可は 3 段で考えます。1 段目でトークンを検証し、2 段目で roles や scope から機能を使ってよいかを確かめます。これを怠ると、機能単位の認可の不備、BFLA になります。3 段目で、データの側でオブジェクトとの関係を確かめます。『セキュアAPI』は、BOLA の修正として、クエリの条件に所有者がトークンの sub であることを加える例を示しています。存在を隠したいなら 404、存在を示してよいなら 403 を返し、利用者 A と B を使った自動テストで回帰を防ぐよう勧めています。また、ゲートウェイや WAF は BOLA を防げないと注意しています。データ層での行単位の制御は Part 7 で扱います。',
      refs: { inst: 'OWASP API Security Top 10 2023 API1・API5／ASVS 8.2.2', book: '『セキュアAPI』4.3 節 pp.101–103・4.7–4.8 節 pp.120–124・2.3.4 節 p.058' },
    });
    L.flow(s, [{ t: '1. トークンを検証', d: '署名・iss・aud・exp・typ', fill: C.accent5 }, { t: '2. 機能を使えるか', d: 'roles・scope（BFLA を防ぐ）' }, { t: '3. このオブジェクトか', d: '所有者・テナントをデータ側で照合（BOLA を防ぐ）', fill: C.accent3 }],
      { x: 0.6, y: 1.95, w: 12.1, h: 1.1, tSize: 15, dSize: 12 });
    L.code(s, '-- 悪い例：ID だけで取り出す\nSELECT * FROM invoices WHERE id = :id;\n\n-- 良い例：トークンのテナントと主体で絞る\nSELECT * FROM invoices\n WHERE id = :id AND tenant_id = :tid\n   AND owner_id = :sub;', { x: 0.6, y: 3.3, w: 6.7, h: 2.1, fontSize: 11 });
    L.card(s, { x: 7.5, y: 3.3, w: 5.2, h: 2.1, color: C.accent3, icon: 'MdFactCheck', title: '照合で決めること', titleSize: 15, body: ['隠すなら 404、示してよいなら 403', 'ゲートウェイ・WAF は BOLA を防げない', '利用者 A・B の自動テストで回帰を防ぐ'], bodySize: 12.5 });
    L.note(s, 'leader', 'クレームは「誰か」「どのテナントか」を運ぶだけ。オブジェクトとの関係は、毎回データの側で確かめる（データ層は Part 7）', { x: 0.6, y: 5.6, w: 12.1, h: 0.85, size: 13.5 });
  }

  {
    const s = L.content('代理の混乱：連鎖を見せ、自分宛てだけを受ける', { id: 'p05-confused-deputy',
      lead: '仲介するサービスが、他人の権限と自分の権限を取り違える。経路をクレームで示し、宛先を確かめる',
      stages: [2, 3, 4],
      notes: '代理の混乱、confused deputy は、仲介するサービスが、呼び出し元の権限と自分の権限を取り違える問題です。たとえば、サービス A が利用者の依頼でサービス B を呼ぶときに、自分の広い権限で呼んでしまうと、B は誰の権限で動いているのか分かりません。対策は表のとおりです。まず、経路を見せます。RFC 8693 の act をネストさせると、委任の連鎖を記録できます。ただし、アクセス制御に使ってよいのは、トップレベルのクレームと今の実行者だけで、ネストした過去の実行者は情報としてだけ扱います。AWS は、サービス間の代理の混乱に対して、aws:SourceArn や aws:SourceAccount で、自分のために動いているサービスかを確かめるよう求めています。MCP の仕様は、受け取ったトークンをそのまま次へ渡すことを禁じ、自分宛てに発行されたトークン以外を受け入れてはならないとしています。AWS の FAS では、IP や VPC のような文脈は、ホップをまたぐと引き継がれないことがあるので、経由したことは CalledVia という別の属性で示します。ホップごとの交換と絞り方は Part 6、AI エージェントは Part 10 で扱います。',
      refs: { spec: 'RFC 8693 §4.1／MCP Security Best Practices／AWS confused deputy・FAS', inst: 'NIST SP 800-228 §2.7.6（confused deputy）／ASVS 8.3.3' },
    });
    L.flow(s, [{ t: '利用者', d: 'sub = u-7f3a…', fill: C.accent5 }, { t: 'サービス A（仲介）', d: '自分の広い権限で B を呼ぶと…', fill: C.accent2 }, { t: 'サービス B', d: '誰の権限か分からない', fill: C.accent3 }],
      { x: 0.6, y: 1.95, w: 12.1, h: 0.95, tSize: 15, dSize: 12 });
    L.table(s, [['対策', '中身', '出典'],
      ['経路を見せる', 'act のネストで委任の連鎖を記録する', 'RFC 8693 §4.1'],
      ['判断は今の実行者まで', 'ネストした過去の act は情報としてだけ使う', 'RFC 8693 §4.1'],
      ['自分のための代理か', 'aws:SourceArn・SourceAccount を確かめる', 'AWS の confused deputy'],
      ['トークンをそのまま渡さない', '自分宛て以外は受け入れない（MUST NOT）', 'MCP の仕様'],
      ['経由を別の属性に', 'CalledVia。IP などの文脈はホップで消える', 'AWS FAS']],
    { x: 0.6, y: 3.1, w: 12.1, colW: [3.1, 5.8, 3.2], fontSize: 12.5, rowH: 0.46 });
    L.note(s, 'tip', 'ホップごとの交換と絞り方は Part 6、AI エージェントの委任は Part 10 で扱う', { x: 0.6, y: 6.0, w: 12.1, h: 0.5, size: 12.5, label: '' });
  }
};
