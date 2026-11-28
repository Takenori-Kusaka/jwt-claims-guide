# レビューの報告：designs/target（しろがね損保　保険金の請求と支払いの内部処理）

- 対象：designs/target/design.md と台帳（claims.yaml・token_types.yaml・hops.yaml・catalog_answers.yaml）
- 問いの 1 枚：sheet.md（行の抜き取りの種 12。抜き取った行：C-agency-code・C-client-id・C-act）
- CI（ci-result.txt）：error 0、warn 9、info 15。設計書の 1. の貼り付けと一致
- 読んだ教材：short_list.md・perspectives.md（重大度の目安）・decision_tree.md・contrasts/act-txn-workload.md・kind_tell.md
- 指摘：Major 2 件、Minor 2 件（Blocker 0 件）

## 段 0：CI の結果と warn の理由

- error 0 を確かめた。warn 9 件のすべてに、設計書の 1. の「残す理由」の表で理由が付いている
  - L1b（C-req-wl・C-tctx）：草案 -11 の名前で、spec_version と見直しの条件がある。通る
  - L16 の aud（H4・H7・H15・H17・H23・H26）：Txn-Token の aud は信頼ドメインで、TTS が「AT の aud が front-gw の書いた口と一致すること」を確かめ（C-aud の tts の行）、内側は aud を shirogane-sonpo.internal だけにする。scope と寿命は上流を超えない（H4 の 300 秒 ≤ H3 の 600 秒など）。通る
  - L16 の寿命（H30：PAY_MSG_CTX 3600 秒 > 上流 H29 の TXN_STAFF 300 秒。q-hop-lifetime）：REQ-06（ブローカーで最大 3600 秒）から来る。PAY_MSG_CTX は TTS の作り直しの要求にしか使えず、作り直しのたびに TTS が社員の在籍・役割と請求の保留を引き直す（H22）。`narrowing_exception` に理由がある。通る
- 宣言を曲げた跡（q-lint-workaround）：H31 を H5 の upstream に置かない理由（assertion は RFC 7523 の grant で、AT の値は代理店の登録の方針で決まる）は H31 の note にあり、妥当と判断した

## 段 1：性質の表を、図と要求に照らして確かめた結果

| 性質 | sheet.md | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | C-agency-code（名前空間つき、authz）。正しい |
| 個人情報を載せる | 当たる | C-sub・C-act・C-email・C-tctx が 個人情報。正しい |
| 発行者が複数 | 当たる | shirogane-as・shirogane-sso・TTS・代理店の IdP 2 社。図の B3・B4 と合う |
| 交換・作り直し | 当たる | H4・H7・H15・H17・H23・H26（reissue）、H22・H24・H30（exchange）。正しい |
| 委任がある | 当たる | C-act（TXN_PROXY。電話の代理受付）。正しい |
| 操作ごとの承認 | 当たらない | authorization_details の行もホップも無いのは正しい。100 万円以上の支払いの承認（REQ-05）は操作ごと（payment_id・金額・payee_ref に結びつく）だが、トークンに載せず payment-svc の承認の記録で確かめる設計（3.1 の見送り）。トークンの性質としては「当たらない」でよいと判断した。念のため dc-05 も見た：オブジェクト型の tctx は、内側の型（9 項目すべて文字列）と比べ方（value_normalization の compare: exact、amount の正規化）が C-tctx の description と付録 D の P5 の 2. に決まっている（JSON Schema が内側を見ないのは 3.1 の見送り）。指摘にしない |
| マルチテナント | 当たらない | lite_criteria.multitenant が false で、代理店ごとの絞り込みは証券の取扱代理店で行う。図にテナントの境界も無い。正しい |
| DB の層まで運ぶ | 当たらない | db_connection のホップが無く、9.1 の DB の接続の層の表も「無い」。正しい |
| 認証の強さ・新しさ | 当たる | C-acr・C-auth-time（REQ-05）。正しい |
| 送信者制約を選んだ | 当たる | AGENCY_AT の mtls。正しい |
| 送信者制約を見送った | 当たる | PH_AT・EMPLOYEE_AT・Txn-Token の none。正しい |
| 長時間・非同期 | 当たる | sheet.md は PH_AT の long_running を読んだ欄に挙げるが、PH_AT の値は「長い処理には使わない」。性質が当たる本当の根拠は H20・H21（broker_connection）と U13 の「該当」（PAY_MSG_CTX）。結論は正しい |

