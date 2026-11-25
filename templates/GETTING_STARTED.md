<!-- template_version: 0.6.0 -->
# 始め方（GETTING_STARTED）

> テンプレートです。候補と検討の問いだけを載せ、採否の理由の見本は載せません（理由の写し書きを防ぐため。#4 の方針）。判断は台帳（claims.yaml など）に 1 回だけ書き、ここからは ID で参照します。

初めて設計書を書く人が、「空の設計書を作る → Lite か Full かの判定 → プロファイルの選択 → 最初の 3 欄の下書き → claim-lint の実行」まで進むための手順です。手順 1〜3 と 5 は合わせて 30 分ほど、手順 4 の下書きは 1〜2 時間を見込んでください。どちらも筆者の見積もりで、人が測った時間ではありません（測った時間は [README.md](README.md) の「記入の目安」に載せる）。最初の 30 分で終わるのは「何を決めるかが分かり、lint の指摘が手元の作業の一覧になる」ところまでです

**始め方は 2 つあります。** どちらも同じファイルを作るので、途中で行き来できます。

| 始め方 | 最初にすること | この手順との関係 |
| --- | --- | --- |
| **エディターで書く** | 設計書のエディター（https://takenori-kusaka.github.io/jwt-claims-guide/claims/ ）を開き、「空の雛形から始める」を押す | 手順 1 のコマンドの代わりになる。手順 2・4 は、エディターで YAML を直して行う。手順 5 の検査は、エディターの中で動く。手順 3 の `--use` と、手順 5 の `render --write` は CLI で行う（書き出したファイルに対して実行する） |
| **CLI で書く** | 下の前提をそろえ、手順 1 から進む | この手順のとおり |

- エディターは、Python を入れなくても使えます。ブラウザの中だけで動き、開いたファイルを外部に送信しません。書き終えたら、ファイルか zip で書き出します
- CLI で作った設計書は、エディターの「フォルダを開く」で開けます。書きながら、表と検査の結果を見られます
- 前提（CLI で書くとき）：Python 3.12 と、`tools/requirements-ci.txt` の依存（`python -m pip install --require-hashes --no-deps -r tools/requirements-ci.txt`）
- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施

<a id="step-1-copy"></a>
## 手順 1（5 分）：空の設計書のディレクトリを作る

項目 ID：`template:GETTING_STARTED#step-1-copy`

記入例の YAML は写しません。記入例をそのまま写すと claim-lint は error 0 で通り、記入例の判断と理由（`rationale`）が残ってしまうからです（#4 の方針「理由の写し書きを防ぐ」）。代わりに、必須のキーだけを持つ空のファイルを作ります。

```
python tools/new_design.py designs/my-service                  # Full の骨組み（Lite か Full かをまだ決めていないときも、これで始める）
python tools/new_design.py designs/my-service --profile lite   # Lite と決まっているとき（hops.yaml を作らない）
```

- 作られるもの：`design.md`（`templates/00_core.md` の写し）、`claims.yaml`（行なし）、`token_types.yaml`（カタログの 17 種類ごとに `decision: 却下`・`rationale` が空の行。使う種類は `採用` に変え、使わない種類は却下の理由を書く）、`hops.yaml`（行なし。`--profile lite` では作らない）、`catalog_answers.yaml`（全イベントの回答が空の行、Lite の 5 問、網羅の節 `idp`・`questions`・`subject_states`・`pairwise`・`outside_enumeration`。問いの ID、主体の状態、層の名前は鍵として入っていて、値だけが空）
- **ホップを書かない Lite の設計は、`hops.yaml` を置きません**。Full の骨組みで始めて、手順 2 で Lite と決まり、ホップを書かないなら、`hops.yaml` を消します。`hops: []` のままでは、スキーマが 1 行以上を求めるので error（TODO）が残ります。Lite では、ファイルが無いこと（中身が空のことも同じ）を claim_lint が info（LOAD）で知らせるだけで、error にはなりません。**Full では経路のホップを書きます**。Full で `hops.yaml` が無い・空のときは、LOAD が warn で知らせます（ホップを読む規則が何も見なくなるため）
- Lite でもホップを書く設計があります（例：DB・ブローカーにトークンで接続する設計。`M_data_layer` の 5. は `hops[].connection_max_lifetime` に書く）。そのときは `--with-hops` を付けて作るか、後から `python tools/new_design.py designs/my-service --with-hops` を実行します（`hops.yaml` が無いときだけ、空の `hops.yaml` を足す。ほかのファイルには触れない）。書くなら 1 行以上を書きます（列は `registry/README.md` の 3.4）
- 組織の名前空間を使わない設計は、`claims.yaml` に `namespaces` のキーを書きません（骨組みにも入っていません。使うときの書き方は、`claims.yaml` の先頭のコメントにあります）
- yaml-language-server の modeline（`$schema`）は、置き場所からの相対パスで書かれます。OS を問わず同じコマンドで動きます（シェルの展開を使わない）
- 作った直後に `python tools/claim_lint designs/my-service`（Lite の骨組みなら `--profile lite` を付ける。まだ判定していないなら付けない）を実行すると、空の欄の数だけ指摘が出ます。目録・発行方式などの空欄は error、カタログへの回答の空欄は Lite では warn（R2。Full では error）です。Lite の 5 問の空欄は、`--profile lite` のときだけ warn で出ます（L73。Full では 5 問を見ません）。その一覧が、これから書くことの一覧です。作った直後の骨組みに、スキーマの違反（SCHEMA）は 1 件もありません。スキーマが求める欄がまだ空（null・空の文字列・空の配列）のときは、SCHEMA ではなく **TODO（まだ書いていない欄）** として 1 欄に 1 件出ます（重大度は error のまま）。SCHEMA が出たら、書いた値の形が違います
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

