# claim_lint render（台帳から設計書の表を生成する）

台帳（`claims.yaml`・`token_types.yaml`・`hops.yaml`・`catalog_answers.yaml`）から、設計書に貼る表と、ビューアー（#36）が読む JSON と、トークン種別ごとのペイロードの JSON Schema を生成します（#19）。YAML と Markdown を手で二重に書くと、最初の版でずれるためです。規則（lint）は `RULES.md`、生成はこの文書です。コードは `tools/claim_lint/render.py` です。

```
python tools/claim_lint render templates/examples/scenario-a                       # 全部の節を Markdown で
python tools/claim_lint render templates/examples/scenario-a --section token-inventory
python tools/claim_lint render templates/examples/scenario-a --format json --out bundle.json   # ビューアー向け（#36）
python tools/claim_lint render templates/examples/scenario-a --write               # design.md の区間と schemas/*.json を書き直す
python tools/claim_lint render templates/examples/scenario-a --check               # 食い違えば終了コード 1（CI）
python tools/claim_lint render templates/examples/scenario-a --validate tools/tests/fixtures/claim_lint/golden/token.json --token-type AT
```

`python -m tools.claim_lint render …` でも同じです。

- 1. 生成する節
- 2. 設計書の区間（`--write`・`--check`）
- 3. JSON の束（ビューアー向け）
- 4. ペイロードの JSON Schema
- 5. 発行方式から導かれる要件の判定
- 6. 範囲外と、まだ確かめていないこと

## 1. 生成する節

節の ID は `--section` と、設計書の区間の名前に使います。どの節も、まず行のデータ（列と行）を作り、Markdown と JSON はその 2 つの見え方です。そのため、設計書の表とビューアーの表は食い違いません。

| 節の ID | 表 | 元の列 | 設計書（00_core、#4）の節 |
| --- | --- | --- | --- |
| `ci-result` | CI の結果：claim_lint の件数と、全部の指摘（規則・重大度・対象・内容）、R8 の計算 | claim_lint の JSON（`--lint-json` で渡すか、render がその場で実行する。`--also-scan design.md` つき） | 1. CI の結果 |
| `issuance-profile` | 発行方式の選択（項目・選択・理由・根拠）と、選択から導かれる要件（`templates/registry/issuance_effects.yaml`）と、それを満たしている台帳の行 | `issuance_profile` | 発行方式の選択（既定から外れた点の理由は手で書く節に書く） |
| `token-inventory` <a id="token-inventory"></a> | トークン目録：ID・種類・採否・発行 → 宛先（`aud`）・持ち手（`holder`）・形式（typ・alg）・寿命（idle と最大）・保存場所・運び方・読める相手（`visible_to`）・JWE・理由 | `token_types`。種類の名前は `templates/catalog/token_kinds.yaml` | トークン目録 |
| `question-mechanism` <a id="question-mechanism"></a> | 問い × 仕組み：問いの一覧の仕組み、答える台帳の行（`answers`）、答えに使わない行（`does_not_answer`）、照合する場所 | `templates/registry/questions.yaml`、台帳 | 問い × 仕組み（縮小 Lite では手で書く節。生成の表は確かめ用） |
| `hop-table` | ホップごとの表：種類・運ぶトークン・aud・scope・寿命・独自クレーム・交換するサービス・検証 | `hops.yaml` | ホップごとの表 |
| `arrow-table` <a id="arrow-table"></a> | 矢印ごとの表：ホップ × 載るトークン × 受け手が確かめるクレーム × 書き手 × 確かめること × aud × 寿命。トークンのないホップ（DB の接続など）では、値を書くのは送り手（`from`）なので、書き手の列には送り手と、台帳の `integrity_until`（書き先と、署名の保護が外れる境界）を出す（トークンの書き手は出さない） | `hops.yaml`、台帳の `carried_in`・`enforced_at`・`authoritative_writer` | シーケンス図の矢印の読み物 |
| `lifecycle` | 寿命の 4 つの層（slide:p08-four-lifetimes）：トークンの寿命、クレームの値の鮮度（`volatility` は反映までに許す秒数で、0 は即時の反映が要る。`never` はトークンの寿命の間に値が変わらないので比べない。載るトークンの受け入れの最大がこれを超える行に「超える」と出し、遅れが許容以内の目録の失効の手段を候補として並べる。手段がそのクレームに効くかは `on_revoke` で人が確かめる。検査の正は L5（#6））、セッションと RT、クレームの定義の寿命 | `token_types`・`hops.yaml`・台帳（`templates/registry/README.md` の 6.） | ライフサイクル表（縮小 Lite では手で書く節。生成の表は確かめ用） |
| `decision-rows` <a id="decision-rows"></a> | 判断の行：ID・候補・採否（却下の種類）・代わりの行（`alt`）・理由・前提・根拠 ID・裏付け・見直しの条件 | 台帳の `decision`・`rejection_kind`・`rationale`・`assumption`・`refs`・`evidence`・`revisit_trigger` | 判断の行 |
| `data-sources` <a id="data-sources"></a> | データ源：載せる行の `source_system`・書き手（段階と、設定できる主体）・発行の契機・再計算・値が変わりうる間隔・反映の遅れ | 台帳 | 判断の行に添える |
| `catalog-summary` | カタログへの回答の集計：全件・発行と利用・該当・**対象外の件数と割合**、該当の行、対象外の行（起きない前提と、前提が崩れる条件） | `catalog_answers.yaml`、`templates/catalog/` | カタログへの回答 |

