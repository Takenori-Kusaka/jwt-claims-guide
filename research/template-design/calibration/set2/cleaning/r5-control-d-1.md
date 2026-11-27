# レビューの記録：designs/target（しろがね損保　保険金の請求と支払いの内部処理）

- 読んだもの：designs/target/ の design.md・claims.yaml・token_types.yaml・hops.yaml・catalog_answers.yaml・claim_request_agency_code.md、ci-result.txt、sheet.md、short_list.md・perspectives.md（問いの書き方と読み方）・decision_tree.md・kind_tell.md
- 行の抜き取りの種：12（sheet.md のまま）。抜き取った行：`C-agency-code`（組織独自の認可の行として必ず入れる行）・`C-client-id`・`C-act`。答えが No になった問いでは `C-sub`・`C-scope` も見た
- 指摘：Major 2 件・Minor 2 件（Blocker 0 件）

---

## 段 0. CI の結果（機械が確かめること）

- design.md の 1. と ci-result.txt は同じ内容。error 0、warn 9、info 15
- warn の理由は 1. の表に行ごとに書いてある
  - `L1b`（C-req-wl・C-tctx）：草案 -11 の名前で、spec_version と見直しの条件がある。理由は通る
  - `L16`（H4・H7・H15・H17・H23・H26 の aud）：Txn-Token の aud は信頼ドメインで、外の AT の aud と名前が違う。宛先の絞り込みは TTS（`C-aud` の tts の行）と内側の受け手（aud が信頼ドメインだけ）が行い、scope と寿命は上流を超えない（hops.yaml で確かめた）。理由は通る
  - `L16`（H30 の寿命 3600 秒 > 上流 H29 の 300 秒）：理由は「PAY_MSG_CTX は TTS への作り直しにしか使えず、TTS が作り直しのときに社員の在籍・役割と請求の保留を引き直す」。**引き直す項目に、請求の割り当て（担当の査定担当者か）と課が入っておらず、60 分待つ間の異動を拾えない**ので、理由は一部しか通らない → 指摘 F4（`q-hop-lifetime`）
- lint を通すために宣言を曲げた跡（`q-lint-workaround`）：hops.yaml の H5 は H31（AGENCY_ASSERTION）を upstream に置いていない（置けば寿命 300 > 60 で L16 が出る）。理由は「assertion は RFC 7523 の認可の grant で、作り直しの上流ではない」で、認可コード（60 秒）から 600 秒の AT が出るのと同じ形であり、AT が assertion より長く生きる分は代理店の担当者の停止の最悪（750 秒）に入れてある。曲げた跡とはみなさない

## 段 1. 性質の表を、図と要求に照らして確かめた結果

| 性質（sheet.md） | sheet の判定 | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 合う（`C-agency-code`、名前空間つき） |
| 個人情報 | 当たる | 合う（`C-sub`・`C-act`・`C-tctx`・`C-email`） |
| 発行者が複数 | 当たる | 合う（shirogane-as・shirogane-sso・TTS・代理店の IdP 2 社） |
| 交換・作り直し | 当たる | 合う（H4 ほかの reissue、H30・H22・H24 の exchange） |
| 委任 | 当たる | 合う（TXN_PROXY の `C-act`） |
| 操作ごとの承認 | 当たらない | **合わない**。100 万円以上の支払いの承認（REQ-05）は、payment-svc の承認の記録として payment_id・金額・payee_ref に結びついた「1 つの操作への承認」で、tctx の operation に payment.approve・payment.cancel がある。トークンに authorization_details を載せないだけで、性質そのものはある → 指摘 F3。この性質の問い `dc-05` を足して答えた（`q-approval-from-as` はもともと sheet にある） |
| マルチテナント | 当たらない | 合う（しろがね 1 社。代理店の絞り込みは agency_code で、テナントではない） |
| DB の層まで運ぶ | 当たらない | 合う（db_connection のホップが無い。U02 は対象外。9.1 の DB の接続の層も「無い」） |
| 認証の強さ・新しさ | 当たる | 合う（`C-acr`・`C-auth-time`） |
| 送信者制約を選んだ | 当たる | 合う（AGENCY_AT が mtls） |
| 送信者制約を見送った | 当たる | 合う（PH_AT・EMPLOYEE_AT が none。3.1 の見送り） |
| 長時間・非同期 | 当たる | 合う（PAY_MSG_CTX・H20〜H22・夜間の実行） |

