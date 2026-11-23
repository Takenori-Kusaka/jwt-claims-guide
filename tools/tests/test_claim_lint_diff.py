# -*- coding: utf-8 -*-
"""Tests of claim_lint diff (L10 of #6): breaking changes against an earlier git ref. A temporary git repository holds the
scenario A files at the base commit; the head is edited in the work tree."""
import os
import shutil
import subprocess
import sys

import pytest
import yaml

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from claim_lint import core, diff  # noqa: E402
from claim_lint.__main__ import main  # noqa: E402

EXAMPLE = os.path.join(ROOT, 'templates', 'examples', 'scenario-a')


def git(cwd, *args):
    subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@example.com', *args], cwd=cwd, check=True,
                   capture_output=True)


@pytest.fixture
def repo(tmp_path):
    d = tmp_path / 'repo' / 'design'
    d.mkdir(parents=True)
    for n in ('claims.yaml', 'token_types.yaml'):
        shutil.copy(os.path.join(EXAMPLE, n), d / n)
    git(tmp_path / 'repo', 'init', '-q')
    git(tmp_path / 'repo', 'add', '.')
    git(tmp_path / 'repo', 'commit', '-q', '-m', 'base')
    return d


def edit(path, fn):
    doc = core.load_yaml(str(path))
    fn(doc)
    with open(path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)


def claim(doc, cid):
    return next(c for c in doc['claims'] if c['id'] == cid)


def errors(res):
    return [f for f in res['findings'] if f['severity'] == 'error']


def test_no_change_pass(repo):
    res = diff.run(str(repo), 'HEAD')
    assert res['counts'] == {'error': 0, 'warn': 0, 'info': 0}


def test_non_breaking_additions_pass(repo):
    # what PR #6 itself added to scenario A: a registered_ref, against on enforced_at, max_clock_skew
    edit(repo / 'claims.yaml', lambda d: claim(d, 'C-roles')['enforced_at'][0].update(against=['api_config']))
    edit(repo / 'token_types.yaml', lambda d: d['token_types'][1].update(max_clock_skew=30))
    assert not errors(diff.run(str(repo), 'HEAD'))


def test_type_shape_usage_change_fail(repo):
    def f(d):
        claim(d, 'C-tenant-id')['type'] = 'integer'
        claim(d, 'C-roles')['shape'] = 'space_delimited'
        claim(d, 'C-user-id')['usage'] = 'authz'
    edit(repo / 'claims.yaml', f)
    assert sorted(x['target'] for x in errors(diff.run(str(repo), 'HEAD'))) == ['C-roles', 'C-tenant-id', 'C-user-id']


def test_removal_and_rename_fail_but_sunset_removal_pass(repo):
    edit(repo / 'claims.yaml', lambda d: d.update(claims=[c for c in d['claims'] if c['id'] != 'C-v']))
    edit(repo / 'claims.yaml', lambda d: claim(d, 'C-user-id').update(name='uid'))
    msgs = [x['message'] for x in errors(diff.run(str(repo), 'HEAD'))]
    assert any('消した' in m for m in msgs) and any('名前を' in m for m in msgs)
    # a claim whose definition reached sunset at the base may leave
    git(repo.parent, 'checkout', '-q', '--', '.')
    edit(repo / 'claims.yaml', lambda d: claim(d, 'C-v').update(status='sunset'))
    git(repo.parent, 'commit', '-q', '-am', 'sunset')
    edit(repo / 'claims.yaml', lambda d: d.update(claims=[c for c in d['claims'] if c['id'] != 'C-v']))
    res = diff.run(str(repo), 'HEAD')
    assert not errors(res) and [f['severity'] for f in res['findings']] == ['info']


def test_made_required_fail(repo):
    edit(repo / 'claims.yaml', lambda d: claim(d, 'C-roles').update(on_missing='拒否'))
    edit(repo / 'token_types.yaml', lambda d: d['token_types'][0]['required_claims'].append('acr'))
    targets = sorted(x['target'] for x in errors(diff.run(str(repo), 'HEAD')))
    assert targets == ['C-roles', 'token_type AT']


def test_description_change_is_warn(repo):
    edit(repo / 'claims.yaml', lambda d: claim(d, 'C-v').update(description='別の意味'))
    res = diff.run(str(repo), 'HEAD')
    assert [(f['severity'], f['target']) for f in res['findings']] == [('warn', 'C-v')]


def test_cli_exit_status(repo, capsys):
    assert main(['diff', '--base', 'HEAD', str(repo)]) == 0
    edit(repo / 'claims.yaml', lambda d: claim(d, 'C-tenant-id').update(type='integer'))
    assert main(['diff', '--base', 'HEAD', str(repo)]) == 1
    assert main(['diff', '--base', 'no-such-ref', str(repo)]) == 2
    capsys.readouterr()


def test_scenario_a_history_detects_known_changes():
    """Measured on this repository's history (RULES.md): from the vertical slice (befd117) to now, the scope shape was
    corrected to space_delimited and azp was made required in the AT (A08). Skipped in a shallow clone."""
    if subprocess.run(['git', 'cat-file', '-e', 'befd117^{commit}'], cwd=ROOT, capture_output=True).returncode != 0:
        pytest.skip('history not available (shallow clone)')
    res = diff.run(EXAMPLE, 'befd117')
    got = sorted((f['target'], f['severity']) for f in res['findings'])
    assert ('C-scope', 'error') in got and ('token_type AT', 'error') in got


def test_vocabulary_value_removed_fails_and_added_is_info(repo):
    edit(repo / 'claims.yaml', lambda d: claim(d, 'C-roles')['value_vocabulary'].update(values=['approver_v2', 'tenant-admin']))
    got = sorted((f['severity'], f['target']) for f in diff.run(str(repo), 'HEAD')['findings'])
    assert got == [('error', 'C-roles'), ('info', 'C-roles')]
