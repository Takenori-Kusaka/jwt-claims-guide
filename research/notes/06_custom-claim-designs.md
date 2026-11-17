# 06. 組織横断で共有するカスタム JWT クレームの設計事例と教訓

- 調査日: 2026-11-17
- 対象: 標準 OIDC/SAML クレームではなく、**アプリ/プラットフォームが定義するカスタム（private / public-namespaced）クレーム**。アクセス制御系・監査/来歴系・コンテキスト伝搬系、消費側のパース/マッチング方法、ガバナンス。
- 方針: 公式ドキュメント・仕様・当事者のエンジニアリングブログを実際に取得して確認した内容のみ記載。取得ページ内で確認できなかったもの、二次情報のみのものは **[未検証]**。
- 凡例: RP = relying party（トークン消費側）、AS = authorization server、TTS = Transaction Token Service、FIC = federated identity credential

---

## 0. 先に結論（スライド用サマリ）

1. **名前より不変 ID**。GitHub は 2026-07-15 以降に作成/改名/移譲されたリポジトリで `sub` に owner/repo の数値 ID を埋め込む「immutable subject」に移行。GitLab は過去に使われたパスを含む `sub` の発行自体をブロック。AWS/GCP/Azure/OWASP も揃って「`*_id` を条件に使え」と明記。
2. **「誰が値を書けるか」でクレームを分ける**。Supabase `user_metadata`（ユーザー編集可）vs `app_metadata`、AWS outbound JWT の `principal_tags`（AWS が付与）vs `request_tags`（呼び出し側が任意指定）、Txn-Token の `rctx`（環境）vs `tctx`（TTS が決めた認可詳細）。
3. **namespace は衝突回避に有効だが、下流ツールのパス表記と衝突する**。`https://aws.amazon.com/tags` のような URL 名は「.」を含むため、Envoy `claim_to_headers.claim_name` の「.」区切りでは参照できない（`claim_path` が必要）。
4. **型を固定する**。同じ「ID」でも GitLab 例では `"project_id": "20"`（文字列）と `"runner_id": 1`（数値）が混在、`"ref_protected": "false"` は文字列ブール。GitHub の multi-select カスタムプロパティはカンマ連結文字列。消費側はこれに合わせた文字列比較を強いられる。
5. **トークンは「スナップショット」**。Firebase/Supabase/OpenFGA/AVP はいずれも「クレーム変更は次のトークン発行まで反映されない」「失効しても有効期限まで効く」と明記。細粒度・揮発的な権限は lookup 側へ（Zanzibar の "new enemy" 問題）。
6. **クレーム→ヘッダ変換は信頼境界**。Istio/Envoy は該当ヘッダを上書き/サニタイズするが、未検証モード・バイパス経路・アンダースコア変種（CVE-2025-64484）・重複ヘッダ（CVE-2026-26308）で破れる。
7. **クレーム集合は API 契約**。Curity: "Changing the content of a token should be considered a breaking change."

---

## 1. 多数の RP を想定したワークロード / CI ID トークン

### 1.1 GitHub Actions OIDC トークン

出典: https://docs.github.com/en/actions/reference/security/oidc , https://docs.github.com/en/actions/concepts/security/openid-connect

**発行者 / 消費者**: 発行 `iss = https://token.actions.githubusercontent.com`（GHEC の enterprise 固有 issuer も可、2022-08 changelog https://github.blog/changelog/2022-08-23-github-actions-enhancements-to-openid-connect-support-to-enable-secure-cloud-deployments-at-scale ）。消費は AWS/Azure/GCP/Vault など任意の RP。`aud` 既定は repository owner の URL、`core.getIDToken(audience)` で変更可。

**GitHub 定義のカスタムクレーム**（"Custom claims provided by GitHub" 表、すべてトップレベル・フラット・snake_case・接頭辞なし）:
`actor`, `actor_id`, `base_ref`, `check_run_id`, `environment`, `event_name`, `head_ref`, `job_workflow_ref`, `job_workflow_sha`, `ref`, `ref_type`, `repository_visibility`, `repository`, `repository_id`, `repository_owner`, `repository_owner_id`, `repo_property_*`, `run_id`, `run_number`, `run_attempt`, `runner_environment`（`github-hosted` / `self-hosted`）, `workflow`, `workflow_ref`, `workflow_sha`。
- `event_name`: Dependabot 更新ジョブでは `dynamic`。「Actions ワークフローだけを許可したいなら、想定する event_name だけ許可せよ」と明記。
- `check_run_id` は 2025-11 追加。「トークンを生成したジョブと計算資源に紐づけて監査する」目的（https://github.blog/changelog/2025-11-13-github-actions-oidc-token-claims-now-include-check_run_id ）→ **監査用クレームを後から追加した実例**。

**`*_id` クレーム追加の経緯**: 2023-01 changelog で `actor_id`, `repository_id`, `repository_owner_id`, `workflow_ref`, `workflow_sha`, `job_workflow_sha` を追加、「reusable workflow を参照していてもジョブの出所を一意に検証するため」（https://github.blog/changelog/2023-01-10-github-actions-openid-connect-token-now-supports-more-claims-for-configuring-granular-cloud-access ）。

**immutable subject（2026）**: 「OIDC 仕様は sub が locally unique かつ再割当てされないことを要求。従来の既定 sub は org/repo 名のみで、名前空間が再利用されると別オーナーが同じ sub を作れた」。
- 2026-07-15 以降に作成されたリポジトリ、および以降の rename/transfer は `repo:OWNER@OWNER-ID/REPO@REPO-ID:ref:refs/heads/BRANCH`（例 `repo:octo-org@123456/octo-repo@456789:ref:refs/heads/main`）。
- 区切りに `@` を使うのは「GitHub のユーザー名/リポジトリ名に `@` は現れない」ため。→ **区切り文字の衝突回避を明示的に設計した例**。
- 既存リポジトリは opt-in（UI/API）。プレビュー endpoint で新 prefix を事前確認できる。GHES は対象外。immutable 形式では `include_claim_keys` でカスタマイズしても ID を除去できない。
- 出典: https://github.blog/changelog/2026-04-23-immutable-subject-claims-for-github-actions-oidc-tokens , 上記 reference。

**sub テンプレートのカスタマイズ**: REST API で `{"include_claim_keys":["repo","context","job_workflow_ref"]}` → `sub = repo:ORG/REPO:environment:prod:job_workflow_ref:octo-org/octo-automation/.github/workflows/oidc.yml@refs/heads/main`。
- 値中の `:` は `%3A` にエスケープ（例 `environment:production%3Aeastus`）。
- **順序の注意**: 「先にクラウド側の一致条件を作ってから GitHub 側のテンプレートを変えよ。逆だと発行トークンが受理されない」。→ **issuer/consumer 間の移行順序が契約になっている**。
- org テンプレートは既存リポジトリに自動適用されない（repo 側で `use_default:false` の opt-in が必要）。

**リポジトリ custom properties → `repo_property_*`**（2026-03 preview、2026-04 GA: https://github.blog/changelog/2026-03-12-actions-oidc-tokens-now-support-repository-custom-properties , https://github.blog/changelog/2026-04-02-github-actions-early-april-2026-updates ）
- 組織/エンタープライズ管理者が選んだプロパティを `repo_property_<name>` として埋め込む＝**組織の分類メタデータを ABAC 属性として配る**仕組み。
- 型表現: String/Single select → 文字列、**Multi select → カンマ連結文字列 `"us-east-1,eu-west-1"`**、True/false → **文字列 `"true"`/`"false"`**。「multi-select はクラウド側で string matching / contains で評価せよ」。
- ドキュメント掲載例（reference ページ）:

```json
{"sub":"repo:my-org/my-repo:ref:refs/heads/main", "aud":"https://github.com/my-org", "repository":"my-org/my-repo", "repo_property_business_unit": "payments", "repo_property_workspace_id":"ws-abc123"}
```

- 教訓: 配列を文字列化すると `contains` 判定で `us-east-1` が `us-east-10` にも一致しうる **[未検証: GitHub はこの点を明記していない。筆者推論]**。

### 1.2 GitLab CI `id_tokens`

出典: https://docs.gitlab.com/ci/secrets/id_token_authentication/ （例ペイロードはソース https://gitlab.com/gitlab-org/gitlab/-/raw/master/doc/ci/secrets/id_token_authentication.md から転記）

```json
{
  "namespace_id": "72",
  "namespace_path": "my-group",
  "project_id": "20",
  "project_path": "my-group/my-project",
  "user_id": "1",
  "user_login": "sample-user",
  "user_email": "sample-user@example.com",
  "user_identities": [
      {"provider": "github", "extern_uid": "2435223452345"},
      {"provider": "bitbucket", "extern_uid": "john.smith"}
  ],
  "pipeline_id": "574",
  "pipeline_source": "push",
  "job_id": "302",
  "ref": "feature-branch-1",
  "ref_type": "branch",
  "ref_path": "refs/heads/feature-branch-1",
  "ref_protected": "false",
  "groups_direct": ["mygroup/mysubgroup", "myothergroup/myothersubgroup"],
  "environment": "test-environment2",
  "environment_protected": "false",
  "deployment_tier": "testing",
  "environment_action": "start",
  "job_source": "push",
  "job_config": {
    "url": "https://gitlab.example.com/my-group/my-policy-project/-/blob/ab035e64eca9a7a85bd62e485d3593f52a2804ac/.gitlab/security-policies/policy.yml",
    "sha": "ab035e64eca9a7a85bd62e485d3593f52a2804ac"
  },
  "runner_id": 1,
  "runner_environment": "self-hosted",
  "sha": "714a629c0b401fdce83e847fc9589983fc6f46bc",
  "project_visibility": "public",
  "ci_config_ref_uri": "gitlab.example.com/my-group/my-project//.gitlab-ci.yml@refs/heads/main",
  "ci_config_sha": "714a629c0b401fdce83e847fc9589983fc6f46bc",
  "jti": "235b3a54-b797-45c7-ae9a-f72d7bc6ef5b",
  "iss": "https://gitlab.example.com",
  "iat": 1681395193,
  "nbf": 1681395188,
  "exp": 1681398793,
  "sub": "project_path:my-group/my-project:ref_type:branch:ref:feature-branch-1",
  "aud": "https://vault.example.com"
}
```

