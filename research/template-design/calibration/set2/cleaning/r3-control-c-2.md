# レビューの記録：designs/target（あおば住まいサービス 修繕の手配）

- 読んだもの：designs/target の design.md（1.〜13.・付録 A〜D）、claims.yaml、token_types.yaml、hops.yaml、catalog_answers.yaml、claim_request_repair_id.md・claim_request_approval_ref.md、schemas の ORDER_TOOL_AT・APPROVAL_AT の受け手のスキーマ、ci-result.txt、sheet.md、教材（short_list.md の参照は sheet.md 経由、perspectives.md の「問いの書き方と読み方」、decision_tree.md、kind_tell.md）
- 抜き取りの種：12（sheet.md の指定のとおり C-approval-ref・C-repair-id・C-authorization-details）

## 0. 受け付け（CI の結果と、宣言を曲げた跡）

- 1. の結果は ci-result.txt と一致（error 0、warn 2、info 24）
- warn は L16 の 2 件（H5・H8 で authorization_details が上流 H4 に無い＝下流で広げる）。書き手の理由（承認の記録という別の権限の元から 1 件分だけ足す。上流の REPAIR_DELEG_AT は承認の前に出すので載せられない。agent-sts は承認済みの記録からだけ作り、受け手は approval-svc の条件つきの更新で確かめる）は、仕組み（C-authorization-details・C-approval-ref の enforced_at、付録 D の P4 の 5.）と合っており、通ると判断した
- 宣言を曲げた跡：hops の upstream は H5〜H8 が H4、H11 が H10、H12 が H2 で、上流を外していない。aud_replacement の理由も実際の宛先の置き換えと合う。寿命の数字は 5.1 で要求（REQ-08・REQ-09）から導かれ、上限に合わせて丸めた跡は無い

## 1. 設計の性質の表の確かめ（12.・2.・6. と図・要求に照らして）

| 性質 | sheet.md | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 正しい。repair_id・approval_ref（名前空間 https://aoba-sumai.example/claims/） |
| 個人情報 | 当たる | 正しい。C-sub・C-repair-id・C-authorization-details・C-name が 個人情報 |
| 発行者が複数 | 当たる | 正しい。aoba-as と agent-sts（2. の図・catalog の idp） |
| 交換・作り直し | 当たる | 正しい。H3・H5〜H9・H11・H12 が exchange |
| 委任 | 当たる | 正しい。act・may_act、深さ 2（REQ-04） |
| 操作ごとの承認 | 当たる | 正しい。authorization_details・approval_ref（REQ-05・REQ-06） |
| マルチテナント | 当たらない | 正しい。組織は 1 つ、テナントの値が無い（物件の持ち主ごとに分けない） |
| トークンの値を DB まで運ぶ | 当たらない | 正しい。発注の台帳は order-tool・order-scheduler の DB アカウント（2. の表のデータ層の行、9.1 の DB の接続の層） |
| 認証の強さ・新しさ | 当たる | 正しい。acr・auth_time（amr は却下） |
| 送信者制約を選んだ | 当たる | 正しい。ツールのトークン 4 種と APPROVAL_AT が mtls |
| 送信者制約を見送った | 当たる | 正しい。CONSOLE_AT・CONSOLE_RT・REPAIR_DELEG_AT が none（3.1 に理由） |
| 長時間・非同期の処理 | 当たる | 正しい。予約の発注（REQ-10。ORDER_TOOL_AT の long_running、H13・H14） |

当たらないとされた性質が実際にある、という食い違いは無かった。

## 2. 6. の「要る」問いと判断の木の節の比べ

