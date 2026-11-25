<!-- template_version: 0.4.0 -->
# 人に渡す短い一覧（レビュアーが答える問い）

<!-- このファイルは python tools/review_triage.py --write が templates/review/triage.yaml から作る。手で直さない -->

設計書の PR をレビューする人が答える問いは、ここにあるものだけです。観点書（[perspectives.md](perspectives.md)）の 168 問を 1 問ずつ振り分け（[triage.yaml](triage.yaml)）、人でなければ判断できない 43 問だけを残しました。そこから、設計の性質に当たるものを、優先の順に出します。

- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施
- **1 回の量の目安**：15〜25 問、30〜60 分。筆者の提案です（追跡 #56）。人のレビュアーで確かめるのは #20 で、それまでは目安にとどめてください。条件に当たる問いが 25 を超えたら、優先 1 を先に答え、優先 2 は時間の中で上から答える。答えなかった問いはレポートに書く
- 区分・優先・出す条件は、どれも筆者の提案です（追跡 #56）。根拠にしたパイロット（#9）の数は [research/template-design/triage-evidence.md](../../research/template-design/triage-evidence.md) にあります
- 「漏れゼロ」は約束しません。パイロットでは、人の判断が要る Major の指摘の半分が、問いの一覧の外から出ました。そのため、問いのほかに「開いた問い」（4.）を置いています

<a id="not-here"></a>

## 0. ここに無い問いの行き先

| 区分 | 数 | 誰が確かめるか |
| --- | --- | --- |
| A 機械 | 86 | claim_lint（[RULES.md](../../tools/claim_lint/RULES.md)）。レビュアーは、設計書の 1. に貼られた結果で error が 0 であることだけを見る（手順の段 0）。うち 20 問は規則がまだ無く、15 問は規則が一部しか見ない。この分は、規則ができるまで書き手の自己点検にも置く（6.） |
| B 書き手の自己点検 | 35 | 書き手が、提出前のチェックリスト（PR のテンプレート `.github/PULL_REQUEST_TEMPLATE/design_doc.md`）で確かめる。レビュアーは、チェックリストで印の無い行（書き手が「満たさない」「当てはまらない」とした行）だけを読む |
| C 人の判断 | 43 | レビュアー。この文書（既定で出すのは優先 1・2 の 31 問のうち、設計の性質に当たるもの） |
| D 専門家 | 4 | レビュアーは答えず、[escalation.md](escalation.md) の基準に当たる行を回す（5.） |

<a id="traits"></a>

## 1. 先に、設計の性質を読む

問いは、設計の性質に当たるものだけを出します。性質は、台帳・目録・ホップ・カタログへの回答から機械で読めます。

```
python tools/review_triage.py --design <設計書のディレクトリ>   # 性質と、出す問いの一覧
```

エディターのレビューモード（`docs/claims/`）の「観点のチェックリスト」は、開いている設計書から同じ性質を読み、既定でこの一覧を出します。

| 性質 | 読み方 | 出る問い（優先 1・2） | 出る開いた問い |
| --- | --- | --- | --- |
| どの設計でも | 条件なし | 12 | 6 |
| 組織独自のクレームがある | 採用の行に、名前空間つきの行、または登録名でない（registered_ref が無い）認可・識別子の行がある | 1 | 0 |
| 個人情報を載せる | 採用の行の pii_category に「該当なし」以外がある | 1 | 0 |
| 発行者（IdP）が複数ある | 採用の種別の issuers の iss が 2 種類以上、または upstream_issuer のある採用の行がある | 3 | 0 |
| トークンの交換・作り直しがある | ホップに kind が exchange・reissue の行がある | 3 | 0 |
| 委任がある（代理で動く主体がいる） | 採用の行に act・may_act がある、または採用の種別に max_delegation_depth がある | 6 | 1 |
| 操作ごとの承認がある | 採用の行かホップに authorization_details がある | 1 | 1 |
| マルチテナント | catalog_answers の lite_criteria.multitenant が Yes。この回答が無いときだけ、採用の種別の tenant_binding の有無で読む | 2 | 0 |
| トークンの値を DB の層まで運ぶ | ホップに kind が db_connection の行がある | 1 | 0 |
| 認証の強さ・新しさで判断する | 採用の行に acr・amr・auth_time がある | 3 | 0 |
| 送信者制約を選んだ | 採用の種別に sender_constraint が dpop・mtls の行がある | 0 | 1 |
| 送信者制約を見送った | 採用のアクセストークン・内部トークンに、sender_constraint が none か未記入の行がある | 1 | 0 |
| 長時間・非同期の処理がある | 採用の種別に long_running がある、またはホップに kind が broker_connection の行がある | 1 | 0 |

