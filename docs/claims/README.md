# 設計書のエディター：実装のメモ

設計書のエディター（このディレクトリ。公開先は `https://takenori-kusaka.github.io/jwt-claims-guide/claims/`）の、作りと確かめ方の記録です。エディターを直す人と、仕組みを確かめたい人に向けて書いています。

- **使い方**は、[リポジトリの README](../../README.md) の「設計書のエディター」にあります。設計書の書き方は [templates/GETTING_STARTED.md](../../templates/GETTING_STARTED.md) です
- 文中のパス（`templates/…`・`tools/…`・`research/…`・`deck/…`）は、リポジトリのルートからのパスです
- `#49` のような番号は、このリポジトリの issue と PR の番号です（経緯をたどるために残しています）
- 画面の用語は、[templates/glossary.md](../../templates/glossary.md) の 5. にそろえています
- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施

## 経緯

設計書のエディター（#49）は、読むだけのビューアー（#36）を置き換えたものです。最初の画面と用語は #53、レビューは #50、レビューで既定で出す問いは #56 で作りました。

## 仕組みと確かめ方

- `https://takenori-kusaka.github.io/jwt-claims-guide/claims/` を開くと、**何も開いていない最初の画面**が出ます。記入例は「サンプルを開く」を押したときだけ読み込みます。スライドの Web 版（`/`）とは別のパスで、同じ公開の方式（`main` の `/docs`）のまま共存します
- **始め方（6 つの入口）**：ファイルを開く（複数）・フォルダを開く（`claims.yaml` のあるディレクトリを読む）・ドラッグ＆ドロップ（ファイルでもフォルダでもよい）・貼り付け・空の雛形から始める（`python tools/new_design.py` と同じ骨組み）・サンプルを開く（シナリオ A・B）。このほかに「設計書をレビューする」（設計書のファイルと `review.yaml` を選ぶと、レビューの手順から始まる）があり、このブラウザに自動保存した設計書は、最初の画面のいちばん上に「続きから開く」として出ます（#53）
- **最初に出る画面（#53）**：1 つのファイルを開くと、その画面が出ます（`claims.yaml` → クレームの一覧、`token_types.yaml` → トークン目録、`hops.yaml` → ホップの表、`catalog_answers.yaml` → カタログへの回答、`review.yaml` → レビュー）。いくつか開くと**ダッシュボード**（開いたファイルの件数・検査の結果・レビューの進み具合と、要対応の項目：error・再確認が要る判定・未回答の問い・カタログの未回答。どれも押すとその画面に移る）が出ます。開いていないファイルの画面は、メニューで薄く（印 ○）表示し、開くと「ファイルを足す」を出します
- **編集とレビュー（#53）**：上のバーで「編集」と「レビュー」を切り替えます。それぞれ最後に見た画面に戻ります。レビューではメニューの上にレビューの画面が並び、設計書の画面（行を判定する所）はその下です。用語は `templates/glossary.md` の 5. にそろえ、画面には issue の番号を出しません
- **幅の狭い窓（#53）**：上のバーの「エディター」「メニュー」で、左のエディターと画面のメニューを畳めます。幅が 1100px 以下ではメニューを畳んだ状態で開きます（760px 以下では縦に並べる）。エディターの行に移る操作をすると、畳んだエディターを開きます
- **更新の後のキャッシュ（#53）**：GitHub Pages は各ファイルを `Cache-Control: max-age=600` で送り、URL のクエリを無視します。版の無い URL では、ブラウザに残った古い `editor.js` と新しい `review.js` が一緒に動き、レビューが消えました（`TypeError: CE.registerCompanion is not a function`）。そこで `python tools/build_claims_viewer.py` が、エディターが読むすべてのファイルの URL に内容のハッシュ（`?v=<sha256 の先頭 12 桁>`）を付けます。`index.html` の `<script>`・`<link>` は書き換え、後から読むもの（サンプル・雛形・レビューの問い・claim_lint の worker・Pyodide の読み込み口・`claim_lint.zip`）は `data/build.js` のハッシュを使います。各モジュールとデータは版の ID（ビルド ID）を持ち、ページが起動するときに比べます。2 つの版のファイルが混ざると、何も起動せずに「新しい版が公開されました。再読み込みしてください」と「再読み込みする」のボタンを出します（例外は出さない）。CI の `--check` は、ハッシュの付け忘れ・古いハッシュ・古いビルド ID・ハッシュを通さない読み込み（`asset()` を使わない `src`・`fetch`・`importScripts`）を見つけます。2 つの版を続けて配信し、キャッシュを持つブラウザで切り替えるテストは `tools/tests/test_claims_editor_ux.py`
- **左右に分けた画面**：左は YAML のエディター（CodeMirror 6。ファイルごとのタブ：`claims.yaml`・`token_types.yaml`（発行方式 `issuance_profile` を含む）・`hops.yaml`・`catalog_answers.yaml`・`claim_request_*.md`・`design.md`。折り畳み・検索・元に戻す）。右は #36 の画面（ダッシュボード・クレームの一覧・台帳を行ごとに開く・詳細・トークン目録・発行方式と、導かれる要件・ホップの表・寿命の 4 つの層・カタログへの回答・検査の結果・判断の行・データ源・問いと仕組み・スライドと成果物の対応）
- **その場の検査**：編集すると少し待ってから検査します
  - YAML の構文（重複したキーを含む）と、台帳の JSON Schema（`templates/registry/*.schema.json`）は、ブラウザの中ですぐに検査します（yaml 2.9.1・@cfworker/json-schema 4.1.6）。Python の `re` の書き方 `(?i)` は、同じ意味の JavaScript の正規表現に書き換えて使います
  - claim_lint は Python のまま Pyodide 314.0.8（CPython 3.14.2 の WebAssembly 版）で動かします。「検査の結果」など Python が作る画面（メニューの印 `Py`。画面の上では「Python で計算する画面（初めて開くと読み込みに数秒）」と説明する）を開いたときに初めて読み込み、以後は編集のたびに Web Worker の中で `python tools/claim_lint <dir> --profile <full|lite> --also-scan <dir>/design.md` と同じ検査と render を行います。claim_lint とそれが読むファイル（カタログ・台帳のスキーマ・`deck/slide_ids.json`）は `docs/claims/data/claim_lint.zip` にまとめています
  - 指摘は、エディターの行（行番号の横の印と下線、タブの件数）と、プレビューの行（一覧・詳細・表の「検査」の列）の両方に出ます。指摘の行番号を押すと、エディターのその行に移動します。claim_lint が最新の内容で動いた後は、ブラウザの Schema の指摘の代わりに claim_lint の `SCHEMA` の指摘（CLI と同じもの）を出します
