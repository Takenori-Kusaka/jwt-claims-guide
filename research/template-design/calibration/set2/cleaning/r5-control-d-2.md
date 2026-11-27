# レビュー：designs/target（しろがね損保　保険金の請求と支払いの内部処理）

- 対象：designs/target/design.md・claims.yaml・token_types.yaml・hops.yaml・catalog_answers.yaml（sheet.md の抜き取りの種は 12）
- 読んだ範囲：design.md の 1.〜3.・6.・9.・12.・付録 A・B・D、台帳 4 つの全体。7. のシーケンス図・8. の生成の表・10.・11.・schemas/ は読んでいない（ホップは hops.yaml で読んだ）
- CI（ci-result.txt）：error 0、warn 9。warn ごとに 1. に理由がある。L16 の H30（下流 3600 秒 > 上流 TXN_STAFF の 300 秒）の理由（PAY_MSG_CTX は TTS への作り直しにしか使えず、作り直しのたびに TTS が引き直す）は通ると判断した。aud の L16（H4・H7・H15・H17・H23・H26）の理由も通る（Txn-Token の aud は信頼ドメイン。TTS が AT の aud と口の一致を確かめる）

## 段 1：性質の表の確かめ

| 性質 | sheet.md | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 合う（C-agency-code） |
| 個人情報 | 当たる | 合う（C-sub・C-act・C-tctx・C-email） |
| 発行者が複数 | 当たる | 合う（shirogane-as・shirogane-sso・TTS・代理店の IdP 2 社） |
| 交換・作り直し | 当たる | 合う（H4・H7・H15・H17・H23・H26 の reissue、H22・H24・H30 の exchange） |
| 委任 | 当たる | 合う（TXN_PROXY の act） |
| 操作ごとの承認 | 当たらない | **合わない**。authorization_details は却下されているが、100 万円以上の支払いの上長の承認（REQ-05）が、payment_id・金額・payee_ref に結びつく 1 件ごとの承認として payment-svc の承認の記録にある（3.1 の見送りの行、H23）。指摘 F7。追加の問い dc-05 と q-approval-from-as にも答えた（q-approval-from-as は委任の条件で既に出ている） |
| マルチテナント | 当たらない | 書き手の宣言（lite_criteria.multitenant: false）のとおり。代理店ごとの区別（別の会社）はテナントに近いが、テナントでなく証券の取扱代理店で絞る理由があり、claim-svc が agency_code と契約管理の仕組みの取扱代理店を照らす。指摘にしない |
| DB の層まで運ぶ | 当たらない | 合う（db_connection のホップが無い。9.1 の DB の層の表にも書いてある） |
| 認証の強さ・新しさ | 当たる | 合う（C-acr・C-auth-time） |
| 送信者制約を選んだ | 当たる | 合う（AGENCY_AT が mtls） |
| 送信者制約を見送った | 当たる | 合う（PH_AT・EMPLOYEE_AT が none） |
| 長時間・非同期 | 当たる | 合う。ただし根拠は PH_AT の long_running ではなく、PAY_MSG_CTX と H20・H21 の broker_connection、U13 の「該当」 |

## 段 2：6. の「要る」の問いと判断の木

| 問い（6. で要る） | 判断の木の節 | 設計の仕組み | 合うか |
| --- | --- | --- | --- |
| q-sub | keep-sub-exchange | Txn-Token の sub を利用者のまま保つ。payment-worker は sub を社員のまま作り直す。payment-batch は自分の ID（利用者の sub を作らない） | 合う |
| q-actor（UC3） | keep-sub-exchange | TXN_PROXY の act（最も外側だけ。入れ子は拒む） | 合う |
| q-req-wl | txn-tctx | req_wl（TTS が mTLS の相手から書く）。直接の相手には使わない | 合う |
| q-peer | peer-mtls | SPIFFE の X.509-SVID の mTLS と、代理店向けの CA の証明書 | 合う |
| q-txn | txn-tctx | txn・tctx。Txn-Token ヘッダーで受け、tctx を使う受け手のすべてが本文と照合する（H4〜H26 の validates） | 合う |
| q-user・q-agent | existing-claim-first | sub・client_id | 合う |
| q-authorized | carry-or-query／rar-vs-custom | scope（TTS が台帳の役割から絞る）、承認は payment-svc の記録（載せずに問い合わせる）、acr・auth_time | おおむね合う。ただし保留を外す操作（assessment.unhold）を上長に限る区別を scope でなく tctx.operation に担わせている（F4） |
| q-resource | existing-claim-first | aud（口ごとに 1 つ、内側は信頼ドメイン） | 合う |
| q-holder（UC2） | existing-claim-first | cnf の x5t#S256 | 合う |
| q-still-valid（6. の生成の表で pending） | lifetime-by-situation | 短命＋TTS の発行ごとの台帳の参照。非同期は PAY_MSG_CTX から作り直し | 合う |

