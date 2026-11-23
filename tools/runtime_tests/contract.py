# -*- coding: utf-8 -*-
"""Consumer contract (templates/runtime/consumer_contract.md): what a receiver reads must be declared in the registry.

The registry row of a claim lists its readers in `consumers`. The contract test runs the receiver on a token whose
payload records every member the receiver touches, maps each member to its registry row (name + namespace), and fails
for a member whose row does not list the receiver. Removing a reader from `consumers` therefore breaks the test
(the completion criterion of #8), and a receiver that starts reading an undeclared claim breaks it too.
"""
import json
import os

import jsonschema


class Recording(dict):
    """A payload dict that records the member names read (get / [] / in), with a prefix for nested objects."""

    def __init__(self, data, log, prefix=''):
        super().__init__()
        self._log, self._prefix = log, prefix
        for k, v in data.items():
            dict.__setitem__(self, k, Recording(v, log, k) if isinstance(v, dict) else v)

    def _hit(self, k):
        if dict.__contains__(self, k):  # only members the token carries; probing for an absent member is not a read
            self._log.add((self._prefix, k))

    def __getitem__(self, k):
        self._hit(k)
        return dict.__getitem__(self, k)

    def get(self, k, default=None):
        self._hit(k)
        return dict.get(self, k, default)

    def __contains__(self, k):
        self._hit(k)
        return dict.__contains__(self, k)


def rows_by_member(claims_rows):
    """(namespace or '', name) -> row, for the adopted rows."""
    out = {}
    for r in claims_rows:
        if r.get('decision') in ('採用', '既定どおり', '条件付き採用'):
            out[(r.get('namespace') or '', r['name'])] = r
    return out


def violations(read_log, claims_rows, consumer, namespace='https://claims.example.com/'):
    """Members read by `consumer` that the registry does not declare it reads. The namespace object itself is a container."""
    rows = rows_by_member(claims_rows)
    out = []
    for prefix, name in sorted(read_log):
        if prefix == '' and name == namespace:
            continue
        row = rows.get((prefix, name))
        if row is None:
            out.append(f'{prefix}{name}: not in the registry')
        elif consumer not in (row.get('consumers') or []):
            out.append(f'{prefix}{name} ({row["id"]}): {consumer} is not in consumers {row.get("consumers")}')
    return out


def schema_errors(payload, schema_path):
    schema = json.load(open(schema_path, encoding='utf-8'))
    v = jsonschema.Draft202012Validator(schema)
    return sorted(f'{"/".join(map(str, e.absolute_path)) or "(root)"}: {e.message}' for e in v.iter_errors(payload))


def issued_claims_missing(payload, claims_rows, token_type, namespace='https://claims.example.com/'):
    """Adopted rows carried in token_type that the issued payload lacks (silent drop: lightweight AT, hook timeout)."""
    out = []
    for r in claims_rows:
        if r.get('decision') != '採用' or token_type not in (r.get('carried_in') or []):
            continue
        ns = r.get('namespace')
        holder = payload.get(ns) if ns else payload
        if not isinstance(holder, dict) or r['name'] not in holder:
            if r.get('on_missing') == '既定値':
                continue  # absent is allowed and means the default (e.g. roles: none)
            out.append(f'{r["id"]} ({(ns or "") + r["name"]})')
    return out


def here(*p):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *p)
