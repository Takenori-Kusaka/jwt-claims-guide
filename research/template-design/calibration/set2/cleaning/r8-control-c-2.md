# レビュー報告：designs/target（あおば住まいサービス 修繕の手配）

- 対象：designs/target/design.md と claims.yaml・token_types.yaml・hops.yaml・catalog_answers.yaml（あわせて schemas/ の一部と claim_request_*.md の存在を確認した）
- 使った 1 枚：sheet.md（行の抜き取りの種 12。抜き取った行は C-approval-ref・C-repair-id・C-authorization-details）
- 機械の結果：ci-result.txt と設計書の 1. は一致する（error 0・warn 2・info 24）。warn 2 件（L16、H5・H8 の authorization_details が上流 H4 に無い）には行ごとの理由がある。理由は「広げる根拠は上流のトークンではなく、別の権限の元である人の承認の記録（approval-svc）で、広がるのは承認した 1 件の分だけ。agent-sts は承認済みの記録からだけ作る」というもの。台帳の enforced_at（受け手が approval-svc の条件つきの更新で使用済みにする）と食い違わないので、通る理由として受け入れた（q-hop-narrowing・rar-vs-custom と照らした）
- 受け付けで確かめたこと（q-lint-workaround）：上流を外す・名前を変える・数値を上限に合わせるといった、宣言を曲げた跡は見つからなかった

## 段 1：性質の表の確かめ（12.・2.・6. と図・要求に照らした）

| 性質 | sheet の判定 | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 当たる。repair_id・approval_ref が名前空間 https://aoba-sumai.example/claims/ にある |
| 個人情報を載せる | 当たる | 当たる。sub・repair_id・approval_ref・authorization_details の pii_category が「個人情報」 |
| 発行者が複数 | 当たる | 当たる。aoba-as と agent-sts の 2 つ（2. の図の AS・STS） |
| 交換・作り直し | 当たる | 当たる。H3・H5〜H9・H11・H12 が exchange |
| 委任 | 当たる | 当たる。act・may_act、max_delegation_depth が 2 |
| 操作ごとの承認 | 当たる | 当たる。REQ-05・REQ-06、authorization_details（H5・H8） |
| マルチテナント | 当たらない | 当たらないことを確かめた。組織は 1 つで、オーナーごとにデータを分けない（REQ・図・lite_criteria が一致） |
| DB の層まで運ぶ | 当たらない | 当たらないことを確かめた。発注の台帳には order-tool・order-scheduler が自分の DB アカウントで接続する（2. の境界の表のデータ層の行、9.1 の DB・ブローカーの接続の層） |
| 認証の強さ・新しさ | 当たる | 当たる。REQ-07、acr・auth_time（付録 B） |
| 送信者制約を選んだ | 当たる | 当たる。ツールのトークン 4 種と APPROVAL_AT が mtls |
| 送信者制約を見送った | 当たる | 当たる。CONSOLE_AT・CONSOLE_RT・REPAIR_DELEG_AT が none（3.1 に見送りの行がある） |
| 長時間・非同期 | 当たる | 当たる。REQ-10 の予約の発注、ORDER_TOOL_AT の long_running、U13 が「該当」 |

「当たらない」とされた性質が実際にはある、という食い違いは無い。12. には確かめていない事実だけが書かれ、見送りは 3.1 に分けてある。

## 段 2：6. で「要る」とした問いと判断の木の節

