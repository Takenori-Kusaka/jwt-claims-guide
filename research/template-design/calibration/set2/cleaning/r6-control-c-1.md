# レビューの報告：designs/target（あおば住まいサービス 修繕の手配）

- 読んだもの：designs/target/ の design.md・claims.yaml・token_types.yaml・hops.yaml・catalog_answers.yaml・claim_request_repair_id.md・claim_request_approval_ref.md・schemas/LOCK_TOOL_AT.consumer.schema.json、ci-result.txt、sheet.md、short_list.md、perspectives.md（問いの書き方と読み方）、decision_tree.md、contrasts/act-txn-workload.md・signed-vs-enforced.md、kind_tell.md
- 行の抜き取りの種：12（sheet.md のとおり。C-approval-ref・C-repair-id・C-authorization-details）
- CI：error 0、warn 2（L16 の hop H5・H8）。warn には行ごとの理由がある（1. の表）。理由は「上流の REPAIR_DELEG_AT は承認の前に出るので承認の内容を載せられない。広げる根拠は別の権限の元（approval-svc の人の承認の記録）で、広がるのは 1 件分。受け手は approval-svc の条件つきの更新で使用済みにする」で、rar-vs-custom の節（承認は受け手が承認 ID・内容を照合）と合う。理由は通ると判断した（指摘にしない）
- 手順の段 0 の「検査を通すために宣言を曲げた跡」：hops の upstream は H3〜H12 に付いていて外していない。寿命の数値は 5.1 の出どころの表で要求（REQ-08・REQ-09）から導かれており、上限に合わせた跡は見当たらない

## 1. 段 1：性質の表を図と要求に照らす

| 性質 | sheet.md | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 合う。C-repair-id・C-approval-ref が名前空間つきの採用の行 |
| 個人情報を載せる | 当たる | 合う。C-sub・C-repair-id・C-authorization-details が「個人情報」 |
| 発行者が複数 | 当たる | 合う。aoba-as と agent-sts（catalog_answers の idp） |
| 交換・作り直し | 当たる | 合う。H3・H5〜H9・H11・H12 が exchange |
| 委任 | 当たる | 合う。C-act・C-may-act、max_delegation_depth 2 |
| 操作ごとの承認 | 当たる | 合う。authorization_details が H5・H8 にある。承認は 1 件の発注・1 回の解錠に結ぶ（時間枠の承認ではない） |
| マルチテナント | 当たらない | 合う。組織は 1 つで、物件の持ち主ごとに分けない（REQ にもテナントの区分は無い） |
| DB の層まで運ぶ | 当たらない | 合う。order-tool・order-scheduler は自分の DB アカウントで接続し、トークンを DB に渡さない（2. のデータ層の行・9.1 の DB の層） |
| 認証の強さ・新しさ | 当たる | 合う。C-acr・C-auth-time（REQ-07） |
| 送信者制約を選んだ | 当たる | 合う。ツールのトークン 4 種と APPROVAL_AT が mtls |
| 送信者制約を見送った | 当たる | 合う。CONSOLE_AT・REPAIR_DELEG_AT が none |
| 長時間・非同期 | 当たる | 合う。ORDER_TOOL_AT.long_running、U13 が該当（予約の発注） |

「当たらない」とされた性質が実際にある、という指摘は無い。

## 2. 段 2：6. の「要る」問いと判断の木の節

