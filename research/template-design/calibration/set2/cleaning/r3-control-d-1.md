# レビューの記録：designs/target（しろがね損保　保険金の請求と支払いの内部処理）

- 種（行の抜き取り）：12。抜き取った行：C-agency-code（組織独自の認可の行として必ず入れる行）・C-client-id・C-act
- 読んだもの：sheet.md、ci-result.txt、designs/target の design.md（1.〜13.・付録 A〜D）、claims.yaml、token_types.yaml、hops.yaml、catalog_answers.yaml。教材は short_list.md・perspectives.md（重大度の目安）・decision_tree.md・contrasts/act-txn-workload.md・kind_tell.md
- 答えなかったもの：暗号の方式・製品の挙動・委任が 2 段以上になる場合は該当なし（委任の深さは 1。TXN_PROXY の max_delegation_depth は 1）

## 段 0：CI の結果

- error 0・warn 9・info 15。warn 9 件（L1b 2 件・L16 7 件）はすべて設計書の 1. に理由がある
- L16 の H30（寿命 3600 秒が上流 H29 の 300 秒を超える）：REQ-06 のブローカーでの最大 3600 秒の待ちと、PAY_MSG_CTX を使えるのは TTS への作り直しだけ・作り直しのたびに社員の状態と請求の保留を引き直す、という理由は通る（q-hop-lifetime）。指摘にしない
- L16 の aud（H4・H7・H15・H17・H23・H26）：Txn-Token の aud を信頼ドメインにするのは草案 §9.2 のとおりで、宛先の絞り込みは TTS の aud の照合と内側の aud の固定で行う。理由は通る
- 宣言を曲げた跡（q-lint-workaround）：H17 の TXN_STAFF の scope に payments:instruct が入っているのは、H30 の scope を上流の部分集合にするためにも見える。ただし payment-svc の指示の API は相手が payment-worker で、req_wl も payment-worker のときだけ受ける（C-req-wl）。この scope だけで通る受け手は無いので、指摘にはしない（気づいたこととして残す）

## 段 1：性質の表を確かめる

| 性質 | sheet | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 当たる。C-agency-code（名前空間つき・authz） |
| 個人情報を載せる | 当たる | 当たる。C-sub・C-act・C-email・C-tctx |
| 発行者が複数 | 当たる | 当たる。shirogane-as・shirogane-sso・TTS・代理店の IdP（2 社） |
| 交換・作り直し | 当たる | 当たる。H4・H7・H15・H17・H23・H26（reissue）、H22・H24・H30（exchange） |
| 委任 | 当たる | 当たる。TXN_PROXY の act（電話の代理受付） |
| 操作ごとの承認 | 当たらない | **実際にはある**。100 万円以上の支払いの承認は、payment-svc の承認の記録に 1 件の支払い（payment_id・金額・payee_ref）ごとに結びつく（3.1 の見送り・H23・H24）。トークンに載せないので authorization_details が無いだけ → F6。足した問い dc-05 にも答えた（下の表） |
| マルチテナント | 当たらない | 当たらない（lite_criteria.multitenant が false。代理店ごとの絞り込みは agency_code で、テナントではない） |
| DB の層まで運ぶ | 当たらない | 当たらない（db_connection のホップは無い。9.1 の DB・ブローカーの接続の層） |
| 認証の強さ・新しさ | 当たる | 当たる。C-acr・C-auth-time |
| 送信者制約を選んだ | 当たる | 当たる。AGENCY_AT が mtls |
| 送信者制約を見送った | 当たる | 当たる。PH_AT・EMPLOYEE_AT・Txn-Token は none |
| 長時間・非同期 | 当たる | 当たる。ただし根拠は sheet の書く PH_AT の long_running（「使わない」と書いた欄）ではなく、PAY_MSG_CTX・TXN_TOKEN の long_running、H20・H21 の broker_connection、U13 の「該当」 |

## 段 2：6. の「要る」問いと判断の木の節

