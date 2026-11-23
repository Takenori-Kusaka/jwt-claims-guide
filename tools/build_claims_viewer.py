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
  schemas.js       the registry JSON Schemas (templates/registry/*.schema.json) for the in-browser schema check
  skeleton.js      the files of python tools/new_design.py (an empty design), for 「空の雛形から始める」
  sample-<x>.js    the files of each worked example (YAML, claim_request_*.md, design.md), for 「サンプルを開く」
  claim_lint.zip   tools/claim_lint and the files it reads (catalogue, registry, slide IDs), unpacked into Pyodide's
                   file system (stored, not deflated: the bytes do not depend on the zlib version)
and docs/claims/vendor/MANIFEST.json: version, license, source and sha256 of every vendored file, with the
vulnerability check of tools/claims_editor_vendor/advisories.json.
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
             'files': [r for r in files if r.startswith('pyodide/') and not r.endswith('.whl')],
             'packages': wheels, 'packages_source': adv['pyodide']['packages_source']},
        ],
        'files': files,
        'vulnerability_check': adv['check'],
    }


def js(name, obj):
    body = json.dumps(obj, ensure_ascii=False, separators=(',', ':'), sort_keys=False)
    return ('// Generated by tools/build_claims_viewer.py (#36, #49). Do not edit: change the YAML and run the script.\n'
            'window.CLAIMS_VIEWER_DATA = window.CLAIMS_VIEWER_DATA || {};\n'
            f'window.CLAIMS_VIEWER_DATA[{json.dumps(name)}] = {body};\n')


def expected():
    """{path under docs/claims/: str (text, LF) or bytes}."""
    cols, problems = columns()
    if problems:
        raise SystemExit('build_claims_viewer: ' + '\n  '.join(['README column table does not match the schema:'] + problems))
    meta = {'format': 'claims-viewer-meta/1', 'generator': 'python tools/build_claims_viewer.py',
            'columns': cols, 'review': review_links(), 'names': names(),
            'datasets': [{'id': i, 'design': rel, 'label': label, 'profile': prof} for i, rel, label, prof in DATASETS],
            'skeleton_dir': SKELETON_DIR,
            'lint_zip': {'file': 'data/claim_lint.zip', 'entries': lint_zip_entries()},
            'review_source': 'templates/review/*.md（見る欄の registry:<ファイル>#<列>）'}
    out = OrderedDict()
    out['data/meta.js'] = js('meta', meta)
    out['data/trace.js'] = js('trace', trace_counts())
    out['data/schemas.js'] = js('schemas', schemas())
    out['data/skeleton.js'] = js('skeleton', {'dir': SKELETON_DIR, 'generator': 'python tools/new_design.py',
                                              'files': skeleton_files()})
    for i, rel, label, prof in DATASETS:
        out[f'data/sample-{i[len("scenario-"):]}.js'] = js('sample-' + i[len('scenario-'):], {
            'id': i, 'design': rel, 'label': label, 'profile': prof, 'files': sample_files(rel)})
    out['data/claim_lint.zip'] = lint_zip()
    out['vendor/MANIFEST.json'] = json.dumps(manifest(), ensure_ascii=False, indent=1) + '\n'
    return out


VIEWER_DIR = os.path.dirname(OUT_DIR)


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
        if cur != body:
            # the data are one long JSON line: show where they first differ, not a megabyte-long diff
            k = next((j for j in range(min(len(cur), len(body))) if cur[j] != body[j]), min(len(cur), len(body)))
            problems.append(f'docs/claims/{n}: differs from the YAML at character {k}: '
                            f'committed {cur[max(0, k - 60):k + 60]!r} / generated {body[max(0, k - 60):k + 60]!r}')
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
