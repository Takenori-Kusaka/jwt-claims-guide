# レビュー報告：designs/target（あおば住まいサービス 修繕の手配）

- 対象：designs/target/design.md・claims.yaml・token_types.yaml・hops.yaml・catalog_answers.yaml・claim_request_*.md
- 問いの 1 枚：sheet.md（行の抜き取りの種 12。抜き取った行：C-approval-ref・C-repair-id・C-authorization-details）
- 指摘：Blocker 0・Major 2・Minor 3

## 段 0：受け付け（CI の結果）

- ci-result.txt と設計書の 1. は一致している：error 0、warn 2、info 24
- warn 2 件（L16 hop H5・H8：authorization_details が上流 H4 に無い＝下流で広げる）には、1. に行ごとの理由がある。広げる根拠を上流のトークンでなく approval-svc の承認済みの記録（別の権限の元）に置き、広がる分を承認した 1 件に限り、受け手が条件つきの使用済みで確かめる、という理由は通る。指摘にしない（q-hop-narrowing は L16 が答えを決める問いで、理由は妥当）
- 検査を通すために宣言を曲げた跡（q-lint-workaround）：見当たらない。H5・H8 の warn を抑止せず残しており、上流を外す・数値を上限に合わせる、といった跡は無い

## 段 1：性質の表を図と要求に照らす

sheet.md の 12 の性質を、2. の図・REQ-01〜13・台帳と照らした。表のとおりで、食い違いは無い。

- 組織独自のクレーム：C-repair-id・C-approval-ref（名前空間 https://aoba-sumai.example/claims/）。当たる
- 個人情報：C-sub・C-repair-id・C-authorization-details・C-name。当たる
- 発行者が複数：aoba-as と agent-sts。当たる
- 交換・作り直し：H3・H5〜H9・H11・H12。当たる
- 委任：act・may_act、max_delegation_depth 2。当たる
- 操作ごとの承認：authorization_details（vendor-order・lock-code）と approval_ref。どちらも 1 件の発注・1 回の解錠に結びつき、時間枠の承認ではない。当たる
- マルチテナント：組織は 1 つで、テナントを表す値もオーナーごとのデータの分け方も無い（REQ に無い）。「当たらない」で正しい
- DB の層までトークンを運ぶ：発注の台帳は order-tool・order-scheduler が自分の DB アカウントで接続する（2. のデータ層の行）。「当たらない」で正しい
- 認証の強さ・新しさ：acr・auth_time（REQ-07）。当たる
- 送信者制約を選んだ：ツールのトークン 4 種と APPROVAL_AT が mtls。当たる
- 送信者制約を見送った：CONSOLE_AT・REPAIR_DELEG_AT が none。当たる
- 長時間・非同期：ORDER_TOOL_AT.long_running、U13 が該当（予約の実行）。当たる

## 段 2：6. の「要る」問いを判断の木と比べる

| 問い | 判断の木の節 | 設計の仕組み | 比べた結果 |
| --- | --- | --- | --- |
| q-sub・q-user | keep-sub-exchange | 交換で sub を写すだけ（差し替えさせない）。宛先ごと・300 秒で作り直す | 合う。非同期（UC4）は、ワーカーが交換し直す既定から外し、order-scheduler が判断の元の記録を引き直す。3. に既定から外れた点として理由・同じ出どころでの確かめ・試験が書いてあり、取り違えではない |
| q-actor・q-agent | keep-sub-exchange（最も外側の act） | 最も外側の act.sub を mTLS の相手と照合し、操作ごとの許可リスト。内側の act は記録だけ（C-act の enforced_at・H5〜H8・H11 の validates） | 合う。受け手の照合の文も最も外側だけを読んでいる |
| q-peer | peer-mtls | wl-ca の証明書の mTLS（tls_client_auth・end_to_end） | 合う。トークンのクレームで代えていない |
| q-txn | txn-tctx | repair_id（独自クレーム）。Txn-Token は却下 | 合う。ここでの q-txn は「どの修繕依頼か」の相関と対象の照合で、経路の途中で取引の内容を固定する用途ではない。取引の内容（金額・協力会社・部屋）は authorization_details で固定している。txn を使わない理由（何日もまたぐ単位で、呼び出しの連鎖ではない）も prior_art_search にある |
| q-authorized | rar-vs-custom | scope（操作）と authorization_details（承認した 1 件）と approval_ref（承認の記録の参照） | 合う。同じ API での併用は、scope は操作の種類・authorization_details は承認の内容、と台帳で分担を書いている |
| q-resource | （aud） | aud は 1 つ。resource は 1 つで、リソースの表にある宛先だけ | 合う |
| q-holder | （cnf） | cnf の x5t#S256 を mTLS の相手と照合 | 合う |
| q-via | （act の連鎖と監査ログ） | 交換の元の jti と出した jti、act の連鎖 | 合う |