性質の表の結論はすべて正しく、足す問いは無い。

## 段 2：6. で「要る」とした問いと、判断の木の節の比べ

| 問い | 判断の木の節 | 設計の仕組み | 比べた結果 |
| --- | --- | --- | --- |
| q-sub（UC1〜UC7） | keep-sub-exchange | TTS が sub を保って Txn-Token に作り直す。PAY_MSG_CTX からの作り直しでも sub は社員のまま。payment-batch は自分の SPIFFE ID（利用者の sub を作らない） | 合う。UC4 で payment-worker に act を付けない点は、木の「act＝仲介するワーカー」から外れるが、payment-worker は中身を変えられない運び手で、運んだワークロードは req_wl と mTLS で記録する、と 6. と catalog_answers の q-actor に理由がある。運び手を q-actor に数えない判断は筋が通るので指摘にしない |
| q-actor（UC3） | keep-sub-exchange の「確かめること」 | act は TXN_PROXY だけ、入れ子なし（act.sub が stf_ で入れ子が無いことを claim-svc・fraud-svc が確かめる。max_delegation_depth 1） | 合う。最も外側の act だけを使う |
| q-req-wl・q-txn | txn-tctx | 専用の Txn-Token ヘッダー。tctx をホップの受け手のすべてが本文と照合する（H4・H7〜H11・H15〜H19・H22〜H26） | 照合は合う。ただし payment.instruct の tctx に policy_number が入るかで、台帳・ホップと P5 の表が食い違う（指摘 F2） |
| q-peer | peer-mtls | すべてのホップで mTLS の SPIFFE ID。req_wl を直接の相手に使わない（C-req-wl の not_meaning） | 合う |
| q-authorized | carry-or-query・rar-vs-custom | scope（TTS が社員の台帳の役割から絞る）・acr・auth_time・agency_code。承認は payment-svc の記録 | 合う。役割は問い合わせ（C-roles 却下）、agency_code は変わらない小さな値で載せる。取引の承認はトークンでなく受け手の記録で、オブジェクト単位の許可を受け手に置く木の方針と合う |
| q-holder（UC2） | existing-claim-first（cnf） | cnf の x5t#S256（RFC 8705） | 合う |
| q-resource | — | aud は 1 つ（max_items 1、2 つ以上は拒む） | 合う |
| q-still-valid（寿命） | lifetime-by-situation | 寿命 300〜600 秒＋TTS が発行のたびに状態を引く（キャッシュ 60 秒） | 合う。数字は REQ-01〜03 の秒数から導いている |

迷った点（act と req_wl の切り分け）は contrasts/act-txn-workload.md の「解く問い」で確かめた。設計は act を q-actor、req_wl を q-req-wl、mTLS を q-peer に分けている。

## 段 3・段 5：問いへの答え

答えは末尾の表 (2)。No の問いは指摘の一覧 (1) に書いた。

## 段 4：開いた問い

### op-proof-holder（鍵の持ち主）

- 辿った範囲：C-cnf の enforced_at（front-gw・tts）、AGENCY_AT の holder・sender_constraint、H5・H6・H31、issuance_profile の tls_termination・forwarded_cert_header、付録 D の M_sender_constraint の 1.〜4.
- 箇所ごとに並べた：
  - shirogane-as のトークンの端点：トークンを持つ者＝代理店のサーバー、鍵を持つ者＝同じ証明書の mTLS（tls_client_auth）を張った代理店のサーバー。cnf はその接続の証明書の拇印から書く
  - front-gw の代理店の口：TLS を終端した接続の証明書の拇印と cnf を照らす。トークンを出した者と、鍵を見せた者が同じ接続にいる
  - TTS：自分で TLS を見ず、front-gw が書いた Shirogane-Client-Cert-S256 と照らす。ヘッダーは代理店からの同名を捨て、TTS は front-gw の SPIFFE ID からの要求でだけ読むので、見ている鍵は front-gw が確かめた接続の鍵