観察（型・存在性の揺れ ＝ 教材として有用）:
- ID は文字列（`"project_id": "20"`）だが `"runner_id": 1` は数値。ブールは文字列（`"ref_protected": "false"`）。
- `environment*` はジョブが environment を指定したときのみ存在。`user_identities` は設定有効時のみ。`groups_direct` は直接所属 0〜200 グループのときのみ、**200 超で丸ごと省略**（feature flag `ci_jwt_groups_direct` 既定無効）。`job_config` はポリシー起動ジョブのみ。
- `ci_config_ref_uri` / `ci_config_sha` は「パイプライン定義が同一プロジェクトにない場合 `null`」→ **absent と null が併存**。
- 既定 `sub = project_path:{group}/{project}:ref_type:{type}:ref:{branch_name}`。GitLab 18.7 で `sub` に `ref_protected`・environment 系を含められるように。プロジェクト API の `ci_id_token_sub_claim_components`（例 `["project_id","ref_type","ref"]`）で構成変更。
- **パス再利用ブロック**: 「設定された sub に、別プロジェクトが過去に使ったパスの `project_path`/`job_project_path`/`source_project_path` が含まれる場合、ID トークン発行をブロック。新プロジェクトが旧プロジェクトの外部 trust policy を継承するのを防ぐため」。解決策は先頭成分を `project_id` 等の ID に。
- 「`project_id` はグローバル一意でプロジェクトの生涯不変、`namespace_id` は現在の namespace にいる間は安定」→ trust policy では path 系と併用せよ。
- AWS（GitLab.com IdP）で条件キーとして使えるのは `namespace_id`, `project_id`, `user_id`, `user_login`, `user_email`, `user_access_level`, `ref_protected`, `pipeline_source` など（同ページ）。

### 1.3 Kubernetes ServiceAccount トークン（入れ子の `kubernetes.io` クレーム）

出典: https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/

```json
{
  "aud": [
    "https://my-audience.example.com"
  ],
  "exp": 1729605240,
  "iat": 1729601640,
  "iss": "https://my-cluster.example.com",
  "jti": "aed34954-b33a-4142-b1ec-389d6bbb4936",
  "kubernetes.io": {
    "namespace": "my-namespace",
    "node": {
      "name": "my-node",
      "uid": "646e7c5e-32d6-4d42-9dbd-e504e6cbe6b1"
    },
    "pod": {
      "name": "my-pod",
      "uid": "5e0bd49b-f040-43b0-99b7-22765a53f7f3"
    },
    "serviceaccount": {
      "name": "my-serviceaccount",
      "uid": "14ee3fa4-a7e2-420f-9f9a-dbc4507c3798"
    }
  },
  "nbf": 1729601640,
  "sub": "system:serviceaccount:my-namespace:my-serviceaccount"
}
```

- 設計: プラットフォーム固有情報を**ドメイン名キー 1 個の下に入れ子オブジェクト**で集約（private claim 衝突回避）。name と uid を対で持つ（名前は再作成で再利用されうる、uid は不変）。`aud` は常に配列。
- node 情報（v1.32 stable）は「kube-apiserver は認証時に検証しない。統合者が Pod/Node API を引かずに済むよう含めている」→ **"情報提供用で検証されないクレーム"を明示した例**。
- 「Kubernetes 固有クレームのスキーマは現在文書化されていない。serviceaccount パッケージのコードを参照」→ **スキーマ未文書化のリスク**を公式が認めている。
- TokenReview で検証すると `extra` に `authentication.kubernetes.io/pod-name`, `.../pod-uid`, `.../node-name`, `.../node-uid`, `.../credential-id`（`JTI=...`）が**文字列配列**で返る。

### 1.4 SPIFFE JWT-SVID

出典: https://github.com/spiffe/spiffe/blob/main/standards/JWT-SVID.md
- `sub` は SPIFFE ID（MUST）。`aud` 必須、検証者は自分が `aud` に含まれない/`aud` なしを拒否（MUST）。「通常は値を 1 つに限ることを強く推奨」（§7.2: 受信者には暗黙の信頼が与えられるため、replay 範囲を絞る）。
- 追加クレーム: 「Implementers should exercise caution when introducing additional claims」「必要なら collision-resistant に」。→ **ワークロード ID 標準はカスタムクレームを意図的に最小化**。
- `typ` 任意、設定するなら `JWT` か `JOSE`。HTTP では `Authorization` ヘッダで送る（SHOULD）。サイズ規定なし。

### 1.5 （補足）AWS IAM outbound identity federation の JWT

出典: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_outbound_token_claims.html , https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_outbound_getting_started.html

AWS 自身が `GetWebIdentityToken` で外部 RP 向け JWT を発行。AWS 固有クレームはすべて URL namespace オブジェクト `"https://sts.amazonaws.com/"` の下:

```json
{
  "iss": "https://abc123-def456-ghi789-jkl012.tokens.sts.global.api.aws",
  "aud": "https://api.example.com",
  "sub": "arn:aws:iam::123456789012:role/DataProcessingRole",
  "iat": 1700000000,
  "exp": 1700000900,
  "jti": "xyz123-def456-ghi789-jkl012",
  "https://sts.amazonaws.com/": {
    "aws_account": "123456789012",
    "source_region": "us-east-1",
    "principal_id": "arn:aws:iam::123456789012:role/DataProcessingRole",
    "org_id": "o-abc1234567",
    "ou_path": [
      "o-a1b2c3d4e5/r-ab12/ou-ab12-11111111/ou-ab12-22222222/"
    ],
    "principal_tags": {
      "environment": "production",
      "team": "data-engineering",
      "cost-center": "engineering"
    },
    "lambda_source_function_arn": "arn:aws:lambda:us-east-1:123456789012:function:process-data",
    "request_tags": {
        "job-id": "job-2024-001",
        "priority": "high",
        "data-classification": "sensitive"
    }
  }
}
```

- **出所による分離**: `principal_tags`（IAM principal/セッションに付いたタグ）と `request_tags`（呼び出し側が API で任意指定、最大 50）を別オブジェクトに。後者は呼び出し元の自己申告なので信頼度が違う。
- `mfa_present` は「MFA 使用時のみ、文字列 `"true"`。`"false"` は決して入らない」。`mfa_age` も文字列。→ **"absent = false" の明示的規約**。
- 各クレームが既存の IAM 条件キー（`aws:PrincipalOrgID` 等）に対応づけて文書化されている＝**クレーム辞書をポリシー語彙と 1:1 対応**。
- 「all these claims may not be present in a token at the same time」。

### 1.6 クラウド側（消費者）の解釈方法

**AWS IAM（`AssumeRoleWithWebIdentity`）** — https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_iam-condition-keys.html
- 条件キーは `<provider host>:<claim>`（例 `token.actions.githubusercontent.com:sub`）。Default 表: `amr`, `aud`(= `azp` があれば `azp`、なければ `aud`), `email`, `oaud`(=`aud`), `sub`。→ **AWS の `aud` キーは必ずしも JWT の `aud` ではない**。
- GitHub タブ: `actor`, `actor_id`, `job_workflow_ref`, `repository`, `repository_id`, `repository_owner_id`, `workflow`, `ref`, `environment`, `enterprise_id`（いずれも「Available in session: No」）。注意書き「名前は変わりうる。`repository_id`, `repository_owner_id`, `actor_id` など不変 ID を使え」。
- IdP 別タブ: AWS STS / Cognito / Login with Amazon / Facebook / GitHub / Google / CircleCI / OCI / GitLab.com / Buildkite。**任意のカスタムクレームを条件キーにできるわけではなく、AWS が IdP ごとに許可リスト化**している（それ以外の IdP は Default の数個のみ）。
- 多値キー（`amr` 等）は `ForAnyValue`/`ForAllValues` 集合演算子で評価。
- 実害: Datadog Security Labs（2023-07-27）は `sub` 条件のない GitHub 信頼ロールを実環境で多数発見（英国政府機関含む）。原因の一つに **Terraform/HCL で重複キー `StringEquals` の後勝ちにより `sub` 条件が黙って消える**問題（https://securitylabs.datadoghq.com/articles/exploring-github-to-aws-keyless-authentication-flaws/ ）。AWS Builder Center 記事は「500 超のロール ARN / 275 超アカウント」に言及（https://builder.aws.com/content/3Lv41qDVwoDbvPPuEwvuvAwmguL/scoped-or-spoofed-what-a-missing-oidc-condition-really-costs-you-in-aws ）**[数値は二次情報経由、Datadog 原典未確認]**。

