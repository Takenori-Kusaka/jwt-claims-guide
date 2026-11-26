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
      marked `（未実装）` right after it; `test:` is a planned item marked `（未実装）` until templates/runtime/ exists;
      after that (#8) it resolves to an anchor of templates/runtime/<file>.md, or it is a planned item not made yet and
      marked `（未実装）` (a test that resolves must not be marked)
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
  V14 templates/review/triage.yaml (#56) gives every question a class (A machine / B author self-check / C human
      judgement / D expert) with a reason; the lint rules cited for class A exist in RULES.md, proposed rules are planned
      items or N<n> entries; the 区分 line of every question, short_list.md and the PR template for design docs are
      what tools/review_triage.py makes from it (T1-T9 there)
  V12 the table between `<!-- counts:begin -->` and `<!-- counts:end -->` of templates/review/README.md equals the number
      of questions per stage (and the total)

Not checked by machine: whether a question is the right question, whether a field really answers it, whether a source
supports a claim (the 10% sampled check of templates/CONTRIBUTING.md 2.).

--report FILE (repeatable) also checks a review report against the form of report_template.md (RP1-RP10 of
check_report: sections, items of 1., table headers, the vocabulary of findings, the confused question of 目的と仕組みの
不一致, the answers of 8.). The review mode of the editor (#50) writes reports in this form.

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
FIELD_RE = re.compile(r'^- (見る欄|No なら|つながり|根拠|区分)：\s*(.*)$')
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
                if kind == 'test' and os.path.isdir(os.path.join(root, 'templates', 'runtime')):
                    # #8: like lint, a planned test not made yet is written （未実装）; a made one must not be
                    problem = resolve(root, ref, planned)
                    if problem:
                        if ref in planned and unimpl:
                            continue
                        errors.append(('V6', f'{rel}:{k}', problem + ('（計画にあるなら「（未実装）」と書く）' if ref in planned else '（計画にも無い）')))
                    elif unimpl:
                        errors.append(('V6', f'{rel}:{k}', f'{ref} は実装済みなのに「（未実装）」と書いている'))
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
    # V14 the triage of the questions (#56): templates/review/triage.yaml classifies every question, the lint rules it
    # cites exist, and the files generated from it (the 区分 lines here, short_list.md, the PR template) match
    import review_triage
    # (the generated files are compared only when nothing else is wrong: a broken question would show up twice)
    errors += [('V14', w, f'{r} {m}') for r, w, m in review_triage.check(root, questions, generated_files=not errors)]
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


ROLE_IDS = [('role-issuer', '発行者'), ('role-consumer', '受け手'), ('role-attacker', '攻撃者'), ('role-operations', '運用'),
            ('role-privacy', '個人情報'), ('role-client', 'クライアントの実装')]
QID_RANGE = re.compile(r'`((?:q|ap|pa|dc|cf|cd)-(?:[a-z]+-)?)(\d+)`〜`\1(\d+)`')


def _section(text, anchor):
    """The lines after <a id="anchor"></a> up to the next anchor line, a `---` rule or a second ## heading."""
    out, on, heads = [], False, 0
    for line in text.splitlines():
        am = ANCHOR_LINE.match(line.strip())
        if am:
            if on:
                break
            on = am.group(1) == anchor
            continue
        if not on:
            continue
        if line.startswith('## '):
            heads += 1
        if line.strip() == '---' or heads > 1:
            break
        out.append(line)
    return '\n'.join(out)


def _qids(text, known):
    """Question IDs quoted in text, with ranges such as `pa-01`〜`pa-25` expanded to the IDs that exist."""
    ids = []
    for m in QID_RANGE.finditer(text):
        pre, a, b = m.group(1), int(m.group(2)), int(m.group(3))
        ids += [f'{pre}{n:0{len(m.group(2))}d}' for n in range(a, b + 1)]
    ids += QID_IN_TICKS.findall(text)
    out = []
    for i in ids:
        if i in known and i not in out:
            out.append(i)
    return out


def roles_and_stages(text, questions):
    """The role index of perspectives.md 7. ([{id, name, title, lead, questions}]) and the heads of the stages 1.-6.
    ([{id, name, title, who}]). A question belongs to a role when the table of the role quotes it (ranges expanded)."""
    known = {q['id'] for q in questions}
    lines = text.splitlines()
    heading = {}
    for k, line in enumerate(lines):
        am = ANCHOR_LINE.match(line.strip())
        if am:
            nxt = next((x for x in lines[k + 1:k + 4] if x.startswith('#')), None)
            if nxt:
                heading[am.group(1)] = nxt.lstrip('#').strip()
    roles = []
    for rid, name in ROLE_IDS:
        sec = _section(text, rid).splitlines()
        lead = next((x.strip() for x in sec if x.strip().startswith('「')), '')
        roles.append({'id': rid, 'name': name, 'title': heading.get(rid, name), 'lead': lead,
                      'questions': _qids('\n'.join(x for x in sec if x.startswith('|')), known)})
    stages = []
    for sid, name in STAGES:
        sec = _section(text, sid).splitlines()
        who = next((x.strip() for x in sec if x.startswith('**誰が確かめるか**')), '')
        stages.append({'id': sid, 'name': name, 'title': heading.get(sid, name), 'who': re.sub(r'^\*\*誰が確かめるか\*\*：', '', who)})
    return roles, stages


# ------------------------------------------------------------------ the form of a review report (#50)
REPORT_FORM = os.path.join(REVIEW_DIR, 'report_template.md')
ANSWER_WORDS = ('Yes', 'No', '該当なし')
RR_WORDS = ('満', '否', '対象外')
PASS_WORDS = ('合格', '不合格')
EMPTY = ('', '—', '-')


def report_form(root):
    """The form of report_template.md (the fenced block after <a id="form">): the ## headings, the table header under
    each, the items of 1., and the vocabulary (origins, kinds, severities, verdicts, states)."""
    text = trace_check._read(os.path.join(root, REPORT_FORM))
    block = re.search(r'<a id="form"></a>.*?```markdown\n(.*?)\n```', text, re.S).group(1)
    sections, cur = [], None
    for line in block.splitlines():
        if line.startswith('## '):
            cur = {'heading': line[3:].strip(), 'header': None, 'items': []}
            sections.append(cur)
        elif cur is not None and line.startswith('|'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if cur['header'] is None:
                cur['header'] = cells
            elif not set(''.join(cells)) <= set('-: ') and cells[0]:
                cur['items'].append(cells[0])

    def first_column(anchor):
        part = text.split(f'<a id="{anchor}"></a>', 1)[1].split('<a id=', 1)[0]
        rows = [[c.strip() for c in x.strip().strip('|').split('|')] for x in part.splitlines() if x.startswith('|')]
        return [r[0] for r in rows[2:]]
    sev = text.split('<a id="severities"></a>', 1)[1].split('<a id=', 1)[0]

    def words(label):
        line = next(x for x in sev.splitlines() if x.startswith(f'- {label}：'))
        return [re.sub(r'（.*', '', w).strip() for w in line.split('：', 1)[1].split('／')]
    return {'sections': sections, 'origins': first_column('origins'), 'kinds': first_column('kinds'),
            'severities': words('重大度'), 'verdicts': words('判定'), 'states': words('対応の状態')}


def _tables(lines):
    """[(header cells, [row cells])] of the Markdown tables in lines."""
    out, cur = [], None
    for line in lines:
        if line.startswith('|'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if cur is None:
                cur = (cells, [])
                out.append(cur)
            elif not set(''.join(cells)) <= set('-: '):
                cur[1].append(cells)
        else:
            cur = None
    return out


def check_report(root, text, questions=None):
    """Problems of a review report against the form of report_template.md: [(rule, where, message)].

    RP1 the title; RP2 the ## sections 1.-8. in order (more sections may follow); RP3 the items of 1., each with a value;
    RP4 the table header of each section; RP5 the findings of 2.: unique IDs, the vocabulary of severity, origin, kind and
    verdict, and the confused question exactly when the kind is 目的と仕組みの不一致; RP6 3. names findings of 2. and a
    state of the vocabulary; RP7 4. has the line 当てはまらなかった基準; RP8 6. scores RR1-RR7 with 満・否・対象外 and
    合格・不合格; RP9 7. is not empty; RP10 8. answers questions of perspectives.md, each at most once, with Yes・No・該当なし."""
    form = report_form(root)
    if questions is None:
        questions = parse_questions(trace_check._read(os.path.join(root, REVIEW_DIR, 'perspectives.md')))
    qids = {q['id'] for q in questions}
    errs = []
    lines = text.replace('\r\n', '\n').split('\n')
    first = next((x for x in lines if x.startswith('# ')), '')
    if not re.match(r'^# レビューレポート：.+', first):
        errs.append(('RP1', 'title', '最初の見出しが「# レビューレポート：<設計書の名前>」でない'))
    heads = [(k, x[3:].strip()) for k, x in enumerate(lines) if x.startswith('## ')]
    want = [s['heading'] for s in form['sections']]
    if [h for _, h in heads][:len(want)] != want:
        errs.append(('RP2', 'sections', f'## の節が様式と違う（様式：{want}／実際：{[h for _, h in heads]}）'))
        return errs
    body = {}
    for i, (k, hd) in enumerate(heads):
        body[hd] = lines[k + 1:heads[i + 1][0] if i + 1 < len(heads) else len(lines)]
    rows = {}
    for s in form['sections']:
        key = s['heading'][:2]
        if s['header'] is None:
            if not any(x.strip() for x in body[s['heading']]):
                errs.append(('RP9', s['heading'], '空'))
            continue
        tabs = _tables(body[s['heading']])
        if not tabs:
            errs.append(('RP4', s['heading'], '表が無い'))
            continue
        for hdr, _ in tabs:
            if hdr != s['header']:
                errs.append(('RP4', s['heading'], f'表の見出しが様式と違う（様式：{s["header"]}／実際：{hdr}）'))
        rows[key] = [r for _, rs in tabs for r in rs if any(r)]
    if errs:
        return errs
    items = next(s['items'] for s in form['sections'] if s['heading'].startswith('1.'))
    if [r[0] for r in rows['1.']] != items:
        errs.append(('RP3', '1.', f'項目が様式と違う（様式：{items}／実際：{[r[0] for r in rows["1."]]}）'))
    for r in rows['1.']:
        if len(r) < 2 or r[1] in EMPTY:
            errs.append(('RP3', '1.', f'{r[0]} の値が空'))
    ids = []
    for r in rows['2.']:
        if len(r) != 8:
            errs.append(('RP5', '2.', f'列の数が 8 でない：{r}'))
            continue
        fid, _, content, sev_, origin, kind, confused, verdict = r
        where = f'2. {fid}'
        if not fid or fid in ids:
            errs.append(('RP5', where, 'ID が空か重複している'))
        ids.append(fid)
        if content in EMPTY:
            errs.append(('RP5', where, '内容が空'))
        for val, vocab, label in ((sev_, form['severities'], '重大度'), (origin, form['origins'], '出どころ'),
                                  (kind, form['kinds'], '種別'), (verdict, form['verdicts'], '判定')):
            if val not in vocab:
                errs.append(('RP5', where, f'{label}「{val}」が語彙（{"・".join(vocab)}）に無い'))
        mismatch = kind == '目的と仕組みの不一致'
        if mismatch and confused in EMPTY:
            errs.append(('RP5', where, '種別が目的と仕組みの不一致なのに、取り違えた問いが無い'))
        if not mismatch and confused not in EMPTY:
            errs.append(('RP5', where, '取り違えた問いは、種別が目的と仕組みの不一致のときだけ書く'))
    for r in rows['3.']:
        if r[0] not in ids:
            errs.append(('RP6', f'3. {r[0]}', '2. に無い指摘 ID'))
        if len(r) < 4 or r[3] not in form['states']:
            errs.append(('RP6', f'3. {r[0]}', f'状態が語彙（{"・".join(form["states"])}）に無い'))
    h4 = next(s['heading'] for s in form['sections'] if s['heading'].startswith('4.'))
    if not any(x.startswith('当てはまらなかった基準：') for x in body[h4]):
        errs.append(('RP7', '4.', '「当てはまらなかった基準：」の行が無い'))
    for r in rows['6.']:
        for v in r[2:9]:
            if v not in RR_WORDS:
                errs.append(('RP8', f'6. {r[0]}', f'採点「{v}」が {"・".join(RR_WORDS)} でない'))
        if len(r) < 10 or r[9] not in PASS_WORDS:
            errs.append(('RP8', f'6. {r[0]}', f'合否が {"・".join(PASS_WORDS)} でない'))
    seen = set()
    for r in rows['8.']:
        q = r[1].strip('`') if len(r) > 1 else ''
        if q not in qids:
            errs.append(('RP10', f'8. {q}', '観点書に無い問い ID'))
        if q in seen:
            errs.append(('RP10', f'8. {q}', '問いの回答が重複している'))
        seen.add(q)
        if len(r) < 3 or r[2] not in ANSWER_WORDS:
            errs.append(('RP10', f'8. {q}', f'回答が {"・".join(ANSWER_WORDS)} でない'))
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--root', default=ROOT)
    ap.add_argument('--report', action='append', default=[], metavar='FILE',
                    help='also check that a review report follows the form of report_template.md (RP1-RP10)')
    ap.add_argument('--list', action='store_true', help='print the question IDs with their stage')
    ap.add_argument('--counts', action='store_true', help='print the number of questions per stage')
    a = ap.parse_args(argv)
    errors, questions, files = check(a.root)
    for rp in a.report:
        with open(rp, encoding='utf-8') as f:
            errors += [(r, f'{rp}: {w}', m) for r, w, m in check_report(a.root, f.read(), questions)]
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
