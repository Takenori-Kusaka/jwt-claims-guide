# 点検の記録（2026-11-22）：設計書テンプレート構想の調査の取り込み（#1、PR #26）

`research/template-design/` の `report.md`・`notes/`（4 本）・`unverified.md` を、作成とは別の LLM のセッションで点検した記録。人による点検は未実施（#20）。

- 作成：2026-11-22（取り込み 9876fe1、編集 f0d2ef9、規約に合わせた修正 dbedf71）
- 点検：2026-11-22。Claude Opus 5.5、作成とは別のセッション（作成の会話の履歴は引き継いでいない）。Web の確認には同じモデルのサブエージェント 3 つを使った
- 点検の原文：https://github.com/Takenori-Kusaka/jwt-claims-guide/pull/26#issuecomment-7074209291
- 点検の対象：ブランチ `issue-1-research-import` の `dbedf71`（`report.md` は f0d2ef9 から変わっていない）
- 渡した資料：PR #26 の本文と差分、issue #1、main の `templates/CONTRIBUTING.md`、本リポジトリの `docs/slides.json`。一次資料は点検者が各項目で当たった（主なもの：rfc-editor.org の RFC 9700・9068・7518・8628、httpwg.org の rfc6265bis、datatracker の ID-JAG と draft-oauth-transaction-tokens-for-agents と draft-araut-oauth-transaction-tokens-for-agents、openid.net の AuthZEN・Back-Channel Logout・OIDC Core・FAPI 2.0、OWASP ASVS 5.0 の原稿、NIST の SP 800-162・NISTIR 8112・SP 800-63C-4・ACTS、Auth0・Cognito・API Gateway・Entra・Envoy・nginx・Okta・Synadia の公式の文書、arXiv の 2102.06909・1612.00163・2202.04586・2401.16310・2601.19239・2604.03826、Crossref と doi.org、Europe PMC、EWD288、researchr の ICSA 2026、KMi-95-13、Tang の博士論文）
- 渡した指示の要旨：(1) report.md の結論・Q1〜Q11・推奨する改訂構想の数値と版を一次資料で確かめる。(2) unverified.md の各行が本当に未確認か、振り分けが正しいか、「未確認の間は出さない」が妥当か。(3)「（非公式）」の付いた引用 10 件と付いていない引用 10 件を抜き取り、分類を確かめる。(4) issue #1 の完了基準。(5) 公開に障る情報。区分は誤り・過大・不一致・曖昧。作成者の結論や意図は渡していない
- 作成者の 1 日以上空けた見直し：未実施（2026-11-23 以降に行い、日付をここに書く）

## 点検した件数

| 対象 | 点検した件数／全件数 |
| --- | --- |
| report.md の事実（範囲 (1)） | 69／88。内訳：IdP・製品・経路の上限 17、仕様・指針 17、論文 20、スライドの番号と題名 13、試算 2 |
| unverified.md の行（範囲 (2)） | 25／25 行を読んだ。一次資料に当たったのは V05・V06・V10・V20 |
| 「（非公式）」の分類（範囲 (3)） | 付いた 10 件・付いていない 10 件を抜き取り。付いた 10 件はすべて妥当。付いていない 10 件のうち 1 件（prior_art.md の Industrial Empathy）は付けるべき |
| 公開に障る情報（範囲 (5)） | research/template-design 以下の全ファイルと tools/linkcheck.py。ローカルのパスと個人の連絡先はなし |

### 点検していない 19 件と理由

点検の原文は理由を書いていない。点検者が範囲 (1) の 88 件のうち手を付けなかったもので、作成者の見直しで確かめる。

| 項目 | 件数 | 理由・扱い |
| --- | --- | --- |
| Q4 の表の「ガイドにない」10 行 | 10 | キーワード検索による判定で、目視の確認は対応表（#22）で行う予定（unverified.md の V12）。点検で確かめても V12 を閉じられないため |
| Falessi（Q6・Q8） | 2 | 点検の範囲で未着手。作成者の見直しで確かめる |
| Curity（Q7・価値評価） | 2 | 同上 |
| MADR の節の名前、ODCS の列、REFEDS R&S、IANA の JWT の登録テンプレート、Osterman | 5 | 同上。テンプレートの列名を借りるとき（#3・#4）に、その issue の点検で確かめる |
| NASA SWEHB と IEEE 1028 の中身 | （上に含む） | SWEHB はこの回線から 403、IEEE 1028 は有料（unverified.md の V21） |
| ASVS V9・V10 | （上に含む） | 観点書（#5）で ID を引くときに確かめる |

