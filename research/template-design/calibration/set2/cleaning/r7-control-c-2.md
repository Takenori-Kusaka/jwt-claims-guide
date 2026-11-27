# レビューの記録：designs/target（あおば住まいサービス 修繕の手配）

- 対象：designs/target/design.md、claims.yaml、token_types.yaml、hops.yaml、catalog_answers.yaml、claim_request_*.md、schemas/
- 使った 1 枚：sheet.md（抜き取りの種 12。抜き取った行：C-approval-ref・C-repair-id・C-authorization-details）
- 機械の結果（ci-result.txt と設計書の 1.）：error 0、warn 2（L16 の hop H5・H8。authorization_details が上流 H4 に無い）。warn の 2 行には 1. に理由がある。理由（上流の REPAIR_DELEG_AT は承認の前に出るので承認の内容を持てず、広げる根拠は approval-svc の人の承認の記録で、広がるのはその 1 件だけ）は通ると判断した。q-hop-narrowing の指摘にはしない
- 受け付けで見ること（lint を通すために宣言を曲げていないか）：hops の upstream はすべての交換に書いてあり、aud の置き換えは narrowing_exception に理由がある。曲げた跡は見つからなかった

## 段 1：性質の表の確かめ（12.・2.・6. を読んで）

| 性質 | sheet.md | 図・要求に照らした確かめ |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 合う。名前空間つきの採用の行は C-repair-id・C-approval-ref（どちらも usage identifier）。組織独自の authz の行は無い |
| 個人情報を載せる | 当たる | 合う。C-sub・C-repair-id・C-approval-ref・C-authorization-details が個人情報 |
| 発行者が複数 | 当たる | 合う。aoba-as と agent-sts（どちらも組織が作る。外部 IdP は無い） |
| 交換・作り直し | 当たる | 合う。H3・H5〜H9・H11・H12 が exchange |
| 委任がある | 当たる | 合う。act・may_act、max_delegation_depth 2 |
| 操作ごとの承認 | 当たる | 合う。authorization_details（発注・解錠の 1 件ごと）と approval_ref |
| マルチテナント | 当たらない | 合う。組織は 1 つで、物件の持ち主ごとにデータを分けない（REQ にもテナントは出ない） |
| トークンの値を DB の層まで運ぶ | 当たらない | 合う。order-tool・order-scheduler は自分の DB アカウントで接続し、トークンで接続しない（2. の表のデータ層の行） |
| 認証の強さ・新しさ | 当たる | 合う。acr・auth_time（amr は却下） |
| 送信者制約を選んだ | 当たる | 合う。ツールのトークン 4 種と APPROVAL_AT が mtls |
| 送信者制約を見送った | 当たる | 合う。CONSOLE_AT・CONSOLE_RT・REPAIR_DELEG_AT が none |
| 長時間・非同期 | 当たる | 合う。ORDER_TOOL_AT の long_running、U13 が該当 |

「当たらない」の 2 つは、図・要求のどちらにも実際には無い。問いの追加は無し。

## 段 2：6. の「要る」問いと判断の木の節

| 問い | 判断の木の節 | 設計の仕組み | 比べた結果 |
| --- | --- | --- | --- |
| q-sub・q-user | keep-sub-exchange | 交換で sub を subject_token から写す。重要な操作は sub で aoba-pdp に問い合わせ | 合う |
| q-actor | keep-sub-exchange（最も外側の act） | 受け手は最も外側の act.sub を mTLS の相手・行為者の許可リストと照合。内側の act は記録だけ（C-act の enforced_at、H5〜H8・H11 の validates） | 合う。入れ子の act で許可していない |
| q-actor（UC3） | keep-sub-exchange | client_id が repair-console で act が無いこと | 合う（承認は人の操作で、代理がいないことを確かめる） |
| q-actor・q-sub（UC4 予約の実行） | keep-sub-exchange（非同期はワーカーが自分の ID で交換し直す） | 交換し直さず、order-scheduler が同じ出どころ（aoba-pdp・修繕依頼の台帳・クライアントの登録の表・approval-svc）を引き直す | 既定から外したことが 3. と 3.1 にあり、答える問い（実行の時点でまだ利用者の権限で通してよいか）は同じ。不一致ではない |
| q-peer | peer-mtls | wl-ca の証明書の mTLS（URI の SAN） | 合う |
| q-txn | txn-tctx | C-repair-id（修繕依頼の ID）。Txn-Token は却下。取引の内容の固定は authorization_details | 合う。txn-tctx は「1 つの呼び出しの連鎖で内容を固定」の節で、この設計の連鎖はツールで終わり、内容の固定は承認の記録から作る authorization_details が受け持つ |
| q-authorized | rar-vs-custom | scope（操作の種類）＋ authorization_details（承認した 1 件の内容）＋ approval_ref | 合う。scope と authorization_details の併用で、どちらが何を決めるかが enforced_at に書いてある |
| q-resource | （aud） | aud は 1 つ。agent-sts のリソースの表 | 合う |
| q-holder | （cnf） | cnf の x5t#S256。REPAIR_DELEG_AT は may_act と mTLS の相手 | 合う（REPAIR_DELEG_AT の見送りは 3.1） |
| q-via | — | 交換の監査ログ（元の jti と出した jti） | 合う |

