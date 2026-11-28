# seeded-c の副作用の点検（C01〜C19）

点検した者：独立の点検者（埋め込みを作っていない）。材料：m-cc/・m-sc/・diff-c.txt・set2/seeded_errors.yaml（C01〜C19）。
行番号は m-sc のもの。「生成」は台帳から写った表（8.・9.1 の確かめ用の表・10.・11.・スキーマ）。

区分：
- **A（直す）**：対照の（clean の）事実を述べたまま残り、m-sc の中で埋め込みの誤りと食い違う。直さないと、レビュアーが「別の矛盾」として拾いうる。
- **J（要判断）**：食い違いは弱いか、直すと salience_phrase の写しが増える。
- **B（同じ誤りを指す矛盾）**：食い違いはあるが、指す先はその誤りそのもの。直さなくても別の指摘にはならないが、手がかりが増え、正解の salience・copies・difficulty の見込みより見つけやすくなる。

---

## 1. 同じ事実を述べる別の場所

### 1-A. 直すもの（12 件）

| # | 誤り | ファイル・行・見出し | 今の文（抜粋） | 直し方（唯一の欠陥を埋め込みにするため） |
|---|---|---|---|---|
| A1 | C01 | claims.yaml C-auth-time `description`（645） | 担当者が最後に認証した時刻（UNIX 時刻。**aoba-as の時計**） | 「…（UNIX 時刻。CONSOLE_AT・ID トークンは aoba-as が書く。APPROVAL_AT は agent-sts が書く）」など。あわせて同じ行の `source_system: aoba-as の認証の記録`・`recompute_trigger: [login]`・`on_revoke: ログインごとの値` も APPROVAL_AT の書き方に合わない（生成の 9.1 の表の 843 行 `login`・「ログインごとの値」、10. の 981 行「aoba-as の認証の記録」「login」に写る）。少なくとも source_system に「（APPROVAL_AT は agent-sts の交換の時刻）」、recompute_trigger に exchange を足す |
| A2 | C01 | design.md 付録 D M_token_validation 6.「時刻を比べるほかの箇所」（1358） | **auth_time（aoba-as の時計）**と今の時刻（approval-svc の時計） | 「auth_time（APPROVAL_AT では agent-sts が交換の時刻を書く）と今の時刻（approval-svc の時計）」。作者が挙げた候補どおり。key の C01 の locations にこの見出しがあるが、本文は対照のまま |
| A3 | C01 | catalog_answers.yaml I11（166・238）／design.md 11. I11 の行（1007、生成） | auth_time は元のログインのままなので、承認の判断（auth_time から 300 秒）は変わらない | 承認の判断は CONSOLE_AT の auth_time でなく APPROVAL_AT の（交換の）auth_time なので、根拠が対照の仕組みのまま。「CONSOLE_AT の auth_time は元のログインのまま。承認の判断は APPROVAL_AT で行う」程度に（弱いので A の中では優先度低） |
| A4 | C04 | claim_request_repair_id.md 問 14（22） | 委任とツールと承認のトークンのすべてに要る（**どの受け手も対象の照合に使う**） | 問 1・問 19 と食い違う。「（受け手は対象の照合か監査ログの相関に使う）」 |
| A5 | C04 | catalog_answers.yaml U02 の assumption（342）／design.md 11. U02 の行（1062、生成） | **ツールは**自分の DB アカウントで台帳を引き、対象が repair_id の修繕依頼のものかを照合する | 「order-tool・contact-tool・lock-tool は…照合する」か「ツールは自分の DB アカウントで台帳を引く」で止める |
| A6 | C04 | design.md 6. UC1 q-txn（439） | `C-repair-id` ｜ **全ツールの**対象の照合と監査ログ | 「ツールの対象の照合と、全ツールの監査ログ」など、payment-tool を照合に含めない書き方に |
| A7 | C06 | design.md M_token_validation 6.（1358） | 承認の期限・…は approval-svc・…が自分の時計で比べる（**承認の期限は approval-svc の時計だけで書いて比べる**） | U30 の「承認の期限と auth_time の比べにそのヘッダーの時刻を使う」と正面から食い違う。「だけ」を外し「（承認の期限は approval-svc が書いて比べる。比べる時刻は 11. の U30）」など。X-Test-Now の語を足すと copies が 2→3 になるので避ける。key の C06 の locations にこの見出しがあるが本文は対照のまま |
| A8 | C08 | claims.yaml C-sub `verification_method`（99） | aoba-pdp は **sub から**社員番号の属性を引いて人事の台帳と突き合わせる | 「aoba-pdp は sub（agent-sts からの問い合わせはログイン名）から…」。salience_phrase「preferred_username（ログイン名）」をそのまま足すと copies が増えるので語を変える |
| A9 | C08 | claims.yaml C-staff-number `rationale`（1154）／design.md 10. C-staff-number の行（959、生成） | 受け手は社員番号で判断せず、aoba-pdp が **sub から** aoba-as の利用者の属性で引く | A8 と同じ直し |
| A10 | C14 | design.md M_privacy_minimization 5.「API で渡す属性と受け手」（1569 付近） | contact-tool・lock-tool は repair_id・相手の種類・**作業員の ID を渡すだけ** | lock-tool は worker_name を SMS の本文に入れる（seeded）。「…作業員の ID を渡す（lock-tool は本文の作業員の氏名も渡す）」 |
| A11 | C19 | claim_request_approval_ref.md 問 16（24）／claim_request_repair_id.md 問 16（24） | **形式の検査は共通の検証部品** | 両方とも受け手に approval-svc がいる（問 5 で枠組みの検証と書き直した）。「形式の検査は共通の検証部品（approval-svc は承認の画面の Web の枠組み）」 |
| A12 | C19 | design.md M_token_validation 10. の repair-console の行（1397） | `repair-console` ｜ OIDC のライブラリ ｜ **同上に nonce** | **埋め込みで新しく生じた意味のずれ**。approval-svc の行を repair-console の上に差し込んだので、「同上」が approval-svc の行（alg と typ と必須クレームは枠組みの既定に任せる）を指すようになった。repair-console まで既定任せに読める＝鍵に無い第 2 の欠陥。approval-svc の行を repair-console の下に移すか、repair-console の明示の設定を書き下す |

