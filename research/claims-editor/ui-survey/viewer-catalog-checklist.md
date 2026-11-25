# ビューアー・エディター・カタログ・チェックリストの UI 調査と提案

調査日: 2026-11-25。対象は「JWT クレーム設計書（YAML）のエディター兼ビューアー兼レビュー道具」（静的ページ、ブラウザ内だけで動く）。

## 0. この文書の読み方

- 事実には出典 URL を付けた。公式の文書・公式リポジトリ・公式デモの文面で確かめたものだけを事実として書いた。
- 公式の文面で確かめられなかったものは **未確認** と書いた。画面の見た目（スクリーンショットの中身）は今回の取得方法では読めないので、文書の本文に書かれていることだけを根拠にした。
- Collibra と Atlan は調べていない（公開文書だけで足りるか確かめる前に時間を他へ回した）。提案はこの 2 つに依存しない。
- 第 5 章が提案。第 1〜4 章はその根拠。

---

## 1. A: 仕様書のエディター／ビューアー

### 1.1 Swagger Editor（旧 v4 と新 v5）

| 項目 | 分かったこと | 出典 |
|---|---|---|
| 位置づけ | ブラウザで OpenAPI を JSON／YAML で編集し、文書を「リアルタイムにプレビュー」する道具。v4 は非推奨、OpenAPI 3.1 は v5 だけ | https://github.com/swagger-api/swagger-editor |
| 売り文句 | 書きながら構文を検査して「簡潔なフィードバックとエラー処理」を返す／定義しながら見た目を描画する／補完 | https://swagger.io/tools/swagger-editor/ |
| v5 の作り | Monaco エディター + プレビュー用プラグイン（OpenAPI は Swagger UI、AsyncAPI なども）。起動時に開く定義を設定（`REACT_APP_DEFINITION_FILE`／`REACT_APP_DEFINITION_URL`）で渡せる | https://swagger.io/docs/open-source-tools/swagger-editor/ |
| 左にエディター、右にプレビューの 2 分割 | **未確認**（公式文書の本文には配置の記述が無かった。デモ https://editor.swagger.io/ で見られるはず） | — |
| 初回に Petstore のサンプルが開く、誤りの一覧から行へ飛べる | **未確認**（同上） | — |

### 1.2 Swagger UI（ビューアー）

設定の文書から、読む人を圧倒しないための既定値が読み取れる。

| 設定 | 内容 | 出典 |
|---|---|---|
| `docExpansion` | 操作とタグの最初の開き具合（`list`／`full`／`none`） | https://swagger.io/docs/open-source-tools/swagger-ui/usage/configuration/ |
| `filter` | 上部に絞り込みの入力欄を出す | 同上 |
| `deepLinking` | タグ・操作ごとの URL（深いリンク） | 同上 |
| `defaultModelsExpandDepth` | モデルを最初に何段開くか（既定 1、-1 で隠す） | 同上 |
| `url`／`urls` | 開く定義を URL で渡す。複数ならトップバーで切り替え | 同上 |

学べること: **最初は畳む。開く深さに既定値を持つ。絞り込みの欄を上に置く。項目ごとに URL を持つ。**

### 1.3 Redoc（ビューアー）

| 項目 | 分かったこと | 出典 |
|---|---|---|
| 配置 | 既定で 3 パネル（左: 検索とナビ、中央: 本文、右: リクエスト／レスポンスの例）。レスポンシブ | https://github.com/Redocly/redoc |
| ナビ | メニューとスクロール位置の同期。`x-tagGroups` でサイドメニューを上位グループに束ねる | 同上 |
| 静的な出力 | `npx @redocly/cli build-docs openapi.yaml` で 1 枚の `redoc-static.html` を作れる | 同上 |
| 開き具合の設定 | `schemas-expansion-level`、`json-samples-expand-level`、`sort-required-props-first`、`max-displayed-enum-values` など | https://redocly.com/docs/redoc/config |

学べること: **左に目次、中央に本文、右に「例」。必須の項目を先に並べる。長い列挙は件数で打ち切る。**

### 1.4 Stoplight Elements／Studio と Spectral

