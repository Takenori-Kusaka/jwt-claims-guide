<!-- template_version: 0.4.0 -->
# 人に渡す短い一覧（レビュアーが答える問い）

<!-- このファイルは python tools/review_triage.py --write が templates/review/triage.yaml から作る。手で直さない -->

レビュアーが答える問いの全部です。1 つの設計で答えるのは、このうち設計の性質に当たる分だけで、**その 1 枚は `python tools/review_triage.py --design <設計書のディレクトリ>` が作ります**。既定で出すのは優先 1 の問い（設計ごとに 10〜18 問）と、開いた問い 3 つです。時間の目安は、問いに答えるのに 30〜60 分、レビューの全体（手順の段 0〜6）で 70〜110 分です（LLM の見積もり。**人では測っていません**。#20）。この文書の作り方・ここに無い問いの行き先は、末尾の 8. にあります。

<a id="traits"></a>

## 1. 先に、設計の性質を読む

問いは、設計の性質に当たるものだけを出します。`--design` の 1 枚の先頭に、12 の性質が「当たる／当たらない／読めない」と、読んだ欄つきで出ます。
**レビュアーは、手順の段 1 で、この表を図と要求に照らして確かめます**（1〜2 分）。「当たらない」とされた性質が実際にはあるなら、それ自体を指摘にし、その性質の問いも足して答えます。

| 性質 | 読み方 | 出る問い（優先 1） | 時間があれば（優先 2） | 出る開いた問い |
| --- | --- | --- | --- | --- |
| どの設計でも | 条件なし | 8 | 1 | 5 |
| 組織独自のクレームがある | 採用の行に、名前空間つきの行、または登録名でない（registered_ref が無い）認可・識別子の行がある | 0 | 1 | 0 |
| 個人情報を載せる | 採用の行の pii_category に「該当なし」以外がある | 0 | 1 | 0 |
| 発行者（IdP）が複数ある | 採用の種別の issuers の iss のホストが 2 種類以上、または upstream_issuer のある採用の行がある（同じ IdP のレルム違いは数えない）。または catalog_answers.yaml の idp が、名前の違う IdP を 2 つ以上並べた配列（台帳 0.3.0、#58） | 1 | 1 | 0 |
| トークンの交換・作り直しがある | ホップに kind が exchange・reissue の行がある、または catalog_answers の lite_criteria.delegation_or_exchange が Yes | 3 | 1 | 0 |
| 委任がある（代理で動く主体がいる） | 採用の行に act・may_act がある、採用の種別に max_delegation_depth がある、または catalog_answers の questions.q-actor が「要る」。どれも無いのに lite_criteria.delegation_or_exchange が Yes なら「読めない（要確認）」として問いを出す | 6 | 2 | 0 |
| 操作ごとの承認がある | 採用の行かホップに authorization_details がある | 2 | 0 | 0 |
| マルチテナント | catalog_answers の lite_criteria.multitenant が Yes。この回答が無いときだけ、採用の種別の tenant_binding の有無で読む | 1 | 1 | 0 |
| トークンの値を DB の層まで運ぶ | ホップに kind が db_connection の行がある | 1 | 0 | 0 |
| 認証の強さ・新しさで判断する | 採用の行に acr・amr・auth_time がある | 1 | 1 | 0 |
| 送信者制約を選んだ | 採用の種別に sender_constraint が dpop・mtls の行がある、または catalog_answers の questions.q-holder が「要る」 | 0 | 0 | 1 |
| 送信者制約を見送った | 採用のアクセストークン・内部トークンに、sender_constraint が none か未記入の行がある | 0 | 1 | 0 |
| 長時間・非同期の処理がある | 採用の種別に long_running がある、またはホップに kind が broker_connection の行がある | 0 | 1 | 0 |

- 性質は、**台帳が示すか、書き手が宣言していれば**当たります。読むためのファイルが無い・宣言どうしが食い違う性質は「読めない」として、問いを出します。黙って一覧を短くしません
- 条件を 2 つ以上持つ問いは、どれか 1 つに当たれば出ます（上の表では、それぞれの行で数えています）

<a id="questions"></a>

## 2. 問い（優先 1。既定で出す 19 問のうち、設計の性質に当たるもの）

問いは 1 文です。**自分の言葉で答えを 1 行書けるか**を確かめ、書けない・設計書から読み取れないなら指摘にします。斜体は手がかり（見る場所と、あわせて確かめること）で、問いだけで答えられるなら読まなくてかまいません。「見る欄」は、開く設計書の節（`template:…`）と台帳の列（`registry:…`）です。No のときの重大度の目安と根拠は、観点書の同じ ID の問いにあります。

<a id="unit-row"></a>

