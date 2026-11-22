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

調査メモ（仕様・IdP・事故事例・公的な指針・独自クレームの実例・データ層・マイクロサービスの流れ）は [research/notes/](research/notes/) にあります。書籍の章ごとの対応表は著作権に配慮して公開していません。全スライドは、作成とは別の担当が一次資料に当たって事実を点検し、指摘を反映しています。

## 前提と限界

- 製品の挙動（特に各 IdP）は 2026 年 11 月時点の公式文書によります。変わりうるので、採用前に現行の文書で確かめてください。
- 草案（Transaction Tokens、ID-JAG など）は、名前や規則が変わりえます。
- 一次資料に記載がなく筆者の推奨・提案として示したもの（契約テスト、監査の指標など）は、スライド上で「筆者の推奨」「筆者の提案」と明示しています。

## ビルド

```bash
cd deck && NODE_PATH=<pptxgenjs などを入れた node_modules> node build.js   # PPTX と deck/slide_ids.json を書く
cd deck && node build.js --ids-only                                       # slide_ids.json だけを書く（PPTX は書かない）
python tools/build_web_slides.py                                          # docs/（slides.json・index.html・slide_ids.csv）を作る
python tools/check_slide_refs.py [ファイルやディレクトリ ...]              # スライド ID と参照を確かめる
```

`build_web_slides.py` は、`docs/slides/` に書き出し済みの PNG があれば WebP に変換し、なければ既存の画像に触れずに `slides.json` と `index.html` だけを作り直します（PNG の書き出しには PowerPoint が要ります：`deck/export.ps1`）。

## スライドの固定 ID

各スライドには、番号とは別に変わらない ID があります（例：`p04-carry-or-query`）。スライドを足して番号がずれても、ID は変わりません。根拠としてスライドを参照するときは、番号ではなく ID を使ってください。

- 形式：`pNN-<kebab-case の英小文字・数字>`。`pNN` は定義しているファイル（`deck/pNN.js`）の Part 番号で、後から Part を移しても変えません。一度付けた ID は変えず、スライドを削除したら ID も欠番にします
- 定義：`deck/p*.js` の各スライドに `id` を書きます（`L.content(title, { id: '…', … })`、`L.divider(…, notes, { id: '…' })`、`L.slide({ id: '…', … })`）。`id` がない・重複・形式違い・別の Part の接頭辞のときは、ビルドが失敗します。ID は画面には出ません
- 一覧：`deck/slide_ids.json`（ビルドが出力）、`docs/slides.json` の `id` 欄、番号との対応表 [docs/slide_ids.csv](docs/slide_ids.csv)（`n,id,title`。番号で書いた既存の参照を ID に置き換えるときに使います）
- Web 版：`https://takenori-kusaka.github.io/jwt-claims-guide/#p04-carry-or-query` でそのスライドが開きます。従来の `#s47` の形も使えます
- 文書からの参照：`slide:<id>` と書きます（例：`slide:p04-carry-or-query`）。ID に使えない文字（`.`・`,`・`)`・空白など）で参照が終わるので、`slide:p06-narrow-downstream` の後ろに `.R1` のような要件の番号を続けても構いません
- 確かめ方：`python tools/check_slide_refs.py templates research` のように、調べるファイルやディレクトリを渡します。ID が 152 件そろって一意であること、`docs/slides.json` と一致していること、渡した中の `slide:<id>` がすべて実在の ID を指すことを確かめ、1 つでも外れれば終了コード 1 で失敗します（スライドの枚数が変わったら `--expect` で指定します）

## ライセンス

スライド・文章は CC BY 4.0、コードは MIT です（[LICENSE-CONTENT.md](LICENSE-CONTENT.md)、[LICENSE](LICENSE)）。本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。
