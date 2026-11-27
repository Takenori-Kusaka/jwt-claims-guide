# レビューの記録：designs/target（しろがね損保 保険金の請求と支払い）

- 読んだもの：designs/target/ の design.md・claims.yaml・hops.yaml・token_types.yaml・catalog_answers.yaml、ci-result.txt、sheet.md（行の抜き取りの種 12）、short_list.md・perspectives.md・decision_tree.md・kind_tell.md
- 抜き取った行：C-agency-code（組織独自の認可の行として必ず入れる行）・C-client-id・C-act
- 答えた範囲：優先 1 の 16 問すべて、開いた問い 3 つ、性質の表で足した問い（dc-05・q-approval-from-as）、優先 2 の 9 問。「さらに」の開いた問い（op-clock・op-key-custody・op-requirement-words）は辿っていない（op-clock は 12. の「時計」の行を読んだだけ）

## 0. 受け付け（CI の結果）

- error 0・warn 8・info 15。design.md の 1. の結果と ci-result.txt は同じ
- warn の理由：L1b（req_wl・tctx）は草案の名前で、spec_version と見直しの条件があるので理由は通る。L16（H4・H7・H15・H17・H23・H26 の aud）は、Txn-Token の aud が信頼ドメインになることが理由。6 つのホップの scope が上流（H3・H6・H14）の部分集合で、寿命も 300 ≤ 600・300 であることを確かめたので、理由は通る
- 宣言を曲げた跡：H20 の書き方に 1 件ある（指摘 F7）

## 1. 性質の表の確かめ（sheet.md の 1.）

| 性質 | sheet | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 合う（C-agency-code） |
| 個人情報 | 当たる | 合う（C-sub・C-act・C-tctx・C-email） |
| 発行者が複数 | 当たる | 合う（shirogane-as・shirogane-sso・TTS・代理店の IdP 2 社） |
| 交換・作り直し | 当たる | 合う（H4・H7・H15・H17・H22〜H24・H26） |
| 委任 | 当たる | 合う（TXN_PROXY の act） |
| **操作ごとの承認** | **当たらない** | **実際には当たる**。100 万円以上の支払いは上長が承認する（REQ-05）。承認は payment_id と金額に結びついた payment-svc の記録で、H23 で 1 件ごとに書く。authorization_details を使わないので、機械が読み落とした（指摘 F3）。dc-05・q-approval-from-as を足して答えた |
| マルチテナント | 当たらない | 合う（書き手の宣言どおり。代理店ごとの絞り込みは agency_code と取扱代理店で行い、q-object-level-authz で確かめた） |
| DB の層まで運ぶ | 当たらない | 合う（db_connection のホップが無い。9.1 の DB の接続の層も「無い」） |
| 認証の強さ・新しさ | 当たる | 合う |
| 送信者制約を選んだ | 当たる | 合う（AGENCY_AT が mtls） |
| 送信者制約を見送った | 当たる | 合う（PH_AT・STAFF_AT・Txn-Token が none） |
| 長時間・非同期 | 当たる | 合う（H20・H21 の broker_connection、U13 が該当） |

## 2. 判断の木の節と、設計の仕組みの比べ（6. で「要る」とした問い）

