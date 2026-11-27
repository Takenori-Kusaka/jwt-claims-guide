# レビューの記録：designs/target（あおば住まいサービス 修繕の手配）

- 対象：designs/target/design.md、claims.yaml、token_types.yaml、hops.yaml、catalog_answers.yaml、claim_request_repair_id.md・claim_request_approval_ref.md、schemas/
- 問いの 1 枚：sheet.md（行の抜き取りの種 12。抜き取った行：C-approval-ref・C-repair-id・C-authorization-details）
- 使った教材：short_list.md、perspectives.md（重大度の目安）、decision_tree.md、contrasts/act-txn-workload.md、kind_tell.md
- CI（ci-result.txt と設計書の 1.）：error 0、warn 2（L16 の hop H5・H8）、info 24。warn の 2 件には行ごとの理由がある（下の 0.）

## 0. 受け付け（lint の結果）

- error 0 を確かめた。設計書の 1. の生成の区間は ci-result.txt と一致する
- L16 warn（H5：authorization_details の vendor-order、H8：lock-code が上流の H4 に無い＝下流で広げる）：理由は「上流の REPAIR_DELEG_AT は承認の前に出すので承認の内容を載せられない。agent-sts は approval-svc の承認済みの記録からだけ作り、広がるのはその 1 件の分。受け手は approval-svc で条件つきで使用済みにする」。台帳の C-authorization-details の authoritative_writer（⑥ agent-sts、承認の記録から）と enforced_at（order-tool・lock-tool が approval-svc で消費）と一致し、広がる根拠が上流のトークンでなく別の権限の元（人の承認の記録）にあることが言えているので、**理由は通る**と判断した（指摘にしない）。答えを決める問いは `q-hop-narrowing`
- 宣言を曲げた跡（q-lint-workaround）：H5・H8 の upstream は H4 のまま、added_claims に出どころを書いており、上流を外す・名前を変える跡は見当たらない

## 1. 性質の表の確かめ（段 1）

図（2. の範囲の図）と要求（REQ-01〜13）に照らした。12 の性質の判定はすべて妥当で、「当たらない」の 2 つも実際に当たらない。

| 性質 | sheet.md | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | C-repair-id・C-approval-ref（名前空間 https://aoba-sumai.example/claims/）。妥当 |
| 個人情報 | 当たる | C-sub・C-name・C-repair-id・C-authorization-details が「個人情報」。妥当 |
| 発行者が複数 | 当たる | aoba-as・agent-sts（どちらも self_built）。妥当 |
| 交換・作り直し | 当たる | H3・H5〜H9・H11・H12 が exchange。妥当 |
| 委任 | 当たる | C-act・C-may-act、max_delegation_depth 2。妥当 |
| 操作ごとの承認 | 当たる | C-authorization-details（vendor-order・lock-code）、1 件の発注・1 回の解錠に結ぶ。妥当 |
| マルチテナント | 当たらない | 組織は 1 つ。物件の持ち主ごとにデータを分けない（lite_criteria、U02・I24 は対象外）。図にもテナントの境界が無い。妥当 |
| トークンを DB の層まで | 当たらない | 発注の台帳は order-tool・order-scheduler が自分の DB アカウントで接続（2. のデータ層の行、9.1 の DB の接続の層）。妥当 |
| 認証の強さ・新しさ | 当たる | C-acr・C-auth-time（REQ-07）。妥当 |
| 送信者制約を選んだ | 当たる | ツールのトークン 4 種と APPROVAL_AT が mtls。妥当 |
| 送信者制約を見送った | 当たる | CONSOLE_AT・CONSOLE_RT・REPAIR_DELEG_AT が none（3.1 に理由）。妥当 |
| 長時間・非同期 | 当たる | ORDER_TOOL_AT.long_running、U13 が該当（予約の発注、最大 24 時間後）。妥当 |

## 2. 6.（問い × 仕組み）と判断の木の照合（段 2）