## 段 3：優先 1 の問いへの答え（抜き取りの行：C-agency-code・C-client-id・C-act）

- q-value-vocabulary：Yes。agency_code は名前でなく AG＋6 桁の番号で、代理店の登録だけから書く。scope の語彙は内側では TTS の発行のものしか受けない。C-client-id・C-act は役割の値でない
- q-identifier-choice：Yes。代理店の IdP の値は (iss, sub) の組で、C-iss・C-sub の行（identifier_properties・on_missing あり）になり、shirogane-as が agst_ に替える
- ap-1-7：Yes。agency_code の元（代理店の登録）は代理店管理部の 2 人の操作と、承認つきの DB の直接の修正だけ。client_id は IT 基盤部の変更の手続きと代理店の登録。act は TTS が EMPLOYEE_AT の sub・人事部の役割・IVR の記録から書く
- q-freshness-mitigation：Yes（抜き取りの 3 行）。agency_code は TTS が登録を毎回引く（390 秒 < 900 秒）。ただし残りの行で、査定担当者の異動のときの割り当ての記録が誰にも更新されない区間を見つけた（F6）
- q-single-aud-resource：Yes。どの種別も aud は 1 つ（C-aud の max_items 1、2 つ以上は拒む）
- q-no-passthrough：Yes。TTS が受ける相手（front-gw・assessment-svc・payment-worker・payment-batch）と subject_token の種類、scope は経路の表と役割から絞る。Txn-Token を subject_token にする要求は拒む
- q-step-up-path-coverage：Yes。承認・取り消しは H23 の payment-svc の API だけ、管理は H26 の as-admin-api だけで、どちらも受け手が acr・auth_time を確かめる。ほかの経路（指示・実行・代理受付）からは承認を書けない
- ap-2-7：Yes。コールセンターの役割には TXN_PROXY でだけ claims:submit・claims:read を出す。claim-svc は stf_ の sub を assessment-svc の経路でしか受けない
- q-authorize-service-and-user：Yes。すべてのホップで mTLS の相手の SPIFFE ID を一覧と照らし、利用者の権限とは別に決めている
- q-agent-short-lived-no-rt：Yes。EMPLOYEE_AT・TXN_PROXY に RT は無い（shirogane-sso は RT を出さない）
- q-outside-catalog：Yes。トークンを運ばない呼び出し（2. の表）、管理の口（as-admin-api）、判定のやり直し、DB の直接の修正（2.2）、U29・U30 に前提と崩れる条件がある
- q-object-level-authz：**No**。請求・書類・支払いは claim-svc・assessment-svc・payment-svc で止まるが、上長の保留・保留の解除がどの課の請求に許されるかを確かめる文が、enforced_at・validates のどこにも無い（F1）
- q-approval-from-as（追加）：Yes。承認は payment-svc の記録で、payment_id・金額・payee_ref に結びつき、実行の取引の中で記録と照らす。頼む側の申告では決めない
- q-operator-act：Yes。代理受付は act、管理は社員の sub と txn、DB の直接の修正は変更の番号、夜間の処理はワークロードの sub で見分けられる
- q-revocation-delivery：Yes（おおむね）。契約者 390・代理店 390・代理店の担当者 750・社員 390・紛失 330・鍵 810／690 秒で、どれも要求に収まる。ただし AUTH_CODE の失効の記述に誤りがある（F5）。支払いの保留には REQ-04 が効かない隙間がありうる（F3）
- q-dependency-outage：Yes。TTS・状態の参照・JWKS は拒む側、CRL は前の CRL で最長 3600 秒、台帳・IVR は社員の口だけ止まる、夜間の実行は次の夜に回す、と決まっている
- dc-05（追加）：Yes。承認はトークンに載らない。オブジェクトの行（tctx）は内側の 9 項目がすべて文字列で、amount は 10 進の文字列、比べ方は exact と決まっている（JSON Schema で内側を見ないことは 3.1 の見送りで、試験で確かめる）

