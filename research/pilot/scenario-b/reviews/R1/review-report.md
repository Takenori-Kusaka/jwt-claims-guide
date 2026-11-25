# レビューレポート：シナリオ B 社内業務システム（パイロット #9、Full、ブラインド）— R1

> 設計書のエディターのレビューモード（#50）が `review.yaml` から生成した。レビュアーの名前は自己申告で、本当の承認は GitHub の PR のレビューで行う。レビュアーは LLM で、人による点検は未実施。

## 1. 基本情報

| 項目 | 値 |
| --- | --- |
| 対象 | research/pilot/scenario-b（版 857320ccadd5f6022e9f71436c16df1ad1d1072d）。worktree agent-acb20059fb1493488 の research/pilot/scenario-b（ブラインド記入の設計書、Full）。読んだもの：design.md・claims.yaml・token\_types.yaml・hops.yaml・catalog\_answers.yaml・claim\_request\_\*.md と要求の概要 brief-B.md。author-log.md・templates/examples・casestudy・ほかのレビュアーの出力は読んでいない |
| Lite／Full | Full（設計書の判定）。README の 5 問のうち境界を越える・委任と交換（作り直し）・新しい発行者が Yes で、Full に合う |
| 実施した手順の段 | 0〜7 を行った。8（対応を確かめて閉じる）は書き手の対応の後で行うので未実施。段 4 の抜き取りは procedure.md の 5 件ではなく、tools/review\_record.py sample の 3 件（却下）と、手で選んだ採用 5 件・却下 2 件（レポートの補遺） |
| レビュアーと役割 | R1（LLM：Claude Opus 5.5（claude-opus-5-5）、Claude Code のサブエージェントのセッション 1 つ（パイロット #9 のレビュアー R1）。名前は自己申告）。1 名・LLM。役割の切り替え：攻撃者 → 受け手 → 発行者 → 運用 → 個人情報 → クライアント（2026-11-24 の同じセッション内。日を分けず、段 3 の No の別セッションでの読み直しはしていない）。独立レビュー：提出まで、ほかのレビュアーの記録を画面で隠した（画面で隠すだけで、review.yaml を開けば見える。守ったかは自己申告） |
| 実施日 | 2026-11-24 |
| 使った教材の版 | templates/review（レビューした時の版：perspectives.md 0.4.0、report\_template.md 0.4.0、問い 168 問）。templates/review の procedure.md・perspectives.md（168 問）・decision\_tree.md・contrasts（必要な表だけ）・escalation.md・rationale\_rubric.md（0.5.0）・report\_template.md |
| CI の結果 | claim\_lint error 0・warn 2・info 16（profile full）。設計書の 1. と一致。レビュー時に worktree の今の claim\_lint で再実行し、設計書の 1. と同じ件数（warn は L69 C-groups・L11 C-sub-unread）。render --check も OK |
| 抜き取りの結果 | 乱数の種「R1-pilot-B」（claims.yaml の却下の行 6 行から 3 行。sha256(種:行) の順）：C-cnf・C-cognito-custom-role・C-idp-department。3 件を採点、合格 2・不合格 1 |
| 問いの回答 | 全 168 問のうち 168 問に回答（未回答 0）。定義 Yes 53／No 3／該当なし 3。発行 Yes 6／No 3／該当なし 3。伝搬 Yes 20／No 1／該当なし 7。検証 Yes 11／No 1／該当なし 2。認可 Yes 11／No 0／該当なし 17。運用 Yes 13／No 9／該当なし 5。合計 Yes 114／No 17／該当なし 37 |

