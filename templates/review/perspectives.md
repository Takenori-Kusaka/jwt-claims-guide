<!-- template_version: 0.4.0 -->
# レビューの観点書（perspectives）

JWT のクレームの設計書（`templates/00_core.md` と台帳の YAML）をレビューするときの問いの一覧です。最上位の構成は、ガイドのスライド「レビューの観点」（slide:p12-review-viewpoints）の 6 段（定義・発行・伝搬・検証・認可・運用）です。各段の冒頭に、スライドの 3 つの観点と「誰が確かめるか」を置き、その下に、追加前の 25 問（slide:p11-pre-add-questions-1・2）、アンチパターンの専用の問い（slide:p12-antipatterns-1・2）、各 Part のチェックリストの問いを並べます。

- 使う場面：設計書の PR のレビュー。手順は [procedure.md](procedure.md)、記録は [report_template.md](report_template.md)
- 読み手：ID の分野の経験が浅いレビュアーも含む。問いは、**設計書の決まった欄を見れば Yes／No を付けられる**ように書いた。知識が要る問いには、対比表（[contrasts/](contrasts/)）と判断の木（[decision_tree.md](decision_tree.md)）へのリンクを付けた
- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施
- 「漏れゼロ」は約束しません。この問いの一覧の内側で、判断の抜けと理由の不備を見つけるためのものです。一覧の外は「カタログ外を問う」（`q-outside-catalog`）と、レビュー後の記録（[escaped_defects.md](escaped_defects.md)）で拾い、ここに戻します

## 問いの書き方と読み方

1 つの問いは次の形です。

```
**<問い ID>**　<Yes なら満たしている、という形の問い>
- 見る欄：答えを決めるために開く設計書の欄（`template:…`）・台帳の列（`registry:…`）
- No なら：重大度の目安と、すぐ取れる対策。専門家に回すなら escalation の ID
- つながり：対比表（`review:contrasts/…`）／判断の木／lint の規則（`lint:…`）／実行テスト（`test:…`）／事例
- 根拠：スライドの固定 ID・仕様の節・指針
```

- **Yes＝満たしている**。どの問いも、Yes なら問題がない向きに書いています。No のとき、または見る欄が空で判定できないときは、指摘にします（判定できないことも指摘です。種別は「理由の不備」か「候補の漏れ」）
- **見る欄**の書き方：`template:00_core#hop-table` は設計書の節（項目 ID。`templates/00_core.md` のアンカー）、`registry:hops#max_lifetime` は台帳の YAML の列（`templates/registry/*.schema.json` のプロパティ）、`template:claim_request#q13` は追加前の 25 問の問 13 の回答です
- **重大度の目安**：Blocker＝偽造・なりすまし・他テナントのデータに届く。Major＝権限の誤り・剥奪の遅れ・監査が崩れる。Minor＝記述の誤り・将来の保守で壊れる。最終の重大度はレビュアーが決めます
- **lint・実行テストとの分担**：lint（`tools/claim_lint`）は宣言の有無と整合を機械で見ます。実行テスト（#8）は実物の挙動を見ます。この観点書は、**理由が妥当か、目的と仕組みが合っているか**を見ます。lint が通っていても、問いを省きません。`（未実装）` の付いた lint・テストは、計画にあって、まだ無いものです
- **ID の付け方**：`ap-1-<n>`・`ap-2-<n>` はアンチパターンの行、`pa-<nn>` は追加前の 25 問の問 nn、`dc-<nn>` は設計のチェックリスト、`cf-<nn>`・`cd-<nn>` は Part 6・Part 7 のチェックリストの項目、`q-…` はそのほかの問いです。指摘の「場所」には、この ID と見た欄を書きます

問いの数（段ごと）は README の表にあります。

---

<a id="stage-definition"></a>

## 1. 定義：クレームの名前・型・意味を決める

**誰が確かめるか**：台帳の持ち主（発行者の側。クレームの持ち主の部門）が答え、受け手の代表（そのクレームを読むサービスの担当）がレビューで確かめます。定義の誤りは全受け手に広がるので、受け手が最低 1 人は加わります（筆者の提案：段ごとの担当の割り当て（追跡 #5））。

| スライド 148 の観点 | この段の問い |
| --- | --- |
| 既存クレームで表せないか | `q-registered-synonym`・`q-reuse-standard-structure`・`pa-03`・`dc-02` |
| 名前空間・型・無いときの意味 | `ap-2-3`・`ap-2-4`・`dc-03`・`dc-05`〜`dc-07`・`pa-04`〜`pa-09` |
| 台帳に登録したか | `pa-22`・`pa-trace`・`dc-gate`（25 問の確認は `pa-01`〜`pa-25` を使う。スライド 148 の「各段の確認に 25 問を使う」） |

根拠：slide:p12-review-viewpoints、slide:p11-pre-add-questions-1、NIST SP 800-162 §2.4.2
<!-- req:p12-review-viewpoints.R1 req:p12-review-viewpoints.R2 req:p12-review-viewpoints.R3 req:p12-review-viewpoints.R19 -->

### 1.1 設計のチェックリスト（スライド 61：12 の確認）

<a id="design-checklist"></a>

新しい独自クレームを載せる行（台帳の `claims` の採用の行）ごとに、12 の問いに答えます。1 つでも No か判定できない問いがあれば、そのクレームはまだトークンに載せません（`dc-gate`）。台帳の列との対応は `registry:README#slide-61-map` にあります。

**dc-01**　（載せるか）台帳の `usage` が認可・識別子で、`volatility` がトークンの受け入れの上限より長いか（認可に使い、寿命の間に変わらない値か）
- 見る欄：`registry:claims#usage`、`registry:claims#volatility`、`template:00_core#freshness`
- No なら：Major。変わる値なら `q-freshness-mitigation` に進む。認可に使わないなら載せない
- つながり：対比表 `review:contrasts/carry-vs-query#misuse`／判断の木 `review:decision_tree#carry-or-query`／lint `lint:L5`
- 根拠：slide:p04-design-checklist、slide:p04-carry-or-query

**dc-02**　（既存）`registered_ref` か `prior_art_search` に、登録名・IdP の既存クレームを探した記録があるか
- 見る欄：`registry:claims#registered_ref`、`registry:claims#prior_art_search`、`template:claim_request#q03`
- No なら：Minor（探した記録がない）。同じ意味の登録名があったなら Major（`q-registered-synonym`）
- つながり：対比表 `review:contrasts/scope-vs-role#misuse`／判断の木 `review:decision_tree#existing-claim-first`／lint `lint:L1a`
- 根拠：slide:p04-design-checklist、slide:p02-check-before-creating

**dc-03**　（名前）名前が組織の名前空間（`namespaces` に宣言した URI）の中にあり、予約名と照合した記録があるか
- 見る欄：`registry:claims#namespace`、`registry:claims#namespaces`、`template:claim_request#q04`
- No なら：Major（IdP が黙って消す・上書きする）。`ap-2-4` も見る
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`／lint `lint:L1b`・`lint:L34`（未実装）
- 根拠：slide:p04-design-checklist、slide:p04-namespace

**dc-04**　（ツール）受け手のすべてのツール（ゲートウェイの式・ポリシー言語・DB）でその名前を参照できることを、受け手ごとに確かめたか
- 見る欄：`registry:claims#consumer_access_path`、`template:claim_request#q05`
- No なら：Minor〜Major。「確かめていない」と書いてあれば、確かめるまで載せない
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`／実行 `test:consumer_contract#tool-access-path`（未実装）
- 根拠：slide:p04-design-checklist、slide:p04-namespace

**dc-05**　（型）型が 1 つに決まり、ID・金額は文字列か
- 見る欄：`registry:claims#type`、`template:claim_request#q07`、`template:claim_request#q08`
- No なら：Major（受け手ごとに解釈が分かれる）
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`／lint `lint:L24`（未実装）
- 根拠：slide:p04-design-checklist、slide:p04-type

**dc-06**　（形）複数の値は JSON の配列で、区切り文字の連結や JSON の文字列化をしていないか
- 見る欄：`registry:claims#shape`
- No なら：Major
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`／lint `lint:L36`（未実装）
- 根拠：slide:p04-design-checklist、slide:p04-shape

**dc-07**　（欠落）無い・null・false・空配列のそれぞれの意味と、無いときの受け手の動き（`on_missing`）が決まっているか
- 見る欄：`registry:claims#absent_semantics`、`registry:claims#on_missing`、`template:claim_request#q09`
- No なら：Major（欠けたトークンで「全件を許す」受け手が出る）
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L37`・`lint:L7`
- 根拠：slide:p04-design-checklist、slide:p04-absent-null-false-empty

**dc-08**　（比較）大文字小文字・空白の扱いが決まり、受け手は完全一致で比べるか
- 見る欄：`registry:claims#value_normalization`、`template:claim_request#q10`
- No なら：Minor〜Major（大小だけ違う値を同じとみなす受け手がいれば Major）
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`／実行 `test:negative_tests#case-variant`（未実装）
- 根拠：slide:p04-design-checklist、slide:p04-case-and-characters

**dc-09**　（識別子）照合に使う値が、表示名ではなく変わらない ID か（名前を出すなら、対になる ID の列があるか）
- 見る欄：`registry:claims#paired_id`、`registry:claims#identifier_properties`
- No なら：Major。`ap-1-6` も見る
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`／lint `lint:L3`
- 根拠：slide:p04-design-checklist、slide:p04-immutable-identifiers

**dc-10**　（書き手）誰が値を書けるか（`authoritative_writer`）と出どころ（`provenance`）が決まり、本人・呼び出し側の申告の値と分かれているか
- 見る欄：`registry:claims#authoritative_writer`、`registry:claims#provenance`、`registry:claims#modifiers`、`template:claim_request#q11`
- No なら：Blocker〜Major（本人が書ける値から権限を作ると昇格になる。`ap-1-7`）
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L31`
- 根拠：slide:p04-design-checklist、slide:p04-split-by-writer

**dc-11**　（サイズ）最大の長さ・件数（`max_bytes`・`max_items`）と、超えたときの挙動（`overflow_strategy`）が決まっているか
- 見る欄：`registry:claims#max_bytes`、`registry:claims#max_items`、`registry:claims#overflow_strategy`、`template:claim_request#q13`
- No なら：Major（黙った欠落）。`ap-2-1` も見る
- つながり：対比表 `review:contrasts/carry-vs-query#misuse`／lint `lint:R8`
- 根拠：slide:p04-design-checklist、slide:p04-size-budget

**dc-12**　（必須）欠けたら拒否するか（`on_missing`）、付与する発行者は 1 つか（`issuers`）
- 見る欄：`registry:claims#on_missing`、`registry:claims#issuers`、`registry:token_types#required_claims`
- No なら：Major
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L7`・`lint:L4`
- 根拠：slide:p04-design-checklist、slide:p04-single-issuer

**dc-gate**　dc-01〜dc-12 に 1 つも No・空欄が無いクレームだけが、トークンに載っているか（答えられない項目があるクレームは、載せずに台帳で `proposed` のままか）
- 見る欄：`registry:claims#status`、`template:claim_request#gate`
- No なら：Major。載せる判断を取り消すよう求める
- つながり：対比表 `review:contrasts/carry-vs-query#misuse`／lint `lint:R1`
- 根拠：slide:p04-design-checklist
<!-- req:p04-design-checklist.R1 req:p04-design-checklist.R2 req:p04-design-checklist.R3 req:p04-design-checklist.R4 req:p04-design-checklist.R5 req:p04-design-checklist.R6 req:p04-design-checklist.R7 req:p04-design-checklist.R8 req:p04-design-checklist.R9 req:p04-design-checklist.R10 req:p04-design-checklist.R11 req:p04-design-checklist.R12 req:p04-design-checklist.R13 -->

### 1.2 追加前の 25 問（スライド 142・143）

<a id="pre-add-questions"></a>

追加・変更する共有クレーム（組織の名前空間で、複数の受け手が読むもの）のそれぞれについて、`claim_request_<名前>.md` を開いて次を確かめます。**空欄がないこと（lint の L72 が見る）だけでなく、回答が妥当か**を見ます。とくに問 1・2・11・12・13・15・17・20 は、答えの中身で設計が決まるので、ここで No が出たら Major 以上にします。指摘の「場所」は `claim_request_<名前>.md の問 13` のように書きます。

**pa-01**　（問 1）回答が「受け手が何を決めるか」（許可・拒否・絞り込みの判断）を受け手の名前つきで書いていて、`usage` と食い違わないか
- 見る欄：`template:claim_request#q01`、`registry:claims#usage`、`registry:claims#answers`
- No なら：Major（使い道のないクレーム、または表示用の値で認可している）
- つながり：対比表 `review:contrasts/carry-vs-query#misuse`／判断の木 `review:decision_tree#carry-or-query`／lint `lint:L72`
- 根拠：slide:p11-pre-add-questions-1

**pa-02**　（問 2）値が寿命の間に変わるなら、変わってから反映されるまでの秒数と、それを超えるときの対策（短命化・都度判定・イベント）が書いてあるか
- 見る欄：`template:claim_request#q02`、`registry:claims#volatility`、`registry:claims#on_revoke`、`template:00_core#freshness`
- No なら：Major。`q-freshness-mitigation` で詳しく見る
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／lint `lint:L5`
- 根拠：slide:p11-pre-add-questions-1、slide:p08-stale-claims

**pa-03**　（問 3）登録簿・仕様の構造・IdP の文書・組織の台帳の順に探した記録があり、既存のクレームで表せない理由が書いてあるか
- 見る欄：`template:claim_request#q03`、`registry:claims#registered_ref`、`registry:claims#prior_art_search`
- No なら：Minor〜Major
- つながり：対比表 `review:contrasts/scope-vs-role#misuse`／判断の木 `review:decision_tree#existing-claim-first`／lint `lint:L1a`
- 根拠：slide:p11-pre-add-questions-1、slide:p02-check-before-creating

**pa-04**　（問 4）組織の名前空間の中で、予約名（IdP が既定で出す名前を含む）と照合した結果が書いてあるか
- 見る欄：`template:claim_request#q04`、`registry:claims#namespace`
- No なら：Major
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`／lint `lint:L1b`・`lint:L34`（未実装）
- 根拠：slide:p11-pre-add-questions-1

**pa-05**　（問 5）「.」「/」入りの名前を、すべての受け手のツールで参照できると確かめたか（「確かめていない」ではないか）
- 見る欄：`template:claim_request#q05`、`registry:claims#consumer_access_path`
- No なら：Minor（確かめるまで受け手を増やさない）
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`／実行 `test:consumer_contract#tool-access-path`（未実装）
- 根拠：slide:p11-pre-add-questions-1

**pa-06**　（問 6）トップレベルか組織のオブジェクトの下かが、台帳の `namespace`・`shape` と一致しているか
- 見る欄：`template:claim_request#q06`、`registry:claims#namespace`、`registry:claims#shape`
- No なら：Minor
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`
- 根拠：slide:p11-pre-add-questions-1、slide:p04-namespace-object-example

**pa-07**　（問 7）型が 1 つで、区切り文字列を使っていないか
- 見る欄：`template:claim_request#q07`、`registry:claims#type`、`registry:claims#shape`
- No なら：Major
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`／lint `lint:L36`（未実装）
- 根拠：slide:p11-pre-add-questions-1

**pa-08**　（問 8）ID・金額を文字列で運ぶか
- 見る欄：`template:claim_request#q08`、`registry:claims#type`
- No なら：Minor〜Major（大きな数値の精度落ち）
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`／lint `lint:L24`（未実装）
- 根拠：slide:p11-pre-add-questions-1、slide:p04-type

**pa-09**　（問 9）無い・null・false・空配列の意味と、無いときに拒否するかが、台帳の `on_missing` と一致しているか
- 見る欄：`template:claim_request#q09`、`registry:claims#absent_semantics`、`registry:claims#on_missing`
- No なら：Major
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L37`
- 根拠：slide:p11-pre-add-questions-1

**pa-10**　（問 10）大文字小文字・空白・比較の方法が書いてあり、受け手が完全一致で比べるか
- 見る欄：`template:claim_request#q10`、`registry:claims#value_normalization`
- No なら：Minor〜Major
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`／実行 `test:negative_tests#case-variant`（未実装）
- 根拠：slide:p11-pre-add-questions-1

