# 04 日本語の参考書籍・公式和訳（JWT クレーム設計デッキ用）

調査日: 2026-11-17
方針: 出版社公式ページ（または出版社公式ストア・公式サポートサイト）で書誌を確認したものを掲載。確認できなかった項目は **[未検証]** と明記。電子版の有無を必ず併記（著者が後で電子書籍で読むため）。

ティア定義:
- **A** = 公式仕様の和訳／仕様策定関係者（仕様著者・OpenID Foundation／OIDF-J 役員等）の著作・監修・監訳
- **B** = 定評ある出版社の専門書
- **C** = 同人誌・入門書

---

## 0. 結論: 実際に読むべき推奨 7 冊（優先順）

| # | 書名 | ティア | 電子版 | デッキで裏付けるトピック |
|---|---|---|---|---|
| 1 | OpenID Connect入門（土岐孝平 著／倉林雅 監修, 技術評論社 2026） | A/B | Gihyo Digital Publishing・Kindle 他 | アクセストークン（JWT vs opaque）・ID トークン・リソースサーバーでのトークン検証・`aud` 検証 |
| 2 | OAuth徹底入門（Richer/Sanso 著, Authlete 監修, 翔泳社 2019） | A | 翔泳社電子書籍（ISBN 9784798159300） | JWT/JOSE・イントロスペクション・失効・OIDC・PoP トークン |
| 3 | 実践Keycloak（Thorgersen/Silva 著, オライリー・ジャパン 2022） | B | PDF/EPUB（オライリー直販） | ID トークンへのカスタム属性・ロール追加、`aud`/ロール/スコープによる制限、トークン検証・有効期限 |
| 4 | デジタルアイデンティティのすべて（Windley 著／富士榮尚寛 監訳, オライリー・ジャパン 2024） | A | PDF/EPUB | 「アイデンティティとクレーム」の概念、フェデレーション、OAuth/OIDC の位置づけ、VC |
| 5 | はじめてのデジタルアイデンティティ（いとうりょう 著, 技術評論社 2026） | A/B | Gihyo Digital Publishing・Kindle 他 | ID 管理の全体像（当人認証・ID 連携・セッション・再認証）、JOSE の基礎 |
| 6 | 認証と認可 Keycloak入門 第2版（中村雄一 他, リックテレコム 2025） | B | Kindle・Kobo・honto 他 | OAuth/OIDC の基礎、トークン失効と認可判断、スコープ設定、Keycloak の実運用 |
| 7 | Auth屋『OAuth・OIDCへの攻撃と対策を整理して理解できる本』＋『…OAuth 2.1 を整理して学べる本』 | C | BOOTH（PDF＋DRMフリーEPUB） | `nonce`/`state`/PKCE/`c_hash`/`at_hash`、トークンインジェクション、OAuth 2.1 の差分 |

補助（概念・権威付け）: 崎村夏彦『デジタルアイデンティティー』（A, Kindle あり）。無料の公式和訳（OIDF-J）は §1 参照。

---

## 1. ティア A: 公式仕様の和訳・仕様策定関係者の著作

### A-1. OpenID ファウンデーション・ジャパン（OIDF-J）公開の仕様和訳【無料】
- 掲載ページ: https://www.openid.or.jp/document/ （公式。確認済み）
- 和訳がある仕様（公式ページで確認）:
  - OpenID Connect: **OpenID Connect Core 1.0 日本語訳**、Basic Client Implementer's Guide 1.0、Implicit Client Implementer's Guide 1.0、OpenID Connect for Identity Assurance 1.0 / Claims Registration 1.0 / Identity Assurance Schema Definition 1.0
  - OAuth 2.0: **RFC 6749**（OAuth 2.0 Authorization Framework）、**RFC 6750**（Bearer Token Usage）、**RFC 6819**（Threat Model and Security Considerations）、RFC 5849（OAuth 1.0）
  - JWx: **JSON Web Token — draft-ietf-oauth-json-web-token-11 の日本語訳**（※最終版 RFC 7519 ではなくドラフト 11 の訳。引用時は「RFC 7519 の策定途中版の和訳」と注記すべき）、draft-ietf-jose-use-cases-03
  - その他: OpenID Authentication 2.0 等
