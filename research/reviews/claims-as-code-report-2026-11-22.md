# 点検の記録（2026-11-22）：クレーム設計の構造化と機械検査の先行事例の調査の取り込み

`research/claims-as-code/` の `report.md` と `notes/`（3 本）を、作成とは別の LLM のセッションで点検した記録。人による点検は未実施（#20）。

- 作成：2026-11-22（取り込み 2d16674。点検の反映は同じ PR の次のコミット）
- 点検：2026-11-22。Claude（作成とは別のセッション。作成の会話の履歴は引き継いでいない）
- 点検の対象：取り込む前の原稿（`reports/クレーム設計の構造化と機械検査の先行事例.md` と `research_notes/クレーム設計の構造化と機械検査の先行事例/` の 3 本。中身は 2d16674 の `research/claims-as-code/` と同じ）。点検者は読み取りだけで、変更していない
- 渡した資料：上の報告と調査ノート、本リポジトリの `templates/CONTRIBUTING.md`・`templates/trace/requirements.yaml`・`templates/trace/planned_items.yaml`・`.github/workflows/trace.yml`、issue #3・#6・#13・#19・#21 の本文。一次資料は点検者が各項目で当たった（IETF Datatracker の API と draft-ietf-oauth-sd-jwt-vc の txt、openid.net の OpenID4VCI 1.0、IANA の JWT Claims の CSV と XML、Microsoft Learn の Entra の 3 文書と APIM、AWS Verified Permissions、Envoy、Bearer、Datadog、kcwarden、OPA、buf、NIST SP 800-63C-4、gitleaks の `gitleaks.toml`、semgrep-rules の YAML、redhat-developer/yaml-language-server のソースとコミット、ethyca/fides・ethyca/fideslang・IABTechLab/fideslang ほかの GitHub リポジトリと issue（`gh api`）、PyPI の JSON API）
- 渡した指示の要旨：報告の中の事実（仕様の名前・版・日付・フィールド名、ツールの規則名と挙動、ライセンス、リポジトリ内の計画の記述）を一次資料で確かめる。【提案】の中身は対象外だが、提案が前提にしている事実は対象にする。報告が【未検証】とした事項も、確かめられるものは確かめる。区分は誤り・過大・不一致・曖昧。作成者の結論や意図は渡していない
- 点検の原文：作成者のセッションの作業ファイル（非公開）。指摘と決着の内容は、下の表にすべて写した
- 作成者の 1 日以上空けた見直し：未実施（2026-11-23 以降に行い、日付をここに書く）

## 点検した件数

| 対象 | 点検した件数／全件数 |
| --- | --- |
| report.md の事実（範囲内） | 59／66。問題なし 45、指摘あり 14 |
| 報告が【未検証】・未解決とした事項 | 9 件が一次資料で決着（下の「決着した未検証の事項」）。残りは「点検していない 7 件」 |
| 出典の URL | 報告の出典は全件、開けるかと主張を支えるかを確かめた（開けない 3 件は指摘の表にある）。調査ノートの URL は `tools/linkcheck.py` で全件（`research/claims-as-code/linkcheck-2026-11-22.txt`） |
| 根拠の中身の抜き取り | 行っていない（報告の出典は全件を見たため） |

### 点検していない 7 件と理由

| 項目 | 理由・扱い |
| --- | --- |
| ARF の rulebook に機械可読版がない | 否定の主張。現行の ARF には rulebook の一覧を置いた別のリポジトリがあり、再調査が要る。報告で【未検証】と明示した |
| OIDC Discovery の `claims_supported`・RFC 9068・RFC 9728 の扱い | 報告が【未検証】としたまま、点検でも原文を取得していない。報告で【未検証】と明示した |
| OpenAPI に標準の仕組みや共通の `x-jwt-claims` がない | 否定の主張。報告で【未検証】と明示した |
| kcwarden に protocol mapper ごとの監査がない | clients のページには記載がない。`/auditors/mappers/` は 404 で、ほかのページは見ていない。報告で【未検証】と明示した |
| スライド 114 の分類 4 と 6 を検出する既存の規則がない | 否定の主張。報告の表で【未検証】と明示した |
| conftest の `--combine`、datacontract-cli の PII 検査、W3C VC JSON Schema の成熟度、ISO 18013-5 の本文 | 報告が未確認としたまま。ISO 18013-5 は有償の規格。W3C VC JSON Schema だけは、取り込みの際に作成者が仕様のページで Candidate Recommendation Draft（2025-02-04）と確かめた（点検者は確かめていない） |
| 誤検知の見込み | 報告自身が推論と明記しており、実データがない |

## 指摘と直し方

区分：誤り＝必ず直す／過大＝原典より強い言い方／不一致＝成果物の間の食い違い／曖昧＝読み違えやすい。直したのは本 PR の 2 つ目のコミット。

