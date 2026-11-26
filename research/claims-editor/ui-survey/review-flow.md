# レビューの流れ: 既存ツールの調査と、本ツールへの当てはめ案

調査日: 2026-11-25。各ツールの公式ドキュメントを読んで確認した内容です。
一次情報で確かめられなかった点は **未確認** と書いています。
画面そのものは操作しておらず、ドキュメントの本文と画像の説明文に基づきます。

出典の略号(本文では [G1] のように引きます)は末尾の「出典一覧」にまとめています。

---

## 1. 先に結論

どのツールも、レビューする人の流れは同じ 4 段階でできています。

1. **変更の一覧を開く**(GitHub の「Files changed」、GitLab の「Changes」、Gerrit のファイル一覧)
2. **1 単位ずつ見て、見終えたものに印を付ける**(「Viewed」)。印は自分だけのメモで、承認ではない
3. **コメントを下書きとしてためる**(「Pending」)。この時点では他の人に見えない
4. **最後に 1 回だけ提出する**。そのとき総評と判定(Approve / Request changes / Comment)を選ぶ

本ツールが分かりにくい原因として考えられるのは、この 2(見た印)と 4(承認)を行ごとの「承認」に
まとめてしまっている点と、4 の「提出」に当たる 1 個のボタンがない点です。
既存ツールでは「見た」と「承認した」は別物で、承認は行ごとではなくレビュー全体に 1 つです。

---

## 2. ツールごとの整理

### 2.1 GitHub のプルリクエストレビュー

| 観点 | 内容 | 出典 |
|---|---|---|
| 入口 | プルリクエストの **Files changed** タブ。行にカーソルを置いて青いコメントアイコンを押し、**Start a review** を押すとレビューが始まる。すでに始めていれば **Add review comment** | [G1] |
| レビューの単位 | ファイル(Viewed の印)、行または行の範囲(コメント)、会話(Resolve conversation) | [G1][G5] |
| 進み具合の表示 | 「The progress bar in the pull request header shows how many files you've viewed.」ヘッダーの進捗バーに、見たファイル数が出る | [G1] |
| 見た印の取り消し | 「If the file changes after you view the file, it will be unmarked as viewed.」発表時の記事では、印が外れ **Changed since last view** のバッジが付くと説明 | [G1][G7] |
| コメントの下書き | 「Before you submit your review, your line comments are *pending* and only visible to you.」 | [G1] |
| 判定の提出 | **Review changes** を押し、総評を書き、種類を選んで **Submit review**。やめるときは **Discard review** | [G1] |
| 判定の 3 種類 | **Comment**(承認も変更依頼もしない一般的な意見)、**Approve**(マージしてよい)、**Request changes**(マージ前に直す必要がある) | [G1][G2] |
| 修正の提案 | コメント内の提案ブロック。作者は **Commit suggestion** か **Add suggestion to batch** で取り込む | [G4][G5] |
| 必須レビュー | 保護ブランチで、必要な承認数を決められる。CODEOWNERS の持ち主に自動でレビュー依頼が行き、持ち主の誰か 1 人の承認で条件を満たす | [G3][G6] |
| 変更後の承認 | 設定で「dismiss stale pull request approvals when commits are pushed that affect the diff」。差分に影響する push があると古い承認を取り下げる | [G3] |
| 再レビュー | 作者が Conversation タブのサイドバーで同期アイコンを押し、レビューを再依頼する。レビューした人は Viewed の印が外れたファイルだけ見直せばよい | [G4][G1] |
| 前回レビュー以降の差分 | 過去のレビューの **View reviewed changes** で、そのレビュー時点の版を見られる。新しい Files changed 画面(2025-12 公開プレビュー)のコミット選択には「show commits since last review」があるが、画像の説明では無効(disabled)。その後有効になったかは **未確認** | [G8][G9] |

日本語の表記について。docs.github.com の日本語版では次のように書かれています [G1ja][G4ja][G5ja]。

