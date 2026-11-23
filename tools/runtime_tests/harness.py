# -*- coding: utf-8 -*-
"""Test registry and result records shared by the offline and the live cases.

A case is registered with @case('<file>#<anchor>', env=...), where <file>#<anchor> is the planned item
`test:<file>#<anchor>` of templates/trace/planned_items.yaml and the anchor of templates/runtime/<file>.md.
The requirement IDs and lint rules of a case are not written here: they are read from templates/trace/requirements.yaml
(every requirement whose planned_items has the test item), so the run log and the trace cannot disagree.
"""
import os
import time
import traceback

import yaml

from validator import Reject

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CASES = []


def case(test_id, env='offline', expected='', lint=(), title=''):
    def deco(fn):
        CASES.append({'id': test_id, 'env': env, 'expected': expected, 'lint_extra': list(lint), 'title': title, 'fn': fn})
        return fn
    return deco


class Run:
    """Collects the checks of one case. A check is (name, expected, observed, ok)."""

    def __init__(self):
        self.checks = []
        self.notes = []

    def add(self, name, expected, observed, ok):
        self.checks.append({'name': name, 'expected': expected, 'observed': observed, 'ok': bool(ok)})

    def reject(self, name, fn, codes):
        codes = (codes,) if isinstance(codes, str) else tuple(codes)
        try:
            fn()
            observed = 'accepted'
        except Reject as e:
            observed = e.code
        self.add(name, 'reject ' + '|'.join(codes), observed, observed in codes)

    def accept(self, name, fn):
        try:
            out = fn()
            observed = 'accepted'
        except Reject as e:
            out, observed = None, f'rejected {e.code} ({e.detail})'
        self.add(name, 'accept', observed, observed == 'accepted')
        return out

    def note(self, text):
        self.notes.append(text)


def trace_links():
    """test item -> (requirement IDs, lint rules, slides) from the trace table."""
    reqs = yaml.safe_load(open(os.path.join(ROOT, 'templates', 'trace', 'requirements.yaml'), encoding='utf-8'))['requirements']
    out = {}
    for r in reqs:
        for p in r['planned_items']:
            if p.startswith('test:'):
                d = out.setdefault(p[5:], {'reqs': [], 'lint': set(), 'slides': set()})
                d['reqs'].append(r['id'])
                d['slides'].add(r['slide'].split(':', 1)[1])
                d['lint'].update(q[5:] for q in r['planned_items'] if q.startswith('lint:'))
    return out


def execute(cases, ctx_factory, select=None):
    links = trace_links()
    results = []
    ctx = None
    for c in cases:
        if select and c['id'] not in select:
            continue
        if ctx is None:
            ctx = ctx_factory()
        run = Run()
        t0 = time.time()
        error = None
        try:
            c['fn'](ctx, run)
        except Exception as e:  # noqa: BLE001 - a crash is a failed case with its traceback in the log
            error = f'{type(e).__name__}: {e}\n' + traceback.format_exc(limit=6)
        link = links.get(c['id'], {'reqs': [], 'lint': set(), 'slides': set()})
        ok = error is None and bool(run.checks) and all(k['ok'] for k in run.checks)
        results.append({'id': 'test:' + c['id'], 'env': c['env'], 'title': c['title'], 'expected': c['expected'],
                        'requirements': sorted(link['reqs']), 'lint': sorted(set(link['lint']) | set(c['lint_extra'])),
                        'slides': sorted(link['slides']), 'ok': ok, 'seconds': round(time.time() - t0, 3),
                        'checks': run.checks, 'notes': run.notes, 'error': error})
    return results


def summary_lines(results):
    lines = []
    for r in results:
        bad = [k for k in r['checks'] if not k['ok']]
        lines.append(f"{'PASS' if r['ok'] else 'FAIL'}  {r['id']:<52} {len(r['checks']) - len(bad)}/{len(r['checks'])} checks"
                     + (f"  ERROR {r['error'].splitlines()[0]}" if r['error'] else ''))
        for k in bad:
            lines.append(f"      - {k['name']}: expected {k['expected']}, observed {k['observed']}")
    n_ok = sum(r['ok'] for r in results)
    lines.append(f'{n_ok}/{len(results)} cases passed, {sum(len(r["checks"]) for r in results)} checks')
    return lines
