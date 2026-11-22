# -*- coding: utf-8 -*-
"""Tests of the claim_lint coverage rules (#17): R2 (substance, Lite inheritance), R3 (an IdP with a list and one
without), R3b, R4, R6, R9, R10, and the severities of --profile lite against the default (Full)."""
import datetime
import os
import shutil
import subprocess
import sys

import pytest
import yaml

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from claim_lint import core  # noqa: E402

EXAMPLE = os.path.join(ROOT, 'templates', 'examples', 'scenario-a')
CATALOG = os.path.join(ROOT, 'templates', 'catalog')
FILES = ('claims', 'token_types', 'catalog_answers')
TODAY = datetime.date(2026, 11, 22)  # before every review_by of the catalogue and the limits


def load_example():
    return {k: core.load_yaml(os.path.join(EXAMPLE, k + '.yaml')) for k in FILES}


def write(path, docs):
    os.makedirs(path, exist_ok=True)
    for k, v in docs.items():
        with open(os.path.join(path, k + '.yaml'), 'w', encoding='utf-8') as f:
            yaml.safe_dump(v, f, allow_unicode=True, sort_keys=False)
    return str(path)


def lint(tmp_path, docs, **kw):
    kw.setdefault('today', TODAY)
    return core.run(write(tmp_path / 'design', docs), **kw)


def by(res, rule, severity=None):
    return [f for f in res['findings'] if f['rule'] == rule and (severity is None or f['severity'] == severity)]


def answer(docs, eid):
    return next(a for a in docs['catalog_answers']['answers'] if a['event'] == eid)


def claim(docs, cid):
    return next(c for c in docs['claims']['claims'] if c['id'] == cid)


def ca(docs):
    return docs['catalog_answers']


def copy_catalog(tmp_path):
    dst = tmp_path / 'catalog'
    shutil.copytree(CATALOG, dst)
    return dst


def edit_yaml(path, fn):
    doc = core.load_yaml(str(path))
    fn(doc)
    with open(path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)


def event_row(doc, eid):
    return next(e for e in doc['events'] if e['id'] == eid)


# ------------------------------------------------------------------ the worked example (scenario A) stays green
def test_example_has_no_error_and_known_warnings():
    res = core.run(EXAMPLE, today=TODAY)
    assert res['counts']['error'] == 0, core.format_table(res)
    # the only warnings: R3b on I25 / I26, where the catalogue has hook_invoked unknown for Keycloak (#2)
    assert sorted((f['rule'], f['target']) for f in res['findings'] if f['severity'] == 'warn') == [('R3b', 'I25'), ('R3b', 'I26')]


def test_example_lite_has_no_error():
    res = core.run(EXAMPLE, profile='lite', today=TODAY)
    assert res['counts']['error'] == 0, core.format_table(res)


# ------------------------------------------------------------------ R2: substance and the Lite inheritance
@pytest.mark.parametrize('bad', ['ああああああああああああ', 'ROPC', 'I04'])
def test_r2_fail_weak_reason(tmp_path, bad):
    docs = load_example()
    answer(docs, 'I04')['assumption'] = bad
    assert any(f['target'] == 'I04' and 'assumption' in f['message'] for f in by(lint(tmp_path, docs), 'R2', 'error'))


def test_r2_fail_reason_is_the_event_name(tmp_path):
    docs = load_example()
    name = event_row(core.load_yaml(os.path.join(CATALOG, 'issue_events.yaml')), 'I07')['name']
    answer(docs, 'I07')['breaks_when'] = name
    assert any(f['target'] == 'I07' for f in by(lint(tmp_path, docs), 'R2', 'error'))


def _inherit(docs, eid, checked='saas-web の Capability config で Direct Access Grants が OFF であることを 2026-11-22 に管理画面で確かめた'):
    a = answer(docs, eid)
    for k in ('assumption', 'breaks_when'):
        a.pop(k, None)
    a['inherit'] = 'idp-default'
    if checked is not None:
        a['setting_checked'] = checked


