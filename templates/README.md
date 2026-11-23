<!-- template_version: 0.3.0 -->
# JWT クレームの設計書テンプレート一式

ガイド（JWT クレーム設計ガイド）に沿って、JWT のクレームの設計書を一通り書くためのテンプレートです。設計書は、ユースケースで答えるべき問いと信頼の境界から書き始め、発行方式とトークンを決めてから、その上に載せるクレームを書きます。分割の主軸は「主体 × フロー」（プロファイル）で、認可方式などは部品（モジュール）の判断表にしました（調査レポート Q3。`research/template-design/report.md`）。

**まだ最初の公開版ではありません。** 最初の公開版は `templates-v1.0.0` のタグで出します（#11）。それまでは列や形が変わることがあります。

- 初めての人は [GETTING_STARTED.md](GETTING_STARTED.md)（空の設計書を作り、判定・プロファイルの選択・最初の 3 欄の下書き・claim-lint の実行まで）
- 用語は [glossary.md](glossary.md)（ガイドと同じ訳語）

## 約束の範囲

このテンプレートは「想定漏れが一切生じない」ことを約束しません（#11 の「約束の範囲」）。約束するのは次のことです。

- ガイドの全スライド（対応表 `trace/`）、発行・利用イベントのカタログ（`catalog/`）、主体の状態 × トークン・セッションの 3 つの軸の内側で、判断の未記入・理由の欠落・データ源の不明を claim-lint が機械で検出すること
- 軸の外の漏れは、カタログの外を問う欄（`outside_enumeration`）とレビュー（#5）で探すこと

## 一式の中身

| ファイル | 中身 |
| --- | --- |
| [00_core.md](00_core.md) | 設計書の本体（共通部分）。節の順と、Lite・Full の扱い |
| [claim_request.md](claim_request.md) | 共有クレームを足す前の 25 問（Lite でも必須） |
| [profiles/P1_human_web.md](profiles/P1_human_web.md) | 人がブラウザで使う Web（BFF とトークンを持つ SPA の判断表） |
| [profiles/P4_ai_agent_delegation.md](profiles/P4_ai_agent_delegation.md) | AI エージェントの委任（MCP の認可の必須チェック表） |
| [profiles/P5_internal_propagation.md](profiles/P5_internal_propagation.md) | 内部の伝搬（入口での変換・Txn-Token・サービス間） |
| [modules/M_token_validation.md](modules/M_token_validation.md) | トークンの検証（発行者・alg・typ・時刻・鍵のローテーション・JWKS のキャッシュ・共通の検証部品） |
| [modules/M_authz_pdp.md](modules/M_authz_pdp.md) | 認可の方式（RBAC・ABAC・ReBAC・併用、載せるか問い合わせるか） |
| [modules/M_sender_constraint.md](modules/M_sender_constraint.md) | 送信者制約（DPoP と mTLS、TLS の終端、nonce と jti、RT のローテーション） |
| [modules/M_multitenancy.md](modules/M_multitenancy.md) | マルチテナント（テナントの判定手段とデータ層の絞り込み） |
| [modules/M_privacy_minimization.md](modules/M_privacy_minimization.md) | 個人情報と最小化（個人情報保護法の判断表、監査ログ、保護の要件表） |
| [modules/M_data_layer.md](modules/M_data_layer.md) | データ層（DB の文脈を設定する主体、接続プール、誰として接続するか、RLS をすり抜ける主体） |
| [modules/M_idp_keycloak.md](modules/M_idp_keycloak.md) | Keycloak 26.8（契機・上限・書き換えられないクレーム・カタログの既定の回答） |
| [registry/](registry/) | 台帳のスキーマ（`claims`・`token_types`・`hops`）、問いの一覧、発行方式の効果（#3） |
| [catalog/](catalog/) | 発行・利用イベントのカタログ（#2） |
| [examples/](examples/) | 記入例。シナリオ A（Lite）、シナリオ B（Full。#4 の 2 つ目の PR） |
| [trace/](trace/) | ガイドのスライドとの対応表（#22） |

P2・P3・P6 のプロファイルと、Keycloak 以外の IdP のモジュールは #21（後回し）です。

<a id="lite-criteria"></a>
## Lite と Full の判定

項目 ID：`template:README#lite-criteria`

次の 5 問に Yes／No で答えます。**1 つでも Yes なら Full** にします。答えは `catalog_answers.yaml` の `lite_criteria` に書き（#6 の L73 が `--profile lite` のときに確かめる）、設計書の冒頭にも写します。

