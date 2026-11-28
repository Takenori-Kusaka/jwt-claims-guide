# レビューの記録：designs/target（あおば住まいサービス 修繕の手配）

- 対象：designs/target/design.md、claims.yaml・token_types.yaml・hops.yaml・catalog_answers.yaml、claim_request_*.md、schemas/
- 使った 1 枚：sheet.md（行の抜き取りの種 **12**。抜き取った行は C-approval-ref・C-repair-id・C-authorization-details）
- 答えた範囲：優先 1 の 17 問・開いた問い 3 つ・優先 2 の 9 問・「さらに」の開いた問い 3 つ（全部に答えた）
- 専門家に回す点：委任の深さ 2（escalation の delegation-depth）は、書き手が 12. で認証基盤チームの責任者に回している。レビュアーは答えない

## 0. 受け付け（CI の結果）

- ci-result.txt と設計書の 1. は一致する：error 0、warn 2（L16 の hop H5・H8）、info 24
- warn 2 件には行ごとの理由がある（1. の表）。上流の REPAIR_DELEG_AT に無い authorization_details（vendor-order・lock-code）を足すのは、approval-svc の人の承認の記録という別の権限の元からだけで、1 件分だけ広がり、受け手が使用済みにして確かめる。理由は通る（`q-hop-narrowing`）。指摘にしない
- 検査を通すために宣言を曲げた跡（upstream の外し・名前の替え・数値を上限に合わせる）は見つからなかった。H5・H8 の upstream は正直に H4 を指している

## 1. 性質の表の確かめ（段 1）

図（2. の flowchart）と要求（REQ-01〜13）に照らして、12 の性質の判定をすべて確かめた。食い違いは無い。

- 組織独自のクレーム・個人情報・発行者 2 つ（aoba-as・agent-sts）・交換（H3 ほか）・委任（act・may_act）・操作ごとの承認（authorization_details）・認証の強さ（acr・auth_time）・送信者制約の選択（ツールのトークン 4 種と APPROVAL_AT が mtls）と見送り（CONSOLE_AT・CONSOLE_RT・REPAIR_DELEG_AT が none）・長時間の処理（予約の発注）：どれも当たる
- マルチテナント：組織は 1 つで、テナントの値も物件の持ち主ごとの分割も無い。当たらないで正しい
- DB の層まで運ぶ：order-tool・order-scheduler は自分の DB アカウントで接続し、トークンで接続しない。当たらないで正しい

## 2. 6.（問い × 仕組み）と判断の木の照合（段 2）

UC1〜UC4 で「要る」とした問いごとに、判断の木の節と比べた。目的と仕組みの不一致は見つからなかった。

| 問い | 判断の木の節 | 設計の仕組み | 判定 |
| --- | --- | --- | --- |
| q-sub | keep-sub-exchange | agent-sts が subject_token の sub を写して交換。UC4 は予約の記録の sub を order-scheduler が実行時に aoba-pdp で確かめ直す | 合う。UC4 で交換し直さないことは 3. に既定からの逸脱として書き、AS が交換で確かめる項目を同じ出どころから引き直す理由がある |
| q-actor | keep-sub-exchange（最も外側の act） | ツールは最も外側の act.sub を mTLS の相手と照合し、操作ごとの行為者の許可リストに当てる。内側の act は記録だけ（C-act・H5〜H8・H11 の validates） | 合う。入れ子の act を許可に使う箇所は無い |
| q-peer | peer-mtls | wl-ca の証明書の mTLS（URI の SAN） | 合う |
| q-txn | txn-tctx | Txn-Token は却下し、C-repair-id で修繕依頼をまたぐ相関と対象の照合をする | 合う。修繕依頼は日をまたいで多くの呼び出しをまたぐので txn の意味と違う、ツールの先にトークンの連鎖が無い、という却下の理由がある（C-txn・TXN_TOKEN・C-repair-id の prior_art_search） |
| q-authorized | rar-vs-custom | scope（操作の種類）＋authorization_details（承認した 1 件の内容。locations で宛先を固定）＋approval_ref | 合う。scope と authorization_details を併用するが、何を決めるかは 6. と台帳に分けて書いてある |
| q-resource | （aud） | aud は 1 つ。resource（RFC 8707）を 1 つだけ受ける | 合う |
| q-holder | （cnf） | cnf の x5t#S256。REPAIR_DELEG_AT は may_act と mTLS の相手で代える（3.1 の見送り） | 合う |
| q-via・q-user・q-agent | — | agent-sts の交換の記録（元の jti と出した jti）・sub・client_id と act | 合う。act の連鎖を経路の証跡にしないと明記 |

