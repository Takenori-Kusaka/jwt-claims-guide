<!-- template_version: 0.3.0 -->
# 追加前の 25 問（claim_request）

> テンプレートです。候補と検討の問いだけを載せ、採否の理由の見本は載せません（理由の写し書きを防ぐため。#4 の方針）。判断は台帳（claims.yaml など）に 1 回だけ書き、ここからは ID で参照します。

- 使う場面：組織の名前空間に**共有クレーム**（複数の受け手が読む独自クレーム）を足すとき、または既存の共有クレームの名前・型・形・意味を変えるとき。クレーム 1 つにつき 1 ファイル（`claim_request_<名前>.md`）を、設計書と同じディレクトリに置きます
- **Lite でも必須です。** 関門 1 で Lite を絞った後も、この様式は外しません。スライド 142・143 の関所そのものだからです（#4 の「追加前の 25 問は Lite でも必須」、`research/template-design/gate1.md` の 10.）
- 問いの文言はガイドのスライド（slide:p11-pre-add-questions-1、slide:p11-pre-add-questions-2）と同じです
- 回答は ADR（設計書の 10. の判断の行）と台帳の 1 行の両方から辿れるようにします（slide:p11-pre-add-questions-2 の「回答は ADR と台帳の 1 件に残す」）
- 記入例：[examples/scenario-a/claim_request_tenant_id.md](examples/scenario-a/claim_request_tenant_id.md)
- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施

<a id="gate"></a>
## 1. 判定の規則〔Lite・Full：記入〕

項目 ID：`template:claim_request#gate`
<!-- req:p11-pre-add-questions-1.R13 req:p09-do-not-carry.R7 -->

決めること：25 問のすべてに答えられたか。**答えられない問いが残るなら、まだ共有クレームにしません。** サービスの中のローカルな属性にとどめるか、台帳の `status` を `proposed` のままにして、答えられるようになってから `active` にします。

- 「答えた」とは、回答の欄が空でなく、「未定」「TBD」「-」でないこと（#6 の L72 が、組織の名前空間で `status` が proposed 以上の採用の行について確かめる）
- 「該当しない」と答えるときは、なぜ該当しないかを書く（例：委任が無いなら問 21 に「委任は無い」と、その前提）
- 迷ったら載せず、必要な受け手が必要なときに API で取りに行く形を既定にします（slide:p09-do-not-carry）

記入欄：

| 対象（台帳の ID） | 25 問に答えたか | 判定（共有クレームにする／ローカルな属性にとどめる）（書き手が書く） | 台帳の `status` |
| --- | --- | --- | --- |
|  |  |  |  |

根拠：slide:p11-pre-add-questions-1、slide:p11-pre-add-questions-2、slide:p09-do-not-carry

<a id="form"></a>
## 2. 記入の様式（この表を写して使う）〔Lite・Full：記入〕

項目 ID：`template:claim_request#form`
<!-- req:p00-claims-are-contracts.R8 req:p02-check-before-creating.R1 req:p09-do-not-carry.R7 req:p12-review-viewpoints.R19 -->

