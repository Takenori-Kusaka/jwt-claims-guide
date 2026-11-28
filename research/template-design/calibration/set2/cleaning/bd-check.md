# 初回の繰り返し欠陥（BD）が 2 組目の対照に再び出るか

ここで確かめたのは、32 の欠陥の族がそれぞれ再び出ているかどうかだけです。設計そのものの良し悪しは判断していません。
判定 A の族は m-cc（P4）、判定 B の族は m-cd（P5）で確かめました。場所は各対照の `design.md` の節の見出しか、台帳・目録・ホップの ID で示します。

## 本表（32 族）

| 初回の ID | 初回の欠陥（短く） | 2 組目の対照 | 判断 | 場所・理由 |
| --- | --- | --- | --- | --- |
| A-BD1 | 予約の返金の非同期の経路が台帳に無い（long_running・ホップ・q-long-running） | m-cc | 無い | `ORDER_TOOL_AT.long_running`、`hops.yaml` の H13・H14、2.2「予約の発注の実行」、6. の UC4、3. の「予約の実行で交換し直さない」 |
| A-BD2 | 人事連携の遅れが未計測で、警報の時間が要求を超え、責任者の判断に任せている | m-cc | 無い | 2.2「人事連携」と 9.2 の表・元のデータからの経路：重要な操作は aoba-pdp が人事の台帳を直接引く（60 秒）ので、hr-sync の遅れは REQ-08 の判断に入らない。登録から確定までは 3.1 の見送りの行（人事の手順、月報で確かめる） |
| A-BD3 | 承認の消費の失敗時（結果不明で未使用に戻す・消費後の落ち・冪等キー） | m-cc | 無い | 3.1 重点「操作ごとの承認…1 回だけ使う」、付録 D の P4 の 5.「消費の競合と再送」（自動で未使用に戻さない、同じ発注 ID で再試行、使用済み・未確定を失効） |
| A-BD4 | ワークロードの ID の発行者（SPIRE）が idp に無く、鍵の持ち主・漏えい時の手順が無い | m-cc | 無い | 付録 D の M_token_validation の 8. の wl-ca の行（鍵の持ち主・中間の CA の漏えいは 60 分）、`catalog_answers.yaml` の outside_enumeration（wl-ca の 2 行）、3.1「wl-ca の中間の CA の鍵の漏えい」 |
| A-BD5 | 予約の実行：承認を消費する時点、委任の記録の書き手と完全性、実行の経路 | m-cc | 無い | 2.2「予約の発注の実行」（DB アカウントの権限、変更の記録の表、委任の世代）、3.1「予約の実行で…交換し直すこと」、H13・H14、6. の UC4 の q-holder |
| A-BD6 | 「権限の元データを書けるのは X だけ」を管理者権限で実現と称する（書き手を数え切れていない） | m-cc | 無い | 2.2「管理用の口」（aoba-as の管理の画面では社員番号の属性を書けない。書けるのは hr-sync の証明書の API だけ）、9.2 の元のデータからの経路、3.1「DB の管理者の直接の書き込み」「両台帳の書き込みの口」 |
| A-BD7 | 金額の閾値が 1 要求ごとで、分割・累計の扱いが無い | m-cc | 無い | REQ-05、3.1 重点「承認の要否を…部屋ごとの累計で決める」（部屋の行の排他の錠、電話での発注も累計に入れる） |
| A-BD8 | 旧いマクロの道具がトークンをどう得るか（主体・client_id・cnf）が無い | m-cc | 該当なし | 旧い経路が無い（11. の U29：新しく作る仕組みで、移行期間の旧い口が無い） |
| A-BD9 | authorization_details の内側の型がスキーマに無く、value_normalization も無い | m-cc | 無い | 3.1 の見送り「生成のスキーマで authorization_details のメンバーの型を表すこと」（理由と確かめ方つき）、付録 D の P4 の 5.「承認の内容」（メンバーの型・書式）、`C-authorization-details.value_normalization`（NFC・完全一致） |
| A-BD10 | 代わりに実行する者がいるのに q-actor を「不要」とした | m-cc | 無い | 6. の UC1〜UC4 は q-actor をすべて「要る」とした。UC4 では実行した order-scheduler と予約した行為者の両方を残す |
| A-BD11 | sender_constraint の理由（「サーバーの中だけ」）が holder・3.1 と食い違う | m-cc | 無い | `issuance_profile.sender_constraint.rationale`、目録の CONSOLE_AT・CONSOLE_RT の持ち手（repair-console のサーバー）、3.1「CONSOLE_AT・CONSOLE_RT の送信者制約」。エージェントには渡さず、REPAIR_DELEG_AT は別の見送りの行に書いた |
| A-BD12 | 承認の入口（ログイン・トークン・承認者のロール）が図・目録・カタログに無い | m-cc | 無い | 2. の図（C→AP の APPROVAL_AT）、目録の `APPROVAL_AT`、6. の UC3、H12、付録 B、2.1 の「上長」の行 |
| A-BD13 | C-sub の id_scheme が uuid なのに、ワークロードを sub にした JWT がある | m-cc | 該当なし | sub にワークロードを入れる JWT が無い（`WL_IDENTITY_JWT` は却下）。ワークロードの URI は `C-act` の act.sub に入り、C-sub は利用者の uuid だけ |
| A-BD14 | 証明書の更新の後に、古い証明書に束縛したトークンが合わなくなる。交換し直す決まりが無い | m-cc | 無い | 付録 D の M_sender_constraint の 4.「証明書・鍵の更新」（共通のクライアント部品が証明書とトークンを組で持つ）、9.1 の生成の表の `cnf` の行 |
| A-BD15 | 鍵の漏えいの目標と、JWKS の TTL・既知の kid では取り直さない・失敗時は最後の値、が両立しない | m-cc | 無い | 付録 D の M_token_validation の 8.・9.（TTL 600 秒、失敗時は拒否、作業 5 分＋キャッシュ 10 分＝15 分）、3.1「JWKS を取り直せないとき…」、5.1 の寿命の数字の出どころ |
| A-BD16 | 交換のサービスが、依存先が止まったときに交換を止めるかが無い | m-cc | 無い | 3.1 の見送り「頼る先が止まったときに通すこと（止める側に倒す）」（aoba-as のイントロスペクション・aoba-pdp・修繕依頼の台帳・approval-svc・agent-sts）、付録 D の M_authz_pdp の 5. の末尾、付録 A の応答の失敗の行 |
| A-BD17 | scope の許容が要求でなく設計の最悪値の写しで、要求を超える | m-cc | 無い | 9.2 の `C-scope`：許容 600 秒は REQ-08 の「そのほかの操作は 10 分」から取り、最悪は 390 秒 |
| A-BD18 | 承認の要らない操作の冪等キーを誰が作るかが無い | m-cc | 無い | 3.1 重点「重複の実行を、業務の ID で防ぐ」（発注 ID は下書きのときに order-tool が採番する。支払い・解錠・連絡も同じ行に書いてある） |
| B-BD1 | 「Txn-Token の scope は上流の AT の部分集合」が誤り | m-cd | 無い | 1. の CI の結果で L16 の scope の warn が無い（aud の warn だけ）。`C-scope.rationale`・10. の行・9.2：AT の scope は TTS が絞るときの上限としてだけ使う。H22・H24 の scope も上流を超えない |
| B-BD2 | 追加認証を BFF だけで確かめていて、承認の記録・対応表を書く API が設計に無い | m-cd | 無い | 付録 B（payment-svc・as-admin-api・assessment-svc が TXN_STAFF の acr・auth_time で確かめる）、3.1 重点「追加の認証…」（承認の記録を書けるのは payment-svc の承認の API だけ）、H23・H26。役割は社員の台帳から引き、経路の表は IT 基盤部の変更の手続き（`C-scope` の note） |
| B-BD3 | configurable_by が platform だけで、外部 IdP の管理者などが漏れる | m-cd | 無い | `C-sub.authoritative_writer` の stage ① 代理店の IdP（configurable_by: client）、3.1 の重点「代理店の AT を…束縛し」（IdP の管理者は担当者を作れるが代理店コードは変えられない）、`C-agency-code` の note |
| B-BD4 | 図・ホップに無い書き込みの経路があり、「X だけが書く」と食い違う | m-cd | 無い | 2. の図（as-admin-api→shirogane-as・shirogane-sso・staff-console）と「トークンを運ばない内部の呼び出し」の表、2.2「データベースの直接の修正」、9.2 の「元のデータからの経路」（DB の管理者の行を含む） |
| B-BD5 | tctx の内側の型・正規化が無く、スキーマが成り立たない（object＋文字列の enum） | m-cd | 無い | 3.1 の見送り「生成の JSON Schema に tctx の内側の型を入れない」、付録 D の P5 の 2. の tctx の 9 項目の表、`C-tctx.value_normalization`。`schemas/TXN_TOKEN.issuer.schema.json` の tctx は type: object だけで、enum は無い |
| B-BD6 | C-aud の説明は userinfo が入るとするのに、目録とスキーマは aud 1 つ | m-cd | 無い | `C-aud.rationale`：「AT には userinfo を宛先に入れない（UserInfo を呼ばない）ので、値は 1 つ」 |
| B-BD7 | SET の却下理由・3.1（RT の取り直しで届く）が 9.2 の値と矛盾 | m-cd | 無い | `SECURITY_EVENT_TOKEN`・`LOGOUT_TOKEN` の rationale と assumption（最大 750 秒）が、3.1「Back-Channel Logout・SSF/CAEP」と 9.1 の「代理店の担当者」の行（750 秒）とそろっている |
| B-BD8 | 作り直しのたびにロールで絞り直すとするが、ロールの出どころが無い | m-cd | 無い | 9.2 の `C-scope`（PAY_MSG_CTX）の行：TTS が社員の台帳を引き直す。2.2「支払いの指示」、付録 D の P5 の 4. |
| B-BD9 | M_token_validation 6. に、業務の期限と、別の時計の値の比べ方が欠けている | m-cd | ある | 付録 D の M_token_validation の 6. に、セキュリティキーの登録の番号の 24 時間（2.2。shirogane-sso が比べる）と、PAY_MSG_CTX の期限（H21 の payment-worker・TTS が比べる。寿命 3600 秒）が無い。PAY_MSG_CTX の exp − iat の上限も書いていない |
| B-BD10 | TTS の依存先が止まったときの倒し方と、可用性の目標の数値が無い | m-cd | 無い | 3.1 重点「TTS・状態の参照・JWKS が応えないときは拒む」（部品ごとの目標値と積の 99.92%・99.93%）、2. の「トークンを運ばない内部の呼び出し」の「止まったとき」の列 |
| B-BD11 | ロールを剥奪したときの最悪（AT＋Txn-Token の連鎖）が volatility を超え、lint は種別ごとにしか見ない | m-cd | 無い | 9.1 の「止める単位」の表の「社員」の行（390 秒が REQ-03 の 600 秒の内側）。9.2 の `C-scope` の 2 行は、AT の 630 秒が TTS が絞るときの上限にしか使われないと説明している |
| B-BD12 | q-peer を「要る」とし、TLS＋client_id で答えている（カタログは mTLS） | m-cd | 無い | 6. の UC1〜UC7 の q-peer はすべて mTLS（SPIFFE ID、代理店は代理店向けの CA の証明書） |
| B-BD13 | 代わりに後で処理する者がいるのに q-actor を不要とし、理由を書いていない | m-cd | 無い | 6. の UC4 の q-actor：不要の理由を書いた（payment-worker は中身を変えられない運び手で、req_wl と q-peer で記録する）。構造は初回と同じ（act を付けずに後で処理する）なので、判定者が理由に反論する余地は残る |
| B-BD14 | 鍵の漏えいの目標に対し、JWKS のキャッシュの間に漏れた鍵を受け入れる時間が書かれていない | m-cd | 無い | 付録 D の M_token_validation の 8.・9.（TTL 300 秒、失敗時は受けない、気づいてから最悪 810 秒、代理店の鍵は 690 秒）、9.1 の「署名の鍵」の行、3.1 の REQ-10 の起点の見送り |

