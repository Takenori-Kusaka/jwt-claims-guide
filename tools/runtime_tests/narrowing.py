# -*- coding: utf-8 -*-
"""Runtime check of "narrow downstream" (slide:p06-narrow-downstream, lint L16) on two real tokens.

L16 checks the DECLARATION (hops.yaml). This checks what an exchange or a re-mint actually ISSUED: the downstream
token's aud, scope, exp, authorization_details and custom claims against the upstream token and the hop declaration.

Rules (the runtime form of L16):
  aud      every value is in the upstream aud, or the hop declares aud_replacement with a single target and the
           downstream aud is exactly that one target (the exception of L16 (1))
  scope    a subset of the upstream scope. For Keycloak, client scopes that only carry an audience mapper
           (audience_scopes: scope name -> audience) are compared as aud, not as scope
  exp      not later than the upstream exp
  authorization_details  every entry equals an upstream entry
  custom   every custom claim (under the namespace) exists upstream with the same value
"""


def _aud(v):
    if v is None:
        return []
    return [v] if isinstance(v, str) else list(v)


def _scope(v):
    return set(str(v or '').split())


def check(upstream, downstream, hop=None, audience_scopes=None, ns='https://claims.example.com/', ignore_aud=()):
    """Return a list of findings (empty = narrowed). upstream / downstream are payload dicts."""
    hop = hop or {}
    aud_scopes = audience_scopes or {}
    found = []
    up_aud = set(_aud(upstream.get('aud'))) - set(ignore_aud)
    down_aud = [a for a in _aud(downstream.get('aud')) if a not in ignore_aud]
    up_scope = {s for s in _scope(upstream.get('scope')) if s not in aud_scopes}
    down_scope_all = _scope(downstream.get('scope'))
    down_scope = {s for s in down_scope_all if s not in aud_scopes}
    # aud
    if hop.get('aud_replacement'):
        target = list(hop.get('aud', []))
        if len(target) != 1 or down_aud != target:
            extra = [a for a in down_aud if a not in target]
            found.append(f'aud {down_aud} is not the declared single replacement {target}' + (f' (added {extra})' if extra else ''))
    else:
        extra = [a for a in down_aud if a not in up_aud]
        if extra:
            found.append(f'aud widened by {extra} (upstream {sorted(up_aud)})')
    # audience carried by a Keycloak audience scope must also be allowed
    for s in sorted(down_scope_all & set(aud_scopes)):
        a = aud_scopes[s]
        if a not in up_aud and not (hop.get('aud_replacement') and [a] == list(hop.get('aud', []))):
            found.append(f'scope {s} carries audience {a}, which is neither upstream nor the declared target')
    # scope
    if down_scope - up_scope:
        found.append(f'scope widened by {sorted(down_scope - up_scope)} (upstream {sorted(up_scope)})')
    # exp
    ue, de = upstream.get('exp'), downstream.get('exp')
    if isinstance(ue, (int, float)) and isinstance(de, (int, float)) and de > ue:
        found.append(f'exp extended by {de - ue} s beyond the upstream exp')
    # authorization_details
    uad = upstream.get('authorization_details') or []
    for d in downstream.get('authorization_details') or []:
        if d not in uad:
            found.append(f'authorization_details entry not upstream: {d}')
    # custom claims under the namespace
    uns, dns = upstream.get(ns) or {}, downstream.get(ns) or {}
    for k, v in dns.items():
        if k not in uns:
            found.append(f'custom claim {k} added')
        elif uns[k] != v:
            found.append(f'custom claim {k} changed {uns[k]!r} -> {v!r}')
    return found
