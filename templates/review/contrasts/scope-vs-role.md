<!-- template_version: 0.4.0 -->
# 対比表：`scope` と `role` と `authorization_details`（RAR）

どれも「何をしてよいか」を表すように見えますが、守る相手が違います。`scope` はクライアントに委ねた範囲、`role` は利用者に許した範囲、`authorization_details` は取引の単位の承認の内容です（slide:p05-scope-vs-role、slide:p02-scope）。

- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施

<a id="question"></a>

## 1. 解く問い

| 仕組み | 解く問い | 解かない問い |
| --- | --- | --- |
| `scope` | 利用者は、このクライアントに何を委ねたか | 利用者に何が許されているか（利用者の全権限ではない） |
| `role`（`roles`・`groups`・`entitlements`） | 利用者（または主体）は、組織の中で何をしてよいか | クライアントに委ねたか、この取引を承認したか |
| `authorization_details`（RFC 9396） | この取引（金額・対象・操作）を、利用者が承認したか | 利用者の一般の権限 |

根拠：slide:p05-scope-vs-role、slide:p02-scope、RFC 9396 §2、RFC 9068 §2.2.3

<a id="unit"></a>

## 2. 仕様上の単位

| 観点 | `scope` | `role` | `authorization_details` |
| --- | --- | --- | --- |
| 値の形 | 空白区切りの文字列 | 文字列の配列（RFC 9068 §2.2.3.1 は SCIM の語彙を使う） | オブジェクトの配列。`type` ごとに項目を組織が決める |
| 誰が決めるか | 利用者の同意と AS の方針 | 組織（IdP・人事の台帳） | 利用者の承認（要求ごと） |
| 意味の単位 | `aud` のリソースにとっての操作 | 組織の役割（IdP ごとに語彙・位置が違う） | 取引（`type` は自分が管理する URI を既定にする） |
| 寿命の目安 | トークンと同じ | 鮮度の対策が要る（変わりやすい） | 取引の間だけ |

根拠：RFC 9068 §2.2.3、RFC 9396 §2、slide:p02-roles-groups-entitlements

<a id="table"></a>

## 3. 対比

| 観点 | `scope` | `role` | `authorization_details` |
| --- | --- | --- | --- |
| 受け手が確かめること | 操作がスコープの中か | 利用者の役割で許されるか | 取引の内容が承認と一致するか（承認 ID の照合） |
| 両方を確かめるか | `role` と両方を確かめる | `scope` と両方を確かめる | 同じ API で `scope` と併用しない |
| 下流のホップ | 宛先ごとに絞る | 下流が読まないなら載せない | 宛先ごとに、その宛先の `type` だけに絞る |
| 爆発の兆し | スコープが API の数だけ増える | ロールにテナント・対象・操作を焼き込む | 独自の権限オブジェクトを作る（まず RAR の `type` で表せるか） |

根拠：slide:p05-scope-vs-role、slide:p05-role-explosion、slide:p06-step-up-approval、RFC 9396 §9.1

<a id="not-covered"></a>

## 4. 扱わないこと

- 細かい権限（オブジェクトごとの許可）は、どれでも表さない。PDP に置く（template:modules/M_authz_pdp#carry-or-query）
- 認証の強さ（`acr`・`amr`）は扱わない。承認の前提になる追加認証は template:00_core#step-up
- 製品ごとの `scope`・`roles` の位置（Entra の `scp`、Keycloak の `realm_access.roles` など）は、入口で組織の形にそろえる（`q-idp-diff-absorbed`）

根拠：slide:p05-coarse-fine-layers、slide:p03-confusing-differences

<a id="misuse"></a>

## 5. 典型的な誤用

| # | 誤用 | 起きること | 見つける問い |
| --- | --- | --- | --- |
| m-1 | `scope` を利用者の全権限と読む | 利用者に許されていない操作を、クライアントの委任で通す | `q-scope-semantics`・`q-scope-and-role` |
| m-2 | `role` だけを見て、`scope` を見ない | クライアントに委ねていない操作をクライアントが行う | `q-scope-and-role` |
| m-3 | 取引の承認を `role` や `scope` で代用する | 金額・対象を変えた取引が、同じ権限で通る | `q-approval-from-as`・`q-rar-per-audience` |
| m-4 | `authorization_details` を全宛先のトークンに載せる | 読まない宛先に取引の内容が漏れる | `q-rar-per-audience` |
| m-5 | ロールの名前に組み合わせを焼き込む・ロールを全部載せる | 件数の上限を超えて欠ける。語彙が管理できない | `q-role-explosion`・`ap-2-1` |
| m-6 | 同じ文字列のロールが IdP をまたいで同じ意味だと仮定する | 別の IdP の `admin` が通る | `q-value-vocabulary` |
| m-7 | 独自の権限オブジェクトを、RAR の `type` を検討せずに作る | 受け手の検証部品が知らない形が増える | `pa-03`・`q-registered-synonym` |

根拠：slide:p05-scope-vs-role、slide:p02-scope、slide:p05-role-explosion、RFC 9396 §2
<!-- req:p05-scope-vs-role.R1 -->

<a id="evidence"></a>

## 6. 根拠

- RFC 9068 §2.2.3（`scope`）・§2.2.3.1（`roles`・`groups`・`entitlements`）、RFC 9396 §2・§9.1
- ガイド：slide:p02-scope、slide:p05-scope-vs-role、slide:p05-role-explosion

根拠：RFC 9068 §2.2.3、RFC 9396 §2、slide:p05-scope-vs-role
