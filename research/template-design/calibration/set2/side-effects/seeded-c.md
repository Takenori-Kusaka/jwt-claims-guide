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