| 問い | 節 | 設計の仕組み | 比べた結果 |
| --- | --- | --- | --- |
| q-sub・q-actor（UC1〜3） | keep-sub-exchange | 交換で sub を写すだけ。act は mTLS の相手から作り、受け手は最も外側の act.sub だけを許可リストに当てる（C-act の enforced_at、H5〜H8・H11 の validates） | 合う。入れ子の act は記録だけで、許可に使っていない |
| q-sub・q-actor（UC4、予約） | keep-sub-exchange | 交換し直さず、order-scheduler が同じ出どころ（aoba-pdp・修繕依頼の台帳・approval-svc・クライアントの登録の表）を実行の時点で引き直す | 木の既定から外れるが、3. と 3.1 に外れた点・理由・確かめ方がある。問いの取り違えではない |
| q-peer | peer-mtls | wl-ca の証明書の mTLS（URI の SAN） | 合う。トークンのクレームで代えていない |
| q-txn | txn-tctx | repair_id（Txn-Token は却下） | 合う。対比表 act-txn-workload の「解く問い」で確かめた。ここで要るのは、日をまたいで何度も呼ばれる修繕依頼を相関させ、対象を照合する鍵で、1 つの呼び出しの連鎖の中で取引の内容を固定する問いではない。取引の内容は authorization_details と承認の記録で固定している |
| q-authorized | rar-vs-custom | scope（操作の種類）＋authorization_details（承認した 1 件）＋approval_ref | 合う。同じ API で両方を使うが、どちらで何を決めるかを enforced_at に書いている（RFC 9396 §3.1） |
| q-holder | （木の節なし。1. の cnf） | cnf.x5t#S256 | 合う |
| q-resource | — | aud を 1 つ、resource を 1 つ | 合う |
| q-still-valid の扱い（寿命） | lifetime-by-situation | 300 秒・RT なし、重要な操作は都度 aoba-pdp と approval-svc に問い合わせる | 合う。寿命の数字は 5.1 で REQ-08・REQ-09 の分数から導いている |

目的と仕組みが合っていない行は見つからなかった。

## 段 3：優先 1 の問いへの答え（1 行ずつ）

- dc-05：Yes。authorization_details のメンバーはすべて文字列で、パターン（金額は 10 進の文字列、時刻は書式を 1 つに固定）と、書式の違う値を拒否してから完全一致で比べる規則が決まっている。スキーマで表せない分は 3.1 で試験に回している
- q-value-vocabulary：Yes。ロール・グループはトークンに載せず、aoba-pdp が人事の台帳から導く。scope・acr・RAR の type は閉じた語彙で、発行者は組織の 2 つだけ
- q-identifier-choice：Yes。利用者のキーは aoba-as の sub（UUID）だけで、agent-sts は写すだけ。identifier_properties と on_missing がある
- ap-1-7：No。設定を 1 人で変えられる緊急の経路があり、追加も含めて変えられる（F2）
- q-freshness-mitigation：Yes。scope は最悪 390 秒（REQ-08 の 600 秒の内側）。在籍・ロール・担当は都度の問い合わせで 60 秒（120 秒の内側）。承認は 0 秒（条件つきの更新）
- q-single-aud-resource：Yes。どの種別も aud が 1 つ
- q-no-passthrough：Yes。委任の表・クライアントごとのリソースの表・may_act と mTLS の照合が規則として決まっている（P4 の 4.）
- q-step-up-path-coverage：Yes。承認の操作の口は approval-svc の 1 つだけで、APPROVAL_AT は act の無い repair-console にしか出ない。エージェントの経路と予約の経路は承認の記録を使うだけ
- ap-2-7：Yes。エージェントが持つ act の無いトークンは 1 段目の REPAIR_DELEG_AT だけで、宛先は agent-sts だけ、交換できるのは may_act の主体だけ
- q-authorize-service-and-user：Yes。すべての呼び出しが mTLS で、許可リストと、トークンの act・cnf の照合を別々に行う（許可リストを書ける人の問題は F2）
- q-agent-short-lived-no-rt：Yes。agent-sts は RT を出さない（refresh_token の grant を受けない）
- q-outside-catalog：Yes。管理用の口・DB の管理者・電話の手配・中間の CA の漏えい・テスト用の口（U30）・旧い経路（U29）が 2.2・3.1・catalog_answers に答えられている（ただし中間の CA の行の中身に誤りがある：F1）
- q-object-level-authz：Yes。他人の修繕依頼・発注・部屋は、各ツールが台帳で repair_id と照らして 404 にし、approval-svc は記録の repair_id と承認者の条件で止める
- q-approval-from-as：Yes。通常の運用では、承認は approval-svc の記録から agent-sts が作り、locations と同じ宛先にだけ載せ、発注 ID と承認 ID に結んで 1 回だけ使う。宛先をすり替える指示も通らない（ただし証明書だけで受ける lock-svc の口については F1）
- q-operator-act：Yes。上長・課長は自分の CONSOLE_AT で操作する。代理ログインは無い。DB の管理者と lock-svc の管理者の操作は、変更の記録と監査ログに残る
- q-revocation-delivery：Yes。重要な操作は 60 秒、下書き・連絡は 390 秒、委任の停止は 330 秒、鍵の漏えいは 15 分。解錠コードを出来事から自動で止めない点は 3.1 で見送り、代わりの点検がある
- q-dependency-outage：Yes。どの頼る先が止まっても止める側に倒す。REQ-13 の 60 分と付録 A の 5 分の警報がある

