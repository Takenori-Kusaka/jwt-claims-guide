<!-- template_version: 0.1.0 -->
# ケーススタディとの対応表

ケーススタディ（https://github.com/Takenori-Kusaka/jwt-claims-casestudy）の成果物と、本計画の台帳（#3）・カタログ（#2）との対応です。どちらを正とするかを決め、二重管理にしないために作りました（#13 の 5.）。

- 対象のケーススタディ：コミット `080b8da`（2026-11-18）。一覧表と判定は 2026-11-17 時点のもの
- 台帳の列は #3 の本文（2026-11-22 時点）、カタログの項目は #2 の本文（同）によります。どちらもまだ作っていないので、列の名前は変わりえます
- 作成方法：本資料は生成AI（Claude）を使ってケーススタディのファイルを読んで作成し、筆者が確認して公開しています。人による点検は未実施です

## 用語

| ケーススタディでの呼び方 | この文書での呼び方 |
| --- | --- |
| ケース A・B・C | シナリオ A・B・C |
| ケース（A1・B9 などの個々の攻撃・正規の要求） | ケース |
| `catalog/`（クレームのカタログ、805 行） | 一覧表 |
| 判定（`decisions/`） | 判定 |

この文書で「カタログ」と書くときは、本計画の発行・利用イベントのカタログ（#2）だけを指します。

## 1. 正とする側（決定）

| 対象 | 正とする側 | もう一方での扱い |
| --- | --- | --- |
| 一覧表 805 行（名前・型・意味・出典・IdP での扱い・属性）。ORG 行の名前と型を含む | ケーススタディ `catalog/catalog.json`（参照するコミットを固定する） | `templates/` には写さない。`jwt-claims-casestudy@080b8da:CLM-0429` のように、コミットつきの ID で参照する |
| シナリオ A・B・C ごとの判定（805 行 × 3） | ケーススタディ `catalog/decisions/part*.json` と `catalog/scripts/header_rows.py` | 写さない。台帳の記入例の行から、判定を ID で参照する。記入例で違う判定にする行は、`templates/casestudy-deviations.yaml` に理由とともに載せる（ケーススタディは変えない） |
| 台帳の行の設計判断（理由・データ源・寿命と鮮度・伝搬・照合・サイズ・定義の寿命） | `templates/`（#3 の台帳と、シナリオ A・B の記入例） | ケーススタディには対応する列がほとんど無い（3.）。ケーススタディ側には作らない |
| 発行・利用イベントのカタログ | `templates/catalog/`（#2） | ケーススタディには無い。実測の結果を、行の `evidence` として参照する |
| 実測の結果（攻撃・正規の要求 67 ケース、除去実験、Keycloak の挙動、寿命の試算、変更の実験） | ケーススタディ `results/` | 写さない。`jwt-claims-casestudy@080b8da:B9` の形で `evidence` に書く |

正の向きは 1 つです。一覧表と判定はケーススタディ、設計判断とカタログは `templates/` です。ケーススタディの一覧表の誤りを見つけたら、ケーススタディを PR で直し、参照するコミットを上げます。

理由は次の 2 つです。

- **二重管理を避ける**。一覧表には生成・統合・検証のスクリプト（`catalog/scripts/`）と、列と判定の点検の記録（`catalog/reviews/`）があります。`templates/` に写すと、直すたびに 2 か所を直すことになります。
- **作り方が違う**。一覧表は「定義した出典ごとに 1 行」で外部の文書から集めた事実で、台帳は「組織が載せると決めたクレームごとに 1 行」の設計判断です。行の単位が違うので、片方をもう片方の上位の版として扱えません。

ライセンスは理由にしません。ケーススタディ（CC BY 4.0）の著作者は筆者なので、筆者が `templates/` に入れた部分は CC0 1.0 で提供し直せます（`LICENSE-CONTENT.md`）。

## 2. シナリオ A・B・C

ケーススタディの `README.md`・`DECISION_POLICY.md`・`cs/scen_a.py`・`cs/scen_b.py`・`cs/scen_c.py`・`results/summary.md` によります。

