<!-- template_version: 0.2.0 -->
# クレームの台帳（v1）

クレームの台帳を、人が読めて機械で検査できる形にしたものです（#3）。v0（#16 の縦の一本）で分かった過不足（[`research/template-design/v0-columns.md`](../../research/template-design/v0-columns.md)）と、#11 のレビュー記録の指摘を反映しました。スキーマの版は `template_version` 0.2.0 です（`$id` の末尾 `/v0.2.0`）。テンプレート一式の最初の公開版（`templates-v1.0.0`）までは 0.y.z で数えるので、「台帳 v1」は 0.2.0 のスキーマを指します。

- 1. ファイル
- 2. 縮小 Lite の印
- 3. 列の一覧（台帳・トークン目録・発行方式の選択・ホップ）
- 4. スライド 134 の 12 項目と台帳の列
- 5. 設計のチェックリスト（スライド 61）と台帳の列
- 6. 寿命の 4 つの層
- 7. 発行方式の選択と、台帳で必要になるもの
- 8. 改ざん防止と流出防止（JWS と JWE）
- 9. 「何のデータか」の語彙（data_category）
- 10. SD-JWT VC のクレームのメタデータとの対応
- 11. 組織の名前空間の持ち主
- 12. ケーススタディとの照合
- 13. 作成方法と点検状況

## 1. ファイル

| ファイル | 中身 | 検査 |
| --- | --- | --- |
| `claims.schema.json` | 台帳（`claims.yaml`）の行の形 | JSON Schema 2020-12。どの判断の行でどの列を埋めるかの大部分は claim_lint の R1（規則の ID つきで出すため）。スキーマでも、採用・却下の理由の 2 つ以上、配列の `max_items`、却下の `rejection_kind`、識別子の `identifier_properties`、`confidential_from` に対する `confidentiality_measure` を強制する |
| `token_types.schema.json` | トークン目録（`token_types`）と発行方式の選択（`issuance_profile`）、R8 の入力（`size`） | 同上。`kind` は `templates/catalog/token_kinds.yaml` の 17 種類（`tools/catalog_check.py`） |
| `hops.schema.json` | 経路のホップごとの宣言（`hops.yaml`）。slide:p06-narrow-downstream の「下流ほど絞る」 | 同上。参照の実在は claim_lint の REF |
| `questions.yaml` | 問いの一覧。台帳の `answers`・`does_not_answer` と、設計書の「問い × 仕組み」（#4）の行 | 文言がスライドの本文と一致することを `tools/tests/test_registry_v1.py` で確かめる |
| `issuance_effects.yaml`・`issuance_effects.schema.json` | 発行方式の選択ごとに、台帳で必要になるもの（#6 の L62〜L64 の入力） | 条件の値がスキーマの列挙にあることをテストで確かめる |

記入例は [`templates/examples/scenario-a/`](../examples/scenario-a/)（`claims.yaml`・`token_types.yaml`・`hops.yaml`・`catalog_answers.yaml`）です。検査は次のとおりです。

```
python tools/claim_lint templates/examples/scenario-a          # スキーマ・R1〜R10・REF・スライドの参照
python tools/casestudy_check.py                                # ORG 行の名前と型、採否とケーススタディの判定の照合
```

YAML の 1 行目は `# template_version: 0.2.0`、2 行目が yaml-language-server の modeline です（`templates/CONTRIBUTING.md` の 4.）。

## 2. 縮小 Lite の印

関門 1 の判定「絞る」（`research/template-design/gate1.md` の 10.）で、Lite で手で書く欄を減らしました。列の一覧の右端の列は、その列の扱いです。

| 印 | 意味 |
| --- | --- |
| 手で書く | Lite でも書き手が書く。トークンに載せて受け手が読む行（`採用`・`既定どおり` で `consumers` が空でない行）の欄。R1 が必須にする列を含む |
| 手で書く（却下の行も） | 却下の行でも書く（却下の行は gate1.md の 10. で「今と同じ」） |
| 生成 | 手で書かない。IdP モジュール（#4 の `M_idp_keycloak`）・カタログ・`token_types`・既定の組み合わせから生成する（#19）。既定から外れたときだけ手で書く |
| Full のみ | Lite では書かない（任意の列）。Full の設計書と、その列を入力にする lint を使うときに書く |

ほかに、行の種類で減らす規則があります（gate1.md の 10.）。

- **既定どおりで `consumers: []` の行**（IdP が出すが誰も読まない行）：`name`・`namespace`・`type`・`shape`・`decision`・`rationale`・`refs`・`max_bytes`・`pii_category`・`carried_in` だけを書く（R8 の計算に要るもの）。v1 では、これに `data_category`・`confidential_from` を足す（R1 の必須。どちらも値が決まりやすい）
- **トークン目録の却下の行**：`kind`・`decision`・`rationale` だけ（スキーマも理由は `rationale` だけを求める）
- **単一値の `overflow_strategy`**：既定（`上限で固定（超えない値域）`）

`claim_lint --profile lite` の R1 の必須の列を、この印に合わせる作業は #4 の担当です（#4 の改訂の項目）。v1 の時点の R1 は、Lite と Full で同じ列を必須にしています。

## 3. 列の一覧

根拠の列の書き方は `templates/CONTRIBUTING.md` の 1. によります。`author-proposal（#3）` は筆者の提案で、裏付けを探す追跡 issue が #3 です。ケーススタディの列は `templates/casestudy-mapping.md` の 3. の対応（同じ／一部／意味が違う／列なし）で、台帳の側から引けるように写しました。

### 3.1 台帳（`claims.yaml` の `claims[]`）

#### 定義

