# レビュー：designs/target（あおば住まいサービス 修繕の手配）

- 対象：designs/target/design.md と claims.yaml・token_types.yaml・hops.yaml・catalog_answers.yaml・schemas/
- 問いの 1 枚：sheet.md（行の抜き取りの種 12。抜き取った行：C-approval-ref・C-repair-id・C-authorization-details）
- CI（ci-result.txt と設計書の 1.）：error 0、warn 2（L16 の hop H5・H8。authorization_details が上流 H4 に無い）。warn には行ごとの理由がある（承認の記録を別の権限の元として 1 件の分だけ広げる）。理由は通ると判断した（承認済みの記録からだけ作り、受け手が approval-svc で条件つきで使用済みにする。H5・H8 の validates と台帳の enforced_at と食い違わない）
- 受け付け（段 0）：lint を通すために宣言を曲げた跡は見つからなかった（hops の upstream は H2〜H12 で切れていない。寿命は上限 3600 秒に合わせた値ではなく REQ から導かれている）

## 段 1：性質の表の確かめ

12.・2.・6. を読み、図（2. の flowchart）と要求（REQ-01〜13）に照らした。

| 性質 | sheet.md | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 当たる（repair_id・approval_ref。名前空間 https://aoba-sumai.example/claims/） |
| 個人情報 | 当たる | 当たる（C-sub・C-repair-id・C-authorization-details が個人情報） |
| 発行者が複数 | 当たる | 当たる（aoba-as と agent-sts。図の AS と STS） |
| 交換・作り直し | 当たる | 当たる（H3・H5〜H9・H11・H12 が exchange） |
| 委任 | 当たる | 当たる（act・may_act、深さ 2） |
| 操作ごとの承認 | 当たる | 当たる（vendor-order・lock-code。1 件の発注・1 回の解錠に結ぶ） |
| マルチテナント | 当たらない | 当たらない（組織は 1 つ。物件の持ち主ごとに分けない。図にもテナントの境界が無い） |
| DB の層まで運ぶ | 当たらない | 当たらない（発注の台帳は order-tool・order-scheduler の自分の DB アカウント。2. のデータ層の行） |
| 認証の強さ・新しさ | 当たる | 当たる（REQ-07。approval-svc が acr・auth_time） |
| 送信者制約を選んだ | 当たる | 当たる（ツールのトークン 4 種と APPROVAL_AT が mtls） |
| 送信者制約を見送った | 当たる | 当たる（CONSOLE_AT・CONSOLE_RT・REPAIR_DELEG_AT が none） |
| 長時間・非同期 | 当たる | 当たる（REQ-10 の予約。order-scheduler の H13・H14） |

「当たらない」とされた性質が実際にある、という食い違いは無い。

## 段 2：6. の「要る」問いと判断の木

| ユースケース・問い | 判断の木の節 | 設計の仕組み | 比べた結果 |
| --- | --- | --- | --- |
| UC1〜3 q-sub・q-user | keep-sub-exchange | 交換で sub を subject_token から写す（C-sub） | 合う |
| UC1・UC2 q-actor・q-agent | keep-sub-exchange（最も外側の act） | 最も外側の act.sub を mTLS の相手と照合し、操作ごとの許可リスト。内側の act は記録だけ（C-act の enforced_at、H5〜H8・H11 の validates） | 合う（入れ子の act を許可に使っていない） |
| UC3 q-actor | keep-sub-exchange | act が無く client_id が repair-console であることを approval-svc が確かめる | 合う（本人の操作で、代理の主体がいないことを確かめる仕組み） |
| UC4 q-sub・q-actor | keep-sub-exchange（非同期は交換し直す） | トークンを持ち越さず、order-scheduler が判断の元の記録を引き直す | 既定から外れるが 3. と 3.1 に理由と代わりの確かめ（同じ出どころ・世代の番号・変更の記録）がある。合うと判断 |
| q-peer（全 UC） | peer-mtls | wl-ca の証明書の mTLS（URI の SAN）。トークンの値で代えていない | 合う |
| q-txn | txn-tctx（迷い：対比表の「解く問い」を見た） | repair_id（何日もまたぐ修繕依頼の相関）。Txn-Token は却下し、prior_art_search に理由 | 合う（1 つの呼び出しの連鎖の取引の固定ではなく、業務の単位の相関。取引の中身は authorization_details が固定する） |
| q-authorized | rar-vs-custom | authorization_details（自分の URI の type）と approval_ref、scope は操作の粗い可否 | 合う。scope と authorization_details の役割の分担は C-scope・C-authorization-details の enforced_at に書いてある |
| q-resource | （RFC 8707） | aud 1 つ、リソースの表 | 合う |
| q-holder | carry-or-query／送信者制約 | cnf の x5t#S256（mTLS） | 合う |
| UC4 q-holder 不要 | — | トークンを持ち越さない | 合う |