| # | 対象 | 区分 | 指摘 | 直し方 |
| --- | --- | --- | --- | --- |
| 1 | report「既存の検査は…」第 1 段落、notes/linters_and_checks | 誤り | Semgrep `jwt-python-exposed-data` は `pattern-inside: def $FUNC(...,$INPUT,...)` と `jwt.encode($INPUT,...)` の組み合わせで、拾うのは関数の引数をそのまま渡す場合だけ。「リテラル以外のすべて」ではない | 「関数の引数をそのまま `jwt.encode` に渡す箇所を拾う監査ルール（WARNING・confidence LOW）」に直し、規則の YAML へのリンクを足した |
| 2 | report「借りるべき型…」第 2 段落、notes/claims_as_code_design | 誤り | `dataset_references` の issue は ethyca/fides#151 で、2021-10-08 に作られ 2021-10-29 に completed で閉じている。いまの制約ではない。出典の lightrun のページは中身がない | 出典を GitHub の issue #151 に替え、「2021 年に報告され、同月に完了として閉じた」と書いた。教訓は【提案】として残した |
| 3 | report「借りるべき型…」第 3 段落、notes/claims_as_code_design（2 か所） | 誤り | oasdiff の破壊的変更は ERR と WARN の 2 段階。INFO は `changelog` の段階 | 「破壊的変更を ERR と WARN に分け（`changelog` ではさらに INFO も出す）」に直した |
| 4 | report「計画への反映」#3 の段落、notes/claims_as_code_design（2 か所） | 誤り | yaml-language-server はコミット 416ede2（2026-06-26）から、modeline を最初の YAML の内容より前のコメントからしか読まない。1 行目がキー `template_version: 0.1.0` なら、2 行目の modeline は無視される | 一次資料（`yamlParser07.ts` の `getDocumentHeaderComments` とコミット 416ede2）を作成者も確かめた。`templates/CONTRIBUTING.md` の YAML の行を「1 行目にコメント `# template_version: 0.1.0`、modeline は最初のキーより前の先頭のコメントに置く」に直した（#5 も参照）。report とノートの「2 行目に置く」を直した |
| 5 | `templates/CONTRIBUTING.md`「版の管理」の表と `templates/trace/*.yaml` | 不一致 | CONTRIBUTING は YAML の 1 行目をキーとするが、`requirements.yaml`・`planned_items.yaml` の 1 行目はコメント。`tools/trace_check.py` もコメントで書き出す | CONTRIBUTING をコメントの形に揃えた（実ファイルとツールはもとからこの形なので変えていない）。`templates/CHANGELOG.md` に記録した。`tools/tests/test_trace_check.py` に、生成する YAML と `templates/trace/*.yaml` の 1 行目がコメントであることの試験を足した |
| 6 | report「既存の検査は…」gitleaks の段落、notes/linters_and_checks（2 か所） | 過大 | 「例示用の JWT は確実に検出される」。`jwt` 規則はヘッダーとペイロードがそれぞれ `ey` で始まる 17 文字以上と entropy 3 以上を求め、省略した例は当たらない | 「完全な形の例示用 JWT は検出される（省略形は当たらない）」に弱め、許可リストの要否を【提案】として分けた |
| 7 | report「計画への反映」#6 の段落、notes/linters_and_checks | 過大 | Entra を根拠にした既知の一覧の `phone_number` は、Entra の 3 つの文書のどれにも出てこない | 一覧から `phone_number` を外し、入れるなら OIDC Core の標準クレームという別の根拠で書く、と添えた。ノートの一覧からは `name` も同じ理由で外した |
| 8 | report「調査ノート間の食い違い」表の `pii_category` の行 | 曖昧 | #3 の値は法の 4 区分と「該当なし」の 5 値で、法の区分が 5 つあるのではない | 「個人情報保護法の 4 区分（個人情報・要配慮個人情報・個人関連情報・仮名加工情報）と『該当なし』の 5 値」に直した |
| 9 | report「調査ノート間の食い違い」表の「規則のエンジン」の行 | 曖昧 | 日本語のメッセージの要件は #13・#6・#19 のどれの本文にもない。#13 にあるのは抑止の理由の出力だけ | 「抑止の理由を出力する要件（#13 の完了の定義『行ごとの理由が lint の出力に出る』）」に絞った |
| 10 | report「借りるべき型…」第 3 段落（Azure）、notes/claims_as_code_design | 曖昧 | 「AutoRest は 2026-07-01 に退役する」は、調査基準日より前の日付なので未来形が紛らわしい | report は「2026-07-01 に退役した（README の予告による）」に、ノートは退役の日を過ぎていることを添えた |
| 11 | report「標準が定めるのは…」第 2 段落の Tetrate のリンク、notes/structured_formats（2 か所） | 曖昧 | 1.5.x の URL は 404。版のない URL で `x-tsb-authorization` と `JWTClaims` を確かめられる | 版のない URL に替え、確かめた日（2026-11-22）を書いた |
| 12 | report「標準が定めるのは…」第 2 段落の AWS のリンク、notes/structured_formats（2 か所） | 曖昧 | `identity-sources_map-token-to-schema.html` は概要のページに転送され、`context.token.<属性>` は OIDC 用のページにある | 出典を `oidc-map-token-to-schema.html` に替え、本文を `context.token.<属性>` にした |
| 13 | report「既存の検査は…」の Semgrep のリンクと表の 1 行目、notes/linters_and_checks | 曖昧 | `registry.semgrep.dev/rule/...` の URL はどちらも 404。`semgrep.dev/r/<規則 ID>` は 200 | リンクを `semgrep.dev/r/...` と GitHub の YAML に替えた。ノートの Ruby 版・njsscan 版のリンクも同じ形に替えた |
| 14 | report「借りるべき型…」第 1 段落（Fides） | 曖昧 | ethyca/fides のリポジトリは archived（最後の push は 2026-08-06、最新のリリースは 2.86.2〔2026-06-01〕）。fideslang は archived ではない | 「ethyca/fides のリポジトリは 2026 年に archived」と添え、借りるのは構成の考え方だけと書いた。ノートにも 1 行足した |

