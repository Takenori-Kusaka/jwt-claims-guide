# claims-as-code：クレーム設計書の構造化（YAML）と CI での機械検査の設計（先行事例の調査）

調査日：2026-11-22。対象リポジトリの計画（`templates/CONTRIBUTING.md`、`templates/trace/README.md`、issue #3・#6・#19）を前提に、OpenAPI 系・policy-as-code・data contract・privacy-as code・IdP 設定の as-code の先行事例を調べた。
凡例：「Cited Findings」は出典のある事実・他者の意見。「Inferences」は本調査者の推論・提案（意見）。調査は WebSearch の要約と一部の一次資料の取得に基づく。検索要約の中身は、一次資料で確かめていないものがある（各項目に注記）。

前提（リポジトリから読んだ計画）：
- `claims.yaml`（台帳）＋ `token_types`・`hops`・`issuance_profile`・`issuance_effects.yaml`、それぞれ JSON Schema（`templates/registry/*.schema.json`、Ajv strict 前提、`$id` に版）
- claim-lint：L1〜L9・L15〜L18・L21〜L23・L62〜L67 など、多数の意味の規則（多くが error）。L2 は IdP ごとの予約名一覧ファイルを読む
- `claim-lint render`：台帳から Markdown 表、トークン種別ごとのペイロード JSON Schema（`required` あり、`additionalProperties: true`）を生成し、CI で設計書の表と差分 0、発行側の設定と照合（#19）
- `trace_check.py`：スライド→要件→成果物の対応を CI で検査。重複キーを拒否する YAML 読み込み
- semver：error 規則の追加はメジャー

---

## 1. OpenAPI/AsyncAPI エコシステムからの教訓（spec-first、Spectral、破壊的変更の検出、overlay、$ref、描画、ガバナンス）

### Takeaway
OpenAPI 系で定着したのは「仕様（YAML/JSON）を正とし、汎用の linter（Spectral）に組織ルールセットを載せ、旧版との diff で破壊的変更を CI で止める」という 3 点セットである。ただし大規模組織（Azure）は手書き OpenAPI から上位の DSL（TypeSpec）へ移っており、「巨大な手書き YAML」そのものは成功の型ではない。

