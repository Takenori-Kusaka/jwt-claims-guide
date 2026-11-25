# レビューレポート：LLM によるレビュー。人による検証ではない

> 設計書のエディターのレビューモード（#50）が `review.yaml` から生成した。レビュアーの名前は自己申告で、本当の承認は GitHub の PR のレビューで行う。レビュアーは LLM で、人による点検は未実施。

## 1. 基本情報

| 項目 | 値 |
| --- | --- |
| 対象 | research/pilot/scenario-b（版 857320c）。worktree agent-acb20059fb1493488 の research/pilot/scenario-b（読み取りだけ） |
| Lite／Full | Full（設計書の判定）。README の 5 問のうち 3 問が Yes で、レビュアーの確認も Full |
| 実施した手順の段 | 0〜7（8 は書き手の対応の後。段 3 の No の読み直しを別のセッションに渡す手順は、このパイロットでは行っていない） |
| レビュアーと役割 | R2（LLM：Claude Opus 5.5（claude-opus-5-5）、Claude Code のサブエージェントのセッション 1 つ。名前は自己申告）。1 名（LLM、役割を切り替えた）：攻撃者 → 運用 → 受け手 → 発行者 → 個人情報 → クライアント。同じ日の同じセッション。独立レビュー：提出まで、ほかのレビュアーの記録を画面で隠した（画面で隠すだけで、review.yaml を開けば見える。守ったかは自己申告） |
| 実施日 | 2026-11-24 |
| 使った教材の版 | templates/review（レビューした時の版：perspectives.md 0.4.0、report\_template.md 0.4.0、問い 168 問）。templates/review の perspectives.md 0.4.0（168 問）・procedure.md 0.4.0・report\_template.md 0.4.0・decision\_tree.md 0.4.0・escalation.md 0.4.0・rationale\_rubric.md 0.5.0（worktree のコミット 857320c）。対比表（contrasts/）は開いていない。perspectives.md の 9.（較正）は過去のレビューの指摘を含むので読んでいない |
| CI の結果 | claim\_lint error 0・warn 2・info 16（profile full）。設計書の 1. と一致。レビュアーが同じコミットで claim\_lint を走らせ、設計書の 1. と一致（L69 C-groups・L11 C-sub-unread の warn） |
| 抜き取りの結果 | 乱数の種「R2-pilot-B-20261124」（claims.yaml の却下の行 6 行から 3 行。sha256(種:行) の順）：C-cognito-custom-role・C-idp-department・C-cnf。3 件を採点、合格 3・不合格 0 |
| 問いの回答 | 全 168 問のうち 168 問に回答（未回答 0）。定義 Yes 49／No 8／該当なし 2。発行 Yes 5／No 4／該当なし 3。伝搬 Yes 20／No 0／該当なし 8。検証 Yes 11／No 1／該当なし 2。認可 Yes 7／No 1／該当なし 20。運用 Yes 14／No 8／該当なし 5。合計 Yes 106／No 22／該当なし 40 |

