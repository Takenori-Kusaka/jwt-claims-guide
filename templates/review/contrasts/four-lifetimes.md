<!-- template_version: 0.4.0 -->
# 対比表：トークンの寿命・クレームの値の鮮度・セッションの寿命・クレームの定義の寿命

「いつまで正しいか」は、4 つの層で別々に決まります。どの層の寿命の話かを決めてから議論します（slide:p08-four-lifetimes。層の分け方は筆者の提案、各層の仕組みは仕様と指針にある）。4 つは独立に動きます。AT が 5 分でも、セッションが 10 時間なら、利用者は 10 時間、新しいトークンを得られます。

- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施

<a id="question"></a>

## 1. 解く問い

| 層 | 解く問い |
| --- | --- |
| トークンの寿命 | 1 枚のトークンを、いつまで受け入れるか |
| クレームの値の鮮度 | 載せた値は、いつまで現実と合っているか。変わってから反映されるまで何秒を許すか |
| セッションと RT の寿命 | 再認証なしに、いつまで新しいトークンを得られるか |
| クレームの定義の寿命 | 名前・型・意味の約束は、いつまで有効か |

根拠：slide:p08-four-lifetimes

<a id="unit"></a>

## 2. 仕様上の単位

| 層 | 何が決めるか | 終わらせ方 | 設計書の欄 |
| --- | --- | --- | --- |
| トークン | `exp`（RFC 7519 §4.1.4）と受け手の時刻のずれの許容 | 期限切れ。すぐ止めるなら問い合わせ | `registry:token_types#max_lifetime`・`registry:token_types#max_clock_skew`・`registry:hops#max_lifetime` |
| 値の鮮度 | 発行の時点。再計算はリフレッシュ・再発行のとき（IdP 次第） | 短命化・都度判定・イベント（CAEP の token-claims-change） | `registry:claims#volatility`・`registry:claims#on_revoke`・`registry:claims#recompute_trigger`・`template:00_core#freshness` |
| セッションと RT | IdP のセッション、RT の期限とローテーション | ログアウト・失効（RFC 7009）・Back-Channel Logout | `registry:token_types#idle_timeout`・`registry:token_types#rt_rotation`・`registry:token_types#revocation`・`template:00_core#lifecycle` |
| 定義 | 台帳の版と廃止の予定 | 受け手が先、発行者が後の手順で廃止 | `registry:claims#status`・`registry:claims#sunset_on`・`template:00_core#definition-lifecycle` |

DB・ブローカーの接続と、判断のキャッシュ・複製は、トークンから作った写しで、トークンの寿命に足されます（template:00_core#lifecycle-db-connection、slide:p08-copies-outlive-token）。

根拠：RFC 7519 §4.1.4、RFC 7009 §2.1、Shared Signals Framework・CAEP 1.0（2025-09 Final）、slide:p08-four-lifetimes、slide:p08-copies-outlive-token

<a id="table"></a>

## 3. 対比

| 観点 | トークン | 値の鮮度 | セッションと RT | 定義 |
| --- | --- | --- | --- | --- |
| 指針の数値の例 | AT・ID トークンは 1 時間以内とすべき（NIST IR 8587） | なし（クレームごとに組織が決める） | 再認証の上限：AAL2 は 24 時間・無操作 1 時間（SP 800-63B-4） | なし（互換期間を短く見積もらない） |
| 下流のホップ | 上流以下（組織の規則。Txn-Token は仕様上は長くてよい） | 上流の値の写し。下流で新しくならない | 内部のホップは RT を持たないか短く | 受け手ごとの移行の状況で決まる |
| 剥奪 | 自己完結の AT は exp まで残る | 寿命が許容を超えるなら対策が要る | ログアウトが止めるのはセッションと RT | 廃止の期日の後に読む受け手が残る |
| よくある前提の誤り | 「AT を短くすれば剥奪が効く」 | 「リフレッシュで必ず再計算される」 | 「ID トークンの期限がセッションの長さ」 | 「名前を変えても受け手は追従する」 |