| 項目 | 分かったこと | 出典 |
|---|---|---|
| Elements の配置 | `layout="sidebar"` の例。3 列（Stripe 風）と、既存サイトへ埋め込みやすい縦積み（stacked）の 2 系統。ルーターは `history`／`hash` の例 | https://github.com/stoplightio/elements |
| Spectral の結果 1 件の形 | `code`（規則名）・`path`（YAML 内の場所の配列）・`message`・`severity`・`range`（開始と終了の行と桁、0 始まり）・`source`（ファイル） | https://github.com/stoplightio/spectral/blob/develop/docs/guides/2-cli.md |
| 重大度 | 高い順に error／warn／info／hint。既定では error だけが失敗扱い。`--display-only-failures` で失敗扱いの重大度以上だけに絞れる | 同上 |
| Studio の画面 | Stoplight の公式ブログに「エディターで書いている間に Spectral の警告とエラーが見える」「problems tab」という言い回しがある | https://blog.stoplight.io/powering-api-governance-with-spectral-part-two 、https://blog.stoplight.io/linting-the-stoplight-docs-with-vale |
| Studio の問題パネルの細部（件数の並び、クリックで行へ） | **未確認**（公式文書のページを取得できなかった） | — |

学べること: **指摘 1 件は「規則名・場所（パス）・行・重大度・文面」の 5 点で持つ。重大度は 4 段、既定で止めるのは error だけ。**

### 1.5 AsyncAPI Studio

公式デモの初回画面に出る案内文そのものが、初回画面の手本になる。

| 項目 | 分かったこと | 出典 |
|---|---|---|
| 初回 | サンプル（街灯の API）が開いた状態で始まり、「Welcome to the AsyncAPI Studio!」の案内が出る。案内は「URL から読み込むにはメニューの Import from URL」「誤りはエディターの下のパネルに出る」「左のナビの 4 つめでデータの流れ」「5 つめでサンプルのテンプレートを選ぶ」「設定は左下」と、**場所と操作を 1 行ずつ**で教える | https://studio.asyncapi.com/?redirectedFrom=playground |
| 読み込み | メニューから、または `?url=` を付けるだけで遠隔の文書が開く。ローカルのフォルダを開くとサイドバーにファイルの木が出て、保存は元のファイルへ戻る（Chrome／Edge／Brave。Firefox と Safari は非対応）。フォルダの許可はセッションごと | https://www.asyncapi.com/blog/asyncapi-studio-from-single-file-to-real-world-usage 、https://github.com/asyncapi/studio |
| 検査 | 開いている全ファイルを通したリアルタイム検査。診断は「Problems タブ」に集まる | https://github.com/asyncapi/studio 、https://github.com/asyncapi/studio/issues/1319 |
| 読むだけの表示 | `readOnly=true` でエディターを隠す使い方がある（隠れない不具合の報告あり） | https://github.com/asyncapi/cli/issues/1627 |

学べること: **空の画面で始めない（サンプルを開いて始める）。誤りはエディターの下の 1 か所に集める。読むだけの入口を別に持つ。**

### 1.6 VS Code の「問題」パネル（多くの道具が手本にしている形）

| 項目 | 分かったこと | 出典 |
|---|---|---|
| 件数の要約 | ステータスバーにエラーと警告の合計を常に出す | https://code.visualstudio.com/docs/editing/editingevolved |
| 一覧 | 要約をクリックすると PROBLEMS パネルが開き、今ある誤りを全部並べる | 同上 |
| 本文側 | 誤りは本文の中にも描かれ、スクロールバー脇の概観にも印が出る | 同上 |
| 順送り | F8 系のキーで次／前の誤りへ進み、その場に詳細と直し方の候補が出る | 同上 |

---

## 2. B: データカタログ／ガバナンスの道具

### 2.1 OpenMetadata

| 項目 | 分かったこと | 出典 |
|---|---|---|
| 資産ページの上段 | 「Source・Owner・Tier・Type・Usage・Description」を上のパネルに出す。右上にフォロー（星）など | https://docs.open-metadata.org/latest/how-to-guides/data-discovery/details |
| タブ | Schema／Activity Feeds & Tasks／Sample Data／Queries／Data Observability／Lineage／Custom Properties ほか。**資産の種類によって出るタブが変わる**（Schema は表・トピック・コンテナだけ、など） | 同上 |
| Schema タブ | 列ごとに「列名・型・説明・タグ・用語集の語」を 1 行で見せる | https://docs.open-metadata.org/latest/how-to-guides/guide-for-data-users/data-asset-tabs |
| 追加の属性 | 標準に無い属性は「Custom Properties」タブへ分ける | 同上 |
| 重要度 | Tier 1〜5。「重要度で決める」。まず Tier 1 と Tier 5 から付けるよう勧めている | https://docs.open-metadata.org/latest/how-to-guides/data-governance/classification/tiers |
| 承認 | 用語集の語は、レビュアーがいると Draft で始まり、レビュアーにタスクが付き、Approve／Reject で Approved／Rejected になる。Review タブに Open と Closed の 2 つの絞り込み。レビュアーがいなければ最初から Approved | https://docs.open-metadata.org/latest/how-to-guides/data-governance/glossary/approval |
| ダッシュボードの指標 | 「説明のある資産の割合」「所有者のいる資産の割合」「Tier 別の資産数」「全体の健康状態の一覧」 | https://docs.open-metadata.org/latest/how-to-guides/data-insights/report |
| ホーム | 役割（ペルソナ）ごとにパネルを足し引きできる（最近見たもの、お知らせ、タスク、KPI） | https://docs.open-metadata.org/latest/how-to-guides/admin-guide/persona-landing-page-customization |

