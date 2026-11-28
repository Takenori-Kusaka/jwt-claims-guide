# レビューの記録：designs/target（しろがね損保　保険金の請求と支払いの内部処理）

- 対象：designs/target/design.md と台帳（claims.yaml・token_types.yaml・hops.yaml・catalog_answers.yaml）、ci-result.txt、sheet.md
- 行の抜き取りの種：12（抜き取った行：C-agency-code・C-client-id・C-act。No が出たので C-sub・C-scope・C-acr・C-tctx も見た）
- 読んだ教材：short_list.md、perspectives.md（問いの書き方と読み方）、decision_tree.md、contrasts/act-txn-workload.md、kind_tell.md

## 0. 受け付け（CI の結果）

- error 0、warn 9、info 15。warn には行ごとの理由がある（設計書の 1.）
- L1b（req_wl・tctx）：草案の名前で名前空間に移せない、spec_version と見直しの条件あり。理由は通る
- L16（H4・H7・H15・H17・H23・H26 の aud）：Txn-Token の aud は信頼ドメイン（草案 §9.2）なので、外の AT の aud と名前が違うのは当然。scope と寿命は上流を超えていない（台帳で確かめた）。理由は通る
- L16（H30 の寿命：上流 H29 の 300 秒 → 3600 秒）：REQ-06 で最大 3600 秒待つため。PAY_MSG_CTX は TTS への作り直しにしか使えず、作り直しのたびに状態を引き直す（H22）。理由は通る（q-hop-lifetime）
- 宣言を曲げた跡（q-lint-workaround）：AGENCY_ASSERTION → shirogane-as のホップが hops.yaml に無いので、L16 は assertion（60 秒）→ AGENCY_AT（300 秒）を比べていない（指摘 F11）。C-sub の reassignable: false も、上流の付け替えを知ったうえでの宣言（指摘 F10）

## 1. 性質の表の確かめ（図と要求に照らして）

| 性質 | sheet.md | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 当たる（C-agency-code） |
| 個人情報を載せる | 当たる | 当たる（sub・act・tctx） |
| 発行者が複数 | 当たる | 当たる（shirogane-as・shirogane-sso・TTS・代理店の IdP 2 社） |
| 交換・作り直し | 当たる | 当たる（H4 ほかの reissue、H22・H24・H30 の exchange） |
| 委任 | 当たる | 当たる（TXN_PROXY の act） |
| 操作ごとの承認 | 当たらない | **実際にはある**。REQ-05 の 100 万円以上の支払いの承認は、payment_id と金額に結びつく 1 件ごとの承認（H23 の承認の記録）。トークンに載らないので authorization_details の読み方では拾えないが、性質としては当たる → 指摘 F15。出さなかった dc-05 を足して答えた（q-approval-from-as は委任で既に出ている） |
| マルチテナント | 当たらない | 当たらないで妥当。代理店ごとの分離は、テナントでなく証券の取扱代理店（agency_code と契約管理の仕組み）で claim-svc が行い、担当者の ID は (iss, sub) で代理店をまたいで混ざらない |
| DB の層まで運ぶ | 当たらない | 当たらない（db_connection のホップ無し。U02 は対象外） |
| 認証の強さ・新しさ | 当たる | 当たる（acr・auth_time。H23・H26） |
| 送信者制約を選んだ | 当たる | 当たる（AGENCY_AT の mtls） |
| 送信者制約を見送った | 当たる | 当たる（PH_AT・EMPLOYEE_AT は none） |
| 長時間・非同期 | 当たる | 当たる（PAY_MSG_CTX、ブローカー、夜間の処理） |

12.（書き手が自信のない点）も読んだ。草案の版・PAY_MSG_CTX の型・代理店の IdP の能力・tls_client_auth_san_uri は、IdP・製品の実際の挙動と仕様の解釈なので、専門家に回す候補として書き手の判断に同意する（レビュアーは答えない）。端末の紛失の要求の数値の欠落は、書き手が自ら挙げているが、問いの規則どおり指摘にした（F13）。

## 2. 6. の「要る」の問いと判断の木の照合

