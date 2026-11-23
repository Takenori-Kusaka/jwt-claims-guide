<!-- template_version: 0.1.0 -->
# 寿命と失効のテスト

剥奪・ログアウト・利用者の無効化のあと、**宣言した許容時間以内に拒否されるようになるか**を実行で確かめます（#8、slide:p08-stale-claims、lint L5）。テストの本体は [negative_tests.md](negative_tests.md) の 5.（`revocation-latency`・`revoked-token-rejected`・`rt-reuse`）にあります。この文書は、時間の縮め方と、測った値の読み方を書きます。

本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。点検状況は [README.md](README.md) の「点検状況」を見てください。

## 1. 宣言した許容時間（シナリオ A）

| 何が変わるか | 台帳の宣言 | 許容時間 |
| --- | --- | --- |
| ロールの剥奪（`C-roles`） | `volatility: 330`、`propagation_delay: 330`。AT の失効の手段は `exp_only`（delay 330） | 330 秒（寿命 300 秒＋受け手の時計のずれ 30 秒） |
| IdP 側のセッションの終了・利用者の無効化 | AT の `refresh_failure`（delay 330）、BFFSESSION の `refresh_failure`（delay 330） | 330 秒（BFF の次のリフレッシュの失敗で BFF のセッションを終える） |
| テナントの停止（`C-tenant-id`） | AT の `db_lookup`（delay 0）。API がすべての要求で tenants.status を引く | 0 秒（次の要求） |
| ローテーション済みの RT の再提示 | RT の `rt_rotation: {rotation: true, reuse_detection: unverified}` | 再提示した RT は拒否。系列の RT の扱いは確かめていなかった（下の 5.） |

<a id="scaling"></a>

## 2. 時間の縮め方

330 秒を待つテストは、手元で何度も回すには長すぎます。そこで、**寿命と時計のずれを同じ比（1/15）で縮めた設定**で測り、上限も同じ比で縮めた値と比べます。

| 値 | 本番の宣言 | テストの設定 | 設定した場所 |
| --- | --- | --- | --- |
| AT の寿命 | 300 秒 | 20 秒 | Keycloak のレルム t1 の accessTokenLifespan（テストの間だけ管理 API で変え、終わったら 300 秒に戻す） |
| 受け手の時計のずれ | 30 秒 | 2 秒 | 参照の saas-api の max_clock_skew（`cases_live.py` の `SHORT`） |
| 受け入れの上限（寿命＋ずれ） | 330 秒 | 22 秒 | 比べる上限 |

縮めてよい理由：この設計の反映の遅れは、すべて AT の期限で決まります。

- 剥奪の前に出た AT は、受け手のローカルの検証で exp＋ずれまで通ります（exp_only）。反映の遅れは「AT の残りの寿命＋ずれ」で、寿命とずれに比例します。
- BFF は AT の期限でリフレッシュし、そのときに Keycloak がロールを評価し直す・セッションの終了を返すので、BFF の側の遅れも「AT の残りの寿命」以下です。
- 比に乗らないのは、ネットワークと Keycloak の応答の時間（数十ミリ秒）と、テストの要求の間隔（1 秒）だけです。これらは縮めた設定では相対的に大きく効くので、縮めた設定で上限の内に入れば、本番の値でも上限の内に入ります（保守側の誤差）。
- 逆に、縮めた設定では見えないもの：Keycloak の SSO セッションの idle（1800 秒）と最大（36000 秒）、JWKS のキャッシュ（3600 秒）は縮めていません。テストの数十秒の間には効かないので、結果に影響しません。
- 時計のずれ（2 秒）は、IdP と受け手が同じホストにいるので、実際には使われていない（設定の値として受け入れの上限に効くだけ）。BFF の経路の遅れには、受け手のずれは関係しない。ずれそのものの扱いは、オフラインの `expired`・`nbf-future` で境界を確かめる
- 鍵の削除の反映（JWKS のキャッシュの TTL 3600 秒）は、このテストの対象外。参照の受け手は TTL を実装していない（未知の kid の取り直しの間隔と負のキャッシュだけを実装し、`untrusted-key` で確かめる）

<a id="role-revocation"></a>

## 3. ロールの剥奪（revocation-latency）

- 手順：縮めた設定のレルム t1 で、参照の BFF が alice でログインし、1 秒ごとに API を呼ぶ。2 秒後に管理 API で alice から approver を外す。API が見るロール（その時点の AT の名前空間の roles）から approver が消えるまでの時間を測る
- 記録（2026-11-23、`research/runtime/run-live-2026-11-23.md`）：18.1 秒。縮めた上限 22 秒の内
- 読み方：approver は、BFF が AT の期限（発行から 20 秒）でリフレッシュした新しい AT から消えた。剥奪は発行から約 2 秒後なので、期待は約 18 秒
- 本番の値での見積もり：剥奪の時刻は縮めていない（発行から 2 秒）ので、18.1 秒を比で直す意味はない。この経路の最悪は、AT が発行された直後に剥奪した場合の「寿命＋要求の間隔」で、本番の値では約 301 秒（寿命 300 秒＋テストの要求の間隔 1 秒）。宣言した上限 330 秒の内に入る。受け手のずれ 30 秒は、BFF の外に写した AT を受け手が直接受けるときにだけ足される（exp_only の上限 330 秒）

<a id="tenant-suspension"></a>

## 4. テナントの停止（revocation-latency）

- 手順：Postgres の tenants.status を suspended にした直後に、同じ AT で要求する
- 記録：次の要求が tenant-suspended で拒否された（停止から拒否まで数ミリ秒）。AT の exp を待たない（volatility 0 の宣言どおり）
- オフラインの版：`MemoryStore` の状態を変えて同じことを確かめる（CI）