目的と仕組みの不一致は見つからなかった。

## 段 3：優先 1 の問いに答える

抜き取った 3 行（C-approval-ref・C-repair-id・C-authorization-details）について行の問いに答え、No の問いでは残りの行も見た。答えは末尾の (2) の表。No にした問いは ap-1-7 と dc-05 で、それぞれ (1) の指摘 F1・F2・F4 にした。

## 段 4：開いた問い

### op-proof-holder（鍵の持ち主を確かめる箇所）

辿った範囲：C-cnf の enforced_at（ツール 4 つ・approval-svc）、各種別の holder・sender_constraint、付録 D の M_sender_constraint の 1.・4.、3.1 の wl-ca の 2 行。

| 箇所 | トークンを持つ者 | 鍵（証明書）を持つ者 | 一致するか |
| --- | --- | --- | --- |
| order-tool・payment-tool・lock-tool | repair-agent（交換を求めた者） | repair-agent | 一致 |
| contact-tool（H6・H11） | repair-agent か visit-subagent（交換を求めた者） | 同じ | 一致 |
| approval-svc（H12） | repair-console | repair-console | 一致 |
| agent-sts（REPAIR_DELEG_AT） | 束縛しない。may_act の主体の mTLS で代える | may_act の主体 | 束縛の代わりに may_act と mTLS の相手を照合 |

気づいたこと：

- 証明書の更新（24 時間、残り 8 時間）は aoba-agent-kit が証明書とトークンを組で持つことで扱い、古い組でも最悪 300 秒で終わる。cnf の食い違いは起きない
- 3.1 では、エージェントを止めたり鍵が漏れたりしたときは「登録と許可リストは URI と拇印の組で持つ」。証明書は 24 時間ごとに替わり、拇印も毎日変わる。呼ばれる側（aoba-pdp・approval-svc・修繕依頼の台帳・通知の基盤・経理の仕組み）の許可リストの拇印を、誰が・どの仕組みで・更新から何分以内に入れ替えるかは書いていない。遅れても止める側に倒れる（呼べなくなる）ので安全側だが、REQ-13 の 60 分の停止とのつながりは確かめていない
- repair-console を複数のインスタンスで動かすとき、全インスタンスが同じ証明書（同じ鍵）を共有するのか、インスタンスごとに束縛するのかが書いていない（C-client-id の assumption は「証明書 1 つに対応」）。APPROVAL_AT を求めたインスタンスと使うインスタンスが違えば cnf が合わない。止める側に倒れるので指摘にはしない

### op-source-change（権限の元データが変わる出来事）

出来事 1：担当者が修繕課から異動する。

- 人事部の担当者が人事システムで登録する → 人事部の承認者がもう 1 人で承認して確定（2 時間以内は人事部の手順書。3.1 の見送りの行、月次の報告で確かめる）→ aoba-pdp が確定した値を人事の台帳の API で読む（キャッシュ 60 秒）→ 発注の確定・解錠・支払いのツールと approval-svc は呼び出しのたびに aoba-pdp に問い合わせるので最悪 60 秒（REQ-08 の 2 分の内側）。agent-sts の次の交換で scope が外れ、下書き・連絡は手元のトークンの分を足して最悪 390 秒（10 分の内側）
- sub から社員番号を引く aoba-as の属性を書けるのは hr-sync の証明書の API と DB の管理者だけで、DB の管理者の分は変更の記録の突き合わせで翌日に検出する（3.1）。辿れた

出来事 2：担当の付け替え（修繕課の課長が repair-console の「担当の割り当て」の画面で行う）。