## 2. 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 出どころ | 種別 | 取り違えた問い（種別が目的と仕組みの不一致のとき） | 判定 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F01 | claims.yaml（行が無い）、C-sub.upstream\_issuer、hops H3〜H5 の validates、design.md 付録 D.6 の 5. | 入口が照合・判定に使う IdP のクレームに台帳の行が無い：Entra の tid・oid（利用者のキー、B10）、Okta の uid（B13・B14）と cid、Entra・Okta の scp、Cognito の token\_use（B17）と cognito:groups、Keycloak の realm\_access.roles、Entra の \_claim\_names・\_claim\_sources（B8・B9）、ver。どれも identifier\_properties・on\_missing・enforced\_at・受け手のスキーマが無く、L3・L7 などの検査も当たらない。C-sub の upstream\_issuer の文と hops の validates に出るだけ。行を足す（usage と、無いときに拒否すること） | Major | 観点 | 候補の漏れ | — | 採用 |
| F02 | token\_types.KC\_AT.aud・assumption、claims C-aud.assumption・rationale・enforced\_at、hops H2・H6 | 宛先の扱いが食い違う。KC\_AT の aud は \[orders, invoices\] で assumption も「aud（orders・invoices）を経路ごとに照合」とあるが、C-aud の assumption は「BFF はサービスごとに別の AT を取る（宛先 1 つ）」。入口の照合は「経路のサービスを含む」なので、両方の宛先を持つ Keycloak の AT は両方の経路で通り、B3 は BFF の取り方という宣言されていない前提に頼る。また C-aud の rationale は Auth0 の https://api.example.com を経路ごとの宛先の値として挙げるが、注文・請求書で同じ値で区別できない（Okta・Auth0・Cognito の B3 は scope と client\_id に頼っている）。目録の aud を 1 つにし、入口の照合を「aud が経路の宛先と一致し、ほかの宛先を含まない」にするか、scope で宛先を区別する前提を C-scope・目録に書く | Major | 観点 | 実装とのずれ | — | 採用 |
| F03 | token\_types.INTERNAL\_TOKEN.required\_claims、hops H7.custom\_claims、claim\_request\_employee\_id.md の問 14 | INTERNAL\_TOKEN の required\_claims に https://claims.example.com/employee\_id（と roles）があり、orders 宛て（H7）にも社員番号が要ることになる。claim\_request の問 14 と H7 は orders に社員番号を載せないと書く。そのまま実装すると orders がすべての内部トークンを拒むか、入口が orders にも社員番号を載せて最小化が崩れる。宛先ごとの必須を目録で分けられないなら、required\_claims から外して H8 の validates に書く | Minor | 観点 | 実装とのずれ | — | 採用 |
| F04 | token\_types.SET（却下）・INTROSPECTION\_JWT（却下）、claims C-iat.revisit\_trigger、design.md 12. の「IdP 側だけのログアウト」 | B12（ログアウト・セッションの失効の後に残ったトークンで経理台帳を読む）で、Keycloak 以外の IdP の側で起きたセッションの失効（管理者による失効、IdP 側のログアウト）は社員台帳のログアウトの時刻を進めず、BFF のセッションと RT も残る。経理台帳でも最悪で AT の受け入れの上限（Entra 630 秒）まで通る。SET・イントロスペクションを却下した代わりの社員台帳の問い合わせは、ポータル経由のログアウトしか知らない。12. に書いたが、要求の「直後」に対する見送りとして 3.1 に書き、見直しの条件と、経理台帳だけでも IdP に問い合わせる案（Okta・Auth0 のイントロスペクション、Entra の CAE）を比べる | Major | 観点 | 候補の漏れ | — | 採用 |
| F05 | design.md 12.、9.1 のライフサイクル表、claims C-groups・C-auth0-roles・C-roles の recompute\_trigger、token\_types KC\_AT.refresh | ロール・グループの剥奪の遅れ（330〜665 秒）と B19・B20 の扱いは、5 つの IdP がリフレッシュでグループ・ロール・フックを再計算する前提に依存するが、どの IdP も確かめた記録が無い（Keycloak の KC\_AT.refresh も前提）。12. には RT の再利用の検知・Entra の寿命・Okta の typ だけがある。再計算されない IdP では古さの上限が RT の寿命（36000 秒）になる。escalation の unverified-idp-behavior に回す（判定の理由：IdP の運用の担当に回し、実測か公式の文書で確かめるまで保留） | Major | 観点 | 理由の不備 | — | 保留 |
| F06 | token\_types.issuance\_profile.rt\_strategy（refs：RFC 9700 §4.14.2）、REFRESH\_TOKEN | 機密クライアント（BFF）の RT のローテーションの根拠に RFC 9700 §4.14.2 を引いているが、その節の要求（送信者制約かローテーション）は公開クライアントが対象。判断（ローテーションする）は害が無いが、理由が状況に当てはまらない（RR5、シナリオ A の A16 と同じ型） | Minor | 観点 | 理由の不備 | — | 採用 |
| F07 | claims C-department・C-employee-id・C-auth0-roles（prior\_art\_search が無い）、各 claim\_request の問 3 の出どころ | 3 つの claim\_request の問 3 は出どころを「台帳：registered\_ref・prior\_art\_search」とするが、台帳の 3 行に prior\_art\_search が無く、独自クレームの行は registered\_ref も無い。探した記録を台帳の列に書く | Minor | 観点 | 実装とのずれ | — | 採用 |
| F08 | hops H7・H8（upstream なし）、design.md 1. の L11（C-sub-unread）・L69（C-groups）、12. の「L16 と作り直し」 | lint の規則に合わない宣言を、規則に渡さずに残した：(1) H7・H8 に upstream を書かず、下流ほど絞る検査（L16）が作り直しのホップで走らない（hops.yaml は upstream に 1 つしか書けないため）。(2) L11（sub を載せて使わない）と L69（細かい権限の配列）の warn に行ごとの理由が無い（CONTRIBUTING の 2.）。(1) は規則の側の不足の候補として #6 に渡し、(2) は抑止の理由を書くか、宣言を直す | Minor | 観点 | 実装とのずれ | — | 採用 |
| F09 | catalog\_answers U21 のメモ、claims C-groups.on\_revoke | Graph で解決したグループを「利用者ごとに AT の残りの寿命まで」キャッシュする。上限は 630 秒で volatility 900 の中だが、キャッシュの寿命を AT の期限から決めている（観点書が No とする型）。キャッシュの寿命を独立の値（例：60 秒）にし、9.1 に書く | Minor | 観点 | 理由の不備 | — | 採用 |
| F10 | token\_types 各行の log\_policy、design.md 付録 D.5 の 7.、6. の UC2 q-via | ログに記録する HTTP ヘッダーの許可リスト、障害調査の資料（HAR）からトークンを除く手順が無い。また入口のログ（IdP の iss・jti）と invoices のログ（内部トークンの jti）を結ぶキー（入口が内部トークンの jti を IdP の jti と並べて残す、など）が無く、経理台帳の操作を IdP のトークンまで辿れるかが書いていない | Minor | 観点 | 候補の漏れ | — | 採用 |
| F11 | claims C-cognito-custom-role.refs、token\_types ENTRA\_AT（寿命の理由） | 根拠の抜き取りで 3 件中 2 件が当てはまらない：C-cognito-custom-role は custom:\* の書き換えの根拠に slide:p03-cognito-token-use（token\_use の節）を引く（観点書は slide:p03-cognito-pre-token-hook を挙げる）。ENTRA\_AT の「Entra で設定できる最短に近い値（600 秒）」に出どころが無い | Minor | 観点 | 理由の不備 | — | 採用 |
| F12 | design.md 2.1 の「ポータルの BFF」の行、hops H3.validates、token\_types ENTRA\_AT | 2.1 は「Entra の azp（入口の設定で照合）」でポータルを確かめると書くが、H3 の validates に azp（または appid）の照合が無い（H2 は azp、H4 は cid、H5・H6 は client\_id を照合する）。同じテナントで api://orders に同意したほかのクライアントの AT を入口が受ける | Minor | 観点 | 実装とのずれ | — | 採用 |
| T1 | claims C-iat（enforced\_at：iat が社員台帳のログアウトの時刻より後）、hops H2〜H6、要求の概要の 6.（時刻は Keycloak 以外では仮想の時計） | ログアウトの判定は、5 つの IdP の時計で書かれた iat と、BFF の時計で書かれた社員台帳のログアウトの時刻を比べる。時計のずれ（目録で 30 秒を許す）と秒の丸めの分だけ、ログアウトの直前に出た AT が通るか、ログアウトの直後に取り直した正規の AT が拒まれる。要求の概要は Keycloak 以外の時刻が仮想の時計で進むと明記しており、試験ではずれが 30 秒を超えうる。「ログアウトは 0 秒」（9.1・付録 E の 3）は、この前提を書かないと支えられない（C-iat の理由の採点で RR2 否）。候補：比較に余裕（ずれ分）を持たせて代償を書く、iat でなく入口が最初に見た時刻か BFF のセッションの世代番号（sid）で止める、IdP ごとに時計のずれを測る | Major | テンプレート外 | 候補の漏れ | — | 採用 |
| T2 | design.md 2. の図と記入欄、7. のシーケンス図（B-&gt;&gt;D）、hops（無い）、catalog\_answers U06・U15、claims C-iat.assumption | BFF（ログアウト・Back-Channel Logout）と管理者（U15）が社員台帳のログアウトの時刻を書くが、この書き込みの経路がホップにも範囲の図にも無い（H10・H11 は読み取り専用）。人事の権威ある台帳にポータルが書く権限、書き込みの認証、書けなかったときの振る舞い（書けないとログアウトが効かず B12 が通る。閉じる側に倒すか）、BFF がどの鍵で利用者を決めるか（ID トークンの sub は Okta ではログイン名、Entra ではペアワイズ）が書いていない。ホップを足し、失敗時は BFF がセッションを残さずエラーにする、などを決める | Major | カタログ外の質問 | 候補の漏れ | — | 採用 |
| T3 | design.md 3.1 の「ヘッダーの除去」、9.3 の移行の手順、12. の「移行の間の守り」 | 移行の間（新しい入口を並行させ、全サービスが内部トークンだけを受けるまで）は B4〜B7 を防げないと書いたが、移行の前からすぐ取れる守り（現状の入口で X-User-Role とその変種を正規化して捨てる、アンダースコアのヘッダーを拒む、同名のヘッダーの重複を拒む、サービスへの直接の経路をネットワークで閉じる）を検討していない。要求は B4〜B7 を防ぐことを求めており、移行の期間の長さも書いていない | Major | テンプレート外 | 候補の漏れ | — | 採用 |
| T4 | claims C-department.absent\_semantics（部署の無い社員（契約社員など））、要求の概要の 3.（社内文書は営業・経理の社員）と B15 | B15（フックが打ち切られ部署なしで出たトークンで契約社員が社内文書を読む）の守りは、社員台帳で契約社員に部署が無いという前提に依存する。雇用の区分（社員・契約社員）を台帳にも内部トークンにも持たないので、社員台帳で営業部に属する契約社員は社内文書を読める。要求の「営業部門または経理部門の社員」が契約社員を含むかを確かめ、含まないなら雇用の区分を社員台帳から引いて判断に入れる（判定の理由：要求の解釈（契約社員を含むか）を要求の持ち主に確かめるまで保留） | Major | テンプレート外 | 候補の漏れ | — | 保留 |
| T5 | token\_types.INTERNAL\_TOKEN（assumption：署名鍵は入口だけが持つ、signing\_key\_scope: shared、key\_rotation） | 内部トークンの署名鍵は、全サービスに任意の sub・roles・社員番号を名乗らせられる唯一の信頼の根だが、保管の場所（KMS・HSM）、取り出せる者、漏えい時の失効（JWKS からの即時の削除と全サービスのキャッシュ 300 秒）が書いていない。入口が複数台なら鍵の配布も要る | Major | テンプレート外 | 候補の漏れ | — | 採用 |
| T6 | claims C-jti.enforced\_at（invoices が 35 秒の間 1 回だけ受ける）、hops H8 | 経理台帳の jti の 1 回だけの受け入れは、invoices が複数台・再起動のとき、受けた jti の記録を共有しないと効かない。記録の置き場所（共有のキャッシュ）と、その障害のときに拒むか通すかが書いていない | Minor | テンプレート外 | 候補の漏れ | — | 採用 |
| T7 | design.md 8. の矢印の表・9.2・9.3・10. の生成の表（https://claims.example.com/.roles など）、token\_types INTERNAL\_TOKEN.required\_claims と付録 D.2（https://claims.example.com/roles） | 名前空間つきのクレームの名前が、生成の表では「https://claims.example.com/.department」（. が入る）、目録の required\_claims と D.2 では「https://claims.example.com/department」と 2 通りに出る。Auth0 の Action や入口の実装者が生成の表を写すと名前がずれ、ロールが空になる（拒否の側に倒れるが正規の要求が落ちる）。tools/claim\_lint の render は flat\_prefix でも名前空間と名前を . でつなぎ、drift.py はつながない。lint・render に戻す | Minor | テンプレート外 | 実装とのずれ | — | 採用 |
| T8 | token\_types GRAPH\_AT（GroupMember.Read.All）・ENTRA\_AT（ver=2.0）、hops H9、claims C-groups | Graph による超過の解決の前提が確かめていない：(1) トークンの \_claim\_sources の URL（古い graph.windows.net を指すことがある）をたどらず、固定の Graph の端点を呼ぶこと、(2) GroupMember.Read.All のアプリの権限で利用者の所属（memberOf・checkMemberGroups）を引けるか、(3) API のアプリ登録で v2 の AT（accessTokenAcceptedVersion=2）を出す設定にすること（v1 なら iss が sts.windows.net になり B9 も拒む）（判定の理由：Microsoft の公式の文書か実測で確かめるまで保留（IdP の運用の担当）） | Minor | テンプレート外 | 前提の誤り | — | 保留 |
| T9 | hops H2〜H6 の forwarded\_headers（X-User-Role だけ）、claim\_request\_employee\_id.md・department.md の問 17 | claim\_request は X-Employee-Id・X-Department のような利用者の属性のヘッダーも外から受けないと書くが、hops の forwarded\_headers・strip\_inbound は X-User-Role だけ。現状の入口がほかの ID 系のヘッダー（X-User-Id、X-Forwarded-User など）を写しているかも調べていない。除去の対象を名前の列挙でなく接頭辞か許可リストで書く | Minor | テンプレート外 | 実装とのずれ | — | 採用 |
| T10 | token\_types LOGOUT\_TOKEN、claims C-events・C-sid | BFF のログアウトトークンの検証に、nonce を含むトークンを拒むこと（OpenID Connect Back-Channel Logout 1.0 の検証の手順）と、sub か sid の少なくとも一方が要ることが台帳に無い。ID トークンをログアウトトークンとして受けない守りが events だけになる | Minor | テンプレート外 | 候補の漏れ | — | 採用 |

