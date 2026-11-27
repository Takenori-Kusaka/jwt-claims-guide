<!-- template_version: 0.4.0 -->
# 送信者制約（modules/M_sender_constraint）

> テンプレートです。候補と検討の問いだけを載せ、採否の理由の見本は載せません（理由の写し書きを防ぐため。#4 の方針）。判断は台帳（claims.yaml など）に 1 回だけ書き、ここからは ID で参照します。

- 使う場面：AT・RT を「持つべき者」に束縛するか（盗まれたトークンを別の端末から再送されても使えないようにするか）を決めるとき。`00_core.md` の「発行方式の選択」（`template:00_core#issuance-profile`）の `sender_constraint` の答えを、このモジュールで検討する
- 組み合わせ：P1（ブラウザの中のクライアント）、P4（エージェントの実行基盤のタスクのトークン）、P5（入口で TLS を終端する構成）
- Lite での扱い：〔Full：記入／Lite：参照〕。Lite で既定の組み合わせ（BFF＋送信者制約なし）から外れて DPoP・mTLS を選んだら、`00_core.md` の「既定から外れた点」に書き、台帳の行（下の 5.）を足す
- 問いの位置づけ：送信者制約は「誰が持つべきか」（`templates/registry/questions.yaml` の q-holder）に答えます。「直接の通信相手は誰か」（q-peer、mTLS・ワークロードの ID）とは別の問いです
- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施。

<a id="dpop-vs-mtls"></a>
## 1. DPoP と mTLS の選び方〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_sender_constraint#dpop-vs-mtls`
<!-- req:p02-keys-events-identity-assurance.R2 req:p10-four-questions.R5 -->

決めること：トークンを持つべき者を、アプリケーションの層の署名（DPoP）で示させるか、TLS のクライアント証明書（mTLS）で示させるか、束縛しないか。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 束縛するか | 漏れたトークンを別の端末から再送されたとき、何が起きるか。許せるか | 束縛しない（none）／DPoP／mTLS | RFC 9700 §2.2.1、slide:p10-four-questions、jwt-claims-casestudy@080b8da:B23 |
| 鍵の置き場所 | クライアントは鍵をどこに持てるか（ブラウザ・エージェントの実行基盤・サーバー） | アプリが持つ鍵（DPoP）／TLS の証明書と鍵（mTLS） | RFC 9449 §1、RFC 8705 §1 |
| 経路の TLS | クライアントから受け手まで TLS が途切れずに届くか。途中で終端するか | 端から端まで／入口で終端（2.） | RFC 8705 §6.5 |
| 受け手の照合 | AT の受け手すべてが、証明（DPoP の proof・TLS の相手の証明書）と `cnf` を照合できるか | 全受け手が照合する／入口だけが照合する | RFC 9449 §4.3・§7、RFC 8705 §3 |
| 束縛の表し方 | AT に何を載せるか | `cnf.jkt`（DPoP。RFC 9449 §6.1）／`cnf.x5t#S256`（mTLS。RFC 8705 §3.1） | RFC 9449 §6.1、RFC 8705 §3.1、RFC 7800 §3.1 |
| 準拠の要求 | FAPI 2.0 などの要求で、送信者制約が必須か | 必須（FAPI 2.0 は DPoP か mTLS）／任意 | FAPI 2.0 Security Profile（Final）§5.3.2.1 |
| 費用 | 要求ごとの proof の作成・検証、サイズの増分を許せるか | 実測で確かめる | jwt-claims-casestudy@080b8da:B23 |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 束縛するか・方式 |  |  | `issuance_profile.sender_constraint`、`token_types[].sender_constraint` |
| 束縛するトークン |  |  | `token_types[]`（AT・RT の行） |
| 照合する受け手 |  |  | `claims[].enforced_at`（cnf の行） |

根拠：RFC 9700 §2.2.1、RFC 9449 §6.1、RFC 8705 §3.1、FAPI 2.0 Security Profile（Final）§5.3.2.1、templates/registry/issuance_effects.yaml の E-dpop

<a id="tls-termination"></a>
## 2. 入口で TLS を終端するときの証明書の渡し方〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_sender_constraint#tls-termination`