### 軽微な指摘（区分は曖昧）

| 対象 | 指摘 | 直し方 |
| --- | --- | --- |
| report §5.6 の `display` | `dir`（任意）もある | 足した |
| report「Consumers MUST ignore…」 | §5.6 ではなく §5.2 の文 | 「Type Metadata の形式（§5.2）で」と直した |
| report・notes/structured_formats の ARF | 引いたのは 1.3.0、現行は v3.0.0。定義の文は同じ | 1.3.0 の URL は 404 なので、v3.0.0 の URL に替え、そのことを書いた |
| report の見出しの「4 つ」と本文の「5 つ」 | `svg_id` を数えない理由がない | 「`svg_id` は描画用の参照なので、台帳の列として数えるのは 4 つ」と添えた |
| notes/linters_and_checks の Google DLP | 「`JSON_WEB_TOKEN` という infoType は確認できなかった」は誤り。Secrets の節にある（"JSON Web Token in compact form"、SENSITIVITY_HIGH） | ノートを直し、スライド 118 向けの検査の候補と書いた。表の行にも足した |
| notes/linters_and_checks の fideslang のライセンス | 「Apache-2.0 と記憶」は誤り | CC BY 4.0 に直した（下の表） |

## 決着した未検証の事項

報告が【未検証】または「未解決」とした事項のうち、点検者が一次資料で決着させたもの。本文の印を【確認済】に変えた。

| 事項 | 結果 | 反映 |
| --- | --- | --- |
| fideslang のライセンス | ethyca/fideslang と IABTechLab/fideslang は、どちらも CC BY 4.0（GitHub の判定と README のバッジ）。Python のパッケージを別のライセンスにする LICENSE ファイルはない | report の表と本文、ノートを直した。CC0 の `templates/` に語彙を写すと表示の義務が混じるので、写さずに版を固定して参照する、と report の表・#3 の段落・結論に書いた |
| fideslang の分類群の数 | 現行の README は「three classification groups」 | report の表を直した |
| Semgrep `jwt-exposed-credentials` | `jwt-python-exposed-credentials` は semgrep-rules に残っている。ERROR、audit。`"password"` というキーのリテラルだけを検出する | report の表の 1 行目とノートを直した |
| NIST SP 800-63C-4 の FAL2 | "At FAL2, federated identifiers SHALL NOT contain plaintext personal information, such as usernames, email addresses, employee numbers, etc."。FAL1 では SHOULD NOT | report に原文を引き、L52 の段落を「FAL1 では warn に下げる条件を加えられる」にした。ノートを直した |
| Entra の groups の超過の閾値 | JWT は 200、SAML は 150 | report とノートを直した |
| Bearer CLI のライセンス | Elastic License 2.0（LICENSE ファイル。GitHub の判定は NOASSERTION） | report とノートを直した |
| gitleaks・trufflehog | MIT・AGPL-3.0 | 同上 |
| Presidio | MIT。`data-privacy-stack/presidio` に移った | 同上 |
| kcwarden | Apache-2.0 | 同上 |

## 取り込みで足した直し（点検の指摘の外）

- 非公式な情報源（フォーラム・個人ブログ・第三者の要約や転載）へのリンクに「（非公式）」を付けた（report の凡例に定義を足した）。対象：Nordic APIs、mataroa、Keycloak forum、dev.to、Practical365、TechTarget、tessl、oneuptime、helpfulbadger、self-issued.info、office365itpros
- `tools/linkcheck.py` で `research/claims-as-code/` の全リンクを点検した（`linkcheck-2026-11-22.txt`）。404 のリンクは公式の代わりに替えるか（IAB Tech Lab の寄贈の告知、ARF v3.0.0、keycloak-config-cli の文書、keycloak-provisioner の GitHub、OPA の Policy Testing、SmartBear の文書）、代わりがなければリンクを外して 404 と書いた（dev.to の記事、APTITUDE の rulebook のテンプレート、German PID rulebook の個別ページ、42Crunch の 2 ページ、Ethyca の「Annotating data categories」）。スクリプトを拒むサイト（npm、office365itpros、Business Wire、W3C）は別の手段で確かめ、`linkcheck-manual-2026-11-22.tsv` に証拠を書いた
- `tools/linkcheck.py` の出力の見出しが `research/template-design/` に固定されていたので、引数のディレクトリを書くように直した
