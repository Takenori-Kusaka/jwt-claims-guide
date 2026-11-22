# -*- coding: utf-8 -*-
"""Check the slide-to-artifact trace table (issue #22).

  python tools/trace_check.py [--root DIR] [--tier core|full] [--require-done]
  python tools/trace_check.py --write-new-items
  python tools/trace_check.py --update-hash SLIDE_ID [SLIDE_ID ...] --reviewed-on YYYY-MM-DD

Reads templates/trace/requirements.yaml and templates/trace/planned_items.yaml (duplicate YAML keys are
an error) and checks:

(a) every slide ID in deck/slide_ids.json appears exactly once in `classification`, and no other ID does;
    each row carries `sha` (first 12 hex digits of sha256 over title, text and notes in docs/slides.json)
    and `reviewed_on`. A slide whose content changed fails until its requirements are re-read and the row
    is updated with --update-hash (which also sets reviewed_on);
(b) every design-decision slide has at least one requirement, and requirements sit only on such slides;
    every knowledge slide has exactly one `teaching` row;
(c) every requirement has an id `<slide-id>.R<n>`, a text, an owner_issue, a tier (core / full), at least
    one planned item that is well-formed and listed in planned_items.yaml, and a valid status; the owner is
    the issue of one of its planned items. 後回し: owner #7 / #20 / #21 and tier full. 扱わない: planned
    items exactly [none:out-of-scope], owner #22, tier full, and assumption + breaks_when of at least
    MIN_REASON characters that differ from the text and from each other (their substance is checked by
    review, not here);
(d) for status 実装済み, every planned item resolves to an existing artifact (see RESOLVERS), template /
    review / test items name an anchor, and the resolved part of the artifact contains the marker
    `req:<requirement id>` (a reverse reference). Kinds without a resolver cannot be 実装済み yet;
(e) prints counts by status, tier x status, owner issue and slide kind, checks the `summary` block, and
    checks that templates/trace/new_items.md matches what --write-new-items generates.

--tier restricts the counts to one tier; --require-done also fails when a requirement of that tier (or of
any tier) is still 未着手 (the "未着手 0 件" condition of #11).
Exit status: 0 if everything holds, 1 otherwise (each problem is printed on its own line).
"""
import argparse, datetime, hashlib, json, os, re, sys
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
RULES_FILE = os.path.join('tools', 'claim_lint', 'RULES.md')  # #16: a Python package, so _ not -
SLIDES_FILE = os.path.join('docs', 'slides.json')

KINDS = ('design-decision', 'knowledge', 'structural')
STATUSES = ('未着手', '実装済み', '後回し', '扱わない')
TIERS = ('core', 'full')
DEFERRED_ISSUES = {'#7', '#20', '#21'}
OUT_OF_SCOPE_OWNER = '#22'
OUT_OF_SCOPE_ITEM = 'none:out-of-scope'
MIN_REASON = 20
REQ_FIELDS = {'id', 'slide', 'text', 'owner_issue', 'planned_items', 'status', 'tier', 'assumption', 'breaks_when', 'note'}
CLS_FIELDS = {'slide', 'kind', 'sha', 'reviewed_on'}
TEACH_FIELDS = {'slide', 'use', 'note'}
ITEM_FIELDS = {'ref', 'issue', 'origin', 'title', 'note'}
ORIGINS = ('issue', 'proposed')

SLIDE_ID = r'p\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*'
SLIDE_REF_RE = re.compile(r'^slide:(' + SLIDE_ID + r')$')
REQ_ID_RE = re.compile(r'^(' + SLIDE_ID + r')\.R([1-9]\d*)$')
ISSUE_RE = re.compile(r'^#[1-9]\d*$')
SHA_RE = re.compile(r'^[0-9a-f]{12}$')
REF_RE = re.compile(r'^(?P<kind>[a-z]+):(?P<path>[A-Za-z0-9_][A-Za-z0-9_./-]*)(?:#(?P<anchor>[A-Za-z0-9_][A-Za-z0-9_.-]*))?$')
SLUG_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
LINT_ID_RE = re.compile(r'^[LR][1-9]\d*[a-z]?$')