条件を 2 つ以上持つ問いは、どれか 1 つに当たれば出ます（上の表では、それぞれの行で数えています）。

<a id="questions"></a>

## 2. 問い（読む単位ごと）

どの問いも、Yes／No では足りません。**自分の言葉で答えを 1 行書けるか**を確かめ、書けない・設計書から読み取れないなら指摘にします。問い ID は観点書の ID で、No のときの重大度の目安・根拠は観点書にあります。「見る欄」は、答えを探すために開く設計書の節（`template:…`）と台帳の列（`registry:…`）です。

<a id="unit-row"></a>

### クレームの行を読みながら（台帳の 1 行ごと）

| 優先 | 問い ID | 問い | 見る欄 | 出す条件 |
| --- | --- | --- | --- | --- |
| 1 | `q-value-vocabulary` | ロール・グループの値は、どの発行者（IdP）の誰が付けた値か。別の IdP の同じ文字列（admin など）を、同じ意味として通していないか。照合に使う値は、変わる名前でなく変わらない ID か | `registry:claims#value_vocabulary`、`registry:claims#upstream_issuer` | 発行者（IdP）が複数ある |
| 1 | `ap-1-7` | 権限・識別子の値ごとに、その値を書ける人を全部挙げる（IdP の管理者・テナントの管理者・本人・呼び出し側・外部の IdP の管理者）。その全員が、その権限を与えてよい人か | `registry:claims#provenance`、`registry:claims#modifiers`、`registry:claims#enforced_at` | どの設計でも |
| 1 | `q-freshness-mitigation` | トークンの寿命の間に変わりうる値（ロール・所属・状態）ごとに、古い値のまま通ると何が起きるか。書いてある対策で、要求が許す遅れに収まるか。その対策を実際に行うのは誰か | `template:00_core#freshness`、`registry:claims#volatility`、`registry:claims#on_revoke`、`registry:claims#recompute_trigger` | どの設計でも |
| 2 | `pa-01` | このクレームを読んで、どの受け手が何を決めるのか（許す・断る・絞る）を、受け手の名前つきで言えるか。使い道の無い値や、表示用の値で認可していないか | `template:claim_request#q01`、`registry:claims#usage`、`registry:claims#answers` | 組織独自のクレームがある |
| 2 | `q-auth-context-semantics` | 認証の新しさを auth_time、強さを acr で判断しているか。iat・amr・sid を、その代わりに使っていないか | `registry:claims#not_meaning`、`registry:claims#usage`、`registry:questions#q-auth-strength`、`template:00_core#step-up` | 認証の強さ・新しさで判断する |
| 2 | `q-derived-value` | この個人情報は、受け手が値そのものを要るのか。判定の結果（18 歳以上か）や参照の ID で足りないか。読まない受け手にも届くトークンに載っていないか | `registry:claims#usage`、`registry:claims#description`、`template:modules/M_privacy_minimization#derived-values` | 個人情報を載せる |

<a id="unit-hop"></a>

### 経路を読みながら（ホップの 1 行ごと・範囲の図）