- **CLI との一致**：シナリオ A・B の Full と Lite で、ブラウザの claim_lint の結果（JSON の全体）が CLI と一致することをテストで確かめています（`research/claims-editor/parity.json`）。CI では、`claim_lint.zip` と worker の Python を CPython で動かして CLI と比べます
- **保存**：「このファイルを書き出す」（`Ctrl+S` でも）と「zip で書き出す」。開いたときの改行（CRLF）と BOM を保ったまま書き出します
  - **黙って消えない**：書き出していない変更があるときに、別の設計書を開く・閉じる操作をすると、ページの中の確認（「zip で書き出してから」「書き出さずに」「やめる」）を出します。ページを離れる（再読み込み・タブを閉じる）ときは、ブラウザが確かめます（`beforeunload`）。エディターの外へのリンク（スライド・RFC・GitHub など）は新しいタブで開き、エディターは残ります
  - **自動保存（localStorage）**：チェックを入れたときだけ行います。設計書のディレクトリごとに 1 件（`claims-editor:autosave:v2:<ディレクトリ>`）を保存し、別の設計書を開いても上書きしません。貼り付けた内容と、フォルダ無しで開いたファイルは、開いた日時と乱数の名前（例 `work/pasted-20261123-153012-a1b2c3`）で別々に保存します。保存するのは編集した後だけです（開いただけでは保存しない）。自動保存した版がある設計書をもう一度開くときは、自動保存した版（名前と保存した日時）と元のファイルのどちらを開くかを確かめます
    - 保存に失敗したとき（容量の超過など）は、画面の上に警告を出し続け、変更は「書き出していない」ものとして扱います（閉じる・別の設計書を開く・ページを離れるときに確かめる）
    - チェックを外すときは、保存したものを残すか消すかを確かめます（件数を出す）。残したものは、最初の画面から開く・消すことができます
    - ページは常に何も開いていない状態で始まり、最初の画面の一覧で「開く」を押したときだけ開きます
    - 同じ設計書を 2 つのタブで開いて編集すると、最後に保存したほうが残ります。別のタブがこの設計書（ファイルか、レビューの記録）を自動保存すると、このタブの上に知らせを出します（`storage` イベント、#50）。「別のタブの版を開く」か「このタブの版を残す」を選ぶまで、知らせは残ります。このタブで続けて保存すると、別のタブの版を上書きします
  - **ファイルを足す**：開いているファイルと同じ名前のファイルを足すときは、「置き換える」「両方残す（足すほうの名前を変える。`hops.2.yaml` のような名前は検査の対象外、`claim_request_x_2.md` は対象）」「やめる」を確かめます