### クレームの行を読みながら（認可・識別子に使う行から、抜き取った 3 行について答える）

**全部の行には答えません。** 認可・識別子に使う行（`usage` が authz・identifier）から 3 行を抜き取り、その行について答えます。抜き取る行は `--design <ディレクトリ> --seed <種>` が決めます（同じ種なら同じ行）。**種はレビュアーが決めます**（PR の番号など。書き手が先に行を知れないように）。付けなければ、台帳の内容と日付から作った種を 1 枚に書きます。種はレポートに書きます。組織独自の認可の行（名前空間つきで `usage` が authz。ロール・グループなど）があれば、**必ず 1 行入れ**、残りを種で引きます（値を書ける人・鮮度の問いは、この行でこそ効くため）。問いが名指す行が抜き取りに無ければ、その行を足します。抜き取った行で答えが No なら、残りの行も見ます。

| 問い ID | 問い | 出す条件 |
| --- | --- | --- |
| `dc-05` | **認可に使うオブジェクトの値の、内側の型と比べ方が決まっているか**<br>*authorization_details などオブジェクト型の行の type・value_normalization と、受け手のスキーマを見る。金額・ID は文字列か*<br>見る欄：`registry:claims#type`、`template:claim_request#q07`、`template:claim_request#q08`<br>（機械で決まる問い。lint の規則ができるまで） | 操作ごとの承認がある |
| `q-value-vocabulary` | **ロール・グループの値を、名前でなく変わらない ID で照合しているか**<br>*value_vocabulary・upstream_issuer を見る。発行者が複数あるなら、別の発行者の同じ文字列（admin など）を同じ意味として通していないか、値を付けられるのは誰かも見る*<br>見る欄：`registry:claims#value_vocabulary`、`registry:claims#upstream_issuer` | どの設計でも |
| `q-identifier-choice` | **利用者・テナントを決めるキーに使う IdP ごとの値が、台帳の行になっているか**<br>*hops の validates と upstream_issuer に出るクレームの名前（oid・tid・uid など）を、claims.yaml の行と照らす。行に identifier_properties と on_missing があるか*<br>見る欄：`registry:claims#usage`、`registry:claims#identifier_properties`、`registry:token_types#subject_type`、`template:00_core#principals`、`template:modules/M_multitenancy#tenant-determination`<br>（機械で決まる問い。lint の規則ができるまで） | 発行者（IdP）が複数ある |
| `ap-1-7` | **権限・識別子の値を書ける人は、全員がその権限を与えてよい人か**<br>*authoritative_writer・modifiers の configurable_by と source_system を見る。トークンに書く発行者だけでなく、元のデータを書き換えられる人（IdP の管理者・テナントの管理者・本人・呼び出し側・外部の IdP の管理者）も数える*<br>見る欄：`registry:claims#provenance`、`registry:claims#modifiers`、`registry:claims#enforced_at` | どの設計でも |
| `q-freshness-mitigation` | **寿命の間に変わりうる値は、古いまま通っても、要求が許す遅れに収まるか**<br>*volatility と対策（on_revoke・recompute_trigger）、設計書の鮮度の表を見る。要求に遅れの数値が無ければ、それ自体を指摘にする。対策を実際に行うのは誰か*<br>見る欄：`template:00_core#freshness`、`registry:claims#volatility`、`registry:claims#on_revoke`、`registry:claims#recompute_trigger` | どの設計でも |

<a id="unit-hop"></a>

### 経路を読みながら（ホップの 1 行ごと・範囲の図）

