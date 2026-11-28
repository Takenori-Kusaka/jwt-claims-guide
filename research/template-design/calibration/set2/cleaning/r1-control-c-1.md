# レビューの記録：designs/target（あおば住まいサービス 修繕の手配）

- 対象：designs/target/design.md と claims.yaml・token_types.yaml・hops.yaml・catalog_answers.yaml・claim_request_*.md・schemas/
- 使った 1 枚：sheet.md（行の抜き取りの種は 12。抜き取った行は C-approval-ref・C-repair-id・C-authorization-details。組織独自の認可の行（名前空間つきで usage が authz）は無い）
- 読んだ教材：short_list.md、perspectives.md（問いの書き方と読み方）、kind_tell.md、decision_tree.md
- CI（ci-result.txt と設計書の 1.）：error 0、warn 2（L16、hop H5・H8 の authorization_details が上流に無い）。warn には 1. に行ごとの理由がある。理由（承認の記録から 1 件の操作に絞った内容を足すもので、範囲を広げない。上流の時点では承認が無い）は通ると判断し、指摘にしない

## 段 1：性質の表を図と要求に照らす

| 性質 | sheet.md | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 合う（repair_id・approval_ref が名前空間つき） |
| 個人情報 | 当たる | 合う（C-sub・C-repair-id・C-authorization-details・C-name が個人情報） |
| 発行者が複数 | 当たる | 合う（aoba-as と agent-sts。どちらも組織の自作） |
| 交換・作り直し | 当たる | 合う（H3・H5〜H9・H11・H12 が exchange） |
| 委任 | 当たる | 合う（act・may_act、深さ 2） |
| 操作ごとの承認 | 当たる | 合う（vendor-order・lock-code の 2 つの type。1 つの操作に結ぶ承認） |
| マルチテナント | 当たらない | 合う。組織は 1 つで、物件の持ち主ごとにデータを分けない（2. の図・REQ にもテナントの区分は無い） |
| トークンの値を DB の層まで | 当たらない | 合う。発注の台帳には order-tool・order-scheduler が自分の DB アカウントで接続し、トークンの値を DB の文脈に注入しない（2. の「データ層」の行） |
| 認証の強さ・新しさ | 当たる | 合う（acr・auth_time。REQ-07） |
| 送信者制約を選んだ・見送った | 当たる・当たる | 合う（ツールのトークン 4 種と APPROVAL_AT は mtls。CONSOLE_AT・CONSOLE_RT・REPAIR_DELEG_AT は none） |
| 長時間・非同期 | 当たる | 合う（予約の発注。REQ-10、H13・H14） |

「当たらない」とされた性質が実際にある箇所は見つからなかった。足す問いは無い。

## 段 2：6. の「要る」問いと判断の木