- **キーボード**：Tab で移動、Enter で押します。エディターの中の Tab は、インデントせずに次へ移ります（インデントは空白で入れるか、行を選んで `Ctrl+]`・`Ctrl+[`）。ファイルのタブは `←`・`→`・`Home`・`End` で移ります（`role="tablist"`・`aria-controls`。指摘の件数は「エラー 1 件」のように読み上げる）。`Ctrl+Shift+M` で指摘の一覧、`F8` で次の指摘。長い行は折り返して表示します
- **折り畳み**：節（採否ごと）・クレーム・列のまとまり（`templates/registry/README.md` の 3.1 の見出し）ごとに開閉でき、開閉の状態は URL（`?fold=`）に残ります。名前は位置ではなく見出しと ID で付けます（`sec~採用`・`claim~C-iss`・`claim~C-iss~grp~定義`・`grp~定義`。`~` は ID に現れない）。列のまとまりの順が変わっても、共有した URL の意味は変わりません
- **レビューのための仕組み**（#50 の前提）
  - 行の固定の名前（アンカー）：台帳の行・トークン種別・ホップ・カタログのイベント・発行方式の項目は `<種類>:<ID>`（例 `claims:C-iss`・`catalog_answers:I25`・`issuance_profile:client_type`）。同じ種類で ID が 2 行以上にあると、その ID にはアンカーを付けず、エディターの指摘（規則 `ANCHOR`、warn）に出します。#50 は、アンカーの無い行にはレビューの記録を付けません
  - 行の内容のハッシュ：`ClaimsEditor.rowHash(anchor)` は、行の値の RFC 8785（JSON Canonicalization Scheme）の文字列を UTF-8 にした SHA-256 です。キーの順・引用符・空白・コメントを変えても変わりません。同じ計算を Python でする `python tools/row_hash.py <設計書のディレクトリ> [--format json]` があり、シナリオ A・B の全アンカーで一致することをテストで確かめています（`research/claims-editor/row-hash-parity.json`）
  - 値の読み方：ブラウザも、claim_lint（PyYAML、YAML 1.1）と同じ規則で読みます。`yaml` の YAML 1.1 の型の判定を、PyYAML の resolver の正規表現に置き換えています。どちらも日付を文字列のままにし、重複したキーを誤りにします。そのため、エディター・claim_lint・`tools/row_hash.py` で値もハッシュも一致します（境目の値の一致はテストで確かめている）
  - 引用符の無い値で、YAML の読み手によって意味が変わるものには、エディターが規則 `YAML11` の warn を出します。claim_lint の読み方では次のとおりで、YAML 1.2 の読み手とは違います。意味どおりに読ませるには引用符で囲んでください（記入例にはありません）
    - `y`・`n`：文字列（ほかの YAML 1.1 の読み手では真偽値）
    - `yes`・`no`・`on`・`off`（大文字を含む）：真偽値（YAML 1.2 では文字列）
    - 符号の無い指数（`1e3`・`1.0e3`）：文字列（YAML 1.2 では数）。`1.0e+3` は数
    - `012`：8 進数で 10。`09`：文字列
    - `10:30`：60 進数で 630
    - `0b101`・`1_000`：数（YAML 1.2 では文字列）
    - マージキー `<<`：claim_lint の読み方では YAML の誤り（エディターは展開するが、`YAML11` の error を出す）
    - `=`：claim_lint の読み方では YAML の誤り（`tag:yaml.org,2002:value` を作れない。エディターは文字列として読むが、`YAML11` の error を出す。#50）
    - 流れの形の中の `:` で始まる値（`[:1]`・`{:1}`）：claim_lint の読み方では YAML の誤り（エディターは文字列 `":1"` として読むが、`YAML11` の error を出す。#50）
    - キーにした `.inf`・`.nan`：claim_lint では数のキー。エディターと `tools/row_hash.py` は、どちらも `"Infinity"`・`"NaN"` の文字列のキーとしてハッシュを計算する（#50 で揃えた）。`YAML11` の warn を出す
  - 対になっていないサロゲート（`"\ud800"`）を含む行は、RFC 8785 が前提にする I-JSON にならないので、ハッシュを計算しません（エディターは `ANCHOR` の warn、`tools/row_hash.py` は `errors` に出して終了コード 1）
  - `ClaimsEditor.registerRowPanel(fn)` で、各画面の行と詳細の画面に、記録の表示を足せます
