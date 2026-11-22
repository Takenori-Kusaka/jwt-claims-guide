# 未検証点の一覧

[調査レポート](report.md)の「未決事項と未検証点」と、[調査ノート](notes/)の「未確認の点」から、確かめていない事実と、測られていない効果を集めた表です。

- 基準日：2026-11-22
- 作成方法：生成 AI（Claude）を使って作り、筆者が確認した。
- 点検の状況：人による点検は未実施。#13 の手順で点検する予定。
- 行の数：25 行。「対象外」として閉じた行は 0 件（0%）。
- 根拠の書き方：「確認先」の列は、[templates/CONTRIBUTING.md](../../templates/CONTRIBUTING.md) の根拠の種類（`spec`・`guidance`・`research` など）と ID の書式に合わせた。製品の文書の版は、確かめたときに書き入れる（「版は確認時」と書いた箇所）。スライドは固定 ID（#15）が付くまで、番号と時点を併記した。

## 使い方

- 各行の確認が済むまで、右端の列に書いた規則・既定値・表現は、テンプレート・台帳・claim-lint・README に入れない。
- 確認が済んだら、確認した一次資料の ID・URL と `verified_on`（確かめた日）を書き添えて、行を「確認済み」の節に移す。結果によっては、影響する issue の成果物を直す。
- 「先行事例がない」「効果がない」の類は、検索の範囲での結論です。見つかったら、その行も直す。

## 事実の未確認（仕様・製品の値）

