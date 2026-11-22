# 関門 1 の資料（#16 縦の一本：シナリオ A、Keycloak）

#16 の終わりに、関門 1（続ける／絞る／方針を変える）を判定するための資料です。**判定はこの文書ではしません。** 判定は筆者が、5. のレビューの結果を入れてから #16 に記録します。

- 基準日：2026-11-22
- 作成方法：生成 AI（Claude、Opus 5.5）を使って作った。人による点検は未実施。別の LLM のセッションでのレビューは未実施（5.）
- 成果物：`templates/catalog/`（v0 の一部）、`templates/registry/`（スキーマ v0）、`templates/examples/scenario-a/`（記入例）、`tools/claim_lint/`、`.github/workflows/claims.yml`、`templates/casestudy-deviations.yaml`、`research/template-design/v0-columns.md`

## 1. R8 の照合（見本トークン）

### 発行の条件

| 項目 | 値 |
| --- | --- |
| IdP | Keycloak 26.8.0（`quay.io/keycloak/keycloak:26.8.0`、image id `sha256:27b3230fbabb…eb05741`）、`start-dev --import-realm`。WSL（Ubuntu-24.04）の Docker 29.9.2。使い終えたコンテナは削除した |
| レルム | ケーススタディ `jwt-claims-casestudy@080b8da` の `kc/import/t1.json`（試験用のレルム・鍵・利用者 alice）。ケーススタディのファイルは変えていない |
| クライアント | 縦の一本のために、管理 API で `saas-web-a` を足した：機密クライアント、認可コード＋PKCE（S256）、Direct Access Grants は OFF、ヘッダーの typ を at+jwt、Full Scope Allowed は OFF（スコープのロールは approver・tenant-admin）、既定のクライアントスコープは basic だけ、マッパーは記入例のとおり（名前空間の tenant_id・user_id・roles・v、Audience saas-api） |
| 発行 | 2026-11-22、認可コード＋PKCE（イベント I01） |
| 保存 | 秘密を含まない（鍵はコンテナの中だけにあり、コンテナは削除した。トークンは 300 秒で失効済み）ので、トークンそのものを `tools/tests/fixtures/claim_lint/golden/token.json` に置いた。secret scan の除外は `.gitleaks.toml` に理由つきで 1 ファイルだけ |

### 計算と実物

R8 の式：`ceil(4/3 × ヘッダー) + ceil(4/3 × ペイロード) + ceil(4/3 × 署名) + 2`（Bearer で運ぶなら + 7）。入力は、見本トークンの値の長さを宣言にしたもの（`tools/tests/fixtures/claim_lint/golden/claims.yaml`・`token_types.yaml`）。

**ヘッダー**：`alg`（RS256、5）・`typ`（at+jwt、6）・`kid`（43）

```
{"alg":"RS256","typ":"at+jwt","kid":"<43>"}  をコンパクトな JSON として数える
  = 2（波かっこ） + (5+1+7) + (5+1+8) + (5+1+45) + 2（カンマ） = 82
+ serializer_extra_bytes 4（Keycloak は "typ" : "at+jwt"、"kid" : "…" と、コロンの前後に空白を入れる）
  = 86 バイト（実物の復号したヘッダーも 86 バイト）
```

**ペイロード**（メンバーごとに「キー（引用符つき）＋コロン 1＋値」）

| メンバー | キー | 値 | 計 |
| --- | --- | --- | --- |
| exp | 5 | 10 | 16 |
| iat | 5 | 10 | 16 |
| auth_time | 11 | 10 | 22 |
| jti | 5 | 45（43＋引用符 2） | 51 |
| iss | 5 | 34（32＋2） | 40 |
| aud | 5 | 10（8＋2） | 16 |
| sub | 5 | 38（36＋2） | 44 |
| typ | 5 | 8（6＋2） | 14 |
| azp | 5 | 12（10＋2） | 18 |
| sid | 5 | 26（24＋2） | 32 |
| scope | 7 | 8（6＋2） | 16 |
| `https://claims.example.com/` | 29 | 111 | 141 |
| 　tenant_id | 11 | 4 | 16 |
| 　user_id | 9 | 38 | 48 |
| 　v | 3 | 3 | 7 |
| 　roles | 7 | 27（2＋(10＋2)×2＋カンマ 1） | 35 |

名前空間のオブジェクト：16＋48＋7＋35＝106、波かっこ 2、カンマ 3 で 111。最上位：メンバーの計 426、波かっこ 2、カンマ 11 で **439 バイト**（実物の復号したペイロードも 439 バイト）。