迷った箇所（q-txn）は対比表を見るまでもなく、木の節の「問い」で区別できた。目的と仕組みの不一致は見つからなかった。

## 段 3：優先 1 の問いへの答え（要点）

- dc-05：authorization_details のメンバーはすべて文字列（金額は 10 進の文字列、時刻は 1 つの書式）、value_normalization（NFC・trim・完全一致）があり、受け手は書式違いを拒否してから比べる。生成のスキーマがメンバーの型を表さない点は 3.1 で試験に回している。→ Yes
- q-value-vocabulary：ロール・グループは載せない（却下）。scope・acr・authorization_details の type は value_vocabulary で閉じた語彙、書けるのは組織の 2 つの発行者だけ。→ Yes
- q-identifier-choice：キーは sub（UUID、identifier_properties・on_missing あり）、client_id、repair_id、approval_ref。社員番号はトークンに出ず、aoba-pdp が aoba-as の属性で引く。→ Yes
- ap-1-7：→ No（F1）。aoba-as の利用者の社員番号の属性と、修繕依頼の台帳の担当の履歴を、DB の管理者が直接書けて、使う前に確かめる対象から外れている
- q-freshness-mitigation：scope（許容 600 秒に最悪 390 秒）、authorization_details（許容 0 秒に approval-svc の条件つきの更新）、載せない在籍・ロール・担当（許容 120 秒に aoba-pdp の 60 秒）、委任の欄（許容 600 秒に 330 秒）。担い手も書いてある。→ Yes
- q-single-aud-resource：どの種別もホップも aud は 1 つ。→ Yes
- q-no-passthrough：exchanger は agent-sts だけ。委任の表・クライアントごとのリソースの表・may_act と mTLS・scope の積。→ Yes
- q-step-up-path-coverage：承認・事後の確認は APPROVAL_AT（H12）だけで通り、エージェント・order-scheduler の経路は承認の操作をしない。→ Yes
- ap-2-7：act の無い 1 段目の REPAIR_DELEG_AT はエージェントが持つが、宛先は agent-sts だけで may_act と mTLS が要る。ツールのトークンには必ず act が入り、APPROVAL_AT は repair-console にしか出ない。→ Yes
- q-authorize-service-and-user：ツール・approval-svc・aoba-pdp・台帳・下流は呼び出し元の証明書の許可リストで受け、利用者の権限とは別に決めている。→ Yes
- q-agent-short-lived-no-rt：エージェントに RT を出さない。300 秒で、手順ごとに交換し直す。→ Yes
- q-outside-catalog：→ No（F3）。3.1 が手作業の取り消しに使う lock-svc の管理の画面が、2.2 の管理用の口にも outside_enumeration にも無い
- q-object-level-authz：対象の ID は、ツールごとに repair_id と台帳の持ち主で照合し、repair_id は agent-sts が担当と委任の欄で確かめる。承認の記録は記録の repair_id とトークンの repair_id を比べる。→ Yes
- q-approval-from-as：承認は approval-svc の記録から agent-sts が作り、locations で宛先に結び、受け手が条件つきの更新で 1 回だけ使う。依頼の金額・部屋はツールの記録から作る。→ Yes（ただし解錠の時間帯の上限を誰も確かめない点は F2 として別に出した）
- q-operator-act：上長の引き継ぎは自分のログイン、運用者は管理の画面に自分のログイン、DB の管理者は変更の記録の表に DB アカウントが残る。予約の実行は order-scheduler を行為者として残す。→ Yes
- q-revocation-delivery：単位ごとの最悪の値がある（重要な操作 60 秒、下書き・連絡 390 秒、委任の停止 330 秒、ログアウト 330 秒、解錠のコードの取り消し 15 分、証明書の鍵の漏えい 30 分、中間の CA 60 分）。寿命の数字は REQ から導いている。→ Yes
- q-dependency-outage：4. の表と 3.1 で、頼る先ごとに止める側に倒し、REQ-13 の 60 分と合わせている。JWKS は reject。→ Yes

