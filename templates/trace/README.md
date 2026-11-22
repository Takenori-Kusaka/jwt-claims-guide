<!-- template_version: 0.1.0 -->
# スライドと成果物の対応表（#22）

ガイドの全スライドと、計画の成果物との対応表です。成果物とは、台帳の列・テンプレートの欄・lint の規則・観点書の問い・実行テストなどを指します。

**網羅の正は、issue の本文ではなく、この対応表です。** issue の本文に要件を並べる方式では、書いた人が思いついたことしか入りません。実際に、5 つの観点のレビューを経た後でも、スライド 81（`slide:p06-narrow-downstream`、下流ほど絞る）が計画から抜けていました（#11・#22）。

各 issue（#3・#4・#5・#6・#8・#17・#18・#19 など）の完了基準は、「この issue が担当する要件が、すべて実装済みになっている（`trace-check` で確かめる）」です。担当の要件は、下の「件数」の表と `python tools/trace_check.py` の出力で確かめます。

## 件数（2026-11-22 時点。#3 の台帳 v1 の後）

<!-- counts:begin -->
- スライド 159 枚：設計判断 135 枚、知識 7 枚、構造 17 枚。教材の行 10 件（知識のスライドは全件）
- 要件 749 件：未着手 636、実装済み 70、後回し 42、扱わない 1
- 段階（2026-11-22 に確定）：core 489 件（未着手 438・実装済み 51）、full 260 件（未着手 198・実装済み 19・後回し 42・扱わない 1）。確定の後の変更 6 件（`tier_changes`。#10 で足した要件を core にした）
- `review:` の成果物を持つ要件：core 167／489 件、full 72／260 件
- **扱わない 1 件／全 749 件（0.1%）**
- 成果物 513 件：issue の本文にあるもの 254 件、対応表で足した提案 259 件（`new_items.md`）

| 担当 | 要件 | core | full | 未着手 | 後回し | 扱わない | 提案した成果物 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| #2 | 12 | 5 | 7 | 11（実装済み 1） | 0 | 0 | 0 |
| #3 | 152 | 118 | 34 | 85（実装済み 67） | 0 | 0 | 32 |
| #4 | 199 | 154 | 45 | 199 | 0 | 0 | 69 |
| #5 | 120 | 75 | 45 | 120 | 0 | 0 | 86 |
| #6 | 147 | 77 | 70 | 147 | 0 | 0 | 36 |
| #8 | 50 | 37 | 13 | 50 | 0 | 0 | 32 |
| #13 | 2 | 2 | 0 | 2 | 0 | 0 | 0 |
| #16 | 2 | 2 | 0 | 1（実装済み 1） | 0 | 0 | 0 |
| #17 | 2 | 2 | 0 | 1（実装済み 1） | 0 | 0 | 0 |
| #18 | 17 | 14 | 3 | 17 | 0 | 0 | 3 |
| #19 | 3 | 3 | 0 | 3 | 0 | 0 | 0 |
| #21 | 42 | 0 | 42 | 0 | 42 | 0 | 1 |
| #22 | 1 | 0 | 1 | 0 | 0 | 1 | 0 |
<!-- counts:end -->

## ファイル

| ファイル | 中身 |
| --- | --- |
| `requirements.yaml` | 次の 4 つの部分からなる。`summary`（件数。`trace_check.py` が実際の件数と照合する）。`classification`（152 枚すべての分類と、本文のハッシュ）。`requirements`（設計判断のスライドの要件）。`teaching`（教材に使うスライド） |
| `review_required.yaml` | レビューで必ず扱うスライドの固定の一覧（10 枚、理由つき）。`classification` の `review_required: true` と一致しなければ検査が失敗する（#16） |
| `planned_items.yaml` | 要件から参照できる成果物の一覧。`origin: issue` は担当の issue の本文にあるもの、`origin: proposed` は対応表を作るときに足した提案 |
| `new_items.md` | `origin: proposed` の一覧を issue ごとにまとめたもの。生成物で、`python tools/trace_check.py --write-new-items` で作る。各 issue の本文に書き足すかどうかは、担当の issue で決める |
| `../../tools/trace_check.py` | 対応表の検査。CI は `.github/workflows/trace.yml` |