# kind -> (allowed paths or None for any, anchor: 'optional' | 'forbidden', path must be a slug)
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
ANCHOR_REQUIRED_WHEN_DONE = {'template', 'review', 'test'}


# ------------------------------------------------------------------ YAML without silent duplicates
class UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    seen = {}
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                'while constructing a mapping', node.start_mark,
                f'duplicate key {key!r} (first at line {seen[key] + 1})', key_node.start_mark)
        seen[key] = key_node.start_mark.line
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def yaml_load(text):
    return yaml.load(text, Loader=UniqueKeyLoader)


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


def slide_sha(slide):
    """First 12 hex digits of sha256 over a docs/slides.json entry's title, text and notes."""
    blob = '\n'.join(str(slide.get(k) or '') for k in ('title', 'text', 'notes'))
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()[:12]


# ------------------------------------------------------------------ resolvers (status 実装済み)
# Each resolver returns (problem, scope): problem is None when the artifact exists; scope is the text of
# the resolved part (anchor section, schema property, rule row ...) in which `req:<id>` must appear.
MD_ANCHOR_RE = re.compile(r'(?:\bid|\bname)="([^"]+)"|\{#([A-Za-z0-9_.-]+)\}')


def _read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def _md_part(root, rel, anchor):
    path = os.path.join(root, rel)
    if not os.path.isfile(path):
        return f'{rel} does not exist', None
    text = _read(path)
    if anchor is None:
        return None, text
    marks = list(MD_ANCHOR_RE.finditer(text))
    for k, m in enumerate(marks):
        if (m.group(1) or m.group(2)) == anchor:
            end = marks[k + 1].start() if k + 1 < len(marks) else len(text)
            return None, text[m.start():end]
    return f'{rel} has no anchor <a id="{anchor}"></a>', None


