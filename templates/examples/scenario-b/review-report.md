<!-- template_version: 0.4.0 -->
# レビューレポート：設計書（Full）記入例 シナリオ B（社内業務システム＋AI エージェントの委任）

> **記入例です。** `templates/review/` の教材を使って、シナリオ B の設計書を改めてレビューしたものです。対象はコミット `a6aad45`（PR #44 の点検を反映する前の版）で、**今のディレクトリの設計書ではありません**（今の版は PR #44 の指摘を直した後のもの）。1.〜8. は教材の作成とは別の LLM のセッションが書き、9. は教材の作成者が書きました。人による点検は未実施


## 1. 基本情報

| 項目 | 値 |
| --- | --- |
| 対象 | `templates/examples/scenario-b/`（design.md・claims.yaml・token_types.yaml・hops.yaml・catalog_answers.yaml・claim_request_*.md 9 件・schemas/・variants/）。版はコミット a6aad45（PR #44 の点検を反映する前の版）の読み取り専用の写し。設計書の版の表記は 0.3.0 |
| Lite／Full | 設計書の判定は Full。`catalog_answers.yaml` の `lite_criteria` は crosses_boundary・delegation_or_exchange・new_issuer が true、multitenant・regulated が false。README の 5 問（`template:README#lite-criteria`）で 1 つでも Yes なら Full なので、判定は合う（確認済み） |
| 実施した手順の段 | 0〜7。段 8（対応を確かめて閉じる）は作成者の対応の後なので未実施。段 0 は、現行の claim_lint で error が 1 件出た（F01）。手順では「error が 0 でなければ返す」だが、較正のデータを取るため、返す判断を記録したうえで段 1 以降も続けた |
| レビュアーと役割 | LLM のセッション（Claude Opus 5.5、claude-opus-5-5）。1 名（役割を切り替えた）。procedure.md の「1 名で行う場合」の順で、攻撃者 → 受け手 → 発行者 → 運用 → 個人情報 → クライアントの順に読んだ（2026-11-23、同じセッションの中で切り替え）。「時間を分ける（段 0〜3 と段 4〜6 を別の日）」は満たしていない。指摘の出どころは、見つけた問い・欄で「観点」などに分けた。すべて LLM（本レポートの書き手）の判断で、人のレビュアーの採否は未了 |
| 実施日 | 2026-11-23 |
| 使った教材の版 | `templates/review/`（template_version 0.4.0。ブランチ issue-5-review-materials のコミット前の版。ベースのコミットは 9202586。レビューの後に 9. の問いを足した）。判断の木・対比表・escalation.md・rationale_rubric.md・report_template.md も同じ版 |
| CI の結果 | 現行の claim_lint（ワークツリーの tools/claim_lint、`--profile full --also-scan design.md`）：**error 1・warn 6・info 28**（claims 46・token_types 24・catalog_events 62）、FAIL。error は `L1b` の `C-tctx`（草案の名前を名前空間なしで使い、usage が authz）。設計書の 1. の貼り付けは error 0・warn 7・info 28（`C-tctx` は warn）で、**一致しない**。差は `tools/claim_lint/draft_claims.yaml` の注記「usage authz・identifier の草案名は error のまま」による規則の変更と見られる（スナップショットより後の lint で走らせたため）。3.3 の「記入例 error 0・warn 7」も同じく古い。F01 |
| 抜き取りの結果 | 乱数の種 20261123（Python の random.Random で、claims.yaml の採用 34 行と却下 8 行からそれぞれ 5 行）。採用：C-jti・C-dpop-htm・C-dpop-htu・C-email・C-v。却下：C-kc-client-id・C-realm-access・C-cognito-custom-role・C-may-act・C-rctx。10 件中 合格 6・不合格 4（C-jti・C-email・C-cognito-custom-role・C-may-act） |
| 問いの回答 | 全 160 問（perspectives.md の 1.〜6.）。定義 Yes 42／No 15／該当なし 1。発行 Yes 8／No 2／該当なし 0。伝搬 Yes 19／No 6／該当なし 1。検証 Yes 10／No 3／該当なし 1。認可 Yes 12／No 9／該当なし 7。運用 Yes 12／No 12／該当なし 0。合計 Yes 103／No 47／該当なし 10 |

段 1・2 の記録（手順の終わりの条件の写し）：

- 12.（自信のない点）から拾った候補：issuance_profile が 1 つ、H15 を L16 で確かめていない、req_wl・tctx が草案、KC_AT の client_id、名前空間のマッパー、RT の再利用の検知、CIBA の流れ、ASVS、ledger の引き直しの遅れ。範囲の外：P2・P3・P6、運用者・break-glass、エージェントの実行基盤を組織の外に置く構成
- 矢印ごとの攻撃者が触れるもの：U→P（Cookie）、P→G（社員のブラウザの要求に付く x-user-* などのヘッダー。KC_AT は BFF だけが持つ）、GA→G（グループ会社のアプリが送る EXT_AT とヘッダー、グループ会社の IdP の管理者が変えられる groups・属性）、G→O/L/D/PY（INT_AT。網の中）、O→L（TXN。orders が選べる要求の本文と tctx の組）、L→DB（DB のセッション変数）、L→EV→W（メッセージの本文）、AR→MCP（モデルの出力で決まるツールの呼び出しと本文、DPoP の proof）、MCP→INV（要求の本文の金額・相手先）
- 6. の「要る」問いと判断の木の節：q-sub・q-actor → keep-sub-exchange（合う）、q-req-wl・q-txn → txn-tctx（F01・F03・F04 で食い違い）、q-peer → peer-mtls（合う）、q-authorized → rar-vs-custom（F27）、q-resource → aud（合う）、q-holder → cnf（合う）、q-user → existing-claim-first・carry-or-query（F07）、q-still-valid（pending）→ lifetime-by-situation（F16）

