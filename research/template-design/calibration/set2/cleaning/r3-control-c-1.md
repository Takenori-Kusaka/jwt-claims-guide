# レビュー報告：designs/target（あおば住まいサービス 修繕の手配）

読んだもの：design.md（1.〜13.・付録 A〜D）、claims.yaml、token_types.yaml、hops.yaml、catalog_answers.yaml、claim_request_repair_id.md・claim_request_approval_ref.md（問 1・11・13・17）、schemas/ORDER_TOOL_AT.consumer.schema.json、ci-result.txt、sheet.md（種 12）。教材は short_list.md の代わりに sheet.md の問い、perspectives.md（各問いの節と重大度の目安）、decision_tree.md（2.〜7.）、kind_tell.md。

## 0. 受け付け（CI の結果と、宣言を曲げた跡）

- claim_lint は error 0・warn 2（L16 の H5・H8）。design.md の 1. の表は ci-result.txt と一致する。
- warn 2 件の理由：上流の REPAIR_DELEG_AT は承認の前に出るので、承認の内容を載せられない。agent-sts は approval-svc の承認済みの記録（追加の認証を経た人の承認）からだけ authorization_details を作り、広がるのは承認した 1 件の分だけ。受け手は approval-svc で条件つきで使用済みにして確かめる。広げる権限の元がトークンの外の別の記録にあり、その記録を受け手が都度引くので、理由は通ると判断した（指摘にしない）。
- 宣言を曲げた跡：hops の upstream は H2〜H12 で途切れない（H12 の上流は H2）。H13・H14 はトークンを運ばないホップで、upstream が無いのは妥当。数値を上限に合わせた跡は見つからなかった（寿命は 5.1 で REQ-08・REQ-09 から導いている）。

## 1. 12.・2.・6. を読み、性質の表を図と要求に照らす

| sheet.md の性質 | 確かめた結果 |
| --- | --- |
| 組織独自のクレーム［当たる］ | 正しい。C-repair-id・C-approval-ref（名前空間 https://aoba-sumai.example/claims/） |
| 個人情報［当たる］ | 正しい。C-sub・C-repair-id・C-authorization-details・C-name が個人情報 |
| 発行者が複数［当たる］ | 正しい。aoba-as と agent-sts（catalog_answers の idp） |
| 交換・作り直し［当たる］ | 正しい。H3・H5〜H9・H11・H12 |
| 委任［当たる］ | 正しい。C-act・C-may-act、深さ 2 |
| 操作ごとの承認［当たる］ | 正しい。C-authorization-details・C-approval-ref |
| マルチテナント［当たらない］ | 正しい。組織は 1 つで、テナントの値が無い（lite_criteria.multitenant） |
| DB の層までトークン［当たらない］ | 正しい。図の「データ層」の行で、発注の台帳は order-tool・order-scheduler が自分の DB アカウントで接続する |
| 認証の強さ・新しさ［当たる］ | 正しい。C-acr・C-auth-time（承認の操作で approval-svc が確かめる） |
| 送信者制約を選んだ・見送った［当たる］ | 正しい。ツールのトークン 4 種と APPROVAL_AT は mtls。CONSOLE_AT・CONSOLE_RT・REPAIR_DELEG_AT は none（3.1 に理由） |
| 長時間・非同期［当たる］ | 正しい。ORDER_TOOL_AT.long_running（予約の発注は最大 24 時間後に実行） |

「当たらない」とされた性質は、実際にも無かった。12. は確かめていない事実だけを挙げ、委任の深さ 2 を専門家に回している。このため深さ 2 に関わる妥当性（根元からの一括失効の十分さ）は、このレビューでは判断せず、専門家の確認に回す。

## 2. 6. で「要る」とした問いと、判断の木の節の比べ

