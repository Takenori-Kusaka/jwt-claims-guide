# -*- coding: utf-8 -*-
"""review.yaml, the review records of a design (#50, #67): check, viewed marks that no longer hold, merge, migrate,
sampling, report.

  python tools/review_record.py check REVIEW_YAML [--design DIR] [--fail-on-stale] [--annotate]
  python tools/review_record.py migrate REVIEW_YAML [-o OUT.yaml | --check OUT.yaml]
  python tools/review_record.py merge A.yaml B.yaml [...] -o OUT.yaml
  python tools/review_record.py sample --seed SEED [--count 3] DIR
  python tools/review_record.py sample DIR --reseed --reason TEXT --file REVIEW_YAML --reviewer NAME
  python tools/review_record.py report REVIEW_YAML --design DIR [--reviewer NAME] [-o OUT.md | --check OUT.md]
  python tools/review_record.py diff BASE_DIR DIR

The design editor (docs/claims/) writes and reads review.yaml; this is the Python side of the same records, for CI.

The form (claims-review/2, templates/review/review.schema.json) follows a pull request review (#67): per reviewer, the
rows marked as viewed (viewed: a personal mark bound to the content hash of the row, not an approval), the comments
(state pending until submitted, then unresolved or resolved; with the severity, kind and so on of report_template.md)
and the submissions (each with one verdict for the whole review - approve, request_changes or comment - and the hashes
of the rows viewed then). The earlier form (claims-review/1, review.v1.schema.json: a decision per row, findings) is
still read: every command validates it against its own schema and works on its migration (migrate()); committed v1
files need not be rewritten (research/pilot/**/reviews/*/review.yaml are kept byte for byte, commitments.txt).

check: the file against its schema (JSON Schema 2020-12), then: the reviewer names are unique; the comment IDs are
  unique within a review; submitted is null exactly when there is no submission, else the time of the latest one; a
  comment named in a submission is not pending and a comment in no submission is; the sha256 of a snapshot is the hash
  of its mark; the escalation criteria are IDs of escalation.md. Warnings (not errors): an answer or a comment about a
  question that today's perspectives.md does not have (the materials changed after the review); with --design, every
  viewed mark is compared with the row as it is now (tools/row_hash.py): the same hash (current), another hash (stale:
  前回の確認から変更あり) or a row that is not in the registry any more (missing: 一覧に無い行); a latest submission
  that approves rows which have changed since (古い承認); and the population of the draw (sha256 of the rejected rows)
  against the recorded one: when it changed, the draw is reported, not failed (sample --reseed draws again and keeps
  the old draw). The same population with other picked rows is an error. Stale and missing marks and an old approval
  fail the check only with --fail-on-stale; --annotate prints the warnings as GitHub Actions ::warning lines. The names
  are self-declared: the approval that counts is the GitHub pull request review.
migrate: a claims-review/1 file as claims-review/2 (rows -> viewed with the old decision kept in migrated_from,
  findings -> comments, one submission with the verdict comment when the review was submitted). --check OUT exits 1
  when OUT is not the migration of the file (CI: the migrated copies of the pilot reviews).
merge: the reviews of several files into one (same design); the same reviewer in two files must have the same records.
  The result is claims-review/2.
sample: the rejected rows of claims.yaml ranked by sha256(seed + ':' + anchor), the first COUNT (2 or 3), the same draw
  as the editor's. --reseed draws again into a review.yaml with a --reason, keeping the earlier draw in
  sampling.previous (templates/CONTRIBUTING.md 4., レビューの記録がある設計書を変えるとき); a v1 file is written
  back as claims-review/2.
report: the review report in the form of templates/review/report_template.md, the same text as the editor's
  (ClaimsReviewFormat.reportText of docs/claims/review-format.js; tools/tests/test_review_record.py checks the form
  with review_check.check_report; the browser test compares the two generators).
diff: the rows whose content hash differs between two versions of a design (added, removed, changed): the rows a
  reviewer has to look at again. claim_lint diff (L10) checks whether a change breaks receivers; this lists every
  changed row, breaking or not.

The file is written in one canonical form (key order, every string in double quotes, JSON escapes), the same as the
editor writes, so that reading and writing it again gives the same bytes.
"""
import argparse
import copy
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
SCHEMA_V1 = os.path.join(ROOT, 'templates', 'review', 'review.v1.schema.json')
FORMAT = 'claims-review/2'
FORMAT_V1 = 'claims-review/1'
# The order of the keys in the canonical text. The keys of claims-review/2 (#67: column, suggestion, summary, state of a
# comment, traits, viewed, comments, submissions, unresolved, migrated, resolved_at, snapshot, migrated_from) are put
# between the keys of claims-review/1 without changing the order of those: a v1 file still dumps to the same bytes.
KEY_ORDER = ['format', 'design', 'independent', 'reviews', 'reviewer', 'id', 'criterion', 'name', 'to', 'location', 'anchors',
             'column', 'questions', 'content', 'suggestion', 'severity', 'origin', 'kind', 'model', 'confused_question',
             'verdict', 'verdict_reason', 'summary',
             'response', 'owner', 'due', 'state', 'ref', 'conclusion', 'self_declared', 'started', 'updated', 'submitted',
             'independence', 'mode', 'broken_at', 'viewed_others_at', 'target', 'commit', 'materials', 'perspectives',
             'report_template', 'context', 'lite_full', 'steps', 'roles_order', 'ci', 'error', 'warn', 'info',
             'profile', 'matches_design', 'human_check', 'traits', 'answers', 'answer', 'memo', 'rows', 'viewed', 'decision',
             'reviewer_kind', 'hash', 'comment', 'edited_after_viewing_others', 'bulk', 'at', 'resolved_at', 'snapshot', 'migrated_from',
             'findings', 'comments', 'unresolved', 'migrated', 'submissions', 'sampling', 'seed', 'count', 'picked',
             'population', 'scores', 'RR1', 'RR2', 'RR3', 'RR4', 'RR5', 'RR6', 'RR7', 'pass', 'reason', 'previous',
             'replaced_at', 'escalations', 'applies', 'not_applicable', 'feedback', 'note']
