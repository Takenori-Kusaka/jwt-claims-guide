# レビューの報告：designs/target（しろがね損保　保険金の請求と支払いの内部処理）

- 対象：designs/target/ の design.md と台帳（claims.yaml・token_types.yaml・hops.yaml・catalog_answers.yaml）、ci-result.txt、sheet.md
- 行の抜き取りの種：12（sheet.md のとおり。C-agency-code・C-client-id・C-act）
- 読んだ教材：short_list.md、perspectives.md（問いの書き方と読み方）、decision_tree.md、contrasts/act-txn-workload.md、kind_tell.md
- 結果の要約：Blocker 0・Major 0・Minor 4

## 0. 受け付け（lint の結果）

- 設計書の 1. と ci-result.txt は同じ内容（error 0・warn 9・info 15）。
- warn ごとの理由を確かめた。
  - L1b（C-req-wl・C-tctx）：草案の名前で、spec_version と見直しの条件がある。理由は通る。
  - L16 の aud（H4・H7・H15・H17・H23・H26）：Txn-Token の aud は信頼ドメイン（草案 §9.2）で、外の AT の口の aud とは名前が違う。宛先の絞り込みは TTS（`C-aud` の tts の行）と内側の受け手（aud は信頼ドメインだけ）が行い、scope と寿命は上流を超えない（H17 は H14 の部分集合、H23 は payments:approve だけ、H26 は admin の 3 つだけ、寿命は 300 秒以下で上流は 600 秒）。理由は通る。
  - L16 の寿命（H30。下流 3600 秒、上流 TXN_STAFF 300 秒。答えを決める問い：q-hop-lifetime）：PAY_MSG_CTX は TTS への作り直しにしか使えず（payment-worker の mTLS の相手からだけ受ける）、作り直しのたびに TTS が社員の勤務の状態と役割を引き直し、payment-svc が版と保留を確かめる。理由は通る。ただし作り直しでは「請求の割り当て」は確かめない（4. の op-source-change に書いた）。
- 宣言を曲げて lint を通した跡（q-lint-workaround）：見つからなかった。H31 を H5 の upstream に置かない理由（assertion は認可の grant で、作り直しの上流ではない）は hops.yaml の note に書いてあり、筋が通る。

## 1. 性質の表を、図と要求に照らして確かめた結果

| 性質 | sheet.md | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 合う（C-agency-code） |
| 個人情報を載せる | 当たる | 合う（C-sub・C-act・C-tctx） |
| 発行者が複数 | 当たる | 合う（shirogane-as・shirogane-sso・TTS・代理店の IdP 2 社） |
| 交換・作り直し | 当たる | 合う（H4・H7・H15・H17・H23・H26 の reissue、H22・H24・H30 の exchange） |
| 委任 | 当たる | 合う（TXN_PROXY の act） |
| 操作ごとの承認 | 当たらない | **合わない（指摘 F1）**。REQ-05 の上長の承認は支払いの 1 件ごと（payment_id・amount・payee_ref に結びつく。H23）で、操作ごとの承認がある。トークンに authorization_details を載せないと決めただけ（3.1 の見送り）。dc-05 を足して答えた（q-approval-from-as はもともと 1 枚にある） |
| マルチテナント | 当たらない | 合う（1 社。代理店は証券の取扱代理店で絞り、テナントではない） |
| DB の層まで運ぶ | 当たらない | 合う（db_connection のホップが無い。9.1 の DB・ブローカーの接続の層） |
| 認証の強さ・新しさ | 当たる | 合う（C-acr・C-auth-time） |
| 送信者制約を選んだ | 当たる | 合う（AGENCY_AT の mtls） |
| 送信者制約を見送った | 当たる | 合う（PH_AT・EMPLOYEE_AT が none） |
| 長時間・非同期 | 当たる | 合う（PAY_MSG_CTX、H20・H21、U13 が該当） |

## 2. 6. の「要る」問いと判断の木の節

UC1〜UC7 の「要る」の行を、木の節と比べた。目的と仕組みの不一致は見つからなかった。