根拠は、`guide-slide` を `slide:<id>`、URL のある根拠をリンク、`author-proposal` を「筆者の提案：…（追跡 issue）」と表示します。表の中の `|` と改行は、Markdown の表が崩れないように書き換えます。

## 2. 設計書の区間（`--write`・`--check`）

設計書（既定は `<設計書のディレクトリ>/design.md`、`--doc` で変えられる）の中で、次の 2 行に挟まれた部分が生成の区間です。

```
<!-- render:token-inventory:begin -->
（ここは render が書く）
<!-- render:token-inventory:end -->
```

- `--write` は、区間の中だけを生成し直し、`schemas/*.json`（4.）を書きます。区間の外（手で書いた文）には触れません。改行（CRLF・LF）はファイルのものを保ちます
- `--check` は、区間と `schemas/*.json` が、台帳から生成し直したものと一致しなければ、差分を出して終了コード 1 にします。台帳が生成しなくなった Schema（トークン種別を却下にした・消した・JWT でなくした）が `schemas/` に残っていても失敗し、`--write` はそれを消します。CI（`.github/workflows/claims.yml`）で実行します
- 知らない節の ID、同じ節の区間の 2 つ目、閉じていない区間は error です
- 区間の中を手で直すと `--check` が失敗します。台帳を直してから `--write` します

`ci-result` の区間は claim_lint の結果なので、規則を足した・変えた PR では、その PR の中で `--write` し直す必要があります（`--check` が失敗して知らせます）。

## 3. JSON の束（ビューアー向け）

`--format json` の出力（`format: claim-lint-render/1`）は、ビューアー（#36）が読むための正規化したデータです。時刻などの実行のたびに変わる値は入れないので、同じ台帳からは同じ JSON ができます（CI で生成物と YAML の食い違いを検出するのに使える）。

| キー | 中身 |
| --- | --- |
| `design` | 設計書のディレクトリ（リポジトリの根からの相対） |
| `sources` | 入力のファイルの sha256（改行を LF にそろえて計算）。設計書の 4 ファイル、`templates/registry/` の `questions.yaml`・`issuance_effects.yaml`、`templates/catalog/` の `token_kinds.yaml`・`issue_events.yaml`・`use_events.yaml`。ビューアーが古い束を見分けるため |
| `section_ids`・`sections` | 1. の節。節ごとに `id`・`title`・`notes`（表の前の文）・`tables`（`id`・`title`・`columns`（`key`・`label`・`fmt`）・`rows`）・`after`（表の後の文）。`rows` の値は文字列に整形する前の値（配列・根拠のオブジェクト・数値）で、`fmt`（`text`・`code`・`codes`・`list`・`refs`・`seconds`・`raw`）が表示の仕方を示す。`catalog-summary` と `ci-result` には `counts`、`issuance-profile` には全部の行の判定（`effects`）がある |
| `payload_schemas` | 4. の Schema（トークン種別ごとに `consumer` と `issuer`） |
| `registry` | 台帳の YAML をそのまま（`claims`・`token_types`・`hops`・`catalog_answers`）。詳細画面で全列を出すため |

## 4. ペイロードの JSON Schema <a id="payload-schema"></a>

slide:p11-schema-contract-tests の「台帳からトークン種別ごとのペイロードの JSON Schema を生成する」（req:p11-schema-contract-tests.R1）。採用・既定どおりの JWT のトークン種別ごとに、2 つの Schema（JSON Schema 2020-12）を `schemas/<ID>.consumer.schema.json`・`schemas/<ID>.issuer.schema.json` に生成します。