決めること：mTLS を選び、入口（ロードバランサー・ゲートウェイ）で TLS を終端するとき、クライアントの証明書（または拇印）を下流へどう渡し、誰がそれを信じてよいか。RFC 8705 §6.5 は入口で終端してよいことを述べますが、証明書の情報を下流へ安全に渡す方法は範囲外としています。そのため組織の規則として決めます。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 終端の場所 | TLS をどこで終端するか | 入口（at_entry）／端から端まで（end_to_end） | RFC 8705 §6.5、`issuance_profile.tls_termination` |
| 渡すヘッダー | 証明書をどの名前のヘッダーで渡すか | 製品のヘッダー（Envoy の `x-forwarded-client-cert` など）／組織で決めた名前 | RFC 8705 §6.5、slide:p06-header-forwarding |
| 同名のヘッダー | クライアントが送ってきた同名のヘッダー（大文字小文字・アンダースコアの変種・重複を含む）を、入口で捨てるか | 捨てる | slide:p06-header-forwarding、jwt-claims-casestudy@080b8da:B5 |
| 書ける者 | そのヘッダーを書けるのは入口だけ、という信頼境界をどう保つか | 入口からの接続だけを受ける（mTLS・ネットワーク）／下流が入口を確かめる | slide:p06-header-forwarding、筆者の提案：証明書を渡すヘッダーは入口だけが書く（追跡 #4） |
| 照合する者 | `cnf.x5t#S256` と証明書を照合するのは、入口か下流か | 入口／下流（渡されたヘッダーで） | RFC 8705 §3 |

記入欄：

| 決めること | 決めたこと（書き手が書く） | 理由（書き手が書く） | 台帳の ID |
| --- | --- | --- | --- |
| 終端の場所 |  |  | `issuance_profile.tls_termination` |
| 渡すヘッダー・同名を捨てる・書ける者 |  |  | `issuance_profile.forwarded_cert_header`（`name`・`strip_inbound`・`written_only_by`） |

根拠：RFC 8705 §6.5、slide:p06-header-forwarding、templates/registry/issuance_effects.yaml の E-mtls-entry、筆者の提案：証明書を渡すヘッダーは入口だけが書く（追跡 #4）

<a id="dpop-nonce-jti"></a>
## 3. DPoP の nonce と、使い回した proof の拒否〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_sender_constraint#dpop-nonce-jti`
<!-- req:p01-client-made-jwts.R2 -->

決めること：DPoP を選んだとき、受け手が proof のどこを照合し、同じ proof の再送をどう拒むか。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 照合する項目 | 受け手は proof の `typ`（dpop+jwt）・`alg`・署名・`htm`・`htu`・`iat`、AT と一緒なら `ath`、`cnf.jkt` との一致を確かめるか | RFC 9449 §4.3 の手順どおり | RFC 9449 §4.3、slide:p01-client-made-jwts |
| `jti` の再送 | 受け手は proof の `jti` を覚えて、同じ `jti` を拒むか。覚えておく期間は | `iat` の許容の窓のあいだ覚える／覚えない（nonce に頼る） | RFC 9449 §11.1、`token_types[].jti_policy` |
| `iat` の窓 | proof の `iat` を、現在時刻からどれだけのずれまで受け入れるか | 秒数を決める | RFC 9449 §4.3・§11.1 |
| AS の nonce | AS が `DPoP-Nonce` を返し、proof に `nonce` を入れさせるか | 使う（§8）／使わない | RFC 9449 §8 |
| 受け手の nonce | リソースサーバーが `DPoP-Nonce` を返すか | 使う（§9）／使わない | RFC 9449 §9 |
| 複数の受け手 | 受け手が複数のインスタンスにまたがるとき、`jti` の記録と nonce をどう共有するか | 共有の保存先／インスタンスごと（再送の窓が開く） | RFC 9449 §11.1 |

記入欄：

| 決めること | 決めたこと（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 照合する項目 |  |  | `claims[].enforced_at`（cnf の行。htm・htu・iat・jti・ath） |
| `jti` の再送・`iat` の窓 |  |  | `token_types[].jti_policy`（DPOP の行） |
| nonce |  |  | `token_types[].note`（DPOP の行） |

根拠：RFC 9449 §4.3・§8・§9・§11.1、templates/registry/issuance_effects.yaml の E-dpop

<a id="rt-rotation"></a>
## 4. RT のローテーションとの関係〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_sender_constraint#rt-rotation`
<!-- req:p08-rotation.R1 req:p08-rotation.R2 -->