同じ C19 で、M_token_validation 11. の台帳の ID の欄「`claims[].consumer_access_path`（書いていない。**全受け手が同じ部品のため**）」（1405）も食い違う。A12 と同じ版で「（書いていない。approval-svc のほかは同じ部品のため）」にする（**A12b として数える → A は計 13 件**）。

### 1-J. 要判断・弱い食い違い（7 件）

| # | 誤り | 場所 | 今の文 | 判断の材料 |
|---|---|---|---|---|
| J1 | C02 | claims.yaml C-aud `authoritative_writer`（157）→ 生成の 8. の aud の行（H2・H4・H5・H6・H7・H8・H10・H11・H12：672・683・694・707・718・729・743・754・765）・10.（971） | agent-sts（交換の要求の resource を、**リソースの表と照合してから書く**） | 作者が挙げた候補。seeded では表に無い /mcp にも出すので「照合してから」は不正確。直すと salience_phrase「https://*.aoba-sumai.example/mcp」が 10 行近く増える（copies 7→約 17）。語を足さずに「リソースの表と規則で確かめてから書く」程度にするか、このまま残して side_effect_note に書く |
| J2 | C03 | claims.yaml C-client-id `rationale`（347）・`authoritative_writer`（359、生成の 8. の client_id の行・10. に写る） | agent-sts は client_id を、**交換を求めた mTLS の相手のクライアントの登録から書き** | description（339）は「CONSOLE_AT・APPROVAL_AT・1 段目の REPAIR_DELEG_AT は repair-console」。seeded では相手がどのワークロードでもよいので、この書き方だと APPROVAL_AT の client_id は盗んだワークロードの登録になり、approval-svc の「client_id が repair-console」（375）・cnf（repair-console の証明書。577・771）で弾かれる。C03 の wrong の「APPROVAL_AT に交換できる」という影響が m-sc の中で打ち消される。直すなら「CONSOLE_AT の交換では CONSOLE_AT の client_id を写す」。点 3 の C03 も参照 |
| J3 | C04 | design.md M_authz_pdp 4.「オブジェクト単位」（1508） | repair_id（台帳と照合）｜ 担当の修繕依頼のものだけを扱う | 一般論で、3. の表で payment-tool を分けたので弱い。そのままでも可 |
| J4 | C08 | design.md 4. agent-sts の頼る先の表 aoba-as の行（328） | aoba-as（イントロスペクションと、aoba-pdp が引く **sub と社員番号の対応**） | agent-sts の経路はログイン名で引く。「利用者と社員番号の対応」とすれば足りる |
| J5 | C13 | claims.yaml C-scope `propagation_delay: 390`（422）→ 9.1 の生成の表（838）・10.（976）の「390 秒」 | propagation_delay 390 | 作者が挙げた候補。on_revoke は「連絡の 2 つはロールの剥奪では止まらない」と書くので、クレームの反映が 390 秒というのは連絡には当てはまらない。ただ、これに気づいたレビュアーが書くのは「連絡がロールの剥奪で止まらない」で、C13 の also_accepted に無い q-freshness/q-revocation 側の指摘になる（channel_note で 0.5 になりうると書かれた型）。390 は下書きの値として残し、side_effect_note に書くのが妥当 |
| J6 | C12 | design.md 3.1 の wl-ca の中間の CA の行（285）・catalog_answers.yaml 76 | 警報の後に当番が lock-svc の管理の画面で**一括で失効させる**（60 分の窓の対策） | 失効が錠に届くのは毎日 3 時なので、この対策は効かない。分数を書いていないので明示の食い違いではない。C12 を見つけた者には同じ誤りの帰結 |
| J7 | C09 | design.md 9.1 ORDER/PAYMENT/LOCK_TOOL_AT の行「下書きは 390」（798）・CONTACT_TOOL_AT の行「330（委任の停止）」（799） | 担当の付け替えの 3930 秒を書いていない | 食い違いではなく書き落とし（REPAIR_DELEG_AT の行には 3600 がある）。そのままでも可 |

