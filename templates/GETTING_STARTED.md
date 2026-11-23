<!-- template_version: 0.3.0 -->
# 始め方（GETTING_STARTED）

> テンプレートです。候補と検討の問いだけを載せ、採否の理由の見本は載せません（理由の写し書きを防ぐため。#4 の方針）。判断は台帳（claims.yaml など）に 1 回だけ書き、ここからは ID で参照します。

初めて設計書を書く人が、「空の設計書を作る → Lite か Full かの判定 → プロファイルの選択 → 最初の 3 欄の下書き → claim-lint の実行」まで進むための手順です。手順 1〜3 と 5 は合わせて 30 分ほど、手順 4 の下書きは 1〜2 時間を見込んでください。どちらも筆者の見積もりで、人が測った時間ではありません（測った時間は [README.md](README.md) の「記入の目安」に載せる）。最初の 30 分で終わるのは「何を決めるかが分かり、lint の指摘が手元の作業の一覧になる」ところまでです

- 前提：Python 3.12 と、`tools/requirements-ci.txt` の依存（`python -m pip install --require-hashes --no-deps -r tools/requirements-ci.txt`）
- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施

<a id="step-1-copy"></a>
## 手順 1（5 分）：空の設計書のディレクトリを作る

項目 ID：`template:GETTING_STARTED#step-1-copy`

記入例の YAML は写しません。記入例をそのまま写すと claim-lint は error 0 で通り、記入例の判断と理由（`rationale`）が残ってしまうからです（#4 の方針「理由の写し書きを防ぐ」）。代わりに、必須のキーだけを持つ空のファイルを作ります。

```
python tools/new_design.py designs/my-service
```

- 作られるもの：`design.md`（`templates/00_core.md` の写し）、`claims.yaml`（行なし）、`token_types.yaml`（カタログの 17 種類ごとに `decision: 却下`・`rationale` が空の行。使う種類は `採用` に変え、使わない種類は却下の理由を書く）、`hops.yaml`（行なし）、`catalog_answers.yaml`（全イベントの回答が空の行と、Lite の 5 問）
- yaml-language-server の modeline（`$schema`）は、置き場所からの相対パスで書かれます。OS を問わず同じコマンドで動きます（シェルの展開を使わない）
- 作った直後に `python tools/claim_lint designs/my-service --profile lite` を実行すると、空の欄の数だけ error が出ます。その一覧が、これから書くことの一覧です
- 記入例（`templates/examples/`）は、書き方に迷ったときに読む資料として使います

根拠：templates/CONTRIBUTING.md の 4.、research/template-design/report.md の Q6、筆者の提案：空の骨組みから始めて lint の指摘を作業の一覧にする（追跡 #4）

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
## 手順 4（1〜2 時間。筆者の見積もり）：最初の 3 欄の下書き

項目 ID：`template:GETTING_STARTED#step-4-first-three`

最初に書くのは、ほかの欄の前提になる次の 3 つと、問いの下書きです。ここでは**使うものだけ**を書き、使わないものの理由は後で書きます。

1. **範囲と信頼の境界**（`design.md` の 2.）：境界を図にし、境界ごとにプロファイルの名前を書く。あわせて、ユースケースごとにどの問い（`templates/registry/questions.yaml` の 11 問）が要るかだけを 6. に書く
2. **発行方式の選択**（`token_types.yaml` の `issuance_profile`）：クライアントの種類・grant・送信者制約・AT の形式・RT の方式・要求の保護・準拠するプロファイル。既定の組み合わせ（機密の BFF＋認可コード＋PKCE）から外れる点だけ理由を考える
3. **トークン目録**（`token_types.yaml` の `token_types`）：使う種類の行だけ `採用` にして、発行者・宛先・持つ者・形式・寿命を書く。シナリオ A の記入例では、目録の全体が 165 欄ほどあり、多くは採用の行の検証の設定（鍵・JWKS・サイズ）です。最初の下書きでは R1 が求める列のうち、発行者・宛先・持つ者・寿命・保存場所・運び方から埋めます。却下の行の理由は、手順 5 の後に書きます

ここまで書くと、台帳（`claims.yaml`）のクレームは「この発行方式とトークンの上に何を載せるか」として考えられます。

根拠：templates/00_core.md の 2.・4.・5.・6.、筆者の提案：境界・発行方式・目録を最初の 3 欄にし、使うものから書く（追跡 #4）

<a id="step-5-lint"></a>
## 手順 5（5 分）：claim-lint を実行する

項目 ID：`template:GETTING_STARTED#step-5-lint`

```
python tools/claim_lint designs/my-service --profile lite     # Full なら --profile を付けない
python tools/claim_lint render designs/my-service --write    # design.md の生成の区間を埋める
```

- 最初は error がたくさん出ます（空の設計書では 100 件を超える）。規則の ID（R1・R2・R8 など）の意味は `tools/claim_lint/RULES.md` にあります
- error を 0 件にしてからレビューに回します。error の規則は抑止できません（`templates/CONTRIBUTING.md` の 2.）
- render の区間を手で直すと、`render --check` が失敗します。台帳を直してから `--write` します

次に進むときは、[README.md](README.md) の「記入の順序」の 5. 以降（問い × 仕組み、台帳、ホップ、ライフサイクル表、カタログへの回答）を書きます。

根拠：tools/claim_lint/RULES.md、tools/claim_lint/RENDER.md の 2.、templates/CONTRIBUTING.md の 2.
