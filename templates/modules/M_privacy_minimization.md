<!-- template_version: 0.3.0 -->
# 個人情報と最小化（modules/M_privacy_minimization）

> テンプレートです。候補と検討の問いだけを載せ、採否の理由の見本は載せません（理由の写し書きを防ぐため。#4 の方針）。判断は台帳（claims.yaml など）に 1 回だけ書き、ここからは ID で参照します。

- 使う場面：個人に関するクレームを載せる境界、ログ・監査・分析基盤にクレームを残す境界、外部の受け手にクレームを渡す境界
- 組み合わせ：`template:00_core#token-inventory`（種別ごとの「誰が読めるか」と JWE の有無）、`template:modules/M_token_validation#nested-jwt`（JWE を使うとき）、`template:modules/M_multitenancy#cross-tenant`（外部の受け手）
- Lite での扱い：規制の対象（個人情報の扱いに特別な規制がある）は #4 の Lite の判定の 5 問の 1 つで、Yes なら Full です。Lite でも、台帳の `pii_category`・`log_policy`・`data_category`・`confidential_from`（と、空でなければ `confidentiality_measure`）は R1 の必須の列なので書きます。このモジュールの記入欄は Full で書きます
- 法令の判断は、筆者の読みです。自組織の法務・個人情報の担当の確認を代わるものではありません
- 作成方法：本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています。人による点検は未実施。

<a id="appi-table"></a>
## 1. 個人情報保護法の判断表〔Lite・Full：記入〕

項目 ID：`template:modules/M_privacy_minimization#appi-table`

決めること：クレームごとに、個人情報の保護に関する法律の区分（台帳の `pii_category` の 5 つの値）のどれに当たるかと、そこから決まる扱い。区分は `data_category`（何のデータか。fideslang の語彙）とは別の軸です（`templates/registry/README.md` の 9.）。

| `pii_category` | 法律の定義（条・項） | 検討の問い | 決まること（台帳の列） | 根拠 |
| --- | --- | --- | --- | --- |
| 個人情報 | 第 2 条第 1 項（生存する個人に関する情報で、特定の個人を識別できるもの。他の情報と容易に照合でき、それで識別できるものを含む） | 社内の利用者の表と容易に照合できる ID（sub・社員番号など）か | `log_policy`、`confidential_from`、`recipients_external`、`cross_border` | 個人情報の保護に関する法律（平成十五年法律第五十七号）第2条第1項 |
| 要配慮個人情報 | 第 2 条第 3 項（人種・信条・社会的身分・病歴・犯罪の経歴など、政令で定める記述等を含む個人情報） | 載せる必要が本当にあるか（下の 6. の順で、載せない・派生値を先に検討したか） | `confidential_from`・`confidentiality_measure` | 個人情報の保護に関する法律（平成十五年法律第五十七号）第2条第3項 |
| 仮名加工情報 | 第 2 条第 5 項（他の情報と照合しない限り特定の個人を識別できないように加工したもの） | 照合の表を誰が持つか。トークンの受け手が照合できないか | `identifier_properties` | 個人情報の保護に関する法律（平成十五年法律第五十七号）第2条第5項 |
| 個人関連情報 | 第 2 条第 7 項（生存する個人に関する情報で、個人情報・仮名加工情報・匿名加工情報のどれにも当たらないもの） | 受け手（第三者）の側で個人データとして取得されることが想定されるか（第 31 条） | `recipients_external` | 個人情報の保護に関する法律（平成十五年法律第五十七号）第2条第7項、個人情報の保護に関する法律（平成十五年法律第五十七号）第31条 |
| 該当なし | — | 個人に関する情報ではないと言えるか（テナント ID・トークンの種別など） | — | 筆者の提案：区分に「該当なし」を置き、理由を台帳の rationale に書く（追跡 #3） |

区分のほかに、第三者に渡す・国外に移すときの条文も確かめます。

| 場面 | 条 | 検討の問い | 台帳の列 | 根拠 |
| --- | --- | --- | --- | --- |
| 社外の受け手に渡す | 第 27 条（第三者提供の制限） | 社外の受け手（取引先の API・SaaS）が、トークンの中身を受け取るか | `recipients_external` | 個人情報の保護に関する法律（平成十五年法律第五十七号）第27条 |
| 国外の受け手に渡す | 第 28 条（外国にある第三者への提供の制限） | 受け手・ログ基盤・分析基盤が国外にあるか | `cross_border` | 個人情報の保護に関する法律（平成十五年法律第五十七号）第28条 |
| 個人関連情報を渡す | 第 31 条（個人関連情報の第三者提供の制限等） | 受け手が個人データとして取得するか | `recipients_external` | 個人情報の保護に関する法律（平成十五年法律第五十七号）第31条 |
| 安全管理 | 第 23 条（安全管理措置） | トークン・ログに写した個人データを、誰が読めるか | `confidential_from`、`log_policy` | 個人情報の保護に関する法律（平成十五年法律第五十七号）第23条 |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| クレームごとの区分 |  |  | `claims[].pii_category` |
| 社外の受け手 |  |  | `claims[].recipients_external` |
| 国外への移転 |  |  | `claims[].cross_border` |