### 1-B. 同じ誤りを指す矛盾（5 群。直さなくても別の指摘にはならないが、手がかりが増える）

| # | 誤り | 場所 | 今の文 | コメント |
|---|---|---|---|---|
| B1 | C15 | design.md 9.1 CONTACT_TOOL_AT の行（799）「330（委任の停止）」・長時間の処理の欄「—」／P4 9.「許す遅れ」（1303）「委任の停止から…手元のツールのトークンは最悪 330 秒」／9.2 委任の欄の行（907）「手元のトークンは最悪 330 秒」／5.1（419）「委任の停止は 330 秒」／9.1 CONSOLE_SESSION の行（793）「手元のトークンで最悪 330 秒動く」／token_types.yaml CONTACT_TOOL_AT `revocation`（402）「連絡は exp まで残る（最悪 330 秒）」（**long_running と同じ種別の中で 2 行下**） | 委任の停止から 330 秒で止まる | long_running の「開いた後に委任の停止を確かめない（最大 2 日）」と直接食い違う。key は C15 を copies 1・salience low・difficulty medium・q-revocation-delivery の見る欄は long_running を名指さないとしているが、9.1・P4 9.・revocation は q-revocation-delivery の見る欄そのもので、そこから矛盾として辿れる。見込みより易しくなる。下げたいなら、作者の考えとして筋の通る形にする：9.1 CONTACT_TOOL_AT の長時間の処理の欄に「返信の購読は開いたまま（token_types の long_running）」、P4 9. に「（開いた返信の購読は除く）」 |
| B2 | C16 | claim_request_approval_ref.md 問 21（29）／design.md B.（1129）「エージェントは承認の操作をできないので…承認に届く道は無い」／P4 5.（1259）「エージェントは承認の操作をできない」／P1 5.（1203）「エージェントは承認の操作をしないので」／catalog_answers.yaml I12 ワークロード（172）「エージェントは承認の操作をしない」／claims.yaml C-client-id の approval-svc の enforced_at（375）→ 8. の 769「エージェントが承認の操作をする経路を作らない」／6. UC3 q-actor（467） | エージェントは承認の操作をできない | 作者が挙げた候補（7 か所）。H8 の note は「エージェントが lock-tool を通じて承認の記録の not_after を更新する」。もう 2 つ：8. の前書き（635）「scope は上流の部分集合」と 4. の E-token-exchange.2（357）「満たす」（H8 を含む）も H8 の scope と食い違う（後者は対照でも authorization_details の warn で同じ書き方なので弱い）。また M_authz_pdp 5. の段落（1523）は approval-svc の口を「承認の依頼・使用済み・予約済みは order-tool・lock-tool・order-scheduler、承認の操作は APPROVAL_AT だけ」と列挙し、lock-tool の not_after の更新の口が無い。下げたいなら、H8 の note・1. の warn の説明・P4 6. に「承認の操作でなく、承認済みの記録の not_after の更新（lock-tool が approval-svc の更新の口で行う）」と作者の言い分を足し、5. の段落の口の列挙に lock-tool の時間帯の更新を足す。そうすれば「承認の操作をできない」の文は作者の考えのまま字義どおりに残る |
| B3 | C17 | claims.yaml C-authorization-details `note`（744） | ログには残さず、**ログの approval_ref から** approval-svc の記録を引く | LOCK_TOOL_AT の authorization_details について、lock-tool のログには approval_ref が無い。absent の C17（difficulty hard）への手がかりになる。直すなら「order-tool のログの approval_ref から」だが、それは答えを書くのに近い。このまま残して見込みを見直すか、文を「承認の内容は approval-svc の記録にある」に変える |
| B4 | C05 | design.md 3.1（269「費用は aoba-pdp の可用性への依存」・275「頼る先が止まったときに通すこと（止める側に倒す）」）／4. の頼る先の表（324〜332「どれも止める側に倒す」）／M_authz_pdp 5. の段落（1523） | 止める側に倒す | C05 の「目的と仕組みの不一致」の「目的」の側で、意図どおり。直さない |
| B5 | C18 | design.md 3.1 重点の行（270）の確かめ方 | 各ツールの結合試験で、同じ ID の要求を並行に 2 件送り、1 回だけ実行されること | 試験に通ると書いているわけではないので弱い。意図どおりの「目的」の側。直さない |

