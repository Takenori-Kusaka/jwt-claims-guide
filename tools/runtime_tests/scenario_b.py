# -*- coding: utf-8 -*-
"""Reference receivers of scenario B for the propagation tests (Txn-Token, act, approval, edge headers), offline.

Written to templates/examples/scenario-b (token_types.yaml TXN / AGENT_AT / TASK_AT, hops.yaml H9 / H10 / H14 / H15,
claims.yaml C-act / C-req-wl / C-tctx / C-authorization-details). The DPoP proof of AGENT_AT / TASK_AT is not checked
here (cnf is only required to be present): the tests of #8 cover the claims, not the sender constraint.
"""
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from jose import decode_unverified  # noqa: E402
from validator import JwksCache, Reject, TokenValidator  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
DESIGN = os.path.join(ROOT, 'templates', 'examples', 'scenario-b')
NS = 'https://claims.example.com/'
TRUST_DOMAIN = 'https://corp.example.com'
GATEWAY_ID = 'spiffe://corp.example.com/gateway'   # the only workload allowed to request a TXN (C-req-wl assumption)
ORDERS_ID = 'spiffe://corp.example.com/orders'
MCP_ID = 'invoice-mcp'
AGENT_ID = 'agent:expense'
PAYMENT_TYPE = 'https://claims.example.com/rar/payment'
RAR_FIELDS = {'type', 'actions', 'identifier', 'instructedAmount', 'creditorAccount'}
IDENTITY_HEADER_PREFIX = 'x-user-'
SINGLE_HEADERS = ('authorization', 'txn-token', 'dpop')


def load_design(design_dir=DESIGN):
    tts = yaml.safe_load(open(os.path.join(design_dir, 'token_types.yaml'), encoding='utf-8'))['token_types']
    claims = yaml.safe_load(open(os.path.join(design_dir, 'claims.yaml'), encoding='utf-8'))['claims']
    return {t['id']: t for t in tts}, {c['id']: c for c in claims}


# ---------------------------------------------------------------- edge (gateway): identity headers from the client
def norm_header(name):
    return name.strip().lower().replace('_', '-')


def edge_filter(raw_headers):
    """raw_headers: list of (name, value) as received. Returns the headers forwarded inside.

    Identity headers (x-user-*) are dropped in every spelling (case, _ for -); a request that repeats Authorization,
    Txn-Token, DPoP or an identity header is rejected (catalog_answers.yaml U11, slide:p06-header-forwarding).
    """
    seen = {}
    for name, _ in raw_headers:
        n = norm_header(name)
        if n in SINGLE_HEADERS or n.startswith(IDENTITY_HEADER_PREFIX):
            seen[n] = seen.get(n, 0) + 1
    dup = sorted(n for n, k in seen.items() if k > 1)
    if dup:
        raise Reject('duplicate-header', ','.join(dup))
    return [(n, v) for n, v in raw_headers if not norm_header(n).startswith(IDENTITY_HEADER_PREFIX)]


def naive_edge_filter(raw_headers):
    """The mistake the test must catch: strip only the exact spelling X-User-Id."""
    return [(n, v) for n, v in raw_headers if n != 'X-User-Id']


# ---------------------------------------------------------------- ledger (H10): Txn-Token
class Ledger:
    def __init__(self, jwks_by_iss, design_dir=DESIGN):
        tts, claims = load_design(design_dir)
        self.txn_tt = tts['TXN']
        self.vocab = claims['C-tctx']['value_vocabulary']['values']
        self.v = TokenValidator(self.txn_tt, TRUST_DOMAIN, JwksCache(jwks_by_iss))
        self.audit = {}  # txn -> claims seen at the start of the chain (H9), the audit log the design compares with

    def record_start(self, claims):
        self.audit[claims['txn']] = claims

    def accept(self, headers, body, peer, now):
        h = {norm_header(k): v for k, v in headers.items()}
        auth = h.get('authorization', '')
        if auth.lower().startswith('bearer '):
            try:
                hdr, _ = decode_unverified(auth[7:].strip())
            except ValueError:
                hdr = {}
            if str(hdr.get('typ', '')).lower() == 'txntoken+jwt':
                raise Reject('txn-token-in-authorization')  # draft-ietf-oauth-transaction-tokens-11 §12
        tok = h.get('txn-token')
        if not tok:
            raise Reject('missing-txn-token')
        c = self.v.verify(tok, now)
        if c.get('req_wl') != GATEWAY_ID:
            raise Reject('req-wl-not-allowed', repr(c.get('req_wl')))
        if peer != ORDERS_ID:
            raise Reject('peer-mismatch', repr(peer))
        start = self.audit.get(c['txn'])
        if start is None:
            raise Reject('unknown-txn')
        problems = remint_violations(start, c)
        if problems:
            raise Reject('txn-changed', '; '.join(problems))
        tctx = c.get('tctx')
        if not isinstance(tctx, dict) or set(tctx) - set(self.vocab):
            raise Reject('tctx-shape', repr(tctx))
        op = tctx.get('operation')
        scopes = c.get('scope', '').split(' ')
        if op != 'ledger.read' or op not in scopes:
            raise Reject('tctx-scope-mismatch', f'operation {op!r}, scope {c.get("scope")!r}')
        if body.get('operation') != op:
            raise Reject('tctx-body-mismatch', f'body {body.get("operation")!r}, tctx {op!r}')
        return c


