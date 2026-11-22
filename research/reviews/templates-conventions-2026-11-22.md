# 点検の記録（2026-11-22）：共通規約と完了の定義（#13、PR #23）

`templates/CONTRIBUTING.md`・`templates/casestudy-mapping.md`・`templates/README.md`・`templates/CHANGELOG.md`・`templates/LICENSE`・`LICENSE-CONTENT.md` を、作成とは別の LLM のセッションで点検した記録。人による点検は未実施（#20）。

- 作成：2026-11-22（コミット `c28e830`）
- 点検：2026-11-22。Claude Opus 5.5、作成とは別のセッション（作成の会話の履歴は引き継いでいない）
- 点検の原文：https://github.com/Takenori-Kusaka/jwt-claims-guide/pull/23#issuecomment-7074027256
- 渡した資料：PR #23 のコミット `c28e830`、issue #2・#3・#11・#13・#16・#22 の本文と #1〜#22 の本文、ケーススタディ `jwt-claims-casestudy@080b8da`（`catalog/catalog.json`・`catalog/decisions/part*.json`・`SCHEMA.md`・`DECISION_POLICY.md`・`results/matrix.json`・`results/measurements.json`・`README.md`）、CC0 1.0 の legalcode.txt、`draft-ietf-oauth-transaction-tokens-11`、OWASP ASVS v5.0.0
- 渡した指示の要旨（英語の原文から要約）：作成者ではない独立した点検者として、次を確かめる。(1) #13 の完了基準ごとの充足と証拠。(2) 事実（CC0 の条文が公式のまま、LICENSE-CONTENT.md の記述、版付き ID の書式の例、ケーススタディのファイル名・シナリオ A/B/C の名前・IdP・件数・一覧表の行数・コミット 080b8da の実在）。(3) 計画（#11・#3・#22）との整合と内部の矛盾、後の issue を形だけで閉じられる抜け道。(4) 文体と用語。指摘は既存の区分（誤り・過大・不一致・曖昧）で、file:line と直し方を付ける。PR へのコメントは 1 件にまとめ、push はしない。作成者の結論や意図は渡していない
- 作成者の 1 日以上空けた見直し：未実施（2026-11-23 以降に行い、日付をここに書く）

## 点検した件数

| 対象 | 点検した件数／全件数 |
| --- | --- |
| 事実（件数・ファイル名・コミット・仕様の節・版） | 全件（点検の原文の「確かめて問題がなかったもの」と指摘 1・11〜15） |
| `templates/LICENSE` | 全文（公式の条文とバイト単位で一致、SHA-256 一致） |
| 根拠の ID の実在 | 全件（ASVS v5.0.0-8.3.2、draft-ietf-oauth-transaction-tokens-11 §12.2、RFC 8693 §4.1、RFC 9700 §2.4 は原典で確認。『実践 Keycloak』・CSRB・NIST IR 8587 はガイドの既存の根拠との一致だけを確認） |
| 対象外の行 | 該当なし（この成果物に対象外の行はない） |

## 指摘と直し方

区分：誤り＝必ず直す／過大＝原典より強い言い方／不一致＝成果物の間の食い違い／曖昧＝読み違えやすい

