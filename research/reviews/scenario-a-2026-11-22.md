# 点検の記録：縦の一本（シナリオ A、Keycloak）（#16、PR #28）

`templates/CONTRIBUTING.md` の 2.（完了の定義）と 3.（点検者の取り決め）による記録です。

> 人による点検は未実施。作成とは別の LLM のセッションで点検した。作成者の 1 日以上空けた見直しは未実施（点検の原文：PR #28 の #issuecomment-7074910571（1 回目）と #issuecomment-7075075798（再点検））。

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

## 再点検（2 回目）と直し方

| 項目 | 内容 |
| --- | --- |
| 点検 | 2026-11-22、記入例の作成者とも 1 回目のレビュアーとも別の Claude のセッション。PR #28 のコメント https://github.com/Takenori-Kusaka/jwt-claims-guide/pull/28#issuecomment-7075075798 |
| 対象 | コミット `115bb62`（1 回目の反映の後） |
| 読んだもの | 1 回目のレビューと反映の対応表、記入例の 4 ファイル、`gate1.md`、この記録、`templates/trace/planned_items.yaml`、#6・#17・#18・#8・#5 の本文 |
| 結果 | 17 件中、直った 15 件、直し残し 1 件（A10）、修正で新しく生じた問題 1 件（A09）。新しい Major は 0 件。ほかに Minor 6 件。gate1.md への指摘 5 件 |

| 指摘 | 区分 | 直し方 |
| --- | --- | --- |
| A10 の直し残し：C-scope の `refs` に、理由で挙げた公式文書がない | 不一致 | C-scope の `refs` に Keycloak Server Administration Guide（26.8.2）「Using lightweight access token」を足した |
| A09 の新しい問題：取り直しを最短 300 秒に 1 回にしたので、でたらめな kid で枠を使われた直後の正規の鍵の入れ替えで、新しい kid が最大 300 秒拒否されうる。JWKS のキャッシュの TTL が無く、消した鍵を信頼し続けうる | 誤り | キャッシュの TTL を 3600 秒にした。鍵の入れ替えの手順を書いた：新しい鍵は署名に使う前に、TTL と取り直しの間隔の和（3900 秒）より長く JWKS に公開する（Keycloak では passive で先に足す）。古い鍵は、最後にその鍵で署名した AT の受け入れの上限（330 秒）が過ぎてから消す。新しい鍵はすでにキャッシュにあるので、取り直しの枠を使われても拒否されない。Keycloak が passive の鍵を JWKS に載せるかは未確認と明記した（AT `key_rotation`、U09、design.md 6.・12.） |
| 受け手の時計のずれ 30 秒を許すので、遅れの上限は 330 秒になる（A03・A15・C-roles の volatility） | 曖昧 | 「受け入れの最大は発行から 330 秒（寿命 300＋ずれ 30）」を design.md 2. で定義し、記入例の「最大 300 秒」「300 秒より早く」をすべて 330 秒に揃えた。C-roles の volatility・propagation_delay を 330 にした |
| design.md 2. の「exp − iat ≤ 300（＋ずれ 30 秒）」と C-exp の「300 秒を超えたら拒否」が食い違う | 不一致 | exp と iat はどちらも発行者が書く値なので、ずれは足さない、に揃えた（design.md 2.、C-exp、AT の note） |
| A04 の残り：所有者の `SECURITY DEFINER` の関数も RLS をすり抜ける | 誤り | 「作らない（作るなら所有者を RLS の対象のロールにする）」を足した（C-tenant-id、design.md 2.） |
| A14 の残り：token_types の SSO は「既定どおり」なのに、design.md 3. では既定から外れた点にしている | 不一致 | SSO を「採用」（Session Max を設定）にし、design.md 5. も揃えた |
| A01 の残り：R8 の最悪 1258 バイトも、テナントの管理者がマッパーを足せば超えられる | 曖昧 | AT の note に書いた（影響はそのテナントだけで、nginx が 400 を返す） |
| A11 の補足：Keycloak が Java の文字数（UTF-16 の単位）で数えるなら厳密な上限は 1533 バイト | 曖昧 | 2044 は安全側として残し、1533 の見方と、数え方を確かめていないことを note に書いた |
| mix-up（BFF が 2 つのレルムのクライアント） | 曖昧 | design.md 12. に、レルムごとに redirect_uri を分けると書いた（RFC 9207 の `iss` の照合は、Keycloak の対応を確かめていない） |
| この記録の冒頭の注記の「記録：」が、このファイル自身を指している | 曖昧 | 注記の参照先を、2 つの点検のコメントに直した |
| gate1.md 8.「続ける」：ヘッダーの 5 文字の差を claim_lint の手柄にしている | 過大 | 見本トークンとの照合のテスト（実行での照合）が見つけた、と直した |
| gate1.md 5.：17 件は 1 つのセッションのレビューで、正解の母数ではない | 過大 | 注記を足した |
| gate1.md 5.：3 つへの分類は点の値でなく幅で示す | 過大 | 作成者と再点検の分類を並べ、不一致 8 件を示し、幅（静的 6〜8・実行 3〜5・レビューだけ 4〜7）にした |
| gate1.md 5.：A01・A09・A17 の宣言はすでに計画にある | 不一致 | 「計画済み」と書いた（#3 の modifiers・unknown_kid・jwks_cache_ttl、#4 の lite-criteria） |
| gate1.md 5.：A04・A12 は実行テストの候補 | 曖昧 | #8 に渡す候補として書き、#8 にコメントで渡した。規則の拡張は #6 にコメントで渡した |
| `.gitleaks.toml` の絞り込みを、別の JWT を入れて検出されることを実行で確かめていない | 曖昧 | 下の「secret scan の除外の確認」で実行した |

