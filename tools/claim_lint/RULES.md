# claim_lint の規則

設計書の台帳（`claims.yaml`）・トークン目録（`token_types.yaml`）・カタログへの回答（`catalog_answers.yaml`）を検査する規則です。#16（縦の一本）で R1・R2・R8 とスライドの参照の解決を作り、#17 で網羅の規則（R2 の強化・R3・R3b・R4・R6・R9・R10。`tools/claim_lint/coverage.py`）を足しました。意味の規則（L1〜）は #6 で足します。

```
python tools/claim_lint templates/examples/scenario-a                 # 人向けの表
python tools/claim_lint templates/examples/scenario-a --format json   # 機械向けの JSON
python tools/claim_lint <設計書のディレクトリ> --profile lite         # Lite：R2・R4 を warn に下げる（R6 はもとから warn）
```

error が 1 件でもあれば終了コード 1 です。error の規則は抑止できません（`templates/CONTRIBUTING.md` の 2.）。

| ID | 内容 | 重大度（Full／Lite） | 根拠 |
| --- | --- | --- | --- |
| SCHEMA | `templates/registry/claims.schema.json`・`token_types.schema.json`・`hops.schema.json`（台帳 v1、template_version 0.2.0）の検証（JSON Schema 2020-12）。YAML の日付は文字列として読む。同じキーを 2 回書くと失敗する（LOAD） | error | #3 |
| R1 | 必須の列が空でない。下の「R1 の必須の列」。スライド 134 の 12 項目を載せる行の必須の列にし、欠ければ検出する（req:p11-registry-fields.R13）。対応表の要件：req:p00-claims-are-contracts.R4 req:p00-why-hard.R3 req:p02-check-before-creating.R2 | error／error | slide:p11-registry-fields、#3 |
| R2 | カタログ（`templates/catalog/`）の全イベントに「該当」か「対象外」の回答がある。「対象外」には `assumption`（起きない前提）と `breaks_when`（崩れる条件）があり、どちらも `tools/catalog_check.py` の種の項目と同じ中身の検査（10 字以上、同じ文字の繰り返しでない、イベントの ID・名前そのものでない）と、仮の値（TODO・TBD・xxx・未定など）でないことの検査を通り、互いに同じでない。「該当」には関係するトークン種別か説明がある。回答の `token_types` は、トークン目録（`token_types.yaml`）の ID でなければならない（目録にない ID は、どちらのプロファイルでも error）。Lite だけ、下の「Lite の既定の回答の引き継ぎ」を使える。カタログにない ID への回答と、同じイベントへの 2 つの回答は、どちらのプロファイルでも error。**理由が妥当かは機械では判定しない**（「対象外です対象外です。」のような文は通る）。妥当性は抜き取りの点検（#13）で見る | error／warn | `templates/CONTRIBUTING.md` の 2.「対象外の書き方」、report Q9 の R2、#4 の改訂（縮小 Lite）。10 字は筆者の提案（tracking #16） |
| R3 | 設計書の `idp` で、IdP の契機の一覧を確かめる。分類は `sources.md` の「契機の一覧を持つ IdP と、持たない IdP」による。**一覧あり・カタログの IdP**（Auth0：`auth0-protocol`・`auth0-trigger`・`auth0-grant`。Keycloak：トークン端点の grant の一覧 `keycloak-grant-types`（`OAuth2GrantType` の実装 10 個）と `keycloak-settings`）は、`seeds.yaml` で `idp: <IdP>` の一覧について、`catalog_check.closure()` の差集合（どの行にもひもづかず、対象外でもない項目）と件数の食い違いを error にする。Keycloak にはフックが呼ばれる契機の一覧はないが、grant の一覧は列挙できる（PR #33 の独立点検）。**一覧あり・カタログにない IdP**（Cognito。#21）は、設計書の `idp.trigger_list` に一覧の全項目と、ひもづくイベントか対象外（前提と崩れる条件）を書き、`idp.trigger_list_source`（url・verified_on）を付ける。**文書で未確認**（Entra・Okta：一覧があるかを文書で確かめていない。`unverified.md` の V07・V08）と、**一覧が存在しない**（設計書が `idp.enumerable: false` と宣言し、`idp.enumerable_source` に確かめた出どころを書いた IdP）は、R9 の `searched` に、その IdP の名前を含む具体的な出どころ（URL、ファイルのパス、15 字以上の文書の名前）を書く。2 つは別のメッセージを出す。一覧の有無が分からない IdP は `idp.enumerable` を宣言する。`idp` が無ければ error | error／error | #17、`templates/catalog/sources.md` |
| R3b | 設計書の IdP の列（カタログの `idp.<IdP>`）で `hook_invoked: no` の発行イベントに「該当」と答え、その発行で独自クレームを運ぶ（クレームの `issue_events` にそのイベントがあるか、回答の `token_types` とクレームの `carried_in` が重なる）なら error。`unknown`・`conditional` は warn で、書き手が回答の `hook_checked` に確かめた方法を書けば info に下げる（`hook_checked` の中身が本当かは機械では確かめない）。発行イベントの「該当」に `token_types` が無ければ error（照合を外せないように。照合にはカタログの `tokens_issued` の種類に当たる目録の行を使う）。独自クレームは、名前空間の付いたクレームと、IANA の JWT Claims にない名前で `usage` が protocol でないもの（IdP 自身が書く Keycloak のペイロードの `typ` は数えない）。発行者が IdP でない行（`issuer` が gateway・tts など）と、IdP が起こさない行（`occurs: no`）は見ない。カタログの IdP でない IdP は照合できないので warn。この規則に結びつく要件 p03-cognito-pre-token-hook.R2（Cognito の V2_0 の M2M の検出がない）と p06-issuance-hook.R2（「失敗する発行」の欄がカタログにない）は、足りない部分があるので未着手のまま（PR #33 の独立点検） | error（no・token_types が無い）・warn（unknown・conditional）／同じ | slide:p03-cognito-pre-token-hook、slide:p06-issuance-hook、#2 の `hook_invoked` |
| R4 | 設計書の `subject_states` に、カタログの行列（`subject_state_matrix.md`）の 7 状態 × 7 層の全セルがあり、結果が「発行・再計算・失効・影響なし」のどれかで、根拠（`basis`）が R2 と同じ中身の検査を通る（「影響なし」も根拠が要る）。使わない層は `unused_layers` に理由を書けば、その層のセルを省ける。ただし、その層の採用の行が `token_types` にあれば error。セッションの 2 つの層（どちらも `kind: session`）は `stored_at` で見分ける（`idp` なら IdP のセッション、それ以外は RP・BFF のセッション）。`stored_at` が無くて見分けられないときは warn。同じ根拠の文が多くのセルに並ぶことは検査しない（抜き取りの点検で見る） | error／warn | #17、#2 の行列、slide:p08-stale-claims |
| R6 | 主体の種類（利用者・ワークロード・システム。slide:p05-three-principals）× 発行イベント（「該当」と答えたもの）× 段階（カタログのそのイベントの `stage`）について、2 因子ずつの組（主体×イベント、主体×段階、イベント×段階）が、`pairwise.combinations` のどれかの組み合わせ（`note` つき）に一度は出る。主体の種類には「該当」か「対象外＋理由」を答える。**pairwise を網羅の目標にするのは筆者の提案（author-proposal、tracking #17）** で、下の「R6 の証拠の状況」のとおり、拾える割合には幅がある（req:p05-three-principals.R3） | warn／warn | report の R6（NIST ACTS）、`research/template-design/notes/coverage_lifecycle.md` |
| R8 | トークン種別ごとの最悪のサイズと、経路の上限。下の「R8 の計算」。配列の max_items と overflow_strategy（切り詰めは書けない）を求め、超えたら「載せるか、問い合わせるか」へ誘導する（req:p02-roles-groups-entitlements.R4 req:p04-carry-or-query.R3 req:p04-size-budget.R1 req:p04-size-budget.R2 req:p06-edge-exchange.R3 req:p11-registry-fields.R7） | error／warn／info（Lite も同じ） | report Q9。しきい値は筆者の提案（tracking #16） |
| R9 | 設計書の `outside_enumeration`（「この列挙の外に契機はないか」）に、回答（`answer`）・回答者（`respondent`）・日付（`date`）・探した範囲（`searched`：見た資料・図）がある。回答が「なし」だけなら error。同じ意味の「ありませんでした」「見つかりませんでした」「特に見つからなかった」「None found」「N/A」と、その繰り返し・括弧の中の補足だけを足したもの（「なし（特になし）」）も「なし」とみなす（`coverage.py` の `NONE_WORDS`。列挙した語だけを落とす）。仮の値（TODO・TBD・xxx・未定など、同じ文字の繰り返し）は、回答・回答者・探した範囲のどれでも error。日付は実在の日で、実行した日の翌日より後でない。探した範囲の各項目は短すぎず、少なくとも 1 つは具体的な出どころ（URL、ファイルのパス、15 字以上の文書の名前）。見つかった契機（`found`）には扱い（`handled_as`）を書く | error／error | report の R9（Threat Modeling Manifesto の 4 つ目の問い）、#11 の約束の範囲 |
| R10 | 出どころ・上限の `review_by` が過ぎている：`seeds.yaml` の一覧、カタログの行（`issue_events`・`use_events`・`token_kinds`）、`path_limits.yaml`（`--limits` で渡したファイル）の上限、`token_types` の `size.path` にその場で宣言した上限（スキーマに `verified_on`・`review_by` を足した）。上限のファイルとその場の宣言で `review_by` が無い・日付でないときも warn（カタログの行と一覧は `catalog_check` の COLUMNS・SOURCES が守る）。ファイルごとに 1 件にまとめ、ID を並べる。範囲はカタログと上限だけで、設計書が自分で書く IdP の挙動（design.md の「Keycloak 26.3 からの既定」など）の確認日は見ない（req:p03-recent-changes.R1） | warn／warn | slide:p03-recent-changes、`sources.md`（見直しの期限は確かめた日の 90 日後。筆者の提案、tracking #17） |
| REF | ファイルの間の参照が実在する（#3 の台帳 v1 で追加）：台帳の `answers`・`does_not_answer` は `templates/registry/questions.yaml` の `questions` の ID（`pending` の問いはスライドに同じ文言がないので参照できない）、`paired_id`・`alt`（`C-` の行）・`namespaces[].namespace_version`・トークン目録の `tenant_binding.claim`・ホップの `custom_claims`・`forwarded_headers[].claim` は台帳の行、ホップの `token_type` はトークン目録、`upstream` はホップ。ホップの `id` は重複せず、`upstream` をたどって循環しない（自分自身を含む）。`data_category_extensions` の `key` は `parent` の子（`parent` + `.` で始まる）。`hops.yaml` が無いときは info（交換・作り直しのホップがない設計では書かなくてよい） | error（`hops.yaml` が無いのは info） | #3。シナリオ A で誤検知 0 件（足した直後の指摘 0 件） |
| SLIDE | `refs` の `guide-slide` の ID と、入力のファイルの中の `slide:<id>` が、実在のスライドを指す（`tools/check_slide_refs.py` の解決を使う） | error | #15 |

