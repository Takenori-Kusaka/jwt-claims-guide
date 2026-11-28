# -*- coding: utf-8 -*-
"""The calibration sets of #12: designs with seeded errors, their clean twins (controls), and the answer keys.

  python tools/calibration_check.py check                    # the checks below (CI)
  python tools/calibration_check.py materialize DESIGN OUT   # the design as a reviewer gets it: plain file names, no marker
  python tools/calibration_check.py packet DESIGN OUT [--seed S]   # the whole packet of one review session (protocol.md 6.)
  python tools/calibration_check.py render DESIGN            # render --write at the neutral path designs/target, written back
  python tools/calibration_check.py mark DIR (--seeded | --control)   # add the markers (used once, when the set is made)
  python tools/calibration_check.py distribution SET         # the difficulty x channel x salience table of a set's key

There are two sets. Set 1 (the first measurement, frozen): research/template-design/calibration/{seeded-a,seeded-b,
control-a,control-b}, with protocol.md, seeded_errors.yaml, expected_lint.yaml and commitments.sha256 beside them.
Set 2 (#82, the re-measurement): research/template-design/calibration/set2/{seeded-c,seeded-d,control-c,control-d}, with its
own protocol.md, seeded_errors.yaml, expected_lint.yaml and commitments.sha256 in set2/. DESIGN is one of the eight names.

The files of a seeded design carry `.broken` in their names and the marker 「意図的に誤りを含む教材。設計に使わない」 inside
(templates/CONTRIBUTING.md 4., 意図的に誤りを含む教材); the controls carry 「測定の対照に使う教材。設計に使わない」. The marker is one exact
line (Markdown: after the first heading, with a blank line before it; YAML: line 2; JSON: line 2 as a "_warning" member), so that
materialize removes it byte for byte: the materialized design is what claim_lint, render --check and the reviewer see.

claim_lint and render write the design's path (relative to the repository) into design.md 1. and into the $id of the payload
schemas. So every design is staged at the same neutral path, designs/target (git-ignored), to be rendered, checked and handed
to a reviewer: nothing in a design tells which of the eight it is.

Checks (errors), for every set:
  C1  every file of every design carries its marker; seeded files have `.broken` in the name, control files do not
  C2  claim_lint (Full profile, --also-scan design.md) on the staged design gives the counts and the warn rows of the set's
      expected_lint.yaml (error 0 for all: a reviewer returns a design with a lint error unread)
  C3  render --check passes on the staged design. Set 1 was rendered and measured before the render fix of #82 (BD5: a
      closed vocabulary of an object claim became an enum on "type": "object"); its files stay as measured (C6). For set 1
      only, the files of RENDER_DRIFT may differ, and only if the current render writes exactly the recorded sha256
  C4  every location of the set's seeded_errors.yaml resolves: the file exists in the materialized seeded design, a YAML row
      id exists in that file, a quoted phrase occurs in that file, a heading exists; every error has a core
  C5  each seeded design and its control show the same traits in review_triage.py --design (the controls are twins)
  C7  a packet built for each design (in a temporary directory outside the repository) passes P1-P3: it holds only the
      materials (and the set's extra materials), ci-result.txt, sheet.md and the materialized design; no file has the
      content of another file of calibration/; no file names a design, the calibration directory or a marker
  C6  the files listed in the set's commitments.sha256 have those sha256 (the targets and the key fixed before measuring;
      CRLF is read as LF, so a Windows checkout gives the same value as git and CI)
  C6 also reads lines `<sha> *@<path>` (from the repository root): set 2 pins the packet materials (templates/review);
      packet refuses to build a set-2 packet when one of them changed (set2/protocol.md S12)
Set 2 only (its protocol.md 3.1, 3.2 and 9.):
  C8  the difficulty of each error follows from signpost x span; the salience facts are what the materialized seeded design
      shows (copies = the lines that hold salience_phrase; masked_by = the errors at the same primary location that are at
      least as copied) and the salience follows from them; the distribution block of set2/protocol.md is the key's table;
      an error whose first channel question had its hint changed by #80 (or whose channel is lint) carries hint_derived,
      and every hint_derived error has a hint_note
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
SETS = {
    'set1': {'dir': CAL, 'controls': {'seeded-a': 'control-a', 'seeded-b': 'control-b'}, 'extra': ()},
    # set 2 adds the kind-distinction note to the packet (set2/protocol.md, revision S2)
    'set2': {'dir': os.path.join(CAL, 'set2'), 'controls': {'seeded-c': 'control-c', 'seeded-d': 'control-d'},
             'extra': ('packet/kind_tell.md',)},
}
CONTROLS = {s: c for v in SETS.values() for s, c in v['controls'].items()}
SEEDED = tuple(CONTROLS)
DESIGNS = SEEDED + tuple(CONTROLS.values())
SET_OF = {d: name for name, v in SETS.items() for pair in v['controls'].items() for d in pair}
M_SEEDED = '意図的に誤りを含む教材。設計に使わない'
M_CONTROL = '測定の対照に使う教材。設計に使わない'
MATERIALS = ('templates/review/short_list.md', 'templates/review/perspectives.md', 'templates/review/decision_tree.md')
MATERIAL_DIRS = ('templates/review/contrasts',)
# C3 for set 1: the payload schemas that the render fix of #82 (BD5) writes differently. Set 1 keeps the files it was
# measured with (commitments.sha256); the current render must give exactly these sha256 (CRLF read as LF), nothing else.
RENDER_DRIFT = {
    'seeded-b': {
        'schemas/TXN_OPS.issuer.schema.json': '32215f43092d3cb433bda7bcb35322eac62c533af8fe98e5592337eb905f2757',
        'schemas/TXN_TOKEN.issuer.schema.json': '1519b9f227ca214d2a8fc792788b95689458127c60976dc4bc8c33c53f365c05',
    },
    'control-b': {
        'schemas/MSG_CTX.issuer.schema.json': '6d89a30c9071417701e00d5705092bf365351f1e07094821385e30e8c3800613',
        'schemas/TXN_OPS.issuer.schema.json': '8cbb841599b36169a6f50904a23405dcc662aa548415ce51bdf73164e7b2947d',
        'schemas/TXN_TOKEN.issuer.schema.json': '1e56b7420e5999a3b74912f8e3097c970221abd39fd3b768e79f11b8d44f81a8',
    },
}
DIFFICULTY = {('P1', '1'): 'easy', ('P1', '2+'): 'medium', ('P2', '1'): 'medium', ('P2', '2+'): 'hard',
              ('なし', '1'): 'hard', ('なし', '2+'): 'hard'}
HINT_DERIVED = ('A01', 'A03', 'A17', 'B02', 'B03', 'B05', 'B14')  # set-1 errors whose core the #80 hints restate
# set2/protocol.md 3.2 (revision S10): an error whose first channel question is one whose hint #80 (PR #84) changed, or whose
# channel is lint (short_list.md 3. got a hint), must carry hint_derived
HINT_QUESTIONS = ('q-revocation-delivery', 'q-long-running', 'q-idp-diff-absorbed', 'q-db-context-writers')
DIST_BEGIN, DIST_END = '<!-- calibration:distribution:begin -->', '<!-- calibration:distribution:end -->'


def design_dir(design):
    return os.path.join(SETS[SET_OF[design]]['dir'], design)


def set_file(design_or_set, name):
    s = SET_OF.get(design_or_set, design_or_set)
    return os.path.join(SETS[s]['dir'], name)


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
    src = design_dir(design)
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
                text, had = strip_marker(f.read().replace('\r\n', '\n'), ext, marker)
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
        src = design_dir(design)
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


def sha256_lf(path):
    """sha256 of the file with CRLF read as LF (what git stores; a Windows checkout with core.autocrlf gives CRLF)."""
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read().replace(b'\r\n', b'\n')).hexdigest()


def row_ids(text):
    return set(re.findall(r'^\s*-?\s*\{?\s*(?:id|event):\s*["\']?([^"\'\s,}#]+)', text, re.M))


def render_drift(design, materialized):
    """C3 for a design of set 1 whose render --check fails: render --write the staged copy, and accept only the files of
    RENDER_DRIFT, each with the recorded sha256. Returns the problems (empty when the drift is exactly the recorded one)."""
    allowed = RENDER_DRIFT.get(design) if SET_OF[design] == 'set1' else None
    if not allowed:
        return ['render --check failed']
    rc, o, e = run(['tools/claim_lint', 'render', TARGET, '--write'])
    if rc:
        return [f'render --write failed: {(o + e).strip()[-300:]}']
    problems = []
    seen = set()
    for p in files_of(TARGET):
        rel = os.path.relpath(p, TARGET).replace(os.sep, '/')
        if rel == STAMP:
            continue
        before = os.path.join(materialized, rel)
        if os.path.isfile(before) and sha256_lf(before) == sha256_lf(p):
            continue
        seen.add(rel)
        if rel not in allowed:
            problems.append(f'{rel} differs from what render writes (not a recorded drift)')
        elif allowed[rel] != sha256_lf(p):
            problems.append(f'{rel}: render writes sha256 {sha256_lf(p)}, RENDER_DRIFT records {allowed[rel]}')
    for rel in sorted(set(allowed) - seen):
        problems.append(f'{rel}: recorded in RENDER_DRIFT but render writes it unchanged (remove the entry)')
    return problems


def load_key(set_name):
    p = os.path.join(SETS[set_name]['dir'], 'seeded_errors.yaml')
    if not os.path.isfile(p):
        return None
    with open(p, encoding='utf-8') as f:
        return yaml.safe_load(f)


def loc_key(loc):
    """The place a location names, for masked_by: the file and the row, or the file and the heading/section."""
    return (loc.get('file'), loc.get('row') or loc.get('heading') or loc.get('section'))


def salience_facts(errors, mats):
    """copies, masked_by and salience of each error, from the materialized seeded designs (set2/protocol.md 3.1)."""
    facts = {}
    for err in errors:
        d = mats.get(err['design'])
        copies = 0
        phrase = err.get('salience_phrase')
        if err.get('form') == 'present' and phrase and d:
            for p in files_of(d):
                if os.path.basename(p) == STAMP:
                    continue
                with open(p, encoding='utf-8', errors='replace') as f:
                    copies += sum(1 for line in f if phrase in line)
        facts[err['id']] = {'copies': copies}
    for err in errors:
        mine = facts[err['id']]['copies']
        place = loc_key(err['locations'][0]) if err.get('locations') else None
        masked = []
        for o in errors:
            if o['id'] == err['id'] or o['design'] != err['design'] or not o.get('locations') or o.get('form') != 'present':
                continue
            if loc_key(o['locations'][0]) == place and facts[o['id']]['copies'] >= mine:
                masked.append(o['id'])
        f = facts[err['id']]
        f['masked_by'] = sorted(masked)
        f['salience'] = 'low' if (err.get('form') == 'absent' or masked or f['copies'] <= 1) else 'high'
    return facts


def distribution(key):
    """The table of set2/protocol.md 9.: difficulty x channel, each cell with its salience split."""
    chans = [('short_list', '1', 'short_list（優先 1）'), ('short_list', '2', 'short_list（優先 2）'), ('lint', None, 'lint'),
             ('open_prompt', None, 'open_prompt'), ('none', None, 'none')]
    errs = key.get('errors') or []

    def col(e):
        if e['channel'] == 'short_list':
            return ('short_list', str(e.get('channel_priority')))
        return (e['channel'], None)
    lines = ['| 難しさ ＼ 経路 | ' + ' | '.join(c[2] for c in chans) + ' | 計 |', '| --- |' + ' --- |' * (len(chans) + 1)]
    for diff in ('easy', 'medium', 'hard', None):
        cells = []
        rows = [e for e in errs if diff is None or e['difficulty'] == diff]
        for c in chans + [None]:
            sel = [e for e in rows if c is None or col(e) == c[:2]]
            hi = sum(1 for e in sel if e['salience'] == 'high')
            cells.append(f'{len(sel)}（高 {hi}・低 {len(sel) - hi}）' if sel else '0')
        lines.append(f'| {diff or "計"} | ' + ' | '.join(cells) + ' |')
    kinds, sev, form = {}, {}, {}
    for e in errs:
        kinds[e['kind']] = kinds.get(e['kind'], 0) + 1
        sev[e['severity']] = sev.get(e['severity'], 0) + 1
    per = {}
    for e in errs:
        per.setdefault(e['design'], {}).setdefault(e['difficulty'], 0)
        per[e['design']][e['difficulty']] += 1
    lines.append('')
    lines.append('- 設計書ごと：' + '、'.join(
        f'{d} は ' + '・'.join(f'{k} {per[d].get(k, 0)}' for k in ('easy', 'medium', 'hard')) + f'（{sum(per[d].values())} 件）'
        for d in sorted(per)))
    lines.append('- 種別：' + '・'.join(f'{k} {v}' for k, v in sorted(kinds.items(), key=lambda kv: -kv[1])))
    lines.append('- 重大度：' + '・'.join(f'{k} {sev.get(k, 0)}' for k in ('Blocker', 'Major', 'Minor') if sev.get(k)))
    absent = sorted(e['id'] for e in errs if e.get('form') == 'absent')
    cps = {e['id']: e.get('copies', 0) for e in errs}
    more = sorted(e['id'] for e in errs if any(cps[o] > cps[e['id']] for o in e.get('masked_by') or []))
    equal = sorted(e['id'] for e in errs if e.get('masked_by') and e['id'] not in more)
    hint = sorted(e['id'] for e in errs if e.get('hint_derived'))
    lines.append(f'- あるべきものが無い形（form: absent）：{len(absent)} 件（{"・".join(absent) or "なし"}）')
    lines.append(f'- 同じ場所に、より写される誤りがある形（masked_by に copies がより多い誤り）：{len(more)} 件（{"・".join(more) or "なし"}）')
    lines.append(f'- 同じ場所に、同じ数だけ写される誤りがある形（masked_by が同数だけ）：{len(equal)} 件（{"・".join(equal) or "なし"}）')
    lines.append(f'- 初回の手がかりから来た型（hint_derived。再現率を分けて出す）：{len(hint)} 件（{"・".join(hint) or "なし"}）')
    return '\n'.join(lines)


def check_salience(key, mats, protocol_path, errors):
    errs = key.get('errors') or []
    for e in errs:
        want = DIFFICULTY.get((e.get('signpost'), str(e.get('span'))))
        if e.get('difficulty') != want:
            errors.append(f"C8 {e['id']}: difficulty {e.get('difficulty')} but signpost x span gives {want}")
        if e.get('form') not in ('present', 'absent'):
            errors.append(f"C8 {e['id']}: form must be present or absent")
        if e.get('form') == 'present' and not e.get('salience_phrase'):
            errors.append(f"C8 {e['id']}: a present error needs a salience_phrase")
        if e.get('channel') == 'short_list' and str(e.get('channel_priority')) not in ('1', '2'):
            errors.append(f"C8 {e['id']}: channel short_list needs channel_priority 1 or 2")
        first = (e.get('channel_question') or [None])[0]
        if (first in HINT_QUESTIONS or e.get('channel') == 'lint') and not e.get('hint_derived'):
            errors.append(f"C8 {e['id']}: channel {e.get('channel')} {first or ''} has a hint changed by #80; hint_derived is required")
        if e.get('hint_derived') and not e.get('hint_note'):
            errors.append(f"C8 {e['id']}: hint_derived needs a hint_note (what differs from the set-1 error)")
        for h in e.get('hint_derived') or []:
            if h not in HINT_DERIVED:
                errors.append(f"C8 {e['id']}: hint_derived {h} is not one of {', '.join(HINT_DERIVED)}")
    facts = salience_facts(errs, mats)
    for e in errs:
        f = facts[e['id']]
        if e.get('form') == 'present' and f['copies'] == 0:
            errors.append(f"C8 {e['id']}: salience_phrase 「{e.get('salience_phrase')}」 occurs nowhere in {e['design']}")
        for k in ('copies', 'masked_by', 'salience'):
            got = e.get(k) if k != 'masked_by' else sorted(e.get(k) or [])
            if got != f[k]:
                errors.append(f"C8 {e['id']}: {k} is {got!r} in the key, the design gives {f[k]!r}")
    if not os.path.isfile(protocol_path):
        errors.append(f'C8 {os.path.relpath(protocol_path, ROOT)} is missing')
        return
    with open(protocol_path, encoding='utf-8') as f:
        text = f.read().replace('\r\n', '\n')
    m = re.search(re.escape(DIST_BEGIN) + r'\n(.*?)\n' + re.escape(DIST_END), text, re.S)
    if not m:
        errors.append('C8 the distribution block of set2/protocol.md is missing')
    elif m.group(1).strip() != distribution(key).strip():
        errors.append('C8 the distribution block of set2/protocol.md differs from the key '
                      '(python tools/calibration_check.py distribution set2)')


def check_commitments(set_name, errors):
    base = SETS[set_name]['dir']
    tag = '' if set_name == 'set1' else f'{set_name} '
    cpath = os.path.join(base, 'commitments.sha256')
    if not os.path.isfile(cpath):
        errors.append(f'C6 {tag}commitments.sha256 is missing')
        return
    n = 0
    for line in open(cpath, encoding='utf-8'):
        m = re.match(r'([0-9a-f]{64}) \*(\S+)$', line.strip())
        if not m:
            continue
        want, rel = m.groups()
        p = os.path.join(ROOT, rel[1:]) if rel.startswith('@') else os.path.join(base, rel)  # @: from the repository root
        got = sha256_lf(p) if os.path.isfile(p) else 'missing'
        if got != want:
            errors.append(f'C6 {tag}{rel}: sha256 {got} differs from commitments.sha256 ({want})')
        n += 1
    if not n:
        errors.append(f'C6 {tag}commitments.sha256 lists no file')


def check(errors, sets=None):
    sets = [s for s in (sets or SETS) if s == 'set1' or os.path.isdir(SETS[s]['dir'])]
    for set_name in sets:
        conf = SETS[set_name]
        designs = tuple(conf['controls']) + tuple(conf['controls'].values())
        exp_path = os.path.join(conf['dir'], 'expected_lint.yaml')
        expected = {}
        if os.path.isfile(exp_path):
            with open(exp_path, encoding='utf-8') as f:
                expected = yaml.safe_load(f) or {}
        else:
            errors.append(f'C2 {set_name}: expected_lint.yaml is missing')
        key = load_key(set_name)
        if key is None:
            errors.append(f'C4 {set_name}: seeded_errors.yaml is missing')
        with tempfile.TemporaryDirectory() as tmp:
            mats, trait_rows = {}, {}
            try:
                for d in designs:
                    src = design_dir(d)
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
                    trait_rows[d] = traits(TARGET)
                    mats[d] = os.path.join(tmp, d)
                    shutil.copytree(TARGET, mats[d], ignore=shutil.ignore_patterns(STAMP))
                    rc, o, e = run(['tools/claim_lint', 'render', TARGET, '--check'])
                    if rc:
                        for problem in render_drift(d, mats[d]):
                            errors.append(f'C3 {d}: {problem}: {(o + e).strip()[-300:]}'
                                          if problem == 'render --check failed' else f'C3 {d}: {problem}')
            finally:
                unstage()
            for err in (key or {}).get('errors', []):
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
                    if 'heading' in loc and not re.search(r'^#{2,4} ' + re.escape(loc['heading']) + r'$', text, re.M):
                        errors.append(f"C4 {err['id']}: heading 「{loc['heading']}」 not found in {loc['file']}")
                if not err.get('core'):
                    errors.append(f"C4 {err['id']}: no core (the one sentence a finding must state)")
            for s, c in conf['controls'].items():
                if s in trait_rows and c in trait_rows and trait_rows[s] != trait_rows[c]:
                    errors.append(f'C5 {s} and {c} show different traits in review_triage.py --design')
            if set_name != 'set1' and key is not None:
                check_salience(key, mats, os.path.join(conf['dir'], 'protocol.md'), errors)
        for d in designs:
            if not os.path.isdir(design_dir(d)):
                continue
            with tempfile.TemporaryDirectory() as tmp:
                try:
                    packet(d, os.path.join(tmp, 'packet'), '12')
                except SystemExit as e:
                    errors.append(f'C7 {d}: {e}')
        check_commitments(set_name, errors)
    return errors


def inside(path, root):
    path, root = os.path.normcase(os.path.realpath(path)), os.path.normcase(os.path.realpath(root))
    return path == root or path.startswith(root + os.sep)


def extra_materials(design):
    """The set's own packet files (set 2: the kind-distinction note), as (source path, name in the packet)."""
    conf = SETS[SET_OF[design]]
    return [(os.path.join(conf['dir'], rel), os.path.basename(rel)) for rel in conf['extra']]


