# レビューレポート：シナリオ C（パイロット #9）レビュアー R1

> 設計書のエディターのレビューモード（#50）が `review.yaml` から生成した。レビュアーの名前は自己申告で、本当の承認は GitHub の PR のレビューで行う。レビュアーは LLM で、人による点検は未実施。

## 1. 基本情報

| 項目 | 値 |
| --- | --- |
| 対象 | research/pilot/scenario-c（版 f8c26c7daeb51b61b590db9f86b1879192e02773）。worktree agent-a9f5b6ad37dc24c26 の research/pilot/scenario-c（未コミットの状態を含む可能性あり） |
| Lite／Full | 設計書は Lite の欄で記入。5 問では delegation\_or\_exchange・new\_issuer が Yes で Full（書き手の判定も Full）。パイロットの指示で Lite のままレビュー（F01） |
| 実施した手順の段 | 0〜7（段 0 で返す条件に当たったがパイロットの指示で続行。段 8 は対応待ち） |
| レビュアーと役割 | R1（LLM：claude-opus-5-5。名前は自己申告）。攻撃者 → 受け手 → 発行者 → 運用 → 個人情報 → クライアント（1 つのセッションの中で切り替えた。別セッションでの読み直しは未実施）。独立レビュー：提出まで、ほかのレビュアーの記録を画面で隠した（画面で隠すだけで、review.yaml を開けば見える。守ったかは自己申告） |
| 実施日 | 2026-11-24 |
| 使った教材の版 | templates/review（レビューした時の版：perspectives.md 0.4.0、report\_template.md 0.4.0、問い 168 問）。templates/review 一式（procedure・perspectives 168 問・decision\_tree・contrasts・escalation・rationale\_rubric・report\_template）、tools/claim\_lint、tools/review\_record.py、要求の概要 brief-C.md |
| CI の結果 | claim\_lint error 53・warn 1・info 9（profile full）。設計書の 1. と一致。設計書の 1. に貼った結果（profile full）と一致。profile lite では error 0・warn 3（L15 1・L73 2）・info 9 |
| 抜き取りの結果 | 乱数の種「r1-pilot-c」（claims.yaml の却下の行 10 行から 3 行。sha256(種:行) の順）：C-may-act・C-org-task-id・C-roles。3 件を採点、合格 2・不合格 1 |
| 問いの回答 | 全 168 問のうち 168 問に回答（未回答 0）。定義 Yes 11／No 3／該当なし 45。発行 Yes 8／No 3／該当なし 1。伝搬 Yes 17／No 2／該当なし 9。検証 Yes 9／No 4／該当なし 1。認可 Yes 9／No 0／該当なし 19。運用 Yes 12／No 13／該当なし 2。合計 Yes 66／No 25／該当なし 77 |

