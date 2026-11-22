# -*- coding: utf-8 -*-
"""Check the slide-to-artifact trace table (issue #22).

  python tools/trace_check.py [--root DIR] [--write-new-items]

Reads templates/trace/requirements.yaml and templates/trace/planned_items.yaml and checks:

(a) every slide ID in deck/slide_ids.json appears exactly once in `classification`, and no other ID does
    (so adding or removing a slide without updating the trace fails);
(b) every design-decision slide has at least one requirement, and requirements sit only on such slides;
(c) every requirement has an id `<slide-id>.R<n>`, a text, an owner_issue, at least one planned item that
    is well-formed and listed in planned_items.yaml, a valid status, and assumption + breaks_when when the
    status is 扱わない; the owner_issue is the issue of at least one of its planned items;
(d) for status 実装済み, every planned item resolves to an existing artifact (see RESOLVERS; kinds without
    a resolver cannot be 実装済み yet);
(e) prints the counts by status, by owner issue and by slide kind, and checks the `summary` block at the
    top of requirements.yaml against them; templates/trace/new_items.md must match what
    --write-new-items generates from the proposed items.

Exit status: 0 if everything holds, 1 otherwise (each problem is printed on its own line).
"""
import argparse, json, os, re, sys
from collections import Counter, OrderedDict

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit('trace_check: PyYAML is required (pip install pyyaml)')

DEFAULT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACE_DIR = os.path.join('templates', 'trace')
REQ_FILE = os.path.join(TRACE_DIR, 'requirements.yaml')
ITEMS_FILE = os.path.join(TRACE_DIR, 'planned_items.yaml')
NEW_ITEMS_FILE = os.path.join(TRACE_DIR, 'new_items.md')
RULES_FILE = os.path.join('tools', 'claim-lint', 'RULES.md')

KINDS = ('design-decision', 'knowledge', 'structural')
STATUSES = ('未着手', '実装済み', '後回し', '扱わない')
DEFERRED_ISSUES = {'#7', '#20', '#21'}
REQ_FIELDS = {'id', 'slide', 'text', 'owner_issue', 'planned_items', 'status', 'assumption', 'breaks_when', 'note'}
ITEM_FIELDS = {'ref', 'issue', 'origin', 'title', 'note'}
ORIGINS = ('issue', 'proposed')

SLIDE_ID = r'p\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*'
SLIDE_REF_RE = re.compile(r'^slide:(' + SLIDE_ID + r')$')
REQ_ID_RE = re.compile(r'^(' + SLIDE_ID + r')\.R([1-9]\d*)$')
ISSUE_RE = re.compile(r'^#[1-9]\d*$')
REF_RE = re.compile(r'^(?P<kind>[a-z]+):(?P<path>[A-Za-z0-9_][A-Za-z0-9_./-]*)(?:#(?P<anchor>[A-Za-z0-9_][A-Za-z0-9_.-]*))?$')
SLUG_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
LINT_ID_RE = re.compile(r'^[LR][1-9]\d*[a-z]?$')

# kind -> (allowed paths or None for any, anchor: 'required' | 'optional' | 'forbidden', path must be a slug)
GRAMMAR = {
    'registry': ({'claims', 'token_types', 'hops', 'questions', 'README'}, 'optional', False),
    'template': (None, 'optional', False),
    'review': (None, 'optional', False),
    'lint': (None, 'forbidden', False),
    'catalog': ({'issue_events', 'use_events', 'subject_state_matrix', 'sources', 'token_kinds'}, 'optional', False),
    'test': ({'negative_tests', 'consumer_contract'}, 'optional', False),
    'ci': (None, 'optional', True),
    'render': (None, 'forbidden', True),
    'calib': (None, 'optional', True),
    'guide': (None, 'forbidden', True),
    'deferred': (None, 'forbidden', True),
    'none': ({'out-of-scope'}, 'forbidden', True),
}


