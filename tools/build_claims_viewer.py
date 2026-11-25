# -*- coding: utf-8 -*-
"""Build the data of the design-document editor (#49; was the viewer of #36, GitHub Pages: docs/claims/).

  python tools/build_claims_viewer.py            # write docs/claims/data/* and docs/claims/vendor/MANIFEST.json
  python tools/build_claims_viewer.py --check    # exit 1 when they differ from the YAML and the vendored files (CI)

The editor is static HTML and JS (docs/claims/index.html, editor.js, preview.js, lint-worker.js). It opens empty; the
data below are loaded with <script src> from the same directory only when they are needed (the samples when the reader
asks for one). claim_lint runs in the browser with Pyodide (docs/claims/vendor/pyodide/), reading its sources from
data/claim_lint.zip; the page CSP allows connections to its own origin only (connect-src 'self').

Files written (docs/claims/data/):
  meta.js          column headings of the registry (templates/registry/README.md 3.1-3.4, checked against the
                   *.schema.json properties), review questions that look at each column (templates/review/),
                   questions, event and token-kind names, slide titles (docs/slide_ids.csv), the list of samples
  trace.js         tier x status counts of the trace table (templates/trace/requirements.yaml, #22)
  schemas.js       the registry JSON Schemas (templates/registry/*.schema.json) for the in-browser schema check, and
                   templates/review/review.schema.json (review.yaml, #50)
  review.js        the review mode (#50): the 168 questions of templates/review/perspectives.md with stage, roles (the
                   index 7.), 見る欄 / No なら / つながり / 根拠 and their refs; the stages and roles; the headings that
                   見る欄 points at; contrasts, decision tree, escalation criteria, rubric; the form of report_template.md
  skeleton.js      the files of python tools/new_design.py (an empty design), for 「空の雛形から始める」
  sample-<x>.js    the files of each worked example (YAML, claim_request_*.md, design.md), for 「サンプルを開く」
  claim_lint.zip   tools/claim_lint and the files it reads (catalogue, registry, slide IDs), unpacked into Pyodide's
                   file system (stored, not deflated: the bytes do not depend on the zlib version)
and docs/claims/vendor/MANIFEST.json: version, license, source and sha256 of every vendored file, with the
vulnerability check of tools/claims_editor_vendor/advisories.json.
Also (#53, cache busting): data/build.js (the build id and the content hashes of the files loaded after the start),
the ?v=<hash> of every <script> and <link> of index.html, and the build id line of editor.js, preview.js, review.js,
lint-worker.js and app.css. --check reports a missing or stale hash, a stale build id, and a load that skips asset().
"""
import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import zipfile
from collections import Counter, OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, 'tools')
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import yaml  # noqa: E402
from claim_lint import render  # noqa: E402
import review_check  # noqa: E402

OUT_DIR = os.path.join(ROOT, 'docs', 'claims', 'data')
VENDOR_DIR = os.path.join(ROOT, 'docs', 'claims', 'vendor')
DATASETS = [  # (id, design dir, label, claim_lint profile of the design)
    ('scenario-a', 'templates/examples/scenario-a', 'シナリオ A（マルチテナント SaaS、Lite）', 'lite'),
    ('scenario-b', 'templates/examples/scenario-b', 'シナリオ B（社内の業務システムと AI エージェント、Full）', 'full'),
]
DESIGN_FILES = ('claims.yaml', 'token_types.yaml', 'hops.yaml', 'catalog_answers.yaml')
# the files claim_lint reads besides the design (found with an audit hook on open() while linting and rendering
# scenarios A and B; whole directories are taken so that a new catalogue file needs no change here)
LINT_FILES = [('tools/claim_lint', r'.+\.(py|yaml)$'), ('tools', r'^(catalog_check|check_slide_refs)\.py$'),
              ('templates/registry', r'.+\.(json|yaml)$'), ('templates/catalog', r'.+\.(yaml|md)$'),
              ('deck', r'^slide_ids\.json$')]
