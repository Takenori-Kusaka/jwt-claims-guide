// The form of review.yaml (#50, #67): the canonical text, the migration from claims-review/1 and the review report.
// MIT (LICENSE of the repository).
// Pure functions, no DOM: the twin of tools/review_record.py (dump, migrate, report_text). Both sides must write the
// same bytes: the browser test compares them, and CI compares the committed report with what review.yaml generates.
// claims-review/2 follows a pull request review: per reviewer, the rows marked as viewed (viewed: bound to the content
// hash of the row, not an approval), the comments (state pending until submitted, then unresolved or resolved) and the
// submissions (one verdict for the whole review each, with the hashes of the rows viewed then).
'use strict';
(function () {
  // the build id (tools/build_claims_viewer.py, #53)
  const BUILD_ID = 'a78a07f6cdd8';
  (window.CLAIMS_BUILD = window.CLAIMS_BUILD || {})['review-format.js'] = BUILD_ID;

  const FORMAT = 'claims-review/2';
  const FORMAT_V1 = 'claims-review/1';
  // The order of the keys in the canonical text (tools/review_record.py KEY_ORDER). The keys of claims-review/2 are put
  // between those of claims-review/1 without changing their order: a v1 record still dumps to the same bytes.
  const KEY_ORDER = ['format', 'design', 'independent', 'reviews', 'reviewer', 'id', 'criterion', 'name', 'to', 'location', 'anchors',
    'column', 'questions', 'content', 'suggestion', 'severity', 'origin', 'kind', 'model', 'confused_question',
    'verdict', 'verdict_reason', 'summary',
    'response', 'owner', 'due', 'state', 'ref', 'conclusion', 'self_declared', 'started', 'updated', 'submitted',
    'independence', 'mode', 'broken_at', 'viewed_others_at', 'target', 'commit', 'materials', 'perspectives',
    'report_template', 'context', 'lite_full', 'steps', 'roles_order', 'ci', 'error', 'warn', 'info',
    'profile', 'matches_design', 'human_check', 'traits', 'answers', 'answer', 'memo', 'rows', 'viewed', 'decision',
    'reviewer_kind', 'hash', 'comment', 'edited_after_viewing_others', 'bulk', 'at', 'resolved_at', 'snapshot', 'migrated_from',
    'findings', 'comments', 'unresolved', 'migrated', 'submissions', 'sampling', 'seed', 'count', 'picked',
    'population', 'scores', 'RR1', 'RR2', 'RR3', 'RR4', 'RR5', 'RR6', 'RR7', 'pass', 'reason', 'previous',
    'replaced_at', 'escalations', 'applies', 'not_applicable', 'feedback', 'note'];
  const HEADER_V1 = '# review.yaml: レビューの記録（#50）。設計書のエディター（docs/claims/）のレビューモードが書き出した形。\n' +
    '# レビュアーの名前は自己申告です。本当の承認は GitHub の PR のレビューで行います。\n';
  const HEADER = '# review.yaml: レビューの記録。設計書のエディター（docs/claims/）が書き出した形（claims-review/2）。\n' +
    '# レビュアーの名前は自己申告です。本当の承認は GitHub の PR のレビューで行います。\n';
  const DECISION_JA = { approve: '承認', request_changes: '修正を求める', hold: '保留' };
  const VERDICT_JA = { approve: '承認', request_changes: '変更を依頼', comment: 'コメントのみ' };
  const ANSWER_JA = { yes: 'Yes', no: 'No', na: '該当なし' };
  const MISMATCH = '目的と仕組みの不一致';
  const MIGRATED_SUMMARY = 'claims-review/1 の記録から移行した。v1 には全体の判定が無い（行ごとの判定は viewed の migrated_from に残した）';
  const own = (o, k) => o !== null && o !== undefined && Object.prototype.hasOwnProperty.call(o, k);
  const isObj = (x) => x !== null && typeof x === 'object' && !Array.isArray(x);

  // ------------------------------------------------------------ the canonical text (tools/review_record.py dump)
  const ESCAPE = /[\x7f-\x9f\u2028\u2029\ufeff\ufffe\uffff]/g;
  function yq(s) { return JSON.stringify(String(s)).replace(ESCAPE, (c) => '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0')); }
  function ykey(k) { return /^[A-Za-z][A-Za-z0-9_-]*$/.test(k) && !/^(?:y|n|yes|no|on|off|true|false|null)$/i.test(k) ? k : yq(k); }
  const RANK = new Map(KEY_ORDER.map((k, i) => [k, i]));
  function order(d) {
    return Object.keys(d).sort((a, b) => {
      const ra = RANK.has(a) ? RANK.get(a) : KEY_ORDER.length; const rb = RANK.has(b) ? RANK.get(b) : KEY_ORDER.length;
      if (ra !== rb) return ra - rb;
      if (RANK.has(a)) return 0;
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
  function isV1(data) { return isObj(data) && data.format === FORMAT_V1; }
  // version: required (the caller knows the version of the file read in, or that of today's materials)
  function dump(data, version) {
    if (!version) throw new Error('ClaimsReviewFormat.dump: the template_version is required');
    const out = []; emit(data, 0, out);
    return `# template_version: ${version}\n` + (isV1(data) ? HEADER_V1 : HEADER) + out.join('\n') + '\n';
  }

  // ------------------------------------------------------------ claims-review/1 -> claims-review/2 (tools/review_record.py migrate)
  // A new object (a v2 record is returned as it is). Nothing is dropped: the decision per row and its comment are kept
  // in viewed[].migrated_from. rows -> viewed; findings -> comments (unresolved when the review was submitted, pending
  // when not); feedback[].findings -> comments; a submitted review gets one submission with the verdict comment (v1 had
  // no verdict for the whole review) and the hashes of all its rows.
  function migrate(data) {
    if (!isV1(data)) return data;
    const src = JSON.parse(JSON.stringify(data));
    const out = {};
    Object.keys(src).forEach((k) => { if (k !== 'reviews') out[k] = k === 'format' ? FORMAT : src[k]; });
    out.reviews = (src.reviews || []).map((rv) => {
      const submitted = rv.submitted;
      const n = {};
      Object.keys(rv).forEach((k) => {
        const v = rv[k];
        if (k === 'rows') {
          const viewed = {};
          Object.keys(v).forEach((a) => {
            const r = v[a];
            const m = { hash: r.hash, at: r.at };
            ['reviewer_kind', 'edited_after_viewing_others'].forEach((x) => { if (own(r, x)) m[x] = r[x]; });
            m.migrated_from = { decision: r.decision };
            if (own(r, 'comment')) m.migrated_from.comment = r.comment;
            viewed[a] = m;
          });
          n.viewed = viewed;
        } else if (k === 'findings') n.comments = v.map((f) => Object.assign({}, f, { state: submitted ? 'unresolved' : 'pending' }));
        else if (k === 'feedback') {
          n.feedback = v.map((fb) => { const o = {}; Object.keys(fb).forEach((x) => { o[x === 'findings' ? 'comments' : x] = fb[x]; }); return o; });
        } else n[k] = v;
      });
      const rows = rv.rows || {};
      const hashes = {}; Object.keys(rows).forEach((a) => { hashes[a] = rows[a].hash; });
      n.submissions = !submitted ? [] : [{ at: submitted, verdict: 'comment', summary: MIGRATED_SUMMARY, viewed: hashes,
        comments: (rv.findings || []).map((f) => f.id), migrated: true }];
      return n;
    });
    return out;
  }

  // ------------------------------------------------------------ the states of the viewed marks
  // {anchor: 'current' | 'stale' | 'missing'} (tools/review_record.py row_states); hashes: {anchor: the hash of the row now}
  function rowStates(rv, hashes) {
    const out = {};
    const viewed = rv.viewed || {};
    Object.keys(viewed).forEach((a) => { out[a] = !own(hashes, a) ? 'missing' : hashes[a] === viewed[a].hash ? 'current' : 'stale'; });
    return out;
  }
  // the rows of the latest submission, when it is an approval, that are not what was approved (changed or gone)
  function staleApproval(rv, hashes) {
    const subs = rv.submissions || [];
    if (!subs.length || subs[subs.length - 1].verdict !== 'approve') return [];
    const v = subs[subs.length - 1].viewed || {};
    return Object.keys(v).filter((a) => !own(hashes, a) || hashes[a] !== v[a]).sort();
  }

  // ------------------------------------------------------------ the report (tools/review_record.py report_text)
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
    const n = Object.values(rv.answers || {}).filter((x) => x.edited_after_viewing_others).length + Object.values(rv.viewed || {}).filter((x) => x.edited_after_viewing_others).length +
      (rv.comments || []).filter((x) => x.edited_after_viewing_others).length;
    if (n) parts.push(`その後に直した記録 ${n} 件（回答・確認済みの印・コメントの edited_after_viewing_others）`);
    if (rv.submitted && rv.updated && String(rv.updated) > String(rv.submitted)) parts.push(`提出（${rv.submitted}）の後に更新した（${rv.updated}）`);
    return parts.join('。');
  }
  // data: a claims-review/2 record (migrate() a v1 record first); rv: one of its reviews; R: the data of data/review.js;
  // env: {hashes: {anchor: the hash of the row now}, rejected: the number of rejected rows of claims.yaml, or null};
  // version: the template_version of line 1 of review.yaml (the materials of the review when materials is not recorded)
  function reportText(data, rv, R, env, label, version) {
    const hashes = (env && env.hashes) || {};
    const cand = env && env.rejected !== null && env.rejected !== undefined ? env.rejected : null;
    const form = R.report;
    const heads = {}; form.sections.forEach((s) => { heads[s.heading.slice(0, 2)] = s; });
    const stageName = new Map(R.stages.map((s) => [s.id, s.name]));
    const qs = R.questions;
    const qids = new Set(qs.map((x) => x.id));
    const ctx = rv.context || {};
    const who = rv.reviewer;
    const llm = who.kind === 'llm';
    const lines = [`# レビューレポート：${md(label || data.design)}`, '',
      '> 設計書のエディターが `review.yaml` から生成した。レビュアーの名前は自己申告で、本当の承認は GitHub の PR のレビューで行う。' + (llm ? 'レビュアーは LLM で、人による点検は未実施。' : ''), ''];
    const head = (k) => { lines.push('## ' + heads[k].heading); lines.push(''); };
    const table = (k, rows) => {
      const hd = heads[k].header;
      lines.push(row(hd)); lines.push(row(hd.map(() => '---')));
      (rows.length ? rows : [hd.map(() => '')]).forEach((r) => lines.push(r.some((x) => x) ? row(r) : '|' + ' |'.repeat(hd.length)));
      lines.push('');
    };
    // 1.
    const tgt = rv.target || {};
    const sm = rv.sampling || null;
    const scores = (sm && sm.scores) || {};
    const scored = ((sm && sm.picked) || []).filter((a) => own(scores, a));
    const passed = scored.filter((a) => scores[a].pass).length;
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
    const samp = !sm ? '記録なし' : `乱数の種「${sm.seed}」（claims.yaml の却下の行` + (cand !== null ? ` ${cand} 行` : '') + `から ${sm.count} 行。sha256(種:行) の順）：` + sm.picked.map(short).join('・') +
      `。${scored.length} 件を採点、合格 ${passed}・不合格 ${scored.length - passed}` + (scored.length < sm.picked.length ? `（未採点 ${sm.picked.length - scored.length}）` : '') +
      (sm.reason ? `。引き直した（${sm.reason}。前の抜き取り ${(sm.previous || []).length} 件）` : '');
    const versions = R.versions || {};
    const nowP = R.template_version;
    const nowR = versions['templates/review/report_template.md'];
    const mt = rv.materials || {};
    const recP = mt.perspectives || version;
    const recR = mt.report_template;
    const hasN = mt.questions !== undefined && mt.questions !== null;
    let mats = 'templates/review（レビューした時の版：perspectives.md ' + (recP || '記録なし') + (recR ? `、report_template.md ${recR}` : '') +
      (hasN ? `、問い ${mt.questions} 問` : '') + '）';
    const differs = (recP && recP !== nowP) || (recR && nowR && recR !== nowR) || (hasN && mt.questions !== qs.length);
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
    // 2. / 3.: the comments, in the columns of the findings of report_template.md
    const fs = rv.comments || [];
    head('2.');
    table('2.', fs.map((f) => [cell(f.id), cell(f.location), cell(f.content + (f.verdict_reason ? `（判定の理由：${f.verdict_reason}）` : '')), cell(f.severity), cell(f.origin), cell(f.kind),
      cell(f.kind === MISMATCH ? f.confused_question : null), cell(f.verdict)]));
    head('3.');
    table('3.', fs.map((f) => { const r = f.response || {}; return [cell(f.id), cell(r.owner), cell(r.due), cell(r.state || '未着手'), cell(r.ref)]; }));
    // 4.
    const esc = rv.escalations || {};
    head('4.');
    table('4.', (esc.applies || []).map((e) => [cell(e.criterion), cell(e.location), cell(e.to), cell(e.due), cell(e.conclusion)]));
    const na = esc.not_applicable;
    lines.push('当てはまらなかった基準：' + (na && na.length ? na.map(md).join('・') : '（記録なし）'));
    lines.push('');
    // 5.
    head('5.');
    table('5.', (rv.feedback || []).map((x) => [cell(x.to), cell(x.content), cell((x.comments || []).join('・')), cell(x.ref)]));
    // 6.
    head('6.');
    table('6.', scored.map((a) => [cell(short(a)), 'rationale'].concat([1, 2, 3, 4, 5, 6, 7].map((i) => cell(scores[a]['RR' + i] || '対象外')), [scores[a].pass ? '合格' : '不合格'])));
    const notes = scored.filter((a) => scores[a].note).map((a) => `- ${md(short(a))}：${md(scores[a].note)}`);
    if (notes.length) { notes.forEach((x) => lines.push(x)); lines.push(''); }
    // 7. (the fixed sentences are not values of review.yaml: nothing in the file can hide them)
    head('7.');
    if (ctx.human_check) { lines.push(mdLine(ctx.human_check)); lines.push(''); }
    lines.push(llm ? '人による点検は未実施（このレビューは LLM のセッションのもの。人のレビュアーの採否は未了）。'
      : 'レビュアーは人（名前は自己申告）。templates/CONTRIBUTING.md の 3. の点検の取り決めによる点検かは、この記録からは分からない。');
    lines.push('');
    lines.push('レビュアーの名前は自己申告です（エディターにはログインが無い）。本当の承認は GitHub の PR のレビューで行います。');
    lines.push('');
    // 8.
    head('8.');
    table('8.', qs.filter((x) => own(ans, x.id)).map((x) => [cell(stageName.get(x.stage) || '—'), x.id, ANSWER_JA[ans[x.id].answer], cell(ans[x.id].memo)]));
    const left = qs.filter((x) => !own(ans, x.id)).map((x) => x.id);
    if (left.length) { lines.push(`未回答：${left.length} 問（` + left.join('・') + '）'); lines.push(''); }
    if (gone.length) { lines.push(`今の観点書に無い問いへの回答：${gone.length} 件（` + gone.map(md).join('・') + '）'); lines.push(''); }
    // 9. the viewed marks and the submissions (not in the form; the form allows sections after 8.)
    lines.push('## 9. 確認済みの行と提出の記録');
    lines.push('');
    lines.push('「確認済み」は、レビュアーがその行の内容を見たという印で、承認ではありません。判定（承認／変更を依頼／コメントのみ）は、提出ごとにレビュー全体に 1 つ付けます。' +
      '印と判定は、行の内容のハッシュ（RFC 8785 JCS の SHA-256、`tools/row_hash.py`）に結びつきます。記録の後に行が変わると「前回の確認から変更あり」になり、承認は古い承認になります。' +
      'ハッシュはその行の値だけを見ます（参照するトークン種別・経路の行、25 問の回答、design.md の本文を変えても変わりません）。下の「今の行との対応」は、このレポートを生成した時のクレーム一覧と比べた状態です。');
    lines.push('');
    const subs = rv.submissions || [];
    const old = staleApproval(rv, hashes);
    lines.push(row(['日時', '判定', '総評', '確認済みの行数', 'コメント数']));
    lines.push(row(['---', '---', '---', '---', '---']));
    subs.forEach((sb, k) => {
      let v = VERDICT_JA[sb.verdict] + (sb.migrated ? '（移行）' : '');
      if (old.length && k === subs.length - 1) v += `（古い承認：内容が変更されました。${old.length} 行）`;
      lines.push(row([cell(sb.at), v, cell(sb.summary), String(Object.keys(sb.viewed || {}).length), String((sb.comments || []).length)]));
    });
    if (!subs.length) lines.push('|' + ' |'.repeat(5));
    lines.push('');
    if (!subs.length) { lines.push('未提出（判定はまだ無い）。'); lines.push(''); }
    const cs = { pending: 0, unresolved: 0, resolved: 0 };
    fs.forEach((f) => { if (own(cs, f.state)) cs[f.state]++; });
    lines.push(`コメントの状態：未提出 ${cs.pending}・未解決 ${cs.unresolved}・解決済み ${cs.resolved}`);
    lines.push('');
    const viewed = rv.viewed || {};
    const stOf = rowStates(rv, hashes);
    lines.push(row(['行', '確認した日時', '今の行との対応', '移行前の判定とコメント']));
    lines.push(row(['---', '---', '---', '---']));
    const labelOf = { current: '一致（確認したときのまま）', stale: '前回の確認から変更あり', missing: '一覧に無い行' };
    const keys = Object.keys(viewed).sort();
    keys.forEach((a) => {
      const r = viewed[a]; const kind = r.reviewer_kind || who.kind;
      const mf = r.migrated_from;
      lines.push(row([cell(a), cell(r.at) + (kind === 'llm' ? '（LLM）' : '') + (r.bulk ? '（まとめて確認）' : ''), labelOf[stOf[a]] + `（${r.hash.slice(0, 12)}）`,
        mf ? DECISION_JA[mf.decision] + (mf.comment ? `：${md(mf.comment)}` : '') : '—']));
    });
    if (!keys.length) lines.push('|' + ' |'.repeat(4));
    lines.push('');
    const cnt = (s) => keys.filter((a) => stOf[a] === s).length;
    const nBulk = keys.filter((a) => viewed[a].bulk).length;
    lines.push(`計 ${keys.length} 行：一致 ${cnt('current')}・前回の確認から変更あり ${cnt('stale')}・一覧に無い ${cnt('missing')}` + (nBulk ? `（うち、まとめて確認 ${nBulk} 行・1 行ずつ確認 ${keys.length - nBulk} 行）` : ''));
    return lines.join('\n') + '\n';
  }

  window.ClaimsReviewFormat = { BUILD_ID, FORMAT, FORMAT_V1, KEY_ORDER, HEADER, HEADER_V1, VERDICT_JA, DECISION_JA, ANSWER_JA, MIGRATED_SUMMARY,
    dump, versionOf, isV1, migrate, rowStates, staleApproval, reportText, independenceText, md, mdLine };
})();
