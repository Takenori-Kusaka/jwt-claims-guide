# 清掃の指摘ごとの判定（2 組目、#82）

> **LLM による作業。人による検証ではない。** 判定は作成を取りまとめたセッションが行った（独立ではない）。

- **再構成した記録**：回り 1〜8 の判定は、清掃の間は件数と例外（真でないもの）だけを、直しを頼むメッセージに書いていた。この表は、`cleaning/` のレビューの出力（指摘の行）と、そのメッセージに書いた例外の一覧から、PR #86 の独立点検の後に機械で組み立てた。理由の列の「真」は「指摘のとおり、双子の両方にある設計の欠陥。直すか 3.1 の見送りにした」の意味で、指摘ごとの個別の理由は、例外の行にだけ書いた。回り 9（PR #86 の独立点検の後）は、7 件とも真で、直しを双子の両方に同じ編集で当てた（理由は各指摘のとおり。a-F1 と b-F1 は同じ欠陥）
- 区分：真（基の設計の欠陥）／誤検出／確認の依頼（初回の手順の 7. の R4）／道具・教材への指摘（2 組目の改訂 S5）
- 直したコミット：その回りの直しを入れたコミット。直しの中身は、対照の作成のセッションの報告（指摘ごとの 1 行）を `cleaning-log.md` の 1. にまとめた
- 指摘の文は、各レビューの出力の「内容」の先頭 80 字。重大度・種別はレビュアーが付けたもの

## r1-control-c-1.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r1-control-c-1-F1 | Major | REQ-05 の「上長は、その修繕依頼の担当でないこと」を、approval-svc は承認の時点に aoba-pdp で「今の担当でないか」として確かめるだけ | 真 | — | 2e30afa |
| r1-control-c-1-F2 | Major | 承認の要否は order-tool が確定・予約のたびに発注の台帳で部屋の累計を数えて決めるが、「数える」と「確定する（下書き→確定の条件つきの更新）」の間を部 | 真 | — | 2e30afa |
| r1-control-c-1-F3 | Major | REQ-08 は退職・異動・ロールの剥奪を人事の台帳に「登録してから」重要な操作は 2 分、そのほかは 10 分で止めると求める。設計の最悪 60 秒・390  | 真 | — | 2e30afa |
| r1-control-c-1-F4 | Major | agent-sts は交換のたびに行為者（may_act・クライアントの登録・委任の表）も確かめるが、order-scheduler が実行の時点で引き直すのは | 真 | — | 2e30afa |
| r1-control-c-1-F5 | Minor | 台帳は予約の記録を書けるのは order-tool の DB アカウントだけとし、UC4 の q-holder を「不要」とする根拠にしているが、2.2・3.1 | 真 | — | 2e30afa |
| r1-control-c-1-F6 | Minor | 承認・却下・取り下げの APPROVAL_AT の repair_id は、agent-sts が approval_ref の承認の記録から写した値で、app | 真 | — | 2e30afa |
| r1-control-c-1-F7 | Minor | ログアウト・セッションの終了の後も、エージェントは手元の REPAIR_DELEG_AT とツールのトークンで最悪 330 秒動ける。REQ-03 にはこの遅れ | 真 | — | 2e30afa |
| r1-control-c-1-F8 | Minor | 停止の間の電話での発注（REQ-13）は、後で修繕依頼の台帳に記録するとあるが、発注の台帳に入るか、部屋ごとの直近 30 日の累計に数えるかが書いていない。入ら | 真 | — | 2e30afa |
| r1-control-c-1-F9 | Minor | aoba-pdp は repair_id をトークンでなく予約の記録の値（H13）で受けるのに、台帳の consumers には入り、25 問の回答の受け手には | 真 | — | 2e30afa |

## r1-control-c-2.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r1-control-c-2-F1 | Major | 中間の CA の鍵が漏れたとき「偽の証明書でも REPAIR_DELEG_AT かツールのトークンを持たなければ何も呼べない」と書いてある。しかし、lock-s | 真 | — | 2e30afa |
| r1-control-c-2-F2 | Major | 承認の要否は、確定・予約のたびに累計を読んで決める。しかし、同じ部屋の確定・予約を直列にする仕組み（部屋ごとの錠、累計の行に対する条件つきの更新など）が無い。累 | 真 | — | 2e30afa |
| r1-control-c-2-F3 | Minor | warn の理由に「足すのは…制限で、範囲を広げるものではない」とある。しかし H5 の authorization_details（vendor-order） | 真 | — | 2e30afa |
| r1-control-c-2-F4 | Minor | 台帳では、agent-sts はどの交換でも「修繕依頼の台帳で修繕依頼の担当が sub（で委任の欄が有効）」を確かめる、と書いてある。しかし H12 で APP | 真 | — | 2e30afa |
| r1-control-c-2-F5 | Minor | 修繕依頼の担当は、REQ-05（上長は担当でない）・REQ-06（担当者本人が承認）・agent-sts の交換・aoba-pdp の判断の元データ。9.2 は | 真 | — | 2e30afa |
| r1-control-c-2-F6 | Minor | 解錠の「1 回だけ」は、lock-svc が承認 ID を重複を避ける鍵として受けることに頼っている。しかし lock-svc は下流の仕組み（2. の範囲の外 | 真 | — | 2e30afa |
| r1-control-c-2-F7 | Minor | C-repair-id の consumers と enforced_at に aoba-pdp があるが、aoba-pdp に repair_id を載せたト | 真 | — | 2e30afa |

