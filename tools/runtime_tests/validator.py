# -*- coding: utf-8 -*-
"""Reference token validator built from a token type of the registry (templates/registry/token_types.schema.json).

It reads the declaration (issuers, alg_allowlist, typ, aud, required_claims, max_clock_skew, max_lifetime,
key_source) and applies it in the order of slide:p01-validation-order. It is a reference for the tests of #8,
not a library to deploy: the tests show that a validator written to the DESIGN rejects what it should.

Every rejection raises Reject(code). The codes are stable, the tests compare them.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jose import DuplicateMember, b64d, public_from_jwk, strict_json, verify_sig  # noqa: E402

HEADER_KEY_PARAMS = ('jku', 'x5u', 'jwk', 'x5c')  # RFC 8725 §3.10 / slide:p01-dangerous-header-params


class Reject(Exception):
    def __init__(self, code, detail=''):
        super().__init__(f'{code}: {detail}' if detail else code)
        self.code, self.detail = code, detail


def claim_path(name):
    """'https://claims.example.com/.tenant_id' -> ['https://claims.example.com/', 'tenant_id']; 'sub' -> ['sub']."""
    if '/.' in name:
        ns, rest = name.rsplit('/.', 1)
        return [ns + '/', rest]
    return [name]


def get_path(claims, path):
    cur = claims
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return None, False
        cur = cur[p]
    return cur, True


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _typ_norm(t):
    t = t.lower()  # RFC 7515 §4.1.9: media type names are case-insensitive; "application/" may be omitted
    return t[len('application/'):] if t.startswith('application/') else t


class JwksCache:
    """Keys per issuer. The keys come from configuration (the issuer's jwks_uri), never from the token header.

    fetch(iss) -> JWKS dict is called at most once per refetch_min_interval for an unknown kid (token_types.unknown_kid);
    a kid still unknown after a fetch is rejected without fetching again during negative_cache_seconds.
    """

    def __init__(self, jwks_by_iss, fetch=None, refetch_min_interval=300, negative_cache=300):
        self.keys = {iss: self._load(j) for iss, j in jwks_by_iss.items()}
        self.fetch, self.min_interval, self.negative = fetch, refetch_min_interval, negative_cache
        self.last_fetch, self.neg, self.fetches = {}, {}, []

    @staticmethod
    def _load(jwks):
        out = {}
        for j in jwks.get('keys', []):
            if j.get('use', 'sig') == 'sig' and 'kid' in j:
                try:
                    out[j['kid']] = (j.get('alg'), public_from_jwk(j))
                except (ValueError, KeyError):
                    continue
        return out

    def get(self, iss, kid, now):
        k = self.keys.get(iss, {}).get(kid)
        if k or self.fetch is None:
            return k
        if self.neg.get((iss, kid), -1) > now:
            return None
        if now - self.last_fetch.get(iss, -10**12) >= self.min_interval:
            self.last_fetch[iss] = now
            self.fetches.append(iss)
            self.keys[iss] = self._load(self.fetch(iss))
            k = self.keys[iss].get(kid)
        if not k:
            self.neg[(iss, kid)] = now + self.negative
        return k


class TokenValidator:
    def __init__(self, tt, audience, jwks, issuer_map=None, url_fetcher=None):
        """tt: one token_types entry (dict). audience: this receiver's name in aud. jwks: JwksCache.

        issuer_map maps a declared iss to the iss of the test environment (e.g. https://idp.example.com/realms/t1 ->
        http://localhost:28080/realms/t1); exact comparison still applies after the mapping.
        url_fetcher is what a naive library would use to follow jku / x5u. It must never be called; the tests count calls.
        """
        self.tt = tt
        m = issuer_map or {}
        self.issuers = [m.get(i['iss'], i['iss']) for i in tt.get('issuers', [])]
        self.algs = list(tt.get('alg_allowlist', []))
        self.typ = tt.get('typ')
        self.audience = audience
        self.required = [claim_path(c) for c in tt.get('required_claims', [])]
        self.skew = tt.get('max_clock_skew') or 0
        self.max_lifetime = tt.get('max_lifetime')
        self.jwks = jwks
        self.url_fetcher = url_fetcher
        self.wrap = None
        ks = tt.get('key_source') or {}
        self.header_key_params = ks.get('header_key_params', 'reject')

    def verify(self, token, now):
        if not isinstance(token, str) or token.count('.') != 2:
            raise Reject('malformed', 'not a compact JWS')
        h64, p64, s64 = token.split('.')
        try:
            header = strict_json(b64d(h64))
        except DuplicateMember as e:
            raise Reject('duplicate-member', f'header: {e}')
        except ValueError as e:
            raise Reject('malformed', f'header: {e}')
        if not isinstance(header, dict):
            raise Reject('malformed', 'header is not an object')
        # 1. alg: allowlist fixed per key type; none and HS* are not on it (RFC 8725 §3.1, §3.2)
        alg = header.get('alg')
        if alg not in self.algs:
            raise Reject('alg-not-allowed', repr(alg))
        # 2. header key parameters are not followed nor trusted (key_source.header_key_params: reject)
        present = [p for p in HEADER_KEY_PARAMS if p in header]
        if present and self.header_key_params == 'reject':
            raise Reject('header-key-param', ','.join(present))
        if 'crit' in header:
            raise Reject('crit-unknown', repr(header['crit']))
        # 3. typ (explicit typing, RFC 8725 §3.11)
        if self.typ:
            t = header.get('typ')
            if not isinstance(t, str) or _typ_norm(t) != _typ_norm(self.typ):
                raise Reject('typ-mismatch', repr(t))
        try:
            payload = strict_json(b64d(p64))
        except DuplicateMember as e:
            raise Reject('duplicate-member', f'payload: {e}')
        except ValueError as e:
            raise Reject('malformed', f'payload: {e}')
        if not isinstance(payload, dict):
            raise Reject('malformed', 'payload is not an object')
        if self.wrap:  # the consumer contract test records which members are read (contract.Recording)
            payload = self.wrap(payload)
        # 4. iss: exact match against the allowlist, before any key is chosen
        iss = payload.get('iss')
        if not isinstance(iss, str) or iss not in self.issuers:
            raise Reject('iss-not-allowed', repr(iss))
        # 5. key: only the keys registered for THIS issuer (Storm-0558: a key of another issuer must not verify)
        kid = header.get('kid')
        key = self.jwks.get(iss, kid, now) if isinstance(kid, str) else None
        if not key:
            raise Reject('unknown-kid', f'{kid!r} for {iss}')
        key_alg, public = key
        if key_alg and key_alg != alg:
            raise Reject('alg-key-mismatch', f'{alg} with a {key_alg} key')
        try:
            sig = b64d(s64)
        except ValueError:
            raise Reject('malformed', 'signature')
        if not verify_sig(alg, public, f'{h64}.{p64}'.encode('ascii'), sig):
            raise Reject('bad-signature')
        # 6. required claims (presence), then the types the checks below rely on
        for path in self.required:
            v, ok = get_path(payload, path)
            if not ok or v is None:
                raise Reject('missing-claim', '.'.join(path))
        for name in ('exp', 'iat', 'nbf'):
            if name in payload and not _num(payload[name]):
                raise Reject('claim-type', name)
        # 7. time: exp / nbf / iat with the declared skew; exp - iat within max_lifetime (no skew added)
        exp = payload.get('exp')
        if exp is not None and now > exp + self.skew:
            raise Reject('expired', f'now - exp = {now - exp}')
        if 'nbf' in payload and now + self.skew < payload['nbf']:
            raise Reject('not-yet-valid', f'nbf - now = {payload["nbf"] - now}')
        iat = payload.get('iat')
        if iat is not None and iat > now + self.skew:
            raise Reject('iat-in-future', f'iat - now = {iat - now}')
        if self.max_lifetime is not None and exp is not None and iat is not None and exp - iat > self.max_lifetime:
            raise Reject('lifetime-too-long', f'exp - iat = {exp - iat}')
        # 8. aud: a string or an array of strings that contains this receiver
        aud = payload.get('aud')
        if aud is not None or ['aud'] in self.required:
            if isinstance(aud, str):
                auds = [aud]
            elif isinstance(aud, list) and aud and all(isinstance(a, str) for a in aud):
                auds = aud
            else:
                raise Reject('claim-type', 'aud')
            if self.audience not in auds:
                raise Reject('aud-mismatch', repr(aud))
        return payload