| 問い | 判断の木の節 | 設計の仕組み | 比べた結果 |
| --- | --- | --- | --- |
| q-sub | keep-sub-exchange | 作り直しの後も sub は利用者のまま（UC4 は査定を確定した社員を PAY_MSG_CTX から TXN_TOKEN まで保つ）。夜間の実行は payment-batch 自身の ID | 合う |
| q-actor（UC3） | keep-sub-exchange | sub は契約者、act.sub は社員。入れ子なし。受け手は最も外側の act だけを見る | 合う |
| q-actor（UC4「不要」） | keep-sub-exchange | payment-worker は act に載せず、req_wl・q-peer で記録する | 木の例（act＝ワーカー）とは違う。ただし payment-worker は中身を変えられない運び手で、tctx は TTS が写す。どのワークロードが運んだかは q-req-wl の問いで、仕組みは req_wl。対比表の「解く問い」とも食い違わないので、指摘にしない |
| q-req-wl | txn-tctx | req_wl。受け手は直接の相手の照合に使わない（C-req-wl の not_meaning・claim-svc の行） | 合う |
| q-peer | peer-mtls | 全ホップで SPIFFE の mTLS。代理店とは代理店向けの CA の証明書 | 合う |
| q-txn | txn-tctx | txn と tctx。Txn-Token を受けるホップの受け手（claim-svc・fraud-svc・document-svc・assessment-svc・payment-svc・as-admin-api）は全員 tctx を本文と照らす。Txn-Token ヘッダーは AT と別 | 仕組みは合う。ただし UC1 のシーケンス図が 1 枚の Txn-Token を claim.submit と document.upload の両方に使う（F2） |
| q-authorized | rar-vs-custom／carry-or-query | 粗い可否は scope、取引の値は tctx、承認は payment-svc の記録。authorization_details は、承認を確かめる受け手が payment-svc だけなので見送り（3.1） | 合う（受け手に運ぶ要が無い） |
| q-resource | — | aud は口ごとに 1 つ、Txn-Token は信頼ドメイン | 合う |
| q-holder（UC2） | existing-claim-first | cnf の x5t#S256（RFC 8705） | 合う |
| q-agent | — | client_id | 合う |

## 段 3：優先 1 の問い（抜き取った 3 行と経路・全体）

- q-value-vocabulary：C-agency-code は「AG と 6 桁」の変わらない番号で、名前ではない。書くのは shirogane-as と TTS だけで、代理店の IdP の値は通さない。C-client-id は不透明な ID。C-act の act.sub は stf_ の ID。→ Yes
- q-identifier-choice：主体を決めるキーは、代理店の IdP の (iss, sub)（C-sub の upstream_issuer と normalization）と client_id（C-client-id）。どちらも行があり、identifier_properties・on_missing がある。agst_ を上流の sub の付け替えが壊しうることは 3.1 の見送りに書いてある → Yes
- ap-1-7：agency_code の元の代理店の登録は、代理店管理部の 2 人の操作（phr の認証つき）と、承認つきの DB の直接の修正だけで書ける。act の元は EMPLOYEE_AT の sub・社員の台帳（人事部）・通話の記録（IVR だけ）。ただし代理店の登録の新規作成と、既存の代理店への client_id の追加が 2 人の操作に入るかが書いていない → No（F9）
- q-freshness-mitigation：agency_code は許す遅れ 900 秒に対して 390 秒、scope は 600 秒に対して 390 秒（PAY_MSG_CTX の 3630 秒は TTS の作り直しのたびの引き直しで抑える）、act は TXN_PROXY の 90 秒。対策を行うのは TTS（db_lookup）→ Yes
- q-single-aud-resource：AT は aud が 1 つ（C-aud の max_items 1・resource で 1 つ）。Txn-Token の aud は信頼ドメインの 1 値で、受け手の絞り込みは scope・operation・mTLS の相手で行う → Yes
- q-no-passthrough：交換するのは TTS だけ。頼めるのは front-gw（口ごと）・assessment-svc（PAY_MSG_CTX だけ）・payment-worker（PAY_MSG_CTX の作り直しだけ）・payment-batch（自分の ID・時間帯）。Txn-Token を subject_token にする要求は拒む。scope は経路の表と役割で絞る → Yes
- q-step-up-path-coverage：承認の記録を書けるのは payment-svc の承認の API（H23）だけで、受け手が acr と auth_time を見る。代理（TXN_PROXY は act を許すサービスにしか届かない）・交換の後（payments:instruct だけ）・非同期（承認を書けない）の経路から承認できない。管理の操作は as-admin-api（H26）→ Yes（付録 B の表が admin:staff-auth を欠くのは F8）
- ap-2-7：コールセンターの社員が act の無いトークンで請求を出す経路は無い。claim-svc は stf_ の sub を assessment-svc からの査定の経路でしか受けず、社員は PH_AT を持てない（I19 の代理ログインも作らない）→ Yes
- q-authorize-service-and-user：全ホップの validates が呼び出し元の SPIFFE ID を一覧と照らし、利用者の可否（sub・scope・tctx）とは別に決める（q-peer の channel）→ Yes
- q-agent-short-lived-no-rt：代理の主体（社員）は RT を持たない（shirogane-sso は RT を出さない）。TXN_PROXY は 60 秒で、refresh は無い → Yes
- q-outside-catalog：DB の直接の修正（2.2）・as-admin-api・試験の口（U30）・旧経路（U29）・判定のやり直し・手作業の振込（作らない）は答えてある。ただし assessment-svc が社員の台帳から上長の課を読む経路が、図にも、トークンを運ばない呼び出しの表（読み取りの API は TTS・shirogane-sso・payment-svc だけを受ける）にも無い → No（F3）
- q-object-level-authz：他人の claim_id は claim-svc（持ち主・取扱代理店・割り当て）で、書類は claim-svc・assessment-svc の前段の確かめで、支払いは payment-svc で止まる。ただし上長の閲覧の範囲（自分の課）を照らす入力を assessment-svc が取れない → No（F3。上長が要配慮の書類を読めるかも決まらない：F4）
- q-approval-from-as：承認は payment-svc の記録で、payment_id・金額・payee_ref に結びつき、実行の取引の中で記録と今の振込先を引き直す。頼む側の申告（tctx）は記録と照らすだけ → Yes
- q-operator-act：代理受付は act、管理の操作は社員本人の sub と txn の記録、DB の直接の修正は変更の番号、夜間の実行は payment-batch の ID。なりかわりの経路は作らない → Yes
- q-revocation-delivery：契約者 390 秒・代理店 390 秒・代理店の担当者 750 秒・社員 390 秒・紛失 330 秒（届けから）・鍵 810 秒／690 秒（気づいてから）。寿命の数字は分数から導いてある（目録の lifetime_refs）→ Yes（REQ-03・REQ-10 の起点と紛失の目標は 12. で要求の持ち主に確かめる、と書いてある）
- q-dependency-outage：TTS・状態の参照・JWKS が応えなければ拒む。CRL は最長 3600 秒の後に口を止める。社員の台帳・IVR が止まれば社員の口だけが止まる。夜間に TTS・契約管理が応えなければ次の夜。可用性の積も 3.1 にある → Yes（応答を失ったときの PAY_MSG_CTX の作り直しは F1）
- dc-05（段 1 で足した問い）：承認に使う取引の値は tctx の中で、すべて文字列（amount は先頭の 0 と符号の無い 10 進の文字列、最大 12 桁）。value_normalization の compare は exact。生成のスキーマは内側の型を見ないが、TTS の発行の試験と共通の検証部品で確かめる（3.1 の見送り）→ Yes