- **レビュー（#50。`docs/claims/review.js`）**：上のバーの「レビュー」に切り替えて使います（#53）。最初は 4 つの手順で始めます：1. レビュアーの名前と、人か LLM か（ここで「始める」を押せば記録できる）、2. 前の `review.yaml` を読み込むか新しく始めるか、3. 独立レビューにするか、4. チェックリストへ。レビュアーが設計書を確かめ、その記録を `review.yaml`（設計書と同じディレクトリ。スキーマは `templates/review/review.schema.json`）に書き出します。サーバーは使わず、外部にも送信しません（ネットワークの記録：`research/claims-editor/review-network-log.json`）
  - **レビュアーの名前は自己申告です。** エディターにはログインが無く、名前は誰でも書けます。本当の承認は GitHub の PR のレビュー（Approve）で行います。`review.yaml` はその PR に台帳と一緒にコミットし、Git の履歴を監査の記録にします
  - **観点のチェックリスト**：観点書（`templates/review/perspectives.md`）の 168 問を、スライド 148 の 6 段と役割（観点書の 7. の索引：発行者・受け手・攻撃者・運用・個人情報・クライアントの実装。索引に載る問いは 47 問だけです。残りの 121 問は「役割の索引が未整備の問い — どの役割にも関わりうる」として絞り込みます。役割で絞ると、索引に無い問いもその役割に関わりうることを画面に出します。全問に役割を付けるのは観点書の側の作業）で絞り込みます。問いは `python tools/build_claims_viewer.py` が観点書から `docs/claims/data/review.js` に書き出し、CI の `--check` が観点書との食い違いを見ます。問いごとに Yes／No／該当なし とメモを記録し、No の問いからそのまま指摘を作れます。「見る欄」を押すと、台帳の列（全部の行のその列）、設計書の節（`design.md` の同じ番号の見出し。開いていなければテンプレートの節）、25 問の回答（全部の `claim_request_*.md` のその問い）に移ります
  - **行ごとの判定**：台帳の行・トークン種別・ホップ・カタログへの回答・発行方式の項目ごとに、承認／修正を求める／保留 を、レビュアー・日時・コメントとともに記録します。判定は行の内容のハッシュ（`ClaimsEditor.rowHash`、`tools/row_hash.py` と同じ）に結びつき、行を変えると、すべての画面で「⟳ 再確認が要る」になります（コメントやキーの順だけの変更では変わらない）。今の台帳に無い行の記録は、消さずに「台帳に無い行」として示します。判定の印には、いつもレビュアーの名前を付け、LLM の判定には「LLM、人による点検は未実施」と書きます
    - **ハッシュが見るのは、その行の値だけです。** 参照するトークン種別・ホップの行、25 問の回答（`claim_request_*.md`）、design.md の本文を変えても、判定は「再確認が要る」になりません。行の詳細の画面に「依存する行」（載るトークン種別・運ぶホップ・25 問の回答）を出すので、それらを変えたときは、自分で見直します
  - **指摘**：`templates/review/report_template.md` の欄（ID・場所・内容・重大度・出どころ・種別・判定・対応）で記録します。種別が「目的と仕組みの不一致」なら、取り違えた問いが要ります。専門家に回す基準（escalation.md の 9 つ）と、カタログ・観点書に戻す事項も記録します
  - **分析**：観点の網羅（段 × 役割ごとに、答えた問いと問いの数）、lint とレビューの重ね合わせ（lint の error があるのに承認した行などを上に出す）、前の版との差分（前の版のファイル・フォルダか、前の `review.yaml` を読み、行のハッシュを比べて変わった行を出す。「行ごとの判定」で変わった行だけに絞れる）、対比表と判断の木への案内、25 問の回答の一覧、却下の理由の抜き取り（乱数の種を記録し、sha256(種:行) の順で 2〜3 行。同じ種なら `python tools/review_record.py sample` と同じ行）
    - 前の版との差分と claim_lint の diff（L10）の関係：L10 は、変更が受け手を壊すか（削除・型の変更など）を規則で確かめます。レビューの差分は、壊すかどうかにかかわらず、内容が変わった行を全部出します（`python tools/review_record.py diff <前の版> <dir>` と同じ）。L10 が通っても、変わった行は再レビューの対象です
  - **独立レビュー**：設定すると、提出するまで、ほかのレビュアーの記録（回答・判定・指摘）を画面で隠します（`templates/review/procedure.md`）
    - **画面で隠すだけです。** review.yaml を開けば誰でも読めます（「zip で書き出す」の zip にも全員の記録が入る。消すと記録が失われるため）。エディターがするのは次のことだけです。守ったかどうかは、名前と同じく自己申告です
    - 提出の前に、隠すのをやめる操作（記録にある別のレビュアーへの切り替え、既にある名前を打つこと、設定を外すこと、「review.yaml を書き出す（全員の記録）」）は、ダイアログで確かめます。それでも行うと、`independence: {mode: broken, broken_at, reason}` を review.yaml に記録します
    - ほかのレビュアーの記録を初めて画面に出した日時（`viewed_others_at`）を記録し、その後に直した回答・判定・指摘には `edited_after_viewing_others: true` を付けます。レポートの 1. に、外れたこと・見た日時・その後に直した件数・提出の後の更新を出します
  - **記録の保存**：「review.yaml を書き出す」（全員の記録）、「自分の記録だけ書き出す」、「review.yaml を読み込む」（複数を選ぶと合わせて表示。同じレビュアーで中身が違う記録は、両方残す・置き換える・今のを残す、を確かめる）。フォルダを開いたときは、同じディレクトリの `review.yaml` も読みます。「zip で書き出す」にも `review.yaml` が入ります。書き出していない記録は、設計書のファイルと同じように、閉じる・別の設計書を開く・ページを離れるときに確かめ、自動保存が有効ならこのブラウザにも保存します（`claims-editor:review:v1:<ディレクトリ>`）。書き出す形は 1 つに決めてあり（キーの順・引用符）、読み込んで書き出すと同じバイトになります
  - **観点のチェックリストの既定の表示**（#56）：既定では、開いている設計書の性質（委任がある・発行者が複数ある・個人情報を載せる など。台帳から読む）に当たる、人の判断が要る問いのうち優先 1 のものと「開いた問い」だけを出します（`templates/review/short_list.md` と同じ選び方。問いは 1 文。既定は優先 1 の 10〜18 問と開いた問い 3 つで、優先 2 は「時間があれば」。筆者の提案で、人では測っていない）。性質は、台帳が示すか書き手が宣言していれば当たり、読めない性質は問いを出す。機械（lint）が確かめる問い・書き手が提出前に確かめる問い・専門家に回す問いは、「表示する問い」で開けます。振り分けは `templates/review/triage.yaml`、根拠と測定は `research/template-design/triage-evidence.md`
  - **レポート**：記録から `report_template.md` の形の Markdown を作ります（レビュアーごと）。`python tools/review_record.py report` が同じものを作り、`python tools/review_check.py --report <ファイル>` が様式（節・表の見出し・語彙・取り違えた問い）を確かめます
  - **記入例**：「サンプルを開く：シナリオ B」で、`templates/examples/scenario-b/review.yaml`（今の版を LLM のセッション 1 つが全 168 問でレビューした記録。人による点検は未実施）が開きます。CI は、`review.yaml` をスキーマと今の台帳で確かめ（`python tools/review_record.py check --annotate`。行が変わった承認は stale として一覧に出し、PR の画面に `::warning` の注記を出す。既定では止めない。`--fail-on-stale` で止める）、生成したレポート（`review-report-2026-11-23.md`）が `review.yaml` から作れるものと一致するかを確かめます。シナリオ B を変える PR の手順は `templates/CONTRIBUTING.md` の「レビューの記録がある設計書を変えるとき」にあります
    - レポートの値は、すべて Markdown のための処理をします（`&`・`<`・`>` は実体参照、`` ` ``・`*`・`_`・`[`・`]`・`~`・`\` はバックスラッシュ、`|` は全角、行の頭の `#`・`>` も文字のまま）。メモに `<!--` と書いても、後ろの節（7. の「人による点検は未実施」など）は隠れません。使った教材の版は、review.yaml に記録した版（`materials`。無ければ 1 行目の `template_version`）を書き、今の教材と違えば両方を出します
    - レビューの記録の自動保存に失敗したときは、設計書と同じく画面の上に警告を出し続け、記録は書き出していないものとして扱います。自動保存した記録がある設計書を開いたときの確かめで Esc を押す（「あとで決める」）と、自動保存した記録は残したまま、レビューの記録の自動保存を止めます（上書きしない）
    - シナリオ B のレビューに渡した指示文は `research/reviews/scenario-b-editor-review-prompt-2026-11-23.md` にあります。「前のレビューを読んでいない」は自己申告で、24 件のうち約 11 件は主題が前のレビュー（`review-report.md`）と重なります（PR #52 の独立点検）。その約 11 件は、独立に見つかった証拠には数えません
  - ブラウザのテスト（`tools/tests/test_claims_review_ui.py`、Playwright。CI では動かず、ローカルで実行）：168 問の絞り込みと見る欄、行の変更での判定の無効化、`review.yaml` の往復と 2 人分の表示、分析、シナリオ B のレポート、独立レビュー、外部に送らないこと、記録を黙って消さないこと、別のタブの知らせ