## 2. 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 出どころ | 種別 | 取り違えた問い（種別が目的と仕組みの不一致のとき） | 判定 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R2-01 | template:00\_core#principals（ポータルの BFF の行）、hops:H3 の validates、claims:C-azp の carried\_in | 2.1 は「Okta の cid・Entra の azp（入口の設定で照合）」と書くが、H3 の validates に azp（または appid）の照合が無く、C-azp の carried\_in は KC\_AT だけ。自社のテナントの別のアプリ（同意の釣りで社員の同意を得た攻撃者のアプリを含む）が api://orders・api://invoices 宛てに取った AT を、入口がポータルの AT と区別せずに受ける。ほかの 4 つの IdP はクライアントを照合している（azp・cid・client\_id）。対策：H3 に「azp がポータルのクライアント ID」を足し、台帳に Entra の azp の行（または C-azp の carried\_in に ENTRA\_AT）を足す。テナントの利用者の同意の設定も前提に書く（判定の理由：2.1 と H3 の 2 つの欄が食い違い、攻撃の経路（同意の釣り）が具体的） | Major | 観点 | 実装とのずれ | — | 採用 |
| R2-02 | hops:H2〜H6 の validates、template:00\_core#priorities-deferrals（送信者制約の見送り）、template:00\_core#scope-boundary（ポータル → 入口の行） | 入口は BFF からの要求を直接の相手として確かめない（H2〜H6 に mTLS・接続元の条件が無い）。入口 → サービスはメッシュの mTLS で確かめるのと非対称。B23 の見送りの理由は「AT は BFF と入口のサーバーにしかない」だが、漏れた AT（ログ・メモリのダンプ・BFF の不具合）はどこからでも入口に送れる。入口が BFF の証明書の接続だけを受ければ、DPoP・mTLS の AT の束縛より安く、B23 の大半（別の端末からの再送）を止められるのに、見送りの比較（3.1・issuance\_profile.sender\_constraint）に候補として出ていない（判定の理由：B23 は要求の脅威で、安価な代替が比べられていない） | Major | 観点 | 候補の漏れ | — | 採用 |
| R2-03 | claims（行が無い）、token\_types:ENTRA\_AT・OKTA\_AT・COGNITO\_AT の required\_claims、schemas/ENTRA\_AT・OKTA\_AT・COGNITO\_AT.consumer.schema.json | 入口が利用者の決定・宛先・種類の判断に読む IdP 固有のクレームが台帳の行に無い：Entra の oid・tid・scp・azp・\_claim\_names・\_claim\_sources、Okta の uid・cid・scp、Keycloak の realm\_access.roles、Cognito の cognito:groups・token\_use。これらは hops の validates の文と C-sub・C-roles の upstream\_issuer の文の中にだけある。結果：(1) required\_claims と受け手のスキーマ（ENTRA\_AT は iss・aud・exp・iat だけ、COGNITO\_AT は空）が欠落を拒否しない、(2) B13（Okta の uid）・B10・B3（Okta は aud が共通で scp だけが守り）の守りが identifier\_properties（stable・reassignable）と on\_missing を持たず、lint・スキーマ・R8 が確かめない、(3) Okta の sub だけが reassignable と書かれ、代わりの uid の不変性が宣言されない（判定の理由：B10・B13・B3 の守りの根になるクレームが未登録） | Major | 観点 | 候補の漏れ | — | 採用 |
| R2-04 | claims:C-roles の assumption・upstream\_issuer、claims:C-groups の provenance、template:00\_core#system-privileges、catalog\_answers の I19・I26 | ロール（admins・editor・approver）の出どころが 5 つの IdP の管理の範囲の和になっている。(1) どの IdP の写しの表でも admins を作れるので、5 つの IdP のどれか 1 つの管理者（Okta の委任のグループ管理者、Entra のグループの所有者・セルフサービスの参加を許したグループ、Cognito のプールの管理者、Auth0 の管理者）が admins を与えられる。(2) 複数の IdP にアカウントを持つ社員は、ロールが多く付く IdP を選んでログインできる（名寄せの表が 1 人に複数の IdP のキーを許すかが書いてない）。(3) IdP の管理者は資格情報のリセット・一時のアクセスパスで任意の社員としてログインでき、給与明細まで読める（I19 は Keycloak の Impersonate だけを扱い、I26 は社員本人の変更として読んでいる）。対策の候補：名寄せの表で社員ごとに使う IdP を 1 つに固定する、admins を与えられる IdP とグループを写しの表で限る（または admins を社員台帳から引く）、IdP の資格情報のリセットを入口の拒否の理由と付録 A の指標に足す（判定の理由：要求の「5 つの IdP の混在」から来る攻撃面で、観点書の問いが 1 つの IdP を前提にしている） | Major | テンプレート外 | 候補の漏れ | — | 採用 |
| R2-05 | claims:C-groups の description・value\_vocabulary（無い）、hops:H4 | Okta の groups はグループの名前で、入口はその名前を写しの表で組織のロールに替える。グループの名前は Okta の管理者（委任のグループ管理者を含む）が改名・同名の作成をできるので、「admins」という名前のグループを作るか改名すれば admins を得られる。Entra はグループの ID（不変）なのに Okta だけ名前。対策：Okta のグループの ID で写す（groups のクレームの値をカスタムの式で ID にする、またはグループのプロファイルの不変の属性を使う）か、Okta の groups の絞り込みを写しの表のグループだけに限り、改名を監視する。C-groups に value\_vocabulary（IdP ごとの値の形）を書く（判定の理由：表示名による照合（dc-09 と同じ型）で権限を作っている） | Major | 観点 | 候補の漏れ | — | 採用 |
| R2-06 | claims:C-roles の on\_revoke・propagation\_delay、template:00\_core#lifecycle（9.1 のロールの剥奪 330・630 秒）、付録 E の 3 | 異動（経理 → 営業など）で外すべきロール（approver・editor・admins）は IdP のグループ・ロールから来るが、人事の異動の発令から IdP のグループを外すまでの経路と秒数が無い。665 秒は「IdP で外した後」の遅れで、外すのが人手なら上限が無い。経理台帳は社員台帳の部署で守られるが、請求書の承認（approver）・管理操作は異動の後も残る。対策：社員台帳の異動を IdP のグループに反映する経路（SCIM・人事連携）と秒数を書くか、異動で変わるロールを社員台帳から引く（判定の理由：要求の主体の説明に「異動が起きる」とあり、ロールの側の反映が設計されていない） | Major | 観点 | 候補の漏れ | — | 採用 |
| R2-07 | template:00\_core#definition-lifecycle（9.3 の移行の手順）、template:00\_core#uncertain（移行の間の守り）、catalog\_answers の outside\_enumeration (4) | 移行の (1)〜(3) の間は B4〜B7 を防げないと書くが、期間の上限・期日が無く、その間の安価な守りを比べていない。(a) 今の入口でも X-User-Role とその変種（大小・\_・重複）を捨てる設定はすぐ入れられる（B4〜B6）、(b) サービスの前のネットワークの閉鎖・メッシュの mTLS を手順の最初に置けば、移行の間も B7 を止められる、(c) サービスが「内部トークンが無い要求の X-User-Role」を拒む段を置ける。現状の手順では管理操作の偽装（B4・B7）が移行の間ずっと開いている（判定の理由：移行期間の旧経路（q-outside-catalog の例）で、偽装に届く） | Major | カタログ外の質問 | 候補の漏れ | — | 採用 |
| R2-08 | template:00\_core#sequence（B-&gt;&gt;D ログアウトの時刻を進める）、template:00\_core#scope-boundary の図と表、hops（BFF → 社員台帳のホップが無い）、token\_types:BFF\_SESSION の revocation | B12 の守り（入口が AT の iat と社員台帳のログアウトの時刻を比べる）は、BFF が社員台帳（人事の権威ある情報源）にログアウトの時刻を書くことに依存するが、この書き込みの経路が範囲の図・ホップの表に無い（入口・invoices は読み取り専用の DB 利用者）。人事の台帳にポータルが書けるという前提、書ける DB 利用者の権限、BFF が奪われたときの影響（任意の社員のログアウトの時刻を未来にして全操作を止める）、Keycloak のログアウトトークンを受けた BFF が落ちていたときの取りこぼしが書いてない（判定の理由：シーケンス図（7.）とホップ・範囲の図（2.・8.）が食い違い、B12 の守りの前提が未検討） | Major | テンプレート項目 | 実装とのずれ | — | 採用 |
| R2-09 | token\_types:ENTRA\_AT の max\_lifetime・issuers・refresh、hops:H3 の validates（exp − iat ≤ 600）、template:00\_core#uncertain | 入口は Entra の AT に exp − iat ≤ 600 と v2.0 の iss を求めるが、それが成り立つ前提（API のアプリ登録の requestedAccessTokenVersion が 2、トークンの寿命のポリシーを API に割り当てる）を設定の項目として書いていない。前提が崩れると（既定の AT は 60〜90 分、v1 の iss は sts.windows.net）、Entra の全社員の要求を入口が拒む（閉じる側の全停止）。リリース前の確かめ（発行された AT の exp − iat と iss を見る）と、付録 A の「入口の拒否の件数」の理由に「寿命の超過」を足すとよい。あわせて、ロールの剥奪の 330・630 秒はリフレッシュでの再計算を前提にしているが、Keycloak・Okta・Entra のどれも出どころが無い（判定の理由：本番の障害の型として妥当。Entra の挙動の事実は IdP の運用の担当に確かめる（unverified-idp-behavior）） | Minor | テンプレート外 | 候補の漏れ | — | 保留 |
| R2-10 | hops:H8 の validates、token\_types:INTERNAL\_TOKEN の jti\_policy、claims:C-jti | 経理台帳で invoices が内部トークンの jti を 35 秒の間 1 回だけ受けるが、(1) invoices が複数の台で動くときの共有の記録先（どの台に来ても再利用を拒める）、(2) 入口・BFF が時間切れで同じ要求を再送したときの扱い（同じ内部トークンを送れば正規の要求が拒まれ、作り直すなら jti の 1 回だけは再送を止めない）、(3) 記録先が止まったときに閉じるか開くかが書いてない（判定の理由：運用の障害の型で、付録 A の「jti の再利用の拒否の件数」の誤検知にもなる） | Minor | テンプレート外 | 候補の漏れ | — | 採用 |
| R2-11 | hops:H2〜H8 の forwarded\_headers（H7・H8 に無い）、token\_types の log\_policy、template:modules/M\_privacy\_minimization#audit-log | ヘッダーの扱いが「X-User-Role とその変種を捨てる」という否定のリストだけで、入口 → サービスで渡してよいヘッダーの許可リストが無い。サービスのフレームワークは同名のヘッダーを「,」でつなぐので、X-User-Role 以外の利用者の属性に見えるヘッダー（X-User-Id・X-Forwarded-User・X-Department など、claim\_request の問 17 では捨てると書く）や Authorization の重複も、入口で拒むか捨てる規則にすべき。ログに残す HTTP ヘッダーの許可リスト、HAR・ログの共有でトークンを除く手順も無い（q-token-logging）（判定の理由：否定のリストは変種の追加で漏れる。要求の CVE の型（連結）は名前を問わない） | Minor | テンプレート外 | 候補の漏れ | — | 採用 |
| R2-12 | token\_types:GRAPH\_AT の assumption、catalog\_answers の U21 | Graph で引いた所属のキャッシュを「利用者ごとに AT の残りの寿命まで」置く。Entra の寿命のポリシーが効かなければ（R2-09）キャッシュも 60〜90 分に延びる。キャッシュの寿命は AT と別の値（例：60 秒か C-groups の volatility 以下）で決める（判定の理由：観点書の No の条件にそのまま当たる） | Minor | 観点 | 候補の漏れ | — | 採用 |
| R2-13 | claims:C-groups の max\_items・overflow\_strategy、token\_types:OKTA\_AT の size（R8 の 19 KB） | C-groups の上限 200 と「問い合わせに切り替える」は Entra の Graph の経路だけで、Okta の groups の件数の上限と超えたときの挙動（レビュアーの記憶では Okta の groups のクレームは 100 件までで、超えるとトークンの要求が失敗する。未確認）が書いてない。R8 の OKTA\_AT の 19 KB は 200 件の前提（判定の理由：事実を Okta の公式文書で確かめてから直す） | Minor | 観点 | 前提の誤り | — | 保留 |
| R2-14 | claims:C-department・C-employee-id・C-auth0-roles の列、claim\_request\_\*.md の問 3・問 5・問 10 | claim\_request の問 3 は出どころを「台帳：registered\_ref・prior\_art\_search」とするが、3 行とも台帳にその列が無い。C-auth0-roles に consumer\_access\_path、C-department・C-auth0-roles に value\_normalization も無い（回答は claim\_request にだけある）。C-auth0-roles は登録名 roles（RFC 9068 §2.2.3.1）と同じ意味なので registered\_ref に書く（判定の理由：25 問と台帳の 2 か所が食い違う） | Minor | 観点 | 実装とのずれ | — | 採用 |
| R2-15 | token\_types:INTERNAL\_TOKEN の required\_claims、schemas/INTERNAL\_TOKEN.consumer.schema.json、hops:H7 の custom\_claims、claim\_request\_employee\_id.md の問 14 | INTERNAL\_TOKEN の required\_claims（と受け手のスキーマ）は社員番号を必須にするが、H7（orders 宛て）は roles・部署だけを運び、問 14 は「orders 宛てには載せない」と書く。どちらかが誤り（orders が全要求を拒むか、orders 宛てにも社員番号を載せることになる）。宛先ごとに必須が違うなら、目録の種別を宛先で分けるか、required\_claims をホップの側に書く（判定の理由：2 つの欄が食い違う） | Minor | 観点 | 実装とのずれ | — | 採用 |
| R2-16 | design.md の 8. の矢印の表・9. の生成の表（https://claims.example.com/.roles など）と、台帳・スキーマ・付録 D.2（https://claims.example.com/roles） | render が組織の名前空間のクレーム名を「https://claims.example.com/.roles」「/.employee\_id」「/.department」と書き、台帳・スキーマ・D.2 の名前（「/」の後に「.」が無い）と違う。実装者が生成の表から Auth0 の Action を書くと、入口が読む名前と食い違い、ロールが黙って空になる（B20 と同じ結果）。namespace の style（flat\_prefix）の表示の規則か render の不具合（判定の理由：生成の表は設計書の読み物として実装者が読む） | Minor | テンプレート外 | 実装とのずれ | — | 採用 |
| R2-17 | template:00\_core#question-mechanism（UC1・UC2 の q-resource）、claims:C-aud・C-scope、hops:H4・H6 | 6. は q-resource を C-aud で答えるが、Okta（api://default）と Auth0（https://api.example.com）は aud が両サービスで共通で、実際の宛先の区別（B3）は scope（scp）で行っている。scope は「クライアントに委ねた範囲」で、BFF が 1 つの AT で両方の scope を求めれば区別が消える（前提は C-scope の assumption だけ）。6. の表に Okta・Auth0 では q-resource を scope で補うことと、その前提が崩れる条件を書く（Auth0 は API を 2 つに分ける見直しの条件も無い）（判定の理由：判断の木の q-resource（aud）と取り違えやすい scope で答えている） | Minor | 観点 | 目的と仕組みの不一致 | q-resource を scope（q-authorized の仕組み）で答えた（Okta・Auth0） | 採用 |
| R2-18 | template:modules/M\_token\_validation（付録 D.3 の 1.・2.・8.・9.）、token\_types の unknown\_kid（use\_last\_known）、token\_types:INTERNAL\_TOKEN | (1) 5 つの発行者の鍵の選び方が未記述：D.3 は「署名の前にペイロードを使わない」と「鍵は各 iss の JWKS だけから取る」を並べるが、iss を署名の前に読んで鍵の集合を選ぶのか、kid で全 JWKS から探して鍵と iss の対応を確かめるのかが書いてない。(2) IdP の鍵の漏えいで IdP が鍵を外しても、入口は JWKS のキャッシュ（最大 3600 秒）と use\_last\_known でその鍵を受け続ける。(3) 内部トークンの署名鍵（入口だけが持つ）の保管（HSM・KMS）と漏えい時の緊急のローテーション（サービスの JWKS のキャッシュ 300 秒・旧鍵 1 時間）が無い。内部トークンの鍵が漏れれば全社員になりすませる（判定の理由：書き足しで済むが、内部トークンの鍵は全体の信頼の根） | Minor | 観点 | 候補の漏れ | — | 採用 |
| R2-19 | hops:H8 の enforced\_at（請求書の承認は approver）、template:00\_core#question-mechanism の UC2、claims:C-roles の enforced\_at | 「請求書の承認（approver）」は要求の 3. の操作の表に無い（要求にあるのは carol が approver のロールを持つことだけ）。設計が操作を足したのに、出どころと「要求に無い」ことが書いてない。逆に、要求の操作 6 つ（read・admin・ledger・docs・edit・payslip）の受け手の対応は追える（判定の理由：要求と設計の対応（トレース）のずれ） | Minor | テンプレート外 | 実装とのずれ | — | 採用 |
| R2-20 | claims:C-sub の issuers・carried\_in・upstream\_issuer | 理由の採点（RR7 否）：C-sub の issuers に Entra・Okta の iss があるが、carried\_in に ENTRA\_AT・OKTA\_AT が無い（その 2 つの sub は C-sub-unread）。同じ行の列の間で、どの発行者のどのクレームがこの行かが食い違う。R2-03 で oid・uid の行を足し、C-sub の issuers を Keycloak・Cognito・Auth0・入口に絞る（判定の理由：RR7（内部の一貫性）） | Minor | 観点 | 理由の不備 | — | 採用 |
| R2-21 | template:00\_core#lifetime-policy、付録 E の 4、token\_types の lifetime\_refs | 寿命の理由は「NIST IR 8587 の 1 時間以内の中で短めにした」だけで、剥奪をどれだけ早く効かせたいか（停止・ログアウトは db\_lookup で 0 秒なので、AT の寿命が効くのはロールだけ）と、代償（リフレッシュの負荷、IdP の停止で 300 秒後に全員が止まる）の比較が無い。RR3（代償）の不足（判定の理由：RR3） | Minor | 観点 | 理由の不備 | — | 採用 |
| R2-22 | token\_types の issuance\_profile.rt\_strategy の refs（RFC 9700 §4.14.2） | 機密クライアント（BFF）の RT の方式の根拠に RFC 9700 §4.14.2 を引いているが、その節がローテーションか送信者制約を求めるのは公開クライアント。機密クライアントの RT はクライアント認証（private\_key\_jwt）に束縛されることを理由にし、ローテーションは補助として書く。RR5（状況への当てはまり）（判定の理由：RR5） | Minor | 観点 | 理由の不備 | — | 採用 |
| R2-23 | hops:H7・H8（upstream なし）、hops.yaml の冒頭の注、template:00\_core#uncertain（L16 と作り直し） | L16 と合わないため作り直しのホップの upstream を外し、寿命・宛先の絞り込みの機械の確認が走らない。12. に書いたのはよいが、規則の側（上流が複数の IdP に分かれる作り直し、独自クレームの出どころがトークンでなく台帳の DB）を #6 に渡した記録が無い（判定の理由：lint の回避として観点書の No の条件に当たる） | Minor | 観点 | 候補の漏れ | — | 採用 |
| R2-24 | token\_types の issuers（5 つの IdP）、要求の 6.（時刻は仮想の時計、鍵・パスワードは試験用）、catalog\_answers の outside\_enumeration | 試験の経路（模擬の IdP・仮想の時計・試験用の鍵）を本番の入口の許可リストから外す規則が無い。入口は iss の完全一致で 5 つの発行者を受けるが、試験用の発行者・鍵・ずれの大きい時計の設定が本番に残る経路（設定の取り違え）を、範囲の外にした前提として書く（判定の理由：q-outside-catalog の例「テストの経路」） | Minor | カタログ外の質問 | 候補の漏れ | — | 採用 |