6. で「要る」とした問いごとに、判断の木の節の「選ぶ仕組み」と比べた。**目的と仕組みの不一致は見つからなかった。**

| 問い | 判断の木の節 | 設計の仕組み | 照合 |
| --- | --- | --- | --- |
| q-sub（UC1〜3） | keep-sub-exchange | agent-sts が sub を subject_token から写す（要求で差し替えさせない）。重要な操作は aoba-pdp に sub で問い合わせる | 合う |
| q-sub（UC4 予約） | keep-sub-exchange（後で動く処理はワーカーが自分の ID で交換し直す） | 交換せず、order-scheduler が予約の記録の sub で aoba-pdp・修繕依頼の台帳・approval-svc を実行の時点で引き直す | 既定から外れるが 3. と 3.1 に理由（subject_token にする担当者のトークンが無い。AS が交換で確かめる項目を同じ出どころから確かめる）と、記録の改ざんの検出（変更の記録の表）が書いてあり、答える問い（誰の権限で・今も許されるか）は同じ。不一致ではない |
| q-actor | keep-sub-exchange の「確かめること」（最も外側の act） | 各ツールの enforced_at・H5〜H8・H11 の validates が最も外側の act.sub を mTLS の相手と照合し、内側の act は記録だけ（C-act の not_meaning にも明記） | 合う。台帳の行だけでなく受け手の照合の文も最も外側だけ |
| q-peer | peer-mtls | wl-ca の証明書の mTLS（end_to_end、入口で終端しない）。act・client_id で代えていない | 合う |
| q-via | （経由の属性・ネストした act） | agent-sts の交換の記録（元の jti と出した jti）と各ツールの監査ログ、UC2 は act の連鎖も | 合う。経路をログで残しており、act の連鎖だけで経路を表してはいない（contrasts m-10 に当たらない） |
| q-txn | txn-tctx（取引の内容を経路で固定）／existing-claim-first | C-repair-id（対象の照合と監査の相関）。取引の内容（金額・部屋）の固定は authorization_details。Txn-Token は「ツールの先に連鎖が無い」で却下 | 合う。q-txn を「修繕依頼という業務の単位」として答え、内容の固定は rar-vs-custom で別に答えている。prior_art_search で txn を比べている |
| q-user・q-agent | keep-sub-exchange・peer-mtls | sub、client_id と act（client_id と最も外側の act が同じことを確かめる） | 合う |
| q-authorized | rar-vs-custom・carry-or-query | scope（操作の種類）＋authorization_details（承認の内容。type は組織の URI）＋approval_ref（記録の参照、状態は approval-svc に問い合わせ）。ロールは載せず aoba-pdp | 合う。scope と authorization_details の役割分担は M_authz_pdp の 4. に書いてある |
| q-resource | （aud・resource） | aud は 1 つ、resource は 1 つでリソースの表で照合 | 合う |
| q-holder | （cnf） | cnf の x5t#S256。REPAIR_DELEG_AT は束縛せず、唯一の受け手 agent-sts が may_act の主体の mTLS だけを受ける | 合う。may_act だけで持ち主を表しているのではなく、mTLS のクライアント認証と組で効かせている |

## 3. 優先 1 の問いへの回答（段 3）

自分の言葉で 1 行ずつ答えた（一覧は末尾の表 (2)）。No は ap-1-7 の 1 つで、指摘 R-1・R-4 にした。Yes の問いでも、確かめる途中で見つけた食い違いは指摘にした（R-1）。

補足（Yes と答えた問いで確かめた要点）：

