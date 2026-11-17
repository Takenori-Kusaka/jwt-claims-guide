# 03 実インシデント・攻撃クラス・AIエージェント委任

- 調査日: 2026-11-17（「現状」はこの日付時点）
- 方針: 一次資料（RFC / IETF datatracker / OpenID仕様 / MCP仕様 / ベンダー公式 / NVD / 研究者本人の記事）を取得・読了したものだけを事実として記載。取得できなかった・裏取りできなかった点は **[未検証]** と明記。
- 略記: NVD = `https://nvd.nist.gov/vuln/detail/<CVE>`（記載内容は NVD API `services.nvd.nist.gov/rest/json/cves/2.0?cveId=` で取得した description に基づく）

---

## 1. JWT 検証に対する攻撃クラス

凡例: **何が起きる / 関与するclaim・header / 検証コードの根本原因 / 対策 / 実例**

### 1.1 `alg: "none"`
- 何が起きる: 署名なしトークンが「検証済み」として受理され、任意のペイロードを偽造できる。
- 関与: header `alg`
- 根本原因: ライブラリがトークン自身の `alg` に従って検証方式を選ぶ。`none` をブロックリストで弾く実装は `"noNE"` のような大文字小文字違いで回避されうる（rfc8725bis 2.11）。
- 対策: 受理アルゴリズムを呼び出し側で allowlist 指定。`none` は既定で拒否。RFC 9068 は JWT アクセストークンで `alg=none` の拒否を MUST とする。
- 実例:
  - Tim McLean「Critical vulnerabilities in JSON Web Token libraries」（Auth0ブログ、初出 2015-03-31）— 複数ライブラリが `none` を検証済み扱い。https://auth0.com/blog/critical-vulnerabilities-in-json-web-token-libraries/
  - CVE-2022-23540（jsonwebtoken ≤8.5.1、`algorithms` 未指定時に `none` 既定で署名検証バイパス。v9.0.0で修正。NVD公開 2022-12-22）
  - CVE-2025-46345（Auth0 Account Link Extension 2.3.4–2.6.6 が JWT 署名を検証しない。NVD 2025-05-01）
- 出典: RFC 8725 §2.1/§3.1/§3.2 https://www.rfc-editor.org/rfc/rfc8725.html 、draft-ietf-oauth-rfc8725bis-10 §2.11 https://datatracker.ietf.org/doc/html/draft-ietf-oauth-rfc8725bis 、RFC 9068 https://www.rfc-editor.org/rfc/rfc9068.html

### 1.2 アルゴリズム混同（RS256 公開鍵を HS256 の秘密として使う）
- 何が起きる: サーバが RS256 を期待しているのに `alg: HS256` のトークンを受け取り、検証鍵（RSA公開鍵＝公開情報）を HMAC 秘密として使ってしまう → 攻撃者が公開鍵で署名した偽造トークンが通る。
- 関与: header `alg`、鍵の種別
- 根本原因: 「鍵」と「アルゴリズム」が束縛されていない。トークンの `alg` を信用。
- 対策: 1鍵1アルゴリズム（RFC 8725 §3.1 “each key MUST be used with exactly one algorithm”）、allowlist、対称/非対称を混在させない（PyJWT ドキュメントも明記）。
- 実例:
  - CVE-2015-9235（jsonwebtoken <4.2.2。NVD 2018-05-29）
  - CVE-2016-10555（jwt-simple ≤0.3.0）
  - CVE-2022-23541（jsonwebtoken ≤8.5.1、鍵取得関数次第で非対称公開鍵を HS256 で検証）
  - CVE-2022-29217（PyJWT <2.4.0、`get_default_algorithms()` 使用時。NVD 2022-05-24）
  - CVE-2024-33663（python-jose ≤3.3.0、OpenSSH ECDSA 鍵等で混同。NVD 2024-04-26）
- 出典: 上記 Auth0 ブログ、RFC 8725 §3.1、https://pyjwt.readthedocs.io/en/stable/api.html

### 1.3 `kid` インジェクション（パストラバーサル / SQL）
- 何が起きる: `kid` をそのままファイルパスやSQLに連結 → `../../dev/null` で空鍵を読ませ、空文字の HMAC 鍵で偽造／SQLiで任意の鍵値を返させる。
- 関与: header `kid`
- 根本原因: 署名検証「前」の未検証ヘッダ値で鍵探索を行い、かつ入力検証をしていない。
- 対策: `kid` は不透明な識別子として allowlist / 固定マップで引く。RFC 8725 §3.10「SQL/LDAPインジェクションを生まないこと」。
- 実例: 特定製品の CVE は確認できず **[未検証]**。関連: CVE-2025-65945（auth0/node-jws ≤3.2.2 と 4.0.0。HMAC 秘密の lookup にヘッダ/ペイロードの利用者データを使う場合に署名検証バイパス。NVD 2025-12-04）。学習用の公開例として PentesterLab 解説 https://pentesterlab.com/blog/jwt-vulnerabilities-attacks-guide （二次資料）。
- 出典: RFC 8725 §2.9/§3.10

### 1.4 `jku` / `x5u` / 埋め込み `jwk` ヘッダの信頼
- 何が起きる: トークン内で「この鍵で検証せよ」と指示される → 攻撃者が自分の鍵（またはURL）を指定して自己署名トークンを通す。`jku`/`x5u` の取得は SSRF にもなる。
- 関与: header `jku`, `x5u`, `jwk`, `x5c`
- 根本原因: 検証鍵の信頼の起点（trust anchor）をトークン自身に委ねている。
- 対策: 鍵は事前設定した issuer の JWKS（メタデータ）からのみ取得。ヘッダURLは無視するか厳格 allowlist、Cookie 送信なし（RFC 8725 §3.10）。rfc8725bis §3.10 は「AS はホスト名の解決先を確認しなければならない（MUST）」と SSRF 対策を強化。Microsoft.IdentityModel の `ValidateIssuerSigningKey` 説明も「トークンが検証用公開鍵を含む場合があるので署名鍵自体を検証することが重要」と述べる（既定 `false`）。
- 実例: CVE-2018-0114（Cisco node-jose <0.11.0、JWS ヘッダ埋め込み JWK を信頼して再署名可能。NVD 2018-01-04）
- 出典: RFC 8725 §3.10、https://learn.microsoft.com/en-us/dotnet/api/microsoft.identitymodel.tokens.tokenvalidationparameters.validateissuersigningkey

### 1.5 `aud` 未検証とサービス間のトークン差し替え（substitution）
- 何が起きる: サービスA宛のトークンをサービスBに提示して通る（RFC 8725 §2.7 substitution）。
- 関与: claim `aud`
- 根本原因: `aud` 検証が任意設定のライブラリで設定し忘れ／`aud` の型（配列）処理バグ。
- 対策: 同一 issuer が複数 RP に発行するなら `aud` 必須かつ RP 側で検証 MUST（RFC 8725 §3.9）。RFC 9700 §2.3「アクセストークンは特定 RS に audience 制限すべき（SHOULD）」「宛先でなければ RS は MUST 拒否」。RFC 8707 の `resource` で発行時に宛先を束縛。
- 実例:
  - CVE-2020-26160（jwt-go <4.0.0-preview1、`aud` が `[]string` のとき型アサーション失敗で `""` 扱い。NVD 2020-09-30）
  - Storm-0558（§2.1）も「どの鍵・どの発行体のトークンを受理するか」のスコープ検証欠如で、広義の substitution。