## 段 4：開いた問い

### op-proof-holder（鍵の持ち主を確かめる箇所）

辿った範囲：C-cnf の enforced_at（front-gw・TTS）、AGENCY_AT の holder・sender_constraint、H5・H6・H31、issuance_profile の tls_termination・forwarded_cert_header、M_sender_constraint の 2.・4.、PH_AT・EMPLOYEE_AT の代わりの守り（口の mTLS の相手）。

| 箇所 | トークンを持つ者 | 鍵を持つ者 | 一致するか |
| --- | --- | --- | --- |
| shirogane-as（H31。AGENCY_AT を出すとき） | 代理店のサーバー（assertion を出す） | 代理店のサーバー（tls_client_auth の証明書） | 一致。拇印を cnf に書く |
| front-gw の代理店の口（H5） | 代理店のサーバー | 代理店のサーバー（TLS の終端で示された証明書） | 一致 |
| TTS（H6） | front-gw（subject_token として持ち込む） | 拇印のヘッダーを書いた front-gw の言う代理店のサーバー | front-gw の SPIFFE ID からの要求でだけヘッダーを読み、外から来た同名のヘッダーは捨てる。確かめの主は front-gw で、TTS は front-gw の取り違えを拾うだけと書いてある |
| front-gw の契約者の口・社員の口（H2・H13） | claim-portal・staff-console | claim-portal・staff-console の SVID（束縛の代わり） | 一致。ほかの部品の SVID は受けない |

気づいたこと：

- 証明書の更新では拇印が変わる。古い証明書に束縛した AGENCY_AT は最大 300 秒で使えなくなり、新しい assertion で取り直す（M_sender_constraint の 4.）。AT には RT が無いので、束縛が切れたまま残る値は無い
- shirogane-as の tls_client_auth は「client_id と証明書のサブジェクトの組」で照らす。代理店向けの CA が同じサブジェクトで別の鍵の証明書を出せば、その鍵にも AGENCY_AT が出る。CA の鍵の扱いは M_token_validation の 8. にあるが、証明書を出す手続き（誰の申請で、何を確かめて出すか）は書いていない（F9 の、代理店の登録の新規作成の 2 人の操作とあわせて見るとよい）
- CRL を取り直せないときは、失効した証明書を最長 3600 秒受けうる。この限界は 3.1 で可用性と引き換えに受け入れている（代理店そのものを止めるのは代理店の登録の停止で、390 秒）