決めること：RT を送信者制約で守るか、ローテーションで守るか。RFC 9700 は、公開クライアントの RT を送信者制約にするかローテーションすることを求め、FAPI 2.0 は送信者制約のある機密クライアントでは AS がローテーションしないとしています（前提が違う）。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| クライアントの種類 | RT を受け取るのは公開クライアントか、機密クライアントか、FAPI の対象か | 公開／機密／FAPI | RFC 9700 §2.2.2、slide:p08-rotation |
| 公開クライアントの RT | 送信者制約で守るか、ローテーション＋再利用の検知で守るか | DPoP で RT を束縛（RFC 9449 §5）／ローテーション＋再利用の検知 | RFC 9700 §4.14.2、RFC 9449 §5 |
| FAPI の対象 | 送信者制約のある機密クライアントで、ローテーションを止めるか | ローテーションしない（例外を除く） | FAPI 2.0 Security Profile（Final）§5.3.2.1 |
| MCP の AS | MCP の公開クライアントに RT を出す AS は、ローテーションするか | ローテーションする（MCP の仕様は MUST） | MCP Authorization Security Considerations（2026-07-28）「Token Theft」 |
| 再利用の検知 | 無効にした RT が来たら、RT の系列全体を失効させるか。試験で確かめたか | 失効させる（確かめた）／確かめていない | slide:p08-rotation、RFC 9700 §4.14.2 |
| 証明書・鍵の更新 | 証明書・DPoP の鍵を更新したとき、束縛した AT と RT はどうなるか。証明書の寿命と RT の寿命の関係は。更新のたびに利用者の再同意が一斉に要らないか（#63 で足した。パイロット #9 の O9） | AT は更新の後に取り直す（RFC 8705 §6.3）／機密クライアントの RT はクライアントの認証に結び、証明書・鍵の更新で使えなくしない／公開クライアントの RT は証明書・鍵に結ぶので、更新で取り直しになる | RFC 8705 §4・§6.3、RFC 9449 §5 |

記入欄：

| 決めること | 決めたこと（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| RT の守り方 |  |  | `issuance_profile.rt_strategy`、`token_types[].rt_rotation`・`sender_constraint`（RT の行） |
| 証明書・鍵の更新 |  |  | `token_types[].sender_constraint`・`max_lifetime`（AT・RT の行）、`claims[].enforced_at`（cnf の行） |

根拠：RFC 9700 §4.14.2、RFC 9449 §5、FAPI 2.0 Security Profile（Final）§5.3.2.1、slide:p08-rotation、RFC 8705 §4・§6.3

<a id="registry-effects"></a>
## 5. 選択で台帳・目録がどう変わるか

項目 ID：`template:modules/M_sender_constraint#registry-effects`

`issuance_profile.sender_constraint` の値ごとに、台帳で必要になるものは `templates/registry/issuance_effects.yaml` に定義してあります（#6 の L62 が検査し、`claim_lint render` の「発行方式の選択」の節が満たしている行を表示する）。選んだら、次の行を足すか直します。

| 選択 | 台帳（claims.yaml） | トークン目録（token_types.yaml） | 発行方式の選択 |
| --- | --- | --- | --- |
| none | `cnf` の行は却下（または行なし） | DPoP proof（kind: dpop_proof）の行は却下＋理由。AT の `transport` は `authorization_bearer` | 公開クライアントなら RT のローテーション＋再利用の検知（E-public-no-sender-constraint） |
| dpop | `cnf`（`cnf.jkt`）の行を採用し、`carried_in` に AT。受け手すべての `enforced_at` に htm・htu・iat・jti・ath（E-dpop.1・E-dpop.2）。`max_bytes` を R8 のサイズに入れる（E-dpop.4） | DPoP proof の行を採用（`typ: dpop+jwt`、`jti_policy`。E-dpop.3）。AT の `transport` は `authorization_dpop`（E-dpop.5）、`sender_constraint: dpop` | `rt_strategy` に sender_constrained を選べる（E-rt-sender-constrained） |
| mtls | `cnf`（`cnf.x5t#S256`）の行を採用し、受け手の `enforced_at` に証明書の拇印との照合（E-mtls.1・E-mtls.2） | AT の `sender_constraint: mtls` | `tls_termination`（E-mtls.3）。入口で終端なら `forwarded_cert_header`（E-mtls-entry） |

記入欄：

| 選択 | 足した・直した行（書き手が書く） | 理由（書き手が書く） |
| --- | --- | --- |
|  |  |  |

根拠：templates/registry/issuance_effects.yaml の E-dpop、templates/registry/README.md の 7.、RFC 9449 §6.1、RFC 8705 §3.1