| 問い ID | 問い | 出す条件 |
| --- | --- | --- |
| `q-single-aud-resource` | **1 つのアクセストークンの宛先（aud）は 1 つか**<br>*種別とホップの aud を見る。2 つ以上なら、1 つのトークンが両方の経路で通る*<br>見る欄：`registry:token_types#aud`、`registry:hops#aud`、`template:profiles/P4_ai_agent_delegation#tool-scopes`<br>（機械で決まる問い。lint の規則ができるまで） | トークンの交換・作り直しがある・委任がある（代理で動く主体がいる） |
| `q-no-passthrough` | **交換・作り直しを頼める相手と、割り当てる宛先・範囲が、規則として決まっているか**<br>*hops の exchanger と、交換の規則の節（P4 の delegation-policy）を見る。頼んではいけない相手や、広すぎる範囲が通らないか*<br>見る欄：`registry:hops#exchanger`、`template:profiles/P4_ai_agent_delegation#delegation-policy` | トークンの交換・作り直しがある・委任がある（代理で動く主体がいる） |
| `q-step-up-path-coverage` | **追加の認証が要る操作は、どの経路から呼ばれても同じ条件で確かめられるか**<br>*設計書の追加認証の節と hops の validates・custom_claims を見る。直接・代理・交換の後・非同期の経路*<br>見る欄：`template:00_core#step-up`、`registry:hops#custom_claims`、`registry:hops#validates` | 認証の強さ・新しさで判断する |
| `ap-2-7` | **代理の主体が、代理であることを示さない（act の無い）トークンを手に入れられる経路はないか**<br>*act の行の carried_in と、種別の holder を見る。本人のトークンをそのまま使える経路、act の無いトークンを出してよい相手の限り方*<br>見る欄：`registry:questions#q-actor`、`template:profiles/P4_ai_agent_delegation#delegation-mode` | 委任がある（代理で動く主体がいる） |
| `q-tenant-data-match` | **トークンのテナントを、保存されたデータのテナントと比べない経路はないか**<br>*tenant_binding と、データ層の絞り込みの節を見る*<br>見る欄：`template:modules/M_multitenancy#data-layer-filter`、`registry:claims#enforced_at` | マルチテナント |
| `q-authorize-service-and-user` | **呼び出してきた直接の相手（サービス）を、通信の層で確かめているか**<br>*catalog_answers の questions の q-peer と hops の validates を見る。mTLS など。利用者の権限とは別に、その相手を通してよいかを決めているか*<br>見る欄：`template:profiles/P5_internal_propagation#service-to-service`、`registry:questions#q-peer` | トークンの交換・作り直しがある・委任がある（代理で動く主体がいる） |
| `q-db-context-writers` | **DB の「いまの利用者・テナント」を書き換えられるのは、注入する部品だけか**<br>*db_connection のホップと、データ層の節を見る。同じ接続で任意の SQL を流せる経路、文脈を戻せる経路*<br>見る欄：`template:modules/M_data_layer#db-context-setter`、`template:00_core#scope-boundary` | トークンの値を DB の層まで運ぶ |
| `q-agent-short-lived-no-rt` | **代理の主体（エージェント）に、リフレッシュトークンを出していないか**<br>*代理の主体が持つ種別の refresh・max_lifetime と、refresh_token の行の holder を見る*<br>見る欄：`registry:token_types#max_lifetime`、`registry:token_types#refresh`<br>（機械で決まる問い。lint の規則ができるまで） | 委任がある（代理で動く主体がいる） |

<a id="unit-design"></a>

### 設計の全体を読んでから

| 問い ID | 問い | 出す条件 |
| --- | --- | --- |
| `q-outside-catalog` | **図に無い入口や場面は、設計書のどこかで答えられているか**<br>*範囲の図・シーケンス図・catalog_answers の outside_enumeration を見る。挙げる場面：入口を通らない経路（サービス間の直接の呼び出し・メッセージ）、管理用の口、テスト用の口・時計・鍵・利用者、移行期間の旧経路、障害時の再送と手作業。本番で開いているなら、同じ守りが掛かるか、いつ誰が閉じるか*<br>見る欄：`template:00_core#catalog-answers`、`template:00_core#sequence`、`template:00_core#scope-boundary` | どの設計でも |
| `q-object-level-authz` | **他人の ID を指定してデータを取ろうとしたとき、どこで止まるかを言えるか**<br>*enforced_at と、データの持ち主・テナントを照合する節を見る。入口やトークンの値だけに任せていないか*<br>見る欄：`template:modules/M_authz_pdp#object-level`、`template:modules/M_multitenancy#data-layer-filter`、`registry:claims#enforced_at` | どの設計でも |
| `q-approval-from-as` | **承認・同意は、頼む側の申告でなく記録と照合され、その操作とその相手（宛先）に結びついているか**<br>*authorization_details の行の enforced_at と、承認・同意の節を見る。承認していない相手（信頼していないサーバー・別のツール・別の代理の主体）に向けて、同じ承認でトークンを出させたり使わせたりできないか。入力に紛れた指示で宛先を変えられたらどうなるか*<br>見る欄：`template:profiles/P4_ai_agent_delegation#human-approval`、`registry:claims#enforced_at` | 操作ごとの承認がある・委任がある（代理で動く主体がいる） |
| `q-operator-act` | **運用者・管理者の操作を、後から利用者の操作と見分けられるか**<br>*設計書の主体の一覧と、システムの特権の節を見る。運用者が利用者の代わりに操作するとき、どのトークンで動くか*<br>見る欄：`template:00_core#system-privileges`、`registry:questions#q-actor` | どの設計でも |
| `q-revocation-delivery` | **権限を外してから、止めたい操作が止まるまで、最悪で何分か**<br>*種別の revocation・max_lifetime と、ライフサイクルの表を見る。退職・鍵や端末の紛失・外部の IdP や取引先の側で止めた場合も同じか。すぐ止めたい操作は、その場で問い合わせて決めているか。却下した手段の代わりはあるか。「期限が切れれば効く」だけに頼っていないか。寿命の数字は、この分数から導かれているか*<br>見る欄：`registry:token_types#revocation`、`template:00_core#lifecycle`、`template:00_core#lifecycle-db-connection`、`registry:claims#on_revoke` | どの設計でも |
| `q-dependency-outage` | **頼る先が止まったとき、通すのか止めるのかが決まっているか**<br>*種別の unknown_kid・jwks_cache_ttl・introspection_cache_ttl と on_revoke を見る。頼る先：IdP・発行のサービス・鍵の取得先・その場で引く記録（承認など）。その倒し方は、業務が許す停止の時間と合うか*<br>見る欄：`registry:token_types#jwks_cache_ttl`、`registry:token_types#introspection_cache_ttl`、`template:modules/M_idp_keycloak#limits`、`template:00_core#uncertain`、`registry:claims#on_revoke` | どの設計でも |