## 3. 対応の一覧

| 指摘 ID | 担当 | 期限 | 状態 | 対応の PR・コミット |
| --- | --- | --- | --- | --- |
| F01 | — | — | 未着手 | — |
| F02 | — | — | 未着手 | — |
| F03 | — | — | 未着手 | — |
| F04 | — | — | 未着手 | — |
| F05 | — | — | 未着手 | — |
| F06 | — | — | 未着手 | — |
| F07 | — | — | 未着手 | — |
| F08 | — | — | 未着手 | — |
| F09 | — | — | 未着手 | — |
| F10 | — | — | 未着手 | — |
| F11 | — | — | 未着手 | — |
| F12 | — | — | 未着手 | — |
| T1 | — | — | 未着手 | — |
| T2 | — | — | 未着手 | — |
| T3 | — | — | 未着手 | — |
| T4 | — | — | 未着手 | — |
| T5 | — | — | 未着手 | — |
| T6 | — | — | 未着手 | — |
| T7 | — | — | 未着手 | — |
| T8 | — | — | 未着手 | — |
| T9 | — | — | 未着手 | — |
| T10 | — | — | 未着手 | — |

## 4. 専門家に回した項目

| 基準の ID（escalation.md） | 行・欄 | 回した先 | 期限 | 結論 |
| --- | --- | --- | --- | --- |
| unverified-idp-behavior | design.md 12.（RT の再利用の検知・Entra の寿命・IdP 側のログアウト）、9.1、F05・F04・T8 | IdP の運用の担当（5 つの IdP ごと） | 設計書の承認の前 | 未定（保留） |

当てはまらなかった基準：draft-spec・custom-crypto・delegation-depth・cross-tenant-exchange・baseline-unmet・jwe-key-management・regulated-data・new-token-type

## 5. カタログ・観点書・対応表に戻す事項

| 戻す先 | 中身 | 指摘 ID | issue・PR |
| --- | --- | --- | --- |
| lint・実行テスト（tools/claim\_lint、#6） | render が flat\_prefix の名前を「名前空間 + . + 名前」で表示し、drift.py・required\_claims の書き方（名前空間 + 名前）と食い違う | T7 | — |
| lint・実行テスト（tools/claim\_lint、#6） | 作り直しのホップ（reissue）に上流が複数あるとき upstream を 1 つしか書けず、L16 が走らない。目録の required\_claims をホップ（宛先）ごとに分けられず、custom\_claims との食い違いを検査しない | F08・F03 | — |
| 観点書（templates/review/perspectives.md） | 問いの候補：iat・時刻の比較で失効を判定するとき、比べる 2 つの時計（IdP と自組織）のずれの前提を書いたか。鮮度の情報源（社員台帳など）に書き込む者と経路をホップに書いたか。移行の期間の旧経路の守り。入口が作るトークンの署名鍵の保管。1 回だけの受け入れの記録の共有 | T1・T2・T3・T5・T6 | — |
| カタログ（templates/catalog/） | 利用のイベントの候補：RP・管理者が、受け手の鮮度の情報源（ログアウトの時刻・停止の状態）を書き込む | T2 | — |
| 観点書（templates/review/procedure.md） | 段 4 は抜き取りを採用・却下から各 5 件とするが、tools/review\_record.py sample と review.yaml の sampling は却下の 2〜3 件だけで、採用の行の採点を記録する欄が無い | — | — |

## 6. 理由の採点（抜き取り）

| 行の ID | 列 | RR1 | RR2 | RR3 | RR4 | RR5 | RR6 | RR7 | 合否 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C-cnf | rationale | 満 | 満 | 満 | 満 | 満 | 満 | 満 | 合格 |
| C-cognito-custom-role | rationale | 満 | 対象外 | 満 | 否 | 満 | 満 | 満 | 不合格 |
| C-idp-department | rationale | 満 | 満 | 満 | 満 | 満 | 満 | 満 | 合格 |

- C-cnf：要求の概要の 7. の 5（B23 は防がない場合に見直し条件を書く）に対応。q-holder を「不要」とし、見直しの条件 3 つ。RR4 は引用の名前と主張の対応だけを見た（RFC は開いていない）
- C-cognito-custom-role：B18 に対応。禁止の行なので崩れる条件は要らない（規則の出どころ p04-split-by-writer）。RR4：p03-cognito-token-use は token\_use の節で、custom 属性を本人が書けることを述べない（F11）
- C-idp-department：B11・B15・B18 と要求の概要の 7. の 6 に対応。代わり C-department、前提と崩れる条件あり

## 7. 点検状況

人による点検は未実施。LLM によるレビューで、人による検証ではない（templates/CONTRIBUTING.md の 3.）

人による点検は未実施（このレビューは LLM のセッションのもの。人のレビュアーの採否は未了）。

レビュアーの名前は自己申告です（エディターにはログインが無い）。本当の承認は GitHub の PR のレビューで行います。

## 8. 問いごとの回答