| | A | B | C |
| --- | --- | --- | --- |
| 名前 | マルチテナント SaaS | 社内業務システム | AI エージェントの委任 |
| IdP | Keycloak 26.8.0（実物）のレルム t1・t2 | Keycloak 26.8.0（実物）のレルム corp と、Entra ID・Okta・Cognito・Auth0 の形の模擬 | 組織のトークン発行サービスの模擬（時刻を進めるため）。Keycloak 26.8 の標準トークン交換は別に実測 |
| ほかの部品 | Postgres 16 の行単位の制御（RLS）、SET LOCAL | 入口（ゲートウェイ）で内部トークンに交換、`x-user-*` ヘッダー | MCP 風のツールサーバー、請求書の API、承認の記録 |
| ケース数 | 14（攻撃 10・正規 4） | 23（攻撃 18・正規 5） | 15（攻撃 12・正規 3） |
| ケース ID | A1〜 | B1〜 | C1〜 |
| 重点の要素 | tenant_iss_bind・data_tenant_check・rls_local・per_tenant_keys | normalize_gw・header_strip・freshness・overage_resolve | act_chain・aud_exchange・approval_bind・short_task・depth_rule |
| 本計画での使い道 | 縦の一本（#16）、台帳の記入例（#3） | 台帳の記入例（#3）、パイロット（#9） | パイロット（#9） |

ほかに汎用のケースが 15 件（G0〜G14。攻撃 14・正規 1。主に Part 1 で、Part 0・4 のものを含む）あり、全部で 67 ケースです。ケーススタディの README は「汎用の攻撃（Part 1、15 件）」としていますが、G0 は正規のトークンです（ケーススタディ側で別に直します）。

「シナリオ A（Keycloak）」（#16）は A を指します。IdP が Keycloak だけで閉じているのは A です。B も Keycloak を使いますが、ほかの 4 つの IdP の模擬を含みます。C の本体は Keycloak を使いません。

## 3. `catalog/catalog.json` の列と台帳の列（#3）

`catalog.json` は 805 行の配列です。内訳は、標準など 290 行（`_src: g1_standards`）、IdP 171 行（`g2_idps`）、プラットフォームと属性の語彙 323 行（`g3_platforms`）の計 784 行（`CLM-0001`〜`CLM-0784`）、ケーススタディで定義した組織のクレーム 11 行（`ORG-01`〜`ORG-11`）、JOSE ヘッダー 10 行（`HDR-01`〜`HDR-10`）です。列の定義は `catalog/SCHEMA.md` にあります。

対応の区分：**同じ**＝そのまま移せる／**一部**＝値の粒度か範囲が違い、移すには判断が要る／**意味が違う**＝名前が似ているが別のもの（取り違えに注意）／**列なし**＝台帳に対応する列がない