| 優先 | 問い ID | 問い | 見る欄 | 出す条件 |
| --- | --- | --- | --- | --- |
| 1 | `q-no-passthrough` | 交換・作り直しごとに、誰が交換を頼めるか・どの宛先とどの範囲を割り当てるかの規則があるか。その規則で、頼んではいけない相手や、広すぎる範囲が通らないか | `registry:hops#exchanger`、`template:profiles/P4_ai_agent_delegation#delegation-policy` | トークンの交換・作り直しがある・委任がある（代理で動く主体がいる） |
| 1 | `q-gateway-bypass-path` | 入口を通らずにサービスへ届く経路（サービス間の直接の呼び出し・管理用の口・メッセージ）を、図から挙げられるか。その経路でも、同じ検証をしているか | `template:00_core#scope-boundary`、`registry:hops#validates`、`template:00_core#sequence` | どの設計でも |
| 1 | `ap-2-7` | 代理で動く主体（エージェントなど）が、本人のトークンをそのまま使える経路はないか。代理であることを示さない（act の無い）トークンを出してよい相手は限られているか | `registry:questions#q-actor`、`template:profiles/P4_ai_agent_delegation#delegation-mode` | 委任がある（代理で動く主体がいる） |
| 1 | `q-tenant-data-match` | トークンのテナントを、保存されたデータのテナントと、どこで比べているか。比べない経路はないか | `template:modules/M_multitenancy#data-layer-filter`、`registry:claims#enforced_at` | マルチテナント |
| 1 | `q-authorize-service-and-user` | 呼び出してきた直接の相手（サービス）が誰かを、通信の層（mTLS など）で確かめているか。利用者の権限とは別に、その相手を通してよいかを決めているか | `template:profiles/P5_internal_propagation#service-to-service`、`registry:questions#q-peer` | トークンの交換・作り直しがある・委任がある（代理で動く主体がいる） |
| 1 | `q-db-context-writers` | DB の「いまの利用者・テナント」を書き換えられるのは誰か。注入する部品のほかに、同じ接続で任意の SQL を流せる経路や、文脈を戻せる経路はないか | `template:modules/M_data_layer#db-context-setter`、`template:00_core#scope-boundary` | トークンの値を DB の層まで運ぶ |
| 2 | `q-step-up-path-coverage` | 追加の認証が要る操作は、どの経路から呼ばれても（直接・代理・交換の後・非同期）、同じ条件で確かめられるか | `template:00_core#step-up`、`registry:hops#custom_claims`、`registry:hops#validates` | 認証の強さ・新しさで判断する |
| 2 | `q-idp-diff-absorbed` | IdP ごとの差（利用者のキー・ロールの位置・宛先）は、入口で吸収しているか。内側のサービスが、特定の IdP の独自の値を直接読んでいないか | `template:profiles/P5_internal_propagation#edge-conversion`、`registry:claims#upstream_issuer`、`registry:claims#issuers` | 発行者（IdP）が複数ある |
| 2 | `q-original-principal` | 内部の呼び出しでも、元の利用者の権限で判断しているか。間に入るサービスの広い権限で、下流に頼んでいないか | `registry:questions#q-sub`、`registry:hops#token_type`、`template:profiles/P5_internal_propagation#service-to-service` | トークンの交換・作り直しがある・委任がある（代理で動く主体がいる） |
| 2 | `q-audit-correlation` | 1 つの操作について、「誰の権限で・誰が代理で・どの承認で」を、ログから後で 1 本につなげられるか | `template:profiles/P4_ai_agent_delegation#audit-correlation`、`registry:claims#log_policy` | 委任がある（代理で動く主体がいる） |

<a id="unit-design"></a>

### 設計の全体を読んでから

