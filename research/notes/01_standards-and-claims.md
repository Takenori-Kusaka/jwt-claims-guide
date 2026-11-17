# 01 標準仕様とクレーム — 一次資料ノート

- 調査日: 2026-11-17
- 対象読者: 新任テックリード（ID トークン／アクセストークンのクレーム設計・検証、および組織横断カスタムクレーム設計の前提整理）
- 方針: 一次資料（rfc-editor.org / datatracker / openid.net / IANA / OASIS / REFEDS）の本文を取得して確認した内容のみ記載。ベンダークレームはベンダー公式ドキュメントを出典とし「ベンダー独自」と明記。一次資料で確認できなかった事項は **[未検証]**。
- 表記: `§` は各仕様の節番号。RFC の URL は `https://www.rfc-editor.org/rfc/rfcNNNN#section-X` 形式。
- 引用は原文の要旨（MUST/SHOULD 等の規範語は原文どおり）。

---

## 0. 主要な出典と状態（2026-11-17 時点）

| 仕様 | 状態 | URL |
|---|---|---|
| RFC 7515 JWS / 7516 JWE / 7517 JWK / 7518 JWA / 7519 JWT | Proposed Standard (2015-05) | https://www.rfc-editor.org/rfc/rfc7519 |
| RFC 8725 JWT BCP | BCP 225 (2020-02) | https://www.rfc-editor.org/rfc/rfc8725 |
| draft-ietf-oauth-rfc8725bis-10 | IESG 承認済み → **RFC Editor Queue（Blocked 状態）**。RFC 8725 を obsolete 予定 | https://datatracker.ietf.org/doc/draft-ietf-oauth-rfc8725bis/ |
| RFC 9068 JWT Access Token Profile | Proposed Standard (2021-10) | https://www.rfc-editor.org/rfc/rfc9068 |
| OpenID Connect Core 1.0 incorporating errata set 2 | Final (2023-12-15) | https://openid.net/specs/openid-connect-core-1_0.html |
| OpenID Connect Back-Channel Logout 1.0 incorporating errata set 1 | Final (2023-12-15) | https://openid.net/specs/openid-connect-backchannel-1_0.html |
| OpenID Shared Signals Framework 1.0 / CAEP 1.0 / RISC Profile 1.0 | **Final**（3仕様とも 2025-08-29 公開、OIDF が 2025-09-02 に Final 承認を告知） | https://openid.net/wg/sharedsignals/ |
| RFC 9901 SD-JWT | Proposed Standard (2025-11) | https://www.rfc-editor.org/rfc/rfc9901 |
| OpenID Identity Assurance Schema Definition 1.0 (errata set 1) / OpenID Connect for Identity Assurance 1.0 | Final（2026-07-01 公開） | https://openid.net/specs/openid-ida-verified-claims-1_0.html |
| draft-ietf-oauth-status-list-21 (Token Status List) | RFC Editor Queue（IANA には `RFC-ietf-oauth-status-list-21` として既に登録） | https://datatracker.ietf.org/doc/draft-ietf-oauth-status-list/ |
| IANA "JSON Web Token Claims" registry | 最終更新 2026-10-28 | https://www.iana.org/assignments/jwt/jwt.xhtml |

- 8725bis の状態は datatracker API で確認: IESG state = "RFC Ed Queue"、RFC Editor state = "Blocked"、WG state = "Submitted to IESG for Publication"、最新版 -10（2026-11-06）。Blocked の理由は本文で明示されていないが、8725bis は draft-ietf-jose-deprecate-none-rsa15 を規範参照しており、その draft も同じく RFC Ed Queue / Blocked 状態（2026-11-17 時点、-08）。**依存待ちと推定 [未検証]**。出典: https://datatracker.ietf.org/api/v1/doc/document/draft-ietf-oauth-rfc8725bis/ , 8725bis-10 §3.2 / Appendix A。

---

## 1. JOSE 基礎（RFC 7515 / 7516 / 7517 / 7518 / 7519）

### 1.1 構造

- JWT は JSON の Claims Set を JWS のペイロードまたは JWE の平文として符号化したもの。RFC 7519 §1, §3 — https://www.rfc-editor.org/rfc/rfc7519#section-3
- JWS Compact Serialization: `BASE64URL(UTF8(Protected Header)) . BASE64URL(Payload) . BASE64URL(Signature)`（3 セグメント）。RFC 7515 §3.1 — https://www.rfc-editor.org/rfc/rfc7515#section-3.1
- JWE Compact Serialization: `Header . EncryptedKey . IV . Ciphertext . AuthTag`（5 セグメント）。RFC 7516 §3.1 — https://www.rfc-editor.org/rfc/rfc7516#section-3.1
- JWS と JWE の判別: Compact ならピリオド区切りのセグメント数（3 vs 5）、JSON Serialization なら `payload` / `ciphertext` メンバーの有無。RFC 7516 §9 — https://www.rfc-editor.org/rfc/rfc7516#section-9
- JWE の `enc` は AEAD 必須。RFC 7516 §4.1.2。
- Nested JWT（署名後に暗号化）では `cty` は MUST で値は `"JWT"`。通常の（入れ子でない）JWT では `cty` の使用は NOT RECOMMENDED。RFC 7519 §5.2 — https://www.rfc-editor.org/rfc/rfc7519#section-5.2
- 署名と暗号化の両方が必要なら、通常は「署名してから暗号化」。RFC 7519 §11.2 — https://www.rfc-editor.org/rfc/rfc7519#section-11.2
- JWE では一部のクレーム（`iss`/`sub`/`aud`）をヘッダーに平文で複製可能。複製した場合、受信側は値の一致を SHOULD 検証。RFC 7519 §5.3 — https://www.rfc-editor.org/rfc/rfc7519#section-5.3
- JWK: `kty` は MUST。`use`（`sig`/`enc`）、`key_ops`、`alg`、`kid` は任意。JWK Set 内では異なる鍵に異なる `kid` を SHOULD。RFC 7517 §4.1–4.5, §5 — https://www.rfc-editor.org/rfc/rfc7517#section-4
- JWA の JWS `alg`: HS256 = Required、RS256 = Recommended、ES256 = Recommended+、`none` = Optional。RFC 7518 §3.1 — https://www.rfc-editor.org/rfc/rfc7518#section-3.1
- HMAC 鍵はハッシュ出力長以上（HS256 なら 256 bit 以上）MUST。RFC 7518 §3.2 — https://www.rfc-editor.org/rfc/rfc7518#section-3.2
- `alg: none`（Unsecured JWS）: 実装はデフォルトで受理 MUST NOT。グローバルに受理を宣言 MUST NOT、オブジェクト単位で SHOULD。RFC 7518 §3.6, §8.5 — https://www.rfc-editor.org/rfc/rfc7518#section-3.6

### 1.2 型定義

- **NumericDate**: 1970-01-01T00:00:00Z からの秒数（うるう秒無視）の JSON 数値。**非整数も可**。RFC 7519 §2 — https://www.rfc-editor.org/rfc/rfc7519#section-2
- **StringOrURI**: 任意文字列可だが **`:` を含む値は URI でなければならない（MUST）**。比較は大文字小文字区別・正規化なしの文字列比較。RFC 7519 §2
- **Collision-Resistant Name**: 衝突しにくい名前空間の名前。例: ドメイン名、OID、UUID。RFC 7519 §2
- 文字列比較: JSON 文字列比較規則を MUST 使用。例外は `typ` と `cty` のみ。`iss` に DNS 名を含める等の場合、生成側で正規形（例: 小文字化）の取り決めが必要になり得る。RFC 7519 §7.3 — https://www.rfc-editor.org/rfc/rfc7519#section-7.3

### 1.3 Claims Set の一般規則

- クレーム名は一意 MUST。重複があればパーサは拒否するか、最後の値のみ返すパーサを使う（MUST）。RFC 7519 §4 — https://www.rfc-editor.org/rfc/rfc7519#section-4
- どのクレームが必須かはアプリケーション依存。**理解できないクレームは無視 MUST**（特段の要件がない限り）。RFC 7519 §4
  - 設計上の含意: 受信側が知らない新クレームを足しても拒否されない一方、「新クレームで制限をかけた」つもりでも古い受信側は無視する。制限系クレームは受信側の実装と同期が必要（RFC 8417 §4 冒頭もこの性質を混同リスクとして指摘）。
- 登録済みクレームはいずれも「全ケースで必須」ではなく、プロファイルが必須性を定義すべき。RFC 7519 §4.1

### 1.4 登録クレーム（RFC 7519 §4.1）

| クレーム | 意味（原文要旨） | 型 | 出典 |
|---|---|---|---|
| `iss` | JWT を発行した主体。処理は概ねアプリ依存 | 大文字小文字区別の StringOrURI | §4.1.1 |
| `sub` | JWT の主体。**issuer の文脈でローカル一意、またはグローバル一意 MUST** | 大文字小文字区別の StringOrURI | §4.1.2 |
| `aud` | 受信者。**処理する主体は自身を `aud` 内の値で識別 MUST**。`aud` があり自分が含まれなければ **拒否 MUST**。一般には文字列配列、単一受信者なら文字列 MAY | StringOrURI の配列 or 単一文字列 | §4.1.3 |
| `exp` | この時刻**以降**は処理受理 MUST NOT。現在時刻が `exp` より**前**であること MUST。時計ずれ対策の小さな leeway（通常数分以内）MAY | NumericDate | §4.1.4 |
| `nbf` | この時刻より前は受理 MUST NOT。現在時刻 ≥ `nbf` MUST。leeway MAY | NumericDate | §4.1.5 |
| `iat` | 発行時刻。JWT の経過時間判定に使える | NumericDate | §4.1.6 |
| `jti` | JWT の一意識別子。偶発的重複の確率が無視できる方式で割当 MUST、複数 issuer 間でも衝突防止 MUST。リプレイ防止に使える | 大文字小文字区別の文字列 | §4.1.7 |

URL: https://www.rfc-editor.org/rfc/rfc7519#section-4.1

### 1.5 Public / Private クレーム名（カスタムクレーム設計の根拠）

- **Public Claim Name**: 新しいクレーム名は、IANA 登録するか、**Collision-Resistant Name を含む Public Name** にすべき（should）。定義者は自分が管理する名前空間を使う合理的注意が必要。RFC 7519 §4.2 — https://www.rfc-editor.org/rfc/rfc7519#section-4.2
- **Private Claim Name**: 発行者と受信者が合意した、登録も衝突耐性もない名前（MAY）。**衝突の可能性があり慎重に使うべき**。RFC 7519 §4.3 — https://www.rfc-editor.org/rfc/rfc7519#section-4.3
- RFC 9068 も「既存仕様にない属性は、衝突耐性のある名前か、プライベートなサブシステム内でのみ使われるトークンなら返してよい（MAY）」と同じ整理。RFC 9068 §2.2.2 — https://www.rfc-editor.org/rfc/rfc9068#section-2.2.2
- 既存の IANA 登録クレームで意味が十分記述されている属性は、**その登録名を SHOULD 使用**（JWT アクセストークン）。RFC 9068 §2.2.2

### 1.6 JOSE ヘッダーパラメータ（セキュリティ上重要なもの）