カタログそのものの検査（列、種になる一覧との差集合、主体の状態の行列、`sources.md` の件数）は、設計書ではなくカタログの検査なので `tools/catalog_check.py` に分けました（#2）。R3 はその `closure()` を、R2・R4 は `_weak_reason()` を、R4 は `seed_items()`・`STATES`・`LAYERS`・`RESULTS` を使います。

## 網羅の規則の入力（`catalog_answers.yaml` の節）

```yaml
idp: {name: keycloak, version: "26.8"}       # R3・R3b・R2（Lite の引き継ぎ）。カタログにない IdP は enumerable・trigger_list
answers:
  - {event: I04, answer: 対象外, inherit: idp-default, setting_checked: "…"}   # Lite だけ（下）
  - {event: I25, answer: 該当, token_types: [AT], note: "…", hook_checked: "…"} # hook_checked は R3b の unknown を info にする
subject_states:                               # R4
  unused_layers: {Logout Token: "使わない理由"}
  states:
    subject-states/suspended:
      AT: {result: 影響なし, basis: "許す遅れか対策"}
pairwise:                                     # R6
  subject_kinds: {利用者: {answer: 該当}, ワークロード: {answer: 対象外, reason: "…"}, システム: {answer: 対象外, reason: "…"}}
  combinations:
    - {subject: 利用者, event: I01, stage: ①, note: "検討したこと"}
outside_enumeration:                          # R9
  answer: "何を探して、何が無かったか（見つかったか）"
  respondent: "…"
  date: "2026-11-22"
  searched: ["見た資料・図", "…"]
  found: [{name: "…", handled_as: "…"}]
```

