# レビュー：designs/target（しろがね損保　保険金の請求と支払いの内部処理）

- 読んだもの：designs/target/ の design.md・claims.yaml・token_types.yaml・hops.yaml・catalog_answers.yaml・claim_request_agency_code.md、ci-result.txt、sheet.md（種 12）。教材は short_list.md・perspectives.md（問いの書き方と読み方）・decision_tree.md・contrasts/act-txn-workload.md・kind_tell.md
- 抜き取った行（種 12）：C-agency-code（組織独自の認可の行として必ず入れる行）・C-client-id・C-act
- 結論：Blocker 0・Major 0・Minor 5。設計の主要な仕組み（入口での Txn-Token への作り直し、TTS が発行のたびに台帳を引くこと、代理受付の act、PAY_MSG_CTX からの作り直し、支払いの承認・保留・実行の直列化）は、それぞれが要る問いに答えている。指摘はどれも、記述の抜けか、根拠の数字に入っていない区間

## 段 0：受け付け（CI の結果と lint の warn）

- ci-result.txt と設計書の 1. は一致する（error 0・warn 9・info 15）
- warn 9 件のすべてに、設計書の 1. の「残す理由」がある
  - L1b（C-req-wl・C-tctx）：草案 -11 の名前で、spec_version と見直しの条件がある。通る
  - L16 の H30（下流の寿命 3600 秒 > 上流の H29 の 300 秒）：REQ-06 の 3600 秒の待ちが理由。PAY_MSG_CTX は TTS への作り直しの要求でしか使えない。作り直しのときに TTS が勤務の状態と役割を引き直し、payment-svc が版と保留を確かめる（narrowing_exception）。q-hop-lifetime の答えは Yes として通す
  - L16 の aud（H4・H7・H15・H17・H23・H26）：Txn-Token の aud は信頼ドメイン（草案 §9.2）で名前が違う。絞り込みは C-aud の tts の行と内側の受け手の行で行う。通る
- 検査（lint）を通すために宣言を曲げた跡（q-lint-workaround）：H31 を H5 の upstream に置いていない。理由は「assertion は RFC 7523 の grant で、作り直しの上流ではない」（H31 の note）で、筋が通る。H24 に upstream が無いのは、内部で始まる取引（草案 §8.2）だから。曲げた跡は見当たらない

## 段 1：性質の表を図と要求に照らす

| 性質 | sheet.md の判定 | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 合う（C-agency-code は名前空間つきの authz の行） |
| 個人情報を載せる | 当たる | 合う（C-sub・C-act・C-email・C-tctx） |
| 発行者が複数 | 当たる | 合う（shirogane-as・shirogane-sso・TTS・代理店の IdP 2 社） |
| 交換・作り直し | 当たる | 合う（H4・H7・H15・H17・H23・H26 は reissue、H22・H24・H30 は exchange） |
| 委任 | 当たる | 合う（TXN_PROXY の act。max_delegation_depth 1） |
| 操作ごとの承認 | 当たらない | **実際には当たる**（F-1）。100 万円以上の支払いの承認は、payment_id・金額・payee_ref に結びつく 1 件ごとの承認（H23、3.1 の見送り）。トークンには載せないが、操作ごとの承認の性質はある。足した問い dc-05 と q-approval-from-as（委任の性質で既に出ている）に答えた |
| マルチテナント | 当たらない | 合う。ただし代理店ごとの絞り込みはテナントに近い。念のため q-tenant-data-match（claim-svc が証券の取扱代理店と agency_code を照らす）と q-cross-tenant-identity（agst_ は (iss, sub) の組で引き、代理店をまたいで名寄せしない）を見た。どちらも Yes |
| DB の層まで運ぶ | 当たらない | 合う（db_connection のホップが無い。U02 は対象外。9.1 の DB・ブローカーの接続の層） |
| 認証の強さ・新しさ | 当たる | 合う（C-acr・C-auth-time） |
| 送信者制約を選んだ | 当たる | 合う（AGENCY_AT は mtls） |
| 送信者制約を見送った | 当たる | 合う（PH_AT・EMPLOYEE_AT は none） |
| 長時間・非同期 | 当たる | 合う（PAY_MSG_CTX、H20・H21、U13） |

