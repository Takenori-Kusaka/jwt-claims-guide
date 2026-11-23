# -*- coding: utf-8 -*-
"""review.yaml, the review records of a design (#50): check, stale approvals, merge, sampling, report.

  python tools/review_record.py check REVIEW_YAML [--design DIR] [--fail-on-stale]
  python tools/review_record.py merge A.yaml B.yaml [...] -o OUT.yaml
  python tools/review_record.py sample --seed SEED [--count 3] DIR
  python tools/review_record.py report REVIEW_YAML --design DIR [--reviewer NAME] [-o OUT.md | --check OUT.md]
  python tools/review_record.py diff BASE_DIR DIR

The review mode of the design editor (docs/claims/) writes and reads review.yaml; this is the Python side of the same
records, for CI.

check: the file against templates/review/review.schema.json (JSON Schema 2020-12), then: the reviewer names are unique;
  the answered questions and the questions of findings are questions of templates/review/perspectives.md; the finding IDs
  are unique within a review; the escalation criteria are IDs of escalation.md; with --design, every row decision is
  compared with the row as it is now (tools/row_hash.py): the same hash (current), another hash (stale: 再確認が要る) or
  a row that is not in the registry any more (missing), and the sampled rows are the ones the seed draws. Stale and
  missing decisions are listed; they fail the check only with --fail-on-stale (a team that wants CI to stop on an
  approval of a row that has changed since turns it on). The names are self-declared: the approval that counts is the
  GitHub pull request review.
merge: the reviews of several files into one (same design); the same reviewer in two files must have the same records.
sample: the rejected rows of claims.yaml ranked by sha256(seed + ':' + anchor), the first COUNT (2 or 3), the same draw
  as the editor's 「抜き取る」.
report: the review report in the form of templates/review/report_template.md, the same text as the editor's 「レポート
  を作る」 (tools/tests/test_review_record.py checks the form with review_check.check_report; the browser test compares
  the two generators).
diff: the rows whose content hash differs between two versions of a design (added, removed, changed): the rows a
  reviewer has to look at again. claim_lint diff (L10) checks whether a change breaks receivers; this lists every
  changed row, breaking or not.

The file is written in one canonical form (key order, every string in double quotes, JSON escapes), the same as the
editor writes, so that reading and writing it again gives the same bytes.
"""
import argparse
import hashlib
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import yaml  # noqa: E402
import row_hash  # noqa: E402

SCHEMA = os.path.join(ROOT, 'templates', 'review', 'review.schema.json')
FORMAT = 'claims-review/1'
KEY_ORDER = ['format', 'design', 'independent', 'reviews', 'reviewer', 'id', 'criterion', 'name', 'to', 'location', 'anchors',
             'questions', 'content', 'severity', 'origin', 'kind', 'model', 'confused_question', 'verdict', 'verdict_reason',
             'response', 'owner', 'due', 'state', 'ref', 'conclusion', 'self_declared', 'started', 'updated', 'submitted',
             'target', 'commit', 'context', 'lite_full', 'steps', 'roles_order', 'materials', 'ci', 'error', 'warn', 'info',
             'profile', 'matches_design', 'human_check', 'answers', 'answer', 'memo', 'rows', 'decision', 'hash', 'comment',
             'at', 'findings', 'sampling', 'seed', 'count', 'picked', 'scores', 'RR1', 'RR2', 'RR3', 'RR4', 'RR5', 'RR6',
             'RR7', 'pass', 'escalations', 'applies', 'not_applicable', 'feedback', 'note']
HEADER = ('# review.yaml: レビューの記録（#50）。設計書のエディター（docs/claims/）のレビューモードが書き出した形。\n'
          '# レビュアーの名前は自己申告です。本当の承認は GitHub の PR のレビューで行います。\n')
DECISION_JA = {'approve': '承認', 'request_changes': '修正を求める', 'hold': '保留'}
ANSWER_JA = {'yes': 'Yes', 'no': 'No', 'na': '該当なし'}


# ------------------------------------------------------------------ reading and writing
class _Loader(yaml.SafeLoader):
    pass


def _no_dup(loader, node, deep=False):
    keys = set()
    for k, _ in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in keys:
            raise yaml.constructor.ConstructorError(None, None, f'duplicate key {key!r}', k.start_mark)
        keys.add(key)
    return loader.construct_mapping(node, deep)


_Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup)
# timestamps stay strings (the editor writes every string quoted; a hand-written date stays a string too)
_Loader.yaml_implicit_resolvers = {k: [(t, r) for t, r in v if t != 'tag:yaml.org,2002:timestamp']
                                   for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()}


def load_text(text):
    return yaml.load(text, Loader=_Loader)


def load(path):
    with open(path, encoding='utf-8') as f:
        return load_text(f.read())


_ESCAPE = re.compile('[\x7f-\x9f\u2028\u2029\ufeff\ufffe\uffff]')
_PLAIN_KEY = re.compile(r'^[A-Za-z][A-Za-z0-9_-]*$')
_SPECIAL = re.compile(r'^(?:y|n|yes|no|on|off|true|false|null)$', re.I)


def q(s):
    """A string as a YAML double-quoted scalar (JSON's escapes, and the characters PyYAML does not take raw)."""
    return _ESCAPE.sub(lambda m: '\\u%04x' % ord(m.group(0)), json.dumps(s, ensure_ascii=False))


def _key(k):
    return k if _PLAIN_KEY.match(k) and not _SPECIAL.match(k) else q(k)


def _order(d):
    rank = {k: i for i, k in enumerate(KEY_ORDER)}
    return sorted(d, key=lambda k: (rank.get(k, len(KEY_ORDER)), k if k not in rank else ''))


def _scalar(v):
    if v is None:
        return 'null'
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return row_hash.es_number(v)
    return q(str(v))


def _emit(v, ind, out):
    """Block YAML of a dict or a list at indent ind (lines appended to out)."""
    pad = ' ' * ind
    if isinstance(v, dict):
        for k in _order(v):
            x = v[k]
            if isinstance(x, dict) and x:
                out.append(f'{pad}{_key(k)}:')
                _emit(x, ind + 2, out)
            elif isinstance(x, list) and x and any(isinstance(i, (dict, list)) for i in x):
                out.append(f'{pad}{_key(k)}:')
                _emit(x, ind + 2, out)
            else:
                out.append(f'{pad}{_key(k)}: {_inline(x)}')
    else:
        for x in v:
            if isinstance(x, dict) and x:
                sub = []
                _emit(x, ind + 2, sub)
                out.append(pad + '- ' + sub[0][ind + 2:])
                out.extend(sub[1:])
            else:
                out.append(f'{pad}- {_inline(x)}')


def _inline(x):
    if isinstance(x, dict):
        return '{}'
    if isinstance(x, list):
        return '[' + ', '.join(_scalar(i) for i in x) + ']'
    return _scalar(x)


def materials_version():
    with open(os.path.join(ROOT, 'templates', 'review', 'perspectives.md'), encoding='utf-8') as f:
        return re.match(r'<!-- template_version: ([0-9.]+) -->', f.readline()).group(1)


def version_of(text):
    m = re.match(r'# template_version: (\d+\.\d+\.\d+)', text or '')
    return m.group(1) if m else None


def dump(data, version=None):
    """The canonical text. Line 1 is the template_version of the review materials (templates/CONTRIBUTING.md 4.: every
    YAML under templates/ starts with it): the version given (a file read in keeps its own), else that of perspectives.md."""
    out = []
    _emit(data, 0, out)
    return f'# template_version: {version or materials_version()}\n' + HEADER + '\n'.join(out) + '\n'


# ------------------------------------------------------------------ checks
def _questions():
    import review_check
    import trace_check
    return review_check.parse_questions(trace_check._read(os.path.join(ROOT, 'templates', 'review', 'perspectives.md')))


def _criteria():
    with open(os.path.join(ROOT, 'templates', 'review', 'escalation.md'), encoding='utf-8') as f:
        return set(re.findall(r'^\| `([a-z0-9-]+)` \|', f.read(), re.M))


def schema_errors(data):
    import jsonschema
    with open(SCHEMA, encoding='utf-8') as f:
        schema = json.load(f)
    v = jsonschema.Draft202012Validator(schema)
    return [f'schema: {"/".join(map(str, e.absolute_path)) or "(root)"}: {e.message}'
            for e in sorted(v.iter_errors(data), key=lambda e: list(map(str, e.absolute_path)))]


