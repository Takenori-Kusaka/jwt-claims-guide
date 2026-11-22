<!-- template_version: 0.1.0 -->
# スライドと成果物の対応表（#22）

ガイドの全スライドと、計画の成果物（台帳の列・テンプレートの欄・lint の規則・観点書の問い・実行テストなど）との対応表です。**網羅の正は、issue の本文ではなく、この対応表です。** issue の本文に要件を並べる方式では、書いた人が思いついたことしか入りません。実際に、5 つの観点のレビューを経た後でも、スライド 81（`slide:p06-narrow-downstream`、下流ほど絞る）が計画から抜けていました（#11・#22）。

各 issue（#3・#4・#5・#6・#8・#17・#18・#19 など）の完了基準は「この issue が担当する要件が、すべて実装済みになっている（`trace-check` で確かめる）」です。担当の要件は、下の「件数」の表と `python tools/trace_check.py` の出力で確かめます。

## 件数（2026-11-22 時点）

<!-- counts:begin -->
- スライド 152 枚：設計判断 125 枚、知識 10 枚、構造 17 枚。教材に使う知識のスライド 10 枚
- 要件 705 件：未着手 660、実装済み 0、後回し 44、扱わない 1
- **扱わない 1 件／全 705 件（0.1%）**
- 成果物 492 件：issue の本文にあるもの 254 件、対応表で足した提案 238 件（`new_items.md`）

| 担当 | 要件 | 未着手 | 後回し | 扱わない | 提案した成果物 |
| --- | --- | --- | --- | --- | --- |
| #2 | 5 | 5 | 0 | 0 | 0 |
| #3 | 128 | 128 | 0 | 0 | 32 |
| #4 | 192 | 192 | 0 | 0 | 69 |
| #5 | 116 | 116 | 0 | 0 | 67 |
| #6 | 145 | 145 | 0 | 0 | 35 |
| #8 | 49 | 49 | 0 | 0 | 31 |
| #13 | 2 | 2 | 0 | 0 | 0 |
| #16 | 2 | 2 | 0 | 0 | 0 |
| #17 | 2 | 2 | 0 | 0 | 0 |
| #18 | 16 | 16 | 0 | 0 | 3 |
| #19 | 3 | 3 | 0 | 0 | 0 |
| #21 | 44 | 0 | 44 | 0 | 1 |
| #22 | 1 | 0 | 0 | 1 | 0 |
<!-- counts:end -->

## ファイル

| ファイル | 中身 |
| --- | --- |
| `requirements.yaml` | `summary`（件数。`trace_check.py` が実際の件数と照合する）、`classification`（152 枚すべての分類）、`requirements`（設計判断のスライドの要件）、`teaching`（教材に使う知識のスライド） |
| `planned_items.yaml` | 要件から参照できる成果物の一覧。`origin: issue` は担当の issue の本文にあるもの、`origin: proposed` は対応表を作るときに足した提案 |
| `new_items.md` | `origin: proposed` の一覧を issue ごとにまとめたもの（生成物。`python tools/trace_check.py --write-new-items`）。各 issue の本文に書き足すかを、担当の issue で決める |
| `../../tools/trace_check.py` | 対応表の検査（CI：`.github/workflows/trace.yml`） |

## スライドの分類

| 分類 | 意味 | 対応表での扱い |
| --- | --- | --- |
| `design-decision` | 設計者・実装者・レビュアーが決める、守る、避けることを求めるスライド（チェックリスト・「リーダーの視点」・推奨を含む） | 1 件以上の要件に分解する |
| `knowledge` | 背景・説明・比較・事実で、それ自体の規則を持たないスライド | 教材（対比表・用語集・判断の木・観点書）に使うものだけ `teaching` に載せる |
| `structural` | 表紙・Part の扉・目次・締め | なし |

### 初回の突き合わせの表からの分類の変更

初回の表（#22 の「現状」。設計判断 118 枚）から、次の 7 枚を `knowledge` から `design-decision` に変えました。設計判断は 125 枚です。

| 番号 | スライド | 理由 |
| --- | --- | --- |
| 10 | `slide:p01-jwt-structure` | 「秘密にしたい情報は JWS に入れず、必要なら JWE」「ヘッダーを鵜呑みにしない」という規則がある |
| 41 | `slide:p03-recent-changes` | 「手順書や書籍の記述は、現行の公式文書で確かめ直してから使う」という規則がある |
| 60 | `slide:p04-namespace-object-example` | 構造の版 `v` と、フラットな別名を台帳に定義することを求めている |
| 66 | `slide:p05-pep-pdp` | PEP・PDP の分担と「トークンが有効かどうかだけで認可しない」を求めている |
| 87 | `slide:p06-flow-browser-to-db` | 見出しが規則（ブラウザにトークンを置かない、ID トークンを API に送らない、DB に利用者の AT を渡さない） |
| 113 | `slide:p09-jws-is-readable` | 「載せる前に誰が読めるかを問う」「ペイロードを機微データとして分類する」を求めている |
| 130 | `slide:p10-guidance-standards` | 規則の根拠に何を使い、草案を必須と書かないという根拠の書き方の規則がある |

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
  # 扱わない のときだけ（#13 の「対象外」の書き方に合わせる）
  assumption: 起きない前提
  breaks_when: その前提が崩れる条件