| 列 | 見出し | 意味 | ケーススタディの列（区分） | 根拠 | 縮小 Lite |
| --- | --- | --- | --- | --- | --- |
| `id` | 行の ID | `C-` で始まる台帳の行の ID。ほかのファイル（ホップ・トークン目録）から参照する | `id`（列なし。`catalog_refs` で参照） | author-proposal（#3） | 手で書く（却下の行も） |
| `name` | 名前 | JSON に現れる名前（名前空間を除く）。接続元の値は、認証時の値と分かる名前にする | `name`（一部） | slide:p11-registry-fields、slide:p06-access-context | 手で書く（却下の行も） |
| `namespace` | 名前空間 | 名前空間のオブジェクトの名前。最上位は `null`。運び方は最上位の `namespaces[].style` | `name`（一部。`.` で分ける） | slide:p04-namespace、slide:p04-namespace-object-example | 手で書く（却下の行も） |
| `catalog_refs` | ケーススタディの行 | ケーススタディの一覧表の行（コミットつき）。名前と型の正はそちら。記入例ではすべての行に書く（`tools/casestudy_check.py`）。同じ ID を 2 つの行から参照しない。組織の名前空間の行は ORG の行を参照する | `id`（列なし） | `templates/casestudy-mapping.md` の 1.、v0-columns.md の 1. #1、PR #37 の独立点検 | 手で書く（却下の行も） |
| `catalog_refs_reason` | 一覧表に行が無い理由 | `catalog_refs: []` のときの理由（スキーマで必須） | なし | PR #37 の独立点検、author-proposal（#3） | 手で書く（却下の行も） |
| `registered_ref` | 登録の参照 | IANA に登録された名前を使うときの登録の参照 | `source_kind`・`source`・`url`・`is_custom`（一部） | slide:p02-name-categories、IANA JWT Claims registry | 手で書く |
| `type` | 型 | 1 つの値（配列なら要素）の JSON の型。1 つに固定する | `value_type`（同じ） | slide:p04-type、slide:p11-registry-fields | 手で書く（却下の行も） |
| `shape` | 形 | 単一・配列・空白区切りの文字列（scope）。受け手が読み方をずらさない。配列と空白区切りは `max_items` が必須（スキーマ）。空白区切りの `max_bytes` は文字列全体の上限 | `multiplicity`（一部） | slide:p04-shape、slide:p02-scope、RFC 9068 §2.2.3（scope の形は RFC 8693 §4.2 に委ねている）、RFC 8693 §4.2 | 手で書く |
| `allowed_values` | 形式と許容値 | 正規表現・列挙・最小・最大・形式 | `comparison`・`vocabulary`（列なし） | slide:p11-registry-fields（「形式・許容値」）、NIST SP 800-162 §2.4.2（スライドの引用） | Full のみ |
| `value_vocabulary` | 値の語彙 | 組織が持つ値の語彙（roles・groups・acr の値・authorization_details の type）と持ち主 | `vocabulary`（列なし） | slide:p02-roles-groups-entitlements、slide:p02-auth-strength-session、RFC 9396 §2 | Full のみ |
| `description` | 意味 | 何を表すか | `purpose`（一部） | slide:p11-registry-fields、slide:p02-check-before-creating | 手で書く |
| `not_meaning` | 意味しないこと | 何を意味しないか（azp は client_id ではない、email_verified は本人確認ではない など） | `purpose`（一部） | slide:p11-registry-fields、slide:p02-registered-claims | 手で書く |
| `absent_semantics` | 無いときの意味 | 無い・null・false・空配列・空文字の意味。上限で消えうるクレームを「所属なし」と読まない | なし | slide:p04-absent-null-false-empty、slide:p03-entra-scp-roles-groups、v0-columns.md の 1. #3 | Full のみ |
| `flat_alias` | フラットな別名 | ネストを扱えない IdP 向けの、同じ内容のフラットな名前 | なし | slide:p04-namespace、slide:p04-namespace-object-example | Full のみ |
| `paired_id` | 対になる ID | 名前のクレームと対で出す、変わらない ID のクレームの行 | なし | slide:p04-immutable-identifiers、slide:p00-incident-signature-valid | Full のみ |
| `composite_format` | 合成の識別子の書式 | 部分・区切り文字・区切り文字の退避。発行者が決めて公開する | なし | slide:p04-immutable-identifiers | Full のみ |
| `value_normalization` | 値の正規化 | 大小・Unicode の正規化・前後の空白。書き手が一度だけ行い、受け手の比べ方を決める | `comparison`（列なし） | slide:p04-case-and-characters | Full のみ |
| `prior_art_search` | 作る前に探した記録 | 探した場所と、近い既存のクレームを使わない理由 | `synonym_group`（列なし。照合の入力になりうる） | slide:p02-check-before-creating | Full のみ（共有クレームは追加前の 25 問で書く） |
| `path` | パス（SD-JWT VC） | SD-JWT VC のクレームのメタデータの `path`。同じ名前・同じ意味 | なし | draft-ietf-oauth-sd-jwt-vc-27 §5.6 | Full のみ |
| `mandatory` | 必須（SD-JWT VC） | 同 `mandatory`（既定 false） | なし | draft-ietf-oauth-sd-jwt-vc-27 §5.6 | Full のみ |
| `sd` | 選択的開示（SD-JWT VC） | 同 `sd`（always・allowed・never。既定 allowed） | なし | draft-ietf-oauth-sd-jwt-vc-27 §5.6 | Full のみ |
| `display` | 表示ラベル（SD-JWT VC） | 同 `display`（locale・label・description・dir。dir は ltr・rtl・auto で、省略時は auto） | なし | draft-ietf-oauth-sd-jwt-vc-27 §5.6.2・§5.5 | Full のみ |

#### 判断

| 列 | 見出し | 意味 | ケーススタディの列（区分） | 根拠 | 縮小 Lite |
| --- | --- | --- | --- | --- | --- |
| `decision` | 採否 | 採用・却下・既定どおり（IdP が既定で出すものをそのまま受ける） | `judgement`（一部。`casestudy-mapping.md` の 4.） | #3 の本文、slide:p11-registry-fields | 手で書く（却下の行も） |
| `rejection_kind` | 却下の種類 | 代替あり・不要・禁止・IdP が出さない。却下の行だけ（スキーマで必須） | `judgement` の不採用の 3 つ（一部） | `casestudy-mapping.md` の 4.、v0-columns.md の 1. #14 | 手で書く（却下の行も） |
| `alt` | 代わりのクレーム | 却下・代替ありで代わりに使う行 | `alt`（同じ） | `casestudy-mapping.md` の 4. | Full のみ |
| `rationale` | 理由 | 採用は「どう使うか」、却下は「何ができなくなるか」 | `use_or_loss`（一部） | #3 の本文、#11 の目的（「検討したか」で残す） | 手で書く（却下の行も） |
| `assumption` | 前提 | その判断が成り立つ前提 | `condition`（一部） | #3 の本文、`templates/CONTRIBUTING.md` の 2.「対象外の書き方」 | 手で書く（却下の行も） |
| `revisit_trigger` | 見直しの条件 | 前提が崩れる条件 | `revisit`（同じ） | #3 の本文 | 手で書く（却下の行も） |
| `refs` | 根拠 | 根拠（版付き。ASVS は書かない） | `source`・`url`・`guide_part`（一部） | `templates/CONTRIBUTING.md` の 1. | 手で書く（却下の行も） |

採用（既定からの逸脱）と却下の行は、`refs`・`assumption`・`revisit_trigger` のうち 2 つ以上を書きます（スキーマと R1 の両方で検査する）。

#### 目的

| 列 | 見出し | 意味 | ケーススタディの列（区分） | 根拠 | 縮小 Lite |
| --- | --- | --- | --- | --- | --- |
| `answers` | 答える問い | `questions.yaml` の問いの ID | なし | slide:p05-one-request-carries、slide:p10-four-questions、#18 | Full のみ（Lite は設計書の「問い × 仕組み」で書く） |
| `does_not_answer` | 答えない問い | 答えに使ってはいけない問い（入れ子の act を今の代理者に使わない など） | なし | RFC 8693 §4.1、#18 の L12 | Full のみ |
| `usage` | 用途 | identifier・authz・display・protocol。名前は表示だけに使い、照合は対の ID で行う | `authz_use`（一部） | slide:p02-claims-by-purpose、slide:p04-immutable-identifiers、v0-columns.md の 1. #2 | 手で書く |

#### 発行

