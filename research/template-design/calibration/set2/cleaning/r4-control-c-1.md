# レビューのレポート：designs/target（あおば住まいサービス 修繕の手配）

- 抜き取りの種：12（sheet.md のとおり。C-approval-ref・C-repair-id・C-authorization-details）
- 読んだもの：design.md（1.〜9.、11. の一部、12.、付録 A・B・C・D の P4・M_token_validation・M_sender_constraint・M_authz_pdp）、claims.yaml（C-iss〜C-sid）、token_types.yaml（採用の全行）、hops.yaml（全行）、catalog_answers.yaml（全文）、schemas の ORDER_TOOL_AT・CONSOLE_AT の一部、ci-result.txt
- 読まなかったもの：claim_request_*.md、design.md の 10.・付録 D の M_privacy_minimization、却下の種別・クレームの詳細

## 段 0：CI の結果

- error 0、warn 2（L16 の H5・H8。authorization_details が上流 H4 に無い＝下流で広げる）
- warn の理由は design.md の 1. に行ごとに書いてある。広げる根拠を上流のトークンでなく approval-svc の承認済みの記録（人が追加の認証のうえで 1 件について承認したもの）に置き、agent-sts は記録からだけ作り、受け手は approval-svc の条件つきの更新で使用済みにして確かめる（C-authorization-details・C-approval-ref の enforced_at、H5・H8 の validates と一致）。理由は通ると判断した（q-hop-narrowing）
- 検査を通すために宣言を曲げた跡（上流を外す・名前を変える・数値を上限に合わせる）は見つからなかった。H13・H14 に upstream が無いのは、トークンを運ばない経路だから（3. の外れた点と 3.1 に理由あり）

## 段 1：性質の表の確かめ（図と要求に照らして）

| 性質 | sheet.md | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 合う（repair_id・approval_ref が名前空間つき） |
| 個人情報を載せる | 当たる | 合う（C-sub・C-repair-id・C-authorization-details が「個人情報」） |
| 発行者が複数 | 当たる | 合う（aoba-as・agent-sts。2. の図にも両方ある） |
| 交換・作り直し | 当たる | 合う（H3・H5〜H9・H11・H12 が exchange） |
| 委任 | 当たる | 合う（act・may_act、max_delegation_depth 2。REQ-03・REQ-04） |
| 操作ごとの承認 | 当たる | 合う（authorization_details。REQ-05・REQ-06 は 1 件の発注・1 回の解錠に結ぶ承認） |
| マルチテナント | 当たらない | 合う。組織は 1 つで、物件の持ち主ごとにデータを分けない（lite_criteria、U02・U24 の回答）。図にもテナントの境界は無い |
| DB の層まで運ぶ | 当たらない | 合う。図の DB への矢印（OT→OD・SCH→OD）は DB アカウントで、トークンを運ばない（2. のデータ層の行） |
| 認証の強さ・新しさ | 当たる | 合う（acr・auth_time。REQ-07） |
| 送信者制約を選んだ | 当たる | 合う（ツールの 4 種と APPROVAL_AT が mtls） |
| 送信者制約を見送った | 当たる | 合う（CONSOLE_AT・CONSOLE_RT・REPAIR_DELEG_AT が none） |
| 長時間・非同期 | 当たる | 合う（ORDER_TOOL_AT.long_running、U13、REQ-10） |

「当たらない」とされた性質が実際にはある、という食い違いは無かった。

## 段 2：6. の「要る」問いと判断の木