ファイルの冒頭に次の 3 行を書き、その下に 25 行の表を写します。`- 対象：` の行には台帳の行の ID を `` ` `` で囲んで書きます（#6 の L72 が、この行で台帳の行と結びつけます）。

```markdown
# 追加前の 25 問：`<名前空間>` の `<クレーム名>`
- 対象：台帳の `C-...`（claims.yaml）
- 判定：（共有クレームにする／ローカルな属性にとどめる）
```

「出どころ」の列は、回答を台帳の列から写せる問い（11 問）は `台帳：<列>`、手で書く問い（14 問）は `手書き` と書きます。台帳から写せる問いでも、写した結果が問いに答えていなければ、手で補います。作る前に探した記録（IANA の登録簿 → 仕様の構造 → IdP の文書 → 組織の台帳の順。slide:p02-check-before-creating）は、問 3 と台帳の `prior_art_search` に書きます。

| # | 問い（スライド 142・143） | 回答（書き手が書く） | 出どころ |
| --- | --- | --- | --- |
| 1 | 受け手はこのクレームで何を決めるか |  | 台帳：`usage`・`answers`・`rationale` |
| 2 | 寿命中に値が変わっても困らないか |  | 台帳：`volatility`・`on_revoke` |
| 3 | 既存の標準クレームで表せないか |  | 台帳：`registered_ref`・`prior_art_search` |
| 4 | 自組織の名前空間か。予約名と衝突しないか |  | 手書き |
| 5 | 「.」「/」入りの名前を全ての受け手のツールで参照できるか |  | 手書き |
| 6 | トップレベルか、組織のオブジェクトの下か |  | 台帳：`namespace`・`shape` |
| 7 | 型は 1 つか。区切り文字列を避けたか |  | 台帳：`type`・`shape` |
| 8 | ID・金額は文字列で運ぶか |  | 手書き |
| 9 | 無い・null・false・空配列の意味は |  | 台帳：`absent_semantics`・`on_missing` |
| 10 | 大文字小文字・空白・比較方法は |  | 手書き |
| 11 | 誰が値を書けるか。自己申告と分けたか |  | 台帳：`authoritative_writer`・`provenance` |
| 12 | 名前と不変の ID を出し、ID で照合させるか |  | 手書き |
| 13 | 上限は。超えたら失敗か、欠落か |  | 台帳：`max_bytes`・`max_items`・`overflow_strategy` |
| 14 | 全リクエストに載せる価値があるか。宛先ごとに絞れるか |  | 手書き |
| 15 | 付与するのは単一の発行者だけか |  | 台帳：`issuers`・`enforced_at` |
| 16 | 検証を共通ライブラリで提供するか |  | 手書き |
| 17 | ヘッダーに移すとき、同名ヘッダーの偽装（大文字小文字・アンダースコアの変種・重複）を除去するか |  | 手書き |
| 18 | 未検証の値を流すモードは無いか |  | 手書き |
| 19 | 知らない受け手が無視しても安全か |  | 手書き |
| 20 | ログに残すか。値かハッシュか。個人情報か |  | 台帳：`log_policy`・`pii_category` |
| 21 | 委任なら act・承認 ID との関係は |  | 手書き |
| 22 | 台帳に登録し、受け手を把握したか |  | 台帳：`consumers` |
| 23 | 形式を変えるときの移行計画はあるか |  | 手書き |
| 24 | 改名・廃止の互換期間と並行発行は |  | 手書き |
| 25 | 発行前の確認手段と、受け手の条件のテストは |  | 手書き |

縮小 Lite で「台帳から写す」11 問（1・2・3・6・7・9・11・13・15・20・22）と「手書き」14 問の分け方は、シナリオ A の記入例で数えたもの（`research/template-design/gate1.md` の 10.、`python tools/count_lite_fields.py` が「手書き」の行を数える）です。

根拠：slide:p11-pre-add-questions-1、slide:p11-pre-add-questions-2、slide:p02-check-before-creating、slide:p00-claims-are-contracts、research/template-design/gate1.md の 10.

## 3. 問いごとの説明

各問いが、台帳のどの列か、どの lint の規則に対応するかと、関係するテンプレートの項目です。対応する列も規則も無い問いは、自由記述の回答が必須です（この様式の「手書き」）。lint の規則の ID は `tools/claim_lint/RULES.md`（#6 の意味の規則は PR #40・#41 で入る）によります。

<a id="q01"></a>
### 問 1　受け手はこのクレームで何を決めるか

項目 ID：`template:claim_request#q01`
<!-- req:p11-pre-add-questions-1.R1 -->

- 対応：台帳の `usage`（identifier・authz・display・protocol）、`answers`（`templates/registry/questions.yaml` の問い）、`rationale`
- 検討の問い：認可・ルーティングに使わないなら、載せずに UserInfo・DB で取れないか（template:modules/M_authz_pdp#carry-or-query）

根拠：slide:p11-pre-add-questions-1、slide:p04-carry-or-query

<a id="q02"></a>
### 問 2　寿命中に値が変わっても困らないか

項目 ID：`template:claim_request#q02`
<!-- req:p11-pre-add-questions-1.R2 -->

- 対応：台帳の `volatility`（反映までに許す秒数。`never` はトークンの寿命の間に変わらない）と `on_revoke`、lint は #6 の L5（`volatility` と載る種別の受け入れの上限の比較）
- 検討の問い：困るなら、00_core の 9.2（クレームの鮮度の表）の対策（寿命を縮める・問い合わせる・失効を伝える）のどれを使うか

根拠：slide:p11-pre-add-questions-1、slide:p04-token-is-snapshot、slide:p08-stale-claims

