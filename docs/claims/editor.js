// Design editor (#49). MIT (LICENSE of the repository).
// The page opens empty. The reader opens files, a folder, a drop, a paste, the skeleton of tools/new_design.py or a
// worked example; the left pane edits the files (CodeMirror 6), the right pane is the preview of #36 (preview.js).
// Checks run in the browser while the reader types: YAML syntax and the registry JSON Schemas at once (yaml +
// @cfworker/json-schema, vendor/editor-libs.js), and claim_lint in Pyodide (lint-worker.js) once it has been loaded.
// Nothing is sent: files are read with File / FileReader APIs, written with download links, and the page CSP limits
// connections to this site (connect-src 'self'), where only the static files of the editor are fetched (GET).
'use strict';
(function () {
  // ------------------------------------------------------------ the build (#53)
  // tools/build_claims_viewer.py writes the build id below and in every other module and data file, and the content
  // hash of each file into its URL (?v=). Files of two builds read together (an index.html still in the browser's
  // cache, a newer file from the server) are found here: a banner asks for a reload, and the editor does not start on
  // the mixed files (no exception, nothing half working).
  const BUILD_ID = '34f1924be1d0';
  const BUILDS = (window.CLAIMS_BUILD = window.CLAIMS_BUILD || {});
  BUILDS['editor.js'] = BUILD_ID;
  const BUILD_INFO = window.CLAIMS_BUILD_INFO || { id: null, files: {} };
  // the URL of a file loaded after the start, with its content hash (data/build.js)
  function asset(path) { const v = BUILD_INFO.files && BUILD_INFO.files[path]; return v ? path + '?v=' + v : path; }
  const LOADED_BEFORE = ['data/build.js', 'data/meta.js', 'data/schemas.js', 'data/trace.js', 'preview.js', 'app.css'];
  function cssBuild() {
    try { return getComputedStyle(document.documentElement).getPropertyValue('--build-id').trim().replace(/^"|"$/g, ''); } catch (e) { return ''; }
  }
  function buildOf(name) { return name === 'app.css' ? cssBuild() : BUILDS[name]; }
  function mismatched(names) { return names.filter((n) => buildOf(n) !== BUILD_ID); }
  // the same banner is made by preview.js and review.js (each module must be able to say it, whichever one is old)
  function buildBanner(parts) {
    let el = document.getElementById('build-banner');
    if (!el) {
      el = document.createElement('div');
      el.id = 'build-banner'; el.className = 'buildwarn'; el.setAttribute('role', 'alert');
      const p = document.createElement('p');
      const b = document.createElement('button');
      b.type = 'button'; b.id = 'build-reload'; b.className = 'primary'; b.textContent = '再読み込みする';
      b.addEventListener('click', () => location.reload());
      const d = document.createElement('span');
      d.id = 'build-parts'; d.className = 'small';
      p.append('新しい版が公開されました。再読み込みしてください。 ', b, ' ', d);
      el.append(p);
      document.body.prepend(el);
    }
    const d = el.querySelector('#build-parts');
    const all = new Set((d.dataset.parts || '').split(',').filter(Boolean));
    parts.forEach((x) => all.add(x));
    d.dataset.parts = Array.from(all).join(',');
    d.textContent = `（版のそろわないファイル：${Array.from(all).join('・')}）`;
  }
  const L = window.EditorLibs;
  const DATA = (window.CLAIMS_VIEWER_DATA = window.CLAIMS_VIEWER_DATA || {});
  const META = DATA.meta;
  const SCHEMAS = DATA.schemas;
  const P = window.ClaimsPreview;
  const $ = (s, r) => (r || document).querySelector(s);
  const own = (o, k) => o !== null && o !== undefined && Object.prototype.hasOwnProperty.call(o, k);

  // ------------------------------------------------------------ constants
  const REGISTRY = ['claims', 'token_types', 'hops', 'catalog_answers'];
  const FILE_ORDER = ['claims.yaml', 'token_types.yaml', 'hops.yaml', 'catalog_answers.yaml'];
  const FILE_LABEL = { 'claims.yaml': '台帳', 'token_types.yaml': 'トークン目録・発行方式', 'hops.yaml': 'ホップ',
    'catalog_answers.yaml': 'カタログへの回答', 'design.md': '設計書の本文' };
  const NAME_RE = /^(claims|token_types|hops|catalog_answers)\.yaml$|^claim_request_[A-Za-z0-9_-]+\.md$|^design\.md$/;
  const ROWS = { claims: ['claims.yaml', 'claims', 'id'], token_types: ['token_types.yaml', 'token_types', 'id'],
    hops: ['hops.yaml', 'hops', 'id'], catalog_answers: ['catalog_answers.yaml', 'answers', 'event'] };
  const SEV_CM = { error: 'error', warn: 'warning', info: 'info' };
  // autosave: one slot per design directory (claims-editor:autosave:v2:<designRel>), written only after an edit
  const AUTOSAVE_PREFIX = 'claims-editor:autosave:v2:';
  const AUTOSAVE_ON = 'claims-editor:autosave-enabled';
  const DEBOUNCE_CHECK = 300;
  const DEBOUNCE_LINT = 700;
  // The YAML 1.1 schema of the yaml package, with the plain-scalar rules of PyYAML's resolver (yaml/resolver.py), which
  // claim_lint uses: no timestamps (claim_lint keeps dates as strings), bool only for yes/no/true/false/on/off (not y/n),
  // floats need a dot and a signed exponent (1e3 and 1.0e3 stay strings), decimal ints have no leading 0 (09 is a string),
  // sexagesimal ints start with 1-9. So the editor, claim_lint and tools/row_hash.py get the same values.
  const PY_TRUE = /^(?:yes|Yes|YES|true|True|TRUE|on|On|ON)$/;
  const PY_FALSE = /^(?:no|No|NO|false|False|FALSE|off|Off|OFF)$/;
  const PY_FLOAT = /^(?:[-+]?[0-9][0-9_]*\.[0-9_]*(?:[eE][-+][0-9]+)?|\.[0-9][0-9_]*(?:[eE][-+][0-9]+)?|[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))$/;
  const PY_INT = /^[-+]?(?:0|[1-9][0-9_]*)$/;
  const PY_INT_TIME = /^[-+]?[1-9][0-9_]*(?::[0-5]?[0-9])+$/;
  function pyFloat(str) {
    let v = str.replace(/_/g, '').toLowerCase();
    let sign = 1;
    if (v[0] === '-' || v[0] === '+') { if (v[0] === '-') sign = -1; v = v.slice(1); }
    if (v === '.inf') return sign * Infinity;
    if (v === '.nan') return NaN;
    if (v.includes(':')) { let n = 0; v.split(':').forEach((d) => { n = n * 60 + parseFloat(d); }); return sign * n; }
    return sign * parseFloat(v);
  }
  const YAML_TAGS = (tags) => {
    const out = [];
    let floatDone = false;
    for (const t of tags) {
      if (t.tag === 'tag:yaml.org,2002:timestamp') continue;
      if (t.tag === 'tag:yaml.org,2002:bool') out.push(Object.assign({}, t, { test: /rue/.test(String(t.test)) ? PY_TRUE : PY_FALSE }));
      else if (t.tag === 'tag:yaml.org,2002:float') {
        if (!floatDone) out.push(Object.assign({}, t, { format: undefined, test: PY_FLOAT, resolve: pyFloat }));
        floatDone = true;
      } else if (t.tag === 'tag:yaml.org,2002:int' && !t.format) out.push(Object.assign({}, t, { test: PY_INT }));
      else if (t.tag === 'tag:yaml.org,2002:int' && t.format === 'TIME') out.push(Object.assign({}, t, { test: PY_INT_TIME }));
      else out.push(t);
    }
    return out;
  };
  // plain scalars that YAML readers disagree on (PyYAML / YAML 1.1 vs YAML 1.2): a warning, so that the writer quotes them
  const YAML11 = [
    [/^(?:y|Y|n|N)$/, 'y・n は、claim_lint（PyYAML）とこのエディターでは文字列、ほかの YAML 1.1 の読み手では真偽値'],
    [/^(?:yes|Yes|YES|no|No|NO|on|On|ON|off|Off|OFF)$/, 'yes・no・on・off は、claim_lint（YAML 1.1）では真偽値、YAML 1.2 の読み手では文字列'],
    [/^[-+]?(?:[0-9][0-9_]*)?\.?[0-9_]*[eE][0-9]+$/, '符号の無い指数（1e3・1.0e3）は、claim_lint では文字列、YAML 1.2 の読み手では数'],
    [/^[-+]?0[0-7_]+$/, '0 で始まる数は、claim_lint では 8 進数（010 は 8）、YAML 1.2 の読み手では 10 進数'],
    [/^[-+]?0[0-9_]*[89][0-9_]*$/, '0 で始まる 8・9 を含む数は、claim_lint では文字列、YAML 1.2 の読み手では数'],
    [/^[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+(?:\.[0-9_]*)?$/, 'コロンで区切った数（10:30）は、claim_lint では 60 進数（630）、YAML 1.2 の読み手では文字列'],
    [/^[-+]?(?:0b[01_]+|[0-9][0-9_]*_[0-9_]*(?:\.[0-9_]*)?)$/, '0b の数や _ で区切った数は、claim_lint では数、YAML 1.2 の読み手では文字列'],
  ];
  // plain scalars that claim_lint's loader (PyYAML) refuses although the yaml package reads them: an error (#50 leftovers
  // of the PR #51 check). `=` resolves to tag:yaml.org,2002:value, which SafeLoader cannot construct; a flow collection
  // entry that starts with `:` ([:1], {:1}) is a ParserError of PyYAML ("while parsing a flow node").
  const PY_ERROR = [
    [/^=$/, '= は、claim_lint（PyYAML）の読み込みでは誤り（tag:yaml.org,2002:value を作れない）。このエディターは文字列として読む'],
    [/^<<$/, 'マージキー（<<）は、claim_lint の読み込みでは誤りになる（このエディターは展開する）。書き下す'],
  ];
  function yaml11Diags(f) {
    const out = [];
    const seen = new Set();
    const push = (pos, src, severity, msg) => {
      const line = f.lc.linePos(pos).line;
      const k = line + '|' + src;
      if (seen.has(k)) return;
      seen.add(k);
      out.push({ source: 'yaml', severity, rule: 'YAML11', file: f.name, line, target: f.name.replace(/\.yaml$/, ''), message: msg });
    };
    const visit = (node, depth, isKey, inFlow) => {
      if (!node || depth > 200) return;
      if (L.isMap(node) || L.isSeq(node)) {
        const flow = !!node.flow;
        node.items.forEach((it) => {
          if (L.isPair(it)) { visit(it.key, depth + 1, true, flow); visit(it.value, depth + 1, false, flow); } else visit(it, depth + 1, false, flow);
        });
        return;
      }
      if (!L.isScalar(node) || node.type !== 'PLAIN' || typeof node.source !== 'string' || !node.range) return;
      const src = node.source;
      // [:1] / {:1}: the yaml package reads the plain scalar ":1"; in a flow collection PyYAML takes the ":" as the value
      // indicator and fails ("while parsing a flow node")
      if (inFlow && src[0] === ':') {
        push(node.range[0], src, 'error', `流れの形（[ ]・{ }）の中の、引用符の無い ${src}：claim_lint（PyYAML）の読み込みでは「:」が値の印になり誤り（while parsing a flow node）。このエディターは文字列 "${src}" として読む。引用符で囲む（"${src}"）`);
        return;
      }
      const err = PY_ERROR.find(([re]) => re.test(src));
      if (err) { push(node.range[0], src, 'error', `引用符の無い ${src}：${err[1]}。意味どおりに読ませるには引用符で囲む（"${src}"）`); return; }
      if (isKey && typeof node.value === 'number' && !isFinite(node.value)) {
        // .inf / .nan as a mapping key: both readers turn it into the text of the number (Infinity, NaN), see tools/row_hash.py
        push(node.range[0], src, 'warn', `引用符の無い ${src} をキーにしている：claim_lint では数（${node.value}）のキー、このエディターと tools/row_hash.py では文字列 "${String(node.value)}" のキーとして扱う。キーは引用符で囲んだ文字列にする（"${src}"）`);
        return;
      }
      const hit = YAML11.find(([re]) => re.test(src));
      if (hit) push(node.range[0], src, 'warn', `引用符の無い ${src}：${hit[1]}。意味どおりに読ませるには引用符で囲む（"${src}"）`);
    };
    visit(f.doc && f.doc.contents, 0, false);
    return out;
  }

  // ------------------------------------------------------------ DOM helper (text only)
  function h(tag, attrs) {
    const el = document.createElement(tag);
    if (attrs) {
      for (const k of Object.keys(attrs)) {
        const v = attrs[k];
        if (v === null || v === undefined || v === false) continue;
        if (k === 'class') el.className = v;
        else if (k.slice(0, 2) === 'on') el.addEventListener(k.slice(2), v);
        else el.setAttribute(k, v === true ? '' : String(v));
      }
    }
    for (let i = 2; i < arguments.length; i++) add(el, arguments[i]);
    return el;
  }
  function add(el, c) {
    if (c === null || c === undefined || c === false) return;
    if (Array.isArray(c)) { c.forEach((x) => add(el, x)); return; }
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  function code(t) { return h('code', null, String(t)); }

  // ------------------------------------------------------------ workspace
  // files: Map(name -> {name, text (as in the editor, LF), eol ('\n' | '\r\n'), bom, original, state (EditorState),
  //   doc (yaml Document), lc (LineCounter), value, yamlDiags, schemaDiags, lintDiags})
  const ws = { open: false, name: '', label: '', designRel: '', origin: '', profile: 'full', files: new Map(), active: null,
    rev: 0, lintRev: -1, registry: {}, diag: { byTarget: new Map(), list: [] } };
  const lint = { state: 'off', worker: null, pending: null, running: false, last: null, info: null, ms: null, timer: null, seq: 0, waiters: {} };
  let view = null;
  let checkTimer = null;

  function sortedNames() {
    const names = Array.from(ws.files.keys());
    const rank = (n) => { const i = FILE_ORDER.indexOf(n); return i >= 0 ? i : n === 'design.md' ? 99 : 50; };
    return names.sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
  }
  function safeDirName(s) { return String(s || 'design').replace(/[^A-Za-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '') || 'design'; }

  // ------------------------------------------------------------ file kinds
  function classify(name, text) {
    const base = name.split('/').pop();
    if (NAME_RE.test(base)) return base;
    if (/\.md$/i.test(base)) return null;
    let obj = null;
    try { obj = L.parseDocument(text, { schema: 'yaml-1.1', customTags: YAML_TAGS }).toJS({ maxAliasCount: 100 }); } catch (e) { return null; }
    if (!obj || typeof obj !== 'object') return null;
    if (Array.isArray(obj.claims)) return 'claims.yaml';
    if (Array.isArray(obj.token_types) || obj.issuance_profile) return 'token_types.yaml';
    if (Array.isArray(obj.hops)) return 'hops.yaml';
    if (Array.isArray(obj.answers)) return 'catalog_answers.yaml';
    return null;
  }
  function decode(buf) {
    const u = new Uint8Array(buf);
    const bom = u.length >= 3 && u[0] === 0xef && u[1] === 0xbb && u[2] === 0xbf;
    const text = new TextDecoder('utf-8', { fatal: false, ignoreBOM: false }).decode(u);
    return { text, bom };
  }
  function makeFile(name, raw, bom) {
    const eol = /\r\n/.test(raw) ? '\r\n' : '\n';
    const text = raw.replace(/\r\n?/g, '\n');
    const original = (bom ? '\ufeff' : '') + raw;
    return { name, text, eol, bom: !!bom, original, savedText: original, state: null, doc: null, lc: null, value: null,
      yamlDiags: [], schemaDiags: [], lintDiags: [], anchorDiags: [] };
  }
  function exportText(f) { const t = f.eol === '\r\n' ? f.text.replace(/\n/g, '\r\n') : f.text; return (f.bom ? '﻿' : '') + t; }

  // ------------------------------------------------------------ opening a workspace (the six entry points end here)
  // Every entry point ends here. Nothing is replaced silently (F1 of the PR #51 check): edits that were not written out
  // are offered for export first, and an autosaved version of the design being opened is offered instead of it.
  function openWorkspace(opts, entries, skipped) {
    return confirmReplace(opts, entries, '開く').then((c) => {
      if (c === 'cancel') return false;
      if (c && c.saved) return doOpen(Object.assign({}, c.saved, { origin: 'autosave', extras: opts.extras }), Object.keys(c.saved.files).map((n) => ({ name: n, text: c.saved.files[n] })), skipped);
      return doOpen(opts, entries, skipped);
    });
  }
  function doOpen(opts, entries, skipped) {
    closeWorkspace(true);
    status.note = '';
    saveWarning(null);
    ws.edited = false;
    ws.open = true;
    ws.name = opts.name;
    ws.label = opts.label || opts.name;
    ws.designRel = opts.designRel || 'work/' + safeDirName(opts.name);
    ws.origin = opts.origin;
    ws.profile = opts.profile || 'full';
    ws.files = new Map();
    entries.forEach((e) => ws.files.set(e.name, makeFile(e.name, e.text, e.bom)));
    ws.active = sortedNames()[0] || null;
    ws.rev++;
    $('#start').hidden = true;
    $('#split').hidden = false;
    $('#ws-bar').hidden = false;
    document.body.classList.add('ws-open');
    $('#ws-name').textContent = ws.label;
    $('#ws-name').title = `${ws.designRel}（${entries.length} ファイル）`;
    ensureView();
    ws.files.forEach((f) => { f.state = makeState(f); });
    view.setState(ws.active ? ws.files.get(ws.active).state : L.EditorState.create({ doc: '' }));
    renderTabs();
    layoutDefaults();
    // the first screen follows what was opened (#53): one file -> its screen, several -> the dashboard
    if (opts.route) history.replaceState(null, '', opts.route);  // 設計書をレビューする: the review stepper
    else if (!/^#\/[a-z]/.test(location.hash)) history.replaceState(null, '', firstRoute(entries, opts.extras || []));
    setMode(/^#\/review/.test(location.hash) ? 'review' : 'edit');
    runChecks(true);
    if (skipped && skipped.length) status(`開かなかったファイル：${skipped.join('、')}（設計書のファイル名でも、中身で見分けられる YAML でもない）`);
    if (lint.state === 'fresh' || lint.state === 'stale' || lint.state === 'running') scheduleLint(0);
    foreign.notes.clear(); renderForeign();
    // review.yaml found next to the design (a folder, files, a sample) goes to the review mode (#50)
    companions.forEach((c) => { if (c.onOpen) c.onOpen({ designRel: ws.designRel, origin: ws.origin, extras: opts.extras || [] }); });
    return true;
  }
  // what other parts (the review mode of #50) keep with the design: [{unsaved() -> bool, label, autosave() -> bool,
  // exportEntries() -> [{name, text}], markSaved(), onOpen(info), onClose()}]
  const companions = [];
  function filesUnsaved() {
    if (!ws.open) return false;
    for (const f of ws.files.values()) if (exportText(f) !== f.savedText) return true;
    return false;
  }
  function unsaved() { return ws.open && (filesUnsaved() || companions.some((c) => c.unsaved())); }
  function unsavedLabel() {
    const parts = [];
    if (filesUnsaved()) parts.push('設計書のファイル');
    companions.forEach((c) => { if (c.unsaved()) parts.push(c.label); });
    return parts.join('と');
  }
  function sameFiles(saved, entries) {
    const names = Object.keys(saved || {});
    return names.length === entries.length && entries.every((e) => saved[e.name] === (e.bom ? '\ufeff' : '') + e.text);
  }
  function confirmReplace(opts, entries, verb) {
    const steps = [];
    if (ws.open && unsaved()) {
      if (!keptByAutosave()) {  // kept in its own slot when the save succeeds
        steps.push(() => ask('書き出していない変更があります',
          `開いている「${ws.label}」には、書き出していない変更（${unsavedLabel()}）があります。${verb}と、その変更は消えます（自動保存は${autosaveEnabled() ? '有効ですが、保存できていません' : '無効です'}）。zip には ${companions.some((c) => c.unsaved()) ? 'review.yaml も' : '設計書のファイルを'}入れます。`,
          [['export', 'zip で書き出してから' + verb], ['discard', '書き出さずに' + verb + '（変更は消える）'], ['cancel', 'やめる']])
          .then((c) => {
            if (c !== 'export') return c === 'cancel' ? 'cancel' : null;
            // the review mode may ask what goes into the zip (#50: independent review); what is still not written out
            // after the export (another reviewer's records left out) is asked about again, not dropped
            return exportZip().then((done) => {
              if (!done) return 'cancel';
              if (!unsaved()) return null;
              return ask('まだ書き出していない記録があります', `zip に入れなかった変更（${unsavedLabel()}）が残っています。${verb}と、それは消えます。`,
                [['cancel', 'やめる'], ['discard', '書き出さずに' + verb + '（残りは消える）']]).then((c2) => (c2 === 'discard' ? null : 'cancel'));
            });
          }));
      }
    }
    if (opts && opts.origin !== 'autosave') {
      const rel = opts.designRel || 'work/' + safeDirName(opts.name);
      const sv = slot(rel);
      if (sv && !sameFiles(sv.files, entries)) {
        steps.push(() => ask('自動保存した版があります',
          `いま開こうとしている設計書（${opts.label || rel}、保存先 ${rel}）には、このブラウザに自動保存した版（${sv.label || sv.name}、${sv.savedAt} に保存）があります。「元のファイルを開く」で開いて編集すると、自動保存した版は上書きされます。`,
          [['saved', '自動保存した版を開く'], ['original', '元のファイルを開く'], ['cancel', 'やめる']])
          .then((c) => (c === 'cancel' ? 'cancel' : c === 'saved' ? { saved: sv } : null)));
      }
    }
    let p = Promise.resolve(null);
    steps.forEach((st) => { p = p.then((r) => (r ? r : st())); });
    return p.then((r) => r || 'ok');
  }
  // an in-page dialog (not window.confirm): resolves with the key of the button, 'cancel' on Esc
  function ask(title, text, buttons) {
    return new Promise((resolve) => {
      const d = h('dialog', { class: 'confirm', id: 'confirm', 'aria-labelledby': 'confirm-title', 'aria-describedby': 'confirm-text' },
        h('h2', { id: 'confirm-title' }, title), h('p', { id: 'confirm-text' }, text),
        h('p', { class: 'buttons' }, buttons.map(([k, label], i) => h('button', { type: 'button', 'data-choice': k, class: i === 0 ? 'primary' : null,
          onclick: () => { d.close(k); } }, label))));
      d.addEventListener('close', () => { const v = d.returnValue || 'cancel'; d.remove(); resolve(v); });
      document.body.append(d);
      d.showModal();
    });
  }
  function requestClose() {
    return confirmReplace(null, [], '閉じる').then((c) => { if (c !== 'cancel') closeWorkspace(false); });
  }
  function closeWorkspace(silent) {
    if (ws.open) companions.forEach((c) => { if (c.onClose) c.onClose(); });
    foreign.notes.clear();
    if ($('#tab-warn')) renderForeign();
    ws.open = false;
    ws.files = new Map();
    ws.registry = {};
    ws.diag = { byTarget: new Map(), list: [] };
    lint.last = null;
    if (lint.state === 'fresh' || lint.state === 'stale') lint.state = 'stale';
    if (!silent) {
      $('#split').hidden = true;
      $('#ws-bar').hidden = true;
      document.body.classList.remove('ws-open');
      setMode('edit');
      modes.last = { edit: '#/dashboard', review: '#/review' };
      P.clear();
      history.replaceState(null, '', '#/');
      renderStart(true);
    }
  }
  function entriesFromFiles(list) {
    // list: [{name, path, buf}] -> design files; a folder is read from the directory that holds claims.yaml (or the top)
    const byDir = new Map();
    list.forEach((x) => { const dir = x.path.includes('/') ? x.path.slice(0, x.path.lastIndexOf('/')) : ''; if (!byDir.has(dir)) byDir.set(dir, []); byDir.get(dir).push(x); });
    let dir = '';
    if (byDir.size > 1) {
      const withClaims = Array.from(byDir.keys()).filter((d) => byDir.get(d).some((x) => x.name === 'claims.yaml'));
      dir = withClaims.sort((a, b) => a.split('/').length - b.split('/').length)[0];
      if (dir === undefined) dir = Array.from(byDir.keys()).sort((a, b) => a.split('/').length - b.split('/').length)[0];
    } else dir = Array.from(byDir.keys())[0] || '';
    const out = []; const skipped = []; const seen = new Set(); const extras = [];
    for (const x of byDir.get(dir) || []) {
      const { text, bom } = decode(x.buf);
      if (/^review(?:[._-][A-Za-z0-9_.-]*)?\.ya?ml$/.test(x.name)) { extras.push({ name: x.name, text }); continue; }  // #50
      const kind = classify(x.name, text);
      if (!kind || seen.has(kind)) { skipped.push(x.name); continue; }
      seen.add(kind);
      out.push({ name: kind, text, bom, from: x.name });
    }
    return { out, skipped, dir, extras };
  }
  function readFileList(fileList, origin, route) {
    const arr = Array.from(fileList || []);
    if (!arr.length) return Promise.resolve(false);
    return Promise.all(arr.map((f) => f.arrayBuffer().then((buf) => ({ name: f.name, path: (f.webkitRelativePath || f.name).replace(/\\/g, '/'), buf }))))
      .then((list) => openList(list, origin, route));
  }
  function openList(list, origin, route) {
    const { out, skipped, dir, extras } = entriesFromFiles(list);
    // review.yaml alone (#53): the review records of a design whose files are added afterwards
    const review = extras.find((e) => /^review\.ya?ml$/.test(e.name));
    if (!out.length && review) {
      let design = '';
      try { const v = parseYaml(review.text); design = v && typeof v.design === 'string' ? v.design : ''; } catch (e) { /* the review mode says what is wrong */ }
      const nm = design ? design.split('/').pop() : uniqueName('review');
      return openWorkspace({ name: nm, label: `レビューの記録（${review.name}${design ? '、' + design : ''}、${stamp().label}）`, designRel: design || undefined, origin, extras, route }, [], skipped);
    }
    if (!out.length) { status('開けるファイルがありません（claims.yaml・token_types.yaml・hops.yaml・catalog_answers.yaml・claim_request_*.md・design.md、または中身で見分けられる YAML）。'); return false; }
    const how = origin === 'folder' ? 'フォルダ' : origin === 'drop' ? 'ドロップ' : 'ファイル';
    // a folder names the design; files without a folder get a name of their own (their autosave slot is not shared)
    let name = dir ? dir.split('/').pop() : uniqueName(origin === 'drop' ? 'dropped' : 'files');
    // files chosen without their folder, with a review.yaml: the design is the one the review is of (#53)
    let designRel;
    if (!dir && review) {
      try { const v = parseYaml(review.text); if (v && typeof v.design === 'string' && v.design) { designRel = v.design; name = v.design.split('/').pop(); } } catch (e) { /* the review mode says what is wrong */ }
    }
    return openWorkspace({ name, label: (dir ? dir.split('/').pop() : '開いたファイル（' + out.map((e) => e.from).join('・') + '）') + `（${how}、${stamp().label}）`, designRel, origin, extras, route }, out, skipped);
  }
  function stamp() {
    const d = new Date();
    const p = (n) => String(n).padStart(2, '0');
    return { id: `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`,
      label: `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())} に開いた` };
  }
  function uniqueName(base) {
    const r = new Uint8Array(3);
    crypto.getRandomValues(r);
    return `${base}-${stamp().id}-${Array.from(r).map((x) => x.toString(16).padStart(2, '0')).join('')}`;
  }
  function loadScript(src, key) {
    if (DATA[key]) return Promise.resolve(DATA[key]);
    return new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = asset(src);
      s.onload = () => {
        // a file of another build (the server has a newer one than this page): not used (#53)
        if (BUILDS[src] !== BUILD_ID) { buildBanner([src]); delete DATA[key]; reject(new Error(src + ' は別の版です。再読み込みしてください。')); return; }
        if (DATA[key]) resolve(DATA[key]); else reject(new Error('no data in ' + src));
      };
      s.onerror = () => reject(new Error(src + ' を読めません'));
      document.head.append(s);
    });
  }
  function openSample(letter) {
    return loadScript(`data/sample-${letter}.js`, 'sample-' + letter).then((s) => openWorkspace(
      { name: s.id, label: s.label, designRel: s.design, origin: 'sample', profile: s.profile, extras: s.review ? [{ name: 'review.yaml', text: s.review }] : [] },
      Object.keys(s.files).map((n) => ({ name: n, text: s.files[n] }))));
  }
  function openSkeleton() {
    return loadScript('data/skeleton.js', 'skeleton').then((s) => openWorkspace(
      { name: s.dir, label: '空の雛形（' + s.dir + '）', origin: 'skeleton', profile: 'lite' },
      Object.keys(s.files).map((n) => ({ name: n, text: s.files[n] }))));
  }
  function openPaste(text, kindSel) {
    const kind = kindSel || classify('pasted.yaml', text);
    if (!kind) { status('貼り付けた内容が何のファイルか分かりません。種類を選んでください。'); return false; }
    return openWorkspace({ name: uniqueName('pasted'), label: `貼り付けた内容（${kind}、${stamp().label}）`, origin: 'paste' }, [{ name: kind, text }]);
  }
  // drag and drop: files, or folders (webkitGetAsEntry)
  function readEntry(entry, path) {
    return new Promise((resolve) => {
      if (entry.isFile) entry.file((f) => f.arrayBuffer().then((buf) => resolve([{ name: f.name, path: path + f.name, buf }])), () => resolve([]));
      else if (entry.isDirectory) {
        const r = entry.createReader(); const all = [];
        const next = () => r.readEntries((es) => {
          if (!es.length) { Promise.all(all.map((e) => readEntry(e, path + entry.name + '/'))).then((xs) => resolve([].concat(...xs))); return; }
          all.push(...es); next();
        }, () => resolve([]));
        next();
      } else resolve([]);
    });
  }
  function onDrop(e) {
    e.preventDefault();
    $('#drop-overlay').hidden = true;
    const items = Array.from((e.dataTransfer && e.dataTransfer.items) || []);
    const entries = items.map((i) => (i.webkitGetAsEntry ? i.webkitGetAsEntry() : null)).filter(Boolean);
    if (entries.length) Promise.all(entries.map((en) => readEntry(en, ''))).then((xs) => openList([].concat(...xs), 'drop'));
    else readFileList(e.dataTransfer && e.dataTransfer.files, 'drop');
  }

  // ------------------------------------------------------------ the start screen (nothing open)
  function slot(rel) {
    try { const raw = localStorage.getItem(AUTOSAVE_PREFIX + rel); return raw ? JSON.parse(raw) : null; } catch (e) { return null; }
  }
  function slots() {
    const out = [];
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (k && k.startsWith(AUTOSAVE_PREFIX)) { const v = slot(k.slice(AUTOSAVE_PREFIX.length)); if (v && v.files) out.push(v); }
      }
    } catch (e) { /* storage unavailable */ }
    return out.sort((a, b) => String(b.savedAt).localeCompare(String(a.savedAt)));
  }
  function autosaveEnabled() { try { return localStorage.getItem(AUTOSAVE_ON) === '1'; } catch (e) { return false; } }
  // a sample or the skeleton that cannot be loaded (offline, a file of another build) is said on the start screen
  function startFrom(p) {
    return Promise.resolve(p).catch((e) => { const m = $('#start-msg'); if (m) m.textContent = String((e && e.message) || e); return false; });
  }
  function renderStart(focus) {
    const st = $('#start');
    st.textContent = '';
    st.hidden = false;
    // the file inputs are pressed through the buttons only: out of the tab order and hidden from assistive technology
    const files = h('input', { type: 'file', id: 'in-files', multiple: true, accept: '.yaml,.yml,.md,text/yaml,text/markdown', class: 'vh', tabindex: '-1', 'aria-hidden': 'true' });
    const folder = h('input', { type: 'file', id: 'in-folder', webkitdirectory: true, directory: true, multiple: true, class: 'vh', tabindex: '-1', 'aria-hidden': 'true' });
    files.addEventListener('change', () => readFileList(files.files, 'files'));
    folder.addEventListener('change', () => readFileList(folder.files, 'folder'));
    const pasteArea = h('textarea', { id: 'paste-text', rows: '8', spellcheck: 'false', 'aria-label': '貼り付ける YAML' });
    const pasteKind = h('select', { id: 'paste-kind', 'aria-label': 'ファイルの種類' }, h('option', { value: '' }, '中身から見分ける'),
      FILE_ORDER.map((n) => h('option', { value: n }, n)));
    const paste = h('div', { class: 'paste', id: 'paste-box', hidden: true },
      h('p', null, 'YAML を貼り付けて「開く」を押します（1 つのファイル）。'), pasteArea,
      h('p', null, h('label', null, 'ファイルの種類：', pasteKind), ' ', h('button', { type: 'button', class: 'primary', id: 'paste-open', onclick: () => openPaste(pasteArea.value, pasteKind.value) }, '開く')));
    const card = (id, title, desc, onclick, extra) => h('li', null, h('button', { type: 'button', class: 'entry', id, onclick }, h('strong', null, title), h('span', null, desc)), extra || null);
    const saved = slots();
    // 設計書をレビューする: files or a folder (review.yaml with the design files), then straight to the review stepper
    const rvFiles = h('input', { type: 'file', id: 'in-review-files', multiple: true, accept: '.yaml,.yml,.md,text/yaml,text/markdown', class: 'vh', tabindex: '-1', 'aria-hidden': 'true' });
    const rvFolder = h('input', { type: 'file', id: 'in-review-folder', webkitdirectory: true, directory: true, multiple: true, class: 'vh', tabindex: '-1', 'aria-hidden': 'true' });
    rvFiles.addEventListener('change', () => readFileList(rvFiles.files, 'files', '#/review'));
    rvFolder.addEventListener('change', () => readFileList(rvFolder.files, 'folder', '#/review'));
    const restore = (sv) => openWorkspace(Object.assign({}, sv, { origin: 'autosave' }), Object.keys(sv.files).map((n) => ({ name: n, text: sv.files[n] })));
    st.append(h('div', { class: 'start-in' },
      h('h1', { tabindex: '-1' }, '設計書のエディター'),
      h('p', { class: 'lead' }, 'YAML の設計書を開いて、見る・直す・レビューする。下のどれかで始めてください。'),
      h('p', { id: 'start-msg', class: 'err', role: 'status' }),
      // like the recent files of an editor: the designs autosaved in this browser come first
      saved.length ? h('section', { class: 'recent', id: 'autosave-box', 'aria-labelledby': 'recent-h' }, h('h2', { id: 'recent-h' }, '続きから開く'),
        h('p', { class: 'muted small' }, `このブラウザに自動保存した設計書（${saved.length} 件、設計書のディレクトリごとに 1 件）`),
        h('ul', { class: 'recent-list' }, saved.map((sv) => h('li', { 'data-slot': sv.designRel },
          h('button', { type: 'button', class: 'entry', 'data-restore': sv.designRel, onclick: () => restore(sv) }, h('strong', null, sv.label || sv.name), h('span', null, sv.designRel, `（${sv.savedAt} に保存）`)),
          h('button', { type: 'button', class: 'link small', 'data-forget': sv.designRel, 'aria-label': `${sv.designRel} の自動保存を消す`, onclick: () => ask('自動保存を消す', `${sv.designRel} の自動保存を消します。`, [['delete', '消す'], ['cancel', 'やめる']])
            .then((c) => { if (c === 'delete') { try { localStorage.removeItem(AUTOSAVE_PREFIX + sv.designRel); } catch (e) { /* ignore */ } renderStart(); } }) }, '消す'))))) : null,
      h('ul', { class: 'entries' },
        card('btn-open-files', 'ファイルを開く', '複数の YAML・Markdown を選ぶ', () => files.click(), files),
        card('btn-open-folder', 'フォルダを開く', '設計書のディレクトリを選ぶ（claims.yaml のあるフォルダを読む）', () => folder.click(), folder),
        h('li', null, h('div', { class: 'entry static', id: 'drop-hint' }, h('strong', null, 'ドラッグ＆ドロップ'), h('span', null, 'ファイルかフォルダを、このページのどこかにドロップする'))),
        h('li', null, h('button', { type: 'button', class: 'entry review', id: 'btn-review', onclick: () => rvFiles.click() }, h('strong', null, '設計書をレビューする'),
          h('span', null, '設計書のファイルと review.yaml（あれば）を選び、レビューの手順へ進む')), rvFiles,
          h('button', { type: 'button', class: 'link small', id: 'btn-review-folder', onclick: () => rvFolder.click() }, 'フォルダで選ぶ'), rvFolder),
        card('btn-paste', '貼り付け', 'YAML を貼り付けて開く', () => { paste.hidden = false; pasteArea.focus(); }),
        card('btn-skeleton', '空の雛形から始める', 'tools/new_design.py と同じ骨組み（記入例の理由は写さない）', () => startFrom(openSkeleton())),
        card('btn-sample-a', 'サンプルを開く：シナリオ A', 'マルチテナント SaaS（Lite）。templates/examples/scenario-a', () => startFrom(openSample('a'))),
        card('btn-sample-b', 'サンプルを開く：シナリオ B', '社内の業務システムと AI エージェント（Full）、レビューの記録つき。templates/examples/scenario-b', () => startFrom(openSample('b')))),
      paste,
      h('div', { class: 'note', id: 'start-note' }, h('p', null, h('strong', null, '開いたファイルはどこにも送りません。'), '読み込みも検査（JSON Schema と claim_lint）もブラウザの中で行います。'),
        h('details', { id: 'start-more' }, h('summary', null, '詳しく'),
          h('ul', null,
            h('li', null, '1 つのファイルを開くとその画面、いくつか開くとダッシュボード（件数・検査の結果・要対応）が出ます。左のエディターで直すと、右の画面と検査の結果がすぐ変わります。'),
            h('li', null, 'レビューは、上のバーの「レビュー」に切り替えて始めます（review.yaml があれば一緒に開く）。'),
            h('li', null, 'claim_lint は Pyodide で動く Python です。初めて使うときに、このサイトから約 13 MB を読み込みます。CSP で、このサイト以外への接続を禁じています。自動保存は、上のバーで有効にしたときだけ、このブラウザの localStorage に保存します。'),
            h('li', null, 'キーボード：', h('kbd', null, 'Tab'), ' で移動、', h('kbd', null, 'Enter'), ' で押す。エディターの中の ', h('kbd', null, 'Tab'), ' はエディターから次へ移る（Tab ではインデントしない。インデントは空白で入れるか、行を選んで ', h('kbd', null, 'Ctrl'), '+', h('kbd', null, ']'), '・', h('kbd', null, 'Ctrl'), '+', h('kbd', null, '['), '）。', h('kbd', null, 'Ctrl'), '+', h('kbd', null, 'Shift'), '+', h('kbd', null, 'M'), ' で指摘の一覧、', h('kbd', null, 'F8'), ' で次の指摘。'))))));
    if (focus) st.querySelector('h1').focus();
  }

  // ------------------------------------------------------------ CodeMirror
  const langComp = new L.Compartment();
  function extensions(f) {
    return [
      L.lineNumbers(), L.highlightActiveLineGutter(), L.foldGutter(), L.history(), L.drawSelection(), L.highlightActiveLine(), L.EditorView.lineWrapping,
      L.indentOnInput(), L.bracketMatching(), L.highlightSelectionMatches(), L.syntaxHighlighting(L.defaultHighlightStyle, { fallback: true }),
      L.indentUnit.of('  '), L.EditorState.tabSize.of(2),
      L.keymap.of([].concat(L.defaultKeymap, L.historyKeymap, L.foldKeymap, L.searchKeymap, L.lintKeymap,
        [{ key: 'Mod-s', preventDefault: true, run: () => { exportOne(); return true; } }])),
      L.search({ top: true }), L.lintGutter(), THEME,
      langComp.of(/\.ya?ml$/.test(f.name) ? L.yamlLanguage() : []),
      L.EditorView.contentAttributes.of({ 'aria-label': `${f.name} の内容（YAML のエディター）` }),
      L.EditorView.updateListener.of((u) => { if (u.docChanged) onEdit(f.name, u.state); }),
    ];
  }
  function makeState(f) { return L.EditorState.create({ doc: f.text, extensions: extensions(f) }); }
  // The editor lives in a shadow root: CodeMirror's styles then go to a constructed stylesheet (adoptedStyleSheets),
  // which the page CSP (style-src 'self', no 'unsafe-inline') allows, instead of a <style> element, which it blocks.
  function ensureView() {
    if (view) return;
    const host = $('#editor');
    const shadow = host.attachShadow({ mode: 'open' });
    const sheet = new CSSStyleSheet();
    sheet.replaceSync(':host{display:block;height:100%;min-height:0} .wrap{height:100%}');
    shadow.adoptedStyleSheets = [sheet];
    const wrap = document.createElement('div');
    wrap.className = 'wrap';
    shadow.append(wrap);
    view = new L.EditorView({ parent: wrap, root: shadow, state: L.EditorState.create({ doc: '' }) });
  }
  const THEME = L.EditorView.theme({
    '&': { height: '100%', fontSize: '13px', backgroundColor: 'var(--panel)', color: 'var(--ink)' },
    '.cm-scroller': { fontFamily: 'var(--mono)', lineHeight: '1.5' },
    '.cm-gutters': { backgroundColor: 'var(--soft)', color: 'var(--muted)', borderRight: '1px solid var(--line)' },
    '.cm-activeLine': { backgroundColor: 'rgba(127,127,127,.08)' },
    '.cm-activeLineGutter': { backgroundColor: 'rgba(127,127,127,.16)' },
    '&.cm-focused': { outline: '2px solid var(--focus)', outlineOffset: '-2px' },
    '.cm-content': { caretColor: 'var(--ink)' },
    '&.cm-focused .cm-cursor': { borderLeftColor: 'var(--ink)' },
    '.cm-tooltip': { backgroundColor: 'var(--panel)', color: 'var(--ink)', border: '1px solid var(--line)' },
    '.cm-panels': { backgroundColor: 'var(--soft)', color: 'var(--ink)' },
    '.cm-diagnostic': { whiteSpace: 'pre-wrap' },
  });
  function switchTo(name, line) {
    const f = ws.files.get(name);
    if (!f) return;
    if (ws.active && ws.files.get(ws.active)) ws.files.get(ws.active).state = view.state;
    ws.active = name;
    view.setState(f.state);
    applyDiagnostics(f);
    renderTabs();
    if (line) {
      if (panes.editor === false) setPane('editor', true);  // a jump to a line opens the folded editor (#53)
      const ln = Math.max(1, Math.min(line, view.state.doc.lines));
      const pos = view.state.doc.line(ln).from;
      view.dispatch({ selection: { anchor: pos }, effects: L.EditorView.scrollIntoView(pos, { y: 'center' }) });
      view.focus();
    }
  }
  function onEdit(name, state) {
    const f = ws.files.get(name);
    if (!f) return;
    f.state = state;
    f.text = state.doc.toString();
    ws.rev++;
    ws.edited = true;
    if (lint.state === 'fresh') lint.state = 'stale';
    clearTimeout(checkTimer);
    checkTimer = setTimeout(() => runChecks(false), DEBOUNCE_CHECK);
    autosaveSoon();
  }

  // ------------------------------------------------------------ tabs
  function renderTabs() {
    const bar = $('#tabs');
    bar.textContent = '';
    const names = sortedNames();
    names.forEach((n, i) => {
      const f = ws.files.get(n);
      const ds = diagsOf(f);
      const cnt = { error: 0, warn: 0, info: 0 };
      ds.forEach((d) => { cnt[d.severity]++; });
      const changed = exportText(f) !== f.original;
      // a tab: the file name, then the counts as symbols for the eye and as words for a screen reader
      const b = h('button', { type: 'button', role: 'tab', id: 'tab-' + n, 'data-file': n, 'aria-selected': n === ws.active ? 'true' : 'false',
        'aria-controls': 'editor', tabindex: n === ws.active ? '0' : '-1', title: (FILE_LABEL[n] || (n.startsWith('claim_request_') ? 'クレームの追加の申請' : '')) + (changed ? '（変更あり）' : ''),
        onclick: () => switchTo(n) },
      n, changed ? [h('span', { class: 'dirty', 'aria-hidden': 'true' }, ' ●'), h('span', { class: 'vh' }, '（変更あり）')] : null,
      cnt.error ? [h('span', { class: 'tb ng', 'aria-hidden': 'true' }, ' ✖' + cnt.error), h('span', { class: 'vh' }, `（エラー ${cnt.error} 件）`)] : null,
      cnt.warn ? [h('span', { class: 'tb warn', 'aria-hidden': 'true' }, ' ▲' + cnt.warn), h('span', { class: 'vh' }, `（警告 ${cnt.warn} 件）`)] : null);
      b.addEventListener('keydown', (e) => {
        const keys = { ArrowRight: i + 1, ArrowLeft: i - 1 + names.length, Home: 0, End: names.length - 1 };
        if (!(e.key in keys)) return;
        e.preventDefault();
        const j = keys[e.key] % names.length;
        switchTo(names[j]);
        $('#tab-' + CSS.escape(names[j])).focus();
      });
      bar.append(b);
    });
    if (ws.active) $('#editor').setAttribute('aria-labelledby', 'tab-' + ws.active); else $('#editor').removeAttribute('aria-labelledby');
    // outside the tablist: the button that adds files (its file input is out of the tab order)
    const tools = $('#tab-tools');
    tools.textContent = '';
    const addIn = h('input', { type: 'file', multiple: true, accept: '.yaml,.yml,.md', class: 'vh', id: 'in-add', tabindex: '-1', 'aria-hidden': 'true' });
    addIn.addEventListener('change', () => addFiles(addIn.files));
    tools.append(h('button', { type: 'button', class: 'addfile', id: 'btn-add-file', title: 'ファイルを足す（同じ名前なら置き換える）', onclick: () => addIn.click() }, '＋ ファイルを足す'), addIn);
    if (!names.length) tools.append(' ', h('span', { class: 'muted small', id: 'tabs-empty' }, '設計書のファイルがまだありません。'));
  }
  // a name that is free: claim_request_x.md -> claim_request_x_2.md (still a design file); claims.yaml -> claims.2.yaml
  // (kept and editable, but not one of the design's files: the checks and claim_lint read claims.yaml only)
  function freeName(n) {
    for (let i = 2; ; i++) {
      const m = /^(claim_request_[A-Za-z0-9_-]+)\.md$/.exec(n);
      const cand = m ? `${m[1]}_${i}.md` : n.replace(/(\.[a-z]+)$/, `.${i}$1`);
      if (!ws.files.has(cand)) return cand;
    }
  }
  function addFiles(list) {
    return Promise.all(Array.from(list || []).map((f) => f.arrayBuffer().then((buf) => ({ name: f.name, path: f.name, buf })))).then((xs) => {
      const { out, skipped, extras } = entriesFromFiles(xs);
      if (skipped.length) status('開かなかったファイル：' + skipped.join('、'));
      if (extras.length) companions.forEach((c) => { if (c.onExtras) c.onExtras(extras); });  // review.yaml (#50)
      let p = Promise.resolve();
      const added = [];
      out.forEach((e) => {
        p = p.then(() => {
          if (!ws.files.has(e.name)) return e.name;
          const cur = ws.files.get(e.name);
          const dirty = exportText(cur) !== cur.savedText;
          const alt = freeName(e.name);
          return ask('同じ名前のファイルがあります',
            `「${e.from}」を足そうとしています。開いている ${e.name} ${dirty ? 'には書き出していない変更があり、' : 'は'}置き換えると今の中身は消えます。`,
            [['replace', `${e.name} を置き換える`], ['both', `両方残す（足すほうを ${alt} にする）`], ['cancel', 'やめる']])
            .then((c) => (c === 'replace' ? e.name : c === 'both' ? alt : null));
        }).then((name) => {
          if (!name) return;
          const f = makeFile(name, e.text, e.bom);
          f.savedText = '';  // not written out yet under this name
          f.state = makeState(f);
          ws.files.set(name, f);
          added.push(name);
        });
      });
      return p.then(() => {
        if (added.length) { ws.rev++; ws.edited = true; switchTo(added[0]); runChecks(true); autosaveSoon(); }
        return added;
      });
    });
  }

  // ------------------------------------------------------------ checks: YAML, JSON Schema (at once), claim_lint (Pyodide)
  const validators = {};
  // The registry schemas are written for Python's jsonschema (re): a pattern may start with the inline flag (?i), which
  // a JavaScript RegExp does not accept. It is rewritten to the same pattern with each ASCII letter as [xX].
  function jsPattern(p) {
    if (!/^\(\?i\)/.test(p)) return p;
    let out = ''; let esc = false; let cls = false;
    for (const ch of p.slice(4)) {
      if (esc) { out += ch; esc = false; continue; }
      if (ch === '\\') { out += ch; esc = true; continue; }
      if (ch === '[') cls = true;
      else if (ch === ']') cls = false;
      if (/[A-Za-z]/.test(ch)) {
        if (cls) throw new Error('(?i) with letters inside a character class: ' + p);
        out += '[' + ch.toLowerCase() + ch.toUpperCase() + ']';
      } else out += ch;
    }
    return out;
  }
  function jsSchema(node) {
    if (Array.isArray(node)) return node.map(jsSchema);
    if (!node || typeof node !== 'object') return node;
    const out = {};
    Object.keys(node).forEach((k) => { out[k] = k === 'pattern' && typeof node[k] === 'string' ? jsPattern(node[k]) : jsSchema(node[k]); });
    return out;
  }
  function validator(kind) {
    if (!SCHEMAS || !SCHEMAS[kind]) return null;
    if (!validators[kind]) validators[kind] = new L.Validator(jsSchema(SCHEMAS[kind]), '2020-12', false);
    return validators[kind];
  }
  function parseFile(f) {
    f.lc = new L.LineCounter();
    f.yamlDiags = [];
    f.doc = null; f.value = null;
    if (!/\.ya?ml$/.test(f.name)) return;
    try {
      f.doc = L.parseDocument(f.text, { lineCounter: f.lc, schema: 'yaml-1.1', customTags: YAML_TAGS, uniqueKeys: true, prettyErrors: true });
      f.doc.errors.forEach((e) => {
        const line = e.linePos && e.linePos[0] ? e.linePos[0].line : 1;
        f.yamlDiags.push({ source: 'yaml', severity: 'error', rule: 'YAML', file: f.name, line, target: f.name.replace(/\.yaml$/, ''),
          message: 'YAML の誤り：' + String(e.message).split('\n')[0] });
      });
      if (!f.doc.errors.length) f.value = f.doc.toJS({ maxAliasCount: 100 });
      f.yamlDiags.push(...yaml11Diags(f));
    } catch (e) {
      f.yamlDiags.push({ source: 'yaml', severity: 'error', rule: 'YAML', file: f.name, line: 1, target: f.name, message: 'YAML の誤り：' + (e.message || e) });
    }
  }
  function decodePointer(p) {
    return String(p || '').replace(/^#/, '').split('/').slice(1).map((s) => { try { return decodeURIComponent(s); } catch (e) { return s; } }).map((s) => s.replace(/~1/g, '/').replace(/~0/g, '~'));
  }
  const WRAPPERS = new Set(['properties', 'items', 'prefixItems', '$ref', 'allOf', 'if', 'then', 'else', 'false', 'contains', 'dependentSchemas',
    'propertyNames', 'patternProperties', 'unevaluatedProperties', 'unevaluatedItems', '$dynamicRef']);
  function jaSchemaMessage(e) {
    const m = String(e.error);
    let x;
    if ((x = /does not have required property "([^"]+)"/.exec(m))) return `必須の項目 ${x[1]} がない`;
    if ((x = /^Instance type "([^"]+)" is invalid\. Expected "([^"]+)"/.exec(m))) return `型が違う（${x[1]}。スキーマは ${x[2]}）`;
    if ((x = /^Property "([^"]+)" does not match additional properties schema/.exec(m))) return `スキーマにない項目 ${x[1]}`;
    if (e.keyword === 'enum') return '値が選択肢（enum）にない';
    if (e.keyword === 'const') return '値が決まった値（const）と違う';
    if (e.keyword === 'anyOf') return 'どの書き方（anyOf）にも合わない';
    if (e.keyword === 'oneOf') return '書き方（oneOf）のちょうど 1 つに合わない';
    if (e.keyword === 'pattern') return '書式（pattern）に合わない';
    if (e.keyword === 'minLength') return '短すぎる（minLength）';
    if (e.keyword === 'minItems') return '要素が足りない（minItems）';
    if (e.keyword === 'uniqueItems') return '要素が重複している（uniqueItems）';
    return m;
  }
  function schemaCheck(f, kind) {
    f.schemaDiags = [];
    let v = null;
    try { v = validator(kind); } catch (e) { v = null; }
    if (!v || f.value === null || f.value === undefined) return;
    let res;
    try { res = v.validate(f.value); } catch (e) {
      f.schemaDiags.push({ source: 'schema', severity: 'info', rule: 'SCHEMA', file: f.name, line: 1, path: [], target: kind,
        message: 'ブラウザの JSON Schema の検査を実行できませんでした（' + (e.message || e) + '）。claim_lint の SCHEMA の結果を見てください。' });
      return;
    }
    if (res.valid) return;
    const seen = new Set();
    res.errors.forEach((e) => {
      if (WRAPPERS.has(e.keyword)) return;
      if (/\/(anyOf|oneOf)\/\d+\//.test(e.keywordLocation)) return;  // the reasons of each alternative: the anyOf error says it
      const path = decodePointer(e.instanceLocation);
      const msg = jaSchemaMessage(e);
      const key = path.join('/') + '|' + msg;
      if (seen.has(key)) return;
      seen.add(key);
      const loc = locate(f, path);
      const anchor = anchorOfPath(kind, path);
      f.schemaDiags.push({ source: 'schema', severity: 'error', rule: 'SCHEMA', file: f.name, line: loc, path,
        target: `${kind}:${path.join('/') || '(root)'}`, anchorKind: anchor && anchor[0], anchorId: anchor && anchor[1],
        message: `${msg}（${path.join('/') || '(root)'}；${e.keyword}）` });
    });
  }
  // the line of a YAML path (keys and list indexes) in a parsed file; the deepest node found
  function locate(f, path) {
    if (!f || !f.doc || !f.lc) return 1;
    let node = f.doc.contents;
    let pos = node && node.range ? node.range[0] : 0;
    for (const seg of path) {
      if (L.isMap(node)) {
        const pair = node.items.find((p) => p.key && String(L.isScalar(p.key) ? p.key.value : p.key) === String(seg));
        if (!pair) break;
        if (pair.key && pair.key.range) pos = pair.key.range[0];
        node = pair.value;
      } else if (L.isSeq(node)) {
        const it = node.items[Number(seg)];
        if (!it) break;
        node = it;
        if (it.range) pos = it.range[0];
      } else break;
    }
    return f.lc.linePos(pos).line;
  }
  function rowList(kind) {
    const r = ROWS[kind];
    const f = r && ws.files.get(r[0]);
    const v = f && f.value;
    return v && typeof v === 'object' && Array.isArray(v[r[1]]) ? v[r[1]] : [];
  }
  function anchorOfPath(kind, path) {
    const r = ROWS[kind];
    if (r && path[0] === r[1] && path.length > 1) {
      const row = rowList(kind)[Number(path[1])];
      if (row && typeof row === 'object' && row[r[2]] !== undefined) return [kind, String(row[r[2]])];
    }
    if (kind === 'token_types' && path[0] === 'issuance_profile' && path[1]) return ['issuance_profile', path[1]];
    return null;
  }
  // where a claim_lint finding points: a file and a line, and the row (anchor) it is about
  function resolveTarget(target) {
    const t = String(target || '');
    let m = /^(claims|token_types|hops|catalog_answers):(.*)$/.exec(t);
    if (m) {
      const path = m[2] === '(root)' || m[2] === '' ? [] : m[2].split('/');
      const a = anchorOfPath(m[1], path);
      return { file: m[1] + '.yaml', path, anchor: a };
    }
    m = /^(token_type|hop) (.+)$/.exec(t);
    const id = m ? m[2] : t;
    const order = m ? [m[1] === 'hop' ? 'hops' : 'token_types'] : ['claims', 'token_types', 'hops', 'catalog_answers'];
    for (const kind of order) {
      const r = ROWS[kind];
      const i = rowList(kind).findIndex((x) => x && typeof x === 'object' && String(x[r[2]]) === id);
      if (i >= 0) return { file: r[0], path: [r[1], String(i)], anchor: [kind, id] };
    }
    const tops = [['catalog_answers.yaml', []], ['token_types.yaml', ['issuance_profile']], ['token_types.yaml', []], ['claims.yaml', []], ['hops.yaml', []]];
    for (const [file, pre] of tops) {
      const f = ws.files.get(file);
      let v = f && f.value;
      pre.forEach((k) => { v = v && typeof v === 'object' ? v[k] : undefined; });
      if (v && typeof v === 'object' && !Array.isArray(v) && own(v, id)) {
        return { file, path: pre.concat([id]), anchor: pre.length ? ['issuance_profile', id] : null };
      }
    }
    const base = t.split('/').pop();
    if (ws.files.has(base)) return { file: base, path: [], anchor: null };
    return { file: null, path: [], anchor: null };
  }
  function lintDiagnostics(result) {
    const out = [];
    ((result && result.findings) || []).forEach((x) => {
      const r = resolveTarget(x.target);
      const f = r.file ? ws.files.get(r.file) : null;
      let line = f ? locate(f, r.path) : null;
      const lm = /^(?:.*\/)?([^/:]+\.md):(\d+)/.exec(String(x.message));  // a slide reference in design.md: file:line
      if (lm && ws.files.has(lm[1])) { line = Number(lm[2]); r.file = lm[1]; }
      out.push({ source: 'claim_lint', severity: x.severity, rule: x.rule, message: x.message, target: x.target, file: r.file, line,
        anchorKind: r.anchor && r.anchor[0], anchorId: r.anchor && r.anchor[1] });
    });
    return out;
  }
  function diagsOf(f) {
    const fresh = lint.state === 'fresh';
    // the JSON Schema check in the browser is shown until claim_lint has checked the same text (claim_lint checks the
    // same schemas with jsonschema: its SCHEMA findings are then the ones shown, as the CLI prints them)
    return [].concat(f.yamlDiags, fresh ? [] : f.schemaDiags, f.lintDiags.filter((d) => !(d.rule === 'SCHEMA' && !fresh)), f.anchorDiags);
  }
  function applyDiagnostics(f) {
    const doc = f.state.doc;
    const list = diagsOf(f).filter((d) => d.line).map((d) => {
      const ln = doc.line(Math.max(1, Math.min(d.line, doc.lines)));
      return { from: ln.from, to: ln.to, severity: SEV_CM[d.severity] || 'info', source: d.source === 'claim_lint' ? 'claim_lint ' + d.rule : d.rule, message: d.message };
    });
    const tr = L.setDiagnostics(f.state, list);
    if (f.name === ws.active && view) { view.dispatch(tr); f.state = view.state; } else f.state = f.state.update(tr).state;
  }
  function runChecks(first) {
    if (!ws.open) return;
    ws.files.forEach((f) => parseFile(f));
    ws.registry = {};
    REGISTRY.forEach((k) => { const f = ws.files.get(k + '.yaml'); if (f && f.value && typeof f.value === 'object') ws.registry[k] = f.value; });
    ws.files.forEach((f) => { const k = f.name.replace(/\.yaml$/, ''); if (REGISTRY.includes(k)) schemaCheck(f, k); });
    anchorCheck();
    if (lint.last) {  // re-point the last claim_lint findings at the current lines
      const byFile = new Map();
      lintDiagnostics(lint.last.lint).forEach((d) => { if (!byFile.has(d.file)) byFile.set(d.file, []); byFile.get(d.file).push(d); });
      ws.files.forEach((f) => { f.lintDiags = byFile.get(f.name) || []; });
      ws.lintLoose = byFile.get(null) || [];
    } else { ws.files.forEach((f) => { f.lintDiags = []; }); ws.lintLoose = []; }
    ws.files.forEach((f) => applyDiagnostics(f));
    publish(first);
    renderTabs();
    if (lint.state === 'stale' || lint.state === 'fresh' || lint.state === 'running') scheduleLint(DEBOUNCE_LINT);
  }
  function publish(first) {
    const list = [];
    ws.files.forEach((f) => list.push(...diagsOf(f)));
    list.push(...(ws.lintLoose || []).filter((d) => lint.state === 'fresh' || d.rule !== 'SCHEMA'));
    const byTarget = new Map();
    list.forEach((d) => { const k = d.anchorId || d.target; if (!k) return; if (!byTarget.has(k)) byTarget.set(k, []); byTarget.get(k).push(d); });
    ws.diag = { byTarget, list };
    const b = lint.last && lint.last.bundle;
    P.setData({ registry: ws.registry, sections: b ? b.sections : [], design: ws.designRel, label: ws.label, stale: !!b && lint.state !== 'fresh',
      payload_schemas: b ? b.payload_schemas : null, files: sortedNames() }, ws.diag, { keepScroll: !first });
    status();
  }

  // ------------------------------------------------------------ claim_lint in Pyodide (lazy)
  function base() { return new URL('./', location.href).href; }
  function workerCall(msg) {
    const id = ++lint.seq;
    return new Promise((resolve, reject) => { lint.waiters[id] = { resolve, reject }; lint.worker.postMessage(Object.assign({ id }, msg)); });
  }
  function loadLint() {
    if (lint.state !== 'off' && lint.state !== 'error') return lint.loading || Promise.resolve();
    if (location.protocol === 'file:') { lint.state = 'unavailable'; if (ws.open) publish(false); return Promise.resolve(); }
    lint.state = 'loading';
    if (ws.open) publish(false);
    const t0 = performance.now();
    const abs = new URL(asset('lint-worker.js'), location.href).href;
    // a blob: worker inherits the CSP of this page (worker-src blob:); it only does importScripts(<same-origin file>)
    const url = URL.createObjectURL(new Blob(['importScripts(' + JSON.stringify(abs) + ');'], { type: 'text/javascript' }));
    lint.worker = new Worker(url);
    lint.worker.onmessage = (e) => {
      const m = e.data || {};
      const w = lint.waiters[m.id];
      if (!w) return;
      delete lint.waiters[m.id];
      if (m.type === 'error') w.reject(new Error(m.message)); else w.resolve(m);
    };
    lint.worker.onerror = (e) => { lint.state = 'error'; lint.error = e.message; status(); };
    const giveUp = new Promise((resolve, reject) => setTimeout(() => reject(new Error('Pyodide が 90 秒たっても起動しません')), 90000));
    lint.loading = Promise.race([workerCall({ type: 'init', base: base(), assets: BUILD_INFO.files || {} }), giveUp]).then((m) => {
      if (!m.info || m.info.build !== BUILD_ID) { buildBanner(['lint-worker.js']); throw new Error('lint-worker.js が別の版です。再読み込みしてください'); }
      lint.info = Object.assign({ loadMs: Math.round(performance.now() - t0) }, m.info);
      lint.state = 'stale';
      window.ClaimsEditor.lintInfo = lint.info;
      scheduleLint(0);
    }).catch((err) => { lint.state = 'error'; lint.error = String(err.message || err); if (ws.open) publish(false); });
    return lint.loading;
  }
  function scheduleLint(ms) {
    clearTimeout(lint.timer);
    lint.timer = setTimeout(runLint, ms);
  }
  function runLint() {
    if (!ws.open || !lint.worker || lint.state === 'loading' || lint.state === 'error') return;
    if (lint.running) { lint.again = true; return; }
    const rev = ws.rev;
    const profile = ws.profile;
    const files = {};
    ws.files.forEach((f) => { files[f.name] = f.text; });
    lint.running = true;
    const prev = lint.state;
    lint.state = 'running';
    status();
    workerCall({ type: 'lint', files, designRel: ws.designRel, profile }).then((m) => {
      lint.running = false;
      lint.ms = m.ms;
      if (m.out.errors && m.out.errors.length) status('claim_lint の実行で例外：' + m.out.errors[0].split('\n').slice(-2).join(' '));
      lint.last = { lint: m.out.lint || { findings: [], counts: { error: 0, warn: 0, info: 0 } }, bundle: m.out.bundle, rev, profile };
      lint.state = rev === ws.rev && profile === ws.profile ? 'fresh' : 'stale';
      window.ClaimsEditor.lastLint = { rev, profile, result: lint.last.lint, ms: m.ms, fresh: lint.state === 'fresh' };
      runChecks(false);
      if (lint.state === 'stale' || lint.again) { lint.again = false; scheduleLint(DEBOUNCE_LINT); }
    }).catch((err) => { lint.running = false; lint.state = prev === 'fresh' ? 'stale' : 'error'; lint.error = String(err.message || err); status(); });
  }

  // ------------------------------------------------------------ status line
  function status(msg) {
    const el = $('#status');
    if (!el) return;
    el.textContent = '';
    const all = ws.diag.list || [];
    const c = { error: 0, warn: 0, info: 0 };
    all.forEach((d) => { c[d.severity]++; });
    const ls = { off: '設計の規則の検査：まだ動かしていない', loading: '設計の規則の検査：読み込み中…', running: '設計の規則の検査：検査中…',
      fresh: `設計の規則の検査：最新（${lint.ms} ms、${ws.profile === 'lite' ? '縮小 Lite' : 'Full'} の規則）`, stale: '設計の規則の検査：編集の後、まだ検査していない', error: '設計の規則の検査：動かなかった（' + (lint.error || '') + '）', unavailable: '設計の規則の検査：ファイルとして直接開いたときは動かない' }[lint.state];
    if (msg) status.note = msg;
    add(el, [h('span', { 'data-counts': `${c.error}/${c.warn}/${c.info}` }, `指摘 error ${c.error}・warn ${c.warn}・info ${c.info}`), ' ｜ ',
      h('span', { id: 'lint-state', 'data-state': lint.state }, ls),
      lint.state === 'off' || lint.state === 'error' ? [' ', h('button', { type: 'button', class: 'link', id: 'btn-load-lint', onclick: loadLint, title: 'claim_lint を Python でブラウザの中で動かす（初めては約 13 MB を読み込み、数秒かかる）' }, '動かす')] : null,
      status.note ? [' ｜ ', h('span', { class: 'msg' }, status.note)] : null]);
  }

  // ------------------------------------------------------------ export, autosave
  function download(name, blob) {
    const a = h('a', { href: URL.createObjectURL(blob), download: name });
    document.body.append(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  }
  function exportOne() {
    if (!ws.open || !ws.active) return;
    if (ws.files.get(ws.active)) ws.files.get(ws.active).state = view.state;
    const f = ws.files.get(ws.active);
    download(f.name, new Blob([exportText(f)], { type: /\.md$/.test(f.name) ? 'text/markdown' : 'text/yaml' }));
    f.savedText = exportText(f);
  }
  // -> Promise<true when written, false when a companion's question was cancelled>
  function exportZip() {
    if (!ws.open) return Promise.resolve(false);
    // review.yaml (#50) goes next to the design files, as it is kept in the repository. A companion may ask first what
    // to put in (prepareExport -> {entries, markSaved} or null to cancel)
    let p = Promise.resolve([]);
    companions.forEach((c) => {
      p = p.then((acc) => (c.prepareExport ? c.prepareExport() : Promise.resolve({ entries: c.exportEntries ? c.exportEntries() : [], markSaved: c.markSaved }))
        .then((r) => (r === null || acc === null ? null : acc.concat([r]))));
    });
    return p.then((parts) => {
      if (parts === null) return false;
      const dir = safeDirName(ws.designRel.split('/').pop());
      const entries = {};
      sortedNames().forEach((n) => { entries[dir + '/' + n] = [L.strToU8(exportText(ws.files.get(n))), { mtime: new Date(1980, 0, 2) }]; });
      parts.forEach((r) => (r.entries || []).forEach((e) => {
        if (!entries[dir + '/' + e.name]) entries[dir + '/' + e.name] = [L.strToU8(e.text), { mtime: new Date(1980, 0, 2) }];
      }));
      download(dir + '.zip', new Blob([L.zipSync(entries, { level: 6 })], { type: 'application/zip' }));
      ws.files.forEach((f) => { f.savedText = exportText(f); });
      parts.forEach((r) => { if (r.markSaved) r.markSaved(); });
      return true;
    });
  }
  let autosaveTimer = null;
  function autosaveSoon() { clearTimeout(autosaveTimer); autosaveTimer = setTimeout(autosave, 1000); }
  // true when the current text is in the slot. A failure (quota, storage blocked) keeps the edits counted as not saved:
  // the dialogs and beforeunload still ask, and a warning stays on screen until a save succeeds
  function autosave() {
    if (!ws.open || !autosaveEnabled() || !ws.edited) return false;
    const files = {};
    ws.files.forEach((f) => { files[f.name] = exportText(f); });
    try {
      localStorage.setItem(AUTOSAVE_PREFIX + ws.designRel, JSON.stringify({ name: ws.name, label: ws.label, designRel: ws.designRel, origin: ws.origin, profile: ws.profile,
        savedAt: new Date().toISOString().replace('T', ' ').slice(0, 19), files }));
      saveWarning(null);
      return true;
    } catch (e) {
      saveWarning(`自動保存に失敗しました（${e.name || 'Error'}：${e.message || e}）。今の変更はこのブラウザに保存されていません。「zip で書き出す」で保存してください。`);
      return false;
    }
  }
  // the warnings that stay on screen until the save succeeds, one per source (the files; the review records of #50)
  const saveWarnings = new Map();
  function saveWarning(text, key) {
    const k = key || 'files';
    if (text) saveWarnings.set(k, text); else saveWarnings.delete(k);
    const el = $('#save-warn');
    if (!el) return;
    el.hidden = !saveWarnings.size;
    el.textContent = Array.from(saveWarnings.values()).map((t) => '⚠ ' + t).join(' ');
  }
  function keptByAutosave() {
    if (!autosaveEnabled()) return false;
    if (filesUnsaved() && !(ws.edited && autosave())) return false;
    return companions.every((c) => !c.unsaved() || (c.autosave && c.autosave()));
  }

  // ------------------------------------------------------------ two tabs on one design (#50, the PR #51 check)
  // localStorage fires a storage event in the other tabs of this origin. When another tab saves the slot of the design
  // that is open here (the files, or the review records of #50), this tab says so and offers the other tab's version;
  // saving here afterwards would overwrite it (last write wins), so the note stays until it is answered.
  const foreign = { notes: new Map() };
  function onStorage(e) {
    if (!ws.open || !e.key || e.storageArea !== localStorage) return;
    const mine = AUTOSAVE_PREFIX + ws.designRel;
    const comp = companions.find((c) => c.slotKey && c.slotKey() === e.key);
    if (e.key !== mine && !comp) return;
    if (e.newValue === null) return;
    let when = '';
    try { when = (JSON.parse(e.newValue) || {}).savedAt || ''; } catch (err) { /* not ours */ }
    const what = e.key === mine ? '設計書のファイル' : comp.label;
    foreign.notes.set(e.key, { what, when, comp });
    renderForeign();
  }
  function renderForeign() {
    let el = $('#tab-warn');
    if (!el) { el = h('div', { id: 'tab-warn', class: 'savewarn', role: 'alert' }); $('#save-warn').after(el); }
    el.textContent = '';
    el.hidden = !foreign.notes.size;
    foreign.notes.forEach((n, key) => {
      el.append(h('p', { 'data-foreign': key }, '⚠ 別のタブで、この設計書（', code(ws.designRel), `）の${n.what}が保存されました（${n.when || '時刻不明'}）。このタブで続けて保存すると、別のタブの版を上書きします。 `,
        h('button', { type: 'button', 'data-foreign-load': key, onclick: () => {
          foreign.notes.delete(key); renderForeign();
          if (n.comp) n.comp.loadForeign();
          else { const sv = slot(ws.designRel); if (sv) openWorkspace(Object.assign({}, sv, { origin: 'autosave' }), Object.keys(sv.files).map((x) => ({ name: x, text: sv.files[x] }))); }
        } }, '別のタブの版を開く'), ' ',
        h('button', { type: 'button', 'data-foreign-keep': key, onclick: () => { foreign.notes.delete(key); renderForeign(); } }, 'このタブの版を残す（知らせを閉じる）')));
    });
  }

  // ------------------------------------------------------------ row anchors and content hashes (#50)
  // RFC 8785 (JSON Canonicalization Scheme): object keys sorted by UTF-16 code units (the default sort of JavaScript
  // strings), numbers as ECMAScript's Number.prototype.toString (what JSON.stringify writes: 1.0 -> 1, 1e21 -> 1e+21),
  // strings as JSON.stringify writes them, no whitespace. The Python twin is tools/row_hash.py (jcs).
  function canonicalJson(v) {
    if (v === null || v === undefined) return 'null';
    if (typeof v === 'number') { if (!isFinite(v)) throw new Error('JCS: a number that is not finite'); return JSON.stringify(v); }
    if (typeof v === 'string') return jcsString(v);
    if (typeof v !== 'object') return JSON.stringify(v);
    if (Array.isArray(v)) return '[' + v.map(canonicalJson).join(',') + ']';
    return '{' + Object.keys(v).sort().map((k) => jcsString(k) + ':' + canonicalJson(v[k])).join(',') + '}';
  }
  const LONE_SURROGATE = /[\ud800-\udbff](?![\udc00-\udfff])|(?:^|[^\ud800-\udbff])[\udc00-\udfff]/;
  function jcsString(x) {
    if (LONE_SURROGATE.test(x)) throw new Error('JCS: a string with a lone surrogate (not I-JSON)');
    return JSON.stringify(x);
  }
  function hashOf(row) { try { return sha256(canonicalJson(row)); } catch (e) { return null; } }
  // the value of a YAML text as the editor reads it (the same options as the files), canonicalised: for the parity test
  function canonicalYaml(text) {
    const d = L.parseDocument(text, { schema: 'yaml-1.1', customTags: YAML_TAGS, uniqueKeys: true });
    if (d.errors.length) throw new Error(d.errors[0].message);
    return canonicalJson(d.toJS({ maxAliasCount: 100 }));
  }
  // SHA-256 (FIPS 180-4) of a string's UTF-8 bytes, synchronous so that it also works outside a secure context
  function sha256(str) {
    const K = [0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
      0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
      0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
      0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
      0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
      0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2];
    const bytes = new TextEncoder().encode(str);
    const len = bytes.length;
    const n = ((len + 9 + 63) >> 6) << 6;
    const m = new Uint8Array(n);
    m.set(bytes);
    m[len] = 0x80;
    const dv = new DataView(m.buffer);
    dv.setUint32(n - 4, (len * 8) >>> 0);
    dv.setUint32(n - 8, Math.floor(len / 0x20000000));
    const H = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
    const W = new Uint32Array(64);
    const rot = (x, r) => (x >>> r) | (x << (32 - r));
    for (let o = 0; o < n; o += 64) {
      for (let i = 0; i < 16; i++) W[i] = dv.getUint32(o + i * 4);
      for (let i = 16; i < 64; i++) {
        const s0 = rot(W[i - 15], 7) ^ rot(W[i - 15], 18) ^ (W[i - 15] >>> 3);
        const s1 = rot(W[i - 2], 17) ^ rot(W[i - 2], 19) ^ (W[i - 2] >>> 10);
        W[i] = (W[i - 16] + s0 + W[i - 7] + s1) >>> 0;
      }
      let [a, b, c, d, e, f, g, hh] = H;
      for (let i = 0; i < 64; i++) {
        const t1 = (hh + (rot(e, 6) ^ rot(e, 11) ^ rot(e, 25)) + ((e & f) ^ (~e & g)) + K[i] + W[i]) >>> 0;
        const t2 = ((rot(a, 2) ^ rot(a, 13) ^ rot(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) >>> 0;
        hh = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
      }
      H[0] = (H[0] + a) >>> 0; H[1] = (H[1] + b) >>> 0; H[2] = (H[2] + c) >>> 0; H[3] = (H[3] + d) >>> 0;
      H[4] = (H[4] + e) >>> 0; H[5] = (H[5] + f) >>> 0; H[6] = (H[6] + g) >>> 0; H[7] = (H[7] + hh) >>> 0;
    }
    return H.map((x) => x.toString(16).padStart(8, '0')).join('');
  }
  // The anchor of a row is <kind>:<id>. An id that is written twice has no anchor (the review mode cannot tell the rows
  // apart): such rows are left out of anchors() and reported as a diagnostic (rule ANCHOR).
  function allAnchors() { return anchorsOf((kind) => rowList(kind), () => { const tt = ws.files.get('token_types.yaml'); return tt && tt.value && tt.value.issuance_profile; }); }
  function anchorsOf(listOf, profileOf) {
    const out = [];
    Object.keys(ROWS).forEach((kind) => {
      const key = ROWS[kind][2];
      listOf(kind).forEach((r, i) => {
        if (r && typeof r === 'object' && !Array.isArray(r) && r[key] !== undefined && r[key] !== null) out.push({ anchor: kind + ':' + r[key], kind, id: String(r[key]), index: i, row: r });
      });
    });
    const prof = profileOf();
    if (prof && typeof prof === 'object' && !Array.isArray(prof)) Object.keys(prof).forEach((k) => out.push({ anchor: 'issuance_profile:' + k, kind: 'issuance_profile', id: k, row: prof[k] }));
    return out;
  }
  // the anchors and hashes of another version of a design ({file name: text}), read as the open files are read: the
  // review mode compares them with the open design (the rows that changed, #50; tools/review_record.py diff)
  function hashesOfTexts(texts) {
    const values = {}; const errors = [];
    Object.keys(ROWS).forEach((kind) => {
      const name = ROWS[kind][0];
      if (typeof texts[name] !== 'string') return;
      try {
        const d = L.parseDocument(texts[name], { schema: 'yaml-1.1', customTags: YAML_TAGS, uniqueKeys: true });
        if (d.errors.length) { errors.push(`${name}: ${String(d.errors[0].message).split('\n')[0]}`); return; }
        values[kind] = d.toJS({ maxAliasCount: 100 });
      } catch (e) { errors.push(`${name}: ${e.message || e}`); }
    });
    const listOf = (kind) => { const v = values[kind]; const k = ROWS[kind][1]; return v && typeof v === 'object' && Array.isArray(v[k]) ? v[k] : []; };
    const all = anchorsOf(listOf, () => values.token_types && values.token_types.issuance_profile);
    const n = new Map();
    all.forEach((a) => n.set(a.anchor, (n.get(a.anchor) || 0) + 1));
    const hashes = {};
    all.forEach((a) => { if (n.get(a.anchor) === 1) { const x = hashOf(a.row); if (x) hashes[a.anchor] = x; } });
    return { hashes, duplicates: Array.from(n.keys()).filter((k) => n.get(k) > 1), errors, files: Object.keys(texts) };
  }
  // a YAML text read with the options of the design files (YAML 1.1 as PyYAML, duplicate keys refused): review.yaml
  function parseYaml(text) {
    const d = L.parseDocument(text, { schema: 'yaml-1.1', customTags: YAML_TAGS, uniqueKeys: true });
    if (d.errors.length) throw new Error(String(d.errors[0].message).split('\n')[0]);
    return d.toJS({ maxAliasCount: 100 });
  }
  const extraValidators = {};
  function validateWith(kind, value) {
    if (!SCHEMAS || !SCHEMAS[kind]) return [{ path: '', message: 'スキーマ ' + kind + ' がない' }];
    if (!extraValidators[kind]) extraValidators[kind] = new L.Validator(jsSchema(SCHEMAS[kind]), '2020-12', false);
    const res = extraValidators[kind].validate(value);
    if (res.valid) return [];
    return res.errors.filter((e) => !WRAPPERS.has(e.keyword) && !/\/(anyOf|oneOf)\/\d+\//.test(e.keywordLocation))
      .map((e) => ({ path: decodePointer(e.instanceLocation).join('/') || '(root)', message: jaSchemaMessage(e) }));
  }
  function duplicateAnchors() {
    const n = new Map();
    allAnchors().forEach((a) => n.set(a.anchor, (n.get(a.anchor) || 0) + 1));
    return new Set(Array.from(n.keys()).filter((k) => n.get(k) > 1));
  }
  function anchors() { const dup = duplicateAnchors(); return allAnchors().filter((a) => !dup.has(a.anchor)); }
  function anchorCheck() {
    ws.files.forEach((f) => { f.anchorDiags = []; });
    const dup = duplicateAnchors();
    allAnchors().filter((a) => dup.has(a.anchor) && ROWS[a.kind]).forEach((a) => {
      const r = ROWS[a.kind];
      const f = ws.files.get(r[0]);
      if (!f) return;
      f.anchorDiags.push({ source: 'editor', severity: 'warn', rule: 'ANCHOR', file: r[0], line: locate(f, [r[1], String(a.index)]), target: a.id,
        message: `${r[2]} が ${a.id} の行が 2 つ以上ある。行の固定の名前（${a.anchor}）が一意にならないので、この行にはレビューの記録を付けられない` });
    });
    allAnchors().filter((a) => !dup.has(a.anchor) && ROWS[a.kind]).forEach((a) => {
      const r = ROWS[a.kind];
      const f = ws.files.get(r[0]);
      if (!f || hashOf(rowList(a.kind)[a.index]) !== null) return;
      f.anchorDiags.push({ source: 'editor', severity: 'warn', rule: 'ANCHOR', file: r[0], line: locate(f, [r[1], String(a.index)]), target: a.id,
        message: `行 ${a.anchor} の内容のハッシュを計算できない（対になっていないサロゲート、または有限でない数がある。RFC 8785 の JCS にできない）` });
    });
  }
  function rowOf(anchor) {
    const i = String(anchor).indexOf(':');
    const kind = anchor.slice(0, i); const id = anchor.slice(i + 1);
    if (kind === 'issuance_profile') {
      const tt = ws.files.get('token_types.yaml');
      const prof = tt && tt.value && tt.value.issuance_profile;
      return prof && own(prof, id) ? { kind, id, file: 'token_types.yaml', path: ['issuance_profile', id], row: prof[id] } : null;
    }
    const r = ROWS[kind];
    if (!r || duplicateAnchors().has(anchor)) return null;
    const idx = rowList(kind).findIndex((x) => x && typeof x === 'object' && String(x[r[2]]) === id);
    return idx < 0 ? null : { kind, id, file: r[0], path: [r[1], String(idx)], row: rowList(kind)[idx] };
  }
  function reveal(anchor) {
    const r = rowOf(anchor);
    if (!r) return false;
    switchTo(r.file, locate(ws.files.get(r.file), r.path));
    return true;
  }

  // ------------------------------------------------------------ the first screen, the two modes, the panes (#53)
  const FIRST_SCREEN = { 'claims.yaml': '#/claims', 'token_types.yaml': '#/tokens', 'hops.yaml': '#/hops', 'catalog_answers.yaml': '#/catalog' };
  function firstRoute(entries, extras) {
    const review = (extras || []).some((e) => /^review\.ya?ml$/.test(e.name));
    const n = entries.length + (review ? 1 : 0);
    if (n !== 1) return '#/dashboard';
    if (review) return '#/review';
    return FIRST_SCREEN[entries[0].name] || '#/dashboard';
  }
  // 編集 (the editor and the screens of the design) and レビュー (the review screens first in the menu), switched in the
  // top bar. The screen last seen in each mode is kept, so that switching back returns to it.
  const modes = { cur: 'edit', last: { edit: '#/dashboard', review: '#/review' } };
  function setMode(m) {
    modes.cur = m === 'review' ? 'review' : 'edit';
    document.body.classList.toggle('mode-review', modes.cur === 'review');
    ['edit', 'review'].forEach((k) => { const b = $('#mode-' + k); if (b) b.setAttribute('aria-pressed', k === modes.cur ? 'true' : 'false'); });
  }
  function switchMode(m) {
    if (!ws.open) return;
    setMode(m);
    const target = modes.last[modes.cur];
    if (location.hash === target) P.render(); else location.hash = target;
    const h1 = $('#main h1');
    if (h1) h1.focus();
  }
  // a review screen is always in レビュー; a screen of the design stays in the mode it was opened from
  function onRoute() {
    const p = location.hash;
    if (!ws.open || !/^#\/[a-z]/.test(p)) return;
    if (/^#\/review/.test(p) && modes.cur !== 'review') setMode('review');
    modes.last[modes.cur] = p;
  }
  // the editor and the menu can be folded (a window of about 900px has no room for three columns); folded by default
  // where it is narrow, and the reader's choice is kept while the page is open
  const panes = { editor: null, nav: null };
  function setPane(which, open) {
    panes[which] = !!open;
    document.body.classList.toggle(which + '-off', !open);
    const b = $('#btn-toggle-' + which);
    if (b) { b.setAttribute('aria-expanded', open ? 'true' : 'false'); b.textContent = (open ? '◀ ' : '▶ ') + (which === 'editor' ? 'エディター' : 'メニュー'); b.title = (open ? '畳む：' : '開く：') + (which === 'editor' ? 'YAML のエディター' : '画面のメニュー'); }
  }
  const NARROW = window.matchMedia ? window.matchMedia('(max-width: 1100px)') : null;
  function layoutDefaults() {
    const narrow = !!(NARROW && NARROW.matches);
    setPane('editor', panes.editor === null ? true : panes.editor);
    setPane('nav', panes.nav === null ? !narrow : panes.nav);
  }
  // until the reader folds or opens the menu, it follows the width of the window
  if (NARROW && NARROW.addEventListener) NARROW.addEventListener('change', () => { if (ws.open && !panes.navChosen) setPane('nav', !NARROW.matches); });

  // ------------------------------------------------------------ layout: the splitter
  function initSplitter() {
    const sp = $('#splitter'); const split = $('#split');
    const set = (pct) => { split.style.setProperty('--left', Math.max(20, Math.min(80, pct)) + '%'); };
    sp.addEventListener('pointerdown', (e) => {
      sp.setPointerCapture(e.pointerId);
      const move = (ev) => { const r = split.getBoundingClientRect(); set(((ev.clientX - r.left) / r.width) * 100); };
      const up = () => { sp.removeEventListener('pointermove', move); sp.removeEventListener('pointerup', up); };
      sp.addEventListener('pointermove', move); sp.addEventListener('pointerup', up);
    });
    sp.addEventListener('keydown', (e) => {
      const cur = parseFloat(getComputedStyle(split).getPropertyValue('--left')) || 50;
      if (e.key === 'ArrowLeft') { set(cur - 5); e.preventDefault(); }
      if (e.key === 'ArrowRight') { set(cur + 5); e.preventDefault(); }
    });
  }

  // ------------------------------------------------------------ init
  function init() {
    // files of another build read together with this one: say so, and do not start on them (#53)
    const bad = mismatched(LOADED_BEFORE);
    if (bad.length) { buildBanner(bad); return; }
    addEventListener('DOMContentLoaded', () => { const late = mismatched(['review.js']); if (late.length) buildBanner(late); });
    if (!L || !META || !P) { document.body.prepend(h('p', { class: 'err' }, 'エディターのスクリプト（vendor/editor-libs.js・data/meta.js・preview.js）を読めません。')); return; }
    P.setHooks({
      reveal,
      goto: (file, line) => { if (ws.files.has(file)) switchTo(file, line); },
      loadLint,
      lintState: () => lint.state,
      onLintView: () => { if (lint.state === 'off') setTimeout(loadLint, 0); },
      profile: () => ws.profile,
      setProfile: (p) => { ws.profile = p === 'lite' ? 'lite' : 'full'; if (lint.state === 'fresh') lint.state = 'stale'; scheduleLint(0); publish(false); },
      // the screens of a file that is not open offer to add it (#53)
      addFile: () => { const i = $('#in-add'); if (i) i.click(); },
      mode: () => modes.cur,
    });
    $('#mode-edit').addEventListener('click', () => switchMode('edit'));
    $('#mode-review').addEventListener('click', () => switchMode('review'));
    $('#btn-toggle-editor').addEventListener('click', () => { setPane('editor', !panes.editor); if (panes.editor && view) view.requestMeasure(); });
    $('#btn-toggle-nav').addEventListener('click', () => { panes.navChosen = true; setPane('nav', !panes.nav); });
    addEventListener('hashchange', onRoute);
    $('#btn-export-one').addEventListener('click', exportOne);
    $('#btn-export-zip').addEventListener('click', () => { exportZip(); });
    $('#btn-close').addEventListener('click', requestClose);
    // leaving the page with edits that were not written out (a link, a reload, closing the tab): the browser asks first.
    // With autosave on, the edits are saved to their slot instead.
    addEventListener('beforeunload', (e) => {
      if (!unsaved()) return;
      if (keptByAutosave()) return;
      e.preventDefault();
      e.returnValue = '';
    });
    $('#home').addEventListener('click', (e) => { if (ws.open) { e.preventDefault(); setMode('edit'); location.hash = '#/dashboard'; } });
    const chk = $('#chk-autosave');
    chk.checked = autosaveEnabled();
    chk.addEventListener('change', () => {
      try {
        if (chk.checked) { localStorage.setItem(AUTOSAVE_ON, '1'); if (ws.edited) autosave(); status('自動保存を有効にしました（編集した設計書を、このブラウザの localStorage に、設計書のディレクトリごとに保存します）。'); return; }
      } catch (e) { status('localStorage を使えません'); chk.checked = false; return; }
      const n = slots().length;
      const stop = (forget) => {
        try {
          localStorage.removeItem(AUTOSAVE_ON);
          if (forget) Object.keys(localStorage).filter((k) => k.startsWith(AUTOSAVE_PREFIX)).forEach((k) => localStorage.removeItem(k));
        } catch (e) { /* storage unavailable */ }
        status(forget ? `自動保存をやめ、保存した ${n} 件を消しました。` : n ? `自動保存をやめました。保存した ${n} 件は残っています（最初の画面から開ける・消せる）。` : '自動保存をやめました。');
      };
      if (!n) { stop(false); return; }
      ask('自動保存をやめる', `このブラウザに自動保存した設計書が ${n} 件あります。`,
        [['keep', `${n} 件を残して、自動保存だけやめる`], ['delete', `${n} 件を消して、自動保存をやめる`], ['cancel', 'やめない（自動保存を続ける）']])
        .then((c) => { if (c === 'cancel') chk.checked = true; else stop(c === 'delete'); });
    });
    let depth = 0;
    addEventListener('dragenter', (e) => { if (e.dataTransfer && Array.from(e.dataTransfer.types || []).includes('Files')) { depth++; $('#drop-overlay').hidden = false; } });
    addEventListener('dragleave', () => { depth = Math.max(0, depth - 1); if (!depth) $('#drop-overlay').hidden = true; });
    addEventListener('dragover', (e) => e.preventDefault());
    addEventListener('drop', (e) => { depth = 0; onDrop(e); });
    addEventListener('storage', onStorage);
    initSplitter();
    window.ClaimsEditor.started = true;
    renderStart();
  }

  window.ClaimsEditor = {
    BUILD_ID,
    started: false,
    asset,
    buildBanner,
    mode: () => modes.cur,
    // for the review mode (#50) and the tests
    state: () => ({ open: ws.open, name: ws.name, designRel: ws.designRel, origin: ws.origin, profile: ws.profile, active: ws.active,
      files: sortedNames(), lint: lint.state, rev: ws.rev }),
    fileText: (n) => (ws.files.get(n) ? exportText(ws.files.get(n)) : null),
    // replace the first occurrence of `search` in a file through a CodeMirror transaction (the same path as typing)
    replaceText: (n, search, replacement) => {
      const f = ws.files.get(n);
      if (!f) return false;
      if (n === ws.active) f.state = view.state;
      const i = f.state.doc.toString().indexOf(search);
      if (i < 0) return false;
      const spec = { changes: { from: i, to: i + search.length, insert: replacement } };
      if (n === ws.active) view.dispatch(spec); else { const tr = f.state.update(spec); onEdit(n, tr.state); }
      return true;
    },
    diagnostics: () => (ws.diag.list || []).map((d) => Object.assign({}, d)),
    anchors,
    rowOf,
    rowHash: (anchor) => { const r = rowOf(anchor); return r ? hashOf(r.row) : null; },
    canonicalJson,
    canonicalYaml,
    duplicateAnchors: () => Array.from(duplicateAnchors()),
    unsaved,
    sha256,
    reveal,
    loadLint,
    open: { sample: openSample, skeleton: openSkeleton, paste: openPaste },
    registerRowPanel: (fn) => P.registerRowPanel(fn),
    // for the review mode (#50)
    registerCompanion: (c) => { companions.push(c); },
    hashesOfTexts,
    parseYaml,
    validate: validateWith,
    ask,
    download,
    goto: (file, line) => { if (ws.files.has(file)) { switchTo(file, line); return true; } return false; },
    autosaveEnabled,
    saveWarning,
    label: () => ws.label,
    publish: () => { if (ws.open) publish(false); },
    lintCounts: () => (lint.state === 'fresh' && lint.last ? Object.assign({ profile: lint.last.profile }, lint.last.lint.counts) : null),
    lintInfo: null,
    lastLint: null,
  };
  init();
})();