**pa-11**　（問 11）誰が値を書けるかが、管理者・本人・呼び出し側・テナントの管理者のどれかまで書いてあり、本人や呼び出し側が書ける値を認可に使っていないか
- 見る欄：`template:claim_request#q11`、`registry:claims#authoritative_writer`、`registry:claims#provenance`、`registry:claims#modifiers`
- No なら：Blocker〜Major。「設定を変えられる者」に tenant_admin がいて API が照合していないなら Major 以上（シナリオ A の A01）
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L31`
- 根拠：slide:p11-pre-add-questions-1、slide:p04-split-by-writer

**pa-12**　（問 12）照合には不変の ID を使い、名前は表示だけに使うと書いてあるか
- 見る欄：`template:claim_request#q12`、`registry:claims#paired_id`
- No なら：Major
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`／lint `lint:L3`
- 根拠：slide:p11-pre-add-questions-1、slide:p04-immutable-identifiers

**pa-13**　（問 13）上限（長さ・件数）と、超えたときに失敗か欠落かが書いてあり、受け手がそれを検知できるか
- 見る欄：`template:claim_request#q13`、`registry:claims#max_items`、`registry:claims#overflow_strategy`
- No なら：Major
- つながり：対比表 `review:contrasts/carry-vs-query#misuse`／lint `lint:R8`
- 根拠：slide:p11-pre-add-questions-2

**pa-14**　（問 14）全リクエストに載せる理由があるか。読まない宛先のトークンには載せない（ホップごとに絞る）と書いてあるか
- 見る欄：`template:claim_request#q14`、`registry:claims#carried_in`、`registry:hops#custom_claims`
- No なら：Minor〜Major（読まない受け手に個人情報が届くなら Major）
- つながり：対比表 `review:contrasts/carry-vs-query#misuse`／lint `lint:L16`
- 根拠：slide:p11-pre-add-questions-2

**pa-15**　（問 15）付与する発行者が 1 つに決まっているか（入口の STS と IdP の両方が書くなら、段階が分かれ、どちらが正かが書いてあるか）
- 見る欄：`template:claim_request#q15`、`registry:claims#issuers`、`registry:claims#authoritative_writer`
- No なら：Major
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L4`
- 根拠：slide:p11-pre-add-questions-2、slide:p04-single-issuer

**pa-16**　（問 16）検証を組織の共通ライブラリ（共通の検証部品）で提供し、受け手ごとの独自の読み方をさせないか
- 見る欄：`template:claim_request#q16`、`template:modules/M_token_validation#shared-validator`
- No なら：Minor〜Major
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`
- 根拠：slide:p11-pre-add-questions-2

**pa-17**　（問 17）ヘッダーに移すなら、同名ヘッダーの変種（大文字小文字・アンダースコア・重複）を入口で除去すると書いてあるか（移さないなら「移さない」と書いてあるか）
- 見る欄：`template:claim_request#q17`、`registry:hops#forwarded_headers`
- No なら：Blocker（なりすまし）
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L8`／実行 `test:negative_tests#spoofed-identity-header`（未実装）
- 根拠：slide:p11-pre-add-questions-2、slide:p06-header-forwarding

**pa-18**　（問 18）未検証の値を流すモード（検証の無効化・デバッグ・既定値で続行）が無いと書いてあるか
- 見る欄：`template:claim_request#q18`
- No なら：Blocker〜Major。`q-no-unverified-passthrough-mode`
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`
- 根拠：slide:p11-pre-add-questions-2

**pa-19**　（問 19）知らない受け手が無視しても安全か。安全でない（制限のクレーム）なら、読む受け手を限定し、受け手の対応を先に済ませる手順があるか
- 見る欄：`template:claim_request#q19`、`registry:claims#consumers`
- No なら：Major（制限が効かない受け手が出る）
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L60`（未実装）
- 根拠：slide:p11-pre-add-questions-2、slide:p04-forward-compatibility

**pa-20**　（問 20）ログに残すか・値かハッシュか・個人情報の区分が書いてあり、台帳の `log_policy`・`pii_category` と一致しているか
- 見る欄：`template:claim_request#q20`、`registry:claims#log_policy`、`registry:claims#pii_category`
- No なら：Major（個人情報のログ）
- つながり：対比表 `review:contrasts/jws-vs-jwe#misuse`／lint `lint:L70`
- 根拠：slide:p11-pre-add-questions-2、NIST IR 8587 §5.3.1.7

**pa-21**　（問 21）委任のトークンに載るなら、`act`・承認 ID との関係（誰の値か、どちらで照合するか）が書いてあるか
- 見る欄：`template:claim_request#q21`、`registry:questions#q-actor`、`template:profiles/P4_ai_agent_delegation#audit-correlation`
- No なら：Major
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`
- 根拠：slide:p11-pre-add-questions-2

**pa-22**　（問 22）台帳に登録され、受け手（`consumers`）がすべて書いてあるか（設計書に出てくる受け手と一致するか）
- 見る欄：`template:claim_request#q22`、`registry:claims#consumers`
- No なら：Major（廃止のとき連絡できない受け手が残る）
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／lint `lint:R1`
- 根拠：slide:p11-pre-add-questions-2、slide:p11-registry-fields

**pa-23**　（問 23）形式を変えるときの移行計画（受け手が先・発行者が後）があるか
- 見る欄：`template:claim_request#q23`、`template:00_core#definition-lifecycle`
- No なら：Minor（いま変更の予定がなければ）〜Major（変更中なら）
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／lint `lint:L10`
- 根拠：slide:p11-pre-add-questions-2、slide:p11-change-procedure

**pa-24**　（問 24）改名・廃止の互換期間と並行発行の期間が書いてあるか（「同じ手順」と書くなら、参照先の手順が実在するか）
- 見る欄：`template:claim_request#q24`、`registry:claims#sunset_on`、`template:00_core#definition-lifecycle`
- No なら：Minor〜Major
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／lint `lint:L18`
- 根拠：slide:p11-pre-add-questions-2、slide:p11-change-procedure

**pa-25**　（問 25）発行前の確認手段（IdP のプレビュー・発行側のスキーマ）と、受け手の条件のテスト（欠落・語彙の外を拒否する）が書いてあるか
- 見る欄：`template:claim_request#q25`、`template:modules/M_idp_keycloak#token-preview`
- No なら：Minor〜Major
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／実行 `test:consumer_contract#issued-claims-present`（未実装）
- 根拠：slide:p11-pre-add-questions-2、slide:p11-schema-contract-tests

**pa-gate**　答えられない問いが残るクレームを、共有クレームにしていないか（残るなら、サービス内のローカルな属性にとどめるか `status: proposed` のままか）。また、25 問の回答がクレームごとに固有か（ほかのクレームの回答の写しになっていないか）
- 見る欄：`template:claim_request#gate`、`registry:claims#status`
- No なら：Major
- つながり：対比表 `review:contrasts/carry-vs-query#misuse`／lint `lint:L72`
- 根拠：slide:p11-pre-add-questions-1、slide:p09-do-not-carry

**pa-trace**　25 問の回答が、設計書の判断の行（ADR）と台帳の該当の 1 行の両方から辿れるか（`claim_request_<名前>.md` の「対象：」が台帳の ID を指し、台帳の `rationale` が 25 問と食い違わないか）
- 見る欄：`template:claim_request#form`、`template:00_core#decisions`、`registry:claims#rationale`
- No なら：Minor（辿れない）〜Major（食い違う）
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／lint `lint:L72`
- 根拠：slide:p11-pre-add-questions-2
<!-- req:p11-pre-add-questions-1.R1 req:p11-pre-add-questions-1.R2 req:p11-pre-add-questions-1.R3 req:p11-pre-add-questions-1.R4 req:p11-pre-add-questions-1.R5 req:p11-pre-add-questions-1.R6 req:p11-pre-add-questions-1.R7 req:p11-pre-add-questions-1.R8 req:p11-pre-add-questions-1.R9 req:p11-pre-add-questions-1.R10 req:p11-pre-add-questions-1.R11 req:p11-pre-add-questions-1.R12 req:p11-pre-add-questions-1.R13 req:p11-pre-add-questions-2.R1 req:p11-pre-add-questions-2.R2 req:p11-pre-add-questions-2.R3 req:p11-pre-add-questions-2.R4 req:p11-pre-add-questions-2.R5 req:p11-pre-add-questions-2.R6 req:p11-pre-add-questions-2.R7 req:p11-pre-add-questions-2.R8 req:p11-pre-add-questions-2.R9 req:p11-pre-add-questions-2.R10 req:p11-pre-add-questions-2.R11 req:p11-pre-add-questions-2.R12 req:p11-pre-add-questions-2.R13 req:p11-pre-add-questions-2.R14 -->

### 1.3 既存のクレームと意味

<a id="q-registered-synonym"></a>

**q-registered-synonym**　登録クレーム・台帳の既存のクレームと同じ意味の独自クレームを、別名で作っていないか（台帳に同じ意味の行が 2 つないか）
- 見る欄：`registry:claims#registered_ref`、`registry:claims#prior_art_search`、`registry:claims#description`
- No なら：Major（受け手がどちらを読むかで判断が分かれる）
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`／判断の木 `review:decision_tree#existing-claim-first`／lint `lint:L1a`
- 根拠：slide:p02-registered-claims、slide:p02-name-categories、slide:p02-check-before-creating
<!-- req:p02-registered-claims.R7 req:p02-name-categories.R3 req:p02-check-before-creating.R5 -->

<a id="q-reuse-standard-structure"></a>

**q-reuse-standard-structure**　鍵への結び付けは `cnf`、相関 ID は `txn`、確認済みの属性は `verified_claims` のように、既存の構造で表せるものを既存の構造で表しているか
- 見る欄：`registry:claims#registered_ref`、`registry:claims#verification_method`、`registry:questions#q-holder`
- No なら：Minor〜Major（独自の `device_key` などは、受け手の検証部品が知らない）
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／判断の木 `review:decision_tree#existing-claim-first`
- 根拠：slide:p02-keys-events-identity-assurance、RFC 9449 §6.1
<!-- req:p02-keys-events-identity-assurance.R1 req:p02-keys-events-identity-assurance.R3 req:p02-keys-events-identity-assurance.R4 -->

<a id="q-auth-context-semantics"></a>

**q-auth-context-semantics**　`iat` を認証の時刻に、`amr` の `mfa` を保証の水準に、`sid` をアプリのセッション ID に使っていないか（認証の新しさは `auth_time`、強さは `acr` で見ているか）
- 見る欄：`registry:claims#not_meaning`、`registry:claims#usage`、`registry:questions#q-auth-strength`、`template:00_core#step-up`
- No なら：Major（サイレント再認証で `iat` だけが新しくなり、古い認証で高リスクの操作が通る）
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`
- 根拠：slide:p02-registered-claims、slide:p02-auth-strength-session、slide:p08-reissue-triggers、OpenID Connect Core 1.0 §2
<!-- req:p02-registered-claims.R4 req:p02-auth-strength-session.R2 req:p02-auth-strength-session.R3 req:p08-reissue-triggers.R5 -->

<a id="q-scope-semantics"></a>

**q-scope-semantics**　`scope` を利用者の全権限と読まず（クライアントに委ねた範囲として扱い）、各スコープが `aud` のリソースにとって意味を持ち、同じ API で `scope` と `authorization_details` を併用していないか
- 見る欄：`registry:claims#not_meaning`、`registry:hops#scope`、`registry:hops#aud`、`registry:claims#value_vocabulary`
- No なら：Major
- つながり：対比表 `review:contrasts/scope-vs-role#misuse`／判断の木 `review:decision_tree#rar-vs-custom`
- 根拠：slide:p02-scope、RFC 9396 §2、RFC 9068 §2.2.3
<!-- req:p02-scope.R1 req:p02-scope.R2 req:p02-scope.R4 req:p02-scope.R6 -->

<a id="q-value-vocabulary"></a>

**q-value-vocabulary**　`roles`・`groups` などの値の語彙が台帳（`value_vocabulary`）にあり、同じ文字列が受け手・IdP をまたいで同じ意味だと仮定していないか（IdP ごとの出どころ `upstream_issuer` が書いてあるか）
- 見る欄：`registry:claims#value_vocabulary`、`registry:claims#upstream_issuer`
- No なら：Major（別の IdP の `admin` が組織の `admin` として通る）
- つながり：対比表 `review:contrasts/scope-vs-role#misuse`
- 根拠：slide:p02-roles-groups-entitlements、slide:p03-confusing-differences
<!-- req:p02-roles-groups-entitlements.R3 -->

<a id="q-role-explosion"></a>

**q-role-explosion**　ロールの名前に、テナント・対象・操作の組み合わせを焼き込んでいないか（細かい権限は PDP に置いているか）
- 見る欄：`registry:claims#value_vocabulary`、`registry:claims#max_items`、`template:modules/M_authz_pdp#model-choice`
- No なら：Minor〜Major
- つながり：対比表 `review:contrasts/scope-vs-role#misuse`／lint `lint:L69`・`lint:L40`（未実装）
- 根拠：slide:p05-role-explosion
<!-- req:p05-role-explosion.R1 -->

### 1.4 識別子

<a id="q-identifier-choice"></a>

**q-identifier-choice**　利用者・テナントを決めるキーが `iss`＋`sub` か組織の不変の ID で、`email`・`upn`・ペアワイズの `sub` の突き合わせ・`sub_id` と `sub` の組み合わせを使っていないか。テナントを実際に決めている値（`iss` か `tenant_id` か）が 1 つに書いてあるか
- 見る欄：`registry:claims#usage`、`registry:claims#identifier_properties`、`registry:token_types#subject_type`、`template:00_core#principals`、`template:modules/M_multitenancy#tenant-determination`
- No なら：Major〜Blocker（乗っ取り）。シナリオ A の A02・A05 はここ
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`／lint `lint:L3`・`lint:L28`（未実装）
- 根拠：slide:p02-user-identifier、slide:p04-immutable-identifiers
<!-- req:p02-user-identifier.R1 req:p02-user-identifier.R3 req:p02-user-identifier.R4 req:p02-user-identifier.R5 -->

<a id="ap-1-6"></a>

**ap-1-6**　（アンチパターン：email・upn を利用者のキーにする）利用者のキーが `iss`＋`sub`（Entra は `tid`＋`oid`）で、`email`・`upn`・`preferred_username` を照合のキーにしていないか
- 見る欄：`registry:claims#usage`（identifier の行）、`registry:claims#identifier_properties`、`template:modules/M_data_layer#db-identity`
- No なら：Blocker（アカウントの乗っ取り）
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`／lint `lint:L3`／事例 nOAuth（2023。Entra の変更できる email を信じた RP の乗っ取り）
- 根拠：slide:p12-antipatterns-1、slide:p02-user-identifier、OpenID Connect Core 1.0 §5.7
<!-- req:p12-antipatterns-1.R6 -->

<a id="q-pairwise-external"></a>

**q-pairwise-external**　外部の受け手に出す `sub` をペアワイズにするかを、トークン種別ごとに決め、ペアワイズの値が推測できない（識別情報を含まない）か
- 見る欄：`registry:token_types#subject_type`、`template:modules/M_privacy_minimization#identifier-sectors`
- No なら：Minor〜Major（取引先の間で名寄せされる）
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`
- 根拠：slide:p09-pairwise-identifiers、slide:p09-checklist、OpenID Connect Core 1.0 §8
<!-- req:p09-pairwise-identifiers.R1 req:p09-pairwise-identifiers.R3 req:p09-checklist.R3 -->

### 1.5 載せる値の選び方と個人情報

<a id="ap-2-1"></a>

**ap-2-1**　（アンチパターン：グループ・ロールを全部トークンに詰める）トークンに載せるのは粗いロールだけで、件数の上限（`max_items`）と超過時の扱いがあり、細かい権限は PDP に置いているか
- 見る欄：`registry:claims#max_items`、`registry:claims#overflow_strategy`、`template:modules/M_authz_pdp#carry-or-query`
- No なら：Major（ヘッダーの上限・IdP の打ち切りで黙って欠ける）
- つながり：対比表 `review:contrasts/carry-vs-query#misuse`／判断の木 `review:decision_tree#carry-or-query`／lint `lint:R8`・`lint:L69`／事例 Entra のグループの超過（200 件で `_claim_names` に替わる）
- 根拠：slide:p12-antipatterns-2、slide:p03-entra-scp-roles-groups、slide:p04-size-budget
<!-- req:p12-antipatterns-2.R1 -->

