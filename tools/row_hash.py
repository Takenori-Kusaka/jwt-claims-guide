# -*- coding: utf-8 -*-
"""Row anchors and row content hashes of a design (#49, for the review mode of #50). The Python twin of the editor's
ClaimsEditor.anchors() / rowHash() (docs/claims/editor.js).

  python tools/row_hash.py DESIGN_DIR [--format table|json]

Anchor: <kind>:<id> for each row of claims (claims[].id), token_types (token_types[].id), hops (hops[].id) and
catalog_answers (answers[].event), and issuance_profile:<key> for each key of token_types.yaml's issuance_profile.
An id written on two or more rows of the same kind has no anchor (listed under `duplicates`).

Hash: SHA-256 (hex) of the RFC 8785 JSON Canonicalization Scheme (JCS) text of the row's value, as UTF-8. The value is
read with claim_lint's YAML loader (PyYAML, YAML 1.1, dates kept as strings, duplicate keys rejected); the editor reads
the same files with the yaml package in YAML 1.1 mode with the same two rules. JCS: object keys sorted by their UTF-16
code units, numbers as ECMAScript writes a double (1.0 -> 1, 1e21 -> 1e+21, 1e-7 -> 1e-7), strings as JSON with only
the required escapes, no whitespace. Comments, key order, quoting and layout of the YAML do not change the hash.
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

ROWS = {'claims': ('claims.yaml', 'claims', 'id'), 'token_types': ('token_types.yaml', 'token_types', 'id'),
        'hops': ('hops.yaml', 'hops', 'id'), 'catalog_answers': ('catalog_answers.yaml', 'answers', 'event')}
_REPR = re.compile(r'^(\d+)(?:\.(\d+))?(?:e([+-]\d+))?$')


def es_number(x):
    """A double written as ECMAScript's Number.prototype.toString writes it (RFC 8785 3.2.2.3)."""
    x = float(x)
    if math.isnan(x) or math.isinf(x):
        raise ValueError('JCS: a number that is not finite')
    if x == 0:
        return '0'
    if x < 0:
        return '-' + es_number(-x)
    m = _REPR.match(repr(x))  # repr is the shortest text that reads back as the same double, as in ECMAScript
    intp, frac, exp = m.group(1), m.group(2) or '', int(m.group(3) or 0)
    allds = intp + frac
    lead = len(allds) - len(allds.lstrip('0'))
    digits = allds.lstrip('0').rstrip('0') or '0'
    n = len(intp) + exp - lead  # the value is 0.<digits> x 10^n
    k = len(digits)
    if k <= n <= 21:
        return digits + '0' * (n - k)
    if 0 < n <= 21:
        return digits[:n] + '.' + digits[n:]
    if -6 < n <= 0:
        return '0.' + '0' * (-n) + digits
    e = n - 1
    return digits[0] + ('.' + digits[1:] if k > 1 else '') + 'e' + ('+' if e >= 0 else '-') + str(abs(e))


_LONE = re.compile('[\ud800-\udfff]')


def _jcs_str(s):
    # RFC 8785 works on I-JSON: a string must be valid Unicode. A pair of surrogates that PyYAML keeps as two code points
    # ("😀" written as two escapes) is joined first; a surrogate left alone is refused, as editor.js does
    s = s.encode('utf-16', 'surrogatepass').decode('utf-16', 'surrogatepass')
    if _LONE.search(s):
        raise ValueError('JCS: a string with a lone surrogate (not I-JSON)')
    return json.dumps(s, ensure_ascii=False)


def _key(k):
    """A mapping key as the editor gets it (the yaml package turns a non-string key into its text)."""
    if isinstance(k, str):
        return k
    if k is True or k is False:
        return 'true' if k else 'false'
    if k is None:
        return ''
    if isinstance(k, float) and (math.isnan(k) or math.isinf(k)):
        # .inf / .nan as a key: the yaml package writes String(Infinity) (#50, the PR #51 check). A value of .inf is
        # still refused (jcs); only a key is turned into its text, as the editor does
        return 'NaN' if math.isnan(k) else 'Infinity' if k > 0 else '-Infinity'
    if isinstance(k, (int, float)):
        return es_number(k)
    return str(k)


def jcs(v):
    """RFC 8785 canonical JSON text of a value (dict, list, str, int, float, bool, None)."""
    if v is None:
        return 'null'
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if isinstance(v, (int, float)):
        return es_number(v)
    if isinstance(v, str):
        return _jcs_str(v)
    if isinstance(v, (list, tuple)):
        return '[' + ','.join(jcs(x) for x in v) + ']'
    if isinstance(v, dict):
        items = {_key(k): x for k, x in v.items()}
        return '{' + ','.join(_jcs_str(k) + ':' + jcs(items[k])
                              for k in sorted(items, key=lambda s: s.encode('utf-16-be'))) + '}'
    raise TypeError(f'JCS: cannot write {type(v).__name__}')


def sha256_hex(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def load(design_dir):
    from claim_lint.core import load_yaml
    out = {}
    for kind, (fname, _, _) in ROWS.items():
        p = os.path.join(design_dir, fname)
        out[kind] = (load_yaml(p) or {}) if os.path.isfile(p) else {}
    return out


def anchors(docs):
    """[(anchor, kind, id, row)] in file order, and the set of anchors written twice or more."""
    out = []
    for kind, (_, key, idk) in ROWS.items():
        doc = docs.get(kind)
        rows = doc.get(key) if isinstance(doc, dict) else None
        for r in rows if isinstance(rows, list) else []:
            if isinstance(r, dict) and r.get(idk) is not None:
                rid = r[idk] if isinstance(r[idk], str) else _key(r[idk])
                out.append((f'{kind}:{rid}', kind, rid, r))
    tt = docs.get('token_types')
    prof = tt.get('issuance_profile') if isinstance(tt, dict) else None
    if isinstance(prof, dict):
        for k, v in prof.items():
            out.append((f'issuance_profile:{_key(k)}', 'issuance_profile', _key(k), v))
    seen = {}
    for a in out:
        seen[a[0]] = seen.get(a[0], 0) + 1
    return out, {a for a, n in seen.items() if n > 1}


def row_hashes(design_dir):
    """{'hashes': {anchor: sha256 hex}, 'duplicates': [anchor], 'errors': {anchor: why there is no hash}}."""
    rows, dup = anchors(load(design_dir))
    hashes, errors = {}, {}
    for a, _, _, r in rows:
        if a in dup:
            continue
        try:
            hashes[a] = sha256_hex(jcs(r))
        except (ValueError, TypeError) as e:
            errors[a] = str(e)
    return {'hashes': hashes, 'duplicates': sorted(dup), 'errors': errors}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('design_dir')
    ap.add_argument('--format', choices=('table', 'json'), default='table')
    a = ap.parse_args(argv)
    res = row_hashes(a.design_dir)
    if a.format == 'json':
        text = json.dumps(res, ensure_ascii=False, indent=1)
    else:
        text = '\n'.join(f'{h}  {k}' for k, h in res['hashes'].items())
        if res['errors']:
            text += '\n' + '\n'.join(f'(no hash: {why})  {k}' for k, why in res['errors'].items())
        if res['duplicates']:
            text += '\n' + '\n'.join(f'(duplicate, no anchor)  {k}' for k in res['duplicates'])
    sys.stdout.buffer.write((text + '\n').encode('utf-8'))
    return 1 if res['errors'] else 0


if __name__ == '__main__':
    sys.exit(main())