## 3. 優先 1 の問い（段 3）と、開いた問い（段 4）

回答の 1 行は末尾の表 (2)。No にした問いは q-outside-catalog と q-operator-act の 2 つ（F1〜F3）。

### 開いた問いを辿った範囲と気づき

**op-proof-holder**（辿った範囲：C-cnf の enforced_at、目録の holder・sender_constraint、付録 D の M_sender_constraint の 4.、C-may-act）

| 確かめる箇所 | トークンを持つ者 | 鍵（証明書）を持つ者 | 一致 |
| --- | --- | --- | --- |
| order-tool・payment-tool・lock-tool | repair-agent | 交換を求めた repair-agent の証明書（cnf） | 一致 |
| contact-tool | repair-agent か visit-subagent | 交換を求めた側の証明書（H6・H11） | 一致 |
| approval-svc | repair-console | 交換を求めた repair-console の証明書 | 一致 |
| agent-sts（REPAIR_DELEG_AT） | repair-agent・visit-subagent | 束縛なし。may_act.sub の URI と mTLS の相手の URI で代える | 鍵でなく URI で一致（3.1 で見送り。中間の CA の鍵の漏えいで開くことも 3.1 に書いてある） |

- 証明書の更新（24 時間、残り 8 時間で更新）では、aoba-agent-kit が証明書とトークンを組で持ち、古い組は古い接続で使い切る。ツールのトークンは 300 秒なので食い違いは起きない
- 気づき（指摘にしない）：組で持つ部品はエージェント側の aoba-agent-kit と書いてあるが、APPROVAL_AT を持つ repair-console（BFF）の証明書の更新の扱いは明記が無い。APPROVAL_AT は 120 秒で 1 回の操作ごとに交換するので害は小さい

**op-source-change**（出来事：異動で修繕担当のロールが外れる。辿った範囲：9.2 の「元のデータからの経路」、C-sub.source_system、付録 D の M_authz_pdp の 5.、3.1 の人事の台帳の行）

人事部の担当者が登録 → 人事部の 2 人目が承認して確定（REQ-08 の起点）→ aoba-pdp が確定した値を人事の台帳の API で読む（60 秒キャッシュ）→ 重要な操作のツール・approval-svc は呼び出しごと、agent-sts は交換ごとに aoba-pdp に問い合わせる → 重要な操作は最悪 60 秒、下書き・連絡は 390 秒。

- 誰も時間を約束していない区間は「登録から確定まで」だけで、3.1 で人事部の手順（当日 2 時間）と月 1 回の報告に回している。hr-sync（5 分）は判断の経路に入らない
- ロールを手で付ける口は aoba-pdp に無く、社員番号の属性は hr-sync の証明書の API だけが書け、DB の管理者の直接の書き込みは変更の記録の表で止める。図に無い書き込みの経路は見つからなかった

**op-one-time**（辿った範囲：付録 D の P4 の 5.、M_token_validation の 6.、C-approval-ref の enforced_at、3.1 の「重複の実行を業務の ID で防ぐ」行）

| 1 回だけの値 | 並行の 2 件 | 通信が切れた後の再送 | 記録先の障害 |
| --- | --- | --- | --- |
| 発注の承認 | approval-svc の原子的な条件つきの更新で片方だけ | 同じ発注 ID には前の結果を返す。確定は「下書き→確定」の条件つきの更新 | approval-svc が応答しなければ拒否 |
| 解錠の承認とコード | 条件つきの更新。lock-svc は承認 ID ごとに 1 つ | 同じ承認・同じ送信の回で送り直し、通知の基盤は（承認 ID・回）で重複を捨てる。送り直しは回を条件つきで上げてから（3 回まで） | 拒否 |
| 予約の承認 | 予約済み→使用済みの条件つきの更新（H14） | 同じ発注 ID で次の回に再試行 | 実行しない |
| ログアウトトークンの jti | 150 秒覚える | 同上 | — |
| 連絡の送信 | 「下書き→送信済み」の条件つきの更新 | **通知の基盤への送信と状態の更新の順序、通知の基盤の重複を避ける鍵が書いていない**（F4） | 書いていない |