| UC | 問い | 木の節 | 節の選ぶ仕組み | 設計の仕組み | 判定 |
| --- | --- | --- | --- | --- | --- |
| UC1〜3 | q-sub | keep-sub-exchange | sub を保って交換 | agent-sts が sub を subject_token から写す（C-sub）。重要な操作は aoba-pdp で確かめ直す | 合う |
| UC1・2 | q-actor | keep-sub-exchange | act の最も外側で行為者 | C-act の最も外側を mTLS の相手と許可リストに当てる。内側は記録だけ（enforced_at・H5〜H8・H11 の validates でも同じ） | 合う |
| UC3 | q-actor | keep-sub-exchange | — | act が無く client_id が repair-console であること（本人の操作） | 合う |
| UC4 | q-sub・q-actor | keep-sub-exchange | 後で動く処理はワーカーが自分の ID で交換し直し、AS が承認の記録と利用者の状態で決める | 交換せず、order-scheduler が自分の証明書で同じ出どころ（aoba-pdp・修繕依頼の台帳・approval-svc・クライアントの登録の表）を実行の時点で引き直す。予約の記録は order-tool の DB アカウントだけが作り、変更の記録で改ざんを検出 | 答える問いは同じ（実行の時点の利用者の権限）。3. に既定から外れた点として理由つきで書いてある。不一致ではない |
| 全 UC | q-peer | peer-mtls | mTLS・SPIFFE | wl-ca の証明書の mTLS。act・client_id で代えていない | 合う |
| UC1〜3 | q-txn | txn-tctx | 1 つの呼び出しの連鎖なら Txn-Token の tctx | repair_id（何日もまたぐ修繕依頼の ID）を受け手が台帳と照合。取引の内容の固定は authorization_details が受け持つ。Txn-Token を却下した理由（ツールの先に連鎖が無い）が書いてある | 合う（連鎖が無いので tctx の出番が無い） |
| UC1・3 | q-authorized | rar-vs-custom / carry-or-query | 取引の承認は authorization_details、状態は問い合わせ | authorization_details（type は自組織の URI、宛先ごとに 1 つ）＋approval_ref で approval-svc の条件つきの更新。scope と併用するが、scope は操作の種類、authorization_details は 1 件の内容と台帳に分担が書いてある | 合う |
| UC1 | q-authorized（ロール） | carry-or-query | 変わる値は問い合わせ | ロールは載せず aoba-pdp（C-roles 却下） | 合う |
| 全 UC | q-holder | （木に節なし。対比表で確認） | cnf | ツール・approval-svc は C-cnf。REPAIR_DELEG_AT は may_act＋mTLS の URI で受ける（3.1 に見送りの理由と、中間の CA の漏えい時に開く口が書いてある） | 見送りとして理由あり。不一致にしない |
| 全 UC | q-resource・q-via・q-user・q-agent | — | aud・ログ・sub・client_id/act | それぞれ C-aud（1 つ）、交換の監査ログ（act の連鎖を経路にしていない：UC2 の q-via に明記）、C-sub、C-act・C-client-id | 合う |

目的と仕組みの不一致は見つからなかった。

## 3. 段 3：優先 1 の問い（自分の言葉で 1 行）

- dc-05：Yes。authorization_details のメンバーはすべて文字列で、金額は 10 進の文字列、時刻は 1 つの書式に固定し、受け手は書式違いを拒否してから完全一致で比べる。受け手のスキーマは items が object だけだが、3.1 の見送りで共通の部品の試験に回している
- q-value-vocabulary：Yes。ロールは載せず aoba-pdp が人事の台帳から導く。acr は aoba-as だけが書き agent-sts は写すだけなので、2 つの発行者で同じ文字列の意味がずれない
- q-identifier-choice：Yes。利用者のキーは aoba-as の sub（UUID、stable・再割り当てなし・on_missing 拒否）だけで、agent-sts は写すだけ。repair_id・approval_ref も identifier_properties と on_missing がある
- ap-1-7：Yes。修繕依頼の担当は課長のセッションの repair-console だけ、委任の欄は担当者のセッションだけ、ロールは人事の 2 人の手順だけ、承認の状態は approval-svc のアプリだけが書ける。DB の管理者の直接の書き込みは、変更の記録で使う前に検出する（3.1）
- q-freshness-mitigation：Yes。要求に数値がある（REQ-08 の 2 分・10 分、REQ-05 の直ちに）。重要な操作は呼び出しのたびの aoba-pdp（60 秒）と approval-svc（0 秒）、下書き・連絡は 390 秒で収まる（9.2）
- q-single-aud-resource：Yes。すべての AT の aud は 1 つで、ツールは配列にほかの値があれば拒否する
- q-no-passthrough：Yes。交換を頼めるのは委任の表とクライアントごとのリソースの表にある相手・宛先だけで、resource は 1 つ、scope は上流・宛先の操作・ロールの積
- q-step-up-path-coverage：Yes。追加の認証が要る操作（承認・手作業の事後の確認）は approval-svc の 1 か所で、入口は APPROVAL_AT だけ。代理・予約の経路からは承認の操作に届かない（付録 B）
- ap-2-7：Yes。エージェントが持つ act の無いトークンは 1 段目の REPAIR_DELEG_AT だけで、宛先は agent-sts、交換で出るツールのトークンには必ず act が入る。CONSOLE_AT はエージェントに渡らない
- q-authorize-service-and-user：Yes。すべてのホップで mTLS の相手を確かめ、呼ばれる側の許可リスト（証明書の URI）で通してよい相手を決める
- q-agent-short-lived-no-rt：Yes。agent-sts は RT を出さず、エージェントのトークンは 300 秒・手順ごとに交換し直す
- q-outside-catalog：Yes。管理用の口、テスト用の口（U30）、旧経路（U29）、証明書だけで受ける口、停止の間の電話の手配と再開の手順が 2.2・3.1・catalog_answers に答えてある
- q-object-level-authz：Yes。agent-sts（担当と委任の欄）、各ツール（発注・相手・部屋が repair_id のもの）、approval-svc（記録の repair_id）で止まり、どこも台帳で照合する（M_authz_pdp の 3.）
- q-approval-from-as：Yes（ただし R-3 の状態の遷移の書き漏れがある）。agent-sts は承認の記録からだけ作り、locations で宛先を固定し、受け手は条件つきの更新で使用済みにする。別のツール・visit-subagent には出せない
- q-operator-act：Yes。上長の引き継ぎは自分の CONSOLE_AT、担当の割り当ては課長の sub、DB の管理者・lock-svc の管理の画面の操作は変更の記録・監査ログに残る。代理ログインは作らない
- q-revocation-delivery：Yes。利用者の剥奪は重要な操作 60 秒・ほか 390 秒、委任の停止は 330 秒、ワークロードの証明書の漏えいは 30 分、中間の CA は 60 分（3.1 の見送り）、発行済みの解錠のコードは取り消しから 15 分。寿命 300 秒はこの分数から導いた（5.1）
- q-dependency-outage：Yes。aoba-as・aoba-pdp・修繕依頼の台帳・approval-svc・JWKS のどれも止める側に倒し、REQ-13 の 60 分は電話の手配で受ける（4.・3.1・付録 A の 5 分の警報）