| 問い | 判断の木の節 | 設計の仕組み | 比べた結果 |
| --- | --- | --- | --- |
| q-sub・q-actor（UC1・UC2） | keep-sub-exchange | 交換で sub を保ち、act を agent-sts が mTLS の相手から作る。宛先ごと・300 秒 | 合う。受け手が許可に使うのは最も外側の act だけで、内側は記録だけ（C-act の enforced_at、H5〜H8・H11 の validates）。入れ子の act で照合していない |
| q-sub・q-actor（UC4 予約の実行） | keep-sub-exchange（非同期はワーカーが自分の ID で交換し直す） | 交換し直さず、order-scheduler が同じ出どころ（aoba-pdp・修繕依頼の台帳・approval-svc・クライアントの登録の表）を引き直す | 既定から外しているが、3. の表と 3.1 の見送りの行に理由・確かめ方・見直しの条件がある。担当者の RT やトークンを持ち越さず、実行の時点で判断するので、節の問い（後で動く処理を利用者の今の状態で判断するか）には答えている |
| q-sub・q-actor（UC3 承認） | keep-sub-exchange | 本人の操作で act が無いことを approval-svc が確かめる | 合う（代理する者がいない操作） |
| q-txn | txn-tctx | Txn-Token は却下。repair_id で対象の照合と相関、取引の内容（金額・協力会社・部屋・時間帯）は authorization_details で固定し、受け手が下書きの記録・台帳と完全一致で照合 | 節が求める「内容を途中で変えさせない」「受け手のすべてが照合する」は、authorization_details と受け手の照合で満たす。ツールの先にトークンの連鎖が無い（P4 の 1. の 3）ので Txn-Token が要らない理由も通る |
| q-peer | peer-mtls | wl-ca の証明書の mTLS（URI の SAN）。cnf・act と照らす | 合う。トークンのクレームで直接の相手を代えていない |
| q-authorized | rar-vs-custom | scope（操作の種類）と authorization_details（取引 1 件）を併用。type は自分の URI | 合う。併用でどちらが何を決めるかは M_authz_pdp の 4.（3 層）と C-scope・C-authorization-details に書いてある。宛先ごとに type を絞る（vendor-order は order-tool だけ、lock-code は lock-tool だけ） |
| q-resource | （aud） | aud は 1 つ、resource は 1 つ、リソースの表 | 合う |
| q-holder | existing-claim-first（cnf） | cnf の x5t#S256。REPAIR_DELEG_AT は may_act と mTLS | 合う（見送りは 3.1 に理由） |
| q-still-valid | lifetime-by-situation | 300 秒＋重要な操作は都度 aoba-pdp・approval-svc。エージェントに RT なし | 合う（「剥奪をすぐ効かせたい操作」と「サービス間のワークロード」の行のとおり） |

目的と仕組みの不一致は見つからなかった。

## 段 3：優先 1 の問いへの回答

表 (2) に書いた。No は 0 件。

## 段 4：開いた問い

### op-proof-holder

- 辿った範囲：cnf の行の enforced_at、ツールの 4 種と APPROVAL_AT の holder・sender_constraint、REPAIR_DELEG_AT の may_act、付録 D の M_sender_constraint の 4.
- 箇所ごとの「トークンを持つ者」と「鍵を持つ者」：
  - order-tool・payment-tool・lock-tool：持つ者は repair-agent、cnf は交換を求めた repair-agent の証明書。同じ
  - contact-tool：H6 では repair-agent、H11 では visit-subagent。どちらも交換を求めた者の証明書に束縛するので同じ。ツールは最も外側の act.sub が mTLS の相手の URI であることも確かめる
  - approval-svc：持つ者も鍵も repair-console
  - agent-sts（REPAIR_DELEG_AT）：束縛しないが、may_act.sub と mTLS の相手の URI を照らす。1 段目は repair-console が求めて repair-agent に渡すが、may_act は repair-agent なので、交換できるのは実際に持つ repair-agent だけ
- 証明書の更新：24 時間で残り 8 時間で更新。aoba-agent-kit が証明書とトークンを組で持ち、古い組は最悪 300 秒。更新で cnf が食い違わない
- 気づき：受け手の許可リストは証明書の URI で持ち、cnf は拇印で持つ。鍵が漏れた証明書は期限（最悪 24 時間）まで使えるが、3.1 に URI の世代を上げて 30 分で外す手順と確かめ方がある。指摘にしない

### op-source-change

- 選んだ出来事：担当者の異動（修繕課から別の課へ）
- 辿った経路：人事部の担当者が人事システムで登録 → 人事部の承認者が承認して確定（REQ-08 の起点）→ aoba-pdp が人事の台帳の API を引く（60 秒キャッシュ。sub と社員番号の対応は aoba-as の属性で、hr-sync だけが書き、異動では変わらない）→
  - 発注の確定・予約・解錠・支払い：ツールが呼び出しのたびに aoba-pdp（最悪 60 秒。REQ-08 の 2 分の内側）
  - 下書き・連絡：agent-sts が次の交換で aoba-pdp（60 秒）、手元のトークン 330 秒で最悪 390 秒（10 分の内側）
  - 承認の操作：approval-svc が aoba-pdp（60 秒）
  - 予約の実行：order-scheduler が実行の時点で aoba-pdp
- 図に無い書き込みの経路：aoba-pdp にロールを手で付ける口が無い、aoba-as の管理の画面で社員番号を書けない、DB の管理者の直接の書き込みは変更の記録と毎日の突き合わせ（3.1）。担当の付け替えは課長だけが repair-console から書き、agent-sts はキャッシュせずに引く
- 誰も時間を約束していない区間：人事の登録から確定まで。3.1 の見送りの行で、人事部の手順（2 時間）と月 1 回の報告で受けている。hr-sync の 5 分の遅れはセッションの削除だけに効き、REQ-08 の判断には入らない
- 気づき：無い（指摘にしない）