| 問い | 判断の木の節 | 設計の仕組み | 合っているか |
| --- | --- | --- | --- |
| q-sub・q-actor | keep-sub-exchange | sub を保ったまま交換し、act の最も外側を行為者として許可リストに当てる。内側の act は記録だけ（C-act の enforced_at、H11） | 合う。最も外側の act だけで許可している（受け手の enforced_at・validates でも確かめた） |
| q-actor（UC4：予約の実行） | keep-sub-exchange | ワーカー（order-scheduler）が交換し直さず、判断の元の記録を同じ出どころから引き直す | 木の既定から外れるが、3. と 3.1 に、外れる理由と同じ確かめを行う方法を書いている。答える問いは同じ（実行の時点で許すかを決め直す） |
| q-peer | peer-mtls | wl-ca の証明書の mTLS（URI の SAN）。呼ばれる側の許可リスト | 合う。トークンのクレームで代えていない |
| q-txn | txn-tctx | Txn-Token を却下し、repair_id で修繕依頼を表す。取引の内容は authorization_details で固定する | 合う。ツールの先にトークンの連鎖が無く、修繕依頼は日をまたぐので txn の意味と違う（prior_art_search に書いてある） |
| q-authorized | rar-vs-custom | scope（粗い操作）＋authorization_details（承認した 1 件）＋approval_ref（記録の ID）。type はツールごとに 1 つ | 合う。宛先ごとに type を絞っている（H5 は vendor-order だけ、H8 は lock-code だけ）。scope と併用する場合の分担も書いてある |
| q-resource | lifetime-by-situation と P4 | resource を 1 つだけ受け、aud を 1 つにする | 合う |
| q-holder | （M_sender_constraint） | cnf の x5t#S256 と mTLS の相手の照合 | 合う |
| 鮮度の全般 | carry-or-query・lifetime-by-situation | ロール・在籍・担当は載せずに aoba-pdp に問い合わせる。承認の状態は approval-svc で都度引く | 合う |

迷った点は無く、対比表を見るまでもなかった。

## 3. 優先 1 の問いへの答え（1 行ずつ）

- dc-05：Yes。authorization_details は object の配列で、メンバーはすべて文字列（金額は 10 進の文字列、時刻は 1 つの書式）と台帳と付録 D の P4 の 5. で決めている。生成のスキーマがメンバーの型を表せない点は 3.1 に見送りと試験がある。
- q-value-vocabulary：Yes。ロール・グループはトークンに載せず（C-roles・C-groups は却下）、scope・acr・authorization_details の type は value_vocabulary を持ち、書くのは組織の 2 つの発行者だけ。別の発行者の同じ文字列を通す経路が無い。
- q-identifier-choice：Yes。利用者のキーは aoba-as の sub（UUID、stable・再割り当てなし）だけで、agent-sts は写すだけ。社員番号は aoba-pdp の内側でだけ使う。識別子の行（C-sub・C-client-id・C-repair-id・C-approval-ref）は identifier_properties と on_missing を持つ。
- ap-1-7：Yes。値を書ける人を、元のデータまで数えた：社員番号は hr-sync の証明書だけ、人事の台帳は 2 人の手順、担当は課長の画面だけ（履歴は追記だけ）、部屋は作成時に固定、作業員の番号は 2 人目の承認、委任の表・リソースの表は 2 人の承認の PR。DB の管理者の直接の書き込みは 3.1 で検出の手段と理由つきで見送っている。課長が自分を担当にして解錠を 1 人で承認できる点も 3.1 で理由と点検つきで見送っている。
- q-freshness-mitigation：Yes。許す遅れの数値が要求（REQ-05・REQ-08・REQ-09）にあり、寿命が許容を超える行（scope・authorization_details と、載せない値の在籍・担当・委任の欄）のすべてに対策と、それを行う受け手（agent-sts・各ツール・approval-svc・order-scheduler）が書いてある。
- q-single-aud-resource：Yes。交換の要求の resource は 1 つで、すべての種別とホップの aud は 1 つ。受け手は配列に別の値があれば拒否する。
- q-no-passthrough：Yes。交換は agent-sts だけが行い、委任の表（may_act）とクライアントごとのリソースの表が、頼める相手と割り当てる宛先を決める。ツールは上流にトークンを渡さない（付録 D の P4 の 1. の 3、P4 の 4.）。
- q-step-up-path-coverage：Yes。追加の認証が要るのは承認の操作だけで、承認を受けられる口は APPROVAL_AT（act 無し・client_id が repair-console・repair-console の cnf）だけ。エージェントの経路・予約の経路・交換の後の経路からは承認の操作に届かない。ツール側は承認の記録の状態を確かめる。
- ap-2-7：Yes。エージェントは CONSOLE_AT を受けない。act の無い 1 段目の REPAIR_DELEG_AT は宛先が agent-sts だけで、may_act の主体の mTLS でしか交換できない。repair-agent のリソースの表に approval-svc は無いので、act の無い APPROVAL_AT も得られない。ツールのトークンには act が必ず入る（深さ 2 の妥当性は専門家に回す）。
- q-authorize-service-and-user：Yes。直接の相手は mTLS の証明書の URI と、呼ばれる側の許可リストで確かめる。利用者の権限は sub で aoba-pdp に問い合わせる。両者を別々に判断している。
- q-agent-short-lived-no-rt：Yes。agent-sts は RT を出さず、エージェントが持つ種別はどれも 300 秒（REPAIR_DELEG_AT・ツールのトークン）。CONSOLE_RT の holder は repair-console のサーバーだけ。
- q-outside-catalog：Yes。outside_enumeration に、管理用の口（2.2）、試験用の口（U30）、移行期間の旧経路（U29）、障害時の再送（P4 の 5.・付録 A）、手作業（電話の手配。REQ-13）、トークンを使わない口（中間の CA の鍵の漏えい）が、範囲と扱いつきで挙がっている。
- q-object-level-authz：Yes（ただし一覧の参照は未記述。指摘 F2）。agent-sts は修繕依頼の担当と委任の欄を、ツールは発注・連絡の相手・部屋が repair_id のものかを、データの側で照合する。ゲートウェイやクレームだけに任せていない。
- q-approval-from-as：Yes。承認は approval-svc の記録で、承認の依頼の中身はツールが自分の記録から作る（エージェントの申告を使わない）。agent-sts は記録からだけ authorization_details を作り、locations と同じ宛先にだけ載せる。受け手は approval-svc の条件つきの更新（発注 ID か承認自身に結ぶ）で 1 回だけ使う。別のツール・別の代理の主体には、locations・type・行為者の許可リストで通らない。
- q-operator-act：Yes。代理ログインは作らない（I19 は対象外）。上長の引き継ぎは担当を自分に付け替えて自分のログインで行い、監査の sub は上長。管理の画面と設定の変更は運用者のログインと PR で、利用者の操作と混ざらない。
- q-revocation-delivery：Yes。最悪の分数を、止める単位ごとに挙げている：重要な操作 60 秒・下書きと連絡 390 秒（剥奪）、委任の停止 330 秒、承認の取り下げ 0 秒、エージェントの登録の取り消し 330 秒、ワークロードの鍵の漏えい 30 分、中間の CA 60 分、署名の鍵の漏えい 15 分。寿命の数字はこれらの分数から導いている（5.1）。
- q-dependency-outage：Yes。頼る先（aoba-as・aoba-pdp・修繕依頼の台帳・approval-svc・agent-sts の鍵・JWKS）ごとに、止める側に倒すと決めている（4. の表・3.1）。REQ-13 の 60 分を、5 分の警報と電話の手配で受ける。

