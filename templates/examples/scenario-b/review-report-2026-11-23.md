# レビューレポート：templates/examples/scenario-b

> 設計書のエディターが `review.yaml` から生成した。レビュアーの名前は自己申告で、本当の承認は GitHub の PR のレビューで行う。レビュアーは LLM で、人による点検は未実施。

## 1. 基本情報

| 項目 | 値 |
| --- | --- |
| 対象 | templates/examples/scenario-b（版 bd1747b）。main の bd1747b の作業ツリーの版（PR #44 の点検を反映した後の版） |
| Lite／Full | Full。catalog\_answers.yaml の lite\_criteria は crosses\_boundary・delegation\_or\_exchange・new\_issuer の 3 つが true で、README の「1 つでも Yes なら Full」と合う。ただし Full で使うと宣言した P1・P4・P5 とモジュールの欄が設計書に無く、書かない理由も 12. に無い（README の判定がずれるときの規則にも合わない。F01） |
| 実施した手順の段 | 0〜7 を実施（0 受け付け・1 範囲と 12. を先に読む・2 判断の木と対比表で 6. の要る問いを照合・3 全 168 問・4 共有クレーム 9 件の 25 問と、指定の却下 3 行の理由の採点（採用の行の抜き取りは指定が無く未実施）・5 カタログ外の場面・6 専門家に回す基準・7 記録と戻す事項）。8 は対応が無いので未実施。引用元（RFC・製品文書）は開いていない（オフライン。q-evidence-attribution は No）。役割の切り替え順：攻撃者→受け手→発行者→運用→個人情報→クライアント |
| レビュアーと役割 | Claude Opus 5.5（LLM の一次スクリーニング）（LLM：claude-opus-5-5、1 つのセッション。名前は自己申告）。攻撃者 → 受け手 → 発行者 → 運用 → 個人情報 → クライアント（2026-11-23、1 つのセッションの中で切り替えた。日を分ける代わりに No の指摘を別のセッションで読み直すことは未実施） |
| 実施日 | 2026-11-23 |
| 使った教材の版 | templates/review（レビューした時の版：perspectives.md 0.4.0、report\_template.md 0.4.0、問い 168 問）。レビュアーは templates/examples/scenario-b/review-report.md（前のレビュー）、perspectives.md の 9.（較正）、research/reviews/ を読んでいない。レビューに渡した指示の全文は research/reviews/scenario-b-editor-review-prompt-2026-11-23.md。「前のレビューを読んでいない」は自己申告で、24 件のうち約 11 件は主題が前のレビュー（review-report.md）と重なる（PR #52 の独立点検）。その約 11 件は独立に見つかった証拠に数えない |
| CI の結果 | claim\_lint error 0・warn 6・info 31（profile full）。設計書の 1. と一致。今の版の claim\_lint の結果（error 0・warn 6・info 31、OK）が design.md の 1. の貼り付けと一致。R3b の warn 3 件（I12・I25・I26）は未解決のまま（F18） |
| 抜き取りの結果 | 乱数の種「20261123-b」（claims.yaml の却下の行 8 行から 3 行。sha256(種:行) の順）：C-rfc-roles・C-rctx・C-upn。3 件を採点、合格 2・不合格 1 |
| 問いの回答 | 全 168 問のうち 168 問に回答（未回答 0）。定義 Yes 45／No 12／該当なし 2。発行 Yes 9／No 3／該当なし 0。伝搬 Yes 24／No 2／該当なし 2。検証 Yes 12／No 1／該当なし 1。認可 Yes 15／No 6／該当なし 7。運用 Yes 13／No 14／該当なし 0。合計 Yes 118／No 38／該当なし 12 |

## 2. 指摘の一覧