| 列 | 見出し | 意味 | ケーススタディの列（区分） | 根拠 | 縮小 Lite |
| --- | --- | --- | --- | --- | --- |
| `issuers` | 付与してよい発行者 | このクレームを付けてよい `iss`。受け手はこれ以外からの値を信じない | なし | slide:p11-registry-fields、slide:p04-single-issuer | 生成 |
| `upstream_issuer` | 上流の発行者 | 中継・ブローカー・宣言的な写像で上流の値を写すときの、上流の `iss` と正規化の規則 | なし | slide:p02-saml-attributes、slide:p03-absorb-idp-differences、slide:p11-translation-layer | Full のみ |
| `authoritative_writer` | 段階ごとの書き手 | 段階ごとに 1 つの書き手と、その設定を変えられる者（`configurable_by`） | `writer`（一部） | slide:p00-claims-are-contracts、slide:p06-stage-map、gate1.md の 5.（A01） | 手で書く |
| `stage` | 段階 | ① 認証時〜⑥ 承認・同意（`authoritative_writer`・`modifiers` の中） | なし | slide:p06-stage-map | 手で書く |
| `configurable_by` | 設定を変えられる者 | platform・tenant_admin・end_user・client・caller（`authoritative_writer`・`modifiers` の中。トークン目録の `lifetime_set_by` も同じ値） | `writer`（一部） | gate1.md の 5.（A01、L31 の拡張） | 手で書く |
| `modifiers` | 追加・抑止・上書きをする者 | 書き手の後に値を足す・消す・上書きする者（フック・入口） | `writer`（一部） | #3 の本文、v0-columns.md の 2. | Full のみ |
| `provenance` | 値の出どころ | 発行者が確かめた値・管理者が設定した値・本人が編集できる値・呼び出し側の申告 | `writer`（一部） | slide:p04-split-by-writer、slide:p11-registry-fields（「書ける者」） | Full のみ |
| `issue_events` | 発行イベント | カタログ（`templates/catalog/issue_events.yaml`）のイベントの ID | なし | #2、slide:p06-stage-map | 生成 |

#### データ源

| 列 | 見出し | 意味 | ケーススタディの列（区分） | 根拠 | 縮小 Lite |
| --- | --- | --- | --- | --- | --- |
| `source_system` | データ源 | 値の権威ある情報源 | なし | slide:p11-registry-fields（「鮮度」）、slide:p11-ownership | 手で書く |
| `verification_method` | 値の確かめ方 | データ源の値をどう確かめるか（所属はメールのドメインだけで付けない など） | なし | slide:p03-keycloak-aud-lightweight、NIST IR 8112 §3.1（スライドの引用） | Full のみ |
| `last_verified` | 最後に確かめた日 | データ源の値を確かめた日 | `checked_on`（意味が違う：出典を開いた日） | NIST IR 8112 §3.2.1（スライドの引用）、`casestudy-mapping.md` の 3. | Full のみ |
| `source_max_length` | データ源の長さの上限 | データ源の欄の上限と単位（バイト・UTF-16 の単位・符号位置）。`max_bytes` の根拠 | `limit`（一部） | gate1.md の 5.（A11） | Full のみ |

#### 寿命と鮮度

| 列 | 見出し | 意味 | ケーススタディの列（区分） | 根拠 | 縮小 Lite |
| --- | --- | --- | --- | --- | --- |
| `volatility` | 反映までに許す秒数 | 値が変わってから反映されるまでに許す秒数。載るトークンの `max_lifetime` と比べる（L5） | `mutability`（一部） | slide:p04-token-is-snapshot、slide:p08-four-lifetimes | 手で書く |
| `recompute_trigger` | 再計算の契機 | login・refresh・exchange・reissue・never | `freshness`（一部） | slide:p08-stale-claims、slide:p08-reissue-triggers、slide:p02-auth-strength-session | 生成 |
| `propagation_delay` | 伝搬の遅れ | 変化が受け手に届くまでの最悪の秒数 | なし | slide:p08-stale-claims、slide:p11-registry-fields（「反映までの遅れ」） | 生成 |
| `on_revoke` | 剥奪の反映手段 | 剥奪したときにどの手段で反映するか | なし | slide:p01-self-contained-vs-reference、slide:p08-revocation-propagation | 手で書く |

#### 伝搬と照合

| 列 | 見出し | 意味 | ケーススタディの列（区分） | 根拠 | 縮小 Lite |
| --- | --- | --- | --- | --- | --- |
| `carried_in` | 載るトークン種別 | トークン目録の ID。ホップは `hops.yaml` | `token`（一部） | #3 の本文、v0-columns.md の 1. #1 | 手で書く（却下の行は書かない） |
| `consumers` | 許可された受け手 | 読んでよいサービス（契約。誰も読まないなら `[]`） | なし | slide:p11-registry-fields、slide:p11-why-govern | 手で書く |
| `consumer_access_path` | 受け手の読み方 | 受け手がどの部品で読むか（ライブラリ・入口のヘッダー・メッシュ・CEL など） | なし | slide:p04-design-checklist（「ツール」） | Full のみ |
| `consumers_migration` | 受け手の移行状況 | 新しい形への移行の、受け手ごとの状態 | なし | slide:p11-change-procedure | Full のみ |
| `on_missing` | 欠落時の挙動 | 拒否・既定値・無視（意味は `absent_semantics`） | なし | slide:p04-reject-missing-required、slide:p04-absent-null-false-empty | 手で書く |
| `enforced_at` | 照合する場所 | どのサービスが何と何を照合するか | `checks`（一部。ケースの ID は `evidence`） | #3 の本文、#18 の L11 | 手で書く |

#### サイズ

| 列 | 見出し | 意味 | ケーススタディの列（区分） | 根拠 | 縮小 Lite |
| --- | --- | --- | --- | --- | --- |
| `max_bytes` | 最大バイト数 | 1 つの値の最悪の UTF-8 のバイト数（JSON の退避の後、文字列の引用符を除く） | `limit`（一部） | slide:p04-size-budget、RFC 7515 §2（R8） | 手で書く |
| `max_items` | 最大要素数 | 配列の最悪の要素数（配列ならスキーマで必須） | `limit`（一部） | slide:p04-size-budget、slide:p02-roles-groups-entitlements | 手で書く |
| `typical_items` | 典型の要素数 | 典型の件数。上限に近ければ集約の兆候 | なし | slide:p05-role-explosion | Full のみ |
| `overflow_strategy` | あふれたときの方針 | 発行を失敗させる・問い合わせに切り替える・上限で固定。**切り詰め（truncate）は書けない** | `limit`（一部） | slide:p04-size-budget、slide:p04-carry-or-query、slide:p06-edge-exchange | 手で書く |

#### 保護（JWS と JWE）

| 列 | 見出し | 意味 | ケーススタディの列（区分） | 根拠 | 縮小 Lite |
| --- | --- | --- | --- | --- | --- |
| `confidential_from` | 読まれてはいけない相手 | browser・client・gateway・`hop:<サービス>`・logs・analytics・external_rp など。`[]` なら改ざん防止だけで足りる | なし | slide:p09-jws-is-readable、RFC 7519 §11.2 | 手で書く |
| `confidentiality_measure` | 落ち着いた手段 | 載せない・派生値・参照・JWE のどれかと理由（`confidential_from` が空でなければスキーマで必須、空なら書けない） | なし | slide:p09-jwe-sd-jwt、slide:p09-minimize-derived | 手で書く |
| `integrity_until` | 署名の保護が外れる場所 | ヘッダー・DB のセッションの文脈・キュー・ログ・キャッシュに写した場所と、写した先の信頼境界 | なし | slide:p07-trust-boundary、slide:p06-header-forwarding、v0-columns.md の 1. #4 | 手で書く |