- dc-05：authorization_details のメンバーはすべて文字列（金額は 10 進の文字列 ^[1-9][0-9]{0,8}$、ID は正規表現、時刻は RFC 3339 の UTC）、NFC・trim・exact。生成のスキーマ（schemas/ORDER_TOOL_AT.consumer.schema.json）は items が object だけでメンバーの型を表さないが、3.1 の見送りの行に代わりの守り（aoba-jwt-guard の試験、付録 A の毎日の突き合わせ）がある
- q-freshness-mitigation：要求に数値がある（REQ-03 10 分、REQ-08 2 分・10 分、REQ-09 10 分、REQ-05 直ちに）。scope 390 秒 ≤ 600、在籍・ロール・担当 60 秒 ≤ 120、委任の欄 330 秒 ≤ 600、承認の取り下げ 0 秒（条件つきの更新）。対策を行うのは agent-sts・各ツール・approval-svc・order-scheduler と書いてある
- q-revocation-delivery：重要な操作は aoba-pdp で 60 秒、下書き・連絡は 390 秒、委任の停止 330 秒、ログアウトの後のエージェントは exp の連鎖（下流の exp ≤ subject_token の exp）で 330 秒、予約は実行の時点で 0。寿命 300 秒は 5.1 で 10 分から導いている
- q-dependency-outage：4. の表と 3.1 で、aoba-as・aoba-pdp・修繕依頼の台帳・approval-svc・署名の鍵のどれでも止める側に倒し、REQ-13（60 分まで電話の手配）と付録 A の 5 分の警報に合わせている。JWKS は 600 秒の後に拒否

## 4. 開いた問い（段 4）

### op-proof-holder

- 辿った範囲：C-cnf の enforced_at（order-tool・contact-tool・payment-tool・lock-tool・approval-svc）、目録の holder・sender_constraint、H5〜H8・H11・H12 の validates、付録 D の M_sender_constraint の 4.、3.1 の「wl-ca の証明書の失効」の見送りの行、2.2 の管理用の口
- 箇所ごとの「トークンを持つ者」と「鍵を持つ者」：ORDER/PAYMENT/LOCK_TOOL_AT は repair-agent と repair-agent、CONTACT_TOOL_AT は交換を求めた repair-agent か visit-subagent と同じ者（H11 は visit-subagent が自分で交換する）、APPROVAL_AT は repair-console と repair-console。REPAIR_DELEG_AT は束縛しないが、受け手の agent-sts が may_act の主体の mTLS だけを受ける。どの箇所も一致する
- 証明書の更新：aoba-agent-kit が証明書とトークンを組で持ち、古い証明書に束縛したトークンは古い接続で使い切る（最悪 300 秒）。cnf の食い違いは起きない
- 気づき：3.1 は「登録と許可リストは URI と拇印の組で持つ」「漏れた証明書は許可リストから外せば足りる」とし、2.2 は agent-sts のクライアントの登録を設定のリポジトリの PR と配備で変えるとする。一方、証明書は 24 時間で毎日更新され、拇印が毎日変わる。更新した拇印を登録・各受け手の許可リストに誰がいつ入れるのか（PR と配備では毎日の更新に追いつかない）、漏えいのときに外すまで何分かが書いていない → 指摘 R-3

### op-source-change

- 選んだ出来事：異動で修繕課から外れる（修繕担当のロールが外れる）と、担当の付け替え
- 辿った経路：人事部の担当者が人事システムで登録 → 人事部の 2 人目の承認で確定（REQ-08 の起点。登録から確定までは 3.1 で人事部の手順書の 2 時間と月 1 回の報告）→ aoba-pdp が sub → 社員番号（aoba-as の属性。hr-sync の証明書の API だけが書く）→ 人事の台帳の API を引く（60 秒キャッシュ）→ ロールを導く（手で付ける口は無い）→ 重要な操作のツール・approval-svc・agent-sts が呼び出しのたびに aoba-pdp に問い合わせる（最悪 60 秒）。hr-sync の 5 分の写しは経路に入らない。担当の付け替えは課長が repair-console の画面で行い、修繕依頼の台帳の担当の履歴に追記
- 時間を約束していない区間：登録から確定まで（3.1 で見送り、報告の仕組みあり）
- 気づき：図に無い書き込みの経路として、DB の管理者の直接の書き込みは approval-svc・発注の台帳・aoba-as の利用者の DB だけが 2.2・3.1 に挙がっている。発注の承認者の条件（REQ-05 の「担当になったこともない人」）と委任の可否を決める修繕依頼の台帳（担当・担当の履歴・委任の欄）と、ロールの元の人事の台帳については、直接の書き込みの経路も、履歴が追記だけであることの前提の出どころも書いていない（2. では「台帳そのものの中は別の設計書」とだけある） → 指摘 R-4