| 英語 | 日本語版ドキュメントの表記 |
|---|---|
| Files changed | Files changed(英語のまま) |
| Viewed | 表示済み(説明文では「閲覧済み」とも) |
| Start a review | レビューの開始(別ページでは英語のまま) |
| Review changes | 変更の確認 |
| Submit review | レビューをサブミット |
| Approve / Request changes / Comment | 承認 / 変更の要求 / コメント |
| Pending | 保留中 |
| Resolve conversation | 会話の解決 |
| Commit suggestion | 提案のコミット |
| Re-request review | レビューを再リクエストする |

注意: これはドキュメントの翻訳であり、ページ内でも表記が揺れています。
GitHub の画面自体に日本語表示があるかどうかは **未確認** です(画面は英語のみという理解ですが、一次情報で確かめていません)。

### 2.2 GitLab のマージリクエストレビュー

| 観点 | 内容 | 出典 |
|---|---|---|
| 入口 | **Changes** タブでコメントを書き、**Start a review** を押す。レビューする人の状態が「Awaiting review」から「Reviewer started review」に変わる | [L1] |
| レビューの単位 | ファイル(Viewed)、行、スレッド(Resolve thread) | [L3][L5] |
| 進み具合の表示 | レビューする人ごとの状態アイコン: 未着手 / レビュー開始 / 進行中 / 承認済み / 変更を依頼して止めている | [L1] |
| 見た印の取り消し | 見た印を付けたファイルは、「The contents of the file change.」か、自分で印を外すまで再表示されない | [L3] |
| 1 つずつ見る | **Show one file at a time**。ファイルの末尾の **Prev** / **Next** で移動 | [L3] |
| コメントの下書き | **Add to review**(提出まで非公開、**Pending** と表示)と **Add comment now**(すぐ公開)を選べる | [L1] |
| 判定の提出 | 右上の **Your review** を開き、総評(任意)を書き、**Approve** / **Comment** / **Request changes** を選ぶ。やめるときは **Discard review** | [L1] |
| 承認ルール | 承認ルールは、マージ前に承認が必要な人数と人の種類を決める。作者自身の承認を禁じる設定もある | [L2] |
| 変更後の承認 | **Remove all approvals when commits are added to the source branch**、または **Remove approvals by Code Owners if their files changed**(持ち主のファイルが変わったときだけ、その人の承認を外す) | [L2] |
| スレッドの解決 | すべてのスレッドが解決するまでマージを止める設定がある(設定の正確なラベルは **未確認**) | [L5] |
| 再レビュー | レビューする人の名前の横の **Re-request a review** アイコン。変更を依頼した人が再度見て承認するまで止まる | [L1] |
| 前回以降の差分 | push ごとに差分の版ができ、**Compare** で版どうしを比べられる | [L4] |

日本語の表記(docs.gitlab.com/ja-jp)[L1ja][L3ja]:

| 英語 | 日本語版の表記 |
|---|---|
| Changes | 変更 |
| Viewed | 閲覧済み |
| Show one file at a time | 一度に1つのファイルを表示 |
| Prev / Next | 前へ / 次へ |
| Start a review | レビューを開始 |
| Add to review / Add comment now | レビューに追加する / 今すぐコメントを追加 |
| Pending | 保留中 |
| Your review | あなたのレビュー |
| Approve / Request changes / Comment | 承認 / 変更をリクエスト / コメント |
| Discard review | レビューを破棄 |
| Awaiting review | レビュー待ち |
| Re-request a review | レビューを再リクエスト |
| Reviewers | レビュアー |

注意: 英語との対応は日本語ページの文脈から読み取ったものです。実際の画面の文言と一字一句同じかは **未確認** です。

### 2.3 Gerrit