#### 個人情報と「何のデータか」

| 列 | 見出し | 意味 | ケーススタディの列（区分） | 根拠 | 縮小 Lite |
| --- | --- | --- | --- | --- | --- |
| `pii_category` | 個人情報の区分 | 個人情報保護法の区分（個人情報・要配慮個人情報・個人関連情報・仮名加工情報・該当なし） | `pii`（一部。語彙が違う） | slide:p09-jws-is-readable、slide:p11-registry-fields | 手で書く |
| `data_category` | 何のデータか | 固定した版の fideslang の data category のキー（または組織の子カテゴリ）。`pii_category` とは別の軸 | なし | `research/claims-as-code/report.md`、fideslang 3.1.4（9.） | 手で書く |
| `identifier_properties` | 識別子の性質 | stable・reassignable・pairwise・id_scheme。`volatility` とは別の性質（`usage: identifier` ならスキーマで必須） | なし | `research/claims-as-code/report.md`、slide:p04-immutable-identifiers、slide:p09-pairwise-identifiers | 手で書く |
| `recipients_external` | 外部の受け手 | 社外の受け手と目的 | なし | #3 の本文、slide:p09-checklist | Full のみ |
| `cross_border` | 越境移転 | 国外に移すか、移す国と根拠 | なし | #3 の本文 | Full のみ |
| `log_policy` | ログの方針 | 記録する・ハッシュ化して記録・記録しない | `log_policy`（一部。向きが違う） | slide:p09-logs-traces、slide:p11-registry-fields | 手で書く |

#### 定義の寿命と根拠

| 列 | 見出し | 意味 | ケーススタディの列（区分） | 根拠 | 縮小 Lite |
| --- | --- | --- | --- | --- | --- |
| `status` | 状態 | proposed・active・deprecated・sunset（定義の寿命） | `status`（意味が違う：標準の状態） | slide:p11-registry-fields、slide:p11-change-procedure | 生成 |
| `sunset_on` | 廃止日 | deprecated の行の期限（L18） | なし | slide:p11-change-procedure | Full のみ |
| `owner` | 持ち主 | 意味・値・鮮度に責任を持つ部門 | なし | slide:p11-ownership、slide:p11-registry-fields | 手で書く |
| `change_controller` | 変更の管理者 | 登録名は仕様の発行元、組織のクレームは台帳の持ち主（11.） | `change_controller`（同じ：標準の行） | slide:p11-ownership、IANA JWT Claims registry（Change Controller の欄） | 生成 |
| `evidence` | 検証の記録 | `jwt-claims-casestudy@<コミット>:<ケース>`、テスト、設定へのリンク | `checks`（同じ） | `templates/CONTRIBUTING.md` の 1.（実測は根拠の種類に入れない） | Full のみ |
| `asvs_ids` | ASVS の項目 | 版付きの ASVS の ID（`v5.0.0-8.3.2`）。ASVS はここだけに書き、`refs` に書くとスキーマが拒む | なし | `templates/CONTRIBUTING.md` の 1. | Full のみ |
| `spec_version` | 依存する仕様の版 | 草案に依存する行の版（L14） | `status`（一部：草案の版） | #18 の L14 | Full のみ |
| `note` | 注記 | 機械が読まない補足 | `notes`（列なし） | author-proposal（#3） | Full のみ |

#### 最上位の項目（行ではないもの）

| 項目 | 意味 | 根拠 |
| --- | --- | --- |
| `scenario`・`casestudy_commit` | 記入例のシナリオと、参照するケーススタディのコミット | `casestudy-mapping.md` の 1. |
| `namespaces` | 名前空間ごとの運び方（object・flat_prefix）、持ち主、構造の版のクレーム（`namespace_version`。object ならスキーマで必須）、名前の割り当て方 | slide:p04-namespace、slide:p04-namespace-object-example、slide:p11-reserved-names |
| `data_category_vocabulary` | `data_category` の語彙の固定（fideslang、版・URL・CC BY 4.0・確かめた日） | 9. |
| `data_category_extensions` | 組織の子カテゴリ（`key` は `parent` の子。claim_lint の REF が確かめる） | 9. |

### 3.2 トークン目録（`token_types.yaml` の `token_types[]`）

`templates/catalog/token_kinds.yaml` の全種類に、採用・既定どおり・却下＋理由のどれかを付けます（JWT でないセッション・認可コード・不透明な RT も同じ目録に載せる）。

