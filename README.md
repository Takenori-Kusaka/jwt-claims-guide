# JWT クレーム設計ガイド：組織で共用する独自クレームを、どう設計し、どう流し、どう治めるか

認証認可とマイクロサービスの設計を任された新任のテックリーダーに向けた解説スライドです（全 152 枚、解説ノートつき）。主題は、OpenID Connect や OAuth の標準クレームそのものではなく、**組織のあらゆるサービスで共用する独自クレーム**の設計・伝搬・検証・ガバナンスです。独自クレームで既存のクレームと重複・衝突しないよう、標準クレームの地図と、4 つの IdP（Microsoft Entra ID・Keycloak・Auth0/Okta・Amazon Cognito）の実際を前提として扱います。

- Web スライド: https://takenori-kusaka.github.io/jwt-claims-guide/
- PDF / PPTX: [slides/](slides/)
- Docswell: https://www.docswell.com/s/takenori_kusaka/ZWR7NJ-jwt-claims-guide
- ケーススタディ（実測、67 ケースの攻撃・正規の要求と除去実験）: https://github.com/Takenori-Kusaka/jwt-claims-casestudy
- ケーススタディのスライド（49 枚、Web 版）: https://takenori-kusaka.github.io/jwt-claims-casestudy/（Docswell: https://www.docswell.com/s/takenori_kusaka/KJWMVQ-jwt-claims-casestudy）
- 付録：JWT クレーム一覧（xlsx、805 行、3 ケースの採否つき）: https://github.com/Takenori-Kusaka/jwt-claims-casestudy/blob/main/catalog/jwt-claims-catalog.xlsx

## 中心の主張

クレームは、1 つの発行者が書き、多数のサービスが読む「契約」です。名前空間・型・意味と意味しないこと・書き手・寿命・持ち主を決め、台帳に載せてから足す。受け手は、署名・発行者・宛先・期限・種類を確かめてから読む。トークンは発行時点の写しなので、変わりやすい権限や関係は載せずに都度判定する。銀の弾丸はなく、どの組織でも外せない共通の基準の上で、何に重点を置き、何を見送るかを、見直しの条件とともに決める。

## 構成

| Part | 内容 |
| --- | --- |
| 0 | 導入：クレームはサービス間の契約、事故の例（Storm-0558、CVE-2025-55241、nOAuth、GitHub の sub） |
| 1 | 基礎：JWT の構造、検証の順序、危険なヘッダー、ID トークンとアクセストークン、ライブラリの既定値 |
| 2 | 既存のクレームの地図：16 の用途ごとの標準クレームと、独自クレームが要る隙間、SAML の属性 |
| 3 | 4 つの IdP の実際：利用者キー・テナント・aud・ロールの位置・独自クレームの規則、最近の変更 |
| 4 | 独自クレームの設計原則：載せるか問い合わせるか、名前空間、型、不変の ID、書き手、サイズ、前方互換 |
| 5 | 権限の表現：利用者・ワークロード・システム、RBAC/ABAC/関係ベース、マルチテナント、BOLA |
| 6 | 流れ：どこで足し、どこで絞るか（発行時フック、入口での交換、Transaction Tokens、ヘッダー、証跡） |
| 7 | データ層：行単位の制御、DB の文脈と信頼境界、接続プール、トークンでの DB 認証、マスキング |
| 8 | 有効期限・リフレッシュ・失効・非同期処理 |
| 9 | 機微情報・最小化・ログ |
| 10 | AI エージェントのアクセスポリシー：委任（act）、ツールごとのスコープ、承認の証拠、MCP の認可 |
| 11 | ガバナンス：クレームの台帳、スキーマと契約テスト、変更の手順、追加前の 25 の質問 |
| 12 | 実践：アンチパターン、レビューの観点、重点と見送り、主張と根拠の対応、参考文献 |

## 根拠

各スライドの下に、仕様・公的な指針・日本語の書籍の 3 種類の根拠を示しています（調査基準日 2026-11-17）。

- 仕様：RFC 7519・8725・9068・8693・9700・7662・9396 など、OpenID Connect Core、Transaction Tokens（草案 11）、MCP 認可仕様（2026-07-28）
- 公的な指針：NIST IR 8587・SP 800-63C-4・SP 800-162、OWASP ASVS 5.0・JWT Cheat Sheet、デジタル庁 DS-212・DS-511、CSRB 報告書（Storm-0558）
- 日本語の書籍（章・印刷ページで引用）：『OpenID Connect入門』（技術評論社 2026）、『デジタルアイデンティティのすべて』（オライリー・ジャパン 2024、考え方の根拠として引用）、『実践 Keycloak』（オライリー・ジャパン 2022）、『セキュアAPI』（翔泳社 2026）