| UC | 問い | 木の節 | 設計の仕組み | 比べた結果 |
| --- | --- | --- | --- | --- |
| UC1・UC2 | q-sub | keep-sub-exchange | 交換で sub を保ち、agent-sts・重要な操作のツールが aoba-pdp に問い合わせる | 合う |
| UC1・UC2 | q-actor | keep-sub-exchange | 最も外側の act.sub を mTLS の相手と照合し、操作ごとの許可リスト。内側の act は記録だけ（C-act の enforced_at、H5〜H8・H11 の validates） | 合う（入れ子の act を許可に使っていない） |
| UC1〜UC4 | q-peer | peer-mtls | wl-ca の証明書の mTLS（URI の SAN）。end_to_end | 合う |
| UC1〜UC3 | q-via | （ネストした act） | act の連鎖と交換の監査ログ（元の jti と出した jti） | 合う |
| UC1・UC2 | q-txn | txn-tctx | repair_id（独自）。Txn-Token は却下 | 合う。木の問い「1 つの呼び出しの連鎖の中で取引の内容を固定したいか」は「いいえ」（ツールの先に連鎖が無い）。取引の内容の固定は authorization_details が担う |
| UC3 | q-txn | txn-tctx | APPROVAL_AT の repair_id を、approval-svc が承認の記録と照合 | 合わない（指摘 F6）。トークンの repair_id は同じ承認の記録から写した値で、照合が何も確かめない |
| UC4 | q-sub・q-actor | keep-sub-exchange | 交換し直さず、order-scheduler が判断の元の記録を直接引き直す（3. の既定から外れた点に書いてある） | 利用者の側の確かめは合う。行為者（予約したエージェント）の側の確かめが抜けており、3.1 の理由「AS が確かめる項目と同じ」が成り立たない（指摘 F4） |
| UC1・UC3・UC4 | q-authorized | rar-vs-custom（承認）／carry-or-query（scope） | scope は操作の種類、authorization_details は承認した 1 件の内容、approval_ref は承認の記録の鍵。併用の分担は台帳に書いてある | 合う |
| 全 UC | q-resource | — | aud 1 つ（ツールごとに種別を分ける） | 合う |
| UC1〜UC3 | q-holder | existing-claim-first（cnf） | cnf の x5t#S256 | 合う |
| UC4 | q-holder（不要） | — | 予約の記録を書けるのは order-tool の DB アカウントだけ（integrity_until） | 前提の書き方が 3.1・2.2 と食い違う（指摘 F5） |
| — | q-still-valid | lifetime-by-situation | 剥奪を急ぐ操作は短命＋都度判定（aoba-pdp・approval-svc）、エージェントは RT なし | 合う。ただし剥奪の起点の扱い（指摘 F3） |

## 段 3：優先 1 の問いへの答え

答えは末尾の表 (2) にまとめた。No の問いはすべて指摘にした。

## 段 4：開いた問いを辿る

### op-proof-holder（鍵の持ち主を確かめる箇所）

- 辿った範囲：C-cnf の enforced_at（ツール 4 つ・approval-svc）、token_types の holder・sender_constraint、付録 D の M_sender_constraint の 4.、M_token_validation の 8.（wl-ca）、C-may-act の enforced_at、3.1 の REPAIR_DELEG_AT の見送りの行
- 箇所ごとの「トークンを持つ者」と「鍵を持つ者」：ORDER・PAYMENT・LOCK_TOOL_AT は repair-agent／repair-agent、CONTACT_TOOL_AT は交換を求めた repair-agent か visit-subagent／同じ者、APPROVAL_AT は repair-console／repair-console。どれも一致する。証明書の更新では、aoba-agent-kit が証明書とトークンを組で持ち、古い組を古い接続で使い切る（最悪 300 秒）ので、cnf の食い違いは起きない
- 気づいたこと：REPAIR_DELEG_AT の交換で agent-sts が見ているのは may_act.sub と mTLS の相手の証明書の **URI**（名前）で、鍵の拇印ではない。3.1 の見送りの行は「漏れた REPAIR_DELEG_AT は may_act の主体の**鍵**が無ければ使えない」と書くが、実際には「wl-ca がその URI で出した証明書なら誰の鍵でもよい」。普段は同じことだが、M_token_validation の 8. の wl-ca の中間の CA の鍵の漏えい（最大 60 分で入れ替え）の間は、偽の証明書と、エージェントの実行基盤から漏れた REPAIR_DELEG_AT の組でツールのトークンを得られる。8. の「REPAIR_DELEG_AT かツールのトークンを持たなければ何も呼べない」はこの組を数えていない。指摘にはしない（wl-ca の漏えいと REPAIR_DELEG_AT の漏えいの両方が要る）が、3.1 の言い方を「may_act の URI の証明書が無ければ」に直すと読み違いが減る

### op-source-change（権限の元データが変わる出来事）

