# 記入の記録：シナリオ C（Lite、ブラインド記入）

パイロット #9 の書き手の記録です。**LLM（Claude）による記入。人による検証ではない。** 時間は LLM の作業の壁時計で、人の記入時間の代わりになりません（`templates/README.md` の「記入の目安」の注記と同じ）。

- 書き手：Claude（LLM。設計の書き手の役）
- 読んだもの：要求の概要（brief-C.md）、`templates/`（examples と casestudy-* を除く）、`tools/`（claim_lint の RULES.md・RENDER.md・coverage.py・r8.py、new_design.py、count_lite_fields.py）、Web の fideslang 3.1.4 の data_categories.csv
- 読まなかったもの：`templates/examples/**`、`templates/casestudy-*`、`research/**`（この記録のディレクトリを除く）、`docs/claims/data/**`、ケーススタディのリポジトリ、#9 以外の issue・PR のコメント、brief-B.md。誤って開いたものはない
- 注：`templates/registry/README.md` と `tools/claim_lint/RULES.md` の本文には、記入例のパスや測定の数（シナリオ A の誤検知の数など）が載っている。ファイルは開いていないが、本文の中の言及は読んだ

## 1. 時間（壁時計、JST）

| 区間 | 開始 | 終了 | 中身 |
| --- | --- | --- | --- |
| 要求と始め方を読む・空の設計書を作る | 06:38:48 | 06:39:00 | brief-C.md、GETTING_STARTED.md、`python tools/new_design.py research/pilot/scenario-c`（最初の lint：error 120・warn 69） |
| テンプレートを読む | 06:39:00 | 06:42:35 | README.md、00_core.md、P4、registry/README.md の 2.・3.、RULES.md の R1・網羅の規則、スキーマ 3 つ |
| 判定と方針（§7 の 9 点）を決める・カタログの一覧を読む | 06:42:35 | 06:44:07 | 下の 2. の迷い 1〜14 |
| トークン目録と発行方式（token_types.yaml） | 06:44:07 | 06:47:30 頃 | 19 行（採用 6・却下 13）。最初の lint で L7（必須クレームが台帳に無い）を確認 |
| 台帳とホップ（claims.yaml・hops.yaml） | 06:47:30 頃 | 06:48:57 | 21 行（採用 11・却下 10）、ホップ 3 つ（交換 1）。lint：error 10 |
| カタログへの回答と網羅の節（catalog_answers.yaml）・直し | 06:48:57 | 06:51:41 | 62 件、idp、questions、subject_states、pairwise、outside_enumeration。lint：**error 0** |
| 設計書の手で書く節（design.md）と render | 06:51:41 | 06:53:56 | 冒頭の 4 行、2.・2.1・2.3（MCP の表）・3.・3.1・3.2・6.・9.1・9.2・12.・13.。`render --write`、`render --check` OK |
| ほかの検査と欄の数 | 06:53:56 | 06:54:30 | check_mermaid・check_slide_refs・template_check、count_lite_fields |
| この記録 | 06:54:55 | 06:58 頃 | — |

合計：約 20 分（06:38:48〜06:58 頃）。手で書いた欄は 1033（`python tools/count_lite_fields.py --current research/pilot/scenario-c --profile lite`）。

## 2. 迷った点（26 件）

