# 「候補を列挙し採否と理由を記録させ、レビューは理由の妥当性だけを評価する」方式の有効性・コスト・リスク

調査日: 2026-11-22。凡例: 【実証】= 実験・観察研究に基づく / 【意見】= 実務家・著者の主張 / 【二次】= 二次資料・要旨のみ確認。
前提の検証対象: 「全候補 claim / ケースに採否と理由が付いていれば、レビューは理由の判定に縮約され、網羅漏れは起こり得ない」。

---

## Q1. 設計根拠 (Design Rationale) 研究: IBIS / QOC / DRL / ADR・MADR はレビュー品質・保守に効くか、既知の問題は何か

### Takeaway
設計根拠を記録すると保守時の変更特定や推論を助けるという実証は「ある」が、規模は小さく、捕捉コスト・記録者と受益者の不一致・事後記録化 (post-hoc) が一貫した障害として報告されている。ADR は実務で「有用」と評価される一方、採用後の継続率は低く、多くが熟議なしに "accepted" 状態で作成されている。

### Cited Findings
- 【実証/二次】Buckingham Shum & Hammond (1994) のレビュー: 議論型 DR (IBIS/QOC 系) の 2 つの基本主張 (「議論として表現することが有用」「設計者がその記法を使える」) は、設計外の半形式的議論研究からは説得的に裏付けられていない。ただし、表現の手間を設計者の利点に転化できる種類の推論では支援効果の兆候があり、後で再訪する際に価値がある — [IJHCS 40(4):603-652, 1994 (dblp)](https://dblp1.uni-trier.de/rec/journals/ijmms/ShumH94.html) / [Scribd 全文コピー](https://www.scribd.com/document/65622348/Argumentation-Based-Design-Rationale)
- 【実証/二次】QOC は理解が浅い設計空間を展開するときに最も役立ち、制約が強く定まった設計空間を評価するときにはむしろ邪魔になる — [KMi Tech Report (Buckingham Shum)](https://kmi.open.ac.uk/publications/techreport/kmi-95-13)
- 【実証/二次】設計根拠を与えられた設計者は保守課題でより速く、より多くの必要変更を特定した、という実験結果がある。また設計者の質問の約 50% が意思決定の理由に関するものだった — [Antony Tang 博士論文 (Swinburne)](https://researchbank.swinburne.edu.au/file/198ab8bf-fbaa-422b-bd24-2ecf7d23aa0c/1/Antony%20Tang%20Thesis.pdf)
- 【実証】Tang, Babar, Gorton, Han (2006) の実務家調査 (有効回答 81): 実務家は根拠の記録に価値を認め推論に使っているが、記録・利用には障壁があり、体系的な捕捉手法は実務に存在しない — [JSS 79(12):1792-1804, doi:10.1016/j.jss.2006.04.029 (figshare)](https://figshare.swinburne.edu.au/articles/report/A_survey_of_architecture_design_rationale/26269849)
- 【実証/意見】Falessi ら: DR 文書化が普及しない阻害要因として「タイミングが悪く便益が遅れて来る」「記録・維持する人と直接受益する人が別」を挙げ、価値ベースで記録対象を絞る原則を提案 — [WICSA 2008 Value-Based DDRD](https://art.torvergata.it/bitstream/2108/57813/1/2008_WICSA_FCK_Value-Based%20Design%20Decision%20Rationale%20Documentation%20Principles%20and%20empirical%20feasibility%20study.pdf)
- 【意見】DR 研究の多くは実証評価がほとんどなく、「根拠の価値が収集コストに見合うか」は未解決 — [AI EDAM 特集号 "Design rationale: researching under uncertainty"](https://cambridge.org/core/services/aop-cambridge-core/content/view/BC91F6968115F74046BD4A7DD1E89445/S0890060408000206a.pdf/special-issue-design-rationale.pdf)
- 【意見・古典】Parnas & Clements「合理的設計プロセス: なぜ、どう偽装するか」: 実際の設計は合理的手順では進まないが、文書は合理的に導かれたかのように書くべき、と主張 (= 根拠文書は本質的に事後再構成である、という認識) — [IEEE TSE 12(2), 1986, doi:10.1109/TSE.1986.6312940](https://doi.org/10.1109/TSE.1986.6312940)
- 【実証】ADR 導入のアクションリサーチ (ECSA 2024): 文書化文化・知識移転・何を記録するかの優先付けの課題には ADR が有効だったが、分散コンポーネント (共有・分散システム) の決定記録は未解決。何を中央に置き何をローカル repo に置くか慎重に設計すべき — [Ahmeti et al., ECSA 2024](https://rebekkaa.github.io/files/2024_ECSA.pdf) / [Chalmers](https://research.chalmers.se/en/publication/538920)
- 【実証】GitHub マイニング: ADR 採用は低いが年々増加 — [Buchgeher et al., IEEE Access 2023](https://doaj.org/article/f838f2a538ea48e7a3b15ce99befe612)
- 【実証/二次】OSS の ADR 5,800 件のうち約 3,674 件 (約 63%) が最初から "accepted" 等の状態で作成されており、ADR が本来捉えるべき熟議過程を迂回している — [Garcia de Santana Junior et al., ICSA 2026](https://conf.researchr.org/details/icsa-2026/icsa-2026-papers/34/Architecture-Decision-Records-Adoption-Impact-and-Developer-Engagement-in-Open-Sou)
- 【実証/二次】ADR を始めたリポジトリの約 50% は 5 件未満で止まっており、試行後に放棄される「採用ギャップ」がある — [arXiv 2604.03826](https://arxiv.org/html/2604.03826)
- 【実証/二次】ADR テンプレート間の理解性・使いやすさ・採用容易性を比較した研究は少なく、2026 年に比較実験が出始めた段階 — [arXiv 2604.27333](https://arxiv.org/pdf/2604.27333)

### Inferences
- 「採否と理由の記録」は保守者・後任レビュアーが「なぜこの claim が無いのか」を問う場面では価値が高い (質問の半数が理由に関する、という知見と整合)。JWT claim は外部 RP/RS との契約であり後から変えにくいため、この便益は通常の内部設計より大きい可能性がある。
- 一方、ICSA 2026 の「63% が最初から accepted」は、テンプレートが要求しても記録が事後の正当化 (post-hoc rationalization) になりやすいことの直接的な兆候。本テンプレートでも「却下理由」が実際の検討ではなく後付けの定型文になるリスクは高い。
- QOC の知見から、「設計空間が未知の領域 (新規の認可モデル、マルチテナント、委任)」ではフル列挙が有効、「定型的な領域 (標準 claim の iss/aud/exp)」では列挙は邪魔になりやすい、という使い分けが示唆される。
- 記録者 (設計者) と受益者 (レビュアー・保守者・監査) が別、という阻害要因に対しては、記録量を最小化し受益者側 (レビュアー) に負担の一部を移す設計 (例: 既定値は記録不要、逸脱時のみ理由必須) が合理的。

### Gaps
- 「根拠を記録するとレビューの欠陥検出率が上がる」ことを直接測った対照実験は見つからなかった (保守課題での効果のみ)。
- rationale decay (根拠の陳腐化) を定量化した研究は見つからなかった。ADR の放棄率が間接指標にとどまる。
- Shum & Hammond、Tang (2006) の本文中の具体的な数値・障壁リストは要旨レベルでしか確認できていない。

---

## Q2. ソフトウェアインスペクション研究: チェックリスト vs 観点ベース (PBR) vs アドホック、セキュリティレビューの実効性

### Takeaway
チェックリスト型リーディングがアドホックより優れるという頑健な証拠はなく、効果は「レビュアーの理解度・観点の明示・変更規模」に強く依存する。セキュリティレビューでは「セキュリティに注目せよ」と明示するだけで検出確率が大きく上がる一方、セキュリティチェックリスト自体は検出を増やさなかった。認証・認可・データ真正性系の欠陥はレビューで最も見逃されやすいカテゴリである。

### Cited Findings
- 【実証】Porter, Votta, Basili (1995) 要求仕様インスペクション実験: シナリオ (欠陥クラス特化) 読者はアドホック・チェックリスト読者より約 35% 良好。チェックリスト読者はアドホック読者より有効ではなかった。収集ミーティングは検出率を純増させない (ミーティングでの発見と損失が相殺) — [IEEE TSE 21(6):563-575, doi:10.1109/32.391380](https://www.cs.umd.edu/~aporter/html/scenarios.html) / [UMD 講義資料 (35% の出典)](https://www.cs.umd.edu/~mvz/handouts/emp_pbr.pdf)
- 【実証】独立追試ではシナリオ法の優位を示す証拠が得られなかった — [Empirical Software Engineering, doi:10.1023/A:1009742216007](https://doi.org/10.1023/A:1009742216007)
- 【実証】Ciolkowski (2009) PBR メタ分析: PBR チームはアドホックより有効だが、チェックリスト型より有効ではなく、明確な正の効果は見られない。研究者バイアス (開発者自身による実験) の強い兆候がある — [ESEM 2009, doi:10.1145/1671248.1671262](https://researchr.org/publication/Ciolkowski09) / [データセット (reproducer)](https://rdrr.io/cran/reproducer/man/Ciolkowski09ESEM.MetaAnalysis.PBRvsCBRorAR.html)。Madeyski & Kitchenham がこのデータを訂正・再分析している (同データセット頁)
- 【実証】Gonçalves et al. (2022) 70 名のコードレビュー実験 (アドホック / チェックリスト / ガイド付きチェックリスト): ガイド付きは単純課題で、チェックリストは複雑課題で効率・有効性を補助したが、ガイダンスとレビュー成績の強い関係は確認されず、最大の要因はコードの理解だった — [EMSE 27:99, doi:10.1007/s10664-022-10123-8](https://link.springer.com/10.1007/s10664-022-10123-8) / [登録報告 MSR 2020](https://efregnan.github.io/publications/msr2020rr.pdf)
- 【実証】Braz, Aeberhard, Çalikli, Bacchelli (ICSE 2022) 150 名のオンライン実験: レビュー時に「セキュリティに注目する」よう明示するだけで脆弱性検出確率が 8 倍。一方、セキュリティチェックリストはセキュリティ重視レビューでの検出を増やさなかった — [arXiv 2202.04586, doi:10.1145/3510003.3511560](https://arxiv.org/abs/2202.04586)
- 【実証】Edmundson et al. (ESSoS 2013) 30 名の開発者に Web アプリを手動セキュリティレビューさせた: 経験・学歴はレビュー有効性と相関せず、全体の有効性は低く、レビュアー間のばらつきが大きい — [ESSoS 2013 pp.197-212 (dblp)](https://dblp.uni-trier.de/rec/conf/essos/EdmundsonHRFMW13.html) / [Berkeley Tech Report EECS-2013-49](https://www2.eecs.berkeley.edu/Pubs/TechRpts/2013/EECS-2013-49.html)
- 【実証】Paul et al. Chromium OS の事例対照研究 (検出 516 件 vs 見逃し 374 件、AUC 0.91): 見逃しの最強予測因子はレビュー対象ディレクトリ数 (OR 0.76)。バグ修正レビューは 4.55 倍検出しやすく、当該ファイルのレビュー経験 (OR 1.83) が効く。**データ真正性の検証不足 (CWE-345) は 13/13 全件見逃し、不適切なアクセス制御 (CWE-284) は約 88%、入力検証 (CWE-20) は約 89% 見逃し**。一方「危険関数の使用 (CWE-676)」は 53/53 全件検出。実行時・広い文脈の理解を要する欠陥ほど漏れる — [arXiv 2102.06909](https://ar5iv.labs.arxiv.org/html/2102.06909)
- 【実証/二次】チューリッヒ大の面接 10 名・調査 182 名: 開発者はセキュリティ訓練・知識不足でレビュー時にセキュリティ問題を扱えず、組織もセキュアレビューを評価しない — [The Daily Swig 記事](https://portswigger.net/daily-swig/developers-still-struggling-with-security-issues-during-code-reviews-study-finds) / [arXiv 2208.04261](https://arxiv.org/pdf/2208.04261)
- 【実証/二次】GitHub の 37 OSS プロジェクト開発者 5,697 名への調査から、レビューでセキュリティ欠陥を見逃す 5 つの主要理由を特定 — [Paul 博士論文 (Wayne State)](https://digitalcommons.wayne.edu/oa_dissertations/3842)
- 【実証】医療の外部証拠: WHO 手術安全チェックリスト導入 8 施設で死亡率 1.5%→0.8%、合併症 11.0%→7.0% — [Haynes et al., NEJM 2009, doi:10.1056/NEJMsa0810119](https://doi.org/10.1056/NEJMsa0810119)
- 【実証】しかしオンタリオ州 101 病院の義務化導入では、ほぼ全病院が約 100% 遵守を報告したにもかかわらず、死亡率 0.71%→0.65% (OR 0.91, 非有意)、合併症等も改善なし。Leape の論説は、チェックリストが形式的作業 (perfunctory) になっていた可能性と、現場適応・訓練・チームのワークフロー化が必要だと指摘 — [Urbach et al., NEJM 2014 (PubMed 24620866)](https://pubmed.ncbi.nlm.nih.gov/24620866/) / [PSNet 解説](https://psnet.ahrq.gov/issue/introduction-surgical-safety-checklists-ontario-canada)。Gawande は方法論 (導入後 3 か月での測定など) を批判 — [Author reply (PubMed 24918385)](https://pubmed.ncbi.nlm.nih.gov/24918385/)
- 【意見/実務報告】SmartBear/Cisco の事例に基づく実務指針: 一度に 200-400 LOC、60-90 分以内、速すぎるレビュー (約 500 LOC/時超) で検出力が低下 — [SmartBear: Best Practices for Peer Code Review](https://smartbear.com/learn/code-review/best-practices-for-peer-code-review/) (ベンダー資料であり査読研究ではない)

### Inferences
- **「採否と理由が全部あれば網羅漏れは起きない」は成り立たない。** テンプレートが保証できるのは「列挙された候補について判断が記録されていること」だけで、「列挙されなかった候補」(unknown unknowns) は検出できない。Chromium の結果では、JWT 設計に最も関係する CWE-345 (データ真正性) と CWE-284 (アクセス制御) がまさに最も見逃されるクラスであり、これは記述の有無ではなく実行時文脈の理解不足に起因する。
- 「理由の妥当性だけを評価する」とレビュアーの注意を狭めることは、Braz らの「注目点を明示すると検出が上がる」効果を得られる半面、指示された焦点の外 (例: claim 以外の鍵管理・トークン受け渡し経路・キャッシュ) を見なくなる可能性がある。焦点の明示は有効だが「だけ」は危険。
- チェックリスト型の効果がアドホックと同等程度、という知見から、テンプレートの価値は「チェック項目の網羅」よりも「レビュアーに理解のための構造化情報 (候補・採否・理由・前提) を渡すこと」にあると考えるのが整合的 (Gonçalves の「理解が最大因子」)。
- オンタリオの結果は、遵守率 100% の報告と実効性が無関係になり得る (checkbox compliance) ことの強い外部証拠。テンプレートの「全欄記入済み」は品質指標にならない。
- PBR (観点ベース) は、JWT では「発行者 (IdP) 視点 / 検証者 (RS) 視点 / 攻撃者視点 / 運用・監査視点」などに分ける形で応用できるが、メタ分析上チェックリストに勝る保証はない。観点分割はレビュアー間の重複を減らす手段と位置付けるのが妥当。

### Gaps
- Edmundson の「7 件の脆弱性を全員が見つけられなかった」等の具体数値は、PDF をテキスト化できず確認できなかった (要旨では「有効性は低く、ばらつき大」まで確認)。
- Microsoft / Google 社内の設計レビュー (設計段階の脅威モデリング) の有効性を定量化した公開研究は見つからなかった。Microsoft SDL・OWASP は手順を示すが効果測定データは示していない。
- チェックリストの長さと疲労 (項目数と検出率の関係) をソフトウェア領域で測った研究は見つからなかった (Chromium のレビュー経験と見逃しの弱い正相関が疲労仮説として言及される程度)。
- 「設計書レビュー」(コードではなく設計文書) に限定したセキュリティレビュー実験はほぼ見当たらない。

---

## Q3. 事前記入済みの「却下候補カタログ」のリスク (アンカリング、コピペ理由、完全性の錯覚) と緩和策

### Takeaway
却下候補カタログ自体の効果・リスクを直接測った研究は見つからなかったが、隣接証拠 (ADR の 63% が熟議なしで accepted、オンタリオの形式的遵守、DR の事後再構成性) は、カタログが「考えた形跡の定型化」を生むリスクを強く示唆する。緩和策は「証拠リンク必須」「既定と逸脱の区別」「サンプリング深掘り」「列挙外を問う質問」が有力だが、これらの効果も実証は乏しく意見レベル。

### Cited Findings
- 【実証】アンカリング: 提示された初期値に判断が引き寄せられる — [Tversky & Kahneman, Science 1974, doi:10.1126/science.185.4157.1124](https://doi.org/10.1126/science.185.4157.1124)
- 【実証/二次】ADR の約 63% が最初から accepted で作られ熟議を迂回 (形式だけの記録) — [ICSA 2026](https://conf.researchr.org/details/icsa-2026/icsa-2026-papers/34/Architecture-Decision-Records-Adoption-Impact-and-Developer-Engagement-in-Open-Sou)
- 【実証】遵守報告ほぼ 100% でも成果改善なし、形式的実施の疑い — [Urbach et al. 2014](https://pubmed.ncbi.nlm.nih.gov/24620866/) / [PSNet](https://psnet.ahrq.gov/issue/introduction-surgical-safety-checklists-ontario-canada)
- 【実証】セキュリティチェックリストは検出を増やさなかったが、「セキュリティに注目」の指示は 8 倍効いた — [Braz et al. ICSE 2022](https://arxiv.org/abs/2202.04586)
- 【意見】価値ベースで記録対象を絞ることで記録コストと形骸化を抑える — [Falessi et al. WICSA 2008](https://art.torvergata.it/bitstream/2108/57813/1/2008_WICSA_FCK_Value-Based%20Design%20Decision%20Rationale%20Documentation%20Principles%20and%20empirical%20feasibility%20study.pdf)
- 【実証】QOC は制約の強い設計空間では邪魔になる (= 定型項目に毎回理由を書かせるのは逆効果になり得る) — [KMi Tech Report](https://kmi.open.ac.uk/publications/techreport/kmi-95-13)

### Inferences
- カタログ化の主なリスク:
  1. **アンカリング / 列挙の閉包化**: カタログにある候補だけが検討対象になり、プロダクト固有の候補 (例: 独自の tenant 境界 claim、step-up 認証の acr/amr、委任の act/may_act) が出てこない。
  2. **コピペ理由**: カタログに例示理由があると、そのまま転記される。理由の文面がリポジトリ横断で一致する率は検出可能な警告指標。
  3. **完全性の錯覚**: 「全行に採否がある」ことが「網羅した」と誤認される (Q2 の CWE-345/284 の見逃しは記入とは独立)。
  4. **レビュアーの rubber-stamping**: 理由が「もっともらしく書かれている」かを判定するだけになり、主張の真偽 (実装・設定が本当にそうなっているか) を確認しない。
- 緩和策 (いずれも実証は未確認、設計提案):
  - **理由の最低品質ルーブリック**: 理由は (a) 脅威/要件 ID への参照、(b) 前提条件 (例: 「RS は 1 つのみ」)、(c) 前提が崩れたときの再検討トリガー、のうち最低 2 つを含むこと。「不要」「標準に従う」だけの理由は不可。
  - **証拠リンク必須**: 採用 claim は検証コード / 設定 / contract test へのリンク、却下 claim は代替手段 (例: 「権限は token ではなく PDP 照会で解決」) の所在を示す。主張と実装の乖離を機械的に追える。
  - **既定と逸脱の分離**: カタログ既定値 (例: `aud` 必須検証) どおりなら記入不要または一括宣言、逸脱時のみ理由必須。記録負担を価値の高い箇所に集中 (Falessi の価値ベース原則と整合)。
  - **カタログ外の強制質問 (red-team prompts)**: 「この設計で攻撃者が最初に偽造/再利用/混同を試みるトークンはどれか」「カタログにない claim / ケースを最低 1 つ挙げよ (無ければその理由)」をテンプレートに固定設置。
  - **サンプリング深掘り**: レビュアーは却下理由のうち無作為に N 件 (例: 2-3 件) を選び、実装・設定まで追跡確認する。全件の表面確認より抜き打ちの深い確認の方が形骸化を抑えるという発想 (監査サンプリングの類推、実証は未確認)。
  - **例示理由を載せない**: カタログには候補と「検討観点 (問い)」だけを載せ、理由の模範文は載せない (コピペ源を断つ)。

### Gaps
- 「却下候補を事前記入したテンプレート」がアンカリングや網羅性に与える影響を測った SE 研究は見つからなかった。
- 理由品質ルーブリックやサンプリングレビューの効果を SE で測った研究は見つからなかった (上記は推論・提案)。

---

## Q4. レビュー報告テンプレート: 重大度分類、指摘とチェック項目のトレーサビリティ、テンプレート価値を測る指標

### Takeaway
インスペクション研究の伝統では、検出欠陥数・工数あたり検出数・流出欠陥 (escaped defects) が基本指標であり、Chromium 研究のように「検出された欠陥」と「流出した欠陥」を比較するケース対照の考え方が、テンプレート価値の測定に最も直接応用できる。指摘をテンプレート項目に紐付けることで「どの項目が効いているか/一度も効いていないか」を判定できる。

### Cited Findings
- 【実証】インスペクション工程の測定 (検出欠陥・工数) を前提とした Fagan のインスペクション — [Fagan, IBM Systems Journal 15(3), 1976, doi:10.1147/sj.153.0182](https://doi.org/10.1147/sj.153.0182)
- 【実証】検出されたレビューと流出したレビューを比較し、見逃しやすい欠陥クラス・状況を特定する事例対照設計 — [Paul et al., arXiv 2102.06909](https://ar5iv.labs.arxiv.org/html/2102.06909)
- 【実証】レビューミーティングは検出率を純増させない — [Porter, Votta, Basili 1995](https://www.cs.umd.edu/~aporter/html/scenarios.html)
- 【意見/実務報告】レビュー速度・時間の上限と検査率の指標化 — [SmartBear](https://smartbear.com/learn/code-review/best-practices-for-peer-code-review/)
- 【意見】CVSS 等の標準重大度体系 — [FIRST CVSS v4.0](https://www.first.org/cvss/v4-0/)

### Inferences
- 報告テンプレートの推奨項目:
  - 指摘 ID / 重大度 (例: Blocker=トークン偽造・権限昇格に直結、Major=誤検証の余地、Minor=記述・保守性) / 対象 (claim 名・ケース ID) / **起点: どのテンプレート項目・観点・red-team 質問から見つかったか、または「テンプレート外」** / 種別 (理由不備・前提誤り・実装乖離・候補漏れ) / 対応と検証証拠。
  - 「テンプレート外で見つかった指摘」と「本番・テストで後から見つかった流出欠陥」を記録することが、前提 (網羅漏れは起きない) を継続的に反証・改善する唯一の手段。
- テンプレート価値の測定指標:
  - 流出欠陥率: 設計レビュー後に実装・ペンテスト・インシデントで発見された claim/認可欠陥のうち、テンプレート上に候補として存在したもの / しなかったもの。前者は「理由判定の失敗」、後者は「カタログの穴」。
  - 項目別の発火率: 一定期間一度も指摘を生まない項目は削除・統合候補 (チェックリスト肥大化対策)。
  - 「テンプレート外」指摘の比率: 高ければカタログ不足、ゼロが続けばレビュアーが枠外を見ていない兆候。
  - 記入・レビュー工数 (分) と、Blocker/Major 指摘数の比。
  - 理由の重複率 (コピペ指標)。
- 少数プロジェクトでは統計的に有意な測定は困難なため、定量指標よりも「流出欠陥ごとのふりかえりでカタログ・観点を更新する」定性ループが現実的。

### Gaps
- 設計レビュー (文書レビュー) 固有の工数あたり検出数のベンチマーク値は見つからなかった。
- 重大度分類とトレーサビリティがレビュー効果を高めるという実証研究は見つからなかった (実務慣行・意見レベル)。

---

## Q5. コストと便益: 重いテンプレートの採用障壁、テーラリング、docs-as-code、自動化 (スキーマ検証・lint・contract test・LLM 支援レビュー)

### Takeaway
重いテンプレートは「記録者と受益者が別」「便益が遅れる」ため放棄されやすく (ADR の約半数は 5 件未満で停止)、軽量版と完全版のテーラリングと、機械検証可能な部分の自動化が採用の鍵。LLM 支援レビューは静的解析より優れるとの報告がある一方、誤検知率は高く、人手レビューの代替ではなく補助・トリアージの位置付けが妥当。

### Cited Findings
- 【実証/意見】阻害要因: 便益が遅れる・記録者と受益者が別 — [Falessi et al. WICSA 2008](https://art.torvergata.it/bitstream/2108/57813/1/2008_WICSA_FCK_Value-Based%20Design%20Decision%20Rationale%20Documentation%20Principles%20and%20empirical%20feasibility%20study.pdf)
- 【実証/二次】ADR 採用リポジトリの約 50% が 5 件未満で停止 — [arXiv 2604.03826](https://arxiv.org/html/2604.03826)
- 【実証】ADR は導入チームに有用と評価されるが、文化・暗黙知・プロセス/ツールが課題 — [Chalmers 2023](https://research.chalmers.se/en/publication/538920)
- 【実証】Chromium: 見逃しへの対策としてレビューだけでなく静的解析・ファジングで補完し、絡み合った変更を避け、レビュアー負荷を管理すべき — [arXiv 2102.06909](https://ar5iv.labs.arxiv.org/html/2102.06909)
- 【実証/二次】LLM によるセキュリティコードレビュー (534 ファイル): LLM は最先端静的解析を有意に上回り、推論最適化モデルが汎用モデルより良い。ただし初期版では「能力は限定的」とも記述、GPT-4 は簡潔でない・指示非準拠の応答が多かった — [Yu et al., arXiv 2401.16310](https://arxiv.org/html/2401.16310v5)
- 【実証/二次】プロジェクト規模の LLM 脆弱性検出: LLM・従来手法とも誤検出率 (false discovery rate) が高く、385 件の報告を 150 時間超かけて人手検証。LLM は再現率は低いが従来ツールより固有の脆弱性を多く発見 — [Li et al., arXiv 2601.19239](https://arxiv.org/html/2601.19239v1)
- 【実証/二次】静的解析 + LLM のハイブリッドで誤警告の 94-98% を除去しつつ高い再現率を維持 (Tencent 産業研究、セキュリティ限定ではない) — [Du et al., arXiv 2601.18844](https://arxiv.org/pdf/2601.18844)
- 【意見】Microsoft SDL は設計段階の脅威モデリングを必須プラクティスとして位置付け — [Microsoft SDL Practices](https://www.microsoft.com/en-us/securityengineering/sdl/practices)
- 【意見】OWASP ASVS はトークン/セッション/アクセス制御の検証要件を段階 (レベル) 別に提供し、テーラリングの土台になる — [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/)

### Inferences
- **自動化で置き換えるべき部分**: claim レジストリ (YAML/JSON) を正とし、(1) JSON Schema でレジストリ形式と必須欄 (採否・理由・証拠リンク・再検討トリガー) を検証、(2) lint で「理由が空/定型文」「証拠リンク切れ」「カタログ既定からの逸脱なのに理由なし」「理由の重複」を検出、(3) 発行側の実トークンと検証側の期待を contract test (例: 発行トークンのデコード結果がレジストリと一致、未登録 claim の混入検知、aud/iss/exp 検証のネガティブテスト) で突合。これで「記述と実装の乖離」という rubber-stamping の主要盲点を機械で潰せ、人間レビュアーは理由の妥当性と枠外の思考に集中できる。
- **LLM 支援レビュー**: レジストリと設計書をテンプレート・観点文書に照らして「理由が前提と矛盾していないか」「カタログ外の候補はないか」の一次スクリーニングに使うのは合理的だが、誤検知の多さと見逃しから、人手判断の代替にはしない。LLM の指摘も報告テンプレートの「起点」欄で区別して記録し、有効率を測る。
- **テーラリング案**: Lite (既存パターン踏襲・単一 RS・内部 API: 逸脱のみ記録 + red-team 質問 3 つ) / Full (新規発行者、外部 RP、マルチテナント、委任・トークン交換、規制対象: 全候補列挙 + 観点別レビュー + サンプリング深掘り)。判定基準をテンプレート冒頭に置く。
- docs-as-code (レジストリを repo 内に置き PR でレビュー) は、ADR 研究の「中央とローカルの置き場所」課題に対して、claim レジストリは発行者 repo を正とし、消費者側は参照・contract test で追従する構成が整合的。

### Gaps
- 設計テンプレートの記入工数を実測した研究は見つからなかった。
- JWT claim レジストリの lint / contract test の効果を測った公開事例は見つからなかった。
- LLM による「設計文書」(コードでなく) のセキュリティレビュー評価は見つからなかった。

---

## Q6. 総合: どの条件で高価値、どこで低価値か

### Takeaway
この活動は「網羅漏れを無くす仕組み」ではなく、「判断を可視化して再検討可能にし、レビュアーに理解の足場を与え、流出欠陥からカタログを学習させる仕組み」として設計すれば高価値。前提「理由だけ見ればよく漏れは起きない」は実証と矛盾するため、テンプレートと観点文書の文言から外すべき。

### Cited Findings
- 【実証】チェックリストはアドホックより一貫して優れるとは言えない — [Porter et al. 1995](https://www.cs.umd.edu/~aporter/html/scenarios.html); [Ciolkowski 2009](https://researchr.org/publication/Ciolkowski09); [Gonçalves et al. 2022](https://link.springer.com/10.1007/s10664-022-10123-8)
- 【実証】焦点の明示は効くがセキュリティチェックリストは効かなかった — [Braz et al. 2022](https://arxiv.org/abs/2202.04586)
- 【実証】データ真正性・アクセス制御系欠陥はレビューで最も漏れる — [Paul et al.](https://ar5iv.labs.arxiv.org/html/2102.06909)
- 【実証】チェックリストは適切に導入されれば大きな効果 (Haynes 2009)、形式的導入では効果なし (Urbach 2014) — [NEJM 2009](https://doi.org/10.1056/NEJMsa0810119); [NEJM 2014](https://pubmed.ncbi.nlm.nih.gov/24620866/)
- 【実証】DR は理解の浅い設計空間で有効、定型空間では邪魔 — [KMi](https://kmi.open.ac.uk/publications/techreport/kmi-95-13)
- 【実証/二次】記録は形骸化・放棄されやすい — [ICSA 2026](https://conf.researchr.org/details/icsa-2026/icsa-2026-papers/34/Architecture-Decision-Records-Adoption-Impact-and-Developer-Engagement-in-Open-Sou); [arXiv 2604.03826](https://arxiv.org/html/2604.03826)

### Inferences
- **高価値の条件**
  - トークンが組織・チーム境界を越える契約 (外部 RP/RS、複数 RS、マルチテナント) で、後からの claim 変更コストが高い。
  - 設計空間が未知・新規 (委任、token exchange、step-up、細粒度認可を token に載せるか PDP に問うかの判断)。
  - 担当者交代・監査・インシデント対応で「なぜその claim が無い/あるのか」を後から問われる。
  - レジストリが機械可読で、lint・contract test により記述と実装の一致が自動検証されている。
  - 流出欠陥のふりかえりでカタログと観点を更新する運用がある (Haynes 型の「現場適応・訓練・ワークフロー化」)。
- **低価値 (またはマイナス) の条件**
  - 定型的な単一サービス内部 API で、カタログ既定どおりの設計 → 全列挙は儀式化し、理由はコピペになる。
  - 記入率・遵守率を KPI にしている (オンタリオ型の形式的遵守)。
  - レビュアーに「理由の妥当性だけ」を見る役割を課し、枠外の質問や実装確認を求めない。
  - 記入者に見返りがなく、レビュー結果がカタログ改善に還流しない。
- **前提の修正提案 (文言)**: 「全候補に採否と理由があれば網羅漏れは起こらない」→「採否と理由の記録は、*列挙された*候補の判断漏れと判断の不透明さを減らす。列挙されなかった候補は、観点別の問い・red-team 質問・流出欠陥のふりかえりで補う」。
- **具体的設計推奨 (要約)**
  1. カタログは「候補 + 検討の問い」のみ、模範理由は載せない。
  2. 既定どおりは一括宣言、逸脱と却下のみ理由必須 (理由ルーブリック: 脅威/要件参照・前提・再検討トリガー)。
  3. 採用 claim には検証の証拠リンク (コード・設定・contract test) 必須。
  4. 観点文書は PBR 的に視点分割 (発行者 / 検証者 / 攻撃者 / 運用) し、各視点に「カタログ外を 1 つ挙げよ」を固定。CWE-345/284 系 (署名検証・alg/kid 混同・aud 取り違え・権限 claim の信頼境界) は重点問いとして明示 (Braz の焦点明示効果)。
  5. レビュアーは却下理由を無作為抽出で 2-3 件深掘り (実装まで追跡)。
  6. 報告テンプレートに「起点 (項目/観点/枠外/LLM)」「種別 (理由不備/前提誤り/実装乖離/候補漏れ)」欄。流出欠陥ログを別に持つ。
  7. Lite/Full の 2 段テーラリングと判定基準。
  8. レジストリの schema 検証・lint・contract test を CI 化し、LLM は一次スクリーニングに限定。
  9. 一定期間発火しない項目は削除し、チェックリストを短く保つ。

### Gaps
- 本方式 (候補列挙 + 採否 + 理由 + 理由のみ評価) を JWT/認可設計に適用した事例研究・効果測定は見つからなかった。上記の高/低価値条件は隣接領域の証拠からの推論である。