- 選んだ出来事：退職（REQ-08）と、修繕依頼の担当の付け替え
- 辿った範囲：9.2 の「元のデータからの経路」、9.2 の表、2.2 の人事連携と運用者の操作の行、C-sub の source_system、REQ-08
- 退職：人事部の担当者が人事システムで登録 → 人事部の承認者がもう 1 人で承認して確定 → aoba-pdp が確定した値を人事の台帳の API で読む（キャッシュ 60 秒）→ 重要な操作のツールが呼び出しのたびに aoba-pdp に問い合わせる。並行して hr-sync が 5 分ごとに aoba-as の利用者を無効にし、Back-Channel Logout で BFF のセッションを消す
- 気づいたこと 1：REQ-08 の時間は「人事の台帳に**登録してから**」2 分・10 分。設計の経路は、確定（2 人目の承認）の後の値だけを読む。登録から確定までの区間は、誰も時間を約束していない（人事システムの手順は別の設計書）。→ 指摘 F3
- 担当の付け替え：「修繕課の課長が修繕依頼の台帳で割り当てる」（9.2）、「上長は担当を自分に付け替えてから自分の権限で操作する」（2.2）。aoba-pdp と agent-sts は台帳の今の担当を直接引くので、時間は 60 秒・0 秒で収まる
- 気づいたこと 2：担当を書ける人（課長＝上長）が、10 万円を超える発注の承認者でもある。承認の時点の「担当でないこと」だけを見るので、付け替えを挟めば自分の発注を自分で承認できる。→ 指摘 F1

### op-one-time（1 回だけ使える値）

- 辿った範囲：付録 D の P4 の 5.（消費の競合と再送）、M_token_validation の 6.、3.1 の重点（重複の実行を業務の ID で防ぐ・累計で決める）、C-approval-ref の enforced_at、H5・H8・H13・H14 の validates、2.2 の予約の実行の行
- 承認：approval-svc の条件つきの更新（承認済み・未使用→使用済み）を 1 回の原子的な更新で、発注 ID（解錠は承認自身）に結ぶ。並行の 2 件は片方だけ成功し、同じ発注 ID の再送には前の結果を返す。使用済みの後に確定・発行が失敗したら同じ ID で再試行する。予約は「予約済み」に結び、order-scheduler が H14 で使用済みにする。記録先（approval-svc）の障害では拒否。正しい 1 回は、同じ ID の再試行で失われない（解錠は not_after を過ぎれば承認し直し）。ここは足りている
- ログアウトトークンの jti は 150 秒、認可コードは aoba-as が 1 回限り。足りている
- 気づいたこと：承認の要否を決める「部屋ごとの直近 30 日の累計」は、「数える」と「確定する」の間に別の発注 ID の確定が入ると、両方が累計 10 万円以下と数えて承認なしで通る。業務の ID での重複の防止は同じ発注 ID の 2 回目しか止めない。試験も「分けた 2 件目」の順の試験だけで、並行の試験が無い。→ 指摘 F2

## 段 5：優先 2 の問い