## 段 4：開いた問い

### op-proof-holder（鍵の持ち主）

辿った範囲：C-cnf の enforced_at（ツール 4 つ・approval-svc）、種別の holder・sender_constraint、M_sender_constraint の 4.、2.1。

| 確かめる箇所 | トークンを持つ者 | 鍵を持つ者（cnf の証明書） |
| --- | --- | --- |
| order-tool・payment-tool・lock-tool | repair-agent | repair-agent（交換を求めた者） |
| contact-tool（H6） | repair-agent | repair-agent |
| contact-tool（H11） | visit-subagent | visit-subagent（自分で H10 の交換をする） |
| approval-svc | repair-console | repair-console |
| agent-sts（REPAIR_DELEG_AT。束縛なし） | repair-agent・visit-subagent | may_act の URI と mTLS の相手の URI で照合 |

気づいたこと：どの箇所も「持つ者＝鍵を持つ者」。ツールは cnf に加えて act.sub と mTLS の相手の URI も比べる。証明書の更新のときは aoba-agent-kit が証明書とトークンを組で持つと書いてあるが、これはエージェントの部品で、APPROVAL_AT を持つ repair-console が同じ扱いをするかは書いていない（APPROVAL_AT は 120 秒で操作ごとに取り直すので影響は小さい）。同じ URI のワークロードを複数の実体で動かす場合（実体ごとに鍵が違う）、ある実体が交換したトークンを別の実体が使うと cnf が合わずに失敗する。可用性の点で、指摘にはしない。

### op-source-change（元データの変更から辿る）

出来事：担当者の異動（修繕課から外れる）。

辿った経路：人事部の担当者が人事システムで登録 → 人事部の 2 人目が承認して確定（REQ-08 の起点。登録から確定まで 2 時間以内は人事部の手順で、3.1 の見送り）→ aoba-pdp が人事の台帳の API を引く（60 秒キャッシュ）→ 重要な操作のツール・approval-svc は呼び出しごとに aoba-pdp（最悪 60 秒）、agent-sts は交換ごとに scope を絞る（下書き・連絡は最悪 390 秒）→ hr-sync は 5 分ごとに aoba-as を更新（判断の経路には入らない）。

気づいたこと：
- aoba-pdp は sub から社員番号を aoba-as の利用者の属性で引く。この属性の書き手は hr-sync の証明書の API だけと書くが、aoba-as の利用者の DB の管理者も直接書ける（2.2 の DB の管理の行、3.1）。書き換えると、その sub に別の社員（課長など）の在籍・職位・所属が付く。これは使う前に確かめる対象に入っておらず、翌日の突き合わせまで通る（F1）
- 人事の台帳の API が、確定をどれだけ遅れずに返すかは書いていない（人事の台帳は別の設計書）。REQ-08 の 2 分は「確定の時点」からなので、この区間はどの設計書も時間を約束していない可能性がある。確かめの依頼に留める

### op-one-time（1 回だけ使える値）

辿った範囲：承認の記録（P4 の 5.、C-approval-ref・C-authorization-details の enforced_at、3.1 の重点の行）、発注 ID・承認 ID・下書きの ID、ログアウトトークンの jti、認可コード。