**Google Cloud Workload Identity Federation** — https://docs.cloud.google.com/iam/docs/workload-identity-federation , https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines
- **attribute mapping** `TARGET_ATTRIBUTE=SOURCE_EXPRESSION`（CEL）。`google.subject`（必須・一意・127 文字以内）、`google.groups`、`attribute.*`（最大 50 個）。例: `google.subject='myprovider::' + assertion.aud + '::' + assertion.sub`、GUID→表示名の辞書引き、`assertion.department.join(".")`、`assertion.email.split("@")[0]`。→ **IdP 固有クレームを社内語彙に正規化する anti-corruption layer**。
- **attribute condition**（CEL、true なら受理）。GitHub: `assertion.repository_owner=='ORGANIZATION'`（+ `&& assertion.ref=='refs/heads/main'`）。GitLab: `assertion.namespace_id=='GROUP_ID'`。「GitHub org / GitLab group / HCP Terraform org に限定する attribute condition を必ず使え」「`repository`/`repository_owner` などの name フィールドは（乗っ取り）リスクを高める。一意で再利用されない数値 `*_id` を使え」。
- 同ページの例で `repository_id` は `"20300177"`、`repository_owner_id` は `"1342004"`（**文字列**）。→ CEL で `== 20300177`（数値）と書くと型不一致になる **[未検証: GCP 側の挙動は未確認、CEL の型規則からの推論]**。
- 「attribute condition で使う全フィールドに attribute mapping が必要」。`principalSet://.../attribute.NAME/VALUE` で属性値ごとに権限付与。

**Azure / Entra 連携 ID 資格情報** — https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation , https://learn.microsoft.com/en-us/entra/workload-id/workload-identities-flexible-federated-identity-credentials
- 通常の FIC: `issuer`/`subject`/`audience` を**大文字小文字区別で完全一致**。外部 IdP の署名鍵は先頭 100 個までしか保存しない。
- **Flexible FIC（preview）**: claims matching expression。構文 `claims['sub'] matches '...' and claims['repository_id'] eq '456789'`。演算子 `matches`（`?` 1 文字・`*` 複数文字ワイルドカード）と `eq`、比較値はシングルクォート文字列、区切りは単一スペース。
- クレームごとに使える演算子が限定: `sub`/`job_workflow_ref` は `eq`,`matches`、`repository_id`/`repository_owner_id` は `eq` のみ。「GitHub の式は `sub` と少なくとも 1 つの immutable claim を一致させよ」。GitLab で mutable sub を使うなら `sub` と `project_id` 両方。
- → **ワイルドカード対象を可変名クレームに限定し、不変 ID は完全一致のみ**という言語レベルのガードレール。

### 1.7 このカテゴリの教訓
- 多数 RP 向けトークンでは「RP が `sub` 1 本で一致判定する」前提で **`sub` を合成文字列**にし、テンプレート化・エスケープ規則・区切り文字を issuer が厳密に定義する必要がある（GitHub, GitLab）。
- 名前（可変）と ID（不変）を**対で**出し、RP には ID 側の一致を要求させる（GitHub/GitLab/K8s/Azure/GCP/OWASP WIF Cheat Sheet https://cheatsheetseries.owasp.org/cheatsheets/Workload_Identity_Federation_Cheat_Sheet.html 「Prefer immutable, non-reusable organization and repository identifiers」「Avoid wildcards that admit every repository」）。
- issuer が sub 形式を変える時は「RP 側を先に更新 → opt-in → 既定化（日付で）」の段階移行（GitHub 2026）。

---

## 2. プラットフォーム定義のカスタムクレーム規約

### 2.1 Hasura
出典: https://hasura.io/docs/2.0/auth/authentication/jwt/
- 既定 namespace `https://hasura.io/jwt/claims` の下に `x-hasura-default-role`（例 `"user"`）, `x-hasura-allowed-roles`（`["user","admin"]`）, `x-hasura-user-id`（`"123"`）, `x-hasura-org-id`, `x-hasura-*` 任意。default-role と allowed-roles は必須。
- 「All `x-hasura-*` values should be of type `String`」（Hasura が型変換）→ **値は文字列に統一**。「`x-hasura-default-role` 等のクレームフィールドは case-insensitive」。
- `claims_format`: `json`（既定）| `stringified_json`。理由「AWS Cognito のようにクレームに文字列しか許さない IdP があるため」→ **IdP 制約で JSON を文字列埋め込みせざるを得ない実例**。
- `claims_namespace` か `claims_namespace_path`（JSONPath、`$.hasura.claims` や `$`）のどちらか一方のみ。
- `claims_map`: IdP がカスタムクレームを入れられない場合、既存クレームの JSONPath（`{"path":"$.user.all_roles"}`、`default` 付き可）やリテラルで Hasura セッション変数に写像。`claims_map` があると namespace/format 設定は無視。JSONPath 先の値は文字列必須（allowed-roles は文字列配列）。→ **消費側マッピング層で IdP 差を吸収する設計**。

### 2.2 Supabase
出典: https://supabase.com/docs/guides/database/postgres/row-level-security , https://supabase.com/docs/guides/auth/jwt-fields
- 必須（除去不可）クレーム: `iss`, `aud`, `exp`, `iat`, `sub`, `role`, `aal`, `session_id`, `email`, `phone`, `is_anonymous`。`role` は `anon` / `authenticated` / `service_role`。例: `"amr": [{"method": "password", "timestamp": 1640991600}]`（オブジェクト配列）、`"app_metadata": {"provider": "email", "providers": ["email"]}`、`"user_metadata": {"name": "John Doe"}`。
- RLS ページ: 「`user_metadata` に依存する RLS ポリシーはセキュリティ問題を生む。認証済みエンドユーザーが変更できるから」「`raw_user_meta_data` は `supabase.auth.update()` でユーザーが更新可能。認可データの置き場所ではない」「`raw_app_meta_data` はユーザーが更新できないので認可データ向き」。
- 「JWT は常に最新とは限らない。app_metadata を更新しても JWT がリフレッシュされるまで `auth.jwt()` に反映されない」。
- 例: `using ( team_id in (select auth.jwt() -> 'app_metadata' -> 'teams'));` ＝**DB が JSON パスで直接クレームを読む**消費者。

### 2.3 Firebase custom claims
出典: https://firebase.google.com/docs/auth/admin/custom-claims , https://firebase.google.com/docs/auth/admin/create-custom-tokens
- ペイロード **1000 バイト上限**（超過でエラー）。JSON シリアライズ可能な型（string/number/boolean/array/object/null）のみ。
- 予約名（使用不可）: OIDC 系 `acr, amr, at_hash, aud, auth_time, azp, cnf, c_hash, exp, iat, iss, jti, nbf, nonce, sub`、Firebase 系 `firebase`, `user_id`。
- 「custom claims はアクセス制御専用。プロフィール等の追加データ保存は強く非推奨。全認証リクエストに ID トークンが乗るので性能問題」。
- `setCustomUserClaims` は**常に既存クレームを上書き**。`null` 指定で削除。
- 伝搬: 再ログイン/再認証、旧トークン期限切れ後のリフレッシュ、`getIdToken(true)` の強制リフレッシュのいずれかでのみ反映。

### 2.4 AWS ABAC: セッションタグ `https://aws.amazon.com/tags`
出典: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_session-tags.html

ネスト形式（公式例そのまま）:
```json
{
    "sub": "johndoe",
    "aud": "ac_oic_client",
    "jti": "ZYUCeRMQVtqHypVPWAN3VB",
    "iss": "https://xyz.com",
    "iat": 1566583294,
    "exp": 1566583354,
    "auth_time": 1566583292,
    "https://aws.amazon.com/tags": {
        "principal_tags": {
            "Project": ["Automation"],
            "CostCenter": ["987654"],
            "Department": ["Engineering"]
        },
        "transitive_tag_keys": [
            "Project",
            "CostCenter"
        ]
    }
}
```
フラット形式（「Microsoft Entra ID のようにネストを扱えない IdP 向け」）:
```json
{
    "https://aws.amazon.com/tags/principal_tags/Project": "Automation",
    "https://aws.amazon.com/tags/principal_tags/CostCenter": "987654",
    "https://aws.amazon.com/tags/principal_tags/Department": "Engineering",
    "https://aws.amazon.com/tags/transitive_tag_keys": [
        "Project",
        "CostCenter"
    ]
}
```
- 本文は「各 principal tag は単一の文字列値」「STS は多値セッションタグをサポートしない」と書く一方、ネスト例は `["Automation"]` と**1 要素配列**。→ **公式ドキュメント内でも string/array が揺れている**（消費側は両方許容しているように読める **[未検証: 実挙動未確認]**）。
- 制約: 50 タグまで、キー平文 128 文字、値 256 文字、セッションポリシー 2048 文字。タグとポリシーはセッショントークンサイズを消費（`SessionTokenUtilization` で監視、`PackedPolicySize` は非推奨）。
- 「新しいセッションタグは、**大文字小文字に関係なく**同じキーの既存タグを上書き」。信頼ポリシーに `sts:TagSession` 必須。transitive タグはロールチェーンで伝搬し `ResourceTag` を上書き。
- → 同じ論理データに **2 つの JSON 形状**（ネスト/フラット）を公式に許す＝ IdP 能力差への妥協。