| ID | 場所 | 内容 | 重大度 | 出どころ | 種別 | 取り違えた問い（種別が目的と仕組みの不一致のとき） | 判定 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F01 | template:00\_core（Full の設計書の全体）、template:modules/M\_token\_validation・M\_authz\_pdp・M\_idp\_keycloak・M\_privacy\_minimization・M\_sender\_constraint、template:profiles/P1\_human\_web・P4\_ai\_agent\_delegation・P5\_internal\_propagation、template:00\_core#uncertain | 冒頭で P1＋P4＋P5 を使う Full と宣言したが、プロファイルとモジュールの欄（shared-validator・library-config・limits・audit-log・audit-log-protection・human-approval・delegation-depth・tool-scopes・txn-token など）が設計書に 1 つも無く、書かない理由も 12. に無い（12. の CIBA の行は「P4 の human-approval の欄を埋めて」と未記入を認めている）。台帳で代替できない問い（ログのヘッダーの許可リスト・監査ログの保護・Keycloak の管理 API の障害・traceparent・スコープの昇格の記録）が判定できない | Major | 観点 | 候補の漏れ | — | 保留 |
| F02 | hops:H11 の validates.checks、template:modules/M\_data\_layer#masking-rls-bypass・#db-context-setter・#connection-lifetime、9.1 の DB の層 | ledger-db の RLS は「ENABLE と FORCE」「文脈が未設定なら 0 行」だけで、RLS をすり抜ける主体（スーパーユーザー・BYPASSRLS・テーブルの所有者・SECURITY DEFINER の関数）を ledger の接続の主体から外すこと、最小権限、同じ取引で任意の SQL や RESET ROLE を流せないこと、これらを試験で確かめる計画が無い | Major | 観点 | 候補の漏れ | — | 保留 |
| F03 | C-department.volatility・C-department.propagation\_delay・C-department.assumption、C-roles.volatility・C-roles.on\_revoke、claim\_request\_department.md の問 2、hops:H5〜H7 の note、9.2 | C-department は volatility・propagation\_delay とも 330 だが、同じ行の assumption は「異動は人事の台帳から 1 時間ごとに Keycloak へ同期」で、異動から反映まで最悪約 3600＋330 秒かかる。ledger が「操作のたびに Keycloak で引き直す現在の部署」（H11・B11 の対策）も Keycloak の値なので最大 1 時間古い。また INT\_AT 系の部署・ロールは KC\_AT（最大 330 秒）から写すが、INT\_AT の寿命を KC\_AT の残りの寿命以下にする記述は H4 だけで H5〜H7 に無く、写した値の古さは最悪 330＋330 秒になりうる（C-roles の 390 秒の計算も KC\_AT の古さを数えていない） | Major | 観点 | 理由の不備 | — | 保留 |
| F04 | C-iss.enforced\_at（payment-worker）・C-exp.enforced\_at（payment-worker）・C-sub.enforced\_at（payment-worker）、hops:H12・H13 の validates.checks、2.2 の支払いの通知の行、catalog\_answers の U13 | H12・H13・2.2・KC\_AT の long\_running は「メッセージにはハッシュした user\_id と txn と approval の ID だけ、トークンを入れない、ワーカーは利用者のトークンを持たない」とするが、台帳は payment-worker に「メッセージに付いた TXN の iss」「TXN の exp。処理が寿命を超えたら自分のワークロード ID で TTS から取り直す」「TXN の sub を処理の主体として記録」を求める（payment-worker は C-iss の consumers にも無い）。取り直す TXN の sub が誰かも無い。さらに ledger の受けるトークン（INT\_AT\_LEDGER・TXN）に approval\_id は無いのに、ledger のイベントに approval の ID を入れるとある | Major | 観点 | 実装とのずれ | — | 保留 |
| F05 | C-sub.enforced\_at（orders・invoices）、C-user-id.enforced\_at（orders・invoices）、C-sub.description、6. の q-user、template:modules/M\_authz\_pdp#object-level | orders は sub で「注文の持ち主の列と照合（BOLA）」し、user\_id でも「注文の持ち主と照合」する。invoices も sub と user\_id の両方で請求書の持ち主と照合する。STS のトークンでは sub と user\_id は同じ値（C-sub の description）で、同じ意味の値に 2 つの名前を付けている（C-sid の note は「同じ値に 2 つの名前を付けない」としている）。持ち主の照合のキーを 1 つに決めていない | Major | 観点 | 目的と仕組みの不一致 | \`q-user\` を \`sub\`（C-sub）でも答えた（orders・invoices の持ち主の照合。生成の表の q-user の答えは iss と user\_id） | 保留 |
| F06 | catalog\_answers:I05 の assumption、C-sid.assumption、INT\_AT\_LEDGER.revocation（db\_lookup）、C-roles.enforced\_at（orders・gateway）、template:00\_core#catalog-answers（outside\_enumeration） | ledger は「Keycloak の管理 API（セッションの一覧）を読み取り専用のサービスアカウントで引ける」前提で、orders も管理の操作で Keycloak のロールを引き直し、入口は各社のディレクトリで所属を引く。これらの資格情報（Keycloak のサービスアカウントの AT、各社のディレクトリの API のトークン）は目録にもカタログの回答にも無く、I05 は「Keycloak から client credentials の AT を出さない」と答えている。管理 API の権限の範囲・寿命・漏れたときの影響が検討されていない | Major | カタログ外の質問 | 候補の漏れ | — | 保留 |
| F07 | token\_types:AGENT\_AT.required\_claims、7. のシーケンス図の CIBA（G-&gt;&gt;P・P--&gt;&gt;G）、catalog\_answers:I13、付録 B、12. の CIBA の行 | 支払い（invoices.pay）は CIBA の承認で許すが、承認は sts が portal に依頼し、社員が portal で承認する形で、承認の時の認証の強さ・新しさ（acr・auth\_time・max\_age）を求めていない（AGENT\_AT・TASK\_AT にも acr・auth\_time が無い。付録 B は ledger.post だけ）。portal から sts へ承認の結果を返す経路の認証・完全性も書いてない。BFF のセッション（最大 36000 秒・pwd）のまま支払いを承認できうる。CIBA の流れは 12. で未実測 | Major | 観点 | 候補の漏れ | — | 保留 |
| F08 | token\_types:EXT\_AT.revocation、9.1 の EXT\_AT の行、C-roles.on\_revoke、template:00\_core#lifecycle | グループ会社の社員の停止は、EXT\_AT の exp\_only（5430 秒）と「入口の許可リスト（グループ会社の IdP ごとの停止）」だけで、利用者単位の止め方が無い。入口は INT\_AT を作るたびにディレクトリで所属を引くが、無効化・削除した利用者をそこで拒むかは書いてない。シナリオ B の重点（退職・異動の直後）がグループ会社の社員では最悪 5430＋330 秒届かない | Major | 観点 | 候補の漏れ | — | 保留 |
| F09 | claim\_request\_tenant\_id.md・user\_id.md・department.md・employee\_id.md・v.md・task\_id.md・approval\_id.md の問 5 と判定の行、各行の status | 7 件の問 5（「.」「/」入りの名前を全受け手のツールで読めるか）が「まだ試していない」「確かめた記録が無い」「この記入例では確かめていない」なのに、判定は「25 問すべてに答えた。共有クレームにする」で status active のまま KC\_AT・INT\_AT 系に載せている。dc-04 は「確かめていない」なら確かめるまで載せないとする | Major | 観点 | 理由の不備 | — | 保留 |
| F10 | C-user-id・C-department・C-employee-id の authoritative\_writer（Keycloak の User Attribute マッパー）と provenance、各 claim\_request の問 11、12. の名前空間のマッパーの行 | 3 件は Keycloak の利用者の属性から出し、provenance は管理者の値、問 11 は「本人は書けない」とするが、Keycloak 26.8 の利用者プロファイルでその属性を利用者が編集できない設定（アカウントコンソール・登録の画面での権限）にしたことの記録・出どころが無い。docs の部門の認可（C-department）と持ち主の照合（C-user-id）が依存する。却下した Cognito の custom:role と同じ型の危険を、Keycloak の側で確かめていない（仕様・製品の挙動の正否は専門家の確認が要る） | Major | 観点 | 理由の不備 | — | 保留 |
| F11 | claim\_request\_idp.md の問 9 と C-idp.on\_missing・C-idp.absent\_semantics・C-idp.enforced\_at、claim\_request\_approval\_id.md の問 19 と C-approval-id.consumers、C-idp.usage | idp の問 9 は「無ければ監査に unknown と書く（処理は続ける）」だが、台帳は on\_missing 拒否・absent\_semantics「拒否」・orders の「必須（無ければ拒否）」。approval\_id の問 19 は「読むのは invoices だけ」だが consumers は invoice-mcp と invoices（問 22 も両方）。また C-idp は usage display（監査だけ）で、dc-01 の「認可に使わないなら載せない」に当たる理由が無い | Minor | 観点 | 実装とのずれ | — | 保留 |
| F12 | claim\_request\_department.md・roles.md・idp.md・employee\_id.md の問 16、template:modules/M\_token\_validation#shared-validator | 問 16 の回答が「docs の 1 か所で確かめる」「orders の 1 か所で確かめる」「payroll にも同じ検査を置く（旧システムで共通の部品を使えない）」で、組織の共通の検証部品で読むと言えない。payroll が共通部品を使わないことは、検証の例外として 3.2 や 12. に書かれていない | Minor | 観点 | 理由の不備 | — | 保留 |
| F13 | 3.2 の「ログにトークン全文と個人情報を残さない：満たす」、C-department.log\_policy・C-department.pii\_category、claim\_request\_department.md の問 20 | 3.2 は満たすとするが、C-department は pii\_category 個人情報で log\_policy「記録する」（値のまま）。基準を満たさないなら baseline-unmet で回す、満たすならハッシュ化するか個人情報でない理由を書く必要がある | Minor | 観点 | 実装とのずれ | — | 保留 |
| F14 | INT\_AT・INT\_AT\_LEDGER・INT\_AT\_DOCS・INT\_AT\_PAYROLL・AGENT\_AT の jwe.note、catalog\_answers:I06・I13 の hook\_checked、6. の q-peer（エージェントの行）と C-act.enforced\_at（invoice-mcp）、9.1 の DB の層の行と hops:H11、TXN.log\_policy と required\_claims | (1) INT\_AT 系の jwe.note「個人情報を載せない（IDT だけ）」だが user\_id・department・employee\_id（pii 個人情報）を載せる。AGENT\_AT の「載るのは ID と task\_id だけ」だが authorization\_details（creditorAccount）を載せる。(2) I06・I13 は「設計書の 3. の設定の一覧で確かめる」とするが 3. にその一覧が無い。(3) 6. は q-peer の mTLS を invoice-mcp と invoices の間だけとするが、invoice-mcp は act.sub を agent-runtime との mTLS の相手と照合する。(4) 9.1 は「部署は DB の側で社員の表から引く」、H11 は「Keycloak の管理 API で引き直した部署を app.department に設定」。(5) TXN の log\_policy は jti だけだが required\_claims に jti が無い | Minor | 観点 | 実装とのずれ | — | 保留 |
| F15 | C-iat.enforced\_at（invoice-mcp・invoices）、C-jti.enforced\_at（invoice-mcp・invoices）、token\_types:DPOP.jti\_policy・revocation | DPoP の proof は iat が「今から ±60 秒の中」なら受ける（受け入れの幅 120 秒）が、jti は 90 秒（60＋30）しか覚えない（max\_age\_seconds 90）。iat が未来寄りの proof は、jti を忘れた後も受け入れの窓に残り、同じ proof の再送を拒めない時間がありうる。片方は「受け入れる期間 60 秒＋ずれ 30 秒」、もう片方は ±60 秒で、受け入れの期間の定義が 2 つある | Minor | 観点 | 実装とのずれ | — | 保留 |
| F16 | issuance\_profile:rt\_strategy の rationale と refs、token\_types:RT.rt\_rotation | RT は機密クライアントの BFF だけが持つのに、方式の根拠に公開クライアントへの要求である RFC 9700 §4.14.2 だけを引く（RR5）。再利用の検知は unverified のままで、機密クライアントでローテーションを選ぶ理由（漏れたときに何で止めるか）が無い | Minor | 観点 | 理由の不備 | — | 保留 |
| F17 | template:00\_core#lifetime-policy（5.1）、各種別の lifetime\_refs | 5.1 は組織の上限 3600 秒とこの設計の 300 秒を並べるだけで、300 秒を「剥奪をどれだけ早く効かせたいか」から導いた理由と、短くする代償（リフレッシュ・入口の作り直しの負荷、IdP・sts の停止の影響）の比較が無い | Minor | 観点 | 理由の不備 | — | 保留 |
| F18 | catalog\_answers:I12・I25・I26（hook\_checked なし）、1. の R3b の warn 3 件 | 追加認証（I12）・初回ログイン（I25）・パスワード変更の後のログイン（I26）で、プロトコルマッパーが呼ばれて独自クレーム 7 件が載るかが unknown のまま（R3b warn）。受け手の拒否で閉じる側には倒れるが、hook\_checked が無く、確かめ方も書いてない | Minor | 観点 | 候補の漏れ | — | 保留 |
| F19 | C-v.absent\_semantics（無い）、C-department.absent\_semantics（absent だけ） | C-v に absent\_semantics が無く、C-department は absent だけで null・空文字の意味が無い（on\_missing はどちらも拒否） | Minor | 観点 | 候補の漏れ | — | 保留 |
| F20 | C-rfc-roles.rationale・C-rfc-roles.revisit\_trigger（無い） | 理由の採点（抜き取り）で RR2 が否：却下の種類は「代替あり」で、前提（入口が全 IdP のロールを写す）はあるが崩れる条件（revisit\_trigger）が無い | Minor | 観点 | 理由の不備 | — | 保留 |
| F21 | template:00\_core#operational-metrics（付録 A） | 付録 A に、共通の検証ライブラリの採用率と版を誰がどの周期で測るかが無い（aud・typ の失敗の件数と発行側のスキーマの不一致はある） | Minor | 観点 | 候補の漏れ | — | 保留 |
| F22 | token\_types:AGENT\_AT・TASK\_AT の max\_delegation\_depth、C-act.enforced\_at（invoices）・C-act.note、template:profiles/P4\_ai\_agent\_delegation#delegation-depth・#chain-revocation | 深さの上限 3 の理由はケーススタディの規則だけで、この設計の経路（TASK\_AT で深さ 2）で 3 を許す理由と、根元の承認からの一括失効（タスクの取り消しで発行済みの TASK\_AT を止める手段）が P4 の欄として無い。深さ 2 以上は専門家に回す基準に当たるが、回した記録が無い | Major | 観点 | 候補の漏れ | — | 保留 |
| F23 | hops:H10・H11（upstream が H5 だけ）、C-tenant-id・C-user-id の carried\_in（TXN に無い） | ledger は TXN だけの要求（H10、ledger.read）も受けるが、H11 の upstream は H5 だけで、TXN の経路で app.user\_id・app.department を何から設定するか（TXN に user\_id・tenant\_id は無く sub だけ）、部署の引き直しをするかが書いてない。読み取りの経路の RLS の文脈の出どころが宣言されていない | Minor | テンプレート外 | 候補の漏れ | — | 保留 |
| F24 | token\_types:CLIENTASSERTION.note（RFC 10070 §4）、token\_types:KC\_AT.lifetime\_refs（NIST IR 8587 §5.3.1.1）、registry の refs 全般 | 根拠つきの行の抜き取り 3 件（CLIENTASSERTION の typ の RFC 10070 §4、KC\_AT の NIST IR 8587 §5.3.1.1、RT の RFC 9700 §4.14.2）のうち、前の 2 件はこのセッションで引用元を開いて確かめられなかった（RFC 10070 の番号と節が RFC 7523 の更新を述べるかは未確認）。3 件目は節は実在するが公開クライアント向けで、状況に当てはまらない（F16）。人のレビューで引用元を確かめる | Minor | 観点 | 理由の不備 | — | 保留 |

