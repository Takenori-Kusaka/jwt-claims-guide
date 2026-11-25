<!-- template_version: 0.3.0 -->
# 用語集（glossary）

> テンプレートです。候補と検討の問いだけを載せ、採否の理由の見本は載せません（理由の写し書きを防ぐため。#4 の方針）。判断は台帳（claims.yaml など）に 1 回だけ書き、ここからは ID で参照します。

テンプレート一式で使う訳語と表記です。ガイド（JWT クレーム設計ガイド）と同じ訳語にそろえています。ガイドにない語（台帳・トークン目録など、テンプレートで作った語）は、その旨を書きました。

- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施

<a id="notation"></a>
## 1. 表記の決まり

項目 ID：`template:glossary#notation`

| 表記 | 使い方 | 書かない表記 | 根拠 |
| --- | --- | --- | --- |
| Transaction Token（Txn-Token） | 初出は「Transaction Token（Txn-Token）」、2 回目からは「Txn-Token」。仕様名は「Transaction Tokens」（草案の名前）。発行するサービスは「Transaction Token Service（TTS）」 | トランザクショントークン、TxnToken、txn token | slide:p06-transaction-tokens、draft-ietf-oauth-transaction-tokens-11 §3 |
| 誰の権限で | `sub` が答える問い（`q-sub` の意味。DB の主体を指す「誰として DB に接続するか」（slide:p07-connect-as-whom）は別の問いで、この表記の対象ではない）（`templates/registry/questions.yaml` の `q-sub`）。「誰が代理して実行しているか」（`act`）と分けて書く | 誰として、誰の権限によって | slide:p05-one-request-carries、slide:p10-four-questions |
| アクセストークン（AT）・ID トークン（IDT）・リフレッシュトークン（RT） | 略称は表の中とトークン目録の ID だけで使う | アクセス・トークン | slide:p08-token-types-lifetimes |
| クレームの名前 | JSON に現れる名前をコードで書く（`sub`・`act`・`https://claims.example.com/` の `tenant_id`） | 地の文に名前をそのまま混ぜる | slide:p04-claim-names |
| スライド | 固定 ID で `slide:p06-narrow-downstream` と書く。番号では書かない | スライド 81 | templates/CONTRIBUTING.md の 1. |
| 筆者の提案 | 一次資料の裏付けのない判断。追跡 issue の番号を付ける | 推奨（裏付けがあるように読める） | templates/CONTRIBUTING.md の 1.、slide:p10-guidance-standards |

根拠：slide:p00-terminology、templates/CONTRIBUTING.md の 1.、筆者の提案：表記をこの表にそろえる（追跡 #4）

<a id="terms-basic"></a>
## 2. ガイドの基本の用語

項目 ID：`template:glossary#terms-basic`

| 用語 | 意味 | ほかの呼び方 | 根拠 |
| --- | --- | --- | --- |
| トークン | 主に JWT 形式のアクセストークンと ID トークン | アサーション（SAML、NIST） | slide:p00-terminology |
| クレーム | トークンの中の、名前と値の組 | 属性値、claim | slide:p00-terminology、RFC 7519 §2 |
| 属性 | 主体が持つ性質。クレームはそれを運ぶ形 | attribute | slide:p00-terminology |
| 発行者 | トークンに署名して発行する主体 | IdP、認可サーバー（AS）、STS、内部のトークン発行サービス | slide:p00-terminology |
| 受け手 | トークンを検証し、判断に使う側 | RP、リソースサーバー（RS）、API | slide:p00-terminology |
| 主体 | トークンが誰について述べているか。利用者・ワークロード（サービス・エージェント）・システム | subject、principal | slide:p00-terminology、slide:p05-three-principals |
| PEP／PDP | 要求を止める場所／許可するかを判断する場所 | ポリシー実施点／判断点 | slide:p00-terminology、slide:p05-pep-pdp |
| 入口 | 組織の網の入口のゲートウェイ。外部のトークンを検証し、内部トークンに交換する | エッジ、API ゲートウェイ | slide:p06-edge-exchange |
| 内部トークン | 入口で外部のトークンを検証し、作り直したトークン（phantom token を含む） | internal token | slide:p06-edge-exchange、templates/catalog/token_kinds.yaml |
| 共有クレーム | 複数の受け手が読む、組織の独自クレーム。足す前に追加前の 25 問に答える | — | slide:p11-pre-add-questions-1 |
| 名前空間 | 組織の独自クレームをまとめる名前（`https://claims.example.com/` のオブジェクトなど） | namespace | slide:p04-namespace |
| 下流ほど絞る | 下流のトークンは `aud`・`scope`・寿命のどれでも上流を超えない、という組織の規則 | narrowing | slide:p06-narrow-downstream |
| 送信者制約 | トークンを持つ者の鍵に束縛し、漏れたトークンをそのまま使えなくする仕組み（DPoP・mTLS） | sender-constrained token | slide:p08-rotation、RFC 9449 §1 |
| 剥奪 | 権限・属性を外すこと。届くまでの時間は、失効の手段とトークンの寿命で決まる | revoke（権限の） | slide:p08-stale-claims |
| 失効 | トークン・セッションを無効にすること | revocation | slide:p08-revocation-propagation、RFC 7009 §2 |
| 寿命の 4 つの層 | トークン・クレームの値の鮮度・セッションと RT・クレームの定義の寿命 | — | slide:p08-four-lifetimes |
| 鮮度 | 載せた値が現実と合っている期間。台帳では反映までに許す秒数（`volatility`） | freshness | slide:p08-four-lifetimes、slide:p08-stale-claims |