| ユースケース・問い | 判断の木の節 | 節が選ぶ仕組み | 設計の仕組み | 結果 |
| --- | --- | --- | --- | --- |
| UC1〜UC3 q-sub・q-actor | keep-sub-exchange | 交換で sub＝利用者、act＝代理者、宛先ごと・分単位。許可には最も外側の act | C-sub（写すだけ）、C-act（最も外側の act.sub だけを許可リストに当て、内側は記録だけ。enforced_at・H5〜H8・H11 の validates でも同じ） | 一致 |
| UC4 q-sub・q-actor | keep-sub-exchange（非同期） | ワーカーが自分の ID で交換し直し、そのたびに AS が承認の記録と利用者の状態で決める | トークンを使わず、order-scheduler が実行の時点で AS と同じ出どころ（aoba-pdp・委任の欄・approval-svc・クライアントの登録の表）を引き直す。3. と 3.1 に既定から外れた点として理由と確かめ方がある | 答える問いは同じ（実行の時点で利用者の権限と承認を確かめ直す）。不一致ではない |
| q-peer | peer-mtls | mTLS・SPIFFE。クレームで代えない | wl-ca の証明書の mTLS（URI の SAN）。end_to_end で終端 | 一致 |
| q-txn | txn-tctx | 経路全体で取引の内容を固定したいなら Txn-Token | 相関と対象の照合には repair_id。取引の内容（金額・部屋）の固定は authorization_details が担い、ツールの先にトークンの連鎖が無い（TXN_TOKEN 却下の理由） | 「経路全体で固定したいか」は No で、節の選び方どおり |
| q-authorized | rar-vs-custom | authorization_details（type は自分の URI）、宛先ごとに絞る。scope と併用なら役割を書く | authorization_details（locations で宛先を固定、宛先ごとに 1 つの type）、scope は操作、承認の状態は approval_ref で問い合わせる | 一致 |
| q-holder | existing-claim-first | cnf | C-cnf（x5t#S256） | 一致 |
| q-agent・q-resource・q-user・q-via | existing-claim-first | client_id・act、aud、iss と sub、ネストした act | 同じ | 一致 |
| 寿命（q-still-valid に当たる判断） | lifetime-by-situation | 剥奪の速さを先に決める。重要な操作は短命＋都度判定、ワークロードは RT なし | REQ-08 の 2 分・10 分から 300 秒と aoba-pdp の都度の問い合わせ、エージェントに RT なし | 一致 |

目的と仕組みの不一致は見つからなかった。

## 3. 優先 1 の問い（自分の言葉で 1 行ずつ）

