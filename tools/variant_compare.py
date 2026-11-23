# -*- coding: utf-8 -*-
"""Compare a worked example with a variant of it (an overlay of the changed rows), to show how one design choice moves
the registry, the token inventory, the requirements derived from the issuance profile and the claim_lint result (#4:
sender constraint DPoP vs none in scenario B).

  python tools/variant_compare.py EXAMPLE_DIR OVERLAY.yaml                 # print the comparison (Markdown)
  python tools/variant_compare.py EXAMPLE_DIR OVERLAY.yaml --check DOC.md  # exit 1 when the region of DOC.md differs
  python tools/variant_compare.py EXAMPLE_DIR OVERLAY.yaml --write DOC.md  # rewrite the region of DOC.md
  python tools/variant_compare.py EXAMPLE_DIR OVERLAY.yaml --out DIR       # also keep the merged variant in DIR

The region of the design doc is the text between `<!-- variant:<name>:begin -->` and `<!-- variant:<name>:end -->`
(<name> is the overlay's `name`). Only that text is generated; the rest of the doc is hand-written.

Overlay file (YAML):

  name: sender-none                    # the region name
  description: ...                     # one line, printed above the tables
  files:
    token_types.yaml:                  # a file of the example and what changes in it
      issuance_profile:
        sender_constraint: {value: none, rationale: ...}
      token_types:
        - {id: DPOP, _replace: true, kind: dpop_proof, decision: 却下, ...}
        - {id: AGENT_AT, sender_constraint: none, transport: authorization_bearer, _unset: [jti_policy]}

Merge rules (applied to a copy of the example; the example itself is never written):
  M1  a mapping is merged key by key; a key of the overlay replaces the value of the example, except that a mapping
      under a mapping is merged again (M1). A key whose overlay value is null is removed
  M2  a list whose items are mappings with `id` (claims, token_types, hops) or `event` (catalogue answers) is merged
      row by row with the same key: the overlay row is merged into the example row (M1, one level: the row's own keys
      are replaced, not merged deeper), `_replace: true` replaces the whole row, `_delete: true` removes it,
      `_unset: [keys]` removes keys from the row. A row with a new key is appended
  M3  any other list is replaced as a whole
  M4  the keys `_replace`, `_delete`, `_unset` never reach the merged file; a row that names an unknown key with
      `_delete` or `_unset` is an error (the overlay must not silently do nothing)

The comparison has four parts: the registry rows that change (claims.yaml), the token inventory and issuance profile
(token_types.yaml), the hops, and claim_lint (the findings only on one side, by rule, severity and target) together
with the requirements derived from the issuance profile (templates/registry/issuance_effects.yaml, read by render).
"""
import argparse
import copy
import os
import shutil
import sys
import tempfile

import yaml

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from claim_lint import core, render  # noqa: E402

FILES = ('claims.yaml', 'token_types.yaml', 'hops.yaml', 'catalog_answers.yaml')
ROW_KEYS = ('id', 'event')
CONTROL = ('_replace', '_delete', '_unset')


class OverlayError(ValueError):
    pass


# ------------------------------------------------------------------ merge
def _row_key(item):
    if isinstance(item, dict):
        for k in ROW_KEYS:
            if k in item:
                return k
    return None


def merge(base, over, where='(root)'):
    """Return base with over applied (rules M1..M4). Neither argument is modified."""
    if isinstance(base, dict) and isinstance(over, dict):
        out = copy.deepcopy(base)
        for k, v in over.items():
            if v is None:
                out.pop(k, None)
            elif isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = merge(out[k], v, f'{where}.{k}')
            elif isinstance(v, list) and isinstance(out.get(k), list) and v and all(_row_key(x) for x in v):
                out[k] = merge_rows(out[k], v, f'{where}.{k}')
            else:
                out[k] = copy.deepcopy(v)
        return out
    return copy.deepcopy(over)


def merge_rows(base, over, where):
    key = _row_key(over[0])
    out = [copy.deepcopy(r) for r in base]
    index = {r.get(key): i for i, r in enumerate(out) if isinstance(r, dict)}
    for o in over:
        rid = o.get(key)
        here = f'{where}[{key}={rid}]'
        if o.get('_delete'):
            if rid not in index:
                raise OverlayError(f'{here}: _delete of a row that the example does not have')
            out[index[rid]] = None
            continue
        clean = {k: copy.deepcopy(v) for k, v in o.items() if k not in CONTROL}
        if rid not in index:
            if o.get('_unset'):
                raise OverlayError(f'{here}: _unset on a new row')
            out.append(clean)
            index[rid] = len(out) - 1
            continue
        if o.get('_replace'):
            row = clean
        else:
            row = out[index[rid]]
            for k, v in clean.items():
                if v is None:
                    row.pop(k, None)
                else:
                    row[k] = v
        for k in o.get('_unset') or []:
            if k not in row:
                raise OverlayError(f'{here}: _unset of {k}, which the row does not have')
            row.pop(k)
        out[index[rid]] = row
    return [r for r in out if r is not None]