記入例は `templates/examples/scenario-a/catalog_answers.yaml` です。

## Lite の既定の回答の引き継ぎ

#4 の改訂（縮小 Lite。`research/template-design/gate1.md` の 10.）に合わせました。`--profile lite` のときだけ、「対象外」の回答に `inherit: idp-default` と `setting_checked` を書けば、`assumption`・`breaks_when` を省けます。`setting_checked` には、どの設定を、どこで、いつ確かめたかを書きます。

- **引き継げるイベント**：カタログの行の `idp.<IdP>.lite_inherit: true` の印があるものだけです。Keycloak の I03・I04・I05・I07 に付けました。gate1.md の 10. の「引き継ぐ」4 件で、どれもクライアントの設定のスイッチ 1 つで止めていて、指摘が出ていません。I03 はクライアントポリシーの executor で、`stop_setting` の `scope` は realm です。それでも gate1.md の分類に合わせました。
- **手で書くイベント**：印のないイベントは手で書きます。
  - 指摘が出た行（I06・I09・U07・U10 など）
  - レルム・クライアントの既定に依存する行（I08）
  - 利用イベント（U05・U08 など）
  - Auth0 の行（gate1.md の分類がない）
  - カタログの IdP でない IdP
- **`setting_checked` の検査**：カタログの `stop_setting.setting` の英字の語（6 字以上）のどれかを含むことを求めます。例：I04 なら Direct か Grants。
- **Full では**：`inherit` を書くと R2 の error です。