| 問い | 木の節 | 設計の仕組み | 比べた結果 |
| --- | --- | --- | --- |
| q-sub | keep-sub-exchange | Txn-Token の sub に利用者を保つ。PAY_MSG_CTX からの作り直しでも査定を確定した社員のまま。夜間の実行は payment-batch 自身の ID | 合う。利用者の文脈が要らない処理（UC6）はワークロードの ID で、sub を捏造しない |
| q-actor（UC3） | keep-sub-exchange | TXN_PROXY の act（入れ子なし、最も外側だけ） | 合う。claim-svc・fraud-svc の enforced_at が入れ子を拒む |
| q-req-wl・q-txn | txn-tctx | req_wl、txn・tctx、専用の Txn-Token ヘッダー | 合う。Txn-Token を受けるホップの受け手のすべて（claim-svc・fraud-svc・document-svc・assessment-svc・payment-svc・as-admin-api）が tctx を本文・パス・記録と照合する。Authorization ヘッダーを Txn-Token として読まない |
| q-peer | peer-mtls | SPIFFE の X.509-SVID の mTLS、代理店とは代理店向けの CA の mTLS | 合う。req_wl・act・client_id で代えていない（C-req-wl の does_not_answer） |
| q-authorized | carry-or-query／rar-vs-custom | TTS が台帳の役割から絞った scope。承認は payment-svc の記録。acr・auth_time | 合う。役割は載せずに問い合わせ（C-roles 却下）、承認はトークンでなく記録 |
| q-resource | — | aud（AT は口ごと 1 つ、Txn-Token は信頼ドメイン） | 合う |
| q-holder（UC2） | — | AGENCY_AT の cnf（x5t#S256） | 合う |
| q-user・q-agent | — | sub、client_id | 合う |

UC4 の q-actor を「不要」とした点も確かめた。木の keep-sub-exchange は「act＝仲介するワーカー」を例に挙げるが、この設計の payment-worker は tctx を変えられない運び手で、運んだワークロードは req_wl と q-peer で別に記録し、payment-svc は payment.instruct を req_wl＝payment-worker と mTLS の相手でだけ受ける（社員が直接は指示できない）。木の「期限切れの後や非同期の処理でも、ワーカーが自分の ID で交換し、そのたびに可否を決める」は満たしている。指摘にしない。

## 3. 優先 1 の問いへの答え

（下の表 (2) に 1 行ずつ書いた。No は指摘にした）

## 4. 開いた問い

### op-proof-holder（辿った範囲：C-cnf の enforced_at、AGENCY_AT・PH_AT・EMPLOYEE_AT の holder・sender_constraint、H5・H6・H31、付録 D の M_sender_constraint の 1.〜4.、3.1 の CRL の扱い）

| 箇所 | トークンを持つ者 | 確かめる鍵を持つ者 | 結果 |
| --- | --- | --- | --- |
| shirogane-as のトークンの端点（H31） | 代理店のサーバー（AGENCY_AT を受け取る） | 代理店のサーバー（tls_client_auth の証明書） | 一致。cnf はトークンの要求の証明書の拇印 |
| front-gw の代理店の口（H5） | 代理店のサーバー | 代理店のサーバー（TLS を front-gw が終端） | 一致 |
| TTS（H6） | front-gw（subject_token として渡す） | front-gw が書いた拇印のヘッダー | 確かめの主は front-gw。ヘッダーは front-gw だけが書け、同名のヘッダーは捨てる。TTS は front-gw の SPIFFE ID からの要求でだけ読む |
| front-gw の契約者・社員の口（H2・H13） | claim-portal・staff-console | 束縛なし。口が claim-portal・staff-console の SVID だけを受ける | 見送り（3.1）。持つ者と接続の相手は同じ BFF |

気づき：
- cnf が示すのは「代理店のサーバー」で、担当者（sub）ではない。I29 の note で書き手が明示しており、AT を持つのはサーバーなので筋が通る。
- 証明書の更新では拇印が替わり、古い証明書に束縛した AGENCY_AT は最大 300 秒で使えなくなる（M_sender_constraint の 4.）。RT が無いので、取り直しは新しい assertion で済む。
- CRL を取り直せない間は、失効した証明書を最長 3600 秒受けうる（3.1 で受け入れた限界）。代理店の登録の停止は CRL と別の経路（shirogane-as と TTS の登録の確認）で 390 秒で効くので、REQ-02 はこの限界に頼らない。

