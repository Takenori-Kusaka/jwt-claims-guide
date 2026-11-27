# レビューの記録：designs/target（しろがね損保　保険金の請求と支払いの内部処理）

- 読んだもの：designs/target/ の design.md（1.〜13.・付録 A〜D）、claims.yaml、token_types.yaml、hops.yaml、catalog_answers.yaml、claim_request_agency_code.md、ci-result.txt、sheet.md（種 12）
- 教材：short_list.md（見出しのみ）、perspectives.md（問いの書き方と読み方・重大度）、decision_tree.md（2.〜7.）、contrasts/act-txn-workload.md、kind_tell.md
- 指摘の件数：Blocker 0、Major 3、Minor 4

---

## 段 0：受け付け（CI の結果と、宣言を曲げた跡）

- 設計書の 1. と ci-result.txt は一致（error 0、warn 9、info 15）。warn の理由は 1. の表にある
  - L1b（req_wl・tctx）：草案の名前で、spec_version と見直しの条件がある。通る
  - L16 の aud（H4・H7・H15・H17・H23・H26）：Txn-Token の aud は信頼ドメイン（草案 §9.2）で、外の AT の aud と名前が違う。宛先の絞り込みは TTS の `C-aud` の行と内側の受け手の aud の照合で行う。通る
  - L16 の寿命（H30。3600 秒 > 300 秒）：REQ-06（ブローカーで最大 3600 秒）が理由で、PAY_MSG_CTX は TTS への作り直しにしか使えず、TTS が作り直しのたびに在籍・役割・保留を引き直す（H22）。通る（PAY_MSG_CTX が草案 §13.15 の「期限切れを作り直さない」を実質で回り込む形かどうかは 12. のとおり専門家に回す候補）
- 曲げた跡：H31 を H5 の upstream に置いていない（AGENCY_AT 300 秒 > assertion 60 秒で L16 に当たるはず）。理由は H31 の note（assertion は RFC 7523 の認可の grant で、作り直しの上流ではない）にあり、寿命の差の影響（代理店の側の担当者の停止 750 秒）は 3.1 と 9.1 で REQ-02 の 900 秒に収めている。宣言の曲げではなく、理由のある選択と判断した（指摘にしない）
- H24 に upstream が無いのは草案 §8.2（内部で始まる取引）で、妥当

## 段 1：性質の表を、図と要求に照らして確かめた結果

| 性質 | sheet の判定 | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 当たる（`C-agency-code`。名前空間つき） |
| 個人情報 | 当たる | 当たる（`C-sub`・`C-act`・`C-email`・`C-tctx`） |
| 発行者が複数 | 当たる | 当たる（shirogane-as・shirogane-sso・shirogane-tts・agency-idp（2 社）） |
| 交換・作り直し | 当たる | 当たる（H4・H7・H15・H17・H23・H26 の reissue、H22・H24・H30 の exchange） |
| 委任 | 当たる | 当たる（`C-act`。TXN_PROXY） |
| 操作ごとの承認 | 当たらない | **実際にはある**。100 万円以上の支払いの上長の承認（REQ-05、UC5、H23）、管理の操作の 2 人の操作（H26）。authorization_details を使わず payment-svc の承認の記録で表すので（3.1 の見送り）、行の有無からは判定が「当たらない」になった。指摘 F7。出さなかった問い dc-05 を足して答えた（問いの表の末尾） |
| マルチテナント | 当たらない | 当たらないと判断した。代理店は別の会社だが、データの分け方はテナントではなく証券の取扱代理店（agency_code）で、claim-svc が照らす（M_authz_pdp の 3.）。代理店をまたぐ識別子は (iss, sub) で混ざらない（`C-sub` の normalization）。参考に q-tenant-data-match・q-cross-tenant-identity に当たる点を見たが、どちらも答えがある |
| DB の層まで運ぶ | 当たらない | 当たらない（db_connection のホップが無い。9.1 の DB・ブローカーの接続の層） |
| 認証の強さ・新しさ | 当たる | 当たる（`C-acr`・`C-auth-time`、付録 B） |
| 送信者制約を選んだ | 当たる | 当たる（AGENCY_AT の mtls） |
| 送信者制約を見送った | 当たる | 当たる（PH_AT・EMPLOYEE_AT の none。3.1 の見送り） |
| 長時間・非同期 | 当たる | 当たる。ただし根拠は PH_AT の long_running ではなく（PH_AT は「長い処理には使わない」）、PAY_MSG_CTX（U13、H20〜H22）と payment-batch（H24）。性質の判定は変わらない |