| 問い | 木の節 | 設計の仕組み | 比べた結果 |
| --- | --- | --- | --- |
| q-sub | keep-sub-exchange | TTS が sub を保って Txn-Token を作り直す。UC4 は社員の sub を PAY_MSG_CTX から引き継ぐ。UC6 は payment-batch 自身の ID | 合う（利用者の文脈が要らない UC6 は、サービスの ID で動いている） |
| q-actor（UC3） | keep-sub-exchange | act（act.sub は社員、入れ子なし）。claim-svc・fraud-svc は最も外側の act.sub だけを照らす | 合う |
| q-actor（UC4。設計は「不要」） | keep-sub-exchange | 非同期の指示を動かす payment-worker を、act でなく req_wl と q-peer で表す | **合わない**：木は「sub＝利用者、act＝仲介するワーカー」。設計の C-req-wl も does_not_answer に q-actor を書いている（指摘 F4） |
| q-req-wl | txn-tctx | req_wl（TTS が mTLS の相手の ID を書く） | 合う。req_wl を直接の相手とみなしていない |
| q-peer | peer-mtls | SPIFFE の mTLS と、代理店向けの CA の証明書の mTLS。ホップごとの呼び出し元の一覧 | 合う |
| q-txn | txn-tctx | txn・tctx。専用の Txn-Token ヘッダー。受け手が本文と照合する | おおむね合う。H18 だけ、ホップの validates に claim_id の照合が無い（指摘 F9） |
| q-user | carry-or-query | sub（不透明な ID）。属性は問い合わせる | 合う |
| q-agent | （該当の節なし。existing-claim-first） | client_id（RFC 9068） | 合う |
| q-authorized | rar-vs-custom・carry-or-query | scope（TTS が台帳の役割から絞る）、agency_code、acr・auth_time。高額の承認はトークンに載せず payment-svc の記録 | 合う。authorization_details は 3.1 で検討して見送り、照合する受け手が payment-svc だけという理由が付いている。role は載せずに問い合わせる（C-roles は却下） |
| q-resource | （aud） | 口ごとに 1 つの aud、内側は信頼ドメイン | 合う |
| q-holder（UC2） | existing-claim-first（cnf） | cnf.x5t#S256（RFC 8705） | 合う |
| q-still-valid | lifetime-by-situation | 短い寿命と、TTS が発行のたびに台帳を引く | 考え方は合う。ただし代理店の担当者の停止の最悪の秒数を数え落としている（指摘 F1） |

## 3. 優先 1 の問いへの答え

### クレームの行（C-agency-code・C-client-id・C-act）

- q-value-vocabulary：Yes。agency_code は AG＋6 桁の変わらない番号で、しろがねの代理店の登録からだけ書き、代理店の申告（assertion）からは取らない。client_id は口ごとに 1 つの発行者のものだけを受ける。act は stf_ の ID。名前の文字列での照合は無い
- q-identifier-choice：Yes。代理店の IdP の sub は C-sub の upstream_issuer で (iss, sub) の組から agst_ に替え、行に identifier_properties と on_missing がある。C-client-id にもある。補足：(iss, sub) を代理店が付け替えると agst_ が別の人を指す。12. に既知の限界として書いてあるので、指摘にはしない
- ap-1-7：Yes。agency_code の元の登録を書けるのは代理店管理部だけ（as-admin-api、phr と 2 人の操作）。代理店の IdP の管理者は書けない。client_id はクライアントの登録（IT 基盤部の変更の手続き）。act は TTS が STAFF_AT の sub から書き、照らす相手は IVR だけが書く通話の記録と、人事部だけが書く役割
- q-freshness-mitigation：Yes（この 3 行）。agency_code は許容 900 に対して遅れ 390（登録のキャッシュ 60＋Txn-Token 330）。client_id と act は寿命の間に変わらない。act は発行のたびに記録と台帳を引く

### 経路

- q-single-aud-resource：Yes。AT の aud は口ごとに 1 つ（resource で 1 つだけ求める）。2 つ以上の値はどの受け手も拒む
- q-no-passthrough：Yes。TTS が受ける要求は 4. の表のとおり、要求するワークロード・subject_token・出す種別の組で決まっている。Txn-Token を subject_token にする要求は受けない（PAY_MSG_CTX を作る場合だけが例外）。scope は経路の表と役割で絞る
- q-step-up-path-coverage：Yes。承認・承認の取り消しは payment-svc の 1 つの API だけが受け（req_wl と mTLS の相手は front-gw）、管理の変更は as-admin-api だけが受ける。どちらも acr の phr と auth_time の 300 秒を、操作を受ける側が確かめる。代理受付（TXN_PROXY の scope）と非同期の経路（payment.instruct）からは承認を書けない
- ap-2-7：Yes。代理受付の社員が自分の TXN_STAFF で請求を出そうとしても、claim-svc は stf_ の sub を assessment-svc からの査定の経路でしか受けない。TXN_PROXY には必ず act が入る
- q-authorize-service-and-user：Yes。すべてのホップで、mTLS の相手の ID を呼び出し元の一覧と照らす。そのうえで Txn-Token の sub と scope を見る
- q-agent-short-lived-no-rt：Yes。代理の主体（コールセンターの社員）には RT を出さない（shirogane-sso は RT を出さない）。payment-worker も RT を持たない