<a id="optional"></a>

### 時間があれば（優先 2。10 問のうち、設計の性質に当たるもの）

優先 1 と開いた問いを終えて、時間が残ったときに答えます。答えなかった問いは、レポートに書きます。量の目安には数えていません。

| 問い ID | 問い | 出す条件 |
| --- | --- | --- |
| `pa-01` | **このクレームを読んで、どの受け手が何を決めるかを言えるか**<br>*25 問の問 1 の回答と usage を見る。使い道の無い値、表示用の値での認可が無いか*<br>見る欄：`template:claim_request#q01`、`registry:claims#usage`、`registry:claims#answers` | 組織独自のクレームがある |
| `q-derived-value` | **個人情報の値そのものを、届く相手のすべてが必要としているか**<br>*pii_category が「該当なし」でない行の consumers と carried_in を見る。判定の結果や参照の ID で足りないか、読まない受け手に届くトークンに載っていないか*<br>見る欄：`registry:claims#usage`、`registry:claims#description`、`template:modules/M_privacy_minimization#derived-values` | 個人情報を載せる |
| `q-variant-comparison` | **既定から外した選択の理由は、それで開く攻撃と代わりの守りを比べているか**<br>*設計書の 3.（既定から外した点）と issuance_profile の rationale を見る。送信者制約の見送り・寿命の延長など。比べた候補は足りているか*<br>見る欄：`template:00_core#deviations`、`template:00_core#issuance-profile`、`registry:token_types#size` | 送信者制約を見送った |
| `q-idp-diff-absorbed` | **内側のサービスが、特定の IdP の独自の値を直接読んでいないか**<br>*upstream_issuer と、入口の作り直しのホップを見る。IdP ごとの差（利用者のキー・ロールの位置・宛先）を入口で吸収しているか*<br>見る欄：`template:profiles/P5_internal_propagation#edge-conversion`、`registry:claims#upstream_issuer`、`registry:claims#issuers` | 発行者（IdP）が複数ある |
| `q-original-principal` | **内部の呼び出しでも、元の利用者の権限で判断しているか**<br>*交換・作り直しの後のトークンの sub と scope を見る。間に入るサービスの広い権限で、下流に頼んでいないか*<br>見る欄：`registry:questions#q-sub`、`registry:hops#token_type`、`template:profiles/P5_internal_propagation#service-to-service` | トークンの交換・作り直しがある・委任がある（代理で動く主体がいる） |
| `q-step-up-by-rs` | **追加の認証を求めるかどうかを、操作を受ける側が決めているか**<br>*設計書の追加認証の節を見る。クライアントやトークンの値に任せていないか*<br>見る欄：`template:00_core#step-up`、`registry:questions#q-auth-strength` | 認証の強さ・新しさで判断する |
| `q-cross-tenant-identity` | **テナントをまたいで、同じ人だと暗黙に決めていないか**<br>*利用者のキーの行を見る。メールアドレスでの突き合わせなど*<br>見る欄：`template:modules/M_multitenancy#cross-tenant`、`registry:claims#usage` | マルチテナント |
| `q-long-running` | **後で動く処理は、途中で権限が外れたら止まるか**<br>*種別の long_running と、非同期の経路を見る。利用者のトークンを持ち続けていないか*<br>見る欄：`registry:token_types#long_running`、`template:00_core#lifecycle`、`template:profiles/P5_internal_propagation#async-messaging` | 長時間・非同期の処理がある |
| `q-copies-outlive` | **トークンの値の写しは、元のトークンが切れた後に止められるか**<br>*integrity_until と、ライフサイクルの表を見る。開いたままの接続・判断や結果のキャッシュ・分析用の複製を挙げ、いつまで残るかを言う*<br>見る欄：`template:00_core#lifecycle`、`template:00_core#lifecycle-db-connection` | どの設計でも |
| `q-audit-correlation` | **1 つの操作の「誰の権限で・誰が代理で・どの承認で」を、ログから 1 本につなげられるか**<br>*log_policy と、監査の節を見る。経路の途中で値の作り方（ハッシュなど）が変わらないか*<br>見る欄：`template:profiles/P4_ai_agent_delegation#audit-correlation`、`registry:claims#log_policy` | 委任がある（代理で動く主体がいる） |