PR #33 の独立点検より前は、`stop_setting.scope == client` で判定していました。そのため I08 が引き継げ、I03 が引き継げない、という #4 と逆の結果になっていました。印は `catalog_check` が確かめます（`true` だけ、`stop_setting` のある発行イベントだけ）。新しく「指摘が出た行」が見つかったら、印を外します。「指摘が出たか」は機械では判定できません。

## R6 の証拠の状況

R6 の目標（2 因子の組をすべて一度は検討する）は、組み合わせテストの知見を設計の検討に当てはめた筆者の提案です（tracking #17）。根拠は NIST の組み合わせテストの研究だけで、それもソフトウェアの障害についてのものです。NIST が示す 10 種類のアプリケーションのデータでは、2 因子までの組み合わせで起きた障害の割合はおおよそ 47%〜97% と幅があります（グラフからの読み取り。[NIST ACTS](https://csrc.nist.gov/projects/automated-combinatorial-testing-for-software/combinatorial-methods-in-testing/interactions-involved-in-software-failures)。`research/template-design/report.md` の訂正）。設計の想定漏れを pairwise でどれだけ拾えるかは、測っていません。そのため R6 は warn にとどめ、昇格もしません。対象は設計書が「該当」と答えた主体と発行イベントだけなので、答えなかった主体・イベントの漏れは R2 と R9 で拾います。

## 重大度の決め方と、シナリオ A での誤検知の数

新しい規則は warn から始め、#17 の表が error としていて、シナリオ A（`templates/examples/scenario-a`）で誤検知が 0 件のものだけを error にしました（2026-11-22 に測定）。測り方：規則を足した直後に、記入例に手を入れずに実行し、出た指摘を 1 件ずつ「正しい指摘（記入例に欄が無い・値を確かめていない）」か「誤検知」かに分けました。その後、記入例に欄を足して再び実行しました。