- 出典: RFC 8725、RFC 9700 https://www.rfc-editor.org/rfc/rfc9700.html （2025年1月, BCP 240）、RFC 8707

### 1.6 マルチテナントでの `iss`（テナント）未検証
- 何が起きる: 共通鍵で署名するマルチテナント IdP の場合、別テナントで発行された「同じ aud」のトークンが通る。
- 関与: `iss`, `tid`（Entra）
- 根本原因: 署名鍵がテナント共通なので「署名OK＝自テナント」ではない。
- 対策: `iss`（およびテナントID）を許可リストで検証し、データのテナントとトークンのテナントを突合。Microsoft: 「`tid` がデータを保存したテナントと一致することを常に確認」。`ValidateIssuer`（既定 `true`）の説明: 「IdP が複数テナントを同じ鍵で署名する場合の forwarding 攻撃を緩和」。
- 実例: CVE-2025-55241 Entra「Actor tokens」（§2.2、発信元テナントの検証欠如）。CVE-2024-53861（PyJWT 2.10.0 の `iss` 比較が部分文字列一致になったバグ。NVD 2024-11-29）。
- 出典: https://learn.microsoft.com/en-us/entra/identity-platform/claims-validation （ms.date 2025-03-21）、https://learn.microsoft.com/en-us/dotnet/api/microsoft.identitymodel.tokens.tokenvalidationparameters.validateissuer

### 1.7 ID トークンをアクセストークンとして使う
- 何が起きる: クライアント向けの ID トークン（`aud`=client_id）を API が受理 → 任意のRPが入手したIDトークンで API にアクセスできる。
- 関与: `aud`, `typ`, `scp`
- 根本原因: API が「同じ IdP が署名した JWT」なら何でも受ける。
- 対策: RFC 9068 の `typ: at+jwt` を要求、`aud` を API 自身に限定、`scp`/`roles` の存在確認。Microsoft:「ID トークンでは `scp` がないので不在を確認せよ」。
- 実例: CVE-2025-68129（Auth0-PHP SDK v8.0.0–v8.17.0、audience 検証不備で ID トークンをアクセストークンとして受理しうる。NVD 2025-12-17）
- 出典: RFC 9068 https://www.rfc-editor.org/rfc/rfc9068.html （2021年10月）、Microsoft claims-validation

### 1.8 Cross-JWT confusion（`typ` 未確認）
- 何が起きる: 同じ発行体の別用途 JWT（ログアウトトークン、ID-JAG、Txn-Token等）が別文脈で受理される。
- 関与: header `typ`
- 根本原因: 用途ごとの検証ルールが相互排他になっていない。
- 対策: RFC 8725 §3.11 明示的型付け（例 `at+jwt`, `oauth-id-jag+jwt`, `txntoken+jwt`）、§3.12「検証ルールは相互排他に書かねばならない（MUST）」。注意: Microsoft.IdentityModel は `ValidTypes` 未設定だと `typ` を検証しない（既定 null）。Entra のアクセストークン `typ` は「常に `JWT`」なので `typ` だけでは区別できない。
- 出典: RFC 8725、https://learn.microsoft.com/en-us/dotnet/api/microsoft.identitymodel.tokens.tokenvalidationparameters 、https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference

### 1.9 `exp`/`nbf` 未検証・過大な leeway
- 何が起きる: 期限切れトークンや失効させたはずのセッションが使い続けられる。
- 関与: `exp`, `nbf`, `iat`
- 根本原因: 多くのライブラリが「claim が存在すれば検証」＝存在しなければ素通り（PyJWT・golang-jwt v5 は既定で `exp` 任意）。エラー判定の誤り。
- 対策: `exp` を必須化（PyJWT `require`、golang-jwt `WithExpirationRequired`、MS は `RequireExpirationTime` 既定 true）。leeway は RFC 7519 §4.1.4「通常数分以内」。
- 実例:
  - CVE-2024-51744（golang-jwt: `ErrTokenExpired` だけを `errors.Is` で見ると同時に返る署名不正エラーを見落とす。NVD 2024-11-04）
  - CVE-2025-46344（Auth0 Next.js SDK 4.0.1–4.5.0、セッション JWE に内部 exp が無く、Cookie 失効後も JWE は有効。NVD 2025-04-29）
- 出典: RFC 7519 https://www.rfc-editor.org/rfc/rfc7519.html 、各ライブラリ文書（§3）

### 1.10 リプレイ（`jti`）
- 何が起きる: 盗んだトークン（特に client assertion、ID-JAG、ワンタイム用途）を再送。
- 関与: `jti`, `exp`, `iat`
- 根本原因: bearer トークンは提示者を問わない。`jti` 記録をしていない。
- 対策: 一回性が必要な JWT は `jti` を `exp` までキャッシュして再利用拒否（RFC 7519 §4.1.7）。sender-constrained（DPoP RFC 9449 / mTLS RFC 8705、RFC 9700 §2.2.1 SHOULD）。ID-JAG は `jti` 必須。
- 関連実例: CVE-2026-1035（Keycloak、厳格 refresh token rotation 時の検証と更新が非アトミックで並行リクエストにより同一 refresh token から複数アクセストークン発行。NVD 2026-01-21）
- 出典: RFC 7519、RFC 9700、draft-ietf-oauth-identity-assertion-authz-grant-06

### 1.11 JWE/JWS 混同（sign/encrypt confusion）と「Psychic Signatures」
- sign/encrypt confusion: 公開鍵で暗号化した JWE（誰でも作れる）を、署名済み JWS と同等に扱ってしまう。Tom Tervoort（Secura）Black Hat USA 2023「Three New Attacks Against JSON Web Tokens」で sign/encrypt confusion・polyglot token・billion hash attack を発表。https://i.blackhat.com/BH-US-23/Presentations/US-23-Tervoort-Three-New-Attacks-Against-JSON-Web-Tokens-whitepaper.pdf
  - 実例: CVE-2023-51774（Ruby json-jwt 1.16.3、JWE で `JSON::JWT.decode` の同一性チェックをバイパス。NVD 2024-02-29）
  - 対策: rfc8725bis §3.3「ライブラリは Unsecured/JWS/JWE/Nested を区別可能にしなければならない（MUST）」、§3.14 形式チェック（JSONシリアライズを Compact として誤解析させる format confusion 対策）。
  - polyglot 実例: CVE-2022-39227（python-jwt <3.3.4、JWT 内容を秘密鍵なしで偽造可能。NVD 2022-09-23）
- Psychic Signatures: CVE-2022-21449。Java 15–18 の ECDSA 検証が r=s=0 を拒否せず、任意メッセージ・任意鍵で「有効」。ES256 の JWT、OIDC ID トークン、SAML、WebAuthn に波及。原因は Java 15 での EC 実装の C++→Java 書き換え。報告 2021-11-11、修正 2022-04-19（April 2022 CPU）。Oracle CVSS 7.5 / ForgeRock 社内評価 10.0。NVD は Java SE 17.0.2, 18 を記載。
  - 出典: Neil Madden https://neilmadden.blog/2022/04/19/psychic-signatures-in-java/ 、NVD CVE-2022-21449
  - 教訓: 「標準ライブラリの暗号プリミティブ」自体も検証対象。ランタイム更新が JWT セキュリティの一部。