### secret scan の除外の確認

見本のファイルと `.gitleaks.toml` を scratchpad の空のディレクトリに同じ相対パスで写し、gitleaks 8.30.1（CI と同じ版）で走査した。2 回目は、写したファイルに別の JWT（HS256 の試験用の値）を足した。リポジトリのファイルは変えていない。

```
$ gitleaks version
8.30.1
== 1. copy as committed
$ gitleaks dir --no-banner --redact --config=.gitleaks.toml .
INF no leaks found
== 2. second JWT added to the fixture
$ gitleaks dir --no-banner --redact --verbose --config=.gitleaks.toml .
Secret:      REDACTED
RuleID:      jwt
File:        tools/tests/fixtures/claim_lint/golden/token.json
Line:        2
WRN leaks found: 1
```

足した JWT だけが検出され、見本のトークン（5 行目）は除外されたままだった。除外が「そのファイル」ではなく「そのトークン」に絞られていることを確かめた。

反映した後の claim_lint：`error 0, warn 0, info 5`。

## 関門 1 の判定と、それに伴う変更

- 判定：2026-11-22、作成者が「絞る」とした（Lite の記入は 4 時間を超えるという作成者の見積もり。実測ではない）。記録は `research/template-design/gate1.md` の 9.
- tier：gate1.md の 7. の案の 5 件に加え、案に無かった 27 件（L27・L31・L23 の拡張に結びつく 13 件、作成者の追加の指示による 14 件）を core にして確定した（PR #31 の点検の後に、設計のチェックリストの 6 件を足して計 38 件）。`templates/trace/requirements.yaml` に `tier_confirmed` を足し、`trace_check.py` がそれを検査・表示する
- レビューで必ず扱うスライド：チェックリスト・アンチパターン・レビューの観点・追加前の問いの 10 枚に `review_required: true` を付け、要件ごとに `review:` の成果物を必須にした。アンチパターンの 17 件に専用の問い（`review:perspectives#ap-*`）、設計のチェックリストの 13 件に `review:perspectives#design-checklist`、追加前の 25 問の 27 件に `review:perspectives#pre-add-questions` と `lint:L72` を足した
- Lite の縮小案：gate1.md の 10.（PR #31 の点検の後の値）。手で書く YAML の欄 875 → 700（20% 減。追加前の 25 問の 56 欄を足した後。`tools/count_lite_fields.py` で再現できる。PR #31 の再点検の後の値）、設計書の手で書く節は #4 の Lite の定義に対して 6 → 5（記入例が書いた 12 節に対して 12 → 5）。時間は約 18% 減（#4 の Lite の定義に対して。上限の見積もりは約 39%）と見積もった（実測ではない）
- 追加前の 25 問の記入例：`templates/examples/scenario-a/claim_request_tenant_id.md`（tenant_id。25 問すべてに回答）
- これらの変更は、まだ別のセッションで点検していない