| 問い | 判断の木の節 | 設計の仕組み | 合うか |
| --- | --- | --- | --- |
| q-sub | keep-sub-exchange | TTS が sub を利用者のまま作り直す。PAY_MSG_CTX → TXN_TOKEN も sub は査定を確定した社員。payment-batch は自分の SPIFFE ID（利用者の sub を作らない） | 合う |
| q-actor（UC3） | keep-sub-exchange の確かめること | 最も外側の act だけ、入れ子なし（claim-svc・fraud-svc が入れ子を拒む） | 合う |
| q-actor 不要（UC4） | 対比表 act-txn-workload の「解く問い」 | payment-worker は中身を変えられない運び手で、req_wl（q-req-wl）と mTLS（q-peer）で別に記録。act で代えていない | 合う（取り違えではない） |
| q-req-wl | txn-tctx | req_wl を TTS が mTLS の相手から書く。payment-svc は operation ごとに req_wl を決め、直接の相手は mTLS で別に見る | 合う |
| q-peer | peer-mtls | すべてのホップで SPIFFE の mTLS、代理店とは代理店向けの CA の mTLS | 合う |
| q-txn | txn-tctx | Txn-Token ヘッダーで受け取ったまま渡す。ホップで受けるすべての受け手（H4・H7〜H11・H15〜H19・H22〜H26）が tctx を本文・パス・記録と照合 | 合う |
| q-user | keep-sub-exchange | sub（代理店は (iss, sub) から割り当てた agst_） | 合う |
| q-agent | （existing-claim-first） | client_id（RFC 9068） | 合う |
| q-authorized | carry-or-query・rar-vs-custom | scope（TTS が台帳から絞る）、agency_code（変わらない値なので載せる）、役割・承認の上限額・承認の記録は問い合わせる。承認は authorization_details に載せず payment-svc の記録（受け手が 1 つ） | 合う。ただし承認の記録が宛先（振込先）に結びつかない → F2 |
| q-resource | （aud） | AT は口ごとに 1 つ、Txn-Token は信頼ドメイン | 合う |
| q-holder（UC2） | existing-claim-first（cnf） | cnf.x5t#S256、front-gw が終端で照合、TTS が拇印のヘッダーで照合 | 合う |
| q-still-valid（寿命） | lifetime-by-situation | 寿命は「何秒で止めたいか」（REQ-01〜03・REQ-10）から導き、剥奪は TTS の発行のたびの問い合わせ | 合う |

判断の木の上では、目的と仕組みの不一致は見つからなかった。

## 3. 優先 1 の問いへの答え（自分の言葉で）