| 観点 | 内容 | 出典 |
|---|---|---|
| 入口 | 変更画面のファイル一覧からファイルを開く。行コメントは **Save** で下書きになる | [R1] |
| レビューの単位 | 変更(change)とその版(patch set)。ファイルごとに見た印、コメントごとに解決/未解決 | [R1] |
| 見た印 | 「The checkbox in front of the file name allows the patch to be marked as reviewed.」**Mark Reviewed** の設定で、開いたら自動で印を付けることもできる。版をまたいだときの印の扱いは文書に書かれておらず **未確認** | [R1] |
| 判定の提出 | **Reply…** を押すと、総評の欄とラベルごとの投票ボタンが出る。**SEND** で下書きコメントと投票をまとめて公開する。投票できるのは現在の版だけ | [R1] |
| 判定の種類 | ラベルと点数。Code-Review は「-2 This shall not be submitted」「-1 I would prefer this is not submitted as is」「0 No score」「+1 Looks good to me, but someone else must approve」「+2 Looks good to me, approved」 | [R3] |
| 変更後の投票 | 新しい版に引き継ぐかはラベルの copyCondition で決まる。引き継がれない投票は「outdated」と呼ぶ。コードの差分が同じ(コミットメッセージだけ変更)なら引き継ぐ、といった条件を書ける | [R3] |
| 誰の番か | **Attention Set**: 「users that are currently expected to act on the change」。返信すると自分は外れ、作者が入る。ダッシュボードの「Your turn」に出る | [R2] |
| コメントの解決 | 未解決(直すべき)と解決済み(参考)。直したら **Done**、直さず了解なら **Ack** | [R1] |
| 前回以降の差分 | 版 A と版 B を選んで比べる。古い版を見た人は「may see what has changed since that version by comparing the old patch against the current patch」 | [R1] |

Gerrit の公式な日本語画面・日本語ドキュメントは見つけておらず **未確認** です。

### 2.4 Reviewable

| 観点 | 内容 | 出典 |
|---|---|---|
| 見た印 | ファイルごと・版ごとの印。ボタンは見る必要があると赤、印を付けると緑。「Marking a file as reviewed doesn't necessarily mean you think it's ready to merge.」(見た印は承認ではない) | [V1] |
| 印の公開 | 印は下書きで、公開するまで自分にしか見えない | [V1] |
| 進み具合の表示 | カウンター 3 つ: 残りファイル数、返信待ちか未解決の議論の数、下書きの数。「Red counters indicate that you must address the given number of items to advance the review.」 | [V2] |
| 次へ | 「When there are items needing your attention, a **Next** button takes you to the next one.」 | [V2] |
| 判定の提出 | **Publish**。判定(Comment / Approve / Request changes)は、付けた印から既定値を自動で選んでくれる | [V2] |
| 前回以降の差分 | ファイルの一覧表(file matrix)で、ファイルごとに「最後に見た版から最新の版まで」に差分の範囲を合わせられる | [V1] |

### 2.5 Phabricator の Differential

- 行コメントは最初「Unsubmitted」の下書きで、ページ下部のフォームを送信すると、総評・操作と一緒に公開される [P2]。
- 版が更新されると、行コメントを新しい差分へ引き継いで薄く表示する(元の位置へ戻るボタン付き)[P2]。
- ホーム画面は「Action Required」(自分の番)と「Waiting on Others」(相手の番)の 2 つの一覧 [P1]。
- 状態名(Needs Review など)や「Accept Revision」などの操作名、版どうしの比較は、読んだ公式ページに書かれておらず **未確認** です。

### 2.6 Google ドキュメント / ドライブの承認

- 承認の依頼が進行中だと、ファイルの上部にバナーが出て、承認か却下を選び、任意でメモを書ける [D1]。
- ファイルをロックでき、ロック中は「Edits, comments and suggestions can't be added to locked documents.」[D1]
- 「Require all approvers to review the same content」をオンにすると「Edits reset all approvals.」[D1]。内容が変われば全員の承認がやり直しになる、という考え方です。
- 使えるのは Enterprise と Education Plus の一部のアカウントだけです [D1]。
- Google 社内の設計書レビューの手順を定めた一次情報は見つけておらず **未確認** です。コードレビューについては、「まず全体を見る → 主要部分を見る → 残りを順に見る」という 3 段階の読み方が公開されています [D2]。

---

## 3. 共通する型