根拠：slide:p00-terminology、slide:p08-four-lifetimes

<a id="terms-questions"></a>
## 3. 問いの文言

項目 ID：`template:glossary#terms-questions`

設計書の「問い × 仕組み」（00_core の 6.）で使う問いです。文言はスライドと同じで、`templates/registry/questions.yaml` が正です（`tools/tests/test_registry_v1.py` が一致を確かめる）。

| 問い | ID | 主に答える仕組み | 根拠 |
| --- | --- | --- | --- |
| 誰の権限で | `q-sub` | `sub` | slide:p05-one-request-carries |
| 誰が代理して実行しているか | `q-actor` | `act`（最も外側が今の行為者） | slide:p05-one-request-carries、RFC 8693 §4.1 |
| どのワークロードが Txn-Token を求めたか | `q-req-wl` | Txn-Token の `req_wl` | slide:p05-one-request-carries、draft-ietf-oauth-transaction-tokens-11 §9.2 |
| 直接の通信相手は誰か | `q-peer` | mTLS・SPIFFE（通信の層） | slide:p05-one-request-carries |
| どこを経由したか | `q-via` | 証跡 | slide:p05-one-request-carries |
| どの取引か | `q-txn` | Txn-Token の `txn` | slide:p05-one-request-carries |
| 誰が利用者か | `q-user` | `sub` と組織の `user_id` | slide:p10-four-questions |
| どのエージェント・クライアントか | `q-agent` | `client_id`・`act` | slide:p10-four-questions |
| 何が承認されたか | `q-authorized` | `scope`・`authorization_details` | slide:p10-four-questions |
| どのリソース向けか | `q-resource` | `aud` | slide:p10-four-questions |
| 誰が持つべきか | `q-holder` | 送信者制約（`cnf`） | slide:p10-four-questions |

根拠：templates/registry/questions.yaml、slide:p05-one-request-carries、slide:p10-four-questions

<a id="terms-design-doc"></a>
## 4. テンプレートで作った用語

項目 ID：`template:glossary#terms-design-doc`