- 公式ページに**無い**もの: OIDC Discovery / Dynamic Registration / Session・各種 Logout、RFC 7515–7518（JWS/JWE/JWK/JWA）、RFC 7636（PKCE）、RFC 8693（Token Exchange）、RFC 9068、RFC 9700（Security BCP）、CIBA、FAPI 本体（FAPI はホワイトペーパーのみ）
- 翻訳者名: 公式ページには記載なし **[未検証]**（各訳文 PDF 内に記載がある可能性）
- 使い方: 「ID トークンの必須クレーム（`iss`/`sub`/`aud`/`exp`/`iat`/`nonce`/`auth_time`/`acr`/`amr`/`azp`）と検証手順は OIDC Core 1.0（OIDF-J 日本語訳）§2・§3.1.3.7 に従う」と日本語で引用できる。

### A-2. OIDF-J 翻訳ホワイトペーパー『Agentic AIのためのアイデンティティ管理』【無料】
- 原文: OpenID Foundation "Identity Management for Agentic AI: The new frontier of authorization, authentication, and security for an AI agent world"（2025-10-07 公開, AI Identity Management Community Group）
- 日本語版公開: 2025-11-09（OIDF-J お知らせ https://www.openid.or.jp/news/2025/11/identity-management-for-agentic-ai.html で確認）
- 形式: Web 公開（PDF 形式か等の詳細は **[未検証]**）
- 使い方: デッキの「AI エージェントと委任／トークン交換」章で、**日本語で引用できる唯一の準公式資料**。ヒト前提のアクセス管理の限界、エージェントへの委任・権限縮小の論点の裏付けに使う。

### A-3. OAuth徹底入門 セキュアな認可システムを適用するための原則と実践
- 著: Justin Richer, Antonio Sanso／翻訳: 須田智之／監修: Authlete, Inc.（翔泳社公式ページで確認）
  - 権威: Justin Richer は RFC 7591（動的クライアント登録）・RFC 7662（トークンイントロスペクション）等の著者。Authlete は川崎貴彦氏（Authlete 創業者・OIDF-J 関係者）の会社で、Authlete 公式サイトでも「OAuth 2 in Action の日本語訳を監修」と明記。
- 原書: *OAuth 2 in Action*（Manning, 2017）
- 出版社: 翔泳社「徹底入門」シリーズ
- 発売日: 2019-01-30／B5変・464 ページ／定価 4,620 円（税込）
- ISBN: 紙 978-4-7981-5929-4／**電子 978-4-7981-5930-0**（翔泳社公式の電子書籍ページあり）
- 電子版: 翔泳社公式に電子書籍ページあり。SEshop の PDF 版（DRM 形式）・Kindle の有無は **[未検証]**
- 関連章（公式目次より）:
  - Chapter 4 シンプルなOAuthの保護対象リソースの構築（4.1 HTTPリクエストからのOAuthトークンの解析）
  - Chapter 8 よく狙われる保護対象リソースの脆弱性（8.3 トークンのリプレイ攻撃）
  - Chapter 10 よく狙われるOAuthトークンの脆弱性（Bearer トークンのリスク）
  - **Chapter 11 OAuthトークン**（11.2 JWT（JSON Web Token）／11.3 JOSE／11.4 トークン・イントロスペクション／11.5 トークン取り消し／11.6 OAuthトークンのライフサイクル）
  - **Chapter 13 OAuth 2.0を使ったユーザー認証**（13.1 なぜOAuth 2.0は認証プロトコルではないのか／13.4 落とし穴／13.5 OpenID Connect）
  - Chapter 15 Bearerトークンの次にくるもの（PoP トークン、TLS トークン・バインディング）
- 注意: 2019 年刊で OAuth 2.1 / RFC 9068 / DPoP（RFC 9449）以前。原書は Manning で第 2 版が進行中（英語）。
- 使い方: 「JWT（自己完結型）とイントロスペクション（参照型）の選択」「OAuth は認証ではない → ID トークンが必要」の章の裏付け。

