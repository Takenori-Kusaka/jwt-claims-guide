// Preview of the design editor (#49; the screens of the viewer of #36). MIT (LICENSE of the repository).
// editor.js gives it the design being edited (setData: the registry parsed in the browser and, once claim_lint has run in
// Pyodide, the render bundle of tools/claim_lint) and the diagnostics (JSON Schema and claim_lint) by row. Every value
// from the data is put into the page as text (textContent), never as HTML.
//
// Hooks for the review mode (#50): every registry row on every screen carries data-anchor="<kind>:<id>" (anchorOf), and
// registerRowPanel(fn) adds what fn(anchor, row, kind) returns to the badge cell of that row and to the side panel of its
// detail screen. The row content hash is ClaimsEditor.rowHash(anchor) (editor.js).
'use strict';
(function () {
  // the build id (tools/build_claims_viewer.py, #53). editor.js checks it; this module also checks editor.js when the
  // page has read every script, in case editor.js is the one of another build (it would not check anything)
  const BUILD_ID = 'a78a07f6cdd8';
  (window.CLAIMS_BUILD = window.CLAIMS_BUILD || {})['preview.js'] = BUILD_ID;
  addEventListener('DOMContentLoaded', () => {
    const ce = window.ClaimsEditor;
    if (ce && ce.BUILD_ID === BUILD_ID) return;
    // the banner of editor.js, made here because editor.js may be too old to make it
    if (document.getElementById('build-banner')) return;
    const el = document.createElement('div');
    el.id = 'build-banner'; el.className = 'buildwarn'; el.setAttribute('role', 'alert');
    const p = document.createElement('p');
    const b = document.createElement('button');
    b.type = 'button'; b.id = 'build-reload'; b.className = 'primary'; b.textContent = '再読み込みする';
    b.addEventListener('click', () => location.reload());
    p.append('新しい版が公開されました。再読み込みしてください。 ', b, ' （版のそろわないファイル：editor.js・preview.js）');
    el.append(p);
    document.body.prepend(el);
  });
  const DATA = (window.CLAIMS_VIEWER_DATA = window.CLAIMS_VIEWER_DATA || {});
  const META = DATA.meta;
  const CASESTUDY = 'https://github.com/Takenori-Kusaka/jwt-claims-casestudy/tree/';
  const REPO = 'https://github.com/Takenori-Kusaka/jwt-claims-guide';
  const ASVS_CHAPTERS = { 1: 'Encoding-and-Sanitization', 2: 'Validation-and-Business-Logic', 3: 'Web-Frontend-Security',
    4: 'API-and-Web-Service', 5: 'File-Handling', 6: 'Authentication', 7: 'Session-Management', 8: 'Authorization',
    9: 'Self-contained-Tokens', 10: 'OAuth-and-OIDC', 11: 'Cryptography', 12: 'Secure-Communication', 13: 'Configuration',
    14: 'Data-Protection', 15: 'Secure-Coding-and-Architecture', 16: 'Security-Logging-and-Error-Handling', 17: 'WebRTC' };
  const REF_KIND = { spec: '仕様', guidance: '指針', research: '研究', book: '書籍', incident: '事故', 'guide-slide': 'ガイドのスライド',
    'author-proposal': '筆者の提案' };
  const SEVERITY = { error: ['ng', '✖'], warn: ['warn', '▲'], info: ['info', 'ℹ'] };
  // the words of the problems panel (templates/glossary.md 5.1): the screens do not show the English names of the levels
  const SEV_WORD = { error: 'エラー', warn: '警告', info: '情報' };
  const STATUS = { satisfied: ['ok', '✓', '満たす'], unsatisfied: ['ng', '✖', '満たさない'], unknown: ['warn', '?', '判定できない'] };
  const DECISION = { '採用': ['ok', '●'], '既定どおり': ['neutral', '○'], '却下': ['ng', '✖'] };
  // kinds of rows of templates/registry/README.md 2. (縮小 Lite の印). Not the trace tier (core/full).
  const ROW_KIND = { read: '受け手が読む行', unread: '受け手のない採用の行', idle: '省ける行（既定どおり・受け手なし）', rejected: '却下の行' };
  const own = (o, k) => o !== null && o !== undefined && Object.prototype.hasOwnProperty.call(o, k);
  const lookup = (o, k) => (own(o, k) ? o[k] : undefined);

  // bundle: {registry, sections, design, label, stale}; diag: {byTarget: Map(id -> [finding]), list: [finding]}
  const state = { bundle: null, diag: { byTarget: new Map(), list: [] }, panels: [], hooks: {}, folds: new Set(), views: {} };
  const $ = (s, r) => (r || document).querySelector(s);
  // kinds of rows (the anchor of a row is `${kind}:${id}`; #50 keys review records by it)
  const ANCHOR_KIND = { claim: 'claims', token: 'token_types', hop: 'hops', event: 'catalog_answers', profile: 'issuance_profile' };
  function anchorOf(kind, id) { return kind + ':' + id; }

  // ------------------------------------------------------------ DOM helpers (text only)
  function h(tag, attrs) {
    const el = document.createElement(tag);
    if (attrs) {
      for (const k of Object.keys(attrs)) {
        const v = attrs[k];
        if (v === null || v === undefined || v === false) continue;
        if (k === 'class') el.className = v;
        else if (k === 'text') el.textContent = v;
        else if (k.slice(0, 2) === 'on') el.addEventListener(k.slice(2), v);
        else el.setAttribute(k, v === true ? '' : String(v));
      }
    }
    // a link that leaves the editor (another site, the slide page) opens in a new tab, so that the edits stay
    if (tag === 'a' && /^(https?:|\.\.\/)/i.test(el.getAttribute('href') || '')) { el.setAttribute('target', '_blank'); el.setAttribute('rel', 'noopener noreferrer'); }
    for (let i = 2; i < arguments.length; i++) add(el, arguments[i]);
    return el;
  }
  function add(el, c) {
    if (c === null || c === undefined || c === false) return;
    if (Array.isArray(c)) { c.forEach((x) => add(el, x)); return; }
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  function code(t) { return h('code', null, String(t)); }
  // the words of the screens (#67) in the headings that come from the generated tables (tools/claim_lint render keeps the
  // words of the templates; templates/glossary.md 5.1 has the table)
  const UI_TERMS = [['値の出どころ', '値の元データ'], ['出どころ', '元データ'], ['台帳の行', 'クレーム'], ['台帳', 'クレーム一覧'], ['ホップ', '経路'], ['観点', '確認事項'], ['縮小 Lite', 'Lite'], ['載るトークン', '入るトークン']];
  function ui(s) { let t = String(s === null || s === undefined ? '' : s); UI_TERMS.forEach(([a, b]) => { t = t.split(a).join(b); }); return t; }
  function badge(kind, symbol, text, title) {
    return h('span', { class: 'badge ' + kind, title: title || null }, h('span', { 'aria-hidden': 'true' }, symbol), text);
  }
  function safeUrl(u) { return /^https?:\/\//i.test(String(u)) ? String(u) : null; }
  function ext(url, text) { const u = safeUrl(url); return u ? h('a', { href: u, rel: 'noreferrer noopener' }, text) : text; }
  function slideLink(id) {
    const s = lookup(META.names.slides, id);
    return h('a', { href: '../#' + encodeURIComponent(id), title: s ? `スライド ${s.n}：${s.title}` : 'スライド（ID が一覧に無い）',
      'data-slide': id }, 'slide:' + id);
  }
  // #/<view>[/<id>][?<query>]; the query keeps the filters and the folds (fold=<keys that are closed>)
  function route(view, id, query) {
    let r = '#/' + view + (id !== undefined && id !== null ? '/' + encodeURIComponent(id) : '');
    const q = new URLSearchParams(query || {});
    if (state.folds.size && !q.has('fold')) q.set('fold', foldParam());
    const qs = q.toString();
    if (qs) r += '?' + qs;
    return r;
  }
  // a foldable block: <details data-fold=key>, open unless key is in the URL's fold list. The content is built when it is
  // first opened (a ledger of 60 rows x 73 columns stays light).
  function foldable(key, summary, content, opts) {
    opts = opts || {};
    const d = h('details', { class: 'fold ' + (opts.cls || ''), 'data-fold': key, id: opts.id || null });
    const closedByDefault = !!opts.closed;
    const isClosed = state.folds.has(key) ? !closedByDefault : closedByDefault;
    d.open = !isClosed;
    d.append(h('summary', null, summary));
    let built = false;
    const build = () => { if (built) return; built = true; add(d, typeof content === 'function' ? content() : content); };
    if (d.open || opts.eager) build();  // eager: the content is in the page while the fold is closed (a jump can land in it)
    d.addEventListener('toggle', () => {
      if (d.open) build();
      const differs = d.open === closedByDefault;  // the state that is not the default is written in the URL
      if (differs) state.folds.add(key); else state.folds.delete(key);
      const p = parseHash();
      const q = new URLSearchParams(p.query);
      if (state.folds.size) q.set('fold', foldParam()); else q.delete('fold');
      const qs = q.toString();
      history.replaceState(null, '', '#/' + p.parts.map(encodeURIComponent).join('/') + (qs ? '?' + qs : ''));
    });
    return d;
  }
  // fold keys are names, not positions: sec~<decision>, claim~<id>, claim~<id>~grp~<column group name>, grp~<name>.
  // `~` does not occur in an id (^C-[a-z0-9-]+$ and the other ids) and each key is URI-encoded in the list.
  function foldKey() { return Array.prototype.slice.call(arguments).map((x) => String(x).replace(/\s+/g, '_')).join('~'); }
  function foldParam() { return Array.from(state.folds).sort().map(encodeURIComponent).join(','); }
  function foldAllIn(root, open) { root.querySelectorAll('details.fold').forEach((d) => { if (d.open !== open) { d.open = open; d.dispatchEvent(new Event('toggle')); } }); }
  function foldButtons(root) {
    return h('p', { class: 'foldbar' }, h('button', { type: 'button', onclick: () => foldAllIn(root(), true) }, 'すべて開く'), ' ',
      h('button', { type: 'button', onclick: () => foldAllIn(root(), false) }, 'すべて畳む'));
  }
  // the badges and side panels of #50 (registerRowPanel) and the link to the YAML line of the row
  function rowExtras(kind, id, row, where) {
    const anchor = anchorOf(kind, id);
    const out = [];
    state.panels.forEach((fn) => { try { const x = fn(anchor, row, kind, where); if (x) out.push(x); } catch (e) { /* a panel must not break the page */ } });
    return out;
  }
  function revealLink(kind, id) {
    if (!state.hooks.reveal) return null;
    return h('button', { type: 'button', class: 'link', 'data-reveal': anchorOf(kind, id), title: 'エディターでこの行を開く',
      onclick: () => state.hooks.reveal(anchorOf(kind, id)) }, h('span', { 'aria-hidden': 'true' }, '✎'), ' YAML');
  }

  // inline text: `code`, **bold**, slide:<id>, URLs, C-… / token ids (when they exist in the dataset)
  const INLINE = /(`[^`]+`)|(\*\*[^*]+\*\*)|(slide:p\d{2}-[a-z0-9-]+)|(https?:\/\/[^\s）、。」)"'<>]+)/g;
  function inline(text) {
    const out = []; const s = String(text); let last = 0; let m;
    INLINE.lastIndex = 0;
    while ((m = INLINE.exec(s))) {
      if (m.index > last) out.push(s.slice(last, m.index));
      if (m[1]) out.push(code(m[1].slice(1, -1)));
      else if (m[2]) out.push(h('strong', null, m[2].slice(2, -2)));
      else if (m[3]) out.push(slideLink(m[3].slice(6)));
      else if (m[4]) out.push(ext(m[4], m[4]));
      last = INLINE.lastIndex;
    }
    if (last < s.length) out.push(s.slice(last));
    return out;
  }
  // the paragraphs of the design document and of what claim_lint writes into it (data-design-text: the checks of the
  // words of the screens leave them out; tools/tests/test_claims_editor_ux.py)
  function paras(list) { return (list || []).map((t) => h('p', { class: 'muted', 'data-design-text': '1' }, inline(t))); }
  // text of this guide's own materials (the review questions, the trace table): `#5` is an issue of this repository and
  // becomes a link that says so (never a bare number on the screen)
  function issueLink(n) { return h('a', { href: REPO + '/issues/' + n, class: 'gh-issue', title: `GitHub の issue ${n}（このガイドのリポジトリ）` }, `GitHub の issue ${n}`); }
  function inlineRepo(text) {
    const out = [];
    inline(text).forEach((x) => {
      if (typeof x !== 'string') { out.push(x); return; }
      let last = 0; let m;
      const re = /(?:追跡 )?#(\d+)/g;
      while ((m = re.exec(x))) {
        if (m.index > last) out.push(x.slice(last, m.index));
        out.push(issueLink(m[1]));
        last = re.lastIndex;
      }
      if (last < x.length) out.push(x.slice(last));
    });
    return out;
  }

  // ------------------------------------------------------------ data access
  function B() { return state.bundle || { registry: {}, sections: [] }; }
  function isObj(x) { return x !== null && typeof x === 'object' && !Array.isArray(x); }
  function arr(v) { return Array.isArray(v) ? v : []; }
  function rows(doc, key) { return isObj(doc) ? arr(doc[key]).filter(isObj) : []; }
  function reg(b) { return (b || B()).registry || {}; }
  function claims(b) { return rows(reg(b).claims, 'claims'); }
  function tokenTypes(b) { return rows(reg(b).token_types, 'token_types'); }
  function profile(b) { const t = reg(b).token_types; return isObj(t) && isObj(t.issuance_profile) ? t.issuance_profile : null; }
  function hops(b) { return rows(reg(b).hops, 'hops'); }
  function answers(b) { return rows(reg(b).catalog_answers, 'answers'); }
  function section(id, b) { return ((b || B()).sections || []).find((s) => s.id === id) || null; }
  function claimById(id) { return claims().find((c) => c.id === id); }
  function tokenById(id) { return tokenTypes().find((t) => t.id === id); }
  function hopById(id) { return hops().find((x) => x.id === id); }
  function fullName(c) { return (c.namespace ? c.namespace : '') + (c.name || ''); }
  function rowKind(c) {
    if (c.decision === '却下') return 'rejected';
    const read = Array.isArray(c.consumers) && c.consumers.length > 0;
    if (c.decision === '既定どおり' && !read) return 'idle';
    if (!read) return 'unread';  // 採用 with no consumer: not a row that receivers read
    return 'read';
  }
  function stages(c) { return arr(c.authoritative_writer).map((w) => w && w.stage).filter((x) => typeof x === 'string'); }

  // diagnostics by target (claim id, token type id, hop id, event id), from editor.js: JSON Schema (in the browser) and
  // claim_lint (Pyodide). Each has source 'schema' | 'claim_lint' | 'yaml'.
  function lintIndex() { return state.diag.byTarget; }
  const SOURCE = { schema: 'Schema', claim_lint: '設計の規則', yaml: 'YAML', editor: 'エディター' };
  function lintBadges(id) {
    const fs = lintIndex().get(id) || [];
    if (!fs.length) return null;
    const by = Object.create(null);
    fs.forEach((f) => { by[f.severity] = (by[f.severity] || 0) + 1; });
    return h('span', { class: 'codes', 'data-diag-for': id }, Object.keys(SEVERITY).filter((k) => by[k]).map((k) =>
      badge(SEVERITY[k][0], SEVERITY[k][1], `${SEV_WORD[k]} ${by[k]}`, fs.filter((f) => f.severity === k).map((f) => `[${SOURCE[f.source] || f.source}] ${f.rule} ${f.message}`).join('\n'))));
  }
  function lintList(id, title) {
    const fs = lintIndex().get(id) || [];
    if (!fs.length) return null;
    return h('div', { class: 'note warn', 'data-lint-for': id }, h('strong', null, title || '問題（自動の検査）'),
      h('ul', null, fs.map((f) => h('li', null, sevBadge(f.severity), ' ', h('span', { class: 'src' }, SOURCE[f.source] || f.source), ' ', code(f.rule), ' ',
        f.line ? h('button', { type: 'button', class: 'link', onclick: () => state.hooks.goto && state.hooks.goto(f.file, f.line) }, `${f.file}:${f.line}`) : null, ' ', inline(f.message)))));
  }
  function lintProfile(sec) { const m = /（profile (\w+)）/.exec(((sec && sec.notes) || []).join(' ')); return m ? m[1] : null; }
  function datasetLabel() { return B().label || ''; }
  function sevBadge(s) { const x = lookup(SEVERITY, s) || ['neutral', '•']; return badge(x[0], x[1], lookup(SEV_WORD, s) || s); }

  // ------------------------------------------------------------ value rendering
  function refItem(r) {
    if (!r || typeof r !== 'object') return text(r);
    if (r.kind === 'guide-slide') return slideLink(r.id);
    if (r.kind === 'author-proposal') {
      const t = r.tracking && /^#\d+$/.test(r.tracking) ? h('a', { href: REPO + '/issues/' + r.tracking.slice(1) }, r.tracking) : r.tracking;
      return h('span', null, '筆者の提案：', r.id, t ? ['（追跡 ', t, '）'] : null);
    }
    const label = r.url ? ext(r.url, r.id) : r.id;
    return h('span', null, label, h('span', { class: 'muted' }, `（${lookup(REF_KIND, r.kind) || r.kind}${r.verified_on ? '、確かめた日 ' + r.verified_on : ''}）`));
  }
  function refs(v) {
    const list = Array.isArray(v) ? v : [v];
    if (!list.length) return none();
    return h('ul', null, list.map((r) => h('li', null, refItem(r))));
  }
  function asvs(id) {
    const m = /^v(\d+\.\d+\.\d+)-(\d+)\.\d+\.\d+$/.exec(id);
    if (!m) return code(id);
    const ch = +m[2]; const name = m[1] === '5.0.0' ? lookup(ASVS_CHAPTERS, ch) : undefined;
    if (!name) return h('span', { title: 'ASVS の章が分からないのでリンクにしない' }, code(id));
    // the files of OWASP/ASVS v5.0.0 5.0/en are numbered 0x10-V1 ... 0x19-V10, 0x20-V11 ... 0x26-V17 (decimal after 0x)
    return h('a', { href: asvsUrl(ch), rel: 'noreferrer noopener',
      title: `OWASP ASVS ${m[1]} の V${ch}` }, 'ASVS ' + id);
  }
  function asvsUrl(ch) {
    return `https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x${ch + 9}-V${ch}-${ASVS_CHAPTERS[ch]}.md`;
  }
  function caseRef(s) {
    const m = /^jwt-claims-casestudy@([0-9a-f]{7,40}):(.+)$/.exec(s);
    return m ? h('a', { href: CASESTUDY + m[1], title: 'ケーススタディのコミット ' + m[1] }, s) : text(s);
  }
  function claimLink(id) { return claimById(id) ? h('a', { href: route('claim', id) }, id) : code(id); }
  function tokenLink(id) { return tokenById(id) ? h('a', { href: route('token', id) }, id) : code(id); }
  function hopLink(id) { return hopById(id) ? h('a', { href: route('hop', id) }, id) : code(id); }
  function eventLabel(id) { const n = lookup(META.names.events, id); return h('span', null, code(id), n ? ' ' + n : ''); }
  function questionLabel(id) { const n = lookup(META.names.questions, id); return h('span', null, code(id), n ? `「${n}」` : ''); }
  function none() { return h('span', { class: 'muted' }, '—（なし）'); }
  function text(v) { return h('span', null, inline(v)); }

  function smartString(s) {
    if (claimById(s)) return claimLink(s);
    if (tokenById(s)) return tokenLink(s);
    if (/^jwt-claims-casestudy@/.test(s)) return caseRef(s);
    if (/^v\d+\.\d+\.\d+-\d+\.\d+\.\d+$/.test(s)) return asvs(s);
    return text(s);
  }
  function value(v, col, depth) {
    depth = depth || 0;
    if (v === null || v === undefined) return none();
    if (typeof v === 'boolean') return h('span', null, v ? 'はい' : 'いいえ', ' ', code(String(v)));
    if (typeof v === 'number') return h('span', { class: 'num' }, String(v));
    if (typeof v === 'string') return smartString(v);
    if (Array.isArray(v)) {
      if (!v.length) return h('span', { class: 'muted' }, '[]（空）');
      if (v.every((x) => x && typeof x === 'object' && !Array.isArray(x))) {
        if (v.every((x) => own(x, 'kind') && own(x, 'id') && own(REF_KIND, x.kind))) return refs(v);
        return miniTable(v, col);
      }
      if (v.every((x) => typeof x !== 'object')) return h('ul', null, v.map((x) => h('li', null, value(x, col, depth + 1))));
      return h('ul', null, v.map((x) => h('li', null, value(x, col, depth + 1))));
    }
    if (typeof v === 'object') {
      if (own(v, 'kind') && own(v, 'id') && own(REF_KIND, v.kind)) return refItem(v);
      return h('dl', { class: 'obj' }, Object.keys(v).map((k) => [h('dt', null, partLabel(col, k)), h('dd', null, value(v[k], null, depth + 1))]));
    }
    return text(String(v));
  }
  function partLabel(col, k) {
    const p = col && (col.parts || []).find((x) => x.key === k);
    return p ? h('span', { title: k }, p.label, ' ', h('span', { class: 'muted' }, '(' + k + ')')) : k;
  }
  function miniTable(rows, col) {
    const keys = [];
    rows.forEach((r) => Object.keys(r).forEach((k) => { if (!keys.includes(k)) keys.push(k); }));
    return h('table', { class: 'mini' }, h('thead', null, h('tr', null, keys.map((k) => h('th', { scope: 'col' }, partLabel(col, k))))),
      h('tbody', null, rows.map((r) => h('tr', null, keys.map((k) => h('td', null, k in r ? value(r[k], null, 1) : ''))))));
  }
  // columns whose values need a specific link
  function columnValue(coll, key, v, col) {
    if (v === undefined) return null;
    if (key === 'refs' || key === 'registered_ref' || key === 'lifetime_refs') return v === null ? none() : refs(v);
    if (key === 'asvs_ids') return Array.isArray(v) && v.length ? h('ul', null, v.map((x) => h('li', null, asvs(x)))) : value(v, col);
    if (coll === 'claims' && key === 'carried_in') return Array.isArray(v) && v.length ? h('span', { class: 'codes' }, v.map(tokenLink)) : value(v, col);
    if (key === 'answers' || key === 'does_not_answer') return Array.isArray(v) && v.length ? h('ul', null, v.map((x) => h('li', null, questionLabel(x)))) : value(v, col);
    if (key === 'issue_events') return Array.isArray(v) && v.length ? h('ul', null, v.map((x) => h('li', null, eventLabel(x)))) : value(v, col);
    // upstream is one hop ID or a list of IDs (#58: a reissue hop that receives the tokens of several IdPs)
    if (coll === 'hops' && key === 'upstream') return [].concat(v || []).length ? h('span', null, [].concat(v || []).map((x, i) => [i ? '、' : null, hopLink(x)])) : none();
    if (coll === 'hops' && key === 'token_type') return v ? tokenLink(v) : none();
    return value(v, col);
  }

  // one record with every column of the schema (README headings), grouped as in README 3.
  function record(coll, obj, opts) {
    const cols = META.columns[coll] || [];
    const groups = [];
    cols.forEach((c) => {
      const g = c.group || '';
      let grp = groups.find((x) => x.name === g);
      if (!grp) { grp = { name: g, cols: [] }; groups.push(grp); }
      grp.cols.push(c);
    });
    const out = [];
    const key = (g) => foldKey.apply(null, ((opts && opts.foldPrefix) || []).concat(['grp', g.name]));
    if (groups.length > 1) out.push(h('nav', { class: 'toc', 'aria-label': '列のまとまり' }, groups.map((g) => h('a', { href: '#' + key(g), onclick: jump }, g.name))));
    // each column group of README 3. is a fold (its key is in the URL when it is closed)
    groups.forEach((g) => {
      const cols = () => h('div', { class: 'cols' }, g.cols.map((c) => column(coll, c, obj)));
      if (!g.name) { out.push(cols()); return; }
      const filled = g.cols.filter((c) => own(obj, c.key)).length;
      out.push(foldable(key(g), h('span', { class: 'fh' }, g.name, ' ', h('span', { class: 'muted small' }, `（${filled} / ${g.cols.length} 列を記入）`)), cols, { id: key(g) }));
    });
    const known = new Set(cols.map((c) => c.key));
    const extra = Object.keys(obj).filter((k) => !known.has(k));
    if (extra.length && !(opts && opts.noExtra)) {
      out.push(h('h2', null, 'スキーマにない列'));
      out.push(h('p', { class: 'muted' }, 'クレーム一覧のスキーマ（templates/registry/*.schema.json）に無い列です。スキーマの検査（claim_lint）で落ちます。'));
      out.push(h('div', { class: 'cols' }, extra.map((k) => column(coll, { key: k, label: k, lite: '' }, obj))));
    }
    return out;
  }
  function jump(e) {
    const id = e.currentTarget.getAttribute('href').slice(1);
    const t = document.getElementById(id);
    if (t) { e.preventDefault(); if (t.tagName === 'DETAILS' && !t.open) { t.open = true; t.dispatchEvent(new Event('toggle')); } t.scrollIntoView(); (t.querySelector('summary') || t).focus(); }
  }
  function column(coll, c, obj) {
    const has = Object.prototype.hasOwnProperty.call(obj, c.key);
    const qs = (META.review || {})[coll + '.' + c.key] || [];
    return h('div', { class: 'col' + (has ? '' : ' empty'), 'data-col': c.key },
      h('div', { class: 'ch' }, h('span', { class: 'lbl' }, c.label), h('code', { class: 'key' }, c.key),
        c.lite ? h('span', { class: 'lite' }, 'Lite：' + c.lite) : null,
        c.meaning ? h('details', null, h('summary', null, '列の意味'), h('p', null, inline(c.meaning))) : null,
        qs.length ? h('details', { 'data-review': c.key }, h('summary', null, `レビューの問い ${qs.length} 件`),
          h('ul', null, qs.map((q) => h('li', null, h('a', { href: q.url }, q.id), ' ', q.text)))) : null),
      h('div', { class: 'cv' }, has ? columnValue(coll, c.key, obj[c.key], c) : '（未記入）'));
  }

  // generic table of a render section (columns with fmt)
  function cell(v, fmt, key, row) {
    if (v === null || v === undefined || v === '') return '—';
    switch (fmt) {
      case 'code': return linkish(String(v), key);
      case 'codes': return Array.isArray(v) ? (v.length ? h('span', { class: 'codes' }, v.map((x) => linkish(String(x), key))) : '—') : linkish(String(v), key);
      case 'list': return Array.isArray(v) ? (v.length ? h('ul', null, v.map((x) => h('li', null, inline(x)))) : '—') : inline(v);
      case 'refs': return refs(v);
      case 'seconds': return typeof v === 'number' ? v + ' 秒' : String(v);
      default:
        if (key === 'hop' && row && row.id && hopById(row.id)) return h('a', { href: route('hop', row.id) }, String(v));
        return typeof v === 'object' ? value(v) : inline(String(v));
    }
  }
  function linkish(s, key) {
    if (key === 'event' && own(META.names.events, s)) return code(s);
    if (claimById(s)) return claimLink(s);
    if (tokenById(s)) return tokenLink(s);
    if (hopById(s)) return hopLink(s);
    const c = claims().find((x) => x.name === s && x.decision !== '却下');
    if (c && (key === 'claim' || key === 'candidate' || key === 'claims' || key === 'mechanisms' || key === 'not_claims')) return h('a', { href: route('claim', c.id) }, s);
    return code(s);
  }
  function rowTarget(row) {
    return row.claim_id || (row.id && claimById(row.id) && row.id) || (row.id && tokenById(row.id) && row.id) ||
      (row.id && hopById(row.id) && row.id) || row.event || row.hop || null;
  }
  function anchorKind(target) {
    if (claimById(target)) return 'claims';
    if (tokenById(target)) return 'token_types';
    if (hopById(target)) return 'hops';
    if (answers().some((a) => a.event === target)) return 'catalog_answers';
    return null;
  }
  function table(t, opts) {
    opts = opts || {};
    const cols = t.columns.slice();
    const withLint = opts.lint !== false && lintIndex();
    return h('div', { class: 'tablewrap' }, h('table', { 'data-table': t.id },
      t.title ? h('caption', null, ui(t.title)) : null,
      h('thead', null, h('tr', null, cols.map((c) => h('th', { scope: 'col' }, ui(c.label))), withLint ? h('th', { scope: 'col' }, '問題') : null)),
      h('tbody', null, t.rows.map((r) => {
        const target = rowTarget(r);
        const kind = target ? anchorKind(target) : null;
        const tr = h('tr', { 'data-row': target || null, 'data-anchor': kind ? anchorOf(kind, target) : null, class: r.exceeds ? 'exceeds' : null },
          cols.map((c, i) => h(i === 0 ? 'th' : 'td', i === 0 ? { scope: 'row' } : null, cell(r[c.key], c.fmt, c.key, r))),
          withLint ? h('td', null, target ? lintBadges(target) : null, kind ? rowExtras(kind, target, r, 'table') : null) : null);
        return tr;
      }))));
  }
  function sectionBlock(s, level) {
    if (!s) return null;
    return [h(level || 'h2', null, ui(s.title)), paras(s.notes), s.tables.map((t) => table(t)), paras(s.after)];
  }
  // ------------------------------------------------------------ views
  const VIEWS = [
    ['dashboard', 'ダッシュボード'], ['claims', 'クレーム一覧'], ['ledger', 'クレームを 1 件ずつ開く'], ['tokens', 'トークン目録'], ['profile', '発行方式と、導かれる要件'],
    ['hops', '経路の一覧'], ['lifecycle', '寿命の 4 つの層'], ['catalog', 'カタログへの回答'], ['lint', '問題'],
    ['tables', '判断の行・データ源・問いと仕組み'],
  ];
  // the file each screen is made from (#53): without it the menu shows the screen dimmed and the screen offers to add it
  const VIEW_FILE = { claims: 'claims.yaml', ledger: 'claims.yaml', tables: 'claims.yaml', tokens: 'token_types.yaml', profile: 'token_types.yaml',
    lifecycle: 'token_types.yaml', hops: 'hops.yaml', catalog: 'catalog_answers.yaml' };
  const FILE_WHAT = { 'claims.yaml': 'クレーム一覧', 'token_types.yaml': 'トークン目録と発行方式の選択', 'hops.yaml': '経路の一覧', 'catalog_answers.yaml': 'カタログへの回答' };
  const DETAIL = { claim: 'claims', token: 'tokens', hop: 'hops' };
  function hasFile(name) { const f = B().files; return !name || !f || f.includes(name); }
  const PY_TITLE = 'Python で計算する画面（claim_lint をブラウザの中で動かす。初めて開くと読み込みに数秒）';
  function nav(cur) {
    const ul = $('#nav'); ul.textContent = '';
    const mode = state.hooks.mode ? state.hooks.mode() : 'edit';
    const all = state.diag.list || [];
    const cur2 = parseHash().parts;
    const design = () => {
      ul.append(h('li', { class: 'sep' }, '設計書の画面'));
      VIEWS.forEach(([v, label]) => {
        const missing = !hasFile(VIEW_FILE[v]);
        ul.append(h('li', null, h('a', { href: route(v), 'aria-current': cur === v ? 'page' : null, 'data-view': v, class: missing ? 'nofile' : null,
          'data-nofile': missing ? VIEW_FILE[v] : null, title: missing ? `${FILE_WHAT[VIEW_FILE[v]]}のファイル（${VIEW_FILE[v]}）をまだ開いていません` : null }, label,
        missing ? h('span', { class: 'vh' }, '（ファイルをまだ開いていない）') : null,
        PYTHON_VIEWS[v] ? h('span', { class: 'py', title: PY_TITLE }, h('span', { 'aria-hidden': 'true' }, 'Py'), h('span', { class: 'vh' }, '（Python で計算。初めては数秒）')) : null,
        v === 'lint' && all.length ? h('span', { class: 'cnt' }, ' ', String(all.length)) : null)));
      });
    };
    const extras = () => Object.keys(state.views).forEach((name) => {
      const v = state.views[name];
      ul.append(h('li', { class: 'sep' }, v.group));
      v.nav().forEach((it) => ul.append(h('li', null, h('a', { href: route(name, it.sub || null), 'data-view': name + (it.sub ? '/' + it.sub : ''),
        'aria-current': cur === name && (cur2[1] || '') === (it.sub || '') ? 'page' : null }, it.label, it.count ? h('span', { class: 'cnt' }, ' ', it.count) : null))));
    });
    // while a review is going on, its screens come first; otherwise the screens of the design come first (#67)
    if (mode === 'review') { extras(); design(); } else { design(); extras(); }
    ul.append(h('li', { class: 'sep' }, 'ガイド全体'));
    ul.append(h('li', null, h('a', { href: '#/trace', 'aria-current': cur === 'trace' ? 'page' : null }, 'スライドと成果物の対応')));
    ul.append(h('li', { class: 'legend', id: 'nav-legend' }, h('span', { class: 'py', 'aria-hidden': 'true' }, 'Py'), '：Python で計算する画面（初めて開くと読み込みに数秒）。',
      h('br'), h('span', { 'aria-hidden': 'true' }, '○'), '：ファイルをまだ開いていない画面'));
  }
  function viewNoFile(v) {
    const file = VIEW_FILE[v];
    const label = (VIEWS.find((x) => x[0] === v) || [v, v])[1];
    return [h('h1', { tabindex: '-1' }, label),
      h('div', { class: 'note nofile-box', 'data-nofile': file },
        h('p', null, h('strong', null, `${FILE_WHAT[file]}のファイルは、まだ開いていません。`)),
        h('p', null, 'この画面は、', FILE_WHAT[file], 'のファイル ', code(file), ' から作ります。足すと、ここに表示します（名前が違っても、中身で見分けます）。'),
        h('p', { class: 'buttons' }, h('button', { type: 'button', class: 'primary', 'data-action': 'add-file', id: 'btn-nofile-add', onclick: () => state.hooks.addFile && state.hooks.addFile() }, 'ファイルを足す'),
          h('a', { href: route('dashboard') }, 'ダッシュボードへ')))];
  }

  // the dashboard (#53): what is open, the checks, the review, and what needs doing, each linked to its screen
  function viewDashboard() {
    const b = B();
    const files = b.files || [];
    const cs = claims();
    const dec = Object.create(null);
    cs.forEach((c) => { dec[c.decision] = (dec[c.decision] || 0) + 1; });
    const cat = section('catalog-summary');
    const diag = state.diag.list || [];
    const dc = { error: 0, warn: 0, info: 0 };
    diag.forEach((f) => { dc[f.severity] = (dc[f.severity] || 0) + 1; });
    const st = state.hooks.lintState ? state.hooks.lintState() : 'off';
    const counts = [
      ['claims.yaml', 'クレーム', cs.length, Object.keys(dec).map((k) => `${k} ${dec[k]}`).join('・'), 'claims'],
      ['token_types.yaml', 'トークンの種類', tokenTypes().length, null, 'tokens'],
      ['hops.yaml', '経路', hops().length, null, 'hops'],
      ['catalog_answers.yaml', 'カタログへの回答', answers().length, cat && cat.counts ? `対象外 ${cat.counts.out_of_scope}（${cat.counts.out_of_scope_pct}%）` : null, 'catalog'],
    ];
    const open = counts.filter((x) => files.includes(x[0]));
    const closed = counts.filter((x) => !files.includes(x[0]));
    const out = [h('h1', { tabindex: '-1' }, 'ダッシュボード', ' ', h('span', { class: 'muted small' }, b.label || '')),
      h('p', { class: 'lead' }, '開いた設計書の件数・問題・レビューの進み具合と、要対応の項目です。どれも押すと、その画面に移ります。', h('span', { class: 'muted small' }, ' 保存先：', code(b.design || '（ローカル）'))),
      open.length ? h('div', { class: 'cards', id: 'dash-counts' }, open.map(([file, k, v, sub, view]) =>
        h('a', { class: 'card', href: route(view), 'data-dash': view, title: file }, h('div', { class: 'k' }, k), h('div', { class: 'v' }, String(v)), sub ? h('div', { class: 'muted' }, sub) : null))) : null,
      closed.length ? h('p', { class: 'muted', id: 'dash-closed' }, 'まだ開いていないファイル：', closed.map(([file, k], i) => [i ? '・' : '', k, ' ', h('span', { class: 'small' }, '(' + file + ')')]), ' ',
        h('button', { type: 'button', id: 'btn-dash-add', onclick: () => state.hooks.addFile && state.hooks.addFile() }, 'ファイルを足す')) : null];
    // what needs doing: errors, the rows to look at again, the questions not answered
    const todos = [];
    diag.filter((f) => f.severity === 'error').slice(0, 8).forEach((f) => {
      const where = f.anchorKind === 'claims' ? claimLink(f.anchorId) : f.anchorKind === 'token_types' ? tokenLink(f.anchorId) : f.anchorKind === 'hops' ? hopLink(f.anchorId)
        : f.line ? h('button', { type: 'button', class: 'link', 'data-goto': f.file + ':' + f.line, onclick: () => state.hooks.goto && state.hooks.goto(f.file, f.line) }, `${f.file} の ${f.line} 行`) : null;
      todos.push(h('li', { 'data-todo-kind': 'error' }, sevBadge('error'), where, h('span', null, inline(String(f.message).slice(0, 140)))));
    });
    if (dc.error > 8) todos.push(h('li', { 'data-todo-kind': 'error' }, h('a', { href: route('lint', null, { sev: 'error' }) }, `エラーをすべて見る（${dc.error} 件）`)));
    const sums = Object.keys(state.views).map((name) => { try { return state.views[name].summary ? state.views[name].summary() : null; } catch (e) { return null; } }).filter(Boolean);
    sums.forEach((x) => (x.todos || []).forEach((t) => todos.push(h('li', { 'data-todo-kind': t.kind }, h('strong', null, t.label), h('a', { href: t.href, 'data-todo-link': t.kind }, t.text)))));
    if (cat && cat.counts && (cat.counts.missing || []).length) {
      todos.push(h('li', { 'data-todo-kind': 'catalog' }, h('strong', null, 'カタログの未回答'), h('a', { href: route('catalog') }, `${cat.counts.missing.length} 件のイベントに、該当か対象外かを答えていない`)));
    }
    out.push(h('h2', null, '要対応'), todos.length ? h('ul', { class: 'todo', id: 'dash-todo' }, todos) : h('p', { class: 'muted', id: 'dash-todo' }, '要対応の項目はありません。'));
    // the checks and the review
    const rules = Object.create(null);
    diag.forEach((f) => { rules[f.rule] = (rules[f.rule] || 0) + 1; });
    const top = Object.keys(rules).sort((x, y) => rules[y] - rules[x]).slice(0, 5);
    const lintSec = h('section', { id: 'dash-lint', 'aria-labelledby': 'dash-lint-h' }, h('h2', { id: 'dash-lint-h' }, h('a', { href: route('lint') }, '問題')),
      h('p', null, Object.keys(SEVERITY).map((k) => [badge(SEVERITY[k][0], SEVERITY[k][1], `${SEV_WORD[k]} ${dc[k] || 0}`), ' '])),
      top.length ? h('ul', null, top.map((r) => h('li', null, code(r), ` ${rules[r]} 件`))) : h('p', { class: 'muted' }, '問題はありません。'),
      h('p', { class: 'muted small' }, '書式の検査（JSON Schema）は入力のたびに行います。設計の規則の検査（claim_lint）：',
        { off: 'まだ動かしていません', loading: '読み込み中', running: '検査中', fresh: '最新の内容で検査済み', stale: '編集の後、まだ検査していません', error: '動きませんでした', unavailable: 'ファイルを直接開いたときは動きません' }[st] || st),
      st === 'off' || st === 'error' ? h('p', null, h('button', { type: 'button', 'data-action': 'load-lint', onclick: () => state.hooks.loadLint && state.hooks.loadLint() }, '設計の規則も検査する（初めては数秒）')) : null);
    const secs = [lintSec].concat(sums.map((x) => h('section', { 'data-dash-summary': x.id || '' }, h('h2', null, h('a', { href: x.href }, x.title)), h('ul', null, (x.lines || []).map((l) => h('li', null, l))))));
    out.push(h('div', { class: 'dash' }, secs));
    out.push(h('details', { class: 'note' }, h('summary', null, '詳しく（画面の読み方・送信しないこと）'),
      h('ul', null, h('li', null, '根拠の ', code('slide:<id>'), ' は、スライドの Web 版の該当スライドに移動します。RFC・ASVS などは原典に移動します。'),
        h('li', null, '状態は色だけでなく、記号と文字（✓ 満たす・✖ 満たさない・? 判定できない、error・warn・info）で示します。'),
        h('li', null, 'キーボード：', h('span', { class: 'kbd' }, 'Tab'), ' で移動し、', h('span', { class: 'kbd' }, 'Enter'), ' で開きます。一覧で ', h('span', { class: 'kbd' }, '/'), ' を押すと検索欄に移ります。'),
        h('li', null, '入力した内容は、このページの外に送りません（リンクを押したときの移動は除く）。技術的には、ページの CSP（', code("connect-src 'self'"), '）で、このサイト以外への通信を禁じています。'))));
    return out;
  }
  function card(k, v, sub) { return h('div', { class: 'card' }, h('div', { class: 'k' }, k), h('div', { class: 'v' }, String(v)), sub ? h('div', { class: 'muted' }, sub) : null); }

  const FILTERS = [
    ['token', '入るトークン', (c) => arr(c.carried_in).map(String)],
    ['stage', '段階（書き手）', (c) => stages(c)],
    ['decision', '採否', (c) => [String(c.decision || '（未記入）')]],
    ['row_kind', '行の種類', (c) => [ROW_KIND[rowKind(c)]]],
    ['data_category', '何のデータか（data_category）', (c) => arr(c.data_category).map(String)],
    ['pii_category', '個人情報の区分', (c) => [String(c.pii_category || '（未記入）')]],
  ];
  function viewClaims(query) {
    const cs = claims();
    const q = new URLSearchParams(query || '');
    const opts = {};
    FILTERS.forEach(([k, , f]) => { const set = new Set(); cs.forEach((c) => f(c).forEach((x) => x && set.add(x))); opts[k] = Array.from(set).sort(); });
    const search = h('input', { type: 'search', id: 'f-q', value: q.get('q') || '', placeholder: 'ID・名前・意味・理由で探す', 'aria-describedby': 'f-hint' });
    const selects = FILTERS.map(([k, label]) => {
      const s = h('select', { id: 'f-' + k, 'data-filter': k }, h('option', { value: '' }, 'すべて'), opts[k].map((x) => h('option', { value: x }, x)));
      s.value = q.get(k) || '';
      return h('label', null, label, s);
    });
    const count = h('p', { class: 'count', id: 'f-count', 'aria-live': 'polite' });
    const tbody = h('tbody');
    const tbl = h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'claims' }, h('caption', null, 'クレーム（クリックかキーボードで詳細を開く）'),
      h('thead', null, h('tr', null, ['ID', '名前', '型', '採否', '行の種類', '入るトークン', 'data_category', 'pii_category', '状態', '段階', '問題'].map((x) => h('th', { scope: 'col' }, x)))), tbody));
    function apply() {
      const params = {};
      const text = search.value.trim().toLowerCase();
      if (text) params.q = search.value.trim();
      const sel = {};
      FILTERS.forEach(([k]) => { const v = $('#f-' + k).value; if (v) { sel[k] = v; params[k] = v; } });
      const rows = cs.filter((c) => {
        if (text) {
          const hay = [c.id, fullName(c), c.description, c.not_meaning, c.rationale, c.note].filter(Boolean).map(String).join(' ').toLowerCase();
          if (!hay.includes(text)) return false;
        }
        return FILTERS.every(([k, , f]) => !sel[k] || f(c).includes(sel[k]));
      });
      tbody.textContent = '';
      rows.forEach((c) => {
        const d = lookup(DECISION, c.decision) || ['neutral', '•'];
        tbody.append(h('tr', { 'data-row': c.id, 'data-anchor': anchorOf('claims', c.id) },
          h('th', { scope: 'row' }, h('a', { href: route('claim', c.id) }, String(c.id))),
          h('td', null, c.namespace ? h('span', { class: 'muted' }, c.namespace) : null, h('strong', null, c.name)),
          h('td', null, code(c.type || '—'), c.shape && c.shape !== 'single' ? [' ', h('span', { class: 'muted' }, c.shape)] : null),
          h('td', null, badge(d[0], d[1], c.decision)),
          h('td', null, ROW_KIND[rowKind(c)]),
          h('td', null, arr(c.carried_in).length ? h('span', { class: 'codes' }, arr(c.carried_in).map(tokenLink)) : '—'),
          h('td', null, arr(c.data_category).length ? h('span', { class: 'codes' }, arr(c.data_category).map(code)) : '—'),
          h('td', null, String(c.pii_category || '—')),
          h('td', null, c.status === 'deprecated' ? badge('warn', '▲', '廃止予定 deprecated') : String(c.status || '—')),
          h('td', null, stages(c).join('・') || '—'),
          h('td', null, lintBadges(c.id), rowExtras('claims', c.id, c, 'list'))));
      });
      count.textContent = `${rows.length} / ${cs.length} 行`;
      const hash = route('claims', null, params);
      if (location.hash !== hash) history.replaceState(null, '', hash);
    }
    const form = h('form', { class: 'filters', role: 'search', onsubmit: (e) => e.preventDefault(), oninput: apply, onchange: apply },
      h('label', { class: 'wide' }, '検索', search, h('span', { id: 'f-hint' }, '/ キーでここに移ります')), selects,
      h('div', null, h('button', { type: 'button', onclick: () => { search.value = ''; FILTERS.forEach(([k]) => { $('#f-' + k).value = ''; }); apply(); } }, '絞り込みを解く')));
    setTimeout(apply, 0);
    return [h('h1', { tabindex: '-1' }, 'クレーム一覧'),
      h('p', { class: 'lead' }, 'クレーム一覧（claims.yaml）の全部の行。「行の種類」は、クレーム一覧の README の 2.（Lite の印）の区分です（対応表の tier（core・full）とは別）。'),
      form, count, tbl];
  }

  // ---- one claim, as an entity page of a data catalogue (#67): six fields on top, the other columns in tabs.
  // Which column is in which tab is data (meta.claim_tabs, tools/build_claims_viewer.py CLAIM_TABS); a column of the
  // schema that the table does not name is in the last tab, and so are the keys of the row that the schema does not have.
  const CLAIM_TAB_DEFAULT = 'overview';
  function claimTabs(c) {
    const cols = META.columns.claims || [];
    const by = new Map(cols.map((x) => [x.key, x]));
    const extra = Object.keys(c).filter((k) => !by.has(k));
    const tabs = (META.claim_tabs && META.claim_tabs.length ? META.claim_tabs : [{ id: 'other', label: 'そのほか', columns: cols.map((x) => x.key) }]);
    return tabs.map((t, i) => ({ id: t.id, label: t.label, cols: t.columns.map((k) => by.get(k)).filter(Boolean), extra: i === tabs.length - 1 ? extra : [] }));
  }
  function claimTabOf(c, column) {
    const t = claimTabs(c).find((x) => x.cols.some((k) => k.key === column) || x.extra.includes(column));
    return t ? t.id : null;
  }
  function claimColumn(c, obj) {
    const has = own(obj, c.key);
    const qs = (META.review || {})['claims.' + c.key] || [];
    return h('div', { class: 'col' + (has ? '' : ' empty'), 'data-col': c.key },
      h('div', { class: 'ch' }, h('span', { class: 'lbl' }, c.label), h('code', { class: 'key' }, c.key),
        has && c.meaning ? h('details', null, h('summary', null, '列の意味'), h('p', null, inline(c.meaning))) : null,
        qs.length ? h('details', { 'data-review': c.key }, h('summary', null, `確認事項 ${qs.length} 件`),
          h('ul', null, qs.map((q) => h('li', null, h('a', { href: q.url }, q.id), ' ', q.text)))) : null),
      h('div', { class: 'cv' }, has ? columnValue('claims', c.key, obj[c.key], c) : [h('span', null, '（未記入）'), c.meaning ? h('p', { class: 'small' }, inline(c.meaning)) : null]));
  }
  function claimHead(c) {
    const d = lookup(DECISION, c.decision) || ['neutral', '•'];
    const blank = () => h('span', { class: 'muted' }, '（未記入）');
    const col = (k) => (own(c, k) ? columnValue('claims', k, c[k], (META.columns.claims || []).find((x) => x.key === k)) : blank());
    const item = (key, label, body) => h('div', { class: 'chi', 'data-head': key }, h('dt', null, label), h('dd', null, body));
    return h('dl', { class: 'chead', 'data-claim-head': c.id },
      item('name', '名前', [c.namespace ? h('span', { class: 'muted' }, String(c.namespace)) : null, h('strong', null, String(c.name || '')), ' ', code(c.id)]),
      item('description', '意味', col('description')),
      item('type', '型', [own(c, 'type') ? code(String(c.type)) : blank(), own(c, 'shape') && typeof c.shape === 'string' ? h('span', { class: 'muted' }, `（${c.shape}）`) : null]),
      item('issuers', '発行元', col('issuers')),
      item('carried_in', '入るトークン', col('carried_in')),
      item('status', '状態', [badge(d[0], d[1], String(c.decision || '—')), own(c, 'status') ? [' ', text(String(c.status))] : null]));
  }
  function viewClaim(id, query) {
    const c = claimById(id);
    if (!c) return notFound('クレーム ' + id);
    const onHops = hops().filter((x) => arr(x.custom_claims).includes(c.id));
    const prof = section('issuance-profile');
    const effects = [];
    if (prof && prof.effects) prof.effects.forEach((e) => (e.requires || []).forEach((r) => { if ((r.rows || []).includes(c.id)) effects.push([e, r]); }));
    const tabs = claimTabs(c);
    const want = new URLSearchParams(query || '').get('tab');
    const first = tabs.some((t) => t.id === want) ? want : (tabs.some((t) => t.id === CLAIM_TAB_DEFAULT) ? CLAIM_TAB_DEFAULT : tabs[0].id);
    const related = { consume: onHops.length ? h('p', { class: 'note', 'data-related': 'hops' }, 'このクレームを運ぶ経路：', h('span', { class: 'codes' }, onHops.map((x) => hopLink(x.id)))) : null,
      issue: effects.length ? h('p', { class: 'note', 'data-related': 'effects' }, '発行方式から導かれる要件のうち、このクレームが満たすもの：', h('span', { class: 'codes' },
        effects.map(([e, r]) => h('a', { href: route('profile') + '', title: r.text }, r.id)))) : null };
    const buttons = []; const panels = [];
    const mark = (tid) => {
      buttons.forEach((b) => { const on = b.dataset.tab === tid; b.setAttribute('aria-selected', on ? 'true' : 'false'); b.tabIndex = on ? 0 : -1; });
      panels.forEach((p) => { p.hidden = p.dataset.tabpanel !== tid; });
    };
    // the selected tab is kept in the query (?tab=), so that a reload and the back button come back to it
    const select = (tid, focus) => {
      mark(tid);
      if (focus) buttons.find((b) => b.dataset.tab === tid).focus();
      const p = parseHash();
      const q = new URLSearchParams(p.query);
      if (tid === CLAIM_TAB_DEFAULT) q.delete('tab'); else q.set('tab', tid);
      const qs = q.toString();
      const hash = '#/' + p.parts.map(encodeURIComponent).join('/') + (qs ? '?' + qs : '');
      if (location.hash !== hash) history.replaceState(null, '', hash);
    };
    tabs.forEach((t, i) => {
      const filled = t.cols.filter((x) => own(c, x.key));
      const empty = t.cols.filter((x) => !own(c, x.key));
      const total = t.cols.length + t.extra.length;
      const n = filled.length + t.extra.length;
      const b = h('button', { type: 'button', role: 'tab', id: 'ctab-' + t.id, 'data-tab': t.id, 'aria-controls': 'cpanel-' + t.id, class: n ? null : 'none',
        'aria-selected': 'false', tabindex: '-1', onclick: () => select(t.id) },
      t.label, ' ', h('span', { class: 'cnt', 'aria-hidden': 'true' }, `${n}/${total}`), h('span', { class: 'vh' }, `（${total} 項目のうち ${n} 項目を記入）`));
      b.addEventListener('keydown', (e) => {
        const keys = { ArrowRight: i + 1, ArrowLeft: i - 1 + tabs.length, Home: 0, End: tabs.length - 1 };
        if (!(e.key in keys)) return;
        e.preventDefault();
        select(tabs[keys[e.key] % tabs.length].id, true);
      });
      buttons.push(b);
      panels.push(h('div', { role: 'tabpanel', id: 'cpanel-' + t.id, 'data-tabpanel': t.id, 'aria-labelledby': 'ctab-' + t.id, tabindex: '0', hidden: true },
        lookup(related, t.id) || null,
        filled.length ? h('div', { class: 'cols' }, filled.map((x) => claimColumn(x, c))) : null,
        t.extra.length ? [h('h2', null, 'スキーマにない列'), h('p', { class: 'muted' }, 'クレーム一覧のスキーマ（templates/registry/claims.schema.json）に無い列です。問題として報告されます。'),
          h('div', { class: 'cols' }, t.extra.map((k) => claimColumn({ key: k, label: k }, c)))] : null,
        !n ? h('p', { class: 'muted', 'data-tab-empty': t.id }, total ? 'このタブの項目は、まだ記入されていません。' : 'このタブに入る項目はありません。') : null,
        empty.length ? foldable(foldKey('unfilled', t.id), h('span', { 'data-unfilled': String(empty.length) }, `未記入 ${empty.length} 件を表示`), () => h('div', { class: 'cols' }, empty.map((x) => claimColumn(x, c))),
          { closed: true, eager: true, cls: 'unfilled' }) : null));
    });
    mark(first);
    const pii = typeof c.pii_category === 'string' && c.pii_category !== '該当なし' ? badge('info', '◆', '個人情報：' + c.pii_category) : null;
    return [h('p', null, h('a', { href: route('claims') }, '← クレームの一覧')),
      h('h1', { tabindex: '-1', 'data-anchor': anchorOf('claims', c.id) }, c.namespace ? h('span', { class: 'muted' }, String(c.namespace)) : null, String(c.name || ''), ' ', h('span', { class: 'muted' }, '(' + c.id + ')')),
      h('p', { class: 'cbadges' }, pii, ' ', lintBadges(c.id), ' ', revealLink('claims', c.id)),
      claimHead(c),
      lintList(c.id, 'このクレームの問題'),
      h('div', { class: 'ctabs', role: 'tablist', 'aria-label': 'クレームの項目', id: 'claim-tabs' }, buttons),
      panels,
      // what other parts add to the row (the review of #50 and #67): after the columns, where the reader has read them
      h('aside', { class: 'rowpanel', 'data-panel-for': anchorOf('claims', c.id) }, rowExtras('claims', c.id, c, 'detail'))];
  }
  // a problem lands on its field (#67): the detail screen of the row, for a claim the tab that holds the column, the
  // fold of the unfilled columns opened when the column is in it; the row of the column gets the focus and a mark
  function focusColumn(kind, id, column) {
    const view = lookup({ claims: 'claim', token_types: 'token', hops: 'hop' }, kind);
    const row = lookup({ claims: claimById, token_types: tokenById, hops: hopById }, kind);
    if (!view || !row(id)) return false;
    const col = column === null || column === undefined || column === '' ? null : String(column).split(/[.[/]/)[0];
    const q = {};
    if (kind === 'claims' && col) { const t = claimTabOf(row(id), col); if (t && t !== CLAIM_TAB_DEFAULT) q.tab = t; }
    state.pendingCol = col;
    const r = route(view, id, q);
    if (location.hash === r) render(); else location.hash = r;
    return true;
  }
  function landOnColumn() {
    const col = state.pendingCol;
    state.pendingCol = null;
    if (!col) return;
    const el = Array.from(document.querySelectorAll('#main [data-col]')).find((x) => x.dataset.col === col);
    if (!el) return;
    const panel = el.closest('[role="tabpanel"]');
    if (panel && panel.hidden) { const b = document.getElementById('ctab-' + panel.dataset.tabpanel); if (b) b.click(); }
    const fold = el.closest('details.fold');
    if (fold && !fold.open) { fold.open = true; fold.dispatchEvent(new Event('toggle')); }
    el.tabIndex = -1;
    el.classList.add('flash');
    el.scrollIntoView({ block: 'center' });
    el.focus({ preventScroll: true });
    setTimeout(() => el.classList.remove('flash'), 2500);
  }

  function viewTokens() {
    const s = section('token-inventory');
    const out = [h('h1', { tabindex: '-1' }, 'トークン目録')];
    if (s) out.push(paras(s.notes), s.tables.map((t) => table(t)));
    else out.push(registryTable('token_types', tokenTypes(), ['id', 'kind', 'decision', 'purpose', 'issuer', 'aud', 'holder', 'format', 'max_lifetime', 'transport'], 'token'));
    out.push(h('p', { class: 'muted' }, '種別の ID を開くと、目録の全列を表示します。'));
    return out;
  }
  function viewToken(id) {
    const t = tokenById(id);
    if (!t) return notFound('トークン種別 ' + id);
    const d = lookup(DECISION, t.decision) || ['neutral', '•'];
    const carried = claims().filter((c) => arr(c.carried_in).includes(id));
    return [h('p', null, h('a', { href: route('tokens') }, '← トークン目録')),
      h('h1', { tabindex: '-1', 'data-anchor': anchorOf('token_types', id) }, id, ' ', h('span', { class: 'muted' }, String(lookup(META.names.token_kinds, t.kind) || t.kind || ''))),
      h('p', null, badge(d[0], d[1], String(t.decision || '—')), ' ', revealLink('token_types', id)),
      h('aside', { class: 'rowpanel', 'data-panel-for': anchorOf('token_types', id) }, rowExtras('token_types', id, t, 'detail')), lintList(id),
      carried.length ? h('p', null, '含まれるクレーム：', h('span', { class: 'codes' }, carried.map((c) => h('a', { href: route('claim', c.id), title: c.id }, fullName(c))))) : null,
      record('token_types', t)];
  }
  // a table built in the browser from the YAML (before claim_lint has run, or when render has no such table)
  function registryTable(coll, rows, keys, view) {
    const cols = META.columns[coll] || [];
    const lab = (k) => (cols.find((c) => c.key === k) || {}).label || k;
    const kind = coll === 'catalog' ? 'catalog_answers' : coll;
    return h('div', { class: 'tablewrap' }, h('table', { 'data-table': coll },
      h('thead', null, h('tr', null, keys.map((k) => h('th', { scope: 'col' }, lab(k))), h('th', { scope: 'col' }, '検査'))),
      h('tbody', null, rows.map((r) => h('tr', { 'data-row': r.id || null, 'data-anchor': r.id ? anchorOf(kind, r.id) : null }, keys.map((k, i) => h(i === 0 ? 'th' : 'td', i === 0 ? { scope: 'row' } : null,
        i === 0 && view ? h('a', { href: route(view, r.id) }, String(r.id)) : columnValue(coll, k, r[k]) || '—')),
        h('td', null, r.id ? lintBadges(String(r.id)) : null, r.id ? rowExtras(kind, r.id, r, 'table') : null))))));
  }

  function viewProfile() {
    const s = section('issuance-profile');
    const p = profile();
    const out = [h('h1', { tabindex: '-1' }, '発行方式の選択と、導かれる要件')];
    if (!s) {
      out.push(needBundle('導かれる要件（issuance_effects.yaml）'));
      if (p) out.push(h('h2', null, '発行方式の選択（書いたままの値）'), record('issuance_profile', p, { noExtra: true }));
      return out;
    }
    out.push(paras(s.notes), s.tables.map((t) => table(t, { lint: false })), paras(s.after));
    const holds = (s.effects || []).filter((e) => e.holds);
    const rest = (s.effects || []).filter((e) => !e.holds);
    out.push(h('h2', null, '選択から導かれる要件'),
      h('p', { class: 'muted small' }, '要件の出典：templates/registry/issuance_effects.yaml'),
      h('div', { class: 'note warn' }, h('p', null, h('strong', null, 'これは検査ではありません。'), '表を作るときの簡易な読み取りです。正しい判定は、問題の規則 L62〜L64 を見てください。', h('span', { class: 'muted small' }, '（tools/claim_lint/RENDER.md の 5.）'))));
    const tally = Object.assign(Object.create(null), { satisfied: 0, unsatisfied: 0, unknown: 0 });
    holds.forEach((e) => (e.requires || []).forEach((r) => { tally[r.status] = (tally[r.status] || 0) + 1; }));
    out.push(h('p', null, `成り立つ条件 ${holds.length} 件、要件 `, Object.keys(STATUS).map((k) => [badge(STATUS[k][0], STATUS[k][1], `${STATUS[k][2]} ${tally[k] || 0}`), ' '])));
    holds.forEach((e) => {
      out.push(h('section', { class: 'effect', 'data-effect': e.id },
        h('h3', null, code(e.id), ' ', h('span', { class: 'muted' }, '条件：'), (e.when || []).map((w, i) => [i ? '、' : '', code(w.field), ' = ', code(JSON.stringify(w.equals !== undefined ? w.equals : w))])),
        h('div', { class: 'tablewrap' }, h('table', null, h('thead', null, h('tr', null, ['要件', '内容', '判定（簡易な読み取り。正は L62）', '満たしている行'].map((x) => h('th', { scope: 'col' }, x)))),
          h('tbody', null, (e.requires || []).map((r) => {
            const st = lookup(STATUS, r.status) || ['neutral', '•', r.status];
            return h('tr', { 'data-require': r.id }, h('th', { scope: 'row' }, code(r.id)), h('td', null, inline(r.text)),
              h('td', null, badge(st[0], st[1], st[2]), r.check ? h('div', { class: 'muted' }, code(r.check.path + ' ' + r.check.op)) : null),
              h('td', null, (r.rows || []).length ? h('span', { class: 'codes' }, r.rows.map((x) => claimById(x) ? claimLink(x) : tokenLink(x))) : '—'));
          })))),
        h('p', { class: 'muted' }, '根拠：'), refs(e.refs || []), e.lint && e.lint.length ? h('p', { class: 'muted' }, '検査の規則：', e.lint.join('・')) : null));
    });
    if (rest.length) out.push(h('details', null, h('summary', null, `この選択では成り立たない条件 ${rest.length} 件`),
      h('ul', null, rest.map((e) => h('li', null, code(e.id), ' ', (e.when || []).map((w) => code(w.field + ' = ' + JSON.stringify(w.equals !== undefined ? w.equals : w))))))));
    if (p) out.push(h('details', null, h('summary', null, '発行方式の選択の全項目（書いたままの値）'), record('issuance_profile', p, { noExtra: true })));
    return out;
  }

  function viewHops() {
    const out = [h('h1', { tabindex: '-1' }, '経路の一覧'),
      h('p', { class: 'lead' }, inline('下流に進むほど、aud・scope・寿命・独自クレームが絞られていく様子を、上流の経路と並べて示します（slide:p06-narrow-downstream）。'))];
    const s = section('hop-table');
    const a = section('arrow-table');
    if (s) out.push(sectionBlock(s, 'h2')); else out.push(registryTable('hops', hops(), ['id', 'from', 'to', 'kind', 'upstream', 'token_type', 'aud', 'scope', 'max_lifetime', 'custom_claims'], 'hop'));
    out.push(narrowing());
    if (a) out.push(sectionBlock(a, 'h2'));
    return out;
  }
  // per hop: what changed against its upstream hop (fewer aud / scope / claims, shorter lifetime)
  function narrowing() {
    // one row per (hop, upstream hop): upstream may be a list (#58)
    const hs = hops().flatMap((x) => [].concat(x.upstream || []).map((up) => [x, up]));
    if (!hs.length) return null;
    const diff = (a, b) => arr(a).filter((x) => !arr(b).includes(x));
    return [h('h2', null, '上流との比較（絞り込み）'),
      h('p', { class: 'muted' }, '「減った」は上流にあって下流に無いもの、「増えた」は下流で足されたもの（増えたら理由が要る。この比較は、設計の規則の検査 L16 でも確かめる）。'),
      h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'narrowing' }, h('thead', null, h('tr', null, ['経路', '上流', 'aud', 'scope', '寿命', '独自クレーム'].map((x) => h('th', { scope: 'col' }, x)))),
        h('tbody', null, hs.map(([x, up]) => {
          const u = hopById(up) || {};
          const cmp = (k) => {
            const less = diff(u[k], x[k]); const more = diff(x[k], u[k]);
            return h('td', null, less.length ? h('div', null, badge('ok', '−', '減った'), ' ', less.join('、')) : null,
              more.length ? h('div', null, badge('warn', '+', '増えた'), ' ', more.join('、')) : null, !less.length && !more.length ? '同じ' : null);
          };
          const lt = typeof x.max_lifetime === 'number' && typeof u.max_lifetime === 'number'
            ? (x.max_lifetime < u.max_lifetime ? [badge('ok', '↓', '短い'), ` ${u.max_lifetime} → ${x.max_lifetime} 秒`] : x.max_lifetime > u.max_lifetime ? [badge('warn', '↑', '長い'), ` ${u.max_lifetime} → ${x.max_lifetime} 秒`] : `同じ（${x.max_lifetime} 秒）`)
            : '—';
          return h('tr', { 'data-row': x.id, 'data-anchor': anchorOf('hops', x.id) }, h('th', { scope: 'row' }, hopLink(x.id), ' ', h('span', { class: 'muted' }, `${x.from} → ${x.to}`)), h('td', null, hopLink(up)),
            cmp('aud'), cmp('scope'), h('td', null, lt), cmp('custom_claims'));
        }))))];
  }
  function viewHop(id) {
    const x = hopById(id);
    if (!x) return notFound('経路 ' + id);
    return [h('p', null, h('a', { href: route('hops') }, '← 経路の一覧')),
      h('h1', { tabindex: '-1', 'data-anchor': anchorOf('hops', id) }, id, ' ', h('span', { class: 'muted' }, `${x.from} → ${x.to}`)), h('p', null, revealLink('hops', id)),
      h('aside', { class: 'rowpanel', 'data-panel-for': anchorOf('hops', id) }, rowExtras('hops', id, x, 'detail')), lintList(id), record('hops', x)];
  }

  function viewLifecycle() {
    const s = section('lifecycle');
    const out = [h('h1', { tabindex: '-1' }, '寿命の 4 つの層')];
    if (!s) return out.concat(needBundle('寿命の 4 つの層'));
    out.push(paras(s.notes), s.tables.map((t) => table(t)), paras(s.after));
    return out;
  }
  function viewCatalog() {
    const s = section('catalog-summary');
    const out = [h('h1', { tabindex: '-1' }, 'カタログへの回答'),
      h('p', { class: 'lead' }, '発行と利用のイベントのカタログ（templates/catalog/）の全部に、該当か対象外を答えたもの。対象外は、起きないとした前提と、その前提が崩れる条件をあわせて示します。')];
    if (s) {
      const c = s.counts || {};
      out.push(h('div', { class: 'cards' }, card('全件', c.total), card('発行', c.issue), card('利用', c.use), card('該当', c.applies), card('対象外', c.out_of_scope, `${c.out_of_scope_pct}%`),
        card('未回答', (c.missing || []).length)), paras(s.notes), s.tables.map((t) => table(t)));
    } else {
      out.push(registryTable('catalog', answers().map((a) => Object.assign({ id: a.event }, a)), ['event', 'answer', 'token_types', 'assumption', 'breaks_when', 'note']));
    }
    return out;
  }
  // every diagnostic of the design (JSON Schema in the browser, YAML syntax, claim_lint in Pyodide), with the line in the
  // editor; the claim_lint section of render (profile, counts, R8 sizes) below
  function viewLint(query) {
    const q0 = new URLSearchParams(query || '');
    const s = section('ci-result');
    const all = state.diag.list || [];
    const st = state.hooks.lintState ? state.hooks.lintState() : 'off';
    const prof = state.hooks.profile ? state.hooks.profile() : null;
    const out = [h('h1', { tabindex: '-1' }, '問題'),
      h('p', { class: 'lead' }, '書式の検査（JSON Schema）と、設計の規則の検査（claim_lint、Python でブラウザの中で動かす）の指摘です。行の番号を押すと、エディターのその行に移ります。')];
    const by = { error: 0, warn: 0, info: 0 };
    all.forEach((f) => { by[f.severity] = (by[f.severity] || 0) + 1; });
    out.push(h('p', null, Object.keys(SEVERITY).map((k) => [badge(SEVERITY[k][0], SEVERITY[k][1], `${SEV_WORD[k]} ${by[k] || 0}`), ' ']),
      h('span', { 'data-lint-state': st }, 'claim_lint：', { off: '未読み込み', loading: '読み込み中', running: '検査中', fresh: '最新の内容で検査済み', stale: '編集後に未検査', error: '失敗', unavailable: '使えない（file://）' }[st] || st)));
    if (state.hooks.setProfile) {
      const sel = h('select', { id: 'lint-profile', onchange: (e) => state.hooks.setProfile(e.target.value) },
        h('option', { value: 'full' }, 'full（既定）'), h('option', { value: 'lite' }, 'lite（Lite。R2・R4 を warn に下げ、必須の列が減る）'));
      sel.value = prof || 'full';
      out.push(h('p', null, h('label', { for: 'lint-profile' }, 'claim_lint の profile：'), sel, ' ',
        h('span', { class: 'muted' }, 'CLI の ', code('python tools/claim_lint <dir> --profile <profile> --also-scan <dir>/design.md'), ' と同じ検査です。')));
    }
    if (st !== 'fresh' && st !== 'stale' && st !== 'running') out.push(needBundle('claim_lint の指摘'));
    const sources = ['schema', 'yaml', 'claim_lint', 'editor'];
    const fsel = h('select', { id: 'diag-source' }, h('option', { value: '' }, 'すべて'), sources.map((x) => h('option', { value: x }, SOURCE[x])));
    const ssel = h('select', { id: 'diag-severity' }, h('option', { value: '' }, 'すべて'), Object.keys(SEVERITY).map((x) => h('option', { value: x }, SEV_WORD[x])));
    const tbody = h('tbody');
    const apply = () => {
      tbody.textContent = '';
      all.filter((f) => (!fsel.value || f.source === fsel.value) && (!ssel.value || f.severity === ssel.value)).forEach((f) => {
        const tg = f.target || '';
        const where = f.anchorKind === 'claims' ? claimLink(f.anchorId) : f.anchorKind === 'token_types' ? tokenLink(f.anchorId) : f.anchorKind === 'hops' ? hopLink(f.anchorId)
          : f.anchorKind === 'catalog_answers' ? h('a', { href: route('catalog') }, f.anchorId) : code(tg || '—');
        tbody.append(h('tr', { 'data-row': f.anchorId || tg, 'data-source': f.source },
          h('th', { scope: 'row' }, code(f.rule)), h('td', null, sevBadge(f.severity)), h('td', null, SOURCE[f.source] || f.source), h('td', null, where),
          h('td', null, f.line ? h('button', { type: 'button', class: 'link', 'data-goto': f.file + ':' + f.line, onclick: () => state.hooks.goto && state.hooks.goto(f.file, f.line) }, `${f.file}:${f.line}`) : (f.file || '—')),
          h('td', null, inline(f.message))));
      });
    };
    fsel.value = q0.get('src') || ''; ssel.value = q0.get('sev') || '';
    fsel.addEventListener('change', apply); ssel.addEventListener('change', apply);
    apply();
    out.push(h('form', { class: 'filters', onsubmit: (e) => e.preventDefault() }, h('label', null, '検査の種類', fsel), h('label', null, '重大度', ssel)),
      h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'diagnostics' }, h('thead', null, h('tr', null, ['規則', '重大度', '検査の種類', '対象', '行', '内容'].map((x) => h('th', { scope: 'col' }, x)))), tbody)));
    if (s) out.push(h('h2', null, '設計の規則の検査の要約'), h('p', { class: 'muted small' }, '設計書（design.md）の「CI の結果」の節と同じ内容'), paras(s.notes), paras(s.after));
    return out;
  }
  function viewTables() {
    const ids = ['decision-rows', 'data-sources', 'question-mechanism'];
    const out = [h('h1', { tabindex: '-1' }, '判断の行・データ源・問いと仕組み'), h('p', { class: 'lead' }, '設計書（design.md）の生成の区間と同じ表です（tools/claim_lint/RENDER.md の 1.）。')];
    const ss = ids.map((i) => section(i)).filter(Boolean);
    if (!ss.length) return out.concat(needBundle('判断の行・データ源・問い × 仕組み'));
    out.push(h('nav', { class: 'toc', 'aria-label': '表' }, ss.map((s) => h('a', { href: '#t-' + s.id, onclick: jump }, ui(s.title)))));
    ss.forEach((s) => out.push(h('h2', { id: 't-' + s.id, tabindex: '-1' }, ui(s.title)), paras(s.notes), s.tables.map((t) => table(t)), paras(s.after)));
    return out;
  }

  function viewTrace() {
    const t = DATA.trace;
    if (!t) return [h('h1', { tabindex: '-1' }, '対応表の進み具合'), h('p', { class: 'err' }, 'data/trace.js を読めません。')];
    const out = [h('h1', { tabindex: '-1' }, 'スライドと成果物の対応表の進み具合'),
      h('p', { class: 'lead' }, `ガイドのスライドが求める要件 ${t.total} 件を、段階（core・full）と状態で数えたもの。設計書ごとではなく、ガイド全体の値です（出典：${t.source}）。`)];
    const head = (first) => h('thead', null, h('tr', null, h('th', { scope: 'col' }, first), t.statuses.map((s) => h('th', { scope: 'col', class: 'num' }, s)), h('th', { scope: 'col', class: 'num' }, '計'), h('th', { scope: 'col' }, '実装済みの割合')));
    const row = (label, ts) => {
      const total = t.statuses.reduce((a, s) => a + (ts[s] || 0), 0);
      const done = ts['実装済み'] || 0;
      const pct = total ? Math.round((done / total) * 100) : 0;
      return h('tr', null, h('th', { scope: 'row' }, label), t.statuses.map((s) => h('td', { class: 'num' }, String(ts[s] || 0))), h('td', { class: 'num' }, String(total)),
        h('td', null, h('span', { class: 'bar', 'aria-hidden': 'true' }, barFill(pct)), `${pct}%（${done} / ${total}）`));
    };
    out.push(h('h2', null, '段階（core・full）× 状態'), h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'trace-tier' }, head('段階'),
      h('tbody', null, t.tiers.map((x) => row(x, t.tier_status[x])), row('計', sumBy(t.tiers.map((x) => t.tier_status[x])))))));
    out.push(h('h2', null, 'スライドの Part ごと（段階 × 状態）'), h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'trace-parts' }, head('Part・段階'),
      h('tbody', null, t.parts.map((p) => t.tiers.map((x) => row(`${p.part} ${x}`, p.tier_status[x])))))));
    out.push(h('h2', null, '担当ごと（GitHub の issue）'), h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'trace-owners' }, head('担当'),
      h('tbody', null, t.owners.map((o) => row(/^#\d+$/.test(o.owner) ? issueLink(o.owner.slice(1)) : o.owner, o.status))))));
    return out;
  }
  function barFill(pct) { const s = h('span'); s.style.width = pct + '%'; return s; }
  function sumBy(list) { const o = {}; list.forEach((x) => Object.keys(x).forEach((k) => { o[k] = (o[k] || 0) + x[k]; })); return o; }

  // ------------------------------------------------------------ the ledger with folds (sections, claims, column groups)
  function viewLedger() {
    const cs = claims();
    const body = h('div', { id: 'ledger' });
    const byDecision = [['採用', '採用の行'], ['既定どおり', '既定どおりの行'], ['却下', '却下の行']];
    const other = cs.filter((c) => !byDecision.some(([d]) => d === c.decision));
    byDecision.concat(other.length ? [['', 'そのほか（採否が未記入・不正）']] : []).forEach(([dec, title]) => {
      const rows = dec ? cs.filter((c) => c.decision === dec) : other;
      if (!rows.length) return;
      body.append(foldable(foldKey('sec', dec || 'other'), h('span', { class: 'fs' }, `${title}（${rows.length} 行）`),
        () => rows.map((c) => {
          const d = lookup(DECISION, c.decision) || ['neutral', '•'];
          return foldable(foldKey('claim', c.id), h('span', { class: 'fs', 'data-anchor': anchorOf('claims', c.id) }, badge(d[0], d[1], c.decision || '—'), ' ',
            h('strong', null, fullName(c) || c.id), ' ', h('span', { class: 'muted' }, '(' + c.id + ')'), ' ', lintBadges(c.id), rowExtras('claims', c.id, c, 'ledger')),
          () => [h('p', null, h('a', { href: route('claim', c.id) }, '詳細の画面'), ' ', revealLink('claims', c.id)), lintList(c.id),
            record('claims', c, { foldPrefix: ['claim', c.id] })], { closed: true, cls: 'row' });
        })));
    });
    return [h('h1', { tabindex: '-1' }, 'クレームを 1 件ずつ開く'),
      h('p', { class: 'lead' }, 'クレームを採否ごとの節にまとめ、行と列のまとまり（templates/registry/README.md の 3.1 の見出し）ごとに開閉できます。開閉の状態は URL に残ります（そのまま共有できます）。'),
      foldButtons(() => body), cs.length ? body : h('p', { class: 'muted' }, 'クレームがありません。')];
  }

  // ------------------------------------------------------------ screens that need claim_lint (Pyodide)
  function needBundle(what) {
    const st = state.hooks.lintState ? state.hooks.lintState() : 'off';
    const msg = { off: 'まだ動かしていません。', loading: '読み込んでいます…', running: '検査しています…',
      error: '読み込めませんでした。', unavailable: 'このページをファイルとして直接開いているので動きません（Web サーバーから開いてください）。' }[st] || '';
    return h('div', { class: 'note warn', 'data-need-lint': what }, h('p', null, `${what}は、設計の規則の検査（claim_lint、Python で書いた検査をブラウザの中で動かす）が作る表です。`, msg),
      st === 'off' || st === 'error' ? h('p', null, h('button', { type: 'button', class: 'primary', 'data-action': 'load-lint', onclick: () => state.hooks.loadLint && state.hooks.loadLint() },
        '設計の規則も検査する'), h('span', { class: 'muted' }, '（claim_lint。初めては約 13 MB をこのサイトから読み込みます。外部には送信しません）')) : null);
  }
  function staleNote() {
    return B().stale ? h('div', { class: 'note warn', 'data-stale': '1' }, h('p', null, badge('warn', '…', '古い'), ' 編集の後、まだ claim_lint を実行し終えていません。この画面の生成した表は、前の検査の時点のものです。')) : null;
  }

  // ------------------------------------------------------------ routing
  function notFound(what) { return [h('h1', { tabindex: '-1' }, '見つかりません'), h('p', null, what + ' はこの設計書にありません。')]; }

  function parseHash() {
    let raw = location.hash.replace(/^#\/?/, '');
    let query = '';
    const qi = raw.indexOf('?');
    if (qi >= 0) { query = raw.slice(qi + 1); raw = raw.slice(0, qi); }
    const parts = raw.split('/').filter((x) => x !== '').map((x) => { try { return decodeURIComponent(x); } catch (e) { return x; } });
    return { parts, query };
  }
  const PYTHON_VIEWS = { profile: 1, lifecycle: 1, lint: 1, tables: 1 };
  function render() {
    const { parts, query } = parseHash();
    const q = new URLSearchParams(query);
    state.folds = new Set((q.get('fold') || '').split(',').filter(Boolean).map((x) => { try { return decodeURIComponent(x); } catch (e) { return x; } }));
    if (!state.bundle) return;
    const view = parts[0] === 'overview' ? 'dashboard' : parts[0] || 'dashboard';
    const id = parts[1];
    if (view === 'lint' && state.hooks.onLintView) state.hooks.onLintView();
    const base = lookup(DETAIL, view) || view;
    const noFile = own(VIEW_FILE, base) && !hasFile(VIEW_FILE[base]) ? () => viewNoFile(base) : null;
    const fn = noFile || lookup({ dashboard: viewDashboard, claims: () => viewClaims(query), claim: () => viewClaim(id, query), ledger: viewLedger, tokens: viewTokens, token: () => viewToken(id),
      profile: viewProfile, hops: viewHops, hop: () => viewHop(id), lifecycle: viewLifecycle, catalog: viewCatalog, lint: () => viewLint(query), tables: viewTables,
      trace: viewTrace }, view);
    const navView = lookup({ claim: 'claims', token: 'tokens', hop: 'hops' }, view) || view;
    const extra = !fn && own(state.views, view) ? () => state.views[view].render(parts.slice(1), query) : null;
    show(navView, fn || extra || (() => notFound('画面 ' + view)), PYTHON_VIEWS[view]);
    landOnColumn();
  }
  function show(navView, fn, python) {
    nav(navView);
    const main = $('#main');
    const y = render.keepScroll ? main.scrollTop : 0;
    main.textContent = '';
    if (python) add(main, staleNote());
    add(main, fn());
    const h1 = main.querySelector('h1');
    document.title = (h1 ? h1.textContent + ' ― ' : '') + '設計書のエディター';
    if (render.focus && h1 && !render.keepScroll) h1.focus();
    render.focus = true;
    main.scrollTop = y;
    render.keepScroll = false;
    return null;
  }

  render.focus = false;
  addEventListener('keydown', (e) => {
    if (e.key === '/' && !/^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement.tagName) && !document.activeElement.closest('.cm-editor')) {
      const s = $('#f-q');
      if (s) { e.preventDefault(); s.focus(); }
    }
  });

  window.ClaimsPreview = {
    // bundle: {registry: {claims, token_types, hops, catalog_answers}, sections, design, label, stale}
    setData(bundle, diag, opts) {
      state.bundle = bundle;
      state.diag = diag || { byTarget: new Map(), list: [] };
      render.keepScroll = !!(opts && opts.keepScroll);
      if (opts && opts.keepScroll) render.focus = false;
      render();
    },
    clear() { state.bundle = null; $('#main').textContent = ''; $('#nav').textContent = ''; },
    render,
    setHooks(hooks) { Object.assign(state.hooks, hooks); },
    registerRowPanel(fn) { state.panels.push(fn); },
    // a screen of its own (the review mode of #50): render(parts after the name, query) -> nodes; nav() -> [{sub, label, count}]
    registerView(name, view) { state.views[name] = view; },
    // the renderers of the preview, for the screens of #50 (text only)
    helpers: { value: (v, col) => value(v, col), columnValue: (coll, key, v) => columnValue(coll, key, v, (META.columns[coll] || []).find((c) => c.key === key)),
      inline, inlineRepo, badge, lintBadges, foldable, foldKey, slideLink, revealLink, claimLink, tokenLink, hopLink, columns: (coll) => META.columns[coll] || [],
      registry: () => reg(), keepScroll: () => { render.keepScroll = true; render.focus = false; } },
    // focusColumn(kind, id, column) -> bool: go to the detail screen of the row and land on the column (#67)
    focusColumn,
    anchorOf,
    route,
    parseHash,
  };
  addEventListener('hashchange', () => { if (state.bundle) render(); });
})();
