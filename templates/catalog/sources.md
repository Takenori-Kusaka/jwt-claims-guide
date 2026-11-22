<!-- template_version: 0.1.0 -->
# カタログの出どころ（種になる一覧）

発行・利用イベントのカタログ（`issue_events.yaml`・`use_events.yaml`）、トークンの種類（`token_kinds.yaml`）、主体の状態の行列（`subject_state_matrix.md`）の行は、人の記憶ではなく、ここに挙げた外部の一覧（種になる一覧）から作りました（#2）。

**対象外 137 件／全 345 件（40%）**

- 種になる一覧の全 345 項目のうち、208 項目がカタログのどれかの行にひもづき、137 項目が「対象外」です。差集合（どの行にもひもづかず、対象外でもない項目）は 0 件です。
- カタログの全行（発行イベント 33 件、利用イベント 28 件、トークンの種類 17 件、行列の 7 状態）が、種の項目に 1 つ以上ひもづいています。
- 対象外の 137 件のうち 109 件は IANA の JWT Claims の登録簿の項目です。電話（STIR・SIP）、機器の証明（EAT）、CDN、5G（3GPP）、OpenID Federation など、組織の API のトークンに載らない分野のクレームです。登録簿を除いた対象外は 28 件／182 件です。
- 対象外の項目には、それぞれ「起きない前提」（`assumption`）と「崩れる条件」（`breaks_when`）があります（`seeds.yaml`）。137 件の理由の文は 40 通りです。同じ分野の項目（たとえば EAT のクレーム 22 件、STIR・SIP のクレーム 21 件）は、分野全体に当てはまる 1 つの理由を共有しています。分野ごとにまとめてよいのは、その理由が分野のすべての項目に当てはまるときだけです。
- 検査は、理由が 10 字以上であること、同じ文字の繰り返しでないこと、項目の名前そのものでないこと、assumption と breaks_when が違う文であることだけを確かめます。理由が妥当かは機械では判定できず、抜き取りの点検（#13）に頼ります。
- 件数は `python tools/catalog_check.py` が `seeds.yaml` から計算し、この節の太字の行と、下の表の「項目」「対象外」の列と照合します。各一覧の項目の数は、出どころの一覧の件数（`seeds.yaml` の `expected`。数え方と確かめた日つき）とも照合します。食い違うと CI が失敗します。

この閉包は「種になる一覧の内側」についてのものです。一覧の外にある発行・利用の場面（組織に固有の業務のイベント、製品の新しい契機など）は、カタログでは見つかりません。設計書では「この列挙の外に契機はないか」の問い（#17 の R9）で探し、見つかったら一覧かカタログに戻します。

## 種になる一覧

機械で読む形は `seeds.yaml` にあります。項目は `<一覧の id>/<項目の id>` の形で、カタログの行の `seeds` から参照します。IANA の JWT Claims だけは、行の `claims_produced`（発行イベント）か `claims_read`（利用イベント）にクレーム名を書けばひもづきます。

<!-- req:p03-recent-changes.R1（catalog の部分。lint:R10 は #17） -->
見直しの期限（`review_by`）は確かめた日の 90 日後です（筆者の提案。tracking #17。#17 の R10 が期限切れを warn にする）。持ち主はすべて #2 です。

