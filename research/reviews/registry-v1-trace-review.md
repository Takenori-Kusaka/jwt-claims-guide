# 台帳 v1（#3）：「実装済み」にした要件の見直し（全 67 件）

PR #37 の独立点検（https://github.com/Takenori-Kusaka/jwt-claims-guide/pull/37#issuecomment-7078821386）は、67 件のうち 15 件を抜き取り、3 件を過大・不一致、2 件を一部とした。指摘を受けて、作成者が **67 件すべて**を同じ基準で見直した記録です。

- 見直した日：2026-11-23。見直した人：作成者（生成AI、Claude）。人による点検は未実施。この見直しそのものは別のセッションで点検していない
- 基準：要件の文が「列・宣言を持つ／決める／書く／宣言する」（**宣言**の要件）なら、その列がスキーマにあり、記入例でその列を書けることを確かめて維持する。要件の文が「〜にする・〜しない・〜だけを読む」（**規定**の要件）なら、スキーマ・R1・R8 のどれかがその規定を機械で強制している場合だけ維持し、列があるだけの場合は未着手に戻す（規定を確かめる lint・観点書・テストの担当に残す）
- 結果：**維持 54 件（core 39・full 15）、未着手に戻した 13 件**。見直しに合わせて、スキーマ・R1 を 4 か所強めた（下の「強めたもの」）。`trace_check.py` は通常と `--tier core` の両方で OK

## 未着手に戻したもの（13 件）

| 要件 | 文（要約） | 戻した理由 |
| --- | --- | --- |
| p02-delegation-client.R6 | AT に client_id を入れ、azp と区別する | 規定。`required_claims` の列があるだけで、記入例（Keycloak）は client_id を却下している（独立点検の指摘） |
| p06-flow-partner-events.R7 | 失効を SSF・CAEP で受け、txn で同じ原因を相関する | 規定。`revocation.method: ssf_caep` は書けるが、txn での相関を表す列がない（独立点検の指摘） |
| p03-entra-scp-roles-groups.R1 | 上限で消えうるクレームが無いことを「所属なし」と読まない | 規定（受け手の読み方）。`absent_semantics` は任意の列で、読み方を確かめる規則（L33 など）がない |
| p03-keycloak-aud-lightweight.R3 | 組織の所属は確かな情報源から付ける（メールのドメインだけで付けない） | 規定。`verification_method` は自由記述で、ドメインで付けていないかを見る検査がない |
| p04-namespace.R4 | ネストを扱えない IdP 向けに、フラットな名前も定義する | 規定（その IdP があるなら必須）。`flat_alias` は任意で、いつ要るかを判定していない |
| p04-namespace-object-example.R2 | 同上 | 同上 |
| p06-grant-types.R1 | 利用者の発行は認可コード、公開クライアントは PKCE | 規定。`issuance_effects.yaml` の E-public-pkce に書いたが、それを読む L62 は #6 で、まだない |
| p06-edge-exchange.R2 | 内部トークンに正規化した主体 ID・認証レベル・内部の aud を入れ、サービスは内部の形だけを読む | 規定（中身）。ホップの `aud`・`custom_claims`・`exchanger` は宣言できるが、中身の規定を確かめない |
| p06-access-context.R2 | アクセス元の値は認証時の値と分かる名前にし、意味しないことを書く | 一部。`not_meaning` は R1 で必須だが、名前の規則を表す列も検査もない（独立点検の「一部」） |
| p06-flow-browser-to-db.R3 | AT の宛先を resource（RFC 8707）で API に限る | 規定。ホップの `aud` は宣言できるが、resource で要求しているか・1 つに限っているかを確かめない |
| p08-rotation.R2 | クライアントの種類を宣言し、FAPI の機密クライアントは送信者制約付きでローテーションしない | 前半は宣言（`client_type`）だが、後半は規定で、E-fapi-no-rotation を読む L15・L62 がない |
| p08-revocation-propagation.R3 | イントロスペクションの応答のキャッシュを、応答の exp を超えて使わない | 規定。`introspection_cache_ttl` の列はあるが、応答の exp との比較はできない（実行時の性質） |
| p11-ownership.R2 | クレームの持ち主は、権威ある情報源の部門とする | 規定（誰を持ち主にするか）。`owner`・`source_system` は R1 で必須だが、両者の関係を確かめない |

