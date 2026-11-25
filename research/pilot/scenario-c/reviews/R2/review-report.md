# レビューレポート：シナリオ C AI エージェントの委任（Lite）。LLM によるレビュー。人による検証ではない

> 設計書のエディターのレビューモード（#50）が `review.yaml` から生成した。レビュアーの名前は自己申告で、本当の承認は GitHub の PR のレビューで行う。レビュアーは LLM で、人による点検は未実施。

## 1. 基本情報

| 項目 | 値 |
| --- | --- |
| 対象 | research/pilot/scenario-c（版 f8c26c7）。research/pilot/scenario-c（worktree agent-a9f5b6ad37dc24c26、読み取りだけ）。LLM によるレビュー。人による検証ではない |
| Lite／Full | 設計書は 5 問で Full と判定し、パイロットの指示で Lite の欄で書いた。レビュアーの確認：Full が正しい（委任・交換 Yes、新しい発行者 Yes）。F01 |
| 実施した手順の段 | 0〜7（8 は書き手の対応の後。段 0 は error 53 で返却の条件に当たるが、パイロットの指示で続けた） |
| レビュアーと役割 | R2（LLM：claude-opus-5-5（Claude Code のサブエージェントのセッション。パイロット #9 のブラインドのレビュアー R2）。名前は自己申告）。1 名（LLM）の役割の切り替え：攻撃者 → 運用 → 受け手 → 発行者 → 個人情報 → クライアント（本番の失敗から読む指示のため、運用を 2 番目に上げた）。同じセッションの中で切り替え、日は分けていない。独立レビュー：提出まで、ほかのレビュアーの記録を画面で隠した（画面で隠すだけで、review.yaml を開けば見える。守ったかは自己申告） |
| 実施日 | 2026-11-24 |
| 使った教材の版 | templates/review（レビューした時の版：perspectives.md 0.4.0、report\_template.md 0.4.0、問い 168 問）。templates/review（perspectives 0.4.0・report\_template 0.4.0・procedure 0.4.0・rationale\_rubric 0.5.0・escalation 0.4.0）、decision\_tree、contrasts、tools/claim\_lint、tools/review\_record.py。worktree のコミット f8c26c7 |
| CI の結果 | claim\_lint error 53・warn 1・info 9（profile full）。設計書の 1. と一致。設計書の 1. と同じ（worktree f8c26c7 と main 1a24390 の lint で同じ件数）。--profile lite では error 0・warn 3（L15、L73 が 2 件）。render --check は OK |
| 抜き取りの結果 | 乱数の種「R2-scenario-c-2026-11-24」（claims.yaml の却下の行 10 行から 3 行。sha256(種:行) の順）：C-azp・C-email・C-roles。3 件を採点、合格 1・不合格 2 |
| 問いの回答 | 全 168 問のうち 168 問に回答（未回答 0）。定義 Yes 15／No 6／該当なし 38。発行 Yes 8／No 2／該当なし 2。伝搬 Yes 15／No 4／該当なし 9。検証 Yes 10／No 3／該当なし 1。認可 Yes 11／No 3／該当なし 14。運用 Yes 11／No 13／該当なし 3。合計 Yes 70／No 31／該当なし 67 |