### 2.5 Kubernetes JWT authenticator（StructuredAuthenticationConfiguration）
出典: https://kubernetes.io/docs/reference/access-authn-authz/authentication/
- **v1.34 で stable**（v1.29 初出、feature gate はロック）。`--authentication-config` と `--oidc-*` フラグ併用は起動エラー。authenticator 最大 64。
- 公式例（抜粋、そのまま）:
```yaml
  claimValidationRules:
  - claim: hd
    requiredValue: example.com
  - expression: 'claims.hd == "example.com"'
    message: the hd claim must be set to example.com
  - expression: 'claims.exp - claims.nbf <= 86400'
    message: total token lifetime must not exceed 24 hours
  claimMappings:
    username:
      expression: 'claims.username + ":external-user"'
    groups:
      expression: 'claims.roles.split(",")'
    uid:
      expression: 'claims.sub'
    extra:
    - key: 'example.com/tenant'
      valueExpression: 'claims.tenant'
  userValidationRules:
  - expression: "!user.username.startsWith('system:')"
    message: 'username cannot used reserved system: prefix'
  - expression: "user.groups.all(group, !group.startsWith('system:'))"
    message: 'groups cannot used reserved system: prefix'
```
- 型契約: claimValidationRules は bool、username/uid は string、groups と extra は「string または string のリスト」。username が空文字なら認証失敗。
- `extra` キー: ドメイン接頭辞パス必須（`example.org/foo`）、小文字、一意、`k8s.io`/`kubernetes.io` 予約。→ **組織内カスタム属性の命名規則をプラットフォームが強制**。
- `username.claim` を使うなら `prefix` 必須（不要なら明示的に `""`）。`--oidc-username-prefix` の目的は「既存名（`system:` ユーザー等）との衝突防止」、既定 `(Issuer URL)#`。
- `claims.email` を使うなら `email_verified` を必ずどこかで検査（推奨式 `claims.?email_verified.orValue(true) == true`、「明示的に true と比較することで非ブール値を実行時に捕捉」）。
- 「Distributed claims do not work via CEL expressions」。
- 例の `claims.roles.split(",")` は**カンマ連結文字列のロールを配列化**する変換 → 消費側で区切り文字を知っている必要がある。

### 2.6 Istio / Envoy
出典: https://istio.io/latest/docs/reference/config/security/request_authentication/ , https://istio.io/latest/docs/reference/config/security/conditions/ , https://istio.io/latest/docs/tasks/security/authorization/authz-jwt , https://github.com/envoyproxy/envoy/blob/main/api/envoy/extensions/filters/http/jwt_authn/v3/config.proto

**Istio RequestAuthentication**
- `outputClaimToHeaders`（Experimental）: `header`/`claim` 対。例 `x-my-company-jwt-group ← my-group`、`x-jwt-claim-group ← nested.key.group`。「ネストクレームの string/int/bool をサポート」「string/int/bool 以外は不可」「ヘッダが既にあれば上書き」「クレームが無い/型非対応ならヘッダは付かない」。
- `outputPayloadToHeader`、`forwardOriginalToken`（既定 false）。
- 「認証情報を含まないリクエストは受理される。認証済みのみに制限するには AuthorizationPolicy を併用」→ **RequestAuthentication 単体はゲートではない**。
- `spaceDelimitedClaims`: 「`scope` と `permission` は常に空白区切りとして分割。他のカスタムクレームはこのフィールドで opt-in。なければ `"admin editor"` は 1 つの完全文字列としてマッチ」。

**Istio AuthorizationPolicy 条件**
- `request.auth.claims[<name>]`（クォートなしの `[]`）、ネストは `request.auth.claims[nested1][nested2]`。**string または string リストのみ**サポート。`request.auth.principal` は `<iss>/<sub>`、`audiences` は `aud`、`presenter` は `azp`。HTTP のみ。

**Envoy jwt_authn**（main ブランチの proto コメント）
- `claim_to_headers`: 「string/int/double/bool はそのままコピー。**array/object は JSON 化して base64 でコピー**」。「ヘッダ名は（JWT 検証をバイパスする経路も含め）全プロバイダについてリクエストからサニタイズされ、検証成功時にクレーム値で置換」「このヘッダは JWT クレーム専用。他の値は上書き」。
- `claim_name` は「`.` で分割してネスト参照するため、**`http://example.org/parent_token` のような URL namespaced クレームは参照できない**。`claim_path`（キーを完全一致するセグメント列）を使え」。→ RFC 7519 推奨の URI 名と下流ツールが衝突する一次資料。
- `normalize_payload_in_metadata.space_delimited_claims`: `scope` 等を空白区切りでリスト化。
- `extract_only_without_validation`: 「署名を検証しない。誰でも任意クレームの JWT を偽造でき、それがヘッダとして転送される。完全検証済みのヘッダと**区別不能**（`verification_status_header` を確認しない限り）。RBAC/ext_authz/バックエンドが JWT 由来ヘッダで認可するなら使うな」。

### 2.7 Microsoft Entra ディレクトリ拡張属性
出典: https://learn.microsoft.com/en-us/entra/identity-platform/schema-extensions , https://learn.microsoft.com/en-us/entra/identity-platform/optional-claims
- 属性 ID は `extension_<appId(英数字のみ)>_<AttributeName>`。optional claims で JWT に出すと名前は `extn.<AttributeName>`（SAML では URI 形式）。claims mapping policy で任意の `JWTClaimType`（例 `http://schemas.contoso.com/identity/claims/exampleclaim`）に写像も可。
- 「全拡張を 1 つの専用アプリに登録する」パターンを推奨（appId が揃う）。
- Tip: 「拡張属性名は設定時は case-insensitive だが、トークンサービスが読むときは **case-sensitive**。`LegacyId` と `legacyid` で設定されたユーザーが混在すると、`LegacyId` で写像したクレームは後者に出ない」→ **大小文字の揺れでクレームが黙って欠落**。
- 「アクセストークンは常にリソース側のマニフェストで生成」→ クライアント側マニフェストを変えても Graph 向け AT は変わらない。

### 2.8 Okta Expression Language
出典: https://developer.okta.com/docs/guides/customize-tokens-returned-from-okta/main/ , https://developer.okta.com/docs/reference/api/oidc , https://developer.okta.com/docs/guides/customize-tokens-dynamic/main
- カスタムクレームは custom authorization server のみ（org AS 不可）。値は Groups filter か EL 式（最大 1024 文字、例 `user.preferredLanguage`）。スコープ単位で付与可、Token Preview タブで検証。
- `groups` クレームは 100 件上限、超過で**リクエスト失敗**（「将来変わりうる」）。`Groups.startsWith("OKTA", "IT", 10)` のような上限付き関数。
- 他のスコープ: カスタムスコープは `scp` クレームに入る（配列）**[未検証: 配列型は本ノートでは未確認、02_idp-claims.md 参照]**。

### 2.9 Auth0 namespaced claims
出典: https://auth0.com/docs/secure/tokens/json-web-tokens/create-custom-claims
- 現在は namespaced / non-namespaced 両方を許容（ただし制約あり）。「どうしても必要でない限り public の namespaced（collision resistant）を使え」。namespace は自分が管理する http/https URL（例 `http://www.example.com/favorite_color`）。
- 使用不可: `urn:auth0`、`auth0.com`/`webtask.io`/`webtask.run` ドメイン。`aud`, `iss`, `sub`, `roles`, `permissions` 等は変更不可。Auth0 API audience 向け AT には private（非 namespaced）カスタムクレーム不可。
- カスタムクレームペイロード上限 **100KB**、「重いペイロードを避けよ」。

### 2.10 Cloudflare Access アプリケーショントークン（ゲートウェイ発行の内部向け JWT）
出典: https://developers.cloudflare.com/cloudflare-one/identity/authorization-cookie/application-token/
```json
{
	"aud": ["32eafc7626e974616deaf0dc3ce63d7bcbed58a2731e84d06bc3cdf1b53c4228"],
	"email": "user@example.com",
	"exp": 1659474457,
	"iat": 1659474397,
	"nbf": 1659474397,
	"iss": "https://yourteam.cloudflareaccess.com",
	"type": "app",
	"identity_nonce": "6ei69kawdKzMIAPF",
	"sub": "7335d417-61da-459d-899c-0a01c76a2f94",
	"country": "US"
}
```
- IdP 由来のカスタム SAML 属性/OIDC クレームは `custom` クレームに **best-effort** で入る。シリアライズ後 **約 1KB 超で末尾から切り捨て**。「大きくなりうるカスタムクレームを認可判断に使うな」。完全な ID は `/cdn-cgi/access/get-identity` で取得。
- 「ヘッダの検証だけでは不十分。JWT と署名を確認しないと ID なりすましを許す」。
- → **サイズ超過で黙って欠落するクレームは認可に使えない**という一次資料。

---

## 3. サービスメッシュ / マイクロサービス内のコンテキスト伝搬

### 3.1 IETF draft-ietf-oauth-transaction-tokens（Txn-Token）
出典: https://datatracker.ietf.org/doc/draft-ietf-oauth-transaction-tokens/ , 本文 https://www.ietf.org/archive/id/draft-ietf-oauth-transaction-tokens-11.txt

