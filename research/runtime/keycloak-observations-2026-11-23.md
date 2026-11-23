# Keycloak 26.8.0 の 2 つの観測（#8）

#8 の live の実行（`run-live-2026-11-23.md`）と、PR #48 の独立点検の再現（PR のコメント、一時の compose プロジェクト `jcg-pr48-check`）で観測したことを、条件とあわせて記録します。どちらも Keycloak の不具合ではなく、設計で扱う事柄です。

- 環境：`quay.io/keycloak/keycloak:26.8.0`（image id sha256:27b3230fbabb8c9ff3c66c864cf09dcd8a41aca82e5100679d109ef0eeb05741）、`start-dev --features=token-exchange-standard:v2`。レルムは `tools/runtime_tests/kc.py` が実行のたびに作る
- 作成：2026-11-23、LLM（Claude、Opus 5.5）。人による点検は未実施

## 1. 標準のトークン交換（V2）で出た AT の exp

| 条件 | 観測 | 出どころ |
| --- | --- | --- |
| レルム corp（accessTokenLifespan 300）、portal で carol の AT（scope `openid aud-mcp`）を取り、3 秒後に mcp-tools が交換（audience invoices・scope aud-invoices など 5 通り） | 交換で出た AT の `exp − 元の exp` = +3 秒。寿命（exp − iat）はどちらも 300 秒 | 本リポジトリの live（`run-live-2026-11-23.md` の exchange-narrowing） |
| 同じ、待たずに交換 | +0〜+1 秒 | 本リポジトリの live の試行（2026-11-23、記録は残していない） |
| corp の寿命を 20 秒にし、15 秒後に交換 | +16 秒。寿命はどちらも 20 秒。RT は出ない | 独立点検の再現（PR #48 のコメント） |
| 元の AT が期限切れになった後に交換 | 400（`invalid_request: Invalid token`） | 独立点検の再現 |

読み方：

- 交換で出る AT の寿命は、交換の時刻から寿命 1 本分で、**元の AT の exp では抑えられない**。1 回の交換で延びるのは、元の AT の残りの寿命まで（元が切れていれば交換できない）なので、上限はおよそ寿命 1 本分（300 秒）
- 交換を重ねる構成では、ホップの数だけ延びうる（試していない）
- Keycloak の文書（Securing Applications 26.8.2「Standard token exchange」を `templates/modules/M_idp_keycloak.md` の 9. が要約した記述）は「AT は subject token の exp を超えない（既定）」としており、この観測と食い違う。文書の版（26.8.2）とイメージの版（26.8.0）の違いか、記述の読み違いかは確かめていない（点検の対象）
- RFC 8693 は、交換で出すトークンの exp を元で抑えることを求めていない
- 設計で扱うこと：受け手（または交換のサービス）が `exp` と元の `exp` を比べるか、交換のクライアントの寿命を短くする。L16 の「寿命が上流より長い」に当たる。`tools/runtime_tests/narrowing.py` は「exp extended」と指摘する

## 2. ローテーション済みの RT の再提示

条件：レルム t1、`revokeRefreshToken: true`・`refreshTokenMaxReuse: 0`、クライアント saas-web（機密クライアント）。

| 手順 | 観測 | 出どころ |
| --- | --- | --- |
| RT1 でリフレッシュして RT2 を得た後、RT1 を再提示 | 400 `invalid_grant: Maximum allowed refresh token reuse exceeded` | 本リポジトリの live（rt-reuse） |
| 続けて RT2 でリフレッシュ | 400 `invalid_grant: Session doesn't have required client`（系列の新しい RT も失効） | 本リポジトリの live、独立点検の再現 |
| 順番を逆に：攻撃者が先に RT1 で RT2a を得て、正規の利用者が RT1 を再提示 | 攻撃者の RT2a も失効した | 独立点検の再現 |
| 再提示の後の管理 API のセッションの一覧 | 利用者のセッションは残り、そのクライアント（saas-web）のセッションだけが消えていた | 独立点検の再現 |

読み方：

- 再提示で失効するのは **クライアントのセッション**（そのクライアントの RT の系列）で、**利用者の SSO のセッションは続く**。BFF のセッションは次のリフレッシュの失敗で終わるが、IdP にログインしたままなので、再ログインは利用者の操作なしで済みうる
- 観測は `refreshTokenMaxReuse: 0` に依存する。0 では、BFF が同じ RT で 2 つのリフレッシュを並行して送るだけで、2 つ目が再提示とみなされ、正規の利用者が BFF からログアウトする（上の観測からの推論。並行のリフレッシュそのものは試していない）
- 設計の注（筆者の提案、追跡 #8）：Keycloak の RT のローテーションを使う BFF は、リフレッシュを利用者のセッションごとに直列にする。`templates/modules/M_idp_keycloak.md` の 9. と `templates/profiles/P1_human_web.md` の 4. に行を足した
- シナリオ A の台帳（`templates/examples/scenario-a/token_types.yaml` の RT）は `reuse_detection: unverified` のまま。値を直すかは記入例の担当（#16・#3）が決める。対応表の `p08-rotation.R3` は未着手のまま