## 段 4：開いた問い

### op-proof-holder

- 辿った範囲：C-cnf の enforced_at（front-gw・tts）、AGENCY_AT の holder・sender_constraint、H5・H6・H31、M_sender_constraint の 2.・4.、PH_AT・EMPLOYEE_AT の代わりの守り（3.1）
- 箇所ごとの「トークンを持つ者」と「鍵を持つ者」：
  - front-gw の代理店の口：AGENCY_AT を持つのは代理店のサーバー、TLS の鍵を持つのも代理店のサーバー（shirogane-as がトークンの要求の mTLS の証明書から cnf を書く）。一致する
  - TTS：front-gw が書いた拇印のヘッダーと cnf を比べる。見ているのは front-gw の見た鍵で、確かめの主は front-gw と明記されている。ヘッダーは front-gw だけが書け、同名は捨てる
  - 契約者・社員の口：PH_AT・EMPLOYEE_AT を持つのは claim-portal・staff-console で、口が受ける SVID もその 2 つだけ。一致する
- 気づき：証明書の更新（同じサブジェクトで出し直す）で拇印が変わり、古い証明書に束縛した AGENCY_AT は最大 300 秒で使えなくなる、と書いてある。CRL を取り直せないときに失効した証明書を最長 3600 秒受けうる限界は、可用性との引き換えとして書いてある。指摘なし

### op-source-change

- 選んだ出来事：査定担当者の退職・休職と、課をまたぐ異動
- 辿った範囲：C-scope・C-sub の source_system、9.2 の「元のデータからの経路」、H14・H17・H22・H23、3.1 の REQ-03 の起点の見送り、付録 D の M_authz_pdp の 1.・3.
- 退職・休職：人事部の入力と責任者の承認 → 社員の台帳 → TTS（キャッシュ 60 秒）→ 発行済みの TXN_STAFF 330 秒で、390 秒。ブローカーで待つ指示は H22 の作り直しで止まる。発効から台帳の更新までの区間は、持ち主（人事部・情報セキュリティ部）が受け入れると書いてある
- 気づき（F6）：課をまたぐ異動で役割（査定担当者）が残るとき、claim-svc の割り当ての記録を外す経路と時間が書かれていない。assessment-svc は「sub が請求に割り当てた査定担当者であること」だけを見て課を見ないので、異動した査定担当者は前の課の請求の要配慮の書類（documents:read-sensitive）を読み続けられる。9.2 は上長の異動（要求のたびに課を引く）だけを扱っている

### op-one-time

- 辿った値：AGENCY_ASSERTION の jti、AUTH_CODE、nonce、セキュリティキーの登録の番号、支払いの指示（(claim_id, assessment_ref)）、承認の記録、実行（payment_id）、保留の印
- jti：一意の制約つきの 1 回の書き込みで、並行の 2 件は 1 件だけ通り、記録先が応えなければ拒む。正しい 1 回は代理店のサーバーが新しい assertion で取り直せる
- 登録の番号：shirogane-sso が鍵の登録と同じ取引で条件つきの書き込みをする。並行・障害とも閉じている
- 支払いの指示：再配送・送り直しは (claim_id, assessment_ref) の一意の制約で 1 件になる。payment-worker は受け付けの後にだけ処理済みにするので、正しい 1 件は落ちない
- 気づき（F2）：古い版の指示の扱いが閉じていない。「同じ請求に未実行の指示がある間は新しい版を受けない」は、古い版のメッセージがブローカーに残ったまま新しい版が受け付けられ、夜間に実行された後に、古い版のメッセージ（PAY_MSG_CTX は 3600 秒有効）が届く場合を止めない。未実行の指示が無く、古い版の assessment_ref は初めてなので受け付けられ、合計が 100 万円未満なら承認なしで次の夜に実行される（二重払い）
- 気づき（F3）：保留の印の単位が決まっていない。H25 は「その請求の未実行の支払いの行をロックして保留の印を書く」、H24 は「請求の保留の印」と書く。行ごとの印なら、TTS の H22 の保留の参照の直後に保留が入り、その後で payment-svc が指示の行を書くと、その行に印が無く、実行の取引の確かめを通る（REQ-04 の「必ず効く」が崩れる）
- 気づき（F5）：AUTH_CODE の「2 回目の使用でその認可コードから出したトークンも失効させる」は、RT には効くが、JWT の PH_AT・EMPLOYEE_AT には効かない（front-gw と TTS は手元で検証し、イントロスペクションは却下）