def packet_errors(out, design):
    """P1-P3 of protocol.md 6.: the packet holds exactly the listed files, and nothing of calibration/ but the design
    (and, for set 2, the set's own packet files)."""
    errors = []
    extras = extra_materials(design)
    allowed = {os.path.basename(m) for m in MATERIALS} | {'ci-result.txt', 'sheet.md'} | {n for _, n in extras}
    extra_src = {os.path.normcase(os.path.realpath(p)) for p, _ in extras}
    contrasts = set(os.listdir(os.path.join(ROOT, MATERIAL_DIRS[0])))
    own = {}
    with tempfile.TemporaryDirectory() as tmp:
        materialize(design, tmp)
        for p in files_of(tmp):
            own[os.path.relpath(p, tmp).replace(os.sep, '/')] = sha256_lf(p)
    mine = os.path.normcase(os.path.realpath(design_dir(design)))
    others = {}
    for p in files_of(CAL):
        rp = os.path.normcase(os.path.realpath(p))
        if rp.startswith(mine + os.sep) or rp in extra_src:
            continue
        others[sha256_lf(p)] = os.path.relpath(p, CAL).replace(os.sep, '/')
    for d in DESIGNS:
        if d == design or not os.path.isdir(design_dir(d)):
            continue
        with tempfile.TemporaryDirectory() as tmp:
            materialize(d, tmp)
            for p in files_of(tmp):
                others.setdefault(sha256_lf(p), f'{d} (materialized) {os.path.relpath(p, tmp)}')
    found_design = False
    for p in files_of(out):
        rel = os.path.relpath(p, out).replace(os.sep, '/')
        h = sha256_lf(p)
        if rel.startswith('designs/target/'):
            sub = rel[len('designs/target/'):]
            found_design |= sub == 'design.md'
            if own.get(sub) != h:
                errors.append(f'P1 {rel}: not a file of the materialized design')
            continue
        if not (rel in allowed or (rel.startswith('contrasts/') and rel[len('contrasts/'):] in contrasts)):
            errors.append(f'P1 {rel}: not a file the packet may hold (protocol.md 6.)')
        if h in others:
            errors.append(f'P2 {rel}: same content as {others[h]} (another file of calibration/)')
    words = DESIGNS + ('template-design/calibration', 'calibration/set2', M_SEEDED, M_CONTROL, '.broken')
    for p in files_of(out):
        rel = os.path.relpath(p, out).replace(os.sep, '/')
        with open(p, encoding='utf-8', errors='replace') as f:
            t = f.read()
        for word in words:
            if word in t:
                errors.append(f'P3 {rel}: contains 「{word}」')
    if not found_design:
        errors.append('P1 designs/target/design.md is missing')
    return errors


