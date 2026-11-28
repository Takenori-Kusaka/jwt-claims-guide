# レビュー報告：designs/target（あおば住まいサービス 修繕の手配）

- 対象：designs/target/design.md と claims.yaml・token_types.yaml・hops.yaml・catalog_answers.yaml・claim_request_*.md・schemas/
- 問いの 1 枚：sheet.md（行の抜き取りの種 12。抜き取った行：C-approval-ref・C-repair-id・C-authorization-details）
- CI：ci-result.txt（error 0、warn 2、info 24。OK）。設計書 1. の転記と一致

## 段 1：性質の表の確かめ（12.・2.・6. と図・要求に照らして）

| 性質 | sheet.md | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 合う。C-repair-id・C-approval-ref（名前空間 https://aoba-sumai.example/claims/） |
| 個人情報を載せる | 当たる | 合う。C-sub（個人情報）、ほかに C-repair-id・C-approval-ref・C-authorization-details も pii_category が個人情報 |
| 発行者が複数 | 当たる | 合う。aoba-as と agent-sts（どちらも self_built。iss のホストも 2 種類） |
| 交換・作り直し | 当たる | 合う。H3・H5〜H9・H11・H12 が exchange |
| 委任がある | 当たる | 合う。act・may_act、max_delegation_depth 2（REQ-03・REQ-04） |
| 操作ごとの承認 | 当たる | 合う。authorization_details（vendor-order・lock-code）と approval_ref（REQ-05・REQ-06）。時間枠の承認ではない |
| マルチテナント | 当たらない | 合う。組織は 1 つ、テナントの値なし（lite_criteria.multitenant false、U02・I24 も対象外）。図・要求にもテナントは無い |
| DB の層まで運ぶ | 当たらない | 合う。db_connection のホップなし。ツール・order-scheduler は自分の DB アカウントで接続（2. の表のデータ層の行、9.1 の DB・ブローカーの接続の層） |
| 認証の強さ・新しさ | 当たる | 合う。acr・auth_time（REQ-07）。amr は却下 |
| 送信者制約を選んだ | 当たる | 合う。ツールのトークン 4 種と APPROVAL_AT が mtls |
| 送信者制約を見送った | 当たる | 合う。CONSOLE_AT・CONSOLE_RT・REPAIR_DELEG_AT が none（3.1 に理由） |
| 長時間・非同期 | 当たる | 合う。ORDER_TOOL_AT.long_running、U13 該当、H13・H14 |

「当たらない」とされた性質が実際にある例は見つからなかった。12. は確かめていない事実だけで、見送りは 3.1 に分けてある（12. の「専門家に回す点」で委任の深さ 2 を escalation に回している）。

## 段 2：6.（問い × 仕組み）と判断の木の照合

| UC・問い | 設計の仕組み | 判断の木の節 | 結果 |
| --- | --- | --- | --- |
| UC1〜3 q-sub | C-sub（agent-sts は subject_token から写すだけ） | keep-sub-exchange | 合う。交換で sub を保ち、act を足す |
| UC1・UC2 q-actor | C-act の最も外側の act.sub を mTLS の相手と許可リストに照合。内側の act は記録だけ | keep-sub-exchange（最も外側の act か） | 合う。C-act の enforced_at・H5〜H8・H11 の validates・付録 D の P4 の 7. まで、許可に使うのは最も外側だけ |
| UC3 q-actor | client_id が repair-console で act が無いこと | keep-sub-exchange | 合う（承認はエージェントの経路から届かない） |
| UC4 q-sub・q-actor | 予約の記録の sub の写しと order-scheduler の証明書。交換し直さない | keep-sub-exchange（非同期もワーカーが交換し直す） | 既定から外れているが、3. と 3.1 に明示し、AS が交換で見る項目（在籍・ロール・担当・委任の世代・行為者の登録・承認）を同じ出どころから実行の時点で引き直す。記録の改ざんは DB アカウントの分離と変更の記録の表で止める。sub を捏造しない。不一致とはしない |
| q-peer | wl-ca の証明書の mTLS（URI の SAN） | peer-mtls | 合う。トークンのクレームで代えていない。end_to_end で終端なし |
| q-txn | C-repair-id（Txn-Token は却下） | txn-tctx | 合う。ここで要るのは「どの修繕依頼か」の相関で、取引の内容の固定は authorization_details が受け持つ。prior_art_search に txn を使わない理由がある。Txn-Token と AT の取り違えも起きない |
| q-authorized | C-scope＋C-authorization-details＋C-approval-ref | rar-vs-custom | 合う。type は組織の URI、宛先ごとに 1 つの type、併用は台帳に役割分担（scope は操作の範囲、承認は 1 件の内容）を書いてある。ロールは PDP |
| q-resource | C-aud（1 つ） | — | 合う |
| q-holder | C-cnf（REPAIR_DELEG_AT は may_act＋mTLS） | existing-claim-first（cnf） | 合う。独自の鍵クレームを作っていない |
| q-still-valid（寿命） | 300 秒・都度の aoba-pdp・approval-svc・イントロスペクション | lifetime-by-situation | 合う。5.1 で寿命を REQ-08・REQ-09 の分数から導いている |

