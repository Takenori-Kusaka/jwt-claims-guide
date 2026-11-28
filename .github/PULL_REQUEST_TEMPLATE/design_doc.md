<!-- このファイルは python tools/review_triage.py --write が templates/review/triage.yaml から作る。手で直さない -->
<!-- 設計書（台帳の YAML と design.md）の PR 用。PR を作る URL に ?template=design_doc.md を付けると、この様式になる -->

## 設計書

- 設計書のディレクトリ：
- Lite／Full：
- claim_lint の結果（error・warn・info の件数。error は 0 にする）：
- レビュアーに特に見てほしい点（設計書の 12. の自信のない点）：

## 提出前の自己点検（書き手が確かめる）

書き手が自分の設計書を開けば確かめられることを、55 行にまとめました（観点書 `templates/review/perspectives.md` の 78 問に当たる。行の末尾が問いの ID で、見る欄は観点書の同じ ID の問いにある）。レビュアーは、ここの問いには答えません。
満たす行に印を付け、満たさない・当てはまらない行は、印を付けずに行の末尾に理由を書いてください。レビュアーは、印の無い行を読み、**25 問の回答の行（必ず）と、【No なら Blocker】の行から 2 件を抜き取って、欄を開きます**（手順の段 0）。
区分と理由は `templates/review/triage.yaml` にあります。量と分け方は筆者の提案です（追跡 #56）。

### どの設計でも

- [ ] **【レビュアーが必ず抜き取る】** **【No なら Blocker】** 追加前の 25 問の回答（claim_request_*.md）は、どれも問いに答えていて、台帳の該当の行（namespace・shape・log_policy・pii_category・rationale）と同じことを言っているか（空欄でないことは lint の L72 が見る） — `pa-03`・`pa-05`・`pa-06`・`pa-10`・`pa-16`・`pa-18`・`pa-20`・`pa-23`・`pa-24`・`pa-25`・`pa-trace`
- [ ] 共通の基準（受け入れの検証・必須の欠落の拒否・型の固定・不変の ID・組織の名前空間・ログにトークン全文と個人情報を残さない）を、すべて満たしているか（満たさない基準があれば、Full にし、専門家に回したか） — `q-baseline-kept`
- [ ] （項目 9）アクセス元の文脈（IP・ネットワーク・端末）を、PEP が要求ごとに評価しているか — `cf-09`
- [ ] 受け手のすべてが、アルゴリズム・発行者・宛先・必須クレームを固定した組織の共通の検証部品で検証するか（受け手ごとの独自の設定・読み方があれば No） — `q-shared-validator`
- [ ] **【No なら Blocker】** テナント・権限の独自クレームを読む処理（ログ出し・ルーティングを含む）は、どれも受け入れの確認（署名・`iss`・`aud`・`exp`・`typ`）を全部通った後か — `q-validate-before-read`
- [ ] **【No なら Blocker】** `template:modules/M_token_validation#library-config` の「未検証の値を流すモード」の行と、各受け手の「明示した設定」に、検証の無効化・デバッグ・「欠けたら既定値で続行」のモードを持たない（持つなら本番で無効にする方法）と書いてあり、`claim_request#q18` の回答と一致するか — `q-no-unverified-passthrough-mode`
- [ ] 独自クレームごとに、寿命の 4 つの層（トークン・値の鮮度・セッションと RT・定義）が別々の欄に書いてあるか（1 つの数字だけなら No） — `q-four-lifetimes-written`
- [ ] クレームの名前・型・形の変更を破壊的変更として扱い、「受け手が先、発行者が後」の順（事前の通知・プレビュー・並行発行の期間）で進める手順が書いてあるか — `q-change-order`
- [ ] ログ・トレースにトークン全文を出さず、記録する HTTP ヘッダーを許可リストにしているか（障害調査で共有する HAR ファイル・ログからトークンを除く手順を含む） — `q-token-logging`
- [ ] 監査ログ自体を機微な情報として扱い、保護と取り扱いの方針（読める人・保存期間）を書いているか — `q-audit-log-protected`
- [ ] 監査には署名されたトークンの中の `txn` を使い、改ざんできる `traceparent` は観測だけに使っているか — `q-trace-id-trust`
- [ ] 共通の検証ライブラリの採用率と版、`aud`・型の検証失敗の件数、台帳と実際の発行のずれを、誰がどの周期で測るかが書いてあるか — `q-operational-metrics`
- [ ] 同じ事実（組織の寿命の上限・受け手が照合する内容・受け手の一覧）を書いた 2 か所以上の欄（目録の `note`・5.1・生成の表・矢印の表）が、同じ値と同じトークンを指しているか — `q-limit-consistency`