def _dump_with_header(src_path, doc):
    head = []
    with open(src_path, encoding='utf-8') as f:
        for line in f:
            if line.startswith('#'):
                head.append(line.rstrip('\n'))
            else:
                break
    text = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=1000)
    return '\n'.join(head + ['# variant: generated by tools/variant_compare.py (not committed)', text])


def build_variant(example, overlay, out_dir):
    """Copy the example to out_dir and apply the overlay. Returns out_dir."""
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    shutil.copytree(example, out_dir, ignore=shutil.ignore_patterns('variants', 'schemas'))
    for name, change in (overlay.get('files') or {}).items():
        if name not in FILES:
            raise OverlayError(f'files.{name}: only {", ".join(FILES)} can be changed')
        src = os.path.join(example, name)
        merged = merge(core.load_yaml(src) or {}, change, name)
        with open(os.path.join(out_dir, name), 'w', encoding='utf-8', newline='\n') as f:
            f.write(_dump_with_header(src, merged))
    return out_dir


# ------------------------------------------------------------------ compare
def _short(v, n=70):
    if v is None:
        return '（なし）'
    if isinstance(v, (str, int, float, bool)):
        s = str(v)
    else:
        s = yaml.safe_dump(v, allow_unicode=True, default_flow_style=True, width=10000).strip()
        if s.endswith('...'):
            s = s[:-3].strip()
    s = ' '.join(str(s).split()).replace('|', '／')
    return s if len(s) <= n else s[:n - 1] + '…'


def row_changes(a_rows, b_rows, key='id', skip=()):
    a = {r.get(key): r for r in a_rows or []}
    b = {r.get(key): r for r in b_rows or []}
    out = []
    for rid in list(a) + [x for x in b if x not in a]:
        ra, rb = a.get(rid), b.get(rid)
        if ra == rb:
            continue
        if ra is None:
            out.append((rid, '（行を足した）', '', _short(rb.get('decision'))))
            continue
        if rb is None:
            out.append((rid, '（行を消した）', _short(ra.get('decision')), ''))
            continue
        gone = []
        for k in list(ra) + [x for x in rb if x not in ra]:
            if k in skip or ra.get(k) == rb.get(k):
                continue
            if ra.get('decision') != rb.get('decision') and k not in ('decision', 'rejection_kind', 'carried_in') and k not in rb:
                gone.append(k)  # a column of the adopted row that the rejected row does not have
                continue
            va, vb = ra.get(k), rb.get(k)
            if isinstance(va, dict) and isinstance(vb, dict) and isinstance(va.get('checks'), list) and isinstance(vb.get('checks'), list):
                va, vb = va['checks'], vb['checks']
                k = f'{k}.checks'
            if isinstance(va, list) and isinstance(vb, list) and all(isinstance(x, (str, int)) for x in va + vb):
                minus = [x for x in va if x not in vb]
                plus = [x for x in vb if x not in va]
                out.append((rid, k, _short(va), '・'.join([f'−{x}' for x in minus] + [f'＋{x}' for x in plus]) or _short(vb)))
                continue
            out.append((rid, k, _short(va), _short(vb)))
        if gone:
            out.append((rid, f'（ほかの {len(gone)} 列）', '・'.join(f'`{g}`' for g in gone), '（却下の行には書かない）'))
    return out


def _table(head, rows):
    if not rows:
        return ['（違いなし）']
    lines = ['| ' + ' | '.join(head) + ' |', '| ' + ' | '.join('---' for _ in head) + ' |']
    lines += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
    return lines


def lint_of(design_dir):
    res = core.run(os.path.abspath(design_dir))
    keyed = {}
    for f in res['findings']:
        keyed.setdefault((f['rule'], f['severity'], str(f['target'])), f['message'])
    return res['counts'], keyed, res.get('checked') or {}


def effects_of(design_dir):
    d = render.load_design(design_dir)
    out = {}
    for e in render.issuance_effects(d):
        if not e['holds']:
            continue
        for r in e['requires']:
            out[r['id']] = (render.STATUS.get(r['status'], r['status']), r['text'])
    return out