| ケーススタディの列 | 台帳の列（#3） | 区分 | メモ |
| --- | --- | --- | --- |
| `id` | （なし） | 列なし | 台帳の行からの参照に使う。#3 に参照の列（例：`catalog_ref`）を足すかを決める（筆者の提案） |
| `name` | `name`・`namespace` | 一部 | ORG 行は、ORG-08 を除き、`https://claims.example.com/.tenant_id` のように名前空間と名前を `.` でつないでいる。ORG-08 は `authorization_details[type=https://claims.example.com/rar/payment]`。台帳では `namespace` と `name` に分ける |
| `category` | （なし） | 列なし | 18 の分類。台帳では使わない |
| `purpose` | `description`・`not_meaning` | 一部 | 「表すこと」と「表さないこと」が 1 つの文に入っている。台帳では 2 列に分けて書き直す（文章は写さない） |
| `source_kind`・`source`・`url` | `registered_ref`・`refs` | 一部 | 標準の行は `registered_ref` に当たる。`source_kind` の 9 つの値の、根拠の種類（#13 の 1.）での行き先は下の表 |
| `value_type` | `type` | 同じ | |
| `multiplicity` | `shape` | 一部 | 「単一・配列・単一または配列（揺れあり）」。揺れのあるものは、台帳では入口で正規化した後の形を書く |
| `token` | `carried_in` | 一部 | ケーススタディはトークンの種類だけ。台帳はトークン種別とホップの組 |
| `support`（5 社） | （なし。#2 の IdP モジュール） | 列なし | 主な値は「既定・設定で追加・独自の名前で・フック・式で可・不可・未対応・不明」。ほかに「既定（AT のみ）」のような条件つきの値がある。クレームごとの値で、イベントごとの `hook_invoked`（#2）とは別のもの |
| `support_note` | （なし） | 列なし | 60 行だけにある |
| `is_custom` | `registered_ref` の有無 | 一部 | |
| `notes` | （なし） | 列なし | |
| `checked_on` | （なし。#2 の `verified_on`） | 一部 | 出典の文書を開いた日。台帳の `last_verified`（データ源の値を確かめた日）とは別のもの |
| `verified` | （なし） | 列なし | 真偽値（出典を開いたか）。本計画では、確かめた日を `verified_on` に書くことで代える |
| `status` | `status` | 意味が違う | ケーススタディは**標準の状態**（最終・草案（版）・ベンダー提供中など）。台帳は**組織のクレームの定義の寿命**（proposed・active・deprecated・sunset）。草案の版は `spec_version` に当たる |
| `change_controller` | `change_controller` | 同じ（標準の行） | 組織のクレームでは、台帳の `owner`・`change_controller` を新たに決める |
| `writer` | `authoritative_writer`・`modifiers` | 一部 | ケーススタディは「発行者（権威ある情報源）・本人が編集できる」などの区分。台帳は段階ごとの具体的な書き手 |
| `mutability` | `volatility` | 一部 | ケーススタディは区分（670 行が「不明」）。台帳は秒数 |
| `freshness` | `recompute_trigger` | 一部 | 「発行時点で固定・発行ごとに再計算・都度照会が必要」。台帳は契機（ログイン時だけ・リフレッシュ時も・交換時も） |
| `authz_use` | `usage` | 一部 | 出典の指針で、採否ではない。台帳の `usage`（identifier・authz・display）は組織の判断 |
| `pii` | `pii_category` | 一部 | 語彙が違う。ケーススタディは「非該当・仮名の識別子・直接識別できる個人情報・機微な個人情報」、台帳は個人情報保護法の区分（個人情報・要配慮個人情報・個人関連情報・仮名加工情報・該当なし）。機械的に写せない |
| `log_policy` | `log_policy` | 一部 | 805 行のうち 781 行が「記載なし」。ケーススタディの「平文で可」は出典が記録を許すという意味で、台帳の「記録する」（組織の決定）とは向きが違う。「ハッシュ・マスク」のマスクは、台帳の値にない |
| `limit` | `max_bytes`・`max_items`・`overflow_strategy` | 一部 | 自由な文（例：200 件超で欠落）。台帳では数値と方針に分ける |
| `comparison`・`uniqueness`・`vocabulary` | （なし） | 列なし | 照合の規則に要る。#3 に足すかを決める（筆者の提案） |
| `synonym_group` | （なし） | 列なし | 204 のグループ。独自クレームが既存のクレームと重なっていないかの確認に使える（#6 の規則の入力） |
| `_src` | （なし） | 列なし | 生成の作業用 |

### `source_kind` の値と根拠の種類

| `source_kind` | 根拠の種類 |
| --- | --- |
| 標準（IETF RFC） | `spec` |
| 標準（OpenID Foundation 最終版） | `spec` |
| 草案（IETF・OIDF） | `spec`（版番号つき） |
| IANA 登録（その他の標準化団体） | `spec` |
| 公的機関・研究 | 公的機関の指針は `guidance`、研究は `research`。行ごとに分ける |
| ベンダー独自 | `spec`（製品の公式文書） |
| プラットフォーム独自 | `spec`（製品の公式文書） |
| 業界の属性語彙 | `spec` |
| 本ケーススタディで定義 | 根拠ではない。台帳の行そのもの（設計判断）で、理由の根拠は行ごとに別に書く |

### 台帳にあってケーススタディに無い列

`answers`・`does_not_answer`、`issuers`・`upstream_issuer`・`issue_events`・`stage`、`source_system`・`verification_method`・`last_verified`、`propagation_delay`・`on_revoke`、`consumers`・`on_missing`、`enforced_at`、`typical_items`、`recipients_external`・`cross_border`、`sunset_on`・`owner`、`asvs_ids`。これらは台帳の記入例で新しく書きます。

## 4. `catalog/decisions/` と台帳の判断の列

`decisions/part1.json`〜`part4.json` と `part5_org11.json` は、CLM 784 行と ORG 11 行（計 795 行）の判定です。HDR 10 行の判定は `catalog/scripts/header_rows.py` にあります。1 行は `{id, guide_part, A, B, C}` で、A・B・C のそれぞれに次の項目があります。判定の書き方は `catalog/DECISION_BRIEF.md` と `DECISION_POLICY.md` にあります。