## 3. 対応の一覧

| 指摘 ID | 担当 | 期限 | 状態 | 対応の PR・コミット |
| --- | --- | --- | --- | --- |
| F01 | — | — | 未着手 | — |
| F02 | — | — | 未着手 | — |
| F03 | — | — | 未着手 | — |
| F04 | — | — | 未着手 | — |
| F05 | — | — | 未着手 | — |
| F06 | — | — | 未着手 | — |
| F07 | — | — | 未着手 | — |
| F08 | — | — | 未着手 | — |
| F09 | — | — | 未着手 | — |
| F10 | — | — | 未着手 | — |
| F11 | — | — | 未着手 | — |
| F12 | — | — | 未着手 | — |
| F13 | — | — | 未着手 | — |
| F14 | — | — | 未着手 | — |
| F15 | — | — | 未着手 | — |
| F16 | — | — | 未着手 | — |
| F17 | — | — | 未着手 | — |
| F18 | — | — | 未着手 | — |
| F19 | — | — | 未着手 | — |
| F20 | — | — | 未着手 | — |
| F21 | — | — | 未着手 | — |
| F22 | — | — | 未着手 | — |
| F23 | — | — | 未着手 | — |
| F24 | — | — | 未着手 | — |

## 4. 専門家に回した項目

| 基準の ID（escalation.md） | 行・欄 | 回した先 | 期限 | 結論 |
| --- | --- | --- | --- | --- |
| draft-spec | claims:C-txn・C-req-wl・C-tctx（spec\_version draft-ietf-oauth-transaction-tokens-11）、token\_types:TXN、design.md の 12. の Txn-Token の行 | 組織の認証基盤の担当 | — | 未了 |
| delegation-depth | token\_types:AGENT\_AT・TASK\_AT の max\_delegation\_depth 3、claims:C-act（入れ子の act）（F22） | 組織の認証基盤の担当 | — | 未了 |
| unverified-idp-behavior | design.md の 12. の CIBA の流れ（AGENT\_AT・I13。F07）と名前空間を出すマッパー（C-department・C-employee-id。F10）、RT の再利用の検知（F16） | 組織の認証基盤の担当（Keycloak の担当） | — | 未了 |

当てはまらなかった基準：custom-crypto・cross-tenant-exchange・baseline-unmet・jwe-key-management・regulated-data・new-token-type

## 5. カタログ・観点書・対応表に戻す事項

| 戻す先 | 中身 | 指摘 ID | issue・PR |
| --- | --- | --- | --- |
| 観点書 | volatility に、値の出どころの同期の間隔（人事→IdP）と、上流のトークンから写した値の古さ（KC\_AT→INT\_AT の連鎖）を含めたかを問う文言を q-freshness-mitigation・pa-02 に足す | F03 | — |
| 観点書 | 受け手が鮮度のために IdP の管理 API・ディレクトリを引くとき、その資格情報（サービスアカウント）の権限と寿命を問う問いを q-outside-catalog の例か新しい問いに足す | F06 | — |
| 観点書 | CIBA などの人の承認で高リスクの操作を許すとき、承認の時の認証の強さ・新しさと、承認の結果を返す経路の完全性を問う文言を q-step-up-path-coverage か q-approval-from-as に足す | F07 | — |
| カタログ | 「受け手が IdP の管理 API・外部のディレクトリを引くためのサービスアカウントのトークンの発行」と「CIBA の承認の結果の受け渡し」を発行・利用のイベントの候補にする | F06・F07 | — |
| lint | enforced\_at の service が consumers に無い行（C-iss の payment-worker）、jti\_policy.max\_age\_seconds が受け手の iat の受け入れの窓より短い行、absent\_semantics の無い独自クレーム（C-v）を機械で拾う | F04・F15・F19 | — |
| lint | claim\_request の問 5 の「確かめていない」と判定「共有クレームにする」・status active の組み合わせ、問 9 と on\_missing の食い違いを L72 の拡張で拾う | F09・F11 | — |
| lint | Full で使うと宣言したプロファイル・モジュールの欄が設計書に無いことを、冒頭の「使うプロファイル」と節の有無で拾う | F01 | — |
| 対応表 | slide:p06-step-up-approval の要件が、委任の承認（CIBA）の経路の認証の強さまで要件にしているかを確かめる（要件になっていなければ対応表に足す。要確認） | F07 | — |

## 6. 理由の採点（抜き取り）

| 行の ID | 列 | RR1 | RR2 | RR3 | RR4 | RR5 | RR6 | RR7 | 合否 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C-rfc-roles | rationale | 満 | 否 | 満 | 満 | 満 | 満 | 満 | 不合格 |
| C-rctx | rationale | 満 | 満 | 満 | 満 | 満 | 満 | 満 | 合格 |
| C-upn | rationale | 満 | 満 | 満 | 満 | 満 | 満 | 満 | 合格 |