### 2.2 DataHub

| 項目 | 分かったこと | 出典 |
|---|---|---|
| 追加の属性の見せ場所 | 構造化プロパティごとに「資産のバッジ／サイドバー／列の表」のどこに出すか選べる。隠すこともできる。検索の絞り込みに出すかも選べる | https://docs.datahub.com/docs/features/feature-guides/properties/overview |
| サイドバーの並び | 「いちばん使われる文書と系譜を上へ、状態と共有を下へ」並べ替えた。タブ名に件数（プロパティ数・列数・インシデント数）を付けた。列の表からメモのアイコンを消して列のサイドバーだけに出した | https://docs.datahub.com/docs/managed-datahub/release-notes/v_0_3_7 |
| 列（フィールド）が持つもの | 型などの情報・文書・タグ・用語集の語・構造化プロパティ・非推奨・フォーム・状態 | https://docs.datahub.com/docs/generated/metamodel/entities/schemafield |
| 要約タブ | 上にプロパティの見出し、次に「About」（説明とリンク）、その下にモジュール。見出しに出すプロパティは選べる（選ぶ機能は Cloud 版だけ） | https://docs.datahub.com/docs/features/feature-guides/custom-asset-summaries |
| ホーム | 既定のモジュールは「自分の資産」「購読」「ドメイン」。追加で「リンク」「コレクション」「文書」「階層」。お知らせはいちばん上 | https://docs.datahub.com/docs/features/feature-guides/custom-home-page |
| フォーム（点検の依頼） | 「対象の資産」「質問」「担当者」の 3 つで作る。種類は 2 つ: 完了型（必須の質問に全部答えたら完了）と検証型（全部答えたうえで担当者がはっきり「verified」と押して完了）。資産は、割り当てられた全フォームの必須の質問が済んで初めて Documented／Verified になる。進み具合は分析に出る | https://docs.datahub.com/docs/features/feature-guides/compliance-forms/overview 、https://docs.datahub.com/docs/features/feature-guides/compliance-forms/create-a-form 、https://docs.datahub.com/docs/generated/metamodel/entities/form |
| 提案と承認 | タグ・用語・所有者・説明は「提案」でき、提案中の状態で表示され、レビュアーの受信箱で承認か却下。履歴が残る（Cloud 版） | https://docs.datahub.com/docs/managed-datahub/change-proposals |
| データセットのページのタブ名の一覧（Columns／Documentation／Lineage／Properties など） | **未確認**（公式文書に一覧の記述を見つけられなかった。上のリリースノートから「Properties タブ」「Columns の表」「列のサイドバー」があることまでは確か） | — |

### 2.3 Backstage（ソフトウェアカタログと TechDocs）

| 項目 | 分かったこと | 出典 |
|---|---|---|
| 一覧 | 既定で「自分のチームが持つもの」を見せ、All に切り替えられる。星を付けられる。行内検索と列の絞り込み | https://backstage.io/docs/features/software-catalog/ |
| 絞り込み | kind／type／owner／lifecycle／tag／namespace／処理状態。最初に選ばれている絞り込みを設定できる（既定は owned） | https://backstage.io/docs/features/software-catalog/catalog-customization |
| 1 件が必ず持つもの | name、title（表示名）、description（短い要約）、tags、links。Component は type・lifecycle・owner が必須 | https://backstage.io/docs/features/software-catalog/descriptor-format |
| ライフサイクル | experimental／production／deprecated の 3 値 | 同上 |
| ページのタブ | タブをグループに束ねられる。**対象の種類に合うものだけ出す**条件を書ける | https://backstage.io/docs/features/software-catalog/catalog-customization |
| TechDocs | 文書はコードの隣に Markdown で置き、カタログのその部品のページからたどれる。検索できる | https://backstage.io/docs/features/techdocs/ |
| 既定のタブ名（Overview／CI/CD／API／Docs）と About カードの項目 | **未確認**（公式デモはスクリプト描画で本文を取得できなかった） | — |

### 2.4 3 つに共通する形（確かめた範囲で）