- **外部に送信しない**：CSP（`<meta>`）は `default-src 'none'` を基本に、`connect-src 'self'`（Pyodide がこのサイトの `vendor/pyodide/` と `data/claim_lint.zip` を GET するため）、`script-src 'self' 'wasm-unsafe-eval'`（WebAssembly のコンパイルを許すだけで、JavaScript の `eval` は許さない。外すと Pyodide が起動しないことをテストで確かめた）、`worker-src blob:`（claim_lint の worker を blob: から起動し、このページの CSP を引き継がせる。GitHub Pages は CSP のヘッダーを付けられないので、URL から起動した worker には CSP が効かない）、`style-src 'self'`（エディターは shadow root の中に置き、CodeMirror のスタイルを constructed stylesheet で当てる）です。外部の CDN は使いません
  - 確かめ方（`research/claims-editor/network-log.json`）：
    - Playwright（Chromium）のネットワークの記録で、サンプル B を開く・claim_lint を読み込んで検査する・編集して再検査する・自動保存を有効にする・zip で書き出す・各画面を見る、の間の全リクエスト（ページと worker）が、同じオリジンへの GET だけであること
    - 別のポートに、来たリクエストをすべて記録する「受け手」のサーバーを立て、ページから `fetch`（POST）・`sendBeacon`・WebSocket・`<img>`・フォームの POST を、blob: の worker から `fetch`（POST）を試みても、受け手に届いたリクエストが 0 件であること。CSP の違反（`connect-src`・`img-src`・`form-action`）がそれぞれ記録されること
  - meta の CSP では `frame-ancestors` を指定できないので、ほかのサイトの枠の中に表示されることは防げません（クリックジャッキング）。このページには送信や認証の操作が無いので、影響は小さいと判断しています