### 1.12 Claim パース差異（重複 claim、JSON パーサ差）
- 何が起きる: `{"role":"user","role":"admin"}` を検証層と利用層で別解釈。
- 根本原因: JSON 重複キーの優先順位（先勝ち/後勝ち）、文字切り詰め、数値表現がパーサごとに異なる（Bishop Fox, Jake Miller「An Exploration of JSON Interoperability Vulnerabilities」2021-02-25 https://bishopfox.com/blog/json-interoperability-vulnerabilities ）。
- 仕様: RFC 7519 §4「JWT パーサは重複 claim 名を拒否するか、字句的に最後のものを返す JSON パーサを使わなければならない（MUST）」。RFC 8725 §2.6/§3.7 は UTF-8 以外のエンコーディング拒否。
- 対策: 検証したオブジェクトをそのまま下流に渡す（再パースしない）、重複キーを拒否するパーサを選ぶ。
- 注: rfc8725bis-10 には重複 claim 専用の新節は無い（同ドラフト Appendix A 確認、WebFetch 要約による）。

### 1.13 未検証 email を信頼（nOAuth）
- 何が起きる: Azure AD マルチテナントアプリで `email` claim をユーザー識別子／アカウント統合キーに使用 → 攻撃者が自テナントで email 属性を被害者のアドレスに変更 → 被害者アカウント乗っ取り。
- 関与: `email`（Entra では mutable かつ unverified）
- 対策: `sub`（Entra なら `oid`+`tid`）を識別子に。OIDC Core §5.7「`iss`+`sub` の組だけが安定した一意識別子。`email`・`phone_number`・`preferred_username`・`name` を一意識別子に使ってはならない（MUST NOT）」。Microsoft は `xms_edov` optional claim と `RemoveUnverifiedEmailClaim` を提供。
- 詳細は §2.3。
- 出典: https://www.descope.com/blog/post/noauth （2023-06-20）、https://openid.net/specs/openid-connect-core-1_0.html

### 1.14 可変（mutable）な claim をキーにする
- `upn` は一意だが変わるので認可に使わない、`email`/`preferred_username`/`unique_name` は表示専用（Microsoft 警告）。`sub` は Entra ではアプリごとのペアワイズ値、`oid` はテナント内でアプリ横断の不変値。
- 関連実例: CVE-2025-1391（Keycloak organization mapper がユーザー名/メールのドメイン一致だけで組織所属 claim を付与。NVD 2025-02-17）＝「属性の見た目」から権限 claim を作る危険。Cognito の書き込み可能 custom attribute（`custom:role` 等）による権限昇格（Yassine Aboukir, HITB 2023 https://conference.hitb.org/hitbsecconf2023hkt/materials/D2T1%20-%20Hunting%20for%20Amazon%20Cognito%20Security%20Misconfigurations%20-%20%20Yassine%20Aboukir.pdf 「custom attribute は read-only にしない限り既定で書き込み可能」）。
- 出典: Microsoft claims-validation / access-token-claims-reference

### 1.15 失効後も残る groups/roles（stale claims）
- 何が起きる: 自己完結型 JWT の claim は発行時点のスナップショット。グループ削除・無効化後も `exp` まで有効。
- 事例・データ点:
  - Entra CAE: グループメンバーシップ／CA ポリシー変更の反映は「最大1日」、即時反映には refresh token 失効（`revoke-mgusersigninsession`）。CAE セッションではアクセストークン寿命が最大28時間に延びる（代わりに critical event で失効）。https://learn.microsoft.com/en-us/entra/identity/conditional-access/concept-continuous-access-evaluation （ms.date 2026-04-08）
  - Entra groups overage: JWT は200グループ超、SAML は150超で `groups` を出さず `_claim_names`/`_claim_sources`（Graph 参照）に置換 — 「HTTPヘッダのサイズ制限内に収めるため」。
  - CVE-2025-14559（Keycloak Token Exchange が無効化ユーザーにもアクセス/リフレッシュトークンを発行。NVD 2026-01-21）
- 対策: 短命アクセストークン、重要操作はサーバ側で再評価、CAEP/SSF による失効イベント購読（§5.4）。

---

## 2. 実インシデント（タイムラインと教訓）

### 2.1 Storm-0558（2023年、MSA コンシューマ鍵で Azure AD トークン偽造）
タイムライン（CSRB 報告書 “Review of the Summer 2023 Microsoft Exchange Online Intrusion”, 表紙日付 2024-03-20、DHS 公表 2024-04-02）:
- 2016: 問題の MSA（コンシューマ）署名鍵作成。2021年3月に退役予定だったが遅延。
- 2021: 大規模クラウド障害（手動ローテーション起因）後、Microsoft はコンシューマ MSA 鍵のローテーションを完全停止。鍵の年齢を警告する仕組みもなし。
- 2023年5月〜: Exchange Online 侵入。22組織＋個人503アカウント（うち少なくとも391は米国）。商務長官、駐中国米国大使などが被害。
- 2023-06-15/16: 国務省 SOC が自作ルール “Big Yellow Taxi”（MailItemsAccessed ログ。Purview Audit Premium 契約で利用可能だった）で検知、6/16 に Microsoft へ通報。
- 2023-06-24: Microsoft が盗まれた鍵を無効化。6/26–27 にコンシューマ鍵で署名されたトークンでエンタープライズにアクセスしていると判明。
- 2023-07: Microsoft 公表（MSRC https://www.microsoft.com/en-us/msrc/blog/2023/07/microsoft-mitigates-china-based-threat-actor-storm-0558-targeting-of-customer-email 、Security Blog 2023-07-14 https://www.microsoft.com/en-us/security/blog/2023/07/14/analysis-of-storm-0558-techniques-for-unauthorized-email-access ）。Microsoft は約25組織と記載（CSRB は22組織）。
- 2023-09-06: Microsoft「crash dump（2021年4月）に鍵が混入→侵害されたエンジニアアカウント経由」を最有力仮説として公表。
- 2024-03-12: Microsoft が同記事を更新し「鍵を含む crash dump は見つかっていない」と訂正。CSRB は訂正の遅れを批判。
検証上の欠陥（JWT 設計の教訓の核心）:
- Microsoft: 2018年9月にコンシューマ/エンタープライズ共通の鍵メタデータ公開エンドポイントを導入したが、ライブラリを「スコープ検証を自動で行う」よう更新しなかった。「メールシステムの開発者はライブラリが完全な検証をしていると誤って想定」し、必要な issuer/scope 検証を追加しなかった → エンタープライズのメールがコンシューマ鍵署名トークンを受理。https://www.microsoft.com/en-us/msrc/blog/2023/09/results-of-major-technical-investigations-for-storm-0558-key-acquisition
- CSRB: 原因は共通 OIDC エンドポイント（両系統の有効鍵を列挙）に対し SDK が consumer と enterprise の鍵を区別するよう更新されなかったこと。「2016 MSA 鍵＋検証の欠陥で、事実上あらゆる Exchange Online アカウントにフルアクセス可能」。「侵入は防止可能だった」「Microsoft のセキュリティ文化は不十分」。報告時点で鍵の入手経路は不明。
- CSRB が挙げた他CSPのベストプラクティス: 自動定期ローテーション、HSM 等での隔離保管、stateful なトークン検証、鍵スコープの限定（顧客単位など）、偽造検知用の独自データ、操作/セッション束縛トークン。Google は stateful トークン化と完全自動ローテーションを採用。
- 出典: CSRB PDF https://www.cisa.gov/sites/default/files/2025-03/CSRBReviewOfTheSummer2023MEOIntrusion508.pdf 、CISA ページ https://www.cisa.gov/resources-tools/resources/CSRB-Review-Summer-2023-MEO-Intrusion
- 教訓: (1)「署名が正しい」≠「受理すべき」。鍵→発行体→テナント→audience の対応を検証する。(2) ライブラリの既定に「どこまで検証しているか」を仮定しない。(3) 鍵ローテーションを止めることが最大のリスクになる。(4) 監査ログはプレミアム機能に置かない（CSRB 指摘）。
- その後の関連 API: Microsoft.IdentityModel に `EnableAadSigningKeyIssuerValidation`（署名鍵の issuer とトークンの issuer を照合）拡張がある。導入時期は **[未検証]**。https://learn.microsoft.com/en-us/dotnet/api/microsoft.identitymodel.tokens.tokenvalidationparameters