## 2. 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 出どころ | 種別 | 取り違えた問い（種別が目的と仕組みの不一致のとき） | 判定 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F01 | template:00\_core#ci-results、冒頭の Lite／Full、catalog\_answers.lite\_criteria | 段 0 の受け付けの条件に 2 つ当たる。(1) 5 問のうち delegation\_or\_exchange と new\_issuer が Yes で、設計書自身も「判定は Full」と書くのに Lite の欄で書いている（L73 の warn 2 件）。(2) 1. に貼った CI の結果は profile full で error 53（FAIL。issuers・issue\_events・propagation\_delay・status・overflow\_strategy の列が空）。手順どおりなら返す。パイロットの指示（Lite で記入）を受けて、レビューは続けた（判定の理由：procedure.md の段 0 の 1.・2. にそのまま当たる。Lite の profile では error 0・warn 3 を確かめた） | Major | テンプレート項目 | 実装とのずれ | — | 採用 |
| F02 | catalog\_answers.yaml の U10、token\_types\[AGENT\_AT\].holder・sender\_constraint、C-cnf.enforced\_at | U10 の回答は「STS は subject\_token の cnf が actor の証明書と同じことを確かめる」と書く。しかし AGENT\_AT はエージェントの証明書に束縛され（holder・cnf）、交換を要求する actor はツールサーバーで証明書が違う。書いたとおりに実装すると、正規の C1・C8・C11 の交換がすべて拒否される。正しくは「subject\_token の aud が actor（ツールサーバー）の正規の URI と一致し、actor は mTLS で認証する」ではないか。C-cnf・C-aud の consumers・enforced\_at に sts-token-exchange が無く、どちらの台帳の行も STS のこの確認を表していない（判定の理由：2 か所（U10 と AGENT\_AT の cnf）が同じトークンについて両立しない） | Major | 観点 | 実装とのずれ | — | 採用 |
| F03 | claims:C-aud・C-jti・C-act の enforced\_at（sts-token-exchange）、hops\[H2\].exchanger、issuance\_profile.grants | 交換の STS が subject\_token について確かめることが台帳の enforced\_at に揃っていない。(a) subject\_token の aud が actor 自身の resource であること（U10 にだけある。F02）、(b) subject\_token から委任の記録を引いて取り消し済みでないこと（C9 の要。jti の行は「監査ログに記録」だけ）、(c) actor ごとに得てよい宛先（tool:invoice-mcp だけが invoices 向けを得る）。(c) が無いと、悪意ある MCP サーバー B が自分宛ての AGENT\_AT を交換して請求書の API 向けを得ようとしたとき、STS で止める規則が無く、止まるのは請求書の API の行為者の方針の表だけになる。エージェントのクライアントが resource=請求書の API で AT を直接得られるか（ツールを迂回する経路）も書いていない（判定の理由：攻撃者の視点で H1→STS→H2 の矢印をたどって見つけた。観点書の問いは交換の結果（aud・scope）を見るが、交換の入力（subject\_token）の確認を直接は問わない） | Major | テンプレート外 | 候補の漏れ | — | 採用 |
| F05 | token\_types\[AGENT\_RT\]、issuance\_profile.rt\_strategy、9.1 | エージェントに最大 8 時間・無操作 1 時間の RT を出す。観点書の q-agent-short-lived-no-rt（タスク単位の短命で RT を出さない）から外れるのに、RT を出さない案（AT の取り直しのたびに同意か、短い委任の付与）との比較と、エージェントの証明書と RT が同時に漏れたときの最悪の期間（8 時間）の評価が理由に無い。再利用の検知は unverified で、L15 の warn（RT に載る cnf の行が無い）も残る（判定の理由：RR3（代わりと代償）が満たされない。RT 自体を否定するのでなく比較を求める） | Major | 観点 | 理由の不備 | — | 採用 |
| F06 | 3.1 の「タスク単位の短命トークン」、token\_types\[SECURITY\_EVENT\_TOKEN\]・\[TOOL\_AT\].revocation・refresh、C-scope.volatility、U14、C-authorization-details.log\_policy | 同じ事実の値が欄ごとに違う。(1) 取り消しの反映の目標が 3.1 で 120 秒、SET の却下・I23 で 90 秒、C-scope の volatility は 900 秒。(2) TOOL\_AT の refresh は「呼び出しのたびに交換」なのに revocation の note は「手元の TOOL\_AT が切れるまで最悪 60 秒」で、使い回しを前提にする。(3) U14 は監査ログに approval\_id を残すと書くが、approval\_id を含む C-authorization-details の log\_policy は「記録しない」（判定の理由：RR7 の食い違い。どれが正かを書き手が決める） | Minor | 観点 | 実装とのずれ | — | 採用 |
| F07 | catalog\_answers.yaml の I14 と pairwise の I14、C-authorization-details.enforced\_at | 承認つきの AGENT\_AT の発行（I14）で STS が確かめること（承認済み・持ち主が sub）は pairwise の note にしか無く、STS の enforced\_at に無い。承認がタスクの同意の後に出たとき、エージェントが何の要求（RT の取り直しに authorization\_details を付ける。RFC 9396 §6 は許す）で載せ直すか、承認を特定のタスク・エージェントに結ぶか（u1 の別のタスクのエージェントが同じ承認を使えるか）が書いていない。請求書の API が支払いのたびに記録を引くので、直ちに不正な支払いにはならない（判定の理由：承認の一生（作成→載せる→使う→消費）を追う外の質問で見つけた） | Minor | テンプレート外 | 候補の漏れ | — | 採用 |
| F08 | C-authorization-details.enforced\_at（invoices-api）、目録の db\_lookup | 「承認済み・未使用を確かめて消費する」の、同時の 2 つの支払いの要求（競合）への扱い（条件つきの更新で 1 回だけ成功させる）と、消費と支払いの順序（消費した後に支払いが失敗したら承認を戻すか、タイムアウトの後の再試行を冪等に扱うか）が無い。同じ承認での二重払い（作者が outside\_enumeration で見つけた場面）の防ぎ方が、実装しだいで崩れる（判定の理由：障害時の再送と並行の要求を問う外の質問で見つけた。カタログに戻す候補） | Major | カタログ外の質問 | 候補の漏れ | — | 採用 |
| F09 | C-client-id.enforced\_at（invoices-api）、PORTAL\_AT、§7 の 8（Keycloak） | 請求書の API の「act の無い AT は client\_id と mTLS の相手が一致すれば受け入れる」は、act の無い AT を出してよいクライアントを限っていない。エージェントのクライアントが act の無い利用者の AT を得る経路が 1 つでもできると（STS の設定の誤り、Keycloak の標準の交換で act が付かない構成に置き換えたとき）、エージェントは自分の証明書のまま「利用者本人」として通り、C12 の防ぎ方と行為者の方針の照合を迂回する。act の無い AT は client\_id が portal のときだけ受け入れる許可リストにすべき（判定の理由：C12 の防ぎ方を cnf 以外の層で外したらどうなるかを問う外の質問で見つけた） | Major | テンプレート外 | 候補の漏れ | — | 採用 |
| F10 | C-authorization-details.carried\_in・consumers・pii\_category、hops\[H1\].authorization\_details | 振込先の口座（user.financial.bank\_account）を含む authorization\_details が H1 の AGENT\_AT に載り、読まない受け手（エージェント・ツールサーバー）に平文で届く。請求書の API は支払いのたびに承認の記録を DB で引くので、トークンに載せるのは approval\_id（と金額・相手先のハッシュ）で足りるか、STS が交換のときにだけ TOOL\_AT に載せる案と比べていない。12. で書き手も迷った点（判定の理由：観点書が「個人情報が読まない受け手に届くなら Major」とする） | Major | 観点 | 候補の漏れ | — | 採用 |
| F11 | hops\[H2\].scope、C-scope.enforced\_at（sts-token-exchange） | TOOL\_AT は読むだけの呼び出しでも invoices:read invoices:pay を持つ。交換は呼び出しごとなので、呼ばれたツールの操作だけに絞れる。C14 のような引き上げの要求を STS が拒否したことを、相関 ID（jti）つきで記録する規則も無い（判定の理由：最小の範囲と昇格の記録の問い） | Minor | 観点 | 候補の漏れ | — | 採用 |
| F12 | 12. の「深さの数え方」、6. の UC1（C1・C11 を同じ行に）、C-act | 深さを「act の数（エージェントとツールで 2）」と読んだため、C1 と C11 が同じユースケースになっている。要求が C1 と C11 を別のケースに挙げていることから、C11 の「2 段」は C1 より長い連鎖を指す可能性がある。その場合は正規の C11 を拒否する。数え方の定義（利用者→エージェントの委任を数えるか）を台帳の description に書き、要求の出し手に確かめる（判定の理由：書き手が 12. に挙げた点。要求の出し手の確認と、escalation の delegation-depth で決める） | Minor | テンプレート項目 | 理由の不備 | — | 保留 |
| F13 | 2.2・5.1・7.・付録 A、P4 の 2.〜9.、M\_token\_validation・M\_privacy\_minimization の欄 | Lite で書いたため、Full で要る欄が無く、観点書の次の問いが判定できない（No と扱った）：q-shared-validator、q-validate-before-read、q-no-unverified-passthrough-mode、q-token-logging、q-lifetime-rationale、q-operational-metrics。2.2（console:admin の扱い）と 7.（同意・交換・支払い・取り消しのシーケンス）が無いので、C4・C9 の流れを図で追えない（判定の理由：procedure.md の段 3（モジュールの欄が無く台帳で答えられなければ No。Full で使うと決めたモジュールの欄が無いことも指摘）） | Major | テンプレート項目 | 候補の漏れ | — | 採用 |
| F14 | template:00\_core#hop-table の矢印の表、hops\[H3\].validates、hops\[\*\].to と claims\[\*\].enforced\_at.service | 矢印の表（render）が 3 ホップとも「—」で、受け手の確かめるクレームが 1 つも引けていない。hops の to が URI（https://invoices.example.com）で、enforced\_at の service が名前（invoices-api・tool:invoice-mcp）のため結びつかない。機械の照合が働かず、H3 の validates に scope が無いこと（C-scope.enforced\_at は請求書の API が scope を見ると書く）も表に出ない（判定の理由：生成の表と台帳が食い違う。名前をそろえるか、render の側の対応づけを #6 に渡す） | Minor | テンプレート項目 | 実装とのずれ | — | 採用 |
| F15 | token\_types\[AGENT\_AT\].revocation、9.1、catalog\_answers U21 | 取り消しの後もツールサーバーは AGENT\_AT を最悪 330 秒受け入れる。上流は交換の拒否で止まるが、ツールサーバーが上流の結果（請求書の内容）をキャッシュして返すと、要求の「取り消した後はエージェントが続けて使えてはいけない」を満たさない。U21 は認可の判断と承認の照会のキャッシュだけを否定し、ツール側の結果のキャッシュについて書いていない（判定の理由：写しの寿命の問い） | Minor | 観点 | 候補の漏れ | — | 採用 |
| F16 | C-authorization-details.on\_revoke、TOOL\_AT.revocation、3.1 | 承認のサービス（DB）と STS が落ちたとき、請求書の API が支払いを拒否する（閉じる）か、交換の失敗でツールが何を返すかが書いていない。3.1 は可用性を見直しの条件に挙げるだけ（判定の理由：依存先の障害の問い） | Minor | 観点 | 候補の漏れ | — | 採用 |
| F17 | C-authorization-details（type・shape・value\_vocabulary）、schemas/TOOL\_AT.consumer.schema.json | 照合の要である authorization\_details の中の項目（approval\_id・invoice\_id・instructedAmount.amount と currency・creditorAccount）の型と比較の方法が無い（consumer schema は items: object だけ）。金額を数値にするか文字列にするか（RFC 9396 の例は "123.50" の文字列）、振込先の表記の正規化が決まらないと、C5・C6 の「完全一致」が受け手ごとに違う（判定の理由：RFC 9396 §2 は項目の型を type ごとに API が決めるとする） | Minor | 観点 | 候補の漏れ | — | 採用 |
| F18 | 台帳の rationale（抜き取り：C-roles・C-org-task-id・C-may-act、採用の C-aud・C-iss・C-sub） | 理由の採点で C-roles が RR2 否（assumption はあるが revisit\_trigger が無い）。同じ欠けが抜き取りの外の C-azp・C-org-approval-id・C-exp・C-iat・C-jti にもある。採用の C-iss・C-sub は代償（RR3）が無い（判定の理由：rationale\_rubric の採点の決まり（RR2 は前提と崩れる条件の両方、RR3 は採用でも代償を 1 つ）） | Minor | 観点 | 理由の不備 | — | 採用 |
| F19 | C-act.rationale・enforced\_at（invoices-api）、refs の RFC 8693 §4.1 | RFC 8693 §4.1 は「受け手は access control の判断に、トップレベルのクレームと今の行為者だけを考え、入れ子の act の過去の行為者は情報だけで判断に使わない（MUST）」とする。設計は請求書の API で入れ子の行為者の方針を「削る照合」に使う（C4）。C4 は、STS が交換のときに scope を連鎖の全行為者の方針の積で決める（C-scope の rationale に既にある）ことで、受け手が仕様どおり最も外側と scope だけを見ても防げる。受け手側の入れ子の照合を外すか、仕様と違う使い方として根拠を書き直す（判定の理由：書き手が 12. で専門家に見てほしいと書いた点。delegation-depth に回した） | Minor | 観点 | 前提の誤り | — | 保留 |
| F20 | 12. の「STS の実装」、AGENT\_RT.rt\_rotation、hops\[H2\] | STS は組織で作るもので、交換での深さ・取り消しの確認、resource が 2 つ以上の要求の拒否、取り直しでの scope の再計算、RT の再利用の検知を、どれも実測していない。C9・C10・C13・C14・C15 の防ぎ方がこれに依存する（Major 以上の判断）（判定の理由：escalation の unverified-idp-behavior に回した。拒否の試験（runtime/negative\_tests）で確かめるまで保留） | Major | 観点 | 理由の不備 | — | 保留 |

