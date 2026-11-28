# レビュー：designs/target（あおば住まいサービス 修繕の手配。Full）

- 読んだもの：designs/target/ の design.md（1.〜12.・付録 A・B・D の P4・M_token_validation・M_sender_constraint）、claims.yaml、token_types.yaml、hops.yaml、catalog_answers.yaml（lite_criteria・idp・outside_enumeration・questions・U29・U30）、claim_request_repair_id.md、schemas/LOCK_TOOL_AT.consumer.schema.json、ci-result.txt、sheet.md。教材は short_list.md・perspectives.md（重大度の目安）・decision_tree.md（keep-sub-exchange・peer-mtls・rar-vs-custom）・kind_tell.md
- 行の抜き取りの種：12（sheet.md のとおり。C-approval-ref・C-repair-id・C-authorization-details）
- 指摘：4 件（Blocker 0・Major 2・Minor 2）

## 段 0：CI の結果（機械）

- error 0、warn 2（L16 hop H5・H8：authorization_details が上流 H4 に無い＝下流で広げる）。design.md 1. に行ごとの理由がある
- 理由の確かめ：広げる根拠は上流のトークンではなく approval-svc の承認済みの記録（別の権限の元）で、広がるのは承認した 1 件の分だけ。受け手は approval-svc の条件つきの更新で 1 回だけ使う。承認の無い時点で出す REPAIR_DELEG_AT に承認を載せる手段が無い、という説明も通る。理由は通ると判断し、指摘にしない（q-hop-narrowing）
- 宣言を曲げた跡（q-lint-workaround）：上流を外す・名前を替える・数値を上限に合わせた跡は見当たらない

## 段 1：性質の表の確かめ（sheet.md の 1.）

| 性質 | sheet の判定 | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 合う（repair_id・approval_ref が名前空間つき） |
| 個人情報を載せる | 当たる | 合う（sub・repair_id・approval_ref・authorization_details が個人情報） |
| 発行者が複数 | 当たる | 合う（aoba-as と agent-sts。どちらも組織の自作） |
| 交換・作り直し | 当たる | 合う（H3・H5〜H9・H11・H12 が exchange） |
| 委任がある | 当たる | 合う。なお may_act は C-act でなく別の行 C-may-act（読んだ欄の書き方の差で、判定は変わらない） |
| 操作ごとの承認 | 当たる | 合う（authorization_details の vendor-order・lock-code。時間枠の承認ではない） |
| マルチテナント | 当たらない | 合う（組織は 1 つ。物件の持ち主ごとにデータを分けない。図にも tenant の値が無い） |
| トークンの値を DB の層まで運ぶ | 当たらない | 合う（発注の台帳は order-tool・order-scheduler が自分の DB アカウントで接続。db_connection のホップ無し） |
| 認証の強さ・新しさ | 当たる | 合う（acr・auth_time。承認と手作業の発注の事後の確認） |
| 送信者制約を選んだ | 当たる | 合う（ツールのトークン 4 種・APPROVAL_AT が mtls） |
| 送信者制約を見送った | 当たる | 合う（CONSOLE_AT・CONSOLE_RT・REPAIR_DELEG_AT が none） |
| 長時間・非同期 | 当たる | 合う（予約の発注。ORDER_TOOL_AT の long_running、H13・H14） |

「当たらない」とされた性質が実際にある例は見つからなかった。出さない問い（q-tenant-data-match・q-cross-tenant-identity・q-db-context-writers）は足さない。

## 段 2：6. の「要る」問いと判断の木の節