## 指摘と直し方

区分：誤り＝必ず直す／過大＝原典より強い言い方／不一致＝成果物の間の食い違い／曖昧＝読み違えやすい。直したコミットは PR #26 の点検の反映のコミット。

| # | 対象 | 区分 | 指摘 | 直し方 |
| --- | --- | --- | --- | --- |
| 1 | report Q4 の表 | 誤り | device flow（RFC 8628）のリンクが IANA を指す | rfc-editor.org の RFC 8628 に直した。unverified.md の V10 からリンクの文を消した |
| 2 | report Q4、notes/coverage_lifecycle | 誤り | 「RFC 9700 で非推奨」は弱すぎる。ROPC は §2.4 で MUST NOT、implicit は §2.1.2 で SHOULD NOT | 両方を「ROPC は RFC 9700 §2.4 で使用禁止（MUST NOT）、implicit は §2.1.2 で SHOULD NOT」に直した。CONTRIBUTING の例と合う |
| 3 | report R6、notes/coverage_lifecycle | 誤り | NIST ACTS に 96% はない。10 種類のアプリで 2 因子までの累積はおよそ 47〜97% | report は幅で書き直し、2 因子の網羅は全部を拾う保証でないので R6 を warn にとどめる理由にした。ノートは発表の 96% を残し、ページの値との違いを訂正として書いた。ノートの要点と推論の「費用対効果の良い目標」を「なりうる」に弱めた |
| 4 | report Q1、notes/coverage_lifecycle | 誤り（過大を含む） | 48% は 1612.00163 にない。主因は領域知識だけではない | 1611.10288（EMSE 2016）の Table 9 で 109／228（48%）を確かめ、出典をこれに直した。原因は「資格や経験の不足、時間の圧力など」（同 Fig. 4）にした |
| 5 | report Q1、notes/coverage_lifecycle | 誤り | EWD288 は 1970 年 7 月 | report は「1969 年の NATO 会議で述べ、EWD288（1970 年 7 月）にも書いた」にした。ノートの「1968 年」を直した |
| 6 | report Q6、notes/review_effectiveness | 誤り | KMi-95-13 に「未知の空間で有効、定型で邪魔」の対比がない | 置き換えの論文は見つけていない。report から文を消し、ノートは訂正の注記を付けて根拠として使わないとした。unverified.md に V27 を足した |
| 7 | report 価値評価、notes/review_effectiveness | 誤り（要再確認） | Tang の「質問の約 50% が理由について」が全文で見つからない | report から消した。ノートは訂正の注記を付けた。unverified.md に V26 を足した |
| 8 | notes/authz_model_axis、unverified.md、PR の本文 | 誤り | draft-oauth-transaction-tokens-for-agents は失効し、draft-araut-oauth-transaction-tokens-for-agents（最新 -03、2026-10-31）に置き換わった | datatracker で確かめて 3 か所を直した |
| 9 | unverified.md V05、report 未決事項、notes/authz_model_axis | 誤り | Okta の 100 件の上限は公式の開発者文書にある。Authorization Code と PKCE は例外 | developer.okta.com のガイドで「between 1-100」と例外を確かめた。V05 を「確認済み」に移し、R8 の既定値に入れてよいが 2 つのフローを除く、とした。report とノート（チェッカーの案を含む）を直した |
| 10 | report Q11、notes/review_effectiveness | 誤り（要再確認） | Li et al. の 150 時間は要旨にない。385 件は v1、v2 は 355 件 | 版を v1 に固定し、v2 の値を併記した。150 時間は消した。unverified.md に V29 を足した |
| 11 | report Q3 | 過大 | 「実システムの大半はハイブリッド」は V20 の規則に反する | 「標準と主要な製品はハイブリッドを前提にしている」にし、V20 を指した。ノートの要点も弱めた |
| 12 | report Q3、notes/authz_model_axis | 過大 | SP 800-162 の定義そのものに relationships はない。本文の「関係」は ReBAC の関係と意味が違う | 「本文の説明では」とし、意味の違いを書いた。「定義自体に含まれる」を消した |
| 13 | report Q2、notes/review_effectiveness | 過大 | Gonçalves の有意な予測因子は認知負荷で、理解が最大の要因とは測っていない | 「対象の理解が欠かせないと論じている」にした |
| 14 | report Q2、notes/review_effectiveness | 過大 | チェックリストとアドホックの比較に Ciolkowski を挙げている | report の出典を Porter ら（1995）だけにした。ノートの総合の節では、それぞれ何を比べたかを添えた。Ciolkowski は「PBR がチェックリストに勝る保証はない」の出典として残した |
| 15 | report Q1、notes/coverage_lifecycle | 過大 | Shostack は「それで足りる場合もある」とも書いている | 原文に合わせて書き直した |
| 16 | report 冒頭と結論 | 過大 | 結論は Q1 の出典を前提にしている。直したあと言い方を見直す | 見直した。「漏れゼロは約束できない」の根拠は Dijkstra・Shostack・Paul et al. で、48% の出典の訂正や Shostack の弱めでは変わらないため、結論の文は変えていない。report の冒頭の「訂正」の節にこの判断を書いた |
| 17 | notes/prior_art | 不一致 | Industrial Empathy の 2 本の記事のうち 1 本だけ（非公式） | もう 1 本にも付けた |
| 18 | PR の本文 | 不一致 | リンクの件数とコミットの説明が古い | 最新の出力（268 件、BROKEN 0）とコミットの一覧に直した |
| 19 | unverified.md V10 | 不一致 | リンクの誤りは直せる誤りで、未確認ではない | #1 と一緒に直し、V10 からその文を消した |
| 20 | report Q4 | 曖昧 | IANA に「grant type」という名前の登録簿はない | 「OAuth URI」「OAuth Access Token Types」「OAuth Authorization Endpoint Response Types」の名前で書いた |
| 21 | report サイズチェッカー | 曖昧 | RSA の署名長は RFC 7518 §3.3 ではなく RFC 8017 §8.2.1 による | `RFC 8017 §8.2.1` を足し、ES256 は `RFC 7518 §3.4` を指した |
| 22 | report Q3 | 曖昧 | AWS の例は identity-sources-oidc.html にある | そのページへのリンクを足した |
| 23 | report Q2、notes/review_effectiveness | 曖昧 | Braz の原文は「それ以上は有意に改善しない」 | その言い方に直した（ノートの 4 か所を含む） |
| 24 | report Q8 | 曖昧 | ADR の約 50% は Buchgeher et al. からの孫引き | 一次の出典として Buchgeher et al. を引き、arXiv 2604.03826 は「引用」とした。ノートにも注記した |
| 25 | report Q1、notes/review_effectiveness | 曖昧 | Urbach の「約 100% の遵守」が要旨で確かめられない | PSNet でも確かめられなかった。report とノートから「約 100% の遵守」を外し、「義務化して導入しても成果が変わらなかった」までにした。unverified.md に V28 を足した |