def sample(seed, count, docs):
    """The rejected rows of claims.yaml (anchors) ranked by sha256(seed:anchor), the first count."""
    rows, dup = row_hash.anchors(docs)
    cand = sorted(a for a, kind, _, r in rows if kind == 'claims' and a not in dup and isinstance(r, dict)
                  and r.get('decision') == '却下')
    return sorted(cand, key=lambda a: hashlib.sha256(f'{seed}:{a}'.encode('utf-8')).hexdigest())[:count]


def row_states(review, hashes):
    """{anchor: 'current' | 'stale' | 'missing'} of the row decisions of one review."""
    out = {}
    for a, r in (review.get('rows') or {}).items():
        out[a] = 'missing' if a not in hashes else 'current' if hashes[a] == r.get('hash') else 'stale'
    return out


def check(data, design=None):
    """(errors, notes): errors fail the check; notes are the stale / missing decisions."""
    errs = schema_errors(data)
    if errs:
        return errs, []
    qids = {x['id'] for x in _questions()}
    crit = _criteria()
    names = [r['reviewer']['name'] for r in data['reviews']]
    for n in sorted({n for n in names if names.count(n) > 1}):
        errs.append(f'reviewer {n!r} has two reviews (merge them or rename one)')
    notes = []
    hashes = docs = None
    if design:
        docs = row_hash.load(design)
        hashes = row_hash.row_hashes(design)['hashes']
    for rv in data['reviews']:
        who = rv['reviewer']['name']
        for qid in rv['answers']:
            if qid not in qids:
                errs.append(f'{who}: answers: {qid} is not a question of perspectives.md')
        ids = [f['id'] for f in rv['findings']]
        for i in sorted({i for i in ids if ids.count(i) > 1}):
            errs.append(f'{who}: finding {i} is written twice')
        for f in rv['findings']:
            for qid in f.get('questions') or []:
                if qid not in qids:
                    errs.append(f'{who}: finding {f["id"]}: {qid} is not a question of perspectives.md')
        esc = rv.get('escalations') or {}
        for c in [x['criterion'] for x in esc.get('applies') or []] + list(esc.get('not_applicable') or []):
            if c not in crit:
                errs.append(f'{who}: escalations: {c} is not a criterion of escalation.md')
        fids = set(ids)
        for fb in rv.get('feedback') or []:
            for i in fb.get('findings') or []:
                if i not in fids:
                    errs.append(f'{who}: feedback names finding {i}, which is not in findings')
        sm = rv.get('sampling')
        if sm:
            for a in (sm.get('scores') or {}):
                if a not in sm['picked']:
                    errs.append(f'{who}: sampling: {a} is scored but not picked')
            if docs is not None:
                want = sample(sm['seed'], sm['count'], docs)
                if sm['picked'] != want:
                    errs.append(f'{who}: sampling: seed {sm["seed"]!r} draws {want}, the file has {sm["picked"]}')
        if hashes is not None:
            for a, st in row_states(rv, hashes).items():
                if st != 'current':
                    d = DECISION_JA[rv['rows'][a]['decision']]
                    notes.append(f'{who}: {a} ({d}): ' + ('再確認が要る（行の内容が記録の後に変わった）' if st == 'stale'
                                                          else '台帳に無い行の記録（行が消えたか ID が変わった）'))
    return errs, notes


def merge(datas):
    """One file with the reviews of all; the same reviewer twice must have equal records."""
    designs = sorted({d['design'] for d in datas})
    if len(designs) > 1:
        raise ValueError(f'the files are about different designs: {designs}')
    out = {'format': FORMAT, 'design': designs[0], 'independent': any(d.get('independent') for d in datas), 'reviews': []}
    by = {}
    for d in datas:
        for rv in d['reviews']:
            n = rv['reviewer']['name']
            if n in by:
                if json.dumps(by[n], sort_keys=True, ensure_ascii=False) != json.dumps(rv, sort_keys=True, ensure_ascii=False):
                    raise ValueError(f'reviewer {n!r} is in two files with different records (keep one, or rename)')
                continue
            by[n] = rv
            out['reviews'].append(rv)
    return out


# ------------------------------------------------------------------ the report (the twin of the editor's generator)
def _cell(s):
    s = '' if s is None else str(s)
    s = re.sub(r'\s*\n\s*', ' ', s).replace('|', '｜').strip()
    return s or '—'


def _row(cells):
    return '| ' + ' | '.join(cells) + ' |'


def _date(t):
    return str(t or '')[:10]


def _short(anchor):
    return anchor.split(':', 1)[1] if anchor.startswith('claims:') else anchor