## 2. 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 出どころ | 種別 | 取り違えた問い（種別が目的と仕組みの不一致のとき） | 判定 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F01 | template:00\_core（冒頭の Lite／Full）、template:00\_core#ci-results、2.2・5.1・7.・9.3・付録 A〜C | 設計書自身が README の 5 問で Full と判定（委任・交換 Yes、新しい発行者 Yes）しながら Lite の欄で書いた。claim\_lint の既定（profile full）で error 53（R1：issuers・issue\_events・overflow\_strategy・propagation\_delay・status が空）。procedure.md の段 0 の 1.（error が 0 でなければ返す）と 2.（シナリオ A の A17）に当たる。Lite の profile では error 0・warn 3（L73 が 2 件）。Full だけの 2.2 システムの権限・5.1 寿命の上限・7. シーケンス図・9.3・付録が空で、console:admin・寿命の方針・変更の手順の判断が抜けている（F09・F17）（判定の理由：パイロットの指示で Lite にしたと冒頭と 12. に明記。手順の上は返却に当たるが、指示との関係を #9 で決める） | Major | テンプレート項目 | 実装とのずれ | — | 保留 |
| F02 | catalog\_answers:U10.note、token\_types:AGENT\_AT.holder、hops:H1.validates | U10 の回答は「STS は subject\_token の cnf が actor（ツールサーバー）の証明書と同じことを確かめる」と書く。しかし AGENT\_AT の cnf は要求したエージェントの証明書の拇印で（AGENT\_AT の holder、H1 の checks）、ツールの証明書と一致することはない。書いたとおりに作ると正規の C1・C8・C11 の交換がすべて失敗し、運用で「cnf の確認を外す」直しが入りやすい。交換で確かめるべきは「subject\_token の aud が actor の登録した resource と一致する」こと（と、必要なら subject\_token の cnf が呼び出し元のエージェントの証明書だったこと）で、どの照合を STS が行うかを台帳の enforced\_at（sts-token-exchange）に書く（判定の理由：同じ事実が 2 か所で食い違う。攻撃の側から交換の束縛を辿って見つけた） | Major | テンプレート外 | 実装とのずれ | — | 採用 |
| F03 | claims:C-authorization-details.enforced\_at（invoices-api）、token\_types:TOOL\_AT.revocation（db\_lookup） | 請求書の API は「承認の記録が承認済み・未使用であることを確かめてから消費する」と書くが、確かめと消費を 1 つの原子的な条件つき更新（未使用なら使用済みにする）で行うと書いていない。TOOL\_AT の 60 秒の間に同じ承認で並行に 2 件の支払いを送ると、どちらも「未使用」を読んで二重に払える（TOCTOU）。また応答が失われた支払いの再試行で、二重払いか「使用済み」の誤った拒否になる。冪等キー（approval\_id を支払いの冪等キーにする）と、再試行で前の結果を返す扱いを決める（判定の理由：要求の C5〜C8 の外の、本番の並行と再送の失敗の型。カタログ外の場面「障害時の再送」にも当たる） | Major | テンプレート外 | 候補の漏れ | — | 採用 |
| F04 | token\_types:AGENT\_AT（aud・visible\_to）、issuance\_profile:request\_protection、template:00\_core#scope-boundary（MB） | 同意（委任）が「どの MCP サーバー向けにトークンを得てよいか」を束縛していない。STS は resource が 1 つであることだけを確かめるので、エージェント（LLM。プロンプトインジェクションで誘導されうる）が悪意ある MCP サーバー B の resource で AGENT\_AT を求めれば、B に sub・scope（読む・支払う）・authorization\_details（振込先の口座・approval\_id）が届く。cnf で B は使えないが、個人情報と承認の内容は漏れ、B が交換の行為者として登録されていれば交換も試せる。さらに、エージェントが読んだ u1 の請求書の内容をツールの引数で B に渡す漏えいはトークンでは止まらない。委任の記録に許す resource の一覧を持ち STS が照合すること、トークンをモデルの文脈に入れないこと、B への引数の流出を範囲の外と明記するか対策を書く（判定の理由：要求 C13 は再送だけを挙げるが、悪意ある MCP サーバーへの発行そのものが別の脅威） | Major | テンプレート外 | 候補の漏れ | — | 採用 |
| F05 | hops:H2.exchanger、claims:C-act.enforced\_at（sts-token-exchange）、claims:C-client-id.enforced\_at（invoices-api）、template:profiles/P4\_ai\_agent\_delegation#delegation-policy | 交換の規則が表になっていない：どの行為者（mTLS の主体）が、どの宛先の subject\_token を、どの宛先（resource）へ、どの範囲で交換してよいか。may\_act の却下の理由は「STS の方針の表で決める」とするが、その表の中身が無い。また請求書の API は「act の無いトークンは client\_id と mTLS の相手が一致すれば受ける」だけで、act の無いトークンを出してよいクライアントの許可の一覧（portal だけ）が無い。STS がエージェントの認可コードの経路で act を付け忘れた・resource=invoices を許した場合に、エージェントが利用者のトークン相当で直接請求書の API を呼べる（C12 の型）（判定の理由：q-no-passthrough の「交換を許すクライアント・割り当てる宛先・範囲を組織の規則として」に当たる） | Major | 観点 | 候補の漏れ | — | 採用 |
| F06 | catalog\_answers.outside\_enumeration、template:00\_core#scope-boundary | 要求の概要の補足に「現状の実装では、交換をしないときツールは自分の広い ID で上流を読む」「承認の ID は本文のものを信じる」とある。設計はどちらも禁じるが、移行の期間の旧経路（ツールの広い ID の資格情報、本文の承認 ID を読む支払いの口）をいつ・どう閉じるか、請求書の API が旧経路のトークン・資格情報を拒否し始める順序、閉じたことの確かめ方が無い。旧経路が残る限り C2・C7 は防げない（判定の理由：q-outside-catalog の例「移行期間の旧経路」に当たる） | Major | カタログ外の質問 | 候補の漏れ | — | 採用 |
| F07 | claims:C-authorization-details.enforced\_at、token\_types:TOOL\_AT.revocation、template:00\_core#lifecycle | 委任の取り消しの後も、ツールが手元に持つ TOOL\_AT（最大 60＋30 秒）で、未使用の承認の支払いが通る。請求書の API は支払いのたびに承認の記録を DB で引くのに、委任（タスク）の状態は引かない。要求は「取り消した後は、エージェントが続けて使えてはいけない」。支払いは即時に止めたい操作なので、承認の照会と同じ往復で委任の状態も確かめる（または取り消しで、その委任に結んだ未使用の承認を無効にする）（判定の理由：要求 §3 に照らすと剥奪の遅れ。C9（9 分後の読む）はこの設計で防げるが、取り消し直後の支払いは防げない） | Major | 観点 | 候補の漏れ | — | 採用 |
| F08 | template:00\_core#priorities-deferrals、token\_types:TOOL\_AT.refresh、claims:C-authorization-details.on\_revoke | ツールは呼び出しのたびに STS で交換し、請求書の API は支払いのたびに承認の DB を引き、STS は交換・取り直しのたびに委任の DB を引く。これらの障害のときに閉じる側に倒す（拒否する）こと、STS の可用性と応答時間の目標、交換の結果の再利用（60 秒の TOOL\_AT を同じタスクで使い回すか）が書いていない。9.1 の「呼び出しのたびに交換」と「タスクをまたいで使い回さない」が両立する読み方（タスクの中では使い回すのか）も曖昧。STS が単一障害点になり、障害時に「照会を飛ばして通す」直しが入りやすい（判定の理由：q-dependency-outage の No） | Major | 観点 | 候補の漏れ | — | 採用 |
| F09 | template:00\_core#system-privileges（空）、catalog\_answers:I19、template:00\_core#principals（console:admin） | 要求の表で console:admin は「読む・支払う・返金する」行為者だが、どのトークンで請求書の API を呼ぶか（運用者の代理は sub＝利用者・act＝運用者か、自分の ID か）が無い。I19 は「委任の行為者として許さない」で閉じるが、管理コンソール自身の経路は 2.2（Full）が空のまま。請求書の API は act の無いトークンを client\_id と mTLS の一致で受けるので、管理コンソールが利用者の sub で act なしのトークンを得る構成なら、監査で運用者の操作と見分けられない。緊急時の特権（承認・短い期限）も無い（判定の理由：q-operator-act・q-break-glass の No） | Major | 観点 | 候補の漏れ | — | 採用 |
| F10 | claims:C-authorization-details（type・description・value\_vocabulary）、schemas/TOOL\_AT.consumer.schema.json | C5・C6 の防御は「請求書・金額・通貨・振込先の完全一致」だが、authorization\_details の内側の項目の型と正規化が台帳にも受け手のスキーマにも無い（items は {type: object} だけ）。金額を数値で比べるか文字列で比べるか（120000 と 120000.0、"120000"）、通貨の大文字小文字、口座 ID の空白・大文字小文字が受け手ごとに分かれると、誤拒否か、緩い比較での通過が起きる。金額は文字列の 10 進（RFC 9396 の例と同じ）、通貨は ISO 4217 の大文字、口座は参照 ID の完全一致と決め、受け手のスキーマの properties と required に書く（判定の理由：dc-05・dc-08・ap-2-3 を authorization\_details の内側に当てた） | Major | 観点 | 候補の漏れ | — | 採用 |
| F11 | template:00\_core#uncertain（STS の実装）、issuance\_profile:grants、token\_types:AGENT\_RT.rt\_rotation | 守りの中心（resource の 2 つ以上の拒否、交換での深さ・取り消し・部分集合の確認、sub の差し替えの拒否、RT の再利用の検知、取り直しでの再評価）が、これから作る組織の STS の挙動に依存し、実測も仕様書も無い。12. に書いてあり、確かめ方の案（C2〜C15 の拒否の試験）もあるが、受け入れの条件（どの試験が通れば本番に出すか）が無い（判定の理由：escalation の unverified-idp-behavior に回す） | Major | 観点 | 候補の漏れ | — | 保留 |
| F12 | claims:C-act（description「深さは 2 まで」）、token\_types:TOOL\_AT.max\_delegation\_depth、template:00\_core#uncertain（深さの数え方） | 要求は「2 段は正規（C11）、5 段は拒否（C10）」。設計は act の数で 2 まで（エージェント・ツール）とし、それは C1 の経路そのもの。要求が C1 と別に C11 を「2 段の連鎖」として挙げることから、C11 は C1 より長い連鎖（エージェント → ツール → 別のツール）の可能性があり、その読み方なら上限 2 は C11 を誤って拒否する。C10・C11 の具体的な act の形（例のトークン）を要求の出し手に確かめ、上限の値と 3・4 段の扱いを決める（判定の理由：書き手も 12. に挙げた。escalation の delegation-depth に回す） | Minor | テンプレート項目 | 前提の誤り | — | 保留 |
| F13 | claims:C-authorization-details.on\_missing、claims:C-act.on\_missing | on\_missing が「拒否」だが、無いのが正規のトークンがある：読む操作の AGENT\_AT・TOOL\_AT には authorization\_details が無く（「支払いのときだけ載せる」）、PORTAL\_AT には act が無い。受け手が台帳どおりに実装すると C1・ポータルの利用を落とす。逆に、受け手が「無ければ読む操作として通す」を実装すると、支払いの端点で authorization\_details の無いトークンを通す誤りが起きうる。操作ごと（支払いでは必須、読むでは無くてよい）・種別ごとの意味を absent\_semantics に書く（判定の理由：dc-07・q-consumer-expression） | Minor | 観点 | 実装とのずれ | — | 採用 |
| F14 | claims:C-authorization-details.log\_policy、catalog\_answers:U14、token\_types（log\_policy の列が無い） | authorization\_details の log\_policy は「記録しない」だが、U14 は approval\_id を監査ログに残すと書く（q-txn の仕組みも approval\_id で結ぶ）。項目単位の扱い（approval\_id は記録、creditorAccount は記録しない）を書き分ける。目録の log\_policy（Full の列）、記録する HTTP ヘッダーの許可リスト、HAR・ログからトークンを除く手順、監査ログの保存期間も無い。sub のハッシュは ID の空間が小さいので、塩なしなら総当たりで戻せる（鍵つきのハッシュにする）（判定の理由：cf-10・q-token-logging・q-audit-log-protected・q-internal-delegation-token） | Minor | 観点 | 実装とのずれ | — | 採用 |
| F15 | claims:C-authorization-details（data\_category user.financial.bank\_account） | 振込先の口座を平文で AGENT\_AT・TOOL\_AT に載せ、エージェント（LLM）・ツール・（F04 の経路では）信頼しない MCP サーバーが読める。受け手が要るのは「承認どおりの相手先か」の判定で、要求の例の振込先も B-019 という参照 ID。口座の番号ではなく承認の記録の相手先の参照 ID（か拇印）だけを載せれば、C6 の照合を保ったまま個人情報を減らせる。12. の「JWE にするか決めていない」より先に、載せない案を比べる（判定の理由：q-no-secret-or-raw-pii・q-derived-value） | Minor | 観点 | 候補の漏れ | — | 採用 |
| F16 | issuance\_profile:rt\_strategy、token\_types:AGENT\_RT（rt\_rotation）、template:00\_core#deviations（RT の方式） | RT の方式の理由が「RFC 9700 §4.14.2 が挙げる 2 つの手段の 1 つ」だが、その節の 2 つの手段は公開クライアントへの要求で、エージェントは機密クライアント（tls\_client\_auth）。さらに送信者制約なのにローテーションも行い、再利用の検知は unverified。render の E-rt-sender-constrained.1（送信者制約ならローテーション不要）とも食い違う。ローテーションをやめるか、行う理由（証明書の漏えいへの備えなど）を書く（判定の理由：q-rt-policy-by-client。理由の採点の RR5・RR7） | Minor | 観点 | 理由の不備 | — | 採用 |
| F17 | template:00\_core#lifetime-policy（空）、token\_types:AGENT\_AT・TOOL\_AT・AGENT\_RT（lifetime\_refs） | 寿命の数値（300・60・28800 秒）が組織の上限の表（5.1）の中に無く、取り消しの目標 120 秒（3.1）から 60＋30＝90 秒を導く式は暗黙。AGENT\_AT の lifetime\_refs が slide:p10-per-tool-scopes（範囲の節）を引いており、寿命の根拠に当たるか疑わしい。目標（要求には数値が無い。§7 の 2）を業務の持ち主に確かめ、式と代償（交換の回数）を書く（判定の理由：q-lifetime-rationale。書き手も 12. に挙げた） | Minor | 観点 | 理由の不備 | — | 採用 |
| F18 | template:modules/M\_token\_validation（欄が無い）、hops:H1〜H3.validates | 受け手は 3 つ（ツール・請求書の API・STS の交換）で、act の最も外側と mTLS の照合、深さ、行為者の方針の積など独自の照合が多いのに、共通の検証部品で提供すること、検証の無効化・デバッグのモードを持たないことが書いていない。受け手ごとの実装の差が C4・C10 の取りこぼしになる（判定の理由：q-shared-validator・q-no-unverified-passthrough-mode） | Minor | 観点 | 候補の漏れ | — | 採用 |
| F19 | claims:C-sub.enforced\_at（invoices-api）、template:00\_core#lifecycle-db-connection | 請求書の DB へはサービスの資格情報で接続し、持ち主の条件で利用者を分ける。C3・C15 の防御はこの条件に懸かるのに、全 SQL（一覧・検索・支払い・返金・書き出し）に持ち主の条件を付ける規約と、それを確かめる検査（コードの検査・試験）が無い。新しい端点で条件を付け忘れると他人の請求書が読める（判定の理由：q-sql-tenant-predicate（テナントを持ち主に読み替えた）） | Minor | 観点 | 候補の漏れ | — | 採用 |
| F20 | template:00\_core#operational-metrics（空） | 攻撃の試みを運用で見る指標が無い：aud・cnf の不一致（C2・C13）、act の最も外側と相手の不一致（C12）、深さ超過（C10）、範囲の引き上げの要求（C14）、sub の差し替えの要求（C15）、承認の不一致（C5〜C7）の件数と、しきい値・通知先。どれも「正しく署名された、期限内のトークン」での攻撃（要求の §6）なので、拒否のログが唯一の検知の手段（判定の理由：q-operational-metrics・q-scope-elevation-logged） | Minor | 観点 | 候補の漏れ | — | 採用 |
| F21 | token\_types:AGENT\_RT | 観点書はエージェントのトークンをタスク単位の短命にし RT を出さない形を求めるが、設計は AGENT\_RT（idle 1 時間・最大 8 時間）を出す。取り消しの起点を STS に集める理由（AGENT\_RT の rationale）はあるが、タスクごとの再同意・交換だけで足りない理由（8 時間のタスクの実例）が無い（判定の理由：q-agent-short-lived-no-rt。RT を出す判断自体は妥当な余地があり、業務のタスクの長さを確かめて決める） | Minor | 観点 | 理由の不備 | — | 保留 |
| F22 | template:00\_core#hop-table（render:arrow-table）、hops:H1〜H3.to、claims:\*.enforced\_at.service | 矢印ごとの表の「確かめるクレーム」がすべて「—」。hops の to が URI（https://invoices.example.com など）で、台帳の enforced\_at の service が名前（invoices-api・tool:invoice-mcp）なので、render が受け手を結べない。生成の表で受け手の照合の漏れを確かめられない。to を台帳の service の名前にそろえる（か対応を宣言する）（判定の理由：lint が警告しないので、lint にも戻す（5.）） | Minor | テンプレート項目 | 実装とのずれ | — | 採用 |
| F23 | template:00\_core#ci-results（L15 warn）、token\_types:AGENT\_RT | L15 が「AGENT\_RT は mtls なのに cnf の行がない」と warn を出す。AGENT\_RT は opaque で、束縛は STS の DB にありクレームの cnf は載らない。lint の誤検知の候補だが、設計書は warn に行ごとの理由を書いていない（templates/CONTRIBUTING.md の 2.）（判定の理由：設計の誤りではなく lint の規則の候補。#6 に渡す） | Minor | テンプレート項目 | 実装とのずれ | — | 保留 |
| F24 | claims:C-cnf、token\_types:AGENT\_RT（sender\_constraint mtls） | ワークロードの証明書の更新（組織の PKI の有効期間・更新の周期が書いていない）と cnf の束縛の関係が無い。RT を証明書の拇印に束縛すると、証明書の更新で進行中のタスクの RT（最大 8 時間）がすべて使えなくなり、利用者の再同意が一斉に要る。運用で「拇印でなく主体名で束縛」に緩める直しが入りやすい。証明書の寿命と RT の寿命の関係、更新のときの扱い（RT はクライアントに束縛し、AT だけ拇印に束縛するなど）を決める（判定の理由：本番の運用（証明書の更新）から辿った） | Minor | テンプレート外 | 候補の漏れ | — | 採用 |
| F25 | token\_types:AGENT\_AT・TOOL\_AT・PORTAL\_AT（key\_rotation・signing\_key\_scope shared） | 署名鍵は 3 種類の AT で共有（signing\_key\_scope shared）で、ローテーションは 90 日の通常の手順だけ。鍵の漏えいのときの緊急の手順（新しい鍵への即時の切り替え、古い kid の JWKS からの削除と受け手のキャッシュ 3600 秒・use\_last\_known の扱い）が無い。use\_last\_known は、JWKS を取れない受け手が外した鍵を使い続ける経路にもなる（判定の理由：本番の失敗の型（鍵の漏えい）から辿った） | Minor | テンプレート外 | 候補の漏れ | — | 採用 |
| F26 | claims:C-azp・C-roles・C-org-approval-id（revisit\_trigger）、claims:C-scope（代償） | 理由の抜き取りで不合格：C-azp・C-roles・C-org-approval-id は assumption はあるが revisit\_trigger が無い（RR2）。採用の C-scope は代償（交換のたびの部分集合の計算、方針の表の保守）が行にも 3.1 にも無い（RR3）。抜き取りの外でも C-exp・C-iat・C-jti に revisit\_trigger が無い（判定の理由：rationale\_rubric の RR2・RR3） | Minor | 観点 | 理由の不備 | — | 採用 |
| F27 | template:00\_core#scope-boundary（STS）、要求の概要 §2「時刻を進めて試すための模擬」 | 要求の発行サービスは仮想の時計で時刻を進められる模擬。組織の STS を本番に出すとき、時刻を進める口・試験用の鍵・試験用の行為者が本番に残らないこと（と、試験の STS の鍵を本番の受け手の JWKS に載せないこと）が書いていない。残れば、期限と取り消しの守り（C9）が全部崩れる（判定の理由：カタログ外の場面「テストの経路」から辿った） | Minor | テンプレート外 | 候補の漏れ | — | 採用 |

