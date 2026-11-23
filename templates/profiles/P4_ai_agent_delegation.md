<!-- template_version: 0.3.0 -->
# P4 AI エージェントの委任（profiles/P4_ai_agent_delegation）

> テンプレートです。候補と検討の問いだけを載せ、採否の理由の見本は載せません（理由の写し書きを防ぐため。#4 の方針）。判断は台帳（claims.yaml など）に 1 回だけ書き、ここからは ID で参照します。

- 使う場面：AI エージェントが利用者の代理で、または自分の権限で、ツール（MCP サーバーなど）や API を呼ぶ境界。`00_core.md` の「範囲と信頼の境界」で、エージェントの実行基盤・ツールサーバー・上流の API の境界に P4 を書く
- 組み合わせ：利用者のログインは P1、組織の内側の伝搬（Txn-Token・サービス間）は P5。送信者制約は `template:modules/M_sender_constraint`、承認の内容の照合は `template:modules/M_authz_pdp`
- Lite での扱い：委任・トークン交換がある設計は、#4 の判定（5 問）で Full になります。MCP の必須チェック表（1.）だけは〔Lite・Full：記入〕で、MCP を使うなら必ず確かめます。ほかは〔Full：記入／Lite：参照〕
- 問いの区別：「誰の権限で」（`sub`）、「誰が代理して実行しているか」（`act`）、「どの取引か」（Txn-Token の `txn`）、「直接の通信相手は誰か」（mTLS・ワークロードの ID）は別々の問いです。`00_core.md` の「問い × 仕組み」で別々の行に書きます（`templates/registry/questions.yaml` の q-sub・q-actor・q-txn・q-peer）
- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施。

<a id="mcp-checklist"></a>
## 1. MCP の認可の必須チェック表〔Lite・Full：記入〕

項目 ID：`template:profiles/P4_ai_agent_delegation#mcp-checklist`
<!-- req:p10-mcp-authorization.R1 req:p10-mcp-authorization.R2 req:p10-mcp-authorization.R4 req:p10-mcp-authorization.R5 req:p10-mcp-authorization.R6 req:p08-rotation.R6 -->

決めること：MCP の認可の仕様（2026-07-28 版。2026-11-23 に確認）が MUST とする事項を、自分の構成で誰が・どう確かめるか。仕様の要求なので、採否ではなく「確かめ方」と「確かめた結果」を書きます。HTTP 以外の運び方（STDIO）では、この仕様に従わず環境から資格情報を得る、と仕様は述べています（「Protocol Requirements」）。

| # | 必須の確認 | 担う部品 | 仕様の強さ | 根拠 |
| --- | --- | --- | --- | --- |
| 1 | 認可要求とトークン要求の両方に `resource`（MCP サーバーの正規の URI）を入れる。AS が対応していなくても送る | MCP クライアント | MUST | MCP Authorization（2026-07-28）「Resource Parameter Implementation」、RFC 8707 §2 |
| 2 | MCP サーバーは、自分を宛先として発行されたトークンだけを受け入れ、ほかのトークンを受け入れも中継もしない | MCP サーバー | MUST | MCP Authorization（2026-07-28）「Token Handling」、RFC 8707 §2 |
| 3 | 上流の API には、上流の AS が発行した別のトークンを使い、受け取ったトークンを渡さない（パススルーの禁止） | MCP サーバー | MUST NOT（渡すこと） | MCP Authorization Security Considerations（2026-07-28）「Access Token Privilege Restriction」 |
| 4 | 固定のクライアント ID を使うプロキシは、動的に登録されたクライアントごとに利用者の同意を取ってから、第三者の AS へ転送する | MCP のプロキシ | MUST | MCP Authorization Security Considerations（2026-07-28）「Confused Deputy Problem」 |
| 5 | 認可応答の `iss` を、記録した発行者と単純な文字列比較で照合する（AS が対応を宣言し、`iss` が無ければ拒否） | MCP クライアント | MUST（RFC 9207 §2.4 の照合） | MCP Authorization（2026-07-28）「Authorization Response Validation」、RFC 9207 §2.4 |
| 6 | PKCE を使い、可能なら `S256` を使う。AS のメタデータに `code_challenge_methods_supported` が無ければ進まない | MCP クライアント | MUST | MCP Authorization Security Considerations（2026-07-28）「Authorization Code Protection」 |
| 7 | 公開クライアントの RT を、AS がローテーションする | AS | MUST | MCP Authorization Security Considerations（2026-07-28）「Token Theft」、slide:p08-rotation |
| 8 | AT はすべての要求の Authorization ヘッダーで送り、URI のクエリに入れない | MCP クライアント | MUST・MUST NOT | MCP Authorization（2026-07-28）「Token Requirements」 |
| 9 | MCP サーバーは Protected Resource Metadata（RFC 9728）を公開する | MCP サーバー | MUST | MCP Authorization（2026-07-28）「Overview」、RFC 9728 §3 |