lint の warn（L16、hop H5・H8：authorization_details が上流 H4 に無い）：書き手の理由（承認の記録という別の権限の元から、その 1 件の分だけ広げる。agent-sts は承認済みの記録からだけ作り、受け手は approval-svc の条件つきの更新で使用済みにする）は、rar-vs-custom と q-approval-from-as の求める「承認は頼む側の申告でなく記録から」に合い、選択を支えている。指摘にしない（q-hop-narrowing は理由つきで受け入れ）。

## 段 3：優先 1 の問いの答え

下の (2) の表に書いた。No は q-outside-catalog の 1 問で、指摘 F1 にした。

## 段 4：開いた問い

**op-proof-holder**（辿った範囲：C-cnf の enforced_at、token_types の holder・sender_constraint、付録 D の M_sender_constraint の 4.、3.1 の証明書の行と中間の CA の行）
- 箇所ごとに並べた：ORDER/PAYMENT/LOCK_TOOL_AT は持つ者＝鍵を持つ者＝repair-agent。CONTACT_TOOL_AT は交換を求めた repair-agent か visit-subagent。APPROVAL_AT は repair-console（人ではなく BFF の鍵。人は acr・auth_time で別に確かめる）。REPAIR_DELEG_AT は束縛なしで、agent-sts が may_act の URI と mTLS の相手の URI を比べる
- 気づき：cnf は拇印、may_act・許可リストは URI で照合するので、同じ URI の有効な証明書（24 時間）ならどれでも REPAIR_DELEG_AT を交換できる。3.1 に、鍵の漏えいは URI の世代を上げて 30 分で外す手順として書かれている。証明書の更新では共通のクライアント部品が証明書とトークンを組で持つ。指摘にはしない

**op-source-change**（選んだ出来事：異動で修繕担当のロールが外れる。辿った範囲：9.2 の元のデータからの経路、C-sub・C-scope の source_system と on_revoke、2.2、3.1 の人事の台帳の行）
- 人事部の担当者が人事システムで登録 → 人事部のもう 1 人が承認して確定（REQ-08 の起点）→ aoba-pdp が人事の台帳を直接読む（キャッシュ 60 秒）→ 確定・解錠・支払い・承認の使用のたびにツールと approval-svc が aoba-pdp を引く（最悪 60 秒）→ 下書き・連絡は agent-sts の次の交換で scope が外れる（最悪 390 秒）。予約は実行の時点で H13 が引く
- 気づき：hr-sync（5 分）は経路に入らない。aoba-pdp のロールは人事の値から導くだけで、手で書く口が無い。導き方の規則の変更は 2 人の承認の PR。誰も時間を約束していない区間は「登録から確定まで」だけで、3.1 で人事部の手順（2 時間以内）と月次の報告に預けてある。図に無い書き込みの経路は見つからなかった

**op-one-time**（辿った範囲：付録 D の P4 の 5.、C-approval-ref・C-authorization-details の enforced_at、3.1 の重複の実行の行、LOGIN_CODE・CONSOLE_LOGOUT の revocation）
- 並行の 2 件：approval-svc の原子的な条件つきの更新で片方だけが使用済みにする。確定は「下書き→確定」の条件つきの更新。解錠は lock-svc が承認 ID ごとにコードを 1 つだけ作り、送り直しの回も条件つきの更新
- 通信が切れた後の再送：同じ発注 ID・同じ承認には前の結果を返すので、正しい 1 回は失われず、2 回目も通らない。確定できない発注は承認を失効させて新しい発注 ID で依頼し直す
- 記録先の障害：approval-svc が応答しなければ拒否（止める側）。ログアウトトークンは jti を 150 秒覚える
- 気づき：予約を取り消したときに予約済みの承認がどの状態になるか（9.1 は「予約の実行か取り消しまで残る」とだけ書く）が明示されていない。P4 の 5. に「承認を自動で未使用に戻さない」とあるので、取り消しで承認済みに戻らない読みが自然で、承認は発注 ID に結ばれているので別の発注には使えない。指摘にはしないが、状態の遷移の表に「予約→取り消し」の後の承認の状態を書くとよい