## 4. 開いた問い（辿った範囲と気づき）

### op-proof-holder

- 辿った範囲：C-cnf の enforced_at（ツール 4 つ・approval-svc）、token_types の holder・sender_constraint、付録 D の M_sender_constraint の 4.、2. の図の証明書の矢印。
- 箇所ごとの「トークンを持つ者」と「鍵を持つ者」：ORDER/PAYMENT/LOCK_TOOL_AT は repair-agent と repair-agent。CONTACT_TOOL_AT は交換を求めた repair-agent か visit-subagent で、cnf もその者。APPROVAL_AT は repair-console と repair-console。どの箇所でも一致する。
- 証明書の更新：残り 8 時間で更新し、新しい証明書の接続では新しい証明書で交換し直したトークンだけを使う（aoba-agent-kit が組で持つ）。古い組は最悪 300 秒残る。
- 気づき：repair-console を複数の台で動かすとき、台ごとに別の証明書なら、別の台で交換した APPROVAL_AT は cnf が合わず拒否される（安全な側に倒れる）。台の数と証明書の持ち方は書いていないので、実装のときに確かめるとよい（指摘にはしない）。

### op-source-change（選んだ出来事：担当者の異動で修繕課を外れる）

- 辿った経路：人事部の担当者が人事システムの画面で登録する → 人事部の承認者がもう 1 人で承認して確定する（登録から確定までは人事部の手順で 2 時間以内。3.1 の見送りの行で、月に 1 回の報告） → aoba-pdp が sub から aoba-as の社員番号の属性（hr-sync だけが書く）を引き、人事の台帳の API で在籍・所属を読む（60 秒キャッシュ） → ロール「修繕担当」は「修繕課に在籍」から導かれるので外れる → agent-sts は次の交換で scope を外す。ツールは確定・解錠・支払いのたびに aoba-pdp を引く（最悪 60 秒）。手元の下書き・連絡のトークンは最悪 390 秒。予約は order-scheduler が実行の時点で引く。
- 図に無い書き込みの経路：aoba-pdp のロールを手で書く口は無い（9.2）。DB の管理者の直接の書き込み（aoba-as の利用者の社員番号・修繕依頼の台帳）は 3.1 で、毎日の突き合わせで検出する。予約の記録だけは実行の前に検出する。
- 誰も時間を約束していない区間：登録から確定までの区間は、人事部の手順書と月次の報告で扱っている。hr-sync の 5 分の写しは判断の経路に入らない。見つからなかった区間は無い。