| 問い | 判断の木の節 | 設計の仕組み | 一致するか |
| --- | --- | --- | --- |
| q-sub・q-actor | keep-sub-exchange | agent-sts の交換で sub を保ち、act に mTLS の相手の URI。ツールは最も外側の act だけを許可リストに当てる（enforced_at と H5〜H8・H11 の validates も同じ） | 一致 |
| q-sub・q-actor（UC4 予約） | keep-sub-exchange（ワーカーが自分の ID で交換し直す） | 交換せず、order-scheduler が判断の元の記録を直接引き直す | 既定から外したことを 3. と 3.1 に理由つきで書き、AS が交換で確かめる項目を同じ出どころから確かめる。問いには答えている |
| q-peer | peer-mtls | wl-ca の証明書の mTLS（URI の SAN）。トークンのクレームで代えていない | 一致。ただし lock-svc の口で、相手の確かめの代わりに置いた仕組みが別の問いに答えている（F1） |
| q-authorized | rar-vs-custom | authorization_details（自管理の URI の type）＋ approval_ref。宛先ごとに type を 1 つ。細かい判断は aoba-pdp | 一致（scope と併用。scope は操作の種類、authorization_details は 1 件の承認と書き分けてある） |
| q-resource | lifetime-by-situation 以前の宛先の束縛（RFC 8707） | aud は 1 つ、resource は 1 つ、リソースの表 | 一致 |
| q-holder | （送信者制約） | cnf の x5t#S256 と mTLS の相手の拇印 | 一致 |
| q-txn | txn-tctx を選ばない | repair_id（何日もまたぐ修繕依頼）。Txn-Token は却下 | 選ばない理由が prior_art_search に書いてある。一致 |
| q-via | — | agent-sts の交換の監査ログ（元の jti と出した jti） | 一致 |

## 段 3：優先 1 の問いに 1 行ずつ

- dc-05：Yes。authorization_details のメンバーはすべて文字列（amount は 10 進の文字列、時刻は 1 つの書式）、受け手は書式を拒否してから完全一致。スキーマで表せない点は 3.1 に見送りと試験を書いてある
- q-value-vocabulary：Yes。ロール・グループは載せず aoba-pdp で引く。scope と acr は閉じた語彙で、ツール・approval-svc は agent-sts の発行だけを受けるので、2 つの発行者の同じ文字列が混ざらない
- q-identifier-choice：Yes。利用者のキーは aoba-as の sub（UUID、identifier_properties と on_missing あり）だけ。社員番号は C-staff-number（却下）に突き合わせの性質を書いてある
- ap-1-7：Yes（抜き取りの 3 行）。トークンに書くのは agent-sts だけで、元のデータ（修繕依頼の台帳の部屋・担当・委任の欄、承認の記録、協力会社の台帳）の書き手と DB の管理者の直接の書き込み（変更の記録で使う前に止める）まで数えてある
- q-freshness-mitigation：Yes。REQ-08 の 2 分・10 分、REQ-09 の 10 分に対し、重要な操作は aoba-pdp（60 秒）、そのほかは 390 秒、承認は 0 秒。対策を行う部品も書いてある
- q-single-aud-resource：Yes。全種別・全ホップの aud が 1 つ
- q-no-passthrough：Yes。交換は agent-sts だけ。クライアントごとのリソースの表と委任の表で宛先・行為者を決め、ツールは上流にトークンを渡さない
- q-step-up-path-coverage：Yes。追加の認証が要る操作（承認・事後の確認）の入口は approval-svc だけで、エージェントの経路・予約の経路からは承認の記録を通る
- ap-2-7：Yes。act の無いトークンをエージェントが持つのは 1 段目の REPAIR_DELEG_AT だけで、宛先は agent-sts、交換は may_act の主体だけ。ツールは aoba-as のトークンを受けない
- q-authorize-service-and-user：No（lock-svc の口）。トークンの経路は mTLS で相手を確かめているが、lock-svc の「証明書だけでコードを作らせない」守りが相手の確かめになっていない（F1）
- q-agent-short-lived-no-rt：Yes。agent-sts は RT を出さず、エージェントのトークンは 300 秒
- q-outside-catalog：Yes。管理用の口・DB の管理者・CA の漏えい・停止の間の電話の発注・旧経路（U29）・試験の口（U30）が答えてある（U30 の前提に aoba-as・repair-console・order-scheduler・aoba-pdp が並んでいないのは軽い漏れで、指摘にはしない）
- q-object-level-authz：Yes。agent-sts が担当と委任の欄、ツールが修繕依頼と対象（下書き・相手・発注・部屋）を台帳で照合し、approval-svc は画面の修繕依頼と記録の修繕依頼を比べる
- q-approval-from-as：No。承認の記録との照合と宛先（locations）への束縛はあるが、手作業の発注の口で 10 万円を超える発注が事前の承認なしに支払いまで通り（F2）、解錠コードを受け取る作業員が承認の内容に入っていない（F3）
- q-operator-act：Yes。上長の引き継ぎ・課長の担当の割り当て・手作業の発注・基盤チームの lock-svc の管理の画面・DB の管理者が、それぞれ自分の ID で動き、ログに残る。代理ログインは作らない
- q-revocation-delivery：Yes。退職・異動は重要な操作 60 秒・ほか 390 秒、委任の停止 330 秒、ログアウト 330 秒、鍵の漏えい 15 分、解錠コードの取り消し 15 分。発行済みのコードを出来事で自動で止めない点は 3.1 に理由と代わりの点検がある
- q-dependency-outage：Yes。aoba-as・aoba-pdp・修繕依頼の台帳・approval-svc・agent-sts・JWKS のどれも止める側に倒し、REQ-13 の 60 分の手作業に切り替える（4. の表と 3.1）

