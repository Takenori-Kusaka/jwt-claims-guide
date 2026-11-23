# 記入ログ：シナリオ B（Full、ブラインド記入）

- 書き手：LLM（Claude Opus 5.5）。**LLM による記入で、人による記入・検証ではない**。記入の時間は人の記入の手間の代わりにならない
- 入力：要求の概要（brief-B.md）、`templates/`（`examples/**`・`casestudy-*` を除く）、`tools/` とその README、公開の仕様・IdP の文書（fideslang 3.1.4 の CSV を取得して data_category のキーを確かめた）
- 時刻は記入した環境の実時刻（JST、`date -Iseconds` で各区切りに取った）。区切りの間の時刻は、その区切りで取った値

## 読んではいけない資料を開いたか

なし。`templates/examples/**`・`templates/casestudy-*`・`research/**`（この記入の出力の置き場を除く）・`docs/claims/data/**`・ケーススタディのリポジトリ・brief-C.md は開いていない。テンプレートの本文が `research/template-design/...` を根拠として名指ししている箇所があったが、開いていない。`templates/00_core.md` の 3. の「ケーススタディの判定」の行と、台帳の `catalog_refs` は、ケーススタディを見ないと書けないので、`catalog_refs: []` と理由を書いた。

## 時間

| 区分 | 開始 | 終了 | 分 |
| --- | --- | --- | --- |
| 着手：brief・GETTING_STARTED・README・00_core・台帳の README・RULES を読む、new_design.py | 06:38:43 | 06:43:30 | 5 |
| スキーマ・カタログ・P5・M_token_validation の typ を読み、構成を決め、token_types.yaml（発行方式・目録 23 行）を書く | 06:43:30 | 06:50:28 | 7 |
| claims.yaml（台帳 24 行）・hops.yaml（13 ホップ）を書く | 06:50:28 | 06:55:49 | 5 |
| 最初の lint（error 115）→ YAML の誤り・R1・L1b などを直す | 06:55:49 | 06:56:43 | 1 |
| catalog_answers.yaml（62 件・行列 49 セル・pairwise 21 件・問い 11）を書く | 06:56:43 | 06:59:28 | 3 |
| 追加前の 25 問 × 3（社員番号・部署・Auth0 の roles）→ lint error 0 | 06:59:28 | 07:00:49 | 1 |
| design.md の手で書く節・Full の節・付録 D（プロファイルとモジュールの記入欄）・付録 E（あいまいな点の決定）、render --write・--check、check_mermaid、check_slide_refs | 07:01:35 | 07:05:20 | 4 |
| このログ、コミット、PR | 07:06:06 | （PR の作成まで） | — |
| **計（着手から design.md の完了まで）** | 06:38:43 | 07:05:20 | **約 27 分** |

日付はすべて 2026-11-24。

## 結果

- `python tools/claim_lint research/pilot/scenario-b`（Full）：**error 0、warn 2、info 16**。抑止は使っていない
  - warn L69（C-groups）：Entra のグループの超過の上限 200 に合わせて max_items を 200 にしたため（50 を超える）。設計の判断として残した
  - warn L11（C-sub-unread）：Okta・Entra の AT の sub は IdP が既定で出し、入口は読まない。AT から外せないので残した
- `python tools/claim_lint render research/pilot/scenario-b --check`：OK
- `python tools/check_mermaid.py research/pilot/scenario-b/design.md`：2 つの図、失敗 0
- `python tools/check_slide_refs.py research/pilot/scenario-b`：問題 0
- `python tools/template_check.py`：error 0（テンプレートは変えていない）

## 迷った点（28 件）

