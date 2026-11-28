# レビューの記録：designs/target（あおば住まいサービス 修繕の手配）

- 対象：designs/target/design.md、claims.yaml、token_types.yaml、hops.yaml、catalog_answers.yaml、claim_request_repair_id.md、claim_request_approval_ref.md、schemas/
- 使った問いの 1 枚：sheet.md（抜き取りの種 12。抜き取った行：C-approval-ref・C-repair-id・C-authorization-details）
- 読んだ教材：short_list.md、perspectives.md（重大度の目安）、decision_tree.md、kind_tell.md
- 範囲：優先 1 の 17 問、開いた問い 3 つ、優先 2 の 9 問、さらにの開いた問いのうち op-clock（一部）。op-key-custody・op-requirement-words は手がかりの欄を読んだが、辿り切っていない

## 0. 受け付け（CI の結果と lint の warn）

- ci-result.txt と設計書の 1. は同じ結果：error 0、warn 2、info 24
- warn 2 件は L16（hop H5 の `https://aoba-sumai.example/rar/vendor-order`、hop H8 の `https://aoba-sumai.example/rar/lock-code` の authorization_details が上流 H4 に無い）。書き手の理由は 1. の表にある。「広げる根拠は上流のトークンでなく approval-svc の承認の記録で、広がるのはその 1 件だけ。agent-sts は承認済みの記録からだけ作り、受け手は approval-svc で条件つきで使用済みにする」。理由は通ると判断した（`q-hop-narrowing`。上流の REPAIR_DELEG_AT は承認より前に出るので、上流に載せる手段が無い）
- lint を通すために宣言を曲げた跡（`q-lint-workaround`）：hops の upstream（H5〜H8 は H4、H11 は H10、H12 は H2）は図と合う。寿命はどれも上流以下。跡は見つからなかった

## 1. 性質の表の確かめ（段 1）

| 性質 | sheet の判定 | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 合う（C-repair-id・C-approval-ref。名前空間つき） |
| 個人情報を載せる | 当たる | 合う（C-sub・C-repair-id・C-authorization-details が「個人情報」） |
| 発行者が複数 | 当たる | 合う（aoba-as・agent-sts。どちらも組織が作る発行者） |
| 交換・作り直し | 当たる | 合う（H3・H5〜H9・H11・H12 が exchange） |
| 委任 | 当たる | 合う（C-act・C-may-act、max_delegation_depth 2） |
| 操作ごとの承認 | 当たる | 合う（C-authorization-details、H5・H8） |
| マルチテナント | 当たらない | 合う。組織は 1 つで、物件のオーナーごとにもデータを分けない（lite_criteria の reason）。図にもテナントの境界は無い |
| トークンの値を DB の層まで運ぶ | 当たらない | 合う。発注の台帳には order-tool・order-scheduler が自分の DB アカウントで接続し、トークンを渡さない（2. の表のデータ層の行、9.1 の DB の層の表） |
| 認証の強さ・新しさ | 当たる | 合う。ただし sheet の読んだ欄の「acr・amr・auth_time」の amr は却下の行（C-amr）で、採用しているのは acr と auth_time だけ（sheet の記述の誤り。設計の指摘ではない） |
| 送信者制約を選んだ | 当たる | 合う（ツールのトークン 4 種と APPROVAL_AT が mtls） |
| 送信者制約を見送った | 当たる | 合う（CONSOLE_AT・CONSOLE_RT、REPAIR_DELEG_AT も none） |
| 長時間・非同期 | 当たる | 合う（ORDER_TOOL_AT の long_running、U13 が該当、H13・H14） |

「当たらない」とされた性質は、実際にも無い。足す問いは無い。

## 2. 6. の「要る」問いと判断の木（段 2）