## r2-control-c-1.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r2-control-c-1-F1 | Major | 許可リストの宣言と、それに頼る仕組みが食い違う。(a) 2.2 では、担当の割り当ての前に repair-console が「セッションの sub が修繕課の課 | 真 | — | a9fd530 |
| r2-control-c-1-F2 | Major | 権限・識別子の元のデータを書ける者を全部は数えていない。設計は、修繕依頼の台帳の (1) 修繕依頼の部屋（lock-tool の unit_id の照合と解錠の | 真 | — | a9fd530 |
| r2-control-c-1-F3 | Minor | APPROVAL_AT の repair_id の出どころの記述が、ほかの 4 か所と食い違う。C-repair-id の authoritative_writ | 真 | — | a9fd530 |
| r2-control-c-1-F4 | Minor | 時刻のメンバーの比べ方が 1 つに決まっていない。not_before・not_after は「RFC 3339 の UTC の時刻の文字列」で、lock-to | 真 | — | a9fd530 |
| r2-control-c-1-F5 | Minor | P4 の 7. はツールでも深さ 2 を超える act を拒否すると書くが、C-act の enforced_at と各ホップの validates のツールの | 真 | — | a9fd530 |

## r2-control-c-2.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r2-control-c-2-R-1 | Minor | APPROVAL_AT の repair_id の出どころが 2 か所で食い違う。書き手・H12・4. は「画面で開いた修繕依頼を、sub が担当か上長かを確か | 真 | — | a9fd530 |
| r2-control-c-2-R-2 | Minor | 「確定しないまま止めた発注は、上長が承認を取り下げて承認し直す」とあるが、その時点の承認は使用済み（order-tool が確定の前に使用済みにする）で、REQ | 真 | — | a9fd530 |
| r2-control-c-2-R-3 | Minor | 証明書は毎日更新されて拇印が変わるのに、拇印を含む登録と各受け手（agent-sts・aoba-pdp・approval-svc・修繕依頼の台帳・下流の仕組み） | 真 | — | a9fd530 |
| r2-control-c-2-R-4 | Minor | 発注の承認者の条件（REQ-05：担当になったことがない人）は修繕依頼の台帳の担当の履歴で、委任の可否は同じ台帳の担当と委任の欄で、ロールは人事の台帳で決まる。 | 真 | — | a9fd530 |

## r3-control-c-1.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r3-control-c-1-F1 | Major | 台帳の contact-tool の照合は、連絡の相手を「repair_id の修繕依頼の入居者と、その発注の協力会社の窓口」に限るとしか書いておらず、行為者で | 真 | — | 64ba505 |
| r3-control-c-1-F2 | Minor | approval_ref の無い APPROVAL_AT で行う「承認の一覧の参照」について、approval-svc が返す記録を、トークンの repair_ | 真 | — | 64ba505 |
| r3-control-c-1-F3 | Minor | どちらの行も pii_category は「個人情報」なのに、data_category は [system.operations]（利用者のデータでない区分） | 真 | — | 64ba505 |
| r3-control-c-1-F4 | Minor | ツールは「client_id が act の最も外側と同じエージェントか」を確かめると書いてある。しかし client_id は登録の名前（enum の "re | 真 | — | 64ba505 |
| r3-control-c-1-F5 | Minor | REQ-12 は入居者の個人情報（氏名・電話番号・住所）を「修繕依頼の台帳・通知の基盤だけが扱う」と求めている。しかし設計では、contact-tool が修繕 | 真 | — | 64ba505 |

## r3-control-c-2.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r3-control-c-2-F1 | Major | 承認の要否（REQ-05 の部屋の累計。取り消した発注を除く）と支払いの可否・額（確定済み・完了の報告・確定額）は、発注の台帳の値で決まる。ところが発注の台帳に | 真 | — | 64ba505 |
| r3-control-c-2-F2 | Minor | 解錠コードの送信について、通知の基盤は承認 ID を送信の重複を避ける鍵にすると書く一方、作業員に届かないと担当者が知らせたら、エージェントが同じ承認 ID で | 真 | — | 64ba505 |
| r3-control-c-2-F3 | Minor | 止める単位を利用者・委任・エージェントで並べた表はあるが、取引先（協力会社・作業員）の単位が無い。発行した解錠コードは not_after（最大 4 時間）まで | 真 | — | 64ba505 |

## r4-control-c-1.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r4-control-c-1-F1 | Minor | H2 の CONSOLE_AT の scope の上限は 8 個（openid・orders:draft・orders:place・tenant.message | 真 | — | 64ba505 |

## r4-control-c-2.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r4-control-c-2-F1 | Major | REQ-09 は「委任をやめたら予約した発注は実行しない」を求めている。しかし order-scheduler が確かめるのは、実行の時点で委任の欄が今「停止」 | 真 | — | 64ba505 |
| r4-control-c-2-F2 | Minor | 自動で止めない代わりの守りは、課長が「発行中のコードの一覧」を見て取り消すこと。しかし APPROVAL_AT は 1 つの修繕依頼（repair_id）に限ら | 真 | — | 64ba505 |
| r4-control-c-2-F3 | Minor | 事後の確認は承認の画面で行うとあるが、その操作がどこにも定義されていない：付録 B の追加の認証の対象に無い（mfa・300 秒を求めるかが分からない）、H12 | 真 | — | 64ba505 |
| r4-control-c-2-F4 | Minor | 件数の記述と中身が合わない。どれかを数え落としたのか、後から足した行の記述を直していないのかが読み取れず、カタログの外の場面の点検の範囲が確かめにくい | 真 | — | 64ba505 |
| r4-control-c-2-F5 | Minor | 同じ contact-tool の照合について、2 つの行で連絡の相手の範囲が食い違っている。C-sub の行のとおりに作ると、repair-agent が協力 | 真 | — | 64ba505 |

