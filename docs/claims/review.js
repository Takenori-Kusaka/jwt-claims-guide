// The review flow of the design editor (#50, redesigned in #67 on the pattern of a pull request review). MIT (LICENSE).
// 「レビューを開始」 -> the reviewer looks at each row and marks it 「確認済み」 (a personal mark bound to the row's content
// hash, not an approval) -> comments are kept as 未提出 -> 「レビューを提出」 once, with a summary and one verdict
// (承認 / 変更を依頼 / コメントのみ) and the hashes of the rows viewed. A later review shows the rows that changed since.
// 確認事項 are the questions of templates/review/perspectives.md (data/review.js) that apply to this design.
// Nothing is sent: review.yaml is read with the File API and written with a download link, like the design files.
// The reviewer's name is self-declared (there is no login); the approval that counts is the GitHub pull request review.
'use strict';
(function () {
  // the build id (tools/build_claims_viewer.py, #53). An editor.js of another build (an old one kept in the browser's
  // cache) may not have what this module calls: then nothing is registered, and the banner asks for a reload
  const BUILD_ID = '523463319fd2';
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
  const F = window.ClaimsReviewFormat;  // review-format.js: the canonical text of review.yaml, v1 -> v2, the report
  if (!F) return;
  const $ = (s, r) => (r || document).querySelector(s);
  const own = (o, k) => o !== null && o !== undefined && Object.prototype.hasOwnProperty.call(o, k);
  const isObj = (x) => x !== null && typeof x === 'object' && !Array.isArray(x);

  const FORMAT = F.FORMAT;
  const SLOT = 'claims-editor:review:v1:';  // the slot of this browser (a v1 text kept there is read and migrated)
  const VERDICT = { approve: ['ok', '✓', '承認', 'この内容でよい'], request_changes: ['ng', '✎', '変更を依頼', '直してほしい点がある'], comment: ['neutral', '…', 'コメントのみ', '判定はしない'] };
  const CSTATE = { pending: ['warn', '✎', '未提出'], unresolved: ['ng', '!', '未解決'], resolved: ['ok', '✓', '解決済み'] };
  const VIEWED = ['ok', '✓', '確認済み'];
  const CHANGED = ['warn', '⟳', '前回の確認から変更あり'];
  const MISSING = ['neutral', '?', '一覧に無い行'];
  const ANS = { yes: ['ok', '✓', '問題なし'], no: ['ng', '✖', '直す必要あり'], na: ['neutral', '–', '対象外'] };
  const SEV_HELP = { Blocker: 'このままでは進められない', Major: '直すべき', Minor: '直したほうがよい' };
  const KIND_LABEL = { claims: 'クレーム', token_types: 'トークン', hops: '経路', catalog_answers: 'カタログへの回答', issuance_profile: '発行方式の項目' };
  const KIND_VIEW = { claims: 'claim', token_types: 'token', hops: 'hop' };
  const ROWS_KEY = { claims: 'claims', token_types: 'token_types', hops: 'hops', catalog_answers: 'answers' };
  let QBY = new Map(); let ROLE = new Map();
  function index() { QBY = new Map(R.questions.map((x) => [x.id, x])); ROLE = new Map(R.roles.map((x) => [x.id, x])); }
  if (R) index();
  const MISMATCH = '目的と仕組みの不一致';

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

  function dump(data, version) { return F.dump(data, version || st.version || (R && R.template_version) || '0.0.0'); }
  const versionOf = F.versionOf;

  // ------------------------------------------------------------ state
  // file: the records (review.yaml, claims-review/2); me: the name of the reviewer who records in this tab (self-declared);
  // bar: a review is going on (the bar with the progress and 「レビューを提出」 is shown); shown: the rows listed on the
  // rows screen (kept while the reviewer works, so that a row does not vanish when it is marked); openRow: the row that
  // is unfolded; form: the comment being written ({anchor, column, question, general, edit})
  const st = { file: emptyFile(''), savedText: '', me: null, designRel: '', open: false, timer: null, focus: null, version: null,
    bar: false, filter: null, kind: '', shown: null, openRow: null, form: null, allQ: false, justSubmitted: false, migrated: false };
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
    const others = st.file.reviews.filter((r) => r !== m && (Object.keys(r.answers).length || Object.keys(r.viewed).length || r.comments.length));
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
  function changed(rerender, keepUpdated) {
    const m = mine();
    if (m && !keepUpdated) m.updated = now();
    autosaveSoon();
    refreshCounts();
    renderBar();
    if (rerender) { H.keepScroll(); P.render(); restoreFocus(); }
  }
  function restoreFocus() { if (st.focus) { const el = document.getElementById(st.focus); if (el) el.focus(); st.focus = null; } }
  function sid(anchor) { return String(anchor).replace(/[^A-Za-z0-9_-]/g, '_'); }

  // ------------------------------------------------------------ rows: anchors, hashes, the viewed marks
  // 「確認済み」 is the reviewer's own mark that they have looked at this content of the row (like Viewed of a pull request
  // review): it is not an approval. It is bound to the hash of the row; when the row changes, the mark does not count
  // any more and the row says 「前回の確認から変更あり」. The approval is one verdict for the whole review, at the submission.
  const hmemo = new WeakMap();
  function hashOfRow(anchor, row) {
    if (row && typeof row === 'object') { if (!hmemo.has(row)) hmemo.set(row, CE.rowHash(anchor)); return hmemo.get(row); }
    return CE.rowHash(anchor);
  }
  function rowHash(anchor) { const r = CE.rowOf(anchor); return r ? hashOfRow(anchor, r.row) : null; }
  function rowsNow() { return CE.anchors().map((a) => ({ anchor: a.anchor, kind: a.kind, id: a.id, row: a.row, hash: hashOfRow(a.anchor, a.row) })); }
  function anchorSet() { return new Set(CE.anchors().map((a) => a.anchor)); }
  function markState(rec, anchor, set) {
    const cur = rowHash(anchor);
    if (!(set || anchorSet()).has(anchor) || cur === null) return 'missing';
    return cur === rec.hash ? 'current' : 'changed';
  }
  function myMark(anchor) { const m = mine(); return m && own(m.viewed, anchor) ? m.viewed[anchor] : null; }
  function isViewed(anchor, set) { const r = myMark(anchor); return !!r && markState(r, anchor, set) === 'current'; }
  const SNAPSHOT_MAX = 200000;
  function setViewed(anchor, on) {
    const m = mine();
    if (!m) return false;
    if (!on) { delete m.viewed[anchor]; changed(false); return true; }
    const hash = rowHash(anchor);
    if (!hash) return false;
    const rec = flagEdit({ hash, at: now(), reviewer_kind: m.reviewer.kind });
    // the row as it is now (its RFC 8785 text, whose SHA-256 is the hash): the next review shows old and new side by side
    const snap = CE.rowJcs(anchor);
    if (snap !== null && snap.length <= SNAPSHOT_MAX) rec.snapshot = snap;
    m.viewed[anchor] = rec;
    changed(false);
    return true;
  }
  function progress() {
    const m = mine();
    const all = rowsNow();
    let viewed = 0; let chg = 0;
    all.forEach((a) => { const r = m && own(m.viewed, a.anchor) ? m.viewed[a.anchor] : null; if (!r || a.hash === null) return; if (r.hash === a.hash) viewed++; else chg++; });
    const cs = m ? m.comments : [];
    return { total: all.length, viewed, changed: chg, comments: cs.length, pending: cs.filter((c) => c.state === 'pending').length,
      unresolved: cs.filter((c) => c.state === 'unresolved').length };
  }
  // the badge of a mark names the reviewer; an LLM's mark says that no person has checked it
  function markBadge(rec, anchor, rv, set) {
    const s = markState(rec, anchor, set);
    const kind = rec.reviewer_kind || rv.reviewer.kind;
    const who = `（${rv.reviewer.name}` + (kind === 'llm' ? '・LLM、人による点検は未実施' : '・名前は自己申告') + '）';
    const x = s === 'current' ? VIEWED : s === 'changed' ? CHANGED : MISSING;
    return h('span', { class: 'rvb', 'data-review-for': anchor, 'data-review-state': s === 'current' ? 'viewed' : s, 'data-review-by': rv.reviewer.name, 'data-review-kind': kind },
      badge(x, x[2] + who, s === 'changed' ? `${rec.at} に確認した後で、行の内容が変わった` : rec.at));
  }
  function commentsOf(anchor) {
    const out = [];
    visible().forEach((rv) => rv.comments.forEach((c) => { if ((c.anchors || []).includes(anchor)) out.push([rv, c]); }));
    return out;
  }
  function allComments() { const out = []; visible().forEach((rv) => rv.comments.forEach((c) => out.push([rv, c]))); return out; }
  function nextId(rv) { for (let i = 1; ; i++) { const id = 'C' + String(i).padStart(2, '0'); if (!rv.comments.some((c) => c.id === id)) return id; } }
  function colLabel(kind, key) { const c = H.columns(kind).find((x) => x.key === key); return c ? c.label : key; }
  function kindOf(anchor) { return String(anchor).slice(0, String(anchor).indexOf(':')); }
  function idOf(anchor) { return String(anchor).slice(String(anchor).indexOf(':') + 1); }
  function rowTitle(a) {
    const r = a.row;
    if (a.kind === 'claims' && isObj(r)) return [h('strong', null, (r.namespace || '') + (r.name || a.id)), ' ', h('span', { class: 'muted' }, '(' + a.id + ')')];
    return h('strong', null, a.id);
  }

  // the badges on every row of every screen, and the panel of the detail screens (registerRowPanel of #49)
  CE.registerRowPanel((anchor, row, kind, where) => {
    if (!st.open || !R) return null;
    const m = mine();
    const set = anchorSet();
    const cs = commentsOf(anchor);
    const marks = visible().filter((rv) => own(rv.viewed, anchor));
    if (marks.some((rv) => rv !== m)) noteViewing();
    if (where !== 'detail') {
      if (!marks.length && !cs.length) return null;
      const open = cs.filter(([, c]) => c.state !== 'resolved').length;
      const list = cs.map(([, c]) => `${c.id} ${c.severity} ${c.content}`).join('／');
      return h('span', { class: 'codes rvbadges' }, marks.map((rv) => markBadge(rv.viewed[anchor], anchor, rv, set)),
        cs.length ? [badge(['info', '!', ''], `コメント ${cs.length}` + (open ? `（未解決・未提出 ${open}）` : ''), list), h('span', { class: 'vh' }, '：' + list)] : null);
    }
    return h('section', { class: 'rv-panel', 'aria-labelledby': 'rvp-h', 'data-review-panel': anchor },
      h('h2', { id: 'rvp-h' }, 'この行のレビュー'),
      m ? rowHead(anchor, set, true) : h('p', null, '「確認済み」の印とコメントを付けるには、上の「レビューを開始」を押します。'),
      rowBody(anchor, true, set));
  });
  // the head of a row: the 「確認済み」 checkbox and what stands out (changed since the last look, comments)
  function rowHead(anchor, set, detail) {
    const m = mine();
    const mark = myMark(anchor);
    const s = mark ? markState(mark, anchor, set) : null;
    const hash = rowHash(anchor);
    const cid = 'rv-v-' + sid(anchor);
    const cb = h('input', { type: 'checkbox', id: cid, 'data-viewed': anchor, checked: s === 'current' ? true : null, disabled: m && hash ? null : true,
      onchange: (e) => {
        st.focus = cid;
        if (e.target.checked && st.openRow === anchor) st.openRow = null;  // a row marked as viewed folds
        if (e.target.checked && st.form && st.form.anchor === anchor) st.form = null;
        setViewed(anchor, e.target.checked);
        changed(true, true);
      } });
    return h('span', { class: 'rv-viewed', 'data-row-state': s === 'current' ? 'viewed' : s || 'open' },
      h('label', { class: 'chk', for: cid, title: '「確認済み」は、この内容を見たという自分の印です（承認ではありません）。行の内容が変わると外れます。' }, cb, ' 確認済み'),
      s === 'changed' ? [' ', h('span', { 'data-changed': anchor }, badge(CHANGED))] : null,
      s === 'missing' ? [' ', badge(MISSING)] : null,
      !hash && detail ? h('span', { class: 'muted small' }, ' この行は内容を照合できないので、印を付けられません（ID が 2 行以上にある、など）。') : null);
  }
  // old and new, side by side, of the columns that changed since the reviewer's mark
  function changeBlock(anchor, mark) {
    const r = CE.rowOf(anchor);
    const box = h('div', { class: 'note warn rv-changed', 'data-changed-row': anchor },
      h('p', null, h('strong', null, '前回の確認から変更あり。'), `${mark.at} に確認した後で、この行の内容が変わりました。変わった所を見て、よければ「確認済み」を付け直します。`));
    let old = null; let have = false;
    if (typeof mark.snapshot === 'string') { try { old = JSON.parse(mark.snapshot); have = true; } catch (e) { have = false; } }
    if (!have || !r) {
      box.append(h('p', { class: 'muted small', 'data-no-snapshot': '1' }, '前回の値は、この記録にありません（古い形の記録か、値を含めずに提出した記録）。行の全体を見直してください。'));
      return box;
    }
    const kind = r.kind; const cur = r.row;
    const val = (v, k) => (H.columns(kind).length && k ? H.columnValue(kind, k, v) : H.value(v));
    const none = () => h('span', { class: 'muted' }, '（無し）');
    let keys;
    if (isObj(old) && isObj(cur)) {
      const order = H.columns(kind).map((c) => c.key);
      keys = Array.from(new Set(Object.keys(old).concat(Object.keys(cur)))).filter((k) => own(old, k) !== own(cur, k) || CE.canonicalJson(old[k]) !== CE.canonicalJson(cur[k]))
        .sort((a, b) => (order.indexOf(a) < 0 ? 999 : order.indexOf(a)) - (order.indexOf(b) < 0 ? 999 : order.indexOf(b)));
    } else keys = [null];
    box.append(h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'row-diff' }, h('caption', null, `変わった列 ${keys.length} 件（前回の確認 → 今）`),
      h('thead', null, h('tr', null, ['列', '前回の確認のとき', '今'].map((x) => h('th', { scope: 'col' }, x)))),
      h('tbody', null, keys.map((k) => h('tr', { 'data-diff-col': k || '' }, h('th', { scope: 'row' }, k ? [colLabel(kind, k), ' ', h('span', { class: 'muted small' }, k)] : '値'),
        h('td', { class: 'rv-old' }, k === null ? val(old) : own(old, k) ? val(old[k], k) : none()), h('td', { class: 'rv-new' }, k === null ? val(cur) : own(cur, k) ? val(cur[k], k) : none())))))));
    return box;
  }
  // the filled columns of a row, each with a button that adds a comment on that column
  function valuesBlock(anchor) {
    const r = CE.rowOf(anchor);
    if (!r) return null;
    const m = mine();
    const kind = r.kind; const row = r.row;
    const cols = H.columns(kind);
    if (!isObj(row)) return h('div', { class: 'cols rv-values' }, h('div', { class: 'col' }, h('div', { class: 'ch' }, code(r.id)), h('div', { class: 'cv' }, H.value(row))));
    const known = new Set(cols.map((c) => c.key));
    const keys = cols.filter((c) => own(row, c.key)).map((c) => [c.key, c.label]).concat(Object.keys(row).filter((k) => !known.has(k)).map((k) => [k, k]));
    const empty = cols.filter((c) => !own(row, c.key)).length;
    const qn = (k) => applicable().filter((x) => x.see_refs.some((s) => s.kind === 'registry' && s.path === kind && s.anchor === k)).length;
    return [h('div', { class: 'cols rv-values' }, keys.map(([k, label]) => {
      const n = known.has(k) ? qn(k) : 0;
      return h('div', { class: 'col', 'data-col': k }, h('div', { class: 'ch' }, h('span', { class: 'lbl' }, label), label !== k ? h('span', { class: 'key muted' }, k) : null,
        h('span', { class: 'rv-coltools small' }, h('button', { type: 'button', class: 'link', 'data-add-comment-col': anchor + '#' + k, 'aria-label': `${label} にコメントを追加`, disabled: m ? null : true,
          onclick: () => openForm({ anchor, column: k }) }, 'コメント'),
        n ? [' ・ ', h('a', { href: P.route('review', 'col') + '/' + kind + '/' + encodeURIComponent(k), title: 'この欄を見る確認事項' }, `確認事項 ${n}`)] : null)),
      h('div', { class: 'cv' }, known.has(k) ? H.columnValue(kind, k, row[k]) : H.value(row[k]),
        m && st.form && st.form.anchor === anchor && st.form.column === k ? commentForm(st.form) : null));
    })), empty ? h('p', { class: 'muted small' }, `未記入の欄 ${empty} 件は、ここには出していません（詳細の画面で見られます）。`) : null];
  }
  function rowBody(anchor, detail, set) {
    const m = mine();
    const mark = myMark(anchor);
    const out = [];
    if (mark && markState(mark, anchor, set) === 'changed') out.push(changeBlock(anchor, mark));
    if (!detail) out.push(valuesBlock(anchor));
    const others = visible().filter((rv) => rv !== m && own(rv.viewed, anchor));
    if (others.length) out.push(h('p', { class: 'small' }, 'ほかのレビュアー：', h('span', { class: 'codes' }, others.map((rv) => markBadge(rv.viewed[anchor], anchor, rv, set)))));
    if (hiding() && hiddenCount()) out.push(h('p', { class: 'muted small', 'data-hidden-others': String(hiddenCount()) }, `独立レビュー：提出するまで、ほかのレビュアー ${hiddenCount()} 人の記録を隠しています。`));
    const cs = commentsOf(anchor);
    if (cs.length) out.push(h('div', { class: 'rv-comments', 'data-comments-for': anchor }, cs.map(([rv, c]) => commentItem(rv, c))));
    const inCol = !detail && st.form && st.form.column && isObj((CE.rowOf(anchor) || {}).row) && own(CE.rowOf(anchor).row, st.form.column);
    if (st.form && st.form.anchor === anchor && m && !inCol) out.push(commentForm(st.form));
    else {
      out.push(h('p', { class: 'buttons' },
        h('button', { type: 'button', id: 'rv-addc-' + sid(anchor), 'data-add-comment': anchor, disabled: m ? null : true, onclick: () => openForm({ anchor }) }, 'コメントを追加'),
        detail ? null : (KIND_VIEW[kindOf(anchor)] ? h('a', { href: rowHref(anchor) }, '詳細の画面') : null), H.revealLink(kindOf(anchor), idOf(anchor)),
        detail ? null : h('button', { type: 'button', class: 'link', 'data-next-from': anchor, onclick: () => nextUnviewed(anchor) }, '次の未確認へ →')));
    }
    const rel = relatedQuestions(anchor);
    if (rel) out.push(rel);
    return out;
  }

  // ------------------------------------------------------------ comments (kept as 未提出 until the review is submitted)
  function openForm(f) {
    if (!mine()) { openStart(); return; }
    st.form = f;
    if (f.anchor && !f.general) st.openRow = f.anchor;
    H.keepScroll(); P.render();
    const el = $('#rvc-content');
    if (el) { el.focus(); if (el.scrollIntoView) el.scrollIntoView({ block: 'nearest' }); }
  }
  function commentItem(rv, c, withRow) {
    const m = mine();
    const a0 = (c.anchors || [])[0];
    const old = !!(c.hash && a0 && rowHash(a0) !== c.hash);
    const act = (label, attrs, fn) => h('button', Object.assign({ type: 'button', onclick: fn }, attrs), label);
    return h('article', { class: 'rv-c', 'data-comment': c.id, 'data-comment-state': c.state, 'data-comment-by': rv.reviewer.name },
      h('p', { class: 'rv-c-head' }, badge(CSTATE[c.state]), ' ', code(c.id), ' ', h('span', { class: 'chip', title: SEV_HELP[c.severity] || '' }, c.severity), ' ', h('span', { class: 'chip' }, c.kind),
        c.column && a0 ? [' ', h('span', { class: 'chip' }, '列：' + colLabel(kindOf(a0), c.column))] : null,
        ' ', h('span', { class: 'muted small' }, rv.reviewer.name + (rv.reviewer.kind === 'llm' ? '（LLM、人による点検は未実施）' : '')),
        old ? [' ', badge(['neutral', '⟲', '古い内容へのコメント'], null, 'コメントを書いた後で、行の内容が変わりました')] : null,
        withRow ? [' ', (c.anchors || []).length ? h('span', { class: 'codes' }, c.anchors.map(rowLink)) : h('span', { class: 'muted small' }, H.inline(c.location))] : null),
      h('p', { class: 'rv-c-body' }, H.inline(c.content)),
      c.suggestion ? h('p', { class: 'small' }, '修正の提案：', code(c.suggestion)) : null,
      c.kind === MISMATCH && c.confused_question ? h('p', { class: 'small muted' }, '取り違えた問い：', H.inline(c.confused_question)) : null,
      c.verdict_reason ? h('p', { class: 'small muted' }, '採否の理由：', c.verdict_reason) : null,
      rv === m ? h('p', { class: 'buttons small' },
        c.state === 'pending' ? [act('直す', { 'data-edit-comment': c.id }, () => openForm({ anchor: a0, column: c.column, question: (c.questions || [])[0], general: !a0 && !(c.questions || []).length, edit: c.id })),
          act('消す', { 'data-delete-comment': c.id }, () => CE.ask('コメントを消す', `未提出のコメント ${c.id} を消します。`, [['delete', '消す'], ['cancel', 'やめる']]).then((x) => { if (x === 'delete') { m.comments.splice(m.comments.indexOf(c), 1); changed(true); } }))]
          : c.state === 'unresolved' ? act('解決済みにする', { 'data-resolve': c.id }, () => { c.state = 'resolved'; c.resolved_at = now(); flagEdit(c); changed(true); })
            : act('未解決に戻す', { 'data-unresolve': c.id }, () => { c.state = 'unresolved'; delete c.resolved_at; flagEdit(c); changed(true); })) : null);
  }
  // The form asks only what the report needs: the text, the severity and the kind (report_template.md 2.). Where it came
  // from (origin) follows from where it was written, and the author's decision on it (採用・却下・保留) starts as 保留.
  function commentForm(f) {
    const m = mine();
    const ex = f.edit ? m.comments.find((c) => c.id === f.edit) : null;
    const v = ex || {};
    const content = h('textarea', { id: 'rvc-content', rows: '3', 'aria-describedby': 'rvc-hint' }, v.content || f.content || '');
    const sev = h('select', { id: 'rvc-severity' }, R.report.severities.map((x) => h('option', { value: x, selected: x === (v.severity || 'Major') ? true : null }, `${x}（${SEV_HELP[x] || ''}）`)));
    const confused = h('input', { type: 'text', id: 'rvc-confused', value: v.confused_question || '' });
    const cbox = h('label', { class: 'wide', id: 'rvc-confused-box', hidden: (v.kind || '') !== MISMATCH ? true : null }, '取り違えた問い（どの問いに、別の問いのための仕組みで答えているか）', confused);
    const kind = h('select', { id: 'rvc-kind', onchange: (e) => { cbox.hidden = e.target.value !== MISMATCH; } }, R.report.kinds.map((x) => h('option', { value: x, selected: x === (v.kind || R.report.kinds[0]) ? true : null }, x)));
    const sugg = f.column ? h('input', { type: 'text', id: 'rvc-suggestion', value: v.suggestion || '' }) : null;
    const msg = h('p', { class: 'err', id: 'rvc-msg', role: 'alert' });
    const where = f.anchor ? (f.column ? `${f.anchor} の「${colLabel(kindOf(f.anchor), f.column)}」` : f.anchor) : f.question ? `確認事項 ${f.question}` : '設計書の全体';
    return h('form', { class: 'filters rv-cform', id: 'rv-comment-form', 'data-comment-form': f.anchor || f.question || 'general', onsubmit: (e) => {
      e.preventDefault();
      const text = content.value.trim();
      if (!text) { msg.textContent = 'コメントの文を書いてください。'; content.focus(); return; }
      if (kind.value === MISMATCH && !confused.value.trim()) { msg.textContent = '種別が「目的と仕組みの不一致」のときは、取り違えた問いを書いてください。'; confused.focus(); return; }
      const c = ex || { id: nextId(m), state: 'pending', verdict: '保留' };
      c.location = ex ? ex.location : (f.anchor ? idOf(f.anchor) + (f.column ? ` の ${f.column}` : '') : f.question ? f.question : '設計書の全体');
      c.content = text; c.severity = sev.value; c.kind = kind.value;
      if (!ex) c.origin = m.reviewer.kind === 'llm' ? 'LLM' : f.question ? '観点' : 'テンプレート項目';
      if (kind.value === MISMATCH) c.confused_question = confused.value.trim(); else delete c.confused_question;
      if (f.anchor) { c.anchors = [f.anchor]; const hh = rowHash(f.anchor); if (hh) c.hash = hh; }
      if (f.column) c.column = f.column;
      if (f.question) c.questions = [f.question];
      if (sugg && sugg.value.trim()) c.suggestion = sugg.value.trim(); else delete c.suggestion;
      c.at = now();
      flagEdit(c);
      if (!ex) m.comments.push(c);
      st.form = null;
      st.focus = f.anchor ? 'rv-addc-' + sid(f.anchor) : null;
      changed(true);
    } },
    h('h3', { class: 'wide' }, ex ? `コメント ${ex.id} を直す` : 'コメントを追加', ' ', h('span', { class: 'muted small' }, where)),
    h('label', { class: 'wide' }, 'コメント', content),
    h('label', null, '重大度', sev), h('label', null, '種別', kind), cbox,
    sugg ? h('label', { class: 'wide' }, '修正の提案（任意。この列をどう書けばよいか）', sugg) : null,
    h('p', { class: 'wide muted small', id: 'rvc-hint' }, '提出するまでは「未提出」で、自分にだけ見え、直せます。重大度と種別は、レポートに載ります。'),
    h('div', { class: 'wide buttons' }, msg, h('button', { type: 'submit', class: 'primary', id: 'rvc-save' }, ex ? '直した内容で保存' : 'コメントを追加（未提出）'),
      h('button', { type: 'button', id: 'rvc-cancel', onclick: () => { st.form = null; st.focus = f.anchor ? 'rv-addc-' + sid(f.anchor) : null; H.keepScroll(); P.render(); restoreFocus(); } }, 'やめる')));
  }

  // ------------------------------------------------------------ 確認事項: the questions that apply to this design
  // The questions come from data/review.js (perspectives.md). Which of them a reviewer answers is data too
  // (templates/review/triage.yaml, #56): the class of each question (A the checks, B the author, C a person's judgement,
  // D an expert), and for class C a priority, the unit it is read with (row / hop / design), the conditions under which
  // it is shown (show_when: properties of the design) and a plain wording (ask). The properties are read from the
  // design (designTraits); a condition that cannot be read carries a question (ask) and is asked of the reviewer, the
  // answer kept in review.yaml (traits).
  // the words of the screens (#67) in texts that come from the templates (the templates keep their own words)
  const UI_TERMS = [['値の出どころ', '値の元データ'], ['出どころ', '元データ'], ['台帳の行', 'クレーム'], ['台帳', 'クレーム一覧'], ['ホップ', '経路'], ['観点書', '確認事項の一覧'], ['観点', '確認事項'],
    ['縮小 Lite', 'Lite'], ['lint の', '自動の検査の'], ['lint', '自動の検査']];
  function ui(s) { let t = String(s === null || s === undefined ? '' : s); UI_TERMS.forEach(([a, b]) => { t = t.split(a).join(b); }); return t; }
  // The traits of the open design that the conditions name. The same reading as traits() of tools/review_triage.py (#56).
  function designTraits() {
    const reg = H.registry() || {};
    const adopted = (rows) => (Array.isArray(rows) ? rows : []).filter((r) => isObj(r) && r.decision !== '却下');
    const claims = adopted(reg.claims && reg.claims.claims); const types = adopted(reg.token_types && reg.token_types.token_types);
    const hops = (reg.hops && Array.isArray(reg.hops.hops) ? reg.hops.hops : []).filter(isObj);
    const lite = (reg.catalog_answers && reg.catalog_answers.lite_criteria) || {};
    const names = new Set(claims.map((c) => String(c.name))); const kinds = new Set(hops.map((x) => x.kind));
    const has = (v) => (Array.isArray(v) ? v.length > 0 : isObj(v) ? Object.keys(v).length > 0 : !!v);
    const t = new Set(['always']);
    if (claims.some((c) => has(c.namespace) || (!has(c.registered_ref) && (c.usage === 'authz' || c.usage === 'identifier')))) t.add('org_claims');
    if (claims.some((c) => c.pii_category && c.pii_category !== '該当なし')) t.add('pii');
    const iss = new Set(); types.forEach((x) => (Array.isArray(x.issuers) ? x.issuers : []).forEach((i) => { if (isObj(i) && i.iss) iss.add(String(i.iss)); }));
    if (iss.size > 1 || claims.some((c) => has(c.upstream_issuer))) t.add('multi_idp');
    if (kinds.has('exchange') || kinds.has('reissue')) t.add('exchange');
    if (names.has('act') || names.has('may_act') || types.some((x) => x.max_delegation_depth !== undefined && x.max_delegation_depth !== null)) t.add('delegation');
    if (names.has('authorization_details') || hops.some((x) => has(x.authorization_details))) t.add('approval');
    // the author's answer decides; tenant_binding is read only when there is no answer
    const answered = isObj(lite.multitenant) && typeof lite.multitenant.answer === 'boolean';
    if (answered ? lite.multitenant.answer === true : types.some((x) => has(x.tenant_binding))) t.add('multitenant');
    if (kinds.has('db_connection')) t.add('data_layer');
    if (names.has('acr') || names.has('amr') || names.has('auth_time')) t.add('auth_context');
    if (types.some((x) => x.sender_constraint === 'dpop' || x.sender_constraint === 'mtls')) t.add('sender_constrained');
    if (types.some((x) => (x.kind === 'access_token' || x.kind === 'internal_token') && (x.sender_constraint === undefined || x.sender_constraint === null || x.sender_constraint === 'none'))) t.add('sender_declined');
    if (types.some((x) => has(x.long_running)) || kinds.has('broker_connection')) t.add('long_running');
    return t;
  }
  const TRAIT_FILES = { org_claims: ['claims.yaml'], pii: ['claims.yaml'], multi_idp: ['claims.yaml', 'token_types.yaml'], exchange: ['hops.yaml'], delegation: ['claims.yaml', 'token_types.yaml'],
    approval: ['claims.yaml', 'hops.yaml'], multitenant: ['catalog_answers.yaml'], data_layer: ['hops.yaml'], auth_context: ['claims.yaml'], sender_constrained: ['token_types.yaml'],
    sender_declined: ['token_types.yaml'], long_running: ['token_types.yaml', 'hops.yaml'] };
  function conditions() { return (R.checklist && R.checklist.conditions) || []; }
  // {id: true | false | null}: read from the design, or (a condition with `ask`) answered by the reviewer; null = not known yet
  function traits() {
    const read = designTraits();
    const m = mine();
    const out = { always: true };
    // a property that does not hold while a file it is read from is not open cannot be read (null): its questions stay,
    // with a note (when the data name the files of a condition: needs; else the table below)
    const open = new Set(CE.state().files);
    conditions().forEach((c) => {
      if (c.ask) { out[c.id] = m && m.traits && own(m.traits, c.id) ? m.traits[c.id] : null; return; }
      const needs = c.needs || TRAIT_FILES[c.id] || [];
      out[c.id] = read.has(c.id) ? true : needs.some((n) => !open.has(n)) ? null : false;
    });
    return out;
  }
  const CLASS_WHY = { A: '自動の検査で確かめる（画面の下の「問題」に出る。レビュアーは答えない）', B: '書き手が、提出の前に自分で確かめる', D: '専門家に回す基準で見る（レポートの画面の「専門家に回した項目」）' };
  // -> {show, why}: why it is shown (the properties that hold) or why it is not
  function triage(x, tr, warned) {
    const cls = x.triage && x.triage !== 'all' ? x.triage : 'C';
    if (cls !== 'C') return { show: false, why: CLASS_WHY[cls] || cls };
    const label = (id) => { const c = conditions().find((y) => y.id === id); return c ? ui(c.label) : id; };
    const byLint = (x.show_on_lint || []).filter((r) => warned.has(r));
    if (byLint.length) return { show: true, why: `「問題」に、規則 ${byLint.join('・')} の警告が出ているため` };
    const short = (R.checklist && R.checklist.short) || {};
    if (Array.isArray(short.priorities) && x.priority !== undefined && x.priority !== null && !short.priorities.includes(x.priority)) {
      return { show: false, why: `優先 ${x.priority}（当てはまる設計が限られる、またはほかの問いに答える中で見える）` };
    }
    const when = (x.show_when || []).length ? x.show_when : ['always'];
    const hit = when.filter((id) => tr[id] === true);
    if (hit.length) return { show: true, why: hit.includes('always') ? 'どの設計書でも確かめる' : hit.map(label).join('・') + '（設計書から読んだ性質）' };
    const unknown = when.filter((id) => tr[id] === null || tr[id] === undefined);
    if (unknown.length) return { show: true, why: unknown.map(label).join('・') + ' かどうかを、まだ読めない（分からない）ため' };
    return { show: false, why: 'この設計書に当てはまらない（' + when.map(label).join('・') + ' に当たらない）' };
  }
  function triageAll() {
    const tr = traits();
    const warned = new Set(CE.diagnostics().filter((d) => d.source === 'claim_lint' && d.severity !== 'info').map((d) => d.rule));
    return R.questions.map((x) => [x, triage(x, tr, warned)]);
  }
  function applicable() { return triageAll().filter(([, t]) => t.show).map(([x]) => x); }
  function answerOf(rv, qid) { return rv && rv.answers[qid] ? rv.answers[qid].answer : ''; }
  function relatedQuestions(anchor) {
    const kind = kindOf(anchor);
    const m = mine();
    const unit = { claims: 'row', hops: 'hop' }[kind];
    const qs = applicable().filter((x) => (x.unit ? x.unit === unit : x.see_refs.some((s) => s.kind === 'registry' && s.path === kind)));
    if (!qs.length) return null;
    const open = qs.filter((x) => !answerOf(m, x.id)).length;
    // a plain <details> (not a fold kept in the URL): the questions are rendered when it is first opened
    const box = h('details', { class: 'rv-related' }, h('summary', { 'data-related-questions': String(qs.length) }, `この行を見ながら確かめる確認事項 ${qs.length} 件` + (m ? `（未回答 ${open} 件）` : '')));
    box.addEventListener('toggle', () => {
      if (!box.open || box.dataset.filled) return;
      box.dataset.filled = '1';
      add(box, [h('p', { class: 'muted small' }, '確認事項の答えは、設計書の全体に 1 つです（行ごとではありません）。'), qs.map((x) => questionItem(x, m, null, 'r-' + sid(anchor) + '-'))]);
    });
    return box;
  }
  function viewChecklist(query) {
    const q = new URLSearchParams(query || '');
    const m = mine();
    const tr = traits();
    const all = triageAll();
    const shownN = all.filter(([, t]) => t.show).length;
    const total = all.length;
    const reasons = new Map();
    all.forEach(([, t]) => { if (!t.show) reasons.set(t.why, (reasons.get(t.why) || 0) + 1); });
    const ansSel = h('select', { id: 'rv-f-ans' }, h('option', { value: '' }, 'すべて'), h('option', { value: 'open' }, '未回答'), Object.keys(ANS).map((k) => h('option', { value: k }, ANS[k][2])));
    const text = h('input', { type: 'search', id: 'rv-f-q', placeholder: '問いの文・ID で探す' });
    ansSel.value = q.get('ans') || ''; text.value = q.get('q') || '';
    if (q.get('all') === '1') st.allQ = true;
    const count = h('p', { class: 'count', id: 'rv-count', 'aria-live': 'polite' });
    const list = h('div', { id: 'rv-questions' });
    const items = [];
    const units = (R.checklist && R.checklist.units) || null;
    const groups = units && all.some(([x]) => x.unit) ? Object.keys(units).map((k) => ({ id: k, title: ui(units[k]), has: (x) => x.unit === k })).concat([{ id: 'other', title: 'そのほか（レビュアーが答えない問いを含む）', has: (x) => !x.unit }])
      : R.stages.map((s) => ({ id: s.id, title: s.title, has: (x) => x.stage === s.id }));
    groups.forEach((s) => {
      const qs = all.filter(([x, t]) => s.has(x) && (st.allQ || t.show)).sort((a, b) => (a[0].priority || 9) - (b[0].priority || 9));
      if (!qs.length) return;
      const sec = h('section', { class: 'rv-stage', 'data-stage': s.id }, h('h2', null, s.title));
      qs.forEach(([x, t]) => { const el = questionItem(x, m, t); items.push([x, el]); sec.append(el); });
      list.append(sec);
    });
    function apply() {
      const t = text.value.trim().toLowerCase();
      let n = 0;
      items.forEach(([x, el]) => {
        const a = answerOf(mine(), x.id);
        const ok = (!ansSel.value || (ansSel.value === 'open' ? !a : a === ansSel.value)) && (!t || (x.id + ' ' + x.text + ' ' + (x.ask || '') + ' ' + x.see).toLowerCase().includes(t));
        el.hidden = !ok;
        if (ok) n++;
      });
      list.querySelectorAll('.rv-stage').forEach((sec) => { sec.hidden = !sec.querySelector('.rv-q:not([hidden])'); });
      const done = m ? items.filter(([x]) => answerOf(m, x.id)).length : 0;
      count.textContent = `${n} 件を表示` + (m ? `（回答済み ${done} / ${items.length} 件）` : '');
      const params = {};
      if (ansSel.value) params.ans = ansSel.value;
      if (t) params.q = text.value.trim();
      if (st.allQ) params.all = '1';
      const hash = P.route('review', 'checklist', params);
      if (location.hash !== hash) history.replaceState(null, '', hash);
    }
    setTimeout(apply, 0);
    const conds = conditions().filter((c) => c.id !== 'always');
    const auto = conds.filter((c) => !c.ask);
    const asked = conds.filter((c) => c.ask);
    const mark = (v) => (v === true ? badge(['info', '●', '当たる']) : v === false ? badge(['neutral', '○', '当たらない']) : badge(['warn', '?', '読めない'], null, 'この性質を読むファイルを、まだ開いていない（または、まだ答えていない）。関係する問いは、出したままにします'));
    const prompts = ((R.checklist && R.checklist.open_prompts) || []).filter((p) => (p.show_when || ['always']).some((c) => tr[c] === true));
    return [h('h1', { tabindex: '-1' }, '確認事項'),
      h('p', { class: 'lead' }, 'この設計書に当てはまり、人が判断しないと決まらない問いだけを出します。問いは、どれも「はい」なら問題なしの向きです。自動の検査で確かめられることは、画面の下の「問題」に出ます。'),
      h('section', { class: 'rv-traits', id: 'rv-traits', 'aria-labelledby': 'rv-traits-h' }, h('h2', { id: 'rv-traits-h' }, 'この設計書の性質'),
        h('p', { class: 'muted small' }, '設計書から読んだもの（違っていたら、設計書を直します）：'),
        h('ul', { class: 'rv-traitlist' }, auto.map((t) => h('li', { 'data-trait': t.id, 'data-trait-value': String(tr[t.id]), title: t.read ? ui(t.read) : null }, mark(tr[t.id]), ' ', ui(t.label)))),
        asked.length ? [h('p', { class: 'muted small', id: 'rv-asked', 'data-asked': String(asked.length) }, `設計書からは読めないこと（${asked.length} 問。答えで、出す問いが変わります）：`),
          asked.map((t) => h('fieldset', { class: 'rv-ans rv-ask', 'data-trait': t.id, 'data-trait-value': String(tr[t.id]), disabled: m ? null : true }, h('legend', null, ui(t.ask)),
            [[null, 'まだ分からない'], [true, 'はい'], [false, 'いいえ']].map(([v, label]) => h('label', null, h('input', { type: 'radio', name: 'rv-trait-' + t.id, value: String(v), checked: tr[t.id] === v ? true : null, 'data-trait-answer': t.id,
              onchange: () => { const me = mine(); if (!me) return; me.traits = me.traits || {}; if (v === null) delete me.traits[t.id]; else me.traits[t.id] = v; if (!Object.keys(me.traits).length) delete me.traits; st.focus = null; changed(true); } }), ' ', label)))),
          m ? null : h('p', { class: 'muted small' }, '答えるには、上の「レビューを開始」を押します。')] : null),
      h('p', { id: 'rv-q-count', class: 'count', 'data-shown': String(shownN), 'data-total': String(total) }, `全 ${total} 件のうち ${shownN} 件を表示`, st.allQ ? '（いまは、全件を表示しています）' : '', ' ',
        h('button', { type: 'button', id: 'rv-q-all', 'aria-pressed': st.allQ ? 'true' : 'false', onclick: () => { st.allQ = !st.allQ; st.focus = 'rv-q-all'; history.replaceState(null, '', P.route('review', 'checklist', st.allQ ? { all: '1' } : null)); H.keepScroll(); P.render(); restoreFocus(); } }, st.allQ ? '当てはまる問いだけに戻す' : `すべての確認事項を見る（${total} 件）`)),
      reasons.size ? h('details', { id: 'rv-q-why' }, h('summary', null, `出していない ${total - shownN} 件の理由`),
        h('table', { 'data-table': 'hidden-reasons' }, h('thead', null, h('tr', null, h('th', { scope: 'col' }, '理由'), h('th', { scope: 'col', class: 'num' }, '件数'))),
          h('tbody', null, Array.from(reasons.entries()).sort((a, b) => b[1] - a[1]).map(([why, n]) => h('tr', null, h('td', null, why), h('td', { class: 'num' }, String(n))))))) : null,
      R.checklist.provisional ? h('p', { class: 'muted small', id: 'rv-q-provisional' }, R.checklist.provisional) : null,
      m ? null : h('p', { class: 'note warn' }, '答えを記録するには、上の「レビューを開始」を押して、名前（自己申告）を決めます。'),
      h('form', { class: 'filters', role: 'search', onsubmit: (e) => e.preventDefault(), oninput: apply, onchange: apply }, h('label', null, '自分の答え', ansSel), h('label', { class: 'wide' }, '検索', text)),
      count, list,
      prompts.length ? h('section', { id: 'rv-prompts', 'data-prompts': String(prompts.length) }, h('h2', null, `答えの決まっていない問い ${prompts.length} 件`),
        h('p', { class: 'muted small' }, '「はい」「いいえ」では答えません。設計書を辿って、気づいたことをコメントにします。'),
        h('ul', null, prompts.map((p) => h('li', { 'data-prompt': p.id }, H.inlineRepo(ui(p.ask)), ' ',
          h('button', { type: 'button', class: 'link', disabled: m ? null : true, onclick: () => { location.hash = P.route('review', 'comments'); openForm({ general: true }); } }, '気づいたことをコメントにする'))))) : null];
  }
  function questionItem(x, m, t, prefix) {
    const p = prefix || '';
    const a = answerOf(m, x.id);
    const memo = h('textarea', { id: p + 'rv-memo-' + x.id, rows: '1', class: 'rv-memo', 'aria-label': `${x.id} の理由（1 行）`, disabled: m ? null : true }, m && m.answers[x.id] && m.answers[x.id].memo ? m.answers[x.id].memo : '');
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
    const name = p + 'rv-a-' + x.id;
    const others = visible().filter((rv) => rv !== m && rv.answers[x.id]);
    const el = h('article', { class: 'rv-q', id: p + 'q-' + x.id, 'data-q': x.id, 'data-answer': a, 'data-shown': t ? (t.show ? '1' : '0') : null },
      h('h3', null, H.inlineRepo(ui(x.ask || x.text)), ' ', h('span', { class: 'muted small' }, x.id), x.priority ? h('span', { class: 'chip', title: ((R.checklist.priorities || {})[String(x.priority)]) || '' }, '優先 ' + x.priority) : null),
      x.hint ? h('details', { class: 'rv-hint small' }, h('summary', null, '補足'), h('p', { class: 'muted' }, H.inlineRepo(ui(x.hint)))) : null,
      t ? h('p', { class: 'rv-why small', 'data-why': '1' }, h('span', { class: 'muted' }, t.show ? 'なぜ出たか：' : '出していない理由：'), t.why) : null,
      h('p', { class: 'rv-see' }, h('span', { class: 'muted' }, '見る場所：'), x.see_refs.map((r, i) => [i ? '、' : '', seeLink(r)])),
      h('details', null, h('summary', null, '「いいえ」のとき・関連する資料・根拠'), h('dl', { class: 'obj' }, x.ask ? [h('dt', null, '元の問い'), h('dd', null, H.inlineRepo(ui(x.text)))] : null, h('dt', null, '「いいえ」なら'), h('dd', null, H.inlineRepo(ui(x.no))), h('dt', null, '関連'), h('dd', null, H.inlineRepo(ui(x.links))),
        h('dt', null, '根拠'), h('dd', null, H.inlineRepo(x.evidence)), h('dt', null, '原文'), h('dd', null, h('a', { href: x.url }, x.id + ' の原文')))),
      h('fieldset', { class: 'rv-ans', disabled: m ? null : true }, h('legend', null, m ? `答え（${m.reviewer.name}）` : '答え'),
        [['', '未回答']].concat(Object.keys(ANS).map((k) => [k, ANS[k][2]])).map(([v, label]) => h('label', null,
          h('input', { type: 'radio', name, value: v, checked: a === v ? true : null, 'data-answer-for': x.id, onchange: () => setAns(v) }), ' ', v ? ANS[v][1] + ' ' : '', label)),
        h('label', { class: 'rv-memo-l', for: p + 'rv-memo-' + x.id }, '理由（「直す必要あり」「対象外」では書く）'), memo,
        h('button', { type: 'button', class: 'rv-findbtn', hidden: a !== 'no' ? true : null, onclick: () => { location.hash = P.route('review', 'checklist', { q: x.id }); openForm({ question: x.id, content: memo.value.trim() }); } }, 'コメントにする')),
      !p && st.form && st.form.question === x.id && !st.form.anchor && m ? commentForm(st.form) : null,
      others.length ? h('ul', { class: 'rv-others small' }, others.map((rv) => h('li', null, badge(ANS[rv.answers[x.id].answer]), ' ', rv.reviewer.name, rv.answers[x.id].memo ? '：' + rv.answers[x.id].memo : ''))) : null);
    return el;
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
    CE.saveWarning('このブラウザに自動保存したレビューの記録が残っていて、どれを使うかが決まっていないので、レビューの記録の自動保存を止めています（上書きしない）。「提出と記録」の画面で選んでください。', 'review');
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
    st.bar = !!st.me; st.shown = null; st.openRow = null; st.form = null;
    if (st.bar) CE.setMode('review');
  }
  // a review.yaml text -> {data} or {error}; checked with templates/review/review.schema.json and the questions
  function parseReview(text, name) {
    let v;
    try { v = CE.parseYaml(text); } catch (e) { return { error: `${name}：YAML の誤り（${e.message}）` }; }
    const v1 = F.isV1(v);
    const errs = CE.validate(v1 ? 'review_v1' : 'review', v);
    if (errs.length) return { error: `${name}：レビューの記録の形に合わない（` + errs.slice(0, 4).map((e) => `${e.path}：${e.message}`).join('、') + (errs.length > 4 ? ` ほか ${errs.length - 4} 件` : '') + '）' };
    if (v1) v = F.migrate(v);
    const bad = [];
    const names = v.reviews.map((r) => r.reviewer.name);
    names.forEach((n, i) => { if (names.indexOf(n) !== i) bad.push(`レビュアー ${n} が 2 回ある`); });
    v.reviews.forEach((rv) => {
      Object.keys(rv.answers).forEach((q) => { if (!QBY.has(q)) bad.push(`${rv.reviewer.name}：問い ${q} は確認事項に無い`); });
      const ids = rv.comments.map((f) => f.id);
      ids.forEach((x, i) => { if (ids.indexOf(x) !== i) bad.push(`${rv.reviewer.name}：コメント ${x} が 2 つある`); });
    });
    if (bad.length) return { error: `${name}：` + bad.slice(0, 4).join('、') };
    // a v1 text is the same records in the old form: nothing of it is lost by reading it, so the migrated text counts as
    // written out (the old file is still where it was)
    return { data: v, migrated: v1, text: v1 ? dump(v, versionOf(text) || undefined) : String(text).replace(/\r\n/g, '\n') };
  }
  function companionOpen(info) {
    st.opening = true;
    loadData().then(() => companionOpen2(info), (e) => { st.opening = false; if (e.message !== 'stale') CE.ask('レビューを使えません', String(e.message || e), [['ok', '閉じる']]); });
  }
  function companionOpen2(info) {
    st.open = true;
    st.designRel = info.designRel;
    st.migrated = false; st.allQ = false; st.justSubmitted = false; st.lastKey = undefined; st.filter = null; st.kind = '';
    const empty = emptyFile(info.designRel);
    setFile(empty, dump(empty), null);
    const extra = (info.extras || []).filter((e) => /^review\.ya?ml$/.test(e.name));
    let p = Promise.resolve();
    if (extra.length) {
      const r = parseReview(extra[0].text, extra[0].name);
      if (r.error) CE.ask('review.yaml を読めません', r.error + '。レビューの記録は空で始めます（ファイルはそのまま）。', [['ok', '閉じる']]);
      else if (r.data.design !== info.designRel) {
        p = CE.ask('review.yaml の設計書が違います', `review.yaml は ${r.data.design} の記録です。開いた設計書は ${info.designRel} です。`, [['load', 'この設計書の記録として読む'], ['skip', '読まない']])
          .then((c) => { if (c === 'load') { r.data.design = info.designRel; st.migrated = !!r.migrated; setFile(r.data, '', null); } });
      } else { st.migrated = !!r.migrated; setFile(r.data, r.text, null, extra[0].text); }
    }
    p.then(() => {
      st.slotHold = null;
      CE.saveWarning(null, 'review');
      let sv = null;
      try { const raw = localStorage.getItem(slotKey()); sv = raw ? JSON.parse(raw) : null; } catch (e) { sv = { savedAt: '不明', text: '\u0000' }; }
      if (sv && typeof sv.text !== 'string') sv = { savedAt: sv.savedAt || '不明', text: '\u0000' };
      if (sv && sv.text !== dump(st.file)) return askSlot(sv);
      return null;
    }).then(() => { st.opening = false; renderBar(); CE.publish(); if (info.startReview && !mine()) openStart(); });
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
        return CE.ask('同じレビュアーの記録が 2 つあります', `「${rv.reviewer.name}」の記録が、開いている記録と読み込む記録で違います（確認済みの行 ${Object.keys(st.file.reviews[i].viewed).length}・${Object.keys(rv.viewed).length}、コメント ${st.file.reviews[i].comments.length}・${rv.comments.length}、確認事項の答え ${Object.keys(st.file.reviews[i].answers).length}・${Object.keys(rv.answers).length}）。`,
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
      xs.forEach((x) => { const r = parseReview(x.text, x.name); if (r.error) errs.push(r.error); else { ok.push([x, r.data, r.text]); if (r.migrated) st.migrated = true; } });
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
          if (wasClean && use.length === 1 && use[0][1].design === st.designRel) { st.savedText = use[0][2]; st.version = versionOf(use[0][2]) || st.version; }
          st.file.design = st.designRel;
          if (errs.length) CE.ask('読めなかった review.yaml', errs.join('\n'), [['ok', '閉じる']]);
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
    // the design changed (an edit, a check that finished): the progress of the bar follows the rows as they are now
    onPublish: () => { if (st.open && !st.opening) renderBar(); },
    onOpen: companionOpen,
    onClose: () => { st.slotHold = null; CE.saveWarning(null, 'review'); st.open = false; st.file = emptyFile(''); st.savedText = dump(st.file); st.me = null; st.bar = false; st.form = null; st.shown = null; st.openRow = null; renderBar(); },
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
      : CE.ask('既にあるレビュアーの記録で続ける', `「${name}」の記録（${target && target.submitted ? '提出済み' : '未提出'}）で続けます。名前は自己申告なので、この操作で、ほかの人の記録を自分のものとして直せてしまいます。${typed ? '同じ名前を打ちました。' : ''}本人のときだけ続けてください。`,
        [['go', '続ける'], ['cancel', 'やめる']]).then((c) => c === 'go');
    return p.then((ok) => { if (ok) st.me = name; changed(true); return ok; });
  }
  // 「レビューを開始」: one dialog. The name (self-declared), a person or an LLM, a review.yaml to read in if there is
  // one, and whether the review is independent. Then the rows to review, with the bar on top.
  function openStart() {
    if (st.opening) return;
    if (!st.open || !R) { CE.ask('レビューを開始できません', '設計書を開いてから、もう一度「レビューを開始」を押してください。', [['ok', '閉じる']]); return; }
    if ($('#rv-start')) return;
    const m = mine();
    const names = st.file.reviews.map((r) => r.reviewer.name);
    const name = h('input', { type: 'text', id: 'rv-name', autocomplete: 'off', 'aria-describedby': 'rv-name-hint', value: m ? m.reviewer.name : '' });
    const model = h('input', { type: 'text', id: 'rv-model', placeholder: 'モデルの名前とセッション', value: m && m.reviewer.model ? m.reviewer.model : '' });
    const mbox = h('label', { id: 'rv-model-box', hidden: m && m.reviewer.kind === 'llm' ? null : true }, 'モデル（LLM のとき）', model);
    const radio = (v, label) => h('label', null, h('input', { type: 'radio', name: 'rv-kind', id: 'rv-kind-' + v, value: v, checked: (m ? m.reviewer.kind : 'human') === v ? true : null, onchange: () => { mbox.hidden = v !== 'llm'; } }), ' ', label);
    const ind = h('input', { type: 'checkbox', id: 'rv-independent', checked: st.file.independent ? true : null });
    const imp = h('input', { type: 'file', id: 'rv-import', multiple: true, accept: '.yaml,.yml', class: 'vh', tabindex: '-1', 'aria-hidden': 'true' });
    const msg = h('p', { class: 'err', id: 'rv-start-msg', role: 'alert' });
    const d = h('dialog', { class: 'confirm rv-start', id: 'rv-start', 'aria-labelledby': 'rv-start-h' });
    imp.addEventListener('change', () => importFiles(imp.files).then(() => { d.close('reopen'); }));
    const form = h('form', { method: 'dialog', onsubmit: (e) => {
      e.preventDefault();
      const n = name.value.trim();
      if (!n) { msg.textContent = '名前を入れてください（自己申告です。あだ名でもかまいません）。'; name.focus(); return; }
      const kind = form.querySelector('input[name="rv-kind"]:checked').value;
      d.close('go');
      startAs(n, kind, model.value.trim(), ind.checked);
    } },
    h('h2', { id: 'rv-start-h' }, 'レビューを開始'),
    h('p', { class: 'muted' }, '行を 1 つずつ見て「確認済み」の印を付け、気づいた点はコメントにためます。最後に 1 回だけ、総評と判定を付けて「レビューを提出」します。'),
    h('label', { class: 'rv-field' }, '名前（自己申告）', name),
    h('p', { class: 'muted small', id: 'rv-name-hint' }, 'ログインは無く、名前は記録に書くだけです。本当の承認は、GitHub の pull request のレビューで行います。'),
    h('fieldset', { class: 'rv-ans' }, h('legend', null, 'レビューするのは'), radio('human', '人'), radio('llm', 'LLM')), mbox,
    h('p', { id: 'rv-start-records', 'data-reviewers': String(names.length) }, names.length
      ? `読み込んだ記録：レビュアー ${names.length} 人（${names.join('・')}）。同じ名前で始めると、その記録の続き（再レビュー）になります。`
      : '前のレビューの記録（review.yaml）があれば、読み込んでから始めます。無ければ、このまま始めます。', ' ',
    h('button', { type: 'button', id: 'rv-import-btn', onclick: () => imp.click() }, 'review.yaml を読み込む'), imp),
    st.migrated ? h('p', { class: 'muted small', id: 'rv-migrated' }, '古い形の記録を読み込み、新しい形に直しました（行ごとの判定は「確認済み」の印に、指摘はコメントになります）。') : null,
    h('p', null, h('label', { class: 'chk' }, ind, ' 独立レビューにする（提出するまで、ほかの人の記録を画面に出さない）')),
    msg,
    h('p', { class: 'buttons' }, h('button', { type: 'submit', class: 'primary', id: 'rv-start-go' }, 'レビューを開始'), h('button', { type: 'button', id: 'rv-start-cancel', onclick: () => d.close('cancel') }, 'やめる')));
    d.append(form);
    d.addEventListener('close', () => { const v = d.returnValue; d.remove(); if (v === 'reopen') openStart(); });
    document.body.append(d);
    d.showModal();
    name.focus();
  }
  function startAs(n, kind, model, independent) {
    const begin = () => {
      st.bar = true; st.shown = null; st.filter = null; st.openRow = null; st.form = null;
      CE.setMode('review');
      CE.setPane('editor', false);  // a review is reading: the YAML editor is folded (「▶ エディター」 opens it again)
      changed(false, true);
      const target = P.route('review');
      if (location.hash === target) P.render(); else location.hash = target;
      setTimeout(() => { const h1 = $('#main h1'); if (h1) h1.focus(); }, 0);
      return true;
    };
    // the independent review is a setting of the records; taking it off before submitting is leaving it (recorded)
    const setInd = () => {
      if (independent && !st.file.independent) { st.file.independent = true; const me = mine(); if (me && !me.submitted && !me.independence) me.independence = { mode: 'kept' }; return Promise.resolve(true); }
      if (!independent && st.file.independent) return breakIndependence('独立レビューの設定を外した').then((ok) => { if (ok) st.file.independent = false; return true; });
      return Promise.resolve(true);
    };
    const existing = st.file.reviews.find((r) => r.reviewer.name === n);
    if (existing) {
      const p = st.me === n ? Promise.resolve(true) : switchTo(n, true);
      return p.then((ok) => (ok && st.me === n ? setInd().then(begin) : false));
    }
    const make = () => {
      const rv = { reviewer: { name: n, kind }, self_declared: true, started: now(), submitted: null,
        materials: { perspectives: R.template_version, report_template: (R.versions || {})['templates/review/report_template.md'] || R.template_version, questions: R.questions.length },
        answers: {}, viewed: {}, comments: [], submissions: [] };
      if (model && kind === 'llm') rv.reviewer.model = model;
      st.file.reviews.push(rv);
      st.me = n;
      return setInd().then(() => { if (st.file.independent) rv.independence = { mode: 'kept' }; return begin(); });
    };
    // a new reviewer while I have not submitted: the new name would see nothing of mine, but I leave my review
    if (locked()) return breakIndependence(`新しいレビュアー「${n}」に切り替えた`).then((ok) => (ok ? make() : false));
    return make();
  }
  function leave() { st.bar = false; st.form = null; CE.setMode('edit'); CE.setPane('editor', true); renderBar(); P.render(); const b = $('#btn-start-review'); if (b) b.focus(); }
  // the bar that stays on top while a review is going on: the progress and the one button that submits
  function renderBar() {
    const bar = $('#review-bar'); const btn = $('#btn-start-review');
    if (!bar) return;
    const m = mine();
    const on = st.open && st.bar && !!m && !!R;
    bar.hidden = !on;
    document.body.classList.toggle('reviewing', on);
    if (btn) { btn.hidden = on; btn.textContent = st.open && m ? 'レビューを続ける' : 'レビューを開始'; }
    bar.textContent = '';
    if (!on) return;
    const p = progress();
    const sub = m.submissions.length;
    const dirty = !sub || p.pending > 0 || (m.updated && String(m.updated) > String(m.submitted));
    const state = !sub ? '未提出' : dirty ? `提出済み（${String(m.submitted).slice(0, 10)}）の後に、未提出の変更あり` : `提出済み（${String(m.submitted).slice(0, 10)}）`;
    add(bar, [h('span', { class: 'rb-who' }, sub && !dirty ? 'レビュー（提出済み）：' : 'レビュー中：', h('strong', null, m.reviewer.name), m.reviewer.kind === 'llm' ? '（LLM）' : ''),
      h('span', { id: 'rv-progress', class: 'rb-progress', role: 'status', 'data-viewed': String(p.viewed), 'data-total': String(p.total), 'data-comments': String(p.comments), 'data-pending': String(p.pending),
        'data-changed': String(p.changed), 'data-submitted': sub && !dirty ? '1' : '0' },
      `確認済み ${p.viewed} / ${p.total} 行・コメント ${p.comments} 件・${state}`, p.changed ? `・前回の確認から変更あり ${p.changed} 行` : ''),
      h('progress', { max: String(p.total || 1), value: String(p.viewed), 'aria-label': '確認済みの行の割合' }),
      h('span', { class: 'rb-actions' }, h('button', { type: 'button', id: 'rv-next', onclick: () => nextUnviewed(st.openRow) }, '次の未確認へ'),
        h('button', { type: 'button', class: sub && !dirty ? null : 'primary', id: 'rv-submit', title: sub && !dirty ? '提出の後に変えたことは、ありません。もう一度提出することもできます' : null, onclick: openSubmit }, 'レビューを提出'),
        h('button', { type: 'button', class: 'link small', id: 'rv-leave', title: '記録は残ります。「レビューを続ける」で戻れます', onclick: leave }, '中断'))]);
  }
  // 「次の未確認へ」: the next row after `from` (in the order of the list) that is not marked, unfolded and focused
  function nextUnviewed(from) {
    const set = anchorSet();
    const order = (st.shown && st.shown.length ? st.shown.filter((a) => set.has(a)) : []).concat(CE.anchors().map((a) => a.anchor));
    const uniq = Array.from(new Set(order));
    const i = from ? uniq.indexOf(from) : -1;
    const next = uniq.slice(i + 1).concat(uniq.slice(0, i + 1)).find((a) => a !== from && rowHash(a) && !isViewed(a, set));
    const say = $('#rv-progress');
    if (!next) { if (say) say.append(' ― 未確認の行はありません'); return null; }
    st.openRow = next; st.form = null;
    if (st.shown && !st.shown.includes(next)) st.shown.push(next);
    const go = () => { const el = document.getElementById('rv-t-' + sid(next)); if (el) { el.focus(); const art = el.closest('.rv-row'); if (art && art.scrollIntoView) art.scrollIntoView({ block: 'start' }); } };
    const target = P.route('review');
    if (P.parseHash().parts.join('/') === 'review') { H.keepScroll(); P.render(); go(); } else { location.hash = target; setTimeout(go, 0); }
    return next;
  }
  function rowLink(anchor) {
    const kind = kindOf(anchor); const id = idOf(anchor);
    if (KIND_VIEW[kind]) return h('a', { href: P.route(KIND_VIEW[kind], id) }, anchor);
    if (kind === 'catalog_answers') return h('a', { href: P.route('catalog') }, anchor);
    if (kind === 'issuance_profile') return h('a', { href: P.route('profile') }, anchor);
    return code(anchor);
  }
  function rowHref(anchor) {
    const kind = kindOf(anchor);
    if (KIND_VIEW[kind]) return P.route(KIND_VIEW[kind], idOf(anchor));
    return kind === 'catalog_answers' ? P.route('catalog') : kind === 'issuance_profile' ? P.route('profile') : P.route('review');
  }

  // ---- the rows to review (the first screen of a review)
  const FILTERS = { todo: '未確認', comments: 'コメントあり', all: 'すべての行' };
  function viewRows(query) {
    const q = new URLSearchParams(query || '');
    const m = mine();
    const out = [h('h1', { tabindex: '-1' }, 'レビューする行')];
    if (!m) {
      const n = st.file.reviews.length;
      out.push(h('p', { class: 'lead' }, '設計書の行（クレーム・トークン・経路など）を 1 つずつ見て「確認済み」にし、気づいた点をコメントにためて、最後に 1 回だけ提出します。'),
        h('p', null, h('button', { type: 'button', class: 'primary', id: 'rv-begin', onclick: openStart }, 'レビューを開始')),
        n ? h('p', { class: 'muted', 'data-reviewers': String(n) }, `この設計書には、レビュアー ${n} 人の記録があります。` + (hiding() ? '独立レビューなので、始めて提出するまで中身は出しません。' : ''), ' ', h('a', { href: P.route('review', 'record') }, '提出と記録を見る')) : null,
        selfDeclared());
      return out;
    }
    const set = anchorSet();
    const rows = rowsNow();
    const re = m.submissions.length > 0;  // a review after a submission: by default only what changed since
    if (q.get('filter') && FILTERS[q.get('filter')]) st.filter = q.get('filter');
    if (!st.filter) st.filter = re ? 'todo' : 'all';
    if (q.get('kind') !== null && q.get('kind') !== st.kind) { st.kind = q.get('kind') || ''; st.shown = null; }
    const has = (a) => commentsOf(a.anchor).length > 0;
    const todo = (a) => a.hash !== null && !(own(m.viewed, a.anchor) && m.viewed[a.anchor].hash === a.hash);
    const match = (a) => (st.filter === 'all' || (st.filter === 'todo' ? todo(a) : has(a))) && (!st.kind || a.kind === st.kind);
    const key = st.filter + '|' + st.kind;
    if (!st.shown || st.shownKey !== key) { st.shown = rows.filter(match).map((a) => a.anchor); st.shownKey = key; }
    else rows.forEach((a) => { if (match(a) && !st.shown.includes(a.anchor)) st.shown.push(a.anchor); });  // rows marked on this screen stay listed
    const shown = new Set(st.shown);
    const list = rows.filter((a) => shown.has(a.anchor));
    const nTodo = rows.filter(todo).length;
    const label = (k) => (k === 'todo' && re ? '前回のレビュー以降の変更' : FILTERS[k]) + (k === 'todo' ? `（${nTodo}）` : k === 'all' ? `（${rows.length}）` : `（${rows.filter(has).length}）`);
    const setFilter = (k) => { st.filter = k; st.shown = null; st.focus = 'rv-flt-' + k; history.replaceState(null, '', P.route('review', null, Object.assign({ filter: k }, st.kind ? { kind: st.kind } : {}))); P.render(); restoreFocus(); };
    const kindSel = h('select', { id: 'rv-r-kind', 'aria-label': '行の種類', onchange: (e) => { st.kind = e.target.value; st.shown = null; st.focus = 'rv-r-kind'; H.keepScroll(); P.render(); restoreFocus(); } },
      h('option', { value: '' }, 'すべての種類'), Object.keys(KIND_LABEL).filter((k) => rows.some((a) => a.kind === k)).map((k) => h('option', { value: k, selected: st.kind === k ? true : null }, `${KIND_LABEL[k]}（${rows.filter((a) => a.kind === k).length}）`)));
    const last = re ? m.submissions[m.submissions.length - 1] : null;
    out.push(h('p', { class: 'lead' }, re
      ? `前回の提出（${last.at}、${VERDICT[last.verdict][2]}）の後に内容が変わった行と、まだ確認していない行を出しています。変わった列は、前回と今を並べます。`
      : '行を開いて内容を見て、「確認済み」を付けます（自分の印で、承認ではありません）。気づいた点は「コメントを追加」でためます。全部を見なくても提出できます（見た行だけが記録に残ります）。どこから見るか迷ったら、「コメントあり」の行や、種類を「クレーム」に絞って上から見ます。'),
    h('div', { class: 'rv-filter', role: 'group', 'aria-label': '表示する行', id: 'rv-filter', 'data-filter': st.filter, 'data-rereview': re ? '1' : '0' },
      Object.keys(FILTERS).map((k) => h('button', { type: 'button', id: 'rv-flt-' + k, 'data-filter-btn': k, 'aria-pressed': st.filter === k ? 'true' : 'false', onclick: () => setFilter(k) }, label(k))), kindSel));
    // the comments that are not resolved come first in a review after a submission
    const open = allComments().filter(([, c]) => c.state === 'unresolved');
    if (re && open.length) {
      out.push(h('section', { id: 'rv-unresolved', class: 'rv-unresolved', 'aria-labelledby': 'rv-unresolved-h' }, h('h2', { id: 'rv-unresolved-h' }, `未解決のコメント ${open.length} 件`),
        h('p', { class: 'muted small' }, '直っていれば「解決済みにする」を押します。残すなら、そのままにします。'), open.map(([rv, c]) => commentItem(rv, c, true))));
    }
    const gone = Object.keys(m.viewed).filter((a) => !set.has(a) || rowHash(a) === null);
    out.push(h('p', { class: 'count', id: 'rv-r-count', 'aria-live': 'polite', 'data-rows': String(list.length) }, `${list.length} 行を表示（全 ${rows.length} 行）`));
    if (!list.length) {
      out.push(h('p', { class: 'note', id: 'rv-r-empty' }, st.filter === 'todo' ? (re ? '前回のレビューの後に変わった行は、ありません。' : '未確認の行は、ありません。') + '「レビューを提出」で提出できます。' : '当てはまる行がありません。'));
    }
    let kind = null;
    list.forEach((a) => {
      if (a.kind !== kind) { kind = a.kind; out.push(h('h2', { class: 'rv-kind-h', 'data-kind': kind }, KIND_LABEL[kind] || kind)); }
      out.push(rowCard(a, set));
    });
    if (gone.length) {
      out.push(h('h2', null, '一覧から消えた行'), h('p', { class: 'muted' }, '確認済みの印があるのに、いまの設計書に無い行です（行が消えたか、ID が変わった）。印は消さずに残しています。'),
        h('ul', { id: 'rv-gone' }, gone.map((a) => h('li', { 'data-missing': a }, code(a), `（${m.viewed[a].at} に確認）`))));
    }
    return out;
  }
  function rowCard(a, set) {
    const anchor = a.anchor;
    const open = st.openRow === anchor;
    const cs = commentsOf(anchor);
    const mark = myMark(anchor);
    const s = mark ? markState(mark, anchor, set) : 'open';
    const diags = CE.diagnostics().filter((d) => d.anchorKind === a.kind && d.anchorId === a.id);
    const errs = diags.filter((d) => d.severity === 'error').length; const warns = diags.filter((d) => d.severity === 'warn').length;
    const tid = 'rv-t-' + sid(anchor); const bid = 'rv-b-' + sid(anchor);
    return h('article', { class: 'rv-row' + (open ? ' open' : ''), id: 'rv-row-' + sid(anchor), 'data-anchor': anchor, 'data-row-state': s === 'current' ? 'viewed' : s, 'data-open': open ? '1' : '0' },
      h('div', { class: 'rv-row-head' }, rowHead(anchor, set, false),
        h('button', { type: 'button', class: 'rv-row-title', id: tid, 'aria-expanded': open ? 'true' : 'false', 'aria-controls': bid, 'data-toggle-row': anchor,
          onclick: () => { st.openRow = open ? null : anchor; st.form = null; st.focus = tid; H.keepScroll(); P.render(); restoreFocus(); } },
        h('span', { 'aria-hidden': 'true' }, open ? '▼ ' : '▶ '), rowTitle(a)),
        h('span', { class: 'codes' }, cs.length ? badge(['info', '!', ''], `コメント ${cs.length}`) : null,
          errs || warns ? h('button', { type: 'button', class: 'link small', 'data-row-problems': anchor, title: 'この行の問題を、下の問題の一覧で見る', onclick: () => { if (!CE.problems.open()) CE.problems.toggle(true); } }, `問題 ${errs + warns}`) : null)),
      h('div', { class: 'rv-row-body', id: bid, hidden: open ? null : true }, open ? rowBody(anchor, false, set) : null));
  }

  // ---- every comment
  function viewComments() {
    const m = mine();
    const all = allComments();
    const order = { unresolved: 0, pending: 1, resolved: 2 };
    all.sort((x, y) => order[x[1].state] - order[y[1].state]);
    const n = (s) => all.filter(([, c]) => c.state === s).length;
    return [h('h1', { tabindex: '-1' }, 'コメント'),
      h('p', { class: 'lead' }, `人が書いたコメントです（自動の検査の結果は、画面の下の「問題」）。未提出 ${n('pending')} 件・未解決 ${n('unresolved')} 件・解決済み ${n('resolved')} 件。`),
      hiding() && hiddenCount() ? h('p', { class: 'note', 'data-hidden-others': String(hiddenCount()) }, `独立レビュー：提出するまで、ほかのレビュアー ${hiddenCount()} 人のコメントを隠しています。`) : null,
      m ? (st.form && st.form.general ? commentForm(st.form) : h('p', null, h('button', { type: 'button', id: 'rv-c-general', onclick: () => openForm({ general: true }) }, '行に付かないコメントを追加'),
        h('span', { class: 'muted small' }, ' 行や列へのコメントは、「レビューする行」か、行の詳細の画面で付けます。'))) : h('p', { class: 'note warn' }, 'コメントを付けるには、上の「レビューを開始」を押します。'),
      all.length ? h('div', { id: 'rv-comment-list', 'data-comments': String(all.length) }, all.map(([rv, c]) => commentItem(rv, c, true))) : h('p', { class: 'muted', id: 'rv-comment-list', 'data-comments': '0' }, 'コメントはありません。')];
  }

  // ---- 「レビューを提出」: once, with a summary and one verdict for the whole review
  function openSubmit() {
    const m = mine();
    if (!m || $('#rv-submit-dialog')) return;
    const p = progress();
    const open = p.pending + p.unresolved;
    const def = open ? 'request_changes' : p.viewed === p.total && p.total ? 'approve' : 'comment';
    const warn = h('p', { class: 'note warn', id: 'rv-submit-warn', hidden: true });
    const setWarn = (v) => {
      const left = p.total - p.viewed;
      const t = v === 'approve' && left ? `未確認の行が ${left} 行あります。承認は、確認済みの ${p.viewed} 行の今の内容にだけ結びつきます。` : v === 'approve' && open ? `未解決・未提出のコメントが ${open} 件あります。それでも承認にしますか。` : '';
      warn.hidden = !t; warn.textContent = t;
    };
    const summary = h('textarea', { id: 'rv-summary', rows: '4' });
    const snaps = h('input', { type: 'checkbox', id: 'rv-snapshots', checked: true });
    const d = h('dialog', { class: 'confirm rv-submit', id: 'rv-submit-dialog', 'aria-labelledby': 'rv-submit-h' });
    const form = h('form', { method: 'dialog', onsubmit: (e) => {
      e.preventDefault();
      const v = form.querySelector('input[name="rv-verdict"]:checked').value;
      d.close('go');
      submit(v, summary.value.trim(), snaps.checked);
    } },
    h('h2', { id: 'rv-submit-h' }, 'レビューを提出'),
    h('p', { id: 'rv-submit-counts', 'data-default': def }, `確認済み ${p.viewed} / ${p.total} 行。未提出のコメント ${p.pending} 件（提出すると「未解決」になり、ほかの人に見えます）。未解決のコメント ${p.unresolved} 件。`),
    h('label', { class: 'rv-field', for: 'rv-summary' }, '総評（全体について、ひとこと）'), summary,
    h('fieldset', { class: 'rv-verdict' }, h('legend', null, '判定（レビュー全体に 1 つ）'),
      Object.keys(VERDICT).map((k) => h('label', null, h('input', { type: 'radio', name: 'rv-verdict', id: 'rv-verdict-' + k, value: k, checked: k === def ? true : null, onchange: () => setWarn(k) }), ' ',
        h('strong', null, VERDICT[k][2]), '：', VERDICT[k][3]))),
    warn,
    h('p', { class: 'small' }, h('label', { class: 'chk' }, snaps, ' 確認した行の今の値も記録に含める（次のレビューで、変わった列の前と後を並べるため。記録のファイルは大きくなる）')),
    h('p', { class: 'muted small' }, '提出すると、判定と、確認済みの各行の内容の照合用の値を記録します。その後に行が変わると、その行は「前回の確認から変更あり」になります。'),
    h('p', { class: 'buttons' }, h('button', { type: 'submit', class: 'primary', id: 'rv-submit-go' }, '提出する'), h('button', { type: 'button', id: 'rv-submit-cancel', onclick: () => d.close('cancel') }, 'やめる')));
    d.append(form);
    d.addEventListener('close', () => d.remove());
    document.body.append(d);
    d.showModal();
    setWarn(def);
    summary.focus();
  }
  function submit(verdict, summary, keepSnapshots) {
    const m = mine();
    if (!m) return null;
    const at = now();
    const viewed = {};
    rowsNow().forEach((a) => { const r = own(m.viewed, a.anchor) ? m.viewed[a.anchor] : null; if (r && a.hash !== null && r.hash === a.hash) viewed[a.anchor] = r.hash; });
    if (!keepSnapshots) Object.keys(m.viewed).forEach((a) => { delete m.viewed[a].snapshot; });
    const ids = m.comments.filter((c) => c.state === 'pending').map((c) => { c.state = 'unresolved'; return c.id; });
    const sub = { at, verdict, viewed };
    if (summary) sub.summary = summary;
    if (ids.length) sub.comments = ids;
    sub.unresolved = m.comments.filter((c) => c.state === 'unresolved').length;
    m.submissions.push(sub);
    m.submitted = at; m.updated = at;
    st.justSubmitted = true; st.form = null; st.shown = null;
    changed(false, true);
    const target = P.route('review', 'record');
    if (location.hash === target) P.render(); else location.hash = target;
    setTimeout(() => { const el = $('#rv-next-steps'); if (el) el.focus(); }, 0);
    return sub;
  }

  // ---- 提出と記録: what to do after the submission, the submissions, reading and writing review.yaml
  function viewRecord() {
    const m = mine();
    const vis = visible();
    const set = anchorSet();
    const imp = h('input', { type: 'file', id: 'rv-import', multiple: true, accept: '.yaml,.yml', class: 'vh', tabindex: '-1', 'aria-hidden': 'true' });
    imp.addEventListener('change', () => importFiles(imp.files));
    const subs = [];
    vis.forEach((rv) => rv.submissions.forEach((s, i) => subs.push([rv, s, i])));
    const lastApprove = (rv) => { const s = rv.submissions[rv.submissions.length - 1]; return s && s.verdict === 'approve' ? s : null; };
    const staleApproval = (rv) => { const s = lastApprove(rv); return !!s && Object.keys(s.viewed).some((a) => rowHash(a) !== s.viewed[a]); };
    return [h('h1', { tabindex: '-1' }, '提出と記録'),
      m && m.submitted ? h('section', { class: 'note', id: 'rv-next-steps', tabindex: '-1', 'aria-labelledby': 'rv-next-h', 'data-just': st.justSubmitted ? '1' : '0' },
        h('h2', { id: 'rv-next-h' }, st.justSubmitted ? 'レビューを提出しました。次にやること' : '提出の後にやること'),
        h('ol', null, h('li', null, '記録のファイルを書き出す：', h('button', { type: 'button', class: 'primary', id: 'rv-export-next', onclick: () => exportAll() }, 'review.yaml を書き出す')),
          h('li', null, '書き出した review.yaml を、設計書と同じフォルダーに置き、その設計書の pull request にコミットする。'),
          h('li', null, 'GitHub の pull request でも、同じ判定でレビューする（ここでの名前は自己申告で、本当の承認は pull request のレビュー）。')),
        h('p', { class: 'muted small' }, '設計書が直されたら、直した設計書と、この review.yaml を一緒に開いて「レビューを開始」を押します。変わった行だけが出ます。')) : null,
      st.migrated ? h('p', { class: 'note', id: 'rv-migrated-note' }, '古い形（claims-review/1）の記録を読み込み、新しい形に直しました。行ごとの判定（承認・修正を求める・保留）は「確認済み」の印になり、元の判定は記録に残しています。書き出すと、新しい形のファイルになります。') : null,
      h('h2', null, '提出の記録'),
      subs.length ? h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'submissions' }, h('thead', null, h('tr', null, ['レビュアー（自己申告）', '日時', '判定', '総評', '確認済みの行', 'コメント'].map((x) => h('th', { scope: 'col' }, x)))),
        h('tbody', null, subs.map(([rv, s, i]) => h('tr', { 'data-submission-by': rv.reviewer.name, 'data-verdict': s.verdict },
          h('th', { scope: 'row' }, rv.reviewer.name, rv.reviewer.kind === 'llm' ? '（LLM）' : ''), h('td', null, s.at), h('td', null, badge(VERDICT[s.verdict]),
            i === rv.submissions.length - 1 && s.verdict === 'approve' && staleApproval(rv) ? [' ', h('span', { 'data-stale-approval': '1' }, badge(['warn', '⟳', '古い承認（内容が変更されました）']))] : null,
            s.migrated ? h('div', { class: 'muted small' }, '古い形の記録から移した') : null),
          h('td', null, s.summary || '—'), h('td', { class: 'num' }, String(Object.keys(s.viewed).length)), h('td', { class: 'num' }, String((s.comments || []).length))))))) : h('p', { class: 'muted', id: 'rv-no-submission' }, 'まだ提出していません。'),
      h('h2', null, 'レビュアーごとの記録'),
      hiding() && hiddenCount() ? h('p', { class: 'note', id: 'rv-hidden', 'data-hidden-others': String(hiddenCount()) }, `ほかのレビュアー ${hiddenCount()} 人の記録を隠しています（${m ? '提出すると見えます' : 'レビューを始めて提出すると見えます'}）。`) : null,
      vis.length ? h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'reviewers' }, h('thead', null, h('tr', null, ['レビュアー（自己申告）', '種類', '確認済み', '前回の確認から変更あり', 'コメント', '確認事項の答え', '提出'].map((x) => h('th', { scope: 'col' }, x)))),
        h('tbody', null, vis.map((rv) => {
          let ok = 0; let chg = 0;
          Object.keys(rv.viewed).forEach((a) => { const s = markState(rv.viewed[a], a, set); if (s === 'current') ok++; else if (s === 'changed') chg++; });
          return h('tr', { 'data-reviewer': rv.reviewer.name }, h('th', { scope: 'row' }, rv.reviewer.name), h('td', null, rv.reviewer.kind === 'llm' ? 'LLM' + (rv.reviewer.model ? `（${rv.reviewer.model}）` : '') : '人'),
            h('td', { class: 'num' }, String(ok)), h('td', { class: 'num' }, String(chg)), h('td', { class: 'num' }, String(rv.comments.length)), h('td', { class: 'num' }, String(Object.keys(rv.answers).length)), h('td', null, rv.submitted || '未提出'));
        })))) : h('p', { class: 'muted' }, '表示できる記録はありません。'),
      m && st.file.reviews.length > 1 && !hiding() ? h('p', null, h('label', { for: 'rv-pick' }, '別のレビュアーの記録で続ける：'), ' ',
        h('select', { id: 'rv-pick' }, st.file.reviews.map((r) => h('option', { value: r.reviewer.name, selected: r.reviewer.name === st.me ? true : null }, r.reviewer.name))), ' ',
        h('button', { type: 'button', id: 'rv-pick-go', onclick: () => switchTo($('#rv-pick').value || null) }, 'このレビュアーで続ける')) : null,
      h('h2', null, '記録のファイルを読み込む・書き出す'),
      h('p', { class: 'muted small' }, '記録のファイル：review.yaml（設計書と同じフォルダーに置く）'),
      h('p', { id: 'rv-file-state', 'data-unsaved': unsaved() ? '1' : '0' }, unsaved() ? '書き出していない記録があります。' : '書き出していない記録はありません。', ` レビュアー ${st.file.reviews.length} 人。`),
      h('p', { class: 'buttons' }, h('button', { type: 'button', id: 'rv-import-btn', onclick: () => imp.click() }, 'review.yaml を読み込む（複数を選ぶと合わせる）'), imp, ' ',
        h('button', { type: 'button', class: m && m.submitted ? null : 'primary', id: 'rv-export', onclick: () => exportAll() }, 'review.yaml を書き出す（全員の記録）'), ' ',
        m && st.file.reviews.length > 1 ? h('button', { type: 'button', id: 'rv-export-mine', onclick: () => exportReview(true) }, '自分の記録だけ書き出す') : null, ' ',
        h('a', { href: P.route('review', 'report') }, 'レポートを作る')),
      st.slotHold ? h('div', { class: 'note warn', id: 'rv-slot-hold' }, h('p', null, `このブラウザに自動保存したレビューの記録（${st.slotHold.savedAt} に保存）が残っています。どれを使うかを選ぶまで、レビューの記録の自動保存を止めています。`),
        h('p', { class: 'buttons' }, h('button', { type: 'button', id: 'rv-slot-ask', onclick: () => askSlot(st.slotHold).then(() => changed(true)) }, '自動保存した記録をどうするか選ぶ'), ' ',
          h('button', { type: 'button', id: 'rv-slot-forget', onclick: () => CE.ask('自動保存した記録を消す', 'このブラウザに自動保存したレビューの記録を消して、いま開いている記録を使います。', [['delete', '消す'], ['cancel', 'やめる']])
            .then((c) => { if (c === 'delete') { try { localStorage.removeItem(slotKey()); } catch (e) { /* ignore */ } st.slotHold = null; CE.saveWarning(null, 'review'); changed(true); } }) }, '自動保存した記録を消す'))) : null,
      selfDeclared(),
      h('h2', null, '独立レビュー'),
      h('p', { id: 'rv-independent-state', 'data-independent': st.file.independent ? '1' : '0' }, st.file.independent ? 'この記録は独立レビューです：提出するまで、ほかのレビュアーの記録（確認済みの印・コメント・確認事項の答え）を画面に出しません。' : '独立レビューではありません（「レビューを開始」のときに選べます）。'),
      h(st.file.independent ? 'p' : 'details', { class: 'note warn', id: 'rv-independence-limits' }, st.file.independent ? null : h('summary', null, '独立レビューでできないこと'), h('strong', null, '独立レビューは画面で隠すだけです。'),
        'review.yaml を開けば、ほかのレビュアーの記録は誰でも読めます。このエディターにできるのは、提出の前に隠すのをやめる操作（ほかのレビュアーへの切り替え・設定を外す・全員の記録の書き出し）を確かめ、外れたことと日時・理由を review.yaml に記録すること、ほかの記録を初めて見た日時と、その後に直した記録に印を付けることだけです。'),
      m && m.independence ? h('p', { id: 'rv-independence', 'data-mode': m.independence.mode }, '自分の独立レビュー：', m.independence.mode === 'broken' ? `提出の前に外れた（${m.independence.broken_at}、${m.independence.reason || ''}）` : '続けている',
        m.independence.viewed_others_at ? `。ほかの記録を初めて見た日時 ${m.independence.viewed_others_at}（その後に直した記録には印が付く）` : '') : null];
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
    const out = [h('p', null, h('a', { href: P.route('review') }, '← レビューする行'), ' ・ ', h('a', { href: P.route('review', 'checklist') }, '確認事項の一覧')),
      h('h1', { tabindex: '-1', 'data-column': coll + '.' + col }, `欄：${c ? c.label : col}`),
      h('p', { class: 'muted small' }, '項目の名前：', code(`registry:${coll}#${col}`)),
      c && c.meaning ? h('p', { class: 'lead' }, H.inline(c.meaning)) : null,
      qs.length ? h('details', { open: true }, h('summary', null, `この欄を見る確認事項 ${qs.length} 件`), h('ul', null, qs.map((x) => h('li', null, h('a', { href: P.route('review', 'checklist', { q: x.id, all: '1' }) }, x.id), ' ', H.inlineRepo(x.text))))) : null];
    if (isProfile) {
      const p = reg.token_types && reg.token_types.issuance_profile;
      out.push(h('p', null, '発行方式の選択（token_types.yaml の issuance_profile）の項目です：'), h('div', { class: 'cols' }, h('div', { class: 'col' }, h('div', { class: 'ch' }, code(col)), h('div', { class: 'cv' }, p && own(p, col) ? H.value(p[col]) : '（未記入）'))));
      return out;
    }
    const idk = coll === 'catalog_answers' ? 'event' : 'id';
    out.push(h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'column' }, h('caption', null, `${KIND_LABEL[coll] || coll}の ${col}（${rows.length} 行）`),
      h('thead', null, h('tr', null, ['行', col, '問題', 'レビュー'].map((x) => h('th', { scope: 'col' }, x)))),
      h('tbody', null, rows.map((r) => {
        const anchor = coll + ':' + r[idk];
        return h('tr', { 'data-anchor': anchor }, h('th', { scope: 'row' }, rowLink(anchor), ' ', H.revealLink(coll, r[idk])),
          h('td', null, own(r, col) ? H.columnValue(coll, col, r[col]) : h('span', { class: 'muted' }, '（未記入）')),
          h('td', null, H.lintBadges(String(r[idk]))), h('td', null, rowBadges(anchor)));
      })))));
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
    const fids = h('input', { type: 'text', id: 'rv-fb-findings', 'aria-label': 'コメントの ID（空白で区切る）', placeholder: 'C01 C02', oninput: (e) => e.target.setCustomValidity('') });
    const ref = h('input', { type: 'text', id: 'rv-fb-ref', 'aria-label': 'issue・PR' });
    return [h('h2', null, 'カタログ・確認事項・対応表に戻す事項'),
      list.length ? h('ul', null, list.map((x, i) => h('li', null, h('strong', null, x.to), '：', x.content, (x.comments || []).length ? `（${x.comments.join('・')}）` : '', x.ref ? ` ${x.ref}` : '', ' ',
        h('button', { type: 'button', onclick: () => { list.splice(i, 1); m.feedback = list; if (!list.length) delete m.feedback; changed(true); } }, '消す')))) : h('p', { class: 'muted' }, 'まだありません。'),
      h('form', { class: 'filters', onsubmit: (e) => {
        e.preventDefault();
        if (!content.value.trim()) { content.focus(); return; }
        const x = { to: to.value, content: content.value.trim() };
        const ids = fids.value.split(/[\s,、]+/).filter(Boolean);
        if (ids.some((i) => !m.comments.some((f) => f.id === i))) { fids.setCustomValidity('コメントの一覧に無い ID がある'); fids.reportValidity(); return; }
        fids.setCustomValidity('');
        if (ids.length) x.comments = ids;
        if (ref.value.trim()) x.ref = ref.value.trim();
        list.push(x); m.feedback = list; changed(true);
      } }, h('label', null, '戻す先', to), h('label', null, '中身', content), h('label', null, 'コメントの ID', fids), h('label', null, 'issue・PR', ref), h('div', null, h('button', { type: 'submit' }, '足す')))];
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
      out.push(h('p', { class: 'note warn', id: 'rv-pop-changed', role: 'status' }, '⚠ 抜き取りの母集団が変わった：記録した後に、却下の行か、その内容が変わりました。記録した抜き取りは、その時のクレーム一覧では正しいものです。引き直すなら「抜き取る」を押します（前の抜き取りは previous に残ります）。'));
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
          r && r.row ? h('dl', { class: 'obj' }, ['rationale', 'assumption', 'revisit_trigger'].map((k) => [h('dt', null, k), h('dd', null, own(r.row, k) ? H.value(r.row[k]) : '（未記入）')])) : h('p', { class: 'muted' }, '今のクレーム一覧に無い行'),
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
      h('p', { class: 'lead' }, 'claim_request_*.md（共有クレームごとの 25 問）の回答を、問いごとに並べます。回答が妥当かは、確認事項（pa-01〜pa-25）で確かめます。'),
      h('p', null, h('label', { for: 'rv-pa-q' }, '問い：'), sel)];
    if (!files.length) out.push(h('p', { class: 'muted' }, 'claim_request_*.md が開かれていません。'));
    if (n && pq) out.push(h('div', { class: 'note' }, h('p', null, h('a', { href: P.route('review', 'checklist', { q: pq.id, all: '1' }) }, pq.id), ' ', H.inlineRepo(pq.text))));
    if (n) {
      out.push(h('div', { class: 'tablewrap' }, h('table', { 'data-table': 'pa' }, h('caption', null, `問 ${n}：${qtext(n)}`),
        h('thead', null, h('tr', null, ['クレーム', '回答', '根拠', ''].map((x) => h('th', { scope: 'col' }, x)))),
        h('tbody', null, files.map((f) => { const r = f.rows[n]; return h('tr', { 'data-pa-file': f.name }, h('th', { scope: 'row' }, f.target ? rowLink('claims:' + f.target) : code(f.name)),
          h('td', null, r ? H.inline(r.a) : h('span', { class: 'err' }, '（回答が無い）')), h('td', null, r ? H.inline(r.src) : '—'),
          h('td', null, r ? h('button', { type: 'button', class: 'link', onclick: () => CE.goto(f.name, r.line) }, `${f.name}:${r.line}`) : null)); })))));
    }
    out.push(h('h2', null, 'クレームごとの 25 問'), files.map((f) => H.foldable(H.foldKey('pa', f.name), h('span', null, code(f.name), f.target ? ' ― ' + f.target : ''), () => h('div', { class: 'tablewrap' }, h('table', null,
      h('thead', null, h('tr', null, ['#', '問い', '回答', '根拠'].map((x) => h('th', { scope: 'col' }, x)))),
      h('tbody', null, Object.keys(f.rows).map((k) => h('tr', { class: Number(k) === n ? 'exceeds' : null }, h('th', { scope: 'row' }, k), h('td', null, f.rows[k].q), h('td', null, H.inline(f.rows[k].a)), h('td', null, H.inline(f.rows[k].src))))))), { closed: true })));
    return out;
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
    const text = F.reportText(st.file, rv, R, env(), undefined, st.version);
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
    } }, h('h2', { class: 'wide' }, '基本情報（任意。空のままでも書き出せます）'),
    h('p', { class: 'wide muted small' }, 'レポートの最初の表に載る補足です。分かるものだけ入れます。入れない欄は「記録なし」と出ます。'),
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
      } }, '問題の件数を写す')));
  }

  function rowBadges(anchor) { const set = anchorSet(); return visible().filter((rv) => own(rv.viewed, anchor)).map((rv) => markBadge(rv.viewed[anchor], anchor, rv, set)); }
  function date(t) { return String(t || '').slice(0, 10); }
  // what the report needs of the design as it is now (the twin of tools/review_record.py report: hashes, docs)
  function env() { const hashes = {}; rowsNow().forEach((a) => { if (a.hash) hashes[a.anchor] = a.hash; }); return { hashes, rejected: rejectedAnchors().length }; }
  function viewReportFull(query) {
    const out = viewReport(query);
    const m = mine();
    if (m) out.push(h('details', { id: 'rv-report-more' }, h('summary', null, 'レポートに足す記録（専門家に回した項目・戻す事項・却下の理由の抜き取り）'),
      escalationBlock(m), feedbackBlock(m), h('h2', { id: 'rv-a-sample', tabindex: '-1' }, '却下の理由の抜き取り'), samplingBlock(m)));
    return out;
  }

  // ------------------------------------------------------------ the screens in the navigation
  function refreshCounts() {
    const s = $('#rv-file-state');
    if (s) { s.dataset.unsaved = unsaved() ? '1' : '0'; }
    const m = mine();
    if (!m || !R) return;
    const p = progress();
    const a = document.querySelector('#nav a[data-view="review"] .cnt');
    if (a) a.textContent = ' ' + p.viewed + '/' + p.total;
    const c = document.querySelector('#nav a[data-view="review/comments"] .cnt');
    if (c) c.textContent = ' ' + allComments().length;
    const q = document.querySelector('#nav a[data-view="review/checklist"] .cnt');
    if (q) { const tri = applicable(); q.textContent = ' ' + tri.filter((x) => m.answers[x.id]).length + '/' + tri.length; }
  }
  CE.onStartReview = openStart;
  P.registerView('review', {
    group: 'レビュー',
    entry: 'レビューする行',
    // the review on the dashboard: the progress, and what to look at again
    summary: () => {
      if (!st.open || !R) return null;
      const m = mine();
      const p = m ? progress() : null;
      const todos = [];
      // the rows that changed after someone marked them (every reviewer whose records are shown)
      const set = anchorSet();
      const stale = [];
      visible().forEach((rv) => Object.keys(rv.viewed).forEach((a) => { if (markState(rv.viewed[a], a, set) === 'changed') stale.push([rv, a]); }));
      stale.slice(0, 8).forEach(([rv, a]) => todos.push({ kind: 'stale', label: '前回の確認から変更あり', text: `${a}（${rv.reviewer.name} が確認した後に、行が変わった）`, href: rowHref(a) }));
      if (stale.length > 8) todos.push({ kind: 'stale', label: '前回の確認から変更あり', text: `すべて見る（${stale.length} 行）`, href: P.route('review', null, { filter: 'todo' }) });
      const un = allComments().filter(([, c]) => c.state === 'unresolved').length;
      if (un) todos.push({ kind: 'question', label: '未解決のコメント', text: `${un} 件`, href: P.route('review', 'comments') });
      if (!m) todos.push({ kind: 'start', label: 'レビュー', text: '「レビューを開始」を押すと、行の確認とコメントを記録できます', href: P.route('review') });
      else if (p.pending) todos.push({ kind: 'question', label: '未提出のコメント', text: `${p.pending} 件（「レビューを提出」で提出する）`, href: P.route('review', 'comments') });
      const lines = [`レビュアー ${visible().length} 人` + (hiddenCount() ? `（ほか ${hiddenCount()} 人は独立レビューで隠している）` : '')];
      if (m) lines.push(`${m.reviewer.name}：確認済み ${p.viewed} / ${p.total} 行・コメント ${p.comments} 件` + (m.submitted ? '・提出済み' : '・未提出'));
      lines.push(unsaved() ? '書き出していない記録があります' : '書き出していない記録はありません');
      return { id: 'review', title: 'レビュー', href: P.route('review'), lines, todos };
    },
    nav: () => {
      if (!R || !st.open) return [{ sub: '', label: 'レビューする行' }];
      const m = mine();
      const p = m ? progress() : null;
      const tri = applicable();
      return [{ sub: '', label: 'レビューする行', count: p ? p.viewed + '/' + p.total : null },
        { sub: 'checklist', label: '確認事項', count: (m ? tri.filter((x) => m.answers[x.id]).length : 0) + '/' + tri.length },
        { sub: 'comments', label: 'コメント', count: String(allComments().length) }, { sub: 'record', label: '提出と記録' },
        { sub: 'report', label: 'レポート' }, { sub: 'pa', label: '25 問の回答' }];
    },
    render: (parts, query) => {
      if (!st.open || !R) return needOpen();
      noteViewing();
      const sub = parts[0] || '';
      const key = parts.join('/');
      if (key !== st.lastKey) { if (!sub && st.lastKey !== undefined) st.shown = null; if (st.lastKey === 'record') st.justSubmitted = false; st.lastKey = key; }
      if (sub === 'checklist') return viewChecklist(query);
      if (sub === 'comments') return viewComments();
      if (sub === 'record') return viewRecord();
      if (sub === 'pa') return viewPa(query);
      if (sub === 'col') return viewColumn(parts.slice(1));
      if (sub === 'report') return viewReportFull(query);
      return viewRows(query);
    },
  });

  const RV = {
    ready: () => !!R && st.open && !st.opening,
    data: () => JSON.parse(JSON.stringify(st.file)),
    text: () => dump(st.file),
    dump,
    me: () => st.me,
    reviewing: () => st.bar && !!mine(),
    unsaved,
    reportText: (name, label) => { const rv = st.file.reviews.find((x) => x.reviewer.name === name) || visible()[0]; return rv ? F.reportText(st.file, rv, R, env(), label, st.version) : null; },
    draw,
    visibleNames: () => visible().map((r) => r.reviewer.name),
    importTexts: (list) => importFiles(list.map((x) => ({ name: x.name, text: () => Promise.resolve(x.text) }))),
    openStart,
    start: startAs,
    submit,
    progress,
    traits: () => traits(),
    triage: () => triageAll().map(([x, t]) => ({ id: x.id, show: t.show, why: t.why })),
    clock: null,
  };
  window.ClaimsReview = RV;
})();
