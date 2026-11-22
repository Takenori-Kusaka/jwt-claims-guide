# -*- coding: utf-8 -*-
"""Tests of tools/catalog_check.py (#2): the real catalogue passes, and each check fails on a broken copy."""
import copy
import os
import sys

import pytest

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
import catalog_check as cc  # noqa: E402


@pytest.fixture(scope='module')
def base():
    docs, findings = cc.load()
    assert findings == []
    return docs


def run(docs):
    return cc.run(docs=docs)


def errors(res, check=None, contains=None):
    return [f for f in res['findings'] if f['severity'] == 'error' and (check is None or f['check'] == check)
            and (contains is None or contains in f['message'] or contains in f['target'])]


def event(docs, eid):
    kind = 'issue_events' if eid.startswith('I') else 'use_events'
    return next(r for r in docs[kind]['events'] if r['id'] == eid)


def item(docs, key):
    lst, iid = key.split('/', 1)
    sl = next(s for s in docs['seeds']['seed_lists'] if s['id'] == lst)
    return next(i for i in sl['items'] if i['id'] == iid)


def test_catalogue_passes(base):
    res = run(base)
    assert errors(res) == [], errors(res)
    s = res['stats']
    assert s['unmapped'] == 0
    assert s['matrix_cells'] == 49
    assert s['issue_events'] >= 33 and s['use_events'] >= 28 and s['token_kinds'] >= 17


def test_closure_is_reusable_for_r3(base):
    findings, stats = cc.closure(base)
    assert findings == [] and stats['unmapped'] == 0 and stats['seed_items'] > 0


def test_seed_item_without_row_or_out_of_scope_fails(base):
    docs = copy.deepcopy(base)
    for r in docs['issue_events']['events']:
        r['seeds'] = [s for s in r['seeds'] if s != 'auth0-protocol/oauth2-device-code']
    res = run(docs)
    assert errors(res, 'CLOSURE', 'auth0-protocol/oauth2-device-code')


def test_jwt_claim_only_in_claims_produced_counts_as_mapped(base):
    docs = copy.deepcopy(base)
    i27 = event(docs, 'I27')
    i27['claims_produced'] = [c for c in i27['claims_produced'] if c != 'ttl']
    for r in docs['use_events']['events']:
        r['claims_read'] = [c for c in r['claims_read'] if c != 'ttl']
    assert errors(run(docs), 'CLOSURE', 'iana-jwt-claims/ttl')


def test_unknown_seed_reference_fails(base):
    docs = copy.deepcopy(base)
    event(docs, 'I01')['seeds'].append('auth0-protocol/no-such-value')
    assert errors(run(docs), 'CLOSURE', 'no-such-value')


def test_row_without_seed_fails(base):
    docs = copy.deepcopy(base)
    u23 = event(docs, 'U23')
    u23['seeds'] = []
    u23['claims_read'] = []
    assert errors(run(docs), 'CLOSURE', '種になる一覧のどの項目にもひもづいていない')


def test_out_of_scope_needs_assumption_and_breaks_when(base):
    docs = copy.deepcopy(base)
    item(docs, 'oidc-logout/session-management')['out_of_scope']['breaks_when'] = '短い'
    assert errors(run(docs), 'CLOSURE', 'breaks_when')
    docs = copy.deepcopy(base)
    o = item(docs, 'oidc-logout/session-management')['out_of_scope']
    o['breaks_when'] = o['assumption']
    assert errors(run(docs), 'CLOSURE', '同じ文')


def test_out_of_scope_item_referenced_by_a_row_fails(base):
    docs = copy.deepcopy(base)
    event(docs, 'U06')['seeds'].append('oidc-logout/session-management')
    assert errors(run(docs), 'CLOSURE', '対象外なのに')


def test_matrix_cell_missing_or_without_basis_fails(base):
    docs = copy.deepcopy(base)
    docs['matrix'] = docs['matrix'].replace('| Logout Token | 影響なし | セッションを終えないので出ない（OpenID Connect Back-Channel Logout 1.0 §2.4） | — | — |\n', '', 1)
    assert errors(run(docs), 'MATRIX', 'セルがない')
    docs = copy.deepcopy(base)
    docs['matrix'] = docs['matrix'].replace('| AT | 発行 | ログインで出る', '| AT | 発行済み | ログインで出る', 1)
    assert errors(run(docs), 'MATRIX', '結果は')


def test_hook_invoked_must_be_in_enum_and_conditional_needs_note(base):
    docs = copy.deepcopy(base)
    event(docs, 'I01')['idp']['keycloak']['hook_invoked'] = 'maybe'
    assert errors(run(docs), 'COLUMNS', 'hook_invoked')
    docs = copy.deepcopy(base)
    b = event(docs, 'I03')['idp']['keycloak']
    b['hook_note'] = ''
    assert errors(run(docs), 'COLUMNS', 'hook_note')


def test_issue_row_needs_lifetime_impact(base):
    docs = copy.deepcopy(base)
    del event(docs, 'I02')['lifetime_impact']['recomputed']
    assert errors(run(docs), 'COLUMNS', 'lifetime_impact')


def test_stop_setting_needs_setting_scope_default(base):
    docs = copy.deepcopy(base)
    event(docs, 'I04')['idp']['keycloak']['stop_setting'] = {'setting': 'Direct Access Grants', 'scope': 'everywhere', 'default': 'OFF'}
    assert errors(run(docs), 'COLUMNS', 'stop_setting')