1. **上段に 5〜6 個だけ**出す（何か・誰の物か・重要度・種類・状態・短い説明）。
2. その下を**タブ**に分け、**対象の種類に合わないタブは出さない**。
3. 標準から外れる属性は**「追加の属性」タブ**へ逃がし、見せ場所を属性ごとに決める。
4. 一覧の 1 行は**名前・型・説明・タグ**まで。残りは行を開いた先（サイドバー）。
5. ホームは**「自分に関係するもの」「未済のタスク」「埋まり具合の割合」**。
6. 承認は**状態の語を 3〜4 個に絞る**（Draft／In Review／Approved／Rejected）。

---

## 3. C: セキュリティのレビュー／チェックリストの道具

### 3.1 OWASP Threat Dragon

| 項目 | 分かったこと | 出典 |
|---|---|---|
| 最初の画面 | Welcome に 3 つの入口: 「新しいモデルを作る」「既存のモデルを開く」「サンプルを見てみる」 | https://www.threatdragon.com/docs/usage/getting-started.html |
| 状態 | N/A、Open、または処置の結果（Mitigated／Accepted／Transferred／Avoided／Eliminated）。Open は「まだ処置の判断が要る」 | https://www.threatdragon.com/docs/usage/threats.html |
| 重大度 | TBD／Low／Medium／High／Critical | 同上 |
| 絞り込み方 | 「種類から足す」は部品の種類に合う脅威を 1 件ずつ見せ、Apply／Previous／Next で採否を決める。「文脈から足す」は**部品に付けた性質**（データの流れ: プロトコル・暗号化・公衆網。データ置き場: 資格情報を持つ・ログである・暗号化・署名。プロセス: 権限・カード決済）から脅威を出す。性質が無ければ一般的な 1 件 | 同上 |
| 対象外 | 対象外にした部品には脅威を足せない（ボタンが無効） | 同上 |
| 報告書の選択肢と件数の表 | **未確認**（文書のページが 401 で取得できなかった） | — |

### 3.2 Microsoft Threat Modeling Tool

| 項目 | 分かったこと | 出典 |
|---|---|---|
| 最初の画面 | 「Create A Model」「Open A Model（最近開いたものの一覧つき）」「テンプレートの選択」「Getting Started Guide」 | https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-getting-started |
| 開いた後の画面 | モデルを開くか作ると **Design ビュー**が開く。虫眼鏡で **Analysis ビュー**（生成された脅威の一覧）へ切り替える | https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-feature-overview |
| 一覧と図の行き来 | 脅威を選ぶと、図の中の該当する線が強調され、右に脅威の詳細が出る。**既読の印**で見たものを追える | 同上 |
| 状態 | Not Started（既定）／Needs Investigation／Not Applicable／Mitigated。理由（justification）の欄がある | https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-getting-started |
| 対象外 | 部品を対象外にすると脅威の生成から外れる。**理由の欄が対になっている** | https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-feature-overview |
| メッセージ | 線がつながっていない等の不備は Messages の欄に出る。無視もできる | 同上 |
| 報告 | Reports → Create Full Report で HTML。要約・図・脅威の一覧 | 同上 |

### 3.3 OWASP SecurityRAT

| 項目 | 分かったこと | 出典 |
|---|---|---|
| 流れ | (1) これから作る物の性質を伝える → (2) 満たすべき要件が出る → (3) 要件ごとに扱いを決める → (4) 状態を課題管理に残す | https://wiki.owasp.org/index.php/OWASP_SecurityRAT_Project |
| 絞り込みの入力 | ASVS の章（空なら全部）・検証レベル（L1〜L3）・SSO を使うか、の 3 つ | https://devguide.owasp.org/en/03-requirements/04-security-rat/ |
| 要件ごとの記録 | 「実装するか」と「コメント（実装しないならその理由）」 | https://securityrat.github.io/ |
| 持ち運び | 要件の集合を **YAML ファイル**として JIRA のチケットに添付して残し、後で読み込み直す | 同上 |
| 画面の列の構成 | **未確認** | — |

### 3.4 OWASP ASVS

| 項目 | 分かったこと | 出典 |
|---|---|---|
| 規模 | 17 章で約 350 要件 | https://github.com/OWASP/ASVS/blob/master/5.0/en/0x02-Preface.md |
| 段階 | L1 は「ASVS を採り入れる最初の一歩」。L2 は標準的な実践の広い土台。L3 は高い保証 | 同上 |
| 段階ごとの要件数、適用外の扱いの文面 | **未確認**（該当ページを取得できなかった） | — |

### 3.5 IriusRisk