- **現状（2026-11-17 時点）: draft-11（2026-07-30）、WG state「WG Consensus: Waiting for Write-Up」、IESG「I-D Exists」、本文ヘッダは Standards Track、期限 2027-01-31**。
- **依頼文にある `purp` / `azd` / `sub_id` は旧名**: 改訂履歴に「Since Draft 04: Renamed azd claim to tctx claim」「Since Draft 06: Rename the purpose claim to scope」。`sub_id` は draft-11 には存在しない（初期版で使われていた可能性 **[未検証]**）。
- ヘッダ: `typ` は `txntoken+jwt`（MUST）、`kid` で鍵ローテーション（SHOULD）。
- クレーム: `iss` OPTIONAL（単一 Trust Domain に束縛されるため）、`iat`/`aud`（Trust Domain を識別、外では受理禁止）/`exp` REQUIRED、`txn` REQUIRED（RFC 8417 §2.2 の一意 ID）、`sub` REQUIRED（Trust Domain 内で一意、**OIDC と違い iss に紐づかない**）、`scope` REQUIRED（TTS が決める。要求スコープや外部トークンのスコープと一致不要）、`tctx` RECOMMENDED（Call Chain 全体で不変の JSON オブジェクト）、`rctx` RECOMMENDED（環境コンテキスト）、`req_wl` REQUIRED（Txn-Token を要求したワークロード）。
- 「Txn-Token は仕様外の追加クレームを含んでよい。受信者は理解できないクレームを MUST 無視」。
- 公式例（Figure 4、コメント付き非規範例）:
```
{
  "iat": 1686536226,
  "aud": "trust-domain.example",
  "exp": 1686536586,
  "txn": "97053963-771d-49cc-a4e3-20aad399c312",
  "sub": "d084sdrt234fsaw34tr23t",
  "req_wl": "apigateway.trust-domain.example", // the internal entity that requested the Txn-Token
  "rctx": {
    "req_ip": "69.151.72.123", // env context of external call
    "authn": "face" // from RFC 8176
  },
  "scope" : "trade.stocks",
  "tctx": {
    "action": "BUY", // parameter of external call
    "ticker": "MSFT", // parameter of external call
    "quantity": "100", // parameter of external call
    "customer_type": { // computed value not present in external call
      "geo": "US",
      "level": "VIP"
    }
  }
}
```
  - `quantity` が文字列 `"100"` である点に注意（例示上の選択。数値精度問題を避ける慣行と整合）。
- 伝送: HTTP ヘッダ **`Txn-Token`**（MUST、値は Txn-Token ちょうど 1 個）。`Authorization: Bearer` と分けるのは「委任情報の AT と、トランザクション文脈の Txn-Token を区別するため」(§13.13)。「Txn-Token を OAuth AT として使ってはならない」「文脈を AT に入れずに済み、トークンサイズも減る」。
- 検証: 署名・`aud` が自 Trust Domain・期限（§12.2）。
- セキュリティ: 外部 AT を Txn-Token に含めてはならない（§13.4）。置換発行時は権限を広げる変更禁止、`txn`/`sub`/`aud` 変更禁止、Call Chain を維持（§13.15）。subject_token のスコープ不明なら拒否（§13.14）。
- 監査: `txn` を TTS と各ワークロードがログすることで成功/失敗トランザクションの追跡が可能、`txn` 記録でリプレイ検知も（§13.2）。**「Txn-Token 全体をそのままログしてはならない」。ハッシュか署名除去後のペイロードを、PII に注意してログ**（§15.2）。`req_ip` は個人情報になりうる（§15.1）。

### 3.2 Netflix "Passport"
出典: https://netflixtechblog.com/edge-authentication-and-token-agnostic-identity-propagation-514e47e0b602 （tavily 経由で本文抽出。日付・著者は本文から取れず **[未検証]**）, 講演 https://www.infoq.com/presentations/netflix-user-identity （QCon SF 2019, Satyajit Thadeshwar）
- 「Passport はリクエストごとに Edge（Zuul の Identity Filters）で作る短命の ID 構造。完全に Netflix 内部。user と device の ID を含み、**protobuf 形式で HMAC による完全性保護**」。外部トークン（デバイスの MSL トークン、ブラウザ Cookie、パートナー OAuth）はエッジで終端し、内部には Passport だけが流れる（"token-agnostic"）。
- 完全性要素: `message Integrity {int32 version = 1; string key_name = 2; bytes hmac = 3;}`。「version 1 は SHA-256。将来の version は別ハッシュ/エンコードを使いうる」→ **構造自体にバージョン番号**。
- 消費: 「Passport オブジェクトは opaque。クライアントは **Passport Introspector** でヘッダから取り出して中身を読む」。アクセサ例 `getCustomerId()`, `getAccountOwnerId()`, `getEsn()`, `getDeviceTypeId()`。→ **各サービスに生パースさせず、公式ライブラリ経由で読ませる**。
- Passport Actions: 下流サービスが ID 変更（ログイン等）をレスポンスで明示シグナルし、エッジがデバイス向けトークンを更新（講演）。
- 移行の教訓（講演 Q&A）: レガシー API を「Passport あり/なし両対応」に改修したが「遅く痛みを伴った」。
- 注: JWT ではないが、「エッジで外部資格情報を内部の正規化 ID 構造に交換する」パターンの代表例。

### 3.3 その他の当事者事例
- **Cloudflare Access**（§2.10）: ゲートウェイ（Access）が IdP 認証を終端し、オリジン向けに自前 JWT を発行、IdP カスタム属性は `custom` に best-effort 格納。
- **Uber MCP Gateway**（2026-10）: Uber Engineering の X 投稿で「MCP Gateway は呼び出し元の user token を下流に中継」「Third-Party MCP Service が internal user token を外部向け認証トークンに交換」と説明（https://x.com/UberEng/status/2106071967619322330 ）。**[本文ブログ未読・クレーム構造は未公開のため未検証]**
- Spotify / Airbnb / Shopify / Monzo について、内部トークンのクレーム設計を記した一次資料は今回見つからず（記載せず）。

### 3.4 OWASP の整理（2026 版チートシート）
- Identity Propagation Patterns（https://cheatsheetseries.owasp.org/cheatsheets/Identity_Propagation_Patterns_Cheat_Sheet.html ）: forwarding（「同じ資格情報を受理する受信者間の分離がない」）、token exchange（「下流が別 audience や明示的委任を要するとき」）、trusted internal assertions（「複数の外部認証方式が同じ内部サービス群に流れ込むときに推奨」）。「forwarding のために audience を広げるな」「trusted proxy header を使うならクライアント送信のコピーを除去し、プロキシを認証し、バイパスを防げ」「外部 ID を内部 ID に写像しても相関は防げない。署名は機密性を与えない」「内部アサーションをクライアント応答に出すな」。
- Authentication Patterns（https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Patterns_Cheat_Sheet.html ）: 「エッジで外部認証データを一度検証し、新規発行 JWT・HTTP Message Signatures 付きヘッダ・署名付き独自構造などの実装非依存形式で内部に伝搬」。
- Authorization Patterns（https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Patterns_Cheat_Sheet.html ）: 「下流は信頼 issuer・完全性・audience・期限・リクエストへの適用性を検証。信頼ヘッダを埋める前にクライアント送信のコピーを除去。署名だけではバイパス防止にも別リソース/テナント/操作の認可にもならない」。

---

## 4. 構造化認可データと「クレームか lookup か」

### 4.1 RFC 9396 `authorization_details`
出典: https://www.rfc-editor.org/rfc/rfc9396
- オブジェクト配列。各要素の `type`（REQUIRED、文字列）が許容フィールドを決める。同じ type の複数要素可。
- §2.1: type 値は「曖昧さなくコピーできる値に。Unicode で同じ見た目の別コードポイントがある。ASCII に限る、機械可読リストを提供する等」。「複数サーバーに展開される API なら、自分が管理する URI など**衝突耐性のある namespace**を推奨」。
- §5: **AS は未知 type・既知 type の未知フィールド・型違い・不正値を拒否**（`invalid_authorization_details`）。
  - 依頼文の「RS は未知 type を無視せよ」という規定は RFC 9396 本文には見当たらず **[未検証/該当記述なし]**。RS 側の扱いは §9「RS 固有ポリシーで AS と決める」に委ねられている。一般則としては RFC 7519 §4「理解できないクレームは MUST 無視」がある。
- §9.1: JWT AT では「**audience 向けにフィルタした** authorization_details をトップレベルクレームとして入れることを推奨」。例（そのまま）:
```json
   {
      "iss": "https://as.example.com",
      "sub": "24400320",
      "aud": "a7AfcPcsl2",
      "exp": 1311281970,
      "acr": "psd2_sca",
      "txn": "8b4729cc-32e4-4370-8cf0-5796154d1296",
      "authorization_details": [
         {
            "type": "https://scheme.example.com/payment_initiation",
            "actions": [
               "initiate",
               "status",
               "cancel"
            ],
            "locations": [
               "https://example.com/payments"
            ],
            "instructedAmount": {
               "currency": "EUR",
               "amount": "123.50"
            },
            "creditorName": "Merchant A",
            "creditorAccount": {
               "iban": "DE02100100109307118603"
            },
            "remittanceInformationUnstructured": "Ref Number Merchant"
         }
      ],
      "debtorAccount": {
         "iban": "DE40100100103307118608",
         "user_role": "owner"
      }
   }
```
  - `txn` は「provider 内でトランザクションを追跡するための ID」、`debtorAccount` は認可時にユーザーが選んだ API 固有フィールド。金額は**文字列 `"123.50"`**。
- §11.3: type を JSON Schema の識別子にしてよいが「type が機械可読スキーマを指すとも、誰かが dereference するとも仮定しない」。§11.4: 大きいので PAR（RFC 9126）推奨。