<a id="ap-2-2"></a>

**ap-2-2**　（アンチパターン：変わりやすい権限を焼き込む）変わりやすい権限のクレームに、短命化・都度判定・失効の伝播のどれかの対策が書いてあるか
- 見る欄：`registry:claims#volatility`、`registry:claims#on_revoke`、`template:00_core#freshness`
- No なら：Major（剥奪が期限まで届かない）
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／判断の木 `review:decision_tree#lifetime-by-situation`／lint `lint:L5`／事例 Entra CAE のグループ変更の反映に最大 1 日
- 根拠：slide:p12-antipatterns-2、slide:p08-stale-claims
<!-- req:p12-antipatterns-2.R2 -->

<a id="ap-2-3"></a>

**ap-2-3**　（アンチパターン：型を決めない・配列を区切り文字列にする）型と形が台帳で 1 つに固定され、受け手のスキーマ（`schemas/*.consumer.schema.json`）と一致しているか
- 見る欄：`registry:claims#type`、`registry:claims#shape`
- No なら：Major
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`／lint `lint:L1a`・`lint:L24`（未実装）／実行 `test:consumer_contract#type-shape-match`（未実装）／事例 ガイドに事例の行なし
- 根拠：slide:p12-antipatterns-2、slide:p04-type、slide:p04-shape
<!-- req:p12-antipatterns-2.R3 -->

<a id="ap-2-4"></a>

**ap-2-4**　（アンチパターン：名前空間なしの独自クレーム）独自クレームがすべて組織の URI の名前空間の下にあるか
- 見る欄：`registry:claims#namespace`、`registry:claims#namespaces`
- No なら：Major（予約名と衝突し、黙って消える）
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`／lint `lint:L1b`／事例 Auth0 の予約名（`roles`・`groups` など）と衝突した独自クレームは、エラーにならず黙って追加されない
- 根拠：slide:p12-antipatterns-2、slide:p03-auth0-namespace
<!-- req:p12-antipatterns-2.R4 -->

<a id="q-payload-readable"></a>

**q-payload-readable**　署名だけの JWT のペイロードは、持つ者・経由する全ホップ・ログが読めることを前提に、載せる値を選んでいるか（台帳の `confidential_from` の相手が、目録の `visible_to` にいないか）
- 見る欄：`registry:claims#pii_category`、`registry:claims#confidential_from`、`registry:token_types#visible_to`
- No なら：Major
- つながり：対比表 `review:contrasts/jws-vs-jwe#misuse`／lint `lint:L65`・`lint:L6`
- 根拠：slide:p01-jwt-structure、slide:p09-jws-is-readable、RFC 7515 §1
<!-- req:p01-jwt-structure.R2 -->

<a id="q-confidential-reaches-reader"></a>

**q-confidential-reaches-reader**　読まれてはいけないクレームが、それを読める相手（ブラウザ・入口・ログ・取引先）に届くトークンに載っていないか（載せるなら、その相手が復号できない JWE にしているか）
- 見る欄：`registry:claims#confidential_from`、`registry:token_types#visible_to`、`registry:token_types#jwe`、`template:modules/M_privacy_minimization#protection-table`
- No なら：Major
- つながり：対比表 `review:contrasts/jws-vs-jwe#misuse`／lint `lint:L65`・`lint:L66`
- 根拠：slide:p09-jws-is-readable、slide:p09-jwe-sd-jwt、RFC 7516 §1

<a id="q-no-secret-or-raw-pii"></a>

**q-no-secret-or-raw-pii**　認証の秘密（パスワード・API キー）と平文の個人情報（生年月日・住所など）を、どのトークンにも載せていないか
- 見る欄：`registry:claims#data_category`、`registry:claims#pii_category`
- No なら：Blocker（秘密）〜Major（個人情報）
- つながり：対比表 `review:contrasts/jws-vs-jwe#misuse`／lint `lint:L70`・`lint:L51`（未実装）
- 根拠：slide:p09-do-not-carry、slide:p09-checklist、NIST SP 800-63C-4 §3.10
<!-- req:p09-checklist.R1 -->

<a id="q-derived-value"></a>

**q-derived-value**　受け手が要るのが値か判定かを問い、判定で足りるなら派生値（「18 歳以上か」など）を載せているか
- 見る欄：`registry:claims#usage`、`registry:claims#description`、`template:modules/M_privacy_minimization#derived-values`
- No なら：Minor〜Major
- つながり：対比表 `review:contrasts/carry-vs-query#misuse`
- 根拠：slide:p09-minimize-derived、slide:p09-checklist、NIST SP 800-63C-4 §3.12.2
<!-- req:p09-minimize-derived.R1 req:p09-checklist.R2 -->

<a id="q-baseline-kept"></a>

**q-baseline-kept**　共通の基準（受け入れの検証・必須の欠落の拒否・型の固定・不変の ID・組織の名前空間・ログにトークン全文と個人情報を残さない）を、1 つも外していないか（外すなら Full にし、専門家に回しているか）
- 見る欄：`template:00_core#baseline`、`template:00_core#deviations`
- No なら：Major。外した基準は `review:escalation#baseline-unmet` に回す
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`
- 根拠：slide:p12-priorities-deferrals
<!-- req:p12-priorities-deferrals.R1 -->

---

<a id="stage-issuance"></a>

## 2. 発行：誰が、いつ、どの情報からクレームを書くか

**誰が確かめるか**：発行者（IdP の設定・発行時フック・入口の STS・Txn-Token のサービスの担当）。発行時フックの失敗時の挙動は、運用の担当も確かめます（筆者の提案：段ごとの担当の割り当て（追跡 #5））。

| スライド 148 の観点 | この段の問い |
| --- | --- |
| 書けるのは 1 つの発行者だけか | `q-single-issuer`・`pa-15`・`ap-1-7` |
| フックの失敗で欠けたら拒否できるか | `q-hook-failure`・`cf-02` |
| サイズの上限 | `q-size-limit`・`dc-11`・`pa-13` |

根拠：slide:p12-review-viewpoints、slide:p06-stage-map、slide:p06-issuance-hook
<!-- req:p12-review-viewpoints.R4 req:p12-review-viewpoints.R5 req:p12-review-viewpoints.R6 -->

<a id="q-single-issuer"></a>

**q-single-issuer**　各クレームを付与する発行者が台帳の `issuers` に 1 つ（段階ごとに 1 つ）で、各サービスがクレームを追記したり、トークンを作り直したりしていないか
- 見る欄：`registry:claims#issuers`、`registry:claims#authoritative_writer`、`template:00_core#scope-boundary`
- No なら：Major
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L4`
- 根拠：slide:p04-single-issuer、slide:p06-stage-map

<a id="q-hook-failure"></a>

**q-hook-failure**　発行時フックが失敗・打ち切り・予約名との衝突でクレームを出さなかったとき、そのトークンを受け手が拒否するか（フックが呼ばれない発行の経路が、カタログの回答で確かめてあるか）
- 見る欄：`registry:claims#on_missing`、`registry:token_types#required_claims`、`template:modules/M_idp_keycloak#limits`、`template:00_core#catalog-answers`
- No なら：Major（クレームの無いトークンが「既定の権限」で通る）
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:R3b`・`lint:L7`／実行 `test:negative_tests#missing-required-claim`（未実装）／事例 ケーススタディ B15（Okta のフックの打ち切りで部署が消えた）
- 根拠：slide:p03-custom-claim-injection、slide:p06-issuance-hook、jwt-claims-casestudy@080b8da:B15

<a id="q-size-limit"></a>

**q-size-limit**　トークン種別ごとの最悪のサイズが、経路の上限（ヘッダー・Cookie・IdP の上限）を下回ることを計算で確かめたか
- 見る欄：`registry:token_types#size`、`template:00_core#ci-results`（R8 の計算）
- No なら：Major
- つながり：対比表 `review:contrasts/carry-vs-query#misuse`／lint `lint:R8`
- 根拠：slide:p04-size-budget

<a id="ap-1-7"></a>

**ap-1-7**　（アンチパターン：本人が書ける属性から権限を作る）権限・識別子のクレームの出どころ（`provenance`）に、本人が編集できる値・呼び出し側の申告・テナントの管理者が変えられる値が無いか（あるなら、API が `iss` や API の設定と照合しているか）
- 見る欄：`registry:claims#provenance`、`registry:claims#modifiers`、`registry:claims#enforced_at`
- No なら：Blocker（権限の昇格）
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L31`／事例 Cognito の `custom:` 属性（読み取り専用にしない限り、本人が書き換えられる場合がある）
- 根拠：slide:p12-antipatterns-1、slide:p03-cognito-pre-token-hook、slide:p04-split-by-writer
<!-- req:p12-antipatterns-1.R7 -->

<a id="q-hook-adds-raw-pii"></a>

**q-hook-adds-raw-pii**　発行時フックが、生の個人情報（生年月日など）を足していないか
- 見る欄：`registry:claims#authoritative_writer`、`registry:claims#pii_category`、`registry:claims#data_category`
- No なら：Major
- つながり：対比表 `review:contrasts/jws-vs-jwe#misuse`／lint `lint:L70`
- 根拠：slide:p06-issuance-hook
<!-- req:p06-issuance-hook.R4 -->

<a id="q-minimal-per-recipient"></a>

**q-minimal-per-recipient**　受け手ごとに、その受け手が読むクレームだけを出しているか（台帳の `consumers` に無い受け手のトークンに載せていないか）
- 見る欄：`registry:claims#consumers`、`registry:claims#carried_in`、`registry:hops#custom_claims`
- No なら：Minor〜Major
- つながり：対比表 `review:contrasts/carry-vs-query#misuse`／lint `lint:L16`
- 根拠：slide:p09-minimize-derived、slide:p09-checklist、NIST SP 800-63C-4 §3.10
<!-- req:p09-minimize-derived.R4 req:p09-checklist.R4 -->

<a id="q-rar-per-audience"></a>

**q-rar-per-audience**　承認の内容（`authorization_details`）を JWT に入れるとき、宛先ごとに、その宛先の `type` だけに絞っているか
- 見る欄：`registry:hops#authorization_details`、`registry:hops#custom_claims`
- No なら：Minor〜Major
- つながり：対比表 `review:contrasts/scope-vs-role#misuse`／実行 `test:negative_tests#rar-unknown-type`（未実装）
- 根拠：slide:p06-step-up-approval、RFC 9396 §9.1
<!-- req:p06-step-up-approval.R3 -->

<a id="q-agent-own-identity"></a>

**q-agent-own-identity**　エージェントを独立した主体（自分の `client_id`・ワークロードの ID）として登録し、共有アカウントや利用者のトークンを借りていないか
- 見る欄：`template:profiles/P4_ai_agent_delegation#agent-identity`、`template:00_core#principals`
- No なら：Major（誰が実行したか分からない）
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`／lint `lint:L55`（未実装）
- 根拠：slide:p10-agent-identity、slide:p10-agent-checklist
<!-- req:p10-agent-identity.R1 req:p10-agent-identity.R3 req:p10-agent-checklist.R1 req:p12-antipatterns-2.R7 -->

<a id="q-agent-delegation-claims"></a>

**q-agent-delegation-claims**　代理で動くトークンで、`sub`＝利用者、`act`・`client_id`＝エージェントに分かれているか
- 見る欄：`registry:claims#answers`、`registry:questions#q-actor`、`template:00_core#question-mechanism`
- No なら：Major
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`／判断の木 `review:decision_tree#keep-sub-exchange`／lint `lint:L12`
- 根拠：slide:p10-four-questions、slide:p10-agent-checklist、RFC 8693 §4.1
<!-- req:p10-agent-checklist.R2 -->

<a id="q-idp-capability-verified"></a>

**q-idp-capability-verified**　設計が IdP・製品の機能（RFC 8707 の `resource`・トークン交換・CIBA・フックの呼ばれる契機など）に依存する行のすべてに、その製品の版の公式文書か実測の出どころがあるか
- 見る欄：`template:00_core#issuance-profile`、`registry:token_types#refs`、`registry:claims#refs`、`template:00_core#uncertain`
- No なら：Major（前提の誤り）。出どころの無い行は `review:escalation#unverified-idp-behavior` に回す。較正で追加（B07。templates/examples/scenario-b/review-report.md の 9.）
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`
- 根拠：slide:p03-recent-changes、slide:p03-keycloak-aud-lightweight

<a id="q-variant-comparison"></a>

**q-variant-comparison**　既定から外した選択（送信者制約・JWE・寿命など）の比較が、台帳の機械的な差分だけでなく、安全性の差（開く攻撃の型）と、要求の全体のサイズ（ヘッダーを含む）を比べているか
- 見る欄：`template:00_core#deviations`、`template:00_core#issuance-profile`、`registry:token_types#size`
- No なら：Minor〜Major（理由の不備）。較正で追加（B12。templates/examples/scenario-b/review-report.md の 9.）
- つながり：対比表 `review:contrasts/carry-vs-query#misuse`／lint `lint:R8`
- 根拠：slide:p12-priorities-deferrals、slide:p04-size-budget

<a id="q-outside-catalog"></a>

**q-outside-catalog**　カタログ（発行・利用のイベント）の外を問う欄（`outside_enumeration`）に、探した範囲が具体的に書いてあり、レビュアーが図・経路から思いつく発行・利用の場面（例：管理画面からの発行、障害時の再送、テストの経路、移行期間の旧経路）が、その範囲の中で答えられているか
- 見る欄：`template:00_core#catalog-answers`、`template:00_core#sequence`、`template:00_core#scope-boundary`
- No なら：Major（想定漏れの候補）。見つけた場面は、出どころ「カタログ外の質問」で記録し、カタログに戻す（[procedure.md](procedure.md) の 6.）
- つながり：対比表 `review:contrasts/carry-vs-query#misuse`／lint `lint:R9`・`lint:R2`
- 根拠：templates/catalog/sources.md、tools/claim_lint/RULES.md の R9

---

<a id="stage-propagation"></a>

## 3. 伝搬：トークンをどう渡し、どこで絞るか

