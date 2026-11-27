# -*- coding: utf-8 -*-
"""The calibration set of #12: designs with seeded errors, their clean twins (controls), and the answer key.

  python tools/calibration_check.py check                    # the checks below (CI)
  python tools/calibration_check.py materialize DESIGN OUT   # the design as a reviewer gets it: plain file names, no marker
  python tools/calibration_check.py packet DESIGN OUT [--seed S]   # the whole packet of one review session (protocol.md 6.)
  python tools/calibration_check.py render DESIGN            # render --write at the neutral path designs/target, written back
  python tools/calibration_check.py mark DIR (--seeded | --control)   # add the markers (used once, when the set is made)

DESIGN is a directory name under research/template-design/calibration (seeded-a, seeded-b, control-a, control-b).

The files of a seeded design carry `.broken` in their names and the marker 「意図的に誤りを含む教材。設計に使わない」 inside
(templates/CONTRIBUTING.md 4., 意図的に誤りを含む教材); the controls carry 「測定の対照に使う教材。設計に使わない」. The marker is one exact
line (Markdown: after the first heading, with a blank line before it; YAML: line 2; JSON: line 2 as a "_warning" member), so that
materialize removes it byte for byte: the materialized design is what claim_lint, render --check and the reviewer see.

claim_lint and render write the design's path (relative to the repository) into design.md 1. and into the $id of the payload
schemas. So every design is staged at the same neutral path, designs/target (git-ignored), to be rendered, checked and handed
to a reviewer: nothing in a design tells which of the four it is.

Checks (errors):
  C1  every file of every design carries its marker; seeded files have `.broken` in the name, control files do not
  C2  claim_lint (Full profile, --also-scan design.md) on the staged design gives the counts and the warn rows of
      calibration/expected_lint.yaml (error 0 for all four: a reviewer returns a design with a lint error unread)
  C3  render --check passes on the staged design
  C4  every location of seeded_errors.yaml resolves: the file exists in the materialized seeded design, a YAML row id
      exists in that file, a quoted phrase occurs in that file
  C5  each seeded design and its control show the same traits in review_triage.py --design (the controls are twins)
  C6  the files listed in calibration/commitments.sha256 have those sha256 (the targets and the key fixed before measuring)
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAL = os.path.join(ROOT, 'research', 'template-design', 'calibration')
TARGET = os.path.join(ROOT, 'designs', 'target')
STAMP = '.calibration-staging'
SEEDED = ('seeded-a', 'seeded-b')
CONTROLS = {'seeded-a': 'control-a', 'seeded-b': 'control-b'}
DESIGNS = SEEDED + tuple(CONTROLS.values())
M_SEEDED = '意図的に誤りを含む教材。設計に使わない'
M_CONTROL = '測定の対照に使う教材。設計に使わない'
MATERIALS = ('templates/review/short_list.md', 'templates/review/perspectives.md', 'templates/review/decision_tree.md')
MATERIAL_DIRS = ('templates/review/contrasts',)


def marker_of(design):
    return M_SEEDED if design in SEEDED else M_CONTROL


def _lines(text):
    return text.split('\n')


def add_marker(path, marker):
    with open(path, encoding='utf-8', newline='') as f:
        text = f.read()
    lines = _lines(text)
    ext = os.path.splitext(path.replace('.broken', ''))[1]
    if ext == '.md':
        i = next(k for k, l in enumerate(lines) if l.startswith('#'))
        lines[i + 1:i + 1] = ['', f'> **{marker}**']
    elif ext in ('.yaml', '.yml'):
        lines[1:1] = [f'# {marker}']
    elif ext == '.json':
        if not lines[0].startswith('{'):
            raise ValueError(f'{path}: a JSON file must start with "{{" on its own line')
        lines[1:1] = [f'  "_warning": "{marker}",']
    else:
        raise ValueError(f'{path}: no marker form for {ext}')
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write('\n'.join(lines))


def strip_marker(text, ext, marker):
    """Return (text without the marker, whether the marker was there)."""
    lines = _lines(text)
    if ext == '.md':
        want = f'> **{marker}**'
        for k, l in enumerate(lines):
            if l == want and k > 0 and lines[k - 1] == '':
                return '\n'.join(lines[:k - 1] + lines[k + 1:]), True
    elif ext in ('.yaml', '.yml'):
        if len(lines) > 1 and lines[1] == f'# {marker}':
            return '\n'.join(lines[:1] + lines[2:]), True
    elif ext == '.json':
        if len(lines) > 1 and lines[1] == f'  "_warning": "{marker}",':
            return '\n'.join(lines[:1] + lines[2:]), True
    return text, False


def files_of(d):
    for base, _dirs, names in os.walk(d):
        for n in sorted(names):
            yield os.path.join(base, n)


def source_name(design, plain_rel):
    """The name in the calibration directory of a materialized file (seeded files carry .broken)."""
    if design not in SEEDED:
        return plain_rel
    root, ext = os.path.splitext(plain_rel)
    if root.endswith('.schema'):
        return root[:-len('.schema')] + '.broken.schema' + ext
    return root + '.broken' + ext


def materialize(design, out):
    src = os.path.join(CAL, design)
    marker = marker_of(design)
    missing = []
    for p in files_of(src):
        rel = os.path.relpath(p, src)
        plain = rel.replace('.broken', '')
        ext = os.path.splitext(plain)[1]
        dst = os.path.join(out, plain)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if ext in ('.md', '.yaml', '.yml', '.json'):
            with open(p, encoding='utf-8', newline='') as f:
                text, had = strip_marker(f.read(), ext, marker)
            if not had:
                missing.append(rel)
            with open(dst, 'w', encoding='utf-8', newline='') as f:
                f.write(text)
        else:
            shutil.copyfile(p, dst)
            missing.append(rel)
    return missing


def stage(design):
    """Materialize DESIGN at designs/target, replacing an earlier staging (never a directory this tool did not make)."""
    if os.path.exists(TARGET):
        if not os.path.isfile(os.path.join(TARGET, STAMP)):
            raise SystemExit(f'{TARGET} exists and was not made by calibration_check; move it away first')
        shutil.rmtree(TARGET)
    missing = materialize(design, TARGET)
    open(os.path.join(TARGET, STAMP), 'w').close()
    return missing


def unstage():
    if os.path.isfile(os.path.join(TARGET, STAMP)):
        shutil.rmtree(TARGET)
        parent = os.path.dirname(TARGET)
        if os.path.isdir(parent) and not os.listdir(parent):
            os.rmdir(parent)


def run(cmd):
    r = subprocess.run([sys.executable] + cmd, cwd=ROOT, capture_output=True)
    return r.returncode, r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


def lint(dirpath):
    rc, out, err = run(['tools/claim_lint', dirpath, '--also-scan', os.path.join(dirpath, 'design.md'), '--format', 'json'])
    try:
        return json.loads(out)
    except ValueError:
        raise SystemExit(f'claim_lint gave no JSON for {dirpath}: {err[-500:]}')


def lint_summary(res):
    rows = sorted({(f['rule'], str(f['target'])) for f in res['findings'] if f['severity'] == 'warn'})
    return {'error': res['counts']['error'], 'warn': res['counts']['warn'], 'info': res['counts']['info'],
            'warn_rows': [f'{r} {t}' for r, t in rows]}


def traits(dirpath):
    rc, out, err = run(['tools/review_triage.py', '--design', dirpath, '--seed', '12'])
    if rc:
        raise SystemExit(f'review_triage failed on {dirpath}: {err[-500:]}')
    rows = []
    for line in out.split('\n'):
        m = re.match(r'^\|\s*([^|]+?)\s*\|\s*(当たる|当たらない|読めない[^|]*)\s*\|', line)
        if m:
            rows.append((m.group(1), m.group(2)))
    return rows


def render_back(design):
    """render --write at the neutral path, then write the changed files back with their markers and names."""
    stage(design)
    try:
        rc, o, e = run(['tools/claim_lint', 'render', TARGET, '--write'])
        if rc:
            raise SystemExit(f'render --write failed for {design}: {(o + e)[-500:]}')
        src = os.path.join(CAL, design)
        for p in files_of(TARGET):
            rel = os.path.relpath(p, TARGET)
            if rel == STAMP:
                continue
            dst = os.path.join(src, source_name(design, rel))
            with open(p, encoding='utf-8', newline='') as f:
                plain = f.read()
            if os.path.isfile(dst):
                with open(dst, encoding='utf-8', newline='') as f:
                    cur, _ = strip_marker(f.read(), os.path.splitext(rel)[1], marker_of(design))
                if cur == plain:
                    continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'w', encoding='utf-8', newline='') as f:
                f.write(plain)
            add_marker(dst, marker_of(design))
            print(f'wrote {os.path.relpath(dst, ROOT)}')
    finally:
        unstage()


def row_ids(text):
    return set(re.findall(r'^\s*-?\s*\{?\s*(?:id|event):\s*["\']?([^"\'\s,}#]+)', text, re.M))


def check(errors):
    with open(os.path.join(CAL, 'expected_lint.yaml'), encoding='utf-8') as f:
        expected = yaml.safe_load(f)
    with open(os.path.join(CAL, 'seeded_errors.yaml'), encoding='utf-8') as f:
        key = yaml.safe_load(f)
    with tempfile.TemporaryDirectory() as tmp:
        mats, trait_rows = {}, {}
        try:
            for d in DESIGNS:
                src = os.path.join(CAL, d)
                if not os.path.isdir(src):
                    errors.append(f'C1 {d}: directory missing')
                    continue
                for p in files_of(src):
                    rel = os.path.relpath(p, src)
                    if (d in SEEDED) != ('.broken' in os.path.basename(rel)):
                        errors.append(f'C1 {d}/{rel}: ' + ('seeded files need .broken in the name' if d in SEEDED
                                                           else 'control files must not carry .broken'))
                for rel in stage(d):
                    errors.append(f'C1 {d}/{rel}: marker 「{marker_of(d)}」 missing or not in the exact form')
                got = lint_summary(lint(TARGET))
                want = expected.get(d)
                if got != want:
                    errors.append(f'C2 {d}: claim_lint gives {json.dumps(got, ensure_ascii=False)}, expected_lint.yaml '
                                  f'has {json.dumps(want, ensure_ascii=False)}')
                rc, o, e = run(['tools/claim_lint', 'render', TARGET, '--check'])
                if rc:
                    errors.append(f'C3 {d}: render --check failed: {(o + e).strip()[-400:]}')
                trait_rows[d] = traits(TARGET)
                mats[d] = os.path.join(tmp, d)
                shutil.copytree(TARGET, mats[d])
        finally:
            unstage()
        for err in key.get('errors', []):
            d = err['design']
            if d not in mats:
                continue
            for loc in err.get('locations', []):
                path = os.path.join(mats[d], loc['file'])
                if not os.path.isfile(path):
                    errors.append(f"C4 {err['id']}: {d}/{loc['file']} does not exist")
                    continue
                with open(path, encoding='utf-8') as f:
                    text = f.read()
                if 'row' in loc and loc['row'] not in row_ids(text):
                    errors.append(f"C4 {err['id']}: row {loc['row']} not found in {loc['file']}")
                if 'quote' in loc and loc['quote'] not in text:
                    errors.append(f"C4 {err['id']}: quote 「{loc['quote']}」 not found in {loc['file']}")
        for s, c in CONTROLS.items():
            if s in trait_rows and c in trait_rows and trait_rows[s] != trait_rows[c]:
                errors.append(f'C5 {s} and {c} show different traits in review_triage.py --design')
    cpath = os.path.join(CAL, 'commitments.sha256')
    if os.path.isfile(cpath):
        n = 0
        for line in open(cpath, encoding='utf-8'):
            m = re.match(r'([0-9a-f]{64}) \*(\S+)$', line.strip())
            if not m:
                continue
            want, rel = m.groups()
            p = os.path.join(CAL, rel)
            got = hashlib.sha256(open(p, 'rb').read()).hexdigest() if os.path.isfile(p) else 'missing'
            if got != want:
                errors.append(f'C6 {rel}: sha256 {got} differs from commitments.sha256 ({want})')
            n += 1
        if not n:
            errors.append('C6 commitments.sha256 lists no file')
    else:
        errors.append('C6 commitments.sha256 is missing')
    return errors


def packet(design, out, seed):
    """The packet of one review session: the materials, the design at designs/target, the CI result and the sheet.
    The label of the session is kept in the record only (protocol.md 6.), never in the packet."""
    os.makedirs(out, exist_ok=True)
    for m in MATERIALS:
        shutil.copyfile(os.path.join(ROOT, m), os.path.join(out, os.path.basename(m)))
    for md in MATERIAL_DIRS:
        shutil.copytree(os.path.join(ROOT, md), os.path.join(out, os.path.basename(md)), dirs_exist_ok=True)
    stage(design)
    try:
        rc, o, e = run(['tools/claim_lint', 'designs/target', '--also-scan', 'designs/target/design.md'])
        with open(os.path.join(out, 'ci-result.txt'), 'w', encoding='utf-8') as f:
            f.write(o)
        rc, o, e = run(['tools/review_triage.py', '--design', 'designs/target', '--seed', str(seed)])
        with open(os.path.join(out, 'sheet.md'), 'w', encoding='utf-8') as f:
            f.write(o)
        shutil.copytree(TARGET, os.path.join(out, 'designs', 'target'), ignore=shutil.ignore_patterns(STAMP))
    finally:
        unstage()


def main(argv=None):
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description='The calibration set of #12 (seeded designs, controls, answer key).')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('check')
    p = sub.add_parser('materialize')
    p.add_argument('design', choices=DESIGNS)
    p.add_argument('out')
    p = sub.add_parser('packet')
    p.add_argument('design', choices=DESIGNS)
    p.add_argument('out')
    p.add_argument('--seed', default='12')
    p = sub.add_parser('render')
    p.add_argument('design', choices=DESIGNS)
    p = sub.add_parser('mark')
    p.add_argument('dir')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--seeded', action='store_true')
    g.add_argument('--control', action='store_true')
    a = ap.parse_args(argv)
    if a.cmd == 'check':
        errors = check([])
        for e in errors:
            print(e)
        print(f'calibration_check: {len(errors)} error(s)' if errors else 'calibration_check: OK')
        return 1 if errors else 0
    if a.cmd == 'materialize':
        missing = materialize(a.design, a.out)
        for m in missing:
            print(f'marker missing: {m}')
        return 1 if missing else 0
    if a.cmd == 'packet':
        packet(a.design, a.out, a.seed)
        return 0
    if a.cmd == 'render':
        render_back(a.design)
        return 0
    if a.cmd == 'mark':
        marker = M_SEEDED if a.seeded else M_CONTROL
        for p in list(files_of(a.dir)):
            if a.seeded and '.broken' not in os.path.basename(p):
                root, ext = os.path.splitext(p)
                new = (root[:-len('.schema')] + '.broken.schema' + ext) if root.endswith('.schema') else root + '.broken' + ext
                os.replace(p, new)
                p = new
            add_marker(p, marker)
        return 0


if __name__ == '__main__':
    sys.exit(main())
