# -*- coding: utf-8 -*-
"""Compare a worked example's registry with the pinned casestudy (templates/casestudy-mapping.md 7. and 8., #3).

  python tools/casestudy_check.py [EXAMPLE_DIR] [--cache DIR] [--offline]

Checks (all errors):
  ORG   every claim row that refers to an ORG row of the casestudy claim list (catalog/catalog.json) has the same name
        (namespace + '.' + name) and the same type and shape. Name and type are owned by the casestudy.
  PIN   catalog_refs and casestudy_commit name the pinned commit (tools/casestudy_pin.json), and every downloaded file
        has the sha256 recorded there (the content cannot change under the same pin).
  CARRY for every catalog_ref (CLM / ORG) of the example, the example carries the claim (採用・既定どおり) exactly when the
        casestudy judgement of the scenario carries it (必須・採用・条件付き採用). Every disagreement is listed in
        templates/casestudy-deviations.yaml with kind carry, and every listed carry deviation is a real disagreement.
        A kind condition deviation must point at a row the casestudy judges 条件付き採用 and the example carries.
        Whether the condition is used differently is a reading of the text and is not checked by machine.

The files are fetched from raw.githubusercontent.com at the full commit SHA (public repository) and cached in --cache
(default: a .casestudy-cache directory next to this file, ignored by Git). --offline uses the cache only.
"""
import argparse
import hashlib
import json
import os
import sys
import urllib.request

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from claim_lint import core  # noqa: E402

PIN_FILE = os.path.join(TOOLS, 'casestudy_pin.json')
RAW = 'https://raw.githubusercontent.com/{repo}/{commit}/{path}'
CARRY = {'必須（共通基準）', '採用', '条件付き採用'}
# value_type of catalog.json -> (type, shape) of the registry
VALUE_TYPES = {'string': ('string', 'single'), 'array of string': ('string', 'array'), 'object': ('object', 'single'),
               'boolean': ('boolean', 'single'), 'number': ('number', 'single'), 'integer': ('integer', 'single')}


def load_pin(path=PIN_FILE):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def fetch(pin, rel, cache, offline=False):
    """Bytes of a casestudy file at the pinned commit, checked against the recorded sha256."""
    want = pin['files'].get(rel)
    if want is None:
        raise KeyError(f'{rel} is not in {os.path.basename(PIN_FILE)}')
    local = os.path.join(cache, pin['commit'], rel)
    data = None
    if os.path.isfile(local):
        with open(local, 'rb') as f:
            data = f.read()
    if data is None or hashlib.sha256(data).hexdigest() != want:
        if offline:
            raise FileNotFoundError(f'{local} is missing or differs from the pin (--offline)')
        url = RAW.format(repo=pin['repo'], commit=pin['commit'], path=rel)
        with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 (fixed https URL)
            data = r.read()
        os.makedirs(os.path.dirname(local), exist_ok=True)
        with open(local, 'wb') as f:
            f.write(data)
    got = hashlib.sha256(data).hexdigest()
    if got != want:
        raise ValueError(f'{rel}: sha256 {got} differs from the pin {want}')
    return json.loads(data.decode('utf-8'))


def _ref_id(ref):
    commit, _, rid = ref.partition('@')[2].partition(':')
    return commit, rid