調査メモ（仕様・IdP・事故事例・公的な指針・独自クレームの実例・データ層・マイクロサービスの流れ）は [research/notes/](research/notes/) にあります。設計書テンプレート構想の調査（レポート・調査ノート・未検証点の表）は [research/template-design/report.md](research/template-design/report.md) にあります（人による点検は未実施）。書籍の章・印刷ページとの対応表（書籍ノート 10〜13）も公開しています。書籍の文の引用は、出典の章・印刷ページを明記し、ノートの本文を主・引用を従とし、必要最小限の短い引用に限っています（点検の記録：[research/reviews/book-quotes-2026-11-22.md](research/reviews/book-quotes-2026-11-22.md)）。全スライドは、作成とは別の担当が一次資料に当たって事実を点検し、指摘を反映しています。

## 前提と限界

- 製品の挙動（特に各 IdP）は 2026 年 11 月時点の公式文書によります。変わりうるので、採用前に現行の文書で確かめてください。
- 草案（Transaction Tokens、ID-JAG など）は、名前や規則が変わりえます。
- 一次資料に記載がなく筆者の推奨・提案として示したもの（契約テスト、監査の指標など）は、スライド上で「筆者の推奨」「筆者の提案」と明示しています。

## ビルド

```bash
cd deck && npm install                       # pptxgenjs など（deck/node_modules。lock ファイルは管理しない）
cd deck && node build.js                     # PPTX と deck/slide_ids.json を書く
cd deck && node build.js --ids-only          # deck/slide_ids.json だけを書く（PPTX は書かない）
cd deck && node build.js --ids-only --register   # 新しいスライドの ID を台帳に登録する
python tools/build_web_slides.py             # docs/（slides.json・index.html・slide_ids.csv）を作る
python tools/check_slide_refs.py [ファイルやディレクトリ ...]   # スライド ID・台帳・参照を確かめる
python -m unittest discover -s tools/tests -v                  # ID の仕組みのテスト（node と Playwright がなければ一部を飛ばす）
python tools/tests/cmp_pptx.py before.pptx after.pptx          # 2 つのビルドで描画に関わる部分が同じかを比べる
```

`build_web_slides.py` は、`docs/slides/` に書き出し済みの PNG があれば WebP に変換し、なければ既存の画像に触れずに `slides.json` と `index.html` だけを作り直します（PNG の書き出しには PowerPoint が要ります：`deck/export.ps1`）。`deck/package-lock.json` は `.gitignore` に入れています。依存は `package.json` の範囲指定で入れ、成果物が変わっていないことは `cmp_pptx.py` で出力を比べて確かめるためです。

## スライドの固定 ID

各スライドには、番号とは別の ID があります（例：`p04-carry-or-query`）。スライドを足して番号がずれても、ID は変わりません。根拠としてスライドを参照するときは、番号ではなく ID を使ってください。

### ID の規則
- 形式は `pNN-<slug>` です。`slug` は英小文字と数字の語を `-` でつないだものです
- `pNN` は、ID を初めて付けたときに、そのスライドを定義していた Part の番号です（`deck/pNN.js`）。**接頭辞は発行時に固定**します。後でスライドを別の Part に移しても、ID は変えません
  - ビルドは、台帳にない新しい ID に限って、接頭辞と Part が合っているかを確かめます
- 一度付けた ID は変えず、使い回しもしません。スライドを削除したら、台帳でその ID を `retired` にします（欠番）

### 定義と台帳
- **定義**：`deck/p*.js` の各スライドに `id` を書きます。書き方は次の 3 通りです。ID は画面には出ません
  - `L.content(title, { id: '…', … })`
  - `L.divider(…, notes, { id: '…' })`
  - `L.slide({ id: '…', … })`
- **台帳**：`deck/slide_ids_registry.json` は、発行したすべての ID の記録です。追記だけを行い、行を消しません。ID ごとに次を書きます
  - `issued`：発行日
  - `title`：最初のタイトル
  - タイトルを意図して変えたとき：`retitled` に `{"date", "title"}` を追記します
  - 削除したとき：`retired`（日付）と `reason` を足します