9 問すべてに答えた（表 (2)）。q-long-running は No（指摘 F4）。開いた問いの「さらに」（op-clock・op-key-custody・op-requirement-words）は、M_token_validation の 6.・8. を読んだ範囲で次だけを記す。op-clock：auth_time（aoba-as の時計）と approval-svc の時計を比べ、NTP のずれ 1 秒超のサーバーを外し、ずれを足さない（止める側）ので足りている。op-key-custody：aoba-as・agent-sts の鍵は HSM・15 分、wl-ca は 60 分。上の op-proof-holder の気づきのほかは無い。op-requirement-words：「上長」について指摘 F1 と同じ点に行き着いた。

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | design.md 2. の要求の要約 REQ-05、2.2 システムの権限の「運用者の操作（上長の引き継ぎ）」の行、9.2 の「元のデータからの経路」（担当は修繕課の課長が割り当てる）、付録 D の P4_ai_agent_delegation の 5.「承認を確かめる者」、7. のシーケンス図（V->>P 修繕依頼の担当でないこと）。claims.yaml の C-sub の enforced_at（service: approval-svc）、C-approval-ref の enforced_at（service: order-tool）。hops.yaml の H12 の validates（承認者の条件）。問い ap-1-7・q-approval-from-as | REQ-05 の「上長は、その修繕依頼の担当でないこと」を、approval-svc は承認の時点に aoba-pdp で「今の担当でないか」として確かめるだけ。担当を書けるのは修繕課の課長（＝上長）で、上長は担当を自分に付け替えられる（2.2）。上長 B が担当を自分にしてエージェントに下書きさせ（承認の記録の担当者は B）、担当を A に付け替えてから承認し、担当を B に戻すと、確定のときの照合（aoba-pdp の担当が sub、承認の記録の担当者が sub）はどちらも通り、B の発注を B 自身が承認したことになる。仕組みが答えているのは「承認の時点で承認者が担当か」で、要る問い「承認者は、この発注を頼み・実行する担当者と別人か」ではない。承認者の sub を承認の記録の担当者（と確定する sub）と比べる、承認待ちの間の担当の付け替えで承認を無効にする、のどちらかが要る | Major | 目的と仕組みの不一致（あわせて候補の漏れ） | ap-1-7、q-approval-from-as |
| F2 | design.md 3.1 重点と見送りの「承認の要否を、1 件の金額でなく部屋ごとの累計で決める」の行（確かめ方は順の試験だけ）、3.1 の「重複の実行を、業務の ID で防ぐ」の行。hops.yaml の H5 の validates（確定・予約では発注の台帳で部屋の直近 30 日の累計を数え…）。catalog_answers.yaml の outside_enumeration.found「承認の分割」。問い q-approval-from-as・op-one-time | 承認の要否は order-tool が確定・予約のたびに発注の台帳で部屋の累計を数えて決めるが、「数える」と「確定する（下書き→確定の条件つきの更新）」の間を部屋ごとに直列にする手段が書いていない。同じ部屋の別の発注 ID（例：6 万円と 6 万円）を並行に確定すると、どちらも相手を含まない累計で 10 万円以下と数え、承認なしで合計 12 万円が通る。条件つきの更新と業務の ID は同じ発注 ID の 2 回目しか止めない。予約（後で order-scheduler が確定）も予約の時点の累計で決めるので同じ。部屋ごとの排他（行ロックか直列化のトランザクションで数えて確定する）と、並行の 2 件の結合試験が要る | Major | 候補の漏れ | q-approval-from-as、op-one-time |
| F3 | design.md 2. REQ-08、9.2 の「元のデータからの経路」（aoba-pdp は 2 人目の承認で確定した値だけを読む）、9.2 の表の「担当者の在籍・ロール・担当」の行（反映までに許す秒数 120）、5.1 の数字の出どころ（aoba-pdp のキャッシュ 60 秒）。token_types.yaml の ORDER_TOOL_AT・PAYMENT_TOOL_AT・LOCK_TOOL_AT の revocation（db_lookup 60 秒）。問い q-revocation-delivery・op-source-change | REQ-08 は退職・異動・ロールの剥奪を人事の台帳に「登録してから」重要な操作は 2 分、そのほかは 10 分で止めると求める。設計の最悪 60 秒・390 秒は、人事部の 2 人目が承認して値が確定した時点から数えており、登録から確定までの区間（人事システムの手順、別の設計書）に時間の約束が無い。この区間の上限を人事部と決めて REQ-08 の分数に入れるか、REQ-08 の起点が「確定」であることを要求の側で確かめて書き直すかが要る | Major | 候補の漏れ | q-revocation-delivery、op-source-change |
| F4 | design.md 3. 既定から外れた点の「予約の実行で交換し直さない」の行、3.1 の見送り「予約の実行で、トークンを交換し直すこと」（「AS が交換で確かめることと同じ項目を、order-scheduler が確かめる」）、3.1 の見送り「wl-ca の証明書の失効の確かめ」（エージェントを止めるときは agent-sts のクライアントの登録を外す）。hops.yaml の H13・H14 の validates。claims.yaml の C-act の on_revoke（手元のツールのトークンは最悪 330 秒）。token_types.yaml の ORDER_TOOL_AT の long_running。問い q-long-running・q-revocation-delivery | agent-sts は交換のたびに行為者（may_act・クライアントの登録・委任の表）も確かめるが、order-scheduler が実行の時点で引き直すのは担当者の在籍・ロール・担当、委任の欄、承認だけで、予約した repair-agent の登録が今も有効かを見ない。乗っ取られたエージェントを止める手段として設計が書く「agent-sts のクライアントの登録を外す」は、そのエージェントがした予約に届かず、最大 24 時間後に発注が確定する。C-act の on_revoke の「最悪 330 秒」もこの経路では成り立たない。3.1 の理由「同じ項目を確かめる」が選択を支えていない。H13 に予約の記録の act の連鎖の最も外側の登録の確かめを足すか、登録を外したときに予約を取り消す手順を書く | Major | 理由の不備 | q-long-running、keep-sub-exchange |
| F5 | claims.yaml の C-sub・C-repair-id・C-approval-ref の integrity_until（place: other、「予約の記録を書けるのは order-tool の DB アカウントだけ」）。design.md 2.2 の「予約の発注の実行」の行（order-scheduler の DB アカウントが予約→確定・予約→取り消しを更新）と「DB の管理」の行、3.1 の見送り「DB の管理者の直接の書き込みを止めること」（毎日の突き合わせ）、6. の UC4 の q-holder（不要の理由）、付録 A の「アプリを通らない変更」（毎日） | 台帳は予約の記録を書けるのは order-tool の DB アカウントだけとし、UC4 の q-holder を「不要」とする根拠にしているが、2.2・3.1 では order-scheduler の DB アカウントと DB の管理者（2 人）も予約の記録を書ける。DB の管理者が足した予約は最大 24 時間以内に実行されるので、翌日の突き合わせでは実行の後にしか見つからない（承認の要らない累計 10 万円以下の発注は通る）。integrity_until の trust_boundary を実際に書ける者に合わせ、予約の記録の直接の変更は実行の前に検出する（実行の前に変更の記録の表を見る）か、既知の限界として 3.1 に分けて書く | Minor | 実装とのずれ | q-copies-outlive |
| F6 | hops.yaml の H12 の added_claims（C-repair-id は approval-svc の承認の記録から）と validates（記録の repair_id がトークンと一致）。claims.yaml の C-approval-ref の enforced_at（service: approval-svc）、C-repair-id の enforced_at（service: approval-svc）。design.md 6. の UC3 の q-txn の行。claim_request_repair_id.md の問 1・問 21 | 承認・却下・取り下げの APPROVAL_AT の repair_id は、agent-sts が approval_ref の承認の記録から写した値で、approval-svc はそれを同じ記録の repair_id と比べている。比べる 2 つが同じ出どころなので、この照合は何も確かめない（UC3 の q-txn の答えになっていない）。実際に承認者を止めているのは approval_ref と aoba-pdp の承認者の条件。照合を外して「承認の記録は approval_ref で決まる」と書くか、repair_id を画面で開いた修繕依頼（repair-console の要求）から取り、記録と比べる形に直す | Minor | 目的と仕組みの不一致 | q-txn、txn-tctx |
| F7 | design.md 2. REQ-03（エージェントが動くのは担当者がログインしている間だけ）、9.1 の CONSOLE_SESSION・REPAIR_DELEG_AT の行（セッションが終われば最悪 330 秒で止まる）、付録 D の P1_human_web の 4.「ログアウトの後の AT」。token_types.yaml の REPAIR_DELEG_AT の revocation（exp_only 330）。問い q-freshness-mitigation | ログアウト・セッションの終了の後も、エージェントは手元の REPAIR_DELEG_AT とツールのトークンで最悪 330 秒動ける。REQ-03 にはこの遅れを許す数値が無く、330 秒が要求に収まるかを判定できない。REQ-03 に許す遅れ（例：10 分）を足して 330 秒をそこから導くか、ログアウトのときに委任の欄を停止して重要な操作を止める | Minor | 理由の不備 | q-freshness-mitigation |
| F8 | design.md 2. REQ-05・REQ-13、2.2 の「緊急時の特権」の行（電話での手配は後で修繕依頼の台帳に記録）、3.1 の見送り「頼る先が止まったときに通すこと」。catalog_answers.yaml の outside_enumeration（障害時の手作業の場面が found に無い）。問い q-outside-catalog | 停止の間の電話での発注（REQ-13）は、後で修繕依頼の台帳に記録するとあるが、発注の台帳に入るか、部屋ごとの直近 30 日の累計に数えるかが書いていない。入らなければ、復旧の後に同じ部屋へエージェントが出す発注は、累計を少なく数えて承認を逃れる | Minor | 候補の漏れ | q-outside-catalog |
| F9 | claims.yaml の C-repair-id の consumers（aoba-pdp を含む）と carried_in（aoba-pdp に届くトークンが無い）、enforced_at（service: aoba-pdp、H13）。claim_request_repair_id.md の問 22（受け手に aoba-pdp が無い）・問 11（書けるのは agent-sts だけ。APPROVAL_AT・予約の記録の経路を書いていない） | aoba-pdp は repair_id をトークンでなく予約の記録の値（H13）で受けるのに、台帳の consumers には入り、25 問の回答の受け手には無い。書き手も、APPROVAL_AT では承認の記録・画面の修繕依頼、予約では予約の記録から来るのに、問 11 は agent-sts の修繕依頼の台帳の確かめだけを書く。台帳と 25 問の回答をそろえる | Minor | 実装とのずれ | pa-01 |