- 並行の 2 件：承認の消費は approval-svc の 1 つの原子的な条件つきの更新で、片方だけが成功する。発注の確定は「下書き→確定」の条件つきの更新。部屋の累計は排他の錠の中で数える。解錠は lock-svc が承認 ID ごとにコードを 1 つだけ作る
- 通信が切れた後の再送：同じ発注 ID・同じ承認には前の結果を返す。送信は（承認 ID・送信の回）で重複を捨てる。予約の実行は同じ発注 ID で再試行
- 記録先の障害：approval-svc が応答しなければ拒否（止める側）
- 正しい 1 回の喪失：「使用済み・未確定」の承認を持つ下書きは 7 日で消さず、閉じるまで残す。ただし閉じるのは order-tool の下書きの取り消しか再試行で、エージェントが止まった（ログアウト・委任の停止）後に、誰がいつ閉じるかは書いていない。手作業の運用で拾えるので、指摘にはしない
- ログアウトトークンの jti は repair-console が 150 秒覚える。repair-console を複数の実体で動かすなら、覚える場所を共有するかは書いていない（Back-Channel Logout の再送は、消すセッションが同じなので害は小さい）

辿る途中で見つけたこと：解錠の時間帯（not_before〜not_after）の「4 時間以内」を、どの受け手も確かめていない（F2）。

## 段 5：優先 2 の問い（時間が残ったので答えた）