HEADER_V1 = ('# review.yaml: レビューの記録（#50）。設計書のエディター（docs/claims/）のレビューモードが書き出した形。\n'
             '# レビュアーの名前は自己申告です。本当の承認は GitHub の PR のレビューで行います。\n')
HEADER = ('# review.yaml: レビューの記録。設計書のエディター（docs/claims/）が書き出した形（claims-review/2）。\n'
          '# レビュアーの名前は自己申告です。本当の承認は GitHub の PR のレビューで行います。\n')
STALE_NOTE = '前回の確認から変更あり'
MISSING_NOTE = '一覧に無い行'
OLD_APPROVAL_NOTE = '古い承認（内容が変更されました）'
DECISION_JA = {'approve': '承認', 'request_changes': '修正を求める', 'hold': '保留'}
VERDICT_JA = {'approve': '承認', 'request_changes': '変更を依頼', 'comment': 'コメントのみ'}
ANSWER_JA = {'yes': 'Yes', 'no': 'No', 'na': '該当なし'}
MIGRATED_SUMMARY = 'claims-review/1 の記録から移行した。v1 には全体の判定が無い（行ごとの判定は viewed の migrated_from に残した）'


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
    header = HEADER_V1 if is_v1(data) else HEADER
    return f'# template_version: {version or materials_version()}\n' + header + '\n'.join(out) + '\n'


# ------------------------------------------------------------------ claims-review/1 -> claims-review/2 (#67)
def is_v1(data):
    return isinstance(data, dict) and data.get('format') == FORMAT_V1


def migrate(data):
    """A claims-review/1 record as claims-review/2 (a new dict; a v2 record is returned as it is). Nothing is dropped:
    the decision per row and its comment are kept in viewed[].migrated_from. The same steps as
    ClaimsReviewFormat.migrate of docs/claims/review-format.js (the two give the same text).

    rows -> viewed (the mark that the content was looked at); findings -> comments, with state unresolved when the
    review was submitted and pending when not; feedback[].findings -> comments; a submitted review gets one submission
    with the verdict comment (v1 had no verdict for the whole review) and the hashes of all its rows."""
    if not is_v1(data):
        return data
    data = copy.deepcopy(data)
    out = {k: (FORMAT if k == 'format' else v) for k, v in data.items() if k != 'reviews'}
    out['reviews'] = []
    for rv in data.get('reviews') or []:
        submitted = rv.get('submitted')
        new = {}
        for k, v in rv.items():
            if k == 'rows':
                viewed = {}
                for a, r in v.items():
                    m = {'hash': r['hash'], 'at': r['at']}
                    for x in ('reviewer_kind', 'edited_after_viewing_others'):
                        if x in r:
                            m[x] = r[x]
                    m['migrated_from'] = {'decision': r['decision']}
                    if 'comment' in r:
                        m['migrated_from']['comment'] = r['comment']
                    viewed[a] = m
                new['viewed'] = viewed
            elif k == 'findings':
                new['comments'] = [dict(f, state='unresolved' if submitted else 'pending') for f in v]
            elif k == 'feedback':
                new['feedback'] = [{('comments' if x == 'findings' else x): y for x, y in fb.items()} for fb in v]
            else:
                new[k] = v
        new['submissions'] = [] if not submitted else [{
            'at': submitted, 'verdict': 'comment', 'summary': MIGRATED_SUMMARY,
            'viewed': {a: r['hash'] for a, r in (rv.get('rows') or {}).items()},
            'comments': [f['id'] for f in rv.get('findings') or []], 'migrated': True}]
        out['reviews'].append(new)
    return out