**誰が確かめるか**：入口（ゲートウェイ・トークン交換のサービス・Txn-Token のサービス）の担当。経路の図（シーケンス図・ホップの表）を描いた人と別の人が確かめます（筆者の提案：段ごとの担当の割り当て（追跡 #5））。

| スライド 148 の観点 | この段の問い |
| --- | --- |
| 下流ほど aud・scope・寿命を絞るか | `q-hop-narrowing`・`q-hop-lifetime`・`cf-05` |
| 受け取ったトークンを渡していないか | `ap-2-6`・`q-no-passthrough`・`cf-04` |
| ヘッダーの除去 | `ap-2-5`・`cf-08`・`pa-17` |

根拠：slide:p12-review-viewpoints、slide:p06-narrow-downstream、slide:p06-header-forwarding
<!-- req:p12-review-viewpoints.R7 req:p12-review-viewpoints.R8 req:p12-review-viewpoints.R9 -->

### 3.1 流れの規則（スライド 90：10 項目）

<a id="checklist-p06-flow"></a>

経路（`hops.yaml` とシーケンス図）について、10 項目を確かめます。各項目の詳しい問いは右の ID です。

**cf-01**　（項目 1）段階（① 認証時〜⑥ 承認・同意）ごとに書き手が決まり、フックには安定した属性だけを入れているか
- 見る欄：`registry:claims#authoritative_writer`、`registry:claims#volatility`
- No なら：Major。詳しくは `q-single-issuer`
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L4`
- 根拠：slide:p06-flow-checklist、slide:p06-stage-map

**cf-02**　（項目 2）フックの失敗でクレームが欠けたら、受け手が拒否するか
- 見る欄：`registry:claims#on_missing`、`registry:token_types#required_claims`
- No なら：Major。詳しくは `q-hook-failure`
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L7`
- 根拠：slide:p06-flow-checklist

**cf-03**　（項目 3）外部のトークンは入口で終わらせ、内部専用の形（内部の発行者・内部の `aud`）に替えているか
- 見る欄：`registry:hops#exchanger`、`registry:hops#token_type`、`template:profiles/P5_internal_propagation#edge-conversion`
- No なら：Major。詳しくは `q-idp-diff-absorbed`
- つながり：対比表 `review:contrasts/id-vs-access-token#misuse`／lint `lint:L41`（未実装）
- 根拠：slide:p06-flow-checklist、slide:p06-edge-exchange

**cf-04**　（項目 4）受け取ったトークンを、別の宛先へそのまま渡していないか（ホップごとに `token_type` か `aud` が替わるか）
- 見る欄：`registry:hops#token_type`、`registry:hops#aud`、`registry:hops#upstream`
- No なら：Major。詳しくは `ap-2-6`
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`／lint `lint:L41`（未実装）
- 根拠：slide:p06-flow-checklist

**cf-05**　（項目 5）下流のホップは `aud`・`scope`・寿命で上流を超えないか
- 見る欄：`registry:hops#aud`、`registry:hops#scope`、`registry:hops#max_lifetime`
- No なら：Major。詳しくは `q-hop-narrowing`・`q-hop-lifetime`
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／lint `lint:L16`
- 根拠：slide:p06-flow-checklist、slide:p06-narrow-downstream

**cf-06**　（項目 6）Txn-Token を専用ヘッダー（`Txn-Token`）で送り、アクセストークンとして送っていないか
- 見る欄：`registry:token_types#transport`
- No なら：Major
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`／lint `lint:L43`／実行 `test:negative_tests#txn-token-as-at`（未実装）
- 根拠：slide:p06-flow-checklist、draft-ietf-oauth-transaction-tokens-11 §12.1

**cf-07**　（項目 7）入口で検証しても、各サービスでも検証しているか（ホップごとの `validates` が空でないか）
- 見る欄：`registry:hops#validates`
- No なら：Major。詳しくは `q-gateway-bypass-path`
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L46`（未実装）
- 根拠：slide:p06-flow-checklist、slide:p06-validation-split

**cf-08**　（項目 8）利用者が送った ID 系のヘッダーを、除去してから書き込んでいるか
- 見る欄：`registry:hops#forwarded_headers`、`registry:hops#strip_inbound`
- No なら：Blocker。詳しくは `ap-2-5`
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L8`
- 根拠：slide:p06-flow-checklist

**cf-09**　（項目 9）アクセス元の文脈（IP・ネットワーク・端末）を、PEP が要求ごとに評価しているか
- 見る欄：`template:modules/M_authz_pdp#pep-pdp-inputs`
- No なら：Minor〜Major。詳しくは `q-access-context-from-pep`
- つながり：対比表 `review:contrasts/carry-vs-query#misuse`／lint `lint:L68`
- 根拠：slide:p06-flow-checklist、slide:p06-access-context

**cf-10**　（項目 10）`sub`・`act`・`txn`・承認 ID を分けて記録し、トークン全文は記録しないか
- 見る欄：`registry:claims#log_policy`、`registry:token_types#log_policy`、`template:modules/M_privacy_minimization#audit-log`
- No なら：Major。詳しくは `q-audit-correlation`・`q-token-logging`
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`／lint `lint:L45`（未実装）
- 根拠：slide:p06-flow-checklist、slide:p06-audit-trail
<!-- req:p06-flow-checklist.R1 req:p06-flow-checklist.R2 req:p06-flow-checklist.R3 req:p06-flow-checklist.R4 req:p06-flow-checklist.R5 req:p06-flow-checklist.R6 req:p06-flow-checklist.R7 req:p06-flow-checklist.R8 req:p06-flow-checklist.R9 req:p06-flow-checklist.R10 -->

### 3.2 下流ほど絞る

<a id="q-hop-narrowing"></a>

**q-hop-narrowing**　交換・作り直しのホップごとに、`aud` が 1 つの宛先に絞られ、`scope`・`authorization_details`・独自クレームが上流より広がっていないか（広がるホップには `narrowing_exception` の理由があるか）。交換を担うサービス（組織の STS・IdP）が、その規則を実際に強制する設定を書いているか（Keycloak が交換を担うなら downscope の executor など）
- 見る欄：`registry:hops#aud`、`registry:hops#scope`、`registry:hops#custom_claims`、`registry:hops#narrowing_exception`、`template:modules/M_idp_keycloak#token-exchange-downscope`
- No なら：Major（交換で権限が広がる）
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`／lint `lint:L16`／実行 `test:negative_tests#exchange-narrowing`（未実装）／事例 ケーススタディの Keycloak 26.8 の交換（元に無い orders 宛てが出た）
- 根拠：slide:p06-narrow-downstream、slide:p10-token-exchange-not-narrowing、RFC 8693 §5

<a id="q-hop-lifetime"></a>

**q-hop-lifetime**　ホップごとに、下流のトークンの寿命（`max_lifetime`）が上流のトークン以下か（Txn-Token など、上流より長いホップには `narrowing_exception` に理由があるか）
- 見る欄：`registry:hops#max_lifetime`、`registry:hops#upstream`、`registry:hops#narrowing_exception`、`template:00_core#hop-table`
- No なら：Major
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／lint `lint:L16`
- 根拠：slide:p06-narrow-downstream、draft-ietf-oauth-transaction-tokens-11 §6
<!-- req:p06-narrow-downstream.R1 -->

<a id="q-single-aud-resource"></a>

**q-single-aud-resource**　エージェント・クライアントは `resource` で宛先を要求し、出たトークンの `aud` が 1 つか
- 見る欄：`registry:token_types#aud`、`registry:hops#aud`、`template:profiles/P4_ai_agent_delegation#tool-scopes`
- No なら：Major
- つながり：対比表 `review:contrasts/scope-vs-role#misuse`／lint `lint:L56`（未実装）
- 根拠：slide:p10-agent-checklist、RFC 8707 §2
<!-- req:p10-agent-checklist.R3 -->

### 3.3 渡し方

<a id="ap-2-6"></a>

**ap-2-6**　（アンチパターン：受け取ったトークンを上流へそのまま渡す）サービス・MCP サーバー・エージェントが、受け取ったトークンを別の宛先に渡さず、宛先ごとに交換しているか
- 見る欄：`registry:hops#token_type`、`registry:hops#exchanger`、`registry:hops#aud`
- No なら：Major（代理の混乱・監査の崩壊）
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`／lint `lint:L41`（未実装）／実行 `test:negative_tests#passthrough-rejected`（未実装）／事例 MCP の認可仕様が禁じるトークンのパススルー
- 根拠：slide:p12-antipatterns-2、slide:p10-mcp-authorization、MCP Authorization 2026-07-28
<!-- req:p12-antipatterns-2.R6 -->

<a id="q-no-passthrough"></a>

**q-no-passthrough**　受け取ったトークンを渡さず、ホップごとの交換の要否と、交換を許すクライアント・割り当てる宛先・範囲を組織の規則として書いているか
- 見る欄：`registry:hops#exchanger`、`template:profiles/P4_ai_agent_delegation#delegation-policy`
- No なら：Major
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`／判断の木 `review:decision_tree#keep-sub-exchange`／lint `lint:L16`
- 根拠：slide:p10-agent-checklist、slide:p10-mcp-authorization
<!-- req:p10-agent-checklist.R4 req:p12-antipatterns-2.R6 -->

<a id="ap-2-5"></a>

**ap-2-5**　（アンチパターン：クレームをヘッダーに移し、同名ヘッダーを消さない）クレームを HTTP ヘッダーに写すホップで、利用者が送った同名のヘッダー（大文字小文字・アンダースコアの変種・重複を含む）を入口で除去し、そのヘッダーを入口だけが書けるか
- 見る欄：`registry:hops#forwarded_headers`、`registry:hops#strip_inbound`、`registry:hops#written_only_by`、`registry:claims#integrity_until`
- No なら：Blocker（なりすまし）
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L8`・`lint:L67`／実行 `test:negative_tests#spoofed-identity-header`（未実装）／事例 ガイドに事例の行なし
- 根拠：slide:p12-antipatterns-2、slide:p06-header-forwarding
<!-- req:p12-antipatterns-2.R5 -->

<a id="q-unverified-claim-extraction"></a>

**q-unverified-claim-extraction**　署名を検証せずに取り出したクレーム（ゲートウェイの `extract_only_without_validation` のような設定）を、認可に使っていないか
- 見る欄：`registry:hops#validates`、`registry:hops#forwarded_headers`
- No なら：Blocker
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`
- 根拠：slide:p06-header-forwarding
<!-- req:p06-header-forwarding.R4 -->

<a id="q-gateway-bypass-path"></a>

**q-gateway-bypass-path**　入口を通らない経路（サービス間の直接の呼び出し・管理用の口・メッセージの経路）を範囲の図に書き、その経路でも検証しているか
- 見る欄：`template:00_core#scope-boundary`、`registry:hops#validates`、`template:00_core#sequence`
- No なら：Blocker〜Major（ヘッダーだけを見るサービスに、入口を通らずに届く）
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L46`（未実装）
- 根拠：slide:p06-validation-split、slide:p06-header-forwarding
<!-- req:p06-validation-split.R8 req:p06-header-forwarding.R5 -->

<a id="q-step-up-path-coverage"></a>

**q-step-up-path-coverage**　追加認証（`acr`・`auth_time`）を求める高リスクの操作が、どの経路（直接・エージェント経由・交換の後・非同期）から呼ばれても、その操作の受け手か入口が同じ条件を確かめるか（交換・作り直しで `acr`・`auth_time` が落ちないか）
- 見る欄：`template:00_core#step-up`、`registry:hops#custom_claims`、`registry:hops#validates`
- No なら：Major（ある経路だけ追加認証を素通りする）
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`／実行 `test:negative_tests#insufficient-acr`（未実装）
- 根拠：slide:p06-step-up-approval、RFC 9470 §3

<a id="q-txn-scope-fixed"></a>

**q-txn-scope-fixed**　Txn-Token を使うなら、`tctx`（取引の内容）と `scope` が元のトークンと同じかそれ以下で決まり、受け手が `tctx` の項目を照合する規則があるか。`req_wl` を途中で書き換えないか
- 見る欄：`registry:claims#enforced_at`、`registry:claims#value_vocabulary`、`registry:hops#scope`、`template:profiles/P5_internal_propagation#txn-token`
- No なら：Major（取引の内容を経路の途中で差し替えられる）
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`／判断の木 `review:decision_tree#txn-tctx`／lint `lint:L11`／実行 `test:negative_tests#tctx-mismatch`（未実装）・`test:negative_tests#req-wl-changed`（未実装）
- 根拠：slide:p06-transaction-tokens、draft-ietf-oauth-transaction-tokens-11 §12.2

<a id="q-txn-required-claims"></a>

**q-txn-required-claims**　Txn-Token を使うなら、草案が必須とするクレーム（`iat`・`aud`・`exp`・`txn`・`sub`・`scope`・`req_wl`）が目録の `required_claims` にあり、台帳のそれぞれの行の `carried_in` に Txn-Token があるか
- 見る欄：`registry:token_types#required_claims`、`registry:claims#carried_in`
- No なら：Major（前提の誤り）。較正で追加（B02。templates/examples/scenario-b/review-report.md の 9.）
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`／lint `lint:L7`
- 根拠：draft-ietf-oauth-transaction-tokens-11 §9.2、slide:p06-transaction-tokens

<a id="q-claim-earliest-hop"></a>

**q-claim-earliest-hop**　独自クレーム（承認の ID・取引の内容など）を、その値が初めて分かるホップのトークンから載せ、下流のホップはその部分集合になっているか（交換・作り直しで初めて足して、上流との比較を外していないか）
- 見る欄：`registry:hops#custom_claims`、`registry:hops#upstream`、`registry:claims#carried_in`
- No なら：Major（候補の漏れ）。足すホップと載せるホップの両方の案を比べた跡を求める。較正で追加（B04。templates/examples/scenario-b/review-report.md の 9.）
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`／lint `lint:L16`
- 根拠：slide:p06-narrow-downstream、slide:p10-human-approval-evidence

<a id="ap-2-9"></a>

**ap-2-9**　（アンチパターン：署名がなく、取り消せず、ログも残らない内部の代理トークン）内部の代理・委任のトークンが、署名され、テナントを検証され、失効でき、ログに残るか
- 見る欄：`registry:token_types#signing`、`registry:token_types#revocation`、`registry:token_types#tenant_binding`、`registry:token_types#log_policy`
- No なら：Blocker
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`／lint `lint:L17`・`lint:L9`／事例 CVE-2025-55241（Entra の Actor token）
- 根拠：slide:p12-antipatterns-2、slide:p10-delegation-chain-depth、slide:p00-incident-signature-valid
<!-- req:p12-antipatterns-2.R9 -->

<a id="q-internal-delegation-token"></a>

**q-internal-delegation-token**　内部の代理トークンにも、署名・期限・テナントの照合・失効の手段・ログの扱いが、目録の行として書いてあるか（「内部だから」で省いていないか）
- 見る欄：`registry:token_types#signing`、`registry:token_types#max_lifetime`、`registry:token_types#tenant_binding`、`registry:token_types#revocation`
- No なら：Blocker〜Major
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`／lint `lint:L9`・`lint:L17`／実行 `test:negative_tests#tenant-mismatch`（未実装）／事例 CVE-2025-55241
- 根拠：slide:p00-incident-signature-valid、slide:p10-delegation-chain-depth
<!-- req:p00-incident-signature-valid.R2 req:p10-delegation-chain-depth.R5 req:p12-antipatterns-2.R9 -->

<a id="ap-2-7"></a>