def material_files():
    """The packet materials as paths from the repository root: the listed files and every file of the listed directories."""
    files = list(MATERIALS)
    for md in MATERIAL_DIRS:
        for p in files_of(os.path.join(ROOT, md)):
            files.append(os.path.relpath(p, ROOT).replace(os.sep, '/'))
    return sorted(files)


def pinned_materials(design, cpath=None):
    """The materials a set pins in its commitments.sha256 (lines `<sha> *@<path from the repository root>`). When a set pins
    any, the packet materials must be exactly the pinned files (none added or removed) with the pinned sha256, or a packet
    built now is not the packet the set was fixed with (set2/protocol.md S12)."""
    cpath = cpath or os.path.join(SETS[SET_OF[design]]['dir'], 'commitments.sha256')
    if not os.path.isfile(cpath):
        return []
    pins = {}
    for line in open(cpath, encoding='utf-8'):
        m = re.match(r'([0-9a-f]{64}) \*@(\S+)$', line.strip())
        if m:
            pins[m.group(2)] = m.group(1)
    if not pins:
        return []
    problems = []
    actual = set(material_files())
    for rel in sorted(actual - set(pins)):
        problems.append(f'{rel} is a packet material that is not pinned (added after the set was fixed)')
    for rel, want in sorted(pins.items()):
        p = os.path.join(ROOT, rel)
        if rel not in actual and not os.path.isfile(p):
            problems.append(f'{rel} is pinned but missing (removed after the set was fixed)')
        elif rel not in actual:
            problems.append(f'{rel} is pinned but is not a packet material')
        elif sha256_lf(p) != want:
            problems.append(f'{rel} differs from the pinned sha256')
    return problems


