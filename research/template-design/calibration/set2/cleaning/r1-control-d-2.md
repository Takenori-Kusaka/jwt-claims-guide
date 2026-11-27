# レビュー：designs/target（しろがね損保　保険金の請求と支払いの内部処理）

- 対象：designs/target/design.md と claims.yaml・token_types.yaml・hops.yaml・catalog_answers.yaml
- 使った 1 枚：sheet.md（行の抜き取りの種 12。抜き取った行：C-agency-code・C-client-id・C-act）
- CI（ci-result.txt）：error 0・warn 8・info 15。warn（L1b×2、L16×6）には設計書の 1. に行ごとの理由がある。L16 の理由（Txn-Token の aud は信頼ドメイン。scope は上流と同じか狭く、寿命 300 秒は上流の 300〜600 秒を超えない）は通ると判断した。検査を通すために宣言を曲げた跡（上流を外す・名前を変える・数値を上限に合わせる）は見つからなかった（H5・H24 に upstream が無いのは、網の外からの入口と内部で始まる処理だから）

## 1. 性質の表の確かめ（段 1）

図（2.）と要求（REQ-01〜12）に照らした結果：

| 性質 | sheet の判定 | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 合う（C-agency-code。名前空間つきで usage: authz） |
| 個人情報を載せる | 当たる | 合う（C-sub・C-act・C-tctx・C-email） |
| 発行者が複数 | 当たる | 合う（shirogane-as・shirogane-sso・TTS・代理店の IdP 2 社） |
| 交換・作り直し | 当たる | 合う（H4・H7・H15・H17・H23・H26 の reissue、H22・H24 の exchange） |
| 委任 | 当たる | 合う（TXN_PROXY の act。UC3） |
| 操作ごとの承認 | 当たらない | **合わない**。REQ-05 の高額の支払いの承認は、payment_id と金額に結びついた 1 件ごとの承認（H23 で書き、H24 で実行の時点に引く）。トークンに authorization_details を載せない設計だが、性質としては当たる。指摘 F6 にし、出る問い dc-05 を足して答えた（q-approval-from-as は委任の性質で既に出ている） |
| マルチテナント | 当たらない | 宣言どおり。ただし代理店（別の会社）ごとの絞り込みを agency_code と取扱代理店の照合で行っており、テナントに近い分け方がある。q-tenant-data-match に当たる確かめ（claim-svc が取扱代理店と照らす、document-svc は F3 のとおり経路が曖昧）は q-object-level-authz の中で見た。性質の判定そのものは指摘にしない |
| DB の層まで運ぶ | 当たらない | 合う（db_connection のホップが無い。U02 は対象外、9.1 の DB の層の表も「無い」） |
| 認証の強さ・新しさ | 当たる | 合う（C-acr・C-auth-time。REQ-05） |
| 送信者制約を選んだ | 当たる | 合う（AGENCY_AT の mtls） |
| 送信者制約を見送った | 当たる | 合う（PH_AT・STAFF_AT が none） |
| 長時間・非同期 | 当たる | 合う（PAY_MSG_CTX、H20〜H22、U13） |

## 2. 6. の「要る」の問いと判断の木（段 2）

| 問い | 木の節 | 選ぶ仕組み（木） | 設計の仕組み | 判定 |
| --- | --- | --- | --- | --- |
| q-sub | keep-sub-exchange | sub を保って作り直す | TTS が sub を保つ。PAY_MSG_CTX からの作り直しでも査定を確定した社員を sub に保ち、payment-batch は自分の ID（利用者の sub を捏造しない） | 合う |
| q-actor（UC3） | keep-sub-exchange | 最も外側の act。入れ子を許可に使わない | act.sub だけ・入れ子なし（claim-svc・H15 が入れ子の無いことを確かめる）。act を許す設定は claim-svc・fraud-svc だけ | 合う |
| q-txn・q-req-wl | txn-tctx | tctx を受け手のすべてが本文と照合。Txn-Token ヘッダーで受ける | tctx を受けるホップの受け手（claim-svc・fraud-svc・document-svc・assessment-svc・payment-svc・as-admin-api）がすべて照合する。Txn-Token ヘッダーだけを読む。req_wl を直接の相手とみなさない（C-req-wl の not_meaning） | 合う |
| q-peer | peer-mtls | mTLS・SPIFFE。トークンのクレームで代えない | すべてのホップで呼び出し元の SPIFFE ID を照合。入口の証明書のヘッダーは front-gw だけが書き、外からの同名ヘッダーを捨てる | 合う |
| q-authorized | rar-vs-custom・carry-or-query | 取引の承認をトークンで伝えるなら RAR | 承認を確かめるのは payment-svc だけで、記録を引く（トークンで運ばない）。scope は TTS が台帳の役割から絞る | 合う（承認の判定の競合は F2） |
| q-holder（UC2） | existing-claim-first | cnf（x5t#S256） | AGENCY_AT の cnf を front-gw と TTS が照らす | 合う |
| q-user・q-agent・q-resource | existing-claim-first | sub・client_id・aud | 登録名を使う。aud は値 1 つ | 合う |
| q-still-valid（AT の寿命） | lifetime-by-situation | 剥奪の目標から数字を決める | 寿命でなく TTS の毎回の確認で REQ-01〜03 を満たす（390 秒）。鍵の漏えい（REQ-10）だけ数字が要求に収まらない | F1 |