## 段 5：優先 2 の問い

9 問とも答えた（(2) の表）。No は無い。「さらに」の開いた問い（op-clock・op-key-custody・op-requirement-words）は辿っていない。ただし F1 は op-requirement-words の「設計にあるのに要求・主体の一覧に無い操作」に当たる。

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | design.md の 3.1（priorities-deferrals）の「発注の台帳の書き込みの口を、この設計の部品だけに閉じること」の行（手作業の発注の停止の宣言）。あわせて 2.1（principals）、2.2（system-privileges）、catalog_answers.yaml の outside_enumeration.found の「管理用の口」の行。問い：q-outside-catalog | 手作業の発注の口は、当番（基盤チーム）が repair-console の「当番の画面」で停止を宣言している間と解除から 24 時間だけ開く。つまり停止の宣言は、承認の前の確かめを通らない発注の登録の窓を開ける操作だが、この画面は 3.1 の 1 か所に名前が出るだけで、誰が使えるか（基盤チームの当番を repair-console と aoba-pdp でどう見分けるか。2.1 の主体の一覧に当番の行が無く、aoba-pdp のロールは修繕担当・上長・鍵の取り扱いだけ）、追加の認証の要否、宣言と解除の記録が監査ログのどこに残るかが、どこにも書いていない。2.2 にも管理用の口の列挙（outside_enumeration）にも入っていない。10 万円を超える手作業の発注は事後の確認と支払いの止めで受けるので、すぐ不正な発注にはつながらない。それでも、窓を開けられる人の範囲が決まっていないので、課長が平常時にも承認を後回しにした登録をできるかどうかが読めない。2.2 に「停止の宣言」の行を足し、当番を見分ける手段（aoba-pdp のロールか許可リスト）と記録先を決める | Minor | 候補の漏れ | q-outside-catalog、q-operator-act |

