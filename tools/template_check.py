# -*- coding: utf-8 -*-
"""Check the design-doc templates (#4): stable item IDs, evidence on every item, blank fill-in columns.

  python tools/template_check.py [--root DIR] [--list]

Files: templates/README.md, GETTING_STARTED.md, glossary.md, 00_core.md, claim_request.md, templates/profiles/*.md and
templates/modules/*.md (the worked examples, the registry, the catalogue and the trace table are checked elsewhere).

Checks (all errors):
  T1  the first line is `<!-- template_version: X.Y.Z -->` (templates/CONTRIBUTING.md 4.)
  T2  every item is an anchor `<a id="..."></a>` (lower-case letters, digits, '-'), unique in its file, and the item
      section has the line `項目 ID：`template:<path>#<anchor>`` naming its own file and anchor (the stable ID that the
      review materials (#5) and the trace table (#22) refer to)
  T3  every item section has at least one `根拠：` line, and every element of it (separated by '、') has a known form:
      slide:<id> (the slide must exist, tools/check_slide_refs.py), RFC <n> §<section>, draft-...-<nn>, a versioned
      specification or product document, ASVS v<version>-<id>, NIST/OWASP/CSRB/CVE ids, a book with a page, a path in
      this repository, a casestudy result, or `筆者の提案：...（追跡 #<n>）` (an author proposal must name its tracking
      issue). The form is checked, not whether the source supports the item (that is the 10% sampled check of #13)
  T4  fill-in tables (a header cell containing `（書き手が書く）`) leave that column empty in the template: a template
      gives candidates and questions, never a sample adopt/reject rationale (#4 方針, research report Q6)
      T4 also checks the other columns of a fill-in table (the table right after a line that starts with 記入欄): only the
      first column (what to decide) and columns whose header names an ID (台帳・目録の ID) may hold text
  T5  every `template:` ref of templates/trace/planned_items.yaml resolves to a file, and to an anchor when it has one
  T6  every heading (##, ###, ####) of 00_core.md, claim_request.md, profiles/ and modules/ starts an item (an anchor in the
      two lines before it), or is marked `<!-- heading-only -->` (a heading that only groups items: its text belongs to
      the item above it)

Offline existence checks in T3 (tools/template_sources.yaml pins the lists):
  - slide:<id> exists in deck/slide_ids.json
  - RFC <n>: n is in the pinned list of RFCs (the section is not checked)
  - 筆者の提案：...（追跡 #n）: n is in the pinned list of tracking issues (whether that issue carries the proposal is not)
  - a path in this repository exists (the section after the path is not checked)
Not checked by machine: RFC and draft sections, versions and sections of other specifications and product documents,
guidance item numbers, book pages, casestudy commits and case IDs, and whether a source supports the item (the 10% sampled
check of templates/CONTRIBUTING.md 2.).

--list prints the item IDs (one per line) for the review materials (#5) and the trace table (#22).
"""
import argparse
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import check_slide_refs  # noqa: E402

