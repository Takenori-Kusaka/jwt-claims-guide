# レビュー：designs/target（あおば住まいサービス 修繕の手配）

- 読んだもの：designs/target/ の design.md（1.〜13.・付録 B・D）、claims.yaml、token_types.yaml、hops.yaml、catalog_answers.yaml、schemas/LOCK_TOOL_AT.consumer.schema.json。ci-result.txt、sheet.md、short_list.md、perspectives.md（問いの書き方と読み方）、decision_tree.md、kind_tell.md
- 行の抜き取りの種：12（sheet.md のとおり。C-approval-ref・C-repair-id・C-authorization-details）
- lint（設計書の 1. と ci-result.txt）：error 0、warn 2（L16 の H5・H8。authorization_details を上流より広げる）。warn には行ごとの理由がある。理由（承認の記録という別の権限の元から 1 件分だけ足し、受け手が approval-svc で条件つきに使用済みにする）は通ると判断した。宣言を曲げた跡（上流を外す・名前を変える・数値を上限に合わせる）は見つからなかった

## 段 1：性質の表の確かめ

| 性質 | sheet.md | 図・要求に照らした結果 |
| --- | --- | --- |
| 組織独自のクレーム | 当たる | 合う（repair_id・approval_ref が名前空間つき） |
| 個人情報 | 当たる | 合う（C-sub・C-repair-id・C-approval-ref・C-authorization-details が個人情報） |
| 発行者が複数 | 当たる | 合う（aoba-as と agent-sts） |
| 交換・作り直し | 当たる | 合う（H3・H5〜H9・H11・H12） |
| 委任 | 当たる | 合う（act・may_act、深さ 2） |
| 操作ごとの承認 | 当たる | 合う（vendor-order・lock-code） |
| マルチテナント | 当たらない | 合う（組織は 1 つ。オーナーごとに分けない。REQ にもテナントの区分が無い） |
| DB の層まで運ぶ | 当たらない | 合う（2. のデータ層の行：order-tool・order-scheduler は自分の DB アカウント） |
| 認証の強さ・新しさ | 当たる | 合う（REQ-07、C-acr・C-auth-time） |
| 送信者制約を選んだ | 当たる | 合う（ツールのトークン 4 種と APPROVAL_AT が mtls） |
| 送信者制約を見送った | 当たる | 合う（CONSOLE_AT・REPAIR_DELEG_AT が none） |
| 長時間・非同期 | 当たる | 合う（予約の発注、最大 24 時間。U13 が該当） |

「当たらない」とした性質が実際にある、という指摘は無い。

## 段 2：6. の「要る」問いと判断の木の節

| 問い | 判断の木の節 | 設計の仕組み | 合うか |
| --- | --- | --- | --- |
| q-sub・q-actor | keep-sub-exchange | sub を保った RFC 8693 の交換、最も外側の act だけで行為者を照合（入れ子の act は記録だけ。C-act・H5〜H11 の validates） | 合う。UC4 は交換し直さず order-scheduler が判断の元を引き直す（3. と 3.1 に理由。sub を捏造しない） |
| q-peer | peer-mtls | 全経路で wl-ca の証明書の mTLS。act・client_id で代えていない | 合う |
| q-txn | txn-tctx | Txn-Token は使わず repair_id（日をまたぐ業務の ID）。取引の内容の固定は authorization_details が受け持つ | 合う（prior_art_search に txn と違う理由がある） |
| q-authorized | rar-vs-custom | RFC 9396 の type（組織の URI）を宛先ごとに 1 つ。scope は操作、authorization_details は承認の内容と、分担を台帳に書いている | 合う |
| q-holder | （M_sender_constraint） | cnf の x5t#S256 と TLS の相手の照合 | 合う |
| q-resource | （lifetime・aud） | ツールごとに 1 つの aud | 合う |
| q-via・q-user・q-agent | — | 交換の監査ログ、HMAC の同じ鍵 | 合う |