「目的と仕組みの不一致」に当たる取り違えは見つからなかった。

## 3. 優先 1 の問い（段 3）

抜き取った 3 行（C-agency-code・C-client-id・C-act）で答え、No の問いは残りの行（C-sub・C-scope・C-acr・C-auth-time）も見た。回答の 1 行は末尾の表 (2)。

## 4. 開いた問い（段 4）

### op-proof-holder（鍵の持ち主）
- 辿った範囲：C-cnf の enforced_at（front-gw・TTS）、AGENCY_AT の holder・sender_constraint、H5・H6、forwarded_cert_header、catalog の I26・I29、PH_AT・STAFF_AT の見送り（3.1）
- 箇所ごと：front-gw の代理店の口は「トークンを持つ者＝代理店のサーバー」「鍵を持つ者＝代理店のサーバーの証明書の鍵」で一致。TTS は front-gw が書いた拇印のヘッダーで照らす（入ってきた同名のヘッダーは捨てる）ので一致。PH_AT・STAFF_AT は束縛しないが、口が claim-portal・staff-console の SVID からしか接続を受けないので、「鍵（SVID）を持つ者＝AT を持つ BFF」で一致
- 気づき：証明書の更新（同じサブジェクトで出し直す）では、古い拇印の AGENCY_AT が最大 330 秒で使えなくなるだけで、RT が無いので M_sender_constraint の 4. の問題は起きない。証明書の失効は CRL 300 秒ごとで、失効した証明書と AT は最悪 300 秒＋330 秒使えるが、AT を取るには代理店の IdP の assertion も要る。指摘なし

### op-source-change（権限の元データの変化）
- 選んだ出来事：査定担当者の異動（役割が外れる）と退職
- 辿った範囲：9.2 の「元のデータからの経路」、C-scope の source_system・note、H14・H17・H22、SSO_SESSION の revocation、9.1 の「社員」の行
- 経路：人事部の担当者が人事の仕組みで入力 → 責任者の承認で社員の台帳が変わる → TTS のキャッシュ 60 秒 → 発行済みの TXN_STAFF が最大 330 秒 → 390 秒で止まる。ブローカーで待つ指示は H22 で役割を引き直す。shirogane-sso のセッションは 60 秒ごとの台帳の参照で消える
- 気づき：台帳が変わってからは要求に収まるが、**異動・退職の発効から人事の入力と承認までの区間は、誰も時間を約束していない**（F7）。また、請求の割り当て（claim-svc の記録）は異動の後も残るが、TTS が scope を出さないので操作は止まる。図に無い書き込みの経路は見つからなかった

### op-one-time（1 回だけ使える値）
- 辿った範囲：AUTH_CODE（1 回・2 回目で発行済みも失効）、C-nonce（使ったら消す）、AGENCY_ASSERTION の jti（shirogane-as が 330 秒覚える）、C-txn の payment-worker・payment-svc の重複の拒否、H22 の承認の要否、H24 の実行（実行済みにすることと振込のファイルへの追加を 1 つの取引）
- 並行の 2 件：H22 で、同じ請求の 2 件の指示が並行して届くと、どちらも「合計が 100 万円未満」と読めて承認待ちにならない順序がある。合計の読み取りと指示の記録を 1 つの取引・請求ごとの直列化で行う、という決まりが無い（F2。REQ-05 を飛ばせる）。(txn, claim_id) の重複の拒否も、一意の制約で行うかが書いていない
- 再送：payment-worker は「同じ txn を 2 回 TTS に出さない」が、覚えた後に TTS・payment-svc への送信が失敗したときに、そのメッセージを再送するのか滞留に移すのかが無い（正しい 1 回が失われうる）。jti は (iss, jti) を覚えるが、同時の 2 件をどう 1 件にするか、記録先が止まったときに通すか止めるかが無い（F9）
- 記録先の障害：H24 は claim-svc が応えなければ実行しない（止める側）。承認の記録は payment-svc の中なので、記録先の障害で承認を飛ばす経路は見つからなかった