### 1-C. seeded の文があるのに `locations` に無い場所（1 件）

| 誤り | 場所 | 中身 |
|---|---|---|
| C17 | design.md 8. ホップごとの表の矢印の表 H14 の approval_ref の行（778、生成） | integrity_until から写った「書き先：order-tool・approval-svc・agent-sts・order-scheduler の監査ログ」（lock-tool が抜けた）。C17 の locations に `design.md 8.` が無い（C11 の locations に 8. はあるが、それは同じ行の enforced_at の部分） |

参考（locations にあるのに seeded の文が無い場所。form: absent の C11・C17 の場所を除く）：C01 の hops.yaml H12 の validates・design.md B.・M_token_validation 6.、C06 の M_token_validation 6.、C12 の「要求の要約」（REQ-06 の要求の文）。このうち M_token_validation 6. は対照の文のままで A2・A7 の食い違いになっている。

---

## 2. どの誤りでも説明できない差分の塊

**0 件。** diff-c.txt のすべての塊を C01〜C19 に当てた。

| 塊（m-sc 側） | 当てた誤り |
|---|---|
| catalog 129 / 170 / 396 / 422 / 428–430 / 459–462 | C13 / C01 / C17 / C09 / C15 / C06 |
| claim_request_approval_ref 問 5 | C19 |
| claim_request_repair_id 問 1・問 19 / 問 2 / 問 5 | C04 / C09 / C19 |
| claims C-sub not_meaning（「受け手は sub で照合し」を削る）・on_revoke | C08（key の locations にある）・C05 |
| claims C-aud / C-client-id / C-scope ×4 / C-auth-time ×3 / C-authorization-details ×3 / C-repair-id ×3 / C-approval-ref ×2 | C02 / C03 / C13 / C01 / C14 / C04・C09 / C11・C17 |
| design 1.（warn の数 2→3、L16 の 2 行） | C16 |
| design 2.2 lock-svc の管理の画面 | C10 |
| design 3.1：270（依頼済み）/ 272（wl-ca）/ 280（毎日 3 時）/ 281（監査ログの記述を消す＝C10、毎日 3 時・訓練の「15 分以内」を消す＝C12） | C18 / C03 / C12 / C10・C12 |
| design 4.：317・318・342 | C03・C02・C03 |
| design 5.・5.1・7. | C01・C13・C01 |
| design 8.（ホップの表・矢印の表） | C02・C03・C04・C08・C11・C13・C16・C17・C18・C01 |
| design 9.1・9.2 | C05・C09・C12・C13・C08 |
| design 10.・11.（回答の数 28→30、U14・U21・U23・U30） | C01・C02・C04・C13・C06・C15・C17・C09 |
| design 12.・A. | C12・C19 |
| design 付録 D：P4 1.・4.・5.（左の欄の「説明の文も添える」と右の欄）・6.・8.、M_token_validation 1.・6.・10.・11.、M_authz_pdp 3.・5.（2 行）、M_privacy 1. | C02・C02・C07・C14・C16・C17、C19・C18・C19・C19、C04・C08・C05・C09、C14 |
| hops H2 / H4 / H7 / H8（scope・note）/ H14 | C03・C08 / C02 / C04・C18 / C16 / C11 |
| schemas（ORDER・LOCK の発行側・受け手側の 4 つ） | C14 |
| token_types：CONSOLE_AT の sender_constraint / REPAIR_DELEG_AT revocation / CONTACT_TOOL_AT long_running・revocation / APPROVAL_AT rationale | C03 / C09 / C15・C13 / C01 |