- repair-console が課長であることを aoba-pdp で確かめ、mTLS で修繕依頼の台帳に書き、担当の履歴に追記する（2.2）→ agent-sts はキャッシュせずに担当を引き、aoba-pdp は 60 秒キャッシュ
- 図にも許可リストにも無い経路が見つかった：repair-console → aoba-pdp の呼び出しは範囲の図に矢印が無く、付録 D の M_authz_pdp の 5. の aoba-pdp の許可リストにも repair-console が入っていない（F1）
- 誰も書き手を数えていない区間がある：修繕依頼の台帳は管理業務システム（別の設計書）の一部だが、修繕依頼の部屋・担当・担当の履歴を repair-console のほかに書ける者（管理業務システムの既存の画面や API、台帳の DB の管理者）が挙がっていない。3.1 の DB の管理者の行も、approval-svc・発注の台帳・aoba-as の利用者の DB だけを数えている（F2）。解錠の作業員の番号を持つ協力会社の台帳も同じ（F2）

あわせて気づいたこと（指摘にしない）：2.1 は、退職の手続き中の人を「退職日の前日まで入る」としている（人事部に確かめた）。REQ-08 の起点は「人事の台帳で確定してから」で、退職日より前に確定する退職では、確定から 2 分で止まるのではなく退職日に止まることになる。人事部の確認に基づく解釈なので指摘にはしないが、REQ-08 の文と 2.1 の解釈を要求の側でそろえておくとよい。

### op-one-time（1 回だけ使える値）

辿った範囲：付録 D の P4 の 5.・M_token_validation の 6.、C-approval-ref・C-jti、3.1 の重複の行、2.2 の予約の実行。

| 値 | 並行の 2 件 | 通信が切れた後の再送 | 記録先の障害 | 正しい 1 回を失わないか |
| --- | --- | --- | --- | --- |
| 発注の承認 | approval-svc の原子的な条件つきの更新で、発注 ID に結ぶ。片方だけ成功する | 同じ発注 ID には前の結果を返し、「下書き→確定」の条件つきの更新で確定は 1 回 | approval-svc が止まれば拒否する（消費しない） | 再試行すれば失わない。確定しないまま止めた発注は、上長が取り下げて承認し直す |
| 解錠の承認とコード | 承認自身に結ぶ。lock-svc は承認 ID ごとにコードを 1 つだけ作る | 同じ承認 ID には同じコードを返し、通知の基盤も承認 ID で重複を避ける | lock-svc・通知の基盤が止まれば、not_after まで同じ承認 ID で再試行する | 失わない |
| 予約済みの承認（H14） | 予約済みから使用済みへの条件つきの更新 | 次の回に同じ発注 ID で再試行する | 止まれば実行せず取り消して知らせる | 一時の停止でも予約が取り消される（安全側。業務の影響は運用で見る） |
| ログアウトトークンの jti | 150 秒覚える | 同じ | — | — |
| 認可コード | aoba-as が 1 回限り。2 回目はそのコードで出したトークンも失効 | — | — | — |

気づいたこと：

- 2 回通る経路は見つからなかった
- 発注の承認を使用済みにした後で確定できず、承認の 24 時間の期限を過ぎてから同じ発注 ID で再試行したとき、approval-svc が前の結果（成功）を返すのか、期限切れで拒否するのかが書いていない。どちらでも 2 回通ることはない（確定は「下書き→確定」で 1 回）が、期限の後に確定できるかは REQ-05 の「24 時間で期限が切れる」の読み方に関わる。書き手に確かめるとよい
- 解錠コードの送り直しは、送るたびに協力会社の台帳の作業員の番号を引く。送り直しの間に番号が書き換えられると、同じコードが別の番号に届く。番号の書き手は F2 に含めた

## 段 5：優先 2 の問い

時間が残ったので、9 問すべてに答えた（(2) の表の後半）。どれも Yes で、指摘にしたものは無い。

## 専門家に回す点

- 委任の深さが 2（escalation の delegation-depth）。設計書の 12. で、認証基盤チームの責任者のレビューに回すと書いてある。レビュアーは答えない
- aoba-as の RT の再利用の検知と acr・auth_time の挙動は、組織が作った仕組みの未試験の挙動。12. に試験の案がある（q-idp-capability-verified・q-refresh-reevaluated に当たるので、試験の結果を専門家が見る）

