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
| [short_list.md](short_list.md) | **レビュアーが答える問い**（#56）。観点書の問いのうち、人の判断が要るものだけを、設計の性質に当たる分だけ、優先の順に並べた短い一覧と、一覧の外を辿る「開いた問い」。triage.yaml から作る |
| [triage.yaml](triage.yaml) | 観点書の全問の振り分け（A 機械／B 書き手の自己点検／C 人の判断／D 専門家）と根拠、出す条件、優先、lint の規則の案（#56）。short_list.md・観点書の「区分」の行・書き手の自己点検（`.github/PULL_REQUEST_TEMPLATE/design_doc.md`）・エディターのデータの正 |
| [perspectives.md](perspectives.md) | 観点書（全問の参照用）。スライド 148 の 6 段（定義・発行・伝搬・検証・認可・運用）ごとの問い。各問いに、見る欄・No のとき・対比表・lint・実行テスト・事例・根拠・区分 |
| [decision_tree.md](decision_tree.md) | ユースケースから仕組みを選ぶ判断の木 |
| [contrasts/](contrasts/) | 取り違えやすい概念の対比表（8 本）。各表に、解く問い・仕様上の単位・対比・扱わないこと・典型的な誤用・根拠 |
| [escalation.md](escalation.md) | 専門家に回す基準（9 つ） |
| [rationale_rubric.md](rationale_rubric.md) | 理由の採点基準（RR1〜RR7。各観点に合格と不合格の例。採点の範囲と迷いやすい点の決まり） |
| [report_template.md](report_template.md) | レビューレポートの様式（出どころ 5 種・種別 5 種） |
| [review.schema.json](review.schema.json) | レビューの記録 `review.yaml` の JSON Schema（#50。設計書のエディターのレビューが書き出す。レビュアーの名前は自己申告） |
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

- 観点のチェックリスト：既定で、開いている設計書の性質に当たる、人の判断が要る問い（short_list.md と同じ選び方）と、開いた問いだけを出す（#56）。「表示する問い」で、観点書の 168 問の全部や、区分ごとの問いに切り替えられる（`python tools/build_claims_viewer.py` が観点書と triage.yaml から作る。CI の `--check` が食い違いを見る）。6 段と役割（7. の索引）でも絞り込める。問いごとに Yes／No／該当なし とメモを記録する。「見る欄」から、その欄（台帳の列・設計書の節・25 問の回答）に移る。画面の作り直しは #67
- 行ごとの判定：承認／修正を求める／保留 を、レビュアー・日時・コメントとともに記録する。判定は行の内容のハッシュ（`tools/row_hash.py`）に結びつき、行を変えると「再確認が要る」になる
- 指摘は report_template.md の欄で記録する。分析の画面（網羅・lint との重ね合わせ・前の版との差分・25 問の回答・却下の理由の抜き取り）と、report_template.md の形のレポートの生成がある
- **レビュアーの名前は自己申告です。** 本当の承認は GitHub の PR のレビューで行います
- 独立レビュー：提出するまで、ほかのレビュアーの記録を隠す設定がある（[procedure.md](procedure.md)）。画面で隠すだけで、review.yaml を開けば見える。提出の前に隠すのをやめる操作は確かめて、外れたことを review.yaml に記録する（`independence`）。守ったかは自己申告で、手順で守る
- 行の判定のハッシュは、その行の値だけを見る。参照する行・25 問の回答・design.md の本文を変えても「再確認が要る」にならない
- 記録がある設計書を変える PR の手順（承認した行・却下の行・教材を変えたとき）は [../CONTRIBUTING.md](../CONTRIBUTING.md) の「レビューの記録がある設計書を変えるとき」