記入欄（MCP を使う設計では Lite でも書く）：

| # | 確かめ方（書き手が書く） | 確かめた結果（書き手が書く） | 台帳・目録・試験の ID |
| --- | --- | --- | --- |
| 1 |  |  | `hops[].aud`、`issuance_profile.request_protection`（resource_indicators） |
| 2 |  |  | `token_types[].aud`、`claims[].enforced_at`（aud の行） |
| 3 |  |  | `hops[].exchanger`（ツールから上流へのホップ） |
| 4 |  |  |  |
| 5 |  |  |  |
| 6 |  |  | `issuance_profile.grants`（authorization_code_pkce） |
| 7 |  |  | `token_types[].rt_rotation`、`issuance_profile.rt_strategy` |
| 8 |  |  | `token_types[].transport` |
| 9 |  |  |  |

根拠：MCP Authorization（2026-07-28）「Resource Parameter Implementation」、MCP Authorization Security Considerations（2026-07-28）「Access Token Privilege Restriction」、RFC 8707 §2、RFC 9207 §2.4、slide:p10-mcp-authorization

<a id="agent-identity"></a>
## 2. エージェントの ID〔Full：記入／Lite：参照〕

項目 ID：`template:profiles/P4_ai_agent_delegation#agent-identity`
<!-- req:p10-agent-identity.R1 -->

決めること：エージェントを独立した主体として登録するか。共有のアカウントや、利用者のトークンをそのまま使う形にしないこと。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 登録 | エージェント（とその実行基盤）を、どの ID で表すか | AS のクライアント（`client_id`）／ワークロードの ID（SPIFFE ID など）／両方 | slide:p10-agent-identity、CoSAI Agentic IAM v1.0 §1.2 |
| 共有の禁止 | 複数のエージェントやタスクが同じ資格情報を使っていないか | エージェントごと／タスクごと／共有（避ける） | slide:p10-agent-identity |
| 利用者のトークンの借用 | エージェントが利用者のトークン（`act` なし）を使う経路が残っていないか | 経路なし／ある（なりすましと区別できない） | RFC 8693 §1.1、jwt-claims-casestudy@080b8da:C12 |
| 認証の手段 | エージェントの実行基盤は AS にどう自分を証明するか | private_key_jwt／mTLS／ワークロードの ID のトークン | RFC 7523 §2.2、RFC 8705 §2 |

記入欄：

| 観点 | 決めたこと（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 登録 |  |  | `claims[]`（client_id・act の行） |
| 認証の手段 |  |  | `issuance_profile.client_auth` |

根拠：slide:p10-agent-identity、RFC 8693 §1.1、CoSAI Agentic IAM v1.0 §1.2

<a id="delegation-mode"></a>
## 3. 自律・委任・なりすましの型〔Full：記入／Lite：参照〕

項目 ID：`template:profiles/P4_ai_agent_delegation#delegation-mode`
<!-- req:p10-agent-identity.R2 req:p10-agent-identity.R4 -->

決めること：エージェントの操作ごとに、エージェント自身の権限で動くか、利用者の代理で動くかと、それぞれのクレームの表し方。

| 型 | 検討の問い | クレームの表し方（仕様とガイドの形） | 根拠 |
| --- | --- | --- | --- |
| 自律（エージェント自身の権限） | 利用者がいない操作か（定期の集計など） | `sub`＝エージェント。client credentials など | slide:p10-agent-identity、slide:p05-system-privileges |
| 委任（利用者の代理） | 利用者の権限の範囲で、エージェントが実行するか | `sub`＝利用者、`act.sub`・`client_id`＝エージェント | RFC 8693 §4.1、slide:p10-agent-identity |
| なりすまし | 利用者のトークンをそのまま使う形が残っていないか | 区別できない（避ける） | RFC 8693 §1.1 |
| 権限の分け方 | エージェント自身に許す範囲と、代理で許す範囲を、別々に宣言したか | 別々の scope・別々の行／同じ | slide:p10-agent-identity |