### A-4. デジタルアイデンティティのすべて ―安全かつユーザー中心のアイデンティティシステムを実現するための知識
- 著: Phillip J. Windley／序文: Drummond Reed／**監訳: 富士榮尚寛**（OIDF-J 代表理事）／訳: 柴田健久 ほか 10 名（オライリー・ジャパン公式で確認）
- 原書: *Learning Digital Identity*（O'Reilly, 2023）
- 出版社: オライリー・ジャパン／発行: 2024-12-27／464 ページ
- ISBN: 978-4-8144-0098-0
- 電子版: **PDF・EPUB**（オライリー・ジャパン直販, 5,280 円）、O'Reilly Learning にも収録
- 関連章: 11章 認証と関係の完全性／12章 アクセス制御／**13章 フェデレーションアイデンティティ（13.7.4 OAuth, 13.7.5 OpenID Connect）**／9章 暗号・デジタル署名・PKI／15章 検証可能なクレデンシャル（VC）／20章 IoT（OAuth のデバイス利用）
- 注意: 目次に「JWT」見出しはない（概念書）。
- 使い方: 「クレーム＝主体についての主張であり、発行者への信頼が前提」という概念の日本語での裏付け。フェデレーションと信頼モデルの章。

### A-5. デジタルアイデンティティー 経営者が知らないサイバービジネスの核心
- 著: 崎村夏彦（OpenID Connect Core 1.0 の筆頭著者、米国 OpenID Foundation 理事長／Chairman）
- 出版社: 日経BP／2021年7月／255 ページ（国立国会図書館書誌で確認）
- ISBN: 978-4-296-10990-6
- 電子版: **Kindle 版あり**（Amazon ASIN B099842GV4 で確認）。日経BP 公式ページでの電子版表記は **[未検証]**
- 関連章（NDL 目次、全 14 章中 5 章のみ確認）: 第2章 アイデンティティー管理／**第3章 アイデンティティー連携フレームワーク「OpenID Connect」**／第4章 アクセス制御。残り 9 章 **[未検証]**
- 注意: 経営者向けの概念書。実装・クレーム詳細は期待しない。
- 使い方: 冒頭の「なぜ ID トークンを設計するのか」で、OIDC の筆頭著者による日本語の権威付けとして一言引用。

### A-6. パスキーのすべて ──導入・UX設計・実装（参考・周辺）
- 著: えーじ、倉林雅（OIDF-J 理事・エバンジェリスト）、小岩井航介（米国 OpenID Foundation 理事、OIDF-J KYC WG リーダー）
- 出版社: 技術評論社（WEB+DB PRESS plus）／2025-01-28／256 ページ相当
- ISBN: 紙 978-4-297-14653-5／電子 978-4-297-14654-2
- 電子版: Gihyo Digital Publishing **EPUB/PDF セット**（3,000 円）
- 関連章: 1.4 ID連携、8.6 Attestation。OIDC・JWT・`acr`/`amr` は目次に**なし**
- 使い方: `amr`（`hwk`/`swk`/`user` 等）や `acr` で「パスキーでログインした」ことを伝える話題の背景としてのみ。クレーム自体の裏付けにはならない。

---

## 2. ティア B: 定評ある出版社の専門書

### B-1. OpenID Connect入門 ―アプリケーション開発者のための実践技術解説 ★最優先
- 著: 土岐孝平（合同会社 現場指向）／**監修: 倉林雅（OIDF-J 理事・エバンジェリスト）**（監修者の立場から A 寄り）
- 出版社: 技術評論社／**2026-02-24**／A5・272 ページ／3,300 円
- ISBN: 紙 978-4-297-15456-1／電子 978-4-297-15457-8
- 電子版: **Gihyo Digital Publishing、Kindle、楽天Kobo、BookLive、honto**（gihyo.jp で確認）
- 関連章（公式目次）:
  - 1.6 OIDC のロール、1.7 クライアントの種類（MPA/SPA/BFF/ネイティブ）、1.8 Confidential/Public
  - 3章 エンドポイントとフロー（クライアントクレデンシャル含む）
  - **4章 トークンの種類と形式**（4.2 アクセストークン／4.2.1 opaque／**4.2.2 JWT**／4.2.3 比較／**4.3 IDトークン**／4.4 リフレッシュトークン）
  - 5章 認可コードフロー詳細（5.2.6 `nonce`、5.2.7 PKCE）
  - **6.2 （リソースサーバー）アクセストークンの検証**（6.2.1 デジタル署名による検証／6.2.2 IdP への問い合わせ）、6.4 ユーザー情報
  - 7章 ログイン（RP-Initiated / Front-Channel / Back-Channel Logout）
  - 8〜12章 Keycloak による実装例（SPA・BFF・Android・クライアントクレデンシャル）
  - **13章 セキュリティ脅威と対策**（13.8 他クライアント向けアクセストークンの流用、**13.9.6 リソースサーバーで `aud` クレームをチェック**、13.9.7 アクセストークン有効期限の短縮、13.9.9 FAPI 2.0）
  - 付録C OIDC 公式ドキュメント案内（C.3 アクセストークン、C.7 JWT）