`origin: issue` が本当に issue の本文にあるかは、機械では確かめていません。点検のときに抜き取りで確かめます。YAML で同じキーを 2 回書くと、検査は失敗します。PyYAML の既定のように後勝ちにはしません。

## スライドの分類

| 分類 | 意味 | 対応表での扱い |
| --- | --- | --- |
| `design-decision` | 設計者・実装者・レビュアーが決める、守る、避けることを求めるスライド。チェックリスト・「リーダーの視点」・推奨・事例の教訓を含む | 1 件以上の要件に分解する。教材にも使うなら `teaching` にも載せる |
| `knowledge` | 背景・説明・比較・事実だけで、規則を 1 つも述べないスライド | `teaching` に 1 行ずつ載せ、どの教材に使うかを書く（全件） |
| `structural` | 表紙・Part の扉・目次・締め | なし |

分類の基準は「スライドが規則を述べているか」です。同じ規則が別のスライドの要件で覆われていても、規則を述べていれば `design-decision` にし、要件を置きます。

### 本文のハッシュ（スライドを直したら、要件を読み直す）

`classification` の各行には次の 2 つがあります。
- `sha`：`docs/slides.json` の title・text・notes の sha256 の先頭 12 桁
- `reviewed_on`：要件を読み直した日

スライドの本文かノートを変えると、ハッシュが合わなくなり、その行を直すまで CI が失敗します。要件を読み直して直したら、次のコマンドで行を更新します。

```
python tools/trace_check.py --update-hash <スライド ID> [...] --reviewed-on YYYY-MM-DD
```

この更新は PR の diff に出ます。

### 初回の突き合わせの表からの分類の変更

初回の表（#22 の「現状」。設計判断 118 枚）から、次の 10 枚を `knowledge` から `design-decision` に変えました。設計判断は 128 枚です。5・129・133 は、PR #27 の独立点検の指摘で変えました。

| 番号 | スライド | 理由 |
| --- | --- | --- |
| 5 | `slide:p00-incident-signature-valid` | 事例ごとの教訓が規則になっている（iss と鍵の組を確かめる、変更できる属性をキーにしない、名前と ID を対で出す） |
| 10 | `slide:p01-jwt-structure` | 「秘密にしたい情報は JWS に入れず、必要なら JWE」「ヘッダーを鵜呑みにしない」という規則がある |
| 41 | `slide:p03-recent-changes` | 「手順書や書籍の記述は、現行の公式文書で確かめ直してから使う」という規則がある |
| 60 | `slide:p04-namespace-object-example` | 構造の版 `v` と、フラットな別名を台帳に定義することを求めている |
| 66 | `slide:p05-pep-pdp` | PEP・PDP の分担と「トークンが有効かどうかだけで認可しない」を求めている |
| 87 | `slide:p06-flow-browser-to-db` | 見出しが規則になっている（ブラウザにトークンを置かない、ID トークンを API に送らない、DB に利用者の AT を渡さない） |
| 113 | `slide:p09-jws-is-readable` | 「載せる前に誰が読めるかを問う」「ペイロードを機微データとして分類する」を求めている |
| 129 | `slide:p10-vendor-features` | 「製品の独自クレームを組織の契約にしない。入口で標準のクレームにそろえる」という規則がある |
| 130 | `slide:p10-guidance-standards` | 根拠の書き方の規則がある（規則の根拠に何を使うか、草案を必須と書かない） |
| 133 | `slide:p11-why-govern` | 「トークンの中身の変更は破壊的変更として扱う」という規則がある |

### #10 で足したスライド（2026-11-22）

#10（ガイド本体の空白を埋める）で 7 枚を足し、7 枚とも `design-decision` にしました。規則を述べているためです。新しいスライドの要件は 28 件で、既存のスライドに足した 3 件（下）と合わせて 31 件です。そのうち 6 件を core にしました（`tier_changes`）。core にしたのは、#11 の完了状態 2 に当たる要件です（問い × 仕組みの表、寿命の 4 つの層、検証の設定）。

| スライド | 要件 | core |
| --- | --- | --- |
| `slide:p01-key-rotation-jwks` | 5 | R2・R3・R4（JWKS のキャッシュ、知らない kid、鍵の公開と廃止の順序） |
| `slide:p01-client-made-jwts` | 4 | — |
| `slide:p06-grant-types` | 4 | — |
| `slide:p08-four-lifetimes` | 2 | R1（独自クレームごとに 4 つの層を書く） |
| `slide:p08-reissue-triggers` | 5 | — |
| `slide:p08-logout` | 4 | — |
| `slide:p08-copies-outlive-token` | 4 | — |

