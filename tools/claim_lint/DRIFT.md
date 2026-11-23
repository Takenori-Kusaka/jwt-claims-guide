# claim_lint import／drift（IdP の設定と台帳のずれを検出する）

台帳（設計の正本）と、IdP の実際の設定とのずれを検出します（#30）。設計書を YAML で正本にしても、IdP の設定が別に変えられれば、設計書は実態を表さなくなるためです（`research/claims-as-code/notes/claims_as_code_design.md` の 5.）。MVP の対象は Keycloak（26.8）だけです。コードは `tools/claim_lint/keycloak.py`（取り込み）と `tools/claim_lint/drift.py`（比較）です。

```
python -m tools.claim_lint import keycloak <realm-export.json> -o <observed.yaml>       # 取り込みと正規化
python -m tools.claim_lint drift <設計書のディレクトリ> <observed.yaml>                  # 台帳との差分（表）
python -m tools.claim_lint drift <設計書のディレクトリ> <realm-export.json> --format json  # 書き出しをその場で取り込んでもよい
python -m tools.claim_lint drift templates/examples/scenario-a \
    tools/tests/fixtures/claim_lint/keycloak/scenario-a-t1.observed.yaml \
    --token AT=tools/tests/fixtures/claim_lint/keycloak/scenario-a-t1.at.json \
    --token IDT=tools/tests/fixtures/claim_lint/keycloak/scenario-a-t1.idt.json            # 発行したトークンも照合する
```

`python tools/claim_lint import …`・`python tools/claim_lint drift …` でも同じです。error が 1 件でもあれば終了コード 1 です。抑止の設定はありません（`templates/CONTRIBUTING.md` の 2.）。受け入れる差分は、台帳か設定のほうを直すか、残す理由を設計書に書きます。

- 1. 取り込み（import keycloak）
- 2. 比較の範囲（どのクライアントを見るか）
- 3. 規則（D0〜D14）
- 4. 静的に読めない部分と、発行したトークンでの補い
- 5. シナリオ A の結果
- 6. 範囲外と、まだ確かめていないこと

## 1. 取り込み（import keycloak） <a id="import"></a>

入力は Keycloak のレルムの表現（RealmRepresentation）です。管理 API の部分書き出し（`POST /admin/realms/{realm}/partial-export?exportClients=true&exportGroupsAndRoles=true`。秘密は `**********` に伏せられる）、`kc.sh export`、keycloak-config-cli のファイル（JSON か YAML）のどれでも読みます。

正規化（比べる前の雑音の除去。調査メモの「配列を名前でソートし、内部 ID・タイムスタンプ・秘密を捨てる」）：

| 何を | どうする |
| --- | --- |
| 内部 ID（`id`・`containerId`）・タイムスタンプ（`client.secret.creation.time` など）・秘密（`secret`、鍵・証明書の属性） | 捨てる |
| クライアント・クライアントスコープ | 名前をキーにした表にする（配列の順序に依存しない） |
| マッパー・ロール・スコープの一覧 | 名前で並べる |
| クライアントの属性 | 比較に使うもの（下）を名前の付いた値にし、属性が無いときの Keycloak の既定を入れる（例：`standard.token.exchange.enabled` が無ければ OFF。#4 の K2 の実測）。そのほかは名前だけを `other_attributes` に残す |
| マッパー | 種類ごとにクレームの名前（エスケープしていない `.` で入れ子にする Keycloak の規則で分けたパス）、載るトークン（`access.token.claim` などの既定は Keycloak 26.8 の後方互換：AT とイントロスペクションは無ければ ON、ほかは OFF）、JSON の型、Multivalued、固定値（Hardcoded claim） |

同じ書き出しからは、配列の順序や内部 ID が違っても同じファイルができます（`tools/tests/test_claim_lint_drift.py` の `test_normalization_ignores_array_order_and_internal_ids`）。

正規化の結果（`format: claim-lint-keycloak-observed/1`）には、クライアントごとに次の 2 つを計算して入れます。

- `effective_role_scope`：トークンに出うるロール。Full Scope Allowed が ON ならレルムのすべてのロール、OFF ならクライアントと既定のクライアントスコープのスコープの割り当て（複合ロールを展開）
- `emits`：トークン（`access`・`id`・`userinfo`）ごとに静的に読めるクレームの一覧。クライアントのマッパー、既定のクライアントスコープのマッパー、任意のクライアントスコープのマッパー（`optional: true`。要求されたときだけ）と、マッパーなしで Keycloak が書くクレーム（`tools/claim_lint/keycloak_implicit.yaml`）。軽量アクセストークンのクライアントでは、Add to lightweight access token が ON のマッパーと、軽量でも外せないクレームだけにする