| パラメータ | 要点 | 出典 |
|---|---|---|
| `alg` | MUST 存在・MUST 理解。サポート外アルゴリズム、または署名者に紐づく鍵がなければ署名は無効。大文字小文字区別 | RFC 7515 §4.1.1 |
| `kid` | 使用鍵の**ヒント**。構造は未規定。大文字小文字区別文字列 | RFC 7515 §4.1.4 |
| `jku` | JWK Set の URL。取得は完全性保護 MUST（TLS + サーバ同一性検証） | RFC 7515 §4.1.2 |
| `jwk` | 署名鍵に対応する公開鍵そのもの | RFC 7515 §4.1.3 |
| `x5u` | X.509 証明書（チェーン）の URL。TLS MUST | RFC 7515 §4.1.5 |
| `x5c` | 証明書チェーン（base64 DER の配列）。受信者は RFC 5280 で**チェーン検証 MUST** | RFC 7515 §4.1.6 |
| `x5t` / `x5t#S256` | 証明書の SHA-1 / SHA-256 サムプリント | RFC 7515 §4.1.7–4.1.8 |
| `typ` | JWS 全体のメディアタイプ。**JWS 実装は無視し、処理はアプリケーションが行う**。`/` を含まない値は `application/` を前置して扱う MUST。`application/` 省略を RECOMMENDED | RFC 7515 §4.1.9 |
| `typ`（JWT） | 値を付けるなら `"JWT"`（大文字）RECOMMENDED。OPTIONAL | RFC 7519 §5.1 |
| `cty` | ペイロードのメディアタイプ。Nested JWT 時のみ `"JWT"` MUST | RFC 7515 §4.1.10, RFC 7519 §5.2 |
| `crit` | 理解必須の拡張ヘッダー名リスト。未理解なら JWS 無効。保護ヘッダー内のみ MUST。空配列 MUST NOT | RFC 7515 §4.1.11 |
| `zip` (JWE) | 暗号化前の圧縮（`DEF`）。保護ヘッダー内のみ MUST | RFC 7516 §4.1.3 |

URL: https://www.rfc-editor.org/rfc/rfc7515#section-4.1

関連する検証規定:
- JOSE ヘッダーは、構文・意味とも理解しサポートしているパラメータのみ含むこと（または未理解時は無視と規定されたもの）を検証。RFC 7519 §7.2 step 5 — https://www.rfc-editor.org/rfc/rfc7519#section-7.2
- 署名検証が成功しても、使用アルゴリズムがアプリに受け入れ可能でなければ SHOULD 拒否。RFC 7519 §7.2 末尾 / RFC 7515 §5.2
- 署名値に内包されたハッシュアルゴリズムが `alg` と一致することを MUST 確認（RSASSA-PKCS1-v1_5 の例）。RFC 7515 §10.6
- 公開鍵の取得手段は鍵の出自を認証しなければならない（must）。RFC 7515 §10.3
- JWT の内容は、暗号的に保護され、信頼判断に必要な文脈に結び付けられていない限り信頼判断に使えない。署名鍵は通常 issuer の管理下にあることを検証可能であるべき。RFC 7519 §11.1 — https://www.rfc-editor.org/rfc/rfc7519#section-11.1
- OIDC は ID Token で `x5u` / `x5c` / `jku` / `jwk` ヘッダーを SHOULD NOT 使用と規定。OIDC Core §2

---

## 2. RFC 8725（JWT BCP）と 8725bis

URL: https://www.rfc-editor.org/rfc/rfc8725

### 2.1 脅威（§2）

| § | 脅威 | 対策節 |
|---|---|---|
| 2.1 | `alg` を `none` に書換え／RS256→HS256 書換え（RSA 公開鍵を HMAC 秘密として使わせる） | 3.1, 3.2 |
| 2.2 | 弱い対称鍵（人間が覚えるパスワード）→ オフライン総当たり | 3.5 |
| 2.3 | JWE 復号後に内側 JWS の署名を検証しないライブラリ | 3.3 |
| 2.4 | 暗号文長からの平文漏えい（圧縮で悪化） | 3.6 |
| 2.5 | ECDH-ES の不正曲線点攻撃 | 3.4 |
| 2.6 | JSON エンコーディングの多様性（UTF-16/32） | 3.7 |
| 2.7 | 置換攻撃（ある RS 宛のトークンを別 RS で使う） | 3.8, 3.9 |
| 2.8 | **Cross-JWT Confusion**（ある目的の JWT を別目的に流用）。混同し得る文脈なら対策 MUST | 3.8, 3.9, 3.11, 3.12 |
| 2.9 | サーバへの間接攻撃（クレームを使った DB/LDAP 検索のインジェクション、URL による SSRF） | 3.10 |

### 2.2 ベストプラクティス（§3、全項目）

- **§3.1 アルゴリズム検証**: ライブラリは呼出側が許可アルゴリズム集合を指定できること MUST、それ以外を使わないこと MUST。`alg`/`enc` が実際の暗号操作と一致すること MUST。**各鍵は厳密に 1 つのアルゴリズムでのみ使用 MUST**、操作時にチェック MUST。
- **§3.2 適切なアルゴリズム**: アプリは暗号学的に現行のアルゴリズムのみ許可 MUST、暗号アジリティを設計 MUST。`none` は他手段で保護されている場合のみ。ライブラリは明示要求なしに `none` を生成・受理 SHOULD NOT。RSA-PKCS1 v1.5 暗号は避け RSAES-OAEP を推奨。ECDSA は RFC 6979 決定的方式を SHOULD。
- **§3.3 全暗号操作を検証**: いずれかが失敗したら JWT 全体を拒否 MUST。Nested JWT では外側・内側とも**アプリが与えた鍵とアルゴリズムで** MUST 検証。
- **§3.4 暗号入力の検証**: ECDH-ES の `epk` を検証（NIST 曲線は SP 800-56A r3 §5.6.2.3.4 MUST）。
- **§3.5 鍵エントロピー**: 人間が記憶するパスワードを HS256 等の鍵に直接使用 MUST NOT。
- **§3.6 暗号化前の圧縮**: SHOULD NOT。
- **§3.7 UTF-8**: MUST。
- **§3.8 Issuer と Subject の検証**: `iss` があるなら、**使用された鍵がその issuer に属することを検証 MUST**、違えば拒否 MUST（例: OIDC の issuer メタデータの `jwks_uri`）。`sub` があるなら、subject または issuer-subject ペアがアプリにとって有効であることを検証 MUST。
- **§3.9 Audience の使用と検証**: 同一 issuer が複数 RP/アプリ向けに JWT を発行し得るなら、**`aud` を含めること MUST**。RP は `aud` を検証 MUST、無い／自分と関連しないなら拒否 MUST。
- **§3.10 受信クレームを信用しない**: `kid` による鍵検索で SQL/LDAP インジェクションを起こさないよう検証・サニタイズ。`jku`/`x5u` を盲目的に辿ると SSRF → 許可リスト照合等で SHOULD 防御。
- **§3.11 明示的型付け（Explicit Typing）**: `typ` で JWT の種類を明示し、検証規則で型を検査。`application/example+jwt` 形式を RECOMMENDED、`typ` は `application/` を省略（例 `secevent+jwt`）。Nested JWT では**内側** JWT に `typ` MUST。既存種別の検証規則は `typ` を見ないことが多いので、明示的型付けでも既存 JWT との区別は達成できない場合がある。**新しい JWT 用途では RECOMMENDED**。
- **§3.12 種類ごとに相互排他的な検証規則**: 同一 issuer が複数種の JWT を発行するなら、検証規則は相互排他的に書き、別種の JWT を拒否 MUST。戦略: (1) 異なる `typ`、(2) 異なる必須クレーム／値、(3) 異なる必須ヘッダー／値、(4) **種類ごとに別の鍵**、(5) **用途ごとに別の `aud`**、(6) 種類ごとに別の `iss`。

URL: https://www.rfc-editor.org/rfc/rfc8725#section-3

### 2.3 8725bis（draft-ietf-oauth-rfc8725bis-10）の変更点

出典: https://www.ietf.org/archive/id/draft-ietf-oauth-rfc8725bis-10.txt Appendix A および各節。状態は §0 参照（**未 RFC 化**。番号未割当）。

1. **アルゴリズム検証の防御的実装**（§2.11, §3.1）: `none` をブロックリストで弾く実装が `alg` を大文字小文字無視で読み、`"noNE"` で回避された事例。→ `alg` 等は**ブロックリストでなく許可リスト**を使うべき（should）。受信者は issuer ごとに許可アルゴリズムを決め MUST 準拠確認。`alg`/`enc` が `kid` で引いた鍵に紐づくアルゴリズムと一致することを MUST 検証。
2. **暗号化と署名の混同**（§2.3, §3.3）: ライブラリは Unsecured JWT / JWS / JWE / Nested JWT を受信者が区別できるようにすること MUST（「復号成功」を「署名検証成功」と取り違えない）。認証用途は通常署名付き JWT が必要。
3. **PBES2 反復回数上限**（§2.10, §3.13）: `p2c` が過大な入力を拒否（OWASP の 600,000 の 2 倍超の拒否を RECOMMENDED）。
4. **JWT フォーマット混同**（§2.13, §3.14）: JSON Serialization で検証し Compact として文字列分割で claims を抽出する実装の偽造。→ JWT は base64url 文字とピリオドのみであることを MUST 確認、波括弧・引用符等を含めば MUST 拒否。
5. **JWE 解凍爆弾**（§2.12, §3.15）: 解凍後サイズ上限を RECOMMENDED（実装例 250 KB）。
6. **明示的型付けの拡充**（§3.11, §3.12）: 完全メディアタイプ `application/example+jwt` を SHOULD 登録、`typ` は `example+jwt` を SHOULD。混同し得ない文脈なら省略 MAY。**`typ: "JWT"` は有効な明示的型付けにならない**。既存種別に「必須の型付け」を後付けするのは破壊的変更だが、「`typ` があるなら期待値であること MUST」という後付けは非破壊。例として Logout Token の `nonce` 禁止（アドホックな混同対策）を挙げ、明示的型付けならそのような手段が不要になると説明。
7. **非信頼ヘッダーと SSRF**（§3.10）: クレーム値を攻撃者入力として扱う。`kid` のインジェクション対策は **MUST** に格上げ。許可リストがない場合は、ホスト名の解決先がループバック／ローカル IP なら要求しないこと MUST（DNS 解決チェック）。
8. `none` 関連の文言を MUST 化（ライブラリは明示要求なしに `none` を生成・受理 MUST NOT）。draft-ietf-jose-deprecate-none-rsa15 を規範参照し `none` と RSA-PKCS1 v1.5 暗号を非推奨化。RFC 9864 の完全指定アルゴリズム ID（例 `Ed25519` を `EdDSA` より優先）を新規導入で SHOULD。

---

## 3. RFC 9068 — JWT Profile for OAuth 2.0 Access Tokens

URL: https://www.rfc-editor.org/rfc/rfc9068

### 3.1 ヘッダー（§2.1）
- JWT アクセストークンは**署名 MUST**、`none` MUST NOT。非対称署名を RECOMMENDED。AS/RS は RS256 のサポート MUST。
- `typ` に `application/at+jwt` を含めること MUST。値は `"at+jwt"` を SHOULD。目的は **ID Token をアクセストークンとして受理させないため**。

### 3.2 クレーム（§2.2）
| クレーム | 要件 | 補足 |
|---|---|---|
| `iss` | REQUIRED | RFC 7519 §4.1.1 |
| `exp` | REQUIRED | |
| `aud` | REQUIRED | §3 で決定方法 |
| `sub` | REQUIRED | リソースオーナー関与のグラント（authorization code 等）では RO の subject 識別子を SHOULD。関与しないグラント（client credentials）では **AS がクライアントを示す識別子** を SHOULD |
| `client_id` | REQUIRED | RFC 8693 §4.3 |
| `iat` | REQUIRED | |
| `jti` | REQUIRED | |

