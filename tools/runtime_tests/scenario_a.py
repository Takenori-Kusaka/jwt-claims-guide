# -*- coding: utf-8 -*-
"""Reference resource server (saas-api) and BFF (saas-web) of scenario A, written to its design.

The design is templates/examples/scenario-a (token_types.yaml AT, claims.yaml, hops.yaml H2 / H3, design.md 2. and 6.).
What the API does, in order (design.md 2.「境界の要点」, hops.yaml H2 validates.checks, claims.yaml enforced_at):
  1. the AT validator (validator.TokenValidator with the AT row: RS256 only, iss allowlist, keys per iss, typ at+jwt,
     aud saas-api, exp / iat with 30 s skew, exp - iat <= 300, required_claims)
  2. the tenant is taken from iss (the realm), never from the token value alone nor from a header; tenant_id must equal it
     and the path tenant must equal it (case-sensitive, no normalisation); tenant_id is a non-empty string <= 32 bytes
  3. user_id must equal sub; v must be a known version; roles is an array of at most 2, values outside the vocabulary
     are ignored
  4. every request reads tenants.status in the same transaction (tenant suspension takes effect at once, volatility 0)
  5. data: the tenant condition on every SQL and RLS with set_config('app.tenant', $1, true) per transaction (H3);
     an invoice is returned only when its owner_sub equals sub (BOLA key is sub only)
Unknown claims are ignored (slide:p04-forward-compatibility).
"""
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from validator import JwksCache, Reject, TokenValidator, get_path  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
DESIGN = os.path.join(ROOT, 'templates', 'examples', 'scenario-a')
NS = 'https://claims.example.com/'


def load_design(design_dir=DESIGN):
    tts = yaml.safe_load(open(os.path.join(design_dir, 'token_types.yaml'), encoding='utf-8'))['token_types']
    claims = yaml.safe_load(open(os.path.join(design_dir, 'claims.yaml'), encoding='utf-8'))['claims']
    return {t['id']: t for t in tts}, {c['id']: c for c in claims}


class MemoryStore:
    """Offline stand-in for Postgres: the same answers the design asks of the DB (tenant condition + owner)."""

    def __init__(self):
        self.tenants = {'t1': 'active', 't2': 'active'}
        self.invoices = {1: ('t2', 'bob-sub', 1000), 2: ('t1', 'alice-sub', 2000), 3: ('t1', 'carol-sub', 3000)}

    def tenant_status(self, tenant):
        return self.tenants.get(tenant)

    def invoice(self, tenant, inv_id, sub):
        row = self.invoices.get(inv_id)
        if row and row[0] == tenant and row[1] == sub:
            return {'id': inv_id, 'tenant_id': row[0], 'amount': row[2]}
        return None

    def list(self, tenant):
        return [{'id': i, 'tenant_id': r[0]} for i, r in sorted(self.invoices.items()) if r[0] == tenant]


class PgStore:
    """Postgres store of H3: one pooled connection reused across requests (the pool of the design), app role app_rls.

    Each request is one transaction: set_config('app.tenant', $1, true) with a bound parameter, then tenants.status,
    then the query with the tenant condition. The context disappears at commit.
    """

    def __init__(self, conn):
        self.db = conn

    def _tx(self, tenant, fn):
        with self.db.transaction():
            self.db.execute("SELECT set_config('app.tenant', %s, true)", (tenant,))
            return fn()

    def tenant_status(self, tenant):
        r = self._tx(tenant, lambda: self.db.execute('SELECT status FROM tenants WHERE id = %s', (tenant,)).fetchone())
        return r[0] if r else None

    def invoice(self, tenant, inv_id, sub):
        r = self._tx(tenant, lambda: self.db.execute(
            'SELECT id, tenant_id, amount FROM invoices WHERE id = %s AND tenant_id = %s AND owner_sub = %s', (inv_id, tenant, sub)).fetchone())
        return {'id': r[0], 'tenant_id': r[1], 'amount': r[2]} if r else None

    def list(self, tenant):
        rows = self._tx(tenant, lambda: self.db.execute('SELECT id, tenant_id FROM invoices WHERE tenant_id = %s ORDER BY id', (tenant,)).fetchall())
        return [{'id': r[0], 'tenant_id': r[1]} for r in rows]


