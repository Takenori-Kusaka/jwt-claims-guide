# レビューの記録：designs/target（あおば住まいサービス 修繕の手配）

- 対象：designs/target/design.md と claims.yaml・token_types.yaml・hops.yaml・catalog_answers.yaml・claim_request_*.md・schemas/
- 使った資料：sheet.md（抜き取りの種 12）、short_list.md、perspectives.md、decision_tree.md、contrasts/、kind_tell.md、ci-result.txt
- 抜き取った行（種 12）：C-approval-ref・C-repair-id・C-authorization-details。ap-1-7 の答えが No だったので、C-sub・C-scope も見た
- CI（段 0）：ci-result.txt と設計書の 1. は一致している。error 0・warn 2（L16 の H5・H8）。warn には行ごとの理由がある。理由と実装が食い違う点は F3 に書いた

## 段 1：性質の表の確かめ（12.・2.・6. と照らす）

| 性質 | sheet の判定 | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 正しい（repair_id・approval_ref。名前空間 https://aoba-sumai.example/claims/） |
| 個人情報を載せる | 当たる | 正しい（sub・repair_id・authorization_details・name） |
| 発行者が複数 | 当たる | 正しい（aoba-as と agent-sts。どちらも組織が自分で作る） |
| 交換・作り直し | 当たる | 正しい（H3・H5〜H9・H11・H12 が exchange） |
| 委任 | 当たる | 正しい（act・may_act。max_delegation_depth は 2） |
| 操作ごとの承認 | 当たる | 正しい（authorization_details と approval_ref。どちらも発注 1 件・解錠 1 回に結びつく） |
| マルチテナント | 当たらない | 正しい。組織は 1 つで、テナントを表す値も、物件の持ち主ごとの分離も無い（2. の図・REQ にも無い） |
| DB の層まで運ぶ | 当たらない | 正しい。order-tool・order-scheduler は自分の DB アカウントで接続する（2. のデータ層の行、9.1 の接続の層） |
| 認証の強さ・新しさ | 当たる | 正しい（acr・auth_time。amr は却下） |
| 送信者制約を選んだ | 当たる | 正しい（ツールのトークン 4 種と APPROVAL_AT が mtls） |
| 送信者制約を見送った | 当たる | 正しい（CONSOLE_AT・CONSOLE_RT・REPAIR_DELEG_AT が none） |
| 長時間・非同期 | 当たる | 正しい（ORDER_TOOL_AT の long_running、H13・H14、U13 が該当） |

当たらないとされた性質のうち、実際にあるものは無かった。12.（書き手が自信のない点）は確かめていない事実だけを挙げていて、委任の深さ 2 は専門家に回されている（short_list の 5. の q-delegation-depth-and-revocation は、レビュアーは答えない）。

## 段 2：6. の「要る」の問いと判断の木

| 問い | 判断の木の節 | 設計の仕組み | 合っているか |
| --- | --- | --- | --- |
| q-sub | keep-sub-exchange | 交換では sub を subject_token から写す。UC4 は予約の記録の sub を使い、実行の時点で同じ出どころを引き直す | 合っている。UC4 で交換しないことは 3. と 3.1 に、理由と代わりの確かめとともに書いてある |
| q-actor | keep-sub-exchange（最も外側の act か） | 最も外側の act.sub を mTLS の相手と許可リストに照らす（enforced_at・validates とも）。内側の act は記録だけ。UC3 は act が無いことと client_id | 合っている |
| q-peer | peer-mtls | wl-ca の証明書の mTLS と、呼び出し元の許可リスト | 合っている |
| q-txn | txn-tctx | C-repair-id。Txn-Token は却下（ツールの先に呼び出しの連鎖が無い） | 合っている。節の問い（連鎖の中で取引を固定したいか）の答えは「いいえ」で、却下の理由がある |
| q-authorized | rar-vs-custom | authorization_details（type は組織の URI、locations で宛先を絞る）＋approval_ref＋scope | 合っている。scope と併用するが、M_authz_pdp の 4. で層ごとの役目が決まっている |
| q-resource | （carry-or-query ではなく aud） | aud は 1 つ（resource は 1 つ） | 合っている |
| q-holder | existing-claim-first（cnf） | cnf の x5t#S256。UC2 の REPAIR_DELEG_AT だけ may_act と mTLS の URI | おおむね合っている。may_act は鍵ではなく ID（URI）で照合するので、3.1 の「鍵が無ければ使えない」は言い過ぎ（F4） |
| q-via | （節なし。contrasts/act-txn-workload の m-10） | UC1・UC3・UC4 は監査ログ。UC2 は「act の連鎖と交換の監査ログ」 | UC2 は act の連鎖を経路の証跡に挙げている（F5。監査ログも並べているので影響は小さい） |
| q-user・q-agent | — | sub、client_id・act | 合っている |
| q-still-valid（寿命） | lifetime-by-situation | ツールのトークン 300 秒＋重要な操作は aoba-pdp と approval-svc にその都度問い合わせる。長時間の処理は実行の時点で引き直す | 合っている |

