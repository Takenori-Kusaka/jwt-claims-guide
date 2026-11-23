<!-- template_version: 0.1.0 -->
# 見本のトークン

拒否のテスト（[negative_tests.md](negative_tests.md)）と契約テスト（[consumer_contract.md](consumer_contract.md)）の出発点にする、**正規の**トークンです。各テストは見本を 1 か所だけ変えて作るので、拒否の理由はその 1 か所に限られます。見本そのものが受理されることも、毎回確かめます（下の各節の「受理の確認」）。

本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。点検状況は [README.md](README.md) の「点検状況」を見てください。

## 1. 鍵と発行者の決まり

- **鍵は試験用のものを実行のたびに作り、ディスクに書きません**（`tools/runtime_tests/jose.py` の `Key`：RSA 2048 と P-256）。リポジトリに入るのは、ヘッダーとペイロードを組み立てるコード（`tools/runtime_tests/golden.py`）だけです。署名したトークンも、秘密鍵も、コミットしません（templates/CONTRIBUTING.md 4.「秘密情報の検出」）。
- **自分で作るトークンの `iss` には `example` を含めます**：`https://idp.example.com/realms/t1`・`https://idp.example.com/realms/t2`（シナリオ A の台帳の issuers と同じ）、`https://sts.corp.example.com`・`https://tts.corp.example.com`（シナリオ B）。実在の発行者と取り違えないためです。
- 攻撃者の鍵（`attacker`：t1 の鍵と同じ kid で中身が違う、`attacker_own`：誰も設定していない kid）も、同じように実行のたびに作ります。
- 時刻は固定の `NOW = 1800000000`（2027-01-15T08:00:00Z）を使います。期限切れや時計のずれのテストが、実行した日に左右されないためです。
- 実物（live）の環境では、Keycloak 26.8.0 がレルムの鍵で署名します。鍵はコンテナの中にだけあり、実行の終わりにコンテナごと消えます。実物の `iss` は `http://localhost:38080/realms/t1` なので、参照の受け手は台帳の `https://idp.example.com/realms/t1` をこの値に読み替えてから、完全一致で比べます（`scenario_a.SaasApi` の `issuer_map`）。

<a id="scenario-a-at"></a>

## 2. シナリオ A の AT

- テスト ID：`test:golden_tokens#scenario-a-at`（受理の確認。オフラインと実物）
- 形：#16 の縦の一本で Keycloak 26.8.0 が発行した見本（`tools/tests/fixtures/claim_lint/golden/token.json`、1045 バイト）と同じメンバーにし、`iss` を台帳の発行者に、値を試験用の値に替えた

ヘッダー：

```json
{"alg": "RS256", "typ": "at+jwt", "kid": "t1-rs256"}
```

ペイロード（`golden.at_payload()`）：

```json
{
  "exp": 1800000300, "iat": 1800000000, "auth_time": 1800000000,
  "jti": "onrtac:00000000-0000-4000-8000-000000000001",
  "iss": "https://idp.example.com/realms/t1", "aud": "saas-api", "sub": "alice-sub",
  "typ": "Bearer", "azp": "saas-web", "sid": "golden-session-1", "scope": "openid",
  "https://claims.example.com/": {"tenant_id": "t1", "user_id": "alice-sub", "v": "1", "roles": ["approver"]}
}
```

- t2 の見本は `tenant='t2'`・`sub='bob-sub'` で作り、t2 の鍵（kid `t2-rs256`）で署名します。
- 受理の確認：参照の saas-api が t1 の見本で /t1 を一覧し、t1 の行だけを返す。t2 の見本で /t2 を一覧できる。実物では、Keycloak がクライアント saas-web で発行した alice の AT で、Postgres の RLS つきで /t1 を一覧できる

<a id="scenario-b-tokens"></a>

## 3. シナリオ B の TXN・AGENT_AT・TASK_AT

- テスト ID：`test:golden_tokens#scenario-b-tokens`（受理の確認。オフライン）
- 署名は ES256（シナリオ B の台帳の alg_allowlist）。sts の鍵（kid `sts-es256`）と tts の鍵（kid `tts-es256`）

TXN（`golden.txn_payload()`、ヘッダーの typ は `txntoken+jwt`）：

```json
{"iss": "https://tts.corp.example.com", "iat": 1800000000, "exp": 1800000300, "aud": "https://corp.example.com",
 "txn": "txn-0001", "sub": "emp-0001", "scope": "orders.read ledger.read",
 "req_wl": "spiffe://corp.example.com/gateway", "tctx": {"operation": "ledger.read"}, "jti": "txn-jti-1"}
```

TASK_AT（`golden.task_payload()`、ヘッダーの typ は `at+jwt`）：

```json
{"iss": "https://sts.corp.example.com", "sub": "u1", "aud": "invoices", "exp": 1800000300, "iat": 1800000000, "jti": "task-jti-1",
 "client_id": "invoice-mcp", "scope": "invoices.pay", "cnf": {"jkt": "golden-thumbprint"},
 "act": {"sub": "invoice-mcp", "act": {"sub": "agent:expense"}},
 "authorization_details": [{"type": "https://claims.example.com/rar/payment", "actions": ["pay"], "identifier": "inv-1",
                            "instructedAmount": 120000, "creditorAccount": "JP00-1234-5678"}],
 "https://claims.example.com/": {"tenant_id": "corp", "user_id": "u1", "task_id": "task-1", "approval_id": "appr-1", "v": "1"}}
```

- AGENT_AT（`golden.agent_payload()`）は TASK_AT の aud を `invoice-mcp`、client_id を `agent:expense`、scope を `invoices.read invoices.pay`、act を `{"sub": "agent:expense"}` にしたもの（H14 の上流）
- 受理の確認：参照の ledger が TXN を Txn-Token ヘッダーで受け、参照の invoices が TASK_AT で承認どおりの支払いを受ける
- 注：DPoP の proof は作りません。cnf は必須クレームとして置くだけです（#8 のテストはクレームを見るもので、送信者制約は見ない）

## 4. 使わないもの

- 本番の IdP が発行したトークン、本番の鍵
- 期限の無いトークン（`exp` を欠くトークンは、欠落のテストでだけ作る）
- `.broken` の教材（#12）のトークン。拒否のテストのトークンは実行のたびに作って捨てるので、ファイルに残しません