| # | 欄 | 迷った理由 | 選んだこと |
| --- | --- | --- | --- |
| 1 | `catalog_answers.yaml` の `idp` | 5 つの IdP を使うが、`idp` は 1 つ（name・version）しか書けない | 主な IdP の Keycloak を書き、ほかの 4 つは `outside_enumeration.searched` に文書の URL を書いた |
| 2 | 台帳の `catalog_refs` | 「記入例ではすべての行に書く」とあるが、ブラインド記入ではケーススタディを見られない | 全行 `catalog_refs: []` と `catalog_refs_reason` |
| 3 | `issuance_profile.at_format` | 入口で作り直す構成は phantom に見えるが、IdP の AT は不透明でなく JWT。phantom にすると L62（E-phantom.1「外に出す AT に組織のクレームを載せない」）が Auth0 の名前空間つきの roles で warn になった | jwt にし、作り直しはホップ（reissue）と目録の内部トークンで表した |
| 4 | IdP 固有のクレーム（oid・tid・uid・token_use・realm_access・cognito:groups・scp・cid） | P5 の 1. は入口がこれらを使うよう書くが、名前空間なしの未登録名を受け手のいる行として書くと L1b が error にする | 台帳の行にせず、組織のクレーム（C-sub・C-roles）の `upstream_issuer.source_attribute` と、ホップの `validates.checks` に書いた。目録の `required_claims` からも外した（L7 が台帳の行を求めるため） |
| 5 | COGNITO_AT の `required_claims` | Cognito の AT には aud が無いが、L27 は required_claims に aud を求める | COGNITO_AT の required_claims を書かず、照合は H5 と C-client-id の enforced_at に書いた |
| 6 | Keycloak・Entra の AT の `typ` | ヘッダーの typ は ID トークンと同じ JWT で、L17 が「同じ typ」を error にする。typ の列は 1 つの文字列で、ペイロードでの区別を書く欄が無い | typ の欄に「JWT（…aud と azp で区別する）」のような区別の仕方を含む文字列を書いた |
| 7 | 作り直しのホップ（H7・H8）の `upstream` | 内部トークンの社員番号・部署は社員台帳から引くので、上流の AT に無い。L16 は「独自クレームが上流に無い」を例外なく error にする。上流が IdP ごとに 5 つあり、upstream は 1 つしか書けない | H7・H8 に upstream を書かず、ホップの note と design.md の 12. に書いた（寿命・宛先の絞り込みの機械の検査が走らない） |
| 8 | 同じ名前（sub）の 2 行 | Okta の sub は再利用されうるので別の行にしたいが、L1b は同名の行の description が違うと error | 2 行の description を同じ文にし、違いは rationale・note・not_meaning に書いた。読まない行は usage を protocol にした（identifier にすると L3 が reassignable で error） |
| 9 | 既定どおり・consumers: [] の行の列 | 台帳の README の 2. は列を減らす規則を書くが、Full の R1 はすべての列を求めた | Full なので全列を書いた |
| 10 | 名前空間の `style` | object なら構造の版のクレーム（namespace_version）と、その 25 問が要る | flat_prefix（Auth0 の書き方にもそろう） |
| 11 | 操作とサービスの対応 | brief は 6 つの操作と 2 つのサービスを挙げるが、どの操作がどのサービスかを書いていない | 注文を読む・管理・編集・社内文書は orders、経理台帳・給与明細は invoices |
| 12 | Okta の宛先 | Okta の aud は api://default で、注文と請求書で同じ | 入口が scp で経路のサービスを確かめる |
| 13 | Entra のグループの超過 | Graph で解決するか、アプリロール（roles）に切り替えるか | Graph（要求が groups を前提にしているため）。アプリロールは見直しの条件に書いた |
| 14 | ENTRA_AT の寿命 | Entra の既定は 60〜90 分で、ほかの IdP と違う | トークンの寿命のポリシーで 600 秒にする前提（確かめていない。12.） |
| 15 | 入口のヘッダーの上限 | Entra の groups 200 件を数えると、nginx の既定の 8 KiB を超える（R8） | 入口の nginx を 32 KiB にする値をその場に宣言した（`size.path`） |
| 16 | `issuance_profile.client_auth` | 値は 1 つだが、Cognito は private_key_jwt に対応していない | private_key_jwt とし、Cognito の例外を rationale と 3. に書いた |
| 17 | `tenant_binding` | Entra の tid の固定を書きたいが、書くと L9 がマルチテナントの検査を始める（と RULES から読んだ。試していない） | すべての行から外し、Entra は iss（tid を含む）の完全一致で表した |
| 18 | ログアウトの反映（B12） | Back-Channel Logout は Keycloak だけ。5 つの IdP でそろう手段が無い | BFF がログアウトのたびに社員台帳のログアウトの時刻を進め、入口が AT の iat と比べる（db_lookup） |
| 19 | 部署の出どころ | IdP の属性（Keycloak の属性・Okta のフック・Cognito の custom:*）か、組織の台帳か | 社員台帳（人事）。IdP の部署は却下の行（C-idp-department） |
| 20 | ロール・グループが無いときの `on_missing` | 拒否にすると、グループの無い Cognito の利用者（B16）が注文を読めない | 無視＋absent_semantics（ロールなし。既定値を使わない） |
| 21 | Full のプロファイル・モジュールの記入欄の置き場所 | テンプレートは〔Full：記入〕とするが、どのファイルに書くかを書いていない。new_design.py も作らない | design.md の付録 D に、節ごとの表としてまとめた |
| 22 | U11 の回答 | 新しい設計はヘッダーに転記しないが、外から来る同名のヘッダーの除去はこのイベントの対策 | 該当（現状の入口が当たり、除去を対策として書いた） |
| 23 | `q-authorized` に答えるクレーム | roles か scope か（questions.yaml は roles を取り違えやすい相手としている） | scope。roles には does_not_answer: [q-authorized] |
| 24 | 残った warn | L69・L11 を消すために値を変えるか | 設計の判断として残した（抑止しない） |
| 25 | `subject_states` の結果 | 行列の説明は「設計で足す対策を入れる前の姿」だが、設計書では許す遅れか対策を書く | この設計の対策（社員台帳の問い合わせ）を入れた後の結果を書いた |
| 26 | `pairwise` のワークロード | ポータル・入口をワークロードとして数えるか | 該当（入口の client credentials と内部トークンの発行者）。システムは対象外 |
| 27 | ID トークンの目録の行 | IdP ごとに 5 行にするか 1 行にするか | 1 行（`issuers` に 5 つ）。AT は宛先と検証の規則が IdP ごとに違うので 5 行 |
| 28 | YAML の流れの書き方 | `custom: の属性` のような「: 」を含む文と、「（iss, sub）」のようなカンマを含む文が、フロー形式の YAML で壊れた | `custom:*` と書き換え、カンマを含む文を引用符で囲んだ |