記入欄：

| 操作 | 型（書き手が書く） | 理由（書き手が書く） | 台帳の ID（`answers` に q-sub・q-actor） |
| --- | --- | --- | --- |
|  |  |  |  |

根拠：slide:p10-agent-identity、RFC 8693 §4.1、templates/registry/questions.yaml の q-actor

<a id="delegation-policy"></a>
## 4. 交換の方針（may_act と委任の理由）〔Full：記入／Lite：参照〕

項目 ID：`template:profiles/P4_ai_agent_delegation#delegation-policy`
<!-- req:p02-delegation-client.R3 req:p02-delegation-client.R4 -->

決めること：トークン交換のときに、誰が代理してよいかを誰が判定するか（`may_act`・AS の方針）と、委任の理由・承認者をどこに置くか。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 代理してよい者 | subject token の `may_act` を、交換サービスがどう評価するか | `may_act` と actor token の主体を照合する／AS の方針の表で決める／両方 | RFC 8693 §4.4、slide:p02-delegation-client |
| 評価する者 | 交換を担う部品はどれか | 組織の AS／入口の STS／ツールサーバーの AS | slide:p06-narrow-downstream、`hops[].exchanger` |
| 委任の理由・承認者 | 理由・承認者を独自に運ぶなら、どこに置くか | `act` の外の組織の名前空間（承認 ID など）／運ばない（監査ログで引く） | slide:p02-delegation-client、RFC 8693 §4.1 |
| 絞り込み | 交換で `aud`・`scope` を上流より広げないことを、どこで強制するか | AS の方針／交換を担う部品の検査／受け手の検査 | slide:p10-token-exchange-not-narrowing |

記入欄：

| 観点 | 決めたこと（書き手が書く） | 理由（書き手が書く） | 台帳の ID |
| --- | --- | --- | --- |
| 代理してよい者 |  |  | `claims[]`（may_act の行） |
| 評価する者 |  |  | `hops[].exchanger` |
| 委任の理由・承認者 |  |  | `claims[]`（承認 ID の行） |

根拠：RFC 8693 §4.4、slide:p02-delegation-client、slide:p10-token-exchange-not-narrowing

<a id="human-approval"></a>
## 5. 人の承認〔Full：記入／Lite：参照〕

項目 ID：`template:profiles/P4_ai_agent_delegation#human-approval`
<!-- req:p06-step-up-approval.R4 req:p10-human-approval-evidence.R1 req:p10-human-approval-evidence.R5 -->

決めること：承認が要る操作で、承認の有無を誰が確かめるか（エージェントに判断させない）と、承認の内容をどう運び、受け手が何と照合するか。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 承認を確かめる者 | 承認したかどうかを、AS が本人に確かめるか | CIBA（別の端末で本人に確かめる）／認可コードの同意画面／エージェントの申告（避ける） | slide:p10-human-approval-evidence、OpenID Connect Client-Initiated Backchannel Authentication Flow - Core 1.0 §7.1 |
| 本人に見せる内容 | CIBA の `binding_message` に何を出すか。結果をどう受け取るか | `binding_message` に金額・相手先／poll・ping・push の受け取り方 | OpenID Connect Client-Initiated Backchannel Authentication Flow - Core 1.0 §7.1・§5 |
| 承認の内容 | 承認した対象・金額・相手先をトークンに載せるか | `authorization_details`（`identifier` に対象、`locations` にリソースサーバー）／承認 ID だけ（中身は受け手が引く） | RFC 9396 §2・§2.2、slide:p10-human-approval-evidence |
| 宛先ごとの絞り込み | `authorization_details` を宛先に合わせて絞るか | 宛先ごとに絞る／全部を載せる | RFC 9396 §9.1 |
| 受け手の照合 | 受け手が、要求の内容（金額・相手先・対象）と承認の内容を照合するか | 照合する（不一致は拒否）／照合しない | jwt-claims-casestudy@080b8da:C5、slide:p10-human-approval-evidence |