### op-source-change（元のデータが変わる出来事）

選んだ出来事：査定担当者が異動して、査定担当者の役割が外れる（あわせて退職も見た）。

辿った範囲：C-scope の source_system・note、9.2 の「元のデータからの経路」、3.1 の REQ-03 の起点の見送り、H14・H17・H22・H29、9.1 の社員の行。

- 人事部の担当者が人事の仕組みに入力し、責任者が承認する。発効の時刻に社員の台帳が変わる（急な退職は当番が 1 時間以内。人事の規程の 12 条）。発令から台帳までの区間は、この設計では約束せず、要求の持ち主が受け入れるとしている（3.1・12.）。毎月の突き合わせもある
- 台帳 → TTS（キャッシュ 60 秒）→ 新しい TXN_STAFF からその scope が消える。発行済みの TXN_STAFF は最大 330 秒。合わせて 390 秒で、REQ-03 の 600 秒に収まる
- ブローカーで待っている指示は、payment-worker の作り直しのときに TTS が役割を引き直して止める（H22）
- shirogane-sso も台帳を 60 秒ごとに引き、SSO_SESSION を消す

気づいたこと：

- assessment-svc の上長の確かめ（C-sub の enforced_at：「社員の台帳の上長の課」を照らす）は、社員の台帳を読む経路が図に無い。人事の仕組みの読み取りの API は TTS・shirogane-sso・payment-svc しか受けない。上長が異動したとき、どこで課の変化が効くかを辿れない（F3）
- 役割から scope への対応の表が設計書に無い。「どの役割を外すと、どの操作が止まるか」を確かめられない（F4）
- 代理店の担当者の退職は、代理店が自分の IdP で止めるまでの区間を誰も約束していない。代理店の IdP で止めた後の 750 秒は書いてあるが、代理店連携の仕様に「退職した担当者を何分で止めるか」が無い。要求（REQ-02）が代理店そのものの停止だけを言っているので、指摘にはせず、気づいたこととして残す
- 承認の上限額は承認のたびに問い合わせる（キャッシュしない）。古い値のまま承認する区間は無い

### op-one-time（1 回だけ使える値）

辿った値：AGENCY_ASSERTION の jti、AUTH_CODE、nonce、PAY_MSG_CTX の発行（assessment_ref）と、そこからの指示（payment-svc の一意の制約）、支払いの実行（payment_id）、セキュリティキーの登録の番号（24 時間・1 回だけ）。

| 値 | 並行の 2 件 | 通信が切れた後の再送 | 記録先の障害 |
| --- | --- | --- | --- |
| AGENCY_ASSERTION の jti | 一意の制約つきの 1 回の書き込みで、2 件目を拒む | 同じ assertion は拒む（代理店のサーバーは新しい assertion を取り直す） | 拒む（C-jti の shirogane-as の行） |
| 支払いの指示（PAY_MSG_CTX → TXN_TOKEN → payment-svc） | payment-svc の一意の制約が 1 件にする。ただし制約の列が箇所ごとに違う（H22・C-txn は (claim_id, assessment_ref)、H21 は (txn, claim_id)） | **TTS が PAY_MSG_CTX を出した後に応答が assessment-svc に届かなかったとき、または滞留の後に送り直すとき、H29 は「同じ assessment_ref の PAY_MSG_CTX を 2 回出さない」ので、正しい 1 件の送り直しを TTS が拒む。** 付録 A・3.1・PAY_MSG_CTX の lifetime_refs は「同じ assessment_ref で送り直す」と書く。4. の表は「同じ txn で 2 回出さない」と書く（F1） | TTS が「出した assessment_ref」を記録する先が止まったときの倒し方が書いていない（F1） |
| 支払いの実行 | 支払いの行のロックと、同じ payment_id を 2 回入れない | 実行済みなら効かない | 契約管理・TTS が応えなければ次の夜 |
| セキュリティキーの登録の番号 | 「1 回だけ」をどこで、どう確かめるか（一意の書き込みか）が書いていない（F10） | 同左 | 同左 |

