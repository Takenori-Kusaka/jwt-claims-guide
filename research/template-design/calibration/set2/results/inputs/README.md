# 採点者・判定者に渡したもの（改訂 S2 の当てはめの記録）

> LLM による測定。人による検証ではない。

| ファイル | 中身 |
| --- | --- |
| `scorer-S1-instructions.txt`・`scorer-S2-instructions.txt` | 採点者のセッションに渡した指示の全文（Agent の prompt としてそのまま渡した）。採点者のフォルダには、`rules/`（初回と 2 組目の `protocol.md` の写し）・`seeded_errors.yaml`・`designs/`（4 つの設計書を `materialize` したもの）・`outputs/`（12 件の出力）だけを置いた |
| `judge-C-instructions.txt`・`judge-D-instructions.txt` | 判定者のフォルダに置いた指示の全文。Agent の prompt は次の 1 段落だけで、全文はこのファイルを読ませた |
| `judge-rules.md` | 判定者のフォルダの `rules.md`（初回の手順の 7. の判定の節と、2 組目の手順の 7. の S2・S4・S5・S7。清掃の記録へのリンクは除いた）。判定 C・D で同じ |
| `to_judge-C.yaml`・`to_judge-D.yaml` | 判定する指摘の一覧。seeded は、どちらの採点者もどの誤りにも当てなかった指摘（取りまとめのセッションが、採点者の当てた指摘の和を出力の表から引いて作った）。対照は表 (1) の全部 |

判定者のフォルダには、ほかに `designs/`（その双子の 2 つの設計書）・`packet-extras/`（その 2 つの設計書の `sheet.md`・`ci-result.txt`）・`seeded_errors.yaml`（その双子の seeded の誤りだけに絞ったもの）・`findings/`（その双子の 6 件の出力）を置いた。採点者の出力（`score-*.yaml`）・清掃の記録・初回の結果は置いていない。

判定者の Agent の prompt（C の例。D はフォルダの名前だけが違う）：

```text
You are a judge in a calibration measurement. Your full instructions are in <judge folder>/instructions.txt — read it first and follow it exactly. Work only inside that folder (<judge folder>) with Read/Glob/Grep and the one Write the instructions name, plus official spec/vendor docs on the web only if a finding turns on such a fact. Do not use Bash, git, or any other local file or folder (in particular nothing elsewhere in the scratchpad and nothing in any repository).
```

- 指示の中のパス（取りまとめのセッションのスクラッチのフォルダ）は、渡したときのまま