## 段 2：6. の「要る」問いを判断の木の節と比べる

| 問い | 判断の木の節 | 設計の仕組み | 合うか |
| --- | --- | --- | --- |
| q-sub | keep-sub-exchange | Txn-Token の sub に元の主体を保つ。作り直し（H22）でも査定を確定した社員。payment-batch は自分の SPIFFE ID で、利用者の sub を作らない | 合う |
| q-actor（UC3） | keep-sub-exchange | TXN_PROXY の act.sub（最も外側だけで、入れ子なし）。受け手は claim-svc・fraud-svc だけ | 合う |
| q-actor（UC4 は不要） | keep-sub-exchange | payment-worker は中身を変えられない運び手で、req_wl で記録する。対比表の「解く問い」では、req_wl は q-req-wl に答え、q-actor には答えない。設計はそのとおりに分けている（C-req-wl の does_not_answer に q-actor）。判断の木の「act＝仲介するワーカー」は代理の主体がいるときの選択で、ここでは理由（tctx を TTS が写すだけ、payment-svc が自分の記録で判断する）が書いてある | 合う |
| q-txn・q-req-wl | txn-tctx | txn と tctx を TTS だけが書く。Txn-Token ヘッダーで受け取ったまま渡す。tctx を受けるホップの受け手のすべてが本文・保存データと照合する（H4〜H26 の validates、C-tctx の enforced_at） | 合う |
| q-peer | peer-mtls | すべてのホップで mTLS の SPIFFE ID を照合する。req_wl・act では代えない（q-peer の channel） | 合う |
| q-authorized | carry-or-query／rar-vs-custom | 役割は載せず、TTS が台帳から引いて scope にする（C-roles は却下）。承認はトークンに載せず、payment-svc の記録で確かめる（3.1） | 合う |
| q-holder（UC2） | existing-claim-first（cnf） | cnf の x5t#S256（RFC 8705） | 合う |
| q-resource・q-user・q-agent | — | aud は 1 つ、sub は不変の ID、client_id | 合う |

目的と仕組みの不一致は見つからなかった。

## 段 3：優先 1 の問い（答えは末尾の表 (2)）

抜き取った 3 行ごとの要点：

- C-agency-code：値は AG と 6 桁の変わらない番号で、名前では照合しない。書くのは shirogane-as（代理店の登録から）と TTS（登録を引き直す）だけ。代理店の登録を書けるのは代理店管理部（as-admin-api。変更は 2 人の操作で、phr の認証が要る）と、承認と変更の番号つきの DB の直接の修正だけ。代理店の IdP の管理者は書けない。停止は 390 秒で効き、REQ-02 の 900 秒に収まる
- C-client-id：claim-portal・staff-console の登録は IT 基盤部の変更の手続き、代理店の登録は代理店管理部（2 人の操作）が書く。identifier_properties と on_missing がある
- C-act：書くのは TTS だけ。元になる値は、EMPLOYEE_AT の sub、社員の台帳の役割（人事部が書く）、通話の記録の担当者（IVR だけが書く）。社員の申告は使わない

## 段 4：開いた問い 3 つ

### op-proof-holder（鍵の持ち主）

