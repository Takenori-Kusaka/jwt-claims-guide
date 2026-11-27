# レビュー：designs/target（あおば住まいサービス 修繕の手配）

- 対象：designs/target/design.md（1.0）と claims.yaml・token_types.yaml・hops.yaml・catalog_answers.yaml・claim_request_*.md・schemas/
- 使った資料：sheet.md（行の抜き取りの種 12）、ci-result.txt、short_list.md、perspectives.md、decision_tree.md、contrasts/、kind_tell.md
- 結果の要約：指摘 7 件（Blocker 0・Major 2・Minor 5）。「目的と仕組みの不一致」は 0 件

## 段 0：受け付け（lint の結果）

- ci-result.txt と design.md の 1. は一致している：error 0、warn 2、info 24
- warn 2 件（L16 の H5・H8。authorization_details が上流の H4 に無い）には、design.md の 1. に行ごとの理由がある。ただし理由の書き方に弱いところがある（指摘 F3）
- 検査を通すために宣言を曲げた跡（上流を外す・名前を変える・数値を上限に合わせる）は見つからなかった。H13・H14 は upstream が無いが、トークンを運ばないホップで、3. に理由を書いている

## 段 1：性質の表の確かめ（12.・2.・6. と図・要求で照合）

| 性質 | sheet.md | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 当たる：C-repair-id・C-approval-ref（名前空間 https://aoba-sumai.example/claims/） |
| 個人情報を載せる | 当たる | 当たる：sub・repair_id・authorization_details（部屋と時間帯）・name |
| 発行者が複数 | 当たる | 当たる：aoba-as と agent-sts（2. の図） |
| 交換・作り直し | 当たる | 当たる：H3・H5〜H9・H11・H12 |
| 委任 | 当たる | 当たる：repair-agent → visit-subagent（深さ 2。REQ-03・REQ-04） |
| 操作ごとの承認 | 当たる | 当たる：REQ-05・REQ-06、authorization_details と approval_ref |
| マルチテナント | 当たらない | 当たらない：組織は 1 つで、オーナーごとにデータを分けない（catalog_answers の lite_criteria）。図にもテナントの境界は無い |
| DB の層まで運ぶ | 当たらない | 当たらない：発注の台帳には order-tool・order-scheduler が自分の DB アカウントでつなぐ（2. の範囲の表のデータ層の行） |
| 認証の強さ・新しさ | 当たる | 当たる：REQ-07、acr・auth_time |
| 送信者制約を選んだ | 当たる | 当たる：ツールのトークン 4 種と APPROVAL_AT が mTLS |
| 送信者制約を見送った | 当たる | 当たる：CONSOLE_AT・CONSOLE_RT・REPAIR_DELEG_AT |
| 長時間・非同期 | 当たる | 当たる：REQ-10 の予約の発注（H13・H14） |

「当たらない」とされた性質が実際にある、という食い違いは無かった。抜き取った行（C-approval-ref・C-repair-id・C-authorization-details）は、どれも認可・識別子に使う行。名前空間つきで usage が authz の行は無い（C-approval-ref は q-authorized に答えるのに usage が identifier だが、すでに抜き取りに入っているので、答える問いには影響しない）。

## 段 2：6. で「要る」とした問いと、判断の木の節