**（さらに）op-clock**：exp・iat は NTP でずれ 30 秒、auth_time は aoba-as の時計と approval-svc の時計（ずれを足さない）、承認の期限は approval-svc の時計だけ。気づき：not_before・not_after を最後に当てるのはスマートロックの機器の時計で、M_token_validation の 6. の時計の一覧に無い（F5）。

**（さらに）op-key-custody**：aoba-as（HSM、90 日、漏えい時 15 分）・agent-sts（同じ鍵管理の別の鍵、30 日、15 分）・wl-ca の中間の CA（60 分で差し替え。開く口を 3.1 に列挙）を確かめた。受け手が古い鍵を使い続ける時間は JWKS のキャッシュの 600 秒で、取り直せなければ拒否。指摘なし。

**（さらに）op-requirement-words**：「担当者」（正社員・契約・派遣・休職・退職の手続き中）と「上長」（課長以上・職務代行）は 2.1 で区分されている。気づき：(a) 要求に無い「当番」が、設計では手作業の発注の口を開く停止の宣言をする主体として出てくるのに、2.1・2.2 に無い（F1）。(b) REQ-05 の「依頼の担当者」は取り下げられるが、付け替えで担当を外れた依頼者には agent-sts が APPROVAL_AT を出さない（F6）。

## 4. 結論