## 段 4：開いた問い

### op-proof-holder（辿った範囲：cnf の enforced_at、全種別の holder・sender_constraint、付録 D の M_sender_constraint の 4.、下流の lock-svc・approval-svc の口）

| 箇所 | トークン（権利）を持つ者 | 確かめる鍵 | 同じか |
| --- | --- | --- | --- |
| ツール 4 つ | 交換を求めた repair-agent か visit-subagent | 同じワークロードの wl-ca の証明書（cnf と mTLS の拇印） | 同じ |
| approval-svc（APPROVAL_AT） | repair-console | repair-console の証明書 | 同じ |
| agent-sts（REPAIR_DELEG_AT） | repair-agent・visit-subagent | 鍵でなく may_act の URI と mTLS の相手の URI | 名前の一致まで。CA の漏えいで破れることは 3.1 に書いてある |
| lock-svc（コードの作成・再要求） | lock-tool | lock-tool の証明書だけ。加えて「承認が lock-tool によって使用済み」 | 証明書の URI だけ。使用済みの確かめは呼び出し元を確かめない（F1） |

- 気づき：証明書の更新（24 時間・残り 8 時間）では aoba-agent-kit が証明書とトークンを組で持ち、cnf の食い違いは起きない。repair-console・repair-agent を複数の台数で動かすとき、台ごとに鍵が違うと、別の台でトークンを使えない（運用の注意。指摘にはしない）
- 気づき：lock-svc は「同じ承認 ID の再要求には同じコードを返す」ので、lock-tool の証明書を持つ者は、使用済みで not_after の前の承認すべてのコードを引き出せる。中間の CA の鍵の漏えいの 60 分の間に、偽の lock-tool の証明書で開く（F1）

### op-source-change（辿った出来事：担当者の修繕課から他課への異動）

- 人事部の担当者が人事システムで登録 → 人事部のもう 1 人が承認して確定（REQ-08 の起点。登録から確定まで 2 時間以内は人事部の手順で、3.1 の見送りと月 1 回の報告）
- aoba-pdp が人事の台帳の API で確定した値を読む（キャッシュ 60 秒）→ 修繕担当のロールが外れる → 発注の確定・解錠・支払いのツールと approval-svc は 60 秒以内に拒否、agent-sts の次の交換も拒否 → 手元のツールのトークン（330 秒）で下書き・連絡が最悪 390 秒
- hr-sync（5 分ごと）は aoba-as の利用者の無効化・セッションの削除をするが、判断の経路に入らない
- 書き込みの経路：ロールを手で書く口は aoba-pdp に無い。導き方の規則は設定の PR（2 人）。社員番号の属性は hr-sync の証明書だけ。研修の記録（鍵の取り扱い）・職務代行の登録も人事の台帳の 2 人の手順
- 誰も時間を約束していない区間：人事の台帳の API が確定した値を何秒で返すか（複製の遅れがあるか）は書いていない。aoba-pdp の 60 秒に含めてよいかは人事の台帳の設計書で確かめたい（指摘にはしない）

### op-one-time（辿った値：発注・解錠の承認、解錠コード、送り直しの回、ログアウトトークンの jti、認可コード）