### 当てはまるときだけ：委任がある（代理で動く主体がいる）

- [ ] （問 21）委任のトークンに載るなら、`act`・承認 ID との関係（誰の値か、どちらで照合するか）が書いてあるか — `pa-21`
- [ ] エージェントを独立した主体（自分の `client_id`・ワークロードの ID）として登録し、自分の資格情報で動くか（共有アカウントや利用者のトークンを借りていれば No） — `q-agent-own-identity`

### 当てはまるときだけ：認証の強さ・新しさで判断する


### 当てはまるときだけ：トークンの値を DB の層まで運ぶ

- [ ] **【No なら Blocker】** （項目 1）DB の文脈を設定するのは、検証済みのトークンを受けた注入者だけか — `cd-01`
- [ ] **【No なら Blocker】** （項目 2）PostgreSQL では `SET LOCAL` か `set_config(…, true)` で、取引の単位で設定するか — `cd-02`
- [ ] **【No なら Blocker】** （項目 3）SQL Server では `@read_only = 1` と接続主体の確認をするか — `cd-03`
- [ ] **【No なら Blocker】** （項目 6）RLS をすり抜ける主体（スーパーユーザー・`BYPASSRLS`・テーブルの所有者・SECURITY DEFINER の関数）を、通常の経路から外しているか — `cd-06`
- [ ] （項目 7）DB のユーザーの対応付けは、名前でなく不変の ID で行うか — `cd-07`
- [ ] （項目 9）利用者単位の監査が要るなら、利用者の ID を DB まで伝えているか — `cd-09`
- [ ] **【No なら Blocker】** （項目 10）クレーム・文脈が欠けたら全件を許さず拒否し（文脈なしで 0 行）、DDM・RLS のほかに最小権限と監査も使うか — `cd-10`
- [ ] データ層の設定（文脈の設定・すり抜ける主体・接続の寿命）を製品の既定値に任せず、設計書に書き、試験で確かめる計画があるか — `cd-11`
- [ ] セッション変数やサービスの ID で分離するなら、全 SQL に明示的なテナントの条件を付ける規約と、それを確かめるレビューか検査があるか — `q-sql-tenant-predicate`
- [ ] **【No なら Blocker】** DB の文脈の値を、文字列の連結でなくパラメータで渡しているか（`SET LOCAL` はバインド変数を受けないので、`set_config($1, $2, true)` を使うか） — `q-db-context-parameterized`
- [ ] 機微なデータを DDM・RLS だけで守らず、最小権限と監査を併用しているか — `q-ddm-rls-only`

### lint の規則ができるまで（機械で決まる。規則ができたら、ここから外す）