### 4.2 RFC 9068 §2.2.3.1（groups / roles / entitlements）
出典: https://www.rfc-editor.org/rfc/rfc9068
- 委任以外の認可属性（ロール/グループ所属、エンタイトルメント）を AT に入れるなら、SCIM User スキーマ（RFC 7643 §4.1.2）の `groups`, `roles`, `entitlements` をクレーム型として使うべき（SHOULD）、値も RFC 7643 に従ってエンコード。ただし「roles と entitlements には特定の語彙は定めない」。
- → **名前は標準化、値の語彙は組織が決める**必要がある。

### 4.3 「トークンに入れるべきでないもの」
- **Zanzibar**（USENIX ATC'19, https://www.usenix.org/system/files/atc19-pang.pdf ）: "new enemy" 問題 =「ACL 更新の順序を守らない、または古い ACL を新しいコンテンツに適用すると起きる」。例 B「Alice が Bob を文書 ACL から外す → Charlie が新内容を追加 → 古い ACL で評価すると Bob に見えてしまう」。対策は外部一貫性と zookie による staleness 上限付きスナップショット読み取り。→ 発行時点の権限を凍結した JWT はこの保証を原理的に持てない（推論）。
- **OpenFGA**（https://openfga.dev/docs/modeling/token-claims-contextual-tuples , https://openfga.dev/docs/interacting/contextual-tuples ）: トークンの `groups` を contextual tuples として渡せるが「関係がトークン有効期間中に変わっても、ユーザーはトークンの内容に基づくアクセスを持ち続ける」「グループ所属などが変わってもトークン期限までアクセスが続く」。contextual tuple は 1 リクエスト 100 件上限。
- **Amazon Verified Permissions**（https://docs.aws.amazon.com/verifiedpermissions/latest/apireference/API_IsAuthorizedWithToken.html ）: 「署名と期限は検証する。**トークン失効やリソース削除はトークンの有効性に影響しない**」。ID トークンの属性クレームは principal 属性、AT のクレームは context に写像（https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/identity-sources.html ）。Cognito 連携では pre token generation で `cognito`, `dev`, `custom` という名前のクレームを追加するな（予約接頭辞）（https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-authorization-with-avp.html ）。
- **Curity**（https://curity.io/resources/learn/claims-best-practices/ ）: 「揮発的な業務権限は AS ではなく API で管理」「API はアクセストークン内のクレームから揮発的権限を lookup できる」「頻繁に使うクレームだけ入れる」「AT のバージョニングが必要になる設計を避けよ」「AS のクレーム設定変更を頻繁に要する設計を避けよ」。
- **Firebase**（§2.3）: custom claims はアクセス制御専用、他データは DB へ。1000 バイト。
- **Cloudflare**（§2.10）: 1KB 超で切り捨てられるクレームを認可に使うな。

---

## 5. 監査 / 来歴（provenance）クレーム

### 5.1 `act`（RFC 8693 §4.1）
出典: https://www.rfc-editor.org/rfc/rfc8693
- `act` は JSON オブジェクト、中身は actor を識別するクレーム（`iss`+`sub` の組合せが必要な場合あり）。`exp`/`nbf`/`aud` 等の非 ID クレームは `act` 内では意味を持たない。
- ネストで委任チェーン（外側が現 actor、最深部が最古）。**「アクセス制御にはトップレベルクレームと現 actor のみを使う。ネストした過去の actor は情報提供のみ」** → 監査には残すが認可には使わない、という**クレームの用途区分を仕様が明記**。
```json
    {
      "aud":"https://service26.example.com",
      "iss":"https://issuer.example.com",
      "exp":1443904100,
      "nbf":1443904000,
      "sub":"user@example.com",
      "act":
      {
        "sub":"https://service16.example.com",
        "act":
        {
          "sub":"https://service77.example.com"
        }
      }
    }
```
- `scope` クレームは「空白区切りリストの JSON 文字列」（§4.2）。

### 5.2 同意 / インテント参照
- **UK Open Banking**（https://openbankinguk.github.io/read-write-api-site3/v3.1.2/profiles/read-write-data-api-profile ）: 「`id_token` は常に認可された `intent_id` を識別する」。CIBA の `login_hint_token` で URL namespace 付きカスタムクレーム `http://openbanking.org.uk/sit`（`UID`/`EUID`/`IID`/`ID_TOKEN`）、`http://openbanking.org.uk/openbanking_intent_id`。
  - 同一ページ内で `openbanking-intent-id`（ハイフン）と `openbanking_intent_id`（アンダースコア）の**表記揺れ**がある → **仕様書の誤記がそのまま相互運用バグになりうる**好例。
  - ID トークン/リクエストオブジェクト内の素の `openbanking_intent_id` クレーム（`essential: true` 要求）は UK OB Security Profile 由来とされるが、本調査では原文未確認 **[未検証]**。
- **Open Finance Brasil**（https://github.com/OpenBanking-Brasil/specs-seguranca/blob/main/open-banking-brasil-financial-api-1_ID3.md ）: 同意 ID をクレームではなく**動的スコープ** `consent:urn:bancoex:C1DD33123` で運ぶ。Consent Resource Id は URL セーフ・namespace 付き・nonce 性。AT は有効な同意に紐づく間のみ利用可、RT は同意期限を超えてはならない。
- **RFC 9396** 例（§4.1）: 指示金額 `instructedAmount`・受取人・`txn` を AT に直接埋め込み、RS がそれと照合。

### 5.3 相関 ID: トークン内 vs ヘッダ
- トークン内: Txn-Token `txn`（Trust Domain 内一意、ログ・リプレイ検知用）、RFC 9396 例の `txn`、GitHub `run_id`/`check_run_id`、Netflix Passport（リクエスト単位）。
- ヘッダ: W3C Trace Context（W3C Recommendation 2021-11-23, https://www.w3.org/TR/trace-context/ ）`traceparent`（例 `00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01`）。「これらのフィールドの唯一の目的はトレース相関」「tracestate に PII を入れてはならない」「trace flags は呼び出し側の推奨にすぎない」。
- 整理: **署名済みトークン内の ID は改ざん不可で監査証跡向き、trace ヘッダは改ざん可能で観測性向き**（推論。Txn-Token §13.2 と W3C の記述から）。

### 5.4 「目的」クレーム
- Txn-Token の旧 `purp` は draft-06 で `scope` に統合。§9.2.1「scope はこのトランザクションの目的を可能な限り狭く表す。値は Trust Domain の認可モデルを表すよう TTS が定義」。
- Curity Identity Server はトークン種別判別用に `purpose` クレーム（`access_token`/`id_token`）を付与（https://curity.io/resources/learn/jwt-best-practices ）→ **同名でも「目的」の意味が異なる**ため、名前だけで判断しない。

### 5.5 監査ログに何を残すか
- OWASP Logging Cheat Sheet（https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html ）: 各イベントに「when, where, who and what」。who = 送信元アドレス、ユーザー ID（DB 主キー、ユーザー名等）。"Interaction identifier" で 1 回の操作に属するイベントを連結。**除外**: セッション ID（必要ならハッシュ化）、**access tokens**、機微 PII、パスワード、鍵等。
- Txn-Token §15.2: トークン全文ログ禁止、ハッシュか署名除去ペイロード（PII 注意）。
- GitHub `check_run_id` 追加理由（§1.1）、OWASP WIF Cheat Sheet「トークン交換・ロール使用の監査イベントを有効化し、どの ID フィールドが記録されるかを確認、CI/CD 実行記録と相関させよ。完全なワークフロー帰属は自動ではない」。
- NIST SP 800-92 は今回参照していない（記載なし）。

---

## 6. 組織横断クレームカタログのガバナンス

一次資料で確認できたものに限定。「クレームの JSON Schema レジストリ」「issuer–consumer 間の契約テスト」を**明示的に推奨する vendor 文書は今回見つからなかった** **[未検証/発見できず]**。以下は確認できた周辺実践。

| 実践 | 実例 | 出典 |
|---|---|---|
| 衝突耐性のある名前（RFC 7519 §4.2 Public Name / IANA 登録） vs 合意済み Private Name（§4.3 「衝突しうるので注意」） | Auth0 URL namespace 推奨、Hasura `https://hasura.io/jwt/claims`、AWS `https://aws.amazon.com/tags`・`https://sts.amazonaws.com/`、K8s `kubernetes.io`、UK OB `http://openbanking.org.uk/...` | https://www.rfc-editor.org/rfc/rfc7519 , §2 各節 |
| 予約名・予約 namespace の明文化 | Firebase 予約リスト、Auth0 `urn:auth0`・auth0.com 等、K8s extra の `k8s.io`/`kubernetes.io`、Cognito/AVP の `cognito`/`dev`/`custom` | §2.3, §2.9, §2.5, §4.3 |
| 組織メタデータの単一ソース化 | GitHub `repo_property_*`（「repository governance model と cloud access controls を揃える」） | GitHub changelog 2026-04-02 |
| クレーム辞書をポリシー語彙と対応付けて文書化 | AWS outbound JWT の各クレームに「Source condition key」列 | §1.5 |
| 消費側の正規化（anti-corruption）層 | GCP attribute mapping、K8s claimMappings/CEL、Hasura claims_map、Netflix Passport + Introspector、OWASP trusted internal assertions、Curity「APIs should only use claims asserted by the centralized server and should not add additional information nor issue tokens」（https://curity.io/resources/learn/api-security-best-practices ） | §1.6, §2.5, §2.1, §3.2, §3.4 |
| 破壊的変更としての扱い・段階移行 | Curity「Changing the content of a token should be considered a breaking change」（https://curity.io/resources/learn/what-are-claims-and-how-they-are-used ）、GitHub immutable sub の opt-in→日付で既定化＋プレビュー endpoint、GitHub「RP 側条件を先に作れ」、GitLab sub components 変更時の「各外部サービスの trust policy を更新せよ」 | §1.1, §1.2 |
| 名称変更の記録 | Txn-Token 改訂履歴（azd→tctx, purpose→scope） | §3.1 |
| 構造内バージョン | Netflix Passport `Integrity.version` | §3.2 |
| 発行前プレビュー/デバッグ | GitHub `actions-oidc-debugger`、Okta Token Preview タブ | §1.1 参照ページ, §2.8 |
| 移行期の二重対応 | Netflix レガシー API の「Passport あり/なし両対応」 | §3.2 |
| サイズ・件数上限の明文化 | Firebase 1000B、Auth0 100KB、Cloudflare `custom` ~1KB、Okta groups 100、GitLab groups_direct 200、AWS タグ 50/128/256、GCP 属性 50・google.subject 127 文字、K8s authenticator 64 | §各節 |