- 使い方: デッキの中核（ID トークン vs アクセストークンの使い分け、`aud` 検証、署名検証 vs イントロスペクション）を**最新の日本語書籍**で裏付けられる。

### B-2. 実践 Keycloak ―OpenID Connect、OAuth 2.0を利用したモダンアプリケーションのセキュリティー保護
- 著: Stian Thorgersen（Keycloak プロジェクトリーダー）、Pedro Igor Silva／訳: 和田広之、田村広平、乗松隆志、田畑義之（訳者まえがきによれば Keycloak メンテナー 1 名を含むコントリビューター 4 名）
- 原書: *Keycloak - Identity and Access Management for Modern Applications*（Packt, 初版）
- 出版社: オライリー・ジャパン／2022-10-15／352 ページ
- ISBN: 978-4-8144-0009-6
- 電子版: **PDF・EPUB**（オライリー・ジャパン直販 4,180 円）、O'Reilly Learning
- 関連章（公式目次）:
  - 3章 標準の簡単な紹介（**3.3 アクセストークンでの JWT の利用**）
  - **4章 OIDC によるユーザー認証**（**4.5 IDトークン**：4.5.2 カスタム属性の追加、**4.5.3 IDトークンへのロールの追加**／4.6 UserInfo／4.7 ログアウト）
  - **5章 OAuth 2.0 によるアクセス認可**（**5.5 アクセストークンのアクセス権の制限：audience・ロール・スコープ**／**5.6 アクセストークンの検証**）
  - 8章 認可戦略（RBAC・GBAC・スコープ・ABAC）
  - 12章 トークンとセッションの管理（ID/アクセストークン有効期限、リフレッシュトークンのローテーション、失効）
  - 14章（14.5.2 OAuth 2.0 と OIDC のベストプラクティス）、日本語版補章 15章 クライアントポリシー
- 注意: 原書第 2 版（英語, 2023）あり。和訳は初版ベースで旧 Keycloak（〜19 前後）の UI **[未検証]**。
- 使い方: Keycloak 編の「プロトコルマッパーで何をクレームに入れるか／入れないか」「audience 制御」の裏付け。

### B-3. 認証と認可 Keycloak入門 第2版 ―OAuth/OpenID Connectに準拠したAPI認可とシングルサインオンの実現
- 著: 中村雄一、和田広之、田村広平、田畑義之、青柳隆、奥浦航（所属は公式ページに記載なし。初版著者は日立製作所の Keycloak コミッター等とされるが **[未検証]**）
- 出版社: リックテレコム／2025年3月下旬刊（書店データでは 2025-04-03 発売）／B5変・496 ページ／4,840 円
- ISBN: 978-4-86594-436-5（初版: 978-4-86594-322-1, 2022-01）
- 電子版: **Kindle、楽天Kobo、honto、contendo、紀伊國屋**（リックテレコム公式ページで確認。形式は記載なし）
- 関連章（公式目次）: **2章 OAuthとOIDCの基礎知識**（2.2 アクセストークンとリフレッシュトークン／2.3 トークンの失効と認可判断／2.4 OIDC のフロー）／4.2 セッションとトークンの設定／**5章 OAuthに従ったAPI認可の実現**（5.3 API 呼び出し時の認可判断とスコープ設定／5.4 リフレッシュと失効／5.5 OAuth/OIDC のセキュア化）／6章 SSO（Spring Security 連携含む）／7章 外部 IdP 連携
- 注意: 目次上に JWT・トークン交換・マッパーの独立節は無い。
- 使い方: Keycloak（Quarkus 版）での実設定の日本語リファレンス。「リソースサーバー側の認可判断（スコープ）」の裏付け。