## 2. 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 出どころ | 種別 | 取り違えた問い（種別が目的と仕組みの不一致のとき） | 判定 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F01 | `template:00_core#ci-results`（design.md 1.）、design.md 3.3 の claim_lint の行、design.md 12. の「Txn-Token の req_wl・tctx」の行、design.md 6. の q-txn の行、`C-tctx.usage`・`C-tctx.enforced_at`、procedure.md 段 0、観点 `pa-trace` | 現行の lint で `L1b` error（C-tctx）が出て段 0 の条件を満たさない。設計書の 1.・3.3 の件数（error 0・warn 7）と 12. の「L1b を warn に直した」は、現行の規則（草案名でも usage authz なら error）と合わない。根は台帳の中の食い違いで、6. の q-txn の行は `C-txn`・`C-tctx` を「監査の相関だけ。認可には使わない」とするが、`C-tctx` は usage authz で、ledger・payment-worker が operation を照合して拒否する（enforced_at）。usage を直すか 6. を直し、lint の結果を貼り直す | Minor | テンプレート項目 | 実装とのずれ | — | 採用 |
| F02 | `registry:hops#validates`（H10、H5）、H10 の note「ledger は INT_AT を受けない」、`C-acr.enforced_at`（ledger）・`C-auth-time.enforced_at`・`C-sid.enforced_at`・`C-sub.enforced_at`（ledger「TXN の sub と INT_AT の sub が一致」）、`INT_AT_LEDGER.revocation`（db_lookup）、design.md 付録 B、観点 `q-step-up-path-coverage`・`q-step-up-by-rs`・`q-revocation-delivery` | orders → ledger の経路（H10）で ledger が受けるのは TXN だけで、TXN には acr・auth_time・sid が無い（TXN.required_claims は iss・iat・aud・exp・txn・sub・req_wl）。経理の操作の追加認証（mfa、auth_time ≤ 900。付録 B）と、重要な操作ごとの Keycloak のセッションの引き直し（B12 の対策）は INT_AT_LEDGER（H5）の上にしか定義されていない。一方 `C-tctx.enforced_at` の ledger は operation に ledger.post を受け入れるので、経理の書き込みが H10 の経路では追加認証とログアウト後の拒否を通らずに実行されうる。`C-sub.enforced_at` の ledger の照合（INT_AT の sub と一致）も H10 では行えない。H10 で ledger が何を確かめて ledger.post を許すかを決め、acr・sid を TXN で運ぶか別の手段で確かめるか、H10 では ledger.post を受けない、のどれかにする | Major | 観点 | 候補の漏れ | — | 採用 |
| F03 | `registry:hops#scope`（H4・H9・H10 は orders.read、H5 は ledger.read）、`C-tctx.enforced_at`（ledger：ledger.read・ledger.post）、`C-tctx.value_vocabulary`（values: [operation]）、観点 `q-txn-scope-fixed`、判断の木 `txn-tctx` | Txn-Token の tctx が、元のトークンに無い操作を運ぶ。H9・H10 の TXN の scope は orders.read で、元の INT_AT（H4）も orders.read、INT_AT_LEDGER（H5）も ledger.read だけで、ledger.post を許すトークンはどこにも無い。それでも ledger は tctx の operation が ledger.post なら受け入れる。tctx は「元のトークンと同じかそれ以下」で決めるべきで（q-txn-scope-fixed）、ここでは tctx が権限の付与に使われている。あわせて `C-tctx.value_vocabulary.values` は項目名の [operation] だけで、operation の値の語彙（ledger.read・ledger.post・payment.notify）と、元のどの scope から決めるかの規則が台帳に無い（assumption「入口の経路の表で決まる」だけ） | Major | 観点 | 目的と仕組みの不一致 | `txn-tctx`（取引の内容の固定を、元のトークンに無い権限の付与で答えた） | 採用 |
| F04 | `C-iss`・`C-sub`・`C-aud`・`C-exp`・`C-txn`・`C-req-wl`・`C-tctx` の `consumers`・`enforced_at`（payment-worker）、`C-req-wl.assumption`、hops H12・H13 の validates、design.md 2.2、catalog_answers の U13、`TXN.long_running`、観点 `q-long-running`・`pa-22`・`q-outside-catalog` | payment-worker の扱いが 2 通りに書かれている。H12・H13・2.2・U13・TXN.long_running は「メッセージにはハッシュした user_id・txn・approval の ID だけを入れ、トークンを入れない」。一方、台帳の 7 行は payment-worker を受け手にし、「メッセージに付いた TXN の iss・aud・txn」を検証し、`C-exp` は「処理が TXN の寿命を超えたら自分のワークロード ID で TTS から取り直す」とする。これは `C-req-wl.assumption`「TXN を求めてよいのは入口だけ」とも、payment-worker の照合「req_wl が入口の SPIFFE ID」とも両立しない（取り直した TXN の req_wl は payment-worker になる）。I22 の回答にも、入口以外が TXN を求める発行は無い。どちらかに決め、台帳・目録・カタログの回答をそろえる | Major | 観点 | 実装とのずれ | — | 採用 |
| F05 | `C-department.volatility`・`propagation_delay`（330）・`assumption`（人事の台帳から 1 時間ごとに Keycloak へ同期）、`INT_AT_LEDGER.revocation`（db_lookup）、hops H11 の validates（current_setting('app.department')）・custom_claims・note（部署は DB の側で社員の表から引く）、design.md 9.1 の DB の接続の層、9.2、claim_request_department.md の問 2、観点 `dc-01`・`pa-02`・`ap-2-2`・`q-freshness-mitigation`・`q-copies-outlive`・`cd-01` | 部署の反映の遅れは、assumption の同期の周期で最大 3600 秒（＋トークンの 330 秒）になり、volatility・propagation_delay の 330 秒、問 2 の「330 秒まで古い値が残る」は前提として誤り。ledger の「操作のたびに Keycloak の利用者の属性を引き直す」（B11 の対策）も、Keycloak の値そのものが最大 1 時間古い。さらに ledger の部署の出どころが 3 通りに書かれている：H5・INT_AT_LEDGER は Keycloak の管理 API、H11 の note と 9.1 は DB の社員の表、H11 の RLS は `app.department` のセッション変数（誰がどの値から設定するかは無い。H11 の custom_claims は tenant_id・user_id だけ）。DB の社員の表の鮮度も無い。正しい遅れの値、異動の即時の反映が要るなら人事の台帳からの通知の経路、ledger の部署の出どころを 1 つに決める | Major | 観点 | 前提の誤り | — | 採用 |
| F06 | `C-roles.volatility`（330）・`upstream_issuer`・`on_revoke`・`enforced_at`（orders：管理の操作は Keycloak の利用者のロールを引き直す）、`EXT_AT.revocation`（exp_only 5430・IdP ごとの停止）、hops H3・H8、design.md 9.2 の末尾の文、観点 `q-freshness-mitigation`・`q-external-user-deprovision`・`ap-2-2` | グループ会社の社員（EXT_AT → H8 → INT_AT）のロールは EXT_AT の groups から作るので、上流でロールを外しても、EXT_AT の受け入れの上限（5430 秒）＋INT_AT（330 秒）まで残りうる。C-roles の volatility 330 はこの経路では成り立たない。9.2 の「入口が EXT_AT を受けるたびに読み直す」は同じ古い EXT_AT を読み直すだけで、鮮度を上げない。停止も利用者単位の手段が無く、入口の「IdP ごとの停止」しかない。orders の「管理の操作は Keycloak のロールを引き直す」は、Keycloak にいないグループ会社の社員には効かない。外部の利用者の剥奪の遅れの上限と、管理の操作での引き直し先（各社のディレクトリ）を書く | Major | 観点 | 候補の漏れ | — | 採用 |
| F07 | `C-sub.enforced_at`（orders：注文の持ち主の列と照合、invoices：請求書の持ち主と一致）・`C-user-id.enforced_at`（orders：注文の持ち主と照合、invoices：請求書の持ち主と照合）、`C-sub.value_normalization`（case as_is）・`C-user-id.value_normalization`（case lower）、`C-sub.spec_version`、claim_request_user_id.md の問 3、観点 `q-object-level-authz`・`q-identifier-choice`・`q-registered-synonym` | STS のトークンでは sub と user_id に同じ値を書く（問 3）のに、orders と invoices は両方を持ち主の照合に使うと書き、照合のキーが 1 つに決まっていない（シナリオ A の A02 と同じ型）。しかも sub は「対応表の値をそのまま」、user_id は「小文字の UUID」に正規化するので、対応表が大文字を含むと 2 つの値が食い違い、受け手や実装によって持ち主の判定が分かれる。照合のキーを 1 つに決め、もう一方は照合に使わないと `not_meaning` に書く。あわせて `C-sub.spec_version` が draft-ietf-oauth-transaction-tokens-11 になっている（sub は RFC 7519） | Major | 観点 | 実装とのずれ | — | 採用 |
| F08 | `C-sid.assumption`（ledger は Keycloak の管理 API を読み取り専用のサービスアカウントで引ける）、`INT_AT_LEDGER.revocation`（db_lookup）、`C-roles.enforced_at`（orders）、catalog_answers の I05（対象外：Keycloak から client credentials の AT を出さない）、hops H3（groups の超過はディレクトリで引き直す）、`template:00_core#token-inventory`、観点 `q-outside-catalog`・`q-dependency-outage` | ledger・orders が Keycloak の管理 API を引くには、サービスアカウントのトークン（Keycloak では client credentials の grant で出る）が要るが、I05 は対象外と答え、目録にもそのトークン（寿命・保存場所・管理 API のロールの範囲・鍵）が無い。入口が Entra のディレクトリを引く資格情報（H3）も目録に無い。どちらも利用者のセッション・属性を読める強い権限の資格情報で、漏れたときの影響と失効の手段を決める必要がある。I05 を該当にし、目録に行を足す | Major | カタログ外の質問 | 候補の漏れ | — | 採用 |
| F09 | catalog_answers の I26 と `subject_states`（credential-change：ほかの端末の SSO セッション・RT・BFF のセッションは残る。「残りを許すかは design.md の 12.」）、design.md 12.、`RT.revocation`、観点 `q-revocation-delivery`・`pa-trace` | パスワードの変更・リセットの後も、ほかの端末の SSO セッション・RT・BFF のセッションが最大 36000 秒残る（回答の記述では Keycloak の「Sign out from other devices」が未チェックの既定）。乗っ取りへの対処のリセットで、攻撃者のセッションが止まらない。カタログの回答は判断を「design.md の 12.」に送っているが、12. にその行が無い（参照先の欠落）。リセットで全セッションを終える設定（またはその却下の理由と代わりの手段）を決める | Major | 観点 | 候補の漏れ | — | 採用 |
| F10 | `C-department.pii_category`（個人情報）・`log_policy`（記録する）、claim_request_department.md の問 20、design.md 3.2 の「ログにトークン全文と個人情報を残さない：満たす」、観点 `q-baseline-kept`（`pa-20` は台帳と一致するので Yes） | 部署を個人情報と区分しながら、値のままログに残す。3.2 の共通の基準は「満たす」と書いており食い違う。ハッシュ・記録しないにするか、基準から外す理由を書いて escalation の baseline-unmet に回す | Major | 観点 | 実装とのずれ | — | 保留（baseline-unmet に回した） |
| F11 | `C-scope.carried_in`（KC_AT・AGENT_AT・TASK_AT だけ）、INT_AT 系の `required_claims`（scope なし）、hops H4〜H8 の scope、H3 の note（scope は入口が組織の語彙にそろえる）、`C-client-id.enforced_at`（orders：記録するだけ）、観点 `q-scope-and-role`・`cf-05` | ホップの表は INT_AT 系に scope（orders.read など）を宣言し、L16 もそれで「絞った」と判定するが、台帳では INT_AT 系に scope が載らず、受け手（orders・ledger・docs・payroll）は scope を確かめない。宣言した絞り込みがトークンに存在しない。特に H3 → H8 のグループ会社のアプリ（組織の外のクライアント）に委ねた範囲を orders が確かめられず、利用者のロールの全部で操作できる。INT_AT 系に scope を載せて受け手で確かめるか、宣言から外して理由を書く | Major | 観点 | 実装とのずれ | — | 採用 |
| F12 | hops H11（validates・note・custom_claims）、`template:modules/M_data_layer#db-context-setter`・`#pool-context`・`#masking-rls-bypass`・`#connection-lifetime`（記入なし）、`registry:claims#integrity_until`（C-tenant-id・C-user-id に無い）、観点 `cd-01`・`cd-06`・`cd-11`・`q-db-context-writers`・`q-ddm-rls-only`・`q-unwrapped-value-authz` | データ層の判断が H11 の 3 行と note だけで、RLS をすり抜ける主体（スーパーユーザー・BYPASSRLS・SECURITY DEFINER の関数。FORCE が扱うのはテーブルの所有者だけ）、ledger が接続に使うロールの権限、注入者以外が同じ接続・取引で SQL を流せないか（RESET・別の set_config）、最小権限と監査の併用、設定を試験で確かめる計画が無い。DB のセッション変数に写す値（app.user_id・app.department）を書けるのが注入者だけであることも、台帳の `integrity_until` に無い（シナリオ A の A04 と同じ型。ここでは分離の単位がテナントでなく部署なので Major とした） | Major | 観点 | 候補の漏れ | — | 採用 |
| F13 | 設計書の全体（プロファイル P1・P4・P5、モジュール M_token_validation・M_authz_pdp・M_sender_constraint・M_privacy_minimization・M_data_layer・M_idp_keycloak の〔Full：記入〕の欄が無い）、`template:README#profile-combination` のモジュールを使う条件、観点 `q-validate-before-read`・`q-token-logging`・`q-audit-log-protected`・`q-scope-elevation-logged`・`q-operational-metrics` | Full で、README の条件ではこの 6 つのモジュールと 3 つのプロファイルの〔Full：記入〕を書くが、設計書にも別のファイルにも記入が無い。多くの問いは台帳・ホップの欄で代わりに答えられたが、次は設計として決まっていない：独自クレームを検証の後にだけ読む順序（ログ出し・ルーティングを含む）、ログに残す HTTP ヘッダーの許可リストと HAR・ログからトークンを除く手順、監査ログの保護（読める人・保存期間）、エージェントのスコープの昇格の記録、共通の検証部品の採用率と版の測定（付録 A に無い） | Major | テンプレート項目 | 候補の漏れ | — | 採用 |
| F14 | `TXN.required_claims`・`schemas/TXN.consumer.schema.json` の required（tctx なし）、`C-tctx.on_missing`（拒否）・`usage`（authz）、観点 `dc-12`・`q-required-rejected` | tctx は欠けたら拒否・認可に使うと台帳に書くのに、TXN の必須クレームと受け手のスキーマに無い（シナリオ A の A08 と同じ型）。lint の L7 の逆向きの検査は、TXN の aud が信頼ドメインで受け手の名前を含まないため当たらない。ledger の照合が「一致すること」なので欠落は結果として拒否になると見て Minor とした | Minor | 観点 | 実装とのずれ | — | 採用 |
| F15 | `C-scope.value_vocabulary`（openid・invoices.read・invoices.pay・invoices.refund、extensible false）・`max_items`（4）・`max_bytes`（49）・`overflow_strategy`、hops H2 の scope、`C-scope.enforced_at`（gateway：openid があること。ほかは読まない）、H4 の note（scope の部分集合だけを写す）、観点 `dc-11`・`q-size-limit`・`q-scope-semantics` | KC_AT の scope（H2）の orders.read・ledger.read・docs.read・payslip.read が語彙に無く、openid を足すと 5 件・53 バイト（"openid orders.read ledger.read docs.read payslip.read"）で max_items・max_bytes を超える。「上限で固定（超えない値域）」が成り立たず、R8 の計算もこの分だけ小さい（経路の上限まではまだ余裕がある）。gateway の「ほかは読まない」と H4 の「scope の部分集合を写す」も食い違う | Minor | 観点 | 実装とのずれ | — | 採用 |
| F16 | `issuance_profile.rt_strategy`（根拠 RFC 9700 §4.14.2）・`RT.rt_rotation.reuse_detection`（unverified）、`issuance_profile.sender_constraint` の rationale（「none にした場合の比較は design.md の 4.」、refs slide:p08-rotation）、観点 `q-rt-policy-by-client` | RT を持つのは機密クライアント（BFF、private_key_jwt）なのに、公開クライアントへの要求である RFC 9700 §4.14.2 を根拠に引く（RR4・RR5。シナリオ A の A16 と同じ型）。ローテーションそのものの害は小さいが、根拠は状況に当たらず、再利用の検知も確かめていない。sender_constraint の理由は比較の節を「4.」と書くが、実際は 3.3 | Minor | 観点 | 理由の不備 | — | 採用 |
| F17 | claim_request_*.md 9 件の問 4・5・16・17・18・23・25（同文）、問 25（「Keycloak の Evaluate で KC_AT」「schemas/INT_AT.issuer.schema.json」）、claim_request_task_id.md・claim_request_approval_id.md の問 23・25、観点 `pa-gate`・`pa-23`・`pa-25` | 9 件の回答の 7 問が同文の写し。写しの誤りとして、問 25 はどのクレームでも INT_AT の発行側のスキーマを挙げるが、department は INT_AT_DOCS、employee_id は INT_AT_PAYROLL に載り（INT_AT.issuer.schema.json に department は無い）、task_id・approval_id は Keycloak が出さず AGENT_AT・TASK_AT に載る。task_id・approval_id の問 23 も「Keycloak のマッパー」を発行者に挙げる（RR6） | Minor | 観点 | 理由の不備 | — | 採用 |
| F18 | claim_request_idp.md の問 9（無ければ監査に unknown と書き、処理は続ける）、`C-idp.on_missing`（拒否）・`absent_semantics`（拒否）・hops H4 の照合（必須。無ければ拒否）、`C-v`・`C-sid` の `absent_semantics` が無い、観点 `pa-09`・`dc-07` | idp の欠落の扱いが 25 問と台帳で逆。C-v・C-sid は on_missing 拒否だが absent_semantics の列が無い。idp は表示・監査だけの値なので Minor とした | Minor | 観点 | 実装とのずれ | — | 採用 |
| F19 | `C-act.enforced_at`（invoices：act の方針表で、その代理者に許した操作だけ）、`C-may-act.rationale`（STS の委任の記録とツールの方針表）、`template:profiles/P4_ai_agent_delegation#delegation-policy`・`#human-approval`（記入なし）、観点 `q-no-passthrough`・`q-approval-from-as` | 「act の方針表」「ツールの方針表」が設計のどこにも無い（交換を許すクライアント・割り当てる宛先・範囲の規則）。承認の記録の置き場所（トークンに載せるか、invoices が引く台帳か）を候補から比べた記録も無い（いまは両方を使う） | Minor | 観点 | 候補の漏れ | — | 採用 |
| F20 | `C-iat.enforced_at`（invoice-mcp・invoices：proof の iat が今から ±60 秒）、`C-jti.enforced_at`・`C-jti.assumption`（jti を 90 秒記録すれば足りる）、`DPOP.note`（iat から受け入れる 60 秒）・`DPOP.jti_policy.max_age_seconds`（90） | proof を受け入れる期間の書き方が 2 通り（±60 秒と「iat から 60 秒」）。±60 秒なら同じ proof を受け入れうる期間は 120 秒（＋ずれ）で、90 秒の記録が消えた後に、未来の iat の proof を再送できる余地がある。RFC 9449 §11.1 は、proof を受け入れる期間の間 jti を覚えて再送を拒むよう述べる（と理解している）。期間を 1 つに決め、記録の長さをその期間以上にする | Minor | 観点 | 前提の誤り | — | 採用 |
| F21 | `DPOP.key_rotation`（起動ごとに鍵を作り直す、publish_before_use_seconds 0）・`jwks_cache_ttl`（300）・`unknown_kid`（取り直し 300 秒に 1 回、負のキャッシュ 300 秒、失敗時 reject）、観点 `q-key-rotation` | sts と受け手は登録した jwks_uri の鍵でだけ束縛・照合するので、agent-runtime・invoice-mcp が起動して新しい鍵を作ると、キャッシュと負のキャッシュのために最大 300 秒以上その鍵が使えない。使う前に公開する順序が書かれていない | Minor | 観点 | 候補の漏れ | — | 採用 |
| F22 | hops H15（upstream なし、絞り込みは note だけ）、design.md 4. の `E-token-exchange.2`（満たさない）・1. の L62 warn、12. の「H15 の交換を L16 で確かめていない」、観点 `q-hop-narrowing` | 交換のホップの「下流ほど絞る」が機械でも設定でも確かめられていない。12. に書いてあるのは良いが、sts が積で絞る・sub を差し替えさせない・寿命を縮めることを確かめる試験（拒否のテスト）の計画も無い | Minor | 観点 | 候補の漏れ | — | 採用 |
| F23 | `template:00_core#sequence`（design.md 7.）、catalog_answers の I13（CIBA を受けるのは sts、Keycloak のマッパーは関与しない、portal の CIBA Grant は OFF）、観点 `q-outside-catalog` | 図は「G->>K: CIBA で社員の承認」と Keycloak が CIBA を受けるように描くが、I13 の回答・issuance_profile.grants では sts が受け、社員はポータルで承認する。agent-runtime から sts への CIBA の要求、H5〜H7 の直接の呼び出し、ledger → events → payment-worker の経路も図に無い | Minor | 観点 | 実装とのずれ | — | 採用 |
| F24 | catalog_answers の I12・I25・I26（R3b warn：プロトコルマッパーが呼ばれるかは unknown、hook_checked なし）、design.md 12. の「組織の名前空間を出すマッパー」、`KC_AT.required_claims`、観点 `q-hook-failure` | 追加認証・初回ログイン・資格情報の変更の後の発行で、マッパーが組織の名前空間を出すかを確かめていない。KC_AT は独自クレームを全部必須にしているので、出なければ入口が拒否し（閉じる側）、業務が止まる。確かめの手順（Client Scopes の Evaluate と実発行）を I12・I25・I26 の hook_checked に書く | Minor | 観点 | 候補の漏れ | — | 採用 |
| F25 | hops H5・H6・H7 の note（H4・H8 にある「寿命は残りの寿命以下」が無い）、design.md 9.2 の C-department の行、観点 `q-hop-lifetime` | INT_AT_LEDGER・INT_AT_DOCS・INT_AT_PAYROLL の exp を KC_AT の exp 以下にする規則が書かれていない。無いと、INT_AT_DOCS の部署の古さは 330 秒でなく KC_AT の受け入れ（330）＋INT_AT_DOCS（330）まで延びうる | Minor | 観点 | 候補の漏れ | — | 採用 |
| F26 | `C-email`（revisit_trigger なし）、`C-cognito-custom-role`（revisit_trigger なし）、同じく `C-preferred-username`・`C-upn`（抜き取りの外で目に付いたもの）、rationale_rubric の RR2 | 抜き取りの不合格（RR2）。前提はあるが、崩れたら見直す条件が無い。例：C-cognito-custom-role なら「Cognito の app client で custom: 属性の書き込みを本人に許さない設定を確かめたとき」など | Minor | 観点 | 理由の不備 | — | 採用 |
| F27 | `TASK_AT.required_claims`（scope と authorization_details の両方）、`C-scope.enforced_at`（invoices）・`C-authorization-details.enforced_at`、観点 `q-scope-semantics`、判断の木 `rar-vs-custom` | invoices は同じ API で scope（invoices.pay）と authorization_details（payment）の両方を確かめる。判断の木と観点書は「同じ API では一方」とする。ただし RFC 9396 は scope との併用を想定した記述を持つと理解しており（要確認）、教材の規則の根拠を確かめたうえで、どちらで何を決めるかを台帳に書く | Minor | 観点 | 目的と仕組みの不一致 | `rar-vs-custom`（取引の承認を scope と authorization_details の両方で答えた） | 保留（教材の規則を確かめる。5. に戻す） |
| F28 | `INT_AT_LEDGER.revocation`（db_lookup）、`C-roles.enforced_at`（orders の引き直し）、`C-approval-id.enforced_at`（承認の DB）、`AGENT_AT.revocation`（sts の委任の記録）、hops H13、観点 `q-dependency-outage` | 引き直し先（Keycloak の管理 API・承認の DB・委任の記録）が落ちたとき、受け手が拒否するか続けるかが書かれていない（JWKS だけ use_last_known と書く）。B11・B12・C7 の対策が、障害のときに開く側に倒れないことを書く | Minor | 観点 | 候補の漏れ | — | 採用 |
| F29 | `C-approval-id.absent_semantics`（支払いを拒否。読み取りは許す）・`C-authorization-details.absent_semantics`（読み取りだけ許す）、`TASK_AT.required_claims`（両方を含む）・TASK_AT の scope（invoices.pay だけ） | 「欠けたら読み取りだけ許す」と書くが、TASK_AT は両方を必須にしており、欠けたトークンはそもそも受け入れられない。TASK_AT で読み取りをする経路も無い。どちらかにそろえる | Minor | 観点 | 実装とのずれ | — | 採用 |

