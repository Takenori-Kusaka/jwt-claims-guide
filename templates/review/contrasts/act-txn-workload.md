<!-- template_version: 0.4.0 -->
# 対比表：`act` と Txn-Token とワークロード認証

1 つのリクエストには「誰の権限で」「誰が代理して実行しているか」「どの取引か」「直接の通信相手は誰か」の 4 つの問いが重なります（slide:p05-one-request-carries）。この 3 つの仕組みは、それぞれ別の問いに答えます。1 つで別の問いに答えさせる設計は、問いの取り違え（指摘の種別「目的と仕組みの不一致」）です。

- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施

<a id="question"></a>

## 1. 解く問い

| 仕組み | 解く問い（`templates/registry/questions.yaml` の ID） | 解かない問い |
| --- | --- | --- |
| `act`（RFC 8693 §4.1） | 誰が代理して実行しているか（`q-actor`）。最も外側の `act` が今の行為者 | 誰の権限か（それは `sub`）、直接の通信相手は誰か |
| Txn-Token（draft-ietf-oauth-transaction-tokens-11） | どの取引の文脈か（`q-txn`）。どのワークロードが Txn-Token を求めたか（`q-req-wl`） | 誰が代理しているか、直接の通信相手は誰か |
| ワークロード認証（mTLS・SPIFFE） | 直接の通信相手は誰か（`q-peer`） | 誰の権限か、どの取引か |

根拠：slide:p05-one-request-carries、slide:p10-four-questions、templates/registry/questions.yaml

<a id="unit"></a>

## 2. 仕様上の単位

| 仕組み | 単位 | 書き手 | 照合する者 |
| --- | --- | --- | --- |
| `act` | トークン交換（RFC 8693）で出たトークンの中の、JSON のオブジェクト（`sub` などを持つ）。入れ子の `act` は過去の行為者 | 交換を受けた AS | 受け手。アクセス制御には最も外側の `act` だけを使う |
| Txn-Token | 信頼の領域（trust domain）の中の、1 つの呼び出しの連鎖に付く短命の署名つき JWT。必須（REQUIRED）は `iat`・`aud`・`exp`・`txn`・`sub`・`scope`・`req_wl`（Txn-Token を求めたワークロード）。`tctx`（取引の内容）と `rctx`（`req_ip`・`authn` など要求時点の環境）は推奨（RECOMMENDED） | Transaction Token Service（TTS）だけ | 受け手。`tctx` の照合は受け手が行う（仕様は照合の規則を書かない） |
| ワークロード認証 | 通信の層（TLS のクライアント証明書・SPIFFE の SVID）。トークンのクレームではない | 証明書の発行者（CA・SPIRE） | 接続を受けた側（TLS の終端） |

根拠：RFC 8693 §4.1、draft-ietf-oauth-transaction-tokens-11 §9.2、RFC 8705 §2、slide:p06-transaction-tokens

<a id="table"></a>

## 3. 対比

| 観点 | `act` | Txn-Token | ワークロード認証 |
| --- | --- | --- | --- |
| 寿命 | 交換で出たトークンの寿命に従う | 分以下（草案）。元のトークンより長くてよい（縮小の規則はない） | 証明書の寿命（SPIFFE の SVID は短命が普通） |
| 縮小 | 保証しない（入れ子にしても範囲は狭まらない） | `scope` は元と同じかそれ以下。判別できなければ拒否 | — |
| 運び方 | トークンの中（Authorization ヘッダー） | 専用の `Txn-Token` ヘッダー。アクセストークンとして送らない | TLS の接続そのもの。入口で終端するなら、証明書を渡すヘッダーを入口だけが書ける |
| 途中での書き換え | 交換のたびに AS が作り直す | 受け取ったまま（unmodified）下流に渡す（§12.2 の MUST）。したがって `req_wl` も伝搬の途中では変わらない（`req_wl` を名指しした規定ではなく、そこから導いた帰結）。作り直し（Txn-Token を subject token にした再発行）は §13.15 が定める：範囲を狭める・値を足す・寿命を延ばすのは MAY（延ばすなら回数を制限する SHOULD）、範囲を広げる・`txn`・`sub`・`aud` を変える・期限切れを作り直すのは MUST NOT、Call Chain を引き継ぐのは MUST。仕様が定めていないのは、Call Chain の引き継ぎ方と、作り直しで `req_wl` を変えてよいか（P5 の表） | 接続ごと |
| 監査に残すもの | 今の行為者と、連鎖（入れ子） | `txn`（同じ取引の相関） | 接続相手の ID |

根拠：RFC 8693 §4.1・§5、draft-ietf-oauth-transaction-tokens-11 §6・§12.1・§12.2・§13.15、slide:p06-narrow-downstream、template:profiles/P5_internal_propagation#txn-token

<a id="not-covered"></a>

## 4. 扱わないこと（仕様が決めていないこと）

