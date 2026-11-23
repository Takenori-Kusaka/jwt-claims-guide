# -*- coding: utf-8 -*-
"""Check the review materials (#5): every question has an ID, a field to look at, evidence and links that resolve.

  python tools/review_check.py [--root DIR] [--list] [--counts]

Files: templates/review/*.md and templates/review/contrasts/*.md.

A question in perspectives.md is a block that starts with a line `**<id>**　<question>` (a full-width space after the
bold ID) and is followed by the bullet lines `- 見る欄：`, `- No なら：`, `- つながり：`, `- 根拠：`. An anchor line
`<a id="<id>"></a>` may precede it (then the anchor must equal the ID).

Checks (all errors):
  V1  every file starts with `<!-- template_version: X.Y.Z -->` (templates/CONTRIBUTING.md 4.)
  V2  question IDs are lower-case kebab-case and unique; an anchor right before a question equals its ID; the question
      text ends with 「か」 (optionally followed by a bracketed note), so that it can be answered Yes / No, and is not in the
      negative form (「〜ないか」), so that Yes always means "meets"; the four bullet
      lines are present and not empty
  V3  見る欄 names at least one design-doc field (`template:` item ID, `registry:` column, `catalog:` entry) and every
      such ref resolves (tools/trace_check.py's resolvers: the anchor / schema property / YAML node exists)
  V4  every element of 根拠 has a known evidence form (tools/template_check.py's T3: slide ids exist, RFCs and tracking
      issues are pinned in tools/template_sources.yaml, repository paths exist)
  V5  つながり names at least one contrast table section (`review:contrasts/<name>#<anchor>`); every ap-* question also
      names an incident (`事例`)
  V6  every ref in backticks in any review file resolves: `review:` (file and anchor), `template:`, `registry:`,
      `catalog:`; `lint:<id>` is a rule of tools/claim_lint/RULES.md, or a planned item of templates/trace/planned_items.yaml
      marked `（未実装）` right after it; `test:` is a planned item marked `（未実装）` (until templates/runtime/ exists,
      then it must resolve)
  V7  every question ID quoted in backticks in a review file (`q-…`, `ap-…`, `pa-…`, `dc-…`, `cf-…`, `cd-…`) is a question
      of perspectives.md, or a question of templates/registry/questions.yaml (`q-sub`, `q-actor` ...); a perspectives
      question ID must not equal a questions.yaml ID
  V8  the anti-pattern questions ap-1-1..ap-1-8 and ap-2-1..ap-2-9 (slides 146 / 147, 17 rows) all exist
  V9  each contrast table has the sections question, unit, table, not-covered, misuse, evidence (anchors), and its
      misuse section is a table whose last column names at least one question ID per row
  V10 every requirement of templates/trace/requirements.yaml that has a `review:` planned item: the item names an anchor,
      the file and anchor exist, and that section contains `req:<requirement id>` (whatever the status; trace_check.py
      checks the other kinds when a requirement becomes 実装済み)
  V11 escalation.md: every criterion ID in the first table has its own anchor section with a 根拠 line; every section of
      decision_tree.md has a 根拠 line
  V13 per file: no duplicate anchors; every relative Markdown link `[..](path#anchor)` (outside code fences) points to an
      existing file and, when it names an anchor, to an `<a id>` of that file (inline links with a title, reference definitions
      `[r]: target` and `<a href>` included; anchors are counted in any quoting, `id` or `name`); in perspectives.md a bold question-ID line
      (`**q-…**`, `**ap-…**` …) that does not match the question form (full-width space after the ID) is an error, and
      見る欄・つながり must quote every ref (`template:`, `registry:`, `catalog:`, `review:`, `lint:`, `test:`) in backticks
  V12 the table between `<!-- counts:begin -->` and `<!-- counts:end -->` of templates/review/README.md equals the number
      of questions per stage (and the total)

Not checked by machine: whether a question is the right question, whether a field really answers it, whether a source
supports a claim (the 10% sampled check of templates/CONTRIBUTING.md 2.).

--list prints the question IDs with their stage; --counts prints the number of questions per stage.
"""
import argparse
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import check_slide_refs  # noqa: E402
import template_check  # noqa: E402
import trace_check  # noqa: E402