| ユースケース・問い | 判断の木の節 | 設計の仕組み | 比べた結果 |
| --- | --- | --- | --- |
| UC1・UC2 の q-sub／q-actor | keep-sub-exchange | sub を保って交換し、act の最も外側を今の行為者にする。受け手は最も外側の act.sub だけを許可リストに当て、内側の act は記録だけ（C-act の enforced_at、H5〜H8・H11 の validates） | 合う。入れ子の act を許可に使う箇所は無い |
| UC3 の q-actor | keep-sub-exchange（本人の操作） | client_id が repair-console で act が無いこと | 合う |
| UC4 の q-sub／q-actor | keep-sub-exchange | トークンを使わず、order-scheduler が予約の記録の sub で aoba-pdp・修繕依頼の台帳・approval-svc を実行の時点で引き直す | 木の既定（ワーカーが自分の ID で交換し直す）から外れるが、3. と 3.1 に外した理由・同じ出どころからの確かめ・試験がある。目的（実行の時点で利用者の状態から決める）には答えている |
| q-peer（全 UC） | peer-mtls | wl-ca の証明書の mTLS（URI の SAN）。トークンのクレームで代えていない | 合う |
| q-txn（全 UC） | txn-tctx | Txn-Token を却下し、修繕依頼 ID（C-repair-id）を対象の照合と監査の鍵にする。取引の内容の固定は authorization_details で行う | 問いは「どの修繕依頼か」で、repair_id が答える。却下の理由（何日もまたぐ単位で txn の意味と違う）も台帳にある。不一致ではない |
| q-authorized（UC1・UC3・UC4） | rar-vs-custom | scope（粗い）＋ authorization_details（type は自組織の URI、宛先ごとに 1 type）＋ approval_ref。併用の分担は M_authz_pdp の 4. に書いてある | 合う |
| q-resource | （existing-claim-first） | aud は 1 つ、resource（RFC 8707）は 1 つ | 合う |
| q-holder | existing-claim-first（cnf） | ツールのトークン・APPROVAL_AT は cnf の x5t#S256。REPAIR_DELEG_AT は may_act と mTLS の相手の URI の照合で代える（3.1 の見送り） | 鍵でなく ID（URI）での束縛。見送りの理由はあるが、前提に弱い点がある（指摘 F5） |
| q-still-valid（寿命） | lifetime-by-situation | 重要な操作は短命＋都度の判定（aoba-pdp・approval-svc）、ワークロードに RT なし、非同期は実行の時点で拒否 | 合う |

目的と仕組みの不一致は見つからなかった。

## 3. 優先 1 の問いへの答え（段 3）