- dc-05：Yes。authorization_details のメンバーはすべて文字列で、金額は先頭 0 なしの 10 進の文字列、時刻は 1 つの書式に固定し、書式違いを拒否してから完全一致で比べる。生成のスキーマがメンバーの型を表せない点は 3.1 で見送りにし、共通部品の試験で補っている
- q-value-vocabulary：Yes。ロール・グループは載せずに aoba-pdp が人事の台帳から導く。scope と authorization_details の type は閉じた語彙で持ち主があり、ツールは agent-sts の iss だけを受けるので、別の発行者の同じ文字列は通らない
- q-identifier-choice：Yes。キーに使う sub（UUID）・repair_id・approval_ref・client_id は台帳の行になっており、identifier_properties と on_missing がある。社員番号は aoba-pdp の中だけで使い、トークンに出ない
- ap-1-7：**No**。修繕依頼の台帳・協力会社の台帳・人事の台帳・aoba-as の利用者の書き手は限っているが、承認の要否（部屋の累計）と支払いの額・可否を決める発注の台帳に、order-tool・order-scheduler 以外のアプリの書き手（協力会社の受発注の画面、課長の「手作業の発注」の登録）がいるのに、限り方が無い（指摘 F1）
- q-freshness-mitigation：Yes。scope は 390 秒（許容 600 秒）、在籍・ロール・担当は aoba-pdp の都度の問い合わせで 60 秒（許容 120 秒）、承認は 0 秒（approval-svc の条件つきの更新）。数値は REQ-08・REQ-09・REQ-05 にあり、対策を行う者（agent-sts・各ツール・approval-svc）も書いてある
- q-single-aud-resource：Yes。どの種別も aud は 1 つで、ツールは配列に別の値があれば拒否する
- q-no-passthrough：Yes。交換は agent-sts だけで、クライアントごとのリソースの表と委任の表で宛先と相手を決め、エージェントが申告した resource でも表に無ければ出さない
- q-step-up-path-coverage：Yes。承認の操作の口は approval-svc の APPROVAL_AT の口 1 つだけで、エージェント・予約・証明書だけの口（依頼の登録・予約済みの使用）からは承認済みにできない
- ap-2-7：Yes。act の無いトークンのうち代理の主体が持つのは 1 段目の REPAIR_DELEG_AT だけで、宛先は agent-sts だけ、交換できるのは may_act の主体の mTLS だけ。ツールは aoba-as のトークンも REPAIR_DELEG_AT も受けない
- q-authorize-service-and-user：Yes。ツール・approval-svc・aoba-pdp・下流は呼び出し元の証明書の URI の許可リストで相手を確かめ、ツールは最も外側の act.sub と mTLS の相手、cnf と証明書の拇印を照合する
- q-agent-short-lived-no-rt：Yes。agent-sts は RT を出さず、エージェントのトークンは 300 秒か上流の残りの短いほう
- q-outside-catalog：**No**。outside_enumeration で 9 つの場面を拾っているが、発注の台帳に書き込む図に無い口（協力会社の受発注の画面、停止の後の「手作業の発注」の登録の経路）が、図にも書き手の限りにも無い（指摘 F1）
- q-object-level-authz：Yes。agent-sts（修繕依頼の担当と委任の欄）、order-tool・payment-tool（発注の修繕依頼）、contact-tool（相手を台帳から決める）、lock-tool（部屋）、approval-svc（記録の repair_id）でデータ層と照合し、トークンの値だけに任せていない
- q-approval-from-as：Yes。承認の内容は agent-sts が approval-svc の承認済みの記録から作り、locations の宛先のツールのトークンにだけ載せ、ツールは承認の記録の発注 ID・修繕依頼・担当者を条件に使用済みにする。別のツール（type と locations）・別の代理の主体（リソースの表）には使わせない
- q-operator-act：Yes。上長の引き継ぎは自分の sub で、担当の割り当ては担当の履歴に追記、設定の変更は PR、DB の管理者の直接の書き込みは変更の記録の表と毎日の突き合わせで、利用者の操作と分けて残る
- q-revocation-delivery：**No（一部）**。利用者・委任・エージェントの単位は最悪の分数が並び（重要な操作 60 秒、そのほか 390 秒、委任の停止 330 秒、ワークロードの URI の差し替え 30 分）、要求に収まる。一方、取引先（協力会社・作業員）の単位では、発行した解錠コードを not_after（最大 4 時間）より前に止める手段と、そのとき許す遅れが書いていない（指摘 F3）
- q-dependency-outage：Yes。aoba-as・aoba-pdp・修繕依頼の台帳・approval-svc・agent-sts・JWKS のどれが止まっても止める側に倒し、5 分の警報と電話の手配（REQ-13 の 60 分）に合わせている。lock-svc・通知の基盤の失敗は同じ承認 ID の再試行で扱う

## 4. 開いた問い

### op-proof-holder（鍵の持ち主を確かめる箇所）

辿った範囲：cnf の enforced_at（order-tool・contact-tool・payment-tool・lock-tool・approval-svc）、目録の holder と sender_constraint、REPAIR_DELEG_AT の may_act の確かめ（agent-sts）、付録 D の M_sender_constraint の 4.、3.1 の wl-ca の行。

| 箇所 | トークンを持つ者 | 確かめる鍵の持ち主 | 結果 |
| --- | --- | --- | --- |
| order-tool・payment-tool・lock-tool | repair-agent | 交換を求めた repair-agent の証明書（cnf） | 同じ |
| contact-tool | repair-agent か visit-subagent | 交換を求めた者の証明書 | 同じ（H6 と H11 で別の交換） |
| approval-svc | repair-console | repair-console の証明書 | 同じ |
| agent-sts（REPAIR_DELEG_AT） | repair-agent か visit-subagent（束縛なし） | may_act の主体の mTLS の証明書の URI | 同じ（束縛の代わりに may_act と mTLS の相手を照合） |