def _json_props(node, name, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == 'properties' and isinstance(v, dict) and name in v:
                out.append(v[name])
            _json_props(v, name, out)
    elif isinstance(node, list):
        for v in node:
            _json_props(v, name, out)
    return out


def _yaml_nodes(node, anchor, out):
    """Subtrees whose key is `anchor`, or mappings whose `id` is `anchor`."""
    if isinstance(node, dict):
        if node.get('id') == anchor:
            out.append(node)
        for k, v in node.items():
            if k == anchor:
                out.append(v)
            _yaml_nodes(v, anchor, out)
    elif isinstance(node, list):
        for v in node:
            _yaml_nodes(v, anchor, out)
    return out


def _dump(nodes):
    return json.dumps(nodes, ensure_ascii=False, default=str)


def resolve_registry(root, path, anchor):
    base = os.path.join('templates', 'registry')
    if path == 'README':
        return _md_part(root, os.path.join(base, 'README.md'), anchor)
    if path == 'questions':
        rel = os.path.join(base, 'questions.yaml')
        if not os.path.isfile(os.path.join(root, rel)):
            return f'{rel} does not exist', None
        found = _yaml_nodes(yaml_load(_read(os.path.join(root, rel))), anchor, [])
        return (None, _dump(found)) if found else (f'{rel} has no question id {anchor}', None)
    rel = os.path.join(base, f'{path}.schema.json')
    if not os.path.isfile(os.path.join(root, rel)):
        return f'{rel} does not exist', None
    found = _json_props(json.loads(_read(os.path.join(root, rel))), anchor, [])
    return (None, _dump(found)) if found else (f'{rel} has no property {anchor}', None)


def resolve_lint(root, path, anchor):
    rel = RULES_FILE
    if not os.path.isfile(os.path.join(root, rel)):
        return f'{rel} does not exist', None
    lines = _read(os.path.join(root, rel)).splitlines()
    rule_re = re.compile(r'^(?:\|\s*`?([LR][1-9]\d*[a-z]?)`?\s*\||#{1,6}\s+`?([LR][1-9]\d*[a-z]?)\b)')
    starts = [(k, m.group(1) or m.group(2)) for k, l in enumerate(lines) for m in [rule_re.match(l)] if m]
    for j, (k, rid) in enumerate(starts):
        if rid == path:
            end = starts[j + 1][0] if j + 1 < len(starts) else len(lines)
            return None, '\n'.join(lines[k:end])
    return f'{rel} has no rule {path} (table row or heading)', None


def resolve_catalog(root, path, anchor):
    base = os.path.join('templates', 'catalog')
    for ext in ('.yaml', '.yml'):
        rel = os.path.join(base, path + ext)
        if os.path.isfile(os.path.join(root, rel)):
            text = _read(os.path.join(root, rel))
            if anchor is None:
                return None, text
            found = _yaml_nodes(yaml_load(text), anchor, [])
            return (None, _dump(found)) if found else (f'{rel} has no key or id {anchor}', None)
    return _md_part(root, os.path.join(base, path + '.md'), anchor)


def resolve_ci(root, path, anchor):
    for ext in ('.yml', '.yaml'):
        rel = os.path.join('.github', 'workflows', path + ext)
        if os.path.isfile(os.path.join(root, rel)):
            text = _read(os.path.join(root, rel))
            if anchor is None:
                return None, text
            jobs = (yaml_load(text) or {}).get('jobs') or {}
            if anchor not in jobs:
                return f'{rel} has no job {anchor}', None
            # the marker is a comment, so search the raw text of the job block
            m = re.search(r'(?m)^  ' + re.escape(anchor) + r':\s*$', text)
            nxt = re.search(r'(?m)^  [A-Za-z0-9_-]+:\s*$', text[m.end():]) if m else None
            return None, text[m.start(): m.end() + nxt.start()] if (m and nxt) else (text[m.start():] if m else text)
    return f'.github/workflows/{path}.yml does not exist', None


RESOLVERS = {
    'registry': resolve_registry,
    'template': lambda root, p, a: _md_part(root, os.path.join('templates', p + '.md'), a),
    'review': lambda root, p, a: _md_part(root, os.path.join('templates', 'review', p + '.md'), a),
    'lint': resolve_lint,
    'catalog': resolve_catalog,
    'test': lambda root, p, a: _md_part(root, os.path.join('templates', 'runtime', p + '.md'), a),
    'ci': resolve_ci,
    # render, calib, guide: not built yet -> add a resolver here when the artifact exists.
    # deferred, none: never 実装済み.
}


def marker_re(req_id):
    return re.compile(r'(?<![\w.-])req:' + re.escape(req_id) + r'(?![0-9A-Za-z_-])')


# ------------------------------------------------------------------ loading
def load_yaml(root, rel, errors):
    path = os.path.join(root, rel)
    if not os.path.isfile(path):
        errors.append(f'{rel}: missing')
        return None
    try:
        return yaml_load(_read(path))
    except yaml.YAMLError as e:
        errors.append(f'{rel}: YAML error: {e}')
        return None


def load_json(root, rel, errors):
    path = os.path.join(root, rel)
    if not os.path.isfile(path):
        errors.append(f'{rel}: missing')
        return None
    return json.loads(_read(path))


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


def _valid_date(v):
    if isinstance(v, datetime.date):
        return True
    try:
        datetime.date.fromisoformat(str(v))
        return True
    except ValueError:
        return False


def check(root, tier_filter=None, require_done=False):
    """Return (errors, report_lines, context)."""
    errors, report = [], []
    deck = load_json(root, os.path.join('deck', 'slide_ids.json'), errors) or []
    slide_ids = [x.get('id') for x in deck]
    web = load_json(root, SLIDES_FILE, errors) or []
    content = {s.get('id'): s for s in web}
    items_data = load_yaml(root, ITEMS_FILE, errors)
    req_data = load_yaml(root, REQ_FILE, errors)
    if items_data is None or req_data is None or not slide_ids:
        return errors, report, None
    items = check_items(items_data, errors)
    if not isinstance(req_data, dict):
        errors.append(f'{REQ_FILE}: want a mapping')
        return errors, report, None

    # (a) classification and content hashes
    kind_of = {}
    for k, row in enumerate(req_data.get('classification') or [], 1):
        where = f'{REQ_FILE}: classification row {k}'
        if not isinstance(row, dict):
            errors.append(f'{where}: not a mapping'); continue
        m = SLIDE_REF_RE.match(str(row.get('slide', '')))
        if not m:
            errors.append(f'{where}: slide must be slide:<id>, got {row.get("slide")!r}'); continue
        sid = m.group(1)
        where = f'{REQ_FILE}: slide:{sid}'
        for f in sorted(set(row) - CLS_FIELDS):
            errors.append(f'{where}: unknown field {f!r}')
        if row.get('kind') not in KINDS:
            errors.append(f'{where}: kind must be one of {KINDS}')
        if sid in kind_of:
            errors.append(f'{where}: classified more than once')
            continue
        kind_of[sid] = row.get('kind')
        if not _valid_date(row.get('reviewed_on')):
            errors.append(f'{where}: reviewed_on must be a date YYYY-MM-DD')
        sha = str(row.get('sha') or '')
        if not SHA_RE.match(sha):
            errors.append(f'{where}: sha must be 12 lowercase hex digits')
        elif sid in content and slide_sha(content[sid]) != sha:
            errors.append(f'{where}: slide content changed since it was reviewed on {row.get("reviewed_on")} '
                          f'(sha {sha}, now {slide_sha(content[sid])}); re-read its requirements, then run '
                          f'python tools/trace_check.py --update-hash {sid} --reviewed-on YYYY-MM-DD')
    known = set(slide_ids)
    for sid in slide_ids:
        if sid not in kind_of:
            errors.append(f'{REQ_FILE}: slide:{sid} (slide {slide_ids.index(sid) + 1}) is not classified')
        if web and sid not in content:
            errors.append(f'{SLIDES_FILE}: slide {sid} is missing (rerun python tools/build_web_slides.py)')
    for sid in kind_of:
        if sid not in known:
            errors.append(f'{REQ_FILE}: classification has unknown slide:{sid} (not in deck/slide_ids.json)')

    # (c) requirements
    reqs = req_data.get('requirements') or []
    seen, per_slide, used = set(), Counter(), Counter()
    by_status, by_owner, by_tier = Counter(), Counter(), Counter()
    todo_in_scope = []
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
        text = str(r.get('text') or '').strip()
        if not text:
            errors.append(f'{where}: text is empty')
        owner = str(r.get('owner_issue') or '')
        if not ISSUE_RE.match(owner):
            errors.append(f'{where}: owner_issue must look like "#3"')
        status, tier = r.get('status'), r.get('tier')
        if status not in STATUSES:
            errors.append(f'{where}: status must be one of {"／".join(STATUSES)}')
        if tier not in TIERS:
            errors.append(f'{where}: tier must be one of {"／".join(TIERS)}')
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
                if not resolver:
                    errors.append(f'{where}: 実装済み but {ref}: kind {kind} has no artifact to resolve yet'); continue
                if kind in ANCHOR_REQUIRED_WHEN_DONE and not anchor:
                    errors.append(f'{where}: 実装済み but {ref} names no #anchor (needed to find req:{rid})'); continue
                problem, scope = resolver(root, path, anchor)
                if problem:
                    errors.append(f'{where}: 実装済み but {ref} does not resolve: {problem}')
                elif not marker_re(rid).search(scope or ''):
                    errors.append(f'{where}: 実装済み but {ref} does not contain the reverse reference req:{rid}')
        if owner and issues_of_items and owner not in issues_of_items:
            errors.append(f'{where}: owner_issue {owner} is not the issue of any planned item ({", ".join(sorted(issues_of_items))})')
        if status == '扱わない':
            if pis != [OUT_OF_SCOPE_ITEM]:
                errors.append(f'{where}: 扱わない needs planned_items exactly [{OUT_OF_SCOPE_ITEM}]')
            if owner != OUT_OF_SCOPE_OWNER:
                errors.append(f'{where}: 扱わない needs owner_issue {OUT_OF_SCOPE_OWNER}')
            reasons = {}
            for f in ('assumption', 'breaks_when'):
                v = str(r.get(f) or '').strip()
                reasons[f] = v
                if not v:
                    errors.append(f'{where}: 扱わない needs {f}')
                elif len(v) < MIN_REASON:
                    errors.append(f'{where}: {f} is shorter than {MIN_REASON} characters')
                elif v == text:
                    errors.append(f'{where}: {f} repeats the text')
            if reasons['assumption'] and reasons['assumption'] == reasons['breaks_when']:
                errors.append(f'{where}: assumption and breaks_when are identical')
        else:
            if 'none' in kinds:
                errors.append(f'{where}: {OUT_OF_SCOPE_ITEM} is only for status 扱わない')
            for f in ('assumption', 'breaks_when'):
                if r.get(f):
                    errors.append(f'{where}: {f} is only for status 扱わない')
        if status == '後回し' and owner not in DEFERRED_ISSUES:
            errors.append(f'{where}: 後回し needs owner_issue in {sorted(DEFERRED_ISSUES)}')
        if owner in DEFERRED_ISSUES and status != '後回し':
            errors.append(f'{where}: owner {owner} is a deferred issue; status must be 後回し')
        if status in ('後回し', '扱わない') and tier != 'full':
            errors.append(f'{where}: status {status} needs tier full')
        if tier_filter is None or tier == tier_filter:
            by_status[status] += 1
            by_owner[owner] += 1
            if status == '未着手':
                todo_in_scope.append(rid)
        by_tier[(tier, status)] += 1

    # (b) every design-decision slide has a requirement
    for sid in slide_ids:
        if kind_of.get(sid) == 'design-decision' and per_slide[sid] == 0:
            errors.append(f'{REQ_FILE}: design-decision slide:{sid} has no requirement')

    # teaching material: on knowledge (every one, once) or design-decision slides
    taught = Counter()
    for k, t in enumerate(req_data.get('teaching') or [], 1):
        where = f'{REQ_FILE}: teaching row {k}'
        if not isinstance(t, dict):
            errors.append(f'{where}: not a mapping'); continue
        for f in sorted(set(t) - TEACH_FIELDS):
            errors.append(f'{where}: unknown field {f!r}')
        sm = SLIDE_REF_RE.match(str(t.get('slide', '')))
        if not sm:
            errors.append(f'{where}: slide must be slide:<id>'); continue
        sid = sm.group(1)
        taught[sid] += 1
        if taught[sid] > 1:
            errors.append(f'{where}: slide:{sid} has more than one teaching row')
        if kind_of.get(sid) not in ('knowledge', 'design-decision'):
            errors.append(f'{where}: slide:{sid} is classified {kind_of.get(sid)}; teaching rows are for knowledge or design-decision slides')
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
    for sid in slide_ids:
        if kind_of.get(sid) == 'knowledge' and not taught[sid]:
            errors.append(f'{REQ_FILE}: knowledge slide:{sid} has no teaching row (say how it is used, or reclassify it)')

    # (e) counts and the summary block
    kinds_count = Counter(kind_of.values())
    total = sum(by_status.values())
    scope = f' (tier {tier_filter})' if tier_filter else ''
    report.append(f'slides: {len(slide_ids)} (' + ', '.join(f'{k} {kinds_count[k]}' for k in KINDS) + ')')
    report.append(f'requirements{scope}: {total}; on {sum(1 for s in per_slide if per_slide[s])} slides in all')
    report.append(f'by status{scope}: ' + ', '.join(f'{s} {by_status[s]}' for s in STATUSES))
    for t in TIERS:
        report.append(f'tier {t}: ' + ', '.join(f'{s} {by_tier[(t, s)]}' for s in STATUSES) + f' (total {sum(by_tier[(t, s)] for s in STATUSES)})')
    out = by_status['扱わない']
    report.append(f'扱わない{scope}: {out} / {total} ({(100.0 * out / total) if total else 0:.1f}%)')
    report.append(f'by owner issue{scope}: ' + ', '.join(f'{o} {n}' for o, n in sorted(by_owner.items(), key=lambda x: int(x[0][1:]) if ISSUE_RE.match(x[0]) else 0)))
    proposed = [r for r, it in items.items() if it.get('origin') == 'proposed']
    report.append(f'planned items: {len(items)} ({len(items) - len(proposed)} from issue bodies, {len(proposed)} proposed); unused {sum(1 for r in items if not used[r])}')
    for r in proposed:
        if not used[r]:
            errors.append(f'{ITEMS_FILE}: proposed item {r} is used by no requirement or teaching row')
    if require_done:
        for rid in todo_in_scope:
            errors.append(f'{REQ_FILE}: {rid}: still 未着手' + (f' (tier {tier_filter})' if tier_filter else ''))

    want = summary_of(kind_of.values(), reqs)
    summary = req_data.get('summary')
    if not isinstance(summary, dict) or dict(summary) != dict(want):
        errors.append(f'{REQ_FILE}: summary block is stale; want ' + json.dumps(want, ensure_ascii=False))

    ctx = {'items': items, 'reqs': reqs, 'teaching': req_data.get('teaching') or [], 'slide_ids': slide_ids, 'data': req_data}
    return errors, report, ctx


def summary_of(kinds, reqs):
    kinds = Counter(kinds)
    st = Counter(r.get('status') for r in reqs if isinstance(r, dict))
    tr = Counter((r.get('tier'), r.get('status')) for r in reqs if isinstance(r, dict))
    s = OrderedDict([('design_decision_slides', kinds['design-decision']), ('knowledge_slides', kinds['knowledge']),
                     ('structural_slides', kinds['structural']), ('requirements', sum(st.values()))])
    s.update((k, st[k]) for k in STATUSES)
    for t in TIERS:
        s.update((f'{t}_{k}', tr[(t, k)]) for k in STATUSES)
    return s


# ------------------------------------------------------------------ writing
def _q(s):
    return json.dumps(str(s), ensure_ascii=False)


def dump_requirements(data, slide_ids):
    """Canonical text of requirements.yaml (summary recomputed, rows in slide order)."""
    n_of = {i: k + 1 for k, i in enumerate(slide_ids)}
    order = {i: k for k, i in enumerate(slide_ids)}
    cls = sorted(data.get('classification') or [], key=lambda c: order.get(str(c['slide'])[6:], 10 ** 6))
    reqs = sorted(data.get('requirements') or [], key=lambda r: (order.get(str(r['slide'])[6:], 10 ** 6), int(str(r['id']).rsplit('.R', 1)[1])))
    teach = sorted(data.get('teaching') or [], key=lambda t: order.get(str(t['slide'])[6:], 10 ** 6))
    out = ['# template_version: 0.1.0',
           '# スライドと成果物の対応表（#22）。書式と状態の意味は README.md を参照。',
           '# 検査：python tools/trace_check.py（summary の件数も照合する。summary は --update-hash で書き直される）',
           '# 人による点検は未実施。', '', 'summary:']
    out += [f'  {k}: {v}' for k, v in summary_of([c['kind'] for c in cls], reqs).items()]
    out += ['', '# 152 枚すべての分類（deck/slide_ids.json の順）。sha は docs/slides.json の title・text・notes の sha256 の先頭 12 桁',
            'classification:']
    for c in cls:
        sid = str(c['slide'])[6:]
        out.append(f'  - {{slide: {c["slide"]}, kind: {c["kind"]}, sha: "{c.get("sha", "")}", reviewed_on: "{c.get("reviewed_on", "")}"}}  # {n_of.get(sid, "?")}')
    out += ['', '# 設計判断のスライドの要件', 'requirements:']
    cur = None
    for r in reqs:
        if r['slide'] != cur:
            cur = r['slide']
            out.append(f'  # ---- {n_of.get(str(cur)[6:], "?")} {cur}')
        out.append(f'  - id: {r["id"]}')
        out.append(f'    slide: {r["slide"]}')
        out.append(f'    text: {_q(r["text"])}')
        out.append(f'    owner_issue: "{r["owner_issue"]}"')
        out.append('    planned_items: [' + ', '.join(r['planned_items']) + ']')
        out.append(f'    status: {r["status"]}')
        out.append(f'    tier: {r.get("tier", "")}')
        for f in ('assumption', 'breaks_when', 'note'):
            if r.get(f):
                out.append(f'    {f}: {_q(r[f])}')
    out += ['', '# 教材（対比表・用語集・判断の木・観点書）に使うスライド。知識のスライドは全件', 'teaching:']
    for t in teach:
        out.append(f'  - slide: {t["slide"]}  # {n_of.get(str(t["slide"])[6:], "?")}')
        out.append('    use: [' + ', '.join(t['use']) + ']')
        if t.get('note'):
            out.append(f'    note: {_q(t["note"])}')
    return '\n'.join(out) + '\n'


def update_hashes(root, slide_ids_to_update, reviewed_on):
    data = yaml_load(_read(os.path.join(root, REQ_FILE)))
    deck = [x.get('id') for x in json.loads(_read(os.path.join(root, 'deck', 'slide_ids.json')))]
    content = {s.get('id'): s for s in json.loads(_read(os.path.join(root, SLIDES_FILE)))}
    rows = {str(c.get('slide'))[6:]: c for c in data.get('classification') or []}
    missing = [s for s in slide_ids_to_update if s not in rows or s not in content]
    if missing:
        print('ERROR not classified or not in docs/slides.json: ' + ', '.join(missing))
        return 1
    for s in slide_ids_to_update:
        rows[s]['sha'] = slide_sha(content[s])
        rows[s]['reviewed_on'] = reviewed_on
    with open(os.path.join(root, REQ_FILE), 'w', encoding='utf-8', newline='\n') as f:
        f.write(dump_requirements(data, deck))
    print(f'updated sha and reviewed_on={reviewed_on} for {len(slide_ids_to_update)} slide(s)')
    return 0


def render_new_items(ctx):
    """Markdown list of the proposed planned items, grouped by issue."""
    slides_of = {}
    for r in ctx['reqs']:
        if not isinstance(r, dict):
            continue
        for ref in r.get('planned_items') or []:
            slides_of.setdefault(ref, []).append(str(r.get('id')))
    for t in ctx['teaching']:
        if not isinstance(t, dict):
            continue
        for ref in t.get('use') or []:
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
    ap.add_argument('--tier', choices=TIERS, help='restrict the counts (and --require-done) to one tier')
    ap.add_argument('--require-done', action='store_true', help='also fail while a requirement (of --tier) is 未着手')
    ap.add_argument('--write-new-items', action='store_true', help=f'regenerate {NEW_ITEMS_FILE}')
    ap.add_argument('--update-hash', nargs='+', metavar='SLIDE_ID', help='record the current content hash of these slides after re-reading their requirements')
    ap.add_argument('--reviewed-on', help='date of the re-reading, YYYY-MM-DD (with --update-hash)')
    a = ap.parse_args(argv)
    if a.update_hash:
        if not a.reviewed_on or not _valid_date(a.reviewed_on):
            ap.error('--update-hash needs --reviewed-on YYYY-MM-DD')
        return update_hashes(a.root, a.update_hash, a.reviewed_on)
    errors, report, ctx = check(a.root, a.tier, a.require_done)
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