## r5-control-c-1.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r5-control-c-1-F1 | Major | DB の管理者 2 人は承認の記録の状態を直接書き換えられる（例：承認待ちの 10 万円超の発注や解錠の依頼を「承認済み」にする）。order-tool・loc | 真 | — | d0b3c12 |
| r5-control-c-1-F2 | Major | 依存先が止まると「止める側に倒す」と決めているが、その結果、止める操作も止まる。発行済みの解錠コードの取り消しは repair-console → agent- | 真 | — | d0b3c12 |
| r5-control-c-1-F3 | Minor | lint の L16 の warn（authorization_details の lock-code が上流の H4 に無い。下流で広げている）の理由は「ag | 真 | — | d0b3c12 |
| r5-control-c-1-F4 | Minor | 「漏れた REPAIR_DELEG_AT は may_act の主体の鍵が無ければ使えない」「トークンの要る口は開かない」と書くが、agent-sts は ma | 真 | — | d0b3c12 |
| r5-control-c-1-F5 | Minor | act（入れ子を含む）は行為者を表す仕組みで、経路（どこを経由したか）の証跡ではない（contrasts/act-txn-workload の m-10）。UC | 真 | — | d0b3c12 |
| r5-control-c-1-F6 | Minor | REQ-05 は「承認は使われる前なら取り下げられる」と求める。しかし、誰が取り下げてよいか（承認した上長だけか、依頼した担当者か、同じ課の課長か）が設計のどこ | 真 | — | d0b3c12 |
| r5-control-c-1-F7 | Minor | 委任を止めて有効にし直す前の REPAIR_DELEG_AT を拒む判断は、agent-sts の時計で書いた iat と、修繕依頼の台帳が書いた世代の開始の時 | 真 | — | d0b3c12 |

## r5-control-c-2.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r5-control-c-2-F1 | Major | contact-tool の「返信の読み取り」（tenant.message:read）には、scope の確かめしか書いていない。読む対象（返信・やり取り）が | 真 | — | d0b3c12 |
| r5-control-c-2-F2 | Minor | 委任を止めて有効にし直す前の REPAIR_DELEG_AT を拒否する比べ方が、台帳は「前なら拒否」（同じ秒は通す）、ホップは「後なら通す」（同じ秒は拒否）で | 真 | — | d0b3c12 |
| r5-control-c-2-F3 | Minor | 台帳は contact-tool・payment-tool・lock-tool でも「client_id が act の最も外側と同じエージェント（クライアント | 真 | — | d0b3c12 |
| r5-control-c-2-F4 | Minor | auth_time も acr も authoritative_writer に「③ agent-sts（CONSOLE_AT から写すだけ）」があり、H12  | 真 | — | d0b3c12 |
| r5-control-c-2-F5 | Minor | 3.1 は「中間の CA の鍵が漏れても、トークンの要る口は REPAIR_DELEG_AT かツールのトークンも要るので開かない」とする。しかし REPAIR | 真 | — | d0b3c12 |

## r6-control-c-1.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r6-control-c-1-R-1 | Minor | C-repair-id は「修繕依頼の台帳と突き合わせると入居者が分かる」ので個人情報としてハッシュで残すのに、C-approval-ref は「それだけでは人 | 真 | — | c52212c |
| r6-control-c-1-R-2 | Minor | 図の wl-ca からの「証明書」の線は repair-console・repair-agent・visit-subagent の 3 つだけで、mTLS で相 | 真 | — | c52212c |
| r6-control-c-1-R-3 | Minor | 承認の記録の状態は「承認済み →（予約済み →）使用済み・未確定 → 確定済み」と「取り下げは使用済みの前だけ」しか書いていない。取り下げ・却下した記録を、承認 | 真 | — | c52212c |

## r6-control-c-2.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r6-control-c-2-F1 | Major | 3.1 は「lock-tool は解錠の承認の依頼のときの作業員の番号の鍵つきのハッシュを承認の記録に残し、**発行のときに**今の番号のハッシュと一致しなけれ | 真 | — | c52212c |
| r6-control-c-2-F2 | Major | 解錠の承認は not_after まで有効で、承認から発行までに日をまたぎうる。発注の確定では order-tool が協力会社の取引の有効を確かめるが、解錠の | 真 | — | c52212c |
| r6-control-c-2-F3 | Minor | 手作業の発注の事後の確認（10 万円を超えるもの）に acr が mfa・auth_time から 300 秒を求めることは、C-approval-ref・付録 | 真 | — | c52212c |
| r6-control-c-2-F4 | Minor | ORDER_TOOL_AT・CONTACT_TOOL_AT と 9.1 は「寿命は 300 秒か REPAIR_DELEG_AT の残りの短いほう」と書くが、P | 真 | — | c52212c |

## r7-control-c-1.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r7-control-c-1-F1 | Major | aoba-pdp（重要な操作の剥奪の判断）と hr-sync（利用者の作成・無効化）は、どちらも **社員番号** を、利用者と人事の台帳を結ぶ照合の鍵に使って | 真 | — | c52212c |
| r7-control-c-1-F2 | Major | 承認者の条件（在籍・上長のロール・所属）を確かめるのは、承認の操作のときの approval-svc だけ。確定・予約（order-tool）や予約の実行（or | 真 | — | c52212c |
| r7-control-c-1-F3 | Minor | 承認できる「上長」を、2.1・9.2 は「職位が課長以上で同じ課の人」、APPROVAL_AT の交換と approval-svc の照合は「同じ課の課長」と書 | 真 | — | c52212c |
| r7-control-c-1-F4 | Minor | 解錠コードの送り直しの回数の上限（3 回）と「回を 1 つ上げる」について、回数を誰（approval-svc・lock-tool・通知の基盤）が持ち、上げ方が | 真 | — | c52212c |

