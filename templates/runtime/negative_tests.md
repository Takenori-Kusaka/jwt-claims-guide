<!-- template_version: 0.1.0 -->
# 拒否のテスト（攻撃側の回帰）

拒否されるべきトークン・要求を作り、**設計どおりに書いた受け手が拒否するか**を実行で確かめます（#8）。claim-lint（#6・#18）は設計書の宣言どうしの整合しか見られません。受け手が実際に照合しているかは、トークンを使わないと分かりません（`tools/claim_lint/RULES.md` の「L11〜L14 は宣言の整合の検査です」）。

- 受け手は `tools/runtime_tests/` にある参照の実装です。シナリオ A（`templates/examples/scenario-a`）の saas-api と BFF、シナリオ B（`templates/examples/scenario-b`）の ledger・invoices・入口・sts を、記入例の台帳（`token_types.yaml`・`claims.yaml`・`hops.yaml`）と設計書の本文に沿って書きました。設定（発行者・alg・typ・aud・必須クレーム・時計のずれ・寿命・上限のバイト数・語彙）は台帳から読みます。製品として配る部品ではありません。
- **確かめているのは「設計の受け手が拒否する」ことまでです。** 自組織の受け手が同じように拒否するかは、自組織の受け手に同じトークンを送って確かめます（10. の「自組織で使うとき」）。
- 見本のトークン（正規のトークン）は [golden_tokens.md](golden_tokens.md) にあります。各テストは見本を **1 か所だけ** 変えて作るので、拒否の理由はその 1 か所に限られます。
- 寿命と失効のテストの時間の縮め方は [lifetime_revocation.md](lifetime_revocation.md) にあります。
- 受け手が読むクレームの契約テストは [consumer_contract.md](consumer_contract.md) にあります。

本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。点検状況は [README.md](README.md) の「点検状況」を見てください。

## 1. 実行のしかた

```
python tools/runtime_tests/run.py --env offline                     # 手で作ったトークン＋参照の受け手（CI で動かす）
python tools/runtime_tests/run.py --env live --log research/runtime/run-live-YYYY-MM-DD.json   # Keycloak 26.8.0 と Postgres 16（手元）
python tools/runtime_tests/run.py --env offline --select negative_tests#alg-none                # 1 件だけ
```

- **offline**：試験用の鍵をその場で作り（RSA 2048・P-256。ディスクに書かない）、トークンを手で署名して参照の受け手に渡します。ネットワークもコンテナも使いません。CI（`.github/workflows/claims.yml`）で毎回動かします。
- **live**：WSL（Ubuntu-24.04）の Docker で Keycloak 26.8.0 と Postgres 16 を立て（compose のプロジェクト名 `jcg-issue8-runtime`、ポート 38080・35432）、実物のトークンと DB で確かめます。終わるとコンテナを消します。CI では動かしません。必要なもの・記録は [README.md](README.md) にあります。
- 結果は、テストごとに「確かめたこと・期待・観測・判定」の表になります。1 つでも期待と違えば、終了コードが 1 になります。最新の記録は `research/runtime/` にあります。

各テストの「要件」は、対応表（`templates/trace/requirements.yaml`）でそのテストを成果物に持つ要件です。実行の記録の要件の列も、同じ対応表から作ります。

## 2. 一覧