| 優先 | 問い ID | 問い | 見る欄 | 出す条件 |
| --- | --- | --- | --- | --- |
| 1 | `q-outside-catalog` | 図と経路から思いつく発行・利用の場面（管理画面からの発行・障害時の再送・テストの経路・移行期間の旧経路）は、設計書のどこかで答えられているか | `template:00_core#catalog-answers`、`template:00_core#sequence`、`template:00_core#scope-boundary` | どの設計でも |
| 1 | `q-object-level-authz` | 利用者が ID を指定してデータを取る処理を 1 つ選ぶ。他人の ID を指定したとき、どこで・何と何を比べて止めるか。入口やトークンの値だけに任せていないか | `template:modules/M_authz_pdp#object-level`、`template:modules/M_multitenancy#data-layer-filter`、`registry:claims#enforced_at` | どの設計でも |
| 1 | `q-operator-act` | 運用者・管理者が利用者の代わりに操作するとき、どのトークンで動くか。後から、運用者の操作と利用者の操作を見分けられるか | `template:00_core#system-privileges`、`registry:questions#q-actor` | どの設計でも |
| 1 | `q-revocation-delivery` | 権限を外す・退職させる・端末を失くす、のそれぞれで、止めたい操作が実際に止まるまで最悪で何分か。すぐ止めたい操作は、その場で問い合わせて決めているか。却下した手段の代わりはあるか | `registry:token_types#revocation`、`template:00_core#lifecycle`、`template:00_core#lifecycle-db-connection`、`registry:claims#on_revoke` | どの設計でも |
| 1 | `q-external-user-deprovision` | 外部の IdP・取引先の側で利用者を止めたとき、こちらが出したトークンとセッションは、どの経路で・何分で止まるか | `template:00_core#lifecycle`、`registry:claims#upstream_issuer`、`registry:claims#volatility`、`template:modules/M_idp_keycloak#broker-mapping` | 発行者（IdP）が複数ある |
| 1 | `q-dependency-outage` | IdP・発行のサービス・鍵の取得先・その場で引く台帳（承認の記録など）が止まったとき、通すのか止めるのか。その倒し方は、業務の要求（止まってよい時間）と合うか | `registry:token_types#jwks_cache_ttl`、`registry:token_types#introspection_cache_ttl`、`template:modules/M_idp_keycloak#limits`、`template:00_core#uncertain`、`registry:claims#on_revoke` | どの設計でも |
| 2 | `q-variant-comparison` | 既定から外した選択（送信者制約を見送る・寿命を延ばすなど）の理由は、それで開く攻撃と、代わりの守りを比べているか。比べた候補は足りているか | `template:00_core#deviations`、`template:00_core#issuance-profile`、`registry:token_types#size` | 送信者制約を見送った |
| 2 | `q-step-up-by-rs` | 追加の認証を求めるかどうかを、操作を受ける側が決めているか（クライアントやトークンの値に任せていないか） | `template:00_core#step-up`、`registry:questions#q-auth-strength` | 認証の強さ・新しさで判断する |
| 2 | `q-approval-from-as` | 機微な操作の承認があったかどうかを、頼む側（エージェント・クライアント）の申告でなく、本人に確かめた記録と照合しているか。承認は、その操作・その相手に結びついているか | `template:profiles/P4_ai_agent_delegation#human-approval`、`registry:claims#enforced_at` | 操作ごとの承認がある・委任がある（代理で動く主体がいる） |
| 2 | `q-cross-tenant-identity` | テナントをまたいで、同じ人だと暗黙に決めていないか（メールアドレスでの突き合わせなど） | `template:modules/M_multitenancy#cross-tenant`、`registry:claims#usage` | マルチテナント |
| 2 | `q-lifetime-rationale` | トークンの寿命の数字は、「権限を外してから何分で効かせたいか」から導かれているか。短くする代償（リフレッシュの負荷・IdP が止まったときの影響）と比べているか | `template:00_core#lifetime-policy`、`registry:token_types#lifetime_refs`、`registry:token_types#lifetime_exception` | どの設計でも |
| 2 | `q-long-running` | 長い処理・後で動く処理は、利用者のトークンを持ち続けていないか。途中で権限が外れたら、その処理は止まるか | `registry:token_types#long_running`、`template:00_core#lifecycle`、`template:profiles/P5_internal_propagation#async-messaging` | 長時間・非同期の処理がある |
| 2 | `q-copies-outlive` | トークンの値の写し（開いたままの接続・判断や結果のキャッシュ・分析用の複製）を挙げられるか。それぞれ、元のトークンが切れた後にいつまで残り、どう止めるか | `template:00_core#lifecycle`、`template:00_core#lifecycle-db-connection` | どの設計でも |
| 2 | `q-lint-workaround` | 検査（lint）を通すために、設計の宣言の側を曲げた跡はないか（上流を外す・行にしない・名前を変える） | `template:00_core#ci-results`、`template:00_core#deviations`、`registry:hops#upstream` | どの設計でも |
| 2 | `q-evidence-attribution` | 数値・製品の挙動に根拠を付けた行から 3 件を選び、引いた先が本当にそう述べているか。別の種類のクライアント・別の製品の根拠を引いていないか | `registry:claims#refs`、`registry:token_types#refs`、`template:00_core#uncertain` | どの設計でも |