| # | 対象 | 区分 | 指摘 | 直し方 |
| --- | --- | --- | --- | --- |
| 1 | casestudy-mapping 2. | 誤り | 汎用の攻撃 15 件（Part 1）。実際は攻撃 14・正規 1、Part 0・4 も含む | 「汎用のケースが 15 件（G0〜G14。攻撃 14・正規 1。主に Part 1 で、Part 0・4 のものを含む）」に直した。ケーススタディの README は別に直す |
| 2 | casestudy-mapping 1.・7. | 不一致 | 正とする側が 1. と 7. で食い違う | 正の向きを 1 つにした。一覧表（ORG の名前・型を含む）と判定はケーススタディ、設計判断とカタログは `templates/`。名前・型を変えるときはケーススタディを PR で直してコミットを上げる。判定を変えるときは `templates/casestudy-deviations.yaml` に載せ、ケーススタディは変えない |
| 3 | CONTRIBUTING 2. | 不一致 | 抜き取りの点検と根拠 ID の実在の確認が無い | 完了の定義に 3 項目を足した：根拠の ID の実在を全件機械で、根拠の中身を 10%（最低 10 件）抜き取り、対象外の行を無作為に 5 件抜き取り。数は筆者の提案（追跡 #20） |
| 4 | CONTRIBUTING 2. | 不一致 | 「すべて反映」と「理由を書けばよい」 | 「指摘ごとに、反映したか、反映しない理由を記録している。反映しない指摘は、理由を別の点検で確かめている」にそろえた |
| 5 | CONTRIBUTING 2. | 曖昧 | 抑止 0 件と、入れてよいが両立する | error の抑止・引き下げは 0 件（例外なし）、warning の抑止は行ごとの理由と件数・一覧を完了のコメントに、に直した |
| 6 | CONTRIBUTING 2. | 曖昧 | 事実の点検が全件か抜き取りか | 新しい成果物と変更箇所の事実は全件。抜き取りは明記した 2 項目だけ。記録に「点検した件数／全件数」を必須にした |
| 7 | CONTRIBUTING 3. | 曖昧 | LLM の点検に渡す資料の条件がない | 渡すもの（成果物・issue の本文・一次資料）、渡さないもの（作成者の結論・仮説）、記録するもの、指摘 0 件のときの確かめた項目の一覧を足した |
| 8 | CONTRIBUTING 1. | 曖昧 | `author-proposal` の追跡 issue の条件がない | `tracking` に issue の番号を必須にし、追跡 issue は提案ごとに 1 項目、開いているか結論を書いて閉じる、とした |
| 9 | CONTRIBUTING 1.、mapping 3. | 曖昧 | 論文・技術記事・業界の語彙の行き先がない | 7 番目の種類 `research`（論文・技術記事）を足した。業界の属性語彙は `spec` とした。`source_kind` の 9 つの値すべての行き先の表を対応表に足した |
| 10 | CONTRIBUTING 4.、mapping 1. | 不一致 | ライセンスの理由が #3（スライドの文言を使う）と矛盾 | 筆者自身の文章は `templates/` に入れた部分を筆者が CC0 で提供し直す、と CONTRIBUTING と `LICENSE-CONTENT.md` に書いた。ケーススタディを写さない理由は二重管理と作り方の違いにし、ライセンスを理由から外した |
| 11 | mapping 3. `log_policy` | 過大 | 「同じ」「1 対 1」 | 「一部」にし、781 行が記載なし、「平文で可」と「記録する」の向きの違い、マスクが台帳にないことを書いた |
| 12 | mapping 3. `verified`・`checked_on` | 曖昧 | 何と「意味が違う」のかが読めない | 2 行に分けた：`checked_on` ↔ #2 の `verified_on`（一部、台帳の `last_verified` とは別）、`verified`（真偽値）↔ なし。規約では確かめた日を `verified_on`（日付）に書くことに統一した |
| 13 | mapping 4. `checks_note` | 過大 | `checks_note` を `evidence` と「同じ」 | `checks` は同じ、`checks_note` は一部（写さない）に分けた |
| 14 | mapping 6. | 曖昧 | `measurements.json` の場所と「RT も新しい値」 | `keycloak.refresh_reevaluation`・`keycloak.logout_introspection`・`C.keycloak_exchange` と経路で書き、「RT はローテーションされた（`refresh_token_rotated: true`）」に直した |
| 15 | mapping 3. `name`・`support` | 曖昧 | ORG-08 の形、`support` の値の抜け | 「ORG-08 を除き」と ORG-08 の形を書いた。`support` は「主な値」とし、「不明」と条件つきの値があることを書いた |
| 16 | mapping 8. | 曖昧 | 後続 issue への引き継ぎを確かめる手段がない | 8. を #3・#2・#16 ごとのチェックリストにし、各 issue を閉じるときに項目ごとに実装したか理由を書く、とした。7. の末尾に「対策は未実施」を明記した。各 issue へのコメントはマージ後に行う（未実施） |
| 17 | CONTRIBUTING 2. 対象外の例 | 曖昧 | 例の `status` が台帳の `status` と取り違えやすい | 列名を仮の `coverage` に変え、#2 のカタログの行の例で列名は #2・#3 で決める、と書いた |
| 18 | CONTRIBUTING 1. ASVS | 不一致 | `asvs_ids` と `refs` の 2 か所 | 台帳では `asvs_ids` だけに書き `refs` には書かない、列のない成果物では `refs` に `ASVS v5.0.0-8.3.2` と規格名つきで、とした。スキーマでの確認を #3 に渡した |
| 19 | CONTRIBUTING 4. JSON Schema | 曖昧 | 最上位の独自キーが Ajv の strict でエラー | JSON Schema は `$id` の版と最上位の `$comment` に書き、独自のキーワードは置かない、とした。スキーマ以外の JSON データは最上位のキー |
| 20 | CONTRIBUTING 4. | 不一致 | Markdown の 1 行目が `template_version` と見出しの両方 | 注意書きを「`template_version` の行の次にある最初の見出しの直後」に直した。Markdown の `template_version` は HTML のコメントとし、前付けは使わないと明記した |
| 21 | CONTRIBUTING 4. | 曖昧 | JSON・トークン・コードの教材の表示がない | ファイル名の `.broken`、ディレクトリの README、ファイルの中（JSON の `_warning`、JSON Schema の `$comment`、トークンの `_warning` クレーム）の 3 つを定めた |
| 22 | README 点検状況 | 不一致 | 規約の定型文と違う | 規約に、見直し前の段階の定型文を足し、README をその文（記録のパスつき）にした。見直しの後に最終の定型文に置き換える（未実施） |
| 23 | mapping 全体、CONTRIBUTING 5. | 曖昧 | ケース／シナリオ、カタログ／一覧表の言い換えの宣言がない | 対応表の冒頭に用語の表を足し、本文を「一覧表」にそろえた。CONTRIBUTING 5. にもケースとシナリオの言い分けを書いた |
| 24 | #13 の完了基準 1 | 曖昧 | `CONTRIBUTING.md` へのリンクが #13 に無い | マージ後に #13 へ main のリンクをコメントし、閉じるコメントにも載せる（未実施。マージ前にはリンク先が main に無いため） |

反映しない指摘はない。マージ後に行う作業（16・22・24）が残っている。