## 3. 対応の一覧

| 指摘 ID | 担当 | 期限 | 状態 | 対応の PR・コミット |
| --- | --- | --- | --- | --- |
| F01 | 書き手（パイロット C） | — | 未着手 | — |
| F02 | 書き手（パイロット C） | — | 未着手 | — |
| F03 | 書き手（パイロット C） | — | 未着手 | — |
| F05 | 書き手（パイロット C） | — | 未着手 | — |
| F06 | 書き手（パイロット C） | — | 未着手 | — |
| F07 | 書き手（パイロット C） | — | 未着手 | — |
| F08 | 書き手（パイロット C） | — | 未着手 | — |
| F09 | 書き手（パイロット C） | — | 未着手 | — |
| F10 | 書き手（パイロット C） | — | 未着手 | — |
| F11 | 書き手（パイロット C） | — | 未着手 | — |
| F12 | 書き手（パイロット C） | — | 未着手 | — |
| F13 | 書き手（パイロット C） | — | 未着手 | — |
| F14 | 書き手（パイロット C） | — | 未着手 | — |
| F15 | 書き手（パイロット C） | — | 未着手 | — |
| F16 | 書き手（パイロット C） | — | 未着手 | — |
| F17 | 書き手（パイロット C） | — | 未着手 | — |
| F18 | 書き手（パイロット C） | — | 未着手 | — |
| F19 | 書き手（パイロット C） | — | 未着手 | — |
| F20 | 書き手（パイロット C） | — | 未着手 | — |

## 4. 専門家に回した項目

| 基準の ID（escalation.md） | 行・欄 | 回した先 | 期限 | 結論 |
| --- | --- | --- | --- | --- |
| delegation-depth | claims:C-act、token\_types\[AGENT\_AT・TOOL\_AT\].max\_delegation\_depth（2） | 委任の専門家（未定） | 未定 | 未回答（F12・F19） |
| unverified-idp-behavior | 12. の STS の実装、AGENT\_RT.rt\_rotation（unverified）、H2 | STS の実装の持ち主（未定） | 未定 | 未回答（F20） |

当てはまらなかった基準：draft-spec・custom-crypto・cross-tenant-exchange・baseline-unmet・jwe-key-management・regulated-data・new-token-type

## 5. カタログ・観点書・対応表に戻す事項

| 戻す先 | 中身 | 指摘 ID | issue・PR |
| --- | --- | --- | --- |
| カタログ（templates/catalog） | 承認の記録の同時の消費・支払いの再試行（冪等）を利用のイベントの候補にする | F08 | — |
| 観点書（perspectives.md） | 交換の入力（subject\_token の aud が actor 自身か、actor ごとの宛先、委任の取り消しの確認）を問う問い、act の無い AT を出せるクライアントの許可リストを問う問い、入れ子の act を判断に使うと RFC 8693 §4.1 に反することを問う問い | F03・F09・F19 | — |
| lint・render（#6） | hops の to（URI）と enforced\_at の service（名前）が結びつかず矢印の表が空になる。カタログの回答の note と目録の束縛の食い違い（U10）は機械で拾えない | F14・F02 | — |

## 6. 理由の採点（抜き取り）

| 行の ID | 列 | RR1 | RR2 | RR3 | RR4 | RR5 | RR6 | RR7 | 合否 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C-may-act | rationale | 満 | 満 | 満 | 満 | 満 | 満 | 満 | 合格 |
| C-org-task-id | rationale | 満 | 満 | 満 | 満 | 満 | 満 | 満 | 合格 |
| C-roles | rationale | 満 | 否 | 満 | 満 | 満 | 満 | 満 | 不合格 |

- C-may-act：RFC 8693 §4.4 を開いて確かめた（may\_act の定義）。代わり（STS の方針の表）と失うものがある。要求 §3 の行為者ごとの操作・C4 に辿れる
- C-org-task-id：slide は開いていない（名前と主張の対応だけを見た）。q-txn は STS の記録で答える。要求 §3 のタスクの範囲に辿れる。rejection\_kind は代替ありが近い
- C-roles：assumption はあるが revisit\_trigger が無い（RR2 否）。理由は要求 §3 の「今の行為者の権限で判断」と C4 に辿れる。slide は開いていない

## 7. 点検状況

LLM によるレビュー。人による検証ではない。 人による点検は未実施

人による点検は未実施（このレビューは LLM のセッションのもの。人のレビュアーの採否は未了）。

レビュアーの名前は自己申告です（エディターにはログインが無い）。本当の承認は GitHub の PR のレビューで行います。

## 8. 問いごとの回答