class SaasApi:
    def __init__(self, jwks_by_iss, store=None, issuer_map=None, design_dir=DESIGN, fetch=None, url_fetcher=None, overrides=None):
        tts, claims = load_design(design_dir)
        at = dict(tts['AT'])
        at.update(overrides or {})  # only for the shortened-lifetime run of the revocation test (lifetime_revocation.md)
        m = issuer_map or {}
        self.tenant_of_iss = {m.get(i['iss'], i['iss']): i['iss'].rstrip('/').rsplit('/', 1)[1] for i in at['issuers']}
        uk = at.get('unknown_kid') or {}
        self.jwks = JwksCache(jwks_by_iss, fetch=fetch, refetch_min_interval=uk.get('refetch_min_interval_seconds', 300),
                              negative_cache=uk.get('negative_cache_seconds', 300))
        self.validator = TokenValidator(at, 'saas-api', self.jwks, issuer_map=m, url_fetcher=url_fetcher)
        self.c_tenant, self.c_user, self.c_roles, self.c_v = claims['C-tenant-id'], claims['C-user-id'], claims['C-roles'], claims['C-v']
        self.store = store or MemoryStore()

    def authorize(self, token, path_tenant, now, headers=None):
        """headers are accepted and never read (the tenant does not come from X-Tenant; casestudy A5)."""
        c = self.validator.verify(token, now)
        ns = c.get(NS)
        if not isinstance(ns, dict):
            raise Reject('claim-type', NS)
        tenant_iss = self.tenant_of_iss[c['iss']]
        t = ns.get('tenant_id')
        if not isinstance(t, str):
            raise Reject('claim-type', 'tenant_id')
        if t == '' or len(t.encode('utf-8')) > self.c_tenant.get('max_bytes', 32):
            raise Reject('claim-value', 'tenant_id')
        if t != tenant_iss:
            raise Reject('tenant-iss-mismatch', f'tenant_id {t!r} under iss of {tenant_iss}')
        if path_tenant != tenant_iss:
            raise Reject('tenant-path-mismatch', f'path {path_tenant!r}, token {tenant_iss}')
        if ns.get('user_id') != c['sub'] or not isinstance(c['sub'], str):
            raise Reject('user-id-mismatch')
        if ns.get('v') != '1':
            raise Reject('unknown-version', repr(ns.get('v')))
        roles = ns.get('roles', [])
        if not isinstance(roles, list) or not all(isinstance(r, str) for r in roles):
            raise Reject('claim-type', 'roles')
        if len(roles) > self.c_roles.get('max_items', 2):
            raise Reject('claim-value', 'roles: too many')
        vocab = set(self.c_roles['value_vocabulary']['values'])
        status = self.store.tenant_status(tenant_iss)
        if status != 'active':
            raise Reject('tenant-suspended', repr(status))
        return {'tenant': tenant_iss, 'sub': c['sub'], 'roles': [r for r in roles if r in vocab], 'claims': c}

    def get_invoice(self, token, path_tenant, inv_id, now, headers=None):
        ctx = self.authorize(token, path_tenant, now, headers)
        row = self.store.invoice(ctx['tenant'], inv_id, ctx['sub'])
        if row is None:
            raise Reject('not-found', f'invoice {inv_id}')  # same answer for "other tenant" and "other owner"
        return row

    def list_invoices(self, token, path_tenant, now, headers=None):
        ctx = self.authorize(token, path_tenant, now, headers)
        return self.store.list(ctx['tenant'])


class Bff:
    """saas-web: holds AT and RT server-side; refreshes when the AT has expired (now >= issued + lifetime); ends its own session when a refresh fails.

    refresh(rt) -> token response dict or raises; the BFF session ends on the first failure (token_types BFFSESSION
    revocation refresh_failure, design: IdP-side session end / user disabled is noticed within the 330 s bound).
    """

    def __init__(self, token_response, refresh, at_lifetime):
        self.at, self.rt = token_response['access_token'], token_response.get('refresh_token')
        self.refresh_fn, self.at_lifetime = refresh, at_lifetime
        self.issued = None
        self.active = True
        self.ended_reason = None

    def call(self, api, path_tenant, now, issued_at):
        if not self.active:
            raise Reject('bff-session-ended', self.ended_reason or '')
        if self.issued is None:
            self.issued = issued_at
        if now >= self.issued + self.at_lifetime:  # AT expired: refresh with the RT
            try:
                r = self.refresh_fn(self.rt)
            except Exception as e:  # noqa: BLE001 - any refresh failure ends the BFF session
                self.active, self.ended_reason = False, f'refresh failed: {e}'
                raise Reject('bff-session-ended', self.ended_reason)
            self.at, self.rt, self.issued = r['access_token'], r.get('refresh_token', self.rt), now
        return api.list_invoices(self.at, path_tenant, now)


def tenant_of(claims):
    v, _ = get_path(claims, [NS, 'tenant_id'])
    return v