### op-source-change（出来事：査定担当者の退職と課の異動。辿った範囲：9.2 の「元のデータからの経路」、C-scope・C-sub の source_system、3.1 の課の規則と REQ-03 の起点の見送り、H22・H23・H30、9.1 の社員の行）

- 退職：人事部の担当者が人事の仕組みに入れ、責任者が承認した時点で社員の台帳が変わる → TTS は 60 秒のキャッシュの後に発行を拒む → 発行済みの Txn-Token は最大 330 秒 → 390 秒で止まる（REQ-03 の 600 秒の内）。shirogane-sso も 60 秒ごとに台帳を引く。ブローカーにある PAY_MSG_CTX は作り直しで止まる。台帳を書けるのは人事の仕組みだけで、IT の部品と DB の管理者は書けない（2.2）。
- 誰も時間を約束していない区間：発効から台帳の更新まで（3.1 の見送り。人事の規程と毎月の突き合わせで前提として書いてある）。
- 課の異動：役割が残るので TTS は止めない。上長の基準は「査定者の今の課」で、payment-svc・assessment-svc が要求のたびにキャッシュせずに引くので、上長の側の権限は異動の次の要求から切り替わる。一方、査定担当者の割り当ては業務の手続き（発効の前に付け替える）と毎日の突き合わせに頼る。
- 気づき 1：手続きが発効に間に合わないと、異動した査定担当者の未実行の指示を承認・取り消しできるのは、異動先の課の上長だけになる（前の課の上長は「査定者の今の課の上長」でなくなる）。取り消しの道は残るので REQ-04 は満たすが、査定を見ていない課の上長が承認できる状態が、毎日の突き合わせまで続く。3.1 の前提（発効の前に片づける）が崩れたときの扱いとして、保険金部への返し方に加えてもよい（指摘にはしない）。
- 気づき 2：PAY_MSG_CTX からの作り直し（H22）で TTS が引き直すのは勤務の状態と役割だけで、請求の割り当ては引き直さない。待つ 60 分の間に上長が割り当てを替えても、前の査定担当者の確定はそのまま指示になる。止めるには上長が保留か取り消しをする。H30 の narrowing_exception の「待つ間の変化」の列挙に割り当ての変更を足すとよい（指摘にはしない）。

### op-one-time（辿った範囲：C-jti の shirogane-as の行、AUTH_CODE、2.2 のセキュリティキーの登録の番号、H21・H22 の (claim_id, assessment_ref)、H23・H24 の支払いの行のロック、H25 の保留の印、付録 D の M_token_validation の 6.）

| 1 回だけの値 | 並行の 2 件 | 切れた後の再送 | 記録先の障害 | 正しい 1 回が失われないか |
| --- | --- | --- | --- | --- |
| AGENCY_ASSERTION の (iss, jti) | 一意の制約つきの 1 回の書き込みで 1 件だけ | 2 回目は拒む | 拒む | 代理店が新しい assertion で取り直せる |
| セキュリティキーの登録の番号 | 「未使用→使用済み」の条件つきの書き込みで 1 件だけ | 2 回目は使用済み | 登録しない | 番号の出し直し（2 人の操作）が要るが、安全側 |
| 支払いの指示（PAY_MSG_CTX） | 請求ごとの集計の行のロックと (claim_id, assessment_ref) の一意の制約 | 前の結果を返す | ブローカーの再配送、payment-worker は受け付けの後にだけ処理済みにする | 落とさない（期限を過ぎたものは滞留のキューで新しい版） |
| 支払いの実行 | 支払いの行のロック、同じ payment_id を 2 回入れない | 同上 | 実行せず次の夜 | 落とさない |
| 保留の印（H25） | 集計の行のロック | **claim-svc と payment-svc の 2 か所に保留の状態があり、応答が失われると食い違う（指摘 F4）** | payment-svc が書けなければ失敗にする | — |
| AUTH_CODE | shirogane-as の実装（AS-SPEC）に任せている | 同左 | 同左 | 自社の発行者の仕様書の側で確かめる（ここでは辿れなかった） |

気づき：支払いの実行の「振込のファイルへの追加を、支払いの行をロックした 1 つの取引で行う」（H24）は、振込のファイルが DB の表であれば成り立つ。ファイルを DB の外に書くなら、取引の途中で落ちたときに二重・欠落が起きうる。どちらかを 1 行足すとよい（範囲の外の振込のファイルとの境目なので、指摘にはしない）。

