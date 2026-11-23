<!-- template_version: 0.3.0 -->
# P5 組織の内側の伝搬（profiles/P5_internal_propagation）

> テンプレートです。候補と検討の問いだけを載せ、採否の理由の見本は載せません（理由の写し書きを防ぐため。#4 の方針）。判断は台帳（claims.yaml など）に 1 回だけ書き、ここからは ID で参照します。

- 使う場面：入口（ゲートウェイ）から内側のサービス、サービスからサービス、サービスからキュー・ワーカーへと、利用者の文脈を運ぶ境界。`00_core.md` の「範囲と信頼の境界」で、入口より内側の境界に P5 を書く
- 組み合わせ：外側のログインは P1、エージェントの委任は P4。検証の設定は `template:modules/M_token_validation`、データ層は `template:modules/M_data_layer`
- Lite での扱い：〔Full：記入／Lite：参照〕。入口で交換する設計は、#4 の判定（委任・トークン交換があるか）で Full になります。交換・作り直しのホップは、Lite でもホップの表（`hops.yaml`）を手で書きます（`templates/registry/README.md` の 3.4）
- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施。

<a id="edge-conversion"></a>
## 1. 入口での変換〔Full：記入／Lite：参照〕

項目 ID：`template:profiles/P5_internal_propagation#edge-conversion`
<!-- req:p03-confusing-differences.R1 req:p03-absorb-idp-differences.R1 req:p03-absorb-idp-differences.R3 req:p04-reject-missing-required.R2 req:p04-reject-missing-required.R3 req:p05-one-request-carries.R5 req:p10-vendor-features.R1 req:p11-translation-layer.R1 req:p11-translation-layer.R2 req:p12-priorities-deferrals.R2 -->

決めること：外部の IdP のトークンを入口で検証して終わらせ、組織の内部トークンに作り替えるか。作り替えるなら、IdP ごとの差（利用者のキー・ロールの位置・宛先の表し方・グループの超過・製品の独自クレーム）を、入口で 1 回だけ吸収する規則。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 交換するか | 外部のトークンを内側のサービスに流すか、入口で内部トークンに作り替えるか | 作り替える（内部トークン・phantom token）／そのまま流す | slide:p06-edge-exchange、slide:p11-translation-layer |
| 入口での検証 | IdP ごとの `iss`・`aud`・種類（`typ`・`token_use`・`idtyp`）の検証を、入口で 1 回だけ行うか | 入口で IdP ごとの検証の設定を持つ | slide:p03-absorb-idp-differences、`template:modules/M_token_validation#typ` |
| 利用者のキー | 組織の利用者のキーを、IdP ごとのどのクレームから作るか | Entra は `tid`＋`oid`、Okta の AT は `uid`、Keycloak・Auth0・Cognito は `sub`（どれも `iss` と組で） | slide:p03-confusing-differences、slide:p02-user-identifier |
| 宛先の表し方 | `aud` の無い IdP（Cognito の AT は `client_id`）の宛先を、どう確かめて正規化するか | 入口で `client_id` を照合し、内部トークンの `aud` に写す | slide:p04-reject-missing-required、slide:p03-cognito-token-use |
| ロールの位置 | IdP ごとのロール・グループの位置（`realm_access.roles`・`groups`・`cognito:groups`・名前空間のクレーム）を、組織の語彙にそろえるか | 入口で組織の名前空間のロールに写す | slide:p03-absorb-idp-differences、`claims[].upstream_issuer` |
| scope の形 | scope の形（空白区切り・配列・`scp`）を、組織の形にそろえるか | 入口でそろえる | slide:p03-absorb-idp-differences |
| グループの超過 | グループが上限を超えて消えたトークン（Entra の `_claim_names`）を、どう扱うか | 入口でディレクトリを引いて解決してから必須を確かめる／拒否する | slide:p04-reject-missing-required、jwt-claims-casestudy@080b8da:B9 |
| 製品の独自クレーム | `xms_*` のような製品の独自クレームを、組織の契約にしないか | 入口で `act`・`client_id` などの標準のクレームにそろえる／内部トークンに載せない | slide:p10-vendor-features |
| 内部トークンの形 | 内部トークンは、完全性を守った短命の切符か | 入口が署名する JWT（短命）／Txn-Token（2.）／参照型 | slide:p05-one-request-carries、slide:p06-edge-exchange |
| 共通の基準の当て方 | 共通の基準（必須の欠落の拒否など）を、IdP の差を正規化した後に当てるか | 正規化の後に当てる（正規の要求を落とさない）／IdP のトークンにそのまま当てる | slide:p12-priorities-deferrals、jwt-claims-casestudy@080b8da:B16 |

記入欄（IdP ごとに 1 行）：

| IdP | 利用者のキーの作り方（書き手が書く） | ロール・宛先の写し方（書き手が書く） | 理由（書き手が書く） | 台帳の ID |
| --- | --- | --- | --- | --- |
|  |  |  |  | `claims[].upstream_issuer`・`authoritative_writer` |