| 内容 | 確認先（一次資料） | 影響する issue | 未確認の間は出さない規則・既定値 |
|---|---|---|---|
| **V01** 経路上のヘッダーの上限の既定値が未確認：Tomcat（`maxHttpHeaderSize`。8 KB と推定）、IIS／HTTP.sys（`MaxFieldLength`・`MaxRequestBytes`）、Node.js（`--max-http-header-size`。16 KiB と推定）、Google Cloud LB、Azure Front Door、Application Gateway（report「未決事項」、notes/authz_model_axis Q5） | `spec`：`Apache Tomcat Configuration Reference（版は確認時）「The HTTP Connector」`、`Microsoft Learn「Http.sys registry settings for Windows」`、`Node.js Documentation（版は確認時）「Command-line options」--max-http-header-size`、`Google Cloud Load Balancing「Quotas and limits」`、`Azure Front Door／Application Gateway「limits」` | #16、#4、#3 | R8 の経路の上限の既定値に入れない。プロファイル（P1・P5 など）の「経路上の上限の既定」の表にも載せない。利用者が自分で値を宣言したときだけ計算に使う |
| **V02** Apache httpd のヘッダーの既定値 8 KB は、メーリングリストの報告（非公式）でしか見ていない（notes/authz_model_axis Q5） | `spec`：`Apache HTTP Server Documentation（2.4）「core」LimitRequestFieldSize` | #16、#4 | R8 の既定値に入れない（V01 と同じ扱い） |
| **V03** HTTP/2・HTTP/3 のヘッダー圧縮（HPACK・QPACK）と `SETTINGS_MAX_HEADER_LIST_SIZE` の下での実効の上限（report「未決事項」、notes/authz_model_axis Q5） | `spec`：`RFC 9113 §6.5.2`、`RFC 9114 §4.2.2`、`RFC 9204`、各サーバーの文書（版は確認時） | #16 | R8 で、圧縮による割り引きをした計算をしない。判定はエンコード後・圧縮前のバイト数で行う |
| **V04** Auth0・Okta・Keycloak の「トークン全体のバイト数の上限」が見つからない（公表されていない可能性）（report「未決事項」、notes/authz_model_axis Q2・Q5） | `spec`：Auth0・Okta・Keycloak の公式文書（版は確認時。Keycloak は `Keycloak Server Administration Guide（版は確認時）`） | #3、#16、#21 | IdP の「トークン全体の上限」を R8 の予算に入れない。予算は、確認済みの経路の上限（Cookie・nginx・API Gateway・ALB・Envoy など）だけから決める |
| **V05** Okta の groups の 100 件の上限は、サポート記事にあるだけで、公式の開発者文書では確認できない。200 件返ったという矛盾する報告（非公式）もある（report「未決事項」、notes/authz_model_axis Q5） | `spec`：`Okta Developer「Expression Language reference」Group functions` | #3、#16、#21 | R8 の「IdP の件数の上限を超えるのに `overflow_strategy` が未宣言なら error」の判定に、Okta の 100 件を既定値として入れない。M_idp の上限の表にも載せない |
| **V06** Keycloak の lightweight access token の説明は、第三者の Confluence ページ（非公式）による。公式文書での設定名と挙動は未確認（notes/authz_model_axis Q5） | `spec`：`Keycloak Server Administration Guide（26.8）「Lightweight access token」`、同じ版のリリースノート | #16、#4（M_idp_keycloak） | M_idp_keycloak とシナリオ A で、サイズ超過の既定の解決策として lightweight access token を書かない。書く場合は「公式文書で未確認」と表示し、R8 の error のメッセージから誘導しない |
| **V07** Okta の token inline hook が、リフレッシュや client credentials でも動くか（report「未決事項」、notes/coverage_lifecycle Q1） | `spec`：`Okta Developer「Token inline hook reference」` | #2、#21 | Okta の行の `hook_invoked` を「動く」「動かない」と書かない。「未確認」とし、カタログの既定の回答に使わない |
| **V08** Entra の custom claims provider が、リフレッシュのときに呼ばれるか（report「未決事項」、notes/coverage_lifecycle Q1） | `spec`：`Microsoft Learn「Custom claims provider overview」`、`Microsoft Learn「Custom claims provider reference」` | #2、#21 | Entra の行の `hook_invoked`（リフレッシュ）を書かない。ガイドのスライド 77・106（2026-11-22 時点）と食い違う記述をカタログに足さない |
| **V09** OpenID Native SSO（カタログの I30）の現在の状態（Final か草案か）（report「未決事項」、notes/coverage_lifecycle Q1） | `spec`：`OpenID Connect Native SSO for Mobile Apps 1.0`（openid.net の仕様の一覧で版と状態を確かめる） | #2、#10 | I30 の根拠を、版付きの `spec` として書かない。I30 をガイドに足すスライドの候補（#10）にしない |
| **V10** CIBA・device flow（RFC 8628）・phantom token の一次資料の本文を読んでいない。report の device flow の行は IANA のページにリンクしている（notes/authz_model_axis Q3） | `spec`：`RFC 8628`、`OpenID Connect Client-Initiated Backchannel Authentication Flow - Core 1.0`。`research`：`Curity「The Phantom Token Approach」`（技術記事。`verified_on` 必須） | #2、#4（P4・P5） | カタログの I09・I10・I19 に、節番号付きの根拠 ID（`RFC 8628 §3.4` など）を、本文で確かめるまで書かない |
| **V11** NIST SP 800-63C-4 がアサーションの内容（属性の最小化など）をどう定めているか。§3.11.2 の規範の文言（SHOULD かどうか）（notes/prior_art Q2、notes/coverage_lifecycle Q2） | `guidance`：`NIST SP 800-63C-4 §3.11.2` | #3、#4（M_privacy_minimization） | 派生属性値を載せる規則を、800-63C-4 の規範（SHOULD）として引かない。根拠に使う場合は「推奨（規範の文言は未確認）」と書く |
| **V12** ガイドとの突き合わせはキーワード検索による。言い換えで扱っているスライドを「なし」と誤判定した可能性がある。特に I25（サインアップ・招待）と I26（資格情報の変更の後）は本文を目視していない（report「未決事項」、notes/coverage_lifecycle Q1） | `guide-slide`：本ガイドの全スライド（`docs/slides.json` の本文とノート。#15 の固定 ID が付いたら ID で指す） | #22、#10、#2 | I04・I09・I21・I24・I25・I26・U16・U21 を、対応表（#22）で目視するまで「ガイドにない」と確定しない。#10 で足すスライドの数を、この判定だけから決めない |

## 効果・先行事例の未確認（研究・事例）