## 5. 優先 2（時間が残ったので答えた）

回答は表 (2)。開いた問いの「さらに」のうち、op-key-custody は q-revocation-delivery を答える中で辿った（F1）。op-clock は付録 D の M_token_validation の 6. と 12. の「時計」の行を読んだだけで、IVR の時計が遅れたとき 1800 秒の枠が延びる点は書き手が 12. に挙げているので、足していない。op-requirement-words は辿っていない。

## 6. 表

### (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | design.md 9.1「止める単位」の「署名の鍵」の行、付録 D の M_token_validation の 8.（shirogane-as・shirogane-sso の行「目標 15 分」、TTS の行、代理店の IdP の行）、要求の表 REQ-10。token_types.yaml の PH_AT・STAFF_AT・TXN_TOKEN の key_rotation・jwks_cache_ttl（300）・unknown_kid。問い q-revocation-delivery・op-key-custody | REQ-10 は「鍵が漏れたら 900 秒以内にその鍵の署名を受け入れない」。設計の 330 秒（JWKS のキャッシュ 300＋間隔 30）は、**鍵を JWKS から外した後**からの数字で、外すまでの手順の目標が 15 分（900 秒）なので、合わせると最悪 900＋330＝1230 秒になり、要求を超える。8. の理由「REQ-10 の 900 秒に収める」は数字で支えられていない。また、キャッシュ 300 秒の間は外した鍵が受け入れられ続けるので、900 秒に収めるには外す手順を 570 秒以内にするか、受け手に鍵の拒否を押す手段（キャッシュを捨てさせる配布）が要る。代理店の IdP の鍵は、代理店が気づいて知らせるまでの時間が決まっておらず、660 秒は登録を止めた後からの数字 | Major | 理由の不備 | q-revocation-delivery・op-key-custody・lifetime-by-situation |
| F2 | hops.yaml の H22 の validates（「同じ txn と claim_id の指示を 2 回受けない」と「同じ請求の支払いの合計…1000000 円以上なら承認待ち」）、claims.yaml の C-txn の enforced_at（payment-svc の行）、要求 REQ-05。問い op-one-time | 承認の要否を「同じ請求の支払いの合計（実行済み・承認待ち・この指示）」で決めるが、合計の読み取りと指示の記録を 1 つの取引で、請求ごとに直列化して行う決まりが無い。同じ請求の 2 件の指示（例：60 万円ずつ。査定の確定を 2 回出す、または payment-worker の並行の処理）が並行して届くと、どちらも合計 60 万円と読んで承認待ちにならず、REQ-05 の「100 万円以上は別の上長が承認」を飛ばせる。(txn, claim_id) の重複の拒否も、一意の制約か読んでから書くのかが書いていない。H24 の実行のように「1 つの取引で」と決めて、試験（並行の 2 件）を足す | Major | 候補の漏れ | op-one-time |
| F3 | hops.yaml の H10・H11 の validates（「claim-svc の記録でその請求の持ち主が sub」「claim-svc の記録でその請求の agency_code」）、claims.yaml の C-agency-code の enforced_at（document-svc の行）、design.md 付録 D の P5 の 3.（claim-svc → document-svc の行）と、design.md 3.1 の見送り「document-svc が、査定担当者の割り当てを自分では確かめない」（「document-svc から claim-svc への経路を足す費用を避けた」）、2. の範囲の図（DOC → CL の矢印が無い） | 書類の登録で document-svc が claim-svc の記録（請求の持ち主・agency_code）を引くとホップと台帳には書いてあるが、3.1 は document-svc から claim-svc への経路を作らないとし、図にもその経路が無い。2 か所が同じ確かめ（document-svc が claim-svc を引くか）について食い違う。経路があるなら 3.1 の見送りの理由（費用）が成り立たず、割り当ての確かめも document-svc でできる。無いなら H10・H11・C-agency-code の document-svc の確かめは実装されない（claim-svc の確かめに頼る）。どちらかに揃える | Minor | 実装とのずれ | q-object-level-authz |
| F4 | design.md 2. の範囲の図と記入欄、hops.yaml の H22 の validates（TTS が「請求が保留でないことを引き直して」）・H23 の validates（payment-svc が「承認の上限額を社員の台帳に問い合わせ」）、claims.yaml の C-req-wl・C-sub の claim-svc の enforced_at（受ける呼び出し元の一覧）。問い q-outside-catalog | 図と記入欄に無い呼び出しがある：(a) TTS が請求の保留を引く先と、そのときの認証（claim-svc は Txn-Token と呼び出し元の一覧で受けるが、TTS は一覧に無い）、(b) payment-svc から社員の台帳への問い合わせ（図に HR → PAY が無い）、(c) assessment-svc・payment-worker・payment-batch から TTS への要求（7. のシーケンス図にはあるが、範囲の図に無い）。(a) は決まっていないので、同じ守り（mTLS の相手の一覧・読み取りだけ）が掛かるかを言えない | Minor | 候補の漏れ | q-outside-catalog |
| F5 | claims.yaml の C-sub の identifier_properties（reassignable: false）と upstream_issuer、design.md 12.「代理店の担当者の表」。問い q-identifier-choice | C-sub は reassignable: false と宣言するが、上流の代理店の IdP の sub は代理店が付け替えられ、しろがねでは見分けられないと 12. に書いてある。付け替えられると、別の人が前の人の agst_ の ID を引き継ぎ、請求の記録・監査（REQ-09）で 2 人が 1 人に見える（権限は同じ代理店の中に限られる）。宣言の前提が事実と違う。上流のキーの性質（付け替えうる）を行に書き、付け替えを知る手段（連携の仕様の約束と報告の手順）を対策として行に結ぶ | Minor | 前提の誤り | q-identifier-choice |
| F6 | sheet.md の 1. の「操作ごとの承認がある」（当たらない）、要求 REQ-05、hops.yaml の H23・H24、catalog_answers.yaml の I14 | 性質の判定は authorization_details が無いことだけで「当たらない」になったが、REQ-05 の承認は支払いの 1 件（payment_id・金額）に結びつく操作ごとの承認で、H23 で書き H24 で引く。性質は当たる。出る問い dc-05（tctx の内側の型と比べ方）を足して答えた（Yes）。書き手側の直しは要らないが、性質の読み方（承認の記録をトークンの外に置く設計）が漏れる例として記録する | Minor | 前提の誤り | dc-05・q-approval-from-as |
| F7 | design.md 9.2「元のデータからの経路」の社員の台帳の行、9.1「止める単位」の社員の行、要求 REQ-03。問い op-source-change・q-revocation-delivery | REQ-03 の 600 秒は、社員の台帳が変わってからの 390 秒で満たすとしているが、退職・休職・異動の発効から、人事部の入力と責任者の承認で台帳が変わるまでの区間は、誰も時間を約束していない。REQ-03 の時計がどこから始まるか（発効か、台帳の更新か）を要求の持ち主に確かめ、発効からなら人事の入力の期限を前提（assumption）として書く | Minor | 候補の漏れ | op-source-change・q-revocation-delivery |
| F8 | design.md 9.1「社員の端末・セキュリティキーの紛失」の行、12.「端末の紛失の目標」。問い q-revocation-delivery | 端末・セキュリティキーの紛失の届けから止まるまでの要求の数値が無い（設計は REQ-03 の 600 秒を目標に置き、330 秒とした）。届けまでの時間も数えていない。書き手は 12. に挙げているが、要求の数値が無いこと自体を指摘として残し、要求の持ち主の回答を待つ | Minor | 候補の漏れ | q-revocation-delivery |
| F9 | claims.yaml の C-jti の enforced_at（shirogane-as の行）、AGENCY_ASSERTION の jti_policy、C-txn の enforced_at（payment-worker の行）、hops.yaml の H21 の validates。問い op-one-time | (1) shirogane-as は (iss, jti) を 330 秒覚えるが、同じ組の 2 件が同時に届いたときに 1 件だけ通す（確かめと記録を 1 回の操作にする）ことと、記録先が止まったときに拒むことが書いていない。(2) payment-worker は txn を覚えて 2 回出さないが、覚えた後に TTS・payment-svc への送信が失敗したときの扱い（再送・滞留）が無く、正しい 1 回の指示が失われうる（payment-svc も重複を拒むので、worker 側は送信の成功の後に覚えるか、重複の拒否を payment-svc に任せる） | Minor | 候補の漏れ | op-one-time |
| F10 | hops.yaml の H20 の validates（「TTS は operation が assessment.confirm の TXN_STAFF からだけ出す」）、claims.yaml の C-tctx の enforced_at（tts の行）、catalog_answers.yaml の shirogane-tts の trigger_list と pairwise の I22。問い q-no-passthrough | PAY_MSG_CTX を出す条件は「subject_token の operation が assessment.confirm」だけで、頼める相手（mTLS の相手が assessment-svc であること）が規則として書いていない。H18 で claim-svc も operation が assessment.confirm の TXN_STAFF を受け取るので、claim-svc（またはそれを乗っ取った者）が同じ確定から PAY_MSG_CTX を作らせられる。値は TXN_STAFF の tctx から写され、payment-svc が (txn, claim_id) の重複を拒むので影響は限られるが、F2 の並行の経路を増やす。PAY_MSG_CTX の作り直しの許可リスト（payment-worker だけ）と同じ形で、発行を頼める相手を assessment-svc だけにする | Minor | 候補の漏れ | q-no-passthrough |