| 決めること | 決めたこと（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 交換するか |  |  | `issuance_profile.at_format`、`hops[].kind`（exchange・reissue）・`exchanger` |
| グループの超過 |  |  | `claims[].overflow_strategy`（ロールの行） |
| 内部トークンの形 |  |  | `token_types[]`（kind: internal_token の行） |

根拠：slide:p06-edge-exchange、slide:p03-absorb-idp-differences、slide:p11-translation-layer、slide:p10-vendor-features、jwt-claims-casestudy@080b8da:B16

<a id="txn-token"></a>
## 2. Transaction Token（Txn-Token）〔Full：記入／Lite：参照〕

項目 ID：`template:profiles/P5_internal_propagation#txn-token`
<!-- req:p04-split-by-writer.R4 req:p04-single-issuer.R4 req:p06-transaction-tokens.R1 req:p06-access-context.R3 -->

決めること：呼び出しの連鎖全体の文脈（どの取引か）を Txn-Token で運ぶか。運ぶなら、取得する場所、中身（`tctx`・`rctx`）、運び方、作り直しの規則。仕様は草案で、2026-11-23 の時点の最新は draft-ietf-oauth-transaction-tokens-11（2026-07-30）です。草案に依存する行は、台帳に `spec_version` と見直しの条件を書きます。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 取得する場所 | 入口が TTS から取得するか、内部で始まる処理が取得するか | 入口（§8.1）／内部で始まる処理（§8.2） | draft-ietf-oauth-transaction-tokens-11 §8 |
| 書き手 | サービスの中で文脈を足すとき、各サービスが自分で足すか、TTS（またはトークン交換）に書かせるか | TTS が書く（付与するのは単一の発行者）／各サービスが足す（避ける） | slide:p04-single-issuer、draft-ietf-oauth-transaction-tokens-11 §10 |
| `tctx` と `rctx` | 取引の文脈（TTS が決めた認可の詳細、連鎖の中で変わらない）と、要求の環境（要求元の IP など、要求時点の値）を分けるか | `tctx` に取引の文脈、`rctx` に要求の環境 | draft-ietf-oauth-transaction-tokens-11 §9.2.2・§9.2.3、slide:p04-split-by-writer |
| アクセス元の文脈 | 要求元の IP などを伝えるなら、TTS が書く `rctx` に入れるか | `rctx`／独自のヘッダー（避ける） | slide:p06-access-context |
| 運び方 | サービス間で、Txn-Token を専用のヘッダーで、受け取ったまま渡すか | `Txn-Token` ヘッダーで改変せずに渡す（§12.1・§12.2）／Authorization ヘッダー（使わない） | draft-ietf-oauth-transaction-tokens-11 §12.1・§12.2、slide:p06-transaction-tokens |
| 寿命 | Txn-Token の寿命を何秒にするか。元のトークンより長くするか | 分以下（§6）。元のトークンより長いなら、ホップの表の `narrowing_exception` に書く | draft-ietf-oauth-transaction-tokens-11 §6、templates/registry/README.md の 3.4 |
| 作り直し | Txn-Token を subject token にして作り直すとき、何を変えてよいか | 権限を減らす・値を足すのは可／scope の拡大と `txn`・`sub`・`aud` の変更は不可 | draft-ietf-oauth-transaction-tokens-11 §13.15、slide:p06-transaction-tokens |
| AT として使わない | Txn-Token を AT として受け入れる経路がないか | 経路なし（§13.13）／ある | draft-ietf-oauth-transaction-tokens-11 §13.13 |
| ログ | Txn-Token の全体をログに出さないか | 出さない（`txn` だけ記録） | draft-ietf-oauth-transaction-tokens-11 §15.2 |

記入欄：

| 決めること | 決めたこと（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 取得する場所 |  |  | `token_types[]`（kind: txn_token の行の `issuer`） |
| `tctx`・`rctx` の中身 |  |  | `claims[]`（tctx・rctx の行の `authoritative_writer`） |
| 運び方 |  |  | `token_types[].transport`（txn_token_header） |
| 寿命 |  |  | `token_types[].max_lifetime`、`hops[].narrowing_exception` |

根拠：draft-ietf-oauth-transaction-tokens-11 §6、slide:p06-transaction-tokens、slide:p04-split-by-writer、slide:p06-access-context

<a id="service-to-service"></a>
## 3. サービス間の呼び出し〔Full：記入／Lite：参照〕

項目 ID：`template:profiles/P5_internal_propagation#service-to-service`
<!-- req:p06-validation-split.R7 -->