```
python tools/review_record.py check <dir>/review.yaml --design <dir> [--fail-on-stale] [--annotate]   # スキーマ・問い ID・抜き取り・古くなった承認
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

### 区分ごとの数（#56）

`python tools/review_triage.py --counts` の出力と同じです（`--check` が食い違いを見る）。区分は筆者の提案です（追跡 #56）。

<!-- triage-counts:begin -->
| 区分 | 問いの数 | 行き先 |
| --- | --- | --- |
| A 機械 | 81（既存の規則が確かめる 44、規則が一部を確かめる 18、規則がまだ無い 19） | claim_lint。規則が無い・足りない間は書き手の自己点検にも置く |
| B 書き手の自己点検 | 36 | 提出前のチェックリスト（PR のテンプレート。規則待ちの A と合わせて 51 行） |
| C 人の判断 | 47（優先 1：19、優先 2：10、優先 3：18。うち規則ができるまで人が答える機械の問い 4） | short_list.md（既定で出すのは優先 1 のうち、設計の性質に当たるもの。優先 2 は時間があれば） |
| D 専門家 | 4 | escalation.md |
| 計 | 168 | 開いた問いは、このほかに 6 個 |
<!-- triage-counts:end -->

シナリオ B の較正（`../examples/scenario-b/review-report.md` の 9.）の後に 7 問を足しました（各問いの「No なら」に「較正で追加」と書いた）。PR #45 の独立点検の後に `q-pairwise-external` を 2 問に分けました（`q-pairwise-unguessable`）。定義の段が多いのは、設計のチェックリスト（13 問）と追加前の 25 問（27 問）を置いたためです。25 問の後半（問 13〜25）は発行・伝搬・運用に関わりますが、スライド 143 と issue #5 に合わせて同じ節で扱います。

## 使い方の最短の道

1. [procedure.md](procedure.md) の段 0 で、CI・書き手の自己点検・Lite／Full を確かめる
2. 設計書の 12.（自信のない点）と 6.（問い × 仕組み）を読み、[decision_tree.md](decision_tree.md) で仕組みを確かめる
3. `python tools/review_triage.py --design <設計書のディレクトリ>` で、この設計の 1 枚（性質の表と、当たる優先 1 の問い 10〜18 問、開いた問い 3 つ）を出し、性質の表を図と要求に照らしてから、問いと開いた問いに答える（全部の問いは [short_list.md](short_list.md)）。分からない語は対比表へ。問いの見る欄と根拠は [perspectives.md](perspectives.md) の同じ ID の問いにある
4. [report_template.md](report_template.md) に記録し、[escalation.md](escalation.md) に当たる行を回す

## 検査

```
python tools/review_check.py           # 問い ID・見る欄・根拠・リンクの解決、対応表の印、問いの数
python tools/review_check.py --list    # 問い ID と段の一覧
python tools/review_triage.py --check  # 振り分け（triage.yaml）が全問にあり、引いた lint の規則が実在し、作ったファイルと一致する（review_check.py も V14 として見る）
python tools/review_triage.py --write  # triage.yaml から、短い一覧・区分の行・書き手の自己点検を作り直す
python tools/review_triage_audit.py    # 「既存の規則が答えを決める」とした問いを、記入例の答えを No に書き換えて確かめる
python tools/trace_check.py            # 対応表（review: の成果物を持つ要件）
python tools/check_slide_refs.py templates
```

## 版と作成方法

- 版は `templates/` 一式と同じ semver です（各ファイルの 1 行目。0.4.0）。変更の記録は [../CHANGELOG.md](../CHANGELOG.md)
- 本資料は生成AI（Claude）を使って作成し、筆者が確認して公開しています

## 点検状況

> 人による点検は未実施。作成とは別の LLM のセッションでの点検と、作成者の 1 日以上空けた見直しは、まだ行っていない（材料：`research/reviews/review-materials-facts.md`）。

シナリオ B のレビュー（記入例）は、教材の作成とは別の LLM のセッションが行いました。教材の作成者は、そのレビューの前に、関門 2 の材料（`research/template-design/gate2-evidence.md`）にある B の指摘の 1 行の要約を読んでいました。照合の判定は作成者の自己採点です。較正の数は、この条件で読んでください（[../examples/scenario-b/review-report.md](../examples/scenario-b/review-report.md) の較正の節）。