## (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | design.md 付録 D の M_authz_pdp の 5.（PEP・PDP の分担の後の段落：aoba-pdp と approval-svc の口を呼べる相手）、2. 範囲の図（repair-console → aoba-pdp の矢印が無い）、2.2 の「運用者の操作（上長の引き継ぎ）」の行、3.1 の「委任の欄と担当の割り当ての書き込み」と「wl-ca の中間の CA の鍵の漏えい」の行、catalog_answers.yaml の U12 と subject-states/role-change の RP・BFF のセッション | 許可リストの宣言と、それに頼る仕組みが食い違う。(a) 2.2 では、担当の割り当ての前に repair-console が「セッションの sub が修繕課の課長であること」を aoba-pdp で確かめ、catalog_answers では画面のボタンの出し分けも aoba-pdp に問い合わせる。ところが M_authz_pdp の 5. の aoba-pdp を呼べる相手（agent-sts・order-tool・payment-tool・lock-tool・approval-svc・order-scheduler）に repair-console が無く、図にも矢印が無い。(b) 3.1 と U12 では、lock-svc がコードを作る前に approval-svc で使用済みを確かめ、これが wl-ca の中間の CA の鍵が漏れても解錠の口が開かない根拠になっている。ところが approval-svc の口を呼べる相手（依頼・使用済み・予約済みは order-tool・lock-tool・order-scheduler、参照は agent-sts）に lock-svc が無い。許可リストのとおりに作れば、課長の確かめか lock-svc の確かめのどちらかが動かない。修繕依頼の台帳は repair-console の証明書を信じるだけなので、課長の確かめが落ちれば、ログインした担当者なら誰でも担当を自分に付け替えられる。そうなると、解錠の承認（「担当者本人」が承認する）と委任を他人の修繕依頼に向けられる | Major | 実装とのずれ | ap-1-7、q-authorize-service-and-user、q-outside-catalog |
| F2 | claims.yaml C-repair-id の source_system・authoritative_writer（元のデータの書き手）、design.md 2. 範囲の表の「組織の網」の行（修繕依頼の台帳を範囲の外にした前提）、3.1 の「approval-svc・発注の台帳・aoba-as の利用者の DB の管理者の直接の書き込み」の行、9.2 の「元のデータからの経路」、付録 A（アプリを通らない変更の突き合わせ）、付録 D の M_privacy_minimization の 5.（作業員の番号） | 権限・識別子の元のデータを書ける者を全部は数えていない。設計は、修繕依頼の台帳の (1) 修繕依頼の部屋（lock-tool の unit_id の照合と解錠の承認の依頼の部屋）、(2) 担当と担当の履歴（委任・解錠の承認者・発注の承認者の自己承認の禁止）、(3) 委任の欄に頼る。協力会社の台帳の作業員の番号（解錠コードの届け先。REQ-06）にも頼る。書き手として挙がっているのは repair-console の証明書だけである。修繕依頼の台帳を持つ管理業務システムの既存の画面・API、両方の台帳の DB の管理者、協力会社の台帳を書く画面（別の設計書の受発注の画面など）が、部屋・担当・履歴・番号を書き換えられるかどうかは書いていない。3.1 の DB の管理者の行と毎日の突き合わせも、approval-svc・発注の台帳・aoba-as の利用者の DB だけを数え、修繕依頼の台帳と協力会社の台帳を含まない。部屋か番号を書き換えられれば、担当者本人の承認 1 回で別の部屋の解錠コードを出せる、あるいはコードを別の人に届けられる。担当の履歴を消せれば、REQ-05 の自己承認の禁止が外れる。書き手の一覧（既存の画面・API・DB の管理者）と、止める手段か検出の手段（3.1 の変更の記録の突き合わせに 2 つの台帳を足すなど）を書くべき | Major | 候補の漏れ | ap-1-7、op-source-change |
| F3 | claims.yaml C-repair-id の source_system（「APPROVAL_AT では approval-svc の承認の記録」） | APPROVAL_AT の repair_id の出どころの記述が、ほかの 4 か所と食い違う。C-repair-id の authoritative_writer、hops.yaml H12 の added_claims、design.md 4. の agent-sts の要求の一覧、claim_request_repair_id.md の問 11 は、どれも「repair-console の交換の要求（画面で開いた修繕依頼）から書き、承認の記録の値は写さない」としている。食い違うのは source_system だけである。approval-svc の照合（C-repair-id の enforced_at：出どころの違う 2 つを比べ、画面で見ている修繕依頼と違う承認を操作させない）は、値を承認の記録から写すと必ず一致してしまい、意味を失う。source_system を「repair-console の交換の要求と修繕依頼の台帳」に直す | Minor | 実装とのずれ | q-txn、ap-1-7 |
| F4 | claims.yaml C-authorization-details の description（lock-code の not_before・not_after）・value_normalization・enforced_at（lock-tool の「要求と完全一致」）、design.md 付録 D の P4 の 5.「承認の内容」 | 時刻のメンバーの比べ方が 1 つに決まっていない。not_before・not_after は「RFC 3339 の UTC の時刻の文字列」で、lock-tool は要求の値と文字列の完全一致で比べる。しかし RFC 3339 の UTC には、Z と +00:00、秒の小数の有無、t・z の大文字と小文字の違いがあり、value_normalization（NFC・trim・as_is）ではそろわない。agent-sts（承認の記録から作る）・エージェント（要求を組み立てる）・lock-tool の実装ごとに書式が分かれると、正しい解錠が拒否される。止める側に倒れるので重大度は低いが、書式を固定する（例：YYYY-MM-DDTHH:MM:SSZ、小数なし）か、時刻として解析して比べると決める | Minor | 候補の漏れ | dc-05 |
| F5 | design.md 付録 D の P4 の 7.「上限」（「ツールも深さ 2 を超える act を拒否する」）、claims.yaml C-act の enforced_at（order-tool・contact-tool・payment-tool・lock-tool）、hops.yaml H5〜H8・H11 の validates、token_types.yaml のツールのトークン 4 種の max_delegation_depth | P4 の 7. はツールでも深さ 2 を超える act を拒否すると書くが、C-act の enforced_at と各ホップの validates のツールの確かめには、深さの確かめが無い（最も外側の act.sub と許可リストだけ）。agent-sts が 3 段目を拒否するので今は実害が無いが、2 か所のどちらが正しいかを決め、ツールで確かめるなら台帳とホップに書く | Minor | 実装とのずれ | q-actor |