| # | 問い（キー） | Yes の例 | 根拠 |
| --- | --- | --- | --- |
| 1 | トークンが信頼の境界を越えるか（`crosses_boundary`） | 取引先・外部の IdP・別の組織のサービスにトークンが渡る | slide:p07-trust-boundary、slide:p06-edge-exchange |
| 2 | マルチテナントか（`multitenant`） | 1 つの発行者・API が複数の顧客のテナントを扱う | slide:p05-multitenancy |
| 3 | 委任・トークン交換があるか（`delegation_or_exchange`） | エージェントの代理、RFC 8693 の交換、入口での作り直し | slide:p10-agent-identity、RFC 8693 §2.1 |
| 4 | 新しい発行者か（`new_issuer`） | 組織で初めて使う IdP・トークン発行サービス・TTS | slide:p04-single-issuer |
| 5 | 規制の対象か（`regulated`） | FAPI・金融・医療・要配慮個人情報 | FAPI 2.0 Security Profile（Final）§5.3.2.1、slide:p09-checklist |

判定がずれるとき（例：マルチテナントだが Lite の欄で書きたい）は、Full にしてから、書かない Full の節を 00_core の 12.（書き手が自信のない点）に理由とともに書きます。シナリオ A の記入例は、Lite の欄がどれだけで書けるかを測るために、Full に当たるケースを Lite で書いています（`examples/scenario-a/design.md` の冒頭）。

根拠：research/template-design/gate1.md の 5.（A17）、筆者の提案：5 問の判定と「1 つでも Yes なら Full」の規則（追跡 #4）

<a id="reduced-lite"></a>
## Lite で書くもの（縮小 Lite）

項目 ID：`template:README#reduced-lite`

関門 1（2026-11-22、判定「絞る」）の縮小案（`research/template-design/gate1.md` の 10.）を、Lite の定義とします。

| 区分 | 00_core の節 |
| --- | --- |
| **手で書く節（5 つ）** | 2. 範囲と信頼の境界（2.1 主体の種類を含む）、3. 既定から外れた点（3.1 重点と見送り、3.2 共通の基準は満たさないものがあるときだけ）、6. 問い × 仕組み、9. ライフサイクル表（9.1。9.2 は寿命が許容を超える行の対策だけ、9.3 は廃止予定の行があるときだけ）、12. 書き手が自信のない点。括弧の中の小節は、gate1.md の 10. の 5 節より書く量を増やすので、ここに明記する |
| 生成する節（`claim_lint render --write`） | 1. CI の結果、4. 発行方式の選択（既定から外れた点だけ 3. に手で書く）、5. トークン目録、8. ホップの表（交換・作り直しのホップがあれば手で書く）、10. 判断の行、11. カタログへの回答の集計 |
| Full だけの節 | 7. シーケンス図、9.3 クレームの定義の寿命（廃止予定の行があれば Lite でも書く）、付録 |
| **Lite でも必須の様式** | 追加前の 25 問（[claim_request.md](claim_request.md)）。共有クレームを足す・変えるたびに 1 ファイル |

台帳の欄（YAML）は、`templates/registry/README.md` の 2.「縮小 Lite の印」に列ごとの扱い（手で書く・生成・Full のみ）があります。`python tools/claim_lint <設計書> --profile lite` は、R1 の必須の列をこの印に合わせて減らします（`tools/claim_lint/RULES.md` の「R1 の必須の列」）。

カタログの「対象外」：IdP モジュールの既定の回答を引き継げるのは、クライアントの設定のスイッチ 1 つで止めていて、指摘が出ていないイベントだけです（カタログの行の `lite_inherit: true`。Keycloak の I03・I04・I05・I07）。引き継ぐ行にも「設定を確かめた」の欄（`setting_checked`）を 1 つ書きます。指摘が出た行、レルム・クライアントの既定に依存する行（I08 など）、利用イベントは手で書きます。

根拠：research/template-design/gate1.md の 9. と 10.、templates/registry/README.md の 2.、tools/claim_lint/RULES.md の「Lite の既定の回答の引き継ぎ」

<a id="profile-combination"></a>
## プロファイルとモジュールの組み合わせ方

項目 ID：`template:README#profile-combination`

