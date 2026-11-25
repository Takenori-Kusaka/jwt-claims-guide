# -*- coding: utf-8 -*-
"""Create an empty design directory to start a design doc from (#4, #60, #61; templates/GETTING_STARTED.md).

  python tools/new_design.py DIR [--profile lite|full] [--use P4,M_token_validation,...] [--with-hops] [--force]

Writes DIR/design.md (a copy of templates/00_core.md), and the registry files with the required keys and EMPTY values:
claims.yaml (no rows), token_types.yaml (one row per kind of templates/catalog/token_kinds.yaml, decision 却下 with an empty
rationale that the writer must fill or change to 採用), hops.yaml (no rows; not written with --profile lite, because a
design without hops has no hops.yaml), catalog_answers.yaml (one row per event of the catalogue with an empty answer,
and the coverage sections `questions`, `subject_states` and `pairwise` with their key names).
Nothing is copied from a worked example, so no sample rationale reaches the new design (#4 方針): claim_lint fails until
the writer answers every row, and its errors are the to-do list. A blank value is reported as TODO (a field not written
yet), never as SCHEMA: the skeleton has no SCHEMA finding (tools/tests/test_new_design.py).

--use names the profiles and modules of the design (file names of templates/profiles and templates/modules, or a
unique prefix such as P4). Their fill-in tables (the tables after a 記入欄 line) are copied into appendix D of design.md
(`template:00_core#profile-fill-ins`). With --profile lite only the sections marked 〔Lite・Full：記入…〕 are copied.
P4 is Full only (#61, decided 2026-11-26): --profile lite with P4 in --use writes nothing and exits with 2.
When DIR/design.md already exists, --use (without --force) only adds the fill-in sections that are not there yet and
writes no other file, so it can be run again after the profiles are chosen (GETTING_STARTED 手順 3).
"""
import argparse
import os
import re
import sys

import yaml

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import catalog_check  # noqa: E402  (the layers, results and states of the subject-state matrix)

VERSION = '0.2.0'  # registry schema version (templates/registry/*.schema.json)
SUBJECT_KINDS = ('利用者', 'ワークロード', 'システム')  # tools/claim_lint/coverage.py (R6), slide:p05-three-principals
LITE_CRITERIA = ('crosses_boundary', 'multitenant', 'delegation_or_exchange', 'new_issuer', 'regulated')


def rel_schema(dirpath, name):
    target = os.path.join(ROOT, 'templates', 'registry', name)
    try:
        return os.path.relpath(target, dirpath).replace(os.sep, '/')
    except ValueError:  # another drive (Windows): an absolute path
        return target.replace(os.sep, '/')


def header(dirpath, schema, lines):
    out = [f'# template_version: {VERSION}']
    if schema:
        out.append(f'# yaml-language-server: $schema={rel_schema(dirpath, schema)}')
    out += ['# ' + l for l in lines]
    return '\n'.join(out) + '\n'


