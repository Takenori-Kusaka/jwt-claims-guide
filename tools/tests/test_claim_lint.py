# -*- coding: utf-8 -*-
"""Tests of claim_lint v0 (#16): rules R1, R2, R8 (pass and fail cases), slide references, and the R8 golden token."""
import base64
import copy
import json
import os
import subprocess
import sys

import pytest
import yaml

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from claim_lint import core, r8  # noqa: E402

EXAMPLE = os.path.join(ROOT, 'templates', 'examples', 'scenario-a')
GOLDEN = os.path.join(TOOLS, 'tests', 'fixtures', 'claim_lint', 'golden')
FILES = ('claims', 'token_types', 'catalog_answers')


def load_example():
    return {k: core.load_yaml(os.path.join(EXAMPLE, k + '.yaml')) for k in FILES}


def write(tmp_path, docs):
    for k, v in docs.items():
        with open(tmp_path / (k + '.yaml'), 'w', encoding='utf-8') as f:
            yaml.safe_dump(v, f, allow_unicode=True, sort_keys=False)
    return str(tmp_path)


def lint(tmp_path, docs, **kw):
    return core.run(write(tmp_path, docs), **kw)


def by(res, rule, severity=None):
    return [f for f in res['findings'] if f['rule'] == rule and (severity is None or f['severity'] == severity)]


def claim(docs, cid):
    return next(c for c in docs['claims']['claims'] if c['id'] == cid)


def tt(docs, tid):
    return next(t for t in docs['token_types']['token_types'] if t['id'] == tid)


# ------------------------------------------------------------------ the worked example passes
def test_example_has_no_error():
    res = core.run(EXAMPLE)
    assert res['counts']['error'] == 0, core.format_table(res)
    assert res['catalog_events'] == 19 and res['claims'] == 25


# ------------------------------------------------------------------ R1
def test_r1_pass(tmp_path):
    assert not by(lint(tmp_path, load_example()), 'R1')


def test_r1_fail_missing_column_of_carried_claim(tmp_path):
    docs = load_example()
    del claim(docs, 'C-tenant-id')['owner']
    claim(docs, 'C-roles').pop('max_items')
    res = lint(tmp_path, docs)
    msgs = {(f['target'], f['message']) for f in by(res, 'R1', 'error')}
    assert ('C-tenant-id', '必須の列 owner が空') in msgs
    assert ('C-roles', '必須の列 max_items が空') in msgs


def test_r1_fail_rejected_needs_two_of_refs_assumption_revisit(tmp_path):
    docs = load_example()
    c = claim(docs, 'C-acr')
    c.pop('revisit_trigger')
    res = lint(tmp_path, docs)
    assert any(f['target'] == 'C-acr' for f in by(res, 'R1', 'error'))


def test_r1_fail_namespace_and_consumers_must_be_written(tmp_path):
    docs = load_example()
    claim(docs, 'C-sid').pop('consumers')
    claim(docs, 'C-exp').pop('namespace')
    res = lint(tmp_path, docs)
    targets = {f['target'] for f in by(res, 'R1', 'error')}
    assert {'C-sid', 'C-exp'} <= targets


def test_r1_fail_token_type_without_lifetime(tmp_path):
    docs = load_example()
    tt(docs, 'AT').pop('max_lifetime')
    res = lint(tmp_path, docs)
    assert any(f['target'] == 'token_type AT' and 'max_lifetime' in f['message'] for f in by(res, 'R1', 'error'))


# ------------------------------------------------------------------ R2
def test_r2_pass(tmp_path):
    assert not by(lint(tmp_path, load_example()), 'R2')


def test_r2_fail_missing_answer(tmp_path):
    docs = load_example()
    docs['catalog_answers']['answers'] = [a for a in docs['catalog_answers']['answers'] if a['event'] != 'I05']
    res = lint(tmp_path, docs)
    assert [f['target'] for f in by(res, 'R2', 'error')] == ['I05']