## 3. 対応の一覧

| 指摘 ID | 担当 | 期限 | 状態 | 対応の PR・コミット |
| --- | --- | --- | --- | --- |
| R2-01 | 設計の書き手 | — | 未着手 | — |
| R2-02 | 設計の書き手 | — | 未着手 | — |
| R2-03 | 設計の書き手 | — | 未着手 | — |
| R2-04 | 設計の書き手 | — | 未着手 | — |
| R2-05 | 設計の書き手 | — | 未着手 | — |
| R2-06 | 設計の書き手 | — | 未着手 | — |
| R2-07 | 設計の書き手 | — | 未着手 | — |
| R2-08 | 設計の書き手 | — | 未着手 | — |
| R2-09 | 設計の書き手 | — | 未着手 | — |
| R2-10 | 設計の書き手 | — | 未着手 | — |
| R2-11 | 設計の書き手 | — | 未着手 | — |
| R2-12 | 設計の書き手 | — | 未着手 | — |
| R2-13 | 設計の書き手 | — | 未着手 | — |
| R2-14 | 設計の書き手 | — | 未着手 | — |
| R2-15 | 設計の書き手 | — | 未着手 | — |
| R2-16 | 設計の書き手 | — | 未着手 | — |
| R2-17 | 設計の書き手 | — | 未着手 | — |
| R2-18 | 設計の書き手 | — | 未着手 | — |
| R2-19 | 設計の書き手 | — | 未着手 | — |
| R2-20 | 設計の書き手 | — | 未着手 | — |
| R2-21 | 設計の書き手 | — | 未着手 | — |
| R2-22 | 設計の書き手 | — | 未着手 | — |
| R2-23 | 設計の書き手 | — | 未着手 | — |
| R2-24 | 設計の書き手 | — | 未着手 | — |

## 4. 専門家に回した項目

| 基準の ID（escalation.md） | 行・欄 | 回した先 | 期限 | 結論 |
| --- | --- | --- | --- | --- |
| unverified-idp-behavior | template:00\_core#uncertain（Entra の AT の寿命・版、RT の再利用の検知）、ENTRA\_AT・KC\_AT・OKTA\_AT の refresh（リフレッシュでの再計算）、C-groups（Okta の件数の上限） | IdP の運用の担当 | 設計の次の版の前 | 未 |