### op-one-time

- 辿った値：承認（approval_ref。P4 の 5.）、予約済みの承認（H14）、認可コード（LOGIN_CODE）、ログアウトトークンの jti（M_token_validation の 6.、150 秒）、業務の ID（発注 ID・承認 ID・下書きの ID）
- 並行の 2 件：approval-svc の原子的な条件つきの更新で片方だけ成功。部屋の累計は発注の台帳の部屋の行の排他の錠で直列化（3.1 に結合試験の方法あり）
- 通信が切れた後の再送：同じ発注 ID（解錠は同じ承認）には前の結果を返し、「下書き→確定」「予約→確定」は条件つきの更新なので 1 回だけ。lock-svc は承認 ID ごとにコードを 1 つだけ作る
- 記録先の障害：approval-svc が止まれば拒否（止める側）
- 正しい 1 回が失われないか：P4 の 5. と 3.1 の「重点」の行は、確定しないまま止めた発注について「上長が承認を取り下げて承認し直す」と書く。しかし REQ-05 は「使われる前なら取り下げられ」とし、approval-svc の取り下げも未使用の承認への条件つきの更新である。使用済みにした後で確定できなかった発注（同じ発注 ID で再試行できない場合。たとえば確定しなかった下書きは 7 日で消える）は、取り下げられない状態のまま残り、回復の手順が状態の規則と食い違う → 指摘 R-2

## 5. 優先 2 の問い（段 5）

時間内に 10 問すべてに答えた（表 (2)）。No は無い。気づいた点：