- 認証情報クレーム（§2.2.1）: `auth_time` / `acr` / `amr`（OIDC Core §2 の定義）を MAY。値は**認可応答時点で固定**され、リフレッシュやトークン交換で得た派生アクセストークンでも変わらない。
- アイデンティティクレーム（§2.2.2）: IANA 登録済みの意味が合う属性は登録名を SHOULD。クライアントが特定クレームを直接要求する仕組みは定義しない（AS は `client_id`・`scope`・`resource` から判断）。
- 認可クレーム（§2.2.3）: `scope` パラメータ付き要求なら `scope` クレーム（RFC 8693 §4.2）を SHOULD。**各スコープ文字列は `aud` が示すリソースにとって意味を持つこと MUST**。
- **§2.2.3.1 委譲以外の認可属性**: ロール・グループ・エンタイトルメントを入れるなら、**RFC 7643 §4.1.2 の `groups` / `roles` / `entitlements` をクレーム型として SHOULD 使用**。値のエンコードも RFC 7643 の指針を SHOULD。`roles` と `entitlements` には特定の語彙は無い。

### 3.3 要求とアクセストークン発行（§3）
- `resource`（RFC 8707）付き要求なら、`aud` は `resource` と同じ値を SHOULD。
- 無い場合は**デフォルトのリソース指示子を `aud` に MUST**。`scope` から推定 SHOULD。スコープが異なるデフォルトリソースにまたがれば `invalid_scope` で SHOULD 拒否。
- **付与される認可が曖昧になる場合は JWT アクセストークンを発行 MUST NOT**。

### 3.4 RS 側の検証手順（§4）
1. `typ` が `at+jwt` または `application/at+jwt` であることを MUST 検証、それ以外は拒否。
2. 暗号化されていれば登録時の鍵/アルゴリズムで復号。暗号化を取り決めたのに平文なら SHOULD 拒否。
3. AS の issuer 識別子（通常ディスカバリで取得）が `iss` と**完全一致** MUST。
4. `aud` に自 RS を示すリソース指示子が含まれることを MUST 検証。無ければ拒否 MUST。
5. 署名を `alg` で MUST 検証、`none` は拒否 MUST、**AS が提供した鍵**を使う MUST。
6. 現在時刻 < `exp` MUST（小さな leeway MAY）。
- 失敗時は RFC 6750 §3.1 の `invalid_token`。認可クレームは他の文脈情報と組み合わせて SHOULD 使う（詳細はスコープ外）。
- AS は RFC 8414 メタデータで `jwks_uri` と `issuer` を SHOULD 公開。OIDC Discovery と併用時は一貫 MUST。

### 3.5 セキュリティ・プライバシー（§5, §6）
- ID Token と構造が似るので明示的型付けで区別（§5）。
- AS は、クライアントが `sub` に影響できて RS を混乱させるシナリオを防ぐべき（client credentials で `client_id` を `sub` にするなら任意 `client_id` 登録を許さない）（§5）。
- **同一 issuer が異なるリソース向けに発行するアクセストークンには、それぞれ別個の `aud` を MUST**（Cross-JWT confusion 対策）（§5）。
- 複数リソース指示子を含む要求では、各スコープがどの `aud` に対応するか曖昧にならないよう注意（§5）。
- ID Token とアクセストークンで別の鍵を使っても、RS は公開鍵のどれでも受理せざるを得ないため、鍵漏えい対策にはならない（§5）。
- **クライアントはアクセストークンの中身を見てはならない（MUST NOT）**。フォーマットは変更され得る（§6）。
- 中身はクライアント・エンドユーザーに見え得る。対策: 暗号化、機微クレームの暗号化/省略、opaque トークンへのフォールバック（§6）。
- RS はクレーム内容を受け取る正当な権限（同意等）を持つか評価すべき（§6）。
- `sub` は必須なので相関が可能。追跡防止が必要なら RS ごとに相関不能な異なる `sub`、さらに RS 内相関も防ぐならトークンごとに異なる `sub`（§6）。

---

## 4. OpenID Connect Core 1.0（errata set 2）と関連仕様

URL: https://openid.net/specs/openid-connect-core-1_0.html

### 4.1 ID Token クレーム（§2）
| クレーム | 要件 | 意味・型 |
|---|---|---|
| `iss` | REQUIRED | Issuer Identifier。https スキームの大文字小文字区別 URL。scheme・host・任意の port・path を含み、query/fragment を含まない |
| `sub` | REQUIRED | **Issuer 内でローカル一意かつ再割当されない**エンドユーザー識別子。**255 ASCII 文字以内 MUST**。大文字小文字区別 |
| `aud` | REQUIRED | RP の OAuth `client_id` を **MUST 含む**。他の audience も MAY。配列または単一文字列 |
| `exp` | REQUIRED | この時刻以降は RP は受理 MUST NOT。leeway MAY。**ID Token の有効期限は RP–OP 間の認証セッション寿命とは無関係** |
| `iat` | REQUIRED | 発行時刻 |
| `auth_time` | 条件付き | エンドユーザー認証時刻。`max_age` 要求時、または Essential Claim として要求時は REQUIRED |
| `nonce` | 条件付き | クライアントセッションと ID Token を関連付け、リプレイを緩和。認証要求に含まれていれば AS は MUST 含める。クライアントは一致を MUST 検証 |
| `acr` | OPTIONAL | Authentication Context Class Reference。`"0"` は ISO/IEC 29115 レベル1未満（金銭的価値のあるリソースの認可に SHOULD NOT 使用）。絶対 URI または RFC 6711 登録名を SHOULD |
| `amr` | OPTIONAL | 認証方式の識別子の**配列**。RFC 8176 の IANA 登録値を SHOULD |
| `azp` | OPTIONAL | ID Token が発行された当事者（Client ID）。**errata 2 では、本仕様の範囲外の拡張使用時にしか現れないため、そうでない実装は使わず、現れても無視することを推奨** |

- その他: 理解できないクレームは MUST 無視。ID Token は **JWS 署名 MUST**、暗号化するなら署名→暗号化（Nested JWT）。`none` は、認可エンドポイントから ID Token を返さないレスポンスタイプ（Code Flow 等）かつ登録時に明示要求した場合を除き MUST NOT。

### 4.2 フロー別クレーム
- `at_hash`: `access_token` の ASCII 表現を `alg` のハッシュ関数でハッシュした**左半分**の base64url。Code Flow では OPTIONAL（§3.1.3.6）。Hybrid で認可エンドポイントから `access_token` と同時発行（`code id_token token`）なら REQUIRED（§3.3.2.11）。
- `c_hash`: `code` の同様のハッシュ。Hybrid で `code id_token` / `code id_token token` なら REQUIRED（§3.3.2.11）。
- 用途: RFC 9700 §4.6.1 は OIDC の `at_hash` と `nonce` によりアクセストークン注入攻撃を緩和できると説明。

### 4.3 ID Token 検証（§3.1.3.7、Code Flow、13 ステップ）
1. 暗号化されていれば登録時の鍵/アルゴリズムで復号。暗号化を取り決めたのに平文なら SHOULD 拒否。
2. OP の Issuer Identifier（通常ディスカバリで取得）が `iss` と**完全一致 MUST**。
3. `aud` に、`iss` が示す Issuer に登録した自分の `client_id` が含まれることを MUST 検証。**自分が含まれない、または信頼しない追加 audience を含む場合は拒否 MUST**。
4. `azp` が現れる拡張を使う場合は、その拡張に従って SHOULD 検証。
5. その検証には、`azp` があれば自分の `client_id` であることの確認を含め得る（MAY/SHOULD）。
6. トークンエンドポイントとの直接通信で受け取った場合（本フロー）、署名検証の代わりに TLS サーバ検証で issuer を検証 MAY。それ以外の ID Token は `alg` で署名を MUST 検証、**Issuer 提供の鍵** MUST。
7. `alg` はデフォルト RS256 か登録時の `id_token_signed_response_alg` を SHOULD。
8. HS256 等 MAC の場合、`aud` の `client_id` に対応する `client_secret` の UTF-8 を鍵に使う。`aud` が複数値なら挙動未定義。
9. 現在時刻 < `exp` MUST。
10. `iat` で発行が現在から離れすぎたトークンを拒否でき、nonce 保存期間を制限できる。許容範囲はクライアント依存。
11. 認証要求で `nonce` を送ったなら、`nonce` が存在し一致することを MUST 確認。リプレイ検査 SHOULD。
12. `acr` を要求したなら値が適切か SHOULD 確認。
13. `auth_time` を要求（または `max_age` 使用）したなら SHOULD 確認し、経過しすぎなら再認証を要求。

（番号は HTML の `<ol>` 項目を数えて確認。）URL: https://openid.net/specs/openid-connect-core-1_0.html#IDTokenValidation

### 4.4 標準クレーム（§5.1）
- `sub`, `name`, `given_name`, `family_name`, `middle_name`, `nickname`, `preferred_username`, `profile`, `picture`, `website`, `email`, `email_verified`, `gender`, `birthdate`, `zoneinfo`, `locale`, `phone_number`, `phone_number_verified`, `address`, `updated_at`。
- `preferred_username`: `@`、`/`、空白等を含む任意 JSON 文字列 MAY。**RP は一意性に依存 MUST NOT**（§5.7 参照）。
- `email`: RFC 5322 addr-spec 準拠 MUST。**RP は一意性に依存 MUST NOT**。
- `email_verified`: true は「OP が**検証実施時点で**エンドユーザーがそのアドレスを管理していたことを確認する積極的措置を取った」こと。検証手段は文脈依存（トラストフレームワーク／契約次第）。
- `phone_number_verified` も同様。true なら `phone_number` は E.164 MUST。
- `updated_at`: NumericDate 相当の数値。
- スコープ `email` は `email`/`email_verified` を、`phone` は `phone_number`/`phone_number_verified` を要求（§5.4）。
- 集約／分散クレーム `_claim_names` / `_claim_sources`（§5.6.2、IANA 登録あり）。Entra は groups 超過時にこの形式を使用（§11.4 参照）。

### 4.5 クレームの安定性と一意性（§5.7）— 最重要
- **ID Token の `sub` と `iss` の組合せだけが、RP が安定した識別子として依存できる唯一のクレーム**。`sub` は Issuer 内でローカル一意かつ再割当されないため。
- 他のクレームは issuer をまたいだ一意性・時間的安定性の保証がない。例: Issuer は**同じ `email` 値を時期を変えて別ユーザーに再利用してよい（MAY）**し、ユーザーの `email` は変わり得る（MAY）。
- したがって `email`, `phone_number`, `preferred_username`, `name` は、ID Token・UserInfo いずれから得たものでも **一意識別子として使用 MUST NOT**。

URL: https://openid.net/specs/openid-connect-core-1_0.html#ClaimStability

### 4.6 Subject Identifier の種類（§8, §8.1）
- `public`: 全クライアントに同じ `sub`。`subject_types_supported` がなければデフォルト。
- `pairwise`: クライアントごとに異なる `sub`（無許可の相関を防ぐ）。OP は Sector Identifier ごとに一意な `sub` を計算 MUST、OP 以外には不可逆 MUST、決定的 MUST、異なる Sector Identifier → 異なる値 MUST。
- Sector Identifier: `sector_identifier_uri` 未指定ならリダイレクト URI のホスト。複数ホストのリダイレクト URI があれば `sector_identifier_uri` 登録 MUST。
- 含意: 同一ユーザーでも RP（セクター）が変われば `sub` が変わる。複数アプリで同じユーザーを突合したいなら、同一セクターにするか別識別子を設計する必要。

