# レビュー：designs/target（あおば住まいサービス 修繕の手配、Full）

読んだもの：design.md（1.〜3.1、4. の agent-sts の要求の表、5.、6.、9.、12.、付録 A・B、付録 D の P4 の 1.〜9.）、claims.yaml（C-sub・C-scope・C-act・C-may-act・C-cnf・C-authorization-details・C-repair-id・C-approval-ref）、token_types.yaml（REPAIR_DELEG_AT〜APPROVAL_AT）、hops.yaml（全行）、catalog_answers.yaml（lite_criteria・outside_enumeration・questions・U13・U29・U30）、schemas/ORDER_TOOL_AT.*、ci-result.txt、sheet.md、kind_tell.md、decision_tree.md。

## 段 0：CI の結果（lint）

- error 0、warn 2（L16 の hop H5・H8：authorization_details が上流の H4 に無い）。設計書の 1. に理由がある
- 理由は通ると判断した。足す authorization_details は上流のトークンではなく approval-svc の承認済みの記録という別の権限の元から作られ、広がるのは 1 件の操作の分だけ。受け手は approval-svc で条件つきの使用済みにして確かめる（C-authorization-details・C-approval-ref の enforced_at）。lint の宣言の側を曲げた跡（upstream を外す・名前を変える）は見当たらない

## 段 1：性質の表（sheet.md の 1.）を図と要求に照らす

| 性質 | 表の判定 | 確かめた結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 合う（C-repair-id・C-approval-ref。名前空間 https://aoba-sumai.example/claims/） |
| 個人情報 | 当たる | 合う（C-sub・C-repair-id・C-authorization-details が個人情報） |
| 発行者が複数 | 当たる | 合う（aoba-as と agent-sts） |
| 交換・作り直し | 当たる | 合う（H3・H5〜H9・H11・H12） |
| 委任 | 当たる | 合う（act・may_act、深さ 2） |
| 操作ごとの承認 | 当たる | 合う（vendor-order・lock-code） |
| マルチテナント | 当たらない | 合う（組織は 1 つで、オーナーごとにデータを分けない。REQ にもテナントの区分は無い） |
| DB の層までトークン | 当たらない | 合う（発注の台帳には order-tool・order-scheduler が自分の DB アカウントで接続。lifecycle-db-connection も「無い」） |
| 認証の強さ・新しさ | 当たる | 合う（REQ-07、付録 B） |
| 送信者制約を選んだ | 当たる | 合う（ツールのトークン 4 種と APPROVAL_AT が mtls） |
| 送信者制約を見送った | 当たる | 合う（CONSOLE_AT・CONSOLE_RT・REPAIR_DELEG_AT が none。3.1 に理由） |
| 長時間・非同期 | 当たる | 合う（予約の発注。REQ-10、H13・H14） |

「当たらない」の性質が実はある、ということは無かった。

## 段 2：6. の「要る」問いを判断の木と比べる

| 問い | 判断の木の節 | 設計の仕組み | 比べた結果 |
| --- | --- | --- | --- |
| q-sub | keep-sub-exchange | agent-sts が subject_token の sub を写すだけ。act に行為者 | 合う |
| q-actor | keep-sub-exchange | 最も外側の act.sub を mTLS の相手と照合し、操作ごとの許可リストに当てる。内側の act は記録だけ（C-act の enforced_at、H5〜H8・H11） | 合う（入れ子の act を許可に使っていない） |
| q-peer | peer-mtls | wl-ca の証明書の mTLS（end_to_end）。呼ばれる側の許可リスト | 合う |
| q-txn | txn-tctx | Txn-Token は却下。repair_id で相関・対象の照合、取引の内容は authorization_details | 合う（TXN_TOKEN の却下の理由がある。内容の固定は RAR と受け手の照合で行う） |
| q-authorized | rar-vs-custom | scope（操作の種類）＋ authorization_details（承認の内容）＋ approval_ref（記録の参照）。宛先ごとに type を 1 つに絞る | 合う（併用の分担が台帳に書いてある） |
| q-resource | （lifetime・P4 の tool-scopes） | aud はツールごとに 1 つ | 合う |
| q-holder | existing-claim-first（cnf） | cnf の x5t#S256 | 合う |
| UC4 の q-sub・q-authorized（予約の実行） | keep-sub-exchange・lifetime-by-situation | 交換し直さず、order-scheduler が判断の元の記録を実行の時点で引き直す（3. に既定からの逸脱として記載） | 逸脱そのものは理由と代わりの確かめがあり受け入れられる。ただし委任の停止の確かめ方が要る問いに答えていない（指摘 F1） |