## 3. 対応の一覧

| 指摘 ID | 担当 | 期限 | 状態 | 対応の PR・コミット |
| --- | --- | --- | --- | --- |
| F01 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F02 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F03 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F04 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F05 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F06 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F07 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F08 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F09 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F10 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F11 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F12 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F13 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F14 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F15 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F16 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F17 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F18 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F19 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F20 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F21 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F22 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F23 | lint の持ち主（#6） | — | 未着手 | — |
| F24 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F25 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F26 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |
| F27 | 書き手（パイロット #9 のシナリオ C） | — | 未着手 | — |

## 4. 専門家に回した項目

| 基準の ID（escalation.md） | 行・欄 | 回した先 | 期限 | 結論 |
| --- | --- | --- | --- | --- |
| delegation-depth | token\_types:TOOL\_AT.max\_delegation\_depth（2）、claims:C-act（入れ子の act を削る照合に使う） | 組織の認証基盤の担当 | — | 未（F12） |
| unverified-idp-behavior | template:00\_core#uncertain（STS の実装）、issuance\_profile:grants、token\_types:AGENT\_RT.rt\_rotation | STS（IdP）の運用の担当 | — | 未（F11） |

当てはまらなかった基準：draft-spec・custom-crypto・cross-tenant-exchange・baseline-unmet・jwe-key-management・regulated-data・new-token-type

