<!-- template_version: 0.1.0 -->
# 受け手の契約テスト

受け手が **どのクレームを読むか** を台帳（`claims.yaml` の `consumers`）で宣言し、その宣言と受け手の実際の読み方が一致しているかを実行で確かめます（#8、slide:p11-schema-contract-tests）。宣言と食い違えば、クレームを変える・消すときに、誰が壊れるかを台帳から数えられなくなります（slide:p00-claims-are-contracts）。

- 受け手の例はシナリオ A の参照の saas-api（`tools/runtime_tests/scenario_a.py`）です。
- 契約テストの部品は `tools/runtime_tests/contract.py` です。受け手に渡すペイロードを、読まれたメンバーを記録する辞書（`Recording`）に包み、受け手を 1 回動かしてから、読まれたメンバーを台帳の行（名前空間＋名前）に引き当てます。
- 実行のしかたは [negative_tests.md](negative_tests.md) の 1. と同じです（`--select consumer_contract#declared-reads` など）。

本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。点検状況は [README.md](README.md) の「点検状況」を見てください。

## 1. 一覧

| テスト | 確かめること | 環境 |
| --- | --- | --- |
| [`declared-reads`](#declared-reads) | 受け手が読むクレームが台帳の `consumers` にある。`consumers` から外すと失敗する | CI |
| [`unknown-claim-ignored`](#unknown-claim-ignored) | 未知のクレームを足しても受け手が拒否しない | CI |
| [`issued-claims-present`](#issued-claims-present) | 発行されたトークンに、台帳で載ると宣言した独自クレームが全部ある | CI・実物 |
| [`type-shape-match`](#type-shape-match) | 発行されたトークンの型と形が、台帳から生成した issuer 適合のスキーマに合う | CI・実物 |
| [`format-change-cases`](#format-change-cases) | 型の変わらない形式の変化を、どの検査が見つけるか（型だけの契約の死角） | CI |

<a id="declared-reads"></a>

## 2. declared-reads　読むクレームの宣言

<!-- req:p00-claims-are-contracts.R7 req:p11-schema-contract-tests.R4 -->

- テスト ID：`test:consumer_contract#declared-reads`
- 要件：`p00-claims-are-contracts.R7`（#8・core）、`p11-schema-contract-tests.R4`（#8・core）
- claim-lint：`lint:L18`（deprecated・sunset のクレームを読む受け手）、`lint:L11`（読む受け手ごとの `enforced_at`）。どちらも宣言を見る規則で、受け手が宣言のとおりに読むかはこのテストが見る
- スライド：`slide:p00-claims-are-contracts`、`slide:p11-schema-contract-tests`
- 題材と環境：シナリオ A。オフライン（CI）
- 手順：
  1. 見本の AT（[golden_tokens.md](golden_tokens.md#scenario-a-at)）で参照の saas-api に一覧の要求を送り、読まれたメンバーを記録する
  2. 読まれたメンバーごとに、台帳の行（`namespace`＋`name`）を引き、その行の `consumers` に `saas-api` があるかを見る
  3. 読むクレームの型を、台帳から生成した今の版の consumer のスキーマ（`templates/examples/scenario-a/schemas/AT.consumer.schema.json`）で確かめる。台帳を変えて `tools/claim_lint render` でスキーマを作り直すと、次の実行はその版で回る
  4. 台帳の写しで、`C-roles`・`C-tenant-id`・`C-azp` の `consumers` から `saas-api` を 1 つずつ外し、2. をやり直す
- 期待する結果：1.〜3. は違反 0 件。4. はどれも違反になり、契約テストが失敗する。あわせて、受け手が AT に載せない宣言の `email`（台帳の `carried_in` に AT が無い）を読まないことも確かめる
- 記録の例（2026-11-23）：saas-api が読むのは iss・sub・aud・exp・iat・jti・azp と、名前空間の tenant_id・user_id・v・roles。どれも台帳の `consumers` に saas-api がある
- 注：読んだかどうかは、トークンにあるメンバーを `[]`・`get`・`in` で触ったかで数える。トークンに無いメンバーを探しただけ（nbf が無いかの確認など）は数えない

<a id="unknown-claim-ignored"></a>

## 3. unknown-claim-ignored　未知のクレームを無視する

<!-- req:p04-forward-compatibility.R1 -->

- テスト ID：`test:consumer_contract#unknown-claim-ignored`
- 要件：`p04-forward-compatibility.R1`（#8・full）
- claim-lint：—（受け手の振る舞いで、宣言の規則はない）
- スライド：`slide:p04-forward-compatibility`
- 題材と環境：シナリオ A。オフライン（CI）
- 作るトークン：見本の AT の最上位に未知のクレームを 2 つ足したもの、名前空間に未知の department を足したもの
- 期待する結果：どちらも受理する（拒否しない）。受け手の consumer のスキーマ（`AT.consumer.schema.json`）も未知のクレームを許す
- 注：未知のクレームを無視するので、**制限を表すクレームを後から足しても、古い受け手は黙って無視する**。この死角は [format-change-cases](#format-change-cases) の「制限のクレームの追加」で扱う

<a id="issued-claims-present"></a>

## 4. issued-claims-present　発行されたトークンの黙った欠落

<!-- req:p03-entra-scp-roles-groups.R4 req:p03-auth0-namespace.R2 -->

- テスト ID：`test:consumer_contract#issued-claims-present`
- 要件：`p03-entra-scp-roles-groups.R4`（#8・full）、`p03-auth0-namespace.R2`（#8・full）
- claim-lint：—（宣言と発行の食い違いは、発行されたトークンでしか分からない）
- スライド：`slide:p03-entra-scp-roles-groups`、`slide:p03-auth0-namespace`
- 題材と環境：シナリオ A。オフライン（CI：Keycloak 26.8.0 が発行した見本 `tools/tests/fixtures/claim_lint/golden/token.json`）・実物（Keycloak 26.8.0 のレルム t1）
- 手順：台帳で `decision: 採用` かつ `carried_in` に AT がある行が、発行された AT に全部あるかを見る。`on_missing: 既定値` の行（roles）は、無くてもよい
- 期待する結果：クライアント saas-web の AT は欠落 0 件。軽量アクセストークン（クライアント saas-light）は欠落を検出する（名前空間・aud・sub が落ちる。ケーススタディ keycloak.lightweight と同じ）
- 注：Entra の groups の超過と Auth0 の予約名の黙った削除そのものは、シナリオ A に無い。同じ型の「宣言したのに出ていない」を Keycloak の軽量アクセストークンで確かめた

<a id="type-shape-match"></a>

## 5. type-shape-match　型と形の一致

<!-- req:p04-type.R1 -->

- テスト ID：`test:consumer_contract#type-shape-match`
- 要件：`p04-type.R1`（#3・core）
- claim-lint：—（スキーマは `tools/claim_lint render` が台帳から生成する。CI の「Keycloak-issued golden AT conforms to the issuer-conformance payload schema」と同じスキーマ）
- スライド：`slide:p04-type`
- 題材と環境：シナリオ A。オフライン（CI）・実物
- 手順：発行された AT を `templates/examples/scenario-a/schemas/AT.issuer.schema.json`（additionalProperties false）で検証する。見本を 1 か所ずつ変えたもの（roles を文字列、tenant_id を配列、v を数値、知らないクレームの追加）も検証する
- 期待する結果：発行された AT はスキーマの誤り 0 件。変えたものはどれも誤りになる

<a id="format-change-cases"></a>

## 6. format-change-cases　契約テストが見逃しやすい変更

<!-- req:p11-contract-test-gaps.R1 req:p11-contract-test-gaps.R2 -->

- テスト ID：`test:consumer_contract#format-change-cases`
- 要件：`p11-contract-test-gaps.R1`（#8・full）、`p11-contract-test-gaps.R2`（#6・full）
- claim-lint：`lint:L24`（未実装）
- スライド：`slide:p11-contract-test-gaps`
- 題材と環境：シナリオ A。オフライン（CI）
- 手順：見本の AT に発行側の形式の変化を 1 つずつ入れ、3 つの検査（受け手の consumer のスキーマ＝型だけの契約、issuer 適合のスキーマ、参照の saas-api）のどれが見つけるかを記録する
- 期待する結果：

| 変化 | 型だけの契約（consumer のスキーマ） | issuer 適合のスキーマ | 参照の saas-api |
| --- | --- | --- | --- |
| 区切り文字：roles を配列から空白区切りの 1 つの文字列に | 見つける（型が変わる） | 見つける | 拒否（claim-type） |
| 区切り文字：roles の要素を `approver,tenant-admin` の 1 要素に | **見逃す** | 見つける（語彙の enum） | 受理し、ロールとして数えない |
| 大文字化：tenant_id を T1 に | **見逃す** | **見逃す** | 拒否（tenant-iss-mismatch） |
| 2^53 を超える数値：user_id を数値 9007199254740993 に | 見つける | 見つける | 拒否（user-id-mismatch） |
| null：roles を null に | 見つける | 見つける | 拒否（claim-type） |
| false：tenant_id を false に | 見つける | 見つける | 拒否（claim-type） |
| 真偽値の文字列化に当たるもの：v を `"true"` に | **見逃す** | **見逃す** | 拒否（unknown-version） |
| 制限のクレームの追加：名前空間に read_only: true | **見逃す**（未知を許す） | 見つける（additionalProperties false） | **受理し、黙って無視する** |

- あわせて、2^53 を超える整数を倍精度で読む受け手（JavaScript の Number と同じ読み方）では値が変わることを確かめる
- 注：シナリオ A の AT に真偽値のクレームはありません。「真偽値の文字列化」は、文字列の語彙を持つ版の値 v で代えました。**型だけの契約テストは、上の表の「見逃す」を見つけられません。** 値の語彙（`value_vocabulary`）と issuer 適合のスキーマ、受け手の完全一致の照合を併せて使います

## 7. まだ作っていないテスト

| 計画の項目 | 要件 | 作っていない理由 |
| --- | --- | --- |
| `test:consumer_contract#tool-access-path` | `p04-namespace.R2`（#8・full） | 受け手のツール（ゲートウェイ・メッシュ・CEL・JSONPath）の参照式で名前空間のクレームを読む試験が要る。参照の受け手は Python だけ |

ファイル全体を指す `test:consumer_contract`（#3・#4・#6 が担当の要件の成果物）は、このファイルそのものに解決します。
