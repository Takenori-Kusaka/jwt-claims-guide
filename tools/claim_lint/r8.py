# -*- coding: utf-8 -*-
"""Rule R8: worst-case encoded size of a JWS (compact serialization) per token type, against the path budget.

The model (research/template-design/report.md Q9, "サイズチェッカーの仕様"):

  size = ceil(4/3 * header) + ceil(4/3 * payload) + ceil(4/3 * sig) + 2          (two dots)
         + 7 when the token is sent as "Bearer <token>"

ceil(4n/3) is the length of the base64url encoding of n octets without padding (RFC 7515 §2, RFC 4648 §5).
header and payload are the UTF-8 byte lengths of the JSON texts; both are computed from the declared
members as compact JSON (no whitespace), plus serializer_extra_bytes for issuers whose serializer adds
whitespace (Keycloak 26.8 writes `"typ" : "at+jwt"` in the JOSE header; see research/template-design/gate1.md).

JSON sizes (bytes):
  object  = 2 + sum(member) + (members - 1) commas;  member = len(json key with quotes) + 1 colon + value
  string  = 2 quotes + max_bytes
  number / integer = max_bytes (digits)
  boolean = max_bytes (4 for true, 5 for false)
  array   = 2 + items * element + (items - 1) commas;  worst case: items = max_items, element = max_bytes (+2 for strings)
Claims with a namespace are grouped into one object member whose key is the namespace.
"""
import json
import math

# octets of the signature by alg: HMAC RFC 7518 §3.2 (full hash output), ECDSA RFC 7518 §3.4, RSA (RS/PS, RFC 7518
# §3.3 / §3.5) = modulus length (RFC 8017 §8.1.1, §8.2.1), Ed25519 RFC 8032 §5.1.6 (64 octets)
SIG_OCTETS_FIXED = {'ES256': 64, 'ES384': 96, 'ES512': 132, 'EdDSA': 64, 'Ed25519': 64,
                    'HS256': 32, 'HS384': 48, 'HS512': 64}
RSA_ALGS = {'RS256', 'RS384', 'RS512', 'PS256', 'PS384', 'PS512'}
BEARER_PREFIX = len('Bearer ')          # 7
FIELD_NAME = len('Authorization: ')     # 15, counted against header_field limits (conservative)
# warn threshold: author-proposal (report Q9 gives 50-75%; the upper end is used so that warn stays rare). tracking #16
WARN_RATIO = 0.75


def b64len(n):
    """Length of base64url without padding for n octets."""
    return math.ceil(4 * n / 3)


def key_len(name):
    return len(json.dumps(name, ensure_ascii=False).encode('utf-8'))


def scalar_len(typ, nbytes):
    return nbytes + 2 if typ == 'string' else nbytes


def value_len(typ, shape, elements):
    """elements: list of byte lengths of each scalar (without quotes)."""
    if shape == 'array':
        return 2 + sum(scalar_len(typ, e) for e in elements) + max(len(elements) - 1, 0)
    return scalar_len(typ, elements[0])


def object_len(members):
    """members: list of (key, value_len)."""
    return 2 + sum(key_len(k) + 1 + v for k, v in members) + max(len(members) - 1, 0)


def payload_members(claims):
    """claims: list of dicts with name, namespace, value_len. Returns top-level (key, value_len) members."""
    top, groups, order = [], {}, []
    for c in claims:
        ns = c.get('namespace')
        if ns:
            if ns not in groups:
                groups[ns] = []
                order.append(ns)
            groups[ns].append((c['name'], c['value_len']))
        else:
            top.append((c['name'], c['value_len']))
    return top + [(ns, object_len(groups[ns])) for ns in order]


def worst_value_len(claim):
    typ, shape = claim.get('type'), claim.get('shape', 'single')
    mb = claim.get('max_bytes')
    if mb is None:
        return None
    if shape == 'array':
        if not claim.get('max_items'):
            return None
        return value_len(typ, 'array', [mb] * claim['max_items'])
    return value_len(typ, 'single', [mb])


def sig_octets(signing):
    alg = signing.get('alg')
    if alg in SIG_OCTETS_FIXED:
        return SIG_OCTETS_FIXED[alg]
    if alg in RSA_ALGS and signing.get('key_bits'):
        return math.ceil(signing['key_bits'] / 8)
    return None


def header_len(header):
    members = [(p['name'], scalar_len(p['type'], p['max_bytes'])) for p in header['params']]
    return object_len(members) + header.get('serializer_extra_bytes', 0)


def encoded_size(header_bytes, payload_bytes, sig_bytes):
    return {'header_b64': b64len(header_bytes), 'payload_b64': b64len(payload_bytes), 'sig_b64': b64len(sig_bytes),
            'token': b64len(header_bytes) + b64len(payload_bytes) + b64len(sig_bytes) + 2}


def concrete_payload_len(payload):
    """Size of a concrete payload (dict) computed with the same functions as the worst case (for the golden test).
    Nested objects are accepted one level deep (the namespace object)."""
    def vlen(v):
        if isinstance(v, bool):
            return 4 if v else 5
        if isinstance(v, (int, float)):
            return len(json.dumps(v))
        if isinstance(v, str):
            return scalar_len('string', len(json.dumps(v, ensure_ascii=False).encode('utf-8')) - 2)
        if isinstance(v, list):
            return 2 + sum(vlen(x) for x in v) + max(len(v) - 1, 0)
        if isinstance(v, dict):
            return object_len([(k, vlen(x)) for k, x in v.items()])
        raise TypeError(type(v))
    return object_len([(k, vlen(v)) for k, v in payload.items()])