## 段 4：開いた問い

### op-proof-holder

- 辿った範囲：C-cnf の enforced_at（ツール 4 つと approval-svc）、種別の holder・sender_constraint、issuance_profile の mtls の例外、C-cnf の on_revoke（証明書の更新）、3.1 の REPAIR_DELEG_AT の見送りと wl-ca の行
- 箇所ごとに「トークンを持つ者」と「鍵を持つ者」を並べた：
  - ツールのトークン：交換を求めたのは repair-agent か visit-subagent で、これがそのまま持ち手になる。鍵の持ち主と同じ
  - APPROVAL_AT：交換を求め、持つのは repair-console。鍵の持ち主と同じ
  - REPAIR_DELEG_AT：束縛しない。may_act と mTLS の相手の照合で代えている
  - 証明書の更新：証明書は 24 時間で、残り 8 時間で更新する。共通の部品が証明書とトークンを組で持ち、トークンは 330 秒で切れる
- 気づいたこと：トークンを使わずに証明書だけで受ける口（lock-svc・approval-svc の「lock-tool による使用済み」の状態・通知の基盤・経理）では、確かめる側が見ているのは「この証明書の URI」だけになる。トークンの持ち主かどうかは見ていない。このため、中間の CA が漏れたときに解錠の口が開く（F1）

### op-source-change

- 辿った出来事：異動で修繕担当のロールが外れる
- 辿った経路と時間：
  1. 人事部の担当者が人事システムで登録する
  2. 人事部のもう 1 人が承認して確定する（手順書で 2 時間以内。月に 1 回報告。3.1 の見送り）
  3. aoba-pdp が人事の台帳の API で確定した値を読む（キャッシュ 60 秒）
  4. 重要な操作は、ツールと approval-svc が都度問い合わせて止める（60 秒）。agent-sts も次の交換で止める
  5. 下書き・連絡は最悪 390 秒で止まる
  6. 予約は実行の時点で止まる。その人が承認者なら、まだ使っていない承認は、使う時点の確かめで止まる
- 書き手：人事の台帳は 2 人の手順、社員番号の属性は hr-sync の証明書だけ、ロールを手で書き換える口は無い。DB の管理者の直接の書き込みは、変更の記録の表で「要確認」になり使えない
- 気づいたこと：誰も時間を約束していない区間は、登録から確定までの間（人事の手順）だけで、3.1 に書いてある。hr-sync の 5 分の遅れは判断の経路に入らない。新しい欠けは見つからなかった

### op-one-time

- 辿った値：承認（発注・解錠）、解錠のコード、認可コード、ログアウトトークンの jti、予約の記録
- 並行の 2 件：approval-svc の原子的な条件つきの更新で、片方だけが成功する。部屋の累計は、部屋の行の排他の錠で直列にしている
- 通信が切れた後の再送：同じ発注 ID・同じ承認 ID には前の結果を返す。lock-svc は同じ承認 ID に同じコードを返す。通知の基盤は「承認 ID と送信の回」で重複を捨てる。送り直しは回を条件つきの更新で上げる（3 回まで）
- 記録先の障害：approval-svc が止まれば拒否する。承認を自動で未使用に戻さない。使用済みのまま確定していない状態は、付録 A で 10 分を監視し、同じ ID で再試行する
- 正しい 1 回を失わないか：同じ ID での再試行と、下書きの取り消しと同時の失効で扱っている
- 気づいたこと：lock-svc の「同じ承認 ID の再要求には同じコードを返す」は、結果が分からない後の 1 回を守る仕組みとしては正しい。ただし not_after までは、lock-tool として呼べる者なら誰でもコードを取り直せる。この口が証明書だけで守られている点を F1 に書いた

## 段 5：優先 2 の問い