## 段 3：優先 1 の問いへの答え（1 行ずつ）

- dc-05：Yes。authorization_details のメンバーはすべて文字列で、金額は 10 進の文字列、時刻は書式を 1 つに固定し、書式違いを拒否してから完全一致で比べる。スキーマで表せない点は 3.1 に見送りとして書き、共通の部品の試験で確かめる
- q-value-vocabulary：Yes。ロール・グループはトークンに載せず（却下）、aoba-pdp が人事の台帳から導く。scope と RAR の type は閉じた語彙で持ち主がいる。発行者は 2 つあるが、ツールと approval-svc は agent-sts の iss だけを受けるので、同じ文字列を別の発行者の意味で通すことはない
- q-identifier-choice：Yes。利用者のキーは sub（UUID、stable・reassignable false）。社員番号は aoba-pdp の内側の対応で、トークンでは照合に使わない。repair_id・approval_ref にも identifier_properties と on_missing がある
- ap-1-7：Yes（見送りを含む）。元のデータの書き手（人事部の 2 人の手順、課長の担当の割り当て、担当者の委任の欄、hr-sync の証明書、DB の管理者、協力会社の窓口）を 2.2・3.1・9.2 で数えている。DB の管理者は変更の記録の表と毎日の突き合わせで抑える
- q-freshness-mitigation：Yes。要求の数値（REQ-08 の 2 分・10 分、REQ-09 の 10 分、REQ-05 の即時）があり、9.2 の対策の最悪値（60・390・330・0 秒）が内側に入る。対策を行う者（agent-sts・各ツール・aoba-pdp）も書いてある
- q-single-aud-resource：Yes。どのアクセストークンも aud は 1 つ
- q-no-passthrough：Yes。クライアントごとのリソースの表、委任の表、resource は 1 つ、authorization_details は locations と同じ宛先にだけ載せる
- q-step-up-path-coverage：一部 No。承認の操作の入口は承認の画面の 1 つで、エージェントや予約の経路からは届かない。ただし REQ-13 の停止の後に 10 万円を超える手作業の発注を「別の課長が承認の画面で事後に確かめる」操作が、付録 B・H12・approval-svc の enforced_at のどれにも無い（F3）
- ap-2-7：Yes。act の無いトークンでエージェントが持つのは 1 段目の REPAIR_DELEG_AT だけで、宛先は agent-sts、交換は may_act の主体だけ。APPROVAL_AT は repair-console にしか出ない
- q-authorize-service-and-user：Yes。すべての受け手が mTLS の相手を許可リストと照合し、act.sub・cnf と突き合わせる
- q-agent-short-lived-no-rt：Yes。agent-sts は RT を出さず、ツールのトークンは 300 秒、client_credentials も無い
- q-outside-catalog：Yes（記述の誤りが 1 つ）。管理用の口・試験用の口（U30）・移行の旧経路（U29）・停止中の電話の手配・CA の漏えいを扱っている。ただし outside_enumeration の件数の記述が中身と合わない（F4）
- q-object-level-authz：Yes。各ツールは repair_id とデータの層（発注の修繕依頼・部屋・連絡の相手）を照合し、approval-svc は画面で開いた修繕依頼と承認の記録の修繕依頼を比べる
- q-approval-from-as：Yes。承認は approval-svc の記録と照合して条件つきで使用済みにする。操作（order_id・金額・部屋・時間帯）と宛先（locations、aud）に結ばれ、依頼の中身はツールが自分の記録から作る
- q-operator-act：Yes。代理のログインは無い。上長・課長・運用者は自分の sub で動き、order-scheduler は行為者として記録される
- q-revocation-delivery：一部 No。退職・剥奪（60 秒・390 秒）、ログアウト（330 秒）、鍵（15 分）、証明書（30 分）、CA（60 分）は導かれている。ただし委任の停止のあと委任をもう一度有効にすると、予約した発注が実行される（F1）。発行済みの解錠コードの取り消しの手順が、APPROVAL_AT の範囲では実行できない場合がある（F2）
- q-dependency-outage：Yes。どの依存先が止まっても止める側に倒し、REQ-13 の 60 分と付録 A の 5 分の警報で業務の許す時間に合わせている