### 4.7 Back-Channel Logout の Logout Token（BCL §2.4–2.7, §4.1）
URL: https://openid.net/specs/openid-connect-backchannel-1_0.html
- クレーム: `iss` REQUIRED、`sub` OPTIONAL、`aud` REQUIRED、`iat` REQUIRED、`exp` REQUIRED、`jti` REQUIRED、`events` REQUIRED（`http://schemas.openid.net/event/backchannel-logout` をメンバー名に含む JSON オブジェクト、値は空オブジェクト `{}` を SHOULD）、`sid` OPTIONAL。
- **`sub` か `sid` の少なくとも一方 MUST**。`sid` が無い場合は `iss`+`sub` で識別されるユーザーの RP 上の全セッションをログアウトする意図。
- **`nonce` は PROHIBITED**（ID Token の代わりに偽造認証応答に使われても構文的に無効にするため）。
- 署名 MUST、暗号化 MAY（ID Token と同じ鍵）。`typ: logout+jwt` を RECOMMENDED。ただし**明示的型付けを必須にすると既存デプロイの大半が壊れる**ため、新規プロファイルでの必須化は良い考え、という整理（§4.1）。
- `sid`: セッション ID。OP 上の個別セッションを識別。**特定 issuer の文脈でのみ一意であればよい**。RP にとって不透明。構文は OAuth Client Identifier と同じ。`backchannel_logout_session_supported` が true なら `sid` は **ID Token にも含まれる**（§2.1）。定義は Front-Channel Logout と同一。IANA 上の `sid` の定義元は Front-Channel Logout 1.0。
- 検証（§2.6）: 復号 → ID Token と同様に署名・`alg` 検証（`none` MUST NOT）→ `iss`/`aud`/`iat`/`exp` を ID Token 同様に検証 → `sub`/`sid` の存在 → `events` の存在 → `nonce` 不在 → 任意で `jti` 再受信チェック、`iss`/`sub`/`sid` が現在または最近の ID Token と一致するか。
- OP は短い有効期限（**できれば 2 分以内**）を推奨（§4）。
- RP はセッション状態を消去。`offline_access` なしで発行されたリフレッシュトークンは SHOULD 失効、`offline_access` 付きは通常 SHOULD NOT 失効（§2.7）。

### 4.8 RFC 8176 — Authentication Method Reference Values
URL: https://www.rfc-editor.org/rfc/rfc8176#section-2
- 定義値: `face`, `fpt`, `geo`, `hwk`（ハードウェア保護鍵の PoP）, `iris`, `kba`, `mca`（複数チャネル）, `mfa`（多要素。個別方式も併記可）, `otp`, `pin`, `pwd`, `rba`（リスクベース）, `retina`, `sc`（スマートカード）, `sms`, `swk`（ソフトウェア保護鍵の PoP）, `tel`, `user`（ユーザー存在テスト）, `vbm`, `wia`。
- 注意: `amr` は「どの方式が使われたか」の事実であり、保証レベル（`acr`）とは別物。保証レベルの合意は `acr` 値の意味の合意として当事者間で必要（OIDC Core §2）。

### 4.9 RFC 9470 — Step Up Authentication Challenge
URL: https://www.rfc-editor.org/rfc/rfc9470
- 新エラーコード `insufficient_user_authentication`（Bearer や DPoP 等の `error` パラメータ）（§3）。
- `WWW-Authenticate` の auth-param: `acr_values`（空白区切り、優先順。いずれかを要求）、`max_age`（直近のアクティブ認証からの許容経過秒、非負整数）。両方同時 MAY、不足スコープがあれば `scope` も MAY（§3）。
- クライアントはこれを使って OIDC の `acr_values` / `max_age` 付き認可要求を組み立てる SHOULD（§4）。
- JWT アクセストークンでは `auth_time` と `acr`（RFC 9068 §2.2.1）で伝達。値は認証時に確定しトークン更新で変わらない（§6.1）。イントロスペクションでは `acr` / `auth_time` を応答メンバーとして定義（§6.2）。
- AS は `acr_values_supported` をメタデータに含めることで対応を示す（§7）。
- 注意: OAuth を認証プロトコルとして位置づけるために使っては MUST NOT。`acr_values` のチャレンジは高権限ユーザーの推測等の情報漏えいになり得る。悪意ある RS によるユーザー操作誘発の悪用に注意（§9）。

---

## 5. 委譲・audience・送信者制約

### 5.1 RFC 8693 Token Exchange
URL: https://www.rfc-editor.org/rfc/rfc8693
- 委譲と成りすまし（§1.1）: **成りすまし（impersonation）**では A は B と区別不能で、受信者からは B を扱っているのと同じ。**委譲（delegation）**では A は B とは別のアイデンティティを保ち、「A が B を代理して行動」と明示的に理解される。委譲は主たる subject とアクターの両方の情報を含む「複合トークン」で表現されるのが典型。
- 要求パラメータ（§2.1）:
  - `subject_token` REQUIRED: **要求の代理対象となる当事者**のアイデンティティを表す。通常この subject が発行トークンの subject になる。
  - `actor_token` OPTIONAL: **行動する当事者**のアイデンティティ。通常、発行トークンの使用を認可され subject を代理する当事者。`actor_token_type` は `actor_token` があれば REQUIRED、無ければ MUST NOT。
  - `resource`（URI）/ `audience`（論理名）/ `scope` / `requested_token_type`。複数の resource/audience と scope の組合せは「全ターゲットで全スコープ」の直積の意味（§2.1.1）。
  - 交換は一回限りのイベントで、入出力トークン間に強い連結はない。入力トークンの延長は出力に反映されない（§2.1）。
- `act`（§4.1）: 委譲が起きたことと**現在のアクター**を表す JSON オブジェクト。中のクレームはアクターの識別のみ（`iss`+`sub` 組合せが必要な場合あり）。`exp`/`nbf`/`aud` 等の非識別クレームは `act` 内では意味を持たず使わない。
  - **入れ子 `act`** で委譲チェーン: 最外が現在のアクター、入れ子は以前のアクター、最深が最も古い。
  - **アクセス制御には、トップレベルのクレームと現在のアクター（最外 `act`）のみを考慮 MUST**。以前のアクターは情報目的のみ。
  - 例（図5）: トップレベル `sub` = user@example.com（＝**主体はユーザー**）、`act.sub` = admin@example.com（＝行動者）。
- `scope`（§4.2）: 空白区切りスコープの JSON 文字列。
- `client_id`（§4.3）: トークンを要求した OAuth クライアントの識別子。
- `may_act`（§4.4）: ある当事者が別の当事者の代理としてアクターになることを**認可されている**という表明。トークン交換時、`subject_token` 内の `may_act` で、クライアント（または `actor_token` の当事者）が委譲／成りすましを許されるか AS が判断に使える。中は識別クレームのみ。
- セキュリティ（§5）: 委譲・成りすましは乱用の可能性。`scope` と短い寿命で制限を推奨。プライバシー（§6）: TLS MUST、クライアントに見せたくない情報があれば受信者向けに暗号化 MUST、最小限のデータを SHOULD。

### 5.2 RFC 8707 Resource Indicators
URL: https://www.rfc-editor.org/rfc/rfc8707
- `resource`: 絶対 URI MUST、fragment MUST NOT、query は SHOULD NOT（必要な場合あり）。複数指定 MAY。クライアントは最も具体的な URI（通常 API のベース URI）を SHOULD（§2）。
- エラー `invalid_target`（§2）。
- AS は `resource` で示されたリソースに**audience 制限 SHOULD**（JWT では `aud`、イントロスペクションでは同名メンバー）。正確な値か、より一般的な URI／抽象識別子へのマップ MAY（§2）。
- トークン要求での `resource` + `scope` は直積。AS は可能な限りダウンスコープすべき（§2.2）。
- セキュリティ（§3）: マルチテナントでは**テナントを識別する部分（パス等）を含む resource URI** を使い、テナント間の流用を防ぐ。**単一 `resource` を推奨**。複数 audience のベアラートークンはどの RS も他の RS へアクセスできる。可能なら `resource` はネットワーク上の場所に対応させる。

### 5.3 RFC 9396 Rich Authorization Requests（`authorization_details`）
URL: https://www.rfc-editor.org/rfc/rfc9396
- `authorization_details`: JSON オブジェクトの配列。各オブジェクトの `type` は REQUIRED（API の文脈で AS 内一意）（§2）。オープン標準なら衝突耐性のある名前空間（自分が管理する URI 等）を RECOMMENDED（§2.1）。
- 共通フィールド: `locations`, `actions`, `datatypes`, `identifier`, `privileges`。1 オブジェクト内は直積の意味。細かく制御したければ複数オブジェクト（§2.2）。
- `scope` との併用可、AS は両方を組み合わせて処理 MUST。同一 API ではどちらか一方を RECOMMENDED（§3.1）。
- JWT アクセストークンでは、**audience 向けにフィルタした** `authorization_details` をトップレベルクレームとして追加を RECOMMENDED（§9.1）。イントロスペクションでは同名トップレベルメンバー MUST（§9.2）。
- ユーザーエージェント経由で改ざんされ得る。完全性が問題なら署名付きリクエストオブジェクト（RFC 9101）や PAR（RFC 9126）で保護 MUST。比較は正規化なし。インジェクション対策のサニタイズ MUST（§12）。

### 5.4 RFC 9728 OAuth 2.0 Protected Resource Metadata
URL: https://www.rfc-editor.org/rfc/rfc9728
- Resource Identifier: https スキーム、fragment なしの URL（§1.2）。
- メタデータは `/.well-known/oauth-protected-resource` をホストとパスの間に挿入した URL で公開（§3）。
- 主な項目（§2）: `resource` REQUIRED、`authorization_servers`、`jwks_uri`、`scopes_supported` RECOMMENDED、`bearer_methods_supported`、`resource_signing_alg_values_supported`（`none` MUST NOT）、`tls_client_certificate_bound_access_tokens`、`authorization_details_types_supported`、`dpop_signing_alg_values_supported`、`dpop_bound_access_tokens_required`。
- 検証（§3.3）: 返された `resource` が取得に使った識別子と**同一 MUST**、違えば使用 MUST NOT（なりすまし対策 §7.3）。
- `WWW-Authenticate` でメタデータ URL を返せる（§5）。
- 複数 RS とやり取りするクライアントは RFC 8707 で audience 制限トークンを SHOULD 要求（§7.4、悪意ある RS1 が RS2 用トークンを得て流用する攻撃）。SSRF 対策（内部 IP 範囲ブロック等）SHOULD（§7.7）。

### 5.5 RFC 7800 `cnf`（Proof-of-Possession）
URL: https://www.rfc-editor.org/rfc/rfc7800#section-3
- `cnf` は PoP 鍵を識別するメンバーを含むオブジェクト。未理解のメンバーは無視 MUST（§3.1）。
- `cnf` は**単一の PoP 鍵のみ** MUST（`jwk`/`jwe`/`jku` は高々 1 つ）。複数鍵が必要なら別のクレーム名を定義（§3.1）。
- メンバー: `jwk`（公開鍵。対称鍵なら JWT 暗号化必須、§3.2）、`jwe`（暗号化対称鍵、§3.3）、`kid`（§3.4）、`jku`（§3.5、複数鍵なら `kid` 併記 MUST）。
- IANA "JWT Confirmation Methods" レジストリを設立（§6.2）。DPoP の `jkt`、mTLS の `x5t#S256` はここに登録。