## r7-control-c-2.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r7-control-c-2-F1 | Major | 3.1 は「翌日では遅いもの」を承認の記録と予約の記録だけとし、使う前に変更の記録の表で確かめる。ほかは翌日の突き合わせで見つけるだけにしている。ところが、次の | 真 | — | c52212c |
| r7-control-c-2-F2 | Major | REQ-06 は解錠の時間帯を 4 時間以内に限るが、台帳は description に「差は 4 時間以内」と書くだけで、確かめる受け手がいない。lock-t | 真 | — | c52212c |
| r7-control-c-2-F3 | Major | lock-svc の管理の画面（基盤チームの 2 人が自分のログインで入る）が 3.1 の取り消しの手順にだけ出てくる。2.2 の管理用の口・outside_e | 真 | — | c52212c |
| r7-control-c-2-F4 | Minor | agent-sts が APPROVAL_AT を出してよい相手（担当者でないとき）が、5 か所で 4 通りに書いてある（同じ課の課長／承認者になりうる上長／担 | 真 | — | c52212c |

## r8-control-c-1.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r8-control-c-1-F1 | Major | 設計は、中間の CA の鍵が漏れても「lock-svc が approval-svc で承認が lock-tool によって使用済みにされたことを確かめるので、 | 真 | — | d4062e6 |
| r8-control-c-1-F2 | Major | 手作業の発注の口では、課長 1 人が repair-console の画面から 10 万円を超える発注を登録でき、別の課長の承認は事後の確認だけである。この口を | 真 | — | d4062e6 |
| r8-control-c-1-F3 | Minor | 解錠コードを受け取る作業員（REQ-06 の「協力会社の作業員にだけ届ける」の相手）を、誰がどの値から決めるかが書いていない。承認の依頼の要求は部屋・協力会社・ | 真 | — | d4062e6 |
| r8-control-c-1-F4 | Minor | 解錠の承認は担当者本人がするので、承認した人は上長のロールを持たない。台帳の文のとおりに作ると、lock-tool の使用済みの更新が毎回失敗し、正しい解錠の  | 真 | — | d4062e6 |

## r8-control-c-2.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r8-control-c-2-F1 | Major | 見送りの行は「解錠のコードの作成は、lock-svc が approval-svc で、承認が lock-tool によって使用済みにされたことを確かめるので開 | 真 | — | d4062e6 |
| r8-control-c-2-F2 | Major | 委任の表・リソースの表・クライアントの登録と、各受け手の呼び出し元の許可リストは、どれも権限を与える値である（may_act・act の元、証明書だけで受ける口 | 真 | — | d4062e6 |

## r9-control-c-1.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r9-control-c-1-F1 | Major | 停止の宣言は、課長が手作業の発注を発注の台帳に書ける期間（宣言の間と解除から 24 時間）を開く門で、承認の前の確かめを通らない書き込みを許す。それなのに、宣言 | 真 | — | c8e1fe8 |
| r9-control-c-1-F2 | Minor | approval-svc の口の一覧（依頼・使用済み・予約済み・参照・使用済みの確かめ・APPROVAL_AT）に、当番が記録をそろえる口が無い。DB の直接の | 真 | — | c8e1fe8 |
| r9-control-c-1-F3 | Minor | 剥奪の見送りを支える代わりの守り（30 分ごとの一覧）が、図の経路にも、通知の基盤の呼び出し元にも無い。一覧には修繕依頼 ID・部屋の ID・not_after | 真 | — | c8e1fe8 |
| r9-control-c-1-F4 | Minor | 解錠のコードの送信では、通知の基盤が（承認 ID・送信の回）で重複を捨て、結果が分からなければ同じ回で送り直すと決めている。連絡では、通知の基盤への送信と「下書 | 真 | — | c8e1fe8 |
| r9-control-c-1-F5 | Minor | 解錠の時間帯を最後に当てるのはスマートロックの機器の時計なのに、6. の時計の一覧には approval-svc・order-scheduler・lock-to | 真 | — | c8e1fe8 |
| r9-control-c-1-F6 | Minor | approval-svc は「依頼の担当者」に取り下げを許すが、agent-sts は APPROVAL_AT を「今の担当か同じ課の上長」にしか出さない。担当 | 真 | — | c8e1fe8 |

## r9-control-c-2.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r9-control-c-2-F1 | Minor | 手作業の発注の口は、当番（基盤チーム）が repair-console の「当番の画面」で停止を宣言している間と解除から 24 時間だけ開く。つまり停止の宣言は | 真 | — | c8e1fe8 |

## r1-control-d-1.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r1-control-d-1-F1 | Major | 代理店の IdP で担当者を止めたときの最悪を「AGENCY_AT 330＋Txn-Token 330＝660 秒」としているが、止める直前に出た AGENCY | 真 | — | 2e30afa |
| r1-control-d-1-F2 | Major | 100 万円以上なら承認待ちにする合計の判定を、同じ請求の指示が並行して 2 件届いたときにも正しく行えるか（請求ごとに直列にする・ロックする）が書いていない。 | 真 | — | 2e30afa |
| r1-control-d-1-F3 | Minor | 性質の表は authorization_details が無いことだけで「当たらない」としたが、この設計には 1 件の支払い（payment_id と金額）ごと | 道具・教材への指摘 | 性質「操作ごとの承認」の読み方（review_triage.py）への指摘。設計書の誤りでない | 2e30afa |
| r1-control-d-1-F4 | Minor | 判断の木の keep-sub-exchange では、非同期の処理を利用者の権限で続けるとき「sub＝利用者、act＝仲介するワーカー」とする。設計は paym | 真 | — | 2e30afa |
| r1-control-d-1-F5 | Minor | 見送りの費用は「SVID が 1 時間ごとに替わるたびに直前の AT が使えなくなる」だけで、これは mTLS で束縛した場合の費用。BFF のサーバーが持つ  | 真 | — | 2e30afa |
| r1-control-d-1-F6 | Minor | TTS は作り直しのたびに claim-svc の請求の保留を引くが、その呼び出しが図にもホップにも無い。TTS がどの資格情報（Txn-Token か mTL | 真 | — | 2e30afa |
| r1-control-d-1-F7 | Minor | PAY_MSG_CTX は、TTS が TXN_STAFF（寿命 300 秒）を subject_token にして出す交換（I22）。ところがホップの表では、 | 真 | — | 2e30afa |
| r1-control-d-1-F8 | Minor | REQ-03 の 600 秒を「社員の台帳が変わってから」数えている。退職・休職・異動の発令から、人事部が入力して責任者が承認するまでの区間には、誰も時間を約束 | 真 | — | 2e30afa |
| r1-control-d-1-F9 | Minor | 判断の木の txn-tctx では、Txn-Token を受けるホップの受け手のすべてが tctx の値を本文と照らしているかを確かめる。H18（assessm | 真 | — | 2e30afa |