<a id="on-lint"></a>

## 3. lint の結果から出す問い

lint の warn は、機械が「人が見てほしい」と言っている箇所です。次の規則の warn が出ていたら、その行について右の問いに答えます。
warn に行ごとの理由が書いてあるか（[../CONTRIBUTING.md](../CONTRIBUTING.md) の 2.）も、あわせて見ます。

| lint の規則 | 問い ID | 問い |
| --- | --- | --- |
| `lint:L69` | `q-role-explosion` | ロールの名前に、テナント・対象・操作の組み合わせを詰めていないか |
| `lint:L68` | `q-access-context-from-pep` | 「いまどこから来たか」（IP・端末）の判断に、トークンの値や偽装できるヘッダーを使っていないか |

<a id="open-prompts"></a>

## 4. 開いた問い（要求と運用から辿る）

問いの一覧の内側だけを見ていると、見つからないものがあります。次の問いは Yes／No で答えず、要求の文と運用の場面から自分で辿って、気づいたことを指摘にします（出どころは「テンプレート外」か「カタログ外の質問」）。
1 つにつき 2〜3 分、合わせて 15 分ほどを、2. の問いとは別に取ります（筆者の提案。追跡 #56）。

| ID | 辿ること | 出す条件 |
| --- | --- | --- |
| op-requirement-words | 要求の言葉を 1 つずつ取り出し（例：「社員」「管理者」「承認」）、その言葉に入る人・場合を全部挙げる（例：正社員・契約社員・派遣・休職中・退職の手続き中）。それぞれについて、設計のどの値が、その人を通す・止めるを決めているかを辿る。要求にあるのに設計に無い区分、設計にあるのに要求に無い操作はないか | どの設計でも |
| op-source-change | 権限の元になるデータ（人事の台帳・グループ・ロールの割り当て）が変わる出来事を 1 つ選ぶ（例：異動でロールが外れる・退職）。元のデータを書き換えるのは誰で、どの経路か。変わってから、トークンの値と受け手の判断が変わるまでを、IdP の手前から順に辿る。途中に、図に無い書き込みの経路や、誰も時間を約束していない区間はないか | どの設計でも |
| op-clock | 時刻を比べている箇所を全部挙げる（期限・発行時刻とログアウトや失効の時刻・台帳の更新時刻）。比べる 2 つの時刻は、同じ時計が書いたものか。別の発行者・別のサーバーの時計なら、ずれたときにどちらへ倒れるか（通すのか、止めるのか） | どの設計でも |
| op-key-custody | トークンに署名する鍵ごとに、誰が持ち、どこに置き、誰が触れるかを言えるか。その鍵が漏れたと分かったとき、誰が・何分で・何をするか（鍵の差し替え・出したトークンの扱い）。新しく置いた発行者（入口・STS）の鍵も数えたか | どの設計でも |
| op-one-time | 1 回だけ使えるはずの値（承認・認可コード・jti・ワンタイムの番号）ごとに、「確かめる」と「使用済みにする」の間に同じ値がもう 1 回届いたらどうなるかを辿る。並行の 2 件・通信が切れた後の再送・記録先の障害のそれぞれで、2 回通ることも、正しい 1 回が失われることもないか | どの設計でも |
| op-consent-binding | 本人が承認・同意した内容（誰に・何を・どの相手に向けて）と、その結果のトークンで実際にできることを並べる。承認していない相手（信頼していないサーバー・別のツール）に向けて、同じ承認でトークンを出させたり使わせたりできないか。入力に紛れた指示（プロンプトインジェクション）で宛先を変えられたらどうなるか | 委任がある（代理で動く主体がいる）・操作ごとの承認がある |
| op-proof-holder | 「鍵の持ち主であることを確かめる」（cnf・DPoP・mTLS）と書いた箇所ごとに、そのトークンを実際に持つのは誰で、鍵を持つのは誰かを辿る。確かめる側が見ている鍵は、トークンを持つ者の鍵か。証明書・鍵を更新したとき、束縛したトークンはどうなるか | 送信者制約を選んだ |
| op-old-and-test-paths | 図に無い入口を探す。移行期間の旧経路（古い入口・古いトークンの形）、テスト用の口・時計・鍵・利用者、管理用の口、障害時の手作業の経路。それぞれ、本番で開いているか、開いているなら同じ守りが掛かるか、いつ誰が閉じるか | どの設計でも |