## (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| dc-05 | No | 型はどれも文字列で、金額は 10 進の文字列、比べ方は完全一致と決めている。ただし時刻のメンバーの RFC 3339 の書式が 1 つに固定されていない（F4） |
| q-value-vocabulary | Yes | ロール・所属はトークンに載せず、aoba-pdp が人事の台帳のコードから導く。scope・acr・authorization_details の type は閉じた語彙で、持ち主は 1 つ。発行者は組織の 2 つで、同じ文字列を別の発行者が付ける経路は無い |
| q-identifier-choice | Yes | 利用者のキーは aoba-as の sub（UUID。identifier_properties と on_missing 拒否あり）。repair_id・approval_ref・client_id にも identifier_properties がある。社員番号はトークンに出さず、aoba-pdp の中で引く |
| ap-1-7 | No | トークンに書くのは agent-sts だけで、承認は approval-svc の記録から作る。しかし元のデータ（修繕依頼の部屋・担当・履歴、作業員の番号）の書き手が数えられていない（F2）。課長の確かめと lock-svc の確かめは許可リストと食い違う（F1） |
| q-freshness-mitigation | Yes | authorization_details（許容 0 秒）は、ツールの実行のたびの条件つきの使用済み（キャッシュ無し）で取り下げをすぐ反映する。repair_id が指す担当・委任の欄は、agent-sts がキャッシュせず、aoba-pdp は 60 秒。REQ-08 の 2 分・10 分、REQ-09 の 10 分に収まる |
| q-single-aud-resource | Yes | 全種別・全ホップで aud は 1 つ。resource は 1 つだけ受け、ツールは配列にほかの値があれば拒否する |
| q-no-passthrough | Yes | 交換は agent-sts だけが行う。委任の表とクライアントごとのリソースの表（repair-console は agent-sts と approval-svc、visit-subagent は contact-tool だけ）で、頼める相手・宛先・scope の積を決めている |
| q-step-up-path-coverage | Yes | 承認の操作の口は APPROVAL_AT（act 無し・client_id が repair-console・cnf）だけで、approval-svc が acr=mfa と auth_time 300 秒を確かめる。代理・交換の後・予約の経路からは承認に届かない |
| ap-2-7 | Yes | act の無いトークンのうちエージェントが持つのは 1 段目の REPAIR_DELEG_AT だけで、宛先は agent-sts、交換できるのは may_act の主体の mTLS だけ。ツールのトークンには必ず act が入り、APPROVAL_AT は repair-console にしか出ない |
| q-authorize-service-and-user | Yes | すべての呼び出しで wl-ca の証明書の mTLS を確かめ、呼ばれる側の許可リストと最も外側の act・cnf に照らす。許可リストの記述の食い違いは F1 に書いた |
| q-agent-short-lived-no-rt | Yes | agent-sts は RT を出さない。エージェントのトークンは 300 秒以下で、手順ごとに交換し直す |
| q-outside-catalog | Yes | outside_enumeration で 9 つの場面を挙げ、U29（旧い口無し）・U30（試験の口を本番に含めない）・管理用の口・電話の手配・障害時の再送に答えている。図に無い repair-console → aoba-pdp の経路は F1 に書いた |
| q-object-level-authz | Yes | ツールは repair_id と発注・部屋・連絡の相手を台帳で照合する（404・400・403）。agent-sts は担当が sub であることを確かめる。トークンの値だけに任せていない |
| q-approval-from-as | Yes | agent-sts は承認済みの記録からだけ authorization_details を作り、locations の宛先にだけ載せる。受け手は記録と照合し、発注 ID か承認自身に結んで使用済みにする。依頼の文に紛れた指示で変わった値は、人が画面で確かめる |
| q-operator-act | Yes | 上長は自分のログインで操作し、代理ログインは無い。設定は PR と 2 人の承認、aoba-as の管理の画面は監査ログ、DB の管理者は変更の記録の突き合わせで、利用者の操作と見分けられる（修繕依頼の台帳の DB の管理者が抜けている点は F2） |
| q-revocation-delivery | Yes | 重要な操作は都度 aoba-pdp（最悪 60 秒）、下書き・連絡は 390 秒、委任の停止は交換 0 秒＋手元 330 秒。どれも REQ-08・09 の 2 分・10 分から導かれている。予約は実行の時点で引き直す |
| q-dependency-outage | Yes | aoba-as・aoba-pdp・修繕依頼の台帳・approval-svc・agent-sts・JWKS の取得先のどれが止まっても止める側に倒す（unknown_kid は reject）。REQ-13 の 60 分と 5 分の警報に合わせ、電話の手配に切り替える |
| pa-01 | Yes | repair_id は agent-sts・ツール・approval-svc が対象の照合と監査に使い、approval_ref は order-tool・lock-tool・approval-svc が承認の消費と操作の対象に使う。表示用の値での認可は無い |
| q-derived-value | Yes | 入居者の連絡先・住所は載せない（却下）。authorization_details の部屋・時間帯は lock-tool 宛ての LOCK_TOOL_AT だけに載り、sub・repair_id は受け手がそれぞれ問い合わせと照合に使う |
| q-variant-comparison | Yes | CONSOLE_AT・REPAIR_DELEG_AT の送信者制約の見送りは、盗まれたときに開く口（無い：宛先は agent-sts で、mTLS のクライアント認証か may_act が要る）と、代わりの守り、試験を比べている |
| q-idp-diff-absorbed | Yes | 発行者は組織の 2 つで、ツール・approval-svc は agent-sts のトークンだけを受ける。aoba-as の CONSOLE_AT が内側の受け手に届くホップは無い |
| q-original-principal | Yes | 交換の後も sub は担当者のままで、scope は上流と宛先の操作と aoba-pdp のロールの積。order-scheduler も予約の記録の sub で在籍・ロール・担当を引き直す |
| q-step-up-by-rs | Yes | 追加の認証を求めるかどうかは approval-svc が決めて 401 を返す。repair-console はそれを受けて認証し直してもらうだけ |
| q-long-running | Yes | 予約はトークンを持ち越さず、実行の時点で order-scheduler が在籍・ロール・担当・委任の欄・行為者の登録・承認・記録の改ざんを確かめ直し、通らなければ実行しない |
| q-copies-outlive | Yes | 写しは監査ログ（鍵つきのハッシュ）、予約の記録（変更の記録で改ざんを検出）、aoba-pdp の 60 秒のキャッシュ。開いたままの接続・分析用の複製は無い（U23・U28） |
| q-audit-correlation | Yes | sub・repair_id は全サービスで同じ鍵・同じ正規化のハッシュ、act の連鎖・approval_ref・発注 ID・jti は値のまま残る。agent-sts は交換の元の jti と出した jti を結ぶ。鍵を替えた後も古い鍵で検索できる |