| # | 欄 | 何に迷ったか | 選んだこと |
| --- | --- | --- | --- |
| 1 | `lite_criteria.crosses_boundary` | 組織は 1 つだが、悪意ある MCP サーバー（C13）がいる。「境界を越える」を組織の境界と読むか、信頼の境界と読むか | No（README の Yes の例が「取引先・外部の IdP・別の組織」なので組織の境界と読んだ）。理由に「信頼しない部品」と書いた |
| 2 | `lite_criteria.new_issuer` | 要求の「組織の内部のトークン発行サービス」が既存か新設か書かれていない | Yes（委任・交換の発行はこの設計で初めて使う） |
| 3 | Lite か Full か | 委任・交換が Yes なので定義上 Full。P4 自身も「委任がある設計は Full になる」と書く | パイロットの指示どおり Lite の欄で書き、Full で足すものを 12. に書いた。L73 の warn が 2 件残る |
| 4 | §7 の 8（Keycloak を使うか） | Keycloak 26.8 の標準の交換は act を付けず、委任はプレビュー（M_idp_keycloak の 1.） | 組織の STS（`idp.name: org-sts`）。Keycloak は使わない |
| 5 | `idp`（R3） | 製品でない STS をどの分岐で書くか（enumerable・trigger_list・trigger_list_source）。出どころの URL は「これから公開するメタデータ」しか書けない | enumerable: true と trigger_list を書き、URL は予定のメタデータ。12. に「今は存在しない」と書いた |
| 6 | 発行方式の grants | エージェントの最初のトークンを、利用者のトークンの交換で得るか、同意画面の認可コードで得るか | 認可コード＋PKCE（エージェントが利用者のトークンを持たない。C12 の借用の元を作らない） |
| 7 | §7 の 4（ツールが上流を呼ぶトークン） | 交換か、ツール自身の client credentials か | RFC 8693 の交換。client credentials は STS に実装しない（I05 を対象外に） |
| 8 | §7 の 1（深さ） | 「2 段」の数え方（act の数か、ホップの数か）。3・4 段の扱い。標準の根拠がない | act の数で数え、上限 2。3 以上は交換と受け入れの両方で拒否。C1 の正規の流れがちょうど 2 になる。数え方の誤りの可能性を 12. に |
| 9 | §7 の 7（今の行為者） | RFC 8693 §4.1 は入れ子の act を情報としてだけ扱う。C4 を防ぐには入れ子の行為者の権限も見たい | 最も外側の act.sub を mTLS の相手と照合。入れ子は権限を足さず、削る照合にだけ使う。専門家に見てほしい点として 12. に |
| 10 | §7 の 5（承認の照合） | トークンに載せるか、都度の参照か | 両方：STS が承認の記録から authorization_details を作り、請求書の API が完全一致で照合し、支払いのたびに記録を引いて消費する（二重払いも防ぐ） |
| 11 | §7 の 6（タスクの範囲） | scope の単位、タスク ID の独自クレームを足すか（足すと追加前の 25 問が要る） | scope は invoices:read・pay・refund。タスク ID・承認 ID の独自クレームは却下（STS の記録と authorization_details で足りる）。共有クレームは 0 |
| 12 | §7 の 2（取り消しの速さ） | 要求に数値がない | 目標 120 秒（請求書に届かなくなるまで）。設計の値は 90 秒（TOOL_AT 60 秒＋ずれ 30 秒） |
| 13 | §7 の 3（寿命） | 数値の要求がない。ガイドは「分単位」 | AGENT_AT 300 秒、TOOL_AT 60 秒、RT 8 時間（無操作 1 時間）、コード 60 秒 |
| 14 | §7 の 9（テナント） | 組織は 1 つだが将来の分社などを見込むか | テナントの値を持たない（C-tenant を却下、見直しの条件つき） |
| 15 | PORTAL_AT を目録に入れるか | ポータルは P1 で範囲の外だが、請求書の API が受け入れ、C12 の対象になる | 採用の行として入れ、発行の流れは範囲の外と書いた |
| 16 | `C-sub.log_policy` | 監査では利用者を特定したい（P4 の 8. は iss＋sub を記録）が、L6 が値のままの記録を error にした | ハッシュ化して記録（lint に合わせた）。監査で引く方法は書いていない |
| 17 | `C-authorization-details.confidential_from` | 振込先の口座（個人情報）を載せる。logs から隠すか、JWE にするか | confidential_from は空、log_policy を「記録しない」。JWE は決めず 12. に |
| 18 | `C-scope.volatility` | トークンごとの値（never）か、委任の変更を反映する許容の秒数か | 900 秒（委任・方針の変更の許容）。値の意味が行によって違って見える |
| 19 | P4 の MCP の必須チェック表の置き場所 | Lite でも必須だが、00_core に節がない | design.md に「2.3」を足して写した |
| 20 | P4 の 2.〜9. の記入欄 | 「Full：記入／Lite：参照」。Lite で何も書かないのか、台帳だけでよいのか | 記入欄は書かず、判断は台帳の行（C-act・C-authorization-details など）に書いた |
| 21 | `token_types[].max_delegation_depth` | 委任の深さはこのシナリオの重点（3.1 のガイドの候補）なのに、列は「Full のみ」 | 書いた（任意の列として） |
| 22 | L15（AGENT_RT に cnf の行がない） | 不透明な RT の束縛は STS の DB で持ち、クレームにならない | warn のまま残した（抑止しない） |
| 23 | 3.2 共通の基準 | 「満たさないものがあるときだけ」書く節の表を空で残すか | 「すべて満たすので書かない」の 1 行だけ |
| 24 | `data_category`（authorization_details） | fideslang に「承認」や「支払いの指示」のキーがない | user.financial.bank_account と user.payment |
| 25 | U02（DB の文脈） | 持ち主での絞り込みはデータ層の照合だが、U02 は SET LOCAL・RLS の行 | 対象外（アプリの照会で持ち主を条件にする）。崩れる条件に M_data_layer |
| 26 | I26（資格情報の変更） | 委任は資格情報と独立に続けるか、一括で取り消すか | 一括で取り消す（乗っ取りの疑いを優先）。該当にした |