重大度の内訳：Blocker 0、Major 12（F02〜F13）、Minor 17（F01・F14〜F29）。

## 3. 対応の一覧

| 指摘 ID | 担当 | 期限 | 状態 | 対応の PR・コミット |
| --- | --- | --- | --- | --- |
| F01 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F02 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F03 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F04 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F05 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F06 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F07 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F08 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F09 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F10 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F11 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F12 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F13 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F14 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F15 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F16 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F17 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F18 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F19 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F20 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F21 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F22 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F23 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F24 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F25 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F26 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F27 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F28 | 未定（作成者） | 未定（作成者） | 未着手 | — |
| F29 | 未定（作成者） | 未定（作成者） | 未着手 | — |

## 4. 専門家に回した項目

| 基準の ID（escalation.md） | 行・欄 | 回した先 | 期限 | 結論 |
| --- | --- | --- | --- | --- |
| `draft-spec` | `C-txn`・`C-req-wl`・`C-tctx`（refs・spec_version は draft-ietf-oauth-transaction-tokens-11、revisit_trigger あり）、目録の `TXN`。回す前の確認：版と見直しの条件は書いてある。F01・F03・F14 の tctx の扱いもあわせて | 組織の認証基盤の担当 | 未定 | 保留 |
| `delegation-depth` | `AGENT_AT`・`TASK_AT` の `max_delegation_depth: 3`、`C-act`（入れ子）。回す前の確認：一括失効（sts が交換のたびに委任の記録を引く）と「認可に使うのは最も外側の act だけ」は書いてある。この設計の経路で要る深さは 2（invoice-mcp ＞ agent:expense）で、3 を許す理由が台帳に無い | 組織の認証基盤の担当 | 未定 | 保留 |
| `baseline-unmet` | design.md 3.2 の「ログに…個人情報を残さない」に対し `C-department` の log_policy 記録する（F10。設計書は「満たす」と書いており、レビュアーが当てはまると判断した） | 組織の共通の基準の持ち主 | 未定 | 保留 |
| `unverified-idp-behavior` | design.md 12. の「組織の名前空間を出すマッパー」（KC_AT が全部を必須にしているので、出なければ全社員の API が止まる。F24）、「CIBA の流れ」（承認を AS が確かめる判断が依存）、「RT の再利用の検知」（F16）。12. に無いが同じ基準に当たると判断したもの：`C-auth-time.assumption`「リフレッシュでは認証の時刻を変えない（Keycloak の挙動）」（ledger の追加認証の判断が依存。要確認） | IdP の運用の担当 | 未定 | 保留 |