def test_r2_lite_inherit_pass_for_a_client_switch(tmp_path):
    docs = load_example()
    _inherit(docs, 'I04')  # Keycloak: Capability config > Direct Access Grants (scope client)
    assert not [f for f in by(lint(tmp_path, docs, profile='lite'), 'R2') if f['target'] == 'I04']


def test_r2_lite_inherit_fail_for_a_realm_setting(tmp_path):
    docs = load_example()
    _inherit(docs, 'I03')  # Keycloak: a client policy executor (scope realm), not one client switch
    found = [f for f in by(lint(tmp_path, docs, profile='lite'), 'R2') if f['target'] == 'I03']
    assert found and all(f['severity'] == 'warn' for f in found) and 'scope' in found[0]['message']


def test_r2_lite_inherit_fail_without_setting_checked(tmp_path):
    docs = load_example()
    _inherit(docs, 'I04', checked=None)
    found = [f for f in by(lint(tmp_path, docs, profile='lite'), 'R2', 'warn') if f['target'] == 'I04']
    assert any('設定を確かめた' in f['message'] for f in found)


def test_r2_lite_inherit_fail_without_idp(tmp_path):
    docs = load_example()
    del ca(docs)['idp']
    _inherit(docs, 'I04')
    assert any(f['target'] == 'I04' and 'idp' in f['message'] for f in by(lint(tmp_path, docs, profile='lite'), 'R2', 'warn'))


def test_r2_full_does_not_allow_inherit(tmp_path):
    docs = load_example()
    _inherit(docs, 'I04')
    assert any(f['target'] == 'I04' and 'Lite だけ' in f['message'] for f in by(lint(tmp_path, docs), 'R2', 'error'))


# ------------------------------------------------------------------ R3
def test_r3_pass_idp_without_list_keycloak(tmp_path):
    res = lint(tmp_path, load_example())
    assert not by(res, 'R3', 'error') and by(res, 'R3', 'info')


def test_r3_fail_idp_without_list_needs_r9_search_of_the_idp(tmp_path):
    docs = load_example()
    ca(docs)['outside_enumeration']['searched'] = ['design.md の 2. と 7. の図']
    assert [f['target'] for f in by(lint(tmp_path, docs), 'R3', 'error')] == ['idp']


def test_r3_fail_idp_not_declared(tmp_path):
    docs = load_example()
    del ca(docs)['idp']
    assert by(lint(tmp_path, docs), 'R3', 'error')


def test_r3_pass_idp_with_list_auth0(tmp_path):
    docs = load_example()
    ca(docs)['idp'] = {'name': 'auth0'}
    res = lint(tmp_path, docs)
    assert not by(res, 'R3', 'error')
    assert any('差集合は 0 件' in f['message'] for f in by(res, 'R3', 'info'))


def test_r3_fail_idp_with_list_auth0_item_not_in_catalogue(tmp_path):
    cat = copy_catalog(tmp_path)

    def add(doc):
        sl = next(s for s in doc['seed_lists'] if s['id'] == 'auth0-trigger')
        sl['items'].append({'id': 'new-trigger'})
        sl['expected']['count'] += 1
    edit_yaml(cat / 'seeds.yaml', add)
    docs = load_example()
    ca(docs)['idp'] = {'name': 'auth0'}
    res = lint(tmp_path, docs, catalog_dir=str(cat))
    assert [f['target'] for f in by(res, 'R3', 'error')] == ['auth0-trigger/new-trigger']


def _cognito(docs, triggers, source=True):
    ca(docs)['idp'] = {'name': 'cognito', 'trigger_list': triggers}
    if source:
        ca(docs)['idp']['trigger_list_source'] = {'url': 'https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-pre-token-generation.html',
                                                  'verified_on': '2026-11-22'}