気づいたこと：
- 証明書の更新（24 時間、残り 8 時間で更新）では、クライアント部品が証明書とトークンを組で持ち、古い組は古い接続で使い切るので、cnf の食い違いは起きない
- 鍵の漏えいで世代の番号を上げた URI に替えると、古い URI の行為者が作った正しい予約も order-scheduler が実行しなくなる（止める側に倒れる）。業務の影響（予約の取り直し）が 3.1 に書いていないが、指摘にはしない
- repair-console やエージェントを複数の実体（レプリカ）で動かすとき、実体ごとに鍵が別なら、ある実体が得た APPROVAL_AT・ツールのトークンを別の実体では使えない。「クライアントごとに証明書 1 つ」（C-client-id の assumption）が実体ごとの鍵か共有の鍵かが読み取れない。設計の外の構成なので、確かめの候補として残す

### op-source-change（元のデータが変わる出来事：異動でロールが外れる）

辿った範囲：9.2 の「元のデータからの経路」、C-sub の source_system・verification_method、付録 D の M_authz_pdp の 5.、3.1 の人事の台帳の行、2.2 の人事連携の行。

辿った経路：人事部の担当者が人事システムで異動を登録 → 人事部の 2 人目の承認で確定（人事部の手順書で当日の業務時間内・2 時間以内。月 1 回の報告）→ aoba-pdp が人事の台帳の API で確定値を読む（60 秒キャッシュ）→ 修繕課に在籍しなくなるので修繕担当のロールを導かない → agent-sts は次の交換で scope を外し、重要な操作のツールは呼び出しのたびに拒否（最悪 60 秒）、下書き・連絡は手元のトークンで最悪 390 秒。

気づいたこと：
- aoba-pdp が sub から社員番号を引く aoba-as の属性は hr-sync だけが書くが、異動では社員番号が変わらないので、hr-sync の 5 分の遅れは経路に入らない（設計の主張どおり）
- 誰も時間を約束していない区間は、登録から確定まで（人事部の手順、3.1 で見送りにして測り方を書いた）だけで、それ以外は秒数が決まっている
- ロールの導き方の規則は設定のリポジトリの PR（2 人の承認）で変わり、手で付ける口が無い。図に無い書き込みの経路は、この出来事では見つからなかった（発注の台帳の書き手は別の出来事。F1）

### op-one-time（1 回だけ使える値）

辿った範囲：付録 D の P4 の 5.（消費の競合と再送）、C-approval-ref・C-authorization-details の enforced_at、3.1 の「重複の実行を、業務の ID で防ぐ」、M_token_validation の 6. の「1 回だけ受ける値」、2.2 の予約の実行、12. の lock-svc と通知の基盤の行、ログアウトトークンの jti。

| 値 | 並行の 2 件 | 通信が切れた後の再送 | 記録先の障害 |
| --- | --- | --- | --- |
| 発注の承認 | approval-svc の原子的な条件つきの更新で片方だけ成功。部屋の累計は排他の錠で直列 | 同じ発注 ID に前の結果を返し、「下書き→確定」も条件つきなので 1 回 | approval-svc が止まれば拒否。使用済み・未確定の承認は下書きと一緒に残し、取り消しのときは失効 |
| 予約の承認 | 予約済み→使用済みの条件つきの更新 | order-scheduler が同じ発注 ID で次の回に再試行 | 確定の前に落ちても同じ発注 ID で 1 回 |
| 解錠の承認 | 承認自身に結ぶので 2 件とも同じ結果、lock-svc は承認 ID ごとにコード 1 つ | 同じ承認 ID で再試行、同じコード | approval-svc が止まれば拒否 |
| ログアウトトークン | jti を 150 秒覚えて拒否 | 同上 | repair-console のセッションの保存先 |
| 認可コード | aoba-as が 1 回限り | — | — |

