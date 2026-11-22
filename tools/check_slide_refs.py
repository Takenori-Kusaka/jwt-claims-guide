# -*- coding: utf-8 -*-
"""Check the stable slide IDs (issue #15) and the references to them.

  python tools/check_slide_refs.py [--expect N] [--base GIT_REF] [--ext .adoc ...] [PATH ...]

Fails (exit 1) when any of the following holds. Every problem is printed on its own line.

IDs (always checked)
  - deck/slide_ids.json is stale: its IDs differ from the `id: '...'` declarations in deck/p*.js
    (read statically, in file and source order), or a slide call in deck/p*.js has no id
  - an ID is missing, malformed (not pNN-kebab-slug), duplicated, or the count differs from the
    number of slides declared in deck/p*.js (or from --expect N when given)
  - docs/slides.json does not carry the same IDs in the same order (the web build is stale)
Registry (deck/slide_ids_registry.json, append-only: every ID ever issued)
  - a slide uses an ID that is not in the registry (run `node build.js --ids-only --register`)
  - a slide uses a retired ID (IDs are never reused)
  - an active registry ID is on no slide (restore it, or mark it retired)
  - a slide's title has drifted from the registered title (similarity below TITLE_MIN), or it is
    closer to another ID's registered title (the ID was moved to another slide). An intended
    title change is recorded by appending {"date", "title"} to the entry's "retitled" list
  - with --base GIT_REF: an entry of the registry at GIT_REF was removed or rewritten
    (only appending entries, "retitled" items and "retired"/"reason" is allowed)
References (in the given files / directories)
  - `slide:<id>` names no existing ID, or is malformed (see REFERENCE GRAMMAR)
  - something that looks like a reference to an ID or a slide number but is not written exactly
    `slide:<id>` (other letter case, spaces around the colon)
  - a link to the web viewer (its github.io URL followed by a # fragment) whose fragment is a
    slide number (#sNN, shifts when slides are inserted) or an unknown ID
  - a scanned file is not UTF-8, or a given path does not exist

REFERENCE GRAMMAR
  ref    = "slide:" id [ "." "R" 1*DIGIT ]       ; lower-case "slide", no spaces
  id     = "p" 2DIGIT "-" word *( "-" word )     ; word = 1*( a-z / 0-9 )
  The reference starts where "slide:" is not preceded by a letter, digit, "_" or "-". The id runs
  over [A-Za-z0-9_-] and stops at the first other character (".", ",", ")", space, Japanese text ...).
  A following ".R<digits>" is a requirement number (grammar owned by #22); it is accepted but only
  the id is resolved. Any other text after "." ends the reference (so a sentence may end with ".").
  "slide:" followed by no letter or digit (e.g. the placeholder "slide:<id>") is not a reference.
Directories are searched recursively for the extensions in TEXT_EXT (plus --ext); files given
explicitly are always scanned. Binary formats (.xlsx, .pptx, .pdf) are not scanned.
"""
import argparse, difflib, glob, json, os, re, subprocess, sys, unicodedata
from urllib.parse import unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ID_RE = re.compile(r'^p\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$')
TITLE_MIN = 0.6  # minimum similarity between a slide's title and its registered title
TEXT_EXT = {'.md', '.markdown', '.txt', '.rst', '.adoc', '.yaml', '.yml', '.json', '.csv', '.tsv',
            '.py', '.js', '.ts', '.html', '.toml', '.rego', '.cel'}
SKIP_DIRS = {'.git', 'node_modules', '__pycache__'}

REF_RE = re.compile(r'(?<![A-Za-z0-9_-])(?P<kw>slide)(?P<sp1>\s*):(?P<sp2>[ \t]*)(?P<body>[A-Za-z0-9_.-]*)', re.I)
NEAR_RE = re.compile(r'(?:[pP]\d{2}-|\d+(?![A-Za-z]))')  # id-like or a bare slide number
SUFFIX_RE = re.compile(r'\.R[0-9]+')
URL_RE = re.compile(r'takenori-kusaka\.github\.io/jwt-claims-guide/?(?:index\.html)?#(?P<frag>[A-Za-z0-9_%~-]*)')  # fragment ends at "." "," ")" space ...
SLIDE_CALL_RE = re.compile(r'\bL\.(?:content|divider|slide)\(')
SRC_ID_RE = re.compile(r"\bid: '([^']*)'")


def _read(path, encoding='utf-8'):
    with open(path, encoding=encoding) as f:
        return f.read()


# ---------- IDs ----------