| 一覧の id | 一覧 | 出どころ | 確かめた日 | 見直しの期限 | 持ち主 | 項目 | 対象外 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `rfc6749-grant` | RFC 6749 の grant type（§4.1〜§4.4・§6） | https://www.rfc-editor.org/rfc/rfc6749 | 2026-11-22 | 2027-02-20 | #2 | 5 | 0 |
| `iana-oauth-uri` | IANA「OAuth URI」（grant type・token type・client assertion type ほか。登録簿の更新 2026-11-10） | https://www.iana.org/assignments/oauth-parameters/oauth-parameters.xhtml#uri | 2026-11-22 | 2027-02-20 | #2 | 15 | 6 |
| `iana-response-type` | IANA「OAuth Authorization Endpoint Response Types」 | https://www.iana.org/assignments/oauth-parameters/oauth-parameters.xhtml#endpoint | 2026-11-22 | 2027-02-20 | #2 | 10 | 3 |
| `iana-access-token-type` | IANA「OAuth Access Token Types」 | https://www.iana.org/assignments/oauth-parameters/oauth-parameters.xhtml#token-types | 2026-11-22 | 2027-02-20 | #2 | 4 | 1 |
| `iana-token-type-hint` | IANA「OAuth Token Type Hints」 | https://www.iana.org/assignments/oauth-parameters/oauth-parameters.xhtml#token-type-hint | 2026-11-22 | 2027-02-20 | #2 | 3 | 1 |
| `oidf-grant` | OpenID Foundation の仕様の grant type（CIBA Core 1.0 §4） | https://openid.net/specs/openid-client-initiated-backchannel-authentication-core-1_0.html | 2026-11-22 | 2027-02-20 | #2 | 1 | 0 |
| `oidc-logout` | OpenID Connect のログアウト・セッションの 4 仕様（RP-Initiated・Front-Channel・Back-Channel・Session Management。いずれも Final） | https://openid.net/specs/openid-connect-rpinitiated-1_0.html ほか | 2026-11-22 | 2027-02-20 | #2 | 4 | 1 |
| `iana-jwt-claims` | IANA「JSON Web Token Claims」（登録簿の更新 2026-10-28） | https://www.iana.org/assignments/jwt/jwt.xhtml#claims | 2026-11-22 | 2027-02-20 | #2 | 163 | 109 |
| `auth0-protocol` | Auth0 の post-login の `event.transaction.protocol` の値（16 個） | https://auth0.com/docs/customize/actions/explore-triggers/signup-and-login-triggers/login-trigger/post-login-event-object | 2026-11-22 | 2027-02-20 | #2 | 16 | 6 |
| `auth0-trigger` | Auth0 の Actions のトリガー（Explore Triggers の 8 個） | https://auth0.com/docs/customize/actions/explore-triggers | 2026-11-22 | 2027-02-20 | #2 | 8 | 1 |
| `auth0-grant` | Auth0 の Application Grant Types（仕様の grant・Auth0 の拡張・legacy） | https://auth0.com/docs/get-started/applications/application-grant-types | 2026-11-22 | 2027-02-20 | #2 | 16 | 5 |
| `keycloak-settings` | Keycloak 26.8 のクライアント・レルムの設定のうち、発行・利用を起こす・止めるもの（Capability config ほか） | https://www.keycloak.org/docs/26.8.2/server_admin/index.html | 2026-11-22 | 2027-02-20 | #2 | 23 | 1 |
| `slide-stage-map` | ガイドの段階の地図の 6 段階（slide:p06-stage-map） | `docs/slides.json` | 2026-11-22 | 2027-02-20 | #2 | 6 | 0 |
| `slide103-kinds` | ガイドのトークンの種類（slide:p08-token-types-lifetimes の 6 種類） | `docs/slides.json` | 2026-11-22 | 2027-02-20 | #2 | 6 | 0 |
| `guide-token-kinds` | ガイドで扱うトークンの種類（#2 の本文の一覧：Logout Token・内部トークン・ID-JAG・DPoP の proof・クライアントの assertion・JAR・JARM） | https://github.com/Takenori-Kusaka/jwt-claims-guide/issues/2 | 2026-11-22 | 2027-02-20 | #2 | 7 | 0 |
| `subject-states` | 主体の状態（#2 の本文の 7 つ。行列の行） | https://github.com/Takenori-Kusaka/jwt-claims-guide/issues/2 | 2026-11-22 | 2027-02-20 | #2 | 7 | 0 |
| `prior-catalogue` | 調査ノートの先行の一覧（I01〜I30・U01〜U21） | `research/template-design/notes/coverage_lifecycle.md` | 2026-11-22 | 2027-02-20 | #2 | 51 | 3 |

### 一覧ごとの注意

- **`keycloak-settings`**：Keycloak には、Auth0 の `event.transaction.protocol` のような契機の値の一覧がありません。そこで、公式文書（Server Administration Guide 26.8.2 の Capability Config・Client scopes・Logout settings ほか、Securing Applications の Token exchange・JWT Authorization Grant・DPoP、Release Notes）から、発行・利用を起こす・止める設定を筆者が拾いました（`author-proposal`、tracking #2）。拾い漏れは、この一覧の外の漏れになります。
- **`auth0-protocol`**：文書は値を並べるだけで、各値の説明がありません。`oauth2-resource-owner`・`oauth2-webauthn`・`oauth2-access-token`・`oauth2-resource-owner-jwt-bearer` がどのフローかは確かめていません（`research/template-design/unverified.md` の V35）。
- **`iana-jwt-claims`**：登録簿の全 163 項目です。`...`（SD-JWT の配列の要素の digest）も 1 項目として数えています。
- **`prior-catalogue`**：#16 より前の調査で、キーワード検索から作った一覧です。ID（I01〜I30・U01〜U21）はカタログの ID と別物です（たとえば、一覧の I02 はカタログの I10）。

## 契機の一覧を持つ IdP と、持たない IdP

| IdP | 契機の一覧 | このカタログでの扱い |
| --- | --- | --- |
| Keycloak 26.8 | なし（契機の値の一覧はない）。代わりにクライアント・レルムの設定の一覧（`keycloak-settings`）を種にした | カタログの IdP。各行の `idp.keycloak` |
| Auth0 | あり：post-login の `event.transaction.protocol` の 16 個、Actions のトリガーの 8 個、Application Grant Types | カタログの IdP。各行の `idp.auth0` |
| Amazon Cognito | あり：pre token generation の `triggerSource` の 6 個（`research/template-design/notes/coverage_lifecycle.md` の Q1） | カタログの IdP にしない。#21 で扱う（#2 の範囲は 2 つの IdP） |
| Microsoft Entra ID | **一覧なし**。custom claims provider がいつ呼ばれるか（リフレッシュのときなど）の列挙を、文書で確かめていない（`unverified.md` の V08） | #21。設計書では #17 の R9（列挙の外の契機の問い）の回答を必須にする |
| Okta | **一覧なし**。token inline hook がリフレッシュや client credentials で動くかを、文書で確かめていない（`unverified.md` の V07） | #21。設計書では #17 の R9 の回答を必須にする |

## 確かめ方

```
python tools/catalog_check.py                  # 列・閉包・行列・この文書の件数
python tools/catalog_check.py --format json    # 機械向け（#17 の R3 が closure() を使う予定）
python -m pytest tools/tests/test_catalog_check.py
```

## 作成方法と点検状況

本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。IANA の登録簿は 2026-11-22 に CSV・XML を取得して項目を数えました。Keycloak と Auth0 の事実は、2026-11-22 に公式文書を読んで確かめました。文書に記載のない Keycloak の既定値は、26.8.2 のソースの要約で補い、そう書きました（`unverified.md` の V31）。

人による点検は未実施。作成とは別の LLM のセッションでの点検は、#2 の PR で行う予定です（記録：`research/reviews/` に追加する）。
