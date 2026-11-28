# レビューの記録：designs/target（しろがね損保　保険金の請求と支払い）

読んだもの：designs/target/ の design.md（1.〜12.・付録 A・B）、claims.yaml、token_types.yaml、hops.yaml、catalog_answers.yaml、claim_request_agency_code.md、ci-result.txt、sheet.md。教材は short_list.md、perspectives.md、decision_tree.md、contrasts/act-txn-workload.md、kind_tell.md。

## 段 1：性質の表を、図と要求に照らして確かめた結果

| 性質（sheet.md の判定） | 確かめた結果 |
| --- | --- |
| 組織独自のクレーム［当たる］ | 正しい。`C-agency-code`（名前空間つき、usage: authz） |
| 個人情報［当たる］ | 正しい。`C-sub`・`C-act`・`C-tctx` が「個人情報」 |
| 発行者が複数［当たる］ | 正しい。catalog の idp は shirogane-as・shirogane-sso・shirogane-tts・agency-idp。代理店の IdP は 2 社（hanamizuki・kumoi） |
| 交換・作り直し［当たる］ | 正しい。H30・H22（exchange）、H4・H7・H15・H17・H23・H26（reissue） |
| 委任［当たる］ | 正しい。TXN_PROXY の `C-act`（may_act は無い） |
| **操作ごとの承認［当たらない］** | **誤り**。authorization_details は無いが、REQ-05 の 100 万円以上の上長の承認（payment-svc の承認の記録。H22〜H25）、代理店の登録の変更とセキュリティキーの登録の番号の 2 人の操作（H26）がある。指摘 F8 にし、`dc-05` を足して答えた |
| マルチテナント［当たらない］ | 書き手の宣言どおり No でよいと判断した。ただし代理店ごとの境界（agency_code・代理店の IdP ごとの iss）は、テナントに近い働きをする（F2 はこの境界の問題） |
| DB の層まで運ぶ［当たらない］ | 正しい。db_connection の行が無く、U02 は対象外 |
| 認証の強さ・新しさ［当たる］ | 正しい。`C-acr`・`C-auth-time`（H23・H26・付録 B） |
| 送信者制約を選んだ・見送った［当たる］ | 正しい。AGENCY_AT は mtls、PH_AT・EMPLOYEE_AT は none |
| 長時間・非同期［当たる］ | 性質は正しいが、sheet が挙げた根拠（PH_AT の long_running）は「長い処理には使わない」の行。本当の根拠は PAY_MSG_CTX（3600 秒、ブローカー）と payment-batch |

## 段 2：6. の「要る」の問いと、判断の木の比較

- q-sub（UC1〜UC7）：keep-sub-exchange。sub を保って作り直し（UC4 は社員、UC6 は payment-batch の自分の ID で、利用者の sub を作らない）。木と一致
- q-actor（UC3 だけ要る）：act（TXN_PROXY）。最も外側の act だけを照合（claim-svc で入れ子を拒む）。UC4 は payment-worker を act にせず、req_wl と q-peer で記録する。木は「act＝仲介するワーカー」の例を挙げるが、対比表の「解く問い」では運んだワークロードは q-req-wl の問いで、payment-worker は中身を変えられない運び手と書いてあるので、不一致とはしなかった
- q-req-wl・q-txn：txn-tctx。tctx を受けるすべての受け手（ホップの受け手を含む）が本文と照合している（H4・H7〜H11・H15〜H19・H22〜H26）。Txn-Token は専用のヘッダーで受け、Authorization は読まない（H4）。一致
- q-peer：peer-mtls。どのホップも SPIFFE の mTLS で直接の相手を確かめ、req_wl は「直接の相手の照合には使わない」。一致
- q-authorized：scope と agency_code、承認は payment-svc の記録（rar-vs-custom の「細かい許可は PDP に置く」に当たる）。一致
- q-holder（UC2）：cnf（x5t#S256）。一致。UC1・UC3〜UC7 の不要は 3.1 の見送りの理由あり
- q-agent：client_id。一致。ただし TTS が client_id を確かめる記述が 6. と台帳で食い違う（F6）
- lifetime-by-situation：剥奪を急ぐ操作は TTS の都度の確認・payment-svc の実行の取引の中の確認。一致。ただし代理店の assertion の寿命の数値が台帳の中で食い違う（F1）