| 項目 | 分かったこと | 出典 |
|---|---|---|
| 枠組み | 文書全体が 4 つの問いで章立てされている（何を作るか／何がまずくなりうるか／どうするか／うまくやれたか） | https://www.iriusrisk.com/documentation/the-four-question-framework-for-threat-modeling |
| 絞り込み | 規則エンジンが図・データの流れ・信頼ゾーンから脅威と対策を出す。条件に「質問がある（プロジェクトと部品の文脈）」、動作に「対策を実装済みにする」「知らせる」。質問票の作成画面では**質問ごとに表示条件**を付けられる | https://www.iriusrisk.com/documentation/rules 、https://www.iriusrisk.com/documentation/security-content |
| 未回答の扱い | 「未回答の質問票を見つけて精度を上げる」という項目が文書にある（見出しだけ確認） | https://www.iriusrisk.com/documentation/the-four-question-framework-for-threat-modeling |
| 状態 | 対策は Recommended／Required／Implemented／Rejected／Not Applicable。**Not Applicable と Rejected は理由を書かないと反映されない** | https://www.iriusrisk.com/documentation/countermeasures |
| ダッシュボード | プロジェクトのホームに「脅威のリスク分布」「対策の状態」「テスト結果」。左上に総合点と件数。評価が進むと動く | https://www.iriusrisk.com/documentation/assessing-threats-in-iriusrisk |
| 報告 | 未対応／対応済み／受容の束で並べる。PDF・XLSX・HTML・CSV | https://www.iriusrisk.com/documentation/did-we-do-a-good-job |

### 3.6 5 つに共通する形

1. **先に「作る物の性質」を数問だけ聞く**（SecurityRAT は 3 つ、Threat Dragon は部品の性質、IriusRisk は質問票）。その答えで一覧を作る。全部の一覧を最初に見せる道具は無い。
2. 状態の語は **4〜5 個**で、「未着手」が既定。
3. **「対象外」と「却下」には理由が必須**（IriusRisk、Microsoft TMT）。
4. 一覧の 1 件を選ぶと**設計の該当箇所が強調される**（Microsoft TMT）。
5. 結果は**ファイルで持ち運ぶ**（SecurityRAT の YAML、Threat Dragon のモデルファイル）。
6. 機械が見つけた不備（Messages）と、人が判断する項目（脅威の一覧）は**別の欄**。

---

## 4. いまの画面の言葉（リポジトリから拾ったもの）

`E:\Github\jwt-claims-guide\docs\claims\` の `index.html`・`editor.js`・`preview.js`・`review.js` の文言から拾った。内輪の言葉と見えるもの:

「台帳」「台帳に無い行」「載るトークン」「出どころ」「ホップ」「ホップの表」「カタログへの回答」「25 問の回答」「追加前の 25 問の回答」「観点」「観点書」「観点の網羅」「行の種類（縮小 Lite）」「回した先」「寿命の 4 つの層」「対比表と判断の木」「却下の理由の抜き取り」「lint と指摘の重ね合わせ」「レビュー（#50）」「正本は YAML です」「そのほかの生成した表」。

---

## 5. 提案

前提: 静的ページのまま。サーバーも保存先も足さない。いまある部品（YAML の読み込み、検査のワーカー、プレビュー、レビューの記録、zip の書き出し、ブラウザ内の自動保存）を並べ替える。

### 5.1 最初の画面と、開いたファイルによる行き先

**何も開いていないとき**（Threat Dragon と Microsoft TMT の Welcome、AsyncAPI Studio の「サンプルで始まる」に倣う）

画面の中央に入口を 3 つだけ置く。

| 入口 | 動作 |
|---|---|
| 設計書を開く | フォルダかファイルを選ぶ／ここへ落とす／YAML を貼る |
| サンプルを見る | 同梱の例を開いた状態で「概要」へ。読むだけ |
| 新しく作る | テンプレートから空の設計書を作り、クレーム一覧へ |

その下に 1 行ずつ: 「前回の続き（自動保存: 日時）」があれば 4 つめの入口として出す。「開いたファイルはどこにも送りません」は 1 行だけ残す。作成方法・ライセンス・同梱ライブラリはフッターのリンクへ下げる。

**開いた後の行き先**（Microsoft TMT は開くと必ず同じビューへ行く。迷わせないのが要点）

| 開いた物 | 行き先 |
|---|---|
| 設計書のフォルダ／複数ファイル | **概要（ダッシュボード）** |
| クレームの一覧の YAML 1 枚 | クレーム一覧。上に「ほかのファイルが無いので概要は一部だけ」の帯 |
| トークン／経路の YAML 1 枚 | その一覧 |
| レビューの記録（review.yaml）だけ | 「この記録の対象の設計書を開いてください」+ 記録の要約だけ |
| 設計書 + レビューの記録 | 概要。「確認事項」の件数を上に出す |
| 壊れた YAML | エディター。誤りの行へカーソル、下の問題パネルを開く |
| 何のファイルか分からない | 種類を選ぶ小さな問い（いまの動作のまま） |

URL の `#` に今いる場所（例 `#/claims/C-012/security`）を持たせ、戻る・進むと再読み込みで同じ場所に戻れるようにする（Swagger UI の deepLinking、Elements の hash ルーター）。ファイルの中身は URL に入れない。