これらは、パイロット（#9）で問いの一覧の外から出た Major の指摘を元に作りました。同じ設計で作って同じ設計で確かめた問いなので、別の設計でも効くかは分かっていません（triage-evidence.md の 3.）。

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

| lint の規則 | 確かめる問い |
| --- | --- |
| `lint:L1a` | `dc-02`・`ap-2-3` |
| `lint:L1b` | `dc-03`・`pa-04`・`ap-2-4` |
| `lint:L3` | `dc-09`・`pa-12`・`q-identifier-choice`・`ap-1-6` |
| `lint:L4` | `dc-10`・`dc-12`・`pa-15`・`q-single-issuer`・`cf-01` |
| `lint:L5` | `dc-01`・`pa-02`・`ap-2-2`・`cf-01` |
| `lint:L6` | `pa-20`・`q-payload-readable` |
| `lint:L7` | `dc-07`・`dc-12`・`pa-09`・`q-hook-failure`・`cf-02`・`q-txn-required-claims`・`q-required-rejected`・`q-consumer-expression` |
| `lint:L8` | `pa-17`・`cf-08`・`ap-2-5` |
| `lint:L9` | `ap-2-9`・`q-internal-delegation-token`・`ap-1-4` |
| `lint:L11` | `q-txn-scope-fixed`・`q-consumer-expression` |
| `lint:L12` | `q-agent-delegation-claims` |
| `lint:L15` | `q-session-rt-bounds`・`q-rt-policy-by-client` |
| `lint:L16` | `pa-14`・`q-minimal-per-recipient`・`cf-05`・`q-hop-narrowing`・`q-hop-lifetime`・`q-claim-earliest-hop` |
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
| `lint:L70` | `pa-20`・`q-no-secret-or-raw-pii`・`q-hook-adds-raw-pii` |
| `lint:L71` | `q-no-secret-or-raw-pii` |
| `lint:L72` | `pa-gate`・`pa-trace` |
| `lint:R1` | `dc-11`・`dc-gate`・`pa-22`・`ap-2-9`・`q-internal-delegation-token`・`q-typ-distinguishes` |
| `lint:R3b` | `q-hook-failure` |
| `lint:R8` | `dc-11`・`pa-13`・`ap-2-1`・`q-size-limit` |

規則がまだ無い問い・規則が一部しか見ない問い（35 問）は、規則ができるまで、書き手の提出前のチェックリストに置いています。規則の案は triage.yaml の `proposed_rules` と、その一覧の issue（#68）にあります。