### 2.2 CVE-2025-55241 Entra ID「Actor tokens」（Dirk-jan Mollema）
- Actor token とは: Microsoft バックエンドの “Access Control Service” が発行するサービス間通信用トークン。Exchange 等がユーザーに代わって Exchange Online・SharePoint・Azure AD Graph にアクセスする際に使用。Exchange は Actor token を **署名なしの JWT（impersonation token）** に包み、対象ユーザーの `nameid`（= `netId`、トークンでは `puid`）を入れる。
- 性質: 有効期限は発行から24時間、期間中失効不可、Conditional Access を完全にバイパス、要求・生成・使用時にログが出ない（被害テナント側に記録が残らない）。
- 欠けていた検証: レガシー Azure AD Graph API が「発信元テナントを適切に検証しなかった」→ 攻撃者テナントで取得した Actor token で他テナントのユーザーを偽装可能。`netId` は連番的で総当たりが現実的。Global Admin を偽装すればテナント完全掌握（M365/Azure へも波及）。Microsoft のテレメトリでは悪用は検出されず。
- タイムライン: 2025-07-14 MSRC へ報告 → 07-17 グローバル修正 → 07-23 解決確認 → 08-06 Service Principal 資格情報での Azure AD Graph 向け Actor token 要求をブロック → 09-04 CVE-2025-55241 発行（NVD: “Azure Entra ID Elevation of Privilege Vulnerability”）→ 09-17 ブログ公開。
- 検知: 変更系操作のみ AuditLogs に「偽装ユーザーの UPN＋呼出元サービス表示名（Exchange 等）」として残る。読み取りはログなし。
- 出典: https://dirkjanm.io/obtaining-global-admin-in-every-entra-id-tenant-with-actor-tokens/ 、https://msrc.microsoft.com/update-guide/vulnerability/CVE-2025-55241
- 教訓: 署名なしの内部トークン、テナント（`iss`/`tid`）未検証、失効不能・ログなしの長命トークンという「アンチパターンの合成」。エージェント時代の「代理トークン（act）」設計に直結する。

### 2.3 nOAuth（Descope、2023年6月）
- 2023-04-11 Descope が Microsoft に報告 → 04-12 チケット → 04-18 ガイダンス・修正方針回答、claims ドキュメント更新 → 2023-06-20 修正と共同公開。
- 影響例（社名非公開）: 月間数百万ユーザーのデザインアプリ、上場 CX 企業、マルチクラウドコンサル等。認証プロバイダ2社も検証なしで email によるアカウント統合をしていた。
- Microsoft の対策: `xms_edov`（email ドメイン所有者検証済みか）、`RemoveUnverifiedEmailClaim`。
- 出典: https://www.descope.com/blog/post/noauth
- 教訓: 「IdP が署名した claim」＝「IdP が検証した事実」ではない。`email_verified` 等の意味も IdP ごとに異なる（OIDC Core §5.1 は検証手段を文脈依存と明記）。

### 2.4 Sign in with Apple（Bhavuk Jain、2020年）
- 2020年4月に発見。Apple が「任意のメールアドレス」に対して Apple の鍵で正しく署名された JWT を発行してしまう不具合 → 追加検証のないサードパーティアプリで完全なアカウント乗っ取りが可能だった。Apple Security Bounty で $100,000。Apple はログ調査で悪用なしと回答。記事公開 2020-05-30。
- 出典: https://bhavukjain.com/blog/2020/05/30/zeroday-signin-with-apple
- 教訓: 署名検証は「発行プロセスの正しさ」を保証しない。IdP 側バグは RP 側で防げない → 高リスク操作は追加確認、異常検知。

### 2.5 2024–2026 の注目事例（出典確認済みのもののみ）
| 日付(NVD公開) | 事例 | 要点 |
|---|---|---|
| 2024-01-09 | CVE-2024-21319 Microsoft Identity DoS | NVD 記載は「Microsoft Identity Denial of service vulnerability」のみ。python-jose CVE-2024-33664 の NVD 記載が「CVE-2024-21319 と類似の JWT bomb（高圧縮 JWE）」としているので、JWE 解凍型の DoS と推定 **[詳細未検証]** |
| 2024-03-09 | CVE-2024-28176 panva/jose | JWE 復号後の展開（解凍）でリソース枯渇 |
| 2024-11-04 | CVE-2024-51744 golang-jwt | エラー判定の誤用で無効署名を受理しうる |
| 2024-11-29 | CVE-2024-53861 PyJWT 2.10.0 | `iss` 部分一致バグ |
| 2025-02-17 | CVE-2025-1391 Keycloak | 組織 claim の誤付与 |
| 2025-03-21 | CVE-2025-30204 golang-jwt | 大量の `.` を含むヘッダで O(n) 割り当て DoS |
| 2025-05-01 | CVE-2025-46345 Auth0 Account Link Ext. | JWT 署名未検証 |
| 2025-09-04 | CVE-2025-55241 Entra ID | Actor token（§2.2） |
| 2025-12-04 | CVE-2025-65945 auth0/node-jws | HMAC 秘密探索に未検証データ |
| 2025-12-17 | CVE-2025-68129 Auth0-PHP | ID トークンをアクセストークンとして受理しうる |
| 2026-01-21 | CVE-2025-14559 Keycloak | Token Exchange で無効ユーザーにトークン発行 |
| 2026-01-21 | CVE-2026-1035 Keycloak | refresh token 再利用制限の競合状態 |
| 2026-10-13 | CVE-2026-85473 auth0/java-jwt | 範囲外の `exp`/`nbf`/`iat` で署名検証前にスレッド終了（DoS） |
- 出典: 各 NVD、Okta セキュリティアドバイザリ一覧 https://trust.okta.com/security-advisories
- Keycloak 公式ドキュメントの注意: 「レガシーの external-to-internal token exchange は `subject_token` の `aud` を検証しない」→ 他クライアント宛の外部 ID トークンも署名・期限が通れば受理。https://www.keycloak.org/securing-apps/token-exchange
- Keycloak 26.2.0（2025年4月）: OIDC Core の改訂に合わせ `private_key_jwt`/`client_secret_jwt` のクライアントアサーションで単一 audience を既定で強制。https://www.keycloak.org/2025/04/keycloak-2620-released
- Cognito: 研究（HITB 2023, Aboukir）で書き込み可能 custom attribute による権限昇格、SignUp API 有効化による認証バイパスを指摘（§1.14）。AWS 公式ブログも「custom attribute の値は `UpdateUserAttributes` でユーザー自身が更新できる場合がある」と記載 https://aws.amazon.com/blogs/security/saas-authentication-identity-management-with-amazon-cognito-user-pools 。2024–2026 の新規 Cognito 研究は本調査では一次確認できず **[未検証]**。