VERSION_RE = re.compile(r'^<!-- template_version: \d+\.\d+\.\d+ -->$')
ANCHOR_RE = re.compile(r'<a id="([^"]*)"></a>')
ANCHOR_OK = re.compile(r'^[a-z0-9][a-z0-9-]*$')
ITEM_RE = re.compile(r'^項目 ID：`template:([A-Za-z0-9_/]+)#([a-z0-9-]+)`\s*$')
EVID_RE = re.compile(r'^\s*(?:[-*]\s+)?根拠：\s*(.+?)\s*$')
SLIDE_RE = re.compile(r'^slide:([a-z0-9][a-z0-9-]*)$')
# known forms of an evidence element (templates/CONTRIBUTING.md 1.); each needs a version or a section
FORMS = [
    ('slide', SLIDE_RE),
    ('rfc', re.compile(r'^RFC \d{3,5} §[0-9A-Z][0-9A-Za-z.]*(?:[・〜][0-9A-Za-z.§]+)*(?:（.*）)?$')),
    ('draft', re.compile(r'^draft-[a-z0-9-]+-\d{2}(?: §[0-9A-Za-z.]+(?:[・〜][0-9A-Za-z.§]+)*)?(?:（.*）)?$')),
    ('spec', re.compile(r'^(?:OpenID|FAPI|OAuth 2\.0|SCIM|MCP|SD-JWT|W3C|ISO|IANA|JSON Web|Shared Signals|CAEP|CloudEvents|SPIFFE|CIBA)'
                        r'.*(?:\d\.\d|\d{4}-\d{2}-\d{2}|§|registry|Final|（.+）).*$')),
    ('product', re.compile(r'^(?:Keycloak|Microsoft Entra|Entra ID|Okta|Auth0|Amazon Cognito|Cognito|PostgreSQL|SQL Server'
                           r'|PostgREST|Kafka|Envoy|nginx|Node\.js|AWS|Azure|Google Cloud|Spring|Supabase|Snowflake)'
                           r'.*(?:（[^）]*\d[^）]*）|\d+\.\d+).*$')),
    ('guidance', re.compile(r'^(?:ASVS v\d+\.\d+\.\d+-\d+(?:\.\d+)+'
                            r'|NIST (?:SP 800-\d+[A-Za-z0-9-]*|IR \d{4}) (?:§[\d.]+|REC-[A-Z]+-\d+)'
                            r'|OWASP (?:[A-Z][\w ]+ Cheat Sheet|API Security Top 10 \d{4} API\d+)'
                            r'|CSRB 報告書（[^）]+）勧告 \d+|デジタル庁 DS-\d+.*|CoSAI .+ v\d+(?:\.\d+)* §[\d.]+'
                            r'|個人情報の保護に関する法律（[^）]+）第\d+条.*|個人情報保護委員会「[^」]+」.*)$')),
    ('incident', re.compile(r'^CVE-\d{4}-\d{4,}$')),
    ('book', re.compile(r'^『[^』]+』（[^）]+）.*(?:p\.\s?\d+|節|章).*$')),
    ('research', re.compile(r'^[^「」]+「[^」]+」（[^）]*\d{4}[^）]*）.*$')),
    ('repo', re.compile(r'^(?:templates|research|tools|docs)/[^\s、]+(?: ?の.+)?$')),
    ('casestudy', re.compile(r'^jwt-claims-casestudy@[0-9a-f]{7,40}(?::[A-Za-z0-9_.-]+)?(?:（.*）)?$')),
    ('proposal', re.compile(r'^筆者の提案：.+（追跡 #\d+）$')),
]
FILL_MARK = '（書き手が書く）'


def template_files(root):
    base = os.path.join(root, 'templates')
    out = [os.path.join(base, n) for n in ('README.md', 'GETTING_STARTED.md', 'glossary.md', '00_core.md', 'claim_request.md')]
    for sub in ('profiles', 'modules'):
        d = os.path.join(base, sub)
        if os.path.isdir(d):
            out += sorted(os.path.join(d, n) for n in os.listdir(d) if n.endswith('.md'))
    return [p for p in out if os.path.isfile(p)]


def split_evidence(text):
    # split on '、' outside brackets （） 「」 『』
    out, depth, cur = [], 0, ''
    for ch in text:
        if ch in '（「『(':
            depth += 1
        elif ch in '）」』)':
            depth = max(0, depth - 1)
        if ch == '、' and depth == 0:
            out.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    # an author proposal may contain '、' in its summary: it runs until its （追跡 #n）
    merged = []
    for el in out:
        if merged and merged[-1].startswith('筆者の提案：') and not re.search(r'（追跡 #\d+）$', merged[-1]):
            merged[-1] += '、' + el
        else:
            merged.append(el)
    return merged