| 問い ID | いまの規則 | 規則の案 |
| --- | --- | --- |
| `dc-02` | `lint:L1a` | N1 |
| `dc-03` | `lint:L1b` | `lint:L34`（未実装） |
| `dc-04` | 無い | N1 |
| `dc-05` | 無い | `lint:L24`（未実装）・N5 |
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
| `q-identifier-choice` | `lint:L3` | `lint:L28`（未実装）・N2 |
| `q-pairwise-external` | 無い | N10 |
| `ap-2-3` | `lint:L1a` | `lint:L24`（未実装） |
| `q-no-secret-or-raw-pii` | `lint:L70`・`lint:L71` | `lint:L51`（未実装） |
| `q-minimal-per-recipient` | `lint:L16` | N4 |
| `cf-03` | 無い | `lint:L41`（未実装） |
| `cf-04` | 無い | `lint:L41`（未実装） |
| `cf-07` | 無い | `lint:L46`（未実装） |
| `cf-10` | 無い | `lint:L45`（未実装） |
| `q-single-aud-resource` | 無い | `lint:L56`（未実装） |
| `ap-2-6` | 無い | `lint:L41`（未実装） |
| `q-unverified-claim-extraction` | 無い | `lint:L46`（未実装） |
| `q-txn-required-claims` | `lint:L7` | N8 |
| `q-token-not-in-url` | 無い | `lint:L54`（未実装） |
| `ap-1-2` | 無い | `lint:L46`（未実装） |
| `q-typ-distinguishes` | `lint:L27`・`lint:R1` | N9 |
| `q-required-rejected` | `lint:L7` | N6 |
| `cd-05` | 無い | `lint:L48`（未実装） |
| `cd-08` | 無い | `lint:L49`（未実装） |
| `q-agent-short-lived-no-rt` | 無い | `lint:L58`（未実装） |
| `ap-2-8` | 無い | `lint:L45`（未実装） |

<a id="more"></a>

## 7. 詳しく見る（優先 3。既定では出さない 12 問）

時間が残ったとき、または 2. の問いに答える中で気になったときに見ます。

| 問い ID | 問い | 当たる設計 |
| --- | --- | --- |
| `pa-19` | このクレームを知らない受け手が無視しても安全か。制限を表す値なら、読まない受け手で制限が効かなくならないか | 組織独自のクレームがある |
| `q-registered-synonym` | 同じ意味の値が、別の名前で 2 行に分かれていないか（登録名・既存の行と意味が重なる独自クレーム） | 組織独自のクレームがある |
| `q-reuse-standard-structure` | この独自クレームの用途は、既にある構造（cnf・txn・verified_claims など。判断の木の対応表）で表せないか | 組織独自のクレームがある |
| `q-scope-semantics` | scope を「クライアントに委ねた範囲」として扱い、利用者の全権限と読んでいないか | どの設計でも |
| `q-role-explosion` | ロールの名前に、テナント・対象・操作の組み合わせを詰めていないか | どの設計でも |
| `q-rar-per-audience` | 承認の内容（authorization_details）を、宛先ごとに、その宛先に要る分だけに絞っているか | 操作ごとの承認がある |
| `q-validity-not-authz` | 「トークンが有効」というだけで通している操作はないか。操作・対象・その場の状況も見ているか | どの設計でも |
| `q-scope-and-role` | 受け手は、クライアントに委ねた範囲（scope）と、利用者に許した範囲（role）の両方を確かめているか | どの設計でも |
| `q-access-context-from-pep` | 「いまどこから来たか」（IP・端末）の判断に、トークンの値や偽装できるヘッダーを使っていないか | どの設計でも |
| `q-break-glass` | 緊急時の特権に、承認と短い期限があるか | どの設計でも |
| `q-system-actor-no-fake-sub` | サービス自身の権限で動かす処理は、利用者の文脈が要らない処理だけか | どの設計でも |
| `q-scope-elevation-logged` | 代理の主体の範囲は最小限から始まり、広げたことが記録に残るか | 委任がある（代理で動く主体がいる） |

根拠：筆者の提案：問いの区分・優先・出す条件・1 回の量の目安（追跡 #56）、templates/CONTRIBUTING.md の 2.・3.、research/template-design/pilot.md の 9.