気づいたこと：
- 2 回通る経路は見つからなかった
- 一方、解錠コードの「正しい 1 回」を届ける部分で、同じ仕組みの書き方が 2 か所で食い違う。通知の基盤は承認 ID を送信の重複を避ける鍵にする一方、作業員に届かないと担当者が知らせたら同じ承認 ID で送り直せると書く。通知の基盤が 1 回目を「送信済み」と記録していれば、送り直しは重複として捨てられ、正しい 1 回が失われる。また、送り直しには LOCK_TOOL_AT（approval_ref つき）が要るが、agent-sts は「承認済み」の記録から作るとあり、使用済みの承認で送り直し用のトークンを出すかが決まっていない（指摘 F2）

## 5. 優先 2 の問い（時間が残ったので答えた）

- pa-01：Yes。claim_request の問 1 と usage・enforced_at が対応し、表示用の name は ID トークンだけで認可に使わない
- q-derived-value：Yes。入居者の連絡先・住所・解錠コードは却下し、repair_id や部屋の ID などの参照の ID だけを載せる。authorization_details の部屋の ID・時間帯は照合に要る受け手（order-tool・lock-tool）宛てだけに載り、ログに残さない
- q-variant-comparison：Yes。送信者制約の見送り・JWKS の取り直しの失敗時の拒否・予約で交換し直さないことは、開く攻撃（盗んだ CONSOLE_AT・RT、漏れた鍵、長い寿命のトークン）と代わりの守り（mTLS のクライアント認証、may_act、記録の引き直し）を比べている
- q-idp-diff-absorbed：Yes。ツールには agent-sts のトークンだけが届き、aoba-as の種別が内側の受け手に届くホップは無い
- q-original-principal：Yes。交換の後も sub は担当者のままで、scope は上流と宛先と担当者のロールの積に絞る。order-scheduler も予約の記録の担当者の権限で確かめ直す
- q-step-up-by-rs：Yes。追加の認証の要否は approval-svc が決め、401 と insufficient_user_authentication を返す
- q-long-running：Yes。予約はトークンを持ち越さず、実行の時点で在籍・ロール・担当・委任の欄・承認・行為者の登録・予約の記録の改ざんを確かめ直す
- q-copies-outlive：Yes。監査ログ（鍵つきのハッシュ）と発注の台帳の予約の記録を integrity_until に挙げ、aoba-pdp の 60 秒のキャッシュも書いてある。開いたままの DB の接続にトークンを使わない
- q-audit-correlation：Yes。sub と repair_id は全サービスで同じ鍵の HMAC、approval_ref は値のまま、act の連鎖と jti の結び付けで「誰の権限で・誰が代理で・どの承認で」がつながる