- **RFC 8693 の交換は、範囲を狭めることを求めない。** `act` のネストも縮小を保証しない。「下流は aud・scope・寿命で上流を超えない」は組織の規則として書き、交換のサービスで強制する（slide:p06-narrow-downstream。実測では Keycloak 26.8 の交換で、元に無い宛先のトークンが出た：slide:p10-token-exchange-not-narrowing）
- **Txn-Token の寿命は、元のトークンより長くてよい。** 寿命の縮小は、ホップの表の例外（`narrowing_exception`）として理由を書く
- **委任の深さの上限と、根元からの一括失効は標準にない。** 組織の規則として台帳に書き、深さが 2 以上なら専門家に回す（`review:escalation#delegation-depth`）
- **`tctx` の照合の規則は仕様にない。** 照合は受け手が行い、照合する項目を台帳の `enforced_at`・`value_vocabulary` に書く（`lint:L11`）
- この表は、利用者の認証の強さ（`acr`）と承認（`authorization_details`・承認 ID）を扱わない。承認は [scope-vs-role.md](scope-vs-role.md)

根拠：slide:p06-narrow-downstream、slide:p10-delegation-chain-depth、slide:p10-token-exchange-not-narrowing

<a id="misuse"></a>

## 5. 典型的な誤用

| # | 誤用 | 起きること | 見つける問い |
| --- | --- | --- | --- |
| m-1 | `act` で「どの取引か」を表す・Txn-Token で「誰が代理しているか」を表す | 監査で代理と取引が区別できない。照合の対象を取り違える | `q-agent-delegation-claims`・`q-audit-correlation` |
| m-2 | 入れ子の `act`（過去の行為者）をアクセス制御に使う | 過去の行為者の権限で今の操作を許す（RFC 8693 §4.1 が禁じる） | `q-agent-delegation-claims` |
| m-3 | `req_wl` を直接の通信相手とみなす | 途中のワークロードのなりすましを見逃す。直接の相手は mTLS・SPIFFE で確かめる | `q-authorize-service-and-user` |
| m-4 | `sub` だけを見て、エージェント・別サービス経由の操作を本人の操作として扱う | 誰が実行したか分からない | `q-agent-own-identity`・`ap-2-7`・`q-operator-act` |
| m-5 | 交換や `act` のネストで権限が自動で狭まると考える | 交換で宛先・範囲が広がる | `q-hop-narrowing`・`q-no-passthrough` |
| m-6 | Txn-Token の `tctx` を書いたが、受け手が照合しない | 取引の内容を途中で差し替えられる | `q-txn-scope-fixed` |
| m-7 | Txn-Token をアクセストークンとして送る・受ける | 外部向けの検証で内部の文脈を受け入れる | `cf-06` |
| m-8 | `rctx`（要求時点の環境の値）を、TTS が決めた認可の詳細（`tctx`）と同じ重さで使う | 申告の値で認可する | `q-txn-scope-fixed`・`q-writer-distinguished` |
| m-9 | 内部の代理トークンを、署名・期限・失効・ログなしで作る | CVE-2025-55241 の条件がそろう | `ap-2-9`・`q-internal-delegation-token` |
| m-10 | 「どこを経由したか」を `act` の連鎖で表す | 経路は証跡（ログ・トレース）の問いで、`act` は行為者だけを表す | `q-audit-correlation`・`q-trace-id-trust` |
| m-11 | 利用者の権限で下流を呼ぶべき処理を、仲介サービスの広い権限で呼ぶ | 代理の混乱 | `q-original-principal` |

根拠：RFC 8693 §4.1、draft-ietf-oauth-transaction-tokens-11 §12.2、slide:p05-one-request-carries、slide:p05-confused-deputy、slide:p04-split-by-writer、slide:p02-delegation-client
<!-- req:p02-delegation-client.R1 req:p02-delegation-client.R5 req:p04-split-by-writer.R4 req:p05-one-request-carries.R1 req:p05-one-request-carries.R6 req:p05-one-request-carries.R7 req:p05-confused-deputy.R1 req:p06-narrow-downstream.R6 req:p10-four-questions.R2 -->

<a id="evidence"></a>

## 6. 根拠

- RFC 8693 §4.1（`act`、今の行為者と入れ子の扱い）・§4.4（`may_act`）・§5（セキュリティの考慮。縮小は求めない）
- draft-ietf-oauth-transaction-tokens-11 §6（寿命）・§9.2（クレーム）・§12.1（`Txn-Token` ヘッダー）・§12.2（受け取ったまま渡す）・§13.15（作り直しの規則）
- RFC 8705 §2（mTLS のクライアント認証）
- ガイド：slide:p05-one-request-carries、slide:p06-transaction-tokens、slide:p06-narrow-downstream、slide:p10-token-exchange-not-narrowing

根拠：RFC 8693 §4.1、draft-ietf-oauth-transaction-tokens-11 §9.2、RFC 8705 §2、slide:p05-one-request-carries