| 列 | 見出し | 意味 | 根拠 | 縮小 Lite |
| --- | --- | --- | --- | --- |
| `id` | 種別の ID | 台帳の `carried_in`・ホップ・カタログへの回答から参照する ID | author-proposal（#3） | 手で書く（却下の行も） |
| `kind` | 種類 | カタログの種類の ID（17 種類） | #2 の `token_kinds.yaml` | 手で書く（却下の行も） |
| `decision` | 採否 | 採用・却下・既定どおり | #3 の本文（トークン目録） | 手で書く（却下の行も） |
| `rationale` | 理由 | 却下と逸脱は必須 | #3 の本文 | 手で書く（却下の行も） |
| `assumption` | 前提 | 却下の前提（カタログへの回答と同じ前提を書く） | `templates/CONTRIBUTING.md` の 2. | Full のみ |
| `revisit_trigger` | 見直しの条件 | 前提が崩れる条件 | #3 の本文 | Full のみ |
| `refs` | 根拠 | 根拠（版付き） | `templates/CONTRIBUTING.md` の 1. | 手で書く |
| `purpose` | 役割 | 何のためのトークンか | #3 の本文（トークン目録） | 手で書く |
| `issuer` | 発行者 | 誰が発行するか | #3 の本文 | 手で書く |
| `aud` | 宛先 | 誰に向けたものか | #3 の本文、RFC 7519 §4.1.3 | 手で書く |
| `holder` | 持つ者 | 誰が持つか | #3 の本文 | 手で書く |
| `format` | 形式 | jwt・opaque | #3 の本文、slide:p01-self-contained-vs-reference | 手で書く（却下の行も） |
| `subject_type` | sub の種類 | public・pairwise | slide:p09-pairwise-identifiers、OpenID Connect Core 1.0 §8 | Full のみ |
| `typ` | typ | ヘッダーの typ（at+jwt・txntoken+jwt・logout+jwt など） | slide:p01-validation-order、RFC 9068 §2.1 | 手で書く |
| `alg_allowlist` | 許可する alg | 許可リスト。鍵ごとに 1 つ | slide:p01-dangerous-header-params、RFC 8725 §3.1 | 手で書く |
| `issuers` | 許可する発行者 | 許可する `iss` と、そのメタデータの `jwks_uri` | slide:p00-incident-signature-valid、slide:p01-key-rotation-jwks | 手で書く |
| `key_source` | 鍵の取得元 | 鍵はどこから取るか。ヘッダーの jku・x5u・jwk・x5c はたどらず信頼しない | slide:p01-key-rotation-jwks、slide:p01-dangerous-header-params | 手で書く |
| `required_claims` | 必須クレーム | 無ければ拒否するクレーム（at+jwt は RFC 9068 §2.2 の 7 つ） | RFC 9068 §2.2、slide:p02-registered-claims | 手で書く |
| `max_clock_skew` | 許す時刻のずれ | 秒 | slide:p01-validation-order、RFC 7519 §4.1.4 | 手で書く |
| `max_lifetime` | 寿命の上限 | 秒。セッション・RT では絶対的な上限 | slide:p08-token-types-lifetimes、slide:p08-choosing-lifetime | 手で書く |
| `idle_timeout` | 無操作の期限 | 使われないまま切れるまでの秒数（RT・セッション。絶対的な上限と別の列） | slide:p08-rotation、gate1.md の 5.（A14） | 手で書く |
| `lifetime_refs` | 寿命の根拠 | 寿命の値の根拠 | slide:p08-choosing-lifetime | 手で書く |
| `lifetime_set_by` | 寿命を設定できる者 | platform・tenant_admin など（L23 の拡張） | gate1.md の 5.（A01） | 手で書く |
| `lifetime_exception` | 寿命の例外の承認 | 組織の上限を超えるときの承認 | slide:p08-choosing-lifetime（「例外を認める手順を決める」）、#6 の L23 | Full のみ |
| `refresh` | リフレッシュ | リフレッシュの有無と方法 | #3 の本文 | 手で書く |
| `rt_rotation` | RT のローテーション | ローテーションと、再利用の検知（yes・no・unverified） | slide:p08-rotation、RFC 9700 §4.14.2 | 手で書く |
| `sender_constraint` | 送信者制約 | none・dpop・mtls | slide:p08-rotation、RFC 9449、RFC 8705 | 手で書く |
| `jti_policy` | jti の扱い | 一意の範囲・再送の拒否・受け入れる期間（DPoP proof） | slide:p02-registered-claims、slide:p01-client-made-jwts、RFC 9449 §11.1 | Full のみ |
| `revocation` | 失効の手段 | 手段（exp まで・イントロスペクション・状態リスト・SSF/CAEP・Back-Channel Logout など）と、受け手が止めるまでの最悪の秒数 | slide:p08-revocation-propagation、slide:p08-logout | 手で書く |
| `introspection_cache_ttl` | イントロスペクションのキャッシュ | 応答のキャッシュの秒数（応答の exp を超えない） | RFC 7662 §4、slide:p08-revocation-propagation | Full のみ |
| `long_running` | 長時間の処理での扱い | 非同期・期限の後の下流の呼び出し | slide:p08-async-processing、slide:p08-downstream-after-expiry | Full のみ |
| `max_delegation_depth` | 委任の連鎖の深さ | act の入れ子の上限（組織の規則） | slide:p10-delegation-chain-depth | Full のみ |
| `tenant_binding` | テナントの束縛 | iss・aud・tid・org_id・クレームのどれでテナントを決めるか（L9） | slide:p05-multitenancy、v0-columns.md の 1. #9 | 手で書く |
| `key_rotation` | 鍵のローテーション | 周期、署名に使う前に公開する時間、古い鍵を外すまでの時間 | slide:p01-key-rotation-jwks | 手で書く |
| `unknown_kid` | 未知の kid | 取り直しの最短間隔・負のキャッシュ・取り直しに失敗したとき | slide:p01-key-rotation-jwks、gate1.md の 5.（A09） | 手で書く |
| `jwks_cache_ttl` | JWKS のキャッシュ TTL | 秒 | slide:p01-key-rotation-jwks | 手で書く |
| `signing_key_scope` | 署名鍵のスコープ | テナントごと・共有・クライアントごと | slide:p05-multitenancy | 手で書く |
| `stored_at` | 保存場所 | browser・bff_server・idp・rp_server・service_memory・none | #3 の本文、slide:p06-flow-browser-to-db | 手で書く |
| `transport` | 運搬経路 | Authorization（Bearer・DPoP）・Cookie・応答の本文など。認可コードと JARM の応答のほかは URL（`redirect_query`）で運べない（スキーマで拒む） | slide:p09-url-browser、slide:p08-copies-outlive-token | 手で書く |
| `visible_to` | 読める相手 | そのトークンを手にする・読める相手。`confidential_from` と突き合わせる（L65） | slide:p09-jws-is-readable、v0-columns.md の 1. #6 | 手で書く |
| `jwe` | JWE | 使うか。使うなら署名してから暗号化、宛先ごとの鍵、復号できる相手（スキーマで必須） | slide:p09-jwe-sd-jwt、RFC 7519 §11.2 | 手で書く |
| `log_policy` | トークンのログの方針 | 記録しない・jti だけ・ハッシュ・記録する | slide:p09-logs-traces | Full のみ |
| `size` | サイズの入力 | 署名のアルゴリズムと鍵長、ヘッダーの全パラメータ、発行者の書き出しの空白、経路の上限（R8） | report Q9（`research/template-design/report.md`）、gate1.md の 1. | 手で書く |
| `asvs_ids` | ASVS の項目 | 台帳と同じ | `templates/CONTRIBUTING.md` の 1. | Full のみ |
| `note` | 注記 | 機械が読まない補足 | author-proposal（#3） | Full のみ |

### 3.3 発行方式の選択（`token_types.yaml` の `issuance_profile`）

どれも `{value, rationale, refs}` の形です（`forwarded_cert_header` を除く）。値ごとに台帳で必要になるものは 7. です。

| 列 | 見出し | 意味 | 根拠 | 縮小 Lite |
| --- | --- | --- | --- | --- |
| `client_type` | クライアントの種類 | public・confidential・fapi | slide:p08-rotation、slide:p06-grant-types | 生成 |
| `client_auth` | クライアント認証 | private_key_jwt・tls_client_auth・client_secret_* など | slide:p01-client-made-jwts、OpenID Connect Core 1.0 §9（client_secret_basic・client_secret_post・client_secret_jwt・private_key_jwt・none）、RFC 8705 §2.1・§2.2（tls_client_auth・self_signed_tls_client_auth） | 生成 |
| `grants` | grant | 認可コード＋PKCE・client credentials・token exchange・CIBA・device・refresh・JWT bearer | slide:p06-grant-types | 生成 |
| `sender_constraint` | 送信者制約 | none・dpop・mtls | RFC 9449、RFC 8705、slide:p08-rotation | 生成 |
| `tls_termination` | TLS の終端 | mTLS のとき、入口で終端するか端から端までか（mTLS ならスキーマで必須） | RFC 8705 §6.5（終端してよいことを述べる） | 生成 |
| `forwarded_cert_header` | 証明書を渡すヘッダー | 入口で終端するとき、同名のヘッダーを捨て、入口だけが書く（スキーマで必須）。組織の規則 | slide:p06-header-forwarding、author-proposal（#3）。RFC 8705 §6.5 は、証明書の情報を下流へ安全に渡す方法を範囲外としている | 生成 |
| `at_format` | AT の形式 | JWT・不透明＋イントロスペクション・入口で作り直す phantom token | slide:p01-self-contained-vs-reference、slide:p06-edge-exchange | 生成 |
| `rt_strategy` | RT の方式 | ローテーション＋再利用の検知・ローテーション・送信者制約・なし | RFC 9700 §4.14.2、slide:p08-rotation | 生成 |
| `request_protection` | 要求の保護 | PAR・JAR・RAR・resource indicators | RFC 9396 §2、RFC 8707 §2、FAPI 2.0 Security Profile（Final）§5.3.2.2 | 生成 |
| `conformance_profile` | 準拠するプロファイル | none・fapi2_security・oauth2_1 | FAPI 2.0 Security Profile（Final）§5.3.2.1 | 生成 |