当てはまらなかった基準：`custom-crypto`（alg は RS256・ES256 だけで、独自の暗号・形式が無い。corp-internal+jwt は typ の値で暗号ではない）、`cross-tenant-exchange`（テナントは corp だけ。グループ会社の社員は別テナントにせず、アカウントのリンクもしない（I18 対象外）。運用者の横断作業は範囲外）、`jwe-key-management`（JWE を使う種別が無い）、`regulated-data`（pii_category に要配慮個人情報が無く、conformance_profile は none。authorization_details の口座の情報は個人関連情報で、規制の対象ではないと書かれている）、`new-token-type`（目録の種類はすべて token_kinds.yaml の 17 種類の中。ただし F08 の管理 API のトークンは目録に無い）

## 5. カタログ・観点書・対応表に戻す事項

| 戻す先 | 中身 | 指摘 ID | issue・PR |
| --- | --- | --- | --- |
| 観点書 | 見る欄が台帳のスキーマに無い：`pa-19` の `registry:claims#restrictive`（claims.schema.json に無い）。問いを claim_request の問 19 だけで答えるか、列を足す | — | 未定 |
| 観点書 | 見る欄が記入例で 1 行も使われていない（答えは claim_request で取った）：`registry:claims#prior_art_search`（dc-02・pa-03・q-registered-synonym）、`registry:claims#modifiers`（dc-10・pa-11・ap-1-7・q-writer-distinguished）、`registry:claims#integrity_until`・`#trust_boundary`（ap-2-5・q-unwrapped-value-authz。H11 で DB に写しているのに空）、`registry:claims#consumer_access_path`（dc-04・pa-05。C-act だけ）。lint で必須にしないなら、問いの見る欄に「無ければ claim_request の問 n」と書く | F12 | 未定 |
| 観点書 | `registry:token_types#tenant_binding`（ap-1-4・ap-2-9・q-internal-delegation-token）が全行で空。単一テナントの設計で「該当なし」にしてよいか、`C-tenant-id.enforced_at` で答えてよいかの案内が無い | — | 未定 |
| 観点書 | `template:modules/*`・`template:profiles/*` を見る欄にする問いが多い（pa-16・q-shared-validator・q-validate-before-read・q-validity-not-authz・q-object-level-authz・q-approval-from-as・q-no-passthrough・cf-03・cf-09・q-access-context-from-pep・q-idp-diff-absorbed・q-token-not-in-url・q-hook-failure・q-hop-narrowing・q-pairwise-external・q-derived-value・q-confidential-reaches-reader・q-role-explosion・ap-2-1・ap-1-6・ap-2-7・q-identifier-choice・q-cross-tenant-identity・q-tenant-data-match・q-original-principal・q-authorize-service-and-user・q-single-aud-resource・q-agent-own-identity・q-delegation-depth-and-revocation・q-long-running・q-trace-id-trust・q-audit-correlation・q-scope-elevation-logged・q-token-logging・q-audit-log-protected・cd-01〜cd-11・q-db-context-writers・q-db-context-parameterized・q-sql-tenant-predicate・q-ddm-rls-only）。Full の記入例でもその欄が無く、記入したモジュールを設計書のどこ（同じファイルの付録か、別のファイルか）に置くかが教材に無い。置き場所の規則と、欄が無いときに台帳の列で答えてよいか（本レポートでは「代替」と書いて答えた）を書く | F13 | 未定 |
| 観点書 | `q-hop-narrowing` の見る欄 `template:modules/M_idp_keycloak#token-exchange-downscope` は、交換を Keycloak でなく組織の sts が担う設計では当たらない。「交換を担うサービスの設定」と一般に書く | F22 | 未定 |
| 観点書 | `registry:questions#q-auth-strength` など（q-auth-context-semantics・q-step-up-by-rs・q-reuse-standard-structure・ap-2-7・q-operator-act）は、設計書の側では `catalog_answers.yaml` の `questions` に当たるが、q-auth-strength・q-iss・q-typ・q-still-valid は questions.yaml で pending で、設計書も「要る／不要」を書いていない。見る欄として使えない | F02 | 未定 |
| 観点書 | `q-rt-policy-by-client` の見る欄 `registry:token_types#rt_strategy`・`#reuse_detection` は、記入例では `issuance_profile.rt_strategy` と RT の行の `rt_rotation.reuse_detection` にある。列の名前と場所を合わせる | F16 | 未定 |
| 観点書 | `q-dependency-outage` の見る欄が JWKS・イントロスペクション・フックだけで、受け手が鮮度のために引く外部の台帳（IdP の管理 API・承認の DB）の障害を問わない。`introspection_cache_ttl` はイントロスペクションを使わない設計では空になる | F28 | 未定 |
| 観点書 | 問いの一覧に無かった気づき（足す問いの候補）：(1) 台帳の `consumers`・`enforced_at` の受け手が、そのトークンを実際に受けるホップを持つか（F04）、(2) Txn-Token だけを受ける受け手で、追加認証・セッションの確認・scope が元の経路から落ちないか、tctx の操作が元の scope に含まれるか（F02・F03。q-step-up-path-coverage・q-txn-scope-fixed を手でホップを追ってやっと見つけた）、(3) 同じ値を 2 つのクレームに書くとき、照合のキーと正規化が 1 つか（F07）、(4) `volatility`・`propagation_delay` が `assumption` の同期の周期と矛盾しないか（F05）、(5) 外部の IdP の AT から作るクレームの鮮度の上限は外部の AT の受け入れの上限で決まること（F06）、(6) DPoP の proof の受け入れの期間と jti の記録の長さ（F20） | F02〜F07・F20 | 未定 |
| 観点書・判断の木 | `rar-vs-custom` と `q-scope-semantics` の「同じ API で scope と authorization_details を併用しない」の根拠（RFC 9396 §2 を引く）を確かめる。RFC 9396 は scope との併用を想定した記述を持つと理解しており、規則として言い切れるかを一次資料で確かめる | F27 | 未定 |
| 観点書（procedure.md） | 段 0 の「error が 0 でなければ返す」は、設計書の版と lint の版が違うとき（規則が後で厳しくなったとき）にどちらの版で判定するかが書かれていない。記入例を較正に使うときに必ず起きる | F01 | 未定 |
| 観点書（procedure.md） | 1 名・LLM のセッションでは「時間を分ける」を満たせない。LLM のセッションで行うときの代わり（別のセッションで段 3 の No を読み直す など）を書く | — | 未定 |
| カタログ | 利用の場面の候補：受け手が鮮度のために IdP の管理 API・ディレクトリ（Keycloak の管理 API、Entra の Graph）を、サービスアカウントの資格情報で引く。いまは I05（Client Credentials）に当たるが利用の側の行が無く、設計書は I05 を対象外にしていた | F08 | 未定 |
| カタログ | 発行の場面の候補：非同期のワーカーが、キューのメッセージを処理するときに自分のワークロード ID で Txn-Token を取り直す（I22 の「入口以外が求める」変種） | F04 | 未定 |
| カタログ | subject_state_matrix の資格情報の変更の行に、「ほかの端末のセッションを残すかの判断を設計書のどの欄に書くか」を足す（回答が 12. を参照したが行が無かった） | F09 | 未定 |
| lint・実行テスト | L7 の逆向きの検査（on_missing 拒否なのに required_claims に無い）が、aud が信頼ドメインの Txn-Token に当たらない。TXN の受け手（holder・hops の to）で判定する | F14 | 未定 |
| lint・実行テスト | 機械で拾えたもの：`value_vocabulary`（extensible false）とホップの scope の値の差、`max_items`・`max_bytes` とホップの scope の値（F15）。consumers の受け手が carried_in のトークンを受けるホップの `to` に無い（F04）。claim_request の問 25 が挙げるスキーマのトークンが carried_in に無い（F17）。DPoP の jti の記録の長さが受け入れの期間より短い（F20） | F04・F15・F17・F20 | 未定 |
| 対応表 | 指示により `templates/trace/` は読んでいない。F02（Txn-Token の経路で追加認証が落ちる）と F03（tctx が元の scope を超える）が、スライドの規則（slide:p06-step-up-approval・slide:p06-transaction-tokens）の要件として観点・lint のどちらかに当たっているかを、対応表の持ち主が確かめる | F02・F03 | 未定 |