| 段 | 問い ID | 回答 | 理由（1 行） |
| --- | --- | --- | --- |
| 1. 定義 | dc-01 | Yes | C-department volatility 60 &gt; 受け入れ 35、C-groups 900 &gt; 630、C-roles 900 &gt; 665。9.2 の生成の表に「超える」が無い |
| 1. 定義 | dc-02 | No | C-department・C-employee-id・C-auth0-roles に prior\_art\_search が無い（claim\_request の問 3 は「台帳：prior\_art\_search」を出どころにしている）。F07 |
| 1. 定義 | dc-03 | Yes | namespaces に https://claims.example.com/ を宣言。claim\_request の問 4 に予約名との照合あり（名前の表記の食い違いは T7） |
| 1. 定義 | dc-04 | Yes | 受け手は各 1 つで consumer\_access\_path に token\_library（JSON のキーで読む）と書いてある |
| 1. 定義 | dc-05 | Yes | C-employee-id は数字だけの string（pattern）。数値の C-auth0-employee-number は却下 |
| 1. 定義 | dc-06 | Yes | roles・groups は array、scope は space\_delimited（標準） |
| 1. 定義 | dc-07 | Yes | 採用の行のすべてに absent\_semantics と on\_missing。欠落で既定値を使わない（B15・B20） |
| 1. 定義 | dc-08 | Yes | C-sub・C-employee-id は value\_normalization あり。C-department・C-roles は台帳の列が無く、claim\_request の問 10 で完全一致を書いた（列で書くとよい） |
| 1. 定義 | dc-09 | Yes | 採用の行の照合キーは組織の UUID・社員番号。ただし入口が照合に使う oid・tid・uid は台帳の行が無い（q-identifier-choice・F01） |
| 1. 定義 | dc-10 | Yes | authoritative\_writer と provenance あり。custom:\*・user\_metadata・フックの値を認可に使わない |
| 1. 定義 | dc-11 | Yes | max\_bytes・max\_items・overflow\_strategy あり（groups は 200 で問い合わせに切り替える） |
| 1. 定義 | dc-12 | Yes | iss は段階ごとに 1 つ。認可のクレームの欠落は「権限なし」に倒す（拒否側）。内部トークンの required\_claims の食い違いは F03 |
| 1. 定義 | dc-gate | Yes | 採用の独自クレームは active で、dc-01〜12 に空欄は無い（dc-02 の記録の不備は Minor） |
| 1. 定義 | pa-01 | Yes | 3 件とも受け手（orders・invoices・入口）と判断を書き、usage と一致 |
| 1. 定義 | pa-02 | Yes | department は 60 秒の許容と経理台帳の都度の引き直し、roles は 330 秒、employee\_id は never |
| 1. 定義 | pa-03 | No | 探した記録の本文はあるが、出どころに挙げた台帳の prior\_art\_search が無い。F07 |
| 1. 定義 | pa-04 | Yes | 組織の名前空間で、Auth0 の名前空間の規則・Keycloak・Cognito の予約名との衝突を確かめた |
| 1. 定義 | pa-05 | Yes | 受け手は検証部品で JSON のキーとして読み、CEL・ヘッダー・RLS に写さないと書いた |
| 1. 定義 | pa-06 | Yes | flat\_prefix で台帳の namespace・shape と一致 |
| 1. 定義 | pa-07 | Yes | string／string の配列。区切り文字列なし |
| 1. 定義 | pa-08 | Yes | 社員番号は数字の文字列、部署はコードの文字列 |
| 1. 定義 | pa-09 | Yes | absent\_semantics・on\_missing と一致 |
| 1. 定義 | pa-10 | Yes | 完全一致、employee\_id は trim のみ |
| 1. 定義 | pa-11 | Yes | 書き手は入口（社員台帳）と Auth0 の Action（管理者）で、本人の値を使わない |
| 1. 定義 | pa-12 | Yes | コード・社員番号が ID。表示名は運ばない |
| 1. 定義 | pa-13 | Yes | 上限と、超えたら発行を失敗させる（Action・入口） |
| 1. 定義 | pa-14 | Yes | department は H7 だけ、employee\_id は H8 だけと書いた（ただし目録の required\_claims と食い違う。F03） |
| 1. 定義 | pa-15 | Yes | 入口だけ（Auth0 の roles は Auth0 のテナントだけ） |
| 1. 定義 | pa-16 | Yes | 組織共通の検証部品と入口の正規化の部品 |
| 1. 定義 | pa-17 | Yes | ヘッダーに移さない。X-User-Role の変種を捨てる（ほかの ID 系のヘッダーは hops に無い。T3・T9 の範囲） |
| 1. 定義 | pa-18 | Yes | 社員台帳を引けなければ 503 で拒む |
| 1. 定義 | pa-19 | Yes | 無視すれば許可が増えない向き |
| 1. 定義 | pa-20 | Yes | log\_policy・pii\_category と一致（employee\_id はハッシュ、department・roles は値） |
| 1. 定義 | pa-21 | 該当なし | 委任が無い（act を使わない） |
| 1. 定義 | pa-22 | Yes | consumers は設計書の受け手と一致 |
| 1. 定義 | pa-23 | Yes | 受け手が先の順を書いた |
| 1. 定義 | pa-24 | Yes | 並行発行の期間を書いた |
| 1. 定義 | pa-25 | Yes | 入口の試験と受け手の契約テストを書いた |
| 1. 定義 | pa-gate | Yes | 3 件とも固有の回答で、写しではない |
| 1. 定義 | pa-trace | Yes | 「対象：」が台帳の ID を指し、rationale と同じことを言う |
| 1. 定義 | q-registered-synonym | Yes | C-auth0-roles（Auth0 の Action が書く）と C-roles（入口が書く）は not\_meaning で区別した |
| 1. 定義 | q-reuse-standard-structure | Yes | cnf・txn などに当たる独自クレームが無い |
| 1. 定義 | q-auth-context-semantics | Yes | iat は発行時刻としてログアウトの比較に使い、auth\_time の代わりにしない（not\_meaning）。時計の前提は T1 |
| 1. 定義 | q-scope-semantics | Yes | scope は経路の確認で、利用者の権限と読まない（not\_meaning） |
| 1. 定義 | q-value-vocabulary | Yes | value\_vocabulary（admins・editor・viewer・approver）と upstream\_issuer の写し方あり。写しの表の中身（どのグループがどのロールか）は設計書に無い |
| 1. 定義 | q-role-explosion | Yes | ロール 4 種。部署は別のクレーム |
| 1. 定義 | q-identifier-choice | No | 照合キーの Entra の tid＋oid・Okta の uid が台帳の行として無く、identifier\_properties・on\_missing・enforced\_at を宣言していない（C-sub の upstream\_issuer の文に出るだけ）。F01 |
| 1. 定義 | ap-1-6 | Yes | email・upn・Okta の sub を照合に使わない |
| 1. 定義 | q-pairwise-external | 該当なし | 外部の受け手に利用者のクレームを出さない（GRAPH\_AT は利用者を載せない）。全種別 public |
| 1. 定義 | q-pairwise-unguessable | 該当なし | ペアワイズを使わない |
| 1. 定義 | ap-2-1 | Yes | groups は上限 200 で Graph に切り替え、組織のロールは 4 種（L69 の warn の扱いは F08） |
| 1. 定義 | ap-2-2 | Yes | 部署は都度の引き直し、ロールは 665 秒を許容として 3.1 に見送りとして書いた |
| 1. 定義 | ap-2-3 | Yes | schemas/\*.consumer.schema.json がある |
| 1. 定義 | ap-2-4 | Yes | 独自クレームは https://claims.example.com/ の下 |
| 1. 定義 | q-payload-readable | Yes | confidential\_from が全行で空 |
| 1. 定義 | q-confidential-reaches-reader | Yes | 読まれてはいけないクレームを宣言していない（3.1 の JWE の見送りに理由あり） |
| 1. 定義 | q-no-secret-or-raw-pii | Yes | 秘密・生年月日などを載せない |
| 1. 定義 | q-derived-value | Yes | 部署・社員番号は値そのものが照合に要る |
| 1. 定義 | q-baseline-kept | Yes | 3.2 で全基準を満たすと書いた（Cognito の aud は client\_id と token\_use で代替） |
| 2. 発行 | q-single-issuer | Yes | 段階ごとに 1 つ（IdP → 入口の作り直し）。サービスは作り直さない |
| 2. 発行 | q-hook-failure | Yes | Okta のフックの値・Cognito の発行前のフックに頼らず、欠落は権限なしに倒す（B15・B19） |
| 2. 発行 | q-size-limit | Yes | R8 の計算あり。入口の nginx を 32 KiB にした |
| 2. 発行 | ap-1-7 | Yes | custom:\*・user\_metadata を使わない |
| 2. 発行 | q-hook-adds-raw-pii | Yes | Auth0 の Action はロールだけ |
| 2. 発行 | q-minimal-per-recipient | No | 設計の意図は H7 に部署、H8 に社員番号だが、INTERNAL\_TOKEN の required\_claims に employee\_id が入り、orders 宛てにも要ることになる。F03 |
| 2. 発行 | q-rar-per-audience | 該当なし | authorization\_details を使わない |
| 2. 発行 | q-agent-own-identity | 該当なし | エージェントが無い |
| 2. 発行 | q-agent-delegation-claims | 該当なし | 代理で動くトークンが無い |
| 2. 発行 | q-idp-capability-verified | No | 12. に、Entra の寿命のポリシー・RT の再利用の検知・Okta の typ・Cognito の client\_secret を確かめていないとある。リフレッシュでの再計算（Entra・Okta・Cognito・Auth0）、Okta の AT の uid、Graph の権限は 12. にも出どころにも無い。F05・T8 |
| 2. 発行 | q-variant-comparison | Yes | 送信者制約・JWE の見送りに、開く攻撃（B23）とサイズ（32 KiB）と費用を書いた |
| 2. 発行 | q-outside-catalog | No | outside\_enumeration の 4 件のほかに、BFF・管理者が社員台帳のログアウトの時刻を書く経路（U06・U15）が図にもホップにも無い。T2 |
| 3. 伝搬 | cf-01 | Yes | 段階ごとの書き手あり。フックの値を使わない |
| 3. 伝搬 | cf-02 | Yes | 欠落で権限なし |
| 3. 伝搬 | cf-03 | Yes | 入口で内部トークンに作り直す（H7・H8 は reissue） |
| 3. 伝搬 | cf-04 | Yes | ホップごとに token\_type が替わる |
| 3. 伝搬 | cf-05 | Yes | H7・H8 は upstream が無く機械で見ていないが、手で 30 ＜ 300 秒、宛先 1 つを確かめた（F08） |
| 3. 伝搬 | cf-06 | 該当なし | Txn-Token を使わない |
| 3. 伝搬 | cf-07 | Yes | H7・H8 でサービスも検証する。H10〜H13 は DB 接続 |
| 3. 伝搬 | cf-08 | Yes | X-User-Role の変種を strip\_inbound（ほかの ID 系のヘッダーは T9 に含めた） |
| 3. 伝搬 | cf-09 | 該当なし | アクセス元の文脈を判断に使わない（要求に無い） |
| 3. 伝搬 | cf-10 | Yes | jti だけ、sub はハッシュ。act・txn は無い |
| 3. 伝搬 | q-hop-narrowing | Yes | 手で確かめた：宛先 1 つ、scope は内部トークンに載せない |
| 3. 伝搬 | q-hop-lifetime | Yes | 30 秒 ≤ 上流 300／600 秒（upstream を書かないので機械で見ていない。F08） |
| 3. 伝搬 | q-single-aud-resource | No | KC\_AT の aud が \[orders, invoices\]。C-aud の assumption（宛先 1 つ）と食い違い、入口の照合は「含む」。resource indicators は使わない。F02 |
| 3. 伝搬 | ap-2-6 | Yes | サービスは受け取ったトークンを他へ渡さない（サービス間の呼び出しが無い） |
| 3. 伝搬 | q-no-passthrough | Yes | 入口が作り直す規則を書いた |
| 3. 伝搬 | ap-2-5 | Yes | クレームをヘッダーに写さない |
| 3. 伝搬 | q-unverified-claim-extraction | Yes | 署名の検証の後に取り出す（D.3 の 1.） |
| 3. 伝搬 | q-gateway-bypass-path | Yes | 入口を通らない経路を 2. に書き、内部トークンと mTLS で止める（B7） |
| 3. 伝搬 | q-step-up-path-coverage | 該当なし | 追加認証を使わない（付録 B） |
| 3. 伝搬 | q-txn-scope-fixed | 該当なし | Txn-Token を使わない |
| 3. 伝搬 | q-txn-required-claims | 該当なし | Txn-Token を使わない |
| 3. 伝搬 | q-claim-earliest-hop | Yes | 部署・社員番号は入口で初めて分かる（社員台帳） |
| 3. 伝搬 | ap-2-9 | Yes | 内部トークンは ES256 の署名・30 秒・jti・ログあり（鍵の保管は T5） |
| 3. 伝搬 | q-internal-delegation-token | Yes | 目録の行に署名・寿命・失効・ログがある。テナントは無い |
| 3. 伝搬 | ap-2-7 | 該当なし | エージェントが無い |
| 3. 伝搬 | q-delegation-depth-and-revocation | 該当なし | 委任が無い |
| 3. 伝搬 | q-idp-diff-absorbed | Yes | 入口で吸収し、サービスは組織の名前空間と内部トークンだけを読む |
| 3. 伝搬 | q-token-not-in-url | Yes | URL に載るのは認可コードだけ |
| 4. 検証 | q-shared-validator | Yes | 組織共通の検証部品（版は未定と D.3 の 10. に書いた） |
| 4. 検証 | ap-1-1 | Yes | alg\_allowlist（RS256・ES256） |
| 4. 検証 | ap-1-2 | Yes | 全ホップで署名の検証の後に読む |
| 4. 検証 | q-validate-before-read | Yes | D.3 の 1. の順 |
| 4. 検証 | ap-1-3 | Yes | aud を必須。Cognito は aud が無いので client\_id と token\_use を代わりに照合（3.2 に記録） |
| 4. 検証 | ap-1-4 | Yes | Entra は自社の tid の iss だけ（B10） |
| 4. 検証 | ap-1-5 | Yes | key\_source は各 iss の jwks\_uri、jku・x5u・jwk を拒む |
| 4. 検証 | ap-1-8 | Yes | exp 必須、ずれ 30 秒（内部 5 秒） |
| 4. 検証 | q-typ-distinguishes | Yes | KC・Entra は aud・azp・scp、Cognito は token\_use、Auth0 は at+jwt、内部は internal+jwt（Okta の typ は推測と 12. に） |
| 4. 検証 | q-required-rejected | No | INTERNAL\_TOKEN の required\_claims に employee\_id があるが H7（orders）の宛ての内部トークンには載せない設計。どちらかが誤り。F03 |
| 4. 検証 | q-no-unverified-passthrough-mode | Yes | 代替：D.3 に library-config の「未検証の値を流すモード」の行が無いが、claim\_request の問 18 と D.3 の 10. で無いと書いた（行が無いこと自体は F08 に含めず Minor の記述の不足） |
| 4. 検証 | q-consumer-expression | Yes | 完全一致、欠落は拒否側 |
| 4. 検証 | q-nested-jwt-both-layers | 該当なし | JWE を使わない |
| 4. 検証 | q-unwrapped-value-authz | 該当なし | 署名の外の値（ヘッダー・DB のセッション変数）で認可しない |
| 5. 認可 | q-object-level-authz | Yes | orders は注文の持ち主と sub、invoices は明細の社員番号と照合（404） |
| 5. 認可 | q-tenant-data-match | 該当なし | テナントが無い |
| 5. 認可 | q-writer-distinguished | Yes | IdP の部署を却下し、社員台帳の値だけで認可 |
| 5. 認可 | q-validity-not-authz | Yes | 操作ごとにロール・部署・本人で判断 |
| 5. 認可 | q-original-principal | Yes | 内部トークンの sub は元の利用者 |
| 5. 認可 | q-authorize-service-and-user | Yes | メッシュの mTLS で入口、内部トークンで利用者 |
| 5. 認可 | q-scope-and-role | Yes | scope は入口、ロールはサービスで確かめる（内部トークンに scope を載せない） |
| 5. 認可 | q-access-context-from-pep | 該当なし | アクセス元の文脈を判断に使わない |
| 5. 認可 | q-step-up-by-rs | 該当なし | 要求に追加認証が無く、付録 B と I12 に見送りの条件を書いた |
| 5. 認可 | q-approval-from-as | 該当なし | 承認は請求書の画面で approver のロールの本人が行う（エージェント・CIBA が無い） |
| 5. 認可 | q-cross-tenant-identity | Yes | IdP をまたぐ名寄せは人事の手続きの名寄せの表で、email で突き合わせない |
| 5. 認可 | q-operator-act | 該当なし | 運用者の代理操作が無い（Impersonate を与えない） |
| 5. 認可 | q-break-glass | 該当なし | 業務システムの特権トークンを作らない（2.2） |
| 5. 認可 | cd-01 | 該当なし | DB の文脈を設定しない（M\_data\_layer を使わない） |
| 5. 認可 | cd-02 | 該当なし | SET LOCAL を使わない |
| 5. 認可 | cd-03 | 該当なし | SQL Server の文脈を使わない |
| 5. 認可 | cd-04 | Yes | 認可に本人が書ける属性を使わない |
| 5. 認可 | cd-05 | 該当なし | DB のロールを選ぶクレームが無い |
| 5. 認可 | cd-06 | 該当なし | RLS を使わない |
| 5. 認可 | cd-07 | 該当なし | DB の利用者はサービスの利用者で、利用者ごとの DB のユーザーが無い |
| 5. 認可 | cd-08 | Yes | 接続の最大寿命 3600 秒、剥奪は問い合わせの結果で効く |
| 5. 認可 | cd-09 | Yes | 問い合わせの条件に sub・社員番号を入れ、監査はサービスのログ |
| 5. 認可 | cd-10 | Yes | sub・社員番号が無い内部トークンは拒む |
| 5. 認可 | cd-11 | 該当なし | データ層の設定は接続の寿命だけ（文脈・RLS を使わない） |
| 5. 認可 | q-db-context-writers | 該当なし | DB の文脈を使わない |
| 5. 認可 | q-sql-tenant-predicate | 該当なし | テナントが無い（sub の条件は q-object-level-authz で見た） |
| 5. 認可 | q-db-context-parameterized | 該当なし | DB の文脈を使わない |
| 5. 認可 | q-ddm-rls-only | 該当なし | DDM・RLS を使わない |
| 6. 運用 | q-four-lifetimes-written | Yes | 9.1〜9.3 と DB 接続の層に分けて書いた |
| 6. 運用 | q-lifetime-rationale | Yes | 5.1 に組織の上限と例外の手順、付録 E の 4 に理由 |
| 6. 運用 | q-session-rt-bounds | Yes | 無操作 1800・最大 36000 ≤ 24 時間 |
| 6. 運用 | q-rt-policy-by-client | No | 機密の BFF の RT のローテーションの根拠に RFC 9700 §4.14.2（公開クライアントへの要求）を引いた（RR5）。F06 |
| 6. 運用 | q-freshness-mitigation | Yes | 「超える」行は無く、部署（経理台帳）とログアウトに都度の問い合わせ |
| 6. 運用 | q-refresh-reevaluated | No | ロール・グループの剥奪 330〜665 秒はリフレッシュでの再計算が前提だが、5 つの IdP のどれも確かめた記録が無い（Keycloak も「前提」）。F05 |
| 6. 運用 | q-revocation-delivery | No | Keycloak 以外の IdP 側のログアウト・セッションの失効は届かない（12.）。SET・イントロスペクションを却下し、代わりの社員台帳はポータル経由のログアウトしか知らない。経理台帳でも最悪 630 秒。F04 |
| 6. 運用 | q-external-user-deprovision | Yes | 停止・退職は社員台帳を要求ごとに引いて 0 秒（社員台帳が権威） |
| 6. 運用 | q-relies-on-at-expiry | No | U21：Graph の結果を「AT の残りの寿命まで」キャッシュする。ロールの剥奪も AT の期限に頼る（3.1 で見送りとした）。F09 |
| 6. 運用 | q-long-running | 該当なし | 非同期の処理が無い |
| 6. 運用 | q-system-actor-no-fake-sub | Yes | GRAPH\_AT は入口自身で、利用者の sub を作らない |
| 6. 運用 | q-agent-short-lived-no-rt | 該当なし | エージェントが無い |
| 6. 運用 | q-copies-outlive | Yes | Graph のキャッシュ・JWKS・DB 接続の期限を書いた |
| 6. 運用 | q-deprecated-deadline | 該当なし | deprecated の行が無い |
| 6. 運用 | q-change-order | Yes | 9.3 に受け手が先の手順と X-User-Role からの移行 |
| 6. 運用 | q-key-rotation | Yes | JWKS・未知の kid の間隔・公開と廃止の順あり（鍵の保管は T5） |
| 6. 運用 | q-dependency-outage | Yes | 社員台帳・Graph・JWKS の障害の振る舞いを書いた（BFF が社員台帳に書けないときは T2） |
| 6. 運用 | ap-2-8 | Yes | jti だけ |
| 6. 運用 | q-token-logging | No | トークン全文を残さないとあるが、記録する HTTP ヘッダーの許可リストと、HAR・障害調査の資料からトークンを除く手順が無い。F10 |
| 6. 運用 | q-audit-log-protected | Yes | D.5 の 8.：情報システム部だけ、1 年 |
| 6. 運用 | q-audit-correlation | No | 入口のログ（IdP の iss・jti）と invoices のログ（内部トークンの jti）を結ぶキーを書いていない。F10 |
| 6. 運用 | q-trace-id-trust | 該当なし | txn・traceparent を監査に使わない |
| 6. 運用 | q-scope-elevation-logged | 該当なし | エージェントが無い |
| 6. 運用 | q-operational-metrics | Yes | 付録 A に 7 指標と持ち主・周期 |
| 6. 運用 | q-lint-workaround | No | H7・H8 の upstream を書かず、下流ほど絞る検査（L16）が走らない。12. に書いたが #6 に渡していない。L11・L69 の warn に行ごとの理由が無い。F08 |
| 6. 運用 | q-evidence-attribution | No | 抜き取り 3 件：C-cognito-custom-role の p03-cognito-token-use（token\_use の節で、custom 属性の書き換えを述べない）、ENTRA\_AT の「設定できる最短に近い値」（出どころなし）、C-groups の p03-entra-scp-roles-groups（当てはまる）。F11 |
| 6. 運用 | q-limit-consistency | No | KC\_AT の aud（2 つ）と C-aud の前提（1 つ）、INTERNAL\_TOKEN の required\_claims と H7、2.1 の Entra の azp と H3 の validates、名前空間の表記（/roles と /.roles）が食い違う。F02・F03・F12・T7 |