プロファイルは「主体 × フロー」の型で、**信頼の境界ごとに 1 つ**選びます（00_core の 2. の図に、境界ごとに書く）。1 つの設計書で複数のプロファイルを組み合わせてかまいません（例：社員のブラウザの境界は P1、組織の網の中は P5、エージェントが利用者の代わりに呼ぶ経路は P4）。判断そのものは台帳に 1 回だけ書き、プロファイル・モジュールからは台帳の ID で参照します（#4 の方針）。

| 境界・フロー | プロファイル |
| --- | --- |
| 人がブラウザでログインし、Web アプリ・API を使う | P1_human_web |
| AI エージェントが利用者の代わりに、ツール（MCP）・API を呼ぶ | P4_ai_agent_delegation |
| 入口の内側で、サービスからサービスへ利用者の文脈を運ぶ | P5_internal_propagation |
| モバイル・ネイティブ（P2）、M2M だけの API 公開（P3）、取引先との API（P6） | #21（後回し） |

モジュールは、次の条件に当てはまるときに使います。

| モジュール | 使う条件 |
| --- | --- |
| M_token_validation | いつも（受け手が JWT を検証するすべての設計） |
| M_authz_pdp | 認可に使うクレーム（`usage: authz`）があるとき |
| M_sender_constraint | `issuance_profile.sender_constraint` が none 以外のとき、公開クライアントの RT があるとき |
| M_multitenancy | 5 問の 2 が Yes のとき |
| M_privacy_minimization | 個人情報（`pii_category` が該当なし以外）のクレームか、`confidential_from` が空でないクレームがあるとき |
| M_data_layer | クレームを DB の文脈・行単位の制御に写すとき、DB・ブローカーにトークンで接続するとき |
| M_idp_keycloak | 発行者が Keycloak のとき（ほかの IdP は #21） |

根拠：research/template-design/report.md の Q3、筆者の提案：境界ごとに 1 つのプロファイルを選び、条件に当てはまるモジュールを足す（追跡 #4）

<a id="writing-order"></a>
## 記入の順序

項目 ID：`template:README#writing-order`

1. **判定**：上の 5 問で Lite か Full かを決める
2. **範囲と信頼の境界**（00_core の 2.）：境界を図にし、境界ごとにプロファイルを選ぶ。あわせて **問い × 仕組みの下書き**（00_core の 6.）として、ユースケースごとにどの問いが要るかだけを決める（仕組みは 5. で決める）
3. **発行方式の選択**（`token_types.yaml` の `issuance_profile`。00_core の 4.）：既定の組み合わせから外れる点を決める。送信者制約などの選択で、台帳に要るものが変わる（`registry/issuance_effects.yaml`）
4. **トークン目録**（`token_types.yaml` の `token_types`。00_core の 5.）：17 種類のすべてに採否を付ける
5. **問い × 仕組み**（00_core の 6.）：ユースケースごとに 11 問へ答える仕組みを決める
6. **台帳**（`claims.yaml`）：クレームの行を書く。組織の名前空間に共有クレームを足すなら、先に追加前の 25 問（`claim_request_<名前>.md`）
7. **ホップ**（`hops.yaml`。00_core の 8.）：交換・作り直しのホップがあれば手で書く
8. **ライフサイクル表**（00_core の 9.）：トークン・セッション・接続、クレームの鮮度、定義の寿命
9. **カタログへの回答**（`catalog_answers.yaml`）：全イベントに該当か対象外（前提と崩れる条件）
10. **検査と生成**：`python tools/claim_lint <設計書のディレクトリ> --profile lite`（Full なら `--profile` なし）を error 0 件まで直し、`python tools/claim_lint render <設計書のディレクトリ> --write` で生成の節を埋める
11. **書き手が自信のない点**（00_core の 12.）と、**既定から外れた点**（00_core の 3.）の要約を最後に書く

根拠：research/template-design/gate1.md の 3.（迷った点 16 件）、templates/registry/README.md の 1.、筆者の提案：境界と発行方式を先に決めてから、その結果としてクレームを書く順序（追跡 #4）

<a id="effort"></a>
## 記入の目安（欄の数と時間）

項目 ID：`template:README#effort`

`python tools/count_lite_fields.py --current <記入例のディレクトリ> --profile lite|full` で、記入例の書き手が自分で書いた欄の数を数えました（数え方はスクリプトの冒頭。YAML の各行で、`id` を除き値が null でない欄を 1 と数え、生成の列と節は数えない）。