要求の表（REQ-01〜12）・範囲の図・12.（自信のない点）を読んだ。12. の点（草案の版、PAY_MSG_CTX の型、代理店の IdP の結合試験、時計、終話の後の 90 秒、要求の起点）はどれも確かめ方と持ち主が書いてあり、指摘にしない。

## 段 2：6.（問い × 仕組み）の「要る」と、判断の木の節

| ユースケース・問い | 判断の木の節 | 仕組み | 比べた結果 |
| --- | --- | --- | --- |
| 全 UC の q-sub・q-actor | keep-sub-exchange | Txn-Token の sub は元の利用者のまま、代理受付だけ act | 合う。UC4 の payment-worker に act を置かない選択は、中身を変えられない運び手で q-req-wl と q-peer で別に記録する、という理由があり、対比表（act-txn-workload の解く問い）とも矛盾しない。**ただし UC5 の「査定した人と別」の照合が、指示の sub に頼っている（F1）** |
| q-txn・q-req-wl | txn-tctx | txn・tctx・req_wl。受け手ごとに照合の項目が enforced_at にある | 合う（fraud-svc・document-svc の照合もホップの validates にある） |
| q-peer | peer-mtls | SPIFFE の mTLS、代理店は代理店向けの CA の mTLS | 合う。req_wl・act・client_id で代えない、と catalog_answers の q-peer に明記 |
| q-authorized（UC5 の承認） | rar-vs-custom | authorization_details を使わず、payment-svc の承認の記録（payment_id・金額・payee_ref に結びつける） | 承認を確かめる受け手が payment-svc だけなので、記録で照らす選択は通る。**ただし payee_ref の指す口座が変わりうる点（F3）と、確定し直しで前の版の指示を止める操作が無い点（F2）が残る** |
| q-authorized（社員の役割） | carry-or-query | 役割を載せず、TTS が社員の台帳から引いて scope に替える | 合う（`C-roles` の却下、REQ-03 を 390 秒で満たす） |
| q-holder（UC2） | —（M_sender_constraint） | `C-cnf`（x5t#S256） | 合う |
| q-still-valid | lifetime-by-situation | 短命＋TTS の毎回の確認（db_lookup） | 合う（「剥奪をすぐ効かせたい操作：短命＋都度判定」） |

## 段 3：優先 1 の問いへの回答（No のものは指摘へ）

回答の一覧は末尾の表 (2)。No になったのは ap-1-7（F3・F4）、q-approval-from-as（F3・F2）。

主な読み取り：

- q-value-vocabulary：scope・acr・tctx の項目は語彙が閉じている（extensible: false）。外の発行者の同じ scope の文字列は、front-gw が口ごとに発行者を 1 つにし、TTS が経路の表で絞り直すので、別の発行者の値を同じ意味として通さない。agency_code は登録の ID（^AG[0-9]{6}$）で、名前で照合しない
- q-identifier-choice：hops の validates に出るキー（sub・client_id・agency_code・call_id・act.sub・cnf）はすべて台帳の行があり、`C-sub`・`C-client-id` に identifier_properties と on_missing がある。代理店の IdP の sub は upstream_issuer と normalization で (iss, sub) から agst_ に替える
- ap-1-7：役割は人事部、代理店の登録は代理店管理部（2 人の操作）、セキュリティキーの登録は 2 人の操作、通話の記録は IVR だけ、と書ける人が限られている。ただし、承認の効き目を決める振込先の中身（payee_ref の指す口座）を書く契約部の経路を、承認の結びつきの側で数えていない（F3）。`C-scope` の note は「DB の直接の修正（2.2）でも役割を付けられる」と書くが、2.2 と 9.2 は社員の台帳を直せる表に入れていない（F4）
- q-freshness-mitigation：要求に数値がある（REQ-01〜03 の 900・900・600 秒）。`C-scope` は volatility 600 に対し 390、`C-agency-code` は 900 に対し 390。超える行（PH_AT・EMPLOYEE_AT 630、PAY_MSG_CTX 3630）は 9.2 で TTS の作り直し・発行のたびの確認を対策にし、対策を行うのは TTS
- q-revocation-delivery：止める単位ごとの表（9.1）があり、契約者 390・代理店 390・代理店の担当者 750・社員 390・紛失 330・承認と保留は実行前なら 0・鍵 810／690 秒。どれも要求に収まり、寿命の数字は 390 秒から導かれている
- q-dependency-outage：TTS・状態の参照・JWKS は拒む側（3.1）。社員の台帳・通話の記録の停止は社員の口だけ、CRL は前の CRL で最長 3600 秒（限界を書いた）、夜間は次の夜に回す。業務の停止の許容（REQ-07 の 99.9%）と部品の目標の積を比べている