目的と仕組みの不一致は見つからなかった。

## 段 3：優先 1 の問いへの回答（要点）

クレームの行（C-approval-ref・C-repair-id・C-authorization-details）：
- dc-05：メンバーはすべて文字列で、金額は 10 進の文字列、時刻は 1 つの書式に固定、受け手は書式違いを拒否してから完全一致で比べる。発行側のスキーマが内側の型を表さない点は 3.1 に見送りとして書き、共通の部品の試験で補っている → Yes
- q-value-vocabulary：ロール・グループはトークンに載せず aoba-pdp が人事の台帳から導く。type・scope・acr は閉じた語彙で、発行者ごとに同じ文字列を取り違える経路が無い → Yes
- q-identifier-choice：トークンの中のキー（sub・repair_id・approval_ref・act の URI）は台帳の行で、identifier_properties と on_missing がある。ただし、aoba-pdp と hr-sync が利用者を決める照合の鍵に使う **社員番号** は台帳の行が無く、性質（使い回されるか・変わるか・無いときどうするか）が決まっていない。そのうえ C-sub の not_meaning は社員番号を「人事の台帳で変わりうる値で、照合に使わない」としている → **No（F1）**
- ap-1-7：3 行とも書き手は agent-sts（platform）で、元のデータの書き手（approval-svc のアプリ、order-tool・lock-tool の記録、課長だけが書ける担当の割り当て、受付の画面で決めて変えられない部屋、窓口の 2 人で変える作業員の番号、DB の管理者は変更の記録と突き合わせ）まで絞ってある → Yes
- q-freshness-mitigation：authorization_details は 0 秒（approval-svc の条件つきの更新）、repair_id・approval_ref は never、scope は 600 秒の許容に対し 390 秒。どれも REQ の数値から導き、対策を行う者（order-tool・lock-tool・agent-sts）も書いてある → Yes

経路：
- q-single-aud-resource：全種別とホップの aud が 1 つ → Yes
- q-no-passthrough：委任の表・クライアントごとのリソースの表・may_act と mTLS の照合、resource は 1 つ。表に無い宛先は出さない → Yes
- q-step-up-path-coverage：承認の操作の口は APPROVAL_AT（repair-console だけが得られ、act が無い）だけ。エージェント・予約の経路は承認の記録を使うだけで承認の操作に届かない（付録 B） → Yes
- ap-2-7：act の無い 1 段目の REPAIR_DELEG_AT は宛先が agent-sts だけで、ツールは受けない。repair-agent のリソースの表に approval-svc は無い。ツールのトークンでは act が required → Yes
- q-authorize-service-and-user：ツール・approval-svc・aoba-pdp・下流のすべてが mTLS の相手を許可リストで照合し、利用者の権限とは別に決めている → Yes
- q-agent-short-lived-no-rt：agent-sts は RT を出さず、交換は 300 秒か subject_token の残りの短いほう → Yes

設計の全体：
- q-outside-catalog：管理用の口（2.2）、試験の口（U30）、移行の旧経路（U29）、停止の間の電話の手配と事後の登録（2.2・3.1）、DB の直接の書き込み、wl-ca の中間の CA の漏えい（3.1）が答えてある → Yes
- q-object-level-authz：修繕依頼・発注・連絡の相手・部屋・承認のそれぞれで、データ層と照合する受け手と応答が決まっている（M_authz_pdp の 3.） → Yes
- q-approval-from-as：agent-sts は承認の記録からだけ authorization_details を作り、locations と同じ宛先にだけ載せる。受け手は発注 ID・承認自身に結んだ条件つきの更新で 1 回だけ使う。入力に紛れた指示で宛先を変えてもリソースの表と locations で止まる → Yes
- q-operator-act：上長は自分の CONSOLE_AT、代理ログインを作らない、管理の画面・DB・lock-svc の管理の画面はそれぞれ自分のログインと監査ログ → Yes
- q-revocation-delivery：担当者の剥奪は重要な操作 60 秒・ほか 390 秒、委任の停止 330 秒、ログアウト 330 秒で、どれも REQ から導いている。ただし **発注を承認した上長** の退職・異動・ロールの剥奪は、その承認の使用・予約の実行で確かめ直されず、承認の期限（24 時間）まで効く → **No（F2）**
- q-dependency-outage：頼る先ごとに止める側に倒すと決め（4. の表・3.1）、REQ-13 の 60 分と付録 A の 5 分の警報に合わせている。JWKS は 600 秒の後に拒否 → Yes