REVIEW_DIR = os.path.join('templates', 'review')
ID_PREFIXES = ('q-', 'ap-', 'pa-', 'dc-', 'cf-', 'cd-')
Q_START = re.compile(r'^\*\*([^*]+)\*\*　(.+)$')
ID_OK = re.compile(r'^[a-z0-9][a-z0-9-]*$')
ANCHOR_LINE = re.compile(r'^<a id="([^"]+)"></a>\s*$')
FIELD_RE = re.compile(r'^- (見る欄|No なら|つながり|根拠)：\s*(.*)$')
REF_IN_TICKS = re.compile(r'`((?:review|template|registry|catalog|lint|test|calib):[A-Za-z0-9_][A-Za-z0-9_./-]*(?:#[A-Za-z0-9_][A-Za-z0-9_.-]*)?)`(（未実装）)?')
QID_IN_TICKS = re.compile(r'`((?:q|ap|pa|dc|cf|cd)-[a-z0-9-]+)`')
STAGES = [('stage-definition', '1. 定義'), ('stage-issuance', '2. 発行'), ('stage-propagation', '3. 伝搬'),
          ('stage-validation', '4. 検証'), ('stage-authorization', '5. 認可'), ('stage-operations', '6. 運用')]
CONTRAST_SECTIONS = ('question', 'unit', 'table', 'not-covered', 'misuse', 'evidence')
AP_IDS = [f'ap-1-{n}' for n in range(1, 9)] + [f'ap-2-{n}' for n in range(1, 10)]
FIELD_KINDS = ('template', 'registry', 'catalog')
NEGATIVE_Q = re.compile(r'(?:ないか|無いか|ませんか|なかったか|無かったか)')
QUESTION_END = re.compile(r'か(?:（[^）]*）)?$')


def review_files(root):
    base = os.path.join(root, REVIEW_DIR)
    out = []
    for d in (base, os.path.join(base, 'contrasts')):
        if os.path.isdir(d):
            out += sorted(os.path.join(d, n) for n in os.listdir(d) if n.endswith('.md'))
    return out


def rel_of(root, path):
    return os.path.relpath(path, root).replace(os.sep, '/')


def parse_questions(text):
    """Questions of perspectives.md: dicts with id, line, text, anchor, fields, stage."""
    lines = text.splitlines()
    out, stage, last_anchor, last_anchor_line, fenced = [], None, None, -10, False
    for k, line in enumerate(lines):
        if line.startswith('```'):
            fenced = not fenced
            continue
        if fenced:
            continue
        am = ANCHOR_LINE.match(line.strip())
        if am:
            last_anchor, last_anchor_line = am.group(1), k
            if am.group(1) in dict(STAGES):
                stage = am.group(1)
            continue
        if line.startswith('## 7.'):
            stage = None
        m = Q_START.match(line)
        if not m:
            continue
        q = {'id': m.group(1), 'line': k + 1, 'text': m.group(2).strip(), 'stage': stage, 'fields': {},
             'anchor': last_anchor if 0 < k - last_anchor_line <= 2 else None}
        j = k + 1
        while j < len(lines) and lines[j].strip():
            fm = FIELD_RE.match(lines[j])
            if fm:
                q['fields'][fm.group(1)] = fm.group(2).strip()
            j += 1
        out.append(q)
    return out


def resolve(root, ref, planned):
    """None when ref resolves, else the problem."""
    try:
        kind, path, anchor = trace_check.parse_ref(ref)
    except ValueError as e:
        return f'{ref} の書き方が誤り（{e}）'
    if kind == 'test' and not os.path.isdir(os.path.join(root, 'templates', 'runtime')):
        return None if ref in planned else f'{ref} は planned_items.yaml に無い'
    if kind == 'calib':
        return None if ref in planned else f'{ref} は planned_items.yaml に無い'
    resolver = trace_check.RESOLVERS.get(kind)
    if not resolver:
        return f'{ref}：種類 {kind} は解決できない'
    problem, _ = resolver(root, path, anchor)
    return problem