## 段 4：開いた問いを辿った範囲と気づき

### op-proof-holder

- 辿った範囲：`C-cnf` の enforced_at（front-gw が主、TTS は front-gw の書いた拇印と照らす）、AGENCY_AT の holder（代理店のサーバー）と sender_constraint（mtls）、H5・H6 の forwarded_headers（Shirogane-Client-Cert-S256。同名を捨て、front-gw だけが書く）、M_sender_constraint の 4.（証明書の更新）
- 箇所ごとの並び：front-gw の代理店の口：トークンを持つ者＝代理店のサーバー、鍵を持つ者＝TLS の相手（同じ代理店のサーバー）。TTS：トークンを持つ者＝front-gw（要求者）、照らす鍵＝front-gw が書いた拇印（front-gw の SPIFFE ID からの要求でだけ読む）
- 気づき：確かめる側が見る鍵は、トークンを実際に持つ代理店のサーバーの鍵になっている。証明書の更新では同じサブジェクトでも拇印が替わり、古い証明書に束縛した AGENCY_AT は最大 300 秒で使えなくなる（取り直しで済む）。PH_AT・EMPLOYEE_AT は束縛しないので、この問いは front-gw の口の mTLS の相手の制限（claim-portal・staff-console の SVID だけ）に置き換わる。指摘なし

### op-source-change

- 選んだ出来事：異動で査定担当者の役割が外れる（と、上長の異動）
- 辿った範囲：人事部の担当者が人事の仕組みで入力 → 人事部の責任者の承認で社員の台帳が変わる（9.2 の元のデータの表。発効の前に入力、急な退職は 1 時間以内：3.1 の見送り）→ TTS が 60 秒のキャッシュの後に引き、次の TXN_STAFF から scope を外す → 発行済みの TXN_STAFF は最大 330 秒 → ブローカーで待つ指示は H22 の作り直しで止まる。上長の課は assessment-svc・payment-svc が要求のたびに引く
- 誰も時間を約束していない区間：発令から人事の仕組みへの入力まで（3.1 の見送りで要求の持ち主が受け入れ、毎月の突き合わせがある）
- 気づき：
  - 図に無い書き込みの経路として、`C-scope` の note が「DB の直接の修正（2.2）」を挙げるが、2.2 の表は社員の台帳を含まず、9.2 は「しろがねの IT の部品からは書けない」とする（F4）
  - 権限ではないが承認の効き目を決める元データとして、契約管理の仕組みの振込先（契約部が書く）がある。payee_ref の指す口座を書き換えたときの扱いが無い（F3）
  - 役割が外れた査定担当者の確定は、別の査定担当者の送り直しで指示になり、指示の sub が送り直した人に替わる（F1 の発端）

### op-one-time

- 辿った範囲：代理店の assertion の jti（一意の制約つきの 1 回の書き込み、記録先が応えなければ拒む）、セキュリティキーの登録の番号（鍵の登録と同じ取引の条件つきの書き込み）、AUTH_CODE（60 秒・1 回だけ）、nonce（1 回使ったら消す）、支払いの指示（(claim_id, assessment_ref) の一意の制約）、支払いの実行（支払いの行のロック、同じ payment_id を 2 回入れない）、payment-worker の処理済みの印（payment-svc の受け付けの後だけ）
- 並行の 2 件・再送・記録先の障害：jti・登録の番号・指示・実行は、どれも「確かめる」と「使用済みにする」が 1 回の書き込みで、並行の 2 件は 1 件だけ通る。再送は再配送と一意の制約で 1 件になり、正しい 1 件は再配送で落ちない
- 気づき：
  - 「同じ査定の確定」の 1 回だけは守られるが、査定の確定し直し（新しい版）では assessment_ref の版が替わり、一意の制約では別の指示になる。付録 A は「前の版の指示が未実行なら上長が取り消してから行う」とするが、指示を取り消す operation・API・役割がどこにも無い。100 万円未満の 2 つの版は承認なしで両方とも実行されうる（F2）
  - nonce の「1 回使ったら消す」の並行の扱い、RT のローテーションの並行の取り直しは、記入が無い（shirogane-as の実装に任せている）。影響は小さいので指摘にしない