SKELETON_DIR = 'my-design'  # the directory name the skeleton is made for ($schema comments: ../templates/registry/...)
README = 'templates/registry/README.md'
# README section -> (key in meta.columns, schema file, JSON pointer of the object whose properties are the columns)
COLUMN_SECTIONS = [
    ('### 3.1 ', 'claims', 'templates/registry/claims.schema.json', ('$defs', 'claim')),
    ('### 3.2 ', 'token_types', 'templates/registry/token_types.schema.json', ('$defs', 'token_type')),
    ('### 3.3 ', 'issuance_profile', 'templates/registry/token_types.schema.json', ('$defs', 'issuance_profile')),
    ('### 3.4 ', 'hops', 'templates/registry/hops.schema.json', ('$defs', 'hop')),
]
# The claim detail screen (#67) shows a claim as an entity page of a data catalogue: six fields on top, the other
# columns in tabs. Which column of claims.schema.json ($defs.claim) is in which tab is this table; a column it does not
# name goes to the last tab (そのほか), a name that is not a column of the schema stops the build.
CLAIM_TABS = [
    ('overview', '概要', ['id', 'name', 'namespace', 'description', 'not_meaning', 'absent_semantics', 'usage', 'answers',
                         'does_not_answer', 'registered_ref', 'catalog_refs', 'catalog_refs_reason', 'flat_alias', 'paired_id']),
    ('value', '値と型', ['type', 'shape', 'allowed_values', 'value_vocabulary', 'composite_format', 'value_normalization',
                        'max_bytes', 'max_items', 'typical_items', 'overflow_strategy', 'path', 'mandatory', 'sd', 'display']),
    ('issue', '発行と元データ', ['issuers', 'upstream_issuer', 'authoritative_writer', 'modifiers', 'provenance', 'issue_events',
                              'carried_in', 'source_system', 'verification_method', 'last_verified', 'source_max_length']),
    ('lifetime', '有効期間と更新', ['volatility', 'recompute_trigger', 'propagation_delay', 'on_revoke', 'status', 'sunset_on']),
    ('protect', '保護', ['confidential_from', 'confidentiality_measure', 'integrity_until', 'pii_category', 'data_category',
                        'identifier_properties', 'recipients_external', 'cross_border', 'log_policy']),
    ('consume', '使う側', ['consumers', 'consumer_access_path', 'consumers_migration', 'on_missing', 'enforced_at']),
    ('history', '経緯', ['decision', 'rejection_kind', 'alt', 'rationale', 'assumption', 'revisit_trigger', 'refs',
                        'prior_art_search', 'owner', 'change_controller', 'evidence', 'asvs_ids', 'spec_version', 'note']),
    ('other', 'そのほか', []),
]
# the six fields on top of the claim detail screen: (label on screen, the columns it is made of)
CLAIM_HEAD = [('名前', ['id', 'name', 'namespace']), ('意味', ['description']), ('型', ['type', 'shape']), ('発行元', ['issuers']),
              ('入るトークン', ['carried_in']), ('状態', ['decision', 'status'])]
ROW_RE = re.compile(r'^\|\s*`([a-z_]+)`\s*\|')
REGISTRY_REF_RE = re.compile(r'`registry:(claims|token_types|hops)#([a-z_]+)`')
REPO_BLOB = 'https://github.com/Takenori-Kusaka/jwt-claims-guide/blob/main/'
CHECK_HINT = 'run: python tools/build_claims_viewer.py'


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read().replace('\r\n', '\n')


def _cells(line):
    return [c.strip() for c in line.strip().strip('|').split('|')]


def readme_columns():
    """Column tables of templates/registry/README.md 3.1-3.4: {section: [{key, label, group, meaning, lite}]}."""
    lines = _read(README).split('\n')
    out, cur, group = {}, None, None
    for line in lines:
        if line.startswith('## ') and not line.startswith('## 3.'):
            cur = None
        if line.startswith('### '):
            cur = next((k for p, k, _, _ in COLUMN_SECTIONS if line.startswith(p)), None)
            group = None
            if cur:
                out[cur] = []
            continue
        if cur is None:
            continue
        if line.startswith('#### '):
            group = line[5:].strip()
            continue
        if group and group.startswith('最上位の項目'):
            continue  # top-level keys of claims.yaml, not row columns
        m = ROW_RE.match(line)
        if not m:
            continue
        cells = _cells(line)
        if cells[1].startswith('---') or cells[0] == '列':
            continue
        out[cur].append({'key': m.group(1), 'label': cells[1], 'group': group, 'meaning': cells[2],
                         'lite': cells[-1]})
    return out


def schema_properties(rel, pointer):
    """Properties of the object at pointer, and for each the property names of its nested object (or array items)."""
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        node = json.load(f)
    for p in pointer:
        node = node[p]
    nested = {}
    for name, sub in node['properties'].items():
        sub = sub.get('items', sub)
        nested[name] = list(sub.get('properties', {}))
    return list(node['properties']), nested


def columns():
    """README headings in schema order; every schema property must have a heading (and no heading may be unknown).

    A heading of a field inside a column (authoritative_writer[].stage) is kept as `parts` of that column."""
    heads, problems, out = readme_columns(), [], OrderedDict()
    for _, key, rel, pointer in COLUMN_SECTIONS:
        props, nested = schema_properties(rel, pointer)
        by_key = {c['key']: c for c in heads.get(key, [])}
        for p in props:
            if p not in by_key:
                problems.append(f'{README}: {key}.{p} (a property of {rel}) has no row in the column table')
        cols = [dict(by_key[p]) for p in props if p in by_key]
        for k, c in by_key.items():
            if k in props:
                continue
            parent = next((x for x in cols if k in nested.get(x['key'], [])), None)
            if parent is None:
                problems.append(f'{README}: {key}.{k} is in the column table but not a property of {rel}')
            else:
                parent.setdefault('parts', []).append(c)
        out[key] = cols
    return out, problems