## 9. 行ごとの記録（エディターのレビューモード、#50。生成した時の台帳と比べた状態）

行の内容のハッシュ（RFC 8785 JCS の SHA-256、`tools/row_hash.py`）に結びつけた判定です。記録の後に行が変わると「再確認が要る」になります。ハッシュはその行の値だけを見ます（参照するトークン種別・ホップの行、25 問の回答、design.md の本文を変えても再確認にはなりません）。

| 行 | 判定 | 日時 | 今の行との対応 | コメント |
| --- | --- | --- | --- | --- |
| catalog\_answers:I01 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（14335e7ab23c） | — |
| catalog\_answers:I02 | 保留（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（17e265cb2531） | F05 |
| catalog\_answers:I03 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（71083306dc8a） | — |
| catalog\_answers:I04 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（0af93b980d90） | — |
| catalog\_answers:I05 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（d684a7bfe150） | — |
| catalog\_answers:I06 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（9bcd92149920） | — |
| catalog\_answers:I07 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（e5ad7e9e2a14） | — |
| catalog\_answers:I08 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（6d9f23f228b3） | — |
| catalog\_answers:I09 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（394b9129b54c） | — |
| catalog\_answers:I10 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（37e1d2098027） | — |
| catalog\_answers:I11 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（3f6625dbf39f） | — |
| catalog\_answers:I12 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（e5896744181c） | — |
| catalog\_answers:I13 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（77bebd222963） | — |
| catalog\_answers:I14 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（bbb1cfdf2fc1） | — |
| catalog\_answers:I15 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（22db3cd0b7b1） | — |
| catalog\_answers:I16 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（f8ad339b5dc9） | — |
| catalog\_answers:I17 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（3518cc8369b9） | — |
| catalog\_answers:I18 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（1ee4c6ebd147） | — |
| catalog\_answers:I19 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（05f58f94291c） | — |
| catalog\_answers:I20 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（9cc0263b6301） | — |
| catalog\_answers:I21 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（28781fa5b80f） | — |
| catalog\_answers:I22 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（2909a3aa5377） | — |
| catalog\_answers:I23 | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（d17fa072a9fa） | F04 |
| catalog\_answers:I24 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（4b42c46ba50e） | — |
| catalog\_answers:I25 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（509b0cf0a482） | — |
| catalog\_answers:I26 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（bfb4f143cb62） | — |
| catalog\_answers:I27 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（aecdd6cf160e） | — |
| catalog\_answers:I28 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（aec067f4a784） | — |
| catalog\_answers:I29 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（f1439e6b898b） | — |
| catalog\_answers:I30 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（3be6102b43ca） | — |
| catalog\_answers:I31 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（49ada9a399ab） | — |
| catalog\_answers:I32 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（1d3235c5d3ed） | — |
| catalog\_answers:I33 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（b4d097dbe77a） | — |
| catalog\_answers:I34 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（961bbbbca60c） | — |
| catalog\_answers:U01 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（6cd050222ee3） | — |
| catalog\_answers:U02 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（baa1a92a097f） | — |
| catalog\_answers:U03 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（570c537ea4a2） | — |
| catalog\_answers:U04 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（0f743711d5d5） | — |
| catalog\_answers:U05 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（6a29a9f17a48） | — |
| catalog\_answers:U06 | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（04b9c86a307b） | T2 |
| catalog\_answers:U07 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（cae6c2cf0153） | — |
| catalog\_answers:U08 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（14d295772c66） | — |
| catalog\_answers:U09 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（5307f87db2ba） | — |
| catalog\_answers:U10 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（1b510e02a05b） | — |
| catalog\_answers:U11 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（58102b76eea4） | — |
| catalog\_answers:U12 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（b527ca501814） | — |
| catalog\_answers:U13 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（9165f6932468） | — |
| catalog\_answers:U14 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（43116d9a4137） | — |
| catalog\_answers:U15 | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（18078993d68e） | T2 |
| catalog\_answers:U16 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（a42e6b717eea） | — |
| catalog\_answers:U17 | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（41b7665457d9） | F04 |
| catalog\_answers:U18 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（419b8011aeea） | — |
| catalog\_answers:U19 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（1d7f24f05f8d） | — |
| catalog\_answers:U20 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（9d69d3fef763） | — |
| catalog\_answers:U21 | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（33f3a147bfec） | F09 |
| catalog\_answers:U22 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（2836cb2ca816） | — |
| catalog\_answers:U23 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（b702925636fc） | — |
| catalog\_answers:U24 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（f2feac1ee158） | — |
| catalog\_answers:U25 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（eb108d898996） | — |
| catalog\_answers:U26 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（97000fbfa181） | — |
| catalog\_answers:U27 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（a54a5504ebf9） | — |
| catalog\_answers:U28 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（1c0cade17483） | — |
| claims:C-aud | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（4a8171179b6a） | F02 |
| claims:C-auth0-employee-number | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（d8381ce529db） | B22 |
| claims:C-auth0-plain-roles | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（c8c9effd43b0） | B20 の原因を除く |
| claims:C-auth0-roles | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（978f2163781b） | F07・T7 |
| claims:C-azp | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（151cfbd879ea） | — |
| claims:C-client-id | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（2abb07e7535a） | B16 を受ける根拠 |
| claims:C-cnf | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（b881ecd55bee） | B23 の見送り。見直しの条件あり（書き手の 12. は専門家に回すよう求めている） |
| claims:C-cognito-custom-role | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（ad58d96fcdfc） | F11：根拠の付け替え（判断は妥当） |
| claims:C-department | 保留（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（c35d253dfeeb） | T4：契約社員の扱いを要求の持ち主に確かめるまで |
| claims:C-email | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（cfd68be168c2） | 付録 E の 9 |
| claims:C-employee-id | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（07b80de7c5af） | F07・T7 |
| claims:C-events | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（8e20e4d720c2） | T10 |
| claims:C-exp | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（96e6963be2b2） | — |
| claims:C-groups | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（7e2ad16cb4f9） | F08（L69）・F09 |
| claims:C-iat | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（f5d07a42f623） | T1・T2：時計の前提と、ログアウトの時刻の書き手 |
| claims:C-idp-department | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（4f8724cea133） | B11・B15・B18 |
| claims:C-iss | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（9e234424cd06） | 5 つの IdP と入口の iss の完全一致。Entra は自社の tid だけ（B10） |
| claims:C-jti | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（d6f46850ae6f） | T6 |
| claims:C-nonce | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（8fe666c56c8f） | — |
| claims:C-roles | 保留（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（88d3bcdc427c） | F05：リフレッシュでの再計算を確かめるまで |
| claims:C-scope | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（1fe083b950ec） | F02 の直し方によっては前提を足す |
| claims:C-sid | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（17b95c809bfc） | — |
| claims:C-sub | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（2ae2c73da9e9） | F01：照合キーの tid・oid・uid に行が無い |
| claims:C-sub-unread | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（71bfaca5e25b） | F08：L11 の warn に理由が無い |
| hops:H1 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（a8105b8db7cf） | — |
| hops:H10 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（c47d97e890d1） | T2：BFF の書き込みの経路は別のホップとして足す |
| hops:H11 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（7538119156f9） | — |
| hops:H12 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（f37a768a1c05） | — |
| hops:H13 | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（5afec5e49d2d） | — |
| hops:H2 | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（9ec5601c4d15） | F02・T1・T9 |
| hops:H3 | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（1e59a5824373） | F12・T1・T9 |
| hops:H4 | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（79d665b74698） | T1・T9 |
| hops:H5 | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（a1df7f8f2370） | T1・T9 |
| hops:H6 | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（9fd3435223d8） | F02・T1・T9 |
| hops:H7 | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（1cde20c8bb73） | F03・F08・T3 |
| hops:H8 | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（0eb9bc4fa1f2） | F08・T3・T6 |
| hops:H9 | 保留（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（dda884631f07） | T8 |
| issuance\_profile:at\_format | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（449627a74530） | — |
| issuance\_profile:client\_auth | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（d9c3dea0e1b9） | — |
| issuance\_profile:client\_type | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（f91afed07f36） | — |
| issuance\_profile:conformance\_profile | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（1605db4ea675） | — |
| issuance\_profile:grants | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（aa730346c3df） | — |
| issuance\_profile:request\_protection | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（1495b5790be5） | — |
| issuance\_profile:rt\_strategy | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（4902f4e1744d） | — |
| issuance\_profile:sender\_constraint | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（a8b4a6dc126c） | — |
| token\_types:AUTH0\_AT | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（a9d9cfd04af8） | — |
| token\_types:AUTHORIZATION\_CODE | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（2ab8685d374c） | — |
| token\_types:BFF\_SESSION | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（665cbd72e672） | — |
| token\_types:CLIENT\_ASSERTION | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（5759815bdff3） | — |
| token\_types:COGNITO\_AT | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（3fcbfee7028e） | — |
| token\_types:DPOP\_PROOF | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（e4286f67c9c5） | — |
| token\_types:ENTRA\_AT | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（e08e7ba1588a） | F11・F12・T8 |
| token\_types:GRAPH\_AT | 保留（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（94dcae1673e2） | T8 |
| token\_types:IDP\_SESSION | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（ed1e92f58bd5） | — |
| token\_types:ID\_JAG | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（b13b8951f127） | — |
| token\_types:ID\_TOKEN | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（eb8cba0dae55） | — |
| token\_types:INTERNAL\_TOKEN | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（58d4af9deaf6） | F03・T5・F10 |
| token\_types:INTROSPECTION\_JWT | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（d612a03e766c） | — |
| token\_types:JARM\_RESPONSE | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（4f6774de3c6b） | — |
| token\_types:JAR\_REQUEST\_OBJECT | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（f36f1756fc7f） | — |
| token\_types:KC\_AT | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（c100bfbfabaa） | F02 |
| token\_types:LOGOUT\_TOKEN | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（0d8a9cf20c1c） | T10 |
| token\_types:OKTA\_AT | 保留（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（1c326387bba6） | typ が推測（12.）。F05 |
| token\_types:REFRESH\_TOKEN | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（71393c5f50c5） | F06。再利用の検知は F05 と同じく未確認 |
| token\_types:SET | 修正を求める（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（c9297d14b5ed） | F04：代わりの手段が IdP 側の失効に届かない |
| token\_types:STATUS\_LIST | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（d283e9049b34） | — |
| token\_types:TXN\_TOKEN | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（e3764cb5f844） | — |
| token\_types:WORKLOAD\_JWT | 承認（LLM） | 2026-11-24T07:18:00+09:00 | 一致（記録のときのまま）（82d57b062621） | — |