def test_r3_pass_idp_with_list_outside_the_catalogue(tmp_path):
    docs = load_example()
    _cognito(docs, [{'trigger': 'TokenGeneration_HostedAuth', 'events': ['I01']},
                    {'trigger': 'TokenGeneration_RefreshTokens', 'events': ['I02']},
                    {'trigger': 'TokenGeneration_ClientCredentials',
                     'out_of_scope': {'assumption': 'M2M のアプリクライアントを作らない。利用者のログインだけ',
                                      'breaks_when': 'サービス間の呼び出しに client credentials を使うとき'}}])
    assert not by(lint(tmp_path, docs), 'R3', 'error')


def test_r3_fail_idp_with_list_outside_the_catalogue(tmp_path):
    docs = load_example()
    _cognito(docs, [{'trigger': 'TokenGeneration_HostedAuth', 'events': ['I99']},
                    {'trigger': 'TokenGeneration_RefreshTokens'}], source=False)
    targets = sorted(f['target'] for f in by(lint(tmp_path, docs), 'R3', 'error'))
    assert targets == ['TokenGeneration_HostedAuth', 'TokenGeneration_RefreshTokens', 'idp']
    docs = load_example()
    ca(docs)['idp'] = {'name': 'cognito'}
    assert any('trigger_list' in f['message'] for f in by(lint(tmp_path, docs), 'R3', 'error'))


def test_r3_unknown_idp_must_declare_enumerable(tmp_path):
    docs = load_example()
    ca(docs)['idp'] = {'name': 'someidp'}
    assert any('enumerable' in f['message'] for f in by(lint(tmp_path, docs), 'R3', 'error'))
    ca(docs)['idp'] = {'name': 'someidp', 'enumerable': False}
    ca(docs)['outside_enumeration']['searched'].append('someidp の管理者ガイド（トークンのフックの節）')
    assert not by(lint(tmp_path, docs), 'R3', 'error')


# ------------------------------------------------------------------ R3b
def test_r3b_pass_hook_invoked_yes(tmp_path):
    res = lint(tmp_path, load_example())
    assert not by(res, 'R3b', 'error')
    assert not [f for f in by(res, 'R3b') if f['target'] in ('I01', 'I02')]  # Keycloak: hook_invoked yes


def test_r3b_fail_hook_not_invoked_with_custom_claim(tmp_path):
    docs = load_example()
    ca(docs)['idp'] = {'name': 'auth0'}  # Auth0: I09 (Back-Channel Logout) has hook_invoked no
    a = answer(docs, 'I09')
    for k in ('assumption', 'breaks_when'):
        a.pop(k)
    a.update(answer='該当', token_types=['LOGOUT'])
    claim(docs, 'C-tenant-id')['carried_in'] = ['AT', 'LOGOUT']
    err = by(lint(tmp_path, docs), 'R3b', 'error')
    assert [f['target'] for f in err] == ['I09'] and 'C-tenant-id' in err[0]['message']


def test_r3b_fail_when_catalogue_says_no(tmp_path):
    cat = copy_catalog(tmp_path)
    edit_yaml(cat / 'issue_events.yaml', lambda d: event_row(d, 'I02')['idp']['keycloak'].update(hook_invoked='no'))
    res = lint(tmp_path, load_example(), catalog_dir=str(cat))
    assert [f['target'] for f in by(res, 'R3b', 'error')] == ['I02']


def test_r3b_unknown_is_warn_and_hook_checked_settles_it(tmp_path):
    docs = load_example()
    assert sorted(f['target'] for f in by(lint(tmp_path, docs), 'R3b', 'warn')) == ['I25', 'I26']
    answer(docs, 'I25')['hook_checked'] = '初回ログインの AT を発行して、tenant_id・user_id・roles・v が載ることを実物で確かめた'
    res = lint(tmp_path, docs)
    assert [f['target'] for f in by(res, 'R3b', 'warn')] == ['I26']
    assert [f['target'] for f in by(res, 'R3b', 'info')] == ['I25']


def test_r3b_skips_issuers_other_than_the_idp(tmp_path):
    docs = load_example()
    a = answer(docs, 'I21')  # issuer gateway: the IdP's hook is not the writer, hook_invoked no is not a finding
    for k in ('assumption', 'breaks_when'):
        a.pop(k)
    a.update(answer='該当', token_types=['AT'])
    assert not [f for f in by(lint(tmp_path, docs), 'R3b') if f['target'] == 'I21']


