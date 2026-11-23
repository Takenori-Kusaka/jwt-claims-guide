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
PAYMENT_TYPE = 'https://claims.example.com/rar/payment'
RAR_FIELDS = {'type', 'actions', 'identifier', 'instructedAmount', 'creditorAccount'}
IDENTITY_HEADER_PREFIX = 'x-user-'
SINGLE_HEADERS = ('authorization', 'txn-token', 'dpop')


def load_design(design_dir=DESIGN):
    tts = yaml.safe_load(open(os.path.join(design_dir, 'token_types.yaml'), encoding='utf-8'))['token_types']
    claims = yaml.safe_load(open(os.path.join(design_dir, 'claims.yaml'), encoding='utf-8'))['claims']
    return {t['id']: t for t in tts}, {c['id']: c for c in claims}


def load_hops(design_dir=DESIGN):
    return {h['id']: h for h in yaml.safe_load(open(os.path.join(design_dir, 'hops.yaml'), encoding='utf-8'))['hops']}


def service(name):
    """'gateway（入口）' -> 'gateway': the service name of a hops.yaml from / to."""
    return name.split('（', 1)[0].strip()


class Design:
    """The values the receivers compare with, read from the scenario B registry (not constants).

    - trust domain: TXN aud. SPIFFE IDs are spiffe://<host of the trust domain>/<service of hops.yaml>, the naming
      convention of this harness (claims.yaml C-req-wl says only "the gateway's SPIFFE ID")
    - who may request a TXN (req_wl): the `from` of H9, the hop where the TXN starts
    - the peer of ledger: the `from` of H10; the peer and current actor at invoices: the `from` of H15
    - the aud at invoices: TASK_AT aud, compared as exactly that value (H15 checks: aud が invoices だけ)
    - the operations of each current actor (H15 checks: act の方針表で、その代理者に許した操作だけ): the H15 scope
    """

    def __init__(self, design_dir=DESIGN):
        self.tts, self.claims = load_design(design_dir)
        self.hops = load_hops(design_dir)
        self.trust_domain = self.tts['TXN']['aud'][0]
        self.host = self.trust_domain.split('://', 1)[1].rstrip('/')
        self.txn_requester = self.spiffe(service(self.hops['H9']['from']))
        self.ledger_peer = self.spiffe(service(self.hops['H10']['from']))
        self.mcp = service(self.hops['H15']['from'])
        self.invoices_aud = list(self.tts['TASK_AT']['aud'])
        self.actor_ops = {self.mcp: {s.split('.', 1)[1] for s in self.hops['H15']['scope']}}   # invoice-mcp: {pay}

    def spiffe(self, svc):
        return f'spiffe://{self.host}/{svc}'


D = Design()   # the values of the committed example, for the tests


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
        self.d = Design(design_dir)
        self.txn_tt = self.d.tts['TXN']
        self.vocab = self.d.claims['C-tctx']['value_vocabulary']['values']
        self.v = TokenValidator(self.txn_tt, self.d.trust_domain, JwksCache(jwks_by_iss))
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
        if c.get('req_wl') != self.d.txn_requester:
            raise Reject('req-wl-not-allowed', repr(c.get('req_wl')))
        if peer != self.d.ledger_peer:
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
    """Differences between the Txn-Token at the start of the chain (up) and the one received (down).

    From draft-ietf-oauth-transaction-tokens-11: §13.15 (a replacement Txn-Token keeps txn, sub and aud) and §13.6 (the
    scope issued is the same as or narrower than the subject token's), so a widened scope is a finding. Two more are
    ORGANIZATION rules of the scenario B example, not rules of the draft (findings marked "org rule"):
      - req_wl unchanged: §13.15 does not name req_wl (it asks to keep the call chain); the example uses req_wl to record
        which entry point started the transaction (claims.yaml C-req-wl), and a changed req_wl breaks that record
      - exp not extended: §13.15 allows (MAY) a replacement that lives longer than the original; the example keeps the
        lifetime at most the original's (hops.yaml H9 note: 寿命は INT_AT と同じ 300 秒を上限にする)
    """
    out = []
    for k in ('txn', 'sub', 'aud'):
        if up.get(k) != down.get(k):
            out.append(f'{k} changed (draft-11 §13.15)')
    us, ds = set(str(up.get('scope', '')).split()), set(str(down.get('scope', '')).split())
    if not ds <= us:
        out.append(f'scope widened by {sorted(ds - us)} (draft-11 §13.6)')
    if up.get('req_wl') != down.get('req_wl'):
        out.append('req_wl changed (org rule: C-req-wl)')
    if down.get('exp', 0) > up.get('exp', 0):
        out.append('exp extended (org rule: H9 note)')
    return out


# ---------------------------------------------------------------- invoices (H15): TASK_AT with act and authorization_details
class Invoices:
    """invoices (H15). Authorization reads the outermost act only: RFC 8693 §4.1 says the nested act claims are
    informational and are not used for access control. A nested act is therefore never a reason to grant anything,
    and a token is not rejected for what its nested act says. One ORGANIZATION rule counts the chain without reading it:
    the depth limit (TASK_AT max_delegation_depth 3, the casestudy's depth_rule). The H15 check of the example
    「その内側が agent:expense」 would read the nested act for a decision; this receiver does not implement it (returned
    to the owners of the example, #6 / #18).
    """

    def __init__(self, jwks_by_iss, design_dir=DESIGN, approvals=None):
        self.d = Design(design_dir)
        tt = self.d.tts['TASK_AT']
        self.v = TokenValidator(tt, self.d.invoices_aud[0], JwksCache(jwks_by_iss))
        self.max_depth = tt.get('max_delegation_depth', 3)
        self.approvals = approvals if approvals is not None else {}
        self.owners = {'inv-1': 'u1', 'inv-2': 'u2'}

    def _authorize(self, token, op, peer, now):
        c = self.v.verify(token, now)
        aud = c.get('aud')
        if (aud if isinstance(aud, list) else [aud]) != self.d.invoices_aud:   # H15: aud が invoices だけ
            raise Reject('aud-mismatch', f'aud {aud!r} is not exactly {self.d.invoices_aud}')
        act = c.get('act')
        if not isinstance(act, dict) or not isinstance(act.get('sub'), str):
            raise Reject('act-missing')
        actor = act['sub']   # the CURRENT actor: the outermost act only (RFC 8693 §4.1)
        if actor != peer:
            raise Reject('actor-mismatch', f'outermost act.sub {actor!r}, peer {peer!r}')
        if op not in self.d.actor_ops.get(actor, set()):
            raise Reject('actor-not-allowed', f'{actor!r} may not {op}')
        depth, cur = 0, act
        while isinstance(cur, dict):
            depth += 1
            cur = cur.get('act')
        if depth > self.max_depth:   # organization rule (max_delegation_depth); the names in the chain are not read
            raise Reject('delegation-too-deep', str(depth))
        if f'invoices.{op}' not in str(c.get('scope', '')).split():
            raise Reject('scope-missing', f'invoices.{op}')
        return c, actor

    def refund(self, token, body, peer, now):
        """An operation that no current actor of the example may do (the H15 scope is invoices.pay only)."""
        c, actor = self._authorize(token, 'refund', peer, now)
        return {'refunded': body.get('invoice'), 'actor': actor}

    def pay(self, token, body, peer, now):
        c, actor = self._authorize(token, 'pay', peer, now)
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
        return {'paid': body['invoice'], 'by': c['sub'], 'actor': actor}


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