すべて下の (2) の表に書いた。No は無い。

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | 3.1 の見送りの行「approval-svc・発注の台帳・aoba-as の利用者・修繕依頼の台帳・協力会社の台帳の DB の管理者の直接の書き込みを止めること」、2.2 の「DB の管理」の行、9.2 の「元のデータからの経路」、claims.yaml の C-sub の `source_system`・`verification_method`、C-sub の `enforced_at`（approval-svc：担当の履歴に無いこと）、C-repair-id の `integrity_until`。問い ap-1-7（No） | 3.1 は「翌日では遅いもの」を承認の記録と予約の記録だけとし、使う前に変更の記録の表で確かめる。ほかは翌日の突き合わせで見つけるだけにしている。ところが、次の 2 つも書いたその場で権限の判断に使われ、翌日では遅い。(a) aoba-as の利用者の社員番号の属性：aoba-pdp は sub からこの属性で人事の台帳を引くので、DB の管理者が自分の利用者に課長の社員番号を書けば、自分のログイン（自分の TOTP）のまま上長として 10 万円を超える発注を承認でき、担当の割り当ての画面で担当も付け替えられる（aoba-pdp のキャッシュ 60 秒の後から）。承認の記録そのものは approval-svc のアプリが書くので、使う前の確かめを通る。(b) 修繕依頼の台帳の担当の履歴：行を消すと、担当だった課長が自分の発注を承認できる（REQ-05 の「担当になったこともない人」を外せる）。どちらも翌日の突き合わせまで止まらず、承認した発注は実行の後に見つかる。承認・予約の記録を前もって確かめる理由（すぐ使われる）が、この 2 つにも当てはまるのに、区別の理由が書いていない。対策の案：aoba-pdp が社員番号の属性と担当の履歴を読むときに、変更の記録の表で hr-sync・repair-console の DB アカウントが書いたことを確かめる。または、この 2 つを見送る理由を 3.1 に書く | Major（DB の管理者による上長の権限の取得。観点書の目安は Blocker だが、書き手が DB の管理者を限られた 2 人とし、翌日に検出する手段がある分を下げた） | 理由の不備 | ap-1-7 |
| F2 | claims.yaml の C-authorization-details の `description`（「差は 4 時間以内」）と `enforced_at`（lock-tool）、C-approval-ref の `enforced_at`（lock-tool・approval-svc）、hops.yaml の H8・H12 の `validates.checks`、付録 D の P4 の 5.（承認の内容・受け手の照合）、REQ-06、3.1 の見送りの行「発行した解錠コードを……自動では止めないこと」 | REQ-06 は解錠の時間帯を 4 時間以内に限るが、台帳は description に「差は 4 時間以内」と書くだけで、確かめる受け手がいない。lock-tool の照合は「要求と完全一致し、今が not_before と not_after の間」で、承認の依頼の登録（lock-tool）・承認（approval-svc、H12）・authorization_details を作る agent-sts のどこにも、not_after − not_before が 4 時間以内かの検査が無い。時間帯はエージェントの要求から承認の依頼に入るので、入居者の依頼の文に紛れた指示で長い時間帯を頼ませ、担当者が見落として承認すると、4 時間を超えて使えるコードが出る。しかも 3.1 は、発行済みのコードを出来事から自動で止めない理由に「コードは最大 4 時間の窓」を使っている。直し方：lock-tool が承認の依頼を登録するとき、approval-svc が承認するとき、agent-sts が authorization_details を作るときのどれか（できれば lock-tool と approval-svc の両方）で、差が 14400 秒を超えれば拒否すると enforced_at に書く | Major（権限の誤り：要求より長い解錠の窓。見送りの理由の前提も崩れる） | 候補の漏れ | （q-approval-from-as の関連。承認の内容のうち、人の確かめだけに任せた制約） |
| F3 | 3.1 の見送りの行「頼る先が止まった間の解錠コードの取り消しを、通常の経路で行うこと」（lock-svc の管理の画面）、2.2 の「管理用の口」の行、catalog_answers.yaml の `outside_enumeration.found`（管理用の口の行）、2. の範囲の図（lock-svc に管理の画面の入口が無い）。問い q-outside-catalog（No） | lock-svc の管理の画面（基盤チームの 2 人が自分のログインで入る）が 3.1 の取り消しの手順にだけ出てくる。2.2 の管理用の口・outside_enumeration の管理用の口の列挙・範囲の図に無い。この画面でできることが失効だけか、コードの作成・表示・承認 ID なしの解錠もできるのかが書いていない。作成や表示ができるなら、REQ-06（承認ごとに 1 回だけ発行し、コードは作業員にだけ届け、画面・ログに出さない）を承認の記録なしで外れる口になる。直し方：2.2 と outside_enumeration に lock-svc の管理の画面を足し、できる操作（失効だけ）と、作成・表示ができないことの確かめ方を書く | Major（想定漏れの候補。観点書の q-outside-catalog の目安） | 候補の漏れ | q-outside-catalog |
| F4 | hops.yaml の H2 の `validates.checks`（「同じ課の課長」）、claims.yaml の C-sub の `enforced_at`（agent-sts：「承認者になりうる上長」）、C-repair-id の `authoritative_writer`・`verification_method`・`enforced_at`（agent-sts：「承認者になりうる上長」）、token_types.yaml の APPROVAL_AT の `note`（「担当者の上長」）、design.md の 4. の表（「同じ課の課長（承認・事後の確認・解錠の取り消しのどれかをしうる人）」）、2.1 の上長の行（「職位が課長以上で同じ課の人」） | agent-sts が APPROVAL_AT を出してよい相手（担当者でないとき）が、5 か所で 4 通りに書いてある（同じ課の課長／承認者になりうる上長／担当者の上長／同じ課の課長以上）。2.1 は上長を「課長以上」とし、H2・4. は「課長」に限る。実装で H2 を正にすれば、課長以上の職位（職務代行を含む）の上長が承認の画面で拒否され、2.1 を正にすれば H2 の確かめが広がる。同じ仕組みの条件の食い違い。直し方：aoba-pdp に問い合わせる条件を 1 つの言い方（職位・所属のコード）に決め、5 か所をそろえる | Minor（記述の食い違い。どちらに倒しても、承認者の条件そのものは approval-svc が確かめる） | 実装とのずれ | q-object-level-authz |

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| dc-05 | Yes | authorization_details のメンバーは全部文字列（金額は 10 進、時刻は 1 書式）で、正規化と完全一致の比べ方が決まり、受け手は書式違いを拒否する |
| q-value-vocabulary | Yes | ロール・グループは載せず aoba-pdp に問い合わせ、scope・acr・RAR の type は組織が持つ閉じた語彙で、書けるのは組織の 2 発行者だけ |
| q-identifier-choice | Yes | 利用者のキーは aoba-as の UUID の sub だけで、identifier_properties・on_missing があり、社員番号はトークンに出ない |
| ap-1-7 | No | 社員番号の属性と担当の履歴を DB の管理者が直接書け、使う前の確かめから外れている（F1） |
| q-freshness-mitigation | Yes | 寿命が許容を超える値（scope・authorization_details・載せない在籍とロールと担当・委任の欄）すべてに、担い手つきの対策と最悪の秒数がある |
| q-single-aud-resource | Yes | 種別・ホップの aud はすべて 1 つで、受け手は配列にほかの値があれば拒否する |
| q-no-passthrough | Yes | 交換は agent-sts だけで、委任の表・クライアントごとのリソースの表・may_act と mTLS・scope の積で宛先と範囲を決める |
| q-step-up-path-coverage | Yes | 追加の認証が要る承認・事後の確認は H12 の APPROVAL_AT だけで通り、ほかの経路は承認の操作をしない |
| ap-2-7 | Yes | act の無い 1 段目の REPAIR_DELEG_AT は agent-sts 宛てで may_act の mTLS が要り、ツールのトークンには必ず act が入る |
| q-authorize-service-and-user | Yes | どの受け手も呼び出し元の wl-ca の証明書を許可リストで照合し、ツールは act.sub と mTLS の相手も比べる |
| q-agent-short-lived-no-rt | Yes | エージェントには RT を出さず、トークンは 300 秒で手順ごとに交換し直す |
| q-outside-catalog | No | lock-svc の管理の画面が管理用の口の列挙に無く、できる操作が書いていない（F3） |
| q-object-level-authz | Yes | 他人の修繕依頼・発注・承認は、agent-sts の担当の確かめと、ツール・approval-svc の repair_id と台帳の持ち主の照合で止まる |
| q-approval-from-as | Yes | 承認は approval-svc の記録から agent-sts が作り、locations で宛先に結び、受け手が条件つきの更新で 1 回だけ使う（時間帯の上限の検査漏れは F2） |
| q-operator-act | Yes | 引き継ぎ・管理の画面・手作業の発注は運用者自身のログインで、DB の直接の書き込みは変更の記録に DB アカウントで残る |
| q-revocation-delivery | Yes | 重要な操作 60 秒、下書き・連絡 390 秒、委任の停止 330 秒、解錠コード 15 分など、単位ごとの最悪の値と手段が並び、寿命は REQ から導いている |
| q-dependency-outage | Yes | 頼る先ごとに止める側に倒すことが 4. と 3.1 にあり、REQ-13 の 60 分と合わせている |
| op-proof-holder | 該当なし | 開いた問い。どの箇所も持つ者と鍵を持つ者が同じで、指摘は無し（repair-console の証明書の更新の扱いは未記載。段 4） |
| op-source-change | 該当なし | 開いた問い。異動を辿り、社員番号の属性の書き手の漏れを見つけた（F1）。人事の台帳の API の反映の遅れは未約束（段 4） |
| op-one-time | 該当なし | 開いた問い。並行・再送・障害のどれでも 2 回通らない。辿る途中で解錠の時間帯の上限の検査漏れを見つけた（F2） |
| pa-01 | Yes | repair_id は担当・委任の確かめと対象の照合、approval_ref は消費する承認の記録の特定に、受け手ごとに使い道が書いてある |
| q-derived-value | Yes | 個人情報の行は使う受け手にだけ届き（authorization_details は order-tool・lock-tool だけ）、入居者の連絡先・住所は参照の ID で代えている |
| q-variant-comparison | Yes | 送信者制約の見送り（CONSOLE_AT・CONSOLE_RT・REPAIR_DELEG_AT）は、盗まれたときにできることと代わりの守り（mTLS のクライアント認証・may_act）を比べている |
| q-idp-diff-absorbed | Yes | ツールには agent-sts のトークンだけが届き、aoba-as の CONSOLE_AT は agent-sts だけが受ける |
| q-original-principal | Yes | 交換の後も sub は担当者のままで、scope は上流と宛先とロールの積に絞る |
| q-step-up-by-rs | Yes | 追加の認証の要否は approval-svc が決め、足りなければ 401 insufficient_user_authentication を返す |
| q-long-running | Yes | 予約の実行はトークンを持ち越さず、order-scheduler が実行の時点で在籍・ロール・担当・委任の世代・承認を引き直す |
| q-copies-outlive | Yes | 予約の記録の写しは実行の前に確かめ直し、監査ログはハッシュで残し、aoba-pdp のキャッシュは 60 秒 |
| q-audit-correlation | Yes | sub・repair_id・approval_ref は全サービスで同じ鍵・同じ正規化のハッシュ、act の連鎖と jti・業務の ID も残る |

答えなかった問い：無い（優先 1 の 17 問、開いた問い 3 つ、優先 2 の 9 問に答えた）。「さらに」の開いた問い（op-clock・op-key-custody・op-requirement-words）は辿っていない。専門家に回す点（委任の深さ 2）は、設計書の 12. で既に回してある。