`roles` の値は `["approver","tenant-admin"]`（8＋12＝20 バイト）。R8 は配列を `max_items × max_bytes` で数えるので、見本の照合では `max_bytes` を 1 件あたりの平均の 10 にして、積が実物の 20 バイトと同じになるようにした。最大の 12 で宣言すると 4 バイト大きく出る（安全側）。別のテスト（`test_r8_golden_concrete_values_match_actual_exactly`）では、復号したペイロードの値そのものを同じ関数で数え、439 バイトで一致することを確かめた。

**署名**：RS256、鍵 2048 ビット → 256 バイト

```
ceil(4/3 × 86) + ceil(4/3 × 439) + ceil(4/3 × 256) + 2
= 115 + 586 + 342 + 2
= 1045
実物のトークンの長さ：1045（ヘッダー 115・ペイロード 586・署名 342 文字）
差：0 バイト
Bearer の行の値：1045 + 7 = 1052
```

実行の記録（`python -m pytest -q tools/tests/test_claim_lint.py -k golden`）：

```
....                                                                     [100%]
4 passed, 22 deselected in 0.08s
```

- `test_golden_token_fixture_is_consistent`：保存したトークンを復号すると、保存したヘッダー・ペイロードの JSON と一致し、長さ 1045、署名 256 バイト
- `test_r8_golden_declared_values_match_actual_exactly`：宣言から計算した 1045 と実物の差が 0
- `test_r8_golden_concrete_values_match_actual_exactly`：値そのものから数えても一致
- `test_r8_golden_without_serializer_bytes_is_off_by_five`：ヘッダーの空白を足さないと 5 文字足りない（最初の計算で実際に起きたこと。下の「分かったこと」）

### 分かったこと

- 最初の計算（ヘッダーをコンパクトな JSON として数えた）は、実物より 5 文字短かった（110 と 115）。Keycloak 26.8.0 の JOSE ヘッダーには空白が入る。R8 のヘッダーの計算は「発行者の書き出し方」に依存するので、`serializer_extra_bytes` を IdP と版ごとに持つ必要がある（`v0-columns.md` の 1. の #10）。この差は、宣言だけの静的な計算では見つからず、実物との照合で見つかった。
- 記入例の宣言の最悪のサイズは 1258 バイト（Bearer の行で 1280 バイト）で、見本の 1045 バイトより 213 バイト大きい。差は、`iss`（宣言 63・実物 32）、`sid`（36・24）、`scope`（64・6）、`azp`（32・10）、`tenant_id`（32・2）などの上限の取り方による。
- ケーススタディの既定のクライアント（profile・email・roles などのスコープ付き）の AT は 1398 バイト（ケーススタディ `results/measurements.json` の `A.keycloak_token_bytes.alice`）。記入例の構成では 1045 バイト。

## 2. 記入にかかった時間

| 項目 | 値 |
| --- | --- |
| 書き手 | LLM（Claude、Opus 5.5）。人ではない |
| 人の 4 時間の基準 | **LLM の作業時間からは測れない**。LLM は調べる・書く・検査を回すの速さが人と違い、記入の手間の代わりにならないため、時間を記録していない |
| 記入した欄 | `claims.yaml` 25 行、`token_types.yaml`（発行方式 8 項目・目録 9 行）、`catalog_answers.yaml` 19 件、`design.md`（Lite の欄と、#4 の 5・7・8・10・11） |
| 人の記入時間（筆者が記入） | （未記入：筆者が同じ記入例を、テンプレートを見ながら書き直した時間を測って書く。測り方の案：`design.md` を消し、`claims.yaml` の C-tenant-id・C-roles・C-auth-time の 3 行と、`design.md` の 6・8・9 を書くまで） |

## 3. 迷った点（欄・内容・解決にかかった時間）

解決にかかった時間は、2. と同じ理由で LLM の時間としては記録しない。人が書き直すときに、同じ点で迷ったかと時間を右の列に書く。