def claim_tabs(props=None, tabs=None):
    """meta.claim_tabs: [{id, label, columns}] in the order of CLAIM_TABS; every property of $defs.claim is in exactly one
    tab (the ones CLAIM_TABS does not name are added to the last tab, in schema order)."""
    if props is None:
        props, _ = schema_properties(*[(rel, pointer) for _, key, rel, pointer in COLUMN_SECTIONS if key == 'claims'][0])
    tabs = CLAIM_TABS if tabs is None else tabs
    problems, seen = [], {}
    for tid, _, cols in tabs:
        for c in cols:
            if c not in props:
                problems.append(f'CLAIM_TABS: {tid}.{c} is not a property of $defs.claim of claims.schema.json')
            if c in seen:
                problems.append(f'CLAIM_TABS: {c} is in two tabs ({seen[c]} and {tid})')
            seen[c] = tid
    for _, cols in CLAIM_HEAD:
        for c in cols:
            if c not in props:
                problems.append(f'CLAIM_HEAD: {c} is not a property of $defs.claim of claims.schema.json')
    if len({t[0] for t in tabs}) != len(tabs):
        problems.append('CLAIM_TABS: a tab id is written twice')
    if problems:
        raise SystemExit('build_claims_viewer: ' + '\n  '.join(['the tabs of the claim detail screen do not match the schema:'] + problems))
    out = [{'id': tid, 'label': label, 'columns': list(cols)} for tid, label, cols in tabs]
    out[-1]['columns'] += [p for p in props if p not in seen]
    return out


def review_links():
    """{'claims.usage': [{id, text, file, url}], ...}: review questions whose 見る欄 names a registry column."""
    out = {}
    for path in review_check.review_files(ROOT):
        rel = review_check.rel_of(ROOT, path)
        with open(path, encoding='utf-8') as f:
            text = f.read().replace('\r\n', '\n')
        for q in review_check.parse_questions(text):
            field = q['fields'].get('見る欄', '')
            url = REPO_BLOB + rel + (f"#{q['anchor']}" if q['anchor'] else f"?plain=1#L{q['line']}")
            for coll, col in REGISTRY_REF_RE.findall(field):
                lst = out.setdefault(f'{coll}.{col}', [])
                if not any(x['id'] == q['id'] for x in lst):
                    lst.append({'id': q['id'], 'text': q['text'], 'file': rel, 'url': url})
    return dict(sorted(out.items()))


REF_TICK = re.compile(r'`((?:review|template|registry|catalog|lint|test):[A-Za-z0-9_][A-Za-z0-9_./-]*(?:#[A-Za-z0-9_][A-Za-z0-9_.-]*)?)`')
HEAD_RE = re.compile(r'^(#{1,6})\s+(.*)$')
NUM_RE = re.compile(r'^(\d+(?:\.\d+)*\.?|[A-Z]\.)\s+')  # 1. / 3.2 / A.


def _md_heads(rel):
    """{anchor: {level, number, title}} of the <a id> anchors of a Markdown file (the heading right after each)."""
    lines = _read(rel).split('\n')
    out = {}
    for k, line in enumerate(lines):
        m = re.match(r'^<a id="([^"]+)"></a>\s*$', line.strip())
        if not m:
            continue
        nxt = next((x for x in lines[k + 1:k + 4] if HEAD_RE.match(x)), None)
        if not nxt:
            out[m.group(1)] = {'level': 0, 'number': '', 'title': ''}
            continue
        hm = HEAD_RE.match(nxt)
        title = re.sub(r'〔[^〕]*〕', '', hm.group(2)).strip()
        num = NUM_RE.match(title)
        out[m.group(1)] = {'level': len(hm.group(1)), 'number': num.group(1) if num else '',
                           'title': title[num.end():].strip() if num else title}
    return out


def _ref(r):
    kind, rest = r.split(':', 1)
    path, _, anchor = rest.partition('#')
    return {'ref': r, 'kind': kind, 'path': path, 'anchor': anchor}