def report(data, design, data_review, reviewer=None, label=None):
    """The Markdown report of one review. data_review: the dict of docs/claims/data/review.js (build_claims_viewer)."""
    rvs = data['reviews']
    rv = next((r for r in rvs if r['reviewer']['name'] == reviewer), None) if reviewer else (rvs[0] if rvs else None)
    if rv is None:
        raise ValueError('no such review')
    hashes = row_hash.row_hashes(design)['hashes'] if design else {}
    docs = row_hash.load(design) if design else {}
    return report_text(data, rv, data_review, hashes, docs, label)


def report_text(data, rv, R, hashes, docs, label=None):
    form = R['report']
    heads = {s['heading'][:2]: s for s in form['sections']}
    stage_name = {s['id']: s['name'] for s in R['stages']}
    qs = R['questions']
    ctx = rv.get('context') or {}
    who = rv['reviewer']
    lines = [f'# レビューレポート：{label or data["design"]}', '',
             '> 設計書のエディターのレビューモード（#50）が `review.yaml` から生成した。レビュアーの名前は自己申告で、'
             '本当の承認は GitHub の PR のレビューで行う。', '']

    def head(k):
        lines.append('## ' + heads[k]['heading'])
        lines.append('')

    def table(k, rows):
        hd = heads[k]['header']
        lines.append(_row(hd))
        lines.append(_row(['---'] * len(hd)))
        for r in rows or [[''] * len(hd)]:
            lines.append(_row(r) if any(r) else '|' + ' |' * len(hd))
        lines.append('')
    # 1.
    tgt = rv.get('target') or {}
    sm = rv.get('sampling') or {}
    scores = sm.get('scores') or {}
    scored = [a for a in sm.get('picked') or [] if a in scores]
    passed = sum(1 for a in scored if scores[a].get('pass'))
    cand = sum(1 for _, kind, _, r in row_hash.anchors(docs)[0] if kind == 'claims' and isinstance(r, dict) and r.get('decision') == '却下') if docs else None
    ans = rv.get('answers') or {}
    per = []
    tot = {'yes': 0, 'no': 0, 'na': 0}
    for s in R['stages']:
        c = {'yes': 0, 'no': 0, 'na': 0}
        for x in qs:
            if x['stage'] == s['id'] and x['id'] in ans:
                c[ans[x['id']]['answer']] += 1
        for k in c:
            tot[k] += c[k]
        per.append(f'{s["name"].split(" ", 1)[1]} Yes {c["yes"]}／No {c["no"]}／該当なし {c["na"]}')
    answered = sum(tot.values())
    ci = ctx.get('ci')
    ci_text = ('記録なし' if not ci else
               f'claim_lint error {ci["error"]}・warn {ci["warn"]}・info {ci["info"]}'
               + (f'（profile {ci["profile"]}）' if ci.get('profile') else '')
               + ('' if 'matches_design' not in ci else '。設計書の 1. と' + ('一致' if ci['matches_design'] else '一致しない'))
               + (f'。{ci["note"]}' if ci.get('note') else ''))
    samp = ('記録なし' if not sm else
            f'乱数の種 `{sm["seed"]}`（claims.yaml の却下の行' + (f' {cand} 行' if cand is not None else '') + f'から {sm["count"]} 行。'
            'sha256(種:行) の順）：' + '・'.join(_short(a) for a in sm['picked'])
            + f'。{len(scored)} 件を採点、合格 {passed}・不合格 {len(scored) - passed}'
            + (f'（未採点 {len(sm["picked"]) - len(scored)}）' if len(scored) < len(sm['picked']) else ''))
    versions = R.get('versions') or {}
    mats = f'templates/review（perspectives.md の template_version {R["template_version"]}' + \
        ('、report_template.md ' + versions['templates/review/report_template.md'] if 'templates/review/report_template.md' in versions else '') + '）'
    if ctx.get('materials'):
        mats += '。' + ctx['materials']
    reviewer = f'{who["name"]}（' + ('LLM' + (f'：{who["model"]}' if who.get('model') else '') if who['kind'] == 'llm' else '人') + \
        '。名前は自己申告）' + (f'。{ctx["roles_order"]}' if ctx.get('roles_order') else '')
    date = _date(rv['started']) + (f'〜{_date(rv["submitted"])}' if rv.get('submitted') and _date(rv['submitted']) != _date(rv['started']) else '')
    values = {'対象': f'`{data["design"]}`' + (f'（版 {tgt["commit"]}）' if tgt.get('commit') else '') + (f'。{tgt["note"]}' if tgt.get('note') else ''),
              'Lite／Full': ctx.get('lite_full') or '記録なし', '実施した手順の段': ctx.get('steps') or '記録なし',
              'レビュアーと役割': reviewer, '実施日': date, '使った教材の版': mats, 'CI の結果': ci_text, '抜き取りの結果': samp,
              '問いの回答': f'全 {len(qs)} 問のうち {answered} 問に回答（未回答 {len(qs) - answered}）。' + '。'.join(per)
              + f'。合計 Yes {tot["yes"]}／No {tot["no"]}／該当なし {tot["na"]}'}
    head('1.')
    table('1.', [[k, _cell(values.get(k))] for k in heads['1.']['items']])
    # 2. / 3.
    fs = rv.get('findings') or []
    head('2.')
    table('2.', [[_cell(f['id']), _cell(f['location']), _cell(f['content'] + (f'（判定の理由：{f["verdict_reason"]}）' if f.get('verdict_reason') else '')),
                  f['severity'], f['origin'], f['kind'], _cell(f.get('confused_question') if f['kind'] == '目的と仕組みの不一致' else None),
                  f['verdict']] for f in fs])
    head('3.')
    table('3.', [[_cell(f['id']), _cell((f.get('response') or {}).get('owner')), _cell((f.get('response') or {}).get('due')),
                  (f.get('response') or {}).get('state') or '未着手', _cell((f.get('response') or {}).get('ref'))] for f in fs])
    # 4.
    esc = rv.get('escalations') or {}
    head('4.')
    table('4.', [[_cell(e['criterion']), _cell(e['location']), _cell(e.get('to')), _cell(e.get('due')), _cell(e.get('conclusion'))]
                 for e in esc.get('applies') or []])
    na = esc.get('not_applicable')
    lines.append('当てはまらなかった基準：' + ('・'.join(f'`{x}`' for x in na) if na else '（記録なし）'))
    lines.append('')
    # 5.
    head('5.')
    table('5.', [[_cell(x['to']), _cell(x['content']), _cell('・'.join(x.get('findings') or [])), _cell(x.get('ref'))]
                 for x in rv.get('feedback') or []])
    # 6.
    head('6.')
    table('6.', [[_cell(_short(a)), 'rationale'] + [scores[a].get(f'RR{i}') or '対象外' for i in range(1, 8)]
                 + ['合格' if scores[a].get('pass') else '不合格'] for a in scored])
    notes = [f'- {_short(a)}：{scores[a]["note"]}' for a in scored if scores[a].get('note')]
    if notes:
        lines.extend(notes + [''])
    # 7.
    head('7.')
    hc = ctx.get('human_check') or ('人による点検は未実施。' + ('レビュアーは LLM のセッションで、人のレビュアーの採否は未了。' if who['kind'] == 'llm' else ''))
    lines.append(hc)
    lines.append('')
    lines.append('レビュアーの名前は自己申告です（エディターにはログインが無い）。本当の承認は GitHub の PR のレビューで行います。')
    lines.append('')
    # 8.
    head('8.')
    table('8.', [[stage_name.get(x['stage'], '—'), f'`{x["id"]}`', ANSWER_JA[ans[x['id']]['answer']], _cell(ans[x['id']].get('memo'))]
                 for x in qs if x['id'] in ans])
    left = [x['id'] for x in qs if x['id'] not in ans]
    if left:
        lines.append(f'未回答：{len(left)} 問（' + '・'.join(f'`{i}`' for i in left) + '）')
        lines.append('')
    # 9. the row decisions (not in the form; the form allows sections after 8.)
    lines.append('## 9. 行ごとの記録（エディターのレビューモード、#50）')
    lines.append('')
    lines.append('行の内容のハッシュ（RFC 8785 JCS の SHA-256、`tools/row_hash.py`）に結びつけた判定です。記録の後に行が変わると「再確認が要る」になります。')
    lines.append('')
    rows = rv.get('rows') or {}
    st = row_states(rv, hashes)
    lines.append(_row(['行', '判定', '日時', '今の行との対応', 'コメント']))
    lines.append(_row(['---'] * 5))
    label_of = {'current': '一致（記録のときのまま）', 'stale': '再確認が要る（行が変わった）', 'missing': '台帳に無い行'}
    for a in sorted(rows):
        r = rows[a]
        lines.append(_row([f'`{a}`', DECISION_JA[r['decision']], _cell(r['at']), label_of[st[a]] + f'（{r["hash"][:12]}）', _cell(r.get('comment'))]))
    if not rows:
        lines.append('|' + ' |' * 5)
    c = {k: sum(1 for a in rows if rows[a]['decision'] == k) for k in DECISION_JA}
    lines.append('')
    lines.append(f'計 {len(rows)} 行：' + '・'.join(f'{DECISION_JA[k]} {c[k]}' for k in DECISION_JA)
                 + f'。再確認が要る {sum(1 for v in st.values() if v == "stale")}・台帳に無い {sum(1 for v in st.values() if v == "missing")}')
    return '\n'.join(lines) + '\n'