目的と仕組みの不一致の指摘は無い。

## 段 3：優先 1 の問いの答え（自分の言葉で 1 行）

- q-value-vocabulary：役割は社員の台帳の役割の ID から TTS が scope に替え、外の IdP の文字列を役割として通していない。Yes
- q-identifier-choice：代理店の IdP の sub は `C-sub` の upstream_issuer で (iss, sub) から agst_ に替え、identifier_properties・on_missing がある。Yes（iss と代理店の登録の結びつきは ap-1-7 で No）
- ap-1-7：`C-agency-code` を書けるのは代理店管理部（2 人）と DB の管理者（承認つき）、`C-act` の元は社員の台帳・IVR で、ここは良い。ただし shirogane-as が assertion の iss を「代理店の登録にある iss のどれか」と照らすだけで、mTLS のクライアントの登録の iss と同じかを確かめる記述が台帳に無い。別の代理店の IdP の assertion を、別の代理店のサーバーが使えうる。No（F2）
- q-freshness-mitigation：scope・agency_code は TTS の都度の確認で 390 秒に収まる。しかし代理店の担当者の停止の 750 秒は assertion を 60 秒と置いた計算で、台帳の確かめは 300 秒まで受ける（F1）。TXN_PROXY の終話後の 90 秒は要求の持ち主の受け入れが 12. に無い（F7）。No
- q-single-aud-resource：どの AT も aud は 1 つ（PAR と resource で 1 つ）。Yes
- q-no-passthrough：TTS は要求できるワークロードを SPIFFE ID で限り（PAY_MSG_CTX は assessment-svc だけ、作り直しは payment-worker だけ）、scope は経路の表で絞る。Yes
- q-step-up-path-coverage：承認・取り消し（H23）と管理（H26）は、受ける payment-svc・as-admin-api が acr と auth_time を確かめ、承認を書く経路はほかに無い。Yes
- ap-2-7：社員は TXN_STAFF（sub は自分の stf_）しか取れず、claim-svc は front-gw からの stf_ の sub を受けない。契約者の sub のトークンは act つきの TXN_PROXY だけ。Yes
- q-authorize-service-and-user：q-peer は mTLS で、受け手ごとに呼び出し元の一覧を持つ。Yes
- q-agent-short-lived-no-rt：staff-console・社員には RT を出さない（RT は claim-portal だけ）。TXN_PROXY は 60 秒。Yes
- q-outside-catalog：管理の口（as-admin-api）、DB の直接の修正（2.2）、試験の口（U30）、移行（U29）、トークンの無い呼び出しと再送（2. の表・H21）が書いてある。Yes
- q-object-level-authz：請求は claim-svc、書類は claim-svc・assessment-svc の前段と毎日の突き合わせで止まる。しかし承認では、上長が「その査定担当者の課の上長か」を payment-svc が確かめない（assessment-svc は課で絞るのに）。No（F3）
- q-approval-from-as：承認は payment-svc の記録で、payment_id・金額・payee_ref に結びつき、実行の取引の中で記録を引く。Yes
- q-operator-act：なりすましの経路は無く、DB の管理者の修正には変更の番号と DB の管理者を残す。Yes
- q-revocation-delivery：止める単位ごとの表（9.1）はあるが、代理店の担当者の停止の最悪は assertion を 300 秒まで受けると 300＋30＋330＋330＝990 秒で、REQ-02 の 900 秒を超えうる。No（F1）
- q-dependency-outage：TTS・状態の参照・JWKS が応えないときは拒む、CRL は 3600 秒まで前の CRL、夜間は次の夜に回す、と決めてある。Yes
- （足した問い）dc-05：承認に使う tctx の項目はすべて文字列で、amount は先頭の 0 と符号なしの 10 進の文字列、value_normalization がある。Yes