「生成」は、既定の組み合わせ（BFF＋認可コード＋PKCE）から生成し、外れた点だけ手で書く、の意味です（gate1.md の 10.）。

### 3.4 ホップ（`hops.yaml` の `hops[]`）

| 列 | 見出し | 意味 | 根拠 | 縮小 Lite |
| --- | --- | --- | --- | --- |
| `id` | ホップの ID | `H1` など | author-proposal（#3） | 生成 |
| `from` | 送り手 | | slide:p06-narrow-downstream | 生成 |
| `to` | 受け手 | | slide:p06-narrow-downstream | 生成 |
| `kind` | ホップの種類 | entry・service・exchange・reissue・db_connection・broker_connection・browser | slide:p06-edge-exchange、slide:p07-lifetime-mismatch | 生成 |
| `upstream` | 上流のホップ | 絞り込みを比べる相手 | slide:p06-narrow-downstream | 生成 |
| `token_type` | 運ぶトークン | トークン目録の ID（トークンを渡さないホップは null） | #3 の本文（ホップ） | 生成 |
| `aud` | aud | そのホップのトークンの宛先（resource indicator で絞る） | slide:p06-narrow-downstream、RFC 8707 §2 | 生成（交換・作り直しのホップは手で書く） |
| `scope` | scope | そのホップの scope | slide:p06-narrow-downstream | 生成（交換・作り直しのホップは手で書く） |
| `max_lifetime` | 寿命 | そのホップのトークンの寿命。Txn-Token は元より長くてよい（仕様）ので、その場合は `narrowing_exception` に書く | slide:p06-narrow-downstream、draft-ietf-oauth-transaction-tokens-11 §6 | 生成（交換・作り直しのホップは手で書く） |
| `custom_claims` | 運ぶ独自クレーム | 台帳の行の ID | slide:p06-narrow-downstream | 生成（交換・作り直しのホップは手で書く） |
| `authorization_details` | 運ぶ authorization_details | 宛先に合わせて絞った type | RFC 9396 §9.1、slide:p05-coarse-fine-layers | 生成（交換・作り直しのホップは手で書く） |
| `exchanger` | 交換を担うサービス | 交換・作り直しを担うサービス（そのまま渡すなら null） | slide:p06-narrow-downstream、slide:p06-edge-exchange | 生成（交換・作り直しのホップは手で書く） |
| `validates` | 受け手の検証 | 手元で検証するか問い合わせるかと、確かめること | slide:p08-revocation-propagation、slide:p06-validation-split | 生成 |
| `connection_max_lifetime` | 接続の寿命 | DB・ブローカーの接続の寿命（トークンより長く生きる） | slide:p07-lifetime-mismatch、v0-columns.md の 1. #13 | 手で書く |
| `forwarded_headers` | 転記するヘッダー | ヘッダーに写すクレームと、入口で同名を捨てるか、書ける者、符号化（L8） | slide:p06-header-forwarding | 手で書く |
| `narrowing_exception` | 絞り込みの例外 | 上流より広げる・長くする理由 | draft-ietf-oauth-transaction-tokens-11 §6、slide:p06-narrow-downstream | 手で書く |
| `note` | 注記 | | author-proposal（#3） | Full のみ |

<a id="slide-134-map"></a>
## 4. スライド 134 の 12 項目と台帳の列

<!-- req:p11-registry-fields.R13 req:p11-registry-fields.R12 -->
slide:p11-registry-fields（#3 の本文でいう「スライド 134」。#10 でスライドを足したので、いまの番号は 141）の「クレームごとに決める 12 の項目」と、台帳 v1 の列の対応です。各項目の「決めること」を、列の値で表せます。1〜11 はトークンに載せる行（`採用`・`既定どおり`）の必須の列に入っていて、欠けると claim_lint の R1 が error にします。

| # | 項目 | 決めること（スライド） | 列 | R1 で必須 |
| --- | --- | --- | --- | --- |
| 1 | 名前 | 名前空間つきの完全な名前 | `name`・`namespace`（最上位は `null`）。運び方は `namespaces[].style` | はい |
| 2 | 型 | JSON の型を 1 つ。形式・許容値 | `type`・`shape`。形式と許容値は `allowed_values`・`value_vocabulary`（任意） | はい（`type`・`shape`） |
| 3 | 意味 | 何を表すか。何を意味しないか | `description`・`not_meaning` | はい |
| 4 | 発行者 | どの発行者だけが付与するか | `issuers` | はい |
| 5 | 書ける者 | 管理者か、本人か、呼び出し側か | `authoritative_writer`（段階と書き手と `configurable_by`）・`provenance`（任意） | はい（`authoritative_writer`） |
| 6 | 許可された受け手 | どのサービスが読んでよいか | `consumers`（読む受け手がいなければ `[]`） | はい（キーを書くこと） |
| 7 | 上限 | 最大の長さ・件数。超えたときの挙動 | `max_bytes`・`max_items`（配列）・`overflow_strategy`（切り詰めは書けない） | はい |
| 8 | 個人情報の区分 | ログ・転送してよいか | `pii_category`・`log_policy`。「何のデータか」は `data_category`、転送は `recipients_external`・`cross_border` | はい（`pii_category`・`log_policy`・`data_category`） |
| 9 | 持ち主 | 意味と値に責任を持つ部門 | `owner` | はい |
| 10 | 鮮度 | 値の出どころと、反映までの遅れ | `source_system`・`volatility`・`propagation_delay` | はい |
| 11 | 状態 | 提案・有効・廃止予定・廃止 | `status`（proposed・active・deprecated・sunset）・`sunset_on` | はい（`status`） |
| 12 | 変更履歴 | いつ、誰が、何を変えたか（来歴） | **列にしない。台帳のファイルの Git の履歴で持つ**（コミットの日時・作者・差分）。変更の承認は PR で行う | — |

却下の行（トークンに載せない行）では、1〜11 を必須にしていません。載せない行に上限や受け手を書かせても、答えようがないためです。

<a id="slide-61-map"></a>
## 5. 設計のチェックリスト（スライド 61）と台帳の列

slide:p04-design-checklist（#3 の対応表でいう「スライド 61」。いまの番号は 63）の 12 の観点と、答えを残す列です。観点書（#5）で問うので、対応表の要件はまだ未着手です（`review:perspectives#design-checklist` が要る）。