def review_data():
    import build_claims_viewer
    return build_claims_viewer.review_bundle()


# ------------------------------------------------------------------ CLI
def _write(text, path):
    if path:
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
    else:
        sys.stdout.buffer.write(text.encode('utf-8'))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('check')
    c.add_argument('file')
    c.add_argument('--design')
    c.add_argument('--fail-on-stale', action='store_true')
    m = sub.add_parser('merge')
    m.add_argument('files', nargs='+')
    m.add_argument('-o', '--output')
    s = sub.add_parser('sample')
    s.add_argument('design')
    s.add_argument('--seed', required=True)
    s.add_argument('--count', type=int, default=3, choices=(2, 3))
    r = sub.add_parser('report')
    r.add_argument('file')
    r.add_argument('--design', required=True)
    r.add_argument('--reviewer')
    r.add_argument('--label')
    g = r.add_mutually_exclusive_group()
    g.add_argument('-o', '--output')
    g.add_argument('--check', metavar='REPORT_MD', help='exit 1 when REPORT_MD differs from the generated report')
    d = sub.add_parser('diff')
    d.add_argument('base')
    d.add_argument('design')
    a = ap.parse_args(argv)
    out = sys.stdout
    if a.cmd == 'check':
        data = load(a.file)
        errs, notes = check(data, a.design)
        with open(a.file, encoding='utf-8') as f:
            raw = f.read().replace('\r\n', '\n')
        if not errs and raw != dump(data, version_of(raw)):
            errs.append('the file is not in the canonical form the editor writes (python tools/review_record.py merge FILE -o FILE rewrites it)')
        for e in errs:
            print('error ' + e, file=out)
        for n in notes:
            print('stale ' + n, file=out)
        n_rows = sum(len(rv['rows']) for rv in data.get('reviews') or []) if not schema_errors(data) else 0
        print(f'review_record check: {len(data.get("reviews") or [])} reviews, {n_rows} row decisions, '
              f'{len(notes)} need a new look' + (f', {len(errs)} errors' if errs else '') + ' ->'
              + (' FAIL' if errs or (notes and a.fail_on_stale) else ' OK'), file=out)
        return 1 if errs or (notes and a.fail_on_stale) else 0
    if a.cmd == 'merge':
        _write(dump(merge([load(p) for p in a.files])), a.output)
        return 0
    if a.cmd == 'sample':
        for x in sample(a.seed, a.count, row_hash.load(a.design)):
            print(x, file=out)
        return 0
    if a.cmd == 'report':
        text = report(load(a.file), a.design, review_data(), a.reviewer, a.label)
        if a.check:
            with open(a.check, encoding='utf-8') as f:
                cur = f.read().replace('\r\n', '\n')
            ok = cur == text
            print(f'review_record report --check {a.check}: ' + ('OK' if ok else 'FAIL (differs from what review.yaml generates; '
                  f'run: python tools/review_record.py report {a.file} --design {a.design} -o {a.check})'), file=out)
            return 0 if ok else 1
        _write(text, a.output)
        return 0
    if a.cmd == 'diff':
        old = row_hash.row_hashes(a.base)['hashes']
        new = row_hash.row_hashes(a.design)['hashes']
        for k in sorted(set(old) | set(new)):
            if k not in old:
                print(f'added    {k}', file=out)
            elif k not in new:
                print(f'removed  {k}', file=out)
            elif old[k] != new[k]:
                print(f'changed  {k}', file=out)
        return 0
    return 2


if __name__ == '__main__':
    sys.exit(main())