**全体の枠**

- 左: ナビ（概要／クレーム／トークン／経路／問題／確認事項／ファイル）。各項目に件数のバッジ（DataHub がタブ名に件数を付けたのと同じ）。
- 中央: 本文。右上に「見る｜編集」の切り替え。編集のときだけ YAML のエディターを左右分割で出す（いまの「左右の幅」はここだけに残す）。
- 下: 問題の件数（常時）。クリックで問題パネル。

### 5.2 概要（ダッシュボード）の中身

OpenMetadata の「埋まり具合の割合」、IriusRisk の「状態の分布」、DataHub の「自分に関係するもの」を合わせる。上から順に。

1. **見出し 1 行**: 設計書の名前・版・最終更新・ファイル数。
2. **数字のタイル 4 枚**（どれもクリックで絞り込んだ一覧へ）
   - クレーム: n 件（うち個人情報あり n、承認待ち n）
   - トークン: n 種類
   - 問題: エラー n／警告 n
   - 確認事項: 残り n／全 n
3. **次にやること**（上から 3 件まで。無ければ「やることはありません」）
   - 例: 「エラーが 2 件あります → 問題を開く」「所有者が未記入のクレームが 5 件 → 一覧を開く」「確認事項が 4 件残っています → 続ける」
4. **埋まり具合**（横棒 3 本）: 意味が書かれている割合／所有者がいる割合／保護の方針が書かれている割合。
5. **トークン × クレームの表**（どのクレームがどのトークンに入るか。小さな格子）。件数が多ければ分類ごとに畳む。
6. **経路の図**（発行元 → 中継 → 受け手を 1 本の帯で）。区間を押すと経路の一覧へ。
7. **最近の変更**（前の版との差分があるとき: 足された n／変わった n／消えた n）。

置かないもの: 生成した表の一覧、検査の規則の一覧、レビューの手順の説明。これらは各ページの中か「ファイル」へ。

### 5.3 クレーム 1 件の詳細ページ（約 70 列の分け方）

**一覧**（OpenMetadata の Schema タブと同じく 1 行は少なく）: 名前／意味（1 行）／型／入るトークン／個人情報の印／状態／問題の件数。上に検索と絞り込み（トークン・発行元・個人情報・状態・問題あり）。既定の並びは「問題あり → 承認待ち → そのほか」。列の追加は「列を選ぶ」から。

**詳細ページの上段**（常に見える。OpenMetadata の上パネル、DataHub の要約タブの見出しに倣い 6 個まで）

`名前`｜`意味（1〜2 行）`｜`型`｜`発行元`｜`入るトークン`｜`状態（下書き／確認中／承認済み／廃止予定）`
右端にバッジ: 個人情報・必須・問題 n 件。

**タブ**（7 つ。中身が空のタブは出さない。Backstage と OpenMetadata の「種類に合うタブだけ」）

| タブ | 入れる列の例 | 列数の目安 |
|---|---|---|
| 概要 | 意味の詳細、値の例、使う場面、関連するクレーム、標準での定義（RFC など） | 8〜10 |
| 値と型 | 型、書式、取りうる値、単一か複数か、必須か、既定値、大きさの上限 | 8〜10 |
| 発行と元データ | 発行元、元データの場所、変換の規則、どのトークンに入るか、入れる条件 | 10〜12 |
| 有効期間と更新 | 有効期間、更新のきっかけ、失効のさせ方、キャッシュの扱い | 6〜8 |
| 保護 | 個人情報の区分、見せてよい相手、暗号化、署名、ログへの出し方、最小化の方針 | 10〜12 |
| 使う側 | 経路ごとの扱い（通す／落とす／書き換える）、受け手、検証の方法 | 8〜10 |
| 経緯 | 決めた理由、検討した別案、所有者、承認者、変更の履歴、確認事項の記録 | 8〜10 |

タブの中は「ラベル: 値」の 2 列。**未記入の欄は既定で畳み**、「未記入 4 件を表示」で開く（Swagger UI と Redoc の「最初に開く深さ」の考え方）。必須の欄を上に並べる（Redoc の `sort-required-props-first`）。どのタブにも入らない列は 8 つめの「そのほかの属性」へ（OpenMetadata の Custom Properties、DataHub の Properties タブ）。

右の細い欄（広い画面だけ）: このクレームの問題、このクレームに関わる確認事項、YAML の該当行へのリンク。