def remint_violations(up, down):
    """A Txn-Token passed on or re-minted must keep txn, sub, aud, req_wl and must not widen scope (draft-11 §13.6)."""
    out = []
    for k in ('txn', 'sub', 'aud', 'req_wl'):
        if up.get(k) != down.get(k):
            out.append(f'{k} changed')
    us, ds = set(str(up.get('scope', '')).split()), set(str(down.get('scope', '')).split())
    if not ds <= us:
        out.append(f'scope widened by {sorted(ds - us)}')
    if down.get('exp', 0) > up.get('exp', 0):
        out.append('exp extended')
    return out


# ---------------------------------------------------------------- invoices (H15): TASK_AT with act and authorization_details
class Invoices:
    def __init__(self, jwks_by_iss, design_dir=DESIGN, approvals=None):
        tts, claims = load_design(design_dir)
        self.v = TokenValidator(tts['TASK_AT'], 'invoices', JwksCache(jwks_by_iss))
        self.max_depth = tts['TASK_AT'].get('max_delegation_depth', 3)
        self.approvals = approvals if approvals is not None else {}
        self.owners = {'inv-1': 'u1', 'inv-2': 'u2'}

    def pay(self, token, body, peer, now):
        c = self.v.verify(token, now)
        act = c.get('act')
        if not isinstance(act, dict) or not isinstance(act.get('sub'), str):
            raise Reject('act-missing')
        # the CURRENT actor is the outermost act only (RFC 8693 §4.1); the nested ones are history
        if act['sub'] != MCP_ID or peer != MCP_ID:
            raise Reject('actor-mismatch', f'outermost act.sub {act["sub"]!r}, peer {peer!r}')
        inner = act.get('act')
        if not isinstance(inner, dict) or inner.get('sub') != AGENT_ID:
            raise Reject('delegation-chain-mismatch', f'inner act {inner!r}')
        depth, cur = 0, act
        while isinstance(cur, dict):
            depth += 1
            cur = cur.get('act')
        if depth > self.max_depth:
            raise Reject('delegation-too-deep', str(depth))
        if 'invoices.pay' not in str(c.get('scope', '')).split():
            raise Reject('scope-missing', 'invoices.pay')
        if self.owners.get(body.get('invoice')) != c['sub']:
            raise Reject('not-owner')
        ad = c.get('authorization_details')
        if not isinstance(ad, list) or len(ad) != 1 or not isinstance(ad[0], dict) or ad[0].get('type') != PAYMENT_TYPE:
            raise Reject('approval-missing')
        a = ad[0]
        if (a.get('identifier'), a.get('instructedAmount'), a.get('creditorAccount')) != \
                (body.get('invoice'), body.get('amount'), body.get('creditor')):
            raise Reject('approval-mismatch', 'amount / creditor / invoice differ from the approval')
        appr = c.get(NS, {}).get('approval_id')
        if self.approvals.get(appr) != 'active':
            raise Reject('approval-not-active', repr(appr))
        return {'paid': body['invoice'], 'by': c['sub'], 'actor': act['sub']}


# ---------------------------------------------------------------- sts: authorization_details of a request (RFC 9396 §5)
def sts_check_authorization_details(ad):
    if not isinstance(ad, list) or not ad:
        raise Reject('invalid_authorization_details', 'not a non-empty array')
    for d in ad:
        if not isinstance(d, dict) or d.get('type') != PAYMENT_TYPE:
            raise Reject('invalid_authorization_details', f'unknown type {d.get("type") if isinstance(d, dict) else d!r}')
        extra = set(d) - RAR_FIELDS
        if extra:
            raise Reject('invalid_authorization_details', f'unknown fields {sorted(extra)}')
        if d.get('actions') != ['pay']:
            raise Reject('invalid_authorization_details', f'actions {d.get("actions")!r}')
    return True