| 問い（ユースケース） | 判断の木の節 | 設計の仕組み | 比べた結果 |
| --- | --- | --- | --- |
| q-sub（UC1〜UC3） | keep-sub-exchange | 交換で sub を写し（要求の値で差し替えない）、act にエージェント | 合う |
| q-sub（UC4 予約の実行） | keep-sub-exchange（非同期ではワーカーが自分の ID で交換し直し、AS が決める） | 交換せず、order-scheduler が予約の記録の sub で aoba-pdp・修繕依頼の台帳・approval-svc を引き直す | 木の既定から外れるが、3. と 3.1 に、外す理由・同じ項目を確かめること・試験の方法が書いてある。答える問いは同じ（実行の時点で、利用者の権限を確かめ直す）ので、不一致にはしない |
| q-actor（UC1・UC2） | keep-sub-exchange の「最も外側の act か」 | ツールは最も外側の act.sub を mTLS の相手と許可リストに照らす。内側の act は記録だけ（C-act の enforced_at、H6・H11 の validates） | 合う。入れ子の act を許可に使う箇所は無い |
| q-actor（UC3・UC4） | keep-sub-exchange | 承認は act が無く client_id が repair-console であること。予約の実行は order-scheduler の証明書と、予約の記録の act の連鎖 | 合う |
| q-peer（全 UC） | peer-mtls | wl-ca の証明書の mTLS（URI の SAN）。トークンのクレームで代えていない | 合う |
| q-txn（UC1〜UC4） | txn-tctx | repair_id（相関の ID と対象の照合）。取引の内容は authorization_details と承認の記録で固定。Txn-Token は却下 | 木の「内容を経路全体で固定」は、承認の記録と authorization_details の照合で答えている。ツールの先にトークンを渡す連鎖が無いという却下の理由も通る（contrasts/act-txn-workload） |
| q-authorized（UC1・UC3・UC4） | rar-vs-custom | 取引の承認は authorization_details（type は組織の URI、宛先ごとに 1 つ）、操作の粗い範囲は scope、状態は approval-svc に問い合わせる | 合う。scope と併用するが、何をどちらで決めるかは C-scope と C-authorization-details の enforced_at に書いてある |
| q-authorized（UC2） | rar-vs-custom | scope だけ（連絡は承認が要らない） | 合う |
| q-resource（全 UC） | （木に節なし。registry の q-resource） | aud は 1 つ。UC4 は呼ばれる側の許可リスト | 合う |
| q-holder（UC1〜UC3） | existing-claim-first（cnf） | cnf の x5t#S256。REPAIR_DELEG_AT は may_act と mTLS の相手の照合 | 合う（contrasts/signed-vs-enforced の観点でも、照合する受け手が enforced_at にある） |
| q-via・q-user・q-agent | （木に節なし） | 交換の監査ログと act の連鎖、sub のハッシュ、client_id と act | 合う |
| 承認の要否（部屋の累計） | carry-or-query | 載せずに order-tool が発注の台帳で数える（C-order-limit は却下） | 節の選び方は合う。ただし数え方が並行の要求に効かない（指摘 F2） |

## 段 3：優先 1 の問いへの答え（1 行ずつ）

- dc-05：Yes。authorization_details のメンバーはすべて文字列で、正規表現・NFC・完全一致が決まっている。スキーマで表せない点は 3.1 で共通の検証部品の試験に回している
- q-value-vocabulary：Yes。ロールは載せず aoba-pdp で引く。type の URI と ID は語彙と持ち主が決まっている
- q-identifier-choice：Yes。利用者のキーは aoba-as の sub（UUID）だけで、identifier_properties と on_missing がある
- ap-1-7：Yes（条件つき）。repair_id は agent-sts が台帳を確かめて書き、approval_ref と authorization_details は approval-svc の記録から作る。DB の管理者の直接の書き込みは 3.1 で、事後に検出する。ただし、担当を書く経路が設計書に無い（指摘 F5）
- q-freshness-mitigation：Yes。3 行とも寿命の間に値は変わらない。承認の取り下げは、受け手が approval-svc で条件つきの更新をして 0 秒で効く
- q-single-aud-resource：Yes。どの種別・ホップも aud は 1 つで、ツールは配列にほかの値があれば拒否する
- q-no-passthrough：Yes。交換できるのは agent-sts だけで、委任の表とクライアントごとのリソースの表で、相手と宛先が決まっている
- q-step-up-path-coverage：Yes。承認の操作の口は APPROVAL_AT だけ（act なし・repair-console 限定）。エージェントの経路と予約の経路は承認の記録を使い、承認には届かない
- ap-2-7：Yes。エージェントが持つ act の無いトークンは 1 段目の REPAIR_DELEG_AT だけで、宛先は agent-sts だけ。交換すると必ず act が付き、approval-svc 宛てはリソースの表に無い
- q-authorize-service-and-user：Yes。どのホップも mTLS の相手を許可リストで確かめ、利用者の権限（aoba-pdp）とは別に判断している。ただし CA の鍵が漏れたときの見積もりが誤っている（指摘 F1）
- q-agent-short-lived-no-rt：Yes。agent-sts は RT を出さない。エージェントのトークンは 300 秒で、手順ごとに交換し直す
- q-outside-catalog：No。管理用の口・試験用の口・旧経路・障害時の手作業は答えている。しかし、修繕依頼の担当を割り当てる・付け替える経路（9.2 と 2.2 に書いてある）が、図にも範囲の表にも無い（指摘 F5）
- q-object-level-authz：Yes。他人の修繕依頼は agent-sts で、他人の発注は order-tool・payment-tool で 404、部屋は lock-tool で 403、承認は記録の照合で止まる（M_authz_pdp の 3.）
- q-approval-from-as：Yes。agent-sts は承認済みの記録からだけ authorization_details を作り、locations と同じ宛先にだけ載せる。受け手は、記録を条件つきで使用済みにすることで照合する
- q-operator-act：Yes。上長は自分のログインで担当を付け替えて操作する。代理ログインは作らない。設定は PR で変える。DB の管理者は変更の記録で見分ける
- q-revocation-delivery：Yes。重要な操作は 60 秒（aoba-pdp）、下書き・連絡は 390 秒、委任の停止は 330 秒、予約は実行の時点で確かめる。寿命の数字は 5.1 で REQ-08・REQ-09 から導いている
- q-dependency-outage：Yes。頼る先ごとに止める側に倒すことが 4. と 3.1 に書いてあり、REQ-13 の 60 分と警報の 5 分に合わせている