## PR #31 の独立点検（3 回目）と直し方

- 点検：2026-11-22、作成とは別の Claude のセッション。PR #31 のコメント https://github.com/Takenori-Kusaka/jwt-claims-guide/pull/31#issuecomment-7075377349 。対象は `81bd18a`
- 結果：指摘 15 件（誤り 2、不一致 4、過大 1、曖昧 8）。判定の記録・縮小 Lite で残したもの・25 問の回答の多く・規約への追従は問題なし
- すべて反映した（反映しない指摘は 0 件）

| # | 指摘（要約） | 直し方 |
| --- | --- | --- |
| 1 | 縮小 Lite で「対象外」を既定から引き継ぐと、A03（I09・U07）・A15（U05）・U10 が出た行を手で書かなくなる | 規則を改めた：引き継ぐのは、選んだ発行方式とクライアントの設定で「構造上起きない」と IdP モジュールが印を付けたイベントだけ（I03・I04・I05・I07・I08）。その構成で起こりうるイベントの対象外（I06・I09・U05・U07・U08・U10）は `assumption`・`breaks_when` を手で書く。カタログの欄は 76 → 56 に数え直した |
| 2 | シーケンス図の節で「指摘 0 件」としたが、A12 はこの節で出ていた | 「A12（Minor）が出たが、同じ記述が 2. にもあり、2. と台帳で拾える」と書いた |
| 3 | 欄の数の表が再現できない | 数えるスクリプト `tools/count_lite_fields.py` をリポジトリに置き、表をその出力にした（数え方と規則はスクリプトの冒頭と定数）。テスト `tools/tests/test_count_lite_fields.py` で gate1.md の値と照合する。結果は 875 → 692（21% 減）。対象外をすべて引き継ぐ最初の規則なら 875 → 668（点検の数え直しと一致） |
| 4 | 節の比較の元が #4 の Lite の定義でない。40% の根拠が多めに見える | #4 の Lite の定義（6 節）に対して 6 → 5、記入例が書いた 12 節に対して 12 → 5、と並べた。13.（前の版との差分）を数えない理由を書いた。時間は「#4 の定義に対して約 19% 減、上限の見積もり約 40%」とし、仮定（YAML と設計書に半分ずつ、欄・節の手間は同じ）と、残した節が重いので実際は小さい見込みであることを書いた |
| 5 | 判定に使ったデータに 2.（作成者の見積もり）が無い | 「判定に使ったデータ：2.（作成者の見積もり。実測ではない）」とし、1.・3.・5. は「参考にしたデータ」にした |
| 6 | 「案どおり確定」と読めるが、32 件のうち 27 件は 7. の案に無い | 「7. の案どおりの 5 件に加え、33 件を core にして確定」とし、内訳を書いた（gate1.md 9.、README、記録） |
| 7 | 設計のチェックリストの R3〜R8 が full のまま（25 問の core の問いと重なる） | R3〜R8 の 6 件を core にした。core 477 → 483 |
| 8 | `review_required` はフラグの自己申告だけで、消すだけで外せる | 固定の一覧 `templates/trace/review_required.yaml`（10 枚、理由つき）を置き、`classification` のフラグと完全に一致しなければ失敗するようにした。フラグを消した場合と、一覧に無いフラグを付けた場合のテスト、リポジトリの一覧が 10 枚であることのテストを足した |
| 9 | 確定の後に tier を下げても検出されない | `tier_confirmed` に確定時の `core_count`（483）と `core_sha`（core の要件 ID の sha256 の先頭 12 桁）を持たせ、`--snapshot-tiers` で書くようにした。確定の後の変更は `tier_changes` に id・from・to・on・reason（20 字以上）を書かないと失敗する。記録が無い下げ・記録があれば通る・理由が短いと失敗、のテストを足した |
| 10 | 問 24：330 秒は寿命ではなく受け入れの上限。起点が不明 | 4 段の手順（受け手が両方を読む → 発行者が両方を出す → 新しい名前だけ → 最後の古い AT の受け入れの上限 330 秒の後に、受け手が古い名前をやめる）にした |
| 11 | 問 9：空文字の拒否が台帳の saas-api の `enforced_at` に無い | C-tenant-id の `enforced_at` に「null・空文字・32 バイトを超える値は拒否」を足し、出どころに Postgres の行も書いた |
| 12 | 問 12：レルム名は変更できる | 「レルム名は変更できるので不変の ID ではない。変えない運用に頼る（前提）」と書き、レルムの内部 ID を値にする案を L3 の候補として挙げた |
| 13 | 問 13：受け手が超過を検知できるか、問 15：縮小 Lite での出どころ | 問 13 に「受け手は 32 バイトを超える値を拒否する（欠落や切り詰めとして扱わない）」を足した。問 15 の出どころを `enforced_at`（iss との照合）を先にし、縮小 Lite では `issuers` が生成の列になることを書いた |
| 14 | 1 行目のコメントの検査が `templates/trace/` だけ | `templates/` の下のすべての YAML（9 ファイル）に広げた。`test_claim_lint.py` の重複キーのテストの行もコメントの形にした |
| 15 | スキーマのキーの削除の判断が CHANGELOG に無い | 「キーを持つ既存のファイルは検証で落ちる。semver ではメジャーに当たるが、未リリースのため 0.1.0 のまま」と書いた |