既存のスライドで中身を変えたのは 4 枚です。`slide:p05-one-request-carries`（問いの表を分けた。R6・R7 を core で足し、R1 から `guide:split-slide-64` を外した）、`slide:p06-issuance-hook`（client credentials のフック。R8 を full で足した）、Part 1 と Part 8 の扉（ノートの目次）です。ほかの 137 枚は、スライド番号がずれただけで、本文・ノートは変わっていません（番号を除いて比べて確かめた）。ハッシュはスライド番号を含むので、この 137 枚も `--update-hash` で更新しました。`reviewed_on` は、要件の読み直しが要らなかったので、前の点検日（2026-11-22）のままです。

## 要件の書式

```yaml
- id: p06-narrow-downstream.R1        # <スライド ID>.R<連番>。連番はスライドの中の順
  slide: slide:p06-narrow-downstream  # #15 の参照の書式
  text: 交換・作り直しのたびに aud を上流より広げない
  owner_issue: "#6"                    # 担当の issue。planned_items のどれかの issue と一致させる
  planned_items:                       # 1 つ以上。planned_items.yaml にある ref だけ
    - template:00_core#hop-table
    - lint:L16
    - test:negative_tests#exchange-narrowing
  status: 未着手
  tier: core                           # core / full（下の「段階」）
  # 扱わない のときだけ（#13 の「対象外」の書き方に合わせる）
  assumption: 起きない前提
  breaks_when: その前提が崩れる条件
```

### 状態

| 状態 | 意味 | 検査 |
| --- | --- | --- |
| `未着手` | 担当の成果物がまだない | — |
| `実装済み` | 担当の成果物があり、その中から要件を逆に指している | 次の 3 つをすべて確かめる（下の「実装済みの確かめ方」） |
| `後回し` | MVP の外（#21。ほかに #7・#20） | `owner_issue` が #7・#20・#21 のどれかで、`tier: full`。逆に、これらの issue が担当の要件は `後回し` にする |
| `扱わない` | 成果物を作らない | 次の 4 つを確かめる（下の「扱わないの確かめ方」） |

#### 実装済みの確かめ方

`実装済み` に変えるのは、担当の issue の PR です。成果物を作り、その中に要件の ID を `req:<要件 ID>` の形で書いてから（例：`<!-- req:p06-narrow-downstream.R1 -->`）、状態を変えます。検査は次の 3 つを確かめます。

1. `planned_items` のすべてが、実在の成果物に解決する（下の「成果物の参照の書式」）
2. `template`・`review`・`test` の項目は、アンカーまで指している（ファイル全体を指したままでは実装済みにできない）
3. 解決した部分に、`req:<要件 ID>` がある。解決した部分とは、アンカーから次のアンカーまでの節、スキーマのそのプロパティ、`RULES.md` のその規則の行から次の規則まで、などを指す。Markdown ではコメント、JSON Schema では `$comment` や `description`、YAML ではそのノードの中に書く

ただし、ここで確かめるのは「成果物があり、そこから要件を指している」ことまでです。**中身が要件を満たしているかは、担当の PR のレビューで確かめます。** 検査は、それを保証しません。

解決の手段がまだない種類（`render`・`calib`・`guide`・`deferred`・`none`）は、実装済みにできません。

#### 扱わないの確かめ方

- `planned_items` が `[none:out-of-scope]` だけで、担当が #22、`tier: full`
- `assumption`（起きない前提）と `breaks_when`（崩れる条件）が、それぞれ 20 字以上
- どちらも `text` と同じでなく、互いに同じでもない
- 前提として妥当か（「強制できない」のような、作らない理由になっていないか）は、機械では確かめない。#13 の抜き取りの点検で確かめる

### 段階（tier）

すべての要件に、`tier: core` か `tier: full` を付けます。**この区分は、関門 1（#16、2026-11-22）で作成者が確定しました。** 記録は `requirements.yaml` の `tier_confirmed`（`confirmed_on`・`by`・`record`・`note`）と `research/template-design/gate1.md` です。`tier_confirmed` が無いとき、`trace_check.py` は「tiers: proposal」と表示します。#11 の完了状態 3（「未着手 0 件」）は、`tier: core` の未着手が 0 件、と読み替えます。関門 2 で「絞る」と判定したら、要件の tier を下げる PR で記録します。