- dc-05：Yes。authorization_details のメンバーはすべて文字列で、order_id・vendor_id・unit_id は正規表現、amount は 10 進の文字列、not_before・not_after は 1 つの書式に固定し、受け手は書式の違う値を拒否してから完全一致で比べる（C-authorization-details の description・value_normalization、付録 D の P4 の 5.）。生成のスキーマが中の型を表さないことは 3.1 に見送りとして書かれ、共通部品の試験で補う
- q-value-vocabulary：Yes。ロール・グループは載せず（C-roles・C-groups は却下）、aoba-pdp が人事の台帳のコードから導く。scope・acr の語彙は閉じていて、発行者ごとに受け手が受け入れる iss が 1 つに固定されている
- q-identifier-choice：Yes。利用者のキーは aoba-as の sub（UUID）だけで、agent-sts は写すだけ。sub・client_id・repair_id・approval_ref の行に identifier_properties と on_missing がある。社員番号は aoba-pdp の中の結合の鍵で、トークンにも受け手の照合にも出ない
- ap-1-7：Yes（抜き取りの 3 行）。トークンに書くのは agent-sts だけ。元のデータの書き手は、承認の記録は承認の画面の承認者（APPROVAL_AT・追加の認証）と order-tool・lock-tool の依頼の登録、修繕依頼の担当は課長だけ、委任の欄は担当者だけ、部屋は受付の作成時だけ。DB の管理者の直接の書き込みは、変更の記録の表と毎日の突き合わせ、予約は実行の前の検出（3.1）
- q-freshness-mitigation：Yes。C-authorization-details は許容 0 秒に対し、受け手が approval-svc で条件つきで使用済みにする（キャッシュなし）。C-repair-id・C-approval-ref は値が変わらず、担当・委任・承認の状態は都度引く。要求に数値がある（REQ-05「直ちに」、REQ-08 の 2 分・10 分、REQ-09 の 10 分）
- q-single-aud-resource：Yes。どの種別も aud は 1 つ。ツールは配列に別の値があれば拒否する
- q-no-passthrough：Yes。交換するのは agent-sts だけで、委任の表（may_act）とクライアントごとのリソースの表で、頼める相手と宛先が決まる。scope は上流・宛先の操作・aoba-pdp のロールの積
- q-step-up-path-coverage：Yes。追加の認証が要るのは承認と手作業の発注の事後の確認だけで、入口は APPROVAL_AT を受ける approval-svc の 1 つ。エージェント・予約の経路は承認の記録を使うだけで、承認の操作に届かない（付録 B）
- ap-2-7：Yes。act の無いトークンでエージェントが持つのは 1 段目の REPAIR_DELEG_AT だけで、宛先は agent-sts、交換できるのは may_act の主体だけ。交換で出るツールのトークンには必ず act が入る
- q-authorize-service-and-user：Yes。すべての呼び出しで、呼ばれる側が mTLS の相手の証明書の URI を許可リストで照合する（q-peer の channel、各ホップの validates）
- q-agent-short-lived-no-rt：Yes。agent-sts は RT を出さず、エージェントが持つ種別はどれも 300 秒
- q-outside-catalog：Yes。outside_enumeration に 10 の場面（承認の競合、分割の発注、電話の手作業、委任の世代、管理用の口、wl-ca など）、U29（旧経路なし）、U30（試験の口を本番に持たない、配備前の検査）が答えられている
- q-object-level-authz：**No**。送信の相手・発注・部屋・承認は修繕依頼と照合して止まるが、contact-tool の「返信の読み取り」（tenant.message:read）は scope だけで、読む対象が repair_id の修繕依頼のものかを照合する記述がどこにも無い（指摘 F1）
- q-approval-from-as：Yes。承認は repair-console の画面で人が行い、依頼の内容は order-tool・lock-tool が自分の記録から登録する。agent-sts は承認済みの記録からだけ authorization_details を作り、locations の宛先にだけ載せる。受け手は承認の記録の発注 ID・修繕依頼・担当者と、自分が locations であることを確かめる
- q-operator-act：Yes。代理ログインは作らず、上長・運用者は自分のログインで操作する。予約の実行は order-scheduler を行為者として記録し、DB の管理者の書き込みは変更の記録に残る（2.2）
- q-revocation-delivery：Yes。重要な操作は aoba-pdp で最悪 60 秒（REQ-08 の 2 分の内側）、下書き・連絡は最悪 390 秒、委任の停止は 330 秒（REQ-09 の 10 分の内側）、承認の取り下げは 0 秒、解錠のコードの取り消しは 15 分の目標。寿命の 300 秒は 10 分から導いてある（5.1）
- q-dependency-outage：Yes。aoba-as・aoba-pdp・修繕依頼の台帳・approval-svc・鍵が止まったときの倒し方は 4. の表と 3.1 にあり、どれも止める側。REQ-13 の 60 分と、5 分の警報（付録 A）で合わせている

## 4. 開いた問い（段 4）

### op-proof-holder

辿った範囲：C-cnf の enforced_at、種別の holder・sender_constraint、H2〜H12 の validates、付録 D の M_sender_constraint の 4.、3.1 の wl-ca の 2 行。

| 箇所 | トークンを持つ者 | 確かめる鍵（ID） | 合うか |
| --- | --- | --- | --- |
| ツール 4 つ（H5〜H8・H11） | 交換を求めたエージェント | cnf の x5t#S256 ＝ 交換を求めた者の証明書の拇印 | 合う |
| approval-svc（H12） | repair-console | cnf ＝ repair-console の証明書 | 合う |
| agent-sts（H2、CONSOLE_AT） | repair-console | cnf なし。クライアント認証の mTLS が repair-console | 合う（鍵でなくクライアント認証） |
| agent-sts（H4・H10、REPAIR_DELEG_AT） | repair-agent・visit-subagent | cnf なし。may_act.sub の URI と mTLS の相手の URI | 鍵ではなく URI で照合（指摘 F5） |