SOURCES = {'rfcs': {}, 'tracking_issues': {}}
ROOT_FOR_PATHS = [ROOT]


def load_sources(root):
    import yaml
    p = os.path.join(root, 'tools', 'template_sources.yaml')
    if os.path.isfile(p):
        data = yaml.safe_load(open(p, encoding='utf-8')) or {}
        SOURCES['rfcs'] = {int(k): v for k, v in (data.get('rfcs') or {}).items()}
        SOURCES['tracking_issues'] = {int(k): v for k, v in (data.get('tracking_issues') or {}).items()}
    ROOT_FOR_PATHS[0] = root


def evidence_form(el, slides):
    el = el.strip().strip('`')
    for name, rx in FORMS:
        m = rx.match(el)
        if m:
            if name == 'slide' and m.group(1) not in slides:
                return None, f'slide:{m.group(1)} は実在しないスライド'
            if name == 'rfc' and SOURCES['rfcs']:
                n = int(re.match(r'^RFC (\d+)', el).group(1))
                if n not in SOURCES['rfcs']:
                    return None, f'RFC {n} は tools/template_sources.yaml の rfcs に無い（開いて確かめてから足す）'
            if name == 'proposal' and SOURCES['tracking_issues']:
                n = int(re.search(r'（追跡 #(\d+)）$', el).group(1))
                if n not in SOURCES['tracking_issues']:
                    return None, f'追跡 #{n} は tools/template_sources.yaml の tracking_issues に無い'
            if name == 'repo':
                path = re.match(r'^([^\s、]+?)(?: ?の.*)?$', el).group(1)
                if not os.path.exists(os.path.join(ROOT_FOR_PATHS[0], path)):
                    return None, f'{path} は存在しないパス'
            return name, None
    return None, f'根拠の形が分からない：{el}'


def table_rows(lines, start):
    """Rows (lists of cells) of the Markdown table whose header is lines[start]."""
    rows = []
    for line in lines[start:]:
        s = line.strip()
        if not s.startswith('|'):
            break
        rows.append([c.strip() for c in s.strip('|').split('|')])
    return rows