## 段 4：開いた問い

### op-proof-holder（辿った範囲：H31 → H5 → H6、PH_AT・EMPLOYEE_AT の見送り）

- H31：shirogane-as はトークンの要求の mTLS の証明書の拇印を cnf に書く。トークンを持つ者＝代理店のサーバー、鍵を持つ者＝代理店のサーバー（秘密鍵は代理店のサーバーだけ）
- H5：front-gw は代理店の口の TLS を終端し、接続の証明書の拇印と cnf を照らす。確かめる側が見る鍵は、今つながっている代理店のサーバーの鍵で、トークンを持つ者と一致する
- H6：TTS は鍵を見ず、front-gw が書いた拇印のヘッダー（Shirogane-Client-Cert-S256。strip_inbound: true、front-gw の SPIFFE ID からだけ読む）と cnf を照らす。確かめの主は front-gw と書いてあり、矛盾は無い
- 証明書の更新：同じサブジェクトで出し直すので登録はそのまま、拇印は変わる。古い証明書で取った AGENCY_AT（最大 330 秒）は新しい証明書では通らないが、RT が無く、新しい assertion で取り直すだけなので害は無い
- 気づき：4. の生成の表は「証明書を下流へ渡すヘッダー：None」と出すが、token_types.yaml の forwarded_cert_header には名前があり、表示の側のずれ（render）。PH_AT・EMPLOYEE_AT は鍵の束縛でなく、口の SVID の mTLS の相手の限定で代えている（3.1。鍵を持つ者の確かめではない、と明記されている）
- 答え：Yes

### op-source-change（辿った出来事：社員の異動で役割が外れる、代理店の担当者の退職）

- 社員の異動：人事部の担当者が人事の仕組みに入れ、責任者の承認で社員の台帳が変わる → TTS は 60 秒のキャッシュの後に引く → 発行済みの TXN_STAFF は 330 秒 → 390 秒（REQ-03 の 600 秒内）。SSO_SESSION は 60 秒、承認の上限額は payment-svc が承認のたびに引く、PAY_MSG_CTX は作り直しのときに引き直す
- 誰も時間を約束していない区間：発効から台帳の更新まで。3.1 の見送りで、持ち主（人事部・情報セキュリティ部）と月ごとの突き合わせが書いてある
- 図に無い書き込みの経路：DB の管理者の直接の修正は 2.2・9.2 に書いてある。通話の記録の「担当の社員」を IVR がどこから決めるか（電話機・ACD のログイン）は書いていない。TXN_PROXY の act の元データなので、書けるのは誰かを書き足すとよい（指摘にはしない。気づきとして残す）
- 代理店の担当者の退職：代理店の IdP で止める（しろがねは知らない）→ 次の assertion が出ない → 止める直前の assertion・AGENCY_AT・Txn-Token。ここで、台帳の確かめが assertion を 300 秒まで受けるので、750 秒の計算が崩れる（F1）
- 答え：Yes（辿れる。崩れる区間は F1）

### op-one-time（辿った値：代理店の assertion の jti、PAY_MSG_CTX と支払いの指示、承認、セキュリティキーの登録の番号、認可コード）

