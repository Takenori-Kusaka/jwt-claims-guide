# 「載せない情報」を宣言で止める検査は、まだ誰も作っていない

- 調査基準日：2026-11-22
- 根拠の調査ノート：`research_notes/クレーム設計の構造化と機械検査の先行事例/`（`structured_formats.md`・`linters_and_checks.md`・`claims_as_code_design.md`）
- 背景として参照した計画：`research/template-design/report.md`、`templates/trace/planned_items.yaml`・`requirements.yaml`、issue #3・#6・#19・#21 の本文
- 凡例：本文では、出典で確かめられた事実を **【確認済】**、調査ノートが Gaps に回した・記憶に頼った・食い違う事項を **【未検証】**、本報告の筆者の判断と提案を **【提案】** と明示する。

JWT クレームの設計書を YAML で正本として管理し、スライド 114 の「載せない情報」の 6 分類（認証の秘密、機微な属性、平文の個人情報を含む ID、変わりうる識別子、細かい権限の一覧、接続元の詳細）に当たる定義を CI で検出する仕組みは、今回の調査の範囲では見つからなかった。近いものは三つの方向に分かれている。第一は、クレーム単位のメタデータの標準である。SD-JWT VC の Type Metadata と OpenID4VCI が `path`・`mandatory`・`sd`・`display` までを定めている。第二は、アプリのソースコードにある `jwt.sign` の引数を見る SAST ルールで、Semgrep、Bearer、Datadog にある。第三は、宣言とポリシーを突き合わせる privacy-as-code（Fides）とデータ契約（ODCS）である。どれも「宣言されたクレーム台帳 × トークンが通る場所 × 識別子の安定性」を判定しない。だから、このリポジトリの claim-lint が取り組んでいるのは空白地帯にあたる。ただし、ゼロから作る必要はない。フィールド名は SD-JWT VC に、形の検証は JSON Schema 2020-12 に、名前の衝突は IANA の CSV に合わせられる。「何のデータか」の語彙は fideslang から、「宣言 × ポリシー → 違反を名指し」の構成は `fides evaluate` から、版の比較は oasdiff と buf から借りられる。新しく作るべきなのは、6 分類を判定するための台帳の列と規則である。中でも計画への影響が大きい点が二つある。一つ目に、いまの `pii_category`（個人情報保護法の区分）だけでは「認証の秘密」と「接続元の詳細」を表せない。二つ目に、要件 `p09-do-not-carry.R6`（接続元の詳細）には機械検査が一つも割り当てられていない。

## 標準が定めるのは path・mandatory・sd・display の 4 つまで