brief の 7. のあいまいな点 9 つの決定は、迷った点と別に design.md の付録 E に書いた（理由つき）。

## テンプレートの欠陥・気づき（10 件）

| # | 場所 | 内容 |
| --- | --- | --- |
| 1 | `tools/claim_lint`（L1b）と `profiles/P5_internal_propagation.md` の 1. | P5 は入口が Entra の tid・oid、Okta の uid、Cognito の token_use を使うよう書くが、名前空間なしの未登録名を受け手のいる行として台帳に書くと L1b が error。IdP 固有のクレームを「入口だけが読む上流の値」として書く手段が無い（迷った点 4） |
| 2 | L27 | Cognito の AT は aud を持たないのに、required_claims に aud を必須にする。P5 の 1.（client_id で照合する）と食い違う（迷った点 5） |
| 3 | 目録の `typ` と L17 | Keycloak・Entra の AT はヘッダーの typ が ID トークンと同じ JWT。typ の列は 1 つの文字列で、ペイロードの値（Keycloak の typ、Cognito の token_use）での区別を書く列が無い。L17 を通すには typ の欄に説明文を入れるしかない（迷った点 6） |
| 4 | L16 と `hops.upstream` | 作り直しで社員台帳から値を足す（IdP の AT に無い組織のクレームを内部トークンに書く）構成を、例外なく error にする。upstream が 1 つなので、複数の IdP の AT から 1 つの内部トークンを作る経路も書けない（迷った点 7） |
| 5 | `catalog_answers.yaml` の `idp` | 1 つの IdP しか書けず、複数の IdP の設計で R3・R3b・L2 が主な IdP 以外を見ない（迷った点 1） |
| 6 | `render`（鮮度の表など） | `flat_prefix` の名前空間の名前を `https://claims.example.com/.roles` のように「.」を挟んで表示する（JSON のキーは `https://claims.example.com/roles`。schemas の出力は正しい） |
| 7 | Full のプロファイル・モジュールの記入欄 | 書く場所（ファイル・節）が GETTING_STARTED・README・00_core のどこにも無く、new_design.py も作らない（迷った点 21） |
| 8 | `issuance_effects.yaml` の E-phantom.1 | 「外に出す AT」を、IdP の AT（入口だけが読む）と区別しない。名前空間を必須にする Auth0 と組むと必ず warn になる（迷った点 3） |
| 9 | 台帳の README の 2. と RULES の「R1 の必須の列」 | 既定どおり・consumers: [] の行の列を減らす規則が、Lite だけのものか全体のものか、README の 2. だけでは読み取りにくい（Full では減らない） |
| 10 | new_design.py | 作る catalog_answers.yaml に `questions`・`subject_states`・`pairwise` の節が無い。lint の error で気づくが、7 状態 × 7 層の鍵の名前（`subject-states/invited`、層の「RP・BFF のセッション」など）は RULES の例と catalog_check.py を読まないと分からなかった |

ほかの気づき（欠陥とまでは言えない）：テンプレートの本文（GETTING_STARTED・00_core など）は根拠として `research/template-design/...` を名指しするが、パイロットの書き手は research/ を読めない。読まずに書けたが、気になった。