### 設計の全体

- q-outside-catalog：**No**。図にもホップにも無い呼び出しがある。TTS から claim-svc への請求の保留の問い合わせ（H22 の確かめ）、TTS から shirogane-as の状態の参照の API、payment-svc から社員の台帳への承認の上限額の問い合わせ。どの資格情報で呼び、受ける側が何を確かめるかが書いていない（指摘 F6）。U29・U30・障害時の手作業（2.2）・試験の経路には答えている
- q-object-level-authz：Yes。他人の claim_id は claim-svc で止まる（契約者は証券の契約者と sub、代理店は取扱代理店と agency_code、社員は割り当てで照らし、404 を返す）。書類は document-svc、支払いは payment-svc で止まる
- q-approval-from-as（性質の表で足した問い）：Yes。承認は申告ではなく payment-svc の記録で、payment_id と金額に結びつく。承認者は指示した社員と別で、上限額は台帳で確かめる。実行の時点でも記録を引く
- dc-05（性質の表で足した問い）：Yes。tctx の内側は 8 項目すべて文字列で、amount の正規化（先頭の 0 と符号を付けない）と exact の比べ方を決めている。生成した JSON Schema が内側の型を見ないことは、3.1 の見送りに確かめ方つきで書いてある
- q-operator-act：Yes。管理の操作は社員本人の sub で残る。代理受付は act で見分けられる。なりすましの経路と DB を直接直す経路は 2.2 で決めてある
- q-revocation-delivery：**No**。代理店の担当者を代理店の IdP で止めた場合の最悪を 660 秒としているが、発行済みの assertion の寿命を数えていない。実際は最悪約 990 秒（指摘 F1）
- q-dependency-outage：Yes。TTS・状態の参照・JWKS が応えなければ拒む。fraud-svc が止まれば「判定待ち」で受け付ける。実行の時点で claim-svc が応えなければ、その支払いは次の夜に回す。社員の台帳・IVR が止まれば社員の口だけが止まる。それぞれ 3.1 と 12. に可用性の目標と並べて書いてある

## 4. 開いた問い

### op-proof-holder

- 辿った範囲：AGENCY_AT の cnf（C-cnf の enforced_at）、H5・H6、forwarded_cert_header、M_sender_constraint の 2. と 4.、AGENCY_ASSERTION の note
- 箇所ごとの「トークンを持つ者」と「鍵を持つ者」
  - shirogane-as のトークンの端点：tls_client_auth の証明書の拇印を cnf に書く。トークンを持つのも鍵を持つのも代理店のサーバー
  - front-gw：TLS の相手の証明書と cnf を照らす。どちらも代理店のサーバー
  - TTS：front-gw だけが書けるヘッダーの拇印と cnf を照らす。拇印は front-gw が終端した代理店のサーバーの証明書のもの
- 気づき：どの箇所でも一致する。束縛の単位は代理店のサーバーで、担当者ではない。I29 の pairwise に書いてあり、代理店の信頼の前提どおり。証明書を更新すると、古い証明書に束縛した AT は最大 300 秒で使えなくなり、新しい assertion で取り直す。client_id と証明書が組であることは、front-gw の行では「client_id が登録にあること」だけだが、cnf と tls_client_auth を通して確かめられている

### op-source-change

- 選んだ出来事：査定担当者の異動（役割が外れる）
- 辿った経路：人事部の担当者が人事の仕組みに入力し、責任者が承認する → 社員の台帳がその場で変わる → TTS が 60 秒のキャッシュの後に引く → TXN_STAFF は最大 330 秒 → 390 秒で止まる。ブローカーで待つ PAY_MSG_CTX は、作り直しのときに TTS が台帳を引くので止まる。SSO_SESSION は 60 秒。承認の上限額は承認のたびに問い合わせる
- 気づき：
  - 誰も時間を約束していない区間がある。REQ-03 の 600 秒を「社員の台帳が変わってから」数えているが、異動・退職の発令から人事部が入力して承認するまでの時間には、設計にも 9.2 にも目標が無い（指摘 F8）
  - 作り直し（H22）で引き直すのは、在籍・役割・保留だけ。その請求への割り当てが今も有効かは引き直さない。割り当てを外した後の指示も、役割が残っていれば通る（軽い。指摘にはしない）