### 未検証点の表への指摘

| 指摘 | 扱い |
| --- | --- |
| V05 は確認済みにできる | 反映した（上の #9） |
| V10 のリンクの部分は直せる誤り | 反映した（上の #1・#19） |
| V06（Keycloak の lightweight access token）、V01・V02（Tomcat・Node.js・httpd の既定値）は公式の文書ですぐ確かめられる | 反映しない。この PR は調査の取り込みで、値を確かめて R8 の既定値に入れるのはシナリオ A（#16）の作業のため。#16 で確かめて閉じる |
| V20 の規則が report 自身に当てはめられていない | 反映した（上の #11） |
| 足すべき行（Tang の 50%、Li et al. の 150 時間、Urbach の遵守率、NaPiRE の 48% の出典、Cognito の `sub`） | V26〜V30 として足した。ただし NaPiRE の 48% は出典を確かめられたので行にせず、report とノートを直した（上の #4） |

## まだ残っていること（#13 の完了の定義）

- 作成者の 1 日以上空けた見直し（2026-11-23 以降）
- 根拠の ID の実在を全件確かめること。今回は DOI（11 件）とリンク（268 件、BROKEN 0）を機械で確かめたが、版付きの ID の形で書いた根拠は unverified.md の表だけで、report とノートの本文の引用は ID の形になっていない
- 根拠の中身の 10%（最低 10 件）の抜き取り。今回の点検の 69 件が範囲 (1) の 78% に当たるが、作成者の見直しのときに抜き取りの記録として整理する