def source_ids(deck):
    """IDs declared in deck/p*.js, in slide order, read without running the build."""
    ids, errors = [], []
    for f in sorted(glob.glob(os.path.join(deck, 'p[0-9][0-9].js'))):
        s = _read(f)
        calls, found = len(SLIDE_CALL_RE.findall(s)), SRC_ID_RE.findall(s)
        if calls != len(found):
            errors.append(f'{f}: {calls} slide calls but {len(found)} id declarations (every slide needs an id)')
        ids += found
    return ids, errors


def check_ids(ids, src, expect, web):
    errors = []
    seq = [x.get('id') for x in ids]
    if seq != src:
        errors.append('deck/slide_ids.json is stale: its ids differ from deck/p*.js (run: cd deck && node build.js --ids-only)')
    want = expect if expect is not None else len(src)
    if len(seq) != want:
        errors.append(f'deck/slide_ids.json: {len(seq)} slides, expected {want}')
    for k, x in enumerate(ids, 1):
        if x.get('n') != k:
            errors.append(f'deck/slide_ids.json: entry {k} has n={x.get("n")}')
        if not x.get('id'):
            errors.append(f'deck/slide_ids.json: slide {k} has no id')
        elif not ID_RE.match(x['id']):
            errors.append(f'deck/slide_ids.json: slide {k}: malformed id {x["id"]!r} (want pNN-kebab-slug)')
    for i in sorted({i for i in seq if i and seq.count(i) > 1}):
        errors.append(f'deck/slide_ids.json: duplicate id {i} at slides {[k for k, j in enumerate(seq, 1) if j == i]}')
    if web is not None and [d.get('id') for d in web] != seq:
        errors.append('docs/slides.json: ids differ from deck/slide_ids.json (run: python tools/build_web_slides.py)')
    return errors


# ---------- registry ----------

def norm_title(t):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', t or ''))


def similarity(a, b):
    a, b = norm_title(a), norm_title(b)
    return 1.0 if a == b else difflib.SequenceMatcher(None, a, b).ratio()


def latest_title(e):
    r = e.get('retitled') or []
    return r[-1]['title'] if r else e.get('title', '')


def check_registry(ids, reg):
    errors = []
    active = {i: e for i, e in reg.items() if not e.get('retired')}
    current = {x['id'] for x in ids}
    for i, e in reg.items():
        if not e.get('issued') or not e.get('title'):
            errors.append(f'registry: {i} needs "issued" and "title"')
    for x in ids:
        i, t = x['id'], x.get('title', '')
        e = reg.get(i)
        if e is None:
            errors.append(f'slide {x["n"]}: id {i} is not in deck/slide_ids_registry.json (new slide? run: cd deck && node build.js --ids-only --register)')
            continue
        if e.get('retired'):
            errors.append(f'slide {x["n"]}: id {i} was retired on {e["retired"]} and cannot be reused')
            continue
        own = similarity(t, latest_title(e))
        if own == 1.0:
            continue
        if own < TITLE_MIN:
            errors.append(f'slide {x["n"]}: title of {i} changed from {latest_title(e)!r} to {t!r} '
                          f'(similarity {own:.2f} < {TITLE_MIN}); if intended, append {{"date", "title"}} to its "retitled" list')
        best = max(((similarity(t, latest_title(f)), j) for j, f in active.items() if j != i), default=(0, None))
        if best[0] > own:
            errors.append(f'slide {x["n"]}: title {t!r} matches the registered title of {best[1]} better than that of {i} '
                          f'({best[0]:.2f} > {own:.2f}): was the id moved to another slide?')
    for i, e in active.items():
        if i not in current:
            errors.append(f'registry: id {i} ({e["title"]}) is on no slide: restore it, or mark it "retired" (with "reason")')
    return errors


def check_append_only(base, reg):
    """The registry may only grow: compare with the registry at a base revision."""
    errors = []
    for i, b in base.items():
        e = reg.get(i)
        if e is None:
            errors.append(f'registry: id {i} was removed (entries are never removed; mark it "retired" instead)'); continue
        for k in ('issued', 'title', 'retired'):
            if b.get(k) and e.get(k) != b.get(k):
                errors.append(f'registry: {i}.{k} was changed from {b.get(k)!r} to {e.get(k)!r}')
        br, er = b.get('retitled') or [], e.get('retitled') or []
        if er[:len(br)] != br:
            errors.append(f'registry: {i}.retitled was rewritten (only appending is allowed)')
    return errors


def registry_at(ref, root=ROOT):
    """The registry at a git revision: None if the revision does not exist, {} if it has no registry yet."""
    if subprocess.run(['git', '-C', root, 'rev-parse', '--verify', '--quiet', ref + '^{commit}'], capture_output=True).returncode:
        return None
    out = subprocess.run(['git', '-C', root, 'show', f'{ref}:deck/slide_ids_registry.json'], capture_output=True)
    return json.loads(out.stdout.decode('utf-8')) if out.returncode == 0 else {}