## 5. カタログ・観点書・対応表に戻す事項

| 戻す先 | 中身 | 指摘 ID | issue・PR |
| --- | --- | --- | --- |
| lint（tools/claim\_lint、#6） | hops の to が台帳の consumers・enforced\_at の service のどれとも一致しないときに警告する（矢印の表が空になるのを機械で拾う） | F22 | — |
| lint（tools/claim\_lint、#6） | L15 を opaque の RT（cnf のクレームを持たない）で出さない、または「束縛は STS の側」と宣言する列を設ける | F23 | — |
| 観点書（perspectives.md） | 交換の照合の中身を問う問いが無い：「交換の STS は subject\_token のどの値（aud・cnf・act）を actor のどの値と照合するか」。F02 は q-limit-consistency でしか拾えなかった | F02 | — |
| 観点書（perspectives.md） | 承認・一回限りの値の消費の原子性と冪等（並行と再送）を問う問いを足す（q-approval-from-as の下） | F03 | — |
| 観点書（perspectives.md） | エージェントが求めてよい resource を委任（同意）で束縛するか、信頼しない MCP サーバーへの発行を問う問いを足す（q-single-aud-resource は 1 つかだけを問う） | F04 | — |
| 観点書（perspectives.md） | q-revocation-delivery に「取り消しの後に、手元の下流のトークンで高リスクの操作が通る時間」を明示する | F07 | — |
| カタログ（templates/catalog/） | 利用のイベントに「送信者制約の鍵・証明書の更新（cnf の束縛の切り替え）」と「署名鍵の緊急の失効」を足す | F24・F25 | — |

## 6. 理由の採点（抜き取り）

| 行の ID | 列 | RR1 | RR2 | RR3 | RR4 | RR5 | RR6 | RR7 | 合否 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C-azp | rationale | 満 | 否 | 満 | 満 | 満 | 満 | 満 | 不合格 |
| C-email | rationale | 満 | 満 | 満 | 対象外 | 満 | 満 | 満 | 合格 |
| C-roles | rationale | 満 | 否 | 満 | 満 | 満 | 満 | 満 | 不合格 |

- C-azp：revisit\_trigger が無い（ID トークンを出すことになったとき、が書ける）。RFC 9068 §2.2 は開いていない
- C-email：根拠を引かない行（数値・製品の挙動の主張が無い）
- C-roles：revisit\_trigger が無い。slide:p10-agent-identity は開いておらず、名前と主張の対応だけを見た

## 7. 点検状況

LLM によるレビュー。人による検証ではない。人による点検は未実施

人による点検は未実施（このレビューは LLM のセッションのもの。人のレビュアーの採否は未了）。

レビュアーの名前は自己申告です（エディターにはログインが無い）。本当の承認は GitHub の PR のレビューで行います。

## 8. 問いごとの回答