決めること：内側のサービスどうしの呼び出しで、呼び出し元のサービスと利用者をそれぞれ認可する方法。直接の通信相手（mTLS・SPIFFE などのワークロードの ID）は、`act`（誰が代理して実行しているか）とも、Txn-Token（どの取引か）とも別の問いです。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 直接の通信相手 | 呼び出し元のサービスを何で確かめるか | mTLS（SPIFFE ID など）／ワークロードの ID のトークン／確かめない（避ける） | slide:p06-validation-split、templates/registry/questions.yaml の q-peer |
| 利用者 | 元の利用者の権限で判断するか（仲介サービスの権限で判断しない） | 内部トークン・Txn-Token の `sub` で判断する | slide:p06-validation-split、ASVS v5.0.0-8.3.3 |
| 両方の認可 | 呼び出し元のサービスに許す操作と、利用者に許す操作の両方を確かめるか | 両方を確かめる／利用者だけ | NIST SP 800-228-upd1 REC-API-12、slide:p06-validation-split |
| 各サービスの検証 | 入口で検証した後も、各サービスが受け手としての検証（自分宛てか・署名・期限）をするか | 共通の検証部品で再確認する／入口に任せる | RFC 9068 §4、slide:p06-validation-split |
| 入口を通らない経路 | 入口を通らずにサービスへ届く経路はないか | ない（ネットワークで閉じる）／ある（サービスが検証する） | jwt-claims-casestudy@080b8da:B7 |
| `req_wl` | Txn-Token の `req_wl`（Txn-Token を求めたワークロード）と、直接の通信相手を照合するか | 照合する／しない | draft-ietf-oauth-transaction-tokens-11 §9.2、slide:p06-flow-browser-to-db |

記入欄：

| 呼び出し（from → to） | 通信相手の確かめ方（書き手が書く） | 利用者の確かめ方（書き手が書く） | 理由（書き手が書く） | 台帳の ID |
| --- | --- | --- | --- | --- |
|  |  |  |  | `hops[].validates`、`claims[].enforced_at` |

根拠：slide:p06-validation-split、NIST SP 800-228-upd1 REC-API-12、RFC 9068 §4

<a id="async-messaging"></a>
## 4. 非同期の処理（キュー・イベント）〔Full：記入／Lite：参照〕

項目 ID：`template:profiles/P5_internal_propagation#async-messaging`
<!-- req:p06-flow-partner-events.R6 req:p08-async-processing.R2 req:p08-async-processing.R3 -->

決めること：キューやイベントに利用者のトークンを入れずに、利用者の文脈を運ぶ方法。メッセージには主体の間接参照と `txn`・承認 ID だけを入れ、ワーカーは自分のワークロード ID で認証してトークンを作り直します。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| メッセージの中身 | メッセージに何を入れるか | 主体の間接参照（ハッシュ）・`txn`・承認 ID・テナント／利用者のトークン（入れない） | slide:p08-async-processing、CloudEvents Auth Context（1.0） |
| 資格情報 | `authclaims` などに資格情報を入れていないか | 入れない | slide:p08-async-processing |
| ワーカーの認証 | ワーカーは何で自分を証明するか | 自分のワークロード ID（mTLS・ワークロードの ID のトークン） | slide:p08-async-processing、templates/registry/questions.yaml の q-peer |
| 下流の呼び出し | ワーカーが下流を呼ぶとき、どのトークンを使うか | 交換で作り直す（`sub`＝利用者、`act`＝ワーカー、分単位）／自分の ID で Txn-Token を取る | slide:p08-async-processing、slide:p08-downstream-after-expiry |
| 有効性の判断 | 利用者と承認がまだ有効かを、誰が判断するか | TTS・AS が作り直しのときに判断する／ワーカーが自分で判断する | slide:p06-flow-partner-events |
| 配送の認証 | ブローカーからワーカーへの配送を認証するか（push の場合） | 配送に OIDC のトークンを付け、受け手が `aud` などを確かめる | slide:p08-async-processing |

記入欄：

| 決めること | 決めたこと（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| メッセージの中身 |  |  | `claims[].log_policy`、`hops[]`（kind: broker_connection） |
| ワーカーの認証 |  |  | `token_types[]`（ワーカーのトークンの行） |
| 下流の呼び出し |  |  | `token_types[].long_running` |

根拠：slide:p08-async-processing、slide:p06-flow-partner-events、draft-ietf-oauth-transaction-tokens-11 §6

<a id="registry-map"></a>
## 5. 台帳・目録との対応

項目 ID：`template:profiles/P5_internal_propagation#registry-map`

| 決めること | 列 |
| --- | --- |
| 交換・作り直しのホップ | `hops[].kind`（exchange・reissue）・`exchanger`・`upstream`。下流は上流を超えない（`aud`・`scope`・寿命・独自クレーム。#6 の L16） |
| 上流の値の写し方 | `claims[].upstream_issuer`（上流の `iss` と正規化の規則） |
| 書き手 | `claims[].authoritative_writer`（入口・TTS） |
| ヘッダーへの転記 | `hops[].forwarded_headers`（同名を捨てる・書ける者）、`claims[].integrity_until` |
| 照合する場所 | `claims[].enforced_at`、`hops[].validates` |
| Txn-Token | `token_types[]`（kind: txn_token。`transport: txn_token_header`） |

根拠：templates/registry/README.md の 3.1・3.4、slide:p06-narrow-downstream