- 証明書の更新：同じサブジェクトで出し直すので登録はそのままで、古い証明書に束縛した AGENCY_AT は最大 300 秒で使えなくなり、新しい assertion で取り直す（M_sender_constraint の 4.）
- 気づき：AGENCY_ASSERTION そのものは cnf で束縛しないが、要求の mTLS と組で使うので、assertion だけを盗んでも AT は取れない。指摘は無い

### op-source-change（権限の元データの変化）

- 選んだ出来事：査定担当者の異動（役割が外れる）と退職
- 辿った経路：人事部の担当者が人事の仕組みで入力 → 人事部の責任者が承認した時点で社員の台帳が変わる（9.2 の元のデータからの経路。しろがねの IT の部品からは書けない） → TTS が 60 秒のキャッシュの後に引く → 発行済みの TXN_STAFF は最大 330 秒 → 390 秒で止まる（REQ-03 の 600 秒）。payment-svc の承認の上限額・課と assessment-svc の課はキャッシュしない。SSO_SESSION は shirogane-sso が 60 秒ごとに台帳を引いて消す
- ブローカーで待つ指示：H22 で TTS が作り直しのときに役割を引き直し、外れていれば作り直さない。メッセージは確認されずに再配送され、期限の後に滞留のキューへ移り、別の査定担当者が送り直す（9.1）
- 誰も時間を約束していない区間：発効から台帳の更新まで。3.1 の見送りに、人事部が持ち主の前提と、毎月の突き合わせ（付録 A）がある
- 図に無い書き込みの経路：DB の管理者の直接の修正（2.2）。変更の番号と毎月の監査部の突き合わせがある。社員の台帳そのものは範囲の外の部品で、その書き手は人事の規程に任せている
- 気づき：承認の記録は、承認した上長が後で異動・退職しても有効のまま（9.1 の下の段落。明示した判断）。指摘は無い

### op-one-time（1 回だけ使える値）

- 辿った値と結果：
  - AGENCY_ASSERTION の jti：(iss, jti) を一意の制約つきの 1 回の書き込みで記録し、記録先が応えなければ拒む。並行の 2 件は 1 件だけ通る。正しい 1 回は、代理店のサーバーが新しい assertion で取り直せる
  - セキュリティキーの登録の番号：shirogane-sso が鍵の登録と同じ取引で「未使用」→「使用済み」の条件つきの書き込み。並行・記録先の障害とも 1 件以下（2.2）
  - nonce：セッションに置き、1 回使ったら消す。セッションに結びつくので並行の害は小さい
  - AUTH_CODE：「1 回だけ。2 回目でそのコードから出したトークンも失効」。shirogane-as は自分で作る発行者（kind: self_built）だが、確かめと使用済みにする書き込みを 1 回の操作にするかは書いていない。PKCE と tls_client_auth があり、競合で得をするのは正しいクライアント自身なので、指摘にはしない（書き足しを勧める）
  - 支払いの指示：(claim_id, assessment_ref) の一意の制約で、再配送・頼み直し・滞留の後の送り直しは 1 件になる。payment-worker は payment-svc が受け付けた後にだけ処理済みにするので、正しい 1 件が落ちない
  - 支払いの実行：支払いの行のロックの中で「実行済み」に書き、同じ payment_id を 2 回入れない。取り消し・保留と並んでも一方だけが効く
- 気づき：assessment_ref は「査定の確定の ID と版」なので、**確定し直し（新しい版）**は一意の制約をすり抜けて別の指示になる。前の版の未実行の指示を止める手段が無い（指摘 F3）

### さらに（op-clock・op-key-custody・op-requirement-words）

時間の都合で辿っていない。op-clock は 12. の「時計」の行に、書き手自身が IVR と代理店の IdP の時計を見ていないと書いている。

## 答えなかった問い

- 優先 2 の問いには全部答えた（表 (2)）
- 開いた問いの「さらに」3 つは辿っていない（上の段 4）
- 専門家に回す候補：12. の PAY_MSG_CTX（草案 §11.2 の独自の URN で subject_token を受ける形）は、書き手が回す候補にしている。レビュアーとしても回すのがよいと考える（暗号でも製品の挙動でもないが、草案の解釈）