| ケーススタディの項目 | 台帳の列（#3） | 区分 | メモ |
| --- | --- | --- | --- |
| `judgement` | `decision` | 一部 | 下の表 |
| `condition` | `assumption`・`carried_in` | 一部 | 「ID トークンのみ」は `carried_in`、「入口の正規化でのみ読む」は `stage`、それ以外の前提は `assumption` |
| `alt` | （なし） | 列なし | 代替のクレームの ID。却下の理由の裏付けになる。#3 に足すかを決める（筆者の提案） |
| `use_or_loss` | `rationale` | 一部 | 採用は「どう使うか」、不採用は「何ができなくなるか」。台帳でも同じ観点で書く（文章は写さない） |
| `revisit` | `revisit_trigger` | 同じ | |
| `checks` | `evidence` | 同じ | ケース ID（例：`A3`）。`jwt-claims-casestudy@080b8da:A3` の形にする |
| `checks_note` | `evidence` | 一部 | 自由な文（例：「—（対象外のため検証なし）」）。ケース ID ではないので写さない |
| `related` | （なし） | 列なし | |
| `guide_part` | `refs`（`guide-slide`） | 一部 | Part の単位。台帳ではスライドの固定 ID（#15）まで細かくする |

### 判定の値の対応

| ケーススタディの判定 | 台帳の `decision` | 件数（A・B・C） |
| --- | --- | --- |
| 必須（共通基準） | 採用。トークン種別の `required_claims` にも入れる | 14・14・14 |
| 採用 | 採用 | 6・7・16 |
| 条件付き採用 | 採用（条件は `assumption`・`carried_in`・`stage`） | 34・88・22 |
| 不採用・代替あり | 却下（代替は `rationale` と参照） | 112・80・116 |
| 不採用・不要 | 却下 | 282・257・249 |
| 不採用・禁止 | 却下（載せると害がある理由を `rationale` に） | 44・46・76 |
| 対象外 | 台帳に行を作らない。対象外はケーススタディの判定のまま参照する | 303・303・302 |

件数は CLM と ORG の 795 行の数で、HDR の 10 行は含みません。

台帳の `decision` は 3 値（採用・却下・既定どおり）なので、「代替あり・不要・禁止」の区別が落ちます。区別は lint（#6）の規則に要る場合があります（例：「禁止」のクレームがトークンに載っていたら error）。#3 で、`decision` を細かくするか、別の列で持つかを決めます。「既定どおり」に当たる判定はケーススタディにありません。

## 5. `DECISION_POLICY.md` と台帳・宣言

| `DECISION_POLICY.md` の節 | 本計画で受けるもの | メモ |
| --- | --- | --- |
| 共通の前提（外部の IdP のトークンは入口でだけ検証し、内部トークンに交換） | `hops`（入口のホップ）、`issuers`・`upstream_issuer`（#3） | 3 つのシナリオに共通する構成。記入例の経路の前提になる |
| 共通の基準（`iss`・`sub`・`aud`・`exp`・`iat`・`jti`・`typ`、名前空間の `tenant_id`・`user_id`） | `token_types` の `required_claims`・`typ`・`alg_allowlist` | |
| 組織の独自クレーム（ORG-01〜ORG-11） | 台帳の行（シナリオ A・B の記入例） | 名前と型はケーススタディが正。台帳は設計判断の列を持つ（7.） |
| ケースごとの重点 | 設計書の本文、`hops`、`enforced_at` | 重点の要素名（`tenant_iss_bind` など）は、ケーススタディの実験の要素 |
| 判定の値 | `decision` | 4. の表 |

`SCHEMA.md` は一覧表の行の形式で、台帳の README（#3）の「各列の意味と根拠」と同じ役割です。台帳の README には、列ごとにこの文書の 3. の対応を載せます。

## 6. 発行・利用イベントのカタログ（#2）との対応

ケーススタディには、発行・利用イベントの一覧はありません。カタログの行の根拠に使えるものは次のとおりです。場所は `results/measurements.json` の中の JSON の経路です。

