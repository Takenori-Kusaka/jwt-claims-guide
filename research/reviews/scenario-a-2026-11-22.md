# 点検の記録：縦の一本（シナリオ A、Keycloak）（#16、PR #28）

`templates/CONTRIBUTING.md` の 2.（完了の定義）と 3.（点検者の取り決め）による記録です。

> 人による点検は未実施。作成とは別の LLM のセッションで点検した。作成者の 1 日以上空けた見直しは未実施（記録：`research/reviews/scenario-a-2026-11-22.md`）。

## 点検の方法

| 項目 | 内容 |
| --- | --- |
| 作成 | 2026-11-22、Claude（Opus 5.5）のセッション。ブランチ `issue-16-vertical-slice` のコミット `e842bad`・`befd117` |
| 点検 | 2026-11-22、作成とは別の Claude のセッション（会話の履歴を引き継がない）。PR #28 のコメント https://github.com/Takenori-Kusaka/jwt-claims-guide/pull/28#issuecomment-7074910571 |
| 点検の対象 | コミット `befd117`（PR の先頭）。作業ツリーは読むだけで、変えていない |
| 渡した資料 | PR #28 の本文と差分、#16・#11 の本文とコメント、`templates/CONTRIBUTING.md`、`docs/slides.json`（Part 4〜9）、ケーススタディ `jwt-claims-casestudy@080b8da`、一次資料（Tomcat・Microsoft Learn・Node.js・Apache httpd・nginx・Keycloak の文書、GitHub の API） |
| 渡さなかったもの | 作成者の結論（`gate1.md` の 3. 迷った点と 4. lint の指摘）。レビュアーは Part A の指摘を出し終えるまで読んでいない |
| 指示 | レビュアーのコメントの冒頭にある範囲（Part A：記入例の設計レビュー、Part B：新しい事実の点検、Part C：#16 の完了基準と CI・セキュリティ） |
| 作成者の見直し | 1 日以上空けた見直しは未実施。この記録の「直し方」は、点検を受けた当日に作成者が直したもの |

## 点検した件数

| 項目 | 件数 | 結果 |
| --- | --- | --- |
| 事実（仕様・製品の値・上限・版、新しく足したもの） | 24／24（全件） | 誤り 0 件、補足 2 件（下の「事実の点検」） |
| 記入例の設計（Part A） | 記入例の 4 ファイルの全体 | 指摘 17 件（Blocker 0・Major 4・Minor 13） |
| 根拠の中身の抜き取り（10%、最低 10 件） | 0 件 | **未実施**。A10（根拠と主張のずれ）は、レビューの中で見つかった 1 件 |
| 「対象外」の行の抜き取り（5 件） | 0 件 | **未実施**。カタログへの回答の対象外 11 件のうち、I09・U07 はレビューで指摘を受けた（A03） |
| 根拠の ID の実在の機械での確認 | スライドの ID：claim_lint の SLIDE と `tools/check_slide_refs.py` で全件。URL：新しい YAML の URL 13 件を curl で 200 を確認、OIDC の節のアンカー 10 件と RFC 9700・9068 の節 8 件の実在を確認 | 問題なし。ケーススタディの ID（CLM・ORG）は照合のスクリプトで 32 件すべて実在 |
| lint の抑止・重大度の引き下げ | error の抑止 0 件、引き下げ 0 件、warning の抑止 0 件 | — |
| 「漏れゼロ」を約束する表現 | 成果物の全文を「漏れ」「網羅」で検索 | 約束する表現なし（カタログの冒頭は「漏れがないとは言えない」） |

## 事実の点検（Part B）

24 件すべて一致（Tomcat 11.0.29、HTTP.sys の MaxFieldLength・MaxRequestBytes、Node.js v26.13.1、Apache httpd 2.4、nginx、Keycloak 26.8.2 の軽量アクセストークン、unverified.md の行の数、R8 の再計算、見本の client_id と jti、記入例の最悪のサイズ、ケーススタディとの照合の件数、1398 バイト、アクションの SHA 2 件、gitleaks の sha256）。一覧はレビューのコメントの Part B。

| 対象 | 区分 | 指摘 | 直し方 |
| --- | --- | --- | --- |
| `design.md` 3.（1398 バイト） | 曖昧 | 出典が書かれていない（gate1.md にはある） | 出典（`results/measurements.json` の `A.keycloak_token_bytes.alice`）を書いた |
| `tools/claim_lint/path_limits.yaml`（Node.js） | 曖昧 | 文書の「HTTP headers」を all_headers（要求行を含む）に分類したのは保守側の読み方 | 筆者の提案と `note` に書いた |

## 記入例の指摘（Part A）と直し方

区分は #13 の区分（誤り・過大・不一致・曖昧）に、レビュアーの種別を併記した。すべて反映した（反映しない指摘は 0 件）。