| 観点 | 確認すること（スライド） | 列 |
| --- | --- | --- |
| 載せるか | 認可に使い、寿命の間に変わらないか | `usage`・`volatility` |
| 既存 | 登録名・IdP の既存クレームで足りないか | `registered_ref`・`prior_art_search` |
| 名前 | 自社の名前空間か。予約名と照合したか | `namespace`（予約名の照合は #6 の L34） |
| ツール | 受け手の全ツールで参照できるか | `consumer_access_path` |
| 型 | 型は 1 つか。ID は文字列か | `type` |
| 形 | 複数値は配列か。連結・文字列化していないか | `shape` |
| 欠落 | 無い・null・false・空配列の意味を決めたか | `absent_semantics`・`on_missing` |
| 比較 | 大小の扱いを決め、完全一致で比べるか | `value_normalization` |
| 識別子 | 名前ではなく、変わらない ID か | `paired_id`・`identifier_properties` |
| 書き手 | 誰が書けるか。申告の値と分けたか | `authoritative_writer`・`provenance` |
| サイズ | 上限と、超えたときの挙動を決めたか | `max_bytes`・`max_items`・`overflow_strategy` |
| 必須 | 欠けたら拒否するか。発行者は 1 つか | `on_missing`・`issuers`（トークン目録の `required_claims`） |

<a id="lifetime-layers"></a>
## 6. 寿命の 4 つの層

slide:p08-four-lifetimes の 4 つの層を、どの列・宣言で表すかと、記入例（シナリオ A）での値です。

| 層 | 列・宣言 | 記入例での値 |
| --- | --- | --- |
| トークンの寿命（種類ごと・ホップごと） | トークン目録の `max_lifetime`・`max_clock_skew`・`lifetime_set_by`・`lifetime_exception`、ホップの `max_lifetime` | `token_types.yaml`：AT 300 秒（ずれ 30 秒、寿命はテナントの管理者も変えられる）、IDT 300 秒、CODE 60 秒。`hops.yaml`：H2 は 300 秒、H3 はトークンなし（null） |
| クレームの値の鮮度（`volatility` と `max_lifetime` の関係、剥奪の反映） | 台帳の `volatility`・`recompute_trigger`・`propagation_delay`・`on_revoke`、トークン目録の `revocation`（手段と遅れ） | `claims.yaml`：`roles` は volatility 330 秒＝AT の受け入れの上限（300＋30）。`tenant_id` の停止は DB の確認で 0 秒（`revocation` の `db_lookup`）。`name`・`email` は 86400 秒 |
| セッションと RT の寿命（ローテーション・失効・ログアウト） | トークン目録の `kind: session`・`refresh_token` の行の `max_lifetime`（絶対）・`idle_timeout`・`rt_rotation`・`revocation`。DB の接続はホップの `connection_max_lifetime` | `token_types.yaml`：RT・BFFSESSION・SSO は idle 1800 秒・最大 36000 秒。RT はローテーションあり、再利用の検知は unverified。失効は RP-Initiated Logout とセッションの削除（0 秒）、リフレッシュの失敗（330 秒）。`hops.yaml`：H3 の接続の寿命は決めていない（null。設計書の 12. の自信のない点） |
| クレームの定義の寿命（提案→有効→廃止予定→廃止） | 台帳の `status`・`sunset_on`・`owner`・`change_controller`・`consumers_migration`、最上位の `namespaces[].namespace_version`。変更履歴は Git | `claims.yaml`：すべて `active`。名前空間の構造の版は `C-v`（`namespaces[].namespace_version`）。廃止予定の行はないので、`sunset_on` と `consumers_migration` は書いていない（書ける形はスキーマにある） |

定義の寿命の層で、廃止予定（deprecated）の行を記入例で示すのは、#4 の Full の記入例（P1＋P4＋P5）で行います。

## 7. 発行方式の選択と、台帳で必要になるもの

`issuance_profile` の選択ごとに、台帳で必要になるものを [`issuance_effects.yaml`](issuance_effects.yaml) に定義しました。#6 の L62〜L64 は、この表を入力にして台帳を検査します（この PR では規則を作っていない）。

| 行 | 選択 | 台帳で必要になるもの（要約） |
| --- | --- | --- |
| `E-dpop` | DPoP | AT に `cnf.jkt`。受け手すべての `enforced_at` に DPoP proof（htm・htu・iat・jti・ath）の照合。目録で DPoP proof（`dpop+jwt`）を採用。サイズに cnf。Authorization は `DPoP` |
| `E-mtls`・`E-mtls-entry` | mTLS | AT に `cnf.x5t#S256`。`tls_termination`。入口で終端するなら `forwarded_cert_header`（同名を捨てる・入口だけが書く） |
| `E-opaque` | 不透明＋イントロスペクション | `carried_in` はイントロスペクションの応答。AT は R8 の対象外。`introspection_cache_ttl` |
| `E-phantom` | phantom token | 外の AT に組織のクレームを載せない。内部トークンを目録の別の行に。作り直すホップと `exchanger` |
| `E-client-credentials` | client credentials | 利用者のクレームを載せない。sub はクライアント（区別の手段を書く） |
| `E-token-exchange` | token exchange | `act`・`may_act`。交換のホップで下流ほど絞る（L16） |
| `E-rar` | RAR | `authorization_details` の type の語彙、宛先ごとの絞り込み、サイズ |
| `E-rt-sender-constrained` | RT を送信者制約で守る | RT のローテーションは不要（RFC 9700 §4.14.2） |
| `E-fapi-no-rotation` | FAPI 対象 | RT をローテーションしない（FAPI 2.0 Security Profile §5.3.2.1） |
| `E-public-no-sender-constraint` | 公開クライアントで送信者制約なし | RT のローテーションと再利用の検知が必須（RFC 9700 §2.2.2・§4.14.2） |
| `E-public-pkce`・`E-fapi2` | 公開クライアント・FAPI 2.0 | 認可コード＋PKCE。FAPI 2.0 は送信者制約と PAR（L63） |

シナリオ A の選択（機密の BFF、送信者制約なし、JWT の AT、ローテーション）では、どの行の条件も成り立ちません。

## 8. 改ざん防止と流出防止（JWS と JWE）

JWS が守るのは改ざんだけで、トークンを手にした者は中身を読めます（slide:p09-jws-is-readable）。そこで次の 3 つを宣言し、#6 の L65〜L67 で突き合わせます。

- クレームごとの `confidential_from`（読まれてはいけない相手）と `confidentiality_measure`（slide:p09-jwe-sd-jwt の順に、載せない → 派生値 → 参照 → JWE のどれに落ち着いたか）
- トークン種別ごとの `visible_to`（手にする・読める相手）と `jwe`（使うか。使うなら署名してから暗号化、宛先ごとの鍵、復号できる相手）
- クレームごとの `integrity_until`（署名の保護が外れる場所と、写した先の信頼境界）

記入例では、`name`・`email`・`email_verified` が `confidential_from: [browser]` で、「載せない」（ブラウザに届くものに載せない。IDT は BFF のサーバーに留める）に落ち着きました。IDT の `visible_to` は `[bff]` で、browser を含みません。`tenant_id` の `integrity_until` は、Postgres のセッション変数に写した場所です。

## 9. 「何のデータか」の語彙（data_category）

`data_category` は、そのクレームが「何のデータか」を、fideslang の data category のキーで表します。`pii_category`（個人情報保護法の区分）とは別の軸です。