| 規則 | 足した直後の指摘 | 誤検知 | 欄を足した後 | 重大度 | 理由 |
| --- | --- | --- | --- | --- | --- |
| R2（中身の検査を足した） | 0 | 0 | 0 | error（既存。下げない） | 対象外 49 件のすべてが新しい検査を通った（I34 を足した後は 50 件） |
| R3 | error 1（`idp` がない） | 0 | info 1 | error | 正しい指摘。シナリオ A で動いたのは Keycloak の分岐だけ。測ったときは一覧なしの分岐で、独立点検の後は一覧ありの分岐（`keycloak-grant-types`）。**Auth0・Cognito・文書で未確認・一覧が存在しないの分岐は、どの設計書でも測っていない**（テストの例だけ） |
| R3b | warn 1（`idp` がない） | 0 | warn 2（I25・I26 が unknown） | error（no）・warn（unknown） | unknown の 2 件は正しい指摘（カタログで確かめていない）。**`no` の分岐はシナリオ A で一度も動いていないので、誤検知は測っていない**（機会が 0 回）。また、最初の実装は Keycloak の `typ`（IdP 自身が書く protocol のクレーム）を独自クレームに数え、2 件の指摘に並ぶクレームの一覧を誤らせた。指摘そのものは正しかったので誤検知には数えず、「指摘の中身の誤り 1 件」として記録する。定義は直した |
| R4 | error 1（`subject_states` がない） | 0 | 0 | error | 正しい指摘。欄を足した後の 35 セル＋使わない層 2 つで誤検知 0 |
| R6 | warn 1（`pairwise` がない） | 0 | info 1 | warn | 上の「R6 の証拠の状況」により上げない |
| R9 | error 1（`outside_enumeration` がない） | 0 | 0 | error | 正しい指摘。独立点検の後に足した検査（日付、仮の値、具体的な出どころ）でも、シナリオ A の回答は通った |
| R10 | 0 | — | 0 | warn | **測っていない**。測った日は、どの期限（2027-02-20）より前だった。期限切れは出どころの見直しの合図で、設計書の誤りではない |

シナリオ A は 1 件だけなので、誤検知 0 件は弱い証拠です。ほかの設計書で誤検知が出たら、規則を直す PR を出します（error の抑止はしない）。

## R1 の必須の列

| 行の種類 | 必須の列 |
| --- | --- |
| すべてのクレーム | `id`・`name`・`decision`・`rationale`（R1 は、空白だけの文字列と、空白だけの要素しかない配列を空とみなす） |
| `採用`・`既定どおり`（トークンに載せる行） | 上に加えて `namespace`（最上位は `null`）・`type`・`shape`・`description`・`not_meaning`・`usage`・`issuers`・`authoritative_writer`・`issue_events`・`consumers`（読む受け手がいなければ `[]`）・`carried_in`・`on_missing`・`max_bytes`（配列は `max_items` も）・`overflow_strategy`・`pii_category`・`log_policy`・`owner`・`source_system`・`volatility`・`propagation_delay`・`status`・`data_category`・`confidential_from`（改ざん防止だけで足りるなら `[]`。v1 で足した） |
| `採用`・`却下` | `refs`・`assumption`・`revisit_trigger` のうち 2 つ以上（#3 の「判断」の区分） |
| トークン種別 | `id`・`kind`・`decision`・`rationale`・`format`。`採用`・`既定どおり` は `purpose`・`issuer`・`holder`・`max_lifetime`・`stored_at`・`transport`・`revocation`・`visible_to`（RT とセッションは `idle_timeout` も）。JWT はさらに `typ`・`alg_allowlist`・`issuers`・`key_rotation`・`jwe`（使わないなら `{used: false}`。v1 で `visible_to`・`jwe` を足した）。ヘッダー（Authorization・Cookie）で運ぶ JWT は `size`（R8 の入力） |