def check_file(path, root, slides):
    rel = os.path.relpath(path, os.path.join(root, 'templates')).replace(os.sep, '/')
    tpath = rel[:-3]
    text = open(path, encoding='utf-8').read()
    lines = text.splitlines()
    out, items = [], []
    if not lines or not VERSION_RE.match(lines[0]):
        out.append(('T1', rel, '1 行目が <!-- template_version: X.Y.Z --> でない'))
    marks = [(k, m.group(1)) for k, l in enumerate(lines) for m in ANCHOR_RE.finditer(l)]
    seen = set()
    for j, (k, anchor) in enumerate(marks):
        end = marks[j + 1][0] if j + 1 < len(marks) else len(lines)
        sec = lines[k:end]
        where = f'{rel}#{anchor}'
        if not ANCHOR_OK.match(anchor):
            out.append(('T2', where, 'アンカーは英小文字・数字・- で書く'))
        if anchor in seen:
            out.append(('T2', where, 'アンカーが重複している'))
        seen.add(anchor)
        ids = [ITEM_RE.match(l) for l in sec]
        ids = [m for m in ids if m]
        if not ids:
            out.append(('T2', where, f'「項目 ID：`template:{tpath}#{anchor}`」の行がない'))
        elif (ids[0].group(1), ids[0].group(2)) != (tpath, anchor):
            out.append(('T2', where, f'項目 ID が template:{ids[0].group(1)}#{ids[0].group(2)} で、ファイルとアンカーに合わない'))
        items.append(f'template:{tpath}#{anchor}')
        evid = [m.group(1) for m in (EVID_RE.match(l) for l in sec) if m]
        if not evid:
            out.append(('T3', where, '「根拠：」の行がない'))
        for e in evid:
            for el in split_evidence(e):
                _, err = evidence_form(el, slides)
                if err:
                    out.append(('T3', where, err))
    in_items = rel in ('00_core.md', 'claim_request.md') or rel.startswith(('profiles/', 'modules/'))
    for k, line in enumerate(lines):
        if in_items and re.match(r'^#{2,4} ', line):
            prev = [x for x in lines[max(0, k - 2):k] if x.strip()]
            if not any(ANCHOR_RE.search(x) or '<!-- heading-only -->' in x for x in prev):
                out.append(('T6', f'{rel}:{k + 1}', f'見出し「{line.strip()[:40]}」の前にアンカーが無い（項目にするか <!-- heading-only --> を付ける）'))
        if line.strip().startswith('記入欄'):
            j = k + 1
            while j < len(lines) and not lines[j].strip().startswith('|'):
                if lines[j].strip() and not lines[j].strip().startswith('<!--'):
                    break
                j += 1
            rows = table_rows(lines, j) if j < len(lines) and lines[j].strip().startswith('|') else []
            if len(rows) >= 2:
                for r in rows[2:]:
                    for c, h in enumerate(rows[0]):
                        if c == 0 or FILL_MARK in h or 'ID' in h:
                            continue
                        if c < len(r) and r[c]:
                            out.append(('T4', f'{rel}:{j + 1}', f'記入欄の「{h}」に値がある（{r[c][:30]}）。最初の列と ID の列のほかは空にする'))
        if line.strip().startswith('|') and FILL_MARK in line:
            rows = table_rows(lines, k)
            if len(rows) < 2:
                continue
            cols = [c for c, h in enumerate(rows[0]) if FILL_MARK in h]
            for r in rows[2:]:
                for c in cols:
                    if c < len(r) and r[c]:
                        out.append(('T4', f'{rel}:{k + 1}', f'記入欄の「{rows[0][c]}」に値がある（{r[c][:30]}）。テンプレートには採否と理由の見本を書かない'))
    return out, items


def check_planned(root, files):
    import yaml
    have = {}
    for p in files:
        rel = os.path.relpath(p, os.path.join(root, 'templates')).replace(os.sep, '/')[:-3]
        have[rel] = set(ANCHOR_RE.findall(open(p, encoding='utf-8').read()))
    data = yaml.safe_load(open(os.path.join(root, 'templates', 'trace', 'planned_items.yaml'), encoding='utf-8'))
    out = []
    for it in data.get('items') or []:
        ref = str(it.get('ref', ''))
        if not ref.startswith('template:') or it.get('issue') != '#4':
            continue
        path, _, anchor = ref[len('template:'):].partition('#')
        if path not in have:
            out.append(('T5', ref, f'templates/{path}.md がない'))
        elif anchor and anchor not in have[path]:
            out.append(('T5', ref, f'templates/{path}.md にアンカー {anchor} がない'))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--root', default=ROOT)
    ap.add_argument('--list', action='store_true', help='print the item IDs')
    ap.add_argument('--no-planned', action='store_true', help='skip T5 (planned items of #4 resolve)')
    a = ap.parse_args(argv)
    slides = {s['id'] for s in check_slide_refs.load_json(os.path.join(a.root, 'deck', 'slide_ids.json'), [])}
    load_sources(a.root)
    files = template_files(a.root)
    findings, items = [], []
    for p in files:
        f, i = check_file(p, a.root, slides)
        findings += f
        items += i
    if not a.no_planned:
        findings += check_planned(a.root, files)
    if a.list:
        sys.stdout.buffer.write(('\n'.join(items) + '\n').encode('utf-8'))
        return 0
    lines = [f'template_check  files={len(files)}  items={len(items)}']
    lines += [f'{r}  {w}  {m}' for r, w, m in findings]
    lines.append(f'error {len(findings)}')
    lines.append('FAIL' if findings else 'OK')
    sys.stdout.buffer.write(('\n'.join(lines) + '\n').encode('utf-8'))
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