記入欄：

| 観点 | 決めたこと（書き手が書く） | 理由（書き手が書く） | 台帳の ID |
| --- | --- | --- | --- |
| 承認を確かめる者 |  |  | `issuance_profile.grants`（ciba） |
| 承認の内容 |  |  | `claims[]`（authorization_details・承認 ID の行） |
| 受け手の照合 |  |  | `claims[].enforced_at` |

根拠：slide:p10-human-approval-evidence、RFC 9396 §2.2、OpenID Connect Client-Initiated Backchannel Authentication Flow - Core 1.0 §7.1

<a id="tool-scopes"></a>
## 6. ツールごとのスコープと引き上げ〔Full：記入／Lite：参照〕

項目 ID：`template:profiles/P4_ai_agent_delegation#tool-scopes`
<!-- req:p10-per-tool-scopes.R2 -->

決めること：ツールごとの最小のスコープと、足りないときの引き上げ方。トークンをタスク単位で作り直すか。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 最初のスコープ | ツールの基本の操作だけのスコープで始めるか | 基本だけ／タスクに要る全部 | slide:p10-per-tool-scopes、MCP Authorization（2026-07-28）「Scope Selection Strategy」 |
| 不足の知らせ方 | 足りないとき、サーバーは何を返すか | 403 と `WWW-Authenticate` の `error="insufficient_scope"`・`scope` | MCP Authorization（2026-07-28）「Scope Challenge Handling」、RFC 6750 §3.1 |
| 引き上げ | クライアントは、前のスコープとの和で取り直すか | 和で取り直す／必要なものだけ | MCP Authorization（2026-07-28）「Step-Up Authorization Flow」 |
| ワイルドカード | ワイルドカードのスコープを許すか | 許さない／許す | NIST IR 8587 §5.3.1.6、slide:p10-per-tool-scopes |
| タスク単位 | タスクごとに、宛先 1 つ・分単位・RT なしのトークンを作り直すか | 作り直す／同じトークンを使い続ける | slide:p10-per-tool-scopes、jwt-claims-casestudy@080b8da:C14 |

記入欄：

| ツール | 最初のスコープ（書き手が書く） | 引き上げの方針（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
|  |  |  | `claims[]`（scope の行）、`token_types[].max_lifetime` |

根拠：slide:p10-per-tool-scopes、MCP Authorization（2026-07-28）「Scope Challenge Handling」、NIST IR 8587 §5.3.1.6

<a id="delegation-depth"></a>
## 7. 委任の連鎖の深さ〔Full：記入／Lite：参照〕

項目 ID：`template:profiles/P4_ai_agent_delegation#delegation-depth`

決めること：`act` の入れ子の深さの上限と、それを強制する場所。RFC 8693 は入れ子の `act` を記録の情報とし、深さの上限も縮小も定めていません。上限は組織の規則として決めます。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 上限 | 何段までの委任を許すか | 組織の規則で決めた段数 | slide:p10-delegation-chain-depth、CoSAI Agentic IAM v1.0 §3.4 |
| 強制する場所 | 交換のときに拒むか、受け手が拒むか | 交換を担う部品／受け手／両方 | slide:p10-delegation-chain-depth、jwt-claims-casestudy@080b8da:C10 |
| 認可に使う act | 認可の判断に使うのは、最も外側の `act`（今の行為者）だけか | 最も外側だけ（内側は記録） | RFC 8693 §4.1 |

記入欄：

| 観点 | 決めたこと（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 上限 |  |  | `token_types[].max_delegation_depth` |
| 認可に使う act |  |  | `claims[].does_not_answer`（入れ子の act は q-actor に答えない） |

根拠：RFC 8693 §4.1、slide:p10-delegation-chain-depth

<a id="audit-correlation"></a>
## 8. 監査の相関〔Full：記入／Lite：参照〕

項目 ID：`template:profiles/P4_ai_agent_delegation#audit-correlation`
<!-- req:p10-agent-identity.R5 req:p10-per-tool-scopes.R3 req:p10-human-approval-evidence.R4 req:p11-pre-add-questions-2.R9 -->

