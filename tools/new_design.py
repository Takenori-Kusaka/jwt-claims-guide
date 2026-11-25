# -*- coding: utf-8 -*-
"""Create an empty design directory to start a design doc from (#4, templates/GETTING_STARTED.md).

  python tools/new_design.py DIR [--force]

Writes DIR/design.md (a copy of templates/00_core.md), and the registry files with the required keys and EMPTY values:
claims.yaml (no rows), token_types.yaml (one row per kind of templates/catalog/token_kinds.yaml, decision 却下 with an empty
rationale that the writer must fill or change to 採用), hops.yaml (no rows), catalog_answers.yaml (one row per event of the
catalogue with an empty answer). Nothing is copied from a worked example, so no sample rationale reaches the new design
(#4 方針): claim_lint fails until the writer answers every row, and its errors are the to-do list.
"""
import argparse
import os
import sys

import yaml

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
VERSION = '0.3.0'  # registry schema version (templates/registry/*.schema.json)


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


def build(dirpath):
    kinds = load('templates/catalog/token_kinds.yaml')['kinds']
    events = load('templates/catalog/issue_events.yaml')['events'] + load('templates/catalog/use_events.yaml')['events']
    files = {}
    files['claims.yaml'] = header(dirpath, 'claims.schema.json', [
        '台帳（templates/registry/README.md の 3.1）。行は 1 つも無い状態から始める。記入例の行を写さない（理由の写し書きを防ぐ。#4 の方針）',
        '組織の名前空間に共有クレームを足すなら、先に claim_request_<名前>.md（templates/claim_request.md）を書く']) + yaml.safe_dump(
        {'scenario': None, 'namespaces': [],
         # the fixed vocabulary of data_category (templates/registry/README.md 9.; the schema requires it). Keep it unless
         # the organization pins another version; verified_on is the day the writer opened the vocabulary
         'data_category_vocabulary': {'name': 'fideslang', 'version': '3.1.4',
                                      'url': 'https://github.com/ethyca/fideslang/blob/3.1.4/data_files/data_categories.csv',
                                      'license': 'CC-BY-4.0', 'verified_on': ''},
         'claims': []}, allow_unicode=True, sort_keys=False)
    rows = [{'id': k['id'].upper(), 'kind': k['id'], 'decision': '却下', 'rationale': '', 'format': None} for k in kinds]
    profile = {k: {'value': None, 'rationale': ''} for k in (
        'client_type', 'client_auth', 'grants', 'sender_constraint', 'at_format', 'rt_strategy', 'request_protection',
        'conformance_profile')}
    files['token_types.yaml'] = header(dirpath, 'token_types.schema.json', [
        'トークン目録（templates/registry/README.md の 3.2）と発行方式の選択（3.3）。カタログの種類ごとに 1 行を作った',
        '使う種類は decision を 採用 にして列を書く（R1 が要る列を示す）。使わない種類は 却下 のまま、rationale に何ができなくなるかを書く',
        'ID は大文字の仮の名前。採用する行は、ホップ・台帳の carried_in・カタログへの回答から参照する ID に直してよい']) + yaml.safe_dump(
        {'issuance_profile': profile, 'token_types': rows}, allow_unicode=True, sort_keys=False)
    files['hops.yaml'] = header(dirpath, 'hops.schema.json', [
        'ホップごとの宣言（templates/registry/README.md の 3.4）。交換・作り直しのホップがあれば Lite でも書く']) + yaml.safe_dump(
        {'hops': []}, allow_unicode=True, sort_keys=False)
    answers = [{'event': e['id'], 'answer': None} for e in events]
    files['catalog_answers.yaml'] = header(dirpath, None, [
        'カタログの全イベントへの回答（tools/claim_lint/RULES.md の R2）。answer は 該当 か 対象外',
        '対象外なら assumption（起きない前提）と breaks_when（前提が崩れる条件）を書く。名前だけを見て対象外にしない',
        'lite_criteria は templates/README.md の「Lite と Full の判定」の 5 問']) + yaml.safe_dump(
        {'lite_criteria': {k: {'answer': None, 'reason': ''} for k in (
            'crosses_boundary', 'multitenant', 'delegation_or_exchange', 'new_issuer', 'regulated')},
         'idp': {'name': None}, 'outside_enumeration': {'answer': '', 'respondent': '', 'date': '', 'searched': []},
         'answers': answers}, allow_unicode=True, sort_keys=False)
    with open(os.path.join(ROOT, 'templates', '00_core.md'), encoding='utf-8') as f:
        files['design.md'] = f.read()
    return files


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('dir')
    ap.add_argument('--force', action='store_true', help='overwrite existing files')
    a = ap.parse_args(argv)
    os.makedirs(a.dir, exist_ok=True)
    files = build(os.path.abspath(a.dir))
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