## 6. 理由の採点（抜き取り）

抜き取りの方法：乱数の種 20261123。`claims.yaml` の decision が「採用」の 34 行と「却下」の 8 行から、Python の `random.Random(20261123).sample` でそれぞれ 5 行（採用を先に引いた）。採点したのは各行の `rationale`・`assumption`・`revisit_trigger`・`refs`。

| 行の ID | 列 | RR1 | RR2 | RR3 | RR4 | RR5 | RR6 | 合否 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C-jti（採用） | rationale・assumption・revisit_trigger | 満たす | 満たす | 満たす | 満たさない（RFC 9449 §11.1 は受け入れる期間の間 jti を覚えることを述べるが、assumption の「60 秒＋ずれだけ持てば足りる」は C-iat の ±60 秒の受け入れと合わない。F20） | 満たす | 満たす | 不合格 |
| C-dpop-htm（採用） | 同上 | 満たす | 満たす（DPoP を使う前提と、やめるときの見直し） | 満たす（代償は C-cnf・3.1 の DPoP の費用に寄せている） | 満たす（RFC 9449 §4.3） | 満たす | 満たす | 合格 |
| C-dpop-htu（採用） | 同上 | 満たす | 満たす（入口で URI を書き換えない前提と、書き換える部品を置くときの見直し） | 満たす | 満たす（RFC 9449 §4.3） | 満たす | 満たす | 合格 |
| C-email（採用） | 同上 | 満たす（表示だけ、照合に使わない） | 満たさない（revisit_trigger が無い） | 満たす（照合は C-user-id） | 満たす（slide:p04-immutable-identifiers、B13） | 満たす | 満たす | 不合格 |
| C-v（採用） | 同上 | 満たす | 満たす | 満たす（受け手が先に直す順の制約を assumption に書く） | 満たす | 満たす | 満たす（C-employee-id の廃止で版を上げない理由がこの行に固有） | 合格 |
| C-kc-client-id（却下） | 同上 | 満たす | 満たす（シナリオ A の見本からの推定と明記し、受け手が増えたら見直す。12. にも挙げた） | 満たす（azp で代える） | 満たす（RFC 9068 §2.2 は client_id を REQUIRED とする） | 満たす（同じ製品・版の観測。レルムが違う点は 12. で確かめる計画） | 満たす | 合格 |
| C-realm-access（却下） | 同上 | 満たす | 満たす | 満たす（C-roles で代える） | 満たす | 満たす | 満たす | 合格 |
| C-cognito-custom-role（却下） | 同上 | 満たす | 満たさない（前提「cognito:groups だけを入力にする」はあるが、見直す条件が無い） | 満たす（C-roles・cognito:groups で代える） | 満たす（slide:p03-cognito-pre-token-hook） | 満たす | 満たす | 不合格 |
| C-may-act（却下） | 同上 | 満たす | 満たす | 満たさない（代わりの「ツールの方針表」が設計のどこにも無く、交換の可否に答える手段の一部が欠ける。F19） | 満たす（RFC 8693 §4.4） | 満たす | 満たす | 不合格 |
| C-rctx（却下） | 同上 | 満たす | 満たす | 満たす（接続元で操作を分ける要件が無いので、答える問いが無い） | 満たす | 満たす | 満たす | 合格 |

結果：10 件中 合格 6・不合格 4。不合格は F20（C-jti）・F26（C-email・C-cognito-custom-role）・F19（C-may-act）の指摘にした。

## 7. 点検状況

人による点検は未実施。作成とは別の LLM のセッションで点検した。作成者の 1 日以上空けた見直しは未実施（記録：本レポート。保存先は作成者が決める）。