計 130 行：承認 96・修正を求める 28・保留 6。再確認が要る 0・台帳に無い 0

---

## 補遺（手で足した。review.yaml の欄に無いもの）

> LLM によるレビュー。人による検証ではない。この補遺は `review_record.py report` の生成の外で、`--check` の対象ではない。

### A. 理由の採点の追加の抜き取り（procedure.md の段 4 は採用・却下から各 5 件）

選んだ行：採用は B の重点（鮮度・宛先・groups の超過・型）に当たる 5 行 C-iat・C-aud・C-department・C-groups・C-employee-id。却下は種「R1-pilot-B」の 3 行に、残りから C-auth0-plain-roles・C-auth0-employee-number を足した（却下 6 行のうち C-email だけ未採点）。RR4 は引用の名前と主張の対応だけを見た（引用元は開いていない）。

| 行の ID | 列 | RR1 | RR2 | RR3 | RR4 | RR5 | RR6 | RR7 | 合否 | 不合格の観点の説明 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C-iat（採用） | rationale・assumption・revisit_trigger | 満 | 否 | 満 | 満 | 満 | 満 | 満 | 不合格 | RR2：比べる 2 つの時計（5 つの IdP の iat と、BFF が書くログアウトの時刻）がそろう前提が無い（T1） |
| C-aud（採用） | 同上 | 否 | 満 | 満 | 満 | 満 | 満 | 否 | 不合格 | RR1：Auth0 の宛先は両経路で同じ値で B3 を支えない。RR7：assumption（宛先 1 つ）と KC_AT の aud（2 つ）が食い違う（F02） |
| C-department（採用） | 同上 | 満 | 満 | 満 | 満 | 満 | 満 | 満 | 合格 | 代償（社員台帳への依存）は 3.1 の参照で足りる。契約社員の前提は T4 |
| C-groups（採用） | 同上 | 満 | 満 | 満 | 満 | 満 | 満 | 満 | 合格 | — |
| C-employee-id（採用） | 同上 | 満 | 満 | 満 | 満 | 満 | 満 | 満 | 合格 | — |
| C-auth0-plain-roles（却下） | 同上 | 満 | 満 | 満 | 満 | 満 | 満 | 満 | 合格 | — |
| C-auth0-employee-number（却下・禁止） | 同上 | 満 | 対象外 | 満 | 満 | 満 | 満 | 満 | 合格 | 却下の理由は型（数値）なのに「できなくなること：IdP から社員番号を受け取ること」は出どころまで閉じている。判断を支えるので満とした |

