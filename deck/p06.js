// Part 6: flows - where claims are added, narrowed, propagated, audited and returned
module.exports = (L) => {
  const { C, SH, HEX } = L;
  L.section('Part 6 流れ');
  L.divider('PART 6', '流れ：どこで足し、どこで絞るか', 'クレームは発行時だけでなく、入口・サービス間・追加認証・承認でも生まれる。段階ごとに書き手と寿命を決め、下流ほど絞る',
    ['クレームは、どの段階で誰が足すのか', '下流へ渡すとき、何をどこまで絞るのか', 'IP や端末の情報を、トークンに入れてよいか', '誰が・どの経路で・何の承認で動いたかを、どう残すか'],
    'Part 6 は、クレームの流れを扱います。クレームは IdP がログインのときに一度だけ書くもの、と考えがちですが、実際には、発行時のフック、入口のゲートウェイ、サービス間の伝搬、追加認証、承認の各段階で足されたり、作り替えられたりします。この Part では、段階ごとに足してよいものと足してはいけないもの、下流へ渡すときの絞り方、アクセス元の情報の扱い、クレームを HTTP ヘッダーに移すときの信頼境界、証跡の残し方、処理結果の返し方を順に見ます。最後に、ブラウザから DB まで、マルチテナント、取引先との API、イベント駆動の 4 つの流れで、各ホップのトークンとクレームを確かめます。夜間バッチと AI エージェントの流れは、Part 8 と Part 10 で扱います。');

  // helper: numbered rule grid (2 columns x 5 rows)
  const ruleGrid = (s, items) => {
    items.forEach((t, i) => {
      const col = Math.floor(i / 5), row = i % 5;
      const x = 0.6 + col * 6.15, y = 1.95 + row * 0.9;
      s.addShape(SH.ROUNDED_RECTANGLE, { x, y, w: 5.95, h: 0.78, rectRadius: 0.08, fill: { color: C.background2 }, line: { color: C.background2 } });
      s.addText(String(i + 1), { shape: SH.OVAL, x: x + 0.15, y: y + 0.14, w: 0.5, h: 0.5, fill: { color: C.accent1 }, line: { color: C.accent1 }, fontSize: 14, bold: true, color: C.background1, align: 'center', valign: 'middle', margin: 0 });
      L.T(s, t, { x: x + 0.8, y: y + 0.06, w: 5.0, h: 0.66, fontSize: 13, valign: 'middle', margin: 0 });
    });
  };

  {
    const s = L.content('段階の地図：クレームは 6 か所で生まれる', {
      lead: '段階ごとに、足してよいものと足してはいけないものが違う。寿命と書き手が違うから',
      stages: [1, 2],
      notes: 'クレームが生まれる場所を 6 つの段階に分けた地図です。1 つ目は IdP での認証時で、認証の方式、時刻、強さを表す acr、amr、auth_time が入ります。ここに業務の権限の詳細を入れないのは、認証の事実と権限では、寿命も変わる頻度も違うからです。2 つ目は発行時のフックで、テナント ID や課金プラン、粗いロールのような比較的安定した属性を足します。残高やリスクスコアのように秒単位で変わる値や、生年月日のような生の個人情報は入れません。3 つ目は入口のゲートウェイで、内部用のトークンへの作り替えや、主体 ID の正規化をします。クライアントが送ってきた同名のヘッダーの値は使いません。4 つ目はサービス間で、呼び出し全体で変わらない文脈と取引 ID を運びます。外部から受け取ったアクセストークンそのものは入れません。5 つ目の追加認証と 6 つ目の承認では、より新しい認証の事実や、承認された取引の内容が加わります。段階ごとに書き手を 1 つに決めておくことが、後の検証と監査の前提になります。',
      refs: { spec: 'RFC 9470／RFC 9396 §9／Transaction Tokens 草案 11 §9.2・§13.4', inst: 'NIST SP 800-228 §2.7（資格情報の正規化）', book: '『セキュアAPI』9.1 節 pp.260–268（ゲートウェイの役割）' },
    });
    L.table(s, [['段階', '代表的な仕組み', '足してよいもの', '足してはいけないもの'],
      ['① 認証時（IdP）', 'acr・amr・auth_time', '認証の事実（方式・時刻・強さ）', '業務の権限の詳細'],
      ['② 発行時フック', 'Entra・Auth0・Okta・Cognito・Keycloak', 'テナント ID・プラン・粗いロール', '秒単位で変わる状態、生の個人情報'],
      ['③ 入口', 'phantom token・Passport・ext_authz', '内部用トークン、正規化した主体 ID', 'クライアントが送った同名ヘッダーの値'],
      ['④ サービス間', 'Transaction Tokens・mTLS（SPIFFE）', '呼び出し全体で不変の文脈、取引 ID', '外部のアクセストークンそのもの'],
      ['⑤ 追加認証', 'RFC 9470（step-up）', 'より強い・より新しい認証の事実', '—'],
      ['⑥ 承認・同意', 'RAR・CIBA', '承認された取引の内容（金額・相手先）', '承認していない操作']],
    { x: 0.6, y: 1.95, w: 12.1, colW: [2.2, 3.5, 3.3, 3.1], fontSize: 12, rowH: 0.55, colColor: { 3: HEX.accent3 } });
    L.note(s, 'leader', 'クレームの台帳に「どの段階で、誰が書くか」の列を持つ。段階ごとに書き手を 1 つに決める（Part 4）', { x: 0.6, y: 5.95, w: 12.1, h: 0.6, size: 13, label: '' });
  }

  {
    const s = L.content('発行時フック：失敗しても、トークンは出る', {
      lead: '外部 API を呼んで足すクレームは、遅延・上限・失敗で欠けうる。受け手は欠けたら拒否する',
      stages: [1, 3],
      notes: '発行時フックは、トークンを発行する直前に外部の API を呼び、クレームを足す仕組みです。便利ですが、外部呼び出しなので遅れたり失敗したりします。Okta のトークンのインラインフックは、既定で 3 秒で打ち切られ、リトライしません。失敗しても認証の流れは続き、クレームの付いていない元のトークンがそのまま発行されます。Entra の custom claims provider は、claims mapping policy で明示的に対応付けたクレームだけがトークンに入り、返せる型は文字列と文字列の配列だけ、合計 3KB までです。Auth0 の post-login Action はログインの後だけでなく、リフレッシュトークンの交換のときにも実行されます。Cognito の発行前トリガーも、リフレッシュのときに呼ばれます。ここから導かれる受け手の規則は、独自クレームが無いときに「権限なし」として拒否することです。既定の権限があると解釈してはいけません。また、Entra のサンプルは生年月日を返していますが、生の個人情報をフックで足すのは最小化の原則に反します。各 IdP の詳細は Part 3 で扱いました。',
      refs: { spec: 'Okta Inline Hooks／Entra custom claims provider／Auth0 Login Trigger', inst: 'NIST SP 800-63C-4 §3.12.2（派生属性値）／IR 8587 §5.2.1.1', book: '『実践 Keycloak』4.5.2 節 pp.56–58（マッパーでクレームにする）' },
    });
    L.table(s, [['IdP の仕組み', 'いつ呼ばれるか', '制約と挙動'],
      ['Okta token inline hook', 'カスタム AS の発行時', { text: '既定 3 秒で打ち切り、リトライなし。失敗するとクレームなしで発行', options: { color: HEX.accent3, bold: true } }],
      ['Entra custom claims provider', '発行の直前', '対応付けたものだけ。文字列と文字列配列、合計 3KB'],
      ['Auth0 post-login Action', 'ログイン後と、リフレッシュ時', '同期実行。終わるまで後続が待つ'],
      ['Cognito pre token generation', '発行時。リフレッシュ時も', 'スコープの追加・抑止は V2_0 以上'],
      ['Keycloak protocol mapper', 'トークンの生成時', '属性はマッパーを置いて初めてクレームになる']],
    { x: 0.6, y: 1.95, w: 8.0, colW: [2.6, 2.1, 3.3], fontSize: 11.5, rowH: 0.66 });
    L.card(s, { x: 8.85, y: 1.95, w: 3.85, h: 2.45, icon: 'MdRule', color: C.accent1, title: '受け手の規則', titleSize: 15, body: ['クレームが無ければ拒否する', '無い＝権限なし。既定の権限にしない', '大きな権限表は載せず PDP へ', '安定した属性だけを載せる'], bodySize: 12 });
    L.note(s, 'warn', 'Entra のサンプルは生年月日を返す。生の個人情報はフックで足さない（Part 9）', { x: 8.85, y: 4.55, w: 3.85, h: 1.4, size: 12.5 });
  }

  {
    const s = L.content('入口での交換：外の形式を、内側に持ち込まない', {
      lead: '外部のトークンは入口で検証して終わらせ、内部専用のトークンに作り替える（腐敗防止層）',
      stages: [1, 2],
      notes: '外部から来る資格情報は、ブラウザの Cookie、参照型のアクセストークン、取引先のトークン、IdP ごとに形の違う JWT とさまざまです。これをそのまま内部のサービスに流すと、各サービスがすべての形式を理解しなければならず、外部の都合が内部に染み込みます。そこで入口で外部の資格情報を検証して終わらせ、内部専用の形に作り替えます。ドメイン駆動設計の言葉でいう腐敗防止層です。Curity の phantom token は、クライアントには参照型のトークンを渡し、入口でイントロスペクションして JWT に差し替えます。split token は JWT の署名部分だけをクライアントに渡します。Netflix の Passport は、入口でさまざまなトークンを終わらせ、内部には HMAC で保護した短命の構造だけを流し、各サービスには専用のライブラリで読ませます。Cloudflare Access は、自前の JWT をオリジン向けに発行しますが、IdP の独自属性は custom クレームに best-effort で入り、約 1KB を超えると切り捨てられます。NIST SP 800-228 も、入口で外部の資格情報を内部標準の形に変換することを挙げています。変換層の運用は Part 11 で扱います。',
      refs: { spec: 'Curity Phantom・Split Token／Cloudflare Access app token', inst: 'NIST SP 800-228 §2.7／OWASP Identity Propagation CS（内部アサーション）', book: '『セキュアAPI』9.1 節 pp.260–268' },
    });
    const ext = ['ブラウザの Cookie', '参照型のアクセストークン', '取引先・IdP ごとの JWT'];
    ext.forEach((t, i) => {
      const y = 1.95 + i * 0.55;
      L.box(s, t, { x: 0.6, y, w: 2.9, h: 0.45, fill: C.background2, color: C.text1, lineColor: L.BORDER, fontSize: 12, bold: false });
      L.arrow(s, 3.52, y + 0.225, 0.35, 'r', L.MUTED, 1.25);
    });
    L.box(s, [{ text: '入口（ゲートウェイ）', options: { bold: true, fontSize: 14, breakLine: true } }, { text: '検証して終わらせ、正規化する', options: { fontSize: 11.5 } }], { x: 3.9, y: 2.0, w: 2.9, h: 1.3, fill: C.accent1 });
    L.arrow(s, 6.85, 2.65, 0.45, 'r', L.MUTED, 1.75);
    L.box(s, [{ text: '内部トークン', options: { bold: true, fontSize: 14, breakLine: true } }, { text: '正規化した主体 ID・認証レベル・内部の aud', options: { fontSize: 11.5 } }], { x: 7.4, y: 2.0, w: 2.9, h: 1.3, fill: C.accent5 });
    L.arrow(s, 10.35, 2.65, 0.4, 'r', L.MUTED, 1.75);
    L.box(s, [{ text: 'サービス群', options: { bold: true, fontSize: 14, breakLine: true } }, { text: '内部の形だけを読む', options: { fontSize: 11.5 } }], { x: 10.8, y: 2.0, w: 1.9, h: 1.3, fill: C.accent4 });
    L.table(s, [['方式', '入口でしていること', 'クレームの扱い'],
      ['Phantom token（Curity）', 'クライアントには参照型。入口でイントロスペクションし JWT に差し替え', 'クライアントにはクレームが見えない'],
      ['Split token（Curity）', 'JWT の署名部分だけを渡し、入口で本体と連結', 'イントロスペクションの往復が要らない'],
      ['Netflix Passport', 'Cookie・端末のトークン・取引先のトークンを入口で終わらせる', '内部は HMAC で守った短命の構造。専用ライブラリで読む'],
      ['Cloudflare Access', 'IdP の認証を終え、オリジン向けに自前の JWT を発行', { text: 'IdP の独自属性は best-effort。約 1KB 超で切り捨て', options: { color: HEX.accent3 } }]],
    { x: 0.6, y: 3.6, w: 12.1, colW: [2.6, 5.0, 4.5], fontSize: 11.5, rowH: 0.56 });
  }

  {
    const s = L.content('Transaction Tokens：呼び出し全体の文脈を運ぶ', {
      lead: '入口で発行し、サービス間は Txn-Token ヘッダーで改変せずに渡す。寿命は分以下',
      stages: [1, 2, 3],
      notes: 'Transaction Tokens は、IETF の OAuth ワーキンググループで標準化中の仕様で、2026 年 11 月時点の最新は草案 11 です。外部のアクセストークンを内部に流す代わりに、入口で 1 回、トランザクショントークンサービス（TTS）から短命のトークンを発行してもらい、呼び出しの連鎖全体でそれを運びます。必須のクレームは、取引の一意の ID である txn、取引の主体の sub、TTS が決める最も狭い目的を表す scope、発行を求めたワークロードの req_wl、信頼ドメインを表す aud です。推奨のクレームとして、呼び出し全体で変わらない文脈の tctx と、要求元の IP などの環境の rctx があります。古い資料にある purp と azd は改名前の名前で、今は scope と tctx です。送るときは Txn-Token という専用のヘッダーを使い、Authorization ヘッダーは使ってはいけません。アクセストークンとして使うことも、外部のアクセストークンを中に含めることも禁止です。作り直すときは、権限を減らすことと値を足すことはできますが、scope を広げることや、txn・sub・aud を変えることはできません。寿命は分以下で、トークン全体をログに出すことも禁止されています。',
      refs: { spec: 'Transaction Tokens 草案 11 §6・§9.2・§12・§13.4・§13.15・§15.2', inst: 'NIST IR 8587 §5.3.1.6（ワークロードは短命・狭い範囲）' },
    });
    L.T(s, '例：入口が取得した Txn-Token（ヘッダー typ は txntoken+jwt）', { x: 0.6, y: 1.95, w: 5.9, h: 0.35, fontSize: 12, bold: true, margin: 0, valign: 'middle' });
    L.code(s, '{\n  "aud": "trust-domain.example.com",\n  "txn": "97053963-771d-…",\n  "sub": "u-7f3a…",\n  "scope": "orders.create",\n  "req_wl": "gateway.example.com",\n  "tctx": { "tenant": "t-042", "action": "CREATE" },\n  "rctx": { "req_ip": "203.0.113.7" },\n  "iat": 1795…, "exp": 1795…\n}', { x: 0.6, y: 2.35, w: 5.9, h: 2.75, fontSize: 11 });
    L.note(s, 'tip', '作り直すとき、権限を減らす・値を足すのは可。scope の拡大と txn・sub・aud の変更は不可', { x: 0.6, y: 5.3, w: 5.9, h: 1.2, size: 12.5, label: '' });
    L.table(s, [['クレーム', '要否', '意味'],
      ['txn', '必須', '取引の一意の ID（監査・リプレイ検知）'],
      ['sub', '必須', '取引の主体。信頼ドメイン内で一意'],
      ['scope', '必須', '最も狭い目的。TTS が決める'],
      ['req_wl', '必須', 'Txn-Token を求めたワークロード'],
      ['aud', '必須', '信頼ドメイン。その外では受け入れない'],
      ['tctx', '推奨', '呼び出し全体で変わらない文脈'],
      ['rctx', '推奨', '要求元の IP などの環境']],
    { x: 6.8, y: 1.95, w: 5.9, colW: [1.2, 0.9, 3.8], fontSize: 11.5, rowH: 0.42 });
    L.note(s, 'warn', 'Authorization ヘッダーで送らない。アクセストークンにしない。全体をログに出さない。旧名 purp・azd は使わない', { x: 6.8, y: 5.45, w: 5.9, h: 1.05, size: 12.5, label: '' });
  }

  {
    const s = L.content('追加認証と承認：その場で求め、結果を足す', {
      lead: '認証の強さは発行時点の事実。高リスクの操作では受け手が判断し、追加認証や承認を求める',
      stages: [1, 4],
      notes: 'トークンの acr や auth_time は、トークンが発行された時点の事実にすぎません。送金や削除のような高リスクの操作のときに、もっと強い、あるいはもっと新しい認証が必要なら、受け手であるリソースサーバーがその場で判断して要求します。RFC 9470 では、リソースサーバーが WWW-Authenticate ヘッダーで insufficient_user_authentication というエラーを返し、必要な acr_values や max_age を伝えます。クライアントはその値で認可要求を組み立て直し、利用者が追加の認証をして、新しいアクセストークンを得ます。Entra では、acrs クレームと xms_cc の組で同じことをします。承認については、RFC 9396 の authorization_details で、金額や相手先のような承認された取引の内容をトークンに入れられます。JWT に入れるときは、宛先ごとに絞ることが推奨されています。CIBA は、利用者が別の端末で承認する仕組みで、結果の受け取り方は poll、ping、push の 3 つです。要点は、追加認証を起動するのはトークンのクレームではなく受け手の判断だ、ということです。AI エージェントの承認は Part 10 で扱います。',
      refs: { spec: 'RFC 9470／RFC 9396 §9.1・§9.2／CIBA Core §5', inst: 'NIST SP 800-63C-4 §4.7（認証の新しさ）／OWASP ASVS 10.3.4' },
    });
    L.T(s, '追加認証（RFC 9470 step-up）', { x: 0.6, y: 1.95, w: 6, h: 0.35, fontSize: 13, bold: true, margin: 0, valign: 'middle' });
    L.flow(s, [
      { t: 'API が拒否', d: 'insufficient_user_authentication と acr_values・max_age', fill: C.accent3 },
      { t: 'クライアント', d: '値を使って認可要求を組み立て直す', fill: C.accent5 },
      { t: 'IdP', d: '追加の認証をして新しいトークン', fill: C.accent5 },
      { t: 'API', d: 'acr・auth_time を確かめて実行', fill: C.accent1 }],
    { x: 0.6, y: 2.35, w: 12.1, h: 1.3, tSize: 14, dSize: 11.5 });
    L.card(s, { x: 0.6, y: 3.9, w: 5.9, h: 1.85, icon: 'MdFactCheck', color: C.accent2, title: '承認の内容：RAR（authorization_details）', titleSize: 14, body: ['承認された金額・相手先などを運ぶ', 'JWT に入れるときは宛先ごとに絞る'], bodySize: 12.5 });
    L.card(s, { x: 6.8, y: 3.9, w: 5.9, h: 1.85, icon: 'MdPerson', color: C.accent2, title: '別端末での承認：CIBA', titleSize: 14, body: ['結果は poll・ping・push で受け取る', '要求に binding_message を入れられる'], bodySize: 12.5 });
    L.note(s, 'tip', '追加認証を起動するのは受け手の判断。Entra は acrs と xms_cc で同じことをする。エージェントの承認は Part 10', { x: 0.6, y: 5.9, w: 12.1, h: 0.6, size: 12.5, label: '' });
  }

  {
    const s = L.content('下流ほど絞る：仕様は強制しない。組織で決める', {
      lead: 'RFC 8693 はトークン交換で範囲を狭めることを求めない。aud・scope・寿命の規則は自分で書く',
      stages: [2, 4],
      notes: '下流に渡すトークンほど、宛先、範囲、寿命を絞るのが原則です。RFC 9700 は、アクセストークンの宛先を特定のリソースサーバー、難しければ少数のリソースサーバーに限り、リソースと操作も限るべきだとしています。NIST IR 8587 も、トークンの範囲を意図した操作に必要な最小限に限ることを求めています。ところが、トークン交換の RFC 8693 は、範囲を狭めることを要求していません。scope と短い寿命の併用を推奨しているだけです。Transaction Tokens は、要求する scope を元のトークンと同じかそれ以下に限り、判別できなければ拒否するとしていますが、寿命については、元のトークンより長くてもよいとしています。委任の連鎖を表す act のネストも、縮小を保証しません。書籍でも、受け取ったトークンを下流へそのまま渡して認証の文脈を伝える例が紹介されていますが、それでは絞る段がありません。だから「下流のトークンは、aud、scope、寿命のどれでも上流を超えない」という規則を組織で明文化し、トークン交換のサービスで検証する必要があります。表は、ホップごとに絞る例です。',
      refs: { spec: 'RFC 8693 §5／RFC 9700 §2.3／Txn Tokens 草案 11 §13.6・§13.14', inst: 'NIST IR 8587 §5.3.1.3／OWASP Identity Propagation CS（aud を広げない）', book: '『実践 Keycloak』6.5 節 p.105（そのまま伝搬する例）' },
    });
    L.T(s, '例：ホップごとに絞る', { x: 0.6, y: 1.95, w: 7.2, h: 0.35, fontSize: 13, bold: true, margin: 0, valign: 'middle' });
    L.table(s, [['', '入口', '注文サービスへ', '在庫サービスへ'],
      ['aud', 'api.example.com', 'orders', 'inventory'],
      ['scope', 'orders.read orders.write inventory.reserve', 'orders.write inventory.reserve', 'inventory.reserve'],
      ['寿命', '1 時間以内', '分単位', '分単位'],
      ['独自クレーム', 'tenant・plan・roles', 'tenant・roles', 'tenant だけ']],
    { x: 0.6, y: 2.35, w: 7.2, colW: [1.5, 2.3, 1.9, 1.5], fontSize: 11.5, rowH: 0.6 });
    L.note(s, 'leader', '「下流は aud・scope・寿命のどれでも上流を超えない」を規則に書き、トークン交換のサービスで検証する', { x: 0.6, y: 5.5, w: 7.2, h: 1.0, size: 13 });
    L.card(s, { x: 8.1, y: 1.95, w: 4.6, h: 2.25, icon: 'MdFactCheck', color: C.accent4, title: '縮小を求める規範', titleSize: 14, body: ['Txn-Token：scope は同じかそれ以下', 'OAuth 2.1：RT は同意した範囲に束縛', 'RFC 9700：aud は特定の RS に（SHOULD）', 'IR 8587：scope は最小限（MUST）'], bodySize: 11.5 });
    L.card(s, { x: 8.1, y: 4.35, w: 4.6, h: 2.15, icon: 'MdWarning', color: C.accent3, title: '仕様が求めないもの', titleSize: 14, body: ['RFC 8693 の交換での縮小', '寿命（Txn-Token は元より長くてよい）', 'act のネストによる縮小の保証'], bodySize: 11.5 });
  }

  {
    const s = L.content('検証の分担：入口で検証しても、各サービスでも検証する', {
      lead: '入口は壊れうるし、入口を通らない経路もある。内部の API にも受け手としての検証を置く',
      stages: [3, 4],
      notes: 'ゲートウェイでトークンを検証しているから、内部のサービスは検証しなくてよい、という設計は危険です。『セキュアAPI』は 3 つの理由を挙げています。ゲートウェイも壊れうること、独自クレームを含むトークンはゲートウェイで検証しきれないことがあること、すべての API がゲートウェイを通るとは限らないことです。同書は「内部 API というものは存在しない」という節で、内部だから認証しなくてよいという考えを退けています。NIST SP 800-207 のゼロトラストも、あるリソースへのアクセスが、別のリソースへのアクセスを自動的に許すことはないとしています。分担の目安は表のとおりです。入口では署名、発行者、期限、入口宛てかを確かめ、各サービスでは、共通の検証部品で自分宛てかを確かめ、mTLS の相手と req_wl を照合し、独自クレームの意味を操作に当てはめます。オブジェクト単位の認可は、データを取るときに照合するしかありません。また、SP 800-228 は、呼び出し元のサービスと利用者を、それぞれ認可するよう求めています。',
      refs: { spec: 'RFC 9068 §4（受け手の検証）', inst: 'NIST SP 800-228 REC-API-12／SP 800-207 §2.1 原則 3／OWASP ASVS 8.3.3', book: '『セキュアAPI』8.5 節 NOTE p.250・3.4 節 pp.082–084' },
    });
    L.table(s, [['確かめること', '入口（ゲートウェイ）', '各サービス'],
      ['署名・iss・exp', 'まとめて確かめる', '共通の検証部品で再確認'],
      ['aud', '入口宛てか', '自分宛てか（内部トークン・Txn-Token）'],
      ['相手のサービス', '—', 'mTLS の相手と req_wl'],
      ['独自クレーム', '形と有無', '意味と、その操作への当てはめ'],
      [{ text: 'オブジェクト単位', options: { bold: true } }, { text: 'できない', options: { color: HEX.accent3, bold: true } }, 'データを取るときに照合する']],
    { x: 0.6, y: 1.95, w: 7.4, colW: [2.0, 2.3, 3.1], fontSize: 12, rowH: 0.56 });
    L.note(s, 'tip', '内部の呼び出しでも、元の利用者の権限で判断する。仲介サービスの権限で判断しない（ASVS 8.3.3）', { x: 0.6, y: 5.55, w: 7.4, h: 0.95, size: 12.5, label: '' });
    L.card(s, { x: 8.3, y: 1.95, w: 4.4, h: 2.75, icon: 'MdMenuBook', color: C.accent2, title: '書籍の指摘（p.250）', titleSize: 14, body: ['ゲートウェイも壊れうる', '独自クレームは入口で検証しきれないことがある', 'すべての API が入口を通るとは限らない'], bodySize: 12 });
    L.note(s, 'leader', '呼び出し元のサービスと利用者を、それぞれ認可する（SP 800-228 REC-API-12）', { x: 8.3, y: 4.9, w: 4.4, h: 1.6, size: 12.5 });
  }

  {
    const s = L.content('アクセス元の文脈：トークンに入れると古くなる', {
      lead: 'IP・ネットワーク・端末は、認証した瞬間の値。認可には PEP がその要求から得た値を使う',
      stages: [2, 4],
      notes: 'アクセス元の IP、社内ネットワークからかどうか、端末、場所といった文脈を、トークンのクレームで判断に使うのは危険です。Entra の ipaddr は、認証した時点の IP です。アクセストークンの寿命は既定で 60 分から 90 分のランダムな値（平均 75 分）、CAE に対応したクライアントでは 20 時間から 28 時間で、その間にネットワークが変わっても値は変わりません。AWS の転送アクセスセッションでは、VPC エンドポイントに関する条件キーが、サービスをまたぐと引き継がれません。X-Forwarded-For のようなヘッダー由来の文脈は、クライアントが偽装できます。代わりに、ゲートウェイやサイドカーのような PEP が、実際の接続から要求ごとに文脈を取り、判断に使います。NIST SP 800-207 では、ポリシーエンジンが企業のポリシーと外部の情報をもとに許可を判断し、PEP がそれを実施します。サービス間に伝えるなら、Transaction Tokens の rctx のように、TTS が責任を持つ欄に書きます。トークンに入れるなら、認証時の値だと分かる名前にします。',
      refs: { spec: 'Entra のクレーム（ipaddr）／Txn Tokens 草案 11 §9.2（rctx）', inst: 'NIST SP 800-207 §3（PE・PEP）・§2.1 原則 4／IR 8587 §4.1.4', book: '『デジタルアイデンティティのすべて』（考え方）12.3 節 pp.194–195' },
    });
    L.card(s, { x: 0.6, y: 1.95, w: 5.6, h: 2.85, icon: 'MdHistory', color: C.accent3, title: 'トークンに入れた文脈', titleSize: 15, body: ['Entra の ipaddr は認証した時点の IP', '寿命は既定 60〜90 分、CAE では 20〜28 時間', 'AWS FAS では VPC 系の条件が消える', 'X-Forwarded-For は偽装できる'], bodySize: 12.5 });
    L.arrow(s, 6.3, 3.37, 0.5, 'r', L.MUTED, 2);
    L.card(s, { x: 7.1, y: 1.95, w: 5.6, h: 2.85, icon: 'MdPolicy', color: C.accent1, title: 'PEP で要求ごとに評価する', titleSize: 15, body: ['ゲートウェイ・サイドカーが接続から取る', 'サービス間には Txn-Token の rctx で', 'PE が判断し、PEP が実施（SP 800-207）', 'トークンには「認証時の値」と分かる名前で'], bodySize: 12.5 });
    L.code(s, '// トークン：認証時の値と分かる名前で\n"https://claims.example.com/authn_ip": "198.51.100.20"\n// Txn-Token：TTS が書く要求時点の値\n"rctx": { "req_ip": "203.0.113.7" }', { x: 0.6, y: 5.0, w: 7.0, h: 1.45, fontSize: 11 });
    L.note(s, 'leader', '「今どこから来たか」の判断を、トークンのクレームに頼らない', { x: 7.85, y: 5.0, w: 4.85, h: 1.45, size: 13 });
  }

  {
    const s = L.content('ヘッダーへの転記：利用者が送った同名ヘッダーを消す', {
      lead: '検証済みのクレームをヘッダーに写すと、ヘッダーが信頼の対象になる。偽装の入口を塞ぐ',
      stages: [2, 3],
      notes: 'ゲートウェイやサービスメッシュは、検証したクレームを HTTP ヘッダーに写して、後ろのサービスに渡せます。サービスは JWT を読まずに済みますが、今度はヘッダーそのものが信頼の対象になります。クライアントが最初から同じ名前のヘッダーを送ってきたら、どうなるでしょうか。Istio の outputClaimToHeaders は同名のヘッダーを上書きし、Envoy の claim_to_headers は、検証を通らない経路も含めてリクエストから除去してから書き込みます。一方、Envoy の extract_only_without_validation は署名を検証しないので、誰でも作れるクレームが、検証済みのものと区別できない形でヘッダーになります。認可に使ってはいけません。実際の脆弱性も 3 件あります。CVE-2023-27487 は、Envoy がクライアントの送った内部ヘッダーを除去せず、JWT の確認を回避できた問題です。CVE-2025-64484 は、OAuth2-Proxy がアンダースコアの変種を除去せず、アプリ側がそれを正規の名前に読み替えた問題です。CVE-2026-26308 は、Envoy の RBAC が同名ヘッダーの複数の値を連結して照合し、拒否の規則を回避できた問題です。',
      refs: { spec: 'Istio RequestAuthentication／Envoy jwt_authn（claim_to_headers）', inst: 'NVD（3 件の CVE）／OWASP Authorization Patterns CS（コピーを除去）', book: '『セキュアAPI』1.4 節 pp.033–034（利用者が付けるヘッダー）' },
    });
    L.flow(s, [
      { t: 'クライアント', d: 'X-User-Role: admin を付けて送る', fill: C.accent3 },
      { t: '入口', d: '① 同名ヘッダーを除去 ② 検証 ③ 書き込み', fill: C.accent1 },
      { t: 'サービス', d: '入口が書いたヘッダーだけを読む', fill: C.accent4 }],
    { x: 0.6, y: 1.95, w: 7.6, h: 1.1, tSize: 14, dSize: 11.5 });
    L.table(s, [['事例', '何が起きたか', '教訓'],
      ['CVE-2023-27487（Envoy）', 'クライアントが送った内部ヘッダーを除去せず、JWT の確認を回避', '内部ヘッダーも除去する'],
      ['CVE-2025-64484（OAuth2-Proxy）', 'アンダースコアの変種を除去せず、アプリが「-」に読み替えて信頼', '大小文字と _・- を無視して除去'],
      ['CVE-2026-26308（Envoy RBAC）', '同名ヘッダーの複数の値を連結して照合し、拒否の規則を回避', '重複したヘッダーを拒否']],
    { x: 0.6, y: 3.25, w: 7.6, colW: [2.4, 3.4, 1.8], fontSize: 11, rowH: 0.75 });
    L.card(s, { x: 8.45, y: 1.95, w: 4.25, h: 2.95, icon: 'MdSwapHoriz', color: C.accent5, title: 'ゲートウェイの挙動', titleSize: 14, body: ['Istio：同名ヘッダーを上書き（試験的機能）', 'Envoy：全経路で除去してから書く', 'Envoy：配列等は JSON→base64', 'extract_only_without_validation は認可に使わない'], bodySize: 11.5 });
    L.note(s, 'warn', 'ヘッダーだけを見て JWT と署名を確かめないと、なりすましを許す（Cloudflare Access の注意）', { x: 8.45, y: 5.05, w: 4.25, h: 1.45, size: 12, label: '' });
  }

  {
    const s = L.content('証跡：誰が・どの経路で・何の承認で動いたか', {
      lead: '主体・実行者・経路・承認・取引を別のクレームで残す。ネストした act は監査用で、認可に使わない',
      stages: [2, 5],
      notes: '後から「誰の権限で、誰が、どこを経由して、何の承認に基づいて実行したか」を説明できるよう、それぞれを別のクレームで残します。誰の権限かは最上位の sub です。誰が実行したかは、RFC 8693 の act、Transaction Tokens の req_wl、mTLS の相手の ID で表します。act はネストでき、外側が現在の実行者、内側ほど過去の実行者になりますが、RFC 8693 は、アクセス制御に使ってよいのは最上位のクレームと現在の実行者だけで、過去の実行者は情報提供にすぎないと明記しています。何の承認かは、authorization_details や同意の ID で残します。英国の Open Banking は ID トークンで認可済みの intent_id を示し、ブラジルの Open Finance は同意 ID を動的なスコープで運びます。取引は txn で、TTS と各サービスがログに残せば、追跡とリプレイの検知に使えます。相関 ID は、署名されたトークンの中なら改ざんできず監査向き、W3C Trace Context の traceparent ヘッダーは改ざんできるので観測向きです。NIST IR 8587 は、トークンそのものと、中の個人情報をログに残さないよう求めています。',
      refs: { spec: 'RFC 8693 §4.1／Txn Tokens 草案 11 §13.2・§15.2／W3C Trace Context', inst: 'NIST IR 8587 §5.3.1.4・§5.3.1.7 表 6／OWASP Logging CS', book: '『デジタルアイデンティティのすべて』（考え方）11.6.7 節 pp.182–183' },
    });
    L.table(s, [['問い', 'クレーム・情報', '注意'],
      ['誰の権限で', 'sub（最上位）', 'ログではハッシュなどで隠す'],
      ['誰が実行したか', 'act（現在の実行者）・req_wl・mTLS の相手', '認可に使うのは最上位と現在の実行者だけ'],
      ['どこを経由したか', 'ネストした act（過去の実行者）', { text: '情報提供のみ。認可に使わない', options: { color: HEX.accent3, bold: true } }],
      ['何の承認で', 'authorization_details・同意 ID（intent_id など）', '承認の記録を指す ID を残す'],
      ['どの取引か', 'txn', 'TTS と各サービスが記録。リプレイ検知にも']],
    { x: 0.6, y: 1.95, w: 7.7, colW: [1.7, 3.1, 2.9], fontSize: 11.5, rowH: 0.56 });
    L.code(s, '{\n  "sub": "u-7f3a…",\n  "act": {\n    "sub": "spiffe://example.com/orders",\n    "act": {\n      "sub": "spiffe://example.com/gateway"\n    }\n  },\n  "txn": "97053963-…"\n}', { x: 8.55, y: 1.95, w: 4.15, h: 3.35, fontSize: 11 });
    L.box(s, [{ text: 'トークン内の ID（txn）', options: { bold: true, fontSize: 13, breakLine: true } }, { text: '署名で改ざんできない → 監査向き', options: { fontSize: 12 } }], { x: 0.6, y: 5.5, w: 5.9, h: 1.0, fill: C.accent1 });
    L.box(s, [{ text: 'ヘッダーの ID（traceparent）', options: { bold: true, fontSize: 13, breakLine: true } }, { text: '改ざんできる → 観測向き。tracestate に個人情報を入れない', options: { fontSize: 12 } }], { x: 6.8, y: 5.5, w: 5.9, h: 1.0, fill: C.accent5 });
  }

  {
    const s = L.content('結果を返す：JWT にするのは、自己完結した主張だけ', {
      lead: '否認防止が要る判断は署名つきで返す。業務データの本文は HTTP メッセージ署名で守る',
      stages: [1, 2],
      notes: '処理の結果を返したり、次の段へ渡したりするときにも、署名で完全性を守る方法があります。RFC 9701 は、イントロスペクションの応答を署名つきの JWT で返す仕様で、リソースサーバーは認可サーバーの判断を否認できない形で受け取れます。ただし、この JWT をアクセストークンとして使ってはいけません。JARM は認可応答を JWT にし、iss、aud、exp を必須とし、寿命は最大 10 分を推奨します。Webhook やサービス間の応答の本文を守るなら、RFC 9421 の HTTP Message Signatures が向いています。署名する部分として、メソッド、パス、本文のダイジェストなどを指定し、作成時刻や鍵の ID を必須にできます。JWT が向くのは、結果が自己完結した主張で、受け手が後で第三者に示す場合、受け手が複数いる場合、期限と宛先に意味がある場合です。大きな本文やストリーム、すぐに取り消したい結果、経路上の中継者に見せたくない機密には向きません。どの場合も、typ で種類を分け、種類ごとに検証の規則を分けて、取り違えを防ぎます。',
      refs: { spec: 'RFC 9701／RFC 9421／JARM／RFC 8725 §3.11・§3.12', inst: 'OWASP Authentication Patterns CS（HTTP Message Signatures）', book: '『セキュアAPI』10.6 節 pp.301–304（FAPI 2.0 メッセージ署名）' },
    });
    L.table(s, [['方式', '用途', '要点'],
      ['RFC 9701 署名つきイントロスペクション応答', 'AS の判断を否認できない形で受け取る', { text: 'アクセストークンとして使わない', options: { color: HEX.accent3, bold: true } }],
      ['JARM', '認可応答の完全性', 'iss・aud・exp 必須。最大 10 分を推奨'],
      ['RFC 9421 HTTP Message Signatures', 'Webhook・サービス間の応答', '@method・@path・Content-Digest、created・keyid を要求できる（必須はプロファイルで）'],
      ['承認つきトークン（RAR）', '人の承認の証跡', 'authorization_details を宛先ごとに'],
      ['SET（RFC 8417）・CAEP', '状態の変化の通知', 'Part 8 で扱う']],
    { x: 0.6, y: 1.95, w: 7.5, colW: [2.8, 2.2, 2.5], fontSize: 11, rowH: 0.62 });
    L.note(s, 'tip', 'typ で種類を分け、種類ごとに検証規則を分ける。結果の JWT をアクセストークンと取り違えさせない', { x: 0.6, y: 5.8, w: 7.5, h: 0.7, size: 12, label: '' });
    L.card(s, { x: 8.35, y: 1.95, w: 4.35, h: 2.15, icon: 'MdVerified', color: C.accent4, title: 'JWT が向く', titleSize: 14, body: ['自己完結した主張を第三者に示す', '受け手が複数、オフラインで検証', '期限と宛先に意味がある'], bodySize: 12 });
    L.card(s, { x: 8.35, y: 4.3, w: 4.35, h: 2.2, icon: 'MdBlock', color: C.accent3, title: 'JWT が向かない', titleSize: 14, body: ['大きな本文・ストリーム → RFC 9421', 'すぐ取り消したい → 参照型', '中継者に見せたくない機密'], bodySize: 12 });
  }

  {
    const s = L.content('流れの例 1：ブラウザから DB まで', {
      lead: 'ブラウザにトークンを置かず、入口で内部の形に替え、DB には利用者のトークンを渡さない',
      stages: [1, 2, 3],
      notes: '社内向けの Web アプリで、ブラウザから DB までの各ホップを追います。ブラウザはセッションの Cookie だけを持ち、トークンは BFF、つまりブラウザ専用のバックエンドが持ちます。BFF は認可コードフローで IdP からアクセストークン、リフレッシュトークン、ID トークンを受け取ります。このとき IdP は認証の事実である acr や amr を入れ、発行時フックがテナントやプランのような安定した属性を足します。BFF は ID トークンを API に送りません。アクセストークンの宛先は、RFC 8707 の resource で API に限ります。ゲートウェイは aud、exp、scope を確かめ、利用者が送ってきた X-User- で始まるヘッダーを除去し、TTS から Txn-Token を取ります。Txn-Token には txn、最も狭い scope、テナントを入れた tctx、接続から得た IP を入れた rctx、req_wl が入り、外部のアクセストークンは入りません。サービス間は mTLS と Txn-Token で、相手の ID と req_wl、scope を確かめ、Txn-Token は改変せずに転送します。DB にはサービスの資格情報で接続し、行の絞り込みに tctx のテナントを使います。高リスクの操作では、サービスが追加認証を求め、BFF が取り直します。',
      refs: { spec: 'RFC 8707（resource）／RFC 9470／Txn Tokens 草案 11', inst: 'OWASP ASVS 10.1.1（トークンは必要な所だけ）／NIST SP 800-228 §2.7', book: '『OpenID Connect入門』10 章 pp.143–167（BFF）' },
    });
    const hops = [
      ['ブラウザ', C.accent5, ['セッションの Cookie だけ', 'トークンを置かない']],
      ['BFF', C.accent5, ['IdP から AT・RT・ID トークン', '+ acr・amr（認証時）', '+ tenant・plan（フック）', 'ID トークンは API に送らない']],
      ['ゲートウェイ', C.accent1, ['✓ aud・exp・scope', '− 利用者が送った X-User-*', '+ 正規化した sub', 'TTS から Txn-Token']],
      ['サービス A・B', C.accent1, ['mTLS ＋ Txn-Token', '✓ 相手の ID と req_wl', '✓ scope が操作に合うか', '改変せずに転送']],
      ['DB', C.accent4, ['サービスの資格情報で接続', '利用者の AT は渡さない', '行の絞り込みに tctx.tenant', '詳細は Part 7']]];
    const bw = 2.18, gap = 0.3;
    hops.forEach((h, i) => {
      const x = 0.6 + i * (bw + gap);
      L.box(s, h[0], { x, y: 1.95, w: bw, h: 0.6, fill: h[1], fontSize: 14 });
      if (i < hops.length - 1) L.arrow(s, x + bw + 0.03, 2.25, gap - 0.06, 'r', L.MUTED, 1.5);
      s.addShape(SH.ROUNDED_RECTANGLE, { x, y: 2.7, w: bw, h: 2.75, rectRadius: 0.08, fill: { color: C.background2 }, line: { color: C.background2 } });
      L.T(s, L.runs(h[2], { space: 6 }), { x: x + 0.1, y: 2.8, w: bw - 0.2, h: 2.55, fontSize: 11.5, margin: 0 });
    });
    L.T(s, [{ text: '凡例　', options: { bold: true } }, { text: '+ 追加　− 除去　✓ 検証', options: {} }], { x: 0.6, y: 5.5, w: 6, h: 0.3, fontSize: 11, color: L.MUTED, margin: 0, valign: 'middle' });
    L.note(s, 'tip', '高リスクの操作：サービスが insufficient_user_authentication を返し、BFF が追加認証して新しい AT を取る', { x: 0.6, y: 5.85, w: 12.1, h: 0.65, size: 12.5, label: '' });
  }

  {
    const s = L.content('流れの例 2：マルチテナント SaaS', {
      lead: 'テナントは入口で 1 回確かめて Txn-Token の tctx に固定し、以降は誰も書き換えない',
      stages: [2, 3, 4],
      notes: 'マルチテナントの SaaS で、テナントがどう流れるかを追います。ログインでは、テナント固有の発行者か、テナントのクレームが付いたアクセストークンが発行され、発行時フックがテナントとテナント内のロールを足します。入口のゲートウェイは、iss とテナントの対応、aud を確かめ、さらに URL やヘッダーに書かれたテナント ID がトークンのテナントと一致するかを確かめ、一致しなければ拒否します。そのうえで、Txn-Token の tctx にテナントを入れます。Transaction Tokens は、作り直すときに sub、aud、txn を変えることを禁じ、tctx の値は TTS が責任を持つので、以降のサービスはテナントを書き換えられません。運用者が顧客のテナントを横断して作業するときは、トークン交換で、sub を顧客、act の sub を運用者とする委任のトークンを得て使います。緊急時の承認と期限を確かめ、監査には顧客の sub と運用者の act の両方を残します。識別子は、Entra なら社内の照合には oid と tid、外部にはアプリごとに違う sub を出します。テナントの表し方そのものは Part 5 で扱いました。',
      refs: { spec: 'Txn Tokens 草案 11 §9.2・§13.15／RFC 8693 §4.1・§4.4', inst: 'NIST IR 8587 §5.2.1.2（テナント単位の鍵）／OWASP ASVS 8.4.1', book: '『実践 Keycloak』4.3 節 p.46（iss はレルムごと）' },
    });
    L.table(s, [['ホップ', '持つトークン', 'クレームの操作'],
      ['ログイン', 'テナント固有の発行者、または tenant 付きの AT', '+ tenant、テナント内のロール（発行時フック）'],
      ['入口', '同上', '✓ iss とテナントの対応・aud。✓ URL やヘッダーのテナント ID と一致するか。不一致なら拒否'],
      ['入口 → TTS', 'Txn-Token', '+ tctx.tenant（以降は変わらない）'],
      ['サービス間', 'Txn-Token', '作り直しても sub・aud・txn は変えられない。tctx は TTS が決める'],
      ['運用者の横断作業', 'トークン交換で得た委任の AT（may_act）', '+ act.sub＝運用者。✓ 緊急時の承認と期限。監査に顧客と運用者の両方'],
      ['外部への識別子', 'Entra なら oid＋tid と sub', '社内の照合は不変の ID、外部にはアプリごとの値']],
    { x: 0.6, y: 1.95, w: 12.1, colW: [2.2, 3.7, 6.2], fontSize: 12, rowH: 0.55 });
    L.note(s, 'leader', 'テナントを書ける者を、発行時フックと TTS の 2 つに限る。以降のホップは読むだけ', { x: 0.6, y: 5.95, w: 12.1, h: 0.6, size: 13, label: '' });
  }

  {
    const s = L.content('流れの例 3・4：取引先との API と、イベント駆動', {
      lead: 'ドメインをまたぐときは相手の AS で作り直す。キューにはトークンでなく主体の参照を入れる',
      stages: [2, 3],
      notes: '2 つの流れを並べます。左は取引先との API、つまり信頼ドメインをまたぐ場合です。自社のサービスは、自社の認可サーバーでトークン交換をして、相手の認可サーバー宛ての JWT の認可グラントを得ます。このとき自社の認可サーバーは、主体 ID の写像、最小化、範囲の絞り込みをし、aud を相手の認可サーバー 1 つに限ります。相手の認可サーバーは aud が自分かを確かめ、自分のドメイン向けにクレームを作り直して、短命のアクセストークンを発行します。相手の API への呼び出しは、mTLS か DPoP で送信者に束縛します。応答や Webhook は RFC 9421 で署名します。右はイベント駆動です。トピックに発行するときは発行者のワークロード ID を使い、イベントのメタデータには、利用者の間接参照と txn だけを入れ、アクセストークンは入れません。Pub/Sub の push 配送では、ブローカーがサービスアカウントの OIDC トークンを付け、受け手は aud に加えて期待するサービスアカウントかを確かめます。コンシューマーは自分の ID で Txn-Token を取り、TTS が利用者と承認がまだ有効かを判断します。夜間バッチと AI エージェントの流れは、Part 8 と Part 10 で扱います。',
      refs: { spec: 'Identity Chaining 草案 17 §2.3・§2.5／RFC 7523／RFC 9421／CloudEvents Auth Context', inst: 'FAPI 2.0 §5.3.2.1（送信者制約）／SSF 1.0 §4.1.9' },
    });
    L.T(s, '取引先との API（ドメインをまたぐ）', { x: 0.6, y: 1.95, w: 5.9, h: 0.35, fontSize: 13, bold: true, color: C.accent1, margin: 0, valign: 'middle' });
    L.table(s, [['ホップ', 'クレームの操作'],
      ['自社の AS', 'トークン交換。主体 ID の写像・最小化・絞り込み。aud は相手の AS 1 つ'],
      ['相手の AS', '✓ aud＝自分（RFC 7523 のグラント）。相手の形に作り直し、短命の AT'],
      ['相手の API', 'mTLS か DPoP で送信者に束縛。✓ cnf'],
      ['応答・Webhook', 'RFC 9421 で署名（Content-Digest・created・keyid）']],
    { x: 0.6, y: 2.35, w: 5.9, colW: [1.5, 4.4], fontSize: 11.5, rowH: 0.7 });
    L.T(s, 'イベント駆動（Pub/Sub・Kafka・ワークフロー）', { x: 6.8, y: 1.95, w: 5.9, h: 0.35, fontSize: 13, bold: true, color: C.accent1, margin: 0, valign: 'middle' });
    L.table(s, [['ホップ', 'クレームの操作'],
      ['トピックへ発行', '発行者のワークロード ID。メタデータに利用者の間接参照と txn。AT は入れない'],
      ['配送（push）', 'サービスアカウントの OIDC トークン。✓ aud・期待するアカウントか'],
      ['コンシューマー', '自分の ID で Txn-Token を取得。TTS が利用者と承認の有効性を判断'],
      ['失効', 'SSF・CAEP の SET。txn で同じ原因のものを相関']],
    { x: 6.8, y: 2.35, w: 5.9, colW: [1.5, 4.4], fontSize: 11.5, rowH: 0.7 });
    L.note(s, 'tip', '夜間バッチ・長時間ジョブは Part 8、AI エージェントの流れは Part 10 で扱う', { x: 0.6, y: 6.0, w: 12.1, h: 0.55, size: 12.5, label: '' });
  }

  {
    const s = L.content('流れの規則：レビューで確かめる 10 項目', {
      lead: '足す・絞る・渡す・残すの規則。どれも仕様だけでは担保されず、組織で決めて検証する',
      stages: [1, 2, 3],
      notes: 'Part 6 のまとめとして、サービスの流れをレビューするときに確かめる 10 項目を挙げます。調査では、出典つきの設計規則を 27 項目に整理しましたが、ここでは足す、絞る、渡す、残すに関わるものを抜き出しています。1 と 2 は発行時の規則で、段階ごとに書き手を決め、フックには安定した属性だけを入れ、フックの失敗でクレームが欠けたら受け手が拒否することです。3 から 6 は渡し方の規則です。外部のトークンは入口で終わらせて内部の形に替え、受け取ったトークンを別の宛先へそのまま渡さず、下流は aud、scope、寿命で上流を超えないようにし、Txn-Token は専用のヘッダーで送ります。7 から 9 は受け手の規則で、入口でも各サービスでも検証し、利用者が送った ID 系のヘッダーは除去してから書き込み、アクセス元の文脈は PEP が要求ごとに評価します。10 は証跡で、sub、act、txn、承認の ID を分けて残し、トークンの全文はログに出しません。5 の縮小の規則は、仕様が強制しないので、とくに明文化が必要です。',
      refs: { spec: 'RFC 8693 §4.1・§5／Txn Tokens 草案 11 §12・§13', inst: 'NIST IR 8587 §5.3.1.3・§5.3.1.7／OWASP Identity Propagation CS', book: '『セキュアAPI』8.5 節 NOTE p.250' },
    });
    ruleGrid(s, [
      '段階ごとに書き手を決め、フックには安定した属性だけを入れる',
      'フックの失敗でクレームが欠けたら、受け手は拒否する',
      '外部のトークンは入口で終わらせ、内部専用の形に替える',
      '受け取ったトークンを、別の宛先へそのまま渡さない',
      '下流は aud・scope・寿命で上流を超えない（組織の規則）',
      'Txn-Token は専用ヘッダーで送り、アクセストークンにしない',
      '入口でも、各サービスでも検証する',
      '利用者が送った ID 系のヘッダーは、除去してから書き込む',
      'アクセス元の文脈は、PEP が要求ごとに評価する',
      'sub・act・txn・承認 ID を分けて残す。トークン全文は残さない']);
  }
};