### Cited Findings
- spec/API-first の普及：Postman 2025 State of the API で、何らかの API-first は 82%（完全 API-first 25%、ある程度 57%）。2024 は 74%、2023 は 66% — [Postman State of the API 2025](https://www.postman.com/state-of-api/2025/)、[Nordic APIs の解説](https://nordicapis.com/a-deep-dive-into-the-state-of-the-api-2025/)（数値は自己申告の調査。プレスリリースでは 83.2% とする版もあり、出典間で小差あり — [BusinessWire](https://www.businesswire.com/news/home/20251008162423/en)）
- Spectral のルールセットは `extends`（既存ルールセットの継承と調整）、`rules`（`given` の JSONPath で対象を選び `then` の `field`/`function` で検査）、`overrides`（「どの形式・ファイル・ファイルの部分に適用するか」を調整）、`aliases`（JSONPath の再利用）、`documentationUrl`（警告から説明への導線）を持つ — [Spectral docs: custom rulesets](https://raw.githubusercontent.com/stoplightio/spectral/develop/docs/guides/4-custom-rulesets.md)
- Spectral は `formats` の指定を任意とし、「lint するどの文書にも当てはまる規則なら無視してよい」と書いている（＝OpenAPI 以外の任意の JSON/YAML にも使える）。ただしカスタム format の登録は JS API だけで、CLI は既定の format に限られる — [同上](https://raw.githubusercontent.com/stoplightio/spectral/develop/docs/guides/4-custom-rulesets.md)
- カスタム関数は既定で `functions/` から読み込まれ、定義したルールセットにスコープされる。非同期関数は 5.4.0 から。6.0 で JS 形式のルールセットが加わった — [Spectral docs: custom functions](https://github.com/stoplightio/spectral/blob/13291133b5b8ab853e9e911bc85e3241c67a3b16/docs/guides/5-custom-functions.md)（固定コミットの版。最新の develop で文言を要確認）
- Spectral を内蔵する製品の制約：Insomnia はカスタム関数を許さず組み込み関数だけ — [Kong/Insomnia docs](https://developer.konghq.com/how-to/add-custom-linting-rules/)。Gravitee は Spectral の関数が OAS/AsyncAPI に限られるとし、他形式にはカスタム関数を要するとする — [Gravitee docs](https://documentation.gravitee.io/apim/govern-apis/api-score/rulesets-and-functions)
- ガバナンス：Adidas は API スタイルガイドを文章と Spectral ルールセットの両方で最初期に公開した例として Spectral の README に挙がる — [Spectral README](https://raw.githubusercontent.com/stoplightio/spectral/develop/README.md)（ルールセットの中身は未確認）。Zalando はガイドラインを API Guild が所有し、専用 linter Zally（OpenAPI 2/3、REST API・CLI・Web UI）で検査 — [Zalando guidelines](https://opensource.zalando.com/restful-api-guidelines/)、[Zally](https://opensource.zalando.com/zally/)。Zalando 規則の Spectral 版はコミュニティ（Baloise）が別に保守し、どの規則を実装済みか README で追跡 — [@baloise/spectral-rules](https://npmjs.com/package/@baloise/spectral-rules)
- Azure：`azure-openapi-validator`（別名 LintDiff）は autorest の拡張で Spectral のルール形式をサポートする linter。README には AutoRest とプラグインが非推奨で 2026-07-01 に退役、「新しい lint 規則は受け付けない」とある — [Azure/azure-openapi-validator](https://github.com/Azure/azure-openapi-validator)（README 取得で確認。LintDiff が「PR で新たに生じた違反だけを出す」かは README には書かれておらず未確認）
- Azure は新規サービスに TypeSpec での定義を求め、既存サービスにも移行の検討を求める。GA API の破壊的変更の回避を設計・スタイルより上位の規則に置く。破壊的変更の検査は自前の `openapi-diff`（47 種の変化を検出）で、最新の GA・preview 版と比較 — [azure-rest-api-specs CONTRIBUTING（fork）](https://github.com/ZhidaLiu/azure-rest-api-specs/blob/main/CONTRIBUTING.md)、[Azure/openapi-diff](https://github.com/Azure/openapi-diff)。Swagger→TypeSpec 変換器の出力は「人のレビューと手直しが要る出発点」 — [TypeSpec Azure: migrate swagger](https://azure.github.io/typespec-azure/docs/migrate-swagger/01-get-started)（fork の CONTRIBUTING は本家と同一か未確認）
- oasdiff：`breaking` で 2 版の OpenAPI を比べ、ERR（確実に非互換）／WARN（非互換の可能性）／INFO に分類。`--fail-on ERR` で CI を失敗させる。意図した変更は設定ファイルで許容でき、GitHub Action は PR にコメントする — [oasdiff BREAKING-CHANGES.md](https://github.com/tufin/oasdiff/blob/v1.10.16/BREAKING-CHANGES.md)、[Nordic APIs](https://nordicapis.com/using-oasdiff-to-detect-breaking-changes-in-apis/)（検査の件数は 100 超／250 超と出典で食い違う）
- buf breaking：互換の基準を FILE（既定・最も厳しい）⊃ PACKAGE ⊃ WIRE_JSON ⊃ WIRE の入れ子のカテゴリで選ぶ。各規則がどのカテゴリに属すかが決まっている — [buf docs: breaking rules](https://buf.build/docs/breaking/rules/)
- OpenAPI Overlay 1.0.0 は 2024-10 に公開。元の文書から分離した変更の形式（JSONPath で対象を選び update/remove） — [Overlay Specification v1.0.0](https://spec.openapis.org/overlay/v1.0.0)。ツールの対応状況は各ツールで確かめるよう仕様自体が勧めている（同）

### Inferences
- 「台帳を YAML で正とし、そこから表を生成する」こと自体は spec-first の定石と一致し、妥当（意見）。ただし成功事例の共通点は、**検査（lint）と互換性（diff）を分けている**こと。現計画は lint（L 規則）と trace は厚いが、「前版の claims.yaml との diff による破壊的変更の検出」が独立の成果物として見当たらない。スライド 133（`p11-why-govern`「トークンの中身の変更は破壊的変更として扱う」）は、まさに oasdiff/buf breaking 型の `claim-diff` を要求していると読める。
- buf の「カテゴリの入れ子」は、クレームの互換性にそのまま写せる：例）`WIRE`＝受け手の検証が通るか（必須クレームの追加・型変更・`aud`/`iss` 変更）、`SEMANTIC`＝意味の変更（`not_meaning`・`usage`・`volatility` の変更）、`DOC`＝説明だけ。受け手ごとにどのカテゴリを守るかを選べる。
- Overlay は「組織共通の台帳＋環境別・テナント別の差分」（例：シナリオ A の t1/t2、本番と検証）を、元の YAML を複製せずに表すのに使える。ただし対応ツールが少ないので、MVP では採らないほうが安全（意見）。
- Azure の事例は、(a) 巨大な手書き仕様は上位 DSL に移る圧力がかかる、(b) 自前ツール（AutoRest/LintDiff）は退役しうる、の 2 点の警告になる。claim-lint を自前で作るなら、規則の記述をエンジンから切り離しておく（後述 4.）のが退役の保険になる。

### Gaps
- Spectral を OpenAPI 以外の独自 YAML（台帳のような文書）に大規模に適用した公開事例は、今回の検索では見つからなかった。
- Adidas・Zalando で「規則の数」「誤検知率」「規則の抑止の運用」を数値で公開した資料は見つからなかった。
- Redoc 等の描画ツールについては今回は追加調査していない（台帳の Markdown 生成は自前の render で足りるため優先度を下げた）。

---

## 2. 形式の選択：JSON Schema の方言／OpenAPI の拡張（`x-`）／独自 YAML＋独自 JSON Schema

### Takeaway
「独自 YAML＋その形を定める JSON Schema（2020-12）」が最も筋がよい。エディタ補完は yaml-language-server の `$schema` モードラインで得られ、ペイロード検証用の JSON Schema は台帳から**生成**すればよい。OpenAPI の `securitySchemes` への `x-` 拡張は、クレームの台帳の列（寿命・データ源・PII・ホップ）を載せる場所がなく、相互運用の利点も薄い。

### Cited Findings
- yaml-language-server は先頭のコメント `# yaml-language-server: $schema=<URL またはパス>`（IntelliJ 形式の `# $schema: ...` も可）でスキーマを紐づけ、相対パスは YAML ファイルの位置から解決する。優先順位はモードライン → インラインの `$schema` → カスタムのスキーマプロバイダ → `yaml.schemas` 設定 → SchemaStore — [yaml-language-server README](https://github.com/redhat-developer/yaml-language-server)、[unpkg 1.24.0 README](https://unpkg.com/yaml-language-server@1.24.0/README.md)
- SchemaStore（`https://www.schemastore.org/api/json/catalog.json`）は既定で有効 — 同上
- CUE は JSON Schema との相互変換（JSON Schema→CUE、CUE→JSON Schema）を公式チュートリアルで提供 — [Converting JSON Schema to CUE](https://cuelang.org/docs/tutorial/converting-json-schema-to-cue)、[Converting CUE to JSON Schema](https://cuelang.org/docs/tutorial/converting-cue-to-json-schema/)
- Kubernetes は OpenAPI スキーマに `x-kubernetes-validations`（CEL）を足して、フィールド間の規則（例：`maxReplicas >= minReplicas`、相互排他 `!has(self.a) || !has(self.b)`）をスキーマ内に書く方式を採り、1.29 で GA。ただしルールは現在のオブジェクトだけを見られ、オブジェクトをまたぐ規則は不可 — [Kubernetes blog: CRD validation rules](https://kubernetes.io/blog/2022/09/23/crd-validation-rules-beta/)、[KEP-2876](https://www.kubernetes.dev/resources/keps/2876/)、[Google Open Source Blog](https://opensource.googleblog.com/2023/11/kubernetes-crd-validation-using-cel.html)
- 型のないフィールドや preserve-unknown-fields の配下では CEL の `has(self.X)` がコンパイルできない、という実務上の落とし穴の報告 — [NVIDIA AIPerf docs](https://docs.nvidia.com/aiperf/kubernetes/crd-validation-rules)
- リポジトリの規約：JSON Schema に独自キーワードを置かない（Ajv strict モードがエラーにするため） — `templates/CONTRIBUTING.md` §4「版の管理」

### Inferences
- **台帳の形の定義**：現計画の「独自 YAML＋JSON Schema（2020-12）＋Ajv strict」を維持するのがよい（意見）。各 YAML の 1 行目は `template_version` と決まっているので、2 行目に `# yaml-language-server: $schema=./claims.schema.json` を置けば、VS Code 等で補完・即時検証が得られる（規約の「1 行目」と衝突しない位置に置く必要がある）。
- **OpenAPI の `x-` 拡張を採らない理由**：(1) `securitySchemes` は「どの方式で認証するか」の宣言で、クレームの意味・寿命・データ源・ホップを表す構造を持たない。(2) `x-` は検証の対象外で、結局独自スキーマが要る。(3) 台帳の利用者（IdP 設定者・レビュアー）は OpenAPI を持たないシステムも扱う。代わりに、**生成物として** OpenAPI の `securitySchemes`（`oauth2`/`openIdConnect` の scope 一覧）や、API ごとの `x-required-claims` を出力するのは有益（意見）。
- **ペイロード検証の相互運用**：台帳→トークン種別ごとの payload JSON Schema の生成（#19）は、JSON Schema の主戦場（実行時の検証ライブラリ、契約テスト）に乗るので最も価値が高い生成物（意見）。`additionalProperties: true` の方針は、受け手の「未知のクレームは無視」（`test:consumer_contract#unknown-claim-ignored`）と一致する。
- **CEL を台帳スキーマに埋める案**：Kubernetes 型の `x-...-validations` は Ajv strict と衝突し、オブジェクトをまたぐ規則（台帳 × token_types × hops）は書けない。したがってスキーマ内の規則は単一オブジェクトの形・型・列挙・`if/then`（例：`decision: 採用` なら `refs`/`assumption`/`revisit_trigger` から 2 つ以上）に限り、文書をまたぐ規則は別のエンジンに置く、と線を引くのがよい（意見）。
- JSON Schema の方言（独自 vocabulary）は Ajv strict・エディタの対応が弱くなるので避ける（意見。CONTRIBUTING の方針と一致）。

### Gaps
- JSON Schema 2020-12 の `if/then` で「2 つ以上が必須」（n-of-m）を書くと読みにくくなる点の、定量的な評価資料は見つけていない。
- OpenAPI の security 定義にクレーム要件を持たせる標準化の動き（例：OpenAPI 3.2 以降で scope 以外の要件）は今回確かめていない。

---

## 3. 文書をまたぐ規則のエンジン（OPA/conftest/Rego、CUE、CEL、JSON Schema if/then）

### Takeaway
「DPoP を選んだら AT に `cnf.jkt` があり、全受け手が DPoP を照合する」のような**文書をまたぐ規則**は、JSON Schema では書けず、CEL（Kubernetes 型）も単一オブジェクトに限られる。書けるのは Rego（conftest）か、汎用言語（Python）か、CUE。選択の決め手は「規則を誰が読むか」と「通る例・落ちる例のテストを書けるか」で、Python の自前実装は規則の多さ（60 超）に対して保守が重くなりやすい。

### Cited Findings
- conftest は構造化された設定ファイル（YAML・JSON・TOML・HCL・CUE など多数）を JSON に変換して OPA の Rego ポリシーを適用する。既定で `policy/` を読み、`deny` の集合にメッセージを返すのが典型。`<名前>_test.rego` を `conftest verify` で実行してポリシー自体を単体テストできる。出力は JSON/表、`--trace` で評価の追跡 — [conftest.dev](https://conftest.dev/)、[Red Hat blog](https://www.redhat.com/en/blog/conftest-policy-as-code-ansible)（多くは二次資料・ミラーからの要約。最新版のフラグは未確認）
- conftest は複数ファイルを 1 つの入力にまとめる `--combine` を持つ — 本調査では一次資料で確かめていない（Gaps に記載）
- CUE は「検証を最優先の役割」と位置づけ、制約を unification で合成するため、同じノードに複数の制約が同時に効く。公式の例にフィールド間の大小比較がある — [CUE: data validation use case](https://cuelang.org/docs/concept/data-validation-use-case/)、[How CUE enables data validation](https://cuelang.org/docs/concept/how-cue-enables-data-validation/)
- 一方、CUE だけでは表せないフィールド間比較があり、CI の別段階で強制した、という個人ブログの報告 — [mataroa blog](https://dyb.mataroa.blog/blog/cue-for-safety-critical-infrastructure-validation-235b7fb8/)（一人の筆者の主張）
- Kubernetes の CEL 規則はオブジェクトをまたがない（前節） — [KEP-2876](https://www.kubernetes.dev/resources/keps/2876/)
- privacy-as-code の Fides は「宣言（system YAML の privacy declaration）× ポリシー（data categories に対する ANY/ALL/NONE の規則）」を `fides evaluate` で評価し、違反した宣言と規則を名指しで出す。Git hook や CI に組み込む — [Fides CLI: evaluate](https://ethyca.com/docs/dev-docs/cli/check/cmd-evaluate)、[Evaluating code with Fides](https://ethyca.com/evaluating-code-with-fides)、[fideslang policy](https://ethyca.github.io/fideslang/resources/policy)

### Inferences
- **規則の層を 3 つに分ける**（意見・推奨）：
  1. 形（JSON Schema 2020-12 ＋ Ajv strict）：型・必須・列挙・単一行の `if/then`。エディタで即時に出る。
  2. 文書をまたぐ意味の規則（L4・L5・L9・L15・L16・L21〜L23・L62〜L67 など）：1 か所の「結合した入力」（claims＋token_types＋hops＋issuance_profile＋issuance_effects を 1 つの JSON にまとめたもの）に対する述語として書く。
  3. 外部との照合（L1a の IANA 登録簿、L2 の IdP 予約名、実 IdP 設定との drift）：データを取得・正規化する処理が要るので Python。
- **層 2 のエンジン**：
  - Python 自前（現計画）：利点は依存が少なく、trace_check.py と同じ言語・同じ CI、エラーメッセージを日本語で自由に書け、`req:` の逆参照や「warning の抑止理由を出力に出す」（#13）の独自要件を実装しやすい。欠点は規則のロジックとエンジンが混ざり、規則数（L1〜L67）に比例して保守が増えること。
  - Rego/conftest：規則を宣言的に書け、`_test.rego` で通る例・落ちる例を規則ごとに持てる（#6 の完了基準と一致）。欠点は Rego の学習コスト（読者に IdP 管理者・非エンジニアを想定すると重い）、日本語メッセージ・抑止理由の表示を自前で作る必要。
  - Spectral：JSONPath＋関数で単一文書の規則は書きやすいが、`given` は 1 文書の中を指すため、文書をまたぐ規則は結局カスタム JS 関数になる。Python の CI に Node を足す（リポジトリの CI は現在 node を入れていない、`templates/trace/README.md`）。
  - CUE：形と規則を 1 言語で書けるが、Ajv/JSON Schema を正とする現方針と二重になる。
- **推奨（意見）**：Python のまま進め、ただし「規則＝データ＋小さな述語」の形にする。例：`issuance_effects.yaml` のように、**規則の大半を宣言（YAML の表）にして、エンジンは汎用の評価器にする**（「選択 X なら、対象 Y の集合に条件 Z」を表で持つ）。L62 はすでにこの形。こうしておけば、後で Rego に移す場合も規則の表は再利用できる。Rego は「組織が独自規則を足したい」需要が実際に出たときの拡張点として残す（`--policy-dir` で conftest を併走させる等）。
- Fides の「宣言 × ポリシー → 違反した宣言と規則を名指し」は、claim-lint の出力形式の手本になる（規則 ID・対象のクレーム/ホップ・根拠の版・抑止の理由）。

### Gaps
- conftest の `--combine` など、複数文書をまとめて評価する機能の現行の挙動は一次資料で確かめていない。
- Rego と Python で同規模の規則群を保守した比較事例は見つからなかった。

---

## 4. 類例：data contracts（ODCS・datacontract-cli）と privacy-as-code（fideslang）

### Takeaway
data contract と privacy-as-code は「フィールド単位の分類・所有者・CI での検査・版の比較」を YAML で行う、クレーム台帳に最も近い類例である。両者とも (1) 標準の語彙（ODCS／fideslang の分類体系）を外部に置き、(2) lint（スキーマ適合）と breaking/changelog（版の比較）を別コマンドにしている。一方、評価が見る項目が限られる（Fides）など、「宣言はあるが検査が中身を見ない」穴も報告されている。

### Cited Findings
- datacontract-cli：ODCS（Open Data Contract Standard）の YAML を扱い、`lint` は ODCS の JSON Schema に対する検証（既定で最初のエラーで止まる）。`breaking v1 v2` で破壊的変更を検出（内部で changelog を使い error と warning だけを表示）。新しい版では `changelog v1 v2` が別にある — [datacontract-cli (PyPI)](https://pypi.org/project/datacontract-cli/)、[0.10.24](https://pypi.org/project/datacontract-cli/0.10.24/)（版によりコマンドの有無が異なる。古いミラーでは breaking が「近日」となっていた）
- Go 版 CLI にも `--with stable/datacontract.yaml` で比較して破壊的変更で失敗する機能がある — [datacontract/cli-go](https://github.com/datacontract/cli-go)
- fideslang：プライバシーの分類体系（Data Categories＝データの種類、Data Uses＝目的、Data Subjects＝誰のデータか。古い版では Data Qualifiers も）。カテゴリは階層化され継承される。GDPR・CCPA・LGPD・ISO 19944 を想定。拡張は既存のクラス構造の上に作るよう推奨 — [fideslang (GitHub)](https://github.com/ethyca/fideslang)、[fideslang docs](https://ethyca.github.io/fideslang)。分類群の数（3 か 4 か）は README と古い版で食い違う
- `fides evaluate` は変更されたリソースがポリシーに適合するかを自動で検査し、Git hook・CI に組み込む — [Fides CLI: check](https://ethyca.com/docs/dev-docs/cli/check)
- 既知の穴：evaluate は data categories・data use・data subjects・qualifier だけを見ており、`dataset_references` は検査に入らない、という issue — [lightrun（Fides issue の転載）](https://lightrun.com/answers/ethyca-fides-evaluation-should-consider-a-datasets-privacy-data)（二次転載）
- Ethyca は Enigma 2022 で privacy-as-code を発表 — [USENIX Enigma 2022 slides](https://usenix.org/system/files/enigma2022_slides_kieran.pdf)（スライドの中身は未精読）

### Inferences
- 台帳の `pii_category`（個人情報／要配慮個人情報／個人関連情報／仮名加工情報／該当なし）は、日本の個人情報保護法の区分で fideslang と軸が違う。fideslang を採るより、**独自の列挙を正とし、必要なら fideslang のカテゴリへの対応表を別に持つ**のが現実的（意見）。
- data contract から学ぶべきは「`lint`（形）と `breaking`（版の比較）と `changelog`（人が読む差分）を別コマンドにする」構成。claim-lint にも `claim-lint diff --base <ref>` を足し、出力を (a) CI の失敗判定、(b) PR に貼る人向けの変更点の表、に分けるとよい（意見）。
- Fides の穴（検査が一部の列しか見ない）は、台帳でも「列はあるが、どの規則にも使われない列」が生まれうる警告。trace_check と同じ発想で、**スキーマの各列が少なくとも 1 つの規則か生成物に使われている**ことを検査する（列のカバレッジ）とよい（意見）。

### Gaps
- ODCS・Fides の導入企業数や、導入後に形骸化した事例（失敗事例）の信頼できる資料は見つからなかった。採用の証拠は、ツールの公開と版の更新が続いていること（datacontract-cli は 1.0.x 系まで PyPI に出ている）程度。
- ODCS の現行版（v3 系）のフィールド単位の分類・所有者の列は、今回一次資料で確かめていない。

---

## 5. リスク：YAML の複雑化、台帳と実 IdP 設定の drift、非エンジニアの可読性、規則疲れ、版

### Takeaway
最大のリスクは「台帳は正しいが、実際の IdP の設定が違う」drift である。Keycloak・Auth0・Entra いずれも設定を export できるが、export は順序・ID の揺れでノイズが大きく、正規化してから台帳の「期待値」と比べる必要がある。規則疲れは、error の抑止を禁じる現方針では「誤検知のある規則が error のまま入る」形で現れるので、規則を warn で導入して誤検知率を測ってから error に上げる段階を設けるべき。

### Cited Findings
- keycloak-config-cli は realm export 形式の JSON/YAML から「望む状態」を Keycloak に反映するツール。管理下のリソースだけを purge する state management のオプションがある — [adorsys/keycloak-config-cli](https://github.com/adorsys/keycloak-config-cli)、[docs](https://adorsys.github.io/keycloak-config-cli/intro/)
- Keycloak の export を Git で差分管理すると、配列の順序が不定で返るため差分が大きくなる、エンティティ ID の変化が差分を膨らませる、という利用者の報告 — [Keycloak forum: How do you manage your realm configuration?](https://forum.keycloak.org/t/how-do-you-manage-your-realm-configuration/18099)、[Keycloak forum: Configuration migration](https://forum.keycloak.org/t/configuration-migration/10022)
- 基準の export と比較して正規化・最小化した YAML を作る提案（Javers を使う）が keycloak-config-cli の issue にある（未実装の提案） — [issue #799](https://github.com/adorsys/keycloak-config-cli/issues/799)
- 夜間に Admin API で実 realm を取り、Git の realm JSON と diff して通知する自作の drift 検出の事例（ArgoCD は「健全」と表示する一方で Keycloak が JWT のクレームを落としていた、という題の記事） — [dev.to（infraforge）](https://dev.to/infraforge/when-argocd-shows-healthy-but-keycloak-silently-strips-jwt-claims-5f24)（検索の要約で確認。本文の取得は 404 で、詳細は未確認）
- Auth0 Deploy CLI：`a0deploy export --format=yaml --output_folder=local` でテナント設定を YAML（またはディレクトリ形式の JSON）に出力し、逆に import できる。import はテナントに破壊的なので開発テナントで試すよう勧める — [Auth0 Deploy CLI: use as a CLI](https://auth0.com/docs/deploy-monitor/deploy-cli-tool/use-as-a-cli)、[auth0-deploy-cli docs](https://github.com/auth0/auth0-deploy-cli/blob/master/docs/using-as-cli.md)
- Entra：Microsoft365DSC は設定を DSC の構成ファイルに export し、望む状態との drift を監視できるが、Entra の全設定を export できるわけではない、という報告 — [Practical365](https://practical365.com/dsc-snapshot-microsoft365-tenant/)、[TechTarget](https://www.techtarget.com/searchWindowsServer/tip/How-to-use-Microsoft-365-DSC-to-avoid-configuration-drift)（二次資料）。コミュニティの EntraExporter は Entra の設定を JSON に export する（`Export-Entra -Path ... -All`） — [office365itpros](https://office365itpros.com/2023/08/24/entraexporter-tool/)
- 規則の誤検知と抑止：oasdiff は意図した変更を設定ファイルで許容する仕組みを持つ — [oasdiff](https://github.com/tufin/oasdiff/blob/v1.10.16/BREAKING-CHANGES.md)。Spectral は `overrides` でファイル・部分ごとに適用を変えられる — [Spectral docs](https://raw.githubusercontent.com/stoplightio/spectral/develop/docs/guides/4-custom-rulesets.md)
- 版：oasdiff は ERR/WARN/INFO の 3 段階 — [oasdiff](https://github.com/tufin/oasdiff/blob/v1.10.16/BREAKING-CHANGES.md)。buf は互換のカテゴリを利用者が選ぶ — [buf docs](https://buf.build/docs/breaking/rules/)
- リポジトリの規約：error 規則の抑止と重大度の引き下げは 0 件（#13）。error の規則を足すとメジャー版 — `templates/CONTRIBUTING.md` §2・§4

### Inferences
- **drift の対策（推奨・意見）**：`claim-lint import <idp>` で実 IdP の export を「台帳と同じ語彙の観測値」（`observed.yaml`：トークン種別ごとに実際に載るクレーム、mapper の書き手、寿命、`typ`、`alg`、送信者制約）に正規化し、`claim-lint drift` で台帳の期待値と比べる。正規化では、配列を名前でソートし、内部 ID・タイムスタンプ・秘密を捨てる（Keycloak の報告どおりの雑音対策）。
  - Keycloak：realm export（またはAdmin API）の `protocolMappers`・client scope・`accessTokenLifespan`・lightweight access token の設定などを読む。
  - Auth0：Deploy CLI の YAML（Actions のコードは静的に読み切れないので、「Actions が書く名前空間」を宣言として台帳に持たせ、実トークンの観測で補う）。
  - Entra：claims mapping policy・optional claims をアプリ登録から取る（全設定は export できない前提で、対象を絞る）。
  - **設定の静的照合には限界がある**（Actions・Lambda・スクリプトの mapper）。ケーススタディが実物で行っているように、**実際に発行したトークンのペイロード**を、生成した payload JSON Schema（#19）で検証するのが最終の照合になる。設定の diff と実トークンの検証の両方を持つのがよい。
- **規則疲れ（意見）**：#13 の「error は抑止不可」は強いが、誤検知のある規則が error で入ると、規則を直す PR が溜まり台帳の更新が止まる。新しい規則は warn で入れ（マイナー版）、シナリオ A・B で誤検知率を記録し（#6 の完了基準がすでに求めている）、基準を下回ったら error に上げる（メジャー版）という段階を `RULES.md` に持たせるとよい。Azure の LintDiff のように「新しく変えた部分にだけ新規則を当てる」方式も検討に値する（LintDiff の実際の挙動は未確認）。
- **YAML の複雑化（意見）**：ファイルを token_types・hops・claims に分けるのは $ref によるモジュール化と同じ発想で妥当。ただし YAML の anchor/alias・マージキーは禁止し（読む人と生成器の解釈がずれる）、重複キーの拒否（trace_check と同じ）を claim-lint にも入れる。1 クレームの列が 40 を超えるので、Lite（必須列だけ）と Full を JSON Schema で分ける（Lite で必須、Full で追加）と、記入の負担を下げられる。
- **非エンジニアの可読性**：読む人には YAML を見せず、生成した Markdown 表（#19）を見せる。PR では「生成した表の差分」と「claim-diff の人向け要約」を自動でコメントする（oasdiff の GitHub Action の型）。

### Gaps
- 台帳と実 IdP 設定の drift を CI で検出した、JWT クレームに特化した公開事例は、上記の dev.to 記事（本文未取得）以外に見つからなかった。
- Entra の claims mapping policy・optional claims を Microsoft Graph で export する公式手順は、今回一次資料で確かめていない。
- 規則の数と誤検知率・開発者の離脱の関係を測った研究は見つからなかった。

---

## 6. 推奨（形式・規則のエンジン・生成物・IdP 設定の取り込みと比較）

### Takeaway
「台帳を YAML で正とし、機械で検査し、表や JSON Schema を生成する」ことは、OpenAPI・data contract・privacy-as-code の定石と一致し、良い実践である（意見だが、類例の構成に裏付けがある）。成功の条件は、形の検査・意味の検査・版の比較・実環境との照合の 4 つを分け、特に後ろの 2 つ（claim-diff と IdP drift）を最初から計画に入れることである。

### Cited Findings
- spec-first の構成要素（lint のルールセット、旧版との diff、PR へのコメント）は OpenAPI 系で定着している — [Spectral](https://raw.githubusercontent.com/stoplightio/spectral/develop/README.md)、[oasdiff](https://github.com/tufin/oasdiff/blob/v1.10.16/BREAKING-CHANGES.md)、[Azure/openapi-diff](https://github.com/Azure/openapi-diff)
- data contract も lint／breaking／changelog を別コマンドにしている — [datacontract-cli](https://pypi.org/project/datacontract-cli/)
- 設定を YAML に export／import する IdP のツールがある（Keycloak・Auth0）。export の差分は正規化しないと雑音が多い — [keycloak-config-cli](https://github.com/adorsys/keycloak-config-cli)、[Auth0 Deploy CLI](https://auth0.com/docs/deploy-monitor/deploy-cli-tool/use-as-a-cli)、[Keycloak forum](https://forum.keycloak.org/t/how-do-you-manage-your-realm-configuration/18099)

### Inferences（すべて本調査者の提案）
1. **形式**：独自 YAML ＋ JSON Schema 2020-12（Ajv strict）。現計画のまま。各ファイルの 2 行目に yaml-language-server のモードラインを置く。anchor・マージキー・重複キーを禁止。OpenAPI の `x-` 拡張にはしない。
2. **規則のエンジン**：Python（claim-lint）を主とし、規則を「宣言の表（`issuance_effects.yaml` 型）＋汎用の評価器」に寄せる。規則ごとに通る例・落ちる例のフィクスチャ（#6）。Spectral は採らない（CI に Node が増え、文書をまたぐ規則はカスタム関数になる）。Rego は組織の追加規則の拡張点として後で検討。
3. **版の比較（新規の提案）**：`claim-lint diff --base <git ref>` を作り、変更を buf 型のカテゴリ（受け手の検証が壊れる／意味が変わる／説明だけ）と oasdiff 型の重大度で出す。スライド 133 の「中身の変更は破壊的変更」に対応する。意図した変更の許容は、理由つきで台帳の `change_log` か別ファイルに書く。
4. **生成物**：
   - 設計書の Markdown 表（#19。CI で差分 0）
   - トークン種別ごとの payload JSON Schema（#19。発行したトークンの検証と契約テストに使う）
   - 受け手ごとの「必須クレームと照合」の一覧（`consumers`・`enforced_at` から。ゲートウェイや各サービスの設定の雛形、例：必須 `aud`・`iss`・`typ`・DPoP の照合）
   - CODEOWNERS（`owner`・`change_controller` から。台帳の行の変更に、その所有者のレビューを必須にする）
   - PR コメント用の人向けの変更点の要約
   - （任意）OpenAPI の `securitySchemes` の scope 一覧
5. **IdP 設定の取り込みと比較**：`claim-lint import keycloak|auth0|entra` で export を正規化した `observed.yaml` にし、`claim-lint drift` で台帳と比べる。MVP は Keycloak（シナリオ A・B）だけ。静的に読めない部分（Auth0 Actions、Cognito の Lambda）は、実発行トークンを payload JSON Schema で検証することで補う。
6. **段階的な厳しさ**：新規則は warn で入れ、誤検知率を `RULES.md` に記録してから error に上げる。列のカバレッジ（どの規則・生成物にも使われない列がない）を trace_check と同じ発想で検査する。

### Gaps
- 上記の推奨のうち、claim-diff のカテゴリ分け・列のカバレッジ検査・warn→error の昇格基準は、先行事例からの類推であり、クレーム台帳での実証はない。採る場合は `author-proposal` として追跡 issue を付けるのが、リポジトリの規約（#13）に合う。