- q-audit-correlation：sub・repair_id のハッシュの鍵を 1 年ごとに替える（M_privacy_minimization の 8.）。替える時点が全サービスで同時でないと、日をまたぐ修繕依頼や予約（最大 24 時間）の 1 本の操作が、サービスごとに別の鍵の値でログに残る。「全サービスが共通部品で同じ鍵を使う」とあるので Yes にしたが、切り替えの時点を全サービスでそろえる手順は書き足すとよい（指摘にはしない）
- q-outside-catalog（優先 1 だが関連）：repair-agent が修繕依頼の本文（入居者の依頼の文）を読む経路は図にもホップにも無く、2. で「修繕依頼の本文をモデルに渡す扱いは別の設計書」と明示して範囲から外している。範囲の外と宣言してあるので指摘にはしないが、その経路でも担当の修繕依頼だけに限ることを、別の設計書の前提として書き添えるとよい

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| R-1 | claims.yaml の C-repair-id の `source_system`（「APPROVAL_AT では approval-svc の承認の記録」）、同じ行の `verification_method`（委任の交換の確かめだけ）。design.md の 10.（`#decisions` の render:data-sources の C-repair-id の行「データ源」）。これと食い違う側：C-repair-id の `authoritative_writer`（「承認の記録の値は写さない」）、hops.yaml の H12 の `added_claims`（system は repair-console の交換の要求と修繕依頼の台帳）、design.md の 4.（「修繕依頼 ID は承認の記録から写さない」）、claim_request_repair_id.md の問 11。問い：ap-1-7、q-approval-from-as | APPROVAL_AT の repair_id の出どころが 2 か所で食い違う。書き手・H12・4. は「画面で開いた修繕依頼を、sub が担当か上長かを確かめて載せ、承認の記録の値は写さない」とし、approval-svc はこの値を承認の記録の repair_id と比べる（「出どころの違う 2 つを比べ、画面で見ている修繕依頼と違う承認を操作させない」）。ところが source_system は「承認の記録」とし、verification_method も APPROVAL_AT の確かめを書いていない。source_system に従って実装すると、比べる 2 つが同じ出どころになり approval-svc の照合が常に通る（画面と違う承認の記録を操作させない守りが消える）。source_system を「repair-console の交換の要求（画面で開いた修繕依頼）と修繕依頼の台帳」に直し、verification_method に APPROVAL_AT の確かめ（sub が担当か、aoba-pdp で承認者になりうる上長か）を足す | Minor | 実装とのずれ | ap-1-7（値を書く出どころの宣言） |
| R-2 | design.md 付録 D の P4_ai_agent_delegation の 5.（`template:profiles/P4_ai_agent_delegation#human-approval`）の「消費の競合と再送」の行、3.1（`#priorities-deferrals`）の「操作ごとの承認を…1 回だけ使う」の重点の行。食い違う側：2. の REQ-05（「使われる前なら取り下げられ」）、claims.yaml の C-approval-ref の rationale・assumption（取り下げは条件つきの更新）、3.1 の「重複の実行を、業務の ID で防ぐ」の行（確定しなかった下書きは 7 日で消える）。問い：op-one-time | 「確定しないまま止めた発注は、上長が承認を取り下げて承認し直す」とあるが、その時点の承認は使用済み（order-tool が確定の前に使用済みにする）で、REQ-05 と approval-svc の状態の規則では使用済みの承認は取り下げられない。同じ発注 ID での再試行で回復できない場合（下書きが 7 日で消えた、担当が替わった等）に、使用済みのまま確定していない承認をどう閉じ、新しい承認の依頼をどう受けるかが状態の規則に無く、正しい 1 回が失われるか、規則に無い操作（使用済みの取り下げ）を実装に持ち込む。状態に「使用済み・未確定」からの閉じ方（例：発注の取り消しと承認の失効を approval-svc の条件つきの更新で行い、新しい承認は新しい発注 ID で依頼する）を書く | Minor | 実装とのずれ | op-one-time |
| R-3 | design.md 3.1（`#priorities-deferrals`）の「wl-ca の証明書の失効の確かめ」の見送りの行（「登録と許可リストは URI と拇印の組で持つ」「その証明書を許可リストから外せば足りる」）、2.2（`#system-privileges`）の「管理用の口」の行（agent-sts のクライアントの登録は設定のリポジトリの PR と配備で変える）、付録 D の M_sender_constraint の 4.（証明書は 24 時間、残り 8 時間で更新）、claims.yaml の C-cnf の `on_revoke`。問い：op-proof-holder、q-revocation-delivery | 証明書は毎日更新されて拇印が変わるのに、拇印を含む登録と各受け手（agent-sts・aoba-pdp・approval-svc・修繕依頼の台帳・下流の仕組み）の許可リストを、更新のたびに誰がどの経路で書き換えるかが無い。登録の変更は PR と配備（2 人の承認）とされ、毎日の更新と両立しない。拇印を外した照合にすると、3.1 の「漏れた証明書は許可リストから外せば足りる」が成り立たず、漏えいの後も証明書の期限（最悪 24 時間）まで使える。拇印の登録の更新の経路（例：wl-ca の発行の記録から配る仕組み）と、漏えいのときに外し終えるまでの分数を書く | Minor | 候補の漏れ | op-proof-holder |
| R-4 | design.md 2.2（`#system-privileges`）の「DB の管理」の行、3.1 の「approval-svc・発注の台帳・aoba-as の利用者の DB の管理者の直接の書き込み」の見送りの行、2. の範囲の表の「組織の網」の行（修繕依頼の台帳・人事の台帳の中は別の設計書）、9.2（`#freshness`）の「元のデータからの経路」。台帳：claims.yaml の C-repair-id の `source_system`・`enforced_at`（agent-sts・aoba-pdp）、C-sub の approval-svc の `enforced_at`（担当の履歴で承認者を決める）。問い：ap-1-7、op-source-change | 発注の承認者の条件（REQ-05：担当になったことがない人）は修繕依頼の台帳の担当の履歴で、委任の可否は同じ台帳の担当と委任の欄で、ロールは人事の台帳で決まる。これらの値を書ける者として、設計書は repair-console（課長・担当者のセッション）と人事部の 2 人の手順だけを数え、両台帳の DB の管理者・管理業務システムの既存の口からの書き込みを数えていない（DB の直接の書き込みの検出は approval-svc・発注の台帳・aoba-as だけ）。担当の履歴を消せれば、担当の付け替えを挟んだ自己承認（REQ-05 が止めたい場面）が通る。両台帳について、書ける者と、履歴が追記だけであることの出どころ（別の設計書の節）か、承認の記録と同じ変更の記録の突き合わせを、前提として書く | Minor | 候補の漏れ | ap-1-7 |

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| dc-05 | Yes | authorization_details のメンバーは金額を含めすべて文字列で正規表現・NFC・完全一致が決まり、スキーマが型を表さない点は 3.1 で共通部品の試験に回している |
| q-value-vocabulary | Yes | ロール・所属はトークンに載せず aoba-pdp が人事の台帳のコードから導き、scope・acr は閉じた語彙で、受け手ごとに iss を 1 つに固定するので別の発行者の同じ文字列を通さない |
| q-identifier-choice | Yes | 利用者のキーは aoba-as の sub（UUID、identifier_properties と on_missing あり）だけで、agent-sts は写すだけ。社員番号は aoba-pdp の中の対応でトークンに出ない |
| ap-1-7 | No | 抜き取った 3 行の書き手は agent-sts だけで自己申告を使わないが、元のデータ（修繕依頼の台帳の担当・担当の履歴、人事の台帳）を書ける者を数え切れておらず（R-4）、C-repair-id の出どころの宣言も食い違う（R-1） |
| q-freshness-mitigation | Yes | 9.2 と台帳で scope 390／600 秒、在籍・担当 60／120 秒、委任 330／600 秒、承認 0 秒と、要求の数値の内側に収まり、対策を行う受け手も書いてある |
| q-single-aud-resource | Yes | 全種別・全ホップの aud は 1 つで、agent-sts は resource を 1 つだけ受け、ツールは配列にほかの値があれば拒否する |
| q-no-passthrough | Yes | 交換は agent-sts だけが行い、委任の表（may_act）とクライアントごとのリソースの表で頼める相手と宛先を決め、scope は上流・宛先・ロールの積に絞る |
| q-step-up-path-coverage | Yes | 追加の認証が要るのは承認の操作だけで、その口は APPROVAL_AT（act なし・repair-console だけ）で受ける approval-svc の 1 つであり、代理・予約の経路から承認に届く道が無い |
| ap-2-7 | Yes | エージェントが持つ act の無いトークンは宛先が agent-sts だけの 1 段目の REPAIR_DELEG_AT だけで、交換で出るツールのトークンには必ず act が入り、APPROVAL_AT はエージェントのリソースの表に無い |
| q-authorize-service-and-user | Yes | ツール・approval-svc・aoba-pdp・下流は mTLS の相手の証明書を呼び出し元の許可リストと照合し、ツールは利用者の権限（aoba-pdp）とは別に最も外側の act と mTLS の相手を照合する |
| q-agent-short-lived-no-rt | Yes | agent-sts は RT を出さず（rt_strategy の例外 none）、エージェントのトークンは 300 秒か subject_token の残りの短いほう |
| q-outside-catalog | Yes | 管理用の口・DB の直接の書き込み・電話の手配・試験の口（U30）・旧経路（U29）・wl-ca の中間の CA の漏えい・結果不明の再送が outside_enumeration と 2.2・3.1 にあり、修繕依頼の本文の経路は範囲の外と宣言している |
| q-object-level-authz | Yes | M_authz_pdp の 3. で、修繕依頼（agent-sts）・発注（order-tool・payment-tool。404）・連絡の相手・部屋・承認のそれぞれを台帳と照合する受け手と応答が決まっている |
| q-approval-from-as | Yes | authorization_details と approval_ref は agent-sts が approval-svc の承認済みの記録からだけ作り、locations で宛先に結び、受け手が下書き・部屋と完全一致で比べて approval-svc で条件つきで 1 回だけ使う |
| q-operator-act | Yes | 代理ログインを作らず、上長・管理者は自分のログインで動き、order-scheduler は自分の証明書で動いて予約の act の連鎖と分けて記録する。DB の管理者の書き込みは変更の記録で検出する |
| q-revocation-delivery | Yes | 重要な操作 60 秒・下書きと連絡 390 秒・委任の停止 330 秒・予約は実行の時点で 0 と、止める単位ごとに数え、寿命 300 秒を REQ-08・09 の 10 分から導いている |
| q-dependency-outage | Yes | aoba-as・aoba-pdp・修繕依頼の台帳・approval-svc・署名の鍵・JWKS のどれが止まっても止める側に倒し、REQ-13 の 60 分の電話の手配と 5 分の警報に合わせている |
| pa-01 | Yes | 25 問の問 1 と enforced_at で、repair_id は対象の照合と担当・委任の確かめ、approval_ref は承認を使う鍵と操作してよい記録を決めると言え、表示用の値で認可していない |
| q-derived-value | Yes | 連絡先・住所・解錠コードは載せず参照の repair_id に代え、部屋と時間帯（authorization_details）は使う ORDER/LOCK の 2 種だけに載る |
| q-variant-comparison | Yes | CONSOLE_AT・CONSOLE_RT・REPAIR_DELEG_AT の送信者制約の見送りで、盗まれたときに開く口（mTLS のクライアント認証・may_act で閉じる）と束縛の費用を比べ、確かめ方も書いている |
| q-idp-diff-absorbed | Yes | ツール・approval-svc は agent-sts の iss だけを受け、aoba-as のトークンが作り直されずに内側の受け手へ届くホップが無い |
| q-original-principal | Yes | 交換の後も sub は担当者のまま、scope は上流と宛先とロールの積で、間のサービスの権限で下流を呼ばない（client credentials を持たない） |
| q-step-up-by-rs | Yes | 追加の認証を求めるかは操作を受ける approval-svc が acr・auth_time（自分の時計で 300 秒）で決め、401 insufficient_user_authentication を返す |
| q-long-running | Yes | 予約はトークンを持ち越さず、order-scheduler が実行の時点で在籍・ロール・担当・委任の欄・承認・行為者の登録・記録の改ざんを確かめ直す |
| q-copies-outlive | Yes | 写しは監査ログ（鍵つきのハッシュ）と予約の記録だけで、予約の記録は実行の時点で引き直され、判断のキャッシュは aoba-pdp の 60 秒だけ |
| q-audit-correlation | Yes | sub・repair_id は全サービス同じ鍵・同じ正規化のハッシュで、act の連鎖・approval_ref・業務の ID・jti で 1 本に結べる（鍵の年ごとの切り替えの時点をそろえる手順は書き足すとよい） |
| op-proof-holder | 該当なし（開いた問い） | 持つ者と鍵の持ち主はどの箇所も一致した。証明書の毎日の更新と拇印の登録の更新の経路が無い（R-3） |
| op-source-change | 該当なし（開いた問い） | 人事の台帳の確定から aoba-pdp を経て受け手の判断まで辿れた。修繕依頼の台帳・人事の台帳の直接の書き込みの経路が数えられていない（R-4） |
| op-one-time | 該当なし（開いた問い） | 並行・再送・記録先の障害では 2 回通らない。使用済み・未確定の承認の閉じ方が状態の規則と食い違う（R-2） |