`keycloak_implicit.yaml` の値は、Keycloak 26.8.0 で実際に発行したトークンにあって、どのマッパーも書かないクレームです。**この一覧は保存したトークンから作ったので、マッパーなしのクレームについては、同じトークンとの一致は独立した確かめになりません。** 独立して確かめたのは次の 2 つだけです。
- マッパーの部分：書き出しから計算したクレーム（マッパー・スコープ由来）が、トークンにある（`test_static_view_equals_the_claims_of_the_issued_tokens`。saas-web の設定 1 つについて）
- 再現：PR #47 の独立点検で、別の実行で同じレルムを作り直して発行したトークンのクレーム名の集合が、保存したものと一致した

軽量アクセストークンの一覧と、roles・acr などのスコープを付けたときのマッパーなしのクレームは実測していません。`cnf` は、クライアントが DPoP か mTLS でトークンを束縛するときだけ含めます（`only_if`）。

## 2. 比較の範囲（どのクライアントを見るか） <a id="scope"></a>

台帳のトークン種別が表すトークンを出すクライアントだけを比べます。無効なクライアント（`enabled: false`）は比べず、D13 の info に名前を出します。

- ID トークンの種別（`kind: id_token`）：その種別の `aud` に名前があるクライアント
- アクセストークンの種別（`kind: access_token`）：Audience マッパー（クライアント自身のものと、既定・任意のクライアントスコープのもの）が、その種別の `aud` のどれかを書くクライアントと、ID トークンの種別で当たったクライアント。ID トークンを受け取るクライアントは AT も受け取るので、Audience マッパーを動かしたり値を変えたりしても比較から外れません（PR #47 の独立点検の 1）。どのクライアントにも当たらない AT・ID トークンの種別があれば D0
- 受け手のクライアント：比べる AT の `aud` に名前があるクライアント（例：saas-api）。そのトークンを交換に使えるので、カタログで「対象外」と答えた grant のスイッチ（D9）だけを確かめます

`--client` で明示もできます。どの種別にも当たらないのにトークンを出せるクライアント（既定のクライアントの `account-console`・`admin-cli` など）は D13 の info にまとめます。

## 3. 規則（D0〜D14） <a id="rules"></a>