# ------------------------------------------------------------------ checks
def _questions():
    import review_check
    import trace_check
    return review_check.parse_questions(trace_check._read(os.path.join(ROOT, 'templates', 'review', 'perspectives.md')))


def _criteria():
    with open(os.path.join(ROOT, 'templates', 'review', 'escalation.md'), encoding='utf-8') as f:
        return set(re.findall(r'^\| `([a-z0-9-]+)` \|', f.read(), re.M))


def schema_errors(data):
    """Against review.schema.json (claims-review/2), or review.v1.schema.json for a claims-review/1 record."""
    import jsonschema
    with open(SCHEMA_V1 if is_v1(data) else SCHEMA, encoding='utf-8') as f:
        schema = json.load(f)
    v = jsonschema.Draft202012Validator(schema)
    return [f'schema: {"/".join(map(str, e.absolute_path)) or "(root)"}: {e.message}'
            for e in sorted(v.iter_errors(data), key=lambda e: list(map(str, e.absolute_path)))]


def _rejected(docs):
    rows, dup = row_hash.anchors(docs)
    return sorted(a for a, kind, _, r in rows if kind == 'claims' and a not in dup and isinstance(r, dict)
                  and r.get('decision') == '却下')


def sample(seed, count, docs):
    """The rejected rows of claims.yaml (anchors) ranked by sha256(seed:anchor), the first count."""
    return sorted(_rejected(docs), key=lambda a: hashlib.sha256(f'{seed}:{a}'.encode('utf-8')).hexdigest())[:count]


def population(docs, hashes):
    """sha256 of the population of the draw: each rejected row as '<anchor> <row hash>', sorted, one per line."""
    return hashlib.sha256('\n'.join(f'{a} {hashes.get(a, "")}' for a in _rejected(docs)).encode('utf-8')).hexdigest()


def row_states(review, hashes):
    """{anchor: 'current' | 'stale' | 'missing'} of the viewed marks of one review (claims-review/2)."""
    out = {}
    for a, r in (review.get('viewed') or {}).items():
        out[a] = 'missing' if a not in hashes else 'current' if hashes[a] == r.get('hash') else 'stale'
    return out


def stale_approval(review, hashes):
    """The rows of the latest submission, when it is an approval, whose content is not what was approved (changed or
    gone): the approval is old. [] when the latest submission is not an approval or every row is as it was."""
    subs = review.get('submissions') or []
    if not subs or subs[-1].get('verdict') != 'approve':
        return []
    return sorted(a for a, h in (subs[-1].get('viewed') or {}).items() if hashes.get(a) != h)