根拠：個人情報の保護に関する法律（平成十五年法律第五十七号）第2条、個人情報の保護に関する法律（平成十五年法律第五十七号）第27条、slide:p09-jws-is-readable、templates/registry/README.md の 9.、筆者の提案：法の区分を台帳の 5 つの値に写して判断は自組織の法務が確かめる（追跡 #3）

<a id="protection-table"></a>
## 2. 保護の要件表〔Lite：生成／Full：生成と確かめ〕

項目 ID：`template:modules/M_privacy_minimization#protection-table`

決めること：クレームごとに、改ざん防止（署名）だけで足りるか、流出防止（読ませない）も要るかと、落ち着いた手段。この表は手で書かず、台帳の次の列から作ります。手で直すのは台帳の側です。

| 表の列 | 元にする台帳の列 | 意味 | 根拠 |
| --- | --- | --- | --- |
| 改ざん防止で足りるか、流出防止も要るか | `confidential_from` が `[]` か | `[]` なら署名だけで足りる。空でなければ流出防止が要る | slide:p09-jws-is-readable、RFC 7519 §11.2 |
| 読まれてはいけない相手 | `confidential_from`（browser・client・bff・gateway・idp・api・db・logs・analytics・external_rp・broker・`hop:<名前>`） | 載る種別の `visible_to` と突き合わせる（#6 の L65） | slide:p09-jws-is-readable |
| 落ち着いた手段 | `confidentiality_measure.outcome`（載せない・派生値・参照・JWE）と `rationale` | 6. の順のどこで落ち着いたか | slide:p09-jwe-sd-jwt |
| 署名の保護が外れる場所 | `integrity_until`（http_header・db_session・queue_message・log・cache・other と、写し先・信頼境界） | 署名の外に写した値を、どの境界が守るか | slide:p07-trust-boundary、slide:p06-header-forwarding |
| 載るトークンの JWE の有無 | トークン目録の `jwe`・`visible_to` | 種別ごとに誰が読めるか | slide:p09-jwe-sd-jwt |

生成：`python tools/claim_lint render <設計書のディレクトリ>` には、2026-11-23 の時点でこの表の節がありません（#19 の節の一覧は `tools/claim_lint/RENDER.md` の 1.）。節ができるまでは、上の列を `claims.yaml` から写した表を設計書の付録に置き、L65〜L67（#6）の結果を添えます。

記入欄（台帳の列で答える。理由は台帳の `confidentiality_measure.rationale` に書く）：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 読まれてはいけない相手 |  |  | `claims[].confidential_from` |
| 落ち着いた手段 |  |  | `claims[].confidentiality_measure` |
| 署名の保護が外れる場所 |  |  | `claims[].integrity_until` |

根拠：slide:p09-jws-is-readable、slide:p09-jwe-sd-jwt、RFC 7519 §11.2、templates/registry/README.md の 8.、筆者の提案：保護の要件表を台帳から作って手で二重に書かない（追跡 #19）

<a id="protection-order"></a>
## 3. 機微な値の保護の順〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_privacy_minimization#protection-order`
<!-- req:p09-jwe-sd-jwt.R1 -->

決めること：機微な値を運ぶ必要があるとき、どの手段に落ち着くか。上から順に検討し、下へ進むときは上を採れない理由を台帳に書きます。

| 順 | 手段 | 検討の問い | 注意 | 根拠 |
| --- | --- | --- | --- | --- |
| 1 | 載せない（参照型・identity API・UserInfo） | 受け手は全要求でこの値を要するか | 問い合わせが増える | slide:p09-jwe-sd-jwt、slide:p09-do-not-carry |
| 2 | 派生値（判定だけを渡す） | 受け手が要るのは値か判定か（4.） | 判定の責任は発行者 | slide:p09-minimize-derived |
| 3 | 参照（ID だけを載せ、値は API で） | 参照を解決する API を誰に開くか | 参照の ID も個人情報になりうる | slide:p09-jwe-sd-jwt |
| 4 | JWE（署名してから暗号化）・SD-JWT | 中継を通り、受け手以外に読ませない必要があるか。受け手ごとに開示を変えるか | 外側と内側の両方を検証する（template:modules/M_token_validation#nested-jwt）。SD-JWT では iss・aud・exp・cnf を選択的開示にしない | slide:p09-jwe-sd-jwt、RFC 8725 §3.3 |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| クレームごとの落ち着いた手段 |  |  | `claims[].confidentiality_measure` |
| JWE を使う種別と復号できる相手 |  |  | `token_types[].jwe` |