当てはまらなかった基準：draft-spec・custom-crypto・delegation-depth・cross-tenant-exchange・baseline-unmet・jwe-key-management・regulated-data・new-token-type

## 5. カタログ・観点書・対応表に戻す事項

| 戻す先 | 中身 | 指摘 ID | issue・PR |
| --- | --- | --- | --- |
| 観点書（templates/review/perspectives.md） | 複数の IdP を受ける設計で、ロールを与えられる管理の範囲（どの IdP・どのグループの管理者が組織のロールを作れるか）と、1 人の社員が使う IdP を固定するかを問う問いが無い。IdP の管理者による資格情報のリセット・一時のアクセスパスでの代理ログインも問いに無い | R2-04 | — |
| 観点書（templates/review/perspectives.md） | 移行期間に旧経路（ヘッダーを信じるサービス）が残るとき、その間の守り（今の入口での除去・ネットワークの閉鎖を先に置く）と期日を問う問いが無い（q-outside-catalog の例に名前だけある） | R2-07 | — |
| 観点書（templates/review/perspectives.md） | ヘッダーを否定のリストで捨てるか、入口 → サービスの許可リストにするかを問う問いが無い（ap-2-5 は同名の変種だけ）。jti の 1 回だけの受け入れの運用（共有の記録先・再送）の問いも無い | R2-10・R2-11 | — |
| lint・render（tools/claim\_lint） | render が flat\_prefix の名前空間のクレーム名を「https://claims.example.com/.roles」と書く（台帳・スキーマは「/roles」）。作り直しのホップで上流が複数の IdP に分かれるときの L16（upstream）の書き方。hops の validates の文に出る IdP 固有のクレーム（oid・uid・scp など）が台帳の行に無いことを拾う規則の候補 | R2-03・R2-16・R2-23 | — |
| カタログ（templates/catalog/） | IdP の管理者による資格情報のリセット・一時のアクセスパスの後の発行（I19 は Keycloak の Impersonate、I26 は本人の変更）。Okta の groups の件数の上限と超過時の失敗（確かめてから） | R2-04・R2-13 | — |

## 6. 理由の採点（抜き取り）

| 行の ID | 列 | RR1 | RR2 | RR3 | RR4 | RR5 | RR6 | RR7 | 合否 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C-cognito-custom-role | rationale | 満 | 満 | 満 | 満 | 満 | 満 | 満 | 合格 |
| C-idp-department | rationale | 満 | 満 | 満 | 満 | 満 | 満 | 満 | 合格 |
| C-cnf | rationale | 満 | 満 | 満 | 満 | 満 | 満 | 満 | 合格 |

- C-cognito-custom-role：禁止の行で規則の出どころ（slide:p04-split-by-writer）あり。要求 B18・2. の Cognito の行に辿れる。RR4 は引用元を開かず名前と主張の対応だけ
- C-idp-department：要求 B11・B15・2. の Okta の 3 秒の打ち切りに辿れる。B18 は要求ではロールの書き換えで、部署への拡張は書き手の読み。RR4 は引用元を開いていない
- C-cnf：要求 B23・7. の 5 に辿れる（見直しの条件あり）。安価な代替の比較の漏れは理由の不備でなく R2-02 として指摘。RR4 は引用元を開いていない

## 7. 点検状況

LLM によるレビュー。人による検証ではない（templates/CONTRIBUTING.md の 3.）。指摘の採否は人のレビュアーが決める

人による点検は未実施（このレビューは LLM のセッションのもの。人のレビュアーの採否は未了）。

レビュアーの名前は自己申告です（エディターにはログインが無い）。本当の承認は GitHub の PR のレビューで行います。

## 8. 問いごとの回答