## 段 3：優先 1 の問いへの答え（1 行ずつ）

- dc-05：Yes。authorization_details のメンバーはどれも文字列で、金額は 10 進の文字列、時刻は書式を 1 つに固定し、完全一致で比べる（台帳の description・value_normalization と、付録 D の P4 の 5.）。生成のスキーマがメンバーの型を表さないことは 3.1 に書かれ、共通の部品の試験で補う
- q-value-vocabulary：Yes。抜き取った 3 行はロール・グループではなく、採番する者の決まった不透明な ID と、組織の URI の type。aoba-as は名前空間の値を書かず、ロールは載せずに aoba-pdp が人事の台帳のコードから導く
- q-identifier-choice：Yes。利用者のキーは sub（UUID）だけで、identifier_properties と on_missing がある。社員番号はトークンに出さず、aoba-pdp の中で引くだけ
- ap-1-7：**No**。トークンに書くのは agent-sts だけだが、元の承認の記録・修繕依頼の台帳の担当と委任の欄は DB の管理者 2 人も直接書ける。予約の記録には実行の前の確かめがあるのに、すぐ使う承認の記録には無い（F1）
- q-freshness-mitigation：Yes。authorization_details の取り下げは、使うたびの条件つきの更新で即時に効く。担当の付け替えは、重要な操作なら aoba-pdp で 60 秒、下書き・連絡は 390 秒で止まり、どちらも REQ-08 の 120 秒・600 秒に収まる
- q-single-aud-resource：Yes。どの種別・ホップも aud は 1 つで、ツールはほかの値が並べば拒否する
- q-no-passthrough：Yes（ただし F3）。委任の表・クライアントごとのリソースの表・may_act で、頼める相手と宛先が決まっている。authorization_details を足すホップの warn の理由が、送り直しの経路と食い違う
- q-step-up-path-coverage：Yes。追加の認証が要るのは承認と手作業の事後の確認だけで、入口は approval-svc の 1 つ。エージェント・予約の経路から承認の操作には届かない（付録 B）
- ap-2-7：Yes。act の無いトークンでエージェントが持つのは 1 段目の REPAIR_DELEG_AT だけで、宛先は agent-sts だけ。交換で出るツールのトークンには必ず act が入る
- q-authorize-service-and-user：Yes。ツール・approval-svc・aoba-pdp は mTLS の相手を許可リストで照らし、利用者の権限とは別に判断する
- q-agent-short-lived-no-rt：Yes。agent-sts は RT を出さず、エージェントのトークンはどれも 300 秒以下
- q-outside-catalog：Yes。管理用の口・DB の管理者・試験の口（U30）・旧い経路（U29）・電話での手配・中間の CA の漏えいが、2.2・3.1・outside_enumeration で答えられている
- q-object-level-authz：Yes。agent-sts は修繕依頼の担当を、ツールは発注・部屋・連絡の相手を repair_id と台帳で照らす（M_authz_pdp の 3.）
- q-approval-from-as：Yes。agent-sts は承認の記録からだけ authorization_details を作り、locations の宛先にだけ載せる。受け手は approval-svc で条件つきで使用済みにする。記録そのものを書き換えられる者については F1
- q-operator-act：Yes。上長は自分の CONSOLE_AT で動き、代理ログインは作らない。運用者は監査ログに自分の sub が残り、DB の直接の書き込みは変更の記録に残る
- q-revocation-delivery：Yes。重要な操作は最悪 60 秒、下書き・連絡は 390 秒、委任の停止とログアウトは 330 秒、解錠コードの取り消しは目標 15 分。寿命の数字は 5.1 で分数から導かれている
- q-dependency-outage：**No**。止める操作も同じ依存先に頼っている。発行済みの解錠コードの取り消し（REQ-06 の 15 分）は agent-sts・aoba-as・aoba-pdp・approval-svc を通るが、それらが止まったときの代わりの手段が書かれていない（F2）