根拠：slide:p09-jwe-sd-jwt、slide:p09-minimize-derived、slide:p09-do-not-carry、RFC 8725 §3.3

<a id="derived-values"></a>
## 4. 派生値〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_privacy_minimization#derived-values`
<!-- req:p09-minimize-derived.R1 req:p09-minimize-derived.R2 -->

決めること：受け手が要るのが値そのものか、判定か。判定で足りるなら、元の値を明かさない派生値（例：生年月日ではなく「18 歳以上か」）を載せ、判定の書き手を発行者に限ります。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 受け手が要るもの | 受け手は値で何を決めるか。判定だけで同じことを決められるか | 値／派生値 | slide:p09-minimize-derived、NIST SP 800-63C-4 §3.10 |
| 派生値の書き手 | 判定を計算するのは誰か。受け手や呼び出し側が判定を書けないか | 発行者（IdP・入口の発行サービス）／それ以外 | slide:p09-minimize-derived、NIST SP 800-63C-4 §3.12.2 |
| 判定の鮮度 | 判定が変わるまでの時間と、トークンの寿命の関係 | `volatility` を書き、L5 で確かめる | slide:p04-token-is-snapshot |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 値か派生値か |  |  | `claims[].confidentiality_measure`（outcome：派生値） |
| 派生値の書き手 |  |  | `claims[].authoritative_writer`、`claims[].provenance` |

根拠：slide:p09-minimize-derived、NIST SP 800-63C-4 §3.10、NIST SP 800-63C-4 §3.12.2

<a id="sensitive-via-api"></a>
## 5. 機微な属性を API で渡す〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_privacy_minimization#sensitive-via-api`
<!-- req:p09-minimize-derived.R3 -->

決めること：それでも機微な属性が要る受け手に、トークンではなく identity API（UserInfo など）でどう渡すか。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 取りに行く受け手 | どの受け手が、いつ、どの属性を取りに行くか | 受け手ごとの許可 | slide:p09-minimize-derived、NIST SP 800-63C-4 §3.12.3 |
| API の呼び出しのトークン | API を呼ぶトークンに送信者制約を付けるか | DPoP／mTLS／なし（template:modules/M_sender_constraint） | slide:p09-minimize-derived |
| 期間 | 取得した属性を受け手がいつまで持つか | 要求の間だけ／キャッシュの秒数 | slide:p09-minimize-derived |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| API で渡す属性と受け手 |  |  | `claims[].decision: 却下`（代替ありの行）、`claims[].alt` |
| API のトークンの送信者制約 |  |  | `token_types[].sender_constraint` |
| 受け手が持つ期間 |  |  |  |

根拠：slide:p09-minimize-derived、slide:p09-do-not-carry、NIST SP 800-63C-4 §3.12.3

<a id="identifier-sectors"></a>
## 6. 社内の ID と外部に出す ID〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_privacy_minimization#identifier-sectors`
<!-- req:p09-pairwise-identifiers.R2 -->

決めること：社内で突き合わせる ID と、外部の受け手に出す ID を分けるか。分けるなら、どのセクター単位でペアワイズの sub を出すか。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| sub の種類 | 受け手どうしが sub を突き合わせて利用者を追跡できてよいか | public／pairwise（セクターごと） | slide:p09-pairwise-identifiers、OpenID Connect Core 1.0 §8 |
| 社内の突き合わせ | 複数の社内サービスで同じ利用者を突き合わせる必要があるか | 同じセクターにする／組織の不変の ID を別に持つ | slide:p09-pairwise-identifiers |
| 外部の受け手 | 外部に出す ID に識別情報が含まれないか。推測できないか | ペアワイズの仮名識別子 | slide:p09-pairwise-identifiers、NIST SP 800-63C-4 §3.4.1.2 |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 種別ごとの sub の種類 |  |  | `token_types[].subject_type` |
| 外部の受け手と目的 |  |  | `claims[].recipients_external` |
| 識別子の性質 |  |  | `claims[].identifier_properties` |

根拠：slide:p09-pairwise-identifiers、OpenID Connect Core 1.0 §8、NIST SP 800-63C-4 §3.4.1.2

<a id="audit-log"></a>
## 7. 監査ログに残す項目と伏せる項目〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_privacy_minimization#audit-log`
<!-- req:p05-system-privileges.R4 req:p06-audit-trail.R1 req:p06-audit-trail.R3 req:p07-connect-as-whom.R2 req:p09-logs-traces.R3 -->