## 段 2. 6. の「要る」問いと判断の木の節の比べ

| 問い | 判断の木の節 | 設計の仕組み | 比べた結果 |
| --- | --- | --- | --- |
| q-sub | keep-sub-exchange | Txn-Token の sub。作り直し（H22）でも査定を確定した社員の sub を保ち、TTS が作り直しのたびに状態を引く。夜間の実行は payment-batch 自身の ID（利用者の sub を捏造しない） | 合う |
| q-actor（UC3） | keep-sub-exchange | TXN_PROXY の act（最も外側だけ、入れ子なし。H15 で入れ子を拒む） | 合う。入れ子の act で照合する文は無い |
| q-actor（UC4 は不要） | keep-sub-exchange | payment-worker は act に入れず、req_wl と mTLS で記録 | 節は「ワーカーが自分の ID で交換し、可否はそのたびに AS が決める」で、その部分は満たす。act に入れない理由（中身を変えられない運び手）が 6. と catalog_answers に書いてあり、取り違えの例（act で取引を表す・req_wl を直接の相手とみなす）にも当たらない。指摘にしない |
| q-txn・q-req-wl | txn-tctx | tctx を TTS だけが書き、Txn-Token ヘッダーで改変せずに渡す | 合う。tctx を受けるホップの受け手（claim-svc・fraud-svc・document-svc・assessment-svc・payment-svc・as-admin-api）のすべてに、本文・パス・記録との照合が hops の validates と `C-tctx` の enforced_at にある。AT と同じヘッダー・部品で受けていない（Authorization を読まない、typ を分ける） |
| q-peer | peer-mtls | SPIFFE の X.509-SVID の mTLS、代理店は代理店向けの CA の証明書。拇印のヘッダーは front-gw だけが書く | 合う。req_wl・act・client_id で直接の相手を代えていない |
| q-authorized（UC5） | rar-vs-custom | scope（payments:approve）＋acr・auth_time、承認そのものは payment-svc の記録 | 合う。authorization_details を検討し、承認を確かめるのが payment-svc だけなのでトークンで運ばない理由を 3.1 に書いている。ロールで承認を代用していない |
| q-authorized（UC1〜UC7）・q-user | carry-or-query | 役割・承認の上限額・証券は問い合わせ、agency_code は載せる | 合う（M_authz_pdp の 2.） |
| q-holder（UC2） | existing-claim-first | cnf の x5t#S256 | 合う |
| q-resource | — | aud（AT は口ごとに 1 つ、Txn-Token は信頼ドメイン） | 合う |
| 寿命（q-still-valid に当たる部分） | lifetime-by-situation | 剥奪は TTS の毎回の状態の確認、寿命は盗まれたときの時間で決める | 合う（ただし異動の経路は F2） |

判断の木と仕組みが食い違う行（目的と仕組みの不一致）は見つからなかった。

## 段 3. 優先 1 の問いへの回答（1 行ずつ）

抜き取った行：`C-agency-code`・`C-client-id`・`C-act`。