重大度ごとの件数：Blocker 0、Major 0、Minor 1。

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| dc-05 | Yes | authorization_details のメンバーはすべて文字列で書式（正規表現）が決まっている。金額は 10 進の文字列、時刻は 1 つの書式に固定し、NFC にそろえて書式違いを拒否してから完全一致で比べる。スキーマで型を表せない点は 3.1 で共通部品の試験に預けてある |
| q-value-vocabulary | Yes | ロール・所属はトークンに載せず、aoba-pdp が人事の台帳の職位・所属のコードから導く。scope・acr・type は閉じた語彙で、値を付けるのは認証基盤チームと修繕課のシステム担当だけ。acr は aoba-as だけが作り、agent-sts は写すだけ |
| q-identifier-choice | Yes | 利用者のキーは aoba-as の sub（UUID。identifier_properties と on_missing あり）だけ。人事との突き合わせの社員番号も台帳の行（C-staff-number）があり、性質と欠けたときの扱いが書いてある。テナントのキーは無い |
| ap-1-7 | Yes | 抜き取った 3 行は agent-sts が承認の記録・修繕依頼の台帳からだけ書く。元のデータ（承認・担当・委任・部屋・作業員）の書き手は、承認者の条件・課長・担当者本人・受付・協力会社の窓口の 2 人に限ってある。DB の管理者の直接の書き込みは変更の記録で使う前に止める |
| q-freshness-mitigation | Yes | scope は最悪 390 秒（許容 600）、承認は 0 秒（条件つきの更新）、在籍・ロール・担当は最悪 60 秒（許容 120）。遅れの数値は REQ-08・REQ-09 にあり、対策を行う受け手も書いてある |
| q-single-aud-resource | Yes | 種別もホップも aud は 1 つで、受け手は配列にほかの値があれば拒否する |
| q-no-passthrough | Yes | 交換は agent-sts だけが行い、委任の表・クライアントごとのリソースの表で頼める相手と宛先を固定する。scope は積で絞る。actor_token と client_credentials は受けない |
| q-step-up-path-coverage | Yes | 追加の認証が要る操作（承認・事後の確認）の入口は、repair-console → APPROVAL_AT → approval-svc の 1 つだけ。エージェント・予約・DB の経路からは承認済みにできない（付録 B） |
| ap-2-7 | Yes | act の無い 1 段目の REPAIR_DELEG_AT は宛先が agent-sts だけで、ツールは受けない。交換で出るツールのトークンには必ず act が入る。CONSOLE_AT はエージェントに渡らない |
| q-authorize-service-and-user | Yes | ツール・approval-svc・aoba-pdp・下流は、mTLS の相手の証明書の URI を呼び出し元の許可リストで照合する。利用者の権限（sub・scope・aoba-pdp）とは別に確かめている |
| q-agent-short-lived-no-rt | Yes | agent-sts は RT を出さない。エージェントのトークンは 300 秒で、手順ごとに交換し直す |
| q-outside-catalog | No | 手作業の発注の窓を開ける「当番の画面」（停止の宣言）が、使える人・記録とあわせてどこにも答えられていない（F1）。そのほかの場面（管理の画面・DB・試験の口 U30・旧経路 U29・電話の手配・中間の CA）は答えられている |
| q-object-level-authz | Yes | ツールは対象（下書き・連絡の相手・支払いの発注・部屋）が repair_id の修繕依頼のものかを台帳で照合する（違えば 404）。agent-sts は担当が sub であることを修繕依頼の台帳で確かめる |
| q-approval-from-as | Yes | agent-sts は approval-svc の承認済みの記録からだけ authorization_details を作り、locations の宛先だけに載せる。受け手は内容の一致と条件つきの使用済みで確かめる。依頼の文に紛れた指示で宛先・部屋を変えても、承認の記録とリソースの表で止まる |
| q-operator-act | Yes | 代理ログインは無く、上長の引き継ぎ・管理の画面・lock-svc の管理・DB の管理は、それぞれ自分の sub かアカウントで記録に残る（停止の宣言の記録先だけ未定。F1） |
| q-revocation-delivery | Yes | 重要な操作は剥奪から最悪 60 秒、そのほかは 390 秒、委任の停止は 330 秒、解錠のコードの取り消しは目標 15 分（機器は 12. で未確認）。寿命は 5.1 でこの分数から導いてある |
| q-dependency-outage | Yes | 4. の表と 3.1 で、どの依存先が止まっても止める側に倒す。REQ-13 の 60 分は電話の手配で受ける。JWKS を取り直せなければ拒否し、その理由も書いてある |
| pa-01 | Yes | 独自の 2 行は 25 問の問 1 と enforced_at で、どの受け手が何を決めるか（担当・委任の照合、対象の照合、承認の使用済み）が言える |
| q-derived-value | Yes | 入居者の氏名・電話・住所は載せず（却下）、部屋は lock-tool 宛ての authorization_details の unit_id だけ。repair_id と sub は全受け手が照合か監査に使う |
| q-variant-comparison | Yes | 送信者制約の見送り（CONSOLE_AT・CONSOLE_RT・REPAIR_DELEG_AT）は、開く攻撃（盗んだトークン）と代わりの守り（mTLS のクライアント認証・宛先・may_act）を比べ、確かめ方も書いてある |
| q-idp-diff-absorbed | Yes | 内側の受け手には agent-sts のトークンだけが届き、aoba-as のトークンは agent-sts と repair-console で止まる。発行者はどちらも組織のもの |
| q-original-principal | Yes | 交換の後も sub は担当者のまま、scope は上流・宛先・ロールの積。間に入るサービスの権限で下流を呼ばない |
| q-step-up-by-rs | Yes | 追加の認証を求めるのは承認を受ける approval-svc で、401 と insufficient_user_authentication を返す |
| q-long-running | Yes | 予約はトークンを持ち越さず、実行の時点で在籍・ロール・担当・委任の世代・行為者の登録・承認を引き直す |
| q-copies-outlive | Yes | 写しは監査ログ（鍵つきのハッシュ）、予約の記録（integrity_until と変更の記録）、aoba-pdp のキャッシュ 60 秒だけで、いつまで残り、どう止めるかが書いてある |
| q-audit-correlation | Yes | sub・repair_id・approval_ref を全サービスで同じ鍵・同じ正規化でハッシュし、act の連鎖・jti・業務の ID とあわせて 1 本につなげる |