注: タブへの振り分けは実際の列名を見て決め直すこと。ここでは列の正確な一覧を見ていないので、上の表は分け方の案であって対応表ではない。

### 5.4 問題パネル（検査の結果）

VS Code の Problems パネルと Spectral の結果の形をそのまま使う。

- **常に見える件数**: 画面の下に「エラー 2・警告 5・情報 3」。0 件なら「問題はありません」。クリックでパネルが開く。
- **1 行の形**: 重大度の印｜文面（人の言葉で 1 文）｜場所（`クレーム C-012 › 有効期間`）｜ファイル名:行｜規則の名前（薄い色、押すと説明）。
- **並びと束ね方**: 既定は重大度の順。切り替えで「ファイルごと」「クレームごと」「規則ごと」。
- **絞り込み**: 重大度のトグル 3 つ、文字での検索、「いま開いているクレームだけ」。
- **行を押すと**: 編集のときは YAML の該当行へ飛んで強調。見るときはクレームの該当タブの該当欄へ飛んで強調（Microsoft TMT の「一覧を選ぶと設計の該当箇所が強調される」）。
- **本文側の印**: エディターでは波線と行番号脇の印。一覧とナビでは件数のバッジ。
- **順送り**: F8／Shift+F8 で次／前の問題へ。
- **分けておくもの**: 「YAML として読めない」は検査の結果と混ぜず、パネルのいちばん上に赤い帯で 1 件だけ出す（読めない間はほかの検査が動かないため）。
- **人のレビューの指摘**は問題パネルに混ぜない。置き場は「確認事項」（Microsoft TMT が Messages と脅威の一覧を分けているのと同じ）。

### 5.5 168 問の代わりに、機能で絞った短い確認事項

SecurityRAT（性質を伝える → 要る要件だけ出る）、Threat Dragon（部品の性質から出す）、IriusRisk（質問に表示条件、対象外には理由）、DataHub のフォーム（必須の質問 + 最後に「確認済み」を押す）を合わせる。

**手順 1: 設計書から自動で性質を読む**（聞かずに済むものは聞かない）

設計書に書いてあることから、当てはまる性質を自動で立てる。例: 個人情報の印が付いたクレームがある／更新トークンがある／経路が 2 段以上ある／外部の発行元がある／暗号化するトークンがある／有効期間が基準より長いものがある。

**手順 2: 設計書から読めないことだけ 3〜5 問聞く**

例: 外部の事業者に渡すか／利用者が自分で失効できる必要があるか／監査の対象か。答えは review.yaml に残す。

**手順 3: 当てはまった性質に付いた確認事項だけ出す**

- 質問 1 件ごとに「出す条件」を持たせる（どの性質のときに出すか）。条件の無い共通の質問は 5〜8 問まで。
- 機械で確かめられる問いは確認事項から外して検査（問題パネル）へ移す。確認事項は**人が判断しないと決まらないものだけ**にする。
- 画面の上に必ず書く: 「この設計書に当てはまる確認事項は 14 件です（全 168 件のうち。154 件は当てはまらないので出していません → 理由を見る）」。出さなかった理由を見られることが、絞ったことへの信用になる。

**1 件の形**

| 部分 | 内容 |
|---|---|
| 問い | 1 文。はい／いいえで答えられる形 |
| なぜ出たか | 「更新トークンがあるため」 |
| 見る場所 | 該当するクレーム・トークンへのリンク（押すとそこへ飛んで強調） |
| 答え | 問題なし／直す必要あり／対象外／保留（既定は未回答） |
| 理由 | 「直す必要あり」と「対象外」は必須（IriusRisk と同じ）。それ以外は任意 |

**並べ方と進み具合**: 性質ごとに束ねる。上に進み具合の帯（回答済み n／全 n）。絞り込みは「未回答だけ」が既定。

**締め方**: 全部に答えたら「確認を終える」を押せる。押した人の名前と日時、設計書の版（ハッシュ）を記録する（DataHub の検証型フォームの「verified」に相当）。設計書が後で変わったら、変わった箇所に関わる確認事項だけ「もう一度確認」に戻す（いまの「再確認が要る」の仕組みをそのまま使える）。

**書き出し**: review.yaml に加え、印刷できる 1 枚の報告（要約の数字、直す必要ありの一覧、対象外と理由の一覧）を HTML で。Microsoft TMT の Create Full Report、IriusRisk の報告の束ね方に倣う。

**全件を見たい人へ**: 「すべての確認事項を見る（168 件）」のリンクを下に置く。既定では開かない。

### 5.6 画面に使う日本語と、やめる内輪の言葉