<a id="on-lint"></a>

## 3. lint の結果から出す問い

lint の warn は、機械が「人が見てほしい」と言っている箇所です。次の規則の warn が出ていたら、その行について右の問いに答えます。
warn に行ごとの理由が書いてあるか（[../CONTRIBUTING.md](../CONTRIBUTING.md) の 2.）も、あわせて見ます。

| lint の規則 | 問い ID | 問い |
| --- | --- | --- |
| `lint:L69` | `q-role-explosion` | **ロールの名前に、テナント・対象・操作の組み合わせを詰めていないか**<br>*value_vocabulary と max_items を見る*<br>見る欄：`registry:claims#value_vocabulary`、`registry:claims#max_items`、`template:modules/M_authz_pdp#model-choice` |
| `lint:L68` | `q-access-context-from-pep` | **「いまどこから来たか」の判断に、トークンの値や偽装できるヘッダーを使っていないか**<br>*IP・端末の値を載せたクレームと enforced_at を見る*<br>見る欄：`template:modules/M_authz_pdp#pep-pdp-inputs`、`registry:claims#data_category` |

<a id="open-prompts"></a>

## 4. 開いた問い（要求と運用から辿る）

設計書の決まった欄を開くだけでは答えられない問いです。要求の文と運用の場面から自分で辿り、辿った範囲と気づいたことを書きます（指摘の出どころは「テンプレート外」）。
**設計ごとに 3 つまで**を出します。性質に合うもの（「先に出す設計」に当たるもの。「読めない」性質では数えない）を先に選び、残りは下の表の順です。選ばれなかったものは「さらに」として、時間があれば辿ります。1 つにつき 2〜4 分が目安です（未計測）。

| ID | 辿ること | 出す条件 | 先に出す設計 |
| --- | --- | --- | --- |
| op-source-change | **権限の元データが変わる出来事を 1 つ選び、受け手の判断が変わるまでを、IdP の手前から辿れるか**<br>*出来事の例：異動でロールが外れる・退職。source_system の欄から、元のデータ（人事の台帳・グループ・ロールの割り当て）を書き換えるのは誰で、どの経路かを辿る。図に無い書き込みの経路、誰も時間を約束していない区間を探す* | どの設計でも | 発行者（IdP）が複数ある・組織独自のクレームがある |
| op-one-time | **1 回だけ使える値が、「確かめる」と「使用済みにする」の間にもう 1 回届いても、2 回通らないか**<br>*承認・認可コード・jti・ワンタイムの番号。並行の 2 件、通信が切れた後の再送、記録先の障害のそれぞれで辿る。正しい 1 回が失われることもないか* | どの設計でも | 操作ごとの承認がある・委任がある（代理で動く主体がいる） |
| op-requirement-words | **要求の言葉に入る人・場合を全部挙げたとき、それぞれを通す・止める値が設計にあるか**<br>*要求の文から言葉を 2〜3 個選ぶ（例：「利用者」「管理者」「承認」「取り消し」）。その言葉に入る人・場合を挙げる（例：正社員・契約社員・派遣・休職中・退職の手続き中）。要求にあるのに設計に無い区分、設計にあるのに要求に無い操作を探す* | どの設計でも | — |
| op-clock | **時刻を比べている箇所で、比べる 2 つの時刻は同じ時計が書いたものか**<br>*期限、発行時刻とログアウト・失効の時刻、台帳の更新時刻。max_clock_skew と、時刻を使う enforced_at を見る。別の発行者・別のサーバーの時計なら、ずれたときに通すのか止めるのか* | どの設計でも | 発行者（IdP）が複数ある・トークンの交換・作り直しがある |
| op-key-custody | **署名の鍵ごとに、誰が持ち、漏れたとき誰が何分で何をするかを言えるか**<br>*種別の key_rotation・signing_key_scope・jwks_cache_ttl を見る。新しく置いた発行者（入口・STS）の鍵と、証明書を出す側の鍵も数える。受け手が古い鍵を使い続ける時間はどれだけか* | どの設計でも | トークンの交換・作り直しがある |
| op-proof-holder | **「鍵の持ち主を確かめる」箇所で、確かめる側が見ている鍵は、そのトークンを実際に持つ者の鍵か**<br>*cnf の行の enforced_at と、種別の holder・sender_constraint を見る。箇所ごとに「トークンを持つ者」と「鍵を持つ者」を並べる。証明書・鍵を更新したとき、束縛したトークンはどうなるか* | 送信者制約を選んだ | （条件に当たれば先に出す） |