| ID | 対象 | 区分（種別） | 指摘（要約） | 直し方 |
| --- | --- | --- | --- | --- |
| A01 | C-tenant-id・C-user-id・C-sub・C-roles、AT（Major） | 誤り（前提の誤り） | テナントの管理者は user_id・roles・寿命・aud も書けるのに、iss と照合して守っているのは tenant_id だけ。API は exp − iat を見ていない | 「テナントの管理者は自分のレルムの中では全権を持つ」を `assumption` に明記した。API の強制を足した：`exp − iat ≤ 300`（C-exp・C-iat・AT の note）、roles の語彙の固定と 2 件を超えたら拒否（C-roles）、user_id は sub と一致しなければ拒否（C-user-id）、テナントは iss から引く（C-iss・C-tenant-id）。design.md 2. に一覧を書いた |
| A02 | C-sub・C-user-id、design.md 6.（Major） | 不一致（実装とのずれ） | BOLA の鍵が sub か user_id か決まっていない | 鍵は sub だけにした（請求書の owner_sub と、iss から引いたテナントの組で照合）。user_id は認可の鍵にしない |
| A03 | LOGOUT、I09・U07（Major） | 誤り（前提の誤り） | Back-Channel Logout の却下の理由（RP は 1 つ）が的外れで、代わりの手段がない | 理由を直した：IdP 側のセッションの終了は、BFF の次のリフレッシュの失敗で検知し、BFF は自分のセッションを終える（最大 300 秒の遅れを許すので、受け口を作らない）。BFFSESSION の revocation、I09・U07 の前提と崩れる条件（300 秒より早く反映する必要が出たとき）を直した |
| A04 | design.md 2.・9.、C-tenant-id（Major） | 誤り（候補の漏れ） | RLS をすり抜ける主体（所有者、FORCE ROW LEVEL SECURITY、superuser、ビュー）が抜けている | C-tenant-id の `enforced_at` に Postgres の行を足した：app_rls は所有者でなく NOSUPERUSER・NOBYPASSRLS、テーブルは ENABLE と FORCE、所有者はマイグレーションのロール、ビューは作らないか security_invoker。design.md 2. にも書いた |
| A05 | C-tenant-id `rationale` | 不一致（目的と仕組みの不一致） | 実際にテナントを決めているのは iss | 「テナントを決めるのは iss、tenant_id は照合用の写し」と書き直し、app.tenant には iss から引いた値を使うとした |
| A06 | C-user-id `assumption` | 誤り（実装とのずれ） | 「R8 の info が出る」と書いたが、別の名前のクレームは R8 の重複の検査に出ない | 文を直した（出ないと書いた） |
| A07 | C-client-id、design.md 6. | 誤り（前提の誤り） | at+jwt を名乗るのに RFC 9068 §2.2 で REQUIRED の client_id がない | C-client-id の `rationale` に「RFC 9068 に適合しない。汎用の検証部品は拒否する」と書いた。design.md 3.・6. にも書いた |
| A08 | AT `required_claims` | 不一致（実装とのずれ） | azp は on_missing が拒否なのに required_claims にない | required_claims に azp を足した |
| A09 | U09、AT `key_rotation` | 誤り（候補の漏れ） | 未知の kid での取り直しに回数の制限と負のキャッシュがない | iss ごとに最短 300 秒に 1 回、取り直しても無い kid は 300 秒の負のキャッシュ、と書いた（間隔は筆者の提案。一次資料は未確認） |
| A10 | C-typ-claim・C-sid・C-azp・C-scope | 過大（理由の不備） | 根拠の節は軽量アクセストークンについてで、通常の AT に当てはまるとは書いていない | 「軽量アクセストークンの記述からの推論で、見本の通常の AT にも出た」と書き直した |
| A11 | C-name `max_bytes` | 誤り（前提の誤り） | 属性の上限は文字数で、UTF-8 では 255 バイトを超えうる | 2044 バイト（511 文字 × 4 バイト）にし、仮定（各 255 文字、既定値は未確認）を note に書いた |
| A12 | design.md 7. | 不一致（実装とのずれ） | SET LOCAL は値をバインドできない | `set_config('app.tenant', $1, true)` をパラメータで呼ぶ形に直した（design.md・C-tenant-id・U02） |
| A13 | design.md 9.、C-tenant-id | 誤り（候補の漏れ） | app.tenant が未設定のときに全件を拒否することが書かれていない | ポリシーが NULL・空文字で一致しないこと、tenant_id は NOT NULL で空文字を CHECK で禁止することを書いた |
| A14 | BFFSESSION・SSO・RT | 誤り（候補の漏れ） | idle だけで絶対的な上限がない | SSO Session Max を 36000 秒（10 時間）に設定すると決め、BFFSESSION・RT の上限も 36000 秒にした（Keycloak の既定値は確かめていない） |
| A15 | C-tenant-id `on_revoke`、AT `revocation`、U05 | 曖昧（理由の不備） | テナントの停止の一覧の対象・出どころ・鮮度が決まっていない | 出どころを Postgres の tenants.status、対象をすべての要求、鮮度を 0 秒（同じトランザクションで引く）にした。利用者の無効化は BFF のリフレッシュの失敗（最大 300 秒）。U05 の前提を合わせた |
| A16 | issuance_profile `rt_strategy` | 過大（理由の不備） | ローテーションの根拠は公開クライアントへの要求で、機密の BFF に合わない | 「公開クライアントへの要求で、機密には課されない。BFF から漏れたときに古い RT を使えなくするために採る。再利用の検知は当てにしない」と書き直した |
| A17 | design.md 冒頭 | 不一致（目的と仕組みの不一致） | #4 の定義では Full なのに Lite で書いた | 冒頭に「#4 の定義では Full」と、書いていない Full の欄を明記した。gate1.md 2. に「測る時間は Full に当たるケースを Lite の欄で書いた時間」と書いた |

反映した後の claim_lint：`error 0, warn 0, info 5`（レビューの前と同じ）。

## claim_lint との比較

レビューだけ 17 件、claim_lint だけ 5 件（すべて info）、両方 0 件。分析（17 件を、計画している lint・実行テスト・観点書のどれが後で拾えるか）は `research/template-design/gate1.md` の 5.。

## 点検していないもの

- 根拠の中身の抜き取り（10%、最低 10 件）
- 「対象外」の行の抜き取り（5 件）。カタログへの回答の対象外は 11 件
- 作成者の 1 日以上空けた見直し
- 直した後の記入例を、別のセッションでもう一度点検すること
- 人による点検（#20）