関門 1 で、最初の割り当て（下の規則）から core に上げた要件は 38 件です。gate1.md の 7. の案は 5 件で、残りの 33 件は案に無かったものです（規則の拡張に結びつく 13 件、作成者の追加の指示による 14 件、PR #31 の点検による 6 件）。
- gate1.md の 7. の案の 5 件：`p03-keycloak-mappers.R1`・`R3`、`p04-absent-null-false-empty.R2`、`p07-trust-boundary.R2`、`p08-rotation.R3`
- シナリオ A のレビューの 17 件から導いた規則の拡張（L27・L31・L23 の idle と絶対的な上限）に結びつく要件 13 件：L27 の 2 件、L31 の 10 件、`p08-rotation.R4`
- 追加前の 25 問（スライド 142・143）の 7 件。問いの回答欄は core にし、深い lint（L24・L34・L60 など）は full のままでよい成果物として、要件の `note` に書いた。あわせて 27 件すべてに `review:perspectives#pre-add-questions`（#5）と `lint:L72`（#6、25 問の未回答）を足した
- アンチパターン（スライド 146・147）の 3 件（`p12-antipatterns-2.R6`〜`R8`。`p12-antipatterns-1.R7`・`R8` は L31・L27 で上げた）と、レビューの観点（スライド 148）の 4 件（`p12-review-viewpoints.R3`・`R8`・`R10`・`R17`。`R15` は L31 で上げた）。どちらも観点書の骨格になるため、全件を core にした
- 設計のチェックリスト（スライド 61）の 6 件（`p04-design-checklist.R3`〜`R8`）。追加前の 25 問の core の問い（問 4・5・7・9・10）と中身が重なるため（PR #31 の点検）

確定したときの core の集合は、`tier_confirmed` の `core_count`・`core_sha`（要件 ID を並べた sha256 の先頭 12 桁）に記録してあります（`python tools/trace_check.py --snapshot-tiers --confirmed-on YYYY-MM-DD --by <判定者>` で書く）。確定の後に tier を変えるときは、`tier_changes` に 1 件ずつ次を書きます。記録の無い変更は `trace_check.py` が失敗させます。

```yaml
tier_changes:
  - {id: p01-validate.R1, from: core, to: full, changed_on: "2026-12-01", reason: "関門 2（#9）で Full の欄に移したため、MVP の範囲から外す"}
```

- `changed_on` は `tier_confirmed` の `confirmed_on` 以降の日付。キーを `on` にしないのは、YAML 1.1（PyYAML）が `on`・`off`・`yes`・`no`・`y`・`n` のキーを真偽値として読むためです（`confirmed_on` も同じ理由）
- `from` は、その時点の tier（確定の後に初めて変えるなら確定時の tier）。`to` は変えた後の tier
- `reason` は 20 字以上で、同じ文字の繰り返しでなく、決めた issue・PR・関門（`#NN`・`PR`・`関門`）を書く
- tier を確定し直すときは、`--snapshot-tiers --reconfirm --confirmed-on <日付> --by <判定者>` を使います。日付は前の確定と全ての `tier_changes` の日付以降でなければ拒否します。前の確定の記録は `previous` に残り、`tier_changes` は空になります
- `core_sha` を手で書き換えることは機械では防げません。`core_count`・`core_sha` の差分は、確定のし直しとしてレビューで扱います

提案の lint（L24〜L61）だけに頼る要件は既定で full、という下の目安の例外として、L27・L31 に結びつく要件を core にしました。

### レビューで必ず扱うスライド（`review_required`）

