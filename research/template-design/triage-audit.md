# 振り分けの点検：引いた lint の規則は、問いの答えを本当に決めるか（#56）

> **道具による確かめ。人による点検ではない。** `python tools/review_triage_audit.py --write` が書く。手で直さない。

`templates/review/triage.yaml` で「既存の規則が答えを決める（レビュアーも書き手も答えない）」とした問いを、1 問ずつ確かめた記録です。
記入例の写しを、その問いの答えが No になるように 1 か所書き換え、claim_lint が、引いた規則の error か warn を新しく出すかを見ます（PR #71 の独立点検が使った確かめ方。そこで 5 問が外れた）。出さなければ、その規則は問いを決めていないので、この区分から外します。

- 結果：47 問のうち 47 問で、規則が指摘を出した
- 分かること：その書き換えを、規則が拾うこと
- 分からないこと：答えが No になる書き方の全部を規則が拾うか（1 問につき書き換えは 1 つ）。受け手が宣言どおりに動くか（規則は宣言どうしを比べるだけ。`tools/claim_lint/RULES.md`）
- 「SCHEMA」は、スキーマがその値を許さず、規則の手前で機械が止めたもの
- `tools/tests/test_review_triage.py` が同じ確かめを走らせる（区分を変えて、書き換えの無い問いができると落ちる）

| 問い | 引いた規則 | 書き換え（答えを No にする） | 元の記入例 | 新しく出た指摘 | 判定 |
| --- | --- | --- | --- | --- | --- |
| `dc-01` | L5 | C-department の volatility を 10 秒にし、対策（on_revoke・recompute_trigger）を消す | `templates/examples/scenario-b` | L5 +3 | 決める |
| `dc-09` | L3 | C-user-id の identifier_properties.stable を false にする | `templates/examples/scenario-b` | L3 +1 | 決める |
| `dc-10` | L31・L4 | C-roles の provenance を「本人が編集できる値」にする | `templates/examples/scenario-b` | L31 +1 | 決める |
| `dc-11` | R8・R1 | C-roles の max_items・overflow_strategy を消す | `templates/examples/scenario-b` | R8 +2・R1 +2・SCHEMA +1 | 決める |
| `dc-12` | L7・L4 | 必須の C-roles の on_missing を「無視」にする | `templates/examples/scenario-b` | L7 +2 | 決める |
| `dc-gate` | R1 | C-roles の description を消す | `templates/examples/scenario-b` | R1 +1 | 決める |
| `pa-02` | L5 | C-department の volatility を 10 秒にし、対策（on_revoke・recompute_trigger）を消す | `templates/examples/scenario-b` | L5 +3 | 決める |
| `pa-11` | L31 | C-roles の書き手の configurable_by を end_user にする | `templates/examples/scenario-b` | L31 +1 | 決める |
| `pa-12` | L3 | C-user-id の identifier_properties.stable を false にする | `templates/examples/scenario-b` | L3 +1 | 決める |
| `pa-13` | R8 | C-roles の max_items・overflow_strategy を消す | `templates/examples/scenario-b` | R8 +2・SCHEMA +1 | 決める |
| `pa-15` | L4 | C-roles の同じ段階に書き手をもう 1 つ足す | `templates/examples/scenario-b` | L4 +1 | 決める |
| `pa-17` | L8 | ヘッダーに写すホップの strip_inbound を false にする | `research/pilot/scenario-b` | L8 +1 | 決める |
| `ap-1-6` | L3 | C-email の usage を identifier にする | `templates/examples/scenario-b` | L3 +1・SCHEMA +1 | 決める |
| `ap-2-1` | R8・L69 | C-roles の max_items を 500 にする | `templates/examples/scenario-b` | R8 +1・L69 +1 | 決める |
| `ap-2-2` | L5 | C-department の volatility を 10 秒にし、対策（on_revoke・recompute_trigger）を消す | `templates/examples/scenario-b` | L5 +3 | 決める |
| `ap-2-4` | L1b | 登録名でない C-task-id の namespace を null にする | `templates/examples/scenario-b` | L1b +1 | 決める |
| `q-payload-readable` | L65・L6 | C-roles の confidential_from に gateway を足す（KC_AT は gateway に見える） | `templates/examples/scenario-b` | L65 +2・SCHEMA +1 | 決める |
| `q-confidential-reaches-reader` | L65・L66 | C-roles の confidential_from に gateway を足す（KC_AT は gateway に見える） | `templates/examples/scenario-b` | L65 +2・SCHEMA +1 | 決める |
| `q-single-issuer` | L4 | C-roles の同じ段階に書き手をもう 1 つ足す | `templates/examples/scenario-b` | L4 +1 | 決める |
| `q-hook-failure` | R3b・L7 | 必須の C-roles の on_missing を「無視」にする | `templates/examples/scenario-b` | L7 +2 | 決める |
| `q-size-limit` | R8 | C-roles の max_bytes を 200000 にする | `templates/examples/scenario-b` | R8 +2 | 決める |
| `q-agent-delegation-claims` | L12 | C-act の answers に q-sub を足す | `templates/examples/scenario-b` | L12 +1 | 決める |
| `cf-01` | L4・L5 | C-roles の同じ段階に書き手をもう 1 つ足す | `templates/examples/scenario-b` | L4 +1 | 決める |
| `cf-02` | L7 | 必須の C-roles の on_missing を「無視」にする | `templates/examples/scenario-b` | L7 +2 | 決める |
| `cf-05` | L16 | H4 の scope に、上流に無い admin.write を足す | `templates/examples/scenario-b` | L16 +1 | 決める |
| `cf-06` | L43 | TXN の transport を authorization_bearer にする | `templates/examples/scenario-b` | L43 +1 | 決める |
| `cf-08` | L8 | ヘッダーに写すホップの strip_inbound を false にする | `research/pilot/scenario-b` | L8 +1 | 決める |
| `q-hop-narrowing` | L16 | H4 の scope に、上流に無い admin.write を足す | `templates/examples/scenario-b` | L16 +1 | 決める |
| `q-hop-lifetime` | L16 | H4 の max_lifetime を、上流より長い 3600 秒にする | `templates/examples/scenario-b` | L16 +1 | 決める |
| `ap-2-5` | L8・L67 | ヘッダーに写すホップの strip_inbound を false にする | `research/pilot/scenario-b` | L8 +1 | 決める |
| `q-txn-scope-fixed` | L11 | C-tctx の enforced_at を消す | `templates/examples/scenario-b` | L11 +2 | 決める |
| `q-claim-earliest-hop` | L16 | H4 の custom_claims に、上流に無い C-task-id を足す | `templates/examples/scenario-b` | L16 +1 | 決める |
| `ap-2-9` | L17・L9・R1 | INT_AT の revocation を消す | `templates/examples/scenario-b` | R1 +1 | 決める |
| `q-internal-delegation-token` | L9・L17・R1 | INT_AT の revocation を消す | `templates/examples/scenario-b` | R1 +1 | 決める |
| `ap-1-1` | L17 | KC_AT の alg_allowlist に none を足す | `templates/examples/scenario-b` | L17 +1 | 決める |
| `ap-1-3` | L27 | KC_AT の required_claims から aud を外す | `templates/examples/scenario-b` | L27 +2 | 決める |
| `ap-1-4` | L9 | AT の tenant_binding を消す | `templates/examples/scenario-a` | L9 +1 | 決める |
| `ap-1-5` | L25 | KC_AT の key_source を消す | `templates/examples/scenario-b` | L25 +1 | 決める |
| `ap-1-8` | L27 | KC_AT の max_clock_skew を 900 秒にする | `templates/examples/scenario-b` | L27 +1 | 決める |
| `q-consumer-expression` | L7・L37・L11 | C-roles の enforced_at を消す | `templates/examples/scenario-b` | L11 +2 | 決める |
| `q-nested-jwt-both-layers` | L66 | KC_AT を JWE にし、ネストの宣言（sign_then_encrypt）を書かない | `templates/examples/scenario-b` | L66 +1・SCHEMA +2 | 決める |
| `q-writer-distinguished` | L31 | C-roles の provenance を「本人が編集できる値」にする | `templates/examples/scenario-b` | L31 +1 | 決める |
| `cd-04` | L31 | C-roles の provenance を「本人が編集できる値」にする | `templates/examples/scenario-b` | L31 +1 | 決める |
| `q-session-rt-bounds` | L23・L15 | RT の idle_timeout を消す | `templates/examples/scenario-b` | L23 +1 | 決める |
| `q-rt-policy-by-client` | L15・L62 | クライアントを public にし、RT のローテーションと再利用の検知を外す | `templates/examples/scenario-b` | L15 +1 | 決める |
| `q-deprecated-deadline` | L18 | 受け手のいる C-roles の status を deprecated にする | `templates/examples/scenario-b` | L18 +1 | 決める |
| `q-key-rotation` | L17 | KC_AT の unknown_kid を消す | `templates/examples/scenario-b` | L17 +1 | 決める |