- このレビューは LLM のセッション（Claude Opus 5.5）が 1 名で役割を切り替えて行った。指摘は、人のレビュアーが 1 件ずつ採否を決めるまで確定しない（procedure.md の「LLM で一次スクリーニングする」の 4.）
- 較正のため、以前のシナリオ B のレビュー（PR・issue のコメント、research/、現行の templates/examples/scenario-b/、perspectives.md の 9.2 の指摘の中身）は見ていない。設計書はコミット a6aad45 の写しだけを読んだ
- 本レポートが書いた外部の事実のうち、一次資料で確かめていないもの：Keycloak のサービスアカウントのトークンが client credentials の grant で出ること（F08。一般に知られた挙動として書いた）、RFC 9396 の scope との併用の記述（F27、要確認）、RFC 9449 §11.1 の jti の保持の記述（F20）、Keycloak がリフレッシュで auth_time を保つこと（4. で要確認として回した）

## 8. 問いごとの回答

記号：Y＝Yes、N＝No、NA＝該当なし。「代替」は、見る欄（主にモジュール・プロファイルの欄）が設計書に無く、台帳・ホップ・25 問の別の欄で答えたもの（F13 と 5. に戻した）。

### 8.1 定義（Y 42／N 15／NA 1）

| 問い ID | 回答 | 理由 |
| --- | --- | --- |
| dc-01 | N | C-department の volatility 330 が同期の周期 3600 秒と合わない（F05）。ほかの認可・識別子の行は寿命の間に変わらないか許容内 |
| dc-02 | Y | 登録名は registered_ref、独自クレームは claim_request の問 3 に探した記録（prior_art_search は全行空。5. に戻した） |
| dc-03 | Y | 独自クレームは https://claims.example.com/ のオブジェクトの下。予約名との照合は問 4（L2 は一覧が無く info） |
| dc-04 | Y | 問 5 で受け手の部品（Node.js・Java）とログの基盤を確かめた（consumer_access_path は C-act だけ） |
| dc-05 | Y | 型は 1 つ。ID は文字列（employee_id も文字列、B22） |
| dc-06 | Y | 複数の値は配列（roles・authorization_details）。scope は標準の空白区切り |
| dc-07 | N | C-idp の欠落の扱いが問 9 と台帳で逆、C-v・C-sid に absent_semantics が無い（F18） |
| dc-08 | Y | 問 10 で完全一致・小文字を決めた（value_normalization は C-roles・C-department・C-idp などで空） |
| dc-09 | Y | 照合は user_id（UUID）・部門コード。名前は IDT の表示だけ |
| dc-10 | Y | authoritative_writer・provenance が管理者・発行者。Cognito の custom:role は却下 |
| dc-11 | N | C-scope の max_items・max_bytes を KC_AT の scope が超える（F15） |
| dc-12 | N | C-tctx は on_missing 拒否なのに TXN.required_claims に無い（F14） |
| dc-gate | N | dc-01・dc-07・dc-11・dc-12 に No がある行（C-department・C-idp・C-scope・C-tctx）が active で載っている |
| pa-01 | Y | 9 件とも受け手の名前と決めることを書き、usage と合う（idp は認可に使わないと明記） |
| pa-02 | N | claim_request_department.md の問 2 の「330 秒」が同期の周期と合わない（F05） |
| pa-03 | Y | 9 件とも既存のクレームで表せない理由がある |
| pa-04 | Y | 名前空間のオブジェクトの中で最上位と重ならないと書く |
| pa-05 | Y | 問 5 で「確かめた」と書く |
| pa-06 | Y | 組織のオブジェクトの下で、namespace・shape と一致 |
| pa-07 | Y | 型は 1 つ、区切り文字列なし |
| pa-08 | Y | ID は文字列 |
| pa-09 | N | claim_request_idp.md の問 9 と C-idp.on_missing が逆（F18） |
| pa-10 | Y | 比較の方法を書いた |
| pa-11 | Y | 書けるのは Keycloak の管理者・STS だけ。本人・呼び出し側の値を使わない |
| pa-12 | Y | ID だけを出す、名前は出さない |
| pa-13 | Y | 上限と、超えたら受け手が拒否することを書いた |
| pa-14 | Y | 宛先ごとに絞って載せる（department は INT_AT_DOCS だけ など） |
| pa-15 | Y | 段階②（Keycloak）と③（STS）に分かれ、外部の利用者は STS が書く |
| pa-16 | Y | 問 16 に共通の検証部品（代替。M_token_validation の記入は無い） |
| pa-17 | Y | ヘッダーに移さない。入口が x-user-* を変種ごと捨てる |
| pa-18 | Y | 未検証の値を流すモードを作らないと書く |
| pa-19 | Y | 制限のクレームは読む受け手を限定（restrictive の列はスキーマに無い） |
| pa-20 | Y | 9 件とも台帳の log_policy・pii_category と一致（department の値のログは q-baseline-kept で指摘） |
| pa-21 | Y | 委任のトークンに載るかと act・承認 ID との関係を書く |
| pa-22 | Y | 9 件とも consumers が設計書の受け手と一致 |
| pa-23 | N | task_id・approval_id の問 23 が発行者に Keycloak のマッパーを挙げる写し（F17） |
| pa-24 | Y | 互換期間・並行発行を書く。department の「C-tenant-id と同じ」は参照先の手順が実在 |
| pa-25 | N | 問 25 のスキーマ・Evaluate が、載るトークンと発行者に合わない（F17） |
| pa-gate | N | 7 問が 9 件で同文の写し（F17） |
| pa-trace | Y | 「対象：」が台帳の ID を指し、rationale と 25 問は食い違わない（欠落の扱いの食い違いは pa-09） |
| q-registered-synonym | N | STS のトークンで sub と user_id が同じ意味・同じ値（F07） |
| q-reuse-standard-structure | Y | cnf・txn・act・authorization_details を使う |
| q-auth-context-semantics | Y | 認証の新しさは auth_time、強さは acr、sid は IdP のセッションの有無だけに使う |
| q-scope-semantics | N | invoices が同じ API で scope と authorization_details を併用（F27）。scope の語彙の外の値（F15） |
| q-value-vocabulary | Y | C-roles に語彙・upstream_issuer・正規化がある |
| q-role-explosion | Y | ロールは 4 つの粗い語彙、上限 4 件（代替） |
| q-identifier-choice | N | 持ち主の照合のキーが sub と user_id の 2 つ（F07）。テナントは corp 固定 |
| ap-1-6 | Y | 利用者のキーは入口の対応表（不変の ID）。email・upn・preferred_username は却下 |
| q-pairwise-external | NA | 組織の外へトークンを出さない（EXT_AT は受けるだけ） |
| ap-2-1 | Y | 粗いロールだけ、max_items 4、Entra の超過はディレクトリで解決し引けなければ拒否 |
| ap-2-2 | N | 部署の反映の遅れの誤り（F05）、外部の利用者のロールの対策が無い（F06） |
| ap-2-3 | Y | 型・形が台帳で固定され、schemas の受け手のスキーマと一致（見た範囲） |
| ap-2-4 | Y | 独自クレームは名前空間の下。草案名（tctx・req_wl）は L1b で別に扱う（F01） |
| q-payload-readable | Y | confidential_from（browser・logs）の相手が visible_to にいない |
| q-confidential-reaches-reader | Y | name・email は BFF のサーバーだけ、employee_id・authorization_details はログに残さない |
| q-no-secret-or-raw-pii | Y | 秘密・生年月日などを載せない |
| q-derived-value | Y | 生の個人情報を判定に使う行が無い（代替） |
| q-baseline-kept | N | 3.2 は「満たす」だが C-department を値のままログに残す（F10） |

### 8.2 発行（Y 8／N 2／NA 0）

| 問い ID | 回答 | 理由 |
| --- | --- | --- |
| q-single-issuer | Y | 段階ごとに 1 つの書き手。各サービスはクレームを足さない |
| q-hook-failure | N | 受け手は欠落を拒否するが、I12・I25・I26 でマッパーが呼ばれるかを確かめていない（F24） |
| q-size-limit | Y | R8 で種別ごとの最悪を計算し上限の 29% 以下（scope の上限の誤りは F15） |
| ap-1-7 | Y | 本人が書ける値（custom:role）を使わない |
| q-hook-adds-raw-pii | Y | マッパーが足すのは ID・部門コード・ロール |
| q-minimal-per-recipient | Y | 宛先ごとに INT_AT を分け、読む受け手だけに載せる |
| q-rar-per-audience | Y | authorization_details は H15（invoices）だけ、type は 1 つ |
| q-agent-own-identity | Y | agent:expense は自分の client_id と DPoP の鍵を持つ（代替：2.1） |
| q-agent-delegation-claims | Y | sub は社員、act・client_id はエージェント |
| q-outside-catalog | N | 管理 API のトークン（F08）、payment-worker の TXN の取り直し（F04）がカタログの回答の外 |

### 8.3 伝搬（Y 19／N 6／NA 1）