| 段 | 問い ID | 回答 | 理由（1 行） |
| --- | --- | --- | --- |
| 1. 定義 | dc-01 | 該当なし | 新しい独自クレーム（組織の名前空間）を採用していない（C-org-\* は却下）。設計のチェックリストの対象の行が無い |
| 1. 定義 | dc-02 | 該当なし | 新しい独自クレーム（組織の名前空間）を採用していない（C-org-\* は却下）。設計のチェックリストの対象の行が無い |
| 1. 定義 | dc-03 | 該当なし | 新しい独自クレーム（組織の名前空間）を採用していない（C-org-\* は却下）。設計のチェックリストの対象の行が無い |
| 1. 定義 | dc-04 | 該当なし | 新しい独自クレーム（組織の名前空間）を採用していない（C-org-\* は却下）。設計のチェックリストの対象の行が無い |
| 1. 定義 | dc-05 | 該当なし | 新しい独自クレーム（組織の名前空間）を採用していない（C-org-\* は却下）。設計のチェックリストの対象の行が無い |
| 1. 定義 | dc-06 | 該当なし | 新しい独自クレーム（組織の名前空間）を採用していない（C-org-\* は却下）。設計のチェックリストの対象の行が無い |
| 1. 定義 | dc-07 | 該当なし | 新しい独自クレーム（組織の名前空間）を採用していない（C-org-\* は却下）。設計のチェックリストの対象の行が無い |
| 1. 定義 | dc-08 | 該当なし | 新しい独自クレーム（組織の名前空間）を採用していない（C-org-\* は却下）。設計のチェックリストの対象の行が無い |
| 1. 定義 | dc-09 | 該当なし | 新しい独自クレーム（組織の名前空間）を採用していない（C-org-\* は却下）。設計のチェックリストの対象の行が無い |
| 1. 定義 | dc-10 | 該当なし | 新しい独自クレーム（組織の名前空間）を採用していない（C-org-\* は却下）。設計のチェックリストの対象の行が無い |
| 1. 定義 | dc-11 | 該当なし | 新しい独自クレーム（組織の名前空間）を採用していない（C-org-\* は却下）。設計のチェックリストの対象の行が無い |
| 1. 定義 | dc-12 | 該当なし | 新しい独自クレーム（組織の名前空間）を採用していない（C-org-\* は却下）。設計のチェックリストの対象の行が無い |
| 1. 定義 | dc-gate | 該当なし | 新しい独自クレーム（組織の名前空間）を採用していない（C-org-\* は却下）。設計のチェックリストの対象の行が無い |
| 1. 定義 | pa-01 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-02 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-03 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-04 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-05 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-06 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-07 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-08 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-09 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-10 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-11 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-12 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-13 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-14 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-15 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-16 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-17 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-18 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-19 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-20 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-21 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-22 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-23 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-24 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-25 | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | pa-gate | Yes | 答えられない問いが残る独自クレームを共有にしていない（task\_id・approval\_id を却下し、標準の行で表した） |
| 1. 定義 | pa-trace | 該当なし | 共有クレームの追加が無く claim\_request\_\*.md が無い（claims.yaml の 4 行目）。25 問の対象が無い |
| 1. 定義 | q-registered-synonym | 該当なし | 独自クレームの行が採用に無い。登録名だけを使う |
| 1. 定義 | q-reuse-standard-structure | Yes | 鍵への束縛は cnf、承認は authorization\_details、委任は act と、既存の構造を使う |
| 1. 定義 | q-auth-context-semantics | Yes | C-iat.not\_meaning が「認証の時刻ではない」と書く。acr は却下し、強い確認は承認の記録で行う |
| 1. 定義 | q-scope-semantics | Yes | scope はタスクの範囲（C-scope.not\_meaning）。支払いは scope と authorization\_details の両方、と UC2 と not\_meaning に書いてある |
| 1. 定義 | q-value-vocabulary | 該当なし | roles・groups を載せない（C-roles 却下）。authorization\_details の type の語彙は value\_vocabulary にある |
| 1. 定義 | q-role-explosion | 該当なし | ロールを載せない |
| 1. 定義 | q-identifier-choice | Yes | sub は STS の不変の opaque な ID。テナントは無い（C-tenant 却下） |
| 1. 定義 | ap-1-6 | Yes | 照合は sub。email は却下 |
| 1. 定義 | q-pairwise-external | 該当なし | 外部の受け手が無い（組織は 1 つ、全受け手が社内） |
| 1. 定義 | q-pairwise-unguessable | 該当なし | ペアワイズにしない（外部の受け手が無い） |
| 1. 定義 | ap-2-1 | Yes | ロールを載せない。scope は max\_items 3・超過で発行を失敗 |
| 1. 定義 | ap-2-2 | Yes | authorization\_details は都度 DB を引く。scope は取り直し・交換で決め直す |
| 1. 定義 | ap-2-3 | No | authorization\_details の中の項目（金額・通貨・振込先）の型が台帳にも consumer schema（items が object だけ）にも無い（F17） |
| 1. 定義 | ap-2-4 | 該当なし | 独自クレームを採用していない |
| 1. 定義 | q-payload-readable | Yes | confidential\_from は全行で空なので定義上 Yes。ただし振込先がエージェント・ツールに読める点は F10 |
| 1. 定義 | q-confidential-reaches-reader | Yes | confidential\_from の相手が無い |
| 1. 定義 | q-no-secret-or-raw-pii | No | authorization\_details の creditorAccount（user.financial.bank\_account）が平文で AGENT\_AT に載り、読まない受け手（エージェント・ツール）に届く（F10） |
| 1. 定義 | q-derived-value | No | 請求書の API は支払いのたびに承認の記録を DB で引くので、トークンは approval\_id だけで足りる可能性があるのに比べていない（F10） |
| 1. 定義 | q-baseline-kept | Yes | 3.2 は「すべて満たす」。台帳の on\_missing・目録の alg\_allowlist・issuers で確かめた |
| 2. 発行 | q-single-issuer | Yes | 代替：issuers の列は空（Full の R1 error）だが、authoritative\_writer はすべて STS の 1 つ。サービスが追記しない |
| 2. 発行 | q-hook-failure | Yes | フックが無い（STS が自分で書く）。required\_claims の欠落は拒否 |
| 2. 発行 | q-size-limit | Yes | R8 で最悪 1739／8192 バイト（21%） |
| 2. 発行 | ap-1-7 | Yes | 代替：provenance の列は無いが、書き手はすべて platform の STS。authorization\_details はエージェントの申告でなく承認の記録から写す |
| 2. 発行 | q-hook-adds-raw-pii | 該当なし | 発行時フックが無い |
| 2. 発行 | q-minimal-per-recipient | No | authorization\_details の consumers は invoices-api と STS だけだが、H1 の AGENT\_AT（宛先はツール）に載る（F10） |
| 2. 発行 | q-rar-per-audience | No | H1（宛先 MCP のツール）にも type payment を載せる。ツールは読まない（F10） |
| 2. 発行 | q-agent-own-identity | Yes | エージェントごとに client\_id と証明書（2.1） |
| 2. 発行 | q-agent-delegation-claims | Yes | sub＝利用者、act・client\_id＝エージェント（AGENT\_AT） |
| 2. 発行 | q-idp-capability-verified | No | STS は組織で作るもので、交換での深さ・取り消しの確認・resource の拒否・RT の再利用の検知を、どれも実測も文書も無い（12. が認める）。C9・C10・C13・C15 の判断が依存する（F20） |
| 2. 発行 | q-variant-comparison | Yes | mTLS と DPoP を攻撃の型（TLS の終端）で比べた。mTLS はトークンのサイズを増やさない |
| 2. 発行 | q-outside-catalog | Yes | outside\_enumeration に探した範囲が具体的にある。ただしレビュアーの外の質問で F03・F07・F08・F09 を足した |
| 3. 伝搬 | cf-01 | Yes | 書き手は段階（①②③⑥）ごとに STS |
| 3. 伝搬 | cf-02 | Yes | on\_missing は全行で拒否 |
| 3. 伝搬 | cf-03 | 該当なし | 外部のトークンが無い（発行者は社内の STS の 1 つ） |
| 3. 伝搬 | cf-04 | Yes | H1→H2 で token\_type と aud が替わる |
| 3. 伝搬 | cf-05 | Yes | H2 は aud を置き換え、scope は同じ、寿命は 300→60 |
| 3. 伝搬 | cf-06 | 該当なし | Txn-Token を使わない |
| 3. 伝搬 | cf-07 | Yes | 全ホップの validates に中身がある |
| 3. 伝搬 | cf-08 | 該当なし | クレームをヘッダーに転記しない |
| 3. 伝搬 | cf-09 | 該当なし | IP・端末の文脈を判断に使わない（通信の相手は mTLS のワークロード ID） |
| 3. 伝搬 | cf-10 | Yes | sub はハッシュ、act・jti は記録、トークン全文は残さない（U14）。ただし approval\_id の記録は F06 |
| 3. 伝搬 | q-hop-narrowing | Yes | H2 は aud を 1 つに置き換え、scope・authorization\_details は部分集合で、STS の enforced\_at に強制が書いてある |
| 3. 伝搬 | q-hop-lifetime | Yes | H1 300 秒 → H2 60 秒。exp も subject\_token を超えない |
| 3. 伝搬 | q-single-aud-resource | Yes | resource で 1 つ。2 つ以上の要求は拒否（MCP の表の 1） |
| 3. 伝搬 | ap-2-6 | Yes | ツールは交換した TOOL\_AT だけで上流を呼ぶ |
| 3. 伝搬 | q-no-passthrough | No | 交換を許す actor と、actor ごとに割り当てる宛先（どの actor がどの resource 向けを得られるか）、subject\_token の宛先が actor 自身かの規則が台帳に無い（F03） |
| 3. 伝搬 | ap-2-5 | 該当なし | ヘッダーに写さない |
| 3. 伝搬 | q-unverified-claim-extraction | Yes | 全ホップで local に検証してから読む |
| 3. 伝搬 | q-gateway-bypass-path | No | エージェントが resource=請求書の API で AT を直接得て、ツールを通らずに呼ぶ経路の可否（STS のクライアントごとの許す resource）が書いていない（F03） |
| 3. 伝搬 | q-step-up-path-coverage | 該当なし | 追加認証を使わない（承認の記録で確認。I12 対象外） |
| 3. 伝搬 | q-txn-scope-fixed | 該当なし | Txn-Token を使わない |
| 3. 伝搬 | q-txn-required-claims | 該当なし | Txn-Token を使わない |
| 3. 伝搬 | q-claim-earliest-hop | Yes | authorization\_details は値が分かる AGENT\_AT から載せ、TOOL\_AT は部分集合 |
| 3. 伝搬 | ap-2-9 | Yes | TOOL\_AT は署名・60 秒・iss の束縛・失効の行がある |
| 3. 伝搬 | q-internal-delegation-token | Yes | TOOL\_AT の目録の行に署名・期限・tenant\_binding・revocation がある |
| 3. 伝搬 | ap-2-7 | Yes | 利用者のトークンを借りない。act の AT を同意と交換で得る |
| 3. 伝搬 | q-delegation-depth-and-revocation | Yes | max\_delegation\_depth 2、RT の系列の失効と交換の拒否で一括に止める。深さ 2 は escalation の delegation-depth に回した |
| 3. 伝搬 | q-idp-diff-absorbed | 該当なし | 発行者は 1 つで IdP の差が無い |
| 3. 伝搬 | q-token-not-in-url | Yes | AT は Authorization ヘッダー、クエリは拒否（MCP の表の 8）。SSE は U23 |
| 4. 検証 | q-shared-validator | No | M\_token\_validation の欄が無く、共通の検証部品を使うか判定できない（F13） |
| 4. 検証 | ap-1-1 | Yes | alg\_allowlist は ES256 だけ |
| 4. 検証 | ap-1-2 | Yes | validates は local で署名を検証 |
| 4. 検証 | q-validate-before-read | No | 検証の順序（M\_token\_validation#validation-order）の欄が無く判定できない（F13） |
| 4. 検証 | ap-1-3 | Yes | aud は required\_claims にあり、受け手が自分の URI と照合 |
| 4. 検証 | ap-1-4 | Yes | iss の許可リスト（1 つ）。テナントは無い |
| 4. 検証 | ap-1-5 | Yes | key\_source は issuer の metadata の jwks\_uri、ヘッダーの鍵は拒否 |
| 4. 検証 | ap-1-8 | Yes | exp 必須、ずれ 30 秒 |
| 4. 検証 | q-typ-distinguishes | Yes | AT は at+jwt、種類は aud で分かれる。ID トークンを出さない |
| 4. 検証 | q-required-rejected | Yes | 必須の欠落は拒否 |
| 4. 検証 | q-no-unverified-passthrough-mode | No | M\_token\_validation#library-config の欄も claim\_request の問 18 も無く判定できない（F13） |
| 4. 検証 | q-consumer-expression | No | authorization\_details の「完全一致」の比較で、金額の型・通貨・振込先の表記（大小・空白）の正規化が無い（value\_normalization が無い。F17） |
| 4. 検証 | q-nested-jwt-both-layers | 該当なし | JWE を使わない |
| 4. 検証 | q-unwrapped-value-authz | Yes | 署名の外の値（ログ）を認可に使わない。integrity\_until は監査ログだけ |
| 5. 認可 | q-object-level-authz | Yes | 請求書の API が sub と請求書の持ち主（DB）を照合して 404（C3） |
| 5. 認可 | q-tenant-data-match | 該当なし | 組織は 1 つでテナントが無い |
| 5. 認可 | q-writer-distinguished | Yes | 本人・呼び出し側が書く値で認可しない（承認の ID は本文から読まない。C7） |
| 5. 認可 | q-validity-not-authz | Yes | 操作（scope と行為者の方針）・対象（持ち主）・承認の内容で判断 |
| 5. 認可 | q-original-principal | Yes | 交換で sub を保ち、ツールの広い ID（client credentials）を作らない |
| 5. 認可 | q-authorize-service-and-user | Yes | act の最も外側を mTLS の相手と照合し、sub を持ち主と照合 |
| 5. 認可 | q-scope-and-role | Yes | scope と行為者の方針の表と、持ち主（利用者の権限）を照合。ただし H3 の validates に scope が無い（F14） |
| 5. 認可 | q-access-context-from-pep | 該当なし | アクセス元の文脈を判断に使わない |
| 5. 認可 | q-step-up-by-rs | 該当なし | 追加認証を使わず、支払いは人の承認の記録で確かめる（C-acr 却下・I12 対象外） |
| 5. 認可 | q-approval-from-as | Yes | 承認は承認のサービスの記録を STS が写し、請求書の API が DB で照合する。置き場所の比較は F10 |
| 5. 認可 | q-cross-tenant-identity | 該当なし | テナントが無い |
| 5. 認可 | q-operator-act | 該当なし | 運用者の代理操作を STS が実装しない（I19）。ただし 2.2（Full）が空（F13） |
| 5. 認可 | q-break-glass | 該当なし | break-glass を扱わない（I19）。2.2 が空なのは F13 |
| 5. 認可 | cd-01 | 該当なし | 請求書の DB はアプリの資格情報で接続し、トークン・DB の文脈を使わない（lifecycle-db-connection、U02 対象外） |
| 5. 認可 | cd-02 | 該当なし | 請求書の DB はアプリの資格情報で接続し、トークン・DB の文脈を使わない（lifecycle-db-connection、U02 対象外） |
| 5. 認可 | cd-03 | 該当なし | 請求書の DB はアプリの資格情報で接続し、トークン・DB の文脈を使わない（lifecycle-db-connection、U02 対象外） |
| 5. 認可 | cd-04 | Yes | 認可に使う値はすべて STS（platform）か承認の記録が書く。本人が書き換えられない |
| 5. 認可 | cd-05 | 該当なし | 請求書の DB はアプリの資格情報で接続し、トークン・DB の文脈を使わない（lifecycle-db-connection、U02 対象外） |
| 5. 認可 | cd-06 | 該当なし | 請求書の DB はアプリの資格情報で接続し、トークン・DB の文脈を使わない（lifecycle-db-connection、U02 対象外） |
| 5. 認可 | cd-07 | 該当なし | 請求書の DB はアプリの資格情報で接続し、トークン・DB の文脈を使わない（lifecycle-db-connection、U02 対象外） |
| 5. 認可 | cd-08 | Yes | トークンで DB に接続しないので、接続の層は無いと 9.1 に書いてある |
| 5. 認可 | cd-09 | 該当なし | 請求書の DB はアプリの資格情報で接続し、トークン・DB の文脈を使わない（lifecycle-db-connection、U02 対象外） |
| 5. 認可 | cd-10 | 該当なし | 請求書の DB はアプリの資格情報で接続し、トークン・DB の文脈を使わない（lifecycle-db-connection、U02 対象外） |
| 5. 認可 | cd-11 | 該当なし | 請求書の DB はアプリの資格情報で接続し、トークン・DB の文脈を使わない（lifecycle-db-connection、U02 対象外） |
| 5. 認可 | q-db-context-writers | 該当なし | DB の文脈・RLS を使わない（U02 対象外） |
| 5. 認可 | q-sql-tenant-predicate | 該当なし | DB の文脈・RLS を使わない（U02 対象外） |
| 5. 認可 | q-db-context-parameterized | 該当なし | DB の文脈・RLS を使わない（U02 対象外） |
| 5. 認可 | q-ddm-rls-only | 該当なし | DB の文脈・RLS を使わない（U02 対象外） |
| 6. 運用 | q-four-lifetimes-written | Yes | 9.1・9.2 に分けて書いてある。9.3 は廃止予定の行が無い |
| 6. 運用 | q-lifetime-rationale | No | 5.1（寿命の上限の方針）が空。数字の根拠はガイドと NIST の上限だけと 12. が書く（F13） |
| 6. 運用 | q-session-rt-bounds | Yes | RT は idle 1 時間・最大 8 時間、セッションは 30 分・8 時間 |
| 6. 運用 | q-rt-policy-by-client | Yes | 機密クライアントで送信者制約（加えてローテーション）。RFC 9700 §4.14.2 を引く |
| 6. 運用 | q-freshness-mitigation | Yes | 「超える」の authorization\_details に、請求書の API の都度の DB の照会が書いてある |
| 6. 運用 | q-refresh-reevaluated | No | 「取り直しで scope を委任と方針から決め直す」は STS の挙動で、実測も文書も無い（F20） |
| 6. 運用 | q-revocation-delivery | No | 交換での取り消しの確認（C9 の要）が、台帳の enforced\_at に無い（STS が subject\_token からどうやって委任の記録を引くかが jti の行の監査の記録だけ）（F03） |
| 6. 運用 | q-external-user-deprovision | 該当なし | 外部の IdP・取引先の利用者がいない |
| 6. 運用 | q-relies-on-at-expiry | No | ツールは AGENT\_AT を exp（最悪 330 秒）まで受け入れ、ツール側の結果のキャッシュを持たないことが書いていない（F15） |
| 6. 運用 | q-long-running | Yes | エージェントは自分の証明書に束縛した RT を持ち、取り直しのたびに STS が委任を確かめる。利用者のトークンを保持しない |
| 6. 運用 | q-system-actor-no-fake-sub | Yes | client credentials を作らず、利用者の sub を捏造しない |
| 6. 運用 | q-agent-short-lived-no-rt | No | AGENT\_RT（最大 8 時間）を出す。RT を出さない案との比較が理由に無い（F05） |
| 6. 運用 | q-copies-outlive | No | ツールサーバーが上流の結果をキャッシュするか、その期限と止め方が無い（F15） |
| 6. 運用 | q-deprecated-deadline | 該当なし | 廃止予定の行が無い |
| 6. 運用 | q-change-order | Yes | 9.3 に受け手が先・発行者が後の手順がある（変更中の行は無い） |
| 6. 運用 | q-key-rotation | Yes | JWKS、未知の kid は最短 60 秒・負のキャッシュ 60 秒、使う 1 日前に公開・外して 1 日残す |
| 6. 運用 | q-dependency-outage | No | 承認のサービス・STS の障害時に、支払い・交換を閉じる側に倒すかが書いていない（on\_fetch\_failure は JWKS だけ）（F16） |
| 6. 運用 | ap-2-8 | Yes | 台帳の log\_policy で値を分け、トークン全文は残さない（U14） |
| 6. 運用 | q-token-logging | No | 記録する HTTP ヘッダーの許可リスト・HAR の扱いの欄（M\_privacy\_minimization#audit-log）が無い（F13） |
| 6. 運用 | q-audit-log-protected | Yes | integrity\_until の trust\_boundary に「閲覧は監査の担当だけ」とある（保存期間は無い） |
| 6. 運用 | q-audit-correlation | No | U14 は approval\_id を監査ログに残すと書くが、C-authorization-details の log\_policy は「記録しない」で食い違う（F06） |
| 6. 運用 | q-trace-id-trust | Yes | traceparent を使わず、jti と STS の記録で相関 |
| 6. 運用 | q-scope-elevation-logged | No | ツールごとの最小の scope（呼び出しの操作だけ）から始めず、C14 の引き上げの拒否を記録する規則も無い（F11） |
| 6. 運用 | q-operational-metrics | No | 付録 A（Full）が空（F13） |
| 6. 運用 | q-lint-workaround | Yes | lint を通すための宣言の変更は無い |
| 6. 運用 | q-evidence-attribution | No | 3 件を抜き取った：RFC 9396 §9.1（JWT の AT。当てはまる）、RFC 8705 §3（cnf。当てはまる）、RFC 8693 §4.1（C-act。入れ子の act は access control の判断に使わない MUST に対し、設計は削る照合に使う。F19） |
| 6. 運用 | q-limit-consistency | No | U10 の「cnf が actor の証明書と同じ」は AGENT\_AT の cnf（エージェントの証明書）と食い違う（F02）。取り消しの目標 120 秒・90 秒・scope の volatility 900 秒も食い違う（F06） |