- assertion の jti：確かめと記録は一意の制約つきの 1 回の書き込みで、並行の 2 件は 1 件だけ、記録先の障害では拒む。ただし覚えるのは 90 秒で、受け入れる寿命は台帳の確かめで 300 秒まで。90 秒を過ぎた後、期限内の同じ assertion がもう 1 回通りうる（F1）
- 支払いの指示：再配送・並行は payment-svc の (claim_id, assessment_ref) の一意の制約で 1 件になる（H22）。ただし H21 は (txn, claim_id) と書き、食い違う（F4）
- 正しい 1 回が失われないか：H21 は受け付けまで確認しないので落とさない。しかし期限切れで滞留した後の送り直しは「同じ assessment_ref」と付録 A が書く一方、TTS は同じ assessment_ref の PAY_MSG_CTX を 2 回出さない（H29）。送り直しの経路が閉じていて、正しい指示が出せない（F5）
- 承認と実行：支払いの行のロックで、実行と取り消し・保留はどちらか一方だけが効く。同じ payment_id を 2 回入れない。良い
- セキュリティキーの登録の番号（24 時間・1 回だけ）：誰が「使用済み」にするか、確かめと使用済みが 1 回の書き込みか、並行の 2 件がどうなるかが書いていない（F10）
- 認可コード：60 秒・1 回・PKCE。1 回だけの実装は shirogane-as の実装の挙動なので、ここでは答えず、専門家に回す候補
- 答え：No

## 段 5：優先 2 の問い

- pa-01：claim_request の問 1 と各行の usage・enforced_at で、受け手ごとに決めることが言える。email は表示だけで認可に使わない。Yes
- q-derived-value：tctx の項目は経路の表で操作ごとに決め、IP（rctx）は載せない。傷病は載せない。Yes
- q-variant-comparison：送信者制約の見送りは mTLS と DPoP を比べ、代わりの守りと確かめ方がある。PAY_MSG_CTX の寿命の延長は、作り直しのときの確認で代える。Yes
- q-idp-diff-absorbed：代理店の IdP の値は shirogane-as と TTS で止まり、内側は TTS の Txn-Token だけ。Yes
- q-original-principal：作り直しの後も sub は元の利用者・社員で、scope は経路ごとに絞る。payment-worker は自分の権限で指示しない。Yes
- q-step-up-by-rs：追加の認証を求めるのは payment-svc・as-admin-api（401 insufficient_user_authentication）。Yes
- q-long-running：非同期の指示は作り直しのときに TTS が勤務の状態・役割・保留を引き直し、夜間の実行は承認・保留を実行の取引の中で確かめる。Yes
- q-copies-outlive：トークンの全体は記録せず、sub は HMAC。fraud-svc のアクセスのログは 90 日、分析基盤への複製は無い（U28）。Yes
- q-audit-correlation：txn を PAY_MSG_CTX から引き継ぎ、承認・実行（別の txn）は payment_id でつなぐ。sub と act.sub の HMAC は監査ログの基盤の 1 つの鍵。Yes

## 受け付け（段 0）で確かめたこと