### op-one-time

- 辿った値：AGENCY_ASSERTION の jti（shirogane-as が 330 秒覚える）、AUTH_CODE（1 回だけ。2 回目で発行済みも失効）、nonce（使ったら消す）、PAY_MSG_CTX（payment-worker が txn を覚える）、支払いの指示（payment-svc が txn と claim_id の組を 2 回受けない）、支払いの実行（状態の変更と振込のファイルへの追加を 1 つの取引で行う）
- 気づき：
  - 承認の要否の判定が、並行の 2 件で破れうる。H22 では、同じ請求の支払いの合計（実行済み・承認待ち・この指示）が 100 万円以上なら「承認待ち」にする。同じ請求に txn の違う指示が 2 件同時に届いたとき（例：60 万円ずつ）、この合計の読み取りと判定を請求ごとにまとめて行う（直列にする・ロックする）ことが書いていない。どちらも相手を数えずに 60 万円と判断すれば、承認なしで 120 万円になる（REQ-05）。txn と claim_id での重複の拒否は txn が違うので効かない（指摘 F2）
  - jti の記録の確かめと書き込みが不可分か（並行して届いた同じ assertion を 2 回通さないか）は書いていない。代理店の IdP の実装の範囲ではなく shirogane-as の実装なので、作った後に確かめる項目として残す
  - payment-worker が txn を「処理済み」にする時点が、payment-svc が受け付けた後か前かが書いていない。前なら、TTS への要求の後に worker が落ちたとき、再配送されたメッセージを捨てて、正しい 1 件が失われる。payment-svc の側でも重複を拒むので、worker の側の記録は受け付けの後にするのが安全

## 5. 優先 2 の問い（時間が残った分）

- pa-01：Yes。agency_code は、TTS が登録と照らし、claim-svc が取扱代理店の証券だけを受け、document-svc が請求の agency_code と照らす。使い道の無い値ではない
- q-derived-value：Yes。tctx の項目は operation ごとに経路の表が決め、要らない項目は入れない。口座番号の代わりに payee_ref を使う。傷病は載せない
- q-variant-comparison：**No**。PH_AT・STAFF_AT の送信者制約の見送りは、mTLS で束縛する費用（SVID が 1 時間ごとに替わる）だけを比べていて、DPoP（BFF が持つ鍵。SVID と別）の候補を比べていない（指摘 F5）
- q-idp-diff-absorbed：Yes。内側は TTS の Txn-Token だけを受ける（iss は TTS だけ）。外の AT と assertion は入口より内側に届かない
- q-original-principal：Yes。作り直しの後も sub は元の利用者（社員）で、scope は TTS が絞る。仲介のサービスは自分の資格情報で書かない（H10・H18）
- q-step-up-by-rs：Yes。payment-svc と as-admin-api が決め、staff-console の画面は案内だけ（付録 B）
- q-long-running：Yes。Txn-Token を持ち越さず、作り直しと実行の時点で、社員の状態・役割・保留・承認の記録を確かめ直す。割り当ては op-source-change の気づきのとおり、確かめ直さない
- q-copies-outlive：Yes。写しは、監査ログ（sub の HMAC）、TTS の状態のキャッシュ（60 秒）、ブローカーと滞留のキューの PAY_MSG_CTX（期限が切れると作り直せない）、fraud-svc が読むアクセスのログ。補足：滞留のキューの保持期間は書いていない（中の PAY_MSG_CTX は使えないので軽い）
- q-audit-correlation：Yes。txn が PAY_MSG_CTX からの作り直しでも引き継がれ、承認と実行は payment_id でつながる。sub・act の HMAC は監査ログの基盤の 1 つの鍵で作るので、経路の途中で作り方が変わらない