- 並行の 2 件：approval-svc の条件つきの更新で片方だけが成功。部屋の累計は部屋の行の排他の錠で直列。送り直しの回も条件つきの更新（n が 3 未満なら n+1）
- 通信が切れた後の再送：同じ発注 ID・同じ承認 ID には前の結果を返す。lock-svc は承認 ID ごとにコードを 1 つ、通知の基盤は「承認 ID と送信の回」で重複を捨てる。正しい 1 回は失われない
- 記録先の障害：approval-svc が止まれば拒否し、承認を自動で未使用に戻さない。使用済み・未確定のまま確定できない発注は、下書きの取り消しと同時に承認を失効させ、新しい発注 ID でやり直す
- ログアウトトークンの jti は 150 秒（寿命 120＋ずれ 30）覚える。認可コードは aoba-as が 1 回限り
- 気づき：lock-svc の冪等（同じ承認 ID に同じコード）は「2 回作らない」には答えるが、「2 回目を求めた者が正しい lock-tool か」には答えない。F1 と同じ根

## 段 5：優先 2 の問い

- pa-01：Yes。repair_id は対象の照合と監査の鍵、approval_ref は承認の記録の 1 回の使用と監査の鍵（25 問の問 1）
- q-derived-value：Yes。氏名・電話・住所は載せず、部屋は不透明な unit_id だけ、ログはハッシュ
- q-variant-comparison：Yes。CONSOLE_AT・RT・REPAIR_DELEG_AT の送信者制約の見送りは、盗んだときに何が呼べるかと代わりの守り（mTLS のクライアント認証・may_act）を比べている
- q-idp-diff-absorbed：Yes。ツールには agent-sts のトークンだけが届き、aoba-as のトークンは agent-sts で止まる
- q-original-principal：Yes。交換の後も sub は担当者で、scope は上流・宛先・aoba-pdp のロールの積
- q-step-up-by-rs：Yes。追加の認証を求めるのは approval-svc（受ける側）で、401 と insufficient_user_authentication を返す
- q-long-running：Yes。予約はトークンを持ち越さず、実行の時点で在籍・ロール・担当・委任の世代・承認を引き直す
- q-copies-outlive：Yes。予約の記録（最大 24 時間、実行の時点で確かめ直す）、監査ログ（ハッシュ、3 年）、lock-svc のコード（not_after まで暗号化）と、それぞれの止め方が書いてある
- q-audit-correlation：Yes。sub・repair_id・approval_ref を同じ鍵・同じ正規化のハッシュで全サービスが残し、act の連鎖と jti の対応も残る

