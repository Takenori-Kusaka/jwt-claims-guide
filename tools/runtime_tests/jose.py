# -*- coding: utf-8 -*-
"""Minimal JOSE helpers for the runtime tests (#8): test keys, signing by hand, strict parsing.

Tokens are signed by hand (not with a JWT library) so that a test can put anything in the header or the payload:
alg=none, a duplicated member, an HMAC signature keyed with an RSA public key, a jku / jwk header, a huge integer.

Keys are made in memory for each run (RSA 2048 / P-256) and never written to disk, so no private key can reach
the repository (templates/CONTRIBUTING.md 4.). Issuers of self-made tokens contain `example` (golden_tokens.md).
"""
import base64
import hashlib
import hmac
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature


def b64e(b):
    return base64.urlsafe_b64encode(b).rstrip(b'=').decode('ascii')


def b64d(s):
    if not isinstance(s, str) or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_' for c in s):
        raise ValueError('not base64url')
    return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))


def _int_b64(n):
    return b64e(n.to_bytes((n.bit_length() + 7) // 8, 'big'))


class DuplicateMember(ValueError):
    pass


def strict_json(raw):
    """json.loads that rejects a duplicated member at any depth (RFC 7519 §4 lets a parser reject them; we do)."""
    def hook(pairs):
        seen = {}
        for k, v in pairs:
            if k in seen:
                raise DuplicateMember(f'duplicate member {k!r}')
            seen[k] = v
        return seen
    return json.loads(raw, object_pairs_hook=hook)


class Key:
    """A test signing key. kind is 'RSA' (RS256) or 'EC' (ES256)."""

    def __init__(self, kid, kind='RSA'):
        self.kid, self.kind = kid, kind
        if kind == 'RSA':
            self.private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            self.alg = 'RS256'
        else:
            self.private = ec.generate_private_key(ec.SECP256R1())
            self.alg = 'ES256'
        self.public = self.private.public_key()

    def public_pem(self):
        return self.public.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)

    def jwk(self):
        if self.kind == 'RSA':
            n = self.public.public_numbers()
            return {'kty': 'RSA', 'kid': self.kid, 'use': 'sig', 'alg': 'RS256', 'n': _int_b64(n.n), 'e': _int_b64(n.e)}
        n = self.public.public_numbers()
        return {'kty': 'EC', 'kid': self.kid, 'use': 'sig', 'alg': 'ES256', 'crv': 'P-256',
                'x': b64e(n.x.to_bytes(32, 'big')), 'y': b64e(n.y.to_bytes(32, 'big'))}

    def sign(self, data):
        if self.kind == 'RSA':
            return self.private.sign(data, padding.PKCS1v15(), hashes.SHA256())
        r, s = decode_dss_signature(self.private.sign(data, ec.ECDSA(hashes.SHA256())))
        return r.to_bytes(32, 'big') + s.to_bytes(32, 'big')


def public_from_jwk(j):
    if j.get('kty') == 'RSA':
        n = int.from_bytes(b64d(j['n']), 'big')
        e = int.from_bytes(b64d(j['e']), 'big')
        return rsa.RSAPublicNumbers(e, n).public_key()
    if j.get('kty') == 'EC' and j.get('crv') == 'P-256':
        x = int.from_bytes(b64d(j['x']), 'big')
        y = int.from_bytes(b64d(j['y']), 'big')
        return ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()
    raise ValueError('unsupported jwk')


def verify_sig(alg, public, data, sig):
    """True if sig is a valid alg signature by the public key. Only RS256 and ES256 are known here."""
    try:
        if alg == 'RS256' and isinstance(public, rsa.RSAPublicKey):
            public.verify(sig, data, padding.PKCS1v15(), hashes.SHA256())
            return True
        if alg == 'ES256' and isinstance(public, ec.EllipticCurvePublicKey) and len(sig) == 64:
            public.verify(encode_dss_signature(int.from_bytes(sig[:32], 'big'), int.from_bytes(sig[32:], 'big')), data,
                          ec.ECDSA(hashes.SHA256()))
            return True
    except InvalidSignature:
        return False
    return False


def encode(header, payload, key=None, raw_payload=None, hmac_secret=None, signature=None):
    """Compact JWS. header and payload are dicts (or raw JSON strings via raw_payload, to keep duplicates).

    key: a Key (signs with key.alg unless header says otherwise); hmac_secret: bytes for HS256 (alg confusion);
    neither: alg=none (empty signature) unless signature is given.
    """
    h = header if isinstance(header, str) else json.dumps(header, separators=(',', ':'))
    p = raw_payload if raw_payload is not None else json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    si = (b64e(h.encode()) + '.' + b64e(p.encode())).encode('ascii')
    if signature is not None:
        sig = signature
    elif hmac_secret is not None:
        sig = hmac.new(hmac_secret, si, hashlib.sha256).digest()
    elif key is not None:
        sig = key.sign(si)
    else:
        sig = b''
    return si.decode('ascii') + '.' + b64e(sig)


def decode_unverified(token):
    """(header, payload) without checking the signature. For reports and for the narrowing check only."""
    h, p, _ = token.split('.')
    return strict_json(b64d(h)), strict_json(b64d(p))
