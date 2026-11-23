<!-- template_version: 0.4.0 -->
# 対比表：クレームに載せることと、問い合わせること

トークンに載せた値は発行時点の写しで、期限まで使われます。問い合わせ（イントロスペクション・PDP・DB）は、判断のたびに今の値を見ます（slide:p04-token-is-snapshot、slide:p01-self-contained-vs-reference）。どちらにするかは、4 つの問い（認可に使うか・変わらないか・小さいか・全受け手が要るか）で決めます（slide:p04-carry-or-query）。

- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施

<a id="question"></a>

## 1. 解く問い

| 仕組み | 解く問い | 解かない問い |
| --- | --- | --- |
| クレームに載せる（自己完結） | 発行の時点で、この値だったか | 今もこの値か |
| 問い合わせる（参照型・PDP・DB） | 今、この操作を許してよいか | 発行の時点で何だったか（監査は別に残す） |

根拠：slide:p01-self-contained-vs-reference、slide:p04-token-is-snapshot

<a id="unit"></a>

## 2. 仕様上の単位

| 観点 | 載せる | 問い合わせる |
| --- | --- | --- |
| 仕組み | JWT のクレーム | RFC 7662 のイントロスペクション、PDP の判断、データ層の照合 |
| 古さの上限 | トークンの受け入れの上限（`max_lifetime`＋`max_clock_skew`）。リフレッシュで再計算されるかは IdP 次第 | 問い合わせの応答・判断のキャッシュの寿命（イントロスペクションの応答のキャッシュは応答の `exp` を超えない） |
| 依存 | 受け手は手元で判断できる | 問い合わせ先の可用性と遅延 |
| 設計書の欄 | `registry:claims#carried_in`・`registry:claims#volatility` | `registry:claims#on_revoke`・`registry:claims#enforced_at`・`template:modules/M_authz_pdp#carry-or-query` |

根拠：RFC 7662 §4、slide:p04-carry-or-query、slide:p08-copies-outlive-token

<a id="table"></a>

## 3. 対比（4 つの問い）

| 問い | すべて「はい」なら載せる | 1 つでも「いいえ」なら |
| --- | --- | --- |
| 認可に使うか | 使う | 使わない値は載せない（表示用は ID トークン・API で） |
| 寿命の間に変わらないか | 変わらない（または変わっても許せる） | 問い合わせるか、短命化・イベントで対策する |
| 小さいか | 上限の中 | 載せずに問い合わせる（件数の多いグループなど） |
| 全受け手が要るか | 要る | 宛先ごとに絞るか、要る受け手だけが問い合わせる |

根拠：slide:p04-carry-or-query、template:modules/M_authz_pdp#carry-or-query

<a id="not-covered"></a>

## 4. 扱わないこと

- 問い合わせ先（PDP・AS）の可用性の設計は扱わない。障害時の振る舞いは観点書の `q-dependency-outage`
- アクセス元の文脈（IP・端末）は、載せるか問い合わせるかではなく、PEP が要求ごとに接続から得る（slide:p06-access-context）
- 監査のための記録（発行の時点の値）は、判断とは別に残す

根拠：slide:p06-access-context、slide:p06-audit-trail

<a id="misuse"></a>

## 5. 典型的な誤用

| # | 誤用 | 起きること | 見つける問い |
| --- | --- | --- | --- |
| m-1 | 変わりやすい権限を載せ、対策を書かない | 剥奪が期限まで届かない | `q-freshness-mitigation`・`ap-2-2`・`dc-01` |
| m-2 | グループ・ロールを全部載せる | 上限を超えて黙って欠ける | `ap-2-1`・`dc-11`・`pa-13` |
| m-3 | 全リクエスト・全宛先に載せる | 読まない受け手に個人情報が届く・サイズが増える | `q-minimal-per-recipient`・`pa-14` |
| m-4 | クレームでオブジェクトの持ち主の確認を代用する | BOLA | `q-object-level-authz` |
| m-5 | アクセス元の文脈をトークンに載せる | 古い場所・端末の値で判断する | `q-access-context-from-pep`・`cf-09` |
| m-6 | 答えられない問いが残るクレームを共有クレームにする | 意味の決まらない値が組織の契約になる | `pa-gate`・`dc-gate` |
| m-7 | 「問い合わせる」と書いたが、どの受け手が問い合わせるかを書かない | 誰も問い合わせない | `q-freshness-mitigation` |
| m-8 | 値で足りるか判定で足りるかを問わずに、元の値を載せる | 生年月日などの不要な開示 | `q-derived-value` |

根拠：slide:p04-carry-or-query、slide:p04-token-is-snapshot、slide:p05-bola、slide:p09-minimize-derived

<a id="evidence"></a>

## 6. 根拠

- RFC 7662 §4（イントロスペクションの応答のキャッシュ）
- ガイド：slide:p01-self-contained-vs-reference、slide:p04-token-is-snapshot、slide:p04-carry-or-query、slide:p08-stale-claims

根拠：RFC 7662 §4、slide:p04-carry-or-query、slide:p04-token-is-snapshot