| 用語 | 意味 | 根拠 |
| --- | --- | --- |
| 台帳 | クレームごとの判断を、人が読めて機械で検査できる形にしたもの（`claims.yaml`）。スライド 134 の 12 項目を含む | slide:p11-registry-fields、templates/registry/README.md の 1. |
| トークン目録 | 使うトークンの種類ごとの採否・発行者・宛先・寿命の一覧（`token_types.yaml` の `token_types`） | templates/registry/README.md の 3.2 |
| 発行方式の選択 | クライアントの種類・grant・送信者制約などの選択（`token_types.yaml` の `issuance_profile`） | templates/registry/README.md の 3.3 |
| ホップ | 経路の 1 区間（送り手 → 受け手）。`hops.yaml` に 1 行ずつ書く | templates/registry/README.md の 3.4 |
| カタログ | 発行・利用イベントの一覧（`templates/catalog/`）。設計書はその全イベントに答える | templates/catalog/sources.md |
| 該当／対象外 | カタログのイベントに対する回答。対象外には、起きない前提と、その前提が崩れる条件を書く | templates/CONTRIBUTING.md の 2. |
| 採用／既定どおり／却下 | 台帳の行の採否。既定どおりは IdP が既定で出すものをそのまま受けること | templates/registry/README.md の 3.1 |
| 判断の行 | 台帳から生成する ADR の行（候補・採否・理由・前提・根拠・見直しの条件） | slide:p11-ownership、tools/claim_lint/RENDER.md の 1. |
| 縮小 Lite | 関門 1 の判定「絞る」で減らした Lite の定義（手で書く節は 5 つ） | research/template-design/gate1.md の 10. |
| 模範の理由 | 候補への採否と、その理由を示す文。テンプレートとカタログには載せない | research/template-design/report.md の Q6 |
| プロファイル | 「主体 × フロー」の型（P1・P4・P5）。信頼の境界ごとに 1 つ選ぶ | research/template-design/report.md の Q3 |
| モジュール | 認可方式・検証・データ層などの判断の部品 | research/template-design/report.md の Q3 |
| 項目 ID | テンプレートの節の固定の ID（`template:00_core#token-inventory`）。レビュー教材と対応表が参照する | templates/trace/README.md の「成果物の参照の書式」 |

根拠：templates/registry/README.md の 1.、research/template-design/report.md の Q3、筆者の提案：テンプレートで作った用語を、ガイドの用語と分けて並べる（追跡 #4）

<a id="terms-editor"></a>
## 5. 設計書のエディターの用語

項目 ID：`template:glossary#terms-editor`

設計書のエディター（`docs/claims/`）の画面で使う語です。画面・README・テンプレートで同じ名前を使います（#53）。ファイル名と技術の名前は、見出しやボタンには書かず、小さな補足か「詳しく」の中に書きます。

| 用語 | 意味 | 書かない表記 | 根拠 |
| --- | --- | --- | --- |
| 編集／レビュー | エディターの 2 つのモード。上のバーで切り替える。編集は設計書を直す画面、レビューは観点の問いに答え、行を判定し、指摘を記録する画面 | レビューモード（#50）、プレビュー | docs/claims/index.html |
| ダッシュボード | 開いた設計書の件数・検査の結果・レビューの進み具合・要対応の項目を並べる最初の画面（複数のファイルを開いたとき） | 概要 | docs/claims/preview.js |
| 書式の検査 | 台帳・トークン目録・ホップのファイルが、スキーマ（`templates/registry/*.schema.json`）に合うかの検査。入力のたびに行う | Schema の検査、JSON Schema（見出しでは） | templates/registry/README.md |
| 設計の規則の検査 | `tools/claim_lint` の規則（L1〜・R1〜）による検査。エディターでは Python をブラウザの中で動かす（初めては読み込みに数秒） | lint、claim_lint（見出し・ボタンでは）、Pyodide | tools/claim_lint/RULES.md |
| 検査の結果 | 書式の検査と設計の規則の検査の指摘（error・warn・info）の一覧 | 検査の結果（lint） | tools/claim_lint/RULES.md |
| レビューの記録 | レビュアーごとの回答・判定・指摘。ファイル `review.yaml` として設計書と同じディレクトリに置く | review.yaml（見出しでは） | templates/review/review.schema.json |
| 判定 | 台帳の行・トークンの種類・ホップなどの 1 行に付ける、承認／修正を求める／保留。記録した時の行の中身に結びつく | 行のハッシュ（画面では） | templates/review/review.schema.json |
| 再確認が要る | 判定を記録した後に、その行の中身が変わった状態 | stale | tools/review_record.py |
| 独立レビュー | 提出するまで、ほかのレビュアーの記録を画面に出さないレビュー | — | templates/review/procedure.md |
| 段階（core・full） | スライドと成果物の対応表で、要件が中核（core）か全体（full）か（`tier` の値） | tier（画面では） | templates/trace/README.md |

根拠：筆者の提案：エディターの画面の言葉を、初めて使う開発者・レビュアーに向けてそろえる（追跡 #53）