## 6. 表

### (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | design.md 3.1（見送り「Back-Channel Logout・SSF/CAEP」の行）、9.1 の止める単位の表の「代理店の担当者」の行（660 秒）、付録 D の M_token_validation の 8.（代理店の IdP の行）、token_types.yaml の AGENCY_AT の lifetime_refs・revocation（exp_only の note）、SECURITY_EVENT_TOKEN の assumption、AGENCY_ASSERTION（max_lifetime 300・max_clock_skew 30・stored_at）。問い q-revocation-delivery | 代理店の IdP で担当者を止めたときの最悪を「AGENCY_AT 330＋Txn-Token 330＝660 秒」としているが、止める直前に出た AGENCY_ASSERTION（寿命 300＋ずれ 30）がまだ使える。t=0 に出た assertion を t≈330 で AT に替えると AT は ≈660 まで、そこで作った Txn-Token は ≈990 まで受け入れられる。最悪は約 990 秒で、設計が当てた REQ-02 の 900 秒を超える。「次の assertion が出ないことで止まる」という前提が誤っている。直し方の候補：assertion の寿命を縮める、AT の寿命を縮める、REQ-02 の対象が「代理店の契約」だけか（担当者単位の停止に数値があるか）を要求の持ち主に確かめる | Major | 前提の誤り | q-revocation-delivery・lifetime-by-situation |
| F2 | hops.yaml H22 の validates（「承認の要否は payment-svc が自分の記録で決める：同じ請求の支払いの合計…」）、design.md 3.1（見送り「高額の支払いの承認をトークンの authorization_details に載せない」の確かめ方）、付録 D の M_privacy_minimization の 4.。問い op-one-time・q-approval-from-as | 100 万円以上なら承認待ちにする合計の判定を、同じ請求の指示が並行して 2 件届いたときにも正しく行えるか（請求ごとに直列にする・ロックする）が書いていない。txn の違う 2 件の指示（例：60 万円ずつ）が同時に判定されると、どちらも相手を数えずに承認なしで通り、REQ-05 の上長の承認を避けられる。txn と claim_id での重複の拒否は txn が違うので効かない。3.1 の確かめ方にも並行の試験が無い | Major | 候補の漏れ | — |
| F3 | sheet.md 1. の「操作ごとの承認がある［当たらない］」。design.md 3.1（高額の支払いの承認の行）、hops.yaml H23、claims.yaml C-tctx（payment_id・amount、operation の payment.approve）、C-scope の payments:approve | 性質の表は authorization_details が無いことだけで「当たらない」としたが、この設計には 1 件の支払い（payment_id と金額）ごとの上長の承認がある（REQ-05）。この性質の問い（dc-05・q-approval-from-as）が抜け落ちていたので、足して答えた（どちらも Yes）。承認の ID の行が名前に approval を含まないので、#80 の読み方でも拾えない | Minor | 前提の誤り | — |
| F4 | design.md 6. UC4 の q-actor の行（「不要」）、catalog_answers.yaml の questions.q-actor の note、claims.yaml C-req-wl（does_not_answer: q-actor）、hops.yaml H22 | 判断の木の keep-sub-exchange では、非同期の処理を利用者の権限で続けるとき「sub＝利用者、act＝仲介するワーカー」とする。設計は payment-worker を act でなく req_wl と q-peer で表し、q-actor を「不要」としている。一方で、設計自身の C-req-wl は q-actor に答えないと宣言している。いまは payment-svc が operation ごとに req_wl を照らすので実害は小さい。ただ、「誰が社員の代わりに指示を動かしたか」に答える仕組みが、別の問い（どのワークロードが Txn-Token を求めたか）の値で代わっている。act を入れるか、6. に「req_wl で q-actor に答える」理由を書き、C-req-wl の宣言とそろえる | Minor | 目的と仕組みの不一致 | keep-sub-exchange・q-actor |
| F5 | design.md 3.1（見送り「PH_AT・STAFF_AT の送信者制約（DPoP・mTLS）」の行）、token_types.yaml issuance_profile.sender_constraint の rationale、DPOP_PROOF（却下）の rationale | 見送りの費用は「SVID が 1 時間ごとに替わるたびに直前の AT が使えなくなる」だけで、これは mTLS で束縛した場合の費用。BFF のサーバーが持つ DPoP の鍵（SVID とは別で、替わらない）で束縛する候補を比べていない。DPOP_PROOF の却下の理由も代理店の AT のことしか書いていない。開く攻撃（claim-portal・staff-console の SVID で接続できる部品から、盗まれた AT を使う）への代わりの守りは書いてあるので、軽い | Minor | 理由の不備 | q-variant-comparison |
| F6 | design.md 2. の範囲の図（矢印が無い：TTS→claim-svc、TTS→shirogane-as の状態の参照、payment-svc→社員の台帳）、hops.yaml（該当のホップが無い）、H22 の validates（「請求が保留でないことを引き直して」）、H23 の validates（「承認の上限額を社員の台帳に問い合わせ」）、claims.yaml C-sub の claim-svc の enforced_at（ワークロードの sub は payment-svc からの保留の読み取りだけ）。問い q-outside-catalog | TTS は作り直しのたびに claim-svc の請求の保留を引くが、その呼び出しが図にもホップにも無い。TTS がどの資格情報（Txn-Token か mTLS だけか）で呼び、claim-svc が何を確かめるかが決まっていない。claim-svc の受け入れの規則（ワークロードの sub は payment-svc からだけ）とも合わない。TTS から shirogane-as の状態の参照、payment-svc から社員の台帳の呼び出しも、同じく図に無い | Minor | 候補の漏れ | — |
| F7 | hops.yaml H20（kind: broker_connection、exchanger: tts、upstream: H17、max_lifetime 3600）、catalog_answers.yaml の shirogane-tts の trigger_list（PAY_MSG_CTX の発行）、design.md 4. の TTS が受ける要求の表。問い q-hop-lifetime（L16）・q-lint-workaround | PAY_MSG_CTX は、TTS が TXN_STAFF（寿命 300 秒）を subject_token にして出す交換（I22）。ところがホップの表では、交換をブローカーへの接続（H20）に含めて書いている。そのため、上流 300 秒から下流 3600 秒への延長を L16 が比べない。延長の理由は 5.1 と PAY_MSG_CTX の rationale にある（REQ-06、TTS への作り直しでしか使えない）ので、判断は通る。ただ、ホップの宣言の形が仕組みと合わず、機械の検査から外れている。TTS への交換のホップ（kind: exchange）を分けて書き、延長を例外として宣言する | Minor | 実装とのずれ | — |
| F8 | design.md 9.2 の「元のデータからの経路」の社員の台帳の行、9.1 の止める単位の表の「社員」の行、REQ-03。問い op-source-change | REQ-03 の 600 秒を「社員の台帳が変わってから」数えている。退職・休職・異動の発令から、人事部が入力して責任者が承認するまでの区間には、誰も時間を約束していない。要求の起点がどちらかを決め、台帳への反映までの目標を人事部と決める（12. に書く） | Minor | 候補の漏れ | — |
| F9 | hops.yaml H18 の validates（claim-svc は scope と operation だけを確かめる）、claims.yaml C-tctx の claim-svc の enforced_at（claim_id を本文・パスと照らす）。問い q-txn | 判断の木の txn-tctx では、Txn-Token を受けるホップの受け手のすべてが tctx の値を本文と照らしているかを確かめる。H18（assessment-svc から claim-svc への保留・割り当ての書き込み）のホップの確かめに、tctx の claim_id とパスの請求の照合が無い。台帳の行には書いてあるので、ホップの側の書き漏れ。ホップと台帳の一方だけを読む実装者は、照合を落としうる | Minor | 実装とのずれ | — |