### 5.6 RFC 9449 DPoP
URL: https://www.rfc-editor.org/rfc/rfc9449
- DPoP proof JWT ヘッダー（§4.2）: `typ` = `dpop+jwt`、`alg` = 非対称署名（`none`・MAC は MUST NOT）、`jwk` = 公開鍵（秘密鍵を含めない MUST）。
- ペイロード（§4.2）: `jti`（≥96 bit の擬似乱数または UUIDv4 等）、`htm`（HTTP メソッド）、`htu`（query/fragment を除くターゲット URI）、`iat`。アクセストークンと併用時は `ath`（アクセストークンの SHA-256 の base64url）MUST。サーバが `DPoP-Nonce` を出したら `nonce` MUST。
- 検証（§4.3、12 項目）: DPoP ヘッダーは 1 つ、単一の整形式 JWT、必須クレーム、`typ`、`alg`（許可済み非対称）、`jwk` で署名検証、`jwk` に秘密鍵なし、`htm`/`htu` 一致、`nonce` 一致、`iat`（または nonce）が許容窓内、アクセストークン併用なら `ath` 一致と**トークンに束縛された公開鍵と proof の鍵の一致**。
- アクセストークン側（§6.1）: `cnf.jkt` = DPoP 公開鍵の JWK SHA-256 Thumbprint（RFC 7638）の base64url。RS は proof の鍵とトークン束縛鍵の一致を MUST 確認（§6）。
- リプレイ（§11.1）: proof は作成後短時間（秒〜分）のみ受理 MUST。`jti` を受理窓の間保存して重複拒否が可能（分散環境では困難な場合あり）。巨大 `jti` は拒否するかハッシュのみ保存。
- IANA で `htm`/`htu`/`ath` を JWT クレームとして登録、`nonce` の登録を更新（§12.7）。

### 5.7 RFC 8705 mTLS 証明書束縛アクセストークン
URL: https://www.rfc-editor.org/rfc/rfc8705#section-3
- トークンエンドポイントで使ったクライアント証明書にアクセストークンを束縛。RS は TLS 層から証明書を得て一致を MUST 検証、不一致は 401 `invalid_token`（§3）。
- JWT では `cnf` の `x5t#S256`（DER 証明書の SHA-256 の base64url、パディングなし MUST）を SHOULD 使用（§3.1）。
- アクセストークン自体は TLS ハンドシェイク後のアプリデータなので、mTLS を要求するかの判断材料にはならない（§3）。

### 5.8 RFC 9700 OAuth 2.0 Security BCP（2025-01）のトークン／クレーム関連
URL: https://www.rfc-editor.org/rfc/rfc9700
- **§2.2.1** アクセストークンの送信者制約（mTLS / DPoP）を SHOULD（盗難・漏えいトークンの悪用防止）。
- **§2.2.2** パブリッククライアントのリフレッシュトークンは送信者制約またはローテーション MUST。
- **§2.3** 権限は最小限に SHOULD。**アクセストークンは特定 RS（無理なら少数の RS）に audience 制限 SHOULD**。RS はリクエストごとに自分宛かを検証し、違えば **MUST 拒否**。`aud`（RFC 9068）を使って MAY。さらに特定リソース・アクションへの制限 SHOULD（`scope`, `authorization_details`）。
- **§2.6 / §4.15.1** クライアント ID とユーザー識別子が共通名前空間（例: `sub`）にある場合、クライアントに `client_id` 等の混同を招くクレームへの影響を許すべきでない（SHOULD NOT）。避けられないなら RS が 2 種のトークンを区別できる手段を MUST 提供。**§4.15** は RFC 9068 の `sub` が「ユーザー」か「クライアント」かで混同し得る攻撃を説明。
- **§4.9.3** 送信者制約 SHOULD、audience 制限 SHOULD、RS はアクセストークンを平文で保存・転送 MUST NOT。
- **§4.10.2** audience はフィッシング対策のため**クライアントが実際に送る URL** を使う必要。RS の X.509 証明書フィンガープリントを audience にする変種も可。audience 制限は RS 専用のフォーマット・内容でトークンを発行でき、構造化トークンでのプライバシーにも利点。
- **§4.14.2** リフレッシュトークン: 発行可否はリスク評価で MUST 決定。発行するなら同意されたスコープと RS に束縛 MUST。パブリッククライアントは送信者制約かローテーション MUST（ローテーションでは無効化済みトークンの再使用で侵害を検知しアクティブなものを失効）。トークン自体にグラントを符号化するなら完全性（署名等）MUST。パスワード変更・ログアウト等で自動失効 MAY。非アクティブ時は SHOULD 失効。
- **§4.6.1** 純 OAuth ではアクセストークン注入は検知不能。OIDC の `at_hash`+`nonce` で緩和。
- §4.4 Mix-Up 攻撃と issuer 識別による防御（§4.4.2.1）も参照（本ノートでは本文未精読 **[未検証: 詳細]**）。

---

## 6. SET・Subject Identifier・Shared Signals

### 6.1 RFC 8417 Security Event Token (SET)
URL: https://www.rfc-editor.org/rfc/rfc8417
- コアクレーム（§2.2）: `iss` REQUIRED（SET の発行者はイベント対象の issuer と同じとは限らない）、`iat` REQUIRED、`jti` REQUIRED（イベントフィード内で一意 MUST）、`aud` RECOMMENDED、`sub` OPTIONAL（使うならプロファイルが内容と形式を MUST 定義）、**`exp` は NOT RECOMMENDED**（SET は過去の出来事を表すため）。
- 新クレーム（§2.2）:
  - `events`: キー＝イベント URI、値＝JSON オブジェクト（空可）。同一イベント ID の重複 MUST NOT、独立した複数の論理イベントの表現に使用 MUST NOT。
  - `txn`: 関連する複数 JWT を相関させる取引 ID（OPTIONAL）。**SET 以外の JWT でも使える**。
  - `toe`: イベント発生時刻（NumericDate、OPTIONAL）。
- 明示的型付け（§2.3）: `application/secevent+jwt`、`typ` は `secevent+jwt` を SHOULD。混同し得る文脈では MUST。
- 混同防止（§4）: ID Token と混同し得る SET プロファイルは **`exp` を含めないことを MUST 要求**（ID Token 検証は `exp` 必須なので拒否される）。`typ` は ID Token 検証で見られないため ID Token との区別にはならない（§4.1）。アクセストークンとの区別には `exp` 禁止、別の `aud`、`events` の有無チェック、`typ` 検証を推奨（§4.2）。

### 6.2 RFC 9493 Subject Identifiers for SETs（`sub_id`）
URL: https://www.rfc-editor.org/rfc/rfc9493
- Subject Identifier は `format` メンバーを MUST 持つ JSON オブジェクト（§3）。フォーマット名は IANA "Security Event Identifier Formats" 登録か Collision-Resistant Name MUST。
- 登録フォーマット（§3.2）: `account`, `email`, `iss_sub`, `opaque`, `phone_number`, `did`, `uri`, `aliases`。最も具体的なフォーマットを SHOULD 選択（メールなら `uri` の mailto でなく `email`）。
- **`sub_id` クレーム**（§4.1）: `sub` は文字列なので構造化識別子を入れられない→ `sub_id` を定義。`sub` の有無に関係なく MAY。両方あれば同じ subject を MUST 指す。両方に依存して subject を決定 MUST NOT（一方が理解できなければもう一方にフォールバック MAY）。
- `iss_sub` 形式では JWT の `iss` とメンバーの `iss` が異なってよい（§4.2）。
- プライバシー（§6.1）: 複数識別子（`aliases` や `sub`+`sub_id`）を一緒に送ると相関情報を与える。受信者が既に関連を知っているか、相関が必須の場合のみ SHOULD。

### 6.3 OpenID Shared Signals Framework 1.0 / CAEP 1.0 / RISC 1.0（Final）
- SSF: https://openid.net/specs/openid-sharedsignals-framework-1_0.html（2025-08-29 公開）
- CAEP: https://openid.net/specs/openid-caep-1_0.html
- RISC: https://openid.net/specs/openid-risc-1_0.html
- Final 承認告知: https://openid.net/wg/sharedsignals/ （"Three Shared Signals Final Specifications Approved – 2nd Sept 2025"）

SSF の SET プロファイル（SSF §4.1）:
- 明示的型付け MUST（`typ: secevent+jwt`）（§4.1.1）。
- **JWT の `sub` クレームは MUST NOT 存在**。主体は Subject Members（`sub_id` 等）で表す（§4.1.2, §4.1.3）。
- **`exp` は MUST NOT**（他 JWT との混同対策）（§4.1.7）。
- `iss` はストリーム設定の `iss` と一致 MUST、受信者は検証 MUST（§4.1.6）。
- `aud` は文字列または配列。複数値は同一エンティティと分かっている受信者の場合のみ（§4.1.8）。
- `txn` を SHOULD 設定、同一の根本原因のイベントに同じ値を使ってよい（§4.1.9）。
- `events` は原則 1 イベントのみ SHOULD（§4.2.1）。
- 署名鍵は `jwks_uri` で取得（§4.1.4）。

CAEP イベント（CAEP §3、URI 接頭辞 `https://schemas.openid.net/secevent/caep/event-type/`）:
- `session-revoked`, `token-claims-change`, `credential-change`, `assurance-level-change`, `device-compliance-change`, `session-established`, `session-presented`, `risk-level-change`。
- 共通任意クレーム（§2）: `event_timestamp`（数値秒）、`initiating_entity`（`admin`/`user`/`policy`/`system`）、`reason_admin`、`reason_user`（BCP47 言語タグをキーにした多言語オブジェクト）。
- `token-claims-change` は `claims`（新しい値を持つ 1 つ以上のクレーム）REQUIRED（§3.2.1）。→ トークン内クレームの変更（例: ロール剥奪）を受信者に即時伝える標準手段。

RISC イベント（RISC §2、接頭辞 `https://schemas.openid.net/secevent/risc/event-type/`）:
- `account-credential-change-required`, `account-purged`, `account-disabled`, `account-enabled`, `identifier-changed`, `identifier-recycled`, `credential-compromise`, `opt-in`, `opt-out-initiated`, `opt-out-cancelled`, `opt-out-effective`, `recovery-activated`, `recovery-information-changed`, `sessions-revoked`。
- `identifier-recycled` の存在自体が、メール等の識別子が再利用され得る（OIDC §5.7）ことの実運用上の裏付け。

---

## 7. 寿命・失効・イントロスペクション

### 7.1 RFC 7009 Token Revocation
URL: https://www.rfc-editor.org/rfc/rfc7009
- リフレッシュトークンの失効サポート MUST、アクセストークンの失効は SHOULD（§2）。
- リフレッシュトークン失効時、AS がアクセストークン失効をサポートするなら同一グラントのアクセストークンも SHOULD 無効化。アクセストークン失効時はリフレッシュトークンも MAY（§2.1）。
- 実装ノート（§3）: 自己完結型トークンでは即時失効に（非標準の）AS–RS 間連携が必要。代替は**短命アクセストークン＋リフレッシュ**で、失効の影響時間を制限。選択はリスク分析次第。

