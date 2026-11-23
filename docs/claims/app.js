// Design-document viewer (#36). MIT (LICENSE of the repository).
// Static and read-only: the data are docs/claims/data/*.js (python tools/build_claims_viewer.py) or files the reader
// opens in the browser (FileReader; nothing is sent: the page CSP is connect-src 'none'). Every value from the data is
// put into the page as text (textContent), never as HTML.
'use strict';
(function () {
  const DATA = (window.CLAIMS_VIEWER_DATA = window.CLAIMS_VIEWER_DATA || {});
  const META = DATA.meta;
  const TRACE = DATA.trace;
  const CASESTUDY = 'https://github.com/Takenori-Kusaka/jwt-claims-casestudy/tree/';
  const REPO = 'https://github.com/Takenori-Kusaka/jwt-claims-guide';
  const ASVS_CHAPTERS = { 1: 'Encoding-and-Sanitization', 2: 'Validation-and-Business-Logic', 3: 'Web-Frontend-Security',
    4: 'API-and-Web-Service', 5: 'File-Handling', 6: 'Authentication', 7: 'Session-Management', 8: 'Authorization',
    9: 'Self-contained-Tokens', 10: 'OAuth-and-OIDC', 11: 'Cryptography', 12: 'Secure-Communication', 13: 'Configuration',
    14: 'Data-Protection', 15: 'Secure-Coding-and-Architecture', 16: 'Security-Logging-and-Error-Handling', 17: 'WebRTC' };
  const REF_KIND = { spec: '仕様', guidance: '指針', research: '研究', book: '書籍', incident: '事故', 'guide-slide': 'ガイドのスライド',
    'author-proposal': '筆者の提案' };
  const SEVERITY = { error: ['ng', '✖'], warn: ['warn', '▲'], info: ['info', 'ℹ'] };
  const STATUS = { satisfied: ['ok', '✓', '満たす'], unsatisfied: ['ng', '✖', '満たさない'], unknown: ['warn', '?', '判定できない'] };
  const DECISION = { '採用': ['ok', '●'], '既定どおり': ['neutral', '○'], '却下': ['ng', '✖'] };
  const TIER_ROW = { read: '受け手が読む行', idle: '縮小の行（既定どおり・受け手なし）', rejected: '却下の行' };

  const state = { ds: null, bundles: {}, localFiles: [] };
  const $ = (s, r) => (r || document).querySelector(s);

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
    for (let i = 2; i < arguments.length; i++) add(el, arguments[i]);
    return el;
  }
  function add(el, c) {
    if (c === null || c === undefined || c === false) return;
    if (Array.isArray(c)) { c.forEach((x) => add(el, x)); return; }
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  function code(t) { return h('code', null, String(t)); }
  function badge(kind, symbol, text, title) {
    return h('span', { class: 'badge ' + kind, title: title || null }, h('span', { 'aria-hidden': 'true' }, symbol), text);
  }
  function safeUrl(u) { return /^https?:\/\//i.test(String(u)) ? String(u) : null; }
  function ext(url, text) { const u = safeUrl(url); return u ? h('a', { href: u, rel: 'noreferrer noopener' }, text) : text; }
  function slideLink(id) {
    const s = META.names.slides[id];
    return h('a', { href: '../#' + encodeURIComponent(id), title: s ? `スライド ${s.n}：${s.title}` : 'スライド（ID が一覧に無い）',
      'data-slide': id }, 'slide:' + id);
  }
  function route(ds, view, id, query) {
    let r = '#/' + encodeURIComponent(ds) + '/' + view + (id !== undefined && id !== null ? '/' + encodeURIComponent(id) : '');
    if (query) { const q = new URLSearchParams(query).toString(); if (q) r += '?' + q; }
    return r;
  }

  // inline text: `code`, **bold**, slide:<id>, URLs, C-… / token ids (when they exist in the dataset)
  const INLINE = /(`[^`]+`)|(\*\*[^*]+\*\*)|(slide:p\d{2}-[a-z0-9-]+)|(https?:\/\/[^\s）、。」]+)/g;
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
  function paras(list) { return (list || []).map((t) => h('p', { class: 'muted' }, inline(t))); }

  // ------------------------------------------------------------ data access
  function B() { return state.bundles[state.ds]; }
  function reg(b) { return (b || B()).registry || {}; }
  function claims(b) { const c = reg(b).claims; return (c && c.claims) || []; }
  function tokenTypes(b) { const t = reg(b).token_types; return (t && t.token_types) || []; }
  function profile(b) { const t = reg(b).token_types; return (t && t.issuance_profile) || null; }
  function hops(b) { const x = reg(b).hops; return (x && x.hops) || []; }
  function answers(b) { const x = reg(b).catalog_answers; return (x && x.answers) || []; }
  function section(id, b) { return ((b || B()).sections || []).find((s) => s.id === id) || null; }
  function claimById(id) { return claims().find((c) => c.id === id); }
  function tokenById(id) { return tokenTypes().find((t) => t.id === id); }
  function hopById(id) { return hops().find((x) => x.id === id); }
  function fullName(c) { return (c.namespace ? c.namespace : '') + (c.name || ''); }
  function tierOf(c) {
    if (c.decision === '却下') return 'rejected';
    if (c.decision === '既定どおり' && !(c.consumers || []).length) return 'idle';
    return 'read';
  }
  function stages(c) { return (c.authoritative_writer || []).map((w) => w && w.stage).filter(Boolean); }

  // lint findings by target (claim id, token type id, hop id, event id)
  function lintIndex() {
    const s = section('ci-result');
    const idx = {};
    if (!s || !s.tables.length) return null;
    for (const f of s.tables[0].rows) {
      const t = String(f.target || '').replace(/^(token_type|hop) /, '');
      (idx[t] = idx[t] || []).push(f);
    }
    return idx;
  }
  function lintBadges(id) {
    const idx = lintIndex();
    const fs = (idx && idx[id]) || [];
    if (!fs.length) return null;
    const by = {};
    fs.forEach((f) => { by[f.severity] = (by[f.severity] || 0) + 1; });
    return h('span', { class: 'codes' }, Object.keys(SEVERITY).filter((k) => by[k]).map((k) =>
      badge(SEVERITY[k][0], SEVERITY[k][1], `${k} ${by[k]}`, fs.filter((f) => f.severity === k).map((f) => f.rule + ' ' + f.message).join('\n'))));
  }
  function lintList(id) {
    const idx = lintIndex();
    const fs = (idx && idx[id]) || [];
    if (!fs.length) return null;
    return h('div', { class: 'note warn', 'data-lint-for': id }, h('strong', null, 'lint の指摘（claim_lint）'),
      h('ul', null, fs.map((f) => h('li', null, sevBadge(f.severity), ' ', code(f.rule), ' ', inline(f.message)))));
  }
  function sevBadge(s) { const x = SEVERITY[s] || ['neutral', '•']; return badge(x[0], x[1], s); }

  // ------------------------------------------------------------ value rendering
  function refItem(r) {
    if (!r || typeof r !== 'object') return text(r);
    if (r.kind === 'guide-slide') return slideLink(r.id);
    if (r.kind === 'author-proposal') {
      const t = r.tracking && /^#\d+$/.test(r.tracking) ? h('a', { href: REPO + '/issues/' + r.tracking.slice(1) }, r.tracking) : r.tracking;
      return h('span', null, '筆者の提案：', r.id, t ? ['（追跡 ', t, '）'] : null);
    }
    const label = r.url ? ext(r.url, r.id) : r.id;
    return h('span', null, label, h('span', { class: 'muted' }, `（${REF_KIND[r.kind] || r.kind}${r.verified_on ? '、確かめた日 ' + r.verified_on : ''}）`));
  }
  function refs(v) {
    const list = Array.isArray(v) ? v : [v];
    if (!list.length) return none();
    return h('ul', null, list.map((r) => h('li', null, refItem(r))));
  }
  function asvs(id) {
    const m = /^v(\d+\.\d+\.\d+)-(\d+)\.\d+\.\d+$/.exec(id);
    if (!m) return code(id);
    const ch = +m[2]; const name = ASVS_CHAPTERS[ch];
    const file = name ? `0x${(0x0f + ch).toString(16)}-V${ch}-${name}.md` : '';
    return h('a', { href: `https://github.com/OWASP/ASVS/blob/v${m[1]}/${m[1].split('.').slice(0, 2).join('.')}/en/${file}`, rel: 'noreferrer noopener',
      title: `OWASP ASVS ${m[1]} の V${ch}` }, 'ASVS ' + id);
  }
  function caseRef(s) {
    const m = /^jwt-claims-casestudy@([0-9a-f]{7,40}):(.+)$/.exec(s);
    return m ? h('a', { href: CASESTUDY + m[1], title: 'ケーススタディのコミット ' + m[1] }, s) : text(s);
  }
  function claimLink(id) { return claimById(id) ? h('a', { href: route(state.ds, 'claim', id) }, id) : code(id); }
  function tokenLink(id) { return tokenById(id) ? h('a', { href: route(state.ds, 'token', id) }, id) : code(id); }
  function hopLink(id) { return hopById(id) ? h('a', { href: route(state.ds, 'hop', id) }, id) : code(id); }
  function eventLabel(id) { const n = META.names.events[id]; return h('span', null, code(id), n ? ' ' + n : ''); }
  function questionLabel(id) { const n = META.names.questions[id]; return h('span', null, code(id), n ? `「${n}」` : ''); }
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
        if (v.every((x) => 'kind' in x && 'id' in x && REF_KIND[x.kind])) return refs(v);
        return miniTable(v, col);
      }
      if (v.every((x) => typeof x !== 'object')) return h('ul', null, v.map((x) => h('li', null, value(x, col, depth + 1))));
      return h('ul', null, v.map((x) => h('li', null, value(x, col, depth + 1))));
    }
    if (typeof v === 'object') {
      if ('kind' in v && 'id' in v && REF_KIND[v.kind]) return refItem(v);
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
    if (coll === 'hops' && key === 'upstream') return v ? hopLink(v) : none();
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
    if (groups.length > 1) out.push(h('nav', { class: 'toc', 'aria-label': '列のまとまり' }, groups.map((g, i) => h('a', { href: '#grp-' + i, onclick: jump }, g.name))));
    groups.forEach((g, i) => {
      if (g.name) out.push(h('h2', { id: 'grp-' + i, tabindex: '-1' }, g.name));
      out.push(h('div', { class: 'cols' }, g.cols.map((c) => column(coll, c, obj))));
    });
    const known = new Set(cols.map((c) => c.key));
    const extra = Object.keys(obj).filter((k) => !known.has(k));
    if (extra.length && !(opts && opts.noExtra)) {
      out.push(h('h2', null, 'スキーマにない列'));
      out.push(h('p', { class: 'muted' }, '台帳のスキーマ（templates/registry/*.schema.json）に無い列です。スキーマの検査（claim_lint）で落ちます。'));
      out.push(h('div', { class: 'cols' }, extra.map((k) => column(coll, { key: k, label: k, lite: '' }, obj))));
    }
    return out;
  }
  function jump(e) {
    const id = e.currentTarget.getAttribute('href').slice(1);
    const t = document.getElementById(id);
    if (t) { e.preventDefault(); t.scrollIntoView(); t.focus(); }
  }
  function column(coll, c, obj) {
    const has = Object.prototype.hasOwnProperty.call(obj, c.key);
    const qs = (META.review || {})[coll + '.' + c.key] || [];
    return h('div', { class: 'col' + (has ? '' : ' empty'), 'data-col': c.key },
      h('div', { class: 'ch' }, h('span', { class: 'lbl' }, c.label), h('code', { class: 'key' }, c.key),
        c.lite ? h('span', { class: 'lite' }, '縮小 Lite：' + c.lite) : null,
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
        if (key === 'hop' && row && row.id && hopById(row.id)) return h('a', { href: route(state.ds, 'hop', row.id) }, String(v));
        return typeof v === 'object' ? value(v) : inline(String(v));
    }
  }
  function linkish(s, key) {
    if (key === 'event' && META.names.events[s]) return code(s);
    if (claimById(s)) return claimLink(s);
    if (tokenById(s)) return tokenLink(s);
    if (hopById(s)) return hopLink(s);
    const c = claims().find((x) => x.name === s && x.decision !== '却下');
    if (c && (key === 'claim' || key === 'candidate' || key === 'claims' || key === 'mechanisms' || key === 'not_claims')) return h('a', { href: route(state.ds, 'claim', c.id) }, s);
    return code(s);
  }
  function rowTarget(row) {
    return row.claim_id || (row.id && claimById(row.id) && row.id) || (row.id && tokenById(row.id) && row.id) ||
      (row.id && hopById(row.id) && row.id) || row.event || row.hop || null;
  }
  function table(t, opts) {
    opts = opts || {};
    const cols = t.columns.slice();
    const withLint = opts.lint !== false && lintIndex();
    return h('div', { class: 'tablewrap' }, h('table', { 'data-table': t.id },
      t.title ? h('caption', null, t.title) : null,
      h('thead', null, h('tr', null, cols.map((c) => h('th', { scope: 'col' }, c.label)), withLint ? h('th', { scope: 'col' }, 'lint') : null)),
      h('tbody', null, t.rows.map((r) => {
        const target = rowTarget(r);
        const tr = h('tr', { 'data-row': target || null, class: r.exceeds ? 'exceeds' : null },
          cols.map((c, i) => h(i === 0 ? 'th' : 'td', i === 0 ? { scope: 'row' } : null, cell(r[c.key], c.fmt, c.key, r))),
          withLint ? h('td', null, target ? lintBadges(target) : null) : null);
        return tr;
      }))));
  }
  function sectionBlock(s, level) {
    if (!s) return null;
    return [h(level || 'h2', null, s.title), paras(s.notes), s.tables.map((t) => table(t)), paras(s.after)];
  }
  function needBundle(what) {
    return h('div', { class: 'note warn' }, h('p', null, `${what}は render の JSON の束から表示します。開いたのが YAML だけなので、この画面の生成した表はありません。`),
      h('p', null, '束の作り方：', code('python -m tools.claim_lint render <設計書のディレクトリ> --format json --out bundle.json'), '。できた bundle.json を「自分の YAML を開く」で開いてください（YAML と一緒に開いてもよい）。'));
  }

  // ------------------------------------------------------------ views
  const VIEWS = [
    ['overview', '概要'], ['claims', 'クレームの一覧'], ['tokens', 'トークン目録'], ['profile', '発行方式と要件'],
    ['hops', 'ホップの表'], ['lifecycle', '寿命の 4 つの層'], ['catalog', 'カタログへの回答'], ['lint', 'lint の結果'],
    ['tables', 'そのほかの生成した表'],
  ];
  function nav(cur) {
    const ul = $('#nav'); ul.textContent = '';
    ul.append(h('li', { class: 'sep' }, '設計書'));
    VIEWS.forEach(([v, label]) => ul.append(h('li', null, h('a', { href: route(state.ds, v), 'aria-current': cur === v ? 'page' : null }, label))));
    ul.append(h('li', { class: 'sep' }, 'ガイド全体'));
    ul.append(h('li', null, h('a', { href: '#/trace', 'aria-current': cur === 'trace' ? 'page' : null }, '対応表の進み具合')));
    ul.append(h('li', null, h('a', { href: '#/local', 'aria-current': cur === 'local' ? 'page' : null }, '自分の YAML を開く')));
  }

  function viewOverview() {
    const b = B();
    const cs = claims();
    const dec = {};
    cs.forEach((c) => { dec[c.decision] = (dec[c.decision] || 0) + 1; });
    const ci = section('ci-result');
    const cat = section('catalog-summary');
    const label = (META.datasets.find((d) => d.id === state.ds) || {}).label || 'ローカルのファイル';
    return [h('h1', { tabindex: '-1' }, label),
      h('p', { class: 'lead' }, '設計書のディレクトリ：', code(b.design || '（ローカル）'), b.format ? ['（', code(b.format), '）'] : null),
      h('div', { class: 'cards' },
        card('台帳の行', cs.length, Object.keys(dec).map((k) => `${k} ${dec[k]}`).join('・')),
        card('トークン種別', tokenTypes().length),
        card('ホップ', hops().length),
        card('カタログへの回答', answers().length, cat && cat.counts ? `対象外 ${cat.counts.out_of_scope}（${cat.counts.out_of_scope_pct}%）` : null),
        ci && ci.counts ? card('lint', `${ci.counts.error} / ${ci.counts.warn} / ${ci.counts.info}`, 'error / warn / info') : null),
      h('div', { class: 'note' }, h('p', null, h('strong', null, '外部と通信しません。'), 'このページは、同じディレクトリのスクリプトとデータだけを読みます。CSP（',
        code("connect-src 'none'"), '）で、スクリプトからの通信を禁じています。「自分の YAML を開く」で開いたファイルは、ブラウザの中だけで読み、送信しません。')),
      h('h2', null, '読み方'),
      h('ul', null, h('li', null, '根拠の ', code('slide:<id>'), ' は、スライドの Web 版の該当スライドに移動します。RFC・ASVS などは原典に移動します。'),
        h('li', null, '状態は色だけでなく、記号と文字（✓ 満たす・✖ 満たさない・? 判定できない、error・warn・info）で示します。'),
        h('li', null, 'キーボード：', h('span', { class: 'kbd' }, 'Tab'), ' で移動し、', h('span', { class: 'kbd' }, 'Enter'), ' で開きます。一覧で ',
          h('span', { class: 'kbd' }, '/'), ' を押すと検索欄に移ります。')),
      b.sources ? [h('h2', null, '入力のファイル（sha256、改行を LF にそろえて計算）'),
        h('div', { class: 'tablewrap' }, h('table', null, h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'ファイル'), h('th', { scope: 'col' }, 'sha256'))),
          h('tbody', null, Object.keys(b.sources).map((k) => h('tr', null, h('th', { scope: 'row' }, code(k)), h('td', null, code(b.sources[k])))))))] : null];
  }
  function card(k, v, sub) { return h('div', { class: 'card' }, h('div', { class: 'k' }, k), h('div', { class: 'v' }, String(v)), sub ? h('div', { class: 'muted' }, sub) : null); }

  const FILTERS = [
    ['token', '載るトークン', (c) => c.carried_in || []],
    ['stage', '段階（書き手）', (c) => stages(c)],
    ['decision', '採否', (c) => [c.decision]],
    ['tier', 'Lite の扱い（tier）', (c) => [TIER_ROW[tierOf(c)]]],
    ['data_category', '何のデータか（data_category）', (c) => c.data_category || []],
    ['pii_category', '個人情報の区分', (c) => [c.pii_category || '（未記入）']],
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
    const tbl = h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'claims' }, h('caption', null, '台帳の行（クリックかキーボードで詳細を開く）'),
      h('thead', null, h('tr', null, ['ID', '名前', '型', '採否', 'Lite の扱い', '載るトークン', 'data_category', 'pii_category', '状態', '段階', 'lint'].map((x) => h('th', { scope: 'col' }, x)))), tbody));
    function apply() {
      const params = {};
      const text = search.value.trim().toLowerCase();
      if (text) params.q = search.value.trim();
      const sel = {};
      FILTERS.forEach(([k]) => { const v = $('#f-' + k).value; if (v) { sel[k] = v; params[k] = v; } });
      const rows = cs.filter((c) => {
        if (text) {
          const hay = [c.id, fullName(c), c.description, c.not_meaning, c.rationale, c.note].filter(Boolean).join(' ').toLowerCase();
          if (!hay.includes(text)) return false;
        }
        return FILTERS.every(([k, , f]) => !sel[k] || f(c).includes(sel[k]));
      });
      tbody.textContent = '';
      rows.forEach((c) => {
        const d = DECISION[c.decision] || ['neutral', '•'];
        tbody.append(h('tr', { 'data-row': c.id },
          h('th', { scope: 'row' }, h('a', { href: route(state.ds, 'claim', c.id) }, c.id)),
          h('td', null, c.namespace ? h('span', { class: 'muted' }, c.namespace) : null, h('strong', null, c.name)),
          h('td', null, code(c.type || '—'), c.shape && c.shape !== 'single' ? [' ', h('span', { class: 'muted' }, c.shape)] : null),
          h('td', null, badge(d[0], d[1], c.decision)),
          h('td', null, TIER_ROW[tierOf(c)]),
          h('td', null, (c.carried_in || []).length ? h('span', { class: 'codes' }, c.carried_in.map(tokenLink)) : '—'),
          h('td', null, (c.data_category || []).length ? h('span', { class: 'codes' }, c.data_category.map(code)) : '—'),
          h('td', null, c.pii_category || '—'),
          h('td', null, c.status === 'deprecated' ? badge('warn', '▲', '廃止予定 deprecated') : (c.status || '—')),
          h('td', null, stages(c).join('・') || '—'),
          h('td', null, lintBadges(c.id))));
      });
      count.textContent = `${rows.length} / ${cs.length} 行`;
      const hash = route(state.ds, 'claims', null, params);
      if (location.hash !== hash) history.replaceState(null, '', hash);
    }
    const form = h('form', { class: 'filters', role: 'search', onsubmit: (e) => e.preventDefault(), oninput: apply, onchange: apply },
      h('label', { class: 'wide' }, '検索', search, h('span', { id: 'f-hint' }, '/ キーでここに移ります')), selects,
      h('div', null, h('button', { type: 'button', onclick: () => { search.value = ''; FILTERS.forEach(([k]) => { $('#f-' + k).value = ''; }); apply(); } }, '絞り込みを解く')));
    setTimeout(apply, 0);
    return [h('h1', { tabindex: '-1' }, 'クレームの一覧'),
      h('p', { class: 'lead' }, '台帳（claims.yaml）の全部の行。「Lite の扱い」は、台帳の README の 2.（縮小 Lite の印）の行の種類です。'),
      form, count, tbl];
  }

  function viewClaim(id) {
    const c = claimById(id);
    if (!c) return notFound('台帳の行 ' + id);
    const d = DECISION[c.decision] || ['neutral', '•'];
    const onHops = hops().filter((x) => (x.custom_claims || []).includes(c.id));
    const prof = section('issuance-profile');
    const effects = [];
    if (prof && prof.effects) prof.effects.forEach((e) => (e.requires || []).forEach((r) => { if ((r.rows || []).includes(c.id)) effects.push([e, r]); }));
    return [h('p', null, h('a', { href: route(state.ds, 'claims') }, '← クレームの一覧')),
      h('h1', { tabindex: '-1' }, c.namespace ? h('span', { class: 'muted' }, c.namespace) : null, c.name, ' ', h('span', { class: 'muted' }, '(' + c.id + ')')),
      h('p', null, badge(d[0], d[1], c.decision), ' ', TIER_ROW[tierOf(c)], c.description ? ['：', inline(c.description)] : null),
      lintList(c.id),
      onHops.length || effects.length ? h('div', { class: 'note' },
        onHops.length ? h('p', null, 'この行を運ぶホップ：', h('span', { class: 'codes' }, onHops.map((x) => hopLink(x.id)))) : null,
        effects.length ? h('p', null, '発行方式から導かれる要件のうち、この行が満たすもの：', h('span', { class: 'codes' },
          effects.map(([e, r]) => h('a', { href: route(state.ds, 'profile') + '', title: r.text }, r.id)))) : null) : null,
      h('p', { class: 'muted' }, `台帳の全列（${META.columns.claims.length} 列）を、templates/registry/README.md の見出しで表示します。書いていない列は「（未記入）」です。`),
      record('claims', c)];
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
    const d = DECISION[t.decision] || ['neutral', '•'];
    const carried = claims().filter((c) => (c.carried_in || []).includes(id));
    return [h('p', null, h('a', { href: route(state.ds, 'tokens') }, '← トークン目録')),
      h('h1', { tabindex: '-1' }, id, ' ', h('span', { class: 'muted' }, META.names.token_kinds[t.kind] || t.kind || '')),
      h('p', null, badge(d[0], d[1], t.decision)), lintList(id),
      carried.length ? h('p', null, '載る台帳の行：', h('span', { class: 'codes' }, carried.map((c) => h('a', { href: route(state.ds, 'claim', c.id), title: c.id }, fullName(c))))) : null,
      record('token_types', t)];
  }
  function registryTable(coll, rows, keys, view) {
    const cols = META.columns[coll] || [];
    const lab = (k) => (cols.find((c) => c.key === k) || {}).label || k;
    return h('div', { class: 'tablewrap' }, h('table', { 'data-table': coll },
      h('thead', null, h('tr', null, keys.map((k) => h('th', { scope: 'col' }, lab(k))))),
      h('tbody', null, rows.map((r) => h('tr', { 'data-row': r.id || null }, keys.map((k, i) => h(i === 0 ? 'th' : 'td', i === 0 ? { scope: 'row' } : null,
        i === 0 && view ? h('a', { href: route(state.ds, view, r.id) }, r.id) : columnValue(coll, k, r[k]) || '—')))))));
  }

  function viewProfile() {
    const s = section('issuance-profile');
    const p = profile();
    const out = [h('h1', { tabindex: '-1' }, '発行方式の選択と、導かれる要件')];
    if (!s) {
      out.push(needBundle('導かれる要件（issuance_effects.yaml）'));
      if (p) out.push(h('h2', null, '発行方式の選択（YAML のまま）'), record('issuance_profile', p, { noExtra: true }));
      return out;
    }
    out.push(paras(s.notes), s.tables.map((t) => table(t, { lint: false })), paras(s.after));
    const holds = (s.effects || []).filter((e) => e.holds);
    const rest = (s.effects || []).filter((e) => !e.holds);
    out.push(h('h2', null, '選択から導かれる要件（templates/registry/issuance_effects.yaml）'),
      h('div', { class: 'note warn' }, h('p', null, h('strong', null, 'これは検査ではありません。'), 'render による簡易な読み取りで、検査の正は claim_lint の L62〜L64 です（tools/claim_lint/RENDER.md の 5.）。')));
    const tally = { satisfied: 0, unsatisfied: 0, unknown: 0 };
    holds.forEach((e) => (e.requires || []).forEach((r) => { tally[r.status] = (tally[r.status] || 0) + 1; }));
    out.push(h('p', null, `成り立つ条件 ${holds.length} 件、要件 `, Object.keys(STATUS).map((k) => [badge(STATUS[k][0], STATUS[k][1], `${STATUS[k][2]} ${tally[k] || 0}`), ' '])));
    holds.forEach((e) => {
      out.push(h('section', { class: 'effect', 'data-effect': e.id },
        h('h3', null, code(e.id), ' ', h('span', { class: 'muted' }, '条件：'), (e.when || []).map((w, i) => [i ? '、' : '', code(w.field), ' = ', code(JSON.stringify(w.equals !== undefined ? w.equals : w))])),
        h('div', { class: 'tablewrap' }, h('table', null, h('thead', null, h('tr', null, ['要件', '内容', '判定（簡易な読み取り。正は L62）', '満たしている行'].map((x) => h('th', { scope: 'col' }, x)))),
          h('tbody', null, (e.requires || []).map((r) => {
            const st = STATUS[r.status] || ['neutral', '•', r.status];
            return h('tr', { 'data-require': r.id }, h('th', { scope: 'row' }, code(r.id)), h('td', null, inline(r.text)),
              h('td', null, badge(st[0], st[1], st[2]), r.check ? h('div', { class: 'muted' }, code(r.check.path + ' ' + r.check.op)) : null),
              h('td', null, (r.rows || []).length ? h('span', { class: 'codes' }, r.rows.map((x) => claimById(x) ? claimLink(x) : tokenLink(x))) : '—'));
          })))),
        h('p', { class: 'muted' }, '根拠：'), refs(e.refs || []), e.lint && e.lint.length ? h('p', { class: 'muted' }, 'lint：', e.lint.join('・')) : null));
    });
    if (rest.length) out.push(h('details', null, h('summary', null, `この選択では成り立たない条件 ${rest.length} 件`),
      h('ul', null, rest.map((e) => h('li', null, code(e.id), ' ', (e.when || []).map((w) => code(w.field + ' = ' + JSON.stringify(w.equals !== undefined ? w.equals : w))))))));
    if (p) out.push(h('details', null, h('summary', null, '発行方式の選択の全列（YAML のまま）'), record('issuance_profile', p, { noExtra: true })));
    return out;
  }

  function viewHops() {
    const out = [h('h1', { tabindex: '-1' }, 'ホップの表'),
      h('p', { class: 'lead' }, inline('下流に進むほど、aud・scope・寿命・独自クレームが絞られていく様子を、上流のホップと並べて示します（slide:p06-narrow-downstream）。'))];
    const s = section('hop-table');
    const a = section('arrow-table');
    if (s) out.push(sectionBlock(s, 'h2')); else out.push(registryTable('hops', hops(), ['id', 'from', 'to', 'kind', 'upstream', 'token_type', 'aud', 'scope', 'max_lifetime', 'custom_claims'], 'hop'));
    out.push(narrowing());
    if (a) out.push(sectionBlock(a, 'h2'));
    return out;
  }
  // per hop: what changed against its upstream hop (fewer aud / scope / claims, shorter lifetime)
  function narrowing() {
    const hs = hops().filter((x) => x.upstream);
    if (!hs.length) return null;
    const diff = (a, b) => (a || []).filter((x) => !(b || []).includes(x));
    return [h('h2', null, '上流との比較（絞り込み）'),
      h('p', { class: 'muted' }, '「減った」は上流にあって下流に無いもの、「増えた」は下流で足されたもの（増えたら理由が要る。検査の正は claim_lint の L16）。'),
      h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'narrowing' }, h('thead', null, h('tr', null, ['ホップ', '上流', 'aud', 'scope', '寿命', '独自クレーム'].map((x) => h('th', { scope: 'col' }, x)))),
        h('tbody', null, hs.map((x) => {
          const u = hopById(x.upstream) || {};
          const cmp = (k) => {
            const less = diff(u[k], x[k]); const more = diff(x[k], u[k]);
            return h('td', null, less.length ? h('div', null, badge('ok', '−', '減った'), ' ', less.join('、')) : null,
              more.length ? h('div', null, badge('warn', '+', '増えた'), ' ', more.join('、')) : null, !less.length && !more.length ? '同じ' : null);
          };
          const lt = typeof x.max_lifetime === 'number' && typeof u.max_lifetime === 'number'
            ? (x.max_lifetime < u.max_lifetime ? [badge('ok', '↓', '短い'), ` ${u.max_lifetime} → ${x.max_lifetime} 秒`] : x.max_lifetime > u.max_lifetime ? [badge('warn', '↑', '長い'), ` ${u.max_lifetime} → ${x.max_lifetime} 秒`] : `同じ（${x.max_lifetime} 秒）`)
            : '—';
          return h('tr', { 'data-row': x.id }, h('th', { scope: 'row' }, hopLink(x.id), ' ', h('span', { class: 'muted' }, `${x.from} → ${x.to}`)), h('td', null, hopLink(x.upstream)),
            cmp('aud'), cmp('scope'), h('td', null, lt), cmp('custom_claims'));
        }))))];
  }
  function viewHop(id) {
    const x = hopById(id);
    if (!x) return notFound('ホップ ' + id);
    return [h('p', null, h('a', { href: route(state.ds, 'hops') }, '← ホップの表')),
      h('h1', { tabindex: '-1' }, id, ' ', h('span', { class: 'muted' }, `${x.from} → ${x.to}`)), lintList(id), record('hops', x)];
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
  function viewLint() {
    const s = section('ci-result');
    const out = [h('h1', { tabindex: '-1' }, 'lint の結果（claim_lint）')];
    if (!s) return out.concat(needBundle('lint の結果'));
    const c = s.counts || {};
    out.push(h('p', null, Object.keys(SEVERITY).map((k) => [badge(SEVERITY[k][0], SEVERITY[k][1], `${k} ${c[k] || 0}`), ' '])), paras(s.notes),
      h('p', { class: 'muted' }, '対象の列は、台帳の行・トークン種別・ホップ・カタログのイベントに移動できます。それぞれの画面の行にも、同じ指摘を重ねて表示しています。'));
    const t = s.tables[0];
    if (t) {
      out.push(h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'ci-result' }, h('thead', null, h('tr', null, t.columns.map((x) => h('th', { scope: 'col' }, x.label)))),
        h('tbody', null, t.rows.map((r) => {
          const tg = String(r.target || '').replace(/^(token_type|hop) /, '');
          const where = claimById(tg) ? claimLink(tg) : tokenById(tg) ? tokenLink(tg) : hopById(tg) ? hopLink(tg)
            : META.names.events[tg] ? h('a', { href: route(state.ds, 'catalog') }, tg) : code(r.target);
          return h('tr', { 'data-row': tg }, h('th', { scope: 'row' }, code(r.rule)), h('td', null, sevBadge(r.severity)), h('td', null, where), h('td', null, inline(r.message)));
        })))));
    }
    out.push(paras(s.after));
    return out;
  }
  function viewTables() {
    const ids = ['decision-rows', 'data-sources', 'question-mechanism'];
    const out = [h('h1', { tabindex: '-1' }, 'そのほかの生成した表'), h('p', { class: 'lead' }, '設計書（design.md）の生成の区間と同じ表です（tools/claim_lint/RENDER.md の 1.）。')];
    const ss = ids.map((i) => section(i)).filter(Boolean);
    if (!ss.length) return out.concat(needBundle('判断の行・データ源・問い × 仕組み'));
    out.push(h('nav', { class: 'toc', 'aria-label': '表' }, ss.map((s) => h('a', { href: '#t-' + s.id, onclick: jump }, s.title))));
    ss.forEach((s) => out.push(h('h2', { id: 't-' + s.id, tabindex: '-1' }, s.title), paras(s.notes), s.tables.map((t) => table(t)), paras(s.after)));
    return out;
  }

  function viewTrace() {
    const t = TRACE;
    const out = [h('h1', { tabindex: '-1' }, 'スライドと成果物の対応表の進み具合（#22）'),
      h('p', { class: 'lead' }, `${t.source} の要件 ${t.total} 件を、tier（core・full）と状態で数えたもの。設計書ごとではなく、ガイド全体の値です。`)];
    const head = (first) => h('thead', null, h('tr', null, h('th', { scope: 'col' }, first), t.statuses.map((s) => h('th', { scope: 'col', class: 'num' }, s)), h('th', { scope: 'col', class: 'num' }, '計'), h('th', { scope: 'col' }, '実装済みの割合')));
    const row = (label, ts) => {
      const total = t.statuses.reduce((a, s) => a + (ts[s] || 0), 0);
      const done = ts['実装済み'] || 0;
      const pct = total ? Math.round((done / total) * 100) : 0;
      return h('tr', null, h('th', { scope: 'row' }, label), t.statuses.map((s) => h('td', { class: 'num' }, String(ts[s] || 0))), h('td', { class: 'num' }, String(total)),
        h('td', null, h('span', { class: 'bar', 'aria-hidden': 'true' }, barFill(pct)), `${pct}%（${done} / ${total}）`));
    };
    out.push(h('h2', null, 'tier × 状態'), h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'trace-tier' }, head('tier'),
      h('tbody', null, t.tiers.map((x) => row(x, t.tier_status[x])), row('計', sumBy(t.tiers.map((x) => t.tier_status[x])))))));
    out.push(h('h2', null, 'Part ごと（tier × 状態）'), h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'trace-parts' }, head('Part・tier'),
      h('tbody', null, t.parts.map((p) => t.tiers.map((x) => row(`${p.part} ${x}`, p.tier_status[x])))))));
    out.push(h('h2', null, '担当の issue ごと'), h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'trace-owners' }, head('issue'),
      h('tbody', null, t.owners.map((o) => row(o.owner, o.status))))));
    return out;
  }
  function barFill(pct) { const s = h('span'); s.style.width = pct + '%'; return s; }
  function sumBy(list) { const o = {}; list.forEach((x) => Object.keys(x).forEach((k) => { o[k] = (o[k] || 0) + x[k]; })); return o; }

  // ------------------------------------------------------------ local files (FileReader only)
  function viewLocal() {
    const input = h('input', { type: 'file', id: 'local-files', multiple: true, accept: '.yaml,.yml,.json,application/json,text/yaml' });
    const list = h('ul', { class: 'files', id: 'local-list' });
    const msg = h('div', { id: 'local-msg', 'aria-live': 'polite' });
    const drop = h('div', { class: 'drop' }, h('p', null, h('label', { for: 'local-files' }, h('strong', null, 'ファイルを選ぶ')), '（複数可）か、ここにドロップします。'), input);
    drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('over'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('over'));
    drop.addEventListener('drop', (e) => { e.preventDefault(); drop.classList.remove('over'); readFiles(e.dataTransfer.files, list, msg); });
    input.addEventListener('change', () => readFiles(input.files, list, msg));
    return [h('h1', { tabindex: '-1' }, '自分の YAML を開く'),
      h('div', { class: 'note' }, h('p', null, h('strong', null, 'ファイルは送信しません。'), 'ブラウザの中（FileReader）で読み、同梱の js-yaml 4.1.1 で解釈します。このページは CSP で ',
        code("connect-src 'none'"), ' にしているので、スクリプトからはどこにも接続できません。社内の設計書を外に出さずに見るための機能です。ページを閉じると読み込んだ内容は消えます（保存しません）。')),
      h('p', null, '開けるもの：'),
      h('ul', null, h('li', null, code('claims.yaml'), '・', code('token_types.yaml'), '・', code('hops.yaml'), '・', code('catalog_answers.yaml'), '（名前か中身の最上位のキーで見分けます）。台帳の一覧・詳細・トークン目録・ホップ・カタログへの回答を表示します。'),
        h('li', null, 'render の JSON の束（', code('python -m tools.claim_lint render <dir> --format json --out bundle.json'), '）。発行方式から導かれる要件・寿命の 4 つの層・lint の結果も表示します。')),
      drop, msg, list];
  }
  function classify(name, obj) {
    if (obj && obj.format === 'claim-lint-render/1') return 'bundle';
    const base = name.toLowerCase().replace(/\.(ya?ml|json)$/, '');
    if (['claims', 'token_types', 'hops', 'catalog_answers'].includes(base)) return base;
    if (obj && Array.isArray(obj.claims)) return 'claims';
    if (obj && (Array.isArray(obj.token_types) || obj.issuance_profile)) return 'token_types';
    if (obj && Array.isArray(obj.hops)) return 'hops';
    if (obj && Array.isArray(obj.answers)) return 'catalog_answers';
    return null;
  }
  function readFiles(files, list, msg) {
    const arr = Array.from(files || []);
    if (!arr.length) return;
    Promise.all(arr.map((f) => f.text().then((txt) => ({ f, txt })))).then((items) => {
      const local = { format: 'local-files', design: '（ローカルのファイル）', sections: [], registry: {} };
      let bundle = null;
      list.textContent = ''; msg.textContent = '';
      for (const { f, txt } of items) {
        let obj; let kind; let err = null;
        try {
          obj = /\.json$/i.test(f.name) ? JSON.parse(txt) : window.jsyaml.load(txt, { schema: window.jsyaml.CORE_SCHEMA, json: false });
          kind = classify(f.name, obj);
          if (!kind) err = '何のファイルか分かりません（claims・token_types・hops・catalog_answers・render の JSON のどれでもない）';
        } catch (e) { err = '読めません：' + (e && e.message ? e.message : e); }
        if (!err && kind === 'bundle') bundle = obj;
        else if (!err) local.registry[kind] = obj;
        list.append(h('li', null, err ? badge('ng', '✖', '読めない') : badge('ok', '✓', kind === 'bundle' ? 'render の束' : kind), ' ', code(f.name), ` ${f.size} バイト`, err ? h('div', { class: 'err' }, err) : null));
      }
      const data = bundle ? Object.assign({}, bundle, { registry: Object.assign({}, bundle.registry, local.registry) }) : local;
      if (!bundle && !Object.keys(local.registry).length) { msg.append(h('p', { class: 'err' }, '表示できるファイルがありません。')); return; }
      state.bundles.local = data;
      state.localFiles = items.map((x) => x.f.name);
      fillDatasets();
      msg.append(h('p', null, badge('ok', '✓', '読み込みました'), ' ', h('a', { href: route('local', 'claims'), id: 'local-open' }, '台帳の一覧を開く'), '（',
        h('a', { href: route('local', 'overview') }, '概要'), '）'));
    });
  }

  // ------------------------------------------------------------ loading and routing
  const loading = {};
  function loadDataset(id) {
    if (state.bundles[id]) return Promise.resolve(state.bundles[id]);
    if (!META.datasets.some((d) => d.id === id)) return Promise.reject(new Error('unknown dataset'));
    if (DATA[id]) { state.bundles[id] = DATA[id]; return Promise.resolve(DATA[id]); }
    loading[id] = loading[id] || new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = 'data/' + id + '.js';
      s.onload = () => (DATA[id] ? resolve((state.bundles[id] = DATA[id])) : reject(new Error('no data in data/' + id + '.js')));
      s.onerror = () => reject(new Error('data/' + id + '.js を読めません'));
      document.head.append(s);
    });
    return loading[id];
  }
  function fillDatasets() {
    const sel = $('#dataset');
    sel.textContent = '';
    META.datasets.forEach((d) => sel.append(h('option', { value: d.id }, d.label)));
    if (state.bundles.local) sel.append(h('option', { value: 'local' }, 'ローカルのファイル（' + state.localFiles.join('・') + '）'));
    sel.value = state.ds || META.datasets[0].id;
  }
  function notFound(what) { return [h('h1', { tabindex: '-1' }, '見つかりません'), h('p', null, what + ' はこの設計書にありません。')]; }

  function parseHash() {
    let raw = location.hash.replace(/^#\/?/, '');
    let query = '';
    const qi = raw.indexOf('?');
    if (qi >= 0) { query = raw.slice(qi + 1); raw = raw.slice(0, qi); }
    const parts = raw.split('/').map((x) => { try { return decodeURIComponent(x); } catch (e) { return x; } });
    return { parts, query };
  }
  function render() {
    const { parts, query } = parseHash();
    const main = $('#main');
    let ds = parts[0];
    if (ds === 'trace' || (ds === 'local' && (!parts[1] || !state.bundles.local))) return show(ds, () => (ds === 'trace' ? viewTrace() : viewLocal()));
    if (!ds) ds = META.datasets[0].id;
    const view = parts[1] || 'overview';
    const id = parts[2];
    const p = ds === 'local' ? Promise.resolve(state.bundles.local) : loadDataset(ds);
    return p.then(() => {
      state.ds = ds;
      fillDatasets();
      const fn = { overview: viewOverview, claims: () => viewClaims(query), claim: () => viewClaim(id), tokens: viewTokens, token: () => viewToken(id),
        profile: viewProfile, hops: viewHops, hop: () => viewHop(id), lifecycle: viewLifecycle, catalog: viewCatalog, lint: viewLint, tables: viewTables }[view];
      const navView = { claim: 'claims', token: 'tokens', hop: 'hops' }[view] || view;
      show(navView, fn || (() => notFound('画面 ' + view)));
    }).catch((e) => { main.textContent = ''; main.append(h('h1', null, '読み込めません'), h('p', { class: 'err' }, String(e.message || e))); });
  }
  function show(navView, fn) {
    if (!state.ds) state.ds = META.datasets[0].id;
    nav(navView);
    const main = $('#main');
    main.textContent = '';
    add(main, fn());
    const h1 = main.querySelector('h1');
    document.title = (h1 ? h1.textContent + ' ― ' : '') + '設計書のビューアー';
    if (render.focus && h1) h1.focus();
    render.focus = true;
    window.scrollTo(0, 0);
    return null;
  }

  function init() {
    if (!META) { $('#main').textContent = 'data/meta.js を読めません。'; return; }
    fillDatasets();
    $('#dataset').addEventListener('change', (e) => {
      // keep the screen (not the row: the other design has other rows)
      const cur = parseHash().parts[1];
      const keep = { claim: 'claims', token: 'tokens', hop: 'hops' }[cur] || (VIEWS.some((v) => v[0] === cur) ? cur : 'overview');
      location.hash = route(e.target.value, keep);
    });
    addEventListener('hashchange', render);
    addEventListener('keydown', (e) => {
      if (e.key === '/' && !/^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement.tagName)) {
        const s = $('#f-q');
        if (s) { e.preventDefault(); s.focus(); }
      }
    });
    render.focus = false;
    render();
  }
  init();
})();