- **同梱したライブラリ**：版・ライセンス・sha256 は `docs/claims/vendor/MANIFEST.json`（`python tools/build_claims_viewer.py` が生成し、CI が食い違いを検出）。エディターのライブラリは `tools/claims_editor_vendor/`（`package-lock.json` で版を固定。`npm ci --ignore-scripts && node build.mjs` で `vendor/editor-libs.js` を作る）。Pyodide はリリースの `pyodide-core-314.0.8.tar.bz2`（sha256 `ff3e5f9d…62ca37`）から必要なファイルだけを置き、wheel は `pyodide-lock.json` の sha256 と一致するものを置いています。既知の脆弱性の確認（2026-11-23。OSV・npm audit・GitHub の advisory）は `tools/claims_editor_vendor/advisories.json` に記録しています。同梱したファイルは Dependabot の対象にならないので、版を上げるときは同じ確認をやり直します
- **初回の読み込みの大きさと時間**（2026-11-23、ローカルの HTTP サーバーと headless Chromium、キャッシュなしで測定。gzip は各ファイルを gzip -6 で圧縮した大きさで、GitHub Pages が圧縮して送るときの目安。`research/claims-editor/load-measurements.json`）

  | 場面 | リクエスト | 大きさ | gzip の目安 | 時間 |
  | --- | --- | --- | --- | --- |
  | 最初の画面（何も開いていない） | 8 | 896 KB | 270 KB | 0.18 秒 |
  | サンプル B を開く | 1 | 498 KB | 105 KB | 0.26 秒 |
  | claim_lint を初めて使う（Pyodide と wheel と claim_lint.zip） | 16 | 14.7 MB | 7.1 MB | 6.2 秒（Pyodide の起動 2.2 秒、最初の検査 3.8 秒） |
  | 編集の後の検査（シナリオ B） | 0 | — | — | 3.4 秒（worker の中なので、その間も編集できる） |

  ネットワーク越しでは、claim_lint の初回は回線の速さに応じて長くなります（7 MB を送る時間が加わる）。2 回目以降はブラウザのキャッシュが効きます