---

## 7. カスタムクレーム特有のパース落とし穴

| # | 落とし穴 | 一次資料・実例 |
|---|---|---|
| 1 | **string vs array**（`aud`） | RFC 7519 §4.1.3: 一般には大小区別文字列の配列、単一なら文字列でもよい（MAY）。K8s SA は常に配列、Cloudflare は配列、GitLab は文字列。 |
| 2 | **空白区切り文字列**（`scope`）を配列と思い込む／逆 | RFC 8693 §4.2。Istio は `scope`/`permission` のみ自動分割、他は `spaceDelimitedClaims` で opt-in、無ければ `"admin editor"` は完全一致文字列（authz-jwt タスク）。Envoy `space_delimited_claims`。 |
| 3 | **区切り文字の独自規約**（カンマ連結） | GitHub multi-select `"us-east-1,eu-west-1"`、K8s 例 `claims.roles.split(",")`。 |
| 4 | **文字列化 JSON** | Hasura `claims_format: stringified_json`（Cognito は文字列のみ許容）。Envoy は array/object クレームを JSON→base64 してヘッダ化。 |
| 5 | **string 比較の取り違え**（`in` が部分一致になる） | **CVE-2024-53861**（PyJWT 2.10.0）: `iss` 検査を `isinstance(issuer, Sequence)` に変えた結果、str も Sequence なので `in` で部分文字列比較になり `"acb"` が `"_abc_"` で通る。2.10.1 で修正（https://nvd.nist.gov/vuln/detail/CVE-2024-53861 ）。 |
| 6 | **数値 ID vs 文字列 ID / 精度** | GitLab 例で ID は文字列、`runner_id` は数値。GCP 例の `repository_id` は文字列。Bishop Fox: 大きな数値は「`MAX_INT` や `0` にデコードされうる」、49 パーサ調査（https://bishopfox.com/blog/json-interoperability-vulnerabilities , 2021-02-25）。RFC 9396 例・Txn-Token 例とも金額/数量は文字列。JS の安全整数上限（2^53−1）超の ID は文字列で運ぶべき **[未検証: 本調査で個別一次資料未取得、一般知識]**。 |
| 7 | **ブールの文字列化** | GitHub `repo_property_*` の `"true"`/`"false"`、GitLab `"ref_protected": "false"`、AWS `mfa_present: "true"`。`if (claim)` で `"false"` が truthy になる **[推論]**。K8s は `claims.?email_verified.orValue(true) == true` と明示比較を推奨。 |
| 8 | **重複キー** | RFC 7519 §4: 重複クレーム名の JWT は拒否するか「字句的に最後」を返すパーサを使え（MUST）。Bishop Fox: 先勝ち（Go の例）と後勝ち（Python 標準）が混在 → パーサ差で検証側と利用側が別値を見る。Datadog: Terraform/HCL の重複 `StringEquals` 後勝ちで `sub` 条件消失。 |
| 9 | **null vs absent vs 空** | GitLab `ci_config_ref_uri` は null、`environment` は absent、`groups_direct` は 200 超で absent（＝「0 グループ」と区別不能）。AWS `mfa_present` は absent＝false 規約。Istio は「クレームが無いとヘッダを付けない」。Firebase は `null` で全削除。 |
| 10 | **大文字小文字** | RFC 7519: StringOrURI は「変換なしの大小区別比較」。Hasura クレーム名は case-insensitive。Entra 拡張属性は読み取り時 case-sensitive で欠落。AWS セッションタグは大小無視で上書き。Entra FIC は大小区別完全一致。 |
| 11 | **Unicode の見た目同一** | RFC 9396 §2.1（type 値は ASCII 推奨）。Bishop Fox: 文字切り詰めによるキー衝突「Do not perform character truncation」。正規化（NFC 等）を明示した一次資料は今回なし **[未検証]**。 |
| 12 | **URL namespace とパス表記の衝突** | Envoy `claim_name` は `.` 分割のため `http://example.org/parent_token` 等は参照不可 → `claim_path`。Istio `outputClaimToHeaders` の `nested.key.group` 記法も同種の制約がある可能性 **[未検証]**。 |
| 13 | **クレーム→ヘッダ変換とスプーフィング** | Istio は既存ヘッダを上書き、Envoy は全プロバイダでサニタイズ。だが Envoy `extract_only_without_validation` は検証済みと区別不能。**CVE-2023-27487**: Envoy が内部ヘッダ `x-envoy-original-path` をクライアントから除去せず、`jwt_authn` の判定 URL 等に使われ JWT チェック回避（1.26.0 等で修正）。**CVE-2025-64484**: OAuth2-Proxy が `X-Forwarded-*` のアンダースコア変種を除去せず、Django/Flask/FastAPI/PHP 等が `_`→`-` 正規化して信頼ヘッダ扱い（7.13.0 で修正、大小・`_`/`-` を無視して正規化除去）。**CVE-2026-26308**: Envoy RBAC が同名ヘッダの複数値をカンマ連結して照合、重複ヘッダで Deny ルール回避（1.37.1 等で修正）。（いずれも NVD API で記述確認） |
| 14 | **サイズ超過時の黙った欠落/失敗** | Cloudflare `custom` 切り捨て、GitLab groups_direct 省略、Okta groups 100 超で失敗、AWS セッショントークンサイズ超過で失敗。 |
| 15 | **CEL / 式言語のミス** | GCP: attribute condition 未設定・name 条件で他テナント受理。K8s: `email` 使用時の `email_verified` 未検査、空 username。Azure flexible FIC: `matches` ワイルドカードを可変名に使うなら immutable ID の `eq` 併用必須。AWS: `sub` 条件欠落（Datadog）。OWASP WIF「全リポジトリを許すワイルドカードを避けよ」。 |
| 16 | **AWS の `aud` 条件キーが `azp` を指す** | AWS 条件キー表（§1.6）。名前が同じでも意味が違う写像。 |
| 17 | **ドキュメント例自体の型揺れ** | AWS セッションタグ（「単一文字列」と書きつつ例は配列）、UK OB（hyphen/underscore 表記揺れ）。 |

---

## 8. (a) 組織横断カスタムクレームの設計パターン / アンチパターン カタログ（36 件）

P = 推奨パターン、A = アンチパターン

