# 先行事例調査: 認証・認可／トークン（JWT/OAuth/OIDC）クレーム設計の設計書テンプレート・レビュー観点・レビュー報告書

調査日: 2026-11-22。凡例: 【一次】= 標準化団体・公的機関・ベンダー公式文書。【意見】= ブログ・個人記事・第三者による要約。
注記: 「(本セッションでは未取得)」と書いた URL は、よく知られた一次資料の正式な所在地として挙げたもので、本調査では本文を取得・確認していない。

## Q1. IdP ベンダー・標準化団体による、ID／認可／トークン設計のテンプレートやワークブックは公開されているか

### Takeaway
IdP ベンダー（Microsoft Entra、Curity、Auth0 等）が公開しているのは、クレームのカスタマイズ方法とベストプラクティスの文章です。クレーム設計の「設計書テンプレート」「ワークブック」は、今回の調査では見つかりませんでした。Curity は「トークンの中身は契約（contract）である」「どのクレームを入れるかを統制するプロセスが必要だ」と明言しています。一方で、そのプロセスや様式は示していません。ここがユーザー構想の空白地帯にあたります。

### Cited Findings
- 【一次】Microsoft Entra はクレームのカスタマイズ手段として claims-mapping policy と custom claims policy の2つを提供している。claims-mapping policy は service principal にしか割り当てられない。公式文書は設定手順のリファレンスで、設計用のワークシートではない — [Microsoft Learn: Claims customization reference](https://learn.microsoft.com/entra/identity-platform/reference-claims-customization), [Claims customization PowerShell](https://learn.microsoft.com/en-us/entra/identity-platform/claims-customization-powershell)
- 【一次】Microsoft の計画系文書のうち最も近いのは AD FS アプリ移行のフェーズ概要。Identity Architect が関係者と協力して設計し、引き継ぎ用に文書化する役割を定めているが、クレームの設計様式はない — [Migrate AD FS apps phases overview](https://learn.microsoft.com/nb-no/entra/identity/enterprise-apps/migrate-adfs-apps-phases-overview), [Entra deployment plans](https://learn.microsoft.com/nb-no/Entra/architecture/deployment-plans)
- 【一次・ベンダーブログ】Curity（Michal Trojanowski、2022-02-14）は、トークンの中身を「認可サーバーとトークン消費者の間の contract または interface」と位置づけている。スキーマの変更はすべて破壊的変更になり得るとし、クレームの削除はアクセス拒否に、値リストの変更は意図しないアクセス許可につながり得ると述べる。また「どのクレームをトークンに入れるかを統制するプロセスを持つべきだ」と書いている。ただし正式な設計プロセスやワークシートは示していない — [Curity: Managing Scopes and Claims in OAuth Tokens](https://curity.io/blog/managing-scopes-and-claims-in-oauth-tokens/)
- 【一次・ベンダー】Curity の JWT Best Practices（2024-07-23）は次を推奨している。
  - iss は許可リストと完全一致で照合し、aud を検証する。
  - トークン種別を scope・aud・purpose クレーム・typ=at+JWT・鍵の分離で区別する。
  - PII や内部実装情報をトークンに入れず、Phantom/Split Token パターンや PPID を使う。
  - 有効期限は分〜時間単位、時刻ずれ（clock skew）の許容は30秒以内にする。
  - チェックリストの形式にはなっていない — [Curity: JWT Security Best Practices](https://curity.io/resources/learn/jwt-best-practices/)
- 【一次・ベンダー】Auth0 は登録済みクレームとカスタムクレームを区別し、衝突を避けるために名前空間を付けることを推奨している — [Auth0: JSON Web Token Claims (ja)](https://auth0.com/docs/ja-jp/secure/tokens/json-web-tokens/json-web-token-claims), [Auth0 Token Best Practices](https://auth0.com/docs/secure/tokens/token-best-practices.md)
- 【意見】Curity 由来の内容を第三者が要約した記事（2026-06-23）は、「クレームは認可ポリシーの表面であり、記述的なクレームと権限を担うクレームを分け、誰が各クレームを主張してよいかを統制せよ」と述べる — [NHI Mgmt Group: Token claims and authorization control in APIs](https://nhimg.org/articles/token-claims-and-authorization-control-in-apis/)
- 【一次】FAPI 2.0 Security Profile と Attacker Model は 2025-02 に Final として承認された。Final 版の適合性テストと認証は 2025-07-09 に提供が始まった。FAPI は「プロファイル＋攻撃者モデル＋適合性テスト」で構成されており、プロトコル設定の妥当性を機械的に検証する仕組みである。クレームの業務的な設計（どの情報をどのクレームに載せるか）は対象外 — [OpenID: FAPI 2.0 final conformance tests available](https://openid.net/fapi2-0-final-conformance-tests-available/), [FAPI 2.0 Attacker Model (final)](https://openid.net/specs/fapi-attacker-model-2_0-final.html), [Implementer's Guide: FAPI 2.0 Final vs ID2](https://openid.net/implementers-guide-fapi-2-final-vs-implementers-draft-2/)
- 【一次】大学・研究機関の SAML フェデレーション（REFEDS R&S）には、「属性バンドル（必須・任意属性の束）」と「属性リリースポリシー（ARP）」という先行概念がある。必須バンドルをすべて出せない IdP は、メタデータに R&S のエンティティ属性を出してはならない（SHALL NOT）。必須バンドルには再割当てされない永続識別子が含まれる。これは「利用者の区分ごとに、どの属性をどの情報源から出すか」を宣言的に管理する事例で、クレームとデータソースの対応表に近い — [REFEDS R&S](https://refeds.org/research-and-scholarship), [ENTCAT-RANDS v1.2](https://zenodo.org/records/4739162/files/ENTCAT-RANDS-v1.2.pdf), [SAFIRE Attribute Release Policy](https://safire.ac.za/safire/policy/arp/)
- 【一次】RFC 8725（JWT BCP）、RFC 9700（OAuth 2.0 Security BCP、2025-01）、RFC 9068（JWT アクセストークンのプロファイル）は実装・検証の要件集で、チェックリストの元ネタとして使える。いずれも設計書の様式は定めていない (本セッションでは未取得) — [RFC 8725](https://www.rfc-editor.org/rfc/rfc8725), [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700), [RFC 9068](https://www.rfc-editor.org/rfc/rfc9068)

### Inferences
- ベンダー各社の文書は「どう設定するか（how）」と「何をしてはいけないか（don't）」が中心です。「なぜこのクレームを採用するのか（why）を記録する様式」は空白で、ユーザー構想の中核である「採否と根拠のチェックリスト」は新規性が高いと考えられます。
- Curity の「claims as contract」とガバナンスの主張は、構想を正当化する外部の根拠として引用できます。
- REFEDS の属性バンドル／ARP は、「クレームごとのデータソース対応表」の先行概念として参照する価値があります。

### Gaps
- Okta、AWS Cognito（Pre Token Generation trigger）、Keycloak（Protocol Mapper）、Ping の公式な「設計ワークブック」は今回は確認できていません。設定リファレンスのみと推測されますが、裏付けは未取得です。
- 「Curity が claims as contract を体系化したホワイトペーパー」の有無は未確認です。

## Q2. セキュリティ設計レビューのチェックリスト（OWASP ASVS 5.0、NIST、日本の公的資料）

### Takeaway
OWASP ASVS 5.0 の V8 Authorization は、8.1 に「認可ドキュメント」の要件を置いています。機能単位・データ単位・フィールド単位の認可ルールと、文脈属性・リスク閾値・step-up などの判断方法を文書化することを求めています。つまり「設計書を書くこと」自体が検証要件になっています。ただし、どんな様式で書くかは規定していません。V9/V10 は検証項目（aud、typ、sub/scope/authorization_details を判断に使う、acr/amr/auth_time など）で、レビュー観点表の素材としてそのまま使えます。日本の公的資料（デジタル庁 DS-500 系、IPA 非機能要求グレード）は本人確認や非機能要件の粒度にとどまり、クレーム設計に踏み込んだものは見つかりませんでした。

### Cited Findings
- 【一次】ASVS 5.0 の V8.1 Authorization Documentation の要件:
  - 8.1.1 (L1): 利用者の権限とリソース属性にもとづく機能単位・データ単位のアクセス制限ルールを文書化する。
  - 8.1.2 (L2): フィールド単位の読み書き制限を文書化する（状態などの他属性に依存してよい）。
  - 8.1.3 (L3): 認証・認可の判断に使う環境・文脈属性（時刻・場所・IP・デバイス）を文書化する。
  - 8.1.4 (L3): それらの属性をどう判断に使うか（評価する属性、リスク閾値、allow/challenge/deny/step-up などの処置）を文書化する。
  - 関連して 8.3.2 (L3) は、認可入力の変更を即時に反映することを求め、自己完結型トークンのように即時反映できない場合は検知・巻き戻しの緩和策を求める。8.3.3 (L3) は、中継サービスではなく発信元の利用者の権限で判断することを求める。8.4.1 (L2) はテナント間の分離を求める — [OWASP ASVS 5.0 V8 (GitHub)](https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x17-V8-Authorization.md)
- 【一次】ASVS 5.0 V9 Self-contained Tokens の要件は 9.1.1〜9.2.4 の7件:
  - 9.1.1〜9.1.3: 署名・MAC の検証、alg の許可リスト（none の禁止）、鍵の取得元を信頼できるものに限定。
  - 9.2.1: nbf/exp の確認。
  - 9.2.2 (L2): "Verify that the service receiving a token validates the token to be the correct type"（受け取ったトークンが正しい種別かを検証する）。
  - 9.2.3 (L2): "Verify that the service only accepts tokens which are intended for use with that service (audience)."（自サービス宛てのトークンだけを受け入れる）。
  - 9.2.4 (L2): 複数の audience で鍵を共有する場合の audience 制限 — [OWASP ASVS 5.0 V9 (GitHub)](https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x18-V9-Self-contained-Tokens.md)
- 【一次】ASVS 5.0 V10 OAuth and OIDC は 10.1〜10.7 の7節（Generic, Client, Resource Server, Authorization Server, OIDC Client, OpenID Provider, Consent Management）で構成される:
  - 10.3.2: sub・scope・authorization_details が存在するなら判断に使う。
  - 10.3.4: acr/amr/auth_time を使う。
  - 10.5.2: 再割当てされない sub を使う。
  - 10.5.4: aud が client_id と一致することを確認する。
  - 10.7.1〜10.7.3: 同意の取得・明示・見直し／撤回。
  - 10.2.3 と 10.4.11: scope の最小化。
  - V10 には文書化の要件はない — [OWASP ASVS 5.0 V10 (GitHub)](https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x19-V10-OAuth-and-OIDC.md)
- 【一次・コミュニティ翻訳】ASVS 5.0 には日本語訳がある（V9 自己完結型トークン、V10 OAuth と OIDC） — [coky-t ASVS 日本語訳 V9](https://coky-t.gitbook.io/owasp-asvs-ja/owasp-apurikshonsekyuriti-50/0x18-v9-tokens), [V10](https://coky-t.gitbook.io/owasp-asvs-ja/owasp-apurikshonsekyuriti-50/0x19-v10-oauth2-and-oidc)
- 【意見】第三者のまとめによると、ASVS v5.0.0 は 2025-05 にリリースされ、JWT は session management から独立した章になった。第三者資料の間で要件数の集計が食い違っている — [SecAppDev 2026 handout: What's new in ASVS v5](https://handouts.secappdev.org/handouts/2026/edenyardeni_what-s-new-in-asvs-v5.pdf), [OWASP ASVS GitHub](https://github.com/OWASP/ASVS)
- 【一次】NIST SP 800-162（2014-01、2019-08-02 更新）は ABAC の定義と導入上の考慮事項を示す。2.4.2 に Attribute Management の節がある（本文は未取得） — [NIST SP 800-162 PDF](https://nvlpubs.nist.gov/nistpubs/specialpublications/NIST.SP.800-162.pdf), [CSRC detail](https://csrc.nist.gov/publications/detail/sp/800-162/final)
- 【一次】デジタル庁の DS-500 は、2026-02-24 改訂の第3版で「トラストおよびデジタルアイデンティティに関するガイドライン群」の体系を管理する文書になった。DS-510 番台がデジタルアイデンティティ、520 番台がプライバシー、530 番台がトラスト。DS-511 は本人確認の枠組み・対策基準・リスク評価手順を扱う。DS-210 はゼロトラストアーキテクチャの適用方針 — [デジタル庁 トラスト・デジタルアイデンティティ概要 (2026-02-24)](https://www.digital.go.jp/assets/contents/node/basic_page/field_ref_resources/e2a06143-ed29-4f1d-9c31-0f06fca67afc/fc5cbe4a/20260224_resources_standard_guideline_trustidentityoverview_01.pdf), [デジタル庁 標準ガイドライン一覧](https://www.digital.go.jp/resources/standard_guidelines), 【意見】[PwC: DS-511 解説](https://www.pwc.com/jp/ja/knowledge/column/awareness-cyber-security/digital-identity/new-identity-verification-guideline-ds511-1.html)
- 【一次】IPA の非機能要求グレードは6大項目・236項目で構成され、「項目一覧・グレード表・樹系図」の3点セットで提供される。2018年版でセキュリティ項目が拡充された — [IPA 非機能要求グレード](https://www.ipa.go.jp/archive/digital/iot-en-ci/jyouryuu/hikinou/index.html), [METI 非機能要求グレード概要](https://www.meti.go.jp/policy/it_policy/softseibi/hikinou_grade.pdf)

### Inferences
- ASVS の 8.1 は「何を文書化すべきか」は示していますが、「どう書くか」は示していません。ユーザーのテンプレート群は、8.1.1〜8.1.4 を満たすための様式として位置づけられます。たとえば 8.1.4 の step-up は、スライド76の6段階のうち step-up 段階に対応します。この対応関係をテンプレートに明記すれば、価値の説明がしやすくなります。
- 8.3.2（自己完結型トークンは即時反映できないことへの緩和策）と 8.3.3（発信元利用者の権限で判断）は、「どのタイミングでどの情報をクレームに載せるか」という時系列の対応表が答えるべき論点と直接重なります。
- 非機能要求グレードの「項目一覧・グレード表・樹系図」という形式は、日本の SIer 文化で採否と水準を選ぶ様式として浸透しています。レビュー観点書を「項目＋レベル選択＋根拠」の形にすると、日本の読者に受け入れられやすいと推測されます。

### Gaps
- IPA「安全なウェブサイトの作り方」、Microsoft SDL / Threat Modeling Tool、OWASP Threat Dragon の該当箇所は、今回の調査の範囲では取得できていません。
- NIST SP 800-63C（Federation）の改訂版（-4）がアサーションの内容（属性の最小化など）をどう規定しているかは未確認です。
- 非機能要求グレードのうち、認証・アクセス制御の具体的な項目番号は原本の Excel/PDF で確認が必要です。

## Q3. ADR/MADR・設計書テンプレート（Google design docs、arc42、C4）は代替案と根拠をどう記録しているか

### Takeaway
MADR は「Decision Drivers（判断要因）→ Considered Options（検討した選択肢）→ Decision Outcome → 各案の Pros/Cons（任意）」という構造で根拠を記録します。Google の design doc も "Alternatives Considered" を中核の節に置いています。どちらも「1つの意思決定」単位の様式です。「クレーム1件ごとの採否」を一覧で並べ、横断的に比較する様式ではありません。

### Cited Findings
- 【一次】MADR は「Markdown Any Decision Records」の略で、3.0.0 から Architectural が Any に置き換わった。Decision Drivers には求める品質・制約・懸念を書き、Considered Options はその Drivers を参照して評価する。各案の Pros and Cons は任意の拡張 — [MADR 公式](https://adr.github.io/madr), [Olaf Zimmermann: MADR Template Primer (2022-11-22)](https://ozimmer.ch/practices/2022/11/22/MADRTemplatePrimer.html), [ADR templates 一覧](https://adr.github.io/adr-templates)
- 【意見・元Googleエンジニア】Malte Ubl によると、Google の design doc はトレードオフの記録が中心で、Alternatives Considered は「同じ目的を達成できた他の案を考えさせる」ための固定の節。公式の Google 文書ではない — [Industrial Empathy: Design Docs at Google](https://www.industrialempathy.com/posts/design-docs-at-google/), [Design docs - A design doc](https://www.industrialempathy.com/posts/design-doc-a-design-doc/)
- 【一次・未取得】arc42 は第9節 "Architecture Decisions" で ADR 形式の記録を推奨し、第8節 "Crosscutting Concepts" で認証・認可などの横断関心事を記述する。C4 モデルは構造図の表記法で、決定記録や認可の表現は持たない (本セッションでは未取得) — [arc42 template](https://arc42.org/overview), [C4 model](https://c4model.com/)

### Inferences
- 構想の「採否チェックリスト」は、MADR の Decision Drivers と Considered Options をクレーム単位に縮め、表形式にしたものと捉えられます。MADR の語彙（Drivers / Options / Outcome / Consequences）を列名に借りれば、ADR に慣れた読者に伝わりやすくなります。
- arc42 の第8節（Crosscutting Concepts）に認可モデル別の設計書を、第9節に ADR を置けば、既存のアーキテクチャ文書体系に組み込めます。

### Gaps
- arc42 と C4 の該当節の本文は今回取得していないため、節の番号と名称の最新版は確認が必要です。

## Q4. クレームレジストリ・データコントラクトを設計成果物として使う先行例

### Takeaway
IANA の JWT Claims レジストリは「登録テンプレート（Claim Name / Description / Change Controller / Specification Document）＋ Specification Required という審査手続き」を持っており、グローバル規模のクレームレジストリの原型です。データ分野では ODCS（Open Data Contract Standard）が、生産者と消費者の間の契約を YAML で定義し、所有者・ロール・品質ルール・SLA まで持たせています。組織内のクレームレジストリをこの「契約」として扱う公開事例は見つかりませんでした。

### Cited Findings
- 【一次】IANA の JSON Web Token Claims レジストリの登録手続きは Specification Required。中核クレーム（iss など）の Change Controller は IESG で、ETSI などの外部団体が Change Controller になっている登録例もある。登録テンプレートは RFC 7519 の 10.1.1 で定義されている — [IANA JWT registry](https://www.iana.org/assignments/jwt/jwt.xhtml), [RFC 7519](https://datatracker.ietf.org/doc/rfc7519), [jwt-reg-review 例: at_use_nbr](https://mailarchive.ietf.org/arch/msg/jwt-reg-review/FVrUtnR22OpI9PGMRHOfR6Kfj-w/)
- 【一次】ODCS（Bitol プロジェクト）は、データ生産者と消費者の間の構造化された合意を YAML で定義する。v3 では schema を object/property で表現し、property 単位の品質ルール、SLA、team/ownership、roles、customProperties を持つ。Excel テンプレートと JSON Schema も提供されている — [ODCS 公式](https://bitol-io.github.io/open-data-contract-standard/latest/), [ODCS schema](https://bitol-io.github.io/open-data-contract-standard/latest/schema/), [GitHub bitol-io/open-data-contract-standard](https://github.com/bitol-io/open-data-contract-standard)
- 【意見】Martin Fowler のサイトに、データコントラクトの考え方を解説した記事がある — [martinfowler.com: Data Contracts](https://martinfowler.com/articles/data-contracts.html)
- 【一次・ベンダー】Curity は、token mapper の設定をエクスポートしてバージョン管理し、自動分析することを推奨している。クレーム定義を構成コードとして管理する考え方 — [Curity: Managing Scopes and Claims](https://curity.io/blog/managing-scopes-and-claims-in-oauth-tokens/)

### Inferences
- ユーザーの Part 11 のクレームレジストリに、ODCS の ownership・quality・SLA や、IANA の Change Controller・Specification Document に相当する列を加えれば、「契約としてのクレーム」を設計成果物として具体化できます。これは公開事例の見当たらない組み合わせです。
- 「クレームごとのデータソース対応表」は、ODCS の property 単位メタデータと REFEDS の ARP（Q1）を掛け合わせたものと説明できます。

### Gaps
- 社内のクレームレジストリを ODCS 形式やスキーマレジストリで運用している企業の公開事例は見つかりませんでした。

## Q5. レビュー報告書の様式（インスペクション報告、IEEE 1028、PR セキュリティレビューのテンプレート）

### Takeaway
IEEE 1028 は、レビューの種類（management / technical / inspection / walk-through / audit）と、出力物として「異常リスト（anomaly list）＋アクション項目リスト」を定めています。ただし本文は有料で、今回は二次情報でしか確認できていません。PR 向けのセキュリティチェックリストは多数公開されていますが、汎用的な内容（認証の有無、認可チェック、秘密情報の扱い）にとどまります。「クレームの採否根拠の妥当性」を判定する報告様式は見当たりませんでした。

### Cited Findings
- 【一次・概要のみ】IEEE 1028 は management review、technical review、inspection、walk-through、audit を定義している。2008年版は Inactive-Reserved の扱い — [IEEE 1028-2008 (Xplore)](https://ieeexplore.ieee.org/document/4601584), [ANSI webstore](https://webstore.ansi.org/standards/ieee/ieeestd10282008)
- 【二次】レビューの出力物は一般に anomaly list と action item list（販売サイトの説明による） — [Nimonik IEEE 1028](https://standards.nimonik.com/products/ieee/ieee-1028/)
- 【一次・NASA】NASA Software Engineering Handbook は、インスペクション報告に「分類された異常・欠陥のリスト」とインスペクションのデータ・メトリクスを含めることを求めている — [NASA SWEHB](https://swehb.nasa.gov/x/BQT7), [NASA SWEHB 報告要件](https://swehb.nasa.gov/x/GgT7)
- 【一次・企業ハンドブック】GitLab は AppSec review を issue テンプレートから開始し、理想的な開始時期を設計フェーズとしている — [GitLab AppSec Review Process](https://handbook.gitlab.com/handbook/security/product-security/application-security/appsec-reviews/), [GitLab Security Review Framework](https://handbook.gitlab.com/handbook/security/product-security/security-review-framework)
- 【意見】Endor Labs の PR チェックリストは、各項目に一行の理由と OWASP/CWE の参照を付けている。OWASP の旧チェックリスト類はアーカイブされ、OWASP Developer Guide に移ったとも記している — [Endor Labs: Secure code review checklist](https://www.endorlabs.com/learn/secure-code-review-checklist)
- 【意見】PR レビューを ASVS 5.0 の要件に紐づけ、yes/no の質問で構成し、リスク区分・目標の ASVS レベル・脅威モデルの有無を記入させるテンプレートがある — [NHI Mgmt Group: Secure code review checklist](https://nhimg.org/secure-code-review-checklist)

### Inferences
- 構想のレビュー報告書は、IEEE 1028 や NASA の「異常リスト＋アクション項目」の骨格に、「根拠の妥当性判定（妥当／根拠不足／根拠が誤り）」という独自の判定軸を加える形が考えられます。こうすると既存の様式と互換性を保ちながら差別化できます。
- Endor Labs の「各項目に理由と参照を付ける」流儀は、構想の「レビュアーは根拠の妥当性だけを判断する」という方針と相性が良いと考えられます。

### Gaps
- IEEE 1028 の本文（報告書の必須項目の正確な文言）は有料のため確認できていません。

## Q6. 既存の資料にない空白は何か（ユーザー構想で埋まる部分）

### Takeaway
既存の資料は「検証要件（ASVS・RFC・FAPI）」「設定方法（ベンダー文書）」「汎用的な決定記録（MADR・design doc）」「データ契約（ODCS）」に分かれています。次の5点は、今回の調査範囲では公開されている先行事例が見つかりませんでした。
- 認可モデル別の設計書
- 時系列の6段階 × クレームの対応表
- クレームごとのデータソース対応
- 採否と根拠のチェックリスト
- 根拠の妥当性を判定するレビュー報告

### Cited Findings
- 【一次】ASVS は認可ルールの文書化（8.1.1〜8.1.4）を要件にしているが、様式は規定していない — [OWASP ASVS 5.0 V8](https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x17-V8-Authorization.md)
- 【一次・ベンダー】Curity は、クレームを統制するプロセスが必要だとしながら、その様式は示していない — [Curity](https://curity.io/blog/managing-scopes-and-claims-in-oauth-tokens/)
- 【意見】日本語の記事（Zenn など）は RBAC/ABAC/ReBAC の比較や実装例が中心で、認可設計書のテンプレートは見つからなかった — [NTT DATA TECH (Zenn)](https://zenn.dev/nttdata_tech/articles/bb08c5941eae45), [Zenn: Permit.io ReBAC](https://zenn.dev/seiichi1101/articles/permitio-rebac), [Auth0 ブログ: 適切な認可モデル](https://auth0.com/blog/jp-whats-the-right-authorization-model-for-my-application/)
- 【意見】日本語の JWT 関連資料は製品ごとのカスタムクレーム設定（Hasura、Logto など）が中心 — [Hasura: custom JWT claims](https://hasura.io/learn/ja/graphql/hasura/authentication/2-custom-jwt-claims-rule/), [Logto: custom JWT claims](https://blog.logto.io/ja/glance-on-custom-jwt-access-token-claims)

### Inferences
- 既存の資料と重複する部分（借用すべき部分）:
  - 検証観点は ASVS V8/V9/V10、RFC 8725/9700/9068、FAPI 2.0 にほぼ網羅されている。レビュー観点書は独自の項目を作るより、これらの ID に対応づけるべき。
  - 決定記録の語彙は MADR から借りられる。
  - レジストリの列は IANA と ODCS から借りられる。
- 新規性の高い部分:
  - 「発行・利用のタイミング × 情報 × クレーム」の時系列の対応表。
  - クレームごとのデータソースと鮮度（ASVS 8.3.2 の即時反映問題への答え）。
  - レビュアーの役割を「根拠の妥当性判定」に限定する分業設計。
  - 日本語でこれを体系化していること。
- 最大のリスクは、ASVS 8.1 との対応を示さないと「独自の様式」と見なされることです。各テンプレートに「満たす ASVS 要件 ID」の欄を設けることを推奨します。

### Gaps
- Microsoft SDL、OWASP Threat Dragon、Okta、Cognito、Keycloak、Ping について、クレーム設計の様式がないことを一次資料で直接確認したわけではありません。「見つからなかった」は検索の範囲内での結論です。
- 有償のコンサルティング成果物や社内テンプレート（非公開）は調査できません。