| 内容 | 確認先（一次資料） | 影響する issue | 未確認の間は出さない規則・既定値 |
|---|---|---|---|
| **V13** 先行事例の不在は検索の範囲での結論。Okta・Keycloak・Ping・Cognito・Microsoft SDL・OWASP Threat Dragon・IPA「安全なウェブサイトの作り方」にクレーム設計の様式がないことを、一次資料で直接は確かめていない。非公開の社内テンプレートは調べられない。Curity の体系的な資料の有無も未確認（report「未決事項」、notes/prior_art Q1・Q2・Q6） | `spec`：各社の公式文書（Okta Developer、Keycloak Server Administration Guide、Ping Identity のドキュメント、Amazon Cognito Developer Guide。いずれも版は確認時）。`guidance`：`Microsoft SDL Practices`、`OWASP Threat Dragon`、`IPA「安全なウェブサイトの作り方」（版は確認時）` | #11、#4 | README とテンプレートに「先行事例はない」「初めての」と断定して書かない。「調査の範囲では見つからなかった」と書く |
| **V14** 「クレーム台帳から最悪ケースを合算して予算と比べる静的チェッカー」の直接の先例が見つからない（report Q9、notes/authz_model_axis Q5） | `research`：OSS・製品・論文（追加の検索） | #16 | R8 を「新しい方式」と宣伝しない。R8 は `author-proposal`（筆者の提案、`tracking: "#16"`）として表示する |
| **V15** 採否の根拠を記録するとレビューの欠陥の検出率が上がる、という対照実験がない。チェックリストの導入でセキュリティレビューの見逃しが減った、という定量研究も見つけていない（report「未決事項」、notes/review_effectiveness Q1、notes/coverage_lifecycle Q3） | `research`：研究文献（追加の検索） | #11、#5、#12 | README・観点書で「見逃しが減る」「検出率が上がる」と効果を約束しない。#12 の測定の結果が出るまで、効果を数値で書かない |
| **V16** 設計文書に限ったセキュリティレビューの実験がない。LLM による設計文書のレビューの評価もない（report「未決事項」・Q11、notes/review_effectiveness Q2・Q5） | `research`：研究文献（追加の検索） | #12、#5、#13 | LLM による点検を「人の点検と同じ水準」と書かない。LLM の指摘は、レポートの起点の欄で「LLM」と区別する |
| **V17** 却下候補をあらかじめ記入したテンプレートが、アンカリングに与える影響を測った研究がない（report「未決事項」・Q6、notes/review_effectiveness Q3） | `research`：研究文献（追加の検索）。#12 の測定 | #2、#4 | カタログに理由の模範文を載せない（測るまでは、載せない側を既定にする） |
| **V18** 理由の品質の基準（ルーブリック）と、抜き取りで深く確かめる方法の効果を測った研究がない（report「未決事項」・Q6、notes/review_effectiveness Q3） | `research`：研究文献（追加の検索）。#9・#12 の試行 | #5、#6、#17 | 理由の品質の規則（R7 など）を error にしない（warn にとどめる）。抜き取りの件数（2〜3 件）は `author-proposal`（筆者の提案、`tracking: "#12"`）と表示する |
| **V19** P1〜P5 をどこまで別のファイルにするか（モバイルを P1 に統合するか、など）の根拠となる資料がない。モジュール式の設計書テンプレートの直接の先例もない（report「未決事項」、notes/authz_model_axis Q4） | なし（パイロットの結果で判断する） | #4、#9、#21 | プロファイルの分け方を「最適」「標準」と書かない。分け方は `author-proposal`（筆者の提案、`tracking: "#9"`）と表示する |
| **V20** 実システムでハイブリッドな認可方式がどれだけ採られているか、の統計がない（report Q3 の「大半はハイブリッド」は推論）。Kuhn ら（2010）の本文の 3 方式の詳細も未取得（notes/authz_model_axis Q1） | `research`：業界の調査レポート、`Kuhn, Coyne, Weil「Adding Attributes to Role-Based Access Control」（IEEE Computer 2010）` | #4（M_authz_pdp）、#11 | 「大半」「多く」と量で書かない。「標準と主要な製品がハイブリッドを前提にしている」と書く。Kuhn らの 3 方式を根拠として引かない |
| **V21** IEEE 1028 の本文（報告の必須項目の正確な文言）は有料で読んでいない（notes/prior_art Q5） | `spec`：`IEEE Std 1028-2008` | #5 | レビューレポートの様式を「IEEE 1028 に準拠」と書かない。必須の項目の根拠として IEEE 1028 の文言を引かない |
| **V22** arc42 と C4 の該当する節の本文を取得していない（節の番号と名前は未確認）。非機能要求グレードの認証・アクセス制御の項目番号も未確認（notes/prior_art Q2・Q3） | `research`：`arc42 template（版は確認時）`、`C4 model`。`guidance`：`IPA 非機能要求グレード（2018）` の原本（Excel・PDF） | #4、#5 | テンプレートと観点書に、arc42 の節の番号（第 8・第 9 節）と非機能要求グレードの項目番号を書かない |
| **V23** チェックリストの長さと疲労（項目数と検出率）の関係、設計レビューの工数あたりの検出数の基準値、テンプレートの記入の工数の実測が、ソフトウェアの分野で見つからない（notes/review_effectiveness Q2・Q4・Q5） | `research`：研究文献（追加の検索）。#9・#16 の実測 | #4、#5、#9 | 観点書の項目数の上限や、記入時間の目安を、外部の数値から決めない。目安は #16・#9 の実測だけから出す |
| **V24** 重大度の分類と追跡がレビューの効果を高める、という実証研究がない。根拠の陳腐化（rationale decay）を定量化した研究もない（notes/review_effectiveness Q1・Q4） | `research`：研究文献（追加の検索） | #5、#17 | 重大度の区分（Blocker・Major・Minor）は `author-proposal`（筆者の提案、`tracking: "#5"`）、見直しの期限（`review_by`）の既定の長さは `author-proposal`（`tracking: "#17"`）と表示する。研究の裏付けがあるとは書かない |
| **V25** データの系統の業界標準（OpenLineage など）をクレームの台帳に当てはめた事例を探していない。Edmundson（2013）や Shum と Hammond（1994）、Tang（2006）の本文の具体的な数値も未確認（notes/coverage_lifecycle Q2、notes/review_effectiveness Q1・Q2） | `spec`：`OpenLineage specification（版は確認時）`。`research`：各論文の本文 | #3、#5 | 台帳の系統の列を「OpenLineage 準拠」と書かない。これらの論文の具体的な数値を引かない |