重大度の件数：Blocker 0、Major 4（F1〜F4）、Minor 5（F5〜F9）

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| dc-05 | Yes | authorization_details のメンバーはどれも文字列で書式（金額は 10 進の文字列、ID の正規表現、RFC 3339 の UTC）と完全一致の比べ方が台帳と P4 の 5. にあり、スキーマが表さない分は 3.1 の見送りで共通部品の試験に回している（時刻の文字列の正準形は未定だが、食い違いは拒否の側に倒れる） |
| q-value-vocabulary | Yes | ロール・グループはトークンに載せず（C-roles・C-groups は却下）、aoba-pdp が人事の台帳のコードから導く。scope・acr は閉じた語彙で、agent-sts は acr を写すだけ |
| q-identifier-choice | Yes | 利用者のキーは sub（UUID）だけで、agent-sts は写すだけ。validates に出る識別子（sub・act.sub・client_id・repair_id・approval_ref）はどれも台帳の行で、identifier_properties と on_missing がある |
| ap-1-7 | No | 担当（repair_id を載せる根拠）を書ける課長が承認者でもあり、付け替えを挟んで自分の発注を承認できる（F1） |
| q-freshness-mitigation | No | scope は 390 秒、承認は 0 秒で要求に収まるが、REQ-03 の「ログインしている間だけ」に許す遅れの数値が無く、330 秒を判定できない（F7） |
| q-single-aud-resource | Yes | 全種別・全ホップの aud が 1 つで、ツールは配列にほかの値があれば拒否する |
| q-no-passthrough | Yes | 委任の表とクライアントごとのリソースの表で、頼める相手と宛先が決まり、resource は 1 つ、scope は上流と宛先とロールの積 |
| q-step-up-path-coverage | Yes | 追加の認証が要るのは承認の操作だけで、入口は APPROVAL_AT（repair-console・act なし）の 1 つ。エージェント・予約の経路は承認済みの記録を使うだけで承認に届かない |
| ap-2-7 | Yes | act の無いトークンは 1 段目の REPAIR_DELEG_AT（宛先 agent-sts、may_act の mTLS でしか交換できない）と APPROVAL_AT（repair-console だけ）で、エージェントのリソースの表に approval-svc は無い |
| q-authorize-service-and-user | Yes | 各ツール・approval-svc・aoba-pdp が mTLS の相手を確かめ、act.sub・cnf と照らし、呼び出し元の許可リストで通す |
| q-agent-short-lived-no-rt | Yes | agent-sts は RT を出さず、エージェントのトークンはどれも 300 秒 |
| q-outside-catalog | No | 管理用の口・試験の口・旧経路は答えてあるが、障害時の電話での発注が累計に入るかが無い（F8） |
| q-object-level-authz | Yes | 各ツールが対象（下書き・発注・部屋・連絡の相手）の修繕依頼を repair_id と台帳で照合し、agent-sts が担当と委任の欄を確かめる。トークンの値だけに任せていない |
| q-approval-from-as | No | 承認は記録と照合され宛先（locations）と発注 ID に結ばれるが、承認者の独立（F1）と累計の判定の並行（F2）が守られていない |
| q-operator-act | Yes | 上長は自分のログインで、管理の画面・設定の PR・DB の管理者はそれぞれの記録で利用者の操作と分けて残る（DB の直接の書き込みは毎日の突き合わせ） |
| q-revocation-delivery | No | 剥奪は重要な操作で 60 秒・ほかで 390 秒だが、起点が登録でなく確定（F3）、エージェントの登録を外しても予約に届かない（F4） |
| q-dependency-outage | Yes | aoba-as・aoba-pdp・修繕依頼の台帳・approval-svc・agent-sts・鍵の取得先のどれも止める側に倒し、REQ-13 の 60 分は電話の手配と 5 分の警報で受ける |
| pa-01 | Yes | repair_id・approval_ref の 25 問の問 1 に受け手ごとの判断があり、usage と enforced_at が対応する（受け手の一覧の食い違いは F9） |
| q-derived-value | Yes | 入居者の氏名・電話・住所は載せず（却下の行）、載せるのは不透明な ID だけ。unit_id・時間帯は lock-tool 宛てだけ、name は ID トークンだけ |
| q-variant-comparison | Yes | 送信者制約の見送り（CONSOLE_AT・CONSOLE_RT・REPAIR_DELEG_AT）は、開く攻撃（盗んだトークンだけでの呼び出し）と代わりの守り（mTLS のクライアント認証・may_act）と確かめ方を比べている |
| q-idp-diff-absorbed | Yes | ツール・approval-svc は agent-sts の iss だけを受け、aoba-as のトークンは agent-sts 以外に届かない |
| q-original-principal | Yes | 交換の後も sub は担当者のまま、scope は担当者のロールで絞り、エージェント自身の権限のトークン（client credentials）は無い |
| q-step-up-by-rs | Yes | 追加の認証の要否は approval-svc が決め、401 insufficient_user_authentication を返す |
| q-long-running | No | 担当者の権限は実行の時点で引き直すが、予約したエージェントの登録の取り消しは届かない（F4） |
| q-copies-outlive | Yes | 写しは予約の記録（実行の時点で引き直す。最大 24 時間）、aoba-pdp のキャッシュ 60 秒、監査ログ（鍵つきのハッシュ・3 年）で、いつまで残るかと止め方が書いてある（予約の記録の書ける者の食い違いは F5） |
| q-audit-correlation | Yes | sub・repair_id は全サービスで同じ鍵・同じ正規化の HMAC、approval_ref は値のまま、act の連鎖と jti を残すので、1 本につなげられる |