def packet(design, out, seed):
    """The packet of one review session: the materials, the design at designs/target, the CI result and the sheet.
    The label of the session is kept in the record only (protocol.md 6.), never in the packet. OUT must be a new or
    empty directory outside the repository: a session opened in a clone could reach the answer key."""
    if inside(out, ROOT):
        raise SystemExit(f'{out} is inside the repository; give an empty directory outside it (protocol.md 6.)')
    if os.path.exists(out) and os.listdir(out):
        raise SystemExit(f'{out} is not empty')
    pinned = pinned_materials(design)  # before anything is written: a refused packet leaves no partial directory
    if pinned:
        raise SystemExit(f'packet: {"; ".join(pinned)}; build the packet from the commit recorded in the set README (固定の記録)')
    os.makedirs(out, exist_ok=True)
    for m in MATERIALS:
        shutil.copyfile(os.path.join(ROOT, m), os.path.join(out, os.path.basename(m)))
    for md in MATERIAL_DIRS:
        shutil.copytree(os.path.join(ROOT, md), os.path.join(out, os.path.basename(md)), dirs_exist_ok=True)
    for src, name in extra_materials(design):
        shutil.copyfile(src, os.path.join(out, name))
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
    errors = packet_errors(out, design)
    if errors:
        raise SystemExit(f'packet: {len(errors)} error(s); do not hand this packet to a reviewer: ' + '; '.join(errors[:5]))