### op-one-time

- 辿った範囲：承認（P4 の 5. の消費の競合と再送）、発注の確定（「下書き→確定」の条件つきの更新）、解錠（lock-svc の承認 ID ごとの 1 つのコード）、認可コード（LOGIN_CODE の one_time_use）、ログアウトトークンの jti（150 秒）、予約の実行（H14）。
- 並行の 2 件：approval-svc の原子的な条件つきの更新で片方だけが成功し、発注の台帳の条件つきの更新で確定も 1 回。同じ部屋の並行の確定は部屋の行の排他の錠で直列になる。
- 通信が切れた後の再送：同じ発注 ID・同じ承認には前の結果を返し、確定・発行は 1 回だけ。正しい 1 回を失わないよう、承認を自動で未使用に戻さない。確定できない発注は、下書きの取り消しと同時に承認を失効させ、新しい発注 ID で依頼し直す。
- 記録先の障害：approval-svc が止まれば拒否する（止める側）。lock-svc・通知の基盤の重複の鍵は仕様にあるが試験していない（12. に書いてある）。
- 気づき：ログアウトトークンの jti を覚えておく先が「repair-console のセッションの保存先」とあるだけで、複数の台で共有するかは書いていない。共有しなければ別の台に再送が通る（ただし結果は「セッションを消す」なので害は小さい）。指摘にはしない。

## 5. 優先 2 の問い（時間の範囲で）

答えは末尾の表（2）に入れた。気づいたことは指摘 F3〜F5 に書いた。開いた問いのさらに 3 つは、範囲だけを見た：

- op-clock：時刻を比べる箇所は付録 D の M_token_validation の 6. に挙がっている（auth_time は aoba-as の時計と approval-svc の時計、not_before・not_after は lock-tool と機器、承認の期限は approval-svc の時計だけ）。追加の認証ではずれの 30 秒を足さず、NTP から 1 秒ずれたサーバーは外す。止める側に倒している。
- op-key-custody：aoba-as・agent-sts・wl-ca の鍵ごとに、持ち主・保管・漏えい時の手順と目標（15 分・15 分・60 分）がある（付録 D の M_token_validation の 8.）。受け手が古い鍵を使い続けるのは最悪 600 秒。
- op-requirement-words：「担当者」（社員・契約・派遣、休職、退職の手続き中）、「上長」（課長以上・職務代行）は 2.1 で区分に分けてある。「サブエージェントは入居者への連絡だけ」（REQ-04）と、「個人情報は修繕依頼の台帳・通知の基盤だけが扱う」（REQ-12）を辿ったところ、指摘 F1・F5 が見つかった。

## 6. 表