合計（review.yaml の 3 件を含む）：採用 5 件のうち合格 3・不合格 2、却下 5 件のうち合格 4・不合格 1（C-cognito-custom-role の RR4）。

### B. 要求の概要（brief-B.md）への辿り

| 行 | 種類 | 要求の概要の箇所 | 辿れたか |
| --- | --- | --- | --- |
| C-cnf | 却下 | 5. の B23、7. の 5（防がないなら見直し条件） | 辿れる。見直しの条件 3 つ（3.1・目録・台帳）。書き手は 12. で専門家に回すよう求めているが、escalation.md の基準には当たらない |
| C-cognito-custom-role | 却下 | 2. の Cognito（custom: は本人が書き換えられる）、5. の B18 | 辿れる |
| C-idp-department | 却下 | 2. の Okta（フックは 3 秒で打ち切り）、5. の B11・B15・B18、7. の 6 | 辿れる |
| C-auth0-employee-number | 却下 | 2. の Auth0（社員番号を数値で出す）、5. の B22、7. の 7 | 辿れる |
| C-iat | 採用 | 5. の B12、7. の 3 | 辿れるが、6. の「時刻は Keycloak 以外では仮想の時計」と食い違う前提を置いている（T1） |
| C-groups | 採用 | 2. の Entra（200 を超えると groups が消える）、4. の B9、5. の B8、7. の 8 | 辿れる |
| C-employee-id | 採用 | 3. の給与明細（社員番号で引く）、5. の B22、7. の 7 | 辿れる |
| C-department | 採用 | 3. の社内文書（営業・経理）、5. の B15、7. の 6 | 辿れるが、3. の「社員」が契約社員を含むかの解釈を置いている（T4） |
| C-aud | 採用 | 2. の IdP ごとの宛先の値、5. の B3 | Keycloak・Entra は辿れる。Okta・Auth0・Cognito の B3 は scope・client_id に頼っており C-aud では答えていない（F02） |