def review_bundle():
    """data/review.js: the 168 questions of templates/review/perspectives.md (stage, roles of the index 7., the four
    fields, the refs of 見る欄 and つながり), the stages and roles, the headings that 見る欄 points at, the other review
    materials (contrasts, decision tree, escalation criteria, rubric) and the form of report_template.md (#50)."""
    persp_rel = 'templates/review/perspectives.md'
    text = _read(persp_rel)
    questions = review_check.parse_questions(text)
    roles, stages = review_check.roles_and_stages(text, questions)
    role_of = {}
    for r in roles:
        for q in r['questions']:
            role_of.setdefault(q, []).append(r['id'])
    version = re.match(r'<!-- template_version: ([0-9.]+) -->', text).group(1)
    heads = {}

    def head_of(r):
        if r['kind'] != 'template' or r['ref'] in heads:
            return
        rel = 'templates/' + r['path'] + '.md'
        if os.path.isfile(os.path.join(ROOT, rel)):
            h = _md_heads(rel).get(r['anchor']) if r['anchor'] else {'level': 1, 'number': '', 'title': ''}
            heads[r['ref']] = dict(h or {'level': 0, 'number': '', 'title': ''}, file=rel)
    qs = []
    for q in questions:
        see = [_ref(m) for m in REF_TICK.findall(q['fields'].get('見る欄', ''))]
        links = [_ref(m) for m in REF_TICK.findall(q['fields'].get('つながり', ''))]
        for r in see:
            head_of(r)
        qs.append({'id': q['id'], 'stage': q['stage'], 'text': q['text'], 'roles': role_of.get(q['id'], []),
                   'see': q['fields'].get('見る欄', ''), 'no': q['fields'].get('No なら', ''),
                   'links': q['fields'].get('つながり', ''), 'evidence': q['fields'].get('根拠', ''),
                   'see_refs': see, 'link_refs': links,
                   # how the question is shown by default (#53, for #56): a field 「トリアージ」 of the question, else all
                   'triage': q['fields'].get('トリアージ', '').strip() or 'all',
                   'url': REPO_BLOB + persp_rel + (f"#{q['anchor']}" if q['anchor'] else f"?plain=1#L{q['line']}")})
    contrasts = []
    for path in review_check.review_files(ROOT):
        rel = review_check.rel_of(ROOT, path)
        if '/contrasts/' in rel:
            title = next(x for x in _read(rel).split('\n') if x.startswith('# '))[2:].replace('対比表：', '').strip()
            contrasts.append({'file': rel, 'name': os.path.basename(rel)[:-3], 'title': title,
                              'sections': [{'id': a, 'title': h['title']} for a, h in _md_heads(rel).items()]})
    dt_rel = 'templates/review/decision_tree.md'
    esc = _read('templates/review/escalation.md')
    criteria = [{'id': m.group(1), 'when': m.group(2).strip(), 'why': m.group(3).strip()}
                for m in re.finditer(r'^\| `([a-z0-9-]+)` \|([^|]*)\|([^|]*)\|\s*$', esc, re.M)]
    rub = _read('templates/review/rationale_rubric.md')
    rubric = [{'id': m.group(1), 'name': m.group(2).strip(), 'question': m.group(3).strip()}
              for m in re.finditer(r'^\| (RR\d) ([^|]+)\|([^|]+)\|', rub, re.M)]
    form = review_check.report_form(ROOT)
    return {'format': 'claims-review-data/1', 'generator': 'python tools/build_claims_viewer.py',
            'source': persp_rel, 'template_version': version, 'repo_blob': REPO_BLOB,
            'stages': stages, 'roles': roles, 'questions': qs,
            # the filter the checklist starts with when the URL names none: {'triage': [values]} (empty: every question).
            # Showing a shorter list first is a change of the data (the field トリアージ and this), not of the screen
            'checklist': {'default': {}, 'triage_labels': {'all': 'すべての問い'}}, 'template_heads': dict(sorted(heads.items())),
            'contrasts': contrasts,
            'decision_tree': {'file': dt_rel, 'sections': [{'id': a, 'title': h['title'], 'number': h['number']}
                                                            for a, h in _md_heads(dt_rel).items()]},
            'escalation': {'file': 'templates/review/escalation.md', 'criteria': criteria},
            'rubric': {'file': 'templates/review/rationale_rubric.md', 'items': rubric},
            'report': {'file': 'templates/review/report_template.md',
                       'sections': [{'heading': s['heading'], 'header': s['header'], 'items': s['items']} for s in form['sections']],
                       'origins': form['origins'], 'kinds': form['kinds'], 'severities': form['severities'],
                       'verdicts': form['verdicts'], 'states': form['states']},
            'versions': {review_check.rel_of(ROOT, p): re.match(r'<!-- template_version: ([0-9.]+) -->', _read(review_check.rel_of(ROOT, p))).group(1)
                         for p in review_check.review_files(ROOT)}}


def names():
    def load(rel):
        return yaml.safe_load(_read(rel))
    ev = {}
    for rel in ('templates/catalog/issue_events.yaml', 'templates/catalog/use_events.yaml'):
        for e in load(rel)['events']:
            ev[e['id']] = e['name']
    q = load('templates/registry/questions.yaml')
    questions = {x['id']: x['text'] for x in q['questions']}
    questions.update({x['id']: x['proposed_text'] + '（保留）' for x in q.get('pending') or []})
    kinds = {k['id']: k['name'] for k in load('templates/catalog/token_kinds.yaml')['kinds']}
    with open(os.path.join(ROOT, 'docs', 'slide_ids.csv'), encoding='utf-8', newline='') as f:
        slides = {r['id']: {'n': int(r['n']), 'title': r['title']} for r in csv.DictReader(f)}
    return {'events': ev, 'questions': questions, 'token_kinds': kinds, 'slides': slides}


def trace_counts():
    data = yaml.safe_load(_read('templates/trace/requirements.yaml'))
    reqs = data['requirements']
    statuses = ['実装済み', '未着手', '後回し', '扱わない']
    tiers = ['core', 'full']
    by = Counter((r['tier'], r['status']) for r in reqs)
    parts = OrderedDict()
    for r in reqs:
        part = r['slide'].split(':', 1)[1][:3]  # slide:p04-... -> p04
        parts.setdefault(part, Counter())[(r['tier'], r['status'])] += 1
    owner = Counter((r['owner_issue'], r['status']) for r in reqs)
    return {'source': 'templates/trace/requirements.yaml', 'total': len(reqs), 'tiers': tiers, 'statuses': statuses,
            'tier_status': {t: {s: by[(t, s)] for s in statuses} for t in tiers},
            'parts': [{'part': p, 'tier_status': {t: {s: c[(t, s)] for s in statuses} for t in tiers}}
                      for p, c in sorted(parts.items())],
            'owners': [{'owner': o, 'status': {s: owner[(o, s)] for s in statuses}}
                       for o in sorted({r['owner_issue'] for r in reqs}, key=lambda x: int(x.lstrip('#')))]}