## 段 5：優先 2 の問い

末尾の表 (2) に答えた。q-original-principal は F1 により No。開いた問い（さらに）の 3 つは次のとおり。

- op-clock：期限（TTS と受け手、どちらもしろがねの NTP）、assertion の iat（代理店の IdP の時計と shirogane-as の時計。ずれたら拒む側）、auth_time（shirogane-sso と payment-svc・as-admin-api。300 秒にずれを足さない）、通話の記録（IVR の時計と TTS。IVR の時計のずれは監視に足す予定で 12. にある）、実行の時間帯（TTS の時計）。どれも書いてある。TXN_PROXY の exp は IVR の本人確認の時刻から計算するので、IVR の時計が遅れていると 1800 秒を超えうる（12. の時計の点で認識済み）
- op-key-custody：shirogane-as・shirogane-sso・TTS は HSM・IT 基盤部・漏れたら気づいてから 480 秒で JWKS から外し最悪 810 秒、代理店の IdP は知らせから 300 秒で登録を止め最悪 690 秒、代理店向けの CA と SPIFFE の CA も持ち主と手順がある（M_token_validation の 8.）。受け手が古い鍵を使い続けるのは外してから最悪 330 秒
- op-requirement-words：「契約者」（被保険者・受取人が別の人、止めた人は入らない）、「代理店」（登録が有効な代理店だけ、担当者は代理店の IdP が認証した人）、「上長」（同じ課の上長。2.1・H23）、「社員」（勤務中だけ。休職・退職は拒む。委託先は台帳に載らない）。設計にあって要求に無い区分は「社員の認証の管理者」で、2.1 に「設計で足した」と書いてある。要求の「査定した人と別の上長」の「査定した人」が、送り直しの後は指示の sub と一致しない（F1）