def parse_ref(ref):
    """Return (kind, path, anchor) or raise ValueError with the reason."""
    if not isinstance(ref, str):
        raise ValueError('not a string')
    m = REF_RE.match(ref)
    if not m:
        raise ValueError('want kind:path[#anchor]')
    kind, path, anchor = m.group('kind'), m.group('path'), m.group('anchor')
    if kind not in GRAMMAR:
        raise ValueError(f'unknown kind {kind!r} (known: {", ".join(sorted(GRAMMAR))})')
    paths, anchor_rule, slug = GRAMMAR[kind]
    if paths is not None and path not in paths:
        raise ValueError(f'{kind}: path must be one of {", ".join(sorted(paths))}')
    if slug and not SLUG_RE.match(path):
        raise ValueError(f'{kind}: path must be lowercase kebab-case')
    if '..' in path.split('/') or path.startswith('/'):
        raise ValueError('path must stay inside its directory')
    if anchor_rule == 'forbidden' and anchor:
        raise ValueError(f'{kind}: no #anchor allowed')
    if kind == 'lint' and not LINT_ID_RE.match(path):
        raise ValueError('lint: want a rule ID such as L5, L1a or R3b')
    if kind == 'registry' and path in ('claims', 'token_types', 'hops', 'questions') and not anchor:
        raise ValueError(f'registry:{path} needs #<column or question id>')
    return kind, path, anchor


# ------------------------------------------------------------------ resolvers (status 実装済み)
MD_ANCHOR_RE = re.compile(r'(?:\bid|\bname)="([^"]+)"|\{#([A-Za-z0-9_.-]+)\}')


def _read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def _md_has(root, rel, anchor):
    path = os.path.join(root, rel)
    if not os.path.isfile(path):
        return f'{rel} does not exist'
    if anchor is None:
        return None
    found = {a or b for a, b in MD_ANCHOR_RE.findall(_read(path))}
    return None if anchor in found else f'{rel} has no anchor <a id="{anchor}"></a>'