---

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | hops.yaml H22 の validates（3 つ目「payee_ref が契約管理の仕組みでその証券の振込先」）、claims.yaml C-tctx の enforced_at の payment-svc の行、design.md 付録 D の M_authz_pdp の 3.（振込先の行「査定担当者が振込先を差し替えられない」）・P5 の 2.（payee_ref・policy_number の行）、2. の図（POL → PAY は「振込先を読む」だけで、PAY → CL の経路が無い）。問い：q-object-level-authz | payment-svc が payee_ref を照らす「その証券」を、どこから決めるかが無い。payment.instruct の tctx には（P5 の 2. の表では）policy_number が入らず、payment-svc から claim-svc の記録を引く経路も、請求から証券を引く手段も図と台帳に無い。H30 の書き方どおり tctx の policy_number を使うなら、その値は claim.submit の後に誰も claim_id と照らしていない申告の値になる（assessment.confirm で assessment-svc が照らすのは claim_id・amount・payee_ref だけ）。すると査定担当者は、別の証券の番号とその証券の振込先の payee_ref を確定の要求に書いて、ほかの人の口座に払わせられる。100 万円未満は承認が無いので止まる所が無い。M_authz_pdp の 3. が掲げる目的（査定担当者が振込先を差し替えられない）を、今の仕組みは満たせない。対策：payment-svc が請求の ID から証券を引く値の出どころ（claim-svc の記録の参照、または TTS が作り直しのときに claim-svc の記録から証券番号を書く）を決め、その証券の振込先と照らす | Major | 候補の漏れ | q-object-level-authz、txn-tctx |
| F2 | hops.yaml H30 の validates（1 つ目「claim_id・policy_number・amount・payee_ref を変えずに写し」）、claims.yaml C-tctx の assumption と enforced_at の tts の行、design.md 4. の TTS の表（assessment-svc の行）と design.md 付録 D の P5 の 2. の tctx の表（policy_number の「入る operation」が claim.submit だけ）、C-tctx の description（「表に無い項目は入れない」） | PAY_MSG_CTX と作り直した TXN_TOKEN の tctx に policy_number が入るかで、2 か所が食い違う。H30・C-tctx・4. は TXN_STAFF の tctx から policy_number を写すと書くが、P5 の表では assessment.confirm・payment.instruct に policy_number は入らない（写す元が無い）。受け手の照合の項目（payment-svc は policy_number を照らさない）と、F1 の「その証券」がどの値かが、この食い違いで決まらない。どちらかに揃える | Minor | 実装とのずれ | txn-tctx（q-txn） |
| F3 | design.md 付録 A の「支払いの指示の滞留のキューの件数」の行（「金額などを変える確定し直し（新しい版）は、前の版の指示が未実行なら上長が取り消してから行う」）、claims.yaml C-txn の enforced_at の payment-svc の行（「確定し直しで txn が変わっても二重にならない」）、C-tctx の description（assessment_ref は「確定の ID と版」）、hops.yaml H22 の validates（4 つ目・5 つ目）、design.md 付録 D の P5 の 2.（operation の一覧）・M_authz_pdp の 1.（上長の operation）。開いた問い：op-one-time | 確定し直しで assessment_ref の版が変わると、(claim_id, assessment_ref) の一意の制約は 2 つの指示を別物として両方記録する。C-txn の行の「確定し直しでも二重にならない」は、版を含む assessment_ref とは成り立たない。前の版の未実行の指示を止める操作も無い。付録 A は「上長が取り消す」と書くが、operation の一覧にあるのは承認の取り消し（payment.approval-cancel）だけで、承認の要らない 100 万円未満の指示を取り消す操作が無い。assessment-svc が前の版の指示を見て、新しい確定を拒むこともしない。例：40 万円で確定 → 45 万円で確定し直すと、合計 85 万円で承認待ちにならず、夜間の実行で両方が払われる（二重の支払い）。対策：指示の一意の単位を (claim_id, assessment の ID)（版を除く）にして、新しい版は前の版を置き換える。または payment-svc か assessment-svc で、前の版の未実行の指示を同じ取引で取り消す操作を作り、手順でなく仕組みで強制する | Major | 候補の漏れ | op-one-time、txn-tctx（q-txn） |
| F4 | claims.yaml C-tctx の log_policy（記録する）と pii_category（個人情報）、design.md 付録 D の M_privacy_minimization の 7.（tctx は値で記録）・8.（「ログだけでは誰かが分からない」）、12. の「監査ログの相関」の行。要求：REQ-12 | 監査ログで sub・act を HMAC にしても、tctx の policy_number（証券番号）と payee_ref を平文で残すので、契約管理の仕組みと照らせば契約者がすぐ分かる。台帳自身も tctx を個人情報としている。「sub を HMAC にすれば、ログだけでは誰かが分からない」「REQ-12 を満たす」という前提が誤り。対策：policy_number・payee_ref も HMAC にするか記録から外し、相関は txn・claim_id・payment_id で取る（REQ-09 はこれで足りる、と 12. に書いてある） | Minor | 前提の誤り | — |

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| q-value-vocabulary | Yes | scope・acr・tctx の項目は extensible: false の決まった語彙。役割は社員の台帳の役割の ID で、代理店の IdP からは sub しか受けず、別の発行者の同じ文字列を同じ意味で通す経路が無い |
| q-identifier-choice | Yes | 代理店の IdP の (iss, sub) を C-sub の upstream_issuer に書き、shirogane-as が agst_ に替える。行に identifier_properties と on_missing（拒否）がある。上流の sub の付け替えは 3.1 の見送りと 12. に明示 |
| ap-1-7 | Yes | C-agency-code は代理店管理部の 2 人の操作（phr つき）と、業務の持ち主の承認つきの DB の修正だけ。C-client-id は IT 基盤部の変更の手続きと代理店の登録。C-act は TTS が EMPLOYEE_AT の sub・社員の台帳（人事部）・通話の記録（IVR だけ）から書き、社員本人は書けない |
| q-freshness-mitigation | Yes | C-scope は 390 秒 ≤ 600 秒（REQ-03）、agency_code の停止は 390 秒 ≤ 900 秒（REQ-02）、act は 150 秒。対策を行うのは TTS の発行のたびの参照。PAY_MSG_CTX の 3630 秒は作り直しの参照で止まる（9.2） |
| q-single-aud-resource | Yes | どの種別もホップも aud は 1 つ（C-aud の max_items 1、2 つ以上の値の aud は全受け手が拒む） |
| q-no-passthrough | Yes | 交換は TTS だけで、頼めるのは front-gw・payment-worker・payment-batch・assessment-svc（PAY_MSG_CTX だけ）を SPIFFE ID で照らした相手。scope は経路の表と役割で絞り、広げない |
| q-step-up-path-coverage | Yes | 承認と承認の取り消しは payment-svc の承認の API（H23）だけで書け、管理の変更は as-admin-api のすべての変更の API で、どちらも受け手が acr＝phr と auth_time 300 秒を確かめる。非同期・代理の経路から承認・管理は呼べない |
| ap-2-7 | Yes | コールセンターの役割の claims:submit・claims:read は TXN_PROXY にだけ出し（M_authz_pdp の 1.）、claim-svc は front-gw からの stf_ の sub を受けない。act の無いトークンで代理受付はできない |
| q-authorize-service-and-user | Yes | どのホップも受け手が mTLS の SPIFFE ID を一覧と照らし（H4〜H26）、それとは別に sub・scope・tctx で利用者の権限を見る。req_wl を直接の相手に使わない |
| q-agent-short-lived-no-rt | Yes | 代理の主体（コールセンターの社員）の EMPLOYEE_AT に RT を出さず（refresh：無い）、TXN_PROXY は 60 秒で本人確認から 1800 秒を超えない |
| q-outside-catalog | Yes | トークンを運ばない内部の呼び出し（2. の表）、DB の直接の修正（2.2）、fraud-svc の判定のやり直し（found）、旧経路（U29）・試験の口（U30）、夜間の実行の障害（次の夜に回し、手作業の振込を作らない）が書いてある |
| q-object-level-authz | No | 請求・書類・支払いは claim-svc・assessment-svc・payment-svc の記録で止まるが、振込先は「その証券」を請求から決める値が無く、別の証券の振込先を指定されると止まる所が無い（F1） |
| q-approval-from-as | Yes | 承認は payment-svc が自分の承認の記録と照らし、payment_id・金額・payee_ref に結びつけ、実行の取引の中で引き直す。承認を他の受け手に運ばない |
| q-operator-act | Yes | 管理の操作は社員の sub と txn を記録（H26）、代理受付は act、DB の直接の修正は変更の番号と DB の管理者を「書いた者」に残し、毎月監査部が突き合わせる。なりかわりの経路は作らない（2.2） |
| q-revocation-delivery | Yes | 9.1 の表で止める単位ごとに最悪を並べている：契約者 390 秒、代理店 390 秒、代理店の側の担当者 750 秒、社員 390 秒、紛失 330 秒、鍵 810・690 秒。寿命はこの秒数から導いている |
| q-dependency-outage | Yes | TTS・状態の参照・JWKS・契約管理の仕組みが応えなければ拒む（3.1）。CRL は前の CRL で最長 3600 秒受けてから口を止め、可用性の積が REQ-07 に収まると書いている（12. で未測定と明示） |
| op-proof-holder | Yes | front-gw は TLS の接続の証明書の拇印と cnf を照らし、TTS は front-gw だけが書けるヘッダーと照らすので、見ている鍵はトークンを持ち込んだ代理店のサーバーの鍵。証明書の更新は最大 300 秒で取り直す |
| op-source-change | Yes | 異動・退職は人事の仕組み → 社員の台帳 → TTS（60 秒）→ Txn-Token（330 秒）で 390 秒。発効から台帳の更新までの区間は 3.1 で持ち主と確かめ方つきで見送っている |
| op-one-time | No | jti・登録の番号・指示の再配送・実行は 1 回になるが、確定し直し（新しい版）の指示は一意の制約をすり抜け、前の版を止める操作も無いので二重に払える（F3） |
| pa-01 | Yes | agency_code は TTS が代理店の登録と照らし、claim-svc が証券の取扱代理店と照らして請求を絞る（claim_request_agency_code.md と usage authz） |
| q-derived-value | Yes | トークンの個人情報は sub・act・tctx だけで、届くのは使う受け手（act は claim-svc・fraud-svc だけ）。全証券・IP・傷病は載せず、口座は参照 ID。高額の判定は payment-svc が自分の記録で決める（ログの扱いは別に F4） |
| q-variant-comparison | Yes | PH_AT・EMPLOYEE_AT の送信者制約の見送りで、mTLS（SVID の交替）と DPoP（鍵が同じ BFF にある）を比べ、口の mTLS の相手の制限を代わりの守りとし、CI の試験とログの走査で確かめる |
| q-idp-diff-absorbed | Yes | 内側の受け手は TTS の iss だけを受け、代理店の IdP の sub は shirogane-as が agst_ に替える。外の発行者の種別が作り直されずに内側に届くホップは無い |
| q-original-principal | Yes | 作り直しの後も sub は利用者・社員のまま。仲介のサービスは受けた Txn-Token を改変せずに渡し、自分の資格情報で書かない。payment-batch だけが自分の ID で動くのはシステムの処理だから |
| q-step-up-by-rs | Yes | 追加の認証の要否は操作を受ける payment-svc・as-admin-api が決める。staff-console の確かめは画面の案内だけ（付録 B） |
| q-long-running | Yes | ブローカーで待つ間は PAY_MSG_CTX だけを持ち、作り直しのたびに TTS が社員の状態・役割と請求の保留を引き直す。実行は payment-svc が取引の中で承認と保留を確かめ直す |
| q-copies-outlive | Yes | トークンの写しは残さない（Txn-Token はメモリだけ、ログは jti か記録しない）。監査ログは 7 年で読める者を限る。承認の記録が上長の退職後も残るのは明示の判断 |
| q-audit-correlation | Yes | txn を入口から PAY_MSG_CTX の作り直しまで引き継ぎ、claim_id・payment_id でつなぐ。sub・act は同じ HMAC の鍵で、経路の途中で作り方が変わらない。front-gw が外の AT の jti と txn を 1 行に残す |