def sample_files(design_rel):
    """{file name: text} of a worked example: the registry YAML, claim_request_*.md and design.md (claim_lint reads
    them all: claim_request_*.md for L4, design.md for the slide references of --also-scan)."""
    d = os.path.join(ROOT, design_rel)
    names = [n for n in DESIGN_FILES if os.path.isfile(os.path.join(d, n))]
    names += sorted(n for n in os.listdir(d) if re.match(r'^claim_request_[a-z0-9_]+\.md$', n))
    if os.path.isfile(os.path.join(d, render.DOC_NAME)):
        names.append(render.DOC_NAME)
    return OrderedDict((n, _read(design_rel + '/' + n)) for n in names)


def skeleton_files():
    """The files of python tools/new_design.py, made for a directory next to templates/ (SKELETON_DIR)."""
    import new_design
    return OrderedDict(new_design.build(os.path.join(ROOT, SKELETON_DIR)))


def schemas():
    out = OrderedDict()
    for name in ('claims', 'token_types', 'hops'):
        with open(os.path.join(ROOT, 'templates', 'registry', name + '.schema.json'), encoding='utf-8') as f:
            out[name] = json.load(f)
    with open(os.path.join(ROOT, 'templates', 'review', 'review.schema.json'), encoding='utf-8') as f:
        out['review'] = json.load(f)  # review.yaml (#50), checked when it is read in
    return out


def lint_zip_entries():
    out = []
    for d, pat in LINT_FILES:
        for n in sorted(os.listdir(os.path.join(ROOT, d))):
            if re.match(pat, n) and os.path.isfile(os.path.join(ROOT, d, n)):
                out.append(d + '/' + n)
    return sorted(out)


