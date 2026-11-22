# 不適切なクレーム定義・トークン内容を検出する既存の linter・静的解析・CI チェック（スライド 114 の分類に照らした棚卸し）

調査日: 2026-11-22。対象スライド: docs/slides.json の 113〜118（特に 114「載せない情報：秘密・機微な属性・変わる識別子」）。
凡例: 「Cited Findings」は出典を確認できた事実。「Inferences」は筆者の推論。ライセンスや保守状況のうち、今回の調査で出典に当たれなかったものは Gaps に入れ、「学習知識・未検証」と明記した。

前提（スライド 114 の 6 分類。リポジトリ内の docs/slides.json n=114 から転記）:
1. 認証の秘密（パスワード、API キー）: アサーションに含めてはならない
2. 機微な属性（氏名・住所・生年月日）: identity API・UserInfo で取得する
3. 平文の個人情報を含む ID（メールや社員番号を sub に）: FAL2 以上では禁止（スライドの主張。根拠は NIST SP 800-63C-4。2026-11-22 の点検で原文を確かめた：FAL2 の節に "At FAL2, federated identifiers SHALL NOT contain plaintext personal information, such as usernames, email addresses, employee numbers, etc."、FAL1 では SHOULD NOT — [NIST SP 800-63C-4](https://pages.nist.gov/800-63-4/sp800-63c.html)）
4. 変わりうる識別子（email、upn）: oid＋tid、または iss＋sub を使う
5. 細かい権限の一覧（エンドポイントごとの許可）: PDP に問い合わせる
6. 接続元の詳細（IP、端末の識別子）: PEP でその都度取得する

---

## Q1. JWT/OAuth に特化したツールは何を検出できるか（Semgrep、Bearer、jwt_tool、ZAP、Burp、42Crunch、Spectral OWASP、IdP 設定スキャナ、IaC スキャナ、Entra）

### Takeaway
JWT 専用ツールの大半は**署名と検証の実装の欠陥**（alg=none、鍵混同、JWK 注入、exp の欠落）を狙っている。**ペイロードの中身の妥当性**を見るものは、(a) コード上の `jwt.sign/encode` の引数を見る SAST ルール（Semgrep、Bearer、Datadog）と、(b) Keycloak の設定監査 kcwarden の「full scope allowed（全ロールがトークンに載る）」程度に限られる。スライド 114 の 6 分類を宣言（レジストリ）の段階で検査するツールは見つからなかった。

### Cited Findings
**SAST（コード上の JWT 生成箇所）**
- Semgrep Registry の `python.jwt.security.audit.jwt-exposed-data`（WARNING、confidence LOW）は、囲んでいる関数の引数をそのまま `jwt.encode(...)` に渡す箇所（`pattern-inside: def $FUNC(...,$INPUT,...)` と `jwt.encode($INPUT,...)` の組み合わせ）を拾い、機微データが入っていないかの確認を求める監査ルール。取り込んだ版の「リテラル以外のオブジェクトをすべて拾う」は誤り（2026-11-22 の点検で訂正）。Ruby 版（`ruby-jwt-exposed-data`）と njsscan 由来の JS 版（`jwt_exposed_data`）もある（中身は点検していない） — [Semgrep python jwt-exposed-data](https://semgrep.dev/r/python.jwt.security.audit.jwt-exposed-data.jwt-python-exposed-data)、[規則の YAML](https://github.com/semgrep/semgrep-rules/blob/develop/python/jwt/security/audit/jwt-exposed-data.yaml), [Ruby](https://semgrep.dev/r/ruby.jwt.security.audit.jwt-exposed-data.ruby-jwt-exposed-data), [njsscan](https://semgrep.dev/r/ajinabraham.njsscan.jwt.jwt_exposed_data.jwt_exposed_data)（`registry.semgrep.dev/rule/…` の URL はいま 404 なので、`semgrep.dev/r/…` に替えた）
- Semgrep の `python.jwt.security.jwt-exposed-credentials`（ERROR、subcategory は audit）は、`jwt.encode` に渡す dict に `"password"` というキーのリテラルがあると検出する。規則は semgrep-rules に残っている（2026-11-22 の点検で確認。取り込んだ版は registry の個別ページが 404 なので未確認としていた） — [Semgrep](https://semgrep.dev/r/python.jwt.security.jwt-exposed-credentials.jwt-python-exposed-credentials)、[規則の YAML](https://github.com/semgrep/semgrep-rules/blob/develop/python/jwt/security/jwt-exposed-credentials.yaml)
- Semgrep 公式ブログ（2020）: オブジェクトを要素に分けずにそのまま JWT にすると、中身を管理できなくなりやすいと指摘している — [Semgrep blog](https://semgrep.dev/blog/2020/hardcoded-secrets-unverified-tokens-and-other-common-jwt-mistakes)
- Bearer CLI の `javascript_lang_jwt` は JWT に入れた機微データを検出する。CWE-312、OWASP A04:2021。危険な例は `jwt.sign({ user: { email: 'john@gmail.com' }})`、安全な例は `jwt.sign({ user: user.uuid })`。PHP・Ruby 版もある — [Bearer javascript_lang_jwt](https://docs.bearer.com/reference/rules/javascript_lang_jwt), [php_lang_jwt](https://docs.bearer.com/reference/rules/php_lang_jwt), [ruby_lang_jwt](https://docs.bearer.com/reference/rules/ruby_lang_jwt/)
- Bearer の検出は独自のデータ種別分類（122 種。PD、Sensitive PD、PII、PHI）に依存する（検索結果の要約。一覧ページは未取得） — [Bearer Supported Data Types](https://docs.bearer.com/reference/datatypes)
- Bearer は 2024 年に Cycode に買収された（2024-04-30 に完了）。Bearer CLI は Cygives の枠組みでオープンソースとして提供が続いている — [TechCrunch](https://techcrunch.com/2024/03/05/cycode-acquires-bearer-to-accelerate-its-move-into-ai-enhanced-security-remediation/amp/), [DBTA](https://www.dbta.com/Editorial/News-Flashes/Cycode-Acquires-Bearer-and-Launches-New-Cygives-Developer-Initiative-163832.aspx)
- Datadog Static Analysis の `javascript-node-security/jwt-sensitive-data`（CWE-312）は `jwt.sign({user: {email: ...}})` のような呼び出しを検出する（検索結果の要約） — [Datadog rule](https://docs.datadoghq.com/security/code_security/static_analysis/static_analysis_rules/javascript-node-security/jwt-sensitive-data/)

**動的テスト（ペネトレーション）**
- jwt_tool（ticarpi）: alg 混同、署名なしトークン、弱い署名鍵、JWKS 周りの既知の脆弱性を調べる。Playbook Scan で対象アプリの設定不備を探す — [jwt_tool README](https://raw.githubusercontent.com/ticarpi/jwt_tool/master/README.md)
- ZAP JWT Support add-on: サーバー側の検査は None アルゴリズム、アルゴリズム混同、トークンに添付された JWK の信頼、空の JWT、ヌルバイト注入。クライアント側は、JWT をブラウザに安全でない形で送っていないかなど。ペイロード内の PII や機微データの検査については記載がない — [ZAP blog 2020](https://www.zaproxy.org/blog/2020-09-03-zap-jwt-scanner/)
- Burp: JWT Scanner（BApp）は署名の欠落・不正、期限切れや期限なしの JWT、CVE-2022-21449、JWK 注入を調べる。JWT Editor は手作業でトークンを書き換え・署名する道具で、自動スキャナではない — [PortSwigger JWT Scanner](https://github.com/PortSwigger/jwt-scanner), [JWT Editor](https://github.com/portswigger/jwt-editor)

**OpenAPI lint・監査**
- Spectral OWASP ruleset v2 の `owasp:api2:2023-jwt-best-practices` は、type が oauth2 または bearerFormat が JWT の securityScheme を対象にし、その description が RFC 8725 に言及していることを要求する。v1（2019）は RFC 7519 への言及を要求していた。同じ系統のルールに `no-api-keys-in-url`、`no-credentials-in-url`、`auth-insecure-schemes` がある — [ruleset.ts（unpkg）](https://app.unpkg.com/@stoplight/spectral-owasp-ruleset@2.0.1/files/src/ruleset.ts), [CHANGELOG](https://app.unpkg.com/@stoplight/spectral-owasp-ruleset@2.0.1/files/CHANGELOG.md), [SwaggerHub docs](https://support.smartbear.com/swagger/docs/studio/api-governance/owasp-top-10/)（取り込んだ版の app.swaggerhub.com の URL は 404 なので、SmartBear の現行の文書に替えた。中身は点検していない）
- 42Crunch: OpenAPI の拡張を使って JWT 攻撃を防ぐ、200 以上のベストプラクティス検査を行う、と説明している。JWT 固有の検査項目の一覧は見つからなかった — [スライド PDF](https://info.42crunch.com/hubfs/slidedeck/webinar-how-to-best-leverage-jwt-for-api-security.pdf)（取り込んだ版が併記した webinar のページと「7 ways to avoid JWT pitfalls」は 404。2026-11-22 のリンクの点検）

**IdP 設定スキャナ**
- kcwarden（iteratec、Keycloak 監査）のクライアント監査は 30 種。例: `ClientShouldDisableImplicitGrantFlow`、`PublicClientsMustEnforcePKCE`、`ClientAccessTokenLifespanTooLong`、`ClientWithFullScopeAllowed`（全ロールがトークンに入る）、`UsingNonDefaultUserAttributesInClientsWithoutUserProfilesFeatureIsDangerous`（利用者が自分で書き換えられる属性をクレームに使う危険）。protocol mapper ごとに機微な属性を検査する監査は記載されていない — [kcwarden client auditors](https://iteratec.github.io/kcwarden/auditors/clients), [realm auditors](https://iteratec.github.io/kcwarden/auditors/realm)
- Mondoo cnspec には Auth0 用の検査がある（セッション寿命の上限、implicit grant を使うアプリがないこと） — [Mondoo cnspec Auth0](https://mondoo.com/docs/cnspec/identity/auth0)

**Entra ID**
- Microsoft の optional claims リファレンス: `upn` は永続的な識別子ではなく、認可に使ってはならない。`email` と `upn` は時間とともに変わりうる。DB のキーには `oid` を使う — [Entra optional claims reference](https://learn.microsoft.com/en-us/entra/identity-platform/optional-claims-reference)
- Microsoft の移行ガイド: email クレームで利用者を識別・認可する実装をやめ、マルチテナントでは `tid`＋`oid` で索引する。`xms_edov` はメールのドメイン所有者が検証済みかを示す Boolean — [Migrate away from using email claims](https://learn.microsoft.com/en-nz/entra/identity-platform/migrate-off-email-claim-authorization)

### Inferences
- スライド 114 の分類との対応: 分類 1（秘密）は Semgrep の `jwt-exposed-credentials` が直接扱う。分類 2・3（機微な属性、メールを ID に使う）は Bearer と Datadog の JWT ルールが部分的に扱う。分類 5（権限一覧の肥大）は kcwarden の `ClientWithFullScopeAllowed` が設定の段階で間接的に扱う。分類 4（変わる識別子）と分類 6（IP・端末 ID）を直接検出する既存ルールは見つからなかった。
- これらの SAST ルールの入力は**アプリのソースコード**で、claims.yaml にはそのまま向けられない。それでも、プロジェクトが「IdP の外で自前に JWT を発行するコード」も持つなら、claim-lint と並べて CI に入れる価値がある。claims.yaml とコード上の `jwt.sign` の引数が食い違っていないかを照合する（ドリフト検出）という使い方が考えられる。
- 「Semgrep の監査ルールは encode の呼び出しをすべて拾う」という設計から見て、誤検知は多いと見込まれる（すべての発行箇所が人手の確認対象になる）。Bearer・Datadog は「データ種別を推定した結果、email らしい」場合に絞るので、誤検知は相対的に少ないはずだが、名前から推定する限界は残る（推論）。
- Spectral の JWT ルールは「説明文が RFC 8725 に言及しているか」という形式の検査にすぎず、クレームの中身は見ない。ただし Spectral は任意の JSON/YAML を対象に独自ルールを書ける（学習知識・未検証）。claim-lint の宣言的なルールを Spectral の独自ルールセットとして書く選択肢はある。
- kcwarden の「Keycloak の設定 JSON を監査する」方式は、claims.yaml を IdP の設定（protocol mapper、optional claims）から生成または照合するときの参考になる。

### Gaps
- 42Crunch Audit の JWT・OAuth 検査の具体的な ID（「JWT を使っているのに RFC 8725 に従っていない」など）は、公開ドキュメントを見つけられなかった。
- Checkov、tfsec（Trivy）、KICS に、Keycloak・Auth0・Okta・Entra の Terraform リソース（token lifetime、implicit grant、optional claims）向けの組み込みルールがあるかは、検索では確認できなかった。各カタログの直接確認が要る。
- IdP の CIS Benchmark（Okta、Entra）は今回調べられなかった。Entra のアプリ登録で optional claims や groups クレームを評価する公式の評価ツール（Secure Score など）の有無も未確認。
- kcwarden の入力形式（realm export JSON か API か）は取得したページに記載がなかった。ライセンスは Apache-2.0（2026-11-22 の点検で確認 — [iteratec/kcwarden](https://github.com/iteratec/kcwarden)）。
- Semgrep Registry のルールのライセンス（Semgrep Rules License）は学習知識で未検証。Bearer CLI のライセンスは Elastic License 2.0（LICENSE ファイルの冒頭。GitHub の判定は NOASSERTION。2026-11-22 の点検で確認 — [Bearer/bearer](https://github.com/Bearer/bearer)）。
- jwt_tool と ZAP JWT add-on の現在の保守状況は未確認（ZAP のページ自体に「内容が古い可能性がある」と注記がある）。

---

## Q2. Privacy-as-code・機微データの静的解析はどう分類しているか（Fides/fideslang、Privado、Bearer、Presidio、Google DLP、data contract、dbt）

### Takeaway
**claims.yaml にそのまま流用できる最有力候補は fideslang の data category 分類体系**。階層構造のキー（`user.contact.email`、`user.device.ip_address`、`user.authorization.credentials` など）をクレームの必須タグにすれば、スライド 114 の分類 1・2・6 を宣言だけで判定できる。Presidio と Google DLP は**値のサンプル**を走査する仕組みで、トークンの例やテスト用フィクスチャの検査に向く。

### Cited Findings
- fideslang の data category は階層構造で、上位の `user.contact` でも詳細な `user.contact.email` でも分類できる。GDPR、CCPA、LGPD、ISO 19944 への対応を想定して設計されている。IAB Tech Lab に寄贈された — [fideslang taxonomy overview](https://ethyca.github.io/fideslang/taxonomy/overview), [IAB Tech Lab の寄贈の告知（2024-01-09）](https://iabtechlab.com/iab-tech-lab-accelerates-privacy-taxonomy-project-with-fides-language-product-donation)（取り込んだ版が引いた Ethyca のブログは 404）, [IAB Tech Lab 版](https://iabtechlab.github.io/fideslang)
- fideslang でスライド 114 に関係するキー（公式 taxonomy ページから取得）:
  - 認証の秘密: `user.authorization.credentials`、`user.authorization.password`
  - 機微な属性: `user.name`（`.first`、`.last`）、`user.contact.address.*`、`user.demographic.date_of_birth`、`user.contact.phone_number`、`user.government_id.*`、`user.demographic.race_ethnicity`、`user.demographic.religious_belief`、`user.health_and_medical.*`、`user.biometric.*`
  - メール: `user.contact.email`
  - 接続元: `user.device.ip_address`、`user.device.device_id`、`user.device.cookie_id`、`user.location.precise`、`user.location.imprecise`
  - 識別子: `user.unique_id.pseudonymous`、`user.account.username`
  - 該当なし: API キー専用、社員番号専用、アカウント ID 専用のキーはない（近いのは `user.workplace`、`user.job_title`）。既存の親の下に子カテゴリを足して拡張することが推奨されている — [fideslang data categories](https://ethyca.github.io/fideslang/taxonomy/data_categories/)
- Fides は Dataset の YAML でフィールドごとに `data_categories` を付ける（例: `collections: - name: customer fields: - name: email data_categories: [user.contact.email]`） — [Fides data mapping annotations](https://ethyca.com/docs/data-mapping/guides/data-mapping-annotations)（取り込んだ版が併記した「Annotating data categories」のページは 404）
- Privado: 静的なコード解析で、収集点からシンク（出口）までのデータフローを描き、110 種以上の個人データ要素を検出する。結果は `.privado/privado.json` に出力される。v1 のリポジトリ（privado-datasafety）はアーカイブ済みで、v2 のエンジンは Privado Core として公開されている — [Privado GitHub](https://github.com/privado-inc/privado), [privado-datasafety（アーカイブ）](https://www.github.com/Privado-Inc/privado-datasafety), [Privado docs](https://docs.privado.ai/getting-started-with-privado/understanding-the-results)
- Presidio Analyzer: 組み込みの認識器は 50 以上。主な汎用エンティティと検出方式は、EMAIL_ADDRESS（パターン＋文脈＋RFC-822 検証）、IP_ADDRESS（パターン＋文脈）、MAC_ADDRESS、PERSON と LOCATION（独自ロジック＋文脈。NER を使う）、PHONE_NUMBER、DATE_TIME、URL、UUID（バージョンと variant を検証）、CREDIT_CARD（チェックサム）。日本固有のエンティティの節はない。ドキュメントは microsoft.github.io から presidio.dataprivacystack.org（Data Privacy Stack）に移っている — [Presidio supported entities](https://presidio.dataprivacystack.org/supported_entities/), [tessl の要約](https://tessl.io/registry/tessl/pypi-presidio-analyzer/2.2.0/files/docs/predefined-recognizers.md)（非公式）
- Google Sensitive Data Protection（DLP）には infoType `AUTH_TOKEN` がある。OAuth や Bearer 認証の形式に従うトークンを検出する。あわせて、Secrets の節に `JSON_WEB_TOKEN`（"JSON Web Token in compact form"、SENSITIVITY_HIGH）がある。取り込んだ版の「`JSON_WEB_TOKEN` という infoType は確認できなかった」は誤り（2026-11-22 の点検で訂正）。スライド 118 向けの検査（ログに JWT が出ていないか）の候補になる — [infoTypes reference（high sensitivity）](https://docs.cloud.google.com/sensitive-data-protection/docs/high-sensitivity-infotypes-reference)
- Data Contract Specification には、フィールドが個人データかを示す属性と、分類（sensitive、restricted、internal、public など）の属性がある。datacontract-cli の `lint` は書式の検証として説明されており、PII の検査をするかは確認できなかった — [datacontract-cli（PyPI）](https://pypi.org/project/datacontract-cli), [Data Contract Specification](https://docsearch.algolia.com/mcp/docs/repo/datacontract/datacontract-specification)
- 参考（別プロジェクト）: obs-types は分類の enum に基づく lint を持つ。L002「PII は LABEL に置かない」、L003「SECRET は LOG・AUDIT 層に置かない」。claim-lint の L65（機密度と可視性）と同じ「分類 × 出る場所」の型の先例 — [obs-types classification.rs](https://docs.rs/obs-types/0.1.0/src/obs_types/classification.rs.html)

### Inferences
- 分類の手法は 4 つに分かれる。(1) **宣言による分類**（fideslang、Data Contract の classification）。人が付けたタグを信じる。(2) **名前と型からの推定**（Bearer、Privado）。変数名やフィールド名からデータ種別を推定する。(3) **値のパターン**（Presidio、DLP、gitleaks）。正規表現、チェックサム、検証器を使う。(4) **ML/NER**（Presidio の PERSON・LOCATION）。claims.yaml は宣言の層なので、(1) を本体にし、(2) を「タグの付け忘れ」を拾う補助に、(3)(4) をサンプルトークンの検査に使う、という三段構えが自然。
- fideslang を流用する場合、JWT 固有の概念（「変わりうる」「ペアワイズ」「権限」）は分類体系にない。`data_category`（何のデータか）とは別に、`identifier: {stable: bool, pairwise: bool, reassignable: bool}`、`visibility`、`confidentiality` のような軸を claims.yaml 独自に持つ必要がある。fideslang は「何のデータか」の語彙として借りるのが適切（推論）。
- 社員番号と API キーは fideslang にない。`user.unique_id.employee_number`（名前は仮）、`user.authorization.credentials.api_key`（同）のように子カテゴリを足すのが公式に推奨されている方法に沿う。
- Presidio は日本語の氏名・住所の NER について保証がない（日本固有のエンティティの節がない）。日本語の値を走査するなら独自の認識器（社員番号の書式、郵便番号、都道府県名の辞書など）が必要と見込まれる。

### Gaps
- fideslang のライセンスは CC BY 4.0（ethyca/fideslang と IABTechLab/fideslang の両方。GitHub のライセンスの判定と README のバッジ。Python のパッケージを別のライセンスにする LICENSE ファイルはない）。取り込んだ版の「Apache-2.0 と記憶」は誤り（2026-11-22 の点検で訂正）。語彙を CC0 の `templates/` に写すと表示の義務が生じるので、写さずに版を固定して参照する。IAB Tech Lab への寄贈後の保守体制・リリースの頻度は未確認。
- 「fides の CI 検査」（`fides evaluate` で Policy に照らして Dataset を評価する仕組み）の現在の仕様は今回取得できなかった（学習知識では、data category × data use × data subject の組み合わせを拒否するポリシーを CI で評価できる）。
- Bearer の 122 データ種別の一覧と、名前から推定するロジックの詳細は未取得。
- Presidio のライセンスは MIT。`microsoft/presidio` は `data-privacy-stack/presidio` に移っている（2026-11-22 の点検で確認 — [data-privacy-stack/presidio](https://github.com/data-privacy-stack/presidio)）。移管の経緯（「Project transition update」ページ）は未確認。
- dbt meta タグや data catalog（DataHub、OpenMetadata）の PII 自動タグ付けは今回調べられなかった。

---

## Q3. シークレットスキャン（gitleaks、trufflehog）はトークンのサンプルや設定にどう効くか。ログに出たトークンの検出

### Takeaway
gitleaks の既定ルールには `jwt`（ヘッダーとペイロードがそれぞれ `ey` で始まる 17 文字以上、entropy 3 以上）と `jwt-base64`（JWT 全体をさらに Base64 にしたもの）がある。リポジトリ内の**トークン実物の混入**は検出できるが、ペイロードを復号して中身を判定する仕組みはない。ドキュメントやテスト用フィクスチャに置く完全な形のサンプル JWT は引っかかる（`eyJhbGciOi...` のような省略形は当たらない）ので、許可リスト（allowlist）の運用設計が要る。

### Cited Findings
- gitleaks 既定設定のルール `jwt`: 説明は「Uncovered a JSON Web Token…」、正規表現は `\b(ey[a-zA-Z0-9]{17,}\.ey[a-zA-Z0-9\/\\_-]{17,}\.` で始まり署名部は省略可、keywords は `["ey"]`、entropy は 3 — [gitleaks config/gitleaks.toml](https://raw.githubusercontent.com/gitleaks/gitleaks/master/config/gitleaks.toml)
- ルール `jwt-base64`: `\bZXlK` で始まり、ヘッダーのパラメータ名（alg、aud、crit など）を Base64 にした接頭辞を名前付きグループで列挙する。keywords は `["zxlk"]`、entropy は 2 — [同上](https://raw.githubusercontent.com/gitleaks/gitleaks/master/config/gitleaks.toml)
- gitleaks のルールは Go の正規表現で、keywords で事前に絞り込み、`useDefault` で既定設定を拡張できる。ルールの中で Base64 を復号する仕組みは、検索した資料には出てこなかった — [gitleaks README](https://github.com/gitleaks/gitleaks/blob/e55d3975ec6989fae76f28f5034ca88a7891fd94/README.md)
- Google DLP の `AUTH_TOKEN` は OAuth・Bearer 形式のトークンを検出し、ログ基盤の走査に使える — [DLP infoTypes](https://docs.cloud.google.com/sensitive-data-protection/docs/high-sensitivity-infotypes-reference)
- Bearer には JWT の署名鍵の直書きを検出する `javascript_lang_jwt_hardcoded_secret` がある — [Bearer rule](https://docs.bearer.com/reference/rules/javascript_lang_jwt_hardcoded_secret)

### Inferences
- claim-lint の補助として使える方法: gitleaks の `jwt` ルールで見つかった文字列を後段のスクリプトで Base64URL 復号し、ペイロードのキーを claims.yaml と突き合わせる（未登録のクレーム、`password`、`api_key`、`email` を sub に使うなど）。gitleaks にはこの機能がないので自作になる（推論）。
- スライド 118（ログにトークン全文を残さない）に対しては、gitleaks の `jwt` 正規表現か DLP の `AUTH_TOKEN` をログのサンプルや OpenTelemetry の span 属性に当てる検査が、そのまま流用できる。
- 誤検知: このガイド自体のスライドや docs にある例示用 JWT のうち、完全な形のものは検出される。`.gitleaksignore` か、例示トークンの署名部を明らかなダミーにする規約が必要。`eyJhbGciOiJSUzI1NiIs…` のように「…」で省略したものは、ヘッダーとペイロードの両方を求める正規表現に当たらない（2026-11-22 の点検で、取り込んだ版の「確実に検出される」を弱めた）。

### Gaps
- trufflehog の JWT 検出器の有無と、検証（生きているトークンかの確認）の挙動は今回確認できなかった（trufflehog のライセンスは AGPL-3.0、gitleaks は MIT。2026-11-22 の点検で GitHub のライセンスの判定を確かめた）。
- gitleaks のライセンス（MIT と記憶）は未検証。
- ログ中のトークン検出の専用ツール（Datadog Sensitive Data Scanner、Splunk など）の具体的なルールは調べていない。

---

## Q4. 実行時・テスト時の検査（発行されたトークンを CI で復号してクレームの方針を表明する仕組み）

### Takeaway
専用の「発行済み JWT のクレーム方針チェッカー」は見つからなかった。最も現実的な組み合わせは **OPA/Rego（`io.jwt.decode` か `io.jwt.decode_verify`）＋ conftest または `opa test`**。テスト用 IdP（Keycloak のコンテナなど）から発行したトークンをデコードし、claims.yaml から生成した許可リストやルールで判定する。

### Cited Findings
- OPA の組み込み関数 `io.jwt.decode` は Base64 の復号だけで署名を検証しない。検証には `io.jwt.verify_*` か `io.jwt.decode_verify()` を使う — [OPA Token builtins](https://openpolicyagent.org/docs/policy-reference/builtins/tokens)
- OPA のテストは `test_` で始まる規則を `opa test` で走らせ、`with` キーワードで `io.jwt.decode_verify` をモックにできる。`opa test` は JSON 出力を持つ — [OPA: Policy Testing](https://www.openpolicyagent.org/docs/policy-testing)（取り込んだ版が引いた tessl の要約は 404 なので、公式の文書に替えた）
- conftest は CI の関門として使え、`--output json` で結果を出せる。通る入力と落ちる入力の両方で方針を試すことが推奨されている — [oneuptime: OPA conftest policy testing](https://oneuptime.com/blog/post/2026-01-28-opa-conftest-policy-testing/view)（非公式）
- 実例（Diamond Light Source）: `io.jwt.decode` でヘッダーの kid を読み、JWKS から鍵を引き、`decode_verify` で iss と aud を検証してからクレームを取り出す — [DLS authz how-to](https://diamondlightsource.github.io/authz/how-tos/verify-cas-access-token)
- Envoy＋OPA で JWS を検証する手順の解説がある — [helpfulbadger blog](https://helpfulbadger.github.io/blog/envoy_opa_5_opa_jws)（非公式）

### Inferences
- 構成案: (1) CI で IdP（Keycloak の realm export を読み込んだコンテナ）を起動する → (2) テスト用の利用者でトークンを取得する → (3) ペイロードを JSON にして conftest に渡す → (4) Rego で「claims.yaml に無いクレームがある」「`sensitivity: secret` のクレームがある」「`sub` が email の形をしている」「`visibility: browser` のトークンに `pii: true` のクレームがある」を deny にする。claims.yaml を `data.json` として conftest に渡せば、ルールをハードコードせずに済む。
- Pact などの契約テストでも「消費側が受け取るクレーム」を固定できる。ただし、Pact が JWT の中身を契約の対象として扱う公式の仕組みは見つけられなかった。
- JSON Schema（`additionalProperties: false`、`sub` の `pattern` 否定、`not: {format: email}`）を claims.yaml から生成して、デコード後のペイロードを検証する方法も単純で効果がある。

### Gaps
- Pact の claims の契約テスト、JWT 専用の JSON Schema 検証ツールについて、信頼できる出典は見つからなかった。
- 「発行されたトークンの中身が方針に沿うかを CI で検査する」既存 OSS（例: OIDC conformance suite のクレーム検査）は今回調べられなかった。OpenID Foundation の conformance suite は仕様への準拠を見るもので、データ最小化は見ないと思われる（推論）。

---

## Q5. 各ツールの評価（検出内容、入力、誤検知、ライセンス、保守状況、claims.yaml への適用可否）と、スライド 114 の各分類に対する具体的な検出戦略

### Takeaway
claims.yaml に**直接**向けられるのは、(1) fideslang の分類語彙の流用、(2) JSON Schema、(3) Spectral の独自ルール、(4) OPA/conftest の 4 つ。claim-lint は「宣言的なタグの必須化」を主軸にし、名前のヒューリスティックは**タグとの不一致の警告**に限って使うと誤検知を抑えられる。

### Cited Findings（ツール比較表。各セルの事実は Q1〜Q4 の出典による。「未検証」は学習知識）
| ツール | 検出するもの | 入力 | 114 の分類 | claims.yaml に向けられるか | ライセンス・保守 |
|---|---|---|---|---|---|
| Semgrep JWT ルール | encode に渡すオブジェクト、password キー | ソースコード | 1（2 は監査のみ） | 不可（コード用） | 未検証 |
| Bearer CLI `*_lang_jwt` | JWT に入れたメールなどの機微データ | ソースコード | 2、3 | 不可 | Cycode が買収（2024）。ライセンスは未検証 |
| Datadog jwt-sensitive-data | jwt.sign に渡したメール | ソースコード | 2、3 | 不可 | 商用 |
| jwt_tool、ZAP、Burp JWT Scanner | 署名・検証の欠陥 | 実際のトークンと対象システム | 対象外 | 不可 | 保守状況は未確認 |
| Spectral OWASP | securityScheme の説明が RFC 8725 に言及しているか | OpenAPI | 対象外 | 独自ルールなら可 | npm パッケージ |
| 42Crunch | OpenAPI の監査（200 以上の検査） | OpenAPI | 不明 | 不可 | 商用 |
| kcwarden | implicit、PKCE、full scope、token lifespan | Keycloak の設定 | 5（間接） | 発想を借りられる | 未確認 |
| fideslang | 分類語彙 | YAML | 1、2、6（宣言） | 語彙を流用できる | IAB Tech Lab に寄贈 |
| Privado | データフローと 110 種以上の要素 | ソースコード | 2、6 | 不可 | v1 はアーカイブ、v2 は Core |
| Presidio | 値のパターン、NER | テキスト、値 | 2、3、6（値） | サンプル値の走査に使える | Data Privacy Stack に移管 |
| Google DLP | infoType（AUTH_TOKEN・JSON_WEB_TOKEN など） | テキスト、ログ | 1、2、6 | サンプル値の走査に使える | 商用（GCP） |
| gitleaks | JWT 文字列そのもの | リポジトリ、ログ | 118（全文を残す）、1 | 例示値の走査に使える | 未検証 |
| OPA/conftest | 任意の Rego 方針 | JSON/YAML、デコード後のトークン | すべて | 可（最有力） | CNCF。OSS |

### Inferences（スライド 114 の分類ごとの検出戦略。claim-lint の規則番号は依頼文の例による）
**分類 1: 認証の秘密（パスワード、API キー）**
- 宣言: `data_category` が `user.authorization.credentials*` か `user.authorization.password` なら即 error（どのトークン種別でも禁止）。
- 名前: `password|passwd|pwd|secret|api[_-]?key|client_secret|private_key|otp|pin` を含むクレーム名は error（タグが付いていなくても）。誤検知: `password_changed_at`、`pwd_exp`（期限切れの日時）、`secret_question_set`（boolean）。接尾辞が `_at|_exp|_set|_changed` なら warning に下げる除外が要る。
- 値: example 値に gitleaks の既定ルール（AWS キー、`sk_live_` など）を当てる。誤検知は少ない。

**分類 2: 機微な属性（氏名・住所・生年月日）**（L50 機微情報、L6 ブラウザに見えるトークンに載る PII）
- 宣言: `data_category` が `user.name*|user.contact.address*|user.demographic.*|user.government_id*|user.health_and_medical*|user.biometric*` で、かつトークン種別が access token か、`visibility` が `browser|gateway|logs` なら error。ID トークンの OIDC 標準クレーム（`name`、`birthdate`、`address`）は、`audience: client-only` かつ `delivery: userinfo` を推奨する warning にとどめる（OIDC Core §5.1 の標準クレームなので、一律に error にすると誤検知になる）。
- 名前: OIDC 標準クレーム名（`name|given_name|family_name|birthdate|address|phone_number|gender`）と、日本語のローマ字表記（`shimei|jusho|seinengappi`）、`dob|birth|zip|postal`。誤検知: `name` がアプリ名やテナント名を指す場合、`address` がメールアドレスを指す場合。
- 値: Presidio の PERSON、LOCATION、DATE_TIME、PHONE_NUMBER。日本語の氏名や住所の NER の精度は保証されない（Q2 参照）ので、日付の書式 `\d{4}-\d{2}-\d{2}` のような単純な正規表現の方が確実。

**分類 3: 平文の個人情報を含む ID（メールや社員番号を sub に）**（FAL2 以上で禁止、というスライドの主張による）
- 宣言: `sub`（と `oid` のような ID のクレーム）に `id_scheme: opaque|pairwise|email|employee_number` の宣言を必須にし、`email|employee_number` かつ `fal >= 2` なら error。
- 値: sub の example 値が email の形（`^[^@\s]+@[^@\s]+$`）なら error、`^[A-Z]?\d{5,8}$`（社員番号らしい書式。組織ごとに設定する）なら warning。UUID・ULID・ハッシュ状なら通す。誤検知: 社員番号の書式は組織ごとに違い、数字だけの不透明 ID と区別できない。書式は設定ファイルに出す。
- 型: `format: email` の JSON Schema 宣言を sub に付けることを禁止する。

**分類 4: 変わりうる識別子（email、upn）を鍵に使う**（L3）
- 宣言: 各クレームに `stability: immutable|mutable|reassignable` を必須にする。`usage` に `key|authz|join` を含むクレームが `mutable` なら error。既知の一覧（`email`、`upn`、`preferred_username`、`unique_name`）は、宣言が `immutable` でも warning（Entra の文書が「認可に使わない」「変わりうる」「表示用」と明言しているため。Q1 参照）。`phone_number` と `name` は Entra の文書には出てこないので、入れるなら OIDC Core の標準クレームで利用者が変えうる値、という別の根拠で書く（2026-11-22 の点検で訂正）。
- 推奨の代わり: `oid+tid` または `iss+sub` の複合キー。キー宣言（`key: [iss, sub]`）が `iss` を含まないなら warning にする。
- 誤検知: 自社 IdP で email を変更不可に運用している場合。理由を書いた除外（`waiver: {reason, expires}`）を許す。

**分類 5: 細かい権限の一覧**
- 宣言: `data_category: authorization.permissions`（独自に拡張）や `type: array` で `max_items` の宣言がないクレームを warning。`max_items` の上限（例: 20）や、トークン全体の推定サイズ（ヘッダー上限の 8KB を目安）を超えるなら error。
- 名前: `permissions|perms|entitlements|acl|roles|groups` かつ配列型。誤検知: 粗い `roles`（数個）は正当。件数と粒度（`resource:action` 形式の要素が多いか）で判定する。Entra の groups 超過（JWT では 200 件、SAML では 150 件で超過の扱いに切り替わる。2026-11-22 の点検で確認 — [Entra: access token claims](https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference)）に似た上限ルールを設ける。
- IdP の設定: kcwarden の `ClientWithFullScopeAllowed` に相当する検査を、realm export の照合で行う。

**分類 6: 接続元の詳細（IP、端末の識別子）**
- 宣言: `user.device.ip_address|user.device.device_id|user.device.cookie_id|user.location.*` は、トークンに載せるなら warning（`freshness` か `ttl` が token の exp より短い、という根拠が要る）。`cnf`（RFC 7800、鍵の束縛）はここに含めない（端末 ID ではなく鍵の拇印なので）。
- 名前: `ip|ipaddr|client_ip|x_forwarded|device_id|udid|imei|mac|fingerprint|geo|lat|lon`。誤検知: Entra の `ipaddr` は IdP 標準のクレーム。`fingerprint` は鍵の拇印（正当）の場合がある。
- 値: Presidio の IP_ADDRESS と MAC_ADDRESS（パターン＋文脈）、正規表現 `\b\d{1,3}(\.\d{1,3}){3}\b`。

**横断（L65 機密度と可視性）**
- 「機密度のタグ × トークンが通る場所（`visibility`: browser、gateway、logs、traces）」の行列で判定する。obs-types の L002 と L003（Q2）が同じ型の先例。OPA/Rego で行列を data として持たせれば、claims.yaml の変更で方針も一緒に更新できる。

**誤検知全般**
- 名前のヒューリスティック単独で error にしない。「タグがない」または「タグと名前の推定が食い違う」場合の warning に限ると、Semgrep の監査ルールのような全件確認の負担を避けられる。
- 除外の仕組み（理由と期限を必須にする）を最初から設計する。

### Gaps
- 上の誤検知の見込みは推論で、実データで計測した値はない。
- NIST SP 800-63C-4 の FAL2 に関する記述（sub に平文の PII を入れることの禁止）は、2026-11-22 の点検で原文を確かめた（分類 3 の項を参照）。
- Entra の groups 超過の閾値は JWT で 200、SAML で 150（2026-11-22 の点検で確認）。Keycloak の protocol mapper の監査ツールは未検証。