### op-one-time

- 辿った値：承認（approval_ref）、予約済みの承認、解錠のコード、ログアウトトークンの jti、認可コード
- 並行の 2 件：approval-svc の条件つきの更新を 1 つの原子的な更新で行い、発注 ID（解錠は承認自身）に結ぶので片方だけ通る。部屋の累計も、部屋の行を排他の錠で押さえたトランザクションで数える
- 通信が切れた後の再送：同じ発注 ID・同じ承認の再試行には前の結果を返し、「下書き→確定」も条件つきの更新なので 2 回は確定しない。lock-svc は承認 ID ごとにコードを 1 つだけ作り、通知の基盤は「承認 ID と送信の回」で重複を避ける。予約は order-scheduler が落ちても次の回で同じ発注 ID で再試行する
- 記録先の障害：approval-svc が止まれば拒否する（止める側）。使用済みにした後に確定できない発注は、承認を自動で未使用に戻さず、新しい発注 ID で依頼し直す（正しい 1 回を失わないよう、再試行は同じ発注 ID）
- 気づき（指摘にしない）：order-scheduler が実行の時点の確かめに通らず予約を取り消したとき、予約済みの承認をどの状態にするか（P4 の 5. の状態の遷移に「予約済み→取り消し」が無い）が書いていない。予約済みの承認は order-tool の「承認済み・未使用」の条件に当たらないので 2 回は通らず、付録 A の「予約済みのまま実行されなかった承認」の指標で見つかる。二重の実行には繋がらないので記録だけにする

## 段 5：優先 2 の問い

時間の範囲で pa-01・q-derived-value・q-variant-comparison・q-idp-diff-absorbed・q-original-principal・q-step-up-by-rs・q-long-running・q-copies-outlive・q-audit-correlation に答えた（表 (2)）。開いた問いの「さらに」（op-clock・op-key-custody・op-requirement-words）は、付録 D の M_token_validation の 6.・8. と 2.1 を読んだ範囲で気づきは無かった（時刻を比べる箇所を数え、追加の認証はずれを足さない／鍵ごとの持ち主と 15 分・60 分の手順がある／「担当者」「上長」の区分を休職・退職の手続き中・職務代行まで書いている）。深くは辿っていない。

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | claims.yaml の C-scope の `max_items`（7）・`max_bytes`（120）・`overflow_strategy`（「上限で固定（超えない値域）」）と、hops.yaml の H2 の `scope`（CONSOLE_AT）。関係する問い：`q-size-limit`・`dc-11` | H2 の CONSOLE_AT の scope の上限は 8 個（openid・orders:draft・orders:place・tenant.message:send・tenant.message:read・payments:request・lock.code:issue・approvals:decide）で、台帳の max_items 7 を超える。空白区切りの長さも 115＋空白 7＝122 バイトで、max_bytes 120 と生成の発行側のスキーマ（CONSOLE_AT.issuer.schema.json の scope の maxLength 120）を超える。allowed_values の列挙も 8 個ある。overflow_strategy は「超えない値域」としているが、その前提が台帳の中で成り立っていない。全部の scope を求めた CONSOLE_AT が発行側のスキーマで不合格になるか、どれかを落とす（落ちたのが approvals:decide なら承認の操作の交換が止まる）。max_items を 8、max_bytes を 122 以上にするか、CONSOLE_AT が実際に求める scope を絞る | Minor | 実装とのずれ | — |