def lint_zip():
    """tools/claim_lint and the files it reads, as a stored zip with fixed dates and modes (the same bytes on every
    platform: text is LF, no compression)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_STORED) as z:
        for rel in lint_zip_entries():
            with open(os.path.join(ROOT, rel), 'rb') as f:
                data = f.read().replace(b'\r\n', b'\n')
            zi = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            zi.create_system = 3
            zi.external_attr = 0o100644 << 16
            zi.compress_type = zipfile.ZIP_STORED
            z.writestr(zi, data)
    return buf.getvalue()


def _sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def _wheel_license(path):
    with zipfile.ZipFile(path) as z:
        meta = next(n for n in z.namelist() if n.endswith('.dist-info/METADATA'))
        lines = z.read(meta).decode('utf-8').splitlines()
    for prefix in ('License-Expression: ', 'License: '):
        for line in lines:
            if line.startswith(prefix):
                return line[len(prefix):].strip()
    return None


def vendor_files():
    out = []
    for dirpath, _, files in os.walk(VENDOR_DIR):
        for n in files:
            rel = os.path.relpath(os.path.join(dirpath, n), VENDOR_DIR).replace(os.sep, '/')
            if rel != 'MANIFEST.json':
                out.append(rel)
    return sorted(out)


def manifest():
    """docs/claims/vendor/MANIFEST.json: every vendored file with its sha256 (of the bytes as committed; .gitattributes
    keeps docs/claims/vendor/ byte for byte), the packages inside each file with version, license and source, and the
    vulnerability check (tools/claims_editor_vendor/advisories.json, written by hand when a version changes)."""
    def load(rel):
        with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
            return json.load(f)
    lock = load('tools/claims_editor_vendor/package-lock.json')
    adv = load('tools/claims_editor_vendor/advisories.json')
    pyo_pkg = load('docs/claims/vendor/pyodide/package.json')
    pyo_lock = load('docs/claims/vendor/pyodide/pyodide-lock.json')
    files = OrderedDict()
    for rel in vendor_files():
        with open(os.path.join(VENDOR_DIR, rel), 'rb') as f:
            data = f.read()
        files[rel] = {'bytes': len(data), 'sha256': _sha_bytes(data)}
    npm = [{'name': k[len('node_modules/'):], 'version': p['version'], 'license': p.get('license'),
            'resolved': p.get('resolved'), 'integrity': p.get('integrity')}
           for k, p in sorted(lock['packages'].items()) if k and not p.get('dev')]
    by_file = {p['file_name']: (name, p) for name, p in pyo_lock['packages'].items()}
    wheels, problems = [], []
    for rel in files:
        if not rel.endswith('.whl'):
            continue
        fn = rel.split('/')[-1]
        if fn not in by_file:
            problems.append(f'docs/claims/vendor/{rel}: not in pyodide-lock.json')
            continue
        name, p = by_file[fn]
        if p['sha256'] != files[rel]['sha256']:
            problems.append(f'docs/claims/vendor/{rel}: sha256 differs from pyodide-lock.json ({p["sha256"]})')
        wheels.append({'name': name, 'version': p['version'], 'file': rel, 'sha256_in_lock': p['sha256'],
                       'license': _wheel_license(os.path.join(VENDOR_DIR, rel)), 'depends': p['depends']})
    if problems:
        raise SystemExit('build_claims_viewer: ' + '\n  '.join(['vendored Pyodide packages:'] + problems))
    return {
        'format': 'claims-editor-vendor/1',
        'generator': 'python tools/build_claims_viewer.py',
        'note': 'sha256 of the committed bytes. The files are served from this site only (no CDN).',
        'components': [
            {'name': 'editor-libs.js', 'files': ['editor-libs.js', 'editor-libs.LICENSES.txt'],
             'built_by': 'tools/claims_editor_vendor/build.mjs (esbuild, from package-lock.json)', 'packages': npm},
            {'name': 'pyodide', 'version': pyo_pkg['version'], 'license': pyo_pkg['license'],
             'python': pyo_lock['info']['python'], 'source': adv['pyodide']['source'],
             'source_sha256': adv['pyodide']['source_sha256'],
             'license_file': {'file': 'pyodide/LICENSE', 'source': adv['pyodide']['license_file'],
                              'note': 'not in the core archive; the LICENSE of the pyodide repository at the tag 314.0.8'},
             'files': [r for r in files if r.startswith('pyodide/') and not r.endswith('.whl')],
             'packages': wheels, 'packages_source': adv['pyodide']['packages_source']},
        ],
        'files': files,
        'vulnerability_check': adv['check'],
    }


def js(name, obj):
    body = json.dumps(obj, ensure_ascii=False, separators=(',', ':'), sort_keys=False)
    return ('// Generated by tools/build_claims_viewer.py (#36, #49). Do not edit: change the YAML and run the script.\n'
            f"(window.CLAIMS_BUILD = window.CLAIMS_BUILD || {{}})[{json.dumps('data/' + name + '.js')}] = '{BUILD_PLACEHOLDER}';\n"
            'window.CLAIMS_VIEWER_DATA = window.CLAIMS_VIEWER_DATA || {};\n'
            f'window.CLAIMS_VIEWER_DATA[{json.dumps(name)}] = {body};\n')


# ------------------------------------------------------------ cache busting and the build id (#53)
# GitHub Pages serves every file with Cache-Control: max-age=600 and ignores the query string. Without a version in the
# URLs, a browser kept an old editor.js from its cache and ran it with a new review.js (TypeError, the review mode
# gone). So every URL the editor loads carries ?v=<the first 12 hex digits of the sha256 of the file>: the <script> and
# <link> of index.html are rewritten here, and the files loaded later (samples, the review data, the claim_lint worker,
# Pyodide's loader, claim_lint.zip) take their hash from data/build.js. Every module and data file also carries the
# build id (a hash of all of them), and the page compares them when it starts: files of two builds read together
# (an index.html still in the cache, a file from the server) show a banner that asks for a reload instead of failing.
HASH_LEN = 12
BUILD_PLACEHOLDER = 'dev'
HAND_WRITTEN = ('app.css', 'editor.js', 'preview.js', 'review.js', 'lint-worker.js')
# files that are part of the build but never rewritten (vendored, byte for byte)
VENDOR_PARTS = ('vendor/editor-libs.js', 'vendor/pyodide/pyodide.js')
# loaded after the page has started, by editor.js / review.js / the worker through asset(): their hash is in data/build.js
DYNAMIC = ('data/sample-a.js', 'data/sample-b.js', 'data/skeleton.js', 'data/review.js', 'lint-worker.js',
           'data/claim_lint.zip', 'vendor/pyodide/pyodide.js')
MARK_JS = re.compile(r"((?:const BUILD_ID = |\] = )')([0-9a-f]{%d}|%s)(';)" % (HASH_LEN, BUILD_PLACEHOLDER))
MARK_CSS = re.compile(r'(--build-id: ")([0-9a-f]{%d}|%s)(";)' % (HASH_LEN, BUILD_PLACEHOLDER))
STATIC_REF = re.compile(r'(<script src="|<link rel="stylesheet" href=")([^"?#]+)((?:\?[^"#]*)?)(")')
# a file loaded by a module (a <script> it adds, the worker, importScripts, fetch) named as a bare path, not through
# asset() (loadScript() applies asset() itself): it would be loaded without its hash
LOAD_SITE = re.compile(r"""(?:\.src\s*=\s*|importScripts\(|fetch\(|new URL\(|new Worker\()(?:base\s*\+\s*)?(['`])([^'`]+)\1""")


def _bytes(body):
    return body if isinstance(body, bytes) else body.encode('utf-8')


def _marks(rel, text):
    return (MARK_CSS if rel.endswith('.css') else MARK_JS).findall(text)


def _with_id(rel, text, build_id):
    rx = MARK_CSS if rel.endswith('.css') else MARK_JS
    return rx.sub(lambda m: m.group(1) + build_id + m.group(3), text)


def short_hash(body):
    return _sha_bytes(_bytes(body))[:HASH_LEN]


def stamp(files, parts):
    """files: {path under docs/claims/: str | bytes} of index.html, the hand-written modules, the generated data and
    vendor/MANIFEST.json (the build ids and ?v= in them may be anything); parts: {path: bytes} of the vendored files that
    are loaded but not rewritten. -> the same files with the build id and the hashes filled in, and data/build.js.

    The build id is the hash of every file with its own build id and ?v= blanked, so it does not depend on them."""
    def blank(rel, body):
        if isinstance(body, bytes):
            return body
        if rel == 'index.html':
            return STATIC_REF.sub(lambda m: m.group(1) + m.group(2) + m.group(4), body)
        return _with_id(rel, body, BUILD_PLACEHOLDER)
    every = dict(parts)
    every.update({rel: blank(rel, body) for rel, body in files.items()})
    h = hashlib.sha256()
    for rel in sorted(every):
        h.update(rel.encode('utf-8') + b'\0' + _sha_bytes(_bytes(every[rel])).encode('ascii') + b'\n')
    build_id = h.hexdigest()[:HASH_LEN]
    out = OrderedDict()
    for rel, body in files.items():
        if rel != 'index.html' and not isinstance(body, bytes) and (rel in HAND_WRITTEN or rel.startswith('data/')):
            if len(_marks(rel, body)) != 1:
                want = '--build-id: "dev";' if rel.endswith('.css') else "const BUILD_ID = 'dev';"
                raise SystemExit(f'build_claims_viewer: docs/claims/{rel} must hold exactly one build id ({want})')
            body = _with_id(rel, body, build_id)
        out[rel] = body
    hashes = {rel: short_hash(body) for rel, body in list(out.items()) + list(parts.items())}
    info = {'id': build_id, 'files': {rel: hashes[rel] for rel in DYNAMIC}}
    out['data/build.js'] = ('// Generated by tools/build_claims_viewer.py (#53). Do not edit. The build id and the content hashes of the\n'
                            '// files that the editor loads after it has started (asset() adds ?v=<hash> to their URLs).\n'
                            f"(window.CLAIMS_BUILD = window.CLAIMS_BUILD || {{}})[\"data/build.js\"] = '{build_id}';\n"
                            f'window.CLAIMS_BUILD_INFO = {json.dumps(info, separators=(",", ":"), sort_keys=True)};\n')
    hashes['data/build.js'] = short_hash(out['data/build.js'])
    missing = []

    def ref(m):
        rel = m.group(2)
        if rel not in hashes:
            missing.append(rel)
            return m.group(0)
        return m.group(1) + rel + '?v=' + hashes[rel] + m.group(4)
    if 'index.html' in files:
        out['index.html'] = STATIC_REF.sub(ref, files['index.html'])
    if missing:
        raise SystemExit('build_claims_viewer: docs/claims/index.html loads files the build does not know: ' + ', '.join(missing))
    out.move_to_end('data/build.js', last=False)
    return out


def _read_viewer(rel, root=None):
    with open(os.path.join(root or VIEWER_DIR, *rel.split('/')), 'rb') as f:
        raw = f.read()
    if rel.endswith('.zip') or (rel.startswith('vendor/') and not rel.endswith('.json')):
        return raw
    return raw.decode('utf-8').replace('\r\n', '\n')


def stamp_dir(viewer_dir):
    """Re-stamp a copy of docs/claims/ as it is on disk (the data are not rebuilt from the YAML): for the test that serves
    two builds one after the other (tools/tests/test_claims_editor_ux.py). -> the build id."""
    files = OrderedDict()
    files['index.html'] = _read_viewer('index.html', viewer_dir)
    for rel in HAND_WRITTEN:
        files[rel] = _read_viewer(rel, viewer_dir)
    for n in sorted(os.listdir(os.path.join(viewer_dir, 'data'))):
        if n != 'build.js':
            files['data/' + n] = _read_viewer('data/' + n, viewer_dir)
    files['vendor/MANIFEST.json'] = _read_viewer('vendor/MANIFEST.json', viewer_dir)
    out = stamp(files, {rel: _read_viewer(rel, viewer_dir) for rel in VENDOR_PARTS})
    for rel, body in out.items():
        with open(os.path.join(viewer_dir, *rel.split('/')), 'wb') as f:
            f.write(_bytes(body))
    return MARK_JS.search(out['data/build.js']).group(2)


def load_problems(rel, text):
    """A file of the build loaded by a module without asset(): it would be fetched without its content hash."""
    out = []
    for m in LOAD_SITE.finditer(text):
        path = m.group(2).split('?')[0]
        if path in DYNAMIC or path.startswith('data/') or path.endswith('.js'):
            line = text.count(chr(10), 0, m.start()) + 1
            out.append(f'docs/claims/{rel}:{line}: {m.group(2)} is loaded without its content hash (use asset({m.group(1)}{m.group(2)}{m.group(1)}))')
    return out


def stamp_problems(rel, cur, body):
    """Why a stamped file (index.html, a module, data/build.js) differs: a ?v= missing or stale, a build id stale."""
    out = []
    if rel == 'index.html':
        have = {m.group(2): m.group(3) for m in STATIC_REF.finditer(cur)}
        for m in STATIC_REF.finditer(body):
            path, want = m.group(2), m.group(3)
            if path not in have:
                out.append(f'docs/claims/index.html: {path} is not loaded any more')
            elif not have[path].startswith('?v='):
                out.append(f'docs/claims/index.html: {path} has no content hash (?v=); want {path}{want}')
            elif have[path] != want:
                out.append(f'docs/claims/index.html: {path}{have[path]} is stale (the file is now {path}{want})')
        if not out and STATIC_REF.sub('', cur) != STATIC_REF.sub('', body):
            out.append('docs/claims/index.html: differs from what the build writes')
        return out
    marks = _marks(rel, cur)
    if len(marks) != 1:
        return [f'docs/claims/{rel}: has {len(marks)} build id lines (want 1)']
    want_id = _marks(rel, body)[0][1]
    if marks[0][1] != want_id:
        out.append(f'docs/claims/{rel}: the build id {marks[0][1]} is stale (now {want_id})')
    if _with_id(rel, cur, want_id) != body:
        out.append(f'docs/claims/{rel}: differs from what the build writes' + (' (the content hash of a file loaded later is stale)' if rel == 'data/build.js' else ''))
    return out


def expected():
    """{path under docs/claims/: str (text, LF) or bytes}."""
    cols, problems = columns()
    if problems:
        raise SystemExit('build_claims_viewer: ' + '\n  '.join(['README column table does not match the schema:'] + problems))
    meta = {'format': 'claims-viewer-meta/1', 'generator': 'python tools/build_claims_viewer.py',
            'columns': cols, 'review': review_links(), 'names': names(),
            'datasets': [{'id': i, 'design': rel, 'label': label, 'profile': prof} for i, rel, label, prof in DATASETS],
            'skeleton_dir': SKELETON_DIR,
            'claim_tabs': claim_tabs(), 'claim_head': [{'label': label, 'columns': cols} for label, cols in CLAIM_HEAD],
            'lint_zip': {'file': 'data/claim_lint.zip', 'entries': lint_zip_entries()},
            'review_source': 'templates/review/*.md（見る欄の registry:<ファイル>#<列>）'}
    out = OrderedDict()
    out['data/meta.js'] = js('meta', meta)
    out['data/trace.js'] = js('trace', trace_counts())
    out['data/schemas.js'] = js('schemas', schemas())
    out['data/review.js'] = js('review', review_bundle())
    out['data/skeleton.js'] = js('skeleton', {'dir': SKELETON_DIR, 'generator': 'python tools/new_design.py',
                                              'files': skeleton_files()})
    for i, rel, label, prof in DATASETS:
        sample = {'id': i, 'design': rel, 'label': label, 'profile': prof, 'files': sample_files(rel)}
        if os.path.isfile(os.path.join(ROOT, rel, 'review.yaml')):
            sample['review'] = _read(rel + '/review.yaml')  # the recorded review of the example (#50)
        out[f'data/sample-{i[len("scenario-"):]}.js'] = js('sample-' + i[len('scenario-'):], sample)
    out['data/claim_lint.zip'] = lint_zip()
    out['vendor/MANIFEST.json'] = json.dumps(manifest(), ensure_ascii=False, indent=1) + '\n'
    # the page and its modules: only their build id and the ?v= of their URLs are written here (#53)
    out['index.html'] = _read_viewer('index.html')
    for rel in HAND_WRITTEN:
        out[rel] = _read_viewer(rel)
    return stamp(out, {rel: _read_viewer(rel) for rel in VENDOR_PARTS})


VIEWER_DIR = os.path.dirname(OUT_DIR)
STAMPED = ('index.html', 'data/build.js') + HAND_WRITTEN


def check(want):
    problems = []
    have = sorted('data/' + n for n in os.listdir(OUT_DIR)) if os.path.isdir(OUT_DIR) else []
    for n in have:
        if n not in want:
            problems.append(f'docs/claims/{n}: not generated any more (remove it)')
    for n, body in want.items():
        p = os.path.join(VIEWER_DIR, *n.split('/'))
        if not os.path.isfile(p):
            problems.append(f'docs/claims/{n}: missing')
            continue
        with open(p, 'rb') as f:
            raw = f.read()
        if isinstance(body, bytes):
            if raw != body:
                problems.append(f'docs/claims/{n}: differs from what the sources generate '
                                f'(sha256 {_sha_bytes(raw)[:16]}… / generated {_sha_bytes(body)[:16]}…)')
            continue
        cur = raw.decode('utf-8').replace('\r\n', '\n')
        if n in STAMPED and cur != body:
            problems.extend(stamp_problems(n, cur, body))
            continue
        if cur != body:
            # the data are one long JSON line: show where they first differ, not a megabyte-long diff
            k = next((j for j in range(min(len(cur), len(body))) if cur[j] != body[j]), min(len(cur), len(body)))
            problems.append(f'docs/claims/{n}: differs from the YAML at character {k}: '
                            f'committed {cur[max(0, k - 60):k + 60]!r} / generated {body[max(0, k - 60):k + 60]!r}')
    for rel in ('editor.js', 'preview.js', 'review.js', 'lint-worker.js'):
        p = os.path.join(VIEWER_DIR, rel)
        if os.path.isfile(p):
            with open(p, encoding='utf-8') as f:
                problems.extend(load_problems(rel, f.read()))
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check', action='store_true', help='exit 1 when docs/claims/data/ or vendor/MANIFEST.json differ from what the sources generate')
    a = ap.parse_args(argv)
    want = expected()
    out = sys.stdout
    if a.check:
        problems = check(want)
        for p in problems:
            print(p, file=out)
        print('build_claims_viewer --check: ' + ('FAIL (' + CHECK_HINT + ')' if problems else 'OK'), file=out)
        return 1 if problems else 0
    os.makedirs(OUT_DIR, exist_ok=True)
    for n in os.listdir(OUT_DIR):
        if 'data/' + n not in want:
            os.remove(os.path.join(OUT_DIR, n))
            print('removed docs/claims/data/' + n)
    for n, body in want.items():
        p = os.path.join(VIEWER_DIR, *n.split('/'))
        if isinstance(body, bytes):
            with open(p, 'wb') as f:
                f.write(body)
        else:
            with open(p, 'w', encoding='utf-8', newline='\n') as f:
                f.write(body)
            body = body.encode('utf-8')
        print(f'wrote docs/claims/{n} ({len(body)} bytes)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