- [ ] R1 の必須の列に、組織独自のクレームの prior_art_search、認可・識別子の文字列のクレームの value_normalization、受け手ごとの consumer_access_path を足す（規則の案：N1。いまの lint が一部を見る） — `dc-02`・`dc-04`・`dc-08`
- [ ] （名前）名前が組織の名前空間（`namespaces` に宣言した URI）の中にあり、予約名と照合した記録があるか（規則の案：L34。いまの lint が一部を見る） — `dc-03`・`pa-04`
- [ ] （形）複数の値を JSON の配列で運び、区切り文字の連結も JSON の文字列化も使っていない、と台帳の `shape` から言えるか（規則の案：L36） — `dc-06`・`pa-07`
- [ ] on_missing が拒否なのに、carried_in の種別の一部の required_claims に無い行（無いのが正規のトークンがある）（規則の案：N6。いまの lint が一部を見る） — `dc-07`・`pa-09`・`q-required-rejected`
- [ ] 認可に使うオブジェクト型のクレームに、内側の型（受け手のスキーマの properties）と比べ方を求める（規則の案：L24・N5） — `pa-08`
- [ ] 種別の required_claims が、その種別を運ぶホップの custom_claims に含まれる（25 問の問 14 と目録の必須の食い違い）（規則の案：N3。いまの lint が一部を見る） — `pa-14`
- [ ] 台帳の consumers・enforced_at.service と、ホップの to の名前が結びつく（生成の矢印の表が空になる）（規則の案：N7。いまの lint が一部を見る） — `pa-22`
- [ ] 25 問の回答（claim_request_*.md）が、ほかのクレームの回答と同じ文なら warn（規則の案：N11。いまの lint が一部を見る） — `pa-gate`
- [ ] iat・amr・sid の行の usage が authz、または enforced_at で認証の時刻・強さ・セッションの判断に使っていれば warn（規則の案：N16） — `q-auth-context-semantics`（当てはまるときだけ：認証の強さ・新しさで判断する）
- [ ] 組織の外に届く種別（lite_criteria.crosses_boundary が Yes のときの外向きの aud）に subject_type を求める（規則の案：N10） — `q-pairwise-external`
- [ ] （アンチパターン：型を決めない・配列を区切り文字列にする）型と形が台帳で 1 つに固定され、受け手のスキーマ（`schemas/*.consumer.schema.json`）と一致しているか（規則の案：L24。いまの lint が一部を見る） — `ap-2-3`
- [ ] **【No なら Blocker】** どのトークンのクレームも、認証の秘密（パスワード・API キー）と平文の個人情報（生年月日・住所など）を含まない、と台帳の `data_category`・`pii_category` から言えるか（規則の案：L51。いまの lint が一部を見る） — `q-no-secret-or-raw-pii`
- [ ] 書き手がフック（authoritative_writer の writer にフック・hook・Lambda）の行で、pii_category が個人情報・要配慮個人情報なら warn（規則の案：N14） — `q-hook-adds-raw-pii`
- [ ] 個人情報の行で、carried_in の種別の holder・visible_to に、consumers に無い相手がいれば warn（L6・L65 の拡張）（規則の案：N4。いまの lint が一部を見る） — `q-minimal-per-recipient`
- [ ] 受け手の照合の宣言（claims の enforced_at の check、hops の validates.checks）に、入れ子の act のパス（act.act・act.act.sub など、act が 2 つ以上つながる名前）があり、同じ文に拒否・打ち消しの語（拒否・拒む・reject・使わない・照合しない・読まない）が無ければ warn（L12 の拡張。L12 は path に act が 2 つある台帳の行だけを見る）（規則の案：N24。いまの lint が一部を見る） — `q-agent-delegation-claims`
- [ ] （項目 3）外部のトークンは入口で終わらせ、内部専用の形（内部の発行者・内部の `aud`）に替えているか（規則の案：L41） — `cf-03`・`cf-04`・`ap-2-6`
- [ ] Txn-Token の種別（kind が txn_token）を運ぶホップで、(1) ホップに運び方の列 transport を足して宣言にし、txn_token_header でなければ warn（L43 は目録の種別ごとの transport だけを見る。代わりの案：validates.checks・note が Authorization ヘッダーを名指し、同じ文に打ち消し〔読まない・使わない・受けない〕が無ければ warn）、(2) ホップの to（受け手）が tctx の行の consumers・enforced_at.service に無ければ warn（L11 は consumers に挙げた受け手だけを見る）（規則の案：N25。いまの lint が一部を見る） — `cf-06`・`q-txn-scope-fixed`
- [ ] **【No なら Blocker】** （項目 7）入口で検証しても、各サービスでも検証しているか（すべてのホップの `validates` に中身があれば Yes）（規則の案：L46） — `cf-07`・`q-unverified-claim-extraction`・`ap-1-2`
- [ ] （項目 10）`sub`・`act`・`txn`・承認 ID を分けて記録し、トークン全文は記録しない、と `log_policy` に書いてあるか（規則の案：L45） — `cf-10`・`ap-2-8`
- [ ] ホップの max_lifetime が、そのホップが運ぶ種別（token_type）の max_lifetime より短ければ warn（ホップの寿命は運ぶトークンの受け入れの上限。短く書くと L16 が上流との比較を見落とす）（規則の案：N27。いまの lint が一部を見る） — `q-hop-lifetime`
- [ ] 採用の Txn-Token の required_claims に、草案の必須（iat・aud・exp・txn・sub・scope・req_wl）がそろう（規則の案：N8。いまの lint が一部を見る） — `q-txn-required-claims`
- [ ] **【No なら Blocker】** 内部・委任のトークン種別（internal_token・txn_token と、act を運ぶ種別）に log_policy を求める（規則の案：N18。いまの lint が一部を見る） — `ap-2-9`・`q-internal-delegation-token`
- [ ] どのトークンも、URL・クエリ・リダイレクトの断片以外で運ぶ、と目録の `transport` から言えるか（WebSocket など、ヘッダーを付けられない経路の扱いが書いてあるか）（規則の案：L54） — `q-token-not-in-url`
- [ ] logout_token の種別に、nonce の拒否と、sub か sid の必須を求める（規則の案：N9。いまの lint が一部を見る） — `q-typ-distinguishes`
- [ ] **【No なら Blocker】** 認可・識別子のクレームをヘッダー以外に写す（integrity_until の db_session・cache・queue_message・log）とき、その写し先を書けるのが入口・注入者だけという宣言を求める（L67 の残り）（規則の案：N15。いまの lint が一部を見る） — `q-unwrapped-value-authz`
- [ ] （項目 5）DB のロールを選ぶクレームを高権限として扱い、発行元を限定しているか（規則の案：L48） — `cd-05`（当てはまるときだけ：トークンの値を DB の層まで運ぶ）
- [ ] （項目 8）トークンと接続の寿命を分け、プールの接続の最大寿命（`connection_max_lifetime`）と、剥奪を開いた接続に届かせる手段を決めたか（規則の案：L49） — `cd-08`（当てはまるときだけ：トークンの値を DB の層まで運ぶ）
- [ ] status が deprecated の行に、sunset_on・alt・consumers_migration を求める（L18 は読む受け手がいることだけを知らせる）（規則の案：N17。いまの lint が一部を見る） — `q-deprecated-deadline`
- [ ] 種別の key_rotation に、署名の鍵の名前（signing_key。列の追加を伴う。signing_key_scope は鍵の範囲の 3 値で、どの鍵かを決めない）を宣言にし、retire_after_seconds が 0 より大きい種別で、同じ signing_key の種別の retire_after_seconds が、その種別たちの最も長い max_lifetime より短ければ warn（max_clock_skew は足さない。外部の IdP の鍵・起動ごとの鍵のように retire_after_seconds が 0 の種別は見ない。L17 は鍵のローテーションについては unknown_kid・jwks_cache_ttl の有無だけを見る。代わりの案：note が別の種別と同じ鍵と書けば、その種別と比べる〔書き方でずれるので下げた〕）（規則の案：N26。いまの lint が一部を見る） — `q-key-rotation`

## レビュアーへ

人が答える問いは `templates/review/short_list.md` にあります（`python tools/review_triage.py --design <ディレクトリ>` で、この設計に当たる問いの 1 枚が出ます）。