気づいたこと：
- 証明書の更新（24 時間、残り 8 時間）では、共通のクライアント部品が証明書とトークンを組で持ち、古い組は古い接続で使い切るので、束縛したトークンが食い違わない
- REPAIR_DELEG_AT は鍵に束縛されず、may_act の URI で照合する。URI は証明書を替えても変わらない（3.1 で拇印でなく URI を持つと決めている）。そのため、3.1 の「wl-ca の中間の CA の鍵が漏れても、トークンの要る口は REPAIR_DELEG_AT かツールのトークンも要るので開かない」は、REPAIR_DELEG_AT が漏れないことを前提にしている。一方で cnf の理由（C-cnf の rationale）は「エージェントの実行基盤は外からの入力を読むのでトークンが漏れる前提にする」としている。漏れた REPAIR_DELEG_AT と、偽の repair-agent の URI の証明書がそろうと、agent-sts は偽の証明書に束縛したツールのトークンを出す（指摘 F5）

### op-source-change

選んだ出来事：異動で修繕課から外れる（修繕担当のロールが外れる）。

辿った経路：人事部の担当者が人事システムで登録 → 人事部の承認者がもう 1 人で承認して確定（REQ-08 の起点。登録から確定までは人事部の手順書で当日 2 時間以内、3.1 の見送りの行で月 1 回の報告）→ aoba-pdp が sub から aoba-as の社員番号の属性を引き（60 秒キャッシュ）、その社員番号で人事の台帳の API を引く（60 秒キャッシュ）→ agent-sts は交換ごとに scope を絞り直し、重要な操作のツールと approval-svc は呼び出しごとに aoba-pdp を引く。

気づいたこと：
- ロールを手で付ける口は aoba-pdp に無く、導き方の規則は設定のリポジトリの PR（2 人の承認）だけで変わる。図に無い書き込みの経路は見つからなかった
- 時間を誰も約束していない区間は、登録から確定まで（人事部）だが、3.1 に理由と点検がある
- 社員番号の属性（sub と社員番号の対応）は hr-sync が 5 分ごとに写す値で、9.2・2.2 は「hr-sync の遅れは REQ-08 の判断に入らない」とする。異動・退職では社員番号が変わらないのでこの主張は成り立つ。ただ C-sub の not_meaning は「社員番号は人事の台帳で変わりうる」としており、社員番号が変わる出来事（付け直し）が起きると、aoba-pdp が古い対応で人事の台帳を引く区間が hr-sync の周期だけ残る。権限が外れる向きの出来事ではないので、指摘にはしなかった（社員番号が付け直されうるか、再利用されうるかは書いておくとよい）

### op-one-time

辿った値：承認（approval_ref）、解錠のコード（承認 ID）、連絡の下書きの ID、予約の記録、ログアウトトークンの jti、認可コード。

| 場面 | 承認（発注） | 解錠のコード | 予約の実行 |
| --- | --- | --- | --- |
| 並行の 2 件 | approval-svc の原子的な条件つきの更新で片方だけ成功（P4 の 5.） | 条件つきの更新で片方、lock-svc は承認 ID ごとにコードを 1 つ | 「予約→確定」と「予約済み→使用済み」がどちらも条件つきの更新 |
| 通信が切れた後の再送 | 同じ発注 ID に前の結果を返す。発注の台帳の「下書き→確定」も条件つき | 同じ承認 ID に同じコード。通知は「承認 ID と送信の回」で重複を捨てる | 次の回に同じ発注 ID で再試行 |
| 記録先の障害 | approval-svc が止まれば拒否 | 同じ | 拒否して予約を取り消し、担当者に知らせる |
| 正しい 1 回を失わないか | 使用済み・未確定のまま確定できない発注は、order-tool が下書きの取り消しと同時に承認を失効させ、新しい発注 ID で依頼し直す | 同じ承認で送り直せる（3 回まで） | — |

気づいたこと：
- 2 回通る経路は見つからなかった
- order-scheduler の経路で、使用済みにした後に実行の確かめ直しが通らず予約を取り消した場合、承認を「使用済み・未確定」から閉じる手順は、order-tool の経路（P4 の 5.）ほどはっきり書かれていない。発注 ID に結んであるので 2 回目には使えず、安全側の抜けではない（指摘にはしない）
- 解錠のコードの送り直しの「3 回まで」の数をどこで原子的に数えるかは書いていない。通知の基盤が「承認 ID と送信の回」で重複を捨てるので、同じ番号に同じコードが多く送られる以上のことは起きない（指摘にはしない）

## 5. 優先 2 の問い（段 5）