## 段 4：開いた問い

### op-proof-holder

- 辿った範囲：C-cnf の enforced_at、token_types の holder・sender_constraint（ツールのトークン 4 種・APPROVAL_AT）、3.1 の証明書の行、9.2 の cnf の行
- 並べた結果：ORDER/PAYMENT/LOCK_TOOL_AT は、持つ者＝repair-agent、鍵＝repair-agent の証明書。CONTACT_TOOL_AT は、交換を求めた者（repair-agent か visit-subagent）の証明書に束縛するので、持つ者と鍵を持つ者が一致する。APPROVAL_AT は、持つ者＝repair-console、鍵＝repair-console の証明書
- 気づき：repair-console が複数の台で動くとき、交換した台と approval-svc を呼ぶ台が同じであることが前提になる（共通のクライアント部品が証明書とトークンを組で持つ、で答えていると読める）。証明書を更新すると、新しい証明書で交換し直す（M_sender_constraint の 4.）。lock-svc は証明書だけでなく approval-svc の使用済みも確かめるので、鍵だけでは解錠のコードが作れない。指摘にはしない

### op-source-change

- 選んだ出来事：異動で修繕課から外れる（修繕担当のロールが外れる）
- 辿った範囲：人事部の担当者が人事システムで登録 → 人事部の 2 人目の承認で確定（REQ-08 の起点）→ aoba-pdp が人事の台帳を直接読む（キャッシュ 60 秒）→ 重要な操作のツールと approval-svc は呼び出しのたびに問い合わせる（最悪 60 秒）→ 下書き・連絡は agent-sts の次の交換で scope から外れる（60＋330＝390 秒）。予約は order-scheduler が実行の時点で aoba-pdp を引く
- 気づき：登録から確定までの区間は、この設計が時間を約束しない区間として 3.1 に見送りで書いてある（人事部の手順で 2 時間、月 1 回の報告）。aoba-pdp のロールは人事の台帳から導くだけで、手で書き換える口が無い。sub と社員番号の対応は hr-sync の証明書だけが書ける。図に無い書き込みの経路は、DB の管理者（3.1 の変更の記録）以外に見つからなかった

### op-one-time

- 辿った範囲：承認（C-approval-ref の条件つきの更新）、予約の承認（予約済み → 使用済み。H14）、解錠のコード（lock-svc が承認 ID ごとに 1 つ、通知の基盤の「承認 ID と送信の回」）、jti（replay_check false。業務の ID で重複を防ぐと 3.1 に書いてある）
- 並行の 2 件：approval-svc の原子的な条件つきの更新で片方だけが成功し、発注は「下書き→確定」の条件つきの更新で 1 回だけ
- 通信が切れた後の再送：同じ発注 ID・同じ承認には前の結果を返す。確定できなくなった下書きは、承認を失効させてから新しい発注 ID で依頼し直す
- 記録先の障害：approval-svc が応答しなければ拒否する
- 正しい 1 回が失われないか：承認を自動で未使用に戻さず、同じ ID で再試行するので失われない
- 気づき：「1 回だけ」の値については問題が見当たらない。ただし予約については「止めた」という出来事が 1 回しか効かない値として扱われておらず、後から委任を有効にすると取り消しが失われる（F1。op-one-time ではなく q-long-running の問題として指摘した）

## 段 5：優先 2 の問い