- C-rfc-roles：RR2：却下の種類が「代替あり」（禁止ではない）なのに revisit\_trigger が無い。RR4 は slide:p03-auth0-namespace の名前と主張（Auth0 の予約名）の対応だけを見た（引用元は開いていない）
- C-rctx：前提（接続元の条件は入口だけで判断）と崩れる条件があり、要件が無いので問いが要らないと書いた。ただし入口が接続元をどう判断するかは設計書に無い（cf-09 は該当なし）。RR4 は引用の名前だけを見た
- C-upn：禁止の行で、規則の出どころ（slide:p03-entra-oid-tid）があるので崩れる条件は要らない。代わりに tid と oid で引く（alt C-user-id）。RR4 は引用の名前だけを見た

## 7. 点検状況

人による点検は未実施。このレビューは LLM のセッション 1 つが行った一次スクリーニングで、指摘の判定はすべて「保留」（人のレビュアーが採否を決めていない）。行の判定（承認・修正を求める・保留）も LLM のもの

人による点検は未実施（このレビューは LLM のセッションのもの。人のレビュアーの採否は未了）。

レビュアーの名前は自己申告です（エディターにはログインが無い）。本当の承認は GitHub の PR のレビューで行います。

## 8. 問いごとの回答

| 段 | 問い ID | 回答 | 理由（1 行） |
| --- | --- | --- | --- |
| 1. 定義 | dc-01 | No | C-department の volatility 330 は assumption の「人事→Keycloak の同期 1 時間ごと」を含まず、許容と受け入れの上限の比較が成り立たない（F03）。C-idp は usage display で認可に使わないのに INT\_AT に載る（F11） |
| 1. 定義 | dc-02 | Yes | 独自クレームに registered\_ref は無いが、各 claim\_request の問 3 に登録名・SCIM・IdP の既存の属性を探した記録がある |
| 1. 定義 | dc-03 | Yes | 独自クレームはすべて namespace https://claims.example.com/ の下。問 4 に予約名・IdP の属性名との照合がある |
| 1. 定義 | dc-04 | No | 問 5 で tenant\_id・user\_id・department・employee\_id・v・task\_id・approval\_id の 7 件が「確かめていない／記録が無い」（F09） |
| 1. 定義 | dc-05 | Yes | type は行ごとに 1 つ。ID（user\_id・employee\_id・task\_id・approval\_id）は string |
| 1. 定義 | dc-06 | Yes | 独自クレームの shape は single か array（C-roles）。区切り文字列は登録名の scope だけ |
| 1. 定義 | dc-07 | No | C-v に absent\_semantics が無い。C-department は absent だけで null・空文字の意味が無い（F19） |
| 1. 定義 | dc-08 | Yes | C-roles・C-department・C-idp・C-v は value\_normalization が空だが、各 claim\_request の問 10 に完全一致と大小の扱いがある |
| 1. 定義 | dc-09 | Yes | 照合は user\_id（UUID）・employee\_id。name・email は display で paired\_id は C-sub |
| 1. 定義 | dc-10 | Yes | authoritative\_writer は段階ごと、provenance は管理者・発行者の値。本人が書ける custom:role は却下。Keycloak の属性の編集権限の裏付けは F10 |
| 1. 定義 | dc-11 | Yes | max\_bytes・max\_items・overflow\_strategy が全行にある（act・authorization\_details は発行を失敗させる） |
| 1. 定義 | dc-12 | Yes | on\_missing は拒否（acr・auth\_time は拒否側の既定値）。issuers は段階ごとに 1 つ（② Keycloak・③ sts） |
| 1. 定義 | dc-gate | No | dc-04 が No の 7 件が status active で KC\_AT・INT\_AT 系に載っている（F09） |
| 1. 定義 | pa-01 | Yes | 9 件とも問 1 に受け手の名前と判断（orders の管理操作・docs の部門・payroll のキーなど）があり usage と合う |
| 1. 定義 | pa-02 | No | department の問 2 は 330 秒とするが、assumption の 1 時間ごとの同期と KC\_AT→INT\_AT の連鎖を数えていない（F03） |
| 1. 定義 | pa-03 | Yes | 問 3 に RFC 9068 の roles・SCIM・txn・auth\_req\_id との違いが書いてある |
| 1. 定義 | pa-04 | Yes | 問 4 に名前空間の中であること、Entra・Okta の同名属性・Auth0 の予約名との関係がある |
| 1. 定義 | pa-05 | No | 7 件の問 5 が「確かめていない」「記録が無い」「まだ試していない」（F09） |
| 1. 定義 | pa-06 | Yes | 全件「組織のオブジェクトの下」で namespace の style object と一致 |
| 1. 定義 | pa-07 | Yes | 文字列 1 つか文字列の配列（roles）。区切り文字列なし |
| 1. 定義 | pa-08 | Yes | ID は文字列（employee\_id は B22 に触れて文字列固定）。roles・idp は該当しないと明記 |
| 1. 定義 | pa-09 | No | idp の問 9 は「無ければ unknown と書いて続ける」だが、台帳 C-idp は on\_missing 拒否・enforced\_at「必須（無ければ拒否）」（F11） |
| 1. 定義 | pa-10 | Yes | 問 10 に小文字固定・完全一致・前後の空白の除去（employee\_id）がある |
| 1. 定義 | pa-11 | Yes | 書き手は Keycloak のマッパーと sts だけで本人は書けないと回答。Keycloak の利用者プロファイルの権限の裏付けは F10 |
| 1. 定義 | pa-12 | Yes | 照合は ID だけ。名前（表示名）は IDT だけと書いてある |
| 1. 定義 | pa-13 | Yes | 問 13 に上限と超えたときの受け手の拒否がある |
| 1. 定義 | pa-14 | Yes | 宛先ごとに絞る（roles は orders、department は docs、employee\_id は payroll）。tenant\_id・v は全トークンの理由がある |
| 1. 定義 | pa-15 | Yes | Keycloak（KC\_AT）と sts（INT\_AT 系）で段階が分かれ、台帳の authoritative\_writer の ②③ と一致 |
| 1. 定義 | pa-16 | No | department・roles は「docs／orders の 1 か所で確かめる」、employee\_id は payroll が共通部品を使えない、idp は照合しないと回答し、共通の検証部品で読むと言えない（F12） |
| 1. 定義 | pa-17 | Yes | 全件「ヘッダーに移さない」。X-User-\* は入口で変種を含めて捨てる（H2） |
| 1. 定義 | pa-18 | Yes | 全件に既定値で続行するモードを作らないと書いてある |
| 1. 定義 | pa-19 | Yes | 制限のクレームは読む受け手を限定。approval\_id の「読むのは invoices だけ」は consumers と食い違う（F11） |
| 1. 定義 | pa-20 | Yes | 問 20 は log\_policy・pii\_category と一致（department は値のまま・個人情報。基準との矛盾は F13） |
| 1. 定義 | pa-21 | Yes | user\_id・task\_id・approval\_id に act・承認 ID との関係がある |
| 1. 定義 | pa-22 | Yes | 問 22 の受け手が台帳の consumers と一致 |
| 1. 定義 | pa-23 | Yes | 受け手が先・発行者が後の移行の手順が各問 23 にある |
| 1. 定義 | pa-24 | Yes | department の「C-tenant-id と同じ」は参照先の問 24 に手順が実在する。employee\_id は期日と並行発行がある |
| 1. 定義 | pa-25 | Yes | Evaluate と schemas/\*.issuer.schema.json、#8 の拒否のテストが書いてある |
| 1. 定義 | pa-gate | No | 問 5 が答えられていない 7 件を「25 問すべてに答えた。共有クレームにする」と判定している（F09） |
| 1. 定義 | pa-trace | No | idp の問 9 と台帳の on\_missing、approval\_id の問 19 と consumers が食い違う（F11） |
| 1. 定義 | q-registered-synonym | No | STS のトークンの sub と user\_id は同じ値（C-sub の description）で、orders・invoices が両方で持ち主を照合する（F05） |
| 1. 定義 | q-reuse-standard-structure | Yes | task\_id（相関）は txn との単位の違い、approval\_id は authorization\_details との違いを問 3 に書いた。cnf・authorization\_details・act は既存の構造を使う |
| 1. 定義 | q-auth-context-semantics | Yes | auth\_time で 900 秒、acr で mfa を判断。C-iat の not\_meaning に auth\_time でないとある。sid はセッションの有無の引き直しに使う |
| 1. 定義 | q-scope-semantics | Yes | C-scope の not\_meaning に「利用者のロールではない」「金額の承認は authorization\_details」。宛先ごとに意味のあるスコープ |
| 1. 定義 | q-value-vocabulary | Yes | C-roles の value\_vocabulary と upstream\_issuer に IdP ごとの出どころと写し方（対応表にない値は捨てる）がある |
| 1. 定義 | q-role-explosion | Yes | roles は 4 語の粗いロール。文書・注文ごとの権限は持たない（not\_meaning） |
| 1. 定義 | q-identifier-choice | Yes | 利用者のキーは IdP ごとの不変の ID から引く user\_id。テナントは固定値 corp |
| 1. 定義 | ap-1-6 | Yes | upn・preferred\_username は却下（禁止）、email は display で照合しない |
| 1. 定義 | q-pairwise-external | 該当なし | 組織の外の受け手にトークンを出さない（2. の範囲の外：P6） |
| 1. 定義 | q-pairwise-unguessable | 該当なし | ペアワイズの sub を組織が作らない（外部の受け手が無い） |
| 1. 定義 | ap-2-1 | Yes | roles は max\_items 4、超過は受け手が拒否。Entra の超過はディレクトリで解決 |
| 1. 定義 | ap-2-2 | Yes | roles・department に引き直し（orders・ledger）の対策が書いてある。数値の誤りは F03 |
| 1. 定義 | ap-2-3 | Yes | 台帳の type・shape と schemas/INT\_AT\*.consumer.schema.json・TASK\_AT の型が一致（抜き取り 4 件） |
| 1. 定義 | ap-2-4 | Yes | 独自クレームはすべて名前空間の下。草案の req\_wl・tctx は L1b の warn で記録 |
| 1. 定義 | q-payload-readable | Yes | confidential\_from（browser・logs）の相手が、載るトークンの visible\_to に無い |
| 1. 定義 | q-confidential-reaches-reader | Yes | name・email は IDT（bff・idp）だけ、authorization\_details・employee\_id は logs に届かない（log\_policy jti だけ） |
| 1. 定義 | q-no-secret-or-raw-pii | Yes | 秘密は無い。authorization\_details の creditorAccount（user.financial）は承認の束縛に要る値で、invoice-mcp・invoices だけに届く |
| 1. 定義 | q-derived-value | Yes | 部門コード・粗いロールなど判定に要る値だけ。生の属性は載せない |
| 1. 定義 | q-baseline-kept | No | 3.2 は「ログに個人情報を残さない：満たす」だが、C-department は pii 個人情報で log\_policy 記録する（F13） |
| 2. 発行 | q-single-issuer | Yes | 段階ごとに 1 つの書き手。サービスは追記せず、作り直しは sts だけ |
| 2. 発行 | q-hook-failure | No | 受け手の拒否はある（required\_claims）が、I12・I25・I26 でマッパーが呼ばれるかが unknown のまま（R3b warn。F18） |
| 2. 発行 | q-size-limit | Yes | R8 で全種別の最悪のサイズとヘッダーの行を計算（最大 29%） |
| 2. 発行 | ap-1-7 | Yes | provenance は管理者・発行者の値。Cognito の custom:role は却下。Keycloak の属性の利用者による編集を禁じた設定の記録は無い（F10） |
| 2. 発行 | q-hook-adds-raw-pii | Yes | マッパーが足すのは部門コード・社員番号・組織 ID で、生年月日などは無い |
| 2. 発行 | q-minimal-per-recipient | Yes | 独自クレームは consumers の受け手宛てのトークンにだけ載る（H4〜H7 で絞る） |
| 2. 発行 | q-rar-per-audience | Yes | H14・H15 の authorization\_details は payment の type だけ |
| 2. 発行 | q-agent-own-identity | Yes | agent:expense の client\_id と private\_key\_jwt で、社員のトークンを借りない（C12） |
| 2. 発行 | q-agent-delegation-claims | Yes | AGENT\_AT・TASK\_AT で sub は社員、act・client\_id はエージェント・ツール |
| 2. 発行 | q-idp-capability-verified | No | CIBA の流れ・名前空間を出すマッパー・Keycloak の属性の編集権限に、版の公式文書か実測の出どころが無い（12. に未確認と書いたものを含む。F10・F07） |
| 2. 発行 | q-variant-comparison | Yes | 3.3 に B23 の型の攻撃が開くことと、DPoP ヘッダーを含む要求の全体のサイズの差がある |
| 2. 発行 | q-outside-catalog | No | outside\_enumeration は具体的だが、ledger・orders が Keycloak の管理 API を引くサービスアカウントの資格情報と、入口のディレクトリ参照の資格情報が目録・カタログに無く、I05 の回答と矛盾（F06）。TXN の読み取りの経路の DB の文脈も無い（F23） |
| 3. 伝搬 | cf-01 | Yes | 段階ごとの書き手が台帳にある。マッパーは発行のたびに再評価される（refresh\_reevaluation の実測） |
| 3. 伝搬 | cf-02 | Yes | KC\_AT・INT\_AT 系の required\_claims に独自クレームがあり、欠ければ拒否 |
| 3. 伝搬 | cf-03 | Yes | KC\_AT・EXT\_AT は入口で止め、sts の INT\_AT 系（corp-internal+jwt）に替える |
| 3. 伝搬 | cf-04 | Yes | H4〜H8・H15 で token\_type か aud が替わる。H10 は Txn-Token の受け渡しで問わない |
| 3. 伝搬 | cf-05 | Yes | 下流ほど aud・scope・寿命が上流以下。H15 は aud\_replacement と narrowing\_exception に理由 |
| 3. 伝搬 | cf-06 | Yes | TXN の transport は txn\_token\_header。H9 で Authorization では受けない |
| 3. 伝搬 | cf-07 | Yes | 全ホップの validates に checks がある（H11〜H13 は mode none で RLS・mTLS の確認） |
| 3. 伝搬 | cf-08 | Yes | ヘッダーへの転記は無く、H2 で x-user-\* を変種を含めて捨てる |
| 3. 伝搬 | cf-09 | 該当なし | 接続元の文脈で判断する要件が無い（C-rctx の却下の理由）。M\_authz\_pdp の欄も無い |
| 3. 伝搬 | cf-10 | Yes | U14 で sub・act・req\_wl・承認 ID・txn を別の項目で記録、トークン全文は残さない（jti だけ） |
| 3. 伝搬 | q-hop-narrowing | Yes | 交換は sts が担い、scope は要求と subject\_token の積（C-scope の assumption）。Keycloak の交換は OFF |
| 3. 伝搬 | q-hop-lifetime | Yes | 全ホップ 300 秒以下。INT\_AT を KC\_AT の残りの寿命以下にする記述は H4 だけで H5〜H7 に無い（鮮度の計算は F03） |
| 3. 伝搬 | q-single-aud-resource | Yes | AGENT\_AT は invoice-mcp、TASK\_AT は invoices の 1 つ。KC\_AT の 4 つは Keycloak が resource に対応しない理由と入口での絞り込みがある |
| 3. 伝搬 | ap-2-6 | Yes | invoice-mcp は AGENT\_AT を渡さず交換（C2）。orders は INT\_AT を下流へ渡さない |
| 3. 伝搬 | q-no-passthrough | Yes | 代替：P4 の delegation-policy の欄は無いが、hops の exchanger と C-may-act の理由に交換を許す相手・宛先・範囲がある |
| 3. 伝搬 | ap-2-5 | 該当なし | クレームをヘッダーに写すホップが無い（forwarded\_headers なし。U11 対象外） |
| 3. 伝搬 | q-unverified-claim-extraction | Yes | 全ホップ mode local で署名を検証してから読む。未検証の取り出しは無い |
| 3. 伝搬 | q-gateway-bypass-path | Yes | 入口を通らない経路（H10・H14・H15・H11〜H13）を図に書き、それぞれで検証・mTLS を確かめる |
| 3. 伝搬 | q-step-up-path-coverage | No | 高リスクの支払い（invoices.pay）を CIBA の承認で許すが、承認の時の認証の強さ・新しさ（acr・auth\_time）を求めず、AGENT\_AT にも載らない（F07） |
| 3. 伝搬 | q-txn-scope-fixed | Yes | TXN の scope は H9 以下、ledger が tctx の operation と scope を照合、改変せずに渡す（H10） |
| 3. 伝搬 | q-txn-required-claims | Yes | TXN の required\_claims に iat・aud・exp・txn・sub・scope・req\_wl があり、台帳の各行の carried\_in に TXN がある |
| 3. 伝搬 | q-claim-earliest-hop | Yes | approval\_id・authorization\_details を承認の時点の AGENT\_AT に載せ、TASK\_AT はその部分集合（B04） |
| 3. 伝搬 | ap-2-9 | Yes | AGENT\_AT・TASK\_AT は ES256 の署名、tenant\_id の照合、db\_lookup と exp の失効、jti の記録 |
| 3. 伝搬 | q-internal-delegation-token | Yes | 目録に署名・寿命 300 秒・失効・ログの列がある（tenant\_binding の列は無く tenant\_id の照合で代替） |
| 3. 伝搬 | ap-2-7 | Yes | エージェントは CIBA で act つきの AGENT\_AT を得て、社員のトークンを借りない |
| 3. 伝搬 | q-delegation-depth-and-revocation | No | max\_delegation\_depth 3 の理由はケーススタディの規則だけで、P4 の delegation-depth・chain-revocation の欄が無い。深さ 2 以上の専門家の確認も無い（F22） |
| 3. 伝搬 | q-idp-diff-absorbed | Yes | 内側のサービスは sts の組織の名前空間だけを読む。IdP の独自クレームは upstream\_issuer にだけ書いた |
| 3. 伝搬 | q-token-not-in-url | Yes | transport に URL・クエリの種別は CODE だけ。PAR で request\_uri。長い接続は使わない（U23） |
| 4. 検証 | q-shared-validator | No | M\_token\_validation の欄が無い。payroll は共通部品を使えない（employee\_id の問 16）（F01・F12） |
| 4. 検証 | ap-1-1 | Yes | 全 JWT の行に alg\_allowlist（RS256 か ES256 の 1 つ） |
| 4. 検証 | ap-1-2 | Yes | 全ホップの validates が local の署名検証で、デコードだけの経路は無い |
| 4. 検証 | q-validate-before-read | Yes | 代替：M\_token\_validation#validation-order は無いが、user\_id の問 18 に検証前に読むのを禁じるとある |
| 4. 検証 | ap-1-3 | Yes | aud は全 AT の required\_claims。KC\_AT は入口が「呼び出し先の API を含む」と azp=portal で確かめる（入口自身は aud に無い） |
| 4. 検証 | ap-1-4 | Yes | issuers の許可リスト。Entra は固定のテナントの iss だけ |
| 4. 検証 | ap-1-5 | Yes | key\_source は iss のメタデータの jwks\_uri か設定した jwks\_uri で、ヘッダーの鍵は reject |
| 4. 検証 | ap-1-8 | Yes | exp は必須（EXT\_AT は目録に required\_claims が無いが C-exp の gateway が必須）、ずれ 30 秒 |
| 4. 検証 | q-typ-distinguishes | Yes | typ が at+jwt・corp-internal+jwt・txntoken+jwt・logout+jwt・dpop+jwt で分かれ、AGENT\_AT と TASK\_AT は aud で分かれる |
| 4. 検証 | q-required-rejected | Yes | 必須の欠落は拒否。groups の超過は入口がディレクトリで埋めてから当てる（3.2） |
| 4. 検証 | q-no-unverified-passthrough-mode | Yes | 代替：library-config の欄は無いが、全 claim\_request の問 18 に検証の無効化・既定値で続行のモードが無いとある |
| 4. 検証 | q-consumer-expression | Yes | enforced\_at は完全一致、on\_missing は拒否か拒否側の既定値（acr は pwd）。欠落で通す既定値は無い |
| 4. 検証 | q-nested-jwt-both-layers | 該当なし | JWE を使わない（全行 jwe used false） |
| 4. 検証 | q-unwrapped-value-authz | Yes | 代替：integrity\_until の列は無いが、H11 に app.department を設定するのは ledger だけとある。ヘッダーへの写しは無い |
| 5. 認可 | q-object-level-authz | No | orders・invoices が sub と user\_id の両方で持ち主を照合し、キーが 1 つに決まっていない。M\_authz\_pdp#object-level も無い（F05） |
| 5. 認可 | q-tenant-data-match | 該当なし | テナントは corp 1 つ（lite\_criteria の multitenant false）。データはテナントで分けない |
| 5. 認可 | q-writer-distinguished | Yes | 本人が書ける custom:role・upn を却下し、管理側の値だけで認可 |
| 5. 認可 | q-validity-not-authz | Yes | scope・roles・持ち主・承認の内容を照合し、有効性だけで許さない |
| 5. 認可 | q-original-principal | Yes | orders→ledger は TXN の sub（社員）で判断し、orders の権限で依頼しない |
| 5. 認可 | q-authorize-service-and-user | Yes | H10 で呼び出し元（mTLS の SPIFFE ID）と社員（sub）をそれぞれ認可 |
| 5. 認可 | q-scope-and-role | Yes | orders は scope orders.read と roles、ledger は scope と acr、docs は scope と部門 |
| 5. 認可 | q-access-context-from-pep | 該当なし | IP・端末で判断する要件が無い（C-rctx）。X-Forwarded-For も使わない |
| 5. 認可 | q-step-up-by-rs | Yes | ledger が acr・auth\_time を見て insufficient\_user\_authentication を返す（付録 B・H5） |
| 5. 認可 | q-approval-from-as | Yes | 代替：P4#human-approval は無いが、sts が CIBA で承認を取り、invoices が承認の DB と本文を照合（C-approval-id）。承認の強さは F07 |
| 5. 認可 | q-cross-tenant-identity | Yes | 名寄せをしない（I18）。idp は認可・照合に使わない |
| 5. 認可 | q-operator-act | 該当なし | 運用者の操作は範囲外（2.2。I19 の Impersonate を使わない） |
| 5. 認可 | q-break-glass | 該当なし | 緊急時の特権は範囲外（2.2） |
| 5. 認可 | cd-01 | Yes | 代替：H11 に DB の文脈を設定するのは ledger だけとある |
| 5. 認可 | cd-02 | Yes | 代替：H11 の note に取引ごとに set\_config（第 3 引数 true） |
| 5. 認可 | cd-03 | 該当なし | DB は PostgreSQL（SQL Server を使わない） |
| 5. 認可 | cd-04 | Yes | 認可に使う属性の provenance は管理者・発行者の値（Keycloak の裏付けは F10） |
| 5. 認可 | cd-05 | 該当なし | DB のロールを選ぶクレームが無い（サービスの資格情報で接続） |
| 5. 認可 | cd-06 | No | RLS をすり抜ける主体（スーパーユーザー・BYPASSRLS・所有者・SECURITY DEFINER）の扱いが無い。FORCE だけ（F02） |
| 5. 認可 | cd-07 | Yes | app.user\_id は不変の UUID（C-user-id） |
| 5. 認可 | cd-08 | Yes | connection\_max\_lifetime 1800 秒と取引ごとの注入（9.1 の DB の層） |
| 5. 認可 | cd-09 | Yes | 監査の列に app.user\_id を書く（H11） |
| 5. 認可 | cd-10 | No | 文脈なしで 0 行はあるが、DDM・RLS のほかの最小権限の記述が無い（F02） |
| 5. 認可 | cd-11 | No | データ層の設定を試験で確かめる計画が無い。M\_data\_layer の欄が無い（F02） |
| 5. 認可 | q-db-context-writers | No | 同じ取引で流れる SQL が ledger のアプリの SQL に限られるか、RESET ROLE などで戻せないかが書いてない（F02） |
| 5. 認可 | q-sql-tenant-predicate | 該当なし | テナントは 1 つでテナントの条件を要しない。部署の分離は RLS（FORCE）で行う |
| 5. 認可 | q-db-context-parameterized | Yes | 代替：H11 に set\_config（第 3 引数 true）で設定とある（SET LOCAL の文字列連結ではない） |
| 5. 認可 | q-ddm-rls-only | No | RLS のほかの最小権限・監査の併用の方針が無い（監査の列だけ）（F02） |
| 6. 運用 | q-four-lifetimes-written | Yes | 9.1・9.2・9.3 と生成の表の 4 層が別の欄にある |
| 6. 運用 | q-lifetime-rationale | No | 5.1 は上限の数値だけで、300 秒を剥奪の速さから導いた理由と代償（リフレッシュの負荷・IdP の停止）の比較が無い（F17） |
| 6. 運用 | q-session-rt-bounds | Yes | BFFSESSION・SSO・RT に idle 1800 と最大 36000（24 時間以下） |
| 6. 運用 | q-rt-policy-by-client | No | 機密の BFF の RT の方式の根拠に公開クライアント向けの RFC 9700 §4.14.2 を引く。再利用の検知も未確認（F16） |
| 6. 運用 | q-freshness-mitigation | No | C-department・C-roles の受け入れの最大と許容の比較が、1 時間ごとの同期と KC\_AT→INT\_AT の連鎖を含まない（F03） |
| 6. 運用 | q-refresh-reevaluated | Yes | Keycloak のリフレッシュでのマッパーの再実行は実測（keycloak.refresh\_reevaluation）。外部の IdP は毎回読み直す（9.2） |
| 6. 運用 | q-revocation-delivery | Yes | 種別ごとの手段と最悪の秒数が 9.1 にある。即時が要る操作は db\_lookup |
| 6. 運用 | q-external-user-deprovision | No | グループ会社の社員の停止は EXT\_AT の exp（5430 秒）まで届かず、利用者単位の止め方が無い（F08） |
| 6. 運用 | q-relies-on-at-expiry | Yes | 重要な操作は sid と部署の引き直し、セッションは Back-Channel Logout。INT\_AT のキャッシュは固定の 60 秒 |
| 6. 運用 | q-long-running | No | payment-worker について、H12・H13 は「トークンを持たない」、C-exp は「TXN の寿命を超えたら TTS から取り直す」と食い違う（F04） |
| 6. 運用 | q-system-actor-no-fake-sub | No | payment-worker が自分の ID で TTS から取り直す TXN の sub が何か書いてない。C-sub は「TXN の sub を処理の主体として記録」（F04） |
| 6. 運用 | q-agent-short-lived-no-rt | Yes | AGENT\_AT・TASK\_AT は 300 秒で refresh なし（RT を出さない） |
| 6. 運用 | q-copies-outlive | Yes | DB の接続 1800 秒、INT\_AT のキャッシュ 60 秒、ディレクトリの結果 60 秒、イベントは処理前に承認を引く |
| 6. 運用 | q-deprecated-deadline | Yes | C-employee-id に sunset\_on 2027-03-31・alt C-user-id・consumers\_migration がある |
| 6. 運用 | q-change-order | Yes | 9.3 と各問 23・24 に受け手が先・発行者が後の手順 |
| 6. 運用 | q-key-rotation | Yes | JWKS から取り、未知の kid は 300 秒に 1 回・負のキャッシュ 300 秒、公開 3900 秒前・廃止 330 秒後 |
| 6. 運用 | q-dependency-outage | No | ledger・orders が引く Keycloak の管理 API の障害時の挙動が無い。M\_idp\_keycloak#limits の欄も無い（F01） |
| 6. 運用 | ap-2-8 | Yes | 目録の log\_policy は jti だけ、台帳はハッシュか許した値 |
| 6. 運用 | q-token-logging | No | 記録する HTTP ヘッダーの許可リスト・HAR からトークンを除く手順が無い（M\_privacy\_minimization#audit-log が無い。F01） |
| 6. 運用 | q-audit-log-protected | No | 監査ログの保護と保存期間の方針が無い（F01） |
| 6. 運用 | q-audit-correlation | Yes | 代替：P4#audit-correlation は無いが、U14 に sub・act・req\_wl・承認 ID・txn を別の項目で残すとある |
| 6. 運用 | q-trace-id-trust | No | 監査は txn を使うが、traceparent の扱いが書いてない（P5#txn-token の欄が無い。F01） |
| 6. 運用 | q-scope-elevation-logged | No | U27 に CIBA で昇格とあるが、相関 ID つきの記録が無い（P4#tool-scopes が無い。F01） |
| 6. 運用 | q-operational-metrics | No | 付録 A に共通の検証ライブラリの採用率と版が無い（F21） |
| 6. 運用 | q-lint-workaround | Yes | upstream の無い H3・H8・H9・H14 に理由がある。req\_wl・tctx は #6 の規則の変更として渡した（12.） |
| 6. 運用 | q-evidence-attribution | No | 引用元を開いて確かめていない。RFC 10070 §4（CLIENTASSERTION の typ）、NIST IR 8587 §5.3.1.1 は要確認（F24） |
| 6. 運用 | q-limit-consistency | No | 同じ事実の記述の食い違いが複数（JWE の注記・3. の設定の一覧・9.1 の部署の出どころ・DPoP の jti の保持など。F14・F15） |