決めること：委任の連鎖を、資格情報（`act`）とログの両方でたどれるようにする項目。誰の権限で（`sub`）、誰が実行したか（全アクター）、どの取引か（`txn`）、何の承認か（承認 ID）、スコープの引き上げ（相関 ID）を、別々の項目で記録します。

| 記録する項目 | 検討の問い | 出どころの候補 | 根拠 |
| --- | --- | --- | --- |
| 誰の権限で | 利用者を `iss`＋`sub` の組で記録するか | トークンの `sub`（ハッシュ化の要否は M_privacy_minimization） | slide:p06-audit-trail |
| 誰が実行したか | 連鎖の全アクターを記録するか | `act` の入れ子・`client_id`・mTLS の相手 | slide:p10-agent-identity、RFC 8693 §4.1 |
| どの取引か | 1 つのタスクの全ホップを同じ ID で結ぶか | Txn-Token の `txn`／組織のタスク ID | draft-ietf-oauth-transaction-tokens-11 §9.2 |
| 何の承認か | 承認の記録を指す ID を残すか | 組織の承認 ID／`authorization_details` | slide:p10-human-approval-evidence |
| スコープの引き上げ | 引き上げを相関 ID つきで記録するか | 引き上げの要求の ID | slide:p10-per-tool-scopes |
| 委任のクレームとの関係 | 共有の独自クレーム（承認 ID など）と `act` の関係を、追加前の問い 21 に答えたか | `template:claim_request#q21` | slide:p11-pre-add-questions-2 |

記入欄：

| 記録する項目 | 記録の仕方（書き手が書く） | 理由（書き手が書く） | 台帳の ID |
| --- | --- | --- | --- |
| 誰の権限で |  |  | `claims[].log_policy` |
| 誰が実行したか |  |  | `claims[].log_policy`（act の行） |
| どの取引か |  |  |  |
| 何の承認か |  |  |  |

根拠：slide:p06-audit-trail、slide:p10-agent-identity、draft-ietf-oauth-transaction-tokens-11 §9.2、筆者の提案：委任の監査の項目を問いごとに 1 行にする（追跡 #4）

<a id="chain-revocation"></a>
## 9. 委任の一括失効〔Full：記入／Lite：参照〕

項目 ID：`template:profiles/P4_ai_agent_delegation#chain-revocation`
<!-- req:p10-delegation-chain-depth.R3 -->

決めること：利用者が委任を取り消したとき、そこから交換で作った下流のトークンをどう止めるか。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 止める手段 | 根元の承認（委任）を取り消したら、下流のトークンはいつ使えなくなるか | 短命にして交換のたびに取り消しを確かめる／イントロスペクション／状態リスト／SSF・CAEP の通知 | slide:p10-delegation-chain-depth、slide:p08-revocation-propagation |
| 許す遅れ | 取り消しから下流が止まるまで、最悪何秒を許すか | 下流のトークンの寿命＋時計のずれ／問い合わせの間隔 | jwt-claims-casestudy@080b8da:C9 |
| 長い処理 | 取り消しの後も動き続ける非同期の処理があるか | なし／ある（再開時に確かめる） | slide:p08-async-processing |

記入欄：

| 観点 | 決めたこと（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 止める手段 |  |  | `token_types[].revocation`（委任・タスクのトークンの行） |
| 許す遅れ |  |  | `token_types[].revocation[].delay_seconds` |

根拠：slide:p10-delegation-chain-depth、slide:p08-revocation-propagation

<a id="registry-map"></a>
## 10. 台帳・目録との対応

項目 ID：`template:profiles/P4_ai_agent_delegation#registry-map`

| 決めること | 列 |
| --- | --- |
| 誰の権限で・誰が代理して実行しているか | `claims[].answers`（q-sub・q-actor）・`does_not_answer`（入れ子の act） |
| 宛先の絞り込み・交換 | `hops[].aud`・`scope`・`exchanger`・`narrowing_exception` |
| 委任の深さ | `token_types[].max_delegation_depth` |
| 承認の内容 | `claims[]`（authorization_details）・`claims[].enforced_at` |
| 送信者制約 | `issuance_profile.sender_constraint`、`token_types[].sender_constraint`（`template:modules/M_sender_constraint`） |
| 失効 | `token_types[].revocation` |

根拠：templates/registry/README.md の 3.1・3.2・3.4、templates/registry/questions.yaml の q-actor
