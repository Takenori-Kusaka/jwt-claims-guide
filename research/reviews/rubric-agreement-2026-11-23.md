# 理由の採点の一致率の測定（#5）：材料と記録の様式

#5 の完了基準「採点基準を使い、同じ理由 10 件を、互いに独立した 2 回（別の LLM のセッション、または作成者が 1 日空けて）採点し、一致率を記録している」のための材料です。**この文書の作成者（教材を作った LLM のセッション）は採点していません。** 作成者は教材の作り手なので、採点しても独立になりません。採点は、調整役が別のセッションで 2 回行います（下の 3.）。

- 採点基準：`templates/review/rationale_rubric.md`（RR1〜RR6、各 2 値）
- 対象：記入例の台帳（コミット 9202586 の `templates/examples/scenario-a`・`scenario-b`）の理由 10 件
- 選び方：記入例の `claims.yaml`・`token_types.yaml` の `rationale` を持つ行 113 件から、Python の `random.seed(5)` と `random.sample(rows, 14)` で 14 件を引き、採用・却下・既定どおりが混ざるように 10 件をとった（重複に近い 4 件を外した：シナリオ B の `C-events`・`C-txn`・`INT_AT_DOCS`、シナリオ A の `C-exp`）。行の順は `scenario-a`・`scenario-b` のそれぞれで `claims.yaml` → `token_types.yaml` の並び
- 状態：**未採点**（2026-11-23）

## 1. 採点する 10 件

行の値は記入例からの写しです（台帳の列名つき）。採点者は、必要なら記入例の設計書（`design.md`）と台帳の同じ行を開いてよいものとします。

### T01：シナリオ B `claims.yaml` の `C-task-id`（`task_id`）

- decision: 採用
- rationale: タスク単位の短命のトークンと、監査の記録を相関させる。タスクを取り消したら、STS はそのタスクの交換を断る（ケーススタディ C9）
- assumption: 1 つのタスクは 1 つの利用者と 1 つのエージェントに属する
- revisit_trigger: 複数の利用者が 1 つのタスクを共有するとき
- refs: p10-per-tool-scopes; p10-delegation-chain-depth
- evidence: jwt-claims-casestudy@080b8da:C9

### T02：シナリオ A `token_types.yaml` の `DPOP`（dpop_proof）

- decision: 却下
- rationale: 送信者制約を付けない（issuance_profile.sender_constraint）
- assumption: AT は BFF のサーバーと API の間だけを通り、ブラウザに出ない（I29・I30 の回答と同じ前提）
- revisit_trigger: AT をブラウザや第三者のクライアントに渡すようになったとき

### T03：シナリオ B `token_types.yaml` の `LOGOUT`（logout_token、max_lifetime 120）

- decision: 採用
- rationale: 社員の無効化・セッションの削除を、portal の BFF のセッションに 0 秒で反映する。シナリオ B は退職・異動の直後の古いトークンでの操作 （ケーススタディ B11・B12）を重点にしており、次のリフレッシュの失敗を待つ（最大 330 秒）のでは遅い

### T04：シナリオ B `claims.yaml` の `C-aud`（`aud`）

- decision: 採用
- rationale: ホップごとに宛先を 1 つに絞り、受け取ったトークンを別の宛先へ転送させない（ケーススタディ B3・C2・C13）。外部の IdP の宛先の表し方の違い（Cognito は aud がない）は入口で吸収する
- assumption: KC_AT の aud は Keycloak の Audience マッパーで固定する（Keycloak は RFC 8707 の resource パラメータに対応していない）。組織の sts は resource indicator の値を 1 つだけ受け、その値を aud に書く
- revisit_trigger: 1 つのトークンで 2 つ以上のサービスを呼ぶ設計にするとき
- refs: RFC 8707 §2; p06-narrow-downstream; p10-mcp-authorization
- evidence: jwt-claims-casestudy@080b8da:B3、B16、C2、C13

### T05：シナリオ B `token_types.yaml` の `TXN`（txn_token、max_lifetime 300）

- decision: 採用
- rationale: orders が ledger を社員の文脈で呼ぶとき、呼び出しの連鎖全体で同じ取引の文脈（txn・誰の権限で・どのワークロードが求めたか）を改変せずに運ぶ。内部の AT を下流へ渡さない
- revisit_trigger: draft-ietf-oauth-transaction-tokens が RFC になったとき、または版が上がってクレーム（txn・req_wl・tctx・rctx）の定義が変わったとき
- refs: draft-ietf-oauth-transaction-tokens-11 §6; p06-transaction-tokens

### T06：シナリオ B `claims.yaml` の `C-rfc-roles`（最上位の `roles`）

- decision: 却下（rejection_kind: 代替あり）
- rationale: 最上位の roles（RFC 9068 §2.2.3.1）は IdP ごとに意味と語彙が違う（Auth0 では予約名で黙って外れる。ケーススタディ B20）。組織の名前空間の roles に正規化して載せる
- assumption: 入口が全 IdP のロールを組織の語彙に写す
- refs: p03-auth0-namespace