## 維持したもの（54 件）

「強制」は、その要件を機械で確かめているもの（スキーマ・R1・R8・REF）。「宣言」は、要件が宣言を求めていて、その列がある（任意の列のものは「任意」と書いた）。

| 要件 | 判定の根拠 |
| --- | --- |
| p00-claims-are-contracts.R3 | 宣言。`type`・`shape`（R1 で必須）、`absent_semantics`（任意） |
| p00-claims-are-contracts.R4 | 強制。`description`・`not_meaning`（R1） |
| p00-claims-are-contracts.R6 | 強制。`owner`・`consumers`（R1）、`change_controller`（任意） |
| p00-why-hard.R1 | 宣言。p00-claims-are-contracts.R3 と同じ |
| p00-why-hard.R3 | 強制。`shape`（R1）。記入例の `C-scope` を `space_delimited` に直した（独立点検の不一致） |
| p00-why-hard.R5 | 宣言。`absent_semantics` の absent と null、`on_missing`（R1） |
| p00-incident-signature-valid.R4 | 宣言（任意）。`paired_id`、`composite_format`（components・separator・escape が必須） |
| p01-jwt-structure.R3 | 強制。JWT の採用の種別に `jwe`（R1）。使うならネストと鍵（スキーマ） |
| p01-client-made-jwts.R2 | 宣言（任意）。`jti_policy.max_age_seconds`・`replay_check`、`sender_constraint` |
| p02-registered-claims.R5 | 宣言（任意）。`jti_policy.unique_scope`・`replay_check` |
| p02-roles-groups-entitlements.R2 | 宣言（任意）。`value_vocabulary`（values・owner が必須、namespace） |
| p02-roles-groups-entitlements.R4 | 強制。配列の `max_items`（スキーマ・R8）と `overflow_strategy`（R1・R8。切り詰めは書けない） |
| p02-scope.R7 | 強制。`shape` に `space_delimited`、`max_items` が必須（スキーマ）。記入例を直した |
| p02-auth-strength-session.R4 | 宣言。`recompute_trigger`（R1） |
| p02-saml-attributes.R1 | 宣言（任意）。`upstream_issuer`（iss・normalization が必須） |
| p02-check-before-creating.R2 | 強制。`description`・`not_meaning`（R1） |
| p02-check-before-creating.R3 | 宣言（任意）。`prior_art_search.nearest`・`not_used_because` |
| p03-absorb-idp-differences.R2 | 宣言（任意）。`upstream_issuer.normalization` |
| p04-carry-or-query.R3 | 強制。R8 が経路の上限を超えた種別を error にし、「載せるか問い合わせるか」へ誘導する。`overflow_strategy` に「問い合わせに切り替える」 |
| p04-namespace.R1 | 宣言。`namespaces[].style`（object・flat_prefix が必須）と `namespace` |
| p04-absent-null-false-empty.R1 | 宣言。`absent_semantics`（任意）と `on_missing`（R1） |
| p04-case-and-characters.R2 | 宣言（任意）。`value_normalization.normalized_by`（必須）と `authoritative_writer`（R1） |
| p04-immutable-identifiers.R2 | 宣言。`paired_id`（任意）、`usage`（R1） |
| p04-immutable-identifiers.R3 | 宣言（任意）。`composite_format` |
| p04-split-by-writer.R1 | 強制に近い。`provenance` は 1 行に 1 つの値しか書けないので、出どころの違う値は別の行（別の名前）になる |
| p04-size-budget.R1 | 強制。`max_bytes`（R1・R8）、`max_items`（スキーマ・R8） |
| p04-size-budget.R2 | 強制。`overflow_strategy` に切り詰めは書けない（スキーマ） |
| p04-namespace-object-example.R1 | 強制。`namespaces[].style: object` なら `namespace_version` を必須にした（見直しで強めた） |
| p05-one-request-carries.R2 | 宣言。問い q-via（「経由を示す別の属性」） |
| p05-confused-deputy.R5 | 宣言。同上 |
| p06-stage-map.R1 | 強制。`authoritative_writer[].stage`（R1・スキーマ） |
| p06-edge-exchange.R3 | 強制。R8（経路の上限）と、切り詰めを書けない `overflow_strategy` |
| p06-narrow-downstream.R2 | 強制。ホップの aud・scope・max_lifetime・custom_claims・exchanger はスキーマで必須 |
| p08-stale-claims.R4 | 宣言。`recompute_trigger`・`propagation_delay`（R1） |
| p08-rotation.R4 | 強制。RT・セッションの採用の行に `idle_timeout` を R1 で必須にした（見直しで強めた） |
| p08-revocation-propagation.R4 | 強制。ホップの `validates.mode`（スキーマで必須） |
| p08-logout.R2 | 宣言。`revocation` の手段（exp_only を含む）と遅れ（R1） |
| p08-copies-outlive-token.R4 | 強制。認可コードと JARM の応答のほかは `redirect_query` を書けない（スキーマ。見直しで AT だけから全種類に広げた） |
| p09-jws-is-readable.R2 | 強制。`pii_category`・`data_category`（R1） |
| p11-registry-fields.R2 | 宣言。`type`・`shape`（R1）、形式と許容値は `allowed_values`（任意） |
| p11-registry-fields.R3 | 強制。`description`・`not_meaning`（R1） |
| p11-registry-fields.R4 | 強制。`issuers`（R1） |
| p11-registry-fields.R5 | 強制。`authoritative_writer`（R1）、`provenance`（任意） |
| p11-registry-fields.R6 | 強制。`consumers`（R1。キーを書くこと） |
| p11-registry-fields.R7 | 強制。`max_bytes`・`max_items`・`overflow_strategy`（R1・R8・スキーマ） |
| p11-registry-fields.R8 | 強制。`pii_category`・`log_policy`（R1） |
| p11-registry-fields.R9 | 強制。`owner`（R1） |
| p11-registry-fields.R10 | 強制。`source_system`・`volatility`・`propagation_delay`（R1） |
| p11-registry-fields.R11 | 強制。`status`（R1） |
| p11-registry-fields.R12 | 宣言。README 4.（変更履歴は Git で持つ） |
| p11-change-procedure.R6 | 宣言（任意）。`consumers_migration` |
| p11-reserved-names.R2 | 強制。`namespaces[].owner`（スキーマで必須）、README 11. |
| p11-translation-layer.R4 | 宣言（任意）。`upstream_issuer` |
| p11-ownership.R1 | 宣言。`namespaces[].owner`・`change_controller`、README 11. |

## 強めたもの（見直しに合わせて）

- `namespaces[].style: object` なら `namespace_version` を必須（p04-namespace-object-example.R1）
- RT・セッションの採用の行に `idle_timeout` を R1 で必須（p08-rotation.R4）
- 認可コードと JARM の応答のほかのトークンは `redirect_query` で運べない（p08-copies-outlive-token.R4。前は AT だけ）
- `shape: space_delimited` にも `max_items` を必須（p02-scope.R7）

## 残る弱さ

「宣言（任意）」の 11 件は、列が任意なので、書かなくても検査は通る。要件の文が宣言を求めているので実装済みにしたが、書いたかどうかを確かめるのは #4（テンプレートの欄）と #5（観点書）になる。この判断が甘いと見るなら、任意の列の要件をまとめて未着手に戻すのが次の手になる。