目的と仕組みの不一致は見つからなかった。

## 段 3：優先 1 の問いへの回答（1 行ずつ）

抜き取った 3 行（C-approval-ref・C-repair-id・C-authorization-details）を中心に、問いが名指す行（C-sub・C-scope・C-act・C-cnf・C-acr・C-auth-time）を足した。

- dc-05：Yes。authorization_details のメンバーは全部文字列で、金額は 10 進の文字列・時刻は 1 つの書式に固定し、完全一致で比べる。生成のスキーマがメンバーの型を表さないことは 3.1 の見送りで、共通部品の試験で補う
- q-value-vocabulary：Yes。ロールはトークンに載せず aoba-pdp が人事の台帳から導く。scope・acr・type は列挙で、agent-sts は aoba-as の acr を写すだけ（別の発行者の同じ文字列を別の意味で通す経路が無い）
- q-identifier-choice：Yes。利用者のキーは C-sub（UUID、identifier_properties・on_missing あり）の 1 つで、agent-sts も同じ値を写す。IdP ごとの独自の識別子は無い
- ap-1-7：No。書き手の範囲は 2.2・3.1・9.2 に書かれているが、作業員の番号（解錠のコードの届け先を決める値）の書き換えを承認の後に効かせない守り（発行のときのハッシュの照合）が、3.1 にあるのに台帳・ホップの照合に無い（F1）
- q-freshness-mitigation：Yes。scope は 390 秒（許容 600）、在籍・ロール・担当は 60 秒（許容 120）、authorization_details は approval-svc の条件つきの更新で 0 秒。要求に数値があり、対策を行う者（agent-sts・各ツール・approval-svc）も決まっている
- q-single-aud-resource：Yes。全種別・全ホップの aud が 1 つ（ツールごとに種別を分ける）
- q-no-passthrough：Yes。委任の表・リソースの表・may_act で頼める相手と宛先が決まり、表に無い resource は拒否する。範囲は上流の scope・宛先の操作・aoba-pdp のロールの積
- q-step-up-path-coverage：Yes（ただし記述の食い違い 1 件）。承認の入口は approval-svc の 1 か所で、エージェント・予約の経路から承認に届く道が無い。手作業の発注の事後の確認の条件が、C-acr・C-auth-time の enforced_at と H12 の validates に無い（F3）
- ap-2-7：Yes。代理の主体が持つ act の無いトークンは 1 段目の REPAIR_DELEG_AT だけで、宛先は agent-sts だけ・交換は may_act の主体の mTLS だけ・ツールは受けない。交換で出るツールのトークンには必ず act が入る
- q-authorize-service-and-user：Yes。各ツール・approval-svc・aoba-pdp・下流が mTLS の相手を呼び出し元の許可リストで確かめ、利用者の権限（aoba-pdp）とは別に決めている
- q-agent-short-lived-no-rt：Yes。agent-sts は RT を出さず、エージェントの種別は 300 秒で手順ごとに交換し直す
- q-outside-catalog：Yes。管理用の口・DB の管理者・電話での手配（手作業の発注）・試験の口（U30）・旧経路（U29）・停止の間の解錠の取り消しが 2.2・3.1・11. にある
- q-object-level-authz：Yes。他人の修繕依頼 ID は agent-sts が修繕依頼の台帳で担当を確かめて止め、ツールは対象の発注・部屋の修繕依頼と repair_id を比べて 404、approval-svc は画面の修繕依頼と記録の修繕依頼を比べる
- q-approval-from-as：Yes。agent-sts は approval-svc の承認済みの記録からだけ作り（要求の値を載せない）、locations と宛先・発注 ID・承認自身に結び、受け手が条件つきの更新で 1 回だけ使う。入力に紛れた指示で宛先を変えてもリソースの表と locations で止まる
- q-operator-act：Yes。代理ログインを作らず、上長・運用者は自分の sub で操作する。DB の管理者の直接の書き込みは変更の記録の表で分かる
- q-revocation-delivery：No。利用者の剥奪は 60 秒・390 秒・330 秒で数値から導かれているが、取引先（協力会社）の取引の停止で、承認済みで未発行の解錠コードの発行が止まらない（F2）
- q-dependency-outage：Yes。aoba-as・aoba-pdp・修繕依頼の台帳・approval-svc・署名の鍵・JWKS のどれでも止める側に倒し、REQ-13 の 60 分と警報の 5 分に合わせている。停止の間の解錠の取り消しは手順で受ける