def check(root):
    errors = []
    slides = {s['id'] for s in check_slide_refs.load_json(os.path.join(root, 'deck', 'slide_ids.json'), [])}
    template_check.load_sources(root)
    planned = {}
    data = trace_check.yaml_load(trace_check._read(os.path.join(root, trace_check.ITEMS_FILE)))
    for it in (data or {}).get('items') or []:
        planned[str(it.get('ref'))] = it
    files = review_files(root)
    persp = os.path.join(root, REVIEW_DIR, 'perspectives.md')
    if not os.path.isfile(persp):
        return [('V2', 'templates/review/perspectives.md', 'ない')], [], files
    questions = parse_questions(trace_check._read(persp))
    reg_q = set()
    qpath = os.path.join(root, 'templates', 'registry', 'questions.yaml')
    if os.path.isfile(qpath):
        qdata = trace_check.yaml_load(trace_check._read(qpath)) or {}
        reg_q = {str(x.get('id')) for key in ('questions', 'pending') for x in (qdata.get(key) or []) if isinstance(x, dict)}
    qids = {}
    for q in questions:
        where = f'perspectives.md:{q["line"]} {q["id"]}'
        if not ID_OK.match(q['id']) or not q['id'].startswith(ID_PREFIXES):
            errors.append(('V2', where, f'問い ID は {"・".join(ID_PREFIXES)} で始まる英小文字・数字・- で書く'))
        if q['id'] in qids:
            errors.append(('V2', where, f'問い ID が重複している（{qids[q["id"]]} 行）'))
        qids[q['id']] = q['line']
        if q['id'] in reg_q:
            errors.append(('V2', where, '問い ID が templates/registry/questions.yaml の問いの ID と同じ（別の ID にする）'))
        if q['anchor'] and q['anchor'] != q['id']:
            errors.append(('V2', where, f'直前のアンカー {q["anchor"]} が問い ID と違う'))
        if not QUESTION_END.search(q['text']):
            errors.append(('V2', where, '問いの文が「か」で終わらない（Yes／No で答えられる形にする）'))
        if NEGATIVE_Q.search(q['text']):
            errors.append(('V2', where, '問いが否定の形（「〜ないか」）。Yes が「満たす」になる肯定の形にする（PR #45 の点検）'))
        for f in ('見る欄', 'No なら', 'つながり', '根拠'):
            if not q['fields'].get(f):
                errors.append(('V2', where, f'「- {f}：」の行が無いか、空'))
        see = q['fields'].get('見る欄', '')
        refs = [m.group(1) for m in REF_IN_TICKS.finditer(see)]
        if not any(r.split(':', 1)[0] in FIELD_KINDS for r in refs):
            errors.append(('V3', where, '見る欄に設計書の欄（template:・registry:・catalog:）が無い'))
        for r in refs:
            p = resolve(root, r, planned)
            if p:
                errors.append(('V3', where, p))
        for el in template_check.split_evidence(q['fields'].get('根拠', '')):
            _, err = template_check.evidence_form(el, slides)
            if err:
                errors.append(('V4', where, err))
        links = q['fields'].get('つながり', '')
        if not re.search(r'`review:contrasts/[a-z0-9-]+#[a-z0-9-]+`', links):
            errors.append(('V5', where, 'つながりに対比表の節（review:contrasts/<名前>#<節>）が無い'))
        if q['id'].startswith('ap-') and '事例' not in links:
            errors.append(('V5', where, 'アンチパターンの問いに事例が無い'))
    for ap in AP_IDS:
        if ap not in qids:
            errors.append(('V8', 'perspectives.md', f'アンチパターンの問い {ap} が無い'))
    # V1, V6, V7, V9 over all files
    for path in files:
        rel = rel_of(root, path)
        text = trace_check._read(path)
        lines = text.splitlines()
        if not lines or not template_check.VERSION_RE.match(lines[0]):
            errors.append(('V1', rel, '1 行目が <!-- template_version: X.Y.Z --> でない'))
        for k, line in enumerate(lines, 1):
            for m in REF_IN_TICKS.finditer(line):
                ref, unimpl = m.group(1), bool(m.group(2))
                kind = ref.split(':', 1)[0]
                if kind == 'lint':
                    problem = resolve(root, ref, planned)
                    if problem:
                        if ref in planned and unimpl:
                            continue
                        errors.append(('V6', f'{rel}:{k}', f'{ref} は RULES.md に無い' + ('（計画にあるなら「（未実装）」と書く）' if ref in planned else '（計画にも無い）')))
                    elif unimpl:
                        errors.append(('V6', f'{rel}:{k}', f'{ref} は実装済みなのに「（未実装）」と書いている'))
                    continue
                if kind == 'test' and not os.path.isdir(os.path.join(root, 'templates', 'runtime')) and not unimpl:
                    errors.append(('V6', f'{rel}:{k}', f'{ref} はまだ無い実行テスト。「（未実装）」と書く'))
                    continue
                problem = resolve(root, ref, planned)
                if problem:
                    errors.append(('V6', f'{rel}:{k}', problem))
            for m in QID_IN_TICKS.finditer(line):
                if m.group(1) not in qids and m.group(1) not in reg_q:
                    errors.append(('V7', f'{rel}:{k}', f'問い ID {m.group(1)} は perspectives.md に無い'))
        if rel.startswith('templates/review/contrasts/'):
            anchors = set(re.findall(r'<a id="([^"]+)"></a>', text))
            for s in CONTRAST_SECTIONS:
                if s not in anchors:
                    errors.append(('V9', rel, f'節 <a id="{s}"></a> が無い'))
            problem, scope = trace_check._md_part(root, rel, 'misuse')
            if not problem:
                rows = [l for l in scope.splitlines() if l.startswith('| m-')]
                if not rows:
                    errors.append(('V9', rel, '典型的な誤用の表（| m-<n> | … |）が無い'))
                for r in rows:
                    last = r.strip().strip('|').split('|')[-1]
                    if not QID_IN_TICKS.search(last):
                        errors.append(('V9', rel, f'誤用 {r.split("|")[1].strip()} の「見つける問い」に問い ID が無い'))
    # V10 requirements with review: items
    req = trace_check.yaml_load(trace_check._read(os.path.join(root, trace_check.REQ_FILE)))
    for r in (req or {}).get('requirements') or []:
        for ref in r.get('planned_items') or []:
            if not str(ref).startswith('review:'):
                continue
            where = f'{r.get("id")} → {ref}'
            try:
                _, path, anchor = trace_check.parse_ref(ref)
            except ValueError as e:
                errors.append(('V10', where, str(e)))
                continue
            if not anchor:
                errors.append(('V10', where, '節（#アンカー）を指していない。問い・節の ID まで指す'))
                continue
            problem, scope = trace_check._md_part(root, os.path.join(REVIEW_DIR, path + '.md'), anchor)
            if problem:
                errors.append(('V10', where, problem))
            elif not trace_check.marker_re(r['id']).search(scope or ''):
                errors.append(('V10', where, f'その節に req:{r["id"]} が無い'))
    # V11 escalation and decision tree
    esc = os.path.join(root, REVIEW_DIR, 'escalation.md')
    if os.path.isfile(esc):
        text = trace_check._read(esc)
        ids = re.findall(r'^\| `([a-z0-9-]+)` \|', text, re.M)
        for i in ids:
            problem, scope = trace_check._md_part(root, os.path.join(REVIEW_DIR, 'escalation.md'), i)
            if problem:
                errors.append(('V11', 'escalation.md', f'基準 {i} の節が無い'))
            elif '根拠：' not in scope:
                errors.append(('V11', 'escalation.md', f'基準 {i} の節に根拠が無い'))
    dt = os.path.join(REVIEW_DIR, 'decision_tree.md')
    if os.path.isfile(os.path.join(root, dt)):
        for a in re.findall(r'<a id="([^"]+)"></a>', trace_check._read(os.path.join(root, dt))):
            _, scope = trace_check._md_part(root, dt, a)
            if '根拠：' not in (scope or ''):
                errors.append(('V11', 'decision_tree.md', f'節 {a} に根拠が無い'))
    errors += check_links_and_forms(root, files)
    readme = os.path.join(root, REVIEW_DIR, 'README.md')
    if os.path.isfile(readme):
        m = re.search(r'<!-- counts:begin -->(.*?)<!-- counts:end -->', trace_check._read(readme), re.S)
        want = {name: sum(1 for q in questions if q['stage'] == sid) for sid, name in STAGES}
        want['計'] = len(questions)
        got = {k.strip(): int(v) for k, v in re.findall(r'^\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*$', m.group(1), re.M)} if m else {}
        if got != want:
            errors.append(('V12', 'templates/review/README.md', f'問いの数の表が違う。want {want}'))
    return errors, questions, files