def _rel(path):
    try:
        return os.path.relpath(path, ROOT).replace(os.sep, '/')
    except ValueError:  # another drive (Windows)
        return os.path.basename(path)


def compare(example, variant, overlay):
    name = overlay.get('name', 'variant')
    A = {n: core.load_yaml(os.path.join(example, n)) or {} for n in FILES if os.path.isfile(os.path.join(example, n))}
    B = {n: core.load_yaml(os.path.join(variant, n)) or {} for n in FILES if os.path.isfile(os.path.join(variant, n))}
    md = [f"変種 `{name}`：{overlay.get('description', '')}", '',
          f"生成：`python tools/variant_compare.py {_rel(example)} {_rel(overlay['_path'])} --write <設計書>`。左が記入例、右が変種。手で直さない。", '']
    ip_a = (A.get('token_types.yaml') or {}).get('issuance_profile') or {}
    ip_b = (B.get('token_types.yaml') or {}).get('issuance_profile') or {}
    ip = [(k, _short((ip_a.get(k) or {}).get('value') if isinstance(ip_a.get(k), dict) else ip_a.get(k)),
           _short((ip_b.get(k) or {}).get('value') if isinstance(ip_b.get(k), dict) else ip_b.get(k)))
          for k in list(ip_a) + [x for x in ip_b if x not in ip_a] if ip_a.get(k) != ip_b.get(k)]
    md += ['**発行方式の選択（issuance_profile）**', ''] + _table(['項目', '記入例', '変種'], ip) + ['']
    ea, eb = effects_of(example), effects_of(variant)
    eff = [(k, ea[k][0] if k in ea else '（条件が成り立たない）', eb[k][0] if k in eb else '（条件が成り立たない）', _short((ea.get(k) or eb.get(k))[1], 60))
           for k in sorted(set(ea) | set(eb)) if ea.get(k, (None,))[0] != eb.get(k, (None,))[0]]
    md += ['**発行方式から導かれる要件（`templates/registry/issuance_effects.yaml`。render の簡易な読み取りで、検査の正は L62）**', '']
    md += _table(['要件', '記入例', '変種', '中身'], eff) + ['']
    tt = row_changes((A.get('token_types.yaml') or {}).get('token_types'), (B.get('token_types.yaml') or {}).get('token_types'),
                     skip=('rationale', 'note', 'assumption', 'revisit_trigger'))
    md += ['**トークン目録（token_types。理由・注記の文の違いは省いた）**', ''] + _table(['ID', '列', '記入例', '変種'], tt) + ['']
    cl = row_changes((A.get('claims.yaml') or {}).get('claims'), (B.get('claims.yaml') or {}).get('claims'),
                     skip=('rationale', 'note', 'assumption', 'revisit_trigger', 'description'))
    md += ['**台帳（claims。理由・注記・意味の文の違いは省いた）**', ''] + _table(['ID', '列', '記入例', '変種'], cl) + ['']
    hp = row_changes((A.get('hops.yaml') or {}).get('hops'), (B.get('hops.yaml') or {}).get('hops'), skip=('note',))
    md += ['**ホップ（hops。注記の違いは省いた）**', ''] + _table(['ID', '列', '記入例', '変種'], hp) + ['']
    ans = row_changes((A.get('catalog_answers.yaml') or {}).get('answers'), (B.get('catalog_answers.yaml') or {}).get('answers'),
                      key='event', skip=('note',))
    qa = (A.get('catalog_answers.yaml') or {}).get('questions') or {}
    qb = (B.get('catalog_answers.yaml') or {}).get('questions') or {}
    ans += [(q, 'questions.needed', _short((qa.get(q) or {}).get('needed')), _short((qb.get(q) or {}).get('needed')))
            for q in sorted(set(qa) | set(qb)) if (qa.get(q) or {}).get('needed') != (qb.get(q) or {}).get('needed')]
    md += ['**カタログへの回答と問い（catalog_answers。注記の違いは省いた）**', ''] + _table(['イベント・問い', '列', '記入例', '変種'], ans) + ['']
    (ca, fa, ka), (cb, fb, kb) = lint_of(example), lint_of(variant)
    md += [f"**claim_lint**：記入例 error {ca['error']}・warn {ca['warn']}・info {ca['info']}、"
           f"変種 error {cb['error']}・warn {cb['warn']}・info {cb['info']}（どちらも profile full。この表は、いまのリポジトリの規則での結果）", '']
    only = [(r, s, t, '記入例だけ', _short(fa[(r, s, t)], 90)) for (r, s, t) in sorted(set(fa) - set(fb))]
    only += [(r, s, t, '変種だけ', _short(fb[(r, s, t)], 90)) for (r, s, t) in sorted(set(fb) - set(fa))]
    only += [(r, s, t, '両方（中身が変わった）', f'{_short(fa[(r, s, t)], 60)} → {_short(fb[(r, s, t)], 60)}')
             for (r, s, t) in sorted(set(fa) & set(fb)) if fa[(r, s, t)] != fb[(r, s, t)]]
    md += _table(['規則', '重大度', '対象', '出る側', '内容'], only)
    moved = [(r, ka.get(r, 0), kb.get(r, 0)) for r in sorted(set(ka) | set(kb)) if ka.get(r, 0) != kb.get(r, 0)]
    if moved:  # rules that report how many places they checked (#6, #18)
        md += ['', '規則が確かめた箇所の数（指摘が無くても、選択で検査の対象が変わる）：'
               + '、'.join(f'{r} {x} → {y}' for r, x, y in moved)]
    return '\n'.join(md) + '\n'