気づいたこと：F1 は「正しい 1 回が失われる」側に倒れる。書き手が送り直しのために新しい版（新しい assessment_ref）で確定し直させると、今度は (claim_id, assessment_ref) の制約が効かず、payment-svc が受け付け済みだった前の指示と 2 件になりうる（付録 A は「前の版の指示が未実行なら上長が取り消してから」と書くが、受け付けたかどうかを査定担当者は知らない）。

## 段 5：優先 2 の問いと、さらに辿った開いた問い

- pa-01：agency_code は TTS（登録と一致するか）と claim-svc（取扱代理店の証券か）が決める。fraud-svc・document-svc にも届くが読まない（受け手ごとの最小化は lint の L16 の問い）→ Yes
- q-derived-value：個人情報の行（sub・act・email・tctx）は、届く受け手が記録・照合に使う。email は claim-portal の表示だけ。振込先は参照の ID、傷病・IP は載せない → Yes
- q-variant-comparison：PH_AT・EMPLOYEE_AT の送信者制約の見送りで、mTLS（SVID の切り替えで AT が切れる）と DPoP（鍵が BFF の同じサーバーにある）を比べ、開く攻撃（口に接続できる者だけが使える）と代わりの守り（口の接続の制限・ログの走査）と確かめ方を書いている → Yes
- q-idp-diff-absorbed：内側の受け手は TTS の iss だけを受け、代理店の IdP の sub は shirogane-as が agst_ に替える。外の種別が作り直されずに内側に届くホップは無い → Yes
- q-original-principal：作り直しの後も sub は利用者（UC4 は社員）で、scope は経路と役割で絞る。仲介のサービスは自分の資格情報で書かない（H10・H18）→ Yes
- q-step-up-by-rs：payment-svc・as-admin-api が決め、staff-console は案内だけ（付録 B）→ Yes
- q-long-running：利用者のトークンを持ち越さず、作り直しのたびに TTS が社員の状態・役割と請求の保留を引き直し、実行の取引の中で承認と保留の印を確かめる → Yes
- q-copies-outlive：写しは TTS の状態のキャッシュ（60 秒）、監査ログ（HMAC。7 年）、アクセスのログ（90 日）、payment-svc の保留の印。どれも期間と読める者が書いてある → Yes
- q-audit-correlation：txn は PAY_MSG_CTX からの作り直しでも引き継ぎ、承認は payment_id で結ぶ。sub・act.sub の HMAC は監査ログの基盤の 1 つの鍵で作るので、経路の途中で作り方が変わらない → Yes
- op-clock（さらに）：IVR の時刻と TTS の時計、代理店の IdP の iat と shirogane-as の時計は別の時計で、12. と M_token_validation の 6. に書いてある。auth_time の比べ方は厳しい側（ずれを足さない）。夜間の時間帯は TTS の時計で決める。指摘なし
- op-key-custody（さらに）：shirogane-as・shirogane-sso・TTS の鍵は HSM で、持ち主は IT 基盤部、気づいてから 810 秒。代理店の IdP の鍵は代理店が持ち、知らせから 690 秒。代理店向けの CA と SPIFFE の CA も書いてある。指摘なし
- op-requirement-words（さらに）：「上長」（REQ-05 の承認者・REQ-08 の書類の閲覧）と「社員」（REQ-03）を選んだ。「割り当てた査定担当者だけが書類を読む」（REQ-08）に対し、上長が書類を読めるかが決まらない。管理の操作の主体の「IT 基盤部（社員の認証の管理）」が、TTS が scope を決める役割の一覧（H14）と 2.1 に無い（F4）。3.1 の「終話の後の 90 秒は要求の持ち主が受け入れる（12.）」が 12. に無い（F11）

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | hops.yaml の H29 の validates.checks[2]（「同じ assessment_ref の PAY_MSG_CTX を 2 回出さない」）・H21 の validates.checks[2]（「(txn, claim_id) の一意の制約」）・H22 の validates.checks[3]（「(claim_id, assessment_ref)」）。design.md の 4.（TTS が受ける要求の assessment-svc の行：「同じ txn で 2 回出さない」）・付録 A（滞留のキューの行：「送り直しは同じ assessment_ref で」）・3.1（高額の承認の見送りの行の確かめ方）。token_types.yaml の PAY_MSG_CTX の lifetime_refs。claims.yaml の C-txn の enforced_at（payment-svc・payment-worker）。問い：op-one-time・q-dependency-outage | 支払いの指示の「1 回だけ」の規則が箇所ごとに違う。TTS が PAY_MSG_CTX を出せるのは assessment_ref ごとに 1 回（H29）なのに、滞留の後の送り直しは同じ assessment_ref で行う（付録 A・PAY_MSG_CTX の lifetime_refs）。期限の切れた PAY_MSG_CTX は TTS が受けないので、送り直しには新しい PAY_MSG_CTX が要る。そのため送り直しを TTS が拒み、正しい 1 件の指示が失われる。TTS の応答が assessment-svc に届かなかったときも同じことが起きる。新しい版で確定し直させて避けると、今度は payment-svc の (claim_id, assessment_ref) の制約が効かない。payment-svc が前の指示を受け付け済みだった場合、指示が 2 件になりうる。一意の制約の列も H21 と H22・C-txn で違う（H21 の (txn, claim_id) なら、確定し直しで txn が変わると二重になる）。TTS の発行の記録先の障害のときの倒し方も無い。直し方の案：H29 を「同じ assessment_ref には、前に出した PAY_MSG_CTX と同じ中身で出し直す（冪等）」にする。制約の列は (claim_id, assessment_ref) にそろえる | Major | 実装とのずれ | op-one-time |
| F2 | design.md の 7. シーケンス図（UC1：「請求を出す（書類つき）」の後に C->>F と C->>D で同じ TXN_TOKEN を渡す）。hops.yaml の H10・H11 の validates.checks[2]（operation が document.upload・claim_id がパスと一致）、H8 の validates.checks[2]（operation が claim.submit）。claims.yaml の C-tctx の enforced_at（document-svc）。付録 D の P5 の 2.（claim_id は claim.submit に入らない）。問い：q-txn（判断の木の txn-tctx） | 1 枚の Txn-Token の operation は 1 つで、claim.submit の tctx には claim_id が無い。図のとおり書類つきの請求を 1 回の要求で通すと、document-svc の tctx の照合（3.1 の見送りでは document-svc の唯一の確かめ）が通らない。ホップの表と 3.1（書類は後から付ける）は、書類の登録を別の要求（operation が document.upload）とする形と読める。図だけが食い違う。図に合わせて照合を緩める実装を招くので、図を直す | Minor | 実装とのずれ | — |
| F3 | claims.yaml の C-sub の enforced_at（assessment-svc：「社員の台帳の上長の課を照らす」）と、hops.yaml の H17・H30 の生成の行（design.md の 8.）。design.md の 2. の範囲の図（社員の台帳から assessment-svc への矢印が無い）と、トークンを運ばない内部の呼び出しの表（TTS → 社員の台帳の行：読み取りの API は TTS・shirogane-sso・payment-svc だけを受ける）。付録 D の M_authz_pdp の 3.（請求の行）。問い：q-outside-catalog・q-object-level-authz | 上長の閲覧を「自分の課の査定担当者に割り当てた請求だけ」に絞る確かめには、社員の台帳の上長の課が要る。しかし assessment-svc が台帳を読む経路が図に無く、台帳の読み取りの API は assessment-svc を受けない。課はトークンにも載らない。このままでは、確かめ自体が実装できないか、図に無い読み取りの経路を足すことになる。前者なら、上長が他の課の請求（要配慮の書類を含みうる）に届く。経路を図と表に足し（許可する SPIFFE ID・止まったときの倒し方）、上長が異動したときの反映の遅れも 9.2 に書く | Major | 実装とのずれ | — |
| F4 | claims.yaml の C-scope の assumption・note（「役割ごとに許す scope」の経路の表）。hops.yaml の H14 の validates.checks[2]（役割の一覧：査定担当者・上長・コールセンター・代理店管理部・お客さま窓口の上長）。design.md の 2.1（主体の種類の社員の行）・2.2（管理の操作・社員の認証の管理の行：IT 基盤部の admin:staff-auth）・6. の UC7・REQ-08。問い：op-requirement-words・q-object-level-authz・ap-1-7 | TTS が役割から出す scope の対応の表が、設計書のどこにも無い（「経路の表が配られる」という前提だけがある）。そのため次の 2 点が決まらない。(a) 上長に documents:read-sensitive を出すか。出すなら、REQ-08 の「割り当てた査定担当者だけが書類を読む」と食い違う。(b) admin:staff-auth（セキュリティキーの登録の番号・鍵の抹消。phr の鍵を作れる強い権限）を誰に出すか。2.2 と UC7 は IT 基盤部が使うとするが、H14 の役割の一覧と 2.1 に IT 基盤部の役割が無い。役割 × scope の表を設計書（付録 D の M_authz_pdp か P5 の 2.）に置き、REQ-08 との対応を書く | Major | 候補の漏れ | — |
| F5 | hops.yaml の H25 の validates.checks[1]（「保留を外すのも同じ経路（上長の役割で TTS が出したときだけ）」）。claims.yaml の C-tctx の description と付録 D の P5 の 2.（operation の一覧に保留を外す操作が無い）。問い：q-approval-from-as（REQ-04 の保留） | 保留を外す操作に operation の名前が無い。scope（assessments:write）は査定担当者と上長で同じなので、payment-svc はトークンから「保留を外す」と「上長が出した」を見分けられない。保留の印は REQ-04 の守りなので、保留を外す operation を経路の表に足し、それを上長の役割だけに出すことを書く | Minor | 候補の漏れ | — |
| F6 | sheet.md の 1.（「操作ごとの承認がある：当たらない」）。design.md の 3.1（高額の支払いの承認の見送りの行）・hops.yaml の H23・H24 | 1 件の支払い（payment_id・金額・payee_ref）ごとの承認が実際にある。トークンに載せないので、台帳の読み方で「当たらない」になっただけ。この性質の問いのうち dc-05 を足して答えた（Yes）。q-approval-from-as と op-one-time は別の性質で既に出ていた | Minor | 前提の誤り | — |
| F7 | design.md の 4. の生成の区間（「証明書を下流へ渡すヘッダー：None」）。token_types.yaml の issuance_profile.forwarded_cert_header（Shirogane-Client-Cert-S256） | 生成の表が、目録で宣言した転送のヘッダーを None と出している。目録の書き方（value の欄が無い）か render のどちらかが食い違う。同じ節の E-mtls-entry は「満たす」と出ているので、表だけを読む人を誤らせる | Minor | 実装とのずれ | — |
| F8 | design.md の付録 B（追加認証の表）。claims.yaml の C-acr の rationale と enforced_at（as-admin-api：「すべての変更の API」で phr）。問い：q-step-up-path-coverage | as-admin-api は admin:staff-auth の操作（登録の番号の発行・鍵の抹消・セッションの削除）にも phr と 300 秒を求める。しかし付録 B と C-acr の rationale にその行が無い。紛失の届けの当番が鍵の抹消のたびに認証し直すことを、運用の手順に書き落としうる | Minor | 実装とのずれ | — |
| F9 | hops.yaml の H26 の validates.checks[3]（2 人の操作は「代理店の登録の変更（代理店コード・証明書のサブジェクト・代理店の IdP の iss と JWKS の URL）」）。claims.yaml の C-client-id の source_system・C-agency-code の note。design.md の 2. の境界の表（しろがねの発行者の行）。問い：ap-1-7 | 代理店の登録の新規作成と、既存の代理店への client_id（新しいサーバー）の追加が、2 人の操作に入るかが書いていない。1 人の代理店管理部の社員が、代理店コードと任意の IdP の iss・JWKS を組にした登録を作れると、その代理店の扱う証券に届く。代理店向けの CA の証明書を出す手続きも書いていない。新規作成と client_id の追加も 2 人の操作にすると書く | Minor | 候補の漏れ | — |
| F10 | design.md の 2.2（社員の認証の管理の行：「登録の番号（24 時間・1 回だけ）」）。hops.yaml の H26。問い：op-one-time | 「1 回だけ」をどこで確かめるか（shirogane-sso の一意の書き込みか）と、並行の 2 件・再送・記録先の障害での扱いが書いていない。番号を手に入れた者が鍵を並行に登録すると、phr の鍵が 2 本できうる | Minor | 候補の漏れ | — |
| F11 | design.md の 3.1（電話の代理受付の見送りの行：「前提：要求の持ち主の保険金部がこの 90 秒を受け入れる。12.」）と 12.（該当の行が無い）。問い：op-requirement-words（REQ-11） | 3.1 は、終話の後の最大 90 秒を要求の持ち主が受け入れるかを 12. で確かめるとしている。しかし 12. にその行が無く、確かめの宿題が消えている | Minor | 実装とのずれ | — |