集計：無い 29、ある 1、該当なし 2

## 参考：一般的な族の、もう一方の対照での確かめ（集計には入れない）

| 族 | 確かめた対照 | 判断 | 場所・理由 |
| --- | --- | --- | --- |
| 鍵の漏えいと JWKS の TTL（A-BD15・B-BD14） | m-cd／m-cc | 無い／無い | 上の本表と同じ節 |
| 依存先の停止（A-BD16・B-BD10） | m-cd／m-cc | 無い／無い | m-cd は 3.1 重点、m-cc は 3.1 の見送り（REQ-13 の 60 分の停止を電話で受ける。数値は要求の側にある） |
| q-actor の「不要」（A-BD10・B-BD13） | m-cc | 無い | UC1〜UC4 はすべて「要る」 |
| q-actor の「不要」（A-BD10・B-BD13） | m-cd | 無い（境界） | UC4 は不要で理由つき（本表の B-BD13）。UC6 は payment-batch が sub なので代理は無い |
| scope の許容と最悪値（A-BD17・B-BD11） | m-cd／m-cc | 無い／無い | m-cd は 9.2 の C-scope（600 は REQ-03）、m-cc は本表の A-BD17 |
| 構造のあるクレームの内側の型（A-BD9・B-BD5） | m-cd／m-cc | 無い／無い | どちらも 3.1 の見送りの行に理由が書いてあり、型の表と正規化もある |
| 承認の入口と追加認証の確かめ手（A-BD12・B-BD2） | m-cd／m-cc | 無い／無い | m-cd は付録 B・H23、m-cc は付録 B・H12 |
| 権限の元データの書き手（A-BD6・B-BD3・B-BD4） | m-cd／m-cc | 無い／無い | m-cd は 9.2 の元のデータからの経路、m-cc は 2.2 と 9.2 |
| M_token_validation 6. の時刻の比べ方（B-BD9） | m-cc | ある（軽い） | 6. は承認の期限・予約・not_before・not_after を挙げるが、直近 30 日の累計の窓（order-tool）、停止の解除から 24 時間の後追いの登録（repair-console）、下書きの 7 日を挙げていない |
| C-sub の id_scheme とワークロードの sub（A-BD13） | m-cd | 無い | m-cd の `C-sub` は id_scheme: other で、description に payment-batch の SPIFFE ID を書いている |
| ワークロードの CA の鍵（A-BD4） | m-cd | 無い | 付録 D の M_token_validation の 8. の「代理店向けの CA・SPIFFE の CA」の行 |
| SET の理由の矛盾（B-BD7） | m-cc | 無い | `SECURITY_EVENT_TOKEN` の理由（aoba-pdp が人事の台帳を直接引く）と 9.2 がそろっている |
| userinfo と aud（B-BD6） | m-cc | 無い | `C-aud` は宛先 1 つとだけ書き、userinfo に触れていない（scope の openid は CONSOLE_AT のログインの値） |

## 参考：初回のよくある誤検出（results.md の 6.2・7.）

| 題 | m-cc | m-cd |
| --- | --- | --- |
| DB の文脈を同じ接続で書き換えられる | 該当なし（9.1 の「DB・ブローカーの接続の層」：トークンで DB に接続しない） | 該当なし（同じ節：DB の文脈に写す接続のホップが無い） |
| break-glass の承認の理由 | 該当なし（2.2「緊急時の特権」は無い。電話の手順で受け、理由は REQ-13） | 該当なし（2.2「緊急時の特権」は無い。TTS が止まったら受付も止める） |

## 参考：32 族の外で気づいたこと

- m-cd の 8. の生成の表で、H30（PAY_MSG_CTX、寿命 3600 秒）の exp の確かめ方が「exp − iat が 300 秒を超えるものは受けない」になっている。H15・H16（TXN_PROXY、60 秒）も 300 秒のまま。初回の seeded-b の副作用「矢印の表で exp − iat ≤ 300」と同じ種類（本表の B-BD9 の「ある」とつながっている）。