| ID | 内容 | 重大度 | 台帳の側 |
| --- | --- | --- | --- |
| D0 | 比べるクライアントが無い（`--client` の名前が設定に無い）。採用・既定どおりの AT・ID トークンの種別のうち、どのクライアントにも当たらないものがある | error | `token_types` の `aud` |
| D1 | 設定が出すクレームが、台帳でそのトークン種別に載せると宣言していない（`carried_in` に無い）か、台帳で却下したクレーム。任意のクライアントスコープからだけ出るなら warn | error（任意のスコープは warn） | `claims` の `decision`・`carried_in` |
| D2 | 台帳でそのトークン種別に載せるクレームを、設定のどのマッパーも出さない。`required_claims` にあれば error | error（必須でなければ warn） | `claims` の `carried_in`、`token_types` の `required_claims` |
| D3 | マッパーの JSON の型・Multivalued が、台帳の `type`・`shape` と違う。User Attribute・User Property マッパーが読む利用者の属性の名前が、台帳の行の `source_system`・`authoritative_writer` の書き手に語として無い（例：user_id を id でなく username から読む）。ロールのマッパーの種類（レルムのロール・クライアントのロール）が、台帳の書き手（User Realm Role マッパーなど）と違う | error | `claims` の `type`・`shape`・`source_system`・`authoritative_writer` |
| D4 | 設定が決める値が台帳の制約を満たさない。Hardcoded claim の固定値と、ロールのマッパー（レルムのロール・クライアントのロール）が出しうるロール（`effective_role_scope`）を、そのトークン種別の発行側の検査用スキーマ（#19、`enum`・`pattern`・`maxLength`・`maxItems`）の該当の部分で検証する。aud は、Audience マッパー（クライアントとクライアントスコープ）と audience resolve が書く値の集合を、トークン種別の `aud` と比べる（足りない値・余分な値。余分な値が任意のスコープからだけなら warn） | error（任意のスコープの aud は warn） | `claims` の `max_bytes`・`max_items`・`allowed_values`・`value_vocabulary`、`token_types` の `aud` |
| D5 | 寿命：AT・ID トークン（レルムの accessTokenLifespan か、クライアントの Access Token Lifespan）、RT（SSO Session Idle・Max と、クライアントのセッションの idle・最大の短いほう）、IdP のセッション（`kind: session`・`stored_at: idp` の種別）、認可コード（Client login timeout）。レルムの Remember Me が ON なら、覚えたセッションの値（`ssoSessionIdleTimeoutRememberMe`・`ssoSessionMaxLifespanRememberMe`）が長いときはその値で比べる。設定のほうが長ければ error、短ければ warn | error（短いのは warn） | `token_types` の `max_lifetime`・`idle_timeout` |
| D6 | RT のローテーション：台帳の `rt_rotation`（無ければ `issuance_profile.rt_strategy`）とレルムの Revoke Refresh Token、Refresh Token Max Reuse が 0 でない、台帳に RT があるのにクライアントの Use refresh tokens が OFF | error | `token_types` の `rt_rotation`、`issuance_profile.rt_strategy` |
| D7 | AT のヘッダーの `typ`（クライアントの Use "at+jwt" as access token header type）と、署名のアルゴリズム（クライアントの設定かレルムの既定）が、台帳の `typ`・`alg_allowlist` と違う | error | `token_types` の `typ`・`alg_allowlist` |
| D8 | クライアントの種類（公開・機密）とクライアント認証（Client Authenticator）が、台帳の `issuance_profile` と違う。`client-secret` は `client_secret_basic`・`client_secret_post` のどちらとも合う（Keycloak はどちらも受ける） | error | `issuance_profile.client_type`・`client_auth` |
| D9 | grant のスイッチ：台帳が使わない grant が ON（`issuance_profile.grants` に無い。カタログのイベントの回答が「該当」なら ON でよい）、台帳が使う grant が OFF、認可コードを使うのに PKCE Method が S256 でない。スイッチとイベント：Standard Flow（I01）、Direct Access Grants（I04）、Service accounts（I05）、Standard token exchange（I06）、Device Authorization Grant（I07）、Implicit Flow（I10）、CIBA（I13）、JWT Authorization Grant（I15）。受け手のクライアント（2.）では、カタログで「対象外」と答えたイベントのスイッチが ON なら error（saas-api で Standard token exchange を ON にすると、saas-web の AT を交換する要求が 400 から 200 に変わった。Keycloak 26.8.0、`scenario-a-t1.exchange.json`） | error | `issuance_profile.grants`、`catalog_answers.yaml` |
| D10 | Full Scope Allowed が ON（Keycloak の文書が全クライアントで無効にするよう求めている。#4 の K15） | error | `claims` の `assumption` など（スコープでロールを絞る前提） |
| D11 | 台帳で却下した種類・方式のトークンを出せる：Backchannel logout URL（ログアウトトークン、I09）、Require DPoP bound tokens（送信者制約が dpop でない、I29）、軽量アクセストークン（I03）、offline_access のクライアントスコープ（オフラインの RT、I08 が対象外）、Organizations の organization のスコープ（I24 が対象外）。レルムのクライアントのプロファイルの executor `use-lightweight-access-token` は、どのクライアントに効くかを静的に評価しないので warn | error（プロファイルは warn） | `token_types` の却下の行、`issuance_profile.sender_constraint`、`catalog_answers.yaml` |
| D12 | 静的に読めない部分：知らない種類のマッパー（スクリプトのマッパー・拡張）、有効なクライアントのポリシー | warn | — |
| D13 | どの種別にも当たらないのにトークンを出せるクライアント。無効なクライアント（比べない） | info | `claims` の `enforced_at`（受け手が aud・azp で拒否する） |
| D14 | `--token` で渡した、実際に発行したトークンが、そのトークン種別の発行側の検査用スキーマ（#19、`additionalProperties: false`）を満たさない | error | 台帳全体（`render.payload_schema`） |

重大度の決め方：台帳と設定のどちらかを直さないと設計書が実態を表さない差分は error にしました。warn は、台帳より安全側の違い（寿命が短い・必須でないクレームが出ない）と、要求のしかたしだいで出る差分（任意のスコープ）と、静的に判定できない部分です。誤検知の率は、シナリオ A の 1 件のレルムでしか測っていません（5.）。

## 4. 静的に読めない部分と、発行したトークンでの補い <a id="tokens"></a>

書き出しを読むだけでは分からないものがあります。

- マッパーなしで Keycloak が書くクレーム（`keycloak_implicit.yaml` は 26.8.0 の実測で、版が変われば変わりうる）
- スクリプトのマッパーや拡張のマッパー、クライアントのポリシーの条件と executor の効き方（D12・D11 の warn）
- 利用者ごとの値（ロールの実際の割り当て、属性の値の長さ）
- Hardcoded claim の値とレルムの対応（例：tenant_id の固定値がレルム名と同じか）。台帳にこの対応を表す列が無く、発行側のスキーマも長さしか見ないので、t1 を t2 に変えても静的にも D14 でも出ない。値の語彙を台帳に書いていない固定値（例：v の "1"。enforced_at の文に書いてあるだけ）を変えたものも同じ
- 利用者の属性の中身（user_id を username から読むように変えると D3 で出るが、属性の名前を変えずに中身の入れ方を変えたものは出ない。D14 も長さしか見ない）
- サーバーの機能（`--features`。I16・I34 の止め方）は書き出しに入らない

