<!-- template_version: 0.4.0 -->
# レビュー教材（#5）

JWT のクレームの設計書（`templates/00_core.md` と台帳）をレビューするための教材と様式です。レビューを「採否の理由の妥当性の評価」を中心に進めながら、経験の浅いレビュアーでも、ユースケースから見て仕組みの取り違え（例：「誰が代理しているか」を `act` でなく Txn-Token で答えた設計）に気づけるようにします。

## 約束の範囲

- 問いの一覧の内側で、判断の抜け・理由の不備・仕組みの取り違えを見つけるための教材です。**想定漏れが一切ないことは約束しません**（原理的に証明できないため。#11 の「約束の範囲」）
- 一覧の外は、カタログの外を問う質問（`q-outside-catalog`）・テンプレート外の気づき・レビュー後の欠陥の記録で拾い、一覧に戻します（[procedure.md](procedure.md) の 7.）
- シナリオ A・B の設計レビューでは、設計の欠陥のほとんどを lint でなくレビューが見つけました（`research/template-design/gate1.md` の 5.、`research/template-design/gate2-evidence.md`）。この教材は、その指摘のどれもが、少なくとも 1 つの問いから辿れるように作りました（[perspectives.md](perspectives.md) の 9.）

## 一式の中身

| ファイル | 中身 |
| --- | --- |
| [procedure.md](procedure.md) | 読み方の手順（段 0〜8）。1 名で行う場合、LLM の一次スクリーニング |
| [perspectives.md](perspectives.md) | 観点書。スライド 148 の 6 段（定義・発行・伝搬・検証・認可・運用）ごとの問い。各問いに、見る欄・No のとき・対比表・lint・実行テスト・事例・根拠 |
| [decision_tree.md](decision_tree.md) | ユースケースから仕組みを選ぶ判断の木 |
| [contrasts/](contrasts/) | 取り違えやすい概念の対比表（8 本）。各表に、解く問い・仕様上の単位・対比・扱わないこと・典型的な誤用・根拠 |
| [escalation.md](escalation.md) | 専門家に回す基準（9 つ） |
| [rationale_rubric.md](rationale_rubric.md) | 理由の採点基準（RR1〜RR7。各観点に合格と不合格の例。採点の範囲と迷いやすい点の決まり） |
| [report_template.md](report_template.md) | レビューレポートの様式（出どころ 5 種・種別 5 種） |
| [review.schema.json](review.schema.json) | レビューの記録 `review.yaml` の JSON Schema（#50、#67。形の名前は `claims-review/2`。設計書のエディターのレビューが書き出す。レビュアーの名前は自己申告）。レビュアーごとに、確認済みの印（`viewed`。行の内容のハッシュに結びつく。承認ではない）、コメント（`comments`。未提出・未解決・解決済み）、提出ごとの判定（`submissions`。承認・変更を依頼・コメントのみ）を持つ |
| [review.v1.schema.json](review.v1.schema.json) | 前の形（`claims-review/1`。行ごとの判定と指摘）の JSON Schema。前の形のファイルも読める（`tools/review_record.py` とエディターが、読むときに新しい形へ移す）。書き直すなら `python tools/review_record.py migrate` |
| [escaped_defects.md](escaped_defects.md) | レビュー後に見つかった欠陥の記録 |
| [metrics.md](metrics.md) | レビューの指標（目標にしない観察の記録） |

対比表：

| ファイル | 対比するもの |
| --- | --- |
| [contrasts/act-txn-workload.md](contrasts/act-txn-workload.md) | `act` と Txn-Token とワークロード認証（mTLS・SPIFFE） |
| [contrasts/id-vs-access-token.md](contrasts/id-vs-access-token.md) | ID トークンとアクセストークン（`typ`・`aud`） |
| [contrasts/signed-vs-enforced.md](contrasts/signed-vs-enforced.md) | 署名で守られていることと、受け手が照合していること（と値の書き手） |
| [contrasts/four-lifetimes.md](contrasts/four-lifetimes.md) | トークンの寿命・クレームの値の鮮度・セッションと RT の寿命・クレームの定義の寿命 |
| [contrasts/jws-vs-jwe.md](contrasts/jws-vs-jwe.md) | JWS と JWE（改ざん防止と流出防止。JWE の 4 つの影響） |
| [contrasts/scope-vs-role.md](contrasts/scope-vs-role.md) | `scope` と `role` と `authorization_details`（RAR） |
| [contrasts/carry-vs-query.md](contrasts/carry-vs-query.md) | クレームに載せることと、問い合わせること |
| [contrasts/name-vs-identifier.md](contrasts/name-vs-identifier.md) | 名前（表示・語彙）と識別子（照合のキー）、名前空間 |

記入例：[../examples/scenario-b/review-report.md](../examples/scenario-b/review-report.md)（シナリオ B のレビューと、過去の指摘との較正）。エディターのレビューで記録した例：[../examples/scenario-b/review.yaml](../examples/scenario-b/review.yaml) と、そこから生成した [../examples/scenario-b/review-report-2026-11-23.md](../examples/scenario-b/review-report-2026-11-23.md)（今の版を LLM のセッション 1 つが全 168 問でレビューしたもの。人による点検は未実施）。

## エディターでレビューする（#50）