---

## 3. ライブラリ別の落とし穴（既定値）

| ライブラリ | アルゴリズム指定 | aud / iss | 時刻 | 主な過去CVE |
|---|---|---|---|---|
| jsonwebtoken (Node) | `algorithms` 未指定時は鍵種別から既定（secret→HS256/384/512、RSA→RS*、EC→ES*）。v9.0.0 で `verify()` の `none` 既定サポート削除（CVE-2022-23540） | `audience`/`issuer` は「指定した場合のみ」検証 | `clockTolerance`、`ignoreExpiration`、`maxAge` | CVE-2015-9235, 2022-23539/23540/23541 |
| PyJWT | `decode()` で `algorithms` 未指定は `DecodeError`（PyJWK 鍵の場合は鍵の alg）。「トークンの `alg` から algorithms を計算するな」 | `audience=None` でトークンに `aud` があれば `InvalidAudienceError`（ソース確認）。`issuer=None` なら iss 未検証。`strict_aud` 既定 False | `exp`/`nbf` は存在時のみ検証、`require` で必須化。`leeway` 既定0 | CVE-2022-29217, CVE-2024-53861 |
| jose (panva) | `alg:none` は常に拒否。`algorithms` 未指定時は「鍵に適用可能な全アルゴリズム」 | `audience`/`issuer`/`subject`/`typ` は指定時のみ必須化 | `clockTolerance`、`maxTokenAge` | CVE-2024-28176 |
| Microsoft.IdentityModel (.NET) | `ValidAlgorithms` 任意。`RequireSignedTokens` 既定 true | `ValidateAudience` 既定 true、`RequireAudience` true、`ValidateIssuer` true。`ValidTypes` 未設定なら `typ` 未検証。`ValidateIssuerSigningKey` 既定 **false**。`TryAllIssuerSigningKeys` 既定 true | `ValidateLifetime` true、`RequireExpirationTime` true、**`ClockSkew` 既定 300 秒** | CVE-2024-21319 |
| Spring Security（Resource Server/Nimbus） | 既定は **RS256 のみ**信頼。`jws-algorithms` で変更 | `issuer-uri` 設定時 `iss` 検証。**`aud` は既定で未検証**、`spring.security.oauth2.resourceserver.jwt.audiences` か `JwtClaimValidator` で追加。RFC 9068 向け `createAtJwtValidator()` | `exp`/`nbf` 検証、clock skew 既定 60 秒 | （本調査で特定せず） |
| golang-jwt v5 | `WithValidMethods` を「強く推奨」。`none` は `UnsafeAllowNoneSignatureType` を鍵に渡した時のみ | `WithAudience`/`WithIssuer`/`WithSubject` 指定時に必須化 | **`exp` は既定で任意**（`WithExpirationRequired`）、`WithLeeway` | CVE-2020-26160（旧 jwt-go）, CVE-2024-51744, CVE-2025-30204 |

出典:
- jsonwebtoken README https://github.com/auth0/node-jsonwebtoken/blob/master/README.md 、NVD 各CVE
- PyJWT https://pyjwt.readthedocs.io/en/stable/api.html 、ソース https://github.com/jpadilla/pyjwt/blob/master/jwt/api_jwt.py （`_validate_aud`/`_validate_iss`）、https://github.com/jpadilla/pyjwt/blob/master/jwt/api_jws.py
- jose https://github.com/panva/jose/blob/main/docs/jwt/verify/interfaces/JWTVerifyOptions.md
- Microsoft https://learn.microsoft.com/en-us/dotnet/api/microsoft.identitymodel.tokens.tokenvalidationparameters （v8.23.0 ページ）および各プロパティページ
- Spring https://docs.spring.io/spring-security/reference/servlet/oauth2/resource-server/jwt.html
- golang-jwt https://pkg.go.dev/github.com/golang-jwt/jwt/v5

横断的な教訓: 「`aud`/`iss` は渡さなければ検証されない」系（jsonwebtoken, jose, golang-jwt, Spring の aud）と「既定で検証」系（.NET）が混在。テックリードはライブラリ既定に依存せず、プロジェクト共通の検証ラッパー（alg allowlist・iss・aud・typ・exp必須・leeway上限）を1か所に置くのが Storm-0558 の教訓とも整合。

---

## 4. AI エージェントと委任認可（2026年11月時点）

### 4.1 MCP 認可仕様（現行版 2026-07-28）
- 現行版: `2026-07-28`（`/specification/latest` が 2026-07-28 を参照、前版は 2025-11-25）。https://modelcontextprotocol.io/specification/latest/basic/authorization 、変更点 https://modelcontextprotocol.io/specification/2026-07-28/changelog
- 適用範囲: 認可は OPTIONAL。HTTP 系トランスポートは本仕様に従う SHOULD、STDIO は従わず環境から資格情報取得 SHOULD NOT。
- 役割: MCP サーバ＝OAuth 2.1 resource server、MCP クライアント＝OAuth 2.1 client。準拠先は draft-ietf-oauth-v2-1-13、RFC 6750/8414/7591/8707/9728/9207、Client ID Metadata Documents ドラフト、OIDC Discovery。
- RFC 9728: MCP サーバは Protected Resource Metadata を実装 MUST、クライアントは AS 発見に使用 MUST。401 の `WWW-Authenticate` に `resource_metadata` と `scope` を含める。
- RFC 8707: クライアントは `resource` を認可要求とトークン要求の両方に含める MUST、MCP サーバの canonical URI を使う MUST、AS の対応有無にかかわらず送る MUST。
- トークン処理（原文要旨）: MCP サーバは OAuth 2.1 §5.2 に従い検証 MUST、「自分宛の audience として発行されたことを RFC 8707 §2 に従い検証 MUST」、無効/期限切れは 401 MUST。「MCP サーバは他のトークンを受理も中継もしてはならない（MUST NOT accept or transit any other tokens）」。
- Token passthrough 禁止（Security Considerations「Access Token Privilege Restriction」）: 「audience claim に自分を含まないトークンは拒否 MUST」「上流 API には上流 AS が発行した別トークンを使う。MCP クライアントから受け取ったトークンをパススルーしてはならない（MUST NOT）」。https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations
- Confused deputy: 静的 client ID を使う MCP プロキシサーバは、動的登録クライアントごとにユーザー同意を取得してから第三者 AS に転送 MUST。Best Practices 文書は同意 Cookie/state を同意承認後まで設定してはならない（MUST NOT）と記載。https://modelcontextprotocol.io/specification/latest/basic/security_best_practices
- その他 2026-07-28 の認可関連変更: RFC 9207 `iss` 認可応答パラメータ（AS は SHOULD、クライアントは存在時に検証 MUST、mix-up 対策）、PKCE S256 MUST、`code_challenge_methods_supported` 不在なら中止 MUST、Dynamic Client Registration を Deprecated（Client ID Metadata Documents 優先）、資格情報を issuer で鍵付けし別 AS で再利用禁止、403 `insufficient_scope` による step-up。
- 拡張: Enterprise-Managed Authorization（EMA）が 2026-06-18 に Stable（MCP Blog, Paul Carleton）。IdP から ID-JAG を取得し MCP サーバの AS でアクセストークンへ交換、ユーザーごとの同意画面なし。初の対応 IdP は Okta（Cross App Access）、クライアントは Anthropic（Claude, Claude Code, Cowork）・VS Code（preview）。https://blog.modelcontextprotocol.io/posts/enterprise-managed-auth 、拡張一覧 https://github.com/modelcontextprotocol/ext-auth

