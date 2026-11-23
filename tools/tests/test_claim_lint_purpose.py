# -*- coding: utf-8 -*-
"""Tests of the claim_lint purpose and mechanism rules (#18): L11-L14, a pass and a fail case each. These rules check that
the declarations agree with each other; the runtime tests of #8 (test:negative_tests#tctx-mismatch,
#approval-mismatch for L11, #nested-act for L12) check that a consumer really refuses."""
import copy
import datetime
import os
import sys

import pytest
import yaml

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from claim_lint import core, purpose  # noqa: E402

EXAMPLE = os.path.join(ROOT, 'templates', 'examples', 'scenario-a')
FILES = ('claims', 'token_types', 'catalog_answers', 'hops')
TODAY = datetime.date(2026, 11, 23)
_BASE = {k: core.load_yaml(os.path.join(EXAMPLE, k + '.yaml')) for k in FILES}


def base():
    return copy.deepcopy(_BASE)


def run(docs):
    return purpose.run(docs, ROOT)[0]


def by(findings, rule):
    # the known warning of scenario A (scope carried but unused, ASVS part of L11) is left out of the fail cases
    return [f for f in findings if f['rule'] == rule and f['severity'] in ('error', 'warn')
            and not (f['rule'] == 'L11' and f['target'] == 'C-scope' and 'ASVS' in f['message'])]


def claim(docs, cid):
    return next(c for c in docs['claims']['claims'] if c['id'] == cid)


def new_claim(**kw):
    c = copy.deepcopy(claim(_BASE, 'C-v'))
    c.pop('answers', None)
    c.update(kw)
    return c


@pytest.fixture(scope='module')
def example():
    return core.run(EXAMPLE, today=TODAY)


def test_example_has_no_purpose_error_and_one_known_warning(example):
    got = [(f['rule'], f['severity'], f['target']) for f in example['findings'] if f['rule'] in purpose.SEV and f['severity'] != 'info']
    # the scope of the Keycloak AT (openid only) is carried but not used for decisions: ASVS 10.3.2 part of L11 (warn)
    assert got == [('L11', 'warn', 'C-scope')], core.format_table(example)
    assert all(example['checked'].get(r, 0) > 0 for r in ('L11', 'L12', 'L13'))


# ------------------------------------------------------------------ L11
def test_l11_consumer_without_enforced_at_fails():
    d = base()
    claim(d, 'C-roles')['consumers'] = ['saas-api', 'billing']
    assert [f['target'] for f in by(run(d), 'L11')] == ['C-roles']


def test_l11_tctx_items_without_rules_fail_and_with_rules_pass():
    d = base()
    d['claims']['claims'].append(new_claim(id='C-tctx', name='tctx', namespace=None, type='object', usage='authz',
                                           value_vocabulary={'values': ['tenant', 'amount'], 'owner': 'x', 'extensible': False},
                                           enforced_at=[{'service': 'saas-api', 'check': 'tenant を本文のテナントと照合'}]))
    msgs = [f['message'] for f in by(run(d), 'L11')]
    assert len(msgs) == 1 and 'amount' in msgs[0]
    claim(d, 'C-tctx')['enforced_at'].append({'service': 'saas-api', 'check': 'amount を本文の金額と照合'})
    assert not by(run(d), 'L11')


def test_l11_scope_in_at_unused_warns():
    d = base()
    c = claim(d, 'C-scope')
    c['enforced_at'] = []
    f = [x for x in run(d) if x['rule'] == 'L11']
    assert [(x['target'], x['severity']) for x in f] == [('C-scope', 'warn')]
    c['enforced_at'] = [{'service': 'saas-api', 'check': 'scope に openid があること'}]
    assert not [x for x in run(d) if x['rule'] == 'L11']


# ------------------------------------------------------------------ L12
def test_l12_same_question_in_answers_and_does_not_answer_fails():
    d = base()
    claim(d, 'C-sub')['does_not_answer'] = ['q-sub']
    assert [f['target'] for f in by(run(d), 'L12')] == ['C-sub']


def test_l12_nested_act_as_current_actor_fails():
    d = base()
    d['claims']['claims'].append(new_claim(id='C-act-nested', name='act', namespace=None, type='object', path=['act', 'act'],
                                           answers=['q-actor']))
    msgs = ' '.join(f['message'] for f in by(run(d), 'L12'))
    assert 'RFC 8693 §4.1' in msgs


def test_l12_outermost_act_for_actor_and_nested_for_via_pass():
    d = base()
    d['claims']['claims'].append(new_claim(id='C-act', name='act', namespace=None, type='object', path=['act'], answers=['q-actor']))
    d['claims']['claims'].append(new_claim(id='C-act-nested', name='act', namespace=None, type='object', path=['act', 'act'],
                                           answers=['q-via'], does_not_answer=['q-actor']))
    assert not by(run(d), 'L12')


def test_l12_conflated_questions_fail():
    d = base()
    claim(d, 'C-sub')['answers'] = ['q-sub', 'q-actor']  # q-actor is in not_this of q-sub (questions.yaml)
    assert [f['target'] for f in by(run(d), 'L12')] == ['C-sub']


# ------------------------------------------------------------------ L13
def test_l13_needed_question_without_mechanism_fails():
    d = base()
    d['catalog_answers']['questions']['q-holder'] = {'needed': True}
    assert [f['target'] for f in by(run(d), 'L13')] == ['q-holder']


def test_l13_channel_counts_as_mechanism():
    d = base()
    d['catalog_answers']['questions']['q-peer'] = {'needed': True, 'channel': 'mTLS の相手の SPIFFE ID'}
    assert not by(run(d), 'L13')


def test_l13_missing_section_or_reason_fails():
    d = base()
    d['catalog_answers']['questions']['q-txn'] = {'needed': False}
    assert [f['target'] for f in by(run(d), 'L13')] == ['q-txn']
    d['catalog_answers'].pop('questions')
    assert [f['target'] for f in by(run(d), 'L13')] == ['questions']


# ------------------------------------------------------------------ L14
def test_l14_draft_claim_without_version_warns_and_with_version_pass():
    d = base()
    d['claims']['claims'].append(new_claim(id='C-txn', name='txn', namespace=None, revisit_trigger=None))
    d['claims']['claims'][-1].pop('revisit_trigger', None)
    f = by(run(d), 'L14')
    assert [(x['target'], x['severity']) for x in f] == [('C-txn', 'warn')] and 'spec_version' in f[0]['message']
    claim(d, 'C-txn').update(spec_version=['draft-ietf-oauth-transaction-tokens-11'], revisit_trigger='草案が RFC になったとき')
    assert not by(run(d), 'L14')


def test_l14_preview_ref_and_purp_warn():
    d = base()
    d['claims']['claims'].append(new_claim(id='C-purp', name='purp', namespace=None,
                                           refs=[{'kind': 'spec', 'id': 'Keycloak 26.8 delegation (preview)'}],
                                           spec_version=['keycloak-26.8-preview'], revisit_trigger='正式になったとき'))
    msgs = [f['message'] for f in by(run(d), 'L14')]
    assert len(msgs) == 1 and 'purp' in msgs[0]


def test_l14_no_draft_in_example(example):
    assert not [f for f in example['findings'] if f['rule'] == 'L14']