- **q-value-vocabulary**　Yes。agency_code は AG＋6 桁の変わらない番号で名前でない。client_id・act.sub（stf_）も変わらない ID。役割は社員の台帳の役割の ID で TTS が scope に替え、代理店の IdP の値（同じ文字列）を役割として通す経路は無い
- **q-identifier-choice**　Yes。IdP ごとに違うキー（代理店の IdP の sub）は `C-sub` の upstream_issuer で (iss, sub) の組から agst_ に替え、identifier_properties と on_missing がある。client_id・agency_code にも identifier_properties・on_missing がある
- **ap-1-7**　Yes。agency_code は代理店管理部（as-admin-api、2 人の操作、ハードウェアの鍵）と承認つきの DB の直接の修正だけ。client_id は IT 基盤部の変更の手続きと代理店の登録。act は TTS が EMPLOYEE_AT の sub・人事部が付けたコールセンターの役割・IVR だけが書く通話の記録から書く。代理店とその IdP の管理者は agency_code を書けない
- **q-freshness-mitigation**　Yes（抜き取った 3 行）。agency_code は許容 900 秒に 390 秒、act は寿命 60 秒で通話の記録を毎回引く（150 秒）、client_id は寿命の間に変わらない。止めるのは TTS の毎回の確認（キャッシュ 60 秒）
- **q-single-aud-resource**　Yes。どの種別も aud は 1 つ（`C-aud` の max_items 1、2 つ以上は受け手が拒む）
- **q-no-passthrough**　Yes。作り直しは TTS だけで、頼めるワークロードは mTLS の相手で決まる（front-gw・PAY_MSG_CTX は assessment-svc・作り直しは payment-worker・自分の ID は payment-batch）。scope は経路の表と今の役割で絞り、Txn-Token からの作り直しは拒む
- **q-step-up-path-coverage**　Yes。承認・取り消しは payment-svc の H23 の API だけ（相手は front-gw だけ）、管理の操作は as-admin-api の H26 だけで、どちらも受け手が acr と auth_time 300 秒を確かめる。非同期・代理の経路からは承認を書けない（付録 B）
- **ap-2-7**　Yes。コールセンターの役割に出る scope は TXN_PROXY だけで、claim-svc は front-gw からの stf_ の sub を受けない。act の無いトークンで契約者の請求を出す経路は無い
- **q-authorize-service-and-user**　Yes。すべての受け手が呼び出し元の SPIFFE ID を一覧と照らし（hops の validates）、利用者の scope・sub とは別に決めている
- **q-agent-short-lived-no-rt**　Yes。代理の社員は staff-console の EMPLOYEE_AT（RT を出さない）と 60 秒の TXN_PROXY だけ
- **q-outside-catalog**　Yes。管理の口（as-admin-api）、DB の直接の修正（2.2）、判定のやり直し（トークンなし）、試験の口（U30）、旧経路（U29）、障害時の扱い（3.1・H24 の「次の夜に回す」、手作業の振込は作らない）が答えられている
- **q-object-level-authz**　Yes。請求は claim-svc（持ち主・取扱代理店・割り当て）、書類は前段（claim-svc・assessment-svc）と毎日の突き合わせ、支払いは payment-svc の記録で止まる（M_authz_pdp の 3.）
- **q-approval-from-as**　**No**。承認は申告でなく payment-svc の記録と照合され payment_id・金額・payee_ref に結びつくが、「承認してよい上長」を決める課の基準が、payment-svc（査定者の今の課）と assessment-svc（割り当ての記録の課）で食い違う → F1
- **q-operator-act**　Yes。管理者は自分の TXN_STAFF で操作し記録に sub と txn が残る。なりかわりの経路は作らず、DB の直接の修正は変更の番号を残す（2.2）
- **q-revocation-delivery**　**No**。止める単位ごとの表（9.1）は退職・休職・役割の変更・代理店・鍵・紛失で揃うが、査定担当者が課を移る異動（役割は残る）では、請求の割り当てが残り、誰がいつまでに外すかが無い → F2
- **q-dependency-outage**　Yes。TTS・状態の参照・JWKS は拒む、CRL は 3600 秒の後に口を止める、社員の台帳・通話の記録は社員の口だけ止まる、夜間に頼る先が応えなければ次の夜（3.1・H24）
- **dc-05**（段 1 で足した）　Yes。tctx の内側は 9 項目すべて文字列で、amount は先頭の 0 と符号の無い 10 進の文字列、比べ方は exact（`C-tctx` の description・value_normalization、付録 D の P5 の 2.）。生成の JSON Schema が内側を見ないことは 3.1 の見送りで、試験と共通部品で確かめるとしている

## 段 4. 開いた問い

### op-proof-holder（鍵の持ち主を確かめる箇所）