---

## 3. 誤りごとの性質

| 誤り | core は 1 つの事実か | m-sc だけで言えるか | 答えを明かす自己矛盾・誤りでない恐れ |
|---|---|---|---|
| C01 | はい | はい（C-auth-time の rationale・writer） | **同じ行に答えがある**：C-auth-time の not_meaning「トークンの発行の時刻ではない（それは iat）」と、seeded の「交換した時刻を書く」（＝APPROVAL_AT の iat と同じ）が同じ行に並ぶ。rationale も「朝のログインのまま承認できない」の直後に seeded の文。difficulty easy には合うが、A1 の残りの欄と合わせて易しすぎる |
| C02 | はい | はい（P4 4.・H4） | なし。P4 4. の理由の欄「入居者の依頼の文に紛れた指示で宛先を変えさせない」が同じ行で食い違うのは、意図した目的と仕組みの不一致 |
| C03 | はい | はい（H2・3.1） | **誤りとして弱い恐れ**：CONSOLE_AT は repair-console のサーバーの外に出ない（3.1・4.）。3.1 の見送りの理由も「網の外で盗んでも」と書き換えて筋を通した。J2 の client_id の書き方と approval-svc の cnf・client_id の照合で、APPROVAL_AT の経路の影響は m-sc の中で打ち消される。残る影響は REPAIR_DELEG_AT だけ。レビュアーが「多層の防御が 1 つ減っただけ」として Major にしない恐れ |
| C04 | はい | はい（H7・M_authz_pdp 3.） | なし（A4〜A6 を直せば） |
| C05 | はい | はい（C-sub の on_revoke と 3.1 の「止める側に倒す」） | なし。食い違いは意図した目的の側（B4） |
| C06 | ほぼ（「口が残る」と「閉じる日が無い」の 2 つを含む。1 つの事実として読める） | はい（U30） | A7 を直さないと M_token_validation 6. の「approval-svc の時計だけ」と食い違う（同じ誤りを指す） |
| C07 | はい | はい（P4 5.） | 同じ行の左の欄「エージェントの申告の金額・部屋を使わない」と右の欄が並ぶ。意図した不一致で、copies 1 の low には妥当 |
| C08 | はい | はい（H2 と、claims・CONSOLE_AT の required_claims に preferred_username が無いこと） | なし（A8・A9 を直せば） |
| C09 | はい | はい（9.2 の行に 600 と 3600 が並ぶ） | 同じ行の並びで答えが見える（P1・easy の意図どおり） |
| C10 | はい | はい（2.2） | なし |
| C11 | はい（absent） | はい（C-approval-ref の enforced_at の「（order-tool・lock-tool の更新）」、H14、REQ-08 の括弧を突き合わせる） | なし。enforced_at の括弧で 2 つだけを挙げているので、absent にしては見つけやすい |
| C12 | はい | はい（9.1・3.1 と REQ-06 の 15 分） | なし |
| C13 | はい | はい（C-scope の writer・rationale） | J5（propagation_delay 390）。帰結（ロールの剥奪で連絡が止まらない）を on_revoke・9.1・9.2 に書いたので、q-revocation 側から拾われ 0.5 になりうる（channel_note のとおり） |
| C14 | はい | はい（C-authorization-details の description・スキーマ） | なし（A10 を直せば） |
| C15 | はい | はい（CONTACT_TOOL_AT の long_running） | **B1：同じ種別の revocation（2 行下）と 9.1・P4 9.・5.1 の「330 秒」と食い違う**。salience low・copies 1・medium の見込みより見つけやすい |
| C16 | はい | はい（L16 の warn・H8 の note） | **B2：「エージェントは承認の操作をできない」の 7 か所と 8. の前書きの「上流の部分集合」と食い違う**。どれも C16 を指すので別の指摘にはならないが、lint に加えて多くの手がかりがある |
| C17 | はい（absent） | はい（P4 8.・U14・integrity_until に lock-tool が無く、LOCK_TOOL_AT は approval_ref を運ぶ） | **誤りとして弱い恐れ**：lock-svc は承認 ID ごとにコードを 1 つ作り（C-unlock-code の assumption）、lock-tool のログには発行の参照（code_ref）がある。lock-svc の側で code_ref と承認 ID を結べるなら「1 本につなげられない」は成り立たない。lock-svc のログが承認 ID を持つかは m-sc に書いていないが、レビュアーが「つなげられる」と反論しうる。B3 は手がかり |
| C18 | はい | はい（H7・M_token_validation 6.） | なし。経理の側が発注 ID で重複を除かないことは書いていない（書いていないことに頼る） |
| C19 | はい | はい（M_token_validation 10.・11.） | A11・A12 を直さないと、C19 と別に「repair-console も既定任せ」（A12）という鍵に無い指摘が出うる |