| 記入例 | 区分 | YAML の手で書く欄 | 設計書の手で書く節 | 追加前の 25 問の手書きの問い | 記入の時間 |
| --- | --- | --- | --- | --- | --- |
| シナリオ A（Keycloak、マルチテナント SaaS） | 縮小 Lite の規則で数えた | 1063（下の表の計から 25 問を除く） | 5 | 56 問（共有クレーム 4 つ × 14 問） | 人の記入時間は未測定 |
| 同じ記入例を Full の規則で数えた（比べるため） | Full | 1375 | 6 | 56 問 | — |

<!-- effort:begin -->
| 対象（scenario-a、lite） | 手で書く欄 |
| --- | --- |
| 台帳：載せて誰かが読む行（15 行） | 410 |
| 台帳：既定どおりで誰も読まない行（4 行） | 49 |
| 台帳：却下の行（6 行） | 50 |
| 発行方式の選択（既定から外れた 0 項目） | 0 |
| トークン目録（18 行） | 166 |
| ホップ（0 行。交換・作り直しのホップだけ） | 0 |
| カタログへの回答（62 件。引き継ぎ 0 件は各 1 欄） | 248 |
| 網羅の節（idp・lite_criteria・questions・subject_states・pairwise・outside_enumeration） | 140 |
| 追加前の 25 問（4 ファイルの手書きの問い） | 56 |
| **YAML と 25 問の欄の計** | **1119** |
| 設計書の手で書く節（00_core の番号） | 5（2・3・6・9・12） |
<!-- effort:end -->

関門 1 の見積もり（`research/template-design/gate1.md` の 10.：縮小 Lite で 700 欄）より多いのは、数える範囲が違うためです。関門 1 は台帳 v0 の列と、カタログの v0 の 19 件だけを数えました（同じ数え方は `python tools/count_lite_fields.py` で再現できる）。今の記入例は、台帳 v1 の列（#3）、カタログを全体に広げた 62 件への回答（#2）、網羅の規則の節（#17）を含みます。また、シナリオ A の記入例は Full の判定に当たり、カタログの既定の回答の引き継ぎ（`inherit`）を使っていません。同じ記入例を同じ数え方で数えると、縮小 Lite は 1119、Full は 1431 で、Lite は Full より 22% 少なくなります。縮小 Lite の数は、生成の列と、台帳の README の 3. で「Full のみ」とした列を除き、目録の却下の行は R1 とスキーマが求める 4 列（kind・decision・rationale・format）で数えています。

**時間について**：記入例の書き手は LLM（Claude）で、人の記入の手間の代わりになりません（`research/template-design/gate1.md` の 2.）。人の記入時間は測っていません。#4 の完了基準「縮小した Lite でシナリオ A を書き直し、人が記入時間を測る（4 時間以内に収まらなければ、もう一度絞るか判定基準を見直す）」は、人が測るまで未了です。

根拠：research/template-design/gate1.md の 2. と 10.、tools/count_lite_fields.py、筆者の提案：記入の手間の目安を欄の数で示す（追跡 #4）

## ライセンス

`templates/` のファイルは [CC0 1.0](LICENSE) です。表示の義務なしに、社内の設計書へそのままコピーできます。ガイド本体は CC BY 4.0、コードは MIT です（[LICENSE-CONTENT.md](../LICENSE-CONTENT.md)）。

## 作成方法

本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。

## 点検状況

> 人による点検は未実施。作成とは別の LLM のセッションで点検した。作成者の 1 日以上空けた見直しは未実施（記録：`research/reviews/templates-conventions-2026-11-22.md`）。テンプレート一式（#4）は、別の LLM のセッションで点検した（記録：`research/reviews/templates-mvp-2026-11-23.md`。材料は `research/reviews/templates-mvp-facts.md`）。作成者の 1 日以上空けた見直しは未実施。

点検の手順と表示の決まりは [CONTRIBUTING.md](CONTRIBUTING.md) の「3. 点検者についての取り決め」にあります。人による点検は、協力者が見つかったときに #20 で行います。

## 検査

```
python tools/new_design.py designs/my-service   # 空の設計書を作る（#4）
python tools/template_check.py                  # テンプレートの項目 ID・根拠の形と実在・記入欄が空か（#4）
python tools/check_slide_refs.py templates      # slide:<id> の実在
python tools/claim_lint templates/examples/scenario-a --profile lite
python tools/claim_lint render templates/examples/scenario-a --check
```

## 規約

根拠の書き方、完了の定義、版の管理、公開の決まり、題材は [CONTRIBUTING.md](CONTRIBUTING.md) にあります。変更の記録は [CHANGELOG.md](CHANGELOG.md) です。