- pa-01：Yes。repair_id・approval_ref の 25 問の問 1 に受け手ごとの使い道があり、usage は identifier。表示用の値（name）で認可していない
- q-derived-value：Yes。sub・repair_id は受け手のすべてが照合に使う。authorization_details の部屋と時間帯は lock-code の type だけで、LOCK_TOOL_AT にだけ載る。入居者の連絡先・住所・解錠コードは載せない
- q-variant-comparison：Yes。CONSOLE_AT・CONSOLE_RT・REPAIR_DELEG_AT の送信者制約の見送りは、開く攻撃と代わりの守り（mTLS のクライアント認証、may_act）と確かめ方を 3.1 で比べている。ただし REPAIR_DELEG_AT の比べ方に弱い点がある（F5）
- q-idp-diff-absorbed：Yes。ツールと approval-svc は agent-sts のトークンだけを受け、aoba-as のトークンはツールに届かない
- q-original-principal：Yes。交換の後も sub は担当者で、scope は上流の部分集合。エージェント自身の権限（client credentials）を持たない
- q-step-up-by-rs：Yes。追加の認証を求めるのは approval-svc で、401 insufficient_user_authentication を返す
- q-long-running：Yes。予約はトークンを持ち越さず、実行の時点で在籍・ロール・担当・委任の世代・行為者の登録・承認を引き直す
- q-copies-outlive：Yes。予約の記録（integrity_until に書き手と境界）、監査ログ（鍵つきのハッシュ、3 年）、aoba-pdp の 60 秒キャッシュ。長く開いた接続（U23）は無い
- q-audit-correlation：Yes。sub・repair_id は全サービスで同じ鍵・同じ正規化のハッシュ、approval_ref は値のまま、agent-sts が元の jti と出した jti を結ぶ

さらにの開いた問い：
- op-clock（一部を辿った）：M_token_validation の 6. は、auth_time と今、承認の期限、not_before・not_after、予約の時刻を「時刻を比べるほかの箇所」として数える。ところが agent-sts が REPAIR_DELEG_AT の iat（agent-sts の時計）と委任の欄の世代の開始の時刻（修繕依頼の台帳の時計）を比べる箇所が、この一覧に無い。さらに境界の扱いが台帳とホップで食い違う（指摘 F2）
- op-key-custody・op-requirement-words：辿っていない（時間の都合）