辿った範囲：`C-cnf` の enforced_at（front-gw・TTS）、AGENCY_AT の holder・sender_constraint、H31・H5・H6、M_sender_constraint の 2.・4.。

| 箇所 | トークンを持つ者 | 確かめる側が見る鍵 |
| --- | --- | --- |
| shirogane-as のトークンの端点（H31） | 代理店のサーバー | 代理店のサーバーの証明書（tls_client_auth）。その拇印を cnf に書く |
| front-gw の代理店の口（H5） | 代理店のサーバー | 同じ接続の TLS の証明書の拇印と cnf の x5t#S256 |
| TTS（H6） | front-gw（subject_token として） | front-gw が書いた拇印のヘッダー（代理店から来た同名のヘッダーは捨て、TTS は front-gw の SPIFFE ID からだけ読む） |

気づいたこと：どの箇所も「持つ者」と「鍵の持ち主」が一致する。証明書の更新は同じサブジェクトの新しい鍵で、古い拇印に束縛した AT は最大 300 秒で使えなくなり新しい assertion で取り直す（RT は無い）。残る限界は CRL を取り直せない間の最長 3600 秒で、3.1 に受け入れと確かめ方がある。指摘なし。

### op-source-change（権限の元データが変わる出来事）

選んだ出来事：**査定担当者が別の課に異動する（査定担当者の役割は残る）**。比べるために退職も辿った。

- 元のデータ：社員の台帳の「課」。書くのは人事部の担当者で、責任者の承認の時点で変わる（9.2 の元のデータからの経路）。しろがねの IT の部品からは書けない
- TTS：役割は変わらないので scope も変わらない。勤務の状態も勤務中のまま
- claim-svc の請求の割り当て：書き換える経路は上長の assessment.assign だけ。**異動をきっかけに割り当てを外す人・時間が、どこにも書かれていない**（9.1 の社員の行は退職・休職と役割の変更だけで、ブローカーで待つ指示の扱いも「上長が割り当てを替え」と書くが、異動では止まらないので替わる契機が無い）
- assessment-svc：割り当ての記録で査定担当者を確かめるので、移った社員は前の課の請求の査定の確定と、要配慮の書類の閲覧（H19）を続けられる。上長の閲覧は「割り当ての記録の課」と上長の課で照らす
- TTS の作り直し（H22）：在籍・役割・保留だけを引き直し、割り当てを見ない
- payment-svc の承認（H23）：承認者が「社員の台帳の、査定者の今の課」の上長であること。異動の後は、新しい課の上長が承認・取り消しでき、前の課の上長（割り当ての記録の課の上長で、査定を見られる人）は承認も取り消しもできない
- 気づいたこと：誰も時間を約束していない区間（異動から割り当ての付け替えまで）と、2 つのサービスで課の基準が違う箇所がある → F1・F2。退職・休職は TTS の毎回の確認で 390 秒以内に止まり、ブローカーで待つ指示も作り直しで止まる（問題なし）

### op-one-time（1 回だけ使える値）

辿った範囲：AGENCY_ASSERTION の jti、AUTH_CODE、nonce、セキュリティキーの登録の番号（2.2・H26）、支払いの指示（(claim_id, assessment_ref) の一意の制約）、支払いの実行（行のロック）、承認の記録。

- 並行の 2 件：jti は一意の制約つきの 1 回の書き込み、登録の番号は「未使用 → 使用済み」の条件つきの書き込み、指示は一意の制約、実行は支払いの行のロックで、どれも 1 件だけ通る
- 通信が切れた後の再送：指示は payment-worker が受け付けの後にだけ処理済みにし、2 件目は前の結果が返るので、正しい 1 件も失われない。assertion は 2 回目を拒むので、応答を失った代理店は新しい assertion で取り直す（正しい 1 回の結果は残る）
- 記録先の障害：jti・登録の番号は記録先が応えなければ拒む（止める側に倒れる）
- 気づいたこと（指摘にはしない）：(1) claim.submit の tctx には重複を見分ける値（claim_id など）が無く、front-gw と claim-svc の間で切れた後の再送で請求が 2 件できうる。1 回だけ使う値の問題ではないが、受付の重複の扱いを 1 行書いておくとよい。(2) 登録の番号を社員本人にどう渡すか（窓口で手渡すのか）が 2.2 に無い。番号は対象の社員のパスワードのセッションでだけ使えるので、パスワードが漏れた社員では渡し方が守りの全部になる