**ap-2-7**　（アンチパターン：エージェントが利用者のトークンを借りる）エージェントは利用者のトークンを借りず、`act` で委任を表したトークンを交換で得ているか
- 見る欄：`registry:questions#q-actor`、`template:profiles/P4_ai_agent_delegation#delegation-mode`
- No なら：Major（誰が実行したか分からない）
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`／判断の木 `review:decision_tree#keep-sub-exchange`／lint `lint:L55`（未実装）／事例 ガイドに事例の行なし
- 根拠：slide:p12-antipatterns-2、slide:p10-agent-identity
<!-- req:p12-antipatterns-2.R7 -->

<a id="q-delegation-depth-and-revocation"></a>

**q-delegation-depth-and-revocation**　委任の深さの上限（`max_delegation_depth`）と、根元の承認からの一括失効の手段が書いてあるか（深さが 2 以上なら専門家に回したか）
- 見る欄：`registry:token_types#max_delegation_depth`、`template:profiles/P4_ai_agent_delegation#delegation-depth`、`template:profiles/P4_ai_agent_delegation#chain-revocation`
- No なら：Major。深さが 2 以上は `review:escalation#delegation-depth`
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`／lint `lint:L59`（未実装）
- 根拠：slide:p10-delegation-chain-depth、slide:p10-agent-checklist
<!-- req:p10-agent-checklist.R8 -->

<a id="q-idp-diff-absorbed"></a>

**q-idp-diff-absorbed**　IdP ごとの差（利用者のキー・ロールの位置・`aud`）を、入口か共通部品で吸収し、内側のサービスが読むのは組織の発行者が出した組織の名前空間のクレームだけか（製品の独自クレーム `xms_*` などを組織の契約にしていないか）
- 見る欄：`template:profiles/P5_internal_propagation#edge-conversion`、`registry:claims#upstream_issuer`、`registry:claims#issuers`
- No なら：Major
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`／lint `lint:L32`（未実装）
- 根拠：slide:p11-translation-layer、slide:p10-vendor-features、slide:p03-absorb-idp-differences
<!-- req:p10-vendor-features.R1 req:p11-translation-layer.R1 req:p11-translation-layer.R5 -->

<a id="q-token-not-in-url"></a>

**q-token-not-in-url**　URL・クエリ・リダイレクトの断片にトークンを載せていないか（WebSocket など、ヘッダーを付けられない経路の扱いが書いてあるか）
- 見る欄：`registry:token_types#transport`、`template:profiles/P1_human_web#url-exposure`
- No なら：Major（履歴とログに残る）
- つながり：対比表 `review:contrasts/jws-vs-jwe#misuse`／lint `lint:L54`（未実装）
- 根拠：slide:p09-url-browser、slide:p09-checklist、RFC 9700 §4.3.2
<!-- req:p09-checklist.R6 -->

---

<a id="stage-validation"></a>

## 4. 検証：受け手がトークンを受け入れる条件

**誰が確かめるか**：受け手（各サービスの担当と、共通の検証部品の持ち主）。受け手が複数あるときは、受け手ごとに答えます（筆者の提案：段ごとの担当の割り当て（追跡 #5））。

| スライド 148 の観点 | この段の問い |
| --- | --- |
| 共通の検証部品を使うか | `q-shared-validator` |
| alg・iss・aud・exp・typ | `ap-1-1`・`ap-1-3`・`ap-1-5`・`ap-1-8`・`q-typ-distinguishes` |
| 必須クレームの欠落は拒否 | `q-required-rejected`・`dc-12` |

根拠：slide:p12-review-viewpoints、slide:p01-validation-order
<!-- req:p12-review-viewpoints.R10 req:p12-review-viewpoints.R11 req:p12-review-viewpoints.R12 -->

<a id="q-shared-validator"></a>

**q-shared-validator**　受け手のすべてが、アルゴリズム・発行者・宛先・必須クレームを固定した組織の共通の検証部品で検証し、受け手ごとの独自の設定・読み方をしていないか
- 見る欄：`template:modules/M_token_validation#shared-validator`、`template:modules/M_token_validation#library-config`
- No なら：Major
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L17`
- 根拠：slide:p00-why-hard、slide:p01-library-defaults
<!-- req:p00-why-hard.R2 req:p01-library-defaults.R4 -->

<a id="ap-1-1"></a>

**ap-1-1**　（アンチパターン：トークンの alg に従って検証する）受け手は、トークンの `alg` ではなく、目録の許可リスト（鍵ごとに 1 つ）で検証の方式を決めているか
- 見る欄：`registry:token_types#alg_allowlist`、`template:modules/M_token_validation#alg`
- No なら：Blocker（`none`・HS256 の混同で偽造）
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L17`／実行 `test:negative_tests#alg-none`（未実装）・`test:negative_tests#alg-confusion`（未実装）／事例 CVE-2015-9235
- 根拠：slide:p12-antipatterns-1、slide:p01-dangerous-header-params、RFC 8725 §3.1
<!-- req:p12-antipatterns-1.R1 -->

<a id="ap-1-2"></a>

**ap-1-2**　（アンチパターン：署名を確かめずに中身で認可する）どの受け手も、署名を検証してからクレームを読むか（デコードだけの経路が無いか）
- 見る欄：`registry:hops#validates`、`template:modules/M_token_validation#validation-order`
- No なら：Blocker（誰でもクレームを書ける）
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L46`（未実装）／事例 ガイドに事例の行なし（スライドの事例の欄は「—」）
- 根拠：slide:p12-antipatterns-1、slide:p01-validation-order
<!-- req:p12-antipatterns-1.R2 -->

<a id="q-validate-before-read"></a>

**q-validate-before-read**　受け入れの確認（署名・`iss`・`aud`・`exp`・`typ`）を全部通る前に、テナント・権限の独自クレームを読む実装（ログ出し・ルーティングを含む）が無いか
- 見る欄：`template:modules/M_token_validation#validation-order`
- No なら：Blocker〜Major
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`
- 根拠：slide:p01-validation-order、slide:p01-attack-patterns
<!-- req:p01-validation-order.R9 req:p01-attack-patterns.R7 -->

<a id="ap-1-3"></a>

**ap-1-3**　（アンチパターン：aud を確かめない）`aud` を必須（`required_claims`）にし、受け手が自分の ID を含むかを確かめるか
- 見る欄：`registry:token_types#required_claims`、`registry:token_types#aud`、`template:modules/M_token_validation#audience`
- No なら：Blocker（別サービス宛てのトークンの流用）
- つながり：対比表 `review:contrasts/id-vs-access-token#misuse`／lint `lint:L27`／実行 `test:negative_tests#aud-wrong`（未実装）／事例 CVE-2020-26160
- 根拠：slide:p12-antipatterns-1、RFC 8725 §3.9
<!-- req:p12-antipatterns-1.R3 -->

<a id="ap-1-4"></a>

**ap-1-4**　（アンチパターン：マルチテナントで iss・tid を見ない）受け手は、発行者（`iss`）とテナントの許可リストで照合するか
- 見る欄：`registry:token_types#issuers`、`registry:token_types#tenant_binding`、`template:modules/M_multitenancy#tenant-determination`
- No なら：Blocker（別テナントのトークンを受理）
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`／lint `lint:L9`／実行 `test:negative_tests#tenant-mismatch`（未実装）／事例 CVE-2025-55241
- 根拠：slide:p12-antipatterns-1、slide:p05-multitenancy
<!-- req:p12-antipatterns-1.R4 -->

<a id="ap-1-5"></a>

**ap-1-5**　（アンチパターン：署名が通れば発行者も正しいと仮定する）受け手は、検証に使った鍵がその `iss` の鍵（その発行者の JWKS）であることを確かめるか
- 見る欄：`registry:token_types#issuers`、`registry:token_types#jwks_uri`、`registry:token_types#key_source`、`template:modules/M_token_validation#issuer`
- No なら：Blocker（別系統の鍵の署名を受理）
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L25`／実行 `test:negative_tests#untrusted-key`（未実装）／事例 Storm-0558（CSRB 報告書 2024-03）
- 根拠：slide:p12-antipatterns-1、slide:p00-incident-signature-valid、CSRB 報告書（Storm-0558）勧告 6
<!-- req:p12-antipatterns-1.R5 -->

<a id="ap-1-8"></a>

**ap-1-8**　（アンチパターン：exp を必須にしない・ずれを大きく許す）`exp` を必須にし、時刻のずれの許容（`max_clock_skew`）が数分（300 秒）以内か
- 見る欄：`registry:token_types#required_claims`、`registry:token_types#max_clock_skew`、`template:modules/M_token_validation#time`
- No なら：Major（期限のないトークン）
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／lint `lint:L27`／実行 `test:negative_tests#expired`（未実装）／事例 golang-jwt v5 の既定（exp が無くても通る）
- 根拠：slide:p12-antipatterns-1、RFC 7519 §4.1.4
<!-- req:p12-antipatterns-1.R8 -->

<a id="q-typ-distinguishes"></a>

**q-typ-distinguishes**　種類の違うトークン（ID トークン・AT・Logout Token・Txn-Token・クライアントが作る JWT）を、受け手が `typ` と `aud` で区別し、ID トークンを API で受け入れないか
- 見る欄：`registry:token_types#typ`、`registry:token_types#aud`、`template:modules/M_token_validation#typ`
- No なら：Major
- つながり：対比表 `review:contrasts/id-vs-access-token#misuse`／lint `lint:L27`／実行 `test:negative_tests#typ-wrong`（未実装）
- 根拠：slide:p01-id-token-vs-access-token、slide:p01-client-made-jwts、RFC 9068 §2.1

<a id="q-required-rejected"></a>

**q-required-rejected**　必須のクレームが欠けたトークンを拒否し、誤拒否を避けるために必須の確認や宛先の確認を外していないか（IdP の差は入口で埋めてから当てているか）
- 見る欄：`registry:token_types#required_claims`、`registry:claims#on_missing`、`template:profiles/P5_internal_propagation#edge-conversion`
- No なら：Major
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L7`／実行 `test:negative_tests#missing-required`（未実装）・`test:negative_tests#legit-idp-variants-accepted`（未実装）
- 根拠：slide:p04-reject-missing-required、slide:p04-forward-compatibility

<a id="q-no-unverified-passthrough-mode"></a>

**q-no-unverified-passthrough-mode**　検証の無効化・デバッグ・「欠けたら既定値で続行」のような、未検証の値を流すモードが、設定・実装のどこにも無いか
- 見る欄：`template:modules/M_token_validation#library-config`、`template:claim_request#q18`
- No なら：Blocker〜Major
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`
- 根拠：slide:p11-pre-add-questions-2、slide:p01-library-defaults
<!-- req:p11-pre-add-questions-2.R6 -->

<a id="q-consumer-expression"></a>

**q-consumer-expression**　受け手の式（ゲートウェイ・ポリシー言語・コード）で、値を変換せず完全一致で比べ、真偽値は `true` と明示的に比べ、欠落時に通す既定値（`orValue(true)` など）を使っていないか
- 見る欄：`registry:claims#enforced_at`、`registry:claims#value_normalization`、`registry:claims#on_missing`
- No なら：Major
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／実行 `test:negative_tests#case-variant`（未実装）
- 根拠：slide:p04-shape、slide:p04-case-and-characters
<!-- req:p04-shape.R4 req:p04-case-and-characters.R3 -->

<a id="q-nested-jwt-both-layers"></a>

**q-nested-jwt-both-layers**　暗号化する（JWE の）トークンで、「署名してから暗号化」のネストにし、内側の JWS の署名と発行者も検証するか
- 見る欄：`registry:token_types#jwe`、`template:modules/M_token_validation#nested-jwt`
- No なら：Blocker（復号できれば中身を信じる受け手が出る）
- つながり：対比表 `review:contrasts/jws-vs-jwe#misuse`／lint `lint:L66`／実行 `test:negative_tests#nested-inner-unsigned`（未実装）
- 根拠：slide:p09-checklist、slide:p09-jwe-sd-jwt、RFC 8725 §3.3
<!-- req:p09-checklist.R5 -->

<a id="q-unwrapped-value-authz"></a>

**q-unwrapped-value-authz**　署名の保護が外れた後の値（ヘッダーに写した値・DB のセッション変数・キャッシュ・ログから読み戻した値）を認可に使うなら、その写し先を書けるのが入口・注入者だけだと宣言しているか
- 見る欄：`registry:claims#integrity_until`、`registry:claims#trust_boundary`、`registry:hops#written_only_by`
- No なら：Blocker〜Major
- つながり：対比表 `review:contrasts/jws-vs-jwe#misuse`／lint `lint:L67`
- 根拠：slide:p06-header-forwarding、slide:p07-trust-boundary

---

<a id="stage-authorization"></a>

## 5. 認可：クレームを判断にどう使うか

**誰が確かめるか**：受け手（PEP・PDP・データ層の担当）。データ層（DB の文脈・行単位の制御）は、DB の担当が確かめます（筆者の提案：段ごとの担当の割り当て（追跡 #5））。

| スライド 148 の観点 | この段の問い |
| --- | --- |
| オブジェクト単位は DB で確認 | `q-object-level-authz` |
| テナントを保存データと照合 | `q-tenant-data-match`・`ap-1-4` |
| 書き手で値を区別 | `q-writer-distinguished`・`ap-1-7`・`dc-10` |

根拠：slide:p12-review-viewpoints、slide:p05-bola、slide:p04-split-by-writer
<!-- req:p12-review-viewpoints.R13 req:p12-review-viewpoints.R14 req:p12-review-viewpoints.R15 -->

<a id="q-object-level-authz"></a>

**q-object-level-authz**　利用者が指定した ID でデータを取り出すすべての処理で、オブジェクトの持ち主・テナントを、トークンの `sub`・テナントとデータの側で照合しているか（ゲートウェイ・WAF やクレームで代用していないか）。照合に使うキー（`sub` か組織の `user_id` か）が 1 つに決まっているか
- 見る欄：`template:modules/M_authz_pdp#object-level`、`template:modules/M_multitenancy#data-layer-filter`、`registry:claims#enforced_at`
- No なら：Blocker（BOLA）
- つながり：対比表 `review:contrasts/carry-vs-query#misuse`／実行 `test:negative_tests#bola-other-owner`（未実装）
- 根拠：slide:p05-bola、slide:p06-validation-split、OWASP API Security Top 10 2023 API1
<!-- req:p05-bola.R2 req:p05-bola.R4 req:p06-validation-split.R5 -->

<a id="q-tenant-data-match"></a>

**q-tenant-data-match**　トークンのテナントを、保存されたデータのテナント（行の列・RLS の条件）と照合しているか
- 見る欄：`template:modules/M_multitenancy#data-layer-filter`、`registry:claims#enforced_at`
- No なら：Blocker
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`／lint `lint:L9`
- 根拠：slide:p05-multitenancy、slide:p12-review-viewpoints

<a id="q-writer-distinguished"></a>

**q-writer-distinguished**　同じ意味の値でも、書き手（IdP の管理者・本人・テナントの管理者・呼び出し側）で別のクレームか別の列に分け、受け手が確認済みの値だけで認可しているか
- 見る欄：`registry:claims#provenance`、`registry:claims#authoritative_writer`、`registry:claims#modifiers`
- No なら：Blocker〜Major
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L31`
- 根拠：slide:p04-split-by-writer

<a id="q-validity-not-authz"></a>

**q-validity-not-authz**　「トークンが有効か」だけで認可せず、操作・対象・提示された文脈も判断に使っているか
- 見る欄：`template:modules/M_authz_pdp#pep-pdp-inputs`、`registry:claims#enforced_at`
- No なら：Major
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L11`
- 根拠：slide:p05-pep-pdp、NIST IR 8587 §4.1.4
<!-- req:p05-pep-pdp.R3 -->

<a id="q-original-principal"></a>

**q-original-principal**　内部の呼び出しでも、元の利用者の権限で判断し、仲介するサービスの広い権限で下流に依頼していないか
- 見る欄：`registry:questions#q-sub`、`registry:hops#token_type`、`template:profiles/P5_internal_propagation#service-to-service`
- No なら：Major（代理の混乱）
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`／判断の木 `review:decision_tree#keep-sub-exchange`
- 根拠：slide:p05-one-request-carries、slide:p05-confused-deputy、ASVS v5.0.0-8.3.3
<!-- req:p05-one-request-carries.R3 req:p05-confused-deputy.R3 -->