時間が残ったので、全問に答えた（下の表 (2)）。No の問いは無かった。

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | design.md の 3.1（priorities-deferrals）の見送りの行「wl-ca の中間の CA の鍵の漏えいを、60 分より早く塞ぐこと」。同じ記述のある catalog_answers.yaml の outside_enumeration.found の「wl-ca の中間の CA の鍵の漏えい…」。claims.yaml の C-unlock-code の assumption。design.md の 3.1 の「重複の実行を、業務の ID で防ぐ」の行（lock-svc は同じ承認 ID に同じコードを返す）。2. の図の LT→AP（mTLS だけ。承認の依頼・使用済み）・LT→LS・LS→AP（mTLS だけ） | 見送りの行は「解錠のコードの作成は、lock-svc が approval-svc で、承認が lock-tool によって使用済みにされたことを確かめるので開かない」と書いている。しかし、「lock-tool によって」を approval-svc も lock-svc も呼び出し元の証明書の URI でしか見ていない（どちらもトークンを受けない口）。同じ行が書くとおり、中間の CA の鍵が漏れると任意のワークロードになりすませる。そのため攻撃者は lock-tool の偽の証明書で、(a) approval-svc にある承認済み・未使用の解錠の承認を「使用済み」にでき、(b) lock-svc にコードを作らせられる。さらに (c) lock-svc は同じ承認 ID の再要求に同じコードを返すので、すでに発行した not_after の前の承認からもコードを取り直せる。lock-svc がコードを返す相手は呼び出し元の lock-tool である（lock-tool がコードを通知の基盤に渡す流れ。C-unlock-code の rationale）。したがって、60 分の窓の間に開く口の一覧から「解錠」が抜けており、受け入れた危険の大きさを誤っている。開くのは、入居者の部屋の物理的な解錠になる。直すなら、lock-svc の作成・再要求に、approval-svc の状態とは別の、証明書だけでは作れない証跡を求める（例：lock-tool が受けた LOCK_TOOL_AT（cnf・approval_ref つき）を lock-svc でも検証する、承認の記録に agent-sts の署名を付ける）。または、見送りの行の「開く口」に解錠を書き、60 分の受け入れを見直す | Major | 前提の誤り | q-outside-catalog（中間の CA の行）、op-proof-holder、peer-mtls（証明書の URI で確かめているのは直接の相手で、承認を使ったのが本物の lock-tool かではない） |
| F2 | design.md の 2.2（system-privileges）の「管理用の口（設定の変更）」の行（緊急の変更は当番 1 人の承認で配り、翌営業日に 2 人目が承認）。3.1 の見送りの行「wl-ca の証明書の失効の確かめ」（当番が新しい URI で出し直し、登録と許可リストを替える）。claims.yaml の C-may-act の authoritative_writer（agent-sts の委任の表、configurable_by: platform）と source_system。C-act の on_revoke（クライアントの登録）。各受け手の呼び出し元の許可リスト（lock-svc・approval-svc・通知の基盤・経理） | 委任の表・リソースの表・クライアントの登録と、各受け手の呼び出し元の許可リストは、どれも権限を与える値である（may_act・act の元、証明書だけで受ける口の許可）。通常は 2 人の承認の PR で変える。しかし緊急の変更は「当番 1 人の承認で配り、翌営業日に 2 人目」とあり、変えられる中身を外す変更や、同じワークロードの URI の差し替えに限っていない。wl-ca の行の手順では、新しい URI の追加が前提になっている。このため当番 1 人で、自分の用意したワークロードの URI を、lock-svc や approval-svc の許可リストやリソースの表に足せる。事後の 2 人目の承認までの最大およそ 1 営業日、F1 と同じ解錠の口や、偽の連絡・支払いの依頼の口が開く。ap-1-7 が問う「書ける人は全員がその権限を与えてよい人か」に、緊急の経路が No になる。直すなら、緊急の 1 人の変更は「削除」と「既存の登録の 1 対 1 の URI の差し替え（世代の番号だけを上げる）」に限る。追加は 2 人の承認のままにし、緊急の変更の配布を 5 分以内の警報にする | Major | 候補の漏れ | ap-1-7 |

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| dc-05 | Yes | RAR のメンバーはすべて文字列で、パターン・時刻の書式・拒否してから完全一致で比べる規則が台帳と P4 の 5. にある |
| q-value-vocabulary | Yes | ロールは載せず aoba-pdp が人事の台帳から導く。scope・acr・type は閉じた語彙 |
| q-identifier-choice | Yes | 利用者のキーは aoba-as の sub（UUID）だけ。identifier_properties・on_missing がある |
| ap-1-7 | No | 権限を与える設定（委任の表・許可リスト）を、緊急時は当番 1 人で追加も含めて変えられる（F2） |
| q-freshness-mitigation | Yes | scope は 390 秒で 600 秒以内、在籍・担当は 60 秒で 120 秒以内、承認は 0 秒 |
| q-single-aud-resource | Yes | すべての種別で aud が 1 つ |
| q-no-passthrough | Yes | 委任の表・リソースの表・may_act の照合で、頼める相手と宛先が決まっている |
| q-step-up-path-coverage | Yes | 承認の口は approval-svc の 1 つだけで、ほかの経路は承認の記録を使うだけ |
| ap-2-7 | Yes | act の無い 1 段目の REPAIR_DELEG_AT は agent-sts 宛てで、may_act の主体しか交換できない |
| q-authorize-service-and-user | Yes | すべての呼び出しで mTLS の相手と許可リストを確かめ、トークンの act・cnf とは別に判断する |
| q-agent-short-lived-no-rt | Yes | agent-sts は RT を出さない。ツールのトークンは 300 秒 |
| q-outside-catalog | Yes | 管理用の口・DB の管理者・電話の手配・CA の漏えい・U29・U30 に答えがある（CA の行の中身は F1） |
| q-object-level-authz | Yes | 各ツールが台帳で repair_id と照らして 404 にし、approval-svc は記録の repair_id と承認者の条件で止める |
| q-approval-from-as | Yes | 承認の記録から作った RAR を locations の宛先にだけ載せ、発注 ID・承認 ID に結んで 1 回だけ使う（証明書だけの口は F1） |
| q-operator-act | Yes | 上長・課長は自分のトークンで操作し、代理ログインは無い。DB・lock-svc の管理者の操作は記録に残る |
| q-revocation-delivery | Yes | 重要な操作は 60 秒、下書き・連絡は 390 秒、委任の停止は 330 秒、鍵は 15 分。寿命はこの分数から導いている |
| q-dependency-outage | Yes | 頼る先がどれも止める側に倒れ、REQ-13 の 60 分と 5 分の警報に合う |
| op-proof-holder | 該当なし（開いた問い） | ツールのトークンと APPROVAL_AT は持ち手と鍵の持ち主が同じ。証明書だけの口では鍵しか見ていない（F1） |
| op-source-change | 該当なし（開いた問い） | 異動を人事の登録から辿った。時間を約束していない区間は登録から確定までで、3.1 にある |
| op-one-time | 該当なし（開いた問い） | 並行・再送・障害のどれでも 1 回だけ通る。同じコードを返す口が証明書だけで守られている点は F1 |
| pa-01 | Yes | repair_id はツールの対象の照合と監査、approval_ref は承認の消費と監査に使い、受け手が列挙されている |
| q-derived-value | Yes | 氏名・連絡先・住所は載せず、sub・repair_id・approval_ref・unit_id は受け手が照合に使う |
| q-variant-comparison | Yes | 送信者制約の見送りは、盗まれたときに開く口と、mTLS のクライアント認証による代わりの守りを比べている |
| q-idp-diff-absorbed | Yes | 外部の IdP は無く、ツールには agent-sts のトークンだけが届く |
| q-original-principal | Yes | 交換の後も sub は担当者で、scope は上流と aoba-pdp のロールの積に絞る |
| q-step-up-by-rs | Yes | 追加の認証を求めるかは、操作を受ける approval-svc が決める（401 insufficient_user_authentication） |
| q-long-running | Yes | 予約はトークンを持ち越さず、実行の時点で在籍・担当・委任の世代・承認を確かめ直す |
| q-copies-outlive | Yes | 予約の記録と監査ログの写しは integrity_until にあり、実行の時点の確かめと変更の記録で止まる |
| q-audit-correlation | Yes | sub・repair_id・approval_ref を全サービスで同じ鍵の HMAC で残し、1 本につなげられる |