- q-value-vocabulary：Yes。agency_code は代理店の登録の変わらない番号（^AG[0-9]{6}$）で、代理店の申告（assertion）からは取らない。client_id はロールでなく不透明な ID。act.sub は stf_ の変わらない ID。内側の受け手は TTS の scope だけを読み、shirogane-as と shirogane-sso の同じ scope の文字列を直接は比べない
- q-identifier-choice：Yes。代理店の IdP の sub は C-sub の upstream_issuer で (iss, sub) の組から agst_ に替え、identifier_properties・on_missing がある。ただし reassignable: false は上流の性質と食い違う（F10）
- ap-1-7：No。agency_code の元の代理店の登録は代理店管理部が 2 人の操作で書くが、2.2 の「データベースを直接直す作業」（IT 基盤部）も承認の記録・代理店の登録・割り当て・保留を書ける経路で、台帳の書き手に数えていない（F7）。acr の phr を生むセキュリティキーの登録を誰が行えるかも書いていない（F6）。代理店のクライアントの証明書のサブジェクトを決めるのが IT 基盤部のクライアントの登録か代理店管理部の代理店の登録かが読み取れない（F16）
- q-freshness-mitigation：No。agency_code（390 秒／900 秒）・act（390 秒／600 秒）・client_id（never）は収まる。しかし REQ-03 の「休職」で TTS が止めるかが読めず、最悪 960 秒になりうる（F1）。端末の紛失には要求の数値が無い（F13）
- q-single-aud-resource：Yes。PH_AT・AGENCY_AT・EMPLOYEE_AT は aud が 1 つ（max_items 1、resource を 1 つ）。Txn-Token の aud は信頼ドメイン 1 つで、受け手ごとの口は mTLS の相手と operation で絞る
- q-no-passthrough：Yes。TTS は front-gw・assessment-svc（PAY_MSG_CTX だけ）・payment-worker（PAY_MSG_CTX からだけ）・payment-batch（時間帯の内だけ）からしか受けず、Txn-Token を subject_token とする要求は拒む。scope は経路の表で AT の scope の内に絞る
- q-step-up-path-coverage：Yes。phr と auth_time 300 秒を確かめるのは操作を受ける payment-svc（承認・取り消し）と as-admin-api（すべての変更）で、承認の記録を書く経路は H23 だけ。TXN_TOKEN（acr 無し）では拒まれる。ただし phr の値の元（セキュリティキーの登録）の守りは F6
- ap-2-7：Yes。コールセンターの社員が act の無いトークンで契約者の請求を出す経路は無い（stf_ の sub は claim-svc が assessment-svc の査定の経路でしか受けない、代理ログイン I19 は対象外）
- q-authorize-service-and-user：Yes。すべての受け手が呼び出し元の SPIFFE ID を一覧と照らし、利用者の権限（sub・scope・tctx）とは別に決めている
- q-agent-short-lived-no-rt：Yes。代理の主体（社員）には RT を出さない（EMPLOYEE_AT は prompt=none で取り直す）。TXN_PROXY は 300 秒で作り直しもしない
- q-outside-catalog：No。shirogane-sso の鍵の登録の管理と staff-console の「管理の機能」（9.1 の端末の紛失で使う）が図にも 2.2 にも無い（F6）。障害時の手作業（滞留のキューからの確定し直し）で支払いの指示が二重になりうる（F3）
- q-object-level-authz：Yes。他人の claim_id は claim-svc が持ち主・取扱代理店・割り当てで止め（404）、書類は claim-svc・assessment-svc が呼ぶ前に止める。ただし上長の請求の読み取りの範囲が節によって違う（F14）
- q-approval-from-as：No。承認は payment-svc の記録で、payment_id と金額に結びつき、頼む側の申告ではない。しかし承認の記録に振込先（payee_ref）が入っておらず、承認の後に振込先が変わっても承認が効く（F2）
- q-operator-act：No（軽微）。管理の操作は as-admin-api で sub・txn を残し、代理受付は act で見分けられる。DB を直接直す作業の結果は、業務の記録の上で利用者の操作と見分ける印が無い（F7）
- q-revocation-delivery：No。止める単位ごとの最悪は 9.1 に揃っている（契約者 390・代理店 390・代理店の担当者 750・社員 390・鍵 810／690 秒）。しかし休職（F1）と、実行の直前の保留・取り消しの競合（F4）で、要求の時間・「必ず効く」を満たせない場合がある
- q-dependency-outage：No（軽微）。TTS・状態の参照・JWKS・jti の記録先・社員の台帳は拒む側に倒すと決めている。代理店向けの CA の CRL を取り直せないとき、夜間の実行の時間帯に TTS が止まったときの倒し方が書いていない（F12）

## 4. 開いた問い

### op-proof-holder（鍵の持ち主を確かめる箇所）

辿った範囲：C-cnf の enforced_at（front-gw・TTS）、AGENCY_AT の holder・sender_constraint、H5・H6、issuance_profile の tls_termination・forwarded_cert_header、M_sender_constraint の 2.・4.。

| 確かめる箇所 | トークンを持つ者 | 確かめる鍵の持ち主 | 結果 |
| --- | --- | --- | --- |
| front-gw の代理店の口（H5） | 代理店のサーバー | TLS の相手（代理店のサーバーの証明書の鍵） | 一致する |
| TTS（H6） | front-gw（subject_token として出す） | front-gw が書いた拇印のヘッダー（front-gw の SPIFFE ID からだけ読む）＝代理店のサーバーの鍵 | front-gw の照合の写しを確かめるだけ。主は front-gw と明記しており筋が通る |
| front-gw の契約者の口・社員の口（H2・H13） | claim-portal・staff-console | 束縛なし。口の mTLS の相手（BFF の SVID）で代える | 3.1 の見送りどおり |