| 問い ID | 回答 | 理由 |
| --- | --- | --- |
| cf-01 | Y | 段階ごとに書き手が決まる |
| cf-02 | Y | フックの出す独自クレームは KC_AT の必須で、欠ければ入口が拒否 |
| cf-03 | Y | 外部の AT は入口で終わり、INT_AT に作り直す（代替：hops） |
| cf-04 | Y | INT_AT は宛先ごと。TXN の改変なしの伝搬は Txn-Token の用法 |
| cf-05 | N | INT_AT 系に宣言した scope がトークンに載らない（F11） |
| cf-06 | Y | TXN は Txn-Token のヘッダーで、Authorization では受けない |
| cf-07 | Y | トークンのホップはすべて validates が local |
| cf-08 | Y | H2 で x-user-* を変種ごと捨てる。内側はヘッダーを読まない（H3 の validates には除去の記述が無いが U11 の回答が全体に書く） |
| cf-09 | NA | 接続元の文脈で判断する要件が無い（C-rctx の却下）。M_authz_pdp の記入は無い |
| cf-10 | Y | sub・act・txn・承認 ID を別の項目で記録し、トークンは jti だけ（U14） |
| q-hop-narrowing | N | H15 の絞り込みは note だけで、L62 も満たさない（F22） |
| q-hop-lifetime | N | H5〜H7 に「残りの寿命以下」が無い（F25） |
| q-single-aud-resource | Y | AGENT_AT・TASK_AT の aud は 1 つ（resource indicators） |
| ap-2-6 | Y | invoice-mcp は AGENT_AT を渡さず交換する |
| q-no-passthrough | N | 交換を許す範囲の規則（方針表）が無い（F19） |
| ap-2-5 | Y | クレームをヘッダーに移さない |
| q-unverified-claim-extraction | Y | 検証せずに取り出す設定が無い |
| q-gateway-bypass-path | Y | 内側のサービスはそれぞれトークンを検証し、通信相手を mTLS で確かめる |
| q-step-up-path-coverage | N | H10 の経路で acr・auth_time・sid の確認が落ちる（F02） |
| q-txn-scope-fixed | N | tctx の ledger.post が元の scope を超える（F03） |
| ap-2-9 | Y | INT_AT・TXN は署名・期限・テナント（corp）・ログの扱いがある |
| q-internal-delegation-token | Y | 内部トークンにも目録の行がある（tenant_binding の列は空。5. に戻した） |
| ap-2-7 | Y | エージェントは利用者のトークンを借りず、CIBA と交換で得る |
| q-delegation-depth-and-revocation | Y | 深さ 3 と一括の取り消しを書く（深さ 2 以上なので専門家に回した） |
| q-idp-diff-absorbed | Y | 内側は STS の組織の名前空間だけを読む |
| q-token-not-in-url | Y | URL に載るのは認可コードと request_uri だけ（PAR） |

### 8.4 検証（Y 10／N 3／NA 1）

| 問い ID | 回答 | 理由 |
| --- | --- | --- |
| q-shared-validator | Y | 問 16 の共通の検証部品と目録の列（代替。library-config の記入は無い） |
| ap-1-1 | Y | alg_allowlist が種別ごとに 1 つ |
| ap-1-2 | Y | すべてのホップで署名を先に確かめる |
| q-validate-before-read | N | 検証の順序と「独自クレームは検証の後」を書いた欄が無い（F13） |
| ap-1-3 | Y | aud は必須で、受け手が自分だけかを確かめる |
| ap-1-4 | Y | iss の許可リストと、全受け手の tenant_id＝corp の照合 |
| ap-1-5 | Y | key_source が発行者のメタデータか設定の jwks_uri、ヘッダーの鍵は reject |
| ap-1-8 | Y | exp は必須、ずれは 30 秒 |
| q-typ-distinguishes | Y | typ が種別ごとに違う（at+jwt・corp-internal+jwt・txntoken+jwt・logout+jwt・dpop+jwt）。KC_AT の client_id の欠落は記録済みの逸脱 |
| q-required-rejected | N | TXN で tctx が必須に無い（F14） |
| q-no-unverified-passthrough-mode | Y | 問 18 で作らないと書く |
| q-consumer-expression | Y | 完全一致・語彙の外を無視・欠落で拒否を enforced_at に書く |
| q-nested-jwt-both-layers | NA | JWE を使わない |
| q-unwrapped-value-authz | N | DB のセッション変数に写す値の integrity_until が無く、app.department を誰が書くか不明（F05・F12） |

### 8.5 認可（Y 12／N 9／NA 7）

| 問い ID | 回答 | 理由 |
| --- | --- | --- |
| q-object-level-authz | N | 持ち主の照合のキーが sub と user_id の 2 つで、正規化も違う（F07） |
| q-tenant-data-match | NA | テナントは corp だけ（multitenant false） |
| q-writer-distinguished | Y | 書き手で値を分け、本人が書ける値を使わない |
| q-validity-not-authz | Y | 操作・対象・承認の内容を enforced_at で照合（代替） |
| q-original-principal | Y | 下流でも sub（社員）で判断し、仲介の権限で呼ばない |
| q-authorize-service-and-user | Y | H10・H15 で通信相手（mTLS）と社員をそれぞれ確かめる |
| q-scope-and-role | N | INT_AT 系に scope が無く、orders は role だけ（F11） |
| q-access-context-from-pep | NA | 接続元で判断する要件が無い（C-rctx） |
| q-step-up-by-rs | N | ledger は H5 では insufficient_user_authentication を返すが、H10 の経路で確かめない（F02） |
| q-approval-from-as | N | AS（sts）の承認を invoices が照合するが、承認の記録の置き場所を候補から比べた記録が無い（F19） |
| q-cross-tenant-identity | Y | 暗黙の名寄せをしない（I18 対象外、idp は認可に使わない） |
| q-operator-act | NA | 運用者の操作は範囲外（2.2） |
| q-break-glass | NA | 緊急時の特権は範囲外（2.2） |
| cd-01 | N | user_id は検証済みのトークンを受けた ledger が注入するが、app.department の書き手が不明（F05・F12） |
| cd-02 | Y | 取引ごとに set_config（第 3 引数 true）（代替：H11 の note） |
| cd-03 | NA | SQL Server を使わない（Postgres） |
| cd-04 | Y | 認可に使う値は管理者・発行者が書く |
| cd-05 | NA | DB のロールを選ぶクレームが無い |
| cd-06 | N | RLS をすり抜ける主体が書かれていない（F12） |
| cd-07 | Y | DB の利用者は user_id（UUID）で対応付け（代替：H11） |
| cd-08 | Y | connection_max_lifetime 1800 と取引ごとの注入（9.1） |
| cd-09 | Y | 監査の列に app.user_id を書く |
| cd-10 | Y | 文脈が未設定なら 0 行（H11） |
| cd-11 | N | データ層の設定を試験で確かめる計画が無い（F12） |
| q-db-context-writers | N | 注入者以外が同じ接続で SQL を流せないかが書かれていない（F12） |
| q-sql-tenant-predicate | NA | テナントは 1 つで、テナントでの分離をしない |
| q-db-context-parameterized | Y | set_config を使う（SET LOCAL でない）。バインド変数で渡すことの明記は無い |
| q-ddm-rls-only | N | 最小権限の記述が無い（F12） |

### 8.6 運用（Y 12／N 12／NA 0）

| 問い ID | 回答 | 理由 |
| --- | --- | --- |
| q-four-lifetimes-written | Y | 9.1（トークン）・9.2（鮮度）・RT とセッション・9.3（定義）を分けて書く |
| q-lifetime-rationale | Y | 5.1 の組織の上限と、LOGOUT・KC_AT の理由に剥奪の速さからの説明がある |
| q-session-rt-bounds | Y | idle 1800・最大 36000（24 時間以内） |
| q-rt-policy-by-client | N | 機密クライアントに公開クライアントの根拠を引く（F16） |
| q-freshness-mitigation | N | 部署の遅れの誤り（F05）、外部の利用者のロール（F06） |
| q-refresh-reevaluated | Y | Keycloak のリフレッシュでの再計算はケーススタディの実測、外部の IdP は毎回読むと書く |
| q-revocation-delivery | N | 資格情報の変更でほかのセッションが残る（F09）、H10 でセッションの確認が落ちる（F02） |
| q-external-user-deprovision | N | 外部の利用者の停止は IdP ごとの停止と exp（5430 秒）だけ（F06） |
| q-relies-on-at-expiry | Y | 判断の結果をキャッシュせず、INT_AT のキャッシュは KC_AT の exp を超えない |
| q-long-running | N | payment-worker が TXN を持つのか持たないのかが食い違う（F04） |
| q-system-actor-no-fake-sub | Y | payment-worker は自分の ID で動き、sub を作らない |
| q-agent-short-lived-no-rt | Y | AGENT_AT・TASK_AT は 300 秒で RT を出さない |
| q-copies-outlive | N | ledger-db の社員の表（部署の写し）の鮮度と止め方が無い（F05） |
| q-deprecated-deadline | Y | C-employee-id に sunset_on・alt・consumers_migration |
| q-change-order | Y | 9.3 と C-v に受け手が先の順を書く |
| q-key-rotation | N | DPoP の鍵の公開の順（F21）。ほかの種別は公開の 3900 秒前・廃止の 330 秒後と負のキャッシュがある |
| q-dependency-outage | N | 引き直し先の障害の振る舞いが無い（F28）、マッパーの未確認（F24） |
| ap-2-8 | Y | 目録の log_policy は jti だけ |
| q-token-logging | N | 記録するヘッダーの許可リストと HAR・ログの手順が無い（F13） |
| q-audit-log-protected | N | 監査ログの保護の方針が無い（F13） |
| q-audit-correlation | Y | sub・act・req_wl・承認 ID・txn・task_id を別の項目で残す（U14） |
| q-trace-id-trust | Y | 監査は署名された TXN の txn を使う |
| q-scope-elevation-logged | N | 昇格の記録が書かれていない（F13） |
| q-operational-metrics | N | 共通の検証部品の採用率と版の測定が付録 A に無い（F13） |