## r1-control-d-2.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r1-control-d-2-F1 | Major | REQ-10 は「鍵が漏れたら 900 秒以内にその鍵の署名を受け入れない」。設計の 330 秒（JWKS のキャッシュ 300＋間隔 30）は、**鍵を JW | 真 | — | 2e30afa |
| r1-control-d-2-F2 | Major | 承認の要否を「同じ請求の支払いの合計（実行済み・承認待ち・この指示）」で決めるが、合計の読み取りと指示の記録を 1 つの取引で、請求ごとに直列化して行う決まりが | 真 | — | 2e30afa |
| r1-control-d-2-F3 | Minor | 書類の登録で document-svc が claim-svc の記録（請求の持ち主・agency_code）を引くとホップと台帳には書いてあるが、3.1 は  | 真 | — | 2e30afa |
| r1-control-d-2-F4 | Minor | 図と記入欄に無い呼び出しがある：(a) TTS が請求の保留を引く先と、そのときの認証（claim-svc は Txn-Token と呼び出し元の一覧で受けるが | 真 | — | 2e30afa |
| r1-control-d-2-F5 | Minor | C-sub は reassignable: false と宣言するが、上流の代理店の IdP の sub は代理店が付け替えられ、しろがねでは見分けられないと  | 真 | — | 2e30afa |
| r1-control-d-2-F6 | Minor | 性質の判定は authorization_details が無いことだけで「当たらない」になったが、REQ-05 の承認は支払いの 1 件（payment_id | 道具・教材への指摘 | 性質「操作ごとの承認」の読み方（review_triage.py）への指摘。設計書の誤りでない | 2e30afa |
| r1-control-d-2-F7 | Minor | REQ-03 の 600 秒は、社員の台帳が変わってからの 390 秒で満たすとしているが、退職・休職・異動の発効から、人事部の入力と責任者の承認で台帳が変わる | 真 | — | 2e30afa |
| r1-control-d-2-F8 | Minor | 端末・セキュリティキーの紛失の届けから止まるまでの要求の数値が無い（設計は REQ-03 の 600 秒を目標に置き、330 秒とした）。届けまでの時間も数えて | 真 | — | 2e30afa |
| r1-control-d-2-F9 | Minor | (1) shirogane-as は (iss, jti) を 330 秒覚えるが、同じ組の 2 件が同時に届いたときに 1 件だけ通す（確かめと記録を 1 回 | 真 | — | 2e30afa |
| r1-control-d-2-F10 | Minor | PAY_MSG_CTX を出す条件は「subject_token の operation が assessment.confirm」だけで、頼める相手（mTLS | 真 | — | 2e30afa |

## r2-control-d-1.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r2-control-d-1-F1 | Major | REQ-03 は「退職・休職・役割の変更」を 600 秒で効かせると求めるが、TTS の確かめは「在籍」と役割だけで、休職を止める条件として書いていない（休職は | 真 | — | a9fd530 |
| r2-control-d-1-F2 | Major | 承認の記録は payment_id と金額に結びつくが、宛先（振込先 payee_ref）に結びつかない。振込先は契約部が契約管理の仕組みで書け、実行の時点で承 | 真 | — | a9fd530 |
| r2-control-d-1-F3 | Major | 支払いの指示の重複の防ぎが txn に結びついているが、確定し直し（手作業）や同じ請求の 2 回目の確定では新しい txn になる。前の指示を payment- | 真 | — | a9fd530 |
| r2-control-d-1-F4 | Major | REQ-04 は「実行の前なら必ず効く」を求めるが、保留は claim-svc、実行の記録は payment-svc の別の DB で、問い合わせと実行済みの書 | 真 | — | a9fd530 |
| r2-control-d-1-F5 | Major | REQ-11 は「通話の間」だけ代理受付を許すが、TTS は本人確認からの経過だけを見て通話が続いているかを見ない。通話が切れた後も最大 1800 秒、契約者の | 真 | — | a9fd530 |
| r2-control-d-1-F6 | Major | 9.1 では IT 基盤部が shirogane-sso の鍵の登録を消し、staff-console の管理の機能でセッションを消すが、この 2 つの管理の口 | 真 | — | a9fd530 |
| r2-control-d-1-F7 | Minor | DB を直接直す作業（基盤の変更の手続き）で、承認の記録・代理店の登録・請求の割り当て・保留を書き換えられるが、台帳の書き手と 9.2 の経路に数えていない。業 | 真 | — | a9fd530 |
| r2-control-d-1-F8 | Minor | 台帳と設計書は rctx を載せないと決めているのに、H3 の確かめは TTS が rctx の req_ip を書くとしている。どちらかに揃える | 真 | — | a9fd530 |
| r2-control-d-1-F9 | Minor | front-gw の契約者の口は claim-portal の SVID からしか接続を受けないので、front-gw が接続から記録する IP は契約者のブラ | 真 | — | a9fd530 |
| r2-control-d-1-F10 | Minor | agst_ は上流の代理店の IdP が sub を付け替えると別の人を指しうると自ら書いているのに、reassignable を false と宣言している。 | 誤検出 | 3.1 の見送りと C-sub の note に理由がある（しろがねの割り当ての性質）。言い切りだが理由は要求と矛盾しない（R4） | a9fd530 |
| r2-control-d-1-F11 | Minor | AGENCY_ASSERTION（60 秒）から AGENCY_AT（300 秒）への寿命の延びと、宛先・独自クレームの変わり方が、ホップの表に行が無いため L | 真 | — | a9fd530 |
| r2-control-d-1-F12 | Minor | 代理店向けの CA の CRL を取り直せないときに代理店の口を通すのか止めるのか、毎日 1 時〜3 時の実行の時間帯に TTS が止まったときに支払いをどう扱 | 真 | — | a9fd530 |
| r2-control-d-1-F13 | Minor | 端末・セキュリティキーの紛失の届けから止まるまでの要求の数値が無く、330 秒が足りるかを判定できない（書き手も 12. で挙げている）。要求の持ち主の回答を待 | 確認の依頼 | 3.1 の見送り（紛失の届けの数値が要求に無い）を確かめるよう求めるもの（R4） | a9fd530 |
| r2-control-d-1-F14 | Minor | 上長が役割だけで請求を読めるのか、割り当て（と assessment.assign）に限るのかが 2 か所で違う。役割だけなら上長はすべての請求に届く。どちらか | 真 | — | a9fd530 |
| r2-control-d-1-F15 | Minor | 100 万円以上の支払いの承認は、payment_id と金額に結びつく 1 件ごとの承認で、性質としては当たる。トークンに載せないので authorizati | 道具・教材への指摘 | 性質「操作ごとの承認」の読み方（review_triage.py）への指摘。設計書の誤りでない | a9fd530 |
| r2-control-d-1-F16 | Minor | 代理店のクライアント（client_id と tls_client_auth の証明書のサブジェクト）を書くのが IT 基盤部のクライアントの登録か、代理店管理 | 真 | — | a9fd530 |