| 段 | 問い ID | 回答 | 理由（1 行） |
| --- | --- | --- | --- |
| 1. 定義 | dc-01 | Yes | 独自の 3 行（C-department 60 秒・C-auth0-roles 900 秒・C-employee-id never）とも volatility が載るトークンの受け入れの上限（35・330 秒）以上 |
| 1. 定義 | dc-02 | No | C-department・C-employee-id・C-auth0-roles に registered\_ref も prior\_art\_search も無い（claim\_request の問 3 は台帳のこの列を出どころに挙げている）。R2-14 |
| 1. 定義 | dc-03 | Yes | namespaces に https://claims.example.com/ を宣言。予約名との照合は各 claim\_request の問 4 |
| 1. 定義 | dc-04 | No | C-auth0-roles に consumer\_access\_path が無い（claim\_request の問 5 にだけ書いてある）。R2-14 |
| 1. 定義 | dc-05 | Yes | 型は 1 つ。社員番号は数字の文字列（pattern） |
| 1. 定義 | dc-06 | Yes | 配列は JSON の配列。scope の空白区切りは RFC 9068 の形 |
| 1. 定義 | dc-07 | Yes | 3 行とも absent\_semantics と on\_missing がある |
| 1. 定義 | dc-08 | No | C-department・C-auth0-roles に value\_normalization が無い（claim\_request の問 10 だけ）。R2-14 |
| 1. 定義 | dc-09 | Yes | 独自の 3 行は部署のコード・社員番号・語彙の値で照合（表示名を使わない）。Okta の groups の名前による写しは q-value-vocabulary で No |
| 1. 定義 | dc-10 | Yes | 書き手は入口（社員台帳から）と Auth0 の Action。本人の値（custom:\*・user\_metadata）と分けている |
| 1. 定義 | dc-11 | Yes | 独自の 3 行に max\_bytes・max\_items・overflow\_strategy がある |
| 1. 定義 | dc-12 | Yes | 独自の 3 行の issuers は 1 つ（入口か Auth0）。on\_missing あり |
| 1. 定義 | dc-gate | No | dc-02・dc-04・dc-08 に No がある（台帳の列の欠け。判断の中身は claim\_request にある） |
| 1. 定義 | pa-01 | Yes | 3 件とも受け手（orders・invoices・gateway）と判断を書き、usage と一致 |
| 1. 定義 | pa-02 | Yes | 部署は 60 秒の許容と経理台帳の引き直し、Auth0 のロールは 330 秒、社員番号は never |
| 1. 定義 | pa-03 | Yes | 3 件とも IANA・SCIM・RFC 9068 を探した記録が claim\_request にある（台帳の列は空。dc-02） |
| 1. 定義 | pa-04 | Yes | 問 4 で IdP の予約名・Auth0 の禁止の接頭辞と照合 |
| 1. 定義 | pa-05 | Yes | 受け手は共通の検証部品で JSON のキーとして読むと回答。設計の宣言で、実装での確認ではない |
| 1. 定義 | pa-06 | Yes | flat\_prefix と台帳の namespace・shape が一致 |
| 1. 定義 | pa-07 | Yes | 単一の型、区切り文字列なし |
| 1. 定義 | pa-08 | Yes | 社員番号・部署のコードは文字列 |
| 1. 定義 | pa-09 | Yes | 部署は on\_missing 無視＋部署で絞る操作を拒む、社員番号は拒否、Auth0 のロールは無視＋ロールなしで、台帳と一致 |
| 1. 定義 | pa-10 | Yes | 完全一致（社員番号は数値に変換しない） |
| 1. 定義 | pa-11 | Yes | 書き手は platform（入口・Auth0 の管理者）だけ |
| 1. 定義 | pa-12 | Yes | 部署のコード・社員番号・ロールの語彙で照合 |
| 1. 定義 | pa-13 | Yes | 16・20・32 バイト、超えたら発行を失敗 |
| 1. 定義 | pa-14 | Yes | 部署は H7 だけ、社員番号は H8 だけ。ただし目録の required\_claims は両方に社員番号を求める（R2-15） |
| 1. 定義 | pa-15 | Yes | 入口だけ、または Auth0 だけ |
| 1. 定義 | pa-16 | Yes | 組織共通の検証部品（D.3 の 11.） |
| 1. 定義 | pa-17 | Yes | ヘッダーに移さない。X-User-Role・X-Department・X-Employee-Id の変種を捨てると回答 |
| 1. 定義 | pa-18 | Yes | 社員台帳を引けなければ拒む（503） |
| 1. 定義 | pa-19 | Yes | 絞り込みの値で、無視すれば機能が無いか権限が増えない |
| 1. 定義 | pa-20 | Yes | log\_policy・pii\_category と一致 |
| 1. 定義 | pa-21 | 該当なし | 委任のトークンが無い（q-actor 不要） |
| 1. 定義 | pa-22 | Yes | consumers が設計書の受け手と一致 |
| 1. 定義 | pa-23 | Yes | 受け手が先の順を書いた |
| 1. 定義 | pa-24 | Yes | 並行発行の期間（内部トークンの寿命とリリースの期間）を書いた |
| 1. 定義 | pa-25 | Yes | 入口の試験と受け手の契約テスト、Auth0 の Action のテスト |
| 1. 定義 | pa-gate | Yes | 3 件の回答はクレームごとに固有 |
| 1. 定義 | pa-trace | No | claim\_request の問 3 が出どころとする台帳の registered\_ref・prior\_art\_search が台帳に無く、両方から辿れない。R2-14 |
| 1. 定義 | q-registered-synonym | Yes | C-auth0-roles（Auth0 の上流の値）と C-roles（内部トークン）は段階が違い、not\_meaning で区別 |
| 1. 定義 | q-reuse-standard-structure | No | 役割の用途（roles）に当たる C-auth0-roles に registered\_ref（RFC 9068 §2.2.3.1）が無い。R2-14 |
| 1. 定義 | q-auth-context-semantics | Yes | iat はトークンの発行時刻としてログアウトの時刻と比べるだけ。auth\_time の代わりにしていない（not\_meaning） |
| 1. 定義 | q-scope-semantics | Yes | scope をクライアントの範囲として扱い、利用者の権限は roles。Okta・Auth0 では scope を宛先の区別にも使う（R2-17） |
| 1. 定義 | q-value-vocabulary | No | C-groups に value\_vocabulary が無く、Okta の groups はグループの名前（改名・同名の作成ができる文字列）で写しの表を引く。R2-05 |
| 1. 定義 | q-role-explosion | Yes | ロールは 4 語の役割だけ |
| 1. 定義 | q-identifier-choice | Yes | iss＋sub、Entra は tid＋oid、Okta は uid。email・upn を使わない |
| 1. 定義 | ap-1-6 | Yes | email・upn・preferred\_username を照合に使わない |
| 1. 定義 | q-pairwise-external | Yes | 目録の subject\_type が各行にある（ENTRA\_AT は pairwise と明記） |
| 1. 定義 | q-pairwise-unguessable | 該当なし | 組織がペアワイズの sub を作らない（Entra の仮名の sub は読まない） |
| 1. 定義 | ap-2-1 | No | C-groups の max\_items 200・overflow「問い合わせに切り替える」は Entra の Graph だけ。Okta の groups の上限（公式文書では 100 件と記憶。未確認）と超過時の挙動が書いてない。R2-13 |
| 1. 定義 | ap-2-2 | Yes | ロール・部署は内部トークン 30 秒、経理台帳は引き直し |
| 1. 定義 | ap-2-3 | Yes | 型・形が台帳と受け手のスキーマで一致（社員番号は string） |
| 1. 定義 | ap-2-4 | Yes | 独自の 3 行は組織の名前空間の下 |
| 1. 定義 | q-payload-readable | Yes | confidential\_from が全行で空 |
| 1. 定義 | q-confidential-reaches-reader | Yes | 読まれてはいけないクレームが無い |
| 1. 定義 | q-no-secret-or-raw-pii | Yes | 秘密・生年月日などを載せない |
| 1. 定義 | q-derived-value | Yes | D.5 の 4. で派生値を検討（受け手 1 つで部署のコードそのもの） |
| 1. 定義 | q-baseline-kept | Yes | 3.2 の 7 基準をすべて満たすと記入（Cognito の aud は client\_id＋token\_use で代替） |
| 2. 発行 | q-single-issuer | Yes | 各段階で発行者は 1 つ。サービスは追記・作り直しをしない |
| 2. 発行 | q-hook-failure | Yes | Okta のフックの値は使わず、Cognito・Auth0 のフックで欠けたロールは「権限なし」に倒す（拒否ではないが許可は増えない）。I11・I25・I26 の hook\_invoked は unknown のまま |
| 2. 発行 | q-size-limit | Yes | R8 で 7 種別を計算（Okta の 200 件の前提は R2-13） |
| 2. 発行 | ap-1-7 | No | groups の provenance は「管理者が設定した値」だが、Entra のグループの所有者（管理者でない社員）やセルフサービスの参加、Okta の委任のグループ管理者が、写しの表に載ったグループに人を足せる。R2-04 |
| 2. 発行 | q-hook-adds-raw-pii | Yes | Auth0 の Action が足すのはロールだけ |
| 2. 発行 | q-minimal-per-recipient | Yes | 部署は orders、社員番号は invoices だけ（required\_claims の食い違いは R2-15） |
| 2. 発行 | q-rar-per-audience | 該当なし | authorization\_details を使わない |
| 2. 発行 | q-agent-own-identity | 該当なし | エージェントが無い（P4 を使わない） |
| 2. 発行 | q-agent-delegation-claims | 該当なし | 代理で動くトークンが無い |
| 2. 発行 | q-idp-capability-verified | No | Entra の AT の版（requestedAccessTokenVersion）と寿命のポリシー、Okta の groups の件数の上限、各 IdP のリフレッシュでの再計算に出どころが無い（12. に一部だけ）。R2-09・R2-13 |
| 2. 発行 | q-variant-comparison | No | B23 の見送りで、入口が BFF だけを受ける（BFF → 入口の mTLS）安価な代替を比べていない。R2-02 |
| 2. 発行 | q-outside-catalog | No | 書き手の 4 件に加え、IdP の管理者による資格情報のリセット・一時パスでの代理ログイン、複数の IdP のアカウントを持つ社員の IdP の選び分け、BFF が社員台帳に書く経路、再試行と jti、試験用の IdP・鍵の経路、移行期間の旧経路の守りが答えられていない。R2-04・R2-07・R2-08・R2-10・R2-24 |
| 3. 伝搬 | cf-01 | Yes | 段階ごとに書き手が決まり、フックの値（部署）を使わない |
| 3. 伝搬 | cf-02 | Yes | フックで欠けたロールは空、部署は IdP から取らない（q-hook-failure と同じ） |
| 3. 伝搬 | cf-03 | Yes | 入口で内部トークン（iss 入口・aud 1 つ）に作り直す |
| 3. 伝搬 | cf-04 | Yes | H7・H8 で token\_type と aud が替わる |
| 3. 伝搬 | cf-05 | Yes | H7・H8 は 30 秒・aud 1 つで上流（300・600 秒、aud 2 つ）以下（L16 が走らないので手で確かめた） |
| 3. 伝搬 | cf-06 | 該当なし | Txn-Token を使わない |
| 3. 伝搬 | cf-07 | Yes | すべてのホップの validates に中身がある |
| 3. 伝搬 | cf-08 | Yes | X-User-Role とその変種を入口で捨てる（許可リストでない点は R2-11） |
| 3. 伝搬 | cf-09 | 該当なし | 要求にアクセス元（IP・端末）の条件が無い |
| 3. 伝搬 | cf-10 | Yes | jti と sub のハッシュ、全文を残さない（act・txn は無い） |
| 3. 伝搬 | q-hop-narrowing | Yes | H7・H8 は aud 1 つ、独自クレームは受け手ごと |
| 3. 伝搬 | q-hop-lifetime | Yes | H7・H8 の upstream が無いので手で確かめた（30 ≤ 300）。lint の回避は q-lint-workaround |
| 3. 伝搬 | q-single-aud-resource | 該当なし | エージェント・resource を使う経路が無い |
| 3. 伝搬 | ap-2-6 | Yes | 受け取った AT を渡さず作り直す |
| 3. 伝搬 | q-no-passthrough | Yes | 入口だけが作り直し、IdP と交換しない |
| 3. 伝搬 | ap-2-5 | Yes | X-User-Role（変種を含む）を入口で除去し、誰も書かない |
| 3. 伝搬 | q-unverified-claim-extraction | Yes | 署名の検証の後に取り出す |
| 3. 伝搬 | q-gateway-bypass-path | Yes | サービスは mTLS と内部トークンで止める（B7）。BFF → 社員台帳の書き込みの経路は図に無い（R2-08） |
| 3. 伝搬 | q-step-up-path-coverage | 該当なし | 追加認証を求める操作が無い（付録 B） |
| 3. 伝搬 | q-txn-scope-fixed | 該当なし | Txn-Token を使わない |
| 3. 伝搬 | q-txn-required-claims | 該当なし | Txn-Token を使わない |
| 3. 伝搬 | q-claim-earliest-hop | Yes | 部署・社員番号は入口で社員台帳から初めて分かる値で、その最初のホップ（H7・H8）から載る |
| 3. 伝搬 | ap-2-9 | Yes | 内部トークンは署名・jti の記録・失効の手段（exp・db\_lookup・one\_time\_use）がある。テナントは無い |
| 3. 伝搬 | q-internal-delegation-token | Yes | 目録の INTERNAL\_TOKEN に署名・寿命・失効・ログがある |
| 3. 伝搬 | ap-2-7 | 該当なし | エージェントが無い |
| 3. 伝搬 | q-delegation-depth-and-revocation | 該当なし | 委任が無い |
| 3. 伝搬 | q-idp-diff-absorbed | Yes | サービスが読むのは入口の iss の組織のクレームだけ |
| 3. 伝搬 | q-token-not-in-url | Yes | URL に載るのは認可コードだけ |
| 4. 検証 | q-shared-validator | Yes | 組織共通の検証部品（版は未定） |
| 4. 検証 | ap-1-1 | Yes | alg\_allowlist（RS256・ES256） |
| 4. 検証 | ap-1-2 | Yes | デコードだけの経路が無い |
| 4. 検証 | q-validate-before-read | Yes | 権限のクレームは検証の後。発行者ごとの鍵の選び方は ap-1-5 の補足（R2-18） |
| 4. 検証 | ap-1-3 | Yes | aud を必須（Cognito は client\_id で代替） |
| 4. 検証 | ap-1-4 | Yes | Entra は自社の tid の iss だけ（B10） |
| 4. 検証 | ap-1-5 | Yes | D.3 の 2. で「鍵は各 iss の JWKS だけから取る」。署名の前に iss を読む順序との関係は未記述（R2-18） |
| 4. 検証 | ap-1-8 | Yes | exp 必須、ずれ 30 秒（内部 5 秒） |
| 4. 検証 | q-typ-distinguishes | Yes | aud・azp・token\_use・typ で ID トークンを拒む（B2・B17） |
| 4. 検証 | q-required-rejected | No | 入口が利用者の決定と認可に読む oid・tid（Entra）、uid・cid（Okta）、scp、token\_use（Cognito）が required\_claims・受け手のスキーマに無い。COGNITO\_AT の required\_claims は空。R2-03 |
| 4. 検証 | q-no-unverified-passthrough-mode | Yes | D.3 の 10.、各 claim\_request の問 18 と一致 |
| 4. 検証 | q-consumer-expression | Yes | 完全一致、欠落は拒否か権限なし |
| 4. 検証 | q-nested-jwt-both-layers | 該当なし | JWE を使わない |
| 4. 検証 | q-unwrapped-value-authz | 該当なし | 移行の後はヘッダーなどの写しを認可に使わない（移行の間は R2-07） |
| 5. 認可 | q-object-level-authz | Yes | orders は sub、invoices は社員番号でデータの側と照合（D.4 の 3.） |
| 5. 認可 | q-tenant-data-match | 該当なし | テナントが無い |
| 5. 認可 | q-writer-distinguished | Yes | custom:\* と cognito:groups、IdP の部署と社員台帳の部署を分けている |
| 5. 認可 | q-validity-not-authz | Yes | 操作ごとにロール・部署・本人を判断 |
| 5. 認可 | q-original-principal | Yes | サービス間の呼び出しが無く、内部トークンの sub が元の利用者 |
| 5. 認可 | q-authorize-service-and-user | No | 入口 → サービスは mTLS で確かめるが、BFF → 入口（H2〜H6）は直接の相手を確かめない。R2-02 |
| 5. 認可 | q-scope-and-role | Yes | scope は入口、ロールはサービスで確かめる |
| 5. 認可 | q-access-context-from-pep | 該当なし | アクセス元の条件を使わない |
| 5. 認可 | q-step-up-by-rs | 該当なし | 追加認証を求めない（付録 B。要求に無い） |
| 5. 認可 | q-approval-from-as | 該当なし | エージェント・クライアントが判断する承認が無い（請求書の承認は R2-19） |
| 5. 認可 | q-cross-tenant-identity | 該当なし | テナントが 1 つ（IdP をまたぐ名寄せは社員台帳の表で行い email を使わない） |
| 5. 認可 | q-operator-act | 該当なし | 運用者の代理操作が無い（2.2） |
| 5. 認可 | q-break-glass | 該当なし | 緊急時の特権のトークンを作らない（2.2） |
| 5. 認可 | cd-01 | 該当なし | DB の文脈を設定しない（M\_data\_layer を使わない） |
| 5. 認可 | cd-02 | 該当なし | SET LOCAL を使わない |
| 5. 認可 | cd-03 | 該当なし | SQL Server を使わない |
| 5. 認可 | cd-04 | Yes | 認可は本人が書き換えられない属性だけ（custom:\* を読まない） |
| 5. 認可 | cd-05 | 該当なし | DB のロールを選ぶクレームが無い |
| 5. 認可 | cd-06 | 該当なし | RLS を使わない |
| 5. 認可 | cd-07 | 該当なし | DB のユーザーを利用者に対応付けない |
| 5. 認可 | cd-08 | Yes | H10〜H13 に connection\_max\_lifetime 3600。剥奪は問い合わせの条件で効く |
| 5. 認可 | cd-09 | 該当なし | DB まで利用者の ID を伝える監査の要求が無い（サービスのログで記録） |
| 5. 認可 | cd-10 | 該当なし | DB の文脈を使わない（クレームが欠けたら内部トークンを拒む） |
| 5. 認可 | cd-11 | 該当なし | データ層の文脈・すり抜ける主体の設定が無い |
| 5. 認可 | q-db-context-writers | 該当なし | DB の文脈を使わない |
| 5. 認可 | q-sql-tenant-predicate | 該当なし | テナントが無い |
| 5. 認可 | q-db-context-parameterized | 該当なし | DB の文脈を使わない |
| 5. 認可 | q-ddm-rls-only | 該当なし | DDM・RLS を使わない |
| 6. 運用 | q-four-lifetimes-written | Yes | 9.1〜9.3 と生成の表で 4 層を別に書いた |
| 6. 運用 | q-lifetime-rationale | No | 5.1 と付録 E の 4. の理由は「NIST の 1 時間以内で短めに」で、リフレッシュの負荷・IdP の停止の影響という代償との比較が無い。R2-21 |
| 6. 運用 | q-session-rt-bounds | Yes | idle 1800・最大 36000（24 時間以下） |
| 6. 運用 | q-rt-policy-by-client | No | 機密の BFF の RT の方式の根拠に、公開クライアント向けの RFC 9700 §4.14.2 を引いている。R2-22 |
| 6. 運用 | q-freshness-mitigation | Yes | 超える行は無く、経理台帳とログアウトの対策の担い手（invoices・入口）を書いた |
| 6. 運用 | q-refresh-reevaluated | No | Keycloak・Entra・Okta のリフレッシュでのロール・グループの再計算を前提にした 330・630 秒に、実測・文書の出どころが無い（Entra は「確かめていない」）。R2-09 |
| 6. 運用 | q-revocation-delivery | Yes | 種別ごとに手段と秒数。重要な操作は問い合わせ |
| 6. 運用 | q-external-user-deprovision | No | 異動でのロール（approver・editor・admins）の剥奪は IdP の管理者がグループを外すまで始まらず、人事の異動から IdP への経路と秒数が無い。Keycloak 以外の IdP 側のログアウトも届かない（12.）。R2-06 |
| 6. 運用 | q-relies-on-at-expiry | No | Graph の結果のキャッシュの寿命を「AT の残りの寿命まで」と決めている（GRAPH\_AT の assumption、U21）。R2-12 |
| 6. 運用 | q-long-running | 該当なし | 非同期の処理が無い |
| 6. 運用 | q-system-actor-no-fake-sub | Yes | GRAPH\_AT は入口自身の権限で、利用者のクレームを載せない |
| 6. 運用 | q-agent-short-lived-no-rt | 該当なし | エージェントが無い |
| 6. 運用 | q-copies-outlive | Yes | Graph のキャッシュ・JWKS・DB の接続に期限がある（Graph のキャッシュの決め方は R2-12） |
| 6. 運用 | q-deprecated-deadline | 該当なし | deprecated の行が無い（X-User-Role の移行の期日は R2-07） |
| 6. 運用 | q-change-order | Yes | 9.3 に受け手が先の手順 |
| 6. 運用 | q-key-rotation | Yes | JWKS から取り、取り直しの最短間隔と負のキャッシュ、公開してから使う順序がある（鍵の漏えい時の扱いは R2-18） |
| 6. 運用 | q-dependency-outage | Yes | 社員台帳の停止で全停止、Graph の失敗で拒否、JWKS は最後の鍵、フックの打ち切りで部署を使わないと書いた |
| 6. 運用 | ap-2-8 | Yes | jti だけ記録 |
| 6. 運用 | q-token-logging | No | 記録する HTTP ヘッダーの許可リストと、HAR・ログの共有でトークンを除く手順が無い。R2-11 |
| 6. 運用 | q-audit-log-protected | Yes | D.5 の 8.（情報システム部だけ、1 年） |
| 6. 運用 | q-audit-correlation | Yes | sub のハッシュ・jti・iss で相関（act・txn・承認 ID は無い） |
| 6. 運用 | q-trace-id-trust | 該当なし | txn を使わない |
| 6. 運用 | q-scope-elevation-logged | 該当なし | エージェントが無い |
| 6. 運用 | q-operational-metrics | Yes | 付録 A に 7 指標・周期・持ち主 |
| 6. 運用 | q-lint-workaround | No | H7・H8 の upstream を L16 と合わないため外した（hops.yaml の冒頭・12.）。規則の側の誤りの候補として #6 に渡した記録が設計書に無い。R2-23 |
| 6. 運用 | q-evidence-attribution | Yes | RFC 8693 §4.3（client\_id）・RFC 7800 §3.1（cnf）・Microsoft の configurable token lifetimes（AT の最短 10 分）を記憶で照合（原典は開いていない） |
| 6. 運用 | q-limit-consistency | No | 2.1 は Entra の azp を入口で照合と書くが H3 の validates に無い（R2-01）。INTERNAL\_TOKEN の required\_claims と H7 の custom\_claims が食い違う（R2-15）。生成の表のクレーム名が台帳・スキーマと違う（R2-16） |