<a id="q-authorize-service-and-user"></a>

**q-authorize-service-and-user**　呼び出し元のサービス（直接の通信相手）と利用者を、それぞれ認可しているか（直接の相手は mTLS・SPIFFE など通信の層で確かめているか）
- 見る欄：`template:profiles/P5_internal_propagation#service-to-service`、`registry:questions#q-peer`
- No なら：Major
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`／判断の木 `review:decision_tree#peer-mtls`
- 根拠：slide:p06-validation-split、slide:p05-one-request-carries
<!-- req:p06-validation-split.R7 -->

<a id="q-scope-and-role"></a>

**q-scope-and-role**　受け手が `scope`（クライアントに委ねた範囲）と `role`（利用者に許した範囲）の両方を確かめているか
- 見る欄：`registry:claims#enforced_at`、`registry:hops#scope`
- No なら：Major
- つながり：対比表 `review:contrasts/scope-vs-role#misuse`
- 根拠：slide:p05-scope-vs-role
<!-- req:p05-scope-vs-role.R1 -->

<a id="q-access-context-from-pep"></a>

**q-access-context-from-pep**　「今どこから来たか」（IP・ネットワーク・端末）の判断を、トークンのクレームや `X-Forwarded-For` のような偽装できるヘッダーでなく、PEP が要求ごとに接続から得た値で行っているか
- 見る欄：`template:modules/M_authz_pdp#pep-pdp-inputs`、`registry:claims#data_category`
- No なら：Minor〜Major
- つながり：対比表 `review:contrasts/carry-vs-query#misuse`／lint `lint:L5`・`lint:L68`
- 根拠：slide:p06-access-context、slide:p09-do-not-carry
<!-- req:p06-access-context.R1 req:p06-access-context.R4 req:p06-flow-checklist.R9 req:p09-do-not-carry.R6 -->

<a id="q-step-up-by-rs"></a>

**q-step-up-by-rs**　高リスクの操作で、受け手が `acr`・`auth_time` を見て追加認証を求め（足りなければ `insufficient_user_authentication`）、追加認証の起動をクレームの値に任せていないか
- 見る欄：`template:00_core#step-up`、`registry:questions#q-auth-strength`
- No なら：Major
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／実行 `test:negative_tests#insufficient-acr`（未実装）
- 根拠：slide:p06-step-up-approval、RFC 9470 §3
<!-- req:p06-step-up-approval.R2 -->

<a id="q-approval-from-as"></a>

**q-approval-from-as**　機微な操作の承認の有無を、エージェントやクライアントに判断させず、AS が本人に確かめた結果（CIBA・RAR の承認 ID）を受け手が照合しているか。承認の記録の置き場所（トークンか、受け手が引く台帳か）を候補から比べて選んだか
- 見る欄：`template:profiles/P4_ai_agent_delegation#human-approval`、`registry:claims#enforced_at`
- No なら：Major
- つながり：対比表 `review:contrasts/scope-vs-role#misuse`／実行 `test:negative_tests#approval-mismatch`（未実装）
- 根拠：slide:p10-human-approval-evidence、slide:p10-agent-checklist、RFC 9396 §2
<!-- req:p10-human-approval-evidence.R1 req:p10-agent-checklist.R7 -->

<a id="q-cross-tenant-identity"></a>

**q-cross-tenant-identity**　テナントをまたいだ暗黙の名寄せ（`idp` クレームや email での突き合わせ）をせず、テナントをまたぐ利用者には組織が決めたリンクのキーを使っているか
- 見る欄：`template:modules/M_multitenancy#cross-tenant`、`registry:claims#usage`
- No なら：Major
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`
- 根拠：slide:p05-cross-tenant
<!-- req:p05-cross-tenant.R2 -->

<a id="q-operator-act"></a>

**q-operator-act**　運用者の操作は、交換で得た委任のトークン（`sub` に利用者、`act` に運用者）で行い、運用者が利用者として振る舞っていないか
- 見る欄：`template:00_core#system-privileges`、`registry:questions#q-actor`
- No なら：Major（監査で運用者の操作が利用者の操作に見える）
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`
- 根拠：slide:p05-system-privileges、RFC 8693 §4.1
<!-- req:p05-system-privileges.R3 -->

<a id="q-break-glass"></a>

**q-break-glass**　緊急時の特権（break-glass）で、承認の ID（RAR・CIBA）と短い期限を確かめるか
- 見る欄：`template:00_core#system-privileges`
- No なら：Major
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`
- 根拠：slide:p05-system-privileges、RFC 8693 §4.4
<!-- req:p05-system-privileges.R5 -->

### 5.1 データ層の規則（スライド 101：10 項目）

<a id="checklist-p07-data-layer"></a>

DB・ブローカーに届くホップ（`hops.yaml` の `db_connection` など）と、データ層のモジュール（`template:modules/M_data_layer#db-context-setter` ほか）について確かめます。どの項目も、製品の既定値に任せず、設計書に書いて試験で確かめることを求めます（`cd-11`）。

**cd-01**　（項目 1）DB の文脈を設定するのは、検証済みのトークンを受けた注入者だけか
- 見る欄：`template:modules/M_data_layer#db-context-setter`
- No なら：Blocker。詳しくは `q-db-context-writers`
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`
- 根拠：slide:p07-data-layer-checklist、slide:p07-trust-boundary

**cd-02**　（項目 2）PostgreSQL では `SET LOCAL` か `set_config(…, true)` で、取引の単位で設定するか
- 見る欄：`template:modules/M_data_layer#pool-context`
- No なら：Blocker（前の利用者の文脈が残る）
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／実行 `test:negative_tests#pool-context-leak`（未実装）
- 根拠：slide:p07-data-layer-checklist、slide:p07-connection-pool

**cd-03**　（項目 3）SQL Server では `@read_only = 1` と接続主体の確認をするか
- 見る欄：`template:modules/M_data_layer#pool-context`
- No なら：Blocker
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／実行 `test:negative_tests#db-context-override`（未実装）
- 根拠：slide:p07-data-layer-checklist

**cd-04**　（項目 4）認可には、本人が書き換えられない属性だけを使うか
- 見る欄：`registry:claims#provenance`
- No なら：Blocker。詳しくは `ap-1-7`
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L31`
- 根拠：slide:p07-data-layer-checklist

**cd-05**　（項目 5）DB のロールを選ぶクレームを高権限として扱い、発行元を限定しているか
- 見る欄：`registry:claims#issuers`、`registry:claims#data_category`
- No なら：Major
- つながり：対比表 `review:contrasts/scope-vs-role#misuse`／lint `lint:L48`（未実装）
- 根拠：slide:p07-data-layer-checklist、slide:p07-masking

**cd-06**　（項目 6）RLS をすり抜ける主体（スーパーユーザー・`BYPASSRLS`・テーブルの所有者・SECURITY DEFINER の関数）を、通常の経路から外しているか
- 見る欄：`template:modules/M_data_layer#masking-rls-bypass`
- No なら：Blocker（シナリオ A の A04）
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`
- 根拠：slide:p07-data-layer-checklist、slide:p07-row-level-security

**cd-07**　（項目 7）DB のユーザーの対応付けは、名前でなく不変の ID で行うか
- 見る欄：`template:modules/M_data_layer#db-identity`
- No なら：Major
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`
- 根拠：slide:p07-data-layer-checklist

**cd-08**　（項目 8）トークンと接続の寿命を分け、プールの接続の最大寿命（`connection_max_lifetime`）と、剥奪を開いた接続に届かせる手段を決めたか
- 見る欄：`registry:hops#connection_max_lifetime`、`template:00_core#lifecycle-db-connection`
- No なら：Major
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／lint `lint:L49`（未実装）
- 根拠：slide:p07-data-layer-checklist、slide:p07-lifetime-mismatch

**cd-09**　（項目 9）利用者単位の監査が要るなら、利用者の ID を DB まで伝えているか
- 見る欄：`template:modules/M_data_layer#db-identity`
- No なら：Minor〜Major
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`
- 根拠：slide:p07-data-layer-checklist

**cd-10**　（項目 10）クレーム・文脈が欠けたら全件を許さず拒否し（文脈なしで 0 行）、DDM・RLS だけに頼っていないか
- 見る欄：`template:modules/M_data_layer#db-context-setter`、`registry:claims#on_missing`
- No なら：Blocker（シナリオ A の A13）。詳しくは `q-ddm-rls-only`
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L7`
- 根拠：slide:p07-data-layer-checklist

**cd-11**　データ層の設定（文脈の設定・すり抜ける主体・接続の寿命）を製品の既定値に任せず、設計書に書き、試験で確かめる計画があるか
- 見る欄：`template:modules/M_data_layer#masking-rls-bypass`、`template:modules/M_data_layer#connection-lifetime`
- No なら：Major
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／実行 `test:negative_tests#pool-context-leak`（未実装）・`test:negative_tests#db-context-override`（未実装）
- 根拠：slide:p07-data-layer-checklist
<!-- req:p07-data-layer-checklist.R1 req:p07-data-layer-checklist.R2 req:p07-data-layer-checklist.R3 req:p07-data-layer-checklist.R4 req:p07-data-layer-checklist.R5 req:p07-data-layer-checklist.R6 req:p07-data-layer-checklist.R7 req:p07-data-layer-checklist.R8 req:p07-data-layer-checklist.R9 req:p07-data-layer-checklist.R10 req:p07-data-layer-checklist.R11 -->

<a id="q-db-context-writers"></a>

**q-db-context-writers**　DB の文脈を設定する注入者以外が、同じ接続・取引で任意の SQL を流せないか（`RESET ROLE` などで戻せる経路が無いか）
- 見る欄：`template:modules/M_data_layer#db-context-setter`、`template:00_core#scope-boundary`
- No なら：Blocker
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`
- 根拠：slide:p07-three-db-paths、slide:p07-trust-boundary
<!-- req:p07-three-db-paths.R3 req:p07-trust-boundary.R1 -->

<a id="q-sql-tenant-predicate"></a>

**q-sql-tenant-predicate**　セッション変数やサービスの ID で分離するなら、全 SQL に明示的なテナントの条件を付ける規約と、それを確かめるレビューか検査があるか
- 見る欄：`template:modules/M_data_layer#db-context-setter`、`template:modules/M_multitenancy#data-layer-filter`
- No なら：Major
- つながり：対比表 `review:contrasts/name-vs-identifier#misuse`
- 根拠：slide:p07-trust-boundary、slide:p07-connect-as-whom
<!-- req:p07-trust-boundary.R2 req:p07-connect-as-whom.R3 -->

<a id="q-db-context-parameterized"></a>

**q-db-context-parameterized**　DB の文脈の値を、文字列の連結でなくパラメータで渡しているか（`SET LOCAL` はバインド変数を受けないので、`set_config($1, $2, true)` を使うか）
- 見る欄：`template:modules/M_data_layer#pool-context`
- No なら：Blocker（SQL インジェクション）。シナリオ A の A12
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`
- 根拠：slide:p07-connection-pool
<!-- req:p07-connection-pool.R4 -->

<a id="q-ddm-rls-only"></a>

**q-ddm-rls-only**　機微なデータを DDM・RLS だけで守らず、最小権限と監査を併用しているか
- 見る欄：`template:modules/M_data_layer#masking-rls-bypass`
- No なら：Major
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`
- 根拠：slide:p07-masking、slide:p07-data-layer-checklist
<!-- req:p07-masking.R2 req:p07-data-layer-checklist.R10 -->

---

<a id="stage-operations"></a>

## 6. 運用：鍵・寿命・失効・ログ・変更

**誰が確かめるか**：運用（鍵の更新・IdP とフックの障害・JWKS・ログ・台帳の変更の手順の担当）。寿命と失効は、受け手の担当も確かめます（筆者の提案：段ごとの担当の割り当て（追跡 #5））。

| スライド 148 の観点 | この段の問い |
| --- | --- |
| 変更の手順と互換期間 | `q-change-order`・`q-deprecated-deadline`・`pa-23`・`pa-24` |
| トークン全文をログに残さない | `ap-2-8`・`q-token-logging` |
| 失効の伝え方 | `q-revocation-delivery` |

根拠：slide:p12-review-viewpoints、slide:p11-change-procedure、slide:p08-revocation-propagation
<!-- req:p12-review-viewpoints.R16 req:p12-review-viewpoints.R17 req:p12-review-viewpoints.R18 -->

### 6.1 寿命（Part 8）

寿命の問いは、まず 4 つの層のどの層の話かを決めてから答えます（対比表 `review:contrasts/four-lifetimes#table`）。

<a id="q-four-lifetimes-written"></a>

**q-four-lifetimes-written**　独自クレームごとに、寿命の 4 つの層（トークン・値の鮮度・セッションと RT・定義）が別々の欄に書いてあるか（1 つの数字で語っていないか）
- 見る欄：`template:00_core#lifecycle`、`template:00_core#freshness`、`template:00_core#definition-lifecycle`、`registry:token_types#max_lifetime`
- No なら：Minor〜Major
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／lint `lint:L23`
- 根拠：slide:p08-four-lifetimes、slide:p08-token-types-lifetimes

<a id="q-lifetime-rationale"></a>

**q-lifetime-rationale**　種類ごとの寿命の上限が組織の規則（`lifetime-policy`）の中にあり、「剥奪をどれだけ早く効かせたいか」から数字を導いた理由（短くする利点と、リフレッシュの負荷・IdP 停止の影響という代償の比較）が書いてあるか
- 見る欄：`template:00_core#lifetime-policy`、`registry:token_types#lifetime_refs`、`registry:token_types#lifetime_exception`
- No なら：Minor〜Major。書籍の「まず 30 分」のような根拠のない目安を規範として引いていたら Minor
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／判断の木 `review:decision_tree#lifetime-by-situation`／lint `lint:L23`
- 根拠：slide:p08-choosing-lifetime、slide:p08-decision-table、NIST IR 8587 §5.3.1.1

<a id="q-session-rt-bounds"></a>

**q-session-rt-bounds**　セッションと RT に、無操作の上限（idle）と絶対的な上限の両方があり、対話用の RT が再認証の上限（AAL2 なら 24 時間）を超えないか
- 見る欄：`registry:token_types#idle_timeout`、`registry:token_types#max_lifetime`、`registry:token_types#rt_rotation`
- No なら：Major（シナリオ A の A14）
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／lint `lint:L23`・`lint:L15`
- 根拠：slide:p08-token-types-lifetimes、NIST SP 800-63B-4 §2.2.3

<a id="q-rt-policy-by-client"></a>

**q-rt-policy-by-client**　RT の方式が、クライアントの種類に合っているか（公開クライアントはローテーション＋再利用検知か送信者制約、FAPI 対象の機密クライアントは送信者制約でローテーションなし）。理由が別の種類のクライアントの根拠を引いていないか
- 見る欄：`registry:token_types#issuance_profile`、`registry:token_types#rt_strategy`、`registry:token_types#reuse_detection`
- No なら：Major（シナリオ A の A16）
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／判断の木 `review:decision_tree#lifetime-by-situation`／lint `lint:L15`／実行 `test:negative_tests#rt-reuse`（未実装）
- 根拠：slide:p08-rotation、RFC 9700 §4.14.2