## 段 4：開いた問い

### op-proof-holder（鍵の持ち主を確かめる箇所）

辿った範囲：C-cnf の enforced_at（ツール 4 つ・approval-svc）、種別の holder・sender_constraint、3.1 の REPAIR_DELEG_AT と wl-ca の行、M_sender_constraint の 4.

| 箇所 | トークンを持つ者 | 鍵を持つ者 | 一致するか |
| --- | --- | --- | --- |
| ツール 4 つ（ORDER・CONTACT・PAYMENT・LOCK） | 交換を求めたエージェント | 交換に使った証明書（拇印を cnf に入れる）を持つ同じエージェント | 一致する |
| approval-svc（APPROVAL_AT） | repair-console | repair-console の証明書 | 一致する |
| agent-sts（REPAIR_DELEG_AT。束縛しない） | repair-agent・visit-subagent | may_act の URI を持つ証明書なら何でもよい（拇印でなく URI で照合する） | 鍵では照合していない |

- 証明書を更新するとき：古い組（証明書とトークン）は古い接続で使い切り、最悪 300 秒で終わる。cnf の食い違いは起きない
- 気づいたこと：REPAIR_DELEG_AT は鍵ではなく ID（URI）で守られている。3.1 は「may_act の主体の鍵が無ければ使えない」「トークンの要る口は開かない」と書くが、中間の CA の鍵が漏れれば偽の URI の証明書が作れる。設計は、エージェントの実行基盤からツールのトークンが漏れることを前提にしている。同じ基盤のメモリにある REPAIR_DELEG_AT も漏れれば、その残りの寿命（最悪 300 秒）のあいだ、ツールのトークンを交換で得られる（F4）

### op-source-change（異動でロールが外れる）

辿った経路：人事部の担当者が人事システムで登録する → 人事部の 2 人目が承認して確定する（REQ-08 の起点。登録から確定までの 2 時間は人事部の手順で、3.1 の見送り） → aoba-pdp が人事の台帳の API を引く（60 秒キャッシュ。sub から社員番号への対応は aoba-as の属性で引き、これも 60 秒キャッシュ） → agent-sts は交換ごとに、重要な操作のツールと approval-svc は呼び出しごとに aoba-pdp に問い合わせる。担当の付け替えは、課長が repair-console で行い、修繕依頼の台帳に履歴として追記される

- 元のデータを書き換えられる者：人事部の 2 人（人事システム）、課長（担当の割り当て）、hr-sync（aoba-as の社員番号の属性）、認証基盤チーム（aoba-pdp の導き方の規則。PR で 2 人の承認）、DB の管理者（5 つの DB）
- 誰も時間を約束していない区間は無い（登録から確定までは人事部が月 1 回報告する）。図に無い書き込みの経路は DB の管理者だけで、これは変更の記録と毎日の突き合わせで見る。すぐ使う承認の記録については F1
- 社員番号の対応が変わる出来事（作り直しなど）では、aoba-pdp の 2 つのキャッシュが重なり、最悪 120 秒になりうる。異動・退職では対応は変わらないので、REQ-08 には影響しない

### op-one-time（1 回だけ使える値）

辿った範囲：承認（発注・解錠・予約）、解錠コード、認可コード、ログアウトトークンの jti。付録 D の P4 の 5.、M_token_validation の 6.、3.1 の重複の行

- 並行の 2 件：承認は approval-svc の 1 つの原子的な条件つきの更新で使う。発注は発注の台帳の「下書き→確定」の条件つきの更新でも 1 回に絞る。同じ部屋の累計は、部屋の行を排他の錠で押さえて数える
- 通信が切れた後の再送：同じ発注 ID・同じ承認には前の結果が返る。lock-svc は承認 ID ごとにコードを 1 つだけ作り、通知の基盤は承認 ID と送信の回で重複を避ける。正しい 1 回は失われない（使用済み・未確定の承認は自動で戻さず、失効させて新しい発注 ID で依頼し直す）
- 記録先の障害：approval-svc が止まれば拒否し、承認は消費されない
- 気づいたこと：2 回通る経路は見つからなかった。ログアウトトークンの jti を「セッションの保存先」に 150 秒残すので、repair-console が複数の台で動いても共有される。再送で起きるのも、セッションを 2 回消すことだけ