# ------------------------------------------------------------------ region of the design doc
def _markers(name):
    return f'<!-- variant:{name}:begin -->', f'<!-- variant:{name}:end -->'


def region(text, name):
    b, e = _markers(name)
    if text.count(b) != 1 or text.count(e) != 1 or text.index(b) > text.index(e):
        raise OverlayError(f'the doc needs exactly one {b} ... {e} region')
    i, j = text.index(b) + len(b), text.index(e)
    return text[i:j]


def fill(text, name, body):
    b, e = _markers(name)
    region(text, name)
    i, j = text.index(b) + len(b), text.index(e)
    return text[:i] + '\n' + body + text[j:]


def load_overlay(path):
    ov = core.load_yaml(path) or {}
    if not isinstance(ov, dict) or not isinstance(ov.get('files'), dict) or not ov.get('name'):
        raise OverlayError(f'{path}: an overlay needs name and files')
    ov['_path'] = os.path.abspath(path)
    return ov


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('example')
    ap.add_argument('overlay')
    ap.add_argument('--check', metavar='DOC')
    ap.add_argument('--write', metavar='DOC')
    ap.add_argument('--out', metavar='DIR', help='keep the merged variant in DIR (default: a temporary directory)')
    a = ap.parse_args(argv)
    example = os.path.abspath(a.example)
    try:
        ov = load_overlay(a.overlay)
        tmp = None
        if a.out:
            out_dir = os.path.abspath(a.out)
        else:
            tmp = tempfile.mkdtemp(prefix='variant-')
            # the payload schema $id and render use the directory name; keep the example's name
            out_dir = os.path.join(tmp, os.path.basename(example))
        try:
            build_variant(example, ov, out_dir)
            body = compare(example, out_dir, ov)
        finally:
            if tmp:
                shutil.rmtree(tmp, ignore_errors=True)
    except OverlayError as e:
        sys.stderr.write(f'variant_compare: {e}\n')
        return 2
    doc = a.check or a.write
    if not doc:
        sys.stdout.buffer.write(body.encode('utf-8'))
        return 0
    with open(doc, encoding='utf-8', newline='') as f:
        text = f.read()
    nl = '\r\n' if '\r\n' in text else '\n'
    want = '\n' + body
    try:
        have = region(text.replace('\r\n', '\n'), ov['name'])
    except OverlayError as e:
        sys.stderr.write(f'variant_compare: {doc}: {e}\n')
        return 2
    if a.check:
        if have != want:
            import difflib
            diff = difflib.unified_diff(have.splitlines(), want.splitlines(), 'in the doc', 'generated', lineterm='')
            sys.stdout.buffer.write(('\n'.join(diff) + '\n').encode('utf-8'))
            sys.stdout.buffer.write(f'variant_compare: the region variant:{ov["name"]} of {doc} differs from the overlay (run --write)\n'.encode('utf-8'))
            return 1
        sys.stdout.buffer.write(f'variant_compare: {doc} region variant:{ov["name"]} OK\n'.encode('utf-8'))
        return 0
    new = fill(text.replace('\r\n', '\n'), ov['name'], body)
    with open(doc, 'w', encoding='utf-8', newline='') as f:
        f.write(new.replace('\n', nl))
    sys.stdout.buffer.write(f'variant_compare: wrote the region variant:{ov["name"]} of {doc}\n'.encode('utf-8'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