重大度ごとの件数：Blocker 0・Major 2・Minor 8

### (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| q-value-vocabulary | Yes | agency_code は登録の変わらない番号（^AG[0-9]{6}$）で名前でなく、代理店の申告・代理店の IdP からは取らない。client_id・act.sub も不透明な ID。役割は社員の台帳の役割の ID から TTS が scope に替える |
| q-identifier-choice | No | 代理店の IdP の (iss, sub) は C-sub の upstream_issuer の行になっているが、identifier_properties の reassignable: false が 12. の「付け替えうる」と食い違う（F5） |
| ap-1-7 | Yes | agency_code の元は代理店管理部だけが as-admin-api で書き、変更は別の社員の承認とハードウェアの鍵つき。代理店とその IdP の管理者は書けない。act は IVR だけが書く通話の記録と人事が書く役割から TTS が書く。client_id の登録は IT 基盤部の変更の手続き |
| q-freshness-mitigation | Yes | agency_code は許容 900 秒に 390 秒、act・scope（役割）は REQ-03 の 600 秒に 390 秒。対策は TTS が発行のたびに台帳・登録を引くこと（キャッシュ 60 秒）で、行う者も TTS と決まっている |
| q-single-aud-resource | Yes | どの種別もホップも aud は 1 つ（C-aud の max_items 1、2 つ以上は受け手が拒む）。L16 の aud の warn は信頼ドメインへの名前の違いで、理由は通る |
| q-no-passthrough | No | 交換は TTS だけで、Txn-Token を subject にした作り直しを拒み、scope は経路の表で絞るが、PAY_MSG_CTX の発行を頼める相手が assessment-svc に限られていない（F10） |
| q-step-up-path-coverage | Yes | 承認・取り消しは payment-svc、管理は as-admin-api が、届いた経路に関係なく TXN_STAFF の acr（phr）と auth_time（300 秒）を確かめる。承認の記録を書ける API は 1 つで、代理（TXN_PROXY）・非同期の経路には payments:approve が出ない |
| ap-2-7 | Yes | コールセンターの社員が契約者の請求を出す経路は TXN_PROXY だけで、act の無い Txn-Token では claim-svc が stf_ の sub を査定の経路（assessment-svc から）でしか受けない。契約者としてのログイン（I19）は無い |
| q-authorize-service-and-user | Yes | すべてのホップで呼び出し元の SPIFFE ID を一覧と照らし、利用者の権限（sub・scope・tctx）と別に確かめる。req_wl を直接の相手とみなさない |
| q-agent-short-lived-no-rt | Yes | 代理の主体（社員）は STAFF_AT（RT なし）と TXN_PROXY（300 秒・作り直しなし）だけ。shirogane-sso は RT を出さない |
| q-outside-catalog | No | 管理の口・試験の口（U30）・旧経路（U29）・障害時の手作業（滞留のキュー）は答えてあるが、TTS が請求の保留を引く経路などが図と記入欄に無い（F4） |
| q-object-level-authz | Yes | claim-svc が請求の持ち主（ph_）・取扱代理店（agst_）、assessment-svc が割り当て、payment-svc が payment_id と記録を照らす。document-svc の照合は F3 の食い違いがあるが、前段の claim-svc・assessment-svc で止まる |
| q-approval-from-as | Yes | 承認は payment-svc の記録（承認者の sub・txn・金額・payment_id）と照らし、申告を使わない。承認を使えるのは payment-svc の実行だけで、承認者と指示者が同じなら拒む（承認の要否の競合は F2） |
| q-operator-act | Yes | 管理の操作は社員の sub の TXN_STAFF（as-admin-api が記録）、代理受付は act、なりすましのログインは無い。DB を直す作業は 2 人の承認と記録の手続きでトークンを使わない |
| q-revocation-delivery | No | 契約者・代理店・社員の停止は最悪 390〜660 秒で要求に収まるが、鍵の漏えいは手順の 15 分＋330 秒で REQ-10 を超え（F1）、人事の入力の区間（F7）と端末の紛失の数値（F8）が決まっていない |
| q-dependency-outage | Yes | TTS・状態の参照・JWKS が応えなければ拒む（front-gw は 503）、社員の台帳・IVR が止まれば社員の口だけ止まる、fraud-svc は判定待ちで受ける、claim-svc が応えなければ実行を次の夜に回す。倒し方は 3.1 の可用性の積（99.91%）と照らしてある |
| dc-05（性質を足して出した問い） | Yes | 承認に使うオブジェクト（tctx）の項目はすべて文字列で形が決まり（amount は先頭の 0 と符号の無い 10 進）、value_normalization は exact。JSON Schema が内側を確かめない点は 3.1 で見送りと確かめ方を書いてある |
| op-proof-holder | 該当なし | 開いた問い。辿った範囲と気づきは 4.（指摘なし） |
| op-source-change | 該当なし | 開いた問い。辿った範囲は 4.、気づきは F7 |
| op-one-time | 該当なし | 開いた問い。辿った範囲は 4.、気づきは F2・F9 |
| pa-01 | Yes | agency_code は claim-svc（取扱代理店の証券だけ）と document-svc（同じ代理店の請求の書類だけ）が決め、TTS が登録と一致するかを確かめる。表示用の値での認可は無い（email は表示だけ） |
| q-derived-value | Yes | 個人情報の行（sub・act・tctx・email）は受け手が使う値だけ。email は ID トークンだけ、口座番号は参照の ID（payee_ref）、傷病は載せない（C-injury 却下）。tctx の項目は operation ごとに経路の表が決める |
| q-variant-comparison | Yes | PH_AT・STAFF_AT の送信者制約の見送りは、盗まれた AT を使える者（口に SVID で接続できる者）・費用（SVID の 1 時間ごとの更新）・代わりの守りと確かめ方（CI の口の試験）・見直しの条件を比べている。DPoP の費用は書いていないが、鍵が同じ BFF に置かれるので守りは変わらない |
| q-idp-diff-absorbed | Yes | 代理店の IdP の値は shirogane-as が agst_ の ID に替え、内側は TTS の Txn-Token だけを受ける（iss は TTS だけ）。外の発行者の種別が内側に届くホップは無い |
| q-original-principal | Yes | 作り直しの後も sub は元の利用者（契約者・代理店の担当者・査定を確定した社員）で、scope は TTS がその主体の今の役割から絞る。payment-batch は利用者の文脈が要らない実行だけ |
| q-step-up-by-rs | Yes | 追加の認証を求めるかは操作を受ける payment-svc・as-admin-api が決め、staff-console の確かめは画面の案内だけ（付録 B） |
| q-long-running | Yes | 非同期では Txn-Token を持ち越さず、H22 で TTS が社員の在籍・役割と請求の保留を引き直し、実行（H24）で payment-svc が承認の記録と保留を引く |
| q-copies-outlive | Yes | 写しは監査ログ（sub は HMAC）・fraud-svc の判定の記録（90 日）・TTS の状態のキャッシュ（60 秒）で、分析基盤への複製（U28）と開いたままの接続（U23）は無い。判断の結果はキャッシュしない（U21） |
| q-audit-correlation | Yes | txn・sub と act.sub の HMAC（同じ監査の基盤の鍵）・tctx の claim_id・payment_id でつなぎ、PAY_MSG_CTX からの作り直しは txn を引き継ぐ。承認は payment_id で指示・実行と結ぶ（REQ-09。手順の試しは 12. に挙げてある） |