---

## 件数のまとめ

- 点 1：A（直す）13 件（A1〜A12、A12b）、J（要判断）7 件、B（同じ誤りを指す矛盾）5 群、locations の漏れ 1 件（C17 の design.md 8.）
- 点 2：説明できない塊 0 件
- 点 3：19 件を見た。目立つ注意 5 件（C01 は同じ行に答えがある、C03 と C17 は誤りとして弱い恐れ、C15 と C16 は手がかりが見込みより多い）


## 回り 9 の直しの副作用の確かめ（PR #86 の再点検の後）

作成・清掃・埋め込みに関わらない別のセッションが、回り 9 の直し（`git diff ef62359 c8e1fe8 -- set2/seeded-c`）を読み、埋め込んだ誤りの見つけやすさが変わったかを確かめた出力です（下に、そのまま）。

- 結論：機械で決まる値（手がかり・読む場所・難しさ・目立ちやすさ）は、19 件とも変わらない
- C18 と C12 は、近くに正しい形が書き足されて見つけやすくなったので、対照と seeded の両方に同じ最小の編集を当てて戻した。C18：3.1 の連絡の手順を CONTACT_TOOL_AT の purpose へ移し、3.1 には参照だけを残した。C12：錠の機器の時計の 2 行から「1 時間ごと」を外し、26 時間の上限にした
- C10 の任意の直しは入れていない（下の表のとおり、理由の文は否定されておらず、easy・low の作りは保たれている）
- 直した後の copies は 17 件とも変わらない（C12 は 4 のまま）

# seeded-c 掃除の 9 回目の副作用の点検（protocol 8.2）

点検者：独立の点検者（設計・掃除・埋め込みをしていない）。
材料：`r9-seeded-diff.txt`（a-F1〜a-F6 の 6 件の修正。`controlc_r9.py` で対照と同じ文）、`m9s/`、`m9c/`（比べるため）、正解の一覧 `set2/seeded_errors.yaml`。

## 機械で決まる値（全件に共通）

- **copies**：`m9s/` の全ファイルで salience_phrase を含む行を数え直した（`cnt9.py`）。17 件とも正解の一覧の値と同じ（C01 8, C02 7, C03 10, C04 8, C05 4, C06 2, C07 1, C08 4, C09 7, C10 1, C12 4, C13 15, C14 6, C15 1, C16 3, C18 4, C19 1）。9 回目はどの salience_phrase も足しておらず、消してもいない（スクリプトの PHRASES の確かめどおり）。→ **salience は全件変わらない**。
- **signpost**：9 回目は 1 枚の問い（手がかり・見る欄）を変えていないので、全件変わらない。
- **span**：誤りの文の場所は変わっていない。protocol の規則（誤りを確かめるのに読む場所の数）では全件変わらない。ただし C18 と C12 は、近くに足した文のために、実際に読む場所が規則の値より少なくて済むようになった（下の表の「見つけやすさ」の判断。規則の外）。

## 表