スライド 134（slide:p11-registry-fields）の 12 の項目は、載せる行の必須の列に入っています。項目と列の対応は `templates/registry/README.md` の「スライド 134 の 12 項目と台帳の列」にあります。12 番目の「変更履歴」は列ではなく Git の履歴で持ちます。

## R8 の計算

JWS（コンパクト形式）のエンコード後の長さを、宣言の値から計算します（`tools/claim_lint/r8.py`）。

```
最悪のサイズ = ceil(4/3 × ヘッダー) + ceil(4/3 × ペイロード) + ceil(4/3 × 署名) + 2（ドット 2 つ）
              Authorization の Bearer で運ぶなら + 7（"Bearer "）
```

- `ceil(4n/3)` は、n バイトを base64url（パディングなし）にした長さです（RFC 7515 §2、RFC 4648 §5）。
- ペイロードは、載る全クレームの JSON（空白なし）の UTF-8 のバイト数です。文字列は `max_bytes`＋引用符 2、数値は `max_bytes`（桁数）、配列は `2 ＋ max_items × 要素 ＋（max_items − 1）`、メンバーは `キー（引用符つき）＋ コロン ＋ 値`、オブジェクトは `2 ＋ メンバー ＋（メンバー − 1）`。`namespace` の付いたクレームは、名前空間の名前をキーにした 1 つのオブジェクトにまとめます。
- ヘッダーは、`size.header.params` から同じ規則で計算し、`serializer_extra_bytes`（発行者の JSON の書き出しが足す空白）を足します。Keycloak 26.8.0 では 4 バイトでした（見本トークンの実測。`research/template-design/gate1.md`）。
- 署名の長さは、HMAC は RFC 7518 §3.2、ECDSA は RFC 7518 §3.4、RSA（RS・PS）は鍵の長さ（RFC 8017 §8.1.1・§8.2.1）、Ed25519 は 64 バイト（RFC 8032 §5.1.6）です。
- 経路の上限は `tools/claim_lint/path_limits.yaml`（一次資料で確かめた値だけ）か、根拠つきでその場に宣言した値です。確かめていない値は既定に入れません（`research/template-design/unverified.md` の V01〜V04）。
  - `header_field` の上限（nginx・Apache httpd・HTTP.sys の MaxFieldLength）とは、`Authorization: Bearer <トークン>` の行（ヘッダー名を含む）を比べます。ヘッダー名を数えるのは保守側に倒した読み方で、各サーバーが数えるかは確かめていません（筆者の提案。tracking #16）。
  - `all_headers` の上限（Tomcat・Node.js・HTTP.sys の MaxRequestBytes）とは、上の行に `size.other_headers_bytes`（要求行とほかのヘッダーの見積もり）を足して比べます。宣言がなければ error です。
  - HTTP/2・HTTP/3 の圧縮による割り引きはしません（V03）。

| 判定 | 条件 |
| --- | --- |
| error | 最も厳しい上限を超える。配列に `max_items` がない（値域が無制限）。配列に `overflow_strategy` がない。載る行に `max_bytes` がない。`carried_in` のトークン種別が目録にない。経路の上限が既定の一覧にも宣言にもない。署名の長さが決まらない |
| warn | 最も厳しい上限の 75% を超える（report Q9 は 50〜75% としている。上の端を使った。筆者の提案、tracking #16） |
| info | 計算の結果。同じクレーム（`usage` が protocol でないもの）が 2 つ以上のトークン種別に載る（重複の候補） |

`overflow_strategy` に切り詰め（truncate）は書けません（スキーマの列挙にない）。error のメッセージは「載せるか、問い合わせるか」（slide:p04-carry-or-query）へ誘導します。軽量アクセストークン（Keycloak）は、解決策として誘導しません。

### 限界

R8 は宣言の値を信じます。宣言と実際の発行のずれは、見本トークンとの照合（`tools/tests/test_claim_lint.py` の golden）と、発行されたトークンの計測で補います。配列は `max_items × max_bytes` で数えるので、要素の長さがばらつく配列では実際より大きく出ます（安全側）。
