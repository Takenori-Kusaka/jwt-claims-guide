# レビュー報告：designs/target（しろがね損保　保険金の請求と支払いの内部処理）

- 抜き取りの種：12（sheet.md のとおり。抜き取った行：C-agency-code・C-client-id・C-act）
- 読んだもの：design.md（1.・2.・3.・6.・8.〜9.・12.・付録 B・D）、claims.yaml、token_types.yaml、hops.yaml、catalog_answers.yaml（lite_criteria・questions・outside_enumeration・U13/U29/U30）、ci-result.txt、教材（short_list・perspectives の該当問い・decision_tree・contrasts/act-txn-workload・kind_tell）
- 指摘の件数：Blocker 0、Major 4、Minor 4

## 段 0（受け付け）：CI の結果

- error 0、warn 9。warn の理由は 1. の表に行ごとにある
  - L1b（req_wl・tctx）：草案の名前で、spec_version と見直しの条件あり。通る
  - L16 H30（寿命 3600 秒が上流 H29 の 300 秒を超える）：PAY_MSG_CTX は TTS への作り直しの要求にしか使えず、TTS が作り直しのたびに状態を引き直す（H22）。`narrowing_exception` あり。通る（q-hop-lifetime：Yes）
  - L16 H4・H7・H15・H17・H23・H26（aud が上流に無い）：Txn-Token の aud は信頼ドメイン（草案 §9.2）。TTS が AT の aud と口の一致を確かめる（C-aud の tts の行）。通る
- lint を通すために宣言を曲げた跡：見つからない（upstream は外していない。H24 に upstream が無いのは、内部で始まる処理だから）

## 段 1：性質の表を、図と要求に照らして確かめた

| 性質 | sheet | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 合う（C-agency-code） |
| 個人情報 | 当たる | 合う（C-sub・C-act・C-tctx・C-email） |
| 発行者が複数 | 当たる | 合う（shirogane-as・shirogane-sso・TTS・代理店の IdP 2 社） |
| 交換・作り直し | 当たる | 合う（H4・H7・H15・H17・H23・H26 は reissue、H22・H24・H30 は exchange） |
| 委任 | 当たる | 合う（TXN_PROXY の act） |
| 操作ごとの承認 | 当たらない | **実際にはある**。REQ-05 の上長の承認は、payment_id と金額に結びつく 1 件ごとの承認（H23。payment-svc の承認の記録）。authorization_details を使わないので、読み取りから漏れた → 指摘 F8。足した問い：dc-05（問いごとの回答に入れた）。q-approval-from-as はもとから出ている |
| マルチテナント | 当たらない | 宣言（No）と理由を受け入れる。代理店ごとの絞り込みはテナントに近いが、テナントの問いを当てても Yes（claim-svc が取扱代理店と agency_code を保存データで照らす。agst_ の ID は (iss, sub) ごとで、代理店をまたいで混ざらない） |
| DB の層まで運ぶ | 当たらない | 合う（db_connection のホップは無い。9.1 の DB の層の表） |
| 認証の強さ・新しさ | 当たる | 合う（C-acr・C-auth-time） |
| 送信者制約を選んだ | 当たる | 合う（AGENCY_AT の mtls） |
| 送信者制約を見送った | 当たる | 合う（PH_AT・EMPLOYEE_AT は none） |
| 長時間・非同期 | 当たる | 合う（PAY_MSG_CTX・H20/H21・U13 が該当） |

## 段 2：6. の「要る」問いと、判断の木の節