<a id="q-freshness-mitigation"></a>

**q-freshness-mitigation**　寿命（受け入れの上限＝`max_lifetime`＋`max_clock_skew`）が鮮度の許容時間（`volatility`）を超えるクレームのすべてに、対策（寿命を縮める・都度問い合わせる・失効を伝える・再発行の契機）が書いてあり、その対策の担い手（どの受け手が問い合わせるか）が書いてあるか
- 見る欄：`template:00_core#freshness`、`registry:claims#volatility`、`registry:claims#on_revoke`、`registry:claims#recompute_trigger`
- No なら：Major
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／判断の木 `review:decision_tree#carry-or-query`／lint `lint:L5`
- 根拠：slide:p04-token-is-snapshot、slide:p08-stale-claims、slide:p08-reissue-triggers
<!-- req:p04-token-is-snapshot.R1 req:p08-stale-claims.R2 req:p12-antipatterns-2.R2 -->

<a id="q-refresh-reevaluated"></a>

**q-refresh-reevaluated**　「リフレッシュで値が再計算される」を前提にした行で、その IdP の挙動を実測か文書で確かめた記録があるか（外部 IdP の属性の取り込みが初回だけか毎回かが書いてあるか）
- 見る欄：`template:00_core#lifecycle`、`template:00_core#uncertain`、`registry:claims#recompute_trigger`
- No なら：Major（再計算されない IdP では、古さの上限が RT の寿命になる）
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`
- 根拠：slide:p08-refresh-reevaluation、slide:p08-reissue-triggers

<a id="q-revocation-delivery"></a>

**q-revocation-delivery**　トークン種別ごとに、剥奪・失効がどの手段（exp まで待つ・イントロスペクション・状態リスト・SSF/CAEP・Back-Channel Logout・DB 側の主体の削除）で届き、受け手が止めるまでの最悪の秒数が書いてあるか。すぐ止めたい操作は、参照型か問い合わせで判断しているか
- 見る欄：`registry:token_types#revocation`、`template:00_core#lifecycle`、`template:00_core#lifecycle-db-connection`、`registry:claims#on_revoke`
- No なら：Major。代わりの手段のないまま候補（Back-Channel Logout など）を却下していたら Major（シナリオ A の A03）
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／判断の木 `review:decision_tree#lifetime-by-situation`／実行 `test:negative_tests#revocation-latency`（未実装）・`test:negative_tests#revoked-token-rejected`（未実装）
- 根拠：slide:p08-revocation-propagation、slide:p08-logout、slide:p01-self-contained-vs-reference、slide:p07-lifetime-mismatch
<!-- req:p01-self-contained-vs-reference.R3 req:p03-cognito-token-use.R6 req:p07-lifetime-mismatch.R3 req:p08-four-lifetimes.R2 req:p08-revocation-propagation.R1 req:p12-review-viewpoints.R18 -->

<a id="q-external-user-deprovision"></a>

**q-external-user-deprovision**　外部の IdP・取引先から来た利用者の停止・ロールの剥奪が、どの経路（上流のイベント・取り込みの同期・入口の照会）で何秒以内に組織の受け手まで届くかが書いてあるか（上流で止めても、組織の発行したトークンとセッションが残らないか）
- 見る欄：`template:00_core#lifecycle`、`registry:claims#upstream_issuer`、`registry:claims#volatility`、`template:modules/M_idp_keycloak#broker-mapping`
- No なら：Major
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／実行 `test:negative_tests#disabled-subject-exchange`（未実装）
- 根拠：slide:p08-reissue-triggers、slide:p08-revocation-propagation

<a id="q-relies-on-at-expiry"></a>

**q-relies-on-at-expiry**　AT の期限を当てにした実装（「期限が切れれば剥奪が効く」前提の判断や、残りの期限を使ったキャッシュの寿命）が無いか
- 見る欄：`template:00_core#lifecycle`、`registry:claims#on_revoke`
- No なら：Major
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`
- 根拠：slide:p08-choosing-lifetime
<!-- req:p08-choosing-lifetime.R3 -->

<a id="q-long-running"></a>

**q-long-running**　長時間の処理・非同期の処理で、利用者のトークンや RT（`offline_access`）をキュー・ジョブに保持せず、ワーカーが自分のワークロード ID で交換し、`sub`＝利用者・`act`＝自分の分単位のトークンを作り直しているか。可否を作り直しのたびに AS が決めるか
- 見る欄：`registry:token_types#long_running`、`template:00_core#lifecycle`、`template:profiles/P5_internal_propagation#async-messaging`
- No なら：Major（剥奪がジョブに届かない）
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／判断の木 `review:decision_tree#keep-sub-exchange`／lint `lint:L47`（未実装）
- 根拠：slide:p08-async-processing、slide:p08-downstream-after-expiry
<!-- req:p08-async-processing.R4 req:p08-downstream-after-expiry.R1 -->

<a id="q-system-actor-no-fake-sub"></a>

**q-system-actor-no-fake-sub**　利用者の文脈が要らない処理だけをサービス自身の ID で動かし、利用者の `sub` を捏造していないか
- 見る欄：`template:00_core#system-privileges`、`template:00_core#principals`
- No なら：Major
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`
- 根拠：slide:p08-downstream-after-expiry
<!-- req:p08-downstream-after-expiry.R2 -->

<a id="q-agent-short-lived-no-rt"></a>

**q-agent-short-lived-no-rt**　エージェントのトークンがタスク単位の短命で、RT を出していないか
- 見る欄：`registry:token_types#max_lifetime`、`registry:token_types#refresh`
- No なら：Major
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／lint `lint:L58`（未実装）
- 根拠：slide:p10-agent-checklist、NIST IR 8587 §5.3.1.6
<!-- req:p10-agent-checklist.R6 -->

<a id="q-copies-outlive"></a>

**q-copies-outlive**　トークンから作った写し（長い接続・判断のキャッシュ・分析基盤への複製）のそれぞれに、期限と止める方法が書いてあるか
- 見る欄：`template:00_core#lifecycle`、`template:00_core#lifecycle-db-connection`
- No なら：Minor〜Major
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`
- 根拠：slide:p08-copies-outlive-token、RFC 7662 §4

<a id="q-deprecated-deadline"></a>

**q-deprecated-deadline**　廃止予定（`deprecated`）のクレームに期日（`sunset_on`）と代わりの行（`alt`）があり、期日の後に読む受け手が残っていないか
- 見る欄：`registry:claims#status`、`registry:claims#sunset_on`、`registry:claims#alt`、`registry:claims#consumers_migration`、`template:00_core#definition-lifecycle`
- No なら：Minor〜Major
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／lint `lint:L18`
- 根拠：slide:p11-change-procedure、slide:p11-registry-fields

<a id="q-change-order"></a>

**q-change-order**　クレームの名前・型・形の変更を破壊的変更として扱い、「受け手が先、発行者が後」の順（事前の通知・プレビュー・並行発行の期間）で進める手順が書いてあるか
- 見る欄：`template:00_core#definition-lifecycle`、`template:00_core#diff`
- No なら：Major
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／lint `lint:L10`
- 根拠：slide:p11-why-govern、slide:p11-change-procedure、NIST SP 800-162 §3.3.3
<!-- req:p11-why-govern.R1 req:p11-change-procedure.R1 -->

### 6.2 鍵と障害

<a id="q-key-rotation"></a>

**q-key-rotation**　公開鍵をコードに埋め込まず JWKS から取り、知らない `kid` での取り直しに最短の間隔と負のキャッシュがあり、鍵の公開と廃止の順序（使う前に公開・廃止は最後のトークンの期限の後）が書いてあるか
- 見る欄：`registry:token_types#jwks_cache_ttl`、`registry:token_types#unknown_kid`、`registry:token_types#key_rotation`、`template:modules/M_token_validation#key-rotation`
- No なら：Major（シナリオ A の A09）
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`／lint `lint:L17`
- 根拠：slide:p01-key-rotation-jwks

<a id="q-dependency-outage"></a>

**q-dependency-outage**　IdP・発行時フック・JWKS の取得・イントロスペクション・受け手が鮮度のために引く外部の台帳（IdP の管理 API・承認の DB）の障害のとき、受け手と発行者がどう振る舞うか（閉じる側に倒すか、キャッシュをいつまで使うか、フックの打ち切りでクレームの無いトークンが出るか）が IdP ごとに書いてあるか
- 見る欄：`registry:token_types#jwks_cache_ttl`、`registry:token_types#introspection_cache_ttl`、`template:modules/M_idp_keycloak#limits`、`template:00_core#uncertain`、`registry:claims#on_revoke`
- No なら：Major
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／lint `lint:R3b`
- 根拠：slide:p03-custom-claim-injection、slide:p01-key-rotation-jwks

### 6.3 ログと監査

<a id="ap-2-8"></a>

**ap-2-8**　（アンチパターン：トークン全文をログに出す）ログ・トレースに残すのが、種別・発行者・ハッシュ（と台帳で許したクレーム）だけか
- 見る欄：`registry:token_types#log_policy`、`registry:claims#log_policy`
- No なら：Major（ログ経由の窃取・個人情報の流出）
- つながり：対比表 `review:contrasts/jws-vs-jwe#misuse`／lint `lint:L45`（未実装）／事例 ガイドに事例の行なし
- 根拠：slide:p12-antipatterns-2、slide:p09-logs-traces、NIST IR 8587 §5.3.1.7
<!-- req:p12-antipatterns-2.R8 -->

<a id="q-token-logging"></a>

**q-token-logging**　ログ・トレースにトークン全文を出さず、記録する HTTP ヘッダーを許可リストにしているか（障害調査で共有する HAR ファイル・ログからトークンを除く手順を含む）
- 見る欄：`registry:token_types#log_policy`、`template:modules/M_privacy_minimization#audit-log`
- No なら：Major
- つながり：対比表 `review:contrasts/jws-vs-jwe#misuse`／lint `lint:L45`（未実装）
- 根拠：slide:p09-logs-traces、slide:p09-checklist、slide:p09-url-browser
<!-- req:p09-checklist.R7 req:p09-checklist.R8 req:p12-antipatterns-2.R8 -->

<a id="q-audit-log-protected"></a>

**q-audit-log-protected**　監査ログ自体を機微な情報として扱い、保護と取り扱いの方針（読める人・保存期間）を書いているか
- 見る欄：`template:modules/M_privacy_minimization#audit-log-protection`
- No なら：Minor〜Major
- つながり：対比表 `review:contrasts/jws-vs-jwe#misuse`
- 根拠：slide:p09-checklist、ASVS v5.0.0-16.4.2
<!-- req:p09-checklist.R9 -->

<a id="q-audit-correlation"></a>

**q-audit-correlation**　監査で `sub`・すべてのアクター（`act` の連鎖）・`txn`・承認 ID を相関できるか
- 見る欄：`template:profiles/P4_ai_agent_delegation#audit-correlation`、`registry:claims#log_policy`
- No なら：Major
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`
- 根拠：slide:p10-agent-checklist、slide:p06-audit-trail
<!-- req:p10-agent-checklist.R9 -->

<a id="q-trace-id-trust"></a>

**q-trace-id-trust**　監査には署名されたトークンの中の `txn` を使い、改ざんできる `traceparent` は観測だけに使っているか
- 見る欄：`registry:claims#log_policy`、`template:profiles/P5_internal_propagation#txn-token`
- No なら：Minor〜Major
- つながり：対比表 `review:contrasts/act-txn-workload#misuse`
- 根拠：slide:p06-audit-trail
<!-- req:p06-audit-trail.R4 -->

<a id="q-scope-elevation-logged"></a>

**q-scope-elevation-logged**　エージェントのスコープをツールごとの最小限から始め、昇格を相関 ID つきで記録しているか
- 見る欄：`template:profiles/P4_ai_agent_delegation#tool-scopes`、`template:profiles/P4_ai_agent_delegation#audit-correlation`
- No なら：Minor〜Major
- つながり：対比表 `review:contrasts/scope-vs-role#misuse`／lint `lint:L57`（未実装）
- 根拠：slide:p10-per-tool-scopes、slide:p10-agent-checklist
<!-- req:p10-per-tool-scopes.R3 req:p10-agent-checklist.R5 -->

<a id="q-operational-metrics"></a>

**q-operational-metrics**　共通の検証ライブラリの採用率と版、`aud`・型の検証失敗の件数、台帳と実際の発行のずれを、誰がどの周期で測るかが書いてあるか
- 見る欄：`template:00_core#operational-metrics`
- No なら：Minor
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`
- 根拠：slide:p11-audit-metrics

### 6.4 検査と記述の整合

<a id="q-lint-workaround"></a>

**q-lint-workaround**　lint を通すために設計の宣言を変えた箇所（ホップの `upstream` を外す・台帳の行にしない・名前を変える）が無いか（あれば、規則の側の誤りの候補として #6 に渡したか）
- 見る欄：`template:00_core#ci-results`、`template:00_core#deviations`、`registry:hops#upstream`
- No なら：Major（目的と仕組みの不一致。規則の側のこともある）。規則そのものを試す（一時コピーで規則に当てる）のはこの教材の範囲の外で、#6 の点検に渡す。較正で追加（B05・B06・B13。templates/examples/scenario-b/review-report.md の 9.）
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`
- 根拠：templates/CONTRIBUTING.md の 2.、tools/claim_lint/RULES.md

<a id="q-evidence-attribution"></a>

**q-evidence-attribution**　数値・製品の挙動を根拠つきで書いた行から 3 件を抜き取り、引いた節・文書がその数値・挙動を述べていることを確かめたか（筆者の提案・実測は、その旨の書き方になっているか）
- 見る欄：`registry:claims#refs`、`registry:token_types#refs`、`template:00_core#uncertain`
- No なら：Minor〜Major（前提の誤り・理由の不備。理由の採点の RR4）。較正で追加（B14。templates/examples/scenario-b/review-report.md の 9.）
- つながり：対比表 `review:contrasts/signed-vs-enforced#misuse`
- 根拠：templates/CONTRIBUTING.md の 1.、templates/review/rationale_rubric.md

<a id="q-limit-consistency"></a>

**q-limit-consistency**　同じ事実（組織の寿命の上限・受け手が照合する内容・受け手の一覧）を書いた 2 か所以上の欄（目録の `note`・5.1・生成の表・矢印の表）が、同じ値と同じトークンを指しているか
- 見る欄：`template:00_core#lifetime-policy`、`registry:token_types#lifetime_exception`、`registry:claims#enforced_at`、`template:00_core#hop-table`
- No なら：Minor（実装とのずれ）。較正で追加（B10・B15。templates/examples/scenario-b/review-report.md の 9.）
- つながり：対比表 `review:contrasts/four-lifetimes#misuse`／lint `lint:L23`
- 根拠：slide:p08-choosing-lifetime、templates/CONTRIBUTING.md の 2.

---

## 7. 役割ごとの索引

役割（観点）ごとに、どの問いを読むかの索引です。問いの本体は 1.〜6. にあります。1 名でレビューするときは、[procedure.md](procedure.md) の「1 名で行う場合」の順に、役割を 1 つずつ切り替えて読みます。

<a id="role-issuer"></a>

### 7.1 発行者の視点

「自分が書いた値を、受け手はどう読むか」を問います。

| 読む問い | この視点で見ること |
| --- | --- |
| `q-single-issuer`・`pa-15` | 各サービスがクレームを足したりトークンを作り直したりしていない |
| `ap-2-1` | 詰め込みすぎて黙って欠けない |
| `ap-2-4`・`dc-03` | 名前空間の外の名前を出さない |
| `q-hook-failure`・`q-minimal-per-recipient` | 失敗時と、宛先ごとの絞り込み |