### B-4. はじめてのデジタルアイデンティティ ―Webサービスに欠かせない認証・認可・ID管理
- 著: いとうりょう（株式会社MIXI「MIXI ID」担当、**OIDF-J エバンジェリスト**）
- 出版社: 技術評論社／**2026-01-07**／A5・160 ページ／2,420 円
- ISBN: 紙 978-4-297-15376-2／電子 978-4-297-15377-9
- 電子版: **Gihyo Digital Publishing、Kindle、楽天Kobo、BookLive、honto**
- 関連章（公式目次）: 2-2 当人認証・2-4 ID連携・2-6 セッション管理／3-5 再認証／4章 複数サービスが関わる ID 管理（4-1 ID連携の概要、4-3 RP の ID 管理機能）／5-4 NIST SP 800-63／5-5 標準化仕様（OAuth 2.0・OIDC・SCIM・SSF）／**6-1 JOSE と COSE、Base64URL、暗号技術**
- 注意: ID トークン・クレーム・トークン検証の独立節は**無い**（入門書）。
- 使い方: 「ID トークン＝ID 連携の結果を RP に渡すもの」「`auth_time`／再認証」の背景説明。JWT の Base64URL・JOSE 基礎の日本語参照。

### B-5. Software Design 別冊『今さら聞けない暗号技術＆認証・認可 ―Web系エンジニア必須のセキュリティ基礎力をUP』
- 著: 大竹章裕、瀬戸口聡、庄司勝哉、光成滋生、谷口元紀、くつなりょうすけ、栃沢直樹、渥美淳一、宮川晃一、**富士榮尚寛**、**川﨑貴彦**（Authlete 代表）
- 出版社: 技術評論社／2023-03-06／B5・160 ページ
- ISBN: 紙 978-4-297-13354-2／電子 978-4-297-13355-9（Gihyo Digital Publishing あり）
- 関連章: 第4章 今さら聞けない認証・認可（4-3 クラウド時代の ID 管理技術 ほか）／**第5章 挫折しない OAuth/OpenID Connect 入門**（5-1 OAuth とは・OIDC とは／5-2 知っておきたい仕様と規格／**5-3 トークンハンドリングの基本**）— 第5章は川﨑貴彦氏の『Software Design』2021年10月号記事の再録（Authlete 公式サイトで確認）。各節の執筆者割当は公式ページでは未記載 **[未検証]**。
- 注意: **川﨑貴彦氏名義の単行本は確認できず**（本誌記事・別冊収録のみ）。氏の Qiita 記事（例:「OAuth/OIDC の JWT まとめ」）は書籍ではない。
- 使い方: 「Authlete 川﨑氏による日本語解説」として OAuth/OIDC 仕様群の地図とトークン取り扱いの裏付け。

### B-6. 実践マイクロサービスAPI
- 著: José Haro Peralta／翻訳・監修: 株式会社クイープ／原書 *Microservice APIs*（Manning）
- 出版社: 翔泳社／2023-10-18／4,180 円
- ISBN: 紙 978-4-7981-7973-5／電子 978-4-7981-8412-8（翔泳社公式ページ URL で確認）
- 電子版: SEshop **PDF 版**（「編集・印刷・コピー禁止」等の制限付き PDF）、翔泳社電子書籍
- 関連章: Part 4 マイクロサービスAPIのセキュリティ、テスト、デプロイ／第11章 APIの認証と認可（CodeZine 記事で確認）。節レベル（JWT 検証の有無）は **[未検証]**（原書では OAuth/OIDC と JWT の検証を扱う）
- 使い方: マイクロサービスでの JWT 検証（API ゲートウェイ／各サービス）の補助参照。

### B-7. セキュアAPI 設計・構築・実装を貫く原則（新刊）
- 著: José Haro Peralta／訳: 元内柊也、小栁斉、織茂駿斗、水元恭平／原書 *Secure APIs*（Manning）
- 出版社: 翔泳社／**2026-07-15**／392 ページ／4,950 円
- ISBN: 978-4-7981-9633-6（翔泳社公式 URL・Amazon で確認）
- 電子版: **SEshop PDF 版**あり（4,950 円）
- 関連章: 目次は取得できず **[未検証]**（原書は API 認証・認可、OAuth/OIDC、JWT の安全な扱いを含むとされるが、和訳の章構成は未確認）
- 使い方: 「API セキュリティ（BOLA/過剰なデータ露出とクレームによる認可）」の補強候補。目次確認後に採否判断。

### B-8. ゼロトラストネットワーク 第2版 ―境界防御の限界を超えるためのセキュアなシステム設計
- 著: Razi Rais、Christina Morillo、Evan Gilman、Doug Barth／訳: 鈴木研吾
- 出版社: オライリー・ジャパン／2025-06-16／ISBN 978-4-8144-0123-9
- 電子版: O'Reilly Learning 収録確認（オライリー直販の PDF/EPUB は **[未検証]**）
- 関連章: **[未検証]**（JWT 検証の具体的記述は未確認）
- 使い方: 「トークンは毎リクエスト検証する」というゼロトラスト原則の一般的裏付け程度。