信頼の境界ごとに、プロファイルを 1 つ選びます（[README.md](README.md) の「プロファイルとモジュールの組み合わせ方」）。選んだプロファイルとモジュールの判断表を開き、問いを読んでおきます。

**記入欄を書く場所は、`design.md` の付録 D（プロファイルとモジュールの記入欄）です。** 選んだものを `--use` に並べて、もう一度 `new_design.py` を実行すると、その記入欄の表が付録 D に足されます（`design.md` のほかのファイルと、すでに書いた項目には触れません）。名前は、ファイル名（`.md` を除く）か、1 つに決まる先頭の部分（`P4` など）です。

```
python tools/new_design.py designs/my-service --profile full --use P1,P5,M_token_validation,M_idp_keycloak
python tools/new_design.py designs/my-service --profile lite --use P1,M_token_validation,M_idp_keycloak
```

- Full：記入欄のあるすべての項目が足されます
- Lite：見出しが〔Lite・Full：記入〕で始まる項目だけが足されます（例：`M_privacy_minimization` の個人情報保護法の判断表）。ほかの項目は問いを読み、答えは 00_core の 3. と台帳に書きます
- 見出しの〔〕に書く場所がある項目（`M_data_layer` の 5.〔…記入（00_core に書く）〕、`M_idp_keycloak` の 5.〔…記入（台帳の既定どおりの行）〕）は、付録 D には表を足さず、「その場所に 1 回だけ書く」という 1 行だけを足します。同じ答えを 2 か所に書かないためです
- 当てはまらない記入欄は消さずに、最初の列に「無い」と理由を書きます（00_core の冒頭の「使わない記入欄」）

| 境界 | プロファイル |
| --- | --- |
| 人がブラウザで使う | `profiles/P1_human_web.md` |
| AI エージェントが利用者の代わりに呼ぶ | `profiles/P4_ai_agent_delegation.md` |
| 入口の内側でサービス間に運ぶ | `profiles/P5_internal_propagation.md` |

根拠：templates/README.md の「プロファイルとモジュールの組み合わせ方」、templates/00_core.md の付録 D、research/template-design/pilot.md の 6.

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

- 最初は error がたくさん出ます（空の設計書では、Lite で 100 件ほど、Full で 260 件ほど。Full は、カタログへの回答と主体の状態の行列の空欄も error のため）。規則の ID（TODO・R1・R2・R8 など）の意味は `tools/claim_lint/RULES.md` にあります
- `--profile` は手順 2 の判定に合わせます。5 問に 1 つでも Yes があれば Full なので、`--profile lite` を付けません。Yes があるのに `--profile lite` で実行すると、L73 が warn で知らせ、レビューの受け付けで Full に書き直すよう返されます（[README.md](README.md) の「Lite と Full の判定」）
- error を 0 件にしてからレビューに回します。error の規則は抑止できません（`templates/CONTRIBUTING.md` の 2.）
- render の区間を手で直すと、`render --check` が失敗します。台帳を直してから `--write` します

次に進むときは、[README.md](README.md) の「記入の順序」の 5. 以降（問い × 仕組み、台帳、ホップ、ライフサイクル表、カタログへの回答）を書きます。

根拠：tools/claim_lint/RULES.md、tools/claim_lint/RENDER.md の 2.、templates/CONTRIBUTING.md の 2.

<a id="step-6-self-check"></a>
## 手順 6（レビューに出す前）：提出前の自己点検をする

項目 ID：`template:GETTING_STARTED#step-6-self-check`

設計書を書き終えて、レビューに出す前に行います。レビューの問い（`review/perspectives.md` の 168 問）は、誰が確かめるかで 4 つに分けてあります（`review/triage.yaml`）。

| 区分 | 誰が確かめるか | 書き手がすること |
| --- | --- | --- |
| A 機械 | claim_lint | 手順 5 で error を 0 にする。warn には、行ごとに理由を書く |
| B 書き手の自己点検 | **書き手** | 下のチェックリストで確かめる |
| C 人の判断 | レビュアー（`review/short_list.md`） | 12.（自信のない点）に、見てほしい点を書く |
| D 専門家 | 専門家（`review/escalation.md`） | 当たりそうな行を 12. に書く |

- **チェックリストは、PR のテンプレートにあります**（このリポジトリの `.github/PULL_REQUEST_TEMPLATE/design_doc.md`。PR を作る URL に `?template=design_doc.md` を付けると、本文に入ります）。区分 B の問いと、機械で確かめる規則がまだ無い・足りない区分 A の問いが並んでいます
- `templates/` だけを自分のリポジトリに写して使うときは、このファイルは付いてきません。上のパスから、自分のリポジトリの `.github/PULL_REQUEST_TEMPLATE/` に写してください
- 満たす行に印を付けます。満たさない・当てはまらない行は、印を付けずに、行の末尾に理由を書きます。レビュアーは、印の無い行を読み、3 件（25 問の回答の行と、【No なら Blocker】の行から 2 件）を抜き取って確かめます
- 問いごとの見る欄は、`review/perspectives.md` の同じ ID の問いにあります
- `python tools/review_triage.py --design designs/my-service` で、レビュアーに出る問い（この設計の性質に当たる、人の判断が要る問い）を先に見られます。答えにくい問いがあれば、設計書に書き足すか、12. に書きます

チェックリストは、いま 51 行です（観点書の 73 問に当たる。同じ確かめで答えが決まる問いは 1 行にまとめた）。量と分け方は筆者の提案です（追跡 #56）。lint の規則ができるたびに減ります（#68）。

根拠：templates/review/triage.yaml、筆者の提案：書き手の提出前の自己点検（追跡 #56）