def test_r3b_protocol_claim_of_the_idp_is_not_custom(tmp_path):
    res = lint(tmp_path, load_example())
    assert all('C-typ-claim' not in f['message'] for f in by(res, 'R3b'))


# ------------------------------------------------------------------ R4
def test_r4_pass(tmp_path):
    assert not by(lint(tmp_path, load_example()), 'R4')


def test_r4_fail_missing_section_cell_and_basis(tmp_path):
    docs = load_example()
    st = ca(docs)['subject_states']['states']
    del st['subject-states/deleted']['RT']
    st['subject-states/suspended']['AT']['basis'] = ''
    st['subject-states/role-change']['ID']['result'] = '多分なし'
    targets = {f['target'] for f in by(lint(tmp_path, docs), 'R4', 'error')}
    assert targets == {'subject-states/deleted:RT', 'subject-states/suspended:AT', 'subject-states/role-change:ID'}
    del ca(docs)['subject_states']
    assert [f['target'] for f in by(lint(tmp_path, docs), 'R4', 'error')] == ['subject_states']


def test_r4_fail_missing_state_and_unused_layer_that_is_used(tmp_path):
    docs = load_example()
    sm = ca(docs)['subject_states']
    del sm['states']['subject-states/invited']
    sm['unused_layers']['AT'] = 'この設計では AT を使わないことにした（テスト）'
    targets = {f['target'] for f in by(lint(tmp_path, docs), 'R4', 'error')}
    assert 'subject-states/invited' in targets and 'unused_layers:AT' in targets


def test_r4_no_effect_needs_basis(tmp_path):
    docs = load_example()
    ca(docs)['subject_states']['states']['subject-states/credential-change']['RT']['basis'] = 'なし'
    err = by(lint(tmp_path, docs), 'R4', 'error')
    assert [f['target'] for f in err] == ['subject-states/credential-change:RT'] and '影響なし' in err[0]['message']


# ------------------------------------------------------------------ R6 (warn only)
def test_r6_pass(tmp_path):
    res = lint(tmp_path, load_example())
    assert not by(res, 'R6', 'warn') and by(res, 'R6', 'info')


def test_r6_fail_missing_pair_is_warn_in_full_and_lite(tmp_path):
    docs = load_example()
    pw = ca(docs)['pairwise']
    pw['combinations'] = [c for c in pw['combinations'] if not (c['event'] == 'I26' and c['stage'] == '②')]
    for profile in ('full', 'lite'):
        res = lint(tmp_path, docs, profile=profile)
        assert not by(res, 'R6', 'error')
        assert [f['target'] for f in by(res, 'R6', 'warn')] == ['E×T:I26×②']


def test_r6_fail_new_subject_kind_needs_pairs(tmp_path):
    docs = load_example()
    ca(docs)['pairwise']['subject_kinds']['ワークロード'] = {'answer': '該当'}
    targets = {f['target'] for f in by(lint(tmp_path, docs), 'R6', 'warn')}
    assert {'S×E:ワークロード×I01', 'S×T:ワークロード×①'} <= targets


def test_r6_fail_missing_section_and_wrong_stage(tmp_path):
    docs = load_example()
    ca(docs)['pairwise']['combinations'].append({'subject': '利用者', 'event': 'I02', 'stage': '①', 'note': 'I02 に ① の段階はない'})
    assert any(f['target'].startswith('combinations[') for f in by(lint(tmp_path, docs), 'R6', 'warn'))
    del ca(docs)['pairwise']
    assert [f['target'] for f in by(lint(tmp_path, docs), 'R6', 'warn')] == ['pairwise']


# ------------------------------------------------------------------ R9
def test_r9_pass(tmp_path):
    assert not by(lint(tmp_path, load_example()), 'R9')


@pytest.mark.parametrize('bare', ['なし', 'ない。', '特になし', 'None'])
def test_r9_fail_bare_none(tmp_path, bare):
    docs = load_example()
    ca(docs)['outside_enumeration']['answer'] = bare
    assert by(lint(tmp_path, docs), 'R9', 'error')