- 1. の CI：error 0、warn 9。warn の理由は 1. の表にある（L1b・L16 の H30・aud の 6 ホップ）。数値に矛盾は見当たらない
- lint を通すために宣言を曲げた跡：H31 を H5 の upstream に置いていない（「上流を外す」に当たりうる）。H31 の note に理由（assertion は認可の grant で、作り直しの上流ではない）があり、妥当と判断して指摘にしなかった。H24 に upstream が無いのも、内部で始まる取引で妥当

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | claims.yaml `C-exp` の enforced_at（service: shirogane-as の check）／hops.yaml `H31` の validates.checks の 2 行目／token_types.yaml `AGENCY_ASSERTION` の max_lifetime・lifetime_set_by・jti_policy.max_age_seconds／claims.yaml `C-jti` の enforced_at（shirogane-as）／design.md 3.1 の見送り（Back-Channel Logout・SSF/CAEP の行）・9.1（代理店の担当者の行）。問い：q-revocation-delivery・q-freshness-mitigation・op-one-time | 代理店の assertion の寿命の上限の確かめが食い違う。H31 と目録は「exp − iat が 60 秒以下」だが、`C-exp` の shirogane-as の確かめは「300 秒を超える assertion は受けない」（300 秒まで受ける）。寿命を決めるのは代理店（lifetime_set_by: client）なので、shirogane-as の確かめが実際の上限になる。300 秒まで受けると、(1) 代理店の担当者の停止の最悪が 300＋30＋330＋330＝990 秒になり、REQ-02 の 900 秒と 3.1・9.1 の 750 秒の計算を超える。(2) jti は 90 秒だけ覚えるので、90〜330 秒の間に同じ assertion の 2 回目が通る。`C-exp` の shirogane-as の行を 60 秒に直す（ずれ 30 秒を足して 90 秒） | Major | 実装とのずれ | q-revocation-delivery・op-one-time |
| F2 | claims.yaml `C-iss` の enforced_at（service: shirogane-as）／hops.yaml `H31` の validates.checks の 1・2 行目／claims.yaml `C-sub` の upstream_issuer.normalization。問い：ap-1-7 | shirogane-as は assertion の iss が「代理店の登録にある iss のどれか」と一致するかを確かめるだけで、mTLS で認証したクライアント（client_id・証明書のサブジェクト）の登録の iss と同じかを確かめる記述が台帳に無い（H31 は「代理店の登録の iss」で、どの登録かが読めない）。代理店 A のサーバーが代理店 B の IdP の assertion（盗んだもの・B の IdP の管理者が作った担当者のもの）を出すと、B の担当者の (iss, sub) が A の代理店コードの AGENCY_AT に載り、A の証券の請求と記録に B の人が混ざりうる。agency_code の書き手を絞った意図（3.1 の重点）が、担当者の ID の側から崩れる。「assertion の iss が、認証したクライアントの代理店の登録の iss と一致すること」を `C-iss` と H31 に書き、担当者の表を代理店ごとに引くことを明記する | Major | 実装とのずれ | ap-1-7・q-identifier-choice |
| F3 | hops.yaml `H23` の validates.checks／claims.yaml `C-sub` の enforced_at（service: payment-svc）／design.md 付録 B の 1 行目・2.1（社員の行）・REQ-05。問い：q-object-level-authz・op-requirement-words | 承認する上長が、その支払いを指示した査定担当者の上長（同じ課）かを payment-svc が確かめない。確かめるのは「指示の sub と違う」と「承認の上限額」だけで、上長の役割を持つ社員なら、ほかの課の支払いの payment_id を指定して承認できる。assessment-svc では上長が読めるのを自分の課の請求に限っており（`C-sub` の assessment-svc の行）、同じ「上長」の言葉の扱いが受け手で違う。REQ-05 の「上長」に入る人を決め、payment-svc で割り当ての記録の課と承認者の課を照らすか、ほかの課の上長も承認してよいなら、その理由と要求の持ち主の受け入れを書く | Major | 候補の漏れ | q-object-level-authz |
| F4 | hops.yaml `H21` の validates.checks の 3 行目／hops.yaml `H22` の validates.checks の 4 行目／claims.yaml `C-txn` の enforced_at（payment-svc）。問い：op-one-time | 支払いの指示の重複を 1 件にする一意の制約のキーが食い違う。H21 は「(txn, claim_id)」、H22 と `C-txn` は「(claim_id, assessment_ref)。重複の判定に txn を使わない」。H21 のとおりに作ると、確定し直しで txn が変わった指示が二重に記録される。H21 を (claim_id, assessment_ref) に直す | Minor | 実装とのずれ | op-one-time |
| F5 | hops.yaml `H29` の validates.checks の 3 行目（同じ assessment_ref の PAY_MSG_CTX を 2 回出さない）／design.md 付録 A（支払いの指示の滞留のキューの行）／3.1 の見送り（承認の行の確かめ方「滞留の後に同じ assessment_ref で送り直しても 1 件だけ」）／9.1 の `PAY_MSG_CTX` の行。問い：op-one-time | PAY_MSG_CTX の期限が切れて滞留した指示を、付録 A と 3.1 は「同じ assessment_ref で送り直す」とするが、TTS は同じ assessment_ref の PAY_MSG_CTX を 2 回出さない。送り直しの経路が無く、正しい 1 件の指示が出せない（9.1 は「確定し直す」と書き、3 か所で手順が違う）。「期限切れで支払いの指示が記録されていない assessment_ref には出し直す」などの条件を H29 に書くか、送り直しは新しい版の確定だけと決めて付録 A・3.1 を直す | Minor | 実装とのずれ | op-one-time |
| F6 | design.md 6. の UC1・UC3 の q-agent の行（「TTS が claim-portal／staff-console の client_id だけを受ける」）／claims.yaml `C-client-id` の enforced_at（service: tts）／hops.yaml `H3`・`H14` の validates。問い：q-agent | 6. は TTS も PH_AT・EMPLOYEE_AT の client_id を確かめると書くが、台帳の TTS の確かめは「代理店の登録で client_id から代理店コードを引く」だけで、H3・H14 にも client_id の確かめが無い。実際に確かめるのは front-gw だけ（H2・H13）。TTS でも確かめるなら `C-client-id` の tts の行と H3・H14 に書き、確かめないなら 6. を直す | Minor | 実装とのずれ | q-agent |
| F7 | design.md 3.1 の見送り（電話の代理受付の行。「前提：要求の持ち主の保険金部がこの 90 秒を受け入れる。12.」）／12. の表／REQ-11。問い：q-freshness-mitigation・q-revocation-delivery | REQ-11 は「通話が終わったら止める」と読んだのに、終話の直前に出た TXN_PROXY は終話から最大 90 秒使える。3.1 はこの 90 秒の受け入れを前提とし、12. で確かめるとするが、12. の表にその行が無い。要求の持ち主に確かめる行を 12. に足す | Minor | 理由の不備 | q-freshness-mitigation |
| F8 | sheet.md 1. の「操作ごとの承認がある［当たらない］」／design.md 3.1 の見送り（高額の支払いの承認の行）、hops.yaml `H22`〜`H25`・`H26`。問い：dc-05・op-one-time・q-approval-from-as | 性質の判定が authorization_details の有無だけで決まり、承認の記録（REQ-05）と 2 人の操作という操作ごとの承認があるのに「当たらない」になっている。この性質の問い（dc-05）が出ていなかった。足して答えた結果、dc-05 は Yes（tctx の項目はすべて文字列で、正規化が決まっている） | Minor | 前提の誤り | dc-05 |
| F9 | design.md 2.2（社員の認証の管理の行）／hops.yaml `H26` の validates.checks の 5 行目／catalog_answers の I26 の note。問い：op-one-time | セキュリティキーの登録の番号は「24 時間・1 回だけ」とあるが、使用済みにするのは誰か（shirogane-sso か as-admin-api か）、確かめと使用済みが 1 回の書き込みか、並行の 2 件・記録先の障害でどうなるかが書いていない。この番号で登録した鍵が acr の phr になり、100 万円以上の承認と管理の操作を通すので、1 回だけの守り方を書き足す | Minor | 候補の漏れ | op-one-time |