### 開いた問い（さらに）

- op-clock：設計書の 12.（時計）と付録 D の M_token_validation の 6. に、IVR・代理店の IdP・shirogane-sso の時計と比べる側の時計が書いてあり、ずれたときは拒む側に倒すことも書いてある。これ以上は辿っていない。
- op-key-custody・op-requirement-words：時間の都合で辿っていない。

## 5. 優先 2 の問い

（下の表 (2) に答えた）

---

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | sheet.md の 1. の「操作ごとの承認がある」の行、design.md の 3.1（見送り：高額の支払いの承認をトークンの authorization_details に載せない）、hops.yaml の H23（validates）、claims.yaml の C-scope（value_vocabulary の payments:approve）・C-tctx（operation の payment.approve・payment.cancel） | 性質の表は authorization_details が無いので「当たらない」としたが、REQ-05 の上長の承認は支払いの 1 件ごと（payment_id・amount・payee_ref に結びつき、承認の記録を payment-svc が書く）で、操作ごとの承認がある。トークンに載せないと決めただけで、承認そのものはある。value_vocabulary の値が approval でなく approve なので、#80 の読み方（承認の ID の行を読んだ欄に書いて段 1 で確かめる）も働かなかった。dc-05 を足して答えた（Yes：tctx の内側はすべて文字列で、amount は先頭の 0 と符号の無い 10 進、比べ方は exact。JSON Schema が内側を確かめない点は 3.1 の見送りで試験に回してある）。設計の誤りではなく、1 枚の性質の読み取りの誤り | Minor | 前提の誤り | dc-05・q-approval-from-as |
| F2 | design.md の 2. の範囲の図（ADM → SAS の矢印「代理店の登録・契約者のアカウントの状態を書く」）と「トークンを運ばない内部の呼び出し」の表、2. の境界の表の「しろがねの発行者」の行、claims.yaml の C-agency-code（source_system・note）、C-client-id（source_system） | 「代理店の登録・契約者のアカウントの状態は as-admin-api だけが書く」と宣言しているが、shirogane-as の書き込みの口がどうやって as-admin-api だけを受けるかが書いていない。as-admin-api → shirogane-sso・staff-console の呼び出しは「as-admin-api の SPIFFE ID だけを受ける」と表にあるのに、→ shirogane-as の行が無い。as-admin-api が shirogane-as の部品の一部なのか別のサービスなのかも読み取れない。代理店コード（認可に使う組織独自の値）と client_id の元のデータを書ける者の範囲（ap-1-7）と、REQ-01・REQ-02 の停止の経路が、この 1 行に掛かる。表に 1 行足し、受ける SPIFFE ID と、ほかの部品から書けないことを書く | Minor | 候補の漏れ | q-outside-catalog・ap-1-7 |
| F3 | design.md の付録 B（追加認証）の表、hops.yaml の H17・H18・H25（validates）、design.md の付録 D の M_authz_pdp の 1.（上長の assessment.unhold） | 保留の解除（assessment.unhold）は、保留で止めていた支払い（承認済みのものを含む）を夜間の実行に戻す操作だが、追加の認証を求めず、求めない理由も書いていない。付録 B は「査定の確定」を求めない理由（承認で求める）を書いているのに、保留・保留の解除の行が無い。mfa の上長のセッションを盗めば、取り消し（phr が要る）はできないのに、不正の疑いで掛けた保留を外せる。求めないならその理由（例：解除の後も承認の記録と課の規則で守られる）を付録 B に書く。求めるなら H23 と同じ確かめを H17 か H25 に置く | Minor | 理由の不備 | q-step-up-path-coverage |
| F4 | hops.yaml の H25（validates の 1 つ目）、design.md の 9.1（支払いの承認・請求の行）、付録 D の M_authz_pdp の 2.（請求の保留・承認の記録） | 保留の状態が claim-svc（保留の記録）と payment-svc（集計の行の保留の印）の 2 か所にあり、「payment-svc が書けたときだけ claim-svc は保留を記録する」としか書いていない。payment-svc が印を書いた（消した）後に応答が失われると、claim-svc は失敗を返すので 2 か所が食い違う。保留では安全側（印はある）だが、保留の解除では、payment-svc は印を消して実行に戻したのに、claim-svc と画面は「保留」のままになりうる。H25 の頼み直しを同じ操作で安全に繰り返せること（印の書き込み・削除が冪等）と、実行の可否の正は payment-svc の印だけであること、食い違いを見つける突き合わせを書く | Minor | 候補の漏れ | op-one-time（開いた問い） |

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| q-value-vocabulary | Yes | scope は TTS が社員の台帳の役割の ID から出し（名前で照合しない）、acr は情報セキュリティ部の決めた URN の 2 値、agency_code は ^AG[0-9]{6}$ の変わらない番号で、代理店の IdP の値を通さない |
| q-identifier-choice | Yes | 代理店の IdP の sub は C-sub の upstream_issuer に (iss, sub) の組で書かれ、identifier_properties と on_missing（拒否）がある。付け替えの限界は 3.1 の見送り |
| ap-1-7（C-agency-code） | Yes | 書けるのは代理店管理部（as-admin-api、2 人の操作、phr）と DB の直接の修正（変更の番号と業務の持ち主の承認）だけで、代理店とその IdP の管理者は書けない。ただし書き込みの口の守りは F2 |
| ap-1-7（C-client-id） | Yes | claim-portal・staff-console は IT 基盤部の変更の手続き、代理店のクライアントは代理店の登録（代理店管理部）からだけ作る |
| ap-1-7（C-act） | Yes | TTS だけが書き、値は検証した EMPLOYEE_AT の sub と、IVR だけが書く通話の記録の担当の社員の一致から決まる。役割は人事部だけが付ける |
| q-freshness-mitigation | Yes | C-scope（許容 600・遅れ 390）・C-agency-code（許容 900・遅れ 390）は TTS の発行のたびの確認で収まり、PAY_MSG_CTX の 3630 秒は作り直しのたびの確認（9.2）で対策がある。C-client-id・C-act は寿命の間に変わらない |
| q-single-aud-resource | Yes | AT は口ごとに aud が 1 つ（max_items 1、2 つ以上は拒む）。Txn-Token は信頼ドメインの 1 つで、受け手ごとの絞り込みは mTLS の相手の一覧と tctx の operation で行う |
| q-no-passthrough | Yes | TTS は要求できるワークロードを SPIFFE ID の一覧で決め（PAY_MSG_CTX は assessment-svc だけ、作り直しは payment-worker だけ、自分の ID は payment-batch だけ）、scope は経路の表と役割で絞り、Txn-Token を subject_token とする Txn-Token の要求を拒む |
| q-step-up-path-coverage | Yes | 承認の記録を書けるのは payment-svc の承認の API（front-gw からだけ）だけで、そこで phr と 300 秒を確かめる。管理の変更は as-admin-api のすべての変更の API で確かめる。保留の解除に求めない理由が無い点は F3 |
| ap-2-7 | Yes | コールセンターの社員の TXN_STAFF（sub が stf_）は claim-svc が査定の経路の外では受けず、契約者を sub にした act の無いトークンは PH_AT からしか作れない |
| q-authorize-service-and-user | Yes | どのホップでも受け手が mTLS の相手の SPIFFE ID を一覧と照らし（例：承認は front-gw、指示は payment-worker、実行は payment-batch、保留は claim-svc）、利用者の権限（sub・scope・tctx）と別に決めている |
| q-agent-short-lived-no-rt | Yes | 代理の主体（コールセンターの社員）には RT を出さず（shirogane-sso は RT を出さない）、TXN_PROXY は 60 秒で本人確認から 1800 秒を超えない |
| q-outside-catalog | No | 管理の口・テストの口（U30）・旧経路（U29）・障害時の再送（判定のやり直し）・DB の直接の修正・手作業の振込（作らない）は答えてあるが、as-admin-api から shirogane-as への書き込みの経路の守りが書いていない（F2） |
| q-object-level-authz | Yes | 請求は claim-svc が持ち主・取扱代理店・割り当てと課で、書類は前段の claim-svc・assessment-svc が、支払いは payment-svc が記録で止める（404・409）。document-svc の自分での確かめの見送りは 3.1 に毎日の突き合わせつきで書いてある |
| q-approval-from-as | Yes | 承認は申告でなく payment-svc の承認の記録で、payment_id・金額・payee_ref・承認者に結びつき、実行の取引の中で記録と照合する。宛先は payment-svc だけで、別の相手に使い回す経路が無い |
| q-operator-act | Yes | 管理の操作は社員本人の sub の TXN_STAFF、代理受付は act、DB の直接の修正は変更の番号と DB の管理者を行に残し、なりかわりの経路を作らない（2.2） |
| q-revocation-delivery | Yes | 止める単位ごとに最悪を並べてある（契約者 390・代理店 390・代理店の担当者 750・社員 390・紛失 330・鍵 810／690 秒）。寿命は分数から導かれ、却下した Back-Channel Logout・SSF の代わりに TTS の毎回の確認がある |
| q-dependency-outage | Yes | TTS・状態の参照・JWKS が応えなければ拒む、CRL は前の CRL で最長 3600 秒、社員の台帳・IVR は社員の口だけを止める、fraud-svc は判定待ち、夜間に応えなければ次の夜、と倒し方と業務の影響が書いてある |
| dc-05（F1 で足した） | Yes | tctx の 9 項目はすべて文字列で、amount は先頭の 0 と符号の無い 10 進、value_normalization は exact。JSON Schema が内側を確かめない点は 3.1 の見送りで試験に回してある |
| pa-01 | Yes | agency_code は TTS が登録と照らし、claim-svc が証券の取扱代理店との一致で請求を絞る（25 問の回答は claim_request_agency_code.md） |
| q-derived-value | Yes | 個人情報の行（sub・act・tctx）は届く受け手が記録・照合に使い、口座は payee_ref、傷病・IP・全証券は載せない。tctx の項目は operation ごとに経路の表が必要な分だけにする |
| q-variant-comparison | Yes | PH_AT・EMPLOYEE_AT の束縛の見送りは、mTLS（SVID が 1 時間で替わる）と DPoP（鍵が BFF の同じサーバー）を比べ、開く攻撃（口に接続できる SVID を持つ者だけが使える）と確かめ方（CI の口の設定の試験・ログの走査）を書いてある |
| q-idp-diff-absorbed | Yes | TTS が入口で主体を 1 つの形にし、内側は TTS の iss だけを受け、外の AT は front-gw と TTS で止まる |
| q-original-principal | Yes | 下流は受け取ったまま Txn-Token を渡し、仲介のサービスが自分の資格情報で書かない。作り直しでも sub は査定を確定した社員で、scope は payments:instruct だけ |
| q-step-up-by-rs | Yes | payment-svc と as-admin-api が acr・auth_time を確かめて 401 を返し、staff-console は案内だけ |
| q-long-running | Yes | ブローカーで待つ間は PAY_MSG_CTX だけを持ち、作り直しのときに TTS が勤務の状態と役割を、payment-svc が版と保留を確かめ直す。受け付けた指示を退職の後も有効にする判断は 9.1 に書いてある |
| q-copies-outlive | Yes | 写しは監査ログ（HMAC、7 年、読めるのは監査部とセキュリティの担当）と不正の判定の記録（90 日）で、判断の結果のキャッシュは置かない（U21）。分析用の複製は作らない（U28） |
| q-audit-correlation | Yes | txn を PAY_MSG_CTX からの作り直しにも引き継ぎ、承認・実行は payment_id と claim_id で、sub・act は同じ基盤の同じ HMAC の鍵でつなぐ（REQ-09） |
| op-proof-holder（開いた問い） | 該当なし | 辿った範囲と気づきを 4. に書いた（持つ者と鍵を持つ者は一致） |
| op-source-change（開いた問い） | 該当なし | 辿った範囲と気づきを 4. に書いた |
| op-one-time（開いた問い） | 該当なし | 辿った範囲と気づきを 4. に書いた（F4） |

答えなかった問い：開いた問い（さらに）の op-key-custody・op-requirement-words（時間の都合）。専門家に回す候補：shirogane-sso が「ハードウェアの鍵での認証のときだけ phr を書く」ことの実装（鍵の種類の見分け方。`review:escalation#unverified-idp-behavior`）と、設計書の 12. で書き手が挙げた PAY_MSG_CTX の subject_token の型。