## 6. 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | claims.yaml の C-repair-id の enforced_at（service: contact-tool）・C-scope の enforced_at（service: contact-tool）、hops.yaml の H6・H11 の validates.checks、design.md の付録 D「M_authz_pdp：3. オブジェクト単位の認可」の連絡の相手の行、token_types.yaml の CONTACT_TOOL_AT の purpose。問い：q-object-level-authz | contact-tool の「返信の読み取り」（tenant.message:read）には、scope の確かめしか書いていない。読む対象（返信・やり取り）が repair_id の修繕依頼のものかを照合する記述が、台帳にもホップにもオブジェクト単位の表にも無い（照合が書いてあるのは送信の相手だけ）。このままだと、エージェント（入居者の依頼の文を読むので、紛れた指示で動きうる）が別の修繕依頼の返信の ID を指定して、担当でない入居者の返信（個人情報）を読める。REQ-03（割り当てられた修繕依頼だけ）と REQ-12 に反する。visit-subagent の「入居者だけ」の制限も送信にしか書かれておらず、協力会社の窓口からの返信を読めるかが決まっていない。対策：返信の読み取りでも、対象が repair_id の修繕依頼のものか（visit-subagent なら入居者とのやり取りか）を確かめ、違えば 404 にすることを enforced_at・validates・M_authz_pdp の 3. に足す | Major | 候補の漏れ | q-object-level-authz |
| F2 | claims.yaml の C-repair-id の enforced_at（service: agent-sts。「iat が…開始の時刻より前なら拒否」）、hops.yaml の H4・H10 の validates.checks（「iat が今の委任の世代の開始の時刻より後」）、design.md の付録 D「M_token_validation：6. 時刻」の「時刻を比べるほかの箇所」の行。問い：op-clock | 委任を止めて有効にし直す前の REPAIR_DELEG_AT を拒否する比べ方が、台帳は「前なら拒否」（同じ秒は通す）、ホップは「後なら通す」（同じ秒は拒否）で食い違う。iat は秒の単位なので、止める直前に出したトークンが同じ秒の有効化を越えて通るかどうかが、どちらを実装するかで変わる。また、比べる 2 つの時刻は agent-sts の時計と修繕依頼の台帳の時計で、M_token_validation の 6. の一覧に入っていない。予約の側（H13）は時刻でなく世代の番号で比べているので、REPAIR_DELEG_AT にも世代の番号を載せる（または agent-sts が台帳の世代の番号を交換の記録と比べる）か、少なくとも境界と時計を 1 つに決めて 6. の一覧に足す。NTP のずれを 1 秒で外す運用があり、影響は小さい | Minor | 実装とのずれ | op-clock |
| F3 | hops.yaml の H6・H7・H8・H11 の validates.checks、claims.yaml の C-client-id の enforced_at（service: contact-tool・payment-tool・lock-tool） | 台帳は contact-tool・payment-tool・lock-tool でも「client_id が act の最も外側と同じエージェント（クライアントの登録の表で対応を引く）」を確かめるとするが、ホップの validates にこの確かめがあるのは H5（order-tool）だけで、H6・H7・H8・H11 には無い。同じ確かめについて 2 か所の記述が食い違い、ホップの表から実装すると抜ける。ホップの validates にそろえて書く | Minor | 実装とのずれ | q-agent（questions） |
| F4 | claims.yaml の C-auth-time の consumers・enforced_at、C-acr の consumers・enforced_at | auth_time も acr も authoritative_writer に「③ agent-sts（CONSOLE_AT から写すだけ）」があり、H12 で APPROVAL_AT に写す。C-acr は consumers に agent-sts を入れて enforced_at に「写すだけ」を書くが、C-auth-time は consumers にも enforced_at にも agent-sts が無い。agent-sts が CONSOLE_AT の auth_time を読む受け手であることが台帳から漏れ、写すときの扱い（値を作らない・欠けたら拒否）が決まっていない。C-acr と同じ行を足す | Minor | 実装とのずれ | q-auth-strength（questions） |
| F5 | design.md の 3.1 の見送りの行「wl-ca の中間の CA の鍵の漏えいを、60 分より早く塞ぐこと」と「REPAIR_DELEG_AT の送信者制約」、付録 D「M_token_validation：8.」の wl-ca の行、token_types.yaml の REPAIR_DELEG_AT の note、claims.yaml の C-cnf の rationale。問い：op-proof-holder・q-variant-comparison | 3.1 は「中間の CA の鍵が漏れても、トークンの要る口は REPAIR_DELEG_AT かツールのトークンも要るので開かない」とする。しかし REPAIR_DELEG_AT は鍵に束縛されず、agent-sts は may_act の URI と mTLS の相手の URI だけを照合する（URI は証明書を替えても変わる値ではない）。C-cnf の理由は「エージェントの実行基盤は外からの入力を読むので、トークンが漏れる前提にする」としており、REPAIR_DELEG_AT は同じ実行基盤のメモリにある。漏れた REPAIR_DELEG_AT（最悪 330 秒）と偽の repair-agent の URI の証明書がそろえば、agent-sts は偽の証明書に束縛したツールのトークンを出し、60 分の間に下書き・連絡・承認の要らない発注・支払いの依頼ができる。「開かない」は、REPAIR_DELEG_AT が漏れないという、ほかの節と食い違う前提に立っている。開く口の一覧にこの組み合わせを入れるか、REPAIR_DELEG_AT を渡す相手の証明書の拇印に束縛する（may_act に拇印を入れるなど）案と比べて、見送りの理由を書き直す | Minor | 理由の不備 | op-proof-holder |

重大度ごとの件数：Blocker 0、Major 1、Minor 4