## r2-control-d-2.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r2-control-d-2-F1 | Major | H22 は承認の要否を「同じ請求の支払いの合計（実行済み・承認待ち・この指示）」で決めるが、承認の要らない「指示済みで未実行」の支払いが合計に入っていない。夜間 | 真 | — | a9fd530 |
| r2-control-d-2-F2 | Major | 重複の判定の鍵が txn（1 つの呼び出しの連鎖の ID）で、答えているのは「同じメッセージが再び届いたか」。要るのは「この請求の査定の確定に対して指示が既にあ | 真 | — | a9fd530 |
| r2-control-d-2-F3 | Major | REQ-11 は「本人確認した通話の間（本人確認から 30 分）だけ」だが、TTS は本人確認から 1800 秒以内かと担当の社員しか見ず、通話が終わったかを見 | 真 | — | a9fd530 |
| r2-control-d-2-F4 | Major | 判定待ちの請求を後で fraud-svc に判定させる経路が、図・ホップ・カタログのどこにも無い。元の Txn-Token は 300 秒で切れ、fraud-s | 真 | — | a9fd530 |
| r2-control-d-2-F5 | Minor | ホップは TTS が rctx の req_ip を書くとするが、台帳と設計書は rctx を却下している。実装する人が、却下した rctx（読まない受け手にも | 真 | — | a9fd530 |
| r2-control-d-2-F6 | Minor | 請求の受付の経路の積に、claim-portal 自身と shirogane-as のトークンの端点（PH_AT は 10 分ごとに PH_RT で、AGENC | 真 | — | a9fd530 |
| r2-control-d-2-F7 | Minor | client_id を使わない理由を「証明書を替えて登録し直すと client_id が変わる」とするが、設計は証明書を同じサブジェクトで出し直し、登録は証明書 | 真 | — | a9fd530 |
| r2-control-d-2-F8 | Minor | 設計には 1 件の支払い（payment_id と金額）ごとの上長の承認がある。authorization_details を使わず承認の記録で行うため、性質の | 道具・教材への指摘 | 性質「操作ごとの承認」の読み方（review_triage.py）への指摘。設計書の誤りでない | a9fd530 |

## r3-control-d-1.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r3-control-d-1-F1 | Major | 支払いの指示の「1 回だけ」の規則が箇所ごとに違う。TTS が PAY_MSG_CTX を出せるのは assessment_ref ごとに 1 回（H29）なの | 真 | — | 64ba505 |
| r3-control-d-1-F2 | Minor | 1 枚の Txn-Token の operation は 1 つで、claim.submit の tctx には claim_id が無い。図のとおり書類つきの | 真 | — | 64ba505 |
| r3-control-d-1-F3 | Major | 上長の閲覧を「自分の課の査定担当者に割り当てた請求だけ」に絞る確かめには、社員の台帳の上長の課が要る。しかし assessment-svc が台帳を読む経路が図 | 真 | — | 64ba505 |
| r3-control-d-1-F4 | Major | TTS が役割から出す scope の対応の表が、設計書のどこにも無い（「経路の表が配られる」という前提だけがある）。そのため次の 2 点が決まらない。(a)  | 真 | — | 64ba505 |
| r3-control-d-1-F5 | Minor | 保留を外す操作に operation の名前が無い。scope（assessments:write）は査定担当者と上長で同じなので、payment-svc はト | 真 | — | 64ba505 |
| r3-control-d-1-F6 | Minor | 1 件の支払い（payment_id・金額・payee_ref）ごとの承認が実際にある。トークンに載せないので、台帳の読み方で「当たらない」になっただけ。この性 | 道具・教材への指摘 | 性質「操作ごとの承認」の読み方（review_triage.py）への指摘。設計書の誤りでない | 64ba505 |
| r3-control-d-1-F7 | Minor | 生成の表が、目録で宣言した転送のヘッダーを None と出している。目録の書き方（value の欄が無い）か render のどちらかが食い違う。同じ節の E- | 道具・教材への指摘 | claim_lint render が forwarded_cert_header を None と出す不具合（fedd053 で直した） | 64ba505 |
| r3-control-d-1-F8 | Minor | as-admin-api は admin:staff-auth の操作（登録の番号の発行・鍵の抹消・セッションの削除）にも phr と 300 秒を求める。しか | 真 | — | 64ba505 |
| r3-control-d-1-F9 | Minor | 代理店の登録の新規作成と、既存の代理店への client_id（新しいサーバー）の追加が、2 人の操作に入るかが書いていない。1 人の代理店管理部の社員が、代理 | 真 | — | 64ba505 |
| r3-control-d-1-F10 | Minor | 「1 回だけ」をどこで確かめるか（shirogane-sso の一意の書き込みか）と、並行の 2 件・再送・記録先の障害での扱いが書いていない。番号を手に入れた | 真 | — | 64ba505 |
| r3-control-d-1-F11 | Minor | 3.1 は、終話の後の最大 90 秒を要求の持ち主が受け入れるかを 12. で確かめるとしている。しかし 12. にその行が無く、確かめの宿題が消えている | 真 | — | 64ba505 |