- 辿った範囲：C-cnf の enforced_at（front-gw・tts）、AGENCY_AT の holder・sender_constraint、issuance_profile の tls_termination・forwarded_cert_header、H5・H6・H31、M_sender_constraint の 4.、3.1 の CRL の扱い
- 気づいたこと
  - front-gw（主）：トークンを持つのは代理店のサーバー。TLS で示された証明書の鍵を持つのも代理店のサーバー。この 2 つは一致する
  - TTS（従）：TTS が見ているのは front-gw が書いたヘッダーで、鍵の持ち主を自分では見ていない。設計もこれを「取り違えを拾う照合で、確かめの主は front-gw」と書いている。ヘッダーを書けるのは front-gw だけで、TTS は front-gw の SPIFFE ID からの要求でだけ読む
  - shirogane-as のトークンの端点は TLS を自分で終端するので、cnf に書く拇印は実際に接続してきたクライアントの証明書のもの
  - 証明書を更新すると拇印が変わり、古い AT は最大 300 秒で使えなくなる。代理店は新しい assertion で取り直す
  - 残る限界：CRL を取り直せない間は、失効した証明書を最長 3600 秒受けうる。3.1 に、可用性と引き換えに受け入れたことと、確かめ方が書いてある
- 判定：Yes

### op-source-change（権限の元データの変化を IdP の手前から辿る）

- 選んだ出来事：査定担当者の退職。その査定担当者が確定した支払いの指示が、ブローカーに残っている場合
- 辿った経路
  1. 人事部の担当者が人事の仕組みに入力し、責任者が承認した時点で社員の台帳が変わる（9.2）
  2. TTS は 60 秒のキャッシュの後に退職を見る。TXN_STAFF は最大 330 秒残る（390 秒 < REQ-03 の 600 秒）
  3. shirogane-sso は台帳を 60 秒ごとに引いて SSO_SESSION を消す
  4. ブローカーの PAY_MSG_CTX は、作り直し（H22）のときに TTS が勤務の状態を引き直して拒む。その後は滞留のキューに入り、上長が割り当てを替えて新しい版で確定する
  5. payment-svc がすでに受け付けた指示と承認は有効のまま（9.1 の注）
- 誰も時間を約束していない区間
  - 発令（発効）から台帳の更新まで。3.1 の見送りで人事部の前提（人事の規程の 12 条。急な退職は発覚から 1 時間以内）と毎月の突き合わせがあり、12. で要求の持ち主に確かめる点に挙げてある
  - 課の異動は役割が残るので、トークンの仕組みでは止まらない。3.1 の業務の規則と、毎日の突き合わせ（付録 A）に頼る。これも書いてある
- 図に無い書き込みの経路：IT 基盤部の DB の直接の修正（2.2）は、どの業務の記録にも効く。9.2 に経路として挙げてあり、変更の番号と毎月の監査がある。新しい経路は見つからなかった
- 判定：Yes

### op-one-time（1 回だけ使える値）

| 値 | 確かめと使用済みの記録 | 並行の 2 件 | 再送 | 記録先の障害 |
| --- | --- | --- | --- | --- |
| AGENCY_ASSERTION の jti | 一意の制約つきの 1 回の書き込み | 1 件だけ通る | 2 回目は拒む | 拒む |
| セキュリティキーの登録の番号 | 鍵の登録と同じ取引の中の、条件つきの書き込み | 1 件だけ通る | — | 登録しない |
| PAY_MSG_CTX からの指示 | payment-svc の (claim_id, assessment_ref) の一意の制約と、請求ごとの集計の行のロック | 1 件になる | 前の結果を返す | 再配送。期限を過ぎたら滞留のキュー（正しい 1 件は新しい版で出し直す） |
| 支払いの実行 | 支払いの行をロックした 1 つの取引。同じ payment_id は 2 回入れない | 直列 | 「実行済み」が見える | 実行しない（次の夜に回す） |
| AUTH_CODE | 「1 回だけ使える」とだけ書いてあり、確かめと使用済みにする書き込みが 1 つの操作かは書いていない | 不明 | 2 回目で PH_RT を失効させる（shirogane-sso の分は RT が無い） | 不明 |
| nonce | claim-portal・staff-console が「1 回使ったら消す」 | 書いていない | — | — |