そこで、実際に発行したトークンを `--token TYPE=FILE` で渡し、#19 の発行側の検査用スキーマ（台帳にないクレームを許さない）で検証します（D14）。静的な読み取りと発行したトークンの両方で同じ差分が出ることを、シナリオ A の ID トークンの jti・at_hash（5.）と、わざとずらしたレルム（`scenario-a-t1-shifted.*`）で確かめました。トークンの署名は検証しません（形の検査だけ）。

## 5. シナリオ A の結果 <a id="scenario-a"></a>

2026-11-23 に、Keycloak 26.8.0（`quay.io/keycloak/keycloak:26.8.0`、start-dev。WSL の Docker、ポート 28080、使い終えたコンテナは削除）に、この例のレルム t1（`tools/tests/fixtures/claim_lint/keycloak/scenario-a-t1.import.json`）を作り、認可コード＋PKCE で alice をログインさせ（I01）、1 回リフレッシュし（I02）、レルムを書き出しました。作り方は同じ場所の `measure.py` です。

| 段階 | 差分 | 直したもの |
| --- | --- | --- |
| 最初の比較 | error 3：ID トークンに台帳に無い `jti`・`at_hash` が出る（D1 の 2 件。静的な読み取り）と、保存した ID トークンが発行側の検査用スキーマを満たさない（D14 の 1 件。同じ 2 つのクレーム） | 台帳を実態に合わせた：`C-jti` の `carried_in` に IDT を足し、`C-at-hash` を既定どおりで足した（`templates/examples/scenario-a/design.md` の 13. の 0.2.4） |
| 直した後 | **error 0・warn 0・info 1**。info は D13：どのレルムにもある既定のクライアント（`account`・`account-console`・`admin-cli`・`security-admin-console`）がトークンを出せる。理由：これらのトークンの `aud` は saas-api でなく、`azp` は saas-web でないので、saas-api（`C-aud`・`C-azp` の `enforced_at`）と BFF（ID トークンの `aud`）が拒否する | — |

わざとずらした例（`tools/tests/test_claim_lint_drift.py`）：#30 の 3 つ（マッパーを 1 つ足す → D1、寿命を延ばす → D5、Full Scope Allowed を ON → D10 と D4）は、書き出しの JSON を変えたものと、実際に Keycloak の上でずらして書き出したもの（`scenario-a-t1-shifted.export.json`）の両方で検出し、ずらした後に発行した AT は発行側の検査用スキーマで失敗する（D14）。ほかに、却下したクレームを出すスコープの追加、マッパーの削除、固定値・型・Multivalued の変更、grant のスイッチ 8 つ、PKCE、Backchannel logout URL、DPoP、offline_access、ローテーション、ヘッダーの typ、署名のアルゴリズム、クライアントの種類と認証、軽量アクセストークン、知らない種類のマッパーで、それぞれの規則が出ることを確かめています。PR #47 の独立点検を受けて、Audience マッパーを既定のスコープに移す（差分なし）・値を変える・余分な宛先を足す・ID トークンにも出す、受け手のクライアント saas-api で交換を ON にする、Remember Me で長くする、クライアントのロールのマッパーに変える、user_id の元の属性を変える、無効なクライアントを足す（info だけ）、軽量 AT で cnf を求めない、を足しました。

CI（`.github/workflows/claims.yml`）は、保存した書き出しとトークンでオフラインに動きます（Keycloak を起動しない）。保存した正規化の結果（`scenario-a-t1.observed.yaml`）が書き出しから作り直したものと一致することも確かめます。

## 6. 範囲外と、まだ確かめていないこと <a id="limits"></a>

- Keycloak だけです。Auth0・Entra・Cognito などは #21
- 1 つのレルム（t1）だけを比べます。シナリオ A はテナントごとにレルムを分けるので、運用ではレルムごとに drift を回します（t2 の書き出しは保存していない）
- 管理画面の既定、サーバーの機能、利用者ごとの値、イントロスペクションと UserInfo の応答は比べません（UserInfo は `emits` に出すだけ）
- JAR・JARM・PAR の設定（`request.object.required` など）は読みますが、規則にしていません
- 運用の中での定期的な実行（夜間に管理 API で書き出して比べる）は、この MVP に入れていません。CI は保存した書き出しで動きます。設定を変えたら、書き出しとトークンを取り直して `measure.py` の手順で保存し直します
- シナリオ B の Keycloak の書き出しはまだありません
- 誤検知の率は、シナリオ A の 1 件でしか測っていません。規則を error で入れたのは、#13 の「抑止・重大度の引き下げを 0 件」に合わせ、誤検知が出たら規則のほうを直すためです
- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施
