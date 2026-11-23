# -*- coding: utf-8 -*-
"""Tests of the runtime tests of #8 (tools/runtime_tests, templates/runtime).

- the offline cases pass (crafted tokens against the reference receivers written to the designs)
- every case (offline and live) has its anchor section in templates/runtime/<file>.md, and that section carries the
  req: marker of every requirement whose planned items name the test, and the lint rules linked to it
- every planned test item of #8 is either documented (an anchor) or listed as not yet made
- the run logs under research/runtime hold no raw JWT and no PEM key
The live cases need Keycloak and Postgres and are not run here; their IDs are read from the source.
"""
import glob
import os
import re
import sys

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RT = os.path.join(ROOT, 'tools', 'runtime_tests')
sys.path.insert(0, RT)
sys.path.insert(0, os.path.join(ROOT, 'tools'))

pytest.importorskip('cryptography')
import harness  # noqa: E402
import cases_offline  # noqa: E402,F401  (registers the offline cases)
import trace_check  # noqa: E402

LIVE_SRC = open(os.path.join(RT, 'cases_live.py'), encoding='utf-8').read()
LIVE_IDS = re.findall(r"@case\('([^']+)', env='live'", LIVE_SRC)
OFFLINE = [c for c in harness.CASES if c['env'] == 'offline']
LINKS = harness.trace_links()


def section(test_id):
    f, anchor = test_id.split('#', 1)
    problem, text = trace_check._md_part(ROOT, os.path.join('templates', 'runtime', f + '.md'), anchor)
    assert problem is None, problem
    return text


def test_offline_cases_pass():
    results = harness.execute(OFFLINE, cases_offline.new_ctx)
    bad = [r['id'] + ': ' + (r['error'] or '; '.join(f"{k['name']} -> {k['observed']}" for k in r['checks'] if not k['ok'])) for r in results if not r['ok']]
    assert not bad, '\n'.join(bad)
    assert len(results) >= 30


@pytest.mark.parametrize('test_id', sorted({c['id'] for c in OFFLINE} | set(LIVE_IDS)))
def test_case_is_documented_with_markers(test_id):
    text = section(test_id)
    link = LINKS.get(test_id, {'reqs': [], 'lint': set()})
    missing = [r for r in link['reqs'] if f'req:{r}' not in text]
    assert not missing, f'{test_id}: no req: marker for {missing}'
    extra = {x for c in harness.CASES if c['id'] == test_id for x in c['lint_extra']}
    missing = [r for r in sorted(set(link['lint']) | extra) if f'lint:{r}`' not in text]
    assert not missing, f'{test_id}: lint rules not named {missing}'
    assert f'test:{test_id}' in text, f'{test_id}: the section does not state its test ID'


def test_case_ids_are_planned_items():
    planned = {i['ref'] for i in yaml.safe_load(open(os.path.join(ROOT, 'templates', 'trace', 'planned_items.yaml'), encoding='utf-8'))['items']}
    for tid in {c['id'] for c in OFFLINE} | set(LIVE_IDS):
        if tid.startswith('golden_tokens#'):
            continue  # the acceptance checks of the golden tokens are not trace items
        assert 'test:' + tid in planned, tid


def test_every_planned_test_item_of_8_is_made_or_listed():
    items = yaml.safe_load(open(os.path.join(ROOT, 'templates', 'trace', 'planned_items.yaml'), encoding='utf-8'))['items']
    docs = {f: open(os.path.join(ROOT, 'templates', 'runtime', f + '.md'), encoding='utf-8').read() for f in ('negative_tests', 'consumer_contract')}
    made = {c['id'] for c in OFFLINE} | set(LIVE_IDS)
    for it in items:
        ref = it['ref']
        if not ref.startswith('test:') or it.get('issue') != '#8' or '#' not in ref:
            continue
        tid = ref[5:]
        f = tid.split('#', 1)[0]
        if tid in made:
            continue
        assert f'`{ref}`' in docs[f].split('まだ作っていないテスト', 1)[1], f'{ref}: neither made nor listed as not yet made'
        assert f'<a id="{tid.split("#", 1)[1]}"></a>' not in docs[f], f'{ref}: has an anchor but no case'


def test_run_logs_hold_no_secret_material():
    files = glob.glob(os.path.join(ROOT, 'research', 'runtime', '*'))
    assert files, 'no run log under research/runtime'
    jwt_re = re.compile(r'eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}')
    for p in files:
        t = open(p, encoding='utf-8').read()
        assert not jwt_re.search(t), f'{p}: a raw JWT'
        assert '-----BEGIN' not in t, f'{p}: a PEM block'


def test_golden_issuers_contain_example():
    import golden
    for iss in list(golden.A_ISS.values()) + [golden.STS_ISS, golden.TTS_ISS]:
        assert 'example' in iss