設計書のエディター（`docs/claims/`、https://takenori-kusaka.github.io/jwt-claims-guide/claims/ ）で、上のバーを「レビュー」に切り替えると、この教材を使ってレビューを記録できます（最初の画面の「設計書をレビューする」からも始められる）。サーバーは使わず、記録は `review.yaml` として書き出し、PR で台帳と一緒にコミットします（Git の履歴が監査の記録になる）。

- 観点のチェックリスト：観点書の 168 問（`python tools/build_claims_viewer.py` が観点書から作る。CI の `--check` が食い違いを見る）を、6 段と役割（7. の索引）で絞り込み、問いごとに Yes／No／該当なし とメモを記録する。「見る欄」から、その欄（台帳の列・設計書の節・25 問の回答）に移る
- 行ごとの判定：承認／修正を求める／保留 を、レビュアー・日時・コメントとともに記録する。判定は行の内容のハッシュ（`tools/row_hash.py`）に結びつき、行を変えると「再確認が要る」になる
- 指摘は report_template.md の欄で記録する。分析の画面（網羅・lint との重ね合わせ・前の版との差分・25 問の回答・却下の理由の抜き取り）と、report_template.md の形のレポートの生成がある
- **レビュアーの名前は自己申告です。** 本当の承認は GitHub の PR のレビューで行います
- 独立レビュー：提出するまで、ほかのレビュアーの記録を隠す設定がある（[procedure.md](procedure.md)）。画面で隠すだけで、review.yaml を開けば見える。提出の前に隠すのをやめる操作は確かめて、外れたことを review.yaml に記録する（`independence`）。守ったかは自己申告で、手順で守る
- 行の判定のハッシュは、その行の値だけを見る。参照する行・25 問の回答・design.md の本文を変えても「再確認が要る」にならない
- 記録がある設計書を変える PR の手順（承認した行・却下の行・教材を変えたとき）は [../CONTRIBUTING.md](../CONTRIBUTING.md) の「レビューの記録がある設計書を変えるとき」

```
python tools/review_record.py check <dir>/review.yaml --design <dir> [--fail-on-stale] [--annotate]   # スキーマ・問い ID・コメントの状態・提出・抜き取り・行が変わった確認済みの印と古い承認
python tools/review_record.py migrate <dir>/review.yaml -o <dir>/review.yaml   # 前の形（claims-review/1）を新しい形にする（--check <ファイル> で、移した結果と同じかを確かめる）
python tools/review_record.py sample <dir> --reseed --reason "<理由>" --file <dir>/review.yaml --reviewer "<名前>"   # 母集団が変わった抜き取りを引き直す
python tools/review_record.py report <dir>/review.yaml --design <dir> -o <dir>/review-report-<日付>.md
python tools/review_check.py --report <レポート>                                          # report_template.md の様式どおりか
```

## 問いの数（段ごと）

`python tools/review_check.py --counts` の出力と同じです（検査が食い違いを見る）。

<!-- counts:begin -->
| 段 | 問いの数 |
| --- | --- |
| 1. 定義 | 59 |
| 2. 発行 | 12 |
| 3. 伝搬 | 28 |
| 4. 検証 | 14 |
| 5. 認可 | 28 |
| 6. 運用 | 27 |
| 計 | 168 |
<!-- counts:end -->

シナリオ B の較正（`../examples/scenario-b/review-report.md` の 9.）の後に 7 問を足しました（各問いの「No なら」に「較正で追加」と書いた）。PR #45 の独立点検の後に `q-pairwise-external` を 2 問に分けました（`q-pairwise-unguessable`）。定義の段が多いのは、設計のチェックリスト（13 問）と追加前の 25 問（27 問）を置いたためです。25 問の後半（問 13〜25）は発行・伝搬・運用に関わりますが、スライド 143 と issue #5 に合わせて同じ節で扱います。

## 使い方の最短の道

1. [procedure.md](procedure.md) の段 0 で、CI と Lite／Full を確かめる
2. 設計書の 12.（自信のない点）と 6.（問い × 仕組み）を読み、[decision_tree.md](decision_tree.md) で仕組みを確かめる
3. [perspectives.md](perspectives.md) の 6 段を、段の担当の役割で読む。分からない語は対比表へ
4. [report_template.md](report_template.md) に記録し、[escalation.md](escalation.md) に当たる行を回す

## 検査

```
python tools/review_check.py           # 問い ID・見る欄・根拠・リンクの解決、対応表の印、問いの数
python tools/review_check.py --list    # 問い ID と段の一覧
python tools/trace_check.py            # 対応表（review: の成果物を持つ要件）
python tools/check_slide_refs.py templates
```

## 版と作成方法

- 版は `templates/` 一式と同じ semver です（各ファイルの 1 行目。0.4.0）。変更の記録は [../CHANGELOG.md](../CHANGELOG.md)
- 本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています

## 点検状況

> 人による点検は未実施。作成とは別の LLM のセッションでの点検と、作成者の 1 日以上空けた見直しは、まだ行っていない（材料：`research/reviews/review-materials-facts.md`）。

シナリオ B のレビュー（記入例）は、教材の作成とは別の LLM のセッションが行いました。教材の作成者は、そのレビューの前に、関門 2 の材料（`research/template-design/gate2-evidence.md`）にある B の指摘の 1 行の要約を読んでいました。照合の判定は作成者の自己採点です。較正の数は、この条件で読んでください（[../examples/scenario-b/review-report.md](../examples/scenario-b/review-report.md) の較正の節）。