def test_r2_fail_out_of_scope_needs_assumption_and_breaks_when(tmp_path):
    docs = load_example()
    a = next(a for a in docs['catalog_answers']['answers'] if a['event'] == 'I04')
    a.pop('breaks_when')
    res = lint(tmp_path, docs)
    assert any(f['target'] == 'I04' and 'breaks_when' in f['message'] for f in by(res, 'R2', 'error'))


def test_r2_fail_unknown_event(tmp_path):
    docs = load_example()
    docs['catalog_answers']['answers'].append({'event': 'I99', 'answer': '該当', 'note': 'x'})
    assert any(f['target'] == 'I99' for f in by(lint(tmp_path, docs), 'R2', 'error'))


def test_r2_lite_profile_downgrades_to_warn(tmp_path):
    docs = load_example()
    docs['catalog_answers']['answers'] = docs['catalog_answers']['answers'][1:]
    res = lint(tmp_path, docs, profile='lite')
    assert not by(res, 'R2', 'error')
    assert [f['target'] for f in by(res, 'R2', 'warn')] == ['I01']


# ------------------------------------------------------------------ R8
def test_r8_pass_example_within_budget(tmp_path):
    res = lint(tmp_path, load_example())
    assert not by(res, 'R8', 'error') and not by(res, 'R8', 'warn')
    rep = res['r8'][0]
    assert rep['token_type'] == 'AT' and rep['tightest'] == 'nginx-large-client-header-buffers'


def test_r8_fail_exceeds_budget(tmp_path):
    docs = load_example()
    claim(docs, 'C-roles').update(max_items=600, max_bytes=12)  # 600 roles of 12 bytes: about 11 KB of payload
    res = lint(tmp_path, docs)
    err = by(res, 'R8', 'error')
    assert len(err) == 1 and err[0]['target'] == 'AT' and '上限を超える' in err[0]['message']


def test_r8_warn_above_ratio(tmp_path):
    docs = load_example()
    # find an item count that lands between 75% and 100% of the 8192-byte nginx field limit
    limits = core.load_limits(os.path.join(TOOLS, 'claim_lint', 'path_limits.yaml'))
    for n in range(100, 600):
        claim(docs, 'C-roles').update(max_items=n, max_bytes=12)
        _, reports = core.rule_r8(docs['claims']['claims'], docs['token_types']['token_types'], limits)
        if r8.WARN_RATIO < reports[0]['ratio'] <= 1:
            break
    res = lint(tmp_path, docs)
    assert by(res, 'R8', 'warn') and not by(res, 'R8', 'error')


def test_r8_fail_unbounded_array_and_unknown_limit(tmp_path):
    docs = load_example()
    claim(docs, 'C-roles').pop('max_items')
    tt(docs, 'AT')['size']['path'].append('cookie-4096-unverified')
    res = lint(tmp_path, docs)
    msgs = [f['message'] for f in by(res, 'R8', 'error')]
    assert any('max_items がない' in m for m in msgs)


def test_r8_fail_unknown_path_limit(tmp_path):
    docs = load_example()
    tt(docs, 'AT')['size']['path'].append('cookie-4096-unverified')
    res = lint(tmp_path, docs)
    assert any('path_limits.yaml にない' in f['message'] for f in by(res, 'R8', 'error'))


def test_r8_fail_all_headers_limit_needs_other_headers_bytes(tmp_path):
    docs = load_example()
    tt(docs, 'AT')['size'].pop('other_headers_bytes')
    res = lint(tmp_path, docs)
    assert any('other_headers_bytes' in f['message'] for f in by(res, 'R8', 'error'))


def test_r8_inline_limit_with_basis(tmp_path):
    docs = load_example()
    tt(docs, 'AT')['size']['path'] = [{'id': 'tiny', 'applies_to': 'header_field', 'bytes': 1000, 'basis': 'test'}]
    assert by(lint(tmp_path, docs), 'R8', 'error')


# ------------------------------------------------------------------ R8 golden token (Keycloak 26.8.0, 2026-11-22)
def _golden():
    with open(os.path.join(GOLDEN, 'token.json'), encoding='utf-8') as f:
        tok = json.load(f)
    claims = core.load_yaml(os.path.join(GOLDEN, 'claims.yaml'))['claims']
    tts = core.load_yaml(os.path.join(GOLDEN, 'token_types.yaml'))['token_types']
    return tok, claims, tts


