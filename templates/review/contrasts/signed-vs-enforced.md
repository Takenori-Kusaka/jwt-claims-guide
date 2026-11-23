<!-- template_version: 0.4.0 -->
# 対比表：署名で守られていることと、受け手が照合していること

署名が正しいことは、「発行者が書いた値が途中で変わっていない」ことしか示しません。値が正しいか、自分宛てか、今も有効か、誰が元の値を書いたかは、受け手が照合して初めて守られます（slide:p00-incident-signature-valid）。署名の保護が外れた後（ヘッダー・DB の文脈・キャッシュへ写した後）の値は、署名では守られません。

- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施

<a id="question"></a>

## 1. 解く問い

| 仕組み | 解く問い | 解かない問い |
| --- | --- | --- |
| 署名（JWS） | このバイト列は、この鍵の持ち主が作ってから変わっていないか | 中身を読まれていないか、値が現実と合っているか、自分宛てか |
| 受け手の照合 | この発行者・この宛先・この期限・この種類か。値が許可リスト・保存データと合うか | 発行者が元の値をどこから得たか |
| 値の出どころ（書き手） | この値を書いたのは誰か（管理者・本人・テナントの管理者・呼び出し側） | 署名が正しいか |

根拠：RFC 7515 §1、RFC 8725 §3.10、slide:p04-split-by-writer

<a id="unit"></a>

## 2. 仕様上の単位

| 仕組み | 単位 | 台帳・目録の欄 |
| --- | --- | --- |
| 署名 | トークン全体（ヘッダー＋ペイロード）。鍵は `kid`・JWKS で選ぶ | `registry:token_types#alg_allowlist`・`registry:token_types#jwks_uri`・`registry:token_types#key_source` |
| 受け手の照合 | 受け手ごと・クレームごとの規則 | `registry:token_types#required_claims`・`registry:claims#enforced_at`・`registry:hops#validates` |
| 書き手 | クレームの段階ごとの書き手 | `registry:claims#authoritative_writer`・`registry:claims#provenance`・`registry:claims#modifiers` |
| 保護の範囲 | 署名が守る範囲の終わり（ヘッダーに写した後など） | `registry:claims#integrity_until`・`registry:hops#forwarded_headers` |

根拠：RFC 7515 §5.2、RFC 8725 §3.8、template:modules/M_token_validation#validation-order

<a id="table"></a>

## 3. 対比

| 確かめたいこと | 署名で守られるか | 受け手が照合しなければならないこと |
| --- | --- | --- |
| 途中で書き換えられていない | 守られる（署名の範囲の中だけ） | 検証してから読む。アルゴリズムは受け手が決める |
| 正しい発行者が出した | 鍵の持ち主が作ったことだけ | 鍵とその `iss` の対応（その発行者の JWKS の鍵か） |
| 自分宛て | 守られない | `aud` |
| 今も有効 | 守られない | `exp`・`nbf`、失効の状態 |
| 種類が正しい | 守られない | `typ` |
| 別テナントのものでない | 守られない | `iss`・テナントの許可リスト、保存データとの照合 |
| 値が現実と合っている | 守られない（発行時点の写し） | 鮮度の対策（[four-lifetimes.md](four-lifetimes.md)） |
| 値を書いた者が信頼できる | 守られない | 書き手（`provenance`）を見て、確認済みの値だけを認可に使う |
| 読まれていない | 守られない（JWS は誰でも読める） | [jws-vs-jwe.md](jws-vs-jwe.md) |
| ヘッダーに写した後も正しい | 守られない（保護はそこで終わる） | 同名ヘッダーの除去と、写し先を書ける者の限定 |

根拠：slide:p01-validation-order、slide:p12-antipatterns-1、slide:p09-jws-is-readable、slide:p06-header-forwarding

<a id="not-covered"></a>

## 4. 扱わないこと

- アルゴリズムと鍵の長さの選び方（RFC 8725 §3.2）は扱わない。共通の検証部品の設定に従う
- 独自の暗号（独自の署名方式・鍵の導出）は、この表では判定しない。専門家に回す（`review:escalation#custom-crypto`）
- HTTP メッセージ署名（RFC 9421）で本文を守る場合は template:00_core#result-integrity を見る

根拠：RFC 8725 §3.2、RFC 9421 §2

<a id="misuse"></a>

## 5. 典型的な誤用

| # | 誤用 | 起きること | 見つける問い |
| --- | --- | --- | --- |
| m-1 | 署名は秘匿だと考え、ペイロードに秘密・個人情報を入れる | ブラウザ・ログ・中継が読む。署名は改ざんの検出で、秘匿ではない | `q-payload-readable`・`q-no-secret-or-raw-pii` |
| m-2 | トークンの `alg` に従って検証する | `none`・HS256 の混同で偽造（CVE-2015-9235） | `ap-1-1` |
| m-3 | 署名を確かめずに中身で認可する・確かめる前に読む | 誰でもクレームを書ける | `ap-1-2`・`q-validate-before-read`・`q-unverified-claim-extraction` |
| m-4 | 署名が通れば発行者も正しいと仮定する | 別系統の鍵の署名を受理（Storm-0558） | `ap-1-5` |
| m-5 | 署名済みなら値も信頼できると考え、本人・テナントの管理者が書ける値で認可する | 権限の昇格（シナリオ A の A01） | `ap-1-7`・`pa-11`・`q-writer-distinguished` |
| m-6 | ヘッダーに写した値を、署名済みの値と同じに扱う | 同名ヘッダーの偽装でなりすまし | `ap-2-5`・`q-unwrapped-value-authz` |
| m-7 | 入口で検証したので、各サービスは検証しない | 入口を通らない経路から届く | `cf-07`・`q-gateway-bypass-path` |
| m-8 | 「トークンが有効」を「操作してよい」と同じに扱う | 対象・操作の確認が抜ける | `q-validity-not-authz`・`q-object-level-authz` |
| m-9 | 欠けたクレームを既定値で埋めて続ける | フックの失敗が「既定の権限」になる | `q-hook-failure`・`q-no-unverified-passthrough-mode`・`dc-07` |
| m-10 | 受け手ごとに検証の設定を書く | 1 つの受け手の設定漏れが抜け穴になる | `q-shared-validator` |

根拠：slide:p09-jws-is-readable、slide:p12-antipatterns-1、slide:p00-incident-signature-valid、RFC 8725 §3.1
<!-- req:p09-jws-is-readable.R4 req:p12-antipatterns-1.R2 -->

<a id="evidence"></a>

## 6. 根拠

- RFC 7515 §1・§5.2（JWS と検証）、RFC 8725 §3.1・§3.8・§3.9・§3.10・§3.11
- ガイド：slide:p00-incident-signature-valid、slide:p01-validation-order、slide:p12-antipatterns-1、slide:p06-header-forwarding

根拠：RFC 7515 §1、RFC 8725 §3.10、slide:p00-incident-signature-valid