## 段 4：開いた問い

### op-proof-holder（鍵の持ち主）

- 辿った範囲：トークンを持つ者と、鍵を持つ者を箇所ごとに並べた。ORDER_TOOL_AT・PAYMENT_TOOL_AT・LOCK_TOOL_AT は repair-agent と repair-agent。CONTACT_TOOL_AT は交換を求めた repair-agent か visit-subagent で、それぞれ同じ。APPROVAL_AT は repair-console と repair-console。REPAIR_DELEG_AT は束縛しないが、agent-sts が may_act.sub と mTLS の相手を照合する（1 段目は repair-agent、2 段目は visit-subagent。2 段目を求めた repair-agent 自身は交換できない）。証明書の更新は M_sender_constraint の 4.（証明書とトークンを組で持つ）で扱っている
- 気づいたこと：どの箇所も、確かめる側が見ている鍵は、実際に持つ者の鍵だった。ただし、may_act は証明書の拇印でなく URI の SAN で照合している。そのため、中間の CA の鍵が漏れたときに URI をまねた証明書でも通る。加えて、トークンを使わずに mTLS だけで受ける口（lock-svc・通知の基盤・approval-svc の使用済みの口・aoba-pdp・修繕依頼の台帳）が多い。付録 D の wl-ca の行の「何も呼べない」という見積もりは、この口を数えていない（指摘 F1）

### op-source-change（権限の元データの変化）

- 辿った範囲 1（退職・異動）：人事部の担当者と承認者の 2 人の手順で人事の台帳に確定する → aoba-pdp が人事の台帳の API を直接読む（60 秒キャッシュ。sub と社員番号の対応は hr-sync だけが書く aoba-as の属性）→ 重要な操作のツールと approval-svc は呼び出しのたびに問い合わせる（最悪 60 秒）。agent-sts は交換のたびに問い合わせる（下書き・連絡は最悪 390 秒）。並行して、hr-sync が 5 分ごとに aoba-as の利用者を無効にし、ログアウトトークンで BFF のセッションを消す。この経路は判断に入らないと明記してある。誰も時間を約束していない区間は見つからなかった
- 辿った範囲 2（担当の付け替え）：9.2 では「修繕課の課長が修繕依頼の台帳で割り当てる」、2.2 では「上長が担当を自分に付け替える」と書いてある → aoba-pdp（60 秒）と agent-sts（キャッシュなし）が引く
- 気づいたこと：担当の書き込みは、REQ-05（上長はその修繕依頼の担当でない）と REQ-06（担当者本人の承認）の元データなのに、どの画面・API・認証で書き、どこに記録が残るかが、2. の図・範囲の表・2.2 に無い。2. の範囲の表では、修繕依頼の台帳の書き込みの API として、repair-console が書く委任の欄しか挙げていない（指摘 F5）

### op-one-time（1 回だけ使える値）

- 辿った範囲：発注の承認、解錠の承認、ログアウトトークンの jti、認可コード、予約の実行
  - 並行の 2 件：同じ発注 ID なら、approval-svc は 2 件目に前の結果を返す。そのうえで、発注の台帳の「下書き→確定」の条件つきの更新で 1 件だけが確定する。別の発注 ID なら、2 件目は使用済みにする更新に失敗する
  - 通信が切れた後の再送：同じ発注 ID・同じ承認で再試行すれば、1 回だけ実行される。承認を自動で未使用に戻さないので、確定しなかった発注は上長が承認し直す（P4 の 5.）
  - 記録先の障害：approval-svc が止まれば拒否する。予約の実行は、どれかが通らなければ予約を取り消して担当者に知らせる