## 7. 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| dc-05 | Yes | authorization_details のメンバーはすべて文字列で書式が固定され、受け手は書式を確かめてから完全一致で比べる |
| q-value-vocabulary | Yes | ロール・グループを載せず aoba-pdp が人事の台帳のコードから導き、scope・acr の語彙は閉じている |
| q-identifier-choice | Yes | 利用者のキーは aoba-as の sub（UUID）だけで、識別子の行に identifier_properties と on_missing がある |
| ap-1-7 | Yes | 抜き取った 3 行の値をトークンに書くのは agent-sts だけで、元のデータの書き手は課長・担当者・承認者と記録された口に限られる |
| q-freshness-mitigation | Yes | 承認の状態は都度の条件つきの更新（0 秒）、担当・委任・ロールは都度引き、要求の数値の内側に収まる |
| q-single-aud-resource | Yes | どの種別も aud は 1 つで、ツールは配列に別の値があれば拒否する |
| q-no-passthrough | Yes | 交換は agent-sts だけで、委任の表とリソースの表と scope の積で相手・宛先・範囲が決まる |
| q-step-up-path-coverage | Yes | 追加の認証が要る操作の入口は approval-svc の 1 つで、代理・予約の経路は承認の操作に届かない |
| ap-2-7 | Yes | act の無い 1 段目の REPAIR_DELEG_AT は宛先が agent-sts だけで、交換で出るツールのトークンには必ず act が入る |
| q-authorize-service-and-user | Yes | すべての呼び出しで呼ばれる側が mTLS の相手の URI を許可リストで照合する |
| q-agent-short-lived-no-rt | Yes | agent-sts は RT を出さず、エージェントの種別はどれも 300 秒 |
| q-outside-catalog | Yes | outside_enumeration の 10 の場面と U29・U30 の回答で、図に無い口と試験の口に答えている |
| q-object-level-authz | No | contact-tool の返信の読み取りに、対象が repair_id の修繕依頼のものかの照合が無い（F1） |
| q-approval-from-as | Yes | 承認は記録から agent-sts が作り、locations の宛先だけに載せ、受け手が記録の発注 ID・修繕依頼・担当者と照合する |
| q-operator-act | Yes | 代理ログインが無く、上長・運用者は自分の ID で操作し、予約の実行は order-scheduler として記録する |
| q-revocation-delivery | Yes | 重要な操作は 60 秒、そのほかは 390 秒、委任の停止は 330 秒で、寿命は 10 分から導いてある |
| q-dependency-outage | Yes | 頼る先ごとに止める側に倒すと決め、REQ-13 の 60 分と 5 分の警報で合わせている |
| op-proof-holder | No | ツールと承認は鍵で束縛するが、REPAIR_DELEG_AT は URI の照合で、中間の CA の漏えいの見送りの理由が漏れない前提に立つ（F5） |
| op-source-change | Yes | 異動を人事の台帳の確定から受け手まで辿れ、図に無い書き込みの口は見つからなかった（社員番号の付け直しの扱いは書いておくとよい） |
| op-one-time | Yes | 承認・解錠・連絡・予約はどれも業務の ID の条件つきの更新で、並行・再送・障害のどれでも 2 回通らない |
| pa-01 | Yes | repair_id・approval_ref の 25 問の問 1 に、受け手ごとに決めることが書いてある |
| q-derived-value | Yes | 個人情報の行は、それを照合に使う受け手のトークンにだけ載る |
| q-variant-comparison | Yes | 送信者制約の見送りに開く攻撃・代わりの守り・確かめ方を比べてある（REPAIR_DELEG_AT の弱い点は F5） |
| q-idp-diff-absorbed | Yes | 内側の受け手は agent-sts のトークンだけを受け、aoba-as の値を直接読まない |
| q-original-principal | Yes | 交換の後も sub は担当者で、scope は上流の部分集合 |
| q-step-up-by-rs | Yes | 追加の認証を求めるかは approval-svc が決めて 401 を返す |
| q-long-running | Yes | 予約はトークンを持ち越さず、実行の時点で在籍・委任の世代・承認を引き直す |
| q-copies-outlive | Yes | 予約の記録・監査ログ・aoba-pdp のキャッシュの残る期間と止め方が書いてある |
| q-audit-correlation | Yes | sub・repair_id は全サービスで同じ鍵のハッシュ、approval_ref は値のままで、jti を交換で結ぶ |
| op-clock | No | REPAIR_DELEG_AT の iat と委任の世代の開始の時刻の比較が、時計の一覧に無く、境界の扱いが台帳とホップで食い違う（F2） |
| op-key-custody | 該当なし | 時間の都合で辿っていない（答えていない） |
| op-requirement-words | 該当なし | 時間の都合で辿っていない（答えていない） |
