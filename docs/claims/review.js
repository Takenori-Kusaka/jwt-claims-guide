// Review mode of the design editor (#50). MIT (LICENSE of the repository).
// The reviewer answers the 168 questions of templates/review/perspectives.md (data/review.js, built from it by
// tools/build_claims_viewer.py), decides each row (承認・修正を求める・保留, bound to the row's content hash), records
// findings in the vocabulary of report_template.md, looks at the analysis (coverage, lint x review, the rows changed
// since a base version, the 25 answers, a seeded draw of rejection rationales) and writes review.yaml and the report.
// Nothing is sent: review.yaml is read with the File API and written with a download link, like the design files.
// The reviewer's name is self-declared (there is no login); the approval that counts is the GitHub pull request review.
'use strict';
(function () {
  // the build id (tools/build_claims_viewer.py, #53). An editor.js of another build (an old one kept in the browser's
  // cache) may not have what this module calls: then nothing is registered, and the banner asks for a reload
  const BUILD_ID = '94c6eed0c478';
  (window.CLAIMS_BUILD = window.CLAIMS_BUILD || {})['review.js'] = BUILD_ID;
  const CE = window.ClaimsEditor;
  const P = window.ClaimsPreview;
  if (CE && CE.BUILD_ID !== BUILD_ID) {
    if (CE.buildBanner) { CE.buildBanner(['review.js']); return; }
    if (document.getElementById('build-banner')) return;
    const el = document.createElement('div');
    el.id = 'build-banner'; el.className = 'buildwarn'; el.setAttribute('role', 'alert');
    const pp = document.createElement('p');
    const b = document.createElement('button');
    b.type = 'button'; b.id = 'build-reload'; b.className = 'primary'; b.textContent = '再読み込みする';
    b.addEventListener('click', () => location.reload());
    pp.append('新しい版が公開されました。再読み込みしてください。 ', b, ' （版のそろわないファイル：editor.js・review.js）');
    el.append(pp);
    document.body.prepend(el);
    return;
  }
  if (CE && CE.started === false) return;  // the editor did not start (files of two builds): it has said so
  // data/review.js (the questions, built from perspectives.md) is loaded when a design is opened, not with the page
  // (the first screen stays light, #49); until then R is empty
  let R = (window.CLAIMS_VIEWER_DATA || {}).review || null;
  if (!CE || !P) return;
  let loading = null;
  function loadData() {
    if (R) return Promise.resolve(R);
    if (!loading) {
      loading = new Promise((resolve, reject) => {
        const s = document.createElement('script');
        s.src = CE.asset('data/review.js');
        s.onload = () => {
          if ((window.CLAIMS_BUILD || {})['data/review.js'] !== BUILD_ID) { CE.buildBanner(['data/review.js']); loading = null; reject(new Error('stale')); return; }
          R = (window.CLAIMS_VIEWER_DATA || {}).review || null; if (R) { index(); resolve(R); } else reject(new Error('no data in data/review.js'));
        };
        s.onerror = () => { loading = null; reject(new Error('data/review.js を読めません')); };
        document.head.append(s);
      });
    }
    return loading;
  }
  const H = P.helpers;
  const $ = (s, r) => (r || document).querySelector(s);
  const own = (o, k) => o !== null && o !== undefined && Object.prototype.hasOwnProperty.call(o, k);

  const FORMAT = 'claims-review/1';
  const SLOT = 'claims-editor:review:v1:';
  const DEC = { approve: ['ok', '✓', '承認'], request_changes: ['ng', '✎', '修正を求める'], hold: ['warn', '⏸', '保留'] };
  const STALE = ['warn', '⟳', '再確認が要る'];
  const MISSING = ['neutral', '?', '台帳に無い行'];
  const ANS = { yes: ['ok', '✓', 'Yes'], no: ['ng', '✖', 'No'], na: ['neutral', '–', '該当なし'] };
  const KIND_LABEL = { claims: '台帳の行', token_types: 'トークン種別', hops: 'ホップ', catalog_answers: 'カタログへの回答', issuance_profile: '発行方式の項目' };
  const KIND_VIEW = { claims: 'claim', token_types: 'token', hops: 'hop' };
  let QBY = new Map(); let ROLE = new Map();
  function index() { QBY = new Map(R.questions.map((x) => [x.id, x])); ROLE = new Map(R.roles.map((x) => [x.id, x])); }
  if (R) index();
  const MISMATCH = '目的と仕組みの不一致';
  const KEY_ORDER = ['format', 'design', 'independent', 'reviews', 'reviewer', 'id', 'criterion', 'name', 'to', 'location', 'anchors',
    'questions', 'content', 'severity', 'origin', 'kind', 'model', 'confused_question', 'verdict', 'verdict_reason',
    'response', 'owner', 'due', 'state', 'ref', 'conclusion', 'self_declared', 'started', 'updated', 'submitted',
    'independence', 'mode', 'broken_at', 'viewed_others_at', 'target', 'commit', 'materials', 'perspectives',
    'report_template', 'context', 'lite_full', 'steps', 'roles_order', 'ci', 'error', 'warn', 'info',
    'profile', 'matches_design', 'human_check', 'answers', 'answer', 'memo', 'rows', 'decision', 'reviewer_kind',
    'hash', 'comment', 'edited_after_viewing_others', 'at', 'findings', 'sampling', 'seed', 'count', 'picked',
    'population', 'scores', 'RR1', 'RR2', 'RR3', 'RR4', 'RR5', 'RR6', 'RR7', 'pass', 'reason', 'previous',
    'replaced_at', 'escalations', 'applies', 'not_applicable', 'feedback', 'note'];
  const HEADER = '# review.yaml: レビューの記録（#50）。設計書のエディター（docs/claims/）のレビューモードが書き出した形。\n' +
    '# レビュアーの名前は自己申告です。本当の承認は GitHub の PR のレビューで行います。\n';

  // ------------------------------------------------------------ DOM helper (text only)
  function h(tag, attrs) {
    const el = document.createElement(tag);
    if (attrs) {
      for (const k of Object.keys(attrs)) {
        const v = attrs[k];
        if (v === null || v === undefined || v === false) continue;
        if (k === 'class') el.className = v;
        else if (k.slice(0, 2) === 'on') el.addEventListener(k.slice(2), v);
        else if (k === 'value') el.value = v;
        else el.setAttribute(k, v === true ? '' : String(v));
      }
    }
    if (tag === 'a' && /^https?:/i.test(el.getAttribute('href') || '')) { el.setAttribute('target', '_blank'); el.setAttribute('rel', 'noopener noreferrer'); }
    for (let i = 2; i < arguments.length; i++) add(el, arguments[i]);
    return el;
  }
  function add(el, c) {
    if (c === null || c === undefined || c === false) return;
    if (Array.isArray(c)) { c.forEach((x) => add(el, x)); return; }
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  function code(t) { return h('code', null, String(t)); }
  function badge(x, text, title) { return H.badge(x[0], x[1], text || x[2], title); }
  function gh(path, anchor) { return R.repo_blob + path + (anchor ? '#' + anchor : ''); }

  // ------------------------------------------------------------ review.yaml: the canonical text (tools/review_record.py dump)
  const ESCAPE = /[\x7f-\x9f\u2028\u2029\ufeff\ufffe\uffff]/g;
  function yq(s) { return JSON.stringify(String(s)).replace(ESCAPE, (c) => '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0')); }
  function ykey(k) { return /^[A-Za-z][A-Za-z0-9_-]*$/.test(k) && !/^(?:y|n|yes|no|on|off|true|false|null)$/i.test(k) ? k : yq(k); }
  function order(d) {
    const rank = new Map(KEY_ORDER.map((k, i) => [k, i]));
    return Object.keys(d).sort((a, b) => {
      const ra = rank.has(a) ? rank.get(a) : KEY_ORDER.length; const rb = rank.has(b) ? rank.get(b) : KEY_ORDER.length;
      if (ra !== rb) return ra - rb;
      if (rank.has(a)) return 0;
      return a < b ? -1 : a > b ? 1 : 0;
    });
  }
  function scalar(v) {
    if (v === null || v === undefined) return 'null';
    if (v === true) return 'true';
    if (v === false) return 'false';
    if (typeof v === 'number') return JSON.stringify(v);
    return yq(v);
  }
  const isObj = (x) => x !== null && typeof x === 'object' && !Array.isArray(x);
  function inline(x) {
    if (isObj(x)) return '{}';
    if (Array.isArray(x)) return '[' + x.map(scalar).join(', ') + ']';
    return scalar(x);
  }
  function emit(v, ind, out) {
    const pad = ' '.repeat(ind);
    if (isObj(v)) {
      order(v).forEach((k) => {
        const x = v[k];
        if ((isObj(x) && Object.keys(x).length) || (Array.isArray(x) && x.length && x.some((i) => i !== null && typeof i === 'object'))) {
          out.push(`${pad}${ykey(k)}:`);
          emit(x, ind + 2, out);
        } else out.push(`${pad}${ykey(k)}: ${inline(x)}`);
      });
    } else {
      v.forEach((x) => {
        if (isObj(x) && Object.keys(x).length) {
          const sub = [];
          emit(x, ind + 2, sub);
          out.push(pad + '- ' + sub[0].slice(ind + 2));
          sub.slice(1).forEach((l) => out.push(l));
        } else out.push(`${pad}- ${inline(x)}`);
      });
    }
  }
  // line 1 is the template_version of the review materials the records were made with (templates/CONTRIBUTING.md 4.:
  // every YAML under templates/ starts with it); a file read in keeps its own version
  function versionOf(text) { const m = /^# template_version: (\d+\.\d+\.\d+)/.exec(String(text || '')); return m ? m[1] : null; }
  function dump(data, version) {
    const out = []; emit(data, 0, out);
    return `# template_version: ${version || st.version || (R && R.template_version) || '0.0.0'}\n` + HEADER + out.join('\n') + '\n';
  }

  // ------------------------------------------------------------ state
  // file: the records (review.yaml); me: the name of the reviewer who records in this tab (self-declared)
  const st = { file: emptyFile(''), savedText: '', me: null, base: null, designRel: '', open: false, timer: null, focus: null, editFinding: null, wizard: 1 };
  function emptyFile(design) { return { format: FORMAT, design, independent: false, reviews: [] }; }
  function now() { return (RV.clock ? RV.clock() : new Date()).toISOString().slice(0, 19) + 'Z'; }
  function mine() { return st.me ? st.file.reviews.find((r) => r.reviewer.name === st.me) || null : null; }
  // independent review (#5): until the reviewer has submitted, the other reviewers' records are not shown to them.
  // This is only a screen: anyone can open review.yaml. What the editor can do is make leaving it deliberate (a dialog)
  // and recorded (independence.mode = broken, with when and why), and record when the reviewer first saw the others'
  // records (viewed_others_at) and which records were changed after that (edited_after_viewing_others).
  function broken(m) { return !!(m && m.independence && m.independence.mode === 'broken'); }
  function hiding() { const m = mine(); return !!st.file.independent && !(m && (m.submitted || broken(m))); }
  function locked() { const m = mine(); return !!st.file.independent && !!m && !m.submitted && !broken(m); }
  function visible() { if (!hiding()) return st.file.reviews; const m = mine(); return m ? [m] : []; }
  function hiddenCount() { return st.file.reviews.length - visible().length; }
  function breakIndependence(reason) {
    const m = mine();
    if (!locked()) return Promise.resolve(true);
    return CE.ask('独立レビューを外れる', `${m.reviewer.name} はまだ提出していません。この操作（${reason}）をすると、ほかのレビュアーの記録が見えるようになり、独立レビューを外れます。外れたことと理由・日時は review.yaml に記録され、レポートに出ます。`,
      [['cancel', 'やめる（独立レビューを続ける）'], ['break', '外れる（記録する）']]).then((c) => {
      if (c !== 'break') return false;
      m.independence = Object.assign({}, m.independence || {}, { mode: 'broken', broken_at: now(), reason });
      return true;
    });
  }
  // the first time the others' records are on screen for a reviewer of an independent review
  function noteViewing() {
    const m = mine();
    if (!m || hiding() || !(st.file.independent || m.independence) || (m.independence && m.independence.viewed_others_at)) return;
    const others = st.file.reviews.filter((r) => r !== m && (Object.keys(r.answers).length || Object.keys(r.rows).length || r.findings.length));
    if (!others.length) return;
    m.independence = Object.assign({ mode: 'kept' }, m.independence || {}, { viewed_others_at: now() });
    autosaveSoon();
  }
  function flagEdit(item) {
    const m = mine();
    if (m && m.independence && m.independence.viewed_others_at) item.edited_after_viewing_others = true;
    return item;
  }
  function unsaved() { return st.open && dump(st.file) !== st.savedText; }
  function changed(rerender) {
    const m = mine();
    if (m) m.updated = now();
    autosaveSoon();
    refreshCounts();
    if (rerender) { H.keepScroll(); P.render(); restoreFocus(); }
  }
  function restoreFocus() { if (st.focus) { const el = document.getElementById(st.focus); if (el) el.focus(); st.focus = null; } }

  // ------------------------------------------------------------ rows: anchors, hashes, states
  function anchorSet() { return new Set(CE.anchors().map((a) => a.anchor)); }
  function rowState(rec, anchor, set) {
    const cur = CE.rowHash(anchor);
    if (!(set || anchorSet()).has(anchor) || cur === null) return 'missing';
    return cur === rec.hash ? 'current' : 'stale';
  }
  // the badge of a decision always names the reviewer; an LLM's decision says that no person has checked it. The
  // details (when, the hashes) are in the text for screen readers too, not only in the title
  function stateBadge(rec, anchor, rv, set, shown) {
    const detail = (t) => h('span', { class: shown ? 'muted small rv-detail' : 'vh' }, shown ? ' ' + t : t);
    const s = rowState(rec, anchor, set);
    const d = DEC[rec.decision];
    const kind = rec.reviewer_kind || rv.reviewer.kind;
    const who = `（${rv.reviewer.name}` + (kind === 'llm' ? '・LLM、人による点検は未実施' : '・名前は自己申告') + '）';
    const attrs = (state) => ({ class: 'rvb', 'data-review-for': anchor, 'data-review-state': state, 'data-review-by': rv.reviewer.name, 'data-review-kind': kind });
    if (s === 'stale') {
      const why = `${d[2]} を記録した後に、行の内容が変わった（記録 ${rec.hash.slice(0, 12)}…、今 ${String(CE.rowHash(anchor)).slice(0, 12)}…）`;
      return h('span', attrs('stale'), badge(STALE, '再確認が要る' + who, why), detail(why));
    }
    if (s === 'missing') return h('span', attrs('missing'), badge(MISSING, '台帳に無い行' + who));
    const why = `${rec.at}${rec.comment ? '：' + rec.comment : ''}`;
    return h('span', attrs(rec.decision), badge(d, d[2] + who, why), detail(why));
  }
  function record(anchor, decision, comment) {
    const m = mine();
    if (!m) return false;
    const hash = CE.rowHash(anchor);
    if (!hash) return false;
    if (!decision) { delete m.rows[anchor]; changed(true); return true; }
    const rec = flagEdit({ decision, reviewer_kind: m.reviewer.kind, hash, at: now() });
    const c = comment !== undefined ? comment : (m.rows[anchor] && m.rows[anchor].comment) || '';
    if (c) rec.comment = c;
    m.rows[anchor] = rec;
    changed(true);
    return true;
  }
  function findingsOf(anchor) {
    const out = [];
    visible().forEach((rv) => rv.findings.forEach((f) => { if ((f.anchors || []).includes(anchor)) out.push([rv, f]); }));
    return out;
  }

  // the badges on every row of every screen, and the panel of the detail screens (registerRowPanel of #49)
  CE.registerRowPanel((anchor, row, kind, where) => {
    if (!st.open || !R) return null;
    const set = anchorSet();
    const recs = visible().filter((rv) => own(rv.rows, anchor)).map((rv) => [rv, rv.rows[anchor]]);
    const fs = findingsOf(anchor);
    if (recs.some(([rv]) => rv !== mine())) noteViewing();
    if (where !== 'detail') {
      if (!recs.length && !fs.length) return null;
      const list = fs.map(([, f]) => `${f.id} ${f.severity} ${f.content}`).join('／');
      return h('span', { class: 'codes rvbadges' }, recs.map(([rv, r]) => stateBadge(r, anchor, rv, set)),
        fs.length ? [badge(['info', '!', ''], `指摘 ${fs.length}`, list), h('span', { class: 'vh' }, '：' + list)] : null);
    }
    return rowPanel(anchor, recs, fs, set);
  });
  // rows the decision does not cover: the hash is of this row only (PR #52 check)
  function dependents(anchor) {
    const i = anchor.indexOf(':'); const kind = anchor.slice(0, i); const id = anchor.slice(i + 1);
    const out = [];
    const r = CE.rowOf(anchor);
    if (!r || !r.row) return out;
    if (kind === 'claims') {
      (Array.isArray(r.row.carried_in) ? r.row.carried_in : []).forEach((t) => out.push(['token_types:' + t, '載るトークン種別']));
      CE.anchors().filter((a) => a.kind === 'hops' && a.row && Array.isArray(a.row.custom_claims) && a.row.custom_claims.includes(id)).forEach((a) => out.push([a.anchor, 'この行を運ぶホップ']));
      paFiles().filter((f) => f.target === id).forEach((f) => out.push([f.name, '追加前の 25 問の回答']));
    }
    if (kind === 'hops') {
      if (r.row.token_type) out.push(['token_types:' + r.row.token_type, 'ホップのトークン種別']);
      [].concat(r.row.upstream || []).forEach((u) => out.push(['hops:' + u, '上流のホップ']));  // one ID or a list (#58)
    }
    if (kind === 'token_types') CE.anchors().filter((a) => a.kind === 'claims' && a.row && Array.isArray(a.row.carried_in) && a.row.carried_in.includes(id)).slice(0, 40).forEach((a) => out.push([a.anchor, '載る台帳の行']));
    return out;
  }
  function rowPanel(anchor, recs, fs, set) {
    const m = mine();
    const hash = CE.rowHash(anchor);
    const cur = m && m.rows[anchor];
    const deps = dependents(anchor);
    const box = h('section', { class: 'rv-panel', 'aria-labelledby': 'rvp-h', 'data-review-panel': anchor },
      h('h2', { id: 'rvp-h' }, 'この行のレビュー'),
      h('p', { class: 'muted small' }, '判定は、記録した時のこの行の中身に結びつきます。行を変えると「再確認が要る」になります。', h('span', { title: '行の中身のハッシュ（RFC 8785 で正規化した JSON の SHA-256）' }, '（照合に使う値：', code(hash ? hash.slice(0, 16) + '…' : 'なし'), '）')),
      deps.length ? h('details', { class: 'small', 'data-dependents': anchor }, h('summary', null, `依存する行 ${deps.length} 件（変えても、この判定は「再確認が要る」にならない）`),
        h('ul', null, deps.map(([a, why]) => h('li', null, /^claim_request_/.test(a) ? code(a) : rowLink(a), `：${why}`)))) : null);
    if (!hash) box.append(h('p', { class: 'note warn' }, 'この行にはハッシュが無い（ID が 2 行以上にある、またはハッシュにできない値がある）ので、判定を記録できません。'));
    else if (!m) box.append(h('p', null, '判定を記録するには、', h('a', { href: P.route('review') }, 'レビューを始める'), 'でレビュアーの名前を決めてください。'));
    else {
      const fid = 'rvp-' + anchor.replace(/[^A-Za-z0-9_-]/g, '_');
      const comment = h('textarea', { id: fid + '-c', rows: '2', class: 'rv-comment', 'aria-label': 'コメント' }, cur && cur.comment ? cur.comment : '');
      const radios = h('fieldset', { class: 'rv-dec' }, h('legend', null, `判定（${m.reviewer.name}）`),
        Object.keys(DEC).map((k) => h('label', null, h('input', { type: 'radio', name: fid, value: k, checked: cur && cur.decision === k ? true : null, 'data-decide': anchor }), ' ', DEC[k][1], ' ', DEC[k][2])));
      box.append(h('form', { class: 'rv-form', onsubmit: (e) => {
        e.preventDefault();
        const sel = radios.querySelector('input:checked');
        if (!sel) return;
        st.focus = fid + '-save';
        record(anchor, sel.value, comment.value.trim());
      } }, radios, h('label', { for: fid + '-c' }, 'コメント（修正を求めるなら、指摘の ID も）'), comment,
      h('p', null, h('button', { type: 'submit', class: 'primary', id: fid + '-save', 'data-record': anchor }, '記録する'), ' ',
        cur ? h('button', { type: 'button', 'data-unrecord': anchor, onclick: () => CE.ask('判定を消す', `${anchor} の、${m.reviewer.name} の判定を消します。`, [['delete', '消す'], ['cancel', 'やめる']])
          .then((c) => { if (c === 'delete') record(anchor, null); }) }, '判定を消す') : null, ' ',
        h('button', { type: 'button', onclick: () => { newFinding({ anchors: [anchor], location: anchor.replace(/^claims:/, '') }); } }, '指摘を足す'))));
    }
    if (recs.length) {
      box.append(h('h3', null, '記録'), h('ul', { class: 'rv-recs' }, recs.map(([rv, r]) => h('li', null, stateBadge(r, anchor, rv, set, true)))));
    }
    if (hiding() && hiddenCount()) box.append(h('p', { class: 'muted small', 'data-hidden-others': String(hiddenCount()) }, `独立レビュー：提出するまで、ほかのレビュアー ${hiddenCount()} 人の記録を隠しています。`));
    if (fs.length) box.append(h('h3', null, 'この行の指摘'), h('ul', null, fs.map(([rv, f]) => h('li', null, code(f.id), ' ', f.severity, '・', f.kind, '：', H.inline(f.content), st.file.reviews.length > 1 ? h('span', { class: 'muted' }, `（${rv.reviewer.name}）`) : null))));
    return box;
  }

  // ------------------------------------------------------------ opening, saving, the slot of this browser
  function slotKey() { return SLOT + st.designRel; }
  function readSlot() { try { const raw = localStorage.getItem(slotKey()); return raw ? JSON.parse(raw) : null; } catch (e) { return null; } }
  function autosaveSoon() { clearTimeout(st.timer); st.timer = setTimeout(autosave, 800); }
  // true when the records are in the slot. A failure keeps them counted as not saved (closing and leaving still ask)
  // and leaves a warning on screen, as for the design files. While an autosaved version is waiting for a choice
  // (slotHold), nothing is written over it.
  function autosave() {
    if (!st.open || !CE.autosaveEnabled() || !unsaved()) return false;
    if (st.slotHold) { holdWarning(); return false; }
    try {
      localStorage.setItem(slotKey(), JSON.stringify({ savedAt: new Date().toISOString().replace('T', ' ').slice(0, 19), me: st.me, text: dump(st.file) }));
      CE.saveWarning(null, 'review');
      return true;
    } catch (e) {
      CE.saveWarning(`レビューの記録の自動保存に失敗しました（${e.name || 'Error'}：${e.message || e}）。今の記録はこのブラウザに保存されていません。「review.yaml を書き出す」で保存してください。`, 'review');
      return false;
    }
  }
  function holdWarning() {
    CE.saveWarning('このブラウザに自動保存したレビューの記録が残っていて、どれを使うかが決まっていないので、レビューの記録の自動保存を止めています（上書きしない）。レビューの概要の「自動保存した記録」で選んでください。', 'review');
  }
  // the autosaved records of this design and the ones opened differ: asked; Esc or a slot that cannot be read leaves
  // the slot as it is and stops autosaving the records until a choice is made (nothing is overwritten silently)
  function askSlot(sv) {
    const r = parseReview(sv.text, '自動保存した記録');
    if (r.error) {
      st.slotHold = sv;
      holdWarning();
      return CE.ask('自動保存した記録を読めません', r.error + '。自動保存した記録は消さずに残し、レビューの記録の自動保存を止めます。', [['ok', '閉じる']]).then(() => null);
    }
    return CE.ask('自動保存したレビューの記録があります', `この設計書（${st.designRel}）には、このブラウザに自動保存したレビューの記録（${sv.savedAt} に保存）があります。「開いた記録を使う」を選ぶと、自動保存した記録は次の保存で上書きされます。`,
      [['saved', '自動保存した記録を開く'], ['opened', '開いた記録を使う（自動保存した記録は上書きされる）'], ['merge', '両方を合わせる'], ['cancel', 'あとで決める（自動保存を止める）']]).then((c) => {
      if (c === 'saved') { st.slotHold = null; CE.saveWarning(null, 'review'); setFile(r.data, st.savedText, sv.me, sv.text); return null; }
      if (c === 'opened') { st.slotHold = null; CE.saveWarning(null, 'review'); return null; }
      if (c === 'merge') {
        st.slotHold = null; CE.saveWarning(null, 'review');
        return mergeIn([r.data]).then(() => { if (sv.me && st.file.reviews.some((x) => x.reviewer.name === sv.me)) st.me = sv.me; });
      }
      st.slotHold = sv;
      holdWarning();
      return null;
    });
  }
  function setFile(data, savedText, me, text) {
    st.version = versionOf(text || savedText) || (R && R.template_version);
    st.file = data;
    st.savedText = savedText;
    st.me = me && data.reviews.some((r) => r.reviewer.name === me) ? me : null;
  }
  // a review.yaml text -> {data} or {error}; checked with templates/review/review.schema.json and the questions
  function parseReview(text, name) {
    let v;
    try { v = CE.parseYaml(text); } catch (e) { return { error: `${name}：YAML の誤り（${e.message}）` }; }
    const errs = CE.validate('review', v);
    if (errs.length) return { error: `${name}：review.schema.json に合わない（` + errs.slice(0, 4).map((e) => `${e.path}：${e.message}`).join('、') + (errs.length > 4 ? ` ほか ${errs.length - 4} 件` : '') + '）' };
    const bad = [];
    const names = v.reviews.map((r) => r.reviewer.name);
    names.forEach((n, i) => { if (names.indexOf(n) !== i) bad.push(`レビュアー ${n} が 2 回ある`); });
    v.reviews.forEach((rv) => {
      Object.keys(rv.answers).forEach((q) => { if (!QBY.has(q)) bad.push(`${rv.reviewer.name}：問い ${q} は観点書に無い`); });
      const ids = rv.findings.map((f) => f.id);
      ids.forEach((x, i) => { if (ids.indexOf(x) !== i) bad.push(`${rv.reviewer.name}：指摘 ${x} が 2 つある`); });
    });
    if (bad.length) return { error: `${name}：` + bad.slice(0, 4).join('、') };
    return { data: v };
  }
  function companionOpen(info) {
    st.opening = true;
    loadData().then(() => companionOpen2(info), (e) => { st.opening = false; if (e.message !== 'stale') CE.ask('レビューを使えません', String(e.message || e), [['ok', '閉じる']]); });
  }
  function companionOpen2(info) {
    st.open = true;
    st.designRel = info.designRel;
    st.base = null;
    st.editFinding = null;
    const empty = emptyFile(info.designRel);
    setFile(empty, dump(empty), null);
    const extra = (info.extras || []).filter((e) => /^review\.ya?ml$/.test(e.name));
    let p = Promise.resolve();
    if (extra.length) {
      const r = parseReview(extra[0].text, extra[0].name);
      if (r.error) CE.ask('review.yaml を読めません', r.error + '。レビューの記録は空で始めます（ファイルはそのまま）。', [['ok', '閉じる']]);
      else if (r.data.design !== info.designRel) {
        p = CE.ask('review.yaml の設計書が違います', `review.yaml は ${r.data.design} の記録です。開いた設計書は ${info.designRel} です。`, [['load', 'この設計書の記録として読む'], ['skip', '読まない']])
          .then((c) => { if (c === 'load') { r.data.design = info.designRel; setFile(r.data, '', null); } });
      } else setFile(r.data, extra[0].text.replace(/\r\n/g, '\n'), null);
    }
    p.then(() => {
      st.slotHold = null;
      CE.saveWarning(null, 'review');
      let sv = null;
      try { const raw = localStorage.getItem(slotKey()); sv = raw ? JSON.parse(raw) : null; } catch (e) { sv = { savedAt: '不明', text: '\u0000' }; }
      if (sv && typeof sv.text !== 'string') sv = { savedAt: sv.savedAt || '不明', text: '\u0000' };
      if (sv && sv.text !== dump(st.file)) return askSlot(sv);
      return null;
    }).then(() => { st.opening = false; st.wizard = mine() ? null : 1; CE.publish(); });
  }
  // merge review files into the open records; a reviewer who is in both with different records is asked about
  function mergeIn(datas) {
    let p = Promise.resolve();
    datas.forEach((d) => d.reviews.forEach((rv) => {
      p = p.then(() => {
        const i = st.file.reviews.findIndex((x) => x.reviewer.name === rv.reviewer.name);
        if (i < 0) { st.file.reviews.push(rv); return null; }
        if (JSON.stringify(st.file.reviews[i]) === JSON.stringify(rv)) return null;
        const alt = freeName(rv.reviewer.name);
        return CE.ask('同じレビュアーの記録が 2 つあります', `「${rv.reviewer.name}」の記録が、開いている記録と読み込む記録で違います（回答 ${Object.keys(st.file.reviews[i].answers).length}・${Object.keys(rv.answers).length} 問、行 ${Object.keys(st.file.reviews[i].rows).length}・${Object.keys(rv.rows).length}、指摘 ${st.file.reviews[i].findings.length}・${rv.findings.length}）。`,
          [['both', `両方残す（読み込むほうを「${alt}」にする）`], ['replace', '読み込むほうで置き換える（開いている記録は消える）'], ['keep', '開いている記録を残す（読み込むほうは使わない）']])
          .then((c) => {
            if (c === 'replace') st.file.reviews[i] = rv;
            else if (c === 'both' || c === 'cancel') { rv.reviewer.name = alt; st.file.reviews.push(rv); }
          });
      });
    }));
    return p.then(() => { if (datas.some((d) => d.independent)) st.file.independent = true; });
  }
  function freeName(n) { for (let i = 2; ; i++) { const c = `${n} (${i})`; if (!st.file.reviews.some((r) => r.reviewer.name === c)) return c; } }
  function importFiles(list) {
    return Promise.all(Array.from(list || []).map((f) => f.text().then((t) => ({ name: f.name, text: t })))).then((xs) => {
      const ok = []; const errs = [];
      xs.forEach((x) => { const r = parseReview(x.text, x.name); if (r.error) errs.push(r.error); else ok.push([x, r.data]); });
      const other = ok.filter(([, d]) => d.design !== st.designRel);
      let p = Promise.resolve(true);
      if (other.length) {
        p = CE.ask('別の設計書の記録があります', other.map(([x, d]) => `${x.name} は ${d.design} の記録です`).join('。') + `。開いている設計書は ${st.designRel} です。`,
          [['load', 'この設計書の記録として合わせる'], ['skip', 'その記録は読まない']]).then((c) => c === 'load');
      }
      return p.then((takeOther) => {
        const use = ok.filter(([, d]) => takeOther || d.design === st.designRel);
        const wasClean = !unsaved() && !st.file.reviews.length;
        return mergeIn(use.map(([, d]) => d)).then(() => {
          if (wasClean && use.length === 1 && use[0][1].design === st.designRel) st.savedText = use[0][0].text.replace(/\r\n/g, '\n');
          st.file.design = st.designRel;
          if (errs.length) CE.ask('読めなかった review.yaml', errs.join('\n'), [['ok', '閉じる']]);
          if (st.afterImport && use.length) { st.wizard = st.afterImport; }
          st.afterImport = null;
          changed(true);
          return { loaded: use.length, errors: errs };
        });
      });
    });
  }
  // writing every reviewer's records while the others are hidden is leaving the independent review: asked and recorded
  function exportAll() {
    if (!(hiding() && hiddenCount())) return Promise.resolve(exportReview(false));
    return CE.ask('全員の記録を書き出す', `独立レビューの間は、ほかのレビュアー ${hiddenCount()} 人の記録を画面で隠しています。全員の記録を書き出すと、そのファイルで見えます。`,
      [['mine', '自分の記録だけ書き出す'], ['all', '全員の記録を書き出す（独立レビューを外れたと記録する）'], ['cancel', 'やめる']]).then((c) => {
      if (c === 'mine') return exportReview(true);
      if (c !== 'all') return null;
      const m = mine();
      if (m) m.independence = Object.assign({}, m.independence || {}, { mode: 'broken', broken_at: now(), reason: '提出の前に全員の記録を書き出した' });
      const t = exportReview(false);
      changed(true);
      return t;
    });
  }
  function exportReview(onlyMine) {
    const m = mine();
    const data = onlyMine && m ? Object.assign({}, st.file, { reviews: [m] }) : st.file;
    const text = dump(data);
    CE.download(onlyMine && m ? `review-${m.reviewer.name.replace(/[^A-Za-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '') || 'mine'}.yaml` : 'review.yaml', new Blob([text], { type: 'text/yaml' }));
    if (!onlyMine) st.savedText = text;
    refreshCounts();
    return text;
  }
  CE.registerCompanion({
    label: 'レビューの記録（review.yaml）',
    unsaved,
    autosave: () => { if (!unsaved()) return true; return autosave(); },
    exportEntries: () => (st.file.reviews.length || unsaved() ? [{ name: 'review.yaml', text: dump(st.file) }] : []),
    markSaved: () => { st.savedText = dump(st.file); },
    // "zip で書き出す" (and the export of the dialogs that close or replace the design): while the others' records are
    // hidden (independent review, not submitted), only one's own records by default; every record only after a
    // question, and that is recorded as leaving the independent review (PR #52 re-check)
    prepareExport: () => {
      const full = () => ({ entries: st.file.reviews.length || unsaved() ? [{ name: 'review.yaml', text: dump(st.file) }] : [], markSaved: () => { st.savedText = dump(st.file); } });
      if (!(hiding() && hiddenCount())) return Promise.resolve(full());
      return CE.ask('zip に入れる review.yaml', `独立レビューの間は、ほかのレビュアー ${hiddenCount()} 人の記録を画面で隠しています。zip の review.yaml には、ふつうは自分の記録だけを入れます（ほかの記録はこのタブに残り、書き出していないものとして扱います）。`,
        [['mine', '自分の記録だけ入れる'], ['all', '全員の記録を入れる（独立レビューを外れたと記録する）'], ['cancel', 'やめる']]).then((c) => {
        if (c === 'mine') { const m = mine(); return { entries: [{ name: 'review.yaml', text: dump(Object.assign({}, st.file, { reviews: m ? [m] : [] })) }], markSaved: null }; }
        if (c !== 'all') return null;
        const m = mine();
        if (m) m.independence = Object.assign({}, m.independence || {}, { mode: 'broken', broken_at: now(), reason: '提出の前に全員の記録を zip で書き出した' });
        changed(false);
        return full();
      });
    },
    slotKey: () => (st.open ? slotKey() : null),
    onOpen: companionOpen,
    onClose: () => { st.slotHold = null; CE.saveWarning(null, 'review'); st.open = false; st.file = emptyFile(''); st.savedText = dump(st.file); st.me = null; st.base = null; },
    onExtras: (extras) => {
      const r = extras.filter((e) => /^review/.test(e.name));
      if (r.length) importFiles(r.map((e) => ({ name: e.name, text: () => Promise.resolve(e.text) })));
    },
    loadForeign: () => {
      const sv = readSlot();
      if (!sv) return;
      const r = parseReview(sv.text, '別のタブの記録');
      if (r.error) return;
      const go = () => { setFile(r.data, st.savedText, sv.me || st.me); changed(true); };
      if (unsaved()) CE.ask('このタブの記録を置き換える', 'このタブには、まだ書き出していないレビューの記録があります。別のタブの記録で置き換えると、このタブの記録は消えます。',
        [['replace', '置き換える'], ['merge', '合わせる（同じレビュアーで違うものは確かめる）'], ['cancel', 'やめる']]).then((c) => {
        if (c === 'replace') go(); else if (c === 'merge') mergeIn([r.data]).then(() => changed(true));
      });
      else go();
    },
  });

  // ------------------------------------------------------------ jump to 見る欄
  function designHeadLine(ref) {
    const head = R.template_heads[ref.ref];
    const text = CE.fileText('design.md');
    if (!head || text === null || !head.title && !head.number) return null;
    const lines = text.split(/\r?\n/);
    const clean = (s) => s.replace(/〔[^〕]*〕/g, '').replace(/^#+\s*/, '').trim();
    for (let i = 0; i < lines.length; i++) {
      if (!/^#{1,6}\s/.test(lines[i])) continue;
      const t = clean(lines[i]);
      if (head.number && (t.startsWith(head.number + ' ') || t === head.number)) return i + 1;
      if (!head.number && head.title && t.startsWith(head.title)) return i + 1;
    }
    return null;
  }
  function seeLink(ref) {
    const r = ref;
    const label = r.ref;
    if (r.kind === 'registry' && ['claims', 'token_types', 'hops'].includes(r.path) && r.anchor) {
      return h('a', { href: P.route('review', 'col') + '/' + r.path + '/' + encodeURIComponent(r.anchor), 'data-see': label, class: 'see' }, label);
    }
    if (r.kind === 'template' && r.path === 'claim_request' && /^q\d\d$/.test(r.anchor)) {
      return h('a', { href: '#/review/pa?q=' + Number(r.anchor.slice(1)), 'data-see': label, class: 'see' }, label);
    }
    if (r.kind === 'template' && r.path === '00_core') {
      const line = designHeadLine(r);
      const head = R.template_heads[r.ref] || {};
      if (line) return h('button', { type: 'button', class: 'link see', 'data-see': label, 'data-see-line': String(line), title: `design.md の ${line} 行（${head.number || ''} ${head.title || ''}）をエディターで開く`,
        onclick: () => CE.goto('design.md', line) }, label);
      return h('a', { href: gh('templates/00_core.md', r.anchor), 'data-see': label, class: 'see', title: '設計書（design.md）が開かれていないので、テンプレートの節を開く' }, label);
    }
    if (r.kind === 'template') return h('a', { href: gh('templates/' + r.path + '.md', r.anchor), 'data-see': label, class: 'see', title: 'テンプレートのモジュール・プロファイルの欄（設計書の外）' }, label);
    if (r.kind === 'registry') return h('a', { href: gh(r.path === 'README' ? 'templates/registry/README.md' : 'templates/registry/' + r.path + '.yaml', r.anchor), 'data-see': label, class: 'see' }, label);
    if (r.kind === 'catalog') return h('a', { href: gh('templates/catalog/' + r.path + (r.path === 'sources' ? '.md' : '.yaml'), r.anchor), 'data-see': label, class: 'see' }, label);
    if (r.kind === 'review') return h('a', { href: gh('templates/review/' + r.path + '.md', r.anchor), 'data-see': label, class: 'see' }, label);
    return code(label);
  }

  // ------------------------------------------------------------ screens
  function needOpen() { return [h('h1', { tabindex: '-1' }, 'レビュー'), h('p', null, st.opening ? 'レビューの記録を読み込んでいます…' : '設計書を開いてから使います。')]; }
  function selfDeclared() {
    return h('div', { class: 'note warn', id: 'rv-self-declared' }, h('p', null, h('strong', null, 'レビュアーの名前は自己申告です。'),
      '本当の承認は GitHub の pull request のレビューで行います。', h('details', null, h('summary', null, '詳しく'), h('p', null, 'このエディターにはログインが無く、名前は誰でも書けます。ここでの記録（review.yaml）は、その pull request にコミットし、Git の履歴を監査の記録にします。'))));
  }
  // switching the reviewer of this tab: to another name of the records, a deliberate act (a dialog), and while the
  // current reviewer's independent review is not submitted, leaving it (recorded)
  function switchTo(name, typed) {
    if (!name || name === st.me) { if (!name) { st.me = null; changed(true); } return Promise.resolve(); }
    const target = st.file.reviews.find((r) => r.reviewer.name === name);
    const p = locked() ? breakIndependence(`提出の前に別のレビュアー「${name}」の記録に切り替えた`)
      : CE.ask('既にあるレビュアーの記録で続ける', `「${name}」の記録（${target && target.submitted ? '提出済み' : '未提出'}）に切り替えます。名前は自己申告なので、この操作で、ほかの人の記録を自分のものとして直せてしまいます。${typed ? '同じ名前を打ちました。' : ''}本人のときだけ続けてください。`,
        [['go', '続ける'], ['cancel', 'やめる']]).then((c) => c === 'go');
    return p.then((ok) => { if (ok) st.me = name; changed(true); });
  }
  // a new reviewer: in the overview, and as step 1 of the stepper
  function newForm(m, name, kind, model, onDone) {
    return h('form', { class: 'filters', id: 'rv-new', onsubmit: (e) => {
        e.preventDefault();
        const n = name.value.trim();
        if (!n) { name.focus(); return; }
        if (st.file.reviews.some((r) => r.reviewer.name === n)) { switchTo(n, true).then(() => { if (st.wizard === 1 && st.me === n) { st.wizard = 2; changed(true); } }); return; }
        const go = () => {
          const rv = { reviewer: { name: n, kind: kind.value }, self_declared: true, started: now(), submitted: null,
            materials: { perspectives: R.template_version, report_template: (R.versions || {})['templates/review/report_template.md'] || R.template_version, questions: R.questions.length },
            answers: {}, rows: {}, findings: [] };
          if (model.value.trim()) rv.reviewer.model = model.value.trim();
          if (st.file.independent) rv.independence = { mode: 'kept' };
          st.file.reviews.push(rv);
          st.me = n;
          if (st.wizard === 1) st.wizard = 2;
          changed(true);
          if (onDone) onDone();
        };
        // a new reviewer while I have not submitted: the new name would see nothing of mine, but I leave my review
        if (locked()) breakIndependence(`新しいレビュアー「${n}」に切り替えた`).then((ok) => { if (ok) go(); else P.render(); }); else go();
      } }, h('label', null, '名前（自己申告）', name), h('label', null, '種類', kind), h('label', null, 'モデル（LLM のとき）', model),
      h('div', null, h('button', { type: 'submit', class: 'primary', id: 'rv-new-go' }, m ? '新しいレビュアーを足す' : '始める')));
  }
  // レビューを始める (#53): one step at a time. 1. the reviewer, 2. records to read or a new start, 3. independent or not,
  // 4. on to the checklist. Recording is possible from the end of step 1 (the name is enough); the rest has defaults.
  const STEPS = ['レビュアー', '記録のファイル', '独立レビュー', 'チェックリストへ'];
  function stepper(m, f) {
    const n = st.wizard;
    const go = (k) => { st.wizard = k; st.focus = 'rv-step-h'; changed(true); };
    const back = n > 1 ? h('button', { type: 'button', class: 'link', id: 'rv-step-back', onclick: () => go(n - 1) }, '← 戻る') : null;
    const skip = h('button', { type: 'button', class: 'link small', id: 'rv-step-close', onclick: () => go(null) }, '手順を閉じる');
    let body;
    if (n === 1) {
      body = [h('p', null, '名前と、人か LLM かを入れて「始める」を押します。名前は自己申告です。'),
        newForm(m, f.name, f.kind, f.model),
        st.file.reviews.length ? h('p', null, h('label', { for: 'rv-pick' }, 'または、記録にあるレビュアーで続ける：'), f.pick, ' ',
          h('button', { type: 'button', id: 'rv-pick-go', onclick: () => switchTo(f.pick.value || null).then(() => { if (st.me && st.wizard === 1) go(2); }) }, 'このレビュアーで続ける')) : null];
    } else if (n === 2) {
      const others = st.file.reviews.filter((r) => r !== m).length;
      body = [h('p', null, others ? `いま開いている記録には、ほかのレビュアー ${others} 人の記録があります。` : '前のレビューの記録（review.yaml）があれば読み込みます。無ければ、このまま新しく始めます。'),
        h('p', { class: 'buttons' }, h('button', { type: 'button', id: 'rv-step-import', onclick: () => { st.afterImport = 3; $('#rv-import').click(); } }, 'review.yaml を読み込む'),
          h('button', { type: 'button', class: 'primary', id: 'rv-step-new', onclick: () => go(3) }, others ? 'このまま進む' : '新しく始める'))];
    } else if (n === 3) {
      body = [h('p', null, '独立レビューにすると、提出するまで、ほかのレビュアーの記録を画面に出しません。'),
        h('p', { class: 'buttons' }, h('button', { type: 'button', id: 'rv-step-ind-on', 'aria-pressed': st.file.independent ? 'true' : 'false', onclick: () => {
          st.file.independent = true; const me = mine(); if (me && !me.submitted && !me.independence) me.independence = { mode: 'kept' }; go(4);
        } }, '独立レビューにする'),
        h('button', { type: 'button', class: 'primary', id: 'rv-step-ind-off', onclick: () => {
          if (!st.file.independent) { go(4); return; }
          breakIndependence('独立レビューの設定を外した').then((ok) => { if (ok) st.file.independent = false; go(ok ? 4 : 3); });
        } }, st.file.independent ? '独立レビューをやめる' : 'しない（ふつうのレビュー）')),
        h('details', null, h('summary', null, '詳しく'), h('p', null, '独立レビューは、ほかの人の答えに引きずられないための決まりです（templates/review/procedure.md）。画面で隠すだけなので、review.yaml を開けば誰でも読めます。隠すのをやめる操作は確かめ、外れたことと日時・理由を記録します。'))];
    } else {
      body = [h('p', null, '準備ができました。観点の問いに答えるか、設計書の画面で行ごとに判定します。'),
        h('p', { class: 'buttons' }, h('a', { class: 'btn primary', id: 'rv-step-go', href: P.route('review', 'checklist'), onclick: () => { st.wizard = null; } }, '観点のチェックリストへ'),
          h('a', { class: 'btn', id: 'rv-step-rows', href: P.route('claims'), onclick: () => { st.wizard = null; } }, '台帳の行を判定する（クレームの一覧へ）'))];
    }
    return h('section', { class: 'stepper', id: 'rv-stepper', 'data-step': String(n), 'aria-labelledby': 'rv-step-h' },
      h('ol', { class: 'steps' }, STEPS.map((t, i) => h('li', { 'aria-current': i + 1 === n ? 'step' : null, class: i + 1 < n ? 'done' : null }, `${i + 1}. ${t}`))),
      h('h2', { id: 'rv-step-h', tabindex: '-1' }, `${n}. ${STEPS[n - 1]}`), body, h('p', { class: 'small' }, back, ' ', skip));
  }
  function viewOverview() {
    const m = mine();
    const name = h('input', { type: 'text', id: 'rv-name', 'aria-describedby': 'rv-self-declared', autocomplete: 'off' });
    const kind = h('select', { id: 'rv-kind' }, h('option', { value: 'human' }, '人'), h('option', { value: 'llm' }, 'LLM'));
    const model = h('input', { type: 'text', id: 'rv-model', placeholder: 'LLM ならモデルとセッション' });
    const pick = h('select', { id: 'rv-pick', 'aria-label': '記録するレビュアー' }, h('option', { value: '' }, '（選ぶ）'),
      st.file.reviews.map((r) => h('option', { value: r.reviewer.name, selected: r.reviewer.name === st.me ? true : null }, r.reviewer.name)));
    const imp = h('input', { type: 'file', id: 'rv-import', multiple: true, accept: '.yaml,.yml', class: 'vh', tabindex: '-1', 'aria-hidden': 'true' });
    imp.addEventListener('change', () => importFiles(imp.files));
    const vis = visible();
    const set = anchorSet();
    const lost = []; const stale = [];
    vis.forEach((rv) => Object.keys(rv.rows).forEach((a) => {
      const s = rowState(rv.rows[a], a, set);
      if (s === 'missing') lost.push([rv, a]); else if (s === 'stale') stale.push([rv, a]);
    }));
    const wiz = st.wizard ? stepper(m, { name, kind, model, pick }) : null;
    return [h('h1', { tabindex: '-1' }, 'レビュー', ' ', h('span', { class: 'muted small' }, wiz ? 'はじめる' : '記録の概要')),
      wiz,
      h('p', { class: 'lead' }, '観点の問い（', R.questions.length, ' 問）に答え、台帳の行ごとに判定し、指摘を記録します。記録はファイル（review.yaml）に書き出して、設計書と一緒に管理します。', h('span', { class: 'muted small' }, ' 問いの出典：templates/review/perspectives.md')),
      selfDeclared(),
      h('h2', null, '記録するレビュアー'),
      h('p', { 'data-me': st.me || '' }, m ? ['いま記録しているのは ', h('strong', null, m.reviewer.name), `（${m.reviewer.kind === 'llm' ? 'LLM' : '人'}、自己申告）`, m.submitted ? `。${m.submitted} に提出済み` : '。未提出'] : 'レビュアーが決まっていません（回答・判定・指摘の記録には、名前が要ります）。'),
      st.file.reviews.length && !(wiz && !m) ? h('p', null, h('label', { for: 'rv-pick' }, '記録にあるレビュアーから選ぶ：'), pick, ' ', h('button', { type: 'button', id: 'rv-pick-go', onclick: () => switchTo(pick.value || null) }, 'このレビュアーで記録する')) : null,
      wiz && !m ? null : newForm(m, name, kind, model),
      h('h2', null, '独立レビュー'),
      h('p', null, h('label', { class: 'chk' }, h('input', { type: 'checkbox', id: 'rv-independent', checked: st.file.independent ? true : null, onchange: (e) => {
        const on = e.target.checked;
        if (on) { st.file.independent = true; const me = mine(); if (me && !me.submitted && !me.independence) me.independence = { mode: 'kept' }; changed(true); return; }
        e.target.checked = true;
        breakIndependence('独立レビューの設定を外した').then((ok) => { if (ok) { st.file.independent = false; } changed(true); });
      } }),
        ' 提出するまで、ほかのレビュアーの記録（回答・判定・指摘）を隠す'), h('span', { class: 'muted small' }, '（合わせて読み込んだ記録も、提出の後に見えます。手順：templates/review/procedure.md）')),
      h(st.file.independent ? 'p' : 'details', { class: 'note warn', id: 'rv-independence-limits' }, st.file.independent ? null : h('summary', null, '独立レビューでできないこと'), h('strong', null, '独立レビューは画面で隠すだけです。'),
        'review.yaml を開けば、ほかのレビュアーの記録は誰でも読めます。このエディターにできるのは、提出の前に隠すのをやめる操作（ほかのレビュアーへの切り替え・設定を外す・全員の記録の書き出し）を確かめ、外れたことと日時・理由を review.yaml に記録すること、ほかの記録を初めて見た日時と、その後に直した記録に印を付けることだけです。守ったかどうかは、名前と同じく自己申告で、手順（procedure.md）で守ります。'),
      m && m.independence ? h('p', { id: 'rv-independence', 'data-mode': m.independence.mode }, '自分の独立レビュー：', m.independence.mode === 'broken' ? `提出の前に外れた（${m.independence.broken_at}、${m.independence.reason || ''}）` : '続けている',
        m.independence.viewed_others_at ? `。ほかの記録を初めて見た日時 ${m.independence.viewed_others_at}（その後に直した記録には印が付く）` : '') : null,
      hiding() && hiddenCount() ? h('p', { class: 'note', id: 'rv-hidden', 'data-hidden-others': String(hiddenCount()) }, `ほかのレビュアー ${hiddenCount()} 人の記録を隠しています（${m ? '提出すると見えます' : 'レビュアーを決めて提出すると見えます'}）。`) : null,
      m && !m.submitted ? h('p', null, h('button', { type: 'button', id: 'rv-submit', onclick: () => CE.ask('レビューを提出する', `${m.reviewer.name} のレビューを提出済みにします（日時を記録）。独立レビューなら、提出の後にほかのレビュアーの記録が見えます。提出の後も記録は直せます。`, [['submit', '提出する'], ['cancel', 'やめる']])
        .then((c) => { if (c === 'submit') { m.submitted = now(); changed(true); } }) }, '提出する')) : null,
      st.slotHold ? h('div', { class: 'note warn', id: 'rv-slot-hold' }, h('p', null, `このブラウザに自動保存したレビューの記録（${st.slotHold.savedAt} に保存）が残っています。どれを使うかを選ぶまで、レビューの記録の自動保存を止めています。`),
        h('p', { class: 'buttons' }, h('button', { type: 'button', id: 'rv-slot-ask', onclick: () => askSlot(st.slotHold).then(() => changed(true)) }, '自動保存した記録をどうするか選ぶ'), ' ',
          h('button', { type: 'button', id: 'rv-slot-forget', onclick: () => CE.ask('自動保存した記録を消す', 'このブラウザに自動保存したレビューの記録を消して、いま開いている記録を使います。', [['delete', '消す'], ['cancel', 'やめる']])
            .then((c) => { if (c === 'delete') { try { localStorage.removeItem(slotKey()); } catch (e) { /* ignore */ } st.slotHold = null; CE.saveWarning(null, 'review'); changed(true); } }) }, '自動保存した記録を消す'))) : null,
      h('h2', null, 'レビューの記録を読み込む・書き出す'),
      h('p', { class: 'muted small' }, '記録のファイル：review.yaml（設計書と同じディレクトリに置く）'),
      h('p', { id: 'rv-file-state', 'data-unsaved': unsaved() ? '1' : '0' }, unsaved() ? '書き出していない記録があります。' : '書き出していない記録はありません。', ` レビュアー ${st.file.reviews.length} 人。`),
      h('p', { class: 'buttons' }, h('button', { type: 'button', id: 'rv-import-btn', onclick: () => imp.click() }, 'review.yaml を読み込む（複数を選ぶと合わせる）'), imp, ' ',
        h('button', { type: 'button', class: 'primary', id: 'rv-export', onclick: () => exportAll() }, 'review.yaml を書き出す（全員の記録）'), ' ',
        m ? h('button', { type: 'button', id: 'rv-export-mine', onclick: () => exportReview(true) }, '自分の記録だけ書き出す') : null),
      h('p', { class: 'muted' }, '「zip で書き出す」にも review.yaml が入ります。書き出していない記録があるときに、別の設計書を開く・閉じる・ページを離れると、設計書のファイルと同じように確かめます。自動保存を有効にしていれば、記録もこのブラウザに保存します。'),
      h('h2', null, 'レビュアーごとの記録'),
      vis.length ? h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'reviewers' }, h('thead', null, h('tr', null, ['レビュアー（自己申告）', '種類', '回答', '承認', '修正を求める', '保留', '再確認が要る', '指摘', '提出'].map((x) => h('th', { scope: 'col' }, x)))),
        h('tbody', null, vis.map((rv) => {
          const c = { approve: 0, request_changes: 0, hold: 0 }; let sN = 0;
          Object.keys(rv.rows).forEach((a) => { c[rv.rows[a].decision]++; if (rowState(rv.rows[a], a, set) !== 'current') sN++; });
          return h('tr', { 'data-reviewer': rv.reviewer.name }, h('th', { scope: 'row' }, rv.reviewer.name), h('td', null, rv.reviewer.kind === 'llm' ? 'LLM' + (rv.reviewer.model ? `（${rv.reviewer.model}）` : '') : '人'),
            h('td', { class: 'num' }, `${Object.keys(rv.answers).length} / ${R.questions.length}`), h('td', { class: 'num' }, c.approve), h('td', { class: 'num' }, c.request_changes), h('td', { class: 'num' }, c.hold),
            h('td', { class: 'num' }, sN), h('td', { class: 'num' }, rv.findings.length), h('td', null, rv.submitted || '未提出'));
        })))) : h('p', { class: 'muted' }, '表示できる記録はありません。'),
      h('h2', null, '見直しが要る記録'),
      stale.length || lost.length ? h('ul', { id: 'rv-attention' }, stale.map(([rv, a]) => h('li', { 'data-stale': a }, stateBadge(rv.rows[a], a, rv, set), ' ', rowLink(a))),
        lost.map(([rv, a]) => h('li', { 'data-missing': a }, stateBadge(rv.rows[a], a, rv, set), ' ', code(a), ` ― 記録にある行が、今の台帳に無い（行が消えたか、ID が変わった）。記録は消さずに残しています。`))) : h('p', { class: 'muted', id: 'rv-attention' }, 'ありません。')];
  }
  function rowLink(anchor) {
    const i = anchor.indexOf(':'); const kind = anchor.slice(0, i); const id = anchor.slice(i + 1);
    if (KIND_VIEW[kind]) return h('a', { href: P.route(KIND_VIEW[kind], id) }, anchor);
    if (kind === 'catalog_answers') return h('a', { href: P.route('catalog') }, anchor);
    if (kind === 'issuance_profile') return h('a', { href: P.route('profile') }, anchor);
    return code(anchor);
  }

  // ---- the checklist
  function answerOf(rv, qid) { return rv && rv.answers[qid] ? rv.answers[qid].answer : ''; }
  // The traits of the open design that the conditions of templates/review/triage.yaml name (#56): {condition: 'on' |
  // 'off' | 'unknown'}. The same reading as read_traits() of tools/review_triage.py (tools/tests/test_claims_editor_ux.py
  // compares the two): on when the registry shows it OR the author declared it (catalog_answers); unknown (shown, with
  // a note) when the file it is read from is missing, so that a design does not get a shorter list silently.
  function readTraits() {
    const reg = H.registry() || {};
    const adopted = (rows) => (Array.isArray(rows) ? rows : []).filter((r) => isObj(r) && r.decision !== '却下');
    const claims = adopted(reg.claims && reg.claims.claims); const types = adopted(reg.token_types && reg.token_types.token_types);
    const noHops = !isObj(reg.hops);
    const hops = (isObj(reg.hops) && Array.isArray(reg.hops.hops) ? reg.hops.hops : []).filter(isObj);
    const cat = isObj(reg.catalog_answers) ? reg.catalog_answers : {};
    const lite = isObj(cat.lite_criteria) ? cat.lite_criteria : {}; const asked = isObj(cat.questions) ? cat.questions : {};
    const declared = (sec, key, field) => (isObj(sec[key]) && typeof sec[key][field] === 'boolean' ? sec[key][field] : null);
    const names = new Set(claims.map((c) => String(c.name))); const kinds = new Set(hops.map((x) => x.kind));
    const has = (v) => Array.isArray(v) ? v.length > 0 : isObj(v) ? Object.keys(v).length > 0 : !!v;
    const host = (u) => { const m = /^[a-z][a-z0-9+.-]*:\/\/([^/?#]*)/i.exec(String(u)); return m ? m[1] : ''; };
    const t = { always: 'on' };
    const put = (c, on, unknown) => { t[c] = on ? 'on' : unknown ? 'unknown' : 'off'; };
    put('org_claims', claims.some((c) => has(c.namespace) || (!has(c.registered_ref) && (c.usage === 'authz' || c.usage === 'identifier'))));
    put('pii', claims.some((c) => c.pii_category && c.pii_category !== '該当なし'));
    const hosts = new Set(); types.forEach((x) => (Array.isArray(x.issuers) ? x.issuers : []).forEach((i) => { if (isObj(i) && host(i.iss)) hosts.add(host(i.iss)); }));
    put('multi_idp', hosts.size > 1 || claims.some((c) => has(c.upstream_issuer)));
    put('exchange', kinds.has('exchange') || kinds.has('reissue') || declared(lite, 'delegation_or_exchange', 'answer') === true, noHops);
    put('delegation', names.has('act') || names.has('may_act') || types.some((x) => x.max_delegation_depth !== undefined && x.max_delegation_depth !== null) ||
      declared(asked, 'q-actor', 'needed') === true, declared(asked, 'q-actor', 'needed') === null || declared(lite, 'delegation_or_exchange', 'answer') === true);
    put('approval', names.has('authorization_details') || hops.some((x) => has(x.authorization_details)), noHops);
    // the author's answer decides multitenant; tenant_binding is read only when there is no answer
    const mt = declared(lite, 'multitenant', 'answer');
    put('multitenant', mt !== null ? mt : types.some((x) => has(x.tenant_binding)));
    put('data_layer', kinds.has('db_connection'), noHops);
    put('auth_context', names.has('acr') || names.has('amr') || names.has('auth_time'));
    put('sender_constrained', types.some((x) => x.sender_constraint === 'dpop' || x.sender_constraint === 'mtls') || declared(asked, 'q-holder', 'needed') === true);
    put('sender_declined', types.some((x) => (x.kind === 'access_token' || x.kind === 'internal_token') && (x.sender_constraint === undefined || x.sender_constraint === null || x.sender_constraint === 'none')));
    put('long_running', types.some((x) => has(x.long_running)) || kinds.has('broker_connection'), noHops);
    return t;
  }
  function designTraits() { const t = readTraits(); return new Set(Object.keys(t).filter((c) => t[c] !== 'off')); }
  // the short list of #56: class C, a default priority and a condition that holds, or a lint rule of show_on_lint that warned
  function shortList() {
    const C = (R.checklist && R.checklist.short) || null;
    if (!C) return null;
    const states = readTraits(); const traits = designTraits();
    const warned = new Set(CE.diagnostics().filter((d) => d.source === 'claim_lint' && d.severity !== 'info').map((d) => d.rule));
    const why = new Map(); const more = new Set();
    R.questions.forEach((x) => {
      if (x.triage !== 'C') return;
      const hit = (x.show_when || []).some((c) => traits.has(c));
      const byCond = C.priorities.includes(x.priority) && hit;
      const byLint = (x.show_on_lint || []).filter((r) => warned.has(r));
      if (byCond || byLint.length) why.set(x.id, byLint.length && !byCond ? `lint の ${byLint.join('・')} の warn` : '');
      else if ((C.optional_priorities || []).includes(x.priority) && hit) more.add(x.id);   // "if time remains"
    });
    // the open prompts that fit the design first: a condition other than always, then prefer_when, then the order of the data
    const rank = (p) => (p.show_when.some((c) => c !== 'always' && traits.has(c)) ? 0 : (p.prefer_when || []).some((c) => states[c] === 'on') ? 1 : 2);   // prefer_when: traits that hold, not the ones that cannot be read
    const all = (R.checklist.open_prompts || []).filter((p) => p.show_when.some((c) => traits.has(c))).map((p, i) => [rank(p), i, p]).sort((a, b) => a[0] - b[0] || a[1] - b[1]).map((x) => x[2]);
    const max = C.max_prompts || all.length;
    return { traits, states, why, more, prompts: all.slice(0, max), morePrompts: all.slice(max) };
  }
  function viewChecklist(query) {
    const q = new URLSearchParams(query || '');
    const m = mine();
    const stageSel = h('select', { id: 'rv-f-stage' }, h('option', { value: '' }, 'すべての段'), R.stages.map((s) => h('option', { value: s.id }, s.name)));
    const indexed = new Set(R.roles.flatMap((r) => r.questions));
    const unindexed = R.questions.filter((x) => !indexed.has(x.id)).length;
    const roleSel = h('select', { id: 'rv-f-role' }, h('option', { value: '' }, 'すべての役割'), R.roles.map((r) => h('option', { value: r.id }, r.name + `（索引の ${r.questions.length} 問）`)),
      h('option', { value: 'none' }, `役割の索引が未整備の問い（${unindexed} 問）— どの役割にも関わりうる`));
    const roleNote = h('p', { class: 'note warn', id: 'rv-role-note', role: 'status', hidden: true });
    const ansSel = h('select', { id: 'rv-f-ans' }, h('option', { value: '' }, 'すべて'), h('option', { value: 'open' }, '未回答'), Object.keys(ANS).map((k) => h('option', { value: k }, ANS[k][2])));
    const text = h('input', { type: 'search', id: 'rv-f-q', placeholder: '問い ID・問いの文・見る欄で探す' });
    // the triage of each question (data/review.js): the default filter comes from the data, so that a shorter list shown
    // first is a change of perspectives.md, not of this screen
    const tri = Array.from(new Set(R.questions.map((x) => x.triage || 'all')));
    const tl = (R.checklist && R.checklist.triage_labels) || {};
    const short = shortList();
    const triSel = h('select', { id: 'rv-f-triage' }, short ? h('option', { value: 'short' }, tl.short || '短い一覧') : null,
      short && short.more.size + short.morePrompts.length ? h('option', { value: 'short+' }, tl['short+'] || '短い一覧と、時間があれば') : null, h('option', { value: '' }, `すべての問い（${R.questions.length} 問）`),
      tri.filter((t) => t !== 'all').sort().map((t) => h('option', { value: t }, (tl[t] || t) + `：${R.questions.filter((x) => (x.triage || 'all') === t).length} 問`)));
    const inTriage = (x) => !triSel.value || (triSel.value === 'short' ? !!short && short.why.has(x.id) : triSel.value === 'short+' ? !!short && (short.why.has(x.id) || short.more.has(x.id)) : (x.triage || 'all') === triSel.value);
    const shortNote = h('div', { class: 'note', id: 'rv-short-note', hidden: true });
    const promptBox = h('section', { class: 'rv-stage', id: 'rv-open-prompts', hidden: true });
    const def = (R.checklist && R.checklist.default) || {};
    const anyQuery = Array.from(q.keys()).length > 0;
    triSel.value = q.get('triage') || (!anyQuery && Array.isArray(def.triage) && def.triage.length === 1 ? def.triage[0] : '');
    stageSel.value = q.get('stage') || ''; roleSel.value = q.get('role') || ''; ansSel.value = q.get('ans') || ''; text.value = q.get('q') || '';
    const count = h('p', { class: 'count', id: 'rv-count', 'aria-live': 'polite' });
    const list = h('div', { id: 'rv-questions' });
    const items = [];
    R.stages.forEach((s) => {
      const qs = R.questions.filter((x) => x.stage === s.id);
      const sec = h('section', { class: 'rv-stage', 'data-stage': s.id }, h('h2', null, s.title), h('p', { class: 'muted small' }, h('strong', null, '誰が確かめるか：'), H.inlineRepo(s.who)));
      qs.forEach((x) => { const el = questionItem(x, m); items.push([x, el]); sec.append(el); });
      list.append(sec);
    });
    function apply() {
      const params = {};
      if (triSel.value) params.triage = triSel.value; else if (short) params.triage = 'all';   // keeps "every question" across a re-render (the default is the short list)
      if (stageSel.value) params.stage = stageSel.value;
      if (roleSel.value) params.role = roleSel.value;
      if (ansSel.value) params.ans = ansSel.value;
      if (text.value.trim()) params.q = text.value.trim();
      const t = text.value.trim().toLowerCase();
      let n = 0;
      items.forEach(([x, el]) => {
        const a = answerOf(mine(), x.id);
        const ok = inTriage(x) && (!stageSel.value || x.stage === stageSel.value) &&
          (!roleSel.value || (roleSel.value === 'none' ? !x.roles.length : x.roles.includes(roleSel.value))) &&
          (!ansSel.value || (ansSel.value === 'open' ? !a : a === ansSel.value)) &&
          (!t || (x.id + ' ' + x.text + ' ' + x.see).toLowerCase().includes(t));
        el.hidden = !ok;
        if (ok) n++;
      });
      list.querySelectorAll('.rv-stage').forEach((sec) => { sec.hidden = !sec.querySelector('.rv-q:not([hidden])'); });
      const role = ROLE.get(roleSel.value);
      roleNote.hidden = !role;
      if (role) roleNote.textContent = `「${role.name}」で絞っています：観点書の 7. の索引で「${role.name}」に載っている問い ${role.questions.length} 問だけです。役割の索引が未整備の問い ${unindexed} 問にも、この役割に関わる問いがありえます（「役割の索引が未整備の問い」で絞ると見られます。全問に役割を付けるのは観点書の側の作業）。`;
      count.textContent = `${n} / ${R.questions.length} 問を表示（自分の回答 ${m ? Object.keys(m.answers).length : 0} 問）`;
      const isShort = (triSel.value === 'short' || triSel.value === 'short+') && !!short;
      shortNote.hidden = !isShort; promptBox.hidden = !isShort;
      if (isShort && !shortNote.dataset.done) {
        shortNote.dataset.done = '1';
        const by = (c) => R.questions.filter((x) => x.triage === c).length;
        const word = { on: '当たる', off: '当たらない', unknown: '読めない（問いは出す）' };
        const cond = (R.checklist.conditions || []).filter((c) => c.id !== 'always').map((c) => `${c.label}：${word[short.states[c.id]]}`);
        const b = R.checklist.short.budget || {};
        shortNote.append(h('p', null, h('strong', null, `全 ${R.questions.length} 問のうち、あなたが答える ${short.why.size} 問と、開いた問い ${short.prompts.length} 個を出しています。`),
          b.questions ? ` 問いに答える時間の目安は ${b.minutes[0]}〜${b.minutes[1]} 分です（見積もり。人では測っていません）。` : '',
          short.more.size + short.morePrompts.length ? ` 時間があれば：優先 2 の問い ${short.more.size} 問と、開いた問い ${short.morePrompts.length} 個（「表示する問い」で開けます）。` : '',
          b.row_sample ? ` 行ごとの問いは、全部の行でなく、認可・識別子に使う行から ${b.row_sample} 行を選んで答えます。` : ''),
          h('p', { class: 'small', id: 'rv-short-traits' }, 'この設計から読んだ性質（設計書が示すか、書き手が宣言していれば「当たる」）― ', cond.join('／'), '。図と要求に照らして確かめ、合わないときは、それ自体を指摘にして、「表示する問い」で全部の問いを開いてください。'),
          h('p', { class: 'small', id: 'rv-short-rest' }, `出していない問い：lint が確かめる ${by('A')} 問、書き手が提出前に確かめる ${by('B')} 問、専門家に回す ${by('D')} 問、人の判断が要るがこの設計の性質に当たらない・優先 3 の ${by('C') - short.why.size - short.more.size} 問。「表示する問い」で開けます。分け方は `,
            h('a', { href: gh(R.checklist.short.source) }, 'triage.yaml'), '、紙で読むなら ', h('a', { href: gh(R.checklist.short.doc) }, 'short_list.md'), '。'));
        promptBox.append(h('h2', null, '開いた問い（要求と運用から辿る）'),
          h('p', { class: 'muted small' }, 'Yes／No では答えません。要求の文と運用の場面から自分で辿り、気づいたことを指摘にします（出どころは「テンプレート外」）。1 つにつき 2〜3 分が目安です。'),
          ...short.prompts.concat(short.morePrompts).map((p, i) => h('article', { class: 'rv-prompt', 'data-prompt': p.id, 'data-more': i >= short.prompts.length ? '1' : null, hidden: i >= short.prompts.length ? true : null },
            h('h3', null, code(p.id), ' ', i >= short.prompts.length ? '（時間があれば）' : '', p.ask), p.hint ? h('p', { class: 'muted small rv-hint' }, '手がかり：', p.hint) : null,
            h('button', { type: 'button', disabled: m ? null : true, onclick: () => newFinding({ questions: [], location: p.id, origin: 'テンプレート外', content: '' }) }, '気づきを指摘にする'))));
      }
      promptBox.querySelectorAll('[data-more]').forEach((el) => { el.hidden = triSel.value !== 'short+'; });
      const hash = P.route('review', 'checklist', params);
      if (location.hash !== hash) history.replaceState(null, '', hash);
    }
    const form = h('form', { class: 'filters', role: 'search', onsubmit: (e) => e.preventDefault(), oninput: apply, onchange: apply },
      tri.length > 1 ? h('label', null, '表示する問い', triSel) : null, h('label', null, '段（スライド 148 の 6 段）', stageSel), h('label', null, '役割（観点書の 7. の索引）', roleSel), h('label', null, '自分の回答', ansSel), h('label', { class: 'wide' }, '検索', text));
    setTimeout(apply, 0);
    list.append(promptBox);
    return [h('h1', { tabindex: '-1' }, '観点のチェックリスト'),
      h('p', { class: 'lead' }, '問いはどれも Yes が「満たす」の向きです。見る欄が空で判定できないときは No にして、指摘にします（templates/review/procedure.md の段 3）。「見る欄」を押すと、その欄（台帳の列・設計書の節・25 問の回答）に移動します。'),
      m ? null : h('p', { class: 'note warn' }, '回答を記録するには、', h('a', { href: P.route('review') }, 'レビューの概要'), 'でレビュアーの名前（自己申告）を決めてください。'),
      h('p', { class: 'muted small' }, `役割の索引（perspectives.md の 7.）に載っている問いは ${indexed.size} 問です。残りの ${unindexed} 問は、役割の索引が未整備の問いで、どの役割にも関わりえます（「役割の索引が未整備の問い」で絞り込めます）。`),
      form, shortNote, roleNote, count, list];
  }
  function questionItem(x, m) {
    const a = answerOf(m, x.id);
    const memo = h('textarea', { id: 'rv-memo-' + x.id, rows: '1', class: 'rv-memo', 'aria-label': `${x.id} のメモ（理由 1 行）`, disabled: m ? null : true }, m && m.answers[x.id] && m.answers[x.id].memo ? m.answers[x.id].memo : '');
    const setAns = (v) => {
      const me = mine();
      if (!me) return;
      if (!v) delete me.answers[x.id];
      else { const e = flagEdit({ answer: v, at: now() }); const mm = memo.value.trim(); if (mm) e.memo = mm; me.answers[x.id] = e; }
      el.dataset.answer = v;
      el.querySelector('.rv-findbtn').hidden = v !== 'no';
      changed(false);
    };
    let timer = null;
    memo.addEventListener('input', () => {
      clearTimeout(timer);
      timer = setTimeout(() => { const me = mine(); if (me && me.answers[x.id]) { const mm = memo.value.trim(); if (mm) me.answers[x.id].memo = mm; else delete me.answers[x.id].memo; flagEdit(me.answers[x.id]); changed(false); } }, 250);
    });
    const name = 'rv-a-' + x.id;
    const others = visible().filter((rv) => rv !== m && rv.answers[x.id]);
    const el = h('article', { class: 'rv-q', id: 'q-' + x.id, 'data-q': x.id, 'data-answer': a },
      x.ask ? h('h3', null, code(x.id), ' ', h('span', { class: 'chip' }, '優先 ' + x.priority), ' ', x.ask) : h('h3', null, code(x.id), ' ', H.inlineRepo(x.text)),
      x.hint ? h('p', { class: 'muted small rv-hint' }, '手がかり：', x.hint) : null,
      x.ask ? h('p', { class: 'muted small rv-orig' }, '観点書の問い：', H.inlineRepo(x.text)) : null,
      x.triage_note ? h('p', { class: 'muted small rv-triage', 'data-triage': x.triage }, '区分：', H.inlineRepo(x.triage_note)) : null,
      x.roles.length ? h('p', { class: 'codes small' }, x.roles.map((r) => h('span', { class: 'chip' }, ROLE.get(r).name))) : null,
      h('p', { class: 'rv-see' }, h('span', { class: 'muted' }, '見る欄：'), x.see_refs.map((r, i) => [i ? '、' : '', seeLink(r)])),
      h('details', null, h('summary', null, 'No なら・つながり・根拠'), h('dl', { class: 'obj' }, h('dt', null, 'No なら'), h('dd', null, H.inlineRepo(x.no)), h('dt', null, 'つながり'), h('dd', null, H.inlineRepo(x.links)),
        h('dt', null, '根拠'), h('dd', null, H.inlineRepo(x.evidence)), h('dt', null, '原文'), h('dd', null, h('a', { href: x.url }, 'perspectives.md の ' + x.id)))),
      h('fieldset', { class: 'rv-ans', disabled: m ? null : true }, h('legend', null, m ? `${x.id} の回答（${m.reviewer.name}）` : `${x.id} の回答`),
        [['', '未回答']].concat(Object.keys(ANS).map((k) => [k, ANS[k][2]])).map(([v, label]) => h('label', null,
          h('input', { type: 'radio', name, value: v, checked: a === v ? true : null, 'data-answer-for': x.id, onchange: () => setAns(v) }), ' ', v ? ANS[v][1] + ' ' : '', label)),
        h('label', { class: 'rv-memo-l', for: 'rv-memo-' + x.id }, 'メモ'), memo,
        h('button', { type: 'button', class: 'rv-findbtn', hidden: a !== 'no' ? true : null, onclick: () => newFinding({ questions: [x.id], location: x.id + '（' + x.see_refs.map((r) => r.ref).join('・') + '）', origin: '観点', content: memo.value.trim() }) }, '指摘にする')),
      others.length ? h('ul', { class: 'rv-others small' }, others.map((rv) => h('li', null, badge(ANS[rv.answers[x.id].answer]), ' ', rv.reviewer.name, rv.answers[x.id].memo ? '：' + rv.answers[x.id].memo : ''))) : null);
    return el;
  }

  // ---- 見る欄: one column of the registry, every row
  function viewColumn(parts) {
    const coll = parts[0]; const col = parts[1];
    const cols = H.columns(coll); const prof = H.columns('issuance_profile');
    const c = cols.find((x) => x.key === col) || (coll === 'token_types' ? prof.find((x) => x.key === col) : null);
    const isProfile = !cols.find((x) => x.key === col) && coll === 'token_types' && !!c;
    const reg = H.registry();
    const key = { claims: 'claims', token_types: 'token_types', hops: 'hops' }[coll];
    const rows = reg[coll] && Array.isArray(reg[coll][key]) ? reg[coll][key].filter(isObj) : [];
    const qs = R.questions.filter((x) => x.see_refs.some((r) => r.kind === 'registry' && r.path === coll && r.anchor === col));
    const out = [h('p', null, h('a', { href: P.route('review', 'checklist') }, '← 観点のチェックリスト')),
      h('h1', { tabindex: '-1', 'data-column': coll + '.' + col }, `欄：${c ? c.label : col}`),
      h('p', { class: 'muted small' }, '項目の名前：', code(`registry:${coll}#${col}`)),
      c && c.meaning ? h('p', { class: 'lead' }, H.inline(c.meaning)) : null,
      qs.length ? h('details', { open: true }, h('summary', null, `この欄を見る問い ${qs.length} 件`), h('ul', null, qs.map((x) => h('li', null, h('a', { href: P.route('review', 'checklist', { q: x.id }) }, x.id), ' ', H.inlineRepo(x.text))))) : null];
    if (isProfile) {
      const p = reg.token_types && reg.token_types.issuance_profile;
      out.push(h('p', null, '発行方式の選択（token_types.yaml の issuance_profile）の項目です：'), h('div', { class: 'cols' }, h('div', { class: 'col' }, h('div', { class: 'ch' }, code(col)), h('div', { class: 'cv' }, p && own(p, col) ? H.value(p[col]) : '（未記入）'))));
      return out;
    }
    const idk = coll === 'catalog_answers' ? 'event' : 'id';
    out.push(h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'column' }, h('caption', null, `${KIND_LABEL[coll] || coll}の ${col}（${rows.length} 行）`),
      h('thead', null, h('tr', null, ['行', col, '検査', 'レビュー'].map((x) => h('th', { scope: 'col' }, x)))),
      h('tbody', null, rows.map((r) => {
        const anchor = coll + ':' + r[idk];
        return h('tr', { 'data-anchor': anchor }, h('th', { scope: 'row' }, rowLink(anchor), ' ', H.revealLink(coll, r[idk])),
          h('td', null, own(r, col) ? H.columnValue(coll, col, r[col]) : h('span', { class: 'muted' }, '（未記入）')),
          h('td', null, H.lintBadges(String(r[idk]))), h('td', null, rowBadges(anchor)));
      })))));
    return out;
  }
  function rowBadges(anchor) {
    const set = anchorSet(); const multi = st.file.reviews.length > 1;
    return visible().filter((rv) => own(rv.rows, anchor)).map((rv) => stateBadge(rv.rows[anchor], anchor, rv, set));
  }

  // ---- per-row decisions
  function baseDiff() {
    if (!st.base) return null;
    const cur = {}; CE.anchors().forEach((a) => { const x = CE.rowHash(a.anchor); if (x) cur[a.anchor] = x; });
    const b = st.base.hashes;
    const out = { added: [], removed: [], changed: [], same: [], unknown: [] };
    Object.keys(cur).forEach((a) => {
      if (!own(b, a)) (st.base.kind === 'review' ? out.unknown : out.added).push(a);
      else if (b[a] !== cur[a]) out.changed.push(a); else out.same.push(a);
    });
    Object.keys(b).forEach((a) => { if (!own(cur, a)) out.removed.push(a); });
    Object.keys(out).forEach((k) => out[k].sort());
    return out;
  }
  function viewRows(query) {
    const q = new URLSearchParams(query || '');
    const m = mine();
    const set = anchorSet();
    const diff = baseDiff();
    const changedSet = diff ? new Set(diff.added.concat(diff.changed, diff.unknown)) : null;
    const kindSel = h('select', { id: 'rv-r-kind' }, h('option', { value: '' }, 'すべて'), Object.keys(KIND_LABEL).map((k) => h('option', { value: k }, KIND_LABEL[k])));
    const stateSel = h('select', { id: 'rv-r-state' }, h('option', { value: '' }, 'すべて'), h('option', { value: 'open' }, '自分が未判定'),
      Object.keys(DEC).map((k) => h('option', { value: k }, DEC[k][2])), h('option', { value: 'stale' }, '再確認が要る'));
    const onlyChanged = h('input', { type: 'checkbox', id: 'rv-r-changed', disabled: diff ? null : true });
    kindSel.value = q.get('kind') || ''; stateSel.value = q.get('state') || ''; onlyChanged.checked = !!diff && q.get('changed') === '1';
    const tbody = h('tbody');
    const count = h('p', { class: 'count', id: 'rv-r-count', 'aria-live': 'polite' });
    const anchors = CE.anchors();
    function apply() {
      tbody.textContent = '';
      let n = 0;
      anchors.forEach((a) => {
        const rec = m && m.rows[a.anchor];
        const s = rec ? rowState(rec, a.anchor, set) : null;
        if (kindSel.value && a.kind !== kindSel.value) return;
        if (stateSel.value === 'open' && rec) return;
        if (stateSel.value === 'stale' && s !== 'stale') return;
        if (DEC[stateSel.value] && !(rec && rec.decision === stateSel.value && s === 'current')) return;
        if (onlyChanged.checked && changedSet && !changedSet.has(a.anchor)) return;
        n++;
        tbody.append(rowLine(a, m, set, changedSet));
      });
      count.textContent = `${n} / ${anchors.length} 行`;
      const params = {};
      if (kindSel.value) params.kind = kindSel.value;
      if (stateSel.value) params.state = stateSel.value;
      if (onlyChanged.checked) params.changed = '1';
      const hash = P.route('review', 'rows', params);
      if (location.hash !== hash) history.replaceState(null, '', hash);
    }
    setTimeout(apply, 0);
    const lost = [];
    visible().forEach((rv) => Object.keys(rv.rows).forEach((a) => { if (!set.has(a) || CE.rowHash(a) === null) lost.push([rv, a]); }));
    return [h('h1', { tabindex: '-1' }, '行ごとの判定'),
      h('p', { class: 'lead' }, '台帳の行・トークン種別・ホップ・カタログへの回答・発行方式の項目ごとに、承認／修正を求める／保留 を記録します。判定は、その行の内容のハッシュ（RFC 8785 JCS の SHA-256。tools/row_hash.py と同じ）に結びつきます。行を変えると「再確認が要る」になります。'),
      selfDeclared(),
      m ? null : h('p', { class: 'note warn' }, '判定を記録するには、', h('a', { href: P.route('review') }, 'レビューの概要'), 'でレビュアーの名前を決めてください。'),
      h('form', { class: 'filters', onsubmit: (e) => e.preventDefault(), onchange: apply },
        h('label', null, '種類', kindSel), h('label', null, '自分の判定', stateSel),
        h('label', null, h('span', null, onlyChanged, ' 前の版から変わった行だけ'), diff ? h('span', null, `（変わった ${diff.changed.length}・足された ${diff.added.length}${diff.unknown.length ? '・前の記録に無い ' + diff.unknown.length : ''}）`) : h('a', { href: P.route('review', 'analysis') + '' }, '前の版を分析の画面で読み込む'))),
      count,
      h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'review-rows' }, h('thead', null, h('tr', null, ['行', '判定（自分）', 'コメント', '記録', ''].map((x) => h('th', { scope: 'col' }, x)))), tbody)),
      lost.length ? [h('h2', null, '台帳に無い行の記録'), h('p', { class: 'muted' }, '記録にあるが、今の台帳に無い（または ID が重なってハッシュの無い）行です。消さずに残しています。'),
        h('ul', { id: 'rv-lost' }, lost.map(([rv, a]) => h('li', { 'data-missing': a }, code(a), '：', DEC[rv.rows[a].decision][2], `（${rv.reviewer.name}、${rv.rows[a].at}）`, rv.rows[a].comment ? '：' + rv.rows[a].comment : '')))] : null];
  }
  function rowLine(a, m, set, changedSet) {
    const rec = m && m.rows[a.anchor];
    const sid = a.anchor.replace(/[^A-Za-z0-9_-]/g, '_');
    const sel = h('select', { id: 'rv-d-' + sid, 'data-decide': a.anchor, 'aria-label': `${a.anchor} の判定`, disabled: m ? null : true },
      h('option', { value: '' }, '未判定'), Object.keys(DEC).map((k) => h('option', { value: k, selected: rec && rec.decision === k ? true : null }, DEC[k][2])));
    const cm = h('input', { type: 'text', id: 'rv-c-' + sid, 'aria-label': `${a.anchor} のコメント`, value: rec && rec.comment ? rec.comment : '', disabled: m ? null : true });
    sel.addEventListener('change', () => { st.focus = sel.id; record(a.anchor, sel.value, cm.value.trim()); });
    cm.addEventListener('change', () => { if (sel.value) { st.focus = cm.id; record(a.anchor, sel.value, cm.value.trim()); } });
    const s = rec ? rowState(rec, a.anchor, set) : null;
    return h('tr', { 'data-anchor': a.anchor, 'data-row-state': s || 'open' },
      h('th', { scope: 'row' }, rowLink(a.anchor), changedSet && changedSet.has(a.anchor) ? [' ', H.badge('info', 'Δ', '変わった')] : null),
      h('td', null, sel), h('td', null, cm), h('td', null, rowBadges(a.anchor)),
      h('td', null, s === 'stale' ? h('button', { type: 'button', 'data-rerecord': a.anchor, onclick: () => { st.focus = sel.id; record(a.anchor, rec.decision, rec.comment); } }, '確かめたので今の内容で記録し直す') : null));
  }

  // ---- findings, escalations, feedback
  function nextId(rv) {
    for (let i = 1; ; i++) { const id = 'F' + String(i).padStart(2, '0'); if (!rv.findings.some((f) => f.id === id)) return id; }
  }
  function newFinding(pre) {
    const m = mine();
    if (!m) { location.hash = P.route('review'); return; }
    st.editFinding = Object.assign({ id: nextId(m), location: '', content: '', severity: 'Major', origin: '観点', kind: '候補の漏れ', verdict: '保留' }, pre || {}, { _new: true });
    location.hash = P.route('review', 'findings');
    setTimeout(() => { const el = $('#rv-f-content'); if (el) el.focus(); }, 50);
  }
  function findingForm(m) {
    const f = st.editFinding;
    if (!f) return h('p', null, h('button', { type: 'button', class: 'primary', id: 'rv-f-add', disabled: m ? null : true, onclick: () => { newFinding(); P.render(); } }, '指摘を足す'));
    const sel = (id, list, v, label) => h('label', null, label, h('select', { id }, list.map((x) => h('option', { value: x, selected: x === v ? true : null }, x))));
    const txt = (id, v, label, area) => h('label', { class: area ? 'wide' : null }, label, area ? h('textarea', { id, rows: '3' }, v || '') : h('input', { type: 'text', id, value: v || '' }));
    const resp = f.response || {};
    const confusedBox = h('div', { class: 'wide', id: 'rv-f-confused-box', hidden: f.kind !== MISMATCH ? true : null }, txt('rv-f-confused', f.confused_question, '取り違えた問い（判断の木の節の ID、questions.yaml の ID。例：`q-peer` を `req_wl` で答えた）'));
    const msg = h('p', { class: 'err', id: 'rv-f-msg', role: 'alert' });
    const form = h('form', { class: 'filters rv-fform', id: 'rv-finding-form', onsubmit: (e) => {
      e.preventDefault();
      const v = (id) => ($('#' + id).value || '').trim();
      const x = { id: v('rv-f-id'), location: v('rv-f-location'), content: v('rv-f-content'), severity: v('rv-f-severity'), origin: v('rv-f-origin'), kind: v('rv-f-kind'), verdict: v('rv-f-verdict') };
      const anchors = v('rv-f-anchors').split(/[\s,、]+/).filter(Boolean);
      const qs = v('rv-f-questions').split(/[\s,、]+/).filter(Boolean);
      const problems = [];
      if (!/^[A-Za-z][A-Za-z0-9_-]*$/.test(x.id)) problems.push('ID は英字で始める（F01 など）');
      if (m.findings.some((g) => g.id === x.id && g !== f._orig)) problems.push(`ID ${x.id} はもう使っている`);
      if (!x.location) problems.push('場所が空');
      if (!x.content) problems.push('内容が空');
      anchors.forEach((a) => { if (!/^(claims|token_types|hops|catalog_answers|issuance_profile):.+$/.test(a)) problems.push(`${a} は行の名前（claims:C-… など）でない`); });
      qs.forEach((qq) => { if (!QBY.has(qq)) problems.push(`${qq} は観点書の問いでない`); });
      if (x.kind === MISMATCH) { x.confused_question = v('rv-f-confused'); if (!x.confused_question) problems.push('種別が目的と仕組みの不一致なら、取り違えた問いを書く'); }
      if (problems.length) { msg.textContent = problems.join('。'); return; }
      if (anchors.length) x.anchors = anchors;
      if (qs.length) x.questions = qs;
      if (v('rv-f-reason')) x.verdict_reason = v('rv-f-reason');
      const r = {};
      if (v('rv-f-owner')) r.owner = v('rv-f-owner');
      if (v('rv-f-due')) r.due = v('rv-f-due');
      r.state = v('rv-f-state') || '未着手';
      if (v('rv-f-ref')) r.ref = v('rv-f-ref');
      x.response = r;
      x.at = now();
      flagEdit(x);
      if (f._orig) m.findings[m.findings.indexOf(f._orig)] = x; else m.findings.push(x);
      st.editFinding = null;
      st.focus = 'rv-f-add';
      changed(true);
    } },
    h('h2', { class: 'wide' }, f._orig ? `指摘 ${f._orig.id} を直す` : '指摘を足す'),
    txt('rv-f-id', f.id, 'ID'), txt('rv-f-location', f.location, '場所（項目 ID・行の ID と列・25 問の番号・問い ID）'),
    txt('rv-f-content', f.content, '内容', true),
    sel('rv-f-severity', R.report.severities, f.severity, '重大度'), sel('rv-f-origin', R.report.origins, f.origin, '出どころ'),
    h('label', null, '種別', h('select', { id: 'rv-f-kind', onchange: (e) => { confusedBox.hidden = e.target.value !== MISMATCH; } }, R.report.kinds.map((x) => h('option', { value: x, selected: x === f.kind ? true : null }, x)))),
    confusedBox,
    sel('rv-f-verdict', R.report.verdicts, f.verdict, '判定'), txt('rv-f-reason', f.verdict_reason, '判定の理由（却下・保留のとき）'),
    txt('rv-f-anchors', (f.anchors || []).join(' '), '行（claims:C-… を空白で区切る。行の画面に指摘の印が付く）'), txt('rv-f-questions', (f.questions || []).join(' '), '見つけた問い（問い ID を空白で区切る）'),
    txt('rv-f-owner', resp.owner, '対応の担当'), txt('rv-f-due', resp.due, '期限'), sel('rv-f-state', R.report.states, resp.state || '未着手', '対応の状態'), txt('rv-f-ref', resp.ref, '対応の PR・コミット'),
    h('div', { class: 'wide' }, msg, h('button', { type: 'submit', class: 'primary', id: 'rv-f-save' }, '記録する'), ' ', h('button', { type: 'button', id: 'rv-f-cancel', onclick: () => { st.editFinding = null; P.render(); } }, 'やめる')));
    return form;
  }
  function viewFindings() {
    const m = mine();
    const vis = visible();
    const multi = st.file.reviews.length > 1;
    const all = [];
    vis.forEach((rv) => rv.findings.forEach((f) => all.push([rv, f])));
    const out = [h('h1', { tabindex: '-1' }, '指摘'),
      h('p', { class: 'lead' }, '指摘は templates/review/report_template.md の欄（ID・場所・内容・重大度・出どころ・種別・判定・対応）で記録します。種別が「目的と仕組みの不一致」なら、取り違えた問いも書きます。'),
      m ? null : h('p', { class: 'note warn' }, '記録するには、', h('a', { href: P.route('review') }, 'レビューの概要'), 'でレビュアーの名前を決めてください。'),
      hiding() && hiddenCount() ? h('p', { class: 'note', 'data-hidden-others': String(hiddenCount()) }, `独立レビュー：提出するまで、ほかのレビュアー ${hiddenCount()} 人の指摘を隠しています。`) : null,
      findingForm(m),
      h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'findings' }, h('thead', null, h('tr', null, (multi ? ['レビュアー'] : []).concat(['ID', '場所', '内容', '重大度', '出どころ', '種別', '取り違えた問い', '判定', '対応', '']).map((x) => h('th', { scope: 'col' }, x)))),
        h('tbody', null, all.length ? all.map(([rv, f]) => h('tr', { 'data-finding': f.id, 'data-finding-by': rv.reviewer.name }, multi ? h('td', null, rv.reviewer.name) : null,
          h('th', { scope: 'row' }, code(f.id)), h('td', null, H.inline(f.location), (f.anchors || []).length ? h('div', { class: 'codes' }, f.anchors.map(rowLink)) : null),
          h('td', null, H.inline(f.content), f.verdict_reason ? h('div', { class: 'muted small' }, '判定の理由：', f.verdict_reason) : null), h('td', null, f.severity), h('td', null, f.origin), h('td', null, f.kind),
          h('td', null, f.kind === MISMATCH ? H.inline(f.confused_question || '') : '—'), h('td', null, f.verdict), h('td', null, (f.response && f.response.state) || '未着手'),
          h('td', null, rv === m ? [h('button', { type: 'button', 'data-edit-finding': f.id, onclick: () => { st.editFinding = Object.assign({}, f, { _orig: f }); P.render(); } }, '直す'), ' ',
            h('button', { type: 'button', 'data-delete-finding': f.id, onclick: () => CE.ask('指摘を消す', `指摘 ${f.id} を消します。`, [['delete', '消す'], ['cancel', 'やめる']]).then((c) => { if (c === 'delete') { m.findings.splice(m.findings.indexOf(f), 1); changed(true); } }) }, '消す')] : null)))
          : h('tr', null, h('td', { colspan: multi ? '12' : '11', class: 'muted' }, '指摘はありません。'))))),
      escalationBlock(m), feedbackBlock(m)];
    return out;
  }
  function escalationBlock(m) {
    if (!m) return null;
    const e = m.escalations || {};
    const applies = e.applies || []; const na = e.not_applicable || [];
    const save = () => { m.escalations = { applies: applies.slice(), not_applicable: na.slice() }; if (!applies.length && !na.length) delete m.escalations; changed(true); };
    return [h('h2', null, '専門家に回した項目'),
      h('p', { class: 'muted' }, '基準の表を上から見て、当てはまる行を回します。当てはまらない基準も、確かめたことを記録します（procedure.md の段 6）。'),
      h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'escalation' }, h('thead', null, h('tr', null, ['基準', '当てはまる条件', '確かめた結果', '行・欄／回した先／結論'].map((x) => h('th', { scope: 'col' }, x)))),
        h('tbody', null, R.escalation.criteria.map((c) => {
          const ap = applies.find((x) => x.criterion === c.id);
          const v = ap ? 'applies' : na.includes(c.id) ? 'na' : '';
          const s = h('select', { 'data-escalation': c.id, 'aria-label': `${c.id} を確かめた結果` }, h('option', { value: '' }, '未確認'), h('option', { value: 'applies', selected: v === 'applies' ? true : null }, '当てはまる（回す）'),
            h('option', { value: 'na', selected: v === 'na' ? true : null }, '当てはまらない'));
          s.addEventListener('change', () => {
            const i = applies.findIndex((x) => x.criterion === c.id); if (i >= 0) applies.splice(i, 1);
            const j = na.indexOf(c.id); if (j >= 0) na.splice(j, 1);
            if (s.value === 'applies') applies.push({ criterion: c.id, location: '（書く）', conclusion: '未了' });
            if (s.value === 'na') na.push(c.id);
            save();
          });
          const fld = (k, label) => h('input', { type: 'text', 'aria-label': `${c.id} の${label}`, placeholder: label, value: ap ? ap[k] || '' : '', 'data-escalation-field': c.id + '.' + k,
            onchange: (ev) => { if (ap) { if (ev.target.value.trim()) ap[k] = ev.target.value.trim(); else if (k !== 'location') delete ap[k]; save(); } } });
          return h('tr', null, h('th', { scope: 'row' }, h('a', { href: gh(R.escalation.file, c.id) }, c.id)), h('td', null, H.inlineRepo(c.when)), h('td', null, s),
            h('td', null, ap ? [fld('location', '行・欄'), ' ', fld('to', '回した先'), ' ', fld('due', '期限'), ' ', fld('conclusion', '結論')] : '—'));
        }))))];
  }
  function feedbackBlock(m) {
    if (!m) return null;
    const list = m.feedback || [];
    const to = h('select', { id: 'rv-fb-to' }, ['カタログ', '観点書', '対応表', 'lint・実行テスト'].map((x) => h('option', { value: x }, x)));
    const content = h('input', { type: 'text', id: 'rv-fb-content', 'aria-label': '戻す中身' });
    const fids = h('input', { type: 'text', id: 'rv-fb-findings', 'aria-label': '指摘 ID（空白で区切る）', placeholder: 'F01 F02' });
    const ref = h('input', { type: 'text', id: 'rv-fb-ref', 'aria-label': 'issue・PR' });
    return [h('h2', null, 'カタログ・観点書・対応表に戻す事項'),
      list.length ? h('ul', null, list.map((x, i) => h('li', null, h('strong', null, x.to), '：', x.content, (x.findings || []).length ? `（${x.findings.join('・')}）` : '', x.ref ? ` ${x.ref}` : '', ' ',
        h('button', { type: 'button', onclick: () => { list.splice(i, 1); m.feedback = list; if (!list.length) delete m.feedback; changed(true); } }, '消す')))) : h('p', { class: 'muted' }, 'まだありません。'),
      h('form', { class: 'filters', onsubmit: (e) => {
        e.preventDefault();
        if (!content.value.trim()) { content.focus(); return; }
        const x = { to: to.value, content: content.value.trim() };
        const ids = fids.value.split(/[\s,、]+/).filter(Boolean);
        if (ids.some((i) => !m.findings.some((f) => f.id === i))) { fids.setCustomValidity('指摘の一覧に無い ID がある'); fids.reportValidity(); return; }
        if (ids.length) x.findings = ids;
        if (ref.value.trim()) x.ref = ref.value.trim();
        list.push(x); m.feedback = list; changed(true);
      } }, h('label', null, '戻す先', to), h('label', null, '中身', content), h('label', null, '指摘 ID', fids), h('label', null, 'issue・PR', ref), h('div', null, h('button', { type: 'submit' }, '足す')))];
  }

  // ---- analysis
  function coverage(who) {
    const ans = (qid) => who.some((rv) => rv.answers[qid]);
    const cols = R.roles.map((r) => ({ id: r.id, label: r.name, has: (x) => x.roles.includes(r.id) })).concat([{ id: 'none', label: '索引に無い', has: (x) => !x.roles.length }, { id: '', label: '計', has: () => true }]);
    return h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'coverage' }, h('caption', null, '答えた問い / 問いの数（段 × 役割。役割は観点書の 7. の索引。1 つの問いが複数の役割に入ることがある）'),
      h('thead', null, h('tr', null, h('th', { scope: 'col' }, '段'), cols.map((c) => h('th', { scope: 'col', class: 'num' }, c.label)))),
      h('tbody', null, R.stages.concat([{ id: '', name: '計' }]).map((s) => h('tr', { 'data-stage': s.id || 'all' }, h('th', { scope: 'row' }, s.name), cols.map((c) => {
        const qs = R.questions.filter((x) => (!s.id || x.stage === s.id) && c.has(x));
        const n = qs.filter((x) => ans(x.id)).length;
        const params = {}; if (s.id) params.stage = s.id; if (c.id) params.role = c.id;
        return h('td', { class: 'num' + (qs.length && n === qs.length ? ' done' : ''), 'data-cov': `${s.id || 'all'}|${c.id || 'all'}` }, qs.length ? h('a', { href: P.route('review', 'checklist', Object.assign({ ans: 'open' }, params)), title: `未回答 ${qs.length - n} 問を開く` }, `${n} / ${qs.length}`) : '—',
          qs.length && n === qs.length ? h('span', { class: 'vh' }, '（すべて回答）') : null);
      }))))));
  }
  function overlay() {
    const diags = CE.diagnostics();
    const byA = new Map();
    diags.forEach((d) => { if (d.anchorKind && d.anchorId) { const a = d.anchorKind + ':' + d.anchorId; if (!byA.has(a)) byA.set(a, { error: 0, warn: 0, info: 0 }); byA.get(a)[d.severity]++; } });
    const set = anchorSet();
    const rows = [];
    CE.anchors().forEach((a) => {
      const lintC = byA.get(a.anchor);
      const recs = visible().filter((rv) => own(rv.rows, a.anchor));
      const fs = findingsOf(a.anchor);
      if (!lintC && !recs.length && !fs.length) return;
      const flags = [];
      const approved = recs.some((rv) => rv.rows[a.anchor].decision === 'approve' && rowState(rv.rows[a.anchor], a.anchor, set) === 'current');
      if (lintC && lintC.error && approved) flags.push('lint の error があるのに承認');
      if (fs.some(([, f]) => f.verdict !== '却下') && approved) flags.push('指摘があるのに承認');
      if (recs.some((rv) => rowState(rv.rows[a.anchor], a.anchor, set) === 'stale')) flags.push('再確認が要る');
      if (lintC && (lintC.error || lintC.warn) && !recs.length && !fs.length) flags.push('lint の指摘があるのに、レビューの記録が無い');
      rows.push({ a, lintC, recs, fs, flags });
    });
    rows.sort((x, y) => y.flags.length - x.flags.length);
    return [h('p', { class: 'muted' }, 'lint（JSON Schema・claim_lint）の指摘がある行と、レビューの判定・指摘がある行を重ねます。注意の多い行が上です。claim_lint を読み込んでいないときは、ブラウザの Schema と YAML の指摘だけです。'),
      h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'overlay' }, h('thead', null, h('tr', null, ['行', 'lint（error / warn / info）', 'レビューの判定', '指摘', '注意'].map((x) => h('th', { scope: 'col' }, x)))),
        h('tbody', null, rows.length ? rows.map((r) => h('tr', { 'data-anchor': r.a.anchor, 'data-flags': String(r.flags.length) }, h('th', { scope: 'row' }, rowLink(r.a.anchor)),
          h('td', null, r.lintC ? `${r.lintC.error} / ${r.lintC.warn} / ${r.lintC.info}` : '—'), h('td', null, rowBadges(r.a.anchor)),
          h('td', null, r.fs.length ? r.fs.map(([, f]) => code(f.id)) : '—'), h('td', null, r.flags.length ? h('ul', null, r.flags.map((x) => h('li', null, H.badge('warn', '▲', x)))) : '—')))
          : h('tr', null, h('td', { colspan: '5', class: 'muted' }, '重ねる行がありません。')))))];
  }
  function diffBlock() {
    const files = h('input', { type: 'file', id: 'rv-base-files', multiple: true, accept: '.yaml,.yml', class: 'vh', tabindex: '-1', 'aria-hidden': 'true' });
    const folder = h('input', { type: 'file', id: 'rv-base-folder', webkitdirectory: true, multiple: true, class: 'vh', tabindex: '-1', 'aria-hidden': 'true' });
    const rev = h('input', { type: 'file', id: 'rv-base-review', accept: '.yaml,.yml', class: 'vh', tabindex: '-1', 'aria-hidden': 'true' });
    const readFiles = (list) => Promise.all(Array.from(list || []).map((f) => f.text().then((t) => [f.name, t]))).then((xs) => {
      const texts = {}; xs.forEach(([n, t]) => { if (/^(claims|token_types|hops|catalog_answers)\.yaml$/.test(n)) texts[n] = t; });
      const r = CE.hashesOfTexts(texts);
      st.base = { kind: 'files', label: `前の版のファイル（${Object.keys(texts).join('・') || 'なし'}）`, hashes: r.hashes, errors: r.errors };
      P.render();
    });
    files.addEventListener('change', () => readFiles(files.files));
    folder.addEventListener('change', () => readFiles(folder.files));
    rev.addEventListener('change', () => {
      const f = rev.files && rev.files[0];
      if (!f) return;
      f.text().then((t) => {
        const r = parseReview(t, f.name);
        if (r.error) { CE.ask('前の版の review.yaml を読めません', r.error, [['ok', '閉じる']]); return; }
        const hashes = {};
        r.data.reviews.forEach((rv) => Object.keys(rv.rows).forEach((a) => { const x = rv.rows[a]; if (!hashes[a] || hashes[a].at < x.at) hashes[a] = x; }));
        const hs = {}; Object.keys(hashes).forEach((a) => { hs[a] = hashes[a].hash; });
        st.base = { kind: 'review', label: `前のレビューの記録（${f.name}、記録した ${Object.keys(hs).length} 行のハッシュ）`, hashes: hs, errors: [] };
        P.render();
      });
    });
    const d = baseDiff();
    return [h('p', { class: 'muted' }, '前の版の台帳（claims.yaml・token_types.yaml・hops.yaml・catalog_answers.yaml）か、前のレビューの記録（review.yaml。記録した行のハッシュを前の版とみなす）を読み込むと、行の内容のハッシュを比べて、変わった行を出します。「行ごとの判定」で、変わった行だけに絞れます。'),
      h('p', { class: 'muted small' }, 'claim_lint の diff（L10、CI の ', code('python tools/claim_lint diff --base origin/main <dir>'), '）との関係：L10 は、変更が受け手を壊すか（削除・型の変更・必須化など）を規則で確かめます。ここは、壊すかどうかにかかわらず、内容が変わった行を全部出します（Python では ', code('python tools/review_record.py diff <前の版> <dir>'), '）。L10 が通っても、変わった行は再レビューの対象です。'),
      h('p', { class: 'buttons' }, h('button', { type: 'button', id: 'rv-base-files-btn', onclick: () => files.click() }, '前の版のファイルを開く'), files, ' ',
        h('button', { type: 'button', id: 'rv-base-folder-btn', onclick: () => folder.click() }, '前の版のフォルダを開く'), folder, ' ',
        h('button', { type: 'button', id: 'rv-base-review-btn', onclick: () => rev.click() }, '前の review.yaml を開く'), rev,
        st.base ? [' ', h('button', { type: 'button', onclick: () => { st.base = null; P.render(); } }, '前の版を外す')] : null),
      d ? h('div', { id: 'rv-diff', 'data-changed': String(d.changed.length), 'data-added': String(d.added.length), 'data-removed': String(d.removed.length) },
        h('p', null, st.base.label, '：', `変わった ${d.changed.length}・足された ${d.added.length}・消えた ${d.removed.length}・同じ ${d.same.length}`, d.unknown.length ? `・前の記録に無い ${d.unknown.length}` : '', ' ',
          h('a', { href: P.route('review', 'rows', { changed: '1' }) }, '変わった行だけを判定する')),
        st.base.errors && st.base.errors.length ? h('p', { class: 'err' }, st.base.errors.join('、')) : null,
        [['changed', '変わった'], ['added', '足された'], ['removed', '消えた']].map(([k, label]) => d[k].length ? h('p', null, h('strong', null, label + '：'), h('span', { class: 'codes' }, d[k].map((a) => k === 'removed' ? code(a) : rowLink(a)))) : null))
        : h('p', { class: 'muted' }, '前の版を読み込んでいません。')];
  }
  function linksBlock() {
    const used = new Map();
    R.questions.forEach((x) => x.link_refs.forEach((r) => { if (r.kind === 'review') { const k = r.path + '#' + r.anchor; if (!used.has(k)) used.set(k, []); used.get(k).push(x.id); } }));
    return [h('h3', null, '対比表'), h('ul', null, R.contrasts.map((c) => h('li', null, h('a', { href: gh(c.file) }, c.title), ' ',
      h('span', { class: 'muted small' }, c.sections.map((s) => { const n = (used.get('contrasts/' + c.name + '#' + s.id) || []).length; return [h('a', { href: gh(c.file, s.id) }, s.title), n ? `（問い ${n}）` : '', ' ']; }))))),
      h('h3', null, '判断の木'), h('ul', null, R.decision_tree.sections.map((s) => h('li', null, h('a', { href: gh(R.decision_tree.file, s.id) }, `${s.number} ${s.title}`),
        (used.get('decision_tree#' + s.id) || []).length ? h('span', { class: 'muted small' }, ` 問い：${used.get('decision_tree#' + s.id).join('・')}`) : null)))];
  }
  function samplingBlock(m) {
    if (!m) return h('p', { class: 'muted' }, 'レビュアーを決めると、抜き取りを記録できます。');
    const sm = m.sampling;
    const seed = h('input', { type: 'text', id: 'rv-seed', value: sm ? sm.seed : '', 'aria-describedby': 'rv-seed-hint' });
    const cnt = h('select', { id: 'rv-seed-count' }, ['2', '3'].map((x) => h('option', { value: x, selected: String(sm ? sm.count : 3) === x ? true : null }, x + ' 件')));
    const cands = rejectedAnchors();
    const out = [h('p', { class: 'muted', id: 'rv-seed-hint' }, `claims.yaml の却下の行（${cands.length} 行）から、乱数の種で 2〜3 行を選び、理由（rationale）を rationale_rubric.md の RR1〜RR7 で採点します。選び方は sha256(種 + ":" + 行の名前) の順で、種を記録するので、同じ種なら誰がやっても同じ行になります（tools/review_record.py sample）。`),
      h('form', { class: 'filters', onsubmit: (e) => {
        e.preventDefault();
        if (!seed.value.trim()) { const r = new Uint8Array(4); crypto.getRandomValues(r); seed.value = Array.from(r).map((x) => x.toString(16).padStart(2, '0')).join(''); }
        const picked = draw(seed.value.trim(), Number(cnt.value));
        const pop = populationHash();
        const same = sm && sm.seed === seed.value.trim() && sm.count === Number(cnt.value) && (!sm.population || sm.population === pop);
        const next = { seed: seed.value.trim(), count: Number(cnt.value), picked, population: pop };
        if (sm && same && sm.scores) next.scores = sm.scores;
        if (sm && !same) {
          // the earlier draw is kept, not replaced silently (tools/review_record.py sample --reseed does the same)
          const old = { seed: sm.seed, count: sm.count, picked: sm.picked, replaced_at: now(), reason: 'エディターで引き直した' + (sm.population && sm.population !== pop ? '（抜き取りの母集団が変わった）' : '') };
          if (sm.population) old.population = sm.population;
          if (sm.scores) old.scores = sm.scores;
          next.reason = old.reason;
          next.previous = (sm.previous || []).concat([old]);
          const kept = {}; Object.keys(sm.scores || {}).forEach((a) => { if (picked.includes(a)) kept[a] = sm.scores[a]; });
          if (Object.keys(kept).length) next.scores = kept;
        } else if (sm && sm.previous) { next.previous = sm.previous; if (sm.reason) next.reason = sm.reason; }
        m.sampling = next;
        changed(true);
      } }, h('label', null, '乱数の種（空なら作る）', seed), h('label', null, '件数', cnt), h('div', null, h('button', { type: 'submit', id: 'rv-draw' }, '抜き取る')))];
    if (sm && sm.population && sm.population !== populationHash()) {
      out.push(h('p', { class: 'note warn', id: 'rv-pop-changed', role: 'status' }, '⚠ 抜き取りの母集団が変わった：記録した後に、却下の行か、その内容が変わりました。記録した抜き取りは、その時の台帳では正しいものです。引き直すなら「抜き取る」を押します（前の抜き取りは previous に残ります）。'));
    }
    if (sm) {
      out.push(h('p', { id: 'rv-picked', 'data-picked': sm.picked.join(' ') }, `種 ${sm.seed} で選んだ行：`, h('span', { class: 'codes' }, sm.picked.map(rowLink))));
      sm.picked.forEach((a) => {
        const r = CE.rowOf(a);
        const sc = (sm.scores && sm.scores[a]) || {};
        const sid = a.replace(/[^A-Za-z0-9_-]/g, '_');
        const set = (k, v) => { sm.scores = sm.scores || {}; const cur = sm.scores[a] || {}; if (v === '' || v === undefined) delete cur[k]; else cur[k] = v;
          const vals = R.rubric.items.map((it) => cur[it.id]); if (vals.every((x) => x)) cur.pass = !vals.includes('否'); sm.scores[a] = cur; changed(false); };
        out.push(h('section', { class: 'effect', 'data-sample': a }, h('h3', null, rowLink(a)),
          r && r.row ? h('dl', { class: 'obj' }, ['rationale', 'assumption', 'revisit_trigger'].map((k) => [h('dt', null, k), h('dd', null, own(r.row, k) ? H.value(r.row[k]) : '（未記入）')])) : h('p', { class: 'muted' }, '今の台帳に無い行'),
          h('div', { class: 'rv-rr' }, R.rubric.items.map((it) => h('label', null, h('span', { title: it.question }, `${it.id} ${it.name}`), h('select', { 'data-rr': a + '.' + it.id, onchange: (e) => set(it.id, e.target.value) },
            ['', '満', '否', '対象外'].map((v) => h('option', { value: v, selected: sc[it.id] === v ? true : null }, v || '（未）'))))),
          h('label', null, 'メモ', h('input', { type: 'text', id: 'rv-rr-note-' + sid, value: sc.note || '', onchange: (e) => set('note', e.target.value.trim()) }))),
          h('p', { class: 'small' }, '合否：', sc.pass === undefined ? '（RR1〜RR7 をすべて付けると決まる）' : sc.pass ? H.badge('ok', '✓', '合格') : H.badge('ng', '✖', '不合格'))));
      });
    }
    return out;
  }
  function rejectedAnchors() { return CE.anchors().filter((a) => a.kind === 'claims' && a.row && a.row.decision === '却下').map((a) => a.anchor).sort(); }
  // sha256 of the population of the draw ('<anchor> <row hash>' per rejected row, sorted): tools/review_record.py population
  function populationHash() { return CE.sha256(rejectedAnchors().map((a) => a + ' ' + (CE.rowHash(a) || '')).join('\n')); }
  function draw(seed, count) {
    return rejectedAnchors().map((a) => [CE.sha256(seed + ':' + a), a]).sort((x, y) => (x[0] < y[0] ? -1 : x[0] > y[0] ? 1 : 0)).slice(0, count).map((x) => x[1]);
  }
  function viewAnalysis() {
    const m = mine();
    const vis = visible();
    const whoSel = h('select', { id: 'rv-cov-who', onchange: () => { box.textContent = ''; box.append(coverage(whoSel.value === 'me' && m ? [m] : vis)); } },
      m ? h('option', { value: 'me' }, `自分（${m.reviewer.name}）`) : null, h('option', { value: 'all' }, `表示している全員（${vis.length} 人）`));
    const box = h('div', { id: 'rv-coverage' }, coverage(m ? [m] : vis));
    const pa = paFiles();
    return [h('h1', { tabindex: '-1' }, '分析'),
      h('nav', { class: 'toc', 'aria-label': '分析の節' }, [['rv-a-cov', '観点の網羅'], ['rv-a-ov', 'lint と指摘の重ね合わせ'], ['rv-a-diff', '前の版との差分'], ['rv-a-links', '対比表と判断の木'], ['rv-a-pa', '25 問の回答'], ['rv-a-sample', '却下の理由の抜き取り']]
        .map(([id, t]) => h('a', { href: '#' + id, onclick: (e) => { e.preventDefault(); const el = document.getElementById(id); if (el) { el.scrollIntoView(); el.focus(); } } }, t))),
      h('h2', { id: 'rv-a-cov', tabindex: '-1' }, '観点の網羅'), h('p', null, h('label', { for: 'rv-cov-who' }, '誰の回答：'), whoSel), box,
      h('h2', { id: 'rv-a-ov', tabindex: '-1' }, '検査の指摘とレビューの指摘の重ね合わせ'), overlay(),
      h('h2', { id: 'rv-a-diff', tabindex: '-1' }, '前の版との差分'), diffBlock(),
      h('h2', { id: 'rv-a-links', tabindex: '-1' }, '対比表と判断の木'), linksBlock(),
      h('h2', { id: 'rv-a-pa', tabindex: '-1' }, '25 問の回答'),
      h('p', null, `claim_request_*.md が ${pa.length} 件あります（共有クレームごとの追加前の 25 問）。`, h('a', { href: '#/review/pa' }, '25 問の回答の一覧を開く'), '（問いごとに、全部のクレームの回答を並べる）'),
      h('h2', { id: 'rv-a-sample', tabindex: '-1' }, '却下の理由の抜き取り'), samplingBlock(m)];
  }

  // ---- the 25 answers of claim_request_*.md
  function paFiles() {
    return CE.state().files.filter((n) => /^claim_request_.+\.md$/.test(n)).map((n) => {
      const text = CE.fileText(n) || '';
      const target = (/対象：[^`\n]*`([^`]+)`/.exec(text) || [])[1] || '';
      const rows = {};
      text.split(/\r?\n/).forEach((l, i) => { const m = /^\|\s*(\d{1,2})\s*\|(.*)\|(.*)\|(.*)\|\s*$/.exec(l); if (m) rows[Number(m[1])] = { q: m[2].trim(), a: m[3].trim(), src: m[4].trim(), line: i + 1 }; });
      return { name: n, target, rows };
    });
  }
  function viewPa(query) {
    const q = new URLSearchParams(query || '');
    const n = Number(q.get('q')) || 0;
    const files = paFiles();
    const qtext = (k) => { const f = files.find((x) => x.rows[k]); return f ? f.rows[k].q : ''; };
    const sel = h('select', { id: 'rv-pa-q', onchange: () => { location.hash = '#/review/pa' + (sel.value ? '?q=' + sel.value : ''); } }, h('option', { value: '' }, '問いを選ぶ'),
      Array.from({ length: 25 }, (_, i) => i + 1).map((k) => h('option', { value: String(k), selected: k === n ? true : null }, `問 ${k}：${qtext(k)}`)));
    const pq = n ? QBY.get('pa-' + String(n).padStart(2, '0')) : null;
    const out = [h('h1', { tabindex: '-1', 'data-pa': String(n) }, '追加前の 25 問の回答'),
      h('p', { class: 'lead' }, 'claim_request_*.md（共有クレームごとの 25 問）の回答を、問いごとに並べます。回答が妥当かを観点書の 1.2（pa-01〜pa-25）で確かめます。'),
      h('p', null, h('label', { for: 'rv-pa-q' }, '問い：'), sel)];
    if (!files.length) out.push(h('p', { class: 'muted' }, 'claim_request_*.md が開かれていません。'));
    if (n && pq) out.push(h('div', { class: 'note' }, h('p', null, h('a', { href: P.route('review', 'checklist', { q: pq.id }) }, pq.id), ' ', H.inlineRepo(pq.text))));
    if (n) {
      out.push(h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'pa' }, h('caption', null, `問 ${n}：${qtext(n)}`),
        h('thead', null, h('tr', null, ['クレーム', '回答', '出どころ', ''].map((x) => h('th', { scope: 'col' }, x)))),
        h('tbody', null, files.map((f) => { const r = f.rows[n]; return h('tr', { 'data-pa-file': f.name }, h('th', { scope: 'row' }, f.target ? rowLink('claims:' + f.target) : code(f.name)),
          h('td', null, r ? H.inline(r.a) : h('span', { class: 'err' }, '（回答が無い）')), h('td', null, r ? H.inline(r.src) : '—'),
          h('td', null, r ? h('button', { type: 'button', class: 'link', onclick: () => CE.goto(f.name, r.line) }, `${f.name}:${r.line}`) : null)); })))));
    }
    out.push(h('h2', null, 'クレームごとの 25 問'), files.map((f) => H.foldable(H.foldKey('pa', f.name), h('span', null, code(f.name), f.target ? ' ― ' + f.target : ''), () => h('div', { class: 'tablewrap' }, h('table', null,
      h('thead', null, h('tr', null, ['#', '問い', '回答', '出どころ'].map((x) => h('th', { scope: 'col' }, x)))),
      h('tbody', null, Object.keys(f.rows).map((k) => h('tr', { class: Number(k) === n ? 'exceeds' : null }, h('th', { scope: 'row' }, k), h('td', null, f.rows[k].q), h('td', null, H.inline(f.rows[k].a)), h('td', null, H.inline(f.rows[k].src))))))), { closed: true })));
    return out;
  }

  // ---- the report (the twin of tools/review_record.py report_text)
  // every value of review.yaml is escaped for Markdown: & < > as entities (no raw HTML), \ ` * _ [ ] ~ with a backslash,
  // | as a full-width bar, line breaks as spaces; a line that starts with a value is kept text (PR #52 check)
  function md(s) {
    return (s === null || s === undefined ? '' : String(s)).replace(/\s*\n\s*/g, ' ').trim()
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/([\\`*_[\]~])/g, '\\$1').replace(/\|/g, '｜');
  }
  function mdLine(s) { const t = md(s); return /^(?:[#>+\-=*]|\d+[.)])/.test(t) ? '\\' + t : t; }
  function cell(s) { return md(s) || '—'; }
  function row(cells) { return '| ' + cells.join(' | ') + ' |'; }
  function date(t) { return String(t || '').slice(0, 10); }
  function short(a) { return a.startsWith('claims:') ? a.split(':').slice(1).join(':') : a; }
  function independenceText(data, rv) {
    const ind = rv.independence || {};
    if (!data.independent && !rv.independence) return '';
    const parts = [];
    if (ind.mode === 'broken') parts.push(`独立レビュー：提出の前に外れた（${ind.broken_at || '日時不明'}。${ind.reason || '理由の記録なし'}）`);
    else parts.push('独立レビュー：提出まで、ほかのレビュアーの記録を画面で隠した（画面で隠すだけで、review.yaml を開けば見える。守ったかは自己申告）');
    if (ind.viewed_others_at) parts.push(`ほかのレビュアーの記録を初めて見た日時 ${ind.viewed_others_at}`);
    const n = Object.values(rv.answers || {}).filter((x) => x.edited_after_viewing_others).length + Object.values(rv.rows || {}).filter((x) => x.edited_after_viewing_others).length +
      (rv.findings || []).filter((x) => x.edited_after_viewing_others).length;
    if (n) parts.push(`その後に直した記録 ${n} 件（回答・判定・指摘の edited_after_viewing_others）`);
    if (rv.submitted && rv.updated && String(rv.updated) > String(rv.submitted)) parts.push(`提出（${rv.submitted}）の後に更新した（${rv.updated}）`);
    return parts.join('。');
  }
  function reportText(data, rv, label, version) {
    const form = R.report;
    const heads = {}; form.sections.forEach((s) => { heads[s.heading.slice(0, 2)] = s; });
    const stageName = new Map(R.stages.map((s) => [s.id, s.name]));
    const qs = R.questions;
    const qids = new Set(qs.map((x) => x.id));
    const ctx = rv.context || {};
    const who = rv.reviewer;
    const llm = who.kind === 'llm';
    const lines = [`# レビューレポート：${md(label || data.design)}`, '',
      '> 設計書のエディターのレビューモード（#50）が `review.yaml` から生成した。レビュアーの名前は自己申告で、本当の承認は GitHub の PR のレビューで行う。' + (llm ? 'レビュアーは LLM で、人による点検は未実施。' : ''), ''];
    const head = (k) => { lines.push('## ' + heads[k].heading); lines.push(''); };
    const table = (k, rows) => {
      const hd = heads[k].header;
      lines.push(row(hd)); lines.push(row(hd.map(() => '---')));
      (rows.length ? rows : [hd.map(() => '')]).forEach((r) => lines.push(r.some((x) => x) ? row(r) : '|' + ' |'.repeat(hd.length)));
      lines.push('');
    };
    const tgt = rv.target || {};
    const sm = rv.sampling || null;
    const scores = (sm && sm.scores) || {};
    const scored = ((sm && sm.picked) || []).filter((a) => own(scores, a));
    const passed = scored.filter((a) => scores[a].pass).length;
    const cand = rejectedAnchors().length;
    const ans = rv.answers || {};
    const tot = { yes: 0, no: 0, na: 0 };
    const per = R.stages.map((s) => {
      const c = { yes: 0, no: 0, na: 0 };
      qs.forEach((x) => { if (x.stage === s.id && own(ans, x.id)) c[ans[x.id].answer]++; });
      Object.keys(c).forEach((k) => { tot[k] += c[k]; });
      return `${s.name.split(' ').slice(1).join(' ')} Yes ${c.yes}／No ${c.no}／該当なし ${c.na}`;
    });
    const answered = tot.yes + tot.no + tot.na;
    const gone = Object.keys(ans).filter((q) => !qids.has(q));
    const ci = ctx.ci;
    const ciText = !ci ? '記録なし' : `claim_lint error ${ci.error}・warn ${ci.warn}・info ${ci.info}` + (ci.profile ? `（profile ${ci.profile}）` : '') +
      (!own(ci, 'matches_design') ? '' : '。設計書の 1. と' + (ci.matches_design ? '一致' : '一致しない')) + (ci.note ? `。${ci.note}` : '');
    const samp = !sm ? '記録なし' : `乱数の種「${sm.seed}」（claims.yaml の却下の行 ${cand} 行から ${sm.count} 行。sha256(種:行) の順）：` + sm.picked.map(short).join('・') +
      `。${scored.length} 件を採点、合格 ${passed}・不合格 ${scored.length - passed}` + (scored.length < sm.picked.length ? `（未採点 ${sm.picked.length - scored.length}）` : '') +
      (sm.reason ? `。引き直した（${sm.reason}。前の抜き取り ${(sm.previous || []).length} 件）` : '');
    const versions = R.versions || {};
    const nowP = R.template_version;
    const nowR = versions['templates/review/report_template.md'];
    const mt = rv.materials || {};
    const recP = mt.perspectives || version;
    const recR = mt.report_template;
    let mats = 'templates/review（レビューした時の版：perspectives.md ' + (recP || '記録なし') + (recR ? `、report_template.md ${recR}` : '') +
      (mt.questions !== undefined && mt.questions !== null ? `、問い ${mt.questions} 問` : '') + '）';
    const differs = (recP && recP !== nowP) || (recR && nowR && recR !== nowR) || (mt.questions !== undefined && mt.questions !== null && mt.questions !== qs.length);
    if (differs) mats += `。注意：今の教材は perspectives.md ${nowP}` + (nowR ? `・report_template.md ${nowR}` : '') + `・問い ${qs.length} 問で、レビューの後に変わった（この表の問いの数と 8. は今の観点書で数えた）`;
    if (ctx.materials) mats += '。' + ctx.materials;
    let reviewer = `${who.name}（` + (llm ? 'LLM' + (who.model ? `：${who.model}` : '') : '人') + '。名前は自己申告）' + (ctx.roles_order ? `。${ctx.roles_order}` : '');
    const ind = independenceText(data, rv);
    if (ind) reviewer += '。' + ind;
    const dt = date(rv.started) + (rv.submitted && date(rv.submitted) !== date(rv.started) ? `〜${date(rv.submitted)}` : '');
    const values = { '対象': `${data.design}` + (tgt.commit ? `（版 ${tgt.commit}）` : '') + (tgt.note ? `。${tgt.note}` : ''),
      'Lite／Full': ctx.lite_full || '記録なし', '実施した手順の段': ctx.steps || '記録なし', 'レビュアーと役割': reviewer, '実施日': dt, '使った教材の版': mats,
      'CI の結果': ciText, '抜き取りの結果': samp,
      '問いの回答': `全 ${qs.length} 問のうち ${answered} 問に回答（未回答 ${qs.length - answered}）。` + per.join('。') + `。合計 Yes ${tot.yes}／No ${tot.no}／該当なし ${tot.na}` +
        (gone.length ? `。今の観点書に無い問いへの回答 ${gone.length} 件` : '') };
    head('1.'); table('1.', heads['1.'].items.map((k) => [k, cell(values[k])]));
    const fs = rv.findings || [];
    head('2.');
    table('2.', fs.map((f) => [cell(f.id), cell(f.location), cell(f.content + (f.verdict_reason ? `（判定の理由：${f.verdict_reason}）` : '')), cell(f.severity), cell(f.origin), cell(f.kind),
      cell(f.kind === MISMATCH ? f.confused_question : null), cell(f.verdict)]));
    head('3.');
    table('3.', fs.map((f) => { const r = f.response || {}; return [cell(f.id), cell(r.owner), cell(r.due), cell(r.state || '未着手'), cell(r.ref)]; }));
    const esc = rv.escalations || {};
    head('4.');
    table('4.', (esc.applies || []).map((e) => [cell(e.criterion), cell(e.location), cell(e.to), cell(e.due), cell(e.conclusion)]));
    const na = esc.not_applicable;
    lines.push('当てはまらなかった基準：' + (na && na.length ? na.map(md).join('・') : '（記録なし）'));
    lines.push('');
    head('5.');
    table('5.', (rv.feedback || []).map((x) => [cell(x.to), cell(x.content), cell((x.findings || []).join('・')), cell(x.ref)]));
    head('6.');
    table('6.', scored.map((a) => [cell(short(a)), 'rationale'].concat([1, 2, 3, 4, 5, 6, 7].map((i) => cell(scores[a]['RR' + i] || '対象外')), [scores[a].pass ? '合格' : '不合格'])));
    const notes = scored.filter((a) => scores[a].note).map((a) => `- ${md(short(a))}：${md(scores[a].note)}`);
    if (notes.length) { notes.forEach((x) => lines.push(x)); lines.push(''); }
    head('7.');
    if (ctx.human_check) { lines.push(mdLine(ctx.human_check)); lines.push(''); }
    lines.push(llm ? '人による点検は未実施（このレビューは LLM のセッションのもの。人のレビュアーの採否は未了）。'
      : 'レビュアーは人（名前は自己申告）。templates/CONTRIBUTING.md の 3. の点検の取り決めによる点検かは、この記録からは分からない。');
    lines.push('');
    lines.push('レビュアーの名前は自己申告です（エディターにはログインが無い）。本当の承認は GitHub の PR のレビューで行います。');
    lines.push('');
    head('8.');
    table('8.', qs.filter((x) => own(ans, x.id)).map((x) => [cell(stageName.get(x.stage) || '—'), x.id, ANS[ans[x.id].answer][2], cell(ans[x.id].memo)]));
    const left = qs.filter((x) => !own(ans, x.id)).map((x) => x.id);
    if (left.length) { lines.push(`未回答：${left.length} 問（` + left.join('・') + '）'); lines.push(''); }
    if (gone.length) { lines.push(`今の観点書に無い問いへの回答：${gone.length} 件（` + gone.map(md).join('・') + '）'); lines.push(''); }
    lines.push('## 9. 行ごとの記録（エディターのレビューモード、#50。生成した時の台帳と比べた状態）');
    lines.push('');
    lines.push('行の内容のハッシュ（RFC 8785 JCS の SHA-256、`tools/row_hash.py`）に結びつけた判定です。記録の後に行が変わると「再確認が要る」になります。' +
      'ハッシュはその行の値だけを見ます（参照するトークン種別・ホップの行、25 問の回答、design.md の本文を変えても再確認にはなりません）。');
    lines.push('');
    const rows = rv.rows || {};
    const set = anchorSet();
    const stOf = {}; Object.keys(rows).forEach((a) => { stOf[a] = rowState(rows[a], a, set); });
    lines.push(row(['行', '判定', '日時', '今の行との対応', 'コメント']));
    lines.push(row(['---', '---', '---', '---', '---']));
    const labelOf = { current: '一致（記録のときのまま）', stale: '再確認が要る（行が変わった）', missing: '台帳に無い行' };
    const keys = Object.keys(rows).sort();
    keys.forEach((a) => {
      const r = rows[a]; const kind = r.reviewer_kind || who.kind;
      lines.push(row([cell(a), DEC[r.decision][2] + (kind === 'llm' ? '（LLM）' : ''), cell(r.at), labelOf[stOf[a]] + `（${r.hash.slice(0, 12)}）`, cell(r.comment)]));
    });
    if (!keys.length) lines.push('|' + ' |'.repeat(5));
    const c = {}; Object.keys(DEC).forEach((k) => { c[k] = keys.filter((a) => rows[a].decision === k).length; });
    lines.push('');
    lines.push(`計 ${keys.length} 行：` + Object.keys(DEC).map((k) => `${DEC[k][2]} ${c[k]}`).join('・') +
      `。再確認が要る ${keys.filter((a) => stOf[a] === 'stale').length}・台帳に無い ${keys.filter((a) => stOf[a] === 'missing').length}`);
    return lines.join('\n') + '\n';
  }
  function viewReport(query) {
    const q = new URLSearchParams(query || '');
    const vis = visible();
    const m = mine();
    const name = q.get('who') || (m ? m.reviewer.name : vis[0] && vis[0].reviewer.name);
    const rv = vis.find((x) => x.reviewer.name === name);
    const who = h('select', { id: 'rv-rep-who', onchange: () => { location.hash = P.route('review', 'report', { who: who.value }); } }, vis.map((x) => h('option', { value: x.reviewer.name, selected: x === rv ? true : null }, x.reviewer.name)));
    const out = [h('h1', { tabindex: '-1' }, 'レビューレポート'),
      h('p', { class: 'lead' }, '記録から、templates/review/report_template.md の様式の Markdown を作ります（1 人のレビュアーごと）。様式どおりかは ', code('python tools/review_check.py --report <ファイル>'), ' で確かめられます。CI では、記入例の review.yaml から作ったレポートが、コミットしたレポートと一致するかを ', code('python tools/review_record.py report … --check'), ' で確かめます。')];
    if (!rv) { out.push(h('p', { class: 'muted' }, '表示できるレビューの記録がありません。')); return out; }
    out.push(h('p', null, h('label', { for: 'rv-rep-who' }, 'レビュアー：'), who));
    if (rv === m) out.push(contextForm(m));
    const text = reportText(st.file, rv, undefined, st.version);
    out.push(h('p', { class: 'buttons' }, h('button', { type: 'button', class: 'primary', id: 'rv-report-download', onclick: () => CE.download(`review-report-${date(rv.started) || 'draft'}.md`, new Blob([text], { type: 'text/markdown' })) }, 'レポートを書き出す（.md）')),
      h('pre', { id: 'rv-report', class: 'rv-report', tabindex: '0', 'aria-label': '生成したレポート', 'data-file-preview': 'review-report.md' }, text));
    return out;
  }
  function contextForm(m) {
    const c = m.context || {};
    const t = m.target || {};
    const fld = (id, label, v, wide) => h('label', { class: wide ? 'wide' : null }, label, h('input', { type: 'text', id, value: v || '' }));
    const ci = c.ci || {};
    const lc = CE.lintCounts();
    return h('form', { class: 'filters', id: 'rv-context', onsubmit: (e) => {
      e.preventDefault();
      const v = (id) => ($('#' + id).value || '').trim();
      const ctx = {};
      ['lite_full', 'steps', 'roles_order', 'materials', 'human_check'].forEach((k) => { if (v('rv-ctx-' + k)) ctx[k] = v('rv-ctx-' + k); });
      const num = (id) => (v(id) === '' ? null : Number(v(id)));
      if (v('rv-ctx-ci-error') !== '') {
        const x = { error: num('rv-ctx-ci-error') || 0, warn: num('rv-ctx-ci-warn') || 0, info: num('rv-ctx-ci-info') || 0 };
        if (v('rv-ctx-ci-profile')) x.profile = v('rv-ctx-ci-profile');
        if (v('rv-ctx-ci-match')) x.matches_design = v('rv-ctx-ci-match') === 'yes';
        if (v('rv-ctx-ci-note')) x.note = v('rv-ctx-ci-note');
        ctx.ci = x;
      }
      if (Object.keys(ctx).length) m.context = ctx; else delete m.context;
      const tg = {};
      if (v('rv-ctx-commit')) tg.commit = v('rv-ctx-commit');
      if (v('rv-ctx-tnote')) tg.note = v('rv-ctx-tnote');
      if (Object.keys(tg).length) m.target = tg; else delete m.target;
      st.focus = 'rv-ctx-save';
      changed(true);
    } }, h('h2', { class: 'wide' }, '基本情報（レポートの 1.）'),
    fld('rv-ctx-commit', '対象の版（コミット）', t.commit), fld('rv-ctx-tnote', '対象の注記', t.note), fld('rv-ctx-lite_full', 'Lite／Full の確認', c.lite_full, true),
    fld('rv-ctx-steps', '実施した手順の段', c.steps, true), fld('rv-ctx-roles_order', '役割の切り替えの順と日付', c.roles_order, true), fld('rv-ctx-materials', '教材の版の補足', c.materials, true),
    fld('rv-ctx-ci-error', 'CI：error', ci.error), fld('rv-ctx-ci-warn', 'CI：warn', ci.warn), fld('rv-ctx-ci-info', 'CI：info', ci.info),
    h('label', null, 'CI：profile', h('select', { id: 'rv-ctx-ci-profile' }, ['', 'full', 'lite'].map((x) => h('option', { value: x, selected: (ci.profile || '') === x ? true : null }, x || '—')))),
    h('label', null, 'CI：設計書の 1. と', h('select', { id: 'rv-ctx-ci-match' }, [['', '—'], ['yes', '一致'], ['no', '一致しない']].map(([x, l]) => h('option', { value: x, selected: (own(ci, 'matches_design') ? (ci.matches_design ? 'yes' : 'no') : '') === x ? true : null }, l)))),
    fld('rv-ctx-ci-note', 'CI：注記', ci.note, true),
    fld('rv-ctx-human_check', '点検状況（7.）', c.human_check, true),
    h('div', { class: 'wide' }, h('button', { type: 'submit', class: 'primary', id: 'rv-ctx-save' }, '基本情報を記録する'), ' ',
      h('button', { type: 'button', id: 'rv-ctx-lint', disabled: lc ? null : true, title: lc ? '' : 'claim_lint が最新の内容で動いた後に使える', onclick: () => {
        $('#rv-ctx-ci-error').value = lc.error; $('#rv-ctx-ci-warn').value = lc.warn; $('#rv-ctx-ci-info').value = lc.info; $('#rv-ctx-ci-profile').value = lc.profile;
      } }, '検査の結果を写す')));
  }

  // ------------------------------------------------------------ the screens in the navigation
  function refreshCounts() {
    const m = mine();
    const a = document.querySelector('#nav a[data-view="review/checklist"] .cnt');
    if (a && R) a.textContent = ' ' + (m ? Object.keys(m.answers).length : 0) + '/' + R.questions.length;
    const s = $('#rv-file-state');
    if (s) { s.dataset.unsaved = unsaved() ? '1' : '0'; }
  }
  function rowHref(anchor) {
    const i = anchor.indexOf(':'); const kind = anchor.slice(0, i); const id = anchor.slice(i + 1);
    if (KIND_VIEW[kind]) return P.route(KIND_VIEW[kind], id);
    return P.route('review', 'rows', { state: 'stale' });
  }
  P.registerView('review', {
    group: 'レビュー',
    entry: 'レビューを始める・続ける',
    // the review on the dashboard (#53): progress, and the rows to look at again and the questions not answered
    summary: () => {
      if (!st.open || !R) return null;
      const m = mine(); const vis = visible(); const set = anchorSet();
      const stale = [];
      vis.forEach((rv) => Object.keys(rv.rows).forEach((a) => { if (rowState(rv.rows[a], a, set) === 'stale') stale.push([rv, a]); }));
      const todos = stale.slice(0, 8).map(([rv, a]) => ({ kind: 'stale', label: '再確認が要る', text: `${a}（${rv.reviewer.name} の「${DEC[rv.rows[a].decision][2]}」の後に行が変わった）`, href: rowHref(a) }));
      if (stale.length > 8) todos.push({ kind: 'stale', label: '再確認が要る', text: `すべて見る（${stale.length} 行）`, href: P.route('review', 'rows', { state: 'stale' }) });
      if (m) { const open = R.questions.length - Object.keys(m.answers).length; if (open) todos.push({ kind: 'question', label: '未回答の問い', text: `${open} 問（${m.reviewer.name}）`, href: P.route('review', 'checklist', { ans: 'open' }) }); }
      else todos.push({ kind: 'start', label: 'レビュー', text: 'レビュアーを決めると、回答と判定を記録できます', href: P.route('review') });
      const lines = [`レビュアー ${vis.length} 人` + (hiddenCount() ? `（ほか ${hiddenCount()} 人は独立レビューで隠している）` : '')];
      if (m) lines.push(`${m.reviewer.name}：回答 ${Object.keys(m.answers).length} / ${R.questions.length} 問・判定 ${Object.keys(m.rows).length} 行・指摘 ${m.findings.length} 件` + (m.submitted ? '・提出済み' : ''));
      lines.push(`再確認が要る判定 ${stale.length} 行`, unsaved() ? '書き出していない記録があります' : '書き出していない記録はありません');
      return { id: 'review', title: 'レビュー', href: P.route('review'), lines, todos };
    },
    nav: () => {
      if (!R) return [{ sub: '', label: 'はじめる・概要' }];
      const m = mine();
      let stale = 0;
      if (st.open) { const set = anchorSet(); visible().forEach((rv) => Object.keys(rv.rows).forEach((x) => { if (rowState(rv.rows[x], x, set) !== 'current') stale++; })); }
      return [{ sub: '', label: st.wizard ? 'はじめる' : '記録の概要' }, { sub: 'checklist', label: '観点のチェックリスト', count: (m ? Object.keys(m.answers).length : 0) + '/' + R.questions.length },
        { sub: 'rows', label: '行ごとの判定', count: stale ? '⟳' + stale : null }, { sub: 'findings', label: '指摘', count: String(visible().reduce((n, rv) => n + rv.findings.length, 0)) },
        { sub: 'analysis', label: '分析' }, { sub: 'pa', label: '25 問の回答' }, { sub: 'report', label: 'レポート' }];
    },
    render: (parts, query) => {
      if (!st.open || !R) return needOpen();
      noteViewing();
      const sub = parts[0] || '';
      if (sub === 'checklist') return viewChecklist(query);
      if (sub === 'rows') return viewRows(query);
      if (sub === 'findings') return viewFindings();
      if (sub === 'analysis') return viewAnalysis();
      if (sub === 'pa') return viewPa(query);
      if (sub === 'col') return viewColumn(parts.slice(1));
      if (sub === 'report') return viewReport(query);
      return viewOverview();
    },
  });

  const RV = {
    ready: () => !!R && st.open && !st.opening,
    data: () => JSON.parse(JSON.stringify(st.file)),
    text: () => dump(st.file),
    dump,
    me: () => st.me,
    unsaved,
    reportText: (name, label) => { const rv = st.file.reviews.find((x) => x.reviewer.name === name) || visible()[0]; return rv ? reportText(st.file, rv, label, st.version) : null; },
    draw,
    visibleNames: () => visible().map((r) => r.reviewer.name),
    // #56: the traits read from the open design and the questions of its short list (compared with tools/review_triage.py by the tests)
    traits: () => readTraits(), shortList: () => { const x = shortList(); return x ? { questions: Array.from(x.why.keys()), optional: Array.from(x.more), prompts: x.prompts.map((p) => p.id), morePrompts: x.morePrompts.map((p) => p.id) } : null; },
    importTexts: (list) => importFiles(list.map((x) => ({ name: x.name, text: () => Promise.resolve(x.text) }))),
    clock: null,
  };
  window.ClaimsReview = RV;
})();