### 7.2 RFC 7662 Token Introspection
URL: https://www.rfc-editor.org/rfc/rfc7662
- 応答の `active` REQUIRED。他に `scope`, `client_id`, `username`, `token_type`, `exp`, `iat`, `nbf`, `sub`, `aud`, `iss`, `jti` 等（§2.2）。
- AS は失効・期限・開始時刻・署名・**呼出 RS で使えるか**を含む全チェック MUST（§4）。
- イントロスペクションエンドポイントは呼出側の認証 MUST（トークン探索攻撃対策）（§4）。
- 非アクティブトークンの応答は `active: false` 以外を含めない SHOULD（§4）。
- キャッシュは失効の反映遅延とのトレードオフ。応答に `exp` があればそれを超えてキャッシュ MUST NOT（§4）。
- プライバシー: ユーザー識別子は RS ごとに異なる不透明値で返す方法あり（§5）。

### 7.3 RFC 9701 JWT Response for Token Introspection
URL: https://www.rfc-editor.org/rfc/rfc9701#section-5
- 応答は `application/token-introspection+jwt`、`typ: token-introspection+jwt`。
- 必須クレーム: `iss`、`aud`（受信 RS）、`iat`、`token_introspection`（RFC 7662 応答メンバーを格納するオブジェクト。トップレベルクレームとの衝突回避のため分離）。
- 無効・期限切れ・失効・**呼出 RS 宛でない**トークンは `active: false` のみ MUST。スコープは RS 関連に絞る SHOULD。
- **`sub` と `exp` は SHOULD NOT 含める**（アクセストークンとしての誤用防止）。この JWT はアクセストークンの代替表現ではない。

### 7.4 Token Status List（draft-ietf-oauth-status-list-21、RFC Editor Queue）
URL: https://datatracker.ietf.org/doc/draft-ietf-oauth-status-list/
- 参照トークン（JWT/SD-JWT/CWT 等）に `status` クレームを入れ、`status_list` メンバーでビット配列上の位置を指す。ステータスリスト自体は署名付きトークンとして配布（§1, §6.1–6.2）。
- `status`/`status_list`/`ttl` は IANA に既に登録済み（`RFC-ietf-oauth-status-list-21` として）。
- RFC 番号は未割当 **[状態は 2026-11-17 時点]**。

### 7.5 短命アクセストークン vs イントロスペクション（設計判断の整理）
- 自己完結型 JWT: RS で検証完結。失効は即時反映されず、**影響時間は `exp` までの寿命**で制限（RFC 7009 §3）。
- 参照型／イントロスペクション: 失効を即時反映可能だが、往復とキャッシュのトレードオフ（RFC 7662 §4）。
- 中間策: 短命 JWT＋リフレッシュ（RFC 7009 §3）、CAEP `session-revoked` / `token-claims-change` による能動通知（CAEP §3）、ステータスリスト（draft）。
- 具体的な推奨寿命（例: 5 分、1 時間）は本ノートで確認した一次資料に規範値なし **[未検証: 推奨値]**。Logout Token のみ「できれば 2 分以内」（BCL §4）、DPoP proof は「秒〜分」（RFC 9449 §11.1）。

---

## 8. SD-JWT（RFC 9901）— クレーム設計に関係する部分のみ

URL: https://www.rfc-editor.org/rfc/rfc9901（2025-11、Standards Track）
- 形式: `<Issuer-signed JWT>~<Disclosure 1>~...~<Disclosure N>~[<KB-JWT>]`（§4）。
- Issuer 署名 JWT は署名 MUST、`none` MUST NOT（§4.1）。
- `_sd`: オブジェクトプロパティの Disclosure ダイジェスト配列（任意階層）（§4.2.4.1）。配列要素は `...`（§4.2.4.2）。`_sd`/`...` をダイジェスト以外の目的で使用 MUST NOT（§4.1）。
- `_sd_alg`: ハッシュアルゴリズム。トップレベルのみ、無ければ `sha-256`（§4.1.1）。
- 囮ダイジェスト（decoy）でクレーム数を隠せる（§4.2.5）。
- **鍵束縛**: Holder の公開鍵を `cnf`（RFC 7800、`jwk` を提案）で入れる（§4.1.2）。KB-JWT は `typ: kb+jwt` MUST、`iat`/`aud`（単一文字列）/`nonce`/`sd_hash` REQUIRED（§4.3）。
- **§9.7 有効性クレームを選択開示にしてはならない**: 真正性・有効性評価に重要な内容を選択開示可能にすること MUST NOT。`iss`、`aud`（配列の個別要素は MAY）、`exp`、`nbf`、`cnf` はセキュリティ上重要と SHOULD 扱う。Verifier は必要な有効性クレームが存在（開示）することを MUST 確認。
- 明示的型付け `application/example+sd-jwt`、`typ: example+sd-jwt` を RECOMMENDED（§9.11）。
- 鍵束縛を強制しないと、SD-JWT 保持者は開示を減らして第三者へ転送できる（§9.9）。
- IANA に `_sd`、`...`、`_sd_alg`、`sd_hash` を登録（§11.1）。

---

## 9. IANA "JSON Web Token Claims" レジストリ

URL: https://www.iana.org/assignments/jwt/jwt.xhtml（取得した XML の `updated` = 2026-10-28）

### 9.1 登録ルール
- **Specification Required**、jwt-reg-review@ietf.org での 3 週間レビュー後、Designated Experts の助言で登録。Expert は既存機能との重複、汎用性（単一アプリ専用でないか）、説明の明確さを判断。RFC 7519 §10.1 — https://www.rfc-editor.org/rfc/rfc7519#section-10.1
- 含意: 社内／組織固有クレームは通常登録対象ではなく、**Collision-Resistant Name（自社ドメイン URI 等）を使う Public Name**（§4.2）か、閉じたサブシステム内の Private Name（§4.3）にする。

### 9.2 主な登録クレーム（基本 7 種以外、定義元はレジストリ記載）
| クレーム | 定義元 |
|---|---|
| OIDC 標準クレーム（`name` 〜 `updated_at`）、`azp`, `nonce`, `auth_time`, `at_hash`, `c_hash`, `acr`, `amr`, `sub_jwk` | OpenID Connect Core 1.0（`nonce` は RFC 9449 でも更新） |
| `_claim_names`, `_claim_sources` | OIDC Core（集約／分散クレーム） |
| `cnf` | RFC 7800 §3.1 |
| `events`, `toe`, `txn` | RFC 8417 §2.2 |
| `sid` | OpenID Connect Front-Channel Logout 1.0 |
| `vot`, `vtm` | RFC 8485（Vectors of Trust） |
| `act`, `scope`, `client_id`, `may_act` | RFC 8693 §4.1–4.4 |
| `roles`, `groups`, `entitlements` | RFC 7643 §4.1.2 ; RFC 9068 §2.2.3.1 |
| `token_introspection` | RFC 9701 §5 |
| `authorization_details` | RFC 9396 §9.1 |
| `htm`, `htu`, `ath` | RFC 9449 §4.2 |
| `sub_id` | RFC 9493 §4.1 |
| `_sd`, `...`, `_sd_alg`, `sd_hash` | RFC 9901 |
| `verified_claims` | OpenID Identity Assurance Schema Definition 1.0 |
| `place_of_birth`, `nationalities`, `birth_family_name`, `birth_given_name`, `birth_middle_name`, `salutation`, `title`, `msisdn`, `also_known_as` | OpenID Connect for Identity Assurance Claims Registration |
| `status`, `status_list`, `ttl` | draft-ietf-oauth-status-list-21 |
| `ace_profile`, `cnonce`, `exi` | RFC 9200（ACE） |
| `vc`, `vp` | W3C VC Data Model（2019） |
| `location`, `ueid`, `oemid`, `hwmodel`, `swname` 等 | RFC 9711（EAT: デバイス証明） |
| `cdniip` 等 `cdni*` | CDNI URI Signing（RFC 9246） |
| `jwks`, `metadata`, `trust_marks` 等, `crit`（クレームとしての） | OpenID Federation 1.0 |
| `sip_*`, `orig`, `dest`, `mky`, `attest`, `rcd` 等 | SIP/STIR（電話系） |
| 3GPP 系（`consumerPlmnId` 等）, `geohash`（CTA-5009）, `rdap_*` | 各分野別 |

- **`org` / `tenant` / `organization` / `tid` に相当する登録クレームは無い**（2026-10-28 版レジストリで確認）。datatracker の draft 名・題名検索（"tenant"/"organization"）でも JWT クレームとして採択された draft は見当たらない（ネットワーク層の Tenant ID や SCIM 拡張の個人 draft のみ）。**[網羅検索ではない]**
- **同意・目的（consent/purpose）の汎用登録クレームは無い**（`rdap_allowed_purposes` は RDAP 専用）。

---

## 10. 用途別：既存のクレーム地図（組織横断カスタムクレーム設計の前提）

凡例: 「既存」= 標準または登録済みクレーム、「意味しないこと」= 誤用されやすい点、「ギャップ」= カスタムクレームが正当化される余地。

### 10.1 ユーザー識別
- 既存: `iss`+`sub`（RFC 7519 §4.1.1–4.1.2、OIDC Core §2, §5.7）。`sub_id`（RFC 9493 §4.1、構造化識別子）。
- 意味・型: `sub` は issuer 内ローカル一意・再割当なし（OIDC）、255 ASCII 以内、大文字小文字区別。pairwise なら RP（セクター）ごとに異なる（OIDC §8）。
- 意味しないこと: `email` / `preferred_username` / `phone_number` / `name` は一意キーではない（OIDC §5.7 MUST NOT）。`sub` 単独は issuer をまたいで一意ではない。
- ギャップ: 社内の複数 IdP／複数セクターをまたぐ「社員番号」等の安定キー。ベンダー例: Entra の `oid` は「テナント内でアプリをまたいで同一」、`sub` はアプリごとの pairwise（ベンダー独自; https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference ）。SAML 側の類例は `subject-id` / `pairwise-id`（§11.2）。

### 10.2 テナント／組織
- 既存の登録クレーム: **なし**（§9.2）。
- ベンダー独自:
  - Entra `tid`: ユーザーがサインインしているテナントの GUID。「認可判断では他のクレームと組み合わせて考慮すべき」。`profile` スコープが必要（ベンダー独自; Entra access token claims reference）。SAML では `http://schemas.microsoft.com/identity/claims/tenantid`（Entra SAML token reference）。
  - Auth0 `org_id`（設定により `org_name` も）。Organization 経由のログインで ID/アクセストークンに入る。SDK が検証するが追加検証を推奨、`org_id` での検証が望ましい（ベンダー独自; https://auth0.com/docs/manage-users/organizations/using-tokens ）。
  - Keycloak `organization`: `organization` スコープ要求時、`{"<alias>": {"id": ..., ...}}` 形式（ベンダー独自; https://www.keycloak.org/docs/latest/server_admin/index.html Organizations 節）。
  - Okta の組織クレーム: 確認できず **[未検証]**。
- 代替の標準手段: マルチテナント RS は**テナントを含む resource URI で `aud` を分ける**（RFC 8707 §3）。issuer をテナント別にする（RFC 8725 §3.12 の「別 issuer」戦略）。
- ギャップ: 組織横断でテナント／組織を表す標準クレームは存在しないため、カスタムクレームの正当な候補。ただし `aud`/`iss` 分離で済む設計を先に検討。