### B-9. Web API: The Good Parts
- 著: 水野貴明／オライリー・ジャパン／2014-11-21／224 ページ／ISBN 978-4-87311-686-0
- 電子版: **PDF・EPUB**（オライリー直販）、O'Reilly Learning
- 関連章: 2.6 ログインと OAuth 2.0（アクセストークンの有効期限とリフレッシュ）／6章 堅牢な Web API（XSRF、リクエスト再送等）
- 注意: 2014 年刊。JWT・OIDC の記述は目次上なし。
- 使い方: 古典として 1 行程度。クレーム設計の裏付けには不向き。**推奨対象外**。

### B-10. 体系的に学ぶ 安全なWebアプリケーションの作り方 第2版（徳丸本）
- 著: 徳丸浩（EGセキュアソリューションズ代表、IPA 非常勤研究員）／SBクリエイティブ／2018-06-21／ISBN 978-4-7973-9316-3
- 電子版: Kindle・楽天Kobo（公式サポートサイト wasbook.org で確認）
- **JWT/OAuth について**: 公式目次（wasbook.org）上、**JWT・OAuth・OpenID の章・節は無い**。関連は 3.1 HTTP とセッション管理、4.6 セッション管理の不備、4.16 Web API の脆弱性（JSON/JSONP/CORS）、5.1 認証、5.3 認可（認可不備＝IDOR 系）。
- **第3版**: SBクリエイティブ、**2026-12-23 発売予定・約 600 ページ**（Google Books の出版社紹介文）。新設内容に「**JWT によるセッション管理とその攻撃手法（alg=none 攻撃など）**」を実習付きで解説、OWASP ASVS v5・NIST SP 800-63B-4 準拠（@IT 2026-08-28 記事でも確認）。ISBN・電子版は **[未検証]**（未発売）。
- 使い方: 第2版は「認可はサーバー側で毎回判定（クレームを信じすぎない）」の一般原則（5.3）のみ。**第3版発売後に `alg=none` 等の JWT 攻撃の日本語裏付けとして最有力**になる見込み。

### B-11. マスタリングOkta ―IDaaS設計と運用
- 著: Lovisa Stenbäcken Stjernlöf、HenkJan de Vries／訳: 髙橋基信／オライリー・ジャパン／2021-12-27／256 ページ／ISBN 978-4-87311-971-7
- 電子版: **PDF・EPUB**
- 関連章: 3.5 SAML と OpenID Connect アプリケーション／**7章 API管理**（7.3 API Access Management の基礎・レベル3 OAuth 2.0／7.4 認可サーバー、鍵のローテーション）。クレームの独立節は目次上なし
- 使い方: Okta（カスタム認可サーバー）の補助参照。Auth0 の日本語書籍は見つからず。

### B-12. ひと目でわかる Microsoft Entra ID
- 著: 竹島友理（エディフィストラーニング）／日経BP／2023-12-25／688 ページ／4,620 円／ISBN 978-4-296-08036-6
- 電子版: 日経BP 公式ページに記載なし **[未検証]**
- 関連章: 10章 Microsoft Entra ユーザーの認証と認可／12章 アプリケーションとの統合（節レベル未確認 **[未検証]**）
- 注意: 管理者向け操作解説書。v1/v2 トークン、`roles`/`scp`/`oid`/`tid` 等のクレームの解説は期待できない。
- 使い方: Entra 編で「管理面の日本語参考」として脚注程度。**推奨対象外**。

---

## 3. ティア C: 同人誌・入門書

### C-1. Auth屋「雰囲気OAuth」シリーズ（BOOTH / 技術書典）
いずれも BOOTH で **PDF＋DRMフリー EPUB**（電子 1,400 円、物理＋電子 1,600 円、3冊セット 3,980 円）。BOOTH 公式商品ページで確認。目次は商品ページに未掲載 **[未検証]**。
1. **雰囲気でOAuth を使っているエンジニアが、最新のベストプラクティスOAuth 2.1 を整理して学べる本**（2025年12月改訂, OAuth 2.1 ベース）https://booth.pm/ja/items/1296585
   - 内容: スコープ、認可コード、PKCE（2.1 で必須）、curl とブラウザによるチュートリアル、OAuth 2.0 と 2.1 の差分、付録で旧グラントタイプ