### C. 一覧の外を探した時間と範囲（段 5）

- 時間：2026-11-24 07:12〜07:18（約 6 分を、観点書と問いの一覧を閉じて充てた）。その前の段 1〜3 の読みの中でも、気づいた点を控えた
- 範囲：(1) 要求の概要の 6.（制約・前提）を設計の前提と突き合わせる、(2) 2. の範囲の図とシーケンス図の矢印のうち、ホップの表に無い矢印（B->>D の書き込み）、(3) 移行の期間（現状の入口）の旧経路、(4) 入口が作るトークンの鍵と、1 回だけの受け入れの記録の置き場所（複数台・再起動）、(5) Entra の Graph の呼び出しと v1／v2 の AT、(6) ログアウトトークンの検証の手順、(7) 生成の表と台帳の名前の表記、(8) 要求の「社員」と契約社員
- 出たもの：テンプレート外 9 件（T1・T3〜T10）とカタログ外の質問 1 件（T2）。うち Major 4 件（T1・T3・T4・T5）とカタログ外の T2（Major）
- 探したが指摘にしなかったもの：Okta の ID トークンの sub（BFF のセッションのキー。T2 に含めた）、Auth0 の sub の接続の接頭辞の変化（名寄せの表が人事の手続きで作られるので影響は小さい）、ID トークンの API への送付（B2・B17）の IdP ごとの拒否（5 つとも aud か token_use で拒めると確かめた）

### D. 専門家に回さなかった基準の理由

draft-spec（草案のトークンはすべて却下）、custom-crypto（ES256・RS256 の標準の JWS）、delegation-depth（act が無い）、cross-tenant-exchange（テナントをまたぐ交換が無い。Entra は自社のテナントだけ）、baseline-unmet（3.2 で全基準を満たす）、jwe-key-management（JWE を使わない）、regulated-data（要配慮個人情報・規制のプロファイルの対象が無い）、new-token-type（内部トークンはカタログの internal_token）。

### E. 重大度の集計

Blocker 0・Major 9（F01・F02・F04・F05・T1・T2・T3・T4・T5）・Minor 13（F03・F06〜F12・T6〜T10）。計 22 件。出どころ：観点 12・カタログ外の質問 1・テンプレート外 9。判定：採用 19・保留 3（F05・T4・T8）。