### 10.3 ロール／グループ／エンタイトルメント
- 既存: `roles`, `groups`, `entitlements`（RFC 9068 §2.2.3.1 で SHOULD、型・意味は RFC 7643 §4.1.2）。
- RFC 7643 §4.1.2 の意味:
  - `groups`: 直接・ネスト・動的に所属するグループ。グループ／ロールベースのアクセス制御を表現する意図だが**認可モデルは定義しない**。意味はサービス提供者が定義。`direct`/`indirect` の型。
  - `entitlements`: ユーザーが「持つもの」（権利）。**語彙・構文なし**。
  - `roles`: ユーザーが「何者か」を表すロール（例 "Student"）。**語彙・構文なし**、エンタイトルメントの集合を表すラベルを想定。
- 意味しないこと: 値の語彙は標準化されていない。RS 間で同じ文字列が同じ意味とは限らない。ベンダーの `roles` は意味が異なる（Entra の `roles` は対象アプリのアプリロール／アプリ権限、`wids` はテナント全体のディレクトリロール; ベンダー独自）。Keycloak は `realm_access.roles` / `resource_access.<client>.roles` をデフォルトで使用（ベンダー独自）。
- ギャップ: 名前は標準を使い、**値の語彙（URI 名前空間等）を組織で定義**するのが筋。大量グループはトークン肥大化に注意（Entra は JWT 200 / SAML 150 超で超過クレームに切替; ベンダー独自）。

### 10.4 権限／スコープ
- 既存: `scope`（RFC 8693 §4.2、空白区切り文字列）。RFC 9068 §2.2.3 で SHOULD、各スコープは `aud` のリソースにとって意味を持つ MUST。
- 意味しないこと: `scope` は**クライアントに委譲された権限**であり、ユーザーが持つ全権限ではない。複数 `aud` との対応が曖昧なら発行 MUST NOT（RFC 9068 §3, §5）。
- ベンダー差: Entra は `scp`（ユーザートークン）／`roles`（アプリ権限）、Auth0 は Organization ロール由来の `permissions` クレーム（ベンダー独自）。

### 10.5 細粒度認可
- 既存: `authorization_details`（RFC 9396 §9.1）。`type` 必須、`locations`/`actions`/`datatypes`/`identifier`/`privileges`。
- 意味: クライアントが要求しユーザー／AS が承認した**具体的な取引単位の認可**（例: 決済指図）。audience 向けにフィルタして入れる。
- ギャップ: `type` ごとのスキーマは API 設計者が定義（URI 名前空間推奨、§2.1）。独自の「permission オブジェクト」クレームを作る前に `authorization_details` の `type` 定義で表現できないか検討。

### 10.6 認証の強度・鮮度
- 既存: `acr`（保証クラス、当事者間で意味の合意が必要）、`amr`（使用方式の配列、RFC 8176 値）、`auth_time`（認証時刻）（OIDC Core §2、RFC 9068 §2.2.1）。`vot`/`vtm`（RFC 8485 §3.2、ID Token 内のベクトル・オブ・トラスト）。
- 意味しないこと: `amr: ["mfa"]` は保証レベルを意味しない。`acr` 値の意味は合意次第。`auth_time` は ID Token の `iat` とは別（再認証なしの再発行あり）。アクセストークンでは認可応答時に確定し、リフレッシュで変わらない（RFC 9068 §2.2.1）。
- 連携: 不足時は RFC 9470 の `insufficient_user_authentication` + `acr_values`/`max_age`。
- ベンダー差: Entra の `acrs`（認証コンテキスト ID）＋`xms_cc`（ベンダー独自）。

### 10.7 セッション
- 既存: `sid`（Front-/Back-Channel Logout、issuer 文脈で一意、RP に不透明）（BCL §2.1, §2.4）。
- 意味しないこと: RP 内のアプリセッション ID ではなく **OP 側セッション**の識別子。ID Token の `exp` はセッション寿命と無関係（OIDC §2）。
- 失効通知: Logout Token（BCL）、CAEP `session-revoked`。

### 10.8 委譲／アクター
- 既存: `act`（現在のアクター、入れ子で履歴）、`may_act`（アクター資格の表明）（RFC 8693 §4.1, §4.4）。
- 意味: トップレベル `sub` は**代理される主体**。アクセス制御はトップレベル＋最外 `act` のみ（MUST）。
- ギャップ: 委譲の「理由」「承認者」等は未定義 → 必要ならカスタム（ただし `act` 内は識別クレームのみという制約に留意し、`act` の中に権限情報を入れない）。

### 10.9 クライアント／ワークロード
- 既存: `client_id`（RFC 8693 §4.3、要求したクライアント）、`azp`（OIDC Core §2、ID Token が発行された当事者。errata 2 では通常使わない）。
- 意味しないこと: RFC 9068 で client credentials の `sub` はクライアントを指す場合があり、ユーザー `sub` と混同の危険（RFC 9700 §4.15）。
- ベンダー差: Entra `azp`（v2、クライアントのアプリ ID）、`azpacr`（クライアント認証方式 0/1/2）、`idtyp: app`（アプリ専用トークンの判別）（ベンダー独自）。
- ギャップ: 「ユーザートークンかアプリ専用トークンか」の判別を `sub` の形だけに頼らない仕組み（RFC 9700 §4.15.1 は区別手段を MUST 提供と規定）→ 明示的クレームの候補。ワークロード ID 系の IETF 仕様（WIMSE 等）は本ノートでは未調査 **[未検証]**。

### 10.10 所持証明（PoP）
- 既存: `cnf`（RFC 7800）＋ `jkt`（DPoP、RFC 9449 §6.1）、`x5t#S256`（mTLS、RFC 8705 §3.1）、`jwk`/`kid`/`jku`/`jwe`。
- 意味: トークン提示者が特定鍵を持つことの検証手段。単一鍵のみ。
- ギャップ: 原則なし。独自の「端末バインディング」クレームを作る前に `cnf` を使う。

### 10.11 イベント
- 既存: `events`, `toe`, `txn`（RFC 8417 §2.2）、SSF/CAEP/RISC の各イベント型。
- 注意: `txn` は SET 以外の JWT でも使える相関 ID（RFC 8417 §2.2）。

### 10.12 同意／目的
- 既存: 汎用の登録クレームなし（§9.2）。関連: `scope` / `authorization_details` が同意済み内容の表現手段（RFC 9396 §3.1 は同意画面で統合要件を提示 MUST）。
- ギャップ: 目的（purpose）・同意記録 ID はカスタムの正当な候補。外部標準（Kantara Consent Receipt 等）は未調査 **[未検証]**。

### 10.13 ロケール／プロフィール
- 既存: `locale`, `zoneinfo`, `name`, `given_name`, `family_name`, `picture`, `profile`, `website`, `birthdate`, `gender`, `address` 等（OIDC Core §5.1）。
- 意味しないこと: 表示用・本人申告ベースで、検証済みとは限らない。一意性なし（§5.7）。
- ベンダー差: Entra `ctry` / `tenant_ctry`（ベンダー独自、任意クレーム）。

### 10.14 デバイス／IP／位置
- 既存の登録クレーム:
  - `location`（RFC 9711 §4.2.10）: **証明（attestation）を発する機器の地理的位置**（緯度経度必須）。ユーザーのログイン位置ではない。EAT 文脈。
  - `cdniip`（RFC 9246 §2.1.10）: **CDN 署名 URI が有効な IP/プレフィックス**。PII なので JWE MUST。汎用の「クライアント IP」クレームではない。
  - `geohash`（CTA-5009）, `ueid`/`hwmodel` 等（RFC 9711）: デバイス証明用。
- ベンダー独自: Entra `ipaddr`（ユーザーが認証した IP）、`xms_*` 系（Microsoft 拡張）（https://learn.microsoft.com/en-us/entra/identity-platform/optional-claims-reference ）。
- ギャップ: 認証時のクライアント IP・デバイス準拠状態をアクセストークンに載せる汎用標準はない → カスタム候補。ただし変化する状態は CAEP `device-compliance-change` / `risk-level-change` の通知の方が適切な場合がある。プライバシー上の扱い（RFC 9068 §6）に注意。

### 10.15 検証済みアイデンティティ（eKYC）
- 既存: `verified_claims`（OpenID Identity Assurance Schema Definition 1.0 §5, Final 2026-07）。構造: `verification`（`trust_framework` REQUIRED、`assurance_level`、`assurance_process`、`time`、`verification_process`、`evidence` 等）＋ `claims`（検証済みクレーム、空も可）。単一オブジェクトまたは配列。目的は**検証済みクレームと未検証クレームを受信者が混同しないこと**（§5.1）。理解できない `trust_framework` の `verified_claims` は無視すべき（§5.4.2）。
- 追加の登録クレーム: `place_of_birth`, `nationalities`, `birth_family_name` 等（OIDC4IDA Claims）。
- 意味しないこと: トップレベルの `given_name` 等は検証済みを意味しない。`email_verified` は「検証時点でメールを管理していた」ことのみ（OIDC §5.1）。

### 10.16 失効状態
- 既存: `status`/`status_list`（Token Status List draft、IANA 登録済み）。
- 意味: 参照トークンの状態（無効化・一時停止等）を取得する仕組みへの参照。

---

## 11. SAML 属性と JWT クレームの対応

### 11.1 SAML 2.0 属性プロファイル（OASIS saml-profiles-2.0-os, 2005-03）
URL: https://docs.oasis-open.org/security/saml/v2.0/saml-profiles-2.0-os.pdf
- **§8.1 Basic Attribute Profile**: 「単純だが**一意でない**命名」。`NameFormat` は `urn:oasis:names:tc:SAML:2.0:attrname-format:basic` MUST。属性値は XML Schema 組込み型、`xsi:type` MUST。例 `Name="FirstName"`。
- **§8.2 X.500/LDAP Attribute Profile**: `NameFormat` は `urn:oasis:names:tc:SAML:2.0:attrname-format:uri` MUST。名前は `urn:oid:` URN（RFC 3061）で属性型の OID に基づく（例 `urn:oid:2.5.4.3`）。人間可読の `FriendlyName` は MAY だが**比較には関与しない**。値には `Encoding` XML 属性 MUST。eduPerson や inetOrgPerson のスキーマを SAML で使うための規約。
- 他: UUID（§8.3）、DCE PAC（§8.4）、XACML（§8.5）属性プロファイル。
- 含意: SAML では URI/OID 名で衝突耐性を確保するのが標準的。JWT の Collision-Resistant Name（RFC 7519 §4.2）と同じ発想。

### 11.2 SAML の識別子属性（OASIS SAML V2.0 Subject Identifier Attributes Profile v1.0, CS01, 2019）
URL: https://docs.oasis-open.org/security/saml-subject-id-attr/v1.0/cs01/saml-subject-id-attr-v1.0-cs01.pdf
- `urn:oasis:names:tc:SAML:attribute:subject-id`（§3.3）: 長期・再割当なし・**全 RP 共通**の識別子。`<uniqueID>@<scope>` 形式、**大文字小文字無視で比較 MUST**。メールアドレスとして扱わない。名前・メール・ロール変更で変わるべきでない。
- `urn:oasis:names:tc:SAML:attribute:pairwise-id`（§3.4）: 長期・再割当なし・**RP ごと（一方向）**の識別子。
- OIDC の `public`/`pairwise` `sub` に対応する概念（ただし比較規則が異なる点に注意: OIDC `sub` は大文字小文字区別、subject-id は区別しない）。