def check(data, design=None):
    """(errors, notes): errors fail the check; notes are the viewed marks that no longer hold (the row changed or is
    gone), an approval that is old, and what changed in the materials. A claims-review/1 record is checked against its
    own schema and then as its migration."""
    errs = schema_errors(data)
    if errs:
        return errs, []
    data = migrate(data)
    qids = {x['id'] for x in _questions()}
    crit = _criteria()
    notes = []
    names = [r['reviewer']['name'] for r in data['reviews']]
    for n in sorted({n for n in names if names.count(n) > 1}):
        errs.append(f'reviewer {n!r} has two reviews (merge them or rename one)')
    hashes = docs = None
    if design:
        docs = row_hash.load(design)
        hashes = row_hash.row_hashes(design)['hashes']
    for rv in data['reviews']:
        who = rv['reviewer']['name']
        # a question that is not in today's perspectives.md: the materials changed after the review (not an error; the
        # report keeps the versions of the review, materials)
        gone = [q for q in rv['answers'] if q not in qids]
        if gone:
            notes.append(f'{who}: 今の観点書に無い問いへの回答 {len(gone)} 件（{"・".join(gone[:5])}）。教材が記録の後に変わった'
                         f'（記録した時の版 {(rv.get("materials") or {}).get("perspectives", "不明")}・今の版 {materials_version()}）')
        ids = [f['id'] for f in rv['comments']]
        for i in sorted({i for i in ids if ids.count(i) > 1}):
            errs.append(f'{who}: comment {i} is written twice')
        for f in rv['comments']:
            for qid in f.get('questions') or []:
                if qid not in qids:
                    notes.append(f'{who}: comment {f["id"]}: {qid} は今の観点書に無い（教材が記録の後に変わった）')
        # one verdict per submission; submitted is the time of the latest one
        subs = rv['submissions']
        if rv['submitted'] is None and subs:
            errs.append(f'{who}: submitted is null but there are {len(subs)} submissions')
        elif rv['submitted'] is not None and not subs:
            errs.append(f'{who}: submitted is {rv["submitted"]} but there is no submission')
        elif subs and subs[-1]['at'] != rv['submitted']:
            errs.append(f'{who}: submitted ({rv["submitted"]}) is not the time of the latest submission ({subs[-1]["at"]})')
        sent = set()
        for k, sb in enumerate(subs):
            for i in sb.get('comments') or []:
                if i not in ids:
                    errs.append(f'{who}: submission {k + 1} names comment {i}, which is not in comments')
                sent.add(i)
        # pending = not in a submission yet
        for f in rv['comments']:
            if f['id'] in sent and f['state'] == 'pending':
                errs.append(f'{who}: comment {f["id"]} is in a submission but its state is pending')
            elif f['id'] not in sent and f['state'] != 'pending':
                errs.append(f'{who}: comment {f["id"]} is {f["state"]} but in no submission (a comment that was not submitted is pending)')
        for a, m in rv['viewed'].items():
            if 'snapshot' in m and hashlib.sha256(m['snapshot'].encode('utf-8')).hexdigest() != m['hash']:
                errs.append(f'{who}: viewed {a}: the sha256 of snapshot is not hash')
        esc = rv.get('escalations') or {}
        for c in [x['criterion'] for x in esc.get('applies') or []] + list(esc.get('not_applicable') or []):
            if c not in crit:
                errs.append(f'{who}: escalations: {c} is not a criterion of escalation.md')
        fids = set(ids)
        for fb in rv.get('feedback') or []:
            for i in fb.get('comments') or []:
                if i not in fids:
                    errs.append(f'{who}: feedback names comment {i}, which is not in comments')
        sm = rv.get('sampling')
        if sm:
            for a in (sm.get('scores') or {}):
                if a not in sm['picked']:
                    errs.append(f'{who}: sampling: {a} is scored but not picked')
            if docs is not None:
                want = sample(sm['seed'], sm['count'], docs)
                pop = population(docs, hashes)
                if sm.get('population') and sm['population'] != pop:
                    # the registry changed after the draw: the draw was right for the rows of then
                    notes.append(f'{who}: 抜き取りの母集団が変わった（却下の行か、その内容が記録の後に変わった。種 {sm["seed"]!r} は今の台帳では '
                                 f'{want} を選ぶ）。引き直すなら：python tools/review_record.py sample --reseed --reason "<理由>" '
                                 f'--file <review.yaml> --reviewer "{who}" <dir>')
                elif sm['picked'] != want:
                    errs.append(f'{who}: sampling: seed {sm["seed"]!r} draws {want} from the same rows, the file has {sm["picked"]}'
                                if sm.get('population') else
                                f'{who}: sampling: seed {sm["seed"]!r} draws {want}, the file has {sm["picked"]} (no population '
                                'recorded: run sample --reseed to record one)')
        if hashes is not None:
            for a, st in row_states(rv, hashes).items():
                if st != 'current':
                    notes.append(f'{who}: {a} (確認済み): ' + (STALE_NOTE + '（行の内容が、確認済みの印の後に変わった）' if st == 'stale'
                                                              else MISSING_NOTE + 'の記録（行が消えたか ID が変わった）'))
            old = stale_approval(rv, hashes)
            if old:
                notes.append(f'{who}: {OLD_APPROVAL_NOTE}：{rv["submissions"][-1]["at"]} の承認の後に {len(old)} 行が変わった'
                             f'（{"・".join(old[:5])}{" ほか" if len(old) > 5 else ""}）')
    return errs, notes


def merge(datas):
    """One file with the reviews of all; the same reviewer twice must have equal records. claims-review/1 records are
    migrated: the result is always claims-review/2."""
    datas = [migrate(d) for d in datas]
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
# Every value that comes from review.yaml is escaped for Markdown (PR #52 check): & < > as entities (no raw HTML, so a
# "<!--" in a memo cannot hide the rest of the report), \ ` * _ [ ] ~ with a backslash, | as a full-width bar, line
# breaks as spaces; a line that starts with a user value gets a backslash before # > + - = * or "1." so it stays text.
_MD = re.compile(r'([\\`*_\[\]~])')
_LINE_START = re.compile(r'^(?:[#>+\-=*]|\d+[.)])')


def md(s):
    s = '' if s is None else str(s)
    s = re.sub(r'\s*\n\s*', ' ', s).strip()
    s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return _MD.sub(r'\\\1', s).replace('|', '｜')


def md_line(s):
    t = md(s)
    return '\\' + t if _LINE_START.match(t) else t


def _cell(s):
    return md(s) or '—'


def _row(cells):
    return '| ' + ' | '.join(cells) + ' |'


def _date(t):
    return str(t or '')[:10]


def _short(anchor):
    return anchor.split(':', 1)[1] if anchor.startswith('claims:') else anchor


