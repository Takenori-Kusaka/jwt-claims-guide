# -*- coding: utf-8 -*-
"""Build the data of the design-document viewer (#36, GitHub Pages: docs/claims/).

  python tools/build_claims_viewer.py            # write docs/claims/data/*.js
  python tools/build_claims_viewer.py --check    # exit 1 when docs/claims/data/ differs from the YAML (CI)

The viewer is static HTML and JS (docs/claims/index.html, app.js). It reads no network resource: the data are
JavaScript files that assign JSON to window.CLAIMS_VIEWER_DATA, loaded with <script src> from the same directory,
so the page works from file:// too and its CSP can say connect-src 'none'.

Files written (docs/claims/data/):
  meta.js          column headings of the registry (templates/registry/README.md 3.1-3.4, checked against the
                   *.schema.json properties), review questions that look at each column (templates/review/),
                   questions, event and token-kind names, slide titles (docs/slide_ids.csv), the list of datasets
  trace.js         tier x status counts of the trace table (templates/trace/requirements.yaml, #22)
  <scenario>.js    the render bundle of each worked example (python tools/claim_lint render <dir> --format json, #19)
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, 'tools')
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import yaml  # noqa: E402
from claim_lint import render  # noqa: E402
import review_check  # noqa: E402

OUT_DIR = os.path.join(ROOT, 'docs', 'claims', 'data')
DATASETS = [  # (id, design dir, label)
    ('scenario-a', 'templates/examples/scenario-a', 'シナリオ A（マルチテナント SaaS、Lite）'),
    ('scenario-b', 'templates/examples/scenario-b', 'シナリオ B（社内の業務システムと AI エージェント、Full）'),
]
README = 'templates/registry/README.md'
# README section -> (key in meta.columns, schema file, JSON pointer of the object whose properties are the columns)
COLUMN_SECTIONS = [
    ('### 3.1 ', 'claims', 'templates/registry/claims.schema.json', ('$defs', 'claim')),
    ('### 3.2 ', 'token_types', 'templates/registry/token_types.schema.json', ('$defs', 'token_type')),
    ('### 3.3 ', 'issuance_profile', 'templates/registry/token_types.schema.json', ('$defs', 'issuance_profile')),
    ('### 3.4 ', 'hops', 'templates/registry/hops.schema.json', ('$defs', 'hop')),
]
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


def bundle_of(design_rel):
    design_dir = os.path.join(ROOT, design_rel)
    d = render.load_design(design_dir)
    lint = render.lint_result(design_dir, os.path.join(design_dir, render.DOC_NAME))
    return render.bundle(design_dir, d, render.build_sections(d, lint))


def js(name, obj):
    body = json.dumps(obj, ensure_ascii=False, separators=(',', ':'), sort_keys=False)
    return ('// Generated by tools/build_claims_viewer.py (#36). Do not edit: change the YAML and run the script.\n'
            'window.CLAIMS_VIEWER_DATA = window.CLAIMS_VIEWER_DATA || {};\n'
            f'window.CLAIMS_VIEWER_DATA[{json.dumps(name)}] = {body};\n')


def expected():
    cols, problems = columns()
    if problems:
        raise SystemExit('build_claims_viewer: ' + '\n  '.join(['README column table does not match the schema:'] + problems))
    meta = {'format': 'claims-viewer-meta/1', 'generator': 'python tools/build_claims_viewer.py',
            'columns': cols, 'review': review_links(), 'names': names(),
            'datasets': [{'id': i, 'design': rel, 'label': label} for i, rel, label in DATASETS],
            'review_source': 'templates/review/*.md（見る欄の registry:<ファイル>#<列>）'}
    out = OrderedDict()
    out['meta.js'] = js('meta', meta)
    out['trace.js'] = js('trace', trace_counts())
    for i, rel, _ in DATASETS:
        out[f'{i}.js'] = js(i, bundle_of(rel))
    return out


def check(want):
    problems = []
    have = sorted(n for n in os.listdir(OUT_DIR)) if os.path.isdir(OUT_DIR) else []
    for n in have:
        if n not in want:
            problems.append(f'docs/claims/data/{n}: not generated any more (remove it)')
    for n, text in want.items():
        p = os.path.join(OUT_DIR, n)
        if not os.path.isfile(p):
            problems.append(f'docs/claims/data/{n}: missing')
            continue
        with open(p, encoding='utf-8') as f:
            cur = f.read().replace('\r\n', '\n')
        if cur != text:
            # the data are one long JSON line: show where they first differ, not a megabyte-long diff
            k = next((j for j in range(min(len(cur), len(text))) if cur[j] != text[j]), min(len(cur), len(text)))
            problems.append(f'docs/claims/data/{n}: differs from the YAML at character {k}: '
                            f'committed {cur[max(0, k - 60):k + 60]!r} / generated {text[max(0, k - 60):k + 60]!r}')
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check', action='store_true', help='exit 1 when docs/claims/data/ differs from what the YAML generates')
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
        if n not in want:
            os.remove(os.path.join(OUT_DIR, n))
            print('removed docs/claims/data/' + n)
    for n, text in want.items():
        with open(os.path.join(OUT_DIR, n), 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        print(f'wrote docs/claims/data/{n} ({len(text.encode("utf-8"))} bytes)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