## 9. 行ごとの記録（エディターのレビューモード、#50。生成した時の台帳と比べた状態）

行の内容のハッシュ（RFC 8785 JCS の SHA-256、`tools/row_hash.py`）に結びつけた判定です。記録の後に行が変わると「再確認が要る」になります。ハッシュはその行の値だけを見ます（参照するトークン種別・ホップの行、25 問の回答、design.md の本文を変えても再確認にはなりません）。

| 行 | 判定 | 日時 | 今の行との対応 | コメント |
| --- | --- | --- | --- | --- |
| claims:C-aud | 保留（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（4a8171179b6a） | Okta・Auth0 は aud が共通で、宛先の区別を scope に頼る（R2-17） |
| claims:C-auth0-employee-number | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（d8381ce529db） | B22 |
| claims:C-auth0-plain-roles | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（c8c9effd43b0） | B20 |
| claims:C-auth0-roles | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（978f2163781b） | consumer\_access\_path・value\_normalization・registered\_ref が無い（R2-14） |
| claims:C-azp | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（151cfbd879ea） | Entra の AT の azp を照合する行が無く H3 でも照合しない（R2-01） |
| claims:C-client-id | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（2abb07e7535a） | — |
| claims:C-cnf | 保留（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（b881ecd55bee） | B23 の見送り。BFF → 入口の mTLS の比較（R2-02）と専門家の判断を待つ |
| claims:C-cognito-custom-role | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（ad58d96fcdfc） | B18 |
| claims:C-department | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（c35d253dfeeb） | B11・B15 の守りとして妥当（value\_normalization の欠けは R2-14） |
| claims:C-email | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（cfd68be168c2） | 要求の 7. の 9 の決定 |
| claims:C-employee-id | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（07b80de7c5af） | B22 の守りとして妥当（R2-15 は目録の側） |
| claims:C-events | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（8e20e4d720c2） | — |
| claims:C-exp | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（96e6963be2b2） | — |
| claims:C-groups | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（7e2ad16cb4f9） | Okta はグループの名前で写す（R2-05）、Okta の件数の上限（R2-13）、Graph のキャッシュ（R2-12） |
| claims:C-iat | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（f5d07a42f623） | ログアウトの時刻を社員台帳に書く経路が図・ホップに無い（R2-08） |
| claims:C-idp-department | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（4f8724cea133） | B11・B15 |
| claims:C-iss | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（9e234424cd06） | — |
| claims:C-jti | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（d6f46850ae6f） | 経理台帳の jti の 1 回だけの受け入れの共有の記録先と再試行の扱い（R2-10） |
| claims:C-nonce | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（8fe666c56c8f） | — |
| claims:C-roles | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（88d3bcdc427c） | ロールの出どころが 5 つの IdP の管理の範囲の和になる（R2-04）、異動での剥奪の経路（R2-06） |
| claims:C-scope | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（1fe083b950ec） | Okta・Entra の scp が台帳の行に無いのに、B3 の守りを scp に頼る（R2-03） |
| claims:C-sid | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（17b95c809bfc） | — |
| claims:C-sub | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（2ae2c73da9e9） | issuers に Entra・Okta の iss があるが carried\_in に ENTRA\_AT・OKTA\_AT が無い（R2-20）。oid・tid・uid の行が無い（R2-03） |
| claims:C-sub-unread | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（71bfaca5e25b） | L11 の warn は既定どおりの行として理解できる |
| hops:H1 | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（a8105b8db7cf） | — |
| hops:H10 | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（c47d97e890d1） | — |
| hops:H11 | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（7538119156f9） | — |
| hops:H12 | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（f37a768a1c05） | — |
| hops:H13 | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（5afec5e49d2d） | — |
| hops:H2 | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（9ec5601c4d15） | BFF を直接の相手として確かめない（R2-02）、ヘッダーの許可リスト（R2-11） |
| hops:H3 | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（1e59a5824373） | azp（クライアント）を照合しない（R2-01）、R2-02、R2-11 |
| hops:H4 | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（79d665b74698） | groups の名前による写し（R2-05）、R2-02、R2-11 |
| hops:H5 | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（a1df7f8f2370） | R2-02、R2-11 |
| hops:H6 | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（9fd3435223d8） | R2-02、R2-11 |
| hops:H7 | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（1cde20c8bb73） | upstream を外した（R2-23）、forwarded\_headers が無い（R2-11） |
| hops:H8 | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（0eb9bc4fa1f2） | upstream を外した（R2-23）、jti の運用（R2-10） |
| hops:H9 | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（dda884631f07） | — |
| token\_types:AUTH0\_AT | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（a9d9cfd04af8） | — |
| token\_types:AUTHORIZATION\_CODE | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（2ab8685d374c） | — |
| token\_types:BFF\_SESSION | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（665cbd72e672） | ログアウトで社員台帳に書く経路（R2-08） |
| token\_types:CLIENT\_ASSERTION | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（5759815bdff3） | — |
| token\_types:COGNITO\_AT | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（3fcbfee7028e） | required\_claims が空（token\_use・client\_id・sub を宣言していない。R2-03） |
| token\_types:DPOP\_PROOF | 保留（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（e4286f67c9c5） | B23 の見送り（R2-02、専門家） |
| token\_types:ENTRA\_AT | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（e08e7ba1588a） | azp の照合（R2-01）、required\_claims に oid・tid が無い（R2-03）、寿命・版の前提（R2-09） |
| token\_types:GRAPH\_AT | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（94dcae1673e2） | キャッシュの寿命を AT の残りの寿命にしている（R2-12） |
| token\_types:IDP\_SESSION | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（ed1e92f58bd5） | — |
| token\_types:ID\_JAG | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（b13b8951f127） | — |
| token\_types:ID\_TOKEN | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（eb8cba0dae55） | — |
| token\_types:INTERNAL\_TOKEN | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（58d4af9deaf6） | required\_claims と H7 の食い違い（R2-15）、jti の運用（R2-10）、署名鍵の保護（R2-18） |
| token\_types:INTROSPECTION\_JWT | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（d612a03e766c） | — |
| token\_types:JARM\_RESPONSE | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（4f6774de3c6b） | — |
| token\_types:JAR\_REQUEST\_OBJECT | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（f36f1756fc7f） | — |
| token\_types:KC\_AT | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（c100bfbfabaa） | — |
| token\_types:LOGOUT\_TOKEN | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（0d8a9cf20c1c） | — |
| token\_types:OKTA\_AT | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（1c326387bba6） | required\_claims に uid・cid が無い（R2-03）、groups の件数（R2-13） |
| token\_types:REFRESH\_TOKEN | 修正を求める（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（71393c5f50c5） | rt\_strategy の根拠が公開クライアント向け（R2-22。issuance\_profile の側） |
| token\_types:SET | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（c9297d14b5ed） | Keycloak 以外の IdP 側のログアウトは 12. に記載 |
| token\_types:STATUS\_LIST | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（d283e9049b34） | — |
| token\_types:TXN\_TOKEN | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（e3764cb5f844） | — |
| token\_types:WORKLOAD\_JWT | 承認（LLM） | 2026-11-24T07:40:00+09:00 | 一致（記録のときのまま）（82d57b062621） | — |