- **語彙は写さない。** fideslang は CC BY 4.0 なので、CC0 の `templates/` には語彙（キーの一覧や説明文）を写しません（`research/claims-as-code/report.md`、`templates/CONTRIBUTING.md` の 4.）。台帳の最上位の `data_category_vocabulary` に、版・URL・ライセンス・確かめた日を書いて参照します。記入例は fideslang 3.1.4（https://github.com/ethyca/fideslang/blob/3.1.4/data_files/data_categories.csv、2026-11-22 に確かめた）です。
- **スキーマが確かめるのは形だけ**（小文字の英数字と `_` を `.` でつないだもの）。キーが固定した版に実在するかは確かめません（語彙を写さないため）。
- **足りない区分は、組織の子カテゴリとして足す**（`data_category_extensions`。`key` は `parent` の子で、claim_lint の REF が確かめる）。記入例では `system.operations.tenant`（テナントの識別子）を足しました。

## 10. SD-JWT VC のクレームのメタデータとの対応

SD-JWT VC の Type Metadata のクレームのメタデータ（draft-ietf-oauth-sd-jwt-vc-27 §5.6）の 4 つを、同じ名前・同じ意味で台帳の列にしました。Type Metadata は知らないプロパティを無視する決まり（同草案 §5.2）なので、台帳の独自の列と両立します。`svg_id` は描画のための参照なので入れていません。

| SD-JWT VC | 台帳の列 | 型 | 既定（SD-JWT VC） |
| --- | --- | --- | --- |
| `path` | `path` | 文字列・整数・null の配列 | なし（必須） |
| `mandatory` | `mandatory` | 真偽値 | false |
| `sd` | `sd` | always・allowed・never | allowed |
| `display` | `display` | locale・label・description・dir（ltr・rtl・auto）の配列 | dir は auto（§5.5） |

記入例では `name` に `display`（日本語と英語のラベル）を書きました。

<a id="namespace-owner"></a>
## 11. 組織の名前空間の持ち主

<!-- req:p11-reserved-names.R2 req:p11-ownership.R1 -->
組織の名前空間（記入例では `https://claims.example.com/`）は、台帳の最上位の `namespaces` に持ち主と割り当ての規則を書きます。

- **持ち主**：台帳・名前空間・スキーマを持つ中央の 1 チーム（`namespaces[].owner`）。登録を承認する（slide:p11-ownership）
- **割り当て**：名前空間の下の名前は、この台帳への登録（PR と、共有クレームなら追加前の 25 問）でだけ割り当てる（`namespaces[].assignment`。slide:p11-reserved-names）
- **変更の管理者**：組織のクレームの `change_controller` は、この持ち主（記入例では「SaaS 基盤チーム」）。登録名のクレームの `change_controller` は仕様の発行元
- 変更の承認は PR で行い、履歴は Git で持つ（4. の 12）。名前空間の下の名前が台帳に登録されているかを機械で確かめるのは #6 の L1b・L34

## 12. ケーススタディとの照合

`tools/casestudy_check.py` が、記入例の台帳を、固定したケーススタディ（`tools/casestudy_pin.json` のコミットと各ファイルの sha256）と照合します。CI（`.github/workflows/claims.yml`）で動きます。

- **ORG 行の名前と型**：`catalog_refs` が ORG 行を指す台帳の行は、`namespace` + `.` + `name` と `type`・`shape` が `catalog/catalog.json` と同じでなければ失敗する
- **採否と判定**：`catalog_refs` のすべての行（CLM・ORG）で、記入例の「載せる／載せない」とケーススタディのシナリオの判定が違えば、`templates/casestudy-deviations.yaml` に `kind: carry` で載っていなければ失敗する。載っているのに一致している行も失敗する。`kind: condition` は、ケーススタディが条件付き採用で記入例が載せる行だけに書ける。条件の使い方が違うかは文の読みなので、機械では確かめない
- **漏れ**：ケーススタディがそのシナリオで「載せる」と判定した行は、記入例のどれかの行の `catalog_refs` にあるか、`casestudy-deviations.yaml` に `kind: not_in_example` で理由とともに載っていなければ失敗する（記入例から行や参照を消して食い違いを隠せないように）
- **参照の書き方**：記入例の行はすべて `catalog_refs` を書く（一覧表に無い行は `[]` と `catalog_refs_reason`）。組織の名前空間の行は ORG の行を参照する。同じ ID を 2 つの行が参照すれば、両方の行を名指しして失敗する
- ファイルはコミットの完全な SHA で raw.githubusercontent.com から取り、sha256 を確かめてから使う（同じ固定のまま中身が変わらない）

### `templates/casestudy-mapping.md` の 8.（#3 への引き継ぎ）への回答

| 項目 | 回答 |
| --- | --- |
| ORG 行の名前と型を、固定したコミットの `catalog.json` と照合する CI | **実装した**。`tools/casestudy_check.py` の ORG（上）。シナリオ A の ORG の参照 5 件で食い違い 0 件 |
| 記入例の採否を、ケーススタディの判定と照合する CI と、`casestudy-deviations.yaml` の形式 | **実装した**。`tools/casestudy_check.py` の CARRY と COVER。形式は #16 で作った `casestudy-deviations.yaml` に `kind: not_in_example` を足した。#16 の 32 件の参照では carry 7 件・condition 1 件で、#16 の手作業の数と一致した。PR #37 の独立点検の後、同じクレームの RFC 7519 などの行 9 件を参照に足し（41 件。carry は CLM-0404 を足して 8 件）、ケーススタディが載せるとした 54 件のうち記入例が参照しない 20 件を not_in_example に理由とともに載せた |
| 一覧表の ID を参照する列（`catalog_ref`）を足すか | **足した**（#16 の v0 で配列の `catalog_refs` にした。v1 でも同じ）。一覧表は出典ごとに行が分かれるので、単数ではなく配列 |
| `alt`、`comparison`・`uniqueness`・`vocabulary`、`synonym_group` を足すか | `alt` は**足した**（却下・代替ありの代わりの行）。`vocabulary` は `value_vocabulary`、`comparison` は `value_normalization.compare` として**足した**。`uniqueness` は**足さない**：一意性はトークン種別の `jti_policy`（jti）と `identifier_properties`（識別子）で表し、クレームごとの汎用の列にする用途がシナリオ A になかった。`synonym_group` は**足さない**：一覧表の分類で、台帳では `prior_art_search` に探した結果を書く。重なりの検査（#6）で入力に要れば、`catalog_refs` から一覧表を引く |
| `decision` の値を細かくするか（代替あり・不要・禁止） | **別の列で持つ**ことにした。`decision` は 3 値のまま、却下の行に `rejection_kind`（代替あり・不要・禁止・IdP が出さない）をスキーマで必須にした。`decision` を細かくすると、R1 などの「載せる行」の判定が値の増加に引きずられるため |
| 台帳の README の列ごとの説明に、3. の対応を載せる | **載せた**。3.1 の「ケーススタディの列（区分）」 |
| ASVS を `asvs_ids` に書き、`refs` に書かない、をスキーマで確かめる | **実装した**。`refs` の `id` が ASVS で始まればスキーマの誤り（`claims.schema.json` の `$defs/ref`）。テスト：`test_asvs_is_not_written_in_refs` |

## 13. 作成方法と点検状況

本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。

> 人による点検は未実施。作成とは別の LLM のセッションで点検した。作成者の 1 日以上空けた見直しは未実施（記録：`research/reviews/registry-v1-2026-11-23.md`。対応表の実装済みの見直しは `research/reviews/registry-v1-trace-review.md`）。