---

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | hops.yaml の H23 の validates（4 つ目：「sub が、支払いの指示の sub（査定担当者）と違うこと」）、claims.yaml の `C-sub` の enforced_at（payment-svc の行）、hops.yaml の H29 の validates（送り直し）、design.md の 9.1「止める単位ごと」の社員の行（「割り当てを替えた別の査定担当者が送り直しの操作をする（sub はその査定担当者になる）」）、付録 B の 1 行目、6. の UC5 の q-sub、REQ-05 | REQ-05 は「査定した人と別の上長が承認する」を求めるが、payment-svc は承認者を「指示の sub」と比べ、同じ課かも指示の sub の課で決める。H29 の送り直しは、確定の記録の値が tctx と合えば、確定した本人でない査定担当者でもできるので、送り直しの後は指示の sub＝送り直した人になり、査定した人とずれる。査定した人が上長の役割も持つ、または割り当てを替えられる立場なら、自分の査定を自分で承認できる。仕組み（指示の sub）が答えるのは「誰が指示を出したか」で、要る問いは「誰が査定したか」。照合の相手を assessment_ref が指す確定の記録の sub（査定した人）にするか、送り直しを確定した本人に限る（本人がいなければ確定し直しにする） | Major | 目的と仕組みの不一致 | q-sub（UC5）、q-original-principal、判断の木 keep-sub-exchange |
| F2 | design.md の付録 A（支払いの指示の滞留のキューの行：「金額などを変える確定し直し（新しい版）は、前の版の指示が未実行なら上長が取り消してから行う」）、claims.yaml の `C-txn` の enforced_at（payment-svc の行：「確定し直しで txn が変わっても二重にならない」）、`C-tctx` の description（assessment_ref は「確定の ID と版」）、hops.yaml の H22 の validates（(claim_id, assessment_ref) の一意の制約）、付録 D の P5 の 2. の operation の行と M_authz_pdp の 1. の役割の表（指示を取り消す operation が無い） | 確定し直しでは assessment_ref の版が替わるので、(claim_id, assessment_ref) の一意の制約は前の版の指示と別の行として受け付け、`C-txn` の「二重にならない」は確定し直しには当たらない。前の版の未実行の指示を止める操作は付録 A の運用の文だけで、operation・API・役割・ホップのどこにも無い（payment.approval-cancel は承認を戻すだけで、承認の要らない指示は止まらない）。合計が 100 万円未満の 2 つの版（例：60 万円と 30 万円）は承認なしで両方とも実行されうる。指示の取り消しの operation（上長の役割、H23 と同じ確かめ、支払いの行のロック）を足すか、payment-svc が同じ claim_id の新しい版を受けたときに前の版の未実行の指示を同じ取引で無効にする | Major | 候補の漏れ（あわせて実装とのずれ：`C-txn` の記述と付録 A） | op-one-time、q-approval-from-as |
| F3 | claims.yaml の `C-tctx` の description（payee_ref は「振込先の参照 ID。口座番号そのものではない」）と enforced_at（payment-svc の行）、hops.yaml の H23 の validates（5 つ目）・H24 の validates（4 つ目）、design.md の 3.1 の見送り（高額の支払いの承認を authorization_details に載せない行：「承認の後に振込先を変えても承認していない口座には払わない」）、9.2 の「元のデータからの経路」の証券の取扱代理店・振込先の行、2. の境界の表（社内の台帳と記録の行：振込先は契約部の手続きで書く）、付録 D の M_authz_pdp の 3. の振込先の行 | 承認は payee_ref（参照 ID）に結びつき、実行の取引では「承認の payee_ref＝支払いの記録の payee_ref」と「payee_ref が今もその証券の振込先」を確かめる。しかし payee_ref の指す口座の中身を契約管理の仕組みで書き換えられるか（振込先を替えたら新しい pye_ の ID にするのか、同じ ID のまま口座を直すのか）が、どこにも書いてない。同じ ID のまま直せるなら、承認の後に契約部の操作で口座が替わっても照合は通り、承認していない口座に払う（3.1 の主張が成り立たない）。振込先の書き手（契約部）を、承認の効き目を決める元データの書き手として数えていない。「振込先の参照 ID は口座の中身ごとに変わらない（変えたら新しい ID）」を契約管理の仕組みの前提として台帳の assumption に書いて確かめ方を足すか、承認の記録に口座の中身のハッシュを入れて実行の取引で照らす | Major | 候補の漏れ | ap-1-7、q-approval-from-as、op-source-change |
| F4 | claims.yaml の `C-scope` の note（「役割…を付けられるのは人事部…と、基盤の変更の手続きによる DB の直接の修正（設計書の 2.2。変更の番号を残す）だけ」）、design.md の 2.2 の「データベースの直接の修正」の行（書ける表に社員の台帳が無い）、9.2 の元のデータの表（社員の台帳は「しろがねの IT の部品からは書けない」、DB の管理者が直せる記録の行にも社員の台帳が無い） | 役割（＝TTS が出す scope）を書ける者の範囲が 2 か所で食い違う。台帳は IT 基盤部の DB の管理者も役割を付けられるとし、設計書は付けられないとする。ap-1-7 の答え（役割を付けられる者は人事部だけか）が決まらない。どちらが正かを決め、DB の管理者が直せるなら 2.2 の表と 9.2 に社員の台帳と業務の持ち主（人事部）の承認を足し、直せないなら `C-scope` の note から消す | Minor | 実装とのずれ | ap-1-7 |
| F5 | design.md の付録 D の P5_internal_propagation の 2. の tctx の表（claim_id の行の「document-svc（パスの請求と請求の持ち主）」） | 3.1 の見送り（document-svc は請求の持ち主・代理店・割り当てを自分では確かめない）、H10・H11・H19 の validates、M_authz_pdp の 3. の書類の行は、document-svc が照らすのは呼び出し元・scope・tctx の claim_id とパスだけとする。この表だけが document-svc が請求の持ち主も照らすと書き、受け手の実装の担当が持ち主の照合をしている前提で読み違える。表の「請求の持ち主」を消す | Minor | 実装とのずれ | q-object-level-authz |
| F6 | design.md の付録 D の P5_internal_propagation の 2. の tctx の表（operation の行：「TTS は PAY_MSG_CTX の発行（assessment.confirm のときだけ）」） | hops.yaml の H29、claims.yaml の `C-tctx` の tts の行、4. の TTS が受ける要求の表、catalog_answers.yaml の shirogane-tts の trigger_list は、assessment.confirm か assessment.resend のときに出すとする。表の記述では送り直し（滞留の後の手順、付録 A）が通らないことになる。「assessment.confirm か assessment.resend」に直す | Minor | 実装とのずれ | q-no-passthrough |
| F7 | sheet.md の 1. の「操作ごとの承認がある」の行（当たらない）、design.md の 3.1 の見送り（高額の支払いの承認を authorization_details に載せない）、6. の UC5、hops.yaml の H23・H26 | 設計には操作ごとの承認がある（100 万円以上の支払いの上長の承認（REQ-05）と、代理店の登録・セキュリティキーの登録の番号の 2 人の操作）。承認をトークンでなく payment-svc・as-admin-api の記録で表したので、台帳の行の有無から出す性質の判定が「当たらない」になり、承認の性質の問い（dc-05 など）が 1 枚から落ちた。性質の判定を「当たる」にして承認の問いを出す（この記録では dc-05 を足して答えた）。設計書の側では、承認を記録で表すことを 6. の UC5 の q-authorized の仕組みの列に書くと、判定の元になる | Minor | 前提の誤り | 判断の木 rar-vs-custom、q-approval-from-as |

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| q-value-vocabulary | Yes | scope・acr・tctx の語彙は閉じ（extensible: false）、agency_code は登録の ID で照合し、外の発行者の値は口ごとの発行者と TTS の絞り直しで混ぜない |
| q-identifier-choice | Yes | validates に出るキー（sub・client_id・agency_code・call_id・act.sub・cnf）はすべて行があり、sub・client_id に identifier_properties と on_missing、代理店の sub は (iss, sub) で正規化する |
| ap-1-7 | No | 役割・代理店の登録・鍵の登録の書き手は限られているが、承認の効き目を決める振込先の中身の書き手（契約部）を数えておらず（F3）、役割を DB の管理者が書けるかが食い違う（F4） |
| q-freshness-mitigation | Yes | 要求に数値（600・900 秒）があり、scope・agency_code は 390 秒、超える種別は TTS の発行・作り直しのたびの確認が対策で、行うのは TTS |
| q-single-aud-resource | Yes | AT は口ごとに 1 つ（resource で 1 つ）、Txn-Token は信頼ドメインの 1 つで、2 つ以上の aud はどの受け手も拒む（`C-aud`） |
| q-no-passthrough | Yes | TTS は要求できるワークロードを SPIFFE ID で限り（front-gw・assessment-svc（PAY_MSG_CTX だけ）・payment-worker・payment-batch）、Txn-Token からの Txn-Token の作り直しを拒み、scope は経路の表と役割で絞る |
| q-step-up-path-coverage | Yes | 追加の認証は操作を受ける payment-svc（承認・取り消し）と as-admin-api（すべての変更）が TXN_STAFF の acr・auth_time で確かめ、承認・管理の API は front-gw からの H23・H26 だけで、代理・交換・非同期の経路からは届かない |
| ap-2-7 | Yes | コールセンターの役割は TXN_PROXY の scope だけで、claim-svc は front-gw からの stf_ の sub を受けず、TXN_PROXY は通話の記録の担当の社員にだけ出る。payment-worker は act の代わりに req_wl と mTLS で区別する（6. の UC4） |
| q-authorize-service-and-user | Yes | どのホップも受け手が mTLS の相手の SPIFFE ID を一覧と照らし（catalog_answers の q-peer）、利用者の権限（sub・scope・tctx）とは別に決める |
| q-agent-short-lived-no-rt | Yes | 代理の主体（コールセンターの社員）は RT を持たず（shirogane-sso は RT を出さない）、TXN_PROXY は 60 秒で本人確認から 1800 秒を超えない |
| q-outside-catalog | Yes | 管理の口（as-admin-api は H26 だけ）、トークンを運ばない内部の呼び出し（2. の表）、DB の直接の修正（2.2）、試験の口（U30）、移行の旧経路（U29）、判定のやり直し（found）、手作業の振込の経路を作らないこと、が答えられている |
| q-object-level-authz | Yes | 他人の claim_id は claim-svc（持ち主・取扱代理店・割り当て）、書類は前段の claim-svc・assessment-svc、支払いは payment-svc で止まり、404 を返す（M_authz_pdp の 3.）。表の記述の食い違いは F5 |
| q-approval-from-as | No | 承認は payment-svc の記録で payment_id・金額・payee_ref に結びつくが、payee_ref の指す口座が変わりうる（F3）うえ、確定し直しで前の版の指示を止める操作が無い（F2） |
| q-operator-act | Yes | 運用者は社員の TXN_STAFF で自分の sub と txn を記録し、なりすましの経路を作らず、DB の直接の修正は変更の番号を行に残して毎月監査部が突き合わせる（2.2） |
| q-revocation-delivery | Yes | 9.1 の止める単位ごとの表で、契約者 390・代理店 390・代理店の担当者 750・社員 390・紛失 330・承認と保留は実行前 0・鍵 810／690 秒で、寿命は 390 秒から導いている |
| q-dependency-outage | Yes | TTS・状態の参照・JWKS は拒み、社員の台帳・通話の記録の停止は社員の口だけ、CRL は最長 3600 秒の限界を明記、夜間は次の夜に回し、可用性の積を REQ-07 と比べた（3.1） |
| op-proof-holder | 該当なし（開いた問い） | front-gw が見る鍵は AGENCY_AT を持つ代理店のサーバーの証明書で、更新後の古い束縛は最大 300 秒。辿った範囲は段 4 |
| op-source-change | 該当なし（開いた問い） | 異動から TTS の次の発行までを辿り、約束の無い区間は 3.1 で受け入れ済み。DB の修正の食い違い（F4）と振込先の書き換え（F3）を見つけた |
| op-one-time | 該当なし（開いた問い） | jti・登録の番号・同じ版の指示・実行は 1 回の書き込みで守られるが、確定し直しの新しい版は別の指示になり、前の版を止める操作が無い（F2） |
| pa-01 | Yes | claim_request_agency_code.md の問 1 で、claim-svc が代理店の扱う証券に絞ることと、TTS が登録と照らすことが言え、usage は authz で表示用の値での認可が無い |
| q-derived-value | Yes | 個人情報の行（sub・act・email・tctx）は読む受け手に届き、傷病・IP・役割・全証券の番号は載せず、口座は参照 ID、高額かどうかは payment-svc が自分の記録で決める |
| q-variant-comparison | Yes | 送信者制約の見送りは mTLS と DPoP を比べ、開く攻撃と代わりの守り（口の mTLS の相手の制限、ログの走査）と確かめ方があり、PAY_MSG_CTX の寿命の延長は narrowing_exception に理由がある |
| q-idp-diff-absorbed | Yes | 内側のサービスは TTS の Txn-Token だけを受け、代理店の IdP の sub と代理店コードは shirogane-as と TTS が入口で吸収し、外の発行者の種別が内側に届くホップは無い |
| q-original-principal | No | 交換・作り直しの後も sub は元の主体のままだが、送り直しでは指示の sub が確定した本人から送り直した査定担当者に替わり、承認の分離の照合がずれる（F1） |
| q-step-up-by-rs | Yes | 追加の認証を求めるかを payment-svc・as-admin-api が決め、staff-console の画面の案内は判断に使わない（付録 B） |
| q-long-running | Yes | ブローカーで待つ指示は作り直しのときに TTS が在籍・役割・保留を引き直し、実行は payment-svc が取引の中で承認と保留を確かめ、利用者のトークンを持ち続けない |
| q-copies-outlive | Yes | 写しは監査ログ（sub の HMAC）、TTS の状態のキャッシュ 60 秒、ブローカーの接続 3600 秒（トークンを使わない）、アクセスのログ 90 日で、どれもいつまで残るかが書いてある |
| q-audit-correlation | Yes | txn を入口から支払いの指示まで引き継ぎ、承認の記録は payment_id と txn を持ち、sub・act の HMAC は監査ログの基盤の 1 つの鍵で作る（送り直しでは txn が替わるが assessment_ref と claim_id でつながる） |
| op-clock | 該当なし（開いた問い） | 時刻を比べる 5 か所の時計の出どころと倒し方が書いてある。IVR の時計のずれが TXN_PROXY の上限に効く点は 12. で認識済み |
| op-key-custody | 該当なし（開いた問い） | 発行者ごとの持ち主・HSM・漏えい時の手順と分数（810・690 秒）、CA の鍵も書いてある |
| op-requirement-words | 該当なし（開いた問い） | 契約者・代理店・上長・社員の区分は 2.1 にあり、「査定した人」が送り直しの後にずれる点を見つけた（F1） |
| dc-05（性質の表の誤りで足した問い） | Yes | 型は行ごとに 1 つで、tctx の金額・ID・agency_code はすべて文字列（先頭の 0 を落とさない） |