計 60 行：承認 35・修正を求める 22・保留 3。再確認が要る 0・台帳に無い 0

## 10. 補足（手で書いた節。review.yaml からは生成しない）

**LLM によるレビュー。人による検証ではない。**

### 10.1 理由の採点の追加分（procedure.md の段 4 の「採用・却下からそれぞれ 5 件」に合わせる）

review.yaml の抜き取りは道具の上限（3 件）で、却下の行 3 件だけ。手順の 5 件に足りない分と、採用の行 5 件を手で選んで採点した（選んだ行の ID をここに書く。乱数ではない）。引用元（スライド・仕様）は開いておらず、RR4 は引用の名前と主張が合うかだけを見た。

| 行の ID | 採否 | RR1 | RR2 | RR3 | RR4 | RR5 | RR6 | RR7 | 合否 | 要求（brief-B）への対応 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C-email | 却下（不要） | 満 | 満 | 満 | 満 | 満 | 満 | 満 | 合格 | 7. の 9（個人情報の表示は出典に無い）を「表示しない」と決め、見直しの条件あり |
| C-auth0-employee-number | 却下（禁止） | 満 | 満 | 満 | 満 | 満 | 満 | 満 | 合格 | 2. の Auth0 の行「社員番号を数値として出す」、B22、7. の 7 |
| C-sub | 採用 | 満 | 満 | 満 | 満 | 満 | 満 | 否 | 不合格 | B13・B14、2. の Okta（sub は再利用・uid は不変）と Entra（oid＋tid）の行。RR7：issuers に Entra・Okta があるのに carried_in に無い（R2-20） |
| C-groups | 採用 | 満 | 満 | 満 | 満 | 満 | 満 | 満 | 合格 | B8・B9、7. の 8、2. の Entra の行（上限 200 で groups が消え _claim_names が入る）。ただし Okta の名前による写しは R2-05 |
| C-department | 採用 | 満 | 満 | 満 | 満 | 満 | 満 | 満 | 合格 | 3. の社内文書（sales か finance）、B11・B15、7. の 3・6 |
| C-roles | 採用 | 満 | 満 | 満 | 満 | 満 | 満 | 満 | 合格 | 3. の admin・edit、B18・B19・B20、7. の 6。approver の操作は要求に無い（R2-19） |
| C-employee-id | 採用 | 満 | 満 | 満 | 満 | 満 | 満 | 満 | 合格 | 3. の給与明細（社員番号で本人の明細）、B22、7. の 7 |

