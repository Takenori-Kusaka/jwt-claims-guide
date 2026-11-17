// Title and Part 0 (introduction): claims are contracts between services
module.exports = (L) => {
  const { pres, C, SH, HEX } = L;

  L.section('はじめに');
  {
    const s = pres.addSlide({ masterName: 'TITLE', sectionTitle: 'はじめに' });
    L.T(s, 'JWT CLAIM DESIGN GUIDE', { x: 0.8, y: 1.2, w: 11, h: 0.5, fontSize: 18, bold: true, color: C.accent2, charSpacing: 6, margin: 0 });
    L.T(s, 'JWT クレーム設計ガイド', { x: 0.8, y: 1.8, w: 12.0, h: 1.0, fontSize: 40, bold: true, color: C.background1, margin: 0 });
    L.T(s, '組織のあらゆるサービスで共用する独自クレームを、どう設計し、どう流し、どう治めるか', { x: 0.8, y: 2.85, w: 11.8, h: 0.6, fontSize: 21, color: C.background2, margin: 0 });
    // header.payload.signature motif
    const seg = [['HEADER', 'alg・kid・typ', C.accent3], ['PAYLOAD', 'iss・sub・aud・exp … と独自クレーム', C.accent2], ['SIGNATURE', '発行者の鍵による署名', C.accent1]];
    let x = 0.8;
    seg.forEach(([t, d, col], i) => {
      const w = i === 1 ? 5.4 : 2.9;
      s.addText([{ text: t, options: { bold: true, fontSize: 13, color: C.background1, breakLine: true, charSpacing: 3 } }, { text: d, options: { fontSize: 12, color: C.background1 } }],
        { shape: SH.ROUNDED_RECTANGLE, rectRadius: 0.08, x, y: 3.95, w, h: 0.9, fill: { color: col }, line: { color: col }, align: 'center', valign: 'middle', margin: 0.05 });
      if (i < 2) L.T(s, '.', { x: x + w + 0.02, y: 4.05, w: 0.2, h: 0.6, fontSize: 30, bold: true, color: C.background1, margin: 0, align: 'center' });
      x += w + 0.25;
    });
    L.T(s, '対象：認証認可とマイクロサービスの設計を任された、新任のテックリーダー', { x: 0.8, y: 5.35, w: 11.8, h: 0.4, fontSize: 15, color: C.background2, margin: 0 });
    L.T(s, '根拠：IETF・OpenID の仕様／NIST・OWASP・デジタル庁などの指針／日本語の専門書 4 冊（調査基準日 2026-11-17）', { x: 0.8, y: 5.8, w: 11.8, h: 0.4, fontSize: 13, color: 'A9BCC2', margin: 0 });
    s.addNotes('本資料は、認証認可とマイクロサービスの設計を任された新任のテックリーダーに向けて、JWT に載せる独自クレームの設計を解説します。主題は、OpenID Connect や OAuth の標準クレームそのものではなく、組織のあらゆるサービスで共用する独自のクレームを、どう設計し、どう流し、どう治めるかです。ただし、標準のクレームと、各社の IdP が既に出しているクレームを知らないと、同じ意味のクレームを独自に作ったり、名前を衝突させたりします。そのため前半で、既にあるクレームの地図と、4 つの IdP の実際を厚めに扱います。内容は、IETF と OpenID Foundation の仕様、NIST・OWASP・デジタル庁などの公的な指針、日本語の専門書 4 冊を根拠にしています。調査の基準日は 2026 年 11 月 17 日です。');
  }

  {
    const s = L.content('この資料のゴールと読み方', {
      lead: '「トークンに何を入れるか」を、事故・仕様・運用の根拠つきで説明し、組織の規則として決められる状態を目指す',
      notes: 'ゴールは、トークンに載せる属性を、自分の言葉と根拠で説明できることです。どのクレームを使い、どれを独自に足し、どれを載せずに都度問い合わせるか。その判断を、事故の例、仕様、運用の制約から説明できるようにします。各スライドの右上の 6 つの表示は、その話題がクレームの一生のどこに関わるかを示します。定義はクレームの名前・型・意味を決めること、発行はトークンに入れること、伝搬はサービス間で渡すこと、検証は受け取った側が確かめること、認可はクレームを使って判断すること、運用は変更・失効・監査です。各スライドの下の行は根拠で、仕様、公的な指針、日本語の書籍の 3 種類を色で分けています。本文は要点だけを書き、詳しい説明はノート欄に書いています。',
    });
    const cw = 3.83, y = 1.95, h = 2.6;
    L.card(s, { x: 0.6, y, w: cw, h, icon: 'MdSchool', title: '理解のゴール', body: ['標準と各社 IdP のクレームの意味と範囲を説明できる', '独自クレームの名前・型・意味の決め方を説明できる', 'クレームが事故になる経路を説明できる'], bodySize: 13 });
    L.card(s, { x: 4.73, y, w: cw, h, icon: 'MdFlag', color: C.accent2, title: 'リーダーとしてのゴール', body: ['クレームの台帳と変更の手順を作れる', '発行・伝搬・検証の責任分担を決められる', '新しいクレームの提案を審査できる'], bodySize: 13 });
    L.card(s, { x: 8.87, y, w: cw, h, icon: 'MdMenuBook', color: C.accent5, title: 'この資料の使い方', body: ['本文は要点、ノート欄は詳しい解説', '前半は地図、後半は設計と運用', '最後に審査の質問とチェックリスト'], bodySize: 13 });
    L.T(s, '凡例', { x: 0.6, y: 4.8, w: 1.0, h: 0.35, fontSize: 14, bold: true, margin: 0 });
    s.addText('伝搬', { shape: SH.ROUNDED_RECTANGLE, rectRadius: 0.14, x: 0.6, y: 5.25, w: 0.98, h: 0.28, fill: { color: C.accent1 }, line: { color: C.accent1 }, fontSize: 10, bold: true, color: C.background1, align: 'center', valign: 'middle', margin: 0 });
    L.T(s, '右上の表示：クレームの一生（定義・発行・伝搬・検証・認可・運用）のどこの話か', { x: 1.7, y: 5.17, w: 5.2, h: 0.45, fontSize: 13, margin: 0, valign: 'middle' });
    const legend = [['仕様', C.accent1, 'RFC・OpenID の仕様'], ['指針', C.accent4, 'NIST・OWASP・デジタル庁など'], ['書籍', C.accent2, '日本語の専門書（章・ページ）']];
    legend.forEach(([t, col, d], i) => {
      L.T(s, [{ text: t + '  ', options: { bold: true, color: col } }, { text: d, options: { color: C.text1 } }], { x: 7.0, y: 4.85 + i * 0.42, w: 5.7, h: 0.38, fontSize: 13, margin: 0, valign: 'middle' });
    });
    L.icon(s, 'MdFlag', 0.6, 5.85, 0.42, C.accent2);
    L.T(s, 'リーダーの視点：判断・説明の観点', { x: 1.15, y: 5.85, w: 5, h: 0.42, fontSize: 13, margin: 0, valign: 'middle' });
    L.T(s, 'スライド下の行：そのスライドの根拠（3 種類）', { x: 7.0, y: 6.15, w: 5.7, h: 0.38, fontSize: 12, color: L.MUTED, margin: 0, valign: 'middle' });
  }

  {
    const s = L.content('この資料の主張：クレームは、サービス間の「契約」である', {
      lead: '1 つのクレームを、発行者と多数の受け手が同じ意味で読む。決めずに足すと、読み違いが事故になる',
      stages: [0, 5],
      notes: 'この資料の中心の主張です。JWT のクレームは、発行者が「この主体について、これが正しい」と述べた言明です。受け手は、トークンを持ってきた相手ではなく、発行者を信頼して、その言明を受け入れます。組織で共用する独自クレームは、1 人の発行者が書き、多数のサービスが読みます。つまり、サービス間の契約です。契約である以上、6 つのことを決めておく必要があります。誰が書くのか、名前は何か、型は何か、何を意味し何を意味しないのか、いつまで正しいのか、誰が持ち主で、誰が読んでよいのか。どれかを決めずにクレームを足すと、受け手ごとに解釈がずれ、そのずれが権限の取り違えや情報の漏えいになります。トークンの中身を変えることは、API を変えることと同じ重さで扱うべきだ、という指摘もあります。',
      refs: { spec: 'RFC 7519 §4（クレームの定義）', inst: 'NIST SP 800-162 §2.4.2（属性の名前・定義・値の正規化）／IR 8587 §5.2.1.1（必須要素の文書化）', book: '『デジタルアイデンティティのすべて』（考え方）2.1・15.1 節（クレームは発行者の言明）' },
    });
    const items = [['MdVerifiedUser', '誰が書くか', '発行者（iss）。書き込める主体を 1 つに決める'], ['MdLabel', '名前', '衝突しない名前と名前空間'], ['MdDataObject', '型', '文字列か配列か。無いときの意味'],
      ['MdTranslate', '意味', '何を表し、何を表さないか'], ['MdTimer', '寿命', 'いつまで正しいか。変わったらどうなるか'], ['MdGroups', '持ち主と受け手', '誰が変更を決め、誰が読んでよいか']];
    items.forEach((it, i) => {
      const col = i % 3, row = Math.floor(i / 3);
      L.card(s, { x: 0.6 + col * 4.13, y: 1.95 + row * 1.72, w: 3.85, h: 1.55, icon: it[0], color: [C.accent1, C.accent5, C.accent2][col], title: it[1], titleSize: 15, body: [it[2]], bodySize: 12.5 });
    });
    L.note(s, 'leader', 'クレームの追加・変更は、API の変更と同じ重さで扱う。台帳に載っていないクレームは、どのサービスも頼らない', { x: 0.6, y: 5.5, w: 12.1, h: 0.95, size: 13.5 });
  }

  {
    const s = L.content('なぜ難しいか：1 つの発行者、多数の受け手、それぞれの解釈', {
      lead: '発行者は 1 つでも、受け手は API・ゲートウェイ・DB・エージェントと増え、ライブラリも言語も違う',
      stages: [2, 3],
      notes: '独自クレームが難しいのは、書き手と読み手の数が釣り合わないからです。IdP や内部のトークン発行サービスは 1 つでも、受け手は API サーバー、API ゲートウェイ、サービスメッシュ、データベースの行単位の制御、バッチ、AI エージェントのツールと増えていきます。受け手ごとに言語もライブラリも違います。たとえば、配列のクレームを、ある受け手は配列として、別の受け手は空白区切りの文字列として読むかもしれません。ゲートウェイがクレームを HTTP ヘッダーに移すと、ヘッダーの扱いの違いも加わります。どれか 1 つの受け手が誤って読むだけで、その受け手の先にあるデータが危険にさらされます。だから、クレームの意味と型は、受け手に任せず、発行側で契約として決めておく必要があります。',
      refs: { spec: 'RFC 7519 §4（理解できないクレームは無視）／RFC 8725 §3（受け手の検証）', inst: 'NIST SP 800-162 §3.2.1.3（定義と意味の文書化）／OWASP JWT Cheat Sheet', book: '『セキュアAPI』8.3 節 pp.236–239' },
    });
    L.box(s, [{ text: '発行者', options: { bold: true, fontSize: 16, breakLine: true } }, { text: 'IdP／内部のトークン発行サービス', options: { fontSize: 12 } }], { x: 0.6, y: 3.0, w: 2.6, h: 1.3, fill: C.accent1 });
    const rcv = [['API サーバー', 'Java・Go・Node…'], ['ゲートウェイ', 'クレーム→ヘッダー'], ['サービスメッシュ', '照合式（CEL など）'], ['データベース', '行単位の制御'], ['バッチ・キュー', '利用者がいない時間'], ['AI エージェント', 'ツール呼び出し']];
    rcv.forEach((r, i) => {
      const y = 1.95 + i * 0.68;
      s.addShape(SH.LINE, { x: 3.2, y: Math.min(3.65, y + 0.3), w: 1.25, h: Math.abs(y + 0.3 - 3.65), flipV: y + 0.3 < 3.65, line: { color: L.MUTED, width: 1.25, endArrowType: 'triangle' } });
      L.box(s, [{ text: r[0], options: { bold: true, fontSize: 13, breakLine: true } }, { text: r[1], options: { fontSize: 11 } }], { x: 4.5, y, w: 2.9, h: 0.6, fill: C.background2, color: C.text1, lineColor: L.BORDER, bold: false });
    });
    L.card(s, { x: 7.8, y: 1.95, w: 4.9, h: 2.35, color: C.accent3, icon: 'MdCallSplit', title: '受け手ごとに読み方がずれる', titleSize: 15, body: ['配列か、空白区切りの文字列か', '数値の ID が、言語によって丸められる', 'クレームが無いのか、null なのか', 'ヘッダーに移すと、偽装の余地が生まれる'], bodySize: 12.5 });
    L.note(s, 'tip', '読み方を受け手に任せない。名前・型・無いときの意味を発行側で決め、共通の検証部品で読ませる', { x: 7.8, y: 4.5, w: 4.9, h: 1.6, size: 13 });
  }

  {
    const s = L.content('事故の例：署名は正しかった。受け入れてはいけなかった', {
      lead: 'どの事故も、暗号が破られたのではない。どのクレームを、どこまで確かめるかの設計が欠けていた',
      stages: [3, 4],
      notes: 'クレームの設計と検証の欠落が事故になった例です。Storm-0558 は 2023 年に、個人向けアカウントの署名鍵で企業向けのトークンが偽造され、22 の組織と個人 503 のアカウントのメールが読まれた事件です。米国のサイバー安全審査委員会の報告書によると、鍵の一覧を公開する共通の仕組みに個人向けと企業向けの鍵が並んでいたのに、SDK がその区別を検証しておらず、アプリの開発者はライブラリが検証していると思い込んでいました。CVE-2025-55241 は、Entra ID のサービス間で使われる Actor token を包んだ、署名のない代理用のトークンを、古い API が発行元のテナントを確かめずに受け入れていた問題です。Actor token そのものは Microsoft が署名しています。nOAuth は 2023 年に、変更できるメールアドレスのクレームを利用者のキーにしていたアプリで、アカウントが乗っ取れた問題です。GitHub Actions のトークンでは、名前だけで作った sub が、リポジトリの改名や再作成で別の持ち主にも作れてしまうため、2026 年 7 月 15 日以降に作成、改名、移譲したリポジトリでは、数値の ID を含む形になりました。既存のリポジトリは、選択して切り替えます。4 つとも、署名は正しく、問題はどのクレームを何と照合するかでした。',
      refs: { spec: 'OIDC Core §5.7（sub と iss だけが安定）', inst: 'CSRB 報告書（2024-03、Storm-0558）／NIST IR 8587 §5.2.1.2（鍵のスコープ）', book: '『実践 Keycloak』2.4 節 p.24（sub をキーにする）' },
    });
    L.table(s, [['事例', '何が起きたか', '欠けていた確認', 'クレーム設計の教訓'],
      ['Storm-0558（2023）', '個人向けの署名鍵で、企業向けのトークンを偽造。22 組織と 503 アカウントのメールが読まれた', '鍵と発行者の対応。ライブラリが確認していると思い込んだ', '「署名が正しい」と「受け入れてよい」は別。iss と鍵の組を確かめる'],
      ['CVE-2025-55241（2025）', 'Actor token を包む署名なしの代理トークンを、古い API がテナントを確かめずに受理', '発行元のテナント（tid）', 'テナントのクレームは、必ず照合する。代理のトークンにも署名と期限'],
      ['nOAuth（2023）', 'メールアドレスをキーにしたアプリで、他人のアカウントに入れた', 'email が検証済みか。そもそも email は変更できる', '変更できる属性をキーにしない。sub（と iss）をキーにする'],
      ['GitHub Actions の sub（2026 改定）', '名前だけの sub は、改名や再作成で別の持ち主にも作れた', '名前ではなく不変の ID', '名前と ID を対で出し、照合は ID で。区切り文字も設計する']],
    { x: 0.6, y: 1.9, w: 12.1, colW: [2.4, 3.6, 2.9, 3.2], fontSize: 11, rowH: 0.7 });
    L.note(s, 'leader', '暗号ではなく「どのクレームを、何と照合するか」が破れた。照合の規則は、ライブラリではなく組織で決める', { x: 0.6, y: 5.95, w: 12.1, h: 0.6, size: 13, label: '' });
  }

  {
    const s = L.content('全体の構成', {
      lead: '既にあるクレームを知る → 独自クレームを設計する → 流す・読む → 期限と情報を守る → 治める',
      notes: '導入のあと、全体は 12 の Part に分かれます。Part 1 で JWT の構造と検証の基本を押さえ、Part 2 と 3 で、標準のクレームと 4 つの IdP が既に出しているクレームを、用途ごとに整理します。ここまでが、独自クレームを作る前に知っておくべき地図です。Part 4 から本題で、独自クレームの設計原則、権限の表し方、サービス間の流れでどこで足しどこで絞るか、データ層での使い方を扱います。Part 8 と 9 で、有効期限と、機微な情報の扱いを、Part 10 で AI エージェントを扱います。最後に、クレームを組織で治めるためのガバナンスと、テックリーダーの実践をまとめます。',
    });
    const parts = [
      ['1', '基礎', 'JWT の構造と検証'], ['2', '既存の地図', '用途別の標準クレーム'], ['3', 'IdP の実際', 'Entra・Keycloak・Auth0/Okta・Cognito'], ['4', '設計原則', '名前・型・識別子・書き手'],
      ['5', '権限の表現', '利用者・サービス・システム、テナント'], ['6', '流れ', 'どこで足し、どこで絞るか'], ['7', 'データ層', '行単位の制御と DB 認証'], ['8', '期限', 'リフレッシュ・失効・非同期'],
      ['9', '機微情報', '最小化・暗号化・ログ'], ['10', 'AI エージェント', '委任・承認・ツール'], ['11', 'ガバナンス', '台帳・契約テスト・変更手順'], ['12', '実践', 'アンチパターンとチェックリスト']];
    parts.forEach((p, i) => {
      const col = i % 4, row = Math.floor(i / 4);
      const x = 0.6 + col * 3.06, y = 1.95 + row * 1.45;
      const fill = row === 0 ? C.accent5 : row === 1 ? C.accent1 : C.accent4;
      s.addShape(SH.ROUNDED_RECTANGLE, { x, y, w: 2.86, h: 1.25, rectRadius: 0.08, fill: { color: fill, transparency: 88 }, line: { color: fill, width: 1 } });
      L.T(s, 'PART ' + p[0], { x: x + 0.15, y: y + 0.1, w: 2.6, h: 0.3, fontSize: 11, bold: true, color: fill, margin: 0, charSpacing: 2 });
      L.T(s, p[1], { x: x + 0.15, y: y + 0.38, w: 2.6, h: 0.4, fontSize: 16, bold: true, margin: 0 });
      L.T(s, p[2], { x: x + 0.15, y: y + 0.78, w: 2.6, h: 0.4, fontSize: 11.5, color: L.MUTED, margin: 0 });
    });
    L.T(s, [{ text: '地図（1〜3）', options: { bold: true, color: C.accent5 } }, { text: '　設計と流れ（4〜7）', options: { bold: true, color: C.accent1 } }, { text: '　守りと統治（8〜12）', options: { bold: true, color: C.accent4 } }], { x: 0.6, y: 6.3, w: 12.1, h: 0.35, fontSize: 13, margin: 0 });
  }

  {
    const s = L.content('用語：この資料での呼び方', {
      lead: '同じものを仕様ごとに違う名前で呼ぶ。この資料では次の呼び方に揃える',
      notes: '用語を揃えます。トークンは、この資料では主に JWT 形式のアクセストークンと ID トークンを指します。クレームは、トークンの中身の名前と値の組です。属性は、主体が持つ性質そのもので、クレームはそれを運ぶ形です。発行者は、トークンに署名して発行する主体で、IdP、OAuth の認可サーバー、内部のトークン発行サービスがこれに当たります。受け手は、トークンを受け取って検証し、判断に使う側で、OpenID Connect では RP、OAuth ではリソースサーバーと呼びます。主体は、トークンが誰について述べているかで、利用者だけでなく、サービスや AI エージェントも主体になります。PEP と PDP は認可の役割で、PEP は要求を止めたり通したりする場所、PDP は許可するかを判断する場所です。',
      refs: { spec: 'RFC 7519 §2（用語）／OIDC Core §1.2', inst: 'NIST SP 800-162 §3（PEP・PDP）', book: '『デジタルアイデンティティのすべて』（考え方）2.1 節・12.3 節（pp.194–195）' },
    });
    L.table(s, [['この資料の呼び方', '意味', 'ほかの呼び方'],
      ['トークン', '主に JWT 形式のアクセストークンと ID トークン', 'アサーション（SAML、NIST）'],
      ['クレーム', 'トークンの中の、名前と値の組', '属性値、claim'],
      ['属性', '主体が持つ性質。クレームはそれを運ぶ形', 'attribute'],
      ['発行者', 'トークンに署名して発行する主体', 'IdP、認可サーバー（AS）、STS、内部のトークン発行サービス'],
      ['受け手', 'トークンを検証し、判断に使う側', 'RP、リソースサーバー（RS）、API'],
      ['主体', 'トークンが誰について述べているか。利用者・サービス・エージェント', 'subject、principal'],
      ['PEP／PDP', '要求を止める場所／許可するかを判断する場所', 'ポリシー実施点／判断点']],
    { x: 0.6, y: 1.95, w: 12.1, colW: [2.2, 5.8, 4.1], fontSize: 12.5, rowH: 0.52 });
  }

  {
    const s = L.content('根拠の示し方：仕様・公的な指針・日本語の専門書', {
      lead: '各スライドの下に 3 種類の根拠を示す。権威の高い指針を優先し、書籍は章とページで示す',
      notes: 'この資料の内容が、どの文書に基づくかを示します。仕様は、IETF の RFC と OpenID Foundation の仕様です。公的な指針は、米国の NIST、国際的な非営利団体の OWASP と OpenID Foundation、日本のデジタル庁などの文書です。とくに、NIST が 2026 年 9 月に CISA と共同で出した IR 8587 は、トークンの必須要素の文書化、1 時間以内の有効期間、宛先のないトークンの拒否、トークンと個人情報をログに残さないこと、AI エージェントへの適用を定めており、多くのスライドの根拠になります。日本語の書籍は 4 冊で、章・節・印刷ページで示します。『デジタルアイデンティティのすべて』は概念の書籍で、JWT の実装を扱っていないため、この本は「考え方に沿う」という形で引きます。『実践 Keycloak』の日本語版は Keycloak 18 が前提で、現行版と違う記述は使っていません。',
      refs: { inst: 'NIST IR 8587（2026-09、CISA 共著）／SP 800-63C-4（2025-07）／SP 800-162／OWASP ASVS 5.0／デジタル庁 DS-212・DS-511' },
    });
    const cols = [
      ['MdDescription', C.accent1, '仕様', ['RFC 7519（JWT）・8725（安全な扱い）', 'RFC 9068（アクセストークン）・8693（委任）', 'OpenID Connect Core 1.0', 'Transaction Tokens（草案 11）・MCP 認可仕様']],
      ['MdAccountBalance', C.accent4, '公的な指針', ['NIST IR 8587・SP 800-63C-4・SP 800-162', 'OWASP ASVS 5.0・JWT Cheat Sheet', 'デジタル庁 DS-212・DS-511', 'OpenID Foundation（エージェントの ID 管理）']],
      ['MdMenuBook', C.accent2, '日本語の専門書', ['『OpenID Connect入門』技術評論社 2026（OIDF-J 理事 監修）', '『デジタルアイデンティティのすべて』オライリー 2024（OIDF-J 代表理事 監訳）', '『実践 Keycloak』オライリー 2022', '『セキュアAPI』翔泳社 2026']]];
    cols.forEach((c, i) => L.card(s, { x: 0.6 + i * 4.13, y: 1.95, w: 3.85, h: 3.6, icon: c[0], color: c[1], title: c[2], titleSize: 16, body: c[3], bodySize: 12 }));
    L.note(s, 'warn', '仕様の状態は 2026-11-17 時点。草案（Transaction Tokens など）は名前や規則が変わりうる', { x: 0.6, y: 5.75, w: 12.1, h: 0.7, size: 13, label: '' });
  }
};