## 段 5：優先 2 の問いと、さらにの開いた問い

- 優先 2 の 9 問：下の表（2）に答えた
- op-clock：時刻を比べる箇所は M_token_validation の 6. に挙がっている。ただし、H4・H10 の「REPAIR_DELEG_AT の iat（agent-sts の時計）と委任の世代の開始の時刻（修繕依頼の台帳の時計）の比較」が一覧に無い（F7）
- op-key-custody：aoba-as・agent-sts・wl-ca の鍵ごとに、持ち主・保管・漏えい時の手順と分数（15 分・60 分）が書かれている（M_token_validation の 8.）。指摘は無い
- op-requirement-words：「担当者」（社員・契約社員・派遣社員・休職中・退職の手続き中）と「上長」（課長以上・同じ課・職務代行）は 2.1 に区分がある。一方「取り下げ」（REQ-05）は、誰が取り下げてよいかが設計のどこにも無い（F6）

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | design.md 3.1 の見送りの行（approval-svc・発注の台帳・aoba-as の利用者・修繕依頼の台帳・協力会社の台帳の DB の管理者の直接の書き込み）、2.2 の「DB の管理」の行、claims.yaml の C-approval-ref・C-authorization-details の enforced_at（order-tool・lock-tool）と authoritative_writer、問い ap-1-7・q-approval-from-as | DB の管理者 2 人は承認の記録の状態を直接書き換えられる（例：承認待ちの 10 万円超の発注や解錠の依頼を「承認済み」にする）。order-tool・lock-tool・lock-svc は approval-svc の状態だけを見るので、偽の承認で確定・解錠コードの発行が通る。見つかるのは翌日の突き合わせで、そのときには解錠は済んでいる。3.1 は予約の記録について「翌日では遅い」として実行の前に変更の記録の表を確かめさせているが、同じ理由はすぐ使う承認の記録（解錠は物理の入室）にも当てはまるのに、確かめが無い。承認を与えてよい人に DB の管理者は入らない | Major | 理由の不備 | ap-1-7（registry:claims#provenance） |
| F2 | design.md 3.1 の見送りの行（頼る先が止まったときに通すこと）、4. の「agent-sts が頼る先が止まったとき」の表、3.1 の解錠コードを自動で止めない行、9.1 の承認の記録の行、REQ-06・REQ-13、問い q-dependency-outage | 依存先が止まると「止める側に倒す」と決めているが、その結果、止める操作も止まる。発行済みの解錠コードの取り消しは repair-console → agent-sts（aoba-as のイントロスペクション・aoba-pdp）→ approval-svc → lock-svc を通るので、どれかが止まると取り消せず、コードは not_after（最大 4 時間）まで使える。REQ-06 は取り消しから 15 分以内を求め、REQ-13 の電話の手順は新しい手配の代わりにしかならない。lock-svc を直接止める運用の口や手順の候補が書かれていない | Major | 候補の漏れ | q-dependency-outage（registry:claims#on_revoke、template:00_core#uncertain） |
| F3 | design.md 1. の warn の理由の表（L16 の hop H5・hop H8）、4. の「交換の要求の authorization_details」の行（送り直しの例外）、3.1 の重複の行（送り直しの LOCK_TOOL_AT）、claims.yaml の C-authorization-details の rationale・authoritative_writer、hops.yaml の H8 の added_claims・authorization_details、問い q-hop-narrowing | lint の L16 の warn（authorization_details の lock-code が上流の H4 に無い。下流で広げている）の理由は「agent-sts は承認済みの記録からだけ作る」「広がるのはその 1 回の解錠の分だけ」で、この根拠があるときだけ受け入れるとしている。一方、4. と 3.1 は、使用済みの承認からも送り直し用の LOCK_TOOL_AT を出す（最大 3 回）。warn を受け入れる条件と、実際に足す経路が食い違う。送り直しの経路を理由と台帳に書き足すか、理由の条件を直す | Minor | 実装とのずれ | q-hop-narrowing（lint:L16） |
| F4 | design.md 3.1 の REPAIR_DELEG_AT の送信者制約の見送りの行、wl-ca の中間の CA の鍵の漏えいの行、付録 D の M_token_validation の 8.（wl-ca）、token_types.yaml の REPAIR_DELEG_AT の note、claims.yaml の C-may-act の rationale、問い op-proof-holder・q-variant-comparison | 「漏れた REPAIR_DELEG_AT は may_act の主体の鍵が無ければ使えない」「トークンの要る口は開かない」と書くが、agent-sts は may_act を証明書の URI で照合し、拇印は見ない（クライアントの登録も許可リストも URI で持つ）。中間の CA の鍵が漏れて偽の URI の証明書が作れると、エージェントの基盤から漏れた REPAIR_DELEG_AT（基盤から漏れる前提は C-cnf の理由と同じ）で、残りの寿命（最悪 300 秒）のあいだツールのトークンを得られる。60 分の窓で開く口の一覧と、見送りの比較に、この組み合わせが入っていない | Minor | 前提の誤り | op-proof-holder、q-variant-comparison |
| F5 | design.md 6. の UC2 の q-via の行（仕組み「act の連鎖と交換の監査ログ」）、claims.yaml の C-act の note・not_meaning（内側の act は「どこを経由したか」の記録）、catalog_answers.yaml の questions.q-via の channel | act（入れ子を含む）は行為者を表す仕組みで、経路（どこを経由したか）の証跡ではない（contrasts/act-txn-workload の m-10）。UC1・UC3・UC4 は監査ログで答えているのに、UC2 だけ act の連鎖を q-via の仕組みに挙げている。agent-sts を経由したことなど、行為者でない経路は act に現れない。q-via の仕組みは交換の監査ログ（元の jti と出した jti）だけにし、act の連鎖は q-actor・q-audit-correlation の記録として扱うのがよい。監査ログも並べているので影響は小さい | Minor | 目的と仕組みの不一致 | q-via（contrasts/act-txn-workload#misuse の m-10）、q-audit-correlation |
| F6 | design.md 2.1 の主体の表（要求の言葉と区分）、REQ-05、claims.yaml の C-approval-ref・C-sub の approval-svc の enforced_at、H12 の validates、問い op-requirement-words | REQ-05 は「承認は使われる前なら取り下げられる」と求める。しかし、誰が取り下げてよいか（承認した上長だけか、依頼した担当者か、同じ課の課長か）が設計のどこにも無い。条件は承認・解錠の取り消し・事後の確認についてだけ書かれていて、approval-svc は取り下げを approval_ref の記録と repair_id の一致だけで許すように読める | Minor | 候補の漏れ | op-requirement-words |
| F7 | 付録 D の M_token_validation の 6.（時刻を比べるほかの箇所）、hops.yaml の H4・H10 の validates（REPAIR_DELEG_AT の iat が今の委任の世代の開始の時刻より後）、claims.yaml の C-repair-id の agent-sts の enforced_at、問い op-clock | 委任を止めて有効にし直す前の REPAIR_DELEG_AT を拒む判断は、agent-sts の時計で書いた iat と、修繕依頼の台帳が書いた世代の開始の時刻を比べる。別の時計の値を比べる箇所なのに、6. の一覧に無い。ずれたときに通すか止めるかも決まっていない。実際の窓は NTP のずれ（1 秒）程度で小さいが、世代の番号を REPAIR_DELEG_AT に載せて比べるなら、時計に依らない | Minor | 候補の漏れ | op-clock |