## 3. テンプレートの欠陥・気づき

| # | どこ | 中身 |
| --- | --- | --- |
| D1 | `tools/new_design.py` の骨組み | `claims.yaml` の `namespaces: []` がスキーマ（minItems 1）に反し、最初から SCHEMA の error になる。キーを消すしかない（GETTING_STARTED は「空の欄の数だけ指摘が出る」と書くが、これは空の欄ではなく骨組みの誤り）。`hops.yaml` の `hops: []` も minItems 1 に反するので、交換・作り直しのホップが無い Lite の設計は、ホップを書かない限り error 0 にできない（hops.yaml を消せば通るかは確かめていない） |
| D2 | 00_core | P4 の MCP の必須チェック表は「Lite でも記入」だが、00_core に置き場所の節がない |
| D3 | registry の列の印 | `max_delegation_depth` が「Full のみ」。P4 の重点（深さの組織規則）なのに Lite で書く欄がない。P4 を使う Lite は定義上ありえない（委任があれば Full）ので、P4 の「Lite」の意味がはっきりしない |
| D4 | R3（coverage.py） | 製品でない組織の STS（この設計で一覧を決める発行者）の分岐がない。`trigger_list_source` に url と確かめた日を求めるが、これから作る STS では書ける出どころがない |
| D5 | L15 | 不透明な RT を mTLS で束縛する設計で、cnf のクレームの行を求める warn が出る（RT にクレームは無い）。誤検知の候補 |
| D6 | L6 と P4 の 8. | P4 の 8. は「利用者を iss＋sub の組で記録」と書き、L6 は sub を値のまま記録すると error。どちらに従うかの案内がない（「ハッシュ化の要否は M_privacy_minimization」とだけある） |
| D7 | render の lifecycle の 4. | `status` は Lite で「生成」の列だが、どこからも生成されず、表の「状態」がすべて「—」になる |
| D8 | 00_core の 9.1 の DB・ブローカーの接続の層 | トークンで DB に接続しない設計でも記入欄が残る。「無い」と書く欄にした |
| D9 | R2 | 62 件の対象外の理由は機械では妥当性を見ないので、1 回で通った（RULES.md の明記どおり）。中身の点検はレビュー（#5）に頼る |
| D10 | GETTING_STARTED の手順 4 | 「シナリオ A の記入例では目録の全体が 165 欄ほど」と記入例の数を示す。記入例を読まない条件のパイロットでは参考にならない（害はない） |

## 4. 検査の結果

- `python tools/claim_lint research/pilot/scenario-c --profile lite`：error 0、warn 3（L15 が 1、L73 が 2）、info 9。抑止なし
- `python tools/claim_lint render research/pilot/scenario-c --check`：OK
- `python tools/check_mermaid.py research/pilot/scenario-c/design.md`：2 ブロック、失敗 0
- `python tools/check_slide_refs.py research/pilot/scenario-c`：問題 0
- `python tools/template_check.py`：error 0