根拠：slide:p08-token-types-lifetimes、slide:p08-choosing-lifetime、slide:p08-stale-claims、slide:p08-refresh-reevaluation、slide:p08-logout、slide:p11-change-procedure、NIST IR 8587 §5.3.1.1、NIST SP 800-63B-4 §2.2.3

<a id="not-covered"></a>

## 4. 扱わないこと

- 寿命の具体的な数字は決めない（RFC に数値はない）。組織の上限は template:00_core#lifetime-policy に書く。判断の木は `review:decision_tree#lifetime-by-situation`
- 鍵の寿命（ローテーションの周期）は、この 4 つの層に入れない。鍵の公開と廃止の順序は template:modules/M_token_validation#key-rotation
- 認可コードなどのアサーションの参照の寿命（5 分以内、FAPI 2.0 は 60 秒）は、目録の行として書く

根拠：slide:p08-choosing-lifetime、NIST SP 800-63C-4 §4.11.1、slide:p01-key-rotation-jwks

<a id="misuse"></a>

## 5. 典型的な誤用

| # | 誤用 | 起きること | 見つける問い |
| --- | --- | --- | --- |
| m-1 | 寿命を 1 つの数字で語る（「トークンは 1 時間」） | どの層の話かが分からず、セッション・RT・鮮度の上限が抜ける | `q-four-lifetimes-written` |
| m-2 | ID トークンの `exp` をログインのセッションの長さにする、`sid` をアプリのセッション ID にする | セッションとアサーションの寿命が混ざる | `q-auth-context-semantics`・`q-session-rt-bounds` |
| m-3 | AT を短くしたので剥奪は早く効くと考える | セッションと RT が長ければ、新しい AT が出続ける。鮮度は再計算の有無で決まる | `q-revocation-delivery`・`q-relies-on-at-expiry` |
| m-4 | 変わりやすい権限を、寿命の長いトークンに対策なしで載せる | 剥奪が期限まで届かない | `q-freshness-mitigation`・`ap-2-2` |
| m-5 | 「リフレッシュで再計算される」を確かめずに前提にする | 古さの上限が RT の寿命になる | `q-refresh-reevaluated` |
| m-6 | 下流のトークン・Txn-Token の寿命を上流より長くして、理由を書かない | 上流を止めても下流が動き続ける | `q-hop-lifetime` |
| m-7 | ジョブ・エージェントが利用者の RT を持って延命する | 剥奪がジョブに届かない | `q-long-running`・`q-agent-short-lived-no-rt` |
| m-8 | DB の接続・判断のキャッシュ・分析基盤の複製の寿命を決めない | トークンを止めても写しが生き続ける | `cd-08`・`q-copies-outlive` |
| m-9 | 廃止予定のクレームに期日がない・受け手の移行を把握しない | 古い形式を読む受け手が残り、廃止できない | `q-deprecated-deadline`・`q-change-order` |
| m-10 | 外部の IdP で止めた利用者が、組織のトークン・セッションでは生き続ける | 上流の剥奪が届かない | `q-external-user-deprovision` |
| m-11 | 時刻のずれを大きく許す・`exp` を必須にしない | 期限のないトークン | `ap-1-8` |

根拠：slide:p08-four-lifetimes、slide:p08-token-types-lifetimes、slide:p02-auth-strength-session、slide:p06-narrow-downstream、NIST SP 800-63C-4 §4.7
<!-- req:p02-auth-strength-session.R5 req:p06-narrow-downstream.R6 req:p08-four-lifetimes.R1 req:p08-token-types-lifetimes.R2 -->

<a id="evidence"></a>

## 6. 根拠

- RFC 7519 §4.1.4（`exp`）、RFC 7009 §2.1（失効の要求）、RFC 7662 §4（イントロスペクションの応答のキャッシュ）
- NIST IR 8587 §4.1.4・§5.3.1.1、NIST SP 800-63B-4 §2.2.3、NIST SP 800-63C-4 §4.7・§4.11.1
- ガイド：slide:p08-four-lifetimes から slide:p08-decision-table までの Part 8 の 14 枚、slide:p11-change-procedure

根拠：RFC 7519 §4.1.4、NIST IR 8587 §5.3.1.1、slide:p08-four-lifetimes