## 段 5：優先 2 の問い

10 問すべてに答えた（下の表）。開いた問いの「さらに」（op-clock・op-key-custody・op-requirement-words）は辿っていない（op-clock は 12. と付録 D の M_token_validation の 6. を読んだだけ）。

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | claims.yaml `C-sub` の enforced_at（assessment-svc の行）、hops.yaml `H17` の validates.checks[3]、`H18` の validates.checks[3]・[4]、`H25` の validates.checks[2]、design.md 付録 D の M_authz_pdp の 1.（上長の行：assessment.hold・assessment.unhold）と 3.（請求の行）。答えを決める問い：q-object-level-authz | 上長に保留と保留の解除（assessment.unhold）を出すと決めているが、どの請求に許すかを確かめる文が無い。assessment-svc の確かめは「sub が割り当てた査定担当者」と、上長の閲覧・割り当ての変更（自分の課だけ）だけ。claim-svc（H18）と payment-svc（H25）は役割も課も見ない。この文を字のとおりに作ると、上長の保留が一切通らない（割り当てた査定担当者でないため）か、上長がほかの課の請求の保留（不正の疑いでかけた保留を含む）を外せる。M_authz_pdp の 3. の「上長は自分の課の請求」と、台帳・ホップの確かめが食い違う | Major | 実装とのずれ | q-object-level-authz |
| F2 | hops.yaml `H22` の validates.checks[3]・[4]、`H29` の validates.checks[2]・[3]、`H21` の validates.checks[2]、claims.yaml `C-txn` の enforced_at（payment-svc の行）、design.md 3.1 の見送り（高額の支払いの承認の行の (2)）。答えを決める問い：op-one-time | 支払いの指示の重複は (claim_id, assessment_ref) の一意の制約で止め、新しい版は「同じ請求に未実行の指示がある間」だけ拒む。古い版（v1）のメッセージがブローカーに残る間（PAY_MSG_CTX は 3600 秒）に、新しい版（v2）が受け付けられて夜間に実行されると、その後に届いた v1 は、未実行の指示が無く初めての assessment_ref なので受け付けられる。合計が 100 万円未満なら承認なしで実行される（二重払い）。上長の取り消しは、payment-svc にまだ記録の無い v1 を取り消せない。payment-svc か TTS（作り直しのとき）で、assessment_ref がその請求の今の確定の版であること（版が記録済みの最大より古ければ拒む）を確かめる規則が要る | Major | 候補の漏れ | op-one-time、q-long-running |
| F3 | hops.yaml `H25` の validates.checks[1]、`H24` の validates.checks[3]、`H22` の validates.checks[0]、design.md 付録 D の M_authz_pdp の 2.（請求の保留の行）、9.1 の止める単位の表（支払いの承認・請求の行）。要求：REQ-04 | 保留の印の単位（請求ごとか支払いの行ごとか）と、未実行の支払いの行がまだ無いとき（指示がブローカーにある間）の書き方が決まっていない。H25 は「未実行の支払いの行をロックして保留の印を書く」、H24 は「請求の保留の印」と書いて食い違う。行ごとの印なら、TTS が H22 で保留を引いた直後に保留が入り、その後で payment-svc が指示の行を書くと、印の無い行が実行の確かめを通る。REQ-04 の「実行の前なら必ず効く」を満たすには、請求ごとの印（H22 の請求ごとの集計の行など）にして、指示の受け付けの取引の中でも印を確かめることを書く必要がある | Major | 候補の漏れ | q-revocation-delivery、op-one-time |
| F4 | claims.yaml `C-tctx` の does_not_answer（q-authorized）と provenance、`C-scope` の enforced_at（payment-svc の行：保留の通知は assessments:write）、hops.yaml `H25` の validates.checks[2]（「payment-svc は役割を見ず、operation で見分ける」）、design.md 6. の UC4（q-authorized） | 保留（査定担当者・上長）と保留の解除（上長だけ）は、同じ scope（assessments:write）で、違いは tctx の operation だけ。台帳は tctx を「q-authorized に答えない」と宣言しているのに、payment-svc は operation を「上長だけが許された操作」の区別に使う。tctx は取引の内容を固定する仕組み（どの取引か）で、誰に何を許したかに答える仕組みではない。今は TTS が経路の表で operation を決めるので通るが、operation の値が request_details から来るように変えると、解除の権限が崩れる。解除に別の scope を置くか、台帳の answers・does_not_answer を実際の使い方に合わせて書く | Minor | 目的と仕組みの不一致 | q-authorized（rar-vs-custom・scope-vs-role）、txn-tctx |
| F5 | token_types.yaml `AUTH_CODE` の revocation[0].note | 「2 回目の使用でその認可コードから出したトークンも失効させる」とあるが、PH_AT・EMPLOYEE_AT は JWT で、front-gw と TTS は手元で検証し、イントロスペクションも状態リストも却下している（INTROSPECTION_RESPONSE_JWT・STATUS_LIST_TOKEN）。失効できるのは PH_RT だけで、AT は exp（最大 630 秒）まで受けられる。TTS の発行ごとの状態の参照も、認可コードの再使用を見ない。記述を「RT を失効させる。AT は exp まで残る」に直すか、TTS が見る失効の手段を書く | Minor | 前提の誤り | q-revocation-delivery、op-one-time |
| F6 | claims.yaml `C-sub` の enforced_at（assessment-svc の行）、`C-scope` の source_system・on_revoke、design.md 9.2 の「元のデータからの経路」（社員の台帳の行）、3.1 の見送り（REQ-03 の起点）。要求：REQ-03・REQ-08。答えを決める問い：op-source-change、q-freshness-mitigation | 課をまたぐ異動で役割（査定担当者）が残るとき、claim-svc の割り当ての記録を外す者・経路・時間がどこにも無い。assessment-svc の確かめは割り当てだけで課を見ないので、異動した査定担当者は前の課の請求の要配慮の書類を、割り当てが替えられるまで期限なく読める。9.2 は上長の異動だけを扱う。REQ-03 の「役割の変更」に課の変更が入るかを要求の持ち主に確かめ、入るなら、割り当てに課を持たせて assessment-svc が要求のたびに査定担当者の今の課と照らすか、異動の発効で割り当てを外す手続きと時間を書く | Major | 候補の漏れ | op-source-change、q-freshness-mitigation |
| F7 | sheet.md の 1. の性質の表（操作ごとの承認：当たらない）、design.md 3.1 の見送り（高額の支払いの承認をトークンの authorization_details に載せない）、hops.yaml `H23` | 性質の表は authorization_details が無いので「当たらない」としたが、支払いの 1 件ごとの上長の承認（REQ-05。payment_id・金額・payee_ref に結びつく）がある。設計の誤りではなく、性質の読み取りの漏れ。dc-05 と q-approval-from-as を足して答えた（どちらも Yes）。承認を記録で持つ設計は、承認の行に approval の名を持つ行を台帳に置かないので、triage の条件では拾えない | Minor | 前提の誤り | dc-05、q-approval-from-as |