def main(argv=None):
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description='The calibration sets of #12 (seeded designs, controls, answer keys).')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('check')
    p.add_argument('--set', choices=tuple(SETS), action='append', help='check only these sets (default: all)')
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
    p = sub.add_parser('distribution')
    p.add_argument('set', choices=tuple(s for s in SETS if s != 'set1'))
    a = ap.parse_args(argv)
    if a.cmd == 'check':
        errors = check([], a.set)
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
        print(f'packet: OK ({sum(1 for _ in files_of(a.out))} files in {a.out})')
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
    if a.cmd == 'distribution':
        key = load_key(a.set)
        if key is None:
            raise SystemExit(f'{a.set}: seeded_errors.yaml is missing')
        with tempfile.TemporaryDirectory() as tmp:
            mats = {}
            try:
                for s in SETS[a.set]['controls']:
                    stage(s)
                    mats[s] = os.path.join(tmp, s)
                    shutil.copytree(TARGET, mats[s], ignore=shutil.ignore_patterns(STAMP))
            finally:
                unstage()
            facts = salience_facts(key.get('errors') or [], mats)
        for e in key.get('errors') or []:
            e.update(facts[e['id']])
        print(DIST_BEGIN)
        print(distribution(key))
        print(DIST_END)
        return 0


if __name__ == '__main__':
    sys.exit(main())