## この確かめで区分を直した問い

独立点検（PR #71）と、この確かめで、「既存の規則が決める」から外した問いです。

| 問い | 前 | 後 | 理由 |
| --- | --- | --- | --- |
| `q-hook-adds-raw-pii` | A（L70） | A・規則なし（案 N14）。書き手の自己点検 | L70 は名前からの推測との食い違いだけを見る。フックが書く行の pii_category を書き換えても指摘が増えない |
| `pa-trace` | A（L72） | B | L72 は回答の有無と「対象：」だけ。台帳の rationale と同じことを言うかは見ない |
| `pa-20` | A（L70・L6） | B | 25 問の回答の文と台帳の一致は、規則が見ない（`pa-06` と同じ扱いにそろえた） |
| `q-unwrapped-value-authz` | A（L67） | A・一部（案 N15）。書き手の自己点検 | L67 はヘッダーへの写しだけを見る |
| `dc-09`・`pa-12` | A（L3） | A（L3）＋残りは `q-value-vocabulary`（どの設計でも出す） | L3 は名前と識別子の性質を見て、値が名前かは見ない |
| `q-hop-narrowing` | A（L16） | A（L16）＋残りは `q-no-passthrough` | 交換を担うサービスが規則を強制する設定は、L16 が見ない |
| `q-auth-context-semantics` | C | A・規則なし（案 N16）。書き手の自己点検 | 行の usage・enforced_at の値でほぼ決まる |
| `q-relies-on-at-expiry` | B | C（`q-revocation-delivery` にまとめた） | 自分の前提を自分で疑う問いで、書き手の自己点検に向かない |