## 段 4：開いた問い

### op-proof-holder

辿った範囲：C-cnf の enforced_at、token_types の holder・sender_constraint、H5〜H8・H11・H12 の validates、付録 D の M_sender_constraint の 4. を記載した C-cnf の on_revoke、3.1 の証明書の失効の行。

| 箇所 | トークンを持つ者 | 確かめる鍵の持ち主 | 一致するか |
| --- | --- | --- | --- |
| order-tool・payment-tool・lock-tool | repair-agent のメモリ | 交換を求めた repair-agent の証明書（cnf）と mTLS の相手 | 一致 |
| contact-tool | repair-agent か visit-subagent | 交換を求めた者の証明書 | 一致（H6 と H11 で別のトークン） |
| approval-svc | repair-console のサーバー | repair-console の証明書 | 一致 |
| agent-sts（REPAIR_DELEG_AT） | repair-agent・visit-subagent | 束縛しない。may_act の URI と mTLS の相手の URI を照合 | 鍵ではなく URI での照合。同じ URI の別の証明書（中間の CA の漏えい時）でも通ることは 3.1 に書いてある |

気づいたこと：
- 証明書の更新（24 時間、残り 8 時間で更新）では、共通のクライアント部品が証明書とトークンを組で管理すると書かれ、束縛したトークンが更新で使えなくなる問題は扱われている
- repair-console・repair-agent を複数の実例（インスタンス）で動かすとき、同じ URI で実例ごとに鍵が違うのか、交換した実例と呼び出す実例が同じであることを誰が保つのかは書かれていない。トークンの寿命が 300 秒・120 秒と短いので害は可用性（拒否）にとどまると考え、指摘にはしなかった（書き手への確認の候補）

### op-source-change

辿った出来事：異動で修繕担当のロールが外れる（あわせて担当の付け替え、協力会社の取引の停止）。

- 人事の台帳：人事部の担当者が登録し、もう 1 人が承認して確定（REQ-08 の起点）。登録から確定までは人事部の手順書の 2 時間で、時間を約束する者と報告の経路が 3.1 にある
- aoba-pdp：確定した値だけを人事の台帳の API で読み、ロールを導く（手で書く画面・API が無い）。sub と社員番号の対応は aoba-as の属性で、書けるのは hr-sync の証明書だけ。キャッシュ 60 秒
- 受け手：発注の確定・支払い・解錠の発行は各ツールが呼び出しのたびに aoba-pdp（最悪 60 秒）、下書き・連絡は agent-sts の交換で scope を絞り直す（最悪 390 秒）、予約は order-scheduler が実行の時点で引き直す
- 担当の付け替え：課長が repair-console で書き、修繕依頼の台帳が履歴に追記。agent-sts は交換のたびにキャッシュなしで引く
- hr-sync（5 分ごと）は REQ-08 の経路に入らない、と明記されている