| 型 | GitHub | GitLab | Gerrit | Reviewable |
|---|---|---|---|---|
| 見た印は個人のメモで、承認とは別 | Viewed | Viewed | reviewed のチェック | mark as reviewed |
| 中身が変わると見た印が外れる | あり [G1] | あり [L3] | 未確認 | 版ごとに管理 [V1] |
| コメントは下書きでためる | pending | Pending | draft | draft |
| 提出は 1 回、総評と判定を付ける | Submit review | Your review | Reply… → SEND | Publish |
| 判定は 3 種類 | Approve / Request changes / Comment | 同じ | ラベルの点数 | GitHub と同じ |
| 変更があると承認を取り消す(設定) | dismiss stale approvals [G3] | Remove all approvals [L2] | copyCondition [R3] | — |
| 再レビューは「前回から変わった所」だけ | Viewed が外れた所 | Viewed が外れた所、版の比較 | 版 A と B の比較 | 最後に見た版から最新まで |

承認を内容に結び付ける粒度は、GitLab の「Code Owner のファイルが変わったときだけその承認を外す」[L2] が、
本ツールの「行の内容ハッシュが変わったら、その行の承認を無効にする」に最も近い先例です。

---

## 4. 静的でログインのないツールには持ち込めないもの

| 既存ツールの機能 | 持ち込めない理由 | 代わりの手段 |
|---|---|---|
| レビューの依頼・再依頼、通知、Attention Set | サーバーも利用者の識別もない | PR 側のレビュー依頼に任せる。本ツールは「あなたの残り」を数で示すだけ |
| 必須レビュー、承認数の強制、マージの阻止 | 静的ページは何も強制できない | PR にコミットした review.yaml を CI で検査する(ハッシュの一致、判定、未解決の指摘) |
| 本人確認つきの承認 | ログインがない | レビューする人が名前を入力する。誰がコミットしたかは git の履歴で担保する |
| 他の人のコメントがすぐ見える、スレッドで返信 | 共有する保存先がない | review.yaml を読み込んで他の人の指摘を表示する。返信は review.yaml への追記として扱う |
| サーバー側の下書き保存 | 同上 | ブラウザーの保存領域に下書きを置き、書き出すまで「未提出」と明示する |
| Commit suggestion(提案をその場で取り込む) | リポジトリへ書き込めない | 提案後の値を指摘に持たせ、作者が編集画面で「この値を使う」を押して YAML に反映する |
| サーバーが持つ版の履歴 | 履歴を持てない | review.yaml に記録した行ごとのハッシュと、現在の YAML から計算したハッシュを比べる |

---

## 5. 本ツールへの当てはめ案

前提: 静的ページ、ログインなし、成果物は review.yaml(PR にコミット)とレポート。

### (1) レビューを始める

- 入口を 1 つにします。画面上部に **「レビューを開始」** ボタンを 1 個置きます(GitHub / GitLab の Start a review)。
- 押すと、名前の入力と、あれば既存の review.yaml の読み込みを求め、編集画面から **レビュー用の表示**(読み取り専用の行一覧)に切り替えます。
- 開始後は画面上部に **レビューバー** を常に出します。中身は「確認済み 12 / 70 行」「指摘 3 件」「未提出」「レビューを提出」の 4 つです(GitHub の進捗バー、Reviewable のカウンター)。
- 最初に全体の概要(トークン一覧、ホップ表)を見せ、次にレジストリの行へ進む順にします(Google の「全体 → 主要部分 → 残り」[D2])。

### (2) 行ごとに見て「確認済み」を付ける

- 各行の見出しに **「確認済み」** チェックボックスを置きます(GitHub / GitLab の Viewed)。
- 確認済みは **個人のメモで、承認ではない** と明記します(Reviewable の考え方 [V1])。行ごとの「承認 / 変更を依頼」ボタンは置きません。
- 付けると行をたたみ、**「次の未確認へ」** で次へ進みます(GitLab の Prev / Next、Reviewable の Next)。
- 行の内容ハッシュが変わったら印を外し、**「前回の確認から変更あり」** のバッジを付けます(GitHub の Changed since last view [G7])。
- 絞り込みは「未確認だけ」「変更ありだけ」「指摘ありだけ」の 3 つにします。
- チェックリストの質問は、別の画面にせず、行の一覧の前に置く「全体の確認」の項目として同じ確認済みの仕組みに載せます。

### (3) 行に付くコメント・指摘