### (1) 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 種別 | 取り違えた問い |
| --- | --- | --- | --- | --- | --- |
| F1 | claims.yaml の C-repair-id の enforced_at（service: contact-tool の check）、C-act の enforced_at（service: contact-tool）、hops.yaml の H6・H11 の validates.checks、design.md の 2.（要求の要約）の REQ-04、6.（UC2 の q-txn） | 台帳の contact-tool の照合は、連絡の相手を「repair_id の修繕依頼の入居者と、その発注の協力会社の窓口」に限るとしか書いておらず、行為者で分けていない。C-act の contact-tool の行も、行為者の許可リスト（repair-agent・visit-subagent）に入っているかだけを見る。一方、H11 と 6. の UC2 は visit-subagent の連絡の相手を入居者だけに限っていて、REQ-04 も「サブエージェントは入居者への連絡だけをする」と求めている。台帳が実装の正（判断の正は YAML と冒頭に書いてある）なので、台帳のとおりに作ると、visit-subagent のトークンで協力会社の窓口にも連絡できてしまい、要求より広い権限になる。直し方：C-repair-id か C-act の contact-tool の check に、「最も外側の act.sub が visit-subagent なら相手は入居者だけ」を書き、H6 と H11 の差と合わせる | Major | 実装とのずれ | q-actor（操作ごとの行為者の許可）、op-requirement-words |
| F2 | claims.yaml の C-approval-ref の absent_semantics（APPROVAL_AT の参照だけ）、C-repair-id の enforced_at（service: approval-svc）、token_types.yaml の APPROVAL_AT の note、hops.yaml の H12 の validates.checks、design.md の付録 D の M_authz_pdp の 3. | approval_ref の無い APPROVAL_AT で行う「承認の一覧の参照」について、approval-svc が返す記録を、トークンの repair_id の修繕依頼や承認者の条件で絞るとは、どこにも書いていない。repair_id の照合が書いてあるのは、承認・却下・取り下げの操作だけ。承認の記録には金額・協力会社・部屋・時間帯（この設計自身が個人情報として扱う値）が入るので、絞らない実装にすると、課長が担当外の修繕依頼の承認の記録を読める。直し方：approval-svc の enforced_at に、一覧の参照をトークンの repair_id の記録だけに限ることを足し、M_authz_pdp の 3. の承認の行にも書く | Minor | 候補の漏れ | q-object-level-authz |
| F3 | claims.yaml の C-repair-id と C-authorization-details の pii_category・data_category | どちらの行も pii_category は「個人情報」なのに、data_category は [system.operations]（利用者のデータでない区分）になっている。1 つの行の 2 つの欄が、同じ値の性質について食い違う。fideslang の区分で集計・保護の要件を引く道具や受け手は、個人情報として扱わない。直し方：user.* の区分（部屋・時間帯なら位置や行動に当たる区分など）にそろえるか、system.operations にした理由を書く | Minor | 実装とのずれ | q-derived-value |
| F4 | claims.yaml の C-client-id の enforced_at（service: order-tool・contact-tool・payment-tool・lock-tool の「act の最も外側と同じ」）と allowed_values、C-act の description、hops.yaml の H5 の validates.checks（「client_id も repair-agent」） | ツールは「client_id が act の最も外側と同じエージェントか」を確かめると書いてある。しかし client_id は登録の名前（enum の "repair-agent"）、act.sub はワークロードの URI（https://workloads.aoba-sumai.example/repair-agent）で、形が違う。2 つを結ぶ対応（agent-sts のクライアントの登録の表を、ツールがどう持つか）が書いていない。そのまま比べると必ず食い違うので、受け手ごとに勝手な対応表を作ることになる。直し方：対応の出どころ（設定の配布で受け手に渡す、など）を台帳に書くか、比べる値を 1 つの形にそろえる | Minor | 候補の漏れ | q-agent |
| F5 | design.md の 2.（要求の要約）の REQ-12、付録 D の M_privacy_minimization の 5.（API で渡す属性と受け手） | REQ-12 は入居者の個人情報（氏名・電話番号・住所）を「修繕依頼の台帳・通知の基盤だけが扱う」と求めている。しかし設計では、contact-tool が修繕依頼の台帳から入居者の連絡先を引いて通知の基盤に渡す（処理の間はメモリに持つ）。要求に無い部品が個人情報を扱うのに、要求とのずれを認める理由も、要求の側の確認も書いていない。トークンに載せないこと自体は守れている。直し方：通知の基盤が repair_id から宛先を引く形に替えるか、contact-tool を扱ってよい部品に入れることを要求の持ち主と確かめ、その旨を書く | Minor | 理由の不備 | op-requirement-words |

### (2) 問いごとの回答