<a id="q03"></a>
### 問 3　既存の標準クレームで表せないか

項目 ID：`template:claim_request#q03`
<!-- req:p11-pre-add-questions-1.R3 req:p10-four-questions.R7 -->

- 対応：台帳の `registered_ref`・`prior_art_search`、lint は #6 の L1a（IANA の登録名の型・形の照合）
- 検討の問い：IANA の JWT Claims の登録簿、仕様の構造（`act`・`authorization_details`・`cnf` など）、IdP の文書、組織の台帳の順に探したか

根拠：slide:p11-pre-add-questions-1、slide:p02-check-before-creating、slide:p10-four-questions、IANA JWT Claims registry

<a id="q04"></a>
### 問 4　自組織の名前空間か。予約名と衝突しないか

項目 ID：`template:claim_request#q04`
<!-- req:p11-pre-add-questions-1.R4 -->

- 対応：台帳の `namespace`、最上位の `namespaces`、lint は #6 の L1b（宣言していない名前空間）・L34（予約名との衝突）
- 検討の問い：使う IdP が予約している名前（Auth0 の名前空間の規則、Cognito の書き換えられないクレームなど）と衝突しないか。template:modules/M_idp_keycloak#immutable-claims

根拠：slide:p11-pre-add-questions-1、slide:p04-namespace、slide:p11-reserved-names

<a id="q05"></a>
### 問 5　「.」「/」入りの名前を全ての受け手のツールで参照できるか

項目 ID：`template:claim_request#q05`
<!-- req:p11-pre-add-questions-1.R5 -->

- 対応：台帳の `consumer_access_path`（Full の列）。対応する lint の規則は無い（自由記述が必須）
- 検討の問い：受け手のライブラリ・ゲートウェイの設定（ヘッダーへの写し）・CEL・DB の RLS・Kubernetes の claimMappings などで、その名前を参照できるかを試したか

根拠：slide:p11-pre-add-questions-1、slide:p04-namespace

<a id="q06"></a>
### 問 6　トップレベルか、組織のオブジェクトの下か

項目 ID：`template:claim_request#q06`
<!-- req:p11-pre-add-questions-1.R6 -->

- 対応：台帳の `namespace`・`shape`、最上位の `namespaces[].style`（object・flat_prefix）
- 検討の問い：ネストを扱えない IdP・受け手があるなら、フラットな別名（`flat_alias`）が要るか

根拠：slide:p11-pre-add-questions-1、slide:p04-namespace-object-example

<a id="q07"></a>
### 問 7　型は 1 つか。区切り文字列を避けたか

項目 ID：`template:claim_request#q07`
<!-- req:p11-pre-add-questions-1.R7 -->

- 対応：台帳の `type`・`shape`（配列・空白区切りは `max_items` が必須）
- 検討の問い：IdP のマッパーの設定で型が変わらないか（template:modules/M_idp_keycloak#mappers-scopes）

根拠：slide:p11-pre-add-questions-1、slide:p04-type、slide:p04-shape

<a id="q08"></a>
### 問 8　ID・金額は文字列で運ぶか

項目 ID：`template:claim_request#q08`
<!-- req:p11-pre-add-questions-1.R8 -->

- 対応：台帳の `type`。提案の lint は L24（ID・金額の数値）。自由記述が必須
- 検討の問い：2^53 を超える数値を JavaScript の受け手が丸めないか（ケーススタディ B22）

根拠：slide:p11-pre-add-questions-1、slide:p04-type、jwt-claims-casestudy@080b8da:B22

<a id="q09"></a>
### 問 9　無い・null・false・空配列の意味は

項目 ID：`template:claim_request#q09`
<!-- req:p11-pre-add-questions-1.R9 -->

- 対応：台帳の `absent_semantics`・`on_missing`
- 検討の問い：上限で消えうるクレームを「所属なし」と読まないか。許可を与えるクレームが無いとき、何も許さないか

根拠：slide:p11-pre-add-questions-1、slide:p04-absent-null-false-empty

<a id="q10"></a>
### 問 10　大文字小文字・空白・比較方法は

項目 ID：`template:claim_request#q10`
<!-- req:p11-pre-add-questions-1.R10 -->

- 対応：台帳の `value_normalization`（Full の列）。自由記述が必須
- 検討の問い：書き手が一度だけ正規化し、受け手は完全一致で比べるか。基盤ごとの大小の扱いの違いで値が黙って欠けないか