| # | 欄 | 迷った内容 | どう決めたか | 人が書き直したとき（筆者が記入） |
| --- | --- | --- | --- | --- |
| 1 | Lite／Full の判定 | #4 の 5 問では「マルチテナント」が Yes なので Full になる。#16 は「設計書 1 枚（Lite）」 | Lite の欄で書き、判定とずれることを設計書の冒頭に書いた | |
| 2 | 既定どおりの行の全列 | Keycloak が出すだけで誰も読まない `auth_time`・`typ`・`sid`・`scope` に、上限・個人情報・持ち主など 21 列を書くことになった | 全部書いた。必須を減らす案を `v0-columns.md` の 2. に書いた | |
| 3 | `consumers` | 読む受け手がいないとき、空の配列が R1 で error になった | 「キーを書けば `[]` でよい」に R1 を直した（v0 の規則の見直し。`RULES.md`） | |
| 4 | `usage` | `exp`・`jti` などが identifier／authz／display のどれでもない | 値 `protocol` を足した | |
| 5 | `on_missing` | `roles` は無ければ「ロールなし」で、拒否ではない | 値 `既定値` を足した。欠落の意味の列が要る | |
| 6 | `catalog_ref` | ケーススタディは出典ごとに行が分かれ、AT と ID トークンで別の ID になる | 配列 `catalog_refs` にした | |
| 7 | 利用イベントの段階 | #2 の「段階（①〜⑥）」は、クレームが生まれる場所で、利用イベントに当てはまらない | 利用イベントは `phase`（伝搬・検証・認可・運用）にした | |
| 8 | `hook_invoked` | Keycloak の「フック」は何か（プロトコルマッパー）。確かめていないイベントをどう書くか | マッパーを「フック」とし、確かめていないものは `unknown` にした（#2 の値は yes／no／条件つき） | |
| 9 | R8 のヘッダー | 計算が 5 文字合わなかった | 見本で原因（空白）を見つけ、`serializer_extra_bytes` を足した | |
| 10 | 経路の上限 | ヘッダー 1 つの上限と、全ヘッダーの合計の上限を同じに比べられない。Authorization の名前を数えるか | 2 種類に分け、名前は数える（保守側。筆者の提案） | |
| 11 | 配列の照合 | `max_bytes × max_items` では長さのばらつく配列の実物と合わない | 照合では平均を宣言にし、値そのものでも数えた | |
| 12 | 構成 | ケーススタディの判定は「入口で内部トークンに交換」を前提にしているが、実験（`cs/scen_a.py`）は API が Keycloak の AT を直接受ける | 実験の構成に合わせ、`casestudy-deviations.yaml` の `scenario_premises` に書いた | |
| 13 | ID トークン | 見本で ID トークンを発行していない（クライアントのスコープを basic だけにしたので、name・email のマッパーも足していない） | 設計として書き、`design.md` の 12. に「確かめていない」と書いた | |
| 14 | RT | Keycloak の古い RT を再利用したときの挙動 | 確かめず、「再利用の検知」とは書かなかった | |
| 15 | `pii_category` | `sub`（UUID）が個人情報か | 他の情報と容易に照合できるので個人情報とした（筆者の判断） | |
| 16 | `volatility` | 値が変わらないクレームを 0 と書くか | 0 は「変わらない」と定義した（スキーマの description） | |

## 4. claim_lint が書いている間に出したもの

レビューとは別に、記入の途中で claim_lint が出した指摘です（5. のレビューの指摘と比べるための材料）。

| 指摘 | 規則 | 中身の誤りか | 対応 |
| --- | --- | --- | --- |
| `verified_on` が日付の型になる | SCHEMA | 道具の誤り（PyYAML が日付を date にする） | 読み込みで日付を文字列のままにした |
| `serializer_extra_basis` の YAML の誤り | LOAD | 記入の誤り（引用符が要る） | 直した |
| `consumers` が空（4 行） | R1 | 規則の誤り（答えが「いない」の行を error にした） | R1 を直した（3. の #3） |
| U10 の `breaks_when` が「I06 と同じ」で 10 字未満 | R2 | 記入の不足（崩れる条件を書いていない） | 書き直した |
| ヘッダーの 5 文字の差 | R8（見本との照合） | 計算の前提の誤り | `serializer_extra_bytes` を足した |
| `iss`・`sub`・`aud`・`azp` が AT と ID トークンの両方に載る | R8（info） | 指摘どおりの事実。設計上は意図したもの | そのまま（info） |

## 5. レビュー（別のセッションで行う。作成者は書かない）

`templates/CONTRIBUTING.md` の 3. による。**この節は、作成に使ったものとは別の LLM のセッション（または人）が埋める。作成者（この文書を書いたセッション）は自己レビューをしていない。**

- 日付・使ったモデル：
- 渡した資料（パスとコミット）：`templates/examples/scenario-a/` の 4 ファイル、`templates/catalog/` の 2 ファイル、`templates/registry/` の 2 つのスキーマ、#16・#4・#3 の本文、ケーススタディ `jwt-claims-casestudy@080b8da` の `cs/scen_a.py`・`kc/import/t1.json`・`catalog/DECISION_POLICY.md`、Keycloak Server Administration Guide（26.8.2）「Using lightweight access token」
- 渡さないもの：この文書、`v0-columns.md`、`casestudy-deviations.yaml` の理由、作成者の結論（追認になるのを防ぐため）
- 渡した指示の全文：
- 指摘の一覧（対象・区分（誤り・過大・不一致・曖昧）・指摘・直し方）：

| # | 対象 | 区分 | 指摘 | claim_lint が拾ったか（拾った／拾えなかった） |
| --- | --- | --- | --- | --- |
| | | | | |

- 件数：指摘 __ 件。うち claim_lint が拾った __ 件、拾えなかった __ 件。claim_lint だけが拾い、レビューが拾わなかったもの（4. と比べる） __ 件
- 指摘ごとの反映（作成者が 1 日以上空けて記入）：