気づいたこと：証明書の更新は同じサブジェクトで出し直し、古い証明書に束縛した AT は最大 300 秒で使えなくなる（M_sender_constraint の 4.）。一方、25 問の問 3 には「証明書を替えてクライアントを登録し直すと client_id が変わる」とあり、更新の手順の書き方が 2 か所で違う（F16 に含めた）。代理店のサーバーの鍵が漏れた場合の止め方は、CRL の 300 秒と AT の 330 秒で読めるが、9.1 の「止める単位」の表に行が無い。CRL を取れないときの倒し方も無い（F12）。

### op-source-change（権限の元データが変わる出来事）

出来事：査定担当者が異動で査定担当者の役割を外れる。

辿った経路：人事部の担当者が人事の仕組みに入力 → 人事部の責任者の承認で社員の台帳が変わる（9.2）→ TTS が 60 秒のキャッシュの後に引き、次の TXN_STAFF から payments:instruct・assessments:write を出さない → 発行済みの TXN_STAFF は最大 330 秒 → ブローカーで待つ指示は H22 の作り直しで役割を引き直して止まる → 合計 390 秒（REQ-03 の 600 秒の内）。発効から台帳の更新までの区間は、3.1 の見送りで要求の持ち主が受け入れ、毎月の突き合わせ（付録 A）で確かめる。

気づいたこと：
- 図に無い書き込みの経路として、2.2 の DB の直接の修正がある（F7）
- H22 の作り直しは「在籍し査定担当者の役割があること」を引き直すが、その社員がまだその請求に割り当てられていること（claim-svc の割り当て）は引き直さない。待つ間に上長が別の担当者に割り当て直しても、前の担当者の確定した指示が通る。要求に直接の文は無いので指摘にせず、書き手に確かめを頼む
- 「休職」がこの経路でどう表されるか（在籍のままか）が書いていない（F1）

### op-one-time（1 回だけ使える値）

辿った範囲：AGENCY_ASSERTION の jti、AUTH_CODE、nonce、H29 の「同じ txn の PAY_MSG_CTX を 2 回出さない」、H21・H22 の (txn, claim_id) の一意の制約、H23 の承認の記録、H24 の実行。

| 値 | 並行の 2 件 | 切れた後の再送 | 記録先の障害 |
| --- | --- | --- | --- |
| assertion の jti | 一意の制約つきの 1 回の書き込みで 1 件だけ | 2 回目は拒む（正しい 1 回は、代理店のサーバーが新しい assertion で取り直せる） | 拒む |
| AUTH_CODE・nonce | 1 回だけ（2 回目で出したトークンも失効） | — | — |
| PAY_MSG_CTX（同じ txn） | TTS が 2 回出さない | assessment-svc が応答を受け取れずに再送すると拒まれ、同じ txn では取り直せない。担当者が確定し直すと新しい txn になる | — |
| 支払いの指示 (txn, claim_id) | 同じ txn なら 1 件 | 同じ txn の再配送は 1 件 | — |
| 支払いの実行 | payment_id を 2 回入れない | — | claim-svc が応えなければ次の夜 |

気づいたこと：
- 支払いの指示の重複の防ぎは txn に結びついているが、txn は入口の要求ごとに新しく作られる。滞留のキューに移った指示を「査定担当者が確定し直す」と新しい txn になり、前の指示を payment-svc が受け付けていた場合（受付の応答が payment-worker に届かず確認できなかった場合など）でも、2 件目は (txn, claim_id) の制約をすり抜ける。承認の要否は請求ごとの合計で決めるので、合計が 100 万円未満なら二重の支払いがそのまま実行に進む（F3）
- 実行（H24）は「保留でないことを claim-svc に問い合わせてから」状態を実行済みにするが、claim-svc の保留と payment-svc の実行の記録は別の DB で、問い合わせと書き込みの間に置かれた保留は効かない。承認の取り消しの確かめが実行の書き込みと同じ取引・同じロックの中かも書いていない（F4）

### さらに：op-requirement-words（時間の残りで辿った）

言葉：「休職」（REQ-03）、「通話の間」（REQ-11）。
- 「休職」：TTS の確かめ（H14・H22、4. の TTS の要求の表）は「在籍」と役割だけで、休職中の社員は人事の上では在籍のまま。shirogane-sso だけが「退職・休職」でセッションを消す（SSO_SESSION の revocation）（F1）
- 「通話の間」：TTS は「本人確認から 1800 秒以内」だけを見て、通話が終わったかを見ない。5 分で電話を切っても、残りの 25 分は契約者のいないところで代理の請求を出せる（F5）