気づいたこと：
- 利用者の側の出来事は、元のデータの書き手・経路・時間を約束する者まで辿れた
- 取引先の側の出来事（協力会社の取引の停止・作業員の登録の取り消し）は、発注の確定では order-tool が協力会社の台帳で取引を確かめる（H5）が、解錠の発行では確かめる者がいない。3.1 の見送りは「発行した」コードを自動で止めない点だけで、承認済み・未発行の解錠の承認はその外にあり、課長に送る一覧（使用済みの承認だけ）にも入らない（F2）

### op-one-time

辿った値：発注の承認・解錠の承認（approval-svc の条件つきの更新）、発注 ID（下書き→確定）、lock-svc の承認 ID ごとの 1 つのコード、通知の基盤の「承認 ID と送信の回」、CONSOLE_LOGOUT の jti（150 秒）。

- 並行の 2 件：承認は 1 つの原子的な更新で片方だけ成功。同じ部屋の累計は部屋の行の排他の錠で直列化。解錠の発行は lock-svc が承認 ID ごとに 1 つのコードを返す
- 通信が切れた後の再送：同じ発注 ID・同じ承認なら前の結果を返す。送信は同じ回で再試行し、通知の基盤が重複を捨てる。正しい 1 回は、自動で未使用に戻さず同じ ID で再試行することで守られている（再試行で確定できない発注は、承認を失効させて新しい発注 ID で依頼し直す）
- 記録先の障害：approval-svc が応答しなければ拒否（止める側）。使用済みにした後で確定の前に落ちたら、同じ発注 ID で再試行する
- 予約：予約済み→使用済み（H14）も条件つきの更新で、取り下げてあれば失敗

気づいたこと：
- 「2 回通る」経路は見つからなかった
- 届かないときの送り直し（回を上げる。3 回まで）を並行に 2 件頼んだとき、回の上げ方が条件つきの更新かは書かれていない。送るのは同じコードで、解錠できる範囲は広がらないので指摘にはしなかった

## 段 5：優先 2 の問い（時間が残ったので答えた）