重大度の内訳：Blocker 0、Major 0、Minor 1。

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| dc-05 | Yes | authorization_details のメンバーはどれも文字列で、金額は 10 進の文字列、ID は正規表現、時刻は 1 つの書式に固定し、完全一致で比べる。スキーマで表せない点は 3.1 で共通部品の試験に回している |
| q-value-vocabulary | Yes | ロール・グループはトークンに載せず（却下）、aoba-pdp が人事の台帳から導く。type・acr・scope は語彙を閉じ（extensible false）、別の発行者の同じ文字列を同じ意味で通す経路は無い |
| q-identifier-choice | Yes | 利用者のキーは sub（aoba-as の UUID）だけで、identifier_properties と on_missing がある。社員番号はトークンに出さず aoba-pdp の中で引く。外部の IdP の値は無い |
| ap-1-7 | Yes | sub は hr-sync の API だけ、担当は課長の画面だけ、委任の欄は担当者のセッションだけ、承認は承認者の条件を満たす本人だけが書く。DB の管理者と台帳の書き手は 3.1 で数えて検出の手段がある |
| q-freshness-mitigation | Yes | REQ-08 の 2 分・10 分に対し、重要な操作は aoba-pdp で 60 秒、下書き・連絡は 390 秒、承認は approval-svc で 0 秒。対策を行う者（agent-sts・ツール・approval-svc）も 9.2 に書いてある |
| q-single-aud-resource | Yes | どの種別もホップも aud は 1 つで、ツールは配列にほかの値があれば拒否する |
| q-no-passthrough | Yes | 交換を頼めるのは委任の表と may_act の主体だけ、宛先はクライアントごとのリソースの表だけ、scope は上流・宛先・ロールの積（P4 の 4.） |
| q-step-up-path-coverage | Yes | 追加の認証が要るのは承認の操作だけで、入口は approval-svc の 1 つ。エージェント・予約の経路から承認の操作に届く道が無い（付録 B、H12） |
| ap-2-7 | Yes | エージェントが持つ act の無いトークンは 1 段目の REPAIR_DELEG_AT だけで、宛先は agent-sts、交換できるのは may_act の主体だけ。ツールのトークンには必ず act がある |
| q-authorize-service-and-user | Yes | ツール・approval-svc・aoba-pdp・下流の仕組みは、mTLS の相手を証明書の URI の許可リストで確かめ、利用者の権限とは別に判断する |
| q-agent-short-lived-no-rt | Yes | agent-sts は RT を出さず、エージェントのトークンは 300 秒か上流の残りの短いほう |
| q-outside-catalog | Yes | outside_enumeration で 9 場面を挙げ、管理用の口（2.2）、試験用の口（U30）、旧経路（U29）、停止の間の電話の発注（REQ-13・2.2・3.1）、中間の CA の漏えいで開く口（3.1）に答えている |
| q-object-level-authz | Yes | agent-sts が修繕依頼の台帳で担当を、ツールが発注・部屋・連絡の相手を repair_id と台帳で照合し、承認の一覧も repair_id と承認者の条件で絞る（M_authz_pdp の 3.） |
| q-approval-from-as | Yes | 承認は approval-svc の記録から agent-sts が作り、locations と同じ宛先にだけ載せ、受け手が下書きの記録と照らして条件つきの更新で 1 回だけ使う。宛先はリソースの表で決まり、依頼の文で変えられない |
| q-operator-act | Yes | 上長・課長は自分のログインで操作し sub が残る。代理ログインは無い（I19）。order-scheduler・DB の管理者・認証基盤チームの操作は別の行為者として記録する（2.2） |
| q-revocation-delivery | Yes | 在籍・ロール・担当は重要な操作で 60 秒、その他 390 秒、委任の停止 330 秒、承認の取り下げ 0 秒、解錠のコードの取り消し 15 分（機器は 12.）。寿命の数字は 5.1 で REQ から導いている |
| q-dependency-outage | Yes | aoba-as・aoba-pdp・修繕依頼の台帳・approval-svc・鍵・JWKS のどれが止まっても止める側に倒し、REQ-13 の 60 分を電話の手配で受ける（4.・3.1・付録 A） |
| pa-01 | Yes | repair_id は agent-sts・ツールの対象の照合と監査の相関、approval_ref は承認の使用と監査に使い、どの受け手が何を決めるかが enforced_at に書いてある |
| q-derived-value | Yes | 個人情報の行は sub・repair_id・authorization_details（部屋・時間帯）で、どれも読む受け手のトークンにだけ載る。氏名・連絡先・住所・解錠コードは載せない（REQ-12） |
| q-variant-comparison | Yes | 送信者制約の見送り（CONSOLE_AT・CONSOLE_RT・REPAIR_DELEG_AT）は、開く攻撃（盗んだトークン）と代わりの守り（mTLS のクライアント認証・may_act）と確かめ方を 3.1 で比べている |
| q-idp-diff-absorbed | Yes | 発行者は組織の 2 つだけで、ツールには agent-sts のトークンだけが届き、aoba-as のトークンは拒否する |
| q-original-principal | Yes | 交換の後も sub は担当者のままで、scope は担当者のロールで絞る。間のサービスの権限で下流を呼ぶ経路が無い |
| q-step-up-by-rs | Yes | 求めるかどうかは approval-svc が acr・auth_time で決め、401 と RFC 9470 の応答を返す |
| q-long-running | Yes | 予約はトークンを持ち越さず、order-scheduler が実行の時点で在籍・ロール・担当・委任の欄・承認・行為者の登録・予約の記録の改ざんを確かめ直す |
| q-copies-outlive | Yes | 写しは監査ログ（鍵つきのハッシュ）と予約の記録だけで、予約の記録は実行の時点で確かめ直し、分析基盤には複製しない（U28） |
| q-audit-correlation | Yes | sub・repair_id を全サービスで同じ鍵のハッシュにし、act の連鎖・approval_ref・業務の ID・交換の jti の対応を残す（P4 の 8.） |
