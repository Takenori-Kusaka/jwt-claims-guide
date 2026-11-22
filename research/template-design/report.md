# 「漏れゼロ」を約束せず、漏れを機械で見つける設計書テンプレートへ

この構想には価値がある。ただし価値の源泉は、構想が掲げる「レビューは採否理由の妥当性評価だけで済み、網羅性不足や発行/利用ケースの想定漏れが一切生じない」という約束ではない。この約束は原理的に証明できず、実証研究とも矛盾する。列挙されなかった候補はテンプレートでは検出できない。またレビューで最も見逃されやすいのは、データ真正性の検証不足（CWE-345、13/13 件見逃し）とアクセス制御の不備（CWE-284、約 88% 見逃し）で、どちらも JWT クレーム設計の中核にあたる（[Paul et al.](https://ar5iv.labs.arxiv.org/html/2102.06909)）。価値の源泉は三つある。第一に、ASVS 5.0 が要求しながら様式を定めていない「認可ドキュメント」（V8.1.1〜8.1.4）を具体化できる（[OWASP ASVS 5.0 V8](https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x17-V8-Authorization.md)）。第二に、「発行・利用のタイミング × 情報 × クレーム × データ源」の時系列対応表と採否根拠の一覧は、公開された先行事例が調査範囲で見つからなかった空白地帯にあたる。第三に、定義した列挙軸の内側では未記入を機械的に検出できる。修正すべき点は三つある。ファイルの分割軸を認可方式から「主体 × フロー」に移し、認可方式はモジュールに格下げする。発行イベントのマスターカタログを外部の一覧（IANA、IdP フックの契機値）から作る。トークンサイズのチェッカーは入れるべきで、宣言値から最悪ケースを静的に合算し、経路上で最も厳しい上限を超えたら error にする。約束の文言は「定義した軸の内側では判断漏れを機械的に検出し、軸そのものは外部の一覧と運用の実測で更新し続ける」に改めるのが、根拠に沿った表現である。

## 質疑：想定される疑問・反論・先行事例への回答

### Q1. 「全候補に採否と理由が付いていれば、網羅漏れは起こり得ない」と言えるか

言えない。テンプレートが保証できるのは「列挙された候補には判断が記録されている」ことまでで、列挙されなかった候補（unknown unknowns）には何も言えない。Dijkstra が 1969 年に述べた「テストはバグの存在を示せるが、不在は示せない」は、チェックリストにもそのまま当てはまる（[EWD288](https://www.cs.utexas.edu/%7EEWD/transcriptions/EWD02xx/EWD288.html)、[出典の整理](https://buttondown.com/hillelwayne/archive/testing-can-show-the-presence-of-bugs-but-not-the)）。脅威モデリングの第一人者 Shostack も、図のすべての要素に STRIDE を当てても「かなり良い」と言えるだけで、それは「すべてのドアと窓に鍵があることを確かめた」程度の意味しかないと書いている（[Shostack, MSDN 2008](https://learn.microsoft.com/en-us/archive/msdn-magazine/2008/july/security-briefs-reinvigorate-your-threat-modeling-process)）。要求工学の大規模調査 NaPiRE では、最も多く挙がった問題が「不完全な要求・隠れた要求」（ある分析では回答者の **48%**）で、主因は担当者の領域知識の不足だった（[arXiv 1612.00163](https://arxiv.org/pdf/1612.00163)）。領域知識の不足は様式では埋まらない。

医療のチェックリストの経験は、「全欄記入」が品質の指標にならないことを示している。WHO の手術安全チェックリストは 8 施設で死亡率を 1.5% から 0.8% に下げた（[Haynes et al., NEJM 2009](https://doi.org/10.1056/NEJMsa0810119)）。一方、オンタリオ州の 101 病院で義務化した際は、ほぼ全病院が約 100% の遵守を報告したにもかかわらず、死亡率の改善は有意でなかった（0.71% → 0.65%、OR 0.91）（[Urbach et al., NEJM 2014](https://pubmed.ncbi.nlm.nih.gov/24620866/)、[PSNet](https://psnet.ahrq.gov/issue/introduction-surgical-safety-checklists-ontario-canada)）。したがって、「漏れゼロ」という約束は撤回し、次の文言に置き換えるべきである。

> **修正後の約束（案）**：本テンプレートは、定義した列挙軸（発行イベントカタログ × 段階 × 受け手 × トークン種別）の内側で、判断の未記入・根拠の欠落・データ源の不明を機械的に検出する。列挙軸の外にある漏れは、観点別の問い、カタログ外を問う必須質問、流出欠陥のふりかえりで見つけ、見つけた漏れはカタログに還流する。レビューの主眼は採否理由の妥当性評価に置くが、それだけでは終わらない。

### Q2. レビューを「採否理由の妥当性評価だけ」に絞ってよいか

主眼を置くのはよいが、「だけ」にするのは危険である。焦点を示す効果は大きい。150 名の実験では、「セキュリティに注目せよ」と明示するだけで脆弱性の検出確率が **8 倍**になった。同じ実験で、セキュリティチェックリストは検出を増やさなかった（[Braz et al., ICSE 2022](https://arxiv.org/abs/2202.04586)）。インスペクション研究全体でも、チェックリスト型がアドホック型より頑健に優れるという証拠はない（[Porter, Votta, Basili 1995](https://www.cs.umd.edu/~aporter/html/scenarios.html)、[Ciolkowski 2009](https://researchr.org/publication/Ciolkowski09)）。70 名のコードレビュー実験では、成績を最も左右したのは対象の理解だった（[Gonçalves et al., EMSE 2022](https://link.springer.com/10.1007/s10664-022-10123-8)）。

ここから導ける位置づけは次のとおりである。テンプレートの価値は「チェック項目の網羅」ではなく、候補・採否・理由・前提という構造化された情報をレビュアーに渡し、理解を助けることにある。「理由だけを見よ」と注意を狭めると、焦点の外にある鍵管理、受け渡し経路、キャッシュを見なくなる。さらに、もっともらしく書かれた理由を追認するだけで、実装や設定が本当にそうなっているかを確かめない（rubber-stamping）おそれもある。対策は二つある。記述と実装の一致の確認は、スキーマ検証と契約テストで機械に任せる。人間には、却下理由から無作為に 2〜3 件を選んで実装まで追う深掘りと、カタログ外を問う質問を課す。

### Q3. 認可方式（RBAC / ABAC / ReBAC）別にファイルを分けるのは妥当か

主軸としては勧めない。理由は三つある。

第一に、実システムの大半はハイブリッドである。NIST は純粋な RBAC では動的属性を扱えずロール爆発が起きると指摘している（[Kuhn, Coyne, Weil 2010](https://www.nist.gov/publications/adding-attributes-role-based-access-control)）。SP 800-162 の ABAC の定義自体にも「関係」が含まれている（[NIST SP 800-162](https://csrc.nist.gov/pubs/sp/800/162/upd2/final)）。製品も同様で、OpenFGA は ReBAC を RBAC の上位集合とし、Conditions で ABAC を併用する（[OpenFGA](https://openfga.dev/docs/authorization-concepts)）。AWS Verified Permissions は、同じポリシーストアで `groups` による RBAC と属性による ABAC を共存させる（[AWS](https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/identity-sources.html)）。認可方式別にファイルを分けると、1 システムで 2〜3 本を同時に埋めることになり、共通部分を各ファイルに複製することになる。

第二に、認可方式はトークンの中身をあまり変えない。RFC 9068 が認可クレームとして挙げるのは `groups`・`roles`・`entitlements` と `scope` に限られる（[RFC 9068](https://www.rfc-editor.org/rfc/rfc9068.html)）。関係や変わりやすい属性はトークンに入れず、PDP に問い合わせるのが各社に共通する指針である。トークン内のグループ情報は「取得時点でのみ最新」とされる（[Microsoft Learn](https://learn.microsoft.com/en-us/security/zero-trust/develop/configure-tokens-group-claims-app-roles)）。Zanzibar の設計目標である因果順序の保証は、関係をトークンに焼き込む方式とは両立しない（[Google Research](https://research.google/pubs/pub48190/)）。認可方式によって変わるのは、主に「載せないクレームの一覧」と「PDP 呼び出しのシーケンス」である。

第三に、シーケンス図の形を決めるのは別の軸である。主体の種類とグラントが変われば、同じ RBAC でもクレームの構成が根本から変わる。たとえば Auth0 の client credentials トークンはアプリを表すので、利用者のロールは入らない（[Auth0 Blog](https://auth0.com/blog/five-reasons-permissions-not-in-access-token/)）。Token Exchange（[RFC 8693](https://www.rfc-editor.org/rfc/rfc8693.html)）や Transaction Tokens（[Datatracker](https://datatracker.ietf.org/doc/draft-ietf-oauth-transaction-tokens/)）は、発行のタイミングそのものを 1 段増やす。PEP と PDP の間の API も、AuthZEN 1.0（2026-01 に Final）が認可方式によらない共通の形で定めている（[AuthZEN 1.0](https://openid.net/specs/authorization-api-1_0.html)）。

ガイド自身も、スライド 66「PEP と PDP：クレームは判断の入力の 1 つ」と 67「粗い権限と細かい権限：3 層で分担する」でハイブリッドを前提にしている。認可方式別のファイルは、このガイドの主張ともずれる。分割の先例としては、FAPI 2.0 の「必須プロファイルに選択肢と追加文書を足す」構成（[FAPI 2.0](https://openid.net/specs/fapi-security-profile-2_0-final.html)）や、ASVS の累積レベル制（[OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/)）に倣うのがよい。「共通コア + 主体×フローのプロファイル + 横断モジュール」にし、認可方式は `M_authz_pdp` モジュールの中の決定項目にする。

### Q4. シーケンス図とタイミング毎の対応表で、発行・利用のケースは閉じるか

ケースの母集団を外部の一覧から作れば、少なくとも製品と標準の範囲では閉じた列挙に近づく。作らなければ閉じない。列挙の種として最も機械的に使えるのは、IdP のフックが受け取る契機の値の一覧である。Auth0 の post-login Action の `event.transaction.protocol` は **16 値**ある（[Auth0](https://auth0.com/docs/customize/actions/explore-triggers/signup-and-login-triggers/login-trigger/post-login-event-object)）。M2M は別のトリガー `credentials-exchange` が扱うので、post-login でのクレーム付与は M2M に効かない（[Auth0 M2M trigger](https://auth0.com/docs/customize/actions/explore-triggers/machine-to-machine-trigger)）。Cognito の `triggerSource` は **6 値**で、client credentials はフックのバージョンが V3_0 のときだけ送られる。また `sub`・`acr`・`amr`・`auth_time` などはフックで変えられない（[AWS Cognito](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-pre-token-generation.html)）。標準側では、IANA の grant type・token type・response type の登録（[IANA OAuth Parameters](https://www.iana.org/assignments/oauth-parameters/oauth-parameters.xhtml)）と、OIDC の各ログアウト仕様が種になる。

これらから作ったカタログ（発行約 30、利用約 20）を本ガイド（`docs/slides.json`、152 枚）と突き合わせると、扱いの薄いイベントがある。

| 区分 | ガイドにない（キーワード 0 件）または言及のみのイベント | 事故の型 |
|---|---|---|
| 発行 | サイレント再認証（`prompt=none`） | auth_time が古いまま、acr は前回の値 |
| 発行 | テナント・組織の切り替えによる再発行 | 切り替え後も古い tid が残る |
| 発行 | サインアップ・招待・初回ログイン | 所属が未確定のまま発行される、email_verified=false |
| 発行 | パスワード変更・MFA 登録の後の発行 | amr とセッションの扱いが曖昧になる |
| 発行 | device flow（[RFC 8628](https://www.iana.org/assignments/oauth-parameters/oauth-parameters.xhtml)） | 入力した端末と承認した端末が別 |
| 発行 | Back-Channel Logout の Logout Token | `events` が必須、`nonce` は禁止（[OIDC Back-Channel Logout 1.0](https://openid.net/specs/openid-connect-backchannel-1_0.html)） |
| 発行 | client credentials のフックが別系統であること（△） | 利用者向けフックのクレームが M2M に付かない |
| 利用 | RP-Initiated・Front-Channel・Back-Channel ログアウト（△） | ログアウト後もトークンが有効なまま |
| 利用 | 長時間接続（WebSocket・gRPC ストリーム・SSE） | 接続の途中で期限が切れる |
| 利用 | 分析基盤へのクレームの複製 | 機微なクレームが下流に残る |

表の上の四つは、いずれも「スライド 76 の段階②（発行時フック）が動くか、動いたときにクレームが変わるか」で事故になる。ガイドの主題である独自クレームの鮮度と書き手に直結するので、テンプレートより先にガイドの側を補うべき優先度が高い。カタログには、禁止しているフロー（implicit、ROPC）も「対象外：RFC 9700 で非推奨」という行として残す。暗黙の対象外をなくすためである。

### Q5. 「データ源」の列には何を書けば、鮮度の問題に答えたことになるか

元のシステムの名前を書くだけでは足りない。NISTIR 8112 は属性のメタデータとして「確認の方法」（document verification、record verification、not verified など）と「最終確認の時刻」を定義している（[NISTIR 8112](https://nvlpubs.nist.gov/nistpubs/ir/2018/nist.ir.8112.pdf)）。SP 800-63C-4 は、元の値を含まずに限られた事実だけを表す派生属性値（「18 歳以上」など）を定義している（[SP 800-63C-4 用語集](https://pages.nist.gov/800-63-4/sp800-63c/glossary)）。ASVS 8.3.2 は、自己完結型トークンが認可入力の変更を即時に反映できない場合に、検知と巻き戻しの緩和策を求めている。この要件に答えるには、データ源の列に「反映の遅れ」と「再計算の契機（ログイン時のみか、リフレッシュ時もか）」が必要になる。後者は Q4 の契機値の一覧と結合して初めて埋まる。ガイドのスライド 134 の台帳 12 項目は、すでに「鮮度」と「持ち主」を持っている。足りないのは「確認の方法」「最終確認」「再計算の契機」と、段階の列との結合である。データ源の変更はそれ自体がレビューの契機になる（[Shostack](https://learn.microsoft.com/en-us/archive/msdn-magazine/2008/july/security-briefs-reinvigorate-your-threat-modeling-process)）ので、データ源の列は変更検知の起点としても機能する。

### Q6. 採否チェックリストに却下候補と理由の例を事前に載せると、形骸化しないか

形骸化のリスクは高い。OSS の ADR 約 5,800 件のうち約 **63%** が最初から "accepted" の状態で作られており、本来記録すべき熟議を経ていない（[ICSA 2026](https://conf.researchr.org/details/icsa-2026/icsa-2026-papers/34/Architecture-Decision-Records-Adoption-Impact-and-Developer-Engagement-in-Open-Sou)）。Parnas と Clements は、設計文書は本質的に事後の再構成であると認めたうえで、合理的に導かれたかのように書くべきだと主張した（[IEEE TSE 1986](https://doi.org/10.1109/TSE.1986.6312940)）。例示した理由はアンカーになり、そのまま転記される（[Tversky & Kahneman 1974](https://doi.org/10.1126/science.185.4157.1124)）。QOC の研究は、設計根拠の記録が未知の設計空間では有効で、制約の強い定型の空間ではむしろ邪魔になると報告している（[KMi](https://kmi.open.ac.uk/publications/techreport/kmi-95-13)）。

緩和策は四つある。カタログには候補と検討の問いだけを載せ、模範の理由文は載せない。既定どおりの項目（`aud` の必須検証など）は一括で宣言させ、理由は逸脱と却下にだけ求める（[Falessi et al. の価値ベース原則](https://art.torvergata.it/bitstream/2108/57813/1/2008_WICSA_FCK_Value-Based%20Design%20Decision%20Rationale%20Documentation%20Principles%20and%20empirical%20feasibility%20study.pdf)と整合する）。理由には「脅威・要件 ID への参照」「前提条件」「前提が崩れたときの再検討トリガー」のうち最低 2 つを含めさせる。理由文の重複率を lint で測る。ただし、これらの緩和策の効果を直接測った研究は見つかっておらず、いずれも設計上の提案にとどまる。

### Q7. 先行事例はあるか。車輪の再発明ではないか

部品ごとには先行事例があり、組み合わせは新しい。検証要件は ASVS V8/V9/V10、RFC 8725/9700/9068、FAPI 2.0 にほぼ揃っている（[ASVS V9](https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x18-V9-Self-contained-Tokens.md)、[ASVS V10](https://raw.githubusercontent.com/OWASP/ASVS/master/5.0/en/0x19-V10-OAuth-and-OIDC.md)、[FAPI 2.0 Attacker Model](https://openid.net/specs/fapi-attacker-model-2_0-final.html)）。決定記録の様式は MADR の Decision Drivers / Considered Options / Outcome（[MADR](https://adr.github.io/madr)）にある。レジストリの列は、IANA の JWT Claims 登録テンプレート（[IANA](https://www.iana.org/assignments/jwt/jwt.xhtml)）と、ODCS の ownership・quality・SLA（[ODCS](https://bitol-io.github.io/open-data-contract-standard/latest/)）から借りられる。「利用者の区分ごとに、どの属性をどの情報源から出すか」を宣言的に管理する先例としては、REFEDS R&S の属性バンドルと属性リリースポリシーがある（[REFEDS R&S](https://refeds.org/research-and-scholarship)）。

ベンダーの文書は「どう設定するか」と「何をしてはいけないか」が中心である。Curity はトークンを「認可サーバーと消費者の間の契約」とし、どのクレームを入れるかを統制するプロセスが必要だと述べているが、その様式は示していない（[Curity](https://curity.io/blog/managing-scopes-and-claims-in-oauth-tokens/)）。ASVS 8.1 も、何を文書化すべきかは示すが、どう書くかは規定していない。認可方式（主体×フロー）別の設計書、時系列の段階×クレームの対応表、クレームごとのデータ源と鮮度、採否根拠の一覧、根拠の妥当性を判定するレビュー報告の五つは、今回の調査範囲では公開された先行事例が見つからなかった。最大のリスクは「独自様式」と見なされることである。各テンプレートに「満たす ASVS 要件 ID」の欄を設け、レビュー観点は独自の項目を作らず既存の ID に対応づけるべきである。

### Q8. 重すぎて誰も使わないのではないか

その懸念には根拠がある。ADR を始めたリポジトリの約 **50%** は 5 件未満で止まっている（[arXiv 2604.03826](https://arxiv.org/html/2604.03826)）。設計根拠の記録が普及しない理由としては、「便益が遅れて来る」ことと「記録する人と受益する人が別」であることが挙がっている（[Falessi et al.](https://art.torvergata.it/bitstream/2108/57813/1/2008_WICSA_FCK_Value-Based%20Design%20Decision%20Rationale%20Documentation%20Principles%20and%20empirical%20feasibility%20study.pdf)）。対策は二段のテーラリングである。Lite は、既存パターンを踏襲する単一リソースサーバーの内部 API 向けで、逸脱だけを記録し、カタログ外の質問を 3 つ課す。Full は、新規発行者、外部 RP、マルチテナント、委任・トークン交換、規制対象のいずれかに当てはまる場合で、全候補の列挙、観点別レビュー、サンプリング深掘りを行う。どちらにするかの判定基準はテンプレートの冒頭に置く。機械で確かめられる部分（必須欄、証拠リンク、契機値との差集合、サイズ）は CI に移し、人の記入量を減らす。

### Q9. 採用クレームが多すぎる、または値域が大きすぎてトークン容量の制限を超える場合に、エラーにするチェッカーを設けるべきか

設けるべきである。理由は三つある。

第一に、経路上のサイズ上限は数 KB 単位で、製品ごとにばらばらである。Cookie は名前と値の合計が 4096 octets を超えると無視される（[RFC 6265bis](https://httpwg.org/http-extensions/draft-ietf-httpbis-rfc6265bis.html)）。nginx の既定値はヘッダー 1 行あたり 8 KB で、超えると 400 を返す（[nginx](https://nginx.org/en/docs/http/ngx_http_core_module.html)）。API Gateway（REST）は全ヘッダーの合計が 20,480 bytes で、private API では 8,000 bytes である（[AWS](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-execution-service-limits-table.html)）。Envoy の既定値は 60 KiB で、超えると 431 を返す（[Envoy](https://www.envoyproxy.io/docs/envoy/latest/api-v3/extensions/filters/network/http_connection_manager/v3/http_connection_manager.proto)）。IdP 側では、Entra の `groups` は JWT で 200 件まで（超えると overage に切り替わる）（[Microsoft Learn](https://learn.microsoft.com/en-us/security/zero-trust/develop/configure-tokens-group-claims-app-roles)）、custom claims provider は合計 3 KB まで（[Entra reference](https://learn.microsoft.com/en-au/Entra/identity-platform/custom-claims-provider-reference)）、Cognito は 1 属性 2,048 bytes、グループは 1 ユーザー 100 件までである（[Cognito quotas](https://docs.aws.amazon.com/cognito/latest/developerguide/quotas.html)）。

第二に、上限を超えたときの挙動が「黙って消える」「400・414・431 を返す」「overage に切り替わる」とばらばらで、障害の原因が分かりにくい。ガイドのスライド 56「サイズの予算：上限を超えると黙って消える」が警告しているのはこの点である。

第三に、規模の感覚として、Entra の上限いっぱいの 200 件の GUID を配列にするとペイロードは約 7.8 KB になり、base64url で約 10.4 KB になる（JWS Compact の構成は [RFC 7515](https://www.rfc-editor.org/rfc/rfc7515.html)、4/3 倍の膨張は [RFC 4648](https://www.rfc-editor.org/rfc/rfc4648.html)）。これだけで nginx の既定値と Cookie 1 個の上限を超える。この試算はノート作成者によるものである。

ただし、何でも error にすると誤検知で運用が嫌われる。判定は三段に分けるのがよい。

- **error**：最悪ケースのサイズが、そのトークンが通る経路で最も厳しい上限を超える場合。上限を持たない配列クレームがある場合（値域が無制限のまま）。IdP の件数上限を超えうるのに、超過時の方針が未宣言の場合。
- **warn**：最悪ケースが予算の 50〜75% を超える場合。DPoP の `cnf` や `act` の入れ子など、将来の追加の余地を残すためである。
- **info**：同じクレームが ID トークンにもアクセストークンにも載っている場合（重複の候補）。

error のメッセージからは `M_authz_pdp` モジュールの「載せるか、問い合わせるか」の判断表（スライド 47）へ誘導する。サイズ超過の主な解決策は、クレームを載せずに PDP や UserInfo に問い合わせること、または OIDC Core §5.6.2 の Aggregated / Distributed Claims による overage（[OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html#AggregatedDistributedClaims)）である。切り詰め（truncate）は方針として禁止する。

限界も明記しておく。静的チェッカーは宣言値を信じるので、宣言と実態のずれは捕まえられない。発行された実トークンを CI や監視で計測する動的チェックと組み合わせ、スライド 144「台帳と実際の発行のずれを測る」と結合する必要がある。また「クレーム台帳から最悪ケースを合算して予算と比べる静的チェッカー」の直接の先例は見つからなかった。近いのは、発行済みの NATS のアカウント JWT を検査する Synadia の「excessive JWT size」チェック（既定のしきい値 64 KiB、CI での検査を推奨）である（[Synadia](https://www.synadia.com/insights/checks/nats-excessive-jwt-size)）。

### Q10. レビューレポートには何を残せば、テンプレートの価値を測れるか

指摘の数ではなく、指摘の「起点」と「流出」を記録する。インスペクションの基本は、異常のリストとアクション項目のリストである（[NASA SWEHB](https://swehb.nasa.gov/x/BQT7)、[IEEE 1028 概要](https://ieeexplore.ieee.org/document/4601584)）。これに独自の欄を加える。「どのテンプレート項目・観点・質問から見つかったか、またはテンプレートの外か」を示す起点と、「理由不備・前提誤り・実装乖離・候補漏れ」を示す種別である。Chromium 研究が使った、検出された欠陥と流出した欠陥を比べるケース対照の考え方（[Paul et al.](https://ar5iv.labs.arxiv.org/html/2102.06909)）を当てはめると、レビュー後に見つかった欠陥は二つに分けられる。テンプレートに候補として存在したものは「理由判定の失敗」、存在しなかったものは「カタログの穴」である。「テンプレート外」の指摘の比率は二方向に読める。高ければカタログが不足しており、ゼロが続けばレビュアーが枠の外を見ていない兆候である。これらの指標が、Q1 の修正後の約束を継続的に反証し、改善する唯一の手段になる。

### Q11. LLM や自動化でレビューそのものを置き換えられないか

一次スクリーニングには使えるが、置き換えはできない。セキュリティコードレビューで LLM が静的解析を上回ったという報告がある（[Yu et al.](https://arxiv.org/html/2401.16310v5)）。一方、プロジェクト規模の検証では誤検出が多く、385 件の報告の人手確認に 150 時間超を要した（[Li et al.](https://arxiv.org/html/2601.19239v1)）。設計文書を対象にした LLM レビューの評価は見つからなかった。LLM には「理由が前提と矛盾していないか」「カタログ外の候補はないか」の下読みをさせ、その指摘もレビューレポートの起点欄で「LLM」と区別して記録し、有効率を測るのが妥当である。

## 価値評価：境界を越える契約では高く、定型の内部 API では儀式になる

構想全体の価値は、適用条件によって大きく変わる。設計根拠の記録が効くのは、後から「なぜ」を問われる場面である。保守課題では、設計者の質問の約 50% が意思決定の理由に関するものだった（[Tang 博士論文](https://researchbank.swinburne.edu.au/file/198ab8bf-fbaa-422b-bd24-2ecf7d23aa0c/1/Antony%20Tang%20Thesis.pdf)）。JWT のクレームは外部の RP や RS との契約で、変更は破壊的になりうる（[Curity](https://curity.io/blog/managing-scopes-and-claims-in-oauth-tokens/)）ので、この便益は通常の内部設計より大きい。逆に、定型の設計に全列挙を課すと、理由はコピペになり、記入率が KPI になればオンタリオ型の形式的遵守に陥る。

| 観点 | 高価値になる条件 | 低価値・逆効果になる条件 |
|---|---|---|
| 適用対象 | 組織・チームの境界を越えるトークン、複数 RS、マルチテナント、委任・トークン交換・step-up、エージェント | 単一サービス内部の API で、カタログの既定どおりの設計 |
| 記録の仕方 | 既定は一括宣言、逸脱と却下のみ理由必須、証拠リンク必須 | 全項目に理由を書かせ、模範文を載せる |
| 機械検証 | 台帳が機械可読で、スキーマ・lint・契約テスト・サイズチェッカーが CI にある | 文書のみで、記述と実装の一致を誰も確かめない |
| レビュー | 理由の評価を主眼に、無作為の深掘りとカタログ外の質問を併用 | 「理由だけ見ればよい」と役割を限定する |
| 運用 | 流出欠陥とテンプレート外の指摘をカタログに還流し、発火しない項目を削る | 記入率を品質指標にし、結果がカタログに戻らない |

構成要素ごとの評価は次のとおりである。最も価値が高いのは、発行イベントカタログ × 段階 × クレーム × データ源の対応表である。ASVS 8.3.2 と 8.3.3 に直接答え、Q4 で示したガイドの空白も露わにする。次に高いのはサイズチェッカーで、実装コストが低く、誤りが静かに起きる障害を設計時に止められる。採否チェックリストは、前述の緩和策を入れれば中〜高、入れなければ形骸化する。レビュー観点書は、独自の項目を作ると低く、ASVS・RFC の ID への対応表と PBR 的な視点分割（発行者・検証者・攻撃者・運用）として作れば中である。ただし PBR がチェックリストに勝る保証はなく（[Ciolkowski 2009](https://researchr.org/publication/Ciolkowski09)）、視点分割の効用はレビュアー間の重複を減らすことにとどまる。認可方式別ファイルという分割軸そのものは、現案のままなら低い。

## 推奨する改訂構想：コア・プロファイル・モジュールと機械検証

### ファイル構成

```
templates/
  00_core.md                    # 共通: 発行者と受け手の一覧、登録クレーム検証、名前空間・型、
                                #   サイズ予算、ライフサイクル、プライバシー、ASVS 対応表、Lite/Full 判定
  catalog/
    issue_events.yaml           # 発行イベント I01〜（IANA・OIDC・採用 IdP の契機値から生成）
    use_events.yaml             # 利用イベント U01〜
    subject_state_matrix.md     # 主体の状態（招待・有効・停止・削除・テナント切替・権限変更・資格情報変更）
                                #   × トークン種別（AT/RT/ID/Txn/Logout）→ 発行/再計算/失効/影響なし
  profiles/                     # シーケンス図の形が変わる単位 = 主軸
    P1_human_web_bff.md         # 認可コード+PKCE、BFF/SPA、リフレッシュ、ログアウト
    P2_human_mobile_native.md
    P3_workload_m2m.md          # client credentials、mTLS、ワークロード ID、バッチ
    P4_ai_agent_delegation.md   # token exchange (act/may_act)、CIBA・人の承認、MCP
    P5_internal_propagation.md  # 入口での変換、Transaction Tokens、メッシュ、非同期
  modules/
    M_authz_pdp.md              # RBAC/ABAC/ReBAC/ハイブリッドの選択表、載せるか問い合わせるか、
                                #   PDP 呼び出しシーケンス (AuthZEN)、鮮度とキャッシュ
    M_multitenancy.md
    M_sender_constraint.md
    M_privacy_minimization.md
    M_idp_<IdP>.md              # 契機値一覧・上限値・書き換え不可クレームの差分
  registry/claims.yaml          # 台帳（正）。下表の列を持つ
  review/
    perspectives.md             # レビュー観点書（視点別の問い + ASVS/RFC ID 対応 + カタログ外質問）
    report_template.md          # レビューレポート
  tools/                        # schema・lint・契機値差集合・サイズチェッカー
```

各プロファイルには、シーケンス図、図の各メッセージに対応する「載るトークン × 確かめるクレーム × 書き手 × aud × 寿命」の表、経路上の上限値の既定（P1 なら Cookie 4 KB など）を持たせる。これは STRIDE-per-element（[Osterman](https://learn.microsoft.com/de-de/archive/blogs/larryosterman/threat-modeling-again-stride-per-element)）をクレームに当てはめたものである。

### 台帳（claims.yaml）の必須列

| 列 | 内容 | 由来 |
|---|---|---|
| name / namespace / type / shape | クレーム名、名前空間、型、形 | スライド 48〜53 |
| decision / rationale | 採用・却下・既定どおり。逸脱と却下のみ理由必須（参照・前提・再検討トリガーのうち 2 つ以上） | MADR、Falessi |
| issue_events / stage | 発行イベント ID（1 つ以上）、段階 ①〜⑥ | スライド 76、カタログ |
| writer | プラットフォーム・フック・入口・TTS | Cognito の書き換え不可クレーム |
| source_system / verification_method / last_verified | 元のシステム、確認の方法、最終確認 | NISTIR 8112 |
| propagation_delay / recompute_trigger | 反映の遅れ、再計算の契機（ログインのみ／リフレッシュでも） | ASVS 8.3.2 |
| carried_in / consumers / on_missing | 載るトークン種別と aud、読む受け手、欠落時の挙動（拒否） | スライド 57・58 |
| max_bytes / max_items / typical_items / overflow_strategy | サイズ計算の入力と超過時の方針（truncate 禁止） | Q9 |
| owner / change_controller / evidence / asvs_ids | 持ち主、変更管理者、検証コード・設定・契約テストへのリンク、対応する ASVS ID | スライド 134、IANA、ODCS |

### 自己点検ルール（CI で検査する）

| ID | ルール | 失敗時 |
|---|---|---|
| R1 | 台帳の全行で必須列が空でない | error |
| R2 | カタログの全発行・利用イベントに「該当」か「対象外＋理由」が書かれている（暗黙の対象外を禁止） | error |
| R3 | 採用 IdP の契機値一覧と、カタログの発行イベントの差集合が空である | error |
| R4 | 主体状態 × トークン種別の行列の全セルが埋まっている | error |
| R5 | どの受け手も読まないクレームがない／元のシステムのないクレームがない（双方向の追跡） | warn / error |
| R6 | 主体の種類 × 発行イベント × 段階の 2 因子の組をすべて一度は検討している（pairwise） | warn |
| R7 | 理由が空・定型文・他行と重複していない／証拠リンクが切れていない | warn |
| R8 | サイズチェッカー（下記） | error / warn / info |
| R9 | 「この列挙の外にある発行・利用の契機はないか」に領域の専門家が回答している | error（未回答） |

R6 は、NIST の組み合わせテストの知見による。障害の大半は単一因子か 2 因子の組み合わせで起きる（ある発表では 96%、1 種類のアプリケーションのデータ）（[NIST ACTS](https://csrc.nist.gov/projects/automated-combinatorial-testing-for-software/combinatorial-methods-in-testing/interactions-involved-in-software-failures)）。R9 は、Threat Modeling Manifesto の 4 つ目の問い「十分にうまくやれたか」（[Manifesto](https://www.threatmodelingmanifesto.org/)）を、空欄にできない欄として固定したものである。

### サイズチェッカーの仕様

トークン種別ごとのプロファイルに、署名アルゴリズム、ヘッダーの最大長、運搬経路（Authorization ヘッダー・Cookie・URL・キュー）を宣言させる。署名長は ES256 なら 64 octets、RS256（2048 bit）なら 256 octets である（[RFC 7518](https://www.rfc-editor.org/rfc/rfc7518.html)）。経路上の最小の上限を予算とし、payload = Σ（キー名 + 値の max_bytes × max_items + JSON の区切り）から、`ceil(4/3·header) + ceil(4/3·payload) + ceil(4/3·sig) + 2`（Bearer で運ぶなら +7）を最悪ケースとして計算する。計測の定義は、Auth0 と同じ「エンコード済み JWT 全体の UTF-8 バイト数」とする（[Auth0](https://support.auth0.com/center/s/article/auth0-id-token-size-calculation)）。判定は Q9 の三段で行い、発行された実トークンの計測による動的チェックと組み合わせる。

### レビューレポートの欄

レポートの冒頭には、対象の設計書の版、Lite か Full か、レビュアーと視点の割り当て、無作為に深掘りした却下理由の ID と確認結果、R1〜R9 の CI 結果を置く。指摘ごとに、指摘 ID、重大度（Blocker：偽造・権限昇格に直結／Major：誤検証の余地／Minor：記述・保守性）、対象（クレーム名・イベント ID）、起点（テンプレート項目・観点・カタログ外質問・テンプレート外・LLM）、種別（理由不備・前提誤り・実装乖離・候補漏れ）、判定（妥当・根拠不足・根拠が誤り）、対応、検証の証拠を記録する。末尾には、カタログ・観点書への還流事項を置く。これとは別に、レビュー後に見つかった欠陥を記録する流出欠陥ログを持つ。

## 未決事項と未検証点

先行事例の不在は、検索範囲内での結論にすぎない。Okta、Keycloak、Ping、Microsoft SDL、OWASP Threat Dragon にクレーム設計の様式がないことを一次資料で直接確かめたわけではなく、非公開の社内テンプレートは調べられない。ガイドとの突合はキーワード検索によるので、言い換えで扱っているスライドを「なし」と誤判定した可能性がある。特にサインアップ・招待と資格情報の変更後の発行は、ノート本文まで目視していない。IdP の挙動では、Okta の token inline hook がリフレッシュや client credentials でも動くか、Entra の custom claims provider がリフレッシュ時に呼ばれるか、OpenID Native SSO の現在の状態が未確認である。Okta の groups 100 件の上限は、サポート記事にはあるが公式の開発者ドキュメントでは確認できず、矛盾する報告もある。サイズ上限では、Tomcat、IIS/HTTP.sys、Node.js、Google Cloud LB、Azure Front Door の既定値が未確認である。HTTP/2・HTTP/3 のヘッダー圧縮下での実効上限、Auth0・Okta・Keycloak のトークン全体の上限（公表されていない可能性がある）も分かっていない。ガイドのスライド 110 が引く「ID-JAG 草案 06」は、検索で確認できた最新版（-05、2026-10）と食い違っており、datatracker での確認が必要である。

効果の面では、次の四つがいずれも見つからなかった。「採否根拠を記録するとレビューの欠陥検出率が上がる」ことを直接測った対照実験。設計文書に限ったセキュリティレビューの実験。却下候補を事前記入したテンプレートがアンカリングに与える影響の測定。理由のルーブリックとサンプリング深掘りの効果測定。本報告の高価値・低価値の条件と緩和策は、隣接領域（ADR、インスペクション、医療チェックリスト）の証拠からの推論である。P1〜P5 をどこまで別ファイルにするか（モバイルを P1 に統合するか、など）は、想定読者に依存し、根拠となる資料はない。

## 結論

この構想の本当の成果物は、テンプレートの束ではなく、外部の一覧に結びついた列挙の軸と、それを検査する CI である。「漏れゼロ」は約束できない。しかし、Auth0 の 16 値や Cognito の 6 値のように契機を列挙の種にすれば、「この IdP が動きうる契機のうち、台帳が判断していないもの」は差集合として機械的に出せる。人間のレビューは、その外側の領域知識と理由の真偽に集中させられる。サイズチェッカーは、この「宣言して機械で確かめる」方針を最も安く実証できる部品なので、着手の順序として最初に作る価値がある。

もう一つの示唆は、構想がガイド自体の改善装置になることである。カタログを作った時点で、テナント切り替え、招待、サイレント再認証、Logout Token、長時間接続という、ガイドの主題（独自クレームの鮮度と書き手）に直結する空白が見つかった。テンプレートを作る作業は、設計者の漏れを防ぐより先に、ガイドの漏れを見つける作業として元が取れる。運用に入ってからは、「テンプレート外で見つかった指摘」がゼロのまま続くことを成功ではなく警告として扱えるかどうかが、この活動が儀式に堕ちるかを分ける。