合計（6. の 3 件を含む）：却下 5 件 合格 5、採用 5 件 合格 4・不合格 1（C-sub、RR7）。

### 10.2 要求（brief-B）の脅威と正規の利用の対応（攻撃者の視点で最初に確かめた）

| 要求 | 設計の守り | レビュアーの見立て |
| --- | --- | --- |
| B1・B14・B16・B21（受け付け） | H2・H4・H5・H6 の validates、C-sub・C-client-id | 受けられる。B16 は client_id＋token_use |
| B9（受け付け）／B8（拒否） | C-groups の Graph の解決 | 両立する。Graph の障害で B9 が落ちる（3.1 に記載）、キャッシュの寿命は R2-12 |
| B2・B17 | aud・azp・token_use・typ | 守れる |
| B3 | aud（Keycloak・Entra）、scope（Okta・Auth0） | Okta・Auth0 は scope 頼み（R2-17）、Okta の scp は台帳に無い（R2-03） |
| B4〜B6 | 入口でヘッダーを捨て、サービスは内部トークンだけを読む | 目標の状態では守れる。否定のリスト（R2-11）、移行の間は開く（R2-07） |
| B7 | メッシュの mTLS＋内部トークン | 目標の状態では守れる。移行の間は開く（R2-07） |
| B10 | 自社の tid の iss だけ | 守れる |
| B11 | invoices が経理台帳の要求ごとに社員台帳を引く | 守れる（遅れ 0）。ロールの側の異動は R2-06 |
| B12 | iat と社員台帳のログアウトの時刻、経理台帳の jti の 1 回だけ | 書き込みの経路が未設計（R2-08）。Keycloak 以外の IdP 側のログアウトは 12. に記載 |
| B13 | Okta は uid で名寄せ | 守れるが uid の行が台帳に無い（R2-03） |
| B15 | 部署を社員台帳から引く、無ければ拒む | 守れる |
| B18 | custom:* を読まない | 守れる |
| B19・B20 | 欠けたロールは空、既定値を使わない | 守れる（生成の表のクレーム名の食い違いで同じ結果が起きうる：R2-16） |
| B22 | 社員番号を社員台帳から文字列で | 守れる |
| B23 | 見送り | BFF → 入口の mTLS の比較が無い（R2-02）。書き手の希望どおり専門家に回す（下の 10.4） |

### 10.3 時間の記録（壁時計、JST）

| 区間 | 開始 | 終了 | 中身 |
| --- | --- | --- | --- |
| 全体 | 2026-11-24 07:08:15 | 2026-11-24T07:22:11+09:00 | 段 0〜7 |
| 攻撃者・運用を先に読む（要求の脅威 → 設計書 → hops → 目録 → 台帳） | 07:08 | 07:13 | 範囲の図・12.・3.1・ホップの表を読みながら、要求の B1〜B23 と本番の障害（IdP の停止・異動・退職・ヘッダー・複数の IdP）を当てた |
| 一覧の外（テンプレート外・カタログ外の質問） | 07:08〜07:13 の読みと並行、07:17〜07:18 に単独で 1 回 | — | 単独の時間として区切れたのは約 1 分（R2-24 の試験の経路を足した）。読みと並行した分は分けて測っていない。推定で合計 4〜5 分 |
| 観点書の 168 問への回答・行の判定・記録の生成 | 07:13 | 07:21 | review.yaml を書き、review_record check（OK）と report で生成 |

一覧の外の範囲：要求の 2.（5 つの IdP の癖）・5.（脅威）・7.（あいまいな点）を出発点に、(a) 複数の IdP の管理者とアカウントの組み合わせ、(b) 移行の旧経路、(c) 範囲の図に無い書き込みの経路、(d) 再送・複数台の運用、(e) ヘッダーの名前の変種以外の偽装と重複、(f) IdP の設定の前提が崩れたときの全停止、(g) 試験の経路、(h) render の出力と台帳の食い違い。出どころが「テンプレート外」の指摘は R2-04・R2-09・R2-10・R2-11・R2-16・R2-19 の 6 件、「カタログ外の質問」は R2-07・R2-24 の 2 件。

### 10.4 基準の外で専門家に回すもの

| 行・欄 | 回す先 | 理由 |
| --- | --- | --- |
| C-cnf・DPOP_PROOF・issuance_profile.sender_constraint（B23 の見送り） | 組織の認証基盤の担当 | escalation.md の基準には当たらないが、書き手が 12. で「専門家に回す」と求め、R2-02 の代替の比較も要る |

### 10.5 守ったこと

- 読まなかったもの：設計のディレクトリの author-log.md、templates/examples/**、templates/casestudy-*、research/** の設計のディレクトリ以外、ケーススタディのリポジトリ・xlsx、PR #55 のコメント、ほかのレビュアー（R1）の出力、perspectives.md の 9.（較正。過去のレビューの指摘を含む）
- 設計のワークツリーには書いていない（claim_lint・row_hash・review_record の check・sample・report は読み取りだけ。git status で変更が無いことを確かめた）
