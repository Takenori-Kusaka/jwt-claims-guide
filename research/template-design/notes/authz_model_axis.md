# 認可モデル（RBAC / ABAC / ReBAC / PBAC）は設計書テンプレートのファイル分割の主軸として妥当か

調査日: 2026-11-22。対象リポジトリ: E:\Github\jwt-claims-guide（Part 5 = slides 61–73、Part 6 = 74–89、Part 8 = 101–110、Part 10 = 120–130、Part 11 = 131–143）。

## Q1. 実際のシステムは純粋な RBAC または ABAC か。ハイブリッドはどの程度一般的か

### Takeaway
純粋な単一モデルは少ない。標準化団体、主要 PDP 製品、IdP のいずれも「複数モデルの併用」を前提にしている。トークンにはロールやグループを粗い粒度で載せ、細かい判定は PDP（ポリシーエンジン）で属性や関係を使って行う。この 2 層構成が事実上の標準になっている。認可モデルは「1 システムに 1 つ選ぶもの」ではなく、組み合わせて使う部品と見るべきである。

### Cited Findings
- NIST の Kuhn・Coyne・Weil（IEEE Computer, 2010）は、純粋な RBAC では時刻などの動的属性を十分に扱えず、扱おうとするとロール爆発が起きると指摘した。そのうえで、属性とルールで RBAC を「置き換える、またはより単純で柔軟にする」方向を示した。RBAC の利点としては、権限レビュー、つまり誰が何を持つかを確認できることを挙げている — [NIST publication record](https://www.nist.gov/publications/adding-attributes-role-based-access-control) / [CSRC](https://csrc.nist.gov/pubs/journal/2010/06/adding-attributes-to-rolebased-access-control/final)
- NIST SP 800-162 は ABAC を「logical access control methodology」と定義する。主体・客体・操作・環境条件の属性を、ポリシー・ルール・関係（relationships）と照合して判定する方式である。定義自体に「関係」が含まれており、モデル同士の境界は曖昧になっている — [NIST SP 800-162](https://csrc.nist.gov/pubs/sp/800/162/upd2/final)
- NIST SP 800-178 は XACML と NGAC という 2 つの ABAC 標準を比較している。前提として「要求者の identity・group・role という修飾子だけでは、現実のアクセス制御ポリシーを表現しきれないことが多い」と述べている — [NIST SP 800-178 PDF](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-178.pdf)
- OpenFGA は「ReBAC は RBAC の上位集合であり、属性を関係として表せば ABAC のシナリオもネイティブに扱える」と説明する。関係で表せない属性ベースのケースには Conditions と Contextual Tuples で拡張して対応する。つまり 1 製品の中で RBAC・ReBAC・ABAC を併用する — [OpenFGA Authorization Concepts](https://openfga.dev/docs/authorization-concepts)
- AWS Verified Permissions（Cedar）は IdP の JWT を受け取り、トークンの主体を principal ID に対応づける。ID トークンのクレームは principal の属性に、アクセストークンのクレームは context に入る。どちらのトークンでも `groups` のようなクレームを principal のグループに対応づけて RBAC のポリシーを書ける。この形なら、同じポリシーストアで RBAC（グループ）と ABAC（属性）が自然に共存する — [AWS Verified Permissions: identity sources](https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/identity-sources.html)
- OpenID AuthZEN Authorization API 1.0 は 2026-01-11 に Final になった。PEP と PDP の間の API を Subject・Resource・Action・Context の 4 要素と Decision で定める。ポリシー言語や PDP の内部構造は対象外としており、どの認可モデルかに依存しない（RBAC・ABAC・ReBAC という語自体が出てこない）。Subject の `properties` にはグループ所属などの属性を載せられる — [AuthZEN Authorization API 1.0](https://openid.net/specs/authorization-api-1_0.html)
- Google Zanzibar（USENIX ATC '19）は ACL と関係を集中管理して判定する仕組みで、規模は数兆件の ACL、毎秒数百万件の判定である。発表スライドでは判定の遅延が p95 で 10ms 未満、p99.9 で 100ms 未満と報告されている。ACL の変更と内容の変更の因果順序を守ることを設計目標にしている — [Google Research](https://research.google/pubs/pub48190/) / [USENIX](https://www.usenix.org/conference/atc19/presentation/pang) / [ATC'19 slides](https://www.usenix.net/sites/default/files/conference/protected-files/atc19_slides_pang.pdf)
- Microsoft Entra では、`groups` クレームや `roles`（アプリロール）クレームで RBAC 的な判定をする。それでも足りない場合は、Microsoft Graph への問い合わせ（実行時の最新情報が必要なとき）と組み合わせるよう案内している — [Microsoft Learn: group claims and app roles](https://learn.microsoft.com/en-us/security/zero-trust/develop/configure-tokens-group-claims-app-roles)

### Inferences
- 「RBAC 用」「ABAC 用」とテンプレートを分けると、読者は実際のシステムがどちらか一方だと仮定することになる。しかし標準（NIST）、製品（OpenFGA、Cedar）、API 標準（AuthZEN）のどれもハイブリッドを前提にしている。1 つのシステムで 2〜3 本のテンプレートを同時に埋めることになる可能性が高い。
- ガイドの Part 5 は、slide 65「PEP と PDP：クレームは判断の入力の 1 つ」や slide 66「粗い認可と細かい認可：3 層で分担」で、すでにこのハイブリッドを前提にしている。モデル別にファイルを分けると、ガイド自身の主張とずれる。

### Gaps
- 実システムでのハイブリッド採用率を定量的に示す、信頼できる統計（調査レポートなど）は見つからなかった。
- Kuhn ら（2010）の本文にある 3 方式（dynamic roles、attribute-centric、role-centric）の詳細は、本文 PDF を取得できず確認できていない。概要（abstract）だけを引用した。

## Q2. 認可モデルは JWT に何を入れるかにどう影響するか（肥大化と鮮度のトレードオフ）

### Takeaway
認可モデルが決めるのは、主に「判定の入力をトークンに載せるか、PDP 側で取得するか」の比率である。トークンに載るのは実質的に `scope`、`roles`、`groups`、`entitlements` と、少数の安定した属性（テナントや所属など）に限られる。関係（ReBAC）や変わりやすい属性はトークンに入れず、PDP に問い合わせるのが各社の一致した指針である。したがって、モデルごとのクレーム対応表は大部分が共通になり、違いは「トークンに載せない物」の一覧と、PDP 呼び出しのシーケンスに集中する。

### Cited Findings
- RFC 9068（JWT アクセストークンのプロファイル）は、委任以外の認可の場面では、SCIM User スキーマ（RFC 7643）の `groups`・`roles`・`entitlements` 属性を使うべき（SHOULD）としている。`roles` と `entitlements` の具体的な語彙は定めていない。`scope` の各文字列は `aud` が示すリソースにとって意味を持たなければならない（MUST）。トークンのサイズについては規定がない — [RFC 9068](https://www.rfc-editor.org/rfc/rfc9068.html)
- Entra ID の `groups` クレームの上限は、JWT で 200、SAML で 150、implicit フローで 6 である。上限を超えると `groups` は出力されず、overage 表示（`hasgroups` または `_claim_names`）だけになり、アプリは Graph に問い合わせる必要がある。「トークン内のグループ情報は取得時点でのみ最新」であり、リアルタイムの所属情報が必要なら Graph を使うよう明記している — [Microsoft Learn](https://learn.microsoft.com/en-us/security/zero-trust/develop/configure-tokens-group-claims-app-roles)
- Auth0 では「Add Permissions in the Access Token」を有効にすると `permissions` 配列がアクセストークンに入る。呼び出し回数は減るがトークンは大きくなる、とドキュメントに書かれている。Client Credentials のトークンは利用者ではなくアプリを表すため、利用者のロールは入らない。`scope` で判定するか `gty` を処理する必要がある。テナントのロールと Organization のロールは別の概念である — [Auth0 Docs: enable RBAC for APIs](https://auth0.com/docs/get-started/apis/enable-role-based-access-control-for-apis) / [Auth0 Blog: five reasons permissions not in access token](https://auth0.com/blog/five-reasons-permissions-not-in-access-token/)
- Auth0 の B2B 向け認可ガイドは、トークンのサイズ（特に URL で渡す場合）に注意するよう述べている — [Auth0 B2B authorization](https://auth0.com/docs/get-started/architecture-scenarios/business-to-business/authorization)
- Zanzibar は、関係の変更と内容の変更の順序を守ることを中心に設計されている。トークンに関係を焼き込むと有効期限まで古い値が残るため、この性質とは両立しない。そのため ReBAC では、リクエストのたびに PDP（Check API）へ問い合わせる形になる — [Google Research](https://research.google/pubs/pub48190/)（「new enemy」という用語や zookie の詳細は二次資料にしかない: [Wikipedia](https://en.wikipedia.org/wiki/Google_Zanzibar)）
- AWS Verified Permissions は「IdP トークンの情報で判定するが、IdP とは直接やり取りしない」。トークンのクレームはスナップショットとして PDP の入力になる — [AWS Verified Permissions](https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/identity-sources.html)

### Inferences
- 認可モデルごとのクレームの違いを整理すると次のようになる。
  - RBAC: `roles` または `groups`（あるいは `scope`）を載せる。注意点はロール爆発、グループ数の上限、取り消しの遅れ。
  - ABAC: 安定した属性（`tid`、部署など）だけを載せ、変わりやすい属性は PDP が PIP から取得する。
  - ReBAC: 関係はトークンに載せない。トークンには `sub` と `tid` だけを入れ、PDP に問い合わせる。

  どのモデルでも、トークンに載る部分は iss/sub/aud/exp/scope/tid とロール系クレームという共通部分が大半を占める。
- テンプレートで変わるのは「トークンに何を載せるか」よりも、「判定時に PDP や PIP を呼ぶか、その遅延とキャッシュと整合性をどう設計するか」というシーケンスの側である。これは「認可モデル」というより、ガイド slide 46「載せるか、問い合わせるか」の判断軸そのものである。

### Gaps
- Okta・Keycloak における、トークンのサイズ上限やグループ数上限に相当する公式の値は、今回は確認していない（ガイド Part 3 で既に扱っている可能性がある）。

## Q3. 認可モデルより発行・利用のタイミングを大きく変える代替の分割軸

### Takeaway
シーケンス図の形、つまり誰がいつどのグラントでトークンを得て、どこで交換・検証するかを決めるのは、認可モデルではない。主体の種類（人・ワークロード・AI エージェント）、グラントやフロー、アーキテクチャ（BFF、ゲートウェイ、Transaction Tokens）、トークンの種類である。テナンシーは、どの組み合わせにも横から効くクレーム規則として働く。テンプレートの分割軸としてはこちらの方が適している。

### Cited Findings
- Auth0 の Client Credentials トークンは利用者ではなくアプリを表すため、ロールは入らず `scope` で判定する。主体の種類が違うだけで、同じ RBAC でもクレームの構成が根本から変わる例である — [Auth0 Blog](https://auth0.com/blog/five-reasons-permissions-not-in-access-token/)
- Auth0 では `permissions` は ID トークンではなくアクセストークンに入る。トークンの種類によって載せる場所が変わる — [Auth0 Blog](https://auth0.com/blog/five-reasons-permissions-not-in-access-token/)
- Entra でも、`roles` クレームはアプリ向けには ID トークン、API 向けにはアクセストークンに入る。グループの上限はフローによって 200 / 150 / 6 と変わる（implicit では 6）。フローの違いがクレームの設計に直接効く — [Microsoft Learn](https://learn.microsoft.com/en-us/security/zero-trust/develop/configure-tokens-group-claims-app-roles)
- RFC 8693 Token Exchange は、委任を表す `act` クレーム（入れ子で委任の連鎖を表す）と `may_act` を定めている。エージェントやサービスが代理で呼び出すときに発行のタイミングが 1 段増える — [RFC 8693](https://www.rfc-editor.org/rfc/rfc8693.html)
- OAuth Transaction Tokens（draft-ietf-oauth-transaction-tokens）の最新版は -11（2026-07-30）である。WG の状態は「WG Consensus: Waiting for Write-Up」で、IESG への提出は 2026 年 12 月のマイルストーンになっている。外部から届いたアクセストークンを、信頼境界の内側で短命のトークンに交換して、呼び出し全体に伝搬させる。アーキテクチャという軸で発行のタイミングが追加される例である — [Datatracker](https://datatracker.ietf.org/doc/draft-ietf-oauth-transaction-tokens/) / [draft -10 HTML](https://www.ietf.org/archive/id/draft-ietf-oauth-transaction-tokens-10.html)
- エージェント向けの拡張 draft-oauth-transaction-tokens-for-agents も存在する（2026 年 4 月時点で -05）— [draft-oauth-transaction-tokens-for-agents-05](https://www.ietf.org/archive/id/draft-oauth-transaction-tokens-for-agents-05.html)
- FAPI 2.0 Security Profile は、要件を役割（認可サーバー、クライアント、リソースサーバー）ごとに整理している。送信者制約は MTLS か DPoP のどちらかを選ぶ方式、OIDC は条件付きで必須である。DPoP（RFC 9449）や PAR（RFC 9126）など、フローやアーキテクチャ側の部品が要件の大部分を占めている — [FAPI 2.0 Security Profile](https://openid.net/specs/fapi-security-profile-2_0-final.html)
- AuthZEN の Subject は「user or machine principal」を表し、PEP と PDP の間の API は主体の種類や認可モデルによらず共通である。PDP 呼び出しのシーケンスは 1 つの共通モジュールにまとめられる — [AuthZEN 1.0](https://openid.net/specs/authorization-api-1_0.html)

### Inferences
- シーケンス図に対する各軸の影響度は、筆者の評価で次のとおり。
  1. 主体の種類 × グラント（大）: 人（認可コード + PKCE、リフレッシュ）、ワークロード（client credentials、mTLS、ワークロード ID）、エージェント（token exchange で `act`、CIBA などで人が承認）。図の登場人物と発行回数そのものが変わる。
  2. アーキテクチャ（大〜中）: SPA と BFF、ゲートウェイでの phantom token や内部トークンへの変換、Transaction Tokens、サービスメッシュ。トークンの交換点と検証点が変わる。
  3. トークンの種類（中）: ID トークン、アクセストークン、内部トークン（Txn-Token）。テンプレートの中の表の列として扱うのがよい（ガイド slide 12・102 と対応する）。
  4. テナンシー（中、横断的）: シングルテナント、マルチテナント、B2B フェデレーション。`tid` と `iss` の検証や、テナントをまたぐ運用者の扱いなど、どの組み合わせにも加わる規則になる（slide 70–71）。
  5. 認可モデル（小〜中）: 主に「PDP 呼び出しの有無」と「載せないクレームの一覧」が変わる。
- ガイドの章立てとの対応: Part 5 が主体（slide 62「3 種類の主体」）、Part 6 がアーキテクチャと Transaction Tokens（slide 78）、Part 8 がライフサイクル、Part 10 がエージェント、Part 11 が台帳である。主体の種類を軸にすれば、ガイドの章立てとそのまま対応づけられる。

### Gaps
- CIBA、Device Grant（RFC 8628）、phantom token パターンの一次資料は、今回の調査では取得していない（一般的に知られた仕様だが、本ノートでの引用は RFC 8693 と Txn-Tokens に限った）。
- エージェント向け Txn-Tokens の最新版番号（-05 より新しい版があるか）は確認していない。

## Q4. 認可モデル別に分けると重複や乖離が生じるか。「コア + モジュール / プロファイル」の方がよいか。先例は

### Takeaway
認可モデル別に分けると、共通部分（主体・フロー・検証・ライフサイクル・テナント・プライバシー）の大半を各ファイルに複製することになる。改訂のたびにファイル同士がずれるおそれが高い。FAPI 2.0（1 つの必須プロファイルに選択肢と関連文書を足す構成）や OWASP ASVS（累積的なレベル）と同じように、「共通コア + 選んで足すモジュール」の方が先例にも合い、保守しやすい。

### Cited Findings
- FAPI 2.0 Security Profile は、必須要件をまとめた 1 本のプロファイルの中に、MTLS か DPoP かといった選択肢を持つ構成である。「必須の振る舞いを削除・上書きしてはならない（形式的なセキュリティ分析が無効になる）」と定め、FAPI WG が「このプロファイルの上に構築する追加文書」を出す形をとる（Message Signing、Implementation Advice など）— [FAPI 2.0 Security Profile](https://openid.net/specs/fapi-security-profile-2_0-final.html)
- OWASP ASVS 5.0.0 は 2025-05-30 に公開された。17 章構成で、L1 ⊂ L2 ⊂ L3 の累積的なレベル制をとる。1 つのカタログに対し、レベルで適用範囲を選ぶ方式である — [OWASP ASVS project](https://owasp.org/www-project-application-security-verification-standard/) / [OWASP/ASVS GitHub](https://github.com/OWASP/ASVS)
- RFC 9068 自体も、JWT アクセストークンという共通の形の上に、認可クレーム（scope、または groups/roles/entitlements）を付け足す構成である — [RFC 9068](https://www.rfc-editor.org/rfc/rfc9068.html)
- AuthZEN は PDP のモデルに関係なく、PEP と PDP の間を 1 つの API で定める。「PDP 呼び出し」は認可モデルごとに分けず、共通モジュールとして 1 回だけ書けば足りる — [AuthZEN 1.0](https://openid.net/specs/authorization-api-1_0.html)

### Inferences（推奨するファイル構成）
- 主軸は認可モデルではなく「主体の種類 × 代表的なフロー」にし、その上に「共通コア + 追加モジュール」を重ねる。認可モデルは、モジュールの中の決定項目（と短い差分の付録）に格下げする。
- 推奨するレイアウトの案:
  ```
  templates/
    00_core.md                 # 全システム共通: 発行者と受け取り手の一覧、登録クレーム検証、
                               #   名前空間、型、サイズ予算、ライフサイクル、プライバシー、台帳への接続
    profiles/                  # シーケンス図の形が変わる単位 (主体 × フロー) = 主軸
      P1_human_web_bff.md      # 認可コード + PKCE、BFF または SPA、ID トークンとアクセストークン、リフレッシュ
      P2_human_mobile_native.md
      P3_workload_m2m.md       # client credentials、mTLS、ワークロード ID、バッチ
      P4_ai_agent_delegation.md# token exchange (act/may_act)、CIBA や人の承認、MCP
      P5_internal_propagation.md # ゲートウェイでの変換、Transaction Tokens、メッシュ
    modules/                   # 横断的に選んで足す部品
      M_authz_pdp.md           # 認可方式の決定: RBAC (roles/groups) / ABAC (属性 + PIP) / ReBAC (Check API)
                               #   / ハイブリッド。「載せるか、問い合わせるか」の判断表、PDP 呼び出しのシーケンス
                               #   (AuthZEN)、鮮度とキャッシュ、採否のチェックリスト
      M_multitenancy.md        # tid と iss、テナントをまたぐ運用者、B2B フェデレーション
      M_sender_constraint.md   # DPoP、mTLS (FAPI 相当)
      M_privacy_minimization.md
      M_idp_mapping_<IdP>.md   # Entra、Keycloak、Auth0、Okta、Cognito ごとの差分 (任意)
  ```
- 根拠:
  1. シーケンス図（発行と利用のタイミング）を決めるのは主体とフローであり、認可モデルはトークン発行の外側で PDP 呼び出しを足すかどうかを決めるだけである。
  2. 実システムはハイブリッドなので、認可モデル別のファイルでは 1 システムで複数を埋めることになり、記入が重複する。
  3. FAPI や ASVS と同じく、コアは不変で、選択肢をモジュールとして足す方式は改訂時のずれを防ぐ。
  4. ガイドの Part 5（主体）、6（アーキテクチャ）、8（ライフサイクル）、10（エージェント）、11（台帳）とそのまま対応づけられる。
- 認可モデルを残す場所: `M_authz_pdp.md` の中に「RBAC / ABAC / ReBAC / ハイブリッド」の選択表を置く。行は選んだ方式、列は「トークンに載せるクレーム」「載せないもの」「データソース（IdP / PIP / 関係ストア）」「PDP 呼び出しのタイミング」「鮮度の許容値」「失効の伝わり方」「採否の条件」とする。各方式の差分は 1 ページ程度に収まる見込み。
- 代替案として、ユーザーの案（認可モデル別）を残すなら、ファイル名を「RBAC 中心型 / ABAC 中心型 / ReBAC 中心型」にして、共通部分は 00_core.md を参照する（転記しない）。最低限この形にすれば重複は避けられる。ただし主体やフローの違いを表す場所がなくなるので、勧めない。

### Gaps
- 「モジュール式のセキュリティ設計書テンプレート」として直接の先例（例: 設計書テンプレート集で、コアとプロファイルに分割したもの）は、今回の調査では見つからなかった。先例として挙げたのは、標準仕様の構成（FAPI、ASVS、RFC 9068）からの類推である。
- 主体の種類で分割した場合に、P1〜P5 のどこまでを別ファイルにすべきか（例: モバイルを P1 に統合するか）は、利用者の想定読者次第で、根拠となる資料はない。

## Q5. Token size budget and checker — トークンサイズの予算とチェッカー（クレームを採用しすぎたとき、または値の取りうる範囲が大きすぎるときにエラーを出すチェッカーを入れるべきか）

### Takeaway
入れる価値は高い。経路上のサイズ上限は数 KB 単位で、製品ごとに大きく違う。たとえば Cookie は 1 個 4096 octets、nginx はヘッダー 1 行 8 KB、Entra の custom claims provider は 3 KB、Okta の groups 関数は 100 件、Entra の groups は 200 件である。しかも上限を超えたときの挙動は「黙って消える」「400、414、431 を返す」「overage 表示に切り替わる」とばらばらで、障害の原因が分かりにくい。台帳（クレームの登録簿）の各クレームに「最大長」「最大件数」「どのトークン種別と段階に載るか」を宣言させれば、最悪ケースのサイズを静的に計算できる。設計時のチェッカーとして実装できる。ただし、「クレーム台帳から最悪ケースを合算して予算と比べる静的チェッカー」の直接の先例は見つからなかった。近い先例は、実行時やトークン単位のサイズ検査（NATS、Auth0 のサイズ計算）と、IdP 側の overage という仕組みである。

### Cited Findings
**(1) 経路上のサイズ上限（2026-11 時点）**

IdP 側
- Entra ID の `groups` クレームの上限は、JWT で 200、SAML で 150、implicit フローで 6 である。超えると `groups` は出ず、overage（`hasgroups` または `_claim_names` / `_claim_sources`）に切り替わる。overage の値そのものには依存せず、存在するかどうかだけを見て Graph に問い合わせるよう明記している — [Microsoft Learn](https://learn.microsoft.com/en-us/security/zero-trust/develop/configure-tokens-group-claims-app-roles)
- Entra の custom claims provider（TokenIssuanceStart）が返せるクレームは、全キーと全値の合計で 3 KB までである。超えるとエラー 1003025 CustomExtensionResponseClaimsSizeExceeded になる — [Custom claims provider reference](https://learn.microsoft.com/en-au/Entra/identity-platform/custom-claims-provider-reference) / [Troubleshoot custom claims provider](https://learn.microsoft.com/en-gb/entra/identity-platform/custom-extension-troubleshoot)
- Okta の Groups 関数（`Groups.startsWith` など）の limit 引数は最大 100 で、超えるとエラーになる。クレーム式の値は 1,024 文字までである。ただし、200 件返ったという報告もあり、公式の開発者ドキュメントで 100 という上限は確認できなかった — [Okta Support: 100 groups limitation](https://support.okta.com/help/s/article/how-to-exceed-the-100-groups-limitation-on-a-claim) / [Okta Support: too many groups](https://support.okta.com/help/s/article/error-the-groups-claim-matched-too-many-groups-and-must-be-configured-to-match-fewer-groups) / [Okta Support: field is too long](https://support.okta.com/help/s/article/error-the-field-is-too-long-when-saving-a-custom-claim-expression) / [Okta devforum（矛盾する報告）](https://devforum.okta.com/t/okta-100-groups-truncation/35236)
- Amazon Cognito の上限は次のとおり。所属できるグループは 1 ユーザーあたり 100、1 属性は 2,048 bytes、カスタム属性はユーザープールあたり 50。pre token generation では、既存と追加のクレームとスコープの合計数に 5,000 という quota があり、抑制したものは数えない。トークン全体のバイト数の上限は記載がない — [Cognito quotas](https://docs.aws.amazon.com/cognito/latest/developerguide/quotas.html)
- Auth0 はトークンのサイズ上限を公表していない。サイズは「ヘッダー・ペイロード・署名を含む、エンコード済み JWT 全体の UTF-8 バイト数」で計測すると説明している — [Auth0: ID Token Size Calculation](https://support.auth0.com/center/s/article/auth0-id-token-size-calculation)
- Keycloak にもトークンのサイズ上限は見当たらない。グループのマッパーでトークンが肥大化して失敗した報告がある。対策として lightweight access token（`use.lightweight.access.token`。マッパーごとに「Add to lightweight access token」を選ぶ）がある。ただしここでの説明は公式文書ではなく第三者の Confluence ページによる — [Keycloak forum](https://forum.keycloak.org/t/big-jwt-token-browsers-cut-part-of-token-and-auth-end-with-failure/20300) / [FOLIO EUREKA-755](https://folio-org.atlassian.net/wiki/spaces/FOLIJET/pages/1154678786/EUREKA-755+PoC+-+Are+lightweight+access+tokens+a+viable+solution+to+the+too+many+roles+problem) / [Keycloak javadoc UseLightweightAccessTokenExecutor 26.8.2](https://www.keycloak.org/docs-api/26.8.2/javadocs/org/keycloak/services/clientpolicy/executor/UseLightweightAccessTokenExecutor.html)
- AWS API Gateway の JWT authorizer は「Additional claims per issuer」が 10 である — [API Gateway REST quotas page](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-execution-service-limits-table.html)

Cookie
- RFC 6265bis（Internet-Draft、2026-11-17 版）では、Cookie の名前と値の合計が 4096 octets を超えると無視され、属性値は 1024 octets を超えると無視される。ドメインあたりの上限は実装依存で、例として 50 個が挙げられている — [draft-ietf-httpbis-rfc6265bis](https://httpwg.org/http-extensions/draft-ietf-httpbis-rfc6265bis.html)

プロキシ、サーバー、マネージドサービス
- nginx の既定値は `large_client_header_buffers 4 8k`（初期値は `client_header_buffer_size 1k`）である。ヘッダーの 1 フィールドがバッファ 1 つ（8 KB）を超えると 400、リクエスト行が超えると 414 を返す — [nginx core module](https://nginx.org/en/docs/http/ngx_http_core_module.html)。なお Keycloak フォーラムには「nginx は 4kB」という記述があるが、公式の既定値（8k）と矛盾するので採用しない — [Keycloak forum](https://forum.keycloak.org/t/access-token-limit-size-kb/2453)
- AWS ALB の上限は、リクエスト行 16 K、単一ヘッダー 16 K、リクエストヘッダー全体 64 K、レスポンスヘッダー全体 32 K で、いずれも変更できない — [ALB quotas](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-limits.html)
- AWS API Gateway（REST）の上限は、全ヘッダーの合計 20,480 bytes（private API では 8,000 bytes）、URL 長は Regional API で 10,240 文字、edge-optimized と private で 8,192 文字である — [API Gateway REST quotas](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-execution-service-limits-table.html)
- AWS CloudFront は、ヘッダーとクエリ文字列を含むリクエスト長の上限が 32,768 bytes、URL 長の上限が 8,192 bytes である — [CloudFront quotas](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cloudfront-limits.html)
- Envoy の `max_request_headers_kb` は既定 60 KiB で、超えると 431 を返す — [Envoy HttpConnectionManager](https://www.envoyproxy.io/docs/envoy/latest/api-v3/extensions/filters/network/http_connection_manager/v3/http_connection_manager.proto)
- Kestrel の既定値は、`MaxRequestHeadersTotalSize` が 32 KB（32,768 bytes）、リクエスト行が 8 KB、ヘッダー数が 100 である — [KestrelServerLimits.cs](https://source.dot.net/Microsoft.AspNetCore.Server.Kestrel.Core/KestrelServerLimits.cs.html)
- 第三者の報告として、Apache httpd はヘッダー 8 KB が既定、Keycloak 経由ではブラウザがトークンを切り詰めた事例がある — [keycloak-dev list](https://lists.jboss.org/archives/list/keycloak-dev@lists.jboss.org/message/F5L73YWZEEAKVMGKTYKLXHF4OBOAVV6X/attachment/2/attachment.html) / [Keycloak forum](https://forum.keycloak.org/t/big-jwt-token-browsers-cut-part-of-token-and-auth-end-with-failure/20300)

**(2) エンコード後のサイズの見積もり方**
- JWS Compact は `BASE64URL(header) . BASE64URL(payload) . BASE64URL(signature)` で、base64url はパディングなし — [RFC 7515](https://www.rfc-editor.org/rfc/rfc7515.html)。base64 は入力 3 octets を出力 4 文字に変換する — [RFC 4648](https://www.rfc-editor.org/rfc/rfc4648.html)
- 署名の長さは、ES256 が 64 octets（R‖S）、ES384 が 96 octets、ES512 が 132 octets — [RFC 7518 §3.4](https://www.rfc-editor.org/rfc/rfc7518.html)。RS256 と PS256 は RSA の鍵長と同じで、2048-bit 鍵なら 256 octets — [RFC 7518 §3.3](https://www.rfc-editor.org/rfc/rfc7518.html) / [RFC 8017](https://www.rfc-editor.org/rfc/rfc8017.html)。Ed25519 は 64 octets — [RFC 8037](https://www.rfc-editor.org/rfc/rfc8037.html)
- 計測の定義としては、Auth0 と同じく「エンコード済み JWT 全体の UTF-8 バイト数」を使うのが妥当である — [Auth0](https://support.auth0.com/center/s/article/auth0-id-token-size-calculation)

**(3) 既存の実践**
- overage パターンの標準は OIDC Core §5.6.2 の Aggregated / Distributed Claims（`_claim_names` と `_claim_sources`）で、Entra はこれを groups の overage に使っている — [OpenID Connect Core 1.0 §5.6.2](https://openid.net/specs/openid-connect-core-1_0.html#AggregatedDistributedClaims) / [Microsoft Learn](https://learn.microsoft.com/en-us/security/zero-trust/develop/configure-tokens-group-claims-app-roles)
- IdP 側の回避策には次のものがある。Entra の「Groups assigned to the application」によるフィルタやアプリロール、Okta のクレーム分割と Token Inline Hook、Keycloak の lightweight access token — 上記の各出典
- サイズ検査の先例として最も近いのは Synadia（NATS）の「excessive JWT size」チェックである。既定のしきい値は 64 KiB で設定でき、チーム内の目安を 10 KB 未満とし、CI でのサイズ検査を勧めている。ただしこれは発行済みのアカウント JWT を検査するもので、OAuth のクレーム台帳を検査するものではない — [Synadia insights: nats-excessive-jwt-size](https://www.synadia.com/insights/checks/nats-excessive-jwt-size)
- ライブラリ側にも上限を設けた例がある。jwtiny は入力を 64 KB で制限する — [jwtiny limits.rs](https://docs.rs/crate/jwtiny/latest/source/src/limits.rs)
- JWT のリンター（jwtlint、jwtlens）は存在するが、サイズ予算を検査するという記述は確認できなかった — [jwtlint (PyPI)](https://pypi.org/project/jwtlint/)

### Inferences
- 最悪ケースの計算例（筆者による試算）: Entra の上限いっぱい（200 件）の GUID（36 文字）を JSON 配列にすると、1 要素あたり約 39 bytes（引用符 2 つとカンマ）なので約 7.8 KB になる。base64url で 4/3 倍になり、約 10.4 KB になる。これだけで nginx の既定値（1 ヘッダー 8 KB）と Cookie 1 個（4 KB）を超える。Entra が 200 件で overage に切り替えるのは、この規模感と整合する。
- ガイドとの対応: slide 55「サイズの予算：上限を超えると黙って消える」、slide 133「台帳：クレームごとに決める 12 の項目」、slide 135「スキーマと契約テスト」の延長として、台帳に計算用の列を追加し、静的チェッカーで検証するのが自然である。
- チェッカーの設計案:
  - 台帳の各クレームに必須で宣言する入力
    1. `max_bytes`: 値の最大長。文字列は UTF-8 のバイト数、数値は桁数で表す。enum なら値域の最長値を使う。
    2. `max_items`: 配列クレームの最大件数。根拠も書く（例: IdP の上限が 200、フィルタ後の想定が 20）。
    3. `typical_items`: 通常時の件数。警告の基準に使う。
    4. `carried_in`: どのトークン種別に載るか。ID トークン、アクセストークン（audience ごと）、Txn-Token、ログアウトトークンなどの段階を区別する。
    5. `transport`: Authorization ヘッダー、Cookie、URL の fragment や query、メッセージキューのどれで運ばれるか。
    6. `overflow_strategy`: 上限を超えたときの方針。truncate は禁止とし、overage と取得 API、拒否、別トークンへの分離のいずれかを選ぶ。
    7. 値の生成元: IdP の属性、マッパー、フック。その上限（Entra の 3 KB、Cognito の 2,048 bytes など）も書く。
  - トークン種別ごとのプロファイルで宣言する入力: 署名アルゴリズム（署名の長さが決まる）、ヘッダーの最大長（`kid` の長さを含む）、運搬経路で最も厳しい上限（ゲートウェイ、プロキシ、サーバー、Cookie、URL の最小値）。
  - 計算方法: worst = Σ(キー名 + 値の最大長 × 最大件数 + JSON の区切り文字) をペイロードとし、`ceil(4/3 × payload) + ceil(4/3 × header) + ceil(4/3 × sig) + 2` で求める。Authorization ヘッダーなら `Bearer ` の 7 bytes を足す。
  - しきい値（案）
    - error: 最悪ケースが経路上の最も厳しい上限の 100% を超える。Cookie なら 4096 bytes から名前と属性を引いた値、Authorization ヘッダーなら nginx の既定値 8 KB を基準にする。
    - error: `max_items` が IdP の上限（Entra 200、Okta 100、Cognito 100）を超えているのに `overflow_strategy` が未宣言。
    - error: `max_items` を宣言していない配列クレームがある（値の範囲が上限なしのまま）。
    - warn: 最悪ケースが予算の 50〜75% を超える。将来の追加（DPoP の `cnf`、`act` の入れ子など）の余地を残すため。
    - warn: 典型ケースのサイズが一定の値（例: 2 KB）を超える。性能やログ量への影響、URL 経由で運ぶ場合のため。
    - info: アクセストークンにも ID トークンにも同じクレームが載っている（重複の候補）。
  - 静的チェックの補完として、発行された実トークンを CI や監視で計測する動的チェックを置く（slide 143「台帳と実際の発行のずれ」と結合する）。静的チェッカーは宣言値を信じるので、宣言と実態のずれは動的チェックで捕まえる。
- テンプレート構成との関係: チェッカーは `00_core.md`（サイズの予算の章）と台帳スキーマに置く。主体別のプロファイル（P1〜P5）ごとに経路の上限値を既定値として持たせる（例: P1 BFF なら Cookie 4 KB、P5 なら Txn-Token の経路）。認可モデルのモジュール（`M_authz_pdp.md`）では「載せずに PDP に問い合わせる」がサイズ超過の主な解決策になるので、チェッカーの error から、このモジュールの判断表へ誘導する。

### Gaps
- Tomcat（`maxHttpHeaderSize` の既定値。8 KB と推定されるが未確認）、IIS / HTTP.sys（MaxFieldLength / MaxRequestBytes）、Node.js（`--max-http-header-size` の既定は 16 KiB と思われるが、公式ページの該当部分を取得できず未確認）、Google Cloud LB、Azure Front Door、Application Gateway の上限は、一次資料で確認できていない。
- Auth0、Okta、Keycloak について、トークン全体のバイト数上限を示す公式の値は見つからなかった（公表されていない可能性がある）。
- 「クレーム台帳から最悪ケースを合算して予算と比べる静的チェッカー」の直接の先例（OSS、製品、論文）は見つからなかった。提案したチェッカーは新規の設計である。
- HTTP/2 と HTTP/3 では HPACK / QPACK による圧縮や SETTINGS_MAX_HEADER_LIST_SIZE が効くが、その実効上限は今回調べていない。
