# -*- coding: utf-8 -*-
"""Check the stable slide IDs (issue #15) and the references to them.

  python tools/check_slide_refs.py [--expect N] [PATH ...]

(a) deck/slide_ids.json (written by `cd deck && node build.js`) must give every slide an ID of the form
    pNN-<kebab-slug> (ASCII), with no duplicates and N slides in total (default 152). The IDs in
    docs/slides.json must be the same, in the same order (otherwise the web build is stale).
(b) Every reference `slide:<id>` in the given files or directories (searched recursively) must name an
    existing ID. A reference is the literal `slide:` followed by the ID, e.g. `slide:p04-carry-or-query`;
    anything after the ID that cannot be part of it (`.R1`, `)`, `,`, space ...) ends the reference.

Exit status: 0 if everything resolves, 1 otherwise (each problem is printed as file:line).
"""
import argparse, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ID_RE = re.compile(r'^p\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$')
# `slide:` not preceded by a word character; the candidate is taken greedily and then checked,
# so that a malformed reference (upper case, a bare slide number) is reported instead of being skipped.
REF_RE = re.compile(r'(?<![\w-])slide:([A-Za-z0-9_]+(?:-[A-Za-z0-9_]+)*)')
SKIP_DIRS = {'.git', 'node_modules', '__pycache__'}
TEXT_EXT = {'.md', '.markdown', '.txt', '.yaml', '.yml', '.json', '.csv', '.tsv', '.py', '.js', '.ts', '.html', '.toml', '.rego', '.cel'}


def load_ids(expect):
    errors = []
    path = os.path.join(ROOT, 'deck', 'slide_ids.json')
    ids = json.load(open(path, encoding='utf-8'))
    seq = [x.get('id') for x in ids]
    if len(seq) != expect:
        errors.append(f'{path}: {len(seq)} slides, expected {expect}')
    for k, x in enumerate(ids, 1):
        if x.get('n') != k:
            errors.append(f'{path}: entry {k} has n={x.get("n")}')
        if not x.get('id'):
            errors.append(f'{path}: slide {k} has no id')
        elif not ID_RE.match(x['id']):
            errors.append(f'{path}: slide {k}: malformed id {x["id"]!r} (want pNN-kebab-slug)')
    dup = sorted({i for i in seq if i and seq.count(i) > 1})
    for i in dup:
        errors.append(f'{path}: duplicate id {i} at slides {[k for k, j in enumerate(seq, 1) if j == i]}')
    web = os.path.join(ROOT, 'docs', 'slides.json')
    if os.path.exists(web):
        wseq = [d.get('id') for d in json.load(open(web, encoding='utf-8'))]
        if wseq != seq:
            errors.append(f'{web}: ids differ from deck/slide_ids.json; rerun python tools/build_web_slides.py')
    return set(i for i in seq if i), errors


def iter_files(paths):
    for p in paths:
        if os.path.isdir(p):
            for d, dirs, files in os.walk(p):
                dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
                for f in sorted(files):
                    if os.path.splitext(f)[1].lower() in TEXT_EXT:
                        yield os.path.join(d, f)
        else:
            yield p  # a missing path is reported by check_refs


def check_refs(paths, known):
    errors, n, bad = [], 0, 0
    for f in iter_files(paths):
        if not os.path.isfile(f):
            errors.append(f'{f}: no such file or directory'); continue
        try:
            lines = open(f, encoding='utf-8').read().splitlines()
        except UnicodeDecodeError:
            continue
        for ln, line in enumerate(lines, 1):
            for m in REF_RE.finditer(line):
                n += 1
                ref = m.group(1)
                if ref not in known:
                    bad += 1
                    hint = '' if ID_RE.match(ref) else ' (malformed: want pNN-kebab-slug)'
                    errors.append(f'{f}:{ln}: unknown slide id slide:{ref}{hint}')
    return n, bad, errors


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('paths', nargs='*', help='files or directories to scan for slide:<id> references')
    ap.add_argument('--expect', type=int, default=152, help='expected number of slides (default 152)')
    a = ap.parse_args()
    known, errors = load_ids(a.expect)
    print(f'slide ids: {len(known)} unique')
    n, bad, ref_errors = check_refs(a.paths, known)
    errors += ref_errors
    if a.paths:
        print(f'references: {n} found, {n - bad} resolved')
    for e in errors:
        print('ERROR', e)
    print('FAIL' if errors else 'OK')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