op-clock・op-key-custody は、付録 D の M_token_validation の 6.・8. を読んだ範囲で、比べる時計（IVR・代理店の IdP の時計は 12. で自ら挙げている）と鍵ごとの持ち主・漏えい時の分数が書いてあり、新しい指摘は無い。

## 5. 優先 2 の問い

すべて答えた（下の (2) の表）。答えなかった問いは無い。

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | hops.yaml H14 の validates（「在籍していること」）、H22 の validates、design.md 4. の TTS が受ける要求の表、token_types.yaml SSO_SESSION の revocation（「退職・休職」）、REQ-03、9.1 の「社員」の行。問い：q-revocation-delivery・q-freshness-mitigation・op-requirement-words | REQ-03 は「退職・休職・役割の変更」を 600 秒で効かせると求めるが、TTS の確かめは「在籍」と役割だけで、休職を止める条件として書いていない（休職は人事の上では在籍のまま）。shirogane-sso だけが休職でセッションを消すので、TTS が休職を止めなければ、staff-console に残る EMPLOYEE_AT（630 秒）＋Txn-Token（330 秒）で最悪 960 秒になり 600 秒を超える。TTS が見る台帳の状態の値（在籍・休職・退職）と、休職で止めることを H14・H22 に書く | Major | 実装とのずれ | — |
| F2 | hops.yaml H23 の validates（承認の記録：承認者の sub・txn・時刻・金額）、H24 の validates、design.md 3.1 の見送り（承認を authorization_details に載せない）、9.2 の「証券の取扱代理店・振込先」の行。問い：q-approval-from-as | 承認の記録は payment_id と金額に結びつくが、宛先（振込先 payee_ref）に結びつかない。振込先は契約部が契約管理の仕組みで書け、実行の時点で承認と振込先を突き合わせる確かめが無いので、承認の後に振込先を変えると、上長が承認していない口座に 100 万円以上が払われうる。承認の記録に payee_ref を入れ、実行（H24）で指示の payee_ref・契約管理の仕組みの振込先と一致しなければ実行しない、とする | Major | 候補の漏れ | — |
| F3 | hops.yaml H22 の validates（(txn, claim_id) の一意の制約）、H29（同じ txn の PAY_MSG_CTX を 2 回出さない）、H21、token_types.yaml PAY_MSG_CTX の lifetime_refs（滞留したら査定担当者が確定し直す）、付録 A の滞留のキューの行。問い：op-one-time・q-outside-catalog | 支払いの指示の重複の防ぎが txn に結びついているが、確定し直し（手作業）や同じ請求の 2 回目の確定では新しい txn になる。前の指示を payment-svc が受け付けていた場合（payment-worker が受付の応答を受け取れずに滞留した場合など）、2 件目は一意の制約をすり抜け、合計が 100 万円未満なら承認も要らずに二重に支払われる。同じ請求の同じ査定の確定（確定の ID か claim_id と査定の版）を一意のキーにし、確定し直しの前に前の指示の有無を確かめる手順を書く | Major | 候補の漏れ | — |
| F4 | hops.yaml H24 の validates（保留を H25 で引いてから、状態を実行済みにする）、H25、9.1 の「支払いの承認・請求」の行（実行の前なら 0 秒）、REQ-04。問い：q-revocation-delivery・op-one-time | REQ-04 は「実行の前なら必ず効く」を求めるが、保留は claim-svc、実行の記録は payment-svc の別の DB で、問い合わせと実行済みの書き込みの間に置かれた保留は効かない。承認の取り消しの確かめが、実行の書き込みと同じ取引・同じ行のロックの中で行われるかも書いていない。「実行」の時点（状態を実行済みにした時点か、振込のファイルを送った時点か）を決め、保留・取り消しとの順序（ロックか、実行の後の取り消しの扱い）を書く | Major | 候補の漏れ | — |
| F5 | hops.yaml H14 の validates（本人確認から 1800 秒以内）、token_types.yaml TXN_PROXY、design.md 3.1 の見送り（通話の間の時間枠）、2.1 の「電話の代理受付の社員」の行、REQ-11。問い：op-requirement-words・ap-2-7 | REQ-11 は「通話の間」だけ代理受付を許すが、TTS は本人確認からの経過だけを見て通話が続いているかを見ない。通話が切れた後も最大 1800 秒、契約者のいないところで社員が契約者の名で請求・照会できる。通話の記録の終了の時刻を TTS が引き、終わった通話では出さない（要求の持ち主に「通話の間」と「30 分」のどちらで切るかを確かめる） | Major | 候補の漏れ | — |
| F6 | design.md 2. の範囲の図・2.2 システムの権限、9.1 の「社員の端末・セキュリティキーの紛失」の行、token_types.yaml STAFF_SESSION の revocation（「staff-console の管理の機能」）、catalog_answers.yaml I26、claims.yaml C-acr の authoritative_writer・source_system。問い：q-outside-catalog・ap-1-7 | 9.1 では IT 基盤部が shirogane-sso の鍵の登録を消し、staff-console の管理の機能でセッションを消すが、この 2 つの管理の口が図にも 2.2 にも無く、誰がどの資格情報で使えるかが書いていない。とくにセキュリティキーの登録を誰が行えるかは、REQ-05 の phr（承認・管理の操作の条件）の元のデータで、他人の社員のアカウントに鍵を登録できれば追加認証を満たせる。2 つの管理の口を図と 2.2 に足し、鍵の登録の手順（本人の確認・2 人の操作・記録）を C-acr の source_system に書く | Major | 候補の漏れ | — |
| F7 | design.md 2.2 の「緊急時の特権」の行（データベースを直接直す作業）、2. の「しろがねの発行者」の行、claims.yaml C-agency-code・C-scope の authoritative_writer・source_system、9.2 の「元のデータからの経路」。問い：ap-1-7・q-operator-act | DB を直接直す作業（基盤の変更の手続き）で、承認の記録・代理店の登録・請求の割り当て・保留を書き換えられるが、台帳の書き手と 9.2 の経路に数えていない。業務の記録の上で、その書き換えを利用者の操作と見分ける印も無い（承認の記録は承認者の sub だけ）。書ける表を挙げ、直接の修正で書いた行に変更の手続きの番号を残すなどの見分け方を書く | Minor | 候補の漏れ | — |
| F8 | hops.yaml H3 の validates の 5 行目（「rctx の req_ip は front-gw の接続の IP」）、claims.yaml C-rctx（decision：却下）、design.md 3. の rctx の行、付録 D の P5 の 2. | 台帳と設計書は rctx を載せないと決めているのに、H3 の確かめは TTS が rctx の req_ip を書くとしている。どちらかに揃える | Minor | 実装とのずれ | — |
| F9 | claims.yaml C-rctx の rationale（front-gw のアクセスのログの IP を fraud-svc が読む）、design.md 2. のトークンを運ばない呼び出しの表（front-gw → fraud-svc）、12. の「fraud-svc の IP の分析」の行 | front-gw の契約者の口は claim-portal の SVID からしか接続を受けないので、front-gw が接続から記録する IP は契約者のブラウザでなく claim-portal の IP になる。rctx を却下した前提（IP の傾向はアクセスのログで足りる）が契約者の請求では成り立たない。claim-portal が利用者の IP を渡すなら、その値を書ける者と偽装の扱い、ログの保持の期間と個人情報の扱い（REQ-12）を書く | Minor | 前提の誤り | — |
| F10 | claims.yaml C-sub の identifier_properties（reassignable: false）と note、付録 D の M_privacy_minimization の 6.、3.1 の見送り（担当者の ID の付け替え）。問い：q-identifier-choice・q-lint-workaround | agst_ は上流の代理店の IdP が sub を付け替えると別の人を指しうると自ら書いているのに、reassignable を false と宣言している。受け手や lint が「付け替わらない ID」として扱う（監査で同じ人とみなす）ので、宣言を上流の性質に合わせるか、agst_ だけ別の扱いを台帳に書く | Minor | 前提の誤り | — |
| F11 | hops.yaml H5 の note（代理店のサーバー → shirogane-as の assertion の要求をホップの表に入れない）。問い：q-lint-workaround・q-hop-lifetime（lint:L16） | AGENCY_ASSERTION（60 秒）から AGENCY_AT（300 秒）への寿命の延びと、宛先・独自クレームの変わり方が、ホップの表に行が無いため L16 で比べられていない。入れない理由が「網の外から shirogane-as の端点へ」だけで、ほかの境界の矢印（H1・H12）は入れている。行を足して warn に理由を付けるか、入れない理由を書く | Minor | 理由の不備 | — |
| F12 | hops.yaml H5 の validates（CRL を 300 秒ごとに取り直す）、claims.yaml C-cnf の on_revoke、H24（夜間の実行）、design.md 3.1 の重点（縮退の運転を持たない）。問い：q-dependency-outage | 代理店向けの CA の CRL を取り直せないときに代理店の口を通すのか止めるのか、毎日 1 時〜3 時の実行の時間帯に TTS が止まったときに支払いをどう扱うか（次の夜に回すか、手作業か）が書いていない | Minor | 候補の漏れ | — |
| F13 | design.md 9.1 の「社員の端末・セキュリティキーの紛失」の行、3.1 の見送り、12. の「端末の紛失の目標」。問い：q-freshness-mitigation・q-revocation-delivery | 端末・セキュリティキーの紛失の届けから止まるまでの要求の数値が無く、330 秒が足りるかを判定できない（書き手も 12. で挙げている）。要求の持ち主の回答を待ってから閉じる | Minor | 理由の不備 | — |
| F14 | design.md 付録 D の M_authz_pdp の 3.（社員は割り当てか役割（上長）で照らす）と、claims.yaml C-sub の enforced_at（claim-svc：stf_ は assessment-svc の査定の経路だけ。assessment-svc：割り当てた査定担当者だけ）。問い：q-object-level-authz | 上長が役割だけで請求を読めるのか、割り当て（と assessment.assign）に限るのかが 2 か所で違う。役割だけなら上長はすべての請求に届く。どちらかに揃え、上長の読める範囲を enforced_at に書く | Minor | 実装とのずれ | — |
| F15 | sheet.md 1. の「操作ごとの承認がある」の行（当たらない）。design.md 3.1 の見送り（高額の支払いの承認）、hops.yaml H23、REQ-05 | 100 万円以上の支払いの承認は、payment_id と金額に結びつく 1 件ごとの承認で、性質としては当たる。トークンに載せないので authorization_details の読み方では拾えない。承認の記録を持つ設計でも性質が読めるよう、台帳かホップに承認の ID の宣言を置くことを書き手に勧める（このレビューでは dc-05 を足して答えた） | Minor | 前提の誤り | — |
| F16 | claims.yaml C-client-id の source_system（クライアントの登録と、代理店の登録の client_id・代理店コード・証明書のサブジェクトの組）、design.md 2. の「しろがねの発行者」の行（クライアントの登録は IT 基盤部の変更の手続き）、claim_request_agency_code.md の問 3、付録 D の M_sender_constraint の 4.。問い：ap-1-7 | 代理店のクライアント（client_id と tls_client_auth の証明書のサブジェクト）を書くのが IT 基盤部のクライアントの登録か、代理店管理部の代理店の登録（as-admin-api）かが読み取れない。証明書を替えたときにクライアントを登録し直すのか（問 3）、同じサブジェクトで出し直すのか（M_sender_constraint の 4.）も食い違う。書ける者と更新の手順を 1 つに決める | Minor | 実装とのずれ | — |