## r3-control-d-2.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r3-control-d-2-F1 | Major | 代理店の assertion の寿命の上限の確かめが食い違う。H31 と目録は「exp − iat が 60 秒以下」だが、`C-exp` の shirogan | 真 | — | 64ba505 |
| r3-control-d-2-F2 | Major | shirogane-as は assertion の iss が「代理店の登録にある iss のどれか」と一致するかを確かめるだけで、mTLS で認証したクライ | 真 | — | 64ba505 |
| r3-control-d-2-F3 | Major | 承認する上長が、その支払いを指示した査定担当者の上長（同じ課）かを payment-svc が確かめない。確かめるのは「指示の sub と違う」と「承認の上限額 | 真 | — | 64ba505 |
| r3-control-d-2-F4 | Minor | 支払いの指示の重複を 1 件にする一意の制約のキーが食い違う。H21 は「(txn, claim_id)」、H22 と `C-txn` は「(claim_id, | 真 | — | 64ba505 |
| r3-control-d-2-F5 | Minor | PAY_MSG_CTX の期限が切れて滞留した指示を、付録 A と 3.1 は「同じ assessment_ref で送り直す」とするが、TTS は同じ ass | 真 | — | 64ba505 |
| r3-control-d-2-F6 | Minor | 6. は TTS も PH_AT・EMPLOYEE_AT の client_id を確かめると書くが、台帳の TTS の確かめは「代理店の登録で client_ | 真 | — | 64ba505 |
| r3-control-d-2-F7 | Minor | REQ-11 は「通話が終わったら止める」と読んだのに、終話の直前に出た TXN_PROXY は終話から最大 90 秒使える。3.1 はこの 90 秒の受け入れ | 真 | — | 64ba505 |
| r3-control-d-2-F8 | Minor | 性質の判定が authorization_details の有無だけで決まり、承認の記録（REQ-05）と 2 人の操作という操作ごとの承認があるのに「当たらな | 道具・教材への指摘 | 性質「操作ごとの承認」の読み方（review_triage.py）への指摘。設計書の誤りでない | 64ba505 |
| r3-control-d-2-F9 | Minor | セキュリティキーの登録の番号は「24 時間・1 回だけ」とあるが、使用済みにするのは誰か（shirogane-sso か as-admin-api か）、確かめ | 真 | — | 64ba505 |

## r4-control-d-1.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r4-control-d-1-F1 | Major | REQ-05 は「査定した人と別の上長が承認する」を求めるが、payment-svc は承認者を「指示の sub」と比べ、同じ課かも指示の sub の課で決める | 真 | — | d0b3c12 |
| r4-control-d-1-F2 | Major | 確定し直しでは assessment_ref の版が替わるので、(claim_id, assessment_ref) の一意の制約は前の版の指示と別の行として受 | 真 | — | d0b3c12 |
| r4-control-d-1-F3 | Major | 承認は payee_ref（参照 ID）に結びつき、実行の取引では「承認の payee_ref＝支払いの記録の payee_ref」と「payee_ref が今 | 真 | — | d0b3c12 |
| r4-control-d-1-F4 | Minor | 役割（＝TTS が出す scope）を書ける者の範囲が 2 か所で食い違う。台帳は IT 基盤部の DB の管理者も役割を付けられるとし、設計書は付けられないと | 真 | — | d0b3c12 |
| r4-control-d-1-F5 | Minor | 3.1 の見送り（document-svc は請求の持ち主・代理店・割り当てを自分では確かめない）、H10・H11・H19 の validates、M_auth | 真 | — | d0b3c12 |
| r4-control-d-1-F6 | Minor | hops.yaml の H29、claims.yaml の `C-tctx` の tts の行、4. の TTS が受ける要求の表、catalog_answer | 真 | — | d0b3c12 |
| r4-control-d-1-F7 | Minor | 設計には操作ごとの承認がある（100 万円以上の支払いの上長の承認（REQ-05）と、代理店の登録・セキュリティキーの登録の番号の 2 人の操作）。承認をトーク | 道具・教材への指摘 | 性質「操作ごとの承認」の読み方（review_triage.py）への指摘。設計書の誤りでない | d0b3c12 |

## r4-control-d-2.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r4-control-d-2-F1 | Major | payment-svc が payee_ref を照らす「その証券」を、どこから決めるかが無い。payment.instruct の tctx には（P5 の  | 真 | — | d0b3c12 |
| r4-control-d-2-F2 | Minor | PAY_MSG_CTX と作り直した TXN_TOKEN の tctx に policy_number が入るかで、2 か所が食い違う。H30・C-tctx・4 | 真 | — | d0b3c12 |
| r4-control-d-2-F3 | Major | 確定し直しで assessment_ref の版が変わると、(claim_id, assessment_ref) の一意の制約は 2 つの指示を別物として両方記 | 真 | — | d0b3c12 |
| r4-control-d-2-F4 | Minor | 監査ログで sub・act を HMAC にしても、tctx の policy_number（証券番号）と payee_ref を平文で残すので、契約管理の仕組 | 真 | — | d0b3c12 |

## r5-control-d-1.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r5-control-d-1-F1 | Major | 「承認・取り消しをしてよい上長」の課の基準が 2 か所で違う。payment-svc は査定者の**今の**課（社員の台帳を要求のたびに引く）で、assessm | 真 | — | d0b3c12 |
| r5-control-d-1-F2 | Major | 査定担当者が別の課に異動したとき（役割は残る）、claim-svc の請求の割り当てを外す人・経路・時間がどこにも無い。移った社員は、前の課の請求の査定の確定と | 真 | — | d0b3c12 |
| r5-control-d-1-F3 | Minor | 性質の表は authorization_details と「approval」の名前だけで読み、当たらないとした。設計には 1 件の支払い（payment_id | 道具・教材への指摘 | 性質「操作ごとの承認」の読み方（review_triage.py）への指摘。設計書の誤りでない | d0b3c12 |
| r5-control-d-1-F4 | Minor | 下流の PAY_MSG_CTX（3600 秒）が上流の TXN_STAFF（300 秒）の 12 倍生きる理由は「TTS が作り直しのときに社員の在籍・役割と請 | 真 | — | d0b3c12 |

## r5-control-d-2.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r5-control-d-2-F1 | Major | 上長に保留と保留の解除（assessment.unhold）を出すと決めているが、どの請求に許すかを確かめる文が無い。assessment-svc の確かめは「 | 真 | — | d0b3c12 |
| r5-control-d-2-F2 | Major | 支払いの指示の重複は (claim_id, assessment_ref) の一意の制約で止め、新しい版は「同じ請求に未実行の指示がある間」だけ拒む。古い版（v | 真 | — | d0b3c12 |
| r5-control-d-2-F3 | Major | 保留の印の単位（請求ごとか支払いの行ごとか）と、未実行の支払いの行がまだ無いとき（指示がブローカーにある間）の書き方が決まっていない。H25 は「未実行の支払い | 真 | — | d0b3c12 |
| r5-control-d-2-F4 | Minor | 保留（査定担当者・上長）と保留の解除（上長だけ）は、同じ scope（assessments:write）で、違いは tctx の operation だけ。台 | 真 | — | d0b3c12 |
| r5-control-d-2-F5 | Minor | 「2 回目の使用でその認可コードから出したトークンも失効させる」とあるが、PH_AT・EMPLOYEE_AT は JWT で、front-gw と TTS は手 | 真 | — | d0b3c12 |
| r5-control-d-2-F6 | Major | 課をまたぐ異動で役割（査定担当者）が残るとき、claim-svc の割り当ての記録を外す者・経路・時間がどこにも無い。assessment-svc の確かめは割 | 真 | — | d0b3c12 |
| r5-control-d-2-F7 | Minor | 性質の表は authorization_details が無いので「当たらない」としたが、支払いの 1 件ごとの上長の承認（REQ-05。payment_id・ | 道具・教材への指摘 | 性質「操作ごとの承認」の読み方（review_triage.py）への指摘。設計書の誤りでない | d0b3c12 |

## r6-control-d-1.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r6-control-d-1-F1 | Minor | 性質の表は authorization_details が無いので「当たらない」としたが、REQ-05 の上長の承認は支払いの 1 件ごと（payment_id | 道具・教材への指摘 | 性質「操作ごとの承認」の読み方（review_triage.py）への指摘。設計書の誤りでない | 8120ae7 |
| r6-control-d-1-F2 | Minor | 「代理店の登録・契約者のアカウントの状態は as-admin-api だけが書く」と宣言しているが、shirogane-as の書き込みの口がどうやって as- | 真 | — | 8120ae7 |
| r6-control-d-1-F3 | Minor | 保留の解除（assessment.unhold）は、保留で止めていた支払い（承認済みのものを含む）を夜間の実行に戻す操作だが、追加の認証を求めず、求めない理由も | 真 | — | 8120ae7 |
| r6-control-d-1-F4 | Minor | 保留の状態が claim-svc（保留の記録）と payment-svc（集計の行の保留の印）の 2 か所にあり、「payment-svc が書けたときだけ c | 真 | — | 8120ae7 |

## r6-control-d-2.md

| 指摘 | 重大度 | 内容（先頭） | 判定 | 理由 | 直したコミット |
| --- | --- | --- | --- | --- | --- |
| r6-control-d-2-F-1 | Minor | 性質の表は「authorization_details が無い」ことから「当たらない」としたが、設計には操作ごとの承認がある。100 万円以上の支払いの承認は、 | 道具・教材への指摘 | 性質「操作ごとの承認」の読み方（review_triage.py）への指摘。設計書の誤りでない | 8120ae7 |
| r6-control-d-2-F-2 | Minor | 認可コードを 1 回だけ使わせる仕組みが「1 回だけ使える」としか書いていない。確かめと使用済みにする書き込みが 1 つの操作か、記録先が応えないときに拒むかが | 真 | — | 8120ae7 |
| r6-control-d-2-F-3 | Minor | 330 秒は、IT 基盤部の担当者が届けを受けた瞬間に as-admin-api で消す前提の数字で、担当者が受けて操作するまでの時間（ハードウェアの鍵での認証 | 真 | — | 8120ae7 |
| r6-control-d-2-F-4 | Minor | 滞留のキューに移ったメッセージ（txn・請求の ID・PAY_MSG_CTX。PAY_MSG_CTX には、個人情報とした sub と tctx の金額・pay | 真 | — | 8120ae7 |
| r6-control-d-2-F-5 | Minor | 他の代理店の証券・請求への要求に返す応答の番号が、2 か所で違う。403 を返すと、その証券・請求があることを知らせてしまう。M_authz_pdp の 3.  | 真 | — | 8120ae7 |