- 気づいたこと
  - 承認の要否を決める「部屋の直近 30 日の累計」は、確定のたびに読むだけで、同じ部屋の確定・予約を直列にしていない。10 万円以下の発注 2 件を並行に確定すると、どちらも承認なしで通る（指摘 F2）
  - 解錠では、重複を防ぐのは lock-svc が承認 ID を重複の鍵として受けることに頼っている。lock-svc は下流の仕組みなので、この前提は 12. に無い。また、コードを作った後に通知が失敗したときの扱いも書いていない（lock-tool はコードを保存しない）。正しい 1 回を失うか、2 つ目のコードを出すおそれがある（指摘 F6）
  - 一時的な障害で予約を取り消すと、承認は予約済みのまま戻らないので、上長の承認し直しが要る。業務への影響は REQ-13 で受けられる範囲で、指摘にはしない

## 段 5：優先 2 の問い（時間があれば）

9 問すべてに答えた（下の表 (2)）。pa-01 で、台帳と 25 問の回答の小さな食い違いを見つけた（指摘 F7）。さらにの開いた問い（op-clock・op-key-custody・op-requirement-words）は辿っていない。ただし op-key-custody の範囲は、指摘 F1 で一部に触れた。

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | design.md 付録 D の M_token_validation の 8.（`#profile-fill-ins`）の wl-ca の行、3.1（`#priorities-deferrals`）の「wl-ca の証明書の失効の確かめ」の見送りの行、catalog_answers.yaml の U12。問い：q-authorize-service-and-user・op-proof-holder・op-key-custody | 中間の CA の鍵が漏れたとき「偽の証明書でも REPAIR_DELEG_AT かツールのトークンを持たなければ何も呼べない」と書いてある。しかし、lock-svc・通知の基盤・経理の仕組み・approval-svc の承認の依頼と使用済みの口・aoba-pdp・修繕依頼の台帳の委任の欄の書き込みは、トークンを使わず、呼び出し元の証明書の許可リストだけで受ける（2. の図の「mTLS だけ」、U12）。偽の証明書で lock-tool や repair-console になりすませば、解錠コードの作成・SMS の送信・委任の欄の書き換えに直接届く。agent-sts の may_act も、拇印でなく URI で照合する。3.1 の失効の見送りも、エージェントのトークンが 330 秒で切れることだけを費用の根拠にしていて、この口を数えていない。目標の 60 分の間に何が開くかの見積もりを直し、それでも OCSP・失効リストを見送るかを決め直す必要がある | Major | 前提の誤り | op-key-custody、q-authorize-service-and-user |
| F2 | hops.yaml の H5 の validates（「確定・予約では発注の台帳で部屋の直近 30 日の累計を数え…」）、design.md 3.1 の重点「承認の要否を、部屋ごとの累計で決める」の行と確かめ方、REQ-05。問い：op-one-time | 承認の要否は、確定・予約のたびに累計を読んで決める。しかし、同じ部屋の確定・予約を直列にする仕組み（部屋ごとの錠、累計の行に対する条件つきの更新など）が無い。累計 0 円の部屋で 6 万円の発注 2 件を並行に確定すると、どちらも「10 万円以下」と読んで、承認なしで計 12 万円が確定する。エージェントは手順を並行に進めうる。3.1 の確かめ方（「分けた 2 件目で承認を求めること」）は、順に送る場合しか試さない。REQ-05 の分割の防止が、並行の要求では効かない | Major | 候補の漏れ | op-one-time |
| F3 | design.md 1.（`#ci-results`）の warn の理由の表（L16 の hop H5・H8）、hops.yaml の H5・H8 の authorization_details。lint:L16 が答えを決める問い：q-hop-narrowing | warn の理由に「足すのは…制限で、範囲を広げるものではない」とある。しかし H5 の authorization_details（vendor-order）は、それが無ければ拒否される 10 万円超の確定を通すための値で、トークンでできることを上流（H4）より広げている。H8 の lock-code も、発行を可能にする値。広げてよい根拠は、上流でなく approval-svc の人の承認の記録が別の権限の元であることと、受け手が approval-svc で使用済みにして確かめること。理由をその形に直さないと、「下流ほど絞る」の例外として後の読み手が一般化してしまう | Minor | 理由の不備 | q-hop-narrowing（lint:L16） |
| F4 | claims.yaml の C-sub と C-repair-id の enforced_at（service: agent-sts）と、C-repair-id の authoritative_writer・rationale。比べた箇所：design.md 4.（`#issuance-profile`）の CONSOLE_AT の交換の行、hops.yaml の H12 の added_claims、token_types.yaml の APPROVAL_AT の note | 台帳では、agent-sts はどの交換でも「修繕依頼の台帳で修繕依頼の担当が sub（で委任の欄が有効）」を確かめる、と書いてある。しかし H12 で APPROVAL_AT を求めるのは上長で、上長は REQ-05 によりその修繕依頼の担当ではない。台帳のとおりに作ると、上長の承認の交換が必ず拒否される。4. と H12 は、承認の記録があること・担当者か上長であることを確かめる、という別の条件を書いている。また C-repair-id の authoritative_writer は「APPROVAL_AT では承認の記録の値」だが、参照だけの APPROVAL_AT（承認の記録が無い）では画面で開いた修繕依頼の値で、ここも食い違う。判断の正は台帳なので、enforced_at を交換の種類ごとに分けて書く必要がある | Minor | 実装とのずれ | q-sub |
| F5 | design.md 2.（`#scope-boundary`）の図と範囲の表（修繕依頼の台帳の行）、2.2（`#system-privileges`）の「運用者の操作（上長の引き継ぎ）」の行、9.2（`#freshness`）の「元のデータからの経路」。問い：q-outside-catalog・ap-1-7・op-source-change | 修繕依頼の担当は、REQ-05（上長は担当でない）・REQ-06（担当者本人が承認）・agent-sts の交換・aoba-pdp の判断の元データ。9.2 は「修繕課の課長が修繕依頼の台帳で割り当てる」、2.2 は「上長が担当を自分に付け替える」と書く。しかし、その書き込みをどの画面・API・認証（どのトークンか、mTLS だけか）で行い、記録がどこに残るかは、図にも範囲の表にも無い。範囲の表では、修繕依頼の台帳の書き込みの API として、委任の欄（repair-console）しか前提にしていない。課長が自分を担当にすれば、解錠をひとりで承認できる（REQ-06 の上では許される）。そのため、書ける人の範囲と記録は、この設計の前提として書いておく必要がある | Minor | 候補の漏れ | q-outside-catalog、ap-1-7 |
| F6 | design.md 付録 D の P4 の 5.「消費の競合と再送」の行、3.1 の重点「重複の実行を、業務の ID で防ぐ」の行、12.（`#uncertain`）、claims.yaml の C-unlock-code の assumption。問い：op-one-time | 解錠の「1 回だけ」は、lock-svc が承認 ID を重複を避ける鍵として受けることに頼っている。しかし lock-svc は下流の仕組み（2. の範囲の外の別の部品）で、この挙動を確かめたことが 12. に無い。また、lock-svc がコードを作った後に、通知の基盤への送信が失敗したり結果が分からなかったりしたときの扱いが無い。lock-tool はコードを保存せず、承認はすでに使用済みになっている。この場合、同じ承認で再試行して lock-svc が同じコードを返すのか、作り直すのか（2 つ目のコードになる）、何も返さないのか（作業員にコードが届かず、正しい 1 回を失う）が決まっていない。REQ-06 の「承認ごとに 1 回だけ発行」と「作業員にだけ届ける」に関わる | Minor | 候補の漏れ | op-one-time |
| F7 | claims.yaml の C-repair-id の consumers（aoba-pdp を含む）と enforced_at（service: aoba-pdp）、carried_in。claim_request_repair_id.md の問 22。問い：pa-01 | C-repair-id の consumers と enforced_at に aoba-pdp があるが、aoba-pdp に repair_id を載せたトークンは届かない（carried_in のどの種別も aoba-pdp に行かない。H13 で order-scheduler が予約の記録の値を渡すだけ）。25 問の問 22 の受け手にも aoba-pdp は無い。「クレームを読んで判断する受け手」と「記録の写しを受ける呼ばれる側」が混ざっていて、受け手の一覧と検証部品の配布範囲（付録 D の M_token_validation の 11.）がずれる | Minor | 実装とのずれ | pa-01 |

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| dc-05 | Yes | authorization_details のメンバーはすべて文字列で、正規表現・NFC・完全一致が決まり、型の検査は共通部品の試験に回してある |
| q-value-vocabulary | Yes | ロールは載せず aoba-pdp で引く。type の URI・ID は語彙と持ち主が固定されている |
| q-identifier-choice | Yes | 利用者のキーは aoba-as の sub（UUID）だけで、identifier_properties と on_missing がある |
| ap-1-7 | Yes | 3 行の値は agent-sts が台帳・承認の記録から書き、DB の管理者は事後に検出する。ただし担当を書く経路が未記載（F5） |
| q-freshness-mitigation | Yes | 3 行とも寿命の間に変わらず、承認の取り下げは条件つきの更新で 0 秒で効く |
| q-single-aud-resource | Yes | どの種別・ホップも aud は 1 つで、ツールは配列のほかの値を拒否する |
| q-no-passthrough | Yes | 交換できるのは agent-sts だけで、委任の表とリソースの表で相手と宛先が決まる |
| q-step-up-path-coverage | Yes | 承認の口は APPROVAL_AT だけで、エージェントの経路・予約の経路は承認に届かない |
| ap-2-7 | Yes | act の無いトークンは 1 段目の REPAIR_DELEG_AT だけで、宛先は agent-sts。交換すると必ず act が付く |
| q-authorize-service-and-user | Yes | どのホップも mTLS の相手を許可リストで確かめている（CA の鍵が漏れたときの見積もりの誤りは F1） |
| q-agent-short-lived-no-rt | Yes | agent-sts は RT を出さず、エージェントのトークンは 300 秒で手順ごとに交換する |
| q-outside-catalog | No | 担当の割り当て・付け替えの書き込みの経路が、図・範囲の表に無い（F5） |
| q-object-level-authz | Yes | 修繕依頼・発注・部屋・承認ごとに、止める受け手と応答が M_authz_pdp の 3. にある |
| q-approval-from-as | Yes | agent-sts が承認済みの記録から作り、locations の宛先だけに載せ、受け手が使用済みにして照合する |
| q-operator-act | Yes | 代理ログインは無く、上長は自分の sub で操作し、設定は PR、DB の管理者は変更の記録で見分ける |
| q-revocation-delivery | Yes | 重要な操作は 60 秒、下書き・連絡は 390 秒、委任の停止は 330 秒で、REQ-08・REQ-09 の内側 |
| q-dependency-outage | Yes | 頼る先ごとに止める側に倒すことが 4. と 3.1 にあり、REQ-13 の 60 分と警報の 5 分に合う |
| op-proof-holder | 該当なし（開いた問い） | 持つ者と鍵の持ち主はどの箇所も一致する。CA の鍵の漏えいの見積もりに誤りがある（F1） |
| op-source-change | 該当なし（開いた問い） | 退職は時間が約束されている。担当の書き込みの経路が未記載（F5） |
| op-one-time | 該当なし（開いた問い） | 承認の消費は 1 回になる。累計の並行（F2）と、解錠の lock-svc の前提と通知の失敗（F6）が未対処 |
| pa-01 | Yes | 25 問の問 1 と usage で受け手ごとの用途が言える（consumers の aoba-pdp だけがずれる。F7） |
| q-derived-value | Yes | 個人情報の行（sub・repair_id・authorization_details）は、届く受け手がどれも照合に使い、連絡先・住所は載せない |
| q-variant-comparison | Yes | 送信者制約・予約・JWKS の見送りに、開く攻撃・代わりの守り・確かめ方・見直しの条件がある |
| q-idp-diff-absorbed | Yes | 発行者は組織の 2 つだけで、ツールは agent-sts のトークンだけを受ける |
| q-original-principal | Yes | 交換で sub を保ち、scope を上流・宛先・aoba-pdp のロールの積に絞る |
| q-step-up-by-rs | Yes | 追加の認証を求めるかは approval-svc が acr・auth_time で決め、401 と RFC 9470 の応答を返す |
| q-long-running | Yes | 予約はトークンを持ち越さず、実行の時点で在籍・ロール・担当・委任・承認を引き直す |
| q-copies-outlive | Yes | 予約の記録の写しは実行の時点で確かめ直し、aoba-pdp のキャッシュは 60 秒、監査ログはハッシュで残す |
| q-audit-correlation | Yes | 全サービスが同じ鍵・同じ正規化のハッシュの sub・repair_id と、値のままの approval_ref・発注 ID・jti で結ぶ |