- `file://` で開いた場合も、編集・YAML と Schema の検査・プレビュー・書き出しは動きます。claim_lint は HTTP で開いたときだけ動きます（画面に表示します）
- **リポジトリの大きさ**：同梱した Pyodide とライブラリは、git の中で約 12 MB です（`pyodide.asm.wasm` 9.6 MB・`python_stdlib.zip` 2.5 MB など）。clone のたびに履歴として残り、Pyodide の版を上げるたびに同じくらい増えます。`data/claim_lint.zip`（約 0.7 MB）は、claim_lint・台帳のスキーマ・カタログを変えたときだけ変わります（並びと日時を固定し、圧縮しないので、入力が同じなら同じバイト列になる）。増え方が問題になったら、Pyodide を Git LFS か GitHub のリリースの資産に移します（どちらも GitHub Pages から同じオリジンで配る方法を先に確かめる）
- データ（`docs/claims/data/*`）は YAML などから生成します。台帳・記入例・`templates/registry/README.md` の列の見出し・レビュー教材・対応表・claim_lint を変えたら、作り直してコミットします。食い違いは CI（`.github/workflows/claims.yml`）で落ちます

## ビルドとテスト

リポジトリのルートで実行します。

```bash
python tools/build_claims_viewer.py           # docs/claims/data/ と vendor/MANIFEST.json を書く
python tools/build_claims_viewer.py --check   # 食い違えば終了コード 1
python -m pytest -q tools/tests/test_build_claims_viewer.py
python -m pytest -q tools/tests/test_claims_editor_ui.py   # Playwright（pip install playwright && python -m playwright install chromium）。CI では飛ばす
CLAIMS_EDITOR_EVIDENCE=research/claims-editor python -m pytest -q tools/tests/test_claims_editor_ui.py   # 証跡（画面・ネットワークの記録・CLI との一致・読み込みの測定）も保存する
```