def report(data, design, data_review, reviewer=None, label=None, version=None):
    """The Markdown report of one review. data_review: the dict of docs/claims/data/review.js (build_claims_viewer);
    version: the template_version of line 1 of review.yaml (the materials of the review when materials is not recorded)."""
    data = migrate(data)
    rvs = data['reviews']
    rv = next((r for r in rvs if r['reviewer']['name'] == reviewer), None) if reviewer else (rvs[0] if rvs else None)
    if rv is None:
        raise ValueError('no such review')
    hashes = row_hash.row_hashes(design)['hashes'] if design else {}
    docs = row_hash.load(design) if design else {}
    return report_text(data, rv, data_review, hashes, docs, label, version)


def independence_text(data, rv):
    """How the independent review went (report 1.), or '' when it was not independent."""
    ind = rv.get('independence') or {}
    if not data.get('independent') and not ind:
        return ''
    parts = []
    if ind.get('mode') == 'broken':
        parts.append(f'独立レビュー：提出の前に外れた（{ind.get("broken_at", "日時不明")}。{ind.get("reason", "理由の記録なし")}）')
    else:
        parts.append('独立レビュー：提出まで、ほかのレビュアーの記録を画面で隠した（画面で隠すだけで、review.yaml を開けば見える。守ったかは自己申告）')
    if ind.get('viewed_others_at'):
        parts.append(f'ほかのレビュアーの記録を初めて見た日時 {ind["viewed_others_at"]}')
    n = sum(1 for x in (rv.get('answers') or {}).values() if x.get('edited_after_viewing_others')) + \
        sum(1 for x in (rv.get('viewed') or {}).values() if x.get('edited_after_viewing_others')) + \
        sum(1 for x in rv.get('comments') or [] if x.get('edited_after_viewing_others'))
    if n:
        parts.append(f'その後に直した記録 {n} 件（回答・確認済みの印・コメントの edited_after_viewing_others）')
    if rv.get('submitted') and rv.get('updated') and str(rv['updated']) > str(rv['submitted']):
        parts.append(f'提出（{rv["submitted"]}）の後に更新した（{rv["updated"]}）')
    return '。'.join(parts)