### 4.2 OAuth Token Exchange（RFC 8693, 2020年1月）
- `subject_token` = 「代わりに行動される側」の身元、`actor_token` = 「権限を委任される側」の身元。
- impersonation（A が B の全権を持ち、受信側は B と区別できない）vs delegation（A は B と別の身元を保つ）。エージェントは原則 delegation。
- `act`: 最外側の `act` が現在の actor、ネストは過去の actor で「情報提供のみ、アクセス制御判断に使ってはならない」。`may_act`: ある主体が別主体の代理になることを許可されている旨の表明。
- 出典: https://www.rfc-editor.org/rfc/rfc8693.html
- 実装例: Keycloak の `delegation:client`（AI エージェント等のアプリがユーザーを代理）/`delegation:user` スコープ。同意後 subject token に `may_act`、交換後トークンに `act`（Preview 機能、既定無効）。https://www.keycloak.org/securing-apps/token-exchange

### 4.3 IETF ドラフトの状況（datatracker API で 2026-11-17 確認）
| 文書 | 版 | 状態 | 要点 |
|---|---|---|---|
| draft-ietf-oauth-identity-assertion-authz-grant（ID-JAG / XAA） | -06（2026-10-31） | OAuth WG Document | §4.4 |
| draft-ietf-oauth-transaction-tokens | -11（2026-08-21） | WG Consensus: Waiting for Write-Up | §4.5 |
| draft-ietf-oauth-identity-chaining | -17 | Submitted to IESG → RFC Editor Queue | ドメイン横断の認可連鎖（RFC 8693 + RFC 7523） |
| draft-ietf-oauth-rfc8725bis（JWT BCP 改訂） | -10（2026-08-21） | RFC Editor Queue | §1 参照 |
| draft-ietf-oauth-v2-1 | -17 | WG Document | MCP は -13 を参照 |
| draft-ietf-oauth-client-id-metadata-document | -03 | WG Document | MCP は -00 を参照 |
| draft-oauth-ai-agents-on-behalf-of-user（WSO2 Senarath/Dissanayaka） | -02（2025-08-26） | 個人提出・**Expired** | §4.6 |
| draft-klrc-aiagent-auth「AI Agent Authentication and Authorization」 | -03 | **Replaced** → draft-ietf-wimse-aims | — |
| draft-ietf-wimse-aims「AI Identity Management System」 | -01（2026-11-02） | WIMSE WG Document | 新プロトコルを作らず WIMSE/OAuth 既存標準の適用を整理 |
| draft-ietf-wimse-arch | -09 | WIMSE WG Document | ワークロード ID アーキテクチャ |
- 出典: `https://datatracker.ietf.org/doc/<name>/`（API `https://datatracker.ietf.org/api/v1/doc/document/<name>/`）

### 4.4 ID-JAG（Identity Assertion JWT Authorization Grant）
- フロー: (1) OIDC/SAML SSO → (2) IdP で RFC 8693 交換（`requested_token_type=urn:ietf:params:oauth:token-type:id-jag`、`subject_token`=ID トークン or SAML、`audience`=リソース AS の issuer、`resource` 推奨）→ (3) リソース AS で RFC 7523 JWT bearer grant。
- header `typ: oauth-id-jag+jwt`（MUST）。必須 claim: `iss`, `sub`, `aud`, `client_id`, `jti`, `exp`, `iat`。任意: `resource`, `scope`, `authorization_details`, `act`, `tenant`, `aud_tenant`, `aud_sub`, `auth_time`, `acr`, `amr`, `email`, `cnf` 等。
- リソース AS の MUST: 信頼する IdP 以外の `iss` は `invalid_grant`、マルチテナント issuer なら `tenant` 必須、`aud` は自 AS の issuer、`client_id` が認証済みクライアントと一致、発行アクセストークンを `resource` に限定。
- 出典: https://datatracker.ietf.org/doc/html/draft-ietf-oauth-identity-assertion-authz-grant-06

### 4.5 Transaction Tokens（Txn-Token）
- 信頼ドメイン内の呼び出し連鎖でユーザー・ワークロード・認可コンテキストを運ぶ短命（分単位以下）署名 JWT。`typ: txntoken+jwt` MUST。
- 必須: `iat`, `aud`（信頼ドメイン。外では受理 MUST NOT）, `exp`, `txn`, `sub`, `scope`, `req_wl`。推奨: `tctx`（不変の取引コンテキスト）, `rctx`（要求環境、例 発信IP）。
- 取得: TTS へ RFC 8693 交換（`requested_token_type=urn:ietf:params:oauth:token-type:txn_token`）。refresh token は発行しない／使えない。
- 伝搬: `Txn-Token` ヘッダ（Authorization ヘッダは使わない MUST NOT）、受け取った通りに下流へ。ワークロード自身の認証やアクセストークンとして使ってはならない。**逐語的にログに残してはならない（MUST NOT）**。
- 出典: https://datatracker.ietf.org/doc/html/draft-ietf-oauth-transaction-tokens-11

### 4.6 On-Behalf-Of for AI Agents（期限切れ個人ドラフト）
- 認可要求に `requested_actor`、トークン要求に `actor_token`（actor の `sub` 必須）。発行トークンは RFC 9068 準拠推奨、トップレベル `sub`=ユーザー、`azp`/`client_id`=クライアント、`act.sub`=エージェント。同意画面で actor と scope を明示 SHOULD。コードは user/client/actor に束縛。
- 位置づけ: IETF の合意文書ではない（Expired）。設計思想の参照に留める。
- 出典: https://datatracker.ietf.org/doc/html/draft-oauth-ai-agents-on-behalf-of-user-02