チェックリスト・アンチパターン・レビューの観点・追加前の問いのスライドは、設計書の欄や lint だけでなく、観点書（#5）でも問います。対象のスライドは `templates/trace/review_required.yaml` に理由とともに固定し、`classification` の `review_required: true` がこの一覧と完全に一致しなければ失敗します（フラグを消すだけでは外せない）。`review_required: true` を付けたスライドでは、要件ごとに `review:` の成果物が 1 つ以上要り、無ければ `trace_check.py` が失敗します（#16 で追加）。対象は p04-design-checklist、p06-flow-checklist、p07-data-layer-checklist、p09-checklist、p10-agent-checklist、p11-pre-add-questions-1・2、p12-antipatterns-1・2、p12-review-viewpoints の 10 枚です。アンチパターンの 17 件には、行ごとに専用の問い（`review:perspectives#ap-1-<n>`・`#ap-2-<n>`）を付けました。`trace_check.py` は、`review:` の成果物を持つ要件の数を tier ごとに表示します。

| 段階 | 目安 |
| --- | --- |
| `core` | MVP の issue（#2・#3・#4・#5・#6・#8・#13・#16・#17・#18・#19）が、シナリオ A・B に必要とするもの。対象のテンプレートは P1・P4・P5 と、#4 に挙げたモジュール。lint は L1〜L9・L15〜L18・L21〜L23 |
| `full` | それ以外。後回し・扱わないの要件は必ず full。対応表で提案した lint（L24〜L61）だけに頼る要件も、既定で full |

最初の割り当ては、次の規則で機械的に付けました。
- 次のどちらかに当てはまるものを full にした
  - 担当が MVP の issue でない
  - 未着手でない
- 残りは、成果物のどれかが issue の本文にあるもの（`calib`・`guide` を除く）なら core にした
  - 検証の基本の拒否テストなど、MVP に欠かせない提案（`jku-x5u`・`embedded-jwk`・`alg-confusion`・`untrusted-key`・`tenant-mismatch`・`bola-other-owner`・`spoofed-identity-header`・`revoked-token-rejected` など）を含むものも core にした
  - ただし、提案した lint を含み、MVP に欠かせない提案を含まないものは full にした
- この規則で core に入った提案の lint は 2 つある
  - L25：ヘッダーの `jku`・`x5u`・`jwk`・`x5c`
  - L43：Txn-Token を AT として送る・受ける

```
python tools/trace_check.py --tier core                  # core の件数
python tools/trace_check.py --tier core --require-done   # core に未着手が残っていれば失敗する
```

### 範囲の線引き（後回しとの境目）

- **ワークロードのトークン**：P5（内部の伝搬）とバッチの中のワークロードのトークンは MVP。独立した M2M のプロファイル（client_credentials だけの API 公開など）は #21 の P3
- **データ層**：MVP は PostgreSQL と SQL Server の行単位の制御（RLS・`SESSION_CONTEXT`）まで。クラウドの STS・WIF・DB のトークン認証と製品ごとのモジュールは #21 で扱うことを提案する（`deferred:data-platform-modules`。`new_items.md` の #21 の節）。採るかどうかは #21 で決める
- **IdP**：Keycloak は MVP。Entra・Auth0/Okta・Cognito に固有の要件は #21

## 成果物の参照の書式

`<種類>:<パス>[#<アンカー>]` と書きます。アンカーとパスの末尾の名前は、英小文字・数字・`-` を使います。台帳の列名だけは、`_` を含む snake_case のままにします。

| 種類 | 例 | 担当 | 実装済みのときに解決する場所（`req:<ID>` を探す範囲） |
| --- | --- | --- | --- |
| `registry` | `registry:claims#volatility`、`registry:token_types#alg_allowlist`、`registry:hops#aud`、`registry:questions#q-actor`、`registry:README#slide-134-map` | #3 | `templates/registry/<claims\|token_types\|hops>.schema.json` の、その名前のプロパティ。`questions` は `questions.yaml` のその `id` の項目。`README` は `README.md` のそのアンカーの節 |
| `template` | `template:00_core#hop-table`、`template:modules/M_token_validation#jwks-cache`、`template:claim_request#q01` | #4（`CONTRIBUTING` は #13） | `templates/<パス>.md` の、アンカー `<a id="…"></a>`（または `{#…}`）から次のアンカーまで |
| `review` | `review:perspectives#q-hop-lifetime`、`review:contrasts/four-lifetimes` | #5 | `templates/review/<パス>.md` のアンカーの節 |
| `lint` | `lint:L16`、`lint:L1a`、`lint:R3b` | #6・#16・#17・#18（L10 は #21） | `tools/claim_lint/RULES.md` の、その ID の表の行（`\| L16 \|`）か見出しから、次の規則まで |
| `catalog` | `catalog:issue_events#hook_invoked`、`catalog:token_kinds` | #2 | `templates/catalog/<パス>.yaml` の、そのキーか `id` のノード（`.md` ならアンカーの節） |
| `test` | `test:negative_tests#alg-none`、`test:consumer_contract#unknown-claim-ignored` | #8 | `templates/runtime/<パス>.md` のアンカーの節 |
| `ci` | `ci:claims#secret-scan` | #16 | `.github/workflows/<パス>.yml` のそのジョブ |
| `render` | `render:payload-schema` | #19 | 解決の手段なし。作ったときに `trace_check.py` の `RESOLVERS` に足す |
| `calib` | `calib:errors#exchange-widens` | #12 | 同上 |
| `guide` | `guide:split-slide-64` | #10 | 同上。スライドを足したら、要件の `slide` と分類を新しい ID で更新する |
| `deferred` | `deferred:idp-entra` | #21・#7・#20 | 実装済みにできない。着手したら、具体的な種類の項目に付け替える |
| `none` | `none:out-of-scope` | #22 | 実装済みにできない |