| 問い（UC） | 判断の木の節 | 設計の仕組み | 比べた結果 |
| --- | --- | --- | --- |
| q-sub（UC1〜7） | keep-sub-exchange | TTS が sub を保って作り直す。UC3 は sub に契約者、UC6 はワークロード自身の ID | 合う。UC6 は利用者の sub を捏造していない |
| q-actor（UC3） | keep-sub-exchange | TXN_PROXY の act（社員。入れ子なし）。claim-svc・fraud-svc が受ける | 合う。最も外側の act だけで、入れ子は拒む（H15） |
| q-actor 不要（UC4） | keep-sub-exchange（ワーカーは act か） | payment-worker を act にせず、req_wl と mTLS の相手で記録。payment-svc は operation ごとに req_wl を照らす | 判断の木の例（仲介するワーカーを act に）と形は違うが、ワーカーは中身を変えられない運び手で、「誰が運んだか」は q-req-wl・q-peer で答え、権限は sub の社員について TTS が引き直す。不一致とまでは言えないと判断した（指摘にしない） |
| q-req-wl・q-txn（全 UC） | txn-tctx | txn・tctx・req_wl、専用の Txn-Token ヘッダー | 合う。Txn-Token を受けるホップの受け手はどれも tctx を本文・パス・保存データと照合（H4〜H26）。Authorization ヘッダーでは受けない。ただし txn を「1 件の指示」の重複の判定にも使っている点は F2 |
| q-peer（全 UC） | peer-mtls | SPIFFE の mTLS。受け手ごとの呼び出し元の一覧 | 合う。req_wl を直接の相手の照合に使わないと明記（C-req-wl の claim-svc の行） |
| q-authorized（UC1〜7） | rar-vs-custom | scope（TTS が経路の表と台帳で絞る）。承認は authorization_details に載せず payment-svc の記録（3.1 の見送り） | 合う。authorization_details を候補として比べた理由がある。承認の要否の数え方は F1 |
| q-resource | （M_token_validation 5.） | aud は口ごとに 1 つ、内側は信頼ドメイン | 合う |
| q-holder（UC2） | （送信者制約） | AGENCY_AT の cnf（x5t#S256） | 合う |
| q-user・q-agent | existing-claim-first | sub、client_id | 合う |
| 寿命（全体） | lifetime-by-situation | Txn-Token 300 秒＋発行のたびの状態確認、非同期は PAY_MSG_CTX から都度作り直し | 合う |

## 段 3：優先 1 の問いへの答え（1 行ずつ）

クレームの行（C-agency-code・C-client-id・C-act）：

- q-value-vocabulary：Yes。agency_code は AG＋6 桁の変わらない番号で、代理店の登録からだけ書く（assertion から取らない）。役割は社員の台帳の役割の ID で TTS が引く。act.sub は stf_ の ID
- q-identifier-choice：Yes。代理店の担当者のキーは (代理店の IdP の iss, sub) から shirogane-as が割り当てた agst_ で、C-sub の upstream_issuer・identifier_properties・on_missing にある。付け替えの限界は 3.1 に書いてある
- ap-1-7：Yes。agency_code の元（代理店の登録）は代理店管理部だけが as-admin-api で書き、変更は別の社員の承認と phr の認証つき。client_id はクライアントの登録（IT 基盤部の変更の手続き）。act は TTS が EMPLOYEE_AT・社員の台帳（人事部）・通話の記録（IVR だけが書く）から決める
- q-freshness-mitigation：Yes（抜き取った行）。agency_code は受け入れの上限 330 秒が許容 900 秒の内で、停止は TTS が発行のたびに引く。act の社員の役割を外すと 390 秒で止まる。ただし要求の「通話の間」が通話の終わりで切れない点は F3

経路：

- q-single-aud-resource：Yes。どの AT も aud は 1 つ（C-aud の max_items 1、resource で 1 つだけ求める）。Txn-Token は信頼ドメインだが、受け手は mTLS の相手で経路を限る
- q-no-passthrough：Yes。交換は TTS だけ。頼める相手は front-gw（H3・H6・H14）、assessment-svc（PAY_MSG_CTX だけ。H29）、payment-worker（H22）、payment-batch（H24）の許可リスト。scope は経路の表と台帳で絞り、広げない
- q-step-up-path-coverage：Yes。承認・取り消し・管理の変更は payment-svc・as-admin-api が acr・auth_time で確かめ、その API は front-gw からの TXN_STAFF だけを受ける。代理・非同期の経路はこれらの操作に届かない
- ap-2-7：Yes。代理受付の社員が契約者の請求を act なしで扱う経路は無い（claim-svc は stf_ の sub を assessment-svc の経路でしか受けない。契約者のトークンは社員に届かない）
- q-authorize-service-and-user：Yes。各ホップで受け手が mTLS の SPIFFE ID を一覧と照らし、利用者は Txn-Token の sub・scope と保存データで別に照らす
- q-agent-short-lived-no-rt：Yes。代理の主体（コールセンターの社員）には RT を出さない（EMPLOYEE_AT は refresh なし、TXN_PROXY は 300 秒で作り直しもしない）

全体：