- 気づいたこと：AUTH_CODE だけ、自前で作る発行者（shirogane-as・shirogane-sso。kind: self_built）なのに、ほかの値と同じ形（1 つの書き込みにする・記録先が応えなければ拒む）で書いていない（F-2）。PKCE と tls_client_auth があるので、引き換えられるのは BFF だけになり、影響は小さい
- 判定：No（AUTH_CODE について言い切れない。Minor）

## 段 5：優先 2 の問い

9 問すべてに答えた（表 (2)）。No は q-copies-outlive の 1 問で、指摘にした（F-4）。さらにの開いた問い（op-clock・op-key-custody・op-requirement-words）は、時間の都合で辿っていない。ただし、op-clock の材料（M_token_validation の 6.、12. の時計の行）と、op-key-custody の材料（M_token_validation の 8.）は読み、明らかな穴は見なかった。

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F-1 | sheet.md の 1.（性質の表「操作ごとの承認がある」が当たらない）。design.md の 3.1 の見送り（高額の支払いの承認をトークンの authorization_details に載せない）、hops.yaml の H23 の validates、catalog_answers.yaml の I14、design.md の付録 B | 性質の表は「authorization_details が無い」ことから「当たらない」としたが、設計には操作ごとの承認がある。100 万円以上の支払いの承認は、上長が 1 件ごとに行い、payment_id・金額・payee_ref に結びつく。トークンに載せないのは設計の選択で、承認の性質が無いのではない。そのため、この性質の問い dc-05 と q-approval-from-as を足して答えた（どちらも Yes）。設計を直す必要は無い。性質の読み方に、承認の記録を受け手が持つ形（payment-svc の承認の記録）も入れるとよい | Minor | 前提の誤り | dc-05・q-approval-from-as（rar-vs-custom） |
| F-2 | token_types.yaml の AUTH_CODE の revocation（method: one_time_use）。catalog_answers.yaml の idp（shirogane-as・shirogane-sso は kind: self_built）。claims.yaml の C-nonce の enforced_at（claim-portal・staff-console）。対比：C-jti の shirogane-as の行、design.md の 2.2（登録の番号） | 認可コードを 1 回だけ使わせる仕組みが「1 回だけ使える」としか書いていない。確かめと使用済みにする書き込みが 1 つの操作か、記録先が応えないときに拒むかが書いていない。shirogane-as・shirogane-sso は自前で作るので、決めるのはこの設計書になる。同じ設計書で jti と登録の番号はこの形で書いてあるので、そろえて書く。2 回目の使用で失効させるのは PH_RT だけで、shirogane-sso のコードから出た EMPLOYEE_AT は最大 630 秒残る。この限界も書く。nonce の「1 回使ったら消す」も同じ。PKCE と tls_client_auth で、引き換えられるのは BFF に限られるので、Minor とした | Minor | 候補の漏れ | op-one-time |
| F-3 | design.md の 9.1 の「止める単位ごと」の表の「社員の端末・セキュリティキーの紛失」の行（330 秒。届けを受けてから）、3.1 の見送り（社員の端末・セキュリティキーの紛失）、12. の「端末の紛失の目標」、付録 A | 330 秒は、IT 基盤部の担当者が届けを受けた瞬間に as-admin-api で消す前提の数字で、担当者が受けて操作するまでの時間（ハードウェアの鍵での認証し直しを含む）を数えていない。鍵の漏えい（REQ-10）には 480 秒の目標と毎月の訓練があるが、紛失の届けの受け付けから操作までには目標も測定も無い。そのため、「600 秒の目標に収まる」という結論が数字で支えられていない。担当者の受け付けの目標（当番・時間）を決め、付録 A の訓練に足す | Minor | 理由の不備 | q-revocation-delivery |
| F-4 | hops.yaml の H20 と H21 の validates（期限を過ぎたメッセージは滞留のキューに移る）、token_types.yaml の PAY_MSG_CTX の long_running、design.md の 9.1 の DB・ブローカーの接続の層、付録 A の「支払いの指示の滞留のキュー」 | 滞留のキューに移ったメッセージ（txn・請求の ID・PAY_MSG_CTX。PAY_MSG_CTX には、個人情報とした sub と tctx の金額・payee_ref が入る）を、いつまで持ち、誰が消すかが書いていない。期限が切れているので作り直しには使えないが、写しがいつまで残るかを答えられない。U28 の「分析基盤に複製しない」と、fraud-svc の 90 日の保持の書き方にそろえ、保持の期間と、読める者を書く | Minor | 候補の漏れ | q-copies-outlive |
| F-5 | claim_request_agency_code.md の問 25（「claim-svc の試験で、ほかの代理店の証券の請求を 403 にする」）、design.md の付録 D の M_authz_pdp の 3.（請求の照合に失敗したら 404。存在を知らせない） | 他の代理店の証券・請求への要求に返す応答の番号が、2 か所で違う。403 を返すと、その証券・請求があることを知らせてしまう。M_authz_pdp の 3. の 404 にそろえ、試験の期待値も直す（新しい請求の受付で 403 にする意図なら、その区別を M_authz_pdp の 3. に書く） | Minor | 実装とのずれ | q-object-level-authz |