| テスト | 内容 | 題材 | 環境 | 要件の数 |
| --- | --- | --- | --- | --- |
| [`alg-none`](#alg-none) | alg=none | A | CI | 4 |
| [`alg-confusion`](#alg-confusion) | RS256 と HS256 の混同 | A | CI | 3 |
| [`jku-x5u`](#jku-x5u) | jku・x5u | A | CI | 1 |
| [`embedded-jwk`](#embedded-jwk) | ヘッダーの jwk・x5c | A | CI | 1 |
| [`untrusted-key`](#untrusted-key) | 設定外の鍵・別の発行者の鍵 | A | CI・実物 | 4 |
| [`iss-mismatch`](#iss-mismatch) | iss の不一致 | A | CI | 2 |
| [`aud-wrong`](#aud-wrong) | aud の誤り | A | CI | 14 |
| [`typ-wrong`](#typ-wrong) | typ の誤り | A | CI・実物 | 9 |
| [`expired`](#expired) | 期限切れ | A | CI | 2 |
| [`nbf-future`](#nbf-future) | nbf が未来・時刻のずれ | A | CI | 1 |
| [`missing-required`](#missing-required) | 必須クレームの欠落 | A | CI | 4 |
| [`missing-required-claim`](#missing-required-claim) | 必須の独自クレームの欠落 | A | CI・実物 | 6 |
| [`duplicate-claim`](#duplicate-claim) | 同名のクレームの重複 | A | CI | 1 |
| [`case-variant`](#case-variant) | 大文字小文字の違い | A | CI | 1 |
| [`tenant-mismatch`](#tenant-mismatch) | 別テナント・テナントの食い違い | A | CI・実物 | 8 |
| [`bola-other-owner`](#bola-other-owner) | BOLA：他人のオブジェクト | A | CI・実物 | 3 |
| [`revocation-latency`](#revocation-latency) | 剥奪から拒否までの時間 | A | CI・実物 | 3 |
| [`revoked-token-rejected`](#revoked-token-rejected) | IdP 側の失効と BFF のセッション（A03） | A | 実物 | 1 |
| [`rt-reuse`](#rt-reuse) | RT の再提示 | A | 実物 | 1 |
| [`exchange-narrowing`](#exchange-narrowing) | 交換で絞られているか | B・ケーススタディ | CI・実物 | 5 |
| [`disabled-subject-exchange`](#disabled-subject-exchange) | 無効にした利用者の交換 | ケーススタディ | 実物 | 1 |
| [`txn-token-as-at`](#txn-token-as-at) | Txn-Token を AT として送る | B | CI | 1 |
| [`txn-remint-immutable`](#txn-remint-immutable) | Txn-Token の作り直しで不変であるべきもの | B | CI | 1 |
| [`nested-act`](#nested-act) | 入れ子の act | B | CI | 5 |
| [`req-wl-changed`](#req-wl-changed) | req_wl だけを変えた | B | CI | 1 |
| [`tctx-mismatch`](#tctx-mismatch) | 本文と tctx の食い違い | B | CI | 1 |
| [`approval-mismatch`](#approval-mismatch) | 承認の内容と要求の食い違い | B | CI | 2 |
| [`passthrough-rejected`](#passthrough-rejected) | トークンのパススルー | B | CI | 1 |
| [`rar-unknown-type`](#rar-unknown-type) | 知らない authorization_details | B | CI | 1 |
| [`spoofed-identity-header`](#spoofed-identity-header) | ID 系ヘッダーの偽装 | B・A | CI | 5 |
| [`pool-context-leak`](#pool-context-leak) | 接続プールの文脈の残り（A12・A13） | A | 実物 | 4 |
| [`db-context-override`](#db-context-override) | DB の文脈の上書き・RLS のすり抜け（A04） | A | 実物 | 2 |

## 3. 検証の基本（ヘッダー・発行者・鍵・宛先・種類・時刻・必須クレーム）

<a id="alg-none"></a>

### alg-none　alg=none

<!-- req:p01-validation-order.R2 req:p01-dangerous-header-params.R1 req:p01-attack-patterns.R1 req:p12-antipatterns-1.R1 -->

- テスト ID：`test:negative_tests#alg-none`
- 要件：`p01-validation-order.R2`（#3・core）、`p01-dangerous-header-params.R1`（#3・core）、`p01-attack-patterns.R1`（#8・core）、`p12-antipatterns-1.R1`（#5・core）
- claim-lint：`lint:L17`
- スライド：`slide:p01-attack-patterns`、`slide:p01-dangerous-header-params`、`slide:p01-validation-order`、`slide:p12-antipatterns-1`
- 題材と環境：シナリオ A。オフライン（CI）
- 作るトークン・要求：ヘッダーの alg を none・None・NONE にした署名なしのトークンと、alg の無いトークン
- 期待する結果：`alg-not-allowed` で拒否する（alg の許可リストは RS256 だけ）

<a id="alg-confusion"></a>

### alg-confusion　RS256 と HS256 の混同

<!-- req:p01-dangerous-header-params.R2 req:p01-attack-patterns.R1 req:p12-antipatterns-1.R1 -->

- テスト ID：`test:negative_tests#alg-confusion`
- 要件：`p01-dangerous-header-params.R2`（#8・core）、`p01-attack-patterns.R1`（#8・core）、`p12-antipatterns-1.R1`（#5・core）
- claim-lint：`lint:L17`
- スライド：`slide:p01-attack-patterns`、`slide:p01-dangerous-header-params`、`slide:p12-antipatterns-1`
- 題材と環境：シナリオ A。オフライン（CI）
- 作るトークン・要求：t1 の公開鍵（PEM と JWK の JSON）を HMAC の鍵にした HS256 の署名と、許可リストに無い ES256 の署名
- 期待する結果：`alg-not-allowed` で拒否する。鍵の種類と alg を 1 つに固定しているので、鍵を HMAC の秘密として使う経路がない

<a id="jku-x5u"></a>

### jku-x5u　jku・x5u

<!-- req:p01-dangerous-header-params.R4 -->

- テスト ID：`test:negative_tests#jku-x5u`
- 要件：`p01-dangerous-header-params.R4`（#6・core）
- claim-lint：`lint:L25`
- スライド：`slide:p01-dangerous-header-params`
- 題材と環境：シナリオ A。オフライン（CI）
- 作るトークン・要求：ヘッダーの jku・x5u で攻撃者の鍵の場所を指し、攻撃者の鍵で署名したトークン。正しい t1 の署名に jku・x5u を足しただけのトークン
- 期待する結果：`header-key-param` で拒否し、検証の間に URL を 1 回も取得しない（取得の回数を数える）
- 注：key_source.header_key_params は reject（台帳のスキーマが固定する）なので、正しい署名に足しただけでも拒否する

<a id="embedded-jwk"></a>

### embedded-jwk　ヘッダーの jwk・x5c

<!-- req:p01-dangerous-header-params.R5 -->

- テスト ID：`test:negative_tests#embedded-jwk`
- 要件：`p01-dangerous-header-params.R5`（#6・core）
- claim-lint：`lint:L25`
- スライド：`slide:p01-dangerous-header-params`
- 題材と環境：シナリオ A。オフライン（CI）
- 作るトークン・要求：ヘッダーの jwk に自前の公開鍵を入れ、その鍵で署名したトークン。x5c に自前の証明書を入れたトークン
- 期待する結果：`header-key-param` で拒否する

<a id="untrusted-key"></a>

### untrusted-key　設定外の鍵・別の発行者の鍵

<!-- req:p00-incident-signature-valid.R1 req:p01-validation-order.R3 req:p01-key-rotation-jwks.R1 req:p12-antipatterns-1.R5 -->

- テスト ID：`test:negative_tests#untrusted-key`
- 要件：`p00-incident-signature-valid.R1`（#3・core）、`p01-validation-order.R3`（#8・core）、`p01-key-rotation-jwks.R1`（#3・full）、`p12-antipatterns-1.R5`（#5・core）
- claim-lint：`lint:L25`・`lint:R1`
- スライド：`slide:p00-incident-signature-valid`、`slide:p01-key-rotation-jwks`、`slide:p01-validation-order`、`slide:p12-antipatterns-1`
- 題材と環境：シナリオ A。オフライン（CI）・実物（Keycloak 26.8.0・Postgres 16、手元）
- 作るトークン・要求：オフライン：t1 の kid を名乗って攻撃者の鍵で署名したトークン。iss=t1 を t2 の鍵（t2 の kid）で正しく署名したトークン（Storm-0558 の型、ケーススタディ A9）。未知の kid を 10 秒おきに 3 つ。実物：t1 の AT の kid が t2 の JWKS に無いこと
- 期待する結果：`bad-signature`・`unknown-kid` で拒否する。未知の kid での JWKS の取り直しは 300 秒に 1 回まで（token_types の unknown_kid）。実物では t1 と t2 の JWKS に共通の kid が 0 件
- 注：鍵は iss ごとに引く。iss を先に許可リストと照合してから、その iss の鍵だけで検証する

<a id="iss-mismatch"></a>

### iss-mismatch　iss の不一致

<!-- req:p01-validation-order.R4 req:p02-registered-claims.R1 -->

- テスト ID：`test:negative_tests#iss-mismatch`
- 要件：`p01-validation-order.R4`（#8・core）、`p02-registered-claims.R1`（#8・core）
- claim-lint：`lint:R1`
- スライド：`slide:p01-validation-order`、`slide:p02-registered-claims`
- 題材と環境：シナリオ A。オフライン（CI）
- 作るトークン・要求：t1 の鍵で正しく署名し、iss だけを変えたトークン：末尾のスラッシュ、http、ホストの大文字、レルム名の大文字、接頭辞の一致（t1x）、`..`、末尾の空白、別のドメインの部分一致、レルムのない URL、配列
- 期待する結果：`iss-not-allowed` で拒否する（許可リストと完全一致だけを受ける）

<a id="aud-wrong"></a>

### aud-wrong　aud の誤り

<!-- req:p01-validation-order.R5 req:p01-id-token-vs-access-token.R2 req:p01-library-defaults.R1 req:p01-attack-patterns.R2 req:p02-registered-claims.R3 req:p03-entra-oid-tid.R5 req:p03-keycloak-aud-lightweight.R1 req:p04-reject-missing-required.R4 req:p05-cross-tenant.R6 req:p05-confused-deputy.R4 req:p06-transaction-tokens.R6 req:p06-validation-split.R2 req:p10-mcp-authorization.R2 req:p12-antipatterns-1.R3 -->

- テスト ID：`test:negative_tests#aud-wrong`
- 要件：`p01-validation-order.R5`（#8・core）、`p01-id-token-vs-access-token.R2`（#8・core）、`p01-library-defaults.R1`（#4・core）、`p01-attack-patterns.R2`（#8・core）、`p02-registered-claims.R3`（#4・core）、`p03-entra-oid-tid.R5`（#8・core）、`p03-keycloak-aud-lightweight.R1`（#4・core）、`p04-reject-missing-required.R4`（#8・core）、`p05-cross-tenant.R6`（#8・core）、`p05-confused-deputy.R4`（#6・full）、`p06-transaction-tokens.R6`（#8・core）、`p06-validation-split.R2`（#8・core）、`p10-mcp-authorization.R2`（#4・core）、`p12-antipatterns-1.R3`（#5・core）
- claim-lint：`lint:L27`・`lint:L41`（未実装）
- スライド：`slide:p01-attack-patterns`、`slide:p01-id-token-vs-access-token`、`slide:p01-library-defaults`、`slide:p01-validation-order`、`slide:p02-registered-claims`、`slide:p03-entra-oid-tid`、`slide:p03-keycloak-aud-lightweight`、`slide:p04-reject-missing-required`、`slide:p05-confused-deputy`、`slide:p05-cross-tenant`、`slide:p06-transaction-tokens`、`slide:p06-validation-split`、`slide:p10-mcp-authorization`、`slide:p12-antipatterns-1`
- 題材と環境：シナリオ A・B。オフライン（CI）
- 作るトークン・要求：aud を saas-web（ID トークンの宛先）・account・Microsoft Graph・別の API・大文字の SAAS-API にしたトークンと、aud の型の誤り（数値・空の配列・数値を含む配列・null）。シナリオ B の ledger に、aud を信頼ドメインの外（https://partner.example.com）にした Txn-Token
- 期待する結果：`aud-mismatch`・`claim-type`・`missing-claim` で拒否する。aud が文字列 `"saas-api"` でも配列 `["saas-api","account"]` でも受ける。Txn-Token の aud は信頼ドメイン `https://corp.example.com` だけを受ける

<a id="typ-wrong"></a>

### typ-wrong　typ の誤り

<!-- req:p01-validation-order.R7 req:p01-dangerous-header-params.R6 req:p01-client-made-jwts.R3 req:p01-id-token-vs-access-token.R1 req:p01-attack-patterns.R4 req:p03-cognito-token-use.R1 req:p06-return-results.R2 req:p06-flow-browser-to-db.R2 req:p08-logout.R1 -->

- テスト ID：`test:negative_tests#typ-wrong`
- 要件：`p01-validation-order.R7`（#8・core）、`p01-dangerous-header-params.R6`（#8・core）、`p01-client-made-jwts.R3`（#3・full）、`p01-id-token-vs-access-token.R1`（#5・core）、`p01-attack-patterns.R4`（#3・core）、`p03-cognito-token-use.R1`（#3・core）、`p06-return-results.R2`（#6・core）、`p06-flow-browser-to-db.R2`（#5・core）、`p08-logout.R1`（#8・full）
- claim-lint：`lint:L17`
- スライド：`slide:p01-attack-patterns`、`slide:p01-client-made-jwts`、`slide:p01-dangerous-header-params`、`slide:p01-id-token-vs-access-token`、`slide:p01-validation-order`、`slide:p03-cognito-token-use`、`slide:p06-flow-browser-to-db`、`slide:p06-return-results`、`slide:p08-logout`
- 題材と環境：シナリオ A。オフライン（CI）・実物（Keycloak 26.8.0・Postgres 16、手元）
- 作るトークン・要求：オフライン：ヘッダーの typ を JWT・jwt・logout+jwt・txntoken+jwt・dpop+jwt・at+JWT+extra・無しにしたトークン、ID トークンの形のトークン。実物：Keycloak がレルム t1 で発行した ID トークン
- 期待する結果：`typ-mismatch` で拒否する。`application/at+jwt`（RFC 9068 §2.1 の別の書き方）は受ける
- 注：型の名前は大文字小文字を区別しない（RFC 7515 §4.1.9）ので、比べる前に小文字にする

<a id="expired"></a>

### expired　期限切れ

<!-- req:p01-validation-order.R6 req:p12-antipatterns-1.R8 -->

- テスト ID：`test:negative_tests#expired`
- 要件：`p01-validation-order.R6`（#8・core）、`p12-antipatterns-1.R8`（#5・core）
- claim-lint：`lint:L27`
- スライド：`slide:p01-validation-order`、`slide:p12-antipatterns-1`
- 題材と環境：シナリオ A。オフライン（CI）
- 作るトークン・要求：発行から 330 秒・331 秒・400 秒の時点で使う見本の AT。exp − iat を 301 秒にしたトークン（テナントの管理者がレルムで寿命を延ばした形）。exp が文字列・真偽値
- 期待する結果：発行から 330 秒（exp＋ずれ 30 秒）までは受け、331 秒から `expired`。`lifetime-too-long`・`claim-type` で拒否する
- 注：シナリオ A の「受け入れの上限 330 秒」の境界を確かめる

<a id="nbf-future"></a>

### nbf-future　nbf が未来・時刻のずれ

<!-- req:p01-validation-order.R6 -->

- テスト ID：`test:negative_tests#nbf-future`
- 要件：`p01-validation-order.R6`（#8・core）
- claim-lint：`lint:L27`
- スライド：`slide:p01-validation-order`
- 題材と環境：シナリオ A。オフライン（CI）
- 作るトークン・要求：nbf が 30 秒先・31 秒先、iat が 30 秒先・31 秒先のトークン
- 期待する結果：31 秒先は `not-yet-valid`・`iat-in-future` で拒否し、30 秒先（max_clock_skew の内側）は受ける

<a id="missing-required"></a>

### missing-required　必須クレームの欠落

<!-- req:p01-validation-order.R8 req:p01-library-defaults.R2 req:p03-cognito-token-use.R3 req:p03-confusing-differences.R4 -->

- テスト ID：`test:negative_tests#missing-required`
- 要件：`p01-validation-order.R8`（#8・core）、`p01-library-defaults.R2`（#8・core）、`p03-cognito-token-use.R3`（#3・core）、`p03-confusing-differences.R4`（#8・core）
- claim-lint：`lint:L7`・`lint:L27`
- スライド：`slide:p01-library-defaults`、`slide:p01-validation-order`、`slide:p03-cognito-token-use`、`slide:p03-confusing-differences`
- 題材と環境：シナリオ A。オフライン（CI）
- 作るトークン・要求：AT の required_claims（iss・sub・aud・exp・iat・jti・azp）を 1 つずつ欠いたトークンと、exp が null のトークン
- 期待する結果：`missing-claim`（iss だけは先に照合するので `iss-not-allowed`）で拒否する。aud は配列でも受ける

<a id="missing-required-claim"></a>

### missing-required-claim　必須の独自クレームの欠落

<!-- req:p03-custom-claim-injection.R1 req:p03-absorb-idp-differences.R5 req:p04-absent-null-false-empty.R3 req:p04-forward-compatibility.R2 req:p04-reject-missing-required.R4 req:p06-grant-types.R4 -->

- テスト ID：`test:negative_tests#missing-required-claim`
- 要件：`p03-custom-claim-injection.R1`（#6・core）、`p03-absorb-idp-differences.R5`（#6・core）、`p04-absent-null-false-empty.R3`（#6・full）、`p04-forward-compatibility.R2`（#6・core）、`p04-reject-missing-required.R4`（#8・core）、`p06-grant-types.R4`（#2・full）
- claim-lint：`lint:L7`・`lint:L37`
- スライド：`slide:p03-absorb-idp-differences`、`slide:p03-custom-claim-injection`、`slide:p04-absent-null-false-empty`、`slide:p04-forward-compatibility`、`slide:p04-reject-missing-required`、`slide:p06-grant-types`
- 題材と環境：シナリオ A。オフライン（CI）・実物（Keycloak 26.8.0・Postgres 16、手元）
- 作るトークン・要求：オフライン：名前空間の tenant_id・user_id・v を欠く・null にしたトークン、名前空間ごと欠くトークン（同時に X-Tenant: t2 を付ける）、roles を欠くトークン。実物：軽量アクセストークン（クライアント saas-light）
- 期待する結果：`missing-claim` で拒否する（fail closed）。ヘッダーで補わない。roles の欠落は on_missing が「既定値」なので「ロールなし」で受ける
- 注：実物の軽量アクセストークンには名前空間・aud・sub が無い（ケーススタディ A11 と同じ）

<a id="duplicate-claim"></a>

### duplicate-claim　同名のクレームの重複

<!-- req:p01-attack-patterns.R6 -->

- テスト ID：`test:negative_tests#duplicate-claim`
- 要件：`p01-attack-patterns.R6`（#8・core）
- claim-lint：—（宣言で表せないので、静的な規則はない）
- スライド：`slide:p01-attack-patterns`
- 題材と環境：シナリオ A。オフライン（CI）
- 作るトークン・要求：ペイロードの sub を 2 回、名前空間の中の tenant_id を 2 回、名前空間のオブジェクトを 2 回書いたトークンと、ヘッダーの alg を 2 回書いたトークン（いずれも正しく署名）
- 期待する結果：`duplicate-member` で拒否する（後勝ちのパーサーなら別人・別テナントになる）
- 注：RFC 7519 §4 は、重複を拒否するか、後勝ちで読むかのどちらかを求める。この設計の受け手は拒否する（部品ごとに読み方が違うと、同じトークンを別の値として読むため）。重複は宣言では表せないので、静的な規則はない。検証の部品の設定は `template:modules/M_token_validation#library-config` の「同名のメンバー」

<a id="case-variant"></a>

### case-variant　大文字小文字の違い

<!-- req:p04-case-and-characters.R3 -->

- テスト ID：`test:negative_tests#case-variant`
- 要件：`p04-case-and-characters.R3`（#8・full）
- claim-lint：—（宣言で表せないので、静的な規則はない）
- スライド：`slide:p04-case-and-characters`
- 題材と環境：シナリオ A。オフライン（CI）
- 作るトークン・要求：tenant_id を T1、パスのテナントを T1、user_id を sub の大文字、roles を Approver・TENANT-ADMIN、aud を Saas-Api にしたトークン
- 期待する結果：値を変換せずに完全一致で比べる：`tenant-iss-mismatch`・`tenant-path-mismatch`・`user-id-mismatch`・`aud-mismatch` で拒否し、語彙と違うロールは数えない
- 注：iss の大文字小文字は iss-mismatch で確かめる

## 4. テナントとオブジェクト（シナリオ A）

<a id="tenant-mismatch"></a>

### tenant-mismatch　別テナント・テナントの食い違い

<!-- req:p00-incident-signature-valid.R2 req:p01-attack-patterns.R3 req:p02-tenant-org.R3 req:p05-multitenancy.R3 req:p05-multitenancy.R6 req:p06-flow-multitenant-saas.R2 req:p08-reissue-triggers.R1 req:p12-antipatterns-1.R4 -->

- テスト ID：`test:negative_tests#tenant-mismatch`
- 要件：`p00-incident-signature-valid.R2`（#6・core）、`p01-attack-patterns.R3`（#8・core）、`p02-tenant-org.R3`（#8・core）、`p05-multitenancy.R3`（#6・core）、`p05-multitenancy.R6`（#8・core）、`p06-flow-multitenant-saas.R2`（#8・core）、`p08-reissue-triggers.R1`（#4・full）、`p12-antipatterns-1.R4`（#5・core）
- claim-lint：`lint:L9`
- スライド：`slide:p00-incident-signature-valid`、`slide:p01-attack-patterns`、`slide:p02-tenant-org`、`slide:p05-multitenancy`、`slide:p06-flow-multitenant-saas`、`slide:p08-reissue-triggers`、`slide:p12-antipatterns-1`
- 題材と環境：シナリオ A。オフライン（CI）・実物（Keycloak 26.8.0・Postgres 16、手元）
- 作るトークン・要求：t2 のトークンでパス /t1（X-Tenant: t1 を付けるものも）、t2 の管理者が自分のレルムのマッパーで tenant_id=t1 を出させたトークン（ケーススタディ A8）、tenant_id が配列（A12）・空文字・33 バイトのトークン。実物でも同じ 3 つ（t2 のクライアント rogue-web、t1 のクライアント saas-multi）
- 期待する結果：`tenant-path-mismatch`・`tenant-iss-mismatch`・`claim-type`・`claim-value` で拒否する。テナントは iss（レルム）から決め、tenant_id とパスはそれとの一致を照合するだけ

<a id="bola-other-owner"></a>

### bola-other-owner　BOLA：他人のオブジェクト

<!-- req:p05-bola.R5 req:p06-validation-split.R5 req:p12-review-viewpoints.R13 -->

- テスト ID：`test:negative_tests#bola-other-owner`
- 要件：`p05-bola.R5`（#8・core）、`p06-validation-split.R5`（#4・core）、`p12-review-viewpoints.R13`（#5・core）
- claim-lint：—（宣言で表せないので、静的な規則はない）
- スライド：`slide:p05-bola`、`slide:p06-validation-split`、`slide:p12-review-viewpoints`
- 題材と環境：シナリオ A。オフライン（CI）・実物（Keycloak 26.8.0・Postgres 16、手元）
- 作るトークン・要求：alice のトークンで、自分の請求書・同じテナントの carol の請求書・t2 の請求書を読む。user_id だけを carol にしたトークン。実物では Postgres の owner_sub で照合する
- 期待する結果：自分の請求書だけを返し、ほかは `not-found`（他テナントと他人で同じ答え）。user_id が sub と違えば `user-id-mismatch`
- 注：BOLA の鍵は sub だけ（design.md 2.）

## 5. 寿命と失効

<a id="revocation-latency"></a>

### revocation-latency　剥奪から拒否までの時間

<!-- req:p04-token-is-snapshot.R3 req:p08-stale-claims.R3 req:p08-revocation-propagation.R2 -->

- テスト ID：`test:negative_tests#revocation-latency`
- 要件：`p04-token-is-snapshot.R3`（#8・core）、`p08-stale-claims.R3`（#8・core）、`p08-revocation-propagation.R2`（#8・core）
- claim-lint：`lint:L5`
- スライド：`slide:p04-token-is-snapshot`、`slide:p08-revocation-propagation`、`slide:p08-stale-claims`
- 題材と環境：シナリオ A。オフライン（CI）・実物（Keycloak 26.8.0・Postgres 16、手元）
- 作るトークン・要求：オフライン：テナントを停止した直後の要求と、ロールを外した後の手元の AT（発行から 330 秒・331 秒）。実物：寿命を縮めたレルム t1 で alice の approver を外し、BFF 経由で要求を続ける。Postgres の tenants.status を suspended にした直後の要求
- 期待する結果：テナントの停止は次の要求で `tenant-suspended`（0 秒。AT の exp を待たない）。ロールの剥奪は受け入れの上限（本番の値 330 秒、縮めた値 22 秒）以内に、API が見るロールから消える
- 注：時間の縮め方は [lifetime_revocation.md](lifetime_revocation.md#scaling)

<a id="revoked-token-rejected"></a>

### revoked-token-rejected　IdP 側の失効と BFF のセッション（A03）

<!-- req:p08-revocation-propagation.R2 -->

- テスト ID：`test:negative_tests#revoked-token-rejected`
- 要件：`p08-revocation-propagation.R2`（#8・core）
- claim-lint：`lint:L5`・`lint:L23`
- スライド：`slide:p08-revocation-propagation`
- 題材と環境：シナリオ A。実物（Keycloak 26.8.0・Postgres 16、手元）
- 作るトークン・要求：寿命を縮めたレルム t1 で BFF（参照の saas-web）がログインし、要求を続ける。3 秒後に管理者が alice のセッションを消す（別の回では alice を無効にする）。盗まれた AT（BFF の外の写し）も使う
- 期待する結果：BFF の次のリフレッシュが失敗し、BFF のセッションが受け入れの上限（縮めた値 22 秒、本番の値 330 秒）以内に終わる。盗まれた AT は exp の前は通り（exp_only の残り）、発行から 23 秒後は `expired`
- 注：[lifetime_revocation.md](lifetime_revocation.md#bff-session)

<a id="rt-reuse"></a>

### rt-reuse　RT の再提示

<!-- req:p08-rotation.R3 -->

- テスト ID：`test:negative_tests#rt-reuse`
- 要件：`p08-rotation.R3`（#8・core）
- claim-lint：`lint:L15`
- スライド：`slide:p08-rotation`
- 題材と環境：シナリオ A。実物（Keycloak 26.8.0・Postgres 16、手元）
- 作るトークン・要求：リフレッシュで RT1 を RT2 に替えた後、使い終えた RT1 を再提示し、続けて RT2 でリフレッシュする
- 期待する結果：RT1 は `invalid_grant` で拒否される。RT2 も失効する（Keycloak 26.8.0、Revoke Refresh Token ON、refreshTokenMaxReuse 0）
- 注：シナリオ A の token_types.yaml は RT の reuse_detection を unverified としている。観測の結果は [lifetime_revocation.md](lifetime_revocation.md#rt-reuse)

## 6. 交換で絞られているか

<a id="exchange-narrowing"></a>

### exchange-narrowing　交換で絞られているか

<!-- req:p03-keycloak-aud-lightweight.R4 req:p06-narrow-downstream.R3 req:p10-token-exchange-not-narrowing.R1 req:p10-token-exchange-not-narrowing.R4 req:p10-delegation-chain-depth.R2 -->

- テスト ID：`test:negative_tests#exchange-narrowing`
- 要件：`p03-keycloak-aud-lightweight.R4`（#6・core）、`p06-narrow-downstream.R3`（#8・core）、`p10-token-exchange-not-narrowing.R1`（#8・core）、`p10-token-exchange-not-narrowing.R4`（#6・core）、`p10-delegation-chain-depth.R2`（#6・core）
- claim-lint：`lint:L16`
- スライド：`slide:p03-keycloak-aud-lightweight`、`slide:p06-narrow-downstream`、`slide:p10-delegation-chain-depth`、`slide:p10-token-exchange-not-narrowing`
- 題材と環境：シナリオ B・ケーススタディ。オフライン（CI）・実物（Keycloak 26.8.0・Postgres 16、手元）
- 作るトークン・要求：オフライン：シナリオ B の H14（AGENT_AT）→ H15（TASK_AT）の交換を作り、scope・aud・exp・承認の金額・独自クレームを 1 つずつ広げる。ケーススタディの実測の値（`tools/runtime_tests/fixtures/kc_exchange_casestudy.json`）。実物：ケーススタディと同じレルム corp で、mcp-tools が carol の AT（aud mcp-tools）を 5 通りに交換する
- 期待する結果：正規の交換は指摘 0。広げたものはすべて指摘する。実物では scope=aud-orders の交換で元のトークンに無い orders 宛てが出ることを再現し、検査が指摘する。invoices だけへの交換は aud・scope・独自クレームの指摘 0。交換の時刻から 300 秒の新しい exp が出るので、元のトークンの後に交換すると寿命の延長を指摘する
- 注：検査の規則は `tools/runtime_tests/narrowing.py`（L16 の実行版）。Keycloak の「宛先だけを運ぶスコープ」（aud-orders など）は aud として比べる

<a id="disabled-subject-exchange"></a>

### disabled-subject-exchange　無効にした利用者の交換

<!-- req:p03-keycloak-aud-lightweight.R5 -->

- テスト ID：`test:negative_tests#disabled-subject-exchange`
- 要件：`p03-keycloak-aud-lightweight.R5`（#2・core）
- claim-lint：—（宣言で表せないので、静的な規則はない）
- スライド：`slide:p03-keycloak-aud-lightweight`
- 題材と環境：シナリオ ケーススタディ。実物（Keycloak 26.8.0・Postgres 16、手元）
- 作るトークン・要求：レルム corp で dave の AT を取り、dave を無効にしてから、同じ AT を subject_token にして交換する
- 期待する結果：無効にした後の交換は 400 番台で、新しいトークンが出ない（CVE-2025-14559 の型が Keycloak 26.8.0 で再現しないことの確認）

## 7. 伝搬と委任（シナリオ B）

<a id="txn-token-as-at"></a>

### txn-token-as-at　Txn-Token を AT として送る

<!-- req:p06-transaction-tokens.R2 -->

- テスト ID：`test:negative_tests#txn-token-as-at`
- 要件：`p06-transaction-tokens.R2`（#6・core）
- claim-lint：`lint:L43`
- スライド：`slide:p06-transaction-tokens`
- 題材と環境：シナリオ B。オフライン（CI）
- 作るトークン・要求：ledger に Authorization: Bearer で送った Txn-Token。orders（INT_AT の受け手）に AT として送った Txn-Token
- 期待する結果：ledger は `txn-token-in-authorization`、orders は `typ-mismatch` で拒否する

<a id="txn-remint-immutable"></a>

### txn-remint-immutable　Txn-Token の作り直しで不変であるべきもの

<!-- req:p06-transaction-tokens.R5 -->

- テスト ID：`test:negative_tests#txn-remint-immutable`
- 要件：`p06-transaction-tokens.R5`（#6・full）
- claim-lint：`lint:L16`・`lint:L44`（未実装）
- スライド：`slide:p06-transaction-tokens`
- 題材と環境：シナリオ B。オフライン（CI）
- 作るトークン・要求：TTS が正しく署名し直したうえで、txn・sub・aud を変えた、または scope に ledger.post を足した Txn-Token。作り直しで exp を延ばしたもの（検査の関数）
- 期待する結果：`txn-changed`・`unknown-txn`・`aud-mismatch` で拒否する（監査のログの H9 の値と比べる）。exp の延長も指摘する

<a id="nested-act"></a>

### nested-act　入れ子の act

<!-- req:p02-delegation-client.R1 req:p05-confused-deputy.R2 req:p06-audit-trail.R2 req:p10-four-questions.R6 req:p10-delegation-chain-depth.R4 -->

- テスト ID：`test:negative_tests#nested-act`
- 要件：`p02-delegation-client.R1`（#18・core）、`p05-confused-deputy.R2`（#18・core）、`p06-audit-trail.R2`（#18・core）、`p10-four-questions.R6`（#18・core）、`p10-delegation-chain-depth.R4`（#18・core）
- claim-lint：`lint:L12`
- スライド：`slide:p02-delegation-client`、`slide:p05-confused-deputy`、`slide:p06-audit-trail`、`slide:p10-delegation-chain-depth`、`slide:p10-four-questions`
- 題材と環境：シナリオ B。オフライン（CI）
- 作るトークン・要求：入れ子の act.act.sub だけを admin-console に変えたトークン（署名は正しい）、最も外側を admin-console にして invoice-mcp を内側に入れたトークン、深さ 4 の連鎖、mTLS の相手と違う act.sub、act の無いトークン
- 期待する結果：`delegation-chain-mismatch`・`actor-mismatch`・`delegation-too-deep`・`missing-claim` で拒否する。今の代理者は最も外側の act.sub だけ（RFC 8693 §4.1）
- 注：L12 は「入れ子の act を q-actor の答えにしていないか」を宣言で見る。このテストは受け手が実際に外側だけを読むかを見る

<a id="req-wl-changed"></a>

### req-wl-changed　req_wl だけを変えた

<!-- req:p06-validation-split.R3 -->

- テスト ID：`test:negative_tests#req-wl-changed`
- 要件：`p06-validation-split.R3`（#8・core）
- claim-lint：`lint:L12`
- スライド：`slide:p06-validation-split`
- 題材と環境：シナリオ B。オフライン（CI）
- 作るトークン・要求：req_wl だけを書き換えたトークン（署名はそのまま）、TTS が req_wl=orders で発行したトークン、mTLS の相手が orders でない要求
- 期待する結果：`bad-signature`・`req-wl-not-allowed`・`peer-mismatch` で拒否する。req_wl（どのワークロードが求めたか）と直接の通信相手（mTLS）は別々に確かめる

<a id="tctx-mismatch"></a>

### tctx-mismatch　本文と tctx の食い違い

<!-- req:p06-transaction-tokens.R9 -->

- テスト ID：`test:negative_tests#tctx-mismatch`
- 要件：`p06-transaction-tokens.R9`（#18・core）
- claim-lint：`lint:L11`
- スライド：`slide:p06-transaction-tokens`
- 題材と環境：シナリオ B。オフライン（CI）
- 作るトークン・要求：本文の operation が ledger.post で tctx が ledger.read の要求、tctx.operation が ledger.post の Txn-Token、tctx に語彙に無い項目（amount）を入れた Txn-Token
- 期待する結果：`tctx-body-mismatch`・`tctx-scope-mismatch`・`tctx-shape` で拒否する
- 注：シナリオ B の tctx の項目は operation だけ（claims.yaml の C-tctx）。#8 の本文の「本文の数量」は、この記入例では承認の金額（approval-mismatch）で確かめた

<a id="approval-mismatch"></a>

### approval-mismatch　承認の内容と要求の食い違い

<!-- req:p10-human-approval-evidence.R3 req:p10-agent-checklist.R7 -->

- テスト ID：`test:negative_tests#approval-mismatch`
- 要件：`p10-human-approval-evidence.R3`（#8・core）、`p10-agent-checklist.R7`（#5・full）
- claim-lint：`lint:L11`
- スライド：`slide:p10-agent-checklist`、`slide:p10-human-approval-evidence`
- 題材と環境：シナリオ B。オフライン（CI）
- 作るトークン・要求：承認と違う金額（C5）・相手先の口座（C6）の支払い、空の authorization_details、承認を取り消した後の支払い（C7）
- 期待する結果：`approval-mismatch`・`approval-missing`・`approval-not-active` で拒否する。取り消しはトークンの exp を待たない

<a id="passthrough-rejected"></a>

### passthrough-rejected　トークンのパススルー

<!-- req:p10-mcp-authorization.R3 -->

- テスト ID：`test:negative_tests#passthrough-rejected`
- 要件：`p10-mcp-authorization.R3`（#6・full）
- claim-lint：`lint:L41`（未実装）
- スライド：`slide:p10-mcp-authorization`
- 題材と環境：シナリオ B。オフライン（CI）
- 作るトークン・要求：invoice-mcp が受けた AGENT_AT（aud invoice-mcp）をそのまま invoices に送る（C2）。宛先を invoice-mcp と invoices の 2 つにした広いトークン（C13）
- 期待する結果：1 つ目は `aud-mismatch`、2 つ目は今の代理者の照合（`actor-mismatch`・`delegation-chain-mismatch`）で拒否する
- 注：2 つ目は aud の検査では落ちない。宛先を 1 つにする規則は発行者（sts）と L16 で守る

<a id="rar-unknown-type"></a>

### rar-unknown-type　知らない authorization_details

<!-- req:p05-coarse-fine-layers.R3 -->

- テスト ID：`test:negative_tests#rar-unknown-type`
- 要件：`p05-coarse-fine-layers.R3`（#8・full）
- claim-lint：—（宣言で表せないので、静的な規則はない）
- スライド：`slide:p05-coarse-fine-layers`
- 題材と環境：シナリオ B。オフライン（CI）
- 作るトークン・要求：sts への要求の authorization_details で、知らない type（refund）、知らないフィールド（maxAmount）、知らない actions（refund）
- 期待する結果：参照の sts が `invalid_authorization_details` で拒否する（RFC 9396 §5）

<a id="spoofed-identity-header"></a>

### spoofed-identity-header　ID 系ヘッダーの偽装

<!-- req:p06-header-forwarding.R1 req:p06-header-forwarding.R2 req:p06-header-forwarding.R3 req:p11-pre-add-questions-2.R5 req:p12-antipatterns-2.R5 -->

- テスト ID：`test:negative_tests#spoofed-identity-header`
- 要件：`p06-header-forwarding.R1`（#6・core）、`p06-header-forwarding.R2`（#8・core）、`p06-header-forwarding.R3`（#8・core）、`p11-pre-add-questions-2.R5`（#4・core）、`p12-antipatterns-2.R5`（#5・core）
- claim-lint：`lint:L8`・`lint:L67`・`lint:L72`
- スライド：`slide:p06-header-forwarding`、`slide:p11-pre-add-questions-2`、`slide:p12-antipatterns-2`
- 題材と環境：シナリオ B・A。オフライン（CI）
- 作るトークン・要求：入口に届いた X-User-Id・x-user-id・X_USER_ID・x-User_Roles・先頭に空白のある X-User-Department。x-user-id の大文字小文字違いの重複、Authorization の重複、X_User_Id と X-User-Id の重複。シナリオ A の API に X-Tenant・x_tenant を付けた要求
- 期待する結果：入口（参照の gateway）は x-user-* をどの綴りでも除去し、重複は `duplicate-header` で拒否する。素朴な除去（X-User-Id の完全一致だけ）は変種を 4 件以上通す＝このテストが見つける誤り。シナリオ A の API はヘッダーを読まない

## 8. データ層（シナリオ A の H3）

<a id="pool-context-leak"></a>

### pool-context-leak　接続プールの文脈の残り（A12・A13）

<!-- req:p07-connection-pool.R2 req:p07-connection-pool.R3 req:p07-data-layer-checklist.R2 req:p07-data-layer-checklist.R11 -->

- テスト ID：`test:negative_tests#pool-context-leak`
- 要件：`p07-connection-pool.R2`（#8・full）、`p07-connection-pool.R3`（#4・core）、`p07-data-layer-checklist.R2`（#8・full）、`p07-data-layer-checklist.R11`（#8・full）
- claim-lint：—（宣言で表せないので、静的な規則はない）
- スライド：`slide:p07-connection-pool`、`slide:p07-data-layer-checklist`
- 題材と環境：シナリオ A。実物（Keycloak 26.8.0・Postgres 16、手元）
- 作るトークン・要求：アプリのロール app_rls の 1 本の接続を使い回す。`SET LOCAL app.tenant = $1` をパラメータで実行する。set_config(…, true) で t2 を設定した次のトランザクションで、文脈もテナントの条件も書き忘れた集計を流す。文脈を空文字にする。誤りの例として set_config(…, false)（セッション単位）で t2 を設定する。参照の saas-api で bob（t2）の後に alice（t1）
- 期待する結果：SET LOCAL はパラメータにできず Postgres がエラーを返す（だから set_config を使う）。次のトランザクションでは文脈が空で 0 行、空文字でも 0 行。セッション単位の設定は次の要求に漏れる（このテストが検出する）。参照の saas-api は t1 の行だけを返す
- 注：PgBouncer の transaction pooling は試していない。そのため `p07-connection-pool.R2`（PgBouncer を含む）は未着手のままにした

<a id="db-context-override"></a>

### db-context-override　DB の文脈の上書き・RLS のすり抜け（A04）

<!-- req:p07-trust-boundary.R3 req:p07-data-layer-checklist.R11 -->

- テスト ID：`test:negative_tests#db-context-override`
- 要件：`p07-trust-boundary.R3`（#4・core）、`p07-data-layer-checklist.R11`（#8・full）
- claim-lint：—（宣言で表せないので、静的な規則はない）
- スライド：`slide:p07-data-layer-checklist`、`slide:p07-trust-boundary`
- 題材と環境：シナリオ A。実物（Keycloak 26.8.0・Postgres 16、手元）
- 作るトークン・要求：app_rls で、RLS をすり抜ける主体を照会する（superuser・BYPASSRLS、テーブルの所有者、FORCE の無いテーブル、SECURITY DEFINER の関数、security_invoker の無いビュー）。SET ROLE・SET SESSION AUTHORIZATION で所有者になる。比べるために、弱い設定の broken スキーマ（BYPASSRLS のロールが所有し、FORCE が無く、ビューと SECURITY DEFINER の関数がある）
- 期待する結果：設計どおりの app スキーマでは 5 項目すべて 0 件、SET ROLE は権限エラー。broken スキーマでは 5 項目すべてを検出し、ビューと関数を通すと文脈 t1 でも t2 の行が見える（すり抜けの実例）
- 注：アプリのロールが自分で set_config を呼べることは Postgres では防げない。SQL をパラメータで組むことで守る（観点書の q-db-context-parameterized）

## 9. まだ作っていないテスト

対応表で #8 などが担当し、このファイルにまだ節が無い計画の項目です。要件は `未着手` のままにしています。

| 計画の項目 | 要件 | 作っていない理由 |
| --- | --- | --- |
| `test:negative_tests#legit-idp-variants-accepted` | `p04-reject-missing-required.R4` | シナリオ B の入口の正規化（groups の超過、aud の代わりの client_id）の参照実装がまだ無い |
| `test:negative_tests#insufficient-acr` | `p06-step-up-approval.R1` | acr・auth_time で操作を分ける受け手の参照実装がまだ無い（シナリオ A は認証の強さで操作を分けない） |
| `test:negative_tests#push-delivery-identity` | `p06-flow-partner-events.R5`・`p08-async-processing.R5` | push 配送の受け手の参照実装がまだ無い（シナリオ A・B に push 配送のホップが無い） |
| `test:negative_tests#nested-inner-unsigned` | `p09-jwe-sd-jwt.R2`・`p09-checklist.R5` | ネストした JWT を受ける受け手が記入例に無い（担当は #4・#5） |

## 10. 自組織で使うとき

1. 自組織の受け手（API・ゲートウェイ）の前に、このテストのトークンを送る小さな呼び出しを書きます。トークンは `tools/runtime_tests/golden.py` の見本を、自組織の発行者・aud・名前空間に替えて作ります。鍵は試験用のものをその場で作ります。
2. 参照の受け手を自組織の受け手に置き換えたとき、拒否の理由のコード（`alg-not-allowed` など）は受け手ごとに違います。比べるのは「拒否したか」と、拒否の理由が 1 か所の変更に結びつくか、です。
3. 本番の IdP や本番の鍵では動かしません。live の環境は使い捨てのコンテナです。