| | 受け手向け（`consumer`） | 発行側の適合の検査（`issuer`） |
| --- | --- | --- |
| 使い道 | 受け手が、知らないクレームで壊れずに、必須クレームの欠落を拒否する | 発行側（IdP の設定・マッパー・フック）が、台帳にないクレームを出していないかを確かめる |
| `additionalProperties` | `true`（名前空間のオブジェクトの中も） | `false`（名前空間のオブジェクトの中も） |
| `required` | トークン目録の `required_claims`（名前空間のクレームは `<名前空間>.<名前>` を、そのオブジェクトの `required` にする） | 同じ |
| 値の制約 | 型と形（`type`・`shape`）だけ | 型と形に加えて、文字列の `maxLength`（= `max_bytes`。文字数はバイト数以下なので必要条件）、配列の `maxItems`（`max_items`）、`allowed_values`（pattern・enum・format・min・max）、語彙が閉じている（`value_vocabulary.extensible: false`）なら `enum`。`aud` はトークン種別の `aud` の値だけを許す `enum`（PR #47 の独立点検。長さだけでは短い別の宛先が通った） |

- `$id` は `https://github.com/Takenori-Kusaka/jwt-claims-guide/payload-schemas/<設計書のディレクトリ名>/<ID>.<consumer|issuer>.schema.json/v<版>`、最上位の `$comment` は `template_version: <版>. …`（`templates/CONTRIBUTING.md` の版の管理）。版は設計書の `claims.yaml` の 1 行目の `template_version`。ディレクトリ名だけを使うのは、ディレクトリを写しても同じ Schema になるように（`--check` が比べるため）
- 受け手向けの `aud` は、台帳の形にかかわらず文字列と文字列の配列の両方を通す（RFC 7519 §4.1.3。発行側が宛先を増やしても受け手を壊さない）。発行側の Schema は台帳の形（シナリオ A は `shape: single` で文字列だけ）に従う
- 載るクレームは、台帳で採用・既定どおりで、`carried_in` にそのトークン種別があるもの。却下の行は載らないので、発行側の Schema では出たら失敗する
- 名前空間の `style: object` は入れ子のオブジェクト、`flat_prefix` は `<名前空間><名前>` の最上位のクレームにする
- `--validate` は、ペイロードの JSON、`payload_json` か `token` を持つ見本のファイル（`tools/tests/fixtures/claim_lint/golden/token.json`）、またはコンパクトな JWS を読み、Schema で検証します。**署名は検証しません**（形の検査だけ）

CI では、シナリオ A の Keycloak 26.8.0 で 2026-11-22 に実際に発行した AT（`golden/token.json`）を、発行側の Schema で検証します。台帳にないクレーム（最上位・名前空間の中）、却下したクレーム（`realm_access`）、語彙の外のロール、必須クレームの欠落、型の誤りを足した例で失敗することを `tools/tests/test_claim_lint_render.py` で確かめます。

## 5. 発行方式から導かれる要件の判定

`issuance-profile` の節は、`issuance_effects.yaml` の行のうち `when` が成り立つものについて、`requires` の `check` を簡易に読み取り、「満たす・満たさない・判定できない」と、満たしている台帳の行（例：`E-dpop.1` なら `cnf` の行）を表示します。

- 読み取る形：`claims[name=cnf].carried_in` のような行の選択（`=`・`!=`・`*`）と列、`issuance_profile.<項目>`、op の `present`・`absent`・`equals`・`includes`・`all_consumers`・`not_required`。`carried_in` の値 `kind:<種類>`・`transport:<運び方>` は、目録の行の種類・運び方に読み替える。`grant:` のように台帳の列で表せない値は「判定できない」。`[*]` の `includes` は全部の行が満たすときだけ「満たす」。`equals` の値がオブジェクトなら、書いたキーだけを比べる（行にほかのキーがあってもよい）。`all_consumers` は `enforced_at` の `check` を語に分けて完全に一致する語を探す（`path` は `ath` に当たらない）
- **これは表示のための読み取りで、検査の正は #6 の規則（L62〜L64）です。** 表の前に「次の表は検査ではない」と出し、列の名前も「簡易な読み取り（正は L62）」にしている。render は error を出しません

## 6. 範囲外と、まだ確かめていないこと

- 発行側の Schema の検証は、見本として保存した 1 つの AT に対してだけ行います。Keycloak の設定（レルムの JSON・マッパー）を変えたときに、CI でトークンを発行し直して検証する仕組みはありません（slide:p11-schema-contract-tests の「発行前のフック・設定の変更が Schema を満たすかを CI で確かめる」は未着手）。設定の書き出しと台帳の静的な比較は `claim_lint drift`（#30、`DRIFT.md`）で行い、2026-11-23 に Keycloak 26.8.0 で発行した AT・ID トークン・リフレッシュの AT（`tools/tests/fixtures/claim_lint/keycloak/`）も、CI で発行側の Schema で検証します（drift の `--token`）。ID トークンの Schema は、このときに初めて実物で確かめ、台帳に無かった jti・at_hash が見つかりました
- シナリオ B（#4 の Full の記入例）はまだないので、B の Keycloak のトークンでの検証は、B を作るときに足します
- 「下流は上流を超えない」の検査はホップの表には入れていません（#6 の L16）
- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施