## 9. 行ごとの記録（エディターのレビューモード、#50。生成した時の台帳と比べた状態）

行の内容のハッシュ（RFC 8785 JCS の SHA-256、`tools/row_hash.py`）に結びつけた判定です。記録の後に行が変わると「再確認が要る」になります。ハッシュはその行の値だけを見ます（参照するトークン種別・ホップの行、25 問の回答、design.md の本文を変えても再確認にはなりません）。

| 行 | 判定 | 日時 | 今の行との対応 | コメント |
| --- | --- | --- | --- | --- |
| catalog\_answers:I14 | 修正を求める（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（2f8cb16bc466） | 承認つきの発行の確認を STS の enforced\_at に（F07） |
| catalog\_answers:U10 | 修正を求める（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（4f227902bc64） | cnf が actor の証明書と同じ、は AGENT\_AT の束縛と両立しない（F02） |
| claims:C-acr | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（d732203cc436） | 承認の記録で代える。崩れる条件もある |
| claims:C-act | 保留（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（99eb25540729） | RFC 8693 §4.1 との関係（F19）と深さの数え方（F12）を専門家に回した |
| claims:C-aud | 修正を求める（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（6165409433ff） | STS の subject\_token の宛先の確認を enforced\_at に足す（F02・F03） |
| claims:C-authorization-details | 修正を求める（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（736f75fa199d） | 消費の原子性（F08）、中の項目の型（F17）、振込先が読まない受け手に届く（F10） |
| claims:C-azp | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（fcc339285e37） | revisit\_trigger が無い（F18、軽微） |
| claims:C-client-id | 修正を求める（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（fbf2768b6b1a） | act の無い AT を受け入れる client\_id を portal に限る（F09） |
| claims:C-cnf | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（6bf93cbda653） | 行は妥当。U10 の記述は catalog\_answers:U10 で直す（F02） |
| claims:C-email | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（ae5848f9c405） | 前提と崩れる条件がある |
| claims:C-exp | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（5535342776ea） | revisit\_trigger が無い（F18、軽微） |
| claims:C-iat | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（3b84cf5927a9） | revisit\_trigger が無い（F18、軽微） |
| claims:C-iss | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（8ffe325752d1） | 許可リストの完全一致。代償の記述が無い（F18、軽微） |
| claims:C-jti | 修正を求める（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（0992eed3312c） | 交換で委任の記録を引いて取り消しを確かめる照合を、STS の enforced\_at に書く（F03） |
| claims:C-may-act | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（1e44c36989c1） | 抜き取りで採点：合格。STS の方針の表が代わりに答える |
| claims:C-nbf | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（1d1914b08d83） | 予約の支払いを範囲の外と前提にし、崩れる条件もある |
| claims:C-org-approval-id | 修正を求める（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（ab09efd672aa） | revisit\_trigger が無い（F18） |
| claims:C-org-task-id | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（2b2af546ebfc） | 抜き取りで採点：合格。rejection\_kind は「代替あり」が近い（STS の記録で答える） |
| claims:C-roles | 修正を求める（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（c5ea2dd7d1ad） | 抜き取りで採点：RR2 否（revisit\_trigger が無い。F18） |
| claims:C-scope | 修正を求める（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（73f4595c74a9） | volatility 900 秒と取り消しの目標の食い違い（F06）、呼び出しごとの絞り込み（F11） |
| claims:C-sub | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（466ec1eff55b） | C3・C15 に対応。代償の記述が無い（F18、軽微） |
| claims:C-tenant | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（a0d758138f41） | §7 の 9 に対応。崩れる条件もある |
| claims:C-txn | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（195a2cc2caa1） | TXN\_TOKEN の却下と一貫 |
| hops:H1 | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（b0eae68b2f07） | aud・cnf・act の照合がある。authorization\_details を載せる是非は F10 |
| hops:H2 | 修正を求める（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（f8db20d92c90） | 呼び出しごとの scope の絞り込み（F11）、交換の入力の確認（F03） |
| hops:H3 | 修正を求める（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（e1189b538d01） | validates に scope が無い（F14） |
| token\_types:AGENT\_AT | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（856fe91a85d7） | 寿命・束縛は妥当。取り消しの後のツール側の受け入れ（F15）は別の行で扱う |
| token\_types:AGENT\_RT | 修正を求める（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（ac109c6e9c97） | RT を出さない案との比較（F05）、再利用の検知は unverified（F20） |
| token\_types:AUTHORIZATION\_CODE | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（cb2f24bc9ed7） | 理由と要求の対応を確かめた |
| token\_types:CLIENT\_ASSERTION | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（cf144213ba16） | 理由と要求の対応を確かめた |
| token\_types:DPOP\_PROOF | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（c8a289fc1043） | 理由と要求の対応を確かめた |
| token\_types:ID\_JAG | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（63e2fb53d237） | 理由と要求の対応を確かめた |
| token\_types:ID\_TOKEN | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（1bb85f61c440） | 理由と要求の対応を確かめた |
| token\_types:INTERNAL\_TOKEN | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（6c507d27be4e） | 理由と要求の対応を確かめた |
| token\_types:INTROSPECTION\_RESPONSE\_JWT | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（e8384c6e15fd） | 理由と要求の対応を確かめた |
| token\_types:JARM\_RESPONSE | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（2994ef7bf866） | 理由と要求の対応を確かめた |
| token\_types:JAR\_REQUEST\_OBJECT | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（031b9ea58ec3） | 理由と要求の対応を確かめた |
| token\_types:JWT | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（b0bf798c142f） | 理由と要求の対応を確かめた |
| token\_types:LOGOUT\_TOKEN | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（fd97de2037a3） | 理由と要求の対応を確かめた |
| token\_types:PORTAL\_AT | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（271c374b38e0） | 理由と要求の対応を確かめた |
| token\_types:SECURITY\_EVENT\_TOKEN | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（34bf0d17e87d） | 却下は妥当。90 秒と 3.1 の 120 秒をそろえる（F06） |
| token\_types:SESSION | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（2afb279494c8） | 理由と要求の対応を確かめた |
| token\_types:STATUS\_LIST\_TOKEN | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（3aacf7d50c74） | 理由と要求の対応を確かめた |
| token\_types:TOOL\_AT | 修正を求める（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（d0410c2701be） | 呼び出しのたびの交換と 60 秒の使い回しの食い違い（F06） |
| token\_types:TXN\_TOKEN | 承認（LLM） | 2026-11-24T07:08:54+09:00 | 一致（記録のときのまま）（fb928f649dd3） | 理由と要求の対応を確かめた |