def _json_props(node, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == 'properties' and isinstance(v, dict):
                out.update(v.keys())
            _json_props(v, out)
    elif isinstance(node, list):
        for v in node:
            _json_props(v, out)
    return out


def _yaml_has(node, anchor):
    """True if `anchor` is a mapping key or the value of an `id` key anywhere in the YAML tree."""
    if isinstance(node, dict):
        if anchor in node or node.get('id') == anchor:
            return True
        return any(_yaml_has(v, anchor) for v in node.values())
    if isinstance(node, list):
        return any(_yaml_has(v, anchor) for v in node)
    return False


def resolve_registry(root, path, anchor):
    base = os.path.join('templates', 'registry')
    if path == 'README':
        return _md_has(root, os.path.join(base, 'README.md'), anchor)
    if path == 'questions':
        rel = os.path.join(base, 'questions.yaml')
        if not os.path.isfile(os.path.join(root, rel)):
            return f'{rel} does not exist'
        data = yaml.safe_load(_read(os.path.join(root, rel)))
        return None if _yaml_has(data, anchor) else f'{rel} has no question id {anchor}'
    rel = os.path.join(base, f'{path}.schema.json')
    if not os.path.isfile(os.path.join(root, rel)):
        return f'{rel} does not exist'
    props = _json_props(json.loads(_read(os.path.join(root, rel))), set())
    return None if anchor in props else f'{rel} has no property {anchor}'


def resolve_lint(root, path, anchor):
    rel = RULES_FILE
    if not os.path.isfile(os.path.join(root, rel)):
        return f'{rel} does not exist'
    pat = re.compile(r'^(?:\|\s*`?' + re.escape(path) + r'`?\s*\||#{1,6}\s+`?' + re.escape(path) + r'\b)', re.M)
    return None if pat.search(_read(os.path.join(root, rel))) else f'{rel} has no rule {path} (table row or heading)'


def resolve_catalog(root, path, anchor):
    base = os.path.join('templates', 'catalog')
    for ext in ('.yaml', '.yml'):
        rel = os.path.join(base, path + ext)
        if os.path.isfile(os.path.join(root, rel)):
            if anchor is None:
                return None
            data = yaml.safe_load(_read(os.path.join(root, rel)))
            return None if _yaml_has(data, anchor) else f'{rel} has no key or id {anchor}'
    return _md_has(root, os.path.join(base, path + '.md'), anchor)


def resolve_ci(root, path, anchor):
    for ext in ('.yml', '.yaml'):
        rel = os.path.join('.github', 'workflows', path + ext)
        if os.path.isfile(os.path.join(root, rel)):
            if anchor is None:
                return None
            jobs = (yaml.safe_load(_read(os.path.join(root, rel))) or {}).get('jobs') or {}
            return None if anchor in jobs else f'{rel} has no job {anchor}'
    return f'.github/workflows/{path}.yml does not exist'


RESOLVERS = {
    'registry': resolve_registry,
    'template': lambda root, p, a: _md_has(root, os.path.join('templates', p + '.md'), a),
    'review': lambda root, p, a: _md_has(root, os.path.join('templates', 'review', p + '.md'), a),
    'lint': resolve_lint,
    'catalog': resolve_catalog,
    'test': lambda root, p, a: _md_has(root, os.path.join('templates', 'runtime', p + '.md'), a),
    'ci': resolve_ci,
    # render, calib, guide: not built yet -> add a resolver here when the artifact exists.
    # deferred, none: never 実装済み.
}


# ------------------------------------------------------------------ loading
def load_yaml(root, rel, errors):
    path = os.path.join(root, rel)
    if not os.path.isfile(path):
        errors.append(f'{rel}: missing')
        return None
    try:
        return yaml.safe_load(_read(path))
    except yaml.YAMLError as e:
        errors.append(f'{rel}: YAML error: {e}')
        return None


def load_slide_ids(root, errors):
    rel = os.path.join('deck', 'slide_ids.json')
    path = os.path.join(root, rel)
    if not os.path.isfile(path):
        errors.append(f'{rel}: missing')
        return []
    return [x.get('id') for x in json.loads(_read(path))]


def check_items(data, errors):
    items = OrderedDict()
    if not isinstance(data, dict) or not isinstance(data.get('items'), list):
        errors.append(f'{ITEMS_FILE}: want a mapping with an `items` list')
        return items
    for k, it in enumerate(data['items'], 1):
        where = f'{ITEMS_FILE}: item {k}'
        if not isinstance(it, dict):
            errors.append(f'{where}: not a mapping'); continue
        ref = it.get('ref')
        where = f'{ITEMS_FILE}: {ref}'
        for f in sorted(set(it) - ITEM_FIELDS):
            errors.append(f'{where}: unknown field {f!r}')
        try:
            parse_ref(ref)
        except ValueError as e:
            errors.append(f'{where}: malformed ref ({e})'); continue
        if ref in items:
            errors.append(f'{where}: listed twice'); continue
        if not ISSUE_RE.match(str(it.get('issue', ''))):
            errors.append(f'{where}: issue must look like "#3"')
        if it.get('origin') not in ORIGINS:
            errors.append(f'{where}: origin must be one of {ORIGINS}')
        if not str(it.get('title') or '').strip():
            errors.append(f'{where}: title is empty')
        items[ref] = it
    return items


def check(root):
    """Return (errors, report_lines, context)."""
    errors, report = [], []
    slide_ids = load_slide_ids(root, errors)
    items_data = load_yaml(root, ITEMS_FILE, errors)
    req_data = load_yaml(root, REQ_FILE, errors)
    if items_data is None or req_data is None or not slide_ids:
        return errors, report, None
    items = check_items(items_data, errors)
    if not isinstance(req_data, dict):
        errors.append(f'{REQ_FILE}: want a mapping')
        return errors, report, None

    # (a) classification
    kind_of = {}
    for k, row in enumerate(req_data.get('classification') or [], 1):
        where = f'{REQ_FILE}: classification row {k}'
        if not isinstance(row, dict):
            errors.append(f'{where}: not a mapping'); continue
        m = SLIDE_REF_RE.match(str(row.get('slide', '')))
        if not m:
            errors.append(f'{where}: slide must be slide:<id>, got {row.get("slide")!r}'); continue
        sid = m.group(1)
        if row.get('kind') not in KINDS:
            errors.append(f'{where} ({sid}): kind must be one of {KINDS}')
        if sid in kind_of:
            errors.append(f'{where}: slide:{sid} classified more than once')
            continue
        kind_of[sid] = row.get('kind')
    known = set(slide_ids)
    for sid in slide_ids:
        if sid not in kind_of:
            errors.append(f'{REQ_FILE}: slide:{sid} (slide {slide_ids.index(sid) + 1}) is not classified')
    for sid in kind_of:
        if sid not in known:
            errors.append(f'{REQ_FILE}: classification has unknown slide:{sid} (not in deck/slide_ids.json)')

    # (c) requirements
    reqs = req_data.get('requirements') or []
    seen, per_slide, by_status, by_owner, used = set(), Counter(), Counter(), Counter(), Counter()
    for k, r in enumerate(reqs, 1):
        if not isinstance(r, dict):
            errors.append(f'{REQ_FILE}: requirement {k}: not a mapping'); continue
        rid = r.get('id')
        where = f'{REQ_FILE}: {rid or f"requirement {k}"}'
        for f in sorted(set(r) - REQ_FIELDS):
            errors.append(f'{where}: unknown field {f!r}')
        m = REQ_ID_RE.match(str(rid or ''))
        if not m:
            errors.append(f'{where}: id must be <slide-id>.R<n>'); continue
        if rid in seen:
            errors.append(f'{where}: duplicate id')
        seen.add(rid)
        sm = SLIDE_REF_RE.match(str(r.get('slide', '')))
        if not sm or sm.group(1) != m.group(1):
            errors.append(f'{where}: slide must be slide:{m.group(1)}')
        sid = m.group(1)
        if sid not in known:
            errors.append(f'{where}: unknown slide {sid}')
        elif kind_of.get(sid) != 'design-decision':
            errors.append(f'{where}: slide {sid} is classified {kind_of.get(sid)}, not design-decision')
        per_slide[sid] += 1
        if not str(r.get('text') or '').strip():
            errors.append(f'{where}: text is empty')
        owner = str(r.get('owner_issue') or '')
        if not ISSUE_RE.match(owner):
            errors.append(f'{where}: owner_issue must look like "#3"')
        status = r.get('status')
        if status not in STATUSES:
            errors.append(f'{where}: status must be one of {"／".join(STATUSES)}')
        pis = r.get('planned_items')
        if not isinstance(pis, list) or not pis:
            errors.append(f'{where}: needs at least one planned item'); pis = []
        issues_of_items, kinds = set(), set()
        for ref in pis:
            try:
                kind, path, anchor = parse_ref(ref)
            except ValueError as e:
                errors.append(f'{where}: malformed planned item {ref!r} ({e})'); continue
            kinds.add(kind)
            if ref not in items:
                errors.append(f'{where}: planned item {ref} is not in {ITEMS_FILE}'); continue
            used[ref] += 1
            issues_of_items.add(items[ref].get('issue'))
            if status == '実装済み':
                resolver = RESOLVERS.get(kind)
                problem = resolver(root, path, anchor) if resolver else f'kind {kind} has no artifact to resolve yet'
                if problem:
                    errors.append(f'{where}: 実装済み but {ref} does not resolve: {problem}')
        if owner and issues_of_items and owner not in issues_of_items:
            errors.append(f'{where}: owner_issue {owner} is not the issue of any planned item ({", ".join(sorted(issues_of_items))})')
        if status == '扱わない':
            for f in ('assumption', 'breaks_when'):
                if not str(r.get(f) or '').strip():
                    errors.append(f'{where}: 扱わない needs {f}')
        elif 'none' in kinds:
            errors.append(f'{where}: none:out-of-scope is only for status 扱わない')
        if status == '後回し' and owner not in DEFERRED_ISSUES:
            errors.append(f'{where}: 後回し needs owner_issue in {sorted(DEFERRED_ISSUES)}')
        if owner in DEFERRED_ISSUES and status not in ('後回し', '扱わない'):
            errors.append(f'{where}: owner {owner} is a deferred issue; status must be 後回し')
        by_status[status] += 1
        by_owner[owner] += 1

    # (b) every design-decision slide has a requirement
    for sid in slide_ids:
        if kind_of.get(sid) == 'design-decision' and per_slide[sid] == 0:
            errors.append(f'{REQ_FILE}: design-decision slide:{sid} has no requirement')

    # teaching material
    for k, t in enumerate(req_data.get('teaching') or [], 1):
        where = f'{REQ_FILE}: teaching row {k}'
        sm = SLIDE_REF_RE.match(str((t or {}).get('slide', '')))
        if not sm:
            errors.append(f'{where}: slide must be slide:<id>'); continue
        sid = sm.group(1)
        if kind_of.get(sid) != 'knowledge':
            errors.append(f'{where}: slide:{sid} is not classified knowledge')
        uses = t.get('use')
        if not isinstance(uses, list) or not uses:
            errors.append(f'{where}: needs at least one `use` item')
            continue
        for ref in uses:
            try:
                parse_ref(ref)
            except ValueError as e:
                errors.append(f'{where}: malformed item {ref!r} ({e})'); continue
            if ref not in items:
                errors.append(f'{where}: {ref} is not in {ITEMS_FILE}')
            else:
                used[ref] += 1

    # (e) counts and the summary block
    kinds_count = Counter(kind_of.values())
    total = sum(by_status.values())
    report.append(f'slides: {len(slide_ids)} (' + ', '.join(f'{k} {kinds_count[k]}' for k in KINDS) + ')')
    report.append(f'requirements: {total} on {sum(1 for s in per_slide if per_slide[s])} slides')
    report.append('by status: ' + ', '.join(f'{s} {by_status[s]}' for s in STATUSES))
    out = by_status['扱わない']
    report.append(f'扱わない: {out} / {total} ({(100.0 * out / total) if total else 0:.1f}%)')
    report.append('by owner issue: ' + ', '.join(f'{o} {n}' for o, n in sorted(by_owner.items(), key=lambda x: int(x[0][1:]) if ISSUE_RE.match(x[0]) else 0)))
    proposed = [r for r, it in items.items() if it.get('origin') == 'proposed']
    report.append(f'planned items: {len(items)} ({len(items) - len(proposed)} from issue bodies, {len(proposed)} proposed); unused {sum(1 for r in items if not used[r])}')
    unused_proposed = [r for r in proposed if not used[r]]
    for r in unused_proposed:
        errors.append(f'{ITEMS_FILE}: proposed item {r} is used by no requirement or teaching row')

    summary = req_data.get('summary')
    want = OrderedDict([('design_decision_slides', kinds_count['design-decision']),
                        ('knowledge_slides', kinds_count['knowledge']),
                        ('structural_slides', kinds_count['structural']),
                        ('requirements', total)] + [(s, by_status[s]) for s in STATUSES])
    if not isinstance(summary, dict) or any(summary.get(k) != v for k, v in want.items()):
        errors.append(f'{REQ_FILE}: summary block is stale; want ' + json.dumps(want, ensure_ascii=False))

    ctx = {'items': items, 'reqs': reqs, 'teaching': req_data.get('teaching') or [], 'slide_ids': slide_ids}
    return errors, report, ctx


def render_new_items(ctx):
    """Markdown list of the proposed planned items, grouped by issue."""
    slides_of = {}
    for r in ctx['reqs']:
        if not isinstance(r, dict):
            continue
        for ref in r.get('planned_items') or []:
            slides_of.setdefault(ref, []).append(str(r.get('id')))
    for t in ctx['teaching']:
        for ref in (t or {}).get('use') or []:
            slides_of.setdefault(ref, []).append(str(t.get('slide', '')).replace('slide:', '') + '（教材）')
    by_issue = OrderedDict()
    for ref, it in ctx['items'].items():
        if it.get('origin') == 'proposed':
            by_issue.setdefault(it.get('issue'), []).append((ref, it))
    lines = ['<!-- template_version: 0.1.0 -->',
             '<!-- 生成物。手で書き換えない。python tools/trace_check.py --write-new-items で作り直す -->',
             '# 対応表で足した成果物の提案（#22）', '',
             '対応表（`requirements.yaml`）を作るときに、どの issue の本文にもない成果物が必要になったものの一覧です。'
             '各 issue の本文に書き足すかどうかは、担当の issue で決めます。書き足さない場合は、'
             '`planned_items.yaml` の項目を別の成果物に付け替えるか、要件を「扱わない」にします。', '',
             f'提案の件数：{sum(len(v) for v in by_issue.values())} 件', '']
    for issue in sorted(by_issue, key=lambda s: int(s[1:])):
        rows = by_issue[issue]
        lines += [f'## {issue}（{len(rows)} 件）', '', '| 成果物 | 内容 | 使う要件 |', '| --- | --- | --- |']
        for ref, it in rows:
            uses = ', '.join(f'`{u}`' for u in slides_of.get(ref, []))
            title = str(it.get('title', '')).replace('|', '\\|')
            lines.append(f'| `{ref}` | {title} | {uses} |')
        lines.append('')
    return '\n'.join(lines).rstrip('\n')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--root', default=DEFAULT_ROOT, help='repository root (default: this checkout)')
    ap.add_argument('--write-new-items', action='store_true', help=f'regenerate {NEW_ITEMS_FILE} and exit')
    a = ap.parse_args(argv)
    errors, report, ctx = check(a.root)
    if ctx is not None:
        text = render_new_items(ctx)
        path = os.path.join(a.root, NEW_ITEMS_FILE)
        if a.write_new_items:
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(text + '\n')
            print(f'wrote {NEW_ITEMS_FILE}')
        elif not os.path.isfile(path) or _read(path).rstrip('\n') != text:
            errors.append(f'{NEW_ITEMS_FILE}: stale; run python tools/trace_check.py --write-new-items')
    for line in report:
        print(line)
    for e in errors:
        print('ERROR', e)
    print('FAIL' if errors else 'OK')
    return 1 if errors else 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