すべて答えた（答えなかった問いは無い）。下の (2) の表に載せる。開いた問いの「さらに」（op-clock・op-key-custody・op-requirement-words）は辿っていない。op-clock の観点では、auth_time（aoba-as の時計）と approval-svc の時計の比べにずれの許しが書かれていないことだけ気づいた（指摘にはしていない）。

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | design.md の 3.1（見送り「修繕依頼の台帳と協力会社の台帳の書き込みの口を、この設計で閉じること」）／claims.yaml の C-approval-ref の enforced_at（service: lock-tool）／hops.yaml の H8 の validates.checks／design.md の 8. の H8・`https://aoba-sumai.example/claims/approval_ref` の行／付録 D の P4_ai_agent_delegation の 5.「受け手の照合」。問い ap-1-7 | 3.1 は「lock-tool は解錠の承認の依頼のときの作業員の番号の鍵つきのハッシュを承認の記録に残し、**発行のときに**今の番号のハッシュと一致しなければ送らない（承認の後に番号を書き換えてコードを別の人に届けさせない）」と決めている。ところが台帳の lock-tool の照合と H8 の validates では、ハッシュの照合は**送り直し**にだけあり、発行のときの照合が無い。実装は台帳とホップから作るので、承認の後に作業員の番号を書き換えると、最初の発行のコードが別の人に届く。2 か所が同じ仕組みについて食い違う。台帳の lock-tool の行と H8 に「発行では、作業員の番号のハッシュが承認の記録と一致するときだけ送る」を足す | Major | 実装とのずれ | ap-1-7 |
| F2 | hops.yaml の H8 の validates.checks（H5 にある「協力会社の台帳で協力会社の取引が今も有効」に当たるものが無い）／claims.yaml の C-authorization-details・C-approval-ref の enforced_at（service: lock-tool）／design.md の 3.1（見送り「発行した解錠コードを、退職・担当の付け替え・協力会社や作業員の登録の停止で自動では止めないこと」）／9.1 の承認の記録の行。問い q-revocation-delivery・op-source-change | 解錠の承認は not_after まで有効で、承認から発行までに日をまたぎうる。発注の確定では order-tool が協力会社の取引の有効を確かめるが、解錠の発行では lock-tool も agent-sts も協力会社の取引の停止・作業員の登録の取り消しを確かめない。3.1 の見送りが扱うのは「発行済み」のコードだけで、課長に送る一覧も使用済みの承認だけなので、取引を止めた協力会社に向けた承認済み・未発行の承認から、止めた後でもコードを発行できる。止める単位（取引先）ごとの最悪の時間が言えない。H8 の発行の照合に「協力会社の台帳で取引が有効、作業員の登録が有効」を足すか、承認済み・未発行の承認も課長の一覧と見送りの理由に入れる | Major | 候補の漏れ | q-revocation-delivery |
| F3 | claims.yaml の C-acr・C-auth-time の rationale と enforced_at（service: approval-svc）／hops.yaml の H12 の validates.checks（「承認では acr が mfa で…」）／対して C-approval-ref の enforced_at（approval-svc）・付録 B の「手作業の発注の事後の確認」の行・3.1 の発注の台帳の行。問い q-step-up-path-coverage | 手作業の発注の事後の確認（10 万円を超えるもの）に acr が mfa・auth_time から 300 秒を求めることは、C-approval-ref・付録 B・3.1 にあるが、追加の認証を確かめる行そのもの（C-acr・C-auth-time の enforced_at は「発注の承認・解錠の承認」だけを挙げる）と H12 の validates に無い。追加の認証が要る操作の一覧が 2 か所で食い違い、実装で事後の確認に追加の認証が掛からない恐れがある。C-acr・C-auth-time の enforced_at と H12 に事後の確認を足す | Minor | 実装とのずれ | q-step-up-path-coverage |
| F4 | token_types.yaml の PAYMENT_TOOL_AT の refresh（「なし。手順ごとに agent-sts で交換し直す」）・LOCK_TOOL_AT の refresh（「なし。承認の依頼と発行のそれぞれで交換し直す」）／対して ORDER_TOOL_AT・CONTACT_TOOL_AT の refresh と design.md の 9.1・5.1。問い q-revocation-delivery | ORDER_TOOL_AT・CONTACT_TOOL_AT と 9.1 は「寿命は 300 秒か REPAIR_DELEG_AT の残りの短いほう」と書くが、PAYMENT_TOOL_AT・LOCK_TOOL_AT の行には無い。REQ-03（ログアウトから 10 分）と REQ-09 の最悪 330 秒は、この上限（上流の残りを超えない）に依る。5.1 の組織の規則で決まってはいるが、種別の行が食い違うので、将来の保守で片方だけ直すと壊れる。2 行にも同じ文を足す | Minor | 実装とのずれ | q-revocation-delivery |