No と答えた問いは無い。指摘は、答えの途中で見つけた記述の不整合と書き漏れ（下の表）。

## 4. 段 4：開いた問い

### op-proof-holder

辿った範囲：C-cnf の enforced_at、ツールのトークン 4 種・APPROVAL_AT の holder と sender_constraint、REPAIR_DELEG_AT の見送り（3.1）、付録 D の M_sender_constraint の 4.、hops の H4・H10。

| 箇所 | トークンを持つ者 | 確かめる鍵 | 一致 |
| --- | --- | --- | --- |
| order-tool・payment-tool・lock-tool | repair-agent | mTLS の相手の証明書の拇印＝cnf | 一致 |
| contact-tool | repair-agent か visit-subagent（交換を求めた者） | 同上 | 一致 |
| approval-svc | repair-console のサーバー | repair-console の証明書＝cnf | 一致（承認する人は鍵でなく BFF のセッションと auth_time で確かめる） |
| agent-sts（REPAIR_DELEG_AT の交換） | repair-agent・visit-subagent | 鍵でなく、mTLS の相手の URI＝may_act.sub | 鍵の束縛ではなく ID の照合。3.1 に見送りと、中間の CA の鍵が漏れたときに開く口が書いてある |

気づいたこと：証明書の更新は「証明書とトークンを組で持ち、古い組は古い接続で使い切る」と決めてあり、cnf の食い違いは起きない。REPAIR_DELEG_AT は URI で受けるので、同じ URI のどのインスタンスでも交換できる（実行基盤がトークンを持ち、モデルには渡さない前提）。指摘にはしない。

### op-source-change

辿った出来事：担当者が異動で修繕課から外れる。
人事部の担当者が登録 → 人事部の承認者が確定（2 人の手順。登録から確定まで 2 時間以内は人事部の手順書が約束し、この設計は月 1 回の報告で見る：3.1）→ aoba-pdp が確定した値を人事の台帳の API で読む（sub → 社員番号は hr-sync だけが書く aoba-as の属性。60 秒キャッシュ）→ 「修繕担当＝修繕課に在籍」が外れる → 発注の確定・解錠・支払い・承認は呼び出しのたびの aoba-pdp で最悪 60 秒、下書き・連絡は agent-sts の次の交換で外れ手元のトークンの分で最悪 390 秒、予約は実行の時点で拒否。
気づいたこと：aoba-pdp にロールを手で書く口が無く、元のデータの書き手は人事の 2 人だけ。修繕依頼の台帳の担当は異動の後も残るが、ロールで止まる。発行済みの解錠のコードは出来事から自動では止めず、30 分ごとの一覧と課長の手順で受ける（3.1 の見送り、REQ-06 は取りやめたときの 15 分だけを求める）。誰も時間を約束していない区間は見つからなかった。

### op-one-time