根拠：slide:p11-pre-add-questions-1、slide:p04-case-and-characters

<a id="q11"></a>
### 問 11　誰が値を書けるか。自己申告と分けたか

項目 ID：`template:claim_request#q11`
<!-- req:p11-pre-add-questions-1.R11 -->

- 対応：台帳の `authoritative_writer`（段階・書き手・`configurable_by`）、`provenance`（Full の列）
- 検討の問い：本人が編集できる値・呼び出し側の申告を、認可に使っていないか（ケーススタディ B18）

根拠：slide:p11-pre-add-questions-1、slide:p04-split-by-writer、jwt-claims-casestudy@080b8da:B18

<a id="q12"></a>
### 問 12　名前と不変の ID を出し、ID で照合させるか

項目 ID：`template:claim_request#q12`
<!-- req:p11-pre-add-questions-1.R12 -->

- 対応：台帳の `paired_id`・`identifier_properties`、lint は #6 の L3（変わりうる名前を識別子・認可に使う）。自由記述が必須
- 検討の問い：値は再割り当てされないか（Okta の `sub` のログイン名の再利用。ケーススタディ B13）

根拠：slide:p11-pre-add-questions-1、slide:p04-immutable-identifiers、jwt-claims-casestudy@080b8da:B13

<a id="q13"></a>
### 問 13　上限は。超えたら失敗か、欠落か

項目 ID：`template:claim_request#q13`
<!-- req:p11-pre-add-questions-2.R1 -->

- 対応：台帳の `max_bytes`・`max_items`・`overflow_strategy`（切り詰めは書けない）、lint は R8（トークン種別ごとの最悪のサイズと経路の上限）
- 検討の問い：上限を超えたら、発行を失敗させるか、問い合わせに切り替えるか（Entra の groups の超過。ケーススタディ B8・B9）

根拠：slide:p11-pre-add-questions-2、slide:p04-size-budget、tools/claim_lint/RULES.md の R8

<a id="q14"></a>
### 問 14　全リクエストに載せる価値があるか。宛先ごとに絞れるか

項目 ID：`template:claim_request#q14`
<!-- req:p11-pre-add-questions-2.R2 -->

- 対応：台帳の `carried_in`、ホップの `custom_claims`。自由記述が必須
- 検討の問い：読まない受け手のトークンにまで載せていないか（00_core の 8. ホップごとの表で、宛先ごとに絞る）

根拠：slide:p11-pre-add-questions-2、slide:p06-narrow-downstream

<a id="q15"></a>
### 問 15　付与するのは単一の発行者だけか

項目 ID：`template:claim_request#q15`
<!-- req:p11-pre-add-questions-2.R3 -->

- 対応：台帳の `issuers`・`enforced_at`、lint は #6 の L4（同じ段階に書き手が 2 つ以上）
- 検討の問い：各サービスが値を足していないか。追加の文脈が要るなら、トークン交換か Txn-Token の発行サービスに書かせるか（template:profiles/P5_internal_propagation#txn-token）

根拠：slide:p11-pre-add-questions-2、slide:p04-single-issuer

<a id="q16"></a>
### 問 16　検証を共通ライブラリで提供するか

項目 ID：`template:claim_request#q16`
<!-- req:p11-pre-add-questions-2.R4 -->

- 対応：template:modules/M_token_validation#shared-validator。自由記述が必須
- 検討の問い：受け手ごとに読み方を実装させていないか（ケーススタディの「共有クレームを変えたとき」で、共通の部品は 10 の変更を正しく処理した）

根拠：slide:p11-pre-add-questions-2、slide:p11-contract-test-gaps、jwt-claims-casestudy@080b8da（results/summary.md の「共有クレームを変えたとき」）

<a id="q17"></a>
### 問 17　ヘッダーに移すとき、同名ヘッダーの偽装（大文字小文字・アンダースコアの変種・重複）を除去するか

項目 ID：`template:claim_request#q17`
<!-- req:p11-pre-add-questions-2.R5 -->

- 対応：ホップの `forwarded_headers`（`strip_inbound`・`written_only_by`）、台帳の `integrity_until`、lint は #6 の L8・L67。自由記述が必須
- 検討の問い：入口が、クライアントの送った同名のヘッダーを、大文字小文字・`_` と `-` の変種・重複を含めて捨てるか（ケーススタディ B4〜B7）