### 11.3 eduPerson（REFEDS eduPerson 2020-01）
URL: https://wiki.refeds.org/display/STAN/eduPerson+2020-01
- `eduPersonEntitlement`（OID 1.3.6.1.4.1.5923.1.1.1.7、§2.2.2）: 特定リソースへの権利の集合を示す **URI（URN または URL）**、複数値。ホーム機関が資格判定を行い、リソース側は人物の属性を知らずに権利だけを受け取る。→ JWT の `entitlements`（RFC 7643）と同趣旨で、値を URI にする設計の先例。
- `eduPersonPrincipalName`（…1.6、§2.2.8）: `user@scope` のスコープ付き識別子。**変更・再割当の可能性があり多くの用途に不適**、プロトコル固有の安定識別子か `eduPersonUniqueId` を推奨。メールアドレスと見なさない。
- `eduPersonUniqueId`（…1.13、§2.2.13）: 長期・再割当なし・全方向の識別子。
- `eduPersonAffiliation` / `eduPersonScopedAffiliation`（§2.2.1, §2.2.10）: faculty/staff/student 等の広いカテゴリの所属。
- `eduPersonTargetedID`（§2.2.11）: 歴史的な RP 別識別子（詳細は本ノート未精読 **[未検証]**）。

### 11.4 Microsoft（Entra ID）の SAML 属性 URI と JWT クレームの対応（ベンダー独自）
出典: https://learn.microsoft.com/en-us/entra/identity-platform/reference-saml-tokens
| JWT クレーム | Entra SAML 表現 |
|---|---|
| `iss` | `<Issuer>` |
| `sub` | `<Subject><NameID>` |
| `aud` | `<AudienceRestriction><Audience>` |
| `iat` | `<Assertion IssueInstant>` |
| `nbf`, `exp` | `<Conditions NotBefore/NotOnOrAfter>` |
| （認証時刻） | `<AuthnStatement AuthnInstant>` |
| `amr` | `<AuthnContextClassRef>`（例 `http://schemas.microsoft.com/ws/2008/06/identity/claims/authenticationmethod/password`） |
| `given_name` | `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname` |
| `family_name` | `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname` |
| `unique_name` | `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name`（表示用、テナント内一意も保証なし） |
| `oid` | `http://schemas.microsoft.com/identity/claims/objectidentifier` |
| `tid` | `http://schemas.microsoft.com/identity/claims/tenantid` |
| `roles` | `http://schemas.microsoft.com/ws/2008/06/identity/claims/role` |
| `groups` | `http://schemas.microsoft.com/ws/2008/06/identity/claims/groups`（超過時 `http://schemas.microsoft.com/claims/groups.link`） |
| `idp` | `http://schemas.microsoft.com/identity/claims/identityprovider` |
- 注意: Entra は SAML の `AuthnContextClassRef` を `amr` 相当として表で対応付けている（ベンダー表記）。概念上 SAML の AuthnContextClassRef は OIDC の `acr`（Authentication Context Class Reference）と名称が対応するため、ブローカー設定で `acr` と `amr` のどちらに写すかは要確認 **[解釈: 規範的対応表は未確認]**。
- `xmlsoap.org/ws/2005/05/identity/claims/*` は WS-Federation／Information Card 由来の URI 群（由来の一次資料は未確認 **[未検証]**）。

### 11.5 ブローカーでの SAML → JWT マッピング
- Keycloak（ベンダー独自）: 外部 IdP からのログイン時に **Identity Provider Mapper** がユーザー情報（属性・ロール等）を取り込み、Sync Mode（`import`/`force`/`legacy`/`inherit`）で更新方針を決める。クライアント側の **Protocol Mapper（Token mappers）** が「ユーザー属性・ロール等をトークンや SAML アサーションにどう載せるか」を定義する二段構成。`identity_provider` 等のユーザーセッションノートも User Session Note マッパーで伝播可能。出典: https://www.keycloak.org/docs/latest/server_admin/index.html（Identity provider mappers / Available user session data / Token mappers 節、Keycloak 26 系）。個別マッパー型名（例 "Attribute Importer"）は取得版本文で確認できず **[未検証]**。
- Entra（ベンダー独自）: 同一の属性が JWT では短い名前（`tid` 等）、SAML では URI 名（§11.4 の表）で発行される。
- 一般的な概念対応（`iss`↔Issuer、`sub`↔NameID、`aud`↔Audience、`exp`↔NotOnOrAfter、`auth_time`↔AuthnInstant、`acr`↔AuthnContextClassRef、`sid`↔SessionIndex）を規範的に定めた単一の標準は本調査で確認できず **[未検証]**。
- 設計上の注意: SAML `NameID`（特に transient/email 形式）を JWT `sub` にそのまま写すと、OIDC §5.7 が禁じる「メール等を一意キーにする」状態を作り得る。subject-id/pairwise-id/永続 NameID を `sub` の元にするのが安全側（推論）。

---

## 12. カスタムクレーム命名の実務参考（ベンダー）

- Auth0（ベンダー独自）: 衝突回避のため衝突耐性名を推奨し、**名前空間付き形式**（自社管理の http/https URL、Auth0 ドメインと `urn:auth0` は不可）を推奨。衝突時はトランザクションは失敗せず**カスタムクレームが追加されない**。Auth0 API audience のアクセストークンには名前空間なしのプライベートクレームを入れられない。https://auth0.com/docs/secure/tokens/json-web-tokens/create-custom-claims
- Okta（ベンダー独自）: カスタムクレームはカスタム認可サーバーでのみ追加可（org 認可サーバー不可）。groups クレームの追加手順あり。https://developer.okta.com/docs/guides/customize-tokens-returned-from-okta/main/
- 標準側の根拠は RFC 7519 §4.2/§4.3、RFC 9068 §2.2.2（§1.5 参照）。

---

## 13. 設計判断に効く要点

1. **ユーザーの安定キーは `iss`+`sub` の組だけ**。`sub` は issuer 内でのみ一意で再割当されない。— OIDC Core §5.7, §2 / RFC 7519 §4.1.2
2. **`email`・`preferred_username`・`phone_number`・`name` を一意キーにしてはならない（MUST NOT）**。メールは別ユーザーに再利用され得る。— OIDC Core §5.7（RISC に `identifier-recycled` イベントがある）
3. **pairwise `sub` は RP（セクター）ごとに値が変わる**。アプリ横断で突合するならセクター設計か別の識別子が必要。— OIDC Core §8, §8.1
4. **`aud` を検証しないと、別 RS 宛のトークンを流用される（置換攻撃）**。同一 issuer が複数 RP 向けに発行するなら `aud` は MUST、RP は MUST 検証・不一致は拒否。— RFC 8725 §2.7, §3.9 / RFC 7519 §4.1.3
5. **`aud` は文字列または配列**。両方を受け付ける実装にする。複数 audience のベアラートークンは受け取った RS が他 RS で使えるので、単一 audience を推奨。— RFC 7519 §4.1.3 / RFC 8707 §3
6. **リソースごとに別個の `aud` を割り当てる（MUST）**。マルチテナントならテナント部分を含む resource URI で分ける。— RFC 9068 §5 / RFC 8707 §3
7. **`iss` は完全一致で比較し、その issuer の鍵で署名されたことを確かめる**（MUST）。— RFC 9068 §4 / OIDC Core §3.1.3.7 / RFC 8725 §3.8
8. **アルゴリズムは許可リストで固定し、各鍵は 1 つのアルゴリズムでのみ使う**。`none` は拒否し、ブロックリスト（`noNE` で回避される）は使わない。— RFC 8725 §3.1, §3.2 / 8725bis §2.11, §3.1
9. **新しい種類の JWT には明示的型付け（`typ: xxx+jwt`）を入れ、検証側で確認する**。`typ: "JWT"` では型付けにならない。アクセストークンは `at+jwt` MUST。— RFC 8725 §3.11 / 8725bis §3.11 / RFC 9068 §2.1, §4
10. **同じ issuer が出す JWT 同士で検証規則が相互に排他的になるように設計する**（typ・必須クレーム・鍵・aud・iss のいずれかで区別）。— RFC 8725 §3.12
11. **`kid`/`jku`/`x5u` は攻撃者が制御できる入力**。インジェクション（MUST 対策）と SSRF（許可リスト、ローカル IP 解決拒否）に備える。— RFC 8725 §3.10 / 8725bis §3.10
12. **`exp`/`nbf` の leeway は「数分以内」が上限の目安**。`exp` ちょうどの時刻はもう無効（「以降」は受理しない）。— RFC 7519 §4.1.4–4.1.5
13. **ID Token の `exp` はログインセッションの寿命ではない**。セッションは `sid`／Logout Token／CAEP で扱う。— OIDC Core §2 / BCL §2.4
14. **RFC 9068 では `sub` がユーザーにもクライアントにもなる**。クライアントに `client_id` を自由に決めさせない。ユーザー用トークンとアプリ専用トークンを RS が区別できる手段を必ず用意する（MUST）。— RFC 9068 §2.2, §5 / RFC 9700 §4.15.1
15. **`scope` はクライアントに委譲された範囲であり、各スコープは `aud` のリソースにとって意味を持つ必要がある（MUST）**。対応が曖昧ならトークンを発行しない。— RFC 9068 §2.2.3, §3
16. **ロール・グループは独自名を作らず `roles`/`groups`/`entitlements` を使う（SHOULD）**。値の語彙は標準化されていないので組織で定義する。— RFC 9068 §2.2.3.1 / RFC 7643 §4.1.2
17. **IANA 登録済みのクレームで意味が足りる属性は登録名を使う（SHOULD）**。独自クレームは、自社が管理する名前空間（URI 等）を使った衝突耐性のある名前にする。— RFC 9068 §2.2.2 / RFC 7519 §4.2, §4.3
18. **テナント／組織と同意・目的を表す登録クレームは無い（2026-10 時点）**。`tid`・`org_id` はベンダー独自のクレームで、カスタムクレームを設計する正当な余地がある。— IANA JWT Claims（2026-10-28）/ Entra・Auth0 ドキュメント
19. **委譲では `sub` が代理される主体、`act` が実際に行動する主体**。認可判断に使うのはトップレベルのクレームと最外の `act` だけ（MUST）。— RFC 8693 §1.1, §4.1
20. **`amr` は使った認証方式の事実、`acr` は合意された保証クラス**。どちらも認証時に確定し、リフレッシュしても変わらない。不足していれば RFC 9470 のチャレンジで step-up を求める。— OIDC Core §2 / RFC 8176 §2 / RFC 9068 §2.2.1 / RFC 9470 §3, §6.1
21. **盗まれたトークン対策の本命は送信者制約（DPoP の `cnf.jkt`、mTLS の `cnf.x5t#S256`）**。パブリッククライアントのリフレッシュトークンは送信者制約かローテーションが MUST。— RFC 9700 §2.2 / RFC 9449 §6.1 / RFC 8705 §3.1
22. **自己完結型 JWT は失効が即時に効かず、影響は `exp` までの寿命で決まる**。即時性が必要ならイントロスペクション（キャッシュとのトレードオフあり）か CAEP 等のイベント通知を使う。— RFC 7009 §3 / RFC 7662 §4 / CAEP §3
23. **クライアントはアクセストークンの中身を読んではならない（MUST NOT）**。クレームはクライアントやエンドユーザーにも見える前提で、機微情報は暗号化するか載せない。— RFC 9068 §6
24. **理解できないクレームは無視される（MUST）**。新しく追加した「制限用クレーム」は、受信側が実装するまで効かない。— RFC 7519 §4 / RFC 8417 §4
25. **選択的開示（SD-JWT）でも、`iss`/`aud`/`exp`/`nbf`/`cnf` のような有効性に関わるクレームは隠せる形にしない（MUST NOT）**。— RFC 9901 §9.7