重大度ごとの件数：Blocker 0・Major 0・Minor 5

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| q-value-vocabulary | Yes | agency_code は AG と 6 桁の不変の番号、act.sub・client_id も不変の ID。名前で照合しない。別の発行者の同じ文字列を通す経路も無い（agency_code は shirogane-as・TTS だけが登録から書く） |
| q-identifier-choice | Yes | 上流のキー（代理店の IdP の iss・sub）は C-sub の upstream_issuer にあり、identifier_properties・on_missing がある。付け替えの限界は 3.1 の見送り |
| ap-1-7 | Yes | 代理店の登録は代理店管理部の 2 人の操作（phr つき）か、承認つきの DB の修正だけ。act は TTS が台帳と IVR の記録から書く。代理店の IdP の管理者・社員本人は書けない |
| q-freshness-mitigation | Yes | agency_code は 390 秒 ≤ 900 秒。scope は AT・PAY_MSG_CTX が許容を超えるが、TTS が発行・作り直しのたびに引き直す（9.2）。act は never |
| q-single-aud-resource | Yes | どの種別も aud は 1 つ（C-aud の max_items 1、受け手は 2 つ以上を拒む）。resource で口ごとに 1 つ |
| q-no-passthrough | Yes | TTS は、頼める相手（front-gw・assessment-svc・payment-worker・payment-batch）を mTLS で決め、経路の表と役割で scope を絞る。Txn-Token を subject_token にした要求は拒む |
| q-step-up-path-coverage | Yes | 承認・取り消しの API は H23（front-gw から）だけ、管理の操作は H26 だけ。どちらも受け手が acr・auth_time を確かめる。指示・実行の経路は承認を書けない |
| ap-2-7 | Yes | コールセンターの役割には TXN_PROXY でしか claims の scope を出さない。claim-svc は stf_ の sub を査定の経路のほかでは受けない。契約者の PH_AT は claim-portal の中だけ |
| q-authorize-service-and-user | Yes | すべての受け手が mTLS の SPIFFE ID を一覧と照らし、そのうえで sub・scope・tctx を見る |
| q-agent-short-lived-no-rt | Yes | 代理の社員は EMPLOYEE_AT（RT なし）で、TXN_PROXY は 60 秒で本人確認から 1800 秒を超えない |
| q-outside-catalog | Yes | トークンを運ばない呼び出し、判定のやり直し、DB の直接の修正、U29・U30、夜間の処理の障害（手作業の経路は作らない）が書いてある |
| q-object-level-authz | Yes | 請求は claim-svc（持ち主・取扱代理店・割り当て）、書類は前段の claim-svc・assessment-svc と毎日の突き合わせ、支払いは payment-svc で止まる（応答の番号の食い違いは F-5） |
| q-approval-from-as | Yes | 承認は payment-svc の記録で、payment_id・金額・payee_ref・課の上長・phr に結びつく。頼む側の申告では決まらない |
| q-operator-act | Yes | 代理受付は act、管理の操作は sub と txn、DB の修正は変更の番号で残る。なりかわりの経路は作らない（2.2） |
| q-revocation-delivery | Yes | 止める単位ごとの最悪（390・750・810・690 秒など）が要求に収まり、寿命の数字もここから導いている。紛失の 330 秒には担当者の時間が入っていない（F-3） |
| q-dependency-outage | Yes | TTS・状態の参照・JWKS は拒む側に倒す（キャッシュは 60 秒）。CRL は 3600 秒の後に止める。fraud-svc は判定待ちにし、台帳が止まれば社員の口だけが止まる。それぞれ可用性の目標と照らしてある |
| dc-05（F-1 で足した） | Yes | tctx の内側は 9 項目すべて文字列で、amount は 10 進の文字列。比べ方は exact。スキーマで確かめない点は 3.1 の見送りで、代わりに共通の検証部品で確かめる |
| op-proof-holder | Yes | front-gw が見る鍵（TLS の証明書）は、AGENCY_AT を持つ代理店のサーバーの鍵。TTS は front-gw が書いたヘッダーで補う。更新すると古い AT は 300 秒で使えなくなる |
| op-source-change | Yes | 退職は台帳の更新から 390 秒で止まり、ブローカーの指示は作り直しで止まる。発効から台帳の更新までと課の異動は、3.1 で持ち主と確かめ方つきで見送っている |
| op-one-time | No | jti・登録の番号・指示・実行は 1 回に固まるが、AUTH_CODE（と nonce）の確かめと使用済みにする書き込みが 1 つの操作か書いていない（F-2） |
| pa-01 | Yes | agency_code で claim-svc が代理店の扱う証券だけに絞り、TTS が登録と照らす（25 問の問 1） |
| q-derived-value | Yes | 個人情報の行は、要る受け手と要る経路の tctx の項目にだけ載る。email は claim-portal だけ。IP・傷病・全証券は載せない |
| q-variant-comparison | Yes | 送信者制約の見送りで、mTLS（SVID の交代）と DPoP（同じ BFF に鍵を置く）を比べ、口の mTLS の制限という代わりの守りと、確かめ方がある |
| q-idp-diff-absorbed | Yes | 代理店の IdP の sub は shirogane-as が agst_ に替える。内側は TTS のトークンだけを受ける（M_token_validation の 2.） |
| q-original-principal | Yes | 作り直しの後も sub は元の主体のまま。payment-worker は自分の権限で指示しない。payment-batch は自分の ID だが、承認の記録と保留で判断される |
| q-step-up-by-rs | Yes | 求めるかどうかは payment-svc と as-admin-api が決め、staff-console は案内だけ（付録 B） |
| q-long-running | Yes | 60 分の待ちの後、作り直しで勤務の状態と役割を引き直し、実行の取引で承認・保留・payee_ref を確かめる |
| q-copies-outlive | No | 滞留のキューに残る PAY_MSG_CTX（sub・tctx）の保持の期間と消す者が書いていない（F-4）。監査ログは 7 年で HMAC、アクセスのログは 90 日と書いてある |
| q-audit-correlation | Yes | txn を作り直しまで引き継ぎ、承認・実行は payment_id でつなぐ。sub・act の HMAC は監査ログの基盤の 1 つの鍵で作る |
| q-hop-lifetime（L16 の warn） | Yes | H30 の 3600 秒 > 300 秒は、REQ-06 と作り直しのときの確かめが理由で通る |
| q-lint-workaround | Yes | H31・H24 に upstream を置かない理由は、grant・内部で始まる取引で、筋が通る |
