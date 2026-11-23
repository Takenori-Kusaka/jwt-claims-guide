# -*- coding: utf-8 -*-
"""Golden tokens (templates/runtime/golden_tokens.md): the legitimate tokens that every negative test starts from.

Each golden token is a header and a payload built here and signed at run time with a test key made in memory
(jose.Key). Nothing signed is committed. Issuers contain `example`. A negative test changes ONE thing in a golden
token, so that the rejection can only come from that change; the legitimate golden token itself must be accepted
(the `golden-accepted` check of every run).
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jose import Key, encode  # noqa: E402

NOW = 1_800_000_000          # fixed clock of the offline run (2027-01-15T08:00:00Z)
NS = 'https://claims.example.com/'
A_ISS = {'t1': 'https://idp.example.com/realms/t1', 't2': 'https://idp.example.com/realms/t2'}
STS_ISS = 'https://sts.corp.example.com'
TTS_ISS = 'https://tts.corp.example.com'


class Keys:
    """All test keys of one run. t1 / t2: the realm keys of scenario A; attacker: a key nobody configured;
    partner_t2: a key t2 handed to an integration partner (casestudy A9); sts / tts: scenario B (ES256)."""

    def __init__(self):
        self.t1, self.t2 = Key('t1-rs256'), Key('t2-rs256')
        self.attacker = Key('t1-rs256')          # same kid as t1's key: only the key material differs
        self.attacker_own = Key('attacker-1')
        self.sts, self.tts = Key('sts-es256', 'EC'), Key('tts-es256', 'EC')

    def jwks_a(self):
        return {A_ISS['t1']: {'keys': [self.t1.jwk()]}, A_ISS['t2']: {'keys': [self.t2.jwk()]}}

    def jwks_b(self):
        return {STS_ISS: {'keys': [self.sts.jwk()]}, TTS_ISS: {'keys': [self.tts.jwk()]}}


def at_payload(tenant='t1', sub='alice-sub', now=NOW, lifetime=300):
    """Scenario A AT in the shape Keycloak 26.8 issued for the slice (tools/tests/fixtures/claim_lint/golden/token.json),
    with the issuer of the design (https://idp.example.com/realms/<tenant>) and test values."""
    return {
        'exp': now + lifetime, 'iat': now, 'auth_time': now, 'jti': 'onrtac:00000000-0000-4000-8000-000000000001',
        'iss': A_ISS[tenant], 'aud': 'saas-api', 'sub': sub, 'typ': 'Bearer', 'azp': 'saas-web',
        'sid': 'golden-session-1', 'scope': 'openid',
        NS: {'tenant_id': tenant, 'user_id': sub, 'v': '1', 'roles': ['approver']},
    }


def at_header(key):
    return {'alg': 'RS256', 'typ': 'at+jwt', 'kid': key.kid}


def mint_at(keys, tenant='t1', sub='alice-sub', now=NOW, header=None, payload=None, key=None, **kw):
    k = key or getattr(keys, tenant)
    return encode(header or at_header(k), payload or at_payload(tenant, sub, now), key=k, **kw)


def txn_payload(now=NOW, scope='orders.read ledger.read', operation='ledger.read'):
    return {'iss': TTS_ISS, 'iat': now, 'exp': now + 300, 'aud': 'https://corp.example.com', 'txn': 'txn-0001',
            'sub': 'emp-0001', 'scope': scope, 'req_wl': 'spiffe://corp.example.com/gateway', 'tctx': {'operation': operation},
            'jti': 'txn-jti-1'}


def mint_txn(keys, payload=None, typ='txntoken+jwt', key=None):
    k = key or keys.tts
    return encode({'alg': 'ES256', 'typ': typ, 'kid': k.kid}, payload or txn_payload(), key=k)


def task_payload(now=NOW, amount=120000, creditor='JP00-1234-5678', invoice='inv-1'):
    return {
        'iss': STS_ISS, 'sub': 'u1', 'aud': 'invoices', 'exp': now + 300, 'iat': now, 'jti': 'task-jti-1',
        'client_id': 'invoice-mcp', 'scope': 'invoices.pay', 'cnf': {'jkt': 'golden-thumbprint'},
        'act': {'sub': 'invoice-mcp', 'act': {'sub': 'agent:expense'}},
        'authorization_details': [{'type': 'https://claims.example.com/rar/payment', 'actions': ['pay'], 'identifier': invoice,
                                   'instructedAmount': amount, 'creditorAccount': creditor}],
        NS: {'tenant_id': 'corp', 'user_id': 'u1', 'task_id': 'task-1', 'approval_id': 'appr-1', 'v': '1'},
    }


def agent_payload(now=NOW):
    p = task_payload(now)
    p.update(aud='invoice-mcp', client_id='agent:expense', scope='invoices.read invoices.pay', act={'sub': 'agent:expense'}, jti='agent-jti-1')
    return p


def mint_sts(keys, payload, typ='at+jwt', key=None):
    k = key or keys.sts
    return encode({'alg': 'ES256', 'typ': typ, 'kid': k.kid}, payload, key=k)


def changed(payload, path, value):
    """Copy of payload with one member changed (path: list of keys); value DELETE removes it."""
    p = copy.deepcopy(payload)
    cur = p
    for k in path[:-1]:
        cur = cur[k]
    if value is DELETE:
        cur.pop(path[-1], None)
    else:
        cur[path[-1]] = value
    return p


DELETE = object()