def check(claims_doc, deviations, catalog, decisions, pin):
    """Pure check (testable without network). catalog: list of rows; decisions: {id: {scenario: {judgement, ...}}}."""
    out = []
    rows = {r['id']: r for r in catalog}
    scenario = str(claims_doc.get('scenario'))
    short = str(claims_doc.get('casestudy_commit') or '')
    if not short or not pin['commit'].startswith(short):
        out.append(('PIN', '(root)', f'casestudy_commit {short!r} is not the pinned commit {pin["commit"][:7]}'))
    seen = {}
    for c in claims_doc.get('claims') or []:
        cid = c.get('id')
        carried = c.get('decision') in ('採用', '既定どおり')
        for ref in c.get('catalog_refs') or []:
            commit, rid = _ref_id(ref)
            if not pin['commit'].startswith(commit):
                out.append(('PIN', cid, f'{ref}: commit {commit} is not the pinned commit {pin["commit"][:7]}'))
            row = rows.get(rid)
            if row is None:
                out.append(('ORG' if rid.startswith('ORG') else 'CARRY', cid, f'{rid} is not in catalog.json'))
                continue
            if rid.startswith('ORG'):
                want_name = row['name']
                have_name = (c.get('namespace') or '') + ('.' if c.get('namespace') else '') + str(c.get('name'))
                if have_name != want_name:
                    out.append(('ORG', cid, f'{rid}: name {have_name!r} differs from the casestudy {want_name!r}'))
                want_ts = VALUE_TYPES.get(row.get('value_type'))
                if want_ts is None:
                    out.append(('ORG', cid, f"{rid}: value_type {row.get('value_type')!r} has no mapping (VALUE_TYPES)"))
                else:
                    have = (c.get('type'), c.get('shape', 'single'))
                    # a rejected row may omit shape; compare the type only then
                    if c.get('type') != want_ts[0] or (c.get('shape') is not None and have[1] != want_ts[1]):
                        out.append(('ORG', cid, f'{rid}: type/shape {have} differs from the casestudy {row.get("value_type")!r} {want_ts}'))
            if rid.startswith('HDR'):
                continue
            d = (decisions.get(rid) or {}).get(scenario)
            if d is None:
                out.append(('CARRY', cid, f'{rid}: no judgement for scenario {scenario} in the casestudy decisions'))
                continue
            seen[rid] = (cid, carried, d.get('judgement'))
    devs = [x for x in (deviations.get('deviations') or []) if str(x.get('scenario')) == scenario]
    listed_carry = {x['id']: x for x in devs if x.get('kind') == 'carry'}
    for rid, (cid, carried, judgement) in sorted(seen.items()):
        diverges = carried != (judgement in CARRY)
        if diverges and rid not in listed_carry:
            out.append(('CARRY', cid, f'{rid}: the example {"carries" if carried else "does not carry"} it, the casestudy judges '
                                      f'{judgement}; not listed in casestudy-deviations.yaml'))
        if not diverges and rid in listed_carry:
            out.append(('CARRY', cid, f'{rid}: listed as a carry deviation, but the example and the casestudy ({judgement}) agree'))
    for rid, x in listed_carry.items():
        if rid not in seen:
            out.append(('CARRY', x.get('example_row'), f'{rid}: listed as a deviation, but no row of the example refers to it'))
        elif seen[rid][0] != x.get('example_row'):
            out.append(('CARRY', x.get('example_row'), f'{rid}: example_row {x.get("example_row")} differs from the row {seen[rid][0]}'))
    for x in devs:
        if x.get('kind') == 'condition':
            rid = x['id']
            if rid not in seen:
                out.append(('CARRY', x.get('example_row'), f'{rid}: condition deviation without a row of the example'))
            elif not (seen[rid][1] and seen[rid][2] == '条件付き採用'):
                out.append(('CARRY', x.get('example_row'), f'{rid}: a condition deviation needs 条件付き採用 in the casestudy and a carried row'))
        elif x.get('kind') not in ('carry', 'condition'):
            out.append(('CARRY', x.get('example_row'), f"{x.get('id')}: kind must be carry or condition"))
    return out


def load_decisions(pin, cache, offline):
    out = {}
    for rel in pin['decision_files']:
        for row in fetch(pin, rel, cache, offline):
            out[row['id']] = row
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('example', nargs='?', default=os.path.join(ROOT, 'templates', 'examples', 'scenario-a'))
    ap.add_argument('--cache', default=os.path.join(TOOLS, '.casestudy-cache'))
    ap.add_argument('--offline', action='store_true')
    a = ap.parse_args(argv)
    pin = load_pin()
    claims_doc = core.load_yaml(os.path.join(a.example, 'claims.yaml'))
    deviations = core.load_yaml(os.path.join(ROOT, 'templates', 'casestudy-deviations.yaml'))
    catalog = fetch(pin, pin['catalog_file'], a.cache, a.offline)
    decisions = load_decisions(pin, a.cache, a.offline)
    out = check(claims_doc, deviations, catalog, decisions, pin)
    refs = sum(len(c.get('catalog_refs') or []) for c in claims_doc.get('claims') or [])
    org = sum(1 for c in claims_doc.get('claims') or [] for r in c.get('catalog_refs') or [] if ':ORG-' in r)
    lines = [f"casestudy_check  example={os.path.relpath(a.example, ROOT)}  pin={pin['commit'][:7]}  refs={refs}  org_refs={org}  "
             f"deviations={sum(1 for x in deviations.get('deviations') or [] if str(x.get('scenario')) == str(claims_doc.get('scenario')))}"]
    lines += [f'{k}  {t}  {m}' for k, t, m in out]
    lines.append(f'error {len(out)}')
    lines.append('FAIL' if out else 'OK')
    sys.stdout.buffer.write(('\n'.join(lines) + '\n').encode('utf-8'))
    return 1 if out else 0


if __name__ == '__main__':
    sys.exit(main())