段 3・4 の後に、下の表のとおり答えた。

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | hops.yaml の H13（validates.checks・note「止められていれば実行せず」）、design.md の 9.1 の「予約の記録」の行（「実行より前に止めたいときは委任を止める」）、付録 D の P4 の 9. の「止める手段」、2.2 の「予約の発注の実行」、token_types.yaml の ORDER_TOOL_AT の long_running、REQ-09 | REQ-09 は「委任をやめたら予約した発注は実行しない」を求めている。しかし order-scheduler が確かめるのは、実行の時点で委任の欄が今「停止」かどうかだけ。担当者が委任を止め、その後に（翌朝の再開などで）同じ修繕依頼の委任をもう一度「有効」にすると、止める前に入れた予約が実行の時点で通ってしまう。設計書自身が予約を取り消す手段として「委任を止める」を挙げている（9.1）ので、止めて再開する使い方は普通に起きる。今の仕組みが答えているのは「今、委任は有効か」で、要るのは「予約の後に委任が止められたか」。直し方の例：委任の欄を停止にするとき、同じトランザクションでその修繕依頼の予約を取り消す。あるいは委任の欄に世代の番号（停止の時刻）を持たせ、予約の記録の世代と比べる。直したら order-scheduler の結合試験に「停止→再開の後の予約が実行されない」を足す | Major | 目的と仕組みの不一致 | q-long-running、lifetime-by-situation（長時間ジョブ・非同期処理）、keep-sub-exchange（非同期の処理の可否を委任の記録から決める）、q-revocation-delivery |
| F2 | design.md の 3.1 の見送りの行「発行した解錠コードを、退職・担当の付け替え…で自動では止めないこと」（課長の手順書の「発行中のコードの一覧」）、claims.yaml の C-repair-id の enforced_at（approval-svc：一覧は担当者か「担当の履歴に無い同じ課の課長」だけ）、C-approval-ref の enforced_at（approval-svc：解錠の取り消しは担当者か課長の APPROVAL_AT）、design.md の 4. の agent-sts の要求の表（APPROVAL_AT は画面で開いた 1 つの修繕依頼についてだけ出す）、REQ-06 | 自動で止めない代わりの守りは、課長が「発行中のコードの一覧」を見て取り消すこと。しかし APPROVAL_AT は 1 つの修繕依頼（repair_id）に限られ、approval-svc はその修繕依頼の記録だけを返す。退職した人や取引を止めた協力会社に関わる発行中のコードを、修繕依頼をまたいで一覧にする口がどこにも無い。さらに、その修繕依頼の担当の履歴にある課長は APPROVAL_AT を得られないので、REQ-06 の「課長が取りやめる」ができない場合がある。見送りの理由が頼っている手順と、承認の口の範囲が食い違っている。直し方の例：課長向けに、修繕依頼をまたいで使用済みで not_after の前の解錠の承認を返す参照の口（と、その口の認可の規則）を足す。取り消しの条件は「同じ課の課長」とし、承認者の条件（担当の履歴に無い）と分ける | Minor | 実装とのずれ | q-revocation-delivery、op-source-change |
| F3 | design.md の 3.1 の見送りの行「発注の台帳の書き込みの口…」（「10 万円を超える手作業の発注は、再開の後に別の課長が承認の画面で事後に確かめる（approval-svc の事後の確認の記録）」）、付録 B の追加認証の表、hops.yaml の H12 の validates、claims.yaml の C-approval-ref の enforced_at（approval-svc） | 事後の確認は承認の画面で行うとあるが、その操作がどこにも定義されていない：付録 B の追加の認証の対象に無い（mfa・300 秒を求めるかが分からない）、H12 と approval-svc の照合の文に「事後の確認の記録」の作り方・approval_ref の扱いが無い、「別の課長」（登録した課長と別人）であることを誰が確かめるかも書いていない。REQ-05 の上長の承認を、停止の後で代わりに満たすための操作なので、承認と同じ条件が掛かるかを決める必要がある | Minor | 候補の漏れ | q-step-up-path-coverage |
| F4 | catalog_answers.yaml の outside_enumeration.answer（「見つかったのは 6 つ」）と found（9 行） | 件数の記述と中身が合わない。どれかを数え落としたのか、後から足した行の記述を直していないのかが読み取れず、カタログの外の場面の点検の範囲が確かめにくい | Minor | 実装とのずれ | q-outside-catalog |
| F5 | claims.yaml の C-sub の enforced_at（contact-tool：「連絡の相手は repair_id の修繕依頼の入居者に限る」）と、C-repair-id の enforced_at（contact-tool：入居者と、その発注の協力会社の窓口。visit-subagent なら入居者だけ）・hops.yaml の H6 の validates | 同じ contact-tool の照合について、2 つの行で連絡の相手の範囲が食い違っている。C-sub の行のとおりに作ると、repair-agent が協力会社の窓口に連絡できなくなり、C-repair-id の行のとおりに作ると C-sub の記述と合わない | Minor | 実装とのずれ | q-object-level-authz |

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| dc-05 | Yes | メンバーはすべて文字列で、正規表現と時刻の書式を固定し、書式の違う値を拒否してから完全一致で比べる |
| q-value-vocabulary | Yes | ロールはトークンに載せず aoba-pdp が人事の台帳から導く。ツールは agent-sts の iss だけを受ける |
| q-identifier-choice | Yes | sub（UUID）・repair_id・approval_ref に identifier_properties と on_missing があり、社員番号はトークンの照合に使わない |
| ap-1-7 | Yes | 元のデータの書き手を数え、2.2・3.1 で口を閉じるか、変更の記録で検出している |
| q-freshness-mitigation | Yes | 要求の数値があり、9.2 の対策の最悪値（60・390・330・0 秒）がその内側に入る |
| q-single-aud-resource | Yes | どの AT も aud は 1 つ |
| q-no-passthrough | Yes | 委任の表とリソースの表で宛先を決め、resource は 1 つ、RAR は locations の宛先だけ |
| q-step-up-path-coverage | No | 承認の経路は 1 つだが、手作業の発注の事後の確認に追加の認証の条件が無い（F3） |
| ap-2-7 | Yes | act の無い 1 段目の REPAIR_DELEG_AT は agent-sts 宛てで、may_act の主体しか交換できない |
| q-authorize-service-and-user | Yes | すべての受け手で mTLS の相手を許可リストと照合し、act.sub・cnf と突き合わせる |
| q-agent-short-lived-no-rt | Yes | agent-sts は RT を出さず、ツールのトークンは 300 秒 |
| q-outside-catalog | Yes | 管理の口・試験の口・移行・停止中の手作業・CA の漏えいを扱っている（件数の記述の誤りは F4） |
| q-object-level-authz | Yes | ツールが repair_id とデータの層を照合し、approval-svc は出どころの違う 2 つの修繕依頼を比べる |
| q-approval-from-as | Yes | 承認は approval-svc の記録で条件つきで使用済みにし、操作の中身と locations・aud に結ぶ |
| q-operator-act | Yes | 代理のログインは無く、運用者・上長は自分の sub、order-scheduler は行為者として記録される |
| q-revocation-delivery | No | 委任の停止の後に再開すると予約が実行される（F1）。課長がコードを取り消せない場合がある（F2） |
| q-dependency-outage | Yes | 依存先ごとに止める側に倒し、REQ-13 の 60 分と 5 分の警報に合わせている |
| op-proof-holder | Yes | どの束縛したトークンも、交換を求めた者（＝持つ者）の証明書に束縛している |
| op-source-change | Yes | 確定から受け手までを辿れる。確定までの区間は 3.1 に見送りとして書いてある |
| op-one-time | Yes | 原子的な条件つきの更新と業務の ID で 2 回通らず、再試行で正しい 1 回も失わない |
| pa-01 | Yes | 採用した行に usage・consumers・enforced_at があり、表示だけの name で認可していない |
| q-derived-value | Yes | 連絡先・住所・コードは載せず（却下）、部屋・時間帯は lock-tool 宛てのトークンだけに載る |
| q-variant-comparison | Yes | 3.・3.1 で、開く攻撃（盗んだ CONSOLE_AT・REPAIR_DELEG_AT）と代わりの守り（mTLS・may_act）を比べている |
| q-idp-diff-absorbed | Yes | ツールには agent-sts のトークンだけが届き、aoba-as のトークンを受けない |
| q-original-principal | Yes | 交換の後も sub は担当者で、scope は上流と aoba-pdp のロールの積に絞る |
| q-step-up-by-rs | Yes | approval-svc が acr と auth_time を自分の時計で確かめ、401 で求める |
| q-long-running | No | 実行の時点で委任の欄の今の状態だけを見るので、停止の後に再開すると予約が実行される（F1） |
| q-copies-outlive | Yes | 予約の記録・lock-svc のコード・承認の記録の残る期間と止め方を 9.1・3.1 に書いている |
| q-audit-correlation | Yes | sub・repair_id は全サービスで同じ鍵のハッシュ、approval_ref は値のまま、jti を交換で結ぶ |