| 誤り | 9 回目が近くに足したもの | 機械の分類の変化 | 見つけやすさの判断 | 最小の修正（対照・seeded に同じ文で） |
| --- | --- | --- | --- | --- |
| **C18**（hard・P2・2+・open_prompt。支払いを送ってから「依頼済み」） | a-F4：3.1 の「重複の実行を、業務の ID で防ぐ」の**同じセル**で、支払いの文の 1 つ後の節に、連絡の正しい形を足した：「下書き→送信中」の条件つきの更新の後に、下書きの ID を重複の鍵にして通知の基盤に送り、「送信中→送信済み」にする。結果不明なら同じ ID で送り直し、通知の基盤が重複を捨てる。token_types の CONTACT_TOOL_AT の purpose にも「通知の基盤も下書きの ID で重複を捨てる」 | なし（P2・2+・hard・copies 4・high） | **見つけやすくなった（要修正）**。足した文は正解の clean（「完了の報告済み→依頼中」の条件つきの更新で 1 件だけ通してから経理に送る）と同じ形で、誤りに欠けている 2 点（送る前に途中の状態へ条件つきで更新すること、受け手側の重複の鍵）をちょうど補う。同じセルの隣の節なので、支払いの節と並べるだけで「確かめ→送信→使用済み」の順と経理側の重複の鍵が無いことが分かる。span 2+（経理の扱いを辿る）の作りが、実際には 1 か所で済む。9 回目の前から、同じセルに解錠の「承認 ID と送信の回」の重複の鍵があった（これが元の水準）。連絡の文で、手本がもう 1 つ増え、しかも状態の遷移まで同じ形になった | 3.1 のセルの連絡の節を、9 回目の前の長さに戻して参照だけにする：「連絡は contact-tool が採番した下書きの ID（送る順と重複の鍵は token_types の CONTACT_TOOL_AT の purpose）」。足した手順の文はそのまま CONTACT_TOOL_AT の purpose に移す：「（送信は contact-tool が採番した下書きの ID で 1 回だけ。「下書き→送信中」の条件つきの更新の後に、下書きの ID を重複を避ける鍵にして通知の基盤に送り、「送信中→送信済み」にする。結果が分からなければ同じ下書きの ID で送り直し、通知の基盤が重複を捨てる）」。F4 の指摘の場所には CONTACT_TOOL_AT の purpose が入っているので、掃除の欠陥は戻らない。C18 の場所（H7・M_token_validation 6.・3.1・8.）には手本が残らない。purpose は C13（revocation）・C15（long_running）と同じ行の別の列だが、購読・scope には触れないので影響は無い |
| **C12**（medium・P1・2+・high。失効が錠に届くのは毎日 3 時の同期） | a-F5：M_token_validation 6. に「スマートロックの機器の時計」の行（lock-svc は**錠の網を通して機器の時計を 1 時間ごとに合わせ**、2 時間を超えて合わせていない機器にはコードを作らない）と、**12.（C12 の場所の 1 つ）**に「スマートロックの機器の時計の合わせ」の行（1 時間ごとに合わせられること）。12. の 2 行下の seeded だけの行は「lock-svc の毎日 3 時の同期で錠に失効が届くこと（**錠の機器は同期の時刻に網につながる前提**…）」 | なし（P1・2+・medium・copies 4・high） | **食い違いが生じ、見つけやすくなった（要修正）**。seeded の行は、失効が日に 1 回しか届かない理由として「機器は同期の時刻に網につながる」を置いている。新しい 2 行は、lock-svc が少なくとも 1 時間ごとに錠の網で機器に届く（届かない機器は 2 時間で止める）と書く。同じ 12. の表の中で前提が否定されるので、3 時の同期が錠の制約でなく設計の選択だと分かり、REQ-06 の 15 分と比べる前に疑いが向く。対照は失効をすぐ届けるので、この食い違いは seeded にしかない（対照と seeded の差が、誤りの核のほかにもう 1 つ増える） | 2 行から、網につながる頻度を書いた部分を外す（F5 の欠陥である「合わせ方」と「ずれたら止める」は残す）。M_token_validation 6.：「lock-svc は、機器が lock-svc とつながるたびに機器の時計を合わせ、最後に合わせてから 26 時間を超えた機器か、ずれが 60 秒を超えた機器にはコードを作らない（止める側に倒す。発行は lock-tool に失敗を返す）」。12.：「lock-svc が、機器とつながるたびに機器の時計を合わせられること、合わせられない機器を見分けてコードを作らないこと（機器の提供元の仕様書を読んだだけ）」「確かめ方：試験の部屋の機器の網を切り、26 時間の後にコードの作成が拒否されることを確かめる」。対照（すぐ届ける）でも seeded（日に 1 回つながる）でも成り立つ。「毎日 3 時の同期」の語は足さない（copies が変わらない） |
| **C10**（easy・P1・1・low。失効を頼んだ担当者の ID で記録） | a-F1：2.1 に当番の行（`C-sub` は自分の利用者 ID）。2.2 の lock-svc の管理の画面の行の**すぐ下**に停止の宣言の行（`C-sub` は当番、「宣言した当番の sub・時刻・警報の ID」を記録、監査ログに残る）。a-F2：3.1 の見送りの行で、lock-svc が approval-svc の失効の通知の口に知らせ、approval-svc が記録を「取り消し」にする（当番は記録を書かない） | なし（P1・1・easy・copies 1・low） | **少し見つけやすくなった（修正は任意）**。同じ主体（当番）の別の操作が、隣の行で自分の sub で記録される。ただし 2.2 には 9 回目の前から「監査ログの sub は上長」「監査ログの sub は運用者」の行があり、lock-svc の行の同じセルにも「自分のログインで入る」があった。対比は元からあり、増えたのは 1 行分。誤りの理由「approval-svc の取り消しの記録とそろえるため」は、approval-svc が lock-svc の通知で状態をそろえるようになって弱まったが、そろえるのは状態で、記録の行為者の ID は通知の文に無いので、理由は否定されていない。誤りの文は 2.2 の 1 行のままで、easy・low の作りは保たれている | 任意：(1) 2.2 の停止の宣言の行を lock-svc の行の隣から、管理用の口の行の後（緊急時の特権の行の前）へ移す。(2) 3.1 の「（当番は記録を書かない）」を消す（直前の「approval-svc がその承認の記録を「取り消し」にする」で書き手は決まっているので、F2 は戻らない）。どちらも F1・F2 の中身を消さない |
| C06（easy・P1・high。X-Test-Now） | a-F5：M_token_validation 6. に機器の時計を合わせて、ずれたら止める行 | なし | ごくわずか。時計を信じる側の正しい扱いが同じ表に 1 行増えたが、承認の期限の時計の文（側面の修正済み）が元からある。easy・high で影響は無視できる | 不要（C12 の修正の後も同じ） |
| C01（easy・P1・high。auth_time に交換の時刻） | a-F1：2.2 の停止の宣言の行で、repair-console が ID トークンの acr が mfa で auth_time から 300 秒以内を確かめる | なし | ごくわずか。aoba-as の auth_time をそのまま使う正しい追加認証の形が 2.2 に出たが、C01 の場所（C-auth-time・APPROVAL_AT・I12 など）から離れ、copies 8 の high | 不要 |
| C14（medium・P2・high。worker_name を値で載せる） | a-F3：M_privacy_minimization 5.（C14 の場所。誤りの文の 2 行下）に、上長への一覧を ID だけにし部屋と時間帯を載せない行。3.1 の一覧から部屋・協力会社・作業員を外した | なし | ごくわずか。同じ表に「ID だけを渡す」最小化の手本が 1 行増えたが、対象はトークンでなくメールの一覧で、作業員の氏名には触れない。同じ表の「宛先は通知の基盤だけが台帳から引く」は元からあった | 不要 |
| C11（medium・absent。H14 で承認者を確かめ直さない） | a-F6：C-approval-ref の enforced_at・H12・H14 の validates・REQ-05 の要約で「依頼の担当者」→「今の担当者」 | なし | 変わらない。取り下げの主体の言い換えで、使用済みにするときの確かめ直しの有無に触れない | 不要 |
| C03（H12 の cnf） | a-F6：H12 の validates の同じ行の別の項目 | なし | 変わらない | 不要 |
| C16（M_authz_pdp 5. の口の列挙） | a-F2：M_authz_pdp 5. に「approval-svc の失効の通知の口を呼べる相手は lock-svc だけ」 | なし | 変わらない（not_after の更新の口の記述に触れない） | 不要 |
| C05・C08・C09（M_authz_pdp 5.） | 同上 | なし | 変わらない | 不要 |
| C13・C15（CONTACT_TOOL_AT） | a-F4：同じ行の purpose に重複の鍵の 1 文 | なし | 変わらない（revocation・long_running の列に触れない） | 不要（C18 の修正で purpose が伸びても同じ） |
| C17（absent。lock-tool のログに approval_ref が無い） | a-F1 の停止の記録の項目、a-F3 の M_privacy_minimization 5. の行 | なし | 変わらない（M_privacy_minimization 7.・P4 8.・U14 に触れない） | 不要 |
| C02・C04・C07・C19 | 近くの変更なし | なし | 変わらない | 不要 |

## 修正が要る誤り

- **C18**（必須）：3.1 の同じセルの連絡の正しい形が、誤りの clean と同じ形の手本になっている。
- **C12**（必須）：12.・M_token_validation 6. の「1 時間ごとに錠の網で合わせる」が、seeded だけにある「機器は同期の時刻に網につながる前提」を否定する。
- C10（任意）：対比は元からあり、増えたのは隣の 1 行。easy・low の作りは保たれている。

修正の後に確かめること：`cnt9.py` で copies が変わらないこと（とくに C12 の「毎日 3 時の同期」が 4 のまま）、対照と seeded の差が埋め込みの行だけであること、C-authorization-details を指す 2 行の台帳の ID が変わらないこと。