def test_r9_fail_missing_respondent_date_searched(tmp_path):
    docs = load_example()
    oe = ca(docs)['outside_enumeration']
    for k in ('respondent', 'date', 'searched'):
        del oe[k]
    msgs = ' '.join(f['message'] for f in by(lint(tmp_path, docs), 'R9', 'error'))
    assert 'respondent' in msgs and 'date' in msgs and 'searched' in msgs


def test_r9_fail_found_without_handling(tmp_path):
    docs = load_example()
    ca(docs)['outside_enumeration']['found'].append({'name': '管理者の一括ログアウト'})
    assert [f['target'] for f in by(lint(tmp_path, docs), 'R9', 'error')] == ['outside_enumeration.found[1]']


def test_r9_missing_is_error_in_lite_too(tmp_path):
    docs = load_example()
    del ca(docs)['outside_enumeration']
    assert by(lint(tmp_path, docs, profile='lite'), 'R9', 'error')


# ------------------------------------------------------------------ R10
def test_r10_pass_before_review_by(tmp_path):
    assert not by(lint(tmp_path, load_example()), 'R10')


def test_r10_warn_after_review_by(tmp_path):
    res = lint(tmp_path, load_example(), today=datetime.date(2027, 3, 1))
    found = by(res, 'R10')
    assert found and all(f['severity'] == 'warn' for f in found)
    assert {'seeds.yaml', 'issue_events.yaml', 'path_limits.yaml'} <= {f['target'] for f in found}
    assert res['counts']['error'] == 0


def test_r10_inline_limit(tmp_path):
    docs = load_example()
    at = next(t for t in docs['token_types']['token_types'] if t['id'] == 'AT')
    at['size']['path'].append({'id': 'inline-proxy', 'applies_to': 'header_field', 'bytes': 8192, 'basis': 'test',
                               'review_by': '2026-01-01'})
    assert [f['target'] for f in by(lint(tmp_path, docs), 'R10')] == ['token_types AT']


# ------------------------------------------------------------------ --profile lite against Full
def _broken():
    """One failing case per rule whose severity depends on the profile (or must not)."""
    docs = load_example()
    docs['catalog_answers']['answers'] = docs['catalog_answers']['answers'][1:]           # R2: I01 not answered
    del ca(docs)['subject_states']['states']['subject-states/deleted']['RT']               # R4
    ca(docs)['pairwise']['combinations'].pop()                                              # R6
    ca(docs)['outside_enumeration']['answer'] = 'なし'                                       # R9
    del claim(docs, 'C-tenant-id')['owner']                                                 # R1
    claim(docs, 'C-roles').update(max_items=600, max_bytes=12)                              # R8: over the limit
    return docs


@pytest.mark.parametrize('profile,expected', [
    ('full', {'R1': 'error', 'R2': 'error', 'R4': 'error', 'R6': 'warn', 'R8': 'error', 'R9': 'error'}),
    ('lite', {'R1': 'error', 'R2': 'warn', 'R4': 'warn', 'R6': 'warn', 'R8': 'error', 'R9': 'error'}),
])
def test_profile_severities(tmp_path, profile, expected):
    res = lint(tmp_path, _broken(), profile=profile)
    got = {}
    for rule in expected:
        sev = {f['severity'] for f in by(res, rule) if f['severity'] != 'info'}
        assert len(sev) == 1, (rule, sev)
        got[rule] = sev.pop()
    assert got == expected


def test_cli_profile_lite_exit_status(tmp_path):
    docs = load_example()
    del ca(docs)['subject_states']  # R4: error in Full, warn in Lite
    d = write(tmp_path / 'design', docs)
    cli = [sys.executable, os.path.join(TOOLS, 'claim_lint'), d]
    assert subprocess.run(cli, capture_output=True).returncode == 1
    assert subprocess.run(cli + ['--profile', 'lite'], capture_output=True).returncode == 0