根拠：slide:p11-pre-add-questions-2、slide:p06-header-forwarding、jwt-claims-casestudy@080b8da:B5

<a id="q18"></a>
### 問 18　未検証の値を流すモードは無いか

項目 ID：`template:claim_request#q18`
<!-- req:p11-pre-add-questions-2.R6 -->

- 対応：対応する列・規則は無い。自由記述が必須
- 検討の問い：検証を飛ばす設定・デバッグのモード・入口を通らない経路（ケーススタディ B7）が無いか

根拠：slide:p11-pre-add-questions-2、slide:p06-validation-split

<a id="q19"></a>
### 問 19　知らない受け手が無視しても安全か

項目 ID：`template:claim_request#q19`
<!-- req:p11-pre-add-questions-2.R7 -->

- 対応：提案の列 `restrictive`（制限のクレームか）と提案の lint の L60。今の台帳では自由記述が必須
- 検討の問い：制限のクレーム（`ip_allow` など）を、古い受け手が無視すると制限が効かない。受け手の対応を先に済ませたか（00_core の 9.3）

根拠：slide:p11-pre-add-questions-2、slide:p04-forward-compatibility

<a id="q20"></a>
### 問 20　ログに残すか。値かハッシュか。個人情報か

項目 ID：`template:claim_request#q20`
<!-- req:p11-pre-add-questions-2.R8 -->

- 対応：台帳の `log_policy`・`pii_category`・`data_category`
- 検討の問い：トークン全文をログに残していないか。監査ログに残す項目と伏せる項目（template:modules/M_privacy_minimization#audit-log）

根拠：slide:p11-pre-add-questions-2、slide:p09-logs-traces、NIST IR 8587 §5.3.1.7

<a id="q21"></a>
### 問 21　委任なら act・承認 ID との関係は

項目 ID：`template:claim_request#q21`
<!-- req:p11-pre-add-questions-2.R9 -->

- 対応：問いの一覧の `q-actor`、template:profiles/P4_ai_agent_delegation#audit-correlation。自由記述が必須
- 検討の問い：委任の理由・承認者を独自に運ぶなら、`act` の外に置くか。承認 ID と監査ログを相関させるか

根拠：slide:p11-pre-add-questions-2、RFC 8693 §4.1、slide:p10-human-approval-evidence

<a id="q22"></a>
### 問 22　台帳に登録し、受け手を把握したか

項目 ID：`template:claim_request#q22`
<!-- req:p11-pre-add-questions-2.R10 -->

- 対応：台帳の `consumers`（読む受け手がいなければ `[]`）、`consumers_migration`

根拠：slide:p11-pre-add-questions-2、slide:p11-registry-fields

<a id="q23"></a>
### 問 23　形式を変えるときの移行計画はあるか

項目 ID：`template:claim_request#q23`
<!-- req:p11-pre-add-questions-2.R11 -->

- 対応：template:00_core#definition-lifecycle、最上位の `namespaces[].namespace_version`。自由記述が必須

根拠：slide:p11-pre-add-questions-2、slide:p11-change-procedure

<a id="q24"></a>
### 問 24　改名・廃止の互換期間と並行発行は

項目 ID：`template:claim_request#q24`
<!-- req:p11-pre-add-questions-2.R12 -->

- 対応：台帳の `status`・`sunset_on`・`alt`、template:00_core#definition-lifecycle、lint は #6 の L18（廃止予定のクレームを読む受け手）。自由記述が必須
- 検討の問い：古い形式で出した最後のトークンの受け入れの上限が過ぎてから、古い名前を読むのをやめるか

根拠：slide:p11-pre-add-questions-2、slide:p11-change-procedure

<a id="q25"></a>
### 問 25　発行前の確認手段と、受け手の条件のテストは

項目 ID：`template:claim_request#q25`
<!-- req:p11-pre-add-questions-2.R13 -->

- 対応：template:modules/M_idp_keycloak#token-preview、発行側の検査用スキーマ（`schemas/<ID>.issuer.schema.json`。`tools/claim_lint/RENDER.md` の 4.）、受け手の契約テスト（#8）。自由記述が必須

根拠：slide:p11-pre-add-questions-2、slide:p11-schema-contract-tests、tools/claim_lint/RENDER.md の 4.