辿った値：発注の承認・解錠の承認（approval-svc の条件つきの更新）、解錠のコード（lock-svc の承認 ID ごとに 1 つ）、送信（通知の基盤の「承認 ID と回」）、LOGIN_CODE、CONSOLE_LOGOUT の jti。
- 並行の 2 件：承認の消費は 1 つの原子的な更新で片方だけ成功。部屋の累計は部屋の行の排他の錠で直列。lock-svc は同じ承認 ID に同じコードを返す
- 通信が切れた後の再送：同じ発注 ID・同じ承認なら前の結果を返し、確定は「下書き→確定」の条件つきの更新で 1 回。送信は同じ回で重複を捨てる
- 記録先の障害：approval-svc が止まれば拒否。使用済みにした後に確定が落ちたら同じ発注 ID で再試行し、正しい 1 回を失わない。確定できない下書きは承認を失効させて依頼し直す
気づいたこと：承認・却下・取り下げの操作そのもの（APPROVAL_AT。jti の再送の確かめなし、120 秒）は、記録の状態の遷移で 1 回にするはずだが、「取り下げ・却下した記録を承認し直せるか」が書いていない（R-3）。

## 5. 段 5：優先 2（時間が残ったので答えた）

答えは下の (2) の表。q-audit-correlation は Yes だが、ハッシュの鍵を 1 年ごとに替えるので、年をまたぐ修繕依頼は古い鍵と新しい鍵の両方で検索する運用になる（付録 D の M_privacy_minimization の 8. に書いてある）。
さらにの開いた問い（op-clock・op-key-custody・op-requirement-words）は、op-clock を auth_time（aoba-as の時計）と approval-svc の時計の比べ（ずれを足さない・NTP で 1 秒を超えたら外す）まで見て指摘なし、op-key-custody は R-2 の図の書き漏れだけ見つけた。op-requirement-words は辿っていない。

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| R-1 | claims.yaml の C-approval-ref の pii_category（該当なし）・log_policy（記録する）。claim_request_approval_ref.md の #20。design.md の付録 D の M_privacy_minimization の 1.・7.。比べた行：C-repair-id の pii_category・note、C-authorization-details の note。問い：q-audit-correlation・q-derived-value | C-repair-id は「修繕依頼の台帳と突き合わせると入居者が分かる」ので個人情報としてハッシュで残すのに、C-approval-ref は「それだけでは人を指さない」として値のまま残す。approval_ref は approval-svc の記録（repair_id・担当者・部屋・時間帯を持つ）と容易に突き合わせられ、C-authorization-details の note は「ログの approval_ref から approval-svc の記録を引く」と、部屋と時間帯への道として使っている。同じ基準で区分していないので、repair_id をハッシュにする理由が approval_ref で崩れる。区分をそろえるか、ハッシュにしない理由（読めるのは鍵を持つ監査の担当と部長だけ等）を書く | Minor | 理由の不備 | — |
| R-2 | design.md の 2.（scope-boundary）の範囲の図。比べた節：2.1（hr-sync・aoba-pdp は wl-ca の証明書の URI）、2.2（order-scheduler の証明書）、付録 D の M_authz_pdp の 5.（呼び出し元の許可リスト）、M_token_validation の 8.（wl-ca）。問い：op-key-custody・q-authorize-service-and-user | 図の wl-ca からの「証明書」の線は repair-console・repair-agent・visit-subagent の 3 つだけで、mTLS で相手を確かめるツール 4 つ・approval-svc・aoba-pdp・agent-sts・order-scheduler・hr-sync・lock-svc・通知の基盤・経理の仕組みへの線が無い。本文ではこれらもすべて wl-ca の証明書（URI）で許可リストに当てるので、図が中間の CA の鍵の漏えいで開く口（3.1）の範囲を小さく見せる | Minor | 実装とのずれ | — |
| R-3 | design.md の付録 D の P4_ai_agent_delegation の 5.（消費の競合と再送の状態の列）、hops.yaml の H12 の validates、claims.yaml の C-approval-ref の enforced_at（approval-svc）、APPROVAL_AT の jti_policy（replay_check: false）。問い：op-one-time・q-approval-from-as | 承認の記録の状態は「承認済み →（予約済み →）使用済み・未確定 → 確定済み」と「取り下げは使用済みの前だけ」しか書いていない。取り下げ・却下した記録を、承認者が（あるいは 120 秒以内の同じ APPROVAL_AT の再送で）承認し直せるかが決まっていない。REQ-05 は「取り下げたら直ちに止まる」で、課長・依頼の担当者の取り下げを承認者が上書きできると、止める操作が効かない。承認の操作の条件に「承認待ちの記録だけ」、取り下げ・却下を終わりの状態とすることを書く（上書きできる実装なら Major） | Minor | 候補の漏れ | — |

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| dc-05 | Yes | メンバーはすべて文字列、金額は 10 進の文字列、時刻は 1 つの書式で、書式違いを拒否してから完全一致で比べる（スキーマの欠けは 3.1 で試験に回す） |
| q-value-vocabulary | Yes | ロールは載せず aoba-pdp が人事の台帳から導く。acr は aoba-as だけが書き、agent-sts は写すだけ |
| q-identifier-choice | Yes | 利用者のキーは aoba-as の sub（UUID）だけで、identifier_properties と on_missing（拒否）がある |
| ap-1-7 | Yes | 担当・委任の欄・ロール・承認の状態の書き手が限られ、DB の管理者の直接の書き込みは使う前に変更の記録で検出する |
| q-freshness-mitigation | Yes | 要求の数値（2 分・10 分・直ちに）に対し、60 秒・390 秒・0 秒で収まる |
| q-single-aud-resource | Yes | どの AT も aud は 1 つで、配列にほかの値があれば拒否する |
| q-no-passthrough | Yes | 委任の表とリソースの表で相手と宛先を決め、resource は 1 つ、scope は積で絞る |
| q-step-up-path-coverage | Yes | 追加の認証が要る操作は approval-svc の 1 か所で、APPROVAL_AT の経路だけから届く |
| ap-2-7 | Yes | エージェントの act の無いトークンは宛先が agent-sts だけの 1 段目の REPAIR_DELEG_AT だけ |
| q-authorize-service-and-user | Yes | どのホップも mTLS の相手を確かめ、呼び出し元の許可リストで通す |
| q-agent-short-lived-no-rt | Yes | agent-sts は RT を出さず、エージェントのトークンは 300 秒 |
| q-outside-catalog | Yes | 管理用の口・テストの口・旧経路・証明書だけの口・電話の手配を 2.2・3.1・catalog_answers で答えている |
| q-object-level-authz | Yes | agent-sts・各ツール・approval-svc が repair_id を台帳と照合して止める |
| q-approval-from-as | Yes | 承認の記録からだけ作り locations で宛先を固定し、受け手が条件つきの更新で使う（状態の遷移の書き漏れは R-3） |
| q-operator-act | Yes | 上長・課長・DB の管理者・当番の操作は自分の ID で残り、代理ログインは無い |
| q-revocation-delivery | Yes | 重要な操作 60 秒・ほか 390 秒・委任の停止 330 秒・証明書 30 分・解錠のコード 15 分で、寿命はこの分数から導いた |
| q-dependency-outage | Yes | 依存先のどれも止める側に倒し、REQ-13 の 60 分を電話の手配で受ける |
| op-proof-holder（開いた問い） | 該当なし | 開いた問い。ツール・approval-svc は持つ者と鍵が一致、REPAIR_DELEG_AT は URI の照合で見送りの理由あり（4. に記載） |
| op-source-change（開いた問い） | 該当なし | 開いた問い。異動を人事の 2 人の手順から受け手まで辿れ、約束の無い区間は無かった（4. に記載） |
| op-one-time（開いた問い） | 該当なし | 開いた問い。承認・コード・送信は 1 回になる。取り下げた記録の承認し直しが未記述（R-3） |
| pa-01 | Yes | 25 問の問 1 に、repair_id・approval_ref の受け手ごとの使い道が書いてある |
| q-derived-value | Yes | 個人情報の行（sub・repair_id・authorization_details）は、載る宛先の受け手がどれも照合に使う |
| q-variant-comparison | Yes | 送信者制約の見送りは、盗んだときに呼べる口と代わりの守り（mTLS のクライアント認証・may_act）を比べている |
| q-idp-diff-absorbed | Yes | ツール・approval-svc は agent-sts のトークンだけを受け、aoba-as のトークンは内側の受け手に届かない |
| q-original-principal | Yes | 交換の後も sub は担当者のままで、scope は上流とロールの積に絞る |
| q-step-up-by-rs | Yes | 追加の認証を求めるかは、操作を受ける approval-svc が決める |
| q-long-running | Yes | 予約はトークンを持ち越さず、実行の時点で在籍・ロール・担当・委任の世代・承認を確かめ直す |
| q-copies-outlive | Yes | 予約の記録の写しは実行の時点で確かめ直し、改ざんは変更の記録で検出する。監査ログは 3 年でハッシュ |
| q-audit-correlation | Yes | sub・repair_id は全サービス同じ鍵のハッシュ、approval_ref・発注 ID・jti は値のままで 1 本に結べる（鍵の年替えは両方の鍵で検索） |