答えなかった問い：さらにの開いた問い（op-clock・op-key-custody・op-requirement-words）は深くは辿っていない。目に付いた点だけ：op-clock は付録 D の M_token_validation の 6. に時計の組が数えてある。op-key-custody は付録 D の 8. に 3 つの鍵（aoba-as・agent-sts・wl-ca）の持ち主と分数がある。

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | design.md 3.1 の見送りの行「wl-ca の中間の CA の鍵の漏えいを、60 分より早く塞ぐこと」（効果と費用の列の「解錠のコードの作成は…開かない」）、3.1 の重点の行「重複の実行を、業務の ID で防ぐ」（lock-svc は同じ承認 ID の再要求に同じコードを返す）、11. の U12 の行、付録 D の M_token_validation の 8. の wl-ca の行、claims.yaml の C-unlock-code の assumption、catalog_answers.yaml の outside_enumeration.found（wl-ca の中間の CA の鍵の漏えい）の handled_as | 設計は、中間の CA の鍵が漏れても「lock-svc が approval-svc で承認が lock-tool によって使用済みにされたことを確かめるので、解錠のコードの作成は開かない」とし、これを 60 分の窓を受け入れる理由の 1 つにしている。しかし、approval-svc の使用済みの更新も lock-svc の作成も、どちらも lock-tool の証明書（mTLS だけ）で受ける口である。偽の lock-tool の証明書を持つ者は、(a) 承認済み・未使用の解錠の承認を自分で使用済みにしてからコードを作らせられ、(b) すでに使用済みで not_after の前の承認には、lock-svc の冪等（同じ承認 ID に同じコードを返す）でそのままコードを受け取れる。承認 ID は、同じ窓で開くと設計が認めている approval-svc の記録の参照で集められる。「承認が使用済みか」の確かめは「呼び出し元が本物の lock-tool か・コードを受けてよい者か」に答えないので、最も守りたい解錠コードが窓の間に開く。直し方の例：lock-svc がコードを呼び出し元に返さず、通知の基盤に直接渡す。または作成・再要求のたびに approval-svc が出す 1 回限りの値を求め、再要求に同じコードを返す口を lock-tool の外に出さない。そのうえで 3.1 の開く口の一覧と 60 分の受け入れの判断を書き直す | Major（前提が中間の CA の鍵の漏えいなので Major にした。開くのが部屋の解錠なので、Blocker として扱うかは専門家と相談したい） | 目的と仕組みの不一致（あわせて前提の誤り：開かないという記述が誤り） | peer-mtls（判断の木 5.）、q-authorize-service-and-user、op-proof-holder |
| F2 | design.md 3.1 の見送りの行「発注の台帳の書き込みの口を、この設計の部品だけに閉じること」（手作業の発注）、2.2 の「緊急時の特権」の行、付録 B の「手作業の発注の事後の確認」の行、claims.yaml の C-repair-id の enforced_at（service: payment-tool、check 列）、hops.yaml の H7 の validates.checks、REQ-05・REQ-13 | 手作業の発注の口では、課長 1 人が repair-console の画面から 10 万円を超える発注を登録でき、別の課長の承認は事後の確認だけである。この口を使えるのを停止の間（REQ-13）に限る条件がどこにも無い。さらに payment-tool の条件は「確定済みで完了の報告がある」だけで、事後の確認が済んだか・不適切とされていないかを見ない。不適切とされても管理部の部長に知らせるだけで、支払いは止まらない。このため、平常時でも「上長の承認が要る」（REQ-05）を、手作業の発注として登録するだけで外せ、協力会社の完了の報告の後にエージェントの支払いの依頼で支払いまで通る。直し方の例：手作業の口を、付録 A の停止の警報で開く期間だけに限る。10 万円を超える手作業の発注は、事後の確認が承認済みになるまで payment-tool が支払いを拒否する（H7 と C-repair-id の payment-tool の check に足す） | Major | 候補の漏れ | q-approval-from-as、rar-vs-custom（判断の木 6.） |
| F3 | design.md 付録 D の P4 の 5.「承認を確かめる者」の理由の列（画面に出すのは部屋・協力会社・時間帯）、7. の 2 つ目のシーケンス図（承認の依頼は部屋・協力会社・時間帯だけ）、3.1 の見送りの行「修繕依頼の台帳と協力会社の台帳の書き込みの口…」（作業員の番号のハッシュを承認の記録に残す）、claims.yaml の C-authorization-details の description（lock-code のメンバーに作業員が無い） | 解錠コードを受け取る作業員（REQ-06 の「協力会社の作業員にだけ届ける」の相手）を、誰がどの値から決めるかが書いていない。承認の依頼の要求は部屋・協力会社・時間帯だけなのに、承認の記録には作業員の番号のハッシュが残り、30 分ごとの一覧には作業員の ID が出る。作業員が承認の内容（authorization_details と承認の画面）に入っていないので、担当者本人は誰にコードが届くかを確かめずに承認する。エージェント（入居者の文を読む）の要求で決まるなら、紛れた指示で同じ協力会社の別の作業員に届けさせられる。作業員の決め方（協力会社の台帳の窓口の指定など）を書き、承認の画面と承認の記録の内容に作業員を入れる | Minor | 候補の漏れ | q-approval-from-as |
| F4 | claims.yaml の C-approval-ref の enforced_at（service: approval-svc、check 列の「使用済み・予約済みにするとき（order-tool・lock-tool・order-scheduler の更新）は、承認した人が今も在籍し同じ課の上長のロールを持つこと」）、hops.yaml の H8 の validates.checks（承認者の確かめ直しが無い）と H5・H14（上長の確かめ直しがある） | 解錠の承認は担当者本人がするので、承認した人は上長のロールを持たない。台帳の文のとおりに作ると、lock-tool の使用済みの更新が毎回失敗し、正しい解錠の 1 回が通らない。H8 には承認者の確かめ直しが無く、台帳とホップが食い違う。発注の承認（上長）と解錠の承認（担当者本人・今も担当）で、確かめ直す条件を分けて書く | Minor | 実装とのずれ | q-freshness-mitigation |

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| dc-05 | Yes | authorization_details のメンバーはすべて文字列で書式を固定し、受け手は書式を拒否してから完全一致で比べる |
| q-value-vocabulary | Yes | ロール・グループは載せず aoba-pdp で引く。scope・acr は閉じた語彙で、ツールは agent-sts の発行だけを受ける |
| q-identifier-choice | Yes | 利用者のキーは aoba-as の sub だけで、identifier_properties と on_missing がある。社員番号は却下の行に性質を書いてある |
| ap-1-7 | Yes | 抜き取りの 3 行で、トークンに書く agent-sts と元のデータの書き手・DB の管理者まで数え、止め方がある |
| q-freshness-mitigation | Yes | 重要な操作は aoba-pdp 60 秒、ほかは 390 秒、承認は 0 秒で、REQ-08・REQ-09 の数値に収まる（台帳の文の食い違いは F4） |
| q-single-aud-resource | Yes | 全種別・全ホップで aud が 1 つ |
| q-no-passthrough | Yes | 交換は agent-sts だけで、リソースの表と委任の表で宛先と行為者を決める |
| q-step-up-path-coverage | Yes | 追加の認証が要る承認・事後の確認の入口は approval-svc だけで、ほかの経路は承認の記録を通る |
| ap-2-7 | Yes | エージェントが持つ act の無いトークンは 1 段目の REPAIR_DELEG_AT だけで、宛先は agent-sts、交換は may_act の主体だけ |
| q-authorize-service-and-user | No | トークンの経路は mTLS で相手を確かめるが、lock-svc は承認の使用済みで相手の確かめに代えている（F1） |
| q-agent-short-lived-no-rt | Yes | agent-sts は RT を出さず、エージェントのトークンは 300 秒 |
| q-outside-catalog | Yes | 管理用の口・DB の管理者・CA の漏えい・停止の間の手作業・U29・U30 が答えてある |
| q-object-level-authz | Yes | agent-sts とツールが修繕依頼の台帳で担当・対象を、approval-svc が画面と記録の修繕依頼を照合する |
| q-approval-from-as | No | 手作業の発注で事前の承認なしに支払いまで通り（F2）、コードの受け手の作業員が承認の内容に無い（F3） |
| q-operator-act | Yes | 運用者・課長・基盤チーム・DB の管理者が自分の ID で動き、代理ログインを作らない |
| q-revocation-delivery | Yes | 出来事ごとに最悪の秒数（60・330・390 秒、15 分）が導かれ、発行済みのコードは理由つきで手順に回してある |
| q-dependency-outage | Yes | 頼る先のどれが止まっても止める側に倒し、REQ-13 の 60 分の手作業に切り替える |
| pa-01 | Yes | repair_id は対象の照合と監査、approval_ref は 1 回の使用と監査に使う |
| q-derived-value | Yes | 入居者の氏名・電話・住所は載せず、部屋は不透明な ID だけ |
| q-variant-comparison | Yes | 送信者制約の見送りで、盗まれたときに呼べる口と代わりの守りを比べている |
| q-idp-diff-absorbed | Yes | ツールには agent-sts のトークンだけが届く |
| q-original-principal | Yes | 交換の後も sub は担当者で、scope は上流とロールの積 |
| q-step-up-by-rs | Yes | approval-svc が追加の認証を求め、401 を返す |
| q-long-running | Yes | 予約はトークンを持ち越さず、実行の時点で在籍・委任の世代・承認を確かめ直す |
| q-copies-outlive | Yes | 予約の記録・監査ログ・lock-svc のコードの残る期間と止め方が書いてある |
| q-audit-correlation | Yes | sub・repair_id・approval_ref を全サービスが同じ鍵のハッシュで残し、act の連鎖と jti の対応も残る |
| op-proof-holder | No | lock-svc の口では、コードを受け取る者を証明書の URI でしか確かめない（F1） |
| op-source-change | Yes | 異動を人事の台帳の確定から aoba-pdp・agent-sts・ツールまで辿れる。人事の台帳の API の遅れは書いていない（指摘にしない） |
| op-one-time | Yes | 承認・コード・送り直しの回・jti は、並行・再送・障害のどれでも 2 回通らず、正しい 1 回も失われない |
