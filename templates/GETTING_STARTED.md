<!-- template_version: 0.3.0 -->
# 30 分で始める（GETTING_STARTED）

> テンプレートです。候補と検討の問いだけを載せ、採否の理由の見本は載せません（理由の写し書きを防ぐため。#4 の方針）。判断は台帳（claims.yaml など）に 1 回だけ書き、ここからは ID で参照します。

初めて設計書を書く人が、30 分で「Lite か Full かの判定 → プロファイルの選択 → 最初の 3 欄 → claim-lint の実行」まで進むための手順です。30 分は筆者の見積もりで、人が測った時間ではありません（測った時間は [README.md](README.md) の「記入の目安」に載せる）。

- 前提：Python 3.12 と、`tools/requirements-ci.txt` の依存（`python -m pip install --require-hashes --no-deps -r tools/requirements-ci.txt`）
- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施

<a id="step-1-copy"></a>
## 手順 1（5 分）：記入例を写して、自分の設計書のディレクトリを作る

項目 ID：`template:GETTING_STARTED#step-1-copy`

記入例は推奨ではなく、ケーススタディの前提での一例です。**中身の判断は写さず、形だけを使います。**

```
mkdir -p designs/my-service
cp templates/00_core.md designs/my-service/design.md
cp templates/examples/scenario-a/{claims,token_types,hops,catalog_answers}.yaml designs/my-service/
```

- YAML の 1 行目の `# template_version`、2 行目の yaml-language-server の modeline（`$schema` の相対パス）は、置き場所に合わせて直します（`templates/CONTRIBUTING.md` の 4.）
- 写した YAML の行は、すべて自分の判断で書き直すか、消してから書きます。理由（`rationale`）を写したままにしないでください

根拠：templates/CONTRIBUTING.md の 4.、筆者の提案：記入例の形を写して中身を書き直す始め方（追跡 #4）

<a id="step-2-gate"></a>
## 手順 2（5 分）：Lite か Full かを決める

項目 ID：`template:GETTING_STARTED#step-2-gate`

[README.md](README.md) の「Lite と Full の判定」の 5 問に Yes／No で答え、`catalog_answers.yaml` の `lite_criteria` に書きます。1 つでも Yes なら Full です。

| 問い | キー |
| --- | --- |
| トークンが信頼の境界を越えるか | `crosses_boundary` |
| マルチテナントか | `multitenant` |
| 委任・トークン交換があるか | `delegation_or_exchange` |
| 新しい発行者か | `new_issuer` |
| 規制の対象か | `regulated` |

根拠：templates/README.md の「Lite と Full の判定」、research/template-design/gate1.md の 10.

<a id="step-3-profiles"></a>
## 手順 3（5 分）：プロファイルとモジュールを選ぶ

項目 ID：`template:GETTING_STARTED#step-3-profiles`

信頼の境界ごとに、プロファイルを 1 つ選びます（[README.md](README.md) の「プロファイルとモジュールの組み合わせ方」）。選んだプロファイルとモジュールの判断表を開き、問いを読んでおきます（Lite では、答えは 00_core の 3. と台帳に書く）。

| 境界 | プロファイル |
| --- | --- |
| 人がブラウザで使う | `profiles/P1_human_web.md` |
| AI エージェントが利用者の代わりに呼ぶ | `profiles/P4_ai_agent_delegation.md` |
| 入口の内側でサービス間に運ぶ | `profiles/P5_internal_propagation.md` |

根拠：templates/README.md の「プロファイルとモジュールの組み合わせ方」

<a id="step-4-first-three"></a>
## 手順 4（10 分）：最初の 3 欄を書く

項目 ID：`template:GETTING_STARTED#step-4-first-three`

最初に書くのは、ほかの欄の前提になる次の 3 つです。

1. **範囲と信頼の境界**（`design.md` の 2.）：境界を図にし、境界ごとにプロファイルの名前を書く
2. **発行方式の選択**（`token_types.yaml` の `issuance_profile`）：クライアントの種類・grant・送信者制約・AT の形式・RT の方式・要求の保護・準拠するプロファイル。既定の組み合わせ（機密の BFF＋認可コード＋PKCE）から外れる点だけ理由を考える
3. **トークン目録**（`token_types.yaml` の `token_types`）：使うトークンの種類ごとに、発行者・宛先・持つ者・形式・寿命。使わない種類は却下と理由

ここまで書くと、台帳（`claims.yaml`）のクレームは「この発行方式とトークンの上に何を載せるか」として考えられます。

根拠：templates/00_core.md の 2.・4.・5.、筆者の提案：境界・発行方式・目録を最初の 3 欄にする（追跡 #4）

<a id="step-5-lint"></a>
## 手順 5（5 分）：claim-lint を実行する

項目 ID：`template:GETTING_STARTED#step-5-lint`

```
python tools/claim_lint designs/my-service --profile lite     # Full なら --profile を付けない
python tools/claim_lint render designs/my-service --write    # design.md の生成の区間を埋める
```

- 最初は error がたくさん出ます。規則の ID（R1・R2・R8 など）の意味は `tools/claim_lint/RULES.md` にあります
- error を 0 件にしてからレビューに回します。error の規則は抑止できません（`templates/CONTRIBUTING.md` の 2.）
- render の区間を手で直すと、`render --check` が失敗します。台帳を直してから `--write` します

次に進むときは、[README.md](README.md) の「記入の順序」の 5. 以降（問い × 仕組み、台帳、ホップ、ライフサイクル表、カタログへの回答）を書きます。

根拠：tools/claim_lint/RULES.md、tools/claim_lint/RENDER.md の 2.、templates/CONTRIBUTING.md の 2.