| 段 | 問い ID | 回答 | 理由（1 行） |
| --- | --- | --- | --- |
| 1. 定義 | dc-01 | 該当なし | 新しい独自クレームの採用行が無い。authorization\_details は登録名で、volatility 0 は 9.2 の DB の照合で扱う（q-freshness-mitigation） |
| 1. 定義 | dc-02 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | dc-03 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | dc-04 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | dc-05 | No | authorization\_details の内側（instructedAmount.amount・currency・creditorAccount・invoice\_id）の型が台帳にも受け手のスキーマ（items は object だけ）にも無い。F10 |
| 1. 定義 | dc-06 | 該当なし | 登録名だけ。scope は RFC の space\_delimited、authorization\_details は配列 |
| 1. 定義 | dc-07 | No | C-authorization-details と C-act の on\_missing が「拒否」だが、読む操作の AGENT\_AT・TOOL\_AT は authorization\_details を持たず、PORTAL\_AT は act を持たない。absent\_semantics（Full の列）が空。F13 |
| 1. 定義 | dc-08 | No | 完全一致で照合すると書くが、金額の表記（120000 と "120000.00"）・口座の ID の大文字小文字と空白の正規化が無い。F10 |
| 1. 定義 | dc-09 | Yes | sub は STS の変わらない ID（identifier\_properties）。表示名・メールを載せない |
| 1. 定義 | dc-10 | Yes | すべての採用行に authoritative\_writer があり、STS（platform）だけが書く。authorization\_details は承認の記録から写し、エージェントの申告から作らない |
| 1. 定義 | dc-11 | Yes | authorization\_details は max\_items 1・max\_bytes 400・overflow 発行を失敗。scope は max\_items 3 |
| 1. 定義 | dc-12 | Yes | 代替：claims の issuers（Full の列）は空だが、目録の issuers が STS 1 つ。on\_missing は拒否 |
| 1. 定義 | dc-gate | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-01 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-02 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-03 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-04 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-05 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-06 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-07 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-08 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-09 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-10 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-11 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-12 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-13 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-14 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-15 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-16 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-17 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-18 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-19 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-20 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-21 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-22 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-23 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-24 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-25 | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | pa-gate | Yes | 答えられない問いが残る組織のクレーム（task\_id・approval\_id）は載せずに却下した |
| 1. 定義 | pa-trace | 該当なし | 該当なし：組織の独自の共有クレームを足していない（C-org-task-id・C-org-approval-id は却下。claim\_request\_\*.md が無い） |
| 1. 定義 | q-registered-synonym | Yes | 独自クレームが無い。azp は client\_id と同じ意味として却下し、2 つ載せていない |
| 1. 定義 | q-reuse-standard-structure | Yes | 鍵への結び付けは cnf、承認は authorization\_details、行為者は act と既存の構造を使った |
| 1. 定義 | q-auth-context-semantics | Yes | acr を却下し、C-iat の not\_meaning に「利用者が認証した時刻ではない」とある |
| 1. 定義 | q-scope-semantics | Yes | C-scope・C-authorization-details の not\_meaning に分担（操作の範囲と、どの請求書・金額か）が書いてある |
| 1. 定義 | q-value-vocabulary | 該当なし | roles・groups を載せない（C-roles 却下）。authorization\_details の type の語彙は value\_vocabulary にある |
| 1. 定義 | q-role-explosion | 該当なし | ロールを載せない |
| 1. 定義 | q-identifier-choice | Yes | 利用者のキーは iss（1 つ）＋sub。テナントは持たない（C-tenant 却下、単一の組織） |
| 1. 定義 | ap-1-6 | Yes | email を却下し、照合は sub |
| 1. 定義 | q-pairwise-external | 該当なし | 外部の受け手が無い（組織は 1 つ、crosses\_boundary No） |
| 1. 定義 | q-pairwise-unguessable | 該当なし | ペアワイズの sub を使わない |
| 1. 定義 | ap-2-1 | 該当なし | グループ・ロールを載せない |
| 1. 定義 | ap-2-2 | Yes | scope は委任の取り消しで RT 失効＋交換の拒否、authorization\_details は支払いのたびの DB の照合 |
| 1. 定義 | ap-2-3 | No | 受け手のスキーマ（TOOL\_AT.consumer.schema.json）の authorization\_details の items が {type: object} だけで、内側の型が固定されていない。F10 |
| 1. 定義 | ap-2-4 | 該当なし | 独自クレームが無い |
| 1. 定義 | q-payload-readable | Yes | 形式上は Yes（confidential\_from が全行で空）。ただし振込先の口座が信頼しない MCP サーバーに届きうる点は F04・F15 |
| 1. 定義 | q-confidential-reaches-reader | Yes | confidential\_from を持つ行が無い。JWE を使わない判断は 12. に保留として書いてある |
| 1. 定義 | q-no-secret-or-raw-pii | No | authorization\_details の creditorAccount（振込先の口座）が平文で AGENT\_AT・TOOL\_AT に載り、エージェント（LLM）・ツールが読める。口座の参照 ID だけにできるか未検討。F15 |
| 1. 定義 | q-derived-value | No | 受け手が要るのは「承認どおりの相手先か」の判定で、口座そのものではない。参照 ID か拇印で足りるかを比べていない。F15 |
| 1. 定義 | q-baseline-kept | Yes | 3.2 で全基準を満たすと宣言。受け入れの検証は目録の alg\_allowlist・issuers・required\_claims・typ にある |
| 2. 発行 | q-single-issuer | Yes | 発行者は STS の 1 つで、ツール・請求書の API はクレームを足さない |
| 2. 発行 | q-hook-failure | 該当なし | 発行時フックを使わない（組織の STS が直接書く） |
| 2. 発行 | q-size-limit | Yes | R8 で最悪 1739／8192 バイト |
| 2. 発行 | ap-1-7 | Yes | 全行の書き手が STS（platform）。本文の承認 ID を信じない（C7） |
| 2. 発行 | q-hook-adds-raw-pii | 該当なし | 発行時フックが無い |
| 2. 発行 | q-minimal-per-recipient | Yes | authorization\_details は支払いのときだけ AGENT\_AT に載り、交換の STS と請求書の API が読む。PORTAL\_AT には載せない |
| 2. 発行 | q-rar-per-audience | Yes | H1・H2 の authorization\_details は payment の type だけ |
| 2. 発行 | q-agent-own-identity | Yes | エージェントごとに別の証明書と client\_id（2.1） |
| 2. 発行 | q-agent-delegation-claims | Yes | sub＝利用者、act.sub・client\_id＝エージェント（AGENT\_AT）、ツール（TOOL\_AT） |
| 2. 発行 | q-idp-capability-verified | No | STS は組織がこれから作るもので、resource の拒否・交換での深さと取り消しの確認・RT の再利用の検知・取り直しでの再評価のどれも実測も仕様書も無い（12. に記載）。F11 |
| 2. 発行 | q-variant-comparison | Yes | 3. と 4. で mTLS と DPoP、tls\_client\_auth と private\_key\_jwt を、開く攻撃（C2・C12・C13）とサイズ（R8・other\_headers\_bytes）で比べている |
| 2. 発行 | q-outside-catalog | No | outside\_enumeration に探した範囲と 3 件はある。しかしレビュアーが思いつく「移行期間の旧経路」（現状のツールの広い ID・本文の承認 ID）と「障害時の再送」（支払いの再試行）が範囲の中で答えられていない。F06・F03 |
| 3. 伝搬 | cf-01 | Yes | 台帳の authoritative\_writer に段階（①②③⑥）ごとの書き手がある |
| 3. 伝搬 | cf-02 | Yes | フックは無く、on\_missing は拒否 |
| 3. 伝搬 | cf-03 | 該当なし | 外部のトークンが無い（単一の発行者） |
| 3. 伝搬 | cf-04 | Yes | H2 で交換し aud を替える |
| 3. 伝搬 | cf-05 | Yes | H2 は aud を narrowing\_exception つきで替え、scope は同じ、寿命は 60≦300 |
| 3. 伝搬 | cf-06 | 該当なし | Txn-Token を使わない |
| 3. 伝搬 | cf-07 | Yes | H1〜H3 の validates が local で中身がある |
| 3. 伝搬 | cf-08 | 該当なし | クレームをヘッダーに写さない |
| 3. 伝搬 | cf-09 | 該当なし | IP・端末を認可に使わない。直接の相手は mTLS の主体で要求ごとに確かめる |
| 3. 伝搬 | cf-10 | No | C-authorization-details の log\_policy は「記録しない」だが、U14 の回答は approval\_id を記録すると書く。目録の log\_policy（Full の列）が無い。F14 |
| 3. 伝搬 | q-hop-narrowing | Yes | H2 は aud 1 つ、scope・authorization\_details は subject\_token の部分集合と書いてある（STS の実装で強制するかは F11） |
| 3. 伝搬 | q-hop-lifetime | Yes | TOOL\_AT 60 秒 ≦ AGENT\_AT 300 秒。exp は subject\_token を超えない（C-exp の enforced\_at） |
| 3. 伝搬 | q-single-aud-resource | Yes | resource で 1 つに絞り、2 つ以上を拒否（MCP の必須チェック 1） |
| 3. 伝搬 | ap-2-6 | Yes | ツールは受け取った AGENT\_AT を上流に渡さず交換する |
| 3. 伝搬 | q-no-passthrough | No | 交換を許す行為者・受け付ける subject\_token の宛先・割り当てる宛先・範囲の規則の表が無い（P4 の delegation-policy が未記入）。U10 の「cnf が actor の証明書と同じ」は AGENT\_AT の cnf（エージェントの証明書）と矛盾する。F05・F02 |
| 3. 伝搬 | ap-2-5 | 該当なし | クレームをヘッダーに写さない |
| 3. 伝搬 | q-unverified-claim-extraction | Yes | どのホップも local で署名を検証する |
| 3. 伝搬 | q-gateway-bypass-path | No | 請求書の API を呼ぶ他の経路（console:admin、移行前のツールの広い ID の経路）が範囲の図に矢印として無い。F09・F06 |
| 3. 伝搬 | q-step-up-path-coverage | 該当なし | 追加認証を使わず、支払いは承認の記録で確かめる（acr 却下） |
| 3. 伝搬 | q-txn-scope-fixed | 該当なし | Txn-Token を使わない |
| 3. 伝搬 | q-txn-required-claims | 該当なし | Txn-Token を使わない |
| 3. 伝搬 | q-claim-earliest-hop | Yes | authorization\_details を H1 の AGENT\_AT から載せ、H2 はその部分集合 |
| 3. 伝搬 | ap-2-9 | Yes | TOOL\_AT は署名（ES256）・失効（交換の拒否＋exp）・iss の束縛・監査ログ（U14）がある |
| 3. 伝搬 | q-internal-delegation-token | No | 目録の log\_policy（Full の列）が TOOL\_AT・AGENT\_AT に無く、ログの扱いは U14 の文だけ。F14 |
| 3. 伝搬 | ap-2-7 | Yes | エージェントは利用者のトークンを受け取らず、cnf と act で借用を拒否（C12） |
| 3. 伝搬 | q-delegation-depth-and-revocation | Yes | max\_delegation\_depth 2、委任の取り消しで RT の系列の失効と交換の拒否。深さ 2 なので専門家に回す（escalation delegation-depth） |
| 3. 伝搬 | q-idp-diff-absorbed | 該当なし | 発行者は STS の 1 つで IdP の差が無い |
| 3. 伝搬 | q-token-not-in-url | Yes | AT は Authorization ヘッダーだけ、クエリの access\_token を拒否（必須チェック 8）。SSE もヘッダー |
| 4. 検証 | q-shared-validator | No | 受け手（ツール・請求書の API・STS の交換）が共通の検証部品を使うと書いていない（M\_token\_validation の欄が無い）。F18 |
| 4. 検証 | ap-1-1 | Yes | alg\_allowlist ES256、header\_key\_params reject |
| 4. 検証 | ap-1-2 | Yes | validates が local（署名を検証） |
| 4. 検証 | q-validate-before-read | Yes | act・authorization\_details の照合は受け入れの検証の後と hops の checks の順で読める |
| 4. 検証 | ap-1-3 | Yes | aud は required\_claims にあり、自分の正規の URI と一致 |
| 4. 検証 | ap-1-4 | Yes | iss は許可リストの 1 つと完全一致 |
| 4. 検証 | ap-1-5 | Yes | key\_source は issuer\_metadata\_jwks\_uri |
| 4. 検証 | ap-1-8 | Yes | exp 必須、ずれ 30 秒 |
| 4. 検証 | q-typ-distinguishes | Yes | ID トークンを出さず、AT は at+jwt。請求書の API は TOOL\_AT と PORTAL\_AT を act の有無と client\_id で分ける（F05 で許可の一覧を求める） |
| 4. 検証 | q-required-rejected | Yes | required\_claims と on\_missing 拒否 |
| 4. 検証 | q-no-unverified-passthrough-mode | No | 検証の無効化・デバッグのモードを持たないと書いていない。F18 |
| 4. 検証 | q-consumer-expression | No | on\_missing が拒否の行で、無いのが正規のトークン（読む操作の authorization\_details、PORTAL\_AT の act）がある。式が拒否に倒れると C1・ポータルが落ちる。F13 |
| 4. 検証 | q-nested-jwt-both-layers | 該当なし | JWE を使わない |
| 4. 検証 | q-unwrapped-value-authz | Yes | 署名の外に写した値（監査ログ）を認可に使わない（integrity\_until は log だけ） |
| 5. 認可 | q-object-level-authz | Yes | 請求書の API が sub と請求書の持ち主（DB）を照合し 404（C3・C15）。承認の持ち主も sub と照合 |
| 5. 認可 | q-tenant-data-match | 該当なし | テナントを持たない（単一の組織） |
| 5. 認可 | q-writer-distinguished | Yes | 値はすべて STS が書き、本人・呼び出し側の値（本文の承認 ID）を認可に使わない |
| 5. 認可 | q-validity-not-authz | Yes | 操作（scope）・行為者の方針・持ち主・承認の内容を照合する |
| 5. 認可 | q-original-principal | Yes | ツールは交換で sub＝利用者のトークンを得る。client credentials の広い ID を作らない |
| 5. 認可 | q-authorize-service-and-user | Yes | mTLS の相手と act の最も外側、sub と持ち主をそれぞれ照合 |
| 5. 認可 | q-scope-and-role | Yes | role の代わりに、行為者の方針の表と持ち主の照合。scope と両方を確かめる |
| 5. 認可 | q-access-context-from-pep | 該当なし | IP・端末を判断に使わない |
| 5. 認可 | q-step-up-by-rs | 該当なし | 追加認証ではなく人の承認の記録で確かめる設計（C-acr の却下に理由と崩れる条件） |
| 5. 認可 | q-approval-from-as | Yes | 承認は承認の記録から STS が写し、請求書の API が DB で状態を引く。トークンと台帳の両方を使う理由が C-org-approval-id と 3.1 にある（消費の原子性は F03） |
| 5. 認可 | q-cross-tenant-identity | 該当なし | テナントをまたがない |
| 5. 認可 | q-operator-act | No | console:admin（読む・支払う・返金する）がどのトークンで請求書の API を呼ぶかが無い。2.2（Full）が空で、請求書の API は act の無いトークンを client\_id と相手の一致だけで受ける。F09 |
| 5. 認可 | q-break-glass | No | 緊急時の特権の経路と承認・期限が書いていない（2.2 が空）。F09 |
| 5. 認可 | cd-01 | 該当なし | DB の文脈・RLS・DB のロールをトークンで設定しない。請求書の API がサービスの資格情報で接続し、持ち主の条件で照会する（lifecycle-db-connection） |
| 5. 認可 | cd-02 | 該当なし | DB の文脈・RLS・DB のロールをトークンで設定しない。請求書の API がサービスの資格情報で接続し、持ち主の条件で照会する（lifecycle-db-connection） |
| 5. 認可 | cd-03 | 該当なし | DB の文脈・RLS・DB のロールをトークンで設定しない。請求書の API がサービスの資格情報で接続し、持ち主の条件で照会する（lifecycle-db-connection） |
| 5. 認可 | cd-04 | Yes | 持ち主（DB の行）と STS が書いた sub だけで認可する |
| 5. 認可 | cd-05 | 該当なし | DB の文脈・RLS・DB のロールをトークンで設定しない。請求書の API がサービスの資格情報で接続し、持ち主の条件で照会する（lifecycle-db-connection） |
| 5. 認可 | cd-06 | 該当なし | DB の文脈・RLS・DB のロールをトークンで設定しない。請求書の API がサービスの資格情報で接続し、持ち主の条件で照会する（lifecycle-db-connection） |
| 5. 認可 | cd-07 | 該当なし | DB の文脈・RLS・DB のロールをトークンで設定しない。請求書の API がサービスの資格情報で接続し、持ち主の条件で照会する（lifecycle-db-connection） |
| 5. 認可 | cd-08 | 該当なし | DB の文脈・RLS・DB のロールをトークンで設定しない。請求書の API がサービスの資格情報で接続し、持ち主の条件で照会する（lifecycle-db-connection） |
| 5. 認可 | cd-09 | Yes | 利用者単位の監査は請求書の API と STS の監査ログ（sub のハッシュ・jti）で行う |
| 5. 認可 | cd-10 | Yes | on\_missing 拒否、持ち主の条件が合わなければ 404 |
| 5. 認可 | cd-11 | Yes | DB の層は無いと設計書に書き、C3 は C2〜C15 の拒否の試験の計画に入る（12.） |
| 5. 認可 | q-db-context-writers | 該当なし | DB の文脈を使わない |
| 5. 認可 | q-sql-tenant-predicate | No | サービスの ID で DB に接続し、持ち主の条件だけで利用者を分けるのに、全 SQL（一覧・検索・支払い・返金）に持ち主の条件を付ける規約と検査が無い。F19 |
| 5. 認可 | q-db-context-parameterized | 該当なし | DB の文脈を使わない |
| 5. 認可 | q-ddm-rls-only | 該当なし | DDM・RLS を使わない |
| 6. 運用 | q-four-lifetimes-written | 該当なし | 独自クレームが無い。登録名の 4 層は 9. の生成の表にある |
| 6. 運用 | q-lifetime-rationale | No | 5.1（Full）が空で、AGENT\_AT 300・TOOL\_AT 60・RT 8 時間は書き手の判断（12.）。取り消しの目標 120 秒から導く式と、交換の負荷の代償の比較が無い。F17 |
| 6. 運用 | q-session-rt-bounds | Yes | AGENT\_RT idle 3600／最大 28800、SESSION 1800／28800。24 時間以下 |
| 6. 運用 | q-rt-policy-by-client | No | 機密クライアントに対し、RFC 9700 §4.14.2（公開クライアントへの要求）を根拠に引き、送信者制約なのにローテーションも行い再利用の検知は unverified。E-rt-sender-constrained.1（ローテーション不要）とも食い違う。F16 |
| 6. 運用 | q-freshness-mitigation | Yes | 「超える」の authorization\_details に、請求書の API の支払いのたびの DB の照合（担い手つき） |
| 6. 運用 | q-refresh-reevaluated | No | 取り直しで委任・方針・承認の状態を再評価する前提を、STS の実測も文書も無く置いている。F11 |
| 6. 運用 | q-revocation-delivery | No | 種別ごとの最悪の秒数はある。しかし支払いは「すぐ止めたい操作」なのに、請求書の API は承認の状態だけを引き、委任の状態を引かない。取り消しの後も最大 90 秒、手元の TOOL\_AT で未使用の承認を支払える。F07 |
| 6. 運用 | q-external-user-deprovision | 該当なし | 外部の IdP・取引先の利用者がいない |
| 6. 運用 | q-relies-on-at-expiry | No | 委任の取り消しの請求書への反映が TOOL\_AT の exp（60＋30 秒）に依存する。支払いについて F07 |
| 6. 運用 | q-long-running | Yes | エージェントは自分の ID の委任の RT で取り直し、可否は取り直しのたびに STS が決める。ツールは交換で分単位のトークン |
| 6. 運用 | q-system-actor-no-fake-sub | Yes | client credentials を作らず、サービスの ID で利用者の sub を作らない |
| 6. 運用 | q-agent-short-lived-no-rt | No | AGENT\_AT は 300 秒だが AGENT\_RT（8 時間）を出す。タスク単位の再同意と比べた理由はある（9.1）が、問いの基準は RT を出さないこと。F21 |
| 6. 運用 | q-copies-outlive | Yes | SSE は exp で閉じ（U23）、判断のキャッシュをしない（U21）、分析基盤に複製しない（U28） |
| 6. 運用 | q-deprecated-deadline | 該当なし | 廃止予定の行が無い |
| 6. 運用 | q-change-order | No | 9.3（Full）が空で、authorization\_details の payment の型を変えるときの手順が無い。F01 |
| 6. 運用 | q-key-rotation | Yes | JWKS から取り、未知の kid は 60 秒の最短間隔と負のキャッシュ、使う 1 日前に公開・1 日残す（通常のローテーション。緊急の失効は F25） |
| 6. 運用 | q-dependency-outage | No | STS（呼び出しのたびの交換）・承認の記録の DB・委任の状態の DB の障害のとき、閉じる側に倒すかと、上流の可用性の目標が無い。JWKS だけ use\_last\_known がある。F08 |
| 6. 運用 | ap-2-8 | Yes | U14 にトークンの全文を残さないとある |
| 6. 運用 | q-token-logging | No | 記録する HTTP ヘッダーの許可リストと、HAR・ログからトークンを除く手順が無い。F14 |
| 6. 運用 | q-audit-log-protected | No | 監査ログの閲覧者（監査の担当）は integrity\_until にあるが、保存期間と方針が無い。F14 |
| 6. 運用 | q-audit-correlation | Yes | sub（ハッシュ）・act の連鎖・jti・approval\_id を STS と請求書の API の監査ログで結ぶ（txn は使わない理由あり） |
| 6. 運用 | q-trace-id-trust | Yes | 相関には署名されたトークンの jti を使い、traceparent を監査に使わない |
| 6. 運用 | q-scope-elevation-logged | No | C14 のような範囲の引き上げの要求を STS が拒否すると書くが、その試みを相関 ID つきで記録・通知すると書いていない。F20 |
| 6. 運用 | q-operational-metrics | No | 付録 A が空。aud・cnf の不一致（C2・C13 の試み）、交換の拒否、深さ超過の件数を誰が測るかが無い。F20 |
| 6. 運用 | q-lint-workaround | Yes | lint を通すための宣言の変更は見当たらない（Lite で書いたのはパイロットの指示と 12. に書いてある） |
| 6. 運用 | q-evidence-attribution | Yes | 3 件を抜き取った：rt\_strategy の RFC 9700 §4.14.2（公開クライアントへの要求で、この行の状況に合わない。F16）、C-authorization-details の RFC 9396 §9.1（JWT の AT に載せる節で合う）、AGENT\_AT の NIST IR 8587 §5.3.1.1（1 時間以内で合う）。引用元は開いておらず、名前と主張の対応だけを見た |
| 6. 運用 | q-limit-consistency | No | U10 の「cnf が actor の証明書と同じ」が AGENT\_AT の holder・H1 の checks（cnf はエージェントの証明書）と食い違う。log\_policy と U14 も食い違う。F02・F14 |