件数：Blocker 0、Major 4（F1・F2・F3・F6）、Minor 3（F4・F5・F7）。

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| q-value-vocabulary | Yes | agency_code は変わらない番号で登録からだけ書き、内側の scope は TTS の発行のものだけを受ける |
| q-identifier-choice | Yes | 代理店の IdP の (iss, sub) は C-iss・C-sub の行になり、shirogane-as が agst_ に替える |
| ap-1-7 | Yes | agency_code・client_id・act の元のデータを書けるのは、2 人の操作の代理店管理部・IT 基盤部・人事部・IVR だけ |
| q-freshness-mitigation | Yes | 抜き取りの 3 行は、TTS が発行のたびに引くので要求に収まる（残りの行での異動の扱いは F6） |
| q-single-aud-resource | Yes | どの種別も aud は 1 つで、2 つ以上は受け手が拒む |
| q-no-passthrough | Yes | TTS が受ける相手・subject_token の種類・経路の表と役割による scope の絞り込みが決まっている |
| q-step-up-path-coverage | Yes | 承認・取り消し・管理は H23・H26 の受け手の API だけで、受け手が acr・auth_time を確かめる |
| ap-2-7 | Yes | コールセンターは TXN_PROXY でだけ請求を受け付けられ、claim-svc は stf_ の sub を査定の経路でしか受けない |
| q-authorize-service-and-user | Yes | すべてのホップで mTLS の SPIFFE ID を一覧と照らす |
| q-agent-short-lived-no-rt | Yes | 代理の社員の EMPLOYEE_AT・TXN_PROXY に RT は無い |
| q-outside-catalog | Yes | トークンを運ばない呼び出し・管理の口・やり直し・DB の直接の修正・U29・U30 に答えがある |
| q-object-level-authz | No | 上長の保留・解除の対象の請求を確かめる文が無い（F1） |
| q-approval-from-as | Yes | 承認は payment-svc の記録で、payment_id・金額・payee_ref に結びつき、実行の取引の中で照らす |
| q-operator-act | Yes | 代理は act、管理は社員の sub、DB の修正は変更の番号、夜間はワークロードの sub で見分けられる |
| q-revocation-delivery | Yes | 止める単位ごとに最悪 330〜810 秒で要求に収まる（記述の誤りは F5、保留の隙間は F3） |
| q-dependency-outage | Yes | TTS・状態・JWKS は拒む側、CRL は 3600 秒まで前のもの、夜間は次の夜、と決まっている |
| dc-05 | Yes | 承認はトークンに載らず、tctx の内側は文字列と exact の比べ方が決まっている |
| pa-01 | Yes | agency_code は TTS（登録との一致）と claim-svc（取扱代理店との一致）が使う |
| q-derived-value | Yes | 傷病・口座・全証券は載せず、tctx の項目は operation ごとに要るものだけで、email は ID トークンだけ |
| q-variant-comparison | Yes | 送信者制約の見送りは mTLS・DPoP の両方と比べ、開く攻撃（BFF の侵害）と代わりの守り（口の mTLS の相手）を書いた |
| q-idp-diff-absorbed | Yes | 代理店の IdP の値は shirogane-as と TTS で吸収し、内側は TTS の Txn-Token だけを受ける |
| q-original-principal | Yes | 作り直しの後も sub は元の利用者・社員のままで、仲介のサービスは自分の資格情報で書かない |
| q-step-up-by-rs | Yes | payment-svc・as-admin-api が決め、staff-console は案内だけ |
| q-long-running | Yes | PAY_MSG_CTX からの作り直しのたびに TTS が社員の状態・役割と保留を引き直す（古い版の指示は F2） |
| q-copies-outlive | Yes | ログは HMAC と業務の記録の項目だけ、IP のログは 90 日、トークンの全文は残さない |
| q-audit-correlation | Yes | txn を入口から実行まで引き継ぎ、claim_id・payment_id でつなぎ、sub・act は同じ鍵の HMAC |
| op-proof-holder | 該当なし | 開いた問い：辿った範囲では、確かめる鍵とトークンを持つ者が一致した（段 4） |
| op-source-change | 該当なし | 開いた問い：異動のときの割り当ての隙間を見つけた（F6） |
| op-one-time | 該当なし | 開いた問い：古い版の指示（F2）、保留の印（F3）、AUTH_CODE の記述（F5）を見つけた |