2. **OAuth、OAuth認証、OpenID Connectの違いを整理して理解できる本 [2024年改訂版]**（OpenID Configuration の章とコラムを追加）https://booth.pm/ja/items/1550861
   - 内容: OAuth を認証に使う問題と ID トークンが解決すること
3. **OAuth・OIDCへの攻撃と対策を整理して理解できる本（リダイレクトへの攻撃編）[2023年改訂版]** https://booth.pm/ja/items/1877818（約100ページ）
   - 内容: `state`・`nonce`・PKCE・`c_hash`・`at_hash`、CSRF・リプレイ・認可コード横取り・コードインジェクション・**トークンインジェクション**
- 関連: 『パスキーのすすめ』（BOOTH）
- 使い方: ID トークンの `nonce`/`at_hash`/`c_hash` 検証の「なぜ」を図解で補強。同人誌のため権威付けではなく「わかりやすい日本語解説」として。

### C-2. Auth屋の商業出版
- **雰囲気で使わずきちんと理解する！整理してOAuth2.0を使うためのチュートリアルガイド・最新改訂版**（インプレス NextPublishing／2019-09-20／ISBN 978-4-8443-7818-1／電子 EPUB 1,980 円, honto で確認）— 3章 OAuthのトークン、付録A OAuth認証について。※OAuth 2.0 時代の内容。BOOTH の 2.1 版の方が新しい。
- **Firebase Authenticationで学ぶ ソーシャルログイン入門 ID管理の原則にそった実装のベストプラクティス**（著: Auth屋／監修: いとうりょう／翔泳社／2022-12-12）— 電子書籍 ISBN 978-4-7981-7963-6（翔泳社公式）、紙 ISBN **[未検証]**。Chapter 3 ソーシャルログインを実現するには、Chapter 7 Firebase Auth 単体（SPA＋Web API バックエンド）。

### C-3. OAuth 2.0実装入門 安全なAPI認可の実現方法（技術の泉シリーズ）
- 著: Authマロン／インプレス NextPublishing／2026-09-01／ISBN 978-4-295-60550-8
- 電子版: **EPUB3**（1,800 円＋税）、紙は POD（B5 カラー約200ページ）
- 関連章: 第8章 アクセストークンの発行／第9章 state と PKCE／**第10章 アクセストークンの検証**
- 使い方: 認可サーバーを自作して学ぶ入門書。権威付けには弱い。

### C-4. その他（存在のみ確認・詳細未検証）
- 『OpenID Connect入門: 概念からセキュリティまで体系的に押さえる』土岐孝平（Kindle 自費出版, B-1 の前身と思われる）**[未検証]**（個人ブログのリストで確認したのみ）
- 『実践React＆Nest.js Webアプリケーション開発 Auth0認証とAWS/Azureへのデプロイ完全ガイド』吉倉英貴（インプレス NextPublishing）**[未検証]**
- 『SAML入門』廣瀬翔遥（技術の泉）**[未検証]**

---

## 4. 調査したが推奨しない／該当なしのもの

- **IPA『安全なウェブサイトの作り方』改訂第7版**（無料 PDF, https://www.ipa.go.jp/security/vuln/websecurity/about.html）: 第1章は SQLi・XSS 等 11 種の脆弱性、第2章はパスワード取扱い等の運用面。**JWT・OAuth・OIDC の記述は無い**。デッキでは使わない（せいぜい「認可不備は脆弱性」程度）。
- IPA『API 標準設計ガイド・基礎編』（PDF, ipa.go.jp/digital 配下）: 2.5 セキュリティと認証方式の定義を含む。JWT クレームの扱いの深さは **[未検証]**。
- Real World HTTP（オライリー・ジャパン）: 第2版目次で OAuth/JWT は確認できず（第3版 2024 は **[未検証]**）。
- Spring 系: 『Spring徹底入門 第2版』（翔泳社 2024, 9章 Spring Security）で OAuth2 リソースサーバー／JWT の節は確認できず **[未検証]**。**OAuth2 リソースサーバーを扱う日本語 Spring Security 専門書は見つからず**。Spring Security 公式リファレンスの日本語訳（spring.pleiades.io, 非公式訳）は JWT 検証（`exp`/`nbf`/`iss`、`SCOPE_` マッピング）を扱う。
- Amazon Cognito / Auth0 の日本語単行本: **見つからず**（Auth0 は公式日本語 eBook・ドキュメントのみ）。
- AI エージェント × OAuth/トークン交換の日本語書籍: **見つからず**（A-2 の OIDF-J 翻訳ホワイトペーパーのみ）。
- 川﨑貴彦（Authlete）の単著: **確認できず**（雑誌記事・別冊収録・監修のみ）。