LINK_RE = re.compile(r'''\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+["'(][^)]*)?\)'''   # [x](target "title")
                     r'''|^\s{0,3}\[[^\]]+\]:\s*<?([^\s>]+)>?'''                 # [ref]: target
                     r'''|<a\s[^>]*\bhref\s*=\s*["']([^"']+)["']''')            # <a href="target">
ANCHOR_ANY = re.compile(r'''<a\s+(?:[^>]*\s)?(?:id|name)\s*=\s*["']([^"']+)["']''')
BOLD_QID = re.compile(r'^\*\*(?:q|ap|pa|dc|cf|cd)-[^*]*\*\*')
BARE_REF = re.compile(r'(?<![`A-Za-z0-9_/:-])((?:template|registry|catalog|review|lint|test):[A-Za-z0-9_][A-Za-z0-9_./-]*(?:#[A-Za-z0-9_.-]+)?)')


def _unfenced(lines):
    fenced = False
    for k, line in enumerate(lines, 1):
        if line.startswith('```'):
            fenced = not fenced
            continue
        if not fenced:
            yield k, line


def check_links_and_forms(root, files):
    out = []
    anchors_of = {}
    for path in files:
        text = trace_check._read(path)
        ids = ANCHOR_ANY.findall(text)
        anchors_of[os.path.normpath(path)] = set(ids)
        rel = rel_of(root, path)
        for a in sorted({i for i in ids if ids.count(i) > 1}):
            out.append(('V13', rel, f'アンカー {a} が重複している'))
    for path in files:
        rel = rel_of(root, path)
        lines = trace_check._read(path).splitlines()
        is_persp = rel.endswith('templates/review/perspectives.md')
        for k, line in _unfenced(lines):
            for m in LINK_RE.finditer(line):
                target = m.group(1) or m.group(2) or m.group(3)
                if re.match(r'^[a-z]+:', target):
                    continue
                file_part, _, anchor = target.partition('#')
                tpath = os.path.normpath(os.path.join(os.path.dirname(path), file_part)) if file_part else os.path.normpath(path)
                if not os.path.exists(tpath):
                    out.append(('V13', f'{rel}:{k}', f'リンク先 {target} のファイルが無い'))
                    continue
                if anchor and tpath.endswith('.md'):
                    ids = anchors_of.get(tpath)
                    if ids is None:
                        ids = set(ANCHOR_ANY.findall(trace_check._read(tpath)))
                    if anchor not in ids:
                        out.append(('V13', f'{rel}:{k}', f'リンク先 {target} のアンカーが無い'))
            if is_persp:
                if BOLD_QID.match(line) and not Q_START.match(line):
                    out.append(('V13', f'{rel}:{k}', '問いの見出しの形が違う（ID の後は全角の空白）'))
                fm = FIELD_RE.match(line)
                if fm and fm.group(1) in ('見る欄', 'つながり'):
                    bare = BARE_REF.findall(re.sub(r'`[^`]*`', '', fm.group(2)))
                    for b in bare:
                        out.append(('V13', f'{rel}:{k}', f'{b} をバッククォートで囲む（囲まないと解決を確かめない）'))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--root', default=ROOT)
    ap.add_argument('--list', action='store_true', help='print the question IDs with their stage')
    ap.add_argument('--counts', action='store_true', help='print the number of questions per stage')
    a = ap.parse_args(argv)
    errors, questions, files = check(a.root)
    out = []
    if a.list:
        out += [f'{q["stage"] or "-"}\t{q["id"]}' for q in questions]
    if a.counts or not a.list:
        names = dict(STAGES)
        for sid, name in STAGES:
            out.append(f'{name}: {sum(1 for q in questions if q["stage"] == sid)}')
        out.append(f'questions: {len(questions)}  files: {len(files)}')
    if not a.list:
        out += [f'{r}  {w}  {m}' for r, w, m in errors]
        out.append(f'error {len(errors)}')
        out.append('FAIL' if errors else 'OK')
    sys.stdout.buffer.write(('\n'.join(out) + '\n').encode('utf-8'))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
