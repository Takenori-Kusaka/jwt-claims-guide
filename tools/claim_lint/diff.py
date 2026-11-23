# -*- coding: utf-8 -*-
"""claim_lint diff (L10 of #6): compare a design with the same design at an earlier git ref and report the changes that
break consumers (slide:p11-why-govern, slide:p11-change-procedure): a claim removed or renamed, its type, shape or usage
changed, a value removed from its vocabulary, a claim made required (on_missing becomes 拒否, a name added to
required_claims), a token type removed or its typ
changed. A changed description is reported as a candidate (warn): wording fixes are common and harmless.

  python tools/claim_lint diff --base <git ref> DESIGN_DIR [--format table|json]

The base files are read with `git show <ref>:<path>`, so DESIGN_DIR must be inside a git work tree. A file that does not
exist at the base (a new design) has nothing to break. Exit status 1 when there is an error.
"""
import os
import subprocess

import yaml

from .core import ERROR, WARN, INFO, SEVERITIES, Finding, _Loader

ADOPTED = ('採用', '既定どおり')
REMOVABLE = ('sunset',)  # a claim may leave the registry only after its definition reached sunset (slide:p11-change-procedure)


def _git(cwd, *args):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, check=False)


def load_base(design_dir, ref, name):
    top = _git(design_dir, 'rev-parse', '--show-toplevel')
    if top.returncode != 0:
        raise RuntimeError(f'{design_dir} is not inside a git work tree')
    root = top.stdout.decode().strip()
    rel = os.path.relpath(os.path.join(os.path.abspath(design_dir), name), root).replace(os.sep, '/')
    if _git(root, 'rev-parse', '--verify', '--quiet', ref + '^{commit}').returncode != 0:
        raise RuntimeError(f'unknown git ref {ref!r}')
    out = _git(root, 'show', f'{ref}:{rel}')
    if out.returncode != 0:
        return None  # the file does not exist at the base
    return yaml.load(out.stdout.decode('utf-8'), Loader=_Loader) or {}


def _load_head(design_dir, name):
    p = os.path.join(design_dir, name)
    if not os.path.isfile(p):
        return None
    with open(p, encoding='utf-8') as f:
        return yaml.load(f, Loader=_Loader) or {}


def _key(c):
    return (c.get('namespace'), c.get('name'))


def _label(c):
    return (c.get('namespace') or '') + str(c.get('name'))


def compare_claims(base, head):
    out = []
    b_rows = [c for c in (base or {}).get('claims') or [] if c.get('decision') in ADOPTED]
    h_all = (head or {}).get('claims') or []
    h_by_id = {c.get('id'): c for c in h_all}
    h_by_key = {_key(c): c for c in h_all}
    for b in b_rows:
        h = h_by_id.get(b.get('id')) or h_by_key.get(_key(b))
        cid = b.get('id')
        if h is None or h.get('decision') not in ADOPTED:
            how = '台帳から消した' if h is None else f"採否を {h.get('decision')} にした"
            if b.get('status') in REMOVABLE:
                out.append(Finding('L10', INFO, cid, f'{_label(b)} を{how}（前の版で status が sunset なので、互換を壊さない）'))
            else:
                out.append(Finding('L10', ERROR, cid, f"{_label(b)} を{how}。前の版の status は {b.get('status')}。"
                                                      'deprecated（sunset_on）→ sunset の手順を経てから外す'))
            continue
        if _key(h) != _key(b):
            out.append(Finding('L10', ERROR, cid, f'名前を {_label(b)} から {_label(h)} に変えた（改名は削除と追加。新旧を並行して出す）'))
        for k, what in (('type', '型'), ('shape', '形'), ('usage', '用途（usage）')):
            if b.get(k) != h.get(k):
                out.append(Finding('L10', ERROR, cid, f'{_label(b)} の{what}を {b.get(k)!r} から {h.get(k)!r} に変えた'))
        if b.get('on_missing') != '拒否' and h.get('on_missing') == '拒否':
            out.append(Finding('L10', ERROR, cid, f"{_label(b)} を必須にした（on_missing を {b.get('on_missing')!r} から拒否へ）。"
                                                  '古い発行者のトークンを拒否する。発行者を先に直してから受け手を変える'))
        for k in ('description', 'not_meaning'):
            if (b.get(k) or '').strip() != (h.get(k) or '').strip():
                out.append(Finding('L10', WARN, cid, f'{_label(b)} の {k} を変えた（意味の変更の候補。文の直しだけなら問題ない）'))
        bv = [str(v) for v in (b.get('value_vocabulary') or {}).get('values') or []]
        hv = [str(v) for v in (h.get('value_vocabulary') or {}).get('values') or []]
        gone, new = [v for v in bv if v not in hv], [v for v in hv if v not in bv]
        if gone:
            out.append(Finding('L10', ERROR, cid, f"{_label(b)} の語彙（value_vocabulary.values）から {'・'.join(gone)} を消した・変えた。"
                                                  '受け手は値で分岐するので、新旧を並行して出してから消す'))
        if new:
            out.append(Finding('L10', INFO, cid, f"{_label(b)} の語彙に {'・'.join(new)} を足した（知らない値を受け手が無視できるか確かめる）"))
        lost = [t for t in b.get('carried_in') or [] if t not in (h.get('carried_in') or [])]
        if lost and b.get('consumers'):
            out.append(Finding('L10', ERROR, cid, f"{_label(b)} を {'・'.join(lost)} に載せなくなった（受け手 {'・'.join(b['consumers'])} が読んでいる）"))
    return out


def compare_token_types(base, head):
    out = []
    b_rows = [t for t in (base or {}).get('token_types') or [] if t.get('decision') in ADOPTED]
    h_by_id = {t.get('id'): t for t in (head or {}).get('token_types') or []}
    for b in b_rows:
        h, tid = h_by_id.get(b.get('id')), f"token_type {b.get('id')}"
        if h is None or h.get('decision') not in ADOPTED:
            out.append(Finding('L10', ERROR, tid, '採用していたトークン種別を目録から外した（受け手がそのトークンを受けている）'))
            continue
        if b.get('typ') != h.get('typ'):
            out.append(Finding('L10', ERROR, tid, f"typ を {b.get('typ')!r} から {h.get('typ')!r} に変えた（受け手の検証の規則が変わる）"))
        added = [n for n in h.get('required_claims') or [] if n not in (b.get('required_claims') or [])]
        if added:
            out.append(Finding('L10', ERROR, tid, f"required_claims に {'・'.join(added)} を足した（必須化。発行者を先に直す）"))
    return out


def run(design_dir, ref):
    design_dir = os.path.abspath(design_dir)
    findings = []
    for name, cmp in (('claims.yaml', compare_claims), ('token_types.yaml', compare_token_types)):
        base = load_base(design_dir, ref, name)
        if base is None:
            findings.append(Finding('L10', INFO, name, f'{ref} に {name} がない（新しい設計書。壊す相手がない）'))
            continue
        findings += cmp(base, _load_head(design_dir, name))
    counts = {s: sum(1 for f in findings if f['severity'] == s) for s in SEVERITIES}
    return {'design': design_dir, 'base': ref, 'counts': counts, 'findings': findings}


def format_table(res):
    lines = [f"claim_lint diff  design={res['design']}  base={res['base']}", '']
    for f in res['findings']:
        lines.append(f"{f['rule']}  {f['severity']:<5}  {f['target']}  {f['message']}")
    c = res['counts']
    lines += ['', f"error {c['error']}, warn {c['warn']}, info {c['info']}", 'FAIL' if c['error'] else 'OK']
    return '\n'.join(lines)