def report_text(data, rv, R, hashes, docs, label=None, version=None):
    """rv: a review of a claims-review/2 record (migrate() a v1 record first)."""
    form = R['report']
    heads = {s['heading'][:2]: s for s in form['sections']}
    stage_name = {s['id']: s['name'] for s in R['stages']}
    qs = R['questions']
    qids = {x['id'] for x in qs}
    ctx = rv.get('context') or {}
    who = rv['reviewer']
    llm = who['kind'] == 'llm'
    lines = [f'# レビューレポート：{md(label or data["design"])}', '',
             '> 設計書のエディターが `review.yaml` から生成した。レビュアーの名前は自己申告で、'
             '本当の承認は GitHub の PR のレビューで行う。' + ('レビュアーは LLM で、人による点検は未実施。' if llm else ''), '']

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
    cand = len(_rejected(docs)) if docs else None
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
    gone = [q for q in ans if q not in qids]
    ci = ctx.get('ci')
    ci_text = ('記録なし' if not ci else
               f'claim_lint error {ci["error"]}・warn {ci["warn"]}・info {ci["info"]}'
               + (f'（profile {ci["profile"]}）' if ci.get('profile') else '')
               + ('' if 'matches_design' not in ci else '。設計書の 1. と' + ('一致' if ci['matches_design'] else '一致しない'))
               + (f'。{ci["note"]}' if ci.get('note') else ''))
    samp = ('記録なし' if not sm else
            f'乱数の種「{sm["seed"]}」（claims.yaml の却下の行' + (f' {cand} 行' if cand is not None else '') + f'から {sm["count"]} 行。'
            'sha256(種:行) の順）：' + '・'.join(_short(a) for a in sm['picked'])
            + f'。{len(scored)} 件を採点、合格 {passed}・不合格 {len(scored) - passed}'
            + (f'（未採点 {len(sm["picked"]) - len(scored)}）' if len(scored) < len(sm['picked']) else '')
            + (f'。引き直した（{sm["reason"]}。前の抜き取り {len(sm.get("previous") or [])} 件）' if sm.get('reason') else ''))
    versions = R.get('versions') or {}
    now_p = R['template_version']
    now_r = versions.get('templates/review/report_template.md')
    mt = rv.get('materials') or {}
    rec_p = mt.get('perspectives') or version
    rec_r = mt.get('report_template')
    mats = ('templates/review（レビューした時の版：perspectives.md ' + (rec_p or '記録なし')
            + (f'、report_template.md {rec_r}' if rec_r else '') + (f'、問い {mt["questions"]} 問' if mt.get('questions') is not None else '') + '）')
    differs = (rec_p and rec_p != now_p) or (rec_r and now_r and rec_r != now_r) or (mt.get('questions') is not None and mt['questions'] != len(qs))
    if differs:
        mats += (f'。注意：今の教材は perspectives.md {now_p}' + (f'・report_template.md {now_r}' if now_r else '') + f'・問い {len(qs)} 問で、'
                 'レビューの後に変わった（この表の問いの数と 8. は今の観点書で数えた）')
    if ctx.get('materials'):
        mats += '。' + ctx['materials']
    reviewer = f'{who["name"]}（' + ('LLM' + (f'：{who["model"]}' if who.get('model') else '') if llm else '人') + \
        '。名前は自己申告）' + (f'。{ctx["roles_order"]}' if ctx.get('roles_order') else '')
    ind = independence_text(data, rv)
    if ind:
        reviewer += '。' + ind
    date = _date(rv['started']) + (f'〜{_date(rv["submitted"])}' if rv.get('submitted') and _date(rv['submitted']) != _date(rv['started']) else '')
    values = {'対象': f'{data["design"]}' + (f'（版 {tgt["commit"]}）' if tgt.get('commit') else '') + (f'。{tgt["note"]}' if tgt.get('note') else ''),
              'Lite／Full': ctx.get('lite_full') or '記録なし', '実施した手順の段': ctx.get('steps') or '記録なし',
              'レビュアーと役割': reviewer, '実施日': date, '使った教材の版': mats, 'CI の結果': ci_text, '抜き取りの結果': samp,
              '問いの回答': f'全 {len(qs)} 問のうち {answered} 問に回答（未回答 {len(qs) - answered}）。' + '。'.join(per)
              + f'。合計 Yes {tot["yes"]}／No {tot["no"]}／該当なし {tot["na"]}'
              + (f'。今の観点書に無い問いへの回答 {len(gone)} 件' if gone else '')}
    head('1.')
    table('1.', [[k, _cell(values.get(k))] for k in heads['1.']['items']])
    # 2. / 3.
    fs = rv.get('comments') or []
    head('2.')
    table('2.', [[_cell(f['id']), _cell(f['location']), _cell(f['content'] + (f'（判定の理由：{f["verdict_reason"]}）' if f.get('verdict_reason') else '')),
                  _cell(f['severity']), _cell(f['origin']), _cell(f['kind']), _cell(f.get('confused_question') if f['kind'] == '目的と仕組みの不一致' else None),
                  _cell(f['verdict'])] for f in fs])
    head('3.')
    table('3.', [[_cell(f['id']), _cell((f.get('response') or {}).get('owner')), _cell((f.get('response') or {}).get('due')),
                  _cell((f.get('response') or {}).get('state') or '未着手'), _cell((f.get('response') or {}).get('ref'))] for f in fs])
    # 4.
    esc = rv.get('escalations') or {}
    head('4.')
    table('4.', [[_cell(e['criterion']), _cell(e['location']), _cell(e.get('to')), _cell(e.get('due')), _cell(e.get('conclusion'))]
                 for e in esc.get('applies') or []])
    na = esc.get('not_applicable')
    lines.append('当てはまらなかった基準：' + ('・'.join(md(x) for x in na) if na else '（記録なし）'))
    lines.append('')
    # 5.
    head('5.')
    table('5.', [[_cell(x['to']), _cell(x['content']), _cell('・'.join(x.get('comments') or [])), _cell(x.get('ref'))]
                 for x in rv.get('feedback') or []])
    # 6.
    head('6.')
    table('6.', [[_cell(_short(a)), 'rationale'] + [_cell(scores[a].get(f'RR{i}') or '対象外') for i in range(1, 8)]
                 + ['合格' if scores[a].get('pass') else '不合格'] for a in scored])
    notes = [f'- {md(_short(a))}：{md(scores[a]["note"])}' for a in scored if scores[a].get('note')]
    if notes:
        lines.extend(notes + [''])
    # 7. (the fixed sentences are not values of review.yaml: nothing in the file can hide them)
    head('7.')
    if ctx.get('human_check'):
        lines.append(md_line(ctx['human_check']))
        lines.append('')
    if llm:
        lines.append('人による点検は未実施（このレビューは LLM のセッションのもの。人のレビュアーの採否は未了）。')
    else:
        lines.append('レビュアーは人（名前は自己申告）。templates/CONTRIBUTING.md の 3. の点検の取り決めによる点検かは、この記録からは分からない。')
    lines.append('')
    lines.append('レビュアーの名前は自己申告です（エディターにはログインが無い）。本当の承認は GitHub の PR のレビューで行います。')
    lines.append('')
    # 8.
    head('8.')
    table('8.', [[_cell(stage_name.get(x['stage'], '—')), x['id'], ANSWER_JA[ans[x['id']]['answer']], _cell(ans[x['id']].get('memo'))]
                 for x in qs if x['id'] in ans])
    left = [x['id'] for x in qs if x['id'] not in ans]
    if left:
        lines.append(f'未回答：{len(left)} 問（' + '・'.join(left) + '）')
        lines.append('')
    if gone:
        lines.append(f'今の観点書に無い問いへの回答：{len(gone)} 件（' + '・'.join(md(q) for q in gone) + '）')
        lines.append('')
    # 9. the viewed marks and the submissions (not in the form; the form allows sections after 8.)
    lines.append('## 9. 確認済みの行と提出の記録')
    lines.append('')
    lines.append('「確認済み」は、レビュアーがその行の内容を見たという印で、承認ではありません。判定（承認／変更を依頼／コメントのみ）は、提出ごとにレビュー全体に 1 つ付けます。'
                 '印と判定は、行の内容のハッシュ（RFC 8785 JCS の SHA-256、`tools/row_hash.py`）に結びつきます。記録の後に行が変わると「前回の確認から変更あり」になり、承認は古い承認になります。'
                 'ハッシュはその行の値だけを見ます（参照するトークン種別・経路の行、25 問の回答、design.md の本文を変えても変わりません）。下の「今の行との対応」は、このレポートを生成した時のクレーム一覧と比べた状態です。')
    lines.append('')
    subs = rv.get('submissions') or []
    old = stale_approval(rv, hashes)
    lines.append(_row(['日時', '判定', '総評', '確認済みの行数', 'コメント数']))
    lines.append(_row(['---'] * 5))
    for k, sb in enumerate(subs):
        v = VERDICT_JA[sb['verdict']] + ('（移行）' if sb.get('migrated') else '')
        if old and k == len(subs) - 1:
            v += f'（古い承認：内容が変更されました。{len(old)} 行）'
        lines.append(_row([_cell(sb['at']), v, _cell(sb.get('summary')), str(len(sb.get('viewed') or {})), str(len(sb.get('comments') or []))]))
    if not subs:
        lines.append('|' + ' |' * 5)
    lines.append('')
    if not subs:
        lines.append('未提出（判定はまだ無い）。')
        lines.append('')
    cs = {k: sum(1 for f in fs if f['state'] == k) for k in ('pending', 'unresolved', 'resolved')}
    lines.append(f'コメントの状態：未提出 {cs["pending"]}・未解決 {cs["unresolved"]}・解決済み {cs["resolved"]}')
    lines.append('')
    viewed = rv.get('viewed') or {}
    st = row_states(rv, hashes)
    lines.append(_row(['行', '確認した日時', '今の行との対応', '移行前の判定とコメント']))
    lines.append(_row(['---'] * 4))
    label_of = {'current': '一致（確認したときのまま）', 'stale': '前回の確認から変更あり', 'missing': '一覧に無い行'}
    for a in sorted(viewed):
        r = viewed[a]
        kind = r.get('reviewer_kind') or who['kind']
        mf = r.get('migrated_from')
        lines.append(_row([_cell(a), _cell(r['at']) + ('（LLM）' if kind == 'llm' else '') + ('（まとめて確認）' if r.get('bulk') else ''), label_of[st[a]] + f'（{r["hash"][:12]}）',
                           (DECISION_JA[mf['decision']] + (f'：{md(mf["comment"])}' if mf.get('comment') else '')) if mf else '—']))
    if not viewed:
        lines.append('|' + ' |' * 4)
    lines.append('')
    lines.append(f'計 {len(viewed)} 行：一致 {sum(1 for v in st.values() if v == "current")}'
                 f'・前回の確認から変更あり {sum(1 for v in st.values() if v == "stale")}・一覧に無い {sum(1 for v in st.values() if v == "missing")}'
                 + (f'（うち、まとめて確認 {n_bulk} 行・1 行ずつ確認 {len(viewed) - n_bulk} 行）' if (n_bulk := sum(1 for r in viewed.values() if r.get('bulk'))) else ''))
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