Blocker は無い。委任・交換・承認・剥奪の中心の仕組みは要求の数値と合っていて、6. と判断の木の不一致も無い。指摘は、図と主体の一覧に載っていない運用の口と通知の経路、1 回だけの送信の細部、要求の言葉の区分のずれで、Major 1 件・Minor 5 件。

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | design.md 3.1 の「発注の台帳の書き込みの口を、この設計の部品だけに閉じること」の行（停止の宣言と解除を「当番が repair-console の当番の画面で行い」）、2.1 `#principals`、2.2 `#system-privileges`、2. の範囲の図 | 停止の宣言は、課長が手作業の発注を発注の台帳に書ける期間（宣言の間と解除から 24 時間）を開く門で、承認の前の確かめを通らない書き込みを許す。それなのに、宣言できる主体（「当番」）が 2.1 の主体の一覧・2.2 のシステムの権限・図のどこにも無い。repair-console がその人をどう認証し、どのロールで許すか（aoba-pdp で何を引くか）、追加の認証、監査ログに残る sub が書いていない。宣言できる人の範囲が決まっていないので、課長 1 人で門を開けて手作業の発注を登録できる余地が残る | Major | 候補の漏れ | q-operator-act、q-outside-catalog、ap-1-7 |
| F2 | design.md 3.1 の「頼る先が止まった間の解錠コードの取り消しを、通常の経路で行うこと」の行（「復旧の後、当番は approval-svc の記録を「取り消し」にそろえる」）、付録 D の M_authz_pdp の 5.（approval-svc の口の一覧） | approval-svc の口の一覧（依頼・使用済み・予約済み・参照・使用済みの確かめ・APPROVAL_AT）に、当番が記録をそろえる口が無い。DB の直接の書き込みでそろえるなら、3.1 の DB の管理者の行の規則で「要確認」になり、毎日の突き合わせが部長・監査の担当に知らせることになる。どの口で、誰の権限で書き、監査でどう見分けるかが決まっていない | Minor | 候補の漏れ | q-operator-act |
| F3 | design.md 3.1 の「発行した解錠コードを…自動では止めないこと」の行（approval-svc が 30 分ごとに発行中のコードの一覧を通知の基盤で上長に送る）、2. の範囲の図（approval-svc → 通知の基盤の線が無い）、付録 D の M_privacy_minimization の 5.・7.、2.2 の予約の実行（「予約を取り消して担当者に知らせる」） | 剥奪の見送りを支える代わりの守り（30 分ごとの一覧）が、図の経路にも、通知の基盤の呼び出し元にも無い。一覧には修繕依頼 ID・部屋の ID・not_after が載り、設計自身が「部屋と時間帯は入居者と在宅の時間が分かる個人情報」とした組み合わせ（C-authorization-details の note、M_privacy_minimization の 1.）なのに、送る手段（SMS の配信事業者を通るか）と残す期間が書いていない。order-scheduler が担当者に知らせる経路も図に無い | Minor | 候補の漏れ | q-outside-catalog、q-derived-value |
| F4 | design.md 3.1 の「重複の実行を、業務の ID で防ぐ」の行（連絡は「下書き→送信済み」）、CONTACT_TOOL_AT の purpose、付録 D の P4 の 5. | 解錠のコードの送信では、通知の基盤が（承認 ID・送信の回）で重複を捨て、結果が分からなければ同じ回で送り直すと決めている。連絡では、通知の基盤への送信と「下書き→送信済み」の更新の順序も、通知の基盤が重複を避ける鍵（下書きの ID）も書いていない。結果が分からない応答の後に、入居者に 2 回送るか、送ったのに未送信のまま残すかが決まらない | Minor | 候補の漏れ | op-one-time |
| F5 | design.md 付録 D の M_token_validation の 6.（時刻を比べるほかの箇所）、12. の「スマートロックの機器の時間帯」の行、C-authorization-details（not_before・not_after） | 解錠の時間帯を最後に当てるのはスマートロックの機器の時計なのに、6. の時計の一覧には approval-svc・order-scheduler・lock-tool の時計しか無い。12. が確かめるのは「機器が時間帯の外のコードを拒否するか」だけで、機器の時計の合わせ方と、ずれたときに通すのか止めるのか（4 時間の窓が前後にずれる）が決まっていない | Minor | 候補の漏れ | op-clock |
| F6 | REQ-05（「承認した人・依頼の担当者・同じ課の上長が取り下げられ」）、C-approval-ref の approval-svc の enforced_at、design.md 4. の agent-sts の要求の一覧（subject_token が CONSOLE_AT の行）、hops.yaml H2 の validates の最後の項目 | approval-svc は「依頼の担当者」に取り下げを許すが、agent-sts は APPROVAL_AT を「今の担当か同じ課の上長」にしか出さない。担当の付け替えで外れた依頼者は、要求が認める取り下げをできない。付け替えの後は依頼者のトークンで確定できないので実害は小さいが、要求の言葉の区分と 2 か所の条件が食い違っている。どちらに合わせるか（要求を「今の担当者」に直すか、agent-sts の条件に依頼者を足すか）を決める | Minor | 実装とのずれ | op-requirement-words、q-approval-from-as |

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| dc-05 | Yes | authorization_details のメンバーはすべて文字列で、書式（金額は 10 進の文字列、時刻は 1 つの書式）・NFC・完全一致が台帳と P4 の 5. で決まっている。スキーマが型を表さない点は共通の部品の試験に回している（3.1） |
| q-value-vocabulary | Yes | ロール・所属はトークンに載せず、aoba-pdp が人事の台帳のコードから導く。scope・acr・type は語彙を固定し、acr は aoba-as の値を写すだけ |
| q-identifier-choice | Yes | 利用者のキーは aoba-as の UUID の sub だけで、agent-sts は写すだけ。sub・repair_id・approval_ref に identifier_properties と on_missing がある |
| ap-1-7 | Yes | 抜き取った 3 行の書き手は agent-sts だけで、元の記録（修繕依頼の台帳・approval-svc・協力会社の台帳）の書き手も 3.1 で限っている（停止の宣言の書き手は F1） |
| q-freshness-mitigation | Yes | scope は 390 秒 ≤ 600 秒、在籍・ロール・担当は 60 秒 ≤ 120 秒、承認は都度の条件つきの更新で 0 秒。要求に数値がある |
| q-single-aud-resource | Yes | どの種別もホップも aud は 1 つで、受け手は配列のほかの値も拒否する |
| q-no-passthrough | Yes | 委任の表・クライアントごとのリソースの表・may_act・承認の記録からだけ作る authorization_details が規則として決まっている（P4 の 4.・4. の表） |
| q-step-up-path-coverage | Yes | 承認と事後の確認は APPROVAL_AT を受ける approval-svc の口だけで、エージェント・予約の経路は承認の操作をできない |
| ap-2-7 | Yes | act の無いトークンは 1 段目の REPAIR_DELEG_AT だけで、宛先は agent-sts だけ。ツール・approval-svc は受けず、repair-agent のリソースの表に approval-svc は無い |
| q-authorize-service-and-user | Yes | ツール・approval-svc・aoba-pdp・下流は mTLS の相手を証明書の URI の許可リストで確かめ、利用者の権限とは別に判断する |
| q-agent-short-lived-no-rt | Yes | agent-sts は RT を出さず、エージェントの種別は 300 秒で手順ごとに交換し直す |
| q-outside-catalog | No | 停止の宣言の口（F1）と、approval-svc から通知の基盤への一覧の経路（F3）が図と outside_enumeration に無い |
| q-object-level-authz | Yes | ツールは対象（下書き・連絡の相手・支払いの発注・部屋）を台帳で repair_id と照合して 404・403 で止め、approval-svc は承認の記録の修繕依頼を照合する（M_authz_pdp の 3.） |
| q-approval-from-as | Yes | agent-sts は approval-svc の承認済みの記録からだけ作り、locations で宛先を固定し、受け手が条件つきの更新で 1 回だけ使う（取り下げの主体のずれは F6） |
| q-operator-act | No | 上長・DB の管理者・lock-svc の管理者は自分の ID で記録に残るが、停止の宣言をする「当番」と、approval-svc の記録をそろえる口の主体と記録が決まっていない（F1・F2） |
| q-revocation-delivery | Yes | 重要な操作は剥奪から最悪 60 秒、下書き・連絡は 390 秒、委任の停止・ログアウトは 330 秒で、寿命とキャッシュの数字が REQ-08・09・03 から導かれている（5.1） |
| q-dependency-outage | Yes | aoba-as・aoba-pdp・台帳・approval-svc・JWKS の停止はどれも止める側に倒し、REQ-13 の 60 分の電話の手配と、停止中の解錠の取り消しの手順がある |
| op-proof-holder | 該当なし | 開いた問い。辿った範囲と気づきは 3. に書いた。指摘なし |
| op-source-change | 該当なし | 開いた問い。異動を IdP の手前から辿れた。指摘なし |
| op-one-time | 該当なし | 開いた問い。承認・コード・予約は辿れたが、連絡の送信の重複の鍵が無い（F4） |
| pa-01 | Yes | 25 問の問 1 に、repair_id・approval_ref の受け手ごとの使い道が書いてあり、表示用の値での認可は無い（name は表示だけ） |
| q-derived-value | Yes | トークンの個人情報（sub・repair_id・approval_ref・authorization_details）は読む受け手のトークンにだけ載り、連絡先・住所は参照の ID に代えた（トークンの外の一覧は F3） |
| q-variant-comparison | Yes | CONSOLE_AT・CONSOLE_RT・REPAIR_DELEG_AT の送信者制約の見送りは、盗まれたときの攻撃と代わりの守り（mTLS のクライアント認証・may_act）と確かめ方を比べている |
| q-idp-diff-absorbed | Yes | ツール・approval-svc は agent-sts のトークンだけを受け、aoba-as のトークンが作り直されずに内側に届くホップは無い |
| q-original-principal | Yes | 交換の後も sub は担当者のままで、scope は上流と宛先とロールの積に絞る |
| q-step-up-by-rs | Yes | approval-svc が acr・auth_time を見て 401 insufficient_user_authentication を返して決める |
| q-long-running | Yes | 予約はトークンを持ち越さず、order-scheduler が実行の時点で在籍・ロール・担当・委任の世代・承認を引き直す |
| q-copies-outlive | Yes | 写しは監査ログのハッシュと予約の記録で、予約の記録は実行の時点で確かめ直し、DB の書き換えは変更の記録で検出する |
| q-audit-correlation | Yes | sub・repair_id・approval_ref を全サービスで同じ鍵・同じ正規化のハッシュで残し、act の連鎖と jti で 1 本につなぐ |
| op-clock | 該当なし | 開いた問い（さらに）。機器の時計が一覧に無い（F5） |
| op-key-custody | 該当なし | 開いた問い（さらに）。3 つの鍵の持ち主と漏えい時の手順・分数を確かめた。指摘なし |
| op-requirement-words | 該当なし | 開いた問い（さらに）。「当番」が要求に無く設計にある（F1）、「依頼の担当者」の取り下げがずれる（F6） |