- 行(または行の中の列)に **「コメントを追加」** を置きます。追加したものは **「未提出」** として自分にだけ見え、提出するまで編集・削除できます(pending / 保留中)。
- 指摘には **未解決 / 解決済み** の状態を持たせます(GitHub の Resolve conversation、Gerrit の Done / Ack)。解決済みにできるのは、再レビューのときのレビューした本人とします。
- 列に対する指摘には、任意で **「修正の提案」**(提案後の値)を付けられるようにします(GitHub の suggested changes)。作者は編集画面で「提案を適用」を押します。
- 指摘は、記録した時点の行ハッシュを持たせます。行が変わったあとは「古い内容への指摘」と薄く表示します(Phabricator の引き継ぎ表示 [P2]、Gerrit の outdated [R3])。

### (4) 判定を付けてレビューを提出する

- レビューバーの **「レビューを提出」** を押すと、1 つのダイアログが開きます(GitHub の Review changes → Submit review)。
- 中身は、総評の欄、判定の選択 3 つ、未確認の行数と未提出の指摘数の表示です。
  - **承認**: この内容でよい
  - **変更を依頼**: マージ前に直してほしい点がある
  - **コメントのみ**: 判定はしない
- 判定の既定値はツールが選びます。未解決の指摘があれば「変更を依頼」、すべて確認済みで未解決の指摘がなければ「承認」にします(Reviewable の既定値の選び方 [V2])。
- 未確認の行が残っていると、「承認」は選べないか、警告を出します。
- 承認は **レビュー全体に 1 つ** です。review.yaml には、判定と一緒に「そのとき確認した各行のハッシュ」を記録します。これで「内容が変わったら承認は古い」と機械的に判定できます(GitHub の dismiss stale approvals [G3]、GitLab の Code Owner 承認の取り消し [L2]、Google ドライブの Edits reset all approvals [D1])。
- 提出すると review.yaml とレポートを書き出し、**「このファイルを PR にコミットしてください」** と次の手順を示します。提出の意味が「ファイルを書き出して PR に載せること」だと、ここで言葉にします。
- やめるときは **「レビューを破棄」** です(Discard review)。

### (5) 再レビューでは変わった行だけを見せる

- review.yaml を読み込んだ時点で、行ごとに記録済みのハッシュと現在のハッシュを比べ、行を 4 つに分けます。**変更なし(確認済みのまま)** / **変更あり** / **追加** / **削除**。
- 既定の表示を **「前回のレビュー以降の変更」** にし、変更あり・追加・削除の行だけを出します(Reviewable の「最後に見た版から最新まで」[V1]、Gerrit の版の比較 [R1])。切り替えで「すべての行」も見られます。
- 変更ありの行は、変わった列だけを新旧並べて見せます。前回の値が必要なので、review.yaml には確認した時点の行の値(少なくとも指摘のある列と変わりやすい列。可能なら行全体)を残すか、前の版の YAML を読み込ませて比べます。
- 前回の判定は **「古い承認(内容が変更されました)」** と表示し、有効な承認としては数えません。前回の未解決の指摘は一覧の先頭に出し、解決済みにするか残すかを選ばせます。
- 見終えたら (4) と同じ手順でもう一度提出します。review.yaml にはレビューの回(1 回目、2 回目)を追記します。

### (6) 日本語の画面で使う言葉

GitHub と GitLab の日本語版ドキュメントの表記に寄せ、揺れのある所は平易なほうを選びます。