## 段 5. 優先 2 の問い（時間が残ったので答えた）

- **pa-01**　Yes。agency_code は claim-svc が「その代理店が扱う証券の請求だけ」を決めるために読み、TTS は登録と同じかを確かめる（claim_request の問 1）
- **q-derived-value**　Yes。tctx は operation ごとに要る項目だけを載せ（policy_number は claim.submit だけ）、口座は参照 ID、傷病・IP は載せない。act は読む claim-svc・fraud-svc にだけ届く
- **q-variant-comparison**　Yes。PH_AT・EMPLOYEE_AT の送信者制約の見送りで、mTLS の束縛（SVID が替わる）と DPoP（鍵が BFF に同居）を、BFF が破られたとき・ログから漏れたときで比べ、代わりの守り（口の mTLS の相手の制限）と確かめ方を書いている
- **q-idp-diff-absorbed**　Yes。内側の受け手は TTS の iss だけを受け、代理店の IdP の sub は shirogane-as が agst_ に替える。外の発行者の種別が作り直されずに内側へ届くホップは無い
- **q-original-principal**　Yes。作り直しの後の sub は元の利用者（査定を確定した社員・契約者）で、仲介のサービスは自分の資格情報で下流を呼ばない（H10・H18）
- **q-step-up-by-rs**　Yes。payment-svc・as-admin-api が決め、staff-console は案内だけ（付録 B）
- **q-long-running**　Yes（異動は F2）。60 分待つ指示は作り直しのときに在籍・役割・保留を確かめ直し、夜間の実行は承認・保留・振込先を実行の取引の中で確かめる。利用者のトークンを持ち越さない
- **q-copies-outlive**　Yes。監査ログ（HMAC、7 年、読める者を限る）、fraud-svc の判定の記録（90 日）、TTS の状態のキャッシュ（60 秒）、BFF のセッション（API の呼び出しはすべて TTS を通る）を挙げている
- **q-audit-correlation**　Yes。txn を PAY_MSG_CTX から作り直しにも引き継ぎ、承認は payment_id と承認の txn で、外の AT は front-gw の 1 行（iss・jti・txn）でつなぐ。sub・act の HMAC の鍵は監査ログの基盤の 1 つで、途中で作り方が変わらない

### さらに（開いた問い。短く辿った）

- op-clock：auth_time（shirogane-sso）と payment-svc、TTS と受け手はしろがねの NTP。IVR の時刻と代理店の IdP の iat は別の時計で、12. に未確認として挙げ、assertion は拒む側に倒している。追加の指摘なし
- op-key-custody：shirogane-as・shirogane-sso・TTS（HSM・IT 基盤部・気づいてから 810 秒）、代理店の IdP（知らせから 690 秒）、代理店向けの CA・SPIFFE の CA（M_token_validation の 8.）まで数えている。追加の指摘なし
- op-requirement-words：「上長」は「査定者と同じ課の上長」と読んでいるが、課が変わったときの扱いが無い（F1・F2 と同じ根）。「契約者」は被保険者・受取人を入れない、「社員」は委託先を入れないと 2.1 に書いてある（コールセンターを委託にするなら REQ-11 の経路が無くなる点は、要求の持ち主に確かめる価値がある）