## 9. 行ごとの記録（エディターのレビューモード、#50。生成した時の台帳と比べた状態）

行の内容のハッシュ（RFC 8785 JCS の SHA-256、`tools/row_hash.py`）に結びつけた判定です。記録の後に行が変わると「再確認が要る」になります。ハッシュはその行の値だけを見ます（参照するトークン種別・ホップの行、25 問の回答、design.md の本文を変えても再確認にはなりません）。

| 行 | 判定 | 日時 | 今の行との対応 | コメント |
| --- | --- | --- | --- | --- |
| catalog\_answers:I01 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（fe18bbdbff09） | — |
| catalog\_answers:I02 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（ebfe3a04e916） | — |
| catalog\_answers:I03 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（279be1b2b697） | — |
| catalog\_answers:I04 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（7888f7e88f9e） | — |
| catalog\_answers:I05 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（479c43941772） | 移行の旧経路は F06 |
| catalog\_answers:I06 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（60a34610381b） | — |
| catalog\_answers:I07 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（8937bf599108） | — |
| catalog\_answers:I08 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（cd6678918f1d） | — |
| catalog\_answers:I09 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（df516118fbc5） | — |
| catalog\_answers:I10 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（a347a78c5ea4） | — |
| catalog\_answers:I11 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（5ce7883f6997） | — |
| catalog\_answers:I12 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（873d0040bf34） | — |
| catalog\_answers:I13 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（803cc655e280） | — |
| catalog\_answers:I14 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（2f8cb16bc466） | — |
| catalog\_answers:I15 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（f1f2ac4cd228） | — |
| catalog\_answers:I16 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（6318ec19ae94） | — |
| catalog\_answers:I17 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（4cf5ba277a0d） | — |
| catalog\_answers:I18 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（a61d031d43b9） | — |
| catalog\_answers:I19 | 修正を求める（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（b2ccdb62b796） | F09（管理コンソールの経路） |
| catalog\_answers:I20 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（061cdcc9d7a5） | — |
| catalog\_answers:I21 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（a284529a38e4） | — |
| catalog\_answers:I22 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（ac3aad661eff） | — |
| catalog\_answers:I23 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（dd7782f53365） | — |
| catalog\_answers:I24 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（392e9bfd80e4） | — |
| catalog\_answers:I25 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（49fbfaff0887） | — |
| catalog\_answers:I26 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（533a695b77f8） | — |
| catalog\_answers:I27 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（d9e77fe967a1） | — |
| catalog\_answers:I28 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（91a406761e40） | — |
| catalog\_answers:I29 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（097f31f0d4cc） | — |
| catalog\_answers:I30 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（3ed5018596ad） | — |
| catalog\_answers:I31 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（6c99d9af8b91） | — |
| catalog\_answers:I32 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（c2a39ba7c656） | — |
| catalog\_answers:I33 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（f15a24c07134） | — |
| catalog\_answers:I34 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（94933ed18477） | — |
| catalog\_answers:U01 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（59af16e46254） | — |
| catalog\_answers:U02 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（45adcc6d6457） | — |
| catalog\_answers:U03 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（2812f3661fd8） | — |
| catalog\_answers:U04 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（6e28e34a2996） | — |
| catalog\_answers:U05 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（42cc1ba7a5b6） | — |
| catalog\_answers:U06 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（93cef2c2905d） | — |
| catalog\_answers:U07 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（d7cbecc9e78c） | — |
| catalog\_answers:U08 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（3ba34694584b） | — |
| catalog\_answers:U09 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（f73a3335eadb） | — |
| catalog\_answers:U10 | 修正を求める（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（4f227902bc64） | F02（cnf の照合が AGENT\_AT と矛盾） |
| catalog\_answers:U11 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（0680e35a018c） | — |
| catalog\_answers:U12 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（5ef386648255） | — |
| catalog\_answers:U13 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（34c1d6af3625） | — |
| catalog\_answers:U14 | 修正を求める（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（c1b44943718e） | F14（log\_policy と食い違う） |
| catalog\_answers:U15 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（23966ce7fb3a） | — |
| catalog\_answers:U16 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（802791b1ae05） | — |
| catalog\_answers:U17 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（b18da96c80d1） | — |
| catalog\_answers:U18 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（2d7138d4ad00） | — |
| catalog\_answers:U19 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（f8c21c7af455） | — |
| catalog\_answers:U20 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（7b5f7ce289be） | — |
| catalog\_answers:U21 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（3154738d01ff） | — |
| catalog\_answers:U22 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（e82ba11b5faa） | — |
| catalog\_answers:U23 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（49887af8151c） | — |
| catalog\_answers:U24 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（3e93d7ee3a6c） | — |
| catalog\_answers:U25 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（7ebb6c002c0e） | — |
| catalog\_answers:U26 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（ad9a383f9438） | — |
| catalog\_answers:U27 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（dc76a2049deb） | — |
| catalog\_answers:U28 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（db232aeefb6a） | — |
| claims:C-acr | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（d732203cc436） | — |
| claims:C-act | 保留（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（99eb25540729） | F12（深さの数え方、専門家へ）・F13 |
| claims:C-aud | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（6165409433ff） | — |
| claims:C-authorization-details | 修正を求める（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（736f75fa199d） | F03・F07・F10・F13・F14・F15 |
| claims:C-azp | 修正を求める（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（fcc339285e37） | F26（RR2） |
| claims:C-client-id | 修正を求める（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（fbf2768b6b1a） | F05（act の無いトークンの許可の一覧） |
| claims:C-cnf | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（6bf93cbda653） | 照合の仕組みは妥当。証明書の更新は F24 |
| claims:C-email | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（ae5848f9c405） | — |
| claims:C-exp | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（5535342776ea） | revisit\_trigger が無い（F26 の抜き取り外） |
| claims:C-iat | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（3b84cf5927a9） | revisit\_trigger が無い（F26 の抜き取り外） |
| claims:C-iss | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（8ffe325752d1） | — |
| claims:C-jti | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（0992eed3312c） | revisit\_trigger が無い（F26 の抜き取り外） |
| claims:C-may-act | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（1e44c36989c1） | — |
| claims:C-nbf | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（1d1914b08d83） | — |
| claims:C-org-approval-id | 修正を求める（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（ab09efd672aa） | F26（RR2） |
| claims:C-org-task-id | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（2b2af546ebfc） | — |
| claims:C-roles | 修正を求める（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（c5ea2dd7d1ad） | F26（RR2） |
| claims:C-scope | 修正を求める（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（73f4595c74a9） | F26（代償） |
| claims:C-sub | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（466ec1eff55b） | ログのハッシュは F14 |
| claims:C-tenant | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（a0d758138f41） | — |
| claims:C-txn | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（195a2cc2caa1） | — |
| hops:H1 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（b0eae68b2f07） | to の名前は F22 |
| hops:H2 | 修正を求める（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（f8db20d92c90） | F02・F05（交換の規則と照合） |
| hops:H3 | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（e1189b538d01） | to の名前は F22 |
| issuance\_profile:at\_format | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（929e2ceb5822） | — |
| issuance\_profile:client\_auth | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（df502cd5feaf） | — |
| issuance\_profile:client\_type | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（f68b94344335） | — |
| issuance\_profile:conformance\_profile | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（48bec996e4b7） | — |
| issuance\_profile:grants | 保留（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（d028f0d7537e） | F11（STS の挙動は未実測、専門家へ） |
| issuance\_profile:request\_protection | 修正を求める（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（12c7ee72586a） | F04 |
| issuance\_profile:rt\_strategy | 修正を求める（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（ca55e66cbd3b） | F16（RR5） |
| issuance\_profile:sender\_constraint | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（96cdcebf380f） | — |
| issuance\_profile:tls\_termination | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（6287cc706f71） | — |
| token\_types:AGENT\_AT | 修正を求める（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（856fe91a85d7） | F04（同意が resource を束縛しない）・F17 |
| token\_types:AGENT\_RT | 保留（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（ac109c6e9c97） | F16・F21・F24 |
| token\_types:AUTHORIZATION\_CODE | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（cb2f24bc9ed7） | — |
| token\_types:CLIENT\_ASSERTION | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（cf144213ba16） | — |
| token\_types:DPOP\_PROOF | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（c8a289fc1043） | — |
| token\_types:ID\_JAG | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（63e2fb53d237） | — |
| token\_types:ID\_TOKEN | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（1bb85f61c440） | — |
| token\_types:INTERNAL\_TOKEN | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（6c507d27be4e） | — |
| token\_types:INTROSPECTION\_RESPONSE\_JWT | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（e8384c6e15fd） | — |
| token\_types:JARM\_RESPONSE | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（2994ef7bf866） | — |
| token\_types:JAR\_REQUEST\_OBJECT | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（031b9ea58ec3） | — |
| token\_types:JWT | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（b0bf798c142f） | — |
| token\_types:LOGOUT\_TOKEN | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（fd97de2037a3） | — |
| token\_types:PORTAL\_AT | 修正を求める（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（271c374b38e0） | F05（act の無いトークンの許可の一覧） |
| token\_types:SECURITY\_EVENT\_TOKEN | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（34bf0d17e87d） | — |
| token\_types:SESSION | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（2afb279494c8） | — |
| token\_types:STATUS\_LIST\_TOKEN | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（3aacf7d50c74） | — |
| token\_types:TOOL\_AT | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（d0410c2701be） | 寿命と交換は妥当。支払いの取り消しの遅れは請求書の API の側（F07） |
| token\_types:TXN\_TOKEN | 承認（LLM） | 2026-11-24T07:20:00+09:00 | 一致（記録のときのまま）（fb928f649dd3） | — |

計 114 行：承認 97・修正を求める 14・保留 3。再確認が要る 0・台帳に無い 0