## 9. 較正：PR #44 の指摘（B01〜B15）との照合

この節は、上の 1.〜8. を書いたレビュアーではなく、教材の作成者が、レビューが終わった後に書きました。照合の相手は、同じコミット（`a6aad45`）を PR #44 でレビューした別のセッションの指摘 B01〜B15 です（PR #44 のコメント https://github.com/Takenori-Kusaka/jwt-claims-guide/pull/44#issuecomment-7089791933 ）。

### 9.1 条件（読むときの注意）

- 上のレビュー（F01〜F29）は、教材の作成とは別のセッション（同じモデル）が、教材とスナップショットだけを渡されて書いた。PR #44 のコメント・`research/`・現在の記入例（直した後のもの）・`templates/casestudy-deviations.yaml`・`templates/trace/` は読ませていない
- **教材の作成者は、教材を書く前に、`research/template-design/gate2-evidence.md` にある B の指摘の 1 行の要約（経路をまたぐ追加認証の抜け・Txn-Token の scope の欠落・外部の利用者のロールの剥奪の遅れ・承認の置き場所の候補の漏れ・規則の緩め方の悪用・Keycloak の RFC 8707 の前提の誤り・25 問の回答の使い回し）を読んでいた。** `q-step-up-path-coverage`・`q-txn-scope-fixed`・`q-external-user-deprovision`・`q-approval-from-as` の後半・`pa-gate` の後半は、その影響を受けている可能性がある。この 5 問から再発見した B01・B02・B03・B08 は、教材が B を知らずに作られた場合より見つけやすかったとみなす
- 1 回のレビューの数で、正解の母数ではない（gate1.md の 5. と同じ注意）
- B13 は `casestudy-deviations.yaml` の中身についての指摘で、このレビューでは読ませていない（独立を保つため）。見逃しではなく、範囲の外として数える

### 9.2 照合の表

| B | 指摘の要約 | このレビューで | 対応する F | 見つけた・見つけるはずの問い |
| --- | --- | --- | --- | --- |
| B01 | orders → ledger の経路（H10）で追加認証と鮮度の確認が落ちる | **再発見** | F02 | `q-step-up-path-coverage`（9.1 の注意の対象） |
| B02 | Txn-Token の `scope` が REQUIRED なのに無い（a）、ホップの scope が宣言だけ（b）、ledger.post が scope の外（c） | **一部**（b・c を再発見、a を見逃し） | F11（b）、F03（c） | `q-txn-scope-fixed`・`cf-05`。(a) は `q-txn-required-claims`（較正で追加） |
| B03 | 外部の利用者のロールの剥奪の遅れは EXT_AT の 5430 秒で決まる | **再発見** | F06 | `q-freshness-mitigation`・`q-external-user-deprovision`（9.1 の注意の対象） |
| B04 | 承認の ID と内容を、最初に分かる時点（AGENT_AT）でなく交換で初めて足した。比べた跡が無い | **見逃し** | （F19 は方針表の欠落で別の指摘） | `q-approval-from-as` は「置き場所を候補から比べたか」を問うていたが、Yes と答えた（答えを誤った）。`q-claim-earliest-hop`（較正で追加） |
| B05 | 交換のホップの aud の比較で、規則（L16）の側が誤っており、設計は upstream を外して回避した | **一部**（症状を再発見、規則の側の誤りは見逃し） | F22 | `q-hop-narrowing`。規則の側を疑う問いは `q-lint-workaround`（較正で追加） |
| B06 | L1b の緩め方が広く、架空の草案名で抜けられる | **見逃し** | （F01 は同じ規則の別の面） | 教材は lint の規則そのものをレビューの対象にしていなかった。`q-lint-workaround`（較正で追加）は設計書の側からの入口で、規則の実験（一時コピーで規則を試す）は教材の範囲の外（#6 の点検に渡す） |
| B07 | Keycloak は RFC 8707 の resource に対応していない（前提の誤り） | **見逃し** | — | `q-idp-capability-verified`（較正で追加） |
| B08 | 25 問の手書きの回答の使い回しと、写しの誤り | **再発見** | F17 | `pa-gate`（後半は 9.1 の注意の対象）・`pa-25` |
| B09 | シーケンス図の CIBA の矢印が本文と食い違う | **再発見** | F23 | `q-outside-catalog`（図と回答の照合） |
| B10 | 矢印の表の `enforced_at` が別のトークンの文を出す・consumers の受け手が受けないトークン | **一部**（consumers の面を再発見） | F04 | `pa-22`・`q-long-running`。矢印の表の面は `q-limit-consistency`（較正で追加。同じ事実の 2 か所の食い違い） |
| B11 | H11 の `app.department` を誰が設定するかが無い | **再発見** | F05・F12 | `cd-01`・`q-db-context-writers` |
| B12 | DPoP の有無の比較が、サイズの全体と安全性の差を見ていない | **見逃し** | — | `q-variant-comparison`（較正で追加） |
| B13 | ケーススタディからの逸脱の理由が lint を避けるため | **範囲の外**（読ませていない） | — | `q-lint-workaround`（較正で追加） |
| B14 | 根拠の帰属の誤り（RFC 9449 §11.1 の ±60 秒、RFC 7523 の typ、Auth0・Cognito・Okta の値、Keycloak の act） | **一部**（§11.1 の不整合を再発見し、要確認とした） | F20 | 理由の採点の RR4、`q-evidence-attribution`（較正で追加） |
| B15 | EXT_AT の組織の上限が note（3600）と 5.1（300）で違う | **見逃し** | — | `q-limit-consistency`（較正で追加） |

### 9.3 数

| 区分 | 件数 | ID |
| --- | --- | --- |
| 再発見 | 5 | B01・B03・B08・B09・B11 |
| 一部 | 4 | B02・B05・B10・B14 |
| 見逃し | 4 | B04・B07・B12・B15 |
| 教材の範囲の外 | 2 | B06（lint の規則そのものの欠陥）、B13（読ませていないファイル） |

B の 15 件のうち、少なくとも一部を見つけたのは 9 件（60%）、範囲の外の 2 件を除くと 9／13 件（69%）。そのうち 3 件（B01・B03・B08）は、9.1 の注意の対象の問いから見つけました。

このレビューは、B に無い指摘も多く出しました（F01・F04 の一部・F05・F07〜F10・F12〜F16・F18・F21・F24〜F29）。どれが本物の欠陥かは、作成者の対応（3. の対応の一覧）で決まります。現在の記入例（PR #44 の反映の後）に残っているかは、この PR では確かめていません。

### 9.4 見逃しから観点書に足した問い

見逃し・一部の指摘ごとに、観点書（`templates/review/perspectives.md`）に問いを足しました。足した問いには「較正で追加」と書いています。**足した問いは、上のレビューでは使っていません**（足したのはレビューの後）。次の較正（#12 の埋め込んだ誤り、#9 のパイロット）で効くかを測ります。

| 足した問い | 段 | もとの指摘 |
| --- | --- | --- |
| `q-txn-required-claims` | 3. 伝搬 | B02(a) |
| `q-claim-earliest-hop` | 3. 伝搬 | B04 |
| `q-idp-capability-verified` | 2. 発行 | B07 |
| `q-variant-comparison` | 2. 発行 | B12 |
| `q-lint-workaround` | 6. 運用 | B05・B06・B13 |
| `q-evidence-attribution` | 6. 運用 | B14 |
| `q-limit-consistency` | 6. 運用 | B10・B15 |

あわせて、上のレビューの 5.（教材に戻す事項）から、次を直しました：`pa-19` の見る欄（スキーマに無い `restrictive` を外した。レビューの途中で直したため、レビュアーは旧版を見た）、手順の段 0（lint の版の扱い）・段 3（モジュールの欄が無いときの扱い）・1 名で行う場合（LLM のセッションでの「時間を分ける」の代わり）、`q-dependency-outage`（受け手が引く外部の台帳の障害）、`q-hop-narrowing`（交換を担うサービスの設定を一般に）。RFC 9396 の scope との併用（F27）は、根拠をスライド（slide:p02-scope の要件）のまま残し、一次資料での確かめを `research/reviews/review-materials-facts.md` に回しました。