重大度の件数：Blocker 0、Major 3、Minor 6（計 9）。

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| q-value-vocabulary | Yes | 役割は社員の台帳の役割の ID から TTS が scope に替え、外の IdP の文字列を役割に使わない |
| q-identifier-choice | Yes | 代理店の IdP の sub は C-sub の upstream_issuer と identifier_properties・on_missing がある行で、(iss, sub) から agst_ に替える |
| ap-1-7 | No | assertion の iss を、認証したクライアントの代理店の登録と結びつける確かめが台帳に無い（F2） |
| q-freshness-mitigation | No | 代理店の担当者の停止の計算が台帳の 300 秒の確かめで崩れ（F1）、TXN_PROXY の終話後 90 秒の受け入れが 12. に無い（F7） |
| q-single-aud-resource | Yes | どの AT も resource で aud を 1 つにし、口ごとに分けている |
| q-no-passthrough | Yes | TTS は要求できるワークロードを SPIFFE ID で限り、経路の表で scope を絞る |
| q-step-up-path-coverage | Yes | 承認・取り消し・管理の操作は、受ける payment-svc・as-admin-api だけが書き、acr・auth_time を確かめる |
| ap-2-7 | Yes | 契約者の sub のトークンを社員が得る経路は act つきの TXN_PROXY だけで、claim-svc は front-gw からの stf_ を受けない |
| q-authorize-service-and-user | Yes | どのホップも SPIFFE の mTLS で直接の相手を一覧と照らし、req_wl では代えない |
| q-agent-short-lived-no-rt | Yes | 社員・staff-console には RT を出さず、TXN_PROXY は 60 秒 |
| q-outside-catalog | Yes | 管理の口・DB の直接の修正・試験の口・移行・トークンの無い呼び出しと再送が書いてある |
| q-object-level-authz | No | 承認する上長が、その査定担当者の課の上長かを payment-svc が確かめない（F3） |
| q-approval-from-as | Yes | 承認は payment-svc の記録で、payment_id・金額・payee_ref に結びつき、実行の取引の中で引く |
| q-operator-act | Yes | なりすましの経路が無く、DB の管理者の修正は変更の番号と管理者を残し、毎月突き合わせる |
| q-revocation-delivery | No | 代理店の担当者の停止の最悪が、台帳の確かめでは 990 秒になり REQ-02 の 900 秒を超えうる（F1） |
| q-dependency-outage | Yes | TTS・状態の参照・JWKS の停止は拒む、CRL は 3600 秒、夜間は次の夜に回すと決めてある |
| dc-05 | Yes | （性質を足して答えた）tctx の項目はすべて文字列で、amount の形と正規化が決まっている |
| op-proof-holder | Yes | front-gw が接続の証明書の拇印と cnf を照らし、トークンを持つ者と鍵を持つ者はどちらも代理店のサーバー |
| op-source-change | Yes | 社員の異動は人事の仕組み → 台帳 → TTS（60 秒）→ Txn-Token（330 秒）と辿れ、約束しない区間は 3.1 にある（代理店の担当者の経路は F1 で崩れる） |
| op-one-time | No | assertion の jti の記憶 90 秒と受け入れ 300 秒の食い違い（F1）、重複のキーの食い違い（F4）、滞留の後の送り直しが閉じている（F5）、登録の番号の 1 回だけの守り方が無い（F9） |
| pa-01 | Yes | 受け手ごとに決めることが usage・enforced_at と問 1 で言え、表示用の email を認可に使わない |
| q-derived-value | Yes | tctx の項目は操作ごとに経路の表で決め、IP と傷病は載せない |
| q-variant-comparison | Yes | 送信者制約の見送りは mTLS と DPoP を比べ、代わりの守りと確かめ方がある |
| q-idp-diff-absorbed | Yes | 代理店の IdP の値は shirogane-as と TTS で止まり、内側には TTS のトークンだけが届く |
| q-original-principal | Yes | 作り直しの後も sub は元の利用者・社員で、payment-worker は自分の権限で指示しない |
| q-step-up-by-rs | Yes | 追加の認証を求めるのは操作を受ける payment-svc・as-admin-api |
| q-long-running | Yes | 非同期の指示は作り直しのときに、夜間の実行は実行の取引の中で、権限と保留を確かめ直す |
| q-copies-outlive | Yes | トークンの全体を記録せず、ログは HMAC、分析基盤への複製は無い |
| q-audit-correlation | Yes | txn を PAY_MSG_CTX から引き継ぎ、承認・実行は payment_id でつなぎ、HMAC の鍵は 1 つ |