提案した lint の規則には、仮に `L24`〜`L61` の番号を付けています。#6 の本文にある L1〜L18・L21〜L23 と重ならないように、L24 から付けました。`planned_items.yaml` の題に仮の名前を書いてあります。担当の issue で規則を採るときに番号を決め直してかまいません。その場合は、対応表の参照も同じ PR で直します。

新しい成果物が要るときは、次の手順で足します。どの要件にも使われない提案があると、検査は失敗します。
1. `planned_items.yaml` に `origin: proposed` で足す
2. `python tools/trace_check.py --write-new-items` で `new_items.md` を作り直す

## スライドを追加・修正したとき（#10）

`trace_check.py` は、次の 2 つを照合します。
- `deck/slide_ids.json` の ID の集合と、`classification` の ID の集合
- `docs/slides.json` の本文のハッシュと、`classification` の `sha`

スライドを足す・消す・書き換えると、対応表を直すまで CI が失敗します。

1. ID の一覧と Web 版を作り直す：`cd deck && node build.js` と `python tools/build_web_slides.py`
2. 足したスライドを `classification` に入れ、分類を決める
   - `design-decision` なら要件に分解する
   - `knowledge` なら `teaching` に 1 行足す
   - 消したスライドの行と要件は消す（ID は欠番にする。#15）
3. 中身を変えたスライドは、要件を読み直す
   - 足りない判断を要件に足す
   - 番号（`.R<n>`）は付け直さず、末尾に足す。消した要件の番号は再利用しない
4. `python tools/trace_check.py --update-hash <ID> --reviewed-on <日付>` でハッシュを更新する。`summary` も書き直される
5. `python tools/trace_check.py` を通し、この README の件数の表も直す

## 確かめ方

```
python tools/check_slide_refs.py templates   # slide:<id> の参照がすべて実在する
python tools/trace_check.py                  # 対応表の検査と件数
python -m pytest tools/tests                 # trace_check.py のテスト（通る例と落ちる例）
```

CI の依存は、`tools/requirements-ci.txt` でハッシュまで固定しています（`pip install --require-hashes --no-deps`）。

CI には node と Playwright を入れていません。そのため、`tools/tests` のうち次のテストは CI では skip になります。手元で実行してください。
- `test_slide_ids.py` のうち、node を要するもの（デッキのビルド）
- `test_viewer.py`

## 作成方法と点検状況

対応表は、生成 AI（Claude）が作りました。
- `docs/slides.json` のスライドの本文とノートを読んで、要件に分解した
- 要件を、計画の issue（#2〜#21）の本文に書かれた成果物に割り当てた
- 出発点には、2026-11-22 の LLM による突き合わせの表（#22 の「現状」）を使い、分類と要件はスライドの本文から改めて導いた

**人による点検は未実施。** 作成とは別の LLM のセッションで 1 回点検し、指摘をすべて反映しました（記録：`research/reviews/trace-2026-11-22.md`、PR #27 のコメント）。作成者が 1 日以上空けて見直す手順（#13）は、まだ済んでいません。

点検の範囲は次のとおりです。
- 分類の付け直し：26 枚
- 分解の網羅：20 枚
- 担当の割り当て：30 件
- 後回し・扱わない：全件