重大度ごとの件数：Blocker 0、Major 2、Minor 2。

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| dc-05 | Yes | authorization_details のメンバーは文字列で、金額は 10 進の文字列・時刻は 1 つの書式に固定し、受け手は書式を確かめてから完全一致で比べる |
| q-value-vocabulary | Yes | ロールは載せず aoba-pdp が人事の台帳から導き、scope・acr・type は列挙。agent-sts は aoba-as の acr を写すだけ |
| q-identifier-choice | Yes | 利用者のキーは UUID の sub 1 つで、identifier_properties と on_missing（拒否）がある |
| ap-1-7 | No | 作業員の番号の書き換えを発行に効かせない照合が、3.1 にあるのに台帳・ホップに無い（F1） |
| q-freshness-mitigation | Yes | scope 390 秒／許容 600、在籍・ロール・担当 60 秒／許容 120、承認は 0 秒で、行う者が決まっている |
| q-single-aud-resource | Yes | 全種別・全ホップで aud が 1 つ |
| q-no-passthrough | Yes | 委任の表・リソースの表・may_act で相手と宛先を決め、範囲は上流・宛先・ロールの積 |
| q-step-up-path-coverage | Yes | 承認の入口は approval-svc の 1 か所で、代理・交換・予約の経路から届かない（事後の確認の記述の食い違いは F3） |
| ap-2-7 | Yes | act の無い 1 段目の REPAIR_DELEG_AT は宛先が agent-sts だけで may_act の主体しか交換できず、ツールのトークンには必ず act が入る |
| q-authorize-service-and-user | Yes | 全受け手が mTLS の相手を許可リストで確かめ、利用者の権限は aoba-pdp で別に決める |
| q-agent-short-lived-no-rt | Yes | agent-sts は RT を出さず、エージェントの種別は 300 秒で都度交換 |
| q-outside-catalog | Yes | 管理の口・DB の管理者・電話の手配・試験の口・旧経路・停止の間の取り消しが 2.2・3.1・11. にある |
| q-object-level-authz | Yes | agent-sts が修繕依頼の台帳で担当を、ツールが対象の修繕依頼を、approval-svc が画面と記録の修繕依頼を比べて止める |
| q-approval-from-as | Yes | agent-sts が承認の記録からだけ作り、宛先（locations）と発注 ID・承認に結んで受け手が 1 回だけ使う |
| q-operator-act | Yes | 代理ログインが無く、運用者・上長は自分の sub。DB の直接の書き込みは変更の記録で分かる |
| q-revocation-delivery | No | 取引先（協力会社）の取引の停止で、承認済み・未発行の解錠コードの発行が止まらない（F2） |
| q-dependency-outage | Yes | 依存先のどれでも止める側に倒し、REQ-13 の 60 分と警報 5 分に合わせている |
| op-proof-holder | 該当なし（開いた問い） | 各箇所で持つ者と鍵の持ち主は一致。複数の実例での鍵と交換の対応は未記載（気づき） |
| op-source-change | 該当なし（開いた問い） | 利用者の側は辿れた。取引先の側の停止が解錠の発行に届かない（F2 の出どころ） |
| op-one-time | 該当なし（開いた問い） | 並行・再送・記録先の障害のどれでも 2 回通らず、正しい 1 回も再試行で守られる |
| pa-01 | Yes | repair_id は対象の照合と相関、approval_ref は承認の 1 回の使用に使い、受け手と判断が台帳に書いてある |
| q-derived-value | Yes | 入居者の連絡先・住所は載せず、部屋・時間帯は解錠と発注のトークンだけ、ログはハッシュか記録しない |
| q-variant-comparison | Yes | 送信者制約の見送りは盗んだ場合に開く口と代わりの守り（mTLS のクライアント認証・may_act）を比べている |
| q-idp-diff-absorbed | Yes | ツール・approval-svc は agent-sts のトークンだけを受け、aoba-as の値は agent-sts が写す |
| q-original-principal | Yes | 交換の後も sub は担当者で、scope は上流とロールの積に絞る |
| q-step-up-by-rs | Yes | 追加の認証を求めるかは approval-svc が決め、401 insufficient_user_authentication を返す |
| q-long-running | Yes | 予約はトークンを持ち越さず、実行の時点で在籍・担当・委任の世代・承認を引き直す |
| q-copies-outlive | Yes | 予約の記録・監査ログの写しに integrity_until があり、aoba-pdp のキャッシュは 60 秒 |
| q-audit-correlation | Yes | sub・repair_id は全サービスで同じ鍵・同じ正規化のハッシュ、approval_ref は値のまま、jti を交換で結ぶ |
