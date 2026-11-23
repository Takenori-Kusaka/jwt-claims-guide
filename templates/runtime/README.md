<!-- template_version: 0.1.0 -->
# 実行での照合の確認（#8）

静的な検査（claim-lint）は、設計書の宣言どうしが矛盾していないかしか見られません。ここにあるのは、**トークンを実際に作って受け手に渡し、拒否されるべきものが拒否されるか、交換で実際に絞られているか、剥奪が許容時間以内に効くか、受け手が宣言したクレームだけを読むか**を確かめるテストです。

| ファイル | 中身 |
| --- | --- |
| [negative_tests.md](negative_tests.md) | 拒否のテスト 32 件（検証の基本、テナントと BOLA、寿命と失効、交換、伝搬と委任、データ層）と、まだ作っていない 4 件 |
| [consumer_contract.md](consumer_contract.md) | 受け手の契約テスト 5 件（読むクレームの宣言、未知のクレーム、黙った欠落、型と形、形式の変化）と、まだ作っていない 1 件 |
| [golden_tokens.md](golden_tokens.md) | テストの出発点にする正規のトークン（シナリオ A の AT、シナリオ B の TXN・AGENT_AT・TASK_AT）と、鍵と発行者の決まり |
| [lifetime_revocation.md](lifetime_revocation.md) | 寿命と失効のテストの時間の縮め方（330 秒を 22 秒に）と、測った値の読み方 |
| `../../tools/runtime_tests/` | 実行するコード（MIT）。参照の受け手、トークンの作り方、テストの本体、実行の記録の出力 |
| `../../research/runtime/` | 実行の記録（JSON と Markdown） |

## 実行

```
python tools/runtime_tests/run.py --env offline --log research/runtime/run-offline-YYYY-MM-DD.json
python tools/runtime_tests/run.py --env live    --log research/runtime/run-live-YYYY-MM-DD.json
```

| 環境 | 動かす場所 | 必要なもの | 中身 |
| --- | --- | --- | --- |
| offline | CI（`.github/workflows/claims.yml`）と手元 | Python 3.12 以上、`tools/requirements-ci.txt`（PyYAML・jsonschema・cryptography） | 試験用の鍵をその場で作り、手で署名したトークンを参照の受け手に渡す。34 件 |
| live | 手元だけ | 上に加えて `requests`・`psycopg[binary]`。WSL（Ubuntu-24.04）の Docker と `docker compose`。イメージ `quay.io/keycloak/keycloak:26.8.0`・`postgres:16-alpine` | Keycloak 26.8.0（レルム t1・t2・corp）と Postgres 16 を立てて、実物のトークンと DB で確かめる。15 件。約 3 分 |

- live のコンテナは compose のプロジェクト名 `jcg-issue8-runtime`、ホストのポート 38080（Keycloak）と 35432（Postgres）で動きます。ケーススタディ（18080・15432）や、ほかの作業のコンテナとぶつからないようにするためです。実行の終わりに `docker compose -p jcg-issue8-runtime down -v` でコンテナと volume を消します。途中で止めたときは、同じコマンドを手で実行してください。
- レルムの定義は実行のたびに一時ディレクトリに作り（`tools/runtime_tests/kc.py`）、終わったら消します。管理者・DB・利用者のパスワードとクライアントシークレットは実行のたびに乱数で作り、記録に残しません。
- 記録に残すのは、試験用の利用者の**復号したクレーム**と、観測した結果だけです。生のトークン・鍵・パスワードは残しません（`tools/tests/test_runtime.py` が記録に JWT や PEM の形が無いことを確かめる）。

## テストと対応表

- 各テストの ID は、対応表の計画の項目（`templates/trace/planned_items.yaml` の `test:<ファイル>#<アンカー>`）と同じです。
- 各テストの節には、その項目を成果物に持つ要件の ID を `req:` で書いています（対応表の逆引き）。実行の記録の要件の列も、同じ対応表から作ります。
- `tools/tests/test_runtime.py` が、テストのコードと文書の節の一致（アンカー、`req:` の印、claim-lint の規則）を確かめます。
- 観点書（`templates/review/perspectives.md`）の問いの「つながり」は、ここのテストの ID を指します。

## 確かめていないこと

- 自組織の受け手（API・ゲートウェイ）が同じように拒否するか。ここで確かめたのは、記入例の設計のとおりに書いた参照の受け手です
- DPoP の proof の検証、PgBouncer の transaction pooling、ネストした JWT、push 配送、acr による段階的な認証
- シナリオ B の入口の正規化（IdP ごとの形の正規の要求の受理）。negative_tests.md の 9.

## 作成方法と点検状況

本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。

人による点検は未実施。作成とは別の LLM のセッションでの点検は、PR のレビューで行う（記録：`research/reviews/runtime-facts.md` の事実の一覧を点検の入力にする）。作成者の 1 日以上空けた見直しは未実施。