根拠：slide:p04-single-issuer、slide:p12-antipatterns-2
<!-- req:p04-single-issuer.R2 req:p12-antipatterns-2.R1 req:p12-antipatterns-2.R4 -->

<a id="role-consumer"></a>

### 7.2 受け手の視点

「受け入れる条件と、値を判断に使う条件は書いてあるか」を問います。

| 読む問い | この視点で見ること |
| --- | --- |
| `ap-1-2`・`q-validate-before-read` | 検証してから読む |
| `ap-1-3`・`ap-1-5`・`ap-1-8`・`q-typ-distinguishes` | 宛先・発行者と鍵・期限・種類 |
| `q-required-rejected` | 誤拒否を避けるために必須の確認を外していない |
| `ap-2-3`・`q-consumer-expression` | 型と比べ方 |
| `q-idp-diff-absorbed` | 内側のサービスが読むのは、組織の発行者が出した組織の名前空間のクレームだけ |

根拠：slide:p12-antipatterns-1、slide:p04-reject-missing-required、slide:p03-absorb-idp-differences
<!-- req:p03-absorb-idp-differences.R4 req:p04-reject-missing-required.R1 req:p12-antipatterns-1.R2 req:p12-antipatterns-1.R3 req:p12-antipatterns-1.R5 req:p12-antipatterns-1.R8 req:p12-antipatterns-2.R3 -->

<a id="role-attacker"></a>

### 7.3 攻撃者の視点

「自分が書ける値・選べる値はどれか」を問います。設計書の図の矢印ごとに、攻撃者が触れるもの（ヘッダー・本人の属性・テナントの管理画面・トークンのヘッダー）を書き出してから読みます。

| 読む問い | この視点で見ること |
| --- | --- |
| `ap-1-1` | トークンの `alg` を選べる |
| `ap-1-4`・`q-tenant-data-match` | 別テナントのトークン・データ |
| `ap-1-6`・`dc-09`・`q-identifier-choice` | 変えられる名前・メールで別人になる。改名・再利用で別の主体を指す名前を認可の条件にしていない |
| `ap-1-7`・`pa-11`・`q-writer-distinguished` | 本人・テナントの管理者が書ける値で権限を得る |
| `ap-2-5`・`q-access-context-from-pep` | 同名のヘッダー・`X-Forwarded-For` を偽装する |
| `q-gateway-bypass-path`・`q-hop-narrowing` | 入口を通らない経路、交換で広がる権限 |

根拠：slide:p12-antipatterns-1、slide:p04-immutable-identifiers、slide:p06-access-context
<!-- req:p04-immutable-identifiers.R1 req:p06-access-context.R4 req:p12-antipatterns-1.R1 req:p12-antipatterns-1.R4 req:p12-antipatterns-1.R6 req:p12-antipatterns-1.R7 req:p12-antipatterns-2.R5 -->

<a id="role-operations"></a>

### 7.4 運用の視点（鍵の更新、IdP・フックの障害、JWKS の取得障害）

「止まったとき・変えるとき・調べるときに、何が起きるか」を問います。

| 読む問い | この視点で見ること |
| --- | --- |
| `q-key-rotation` | 公開鍵をコードに埋め込まない。ローテーションの頻度が変わっても追従できる |
| `q-dependency-outage`・`q-hook-failure` | フックの失敗・打ち切り・予約名との衝突で、クレームの無いトークンが出るかを IdP ごとに書いた |
| `q-lifetime-rationale` | 短くする利点と代償を比べて寿命の理由を書いた |
| `q-token-logging` | 障害調査で共有する HAR ファイル・ログからトークンを除く手順 |
| `q-operational-metrics` | 共通の検証ライブラリの採用率と版、`aud`・型の検証失敗の件数を測る |
| `q-revocation-delivery`・`q-change-order` | 失効と変更の手順 |

根拠：slide:p01-key-rotation-jwks、slide:p03-custom-claim-injection、slide:p08-choosing-lifetime、slide:p09-url-browser、slide:p11-audit-metrics
<!-- req:p01-key-rotation-jwks.R5 req:p03-custom-claim-injection.R2 req:p08-choosing-lifetime.R4 req:p09-url-browser.R3 req:p11-audit-metrics.R3 req:p11-audit-metrics.R6 -->

<a id="role-privacy"></a>

### 7.5 個人情報の視点

「この値が漏れたら、誰の何が分かるか」を問います。

| 読む問い | この視点で見ること |
| --- | --- |
| `q-payload-readable`・`q-confidential-reaches-reader` | 読める相手に届くトークンに載せない |
| `q-no-secret-or-raw-pii`・`q-derived-value`・`q-hook-adds-raw-pii` | 秘密・生の個人情報を載せない。派生値で足りる |
| `q-pairwise-external`・`q-minimal-per-recipient` | 外部の受け手と、受け手ごとの最小化 |
| `q-token-logging`・`q-audit-log-protected`・`pa-20` | 監査ログ自体を機微な情報として保護の方針を決めた |

根拠：slide:p09-logs-traces、slide:p09-checklist
<!-- req:p09-logs-traces.R5 -->

<a id="role-client"></a>

### 7.6 クライアントの実装の視点（トークンの保存場所）

「トークンはどこに置かれ、どこに写るか」を問います。

| 読む問い | この視点で見ること |
| --- | --- |
| `q-token-not-in-url` | 認可要求は PAR、認可応答は form_post で URL から外す。URL・履歴に残さない |
| `q-payload-readable` | ブラウザに置くトークンの中身は利用者と拡張機能が読める（`registry:token_types#stored_at`） |
| `q-session-rt-bounds` | ブラウザ・端末に残る RT とセッションの上限 |

根拠：slide:p09-url-browser、slide:p08-copies-outlive-token、RFC 9126 §1
<!-- req:p09-url-browser.R2 -->

---

## 8. スライドの行との対応（完了基準の確かめ用）

各 Part のチェックリスト・アンチパターン・レビューの観点・寿命の主張の全行が、どの問いに当たるかの表です。対応表（`templates/trace/requirements.yaml`）の要件の `req:` の印は、上の各節にあります（`python tools/trace_check.py` と `python tools/review_check.py` が確かめる）。

| スライド | 行 | 問い |
| --- | --- | --- |
| 61（slide:p04-design-checklist） | 12 の確認と「1 つでも答えられなければ載せない」 | `dc-01`〜`dc-12`、`dc-gate` |
| 90（slide:p06-flow-checklist） | 10 項目 | `cf-01`〜`cf-10` |
| 101（slide:p07-data-layer-checklist） | 10 項目と「製品の既定値に任せない」 | `cd-01`〜`cd-11` |
| 120（slide:p09-checklist） | 定義 3・発行 2・伝搬 1・運用 3 | `q-no-secret-or-raw-pii`・`q-derived-value`・`q-pairwise-external`・`q-minimal-per-recipient`・`q-nested-jwt-both-layers`・`q-token-not-in-url`・`q-token-logging`（2 行）・`q-audit-log-protected` |
| 131（slide:p10-agent-checklist） | 主体・委任・宛先・転送・範囲・寿命・承認・連鎖・監査 | `q-agent-own-identity`・`q-agent-delegation-claims`・`q-single-aud-resource`・`q-no-passthrough`・`q-scope-elevation-logged`・`q-agent-short-lived-no-rt`・`q-approval-from-as`・`q-delegation-depth-and-revocation`・`q-audit-correlation` |
| 142・143（slide:p11-pre-add-questions-1・2） | 25 問と「答えられなければ共有クレームにしない」「ADR と台帳の 1 件に残す」 | `pa-01`〜`pa-25`、`pa-gate`、`pa-trace` |
| 146（slide:p12-antipatterns-1） | 8 行 | `ap-1-1`〜`ap-1-8` |
| 147（slide:p12-antipatterns-2） | 8 行とノートの内部の代理トークン | `ap-2-1`〜`ap-2-9` |
| 148（slide:p12-review-viewpoints） | 6 段 × 3 観点と「各段に 25 問を使う」 | 各段の冒頭の表（`stage-definition` ほか 6 つ） |
| 81（slide:p06-narrow-downstream） | aud・scope・寿命・独自クレームを上流より広げない／仕様が縮小を求めない | `q-hop-narrowing`・`q-hop-lifetime`、対比表 `review:contrasts/act-txn-workload#not-covered` |
| 103（slide:p08-four-lifetimes） | 4 つの層を別々に書く | `q-four-lifetimes-written`、対比表 `review:contrasts/four-lifetimes#table` |
| 104（slide:p08-token-types-lifetimes） | 種類ごとに上限、ID トークンの期限とセッションを混同しない | `q-lifetime-rationale`・`q-session-rt-bounds`、対比表 `review:contrasts/four-lifetimes#misuse` |
| 105（slide:p08-choosing-lifetime） | 上限の文書化・例外の手順・AT の期限を当てにしない | `q-lifetime-rationale`・`q-relies-on-at-expiry` |
| 106（slide:p08-stale-claims） | 寿命の間は古い値。3 つの手段 | `q-freshness-mitigation`・`ap-2-2` |
| 107（slide:p08-refresh-reevaluation） | 再計算は IdP 次第。確かめずに前提にしない | `q-refresh-reevaluated` |
| 108（slide:p08-reissue-triggers） | 再発行の契機。auth_time と iat | `q-auth-context-semantics`・`q-refresh-reevaluated`・`q-external-user-deprovision` |
| 109（slide:p08-rotation） | クライアントの種類で RT の方式を分ける | `q-rt-policy-by-client` |
| 110（slide:p08-revocation-propagation） | 失効を届ける手段と時間 | `q-revocation-delivery` |
| 111（slide:p08-logout） | ログアウトが止めるのはセッションと RT | `q-revocation-delivery`、対比表 `review:contrasts/four-lifetimes#misuse` |
| 112（slide:p08-async-processing） | キューに利用者のトークンを入れない | `q-long-running` |
| 113（slide:p08-downstream-after-expiry） | 延命しない・sub を捏造しない・作り直しを AS が判断 | `q-long-running`・`q-system-actor-no-fake-sub` |
| 114（slide:p08-copies-outlive-token） | 写しに期限と止め方 | `q-copies-outlive` |
| 115（slide:p08-decision-table） | 状況で寿命・リフレッシュ・失効を選ぶ | `q-lifetime-rationale`・`q-rt-policy-by-client`、判断の木 `review:decision_tree#lifetime-by-situation` |
| 134（slide:p11-registry-fields） | 鮮度（値の出どころと反映までの遅れ）・状態 | `q-freshness-mitigation`・`q-deprecated-deadline` |
| 138（slide:p11-change-procedure） | 受け手が先・互換期間を短く見積もらない | `q-change-order`・`q-deprecated-deadline` |

スライドの番号は、issue #5 の本文の番号（2026-11-18 の 152 枚の版）です。固定 ID のほうを正とします。寿命の行（103〜115）は、#10 でスライドを足した後の Part 8 の全 14 枚（slide:p08-four-lifetimes〜slide:p08-decision-table）に当てています。

## 9. 較正：過去のレビューの指摘と、それを見つける問い

シナリオ A（#16、指摘 A01〜A17）とシナリオ B（#4、指摘 B01〜B15）の設計レビューの指摘を、この観点書のどの問いが見つけるかで並べます。**どの指摘も、少なくとも 1 つの問いから辿れるようにしました。** 指摘の全文は `research/reviews/scenario-a-2026-11-22.md` と PR #44 のコメント（シナリオ B）にあります。シナリオ B の表は、この観点書でシナリオ B を改めてレビューした結果（`templates/examples/scenario-b/review-report.md`）と、再発見できたかを並べたものです。

### 9.1 シナリオ A（Lite）

| ID | 指摘の要約 | 見つける問い | 指摘の種類 |
| --- | --- | --- | --- |
| A01 | テナントの管理者が書ける値を、API が守っていない | `pa-11`・`ap-1-7`・`q-writer-distinguished` | 前提の誤り |
| A02 | BOLA の鍵が `sub` か `user_id` か決まっていない | `q-object-level-authz`・`q-identifier-choice` | 候補の漏れ |
| A03 | Back-Channel Logout の却下の理由が的外れで、代わりがない | `q-revocation-delivery` | 理由の不備 |
| A04 | RLS をすり抜ける主体が抜けている | `cd-06` | 候補の漏れ |
| A05 | テナントを決めているのは実際には `iss` | `q-identifier-choice` | 目的と仕組みの不一致 |
| A06 | lint の挙動についての記述が実際と違う | `pa-trace`（記述と台帳の食い違い）、[procedure.md](procedure.md) の 3.（CI の結果を貼った欄と照合） | 実装とのずれ |
| A07 | at+jwt を名乗るのに `client_id` がない | `q-typ-distinguishes`・`ap-1-3` | 前提の誤り |
| A08 | `azp` は `on_missing` が拒否なのに `required_claims` にない | `dc-12`・`q-required-rejected` | 実装とのずれ |
| A09 | JWKS の取り直しに回数の制限と負のキャッシュがない | `q-key-rotation` | 候補の漏れ |
| A10 | 「外せない」の根拠が別の節を指している | 理由の採点基準の R4（[rationale_rubric.md](rationale_rubric.md)） | 理由の不備 |
| A11 | `max_bytes` が文字数とバイト数を取り違えている | `dc-11`・`q-size-limit` | 前提の誤り |
| A12 | `SET LOCAL` ではバインド変数を使えない | `q-db-context-parameterized` | 前提の誤り |
| A13 | 文脈が未設定のときに全件を拒否するかが無い | `cd-10` | 候補の漏れ |
| A14 | セッション・RT に絶対的な上限がない | `q-session-rt-bounds` | 候補の漏れ |
| A15 | テナントの停止の一覧の出どころ・鮮度が決まっていない | `q-freshness-mitigation`・`q-revocation-delivery` | 候補の漏れ |
| A16 | ローテーションの根拠が機密クライアントに合わない | `q-rt-policy-by-client` | 理由の不備 |
| A17 | Full の条件に当たるのに Lite で書いた | [procedure.md](procedure.md) の 1.（Lite／Full の確認） | 前提の誤り |

### 9.2 シナリオ B（Full）

シナリオ B の 15 件（B01〜B15）を、改めて行ったレビューが再び見つけたか（再発見）と、見つける問いを並べた表は、`templates/examples/scenario-b/review-report.md` の「較正」の節にあります。**見逃した指摘に対して足した問いには、印（較正で追加）を付けています。** 作成の順は、(1) この観点書を作る、(2) 別のセッションがシナリオ B をレビューする、(3) B01〜B15 と照合する、(4) 見逃した指摘から問いを足す、です。(4) で足した問いは、(2) のレビューでは使っていません。

| 区分 | 件数 | B の ID |
| --- | --- | --- |
| 再発見 | 5 | B01・B03・B08・B09・B11 |
| 一部 | 4 | B02・B05・B10・B14 |
| 見逃し | 4 | B04・B07・B12・B15 |
| 教材の範囲の外 | 2 | B06（lint の規則そのもの）・B13（レビュアーに読ませていないファイル） |

指摘ごとの対応と、見逃しから足した 7 問（`q-txn-required-claims`・`q-claim-earliest-hop`・`q-idp-capability-verified`・`q-variant-comparison`・`q-lint-workaround`・`q-evidence-attribution`・`q-limit-consistency`）は、review-report.md の 9. にあります。B01・B03・B08 は、作成者が B の要約を読んだ後に書いた問いから見つけたので、割り引いて読みます（同 9.1）。