## 6. 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | design.md の 3.1（`#priorities-deferrals`）の見送りの行「修繕依頼の台帳と協力会社の台帳の書き込みの口を、この設計で閉じること」と「DB の管理者の直接の書き込み」の行、2.2（`#system-privileges`）の「緊急時の特権」の行（課長が発注の台帳に「手作業の発注」を登録）、付録 C（`#result-integrity`）の「協力会社からの完了の報告」の行（受発注の画面が発注の台帳に書く）、2.（`#scope-boundary`）の図（発注の台帳 OD への矢印が order-tool・order-scheduler の DB アカウントだけ）、hops.yaml の H5 の validates（部屋の直近 30 日の累計）・H7 の validates（確定済みで完了の報告がある、確定額）、catalog_answers.yaml の outside_enumeration の found（停止の間の電話での発注）と U29。問い：ap-1-7・q-outside-catalog | 承認の要否（REQ-05 の部屋の累計。取り消した発注を除く）と支払いの可否・額（確定済み・完了の報告・確定額）は、発注の台帳の値で決まる。ところが発注の台帳に書くアプリの口は order-tool・order-scheduler のほかに、協力会社の受発注の画面（完了の報告）と、課長の「手作業の発注」の登録（どの画面・どのアカウントで書くかが無い）があり、図にも、3.1 の書き手を限る行にも入っていない。限りが無いと、取り消し・金額・状態をこれらの口から書き換えて、累計を下げて上長の承認を逃れる、完了の報告や確定額を書き換えて支払いを依頼させる、ことを止められない（予約の記録だけは order-scheduler が変更の記録の表で確かめるが、累計と支払いは守られない）。また、手作業の発注を DB の管理者が直接書くなら、毎日の突き合わせで「アプリを通らない変更」として毎回知らせが出るのか、正しい経路なのかも決まらない。直す案：発注の台帳の書き手と書ける欄（状態・金額・取り消し・完了の報告）を 3.1 に足し、受発注の画面が書けるのは完了の報告だけにする、手作業の発注の登録の口と承認を決める | Major | 候補の漏れ | ap-1-7、q-outside-catalog |
| F2 | design.md の 3.1（`#priorities-deferrals`）の重点の行「重複の実行を、業務の ID で防ぐ（jti に頼らない）」、付録 D の P4_ai_agent_delegation の 5.（`template:profiles/P4_ai_agent_delegation#human-approval`）の「消費の競合と再送」、12.（`#uncertain`）の「lock-svc と通知の基盤の重複の鍵」、4.（`#issuance-profile`）の「交換の要求の authorization_details」の条件、claims.yaml の C-approval-ref の enforced_at（lock-tool：承認済み・未使用なら使用済み）。問い：op-one-time | 解錠コードの送信について、通知の基盤は承認 ID を送信の重複を避ける鍵にすると書く一方、作業員に届かないと担当者が知らせたら、エージェントが同じ承認 ID で送り直しを頼めると書く。通知の基盤が 1 回目を送信済みとしていれば、送り直しは重複として捨てられ、作業員に正しい 1 回が届かない（2 か所が同じ仕組みについて食い違う）。さらに送り直しの LOCK_TOOL_AT は、agent-sts が「承認済み」の記録から作るとあり、使用済みの承認で出してよいか、lock-tool の条件つきの更新が送り直しをどう通すかが決まっていない。直す案：送信の重複の鍵を「承認 ID と送信の回」にするか、送り直しは通知の基盤の側の再送の口にする。使用済みの承認での送り直しのトークンを出す条件（not_after まで、送り先は登録の番号のハッシュと一致するときだけ）を 4. と台帳に書く | Minor | 実装とのずれ | op-one-time |
| F3 | design.md の 9.1（`#lifecycle`）の「承認の記録（approval-svc）」の行（解錠は not_after まで、取り下げは使用済みの前だけ）、付録 D の P4_ai_agent_delegation の 9.（`template:profiles/P4_ai_agent_delegation#chain-revocation`）、2.（`#scope-boundary`）の要求の要約の REQ-06・REQ-08、claims.yaml の C-unlock-code（却下）の assumption（lock-svc は not_after まで持つ）、token_types.yaml の LOCK_TOOL_AT の revocation。問い：q-revocation-delivery | 止める単位を利用者・委任・エージェントで並べた表はあるが、取引先（協力会社・作業員）の単位が無い。発行した解錠コードは not_after（最大 4 時間）まで有効で、協力会社との取り引きの停止、作業員の登録の取り消し、担当者の退職・担当の付け替え（REQ-08 は「発行」を止めるだけ）、発行の後に担当者が取りやめたい場合に、そのコードを止める手段（lock-svc での失効）も、要求が許す遅れの数値も書いていない。「期限が切れれば効く」だけに頼っている。直す案：lock-svc に承認 ID ごとのコードの失効の口を置き、誰が（担当者・課長・協力会社の窓口）どの出来事で呼ぶか、許す遅れを要求に足す。要らないと判断するなら、その理由（4 時間以内の窓・機器側の制約）を 3.1 の見送りの行に書く | Minor | 候補の漏れ | q-revocation-delivery |

重大度ごとの件数：Blocker 0、Major 1、Minor 2。