- **新しいスライドを足したとき**：`node build.js --ids-only --register` で台帳に登録します
- **ビルドが失敗する場合**：
  - `id` がない
  - 形式が違う
  - 重複している
  - 台帳にない（`--register` なしの場合）
  - `retired` の ID を使っている
  - 台帳にある有効な ID が、どのスライドにもない（改名や削除を `retired` にせずに行った場合）
  - 新しい ID の接頭辞が、定義している Part と合わない

### 一覧
- `deck/slide_ids.json`：ビルドが出力します。`title` は `deck/p*.js` に書いたタイトルです
- `docs/slides.json`：`id` 欄があります
- 番号との対応表 [docs/slide_ids.csv](docs/slide_ids.csv)：列は `n,id,title,source_title` です。番号で書いた既存の参照を ID に置き換えるときに使います
  - `title` は、Web 版と `slides.json` に出るタイトルです（PPTX のタイトル枠）
  - `source_title` は、`deck/p*.js` に書いたタイトルです
  - 表紙と Part の扉の 13 枚だけは、2 つが違います（例：`PART 1` と `基礎：JWT の構造と検証`）

### Web 版
- `https://takenori-kusaka.github.io/jwt-claims-guide/#p04-carry-or-query` で、そのスライドが開きます
- 従来の、番号で指す `#s47` の形も開けます。ただし、番号はずれるので、文書には書かないでください
- 見つからない ID や壊れたハッシュのときは、1 枚目を開き、見つからなかったことを表示します

### 文書からの参照
参照は `slide:<id>` と書きます（例：`slide:p04-carry-or-query`）。文法は次のとおりです。

```
ref    = "slide:" id [ ".R" 1*DIGIT ]          ; "slide" は小文字、":" の前後に空白を入れない
id     = "p" 2DIGIT "-" word *( "-" word )     ; word = 1*( a-z / 0-9 )
```

- `slide:` の直前が英数字・`_`・`-` のときは、参照とみなしません
- ID は、`slide:` の後の英数字・`_`・`-` の並びです。それ以外の文字（`.`・`,`・`)`・空白・日本語など）で終わります
  - `_` や英大文字を含むときと、末尾が `-` のときは、形式違いのエラーになります
- ID の直後の `.R<数字>` は、要件の番号です（例：`slide:p06-narrow-downstream.R1`。文法は #22 で決めます）。番号の部分は検証しません
- `.` の後がそれ以外のときは、参照は ID で終わります。そのため、文末の `.` は問題ありません
- `slide:` の後に英数字が続かないとき（`slide:<id>` のような書式の説明）は、参照とみなしません
- 参照に見えて形が違うものは、エラーにします。対象は、`slide` の大文字小文字が違うものと、`:` の前後に空白があるもので、後ろに ID らしい文字列か番号が続く場合です
- Web 版の URL（`takenori-kusaka.github.io/jwt-claims-guide/#…`）も検査します。番号で指す形（`#sNN`）と、存在しない ID はエラーです

### 確かめ方
`python tools/check_slide_refs.py templates research` のように、調べるファイルやディレクトリを渡します。次の 1 つでも外れれば、終了コード 1 で失敗します。

- ID がそろって一意であること
- `deck/slide_ids.json` が `deck/p*.js` の宣言と一致していること（古くないこと）
- 枚数が `deck/p*.js` で宣言した数と同じであること（`--expect N` でも指定できます）
- `docs/slides.json` と一致していること
- 台帳の規則：
  - 未登録の ID・`retired` の再使用・消えた ID がないこと
  - タイトルが台帳のタイトルから大きく変わっていないこと（類似度 0.6 未満は失敗）
  - 他の ID の台帳のタイトルに、より近くないこと（ID の付け替えの検出）
- 渡した中の参照が、すべて実在の ID を指していること

スキャンの対象：
- ディレクトリは、`.md` `.markdown` `.txt` `.rst` `.adoc` `.yaml` `.yml` `.json` `.csv` `.tsv` `.py` `.js` `.ts` `.html` `.toml` `.rego` `.cel` を再帰的に調べます。`--ext` で拡張子を足せます
- 直接渡したファイルは、拡張子によらず調べます
- UTF-8 でないファイルは、エラーにします
- `.xlsx` などのバイナリは調べません

`--base origin/main` を付けると、台帳がその版から追記だけで変わっていることも確かめます（エントリの削除や、`issued`・`title`・`retired` の書き換えを検出します）。

## ライセンス

スライド・文章は CC BY 4.0、コードは MIT です（[LICENSE-CONTENT.md](LICENSE-CONTENT.md)、[LICENSE](LICENSE)）。本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。