### 4.7 その他のガイダンス
- OpenID Foundation「Identity Management for Agentic AI」（2025年10月、AI Identity Management Community Group、著者 Tobin South）。MCP 等に対する現行ベストプラクティスと、エージェント ID・委任権限などの将来課題を整理。SSF による失効伝搬、IPSIE、FAPI に言及。https://openid.net/wp-content/uploads/2025/10/Identity-Management-for-Agentic-AI.pdf 、arXiv:2510.25819
- OWASP Top 10 for Agentic Applications 2026（2025-12-09公表）: ASI03「Identity & Privilege Abuse」＝委任権限・曖昧なエージェント ID・信頼前提による不正操作。https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026 、https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai
- NIST NCCoE コンセプトペーパー「Accelerating the Adoption of Software and AI Agent Identity and Authorization」（2026年2月ドラフト、意見募集 2026-04-02まで）。https://www.nccoe.nist.gov/sites/default/files/2026-02/accelerating-the-adoption-of-software-and-ai-agent-identity-and-authorization-concept-paper.pdf 。その後600超のコメントを受け、最初の実装ユースケースを DevSecOps プロジェクトでのソフトウェア開発ライフサイクルに設定（NCCoE ニュース。ページ直接取得は403、検索結果抜粋による **[一部未検証]**）。
- CoSAI「Agentic Identity and Access Management」（TSC 承認 2026-03-20、公開 2026年4月）: 委任トークンは秒〜分の短命かつ厳格スコープ SHOULD、集中失効サービス SHOULD、ランタイムは失効イベントを購読 SHOULD。段階導入 Phase1 で「全エージェントを ID として登録・共有アカウント廃止・不変の操作ログ」。https://www.coalitionforsecureai.org/wp-content/uploads/2026/04/agentic-identity-and-access-control.pdf
- Microsoft: 委任ユーザートークンでは `scp` で actor（クライアント）を認可、アプリ単位認可に `azp`/`appid` を使う場合は `idtyp=app` を確認（委任トークンは他者が取得しうるため）。Microsoft claims-validation。

### 4.8 「誰が・どのエージェントが・何を承認し・どこに対して」を運ぶ claim
| 問い | 主な claim | 根拠 |
|---|---|---|
| 誰がユーザーか | `iss`+`sub`（Entra: `tid`+`oid`）。ID-JAG の `sub`/`aud_sub`/`tenant`、Txn-Token の `sub` | OIDC Core §5.7、ID-JAG、Txn-Tokens |
| 誰がクライアント/エージェントか | `client_id`（RFC 9068 / ID-JAG 必須）、`azp`、`act.sub`（現在の actor）、`may_act`（代理許可）、Txn-Token の `req_wl`（要求ワークロード） | RFC 9068, RFC 8693 §4.1/4.4, Txn-Tokens |
| 何が承認されたか | `scope`/`scp`、`roles`、`authorization_details`（RFC 9396）、Txn-Token の `scope`・`tctx`、認証強度 `acr`/`amr`/`auth_time` | RFC 9068, ID-JAG, Txn-Tokens |
| どのリソース向けか | `aud`（RS 自身。MCP は RFC 8707 canonical URI）、`resource`（ID-JAG）、Txn-Token の `aud`=信頼ドメイン | MCP 仕様、RFC 8707, ID-JAG |
| 誰が持つべきか | `cnf`（DPoP/mTLS の鍵束縛） | RFC 9700 §2.2.1、ID-JAG |
- 重要: ネストした `act` は情報のみで認可判断に使わない（RFC 8693）。エージェントの身元を「ユーザートークンの借用」で表現しない（OWASP ASI03、CoSAI）。

---

## 5. 運用トピック

### 5.1 鍵ローテーションと JWKS キャッシュ
- Microsoft: 署名鍵は定期的に、緊急時は即座にロール。間隔の保証なし。単一鍵のみ対応・手動更新のアプリは「本質的に安全性・信頼性が低い」。推奨キャッシュ: `kid` 単位、TTL 24時間・1時間ごと更新、未知の `kid`（または `tid`）受信時に同期再取得（ただし5分に1回まで）、取得失敗時は last-known-good で継続、テナントごとに個別キャッシュ。https://learn.microsoft.com/en-us/entra/identity-platform/signing-key-rollover （ms.date 2024-10-28）
- 実障害例: Logto ポストモーテム — `.logto.io` で JWKS キャッシュが残ったまま署名鍵をローテーション → 新トークンの検証失敗、複数本番テナントでサインイン不能。16:00発生、16:35原因特定、16:41キャッシュ削除、16:49鍵を差し戻し、17:00復旧（PST）。https://blog.logto.io/postmortem-jwks-cache （日付は記事から未確認 **[未検証]**）
- 逆方向の失敗: Storm-0558 では「ローテーション起因の障害（2021）→ローテーション停止」が古い鍵を残した（CSRB）。
- 教訓: 「新鍵の事前公開 → 署名切替 → 旧鍵は最大トークン寿命経過後に撤去」、未知 `kid` で再取得、鍵年齢アラート。

### 5.2 時計ずれ（clock skew）
- RFC 7519 §4.1.4: leeway は「通常数分以内」。既定値はライブラリで大差: .NET 300秒、Spring 60秒、PyJWT 0、jsonwebtoken/jose/golang-jwt は明示設定。
- 短命トークン（Txn-Token は分単位以下）では 5 分 skew が寿命を実質倍以上にする点に注意（推論）。

### 5.3 トークンサイズと HTTP 431 / ヘッダ上限
- RFC 6585 §5: 431 Request Header Fields Too Large。
- Node.js: 最大ヘッダサイズ既定 16 KiB（v13.13.0 で 8→16 KiB）。超過時 431（v12.0.0 以降の既定挙動）。https://nodejs.org/api/cli.html 、https://nodejs.org/api/http.html
- nginx: `large_client_header_buffers` 既定 `4 8k`、1ヘッダフィールドが1バッファ（8KB）を超えると 400。https://nginx.org/en/docs/http/ngx_http_core_module.html
- Entra は HTTP ヘッダ制限内に収めるため groups を JWT 200件で打ち切り overage claim に置換（§1.15）。
- 教訓: groups/roles を全部詰めない。アプリ固有の権限は API 側で解決、トークンには粗いロール/スコープのみ。

### 5.4 失効と継続的アクセス評価
- 自己完結 JWT は `exp` まで有効。手段: 短命化、RFC 7662 introspection（stateful）、RFC 7009 revocation（refresh token 向け）、CAEP/SSF のイベント購読。
- OpenID Shared Signals Framework・CAEP・RISC は OpenID Final Specification として承認（2025年。Authenticate 2025（10/13–15）で相互運用デモ）。https://openid.net/tag/shared-signals （正確な承認日 **[未検証]**）
- Entra CAE: OpenID CAEP ベース。critical events（ユーザー削除/無効化、パスワード変更、MFA 有効化、refresh token 全失効、高ユーザーリスク）。伝搬遅延は最大15分の可能性、IP ポリシーは即時。CAE 対応クライアントは 401＋claims challenge を理解する必要。ゲストユーザー非対応。§1.15 参照。
- CSRB も「stateful token validation」を他 CSP のベストプラクティスとして挙げる。

### 5.5 トークンのログ記録（PII）
- OWASP Logging Cheat Sheet:「アクセストークン」「セッション識別値（必要ならハッシュ化）」「機微な個人データ/PII」はログに直接記録しない（削除・マスク・ハッシュ・暗号化）。https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- Txn-Tokens ドラフト: 逐語ログ MUST NOT。MCP Security Considerations: 「サーバでキャッシュ/ログされたトークン」の窃取を脅威として明記し、安全な保管 MUST。
- JWT ペイロードは base64url で暗号化ではない → `email`・`name`・`groups`・`ipaddr` 等は個人データになりうる。GDPR 上「個人データ」該当性の判断はケース依存（GDPR Art. 4(1) の一般定義に基づく推論。法的評価は **[未検証]**）。
- .NET: `LogTokenId` 既定 true（トークン識別子 claim をログ）、`LogValidationExceptions` 既定 true。ログ方針と合わせて確認。
- 推奨: ログには `jti`/`uti`・`iss`・`aud`・`sub`（ハッシュ化）・検証結果のみ。トークン全文は記録しない。