## 取り込みの際に確認したもの

| 内容 | 確認した一次資料 | 結果 |
|---|---|---|
| ID-JAG 草案の最新版 | `spec`：`draft-ietf-oauth-identity-assertion-authz-grant-06`（[datatracker](https://datatracker.ietf.org/doc/draft-ietf-oauth-identity-assertion-authz-grant/)、`verified_on: 2026-11-22`） | -06（2026-10-31）。ガイドのスライド 110（2026-11-22 時点）の「草案 06」は正しい。report と notes/coverage_lifecycle の「-05」を直した |
| エージェント向け Transaction Tokens の草案の最新版 | `spec`：`draft-oauth-transaction-tokens-for-agents-06`（[datatracker](https://datatracker.ietf.org/doc/draft-oauth-transaction-tokens-for-agents/)、`verified_on: 2026-11-22`） | -06（2026-04-11）。notes/authz_model_axis の「-05」の記述を直した。-06 の変更点は読んでいない |
| Ciolkowski（2009）の DOI | `research`：`Ciolkowski「What do we know about perspective-based reading?」（ESEM 2009）`（doi.org の handle API と Crossref、`verified_on: 2026-11-22`） | 調査ノートの 10.1145/1671248.1671262 は登録されていない。正しくは [10.1109/ESEM.2009.5316026](https://doi.org/10.1109/ESEM.2009.5316026)。report と notes/review_effectiveness を直した |
| リンク切れ | [linkcheck-2026-11-22.txt](linkcheck-2026-11-22.txt) | 公開が止まった GitBook の ASVS 日本語訳を GitHub の原稿に、移転した GitLab Handbook のページを新しい URL に、著者ページから消えた MSR 2020 の登録報告を DOI に、応答しない researchr.org を DOI に、NASA SWEHB の短縮 URL を正式な URL に差し替えた |
| notes/authz_model_axis のスライド番号 | `guide-slide`：本リポジトリの `docs/slides.json` の `n`（2026-11-22 時点） | 調査時のメモは 1 つ小さい番号だった（例：PEP と PDP は 66、サイズの予算は 56）。`n` に合わせて直した |