原則: 1 つの物に 1 つの名前。YAML のキーやファイル名は画面に出さず、出すなら括弧の中か「YAML を見る」の先に。課題番号（#50）は画面から消す。

| いまの言葉 | これからの言葉 | 理由／手本 |
|---|---|---|
| 台帳／台帳の行 | クレーム一覧／クレーム | 「台帳」は内輪の比喩。Backstage も DataHub も物の名前をそのまま使う |
| 台帳に無い行 | 一覧に無いクレーム | 同上 |
| 載るトークン／載る台帳の行 | 入るトークン／含まれるクレーム | 「載る」は内輪の言い方 |
| 出どころ | 元データ（どこから取るか） | 意味が一度で伝わる |
| ホップ／ホップの表 | 経路／経路の一覧（区間ごとの扱い） | 「ホップ」は通信の専門語 |
| トークン目録 | トークン一覧 | 「目録」を「一覧」にそろえる |
| カタログへの回答／25 問の回答 | 設計の前提（質問への答え） | 問いの数や内部の名前を見出しにしない |
| 観点／観点書／観点のチェックリスト | 確認事項 | 1 語にそろえる |
| 観点の網羅 | 確認事項の進み具合 | 同上 |
| lint／検査 | 問題（画面の名前）、自動チェック（説明の中） | VS Code の「問題」が広く通じる |
| lint と指摘の重ね合わせ | このクレームの問題と指摘 | 仕組みの名前でなく、見える物の名前にする |
| 指摘 | 指摘（そのまま） | 人が書いたものに限って使う |
| 行の種類（縮小 Lite） | 簡易版（列を減らした書き方） | 内部の版の名前を出さない |
| 回した先 | 担当（誰に確かめるか） | 内輪の言い方 |
| 寿命の 4 つの層 | 有効期間（4 段階） | 「寿命」「層」は内輪の比喩 |
| 対比表と判断の木 | 比較表と選び方 | 図の種類の名前を見出しにしない |
| 却下の理由の抜き取り | 却下した理由の一覧 | 同上 |
| そのほかの生成した表 | そのほかの表 | 「生成した」は作り手の都合 |
| 正本は YAML です | 保存されるのは YAML ファイルです | 「正本」は内輪の言葉 |
| レビュー（#50） | レビュー | 課題番号を出さない |
| 概要（いまの中身） | 概要（中身をダッシュボードに替える） | 5.2 |
| 判定: 合格／不合格 | 問題なし／直す必要あり | 人を採点する語を避ける。Threat Dragon も「処置の結果」で言う |
| 未着手／未回答／未提出 | 未回答（1 語にそろえる） | 状態の語を減らす |
| 対象外／該当なし | 対象外（1 語にそろえ、理由を必須に） | IriusRisk、Microsoft TMT |

状態の語は 2 組だけにする。

- クレームの状態: 下書き／確認中／承認済み／廃止予定（OpenMetadata の Draft／In Review／Approved、Backstage の deprecated）
- 確認事項の答え: 未回答／問題なし／直す必要あり／対象外／保留

### 5.7 作る順（小さく切るなら）

1. 最初の画面の 3 つの入口と、開いた物ごとの行き先（5.1）。体感がいちばん変わる。
2. 言葉の置き換え（5.6）。文言だけなので安い。
3. 問題パネルを下に固定し、行へ飛べるようにする（5.4）。
4. 概要をタイル 4 枚 +「次にやること」に替える（5.2 の 1〜3）。図と格子は後。
5. クレームの詳細を上段 + タブに分ける（5.3）。列の振り分けの表が先に要る。
6. 確認事項を「出す条件」つきにして絞る（5.5）。質問ごとの条件付けという中身の作業が大半。

---

## 6. 確かめられなかったことの一覧

| 事柄 | 状態 |
|---|---|
| Swagger Editor の左右 2 分割、初回のサンプル、誤り一覧から行へ飛ぶ動き | 未確認（公式文書の本文に記述なし） |
| Stoplight Studio の問題パネルの細部 | 未確認（文書ページ 404） |
| DataHub のデータセットのページのタブ名の一覧 | 未確認 |
| Backstage の既定のタブ名と About カードの項目 | 未確認（デモはスクリプト描画） |
| Threat Dragon の報告書の選択肢、未解決の脅威がある部品の色 | 未確認（文書ページ 401） |
| SecurityRAT の画面の列 | 未確認 |
| ASVS の段階ごとの要件数、適用外の扱いの文面 | 未確認（ページ 404） |
| Collibra、Atlan、JSON Schema のビューアー | 調べていない |
| クレームの約 70 列の実際の列名とタブへの対応 | 見ていない（5.3 は分け方の案） |