これらは、パイロット（#9）で問いの一覧の外から出た Major の指摘を元に作りました。同じ設計で作って同じ設計で確かめた問いなので、別の設計でも効くかは分かっていません（triage-evidence.md の 3.）。
旧経路・テストの経路は `q-outside-catalog` に、同意と宛先の束縛は `q-approval-from-as` にまとめてあります。

<a id="experts"></a>

## 5. 専門家に回す（レビュアーは答えない）

次の問いは、レビュアーに答えを求めません。[escalation.md](escalation.md) の基準の表を上から見て、当たる行を回します。

| 問い ID | 問い | 回す基準 |
| --- | --- | --- |
| `q-pairwise-unguessable` | ペアワイズにした `sub` の作り方（受け手の区分と生成の方式）が、`identifier-sectors` の記入欄の「識別子の性質」の行に書いてあり、その値が識別情報を含まず推測できない方式か | `review:escalation#custom-crypto` |
| `q-idp-capability-verified` | 設計が IdP・製品の機能（RFC 8707 の `resource`・トークン交換・CIBA・フックの呼ばれる契機など）に依存する行のすべてに、その製品の版の公式文書か実測の出どころがあるか | `review:escalation#unverified-idp-behavior` |
| `q-delegation-depth-and-revocation` | 委任の深さの上限（`max_delegation_depth`）と、根元の承認からの一括失効の手段が書いてあるか（深さが 2 以上なら専門家に回したか） | `review:escalation#delegation-depth` |
| `q-refresh-reevaluated` | 「リフレッシュで値が再計算される」を前提にした行で、その IdP の挙動を実測か文書で確かめた記録があるか（外部 IdP の属性の取り込みが初回だけか毎回かが書いてあるか） | `review:escalation#unverified-idp-behavior` |

<a id="machine"></a>

## 6. 機械が確かめること（レビュアーは答えない）

次の問いは、lint の規則が答えを決めます。レビュアーは、設計書の 1. の結果で error が 0 であることと、warn に理由が付いていることだけを見ます。
規則が決めるのは「宣言が矛盾していない」ことまでです（RULES.md）。既存の規則だけが答えを決めるとした問いは、記入例の答えを No に書き換えて、lint が指摘を出すことを 1 問ずつ確かめました（[research/template-design/triage-audit.md](../../research/template-design/triage-audit.md)）。

| lint の規則 | 確かめる問い |
| --- | --- |
| `lint:L1a` | `dc-02`・`ap-2-3` |
| `lint:L1b` | `dc-03`・`pa-04`・`ap-2-4` |
| `lint:L3` | `dc-09`・`pa-12`・`ap-1-6` |
| `lint:L4` | `dc-10`・`dc-12`・`pa-15`・`q-single-issuer`・`cf-01` |
| `lint:L5` | `dc-01`・`pa-02`・`ap-2-2`・`cf-01` |
| `lint:L6` | `q-payload-readable` |
| `lint:L7` | `dc-07`・`dc-12`・`pa-09`・`q-hook-failure`・`cf-02`・`q-txn-required-claims`・`q-required-rejected`・`q-consumer-expression` |
| `lint:L8` | `pa-17`・`cf-08`・`ap-2-5` |
| `lint:L9` | `ap-2-9`・`q-internal-delegation-token`・`ap-1-4` |
| `lint:L11` | `q-txn-scope-fixed`・`ap-1-3`・`q-consumer-expression` |
| `lint:L12` | `q-agent-delegation-claims` |
| `lint:L15` | `q-session-rt-bounds`・`q-rt-policy-by-client` |
| `lint:L16` | `pa-14`・`q-minimal-per-recipient`・`cf-05`・`q-hop-narrowing`・`q-hop-lifetime`・`q-txn-scope-fixed`・`q-claim-earliest-hop` |
| `lint:L17` | `ap-2-9`・`q-internal-delegation-token`・`ap-1-1`・`q-key-rotation` |
| `lint:L18` | `q-deprecated-deadline` |
| `lint:L23` | `q-session-rt-bounds` |
| `lint:L25` | `ap-1-5` |
| `lint:L27` | `ap-1-3`・`ap-1-8`・`q-typ-distinguishes` |
| `lint:L31` | `dc-10`・`pa-11`・`q-writer-distinguished`・`cd-04` |
| `lint:L37` | `dc-07`・`pa-09`・`q-consumer-expression` |
| `lint:L43` | `cf-06` |
| `lint:L62` | `q-rt-policy-by-client` |
| `lint:L65` | `q-payload-readable`・`q-confidential-reaches-reader` |
| `lint:L66` | `q-confidential-reaches-reader`・`q-nested-jwt-both-layers` |
| `lint:L67` | `ap-2-5`・`q-unwrapped-value-authz` |
| `lint:L69` | `ap-2-1` |
| `lint:L70` | `q-no-secret-or-raw-pii` |
| `lint:L71` | `q-no-secret-or-raw-pii` |
| `lint:L72` | `pa-gate` |
| `lint:R1` | `dc-11`・`dc-gate`・`pa-22`・`ap-2-9`・`q-internal-delegation-token`・`q-typ-distinguishes` |
| `lint:R3b` | `q-hook-failure` |
| `lint:R8` | `dc-11`・`pa-13`・`ap-2-1`・`q-size-limit` |