---

## 5. 日本語書籍の裏付けが無く、RFC/公式仕様で裏付けるべきトピック

| トピック | 根拠にすべき一次資料 |
|---|---|
| JWT アクセストークンのプロファイル（`typ: at+jwt`、必須クレーム `iss`/`exp`/`aud`/`sub`/`client_id`/`iat`/`jti`） | RFC 9068 |
| JWT の安全な取り扱い（アルゴリズム固定、`typ` による型区別、クロス JWT 混同） | RFC 8725（JWT BCP）、RFC 7515–7519（和訳は JWT draft-11 のみ） |
| 委任・トークン交換（`act`／`may_act`、subject_token/actor_token） | RFC 8693 |
| AI エージェント／MCP の認可（Protected Resource Metadata、リソースインジケーター） | RFC 9728、RFC 8707、RFC 8414、MCP Authorization 仕様（＋A-2 和訳ホワイトペーパー） |
| OAuth セキュリティ BCP（2.1 の根拠） | RFC 9700、draft-ietf-oauth-v2-1 |
| 送信者制約トークン（`cnf` クレーム） | RFC 9449（DPoP）、RFC 8705（mTLS） |
| `amr` 値の登録 | RFC 8176 |
| OIDC Discovery／JWKS・鍵ローテーション | OpenID Connect Discovery 1.0（和訳なし） |
| IdP 固有クレーム（Entra ID の `oid`/`tid`/`roles`/`scp`/`ver`、Cognito の `token_use`/`cognito:groups`、Auth0 の名前空間付きカスタムクレーム、Okta） | 各ベンダー公式ドキュメント（日本語版ドキュメントは各社公式にあり。書籍は無し） |
| SCIM・Shared Signals（失効の伝播） | RFC 7643/7644、OpenID SSF/CAEP |

---

## 出典（確認に使った公式ページ）
- 翔泳社 OAuth徹底入門: https://www.shoeisha.co.jp/book/detail/9784798159294 （電子: …/9784798159300）
- 技術評論社 OpenID Connect入門: https://gihyo.jp/book/2026/978-4-297-15456-1
- 技術評論社 はじめてのデジタルアイデンティティ: https://gihyo.jp/book/2026/978-4-297-15376-2
- 技術評論社 パスキーのすべて（電子）: https://gihyo.jp/dp/ebook/2025/978-4-297-14654-2
- 技術評論社 SD別冊 今さら聞けない暗号技術＆認証・認可: https://gihyo.jp/book/2023/978-4-297-13354-2
- オライリー・ジャパン: https://www.oreilly.co.jp/books/9784814400980/ ・ /9784814400096/ ・ /9784873119717/ ・ /9784873116860/
- リックテレコム Keycloak入門 第2版: https://www.ric.co.jp/book/new-publication/detail/2925
- 翔泳社 実践マイクロサービスAPI: https://www.shoeisha.co.jp/book/detail/9784798179735 ／ セキュアAPI: https://shoeisha.co.jp/book/detail/9784798196336
- 翔泳社 Firebase Authentication…: https://www.shoeisha.co.jp/book/detail/9784798179636
- BOOTH（Auth屋）: https://booth.pm/ja/items/1296585 ・ /1550861 ・ /1877818
- インプレス NextPublishing: https://news.nextpublishing.jp/news/detail/1620/ ／ honto https://honto.jp/ebook/pd_29897747.html
- 日経BP: https://bookplus.nikkei.com/atcl/catalog/23/11/30/01130 ／ NDL 崎村本: https://ndlsearch.ndl.go.jp/en/books/R100000002-I031544782
- 徳丸本 第2版サポート: https://wasbook.org/content.html ／ 第3版記事: https://atmarkit.itmedia.co.jp/ait/articles/2608/28/news018.html
- OIDF-J: https://www.openid.or.jp/document/ ・ https://www.openid.or.jp/news/2025/11/identity-management-for-agentic-ai.html
- IPA: https://www.ipa.go.jp/security/vuln/websecurity/about.html