重大度ごとの件数：Blocker 0、Major 2、Minor 7

### (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| q-value-vocabulary | Yes | agency_code・client_id・act.sub は、しろがねの登録が書く変わらない ID で照らし、発行者ごとに口を分けている |
| q-identifier-choice | Yes | 代理店の IdP の sub は C-sub の upstream_issuer で (iss, sub) から替え、行に identifier_properties と on_missing がある |
| ap-1-7 | Yes | agency_code の元を書けるのは代理店管理部だけ（phr と 2 人の操作）。act の照合先は IVR と人事部だけが書く |
| q-freshness-mitigation | Yes | agency_code は許容 900 に対して 390。client_id・act は寿命の間に変わらず、発行のたびに引き直す |
| q-single-aud-resource | Yes | AT は口ごとに 1 つの aud で、2 つ以上の値は拒む |
| q-no-passthrough | Yes | TTS が受ける要求を、要求者・subject_token・出す種別の組で決め、Txn-Token からの作り直しを拒む |
| q-step-up-path-coverage | Yes | 承認と管理の変更は、それぞれ 1 つの API だけが受け、受ける側が acr と auth_time を確かめる |
| ap-2-7 | Yes | 社員自身の TXN_STAFF では claim-svc が請求を受けず、代理受付のトークンには必ず act が入る |
| q-authorize-service-and-user | Yes | すべてのホップで、mTLS の相手を呼び出し元の一覧と照らしてから sub・scope を見る |
| q-agent-short-lived-no-rt | Yes | 代理の主体の社員にも payment-worker にも RT を出さない |
| q-outside-catalog | No | TTS→claim-svc の保留の問い合わせなどが図にもホップにも無く、資格情報と確かめ方が決まっていない（F6） |
| q-object-level-authz | Yes | 他人の claim_id は claim-svc が、持ち主・取扱代理店・割り当てを保存データと照らして 404 で止める |
| q-approval-from-as | Yes | 承認は payment-svc の記録で、payment_id と金額に結びつき、実行の時点で引き直す（並行の判定は F2） |
| dc-05 | Yes | tctx の内側は 8 項目すべて文字列で、正規化と比べ方が決まっている。Schema の不足は見送りに書いてある |
| q-operator-act | Yes | 管理の操作は社員の sub、代理受付は act で残り、なりすましの経路を作らない |
| q-revocation-delivery | No | 代理店の担当者の停止の最悪は、assertion の寿命を足すと約 990 秒で、設計の 660 秒と REQ-02 の 900 秒を超える（F1） |
| q-dependency-outage | Yes | TTS・状態・JWKS が止まれば拒み、fraud-svc・claim-svc が止まったときの倒し方も可用性の目標と並べて決めてある |
| op-proof-holder | Yes | どの箇所でも、トークンを持つのも鍵を持つのも代理店のサーバー。証明書の更新の扱いも決めてある |
| op-source-change | No | 発令から社員の台帳への反映までの区間に、時間の約束が無い（F8） |
| op-one-time | No | 承認が要るかどうかの合計の判定を、並行の 2 件の指示で直列にする規則が無い（F2） |
| pa-01 | Yes | agency_code は TTS・claim-svc・document-svc が、それぞれ決まった判断に使う |
| q-derived-value | Yes | tctx は operation ごとに要る項目だけを入れ、口座は参照 ID にし、傷病を載せない |
| q-variant-comparison | No | 送信者制約の見送りで、DPoP（BFF の鍵）の候補を比べていない（F5） |
| q-idp-diff-absorbed | Yes | 内側は TTS の Txn-Token だけを受け、外の AT と assertion は入口で止まる |
| q-original-principal | Yes | 作り直しの後も sub は元の利用者のままで、仲介のサービスは自分の資格情報で書かない |
| q-step-up-by-rs | Yes | 追加の認証は、操作を受ける payment-svc と as-admin-api が決める |
| q-long-running | Yes | 作り直しと実行の時点で、状態・役割・保留・承認を引き直す（割り当ては引き直さない） |
| q-copies-outlive | Yes | 監査ログは HMAC、キャッシュは 60 秒、期限切れの PAY_MSG_CTX は作り直せない |
| q-audit-correlation | Yes | txn を作り直しでも引き継ぎ、承認と実行は payment_id でつながり、HMAC の鍵は 1 つ |
| op-clock・op-key-custody・op-requirement-words | 該当なし | 時間内に辿っていない（「さらに」の開いた問い） |