def test_gap_needs_marker_and_slide_ids_must_exist(base):
    docs = copy.deepcopy(base)
    # no row is a gap since #10, so make one: a gap row without checked or without the marker fails
    event(docs, 'I07')['guide'] = {'status': 'gap', 'slides': [], 'note': 'device flow を扱うスライドがない', 'checked': '検索して 0 件'}
    del event(docs, 'I07')['guide']['checked']
    assert errors(run(docs), 'GUIDE', 'checked')
    event(docs, 'I07')['guide'] = {'status': 'gap', 'slides': [], 'note': 'device flow を扱うスライドがない', 'checked': '検索して 0 件'}
    assert errors(run(docs), 'GUIDE', 'marker')
    docs = copy.deepcopy(base)
    event(docs, 'I01')['guide']['slides'].append('p99-no-such-slide')
    assert errors(run(docs), 'GUIDE', 'p99-no-such-slide')


def test_draft_reference_needs_a_version(base):
    docs = copy.deepcopy(base)
    event(docs, 'I22')['standard_refs'][0]['id'] = 'draft-ietf-oauth-transaction-tokens §9.1'
    assert errors(run(docs), 'COLUMNS', '版がない')


def test_product_reference_needs_verified_on(base):
    docs = copy.deepcopy(base)
    ref = dict(event(docs, 'I05')['idp']['auth0']['source_refs'][0])
    ref.pop('verified_on')
    event(docs, 'I05')['idp']['auth0']['source_refs'] = [ref]
    assert errors(run(docs), 'COLUMNS', 'verified_on')


def test_review_by_after_verified_on(base):
    docs = copy.deepcopy(base)
    event(docs, 'U01')['review_by'] = '2026-11-01'
    assert errors(run(docs), 'COLUMNS', 'review_by')


def test_unknown_token_kind_and_issued_by_mismatch_fail(base):
    docs = copy.deepcopy(base)
    event(docs, 'I05')['tokens_issued'].append('no_such_kind')
    assert errors(run(docs), 'KINDS', 'no_such_kind')
    docs = copy.deepcopy(base)
    k = next(k for k in docs['token_kinds']['kinds'] if k['id'] == 'txn_token')
    k['issued_by'] = []
    assert errors(run(docs), 'KINDS', 'issued_by')


def test_registry_kinds_must_be_token_kinds(base):
    docs = copy.deepcopy(base)
    docs['token_kinds']['kinds'] = [k for k in docs['token_kinds']['kinds'] if k['id'] != 'dpop_proof']
    assert errors(run(docs), 'KINDS', 'dpop_proof')


def test_sources_md_counts_must_match(base):
    docs = copy.deepcopy(base)
    n = run(base)['stats']['out_of_scope']
    docs['sources'] = docs['sources'].replace(f'対象外 {n} 件', f'対象外 {n - 1} 件')
    assert errors(run(docs), 'SOURCES', '件数')


def _list(docs, lid):
    return next(s for s in docs['seeds']['seed_lists'] if s['id'] == lid)


def _header(stats):
    return f"**対象外 {stats['out_of_scope']} 件／全 {stats['seed_items']} 件（{round(100 * stats['out_of_scope_ratio'])}%）**"


def test_removing_an_item_fails_even_if_counts_are_rewritten(base):
    # L1: the expected count of the external list catches a dropped item although the header and table are adjusted
    docs = copy.deepcopy(base)
    sl = _list(docs, 'iana-response-type')
    dropped = sl['items'].pop(0)
    for r in docs['issue_events']['events']:
        r['seeds'] = [s for s in r['seeds'] if s != f"iana-response-type/{dropped['id']}"]
    docs['sources'] = docs['sources'].replace(_header(cc.closure(base)[1]), _header(cc.closure(docs)[1]))
    docs['sources'] = docs['sources'].replace('| #2 | 10 | 3 |', '| #2 | 9 | 3 |', 1)
    res = run(docs)
    assert errors(res, 'CLOSURE', '出どころの件数')
    assert not errors(res, 'SOURCES')


def test_sources_table_counts_must_match_seeds(base):
    docs = copy.deepcopy(base)
    docs['sources'] = docs['sources'].replace('| #2 | 15 | 6 |', '| #2 | 99 | 0 |', 1)
    assert errors(run(docs), 'SOURCES', 'iana-oauth-uri')


def test_header_count_in_html_comment_is_ignored(base):
    docs = copy.deepcopy(base)
    right = _header(cc.closure(base)[1])
    docs['sources'] = docs['sources'].replace(right, right.replace('対象外 ', '対象外 9'), 1)
    docs['sources'] = f'<!-- {right} -->\n' + docs['sources']
    assert errors(run(docs), 'SOURCES', '件数')


def test_header_count_after_first_section_is_ignored(base):
    docs = copy.deepcopy(base)
    right = _header(cc.closure(base)[1])
    docs['sources'] = docs['sources'].replace(right, '（件数は下）', 1) + f'\n## 末尾\n\n{right}\n'
    assert errors(run(docs), 'SOURCES', '件数')


def test_duplicate_item_id_in_a_list_fails(base):
    docs = copy.deepcopy(base)
    sl = _list(docs, 'oidf-grant')
    sl['items'].append(copy.deepcopy(sl['items'][0]))
    assert errors(run(docs), 'CLOSURE', '重複')


@pytest.mark.parametrize('bad', ['ああああああああああああ', 'session-management'])
def test_weak_out_of_scope_reasons_fail(base, bad):
    docs = copy.deepcopy(base)
    item(docs, 'oidc-logout/session-management')['out_of_scope']['assumption'] = bad
    assert errors(run(docs), 'CLOSURE', 'oidc-logout/session-management')


def test_inferred_yes_fails(base):
    docs = copy.deepcopy(base)
    event(docs, 'I01')['idp']['keycloak']['hook_note'] = '一般の記述からの推論'
    assert errors(run(docs), 'COLUMNS', '推論')