def test_golden_token_fixture_is_consistent():
    tok, _, _ = _golden()
    h, p, s = tok['token'].split('.')
    dec = lambda x: base64.urlsafe_b64decode(x + '=' * (-len(x) % 4))
    assert dec(h).decode() == tok['header_json'] and dec(p).decode() == tok['payload_json']
    assert len(tok['token']) == tok['token_length'] == 1045
    assert len(dec(s)) == tok['sig_bytes'] == 256


def test_r8_golden_declared_values_match_actual_exactly():
    tok, claims, tts = _golden()
    _, reports = core.rule_r8(claims, tts, core.load_limits(os.path.join(TOOLS, 'claim_lint', 'path_limits.yaml')))
    rep = reports[0]
    assert rep['header_bytes'] == len(tok['header_json'].encode()) == 86
    assert rep['payload_bytes'] == len(tok['payload_json'].encode()) == 439
    assert (rep['header_b64'], rep['payload_b64'], rep['sig_b64']) == (tok['header_b64_len'], tok['payload_b64_len'], tok['sig_b64_len'])
    assert rep['token'] - tok['token_length'] == 0
    assert rep['header_value_bytes'] == tok['token_length'] + 7  # "Bearer "


def test_r8_golden_concrete_values_match_actual_exactly():
    tok, _, _ = _golden()
    payload = json.loads(tok['payload_json'])
    assert r8.concrete_payload_len(payload) == len(tok['payload_json'].encode())
    header = json.loads(tok['header_json'])
    assert r8.concrete_payload_len(header) + 4 == len(tok['header_json'].encode())  # Keycloak's " : " in typ and kid


def test_r8_golden_without_serializer_bytes_is_off_by_five():
    """The first computation (compact JSON header) was 5 characters short; this keeps that finding visible."""
    tok, claims, tts = _golden()
    tts = copy.deepcopy(tts)
    tts[0]['size']['header'].pop('serializer_extra_bytes')
    _, reports = core.rule_r8(claims, tts, {})
    assert tok['token_length'] - reports[0]['token'] == 5


# ------------------------------------------------------------------ schema and slide references
def test_schema_error_is_reported(tmp_path):
    docs = load_example()
    claim(docs, 'C-roles')['overflow_strategy'] = 'truncate'
    assert by(lint(tmp_path, docs), 'SCHEMA', 'error')


def test_unknown_guide_slide_id(tmp_path):
    docs = load_example()
    claim(docs, 'C-iss')['refs'].append({'kind': 'guide-slide', 'id': 'p99-no-such-slide'})
    assert by(lint(tmp_path, docs), 'SLIDE', 'error')


def test_duplicate_yaml_key_is_an_error(tmp_path):
    for k in FILES:
        (tmp_path / (k + '.yaml')).write_text(open(os.path.join(EXAMPLE, k + '.yaml'), encoding='utf-8').read(), encoding='utf-8')
    (tmp_path / 'claims.yaml').write_text('# template_version: 0.1.0\nscenario: A\nscenario: B\nclaims: []\n', encoding='utf-8')
    assert by(core.run(str(tmp_path)), 'LOAD', 'error')


# ------------------------------------------------------------------ CLI
def test_cli_json_output_and_exit_status(tmp_path):
    out = tmp_path / 'r.json'
    r = subprocess.run([sys.executable, os.path.join(TOOLS, 'claim_lint'), EXAMPLE, '--format', 'json', '--json-out', str(out)],
                       capture_output=True)
    assert r.returncode == 0
    res = json.loads(r.stdout.decode('utf-8'))
    assert res['counts']['error'] == 0 and json.loads(out.read_text(encoding='utf-8')) == res
    docs = load_example()
    del claim(docs, 'C-sub')['owner']
    bad = write(tmp_path, docs)
    r = subprocess.run([sys.executable, os.path.join(TOOLS, 'claim_lint'), bad], capture_output=True)
    assert r.returncode == 1 and b'FAIL' in r.stdout