| 問い ID | 回答（Yes／No／該当なし） | 理由（1 行） |
| --- | --- | --- |
| dc-05 | Yes | authorization_details は object の配列で、メンバーはすべて文字列（金額は 10 進の文字列、時刻は 1 つの書式）と決まっている。スキーマで表せない点は 3.1 で試験に回している |
| q-value-vocabulary | Yes | ロール・グループは載せず、scope・acr・type は value_vocabulary を持つ。発行者は組織の 2 つだけで、別の発行者の同じ文字列が通らない |
| q-identifier-choice | Yes | 利用者のキーは aoba-as の UUID の sub だけ。agent-sts は写すだけで、識別子の行は identifier_properties と on_missing を持つ |
| ap-1-7 | Yes | 社員番号・人事の台帳・担当・部屋・作業員の番号・委任の表を書ける人は管理側に限られる。DB の管理者は 3.1 の見送り（検出つき） |
| q-freshness-mitigation | Yes | 要求に遅れの数値があり、許容を超える行のすべてに対策と、それを行う受け手が書いてある |
| q-single-aud-resource | Yes | resource は 1 つで、すべての種別・ホップの aud は 1 つ。配列に別の値があれば拒否する |
| q-no-passthrough | Yes | 交換は agent-sts だけが行い、委任の表とクライアントごとのリソースの表で、頼める相手と宛先が決まる。ツールはトークンを渡さない |
| q-step-up-path-coverage | Yes | 追加の認証が要る承認の操作は、APPROVAL_AT の 1 つの口だけで受け、エージェント・予約・交換の経路からは届かない |
| ap-2-7 | Yes | act の無い REPAIR_DELEG_AT は宛先が agent-sts だけで、may_act の mTLS でしか交換できない。APPROVAL_AT もリソースの表で得られない（深さ 2 は専門家に回す） |
| q-authorize-service-and-user | Yes | 直接の相手は mTLS と呼ばれる側の許可リストで、利用者は sub で aoba-pdp に問い合わせて、別々に判断する |
| q-agent-short-lived-no-rt | Yes | agent-sts は RT を出さず、エージェントのトークンは 300 秒。RT は repair-console だけが持つ |
| q-outside-catalog | Yes | 管理用の口・試験用の口・旧経路・再送・手作業・トークンを使わない口が、範囲と扱いつきで答えられている |
| q-object-level-authz | Yes | agent-sts・ツールが台帳の側で持ち主・対象を照合している。承認の一覧の参照だけ絞り方が未記述（F2） |
| q-approval-from-as | Yes | 承認は approval-svc の記録で、agent-sts が記録から作って宛先に結び、受け手は条件つきの更新で 1 回だけ使う |
| q-operator-act | Yes | 代理ログインを作らず、上長も運用者も自分のログインで操作するので、監査で利用者の操作と区別できる |
| q-revocation-delivery | Yes | 止める単位ごとに最悪の秒数・分数があり、寿命の数字はそこから導いている。重要な操作はその場で問い合わせる |
| q-dependency-outage | Yes | 頼る先ごとに止める側に倒すと決め、REQ-13 の 60 分を 5 分の警報と電話の手配で受ける |
| op-proof-holder | 該当なし | 開いた問い。全箇所でトークンを持つ者と鍵を持つ者が一致し、更新時の扱いもある（4. に記述） |
| op-source-change | 該当なし | 開いた問い。異動を人事の画面から受け手の判断まで辿り、約束の無い区間は見つからなかった（4. に記述） |
| op-one-time | 該当なし | 開いた問い。並行・再送・記録先の障害の 3 つとも 2 回通らず、正しい 1 回も失わない（4. に記述） |
| pa-01 | Yes | repair_id・approval_ref とも、問 1 と usage・enforced_at で受け手ごとに決めることが書いてあり、表示用の値で認可していない |
| q-derived-value | Yes | repair_id はすべての受け手が対象の照合に使い、authorization_details は order-tool・lock-tool のトークンにだけ載る（data_category の食い違いは F3） |
| q-variant-comparison | Yes | 送信者制約の見送り・JWKS の reject・予約での交換の見送りのそれぞれに、開く攻撃・代わりの守り・確かめ方が書いてある |
| q-idp-diff-absorbed | Yes | ツール・approval-svc は agent-sts のトークンだけを受け、aoba-as のトークンは内側の受け手に届かない |
| q-original-principal | Yes | 交換の後も sub は担当者のままで、scope は上流・宛先・ロールの積に絞る。仲介の広い権限で頼んでいない |
| q-step-up-by-rs | Yes | 追加の認証を求めるかは、操作を受ける approval-svc が acr・auth_time を見て決める |
| q-long-running | Yes | 予約はトークンを持ち越さず、実行の時点で在籍・担当・委任・承認・行為者の登録・記録の改ざんを確かめ直す |
| q-copies-outlive | Yes | 写し（予約の記録・aoba-pdp の 60 秒のキャッシュ・監査ログ・lock-svc のコード）と、それぞれがいつまで残るかが書いてある |
| q-audit-correlation | Yes | sub・repair_id は同じ鍵・同じ正規化のハッシュで、act の連鎖・approval_ref・発注 ID・jti を全サービスが残す。鍵を替えても古い鍵を 3 年残す |