### T07：シナリオ B `token_types.yaml` の `JAR`（jar_request_object）

- decision: 却下
- rationale: 認可要求は PAR で送る。要求の完全性は PAR の端点でのクライアント認証で守り、Request Object に署名しない
- assumption: 認可要求の否認防止を求める規則（FAPI 2.0 の Message Signing など）の対象ではない（I31 の回答）
- revisit_trigger: 認可要求の署名を求める規則の対象になったとき

### T08：シナリオ B `claims.yaml` の `C-preferred-username`（`preferred_username`）

- decision: 却下（rejection_kind: 禁止）
- rationale: 変わりうる名前で、識別にも認可にも使えない（Okta の AT の sub がログイン名だった例と同じ誤り。ケーススタディ B13）
- assumption: portal に profile スコープの preferred_username マッパーを付けない
- refs: p04-immutable-identifiers

### T09：シナリオ A `token_types.yaml` の `LOGOUT`（logout_token）

- decision: 却下
- rationale: IdP 側でセッションが終わったこと（管理者による削除、利用者の無効化、レルムの無効化）は、BFF が次に RT でリフレッシュするときの失敗で検知し、BFF は自分のセッションを終える。AT の寿命が 300 秒なので、要求が続く利用者では最大 330 秒で反映する。要求の無い利用者は次の要求で反映する。300 秒の遅れを許すので、ログアウトトークンを受ける公開の受け口と、その検証を作らない
- assumption: IdP 側のセッションの終了を BFF のセッションに反映するまで、最大 330 秒の遅れを許す
- revisit_trigger: IdP 側のセッションの終了を 330 秒より早く BFF のセッションに反映する必要が出たとき

### T10：シナリオ A `claims.yaml` の `C-auth-time`（`auth_time`）

- decision: 既定どおり
- rationale: Keycloak の basic スコープが sub と一緒に出す。外すには sub だけの独自のスコープを作る必要があり、JSON で 23 バイト（"auth_time":と 10 桁とカンマ）のために設定の差分を増やさない。API は読まない
- refs: p06-stage-map

## 2. 採点表（1 回目・2 回目で同じ表を別々に埋める）

各セルに「満」（満たす）か「否」（満たさない）を書きます。「否」には 1 行の理由を右の欄に書きます。合否は 6 観点のすべてが「満」なら「合」。

| 項目 | RR1 | RR2 | RR3 | RR4 | RR5 | RR6 | 合否 | 「否」の理由 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T01 |  |  |  |  |  |  |  |  |
| T02 |  |  |  |  |  |  |  |  |
| T03 |  |  |  |  |  |  |  |  |
| T04 |  |  |  |  |  |  |  |  |
| T05 |  |  |  |  |  |  |  |  |
| T06 |  |  |  |  |  |  |  |  |
| T07 |  |  |  |  |  |  |  |  |
| T08 |  |  |  |  |  |  |  |  |
| T09 |  |  |  |  |  |  |  |  |
| T10 |  |  |  |  |  |  |  |  |

## 3. 採点の手順（調整役が行う）

1. 1 回目：作成とは別の LLM のセッション（会話の履歴を引き継がないもの）を開き、次だけを渡す：`templates/review/rationale_rubric.md`、この文書の 1. と 2.（3. 以降は渡さない）、記入例のディレクトリ（コミット 9202586）。指示は下の「渡す指示」
2. 2 回目：1 回目と別の、さらに新しいセッションで、同じ資料と同じ指示を渡す（1 回目の結果は渡さない）。または作成者が 1 日以上空けて、1 回目を見ずに採点する
3. 2 つの表を、下の 4. の様式で突き合わせ、一致率を記録する
4. 一致率の低い観点（下の目安）は、`rationale_rubric.md` の観点の文と例を直す PR の材料にする

渡す指示（全文）：

> 添付の採点基準（rationale_rubric.md）の RR1〜RR6 で、添付の 10 件の理由（T01〜T10）を採点してください。各観点に「満」か「否」を付け、「否」には 1 行の理由を書き、2. の表を埋めて返してください。採点に必要なら、添付の記入例の設計書と台帳を開いてかまいません。ほかの人の採点の結果は渡していません。

## 4. 記録の様式

| 回 | 実施日 | 採点者（セッション・モデル） | 渡した資料（パスとコミット） |
| --- | --- | --- | --- |
| 1 回目 |  |  |  |
| 2 回目 |  |  |  |

| 指標 | 値 |
| --- | --- |
| 観点ごとの一致の割合（RR1〜RR6、各 10 件中） |  |
| 全体の一致の割合（60 セル中） |  |
| 合否の一致の割合（10 件中） |  |
| Cohen の κ（全 60 セル。参考） |  |
| 一致しなかったセル（項目と観点）と、両方の理由 |  |

- 目安（筆者の提案、追跡 #5）：観点ごとの一致が 7／10 未満なら、その観点の文と例を直す
- 2 回とも LLM の場合は「人による採点ではない」と書く