| 場面 | 使う言葉 | 元の言葉 | 避ける言葉 |
|---|---|---|---|
| 始める | レビューを開始 | Start a review | 査読モード、検証開始 |
| 見た印 | 確認済み | Viewed(表示済み / 閲覧済み) | 承認(行ごと)、チェック済み |
| 変わった行 | 前回の確認から変更あり | Changed since last view | 無効化、失効 |
| 下書き | 未提出 | Pending(保留中) | 保留中(判断を保留したように読める) |
| コメント | コメント / 指摘 | comment | 所見、ファインディング |
| 提案 | 修正の提案 / 提案を適用 | Suggestion / Commit suggestion | サジェスト |
| 指摘の状態 | 未解決 / 解決済み | Resolve conversation(会話の解決) | クローズ |
| 提出 | レビューを提出 | Submit review(レビューをサブミット) | サブミット、エクスポート(提出の意味では) |
| 判定 | 承認 / 変更を依頼 / コメントのみ | Approve / Request changes / Comment | 却下、差し戻し |
| やめる | レビューを破棄 | Discard review | リセット |
| 再レビュー | 前回のレビュー以降の変更 | since last review | 差分モード |
| 古い承認 | 古い承認(内容が変更されました) | stale approval / outdated | ハッシュ不一致 |
| 人 | レビュアー / 作成者 | Reviewer / Author | 査読者 |

「確認済み」は依頼文の言葉をそのまま採りました。GitHub の「表示済み」、GitLab の「閲覧済み」は「開いただけ」の意味に近く、
内容を読んで確かめたことを表すには「確認済み」のほうが合います。ただし承認とは別であることを、画面上の説明で必ず添えてください。

---

## 6. 確かめられなかった点

- GitHub の画面に日本語表示があるか。日本語の表記はドキュメントの翻訳から採っており、ページ間で揺れがあります。
- GitHub の「since last review」のコミット選択が、2025-12 のプレビュー以降に有効になったか [G9]。
- GitLab の日本語表記が実際の画面と一致するか。「すべてのスレッドの解決を必須にする」設定の正確なラベル。
- Gerrit で、新しい版が上がったときにファイルの reviewed の印がどう扱われるか。
- Phabricator の状態名、操作名、版どうしの比較。
- Google ドライブの承認ページ [D1] の現行 URL と記載内容の最新性(1 つ目に試した URL は 404 でした)。Google 社内の設計書レビューの公式な手順。
- 本ツールの現在の画面と review.yaml の構造は、この調査では見ていません。当てはめ案は依頼文の説明に基づきます。

---

## 出典一覧

GitHub
- [G1] https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/reviewing-proposed-changes-in-a-pull-request
- [G1ja] https://docs.github.com/ja/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/reviewing-proposed-changes-in-a-pull-request
- [G2] https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/about-pull-request-reviews
- [G3] https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- [G4] https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/incorporating-feedback-in-your-pull-request
- [G4ja] https://docs.github.com/ja/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/incorporating-feedback-in-your-pull-request
- [G5] https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/commenting-on-a-pull-request
- [G5ja] https://docs.github.com/ja/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/commenting-on-a-pull-request
- [G6] https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
- [G7] https://github.blog/news-insights/product-news/mark-files-as-viewed/
- [G8] https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/viewing-a-pull-request-review
- [G9] https://github.blog/changelog/2025-12-11-review-commit-by-commit-improved-filtering-and-more-in-the-pull-request-files-changed-public-preview/

GitLab
- [L1] https://docs.gitlab.com/user/project/merge_requests/reviews/
- [L1ja] https://docs.gitlab.com/ja-jp/user/project/merge_requests/reviews/
- [L2] https://docs.gitlab.com/user/project/merge_requests/approvals/settings/
- [L3] https://docs.gitlab.com/user/project/merge_requests/changes/
- [L3ja] https://docs.gitlab.com/ja-jp/user/project/merge_requests/changes/
- [L4] https://docs.gitlab.com/user/project/merge_requests/versions/
- [L5] https://docs.gitlab.com/user/discussions/

Gerrit
- [R1] https://gerrit-review.googlesource.com/Documentation/user-review-ui.html
- [R2] https://gerrit-review.googlesource.com/Documentation/user-attention-set.html
- [R3] https://gerrit-review.googlesource.com/Documentation/config-labels.html

Reviewable
- [V1] https://docs.reviewable.io/files.html
- [V2] https://docs.reviewable.io/reviews.html

Phabricator
- [P1] https://secure.phabricator.com/book/phabricator/article/differential/
- [P2] https://secure.phabricator.com/book/phabricator/article/differential_inlines/

Google
- [D1] https://support.google.com/drive/answer/9387535?hl=en
- [D2] https://google.github.io/eng-practices/review/reviewer/navigate.html