# ---------- references ----------

def scan_text(text, known, where):
    """Return (number of references, list of errors) for one text."""
    n, errors = 0, []
    for ln, line in enumerate(text.splitlines(), 1):
        for m in REF_RE.finditer(line):
            body = m.group('body')
            if not re.match(r'[A-Za-z0-9]', body):
                continue  # "slide:" with nothing id-like after it, e.g. the placeholder slide:<id>
            if m.group('kw') != 'slide' or m.group('sp1') or m.group('sp2'):
                if not NEAR_RE.match(body):
                    continue  # ordinary prose such as "Slide: overview"
                n += 1
                errors.append(f'{where}:{ln}: {m.group(0)!r} looks like a slide reference; write it exactly as slide:<id>')
                continue
            n += 1
            rid, _, rest = body.partition('.')
            if not ID_RE.match(rid):
                errors.append(f'{where}:{ln}: malformed slide reference slide:{rid} (the id must be pNN-kebab-slug)')
                continue
            if rest:
                sm = SUFFIX_RE.match('.' + rest)
                if sm and re.match(r'[A-Za-z0-9_-]', ('.' + rest)[sm.end():sm.end() + 1] or '.'):
                    errors.append(f'{where}:{ln}: malformed requirement suffix in slide:{body} (want .R<digits>)')
                    continue
            if rid not in known:
                errors.append(f'{where}:{ln}: unknown slide id slide:{rid}')
        for m in URL_RE.finditer(line):
            if not m.group('frag'):
                continue  # no fragment, or a placeholder such as "#…"
            n += 1
            frag = unquote(m.group('frag'), errors='replace')
            if re.fullmatch(r's\d+', frag):
                errors.append(f'{where}:{ln}: web link by slide number #{frag} shifts when slides are inserted; link #<id> instead')
            elif frag not in known:
                errors.append(f'{where}:{ln}: web link to unknown slide id #{frag}')
    return n, errors


def iter_files(paths, exts):
    for p in paths:
        if os.path.isdir(p):
            for d, dirs, files in os.walk(p):
                dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS)
                for f in sorted(files):
                    if os.path.splitext(f)[1].lower() in exts:
                        yield os.path.join(d, f)
        else:
            yield p


def check_refs(paths, known, exts):
    files, n, errors = 0, 0, []
    for f in iter_files(paths, exts):
        if not os.path.isfile(f):
            errors.append(f'{f}: no such file or directory'); continue
        files += 1
        try:
            text = _read(f, 'utf-8-sig')
        except UnicodeDecodeError:
            errors.append(f'{f}: not UTF-8, cannot be scanned'); continue
        k, e = scan_text(text, known, f)
        n += k; errors += e
    return files, n, errors


# ---------- main ----------

def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    return json.loads(_read(path))


def main(argv=None):
    ap = argparse.ArgumentParser(description='Check stable slide IDs and slide:<id> references (issue #15).')
    ap.add_argument('paths', nargs='*', help='files or directories to scan for references')
    ap.add_argument('--expect', type=int, help='expected number of slides (default: the number declared in deck/p*.js)')
    ap.add_argument('--base', help='git revision whose registry must be a prefix of the current one (append-only check)')
    ap.add_argument('--ext', action='append', default=[], help='extra file extension to scan in directories (e.g. .adoc)')
    ap.add_argument('--root', default=ROOT, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    deck = os.path.join(a.root, 'deck')
    ids = load_json(os.path.join(deck, 'slide_ids.json'), [])
    reg = load_json(os.path.join(deck, 'slide_ids_registry.json'), {})
    web = load_json(os.path.join(a.root, 'docs', 'slides.json'))
    src, errors = source_ids(deck)
    errors += check_ids(ids, src, a.expect, web)
    errors += check_registry(ids, reg)
    if a.base:
        base = registry_at(a.base, a.root)
        if base is None:
            errors.append(f'--base {a.base}: no such git revision')
        else:
            if not base:
                print(f'note: {a.base} has no deck/slide_ids_registry.json yet (nothing to compare)')
            errors += check_append_only(base, reg)
    known = {x['id'] for x in ids}
    retired = sum(1 for e in reg.values() if e.get('retired'))
    print(f'slide ids: {len(known)} unique on {len(ids)} slides; registry: {len(reg)} issued, {retired} retired')
    if a.paths:
        exts = TEXT_EXT | {e if e.startswith('.') else '.' + e for e in a.ext}
        files, n, ref_errors = check_refs(a.paths, known, exts)
        errors += ref_errors
        print(f'references: {n} found in {files} files, {len(ref_errors)} problems')
    for e in errors:
        print('ERROR', e)
    print('FAIL' if errors else 'OK')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