## 6. 台帳の列の過不足と、ケーススタディとの食い違い

- 列の過不足：`research/template-design/v0-columns.md`（足りなかった 14 項目、不要だった 7 列、ほぼ使わなかった 3 項目）。#3 に渡す
- ケーススタディとの食い違い：比べた参照 32 件、載せる／載せないの食い違い 7 件、条件の違い 1 件。すべて `templates/casestudy-deviations.yaml` に理由とともに載せた。数え方は同ファイルの冒頭

実行の記録（手作業の照合のための一時的なスクリプト。リポジトリには入れていない。照合の CI は #3）：

```
refs compared: 32; carry/no-carry divergences: 7; same side but condition differs: 1
DIVERGE   C-auth-time CLM-0228・CLM-0229（不採用・不要 / 既定どおり）
DIVERGE   C-typ-claim CLM-0198、C-sid CLM-0243（不採用・不要 / 既定どおり）
DIVERGE   C-client-id CLM-0405（採用 / 却下）
DIVERGE   C-idp ORG-06（条件付き採用 / 却下）
DIVERGE   C-realm-access CLM-0291（条件付き採用 / 却下）
CONDITION C-azp CLM-0410（条件付き採用「入口の正規化でのみ読む」 / 既定どおり）
```

## 7. tier（core／full）の見直しの案

対応表（`templates/trace/requirements.yaml`）の `tier` は暫定です。関門 1 で確定するため、シナリオ A の記入で分かったことから、変える候補を挙げます。**この PR では tier を変えていない**（判定は筆者）。シナリオ A だけからは、B・C に固有の要件を下げる根拠は得られないので、下げる候補は挙げていない。

| 要件 | 今 | 案 | 理由（シナリオ A で分かったこと） |
| --- | --- | --- | --- |
| `p03-keycloak-mappers.R1`（マッパーと Default／Optional のスコープの割り当てを設計書に書く） | full | core | AT に何が載るかは、スコープの割り当て（basic が auth_time を連れてくる、profile が preferred_username を連れてくる）で決まった。書かないと、台帳の「既定どおり」の行の理由が書けない |
| `p03-keycloak-mappers.R3`（Full scope allowed をオフにして、必要なロールだけを載せる） | full | core | 記入例の `roles` の値域（最大 2 件）と R8 の上限は、この設定に依存した。ケーススタディの実測（keycloak.full_scope）でも、オンでは既定のロールと tenant-admin が出る |
| `p04-absent-null-false-empty.R2`（許可を与えるクレームは、無いときに何も許さない） | full | core | `roles` の `on_missing` を決めるのに要った（3. の #5）。シナリオ A の最小の設計で出てくる |
| `p07-trust-boundary.R2`（セッション変数による分離に、全 SQL のテナントの条件を併用する） | full | core | シナリオ A の重点（data_tenant_check・rls_local）そのもの。記入例の `enforced_at` と U02 で、併用を前提に書いた（ケーススタディ A7） |
| `p08-rotation.R3`（無効にした RT の提示で系列を失効させることを試験で確かめる） | full | core | 記入例で RT の方式を「ローテーション」までしか書けず、再利用の検知を確かめられなかった（3. の #14）。確かめる手段がないと、発行方式の選択が書けない |
| `p11-registry-fields.R13`（12 の項目を必須列にし、欠ければ検出する） | core | core のまま | この PR で実装済みにした。R1 で欠落を検出できた |

## 8. 関門 1 の 3 つの選択肢とデータ

基準は #16 の本文（筆者の提案）。判定はしない。

| 選択肢 | 基準（#16） | いまあるデータ | まだ無いデータ |
| --- | --- | --- | --- |
| 続ける | R8 の照合が一致し、Lite の記入が 4 時間以内で、claim-lint が少なくとも 1 件、人や LLM のレビューと異なる指摘を拾った | R8 の照合は 0 バイトで一致（1.）。claim_lint は記入の途中で、記入の不足（U10）と計算の前提の誤り（ヘッダーの空白）を拾った（4.） | Lite の人の記入時間（2.）。レビューの指摘との比較（5.） |
| 絞る | 記入が 4 時間を超えた場合は、Lite の項目を減らしてからフェーズ 2 へ | 迷った点 16 件（3.）。既定どおりの行の 21 列が重い（`v0-columns.md` の 2.） | 人の記入時間 |
| 方針を変える | claim-lint に、レビューを超える上乗せが見られない場合は、構想を「カタログとサイズの検査だけ」に縮める | R8 の見本との照合は、静的な計算だけでは見つからない差（5 文字）を見つけた。R1・R2 の指摘は、書き手が自分でも気づける種類だった | レビューの指摘の数と、claim_lint との重なり（5.） |