def load(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return yaml.safe_load(f)


class _Flow(dict):
    """A small mapping written on one line ({answer: null, reason: ''}), so that a matrix cell stays one line."""


class _Dumper(yaml.SafeDumper):
    pass


_Dumper.add_representer(_Flow, lambda dumper, data: dumper.represent_mapping('tag:yaml.org,2002:map', data, flow_style=True))


def _dump(doc):
    return yaml.dump(doc, Dumper=_Dumper, allow_unicode=True, sort_keys=False, width=1000)


def hops_text(dirpath):
    return header(dirpath, 'hops.schema.json', [
        'ホップごとの宣言（templates/registry/README.md の 3.4）。行は 1 つ以上書く',
        'ホップを書かない Lite の設計は、このファイルを置かない（消す）。`hops: []` のままでは TODO の error が残る（templates/GETTING_STARTED.md の手順 1）'
    ]) + _dump({'hops': []})


def build(dirpath, profile='full', use=(), with_hops=False):
    kinds = load('templates/catalog/token_kinds.yaml')['kinds']
    events = load('templates/catalog/issue_events.yaml')['events'] + load('templates/catalog/use_events.yaml')['events']
    files = {}
    files['claims.yaml'] = header(dirpath, 'claims.schema.json', [
        '台帳（templates/registry/README.md の 3.1）。行は 1 つも無い状態から始める。記入例の行を写さない（理由の写し書きを防ぐ。#4 の方針）',
        '組織の名前空間に共有クレームを足すなら、先に claim_request_<名前>.md（templates/claim_request.md）を書く',
        '組織の名前空間を使うときだけ、最上位に namespaces を足す（使わないならキーを書かない。templates/registry/README.md の 11.）：',
        '  namespaces:',
        '    - {namespace: "https://claims.example.com/", style: flat_prefix, owner: <持ち主>, change_controller: <変更を決める者>}',
        "空の値（null・''・[]）は、claim_lint が TODO（まだ書いていない欄）として出す"]) + _dump(
        # no `namespaces` key: it is optional and an empty list is against the schema (#60)
        {'scenario': None,
         # the fixed vocabulary of data_category (templates/registry/README.md 9.; the schema requires it). Keep it unless
         # the organization pins another version; verified_on is the day the writer opened the vocabulary
         'data_category_vocabulary': {'name': 'fideslang', 'version': '3.1.4',
                                      'url': 'https://github.com/ethyca/fideslang/blob/3.1.4/data_files/data_categories.csv',
                                      'license': 'CC-BY-4.0', 'verified_on': ''},
         'claims': []})
    rows = [{'id': k['id'].upper(), 'kind': k['id'], 'decision': '却下', 'rationale': '', 'format': None} for k in kinds]
    issuance = {k: {'value': None, 'rationale': ''} for k in (
        'client_type', 'client_auth', 'grants', 'sender_constraint', 'at_format', 'rt_strategy', 'request_protection',
        'conformance_profile')}
    files['token_types.yaml'] = header(dirpath, 'token_types.schema.json', [
        'トークン目録（templates/registry/README.md の 3.2）と発行方式の選択（3.3）。カタログの種類ごとに 1 行を作った',
        '使う種類は decision を 採用 にして列を書く（R1 が要る列を示す）。使わない種類は 却下 のまま、rationale に何ができなくなるかを書く',
        'ID は大文字の仮の名前。採用する行は、ホップ・台帳の carried_in・カタログへの回答から参照する ID に直してよい']) + _dump(
        {'issuance_profile': issuance, 'token_types': rows})
    if profile != 'lite' or with_hops:
        # #60: a Lite design without hops has no hops.yaml (claim_lint reports its absence as info in Lite, as a warning
        # in Full). The Lite skeleton has none unless --with-hops asks for it (a Lite design may still write a hop, e.g.
        # a DB connection: M_data_layer 5. points at hops[].connection_max_lifetime)
        files['hops.yaml'] = hops_text(dirpath)
    questions = [q['id'] for q in load('templates/registry/questions.yaml')['questions']]
    states = sorted(k for k in catalog_check.seed_items(load('templates/catalog/seeds.yaml'))[0]
                    if k.startswith(catalog_check.STATES + '/'))
    files['catalog_answers.yaml'] = header(dirpath, None, [
        'カタログの全イベントへの回答（tools/claim_lint/RULES.md の R2）。answer は 該当 か 対象外',
        '対象外なら assumption（起きない前提）と breaks_when（前提が崩れる条件）を書く。名前だけを見て対象外にしない',
        'lite_criteria：templates/README.md の「Lite と Full の判定」の 5 問。answer は true か false',
        'idp（R3・R3b）：name は keycloak・auth0・cognito・entra・okta か、組織の発行者の名前。version も書く',
        'questions（L13）：templates/registry/questions.yaml の問いごとに needed: true か false。false なら reason。'
        'クレームでない仕組みで答える問いには channel を足す',
        'subject_states（R4）：行は主体の状態（templates/catalog/subject_state_matrix.md）、列は層。result は '
        + '・'.join(catalog_check.RESULTS) + ' のどれか。basis に根拠を書く',
        '  使わない層は、unused_layers に「層の名前: 理由」を書き、states の下のその層のセルを消す（両方にあると R4 が指摘する）',
        'pairwise（R6）：subject_kinds の answer は 該当 か 対象外（対象外なら reason）。combinations に検討した組み合わせを足す：',
        '  - {subject: 利用者, event: I01, stage: <カタログのそのイベントの stage の 1 文字>, note: <検討の記録>}',
        'outside_enumeration（R9）：カタログの外の場面を探した範囲（searched）と、その答え']) + _dump(
        {'lite_criteria': {k: _Flow(answer=None, reason='') for k in LITE_CRITERIA},
         'idp': {'name': None, 'version': None},
         'questions': {q: _Flow(needed=None, reason='') for q in questions},
         'subject_states': {'unused_layers': {},
                            'states': {s: {layer: _Flow(result=None, basis='') for layer in catalog_check.LAYERS}
                                       for s in states}},
         'pairwise': {'subject_kinds': {k: _Flow(answer=None, reason='') for k in SUBJECT_KINDS}, 'combinations': []},
         'outside_enumeration': {'answer': '', 'respondent': '', 'date': '', 'searched': []},
         'answers': [{'event': e['id'], 'answer': None} for e in events]})
    with open(os.path.join(ROOT, 'templates', '00_core.md'), encoding='utf-8') as f:
        files['design.md'] = add_fill_ins(f.read(), profile, use)
    return files


# ------------------------------------------------------------------ fill-in tables of profiles and modules (#61)
FILL_BEGIN, FILL_END = '<!-- fill-ins:begin -->', '<!-- fill-ins:end -->'
LITE_MARK = '〔Lite・Full：記入'  # the sections a Lite design fills in too (e.g. 〔Lite・Full：記入（00_core に書く）〕)
ITEM_RE = re.compile(r'^項目 ID：`(template:[A-Za-z0-9_/]+#[a-z0-9-]+)`')
# a section whose mark says that its answer is written elsewhere: 〔Lite・Full：記入（00_core に書く）〕,
# 〔Lite・Full：記入（台帳の既定どおりの行）〕
ELSEWHERE_RE = re.compile(r'〔[^〕]*記入（((?:00_core|台帳)[^）]*)）〕\s*$')
# profiles that have no Lite path (#61, option 0 of research/template-design/p4-lite-options.md): a design that uses
# P4 is Full; an agent design with no trust boundary and no delegation or exchange is written with P5
FULL_ONLY = ('P4_ai_agent_delegation',)


def template_parts():
    """{file name without .md: path below templates/ without .md} of the profiles and modules."""
    out = {}
    for sub in ('profiles', 'modules'):
        d = os.path.join(ROOT, 'templates', sub)
        for fn in sorted(os.listdir(d)):
            if fn.endswith('.md'):
                out[fn[:-3]] = f'{sub}/{fn[:-3]}'
    return out


def resolve_use(names):
    """Names given to --use -> file names. A name is a file name without .md, or a unique prefix of one (P4, M_idp)."""
    parts = template_parts()
    out = []
    for n in names:
        hit = [k for k in parts if k == n] or [k for k in parts if k.startswith(n)]
        if len(hit) != 1:
            why = 'no such profile or module' if not hit else 'ambiguous (' + ', '.join(hit) + ')'
            raise ValueError(f"--use {n}: {why}; one of {', '.join(parts)}")
        if hit[0] not in out:
            out.append(hit[0])
    return out


def full_only_error(profile, use):
    """The message for --profile lite with a Full-only profile in --use, or None."""
    hit = [n for n in resolve_use(use) if n in FULL_ONLY]  # resolve_use raises ValueError for an unknown name
    if profile != 'lite' or not hit:
        return None
    return (f"--profile lite --use {','.join(hit)}: {', '.join(hit)} is Full only and has no Lite fill-ins "
            '(templates/README.md, the Lite/Full criteria; #61). Use --profile full for a design that uses it. '
            'An agent design that crosses no trust boundary and has no delegation or token exchange is written '
            'with P5 (--use P5), not with P4. Nothing was written.')


def fill_in_sections(name, profile='full'):
    """The fill-in tables of one profile or module: [(item id, heading text, [the 記入欄 line and its table])].
    A fill-in table is the table right after a line that starts with 記入欄 (the reading of template_check T4)."""
    path = os.path.join(ROOT, 'templates', template_parts()[name] + '.md')
    with open(path, encoding='utf-8') as f:
        lines = f.read().split('\n')
    out, heading, item = [], None, None
    for i, line in enumerate(lines):
        if re.match(r'^#{2,4} ', line):
            heading, item = line, None
        m = ITEM_RE.match(line)
        if m:
            item = m.group(1)
        if not line.startswith('記入欄') or not heading or not item:
            continue
        if profile == 'lite' and LITE_MARK not in heading:
            continue
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        table = []
        while j < len(lines) and lines[j].startswith('|'):
            table.append(lines[j])
            j += 1
        if len(table) == 2:  # a header and its separator only: add one empty row to write in
            table.append('|' + '  |' * (table[0].count('|') - 1))
        # the heading keeps its 〔…〕 mark, so that a copied section still says how it is filled in
        # (〔Full：記入／Lite：参照〕, 〔Lite：生成／Full：生成と確かめ〕, ...)
        title = heading.lstrip('#').strip()
        m = ELSEWHERE_RE.search(title)
        if m:
            # the answer of this section is written in one place only, the one its mark names (00_core, the registry):
            # appendix D gets a pointer instead of a second table to fill in
            place = ('設計書（`design.md`）の本体の節（00_core から写した節。どの節かは、テンプレートのこの項目の本文が示す）'
                     if m.group(1).startswith('00_core') else f'設計書の台帳（`claims.yaml`）の、{m.group(1)[len("台帳の"):]}')
            out.append((item, title, [f'記入欄：ここには書かない。この項目の答えは、{place}に 1 回だけ書く。'
                                      '問いと候補は、テンプレートのこの項目で読む（テンプレートのファイルには書き込まない）']))
            continue
        out.append((item, title, [line, ''] + table))
    return out


def add_fill_ins(text, profile='full', use=()):
    """Insert the fill-in sections of the chosen profiles and modules into appendix D of a design.md, between the
    fill-ins markers. A section whose item ID is already between the markers is left as it is (the writer's text)."""
    names = resolve_use(use)
    if not names:
        return text
    refused = full_only_error(profile, use)
    if refused:
        raise ValueError(refused)
    if FILL_BEGIN not in text or FILL_END not in text:
        raise ValueError(f'no {FILL_BEGIN} ... {FILL_END} region (appendix D of templates/00_core.md)')
    head, rest = text.split(FILL_BEGIN, 1)
    body, tail = rest.split(FILL_END, 1)
    add = []
    for n in names:
        for item, title, block in fill_in_sections(n, profile):
            if f'`{item}`' in body:
                continue
            add += [f'#### {n}：{title}', '', f'項目：`{item}`（問いと候補は、テンプレートのこの項目にある）', ''] + block + ['']
    if not add:
        return text
    body = body.strip('\n')
    return head + FILL_BEGIN + '\n' + (body + '\n\n' if body else '') + '\n'.join(add) + FILL_END + tail


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('dir')
    ap.add_argument('--profile', choices=('lite', 'full'), default='full',
                    help='lite: no hops.yaml, and only the fill-in sections that a Lite design writes (default: full)')
    ap.add_argument('--use', default='', help='profiles and modules whose fill-in tables go to appendix D of design.md, '
                                              'comma separated (e.g. P1,P4,M_token_validation)')
    ap.add_argument('--with-hops', action='store_true',
                    help='write hops.yaml with --profile lite too (a Lite design that writes a hop, e.g. a DB connection); '
                         'on an existing design, add hops.yaml when it is missing')
    ap.add_argument('--force', action='store_true', help='overwrite existing files')
    a = ap.parse_args(argv)
    use = [x.strip() for x in a.use.split(',') if x.strip()]
    try:
        refused = full_only_error(a.profile, use)
    except ValueError as e:
        sys.stderr.write(f'{e}\n')
        return 2
    if refused:
        sys.stderr.write(refused + '\n')
        return 2
    design = os.path.join(a.dir, 'design.md')
    if a.with_hops and os.path.exists(design) and not a.force:
        # the design exists: add hops.yaml when it is missing, never overwrite it
        hops = os.path.join(a.dir, 'hops.yaml')
        if os.path.exists(hops):
            print('unchanged', hops)
        else:
            with open(hops, 'w', encoding='utf-8', newline='\n') as f:
                f.write(hops_text(os.path.abspath(a.dir)))
            print('wrote', hops)
        if not use:
            return 0
    if use and os.path.exists(design) and not a.force:
        # the design exists: add only the fill-in sections that are missing, and touch nothing else
        with open(design, encoding='utf-8', newline='') as f:
            old = f.read()
        nl = '\r\n' if '\r\n' in old else '\n'
        old = old.replace('\r\n', '\n')
        try:
            new = add_fill_ins(old, a.profile, use)
        except ValueError as e:
            sys.stderr.write(f'{design}: {e}\n')
            return 1
        if new == old:
            print('unchanged', design)
            return 0
        with open(design, 'w', encoding='utf-8', newline='') as f:
            f.write(new.replace('\n', nl))
        print('added fill-in sections to', design)
        return 0
    os.makedirs(a.dir, exist_ok=True)
    files = build(os.path.abspath(a.dir), a.profile, use, a.with_hops)
    for name, text in files.items():
        p = os.path.join(a.dir, name)
        if os.path.exists(p) and not a.force:
            sys.stderr.write(f'{p} exists (use --force)\n')
            return 1
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        print('wrote', p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