<a id="bff-session"></a>

## 5. IdP 側のセッションの終了と BFF のセッション（revoked-token-rejected、A03）

- 手順：縮めた設定のレルム t1 で、参照の BFF が alice でログインし、1 秒ごとに API を呼ぶ。3 秒後に、(1) 管理 API で alice のセッションを消す、(2) 別の回で alice を無効にする。BFF のセッションが終わるまでの時間を測る。あわせて、BFF の外に写した AT（盗まれた AT）を使う
- 記録（2026-11-23）：(1)・(2) とも、取り消しから約 17 秒で BFF のリフレッシュが失敗し（(1) は `invalid_grant: Session not active`、(2) は `invalid_grant: User disabled`）、BFF のセッションが終わった。縮めた上限 22 秒の内。盗まれた AT（BFF の外の写し）は、取り消しの直後（発行から約 3 秒、exp の前）に受け手が受理し（exp_only の残り）、発行から 23 秒後は expired で拒否された
- 読み方：BFF は、AT が期限切れになるまでリフレッシュしないので、取り消しの後も AT の残りの寿命の間は要求が通る。これは設計が許した遅れ（330 秒）で、ログアウトトークンを却下した前提（token_types.yaml の LOGOUT の assumption）どおり
- 注：「失効を受け取る」手段は、この設計ではリフレッシュの失敗だけ（ログアウトトークンと SET は却下。token_types.yaml の LOGOUT・SET）。p08-revocation-propagation.R2 はこの手段で確かめた

<a id="rt-reuse"></a>

## 6. RT の再提示（rt-reuse）

- 手順：リフレッシュで RT1 を RT2 に替えた後、RT1 を再提示し、続けて RT2 でリフレッシュする（Keycloak 26.8.0、Revoke Refresh Token ON、refreshTokenMaxReuse 0）
- 記録（2026-11-23、`research/runtime/keycloak-observations-2026-11-23.md` の 2.）：RT1 は `invalid_grant: Maximum allowed refresh token reuse exceeded` で拒否された。続く RT2 も `invalid_grant: Session doesn't have required client` で拒否された。独立点検（PR #48）の再現では、順番を逆にしても（攻撃者が先に RT1 を使い、正規の利用者が RT1 を再提示する）攻撃者の RT2 が失効した。ただし、消えたのは **クライアントのセッション** で、利用者の SSO のセッションは残った
- 読み方：観測は Keycloak 26.8.0 のこの設定（`revokeRefreshToken: true`・`refreshTokenMaxReuse: 0`。`tools/runtime_tests/kc.py`）に依存する。BFF のセッションは終わるが、SSO のセッションは続く。また refreshTokenMaxReuse 0 では、BFF が同じ RT で並行してリフレッシュするだけで正規の利用者がログアウトする（BFF のリフレッシュは直列にする。`筆者の提案：Keycloak の RT のローテーションでは BFF のリフレッシュを利用者ごとに直列にする（追跡 #8）`、`template:modules/M_idp_keycloak#refresh-token-settings`）。シナリオ A の台帳は `reuse_detection: unverified` のままで、要件 `p08-rotation.R3` は未着手のまま。値を直すかは記入例の担当（#16・#3）が決める

<a id="exchange-lifetime"></a>

## 7. 交換で出たトークンの寿命（exchange-narrowing）

- 手順：レルム corp で carol の AT を取り、3 秒後に mcp-tools が交換する（ケーススタディと同じ 5 通り）
- 記録（2026-11-23、`research/runtime/keycloak-observations-2026-11-23.md` の 1.）：交換で出た AT の exp は、元の AT の exp より約 3 秒後だった（交換の時刻から 300 秒）。独立点検（PR #48）の再現では、寿命 20 秒のレルムで 15 秒後に交換すると +16 秒、元が期限切れになった後の交換は 400 だった。**Keycloak 26.8.0 の標準の交換（V2）は、新しいトークンの寿命を元のトークンの exp で抑えない。1 回の交換で延びるのは元の残りの寿命までで、上限はおよそ寿命 1 本分（300 秒）**。検査（`narrowing.py`）は「exp extended」と指摘する
- 読み方：L16 の「寿命が上流より長い」に当たる。RFC 8693 は exp を元で抑えることを求めていないので、Keycloak の不具合ではなく、設計で扱うこと。交換を重ねる構成では、ホップの数だけ延びうる（試していない）。シナリオ B の H15 は sts が寿命を 300 秒以下に抑えると宣言している。交換を Keycloak に替えるなら、受け手が `exp` と元の `exp` を比べるか、交換の寿命を短くするかを設計に書く

## 8. テストの環境で設計と違えたこと

| 点 | 設計（シナリオ A） | テストの環境 | 理由 |
| --- | --- | --- | --- |
| ログイン | 認可コード＋PKCE（Direct Access Grants は OFF） | saas-web の Direct Access Grants を ON にし、パスワードで取る | ブラウザなしで繰り返すため。発行されるトークンの中身（マッパー・スコープ・寿命）は同じクライアントの設定で決まる |
| 発行者の URL | `https://idp.example.com/realms/<t>` | `http://localhost:38080/realms/<t>` | 手元のコンテナ。受け手は台帳の値を読み替えてから完全一致で比べる |
| AT の寿命・時計のずれ | 300 秒・30 秒 | 20 秒・2 秒（寿命と失効のテストの間だけ） | 2. |
| 接続プール | プールの設定による | psycopg の 1 本の接続を使い回す | 接続の使い回しで文脈が残るかを見るのに 1 本で足りる。PgBouncer は試していない |