```

### 状態

| 状態 | 意味 | 検査 |
| --- | --- | --- |
| `未着手` | 担当の成果物がまだない、または要件を満たしていない | — |
| `実装済み` | 担当の成果物があり、要件を満たしている | `planned_items` のすべてが実在の成果物に解決すること（下の表）。解決の手段がまだない種類（`render`・`calib`・`guide`・`deferred`・`none`）は、実装済みにできない |
| `後回し` | MVP の外（#21。ほかに #7・#20） | `owner_issue` が #7・#20・#21 のどれか。逆に、これらが担当の要件は `後回し` か `扱わない` |
| `扱わない` | 成果物を作らない | `assumption`（起きない前提）と `breaks_when`（崩れる条件）の両方。`planned_items` は `none:out-of-scope`、担当は #22 |

`実装済み` に変えるのは、担当の issue の PR です。成果物を作ったら、その PR で状態を `実装済み` に変え、CI で解決を確かめます。

## 成果物の参照の書式

`<種類>:<パス>[#<アンカー>]`。アンカーとパスの末尾の名前は、英小文字・数字・`-`（台帳の列名は `_` を含む snake_case のまま）です。

| 種類 | 例 | 担当 | 実装済みのときに確かめること |
| --- | --- | --- | --- |
| `registry` | `registry:claims#volatility`、`registry:token_types#alg_allowlist`、`registry:hops#aud`、`registry:questions#q-actor`、`registry:README#slide-134-map` | #3 | `templates/registry/<claims\|token_types\|hops>.schema.json` に、その名前のプロパティがある。`questions` は `questions.yaml` にその `id` がある。`README` は `README.md` にそのアンカーがある |
| `template` | `template:00_core#hop-table`、`template:modules/M_token_validation#jwks-cache`、`template:claim_request` | #4（`CONTRIBUTING` は #13） | `templates/<パス>.md` があり、アンカー `<a id="…"></a>`（または `{#…}`）がある |
| `review` | `review:perspectives#q-hop-lifetime`、`review:contrasts/four-lifetimes` | #5 | `templates/review/<パス>.md` とアンカー |
| `lint` | `lint:L16`、`lint:L1a`、`lint:R3b` | #6・#16・#17・#18（L10 は #21） | `tools/claim-lint/RULES.md` に、その ID の表の行（`\| L16 \|`）か見出しがある |
| `catalog` | `catalog:issue_events#hook_invoked`、`catalog:token_kinds` | #2 | `templates/catalog/<パス>.yaml` に、そのキーか `id` がある（`.md` ならアンカー） |
| `test` | `test:negative_tests#alg-none`、`test:consumer_contract` | #8 | `templates/runtime/<パス>.md` とアンカー |
| `ci` | `ci:claims#secret-scan` | #16 | `.github/workflows/<パス>.yml` にそのジョブがある |
| `render` | `render:payload-schema` | #19 | 解決の手段なし（作ったときに `trace_check.py` の `RESOLVERS` に足す） |
| `calib` | `calib:errors#exchange-widens` | #12 | 同上 |
| `guide` | `guide:split-slide-64` | #10 | 同上。スライドを足したら、要件の `slide` と分類を新しい ID で更新する |
| `deferred` | `deferred:idp-entra` | #21・#7・#20 | 実装済みにできない（着手したら、具体的な種類の項目に付け替える） |
| `none` | `none:out-of-scope` | #22 | 実装済みにできない |

提案した lint の規則には、仮に `L24`〜`L61` の番号を付けています（#6 の本文にある L1〜L18・L21〜L23 と重ならないように、L24 から付けた。`planned_items.yaml` の題に仮の名前を書いてある）。担当の issue で規則を採るときに番号を決め直してよく、その場合は対応表の参照も同じ PR で直します。

新しい成果物が要るときは、`planned_items.yaml` に `origin: proposed` で足し、`python tools/trace_check.py --write-new-items` で `new_items.md` を作り直します。どの要件にも使われない提案は、検査で失敗します。

## スライドを追加・修正したとき（#10）

`trace_check.py` は、`deck/slide_ids.json` の ID の集合と `classification` の ID の集合を照合します。スライドを足す・消すと、対応表を直すまで CI が失敗します。

1. `cd deck && node build.js` と `python tools/build_web_slides.py` で ID の一覧を作り直す
2. 足したスライドを `classification` に入れ、分類を決める。`design-decision` なら要件に分解する。消したスライドの行と要件は消す（ID は欠番にする。#15）
3. 中身を変えたスライドは、要件を読み直し、足りない判断を要件に足す。番号（`.R<n>`）は付け直さず、末尾に足す。消した要件の番号は再利用しない
4. `python tools/trace_check.py` を通す。件数が変わったら `summary` を出力どおりに直し、この README の件数の表も直す

## 確かめ方

```
python tools/check_slide_refs.py templates   # slide:<id> の参照がすべて実在する
python tools/trace_check.py                  # 対応表の検査と件数
python -m pytest tools/tests                 # trace_check.py のテスト（通る例と落ちる例）
```

## 作成方法と点検状況

対応表は、生成 AI（Claude）が `docs/slides.json` のスライドの本文とノートを読んで要件に分解し、計画の issue（#2〜#21）の本文に書かれた成果物に割り当てて作りました。出発点には、2026-11-22 の LLM による突き合わせの表（#22 の「現状」）を使い、分類と要件はスライドの本文から改めて導きました。

**人による点検は未実施。** 作成とは別の LLM のセッションでの点検（#13 の手順）も、まだ行っていません（#22 の作業項目）。点検したら、記録を `research/reviews/trace-<日付>.md` に置き、この節を #13 の定型文に置き換えます。