---

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | claims.yaml `C-sub` の enforced_at の payment-svc の行（「承認の sub は、社員の台帳で査定者と同じ課の上長」）と assessment-svc の行（「割り当ての記録の課と、社員の台帳の上長の課を照らす」）。hops.yaml H23 の validates（4 つ目）。design.md 付録 D の M_authz_pdp の 3.（請求の行）・付録 B（1 行目）・9.2 の元のデータからの経路（社員の台帳の行）。問い：q-approval-from-as | 「承認・取り消しをしてよい上長」の課の基準が 2 か所で違う。payment-svc は査定者の**今の**課（社員の台帳を要求のたびに引く）で、assessment-svc は**割り当ての記録の**課で上長を決める。査定担当者が課を移ると、査定を見られない新しい課の上長が 100 万円以上の支払いを承認・取り消しでき、査定を見て管理している前の課の上長は承認も取り消しもできない。REQ-05 の「別の上長が承認する」の意図（査定を見られる上長の確認）が異動 1 回で崩れ、REQ-04 の取り消しの担い手も変わる。どちらの課を正とするかを決め、payment-svc も同じ基準（割り当ての記録の課、または確定の時点の課を支払いの記録に残す）で照らす | Major | 実装とのずれ | q-approval-from-as、op-source-change |
| F2 | design.md 9.1 の止める単位の表（社員の行）・9.2 の元のデータからの経路（社員の台帳の行）。hops.yaml H17（3 つ目の check）・H19・H22（1 つ目の check：在籍・役割・保留だけを引き直す）。claims.yaml `C-sub` の assessment-svc の行。3.1 の見送り（REQ-03 の起点。異動を REQ-03 の出来事に数えている）。問い：q-revocation-delivery | 査定担当者が別の課に異動したとき（役割は残る）、claim-svc の請求の割り当てを外す人・経路・時間がどこにも無い。移った社員は、前の課の請求の査定の確定と要配慮の書類の閲覧（REQ-08 の「割り当てた査定担当者」）を続けられ、ブローカーで待つ指示も TTS の作り直し（H22）を通る（割り当てを見ない）。設計は 3.1 で異動を REQ-03（600 秒）の出来事に数えているのに、止まるまでの最悪が書けない。異動を契機に割り当てを外す（または assessment-svc・TTS が割り当ての課と社員の今の課を照らす）経路と時間を書き、9.1 の表に行を足す | Major | 候補の漏れ | q-revocation-delivery、op-source-change（判断の木 lifetime-by-situation） |
| F3 | sheet.md の 1. の「操作ごとの承認がある」（当たらない）。設計の該当箇所：design.md REQ-05・3.1 の見送り（承認を authorization_details に載せない）・付録 B、hops.yaml H23、claims.yaml `C-tctx` の operation（payment.approve・payment.cancel） | 性質の表は authorization_details と「approval」の名前だけで読み、当たらないとした。設計には 1 件の支払い（payment_id・金額・payee_ref）に結びつく承認があり、承認の記録を payment-svc が照合している（トークンに載せないだけ）。性質は当たる。足した問い dc-05 には Yes と答えた（tctx の内側の型と比べ方は決まっている）。読み方の条件に「承認の記録を受け手が持つ設計」と scope・operation の approve を足すとよい | Minor | 前提の誤り | dc-05、q-approval-from-as |
| F4 | design.md 1. の warn の理由の表（`L16`・`H30` の行）、hops.yaml H30 の narrowing_exception、token_types.yaml PAY_MSG_CTX の revocation（db_lookup）。lint の warn：L16 H30「寿命 3600 秒が上流（H29）の 300 秒を超える」 | 下流の PAY_MSG_CTX（3600 秒）が上流の TXN_STAFF（300 秒）の 12 倍生きる理由は「TTS が作り直しのときに社員の在籍・役割と請求の保留を引き直す」だが、引き直す項目に請求の割り当て（指示した社員が今もその請求の担当か）と課が無い。60 分の間の異動（F2）は寿命の延長で開いたままになるので、理由は延長を支え切っていない。作り直しの確かめに割り当てを足すか、理由に限界として書く。あわせて、理由が「5.1 に書いた」と言う 5.1 の PAY_MSG_CTX の行は上限 3600 秒を書くだけで、上流より延ばす例外の説明が無い | Minor | 理由の不備 | q-hop-lifetime |

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| q-value-vocabulary | Yes | agency_code・client_id・act.sub は変わらない ID で、役割は社員の台帳の役割の ID から TTS が scope に替える |
| q-identifier-choice | Yes | 代理店の IdP の sub は upstream_issuer で (iss, sub) から agst_ に替え、行に identifier_properties と on_missing がある |
| ap-1-7 | Yes | agency_code は代理店管理部の 2 人の操作と承認つきの DB の修正だけ、act は TTS が人事の役割と IVR の記録から書く |
| q-freshness-mitigation | Yes | agency_code は許容 900 秒に 390 秒、act は 60 秒で通話の記録を毎回引き、client_id は変わらない |
| q-single-aud-resource | Yes | どの種別も aud は 1 つで、2 つ以上は受け手が拒む |
| q-no-passthrough | Yes | 作り直しは TTS だけで、頼める相手は mTLS の ID、範囲は経路の表と今の役割で決まる |
| q-step-up-path-coverage | Yes | 承認・取り消しは H23、管理は H26 の 1 経路だけで、受け手が acr と auth_time を確かめる |
| ap-2-7 | Yes | コールセンターの役割は TXN_PROXY だけで、claim-svc は front-gw からの stf_ の sub を受けない |
| q-authorize-service-and-user | Yes | すべての受け手が呼び出し元の SPIFFE ID を一覧と照らし、利用者の権限とは別に決める |
| q-agent-short-lived-no-rt | Yes | 代理の社員は RT の無い EMPLOYEE_AT と 60 秒の TXN_PROXY だけを使う |
| q-outside-catalog | Yes | 管理の口・DB の直接の修正・判定のやり直し・試験の口・旧経路・障害時の扱いが書いてある |
| q-object-level-authz | Yes | 請求は claim-svc、書類は前段のサービスと毎日の突き合わせ、支払いは payment-svc の記録で止まる |
| q-approval-from-as | No | 承認は記録と照合されるが、承認できる上長の課の基準が payment-svc と assessment-svc で違う（F1） |
| q-operator-act | Yes | 管理者は自分の TXN_STAFF で動き、なりかわりの経路が無く、DB の修正は変更の番号を残す |
| q-revocation-delivery | No | 課を移る異動では請求の割り当てが残り、止まるまでの最悪が書けない（F2） |
| q-dependency-outage | Yes | TTS・状態の参照・JWKS は拒み、CRL・社員の台帳・夜間の実行の倒し方も決まっている |
| dc-05 | Yes | tctx の 9 項目はすべて文字列で、金額の形と exact の比べ方が決まっている（段 1 で足した問い） |
| q-hop-lifetime | No | H30 の 3600 秒 > 上流 300 秒の理由に、割り当ての引き直しが無い（F4） |
| op-proof-holder | 該当なし | 開いた問い。どの箇所も持つ者と鍵の持ち主が一致し、指摘なし |
| op-source-change | 該当なし | 開いた問い。異動を辿り、割り当てと課の基準の抜けを見つけた（F1・F2） |
| op-one-time | 該当なし | 開いた問い。並行・再送・記録先の障害で 2 回通る値は無い。請求の再送の重複は気づきとして記録 |
| pa-01 | Yes | claim-svc が代理店の扱う証券の請求だけに絞るために読む |
| q-derived-value | Yes | tctx は operation ごとに要る項目だけで、口座は参照 ID、傷病・IP は載せない |
| q-variant-comparison | Yes | 送信者制約の見送りで mTLS と DPoP を攻撃の場面ごとに比べ、代わりの守りと確かめ方がある |
| q-idp-diff-absorbed | Yes | 内側は TTS の iss だけを受け、IdP ごとの差は入口と shirogane-as で吸収する |
| q-original-principal | Yes | 作り直しの後も sub は元の利用者で、仲介のサービスは自分の資格情報で下流を呼ばない |
| q-step-up-by-rs | Yes | 操作を受ける payment-svc・as-admin-api が決め、画面は案内だけ |
| q-long-running | Yes | 作り直しと実行の時点で在籍・役割・保留・承認を確かめ直す（異動の抜けは F2） |
| q-copies-outlive | Yes | 監査ログ・判定の記録・状態のキャッシュ・BFF のセッションを挙げ、残る期間を書いている |
| q-audit-correlation | Yes | txn を作り直しにも引き継ぎ、承認は payment_id で、主体は同じ鍵の HMAC でつながる |