規則がまだ無い問い・規則が一部しか見ない問い（37 問）は、規則ができるまで、書き手の提出前のチェックリストに置いています。規則の案は triage.yaml の `proposed_rules` と、その一覧の issue（#68）にあります。

| 問い ID | いまの規則 | 規則の案 |
| --- | --- | --- |
| `dc-02` | `lint:L1a` | N1 |
| `dc-03` | `lint:L1b` | `lint:L34`（未実装） |
| `dc-04` | 無い | N1 |
| `dc-06` | 無い | `lint:L36`（未実装） |
| `dc-07` | `lint:L37`・`lint:L7` | N6 |
| `dc-08` | 無い | N1 |
| `pa-04` | `lint:L1b` | `lint:L34`（未実装） |
| `pa-07` | 無い | `lint:L36`（未実装） |
| `pa-08` | 無い | `lint:L24`（未実装）・N5 |
| `pa-09` | `lint:L37`・`lint:L7` | N6 |
| `pa-14` | `lint:L16` | N3 |
| `pa-22` | `lint:R1` | N7 |
| `pa-gate` | `lint:L72` | N11 |
| `q-auth-context-semantics` | 無い | N16 |
| `q-pairwise-external` | 無い | N10 |
| `ap-2-3` | `lint:L1a` | `lint:L24`（未実装） |
| `q-no-secret-or-raw-pii` | `lint:L70`・`lint:L71` | `lint:L51`（未実装） |
| `q-hook-adds-raw-pii` | 無い | N14 |
| `q-minimal-per-recipient` | `lint:L16` | N4 |
| `cf-03` | 無い | `lint:L41`（未実装） |
| `cf-04` | 無い | `lint:L41`（未実装） |
| `cf-07` | 無い | `lint:L46`（未実装） |
| `cf-10` | 無い | `lint:L45`（未実装） |
| `ap-2-6` | 無い | `lint:L41`（未実装） |
| `q-unverified-claim-extraction` | 無い | `lint:L46`（未実装） |
| `q-txn-required-claims` | `lint:L7` | N8 |
| `ap-2-9` | `lint:L17`・`lint:L9`・`lint:R1` | N18 |
| `q-internal-delegation-token` | `lint:L9`・`lint:L17`・`lint:R1` | N18 |
| `q-token-not-in-url` | 無い | `lint:L54`（未実装） |
| `ap-1-2` | 無い | `lint:L46`（未実装） |
| `q-typ-distinguishes` | `lint:L27`・`lint:R1` | N9 |
| `q-required-rejected` | `lint:L7` | N6 |
| `q-unwrapped-value-authz` | `lint:L67` | N15 |
| `cd-05` | 無い | `lint:L48`（未実装） |
| `cd-08` | 無い | `lint:L49`（未実装） |
| `q-deprecated-deadline` | `lint:L18` | N17 |
| `ap-2-8` | 無い | `lint:L45`（未実装） |

<a id="more"></a>

## 7. 詳しく見る（優先 3。出さない 18 問）

問いに答える中で気になったときに見ます。ほかの問いにまとめた問いと、手順の別の段で確かめる問いも、ここにあります。