---

## アンチパターン集

| # | アンチパターン | 結果 | 対策 | 出典 |
|---|---|---|---|---|
| 1 | トークンの `alg` に従って検証方式を選ぶ | `none`/HS256 混同で偽造 | 呼び出し側 allowlist、1鍵1アルゴリズム | RFC 8725 §3.1、CVE-2015-9235 |
| 2 | `none` をブロックリストで弾く | 大文字小文字違い等で回避 | allowlist 方式 | rfc8725bis-10 §2.11 |
| 3 | `jwt.decode()`（未検証デコード）の結果で認可 | 署名なしで任意 claim | 必ず verify 系 API | jsonwebtoken README |
| 4 | `algorithms` を省略（jsonwebtoken ≤8.5.1） | `none` 既定で署名バイパス | v9+、明示指定 | CVE-2022-23540 |
| 5 | `kid` をパス/SQLに連結 | 空鍵・任意鍵で偽造 | 固定マップで鍵解決 | RFC 8725 §3.10 |
| 6 | HMAC 秘密を未検証ヘッダ/ペイロードから探す | 署名検証バイパス | 鍵は設定済み issuer から | CVE-2025-65945 |
| 7 | `jku`/`x5u`/埋め込み `jwk` を信頼 | 自己署名トークン受理・SSRF | issuer メタデータの JWKS のみ | CVE-2018-0114、RFC 8725 §3.10 |
| 8 | `aud` を検証しない（設定忘れ） | 他サービス宛トークンの流用 | `aud` 必須＋自分を検証 | RFC 8725 §3.9、RFC 9700 §2.3 |
| 9 | `aud` の配列形式を正しく扱わない | `aud` チェック素通り | 文字列/配列両対応のライブラリ | CVE-2020-26160 |
| 10 | マルチテナント IdP で `iss`/`tid` を見ない | 他テナントのトークン受理 | issuer/テナント allowlist、データテナント突合 | MS claims-validation、CVE-2025-55241 |
| 11 | 「署名が通れば発行体も正しい」と仮定 | 別系統鍵の署名で受理 | 鍵↔issuer の対応検証 | Storm-0558（MSRC 2023-09、CSRB） |
| 12 | ライブラリが全部検証してくれると仮定 | issuer/scope 検証漏れ | 共通検証ラッパーと単体テスト | MSRC 2023-09 |
| 13 | ID トークンを API で受理 | 任意 RP の ID トークンで API 利用 | `typ: at+jwt`、`aud`、`scp` 確認 | RFC 9068、CVE-2025-68129 |
| 14 | `typ` を見ず用途の違う JWT を同ルールで検証 | cross-JWT confusion | 明示的型付け・相互排他ルール | RFC 8725 §3.11–3.12 |
| 15 | JWE を復号できた＝真正と扱う | 公開鍵で誰でも作れる JWE を受理 | JWS/JWE/Unsecured を区別 | CVE-2023-51774、rfc8725bis §3.3 |
| 16 | `exp` を必須にしない | 永続トークン | `exp` 必須化 | golang-jwt v5 文書、PyJWT 文書 |
| 17 | 期限切れエラーだけ判定して他エラーを無視 | 不正署名を受理 | 全エラーで拒否 | CVE-2024-51744 |
| 18 | 過大な leeway（5分超、短命トークンに既定5分） | 有効期間の実質延長 | 数十秒〜数分に明示設定 | RFC 7519 §4.1.4、.NET ClockSkew 300s |
| 19 | 一回性 JWT の `jti` を記録しない | リプレイ | `jti` を `exp` までキャッシュ、DPoP | RFC 7519 §4.1.7、RFC 9700 |
| 20 | `email`/`upn`/`preferred_username` をユーザーキーにする | アカウント乗っ取り（nOAuth） | `iss`+`sub`（Entra は `tid`+`oid`） | OIDC Core §5.7、Descope |
| 21 | ユーザーが書き換え可能な属性から権限 claim を作る | 権限昇格 | 属性を read-only、権限は管理側のみ | HITB 2023 Cognito、CVE-2025-1391 |
| 22 | groups/roles を全部トークンに詰める | 431/400、overage で claim 欠落 | 粗いロールのみ、詳細は API 側 | Entra overage、RFC 6585、nginx 文書 |
| 23 | トークン内の権限を失効後も信じる | 退職者・無効ユーザーが継続利用 | 短命化、CAEP/CAE、重要操作の再評価 | Entra CAE 文書、CVE-2025-14559 |
| 24 | 署名鍵をハードコード/ピン留め | ローテーションで全断 → ローテ停止の誘惑 | JWKS 動的取得、未知 `kid` で再取得 | MS signing-key-rollover |
| 25 | JWKS を長期キャッシュしたまま鍵ローテ | 新トークン全拒否 | 事前公開＋キャッシュ制御 | Logto postmortem |
| 26 | 鍵ローテーションを止める/鍵年齢を監視しない | 古い鍵の盗難が致命傷 | 自動ローテ・HSM・年齢アラート | CSRB 2024-03-20 |
| 27 | MCP サーバが受け取ったトークンを上流 API へパススルー | confused deputy、監査・境界崩壊 | 上流用に別トークン取得（RFC 8693 等） | MCP 2026-07-28 Security Considerations |
| 28 | MCP クライアントが `resource` を送らない | 宛先非束縛トークン | RFC 8707 `resource` を常に送信 | MCP 2026-07-28 Authorization |
| 29 | エージェントがユーザーのトークン/資格情報を借用（impersonation） | 行為者の追跡不能、過剰権限 | delegation（`act`）、エージェント固有 ID、短命・最小スコープ | RFC 8693、OWASP ASI03、CoSAI 2026 |
| 30 | 署名なし・失効不能・ログなしの内部代理トークン | テナント横断の完全掌握 | 署名・短命・テナント検証・監査ログ | CVE-2025-55241（dirkjanm.io） |
| 31 | アクセストークン全文をログ出力 | ログ経由の窃取・PII 流出 | `jti`/ハッシュのみ記録 | OWASP Logging CS、Txn-Tokens §ログ |

---

## 主な不確実性（要確認）
- 特定製品の `kid` パストラバーサル/SQLi の CVE は見つからず（教材・スキャナ記事のみ）。
- MSRC 2023-07 の初回ブログの正確な日付（URL は 2023/07。7月11日と記憶しているが本文未取得）**[未検証]**。
- Microsoft.IdentityModel `EnableAadSigningKeyIssuerValidation` の導入時期と Storm-0558 との関係 **[未検証]**。
- OpenID SSF/CAEP/RISC Final の正確な承認日 **[未検証]**。
- Logto ポストモーテムの日付 **[未検証]**。
- NCCoE「コメント要約」ページは 403 で直接取得できず、検索抜粋に依存。
- rfc8725bis の datatracker 上の更新時刻（2026-11-06）は状態変更日で、-10 の公開日は 2026-08-21。
- CVE-2025-55241 の CVSS 値は未取得。