## PR #31 の修正の再点検（4 回目）と直し方

- 点検：2026-11-22、PR の作成とも PR #31 の最初の点検とも別の Claude のセッション。https://github.com/Takenori-Kusaka/jwt-claims-guide/pull/31#issuecomment-7075509441 。対象は `b684571`
- 結果：止める項目 1 件（B1）、止めない項目 3 件（N1〜N3）。ほかの修正（review_required の固定、tier のハッシュ、gate1.md 9. の文言、25 問の回答）は問題なし

| # | 区分 | 指摘（要約） | 直し方 |
| --- | --- | --- | --- |
| B1 | 誤り | `tier_changes` のキー `on` は YAML 1.1 で真偽値として読まれる。手で書いても、ツールの書き出し（`--update-hash`）を一度通しても壊れる。コメントの位置もずれた | キーを `changed_on` にした（コード・README・テスト）。コメントを定数の前に戻した。ツール自身の書き出しと `--update-hash` を通しても `tier_changes` が残り、検査が通るテストを足した。`templates/` の下のすべての YAML で、キーが真偽値として読まれていないことを確かめるテストを足した |
| N1 | 曖昧 | `--snapshot-tiers` を実行すると、記録を消して日付と判定者はそのまま通る | `--confirmed-on`・`--by` を必須にした。確定済みか `tier_changes` があるときは `--reconfirm` が無ければ拒否し、日付が前の確定と全ての変更の日付より前なら拒否する。前の確定は `previous` に残す。`core_sha` を手で書き換えることは機械では防げないので、その差分は確定のし直しとしてレビューで扱うと README に書いた |
| N2 | 曖昧 | 理由の中身、日付、`from` を見ていない | `changed_on` が `confirmed_on` 以降、理由は 20 字以上で同じ文字の繰り返しでなく `#NN`・`PR`・`関門` のどれかを含む、`to` がその時点の tier と一致する（`from` は確定時の tier）、を検査し、テストを足した |
| N3 | 曖昧 | 対象外の分け方の基準が一貫しない（I06・I09 もスイッチで止まる、I08 は Keycloak の既定に依存する） | 基準を「クライアントのスイッチ 1 つで止めたイベントで、指摘が出ていないものだけ引き継ぎ、『設定を確かめた』の 1 欄を書く。指摘が出た行・レルムやクライアントの既定に依存する行・利用イベントは手で書く」と書き直した。I08 を手で書く側へ移した。数え直して 875 → 700（20% 減）、時間の見積もりは約 18%（上限 39%） |

## 点検していないもの

- 根拠の中身の抜き取り（10%、最低 10 件）
- 「対象外」の行の抜き取り（5 件）。カタログへの回答の対象外は 11 件
- 作成者の 1 日以上空けた見直し
- 再点検の後の修正（この記録の「再点検（2 回目）と直し方」）と、関門 1 に伴う変更（PR #31 の点検の後の修正を含む）を、別のセッションで点検すること
- 人による点検（#20）