- q-outside-catalog：No。fraud-svc が応えないときの「判定待ち」の後の判定のやり直しの経路（Txn-Token が切れた後に何の資格情報で呼ぶか）が、図・ホップ・カタログのどこにも無い → F4。滞留のキューからの確定し直しは F2
- q-object-level-authz：Yes。請求は claim-svc が持ち主・取扱代理店・割り当てを保存データで照らし（404）、書類は前段の claim-svc・assessment-svc（3.1 の見送りと日次の突き合わせ）、支払いは payment-svc が記録と照らす
- q-approval-from-as：Yes（結びつき）。承認は上長本人の TXN_STAFF（phr・300 秒）で payment-svc の記録に書き、payment_id と金額に結びつき、実行の時点で記録を引く。ただし承認が要るかの数え方に穴がある → F1
- q-operator-act：Yes。管理の操作は社員本人の sub で target_ref に向けて行い、利用者の代わりに動くのは代理受付だけで act を付ける。なりすましの経路を作らない（2.2）
- q-revocation-delivery：Yes。止める単位ごとに最悪の秒数がある（契約者 390、代理店 390、代理店の担当者 750、社員 390、鍵 810・690）。どれも要求の内。REQ-11 の時間枠の超過は F3
- q-dependency-outage：Yes（倒し方）。TTS・状態の参照・JWKS は拒む側、fraud-svc は判定待ち、claim-svc は次の夜に回す、と決まっている。ただし REQ-07 の可用性の積の部品が足りない → F6

## 段 4：開いた問い

### op-proof-holder

- 辿った範囲：C-cnf の enforced_at（front-gw・TTS）、AGENCY_AT の holder・sender_constraint、H5・H6、M_sender_constraint の 2.・4.、catalog の I26・I29
- 箇所ごとの「トークンを持つ者」と「鍵を持つ者」
  - front-gw（代理店の口）：持つ者＝代理店のサーバー、鍵＝代理店のサーバーの証明書の秘密鍵。TLS の拇印と cnf を照らすので一致する
  - TTS：持つ者＝front-gw（subject_token として受ける）、見る「鍵」＝front-gw だけが書く拇印のヘッダー。同名のヘッダーは入口で捨て、TTS は front-gw の SPIFFE ID からだけ読むので、front-gw の照合の二重の確かめとして成り立つ
  - shirogane-as（発行）：トークンの要求の mTLS の証明書の拇印を cnf に書く
- 証明書の更新：同じサブジェクトで出し直し、古い証明書に束縛した AGENCY_AT は最大 300 秒で使えなくなり、新しい証明書で取り直す（M_sender_constraint 4.）
- 気づいたこと：C-agency-code の `prior_art_search.not_used_because` は「代理店が証明書を替えてクライアントを登録し直すと client_id が変わる」と書くが、M_sender_constraint 4.・I26 では同じサブジェクトで出し直し、登録は証明書のサブジェクトを持つので、更新で client_id は変わらない → F7

### op-source-change

- 選んだ出来事：社員の異動でコールセンターの役割が外れる（と、退職）
- 辿った経路：人事部の担当者が人事の仕組みで入力 → 責任者の承認の時点で社員の台帳が変わる（9.2 の元のデータからの経路）→ TTS が 60 秒のキャッシュの後に引く → 発行済みの TXN_PROXY は最大 330 秒 → 390 秒で止まる（REQ-03 の 600 秒の内）。shirogane-sso のセッションも 60 秒で消える
- 誰も時間を約束していない区間：発効から台帳の更新まで（3.1 の見送りで、人事の規程 12 条と要求の持ち主の受け入れが書いてある）。12. で起点を要求の持ち主に確かめる予定
- ほかに見た元のデータ：代理店の登録（as-admin-api だけ・2 人の操作）、通話の記録（IVR だけ）、承認の上限額（承認のたびに問い合わせ）。証券の振込先は契約部が範囲の外の契約管理の仕組みで書き、payment-svc の payee_ref の照合はこの値に頼る。書き換えの手続き（承認の有無）は設計の範囲の外として書かれていない（指摘にはしないが、要求の持ち主に確かめる候補）
- 図に無い書き込みの経路：見つからない（shirogane-sso は管理の操作で役割を付けない、DB の直接の修正は 2 人の承認の手続き）

### op-one-time