| 問い ID | 問い | 当たる設計 |
| --- | --- | --- |
| `pa-19` | このクレームを知らない受け手が無視しても安全か | 組織独自のクレームがある |
| `q-registered-synonym` | 同じ意味の値が、別の名前で 2 行に分かれていないか | 組織独自のクレームがある |
| `q-reuse-standard-structure` | この独自クレームの用途は、既にある構造で表せないか | 組織独自のクレームがある |
| `q-scope-semantics` | scope を、利用者の全権限でなく「クライアントに委ねた範囲」として扱っているか | どの設計でも |
| `q-role-explosion` | ロールの名前に、テナント・対象・操作の組み合わせを詰めていないか | どの設計でも |
| `q-rar-per-audience` | 承認の内容（authorization_details）を、宛先ごとに、その宛先に要る分だけに絞っているか | 操作ごとの承認がある |
| `q-gateway-bypass-path` | 入口を通らずにサービスへ届く経路でも、同じ検証をしているか（`q-outside-catalog` にまとめた） | どの設計でも |
| `q-validity-not-authz` | 「トークンが有効」というだけで通している操作はないか | どの設計でも |
| `q-scope-and-role` | 受け手は、scope と role の両方を確かめているか | どの設計でも |
| `q-access-context-from-pep` | 「いまどこから来たか」の判断に、トークンの値や偽装できるヘッダーを使っていないか | どの設計でも |
| `q-break-glass` | 緊急時の特権に、承認と短い期限があるか | どの設計でも |
| `q-lifetime-rationale` | トークンの寿命の数字は、「権限を外してから何分で効かせたいか」から導かれているか（`q-revocation-delivery` にまとめた） | どの設計でも |
| `q-external-user-deprovision` | 外部の IdP・取引先の側で利用者を止めたとき、こちらが出したトークンとセッションも止まるか（`q-revocation-delivery` にまとめた） | 発行者（IdP）が複数ある |
| `q-relies-on-at-expiry` | 剥奪とキャッシュの寿命を、「期限が切れれば効く」だけに頼らずに決めているか（`q-revocation-delivery` にまとめた） | どの設計でも |
| `q-system-actor-no-fake-sub` | サービス自身の権限で動かす処理は、利用者の文脈が要らない処理だけか | どの設計でも |
| `q-scope-elevation-logged` | 代理の主体の範囲は最小限から始まり、広げたことが記録に残るか | 委任がある（代理で動く主体がいる） |
| `q-lint-workaround` | 検査（lint）を通すために、設計の宣言の側を曲げた跡はないか | どの設計でも |
| `q-evidence-attribution` | 数値・製品の挙動に付けた根拠は、引いた先が本当にそう述べているか（手順の段 4 で確かめる） | どの設計でも |

<a id="not-here"></a>

## 8. ここに無い問いの行き先と、この文書について

観点書（[perspectives.md](perspectives.md)）の 168 問を 1 問ずつ振り分け（[triage.yaml](triage.yaml)）、人が判断する 47 問を残しました。

| 区分 | 数 | 誰が確かめるか |
| --- | --- | --- |
| A 機械 | 81 | claim_lint（[RULES.md](../../tools/claim_lint/RULES.md)）。レビュアーは、設計書の 1. に貼られた結果で error が 0 であることだけを見る（手順の段 0）。うち 19 問は規則がまだ無く、18 問は規則が一部しか見ない。この分は、規則ができるまで書き手の自己点検にも置く（6.） |
| B 書き手の自己点検 | 36 | 書き手が、提出前のチェックリスト（PR のテンプレート `.github/PULL_REQUEST_TEMPLATE/design_doc.md`）で確かめる。レビュアーは、印の無い行を読み、25 問の回答の行と、No なら Blocker の行から 2 件を抜き取って欄を開く（手順の段 0） |
| C 人の判断 | 47 | レビュアー。優先 1 の 19 問（既定）、優先 2 の 10 問（時間があれば）、優先 3 の 18 問（出さない）。優先 1 のうち 4 問は、機械で決まるが規則がまだ無いので、規則ができるまでレビュアーが答える |
| D 専門家 | 4 | レビュアーは答えず、[escalation.md](escalation.md) の基準に当たる行を回す（5.） |

- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施
- 区分・優先・出す条件・量と時間の目安は、どれも筆者の提案と LLM の見積もりです（追跡 #56）。人が測るのは #20 です。根拠にしたパイロット（#9）の数は [research/template-design/triage-evidence.md](../../research/template-design/triage-evidence.md) にあります
- 「漏れゼロ」は約束しません。パイロットでは、人の判断が要る Major の指摘の半分が、問いの一覧の外から出ました。そのため、問いのほかに開いた問い（4.）を置いています
- エディターのレビューモード（`docs/claims/`）の「観点のチェックリスト」は、開いている設計書から同じ性質を読み、既定でこの一覧を出します

```
python tools/review_triage.py --design <設計書のディレクトリ> [--seed <種>]   # その設計の 1 枚（性質の表、問い、開いた問い）
python tools/review_triage.py --load <設計書のディレクトリ>…                  # 一覧の大きさ（問い・文・字数）
```

根拠：筆者の提案：問いの区分・優先・出す条件・1 回の量の目安（追跡 #56）、templates/CONTRIBUTING.md の 2.・3.、research/template-design/pilot.md の 9.