重大度ごとの件数：Blocker 0、Major 6（F1〜F6）、Minor 10（F7〜F16）。

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| q-value-vocabulary | Yes | agency_code は登録の変わらない番号、client_id・act.sub も変わらない ID で、別の発行者の同じ文字列を内側で直接比べない |
| q-identifier-choice | Yes | 代理店の IdP の sub は C-sub の upstream_issuer で (iss, sub) から agst_ に替え、identifier_properties・on_missing がある（宣言の値は F10） |
| ap-1-7 | No | DB の直接の修正（F7）、セキュリティキーの登録（F6）、代理店のクライアントの登録（F16）の書き手が数えられていない |
| q-freshness-mitigation | No | 抜き取った 3 行は収まるが、休職で TTS が止まるかが読めず最悪 960 秒（F1）、紛失には要求の数値が無い（F13） |
| q-single-aud-resource | Yes | AT は口ごとに aud 1 つ、Txn-Token は信頼ドメイン 1 つで受け手は mTLS の相手と operation で絞る |
| q-no-passthrough | Yes | TTS は決まったワークロードからだけ、決まった subject_token だけを受け、scope を経路の表で AT の内に絞る |
| q-step-up-path-coverage | Yes | 承認・取り消し・管理の変更は H23・H26 だけで、操作を受ける側が acr・auth_time を確かめる |
| ap-2-7 | Yes | 社員の stf_ の Txn-Token は claim-svc が査定の経路でしか受けず、代理ログインも無い |
| q-authorize-service-and-user | Yes | すべての受け手が SPIFFE の mTLS の相手を一覧と照らし、利用者の権限とは別に決める |
| q-agent-short-lived-no-rt | Yes | 社員には RT を出さず、TXN_PROXY は 300 秒で作り直さない |
| q-outside-catalog | No | 鍵の登録・セッションの管理の口が図に無く（F6）、確定し直しの手作業で指示が二重になる（F3） |
| q-object-level-authz | Yes | 他人の請求は claim-svc が持ち主・取扱代理店・割り当てで 404 にする（上長の範囲の食い違いは F14） |
| q-approval-from-as | No | 承認は記録と照合されるが、宛先（振込先）に結びついていない（F2） |
| q-operator-act | No | 管理の操作と代理受付は見分けられるが、DB の直接の修正の結果に見分ける印が無い（F7） |
| q-revocation-delivery | No | 止める単位ごとの最悪は揃っているが、休職（F1）と実行の直前の保留・取り消し（F4）で要求を満たせない場合がある |
| q-dependency-outage | No | CRL を取れないとき・実行の時間帯に TTS が止まったときの倒し方が無い（F12） |
| dc-05（性質を足して答えた） | Yes | 取引の値の tctx は 8 項目すべて文字列で、金額は 10 進の文字列、比べ方は exact と台帳に書いてある（スキーマの外は 3.1 の見送り） |
| pa-01 | Yes | agency_code は claim-svc が証券の取扱代理店を絞り、TTS が登録と一致を確かめる（25 問の問 1） |
| q-derived-value | Yes | 個人情報は sub・act・tctx だけで、tctx は operation ごとに要る項目だけを TTS が入れ、口座は参照 ID |
| q-variant-comparison | Yes | 送信者制約の見送りは mTLS と DPoP を比べ、開く攻撃（盗んだ AT）と代わりの守り（口の mTLS の相手の制限と CI の試験）を書いている |
| q-idp-diff-absorbed | Yes | 外の AT・assertion は front-gw・TTS・shirogane-as で止まり、内側は TTS の形の Txn-Token だけを受ける |
| q-original-principal | Yes | 作り直しの後も sub は元の利用者・社員で、payment-worker・claim-svc が自分の権限で下流を呼ばない |
| q-step-up-by-rs | Yes | 追加の認証を求めるかは payment-svc・as-admin-api が決め、staff-console は案内だけ |
| q-long-running | Yes | Txn-Token を持ち越さず、作り直し（H22）と実行（H24）の時点で状態・保留・承認を引き直す（休職の扱いは F1） |
| q-copies-outlive | Yes | 写しは監査ログ（HMAC・7 年）・fraud-svc の記録（90 日）だけで、判断の結果をキャッシュしない（アクセスのログの保持は F9 に含めた） |
| q-audit-correlation | Yes | txn を入口から作り直しまで引き継ぎ、sub・act.sub は同じ鍵の HMAC、承認は payment_id と txn で 1 本につながる |
| op-proof-holder | 該当なし | 開いた問い：AGENCY_AT の持ち主と鍵の持ち主は一致。気づきは 4. に書いた（F12・F16） |
| op-source-change | 該当なし | 開いた問い：異動を辿り 390 秒で効く。DB の直接の修正（F7）、割り当ての引き直しの欠落、休職（F1）を 4. に書いた |
| op-one-time | 該当なし | 開いた問い：txn に結びつく重複の防ぎ（F3）と、実行の直前の競合（F4）を 4. に書いた |