重大度ごとの件数：Blocker 0、Major 2、Minor 5

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| dc-05 | Yes | authorization_details のメンバーはどれも文字列で、書式を固定して完全一致で比べる。スキーマの限界は 3.1 で補う |
| q-value-vocabulary | Yes | 抜き取った 3 行は採番者の決まった ID と組織の URI の type。ロールは載せず aoba-pdp がコードで引く |
| q-identifier-choice | Yes | 利用者のキーは sub だけで、identifier_properties と on_missing がある |
| ap-1-7 | No | DB の管理者が承認の記録を直接書け、すぐ使う経路には実行の前の確かめが無い（F1） |
| q-freshness-mitigation | Yes | 取り下げは使うたびの条件つきの更新で即時。付け替えは 60 秒・390 秒で REQ-08 に収まる |
| q-single-aud-resource | Yes | どの種別・ホップも aud は 1 つで、ほかの値が並べば拒否する |
| q-no-passthrough | Yes | 委任の表・リソースの表・may_act で相手と宛先が決まる。warn の理由のずれは F3 |
| q-step-up-path-coverage | Yes | 追加の認証が要る操作の入口は approval-svc の 1 つで、ほかの経路から届かない |
| ap-2-7 | Yes | act の無いトークンは 1 段目の REPAIR_DELEG_AT だけで、宛先は agent-sts だけ |
| q-authorize-service-and-user | Yes | どの受け手も mTLS の相手を許可リストで照らし、利用者の権限とは別に判断する |
| q-agent-short-lived-no-rt | Yes | agent-sts は RT を出さず、エージェントのトークンは 300 秒以下 |
| q-outside-catalog | Yes | 管理の口・DB の管理者・U29・U30・電話の手配・中間の CA の漏えいに答えている |
| q-object-level-authz | Yes | agent-sts とツールが、修繕依頼・発注・部屋・相手を台帳と repair_id で照らす |
| q-approval-from-as | Yes | 承認の記録から作り、locations の宛先だけに載せ、受け手が条件つきで使う（記録の書き手は F1） |
| q-operator-act | Yes | 上長・運用者は自分の ID で動き、代理ログインは無い。DB の直接の書き込みは変更の記録に残る |
| q-revocation-delivery | Yes | 重要な操作 60 秒、下書き・連絡 390 秒、委任の停止 330 秒、解錠の取り消し 15 分。数字は分数から導いている |
| q-dependency-outage | No | 止める操作（解錠コードの取り消し）も依存先が止まると止まり、代わりが無い（F2） |
| op-proof-holder | 該当なし（開いた問い） | ツールと APPROVAL_AT では持つ者と鍵を持つ者が一致する。REPAIR_DELEG_AT は URI で照合する（F4） |
| op-source-change | 該当なし（開いた問い） | 人事の確定から aoba-pdp を経て受け手まで辿れた。時間を約束しない区間は無い（DB の管理者は F1） |
| op-one-time | 該当なし（開いた問い） | 並行・再送・障害のどれでも 2 回通らず、正しい 1 回も失われない |
| pa-01 | Yes | repair_id・approval_ref とも、どの受け手が何を照らすかが enforced_at に書いてある |
| q-derived-value | Yes | 個人情報の行は、要る受け手のトークンだけに載る（name は ID トークン、authorization_details は 2 つのツール） |
| q-variant-comparison | No | REPAIR_DELEG_AT の見送りの比較が「鍵が無ければ使えない」を前提にし、中間の CA の漏えいとの組を比べていない（F4） |
| q-idp-diff-absorbed | Yes | 内側の受け手には agent-sts のトークンだけが届き、aoba-as のトークンは受けない |
| q-original-principal | Yes | 交換の後も sub は担当者のままで、scope は aoba-pdp のロールで絞る |
| q-step-up-by-rs | Yes | 追加の認証を求めるかは、操作を受ける approval-svc が決める |
| q-long-running | Yes | 予約は実行の時点で、在籍・ロール・担当・委任の世代・承認を引き直す |
| q-copies-outlive | Yes | 予約の記録は実行の前に完全性と状態を確かめ、監査ログはハッシュで残し、aoba-pdp のキャッシュは 60 秒 |
| q-audit-correlation | Yes | sub・repair_id は同じ鍵のハッシュ、approval_ref と jti は値のままで、1 本につながる |
| op-clock | 該当なし（開いた問い） | 時刻を比べる箇所のうち、iat と委任の世代の開始の時刻の比較が一覧に無い（F7） |
| op-key-custody | 該当なし（開いた問い） | 3 つの鍵それぞれに、持ち主・保管・漏えい時の分数がある |
| op-requirement-words | 該当なし（開いた問い） | 「担当者」「上長」の区分はある。「取り下げ」をしてよい人が無い（F6） |

答えていない問い：無い（優先 2 の 9 問と、さらにの開いた問い 3 つにも答えた）。専門家に回す点（委任の深さ 2）は、書き手が 12. で回している。
