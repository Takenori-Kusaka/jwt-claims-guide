# -*- coding: utf-8 -*-
"""Tests of claim_lint v0 (#16): rules R1, R2, R8 (pass and fail cases), slide references, and the R8 golden token."""
import base64
import copy
import json
import os
import shutil
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
    assert res['catalog_events'] == 64 and res['claims'] == 26  # C-at-hash added by #30; U29 and U30 by #63


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


def test_r1_lite_does_not_ask_for_generated_columns(tmp_path):
    """--profile lite: the reduced Lite (gate1.md 10., #4) generates issue_events, propagation_delay, status, issuers,
    and a 既定どおり row that nobody reads keeps only what R8 and the decision need."""
    docs = load_example()
    read = claim(docs, 'C-tenant-id')
    for k in ('issue_events', 'propagation_delay', 'status', 'issuers'):
        read.pop(k, None)
    unread = next(c for c in docs['claims']['claims'] if c['decision'] == '既定どおり' and c.get('consumers') == [])
    for k in ('description', 'not_meaning', 'owner', 'source_system', 'log_policy'):
        unread.pop(k, None)
    lite = {f['target'] for f in by(lint(tmp_path, docs, profile='lite'), 'R1', 'error')}
    assert read['id'] not in lite and unread['id'] not in lite
    full = {(f['target'], f['message']) for f in by(lint(tmp_path, docs), 'R1', 'error')}
    assert (read['id'], '必須の列 issue_events が空') in full and (unread['id'], '必須の列 owner が空') in full


def test_r1_lite_still_asks_for_hand_written_columns(tmp_path):
    docs = load_example()
    claim(docs, 'C-tenant-id').pop('owner')
    unread = next(c for c in docs['claims']['claims'] if c['decision'] == '既定どおり' and c.get('consumers') == [])
    unread.pop('max_bytes')
    msgs = {(f['target'], f['message']) for f in by(lint(tmp_path, docs, profile='lite'), 'R1', 'error')}
    assert ('C-tenant-id', '必須の列 owner が空') in msgs and (unread['id'], '必須の列 max_bytes が空') in msgs


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


def _with_version(tmp_path, docs, version):
    tmp_path.mkdir(exist_ok=True)
    d = write(tmp_path, docs)
    p = os.path.join(d, 'catalog_answers.yaml')
    with open(p, encoding='utf-8') as f:
        body = f.read()
    with open(p, 'w', encoding='utf-8') as f:
        f.write(f'# template_version: {version}\n' + body)
    return d


def _without_new_events(docs):
    docs['catalog_answers']['answers'] = [a for a in docs['catalog_answers']['answers'] if a['event'] not in ('U29', 'U30')]
    return docs


def test_r2_new_event_is_a_warning_in_its_minor_version_and_an_error_from_the_next(tmp_path, monkeypatch):
    # #63: U29 and U30 carry asked_from 0.3.0. The grace is one minor version of the registry (compared in code)
    d = write(tmp_path, _without_new_events(load_example()))
    for current, sev in (((0, 3, 0), 'warn'), ((0, 3, 7), 'warn'), ((0, 4, 0), 'error'), ((1, 0, 0), 'error')):
        monkeypatch.setattr(core, 'registry_version', lambda root=core.ROOT, v=current: v)
        res = core.run(d)
        assert sorted(f['target'] for f in by(res, 'R2', sev)) == ['U29', 'U30'], current
    monkeypatch.setattr(core, 'registry_version', lambda root=core.ROOT: (0, 4, 0))
    assert [f['target'] for f in by(core.run(d, profile='lite'), 'R2', 'warn')] == ['U29', 'U30']  # Lite: warn as R2 is


def test_r2_version_comment_does_not_exempt_a_design(tmp_path):
    # PR #79 check: an author who writes an old version on the first line is still asked the new events
    docs = _without_new_events(load_example())
    for v in ('0.2.0', '0.0.1'):
        res = core.run(_with_version(tmp_path / v, docs, v))
        assert sorted(f['target'] for f in by(res, 'R2', 'warn')) == ['U29', 'U30'] and not by(res, 'FROZEN')