「クレーム版の OpenAPI」に最も近い標準は、SD-JWT VC の Type Metadata である。**【確認済】** 最新版は draft-ietf-oauth-sd-jwt-vc-27（2026-11-16）で、IESG の評価段階にある。クレーム単位のメタデータ（§5.6）は、`path`（必須）、`display`（`locale`・`label`・`description`）、`mandatory`（既定 false）、`sd`（`always`／`allowed`／`never`）、`svg_id` の 5 つである。仕様は「Consumers MUST ignore properties that are not understood」と定めるので、独自のプロパティを足しても互換性は壊れない。また、-04 で入れた JSON Schema を -12 で削除しており、現行の Type Metadata は型と形を持たない（[IETF Datatracker](https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/)）。OpenID4VCI 1.0（Final、2025-09-16）の claims description も、`path`・`mandatory`・`display` の 3 つにとどまる（[OpenID4VCI 1.0](https://openid.net/specs/openid-4-verifiable-credential-issuance-1_0.html)）。EUDI ARF は namespace を「属性の識別子・構文・意味」をエコシステム全体で一意に定める単位としている。ただし、rulebook は人が読む文書（Markdown・PDF）で、機械可読な版は見つからなかった（[ARF Annex 1](https://eu-digital-identity-wallet.github.io/eudi-doc-architecture-and-reference-framework/1.3.0/annexes/annex-1/annex-1-definitions)）。

OAuth・OIDC 側のメタデータは、クレームをさらに薄くしか扱わない。**【確認済】** IANA の JSON Web Token Claims レジストリの列は、Claim Name、Claim Description、Change Controller、Reference の 4 つだけである。登録は約 160 件で、claims の表は CSV（`/assignments/jwt/claims.csv`）で取得できる（[IANA JWT registry](https://www.iana.org/assignments/jwt/jwt.xhtml)）。**【未検証】** OIDC Discovery の `claims_supported`、RFC 9068、RFC 9728 はクレームを名前でしか扱わない、という記述は記憶に基づき、原文を取得していない。OpenAPI にも JWT クレームを記述する標準の仕組みはなく、`x-jwt-claims` のような共通の拡張もない。必須クレームの宣言は製品ごとの設定に分かれている。Azure APIM の `<required-claims>`（[Microsoft Learn](https://learn.microsoft.com/en-us/azure/api-management/validate-jwt-policy)）、Tetrate の `x-tsb-authorization`（[Tetrate](https://docs.tetrate.io/service-bridge/1.5.x/refs/tsb/application/v2/openapi_extensions)）、Envoy の `jwt_authn` がその例で、Envoy は任意のクレーム値の条件を持たない（[Envoy](https://www.envoyproxy.io/docs/envoy/latest/api-v3/extensions/filters/http/jwt_authn/v3/config.proto)）。型付きでクレームを受け止める仕組みとして最も強いのは、Amazon Verified Permissions と Cedar schema である。ID トークンのクレームは principal の属性に、アクセストークンのクレームは `context.token` に入る（[AWS](https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/identity-sources_map-token-to-schema.html)）。

**【提案】** 以上から、台帳の列のうち標準に対応するものがあるのは、名前・必須性・選択的開示・表示ラベルの 4 種類だけである。意味しないこと（`not_meaning`）、データ源、寿命、サイズ、秘匿先、採否の理由に対応する標準のフィールドはない。そして、スライド 114 の判定に必要な「識別子が変わりうるか」「どこから見えるか」も標準にはない。台帳の 1 行を SD-JWT VC の claim metadata の上位集合として設計し、`path`・`mandatory`・`sd`・`display` を同じ名前と意味で持たせるのが、最も安い互換性の確保になる。標準が未知のプロパティの無視を MUST にしているので、上位集合にしても標準側は壊れない。

## 既存の検査は「コードの中」か「署名の欠陥」を見ている

JWT 専用のツールの大半は、署名と検証の実装の欠陥を狙う。**【確認済】** jwt_tool、ZAP の JWT add-on、Burp の JWT Scanner が見るのは、alg=none、アルゴリズムの混同、JWK の注入、期限の欠落である（[jwt_tool](https://raw.githubusercontent.com/ticarpi/jwt_tool/master/README.md)、[ZAP](https://www.zaproxy.org/blog/2020-09-03-zap-jwt-scanner/)、[PortSwigger](https://github.com/PortSwigger/jwt-scanner)）。Spectral の OWASP ルールセットの `owasp:api2:2023-jwt-best-practices` は、securityScheme の説明文が RFC 8725 に言及しているかを見るだけで、クレームの中身は見ない（[ruleset.ts](https://app.unpkg.com/@stoplight/spectral-owasp-ruleset@2.0.1/files/src/ruleset.ts)）。ペイロードの中身を見るのは、ソースコード上の発行箇所を対象にした SAST ルールである。Semgrep の `jwt-exposed-data` は、`jwt.encode` に渡したリテラル以外のオブジェクトをすべて拾う監査ルールである（[Semgrep](https://registry.semgrep.dev/rule/python.jwt.security.audit.jwt-exposed-data.jwt-python-exposed-data)）。Bearer の `javascript_lang_jwt`（CWE-312）は `jwt.sign({ user: { email } })` を危険、`jwt.sign({ user: user.uuid })` を安全とする（[Bearer](https://docs.bearer.com/reference/rules/javascript_lang_jwt)）。Datadog にも同じ趣旨の規則がある（[Datadog](https://docs.datadoghq.com/security/code_security/static_analysis/static_analysis_rules/javascript-node-security/jwt-sensitive-data/)）。IdP の設定の監査では、kcwarden が `ClientWithFullScopeAllowed`（全ロールがトークンに載る）を検出する。ただし、protocol mapper ごとに機微な属性を見る監査は記載されていない（[kcwarden](https://iteratec.github.io/kcwarden/auditors/clients)）。

スライド 114 の分類に当てはめると、既存ツールの守備範囲が偏っていることがわかる。

| スライド 114 の分類 | 既存の検出手段（入力） | 台帳にそのまま使えるか |
|---|---|---|
| 1. 認証の秘密 | Semgrep `jwt-exposed-credentials`（コード）。ただし個別ページは HTTP 404 で、公開が続いているか **【未検証】** | 使えない |
| 2. 機微な属性 | Bearer・Datadog（コード）、Presidio・Google DLP（値） | 語彙と値の検査だけ使える |
| 3. 平文の個人情報を含む ID | Bearer の email 検出（コード）が部分的に | 使えない |
| 4. 変わりうる識別子 | 検出するルールはない。Entra の文書が「`upn` は認可に使わない」「`email` と `upn` は変わりうる」と明言している（[Entra](https://learn.microsoft.com/en-us/entra/identity-platform/optional-claims-reference)） | 根拠と既知の一覧として使える |
| 5. 細かい権限の一覧 | kcwarden `ClientWithFullScopeAllowed`（Keycloak の設定。間接的） | 発想を借りられる |
| 6. 接続元の詳細 | 検出するルールはない | なし |

**【提案】** これらの SAST ルールの入力はアプリのソースコードなので、台帳には向けられない。それでも、IdP の外で自前に JWT を発行するコードがある組織では、claim-lint と並べて CI に入れる価値がある。台帳の宣言とコード上の発行の食い違い（ドリフト）を見つけるためである。シークレットスキャンも、別の層で役に立つ。**【確認済】** gitleaks の既定ルールには `jwt`（`ey…​.ey…`、entropy 3）と `jwt-base64` があるが、ペイロードを復号して中身を判定する仕組みはない（[gitleaks.toml](https://raw.githubusercontent.com/gitleaks/gitleaks/master/config/gitleaks.toml)）。このガイドのスライドや docs にある例示用の JWT は確実に検出されるので、許可リスト（allowlist）か、署名部を明らかなダミーにする規約が先に要る。

## 借りるべき型は「宣言 × 場所」の判定と「lint／diff の分離」

検出の仕組みとして最も近い先例は、JWT ではなく privacy-as-code にある。**【確認済】** Fides は、システムの YAML に書いたプライバシー宣言（data category × data use × data subject）を、ポリシー（ANY／ALL／NONE の規則）と照らし合わせて `fides evaluate` で評価する。違反した宣言と規則を名指しで出し、Git hook や CI に組み込める（[Fides CLI: evaluate](https://ethyca.com/docs/dev-docs/cli/check/cmd-evaluate)）。fideslang の data category は階層ラベルで、スライド 114 にそのまま対応するキーがある。認証の秘密は `user.authorization.credentials`・`user.authorization.password`、機微な属性は `user.name.*`・`user.contact.address.*`・`user.demographic.date_of_birth`、メールは `user.contact.email`、接続元は `user.device.ip_address`・`user.device.device_id`・`user.location.*` である。API キー、社員番号、アカウント ID の専用キーはなく、既存の親の下に子カテゴリを足して拡張することが推奨されている（[fideslang data categories](https://ethyca.github.io/fideslang/taxonomy/data_categories/)）。もう一つ、小さいが型が同じ先例がある。obs-types は、分類の enum と出力先の組み合わせで lint する。L002 は「PII を LABEL に置かない」、L003 は「SECRET を LOG・AUDIT 層に置かない」である（[obs-types](https://docs.rs/obs-types/0.1.0/src/obs_types/classification.rs.html)）。これは、計画中の L65（`confidential_from` × `visible_to`）と同じ「分類 × 出る場所」の型である。

**【確認済】** 一方で、Fides の evaluate が一部の列（data categories・use・subjects・qualifier）しか見ておらず、`dataset_references` は検査に入らない、という issue が報告されている（[lightrun の転載](https://lightrun.com/answers/ethyca-fides-evaluation-should-consider-a-datasets-privacy-data)。二次転載）。**【提案】** これは台帳にとっての警告である。「列はあるのに、どの規則にも使われない列」は形骸化する。`trace_check.py` と同じ発想で、スキーマの各列が少なくとも一つの規則か生成物に使われていることを検査する「列のカバレッジ」を入れるとよい。

構成の面では、OpenAPI とデータ契約の両方が、形の検査（lint）と版の比較（breaking／changelog）を別のコマンドに分けている。**【確認済】** oasdiff は 2 版を比べて変更を ERR／WARN／INFO に分け、`--fail-on ERR` で CI を止める（[oasdiff](https://github.com/tufin/oasdiff/blob/v1.10.16/BREAKING-CHANGES.md)）。buf breaking は、互換の基準を FILE ⊃ PACKAGE ⊃ WIRE_JSON ⊃ WIRE という入れ子のカテゴリから選ばせる（[buf](https://buf.build/docs/breaking/rules/)）。datacontract-cli は `lint`、`breaking`、`changelog` を分けている（[datacontract-cli](https://pypi.org/project/datacontract-cli/)）。逆の教訓もある。Azure は、手書きの OpenAPI から上位の DSL（TypeSpec）へ移った。自前の linter である azure-openapi-validator は、README で新しい lint 規則を受け付けないとしている。依存する AutoRest は 2026-07-01 に退役する（[Azure/azure-openapi-validator](https://github.com/Azure/azure-openapi-validator)）。**【提案】** claim-lint を自前で作るなら、規則をエンジンから切り離して宣言の表（`issuance_effects.yaml` 型）として持つのが、退役に備える保険になる。

## 調査ノート間の食い違いと、確かめるべきこと

三つの調査ノートは、いくつかの点で食い違っている。どれも本報告では決着させず、下の表に確かめ先を書く。

| 論点 | ノートの記述 | 状態と確かめ方 |
|---|---|---|
| fideslang のライセンス | `structured_formats.md` は「CC BY 4.0、管理は IAB Tech Lab（Ethyca から寄贈）」とし、IAB Tech Lab のページと寄贈の告知を出典に挙げる（[IAB Tech Lab fideslang](https://iabtechlab.github.io/fideslang)、[Ethyca 寄贈告知](https://ethyca.com/blog/ethyca-donates-fideslang-privacy-taxonomy-to-the-iab-tech-lab)）。`linters_and_checks.md` は Gaps で「Apache-2.0 と記憶」とする | **未解決**。IAB Tech Lab と ethyca の各 GitHub リポジトリの `LICENSE` ファイルと、taxonomy のページのライセンス表記を見比べる。コード（Python パッケージ）と分類体系の文書でライセンスが違う、という仮説も併せて確かめる。語彙を台帳のスキーマに写すなら、CC BY 4.0 の場合は表示の義務が生じる。その場合、`LICENSE-CONTENT.md` に出典を表示する |
| fideslang の分類群の数 | Data Categories・Data Uses・Data Subjects の 3 つか、Data Qualifiers を含む 4 つか。README と古い版で食い違う（[fideslang GitHub](https://github.com/ethyca/fideslang)） | **未解決**。台帳で使うのは data category だけなので、影響は小さい。採るときは版を固定する。ラベル自体も変わっており、古い資料には `user.provided.identifiable.contact.email` という旧体系のパスがある（[Ethyca blog](https://ethyca.com/blog/fideslang-a-taxonomy-for-privacy-engineering)） |
| `pii_category` の値 | `structured_formats.md` は fideslang のラベルに限るよう提案する。`linters_and_checks.md` は fideslang の data category を必須のタグにするよう提案する。`claims_as_code_design.md` は、個人情報保護法の区分の独自の列挙を正とし、fideslang へは対応表で結ぶよう提案する | 本報告は、軸が違うので両立させる立場を取る（次節）。#3 の本文は、`pii_category` を個人情報保護法の 5 区分と定めている |
| 規則のエンジン | `linters_and_checks.md` は OPA／conftest を「台帳に向けられる最有力」とし、Spectral の独自ルールも選択肢に挙げる。`claims_as_code_design.md` は、Python を主とし、Rego は後の拡張点にとどめ、Spectral は採らない（Node が増えるうえ、文書をまたぐ規則はカスタム関数になる）とする | 本報告は後者を取る。理由は、CI が Python だけで回っていること、日本語のメッセージと抑止の理由を出力する独自の要件（#13）があることである。ただし、発行済みトークンの検査は、生成した JSON Schema で足りる |
| 版の比較の計画 | `claims_as_code_design.md` は「前版との diff による破壊的変更の検出が計画に見当たらない」とする | ノートの事実誤認である。`lint:L10`（互換性を壊す変更の検出）は #21 にある。ただし #21 は「需要が出たら着手する拡張の一覧」なので、MVP には入っていない |
| 小さな数値 | oasdiff の検査数は 100 超か 250 超か、出典で食い違う。Postman の API-first の割合も 82% と 83.2% の版がある | 本報告の結論には影響しない |

ほかの未検証の事項もここにまとめる。**【未検証】** スライド 114 の「FAL2 以上では、平文の個人情報を含む ID を禁止」は、NIST SP 800-63C-4 の原文の該当節を調査ノートで確かめていない。Entra の groups の超過の閾値（200 件）も記憶に基づく。Bearer CLI（Elastic License 2.0 と記憶）、gitleaks（MIT）、trufflehog（AGPL-3.0）、Presidio（MIT）、kcwarden のライセンスは、どれも確かめていない。conftest の `--combine` の現行の挙動、datacontract-cli が PII を検査するか、W3C VC JSON Schema の成熟度、ISO 18013-5 の本文も同じく未確認である。誤検知の見込みもすべて推論で、実データで測った値はない。

## 計画への反映：二つの列を足し、R6 に検査を割り当てる

いまの計画では、スライド 114 の要件が次のように割り当てられている（`templates/trace/requirements.yaml`）。R1（秘密）は `lint:L51` と `pii_category`、R2（機微な属性）は `lint:L50`、R3（平文の ID）は `lint:L52`、R4（変わる識別子）は `lint:L3`。R5（権限の一覧）は `M_authz_pdp` とサイズの `lint:R8`、R6（接続元）は `review:perspectives#q-access-context-from-pep` だけである。**【提案】** 構造上の穴は三つある。第一に、`pii_category` は個人情報保護法の区分なので、パスワードや API キーのような「個人情報ではないが秘密」なものを表せない。そのため、L51 は何を入力に判定するかが決まっていない。第二に、L3 が見る「変わりうる値」を宣言する列がない。`volatility` は値の反映までに許す秒数で、識別子が付け替わるか（reassignable）とは別の軸である。第三に、R6 を機械で検査する手段が一つもない。以下はすべて本報告の提案で、リポジトリの規約（#13）に従い `origin: proposed`、根拠の種類は `author-proposal` として追跡する。規則の番号は仮で、既存の L1〜L67 と重ならないように L68 から付けた。

**#3（台帳）に足す列。** 一つ目は `data_category` で、「何のデータか」を表す。fideslang の data category を版を固定して使い、足りないものは子カテゴリとして拡張する（`user.authorization.credentials.api_key`、`user.unique_id.employee_number`、`authorization.permissions` など。名前は仮）。`pii_category`（法の区分）はそのまま残し、二つの軸を並べる。両者の組み合わせの矛盾、たとえば `user.contact.email` なのに「該当なし」となっている行は、warn で知らせる。二つ目は `identifier_properties: {stable, reassignable, pairwise, id_scheme}` で、`id_scheme` は `opaque`・`pairwise`・`email`・`employee_number` などを取る。`usage` が identifier か authz のクレームでは必須にする。三つ目として、提案中の `allowed_values`（正規表現）と、SD-JWT VC と同名・同義の `path`・`mandatory`・`sd`・`display` を加える。後者の 4 つは、将来 VC に射影するときのための列である。最後に、エディタでの即時検証のため、各 YAML の 2 行目に `# yaml-language-server: $schema=./claims.schema.json` を置く。1 行目は `template_version` と決まっているので、2 行目にする（[yaml-language-server](https://github.com/redhat-developer/yaml-language-server)）。

**#6（lint）の規則の入力を決める。** L51 は、`data_category` が `user.authorization.credentials*` か `user.authorization.password` のクレームが、どのトークン種別に載っても error とする。L52 は、`sub` の `id_scheme` が `email` か `employee_number` なら error とする。FAL の条件を加えるかどうかは、SP 800-63C-4 を確かめてから決める。L3 は、`identifier_properties.stable` が false か、`reassignable` が true のクレームを、identifier や authz に使ったら error とする。さらに、Entra の文書を根拠にした既知の一覧（`email`・`upn`・`preferred_username`・`unique_name`・`phone_number`）は、宣言が stable でも warn にする。そのうえで、次の新しい規則を warn として入れる。semver の規約では error の規則の追加はメジャー版になるので、warn で誤検知の割合を測ってから昇格させる。

| 仮 ID | 内容 | 対応する要件 | 重大度 |
|---|---|---|---|
| L68 | `data_category` が `user.device.*` か `user.location.*` のクレームがトークンに載っていて、PEP で取得しない理由がない。`cnf`（鍵の拇印）は対象外 | `p09-do-not-carry.R6`（今は lint がない） | warn |
| L69 | `usage` が authz の配列クレームに `max_items` がない。または、`allowed_values` か `value_vocabulary` の要素が `resource:action` の形で、上限を超えている | `p09-do-not-carry.R5`（R8 のサイズを補う） | warn |
| L70 | 名前のヒューリスティック：`password|secret|api[_-]?key|client_secret|ip|device_id|dob|birth` などの名前が、宣言した `data_category` と食い違う。`_at`・`_exp`・`_set` で終わる名前は除く | R1・R2・R6 のタグの付け忘れ | warn（error にしない） |
| L71 | 例の値（`examples`）に、メールの形の `sub`、IPv4 の形、gitleaks の既定ルールに当たる文字列がある | R1・R3・R6 | warn |

名前のヒューリスティックを単独で error にしないのは、Semgrep の監査ルールのように、すべての行が人による確認の対象になるのを避けるためである。誤検知の例として、`name` がテナント名を指す場合や、Entra の `ipaddr` のような IdP 標準のクレームがある。規則が出す違反の形式は、Fides にならって、規則 ID、対象のクレームとホップ、根拠の版、抑止の理由を名指しで出すものにする。

**#19（生成）で、生成するスキーマを二つに分ける。** いまの完了基準は、トークン種別ごとのペイロードの JSON Schema を `additionalProperties: true` で生成し、発行側の設定と照合することである。受け手にとって、これは「未知のクレームは無視」と一致するので正しい。しかし、実際に発行したトークンに台帳にないクレーム（`password` や `email` など）が紛れ込んでも、このスキーマは通してしまう。そこで、受け手用（`additionalProperties: true`）に加えて、発行側の適合性を見るスキーマ（`additionalProperties: false`、`sub` には `not: {format: email}`、`allowed_values` から作る `pattern`）を生成する。そのうえで、シナリオ A・B の Keycloak から CI でトークンを発行し、デコードしたペイロードを後者で検証する。この検証は、`lint:L61`（設定に台帳にないクレーム名がある）の静的な照合では見えない、フックやスクリプトによる追加を捉える最後の照合になる。OPA の `io.jwt.decode` は署名を検証しないので（[OPA Token builtins](https://openpolicyagent.org/docs/policy-reference/builtins/tokens)）、検証済みのトークンを入力にするか、テストの目的を内容の検査に限ると明記する。生成物には、IdP の Discovery 用の `claims_supported` の一覧も加えられる。この向きは台帳からメタデータを作るもので、逆向き（メタデータから台帳を作る）は情報が足りず成り立たない。

**claim-lint の外の CI** としては、三つを提案する。IANA の `claims.csv` を取り込む処理を L1a の入力にする。gitleaks を、例示用 JWT の許可リストと合わせて入れる。L10（版の比較）を #21 から MVP に繰り上げるかを検討する。最後の一つは、スライド 133 の「トークンの中身の変更は破壊的変更」を機械で守る唯一の手段である。buf 型のカテゴリ（受け手の検証が壊れる／意味が変わる／説明だけ）で出力させるのがよい。

## 結論

既存のツールは、クレームが「どう署名されたか」と「どのコードが詰めたか」は見ているが、「その情報がトークンに載るべきだったか」は見ていない。スライド 114 の判断は、データの種類・識別子の安定性・トークンが通る場所という三つの宣言の組み合わせでしか下せない。その三つを同じ行に持てるのは、設計の台帳だけである。そのため、claim-lint が再発明を疑われるのは規則のエンジンの部分であって、判定の対象そのものではない。語彙は fideslang から、形は JSON Schema から、比較は oasdiff と buf から借り、新しく作るのは列と規則に絞るのが、最も根拠に沿った分担である。

計画の上で最も効くのは、規則を足すことより、規則の入力になる列を先に決めることである。`pii_category` を一つの列で全部まかなおうとすると、秘密と端末 ID が抜け落ち、L51 と R6 は空回りする。#3 のスキーマを確定させる前に、`data_category` と `identifier_properties` を入れるかどうかを決め、fideslang のライセンスを確かめるべきである。この二つは、後から足すと台帳の全行の書き直しになる。