def is_row_note(n):
    return STALE_NOTE in n or MISSING_NOTE in n or OLD_APPROVAL_NOTE in n


def reseed(data, design, reviewer, reason, seed=None, count=None, when=None):
    """Draw again (the population changed): the old draw is kept in sampling.previous with the reason; the scores of
    the rows that are drawn again are kept."""
    import datetime
    rv = next(r for r in data['reviews'] if r['reviewer']['name'] == reviewer)
    sm = rv.get('sampling')
    if not sm:
        raise ValueError(f'{reviewer}: no sampling to draw again')
    docs = row_hash.load(design)
    hashes = row_hash.row_hashes(design)['hashes']
    when = when or datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    old = {k: sm[k] for k in ('seed', 'count', 'picked', 'population', 'scores') if k in sm}
    old.update({'replaced_at': when, 'reason': reason})
    seed = seed or sm['seed']
    count = count or sm['count']
    picked = sample(seed, count, docs)
    new = {'seed': seed, 'count': count, 'picked': picked, 'population': population(docs, hashes), 'reason': reason,
           'previous': (sm.get('previous') or []) + [old]}
    kept = {a: v for a, v in (sm.get('scores') or {}).items() if a in picked}
    if kept:
        new['scores'] = kept
    rv['sampling'] = new
    return data


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('check')
    c.add_argument('file')
    c.add_argument('--design')
    c.add_argument('--fail-on-stale', action='store_true', help='exit 1 when a viewed mark is of older content or of a row that is gone, or an approval is old')
    c.add_argument('--annotate', action='store_true', help='print the notes as GitHub Actions ::warning annotations too')
    g = sub.add_parser('migrate')
    g.add_argument('file')
    gg = g.add_mutually_exclusive_group()
    gg.add_argument('-o', '--output')
    gg.add_argument('--check', metavar='OUT_YAML', help='exit 1 when OUT_YAML differs from the migration of the file')
    m = sub.add_parser('merge')
    m.add_argument('files', nargs='+')
    m.add_argument('-o', '--output')
    s = sub.add_parser('sample')
    s.add_argument('design')
    s.add_argument('--seed')
    s.add_argument('--count', type=int, choices=(2, 3))
    s.add_argument('--reseed', action='store_true', help='draw again into --file for --reviewer, keeping the old draw and --reason')
    s.add_argument('--file')
    s.add_argument('--reviewer')
    s.add_argument('--reason')
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
        v1 = is_v1(data)
        errs, notes = check(data, a.design)
        with open(a.file, encoding='utf-8') as f:
            raw = f.read().replace('\r\n', '\n')
        if not errs and raw != dump(data, version_of(raw)):
            errs.append('the file is not in the canonical form the editor writes (python tools/review_record.py merge FILE -o FILE rewrites it)')
        if v1:
            print(f'info {a.file} は前の形（{FORMAT_V1}）。{FORMAT} に移行して確かめた（ファイルは変えない）。新しい形にするなら：'
                  f'python tools/review_record.py migrate {a.file} -o <出力>', file=out)
        for e in errs:
            print('error ' + e, file=out)
        for n in notes:
            print(('stale ' if is_row_note(n) else 'warn ') + n, file=out)
            if a.annotate:
                print(f'::warning file={a.file},title=review_record::' + n.replace('%', '%25').replace('\n', '%0A'), file=out)
        rows_n = [n for n in notes if is_row_note(n)]
        ok_schema = isinstance(data, dict) and not schema_errors(data)
        now = migrate(data) if ok_schema else {}
        n_rows = sum(len(rv['viewed']) for rv in now.get('reviews') or [])
        n_subs = sum(len(rv['submissions']) for rv in now.get('reviews') or [])
        fail = bool(errs) or (bool(rows_n) and a.fail_on_stale)
        print(f'review_record check: {len(now.get("reviews") or [])} reviews, {n_rows} viewed marks, {n_subs} submissions, '
              f'{len(rows_n)} need a new look, {len(notes) - len(rows_n)} other warnings' + (f', {len(errs)} errors' if errs else '')
              + ' ->' + (' FAIL' if fail else ' OK'), file=out)
        return 1 if fail else 0
    if a.cmd == 'migrate':
        with open(a.file, encoding='utf-8') as f:
            ver = version_of(f.read())
        data = load(a.file)
        errs = schema_errors(data)
        if errs:
            for e in errs:
                print('error ' + e, file=out)
            return 1
        text = dump(migrate(data), ver)
        if a.check:
            with open(a.check, encoding='utf-8') as f:
                cur = f.read().replace('\r\n', '\n')
            ok = cur == text
            print(f'review_record migrate --check {a.check}: ' + ('OK' if ok else f'FAIL (differs from the migration of {a.file}; '
                  f'run: python tools/review_record.py migrate {a.file} -o {a.check})'), file=out)
            return 0 if ok else 1
        _write(text, a.output)
        return 0
    if a.cmd == 'merge':
        with open(a.files[0], encoding='utf-8') as f:
            ver = version_of(f.read())
        _write(dump(merge([load(p) for p in a.files]), ver), a.output)
        return 0
    if a.cmd == 'sample':
        if a.reseed:
            if not (a.file and a.reviewer and a.reason):
                ap.error('sample --reseed needs --file, --reviewer and --reason')
            with open(a.file, encoding='utf-8') as f:
                ver = version_of(f.read())
            data = reseed(migrate(load(a.file)), a.design, a.reviewer, a.reason, a.seed, a.count)
            _write(dump(data, ver), a.file)
            print('drawn again: ' + ' '.join(next(r for r in data['reviews'] if r['reviewer']['name'] == a.reviewer)['sampling']['picked'])
                  + '（新しい行は採点し直す）', file=out)
            return 0
        if not a.seed:
            ap.error('sample needs --seed')
        for x in sample(a.seed, a.count or 3, row_hash.load(a.design)):
            print(x, file=out)
        return 0
    if a.cmd == 'report':
        with open(a.file, encoding='utf-8') as f:
            ver = version_of(f.read())
        text = report(load(a.file), a.design, review_data(), a.reviewer, a.label, ver)
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