計 45 行：承認 31・修正を求める 13・保留 1。再確認が要る 0・台帳に無い 0

---

## 付記：レビュアー R1 の記述（手で書いた部分）

> **LLM によるレビュー。人による検証ではない。** 上の 1.〜8. は `tools/review_record.py report` が review.yaml から生成した。この付記はレビュアー（LLM のセッション 1 つ。claude-opus-5-5）が手で書いた。

### A. 読み方と範囲

- 読んだもの：設計のディレクトリの design.md・claims.yaml・token_types.yaml・hops.yaml・catalog_answers.yaml・schemas/TOOL_AT.consumer.schema.json、要求の概要 brief-C.md、templates/review の procedure・perspectives（168 問）・decision_tree・rationale_rubric・escalation・report_template・README・review.schema.json。claim_lint を profile full と lite で実行した。RFC 8693 §4.1・§4.4 と RFC 9396 の目次・§6 を原文で確かめた
- 読んでいないもの：author-log.md、templates/examples/**、templates/casestudy-*、research/** のうち設計のディレクトリ以外、ケーススタディのリポジトリと xlsx、PR #54 のコメント、R2 の記録。contrasts/ は表題だけ見た（本文は読んでいない）
- 指摘の ID の F04 は欠番（下書きの段階で F03 に統合した）

### B. 判断の木での確かめ（段 2）

| 問い（6.） | 判断の木の節 | 設計の仕組み | 結果 |
| --- | --- | --- | --- |
| q-sub・q-actor | keep-sub-exchange | RFC 8693 の交換で sub を保ち act を入れ子 | 一致。ただし入れ子の act を判断に使う点は F19 |
| q-peer | peer-mtls | mTLS の相手の証明書（クレームで代えない） | 一致 |
| q-authorized | rar-vs-custom | authorization_details（type payment）＋scope の併用、どちらで何を決めるか UC2 に記述 | 一致。中の項目の型は F17 |
| q-authorized（承認の鮮度） | carry-or-query | 載せて、支払いのたびに DB でも引く | 載せる・引くの両方を持つ理由が無い（F10） |
| q-txn・q-req-wl | txn-tctx | 使わない（上流 1 段） | 妥当。請求書の API が先を呼ぶと崩れる（revisit_trigger あり） |
| q-still-valid | lifetime-by-situation | AT 300／60 秒、RT 8 時間 | 「長時間ジョブ・非同期」の行は利用者の RT を持たないとするが、AGENT_RT はエージェントの RT（F05 で比較を求めた） |

「目的と仕組みの不一致」の指摘は 0 件。仕組みの取り違えは見つからなかった。

### C. 要求への追跡（却下 3 行・採用 3 行以上）

却下の行（抜き取りの種 `r1-pilot-c` で選んだ 3 行）：

| 行 | 理由が支える要求（brief-C） | 追跡の結果 |
| --- | --- | --- |
| C-may-act | §3「行為者ごとにしてよい操作が違う」、§7 の 7、脅威 C4 | 代わり（STS の方針の表）が C-act・C-scope の enforced_at（sts-token-exchange「actor が方針の表で代理を許されている」）に実在する。辿れる |
| C-org-task-id | §3「タスクには範囲がある」、§7 の 6 | 範囲は C-scope、タスクの特定は STS の委任の記録と jti。受け手が回数・金額を数える要求は brief に無いので、却下は要求と矛盾しない。辿れる |
| C-roles | §3「今その操作をしている行為者の権限で判断する」、脅威 C4 | 役割を載せないことで過去の行為者の役割で通す誤りを避ける、は C4 に直接対応。ただし revisit_trigger が無い（F18） |

採用の行（同じ種で選んだ 3 行 C-aud・C-iss・C-sub と、要求の中心の 2 行 C-act・C-authorization-details）：

| 行 | 要求 | 追跡の結果 |
| --- | --- | --- |
| C-aud | 脅威 C2・C13、§7 の 4 | ツール・請求書の API の enforced_at に宛先の照合がある。STS の側（subject_token の宛先）が無い（F02・F03） |
| C-iss | §6「汎用の攻撃（別の発行者）はシナリオによらず防ぐ」 | 許可リスト 1 つと issuer の JWKS。辿れる。代償の記述が無い（F18） |
| C-sub | §3「利用者の請求書だけを扱う」、脅威 C3・C15 | 請求書の API の data_layer での持ち主の照合と、STS の sub の写し。辿れる |
| C-act | §3「多段の委任。2 段は正規・5 段は拒否」「今の行為者の権限で判断」、C4・C10・C11 | 深さ 2 の強制は STS と API の両方。C11 の数え方は未確定（F12）。入れ子の照合は RFC 8693 §4.1 と衝突（F19） |
| C-authorization-details | §3「承認の記録どおりにだけ支払う」、C5・C6・C7・C8 | 完全一致と DB での状態の確認と消費。競合と再試行（F08）、中の項目の型（F17）が要求を満たすかを左右する |

脅威の表の全件の当てはめ（レビュアーの読み）：C2（aud・cnf）、C3（sub と持ち主）、C4（STS の scope の積と API の方針）、C5・C6（完全一致）、C7（本文の ID を使わない）、C9（RT の失効・交換の拒否。ただし交換での確認が台帳に無い F03、ツール側のキャッシュ F15）、C10（深さ 2）、C12（cnf と client_id。許可リストが無い F09）、C13（resource 1 つ・aud・cnf）、C14（scope の部分集合）、C15（sub の写し）。正規の C1・C8・C11 は、U10 の記述どおりに実装すると交換で拒否される（F02）。

### D. 一覧の外を探した記録（段 5）

- 時間：約 4〜5 分（07:00 ごろ〜07:04 ごろ。設計の読みと並行して考えた時間を含む推定。LLM の思考の時間は機械で測れない）
- 範囲：(1) 要求の脅威 C2〜C15 を、H1→STS（交換の入力）→H2 の矢印ごとに、攻撃者が触れるもの（subject_token・resource・scope・actor の証明書）で置き換えた。(2) 承認の記録の一生（作成・トークンに載せる・使う・消費・取り消し）と、並行の要求・障害時の再送。(3) 各防御を 1 つずつ外したとき（cnf が無い・act が付かない IdP・STS の設定の誤り）に次の層が止めるか。(4) 依存先（STS・承認のサービス）の障害。(5) ツールサーバーの手元の写し（結果のキャッシュ・SSE）。(6) エージェントがツールを迂回して請求書の API を直接呼ぶ経路
- 見つけたもの：F03（交換の入力の確認と actor ごとの宛先）、F07（承認とタスクの結び付け・載せ直しの要求）、F08（消費の競合と冪等）、F09（act の無い AT の許可リスト）。F15・F16 は観点書の問い（q-copies-outlive・q-dependency-outage）にも当たったので出どころは「観点」にした
- 探したが当たらなかったもの：ツールの結果の改ざん（応答の完全性。社内 mTLS の中で、要求に無い）、同意の画面でのエージェントの scope の要求の改ざん（STS が方針の積で決め直す）、署名鍵を全種別で共有すること（at+jwt と aud で分かれ、発行者が 1 つなので指摘にしなかった）

### E. 重大度の分布と、迷った点

- Blocker 0・Major 9・Minor 10（計 19）。出どころ：テンプレート項目 4、観点 11、カタログ外の質問 1、テンプレート外 3
- Blocker を付けなかった理由：偽造・なりすまし・他人のデータに直接届く経路は、どれも別の層（請求書の API の持ち主の照合・行為者の方針の表・承認の DB の照合）が止める。F03・F09 は、その「別の層」が 1 枚だけになる指摘で、層が崩れると Blocker に上がる
- 迷った点は notes.md に書いた