| # | 種別 | 名称 | 要点 | 出典 |
|---|---|---|---|---|
| 1 | P | 不変 ID を一致条件に | 名前は表示/補助、認可条件は `*_id`/uid | GitHub immutable sub; GitLab; AWS GitHub タブ; GCP; OWASP WIF |
| 2 | A | 名前ベースの `sub` に依存 | rename/再取得で他者が同じ sub を得る | GitHub changelog 2026-04-23; GitLab パス再利用ブロック |
| 3 | P | 名前と ID の対出力 | `name`+`uid`（K8s）、`repository`+`repository_id` | K8s SA トークン例; GitHub reference |
| 4 | P | 合成 sub のテンプレート化と区切り文字設計 | 区切り `:`、値内 `:`→`%3A`、名前に現れない `@` で ID 連結 | GitHub reference |
| 5 | P | 発行側変更は RP 先行・opt-in・期日既定化 | 条件を先に作る→テンプレ変更、プレビュー endpoint | GitHub reference/changelog |
| 6 | P | 衝突耐性 namespace（URI/ドメイン） | RFC 7519 §4.2、Auth0/Hasura/AWS/K8s | RFC 7519; Auth0; Hasura; AWS |
| 7 | A | 接頭辞なし private claim の乱立 | 「衝突しうるので注意」 | RFC 7519 §4.3; SPIFFE §3 |
| 8 | P | 単一 namespace オブジェクトへの集約 | `kubernetes.io`、`https://sts.amazonaws.com/` | K8s; AWS outbound |
| 9 | A | 「.」を含むクレーム名をドット記法ツールで参照 | Envoy `claim_name` 不可 → `claim_path` | Envoy proto |
| 10 | P | 書き込み主体ごとにクレームを分離 | issuer 付与 vs 呼出側自己申告 vs ユーザー編集可 | AWS `principal_tags`/`request_tags`; Supabase; Txn-Token `rctx`/`tctx` |
| 11 | A | ユーザー編集可能なメタデータで認可 | Supabase `user_metadata` 警告 | Supabase RLS |
| 12 | P | 型を 1 つに固定し文書化（ID・金額は文字列） | Hasura「値は String」、RFC 9396/Txn-Token 例の文字列数値 | Hasura; RFC 9396; Txn-Token |
| 13 | A | 同種値の型混在（ID が文字列/数値、ブールが文字列） | GitLab 例 | GitLab docs |
| 14 | A | 配列をカンマ/空白連結文字列で表現 | 消費側に分割規則を強いる | GitHub multi-select; K8s 例; Istio spaceDelimitedClaims |
| 15 | A | 文字列化 JSON | IdP 制約時の妥協。可能なら JSON オブジェクト | Hasura claims_format |
| 16 | P | absent/false/null の意味を規約化 | `mfa_present` は absent=false | AWS outbound |
| 17 | A | 上限超過で黙って欠落するクレームを認可に使う | Cloudflare `custom`、GitLab groups_direct | Cloudflare; GitLab |
| 18 | P | サイズ予算と件数上限の明文化 | 1000B/100KB/~1KB/100件/50タグ | Firebase; Auth0; Cloudflare; Okta; AWS |
| 19 | A | プロフィール等の非認可データをトークンに | 全リクエストに乗り性能劣化 | Firebase best practices |
| 20 | A | 細粒度・揮発的権限や関係をトークンに焼く | staleness・new enemy・失効不能 | Zanzibar; OpenFGA; AVP; Curity |
| 21 | P | 安定属性はクレーム、揮発権限は lookup | 「APIs can look up ... volatile business permissions from claims」 | Curity claims best practices |
| 22 | P | audience ごとにフィルタした詳細 | authorization_details を aud 向けに絞る、単一 aud 推奨 | RFC 9396 §9.1; SPIFFE §7.2; OWASP IPP |
| 23 | P | type タグ付き構造化オブジェクト + AS 側厳格検証 | 未知 type/フィールドは AS が拒否 | RFC 9396 §5 |
| 24 | P | 理解できないクレームは無視（前方互換） | RFC 7519 §4、Txn-Token §9.2 | RFC 7519; Txn-Token |
| 25 | P | エッジで外部トークンを内部トークンに交換（ACL） | Passport、Txn-Token、Cloudflare Access、OWASP trusted internal assertions | Netflix; IETF; Cloudflare; OWASP |
| 26 | P | 公式パーサ/イントロスペクタ経由で読ませる | Passport Introspector | Netflix |
| 27 | P | 消費側の宣言的マッピング層（CEL/JSONPath） | GCP attribute mapping、K8s claimMappings、Hasura claims_map | GCP; K8s; Hasura |
| 28 | P | 予約名/予約接頭辞の検証ルール | `system:` 禁止、`k8s.io` 予約、Firebase/Auth0/Cognito 予約 | K8s; Firebase; Auth0; Cognito/AVP |
| 29 | A | クレーム由来ヘッダを、クライアント送信分を除去せず信頼 | CVE-2023-27487 / CVE-2025-64484 / CVE-2026-26308、OWASP | NVD; OWASP Authorization Patterns |
| 30 | A | 署名未検証でクレームを抽出・転送 | Envoy extract_only 警告 | Envoy proto |
| 31 | P | 文脈トークンと権限トークンの分離 | `Txn-Token` ヘッダ vs `Authorization`、AT に文脈を入れない | Txn-Token §12.1, §13.13 |
| 32 | P | 委任チェーンは記録するが認可は現 actor のみ | `act` ネストは情報提供用 | RFC 8693 §4.1 |
| 33 | P | 監査用一意 ID クレーム＋全文ログ禁止 | `txn`、`check_run_id`、ハッシュ/署名除去ログ、AT はログしない | Txn-Token §13.2/§15.2; GitHub; OWASP Logging |
| 34 | P | 「検証されない情報提供クレーム」を明示 | K8s node 情報は apiserver 非検証と明記 | K8s SA docs |
| 35 | A | 仕様書内の名前・型の表記揺れ | UK OB hyphen/underscore、AWS 文字列/配列 | UK OB profile; AWS session tags |
| 36 | P | クレーム集合を API 契約として扱う | 変更は breaking change | Curity |

---

## 9. (b) 新しい共有カスタムクレームを追加する前にテックリードが答えるべき質問

**目的・必要性**
1. このクレームで RP は何を決めるのか（認可・ルーティング・監査・表示）。認可に使わないならトークンに入れる必要はあるか？（Firebase「アクセス制御専用」）
2. 値の変更頻度は？ トークン寿命中に変わったら、旧値で許可され続けて問題ないか？（Supabase/OpenFGA/AVP、Zanzibar new enemy）変わるなら lookup/PDP にすべきでは？
3. 既存の標準クレーム（`sub`, `scope`, `act`, `authorization_details`, RFC 9068 の `groups`/`roles`/`entitlements`）や Txn-Token の `tctx` で表現できないか？

**名前・構造**
4. 名前は衝突耐性 namespace（自組織管理の URI/ドメイン）か、合意済み private 名か？ 予約名（Firebase/Auth0/Cognito/K8s）と衝突しないか？
5. namespace に「.」「/」を含む場合、全消費ツール（Envoy `claim_name`、Istio、CEL、JSONPath）で参照できるか？
6. トップレベルか、組織 namespace オブジェクト配下か？ ネスト不可の IdP（Entra 等）向けにフラット形式も必要か？（AWS の 2 形式）

**型・値**
7. JSON 型は何か（string / array / object / number / bool）。単一値でも常に配列か？ 区切り文字連結や文字列化 JSON を避けられるか？
8. ID は文字列で運ぶか（2^53 超、先頭ゼロ、言語間精度）。金額・数量は？
9. ブールは JSON ブールか。absent/null/false/空配列 の意味をどう定義するか？
10. 大文字小文字・Unicode 正規化・前後空白の扱いは？ 比較は完全一致か？
11. 値は誰が書けるか（IdP 管理者／本人／呼び出し元サービス）。自己申告値と issuer 確認値を別名にしているか？
12. 名前（可変）と ID（不変）を両方出し、RP には ID での一致を要求しているか？ 再利用・改名時に何が起きるか？

**サイズ・性能**
13. 最大サイズ・最大要素数は？ 上限超過時は「失敗」か「欠落」か、RP はそれを検知できるか？（Okta 100、GitLab 200、Cloudflare 1KB）
14. 全リクエストに乗せる価値があるか（ヘッダ長上限・帯域）？ audience ごとに絞れるか？

**発行・消費・境界**
15. 単一の発行者（AS/TTS/エッジ）だけが付与するか？ 各サービスが独自にクレームを足す余地を残していないか？（Curity）
16. RP 側の検証手順（署名・iss・aud・exp・型チェック）を共通ライブラリ/Introspector で提供するか？
17. ゲートウェイでヘッダに展開するなら、クライアント送信の同名ヘッダ（大小・`_`/`-` 変種・重複を含む）を除去し、バイパス経路を塞いでいるか？
18. 未検証の値をヘッダに流すモードが存在しないか？ 下流はヘッダではなく JWT を再検証すべきか？
19. 理解しない RP はこのクレームを無視して安全か（fail-open にならないか）？ 必須クレームとして RP に拒否させるべきか？

**監査・プライバシー**
20. 監査ログに記録するか（値そのもの／ハッシュ）。PII か？ トークン全文はログされないか？（OWASP Logging、Txn-Token §15）
21. 委任・代理実行の場合、`act` チェーンや承認/同意 ID（`intent_id`, consent ID, `txn`）との関係は？

**ガバナンス・ライフサイクル**
22. カタログ（名前・型・意味・発行者・許可消費者・上限・PII 区分・オーナー）に登録したか？ 消費者一覧を把握できるか？
23. 形式・意味を変える時の移行計画（RP 先行更新 → opt-in → 期日で既定化 → 旧形式廃止）とプレビュー手段はあるか？（GitHub 2026）
24. 改名・廃止時の互換期間と並行発行の方針は？ 「トークン内容の変更は breaking change」として扱うレビュー手順があるか？
25. 発行前に実トークンを確認できるデバッグ/プレビュー手段（actions-oidc-debugger、Okta Token Preview 相当）と、消費側ポリシー（CEL/条件キー）のテストを用意したか？

---

## 10. 不確実事項・未検証一覧

- Netflix ブログの公開日・著者（本文抽出のみ、メタデータ未取得）。
- Datadog「500 超ロール / 275 超アカウント」は AWS Builder Center 記事経由（原典で数値未確認）。
- UK OB Security Profile の id_token / request object 内 `openbanking_intent_id`（`essential`）の原文。
- Txn-Token の `sub_id` クレームの存在時期（draft-11 には無い）。
- RFC 9396 に「RS は未知 type を無視せよ」の明文は見当たらず（AS 側の拒否規定のみ）。
- GCP CEL で文字列 ID と数値リテラルを比較した場合の挙動、AWS セッションタグのネスト形式で文字列/配列のどちらが実際に受理されるか、Istio `outputClaimToHeaders` で「.」を含むクレーム名を扱えるか（いずれも実機未確認）。
- JWT クレームの JSON Schema レジストリ／issuer–consumer 契約テストを推奨するベンダー一次資料は発見できず。
- Okta `scp` の型（本ノートでは未確認）。
- Spotify / Airbnb / Shopify / Monzo の内部トークン設計は一次資料を発見できず。Uber は X 投稿のみ。
- NIST SP 800-92 は未参照。
