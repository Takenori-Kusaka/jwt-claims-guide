// Part 10: access policy for AI agents (who acts, on whose behalf, with what approval, against which resource)
module.exports = (L) => {
  const { C, SH, HEX } = L;
  L.section('Part 10 AI エージェント');
  L.divider('PART 10', 'AI エージェントのアクセスポリシー', 'エージェントは独立した主体。利用者の委任と分けて表し、ツールごとに狭く、タスクごとに短く渡す',
    ['エージェントの ID と、利用者の委任をどう分けるか', '誰が・どのエージェントが・何を承認し・どこに対して、をどのクレームで表すか', 'MCP では、受け取ったトークンをどう扱うか', '委任の連鎖の深さを、誰が制限するか'],
    'Part 10 は、AI エージェントのアクセスポリシーです。エージェントは、利用者の代わりにツールや API を呼びますが、その判断は言語モデルに依存するため、決定的ではありません。だからこそ、最小権限と、後から追跡できる記録が重要になります。この Part では、エージェント自身の ID と利用者からの委任を分けること、それを表すクレーム、ツールごとのスコープとタスクごとの短命トークン、人の承認の証拠、MCP の認可の規則、委任の連鎖と深さ、2026 年 11 月時点の各社の機能と指針の状況を見て、最後に設計のチェックリストにまとめます。');

  {
    const s = L.content('エージェントの ID：利用者のトークンを借りない', {
      lead: 'エージェントは独立した主体として登録する。代理で動くときは、利用者と別のクレームで表す',
      stages: [0, 1],
      notes: 'エージェントの ID の表し方には 3 つの型があります。1 つ目は、エージェントが自分の権限で自律的に動く場合で、エージェント自身が sub になります。2 つ目は、利用者の代わりに動く委任で、sub は利用者、act や client_id がエージェントです。3 つ目は、なりすましで、エージェントが利用者のトークンをそのまま使い、受け手からは利用者本人と区別できません。RFC 8693 はなりすましと委任を区別していて、エージェントは原則として委任を使います。CoSAI の Agentic IAM は、エージェントを独立した一級の ID として扱うこと、エージェント自身の権限と代理の権限を分けること、委任の連鎖を資格情報とログの両方で見えるようにすることを、いずれも MUST としています。ただし CoSAI は業界の枠組みで、標準ではありません。OpenID Foundation の白書も、なりすましをやめて代理に移り、委任した利用者とエージェントの 2 つの ID を持つトークンを使うよう述べています。右はその例です。',
      refs: { spec: 'RFC 8693（なりすましと委任）§4.1（act）', inst: 'CoSAI Agentic IAM v1.0 §1.2／OIDF「Agentic AI のためのアイデンティティ管理」§3.2', book: '『デジタルアイデンティティのすべて』（考え方）18.6.1 節 p.326' },
    });
    const ty = [['自律（エージェント自身の権限）', 'sub＝エージェント。client credentials など', C.accent5],
      ['委任（利用者の代理）', 'sub＝利用者、act・client_id＝エージェント', C.accent4],
      ['なりすまし（避ける）', '利用者のトークンをそのまま使う。区別できない', C.accent3]];
    ty.forEach((t, i) => L.box(s, [{ text: t[0], options: { bold: true, fontSize: 15, breakLine: true } }, { text: t[1], options: { fontSize: 12.5, bold: false } }], { x: 0.6, y: 1.95 + i * 1.18, w: 5.6, h: 1.02, fill: t[2], align: 'left', margin: 0.15 }));
    L.code(s, '// 委任：利用者 u-7f3a の代わりに経費アシスタントが動く\n{\n  "iss": "https://idp.example.com",\n  "sub": "u-7f3a…",\n  "client_id": "agent-console",\n  "act": { "sub": "agent:expense-assistant" },\n  "aud": "https://mcp.example.com/expenses",\n  "scope": "expenses:read",\n  "https://claims.example.com/tenant": "t-042"\n}', { x: 6.5, y: 1.95, w: 6.2, h: 3.38, fontSize: 11 });
    L.note(s, 'leader', 'エージェントを独立した ID として登録し、自身の権限と代理の権限を分ける。委任の連鎖は資格情報とログの両方で見せる（CoSAI は MUST。業界の枠組みで標準ではない）', { x: 0.6, y: 5.6, w: 12.1, h: 0.88, size: 13 });
  }

  {
    const s = L.content('4 つの問いとクレーム：誰が・何が・何を・どこに', {
      lead: '利用者・エージェント・承認の内容・宛先を、それぞれ既存のクレームで答える',
      stages: [0, 4],
      notes: 'エージェントのトークンが答えるべき問いは 4 つ、加えて誰が持つべきかの 1 つです。誰が利用者かは、iss と sub の組で表し、Entra ID では tid と oid です。どのエージェントやクライアントかは、client_id、azp、act の sub で表します。Transaction Tokens では req_wl が要求したワークロードです。何が承認されたかは、scope、authorization_details、認証の強さを表す acr、amr、auth_time です。どのリソース向けかは aud で、MCP では MCP サーバーの正規の URI を使います。誰が持つべきかは cnf で、DPoP や mTLS の鍵に束縛します。重要な注意として、ネストした act は過去の経路の情報で、RFC 8693 はアクセス制御の判断に使ってはならないとしています。判断に使うのは、最上位のクレームと、最も外側の act、つまり現在のアクターだけです。新しい独自クレームを作る前に、まずこの既存のクレームで足りないかを確かめます。',
      refs: { spec: 'RFC 8693 §4.1・§4.4／RFC 9068 §2.2／RFC 9396／RFC 8707／ID-JAG 草案 06', inst: 'OIDF Agentic AI §2.11（主体と act を記録）／CoSAI §3.4', book: '' },
    });
    L.table(s, [['問い', '主なクレーム', '注意'],
      ['誰が利用者か', 'iss＋sub（Entra は tid＋oid）', 'sub は発行者と組で扱う'],
      ['どのエージェント・クライアントか', 'client_id、azp、act.sub、req_wl', '現在のアクターは最も外側の act'],
      ['何が承認されたか', 'scope、authorization_details、acr・amr・auth_time', '承認内容は宛先ごとに絞って入れる'],
      ['どのリソース向けか', 'aud（MCP は正規の URI）、resource', 'aud は 1 つに絞る（本資料の推奨。63C-4 は FAL2 以上で必須）'],
      ['誰が持つべきか', 'cnf（DPoP・mTLS の鍵）', '盗まれたトークンの再利用を防ぐ']],
    { x: 0.6, y: 1.95, w: 12.1, colW: [3.2, 5.0, 3.9], fontSize: 12.5, rowH: 0.6 });
    L.note(s, 'warn', 'ネストした act は過去の経路の情報。アクセス制御の判断に使わない（RFC 8693 §4.1）', { x: 0.6, y: 5.8, w: 12.1, h: 0.68, size: 13, label: '' });
  }

  {
    const s = L.content('ツールごとのスコープ：狭く始め、タスクごとに短く', {
      lead: '最小のスコープで始め、必要なときだけ引き上げる。トークンはタスク単位で作り直す',
      stages: [1, 4],
      notes: 'エージェントに渡す権限の形です。MCP のセキュリティのベストプラクティスは、段階的なスコープの付与を勧めています。最初は基本的なツールだけの最小限のスコープで始め、特権の操作で不足したら、サーバーが WWW-Authenticate ヘッダーで必要なスコープを示し、クライアントが引き上げます。ワイルドカードや包括的なスコープは典型的な失敗として挙げられ、昇格のイベントは相関 ID つきでログに残すよう求めています。トークンはタスク単位で短く作ります。ID-JAG の草案は寿命を固定していませんが、例示は 300 秒で、リフレッシュトークンを返すべきでないとしています。Txn-Token は分以下で、リフレッシュトークンを返しません。Cognito のトークン交換もリフレッシュトークンを発行しません。NIST IR 8587 は、エージェントにも適用すべきとしたうえで、非人間の ID は狭いスコープの短命トークンを使わなければならないとしています。OWASP の Agentic Top 10 も、タスクごとの短命で狭いトークンを緩和策に挙げています。',
      refs: { spec: 'MCP Security Best Practices（スコープの最小化）／ID-JAG 草案 06 §4.3.4・§4.4.4', inst: 'NIST IR 8587 §1.1.1・§5.3.1.6／OWASP Agentic Top 10 2026 ASI03', book: '' },
    });
    L.flow(s, [{ t: '最小で始める', d: '基本のツールだけのスコープ', fill: C.accent4 },
      { t: '不足を返す', d: 'WWW-Authenticate で必要な scope を示す', fill: C.accent2 },
      { t: '段階的に引き上げ', d: '昇格は相関 ID つきで記録', fill: C.accent1 },
      { t: 'ホップごとに交換', d: 'aud は 1 つ、分単位、RT なし', fill: C.accent5 }], { x: 0.6, y: 1.95, w: 12.1, h: 1.3, tSize: 15, dSize: 12, gap: 0.36 });
    const st = [['300 秒', 'ID-JAG 草案の例示。RT を返すべきでない'], ['分以下', 'Txn-Token の寿命。RT は返さない'], ['RT なし', 'Cognito のトークン交換（2026-11）']];
    st.forEach((v, i) => L.stat(s, { x: 0.6 + i * 4.1, y: 3.35, w: 3.9, value: v[0], label: v[1], size: 34, vh: 0.75, lh: 0.55, color: C.accent1 }));
    L.note(s, 'leader', '非人間の ID は狭いスコープの短命トークンを使う（IR 8587 §5.3.1.6、MUST）。ワイルドカードのスコープは禁止する', { x: 0.6, y: 5.0, w: 12.1, h: 0.85, size: 13 });
    L.T(s, 'エージェントにも IR 8587 を適用すべき（§1.1.1）。OWASP ASI03 はタスクごとの短命・狭いトークンを緩和策に挙げる', { x: 0.6, y: 5.95, w: 12.1, h: 0.5, fontSize: 12.5, color: L.MUTED, valign: 'middle', margin: 0 });
  }

  {
    const s = L.content('人の承認の証拠：エージェントに判断させない', {
      lead: '承認したかどうかは、認可サーバーが本人に確かめる。承認の内容をトークンに載せて照合する',
      stages: [1, 4],
      notes: '送金や削除のような機微な操作では、人の承認が要ります。このとき、承認があったかどうかを、エージェント自身に判断させてはいけません。Auth0 も、承認の有無をエージェントではなく、ID を認識する認可のフローから得ることを強調しています。標準の手段は CIBA と RAR の組み合わせです。エージェントは CIBA で、金額や相手先などの承認してほしい内容を authorization_details に入れて要求します。利用者は自分の別の端末で承認し、認可サーバーが本人であることを確かめます。発行されたトークンには、承認された内容が、受け手ごとに必要な分だけに絞って入ります。これは RAR の推奨です。受け手のリソースサーバーは、実際の要求と承認された内容が一致するかを確かめます。承認の ID を独自クレームとして載せておくと、監査ログで利用者、エージェント、承認を結びつけられます。例の要素名は、対になるケーススタディの実験（cs/scen_c.py）に揃えました。ただし個別の請求書は、RFC 9396 §2.2 に従って identifier に入れています。locations はリソースサーバーの場所を表す要素です。ケーススタディの実験は請求書の ID を locations に入れ、承認 ID はトークンに載せていません。また実験では CIBA を使わず、交換のときにトークン発行サービスが承認の記録を引くことで、本人の承認を代用しました。',
      refs: { spec: 'OpenID CIBA Core／RFC 9396 §2.2（identifier・locations）・§9.1（宛先ごとに絞る）／ケーススタディ cs/scen_c.py', inst: 'OIDF Agentic AI §2.6（最小権限）／CoSAI §1.2', book: '' },
    });
    L.flow(s, [{ t: 'エージェントが要求', d: 'CIBA。内容を authorization_details に', fill: C.accent5 },
      { t: '利用者が承認', d: '別の端末で。AS が本人を確かめる', fill: C.accent2 },
      { t: 'トークン発行', d: '承認内容を宛先ごとに絞って載せる', fill: C.accent1 },
      { t: '受け手が照合', d: '要求と承認の内容が一致するか', fill: C.accent4 }], { x: 0.6, y: 1.95, w: 12.1, h: 1.3, tSize: 15, dSize: 12, gap: 0.36 });
    L.code(s, '"authorization_details": [{\n  "type": "https://claims.example.com/rar/payment",\n  "actions": ["pay"],\n  "identifier": "inv-1",\n  "instructedAmount": { "currency": "JPY", "amount": "120000" },\n  "creditorAccount": "B-019"\n}],\n"https://claims.example.com/approval_id": "ap-311"', { x: 0.6, y: 3.5, w: 6.9, h: 2.4, fontSize: 10.5 });
    L.card(s, { x: 7.8, y: 3.5, w: 4.9, h: 2.4, color: C.accent3, icon: 'MdHowToReg', title: '承認の扱いの規則', titleSize: 15, body: ['承認の有無をエージェントに任せない', '承認内容は宛先ごとに絞る', '受け手が要求と承認を照合する', '承認 ID を監査ログと相関させる'], bodySize: 12.5 });
    L.note(s, 'tip', '承認は「エージェントが言った」ではなく「認可サーバーが本人に確かめた」ものだけを信じる', { x: 0.6, y: 6.0, w: 12.1, h: 0.5, size: 12.5, label: '' });
  }

  {
    const s = L.content('MCP の認可：受け取ったトークンを渡さない', {
      lead: 'MCP サーバーは自分宛てのトークンだけを受け入れ、上流には別のトークンを使う',
      stages: [2, 3],
      notes: 'MCP の認可の仕様は、2026 年 11 月時点の現行版が 2026-07-28 です。MCP サーバーは OAuth のリソースサーバー、MCP クライアントは OAuth のクライアントです。クライアントは、認可要求とトークン要求の両方に、RFC 8707 の resource パラメータで MCP サーバーの正規の URI を入れなければなりません。サーバーは、自分を宛先として発行されたトークンだけを受け入れ、他のトークンを受け入れることも中継することもしてはなりません。上流の API を呼ぶときは、上流の認可サーバーが発行した別のトークンを使い、受け取ったトークンをそのまま渡すこと、つまりパススルーは禁止です。固定のクライアント ID を使うプロキシは、代理の混乱を防ぐため、動的に登録されたクライアントごとに利用者の同意を取ります。2026-07-28 版では、RFC 9207 の iss の検証と PKCE の S256 も必須です。拡張の Enterprise-Managed Authorization は 2026 年 6 月に Stable になり、IdP の ID-JAG を使って、組織が許可を管理できます。',
      refs: { spec: 'MCP Authorization 2026-07-28（Security Considerations）／RFC 8707／RFC 9207', inst: 'OWASP Agentic Top 10 2026 ASI03（ID と権限の悪用）', book: '' },
    });
    L.table(s, [['規則', '内容', '強さ'],
      ['宛先を指定する', '認可要求とトークン要求の両方に resource（MCP サーバーの正規 URI）', 'MUST'],
      ['宛先を検証する', '自分宛てに発行されたトークンだけを受け入れる', 'MUST'],
      ['パススルーの禁止', '受け取ったトークンを上流 API に渡さない。上流には別のトークン', { text: 'MUST NOT', options: { color: HEX.accent3, bold: true } }],
      ['代理の混乱を防ぐ', '固定のクライアント ID のプロキシは、クライアントごとに同意を取る', 'MUST'],
      ['発行者を確かめる', '認可応答の iss を検証する（RFC 9207）', 'MUST（あれば）'],
      ['PKCE', 'S256 を使う', 'MUST']],
    { x: 0.6, y: 1.95, w: 12.1, colW: [2.6, 7.4, 2.1], fontSize: 12.5, rowH: 0.5 });
    L.note(s, 'add', 'Enterprise-Managed Authorization 拡張（2026-06-18 Stable）：IdP の ID-JAG を MCP サーバーの AS でトークンに交換し、利用者ごとの同意画面なしに組織が許可を管理する', { x: 0.6, y: 5.6, w: 12.1, h: 0.88, size: 12.5, label: '' });
  }

  {
    const s = L.content('トークン交換は絞るとは限らない：Keycloak 26.8 の実測', {
      lead: '交換で得られる宛先と範囲はクライアントの設定で決まる。交換の方針はクライアントごとに絞る',
      stages: [1, 2, 4],
      notes: 'トークン交換を、範囲を狭める仕組みだと思い込まないでください。ケーススタディで、Keycloak 26.8 の標準トークン交換を実際に試しました。元のトークンは、利用者がポータルで得た mcp-tools 宛てのもので、aud は mcp-tools と account です。これを、ツールのクライアント mcp-tools が交換しました。audience に invoices、scope に aud-invoices を指定すると、invoices 宛てに絞ったトークンが出ました。audience だけを指定すると、Requested audience not available というエラーで、設定していない宛先を指定すると Audience not found で拒否されました。ここまでは期待どおりです。ところが、scope に aud-orders だけを指定すると、元のトークンには無かった orders 宛てのトークンが、200 で発行されました。宛先が mcp-tools から orders に付け替わり、範囲は元より広がっています。交換で得られる範囲を決めているのは、元のトークンではなく、交換するクライアントに割り当てたスコープだからです。ここで使った aud-orders は、mcp-tools に optional scope として割り当てたものです。この挙動は Keycloak の文書にも書かれていて、既定では交換で元に無いスコープと宛先を要求できます。audience パラメータは宛先を絞るだけで足さず、宛先を足すのは scope です。絞り込みだけを許すには、client policy の executor（downscope-assertion-grant-enforcer）をクライアントに適用します。何も指定しなければ、aud は account だけでした。また、出たトークンには act がありませんでした。交換の所要時間は 200 回で p50 9.7 ミリ秒、p95 31.3 ミリ秒です。したがって、交換を許すクライアントと、そのクライアントに割り当てる宛先とスコープを、クライアントごとに最小にし、交換のサービスか受け手で、下流が上流を超えていないかを確かめます。',
      refs: { spec: 'RFC 8693 §5（縮小を求めない）／Keycloak Token exchange・Server Admin Guide（downscope-assertion-grant-enforcer）／ケーススタディ results/summary.md（題材 C）', inst: 'NIST IR 8587 §5.3.1.3／OWASP Identity Propagation CS（aud を広げない）', book: '' },
    });
    L.T(s, '元のトークン：利用者がポータルで得た mcp-tools 宛て（aud＝mcp-tools・account）。クライアント mcp-tools が交換する', { x: 0.6, y: 1.9, w: 12.1, h: 0.35, fontSize: 12.5, color: L.MUTED, margin: 0, valign: 'middle' });
    const ok = (t) => ({ text: t, options: { color: HEX.accent4, bold: true } });
    const ng = (t) => ({ text: t, options: { color: HEX.accent3, bold: true } });
    L.table(s, [['交換の要求', '結果', '得た aud', '得た scope'],
      ['audience＝invoices、scope＝aud-invoices', ok('200（絞り込み）'), 'invoices', 'aud-invoices email profile'],
      ['audience＝invoices だけ', ng('400'), '—', 'Requested audience not available: invoices'],
      ['audience＝設定していない宛先', ng('400'), '—', 'Audience not found'],
      [{ text: 'scope＝aud-orders だけ（optional scope。元のトークンに無い宛先）', options: { bold: true, color: HEX.accent3 } }, ng('200（付け替え・拡大）'), { text: 'orders・account', options: { bold: true, color: HEX.accent3 } }, 'aud-orders email profile'],
      ['どちらも指定しない', ok('200'), 'account', 'email profile']],
    { x: 0.6, y: 2.3, w: 12.1, colW: [4.3, 2.3, 1.9, 3.6], fontSize: 12, rowH: 0.46, firstBold: false });
    L.stat(s, { x: 0.6, y: 5.25, w: 3.0, value: 'act なし', label: '標準の交換で出たトークン', size: 26, vh: 0.55, lh: 0.5, lsize: 12, color: C.accent5 });
    L.stat(s, { x: 3.6, y: 5.25, w: 3.0, value: '9.7 ms', label: 'p50（p95 31.3 ms、200 回）', size: 26, vh: 0.55, lh: 0.5, lsize: 12, color: C.accent1 });
    L.note(s, 'leader', '交換は絞るとは限らない。交換を許すクライアントと宛先・スコープを最小にし、downscope-assertion-grant-enforcer で絞り込みだけに限る。「下流は上流を超えない」を確かめる（Part 6）', { x: 6.8, y: 5.2, w: 5.9, h: 1.3, size: 12.5 });
  }

  {
    const s = L.content('委任の連鎖と深さ：上限は組織の規則で決める', {
      lead: 'act の入れ子は記録にすぎず、縮小も深さの上限も標準は保証しない',
      stages: [2, 4],
      notes: 'エージェントがツールを呼び、ツールがさらにバックエンドを呼ぶと、委任の連鎖ができます。RFC 8693 では、act を入れ子にして経路を記録できますが、内側の act は情報にすぎず、権限の縮小を構造的に保証しません。深さを制限する仕組みも標準にはありません。2026 年には縮小や深さを扱う提案が多く出ていますが、いずれも個人の草案で、標準ではありません。製品では、Auth0 の On-Behalf-Of トークン交換で、上限 4 を超えたというエラーの例が文書にあり、早期アクセスの Agent as Principal は最大 5 ホップ、入れ子の act は 4 段です。組織としては、深さの上限、各ホップで権限が前の部分集合であること、根元の承認からの一括失効を、自前の規則で決めます。『デジタルアイデンティティのすべて』も、委任された権限は本人の権限とは別に取り消せるべきだと述べています。CVE-2025-55241 は、署名のない内部の代理トークンが、テナントを検証されず、24 時間失効できず、ログも残らなかった事例で、逆の設計の教訓です。',
      refs: { spec: 'RFC 8693 §4.1（入れ子の act は情報のみ）／Auth0 On-Behalf-Of・Agent as Principal', inst: 'CoSAI §3.4（深さ・TTL・宛先で制御）／OIDF Agentic AI §3.2', book: '『デジタルアイデンティティのすべて』（考え方）18.6.1 節 p.326' },
    });
    L.flow(s, [{ t: '利用者', fill: C.accent2 }, { t: 'エージェント', fill: C.accent5 }, { t: 'ツール（MCP）', fill: C.accent1 }, { t: 'バックエンド', fill: C.accent4 }], { x: 0.6, y: 1.95, w: 12.1, h: 0.65, tSize: 14, gap: 0.5 });
    L.code(s, '{\n  "sub": "u-7f3a…",\n  "act": {\n    "sub": "tool:invoice-mcp",\n    "act": { "sub": "agent:expense-assistant" }\n  }\n}\n// 外側の act（ツール）が現在のアクター\n// 内側は記録用。判断に使わない', { x: 0.6, y: 2.8, w: 5.9, h: 2.6, fontSize: 11 });
    L.table(s, [['仕組み', '深さの扱い'],
      ['RFC 8693', '上限なし。入れ子は情報のみ'],
      ['Auth0 On-Behalf-Of', '上限 4 を超えるとエラー（例）'],
      ['Auth0 Agent as Principal（EA）', '最大 5 ホップ、入れ子 4 段'],
      ['2026 年の縮小・深さの提案', '個人草案のみ。標準ではない']],
    { x: 6.8, y: 2.8, w: 5.9, colW: [2.9, 3.0], fontSize: 12, rowH: 0.52 });
    L.note(s, 'warn', 'CVE-2025-55241：署名のない内部の代理トークンが、テナント未検証・24 時間失効不能・ログなしだった。委任トークンはこの逆に作る', { x: 0.6, y: 5.6, w: 12.1, h: 0.88, size: 12.5, label: '' });
  }

  {
    const s = L.content('各社の機能：2026 年 11 月時点の姿', {
      lead: '各社がエージェント用の ID と委任の仕組みを出している。名前と載るクレームは製品ごとに違う',
      stages: [1, 3],
      notes: '2026 年 11 月時点の、各社のエージェント向けの機能です。Entra ID の Agent ID は、agent identity blueprint という親の ID と子のエージェント ID を持ち、OBO の交換で、利用者、blueprint、エージェントの束縛を認可サーバーが確かめます。トークンには xms_act_fct、xms_sub_fct、xms_par_app_azp などの独自のクレームが載ります。提供段階がプレビューか一般提供かは、確認できていません。Auth0 は、RFC 8693 に基づく On-Behalf-Of のトークン交換と、早期アクセスの Agent as Principal を持ち、act に委任の連鎖が入ります。Okta は Cross App Access で ID-JAG を使い、MCP の Enterprise-Managed Authorization に最初に対応した IdP です。Cognito は 2026 年 11 月 12 日にトークン交換を出し、actor token があれば act を付けますが、may_act は扱いません。Keycloak は 26.8 で AI エージェント向けの委任を加えました。AWS の AgentCore Identity は、エージェントをワークロード ID として管理します。',
      refs: { spec: 'Entra Agent ID／Auth0 for AI Agents／Okta XAA／Cognito token exchange／Keycloak 26.8', inst: '', book: '' },
    });
    L.table(s, [['製品', '機能', 'トークンでの表れ'],
      ['Entra Agent ID', 'blueprint とエージェント ID。OBO で利用者との束縛を検証', 'xms_act_fct・xms_sub_fct・xms_par_app_azp'],
      ['Auth0', 'On-Behalf-Of トークン交換、Agent as Principal（早期アクセス）', 'act（外側が現在のアクター）、sub_profile'],
      ['Okta', 'Cross App Access（ID-JAG）。MCP の EMA に最初に対応', 'ID-JAG から範囲を絞った AT'],
      ['Cognito', 'トークン交換（2026-11-12）。RT なし、may_act は扱わない', 'actor token があれば act'],
      ['Keycloak', '26.8 で AI エージェント向けの委任（同意・監査）', 'may_act と act（プレビュー機能）'],
      ['AgentCore Identity', 'エージェントをワークロード ID として管理、Token Vault', '受信時に client_id・scope・独自クレームを照合']],
    { x: 0.6, y: 1.95, w: 12.1, colW: [2.2, 5.3, 4.6], fontSize: 12, rowH: 0.56 });
    L.note(s, 'leader', '製品の独自クレームを組織の契約にしない。入口で act・client_id など標準のクレームにそろえる（Part 11）', { x: 0.6, y: 5.95, w: 12.1, h: 0.58, size: 12, label: '' });
  }

  {
    const s = L.content('指針と標準化：公的な根拠として引けるものは少ない', {
      lead: '根拠は IR 8587・MCP・RFC。白書や草案は設計の参考に留める',
      stages: [5],
      notes: 'エージェントについての指針と標準化の状況です。最も明確な公的指針は、2026 年 9 月に Final になった NIST IR 8587 です。連邦機関向けの実装推奨で、民間には任意ですが、エージェントがトークンでシステムやツールにアクセスする場合にも適用すべきとしています。NIST NCCoE のコンセプトペーパーはまだドラフトで、委任やログを検討していますが、要求事項はまだありません。OWASP の Agentic Top 10 2026 は ASI03 で ID と権限の悪用を扱い、NHI Top 10 2025 はインキュベーターの段階で、NHI5 で過剰な権限を挙げています。OpenID Foundation の白書には OpenID ファウンデーション・ジャパンの日本語訳があります。CoSAI の Agentic IAM は v1.0 で、MUST を使った原則を示しています。CSA の文書は DID や VC を前提にした提案で、根拠としては弱めです。IETF では、ID-JAG が第 6 版の WG 文書、Transaction Tokens が第 11 版で WG の合意済み、identity-chaining が RFC Editor の処理待ちで、エージェントの代理を扱った個人草案は期限切れです。',
      refs: { spec: 'IETF datatracker（2026-11-17 確認）／MCP Authorization 2026-07-28', inst: 'NIST IR 8587 §1.1.1／NCCoE 概念文書／OWASP／OIDF・OIDF-J／CoSAI v1.0', book: '' },
    });
    L.table(s, [['文書', '状態', '要点'],
      ['NIST IR 8587', 'Final（2026-09）', 'エージェントにも適用（§1.1.1）'],
      ['NIST NCCoE 概念文書', 'ドラフト', '委任とログを検討。要求事項はまだない'],
      ['OWASP Agentic Top 10 2026', '公開', 'ASI03 ID と権限の悪用'],
      ['OWASP NHI Top 10 2025', 'インキュベーター', 'NHI5 過剰な権限'],
      ['OIDF 白書（OIDF-J 訳）', 'ホワイトペーパー', 'sub と act の 2 つの ID'],
      ['CoSAI Agentic IAM', 'v1.0', '自身と代理の権限を分ける（MUST）']],
    { x: 0.6, y: 1.95, w: 7.3, colW: [2.7, 1.9, 2.7], fontSize: 12, rowH: 0.55 });
    L.table(s, [['IETF 草案', '状態（2026-11-17）'],
      ['ID-JAG', '第 6 版、WG 文書'],
      ['Transaction Tokens', '第 11 版、WG の合意済み'],
      ['identity-chaining', 'RFC Editor の処理待ち'],
      ['AI エージェントの OBO', '個人草案、期限切れ'],
      ['縮小・深さの提案', '個人草案のみ']],
    { x: 8.2, y: 1.95, w: 4.5, colW: [2.0, 2.5], fontSize: 12, rowH: 0.55 });
    L.note(s, 'leader', '規則の根拠には IR 8587・MCP 仕様・RFC を使う。白書と草案は「方向性」として示し、必須とは書かない', { x: 0.6, y: 5.92, w: 12.1, h: 0.6, size: 12, label: '' });
  }

  {
    const s = L.content('設計チェックリスト：エージェントのアクセス', {
      lead: 'エージェントを組織のサービスにつなぐ前に、9 つを確かめる',
      stages: [0, 4, 5],
      notes: 'この Part のチェックリストです。まず、エージェントを独立した ID として登録し、共有のアカウントを使っていないかを確かめます。代理で動くときは、sub が利用者、act や client_id がエージェントと分かれているか。宛先は resource で要求し、aud を 1 つに絞っているか。受け取ったトークンをそのまま渡していないか。MCP の仕様が求めるのはこのパススルーの禁止までで、ホップごとに交換するかは組織の選択です。交換するなら、交換は範囲を広げることもあるので、交換を許すクライアントと、割り当てる宛先とスコープを絞っているか。Keycloak 26.8 では、optional scope を求めると元のトークンに無い宛先のトークンが出ました。スコープはツールごとの最小限で、昇格を記録しているか。トークンはタスク単位の短命で、リフレッシュトークンを出していないか。短命で狭いトークンは IR 8587 が、リフレッシュトークンを出さないことは ID-JAG と Transaction Tokens の草案が求めています。機微な操作では、CIBA と RAR による承認を受け手が照合しているか。委任の深さの上限と、根元の承認からの一括失効を決めているか。そして監査で、利用者、すべてのアクター、txn、承認 ID を相関できるか、です。深さの上限と一括失効は標準にまだないので、組織の規則として Part 11 の台帳に書きます。',
      refs: { spec: 'RFC 8693／8707／9396／MCP 認可／ID-JAG 06 §4.4.4／Txn-Token 11 §11.4', inst: 'CoSAI §1.2・§4.4／NIST IR 8587 §5.3.1.6（短命・狭い範囲）', book: '『デジタルアイデンティティのすべて』（考え方）18.6.1 節 p.326' },
    });
    L.table(s, [['観点', '確かめること', '根拠'],
      ['主体', 'エージェントを独立した ID として登録したか', 'CoSAI §1.2'],
      ['委任', 'sub＝利用者、act・client_id＝エージェントで分けたか', 'RFC 8693 §4.1'],
      ['宛先', 'resource で要求し、aud を 1 つに絞ったか', 'RFC 8707、MCP'],
      ['転送', '受け取ったトークンを渡さないか。ホップごとの交換と、交換の宛先・範囲の絞り込みは組織で決めたか', 'MCP 仕様（パススルー禁止）／組織の規則'],
      ['範囲', 'ツールごとの最小スコープで、昇格を記録するか', 'MCP ベストプラクティス'],
      ['寿命', 'タスク単位の短命トークンで、RT を出さないか', 'IR 8587 §5.3.1.6／ID-JAG §4.4.4'],
      ['承認', '機微な操作は CIBA・RAR の承認を照合するか', 'RFC 9396'],
      ['連鎖', '深さの上限と、根元からの一括失効を決めたか', '組織の規則'],
      ['監査', 'sub・全アクター・txn・承認 ID を相関できるか', 'CoSAI §4.4']],
    { x: 0.6, y: 1.95, w: 12.1, colW: [1.4, 7.2, 3.5], fontSize: 12.5, rowH: 0.45 });
  }
};