| ケーススタディ | カタログの項目（#2） | 使い方 |
| --- | --- | --- |
| `keycloak.refresh_reevaluation` | リフレッシュのイベントの「寿命への影響」（Keycloak） | リフレッシュで属性（`department`）とロールが再評価され、RT はローテーションされた（`refresh_token_rotated: true`）実測 |
| `keycloak.logout_introspection` | ログアウトのイベント、主体の状態の行列 | ログアウト後の初回のイントロスペクションで `active=false`（20 回とも）。JWT は残りの寿命（最小 299 秒）の間は残る |
| `C.keycloak_exchange` | トークン交換のイベント | 交換で宛先を付け替えられた、`act` が付かない、の実測 |
| 一覧表の `token` の列 | 「生まれるクレーム」 | どのトークン種別に載るか。イベントとの対応は無いので、カタログ側で付ける |
| 一覧表の `support`（5 社）の「フック・式で可」 | `hook_invoked` | 参考にとどめる。フックが使えるかと、そのイベントでフックが呼ばれるかは別 |
| 攻撃・正規のケース（G・A・B・C） | 利用イベント、実行での照合（#8） | ケースは「ある利用イベントで、ある検証が効くか」の試験。利用イベントの行の `evidence` に書く |

カタログの正は `templates/catalog/` です。

## 7. 二重管理の危険と対策

| 危険 | 起きること | 対策 |
| --- | --- | --- |
| ORG-01〜ORG-11 の名前と型が 2 か所にできる | 台帳の記入例とケーススタディの一覧表が食い違う | 名前と型の正はケーススタディ（固定したコミット）。台帳の記入例は ORG の行を ID で参照し、名前と型は CI で `catalog.json` と照合して、食い違えば失敗させる。名前や型を変えたいときは、ケーススタディを PR で直し、参照するコミットを上げてから記入例を直す |
| シナリオ A・B の判定が 2 か所にできる | 台帳の記入例の採否と、ケーススタディの判定が食い違う | 判定の正はケーススタディ。記入例の採否は CI でケーススタディの判定と照合する。意図して変える行は `templates/casestudy-deviations.yaml` に ID・シナリオ・理由を載せ、載っていない食い違いは失敗させる。ケーススタディの判定は変えない |
| ケーススタディが更新され、参照先がずれる | ID の指す中身が変わる、行が増える | 参照にはコミットを付ける。参照するコミットを上げるときは、差分を見て記入例と `casestudy-deviations.yaml` を見直し、`templates/CHANGELOG.md` に書く |
| 文章を写してしまう | 一覧表の文章が `templates/` に入り、直す場所が 2 か所になる | 文章は写さず、台帳では書き直す。事実（名前・型・値）と ID だけを参照する |
| 似た名前の列を同じものとして写す | `status`・`checked_on`・`pii` が別の意味のまま混ざる | 3. の「意味が違う」「一部」の行は、機械的に写さない |

上の照合の CI と `casestudy-deviations.yaml` は、まだありません。8. で #3 に渡します。それまでは、二重管理の対策は未実施です。

## 8. 後続の issue に渡すこと

この PR のマージ後に、各 issue にコメントで渡します。各 issue を閉じるときは、下の項目ごとに、実装したか、実装しない理由を書きます（完了の定義の「指摘ごとに反映したか、反映しない理由」と同じ扱い）。

### #3（台帳 v1）
- [ ] ORG 行の名前と型を、固定したコミットの `catalog.json` と照合する CI
- [ ] 記入例の採否を、ケーススタディの判定と照合する CI と、`templates/casestudy-deviations.yaml` の形式
- [ ] 一覧表の ID を参照する列（`catalog_ref`）を足すか
- [ ] `alt`（代替のクレーム）、`comparison`・`uniqueness`・`vocabulary`、`synonym_group` を足すか
- [ ] `decision` の値を細かくするか（「代替あり・不要・禁止」の区別）
- [ ] 台帳の README の列ごとの説明に、3. の対応を載せる
- [ ] ASVS を `asvs_ids` に書き、`refs` に書かない、をスキーマで確かめる

### #2（カタログ）
- [ ] `keycloak.refresh_reevaluation`・`keycloak.logout_introspection`・`C.keycloak_exchange` を、Keycloak のリフレッシュ・ログアウト・トークン交換の行の `evidence` にする
- [ ] 一覧表の `support` の「フック・式で可」を `hook_invoked` に写さない（6.）

### #16（縦の一本：シナリオ A）
- [ ] シナリオ A の記入例で、3. の「一部」の列を実際に移し、足りない列と不要だった列を記録して #3 に渡す
- [ ] 記入例の採否とケーススタディのシナリオ A の判定の食い違いを数える（照合の CI ができる前の手作業）