## 段 4：開いた問い

### op-proof-holder
- 辿った範囲：C-cnf の enforced_at（ツール 4 つ・approval-svc）、種別の holder・sender_constraint、H5〜H8・H11・H12 の validates、付録 D の M_sender_constraint の 4.、3.1 の wl-ca の 2 行
- 箇所ごとの並び：ORDER/PAYMENT/LOCK_TOOL_AT は持つ者・鍵を持つ者ともに repair-agent。CONTACT_TOOL_AT は交換を求めた repair-agent か visit-subagent で、cnf もその証明書。APPROVAL_AT は repair-console と repair-console。REPAIR_DELEG_AT は束縛せず、may_act の URI と mTLS の相手で照合
- 気づき：持つ者と鍵の持ち主が食い違う箇所は無かった。証明書の更新では、共通のクライアント部品が証明書とトークンを組で持ち、古い組は最悪 300 秒で使い切る。REPAIR_DELEG_AT の照合が鍵でなく URI であるため、中間の CA の鍵が漏れると偽の証明書で交換できることは 3.1 に既知の限界として書いてある。指摘なし

### op-source-change
- 選んだ出来事：担当者の異動（修繕課から別の課へ）
- 辿った経路：人事部の担当者が人事システムで登録 → もう 1 人の承認で確定（REQ-08 の起点。登録から確定までは 2 時間以内の手順で、3.1 の見送り）→ aoba-pdp が sub から aoba-as の利用者の社員番号の属性を引き（60 秒キャッシュ）、その社員番号で人事の台帳を引く（60 秒キャッシュ）→ 修繕担当のロールが外れる → 重要な操作のツールは呼び出しごとに、agent-sts は交換ごとに拒否する。hr-sync（5 分ごと）は aoba-as の利用者の無効化とセッションの削除を受け持つ
- 気づき：図に無い書き込みの経路は、DB の管理者を含めて 3.1 に挙がっている。ただし、この経路の継ぎ目にある **社員番号**（aoba-as の属性と人事の台帳を結ぶ鍵）が、変わる・使い回される場合の扱いがどこにも無い。社員番号が付け替わると、hr-sync が属性を書き直すまで（最悪 5 分）、aoba-pdp は古い番号で人事の台帳を引く。番号が使い回されるなら、別の人の在籍・ロールを返しうる。一方で C-sub の not_meaning は、社員番号を「人事の台帳で変わりうる値」としている → F1

### op-one-time
- 辿った範囲：承認（C-approval-ref の enforced_at、P4 の 5.）、予約済みの承認（H14）、解錠コードの作成と送信・送り直し（3.1 の重複の行、12. の lock-svc の行）、認可コード・ログアウトトークンの jti（M_token_validation の 6.）
- 並行の 2 件：approval-svc の原子的な条件つきの更新で片方だけが通る。部屋の累計は排他の錠で直列になる
- 通信が切れた後の再送：同じ発注 ID・承認での再試行には前の結果を返し、「下書き→確定」も条件つきの更新なので 1 回だけになる。使用済み・未確定のまま確定できない発注は、承認を失効させて新しい発注 ID でやり直すので、正しい 1 回は失われない
- 記録先の障害：approval-svc が応答しなければ拒否する
- 気づき：解錠コードの **送り直しの回数（3 回まで）** を誰がどこに持ち、上げ方が原子的かが書いていない。並行の 2 件の送り直しが同じ回を読むと、3 回を超えて送れるか、同じ回として重複扱いで捨てられる。送られるのは同じコードを同じ登録の番号へなので影響は小さい → F4（Minor）