決めること：後から「誰の権限で・誰が実行し・どこを経由し・何の承認で・どの取引か」を説明できるように、どの項目をどの形で残すか。トークンの全文と、トークンの中の個人情報は残さない前提で決めます（slide:p09-logs-traces）。

| 問い | 残す項目 | 残し方の候補 | 根拠 |
| --- | --- | --- | --- |
| 誰の権限で | 最上位の `sub` | ハッシュなどで難読化／値のまま | slide:p06-audit-trail、NIST IR 8587 §5.3.1.7 |
| 誰が実行したか | 現在の実行者（最も外側の `act.sub`）・`req_wl`・mTLS の相手の ID | 値のまま／ハッシュ | slide:p06-audit-trail、RFC 8693 §4.1 |
| どこを経由したか | 入れ子の `act`（過去の実行者。認可には使わない） | 値のまま | slide:p06-audit-trail |
| 何の承認で | `authorization_details` の識別子・同意 ID・承認 ID | ID だけ | slide:p06-audit-trail |
| どの取引か | `txn` | 値のまま | slide:p06-audit-trail、draft-ietf-oauth-transaction-tokens-11 §15.2 |
| 運用者の操作 | 顧客の `sub` と運用者の `act` の両方 | 両方を残す | slide:p05-system-privileges |
| トークンの種類 | `typ`・`iss`・`aud`・`scope`・`jti` | 値のまま | slide:p09-logs-traces、NIST IR 8587 §5.3.1.7 |
| イベント | 発行・検証の失敗（理由）・失効 | 値のまま | slide:p09-logs-traces |
| DB の監査 | DB の監査ログに利用者を残すか（ID を DB まで伝えるか。`template:modules/M_data_layer#db-identity`） | 利用者の ID／サービスの ID と注入値 | slide:p07-connect-as-whom |
| 残さないもの | トークンの全文・Authorization ヘッダー・個人情報のクレームの値 | 記録するヘッダーを許可リストで決める | slide:p09-logs-traces、OWASP Logging Cheat Sheet |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| クレームごとのログの方針 |  |  | `claims[].log_policy` |
| 種別ごとのトークンのログの方針 |  |  | `token_types[].log_policy` |
| 承認・取引の相関に使う ID |  |  | `claims[]`（txn・承認 ID の行） |
| 記録するヘッダーの許可リスト |  |  |  |

根拠：slide:p06-audit-trail、slide:p09-logs-traces、slide:p05-system-privileges、slide:p07-connect-as-whom、RFC 8693 §4.1、draft-ietf-oauth-transaction-tokens-11 §15.2、NIST IR 8587 §5.3.1.7、OWASP Logging Cheat Sheet

<a id="audit-log-protection"></a>
## 8. 監査ログ自体の保護〔Full：記入／Lite：参照〕

項目 ID：`template:modules/M_privacy_minimization#audit-log-protection`
<!-- req:p09-logs-traces.R5 -->

決めること：監査ログそのものを機微な情報として扱い、誰が読めるか、いつまで残すかを決めます。ハッシュ化した主体も、照合の表があれば元に戻せます。

| 観点 | 検討の問い | 候補 | 根拠 |
| --- | --- | --- | --- |
| 読める者 | ログ基盤・分析基盤を読める者は誰か。`confidential_from` に logs・analytics を書いたクレームが写っていないか | 役割で限る | slide:p09-logs-traces、個人情報の保護に関する法律（平成十五年法律第五十七号）第23条 |
| 保存期間 | 監査に要る期間と、消す時期 | 期間を決める | slide:p09-logs-traces |
| ハッシュの扱い | ハッシュの鍵（salt・HMAC の鍵）を誰が持つか | HMAC／単純なハッシュ | 筆者の提案：主体のハッシュは鍵つきにして鍵の持ち主を書く（追跡 #4） |
| 分析基盤への複製 | 監査ログやクレームを分析基盤へ複製するか（`catalog:use_events#U28`） | 複製しない／列を絞って複製 | slide:p09-logs-traces |

記入欄：

| 決めること | 選んだ候補（書き手が書く） | 理由（書き手が書く） | 台帳・目録の ID |
| --- | --- | --- | --- |
| 読める者 |  |  |  |
| 保存期間 |  |  |  |
| 主体のハッシュの方式と鍵の持ち主 |  |  | `claims[].log_policy: ハッシュ化して記録` |

根拠：slide:p09-logs-traces、個人情報の保護に関する法律（平成十五年法律第五十七号）第23条、筆者の提案：主体のハッシュは鍵つきにして鍵の持ち主を書く（追跡 #4）
