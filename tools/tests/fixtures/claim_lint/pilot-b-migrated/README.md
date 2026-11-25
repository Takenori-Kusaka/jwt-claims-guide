# パイロットのシナリオ B を、台帳 0.3.0 の列で写した fixture（#58）

`research/pilot/scenario-b/`（パイロット #9 のブラインド記入。**LLM による記入で、人による記入・検証ではない**）の台帳を、#58 で足した列で書き直したものです。パイロットの記録は証拠なので書き換えず、ここに写しを置きます。

- 作り方：`python tools/tests/fixtures/claim_lint/pilot-b-migrated/migrate.py`（パイロットの 4 つの YAML を読み、下の表の変更だけを当てて書き出す。`--check` は、置いてあるファイルが書き出しと同じかを確かめる）。YAML は手で直しません
- 検査：`python tools/claim_lint tools/tests/fixtures/claim_lint/pilot-b-migrated` が **error 0・warn 3・info 33**（2026-11-25）。テストは `tools/tests/test_claim_lint_multi_idp.py`（規則ごとに、この fixture の宣言を 1 つ壊して落ちることを確かめる）
- 値：パイロットの値のままです。足した行の事実（IdP のクレームの名前と意味）は `tools/claim_lint/idp_claims.yaml` の出どころ（2026-11-25 に確認）によります。Cognito が private_key_jwt に対応しない、という例外の理由は、パイロットの書き手の記述のままで、確かめていません
- `design.md` は写していません（設計書の本文と `render` の区間は、パイロットの版のまま読んでください）

## 回避策と、書き直した後

| # | パイロットの回避策（`author-log.md` の迷った点） | 起きていたこと | この fixture | lint の結果 |
| --- | --- | --- | --- | --- |
| 1 | `idp` に Keycloak だけを書き、ほかの 4 つは `searched` に URL を書いた（迷い 1） | R3・R3b・L2 が Keycloak しか見ない。Auth0 の名前空間の roles（C-auth0-roles）を Keycloak のマッパーと照合していた（R3b の info 3 件） | `idp` を 5 つの配列にし、IdP ごとに `token_types` を書いた。Cognito には `trigger_list`（6 項目）を足した | R3 が IdP ごとに info 4（Cognito は一覧の全項目が通る）。R3b が Auth0 の Actions と照合し、warn 1（I26：書き手の確認は Keycloak についての文）。L2 が Cognito の一覧と照合 |
| 2 | `oid`・`tid`・`uid`・`cid`・`scp`・`token_use`・`cognito:groups`・`realm_access` を台帳の行にせず、`source_attribute` と `validates.checks` の文に書いた（迷い 4） | `on_missing`・`identifier_properties`・`required_claims`・受け手の Schema が付かなかった（指摘 B-R1 F01・B-R2 R2-03、どちらも Major） | `idp_defined` の行を 10 足した（Entra 3・Okta 3・Cognito 2・Keycloak 2。Keycloak はペイロードの `typ` を含む）。拒否する 8 つを IdP の AT の `required_claims` に足した | L1b が 10 行を info（error 0）。`ENTRA_AT.consumer.schema.json` に当たる Schema の `required` に `tid`・`oid`・`scp` が入る。行を消すと L74 が warn |
| 3 | 作り直しのホップ H7・H8 の `upstream` を外し、`note` に理由を書いた（迷い 7） | 寿命・宛先の絞り込みの検査（L16）が走らなかった（機会 0）（指摘 B-R1 F08・B-R2 R2-23） | `upstream: [H2, H3, H4, H5, H6]`、`added_claims`（roles は上流のクレームから導く、部署・社員番号は社員台帳）、`aud_mapping`（Entra は aud、Okta・Cognito・Auth0 は scope） | L16 の機会 10（独自クレーム）・10（広げる部分）。error 0・warn 0・info 2 |
| 4 | COGNITO_AT の `required_claims` を書かなかった（迷い 5） | Cognito の AT の必須の検証が宣言されない（受け手の Schema の `required` が空） | `audience_claim: client_id` と `required_claims`（aud を含まない） | L27 が info（error 0） |
| 5 | `typ` の欄に「JWT（…で区別する）」のような文を書いた（迷い 6） | L17 は文字列が違うので通るが、区別の宣言を機械が読めない | `typ` をヘッダーの値に戻し（Cognito・Okta は `(absent)`）、`kind_discriminator` を書いた | L17 が、typ が JWT の 5 種別を info（種類の違う組がすべて排他） |
| 6 | Cognito のクライアント認証の例外を `rationale` の文に書いた（迷い 16） | 例外の値を機械が読めない | `issuance_profile.client_auth.exceptions` | L62 の指摘なし |

残る warn 3 件：L69（C-groups）と L11（C-sub-unread）はパイロットの書き手が設計の判断として残したもの、R3b（I26）は上の 1 で新しく出たものです。

## 写しても変わらないこと

- ID トークンは 1 行のままです（パイロットの迷い 27）。`typ: JWT` は 5 つの IdP の ID トークンをまとめた値で、Cognito の ID トークンのヘッダーには当てはまりません
- Okta の AT のヘッダーの typ は未確認です（Okta の文書はヘッダーの予約のクレームに alg と kid だけを挙げる）。ここでは `(absent)` と書きました
- Okta の再利用されうる `sub` を別の行（C-sub-unread）にする書き方（迷い 8）と、`tenant_binding`（迷い 17）は、#59 の候補 5・6 です。Entra の `tid` の固定は、`C-entra-tid` の行の `enforced_at`（`against: [api_config, iss]`）に書けるようになりました