## 段 5：優先 2 の問い（時間があれば）

9 問とも答えた。答えは次の表 (2) に書いた。どれも Yes。

### さらに辿った開いた問い（短く）
- op-requirement-words：「上長」「承認」「取り消し」「担当者」の範囲を挙げた。担当者の区分（社員・契約・派遣・休職・退職の手続き中）は 2.1 にある。「上長」は 2.1 と 9.2 では「課長以上」、4. の交換の条件・H2・C-repair-id の enforced_at では「同じ課の課長」と、書き方がそろっていない → F3。「承認」については、承認した人の権限が後で外れた場合が設計に無い → F2
- op-clock：auth_time（aoba-as の時計）と approval-svc の時計、not_before・not_after と lock-tool・錠の時計を数え、NTP のずれが 1 秒を超えたら外し、追加の認証ではずれを足さない（M_token_validation の 6.）。錠の機器の時計は 12. で未確認と書いてある。指摘なし
- op-key-custody：aoba-as・agent-sts の鍵は HSM、持ち主は認証基盤チーム、漏えい時は 15 分（作業 5 分＋キャッシュ 10 分）。wl-ca の中間の CA は 60 分（3.1）。受け手が古い鍵を使い続けるのは最悪 600 秒。指摘なし

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | claims.yaml の C-sub の `not_meaning`・`verification_method`・`source_system`。design.md の 9.2 の「元のデータからの経路」、付録 D の M_authz_pdp の 5. の「担当者の在籍・職位・所属・研修の記録」の行、2.2 の「人事連携」の行、11. の I18（catalog_answers.yaml の I18 の assumption）。問い：q-identifier-choice・op-source-change | aoba-pdp（重要な操作の剥奪の判断）と hr-sync（利用者の作成・無効化）は、どちらも **社員番号** を、利用者と人事の台帳を結ぶ照合の鍵に使っている。それなのに、社員番号は台帳の行も identifier_properties（stable・reassignable）も、無いとき・変わったときの扱いも無い。さらに C-sub の not_meaning は、社員番号を「人事の台帳で変わりうる値で、照合に使わない」としていて、PDP の経路と食い違う。社員番号が付け替わると、hr-sync が属性を書き直すまで（最悪 5 分）aoba-pdp は古い番号で引く。これは 2.2・9.2 の「hr-sync の遅れは REQ-08 の判断に入らない」と合わない。番号が使い回されれば、別の人の在籍・ロールを返して重要な操作を通しうる。C-sub の rationale の「作り直しても別の sub になる」も、hr-sync が同じ社員番号で古い利用者を見つけた場合の扱いが決まっていない。対策：社員番号の性質（一度割り当てたら変えない・使い回さない）を人事部に確かめて 2.1・9.2 に書く。aoba-pdp は対応が引けない・食い違うときは拒否すると決める。C-sub の not_meaning を直す | Major | 候補の漏れ（あわせて、C-sub の not_meaning と M_authz_pdp の 5. の実装とのずれ） | q-identifier-choice（ほかに q-sub） |
| F2 | claims.yaml の C-approval-ref の `enforced_at`（order-tool・approval-svc の H14 の使用）。hops.yaml の H5・H14 の `validates`。design.md の 9.1 の「承認の記録」の行、9.2 の「担当者の在籍・ロール・担当」の行、2. の REQ-05・REQ-08。問い：q-revocation-delivery・op-requirement-words | 承認者の条件（在籍・上長のロール・所属）を確かめるのは、承認の操作のときの approval-svc だけ。確定・予約（order-tool）や予約の実行（order-scheduler の H13・H14）で aoba-pdp が確かめるのは、トークンや予約の記録の sub（担当者）だけになっている。そのため、10 万円を超える発注を承認した上長が、承認の後に退職・異動・ロールの剥奪になっても、その承認は期限の 24 時間まで使え、予約なら実行の時点でも通る。REQ-08 は剥奪の確定から 2 分で発注の確定を止めると定めるが、承認者の剥奪がこれに入るかを設計が決めておらず、止める単位（承認者）が 9.1・9.2 の表に無い（解錠の承認は承認者が担当者本人で、lock-tool が発行のたびに aoba-pdp で確かめるので当たらない）。対策：承認者の剥奪を REQ-08 に含めるかを修繕課に確かめる。含めるなら、approval-svc が使用済み・予約済みにする条件つきの更新で承認者の在籍とロールを aoba-pdp で引き直す。含めないなら、その旨と理由を 3.1 に書く | Major（要求が承認者を含めないと確かめられれば Minor） | 候補の漏れ | q-revocation-delivery（ほかに op-requirement-words） |
| F3 | design.md の 2.1 の「上長」の行と 9.2 の「元のデータからの経路」（課長以上）に対し、4. の agent-sts が受ける要求の表の 1 行目、hops.yaml の H2 の `validates.checks`（同じ課の課長）、claims.yaml の C-repair-id・C-approval-ref の approval-svc の `enforced_at`（同じ課の課長）。問い：op-requirement-words | 承認できる「上長」を、2.1・9.2 は「職位が課長以上で同じ課の人」、APPROVAL_AT の交換と approval-svc の照合は「同じ課の課長」と書いていて、書き方がそろっていない。課長より上の職位の人（部長など）や、職務代行として登録された人が承認の画面で APPROVAL_AT を得られるかが、読む箇所によって変わる。実装の担当が「課長」を文字どおりに作ると、要求が認める承認者を拒否するか、逆に広げてしまう。対策：approval-svc と agent-sts の条件を、aoba-pdp が返す「上長」のロールの 1 つの定義で書き直し、2.1 と同じ言葉にする | Minor | 実装とのずれ | op-requirement-words |
| F4 | design.md の 3.1 の「重複の実行を、業務の ID で防ぐ」の行（解錠の送り直し）、hops.yaml の H8 の `validates.checks`（送り直しは 3 回まで）、claims.yaml の C-approval-ref の lock-tool の `enforced_at`、付録 D の P4 の 5. の「消費の競合と再送」。問い：op-one-time | 解錠コードの送り直しの回数の上限（3 回）と「回を 1 つ上げる」について、回数を誰（approval-svc・lock-tool・通知の基盤）が持ち、上げ方が条件つきの原子的な更新かが書いていない。並行の 2 件の送り直しが同じ回を読むと、上限を超えて送れるか、同じ回として重複扱いで捨てられる。送るのは同じコードを登録の番号へなので影響は小さいが、ほかの 1 回限りの値と同じ形（条件つきの更新）で決めておかないと、将来の保守で壊れる。対策：回数を承認の記録に持ち、「回 = n なら n+1」の条件つきの更新で上げると P4 の 5. に書き、結合試験に並行の送り直しを足す | Minor | 候補の漏れ | op-one-time |

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| dc-05 | Yes | メンバーはすべて文字列で、正規表現と時刻の書式を固定し、書式違いを拒否してから完全一致で比べる。スキーマで型を表せない点は 3.1 に書いて試験で補っている |
| q-value-vocabulary | Yes | ロール・グループは載せず、PDP が人事の台帳から導く。type・scope・acr は閉じた語彙で、発行者による同じ文字列の取り違えが起きない |
| q-identifier-choice | No | PDP と hr-sync が利用者を決める鍵の社員番号に台帳の行・性質が無く、C-sub の not_meaning と食い違う（F1） |
| ap-1-7 | Yes | 3 行の書き手は agent-sts だけで、元の記録の書き手も課長・アプリの DB アカウント・2 人の手順に絞られ、DB の管理者は変更の記録で検出する |
| q-freshness-mitigation | Yes | authorization_details は 0 秒（条件つきの更新）、scope は 600 秒に対し 390 秒、ID は never。数値はどれも REQ から来ている |
| q-single-aud-resource | Yes | すべての種別とホップで aud が 1 つ |
| q-no-passthrough | Yes | 委任の表・リソースの表・may_act と mTLS の照合で、頼める相手と宛先が規則として決まっている |
| q-step-up-path-coverage | Yes | 承認の操作の口は APPROVAL_AT の 1 つだけで、代理・交換・予約の経路は承認の操作に届かない |
| ap-2-7 | Yes | act の無い 1 段目の REPAIR_DELEG_AT は agent-sts 宛てだけで、ツールは受けず、エージェントは APPROVAL_AT を得られない |
| q-authorize-service-and-user | Yes | すべての呼ばれる側が mTLS の相手を証明書の URI の許可リストで照合する |
| q-agent-short-lived-no-rt | Yes | agent-sts は RT を出さず、寿命は 300 秒か subject_token の残りの短いほう |
| q-outside-catalog | Yes | 管理の口・試験の口・旧経路・停止の間の手作業・DB の直接の書き込み・CA の漏えいが 2.2・3.1・11. で答えてある |
| q-object-level-authz | Yes | オブジェクトごとに、データ層で照合する受け手と失敗の応答が決まっている |
| q-approval-from-as | Yes | 承認の記録から作り、宛先（locations）と操作（発注 ID・承認自身）に結んで 1 回だけ使う |
| q-operator-act | Yes | 上長・運用者・DB の管理者はそれぞれ自分の ID で動き、代理ログインが無く、監査ログで区別できる |
| q-revocation-delivery | No | 発注を承認した上長の剥奪は、承認の使用・予約の実行で確かめ直されず、24 時間まで効く（F2） |
| q-dependency-outage | Yes | 頼る先ごとに止める側に倒し、REQ-13 の 60 分と 5 分の警報に合わせている |
| op-proof-holder | 該当なし（開いた問い） | どの箇所も、トークンを持つ者と束縛した鍵の持ち主が同じワークロード。指摘なし |
| op-source-change | 該当なし（開いた問い） | 異動を辿り、社員番号の継ぎ目に約束の無い区間を見つけた（F1） |
| op-one-time | 該当なし（開いた問い） | 承認・予約・解錠は条件つきの更新で 1 回だけ。送り直しの回数の持ち方だけが未定（F4） |
| pa-01 | Yes | repair_id は対象の照合と監査、approval_ref は承認の消費、authorization_details は内容の照合と、受け手ごとの使い道が enforced_at にある |
| q-derived-value | Yes | 連絡先・住所・コードは載せず、不透明な ID だけ。authorization_details は order-tool・lock-tool のトークンにだけ載る |
| q-variant-comparison | Yes | CONSOLE_AT・REPAIR_DELEG_AT の送信者制約の見送りは、開く攻撃（盗んだトークン）と代わりの守り（mTLS のクライアント認証・may_act）を比べ、試験の方法も書いてある |
| q-idp-diff-absorbed | Yes | 発行者は組織の 2 つだけで、ツール・approval-svc は agent-sts のトークンだけを受ける |
| q-original-principal | Yes | 交換の後も sub は担当者のままで、scope は上流と宛先とロールの積 |
| q-step-up-by-rs | Yes | 追加の認証を求めるかは approval-svc が操作の種類で決め、401 と RFC 9470 の応答を返す |
| q-long-running | Yes | 予約はトークンを持ち越さず、実行の時点で在籍・ロール・担当・委任の世代・承認を引き直す |
| q-copies-outlive | Yes | 予約の記録と監査ログの写しに integrity_until と書き換えの検出があり、DB・ブローカーの接続は無い |
| q-audit-correlation | Yes | sub・repair_id・approval_ref を同じ鍵・同じ正規化の HMAC で全サービスに残し、交換の jti で結ぶ |