件数：Blocker 0、Major 3（F1・F3・F4）、Minor 8（F2・F5〜F11）。

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| q-value-vocabulary | Yes | agency_code は変わらない AG＋6 桁の番号で、しろがねの登録からだけ書く。client_id と act.sub も不透明な ID |
| q-identifier-choice | Yes | 主体のキー（代理店の IdP の (iss, sub)・client_id）はどちらも台帳の行で、identifier_properties と on_missing がある |
| ap-1-7 | No | 代理店の登録の変更は 2 人の操作だが、新規作成と client_id の追加が 2 人の操作に入るかが書いていない（F9） |
| q-freshness-mitigation | Yes | agency_code 390／900 秒、scope 390／600 秒、act 90 秒。PAY_MSG_CTX は TTS の作り直しのたびの引き直しで抑える |
| q-single-aud-resource | Yes | AT の aud は口ごとに 1 つ、Txn-Token は信頼ドメインの 1 値で、受け手は scope・operation・相手で絞る |
| q-no-passthrough | Yes | 交換は TTS だけで、頼める相手（front-gw・assessment-svc・payment-worker・payment-batch）と出すトークンが決まっている |
| q-step-up-path-coverage | Yes | 承認・管理の操作を受ける受け手が acr・auth_time を確かめ、代理・交換の後・非同期の経路からは承認できない（付録 B の書き落としは F8） |
| ap-2-7 | Yes | 社員は PH_AT を持てず、claim-svc は前段からの stf_ の sub を受けないので、act の無い代理の経路が無い |
| q-authorize-service-and-user | Yes | 全ホップで SPIFFE の mTLS の相手を一覧と照らし、利用者の可否とは別に決める |
| q-agent-short-lived-no-rt | Yes | 社員には RT を出さず、TXN_PROXY は 60 秒で取り直しが無い |
| q-outside-catalog | No | assessment-svc が社員の台帳から上長の課を読む経路が、図にも、トークンを運ばない呼び出しの表にも無い（F3） |
| q-object-level-authz | No | 請求・書類・支払いは止まる。上長の「自分の課だけ」は照らす入力が取れず、上長の書類の範囲も決まらない（F3・F4） |
| q-approval-from-as | Yes | 承認は payment-svc の記録で、payment_id・金額・payee_ref に結びつき、実行の取引の中で引き直す |
| q-operator-act | Yes | 代理受付は act、管理は本人の sub と txn、DB の修正は変更の番号、バッチは自分の ID で記録する |
| q-revocation-delivery | Yes | 止める単位ごとに最悪 390〜810 秒を並べ、寿命はその分数から導いてある |
| q-dependency-outage | Yes | TTS・状態の参照・JWKS・CRL・台帳・夜間の依存先ごとに、拒むか止めるかと期間が決まっている |
| dc-05 | Yes | tctx の取引の値はすべて文字列で、amount の形と exact の比べ方が決まっている（内側の型は試験と共通の部品で確かめる） |
| op-proof-holder | Yes | 各箇所で、トークンを持つ者と鍵（証明書・SVID）を持つ者が一致する。拇印のヘッダーは front-gw だけが書く |
| op-source-change | No | 社員の役割の変化は 390 秒で効く。ただし上長の課を読む経路（F3）と、役割 × scope の表（F4）が無く辿り切れない |
| op-one-time | No | PAY_MSG_CTX の 1 回の規則と一意の制約が箇所ごとに違い、正しい送り直しを TTS が拒む（F1）。登録の番号の 1 回の確かめも無い（F10） |
| pa-01 | Yes | agency_code は TTS と claim-svc が決め、使い道の無い値・表示用の値での認可は無い |
| q-derived-value | Yes | 個人情報の行は受け手が使う分だけで、振込先は参照の ID、傷病・IP は載せない |
| q-variant-comparison | Yes | 送信者制約の見送りで、mTLS と DPoP を比べ、開く攻撃と代わりの守りと確かめ方を書いている |
| q-idp-diff-absorbed | Yes | 内側は TTS の iss だけを受け、代理店の IdP の sub は shirogane-as が替える |
| q-original-principal | Yes | 作り直しの後も sub は元の利用者・社員で、仲介のサービスは自分の資格情報で書かない |
| q-step-up-by-rs | Yes | 求めるかは payment-svc・as-admin-api が決め、staff-console は案内だけ |
| q-long-running | Yes | 利用者のトークンを持ち越さず、作り直しと実行の時点で権限と保留を確かめ直す |
| q-copies-outlive | Yes | キャッシュ・監査ログ・アクセスのログ・保留の印の残る期間と読める者が書いてある |
| q-audit-correlation | Yes | txn を作り直しでも引き継ぎ、承認は payment_id で結び、HMAC の鍵は 1 つ |
| op-clock | Yes | 別の時計どうしを比べる箇所（IVR・代理店の IdP）を挙げ、倒し方と監視が書いてある |
| op-key-custody | Yes | 鍵ごとに持ち主・保管・漏えい時の手順と分数（810・690 秒）があり、CA の鍵も数えている |
| op-requirement-words | No | 「上長」と REQ-08 の閲覧の範囲、IT 基盤部の役割が設計に無く（F4）、終話の後の 90 秒の宿題が 12. に無い（F11） |