## 9. 確認済みの行と提出の記録

「確認済み」は、レビュアーがその行の内容を見たという印で、承認ではありません。判定（承認／変更を依頼／コメントのみ）は、提出ごとにレビュー全体に 1 つ付けます。印と判定は、行の内容のハッシュ（RFC 8785 JCS の SHA-256、`tools/row_hash.py`）に結びつきます。記録の後に行が変わると「前回の確認から変更あり」になり、承認は古い承認になります。ハッシュはその行の値だけを見ます（参照するトークン種別・経路の行、25 問の回答、design.md の本文を変えても変わりません）。下の「今の行との対応」は、このレポートを生成した時のクレーム一覧と比べた状態です。

| 日時 | 判定 | 総評 | 確認済みの行数 | コメント数 |
| --- | --- | --- | --- | --- |
| 2026-11-23 | コメントのみ（移行） | claims-review/1 の記録から移行した。v1 には全体の判定が無い（行ごとの判定は viewed の migrated\_from に残した） | 48 | 24 |

コメントの状態：未提出 0・未解決 24・解決済み 0

| 行 | 確認した日時 | 今の行との対応 | 移行前の判定とコメント |
| --- | --- | --- | --- |
| catalog\_answers:I05 | 2026-11-23（LLM） | 一致（確認したときのまま）（e46535975ee3） | 修正を求める：管理 API のサービスアカウントの発行と矛盾（F06） |
| catalog\_answers:I12 | 2026-11-23（LLM） | 一致（確認したときのまま）（a7e80fb9c4c7） | 修正を求める：マッパーの呼ばれ方が unknown（F18） |
| claims:C-acr | 2026-11-23（LLM） | 一致（確認したときのまま）（2b24afb5def2） | 承認：組織の語彙への正規化、欠落は pwd（拒否側） |
| claims:C-act | 2026-11-23（LLM） | 一致（確認したときのまま）（7a61f44d9afb） | 保留：深さ 3 と一括失効は専門家の確認待ち（F22、delegation-depth） |
| claims:C-approval-id | 2026-11-23（LLM） | 一致（確認したときのまま）（84464fd47e83） | 修正を求める：問 5 未確認（F09）、問 19 と consumers の食い違い（F11） |
| claims:C-aud | 2026-11-23（LLM） | 一致（確認したときのまま）（d35d0b164c6d） | 承認：宛先ごとに 1 つ、KC\_AT の 4 つは理由と入口の絞り込みあり |
| claims:C-auth-time | 2026-11-23（LLM） | 一致（確認したときのまま）（2838819ade6c） | 承認：ledger が max\_age 900 で照合 |
| claims:C-authorization-details | 2026-11-23（LLM） | 一致（確認したときのまま）（372175d7a2d0） | 承認：承認の内容と本文の照合、宛先ごとに type を絞る。載るトークンの注記の食い違いは目録側（F14） |
| claims:C-client-id | 2026-11-23（LLM） | 一致（確認したときのまま）（3db2756a2668） | 承認：sts が private\_key\_jwt で確かめた値、受け手ごとの照合あり |
| claims:C-cnf | 2026-11-23（LLM） | 一致（確認したときのまま）（1015b4f63af0） | 承認：DPoP の cnf.jkt と proof の照合が両受け手にある（PR #52 の点検の後に追記：enforced\_at の「jti を受け入れる期間の間覚えて」は、保留中の F15 の食い違いの片方。承認は cnf.jkt の照合の有無についてだけ） |
| claims:C-department | 2026-11-23（LLM） | 一致（確認したときのまま）（f3e9e1cf3976） | 修正を求める：volatility が 1 時間の同期を含まない（F03）、問 5（F09）、編集権限（F10）、ログの個人情報（F13）、absent\_semantics（F19） |
| claims:C-dpop-ath | 2026-11-23（LLM） | 一致（確認したときのまま）（b4093cbd774b） | 承認：資源サーバーでの AT のハッシュの照合 |
| claims:C-dpop-htm | 2026-11-23（LLM） | 一致（確認したときのまま）（0c82c7eed30d） | 承認：要求のメソッドと照合 |
| claims:C-dpop-htu | 2026-11-23（LLM） | 一致（確認したときのまま）（df5cd0e41b82） | 承認：URI の比較の規則と書き換えの前提がある |
| claims:C-dpop-nonce | 2026-11-23（LLM） | 一致（確認したときのまま）（08a18cf73775） | 承認：書き手を IDT の nonce と分けた |
| claims:C-email | 2026-11-23（LLM） | 一致（確認したときのまま）（4b7c23b2ff5f） | 承認：表示だけで照合に使わない |
| claims:C-employee-id | 2026-11-23（LLM） | 一致（確認したときのまま）（ef15ad92c67a） | 修正を求める：問 5 未確認（F09）、Keycloak の属性の編集権限（F10） |
| claims:C-events | 2026-11-23（LLM） | 一致（確認したときのまま）（955bc7dd9c7b） | 承認：ログアウトトークンの取り違えの防止 |
| claims:C-exp | 2026-11-23（LLM） | 一致（確認したときのまま）（ff6aaa5fba51） | 修正を求める：payment-worker が TXN を取り直す行が H12・H13 と矛盾（F04） |
| claims:C-iat | 2026-11-23（LLM） | 一致（確認したときのまま）（79d209026615） | 修正を求める：DPoP の iat ±60 秒と jti の保持 90 秒の食い違い（F15） |
| claims:C-idp | 2026-11-23（LLM） | 一致（確認したときのまま）（38abea532304） | 修正を求める：問 9 と on\_missing の食い違い、認可に使わないのに載せる理由（F11） |
| claims:C-iss | 2026-11-23（LLM） | 一致（確認したときのまま）（f032ed2fb6a8） | 修正を求める：payment-worker の enforced\_at がトークンを持たない設計と矛盾、consumers にも無い（F04） |
| claims:C-jti | 2026-11-23（LLM） | 一致（確認したときのまま）（d7a7fdb04727） | 修正を求める：DPoP の jti の保持期間が受け入れの窓より短い（F15） |
| claims:C-name | 2026-11-23（LLM） | 一致（確認したときのまま）（57e51b652b9e） | 承認：表示だけ、IDT は BFF に留める |
| claims:C-nonce | 2026-11-23（LLM） | 一致（確認したときのまま）（999cb25cf0be） | 承認：IDT の再送の拒否と LOGOUT の nonce の拒否 |
| claims:C-rctx | 2026-11-23（LLM） | 一致（確認したときのまま）（61d5542124b0） | 承認：理由の採点で合格 |
| claims:C-req-wl | 2026-11-23（LLM） | 一致（確認したときのまま）（0894fae2ef38） | 保留：草案のクレーム・未登録の名前（draft-spec に回す） |
| claims:C-rfc-roles | 2026-11-23（LLM） | 一致（確認したときのまま）（87e5c90ac974） | 修正を求める：revisit\_trigger が無い（F20） |
| claims:C-roles | 2026-11-23（LLM） | 一致（確認したときのまま）（71505e15b4ca） | 修正を求める：鮮度の計算が KC\_AT の古さを含まない（F03） |
| claims:C-scope | 2026-11-23（LLM） | 一致（確認したときのまま）（85bae016c79e） | 承認：宛先・取引ごとに絞り、authorization\_details との役割分担が not\_meaning にある |
| claims:C-sid | 2026-11-23（LLM） | 一致（確認したときのまま）（e4135d52d20f） | 修正を求める：引き直しに使うサービスアカウントの資格情報が目録・カタログに無い（F06） |
| claims:C-sub | 2026-11-23（LLM） | 一致（確認したときのまま）（2b7bb978f728） | 修正を求める：持ち主の照合を user\_id と二重にしている（F05）、payment-worker の行（F04） |
| claims:C-task-id | 2026-11-23（LLM） | 一致（確認したときのまま）（26eee1cca938） | 修正を求める：問 5 未確認（F09） |
| claims:C-tctx | 2026-11-23（LLM） | 一致（確認したときのまま）（d9fb268c4398） | 保留：草案のクレーム（draft-spec に回す） |
| claims:C-tenant-id | 2026-11-23（LLM） | 一致（確認したときのまま）（069a34e32cdf） | 修正を求める：問 5 が未確認のまま共有クレームにした（F09） |
| claims:C-txn | 2026-11-23（LLM） | 一致（確認したときのまま）（da218550403b） | 保留：草案のクレーム（draft-spec に回す） |
| claims:C-upn | 2026-11-23（LLM） | 一致（確認したときのまま）（106ea3a0a9d4） | 承認：理由の採点で合格（禁止の行） |
| claims:C-user-id | 2026-11-23（LLM） | 一致（確認したときのまま）（03ff833eb5e1） | 修正を求める：sub との二重のキー（F05）、問 5 未確認（F09）、Keycloak の属性の編集権限の裏付け（F10） |
| claims:C-v | 2026-11-23（LLM） | 一致（確認したときのまま）（d90a310249ce） | 修正を求める：問 5 未確認（F09）、absent\_semantics が無い（F19） |
| hops:H11 | 2026-11-23（LLM） | 一致（確認したときのまま）（b9d2bc7e23a4） | 修正を求める：RLS のすり抜け・最小権限・試験（F02）、TXN の経路の文脈（F23） |
| hops:H12 | 2026-11-23（LLM） | 一致（確認したときのまま）（1ecbf87d713f） | 修正を求める：ledger が持たない approval の ID をイベントに入れる（F04） |
| hops:H13 | 2026-11-23（LLM） | 一致（確認したときのまま）（02b288834ceb） | 修正を求める：台帳の payment-worker の行と矛盾（F04） |
| hops:H15 | 2026-11-23（LLM） | 一致（確認したときのまま）（38877ac18095） | 承認：aud の置き換えの例外に理由、scope・寿命・独自クレームは上流以下（PR #52 の点検の後に追記：この交換は、保留中の Major の指摘 F22（委任の深さと一括失効）の対象。承認はホップの絞り込みについてだけ） |
| token\_types:AGENT\_AT | 2026-11-23（LLM） | 一致（確認したときのまま）（ee31c2200bc1） | 修正を求める：承認の時の認証の強さ（F07）、jwe の注記（F14）、深さ（F22） |
| token\_types:DPOP | 2026-11-23（LLM） | 一致（確認したときのまま）（e7e807c55fa0） | 修正を求める：jti の保持期間と iat の窓（F15） |
| token\_types:EXT\_AT | 2026-11-23（LLM） | 一致（確認したときのまま）（575a2fa05a66） | 修正を求める：利用者単位の停止の手段が無い（F08） |
| token\_types:RT | 2026-11-23（LLM） | 一致（確認したときのまま）（a7cfb402d4b0） | 修正を求める：機密クライアントに公開クライアントの根拠（F16） |
| token\_types:TXN | 2026-11-23（LLM） | 一致（確認したときのまま）（94e30ff259a7） | 保留：草案のトークン（draft-spec）。log\_policy と required\_claims の jti（F14） |

計 48 行：一致 48・前回の確認から変更あり 0・一覧に無い 0