def _catalog_copy(tmp_path, old, new):
    cat = tmp_path / 'catalog'
    shutil.copytree(os.path.join(ROOT, 'templates', 'catalog'), cat)
    p = cat / 'use_events.yaml'
    text = p.read_text(encoding='utf-8')
    assert old in text
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    return str(cat)


def test_asked_from_on_an_existing_row_does_not_soften_r2(tmp_path):
    # PR #79 check: asked_from "9.9.9" on U01 must not turn its missing answer into a warning (and catalog_check fails)
    import catalog_check
    cat = _catalog_copy(tmp_path, '  - id: U01\n', '  - id: U01\n    asked_from: "9.9.9"\n')
    docs = load_example()
    docs['catalog_answers']['answers'] = [a for a in docs['catalog_answers']['answers'] if a['event'] != 'U01']
    res = core.run(write(tmp_path, docs), catalog_dir=cat)
    assert [f['target'] for f in by(res, 'R2', 'error')] == ['U01']
    cc = catalog_check.run(catalog_dir=cat)
    assert cc['errors'] and any(f['check'] == 'ASKED' and 'U01' in f['target'] for f in cc['findings'])
    # listing U01 in _added does not help either: only rows appended after the unlisted ones may be listed
    cat2 = _catalog_copy(tmp_path / 'b', '  "0.3.0": [U29, U30]', '  "0.3.0": [U01, U29, U30]')
    with open(os.path.join(cat2, 'use_events.yaml'), encoding='utf-8') as f:
        text = f.read()
    with open(os.path.join(cat2, 'use_events.yaml'), 'w', encoding='utf-8') as f:
        f.write(text.replace('  - id: U01\n', '  - id: U01\n    asked_from: "0.3.0"\n', 1))
    cc2 = catalog_check.run(catalog_dir=cat2)
    assert any(f['check'] == 'ASKED' and f['target'].endswith('U01') for f in cc2['findings'])


def test_frozen_record_is_not_asked_the_new_events_and_says_so():
    res = core.run(os.path.join(ROOT, 'research', 'pilot', 'scenario-b'))
    assert not [f for f in by(res, 'R2') if f['target'] in ('U29', 'U30')]
    frozen = by(res, 'FROZEN', 'info')
    assert len(frozen) == 1 and 'U29・U30' in frozen[0]['message']


def test_a_copy_or_a_changed_record_is_not_frozen(tmp_path, monkeypatch):
    pilot = os.path.join(ROOT, 'research', 'pilot', 'scenario-b')
    copy = tmp_path / 'scenario-b'
    shutil.copytree(pilot, copy)
    res = core.run(str(copy))  # not listed in frozen_designs.yaml
    assert sorted(f['target'] for f in by(res, 'R2', 'warn') if f['target'] in ('U29', 'U30')) == ['U29', 'U30']
    assert not by(res, 'FROZEN')
    # listed, but its catalog_answers.yaml changed: the exemption is lost and FROZEN warns. The copy sits under the
    # repository so that its path can be listed (tmp_path may be on another drive)
    import tempfile
    inside = tempfile.mkdtemp(prefix='.frozen-test-', dir=ROOT)
    try:
        listed = os.path.join(inside, 'scenario-b')
        shutil.copytree(pilot, listed)
        rel = os.path.relpath(listed, ROOT).replace('\\', '/')
        frozen = tmp_path / 'frozen.yaml'
        frozen.write_text(f'designs:\n  - {{path: "{rel}", catalog_answers_sha256: "0", version: "0.2.0", reason: test}}\n',
                          encoding='utf-8')
        monkeypatch.setattr(core, 'FROZEN_FILE', str(frozen))
        res = core.run(listed)
        assert by(res, 'FROZEN', 'warn')
        assert sorted(f['target'] for f in by(res, 'R2', 'warn') if f['target'] in ('U29', 'U30')) == ['U29', 'U30']
    finally:
        shutil.rmtree(inside)


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