- 辿った値：AGENCY_ASSERTION の jti、AUTH_CODE、nonce、PAY_MSG_CTX、支払いの指示（(txn, claim_id)）、支払いの実行（payment_id）
  - jti：一意の制約つきの 1 回の書き込みで確かめと記録を兼ね、記録先が応えなければ拒む。並行の 2 件・再送・障害のどれでも 2 回通らない
  - 実行：状態の更新と振込のファイルへの追加を 1 つの取引で行い、同じ payment_id を 2 回入れない
  - PAY_MSG_CTX の再配送：payment-worker は受け付けの後にだけ処理済みにし、payment-svc の (txn, claim_id) の一意の制約で 1 件になる。正しい 1 件も落とさない
- 気づいたこと
  - 再配送の間に PAY_MSG_CTX が期限を過ぎると、メッセージは滞留のキューに移り「査定担当者が確定し直す」。確定し直すと新しい txn になるので、前の指示が payment-svc に既に記録されていても (txn, claim_id) の一意の制約では重なりを止められない → F2
  - 承認が要るかの合計に、承認の要らない未実行の指示が入っていない → F1

## 段 5：優先 2（時間があれば）

問いごとの回答の表の後半に入れた。開いた問いの「さらに」（op-clock・op-key-custody・op-requirement-words）は、op-requirement-words だけを F3 の確かめのために辿った（言葉「代理受付」「通話の間」：本人確認済み・30 分以内・通話中／終話後・別の担当への転送の場合を挙げ、終話後を止める値が無いことを確かめた）。op-clock・op-key-custody は答えていない（代理店向けの CA・SPIFFE の CA の漏えい時に分数の目標が無いことだけ気づいた。REQ-10 はトークンの署名の鍵が対象なので指摘にしない）。

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | hops.yaml H22 の validates の 5 番目（承認の要否）、design.md 3.1 の見送り「高額の支払いの承認をトークンの authorization_details に載せない」の確かめ方、付録 D の M_privacy_minimization 4.、REQ-05 | H22 は承認の要否を「同じ請求の支払いの合計（実行済み・承認待ち・この指示）」で決めるが、承認の要らない「指示済みで未実行」の支払いが合計に入っていない。夜間の実行の前に同じ請求で 60 万円の指示を 2 回出すと、2 件目の合計は 60 万円で承認待ちにならず、合計 120 万円が承認なしで実行される（REQ-05 の迂回）。3.1 の確かめ方は「60 万円の指示 2 件で 2 件目が承認待ちになる」と書いており、2 か所が同じ仕組みについて食い違う。直し方：合計に「指示済み（承認不要・未実行）」を含める | Major | 実装とのずれ | q-approval-from-as（REQ-05） |
| F2 | hops.yaml H21・H22 の validates（(txn, claim_id) の一意の制約）、claims.yaml C-txn の enforced_at（payment-svc・payment-worker）、token_types.yaml PAY_MSG_CTX の lifetime_refs・long_running（滞留のキューに移し、査定担当者が確定し直す）、design.md 9.1 | 重複の判定の鍵が txn（1 つの呼び出しの連鎖の ID）で、答えているのは「同じメッセージが再び届いたか」。要るのは「この請求の査定の確定に対して指示が既にあるか」。payment-svc が指示を記録した後に応答が失われ、再配送の間に PAY_MSG_CTX（3600 秒）が切れると滞留のキューに移り、査定担当者が確定し直す。新しい txn で 2 件目の指示が通り、二重の支払いになる（承認の要らない額なら誰も止めない）。直し方：査定の確定の ID（または claim_id と確定の版）で一意にする、確定し直しの前に既存の指示を確かめる | Major | 目的と仕組みの不一致 | op-one-time、判断の木 txn-tctx（q-txn） |
| F3 | hops.yaml H14 の validates の 4 番目（代理受付）、token_types.yaml TXN_PROXY（max_lifetime 300・revocation）、design.md 2.1 の「電話の代理受付の社員」、3.1 の見送り「電話の代理受付を 1 件の操作ごとの本人確認にしない」、付録 D M_token_validation 6. の通話の記録、claims.yaml C-act（volatility never） | REQ-11 は「本人確認した通話の間（本人確認から 30 分）だけ」だが、TTS は本人確認から 1800 秒以内かと担当の社員しか見ず、通話が終わったかを見ない。5 分で電話を切っても、社員は残り 25 分、契約者の名で請求・照会を続けられる。さらに 1799 秒目に出た TXN_PROXY は 300＋30 秒使えるので、30 分の枠を最大 330 秒超える。直し方：通話の記録の終話の時刻を TTS が引く（キャッシュしない今の形で足せる）、TXN_PROXY の exp を本人確認から 1800 秒で打ち切る | Major | 候補の漏れ | op-requirement-words、q-freshness-mitigation（C-act） |
| F4 | hops.yaml H8 の note（fraud-svc が応えないとき「判定待ち」で受け付ける）、design.md 2. の図とトークンを運ばない呼び出しの表、catalog_answers.yaml outside_enumeration | 判定待ちの請求を後で fraud-svc に判定させる経路が、図・ホップ・カタログのどこにも無い。元の Txn-Token は 300 秒で切れ、fraud-svc は req_wl が front-gw の Txn-Token しか受けないので、やり直しは決めていない資格情報（claim-svc 自身の権限、トークンなしの口）で作られるおそれがある（障害時の再送の想定漏れ）。直し方：やり直しの経路（誰が、どのトークンか mTLS だけか、fraud-svc が何を確かめるか）をホップか 2. の表に足す | Major | 候補の漏れ | q-outside-catalog |
| F5 | hops.yaml H3 の validates の 5 番目（「rctx の req_ip は front-gw の接続の IP」）、claims.yaml C-rctx（decision 却下）、design.md 付録 D P5 2.（rctx は載せない）・M_authz_pdp 5. | ホップは TTS が rctx の req_ip を書くとするが、台帳と設計書は rctx を却下している。実装する人が、却下した rctx（読まない受け手にも届く IP）を Txn-Token に書くおそれがある。直し方：H3 の文を消す | Minor | 実装とのずれ | — |
| F6 | design.md 3.1 の重点「TTS・状態の参照・JWKS が応えないときは拒む」の可用性の積（99.91%）、12. の「可用性の目標」、REQ-07 | 請求の受付の経路の積に、claim-portal 自身と shirogane-as のトークンの端点（PH_AT は 10 分ごとに PH_RT で、AGENCY_AT は 5 分ごとに assertion で取り直す）が入っていない。入れると 99.9% を割りうるので、「REQ-07 に収まる」の理由が選択を支えていない。直し方：部品を足して積を出し直すか、トークンの端点の目標を書く | Minor | 理由の不備 | q-dependency-outage |
| F7 | claims.yaml C-agency-code の prior_art_search.not_used_because、design.md 付録 D M_sender_constraint 4.、catalog_answers.yaml I26（ワークロード） | client_id を使わない理由を「証明書を替えて登録し直すと client_id が変わる」とするが、設計は証明書を同じサブジェクトで出し直し、登録は証明書のサブジェクトを持つので、更新で client_id は変わらない。独自クレームを足す理由が自分の設計と食い違う（足す判断そのものは、代理店ごとの番号が要るので結論は変わらない見込み。理由を「1 つの代理店が複数のクライアントを持ちうる」などに直す） | Minor | 理由の不備 | pa-01、op-proof-holder |
| F8 | sheet.md 1. の「操作ごとの承認がある：当たらない」、design.md REQ-05・H23・3.1 の見送り（承認を authorization_details に載せない） | 設計には 1 件の支払い（payment_id と金額）ごとの上長の承認がある。authorization_details を使わず承認の記録で行うため、性質の読み取りが「当たらない」になった。この性質の問い（dc-05）をこのレビューで足して答えた。台帳か catalog_answers に、承認の記録の宣言（承認の ID・結びつく値）を書くと、次から読み取れる | Minor | 前提の誤り | — |

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| q-value-vocabulary | Yes | agency_code は登録の変わらない番号、役割は台帳の役割の ID、act は stf_ の ID で、別の発行者の文字列を同じ意味として通さない |
| q-identifier-choice | Yes | 代理店の担当者は (iss, sub) から割り当てた agst_ で、C-sub に upstream_issuer・identifier_properties・on_missing がある |
| ap-1-7 | Yes | agency_code の元は代理店管理部だけが 2 人の操作で書き、client_id は IT 基盤部の手続き、act は TTS が台帳と IVR の記録から決める |
| q-freshness-mitigation | Yes | 抜き取った 3 行は受け入れの上限が許容の内か never で、停止は TTS の毎回の確認で 390 秒（終話は F3） |
| q-single-aud-resource | Yes | どの AT も resource で 1 つの aud、2 つ以上は拒む |
| q-no-passthrough | Yes | 交換は TTS だけで、頼める相手を mTLS の許可リストで限り、scope は経路の表と台帳で絞る |
| q-step-up-path-coverage | Yes | 承認・管理の変更は受け手が acr・auth_time を確かめ、その API は front-gw の TXN_STAFF だけを受ける |
| ap-2-7 | Yes | 代理受付の社員が契約者の請求を act なしで扱える経路が無い（claim-svc は stf_ の sub を査定の経路でしか受けない） |
| q-authorize-service-and-user | Yes | 各ホップで mTLS の相手を一覧と照らし、利用者は sub・scope と保存データで別に照らす |
| q-agent-short-lived-no-rt | Yes | 代理の社員には RT を出さず、TXN_PROXY は 300 秒で作り直さない |
| q-outside-catalog | No | fraud-svc の判定待ちの後のやり直しの経路が無い（F4） |
| q-object-level-authz | Yes | 請求・書類・支払いのどれも、保存データの持ち主・取扱代理店・割り当て・記録で止まる |
| q-approval-from-as | Yes | 承認は上長本人の記録で payment_id と金額に結びつき、実行の時点で引く（要否の数え方は F1） |
| q-operator-act | Yes | 管理の操作は社員本人の sub、利用者の代わりの操作は act つきの TXN_PROXY だけ |
| q-revocation-delivery | Yes | 止める単位ごとに最悪の秒数（390・750・810・690）があり、要求の内（REQ-11 の枠の超過は F3） |
| q-dependency-outage | Yes | 依存先ごとに拒む・判定待ち・次の夜に回すが決まっている（可用性の積の不足は F6） |
| dc-05（性質の取り違えで足した） | Yes | tctx の 8 項目はすべて文字列で、amount は 10 進の文字列・exact で比べる（内側の型は schema でなく試験と共通部品で確かめる、3.1） |
| op-proof-holder（開いた問い） | 該当なし | 辿った。front-gw は持つ者と鍵が一致、TTS は front-gw だけが書く拇印で照らす。理由の食い違いを F7 に |
| op-source-change（開いた問い） | 該当なし | 辿った。役割の剥奪は 390 秒、発効から台帳までは 3.1 で受け入れ済み。振込先の書き換えの手続きは範囲の外 |
| op-one-time（開いた問い） | 該当なし | 辿った。jti・実行は 2 回通らないが、確定し直しで指示が二重になる（F2） |
| pa-01 | Yes | agency_code は TTS が登録と照らし、claim-svc が取扱代理店の証券に絞る（理由の食い違いは F7） |
| q-derived-value | Yes | 個人情報は不透明な ID と operation ごとに要る tctx の項目だけで、傷病・IP・全証券は載せない |
| q-variant-comparison | Yes | 送信者制約の見送りで mTLS と DPoP を比べ、開く攻撃（ログ・別の部品）と代わりの守り（口の mTLS の相手の制限）と確かめ方がある |
| q-idp-diff-absorbed | Yes | 内側は TTS のトークンだけで、代理店の IdP の sub は shirogane-as が agst_ に替える |
| q-original-principal | Yes | 作り直しの後も sub は元の利用者・社員で、payment-batch だけが利用者の文脈の無い自分の ID |
| q-step-up-by-rs | Yes | payment-svc・as-admin-api が決め、staff-console の画面は案内だけ |
| q-long-running | Yes | 利用者のトークンを持ち越さず、作り直しの時点で TTS が状態・役割・保留を引き直し、実行の時点で payment-svc が承認と保留を引く |
| q-copies-outlive | Yes | 写しは監査ログの HMAC と 60 秒の状態のキャッシュで、ブローカーには PAY_MSG_CTX だけ（期限後は作り直せない） |
| q-audit-correlation | Yes | txn を入口から実行まで引き継ぎ、sub・act は同じ鍵の HMAC、承認の記録は payment_id と txn を持つ |
| op-requirement-words（さらに） | 該当なし | 「代理受付」「通話の間」を辿り、終話後を止める値が無いことを F3 に |
| op-clock（さらに） | 該当なし | 時間切れで答えていない |
| op-key-custody（さらに） | 該当なし | 時間切れで答えていない（CA の漏えい時の分数の目標が無いことだけ気づいた） |