## 7. 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| dc-05 | Yes | authorization_details のメンバーはすべて文字列、金額は 10 進の文字列、時刻は 1 つの書式に固定して完全一致で比べる |
| q-value-vocabulary | Yes | ロールを載せず aoba-pdp で引き、scope と type の語彙は閉じて持ち主があり、受け手は agent-sts の iss だけを受ける |
| q-identifier-choice | Yes | キーの sub・repair_id・approval_ref・client_id は台帳の行で、identifier_properties と on_missing がある |
| ap-1-7 | No | 発注の台帳の書き手（受発注の画面・手作業の発注の登録）が限られていない（F1） |
| q-freshness-mitigation | Yes | scope 390 秒・在籍とロールと担当 60 秒・承認 0 秒で、要求の数値の内側。対策を行う者も書いてある |
| q-single-aud-resource | Yes | どの種別も aud は 1 つで、ツールは別の値が並べば拒否する |
| q-no-passthrough | Yes | 交換は agent-sts だけで、リソースの表と委任の表で相手と宛先を決める |
| q-step-up-path-coverage | Yes | 承認済みにする口は APPROVAL_AT の口 1 つだけで、ほかの経路から届かない |
| ap-2-7 | Yes | act の無い 1 段目の REPAIR_DELEG_AT は agent-sts 宛てだけで、may_act の主体しか交換できない |
| q-authorize-service-and-user | Yes | 呼ばれる側が証明書の URI の許可リストで相手を確かめ、ツールは act.sub と cnf も照合する |
| q-agent-short-lived-no-rt | Yes | agent-sts は RT を出さず、エージェントのトークンは 300 秒以下 |
| q-outside-catalog | No | 発注の台帳に書く図に無い口（受発注の画面・手作業の発注の登録）が答えられていない（F1） |
| q-object-level-authz | Yes | agent-sts・各ツール・approval-svc が修繕依頼・発注・部屋・承認の記録をデータ層で照合する |
| q-approval-from-as | Yes | 承認の内容は approval-svc の記録から作り、宛先（locations）と発注 ID・担当者に結んで 1 回だけ使う |
| q-operator-act | Yes | 運用者は自分の sub で操作し、担当の割り当て・設定の変更・DB の直接の書き込みは別の記録に残る |
| q-revocation-delivery | No | 取引先・作業員の単位で、発行した解錠コードを not_after より前に止める手段と許す遅れが無い（F3） |
| q-dependency-outage | Yes | 頼る先のどれが止まっても止める側に倒し、REQ-13 の 60 分と 5 分の警報に合わせている |
| op-proof-holder | 該当なし（開いた問い） | 5 種の束縛と REPAIR_DELEG_AT の may_act のどの箇所も、持つ者と鍵の持ち主が同じ。レプリカの鍵の扱いは確かめの候補 |
| op-source-change | 該当なし（開いた問い） | 異動の経路を人事の登録から辿り、時間の約束が無いのは 3.1 で見送った登録から確定までだけ |
| op-one-time | 該当なし（開いた問い） | 2 回通る経路は無いが、解錠コードの送り直しで正しい 1 回が失われうる（F2） |
| pa-01 | Yes | claim_request の問 1 と usage・enforced_at が対応し、表示用の値で認可しない |
| q-derived-value | Yes | 個人情報の値そのものを載せず参照の ID だけで、照合する受け手宛てだけに載せる |
| q-variant-comparison | Yes | 既定から外した点ごとに、開く攻撃と代わりの守りと確かめ方を比べている |
| q-idp-diff-absorbed | Yes | 内側のツールには agent-sts のトークンだけが届き、aoba-as の種別は届かない |
| q-original-principal | Yes | 交換の後も sub は担当者で、scope は担当者のロールで絞る |
| q-step-up-by-rs | Yes | 追加の認証の要否は approval-svc が決める |
| q-long-running | Yes | 予約は実行の時点で権限・委任・承認を確かめ直し、トークンを持ち越さない |
| q-copies-outlive | Yes | 監査ログと予約の記録を integrity_until に挙げ、キャッシュの秒数も書いてある |
| q-audit-correlation | Yes | sub・repair_id を同じ鍵の HMAC で、approval_ref・act の連鎖・jti で 1 本につなげる |
